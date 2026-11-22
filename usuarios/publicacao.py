"""B12: documentos privados, conferência humana e publicação automática.

As operações bloqueiam a monografia antes de consultar documentos. Banco e
auditoria confirmam juntos; arquivos novos são removidos se a transação falhar.
O resultado acadêmico continua pertencendo ao B11.
"""
import hashlib
import hmac
import os
from contextlib import contextmanager
from http.client import HTTPException
from tempfile import SpooledTemporaryFile

from django.conf import settings
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.files import File
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from pypdf import PdfReader

from Curso_Django.services import OperacaoNaoPermitida
from monografias.models import Banca, DocumentoComplementar, HistoricoAcao, Monografia, Publicacao
from .integracao_microservico import MicroservicoIndisponivel, obter_pdf_remoto
from .roles import eh_administrador, pode_convidar_para_banca
from .services import _avaliacoes_titulares, calcular_resultado_banca

TIPOS_ENVIAVEIS = ('TERMO_AUTORIZACAO', 'VERSAO_CORRIGIDA', 'ATA', 'COMPROVANTE_CORRECAO')
ESTADOS_DOCUMENTAIS = ('APROVADA', 'APROVADA_COM_RESSALVAS', 'CORRECOES_ENTREGUES')


def pode_conferir_termo(usuario, monografia):
    return bool(usuario.is_authenticated and usuario.is_active and (
        eh_administrador(usuario) or (
            monografia.curso.coordenador_id
            and monografia.curso.coordenador.usuario_id == usuario.pk
        )
    ))


def pode_consultar_documentos(usuario, monografia):
    return bool(usuario.is_authenticated and usuario.is_active and (
        monografia.aluno.usuario_id == usuario.pk
        or monografia.orientador.usuario_id == usuario.pk
        or pode_conferir_termo(usuario, monografia)
    ))


def exigir_acesso(usuario, monografia):
    if not pode_consultar_documentos(usuario, monografia):
        raise PermissionDenied('Você não tem acesso aos documentos deste trabalho.')


def _monografia(pk):
    return get_object_or_404(Monografia.objects.select_for_update(of=('self',)).select_related(
        'aluno__usuario', 'orientador__usuario', 'curso__coordenador',
    ), pk=pk)


def _registrar(usuario, monografia, acao, **detalhes):
    HistoricoAcao.objects.create(ator=usuario, objeto=f'Monografia:{monografia.pk}', acao=acao,
                                detalhes={'monografia_id': monografia.pk, **detalhes})


@contextmanager
def _escrita():
    criados = []
    try:
        with transaction.atomic():
            yield criados
    except Exception:
        for storage, nome in criados:
            storage.delete(nome)
        raise


def validar_pdf(arquivo):
    """Valida bytes reais, estrutura e legibilidade; não extrai/indexa texto."""
    if arquivo is None or not arquivo.name.lower().endswith('.pdf'):
        raise ValidationError({'arquivo': 'Selecione um arquivo PDF.'})
    limite = settings.DOCUMENTOS_MAX_UPLOAD_MB * 1024 * 1024
    tamanho, digest = 0, hashlib.sha256()
    arquivo.seek(0)
    if arquivo.read(5) != b'%PDF-':
        raise ValidationError({'arquivo': 'O conteúdo não possui um cabeçalho PDF válido.'})
    arquivo.seek(0)
    for bloco in iter(lambda: arquivo.read(65536), b''):
        tamanho += len(bloco)
        if tamanho > limite:
            raise ValidationError({'arquivo': f'O PDF deve ter no máximo {settings.DOCUMENTOS_MAX_UPLOAD_MB} MB.'})
        digest.update(bloco)
    try:
        arquivo.seek(0)
        leitor = PdfReader(arquivo, strict=True)
        if leitor.is_encrypted or not len(leitor.pages):
            raise ValueError('PDF protegido ou sem páginas.')
    except Exception as exc:
        raise ValidationError({'arquivo': 'O PDF está inválido, protegido por senha ou sem páginas.'}) from exc
    finally:
        arquivo.seek(0)
    return digest.hexdigest(), tamanho


def _resultado_final(monografia):
    """Exige fechamento B11 comprovável; um status alterado isoladamente não basta."""
    evento = HistoricoAcao.objects.filter(
        acao='RESULTADO_BANCA_FINALIZADO', detalhes__monografia_id=monografia.pk,
    ).first()
    banca = Banca.objects.filter(pk=evento.detalhes.get('banca_id') if evento else None,
                                 monografia=monografia, status='REALIZADA').first()
    if not banca:
        raise OperacaoNaoPermitida('Não existe resultado de banca finalizado pelo fluxo acadêmico.')
    avaliacoes = _avaliacoes_titulares(banca)
    if any(a.finalizada_em is None for a in avaliacoes):
        raise OperacaoNaoPermitida('Todas as avaliações precisam estar finalizadas.')
    media, resultado = calcular_resultado_banca(banca)
    if evento.detalhes.get('resultado') != resultado or evento.detalhes.get('media') != str(media):
        raise OperacaoNaoPermitida('As avaliações divergem do resultado final registrado.')
    if resultado not in ('APROVADA', 'APROVADA_COM_RESSALVAS'):
        raise OperacaoNaoPermitida('Uma monografia reprovada não pode ser publicada.')
    return banca, media, resultado


def _exigir_aberta(monografia):
    if Publicacao.objects.filter(monografia=monografia).exists() or monografia.status_fluxo == 'PUBLICADA':
        raise OperacaoNaoPermitida('Documentos de uma monografia publicada não podem ser alterados.')
    if monografia.status_fluxo not in ESTADOS_DOCUMENTAIS:
        raise OperacaoNaoPermitida('Os documentos de publicação só podem ser enviados após aprovação final da banca.')


def _salvar_documento(monografia, usuario, tipo, arquivo, sha256, tamanho, criados, **extra):
    DocumentoComplementar.objects.filter(monografia=monografia, tipo=tipo, vigente=True).update(vigente=False)
    documento = DocumentoComplementar(monografia=monografia, tipo=tipo, enviado_por=usuario,
        sha256=sha256, tamanho_bytes=tamanho, nome_original=os.path.basename(arquivo.name)[:255],
        vigente=True, **extra)
    documento.arquivo.save(arquivo.name, arquivo, save=False)
    criados.append((documento.arquivo.storage, documento.arquivo.name))
    documento.full_clean()
    documento.save()
    _registrar(usuario, monografia, 'DOCUMENTO_ENVIADO', documento_id=documento.pk, tipo=tipo,
               sha256=sha256, tamanho_bytes=tamanho, origem_microservico_id=documento.origem_microservico_id)
    return documento


def enviar_documento(usuario, monografia_id, tipo, arquivo):
    with _escrita() as criados:
        monografia = _monografia(monografia_id)
        exigir_acesso(usuario, monografia)
        _exigir_aberta(monografia)
        _, _, resultado = _resultado_final(monografia)
        if tipo not in TIPOS_ENVIAVEIS:
            raise ValidationError({'tipo': 'Tipo de documento não permitido.'})
        if tipo == 'ATA':
            permitido = pode_convidar_para_banca(usuario, monografia)
        else:
            permitido = monografia.aluno.usuario_id == usuario.pk
        if not permitido:
            raise PermissionDenied('Somente o aluno autor envia termo, versão corrigida e comprovante. A ata é enviada pela orientação, coordenação ou administração.')
        if tipo == 'VERSAO_CORRIGIDA' and resultado != 'APROVADA_COM_RESSALVAS':
            raise OperacaoNaoPermitida('A versão corrigida só é permitida quando a banca exige ressalvas.')
        sha256, tamanho = validar_pdf(arquivo)
        documento = _salvar_documento(monografia, usuario, tipo, arquivo, sha256, tamanho, criados,
            decisao='PENDENTE' if tipo in ('TERMO_AUTORIZACAO', 'VERSAO_CORRIGIDA') else 'RECEBIDO')
        if tipo == 'VERSAO_CORRIGIDA':
            monografia.status_fluxo = 'CORRECOES_ENTREGUES'
            monografia.save(update_fields=['status_fluxo'])
        return documento


def abrir_documento_verificado(documento):
    """Confere o hash antes de devolver qualquer byte ao navegador/publicação."""
    try:
        arquivo = documento.arquivo.storage.open(documento.arquivo.name, 'rb')
    except OSError as exc:
        raise OperacaoNaoPermitida('O arquivo não está disponível no armazenamento.') from exc
    try:
        digest, tamanho = hashlib.sha256(), 0
        for bloco in iter(lambda: arquivo.read(65536), b''):
            tamanho += len(bloco)
            if tamanho > documento.tamanho_bytes:
                raise OperacaoNaoPermitida('A integridade do documento não foi confirmada.')
            digest.update(bloco)
        if tamanho != documento.tamanho_bytes or not hmac.compare_digest(digest.hexdigest(), documento.sha256):
            raise OperacaoNaoPermitida('A integridade do documento não foi confirmada.')
        arquivo.seek(0)
        return arquivo
    except Exception:
        arquivo.close()
        raise


def _copiar_original(monografia, usuario, criados):
    # A credencial interserviços vem do vínculo acadêmico confiável, nunca do
    # payload. O ator da publicação permanece registrado como usuario.
    identidade = next((u for u in (monografia.aluno.usuario, monografia.orientador.usuario)
                       if u and u.is_active), None)
    if not identidade or not monografia.microservico_id or not monografia.sha256:
        raise OperacaoNaoPermitida('É necessário um PDF original vinculado, com hash e conta acadêmica ativa.')
    limite = settings.DOCUMENTOS_MAX_UPLOAD_MB * 1024 * 1024
    with SpooledTemporaryFile(max_size=2 * 1024 * 1024, mode='w+b') as copia:
        resposta = obter_pdf_remoto(identidade, monografia.pk)
        tamanho = 0
        try:
            while True:
                bloco = resposta.read(65536)
                if not bloco:
                    break
                tamanho += len(bloco)
                if tamanho > limite:
                    raise ValidationError('O PDF original excede o limite permitido para publicação.')
                copia.write(bloco)
        except (OSError, HTTPException) as exc:
            raise MicroservicoIndisponivel('A transferência do PDF original falhou. Tente a conferência novamente.') from exc
        finally:
            resposta.close()
        arquivo = File(copia, name=f'original-{monografia.pk}.pdf')
        sha256, tamanho = validar_pdf(arquivo)
        if not hmac.compare_digest(sha256, monografia.sha256):
            raise OperacaoNaoPermitida('O PDF remoto difere do hash aprovado na submissão.')
        return _salvar_documento(monografia, usuario, 'ORIGINAL_APROVADA', arquivo, sha256, tamanho, criados,
                                 decisao='RECEBIDO', origem_microservico_id=monografia.microservico_id)


def _publicar_se_elegivel(usuario, monografia, criados):
    existente = Publicacao.objects.filter(monografia=monografia).first()
    if existente:
        return existente
    _exigir_aberta(monografia)
    banca, media, resultado = _resultado_final(monografia)
    termo = monografia.documentos.filter(tipo='TERMO_AUTORIZACAO', vigente=True, decisao='ACEITO').first()
    corrigida = monografia.documentos.filter(tipo='VERSAO_CORRIGIDA', vigente=True, decisao='ACEITO').first()
    if not termo or (resultado == 'APROVADA_COM_RESSALVAS' and not corrigida):
        return None
    with abrir_documento_verificado(termo):
        pass
    if resultado == 'APROVADA_COM_RESSALVAS':
        final = corrigida
        with abrir_documento_verificado(final):
            pass
    else:
        final = _copiar_original(monografia, usuario, criados)
    publicacao = Publicacao.objects.create(monografia=monografia, banca=banca,
        documento_final=final, termo=termo, publicado_por=usuario, sha256=final.sha256,
        resultado_banca=resultado, media_banca=media)
    monografia.status_fluxo = 'PUBLICADA'
    monografia.data_publicacao = timezone.localdate(publicacao.publicado_em)
    monografia.save(update_fields=['status_fluxo', 'data_publicacao'])
    _registrar(usuario, monografia, 'MONOGRAFIA_PUBLICADA', publicacao_id=publicacao.pk,
        banca_id=banca.pk, documento_final_id=final.pk, termo_id=termo.pk, sha256=final.sha256,
        resultado_banca=resultado, media_banca=str(media))
    # Outbox na mesma transação: nenhuma conexão ao broker durante a conferência.
    from repositorio.models import EventoIndexacao
    EventoIndexacao.objects.create(publicacao=publicacao, sha256=final.sha256)
    return publicacao


def publicar_se_elegivel(usuario, monografia_id):
    """Serviço idempotente; não é um botão de liberação nem ignora pré-condições."""
    with _escrita() as criados:
        monografia = _monografia(monografia_id)
        exigir_acesso(usuario, monografia)
        return _publicar_se_elegivel(usuario, monografia, criados)


def conferir_documento(usuario, monografia_id, documento_id, *, decisao, confirmacao=False, motivo=''):
    with _escrita() as criados:
        monografia = _monografia(monografia_id)
        exigir_acesso(usuario, monografia)
        documento = get_object_or_404(DocumentoComplementar, pk=documento_id, monografia=monografia)
        if documento.tipo == 'TERMO_AUTORIZACAO':
            permitido = pode_conferir_termo(usuario, monografia)
        else:
            permitido = documento.tipo == 'VERSAO_CORRIGIDA' and monografia.orientador.usuario_id == usuario.pk
        if not permitido:
            raise PermissionDenied('A correção é conferida pelo orientador; a assinatura do termo, pela coordenação do curso ou administração.')
        if decisao not in ('aceitar', 'rejeitar'):
            raise ValidationError({'decisao': 'Escolha aceitar ou rejeitar.'})
        if decisao == 'aceitar' and confirmacao is not True:
            raise ValidationError({'confirmacao': 'Confirme explicitamente a conferência do conteúdo do documento.'})
        motivo = str(motivo).strip()
        if len(motivo) > 2000 or (decisao == 'rejeitar' and not motivo):
            raise ValidationError({'motivo': 'A rejeição exige um motivo de até 2000 caracteres.'})
        if not documento.vigente:
            raise OperacaoNaoPermitida('Este documento foi substituído por uma versão mais recente.')
        desejada = 'ACEITO' if decisao == 'aceitar' else 'REJEITADO'
        if documento.decisao == desejada:
            return documento, _publicar_se_elegivel(usuario, monografia, criados)
        _exigir_aberta(monografia)
        _resultado_final(monografia)
        if documento.decisao != 'PENDENTE':
            raise OperacaoNaoPermitida('A conferência desta versão já foi encerrada. Envie uma nova versão.')
        with abrir_documento_verificado(documento):
            pass
        documento.decisao, documento.motivo = desejada, motivo
        documento.conferido_por, documento.conferido_em = usuario, timezone.now()
        documento.save(update_fields=['decisao', 'motivo', 'conferido_por', 'conferido_em'])
        if documento.tipo == 'VERSAO_CORRIGIDA':
            monografia.status_fluxo = 'APROVADA' if decisao == 'aceitar' else 'APROVADA_COM_RESSALVAS'
            monografia.save(update_fields=['status_fluxo'])
        _registrar(usuario, monografia, 'DOCUMENTO_ACEITO' if decisao == 'aceitar' else 'DOCUMENTO_REJEITADO',
                   documento_id=documento.pk, tipo=documento.tipo, sha256=documento.sha256, motivo=motivo)
        publicacao = _publicar_se_elegivel(usuario, monografia, criados)
        return documento, publicacao

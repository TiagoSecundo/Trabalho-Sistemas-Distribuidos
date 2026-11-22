"""B09/B17: orquestra o fluxo academico usando o microservico de PDF.

O banco principal e a fonte de verdade para identidade, vinculos e agendamento;
o microservico conserva o PDF, seu hash e o estado da submissao.
Nenhum ID academico e aceito do navegador para autenticar ou vincular registros.
"""

import json
import os
import socket
import uuid
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin
from urllib.request import HTTPRedirectHandler, Request, build_opener

from django.conf import settings
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from rest_framework_simplejwt.tokens import AccessToken

from Curso_Django.services import OperacaoNaoPermitida
from monografias.models import HistoricoAcao, Monografia

ESTADOS_SUBMISSAO = ('RASCUNHO', 'SUBMETIDA', 'EM_ANALISE_ORIENTADOR', 'AJUSTES_SOLICITADOS', 'APROVADA_ORIENTADOR')
ESTADOS_EDITAVEIS = ('RASCUNHO', 'AJUSTES_SOLICITADOS')


class MicroservicoIndisponivel(Exception):
    """Falha de comunicacao/infraestrutura com o servico de arquivos."""


def _token(usuario, monografia, papel):
    if not usuario.is_authenticated or not usuario.is_active:
        raise PermissionDenied('Acesso autenticado necessario.')
    if papel == 'aluno' and monografia.aluno.usuario_id != usuario.pk:
        raise PermissionDenied('Somente o aluno autor pode submeter seu arquivo.')
    if papel == 'orientador' and monografia.orientador.usuario_id != usuario.pk:
        raise PermissionDenied('Somente o orientador desta monografia pode analisar a submissao.')
    if papel not in ('aluno', 'orientador'):
        raise PermissionDenied('Perfil invalido para a integracao.')
    chave = settings.SIMPLE_JWT.get('SIGNING_KEY', '')
    if not isinstance(chave, str) or len(chave) < 32:
        raise MicroservicoIndisponivel('A chave compartilhada de JWT nao esta configurada.')
    token = AccessToken.for_user(usuario)
    token['role'] = papel
    token['aluno_id'] = monografia.aluno_id if papel == 'aluno' else None
    token['professor_id'] = monografia.orientador_id if papel == 'orientador' else None
    token['orientador_id'] = monografia.orientador_id
    token['curso_id'] = monografia.curso_id
    token['curso_ids'] = []
    token['scope'] = 'integracao:origem'
    return str(token)


def _requisicao(metodo, caminho, token, *, dados=None, arquivo=None, stream=False):
    """HTTP servidor-servidor; o JWT nunca e exposto ao navegador."""
    url_base = settings.MICROSERVICO_API_URL.rstrip('/') + '/'
    url = urljoin(url_base, caminho.lstrip('/'))
    cabecalhos = {'Authorization': f'Bearer {token}', 'Accept': 'application/json'}
    corpo = None
    if arquivo is not None:
        fronteira = '----AllTeam' + uuid.uuid4().hex
        nome = os.path.basename(arquivo.name).replace('"', '').replace('\\', '') or 'monografia.pdf'
        cabecalhos['Content-Type'] = f'multipart/form-data; boundary={fronteira}'
        arquivo.seek(0)
        conteudo = arquivo.read()
        arquivo.seek(0)
        corpo = (
            f'--{fronteira}\r\nContent-Disposition: form-data; name="arquivo"; filename="{nome}"\r\n'
            'Content-Type: application/pdf\r\n\r\n'
        ).encode('utf-8') + conteudo + f'\r\n--{fronteira}--\r\n'.encode('ascii')
    elif dados is not None:
        cabecalhos['Content-Type'] = 'application/json'
        corpo = json.dumps(dados, ensure_ascii=False).encode('utf-8')

    requisicao = Request(url, data=corpo, headers=cabecalhos, method=metodo)
    timeout = settings.MICROSERVICO_TIMEOUT

    class SemRedirecionar(HTTPRedirectHandler):
        def redirect_request(self, request, fp, code, msg, headers, newurl):
            # Nao encaminhar o JWT para outro dominio em um HTTP 301/302 malicioso.
            return None

    try:
        resposta = build_opener(SemRedirecionar).open(requisicao, timeout=timeout)
        if stream:
            return resposta  # chamador fecha ao concluir streaming
        with resposta:
            resposta_json = json.loads(resposta.read().decode('utf-8'))
        if not isinstance(resposta_json, dict):
            raise MicroservicoIndisponivel('Resposta inesperada do microservico.')
        return resposta_json
    except HTTPError as exc:
        try:
            conteudo_erro = json.loads(exc.read().decode('utf-8'))
        except (ValueError, UnicodeError):
            conteudo_erro = {}
        finally:
            exc.close()
        if exc.code == 403:
            raise PermissionDenied('O microservico recusou a permissao da operacao.') from exc
        if exc.code in (400, 404, 409, 422):
            mensagem = conteudo_erro.get('erro', conteudo_erro.get('detail', 'Operacao recusada pelo microservico.'))
            if isinstance(mensagem, (list, dict)):
                mensagem = str(mensagem)
            raise ValidationError(str(mensagem)) from exc
        raise MicroservicoIndisponivel(f'O microservico respondeu HTTP {exc.code}.') from exc
    except (URLError, socket.timeout, TimeoutError, ConnectionError) as exc:
        raise MicroservicoIndisponivel('Nao foi possivel comunicar com o microservico de PDF.') from exc
    except (ValueError, UnicodeError) as exc:
        raise MicroservicoIndisponivel('O microservico retornou uma resposta invalida.') from exc


def _validar_vinculos(monografia, resposta):
    """Nao aceitar confirmacao remota de outra monografia/aluno/curso."""
    for campo, esperado in (
        ('aluno_id', monografia.aluno_id),
        ('orientador_id', monografia.orientador_id),
        ('curso_id', monografia.curso_id),
    ):
        if str(resposta.get(campo)) != str(esperado):
            raise OperacaoNaoPermitida(f'Vinculo inconsistente no microservico: {campo}.')
    if str(resposta.get('origem_id')) != str(monografia.pk):
        raise OperacaoNaoPermitida('A monografia remota nao pertence a este registro de origem.')
    if monografia.microservico_id is not None and str(resposta.get('id')) != str(monografia.microservico_id):
        raise OperacaoNaoPermitida('A resposta remota nao corresponde a esta monografia.')


def _registrar(usuario, monografia, acao, **detalhes):
    HistoricoAcao.objects.create(
        ator=usuario, objeto=f'Monografia:{monografia.pk}', acao=acao,
        detalhes={'monografia_id': monografia.pk, **detalhes},
    )


def _aplicar_estado_remoto(monografia, resposta, usuario):
    """So sincroniza estados da orientacao; nunca retrocede uma banca ja iniciada."""
    _validar_vinculos(monografia, resposta)
    novo = resposta.get('status')
    if novo not in ESTADOS_SUBMISSAO:
        raise OperacaoNaoPermitida('Estado remoto desconhecido ou posterior a orientacao.')
    if monografia.status_fluxo not in ESTADOS_SUBMISSAO:
        raise OperacaoNaoPermitida('A monografia ja avancou para o fluxo de banca.')
    monografia.status_fluxo = novo
    if novo != 'AJUSTES_SOLICITADOS':
        monografia.motivo_ajustes = ''
    monografia.sha256 = resposta.get('hash_sha256') or monografia.sha256
    if resposta.get('submetida_em'):
        data = parse_datetime(resposta['submetida_em'])
        if data is not None:
            monografia.data_submissao = timezone.make_aware(data) if timezone.is_naive(data) else data
    monografia.save(update_fields=['status_fluxo', 'sha256', 'data_submissao', 'motivo_ajustes'])
    _registrar(usuario, monografia, 'ESTADO_ORIENTACAO_SINCRONIZADO', estado=novo)
    return monografia


def _payload_academico(monografia):
    palavras = ', '.join(monografia.palavras_chave)
    if len(palavras) > 300:
        raise ValidationError('As palavras-chave excedem 300 caracteres no servico de PDF.')
    return {
        'origem_id': monografia.pk,
        'titulo': monografia.titulo,
        'resumo': monografia.resumo,
        'palavras_chave': palavras,
        'orientador_id': monografia.orientador_id,
        'orientador_nome': monografia.orientador.nome,
        'curso_id': monografia.curso_id,
        'aluno_nome': monografia.aluno.nome,
    }


def _validar_pdf(arquivo):
    if arquivo is None or not arquivo.name.lower().endswith('.pdf'):
        raise ValidationError('Selecione um arquivo PDF.')
    limite = settings.MICROSERVICO_MAX_UPLOAD_MB * 1024 * 1024
    if arquivo.size == 0 or arquivo.size > limite:
        raise ValidationError(f'O PDF deve ter entre 1 byte e {settings.MICROSERVICO_MAX_UPLOAD_MB} MB.')
    arquivo.seek(0)
    assinatura = arquivo.read(5)
    arquivo.seek(0)
    if assinatura != b'%PDF-':
        raise ValidationError('O arquivo enviado nao possui assinatura PDF valida.')


def submeter_pdf(usuario, monografia_id, arquivo):
    """Aluno -> cria/vincula a copia remota, envia PDF e submete de fato."""
    _validar_pdf(arquivo)
    # Guarda o ID da copia remota assim que for confirmado. Se o upload ou RabbitMQ
    # falhar depois, a copia e reaproveitada (origem_id e unico no microservico).
    with transaction.atomic():
        monografia = get_object_or_404(
            Monografia.objects.select_for_update(of=('self',)).select_related('aluno', 'orientador'),
            pk=monografia_id, aluno__usuario=usuario,
        )
        if monografia.status_fluxo not in ESTADOS_EDITAVEIS:
            raise OperacaoNaoPermitida('O trabalho nao esta em rascunho ou aguardando ajustes.')
        token = _token(usuario, monografia, 'aluno')
        if monografia.microservico_id is None:
            remoto = _requisicao('POST', 'monografias/', token, dados=_payload_academico(monografia))
            _validar_vinculos(monografia, remoto)
            monografia.microservico_id = remoto['id']
            monografia.save(update_fields=['microservico_id'])
            _registrar(usuario, monografia, 'MONOGRAFIA_REMOTA_VINCULADA')

    # Segunda transacao: evita que uma falha no envio desfaça o vinculo salvo.
    with transaction.atomic():
        monografia = get_object_or_404(
            Monografia.objects.select_for_update(of=('self',)).select_related('aluno', 'orientador'),
            pk=monografia_id, aluno__usuario=usuario,
        )
        if monografia.status_fluxo not in ESTADOS_EDITAVEIS:
            raise OperacaoNaoPermitida('O trabalho nao esta aguardando submissao.')
        token = _token(usuario, monografia, 'aluno')
        remoto = _requisicao('GET', f'monografias/{monografia.microservico_id}/', token)
        _validar_vinculos(monografia, remoto)
        if remoto.get('status') not in ESTADOS_EDITAVEIS:
            return _aplicar_estado_remoto(monografia, remoto, usuario)
        remoto = _requisicao('PATCH', f'monografias/{monografia.microservico_id}/', token,
                            dados=_payload_academico(monografia))
        _validar_vinculos(monografia, remoto)
        enviado = _requisicao('POST', f'monografias/{monografia.microservico_id}/upload/', token, arquivo=arquivo)
        _validar_vinculos(monografia, enviado)
        if not enviado.get('hash_sha256'):
            raise MicroservicoIndisponivel('O microservico nao confirmou o hash SHA-256.')
        submetido = _requisicao('POST', f'monografias/{monografia.microservico_id}/submeter/', token)
        if submetido.get('status') != 'SUBMETIDA':
            raise MicroservicoIndisponivel('O microservico nao confirmou a submissao.')
        _aplicar_estado_remoto(monografia, submetido, usuario)
        _registrar(usuario, monografia, 'PDF_SUBMETIDO', sha256=monografia.sha256)
        return monografia


@transaction.atomic
def analisar_submissao(usuario, monografia_id, *, aprovar, motivo=''):
    """Orientador dono da monografia aprova ou solicita ajustes no microservico e no principal."""
    monografia = get_object_or_404(
        Monografia.objects.select_for_update(of=('self',)).select_related('orientador', 'aluno'),
        pk=monografia_id, orientador__usuario=usuario,
    )
    if monografia.status_fluxo not in ('SUBMETIDA', 'EM_ANALISE_ORIENTADOR'):
        raise OperacaoNaoPermitida('A monografia nao esta aguardando parecer do orientador.')
    if monografia.microservico_id is None:
        raise OperacaoNaoPermitida('Este trabalho nao tem submissao de PDF vinculada ao microservico.')
    if not aprovar and not motivo.strip():
        raise ValidationError('Informe o motivo dos ajustes solicitados.')
    token = _token(usuario, monografia, 'orientador')
    remoto = _requisicao('GET', f'monografias/{monografia.microservico_id}/', token)
    _validar_vinculos(monografia, remoto)
    if remoto.get('status') == 'APROVADA_ORIENTADOR':
        if not aprovar:
            raise OperacaoNaoPermitida('O orientador ja aprovou esta submissao.')
        return _aplicar_estado_remoto(monografia, remoto, usuario)
    if remoto.get('status') == 'AJUSTES_SOLICITADOS':
        if aprovar:
            raise OperacaoNaoPermitida('O orientador ja solicitou ajustes nesta submissao.')
        return _aplicar_estado_remoto(monografia, remoto, usuario)
    if remoto.get('status') not in ('SUBMETIDA', 'EM_ANALISE_ORIENTADOR'):
        raise OperacaoNaoPermitida('O estado remoto nao permite nova analise.')
    caminho = 'aprovar-orientador' if aprovar else 'solicitar-ajustes'
    resposta = _requisicao('POST', f'monografias/{monografia.microservico_id}/{caminho}/', token,
                          dados={} if aprovar else {'motivo': motivo.strip()[:500]})
    esperado = 'APROVADA_ORIENTADOR' if aprovar else 'AJUSTES_SOLICITADOS'
    if resposta.get('status') != esperado:
        raise MicroservicoIndisponivel('O microservico nao confirmou a decisao da orientacao.')
    _aplicar_estado_remoto(monografia, resposta, usuario)
    if not aprovar:
        monografia.motivo_ajustes = motivo.strip()[:500]
        monografia.save(update_fields=['motivo_ajustes'])
    _registrar(usuario, monografia, 'ORIENTACAO_APROVOU' if aprovar else 'ORIENTACAO_SOLICITOU_AJUSTES',
               **({} if aprovar else {'motivo': motivo.strip()[:500]}))
    return monografia


@transaction.atomic
def sincronizar_orientacao(usuario, monografia_id):
    """Recupera divergencia se uma requisicao remota foi concluida e a resposta se perdeu."""
    monografia = get_object_or_404(
        Monografia.objects.select_for_update(of=('self',)).select_related('aluno', 'orientador'),
        pk=monografia_id,
    )
    if monografia.aluno.usuario_id == usuario.pk:
        papel = 'aluno'
    elif monografia.orientador.usuario_id == usuario.pk:
        papel = 'orientador'
    else:
        raise PermissionDenied('Somente o aluno ou orientador pode sincronizar esta monografia.')
    if monografia.microservico_id is None:
        raise OperacaoNaoPermitida('A monografia ainda nao foi vinculada ao microservico.')
    token = _token(usuario, monografia, papel)
    remoto = _requisicao('GET', f'monografias/{monografia.microservico_id}/', token)
    return _aplicar_estado_remoto(monografia, remoto, usuario)


def obter_pdf_remoto(usuario, monografia_id):
    """Retorna o stream privado do PDF; requer participante autorizado no principal e no micro."""
    monografia = get_object_or_404(
        Monografia.objects.select_related('aluno', 'orientador'), pk=monografia_id,
    )
    papel = ('aluno' if monografia.aluno.usuario_id == usuario.pk else
             'orientador' if monografia.orientador.usuario_id == usuario.pk else None)
    if papel is None:
        raise PermissionDenied('Somente o aluno e o orientador podem consultar este PDF.')
    if monografia.microservico_id is None:
        raise OperacaoNaoPermitida('Nao existe PDF submetido neste microservico.')
    token = _token(usuario, monografia, papel)
    return _requisicao('GET', f'monografias/{monografia.microservico_id}/baixar-pdf/', token, stream=True)

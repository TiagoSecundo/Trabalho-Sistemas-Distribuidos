"""Interface B12 usando os mesmos serviços da API."""
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.shortcuts import redirect, render
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods, require_POST, require_safe
from rest_framework.exceptions import APIException

from Curso_Django.services import OperacaoNaoPermitida
from monografias.models import DocumentoComplementar, Publicacao
from .integracao_microservico import MicroservicoIndisponivel
from .publicacao import ESTADOS_DOCUMENTAIS, conferir_documento, enviar_documento, pode_conferir_termo
from .publicacao_api import monografia_documental, resposta_arquivo
from .roles import pode_convidar_para_banca


def contexto_documentos(request, pk):
    from .views import contexto_perfil
    contexto = contexto_perfil(request)
    monografia = monografia_documental(request.user, pk)
    publicacao = Publicacao.objects.filter(monografia=monografia).select_related('documento_final').first()
    aberta = monografia.status_fluxo in ESTADOS_DOCUMENTAIS and not publicacao
    tipos = []
    documentos = list(monografia.documentos.select_related('enviado_por', 'conferido_por'))
    if aberta:
        if monografia.aluno.usuario_id == request.user.pk:
            tipos = ['TERMO_AUTORIZACAO', 'COMPROVANTE_CORRECAO']
            # O serviço confirma o resultado B11, incluindo após aceitação da correção.
            from .publicacao import _resultado_final
            try:
                if _resultado_final(monografia)[2] == 'APROVADA_COM_RESSALVAS':
                    tipos.insert(0, 'VERSAO_CORRIGIDA')
            except (ValidationError, OperacaoNaoPermitida):
                pass
        if pode_convidar_para_banca(request.user, monografia):
            tipos.append('ATA')
    for doc in documentos:
        doc.pode_conferir = bool(aberta and doc.vigente and doc.decisao == 'PENDENTE' and (
            (doc.tipo == 'TERMO_AUTORIZACAO' and pode_conferir_termo(request.user, monografia))
            or (doc.tipo == 'VERSAO_CORRIGIDA' and monografia.orientador.usuario_id == request.user.pk)
        ))
    contexto.update(monografia=monografia, documentos=documentos, publicacao=publicacao,
        tipos_envio=[(t, dict(DocumentoComplementar.TIPOS)[t]) for t in tipos],
        limite_mb=settings.DOCUMENTOS_MAX_UPLOAD_MB)
    return contexto


def _erro(request, pk, exc):
    contexto = contexto_documentos(request, pk)
    contexto['erro'] = ' '.join(exc.messages) if isinstance(exc, ValidationError) else str(exc)
    codigo = 503 if isinstance(exc, MicroservicoIndisponivel) else 409 if isinstance(exc, OperacaoNaoPermitida) else 400
    return render(request, 'usuarios/documentos.html', contexto, status=codigo)


@never_cache
@login_required
@require_http_methods(['GET', 'POST'])
def documentos(request, pk):
    if request.method == 'POST':
        try:
            enviar_documento(request.user, pk, request.POST.get('tipo'), request.FILES.get('arquivo'))
        except (ValidationError, OperacaoNaoPermitida, MicroservicoIndisponivel) as exc:
            return _erro(request, pk, exc)
        messages.success(request, 'Documento enviado. Termos e correções precisam de conferência antes da publicação.')
        return redirect('usuarios:documentos', pk=pk)
    return render(request, 'usuarios/documentos.html', contexto_documentos(request, pk))


@never_cache
@login_required
@require_POST
def conferir(request, pk, documento_id):
    try:
        _, publicacao = conferir_documento(request.user, pk, documento_id,
            decisao=request.POST.get('decisao'), confirmacao=request.POST.get('confirmacao') == 'on',
            motivo=request.POST.get('motivo', ''))
    except (ValidationError, OperacaoNaoPermitida, MicroservicoIndisponivel) as exc:
        return _erro(request, pk, exc)
    messages.success(request, 'Monografia publicada automaticamente: todos os requisitos foram atendidos.' if publicacao else 'Conferência registrada.')
    return redirect('usuarios:documentos', pk=pk)


@never_cache
@login_required
@require_safe
def arquivo(request, pk, documento_id):
    try:
        return resposta_arquivo(request.user, pk, documento_id)
    except APIException as exc:
        return render(request, 'usuarios/documentos.html', {**contexto_documentos(request, pk), 'erro': str(exc.detail)}, status=exc.status_code)

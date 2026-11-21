from datetime import datetime

from django import forms
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models.deletion import ProtectedError
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone

from .services import OperacaoNaoPermitida
from usuarios.auditoria import registrar_acao


def url_objeto(url, pk):
    return url.replace('/0/', f'/{pk}/')


def exibir(valor, campo):
    if valor is None or valor == '' or valor == []:
        return '—'
    if isinstance(valor, list):
        return ', '.join(str(item) for item in valor)
    if campo in ('inicio', 'fim', 'registrada_em', 'finalizada_em', 'confirmado_em'):
        return timezone.localtime(datetime.fromisoformat(valor)).strftime('%d/%m/%Y %H:%M')
    if campo == 'data_publicacao':
        return datetime.fromisoformat(valor).strftime('%d/%m/%Y')
    return str(valor)


def contexto(config):
    api = {
        'endpoint': reverse(f"{config['api']}-list"),
        'colunas': config['colunas'],
        'campos': config.get('campos', config['colunas']),
        'lista': config['lista_url'],
        'detalhes': config['detalhes_url'],
        'editar': config['editar_url'],
        'excluir': config['excluir_url'],
        'login': reverse('account_login'),
    }
    return {**config, 'api_config': api}


def listar(request, config, template='crud/lista.html'):
    context = contexto(config)
    # Primeira página disponível também sem JavaScript; fetch atualiza pela API.
    dados = config['serializer'](config['queryset'].all()[:20], many=True).data
    context['linhas'] = [
        {'celulas': [exibir(obj.get(campo), campo) for campo, _ in config['colunas']],
         'detalhes': url_objeto(config['detalhes_url'], obj['id']),
         'editar': url_objeto(config['editar_url'], obj['id']),
         'excluir': url_objeto(config['excluir_url'], obj['id'])}
        for obj in dados
    ]
    return render(request, template, context)


def preparar_formulario(form):
    for nome, campo in form.fields.items():
        campo.widget.attrs['data-field'] = nome
        campo.widget.attrs['aria-describedby'] = f'id_{nome}_helptext id_{nome}_api_error'
        if isinstance(campo, forms.ModelChoiceField):
            campo.widget.attrs['data-kind'] = 'relation'
        elif nome == 'palavras_chave':
            campo.widget.attrs['data-kind'] = 'keywords'
        campo.widget.attrs.setdefault('class', 'form-control')


def formulario(request, config, pk=None, template='crud/formulario.html'):
    instance = get_object_or_404(config['queryset'].all(), pk=pk) if pk else None
    form = config['form'](request.POST if request.method == 'POST' else None, instance=instance)
    context = contexto(config)
    context.update({'form': form, 'editando': bool(pk), 'objeto': instance})
    context['api_config']['id'] = pk
    service = config['serializer'].service_class
    status = 200
    try:
        if instance:
            service.validar_alteracao(instance)
        if request.method == 'POST' and form.is_valid():
            alterando = instance is not None
            with transaction.atomic():
                if alterando:
                    instance = service.atualizar(instance, form.cleaned_data)
                else:
                    instance = service.criar(form._meta.model, form.cleaned_data)
                registrar_acao(request.user, instance, 'CRUD_ATUALIZACAO' if alterando else 'CRUD_CRIACAO')
            messages.success(request, 'Cadastro salvo com sucesso.')
            return redirect(url_objeto(config['detalhes_url'], instance.pk))
    except OperacaoNaoPermitida as exc:
        context['erro'] = str(exc)
        status = 409
    except ValidationError as exc:
        for campo, erros in getattr(exc, 'message_dict', {'__all__': exc.messages}).items():
            form.add_error(campo if campo in form.fields else None, erros)
    except IntegrityError:
        form.add_error(None, 'Um registro equivalente já existe ou um vínculo mudou. Atualize a página e confira os dados.')
        status = 409
    preparar_formulario(form)
    return render(request, template, context, status=status)


def detalhes(request, config, pk, template='crud/detalhes.html'):
    instance = get_object_or_404(config['queryset'].all(), pk=pk)
    context = contexto(config)
    context['api_config']['id'] = pk
    context['objeto'] = instance
    dados = config['serializer'](instance).data
    context['valores'] = [(label, exibir(dados.get(campo), campo)) for campo, label in context['api_config']['campos']]
    context['editar_url'] = url_objeto(config['editar_url'], pk)
    context['excluir_url'] = url_objeto(config['excluir_url'], pk)
    try:
        config['serializer'].service_class.validar_alteracao(instance)
    except OperacaoNaoPermitida as exc:
        context['bloqueio'] = str(exc)
    return render(request, template, context)


def excluir(request, config, pk, template='crud/excluir.html'):
    instance = get_object_or_404(config['queryset'].all(), pk=pk)
    context = contexto(config)
    context['objeto'] = instance
    context['api_config']['id'] = pk
    status = 200
    try:
        config['serializer'].service_class.validar_alteracao(instance)
        if request.method == 'POST':
            with transaction.atomic():
                config['serializer'].service_class.excluir(instance)
                registrar_acao(request.user, instance, 'CRUD_EXCLUSAO')
            messages.success(request, 'Cadastro excluído com sucesso.')
            return redirect(config['lista_url'])
    except OperacaoNaoPermitida as exc:
        context['erro'] = str(exc)
        status = 409
    except ProtectedError:
        context['erro'] = 'Este registro está em uso. Remova ou ajuste seus vínculos antes de excluir.'
        status = 409
    return render(request, template, context, status=status)

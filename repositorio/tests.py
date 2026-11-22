import hashlib
from datetime import timedelta
from unittest.mock import Mock, patch

from django.db import transaction
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from equipe.models import Curso, Professor
from monografias.models import DocumentoComplementar, Monografia, Publicacao
from usuarios.publicacao import conferir_documento, enviar_documento
from usuarios.test_publicacao import arquivo_pdf
from Curso_Django.services import OperacaoNaoPermitida
from .indexacao import MensagemInvalida, dados_evento, indexar_evento, registrar_falha
from .mensageria import despachar_pendentes
from .models import EventoIndexacao, IndicePublicacao
from .test_helpers import CenarioRepositorio, pdf_com_texto


class RepositorioTests(CenarioRepositorio, TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.preparar_cenario(cls)

    def setUp(self):
        self.arquivos_temporarios()
        self.p = self.publicar_trabalho()
        self.url = reverse('repositorio-api:monografias')

    def buscar(self, **params):
        resposta = self.client.get(self.url, params)
        self.assertEqual(resposta.status_code, 200, resposta.content)
        return resposta.json()

    def test_api_anonima_lista_detalhe_e_campos_publicos(self):
        self.assertEqual(self.buscar()['count'], 1)
        dados = self.buscar()['results'][0]
        self.assertEqual(dados['id'], self.p.monografia_id)
        self.assertEqual(dados['ano_defesa'], 2024)
        self.assertEqual(set(dados), {'id','titulo','resumo','palavras_chave','autor','orientador','curso','data_defesa','ano_defesa','data_publicacao','arquivo','url'})
        body = self.client.get(reverse('repositorio-api:monografia', args=[dados['id']])).content.decode()
        for privado in [self.aluno.email, self.aluno.matricula, self.orientador.email, self.p.termo.sha256, self.p.termo.arquivo.name, 'media_banca', 'parecer', 'enviado_por']:
            self.assertNotIn(privado, body)
        self.assertContains(self.client.get(dados['url']), dados['titulo'])

    def test_sem_ressalvas_disponibiliza_copia_original_validada(self):
        m=self.trabalho('APROVADA')
        termo=enviar_documento(self.aluno_user,m.pk,'TERMO_AUTORIZACAO',arquivo_pdf('Termo'))
        _,p=conferir_documento(self.coordenador_user,m.pk,termo.pk,decisao='aceitar',confirmacao=True)
        response=self.client.get(reverse('repositorio-api:arquivo',args=[m.pk]))
        self.assertEqual(response.status_code,200)
        self.assertEqual(hashlib.sha256(b''.join(response.streaming_content)).hexdigest(),m.sha256)
        self.assertEqual(p.documento_final.tipo,'ORIGINAL_APROVADA')

    def test_versao_antiga_termo_e_comprovante_nao_sao_indexados(self):
        anterior=DocumentoComplementar.objects.create(monografia=self.p.monografia,tipo='VERSAO_CORRIGIDA',enviado_por=self.aluno_user,
            arquivo=arquivo_pdf(conteudo=pdf_com_texto('segredoantigo')))
        indexar_evento(dados_evento(self.p.evento_indexacao))
        self.assertEqual(self.buscar(busca='segredoantigo')['count'],0)
        self.assertNotIn(anterior.arquivo.name,str(self.buscar()))
        self.assertIn(self.client.get(reverse('api-documento-arquivo',args=[self.p.monografia_id,anterior.pk])).status_code,(401,403))

    def test_migracao_reagenda_publicacoes_existentes_sem_duplicar(self):
        from importlib import import_module
        from types import SimpleNamespace
        from django.db import connection
        from django.db.migrations.executor import MigrationExecutor
        EventoIndexacao.objects.all().delete()
        apps=MigrationExecutor(connection).loader.project_state([('repositorio','0001_initial')]).apps
        migracao=import_module('repositorio.migrations.0002_enfileirar_publicacoes_existentes')
        for _ in range(2): migracao.enfileirar(apps,SimpleNamespace(connection=connection))
        self.assertEqual(EventoIndexacao.objects.count(),1)
        self.assertEqual(EventoIndexacao.objects.get().sha256,self.p.sha256)

    def test_seis_filtros_isolados_e_combinados(self):
        filtros = {'titulo':'ARQUITETURAS', 'autor':'Aluno B12', 'orientador':self.orientador.pk, 'curso':self.curso.pk, 'ano_defesa':2024, 'palavras_chave':'redes, distribuídos'}
        for key, value in filtros.items():
            with self.subTest(filtro=key):
                self.assertEqual(self.buscar(**{key:value})['count'], 1)
        self.assertEqual(self.buscar(**filtros)['count'], 1)
        for key, value in {'titulo':'inexistente', 'autor':'outra pessoa', 'orientador':999999, 'curso':999999, 'ano_defesa':2025, 'palavras_chave':'redes, inexistente'}.items():
            with self.subTest(negativo=key): self.assertEqual(self.buscar(**{key:value})['count'], 0)

    def test_ano_defesa_nao_usa_ano_publicacao_ou_fuso_utc(self):
        self.assertNotEqual(self.p.publicado_em.year, 2024)
        self.assertEqual(self.buscar(ano_defesa=2024)['count'], 1)
        self.assertEqual(self.buscar(ano_defesa=2025)['count'], 0)

    def test_estados_privados_e_status_publicada_sem_registro_nao_vazam(self):
        for status, _ in Monografia.STATUS:
            m = Monografia.objects.create(titulo='Segredo '+status, resumo='Resumo confidencial', aluno=self.aluno, curso=self.curso, orientador=self.orientador, status_fluxo=status)
            for rota in ['repositorio-api:monografia', 'repositorio-api:arquivo', 'repositorio:detalhe']:
                self.assertEqual(self.client.get(reverse(rota,args=[m.pk])).status_code,404)
        self.assertEqual(self.buscar()['count'], 1)

    def test_publicacao_com_status_divergente_ou_documento_privado_e_ocultada(self):
        for status in ['RASCUNHO','SUBMETIDA','REPROVADA','APROVADA','APROVADA_COM_RESSALVAS','CORRECOES_ENTREGUES']:
            Monografia.objects.filter(pk=self.p.monografia_id).update(status_fluxo=status)
            self.assertEqual(self.buscar()['count'], 0)
            self.assertEqual(self.client.get(reverse('repositorio-api:arquivo',args=[self.p.monografia_id])).status_code,404)
        Monografia.objects.filter(pk=self.p.monografia_id).update(status_fluxo='PUBLICADA')
        Publicacao.objects.filter(pk=self.p.pk).update(documento_final=self.p.termo, sha256=self.p.termo.sha256)
        self.assertEqual(self.buscar()['count'],0)

    def test_listas_publicas_expoem_so_nomes_e_ids_com_trabalhos(self):
        Curso.objects.create(nome='Curso sem publicações',codigo='PRIVADO')
        Professor.objects.create(nome='Professor sem trabalhos',email='privado@example.com',departamento='D',area_pesquisa='A')
        for rota, esperado in [('repositorio-api:cursos',{'id':self.curso.pk,'nome':self.curso.nome}),('repositorio-api:orientadores',{'id':self.orientador.pk,'nome':self.orientador.nome})]:
            self.assertEqual(self.client.get(reverse(rota)).json(), [esperado])

    def test_pdf_final_inline_download_e_integridade_sem_vazamento_do_termo(self):
        url = reverse('repositorio-api:arquivo',args=[self.p.monografia_id])
        for params, disposition in [({},'inline'),({'download':'1'},'attachment')]:
            response=self.client.get(url,params)
            self.assertEqual(response.status_code,200)
            self.assertTrue(response['Content-Disposition'].startswith(disposition))
            self.assertEqual(hashlib.sha256(b''.join(response.streaming_content)).hexdigest(),self.p.sha256)
        self.assertEqual(self.client.get(url,{'download':'termo'}).status_code,400)
        self.assertEqual(self.client.get('/media/'+self.p.termo.arquivo.name).status_code,404)
        self.assertIn(self.client.get(reverse('api-documento-arquivo',args=[self.p.monografia_id,self.p.termo_id])).status_code,(401,403))
        self.assertEqual(self.client.get(url+'../documentos/').status_code,404)
        with self.p.documento_final.arquivo.storage.open(self.p.documento_final.arquivo.name,'wb') as stream: stream.write(b'adulterado')
        self.assertEqual(self.client.get(url).status_code,409)

    def test_api_somente_leitura_mesmo_com_admin_e_credencial_invalida(self):
        self.assertEqual(self.client.get(self.url,HTTP_AUTHORIZATION='Basic invalido').status_code,200)
        self.client.force_login(self.admin)
        for method in ('post','patch','delete','put'):
            self.assertEqual(getattr(self.client,method)(self.url,{},content_type='application/json').status_code,405)
            self.assertEqual(getattr(self.client,method)(reverse('repositorio-api:monografia',args=[self.p.monografia_id]),{},content_type='application/json').status_code,405)

    def test_validacao_parametros_e_paginacao(self):
        for params in [{'page':0},{'page':'x'},{'page_size':51},{'ano_defesa':1899},{'curso':-1},{'orientador':'abc'},{'ordering':'sha256'},{'palavras_chave':','},{'titulo':'x'*201},{'status_fluxo':'RASCUNHO'}]:
            self.assertEqual(self.client.get(self.url,params).status_code,400,params)
        self.assertEqual(self.client.get(self.url+'?curso=1&curso=2').status_code,400)
        self.assertEqual(self.client.get(self.url,{'page':9999}).status_code,404)
        outro=self.publicar_trabalho('Zoologia e redes')
        first=self.buscar(ordering='titulo',page_size=1)
        self.assertEqual(first['results'][0]['id'],self.p.monografia_id)
        second=self.client.get(first['next']).json()
        self.assertEqual(second['results'][0]['id'],outro.monografia_id)
        self.assertIsNotNone(second['previous']); self.assertIsNone(second['next'])
        self.assertEqual(self.buscar(ordering='-titulo')['results'][0]['id'],outro.monografia_id)

    def test_consultas_sem_n_mais_um(self):
        self.publicar_trabalho('Mais um trabalho')
        with self.assertNumQueries(2): self.buscar()

    def test_busca_conteudo_so_apos_worker_e_metadados_imediatos(self):
        self.assertEqual(self.buscar(busca='Arquiteturas')['count'],1)
        self.assertEqual(self.buscar(busca='hiperconvergencia')['count'],0)
        self.assertTrue(indexar_evento(dados_evento(self.p.evento_indexacao)))
        self.assertEqual(self.buscar(busca='hiperconvergencia')['count'],1)
        self.assertEqual(self.buscar(busca='hiperconvergencia observabilidade')['count'],1)
        self.assertEqual(self.buscar(busca='Termo privado')['count'],0)
        IndicePublicacao.objects.filter(publicacao=self.p).update(sha256='0'*64)
        self.assertEqual(self.buscar(busca='hiperconvergencia')['count'],0)

    def test_busca_escapa_html_sql_e_consulta_sem_resultados(self):
        self.assertEqual(self.buscar(busca="' OR 1=1 --")['count'],0)
        Monografia.objects.filter(pk=self.p.monografia_id).update(titulo='<script>alert(1)</script>')
        html=self.client.get(reverse('repositorio:detalhe',args=[self.p.monografia_id])).content.decode()
        self.assertIn('&lt;script&gt;',html); self.assertNotIn('<script>alert(1)</script>',html)
        self.assertContains(self.client.get(reverse('repositorio:catalogo')),'data-catalogo')

    def test_outbox_publicacao_atomica_e_sem_chamada_ao_broker(self):
        self.assertEqual(EventoIndexacao.objects.count(),1)
        with patch('repositorio.mensageria.conectar',side_effect=AssertionError('Broker não pertence à requisição')):
            outra=self.publicar_trabalho('Segundo')
        self.assertEqual(EventoIndexacao.objects.get(publicacao=outra).sha256,outra.sha256)
        before=Publicacao.objects.count()
        with self.assertRaises(RuntimeError), transaction.atomic():
            self.publicar_trabalho('Rollback'); raise RuntimeError('rollback')
        self.assertEqual(Publicacao.objects.count(),before)
        self.assertEqual(EventoIndexacao.objects.count(),before)

    def test_indexacao_idempotente_e_rejeita_evento_forjado(self):
        evento=self.p.evento_indexacao; payload=dados_evento(evento)
        self.assertTrue(indexar_evento(payload)); self.assertFalse(indexar_evento(payload))
        self.assertEqual(IndicePublicacao.objects.count(),1)
        self.assertEqual(IndicePublicacao.objects.get().sha256,self.p.sha256)
        for key,value in [('sha256','0'*64),('documento_id',self.p.termo_id),('origem','microservico'),('versao',99)]:
            with self.assertRaises(MensagemInvalida): indexar_evento({**payload,key:value})

    def test_falha_integridade_e_limite_texto_nao_criam_indice(self):
        payload=dados_evento(self.p.evento_indexacao)
        with override_settings(REPOSITORIO_MAX_TEXTO=3), self.assertRaises(ValueError): indexar_evento(payload)
        self.assertFalse(IndicePublicacao.objects.exists())
        with self.p.documento_final.arquivo.storage.open(self.p.documento_final.arquivo.name,'wb') as stream: stream.write(b'quebrado')
        with self.assertRaises(OperacaoNaoPermitida): indexar_evento(payload)
        evento=self.p.evento_indexacao; evento.refresh_from_db(); self.assertIsNone(evento.processado_em)

    def test_outbox_confirma_envio_reenvia_na_duvida_e_retem_falhas(self):
        canal=Mock(); canal.basic_publish.side_effect=ConnectionError('segredo nunca deve ser persistido')
        self.assertEqual(despachar_pendentes(canal),0)
        evento=self.p.evento_indexacao; evento.refresh_from_db()
        self.assertEqual(evento.ultimo_erro,'ConnectionError'); self.assertIsNone(evento.enviado_em)
        EventoIndexacao.objects.update(proxima_tentativa=timezone.now()-timedelta(seconds=1))
        canal.basic_publish.side_effect=None
        self.assertEqual(despachar_pendentes(canal),1)
        self.assertEqual(despachar_pendentes(canal),0)
        EventoIndexacao.objects.update(proxima_tentativa=timezone.now()-timedelta(seconds=1))
        self.assertEqual(despachar_pendentes(canal),1)
        self.assertTrue(canal.basic_publish.call_args.kwargs['mandatory'])
        self.assertEqual(canal.basic_publish.call_args.kwargs['properties'].delivery_mode,2)

    def test_falha_extracao_tem_limite_e_nunca_apaga_publicacao(self):
        dados=dados_evento(self.p.evento_indexacao)
        for _ in range(3): registrar_falha(dados,ValueError('texto sensível'))
        EventoIndexacao.objects.update(proxima_tentativa=timezone.now()-timedelta(seconds=1))
        self.assertEqual(despachar_pendentes(Mock()),0)
        self.assertEqual(self.buscar()['count'],1)
        evento=EventoIndexacao.objects.get(); self.assertEqual(evento.falhas,3); self.assertEqual(evento.ultimo_erro,'ValueError')

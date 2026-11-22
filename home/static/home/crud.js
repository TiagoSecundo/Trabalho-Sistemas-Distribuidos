/* Cliente das telas Django. O servidor continua responsável pelas regras. */
(() => {
    'use strict';
    const flash = document.querySelector('[data-flash]');
    try {
        const mensagem = sessionStorage.getItem('cadastro-mensagem');
        if (mensagem && flash) {
            flash.textContent = mensagem;
            flash.hidden = false;
            sessionStorage.removeItem('cadastro-mensagem');
        }
    } catch (_) { /* Armazenamento opcional em navegadores restritos. */ }

    const configElement = document.getElementById('crud-config');
    if (!configElement) return;
    const config = JSON.parse(configElement.textContent);
    const urlObjeto = (url, id) => url.replace('/0/', `/${id}/`);
    const endpoint = config.id ? `${config.endpoint}${config.id}/` : config.endpoint;
    const feedback = document.querySelector('[data-api-error]');
    const status = document.querySelector('[data-api-status]');
    const login = document.querySelector('[data-api-login]');

    function limparErros() {
        if (feedback) { feedback.hidden = true; feedback.textContent = ''; }
        if (login) login.hidden = true;
        document.querySelectorAll('[data-error-for]').forEach(node => { node.textContent = ''; });
        document.querySelectorAll('[aria-invalid=true]').forEach(node => node.removeAttribute('aria-invalid'));
    }

    function mensagens(value) {
        if (Array.isArray(value)) return value.map(mensagens).join(' ');
        if (value && typeof value === 'object') return Object.values(value).map(mensagens).join(' ');
        return String(value);
    }

    function mostrarErro(error) {
        if (!feedback) return;
        const dados = error.dados || {};
        const texto = mensagens(dados.detail || dados);
        feedback.textContent = error.status === 400
            ? 'Confira os campos indicados. ' + texto
            : (texto || error.message || 'Não foi possível concluir a operação.');
        if (error.status === 401) feedback.textContent = 'Sua sessão expirou. Entre novamente para continuar.';
        if (error.status === 403) feedback.textContent = 'Acesso negado ou sessão inválida. Entre novamente e tente após atualizar a página.';
        if (login) login.hidden = ![401, 403].includes(error.status);
        Object.entries(dados).forEach(([campo, valor]) => {
            const input = document.getElementsByName(campo)[0];
            const erro = document.getElementById(`id_${campo}_api_error`);
            if (input && erro) {
                input.setAttribute('aria-invalid', 'true');
                erro.textContent = mensagens(valor);
            }
        });
        feedback.hidden = false;
        feedback.focus();
    }

    async function requisicao(url, method = 'GET', dados) {
        const destino = new URL(url, location.origin);
        if (destino.origin !== location.origin) throw new Error('Endereço de integração inválido.');
        const controller = new AbortController();
        const timer = setTimeout(() => controller.abort(), 20000);
        const headers = { Accept: 'application/json', 'X-Requested-With': 'XMLHttpRequest' };
        if (method !== 'GET') {
            headers['X-CSRFToken'] = document.querySelector('[name=csrfmiddlewaretoken]').value;
            if (dados !== undefined) headers['Content-Type'] = 'application/json';
        }
        try {
            const response = await fetch(destino, {
                method, credentials: 'same-origin', headers, signal: controller.signal,
                body: dados === undefined ? undefined : JSON.stringify(dados),
            });
            if (response.status === 204) return null;
            const isJson = response.headers.get('Content-Type')?.includes('application/json');
            const resultado = isJson ? await response.json() : null;
            if (!response.ok || !isJson) {
                const error = new Error('O servidor não conseguiu concluir a operação. Atualize a página e tente novamente.');
                error.status = response.status;
                error.dados = resultado;
                throw error;
            }
            return resultado;
        } catch (error) {
            if (!error.status) error.message = method === 'GET'
                ? 'Não foi possível carregar os dados. Verifique a conexão e tente novamente.'
                : 'Não foi possível confirmar a operação. Confira a lista antes de reenviar.';
            throw error;
        } finally { clearTimeout(timer); }
    }

    function exibir(valor, campo) {
        if (valor === null || valor === undefined || valor === '' || (Array.isArray(valor) && !valor.length)) return '—';
        if (Array.isArray(valor)) return valor.join(', ');
        if (['inicio', 'fim', 'registrada_em', 'finalizada_em', 'confirmado_em'].includes(campo)) {
            return new Intl.DateTimeFormat('pt-BR', { dateStyle: 'short', timeStyle: 'short', timeZone: 'America/Sao_Paulo' }).format(new Date(valor));
        }
        if (campo === 'data_publicacao') return valor.split('-').reverse().join('/');
        return String(valor);
    }

    function redirecionar(url, mensagem) {
        try { sessionStorage.setItem('cadastro-mensagem', mensagem); } catch (_) { /* opcional */ }
        location.assign(url);
    }

    const lista = document.querySelector('[data-crud-list]');
    if (lista) {
        const tbody = lista.querySelector('[data-rows]');
        const previous = lista.querySelector('[data-previous]');
        const next = lista.querySelector('[data-next]');
        const retry = lista.querySelector('[data-retry]');
        const searchForm = lista.querySelector('[data-search]');
        const initialQuery = new URLSearchParams(location.search);
        searchForm.elements.search.value = initialQuery.get('search') || '';
        let paginaAnterior = null;
        let proximaPagina = null;
        let atual = new URL(config.endpoint, location.origin);
        ['search', 'page'].forEach(key => { if (initialQuery.has(key)) atual.searchParams.set(key, initialQuery.get(key)); });
        let carregando = false;

        async function carregar(url) {
            if (carregando) return;
            carregando = true;
            atual = new URL(url, location.origin);
            limparErros();
            status.textContent = 'Carregando registros…';
            lista.setAttribute('aria-busy', 'true');
            previous.disabled = next.disabled = true;
            searchForm.querySelector('button').disabled = true;
            retry.hidden = true;
            try {
                const resultado = await requisicao(atual);
                tbody.replaceChildren();
                resultado.results.forEach(item => {
                    const row = document.createElement('tr');
                    config.colunas.forEach(([campo]) => {
                        const cell = document.createElement('td');
                        cell.textContent = exibir(item[campo], campo);
                        row.append(cell);
                    });
                    const actions = document.createElement('td');
                    actions.className = 'crud-actions';
                    [['detalhes', 'Consultar'], ['editar', 'Editar'], ['excluir', 'Excluir']].forEach(([acao, label]) => {
                        if (config.somenteConsulta && acao !== 'detalhes') return;
                        const link = document.createElement('a');
                        link.href = urlObjeto(config[acao], item.id);
                        link.textContent = label;
                        if (acao === 'excluir') link.className = 'text-danger';
                        actions.append(link);
                    });
                    row.append(actions);
                    tbody.append(row);
                });
                if (!resultado.results.length) {
                    const cell = document.createElement('td');
                    cell.colSpan = config.colunas.length + 1;
                    cell.className = 'crud-empty';
                    cell.textContent = 'Nenhum registro encontrado. Tente outro termo.';
                    const row = document.createElement('tr');
                    row.append(cell);
                    tbody.append(row);
                }
                paginaAnterior = resultado.previous;
                proximaPagina = resultado.next;
                previous.disabled = !paginaAnterior;
                next.disabled = !proximaPagina;
                lista.querySelector('[data-count]').textContent = `${resultado.count} registro(s) · Página ${atual.searchParams.get('page') || 1}`;
                const navegacao = new URL(location.href);
                ['page', 'search'].forEach(key => {
                    if (atual.searchParams.has(key)) navegacao.searchParams.set(key, atual.searchParams.get(key));
                    else navegacao.searchParams.delete(key);
                });
                history.replaceState(null, '', navegacao);
                status.textContent = '';
            } catch (error) {
                status.textContent = 'A lista pode estar desatualizada.';
                retry.hidden = false;
                mostrarErro(error);
            } finally {
                lista.removeAttribute('aria-busy');
                searchForm.querySelector('button').disabled = false;
                carregando = false;
            }
        }
        searchForm.addEventListener('submit', event => {
            event.preventDefault();
            const url = new URL(config.endpoint, location.origin);
            const termo = searchForm.elements.search.value.trim();
            if (termo) url.searchParams.set('search', termo);
            carregar(url);
        });
        previous.addEventListener('click', () => carregar(paginaAnterior));
        next.addEventListener('click', () => carregar(proximaPagina));
        retry.addEventListener('click', () => carregar(atual));
        carregar(atual);
    }

    const form = document.querySelector('[data-crud-form], [data-crud-delete]');
    if (form) {
        let enviando = false;
        form.addEventListener('submit', async event => {
            event.preventDefault();
            if (enviando) return;
            limparErros();
            const excluir = form.hasAttribute('data-crud-delete');
            const dados = {};
            try {
                form.querySelectorAll('[data-field]').forEach(input => {
                    let valor = input.value;
                    if (input.dataset.kind === 'relation') valor = valor ? Number(valor) : null;
                    if (input.dataset.kind === 'keywords') {
                        valor = valor.trim().startsWith('[') ? JSON.parse(valor) : valor.split(',').map(x => x.trim()).filter(Boolean);
                    }
                    dados[input.name] = valor;
                });
            } catch (_) {
                mostrarErro({ status: 400, dados: { palavras_chave: ['Informe palavras separadas por vírgula ou uma lista JSON válida.'] } });
                return;
            }
            enviando = true;
            const button = form.querySelector('[type=submit]');
            button.disabled = true;
            status.textContent = excluir ? 'Excluindo…' : 'Salvando…';
            try {
                const resultado = await requisicao(endpoint, excluir ? 'DELETE' : (config.id ? 'PATCH' : 'POST'), excluir ? undefined : dados);
                redirecionar(excluir ? config.lista : urlObjeto(config.detalhes, resultado.id), excluir ? 'Cadastro excluído com sucesso.' : 'Cadastro salvo com sucesso.');
            } catch (error) {
                mostrarErro(error);
                button.disabled = false;
                enviando = false;
                status.textContent = '';
            }
        });
    }

    const detalhe = document.querySelector('[data-crud-detail]');
    if (detalhe) {
        status.textContent = 'Atualizando dados…';
        requisicao(endpoint).then(dados => {
            const valores = detalhe.querySelector('[data-values]');
            valores.replaceChildren();
            config.campos.forEach(([campo, label]) => {
                const bloco = document.createElement('div');
                if (['resumo', 'parecer'].includes(campo)) bloco.className = 'wide';
                const dt = document.createElement('dt');
                const dd = document.createElement('dd');
                dt.textContent = label;
                dd.textContent = exibir(dados[campo], campo);
                bloco.append(dt, dd);
                valores.append(bloco);
            });
            status.textContent = '';
        }).catch(error => { status.textContent = 'Os dados podem estar desatualizados.'; mostrarErro(error); });
    }
})();

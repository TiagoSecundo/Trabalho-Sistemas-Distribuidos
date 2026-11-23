(() => {
    const painel = document.querySelector('#estatisticas');
    const formulario = painel.querySelector('form');
    const curso = formulario.elements.curso;
    const graficos = new Map();
    const numero = new Intl.NumberFormat('pt-BR', {maximumFractionDigits: 2});
    let consulta;

    function dadosGrafico(indicador, dados) {
        if (indicador === 'taxa') {
            return dados.total ? {
                rotulos: ['Aprovadas (inclui ressalvas)', 'Reprovadas'],
                valores: [dados.aprovadas, dados.reprovadas],
                resumo: `${numero.format(dados.percentual)}% de aprovação (${dados.total} defesas com resultado).`,
                tipo: 'doughnut',
            } : null;
        }
        if (indicador === 'tempo') {
            return dados.total ? {
                rotulos: ['Tempo médio'],
                valores: [dados.dias],
                resumo: `${numero.format(dados.dias)} dias (defesas com datas válidas: ${dados.total}).`,
                unidade: ' dias',
                tipo: 'bar',
            } : null;
        }
        if (!dados.length) return null;
        return {
            rotulos: dados.map(item => item.rotulo ?? String(item.ano)),
            valores: dados.map(item => item.total),
            horizontal: indicador !== 'ano',
            resumo: indicador === 'ano' ? 'Defesas realizadas' : 'Monografias submetidas',
            tipo: 'bar',
        };
    }

    async function carregar(secao, cursoId, signal) {
        const status = secao.querySelector('[role=status]');
        const canvas = secao.querySelector('canvas');
        const detalhes = secao.querySelector('details');
        const lista = detalhes.querySelector('ul');
        graficos.get(secao)?.destroy();
        graficos.delete(secao);
        canvas.parentElement.hidden = true;
        detalhes.hidden = true;
        lista.replaceChildren();
        status.textContent = 'Carregando…';
        try {
            const url = new URL(secao.dataset.endpoint, window.location.href);
            if (cursoId) url.searchParams.set('curso', cursoId);
            const resposta = await fetch(url, {headers: {Accept: 'application/json'}, signal});
            if (!resposta.ok) throw new Error(resposta.status);
            const dados = await resposta.json();
            if (signal.aborted) return;
            const grafico = dadosGrafico(secao.dataset.indicador, dados);
            if (!grafico) {
                status.textContent = 'Nenhum dado para este indicador.';
                return;
            }
            grafico.rotulos.forEach((rotulo, indice) => {
                const item = document.createElement('li');
                item.textContent = `${rotulo}: ${numero.format(grafico.valores[indice])}${grafico.unidade ?? ''}`;
                lista.append(item);
            });
            detalhes.hidden = false;
            status.textContent = grafico.resumo;
            canvas.parentElement.hidden = false;
            if (grafico.horizontal) {
                canvas.parentElement.style.height = `${Math.max(220, grafico.rotulos.length * 30 + 40)}px`;
            }
            const barras = grafico.tipo === 'bar';
            graficos.set(secao, new Chart(canvas, {
                type: grafico.tipo,
                data: {
                    labels: grafico.rotulos,
                    datasets: [{
                        data: grafico.valores,
                        backgroundColor: barras ? '#087e8b' : ['#087e8b', '#b54153'],
                    }],
                },
                options: {
                    indexAxis: grafico.horizontal ? 'y' : 'x',
                    maintainAspectRatio: !grafico.horizontal,
                    plugins: {legend: {display: !barras}},
                    scales: barras ? {
                        [grafico.horizontal ? 'x' : 'y']: {
                            beginAtZero: true,
                            ticks: grafico.unidade ? {} : {precision: 0},
                        },
                    } : {},
                },
            }));
        } catch (erro) {
            if (signal.aborted) return;
            canvas.parentElement.hidden = true;
            status.textContent = detalhes.hidden
                ? 'Não foi possível carregar os dados. Tente filtrar novamente.'
                : `${status.textContent} Não foi possível desenhar o gráfico. Consulte os valores.`;
        }
    }

    function atualizar() {
        consulta?.abort();
        consulta = new AbortController();
        painel.querySelectorAll('[data-indicador]').forEach(secao => carregar(secao, curso.value, consulta.signal));
    }

    formulario.addEventListener('submit', evento => {
        evento.preventDefault();
        atualizar();
    });
    atualizar();
})();

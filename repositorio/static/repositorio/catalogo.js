(() => {
  'use strict';
  const root = document.querySelector('[data-catalogo]');
  if (!root) return;
  const form = document.getElementById('busca-repositorio');
  const results = root.querySelector('[data-resultados]');
  const count = document.getElementById('contagem');
  const error = root.querySelector('[data-erro]');
  const pagination = root.querySelector('.repo-pagination');
  const labels = {busca:'Busca', titulo:'Título', autor:'Autor', curso:'Curso', orientador:'Orientador', ano_defesa:'Defesa', palavras_chave:'Palavras-chave'};
  let controller, current, generation = 0;
  const node = (tag, text, className) => {
    const el = document.createElement(tag);
    if (text !== undefined) el.textContent = text;
    if (className) el.className = className;
    return el;
  };
  const link = (text, url, className) => {
    const el = node('a', text, className);
    el.href = url;
    return el;
  };
  async function json(url, signal) {
    const response = await fetch(url, {headers:{Accept:'application/json'}, signal, credentials:'omit'});
    const data = await response.json();
    if (!response.ok) {
      const message = data.detail || Object.entries(data).map(([k,v]) => `${labels[k] || k}: ${[].concat(v).join(' ')}`).join(' ');
      throw new Error(message || 'Não foi possível carregar o acervo.');
    }
    return data;
  }
  function syncForm() {
    const params = new URLSearchParams(location.search);
    for (const name of [...Object.keys(labels), 'ordering']) {
      const el = form.elements.namedItem(name);
      const value = params.get(name) || (name === 'ordering' ? '-data_defesa' : '');
      if (el.tagName === 'SELECT' && value && !Array.from(el.options).some(o => o.value === value)) {
        const option = node('option', `Seleção ${value}`); option.value = value; el.append(option);
      }
      el.value = value;
    }
  }
  function navigate(params) {
    const suffix = params.toString();
    history.pushState({}, '', location.pathname+(suffix ? '?'+suffix : ''));
    syncForm(); load(true);
  }
  function clear() { navigate(new URLSearchParams()); }
  function renderFilters(params) {
    const target = root.querySelector('[data-filtros-ativos]'); target.replaceChildren();
    for (const [name,label] of Object.entries(labels)) {
      if (!params.get(name)) continue;
      const field = form.elements.namedItem(name);
      const value = field.tagName === 'SELECT' ? field.selectedOptions[0]?.textContent : params.get(name);
      const button = node('button', `${label}: ${value} ×`);
      button.type='button'; button.setAttribute('aria-label', `Remover filtro ${label}: ${value}`);
      button.addEventListener('click', () => {const next = new URLSearchParams(location.search);next.delete(name);next.delete('page');navigate(next);});
      target.append(button);
    }
  }
  function card(item) {
    const article = node('article', undefined, 'repo-card');
    const tags = node('div', undefined, 'repo-tags'); tags.append(node('span', item.curso.nome), node('span', `Defesa ${item.ano_defesa}`));
    const title = node('h3'); title.append(link(item.titulo, item.url));
    const meta = node('p', `${item.autor} · Orientação: ${item.orientador.nome}`, 'repo-card-meta');
    const abstract = node('p', item.resumo.length > 230 ? item.resumo.slice(0,230)+'…' : item.resumo, 'repo-card-abstract');
    const bottom = node('div', undefined, 'repo-card-bottom');
    const keywords = node('ul', undefined, 'repo-keywords');
    for (const word of item.palavras_chave.slice(0,4)) keywords.append(node('li', word));
    bottom.append(keywords, link('Ver trabalho →', item.url, 'repo-card-link'));
    article.append(tags,title,meta,abstract,bottom); return article;
  }
  async function load(focus=false) {
    controller?.abort(); controller=new AbortController(); const seq=++generation;
    const params = new URLSearchParams(location.search); renderFilters(params);
    results.setAttribute('aria-busy','true'); error.hidden=true; pagination.hidden=true;
    count.textContent='Buscando trabalhos…'; results.replaceChildren(node('div','Buscando trabalhos publicados…','repo-empty'));
    try {
      const data = await json(root.dataset.api+'?'+params, controller.signal);
      if (seq !== generation) return;
      current=data; results.replaceChildren(...data.results.map(card));
      count.textContent=`${data.count} ${data.count === 1 ? 'trabalho encontrado' : 'trabalhos encontrados'}`;
      if (!data.count) {
        const empty=node('div',undefined,'repo-empty');
        empty.append(node('h3','Nenhum trabalho encontrado'),node('p','Experimente outros termos ou remova alguns filtros.'));
        const button=node('button','Ver todos os trabalhos','repo-btn');button.type='button';button.addEventListener('click',clear);empty.append(button);results.append(empty);
      }
      pagination.hidden=data.pages<=1;
      root.querySelector('[data-pagina]').textContent=`Página ${data.page} de ${data.pages}`;
      root.querySelector('[data-anterior]').disabled=!data.previous;
      root.querySelector('[data-proxima]').disabled=!data.next;
      if(focus) document.getElementById('resultados-titulo').focus({preventScroll:true});
    } catch(exc) {
      if(exc.name==='AbortError' || seq!==generation) return;
      results.replaceChildren(); count.textContent='Pesquisa não concluída.'; error.hidden=false;
      root.querySelector('[data-mensagem-erro]').textContent=exc instanceof TypeError ? 'Não foi possível conectar. Verifique sua conexão e tente novamente.' : exc.message;
    } finally {if(seq===generation) results.setAttribute('aria-busy','false');}
  }
  function submit(event) {
    event?.preventDefault();
    if(!form.reportValidity()) return;
    const params = new URLSearchParams();
    for (const [key,value] of new FormData(form)) if(String(value).trim()) params.set(key,String(value).trim());
    navigate(params);
  }
  form.addEventListener('submit',submit);
  form.elements.ordering.addEventListener('change',submit);
  root.querySelector('[data-limpar]').addEventListener('click',clear);
  root.querySelector('[data-tentar]').addEventListener('click',()=>load());
  for (const [selector,key] of [['[data-anterior]','previous'],['[data-proxima]','next']]) {
    root.querySelector(selector).addEventListener('click',()=>{if(current?.[key]) navigate(new URL(current[key],location.origin).searchParams);});
  }
  window.addEventListener('popstate',()=>{syncForm();load();});
  if(matchMedia('(max-width:767px)').matches) root.querySelector('.repo-filters').open=false;
  async function options() {
    let failed=false;
    await Promise.all(['curso','orientador'].map(async name => {
      try {
        const data=await json(name==='curso' ? root.dataset.cursos : root.dataset.orientadores);
        const select=form.elements.namedItem(name);
        const selected=select.value;
        while(select.options.length>1) select.remove(1);
        for(const item of data){const option=node('option',item.nome);option.value=item.id;select.append(option);}
        if(selected && !Array.from(select.options).some(o=>o.value===selected)) {
          const option=node('option',`Seleção ${selected}`);option.value=selected;select.append(option);
        }
        select.value=selected;
      } catch (_) { failed=true; }
    }));
    root.querySelector('[data-opcoes-erro]').hidden=!failed;
    renderFilters(new URLSearchParams(location.search));
  }
  root.querySelector('[data-recarregar-opcoes]').addEventListener('click',options);
  syncForm();load();options();
})();

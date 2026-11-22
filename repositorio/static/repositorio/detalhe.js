(() => {
  'use strict';
  const root=document.querySelector('[data-api-detalhe]');
  if(!root) return;
  // O HTML inicial também funciona sem JavaScript; a API é o contrato dos dados.
  async function atualizar() {
    const error=root.querySelector('[data-erro-detalhe]');
    try {
      const response=await fetch(root.dataset.apiDetalhe,{headers:{Accept:'application/json'},credentials:'omit'});
      if(response.status===404) {
        root.querySelector('.repo-detail-header').hidden=true;
        root.querySelector('.repo-detail-grid').hidden=true;
        error.textContent='Este trabalho não está disponível no repositório público.';error.hidden=false;return;
      }
      if(!response.ok) throw new Error('Falha ao atualizar');
      const data=await response.json();
      root.querySelector('h1').textContent=data.titulo;
      document.title=data.titulo+' · Repositório AllTeam';
      root.querySelector('.repo-author').textContent=data.autor;
      root.querySelector('[data-curso]').textContent=data.curso.nome;
      root.querySelector('[data-defesa]').textContent='Defesa '+data.ano_defesa;
      const abstract=root.querySelector('.repo-abstract');abstract.replaceChildren();
      for(const text of data.resumo.split(/\n\s*\n/)) {const paragraph=document.createElement('p');paragraph.textContent=text;abstract.append(paragraph);}
      const links=root.querySelectorAll('.repo-file>.repo-btn');
      links[0].href=data.arquivo.url;links[1].href=data.arquivo.download;
      const values=root.querySelectorAll('.repo-file dd');
      values[0].querySelector('a').textContent=data.orientador.nome;
      values[1].textContent=data.curso.nome;values[2].textContent=data.ano_defesa;
      root.dataset.apiConfirmada='true';
    } catch(_) {
      error.textContent='Não foi possível atualizar os dados agora. Recarregue a página para tentar novamente.';
      error.hidden=false;
    }
  }
  atualizar();
})();

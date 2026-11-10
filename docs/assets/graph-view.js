/* Lazy, bounded citation view. Cytoscape version is intentionally pinned. */
(() => {
  let cy = null, layout = null, loader = null;
  window.stopCitationGraph = () => { layout?.stop(); cy?.destroy(); layout = cy = null; };
  function library() {
    if (window.cytoscape) return Promise.resolve(window.cytoscape);
    if (!loader) loader = new Promise((resolve, reject) => {
      const script = document.createElement('script');
      script.src = 'https://cdn.jsdelivr.net/npm/cytoscape@3.33.1/dist/cytoscape.min.js';
      const timeout = setTimeout(() => { script.remove(); loader = null; reject(new Error('Graph library timeout')); }, 15000);
      script.onload = () => { clearTimeout(timeout); resolve(window.cytoscape); };
      script.onerror = () => { clearTimeout(timeout); script.remove(); loader = null; reject(new Error('Graph library unavailable')); };
      document.head.appendChild(script);
    });
    return loader;
  }
  window.renderCitationGraph = async ({panel, manifest, artifact, papers, valid, navigate}) => {
    const descriptor = manifest.graph;
    if (!descriptor) { panel.textContent = 'Graph coverage is unavailable in this build.'; return; }
    const params = new URLSearchParams(location.hash.split('?')[1] || '');
    const center = params.get('paper');
    const hops = params.get('hops') === '2' ? 2 : 1;
    const year = params.get('year') || 'ALL', category = params.get('category') || 'ALL';
    panel.innerHTML = '<a href="#/catalog" class="underline">Catalog</a><h1 class="text-xl font-semibold">Citation graph</h1><p data-graph-status>Loading graph…</p>';
    const status = panel.querySelector('[data-graph-status]');
    try {
      const index = await artifact(descriptor.index.path);
      const pointers = index.pointers;
      const record = async id => {
        if (!Object.hasOwn(pointers,id)) throw new Error('Graph record missing');
        return (await artifact(pointers[id]))[id];
      };
      const byId = new Map(papers.map(p => [p.id,p]));
      const projected = await window.projectCitationGraph({index,record,center,hops,year,category,valid});
      if (!projected || !valid()) return;
      const {nodes,edges} = projected;
      panel.querySelector('h1').textContent = center ? 'Paper citation neighborhood' : 'Most cited in this corpus';
      status.textContent = `${nodes.length} nodes, ${edges.length} edges; ${projected.omitted_nodes} nodes and ${projected.omitted_edges} edges omitted. Partial citation lineage. Arrows: citing paper → referenced paper. OpenAlex references; legacy observations may be unverified.`;
      const controls = document.createElement('div'); controls.className = 'flex flex-wrap gap-3';
      for (const [label, values, value, key] of [['Year',['ALL',...new Set(papers.map(p=>String(p.year)))].sort().reverse(),year,'year'],['Category',['ALL',...new Set(papers.flatMap(p=>p.categories))].sort(),category,'category'],...(center ? [['Hops',['1','2'],String(hops),'hops']] : [])]) {
        const wrapper=document.createElement('label'); wrapper.textContent=label+' ';
        const select=document.createElement('select'); select.className='bg-slate-100 dark:bg-slate-800 rounded p-1';
        for (const option of values) { const el=document.createElement('option');el.value=option;el.textContent=option;select.appendChild(el); }
        select.value=value; select.onchange=()=>{params.set(key,select.value);location.hash='#/graph?'+params;};
        wrapper.appendChild(select);controls.appendChild(wrapper);
      }
      panel.appendChild(controls);
      const canvas=document.createElement('div');canvas.id='citationCanvas';canvas.style.height='480px';canvas.style.maxWidth='100%';canvas.setAttribute('aria-label','Citation graph; equivalent keyboard links follow');panel.appendChild(canvas);
      const list=document.createElement('details');list.open=true;
      const summary=document.createElement('summary');summary.textContent='Papers and directed relationships (keyboard accessible)';list.appendChild(summary);
      const ul=document.createElement('ul');
      for (const node of nodes) {
        const li=document.createElement('li'); const link=document.createElement('a');link.href='#/paper/'+encodeURIComponent(node.id);link.textContent=node.title;link.className='underline';li.appendChild(link);
        const targets=edges.filter(e=>e.source===node.id);
        if (targets.length) { const refs=document.createElement('ul');refs.className='ml-4'; for (const edge of targets) {const item=document.createElement('li'); const target=document.createElement('a');target.href='#/paper/'+encodeURIComponent(edge.target);target.textContent='References: '+byId.get(edge.target).title;target.className='underline';item.appendChild(target);refs.appendChild(item);} li.appendChild(refs); }
        ul.appendChild(li);
      }
      list.appendChild(ul);panel.appendChild(list);
      if (!nodes.length) {canvas.textContent='No papers match these filters.';return;}
      if (!edges.length) canvas.textContent='No matched relationships in this selection. Papers remain available below.';
      try {
        const cytoscape=await library(); if (!valid()) return;
        const positions = new Map(nodes.map((node,index)=>{let seed=2166136261;for(const char of node.id)seed=Math.imul(seed^char.charCodeAt(0),16777619)>>>0;const angle=2*Math.PI*index/nodes.length;const radius=180+(seed%41);return [node.id,{x:radius*Math.cos(angle),y:radius*Math.sin(angle)}];}));
        cy=cytoscape({container:canvas,elements:[...nodes.map(n=>({data:{id:n.id,label:n.title.slice(0,45)},position:positions.get(n.id)})),...edges.map((e,i)=>({data:{id:'edge:'+i,...e}}))],style:[{selector:'node',style:{'background-color':'#0284c7',label:'data(label)','font-size':9,color:'#64748b','text-wrap':'wrap','text-max-width':100}},{selector:'edge',style:{width:1,'line-color':'#94a3b8','target-arrow-color':'#94a3b8','target-arrow-shape':'triangle','curve-style':'bezier'}}],layout:{name:'preset'},minZoom:.1,maxZoom:4});
        layout=cy.layout({name:'preset',positions:node=>positions.get(node.id()),fit:true,padding:30,animate:false});layout.run();
        cy.on('tap','node',event=>navigate(event.target.id()));
        canvas.dataset.ready='true';canvas.dataset.nodes=nodes.length;canvas.dataset.edges=edges.length;
      } catch(error) { if(valid()) canvas.textContent='Interactive graph unavailable. Use the paper and relationship links below.'; }
    } catch(error) {
      if (!valid()) return;
      status.textContent='Graph data could not be loaded.';
      const retry=document.createElement('button');retry.textContent='Retry graph';retry.className='underline';retry.onclick=()=>window.renderCitationGraph({panel,manifest,artifact,papers,valid,navigate});panel.appendChild(retry);
    }
  };
})();

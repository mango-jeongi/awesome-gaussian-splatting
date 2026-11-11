async (page) => {
  const errors=[];
  page.on('pageerror', error=>errors.push(error.message));
  const base=new URL(page.url()); base.hash='';
  const oracle=await page.evaluate(async()=>{
    const m=await (await fetch('./data/manifest.json')).json();
    const g=await (await fetch('./data/'+m.graph.index.path)).json();
    const hub=Object.entries(g.nodes).sort((a,b)=>b[1].incoming_count-a[1].incoming_count||a[0].localeCompare(b[0]))[0];
    return {total:m.total_count,edges:m.total_edges,build:m.build_digest,hub:hub[0],hub_incoming:hub[1].incoming_count};
  });
  if(oracle.total!==4101||oracle.edges!==27329)throw new Error('Unexpected build oracle');
  base.hash='#/paper/2506.21633'; await page.goto(base.href);
  await page.waitForFunction(()=>document.querySelector('#paperRoute h1')?.textContent.startsWith('SAR-GS:'));
  const alias=await page.evaluate(()=>({hash:location.hash,title:document.querySelector('#paperRoute h1').textContent,text:document.querySelector('#paperRoute').textContent}));
  if(alias.hash!=='#/paper/paper%3A2025-b16566cdad'||!alias.text.includes('Aobo Li')||!alias.text.includes('2025-06-25'))throw new Error(JSON.stringify(alias));
  const cdp=await page.context().newCDPSession(page);
  await cdp.send('Emulation.setCPUThrottlingRate',{rate:4});
  await page.setViewportSize({width:1440,height:1000});
  const results=[];
  for(const hash of ['#/graph','#/graph?paper='+encodeURIComponent(oracle.hub),'#/graph?paper='+encodeURIComponent(oracle.hub)+'&hops=2']){
    const oldCanvas=await page.locator('#citationCanvas').count()?await page.locator('#citationCanvas').elementHandle():null;
    await page.evaluate(hash=>{window.__graphStart=performance.now();location.hash=hash;},hash);
    if(oldCanvas)await oldCanvas.waitForElementState('hidden');
    await page.waitForFunction(()=>document.querySelector('#citationCanvas')?.dataset.ready==='true',null,{timeout:30000});
    results.push(await page.evaluate(async()=>{
      await new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)));
      const canvas=document.querySelector('#citationCanvas'),now=performance.now();
      const resources=performance.getEntriesByType('resource').filter(r=>r.startTime>=window.__graphStart&&(r.name.includes('/data/graph/')||r.name.includes('cytoscape')));
      return {route:location.hash,total_ms:now-window.__graphStart,after_last_resource_ms:now-Math.max(window.__graphStart,...resources.map(r=>r.responseEnd)),nodes:Number(canvas.dataset.nodes),edges:Number(canvas.dataset.edges),status:document.querySelector('[data-graph-status]').textContent};
    }));
  }
  await cdp.send('Emulation.setCPUThrottlingRate',{rate:1}); await cdp.detach();
  await page.setViewportSize({width:390,height:844});
  const mobile=await page.evaluate(()=>({width:innerWidth,scrollWidth:document.documentElement.scrollWidth}));
  const caps=results[0].nodes<=300&&results[0].edges<=1200&&results[1].nodes<=80&&results[1].edges<=200&&results[2].nodes<=150&&results[2].edges<=400;
  const egoPassed=results.slice(1).every(x=>x.after_last_resource_ms<=2000);
  const result={oracle,alias:{hash:alias.hash,title:alias.title,source_authors_and_date_verified:true},browser:await page.context().browser().version(),cpu_slowdown:4,network:'unthrottled loopback; ego measured after required resources',results,caps_passed:caps,ego_after_data_passed:egoPassed,mobile,page_errors:errors};
  if(!caps||!egoPassed||mobile.scrollWidth>mobile.width||errors.length)throw new Error(JSON.stringify(result));
  return result;
}

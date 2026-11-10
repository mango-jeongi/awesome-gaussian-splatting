async (page) => {
 await page.setViewportSize({width:1440,height:1000});
 const cdp=await page.context().newCDPSession(page);await cdp.send('Emulation.setCPUThrottlingRate',{rate:4});
 const results=[];
 for(const hash of ['#/graph','#/graph?paper=2501.00000','#/graph?paper=2501.00000&hops=2']) {
  const oldCanvas=await page.locator('#citationCanvas').count() ? await page.locator('#citationCanvas').elementHandle() : null;
  await page.evaluate(hash=>{window.__graphStart=performance.now();location.hash=hash;},hash);
  if(oldCanvas)await oldCanvas.waitForElementState('hidden');
  await page.waitForFunction(()=>document.querySelector('#citationCanvas')?.dataset.ready==='true',null,{timeout:25000});
  results.push(await page.evaluate(async()=>{await new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)));const canvas=document.querySelector('#citationCanvas');const now=performance.now();const resources=performance.getEntriesByType('resource').filter(r=>r.startTime>=window.__graphStart&&(r.name.includes('/data/graph/')||r.name.includes('cytoscape')));const lastResponse=Math.max(window.__graphStart,...resources.map(r=>r.responseEnd));return {route:location.hash,total_ms:now-window.__graphStart,after_last_resource_ms:now-lastResponse,nodes:Number(canvas.dataset.nodes),edges:Number(canvas.dataset.edges),resources:resources.map(r=>({url:r.name,response_end_ms:r.responseEnd,transfer_bytes:r.transferSize})),status:document.querySelector('[data-graph-status]').textContent};}));
 }
 await cdp.send('Emulation.setCPUThrottlingRate',{rate:1});await cdp.detach();
 const caps=results[0].nodes<=300&&results[0].edges<=1200&&results[1].nodes<=80&&results[1].edges<=200&&results[2].nodes<=150&&results[2].edges<=400;
 await page.setViewportSize({width:390,height:844});const mobile=await page.evaluate(()=>({width:innerWidth,scrollWidth:document.documentElement.scrollWidth}));
 if(!caps||mobile.scrollWidth>mobile.width)throw new Error(JSON.stringify({results,mobile}));
 return {fixture_records:5000,fixture_edges:254949,cpu_slowdown:4,network:'loopback without bandwidth/latency throttling; layout measured after required resources',results,caps_passed:caps,ego_after_data_target_ms:2000,ego_after_data_passed:results.slice(1).every(x=>x.after_last_resource_ms<=2000),mobile};
}

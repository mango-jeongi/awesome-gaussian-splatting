async (page) => {
 await page.waitForFunction(()=>Number(document.querySelector('#statTotal')?.textContent)>0);
 const expectedRecords=Number(await page.locator('#statTotal').textContent());
 const base=new URL(page.url());base.hash='';
 await page.setViewportSize({width:1440,height:1000});
 const errors=[];page.on('pageerror',error=>errors.push(String(error)));
 const cdp=await page.context().newCDPSession(page);
 await cdp.send('Network.enable');
 await cdp.send('Network.setCacheDisabled',{cacheDisabled:true});
 await cdp.send('Network.emulateNetworkConditions',{offline:false,latency:100,downloadThroughput:10000000/8,uploadThroughput:1000000/8});
 await cdp.send('Emulation.setCPUThrottlingRate',{rate:4});
 const runs=[];
 for(let i=0;i<5;i++) {
  await cdp.send('Network.clearBrowserCache');
  await page.goto(base.href,{waitUntil:'domcontentloaded'});
  await page.waitForFunction(expected=>document.querySelectorAll('#papersContainer article').length===50 && Number(document.querySelector('#statTotal').textContent.replaceAll(',',''))===expected,expectedRecords);
  runs.push(await page.evaluate(async()=>{
   await new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)));
   return {navigation_time_origin:performance.timeOrigin,navigation_type:performance.getEntriesByType("navigation")[0].type,ready_ms:performance.now(),cards:document.querySelectorAll('#papersContainer article').length,total:document.querySelector('#statTotal').textContent,resources:performance.getEntriesByType('resource').map(x=>({url:x.name,transfer_bytes:x.transferSize,encoded_bytes:x.encodedBodySize,decoded_bytes:x.decodedBodySize}))};
  }));
 }
 await cdp.send('Network.setCacheDisabled',{cacheDisabled:false});
 await cdp.send('Network.emulateNetworkConditions',{offline:false,latency:0,downloadThroughput:-1,uploadThroughput:-1});
 await cdp.send('Emulation.setCPUThrottlingRate',{rate:1});await cdp.detach();
 if(new Set(runs.map(r=>r.navigation_time_origin)).size!==5)throw new Error('Cold runs must use distinct document navigations');
 const values=runs.map(r=>r.ready_ms).sort((a,b)=>a-b);
 return {browser:await page.context().browser().version(),catalog_records:expectedRecords,fixture:'portal at supplied session URL',viewport:{width:1440,height:1000},cpu_slowdown:4,network:{download_mbps:10,upload_mbps:1,latency_ms:100},server_encoding:'gzip for local HTML/JSON/JS; loopback',measurement:'navigation start through 50 mounted cards and two animation frames; five cache-disabled reloads',runs,median_ms:values[2],slowest_ms:values[4],median_target_ms:3000,passed:values[2]<=3000,page_errors:errors};
}

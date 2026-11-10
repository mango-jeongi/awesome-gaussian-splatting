async (page) => {
 const base=new URL(page.url());base.hash='#/catalog';await page.goto(base.href);await page.waitForFunction(()=>document.querySelectorAll('#papersContainer article').length===50);
 await page.getByRole('button',{name:'Reset',exact:true}).click();await page.setViewportSize({width:1440,height:1000});
 const expected=await page.evaluate(async()=>{const r=await fetch('./fixture-measurements.json');if(!r.ok)throw new Error('Fixture oracle missing');return r.json();});
 const total=await page.locator('#statTotal').textContent();
 const first=await page.locator('#papersContainer article h2').first().textContent();
 await page.getByRole('button',{name:'Next',exact:true}).click();const pageTwo=await page.locator('#pageStatus').textContent();
 await page.getByRole('button',{name:'Previous',exact:true}).click();const paginationRestored=first===await page.locator('#papersContainer article h2').first().textContent();
 await page.getByRole('checkbox',{name:'Code Available'}).check();const codeOnly=await page.locator('#statFiltered').textContent();
 await page.getByRole('button',{name:'Reset',exact:true}).click();
 const cdp=await page.context().newCDPSession(page);await cdp.send('Emulation.setCPUThrottlingRate',{rate:4});
 const samples=[];
 for(const year of ['2025','2026','2025','2026','2025']){
  samples.push(await page.evaluate(async year=>{
   const start=performance.now();const el=document.querySelector('#yearSelect');el.value=year;el.dispatchEvent(new Event('change',{bubbles:true}));
   await new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)));
   return {year,paint_ms:performance.now()-start,results:document.querySelector('#statFiltered').textContent,cards:document.querySelectorAll('#papersContainer article').length};
  },year));
 }
 const sortSamples=[];
 await page.evaluate(async()=>{const el=document.querySelector('#yearSelect');el.value='ALL';el.dispatchEvent(new Event('change',{bubbles:true}));await new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)));});
 for(const sort of ['title','newest','oldest','title','newest'])sortSamples.push(await page.evaluate(async sort=>{const start=performance.now();const el=document.querySelector('#sortSelect');el.value=sort;el.dispatchEvent(new Event('change',{bubbles:true}));await new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)));return {sort,paint_ms:performance.now()-start,cards:document.querySelectorAll('#papersContainer article').length};},sort));
 const sortValues=sortSamples.map(x=>x.paint_ms).sort((a,b)=>a-b);
 await cdp.send('Emulation.setCPUThrottlingRate',{rate:1});await cdp.detach();
 await page.getByRole('button',{name:'Reset',exact:true}).click();
 await page.getByRole('combobox',{name:'Sort Order'}).selectOption('title');const titles=(await page.locator('#papersContainer article h2').allTextContents()).map(s=>s.trim());const ordered=titles.every((s,i)=>i===0||titles[i-1].localeCompare(s)<=0);
 await page.keyboard.press('/');const shortcut=await page.locator('#searchInput').evaluate(el=>document.activeElement===el);
 const before=await page.locator('html').getAttribute('class');await page.getByRole('button',{name:'Toggle Dark/Light Mode'}).click();const themeChanged=before!==await page.locator('html').getAttribute('class');
 await page.setViewportSize({width:390,height:844});const mobile=await page.evaluate(()=>({width:innerWidth,scrollWidth:document.documentElement.scrollWidth,cards:document.querySelectorAll('#papersContainer article').length}));
 const sorted=samples.map(x=>x.paint_ms).sort((a,b)=>a-b);
 const report={total,codeOnly,pageTwo,paginationRestored,titlesOrdered:ordered,shortcut,themeChanged,mobile,samples,sortSamples,median_sort_ms:sortValues[2],slowest_sort_ms:sortValues[4],sort_passed:sortValues[2]<=150,median_filter_ms:sorted[2],slowest_filter_ms:sorted[4],median_target_ms:150,filter_passed:sorted[2]<=150};
 if(Number(total)!==expected.fixture_records||Number(codeOnly)!==expected.code_records||samples.some(x=>Number(x.results)!==expected.year_counts[x.year])||!paginationRestored||!ordered||!shortcut||!themeChanged||mobile.scrollWidth>mobile.width)throw new Error(JSON.stringify(report));
 return report;
}

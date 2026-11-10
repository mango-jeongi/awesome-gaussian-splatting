async (page) => {
 await page.evaluate(()=>location.hash='#/paper/2501.00000');
 await page.waitForFunction(()=>document.querySelector('#paperRoute [data-relationship="citations"] h2')?.textContent==='Cited by in this corpus (4999)');
 const section=page.locator('#paperRoute [data-relationship="citations"]');const next=section.getByRole('button',{name:'Next citing papers',exact:true});
 const seen=[];let pages=0,maxMounted=0,lastPage=0;
 while(true){
  const ids=await section.locator('a').evaluateAll(links=>links.map(a=>decodeURIComponent(a.hash.slice('#/paper/'.length))));seen.push(...ids);pages++;lastPage=ids.length;maxMounted=Math.max(maxMounted,await page.locator('#paperRoute [data-relationships] a').count());
  if(await next.isDisabled())break;
  await next.click();
 }
 if(pages!==100||seen.length!==4999||new Set(seen).size!==4999||seen.includes('2501.00000')||lastPage!==49||maxMounted>100)throw new Error(JSON.stringify({pages,count:seen.length,unique:new Set(seen).size,lastPage,maxMounted}));
 await section.getByRole('button',{name:'Previous citing papers',exact:true}).click();const previousRestores=await section.locator('[role="status"]').textContent();
 await page.setViewportSize({width:390,height:844});const mobile=await page.evaluate(()=>({width:innerWidth,scrollWidth:document.documentElement.scrollWidth}));if(mobile.scrollWidth>mobile.width)throw new Error('Mobile overflow');
 return {pages,relationships_reached:seen.length,unique_targets:new Set(seen).size,last_page_links:lastPage,max_mounted_relationship_links:maxMounted,previousRestores,mobile,complete:true};
}

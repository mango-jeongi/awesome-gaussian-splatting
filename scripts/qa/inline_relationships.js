async (page) => {
 const base=new URL(page.url());base.hash='#/catalog?q=2501.00000&year=ALL&sort=newest&provider=openalex&coverage=all&code=0&category=ALL&page=1';
 await page.goto(base.href);await page.reload();
 await page.waitForFunction(()=>document.querySelector('#statFiltered')?.textContent==='1');
 const details=page.locator('details[data-paper-id="2501.00000"]');await details.locator('summary').click();
 const content=details.locator('[data-detail-content]');await content.locator('[data-relationship="citations"]').waitFor();
 const citations=content.locator('[data-relationship="citations"]');const firstCount=await content.locator('a').count();
 await citations.getByRole('button',{name:'Next citing papers',exact:true}).click();
 const pageStatus=await citations.locator('[role="status"]').textContent();const nextCount=await content.locator('a').count();
 const duplicateIds=await page.evaluate(()=>{const ids=[...document.querySelectorAll('[id]')].map(e=>e.id);return ids.length-new Set(ids).size;});
 const target=await citations.locator('a').first().getAttribute('href');await citations.locator('a').first().click();await page.waitForFunction(()=>Boolean(document.querySelector('#paperRoute h1')));
 const hiddenPagination=await page.locator('#pagination').evaluate(el=>el.hidden&&getComputedStyle(el).display==='none');
 const result={inline_initial_links:firstCount,inline_next_links:nextCount,page_status:pageStatus,duplicate_ids:duplicateIds,link_target:target,actual_route:new URL(page.url()).hash,pagination_hidden_on_detail:hiddenPagination};
 if(firstCount>100||nextCount>100||duplicateIds||!hiddenPagination||new URL(page.url()).hash!==target)throw new Error(JSON.stringify(result));return result;
}

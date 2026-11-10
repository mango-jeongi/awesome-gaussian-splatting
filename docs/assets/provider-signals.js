/* Source-separated citation presentation, usable in browser and Node fixtures. */
(function(root){
  const labels={openalex:'OpenAlex',semanticscholar:'Semantic Scholar'};
  function signal(paper,provider,payload,now=Date.now()){
    const row=payload && Object.hasOwn(payload.papers,paper.id) ? payload.papers[paper.id][provider] : null;
    const fallback=provider==='openalex' ? {citation_count:paper.citation_count,status:paper.citation_status||'unknown',fetched_at:paper.citation_fetched_at} : {};
    const value=row||fallback;
    const stamp=Date.parse(value.fetched_at||'');
    const age=(now-Date.parse(paper.published_date))/86400000;
    const ttl=provider==='openalex' ? (age<=7?1:age<=90?7:30) : 7;
    const stale=Number.isFinite(stamp) && now-stamp>=ttl*86400000;
    const count=Number.isInteger(value.citation_count) && value.citation_count>=0 ? value.citation_count : null;
    return {label:labels[provider],count,influential:provider==='semanticscholar' && Number.isInteger(value.influential_citation_count)?value.influential_citation_count:null,
      observedAt:value.fetched_at||null,status:value.status||'unknown',stale};
  }
  function compare(a,b){
    const group=x=>x.count===null?2:x.stale?1:0;
    return group(a)-group(b) || (b.count??0)-(a.count??0);
  }
  const api={signal,compare};
  if(typeof module!=='undefined')module.exports=api;
  root.ProviderSignals=api;
})(typeof window!=='undefined'?window:globalThis);

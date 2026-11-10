/* Pure projection shared by browser rendering and cross-language parity checks. */
async function projectCitationGraph({index, record, center=null, hops=1, year='ALL', category='ALL', valid=()=>true}) {
  if (hops !== 1 && hops !== 2) throw new Error('Only one or two hops are supported');
  const metadata=index.nodes;
  const compare=(a,b)=>a<b?-1:a>b?1:0;
  const eligible=id=>Object.hasOwn(metadata,id) && (year==='ALL'||String(metadata[id].year)===String(year)) && (category==='ALL'||metadata[id].categories.includes(category));
  const priority=(a,b)=>metadata[b].incoming_count-metadata[a].incoming_count || (metadata[b].global_citations||0)-(metadata[a].global_citations||0) || compare(a,b);
  const nodeCap=center?(hops===2?150:80):300, edgeCap=center?(hops===2?400:200):1200;
  let candidates,ids;
  if(center){
    if(!Object.hasOwn(metadata,center))throw new Error('Unknown or archived graph center');
    const distances=new Map([[center,0]]);let frontier=[center];
    for(let distance=1;distance<=hops;distance++){
      const rows=await Promise.all(frontier.map(record));
      if(!valid())return null;
      const next=new Set();
      for(const row of rows)for(const id of [...row.references,...row.citations])if(!distances.has(id)&&eligible(id))next.add(id);
      for(const id of next)distances.set(id,distance);
      frontier=[...next];
    }
    candidates=[...distances.keys()];
    ids=candidates.slice().sort((a,b)=>distances.get(a)-distances.get(b)||priority(a,b)).slice(0,nodeCap);
  }else{
    candidates=Object.keys(metadata).filter(eligible);
    ids=candidates.slice().sort(priority).slice(0,nodeCap);
  }
  const rows=await Promise.all(ids.map(record));if(!valid())return null;
  const selected=new Set(ids);
  const allEdges=rows.flatMap(row=>row.references.filter(id=>selected.has(id)).map(id=>({source:row.id,target:id,provider:'openalex'})));
  allEdges.sort((a,b)=>compare(a.source,b.source)||compare(a.target,b.target));
  return {nodes:rows.map(row=>row.node),edges:allEdges.slice(0,edgeCap),omitted_nodes:candidates.length-ids.length,
          omitted_edges:Math.max(0,allEdges.length-edgeCap),node_cap:nodeCap,edge_cap:edgeCap};
}
if(typeof module!=='undefined')module.exports={projectCitationGraph};
if(typeof window!=='undefined')window.projectCitationGraph=projectCitationGraph;

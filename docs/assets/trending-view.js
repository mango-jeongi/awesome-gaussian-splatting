/* Discovery scores stay source-labelled and unavailable when their snapshot expires. */
(function(root){
  function row(payload,id,provider,now=Date.now()){
    const rows=payload?.providers?.[provider]?.papers;
    let value=rows && Object.hasOwn(rows,id) ? rows[id] : {coverage:'unavailable',score:null,reason:'no_snapshot',velocity:null};
    if(!payload)return value;
    if(Array.isArray(value.velocity))value={...value,velocity:Object.fromEntries(payload.velocity_fields.map((field,index)=>[field,value.velocity[index]]))};
    if(now<Date.parse(payload.as_of))return {...value,coverage:'unavailable',score:null,reason:'future_snapshot'};
    if(now>=Date.parse(payload.valid_until))return {...value,coverage:'unavailable',score:null,reason:'snapshot_expired'};
    return value;
  }
  function compare(a,b){
    const rank={complete:0,partial:1,unavailable:2};
    return rank[a.coverage]-rank[b.coverage] || (b.score??0)-(a.score??0);
  }
  const api={row,compare};
  if(typeof module!=='undefined')module.exports=api;
  root.TrendingView=api;
})(typeof window!=='undefined'?window:globalThis);

/* Supported identifier normalization mirrors src/identity.py; arbitrary IDs stay exact. */
function routeIdentifierKey(value) {
  const original=value.trim();
  if (/^(?:doi:|https?:\/\/(?:dx\.)?doi\.org\/|10\.\d+\/)/i.test(original)) {
    let doi=original;try{doi=decodeURIComponent(doi);}catch{}
    return 'doi:'+doi.toLowerCase().replace(/^(?:https?:\/\/(?:dx\.)?doi\.org\/|doi:\s*)/i,'');
  }
  if (/^(?:arxiv:|https?:\/\/(?:export\.)?arxiv\.org\/|\d{4}\.\d{4,5}(?:v\d+)?$|[a-z-]+(?:\.[A-Z]{2})?\/\d{7})/i.test(original)) {
    return 'arxiv:'+original.toLowerCase().replace(/^https?:\/\/(?:export\.)?arxiv\.org\/(?:abs|pdf)\//,'').replace(/^arxiv:\s*/,'').replace(/\.pdf$/,'').replace(/v\d+$/,'');
  }
  if (/^(?:openalex:|https?:\/\/openalex\.org\/)?W\d+\/?$/i.test(original)) {
    return 'openalex:'+original.replace(/^openalex:/i,'').replace(/\/$/,'').split('/').pop().toUpperCase();
  }
  return original;
}
function ownAlias(aliases,id) {
  if(Object.hasOwn(aliases,id))return aliases[id];
  const key=routeIdentifierKey(id);
  return Object.hasOwn(aliases,key)?aliases[key]:id;
}
if(typeof module!=='undefined')module.exports={routeIdentifierKey,ownAlias};
if(typeof window!=='undefined')Object.assign(window,{routeIdentifierKey,ownAlias});

"use strict";
// Transport Pages : mêmes appels de l'interface, moteur Python dans cet onglet.
(() => {
  const nativeFetch=window.fetch.bind(window);
  const worker=new Worker("/engine-worker.js",{type:"module"});
  let serial=0,resolveBoot,rejectBoot;
  const ready=new Promise((resolve,reject)=>{resolveBoot=resolve;rejectBoot=reject;});
  const pending=new Map();
  const controls=[...document.querySelectorAll("button,select,input")];
  const initialDisabled=controls.map(element=>element.disabled);
  controls.forEach(element=>element.disabled=true);
  function progress(text){const label=document.getElementById("status");if(label)label.textContent=text;}
  progress("Chargement du moteur Python…");
  function fail(message){rejectBoot(new Error(message));for(const request of pending.values())request.reject(new Error(message));pending.clear();}
  worker.addEventListener("error",event=>fail(event.message||"Le moteur Python ne démarre pas."));
  worker.addEventListener("message",({data})=>{
    if(data.kind==="progress"){progress(data.message);return;}
    if(data.kind==="ready"){
      controls.forEach((element,index)=>element.disabled=initialDisabled[index]);
      resolveBoot();return;
    }
    if(data.kind==="error"){fail(data.message);return;}
    const request=pending.get(data.id);
    if(request){pending.delete(data.id);request.resolve(new Response(JSON.stringify(data.body),{
      status:data.status,headers:{"Content-Type":"application/json; charset=utf-8"}
    }));}
  });
  window.fetch=async function(resource,options={}){
    const url=new URL(resource instanceof Request?resource.url:String(resource),location.href);
    if(url.origin!==location.origin||!["/api/state","/api/action","/api/export"].includes(url.pathname)){
      return nativeFetch(resource,options);
    }
    await ready;
    return new Promise((resolve,reject)=>{
      const id=++serial;
      pending.set(id,{resolve,reject});
      worker.postMessage({id,path:url.pathname+url.search,method:options.method||"GET",body:options.body||null});
    });
  };
})();

import {loadPyodide} from "/vendor/314.0.7/pyodide.mjs";

const python=await loadPyodide({indexURL:"/vendor/314.0.7/",stdout:()=>{},stderr:()=>{}});
self.postMessage({kind:"progress",message:"Préparation de la simulation…"});
try {
  const response=await fetch("/engine.zip");
  if(!response.ok)throw Error("Les fichiers de simulation sont indisponibles.");
  python.unpackArchive(await response.arrayBuffer(),"zip",{extractDir:"/app"});
  await python.runPythonAsync(`
import os, sys, json
from pathlib import Path
from urllib.parse import urlsplit, parse_qs
os.chdir('/app')
sys.path.insert(0, '/app')
from dijkstra.visual.server import GraphController
from dijkstra.advanced.topology_io import load_topology
available={p.stem:p for p in sorted(Path('/app/data').glob('*.json'))}
controller=GraphController(load_topology(available['topologie_exemple']), available)
controller.topology_name='topologie_exemple'

def handle_browser_request(serialized):
    request=json.loads(serialized)
    url=urlsplit(request['path'])
    try:
        if request['method']=='GET' and url.path in ('/api/state','/api/export'):
            args=parse_qs(url.query)
            body=controller.snapshot(args.get('source',[None])[0],args.get('destination',[None])[0])
        elif request['method']=='POST' and url.path=='/api/action':
            controller.perform(json.loads(request.get('body') or '{}'))
            body={'ok':True}
        else:
            return json.dumps({'status':404,'body':{'error':'Ressource inconnue.'}})
        return json.dumps({'status':200,'body':body},ensure_ascii=False,allow_nan=False)
    except (ValueError, TypeError, RuntimeError) as error:
        return json.dumps({'status':400,'body':{'error':str(error)}},ensure_ascii=False)
`);
  self.postMessage({kind:"ready"});
  let queue=Promise.resolve();
  self.addEventListener("message",({data})=>{
    queue=queue.then(()=>{
      try {
        python.globals.set("browser_request",JSON.stringify(data));
        const result=JSON.parse(python.runPython("handle_browser_request(browser_request)"));
        self.postMessage({id:data.id,...result});
      } catch(error) {
        self.postMessage({id:data.id,status:500,body:{error:"Erreur de simulation : "+error.message}});
      }
    });
  });
} catch(error) {
  self.postMessage({kind:"error",message:"Chargement du moteur impossible : "+error.message});
}

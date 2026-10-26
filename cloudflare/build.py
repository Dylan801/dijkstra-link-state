"""Construit uniquement la V3 web pour Cloudflare Pages, sans changer le projet Docker."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.request import urlopen
import hashlib
import json
import shutil
import zipfile

ROOT=Path(__file__).resolve().parents[1]
HERE=Path(__file__).resolve().parent
DIST=HERE/"dist"
VERSION="314.0.7"
URL=f"https://cdn.jsdelivr.net/pyodide/v{VERSION}/full/"
CORE=["pyodide.mjs","pyodide.asm.mjs","pyodide.asm.wasm","python_stdlib.zip","pyodide-lock.json"]
LOCK=HERE/"runtime-lock.json"
CACHE=HERE/".runtime-cache"/VERSION

def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def download(name: str) -> tuple[str, bytes]:
    cache=CACHE/name
    if cache.exists():
        data=cache.read_bytes()
    else:
        with urlopen(URL+name,timeout=120) as response:
            data=response.read()
        cache.parent.mkdir(parents=True,exist_ok=True)
        cache.write_bytes(data)
    if LOCK.exists():
        expected=json.loads(LOCK.read_text())["files"][name]["sha256"]
        if sha(data)!=expected:
            raise ValueError(f"Empreinte du moteur Python incorrecte : {name}")
    return name,data

def build() -> None:
    DIST.mkdir(parents=True,exist_ok=True)
    static=ROOT/"dijkstra/visual/static"
    for name in ("app.js","style.css"):
        shutil.copyfile(static/name,DIST/name)
    html=(static/"index.html").read_text(encoding="utf-8")
    html=html.replace('<script defer src="/app.js"></script>',
        '<script defer src="/bridge.js"></script><script defer src="/app.js"></script>')
    (DIST/"index.html").write_text(html,encoding="utf-8")
    for name in ("bridge.js","engine-worker.js","_headers"):
        shutil.copyfile(HERE/name,DIST/name)
    with zipfile.ZipFile(DIST/"engine.zip","w",compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted((ROOT/"dijkstra").rglob("*.py")):
            if path.name in {"v1.py","v2.py","v3.py"}:
                continue
            info=zipfile.ZipInfo(path.relative_to(ROOT).as_posix(),date_time=(1980,1,1,0,0,0))
            info.compress_type=zipfile.ZIP_DEFLATED
            archive.writestr(info,path.read_bytes())
        for path in sorted((ROOT/"data").glob("*.json")):
            info=zipfile.ZipInfo(path.relative_to(ROOT).as_posix(),date_time=(1980,1,1,0,0,0))
            info.compress_type=zipfile.ZIP_DEFLATED
            archive.writestr(info,path.read_bytes())
    vendor=DIST/"vendor"/VERSION
    vendor.mkdir(parents=True,exist_ok=True)
    with ThreadPoolExecutor(max_workers=5) as pool:
        downloaded=dict(pool.map(download,CORE))
    for name,data in downloaded.items():
        (vendor/name).write_bytes(data)
        print(f"{name} : {len(data):,} octets",flush=True)
    if not LOCK.exists():
        LOCK.write_text(json.dumps({"version":VERSION,"url":URL,"files":{
            name:{"sha256":sha(data),"bytes":len(data)} for name,data in downloaded.items()
        }},indent=2)+"\n",encoding="utf-8")
    # Licences des moteurs redistribués, vérifiées elles aussi par empreinte.
    licenses=json.loads((HERE/"licenses-lock.json").read_text())
    for name,metadata in licenses.items():
        cached=CACHE/name
        if cached.exists():
            data=cached.read_bytes()
        else:
            with urlopen(metadata["url"],timeout=60) as response:
                data=response.read()
            cached.write_bytes(data)
        if sha(data)!=metadata["sha256"]:
            raise ValueError(f"Licence du moteur incorrecte : {name}")
        (vendor/name).write_bytes(data)
    if any(path.stat().st_size>25*1024*1024 for path in DIST.rglob("*") if path.is_file()):
        raise ValueError("Un fichier dépasse la limite de 25 Mio de Cloudflare Pages.")
    print(f"Site prêt dans {DIST}",flush=True)

if __name__=="__main__":
    build()

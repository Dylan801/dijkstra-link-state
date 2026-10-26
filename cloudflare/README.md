# Publication de la V3 sur Cloudflare Pages

Site public : https://dijkstra-link-state.pages.dev/

Projet Cloudflare : `dijkstra-link-state`, publication initiale par téléversement direct.
Les mises à jour du dépôt ne déclenchent donc pas automatiquement un déploiement.

Cette branche ajoute une distribution web autonome. La version Docker et les
modules Python d'origine ne sont pas modifiés.

Le même moteur Python s'exécute dans le navigateur grâce à Pyodide/WebAssembly.
Chaque onglet possède sa propre simulation. Aucune instance Docker ni machine
locale ne doit rester allumée. Le premier chargement télécharge le moteur Python ;
les visites suivantes bénéficient du cache du navigateur.

## Construire le site

```bash
python3 cloudflare/build.py
```

Le résultat est dans `cloudflare/dist/`. Le runtime est figé en version 314.0.7,
avec vérification SHA-256 par `runtime-lock.json`. Les fichiers HTML/CSS/JS
de l'interface et les sources Python sont repris du projet existant.
Les points d'entrée terminal V1/V2/V3 ne font pas partie du site publié.

Pour tester : `python3 -m http.server 8081 --directory cloudflare/dist`,
puis ouvrir http://localhost:8081.

## Cloudflare Pages

- Projet : `dijkstra-link-state` (ou le nom disponible choisi dans le compte).
- Type : site statique, sans Functions.
- Construction, avec intégration Git : `python3 cloudflare/build.py`.
- Répertoire de sortie : `cloudflare/dist`.
- Branche : `cloudflare-pages`.

Un téléversement direct du contenu de `cloudflare/dist/` fonctionne aussi.
Le site est public : les ressources nécessaires à l'exécution dans le navigateur,
y compris le moteur Python, peuvent être téléchargées par les visiteurs.
Le dépôt GitHub peut rester privé.

L'état est conservé uniquement en mémoire dans chaque onglet : recharger la page
réinitialise la simulation. Les mêmes tests web du README principal s'appliquent.

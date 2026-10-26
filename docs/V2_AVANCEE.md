# V2 : analyse réseau

La V2 réutilise le cœur V1. `NetworkAnalyzer` conserve un graphe privé,
reconstruit les LSDB et recalcule toutes les tables après chaque changement.
Une opération invalide est appliquée à une copie puis rejetée sans modifier la session.
Dans une invocation CLI, les opérations suivent l'ordre : ajouts de routeurs,
ajouts de liens, changements de coûts, suppressions de liens, suppressions de routeurs.
Le menu permet un ordre arbitraire. Les modifications sont en mémoire ;
`--export` les sauvegarde dans `topology.json`.

```powershell
python -m dijkstra.v2 --topology data/topologie_exemple.json
python -m dijkstra.v2 --command routers
python -m dijkstra.v2 --command lsdb --source R1
python -m dijkstra.v2 --command spf --source R1
python -m dijkstra.v2 --command path --source R1 --destination R5
python -m dijkstra.v2 --command table --source R1
python -m dijkstra.v2 --command diagnose --source R1
python -m dijkstra.v2 --command topology
python -m dijkstra.v2 --update-link R1 R3 1 --command table --source R1 --export outputs/modifie
python -m dijkstra.v2 --add-router R7 --add-link R6 R7 2 --command all
python -m dijkstra.v2 --remove-link R1 R2 --remove-router R6 --command all
python -m dijkstra.v2 --command path --source R1 --destination R5 --svg outputs/topologie.svg
python -m dijkstra.v2 --interactive
python -m dijkstra.v2 --help
```

Le source implicite est le premier identifiant lexical ; `all` est la commande
par défaut. Un chemin exige `--destination`. `--topology` est disponible pour
toutes les commandes. Les fichiers JSON acceptent un BOM UTF-8 et rejettent
clés dupliquées, clés inattendues, JSON incorrect, liaisons dupliquées et voisins inconnus.

Exports : `topology.json`, `lsdb.json`, `distances.json`, `spf.json`, `routing.csv`.
Le dossier est créé automatiquement. INF devient `null` en JSON et `INF` en CSV.
Les décimaux sont exportés comme nombres lorsque la représentation les conserve ;
sinon une chaîne décimale exacte protège la précision. CSV utilise un BOM UTF-8.
Les exports écrasent les résultats homonymes ; choisir un nouveau dossier pour
conserver un état antérieur. Une erreur d'écriture peut laisser des exports partiels.

Les diagnostics calculent les composantes par parcours et les ponts par Tarjan
itératif. Un pont augmente le nombre de composantes si on le retire.
Les statistiques distinguent sommets du chemin, intermédiaires et sauts.
Les mesures `perf_counter` concernent SPF, sans garantie de temps réel.
Le SVG est généré sans dépendance et se lit dans un navigateur ; la disposition
circulaire peut superposer des étiquettes sur de grands graphes.

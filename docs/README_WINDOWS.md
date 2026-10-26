# Dijkstra et routage Link-State — projet ESIEA

Projet Python 3.11+ d'algorithmique réseau : calcul des plus courts chemins,
construction d'arbres SPF et de tables de routage, puis simulation pédagogique
de diffusion des états de liens. Les trois versions sont exécutables séparément.
Le calcul Dijkstra est écrit explicitement une seule fois, avec `heapq`.
Aucune dépendance externe ni bibliothèque de calcul de chemins.

## Démarrage sous Windows / PowerShell

```powershell
Set-Location 'C:\Users\dydys\Desktop\ESIEA\4A\S7\Reseau\Projet\Djikstra'
python --version
python -m dijkstra.v1
python -m dijkstra.v2 --topology data/topologie_exemple.json
python -m dijkstra.v3 --demo
python -m unittest discover -s tests -v
```

Python 3.11 ou supérieur doit être disponible. Aucun `pip install` n'est requis.
Si seul le lanceur Windows est installé, remplacer `python` par `py -3`.
Un environnement virtuel est facultatif : `python -m venv .venv`, puis utiliser
`.\.venv\Scripts\python.exe` dans les commandes ci-dessus.

Sur le poste de réalisation, la commande `python` pointe vers un alias Windows
inactif. Le lanceur fourni cherche un Python compatible, puis le runtime Codex :

```powershell
.\run.ps1 -Version V1
.\run.ps1 -Version V2
.\run.ps1 -Version V3 -Arguments @('--demo')
.\run.ps1 -Version Tests
.\run.ps1 -Version V2 -Arguments @('--command', 'path', '--source', 'R1', '--destination', 'R5')
```

Le lanceur place le terminal dans le dossier du projet, encode les sorties Python
en UTF-8 et propage le code de retour. Il n'installe rien et ne modifie pas le PATH.
Il fonctionne aussi après déplacement du dossier si un Python compatible est installé.
Sur ce poste, Windows PowerShell 5.1 bloque par défaut les scripts. Les commandes
suivantes autorisent uniquement le processus lancé, sans modifier la stratégie permanente :

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\run.ps1 -Version V1
powershell -NoProfile -ExecutionPolicy Bypass -File .\run.ps1 -Version V2
powershell -NoProfile -ExecutionPolicy Bypass -File .\run.ps1 -Version V3 -Arguments --demo
powershell -NoProfile -ExecutionPolicy Bypass -File .\run.ps1 -Version Tests
```

On peut également utiliser le chemin complet de l'interpréteur Python.
Les données par défaut sont relatives à la racine : lancer les modules depuis ce dossier.

## Versions et exemples

| Version | Fonctionnalités | Limites |
| --- | --- | --- |
| V1 | Liste d'adjacence symétrique, LSDB privées complètes, SPF depuis chaque source, prédécesseurs, chemins, arbres, tables et destinations inaccessibles | Topologie de référence intégrée, un seul chemin déterministe |
| V2 | V1 réutilisée, JSON strict, CLI et menu, modifications avec recalcul global, exports, composantes et ponts, statistiques, SVG | Simulation statique, mise à jour immédiate globale |
| V3 | LSDB locales, LSA séquencées, flooding FIFO, événements, reconvergence, pannes/restaurations/coûts/isolement, partitions, ECMP, quatre scénarios, comparaisons et exports | Simulateur pédagogique, pas de protocole OSPF réel ni de paquets IP |

### V1

`python -m dijkstra.v1` affiche pour **chacun des six routeurs** sa LSDB,
son arbre SPF, ses distances, prédécesseurs, chemins et table finale.
Depuis R1 : R2 coûte 2, R3 coûte 3, R4 coûte 4, R5 coûte 5, R6 est inaccessible.
Le Next Hop de R5 est R2 ; son prédécesseur est R4.

### V2

```powershell
python -m dijkstra.v2 --command path --source R1 --destination R5
python -m dijkstra.v2 --command table --source R1
python -m dijkstra.v2 --command diagnose --source R1
python -m dijkstra.v2 --command spf --source R1 --destination R5 --svg outputs/topologie.svg
python -m dijkstra.v2 --update-link R1 R3 1 --command table --source R1 --export outputs/modifie
python -m dijkstra.v2 --interactive
python -m dijkstra.v2 --help
```

Commandes disponibles : `all` (défaut), `routers`, `lsdb`, `spf`, `path`,
`table`, `diagnose`, `topology`. Le menu permet aussi l'ajout/suppression de
routeurs et de liaisons. Les exports créent le dossier indiqué et contiennent
la topologie, toutes les LSDB, les distances, les SPF complets et un CSV de tables.
Le SVG distingue source, arbre et chemin. Voir [V2](V2_AVANCEE.md) pour
la totalité des options et l'ordre des modifications CLI.

### V3

```powershell
python -m dijkstra.v3 --demo --export outputs/demos
python -m dijkstra.v3 --scenario scenarios/panne_liaison.json
python -m dijkstra.v3 --scenario scenarios/partition_reconnexion.json
python -m dijkstra.v3 --steps 1 --lsdb --journal
python -m dijkstra.v3 --fail R1 R2 --journal --export outputs/panne
python -m dijkstra.v3 --interactive
python -m dijkstra.v3 --help
```

Les quatre scénarios montrent : A réseau stable ; B panne et chemin alternatif ;
C réduction d'un coût ; D partition, changement distant et reconnexion.
Le menu démarre avant propagation et permet d'observer chaque livraison,
de lancer la convergence, de modifier les liens, de comparer les tables et
d'exporter le journal. `--restore A B COUT` restaure un lien absent.
Voir [V3](V3_SIMULATION.md) pour les conditions exactes de convergence.

## Architecture

```text
Djikstra/
├── README.md, pyproject.toml, run.ps1, .gitignore
├── dijkstra/
│   ├── __init__.py, examples.py, display.py
│   ├── v1.py, v2.py, v3.py
│   ├── core/        graph.py, lsdb.py, models.py, spf.py, routing.py
│   ├── advanced/    topology_io.py, service.py, diagnostics.py, exports.py, visualization.py
│   └── simulation/  lsa.py, router.py, events.py, simulator.py, scenarios.py
├── data/            cinq topologies JSON
├── scenarios/       quatre scénarios JSON
├── tests/           tests graphe, LSDB, SPF, routage, oracle exhaustif, V2 et V3
├── docs/            guides V1/V2/V3, architecture, explication, préparation de soutenance
└── outputs/         résultats générés, graphiques et rapport de validation
```

Les sous-packages possèdent leur `__init__.py`. `core` n'importe ni `advanced`
ni `simulation` : la V1 reste indépendante. La V2 produit des instantanés
complets ; la V3 assemble la topologie uniquement à partir des annonces reçues.
Les coûts sont des entiers ou flottants strictement positifs et finis. Les
distances utilisent l'arithmétique rationnelle exacte sur leur représentation
décimale pour traiter correctement les égalités. Les identifiants acceptent
lettres, chiffres, `_`, `.` et `-`, sans espaces. Les liens sont non orientés,
symétriques, sans doublons ni boucles.

## Tests et validation

```powershell
python -m unittest discover -s tests -v
```

La suite couvre les résultats de référence exacts, copies LSDB, coûts invalides,
isolement, égalités, décimaux, tas périmé, prédécesseurs, chemins, Next Hops,
modifications, schémas JSON, exports, diagnostics, CLI/menu, LSA obsolètes,
ECMP, partition/reconnexion et messages en transit pendant une panne.
Un oracle indépendant énumère tous les chemins simples de petits graphes
aléatoires ; aucun algorithme de chemin prédéfini n'est utilisé dans les tests.
Les tests V1 sont conservés dans la suite complète pour détecter les régressions.
Le compte rendu des exécutions réelles figure dans `outputs/VALIDATION.md`.

## Documentation et soutenance

- [V1 académique](V1_ACADEMIQUE.md)
- [V2 avancée](V2_AVANCEE.md)
- [V3 simulation](V3_SIMULATION.md)
- [Architecture et complexités](ARCHITECTURE.md)
- [Dijkstra expliqué étape par étape](EXPLICATION_DIJKSTRA.md)
- [Préparation de soutenance](SOUTENANCE.md)

Les durées SPF mesurées sont indicatives, sans garantie de temps réel.
Les graphes sont limités par la mémoire disponible, pas par une liste fixe de routeurs.
Les exports remplacent les fichiers homonymes ; choisir un dossier distinct
pour conserver une exécution. Les annonces V3 ne vieillissent pas : leur
conservation après partition est documentée et testée. Le journal complet et
les instantanés de tables peuvent devenir volumineux. La disposition SVG est
circulaire ; les grands réseaux peuvent nécessiter un autre outil de dessin.

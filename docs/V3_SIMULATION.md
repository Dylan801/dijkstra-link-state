# V3 : simulation Link-State

```powershell
python -m dijkstra.v3 --demo
python -m dijkstra.v3 --scenario scenarios/panne_liaison.json
python -m dijkstra.v3 --interactive
python -m dijkstra.v3 --steps 1 --lsdb --journal
python -m dijkstra.v3 --steps 2 --until-convergence
python -m dijkstra.v3 --fail R1 R2 --journal --export outputs/panne
python -m dijkstra.v3 --isolate R4 --export outputs/isolement
python -m dijkstra.v3 --cost R1 R3 1 --lsdb
python -m dijkstra.v3 --help
```

`--topology` choisit la topologie initiale. Sans menu ni `--steps`, la CLI
converge d'abord, applique les changements, puis reconverge.
Avec `--steps`, la CLI démarre à connaissance locale et n'exécute que ce nombre
de livraisons ; `--until-convergence` termine ensuite la diffusion.
Le menu conserve l'état et propose voisins, annonces, livraison unique,
convergence, panne, restauration, coût, isolement, tables, journal,
comparaison, export et réinitialisation sur la topologie physique actuelle.
Un changement interactif ne converge pas implicitement.
Les options de mutation suivent l'ordre panne, restauration, coût, isolement.
`--restore A B COUT` nécessite que la liaison soit absente à cet instant.
Pour montrer une restauration CLI :

```powershell
python -m dijkstra.v3 --fail R1 R2 --restore R1 R2 1 --journal
python -m dijkstra.v3 --demo --export outputs/demos
python -m dijkstra.v3 --scenario scenarios/partition_reconnexion.json
```

## Connaissance et diffusion

Chaque routeur émet sa seule annonce initiale : identité, voisins, coûts,
séquence 1, identifiant `(origine, séquence)`. Ses LSDB et tables sont privées.
Le moteur utilise uniquement la topologie physique pour livrer aux voisins.
Le SPF reçoit uniquement le graphe reconstitué à partir des LSA locales.
Une destination absente de la LSDB est inconnue : `route_to()` retourne
INF et aucun saut ; elle n'est pas ajoutée artificiellement à la table.
Les voisins mentionnés dans des annonces peuvent déjà apparaître dans la LSDB,
mais une liaison utilisable exige des annonces réciproques de coût identique.

Une étape retire une livraison FIFO. Une annonce de séquence supérieure
remplace la version connue et est transmise aux voisins sauf l'expéditeur.
Une séquence égale ou inférieure est rejetée ; cette suppression des doublons
empêche une diffusion infinie. SPF et ECMP sont recalculés après chaque mise à jour.
Il peut donc exister des routes transitoires avant convergence.
Les livraisons portent une génération de liaison : une rupture puis restauration
invalide les messages qui avaient été envoyés sur l'ancienne liaison.

## Conditions précises de convergence

La file doit être vide. Dans chaque composante physique, chaque routeur doit
connaître la dernière LSA de chaque origine de cette composante, et les
destinations atteignables de sa table doivent correspondre à cette composante.
Le moteur vérifie ces conditions comme observateur sans alimenter le SPF avec
des connaissances globales. Si une borne d'étapes interrompt la diffusion,
`run_until_convergence()` échoue explicitement plutôt que d'annoncer une convergence.

Les annonces apprises avant une partition restent dans les LSDB (pas de vieillissement).
Les versions des routeurs d'une autre composante peuvent donc rester différentes.
Les annonces des extrémités locales coupées invalident les anciennes liaisons ;
les routes devenues inaccessibles disparaissent comme routes valides, mais leurs
destinations restent visibles avec INF. Deux composantes n'échangent aucune LSA.
Lors d'une nouvelle adjacency, les deux extrémités échangent leur base complète.
Cette resynchronisation permet de réunir aussi deux composantes initialement séparées.

## ECMP

Le Dijkstra V1 reste inchangé et conserve un chemin déterministe unique.
La V3 prend ses distances, puis propage les ensembles de premiers sauts sur
les arêtes tendues `d[u] + coût(u,v) == d[v]`, dans l'ordre croissant des distances.
Les coûts positifs rendent ce graphe acyclique. Les chemins qui fusionnent
conservent tous les premiers sauts valides. Les égalités décimales sont exactes.
Le chemin affiché reste le chemin témoin V1 ; chaque Next Hop supplémentaire
correspond à un autre chemin minimal, pas nécessairement au chemin témoin affiché.

## Scénarios et journal

A : diffusion stable sur le réseau de référence, avec R6 isolé.
B : rupture R1–R2 sur le losange ECMP, route R1–R3–R4 conservée.
C : réduction R1–R3 de 5 à 1, changement du meilleur chemin.
D : rupture du pont B–C, changement de coût dans la partition distante,
puis restauration et resynchronisation des deux composantes.

Les fichiers scénario ont `name`, `topology` (relative au fichier), `actions`.
Actions : `run`, `step` avec `count`, `fail`, `restore`, `cost` et `isolate`.
Les liens prennent `source` et `target`, les changements/ajouts `cost`.
Le journal est indexé, chronologique, daté en étapes simulées et exporté
dans `events.json`. `local_lsdb.json`, `routing.json`, `convergence.json`
accompagnent cet export. Les mesures SPF sont les seules valeurs non déterministes.

## Écarts avec OSPF réel

Ce simulateur ne produit aucun paquet IP et n'installe aucune route système.
Il ne modélise ni Hello, machines d'états d'adjacence détaillées, acquittements,
retransmissions temporisées, pertes aléatoires, vieillissement/MaxAge,
authentification, zones, DR/BDR, types multiples de LSA, préfixes IP,
routeurs externes ni métriques spécifiques d'interfaces. Une annonce de même
séquence et contenu différent est également rejetée ; aucun traitement de
conflit, de checksum ou de bouclage de séquence n'est simulé.
La restauration échange des bases complètes dans un mécanisme pédagogique
plus simple que l'échange OSPF. La mémoire conserve le journal complet.

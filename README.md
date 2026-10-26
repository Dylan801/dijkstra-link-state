# Dijkstra et routage Link-State

Projet de réseau en Python, utilisable avec Docker sans installer Python.
Le programme s'utilise dans un terminal : il n'y a pas de page web à ouvrir.

| Version | Ce que l'on teste |
| --- | --- |
| **V1** | Plus courts chemins avec Dijkstra, arbres et tables de routage de tous les routeurs. |
| **V2** | Chargement JSON, calcul d'un chemin, modification de coûts, diagnostic et exports. |
| **V3** | Diffusion des annonces Link-State, pannes, ECMP, partition et reconnexion. |

## 1. Préparer le projet

Prérequis : **Docker avec Docker Compose**. Sous Windows, démarrer Docker Desktop
et activer l'intégration de votre distribution WSL dans ses paramètres.
Vérifier dans le terminal Ubuntu :

```bash
docker --version
docker compose version
```

Sur le poste où le projet a été préparé :

```bash
cd ~/dijkstra-link-state
docker compose build v1
```

Pour quelqu'un qui récupère le dépôt pour la première fois (accès GitHub privé nécessaire) :

```bash
git clone https://github.com/Dylan801/dijkstra-link-state.git
cd dijkstra-link-state
mkdir -p outputs
docker compose build v1
```

Une seule image est utilisée par les quatre services. La première construction
peut télécharger l'image Python. Après modification du code, refaire la commande
`docker compose build v1`.

## 2. Lancer chaque version

```bash
# V1 : affiche les résultats de tous les routeurs
docker compose run --rm v1

# V2 : analyse la topologie d'exemple
docker compose run --rm v2

# V3 : exécute les quatre démonstrations
docker compose run --rm v3
```

Le programme termine après l'affichage. `--rm` supprime le conteneur de cette
exécution ; les résultats enregistrés dans `outputs/` restent sur votre machine.

## 3. Tester la V2

Pour ajouter des options, répéter le module `dijkstra.v2` après le nom du service :

```bash
# Chercher le chemin entre R1 et R5
docker compose run --rm v2 dijkstra.v2 --command path --source R1 --destination R5

# Afficher la table de routage de R1
docker compose run --rm v2 dijkstra.v2 --command table --source R1

# Simuler une réduction de coût et observer la nouvelle table
docker compose run --rm v2 dijkstra.v2 --update-link R1 R3 1 --command table --source R1

# Utiliser le menu interactif (0 pour quitter)
docker compose run --rm v2 dijkstra.v2 --interactive

# Exporter les résultats et dessiner la topologie
docker compose run --rm v2 dijkstra.v2 --command path --source R1 --destination R5 --export outputs/v2 --svg outputs/v2/topologie.svg
```

Résultat attendu sans modification : `R1 -> R2 -> R4 -> R5`, coût **5**.
R6 est isolé et doit apparaître comme inaccessible. Les exports se trouvent
dans `outputs/v2/` ; ouvrir `topologie.svg` dans un navigateur pour voir le graphe.
Vous pouvez modifier ou ajouter un JSON dans `data/` sans reconstruire l'image,
puis le charger avec `--topology data/nom_du_fichier.json`.

## 4. Tester la V3

```bash
# Voir le basculement après la rupture d'une liaison
docker compose run --rm v3 dijkstra.v3 --scenario scenarios/panne_liaison.json

# Voir une partition puis une reconnexion
docker compose run --rm v3 dijkstra.v3 --scenario scenarios/partition_reconnexion.json

# Observer une seule étape de diffusion et les LSDB locales
docker compose run --rm v3 dijkstra.v3 --steps 1 --lsdb --journal

# Piloter manuellement les étapes et les pannes (0 pour quitter)
docker compose run --rm v3 dijkstra.v3 --interactive

# Conserver les journaux des quatre démonstrations
docker compose run --rm v3 dijkstra.v3 --demo --export outputs/demos
```

Les scénarios montrent A : réseau stable, B : panne avec chemin alternatif,
C : réduction d'un coût, D : partition puis reconnexion.
Dans le scénario de panne, R1 rejoint R4 via R3. Dans le scénario de partition,
A ne peut plus joindre D après la coupure ; la route revient après reconnexion.
La V3 est un simulateur pédagogique : aucun paquet réseau réel n'est envoyé.

## 5. Exécuter les tests automatiques

```bash
docker compose run --rm tests
```

La suite doit se terminer par **`Ran 42 tests`** puis **`OK`**.
Un échec fait retourner un code non nul. Les tests couvrent les chemins,
les premiers sauts, les exports, les annonces, les pannes et la reconvergence.

## Aide et problèmes courants

```bash
docker compose run --rm v2 dijkstra.v2 --help
docker compose run --rm v3 dijkstra.v3 --help
```

- **Docker ne répond pas** : démarrer Docker Desktop et vérifier son intégration WSL.
- **Permission refusée dans outputs/** : utiliser votre UID/GID dans le terminal WSL :
  `export LOCAL_UID=$(id -u) LOCAL_GID=$(id -g)`, puis relancer la commande.
- **Version du code ancienne** : refaire `docker compose build v1`.
- **Aucun serveur dans le navigateur** : c'est normal, toutes les versions sont des programmes en terminal.

Sans Docker, depuis la racine avec Python 3.11+ : `python3 -m dijkstra.v1`,
`python3 -m dijkstra.v2`, `python3 -m dijkstra.v3 --demo` ou
`python3 -m unittest discover -s tests -v`.

Les détails pédagogiques et les autres options se trouvent dans [docs/](docs/).
La construction et les tests Docker sont également vérifiés par GitHub Actions.

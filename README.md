# Dijkstra — exécution locale avec Docker

Ce dépôt contient uniquement ce qu'il faut pour lancer le projet : Docker,
le programme, ses topologies et ses scénarios. Les versions V1, V2 et V3
(dont la V3 graphique) sont conservées telles quelles.

## Démarrer

Prérequis : **Docker et Docker Compose**. Sous Windows, démarrer Docker Desktop
avec l'intégration de votre distribution WSL activée. Aucun Python à installer.

```bash
git clone https://github.com/Dylan801/dijkstra-link-state.git
cd dijkstra-link-state
docker compose up --build
```

Ouvrir **http://localhost:8080**. Le dépôt étant privé, le clonage nécessite
un compte GitHub autorisé. La première construction peut télécharger l'image
Python, dont la version et l'empreinte sont fixées dans le Dockerfile.

Dans la V3 graphique, cliquer sur **Converger**, puis sélectionner les routeurs.
Le graphe affiche les liaisons, leurs coûts et les interfaces fictives.
Vous pouvez couper/rétablir un lien, modifier son coût et relancer la convergence.

Pour démarrer en arrière-plan : `docker compose up -d --build`.
Pour arrêter : `docker compose down` (ou `Ctrl+C` au premier plan).
La simulation est en mémoire : un redémarrage repart de la topologie initiale.

## Lancer les versions en terminal

Après la construction de l'image ci-dessus :

```bash
# V1 : tous les calculs Dijkstra et les tables de routage
docker compose run --rm v1

# V2 : analyse de la topologie d'exemple
docker compose run --rm v2

# V3 : les quatre démonstrations Link-State en terminal
docker compose run --rm v3
```

## Essayer quelques fonctions

```bash
# Chemin attendu : R1 -> R2 -> R4 -> R5, coût 5
docker compose run --rm v2 dijkstra.v2 --command path --source R1 --destination R5

# Menu V2 (0 pour quitter)
docker compose run --rm v2 dijkstra.v2 --interactive

# Panne de liaison en V3
docker compose run --rm v3 dijkstra.v3 --scenario scenarios/panne_liaison.json

# Exporter les résultats et une image SVG
docker compose run --rm v2 dijkstra.v2 --command path --source R1 --destination R5 --export outputs/v2 --svg outputs/v2/topologie.svg
```

Les fichiers exportés restent dans `outputs/` sur votre machine.
`data/` et `scenarios/` sont montés en lecture seule dans les conteneurs :
vous pouvez adapter ces fichiers sur votre machine sans reconstruire l'image.
Pour charger une autre topologie : ajouter `--topology data/nom.json` à la commande V2 ou V3.
Les autres options sont accessibles avec `docker compose run --rm v2 dijkstra.v2 --help`
ou `docker compose run --rm v3 dijkstra.v3 --help`.

## Si nécessaire

- Port 8080 occupé : `WEB_PORT=8081 docker compose up --build`, puis ouvrir http://localhost:8081.
- Sous Linux/WSL, en cas de droits insuffisants dans `outputs/`, exécuter
  `export LOCAL_UID=$(id -u) LOCAL_GID=$(id -g)` avant les commandes Docker.
- Après une mise à jour du dépôt : `git pull`, puis `docker compose up --build`.

Le service graphique est le seul démarré par défaut. Les commandes terminal
s'exécutent à la demande. Aucun service distant, compte applicatif ou secret
n'est nécessaire pour utiliser le programme après le clonage.

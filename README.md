# Dijkstra — lancer et tester le projet

**5 tests simples, environ 10 minutes.** V1 et V2 se testent dans le terminal ;
les pannes et la simulation V3 se testent dans le navigateur.

## 1. Installer et démarrer

Prérequis : **Docker et Docker Compose**. Sous Windows, démarrer Docker Desktop
et utiliser un terminal Ubuntu/WSL. Aucun Python à installer.
Le compte GitHub utilisé doit avoir accès à ce dépôt privé.

```bash
git clone https://github.com/Dylan801/dijkstra-link-state.git
cd dijkstra-link-state
docker compose up -d --build
```

Ouvrir **http://localhost:8080**. Garder le terminal ouvert pour les deux premiers tests.
La première construction peut prendre quelques minutes.

Déjà installé ? Dans le dossier du projet : `git pull`, puis `docker compose up -d --build`.

## 2. Vérifier le fonctionnement

### Test 1 — V1 : calcul des routes

Dans le terminal :

```bash
docker compose run --rm v1
```

Regarder uniquement les résultats de **R1**, affichés en premier :

- Vers **R5** : chemin **R1 → R2 → R4 → R5**, coût **5**, Next Hop **R2**.
- Vers **R6** : **INF / Inaccessible**, car ce routeur est isolé.

### Test 2 — V2 : modifier un coût

Copier ces deux commandes, l'une après l'autre :

```bash
docker compose run --rm v2 dijkstra.v2 --command path --source R1 --destination R3
docker compose run --rm v2 dijkstra.v2 --update-link R1 R3 1 --command path --source R1 --destination R3
```

**Attendu :** la première affiche **R1 → R2 → R3, coût 3**.
La seconde affiche **R1 → R3, coût 1**.
Ces commandes sont indépendantes de la simulation ouverte dans le navigateur.

**Avant les tests web 3 à 5**, lancer le conteneur depuis le dossier du projet :

```bash
docker compose up --build v3-web
```

Ouvrir **http://localhost:8080** et garder ce terminal ouvert pendant les tests.
Pour arrêter ce lancement au premier plan, appuyer sur **Ctrl+C** dans ce terminal.

### Test 3 — V3 web : apprendre la topologie

Dans la page web :

1. Choisir **Réseau de référence**, cliquer sur **Réinitialiser** et garder **Source R1 / Destination R5**.
2. Ouvrir l'onglet **LSDB** : seule l'annonce de **R1** est présente.
3. Cliquer sur **Converger**.

**Attendu :** la LSDB contient maintenant les annonces de **R1 à R5**.
Le chemin affiché est **R1 → R2 → R4 → R5**, coût **5**. R6 reste isolé.

### Test 4 — V3 web : panne et chemin alternatif

1. Choisir **Losange ECMP**, puis **Source R1 / Destination R4**. Cliquer sur **Converger**.
   **Attendu :** coût **2**, premiers sauts **R2 et R3** (deux chemins de même coût).
2. Dans **Modifier une liaison**, choisir **R1 ↔ R2**. Cliquer sur **Couper la liaison**, puis **Converger**.
   **Attendu :** le lien est en pointillés rouges. Le coût reste **2**, avec **R3 comme seul premier saut**.
3. Cliquer sur **Rétablir la liaison**, puis **Converger**.
   **Attendu :** les premiers sauts **R2 et R3** sont à nouveau disponibles, au coût **2**.

### Test 5 — V3 web : partition et reconnexion

1. Choisir **Partition & reconnexion**, puis **Source A / Destination D**. Cliquer sur **Converger**.
   **Attendu :** chemin **A → B → C → D**, coût **3**.
2. Dans **Modifier une liaison**, choisir **B ↔ C**. Cliquer sur **Couper la liaison**, puis **Converger**.
   **Attendu :** **INF / Destination inaccessible** ; le réseau est séparé en deux parties.
3. Cliquer sur **Rétablir la liaison**, puis **Converger**.
   **Attendu :** le chemin **A → B → C → D** revient, au coût **3**.

## 3. Arrêter correctement

Dans le terminal, depuis le dossier du projet :

```bash
docker compose down
```

Le serveur web s'arrête. Les fichiers exportés dans `outputs/` sont conservés.
Au prochain démarrage, la simulation repart de son état initial.

## En cas de problème

- **La page ne s'ouvre pas :** vérifier que Docker Desktop est démarré, puis relancer `docker compose up -d --build`.
- **Port 8080 occupé :** lancer `WEB_PORT=8081 docker compose up -d --build`, puis ouvrir http://localhost:8081.
- **Droits insuffisants sur les exports sous Linux/WSL :** exécuter `export LOCAL_UID=$(id -u) LOCAL_GID=$(id -g)`, puis relancer Docker Compose.


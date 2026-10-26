# V3 graphique locale

## Lancement

```bash
docker compose up --build v3-web
```

Ouvrir http://localhost:8080. Le port est publié sur la boucle locale uniquement.
Sans Docker : `python3 -m dijkstra.v3 --web --port 8080`.
Les modes CLI et interactif de V3 restent exécutables séparément.

## Lecture du graphe

La carte montre **l'état physique**, y compris les routeurs isolés et les liens
coupés conservés en pointillés. Cela ne donne pas cette connaissance aux routeurs :
leurs tables et leurs LSDB proviennent uniquement des LSA apprises par le moteur V3.
La légende distingue chemin témoin minimal, arbre SPF, lien actif et coupure.
Le coût est inscrit au centre du lien, et une interface fictive près de chaque extrémité.
Cliquer sur un routeur le sélectionne comme source. Les listes de sélection sont
aussi utilisables au clavier, ainsi que les routeurs SVG (Tab puis Entrée/Espace).

Les noms `Gi0/N` sont affectés localement à chaque routeur, dans l'ordre déterministe
de ses liens initiaux. Les ports ne sont jamais réutilisés pendant une session.
La coupure conserve le nom des deux extrémités ; la restauration les réemploie.
Ce sont des étiquettes, pas une simulation d'adresses IP ou de configurations Cisco.

## Simulation

Au démarrage, chaque routeur n'a que sa propre annonce. Le graphe physique est
visible, mais les chemins peuvent être inaccessibles avant diffusion.
Converger vide la file et vérifie la synchronisation par composante.
Un événement traite une livraison ; Lecture auto répète cette opération avec
une pause de 450 ms. La lecture s'arrête quand il n'y a plus de livraison ou
quand l'onglet passe en arrière-plan. Le repère jaune indique la dernière LSA
traitée, sans représenter un paquet réel. Le texte du journal précise son traitement.

La table affiche tous les premiers sauts ECMP, mais le dessin vert montre le
chemin témoin déterministe du SPF. Un astérisque dans la table signale une
différence par rapport à l'état avant le dernier changement physique.
Les tableaux peuvent être transitoires pendant la diffusion.
Les changements de coût et les pannes mettent d'abord à jour les extrémités ;
l'utilisateur déclenche ensuite les étapes ou la convergence.

L'inspecteur donne les interfaces UP/DOWN et les annonces LSA locales.
Le journal visible présente les 30 derniers événements ; le moteur conserve
son historique complet en mémoire. L'export SVG inclut les noms, coûts et
couleurs de la vue actuelle ; il ne sauvegarde pas une session rejouable.

## Architecture et limites

`dijkstra.visual.server.GraphController` adapte le moteur existant sans réécrire
Dijkstra ni le flooding. Le serveur HTTP utilise la bibliothèque standard Python.
HTML, CSS, JavaScript et SVG sont locaux, sans CDN ni dépendance Python additionnelle.
Le service est destiné à une utilisation pédagogique locale, pas à un déploiement
public. Le contenu servi est limité aux trois ressources de l'interface.
Les mutations JSON sont validées et les origines étrangères rejetées.
La session est partagée entre les utilisateurs du même serveur ; un autre onglet
doit être rafraîchi pour relire l'état. L'arrêt du service efface la simulation.

Le dessin possède une disposition fixe lisible pour la référence et le losange,
et une disposition circulaire pour les autres topologies. Pour les grands réseaux,
les étiquettes peuvent se chevaucher ; sur mobile, le graphe se parcourt horizontalement.
Les commandes graphiques travaillent sur les routeurs et liaisons présents dans
la topologie chargée. Les API locales peuvent aussi rétablir un lien nouveau entre
deux routeurs existants ; de nouveaux numéros d'interface sont alors alloués.

## Vérification

```bash
docker compose run --rm -T tests
```

Les tests couvrent notamment les routes exactes, interfaces persistantes,
coupure/restauration, partition, ECMP, entrées invalides, ressources HTTP,
origines étrangères et compatibilité des options CLI.

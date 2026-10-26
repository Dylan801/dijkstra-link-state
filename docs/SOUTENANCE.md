# Préparation de soutenance

## Démonstration conseillée

1. Lancer les tests et présenter les résultats exacts du jeu de référence.
2. Lancer V1 ; dans la table R1, expliquer coût 5, prédécesseur R4,
   Next Hop R2 pour R5, et R6 inaccessible.
3. Afficher le chemin et le SVG avec V2. Modifier R1–R3 à coût 1,
   montrer le changement de route et exporter les nouveaux résultats.
4. Lancer V3 avec `--steps 1 --lsdb --journal` : montrer les connaissances
   locales, la première livraison et l'absence de connaissance globale.
5. Lancer le scénario de panne : le losange utilise le chemin restant.
6. Lancer partition/reconnexion : montrer INF après coupure et la nouvelle
   distance 4 de A vers D après le coût distant et la restauration.

## Questions possibles

**Pourquoi une liste d'adjacence ?** Elle stocke O(V+E) éléments et parcourt
uniquement les voisins, contrairement à une matrice dense en O(V²).

**Pourquoi le tas ?** Il extrait efficacement la meilleure proposition.
Une distance améliorée est réinsérée ; une ancienne proposition est ignorée.

**Pourquoi Dijkstra ne traite pas les coûts négatifs ?** Un détour futur pourrait
alors améliorer une distance déjà extraite. La preuve du choix glouton échoue.

**Pourquoi chaque LSDB est-elle une copie ?** Chaque routeur possède son état.
Une modification d'une copie ne doit pas modifier les connaissances d'un autre.

**Quelle différence entre prédécesseur et premier saut ?** Le prédécesseur aide
à reconstruire l'arbre près de la destination ; le premier saut commande
l'envoi depuis la source. Ils ne coïncident que pour certains chemins courts.

**Pourquoi la diffusion termine-t-elle ?** Une version n'est acceptée qu'une fois
par routeur ; les versions connues ou plus anciennes ne sont pas rediffusées.
Une topologie stable et une file finie permettent de vider les livraisons.

**Les LSDB sont-elles identiques après une partition ?** Les dernières annonces
des origines de chaque composante sont synchronisées dans cette composante.
Les annonces d'origines distantes peuvent être conservées et périmées.
Une partition ne transmet pas de nouvelles annonces à l'autre composante.

**Pourquoi exiger deux annonces pour un lien ?** Cela empêche une ancienne annonce
de suffire à créer un lien qu'une extrémité vient de supprimer, et évite
des coûts asymétriques pendant la propagation d'un changement.

**Comment ECMP trouve-t-il des premiers sauts au-delà de l'arbre ?** Il utilise
toutes les arêtes satisfaisant l'égalité de distance, pas uniquement les
prédécesseurs retenus. Les ensembles de premiers sauts se propagent sur ce DAG.

**Est-ce OSPF ?** C'est un modèle pédagogique des annonces, LSDB, flooding et SPF.
Il manque les mécanismes de protocole réels détaillés dans la documentation V3.

**Peut-on traiter mille routeurs ?** Le modèle n'impose pas de plafond. Le
calcul seul et les diagnostics sont raisonnables, mais toutes les LSDB,
tous les chemins, les recalculs progressifs et le journal consomment beaucoup
de mémoire. La V3 privilégie une démonstration de taille modérée.

# Architecture, choix et complexités

## Flux de données

V1 : graphe → copies LSDB → Dijkstra → résultat SPF → reconstruction → table → affichage.
V2 : JSON validé → `NetworkAnalyzer` → même cœur → diagnostics/exports/dessin.
V3 : état physique → annonces locales → file de livraisons → LSDB locales
→ graphe réciproque → même Dijkstra → ECMP → table → journal.

`NetworkGraph` encapsule l'adjacence ; ses accesseurs rendent des copies.
`LinkStateDatabase` prend une copie indépendante, même si deux routeurs ont
le même contenu. Les dataclasses décrivent les résultats et routes.
`SPFResult.tree_edges` fournit l'arbre explicitement à partir des prédécesseurs.
Les structures de résultats sont modifiables par leur propriétaire ; ne pas
les modifier pendant leur consommation. La LSA est immuable et ses voisins
forment un tuple ; le dictionnaire de LSA est privé à chaque routeur.

Le moteur FIFO ordonne toutes les livraisons. L'index du journal et le numéro
d'étape constituent le temps simulé. Une liaison a une génération pour
invalider les messages en transit quand sa connectivité change.
L'observateur vérifie la convergence avec la topologie physique ; le calcul
de routes n'accède jamais à cette topologie. La V2 peut recalculer globalement,
la V3 ne diffuse que les annonces par les adjacences physiques existantes.

## Raisons des choix

- Une implémentation SPF unique évite les divergences entre versions.
- Le tas contient `(distance, identifiant)` : extraction déterministe.
- En égalité, le premier prédécesseur est conservé, sans cycles.
- Les rationnels exacts évitent les égalités décimales approximatives et
  les débordements de sommes de coûts flottants valides. INF reste distinct.
- Le graphe V3 exige des annonces réciproques pour utiliser une liaison.
  Pendant un changement de coût, un lien peut donc être provisoirement absent.
- Après partition, les anciennes LSA sont conservées mais ne donnent pas
  de route valide à travers la liaison coupée. Un échange de bases complète
  les connaissances à la reconnexion.
- JSON strict et CSV UTF-8 avec BOM facilitent l'interopérabilité Windows.
- Le SVG ne demande aucune dépendance graphique et ne calcule aucun chemin.

## Coûts théoriques

Soient V routeurs, E liaisons non orientées ; les listes d'adjacence contiennent 2E arcs.
Le graphe occupe O(V+E). Dijkstra avec tas binaire et liste d'adjacence prend
O((V+E) log V) opérations pour un graphe simple (V ≥ 2).
La version avec entrées périmées peut conserver O(E) entrées de tas ;
distances et prédécesseurs occupent O(V), donc SPF utilise O(V+E) mémoire.
Le tri des voisins et routeurs pour le déterminisme reste dans cette borne.
Le cas V=1 est constant ; le cas vide produit zéro SPF.

`Fraction` utilise de grands entiers : les opérations arithmétiques ne sont
pas strictement constantes en nombre de bits. Les bornes ci-dessus comptent
les opérations de graphe ; des coûts très grands ou très précis les ralentissent.
L'utilisation de la bibliothèque standard `heapq` ne délègue que le tas,
aucune partie de l'algorithme de plus court chemin.

N calculs SPF coûtent O(V(V+E) log V) opérations. N copies complètes de LSDB
coûtent O(V(V+E)) en mémoire. La reconstruction d'un chemin prend O(V),
une table complète peut donc prendre O(V²) en temps et en sommets de chemins,
et toutes les tables O(V³) dans le pire cas d'une chaîne.
Les composantes et Tarjan sont O(V+E) hors tri des accesseurs ; les tris de
cette implémentation ajoutent au plus O((V+E) log V).

ECMP propage des ensembles pouvant contenir jusqu'à V premiers sauts :
O(VE + V log V) opérations hors tri des accesseurs et O(V²+E) mémoire.
Le flooding stable diffuse chaque origine sur les liens : O(VE) livraisons
dans une composante, doublons compris. SPF est recalculé à chaque annonce
acceptée pour rendre la progression visible ; le simulateur privilégie la
pédagogie plutôt que les très grandes topologies.
Le journal garde des instantanés de tables avant/après : son volume s'ajoute
à celui des LSDB et peut dominer la mémoire.

## Vérification

Les tests ne s'appuient sur aucun calculateur de chemins externe.
L'oracle énumère tous les chemins simples de cinq sommets avec une graine fixe,
puis compare distances et coût réel de chaque chemin reconstruit.
La simulation est comparée aux résultats statiques après convergence.
Les scénarios de partition changent un coût dans la composante distante
pour détecter une resynchronisation incomplète lors de la reconnexion.
Les tests CLI et menu exercent les points d'entrée, et les exports sont relus.
Les secondes de SPF dépendent de la machine ; la chronologie logique reste déterministe.

Références : [heapq](https://docs.python.org/3.11/library/heapq.html),
[fractions](https://docs.python.org/3.11/library/fractions.html),
[OSPFv2, RFC 2328](https://datatracker.ietf.org/doc/html/rfc2328).
Ces références expliquent les primitives et le protocole réel ; le code de
Dijkstra et le moteur de simulation sont implémentés dans le projet.

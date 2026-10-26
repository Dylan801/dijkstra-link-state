# V1 académique

Depuis la racine : `python -m dijkstra.v1`.
Aucune dépendance tierce. Six sources, six LSDB distinctes, six arbres et six tables.
R6 est isolé. L'affichage distingue explicitement racine, prédécesseurs,
distances, chemins, branches SPF et premier saut.

La liste d'adjacence est symétrique. Les lectures renvoient des copies.
Les LSDB prennent un instantané privé ; SPF lit exclusivement cet instantané.
Le graphe interdit les identifiants vides, espaces, doublons, boucles,
liaisons dupliquées et coûts non numériques, booléens, nuls, négatifs ou non finis.

Dijkstra initialise toutes les distances à INF et celle de la source à zéro.
Un tas extrait le minimum, les arêtes sont relaxées, les entrées périmées
sont ignorées. Une égalité conserve le premier prédécesseur découvert.
L'ordre lexical des identifiants dans le tas et des voisins rend le résultat
indépendant de l'ordre d'insertion ; ce n'est pas une promesse du chemin
lexicographiquement minimal complet. R10 précède R2 dans cet ordre.
Les coûts positifs assurent une progression stricte le long des prédécesseurs.

Les distances finies utilisent `Fraction(str(cost))` pour calculer exactement
les nombres décimaux reçus et éviter les faux écarts d'égalité et débordements.
INF est le seul flottant utilisé pour les distances inaccessibles.
Une valeur flottante calculée avant l'appel (par exemple `0.1 + 0.2`) garde
la valeur décimale de sa représentation Python : fournir `0.3` pour ce coût.

Validation : `python -m unittest discover -s tests -v`.
Les tests couvrent le résultat exact de référence, les composantes isolées,
les égalités, les décimaux, les anciennes entrées du tas, les copies LSDB,
les prédécesseurs, les premiers sauts et la reconstruction avec garde de cycle.

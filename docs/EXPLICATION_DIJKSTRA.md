# Comprendre Dijkstra et la table de routage

## Topologie, LSDB et Link-State

Un routeur connaît ses voisins directement connectés et le coût de ses liens.
Un protocole à état de liens diffuse ces descriptions pour que les routeurs
d'une même composante puissent reconstituer une carte commune.
La LSDB est cette base d'annonces ou, en V1/V2, un instantané déjà complet.
La topologie décrit les connexions ; la table de routage indique quoi faire
pour une destination. Ce sont deux structures distinctes.

En V1 et V2, la diffusion est supposée déjà réalisée : chaque source reçoit
sa copie complète. En V3, les connaissances se construisent progressivement.
SPF signifie Shortest Path First ; un calcul SPF prend une LSDB et une racine.

## Principe de Dijkstra

1. Initialiser toutes les distances à INF et les prédécesseurs à None.
2. Mettre la source à 0 et l'insérer dans un tas de priorité.
3. Extraire le couple de plus petite distance ; départager par identifiant.
4. Ignorer une entrée dont la distance n'est plus celle actuellement connue.
5. Pour chaque voisin, tester `distance[source_courante] + coût_du_lien`.
6. Si cette somme est strictement meilleure, remplacer la distance,
   noter le prédécesseur et ajouter la nouvelle proposition au tas.
7. Répéter jusqu'à épuisement du tas ; les distances encore INF sont inaccessibles.

La relaxation consiste à améliorer une estimation en passant par un sommet
dont on connaît déjà le coût. Exemple : R3 coûte provisoirement 5 depuis R1.
R2 coûte 2 et le lien R2–R3 coûte 1. Passer par R2 coûte 3 : remplacer 5 par 3
et fixer le prédécesseur de R3 à R2. L'ancienne entrée `(5, R3)` reste dans
le tas et sera ignorée à son extraction.

Avec des coûts positifs, le minimum extrait ne peut plus être amélioré par
un détour passant par des sommets de coût supérieur. Le prédécesseur a une
distance strictement inférieure à celle de son enfant : il ne peut y avoir
de cycle de prédécesseurs. Des coûts négatifs invalideraient ce raisonnement ;
le modèle impose des coûts strictement positifs et finis.

## Exemple de référence : source R1

Liaisons : R1–R2=2, R1–R3=5, R2–R3=1, R2–R4=2,
R3–R4=3, R4–R5=1, R3–R5=10. R6 est isolé.

| Extraction utile | R1 | R2 | R3 | R4 | R5 | R6 | Mise à jour |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Initialisation | 0 | INF | INF | INF | INF | INF | Source R1 |
| R1 à 0 | 0 | 2 | 5 | INF | INF | INF | Prédécesseurs de R2/R3 : R1 |
| R2 à 2 | 0 | 2 | 3 | 4 | INF | INF | R3 via R2 ; R4 via R2 |
| R3 à 3 | 0 | 2 | 3 | 4 | 13 | INF | R5 via R3 ; proposition R4=6 rejetée |
| R4 à 4 | 0 | 2 | 3 | 4 | 5 | INF | R5 via R4, meilleure proposition |
| R5 à 5 | 0 | 2 | 3 | 4 | 5 | INF | Aucun meilleur coût |

L'entrée périmée R3 à 5 est extraite avant R5 à 5 (ordre lexical) et ignorée.
L'entrée périmée R5 à 13 est également ignorée. Aucune entrée R6 n'a été insérée.

L'arbre SPF possède les arêtes R1→R2, R2→R3, R2→R4, R4→R5.
Il ne contient ni le lien R1–R3 (trop coûteux), ni une branche vers R6.
La liste des prédécesseurs fournit un arbre dirigé depuis R1 dans la topologie
non orientée ; le choix d'une racine différente donne généralement un autre arbre.

## Reconstruction et table

Pour R5, remonter les prédécesseurs : R5 ← R4 ← R2 ← R1 ; inverser la liste.
Chemin : R1 → R2 → R4 → R5. Le garde de reconstruction détecte les cycles
si la fonction reçoit une structure de prédécesseurs corrompue.
Source=destination donne `[source]`. Une chaîne terminant à None avant la
source donne un chemin vide, interprété comme inaccessible.

| Destination | Coût | Prédécesseur | Next Hop | Chemin |
| --- | --- | --- | --- | --- |
| R1 | 0 | — | Local | R1 |
| R2 | 2 | R1 | R2 | R1 → R2 |
| R3 | 3 | R2 | R2 | R1 → R2 → R3 |
| R4 | 4 | R2 | R2 | R1 → R2 → R4 |
| R5 | 5 | R4 | R2 | R1 → R2 → R4 → R5 |
| R6 | INF | — | — | Inaccessible |

Le coût est la somme des poids du chemin, pas son nombre de sauts.
Le prédécesseur est le dernier sommet avant la destination dans l'arbre.
Le Next Hop est le premier sommet après la source ; il suffit pour transmettre
un paquet au prochain routeur. Chaque routeur utilise ensuite sa propre table.
Cette simulation travaille sur des destinations routeurs, pas des préfixes IP.

## Égalités et ECMP

La V1 choisit un témoin déterministe : les voisins sont triés et une égalité
ne remplace pas le premier prédécesseur. La V3 conserve ce même calcul SPF,
puis trouve tous les premiers sauts minimaux sur les arêtes tendues.
Sur le losange R1–R2–R4 et R1–R3–R4 à coûts unitaires, R4 coûte 2 et les
Next Hops sont R2 et R3. Le partage effectif des paquets n'est pas simulé.

Pour les complexités et le coût des copies/tableaux de chemins, consulter
[ARCHITECTURE.md](ARCHITECTURE.md). Pour les partitions, annonces obsolètes
et resynchronisation, consulter [V3_SIMULATION.md](V3_SIMULATION.md).

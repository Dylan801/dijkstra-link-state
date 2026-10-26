# Validation Docker — 26 octobre 2026

- Image construite dans Ubuntu-24.04 / Docker Desktop avec Python 3.13.16.
- 16 commandes du README exécutées réellement dans Docker : codes de retour 0.
- 42 tests automatiques réussis, sans erreur ni échec.
- V1, V2 et V3 exécutées ; menus V2/V3 ouverts et quittés avec 0.
- Chemin de référence vérifié : R1 → R2 → R4 → R5, coût 5 ; R6 inaccessible.
- Exports JSON, CSV et SVG présents sur le disque WSL après suppression des conteneurs.
- Les quatre scénarios ont convergé ; les journaux appartiennent à l'utilisateur WSL.

Les sorties détaillées sont conservées localement sous `outputs/docker-verification/`
(dossier ignoré par Git). Les commandes sans terminal utilisent `-T` pour la
vérification automatisée ; dans un terminal, les exemples du README restent interactifs.
L'image Python officielle est figée par son empreinte SHA-256 dans le Dockerfile.

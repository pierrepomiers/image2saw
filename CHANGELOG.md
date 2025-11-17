# 📜 CHANGELOG

Ce fichier liste les évolutions du projet Image2Saw selon les versions publiées.  
Format inspiré de *Keep a Changelog*.

---

## [3.1.0] - 2025-11-17  
### ✨ Ajouté
- Nouvelle option `--duration-s` permettant de définir directement la **durée cible** du son (et donc de la vidéo).
- Recalcul automatique de la **taille de l'image** (`--size`) pour que la durée finale corresponde à `--duration-s` sans toucher à `--step-ms`.
- Documentation entièrement réécrite :
  - Explication détaillée de la relation *durée ↔ pixels ↔ oscillateurs*
  - Diagramme ASCII
  - Exemple complet
  - Notes techniques pour développeurs.
- Ajout d’un README V3.1 complet et d’un guide d’utilisation artistique.

### 🔧 Modifié
- Le paramètre `--step-ms` reste désormais **strictement fixe** : il n’est jamais recalculé automatiquement.
- L’image d’entrée est redimensionnée dynamiquement en fonction de la durée demandée.
- Refonte du pipeline interne pour intégrer le recalcul automatique de la taille.
- Nettoyage et clarification des logs CLI.

### 🐞 Fixé
- Ajustements mineurs sur la synchronisation audio → vidéo dans certains cas limites.
- Corrections de bords sur les valeurs minimales de taille d'image et d’oscillateurs.

---

## [3.0.0] - 2025-11-16  
### ✨ Ajouté
- Nouveau moteur audio vectorisé (NumPy + batchs).
- LUT (Look-Up Tables) pré-calculées pour les formes d’onde (`sine`, `saw`, `tri`, `square`).
- Refonte complète de l’API interne (`image2saw_pkg`) :
  - `image_proc.py`  
  - `audio.py`  
  - `video.py`  
  - `cli.py`
- Gestion propre des vidéos basées sur la durée exacte du WAV.
- README v3.0 réécrit entièrement.

### 🔧 Modifié
- Une seule base de code pour audio + vidéo, avec pipeline unifié.
- Amélioration majeure des performances CPU (gains ×5 à ×20 selon les machines).

---

## [2.9.0] - 2025-11-15  
### ✨ Ajouté
- Version audio + vidéo avec génération MP4 complète.
- Effet de **"grignotage" visuel** synchronisé à la fenêtre glissante.
- Support de formes d’onde variées.

### 🔧 Modifié
- Refactorisation complète de `image2saw.py` en vue de V3.0.
- Nettoyage de l’algorithme de zigzag.

---

## [2.8.0] - 2025-11-14  
### ✨ Ajouté
- Support vidéo initial.
- Ajout d’un effet visuel expérimental basé sur la progression de la fenêtre.

---

## [2.7.0] - 2025-11-13  
### ✨ Ajouté
- Première version stable audio.
- Mapping 1 pixel → 1 oscillateur.
- Paramètres principaux :  
  `--step-ms`, `--size`, `--fmin`, `--fmax`, `--waveform`.
- Génération du WAV complet incluant fade-in/fade-out.
- Documentation de la V2.7.

---

### Historique des versions préliminaires
Les versions antérieures à 2.7 étaient expérimentales et ne faisaient pas l'objet d'un changelog structuré.

---

# 📌 Notes  
- Le projet suit désormais une évolution plus stable depuis la V3.0.  
- Les futures versions (V3.2 et V4.0) se concentreront sur :  
  - support des formats non carrés,  
  - modes “artist presets”,  
  - intégration VST / plugin audio,  
  - version Web / WebAssembly.

---

# 📎 Liens  
- Dépôt GitHub : https://github.com/pierrepomiers/image2saw  


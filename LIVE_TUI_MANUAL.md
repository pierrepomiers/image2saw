# Image2Saw — Interface Live TUI 🎧

Ce document décrit l’interface terminal "live" (`live_tui.py`) qui permet
de tester Image2Saw en temps réel sur un petit crop de l’image.

---

## 1. Installation

### 1.1. Pré-requis Python

Assure-toi d’avoir un environnement Python 3 fonctionnel (3.9+ recommandé).

Installe les dépendances nécessaires :

```bash
pip install numpy sounddevice pillow
````

Sur macOS, si `sounddevice` se plaint de PortAudio, installe-le via Homebrew :

```bash
brew install portaudio
pip install --force-reinstall sounddevice
```

---

## 2. Lancement du mode Live TUI

Place-toi à la racine du projet `image2saw` :

```bash
cd image2saw
```

Lance le TUI sur une image :

```bash
python3 live_tui.py mon_image.png
```

Tu peux éventuellement fixer un crop initial :

```bash
python3 live_tui.py mon_image.png --crop-w 32 --crop-h 32
python3 live_tui.py mon_image.png --crop-w 32 --crop-h 32 --x 100 --y 200
```

Si tu ne précises rien, le TUI prend par défaut un **crop 16×16 centré** dans l’image.

---

## 3. Principe général

* Le programme charge l’image.
* Il extrait un **crop** (une petite fenêtre rectangulaire) dans l’image.
* Ce crop est converti en **banque de fréquences et d’amplitudes**, puis en texture sonore.
* Le résultat est joué **en boucle** (loop) en stéréo.
* Tu peux :

  * **déplacer** le crop (scanner l’image),
  * **changer les paramètres audio** (waveform, color_mode, fmin, fmax…),
  * écouter immédiatement le résultat.

Toutes les modifications (crop ou paramètres) **regénèrent entièrement** le son :
pas de traîne ni d’influence des anciens réglages.

---

## 4. Interface : les deux modes

L’interface a deux modes :

1. **Mode PARAMS** (édition des paramètres audio)
2. **Mode CROP** (déplacement + taille de la fenêtre d’image)

Tu alternes entre les deux avec la touche **TAB**.

### 4.1. Informations affichées

En haut du terminal :

* Taille de l’image : `Image: 1024x768`
* Crop actuel : `Crop: x=512, y=384, w=16, h=16`
* Mode courant : `Mode: PARAMS` ou `Mode: CROP`

Ensuite, une liste de paramètres audio issus de la CLI (version “expert”) :

```text
waveform       = saw      (saw/sine/triangle/square…)
color_mode     = grayscale  (grayscale/hsv-notes)
fmin           = 40
fmax           = 8000
step_ms        = 40
...
```

En bas :

* une **ligne d’aide** (raccourcis),
* une **ligne de description** du paramètre sélectionné,
* une **ligne de status** (succès/erreur lors du rendu audio).

---

## 5. Mode PARAMS 🎛️

C’est le mode par défaut au lancement.

### 5.1. Navigation

* **↑ / ↓** : déplacer la sélection dans la liste des paramètres

Le paramètre sélectionné est surligné (fond inversé).

### 5.2. Raccourcis de modification

Les flèches **gauche/droite** ne servent que pour :

* `waveform`
* `color_mode`
* `mono`

Pour ces 3 paramètres :

* **← / →** :

  * `waveform` : cycle dans les formes d’onde disponibles (`saw`, `sine`, `triangle`, `square`, …)
  * `color_mode` : cycle dans les modes (`grayscale`, `hsv-notes`, …)
  * `mono` : bascule `True` / `False`

À chaque changement, le son est **regénéré** et le nouveau rendu est joué en boucle.

### 5.3. Saisie manuelle (tous les paramètres)

Pour **n’importe quel paramètre** (ex : `fmin`, `fmax`, `step_ms`, `hsv_blend_gray`, etc.) :

1. Sélectionne-le avec **↑ / ↓**.

2. Appuie sur **Entrée**.

3. Un prompt apparaît en bas :

   ```text
   fmin (actuel=40): _
   ```

4. Entre la nouvelle valeur :

   * `int` : ex. `200`
   * `float` : ex. `123.45`
   * `bool` : `true/false`, `yes/no`, `1/0`
   * string (si c’est un param de type texte)

5. Valide avec **Entrée**.

Le moteur live :

* met à jour la valeur,
* reconstruit le rendu audio,
* et rejoue immédiatement la nouvelle boucle.

---

## 6. Mode CROP 🖼️

Passe en mode CROP avec la touche **TAB**.

Dans ce mode, les flèches contrôlent le rectangle de crop.

### 6.1. Déplacement du crop

* **↑ / ↓ / ← / →** : déplacer le crop pixel par pixel dans l’image.

Cela permet de **scanner le tableau de pixels** et d’entendre comment
le son change en fonction de la zone de l’image.

Chaque déplacement regenère le son en live.

### 6.2. Taille du crop

* `+` / `=` : **agrandir** le crop (w et h +1)
* `-` / `_` : **réduire** le crop (w et h -1, minimum 1×1)

Astuce :

* Un petit crop = texture plus “fine”, très locale.
* Un crop plus large = mix plus global des fréquences sur une zone.

### 6.3. Recentrage rapide

* `c` : recentre un crop **16×16** au milieu de l’image.

Pratique pour “repartir à zéro” si tu as beaucoup bougé le rectangle.

---

## 7. Raccourcis globaux

Valables dans les deux modes :

* **TAB** : alterner entre **PARAMS** et **CROP**.
* **r** : regénérer le son manuellement (au cas où tu veux forcer un refresh).
* **q** : quitter le TUI.

---

## 8. Flux audio et volume

Le moteur live (`live_core.py`) :

* utilise un **sample rate fixe de 48 kHz** (pas modifiable en live),
* reconstruit **intégralement** la fenêtre de balayage à chaque update,
* applique une **normalisation du volume** identique à celle utilisée
  pour générer les fichiers WAV (pas de surprise niveau niveau sonore),
* clippe la **durée max** du buffer à ~4 secondes pour garder un live fluide.

Résultat :

* le live doit sonner **au même niveau** que les WAV générés par Image2Saw,
* sans traîne d’anciens paramètres.

---

## 9. Conseils de jeu / workflow

Quelques idées pour explorer :

* Fixer `waveform = sine`, `color_mode = grayscale`, et jouer uniquement avec :

  * `fmin` / `fmax`
  * la position du crop
  * la taille du crop

* En `color_mode = hsv-notes` :

  * jouer sur `hsv_max_octave`,
  * déplacer le crop sur des zones de couleurs différentes (fort contraste).

* Tester des valeurs extrêmes de :

  * `step_ms` (rendu plus “haché” ou plus “continu”),
  * `voices` (texture plus dense ou plus creuse),
  * `hsv_blend_gray` (mix entre profondeur lumi / couleur).

---

## 10. Dépannage rapide

* **Pas de son / erreur PortAudio** :

  * Vérifie que ton casque / sortie audio par défaut est bien configurée.
  * Sous macOS : `brew install portaudio`, puis `pip install sounddevice`.

* **Terminal glitché après crash** :

  * Tape simplement `reset` dans le terminal, ou ferme/réouvre la fenêtre.

* **Le son est toujours trop fort** :

  * La normalisation devrait déjà être cohérente avec les WAV.
  * Si besoin, tu peux ajouter un gain global dans le moteur ou baisser
    le volume système.

---

Bon jeu sonore avec Image2Saw Live TUI 🎛️🖼️🎧

```

---

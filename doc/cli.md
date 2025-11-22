# Image2Saw — V3.3

Transformez n’importe quelle image en **texture sonore séquencée**…  
et, si vous le souhaitez, en **vidéo vibrante synchronisée**.

Chaque pixel devient :
- un **oscillateur audio** (fréquence = luminosité/couleur),
- un **point de vibration visuelle** dans la vidéo.

---

## 🚀 Nouveautés V3.3 (par rapport à V3.2)

- Ajout d’un **mode “artist”** :
  - `--artist` + triptyque **style / movement / density**
  - Ces curseurs sont pensés comme une couche expressive au-dessus des paramètres techniques.
- Introduction de paramètres **couleur → son** avancés :
  - `--color-mode hsv-notes` (HUE → note, VALUE → octave, SAT → amplitude)
  - `--hsv-detune-pct` : léger détune de fréquence basé sur la teinte (effet “accordéon” possible).
  - `--hsv-blend-gray` : mix entre luminance couleur (HSV) et luminance en niveaux de gris.
- Clarification et regroupement de **toutes les options CLI** dans ce README.

> ℹ️ Le mode *artist* est en cours de construction :  
> le mapping style/movement/density → paramètres techniques est déjà codé dans `apply_artist_presets`,  
> mais sa calibration fine est encore ouverte (c’est justement l’objectif de cette doc).

---

## 📦 Installation

### 1. Prérequis

- Python **3.9+**
- `ffmpeg` installé et accessible dans le `PATH` (pour la vidéo)

### 2. Installation des dépendances

Dans le dossier du projet :

```bash
pip install -r requirements.txt
````

(Le `requirements.txt` doit contenir au minimum : `numpy`, `Pillow`, `tqdm`, `moviepy`.)

---

## 🔊 Utilisation rapide

### Audio seul

```bash
python3 image2saw.py mon_image.png
```

Cela génère un fichier :

* `mon_image.wav` : texture sonore séquencée, basée sur les **niveaux de gris** par défaut.

### Audio + vidéo

```bash
python3 image2saw.py mon_image.png \
  --video \
  --video-width 800 --video-height 600
```

Produit :

* `mon_image.wav` — audio complet,
* `mon_image.mp4` — vidéo avec la même durée, et un balayage visuel synchronisé.

---

## 🧠 Logique générale

1. L’image d’entrée est mise à l’échelle dans un **espace audio** (grille de pixels utilisée pour les oscillateurs).
2. Chaque pixel devient :

   * une **fréquence** (grayscale ou HSV, suivant `--color-mode`),
   * une **amplitude** (optionnel, en mode `hsv-notes`).
3. Les oscillateurs sont **balayés temporellement** selon `--step-ms`.
4. On applique un **enveloppe** (`--fade-ms`, `--sustain-s`) et un **nombre maximum de voix** (`--voices`).
5. Optionnel : on génère une **vidéo synchronisée** à partir du même “plan de fréquences”.

---

## ⚙️ Référence complète des options CLI

### 1. Entrée et modes de couleur

#### Positionnel

| Paramètre | Type  | Défaut          | Description                                       |
| --------- | ----- | --------------- | ------------------------------------------------- |
| `image`   | `str` | — (obligatoire) | Fichier image d’entrée (par ex. `mon_image.png`). |

#### Couleur → Son

| Option             | Type  | Défaut      | Valeurs                  | Description                                                                                                                                                                                                  |
| ------------------ | ----- | ----------- | ------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `--color-mode`     | `str` | `grayscale` | `grayscale`, `hsv-notes` | Mode de conversion image → son. <br>• `grayscale` : mapping spectral continu basé sur les niveaux de gris (luminosité). <br>• `hsv-notes` : HUE → note (Do..Si), VALUE → octave (Do1..Si5), SAT → amplitude. |
| `--hsv-max-octave` | `int` | `5`         | `1`–`5` (recommandé)     | Octave maximale pour le mode `hsv-notes`. <br>Ex : `5` = plage Do1..Si5. Ignoré si `--color-mode grayscale`.                                                                                                 |

---

### 2. Paramètres audio globaux

| Option         | Type    | Défaut  | Description                                                                                                                                                                                                                                                                                 |
| -------------- | ------- | ------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `--sr`         | `int`   | `48000` | Fréquence d’échantillonnage audio (en Hz).                                                                                                                                                                                                                                                  |
| `--duration-s` | `float` | `None`  | **Durée cible** du rendu audio (en secondes). Si fourni, la taille de l’image audio est recalculée pour que le balayage (`step-ms`) couvre approximativement cette durée, tout en respectant le **ratio original** de l’image source.                                                       |
| `--size`       | `int`   | `64`    | **Taille de base** (côté) de l’image audio en pixels, lorsque `--duration-s` n’est pas spécifié. Comportement historique : l’image audio est **carrée** (`size` × `size`). Si `--duration-s` est utilisé, `size` sert de **pivot** pour la résolution, mais la taille finale peut différer. |

#### Plage de fréquences (mode grayscale)

| Option   | Type    | Défaut   | Description                                                           |
| -------- | ------- | -------- | --------------------------------------------------------------------- |
| `--fmin` | `float` | `40.0`   | Fréquence minimale (Hz) pour le mapping spectral en mode `grayscale`. |
| `--fmax` | `float` | `8000.0` | Fréquence maximale (Hz) pour le mapping spectral en mode `grayscale`. |

> En mode `hsv-notes`, les fréquences sont dérivées des **notes MIDI** (tempérament égal, A4 = 440 Hz), et `--fmin / --fmax` ne sont pas utilisées.

---

### 3. Sequencing temporel & enveloppe

| Option        | Type    | Défaut | Description                                                                                                                                                 |
| ------------- | ------- | ------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `--step-ms`   | `float` | `40.0` | Décalage temporel entre l’activation de chaque “voix” (en millisecondes). Plus la valeur est petite, plus le balayage est **rapide**.                       |
| `--sustain-s` | `float` | `0.0`  | Durée de maintien globale après le dernier oscillateur (en secondes). Permet de laisser “respirer” la fin du son.                                           |
| `--block-ms`  | `float` | `50.0` | Taille des blocs (en ms) pour le rendu audio par batch. Sert surtout à optimiser le CPU et la mémoire.                                                      |
| `--fade-ms`   | `float` | `2.0`  | Durée du fondu d’attaque/relâche de chaque oscillateur (en ms). Une valeur faible donne un son plus “sec”, une valeur plus grande adoucit les transitoires. |

#### Forme d’onde & polyphonie

| Option       | Type   | Défaut  | Valeurs                                                                                                                                                       | Description                                                                                                                                                                                                                                                                                                      |
| ------------ | ------ | ------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `--waveform` | `str`  | `saw`   | `saw`, `sine`, `triangle`, `square`                                                                                                                           | Forme d’onde utilisée pour chaque oscillateur : <br>• `saw` : riche en harmoniques, plus agressif. <br>• `sine` : très doux, idéal pour les textures “accordéon” non stridentes. <br>• `triangle` : intermédiaire, plus douce qu’une dent de scie. <br>• `square` : très marquée, riche en harmoniques impaires. |
| `--voices`   | `int`  | `32`    | Nombre maximal de **voix simultanées**. Contrôle la durée de vie effective de chaque oscillateur : plus il y a de voix, plus les notes peuvent se chevaucher. |                                                                                                                                                                                                                                                                                                                  |
| `--mono`     | *flag* | `False` | —                                                                                                                                                             | Force le rendu en **mono** (somme des canaux) au lieu de laisser un panning stéréo.                                                                                                                                                                                                                              |

---

### 4. Paramètres couleur avancés (HSV)

Ces options agissent seulement lorsque tu exploites l’information couleur.

#### Détune basé sur la teinte

| Option             | Type    | Défaut | Description                                                                                                                                                                                                                                                                                                                                                                       |
| ------------------ | ------- | ------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `--hsv-detune-pct` | `float` | `0.0`  | Amplitude du **détune** basé sur la teinte (HSV), en pourcentage. <br>La teinte (H) est mappée dans [-1, +1], puis appliquée comme facteur multiplicatif sur la fréquence : <br>`freq_finale = freq_grayscale × (1 + (hsv-detune-pct / 100) × hue_signed)` <br>Ex : `1.0` → ±1 % max de variation de fréquence selon la couleur, idéal pour un léger vibrato / effet “accordéon”. |

#### Mélange luminance HSV / gris

| Option             | Type    | Défaut | Description                                                                                                                                                                                                                                                                                                                    |
| ------------------ | ------- | ------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `--hsv-blend-gray` | `float` | `0.0`  | Mélange entre la **luminance couleur** (canal V de HSV) et la luminance en **niveaux de gris**. <br>Clampé dans `[0.0, 1.0]`. <br>• `0.0` : 100 % couleur (V). <br>• `1.0` : 100 % gris. <br>Ex : `0.15` → 85 % couleur / 15 % gris. Très utile pour garder une structure lisible tout en conservant la richesse des couleurs. |

> Combo que tu as validé “à l’oreille” pour l’effet accordéon :
>
> ```bash
> --waveform sine \
> --hsv-detune-pct 1.0 \
> --hsv-blend-gray 0.15
> ```

---

### 5. Mode “Artist” (style / movement / density)

Le mode *artist* a pour but d’exposer des **curseurs expressifs** au lieu de paramètres techniques.

#### Activation

| Option     | Type   | Défaut  | Description                                                                                                                                                                                          |
| ---------- | ------ | ------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `--artist` | *flag* | `False` | Active le **mode artiste** : les curseurs `--style`, `--movement` et `--density` sont interprétés et traduits en paramètres techniques (`waveform`, `step-ms`, `voices`) via `apply_artist_presets`. |

#### Style

| Option    | Type  | Défaut    | Valeurs                                 | Description                                                                                                                                                                                                                        |
| --------- | ----- | --------- | --------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `--style` | `str` | `ambient` | `ambient`, `cinematic`, `glitch`, `raw` | Style artistique préconfiguré. Actuellement, chaque style associe **au moins** une forme d’onde : <br>• `ambient` → waveform `sine` (textures douces) <br>• `cinematic` → `triangle` <br>• `glitch` → `square` <br>• `raw` → `saw` |

> Implémentation actuelle (V3.3) :
> `apply_artist_presets` ne change `waveform` **que si** `args.waveform` est `None`.
> Tant que la valeur par défaut reste `"saw"`, ce mapping devra être affiné pour que le style prenne réellement la main.

#### Movement → step_ms

| Option       | Type  | Défaut | Description                                                                                                                                                                                                                             |
| ------------ | ----- | ------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `--movement` | `int` | `5`    | Curseur de mouvement (1–10) : contrôle la **vitesse de balayage**. Mappé vers `step_ms` par `_map_movement_to_step_ms(movement)`. <br>Doc interne : <br>• `1` → balayage très lent (~120 ms) <br>• `10` → balayage très rapide (~20 ms) |

Formule actuelle :

```python
movement = max(1, min(10, int(movement)))
step_ms = 120.0 - (movement - 1) * (100.0 / 9.0)
```

#### Density → voices

| Option      | Type  | Défaut | Description                                                                                                                                                                                                           |
| ----------- | ----- | ------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `--density` | `int` | `5`    | Curseur de densité (1–10) : contrôle le **nombre de voix simultanées**. Mappé vers `voices` par `_map_density_to_voices(density)`. <br>Doc interne : <br>• `1` → peu de voix (~8) <br>• `10` → beaucoup de voix (~64) |

Formule actuelle :

```python
density = max(1, min(10, int(density)))
voices = round( interp(density, [1, 10], [8, 64]) )
```

> ⚠️ Note importante pour la suite :
> Pour que le mode *artist* prenne réellement le contrôle, il faudra que `waveform`, `step-ms` et `voices` soient initialisés à des valeurs “neutres” (`None`) lorsqu’on active `--artist`, ou revoir les valeurs par défaut dans le parser.
> Cette doc sert justement de base pour ne pas se perdre dans ces décisions.

---

### 6. Paramètres vidéo

Toutes ces options ne sont pertinentes que si tu ajoutes `--video`.

#### Activation & sortie

| Option        | Type   | Défaut  | Description                                                                                                    |
| ------------- | ------ | ------- | -------------------------------------------------------------------------------------------------------------- |
| `--video`     | *flag* | `False` | Si présent, génère également une **vidéo `.mp4`** en plus du WAV.                                              |
| `--video-out` | `str`  | `None`  | Nom du fichier vidéo de sortie. Si non renseigné, on utilise le nom de l’image d’entrée avec extension `.mp4`. |
| `--fps`       | `int`  | `25`    | Fréquence d’images de la vidéo (images par seconde).                                                           |

#### Bande de fréquences visibles

| Option       | Type    | Défaut | Description                                           |
| ------------ | ------- | ------ | ----------------------------------------------------- |
| `--vis-fmin` | `float` | `1.0`  | Fréquence minimale (Hz) pour la bande **visualisée**. |
| `--vis-fmax` | `float` | `10.0` | Fréquence maximale (Hz) pour la bande **visualisée**. |

> Ces paramètres définissent la plage de fréquences audio qui est traduite en vibration visuelle (par défaut, 1–10 Hz ≈ mouvement lent visible).

#### Amplitude visuelle & gaussienne

| Option             | Type    | Défaut  | Description                                                                                                                                                                |
| ------------------ | ------- | ------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `--vis-amp-pct`    | `float` | `5.0`   | Amplitude maximale de la vibration verticale, en **% de la largeur** de la vidéo. <br>Ex : avec une vidéo de largeur 800 px et `--vis-amp-pct 5`, l’amplitude max ≈ 40 px. |
| `--gauss-size-pct` | `float` | `200.0` | Diamètre de la gaussienne (fenêtre de focus) en **% de la largeur** de la vidéo. <br>Ex : `200.0` = gaussienne couvrant 2× la largeur, donc un flou très large.            |

#### Taille de la vidéo

Tu peux fixer la taille de sortie de 3 façons :

| Option           | Type  | Défaut | Description                                                                                                                               |
| ---------------- | ----- | ------ | ----------------------------------------------------------------------------------------------------------------------------------------- |
| `--video-width`  | `int` | `None` | Largeur finale de la vidéo (en pixels). Si seule la largeur ou seule la hauteur est fournie, le **ratio de l’image source** est conservé. |
| `--video-height` | `int` | `None` | Hauteur finale de la vidéo (en pixels). Même logique que pour `--video-width`.                                                            |
| `--video-size`   | `str` | `None` | Preset de taille vidéo (côté max) : `XS=64`, `S=128`, `M=256`, `L=512`, `XL=1024`. Le ratio de l’image source est conservé.               |

> Règle de priorité typique :
>
> 1. Si `--video-width` / `--video-height` sont fournis → utilisés en priorité (avec ratio préservé si un seul côté).
> 2. Sinon, si `--video-size` est fourni → le plus grand côté = preset, ratio conservé.
> 3. Sinon → la vidéo prend la **taille de l’image audio**.

---

## 🧪 Exemple “combo accordéon”

Un exemple complet qui combine tout ce qu’on a décrit :

```bash
python3 image2saw.py tableau.png \
  --color-mode grayscale \
  --waveform sine \
  --hsv-detune-pct 1.0 \
  --hsv-blend-gray 0.15 \
  --duration-s 12 \
  --step-ms 40 \
  --voices 32 \
  --video \
  --video-width 1024 --video-height 576 \
  --vis-amp-pct 5.0 \
  --gauss-size-pct 200.0
```

* **Son :** texture douce type accordéon / orgue, légère instabilité liée à la couleur (detune HSV).
* **Image :** ratio respecté, balayage régulier, gaussienne large pour un rendu organique.

---

## 🧩 À faire autour du mode Artist

Cette documentation sert aussi de **roadmap** pour stabiliser le mode `--artist` :

* [ ] Décider si `--artist` doit :

  * imposer ses propres valeurs (en ignorant `--step-ms`, `--voices`, `--waveform` sauf override explicite), ou
  * simplement proposer des **valeurs par défaut intelligentes**.
* [ ] Éventuellement : changer les **valeurs par défaut du parser** pour qu’elles soient `None` lorsque `--artist` est actif.
* [ ] Ajouter quelques **presets nommés** (par ex. `--artist-preset accordion`) basés sur :

  * `waveform = sine`
  * `hsv-detune-pct = 1.0`
  * `hsv-blend-gray = 0.15`

---

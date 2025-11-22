# Image2Saw — V3.3

Transformez n’importe quelle image en texture sonore séquencée, et,
si vous le souhaitez, en vidéo vibrante synchronisée.

Chaque pixel devient :
- un oscillateur audio (fréquence = luminosité ou couleur),
- un point de vibration visuelle dans la vidéo.

---

## Nouveautés V3.3 (par rapport à V3.2)

- Ajout de **presets artistiques clés en main** :
  - `--artist-preset` permet de charger des combinaisons cohérentes de
    paramètres (waveform, color-mode, fmin/fmax, hsv-*, step-ms, voices).
  - Ces presets servent de “points de départ” expressifs (nappes lentes,
    glitch coloré, scanner rapide, etc.).
- Paramètres couleur → son avancés :
  - `--color-mode hsv-notes` (HUE → note, VALUE → octave, SAT → amplitude).
  - `--hsv-detune-pct` : léger détune de fréquence basé sur la teinte
    (effet "accordéon" possible).
  - `--hsv-blend-gray` : mix entre luminance couleur (HSV) et luminance
    en niveaux de gris.
- Clarification et regroupement de toutes les options CLI dans ce README.

---

## Nouveautés V3.3.1 (par rapport à V3.3)

> ⚠️ Note : l’ancien mode `--artist` (avec `--style`, `--movement`,
> `--density`) a été abandonné au profit de `--artist-preset`, jugé plus
> simple et plus lisible (un preset = un son clairement identifiable).

---

## Installation

### 1. Prérequis

- Python 3.9+
- `ffmpeg` installé et accessible dans le PATH (pour la vidéo)

### 2. Installation des dépendances

Dans le dossier du projet :

```bash
pip install -r requirements.txt
````

Le fichier `requirements.txt` doit contenir au minimum :

* numpy
* Pillow
* tqdm
* moviepy

---

## Utilisation rapide

### Audio seul

```bash
python3 image2saw.py mon_image.png
```

Produit :

* `mon_image.wav` : texture sonore séquencée, basée sur les niveaux
  de gris par défaut.

### Audio + vidéo

```bash
python3 image2saw.py mon_image.png \
  --video \
  --video-width 800 --video-height 600
```

Produit :

* `mon_image.wav` : audio complet.
* `mon_image.mp4` : vidéo de même durée, avec balayage visuel
  synchronisé.

---

## Logique générale

1. L’image d’entrée est mise à l’échelle dans un "espace audio"
   (grille de pixels utilisée pour les oscillateurs).
2. Chaque pixel devient :

   * une fréquence (grayscale ou HSV, suivant `--color-mode`),
   * une amplitude (optionnelle, en mode `hsv-notes`).
3. Les oscillateurs sont balayés temporellement selon `--step-ms`.
4. On applique une enveloppe (`--fade-ms`, `--sustain-s`) et un nombre
   maximum de voix (`--voices`).
5. Optionnel : on génère une vidéo synchronisée à partir du même
   "plan de fréquences".

---

## Référence complète des options CLI

### 1. Entrée et modes de couleur

#### Argument positionnel

* `image`
  Type    : str
  Défaut  : (obligatoire)
  Rôle    : fichier image d’entrée
  Exemple : `mon_image.png`

#### Couleur → Son

* `--color-mode`
  Type    : str
  Défaut  : `grayscale`
  Valeurs : `grayscale`, `hsv-notes`
  Rôle    : mode de conversion image → son.

  * `grayscale` : mapping spectral continu basé sur la luminosité.
  * `hsv-notes` : HUE → note (Do..Si), VALUE → octave (Do1..SiN),
    SAT → amplitude.

* `--hsv-max-octave`
  Type    : int
  Défaut  : 5
  Rôle    : octave maximale pour le mode `hsv-notes`.
  Par exemple 5 ≈ plage Do1..Si5.
  Ignoré si `--color-mode grayscale`.

---

### 2. Paramètres audio globaux

* `--sr`
  Type    : int
  Défaut  : 48000
  Rôle    : fréquence d’échantillonnage audio (en Hz).

* `--duration-s`
  Type    : float
  Défaut  : None
  Rôle    : durée cible du rendu audio (en secondes).
  Si présent, la taille de l’image audio est recalculée
  pour que le balayage (via `--step-ms`) couvre
  approximativement cette durée, en respectant le ratio
  original de l’image source.

* `--size`
  Type    : int
  Défaut  : 64
  Rôle    : taille de base (côté) de l’image audio en pixels, quand
  `--duration-s` n’est pas spécifié.
  Comportement historique : image audio carrée (`size` x `size`).
  Si `--duration-s` est utilisé, `size` sert de pivot pour
  la résolution, mais la taille finale peut différer.

#### Plage de fréquences (mode grayscale)

* `--fmin`
  Type    : float
  Défaut  : 40.0
  Rôle    : fréquence minimale (Hz) pour le mapping spectral
  en mode `grayscale`.

* `--fmax`
  Type    : float
  Défaut  : 8000.0
  Rôle    : fréquence maximale (Hz) pour le mapping spectral
  en mode `grayscale`.

Remarque : en mode `hsv-notes`, les fréquences sont dérivées des
notes MIDI (tempérament égal, A4 = 440 Hz), et `--fmin` / `--fmax`
ne sont pas utilisées.

---

### 3. Sequencing temporel et enveloppe

* `--step-ms`
  Type    : float
  Défaut  : 40.0 (en pratique)
  Rôle    : décalage temporel entre l’activation de chaque voix
  (en millisecondes).
  Plus la valeur est petite, plus le balayage est rapide.
  *Note : en interne, la valeur par défaut est calculée à partir
  des presets ou, à défaut, fixée à 40 ms pour rester compatible
  avec les versions précédentes.*

* `--sustain-s`
  Type    : float
  Défaut  : 0.0
  Rôle    : durée de maintien globale après l’activation du dernier
  oscillateur (en secondes). Permet de laisser "respirer"
  la fin du son.

* `--block-ms`
  Type    : float
  Défaut  : 50.0
  Rôle    : taille des blocs (en ms) pour le rendu audio par batch.
  Sert surtout à optimiser CPU et mémoire.

* `--fade-ms`
  Type    : float
  Défaut  : 2.0
  Rôle    : durée du fondu d’attaque et de relâche pour chaque
  oscillateur (en ms).
  Petite valeur : son plus "sec".
  Grande valeur : transitoires adoucis.

#### Forme d’onde et polyphonie

* `--waveform`
  Type    : str
  Défaut  : `saw` (en pratique)
  Valeurs : `saw`, `sine`, `triangle`, `square`
  Rôle    : forme d’onde utilisée pour chaque oscillateur.

  * `saw`      : riche en harmoniques, plus agressif.
  * `sine`     : très doux, idéal pour textures "accordéon".
  * `triangle` : intermédiaire, plus douce qu’une saw.
  * `square`   : très marquée, riche en harmoniques impaires.

* `--voices`
  Type    : int
  Défaut  : 32 (en pratique)
  Rôle    : nombre maximal de voix simultanées.
  Contrôle le chevauchement des notes : plus il y a de
  voix, plus les notes peuvent se superposer.

* `--mono`
  Type    : flag
  Défaut  : False
  Rôle    : force le rendu en mono (somme L/R), au lieu d’un panning
  stéréo.

---

### 4. Paramètres couleur avancés (HSV)

Ces options n’ont d’effet que lorsque l’information couleur est
utilisée (`hsv-notes`, ou `grayscale` + blend/detune HSV).

#### Détune basé sur la teinte

* `--hsv-detune-pct`
  Type    : float
  Défaut  : 0.0
  Rôle    : amplitude du détune basé sur la teinte (HSV), en pourcent.
  Teinte H ∈ [0,1] mappée vers [-1,1], appliquée comme
  facteur multiplicatif :
  `freq_finale = freq * (1 + (hsv-detune-pct / 100) * H_signed)`
  Exemple : 1.0 → ±1 % max de variation de fréquence
  selon la couleur.

#### Mélange luminance HSV / gris

* `--hsv-blend-gray`
  Type    : float
  Défaut  : 0.0
  Rôle    : mélange entre luminance couleur (canal V de HSV) et
  luminance en niveaux de gris.
  Valeur clampée dans [0.0, 1.0].

  * 0.0 : 100 % couleur (V).
  * 1.0 : 100 % gris.
    Exemple : 0.15 → 85 % couleur / 15 % gris.

Combo validé à l’oreille pour un effet "accordéon" doux :

```bash
--waveform sine \
--hsv-detune-pct 1.0 \
--hsv-blend-gray 0.15
```

---

### 5. Presets artistiques (`--artist-preset`)

Les presets artistiques fournissent des **combinaisons de paramètres
clé en main**, pour explorer rapidement des ambiances très différentes
sans régler chaque option à la main.

Activation :

* `--artist-preset`
  Type    : str
  Valeurs : parmi (liste non exhaustive) :

  * `ambient_slow_dark`
  * `ambient_slow_shimmer`
  * `cinematic_slow`
  * `cinematic_glow`
  * `photo_organ`
  * `scan_fast_bright`
  * `glitch_color_burst`
  * `bitcrush_scan`
  * `ink_in_water`
  * `neon_rain`

Chaque preset définit au minimum :

* `color_mode` (`grayscale` ou `hsv-notes`),
* `waveform` (`sine`, `triangle`, `square`, `saw`),
* une plage de fréquences (`fmin`, `fmax`) ou une plage de notes,
* des réglages HSV (`hsv_detune_pct`, `hsv_blend_gray`, `hsv_max_octave`),
* la vitesse de balayage (`step-ms`),
* la densité (`voices`).

Exemples de caractère (résumé) :

* `ambient_slow_dark`
  Nappes graves très lentes, sombres, graves dominants.

* `ambient_slow_shimmer`
  Nappes lentes plus lumineuses, "accordéon pastel", basées sur
  `sine + hsv_detune_pct=1 + hsv_blend_gray=0.15`.

* `cinematic_slow`
  Texture filmique lente, large, basée sur `hsv-notes + triangle`.

* `glitch_color_burst`
  Glitch couleur agressif, rapide, `hsv-notes + square + detune fort`.

* `bitcrush_scan`
  Balayage rapide, carrés, ressenti 8-bit / bitcrush.

> Remarque : les presets écrasent volontairement certains paramètres
> (waveform, fmin/fmax, hsv-*, step-ms, voices) pour garantir un
> rendu sonore cohérent. Il reste possible de les ajuster ensuite
> en redonnant des options techniques explicites.

---

### 6. Paramètres vidéo

Ces options sont pertinentes uniquement si `--video` est activé.

#### Activation et sortie

* `--video`
  Type    : flag
  Défaut  : False
  Rôle    : génère une vidéo `.mp4` en plus du WAV.

* `--video-out`
  Type    : str
  Défaut  : None
  Rôle    : nom du fichier vidéo de sortie.
  Si absent, on utilise le nom de l’image d’entrée avec
  extension `.mp4`.

* `--fps`
  Type    : int
  Défaut  : 25
  Rôle    : nombre d’images par seconde (fluidité).

#### Bande de fréquences visibles

* `--vis-fmin`
  Type    : float
  Défaut  : 1.0
  Rôle    : fréquence minimale (Hz) pour la bande visualisée.

* `--vis-fmax`
  Type    : float
  Défaut  : 10.0
  Rôle    : fréquence maximale (Hz) pour la bande visualisée.

Par défaut, 1–10 Hz ≈ oscillations lentes visibles dans la vidéo.

#### Amplitude visuelle et gaussienne

* `--vis-amp-pct`
  Type    : float
  Défaut  : 5.0
  Rôle    : amplitude maximale de la vibration verticale, en pourcent
  de la largeur de la vidéo.
  Exemple : largeur = 800 px, vis-amp-pct = 5 → amplitude
  max ≈ 40 px.

* `--gauss-size-pct`
  Type    : float
  Défaut  : 200.0
  Rôle    : diamètre de la gaussienne (fenêtre de focus) en pourcent
  de la largeur de la vidéo.
  Exemple : 200.0 = gaussienne couvrant 2× la largeur,
  flou très large.

#### Taille de la vidéo

Plusieurs façons de fixer la taille :

* `--video-width`
  Type    : int
  Défaut  : None
  Rôle    : largeur finale de la vidéo (en pixels).
  Si seule la largeur ou seule la hauteur est fournie,
  le ratio de l’image source est conservé.

* `--video-height`
  Type    : int
  Défaut  : None
  Rôle    : hauteur finale de la vidéo (en pixels).
  Même logique que pour `--video-width`.

* `--video-size`
  Type    : str
  Défaut  : None
  Rôle    : preset de taille vidéo (côté max) :
  `XS=64`, `S=128`, `M=256`, `L=512`, `XL=1024`.
  Le ratio de l’image source est conservé.

Règle de priorité typique :

1. Si `--video-width` ou `--video-height` sont fournis, ils sont
   utilisés en priorité (le ratio est respecté si un seul côté
   est donné).
2. Sinon, si `--video-size` est fourni, il fixe le plus grand côté.
3. Sinon, la vidéo utilise la taille de l’image audio.

---

## Exemple "combo accordéon"

Exemple complet combinant les paramètres audio et vidéo :

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

Variante en utilisant directement un preset :

```bash
python3 image2saw.py tableau.png \
  --artist-preset ambient_slow_shimmer \
  --duration-s 12 \
  --video \
  --video-width 1024 --video-height 576
```

* Son : texture douce type accordéon / orgue, légère instabilité
  liée à la couleur (detune HSV).
* Image : ratio respecté, balayage régulier, gaussienne large pour
  un rendu organique.

```
```

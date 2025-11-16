# Image2Saw v3.0 🎧🎬

Transforme une image en **texture sonore séquencée** et, en option, en **vidéo vibrante** synchronisée.

Chaque pixel devient un oscillateur (saw / sine / triangle / square) dont la fréquence est déterminée par sa luminosité.  
La vidéo montre l’image “vibrer” autour d’une fenêtre glissante, avec une gaussienne centrée sur la zone en cours de lecture.

---

## ✨ Fonctionnalités principales

### Audio

- Redimensionnement carré de l'image (`--size`, filtre **LANCZOS** pour un rendu doux)
- Parcours **zigzag** des pixels  
  (ligne paire : gauche→droite, ligne impaire : droite→gauche)
- Mapping niveau de gris → fréquence `[fmin, fmax]`
- **Fenêtre glissante** (`--voices`) : nombre de voix simultanées
- **Spatialisation stéréo** constant-power (`--stereo` / `--mono`)
- Rendu **bloc par bloc** (`--block-ms`) pour limiter la charge CPU/mémoire
- Enveloppe d’**attaque/relâche** demi-cosinus (`--fade-ms`) pour éviter les clics
- Formes d’onde audio :
  - `saw`, `sine`, `triangle`, `square`
- Écriture WAV **16-bit stéréo**

### Vidéo (streaming via MoviePy)

- Par défaut : taille vidéo = `--size` (même grille que l’image grayscale)
- Optionnel : `--video-size` pour forcer une taille vidéo (ex: `500 px`)
- Image couleur :
  1. Redimensionnée en `size×size` (**LANCZOS**)
  2. Éventuellement rescalée en `video_size×video_size` (**NEAREST** pour un rendu pixel-art)
- Vibration gaussienne centrée sur la fenêtre glissante :
  - Diamètre de la gaussienne en **% de la largeur vidéo** (`--gauss-size-pct`)
  - Amplitude de vibration en **% de la largeur vidéo** (`--vis-amp-pct`)
- Fondu doux sur les bords de la gaussienne (demi-cosinus)
- Déplacement **radial** modulé par une forme d’onde visuelle
- Génération des frames à la volée via `MoviePy.VideoClip`  
  → pas de stockage massif de frames en RAM
- Barre de progression dédiée :  
  `MoviePy - Building video`
- Nom de la vidéo basé sur l’image :
  - `image.ext` → `image.mp4` par défaut (surchageable avec `--video-out`)

---

## 🧱 Structure du projet (v3.0)

```text
image2saw/
│
├── image2saw.py          # Point d'entrée (CLI) : python3 image2saw.py ...
└── image2saw_pkg/
    ├── __init__.py       # Version, exports
    ├── cli.py            # Parsing des arguments + orchestration
    ├── image_proc.py     # Chargement & prétraitement de l’image (grayscale, zigzag)
    ├── audio.py          # Plan temporel, synthèse audio, écriture WAV
    └── video.py          # MoviePy, keyframes, vibration gaussienne, rendu MP4
````

* Tu peux aussi utiliser les modules directement dans un autre script Python :

  * `from image2saw_pkg.audio import plan_schedule, render_audio, ...`
  * `from image2saw_pkg.video import render_video_with_audio, ...`

---

## 📦 Installation

### 1. Cloner le projet

```bash
git clone <ton-repo-git> image2saw
cd image2saw
```

### 2. Créer un environnement virtuel (recommandé)

```bash
python3 -m venv venv
source venv/bin/activate   # macOS / Linux
# ou
venv\Scripts\activate      # Windows
```

### 3. Installer les dépendances

```bash
pip install -r requirements.txt
```

### 4. Contenu de `requirements.txt`

```txt
numpy
Pillow
tqdm
moviepy
```

> 💡 Si tu ne veux **que l’audio**, `moviepy` est techniquement optionnel.
> Sans `moviepy`, l’audio fonctionnera mais la vidéo sera désactivée avec un message explicite.

---

## ▶️ Utilisation (CLI)

Le point d’entrée est le fichier :

```bash
python3 image2saw.py <image> [options...]
```

### Exemple minimal (audio seul)

```bash
python3 image2saw.py mon_image.jpg
```

* Produit : `mon_image.wav`
  (stéréo, saw, taille logique 128×128, paramètres par défaut)

### Exemple audio + vidéo

```bash
python3 image2saw.py mon_image.jpg \
  --size 128 \
  --sr 32000 \
  --fmin 5 --fmax 200 \
  --step-ms 100 \
  --sustain-s 5 \
  --voices 20 \
  --waveform saw \
  --stereo \
  --video \
  --fps 25 \
  --vis-fmin 1 --vis-fmax 10 \
  --vis-amp-pct 1.5 \
  --gauss-size-pct 30 \
  --video-size 500
```

* Produit :

  * `mon_image.wav`
  * `mon_image.mp4`

---

## ⚙️ Options de la ligne de commande

### Audio

* `image`
  Fichier image d’entrée (JPEG, PNG, etc.)

* `--size` *(int, défaut: 128)*
  Taille du côté **carré logique** utilisé pour la synthèse audio.

* `--sr` *(int, défaut: 32000)*
  Fréquence d’échantillonnage (Hz).

* `--fmin` *(float, défaut: 5.0)*
  Fréquence minimale (Hz).

* `--fmax` *(float, défaut: 200.0)*
  Fréquence maximale (Hz).
  → Le niveau de gris 0 correspond à `fmin`, 255 à `fmax`.

* `--step-ms` *(float, défaut: 100.0)*
  Décalage entre deux oscillateurs successifs (en ms).
  → Définit la vitesse de balayage de l’image.

* `--sustain-s` *(float, défaut: 5.0)*
  Durée ajoutée à la fin du rendu audio après le dernier oscillateur.

* `--block-ms` *(float, défaut: 50.0)*
  Durée d’un bloc de calcul (en ms).
  Plus petit = plus réactif mais plus de boucles CPU.

* `--fade-ms` *(float, défaut: 5.0)*
  Durée du fondu d’attaque/relâche (en ms) appliquée à chaque oscillateur.

* `--waveform {saw,sine,triangle,square}` *(défaut: `saw`)*
  Forme d’onde utilisée pour le son (et pour la modulation visuelle).

* `--voices` *(int, défaut: 20)*
  Nombre maximal d’oscillateurs actifs simultanément
  → règle la largeur temporelle de la fenêtre glissante.

* `--stereo`
  Active la spatialisation stéréo **constant-power**
  (les pixels à gauche sont panés vers la gauche, ceux à droite vers la droite).

* `--mono`
  Force un rendu mono (le canal R copie le canal L).

> Si `--stereo` et `--mono` sont absents, le mode par défaut est **stéréo**.

---

### Vidéo

* `--video`
  Active la génération de la vidéo (sinon : audio uniquement).

* `--fps` *(int, défaut: 25)*
  Framerate de la vidéo.

* `--vis-fmin` *(float, défaut: 1.0)*
  Fréquence visuelle minimale en Hz (lente).

* `--vis-fmax` *(float, défaut: 10.0)*
  Fréquence visuelle maximale en Hz (rapide).
  → La fréquence audio locale `[fmin, fmax]` est mappée dans `[vis-fmin, vis-fmax]`.

* `--vis-amp-pct` *(float, défaut: 1.0)*
  Amplitude maximale de la vibration visuelle en **% de la largeur de la vidéo**.
  Exemple : `--vis-amp-pct 2.0` → déplacement radial max ≈ 2% de la largeur.

* `--gauss-size-pct` *(float, défaut: 30.0)*
  Diamètre de la gaussienne (zone vibrante) en **% de la largeur vidéo**.
  → Plus grand = halo plus large autour de la fenêtre active.

* `--video-size` *(int, défaut: 0)*
  Taille du côté de la vidéo (en pixels).

  * `0` → utilise `--size`
  * sinon, l’image logique `size×size` est rescalée en `video-size×video-size` en NEAREST (pixel-art).

* `--video-out` *(str, défaut: "AUTO")*
  Nom du fichier de sortie vidéo.

  * `"AUTO"` → même nom que l’image avec `.mp4`
  * sinon : utilise la valeur fournie.

---

## 🧠 Annexe technique (pour développeurs)

### Pipeline audio

1. **Image → grayscale carré**

   * `load_image_to_gray_square(path, size)` (dans `image_proc.py`)
   * `ImageOps.fit(..., LANCZOS)` → image `size×size`, niveaux de gris 0–255.

2. **Grayscale → fréquences**

   * `map_gray_to_freq(gray, fmin, fmax)` (dans `audio.py`)
   * Mapping linéaire :
     `f = fmin + (gray / 255) * (fmax - fmin)`.

3. **Planification temporelle**

   * `plan_schedule(freqs, size, sr, step_ms, sustain_s, stereo, voices)`
   * Lecture en zigzag (`zigzag_indices`) pour définir l’ordre des pixels.
   * Pour chaque pixel → un `Osc(f, start, end, pan_l, pan_r)` :

     * `start = i * step_s`
     * `end   = (i + voices) * step_s`
   * Durée totale ~ `(N - 1 + voices) * step_s + sustain_s`.

4. **Synthèse bloc par bloc**

   * `render_audio(oscs, T, sr, block_ms, mono, waveform, fade_ms, voices)`
   * Pour chaque bloc `[s0, s1)` :

     * On accumule les contributions de tous les oscillateurs actifs.
     * Forme d’onde : `saw`, `sine`, `triangle`, `square`
       (via `generate_waveform`).
     * Enveloppe demi-cosinus sur `fade_ms` au début/fin de chaque osc.
   * Sortie : tableau `float64` `(n_samples, 2)` (L/R).

5. **Normalisation + WAV**

   * `write_wav_int16_stereo(path, sr, data_lr)` :

     * Normalisation pour éviter le clipping
     * Conversion en `int16`
     * Fichier WAV 16-bit PCM stéréo.

---

### Pipeline vidéo

1. **Préparation de l’image couleur**

   * On repart de l’image originale (RGB).
   * `ImageOps.fit(..., LANCZOS)` en `size×size`.
   * Optionnel : resize en `video_size×video_size` (NEAREST).

2. **Keyframes vidéo**

   * Pour chaque pixel dans l’ordre zigzag :

     * Temps keyframe : `t_k = i * step_s`
     * Centre dans l’espace vidéo :

       * `cx = (c + 0.5) * scale - 0.5`
       * `cy = (r + 0.5) * scale - 0.5`
     * `f_audio = freqs[r, c]`
     * `f_vis = map_audio_to_visual_freq(f_audio, fmin, fmax, vis_fmin, vis_fmax)`
   * On obtient une liste de `VideoKeyframe(...)`.

3. **Rendu frame-by-frame (MoviePy)**

   * `render_video_with_audio(...)` :

     * Charge l’audio (`AudioFileClip`).
     * Crée un `VideoClip(make_frame, duration=audio_duration)`.
   * Pour chaque `t` :

     * On trouve la keyframe active (dernière dont `time <= t`).
     * On calcule un déplacement radial autour du centre `(cx, cy)` :

       * amplitude spatiale gaussienne (diamètre en `%` de la largeur vidéo)
       * fondu demi-cosinus sur les bords
       * modulation temporelle par `visual_wave(t, f_vis, waveform)`
     * On applique le champ de déplacement aux coordonnées de l’image.

---

## ✅ Résumé

* **v3.0** garde 100% des fonctionnalités de la v2.9…
* …mais dans une **structure modulaire** prête pour :

  * une version GUI
  * une version Web
  * des extensions pour artistes numériques (presets, randomisation, etc.)

Si tu veux, on peut maintenant ajouter au README une section **“Presets artistiques”** (ex : glitch, ambient, drone, noise) avec des combinaisons de paramètres prêtes à l’emploi.

```
```


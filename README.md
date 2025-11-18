# ✅ **README.md (V3.2)**

*(Complet, clair, et conforme à ton architecture actuelle)*

````markdown
# Image2Saw — V3.2
Transformez n’importe quelle image en **texture sonore** et **vidéo synchronisée**, où chaque pixel devient un oscillateur audio et un point de vibration visuelle.

> **Nouveautés V3.2 :**  
> - Formats non-carrés gérés (audio & vidéo)  
> - Pixel-art couleur  
> - Vidéo stretch ou ratio préservé (`--video-width / --video-height`)  
> - Centre de gaussienne aligné sur les pixels (fix artefact)  
> - Fade-out du balayage (fin plus douce)  
> - Compatibilité QuickTime améliorée  

---

# 📦 Installation

### 1. Installer les dépendances Python
```bash
python3 -m pip install -r requirements.txt
````

### Contenu du `requirements.txt`

```
numpy
Pillow
tqdm
moviepy
imageio-ffmpeg
```

Optionnel : MoviePy n’est importé que si `--video` est utilisé.

---

# 🚀 Usage rapide

### Audio seul

```bash
python3 image2saw.py monimage.png --duration-s 8
```

### Audio + vidéo couleur

```bash
python3 image2saw.py monimage.jpg --duration-s 10 --video
```

### Vidéo en taille spécifique (ratio conservé)

```bash
python3 image2saw.py photo.png --duration-s 10 \
  --video --video-width 800
```

### Vidéo stretch (force largeur+hauteur exactes)

```bash
python3 image2saw.py artwork.png --duration-s 10 \
  --video --video-width 800 --video-height 600
```

---

# ⚙️ Paramètres principaux

### Image → Audio

| Option            | Description                                                                                                      |
| ----------------- | ---------------------------------------------------------------------------------------------------------------- |
| `--duration-s`    | Durée cible du son. Ne modifie pas `step-ms`. Recalcule la taille de l’image audio (non-carrée, ratio préservé). |
| `--step-ms`       | Décalage entre oscillateurs.                                                                                     |
| `--fmin / --fmax` | Plage de fréquences des oscillateurs.                                                                            |
| `--waveform`      | saw, sine, square, triangle.                                                                                     |
| `--voices`        | Nombre de voix superposées en même temps.                                                                        |
| `--fade-ms`       | Fade-in/out audio par oscillateur.                                                                               |

---

# 🎬 Paramètres vidéo

| Option                    | Description                                                      |
| ------------------------- | ---------------------------------------------------------------- |
| `--video`                 | Active le rendu vidéo.                                           |
| `--fps`                   | Images/seconde.                                                  |
| `--video-width`           | Largeur finale (px). Préserve le ratio si seule.                 |
| `--video-height`          | Hauteur finale (px). Préserve le ratio si seule.                 |
| `--vis-fmin / --vis-fmax` | Plage de fréquences visuelles (oscillation de la gaussienne).    |
| `--vis-amp-pct`           | Amplitude max de la déformation (% de la largeur vidéo).         |
| `--gauss-size-pct`        | Diamètre de la zone de déformation gaussienne (% largeur vidéo). |
| `--video-out`             | Nom du fichier mp4 final.                                        |

---

# 🖼️ Fonctionnement du rendu vidéo (V3.2)

1. L'image source est :

   * convertie en **pixel-art couleur**
     (reduce → grille audio → upscale NEAREST).
2. Une **fenêtre glissante zigzag** parcourt l’image (même ordre que l’audio).
3. Une **déformation locale gaussienne** est appliquée autour du pixel actif.
4. La fréquence visuelle `f_vis` est dérivée du pixel audio correspondant.
5. Le centre de la gaussienne est **snapé** aux centres de pixels →
   ➜ supprime l’effet “œil” observé en V3.1.
6. Les derniers 15% du balayage ont un **fade-out progressif**.
7. Sortie vidéo : H.264 `yuv420p`, compatible QuickTime.

---

# 📂 Architecture du projet

```
image2saw/
│
├── image2saw.py              # Entrée principale (module -m)
├── image2saw_pkg/
│   ├── cli.py                # Gestion arguments + orchestrateur
│   ├── audio.py              # Rendu audio vectorisé
│   ├── video.py              # Rendu vidéo couleur
│   ├── image_proc.py         # Resize logique audio/vidéo, zigzag
│   └── __init__.py
│
└── README.md
```

---

# 🧪 Exemple complet

```bash
python3 image2saw.py monimage.png \
  --duration-s 12 \
  --video \
  --video-width 900 \
  --fps 25 \
  --vis-fmin 0.5 --vis-fmax 8 \
  --vis-amp-pct 2 \
  --gauss-size-pct 30
```

---

# 📝 Notes développeurs

### 💡 Pourquoi le centre est aligné sur les pixels ?

Le rendu NEAREST génère des artefacts très visibles si la gaussienne tombe
**pile sur une frontière entre deux macro-pixels**.
En centrant toujours sur `(n + 0.5)`, on stabilise le warp → plus d’effet “œil”.

### 🧠 Formats non carrés

`--duration-s` ne touche jamais `step-ms`.
Il calcule simplement la taille logique `(W,H)` → nombre d’oscillateurs exact, ratio préservé.

### 🎞️ Encodage QuickTime

`libx264` + `yuv420p` + `+faststart` + largeur/hauteur paires = compat totale macOS.

---

# 🆘 Support

Pour toute question ou idée d’évolution :
👉 GitHub Issues ou me contacter sur X / LinkedIn.

```

---

Si tu veux, je peux aussi te générer :

✔ un message de release GitHub  
✔ un tag v3.2 propre  
✔ un jeu d’exemples (images + vidéos demo)  

Dis-moi juste ! 🚀
```


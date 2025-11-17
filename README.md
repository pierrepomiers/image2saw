# 🖼️🎵 Image2Saw v3.1  
Transformez n'importe quelle image en une texture sonore et une vidéo synchronisée.

---

## ✨ Nouveautés de la V3.1

- **Nouvelle option `--duration-s`** : permet de définir directement la durée finale du son *sans changer* la texture rythmique.
- **Recalcul automatique de la taille d’image** en fonction de la durée demandée.
- `--step-ms` reste une signature du rendu : **il n'est jamais modifié automatiquement**.
- Pipeline audio/vidéo synchronisé automatiquement.
- Documentation enrichie et pédagogie améliorée pour artistes & dev.

---

# 📦 Installation

### 1. Cloner le dépôt
```bash
git clone https://github.com/pierrepomiers/image2saw
cd image2saw
````

### 2. (Optionnel) Créer un environnement virtuel

```bash
python3 -m venv venv
source venv/bin/activate   # macOS / Linux
venv\Scripts\activate      # Windows
```

### 3. Installer les dépendances

```bash
pip install -r requirements.txt
```

---

# 🚀 Utilisation simple

### Commande minimale

```bash
python3 image2saw.py mon_image.jpg
```

Génère un fichier WAV basé sur l’image avec les paramètres par défaut.

---

# 🎛️ Options principales

| Option             | Rôle                                                                                              |
| ------------------ | ------------------------------------------------------------------------------------------------- |
| `--size N`         | Taille **initiale** de l’image carrée (`N × N`). Peut être remplacée si `--duration-s` est donné. |
| `--duration-s T`   | Durée cible finale du rendu (audio + vidéo). Recalcule automatiquement la taille de l’image.      |
| `--step-ms MS`     | Délai entre oscillateurs (texture temporelle).                                                    |
| `--voices N`       | Polyphonie interne.                                                                               |
| `--sustain-s S`    | Durée finale de maintien des oscillateurs.                                                        |
| `--sr SR`          | Fréquence échantillonnage audio.                                                                  |
| `--fmin`, `--fmax` | Bande de fréquences.                                                                              |
| `--waveform`       | onde : `sine`, `saw`, `tri`, `square`.                                                            |
| `--video`          | Génère une vidéo synchronisée.                                                                    |
| `--video-size N`   | Dimension de la vidéo finale.                                                                     |
| `--fps N`          | Framerate vidéo.                                                                                  |

---

# 📘 Exemple complet (commande + explication)

### 🎯 Objectif artistique

Créer une pièce audiovisuelle de **22 secondes** avec une texture rythmique définie par `--step-ms 12`, 16 voix et une vidéo en 500 px.

### 🔧 Commande

```bash
python3 image2saw.py mon_image.jpg \
  --step-ms 12 \
  --duration-s 22 \
  --voices 16 \
  --sustain-s 1.0 \
  --waveform saw \
  --video \
  --video-size 500 \
  --fps 30
```

### 🧩 Explication

* `--duration-s 22` fixe la durée finale souhaitée.
* L’image est automatiquement redimensionnée pour approximer 22 secondes.
* `--step-ms` reste intact → la “vitesse interne” du mouvement sonore ne change pas.
* La durée audio réelle est utilisée pour la vidéo → synchronisation parfaite.

---

# 🧠 Relation entre durée (`--duration-s`), step (`--step-ms`) et taille d’image (`--size`)

Chaque pixel ↦ un oscillateur.
Pour une image carrée :

```
N = size × size
step_s = step_ms / 1000
```

Durée approximative du son :

```
T ≈ (N - 1 + voices) * step_s + sustain_s
```

## 🔄 Nouveauté V3.1 : contrôle *direct* de la durée

Lorsque `--duration-s` est fourni, Image2Saw **recalcule uniquement la taille de l’image**, pas `step-ms`.

Formule inversée :

```
N_target ≈ (duration_s - sustain_s) / step_s - voices + 1
size ≈ sqrt(N_target)
```

→ La durée finale devient cohérente avec la valeur demandée,
→ tout en conservant la texture temporelle (`step-ms`).

---

# 📐 Diagramme ASCII explicatif

```
                        ┌───────────────────────────┐
                        │     image d'entrée        │
                        │      (originale)          │
                        └───────────┬───────────────┘
                                    │
                                    ▼
                    ┌──────────────────────────────────────┐
                    │  resize automatique basé sur          │
                    │  --duration-s et --step-ms            │
                    │                                       
                    │  size = sqrt(N_target)                │
                    │  N_target ≈ (T - sustain)/step - v    │
                    └──────────────────┬────────────────────┘
                                       │
                                       ▼
                            ┌─────────────────┐
                            │  image finale   │
                            │ size x size px  │
                            └───────┬─────────┘
                                    │
                                    ▼
           ┌──────────────────────────────────────────────────────────┐
           │  Chaque pixel → un oscillateur → une fréquence           │
           │  définie par la luminance                               │
           └──────────────────────────────────────────────────────────┘
                                    │
                                    ▼
                  ┌───────────────────────────────────────────┐
                  │  Déclenchement des oscillateurs :         │
                  │  time(i) = i × step_s                     │
                  │  T ≈ (N - 1 + voices) × step_s + sustain │
                  └─────────────────┬─────────────────────────┘
                                    │
                                    ▼
                ┌────────────────────────────────────────┐
                │       Audio (WAV)                      │
                │     durée ≈ --duration-s               │
                └────────────────┬───────────────────────┘
                                 │
                                 ▼
                   ┌────────────────────────────────────────┐
                   │       Vidéo (MP4)                       │
                   │  durée = durée audio (exacte)           │
                   └────────────────────────────────────────┘
```

---

# 🎥 Génération vidéo

Activer la vidéo :

```bash
--video
```

Options utiles :

```bash
--video-size 500
--fps 30
```

La vidéo se cale automatiquement sur la durée exacte du WAV.

---

# 🎨 Conseils artistiques

* Pour une texture “fine” : `--step-ms 3` à `--step-ms 8`
* Pour une progression lente : `--step-ms 20` à `--step-ms 30`
* Pour un rendu massif : augmenter `--voices`
* Pour générer plusieurs durées à partir d’une même œuvre : jouer uniquement sur `--duration-s`

---

# 🛠 Notes techniques (développeurs)

### Recalcul automatique de la taille d’image

```python
if duration_s is not None:
    step_s = step_ms / 1000
    sweep_T = duration_s - sustain_s

    N = (sweep_T / step_s) - voices + 1
    N = max(1, round(N))

    size = max(1, int(math.sqrt(N)))
```

### Pipeline interne

1. Analyse → resize dynamique
2. Mapping pixels → fréquences
3. Planification temporelle (`plan_schedule`)
4. Synthèse WAV (`render_audio`)
5. Génération vidéo (`render_video_with_audio`)

### Vidéo

```
VideoClip(..., duration=T_audio)
```

→ La durée audio pilote automatiquement la durée vidéo.

---

# 🧾 Licence

MIT — libre pour artistes, VJs, installations, performances, IA créatives.

---

# ❤️ Auteurs

* **Pierre Pomiers** — conception
* **ChatGPT (GPT-5)** — implémentation & documentation

````

---

# ✅ **2) Release notes GitHub pour la V3.1 (prêtes à publier)**

Voici une **release note GitHub parfaitement formatée**.  
Tu peux la coller dans **Releases → Draft a new release**.

---

## 🎉 Image2Saw v3.1 — Release Notes

### ✨ Nouveautés principales

#### 🆕 1. Nouvel argument : `--duration-s`
Vous pouvez désormais demander directement une **durée finale en secondes** pour vos pièces sonores et audiovisuelles.

- **Sans modifier `--step-ms` !**  
- La texture rythmique reste 100% identique.  
- C’est la **taille de l’image** qui est recalculée automatiquement.

> Objectif : donner un contrôle artistique immédiat  
> ("je veux une œuvre de 20 secondes")  
> sans changer la dynamique interne.

---

#### 🔄 2. Recalcul automatique de l’image
Si `--duration-s` est défini :

- On calcule `N_target` (nombre d’oscillateurs)
- On en déduit la taille d’image `size = sqrt(N_target)`
- L’image est redimensionnée en conséquence

Cela permet :

- un contrôle précis de la durée  
- une cohérence totale entre audio et vidéo  
- une simplicité maximale pour les artistes

---

#### 🎥 3. Vidéo automatiquement synchronisée
La vidéo prend la **durée réelle du WAV** et s’y cale exactement.

Aucune option spécifique : juste `--video`.

---

#### 📘 4. Documentation entièrement réécrite
- Section complète sur la relation durée ↔ pixels ↔ oscillateurs
- Exemple complet prêt à l’emploi
- Diagramme ASCII explicatif
- Notes développeurs enrichies

---

### 🛠 Améliorations internes

- Code restructuré autour du recalcul de durée  
- Clarification de la logique `step-ms` → densité  
- Nettoyage du CLI  
- Préparation de la future V3.2 (formats non carrés)

---

### 📦 Commande emblématique de la v3.1

```bash
python3 image2saw.py mon_image.jpg \
  --step-ms 12 \
  --duration-s 22 \
  --voices 16 \
  --sustain-s 1.0 \
  --video \
  --video-size 500
````

---

### ❤️ Remerciements

Merci à Pierre pour son travail artistique et la vision du projet.
Cette version apporte un réel saut d’usage pour les créateurs visuels, VJ, performers, artistes IA et explorateurs sonores.


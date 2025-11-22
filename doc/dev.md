Voici **la version développeur**, pensée comme une documentation technique interne :
➡️ relations mathématiques
➡️ formules exactes
➡️ dépendances entre paramètres
➡️ pipeline complet image → oscillateurs → blocs audio → vidéo.

C’est une base parfaite pour stabiliser les presets et le mode Artist.

---

# 🧠 **Image2Saw – Carte technique développeur (V3.3)**

### *Documentation interne — relations, formules, pipeline complet*

---

# 1. 🏗 ARCHITECTURE GLOBALE (pipeline développeur)

```
             ┌────────────────────────────────────────────┐
             │  1. LOAD IMAGE                             │
             │     - PIL.Image.open()                     │
             └────────────────────────────────────────────┘
                           |
                           v
             ┌────────────────────────────────────────────┐
             │  2. AUDIO IMAGE PREP                       │
             │     - Resize algorithm (size vs duration)  │
             │     - Convert to RGB / HSV / L             │
             └────────────────────────────────────────────┘
                           |
                           v
            ┌──────────────────────────────────────────────┐
            │  3. PIXEL → OSCILLATORS                      │
            │    grayscale: lum → freq                     │
            │    hsv-notes: H → note, V → octave, S → amp  │
            │    detune HSV, blend HSV/gray                │
            └──────────────────────────────────────────────┘
                           |
                           v
          ┌─────────────────────────────────────────────────────┐
          │  4. SEQUENCING & ENVELOPES                          │
          │    activation_time(i) = i * step_ms                 │
          │    fade, sustain, polyphony                         │
          └─────────────────────────────────────────────────────┘
                           |
                           v
       ┌─────────────────────────────────────────────────────────┐
       │  5. BLOCK RENDERING (batch audio)                       │
       │    - block_ms = 50ms (par défaut)                       │
       │    - vectorisation + LUT d’ondes                        │
       └─────────────────────────────────────────────────────────┘
                           |
                           v
        ┌────────────────────────────────────────────────────────┐
        │  6. WAV OUTPUT                                         │
        └────────────────────────────────────────────────────────┘
                           |
                           v
    ┌─────────────────────────────────────────────────────────────┐
    │  7. VIDEO SYNTHESIS (optionnel)                             │
    │    - fréquence → vibration visuelle                         │
    │    - gaussienne / amplitude / fps                           │
    └─────────────────────────────────────────────────────────────┘
```

---

# 2. 📏 **RÉSOLUTION AUDIO (image → oscillateurs)**

## 2.1 Cas **sans `--duration-s`**

```
audio_w = audio_h = size     (image audio carrée)
nb_osc = size * size
```

## 2.2 Cas **avec `--duration-s`**

La durée souhaitée impose une taille :

```
T = duration_s
Δt = step_ms / 1000
nb_osc ≈ T / Δt
```

Puis on **préserve le ratio** de l’image source :

```
ratio = src_w / src_h
audio_h = sqrt(nb_osc / ratio)
audio_w = audio_h * ratio
```

Arrondis aux entiers.

---

# 3. 🎚 **GRAYSCALE — Formules exactes**

### 3.1 Conversion luminosité → fréquence

```
lum ∈ [0, 255]
lum_norm = lum / 255
freq = fmin + lum_norm * (fmax - fmin)
```

### 3.2 Après mélange HSV/gray :

```
lum = (1 - blend) * V + blend * gray_norm      # blend = hsv_blend_gray
freq = fmin + lum * (fmax - fmax)
```

### 3.3 Après détune HSV :

```
hue_norm = H ∈ [0,1]
hue_signed = 2*(hue_norm - 0.5)                # [-1, 1]
detune_factor = 1 + (detune_pct/100) * hue_signed
freq_final = freq * detune_factor
```

---

# 4. 🎨 **HSV-NOTES — Formules exactes**

### 4.1 Notes et fréquence

```
H ∈ [0,1]
pitch_index = int(H * 12)            # 0..11  (Do..Si)
midi_note = base_C + pitch_index     # base_C = 24 = C1

V ∈ [0,1]
oct_range = hsv_max_octave - 1
oct_idx = int(V * oct_range)
midi_note += oct_idx * 12

freq = 440 * 2^((midi_note - 69)/12)
```

### 4.2 Amplitude via Saturation

```
amp = S ∈ [0,1]
```

*(puis normalisé par la polyphonie)*

---

# 5. ⏱ **SEQUENCING TEMPOREL**

Pour chaque oscillateur indexé `i` :

```
activation_time[i] = i * (step_ms / 1000)
```

Durée totale approximative :

```
T ≃ nb_osc * step_ms / 1000 + sustain_s
```

La polyphonie **voices** limite la durée d’une note :

```
voice_life_time = step_ms * voices / 1000
```

---

# 6. 🔉 **ENVELOPPE**

Enveloppe type linear ramp :

```
fade = fade_ms / 1000

if t < fade:
    env = t / fade
elif t > note_duration - fade:
    env = (note_duration - t) / fade
else:
    env = 1
```

---

# 7. ⚡ **FORME D’ONDE (LUT optimisée)**

Pour éviter de recalculer sin/triangle/saw à chaque oscillateur :

### LUT :

```
table_size = 4096
phase = np.linspace(0, 2π, table_size)
sine_table = sin(phase)
triangle_table = ...
saw_table = ...
square_table = ...
```

### Rendu :

```
index = (phase_accumulator % 1) * table_size
sample = lut_waveform[index]
phase_accumulator += freq / sr
```

*(interpoler linéairement pour moins d’aliasing)*

---

# 8. 🎬 **VIDÉO — Vibration visuelle**

### 8.1 Fréquence → déplacement

Seules les fréquences entre `vis_fmin` et `vis_fmax` sont visualisées :

```
f_norm = clamp((freq - vis_fmin) / (vis_fmax - vis_fmin), 0,1)
amp_px = (vis_amp_pct / 100) * video_width
y_offset = sin(2π * f_norm * t) * amp_px
```

### 8.2 Gaussienne (focus spatial)

```
g_size = gauss_size_pct/100 * video_width
g = exp(-(x - center)^2 / (2 * (g_size/2)^2))
```

### 8.3 Résultat :

```
y_final(x, t) = y_offset(t) * g(x)
```

---

# 9. 🧩 **DÉPENDANCES ENTRE PARAMÈTRES**

### Influence SUR LA DURÉE

* duration-s
* step-ms
* voices
* sustain-s
* size (si pas de duration-s)

### Influence SUR LA TEXTURE SONORE

* waveform
* fmin/fmax
* hsv-detune-pct
* hsv-blend-gray
* hsv-max-octave
* color-mode
* voices (épaisseur)

### Influence SUR LA VIDÉO

* video-size / width / height
* vis-fmin / vis-fmax
* vis-amp-pct
* fps
* gauss-size-pct

---

# 10. 🧪 **EXEMPLES DE CONFIGS ADM**

### Accordéon doux

```
color-mode grayscale
waveform sine
hsv-detune-pct 1.0
hsv-blend-gray 0.15
step-ms 40
voices 32
```

### Drone texturé

```
waveform triangle
color-mode grayscale
fmin 20
fmax 2000
step-ms 80
```

### Synthé coloré (HSV)

```
color-mode hsv-notes
hsv-max-octave 5
hsv-detune-pct 0.5
waveform sine
```

---

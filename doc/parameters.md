# 🎛️ Image2Saw — Carte mentale des paramètres

Deux mondes distincts :
- **AUDIO** → crée la texture sonore
- **VIDÉO** → crée le mouvement visuel synchronisé

Ce schéma aide à comprendre :
- les paramètres qui influencent la **durée**,  
- ceux qui influencent la **texture sonore**,  
- et la différence entre **grayscale** et **HSV**.

---

## 🔊 SECTION AUDIO

```
┌──────────────────────────────────────────────────────────┐
│  ⏱ PARAMÈTRES QUI INFLUENCENT LA DURÉE                  │
└──────────────────────────────────────────────────────────┘
- --duration-s      → durée cible (recalcule taille image audio)
- --step-ms         → cadence du balayage (petit = rapide)
- --voices          → polyphonie (plus de voix = chevauchement)
- --sustain-s       → temps ajouté après la fin
- --fade-ms         → attaque / release de chaque note
- (indirect) --size → si pas de duration-s, fixe le nombre de pixels
```

```
┌──────────────────────────────────────────────────────────┐
│  🎚 PARAMÈTRES QUI INFLUENCENT LE SON (TIMBRE)           │
└──────────────────────────────────────────────────────────┘
- --waveform        → forme d’onde : sine / saw / triangle / square
- --mono            → somme les canaux L/R
- --voices          → densité sonore (plus = plus épais)
```

---

## 🌗 Mode GRAYSCALE (par défaut)
```
┌──────────────────────────────────────────────────────────┐
│   GRAYSCALE = la luminosité détermine la fréquence       │
└──────────────────────────────────────────────────────────┘
- --color-mode grayscale
- fmin / fmax → plage de fréquences
- Image claire → son aigu
- Contraste fort → spectre large

Interactions :
- Durée : seulement impactée si --duration-s modifie la résolution
- Son   : structure dictée par la luminosité pure
```

---

## 🎨 Mode HSV (couleur → musique)
```
┌──────────────────────────────────────────────────────────┐
│   HSV = couleur → note, octave, amplitude                │
└──────────────────────────────────────────────────────────┘
- --color-mode hsv-notes
- HUE   → note (Do..Si)
- VALUE → octave (Do1..Si N)
- SAT   → amplitude (saturation = volume)

Paramètres spécifiques :
- --hsv-max-octave : détermine la hauteur max (ex : 5 → Do1..Si5)
- --hsv-detune-pct : léger vibrato basé sur la teinte (±%)
- --hsv-blend-gray : mix HSV/gris (0=couleur, 1=gris)
```

**Exemple “accordéon organique” :**
```bash
--waveform sine
--hsv-detune-pct 1.0
--hsv-blend-gray 0.15
```

---

## 🖼 Image audio & résolution
```
┌──────────────────────────────────────────────────────────┐
│   RÉSOLUTION AUDIO = nombre d’oscillateurs               │
└──────────────────────────────────────────────────────────┘
- image (entrée)     → base
- --size             → carré N×N (si pas de duration-s)
- --duration-s       → recalcul dynamique en gardant le ratio
- Plus de pixels     → son plus riche, plus détaillé
```

---

# 🎬 SECTION VIDÉO

```
┌──────────────────────────────────────────────────────────┐
│  ACTIVATION & DURÉE                                      │
└──────────────────────────────────────────────────────────┘
- --video             → active la génération vidéo
- --video-out         → nom du fichier
- Durée = durée audio
- --fps               → fluidité (25 recommandé)
```

---

```
┌──────────────────────────────────────────────────────────┐
│  TAILLE / CADRAGE VIDÉO                                  │
└──────────────────────────────────────────────────────────┘
- --video-width / --video-height
    • si un seul côté → ratio conservé
- --video-size (XS/S/M/L/XL)
    • fixe le plus grand côté en pixels
- défaut : taille = taille image audio
```

---

```
┌──────────────────────────────────────────────────────────┐
│  🌊 VIBRATION VISUELLE (liée au son)                     │
└──────────────────────────────────────────────────────────┘
- --vis-fmin / --vis-fmax
    • plage audio utilisée pour la vibration (ex: 1–10 Hz)
- --vis-amp-pct
    • amplitude visuelle (% de la largeur)
- --gauss-size-pct
    • taille du focus gaussien (petit = précis, grand = doux)
```

---

# 🧩 Résumé visuel (ASCII)

```
             +---------------------+
             |       IMAGE         |
             +---------------------+
                        |
                        v
            +------------------------+
            |  IMAGE AUDIO (pixels)  |
            +------------------------+
               |            |
               |            |
      (Durée)  |            |  (Timbre)
               |            |
               v            v
      step-ms, duration   waveform, hsv-detune,
      size, sustain       fmin/fmax, hsv-blend
               \            /
                \          /
                 \        /
                   AUDIO
                     |
                     v
                   WAV
                     |
                     v
        +--------------------------+
        |        VIDÉO (option)    |
        +--------------------------+
               |       |       |
             taille   fps   vibration
```

---


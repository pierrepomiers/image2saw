# -*- coding: utf-8 -*-
"""
audio.py (V3.2, optimisé, vectorisé + LUT)
───────────────────────────────────────────
Planification temporelle + synthèse audio + écriture WAV.

Optimisations CPU :
- Pré-calcul des paramètres oscillateurs dans des vecteurs NumPy.
- Rendu bloc par bloc (batch de frames).
- Pour chaque bloc :
    * on ne parcourt que les oscillateurs ACTIFS
    * les formes d’onde sont lues dans une LUT pré-calculée
      (aucun sin/cos dans la boucle principale).
"""

from __future__ import annotations

import math
import wave
from dataclasses import dataclass
from typing import List, Tuple

import numpy as np
from tqdm import tqdm

from .image_proc import zigzag_indices


# Taille de la LUT pour les formes d'onde (phase dans [0,1))
WAVE_LUT_SIZE = 4096


# ───────────────────────────────
#  Modèle d'oscillateur
# ───────────────────────────────

@dataclass
class Osc:
    """Représente un oscillateur unique (lié à un pixel)."""

    f: float           # fréquence en Hz
    start: float       # temps de démarrage (s)
    end: float         # temps d'arrêt (s)
    pan_l: float       # gain du canal gauche
    pan_r: float       # gain du canal droit


def constant_power_pan(x_norm: float) -> Tuple[float, float]:
    """
    Panning constant-power : 0 = full gauche, 1 = full droite.

    Args:
        x_norm: position horizontale normalisée dans [0,1].

    Returns:
        (gain_left, gain_right)
    """
    theta = (math.pi / 2.0) * x_norm
    return math.cos(theta), math.sin(theta)


# ───────────────────────────────
#  Mapping niveaux de gris -> Hz
# ───────────────────────────────

def map_gray_to_freq(gray: np.ndarray, fmin: float, fmax: float) -> np.ndarray:
    """
    Mappe les niveaux de gris (0–255) vers des fréquences [fmin, fmax].

    Mapping linéaire simple :
        0   -> fmin
        255 -> fmax
    """
    gray_f = gray.astype(np.float64)
    return fmin + (gray_f / 255.0) * (fmax - fmin)


# ───────────────────────────────
#  Planification temporelle
# ───────────────────────────────

def plan_schedule(
    freqs: np.ndarray,
    size: int,
    sr: int,
    step_ms: float,
    sustain_s: float,
    stereo: bool,
    voices: int,
) -> Tuple[List[Osc], float]:
    """
    Crée une liste d’oscillateurs (un par pixel) avec :
    - fréquence issue du pixel
    - temps de début/fin calculés à partir du décalage (step)
    - durée de vie dépendant du nombre de voix simultanées (voices)

    Notes V3.2 :
    - L'argument `size` est conservé pour compatibilité,
      mais les dimensions réelles proviennent de `freqs.shape` (support non-carré).
    - Le panning stéréo utilise la position horizontale réelle (w).
    """
    h, w = freqs.shape
    N = freqs.size
    step_s = step_ms / 1000.0

    # Durée de vie de chaque oscillateur : fenêtre de `voices` steps.
    # À tout instant, au plus `voices` oscillateurs sont actifs.
    # Durée totale théorique :
    T = (N - 1 + voices) * step_s + sustain_s

    # Coordonnées horizontales normalisées pour le panning
    if w > 1:
        x_positions = np.linspace(0.0, 1.0, w)
    else:
        x_positions = np.array([0.5])

    # Pré-calcul du panning par colonne
    pan_cache: List[Tuple[float, float]] = []
    for x in x_positions:
        if stereo:
            pl, pr = constant_power_pan(float(x))
        else:
            pl = pr = 1.0
        pan_cache.append((pl, pr))

    # Parcours zigzag pour l'ordre des oscillateurs
    order = zigzag_indices(h, w)

    oscs: List[Osc] = []
    for i, (r, c) in enumerate(order):
        f = float(freqs[r, c])
        start = i * step_s
        end = (i + voices) * step_s  # durée fixe pour tous

        pl, pr = pan_cache[c]
        oscs.append(Osc(f=f, start=start, end=end, pan_l=pl, pan_r=pr))

    return oscs, T


# ───────────────────────────────
#  LUT de formes d'onde
# ───────────────────────────────

def _make_waveform_lut(waveform: str) -> np.ndarray:
    """Construit une LUT 1D pour la forme d'onde demandée."""
    x = np.linspace(0.0, 1.0, WAVE_LUT_SIZE, endpoint=False)

    if waveform == "sine":
        y = np.sin(2.0 * math.pi * x)
    elif waveform == "saw":
        # dent de scie de -1 à 1
        y = 2.0 * (x - 0.5)
    elif waveform == "triangle":
        # triangle de -1 à 1
        y = np.where(x < 0.5, 4.0 * x - 1.0, 3.0 - 4.0 * x)
    elif waveform == "square":
        y = np.where(x < 0.5, 1.0, -1.0)
    else:
        # fallback : sinus
        y = np.sin(2.0 * math.pi * x)

    return y.astype(np.float64)


def _waveform_from_lut(phase: np.ndarray, lut: np.ndarray) -> np.ndarray:
    """
    Retourne la forme d'onde en utilisant une LUT pré-calculée.

    phase : tableau de phases fractionnaires dans [0,1)
    lut   : tableau 1D de taille WAVE_LUT_SIZE
    """
    size = lut.shape[0]
    idx = np.floor(phase * size).astype(np.int64)
    idx %= size
    return lut[idx]


# ───────────────────────────────
#  Rendu audio
# ───────────────────────────────

def render_audio(
    oscs: List[Osc],
    sr: int,
    block_ms: float,
    fade_ms: float,
    waveform: str,
    tqdm_desc: str = "Rendu audio",
) -> np.ndarray:
    """
    Rendu audio bloc par bloc, en utilisant une LUT pour la forme d'onde.

    Args:
        oscs: liste d'oscillateurs planifiés (Osc).
        sr: fréquence d'échantillonnage.
        block_ms: taille d'un bloc en ms.
        fade_ms: durée du fade in/out par oscillateur pour éviter les clics.
        waveform: forme d'onde ('sine', 'saw', 'triangle', 'square').
        tqdm_desc: texte pour la barre de progression.

    Returns:
        np.ndarray de forme (n_samples, 2) en float64 (stéréo).
    """
    if not oscs:
        return np.zeros((0, 2), dtype=np.float64)

    # Durée totale = fin du dernier oscillateur
    T = max(o.end for o in oscs)
    n_samples = int(math.ceil(T * sr))

    audio_l = np.zeros(n_samples, dtype=np.float64)
    audio_r = np.zeros(n_samples, dtype=np.float64)

    # Pré-calculs vectoriels
    f = np.array([o.f for o in oscs], dtype=np.float64)
    start_s = np.array([o.start for o in oscs], dtype=np.float64)
    end_s = np.array([o.end for o in oscs], dtype=np.float64)
    pan_l = np.array([o.pan_l for o in oscs], dtype=np.float64)
    pan_r = np.array([o.pan_r for o in oscs], dtype=np.float64)

    start_idx = (start_s * sr).astype(np.int64)
    end_idx = (end_s * sr).astype(np.int64)
    end_idx = np.clip(end_idx, 0, n_samples)

    # LUT de forme d'onde
    lut = _make_waveform_lut(waveform)

    # Nombre d'échantillons par bloc
    block_size = max(1, int(sr * block_ms / 1000.0))

    # Fade par oscillateur
    fade_samples = max(1, int(sr * fade_ms / 1000.0))

    # Boucle principale par blocs
    n_blocks = (n_samples + block_size - 1) // block_size

    for b in tqdm(range(n_blocks), desc=tqdm_desc):
        n0 = b * block_size
        n1 = min(n_samples, (b + 1) * block_size)
        if n0 >= n1:
            continue

        # Oscillateurs actifs sur ce bloc (indices d'échantillons)
        active = (start_idx < n1) & (end_idx > n0)
        active_idx = np.nonzero(active)[0]
        if active_idx.size == 0:
            continue

        for k in active_idx:
            s0 = start_idx[k]
            s1 = end_idx[k]
            if s1 <= s0:
                continue

            # Recoupe avec le bloc courant
            ls = max(n0, s0)
            le = min(n1, s1)
            if le <= ls:
                continue

            n_global = np.arange(ls, le, dtype=np.float64)

            # Phase fractionnaire dans [0,1)
            phase = (f[k] * (n_global / sr - start_s[k])) % 1.0

            # Forme d'onde via LUT
            wave_seg = _waveform_from_lut(phase, lut)

            # Enveloppe de fade in/out par oscillateur
            total_len = s1 - s0
            pos = n_global - s0  # position relative dans la vie de l'oscillateur

            env = np.ones_like(wave_seg)
            # Fade-in
            m_in = pos < fade_samples
            env[m_in] *= pos[m_in] / fade_samples

            # Fade-out
            remaining = total_len - pos
            m_out = remaining < fade_samples
            env[m_out] *= remaining[m_out] / fade_samples

            wave_seg *= env

            # Accumulation dans les canaux
            audio_l[ls:le] += wave_seg * pan_l[k]
            audio_r[ls:le] += wave_seg * pan_r[k]

    return np.stack([audio_l, audio_r], axis=-1)


# ───────────────────────────────
#  Écriture WAV
# ───────────────────────────────

def write_wav_int16_stereo(path: str, sr: int, data_lr: np.ndarray):
    """Écrit un fichier WAV 16-bit PCM stéréo."""
    if data_lr.ndim != 2 or data_lr.shape[1] != 2:
        raise ValueError("data_lr doit être un tableau (n_samples, 2).")

    peak = float(np.max(np.abs(data_lr))) if data_lr.size > 0 else 1.0
    norm = 1.0 if peak == 0 else min(1.0, 0.999 / peak)
    data_i16 = (data_lr * norm * 32767.0).astype(np.int16)

    with wave.open(path, "wb") as wf:
        wf.setnchannels(2)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(data_i16.tobytes())


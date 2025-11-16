# -*- coding: utf-8 -*-
"""
audio.py
────────
Planification temporelle + synthèse audio + écriture WAV.

Reprend la logique de Image2Saw v2.9 :
- Osc par pixel
- fenêtre glissante (--voices)
- rendu bloc par bloc (--block-ms)
- enveloppe d’attaque/relâche (--fade-ms)
- spatialisation stéréo constant-power (--stereo / --mono)
"""

import math
import wave
from dataclasses import dataclass
from typing import List, Tuple

import numpy as np

from .image_proc import zigzag_indices


@dataclass
class Osc:
    """Représente un oscillateur unique (lié à un pixel)."""
    f: float           # fréquence en Hz
    start: float       # temps de démarrage (s)
    end: float         # temps d'arrêt (s)
    pan_l: float       # gain du canal gauche
    pan_r: float       # gain du canal droit


def constant_power_pan(x_norm: float) -> Tuple[float, float]:
    """Panning constant-power : 0 = full gauche, 1 = full droite."""
    theta = (math.pi / 2.0) * x_norm
    return math.cos(theta), math.sin(theta)


def map_gray_to_freq(gray: np.ndarray, fmin: float, fmax: float) -> np.ndarray:
    """Mappe les niveaux de gris (0–255) vers des fréquences [fmin, fmax]."""
    return fmin + (gray.astype(np.float64) / 255.0) * (fmax - fmin)


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
    """
    h = w = size
    N = freqs.size
    step_s = step_ms / 1000.0

    # Fin "naturelle" de la fenêtre glissante :
    # dernier osc (i=N-1) se termine à (N-1 + voices) * step_s
    T_base = (N - 1 + voices) * step_s if N > 0 else 0.0

    # On ajoute éventuellement un sustain global à la toute fin
    T = T_base + sustain_s

    pan_cache = (
        [constant_power_pan(c / (w - 1 if w > 1 else 1.0)) for c in range(w)]
        if stereo
        else [(1.0, 1.0)] * w
    )

    order = zigzag_indices(h, w)
    oscs: List[Osc] = []

    for i, (r, c) in enumerate(order):
        f = float(freqs[r, c])
        start = i * step_s
        end = (i + voices) * step_s  # durée fixe pour tous

        pl, pr = pan_cache[c]
        oscs.append(Osc(f=f, start=start, end=end, pan_l=pl, pan_r=pr))

    return oscs, T


def generate_waveform(phase: np.ndarray, waveform: str) -> np.ndarray:
    """Crée la forme d’onde audio choisie, normalisée dans [-1, 1]."""
    if waveform == "saw":
        return 2.0 * phase - 1.0
    elif waveform == "sine":
        return np.sin(2.0 * np.pi * phase)
    elif waveform == "triangle":
        return 2.0 * np.abs(2.0 * (phase - np.floor(phase + 0.5))) - 1.0
    elif waveform == "square":
        return np.where(phase < 0.5, 1.0, -1.0)
    else:
        raise ValueError(f"Forme d'onde inconnue : {waveform}")


def render_audio(
    oscs: List[Osc],
    T: float,
    sr: int,
    block_ms: float,
    mono: bool,
    waveform: str,
    fade_ms: float,
    voices: int,
    tqdm_desc: str = "Rendu audio",
):
    """
    Synthèse audio bloc par bloc.
    Chaque bloc contient la somme des oscillateurs actifs.
    Une enveloppe d’attaque/relâche demi-cosinus est appliquée pour éviter les clics.
    """
    from tqdm import tqdm  # import local pour éviter dépendance globale

    n_total = int(math.ceil(T * sr))
    n_block = max(1, int(sr * (block_ms / 1000.0)))
    outL = np.zeros(n_total, dtype=np.float64)
    outR = np.zeros(n_total, dtype=np.float64)

    # Ajustement du volume selon le nombre de voix simultanées
    per_osc_gain = 1.0 / math.sqrt(voices) * 0.95

    blocks = int(math.ceil(n_total / n_block))
    for b in tqdm(range(blocks), desc=tqdm_desc, unit="bloc"):
        s0 = b * n_block
        s1 = min(n_total, (b + 1) * n_block)
        t0, t1 = s0 / sr, s1 / sr

        bufL = np.zeros(s1 - s0, dtype=np.float64)
        bufR = np.zeros(s1 - s0, dtype=np.float64)

        for osc in oscs:
            if osc.start >= t1 or osc.end <= t0:
                continue

            k0 = max(0, int(math.floor((osc.start - t0) * sr)))
            k1 = min(s1 - s0, int(math.ceil((osc.end - t0) * sr)))
            if k1 <= k0:
                continue

            idx = np.arange(k0, k1, dtype=np.float64)
            t_rel = (t0 + idx / sr) - osc.start
            frac = np.mod(t_rel * osc.f, 1.0)
            sig = generate_waveform(frac, waveform)

            # Enveloppe anti-click (fade-in/out)
            s_start = int(round(osc.start * sr))
            s_end = int(round(osc.end * sr))
            seg_len = max(1, s_end - s_start)
            nf = int(sr * (fade_ms / 1000.0))
            nf = min(nf, seg_len // 2)
            if nf > 0:
                env = np.ones_like(sig)
                abs_idx = s0 + idx.astype(np.int64)
                d_start = abs_idx - s_start
                d_end = s_end - abs_idx

                m_in = (d_start < nf)
                if np.any(m_in):
                    env[m_in] = 0.5 * (1.0 - np.cos(np.pi * (d_start[m_in] / nf)))

                m_out = (d_end <= nf)
                if np.any(m_out):
                    env[m_out] *= 0.5 * (1.0 - np.cos(np.pi * (d_end[m_out] / nf)))

                sig *= env

            sig *= per_osc_gain

            if mono:
                bufL[k0:k1] += sig
            else:
                bufL[k0:k1] += sig * osc.pan_l
                bufR[k0:k1] += sig * osc.pan_r

        outL[s0:s1] += bufL
        outR[s0:s1] += bufL if mono else bufR

    return np.stack([outL, outR], axis=1)


def write_wav_int16_stereo(path: str, sr: int, data_lr: np.ndarray):
    """Écrit un fichier WAV 16-bit PCM stéréo."""
    peak = np.max(np.abs(data_lr)) if data_lr.size > 0 else 1.0
    norm = 1.0 if peak == 0 else min(1.0, 0.999 / peak)
    data_lr = (data_lr * norm * 32767.0).astype(np.int16)

    with wave.open(path, "wb") as wf:
        wf.setnchannels(2)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(data_lr.tobytes())


# -*- coding: utf-8 -*-
"""
audio.py (optimisé, vectorisé + LUT)
────────────────────────────────────
Planification temporelle + synthèse audio + écriture WAV.

Optimisations CPU :
- Pré-calcul des paramètres oscillateurs dans des vecteurs NumPy.
- Rendu bloc par bloc (batch de frames).
- Pour chaque bloc :
    * on ne parcourt que les oscillateurs ACTIFS (≤ voices)
    * les formes d’onde sont lues dans une LUT pré-calculée
      (aucun sin/cos dans la boucle principale).
"""

import math
import wave
from dataclasses import dataclass
from typing import List, Tuple

import numpy as np

from .image_proc import zigzag_indices


# Taille de la LUT pour les formes d'onde (phase dans [0,1))
WAVE_LUT_SIZE = 4096


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


# ───────────────────────────────
#  LUT de formes d'onde
# ───────────────────────────────

def _build_waveform_lut(waveform: str, size: int = WAVE_LUT_SIZE) -> np.ndarray:
    """
    Construit une LUT de forme d'onde pour des phases dans [0,1).
    size : nombre d'échantillons dans la LUT.
    """
    # Phase fractionnaire dans [0,1), sans inclure 1.0
    phase = np.linspace(0.0, 1.0, num=size, endpoint=False, dtype=np.float64)

    wf = waveform.lower()
    if wf == "saw":
        lut = 2.0 * phase - 1.0
    elif wf == "sine":
        lut = np.sin(2.0 * np.pi * phase)
    elif wf == "triangle":
        lut = 2.0 * np.abs(2.0 * (phase - np.floor(phase + 0.5))) - 1.0
    elif wf == "square":
        lut = np.where(phase < 0.5, 1.0, -1.0)
    else:
        raise ValueError(f"Forme d'onde inconnue pour la LUT : {waveform}")

    return lut.astype(np.float64)


def _waveform_from_lut(phase: np.ndarray, lut: np.ndarray) -> np.ndarray:
    """
    Retourne la forme d'onde en utilisant une LUT pré-calculée.

    phase : tableau de phases fractionnaires dans [0,1)
            (n'importe quelle forme/shape)
    lut   : tableau 1D de taille WAVE_LUT_SIZE
    """
    size = lut.shape[0]
    # On projette la phase dans [0, size), puis on prend le floor
    idx = np.floor(phase * size).astype(np.int64)
    # Sécurité : clamp dans [0, size-1]
    np.clip(idx, 0, size - 1, out=idx)
    return lut[idx]


# ───────────────────────────────
#  Rendu audio vectorisé + LUT
# ───────────────────────────────

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
    Synthèse audio bloc par bloc (batch de frames).

    Optimisation :
      - On pré-calcul les données des oscillateurs dans des vecteurs NumPy.
      - On pré-calcul une LUT de forme d'onde pour éviter les sin/cos
        pendant le rendu.
      - Pour chaque bloc [s0, s1), on ne parcourt que les oscillateurs
        réellement actifs (liste current_active de taille ≤ voices).
      - Le corps du calcul (phases + waveform) se fait en vectoriel.

    Le rendu reste équivalent à la version sans LUT,
    avec une légère quantification de phase (WAVE_LUT_SIZE steps).
    """
    from tqdm import tqdm  # import local pour éviter dépendance globale

    n_total = int(math.ceil(T * sr))
    n_block = max(1, int(sr * (block_ms / 1000.0)))

    outL = np.zeros(n_total, dtype=np.float64)
    outR = np.zeros(n_total, dtype=np.float64)

    # Ajustement du volume selon le nombre de voix simultanées
    per_osc_gain = 1.0 / math.sqrt(voices) * 0.95 if voices > 0 else 1.0

    n_osc = len(oscs)

    if n_osc == 0 or n_total == 0:
        return np.stack([outL, outR], axis=1)

    # ─────────────────────────────────────────────
    # Pré-calcul : vecteurs d'oscillateurs
    # ─────────────────────────────────────────────
    f_arr = np.empty(n_osc, dtype=np.float64)
    start_s_arr = np.empty(n_osc, dtype=np.float64)
    end_s_arr = np.empty(n_osc, dtype=np.float64)
    pan_l_arr = np.empty(n_osc, dtype=np.float64)
    pan_r_arr = np.empty(n_osc, dtype=np.float64)

    for i, osc in enumerate(oscs):
        f_arr[i] = osc.f
        start_s_arr[i] = osc.start
        end_s_arr[i] = osc.end
        pan_l_arr[i] = osc.pan_l
        pan_r_arr[i] = osc.pan_r

    # Passages en indices d’échantillons
    start_samples = np.round(start_s_arr * sr).astype(np.int64)
    end_samples = np.round(end_s_arr * sr).astype(np.int64)

    # Fade en nombre d'échantillons (max, commun)
    nf = int(sr * (fade_ms / 1000.0))
    nf = max(nf, 0)

    # LUT de forme d'onde (une seule fois pour tout le rendu)
    lut = _build_waveform_lut(waveform, size=WAVE_LUT_SIZE)

    # ─────────────────────────────────────────────
    # Balayage bloc par bloc
    # ─────────────────────────────────────────────
    blocks = int(math.ceil(n_total / n_block))

    current_active: List[int] = []   # indices d'oscillateurs actifs
    next_osc = 0                     # prochain oscillateur à activer (par start_time)

    for b in tqdm(range(blocks), desc=tqdm_desc, unit="bloc"):
        s0 = b * n_block
        s1 = min(n_total, (b + 1) * n_block)
        if s1 <= s0:
            continue

        L = s1 - s0

        bufL = np.zeros(L, dtype=np.float64)
        bufR = np.zeros(L, dtype=np.float64)

        # ─────────────────────────────────────────
        # 1) Ajouter les oscillateurs qui démarrent avant la fin du bloc
        # ─────────────────────────────────────────
        while next_osc < n_osc and start_samples[next_osc] < s1:
            current_active.append(next_osc)
            next_osc += 1

        # ─────────────────────────────────────────
        # 2) Retirer ceux qui sont déjà finis avant le début du bloc
        # ─────────────────────────────────────────
        if current_active:
            current_active = [i for i in current_active if end_samples[i] > s0]

        if not current_active:
            outL[s0:s1] += bufL
            outR[s0:s1] += bufR
            continue

        # ─────────────────────────────────────────
        # 3) Calcul vectorisé pour les oscillateurs actifs
        # ─────────────────────────────────────────
        idx_active = np.array(current_active, dtype=np.int64)
        M = idx_active.size

        # Indices d’échantillons globaux pour ce bloc
        abs_idx = np.arange(s0, s1, dtype=np.int64)            # (L,)
        t_block = abs_idx.astype(np.float64) / float(sr)       # (L,)

        start_act = start_samples[idx_active]  # (M,)
        end_act = end_samples[idx_active]      # (M,)
        f_act = f_arr[idx_active]              # (M,)
        panL_act = pan_l_arr[idx_active]       # (M,)
        panR_act = pan_r_arr[idx_active]       # (M,)

        # Masque temps actif pour chaque osc sur ce bloc : (M, L)
        active_mask = (abs_idx[None, :] >= start_act[:, None]) & (
            abs_idx[None, :] < end_act[:, None]
        )

        # Temps relatif par rapport au début de l'oscillateur, en secondes
        t_rel = t_block[None, :] - (start_act[:, None].astype(np.float64) / float(sr))

        # Fraction de phase [0,1)
        frac = np.mod(t_rel * f_act[:, None], 1.0)

        # Formes d’onde via LUT (M, L)
        sigs = _waveform_from_lut(frac, lut)

        # On met à zéro en dehors de la fenêtre de chaque osc
        sigs *= active_mask

        # ─────────────────────────────────────
        #  Enveloppe anti-click (fade-in/out)
        # ─────────────────────────────────────
        if nf > 0:
            seg_len = (end_act - start_act)               # (M,)
            nf_local = np.minimum(nf, seg_len // 2)       # (M,)

            # d_start, d_end pour tous les oscs et toutes les frames (M, L)
            d_start = abs_idx[None, :] - start_act[:, None]
            d_end = end_act[:, None] - abs_idx[None, :]

            # On applique fade-in/fade-out osc par osc (M est petit : ≤ voices)
            for j in range(M):
                nfj = int(nf_local[j])
                if nfj <= 0:
                    continue

                ds = d_start[j]  # (L,)
                de = d_end[j]    # (L,)

                env = np.ones(L, dtype=np.float64)

                # Fade-in
                m_in = ds < nfj
                if np.any(m_in):
                    env[m_in] = 0.5 * (
                        1.0 - np.cos(np.pi * (ds[m_in] / nfj))
                    )

                # Fade-out
                m_out = de <= nfj
                if np.any(m_out):
                    env[m_out] *= 0.5 * (
                        1.0 - np.cos(np.pi * (de[m_out] / nfj))
                    )

                sigs[j] *= env

        # Gain global en fonction du nombre de voix
        sigs *= per_osc_gain

        # Accumulation L/R vectorisée
        if mono:
            # Mono : R = L
            bufL += np.sum(sigs, axis=0)
        else:
            bufL += np.sum(sigs * panL_act[:, None], axis=0)
            bufR += np.sum(sigs * panR_act[:, None], axis=0)

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


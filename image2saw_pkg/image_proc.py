# -*- coding: utf-8 -*-
"""
image_proc.py
─────────────
Utilitaires liés au traitement d'image :
- conversion en niveaux de gris
- calcul de tailles non carrées en respectant le ratio
- parcours zigzag
"""

from typing import List, Tuple, Optional

import math
import numpy as np
from PIL import Image, ImageOps

def compute_audio_image_shape_from_duration(
    duration_s: float,
    step_ms: float,
    sustain_s: float,
    voices: int,
    orig_width: int,
    orig_height: int,
) -> Tuple[int, int]:
    """
    Calcule (width, height) de l'image utilisée pour le son, en :

      - respectant au mieux le ratio de l'image d'origine
      - utilisant la même logique que la V3.1 pour le nombre d'oscillateurs N

    Logique :
        On part de la durée cible T_target (= duration_s), du step entre oscillateurs
        et de la durée de sustain, comme dans la V3.1 :

            step_s  = step_ms / 1000
            sweep_T = duration_s - sustain_s
            N      ≈ (sweep_T / step_s) - voices + 1

        N est le nombre d'oscillateurs / pixels "utiles". Au lieu de tout forcer
        dans un carré (size x size), on cherche un couple (w, h) tel que :

            w * h ≈ N
            w / h ≈ ratio_original  (w/h ~ orig_width/orig_height)

    Args:
        duration_s: durée cible totale du rendu (audio + vidéo).
        step_ms: décalage entre oscillateurs (ms).
        sustain_s: durée de maintien après le dernier oscillateur (s).
        voices: nombre de voix actives (polyphonie interne).
        orig_width, orig_height: dimensions originales de l'image source.

    Returns:
        (width, height) : dimensions entières >= 1.
    """
    step_s = step_ms / 1000.0
    sweep_T = duration_s - sustain_s

    # Nombre d’oscillateurs cible (même formule que V3.1)
    N = (sweep_T / step_s) - voices + 1
    N = max(1, round(N))

    # Ratio d'origine (fallback 1.0 si hauteur nulle par sécurité)
    r = orig_width / orig_height if orig_height != 0 else 1.0

    # On cherche width * height ≈ N avec width / height ≈ r
    # En continu :
    #   h = sqrt(N / r)
    #   w = r * h
    height_f = math.sqrt(N / r)
    width_f = r * height_f

    height = max(1, int(round(height_f)))
    width = max(1, int(round(width_f)))

    return width, height


def compute_video_output_shape(
    video_width: Optional[int],
    video_height: Optional[int],
    orig_width: int,
    orig_height: int,
) -> Tuple[int, int]:
    """
    Calcule la taille finale (width, height) de la vidéo.

    Règles :
      - Si width ET height sont fournis  → mode STRETCH (déformation assumée).
      - Si un seul est fourni            → on respecte le ratio de l'image d'origine.
      - Si aucun n'est fourni            → on renvoie la taille originale.

    Les valeurs <= 0 sont traitées comme "non fournies".
    """
    # Normalisation des valeurs invalides
    if video_width is not None and video_width <= 0:
        video_width = None
    if video_height is not None and video_height <= 0:
        video_height = None

    # Rien de spécifié → taille d’origine
    if video_width is None and video_height is None:
        return orig_width, orig_height

    # Cas où les deux sont fournis : STRETCH (pas de respect du ratio)
    if video_width is not None and video_height is not None:
        return max(1, int(video_width)), max(1, int(video_height))

    # Ratio source (fallback 1.0 si hauteur nulle)
    r = orig_width / orig_height if orig_height != 0 else 1.0

    # Un seul paramètre → on conserve le ratio
    if video_width is not None:
        width = max(1, int(video_width))
        height_f = width / r
        height = max(1, int(round(height_f)))
        return width, height

    # Sinon on a seulement video_height
    height = max(1, int(video_height))  # type: ignore[arg-type]
    width_f = height * r
    width = max(1, int(round(width_f)))
    return width, height


def zigzag_indices(h: int, w: int) -> List[Tuple[int, int]]:
    """
    Renvoie les indices (r,c) pour une lecture zigzag
    (ligne paire gauche→droite, impaire droite→gauche).
    """
    idx = []
    for r in range(h):
        cols = range(w) if r % 2 == 0 else range(w - 1, -1, -1)
        for c in cols:
            idx.append((r, c))
    return idx


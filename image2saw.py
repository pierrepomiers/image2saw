#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
────────────────────────────────────────────
 Image2Saw v3.0  (audio + vidéo streaming)
────────────────────────────────────────────
Point d'entrée CLI.

Transforme une image en texture sonore générée par des oscillateurs en dents de scie,
sinusoïdaux, triangulaires ou carrés. Chaque pixel devient une voix dont la fréquence
est déterminée par sa luminosité.

Auteurs : Pierre Pomiers (concept) / GPT-5 (implémentation)
Licence : MIT
Date : Novembre 2025
────────────────────────────────────────────
"""

import math

def compute_audio_image_shape_from_duration(
    duration_s: float,
    step_ms: float,
    sustain_s: float,
    voices: int,
    orig_width: int,
    orig_height: int,
):
    """
    Calcule (width, height) de l'image utilisée pour le son, en :
      - respectant au mieux le ratio de l'image d'origine
      - utilisant la même logique que la V3.1 pour le nombre d'oscillateurs N

    duration_s : durée cible (--duration-s)
    step_ms    : step entre oscillateurs (--step-ms)
    sustain_s  : durée de sustain en secondes (--sustain-s)
    voices     : polyphonie interne (--voices)
    orig_width, orig_height : taille d'origine de l'image (PIL)
    """

    step_s = step_ms / 1000.0
    sweep_T = duration_s - sustain_s

    # Nombre d’oscillateurs cible (même formule V3.1)
    N = (sweep_T / step_s) - voices + 1
    N = max(1, round(N))

    # Ratio d'origine
    r = orig_width / orig_height if orig_height != 0 else 1.0

    # On cherche width * height ≈ N avec width / height ≈ r
    height_f = math.sqrt(N / r)
    width_f = r * height_f

    height = max(1, int(round(height_f)))
    width = max(1, int(round(width_f)))

    return width, height


def compute_video_output_shape(
    video_width,
    video_height,
    orig_width,
    orig_height,
):
    """
    Calcule la taille finale (width, height) de la vidéo.

    Règles :
      - Si width ET height sont fournis  → mode STRETCH (déformation assumée).
      - Si un seul est fourni            → on respecte le ratio de l'image d'origine.
      - Si aucun n'est fourni            → on renvoie la taille originale.
    """

    # Rien de spécifié → taille d’origine
    if (not video_width or video_width <= 0) and (not video_height or video_height <= 0):
        return orig_width, orig_height

    # Cas où les deux sont fournis : STRETCH
    if video_width and video_height:
        return max(1, int(video_width)), max(1, int(video_height))

    # Ratio source
    r = orig_width / orig_height if orig_height != 0 else 1.0

    # Un seul paramètre → on conserve le ratio
    if video_width:
        height = max(1, int(round(video_width / r)))
        return int(video_width), height
    else:
        width = max(1, int(round(video_height * r)))
        return width, int(video_height)

from image2saw_pkg.cli import main

if __name__ == "__main__":
    main()


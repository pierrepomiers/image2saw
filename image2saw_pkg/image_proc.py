# -*- coding: utf-8 -*-
"""
image_proc.py
─────────────
Utilitaires liés au traitement d'image :
- conversion en niveaux de gris
- redimensionnement carré (LANCZOS)
- parcours zigzag
"""

from typing import List, Tuple

import numpy as np
from PIL import Image, ImageOps


def load_image_to_gray_square(path: str, size: int) -> np.ndarray:
    """
    Charge une image, la redimensionne en carré (LANCZOS) et la convertit en niveaux de gris.

    Args:
        path: chemin de l'image
        size: taille du côté carré logique (ex: 128)

    Returns:
        np.ndarray uint8 de forme (size, size), valeurs 0–255
    """
    img = Image.open(path).convert("L")
    img = ImageOps.fit(
        img,
        (size, size),
        method=Image.LANCZOS,   # audio : rendu plus doux
        centering=(0.5, 0.5),
    )
    return np.asarray(img, dtype=np.uint8)


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


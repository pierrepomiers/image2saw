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

from image2saw_pkg.cli import main

if __name__ == "__main__":
    main()


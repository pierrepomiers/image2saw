# -*- coding: utf-8 -*-
"""
video.py (V3.2.1, profil cosinus + déplacement horizontal)
───────────────────────────────────────────────────────────
Rendu vidéo avec :

- pixel art COULEUR basé sur l'image source,
- ratio issu de la grille audio (freqs),
- support de --video-width / --video-height,
- balayage zigzag synchronisé avec l'audio,
- déformation locale (vibration) radiale EN AMPLITUDE, mais
  déplacement UNIQUEMENT HORIZONTAL (pas radial),
- fréquence visuelle mappée depuis la fréquence AUDIO locale :
    f_audio in [fmin, fmax] → f_vis in [vis-fmin, vis-fmax]

MoviePy est importé tardivement (optionnel) et l'encodage
est compatible QuickTime (H.264 + yuv420p, width/height pairs).
"""

import math
from typing import Any, Tuple

import numpy as np
from PIL import Image

from .image_proc import compute_video_output_shape, zigzag_indices


def _compute_sigma_from_gauss_size(video_width: int, gauss_size_pct: float) -> float:
    """
    Calcule un sigma de référence à partir d'un diamètre exprimé
    en % de la largeur vidéo. Servira à fixer un rayon R pour le profil cosinus.
    """
    diameter_px = (gauss_size_pct / 100.0) * float(video_width)
    if diameter_px <= 0:
        diameter_px = float(video_width)

    radius_px = diameter_px * 0.5
    sigma = max(1.0, radius_px * 0.5)
    return sigma


def _make_pixel_art_base_from_color(
    image_path: str,
    freqs_shape: Tuple[int, int],
    video_width: int,
    video_height: int,
) -> np.ndarray:
    """
    Construit l'image de base "pixel art COULEUR" :

    - on charge l'image source en RGB
    - on la redimensionne à la taille de la grille audio (Hf, Wf = freqs.shape)
      → chaque "pixel audio" correspond à un bloc de couleur.
    - on upscale en NEAREST vers (video_width, video_height)
      → gros pixels bien nets (pixel art).
    """
    Hf, Wf = freqs_shape

    img_src = Image.open(image_path).convert("RGB")
    img_small = img_src.resize((Wf, Hf), Image.LANCZOS)   # grille logique couleur
    img_video = img_small.resize((video_width, video_height), Image.NEAREST)

    base = np.array(img_video, dtype=np.float32)
    return base


def generate_video_from_args(
    args: Any,
    freqs: np.ndarray,
    out_wav: str,
    default_video_out: str,
) -> None:
    """Génère une vidéo à partir des paramètres CLI + matrice de fréquences.

    args :
        - contient notamment : image, fps, vis_fmin, vis_fmax, vis_amp_pct,
          gauss_size_pct, video_width, video_height, sustain_s, fmin, fmax, etc.
    freqs :
        - matrice 2D des fréquences (même logique que pour l'audio, non carrée possible)
    out_wav :
        - chemin du fichier WAV déjà généré
    default_video_out :
        - chemin du fichier vidéo de sortie
    """
    # Import tardif de MoviePy → évite l'erreur si on ne fait pas de vidéo
    try:
        from moviepy.editor import VideoClip, AudioFileClip
    except ImportError as e:
        raise RuntimeError(
            "La génération vidéo (--video) nécessite le paquet 'moviepy'.\n"
            "Installe-le avec :\n"
            "    python3 -m pip install moviepy imageio-ffmpeg\n"
            "Ou relance la commande sans l'option --video."
        ) from e

    video_out_path = default_video_out

    # Ratio / taille vidéo basés sur la grille audio (freqs)
    Hf, Wf = freqs.shape
    orig_w, orig_h = Wf, Hf

    # Taille finale vidéo (en respectant ou non le ratio selon les options)
    video_w, video_h = compute_video_output_shape(
        video_width=args.video_width,
        video_height=args.video_height,
        orig_width=orig_w,
        orig_height=orig_h,
    )

    # libx264 + yuv420p imposent que width/height soient pairs
    if video_w % 2 != 0:
        video_w -= 1
    if video_h % 2 != 0:
        video_h -= 1
    if video_w < 2:
        video_w = 2
    if video_h < 2:
        video_h = 2

    # Chargement audio
    try:
        audio_clip = AudioFileClip(out_wav)
    except Exception as e:
        raise RuntimeError(f"Impossible de charger le fichier audio '{out_wav}': {e}") from e

    duration_s = float(audio_clip.duration)

    # Image de base pixel art COULEUR (grille audio upscalée)
    base = _make_pixel_art_base_from_color(
        image_path=args.image,
        freqs_shape=freqs.shape,
        video_width=video_w,
        video_height=video_h,
    )  # (h, w, 3)
    h, w, _ = base.shape

    # Grilles de coordonnées
    xs, ys = np.meshgrid(
        np.arange(w, dtype=np.float32),
        np.arange(h, dtype=np.float32),
        indexing="xy",
    )

    sigma = _compute_sigma_from_gauss_size(video_width=w, gauss_size_pct=args.gauss_size_pct)

    # Paramètres de la vibration
    amp_pixels = (args.vis_amp_pct / 100.0) * float(w)
    vis_fmin = float(args.vis_fmin)
    vis_fmax = float(args.vis_fmax)

    # Infos liées aux oscillateurs / ordre zigzag
    N = freqs.size
    order = zigzag_indices(Hf, Wf)

    if N <= 1:
        # Cas dégénéré : on reste centré
        order = [(Hf // 2, Wf // 2)]
        N = 1

    # Durée active (sans le sustain final) pour la progression de la fenêtre
    sweep_T = max(duration_s - float(getattr(args, "sustain_s", 0.0)), 0.001)

    def make_frame(t: float) -> np.ndarray:
        # On borne le temps dans [0, duration_s]
        t_clamped = max(0.0, min(float(t), duration_s))

        # Phase de progression de la fenêtre dans le temps (0→1 sur sweep_T)
        if sweep_T > 0:
            phase = min(t_clamped / sweep_T, 1.0)
        else:
            phase = 1.0

        # Index flottant dans l'ordre zigzag
        idx_float = phase * float(N - 1)
        idx = int(round(idx_float))
        idx = max(0, min(idx, N - 1))

        r, c = order[idx]

        # Position de base du centre dans les coordonnées vidéo
        cx_base = (c + 0.5) / float(Wf) * w
        cy_base = (r + 0.5) / float(Hf) * h

        # 🔥 Fréquence audio locale → fréquence visuelle
        f_audio = float(freqs[r, c])

        if args.fmax <= args.fmin:
            # cas dégénéré : fréquence visuelle constante
            f_vis = vis_fmin
        else:
            rel = (f_audio - args.fmin) / (args.fmax - args.fmin)
            # on borne dans [0,1] par sécurité
            if rel < 0.0:
                rel = 0.0
            elif rel > 1.0:
                rel = 1.0
            f_vis = vis_fmin + (vis_fmax - vis_fmin) * rel

        # Amplitude temporelle (sinus global) à la fréquence visuelle locale
        osc = math.sin(2.0 * math.pi * f_vis * t_clamped)

        # Distance radiale au centre (pour le poids), mais déplacement HORIZONTAL
        dx = xs - cx_base
        dy = ys - cy_base
        d2 = dx * dx + dy * dy
        r_dist = np.sqrt(d2 + 1e-9)

        # Profil radial en cosinus (raised cosine)
        # R ~ 2 * sigma pour avoir un diamètre proche de ce qui était visé
        R = 2.0 * sigma
        t_norm = np.clip(r_dist / R, 0.0, 1.0)
        w_cos = 0.5 * (1.0 + np.cos(np.pi * t_norm))  # 1 au centre, 0 au bord
        w_cos[r_dist >= R] = 0.0

        # Amplitude de déformation EN X uniquement
        # 0.5 pour garder un rendu plutôt doux par défaut
        deform = w_cos * (0.5 * amp_pixels) * osc

        # Nouvelles coordonnées sources : déplacement horizontal seulement
        src_x = xs + deform
        src_y = ys

        # Clamp dans l'image
        src_x = np.clip(src_x, 0.0, float(w - 1))
        src_y = np.clip(src_y, 0.0, float(h - 1))

        # Échantillonnage nearest-neighbor (OK pour du pixel art)
        xi = np.rint(src_x).astype(np.int32)
        yi = np.rint(src_y).astype(np.int32)

        frame = base[yi, xi]
        frame = np.clip(frame, 0.0, 255.0).astype(np.uint8)
        return frame

    # Création du clip vidéo
    clip = VideoClip(make_frame, duration=duration_s).set_audio(audio_clip)

    # Encodage avec barre de progression MoviePy + paramètres compatibles QuickTime
    try:
        clip.write_videofile(
            video_out_path,
            fps=args.fps,
            codec="libx264",
            audio_codec="aac",
            audio_bitrate="192k",
            verbose=True,  # affiche la barre de progression
            ffmpeg_params=[
                "-pix_fmt",
                "yuv420p",      # format de pixels standard QuickTime
                "-movflags",
                "+faststart",   # lecture progressive optimisée
            ],
        )
        print(f"✅ Vidéo générée : {video_out_path}")
        print(f"→ fps={args.fps} | vis-fmin={vis_fmin}Hz | vis-fmax={vis_fmax}Hz")
        print(
            f"→ amp={args.vis_amp_pct}% (~{amp_pixels:.2f}px) | "
            f"gauss_size={args.gauss_size_pct}% de la largeur (video {video_w}×{video_h})"
        )
    finally:
        clip.close()
        audio_clip.close()


# -*- coding: utf-8 -*-
"""
video.py (V3.2 final, centre gaussienne sur centres de pixels)
─────────────────────────────────────
Rendu vidéo avec :

- pixel art COULEUR basé sur l'image source,
- ratio issu de la grille audio (freqs),
- support de --video-width / --video-height,
- balayage zigzag synchronisé avec l'audio,
- déformation locale (vibration) gaussienne,
- fréquence visuelle mappée depuis la fréquence AUDIO locale :
    f_audio in [fmin, fmax] → f_vis in [vis-fmin, vis-fmax]

MoviePy est importé tardivement (optionnel) et l'encodage
est compatible QuickTime (H.264 + yuv420p, width/height pairs).

Optimisations ajoutées (refactor v3.3):
- base image stockée en uint8 pour éviter conversions par frame,
- pré-calculs scalaires hors de la closure make_frame,
- allocation et réutilisation de buffers pour src_x/src_y/xi/yi,
- usages in-place numpy pour limiter allocations temporaires,
- barre de progression globale (tqdm) mise à jour depuis make_frame.
"""
import io
import sys
import os
import contextlib

import math
from typing import Any, Tuple

import numpy as np
from PIL import Image

from .image_proc import compute_video_output_shape, zigzag_indices

# tentative d'import de tqdm ; fallback sur un simple compteur si absent
try:
    from tqdm import tqdm
except Exception:  # pragma: no cover - fallback
    tqdm = None


def _compute_gaussian_sigma(video_width: int, gauss_size_pct: float) -> float:
    """
    Calcule sigma de la gaussienne à partir d'un diamètre exprimé
    en % de la largeur vidéo.
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
    Retourne dtype=np.uint8 pour éviter conversions répétées en sortie.
    """
    Hf, Wf = freqs_shape

    img_src = Image.open(image_path).convert("RGB")
    img_small = img_src.resize((Wf, Hf), Image.LANCZOS)   # grille logique couleur
    img_video = img_small.resize((video_width, video_height), Image.NEAREST)

    base = np.asarray(img_video, dtype=np.uint8)
    return base


def _allocate_frame_buffers(h: int, w: int):
    """
    Alloue buffers réutilisables pour la génération de frames :
    - src_x, src_y : float32 (coordonnées sources)
    - xi, yi : int32 (indices nearest)
    Retourne un dict de buffers.
    """
    buffers = {
        "src_x": np.empty((h, w), dtype=np.float32),
        "src_y": np.empty((h, w), dtype=np.float32),
        "xi": np.empty((h, w), dtype=np.int32),
        "yi": np.empty((h, w), dtype=np.int32),
    }
    return buffers


def _precompute_centers_and_fvis(args: Any, freqs: np.ndarray, w: int, h: int):
    """
    Pré-calcul des coordonnées centres (alignées sur le centre d'un pixel vidéo)
    et des fréquences visuelles par cellule (r,c).

    Retourne deux dicts : centers[(r,c)] = (cx_base, cy_base),
    fvis[(r,c)] = f_vis (float).
    """
    Hf, Wf = freqs.shape
    centers = {}
    fvis = {}

    vis_fmin = float(args.vis_fmin)
    vis_fmax = float(args.vis_fmax)
    fmin = float(args.fmin)
    fmax = float(args.fmax)

    for r in range(Hf):
        for c in range(Wf):
            cx_base = (c + 0.5) / float(Wf) * w
            cy_base = (r + 0.5) / float(Hf) * h
            # alignement sur le centre d'un pixel (n + 0.5)
            cx_base = math.floor(cx_base) + 0.5
            cy_base = math.floor(cy_base) + 0.5
            centers[(r, c)] = (cx_base, cy_base)

            f_audio = float(freqs[r, c])
            if fmax <= fmin:
                fv = vis_fmin
            else:
                rel = (f_audio - fmin) / (fmax - fmin)
                if rel < 0.0:
                    rel = 0.0
                elif rel > 1.0:
                    rel = 1.0
                fv = vis_fmin + (vis_fmax - vis_fmin) * rel
            fvis[(r, c)] = fv

    return centers, fvis


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

    # Image de base pixel art COULEUR (grille audio upscalée) -> dtype uint8
    base = _make_pixel_art_base_from_color(
        image_path=args.image,
        freqs_shape=freqs.shape,
        video_width=video_w,
        video_height=video_h,
    )  # (h, w, 3) uint8
    h, w, _ = base.shape

    # Grilles de coordonnées (float32)
    xs, ys = np.meshgrid(
        np.arange(w, dtype=np.float32),
        np.arange(h, dtype=np.float32),
        indexing="xy",
    )

    # Sigma & paramètres scalaires
    sigma = _compute_gaussian_sigma(video_width=w, gauss_size_pct=args.gauss_size_pct)
    inv_2sigma2 = 1.0 / (2.0 * sigma * sigma)
    half_amp_pixels = (args.vis_amp_pct / 100.0) * float(w) * 0.5

    # Pré-calcul centres alignés et fréquences visuelles par cellule (r,c)
    centers_map, fvis_map = _precompute_centers_and_fvis(args, freqs, w, h)

    # Infos liées aux oscillateurs / ordre zigzag
    order = zigzag_indices(Hf, Wf)
    N = len(order)
    if N <= 1:
        # Cas dégénéré : on reste centré
        order = [(Hf // 2, Wf // 2)]
        N = 1

    # Buffers réutilisables pour réduire allocations par frame
    buffers = _allocate_frame_buffers(h, w)
    src_x = buffers["src_x"]
    src_y = buffers["src_y"]
    xi = buffers["xi"]
    yi = buffers["yi"]

    # Durée active (sans le sustain final) pour la progression de la fenêtre
    sweep_T = max(duration_s - float(getattr(args, "sustain_s", 0.0)), 0.001)

    # Extraire quelques valeurs dans des locaux pour accès rapides
    fps = args.fps

    # --- setup barre de progression globale ---
    total_frames = max(1, int(math.ceil(duration_s * float(fps))))
    if tqdm is not None:
        pbar = tqdm(total=total_frames, desc="Rendu vidéo", unit="frame")
        use_tqdm = True
    else:
        # fallback minimal : simple compteur + print périodique
        pbar = {"count": 0}
        use_tqdm = False

    last_idx = -1  # dernier index de frame comptabilisé dans la barre

    def make_frame(t: float) -> np.ndarray:
        nonlocal last_idx, pbar

        # On borne le temps dans [0, duration_s]
        t_clamped = max(0.0, min(float(t), duration_s))

        # Phase de progression de la fenêtre dans le temps (0→1 sur sweep_T)
        if sweep_T > 0:
            phase = min(t_clamped / sweep_T, 1.0)
        else:
            phase = 1.0

        # Enveloppe de BALAYAGE (fade-out)
        edge = 0.15  # 15% de la durée de balayage
        if phase <= 0.0:
            sweep_env = 0.0
        elif phase > 1.0 - edge:
            sweep_env = (1.0 - phase) / edge
        else:
            sweep_env = 1.0
        sweep_env = max(0.0, min(sweep_env, 1.0))

        # Index flottant dans l'ordre zigzag
        idx_float = phase * float(N - 1)
        idx = int(round(idx_float))
        idx = max(0, min(idx, N - 1))

        r, c = order[idx]

        # Récupère centre pré-calculé et fréquence visuelle
        cx_base, cy_base = centers_map[(r, c)]
        f_vis = fvis_map[(r, c)]

        # Mise à jour de la barre globale : calcul de l'indice de frame courant
        # (on arrondit pour correspondre au frame demandé)
        try:
            frame_idx = int(round(t_clamped * float(fps)))
        except Exception:
            frame_idx = int(t_clamped * float(fps))
        if frame_idx >= total_frames:
            frame_idx = total_frames - 1
        delta = frame_idx - last_idx
        if delta > 0:
            if use_tqdm:
                pbar.update(delta)
            else:
                pbar["count"] += delta
                # print un pourcentage simple toutes les 5%
                if total_frames > 0:
                    perc = int(100 * pbar["count"] / total_frames)
                    if pbar["count"] % max(1, total_frames // 20) == 0:
                        print(f"Rendu vidéo: {perc}%")
            last_idx = frame_idx

        # Amplitude temporelle (sinus global) à la fréquence visuelle locale
        osc = math.sin(2.0 * math.pi * f_vis * t_clamped)

        # Calcul des déformations (vectorisé). On vise à minimiser allocations temporaires :
        dx = xs - cx_base
        dy = ys - cy_base

        # d2 = dx^2 + dy^2
        d2 = dx * dx + dy * dy

        # poids gaussien : g = exp(-d2 / (2*sigma^2))
        g = np.exp(-d2 * inv_2sigma2)

        # distance d
        d = np.sqrt(d2 + 1e-9)

        # vecteurs unitaires radiaux
        ux = dx / d
        uy = dy / d

        # amplitude de déformation radiale (en pixels)
        deform = sweep_env * (g ** 2) * half_amp_pixels * osc

        # nouvelles coordonnées sources (in-place into src_x/src_y where possible)
        # src_x = xs + ux * deform
        np.multiply(ux, deform, out=src_x)  # src_x = ux * deform
        np.add(src_x, xs, out=src_x)        # src_x = xs + ux*deform (in-place)

        np.multiply(uy, deform, out=src_y)
        np.add(src_y, ys, out=src_y)        # src_y = ys + uy*deform (in-place)

        # Clamp dans l'image puis nearest-neighbor (rint)
        np.clip(src_x, 0.0, float(w - 1), out=src_x)
        np.clip(src_y, 0.0, float(h - 1), out=src_y)
        np.rint(src_x, out=src_x)
        np.rint(src_y, out=src_y)

        # Cast in-place into integer index buffers
        try:
            src_x.astype(np.int32, copy=False, out=xi)
            src_y.astype(np.int32, copy=False, out=yi)
        except TypeError:
            np.copyto(xi, np.rint(src_x).astype(np.int32))
            np.copyto(yi, np.rint(src_y).astype(np.int32))

        # Échantillonnage nearest-neighbor (OK pour du pixel art)
        frame = base[yi, xi]
        # base is uint8; returned frame is uint8 -> no extra astype/clip needed

        return frame

    # Création du clip vidéo
        # Création du clip vidéo
    clip = VideoClip(make_frame, duration=duration_s).set_audio(audio_clip)

    # Encodage : on capture stdout/stderr temporairement pour empêcher les barres
    # internes (moviepy / imageio / ffmpeg) d'afficher leur propre progression.
    out_buf = io.StringIO()
    err_buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(out_buf), contextlib.redirect_stderr(err_buf):
            try:
                # Essayer avec logger=None si la version de moviepy le supporte
                clip.write_videofile(
                    video_out_path,
                    fps=fps,
                    codec="libx264",
                    audio_codec="aac",
                    audio_bitrate="192k",
                    verbose=False,
                    logger=None,
                    ffmpeg_params=[
                        "-pix_fmt",
                        "yuv420p",
                        "-movflags",
                        "+faststart",
                    ],
                )
            except TypeError:
                # Fallback pour versions anciennes de moviepy sans logger param
                clip.write_videofile(
                    video_out_path,
                    fps=fps,
                    codec="libx264",
                    audio_codec="aac",
                    audio_bitrate="192k",
                    verbose=False,
                    ffmpeg_params=[
                        "-pix_fmt",
                        "yuv420p",
                        "-movflags",
                        "+faststart",
                    ],
                )
    except Exception:
        # Si une erreur survient, on flush les sorties capturées pour débogage,
        # puis on ré-élève l'exception.
        sys.stdout.write(out_buf.getvalue())
        sys.stderr.write(err_buf.getvalue())
        raise
    else:
        # Succès : on ferme la barre proprement avant d'afficher le message final.
        if tqdm is not None:
            try:
                pbar.close()
            except Exception:
                pass
        else:
            print("Rendu vidéo: 100%")

        # Message final unique, format identique à l'audio
        print(f"\n✅ Vidéo générée : {video_out_path}")
        print(f"→ fps={fps} | vis-fmin={args.vis_fmin}Hz | vis-fmax={args.vis_fmax}Hz")
        print(
            f"→ amp={args.vis_amp_pct}% (~{half_amp_pixels*2:.2f}px) | "
            f"gauss_size={args.gauss_size_pct}% de la largeur (video {video_w}×{video_h})\n"
        )
    finally:
        # fermeture ressources (clip/audio)
        try:
            clip.close()
        except Exception:
            pass
        try:
            audio_clip.close()
        except Exception:
            pass


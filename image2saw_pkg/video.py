# -*- coding: utf-8 -*-
"""
video.py
────────
Rendu vidéo (MoviePy) avec vibration gaussienne centrée
sur la fenêtre glissante.

Fonctionnalités :
- taille vidéo = --size ou --video-size
- vibration gaussienne (diamètre en % de la largeur vidéo)
- amplitude en % de la largeur vidéo
- waveform visuelle synchronisée (sine / square / saw)
- génération frame-by-frame via MoviePy.VideoClip (streaming)
"""

import math
from dataclasses import dataclass
from typing import List

import numpy as np
from PIL import Image, ImageOps
from tqdm import tqdm

from .image_proc import zigzag_indices

# Dépendance vidéo optionnelle (MoviePy 1.x / 2.x)
_HAS_MOVIEPY = False
_MOVIEPY_IMPORT_ERROR = None

try:
    try:
        # MoviePy 1.x
        from moviepy.editor import AudioFileClip, VideoClip
    except ImportError:
        # MoviePy 2.x
        from moviepy import AudioFileClip, VideoClip
    _HAS_MOVIEPY = True
except Exception as e:
    _HAS_MOVIEPY = False
    _MOVIEPY_IMPORT_ERROR = e


@dataclass
class VideoKeyframe:
    """
    Décrit l'état de la fenêtre glissante à un instant donné pour la vidéo.
    time   : temps en secondes (aligné avec osc.start)
    cx, cy : centre de la zone de vibration (coordonnées pixels dans l'image vidéo)
    f_audio: fréquence audio représentative (ici : fréquence du pixel courant)
    f_vis  : fréquence visuelle dérivée (1–10 Hz par défaut)
    """
    time: float
    cx: float
    cy: float
    f_audio: float
    f_vis: float


def has_moviepy() -> bool:
    return _HAS_MOVIEPY


def moviepy_import_error():
    return _MOVIEPY_IMPORT_ERROR


def map_audio_to_visual_freq(
    f_audio: float,
    fmin_audio: float,
    fmax_audio: float,
    fmin_vis: float,
    fmax_vis: float,
) -> float:
    """
    Mappe une fréquence audio (dans [fmin_audio, fmax_audio]) vers une fréquence
    visuelle (dans [fmin_vis, fmax_vis]).
    """
    if fmax_audio <= fmin_audio:
        return (fmin_vis + fmax_vis) * 0.5

    ratio = (f_audio - fmin_audio) / (fmax_audio - fmin_audio)
    ratio = np.clip(ratio, 0.0, 1.0)
    return float(fmin_vis + ratio * (fmax_vis - fmin_vis))


def visual_wave(t: float, f_vis: float, wave_type: str) -> float:
    """
    Forme d'onde visuelle normalisée entre -1 et 1.
    t       : temps en secondes
    f_vis   : fréquence visuelle (Hz)
    wave_type : "sine", "square" ou "saw" (triangle utilise sine côté visuel)
    """
    phase = 2.0 * np.pi * f_vis * t
    wt = wave_type.lower()

    if wt == "sine" or wt == "triangle":
        return float(np.sin(phase))

    elif wt == "square":
        s = np.sin(phase)
        return float(1.0 if s >= 0 else -1.0)

    elif wt == "saw":
        frac = (f_vis * t) % 1.0
        return float(2.0 * frac - 1.0)

    return float(np.sin(phase))


def render_video_with_audio(
    img: Image.Image,
    video_keyframes: List[VideoKeyframe],
    audio_path: str,
    fps: int,
    amp_pixels: float,
    gauss_size_pct: float,
    wave_type: str,
    output_path: str,
):
    """
    Rend la vidéo finale en combinant :
    - un VideoClip(streaming) qui génère chaque frame à la volée
    - le fichier audio WAV déjà produit par image2saw

    amp_pixels : amplitude max de vibration (en pixels, déjà convertis
                 à partir d'un pourcentage de la largeur vidéo).
    """
    if not _HAS_MOVIEPY:
        raise RuntimeError(
            "moviepy n'est pas installé. Installe-le avec 'pip install moviepy'."
        )

    if not video_keyframes:
        print("[video] Aucune keyframe vidéo, vidéo non créée.")
        return

    audio_clip = AudioFileClip(audio_path)
    duration_s = float(audio_clip.duration)

    # Pré-calculs constants pour toutes les frames (image vidéo déjà à sa taille finale)
    base = np.array(img).astype(np.float32)  # (h, w, 3)
    h, w, _ = base.shape

    xs, ys = np.meshgrid(
        np.arange(w, dtype=np.float32),
        np.arange(h, dtype=np.float32),
        indexing="xy",
    )

    # Taille de la gaussienne en pourcentage de la dimension vidéo
    video_diam = float(min(w, h))
    D = (gauss_size_pct / 100.0) * video_diam  # diamètre en pixels, dans l'espace vidéo

    R_max = D / 2.0
    sigma = R_max / 2.0 if R_max > 0 else 1.0
    R_soft = R_max * 0.7

    # On met les infos clés dans des tableaux NumPy pour une recherche rapide
    times = np.array([kf.time for kf in video_keyframes], dtype=np.float32)
    cx_arr = np.array([kf.cx for kf in video_keyframes], dtype=np.float32)
    cy_arr = np.array([kf.cy for kf in video_keyframes], dtype=np.float32)
    f_vis_arr = np.array([kf.f_vis for kf in video_keyframes], dtype=np.float32)
    n_keys = len(times)

    # Progress bar MoviePy (approx : une update par frame)
    total_frames = int(math.ceil(duration_s * fps)) if duration_s > 0 else 1
    pbar = tqdm(total=total_frames, desc="MoviePy - Building video", unit="frame")
    frame_counter = {"n": 0}

    def make_frame(t: float) -> np.ndarray:
        """Callback MoviePy : génère une frame RGB (h, w, 3) pour le temps t."""
        # Clamp t dans [0, duration_s]
        if t < 0.0:
            t_local = 0.0
        elif t > duration_s:
            t_local = duration_s
        else:
            t_local = t

        # On trouve l'index de la keyframe active : dernière keyframe dont time <= t_local
        idx = int(np.searchsorted(times, t_local, side="right") - 1)
        if idx < 0:
            idx = 0
        elif idx >= n_keys:
            idx = n_keys - 1

        cx = float(cx_arr[idx])
        cy = float(cy_arr[idx])
        f_vis = float(f_vis_arr[idx])

        dx0 = xs - cx
        dy0 = ys - cy
        r = np.sqrt(dx0 * dx0 + dy0 * dy0)

        # Gaussienne spatiale
        A_spatial = amp_pixels * np.exp(-(r * r) / (2.0 * sigma * sigma))

        # Fondu doux sur le bord (demi-cos entre R_soft et R_max)
        if R_max > 0:
            mask = np.ones_like(A_spatial, dtype=np.float32)
            annulus = (r >= R_soft) & (r < R_max)
            if R_max > R_soft:
                mask[annulus] = 0.5 * (
                    1.0 + np.cos(
                        np.pi * (r[annulus] - R_soft) / (R_max - R_soft)
                    )
                )
            mask[r >= R_max] = 0.0
            A_spatial *= mask

        # Forme d'onde temporelle
        s_t = visual_wave(t_local, f_vis, wave_type)

        # Amplitude finale
        A = A_spatial * s_t

        # Déplacement radial
        r_safe = np.where(r == 0, 1.0, r)
        dx = dx0 / r_safe * A
        dy = dy0 / r_safe * A

        src_x = np.clip(xs - dx, 0, w - 1).astype(np.int32)
        src_y = np.clip(ys - dy, 0, h - 1).astype(np.int32)

        warped = base[src_y, src_x]
        warped = np.clip(warped, 0, 255).astype(np.uint8)

        # Maj de la progress bar MoviePy
        frame_counter["n"] += 1
        if frame_counter["n"] <= total_frames:
            pbar.update(1)

        return warped

    # Création du clip vidéo MoviePy en mode streaming
    video_clip = VideoClip(make_frame, duration=duration_s)
    try:
        video_clip = video_clip.set_audio(audio_clip)
    except AttributeError:
        # MoviePy 2.x (au cas où)
        video_clip = video_clip.with_audio(audio_clip)

    try:
        video_clip.write_videofile(
            output_path,
            codec="libx264",
            audio_codec="aac",
            fps=fps,
        )
    finally:
        pbar.close()


def generate_video_from_args(
    args,
    freqs: np.ndarray,
    out_wav: str,
    default_video_out: str,
):
    """
    Reprend exactement la logique vidéo du main v2.9,
    mais isolée dans un module.

    args   : arguments CLI (Namespace)
    freqs  : tableau (size, size) de fréquences
    out_wav: chemin du fichier audio déjà généré
    """
    if not args.video:
        return

    if not has_moviepy():
        print("\n⚠️  Vidéo non générée : problème avec moviepy.")
        err = moviepy_import_error()
        if err is not None:
            print(f"   Détail de l'erreur d'import : {err}")
        print("   → vérifie que tu utilises le même interpréteur Python pour :")
        print("       - python3 -c \"import moviepy; ...\"")
        print("       - python3 image2saw.py ... --video")
        return

    print("\n🎬 Génération de la vidéo (mode streaming)...")

    # Taille vidéo finale
    video_size = args.video_size if args.video_size > 0 else args.size

    # Amplitude max de vibration en pixels (en % de la largeur vidéo)
    amp_pixels = (args.vis_amp_pct / 100.0) * float(video_size)

    # 1) Image couleur redimensionnée à la taille logique (ex : 128×128) en LANCZOS
    img_color = Image.open(args.image).convert("RGB")
    img_small = ImageOps.fit(
        img_color,
        (args.size, args.size),
        method=Image.LANCZOS,
        centering=(0.5, 0.5),
    )

    # 2) Mise à l'échelle vers la taille vidéo
    if video_size != args.size:
        img_pil = img_small.resize((video_size, video_size), resample=Image.NEAREST)
    else:
        img_pil = img_small

    # Keyframes vidéo : coordonnées logiques (r, c) → coordonnées vidéo (cx, cy)
    h = w = args.size
    step_s = args.step_ms / 1000.0
    order = zigzag_indices(h, w)

    scale = video_size / args.size
    video_keyframes: List[VideoKeyframe] = []

    for i, (r, c) in enumerate(order):
        t_k = i * step_s

        # centre du macro-pixel dans l'image vidéo
        cx = (c + 0.5) * scale - 0.5
        cy = (r + 0.5) * scale - 0.5

        f_audio = float(freqs[r, c])
        f_vis = map_audio_to_visual_freq(
            f_audio=f_audio,
            fmin_audio=args.fmin,
            fmax_audio=args.fmax,
            fmin_vis=args.vis_fmin,
            fmax_vis=args.vis_fmax,
        )
        video_keyframes.append(
            VideoKeyframe(time=t_k, cx=cx, cy=cy, f_audio=f_audio, f_vis=f_vis)
        )

    # Résolution du nom de fichier vidéo (auto ou forcé)
    video_out_path = args.video_out if args.video_out != "AUTO" else default_video_out

    try:
        render_video_with_audio(
            img=img_pil,
            video_keyframes=video_keyframes,
            audio_path=out_wav,
            fps=args.fps,
            amp_pixels=amp_pixels,
            gauss_size_pct=args.gauss_size_pct,
            wave_type=args.waveform,
            output_path=video_out_path,
        )
        print(f"✅ Vidéo générée : {video_out_path}")
        print(f"→ fps={args.fps} | vis-fmin={args.vis_fmin}Hz | vis-fmax={args.vis_fmax}Hz")
        print(
            f"→ amp={args.vis_amp_pct}% (~{amp_pixels:.2f}px) | "
            f"gauss_size={args.gauss_size_pct}% de la largeur (video {video_size}×{video_size})"
        )
    except RuntimeError as e:
        print(f"⚠️  Vidéo non générée : {e}")


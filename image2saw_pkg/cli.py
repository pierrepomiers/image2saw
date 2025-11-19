# -*- coding: utf-8 -*-
"""
cli.py
──────
Interface en ligne de commande + orchestration globale.

Reprend la CLI et le comportement de Image2Saw v2.9/3.1,
en s'appuyant sur les modules audio, image_proc et video.

V3.2 :
- prise en compte du ratio original de l'image pour l'audio (quand --duration-s est utilisé)
- nouveaux paramètres vidéo : --video-width / --video-height
"""

import argparse
import os
from typing import Tuple

import numpy as np
from PIL import Image

from .audio import (
    map_gray_to_freq,
    plan_schedule,
    render_audio,
    write_wav_int16_stereo,
)
from .image_proc import (
    compute_audio_image_shape_from_duration,
)
from .video import generate_video_from_args


# ─────────────────────────────────────────────
#  Construction du parser d'arguments
# ─────────────────────────────────────────────

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="image2saw.py",
        description="Transforme une image en texture sonore séquencée (+ vidéo optionnelle).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    # Image / audio de base
    parser.add_argument("image", type=str, help="Fichier image d'entrée.")
    parser.add_argument(
        "--size",
        type=int,
        default=128,
        help="Taille du côté carré logique (ex: 128) si aucune durée cible n'est donnée.",
    )
    parser.add_argument("--sr", type=int, default=32000, help="Fréquence d'échantillonnage (Hz).")
    parser.add_argument("--fmin", type=float, default=5.0, help="Fréquence minimale (Hz).")
    parser.add_argument("--fmax", type=float, default=200.0, help="Fréquence maximale (Hz).")
    parser.add_argument(
        "--step-ms",
        type=float,
        default=100.0,
        help="Décalage entre oscillateurs (ms).",
    )
    parser.add_argument(
        "--sustain-s",
        type=float,
        default=5.0,
        help="Durée de maintien après le dernier oscillateur (s).",
    )
    parser.add_argument(
        "--block-ms",
        type=float,
        default=50.0,
        help="Taille du bloc CPU (ms) pour le rendu audio par batch.",
    )
    parser.add_argument(
        "--fade-ms",
        type=float,
        default=5.0,
        help="Durée du fondu d'attaque/relâche (ms).",
    )
    parser.add_argument(
        "--waveform",
        type=str,
        default="saw",
        choices=["saw", "sine", "triangle", "square"],
        help="Forme d'onde utilisée pour le son (et éventuellement la vibration visuelle).",
    )
    parser.add_argument(
        "--voices",
        type=int,
        default=20,
        help="Nombre maximal d'oscillateurs actifs simultanément.",
    )

    parser.add_argument(
        "--duration-s",
        type=float,
        default=None,
        help=(
            "Durée cible du son (en secondes). "
            "Si définie, la taille de l'image utilisée pour l'audio est recalculée "
            "en respectant le ratio original (V3.2), sans modifier step-ms."
        ),
    )

    # Stereo / mono
    g = parser.add_mutually_exclusive_group()
    g.add_argument(
        "--stereo",
        action="store_true",
        help="Active explicitement la spatialisation stéréo (par défaut si rien n'est précisé).",
    )
    g.add_argument(
        "--mono",
        action="store_true",
        help="Force un rendu mono.",
    )

    # Paramètres vidéo
    parser.add_argument(
        "--video",
        action="store_true",
        help="Active la génération d'une vidéo avec vibration gaussienne autour de la fenêtre glissante.",
    )
    parser.add_argument(
        "--fps",
        type=int,
        default=25,
        help="Framerate de la vidéo (défaut: 25).",
    )
    parser.add_argument(
        "--vis-fmin",
        type=float,
        default=1.0,
        help="Fréquence visuelle minimale en Hz (défaut: 1.0).",
    )
    parser.add_argument(
        "--vis-fmax",
        type=float,
        default=10.0,
        help="Fréquence visuelle maximale en Hz (défaut: 10.0).",
    )
    parser.add_argument(
        "--vis-amp-pct",
        type=float,
        default=1.0,
        help="Amplitude maximale de la vibration (en pourcentage de la largeur vidéo, défaut: 1.0).",
    )
    parser.add_argument(
        "--gauss-size-pct",
        type=float,
        default=30.0,
        help="Diamètre de la gaussienne (en pourcentage de la largeur de la vidéo, défaut: 30).",
    )
    parser.add_argument(
        "--video-width",
        type=int,
        default=None,
        help=(
            "Largeur de la vidéo finale (en pixels). "
            "Si seule la largeur ou la hauteur est fournie, le ratio de l'image source est conservé."
        ),
    )
    parser.add_argument(
        "--video-height",
        type=int,
        default=None,
        help=(
            "Hauteur de la vidéo finale (en pixels). "
            "Si largeur ET hauteur sont fournies, l'image est stretchée pour remplir exactement "
            "(pas de bandes, pas de crop)."
        ),
    )
    parser.add_argument(
        "--video-out",
        type=str,
        default=None,
        help="Nom du fichier vidéo de sortie (défaut: même nom que l'image en .mp4).",
    )

    return parser


# ─────────────────────────────────────────────
#  Utilitaires internes
# ─────────────────────────────────────────────

def _compute_audio_image_shape(
    args: argparse.Namespace,
    orig_size: Tuple[int, int],
) -> Tuple[int, int]:
    """
    Retourne (width, height) pour l'image audio.

    - Si args.duration_s est défini → utilise compute_audio_image_shape_from_duration
      en respectant le ratio original.
    - Sinon → retourne (size, size) comme en V3.1.
    """
    orig_w, orig_h = orig_size

    if args.duration_s is not None:
        w, h = compute_audio_image_shape_from_duration(
            duration_s=args.duration_s,
            step_ms=args.step_ms,
            sustain_s=args.sustain_s,
            voices=args.voices,
            orig_width=orig_w,
            orig_height=orig_h,
        )
        return w, h

    # Comportement historique : image carrée
    return args.size, args.size


# ─────────────────────────────────────────────
#  Point d'entrée principal
# ─────────────────────────────────────────────

def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    # Détermination des fichiers de sortie
    base, _ = os.path.splitext(args.image)
    out_wav = base + ".wav"
    default_video_out = base + ".mp4"
    if args.video_out is None:
        args.video_out = default_video_out

    # Chargement de l'image source
    img = Image.open(args.image).convert("L")
    orig_width, orig_height = img.size

    # Calcul de la taille logique pour l'audio
    audio_w, audio_h = _compute_audio_image_shape(args, (orig_width, orig_height))

    # Redimensionnement pour l'audio
    img_audio = img.resize((audio_w, audio_h), Image.LANCZOS)
    gray = np.asarray(img_audio, dtype=np.uint8)

    # Mapping niveaux de gris -> fréquences
    freqs = map_gray_to_freq(gray, args.fmin, args.fmax)

    # Stereo / mono
    if args.mono:
        stereo = False
    else:
        # par défaut ou avec --stereo explicite → stéréo
        stereo = True

    # Planification des oscillateurs
    oscs, T = plan_schedule(
        freqs=freqs,
        size=audio_w,          # en V3.2, audio_w = largeur logique (utilisé pour le panning)
        sr=args.sr,
        step_ms=args.step_ms,
        sustain_s=args.sustain_s,
        stereo=stereo,
        voices=args.voices,
    )

    # Rendu audio
    audio_lr = render_audio(
        oscs=oscs,
        sr=args.sr,
        block_ms=args.block_ms,
        fade_ms=args.fade_ms,
        waveform=args.waveform,
    )

    # Écriture WAV
    write_wav_int16_stereo(out_wav, args.sr, audio_lr)

    # Logs
    duration_real = len(audio_lr) / float(args.sr)
    print(f"\n✅ Fichier audio généré : {out_wav}")
    print(
        f"→ Forme : {args.waveform} | Voix : {args.voices} | Mode : "
        f"{'stéréo' if stereo else 'mono'}"
    )
    print(
        f"→ Durée réelle : {duration_real:.2f}s | sr={args.sr} Hz | "
        f"Taille image audio : {audio_w} x {audio_h} (logique)"
    )
    print(
        f"→ fmin={args.fmin}Hz | fmax={args.fmax}Hz | "
        f"step={args.step_ms}ms | sustain={args.sustain_s}s"
    )
    if args.duration_s is not None:
        print(f"→ Durée cible demandée : {args.duration_s:.2f}s\n")

    # Vidéo (optionnelle)
    if args.video:
        generate_video_from_args(
            args=args,
            freqs=freqs,
            out_wav=out_wav,
            default_video_out=args.video_out,
        )


if __name__ == "__main__":
    main()


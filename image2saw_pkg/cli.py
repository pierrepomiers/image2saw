# -*- coding: utf-8 -*-
"""
cli.py
──────
Interface en ligne de commande + orchestration globale.

Reprend la CLI et le comportement de Image2Saw v2.9,
mais en s'appuyant sur les modules audio, image_proc et video.
"""

import argparse
import os

from .audio import (
    map_gray_to_freq,
    plan_schedule,
    render_audio,
    write_wav_int16_stereo,
)
from .image_proc import load_image_to_gray_square
from .video import generate_video_from_args


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="image2saw.py",
        description="Transforme une image en texture sonore séquencée (+ vidéo optionnelle).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument("image", type=str, help="Fichier image d'entrée.")
    parser.add_argument("--size", type=int, default=128, help="Taille du côté carré logique (ex: 128).")
    parser.add_argument("--sr", type=int, default=32000, help="Fréquence d'échantillonnage (Hz).")
    parser.add_argument("--fmin", type=float, default=5.0, help="Fréquence minimale (Hz).")
    parser.add_argument("--fmax", type=float, default=200.0, help="Fréquence maximale (Hz).")
    parser.add_argument("--step-ms", type=float, default=100.0, help="Décalage entre oscillateurs (ms).")
    parser.add_argument("--sustain-s", type=float, default=5.0, help="Durée de maintien après le dernier oscillateur (s).")
    parser.add_argument("--block-ms", type=float, default=50.0, help="Taille du bloc CPU (ms).")
    parser.add_argument("--fade-ms", type=float, default=5.0, help="Durée du fondu d'attaque/relâche (ms).")
    parser.add_argument(
        "--waveform",
        type=str,
        default="saw",
        choices=["saw", "sine", "triangle", "square"],
        help="Forme d'onde utilisée pour le son (et la vibration visuelle).",
    )
    parser.add_argument("--voices", type=int, default=20, help="Nombre maximal d'oscillateurs actifs simultanément.")

    g = parser.add_mutually_exclusive_group()
    g.add_argument("--stereo", action="store_true", help="Active la spatialisation stéréo.")
    g.add_argument("--mono", action="store_true", help="Force un rendu mono.")

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
        help="Diamètre de la gaussienne en pourcentage de la largeur de la vidéo (défaut: 30).",
    )
    parser.add_argument(
        "--video-size",
        type=int,
        default=0,
        help="Taille du côté de la vidéo en pixels (défaut: même valeur que --size).",
    )
    parser.add_argument(
        "--video-out",
        type=str,
        default="AUTO",
        help="Nom du fichier vidéo de sortie (défaut: même nom que l'image en .mp4).",
    )

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()

    base, _ = os.path.splitext(args.image)
    out_wav = base + ".wav"
    default_video_out = base + ".mp4"

    # Audio : image grisée logique (size x size, LANCZOS)
    gray = load_image_to_gray_square(args.image, args.size)
    freqs = map_gray_to_freq(gray, args.fmin, args.fmax)

    # Mode mono / stéréo (même logique que v2.9)
    stereo = not args.mono if (args.stereo or args.mono) else True

    # Planification + rendu audio
    oscs, T = plan_schedule(
        freqs=freqs,
        size=args.size,
        sr=args.sr,
        step_ms=args.step_ms,
        sustain_s=args.sustain_s,
        stereo=stereo,
        voices=args.voices,
    )

    audio_lr = render_audio(
        oscs=oscs,
        T=T,
        sr=args.sr,
        block_ms=args.block_ms,
        mono=not stereo,
        waveform=args.waveform,
        fade_ms=args.fade_ms,
        voices=args.voices,
        tqdm_desc="Rendu audio",
    )

    write_wav_int16_stereo(out_wav, args.sr, audio_lr)

    print(f"\n✅ Fichier audio généré : {out_wav}")
    print(f"→ Forme : {args.waveform} | Voix : {args.voices} | Mode : {'stéréo' if stereo else 'mono'}")
    print(f"→ Durée : {len(audio_lr)/args.sr:.2f}s | sr={args.sr} Hz | Taille image (logique) : {args.size}")
    print(f"→ fmin={args.fmin}Hz | fmax={args.fmax}Hz | step={args.step_ms}ms | sustain={args.sustain_s}s")

    # Vidéo (streaming, gaussienne, etc.)
    generate_video_from_args(
        args=args,
        freqs=freqs,
        out_wav=out_wav,
        default_video_out=default_video_out,
    )


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

V3.3 :
- ajout d'un "mode artiste" basé sur des presets expressifs (style / movement / density),
  qui se contentent de mapper vers les paramètres techniques existants

V3.4 :
- remplacement du "mode artiste" par jeux de presets basés directement sur les paramètres techniques 
"""

import argparse
import os
from typing import Any, Dict, Tuple

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
#  Presets "artist-preset" : combos clés en main
# ─────────────────────────────────────────────

ARTIST_PRESETS: Dict[str, Dict[str, Any]] = {
    # 1) Nappes lentes, graves, sombres
    "ambient_slow_dark": {
        "color_mode": "grayscale",
        "waveform": "sine",
        "fmin": 40.0,
        "fmax": 1500.0,
        "hsv_detune_pct": 0.0,
        "hsv_blend_gray": 0.20,
        "hsv_max_octave": 5,
        "step_ms": 110.0,
        "voices": 64,
    },

    # 2) Nappes lentes, lumineuses, style "accordéon pastel"
    "ambient_slow_shimmer": {
        "color_mode": "grayscale",
        "waveform": "sine",
        "fmin": 80.0,
        "fmax": 5000.0,
        "hsv_detune_pct": 1.0,
        "hsv_blend_gray": 0.15,
        "hsv_max_octave": 5,
        "step_ms": 90.0,
        "voices": 56,
    },

    # 3) Texture filmique lente, large, basée sur HSV
    "cinematic_slow": {
        "color_mode": "hsv-notes",
        "waveform": "triangle",
        "fmin": 40.0,      # ignoré en hsv-notes, laissé pour cohérence
        "fmax": 8000.0,    # idem
        "hsv_detune_pct": 0.5,
        "hsv_blend_gray": 0.10,
        "hsv_max_octave": 5,
        "step_ms": 80.0,
        "voices": 48,
    },

    # 4) Cinématique plus lumineuse, presque générique
    "cinematic_glow": {
        "color_mode": "hsv-notes",
        "waveform": "triangle",
        "fmin": 40.0,
        "fmax": 8000.0,
        "hsv_detune_pct": 1.0,
        "hsv_blend_gray": 0.05,
        "hsv_max_octave": 5,
        "step_ms": 60.0,
        "voices": 40,
    },

    # 5) "Photo organ" : l’image devient un orgue
    "photo_organ": {
        "color_mode": "grayscale",
        "waveform": "triangle",
        "fmin": 80.0,
        "fmax": 4000.0,
        "hsv_detune_pct": 0.0,
        "hsv_blend_gray": 0.0,
        "hsv_max_octave": 5,
        "step_ms": 60.0,
        "voices": 40,
    },

    # 6) Balayage rapide, lumineux, "scanner"
    "scan_fast_bright": {
        "color_mode": "grayscale",
        "waveform": "saw",
        "fmin": 150.0,
        "fmax": 8000.0,
        "hsv_detune_pct": 0.0,
        "hsv_blend_gray": 0.0,
        "hsv_max_octave": 5,
        "step_ms": 35.0,
        "voices": 24,
    },

    # 7) Glitch très coloré, agressif
    "glitch_color_burst": {
        "color_mode": "hsv-notes",
        "waveform": "square",
        "fmin": 40.0,
        "fmax": 8000.0,
        "hsv_detune_pct": 3.0,
        "hsv_blend_gray": 0.0,
        "hsv_max_octave": 4,
        "step_ms": 25.0,
        "voices": 40,
    },

    # 8) Bitcrush / 8-bit style
    "bitcrush_scan": {
        "color_mode": "grayscale",
        "waveform": "square",
        "fmin": 300.0,
        "fmax": 4000.0,
        "hsv_detune_pct": 0.0,
        "hsv_blend_gray": 0.0,
        "hsv_max_octave": 5,
        "step_ms": 30.0,
        "voices": 20,
    },

    # 9) Tache d’encre très lente
    "ink_in_water": {
        "color_mode": "grayscale",
        "waveform": "sine",
        "fmin": 50.0,
        "fmax": 3000.0,
        "hsv_detune_pct": 0.0,
        "hsv_blend_gray": 0.05,
        "hsv_max_octave": 5,
        "step_ms": 120.0,
        "voices": 64,
    },

    # 10) Pluie de néons : rapide, scintillant, coloré
    "neon_rain": {
        "color_mode": "hsv-notes",
        "waveform": "triangle",
        "fmin": 40.0,
        "fmax": 8000.0,
        "hsv_detune_pct": 1.5,
        "hsv_blend_gray": 0.05,
        "hsv_max_octave": 5,
        "step_ms": 35.0,
        "voices": 36,
    },
}

def apply_artist_preset(args: argparse.Namespace) -> None:
    """
    Applique un preset expressif (--artist-preset) en écrasant directement
    quelques paramètres clés (waveform, color_mode, fmin/fmax, hsv_*, step_ms, voices).

    Hypothèse simple : si l'utilisateur choisit un preset, il accepte
    qu'il prenne vraiment la main. Pour affiner, il pourra ensuite
    passer aux paramètres techniques bruts.
    """
    preset_name = getattr(args, "artist_preset", None)
    if not preset_name:
        return

    preset = ARTIST_PRESETS.get(preset_name)
    if preset is None:
        return

    # On écrase directement les champs connus.
    # (Si on veut être plus subtil plus tard, on pourra conditionner
    #  à "valeur par défaut" avant overwrite.)
    for key, value in preset.items():
        if hasattr(args, key):
            setattr(args, key, value)

# ─────────────────────────────────────────────
#  Mode "hsv-notes" : mapping HSV → (fréquences, amplitudes)
# ─────────────────────────────────────────────

def compute_hsv_notes_from_image(
    img: Image.Image,
    max_octave: int = 5,
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Convertit une image couleur en deux tableaux 2D (freqs_hz, amps)
    en utilisant le mapping suivant :
    - H (teinte)      → note dans l'octave (Do..Si)
    - V (valeur)      → octave (de Do1 jusqu'à Do{max_octave})
    - S (saturation)  → amplitude (0..1)

    max_octave ∈ [1, 5].
    """
    # Clamp de sécurité
    max_octave = int(max_octave)
    if max_octave < 1:
        max_octave = 1
    if max_octave > 5:
        max_octave = 5

    # PIL HSV : H,S,V ∈ [0,255]
    img_hsv = img.convert("HSV")
    hsv = np.asarray(img_hsv, dtype=np.float32)

    H = hsv[..., 0] / 255.0  # 0..1
    S = hsv[..., 1] / 255.0  # 0..1
    V = hsv[..., 2] / 255.0  # 0..1

    # 1) HUE → demi-tons (0..11)
    semitone = np.floor(H * 12.0).astype(np.int32)
    semitone = np.clip(semitone, 0, 11)

    # 2) VALUE → octave_index (0..max_octave-1)
    #    V=0   → octave 1   (index 0)
    #    V=1   → octave max (index max_octave-1)
    octave_index = np.floor(V * max_octave).astype(np.int32)
    # cas où V=1.0 → max_octave → on ramène à max_octave-1
    octave_index = np.clip(octave_index, 0, max_octave - 1)

    # 3) MIDI note : Do1 = 24
    midi = 24 + octave_index * 12 + semitone

    # Au cas où (même si, mathématiquement, on reste dans la borne)
    midi = np.clip(midi, 24, 24 + (5 * 12) - 1).astype(np.float32)  # jusqu'à Si5

    # 4) Fréquence (tempérament égal, A4=440 Hz)
    freqs_hz = 440.0 * (2.0 ** ((midi - 69.0) / 12.0))

    # 5) Amplitude = saturation (0..1)
    amps = S

    return freqs_hz, amps


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
        "--color-mode",
        type=str,
        choices=["grayscale", "hsv-notes"],
        default="grayscale",
        help=(
            "Mode de conversion image → son : "
            "'grayscale' = mapping spectral continu (niveaux de gris), "
            "'hsv-notes' = HUE→note (Do..Si), VALUE→octave (Do1..Si5), SAT→amplitude."
        ),
    )
    parser.add_argument(
        "--hsv-max-octave",
        type=int,
        default=5,
        help=(
            "Octave maximale pour le mode 'hsv-notes' (entre 1 et 5). "
            "1 = Do1..Si1, 5 = Do1..Si5 (défaut: 5)."
        ),
    )
 
    parser.add_argument(
        "--sr",
        type=int,
        default=48000,
        help="Fréquence d'échantillonnage (Hz, défaut: 48000).",
    )
    parser.add_argument(
        "--duration-s",
        type=float,
        default=None,
        help=(
            "Durée cible du rendu audio (en secondes). "
            "Si fourni, la taille de l'image audio est recalculée en conséquence, "
            "tout en respectant le ratio original de l'image."
        ),
    )
    parser.add_argument(
        "--size",
        type=int,
        default=64,
        help=(
            "Taille base de l'image audio (côté en pixels). "
            "Si --duration-s est renseigné, ce paramètre sert de base "
            "pour le calcul, mais la taille finale peut différer."
        ),
    )
    parser.add_argument(
        "--fmin",
        type=float,
        default=40.0,
        help="Fréquence minimale (Hz) pour le mapping spectral grayscale.",
    )
    parser.add_argument(
        "--fmax",
        type=float,
        default=400.0,
        help="Fréquence maximale (Hz) pour le mapping spectral grayscale.",
    )
    parser.add_argument(
        "--step-ms",
        type=float,
        default=None,
        help="Décalage entre oscillateurs (ms).",
    )
    parser.add_argument(
        "--sustain-s",
        type=float,
        default=0.0,
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
        default=2.0,
        help="Durée du fondu d'attaque/relâche (ms).",
    )
    parser.add_argument(
        "--waveform",
        type=str,
        default=None,
        choices=["saw", "sine", "triangle", "square"],
        help="Forme d'onde utilisée pour le son.",
    )
    parser.add_argument(
        "--voices",
        type=int,
        default=None,
        help="Nombre de voix simultanées (contrôle la durée de vie de chaque oscillateur).",
    )
    parser.add_argument(
        "--mono",
        action="store_true",
        help="Force le rendu en mono (pas de panning).",
    )
    parser.add_argument(
        "--hsv-detune-pct",
        type=float,
        default=0.0,
        help=(
            "Amplitude du détune basé sur la teinte (HSV), en pourcentage. "
            "Ex: 1.0 = ±1%% de variation de fréquence selon la couleur."
        ),
    )

    parser.add_argument(
        "--hsv-blend-gray",
        type=float,
        default=0.0,
        help=(
            "Mélange luminance HSV / luminance en niveaux de gris. "
            "0.0 = tout couleur, 1.0 = tout gris. Ex: 0.15 = 15%% gris, 85%% couleur."
        ),
    )
        

    # Mode artiste (optionnel)
    parser.add_argument(
        "--artist-preset",
        type=str,
        choices=sorted(ARTIST_PRESETS.keys()),
        help=(
            "Preset expressif clé en main (ex: ambient_slow_dark, "
            "ambient_slow_shimmer, glitch_color_burst, neon_rain, ...)."
        ),
    )    

    # Vidéo
    parser.add_argument(
        "--video",
        action="store_true",
        help="Génère également une vidéo (mp4) en plus du WAV.",
    )
    parser.add_argument(
        "--video-out",
        type=str,
        default=None,
        help="Nom de fichier de sortie vidéo (mp4).",
    )
    parser.add_argument(
        "--fps",
        type=int,
        default=25,
        help="Fréquence d'images pour la vidéo (défaut: 25 fps).",
    )
    parser.add_argument(
        "--vis-fmin",
        type=float,
        default=1.0,
        help="Fréquence minimale (Hz) pour la bande visible (visualisation).",
    )
    parser.add_argument(
        "--vis-fmax",
        type=float,
        default=10.0,
        help="Fréquence maximale (Hz) pour la bande visible (visualisation).",
    )
    parser.add_argument(
        "--vis-amp-pct",
        type=float,
        default=5.0,
        help=(
            "Amplitude maximale de la vibration (en pourcentage de la largeur vidéo, "
            "défaut: 5.0%)."
        ),
    )
    parser.add_argument(
        "--gauss-size-pct",
        type=float,
        default=200.0,
        help=(
            "Diamètre de la gaussienne (en pourcentage de la largeur de la vidéo, "
            "défaut: 100%)."
        ),
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
            "Si seule la largeur ou la hauteur est fournie, le ratio de l'image source est conservé."
        ),
    )
    parser.add_argument(
        "--video-size",
        type=str,
        choices=["XS", "S", "M", "L", "XL"],
        default=None,
        help=(
            "Preset de taille vidéo (côté max) : "
            "XS=64, S=128, M=256, L=512, XL=1024. "
            "Conserve le ratio de l'image source."
        ),
    )
   

    return parser


# ─────────────────────────────────────────────
#  Utilitaire : calcul de la taille de l'image audio
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
        audio_w, audio_h = compute_audio_image_shape_from_duration(
            duration_s=args.duration_s,
            step_ms=args.step_ms,
            sustain_s=args.sustain_s,
            voices=args.voices,
            orig_width=orig_w,
            orig_height=orig_h,
        )
        return int(audio_w), int(audio_h)

    # Comportement historique : image audio carrée
    return args.size, args.size

# ─────────────────────────────────────────────
#  Point d'entrée principal
# ─────────────────────────────────────────────

def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    has_preset = args.artist_preset is not None
    if has_preset:
        apply_artist_preset(args)

    # Mode classique : defaults si rien n'a été mis par l'utilisateur ni par un preset
    if not has_preset:
        if args.step_ms is None:
            args.step_ms = 40.0
        if args.waveform is None:
            args.waveform = "saw"
        if args.voices is None:
            args.voices = 32

    # Détermination des fichiers de sortie
    base, _ = os.path.splitext(args.image)
    out_wav = base + ".wav"
    default_video_out = base + ".mp4"
    if args.video_out is None:
        args.video_out = default_video_out

    # Chargement de l'image source (couleur)
    img_src = Image.open(args.image).convert("RGB")
    orig_width, orig_height = img_src.size

    # Choix du format vidéo de sortie
    # Priorité :
    # 1) Si l'utilisateur a donné --video-width/--video-height, on les respecte.
    # 2) Sinon, si --video-size est défini (XS/S/M/L/XL), on calcule une taille
    #    en conservant le ratio de l'image source.
    # 3) Sinon, par défaut, la vidéo utilise exactement la taille de l'image source.
    if args.video_width is None and args.video_height is None:
        if getattr(args, "video_size", None) is not None:
            preset_map = {
                "XS": 64,
                "S": 128,
                "M": 256,
                "L": 512,
                "XL": 1024,
            }
            max_side = preset_map[args.video_size]

            src_max = max(orig_width, orig_height)
            if src_max == 0:
                video_w, video_h = max_side, max_side
            else:
                scale = max_side / float(src_max)
                video_w = int(round(orig_width * scale))
                video_h = int(round(orig_height * scale))

            args.video_width = video_w
            args.video_height = video_h

            print(
                f"🎞️ Format vidéo preset {args.video_size} → "
                f"{args.video_width}x{args.video_height} (ratio conservé)"
            )
        else:
            # cas par défaut : même taille que l'image source
            args.video_width = orig_width
            args.video_height = orig_height
            print(
                f"🎞️ Format vidéo par défaut : même taille que l'image source "
                f"({args.video_width}x{args.video_height})"
            )
    else:
        # Un seul des deux (largeur/hauteur) est défini :
        # on calcule l'autre dimension en conservant le ratio de l'image source.
        if args.video_width is not None and args.video_height is None:
            # largeur fixée → hauteur ajustée
            scale = args.video_width / float(orig_width)
            args.video_height = int(round(orig_height * scale))
            print(
                f"🎞️ Format vidéo : largeur forcée à {args.video_width}px, "
                f"hauteur ajustée à {args.video_height}px (ratio conservé)"
            )
        elif args.video_height is not None and args.video_width is None:
            # hauteur fixée → largeur ajustée
            scale = args.video_height / float(orig_height)
            args.video_width = int(round(orig_width * scale))
            print(
                f"🎞️ Format vidéo : hauteur forcée à {args.video_height}px, "
                f"largeur ajustée à {args.video_width}px (ratio conservé)"
            )

    # Calcul de la taille logique pour l'audio
    audio_w, audio_h = _compute_audio_image_shape(args, (orig_width, orig_height))

    # Redimensionnement pour l'audio (on part de l'image couleur source)
    img_audio = img_src.resize((audio_w, audio_h), Image.LANCZOS)

    # Mapping image -> fréquences / amplitudes selon le mode choisi
    if args.color_mode == "grayscale":
        # --- Base : image en niveaux de gris ---
        img_gray = img_audio.convert("L")
        gray_np = np.asarray(img_gray, dtype=np.float32) / 255.0  # [0,1]

        # --- Luminance couleur via HSV (canal V) ---
        img_hsv = img_audio.convert("HSV")
        hsv_np = np.asarray(img_hsv, dtype=np.float32)
        H = hsv_np[..., 0] / 255.0  # teinte ∈ [0,1]
        # S = hsv_np[..., 1] / 255.0  # saturation (pour plus tard si besoin)
        V = hsv_np[..., 2] / 255.0  # "luminance" couleur ∈ [0,1]

        # --- Solution C : mélange HSV / gris ---
        blend = float(args.hsv_blend_gray)
        # clamp dans [0,1]
        if blend < 0.0:
            blend = 0.0
        elif blend > 1.0:
            blend = 1.0

        # 0.0 = tout couleur (V), 1.0 = tout gris
        lum = (1.0 - blend) * V + blend * gray_np

        # Retour en 0–255 pour réutiliser map_gray_to_freq
        lum_255 = np.clip(lum * 255.0, 0.0, 255.0).astype(np.uint8)
        freqs = map_gray_to_freq(lum_255, args.fmin, args.fmax)

        # --- Solution A : détune basé sur la teinte ---
        detune_pct = float(args.hsv_detune_pct)
        if detune_pct != 0.0:
            # Teinte ∈ [0,1] → [-1,1]
            hue_signed = 2.0 * (H - 0.5)
            detune_factor = 1.0 + (detune_pct / 100.0) * hue_signed
            freqs = freqs * detune_factor.astype(freqs.dtype)

        # Pour l’instant, amplitude uniforme comme avant
        amps = None

    elif args.color_mode == "hsv-notes":
        # Mode discret “HUE → note / VALUE → octave / SAT → amplitude”
        freqs, amps = compute_hsv_notes_from_image(
            img_audio,
            max_octave=args.hsv_max_octave,
        )
        print(
            f"[DEBUG HSV] hsv-max-octave={args.hsv_max_octave}, "
            f"freq_min={float(np.min(freqs)):.2f} Hz, "
            f"freq_max={float(np.max(freqs)):.2f} Hz"
        )
        
        # Dans ce mode, les bornes fmin/fmax sont ignorées, on travaille en notes (Do1..Si5).
    else:
        # fallback de sécurité : mode grayscale
        img_gray = img_audio.convert("L")
        gray = np.asarray(img_gray, dtype=np.uint8)
        freqs = map_gray_to_freq(gray, args.fmin, args.fmax)
        amps = None

    # Stereo / mono
    if args.mono:
        stereo = False
    else:
        # mono si --mono, sinon stéréo
        stereo = True

    # Planification des oscillateurs
    oscs, T = plan_schedule(
        freqs=freqs,
        size=audio_w,          # largeur logique (utilisé pour le panning)
        sr=args.sr,
        step_ms=args.step_ms,
        sustain_s=args.sustain_s,
        stereo=stereo,
        voices=args.voices,
        amps=amps,
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
    print(f"✅ Audio généré : {out_wav}")

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


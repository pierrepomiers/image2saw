# -*- coding: utf-8 -*-
"""
live_core.py
────────────
Moteur de pré-écoute "live" pour Image2Saw.

- Mode live épuré : pas de duration_s, pas de block_ms externe.
- Sample rate figé à 48000 Hz (sr est retiré des paramètres live).
- block_ms forcé à 50 ms en interne.
- size dérivé du crop (jamais exposé).
- Fenêtre de balayage purgée : le son est reconstruit totalement à chaque update.
- Normalisation du volume identique au rendu WAV offline.
- Durée maximale de la séquence live clampée à 4 secondes.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Tuple, List, Optional

import numpy as np
from PIL import Image

from . import cli
from .audio import map_gray_to_freq, plan_schedule, render_audio, Osc


# ─────────────────────────────────────────────
#  Paramètres modes live
# ─────────────────────────────────────────────

LIVE_SR: int = 48000         # Sample rate fixe
LIVE_BLOCK_MS: float = 50.0  # Taille de bloc fixe
LIVE_MAX_DUR_S: float = None # Durée maximale pour la pré-écoute


# Paramètres exclus du mode live
_EXCLUDED_DESTS = {
    "help",
    "image",
    "artist_preset",
    # Vidéo
    "video",
    "video_out",
    "fps",
    "vis_fmin",
    "vis_fmax",
    "vis_amp_pct",
    "gauss_size_pct",
    "video_width",
    "video_height",
    "video_size",
    # Non pertinents en live
    "duration_s",
    "block_ms",
    "sr",
    "size",
}


@dataclass
class ParamSpec:
    name: str
    default: Any
    type: Optional[type]
    choices: Optional[List[Any]] = None
    help: str = ""


# ─────────────────────────────────────────────
#  Récupération des paramètres live depuis la CLI
# ─────────────────────────────────────────────

def _build_param_specs_from_cli() -> Dict[str, ParamSpec]:
    parser = cli.build_parser()
    specs: Dict[str, ParamSpec] = {}

    for action in parser._actions:
        dest = action.dest
        if dest in _EXCLUDED_DESTS:
            continue

        # Ignorer l'argument positionnel "image"
        if not action.option_strings and dest == "image":
            continue

        if action.type is not None:
            p_type: Optional[type] = action.type
        else:
            p_type = bool if isinstance(action.default, bool) else None

        choices = (
            list(action.choices)
            if getattr(action, "choices", None) is not None
            else None
        )
        help_text = getattr(action, "help", "") or ""

        specs[dest] = ParamSpec(
            name=dest,
            default=action.default,
            type=p_type,
            choices=choices,
            help=help_text,
        )

    return specs


_PARAM_SPECS: Dict[str, ParamSpec] = _build_param_specs_from_cli()


def get_param_specs() -> Dict[str, ParamSpec]:
    return _PARAM_SPECS


def get_default_expert_params() -> Dict[str, Any]:
    return {name: spec.default for name, spec in _PARAM_SPECS.items()}


# ─────────────────────────────────────────────
#  Crop
# ─────────────────────────────────────────────

@dataclass
class Crop:
    x: int
    y: int
    w: int
    h: int

    def clamp(self, W: int, H: int) -> "Crop":
        x = max(0, min(self.x, W - 1))
        y = max(0, min(self.y, H - 1))
        w = max(1, self.w)
        h = max(1, self.h)
        if x + w > W:
            w = W - x
        if y + h > H:
            h = H - y
        return Crop(x, y, w, h)


# ─────────────────────────────────────────────
#  Live Engine
# ─────────────────────────────────────────────

class LiveEngine:
    def __init__(
        self,
        image_path: str,
        params: Optional[Dict[str, Any]] = None,
        crop: Optional[Crop] = None,
    ):
        self.image_path = image_path
        self.img_src = Image.open(image_path).convert("RGB")
        self.orig_width, self.orig_height = self.img_src.size

        base = get_default_expert_params()
        if params:
            base.update(params)
        self.params = base

        # 🔸 Default live spécifique : démarrer en "pur gris"
        # (0 = couleur, 1 = gris)
        # → On n'écrase PAS une valeur explicite passée via params.
        if not params or "hsv_blend_gray" not in params:
            self.params["hsv_blend_gray"] = 1.0

        self._apply_live_defaults()

        if crop is None:
            s = 16
            cx = self.orig_width // 2
            cy = self.orig_height // 2
            crop = Crop(cx - s // 2, cy - s // 2, s, s)

        self.crop = crop.clamp(self.orig_width, self.orig_height)

    def _apply_live_defaults(self) -> None:
        """Applique les defaults spécifiques au mode live si valeurs None."""
        if self.params.get("step_ms") is None:
            self.params["step_ms"] = 40.0
        if self.params.get("waveform") is None:
            self.params["waveform"] = "saw"
        if self.params.get("voices") is None:
            self.params["voices"] = 32

    # ---------------- PARAMS ----------------

    def get_params(self) -> Dict[str, Any]:
        return dict(self.params)

    def set_params(self, new_params: Dict[str, Any]) -> None:
        for k, v in new_params.items():
            if k in _PARAM_SPECS:
                self.params[k] = v
        self._apply_live_defaults()

    def set_param(self, name: str, value: Any) -> None:
        if name not in _PARAM_SPECS:
            raise KeyError(f"Param inconnu pour LiveEngine : {name}")
        self.params[name] = value
        self._apply_live_defaults()

    # ---------------- CROP ----------------

    def get_crop(self) -> Crop:
        return self.crop

    def set_crop(self, x: int, y: int, w: int, h: int) -> None:
        self.crop = Crop(x, y, w, h).clamp(self.orig_width, self.orig_height)

    def set_center_crop(self, w: int, h: int) -> None:
        cx = self.orig_width // 2
        cy = self.orig_height // 2
        self.crop = Crop(cx - w // 2, cy - h // 2, w, h).clamp(self.orig_width, self.orig_height)

    # ---------------- FREQUENCES ----------------

    def _extract_crop(self) -> Image.Image:
        c = self.crop
        return self.img_src.crop((c.x, c.y, c.x + c.w, c.y + c.h))

    def _compute_freqs_amps(self) -> Tuple[np.ndarray, Optional[np.ndarray]]:
        """
        Version live alignée sur la logique CLI offline :
        - grayscale : mélange V (HSV) / niveaux de gris via hsv_blend_gray
        - hsv-notes : délègue à compute_hsv_notes_from_image
        """
        img = self._extract_crop()
        p = self.params
        color_mode = p.get("color_mode", "grayscale")

        if color_mode == "grayscale":
            # Niveaux de gris normalisés
            gray_np = np.asarray(img.convert("L"), np.float32) / 255.0

            # HSV pour la composante V (luminance couleur) + teinte H
            hsv_np = np.asarray(img.convert("HSV"), np.float32)
            H = hsv_np[..., 0] / 255.0
            V = hsv_np[..., 2] / 255.0

            # Mélange HSV / gris (même logique que la CLI)
            blend = float(p.get("hsv_blend_gray", 0.0))
            if blend < 0.0:
                blend = 0.0
            elif blend > 1.0:
                blend = 1.0

            # 0.0 = tout couleur (V), 1.0 = tout gris
            lum = (1.0 - blend) * V + blend * gray_np

            # 0–1 → 0–255 uint8
            lum_255 = np.clip(lum * 255.0, 0.0, 255.0).astype(np.uint8)

            fmin = float(p.get("fmin", 40.0))
            fmax = float(p.get("fmax", 8000.0))
            freqs = map_gray_to_freq(lum_255, fmin, fmax)

            # Détune basé sur la teinte (même logique que la CLI)
            detune_pct = float(p.get("hsv_detune_pct", 0.0))
            if detune_pct != 0.0:
                hue_signed = 2.0 * (H - 0.5)  # [0,1] → [-1,1]
                detune_factor = 1.0 + (detune_pct / 100.0) * hue_signed
                freqs = freqs * detune_factor.astype(freqs.dtype)

            amps = None
            return freqs, amps

        elif color_mode == "hsv-notes":
            max_oct = int(p.get("hsv_max_octave", 5))
            freqs, amps = cli.compute_hsv_notes_from_image(
                img,
                max_octave=max_oct,
            )
            return freqs, amps

        else:
            # Fallback simple : gris → fréquence
            gray = np.asarray(img.convert("L"), np.uint8)
            fmin = float(p.get("fmin", 40.0))
            fmax = float(p.get("fmax", 8000.0))
            freqs = map_gray_to_freq(gray, fmin, fmax)
            return freqs, None
    
    # ---------------- RENDER LOOP ----------------

    def render_loop(self) -> np.ndarray:
        freqs, amps = self._compute_freqs_amps()
        _, w = freqs.shape
        stereo = not bool(self.params.get("mono", False))

        step_ms = float(self.params.get("step_ms", 40.0))
        sustain_s = float(self.params.get("sustain_s", 0.0))
        voices = int(self.params.get("voices", 32))

        # Fenêtre entièrement recalculée → pas de “traîne”
        oscs, duration = plan_schedule(
            freqs=freqs,
            size=w,
            sr=LIVE_SR,
            step_ms=step_ms,
            sustain_s=sustain_s,
            stereo=stereo,
            voices=voices,
            amps=amps,
        )

        # Pas de clamp de durée : on rend tout

        audio_lr = render_audio(
            oscs=oscs,
            sr=LIVE_SR,
            block_ms=LIVE_BLOCK_MS,
            fade_ms=float(self.params.get("fade_ms", 2.0)),
            waveform=str(self.params.get("waveform", "saw")),
            tqdm_desc="Live",
            use_tqdm=False,
        )

        # Normalisation identique au WAV offline
        if audio_lr.size > 0:
            peak = float(np.max(np.abs(audio_lr)))
            if peak > 0:
                audio_lr = audio_lr * min(1.0, 0.999 / peak)

        return audio_lr.astype(np.float32)


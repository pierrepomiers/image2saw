#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
live_tui.py
───────────
Interface TUI (terminal interactive) pour le mode live d'Image2Saw.

- Utilise image2saw_pkg.live_core.LiveEngine comme moteur audio.
- Joue en boucle le rendu du crop courant.
- Permet de modifier les paramètres en direct, avec retour sonore immédiat.

Deux modes :

  • Mode PARAMS :
      - ↑ / ↓ : sélectionner un paramètre
      - ← / → : modifier rapide pour waveform / mono / color_mode
      - Entrée : saisir une valeur pour le paramètre sélectionné, validation par Entrée
  • Mode CROP :
      - ↑ / ↓ / ← / → : déplacer le crop (x, y)
      - + / - : agrandir / réduire le crop (w, h)
      - c : recentrer un crop 16×16

Raccourcis globaux :
      - TAB : alterner PARAMS / CROP
      - r   : regénérer le son (au cas où)
      - q   : quitter

Dépendances :
    pip install numpy sounddevice
"""

import argparse
import threading
import time
from typing import List

import numpy as np
import sounddevice as sd
import curses

from image2saw_pkg.live_core import LiveEngine, get_param_specs


# ─────────────────────────────────────────────
#  Looper audio stéréo
# ─────────────────────────────────────────────

class AudioLooper:
    """
    Joue un buffer stéréo en boucle via sounddevice.
    - update_buffer(new_buffer) permet de changer le son en temps réel.
    """

    def __init__(self, sample_rate: int):
        self.sample_rate = sample_rate
        self.buffer = np.zeros((1, 2), dtype=np.float32)
        self.pos = 0
        self.lock = threading.Lock()
        self.stream = sd.OutputStream(
            samplerate=self.sample_rate,
            channels=2,
            dtype="float32",
            callback=self._callback,
        )

    def _callback(self, outdata, frames, time_info, status):
        if status:
            # On évite d'afficher dans le callback, ça flinguerait le TUI.
            pass
        with self.lock:
            buf = self.buffer
            if buf.size == 0:
                outdata.fill(0)
                return

            n_samples = buf.shape[0]
            p = self.pos

            remaining = n_samples - p
            if frames <= remaining:
                outdata[:, 0] = buf[p:p+frames, 0]
                outdata[:, 1] = buf[p:p+frames, 1]
                self.pos = (p + frames) % n_samples
            else:
                # Fin de buffer + wrap
                part1 = remaining
                outdata[:part1, 0] = buf[p:, 0]
                outdata[:part1, 1] = buf[p:, 1]
                part2 = frames - part1

                loops = part2 // n_samples
                rest = part2 % n_samples

                # On boucle sur le buffer complet
                for i in range(loops):
                    start = part1 + i * n_samples
                    end = start + n_samples
                    outdata[start:end, 0] = buf[:, 0]
                    outdata[start:end, 1] = buf[:, 1]

                if rest > 0:
                    start = part1 + loops * n_samples
                    end = start + rest
                    outdata[start:end, 0] = buf[:rest, 0]
                    outdata[start:end, 1] = buf[:rest, 1]

                self.pos = rest

    def start(self):
        self.stream.start()

    def stop(self):
        self.stream.stop()

    def update_buffer(self, new_buffer: np.ndarray):
        """
        Remplace le buffer par un nouveau.
        new_buffer doit être (n_samples, 2) ou (n_samples,) mono.
        """
        with self.lock:
            if new_buffer.ndim == 1:
                new_buffer = np.stack([new_buffer, new_buffer], axis=-1)
            elif new_buffer.ndim == 2 and new_buffer.shape[1] == 1:
                new_buffer = np.repeat(new_buffer, 2, axis=1)
            self.buffer = new_buffer.astype(np.float32)
            self.pos = 0


# ─────────────────────────────────────────────
#  Helpers TUI
# ─────────────────────────────────────────────

def _format_value_for_display(value) -> str:
    if isinstance(value, float):
        return f"{value:.3g}"
    return str(value)


def _cycle_choice(choices: List, current, direction: int):
    if not choices:
        return current
    try:
        idx = choices.index(current)
    except ValueError:
        idx = 0
    idx = (idx + direction) % len(choices)
    return choices[idx]


def _draw_ui(
    stdscr,
    engine: LiveEngine,
    param_names: List[str],
    selected_idx: int,
    mode: str,
    status_msg: str,
):
    stdscr.erase()
    max_y, max_x = stdscr.getmaxyx()

    crop = engine.get_crop()
    try:
        w = engine.orig_width
        h = engine.orig_height
    except AttributeError:
        w = h = None

    title = "Image2Saw Live TUI"
    stdscr.addstr(0, 0, title[:max_x - 1], curses.A_BOLD)

    if w is not None and h is not None:
        stdscr.addstr(
            1,
            0,
            f"Image: {w}x{h}  Crop: x={crop.x}, y={crop.y}, w={crop.w}, h={crop.h}"[:max_x - 1],
        )

    stdscr.addstr(2, 0, f"Mode: {'PARAMS' if mode == 'params' else 'CROP'}"[:max_x - 1])

    params = engine.get_params()
    specs = get_param_specs()

    start_row = 4
    max_rows = max_y - start_row - 3  # 3 dernières lignes : aide + status

    if len(param_names) <= max_rows:
        first_visible = 0
    else:
        half = max_rows // 2
        first_visible = max(0, selected_idx - half)
        if first_visible + max_rows > len(param_names):
            first_visible = len(param_names) - max_rows

    for i in range(max_rows):
        idx = first_visible + i
        if idx >= len(param_names):
            break

        name = param_names[idx]
        spec = specs[name]
        val = params.get(name)

        line = f"{name:15s} = {_format_value_for_display(val)}"
        if spec.choices:
            line += f"  ({'/'.join(map(str, spec.choices))})"

        if idx == selected_idx and mode == "params":
            attr = curses.A_REVERSE
        else:
            attr = curses.A_NORMAL

        stdscr.addstr(start_row + i, 0, line[:max_x - 1], attr)

    # Aide
    if mode == "params":
        help_line = (
            "↑/↓: choisir param | ←/→: waveform/mono/color_mode | Entrée: saisir valeur | "
            "TAB: mode CROP | r: regen | q: quit"
        )
    else:
        help_line = (
            "↑/↓/←/→: déplacer crop | +/-: resize | c: center 16x16 | "
            "TAB: mode PARAMS | r: regen | q: quit"
        )

    stdscr.addstr(max_y - 3, 0, help_line[:max_x - 1], curses.A_DIM)

    # Aide sur le param sélectionné
    if 0 <= selected_idx < len(param_names):
        sel_name = param_names[selected_idx]
        sel_spec = specs[sel_name]
        help_text = sel_spec.help or ""
        stdscr.addstr(max_y - 2, 0, f"{sel_name}: {help_text}"[:max_x - 1])

    # Status
    stdscr.addstr(max_y - 1, 0, status_msg[:max_x - 1], curses.A_BOLD)

    stdscr.refresh()


def _regenerate_audio(engine: LiveEngine, looper: AudioLooper) -> str:
    try:
        buf = engine.render_loop()
        looper.update_buffer(buf)
        return "Audio regen OK"
    except Exception as e:
        return f"Erreur rendu audio: {e}"


def _edit_param_with_input(
    stdscr,
    engine: LiveEngine,
    looper: AudioLooper,
    name: str
) -> str:
    """
    Saisie manuelle d'une valeur pour un paramètre :
      - affiche un prompt en bas,
      - lit la ligne,
      - parse selon le type,
      - met à jour + regen audio.
    """
    specs = get_param_specs()
    spec = specs[name]
    all_params = engine.get_params()
    cur_val = all_params.get(name)

    max_y, max_x = stdscr.getmaxyx()
    prompt = f"{name} (actuel={_format_value_for_display(cur_val)}): "
    stdscr.move(max_y - 1, 0)
    stdscr.clrtoeol()
    stdscr.addstr(max_y - 1, 0, prompt[:max_x - 1])
    stdscr.refresh()

    curses.echo()
    try:
        raw_bytes = stdscr.getstr(
            max_y - 1,
            min(len(prompt), max_x - 1),
            max_x - len(prompt) - 1,
        )
    except Exception:
        curses.noecho()
        return "Saisie annulée."
    curses.noecho()

    try:
        raw = raw_bytes.decode("utf-8").strip()
    except Exception:
        raw = ""

    if not raw:
        return "Entrée vide, annulé."

    # Parsing selon type
    try:
        if spec.type is int:
            new_val = int(raw)
        elif spec.type is float:
            new_val = float(raw)
        elif spec.type is bool:
            if raw.lower() in ("1", "true", "yes", "y", "on"):
                new_val = True
            elif raw.lower() in ("0", "false", "no", "n", "off"):
                new_val = False
            else:
                return "Valeur booléenne attendue (true/false, 1/0, yes/no)."
        else:
            new_val = raw
    except ValueError:
        return "Impossible de convertir la valeur saisie."

    try:
        engine.set_param(name, new_val)
        status = _regenerate_audio(engine, looper)
        return f"{status} | {name} = {_format_value_for_display(new_val)}"
    except Exception as e:
        return f"Erreur set_param({name}): {e}"


# ─────────────────────────────────────────────
#  Boucle principale curses
# ─────────────────────────────────────────────

def tui_main(stdscr, args):
    curses.curs_set(0)
    stdscr.nodelay(False)
    stdscr.keypad(True)

    engine = LiveEngine(args.image)

    # Crop initial
    if (
        args.crop_w is not None
        and args.crop_h is not None
        and args.x is not None
        and args.y is not None
    ):
        engine.set_crop(args.x, args.y, args.crop_w, args.crop_h)
    elif args.crop_w is not None and args.crop_h is not None:
        engine.set_center_crop(args.crop_w, args.crop_h)

    # Sample rate fixe : aligné sur LIVE_SR dans live_core.py (48000 typiquement)
    sr = 48000

    looper = AudioLooper(sample_rate=sr)
    status = _regenerate_audio(engine, looper)
    looper.start()

    specs = get_param_specs()
    param_names = sorted(specs.keys())
    selected_idx = 0
    mode = "params"

    running = True

    while running:
        _draw_ui(stdscr, engine, param_names, selected_idx, mode, status)
        ch = stdscr.getch()

        if ch == ord('q'):
            running = False
            break

        if ch == ord('\t'):
            mode = "crop" if mode == "params" else "params"
            status = f"Mode basculé: {mode.upper()}"
            continue

        if ch == ord('r'):
            status = _regenerate_audio(engine, looper)
            continue

        if mode == "params":
            # Navigation
            if ch == curses.KEY_UP:
                if selected_idx > 0:
                    selected_idx -= 1
            elif ch == curses.KEY_DOWN:
                if selected_idx < len(param_names) - 1:
                    selected_idx += 1

            # Flèches gauche/droite : rapide pour waveform / mono / color_mode
            elif ch in (curses.KEY_LEFT, curses.KEY_RIGHT):
                if not (0 <= selected_idx < len(param_names)):
                    continue
                name = param_names[selected_idx]
                direction = -1 if ch == curses.KEY_LEFT else 1

                if name not in ("waveform", "mono", "color_mode"):
                    status = "Pour ce paramètre, utilise Entrée pour saisir une valeur."
                    continue

                spec = specs[name]
                all_params = engine.get_params()
                cur_val = all_params.get(name)

                if name == "mono":
                    new_val = not bool(cur_val)
                else:
                    if not spec.choices:
                        status = f"Param '{name}' n'a pas de liste de choix."
                        continue
                    new_val = _cycle_choice(spec.choices, cur_val, direction)

                try:
                    # Cas particulier : changement de color_mode
                    if name == "color_mode":
                        # Cycle dans les modes : "grayscale" / "hsv-notes"
                        engine.set_param(name, new_val)

                        # Principe : mix HSV/gris (0=couleur, 1=gris)
                        # - Quand on passe en "grayscale" → forcer blend = 1.0 (pur gris)
                        # - Quand on passe en "hsv-notes" → forcer blend = 0.0 (pur couleur)
                        if new_val == "grayscale":
                            engine.set_param("hsv_blend_gray", 1.0)
                        elif new_val == "hsv-notes":
                            engine.set_param("hsv_blend_gray", 0.0)
                    else:
                        # waveform / mono
                        engine.set_param(name, new_val)

                    status = _regenerate_audio(engine, looper)
                except Exception as e:
                    status = f"Erreur set_param({name}): {e}"
                
            # Entrée : saisie manuelle
            elif ch in (10, 13, curses.KEY_ENTER):
                if not (0 <= selected_idx < len(param_names)):
                    continue
                name = param_names[selected_idx]
                status = _edit_param_with_input(stdscr, engine, looper, name)

        else:  # mode == "crop"
            crop = engine.get_crop()
            x, y, w, h = crop.x, crop.y, crop.w, crop.h
            moved = False
            resized = False

            if ch == curses.KEY_UP:
                y -= 1
                moved = True
            elif ch == curses.KEY_DOWN:
                y += 1
                moved = True
            elif ch == curses.KEY_LEFT:
                x -= 1
                moved = True
            elif ch == curses.KEY_RIGHT:
                x += 1
                moved = True
            elif ch in (ord('+'), ord('=')):
                w += 1
                h += 1
                resized = True
            elif ch in (ord('-'), ord('_')):
                if w > 1 and h > 1:
                    w -= 1
                    h -= 1
                    resized = True
            elif ch == ord('c'):
                engine.set_center_crop(16, 16)
                status = _regenerate_audio(engine, looper)
                continue

            if moved or resized:
                engine.set_crop(x, y, w, h)
                status = _regenerate_audio(engine, looper)

    looper.stop()
    time.sleep(0.1)


# ─────────────────────────────────────────────
#  Entry point
# ─────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Interface TUI live pour Image2Saw (flèches & raccourcis)."
    )
    parser.add_argument("image", help="Chemin de l'image source")
    parser.add_argument(
        "--crop-w", type=int, default=None, help="Largeur initiale du crop"
    )
    parser.add_argument(
        "--crop-h", type=int, default=None, help="Hauteur initiale du crop"
    )
    parser.add_argument("--x", type=int, default=None, help="X initial du crop")
    parser.add_argument("--y", type=int, default=None, help="Y initial du crop")
    args = parser.parse_args()

    curses.wrapper(tui_main, args)


if __name__ == "__main__":
    main()


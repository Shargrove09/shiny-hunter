"""Show what the detectors see on the screen right now.

Grabs the game, normalises it to native 240x160, scores every detector, and
writes an annotated PNG with each region boxed. Sends no input.

Use it when a wait_for_screen times out on a screen you can see is correct —
it answers "what is the matcher actually looking at" in one shot.

Run from the repo root:

    python tools/diagnose_screen.py            # one snapshot
    python tools/diagnose_screen.py --watch 20 # print scores for 20s
"""
import argparse
import json
import os
import sys
import time
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                'src', 'shinyhunter'))

import cv2  # noqa: E402
import numpy as np  # noqa: E402

from config import ConfigManager, project_path  # noqa: E402
from image_processor import ImageProcessor, crop, describe_scale, resolve_region  # noqa: E402
from screenshot_manager import ScreenshotManager  # noqa: E402

OUT_DIR = 'screenshots/diagnose'


def detectors(config):
    """Every named detector: (label, roi, template_path, threshold)."""
    return [
        ('battle_detector', config.battle_detector_roi,
         project_path(config.battle_detector_template), config.battle_detector_threshold),
        ('battle_menu', config.battle_menu_roi,
         project_path(config.battle_menu_template), config.battle_menu_threshold),
    ]


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--watch', type=float, default=0,
                        help="Keep printing scores for this many seconds")
    parser.add_argument('--interval', type=float, default=0.5)
    args = parser.parse_args()

    config = ConfigManager().get_config()
    manager = ScreenshotManager()
    processor = ImageProcessor()

    raw = manager.grab_array()
    print(f"capture  : {raw.shape[1]}x{raw.shape[0]}")
    detected, reason = manager.detect_viewport(raw)
    if detected:
        print(f"viewport : {detected['pixels']}  {describe_scale(detected['pixels'])}")
        stored = resolve_region(config.game_viewport, raw.shape)
        drift = max(abs(a - b) for a, b in zip(detected['pixels'], stored))
        if drift > 4:
            print(f"!! stored viewport {stored} is {drift}px off the detected one — "
                  "sprite and detector crops will not line up")
    else:
        print(f"viewport : not verifiable ({reason}) — expected outside a battle")

    def snapshot(label=''):
        native = manager.grab_native()
        line = []
        for name, roi, template, threshold in detectors(config):
            matched, score = processor.matches_template(native, template,
                                                        region=roi, threshold=threshold)
            line.append(f"{name}={score:.3f}{'*' if matched else ' '}")
        print(f"  {label}{'  '.join(line)}")
        return native

    if args.watch:
        print(f"\nwatching for {args.watch}s ('*' = over threshold). "
              "Move through a battle and watch which fires.\n")
        end = time.time() + args.watch
        while time.time() < end:
            snapshot()
            time.sleep(args.interval)
        native = manager.grab_native()
    else:
        print()
        native = snapshot()

    os.makedirs(OUT_DIR, exist_ok=True)
    stamp = datetime.now().strftime('%Y%m%d_%H%M%S')

    frame_path = os.path.join(OUT_DIR, f'{stamp}_native.png')
    cv2.imwrite(frame_path, native)

    canvas = cv2.resize(native, (720, 480), interpolation=cv2.INTER_NEAREST)
    colours = [(0, 0, 255), (0, 200, 0), (255, 128, 0)]
    for index, (name, roi, template, threshold) in enumerate(detectors(config)):
        x, y, w, h = resolve_region(roi, native.shape)
        colour = colours[index % len(colours)]
        cv2.rectangle(canvas, (x * 3, y * 3), ((x + w) * 3, (y + h) * 3), colour, 2)
        cv2.putText(canvas, name, (x * 3, max(12, y * 3 - 4)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, colour, 1)
    sx, sy, sw, sh = resolve_region(config.enemy_sprite_roi, native.shape)
    cv2.rectangle(canvas, (sx * 3, sy * 3), ((sx + sw) * 3, (sy + sh) * 3), (255, 0, 255), 2)
    cv2.putText(canvas, 'enemy_sprite', (sx * 3, max(12, sy * 3 - 4)),
                cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 0, 255), 1)

    annotated = os.path.join(OUT_DIR, f'{stamp}_regions.png')
    cv2.imwrite(annotated, canvas)

    # Each ROI as a strip beside the template it is compared against.
    strips = []
    for name, roi, template, threshold in detectors(config):
        live = cv2.resize(crop(native, roi), (240, 144), interpolation=cv2.INTER_NEAREST)
        stored = cv2.imread(template)
        stored = (cv2.resize(stored, (240, 144), interpolation=cv2.INTER_NEAREST)
                  if stored is not None else np.zeros_like(live))
        pair = np.hstack([live, stored])
        pair = cv2.copyMakeBorder(pair, 22, 4, 4, 4, cv2.BORDER_CONSTANT, value=(30, 30, 30))
        cv2.putText(pair, f'{name}: LIVE | TEMPLATE', (6, 16),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 255), 1)
        strips.append(pair)
    compare = os.path.join(OUT_DIR, f'{stamp}_compare.png')
    cv2.imwrite(compare, np.vstack(strips))

    print(f"\nwrote:\n  {frame_path}\n  {annotated}\n  {compare}")
    print("\nOpen the *_compare.png: if LIVE and TEMPLATE show different things, the")
    print("region is wrong or the geometry drifted. If they look the same but the")
    print("score is low, the template needs recutting from a current capture.")


if __name__ == '__main__':
    main()

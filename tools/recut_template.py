"""Recut a detector template from the screen as it looks right now.

Templates are small patches of the normalised 240x160 frame. Normalising makes
position and scale consistent between captures, but not resampling: a viewport at
6x native averages 6x6 blocks down to one pixel, at 3x it averages 3x3, and on a
patch of small text the resulting anti-aliasing differs enough to drop a correct
match well below threshold. So a template cut at one window size can legitimately
fail at another even when the geometry is perfect.

Put the game on the screen the template is meant to detect, then run this.

    python tools/recut_template.py battle_menu        # preview only
    python tools/recut_template.py battle_menu --write
    python tools/recut_template.py battle_menu --roi 150 126 48 20 --write
"""
import argparse
import json
import os
import shutil
import sys
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                'src', 'shinyhunter'))

import cv2  # noqa: E402
import numpy as np  # noqa: E402

from config import ConfigManager, project_path  # noqa: E402
from image_processor import ImageProcessor, crop, describe_scale, resolve_region  # noqa: E402
from screenshot_manager import ScreenshotManager  # noqa: E402

CONFIG_PATH = 'shinyhunter_config.json'
OUT_DIR = 'screenshots/diagnose'

NAMES = ('battle_detector', 'battle_menu')


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('name', choices=NAMES)
    parser.add_argument('--roi', nargs=4, type=int, metavar=('X', 'Y', 'W', 'H'),
                        help="Use a different native-pixel region and save it to config")
    parser.add_argument('--samples', type=int, default=3,
                        help="Frames to median together (rejects a stray animation frame)")
    parser.add_argument('--gap', type=float, default=0.25)
    parser.add_argument('--write', action='store_true')
    args = parser.parse_args()

    config = ConfigManager().get_config()
    manager = ScreenshotManager()
    processor = ImageProcessor()

    roi = args.roi or getattr(config, f'{args.name}_roi')
    template_path = project_path(getattr(config, f'{args.name}_template'))
    threshold = getattr(config, f'{args.name}_threshold')

    raw = manager.grab_array()
    detected, reason = manager.detect_viewport(raw)
    print(f"capture  : {raw.shape[1]}x{raw.shape[0]}")
    if detected:
        print(f"viewport : {detected['pixels']}  {describe_scale(detected['pixels'])}")
    else:
        print(f"viewport : not verifiable ({reason})")
    print(f"region   : {list(roi)} native\n")

    frames = []
    for index in range(max(1, args.samples)):
        if index:
            import time
            time.sleep(args.gap)
        frames.append(manager.grab_native().astype(np.float32))
    native = np.median(np.stack(frames), axis=0).astype(np.uint8)

    # A moving screen means this is not a stable state to cut a template from.
    spread = float(np.abs(np.stack(frames) - native.astype(np.float32)).mean())
    patch = crop(native, roi)

    old = cv2.imread(template_path)
    if old is not None:
        matched, score = processor.matches_template(native, template_path,
                                                    region=roi, threshold=threshold)
        print(f"current template scores {score:.3f} here "
              f"({'over' if matched else 'UNDER'} the {threshold} threshold)")
    print(f"frame stability across {len(frames)} samples: {spread:.2f} "
          f"{'(steady)' if spread < 3 else '(MOVING - the screen is still animating)'}")

    os.makedirs(OUT_DIR, exist_ok=True)
    stamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    scale = 8
    strip = [cv2.resize(patch, (roi[2] * scale, roi[3] * scale), interpolation=cv2.INTER_NEAREST)]
    if old is not None:
        strip.append(cv2.resize(old, (roi[2] * scale, roi[3] * scale),
                                interpolation=cv2.INTER_NEAREST))
    preview = np.hstack(strip)
    preview = cv2.copyMakeBorder(preview, 24, 4, 4, 4, cv2.BORDER_CONSTANT, value=(30, 30, 30))
    cv2.putText(preview, 'NEW (live)   |   CURRENT', (6, 17),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)
    preview_path = os.path.join(OUT_DIR, f'{stamp}_recut_{args.name}.png')
    cv2.imwrite(preview_path, preview)
    print(f"\npreview  : {preview_path}")

    if not args.write:
        print("\nLooks right? Re-run with --write to save it.")
        return

    if spread >= 3:
        print("\nRefusing to save: the screen is still animating, so this patch would")
        print("bake in a transient frame. Wait for it to settle and try again.")
        sys.exit(1)

    if old is not None:
        backup = template_path.replace('.png', f'.{stamp}.bak.png')
        shutil.copy2(template_path, backup)
        print(f"backup   : {backup}")

    os.makedirs(os.path.dirname(template_path), exist_ok=True)
    cv2.imwrite(template_path, patch)
    print(f"written  : {template_path}")

    if args.roi:
        with open(CONFIG_PATH, encoding='utf-8') as handle:
            stored = json.load(handle)
        stored[f'{args.name}_roi'] = [int(v) for v in args.roi]
        with open(CONFIG_PATH, 'w', encoding='utf-8') as handle:
            json.dump(stored, handle, indent=2)
        print(f"config   : {args.name}_roi = {list(args.roi)}")

    matched, score = processor.matches_template(manager.grab_native(), template_path,
                                                region=roi, threshold=threshold)
    print(f"\nverify   : scores {score:.3f} against a fresh capture "
          f"({'PASS' if matched else 'still under threshold'})")
    print("\nNow confirm it does NOT fire on the wrong screen:")
    print("  python tools/diagnose_screen.py --watch 20")


if __name__ == '__main__':
    main()

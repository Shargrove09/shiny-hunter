"""Find where the wild sprite actually sits, and set the sprite ROI to match.

Run it during a wild battle. It needs no library and no background plate: the
battle backdrop is horizontal banding, so it is nearly flat across any row, and
the sprite is the one thing in the upper right with strong left-to-right
structure.

Validated against ten real captures spanning four species and both battle
stages: it recovers [141, 10, 64, 64] where the hand-derived box was
[143, 8, 64, 64], and every sprite fits inside.

    python tools/tune_sprite_roi.py             # measure and preview
    python tools/tune_sprite_roi.py --write     # save the ROI to config
    python tools/tune_sprite_roi.py --roi 143 8 64 64 --write   # set it by hand

A GBA battle sprite is at most 64x64, so the box stays 64x64 and only moves.
"""
import argparse
import json
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                'src', 'shinyhunter'))

import cv2  # noqa: E402
import numpy as np  # noqa: E402

from config import ConfigManager, project_path  # noqa: E402
from image_processor import crop, describe_scale, resolve_region  # noqa: E402
from screenshot_manager import ScreenshotManager  # noqa: E402

# The config in use, not one relative to whatever directory you happen to
# be in -- a CWD-relative path meant writing one file and reading another.
CONFIG_PATH = ConfigManager().path
OUT_DIR = 'screenshots/diagnose'
SPRITE_BOX = 64

# The wild sprite lives in the upper right. The search stops above row 90 so the
# player's own HP box -- which only appears once the command menu is up -- cannot
# be mistaken for the sprite.
SEARCH = (108, 0, 132, 90)      # x, y, w, h in native pixels

# The player's HP box intrudes from this row down. The sprite box must end above
# it, or menu-stage frames pick up box edges that are absent from "appeared"
# frames and the same species stops matching itself.
PLAYER_HP_TOP = 74


def find_sprite(native, search=SEARCH, threshold=18):
    """Bounding box of the sprite within the search area, in native pixels.

    Keys on horizontal gradient. The battle backdrop is horizontal banding, so it
    varies down the frame but is nearly flat across any row; the sprite is the
    one thing in the upper right with strong left-to-right structure. A per-row
    median backdrop was tried first and failed -- the platform ellipse breaks the
    assumption that a row is mostly uniform.
    """
    x0, y0, w, h = search
    area = cv2.cvtColor(native[y0:y0 + h, x0:x0 + w], cv2.COLOR_BGR2GRAY).astype(np.float32)

    gradient = np.abs(cv2.Sobel(area, cv2.CV_32F, 1, 0, ksize=3))
    mask = (gradient > threshold).astype(np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))

    count, _labels, stats, _ = cv2.connectedComponentsWithStats(mask, 8)
    if count < 2:
        return None, mask

    biggest = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
    x, y, width, height = (int(stats[biggest, i]) for i in range(4))
    if width < 12 or height < 12:
        return None, mask
    return (x0 + x, y0 + y, width, height), mask


def suggest_box(found, clear_below=PLAYER_HP_TOP):
    """Place the fixed 64x64 box around a located sprite.

    Centred horizontally, but the vertical placement is anchored to the bottom
    rather than centred on what was seen: GBA battle sprites are bottom-aligned
    on the platform, so a larger species grows upward, and the box must still end
    above the player's HP box.
    """
    fx, fy, fw, fh = found
    x = max(0, min(240 - SPRITE_BOX, fx + fw // 2 - SPRITE_BOX // 2))
    y = max(0, min(160 - SPRITE_BOX, clear_below - SPRITE_BOX))
    return [x, y, SPRITE_BOX, SPRITE_BOX]


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--roi', nargs=4, type=int, metavar=('X', 'Y', 'W', 'H'),
                        help="Set this native-pixel ROI directly, skipping detection")
    parser.add_argument('--samples', type=int, default=3)
    parser.add_argument('--clear-below', type=int, default=PLAYER_HP_TOP,
                        help="Native row the player's HP box starts at; the sprite "
                             "box is placed to end above it (default 74)")
    parser.add_argument('--write', action='store_true')
    args = parser.parse_args()

    config = ConfigManager().get_config()
    manager = ScreenshotManager()
    current = list(config.enemy_sprite_roi)

    if args.roi:
        chosen = [int(v) for v in args.roi]
        native = manager.grab_native()
        found = None
    else:
        frames = []
        for index in range(max(1, args.samples)):
            if index:
                import time
                time.sleep(0.2)
            frames.append(manager.grab_native().astype(np.float32))
        native = np.median(np.stack(frames), axis=0).astype(np.uint8)

        detected, _ = manager.detect_viewport()
        if detected:
            print(f"viewport : {detected['pixels']}  {describe_scale(detected['pixels'])}")

        found, _mask = find_sprite(native)
        if found is None:
            print("\nNo sprite found in the upper-right area.")
            print("Either this is not a battle screen, or the viewport is wrong —")
            print("check with: python tools/diagnose_screen.py")
            sys.exit(1)

        fx, fy, fw, fh = found
        print(f"\nsprite occupies : x {fx}..{fx + fw - 1}  y {fy}..{fy + fh - 1}  ({fw}x{fh})")

        chosen = suggest_box(found, args.clear_below)

    print(f"current ROI     : {current}")
    print(f"suggested ROI   : {chosen}")
    if chosen == current:
        print("                  (unchanged — the box already fits)")
    else:
        print(f"                  shift of dx={chosen[0] - current[0]} dy={chosen[1] - current[1]}")

    if found:
        fx, fy, fw, fh = found
        inside = (fx >= current[0] and fy >= current[1]
                  and fx + fw <= current[0] + current[2]
                  and fy + fh <= current[1] + current[3])
        print(f"sprite inside the CURRENT box? {'yes' if inside else 'NO — it is being clipped'}")

    os.makedirs(OUT_DIR, exist_ok=True)
    stamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    canvas = cv2.resize(native, (720, 480), interpolation=cv2.INTER_NEAREST)
    for rect, colour, label in ((current, (0, 0, 255), 'current'),
                                (chosen, (0, 220, 0), 'suggested')):
        x, y, w, h = rect
        cv2.rectangle(canvas, (x * 3, y * 3), ((x + w) * 3, (y + h) * 3), colour, 2)
        cv2.putText(canvas, label, (x * 3 + 4, max(12, y * 3 - 4)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, colour, 1)
    overview = os.path.join(OUT_DIR, f'{stamp}_sprite_roi.png')
    cv2.imwrite(overview, canvas)

    pair = np.hstack([
        cv2.resize(crop(native, current), (256, 256), interpolation=cv2.INTER_NEAREST),
        cv2.resize(crop(native, chosen), (256, 256), interpolation=cv2.INTER_NEAREST)])
    pair = cv2.copyMakeBorder(pair, 24, 4, 4, 4, cv2.BORDER_CONSTANT, value=(30, 30, 30))
    cv2.putText(pair, 'CURRENT   |   SUGGESTED', (6, 17),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)
    crops = os.path.join(OUT_DIR, f'{stamp}_sprite_crops.png')
    cv2.imwrite(crops, pair)
    print(f"\npreview  : {overview}\n           {crops}")

    if not args.write:
        print("\nThe sprite should sit centred with a little margin. "
              "Happy? Re-run with --write.")
        return

    with open(CONFIG_PATH, encoding='utf-8') as handle:
        stored = json.load(handle)
    stored['enemy_sprite_roi'] = chosen
    with open(CONFIG_PATH, 'w', encoding='utf-8') as handle:
        json.dump(stored, handle, indent=2)
    print(f"\nconfig   : enemy_sprite_roi = {chosen}")

    hunt = project_path('hunts/powerplant.json')
    if os.path.exists(hunt):
        with open(hunt, encoding='utf-8') as handle:
            spec = json.load(handle)
        if 'rois' in spec and 'enemy_sprite' in spec['rois']:
            spec['rois']['enemy_sprite'] = chosen
            with open(hunt, 'w', encoding='utf-8') as handle:
                json.dump(spec, handle, indent=2)
            # The hunt file's rois shadow config, so leaving it stale would make
            # the config change look like it had no effect.
            print(f"{hunt}: rois.enemy_sprite = {chosen}")

    if chosen != current:
        print("\nThe library was built against the old box, so rebuild it:")
        print("  python tools/build_library.py powerplant --force")
        print("  python tools/score_library.py powerplant")


if __name__ == '__main__':
    main()

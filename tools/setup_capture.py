"""Point Shiny Hunter at a game window and locate the game inside it.

Replaces screen-rectangle capture. Capturing the window by id means the capture
no longer depends on where the window sits, what is on top of it, or how the
display scales — the three things that silently corrupt a region capture.

Run from the repo root:

    python tools/setup_capture.py                  # list windows
    python tools/setup_capture.py --owner Playback # capture it, find the game
    python tools/setup_capture.py --owner Playback --write
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                'src', 'shinyhunter'))

import cv2  # noqa: E402
import numpy as np  # noqa: E402

import window_capture  # noqa: E402
from image_processor import detect_game_viewport, describe_scale, validate_viewport  # noqa: E402

CONFIG_PATH = 'shinyhunter_config.json'
PREVIEW_PATH = 'screenshots/window_capture_preview.png'


def show_windows():
    windows = window_capture.list_windows()
    if not windows:
        print("No capturable windows found. Is the game window open and un-minimised?")
        return
    print(f"{len(windows)} window(s), largest first:\n")
    for w in windows:
        label = w['title'] or '(untitled)'
        print(f"  owner={w['owner']!r:24s} {label[:34]:36s} "
              f"{w['width']}x{w['height']} @ ({w['x']},{w['y']})")
    print("\nPick one with:  python tools/setup_capture.py --owner <owner>")


def write_config(owner, title, viewport):
    with open(CONFIG_PATH, 'r', encoding='utf-8') as handle:
        config = json.load(handle)

    config['capture_mode'] = 'window'
    config['capture_window_owner'] = owner
    config['capture_window_title'] = title
    config['game_viewport'] = viewport

    with open(CONFIG_PATH, 'w', encoding='utf-8') as handle:
        json.dump(config, handle, indent=2)

    print(f"\nconfig updated:")
    print(f"  capture_mode         = window")
    print(f"  capture_window_owner = {owner!r}")
    print(f"  game_viewport        = {viewport}")
    print("\nRegion settings (screenshot_region_*, emulator_*) are now unused.")
    print("Existing calibration references and templates are stale — recapture them.")


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--owner', help="App name to capture, e.g. Playback")
    parser.add_argument('--title', default='', help="Optional window title substring")
    parser.add_argument('--write', action='store_true', help="Commit to config")
    parser.add_argument('--viewport', nargs=4, type=float, metavar=('X', 'Y', 'W', 'H'),
                        help="Set the viewport manually as fractions (0-1) of the window")
    parser.add_argument('--full', action='store_true',
                        help="Use the whole window as the viewport (skip detection)")
    args = parser.parse_args()

    if not window_capture.available():
        print("Window capture needs macOS with Quartz (pyobjc). Use tools/find_region.py.")
        sys.exit(1)

    if not args.owner:
        show_windows()
        return

    window = window_capture.resolve_window(args.owner, args.title)
    print(f"Window: {window['owner']!r} {window['title']!r}  "
          f"id={window['id']}  {window['width']}x{window['height']} points")

    image = window_capture.capture(window['id'])
    bgr = cv2.cvtColor(np.asarray(image), cv2.COLOR_RGB2BGR)
    print(f"Captured: {bgr.shape[1]}x{bgr.shape[0]} pixels "
          f"({bgr.shape[1] / max(window['width'], 1):.1f}x the point size)")

    if args.viewport:
        viewport = [round(v, 5) for v in args.viewport]
        chosen_px = None
        print(f"\nViewport set manually: {viewport}")
    elif args.full:
        viewport = [0.0, 0.0, 1.0, 1.0]
        chosen_px = (0, 0, bgr.shape[1], bgr.shape[0])
        print("\nUsing the whole window as the viewport.")
    else:
        candidates = detect_game_viewport(bgr)
        if not candidates:
            print("\nNo 3:2 game area found inside the window.")
            print("Save the preview and set it by hand:")
            print("  python tools/setup_capture.py --owner <owner> --viewport X Y W H")
            print("  (fractions of the window, e.g. 0.02 0.11 0.96 0.85)")
            print("Or use the whole window with --full.")
            cv2.imwrite(PREVIEW_PATH, bgr)
            print(f"Preview: {PREVIEW_PATH}")
            return

        print(f"\n{len(candidates)} candidate game area(s):\n")
        for i, cand in enumerate(candidates[:5], start=1):
            x, y, w, h = cand['pixels']
            print(f"  #{i}  {w}x{h}px at ({x},{y})  ratio={cand['ratio']:.3f}  "
                  f"off-by {cand['error'] * 100:4.1f}%   fraction={cand['fraction']}")

        best = candidates[0]
        viewport = best['fraction']
        chosen_px = best['pixels']

        ok, reason = validate_viewport(chosen_px)
        print(f"\nscale: {describe_scale(chosen_px)}")
        if not ok:
            print(f"!! This does not look like the game viewport: {reason}")
            print("   Detection is only reliable on a BATTLE screen — outside battle,")
            print("   Gen 3 fills beyond the map edge with black and that reads as")
            print("   letterbox. Start a wild battle and run this again.")

    os.makedirs(os.path.dirname(PREVIEW_PATH) or '.', exist_ok=True)
    preview = bgr.copy()
    if chosen_px:
        x, y, w, h = chosen_px
        cv2.rectangle(preview, (x, y), (x + w, y + h), (0, 0, 255), 4)
    cv2.imwrite(PREVIEW_PATH, preview)
    print(f"\nPreview: {PREVIEW_PATH}  (red box = the game area that will be used)")

    if args.write:
        write_config(window['owner'], args.title, viewport)
    else:
        print("\nCheck the preview, then commit with --write")


if __name__ == '__main__':
    main()

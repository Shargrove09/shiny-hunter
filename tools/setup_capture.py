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
from config import ConfigManager, project_path  # noqa: E402
from image_processor import (detect_game_viewport, describe_scale,  # noqa: E402
                             explain_viewport_mismatch, resolve_region, to_native,
                             validate_viewport, viewport_fits)

PREVIEW_PATH = project_path('screenshots/window_capture_preview.png')


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


def write_config(owner, title, viewport, capture_size):
    path = ConfigManager().path
    config = {}
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as handle:
            config = json.load(handle)

    config['capture_mode'] = 'window'
    config['capture_window_owner'] = owner
    config['capture_window_title'] = title
    config['game_viewport'] = viewport
    # Recorded so a later mismatch can name what changed. The fraction is only
    # correct at this capture's aspect ratio.
    config['game_viewport_capture'] = [int(capture_size[0]), int(capture_size[1])]

    with open(path, 'w', encoding='utf-8') as handle:
        json.dump(config, handle, indent=2)

    print(f"\nconfig updated: {os.path.relpath(path, project_path('.'))}")
    print(f"  capture_mode          = window")
    print(f"  capture_window_owner  = {owner!r}")
    print(f"  game_viewport         = {viewport}")
    print(f"  game_viewport_capture = {config['game_viewport_capture']}")
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
    parser.add_argument('--force', action='store_true',
                        help="Save even a viewport that fails validation")
    args = parser.parse_args()

    if not window_capture.available():
        print(window_capture.unavailable_reason())
        print("Falling back to screen-region capture: python tools/find_region.py")
        sys.exit(1)
    print(f"backend: {window_capture.backend()}")

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
        # Resolve it so a hand-typed viewport is previewed and validated like a
        # detected one; --force is the way past the gate if it is deliberate.
        chosen_px = resolve_region(viewport, bgr.shape)
        print(f"\nViewport set manually: {viewport}")
        print(f"  -> {chosen_px[2]}x{chosen_px[3]}  {describe_scale(chosen_px)}")
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

    # What the CURRENT config would crop, beside what was just detected. Setup
    # previously drew only the detected box, so it always looked right even when
    # config pointed somewhere else entirely -- and that is precisely how a stale
    # viewport survived being looked at.
    current = list(ConfigManager().get_config().game_viewport)
    current_ok, current_px, current_reason = viewport_fits(current, bgr.shape)
    if current != viewport:
        print(f"\ncurrent config viewport: {current}")
        print(f"  -> {current_px[2]}x{current_px[3]} on this capture, "
              f"{'OK — ' if current_ok else 'INVALID — '}{current_reason}")
        if not current_ok:
            print("  This is what every detector has been looking at. Writing the "
                  "detected viewport below replaces it.")

    os.makedirs(os.path.dirname(PREVIEW_PATH) or '.', exist_ok=True)
    preview = bgr.copy()
    if current_px and current != viewport:
        x, y, w, h = current_px
        cv2.rectangle(preview, (x, y), (x + w, y + h), (0, 165, 255), 3)
        cv2.putText(preview, 'current config', (x + 6, max(24, y + 30)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 165, 255), 2)
    if chosen_px:
        x, y, w, h = chosen_px
        cv2.rectangle(preview, (x, y), (x + w, y + h), (0, 0, 255), 4)
        cv2.putText(preview, 'detected', (x + 6, max(24, y - 10)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 255), 2)
    cv2.imwrite(PREVIEW_PATH, preview)
    print(f"\nPreview: {PREVIEW_PATH}")
    print("  red = the game area that will be used"
          + ("   orange = what config crops today" if current_px and current != viewport else ""))

    # The 240x160 each one actually produces — the frame the matcher sees.
    renders = [to_native(bgr, viewport)]
    labels = ['DETECTED']
    if current_px and current != viewport:
        renders.append(to_native(bgr, current))
        labels.append('CURRENT CONFIG')
    strip = np.hstack([cv2.resize(r, (480, 320), interpolation=cv2.INTER_NEAREST)
                       for r in renders])
    strip = cv2.copyMakeBorder(strip, 26, 4, 4, 4, cv2.BORDER_CONSTANT, value=(30, 30, 30))
    cv2.putText(strip, '   |   '.join(labels), (8, 19),
                cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 0, 255), 1)
    native_path = PREVIEW_PATH.replace('.png', '_native.png')
    cv2.imwrite(native_path, strip)
    print(f"         {native_path}  (the 240x160 frame the matcher sees)")

    if args.write:
        if chosen_px and not args.force and not validate_viewport(chosen_px)[0]:
            print("\nRefusing to save: this viewport is not a 3:2 box at an integer "
                  "scale, so it is not the game.")
            print("Detection is only reliable on a BATTLE screen. Start a wild battle "
                  "and run this again,")
            print("or pass --force if you are certain.")
            sys.exit(1)
        write_config(window['owner'], args.title, viewport, (bgr.shape[1], bgr.shape[0]))
    else:
        print("\nCheck the preview, then commit with --write")


if __name__ == '__main__':
    main()

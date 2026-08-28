"""Capture battle screenshots for building a sprite library.

Samples MUST come through the same capture path the hunt uses, or library
entries will not match hunt-time crops. This uses the app's own ScreenshotManager
and the region from shinyhunter_config.json, so the pixels are identical to what
the detector will see.

Full frames are saved, never crops — ROIs can change, and re-cropping a saved
frame is free while re-capturing a route is not.

Run from the repo root:

    # Hotkey mode (default): focus the emulator, press F9 on each battle screen
    python tools/capture_samples.py route4_grass

    # Interval mode: grabs every 2s, skipping frames near-identical to the last
    python tools/capture_samples.py route4_grass --interval 2.0

Press Esc (hotkey mode) or Ctrl+C to finish.
"""
import argparse
import os
import sys
import time
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                'src', 'shinyhunter'))

import numpy as np  # noqa: E402
from PIL import Image  # noqa: E402

from config import ConfigManager  # noqa: E402
from screenshot_manager import ScreenshotManager  # noqa: E402

_MANAGER = None


def grab(config=None):
    """Grab through ScreenshotManager so samples match hunt-time captures exactly.

    Whichever capture mode is configured, the same code path is used here and by
    the detector — that identity is what makes the sprite library valid.
    """
    global _MANAGER
    if _MANAGER is None:
        _MANAGER = ScreenshotManager()
    return _MANAGER.grab()


def frame_difference(a: Image.Image, b: Image.Image) -> float:
    """Mean absolute difference of two frames, 0-255, on a downscaled grayscale copy."""
    if a is None or b is None:
        return 255.0
    small_a = np.asarray(a.convert('L').resize((160, 120)), dtype=np.int16)
    small_b = np.asarray(b.convert('L').resize((160, 120)), dtype=np.int16)
    return float(np.abs(small_a - small_b).mean())


def save(image: Image.Image, out_dir: str, count: int) -> str:
    stamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')[:-3]
    path = os.path.join(out_dir, f"{count:03d}_{stamp}.png")
    image.save(path)
    return path


def run_interval(config, out_dir, args):
    print(f"Interval mode: grabbing every {args.interval}s, "
          f"skipping frames within {args.min_diff} of the last saved one.")
    print("Walk the route. Ctrl+C when done.\n")

    last_saved = None
    count = 0
    try:
        while True:
            frame = grab(config)
            diff = frame_difference(frame, last_saved)
            if diff >= args.min_diff:
                count += 1
                path = save(frame, out_dir, count)
                last_saved = frame
                print(f"[{count:3d}] saved {os.path.basename(path)}  (diff {diff:.1f})")
            time.sleep(args.interval)
    except KeyboardInterrupt:
        pass
    return count


def run_hotkey(config, out_dir, args):
    try:
        from pynput import keyboard
    except ImportError:
        print("pynput unavailable — falling back to interval mode.")
        return run_interval(config, out_dir, args)

    print(f"Hotkey mode: focus the emulator, press {args.key.upper()} on each battle screen.")
    print("Press Esc to finish.\n")

    state = {'count': 0}
    target = getattr(keyboard.Key, args.key)

    def on_press(key):
        if key == keyboard.Key.esc:
            return False
        if key == target:
            state['count'] += 1
            path = save(grab(config), out_dir, state['count'])
            print(f"[{state['count']:3d}] saved {os.path.basename(path)}")

    with keyboard.Listener(on_press=on_press) as listener:
        try:
            listener.join()
        except KeyboardInterrupt:
            pass
    return state['count']


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('hunt_name', help="Route name, e.g. route4_grass")
    parser.add_argument('--interval', type=float, default=None,
                        help="Seconds between grabs. Omit for hotkey mode.")
    parser.add_argument('--min-diff', type=float, default=6.0,
                        help="Interval mode: skip frames this similar to the last saved (0-255).")
    parser.add_argument('--key', default='f9',
                        help="Hotkey mode: capture key (default f9 — must be unbound in the emulator).")
    parser.add_argument('--out', default=None, help="Output directory override.")
    args = parser.parse_args()

    config = ConfigManager().get_config()
    mode = getattr(config, 'capture_mode', 'region')

    out_dir = args.out or os.path.join('sprite_library', args.hunt_name, '_samples')
    os.makedirs(out_dir, exist_ok=True)

    if mode == 'window':
        print(f"Capture mode   : window ({config.capture_window_owner!r})")
    else:
        width = config.screenshot_capture_width or config.emulator_width
        height = config.screenshot_capture_height or config.emulator_height
        print(f"Capture mode   : region  x={config.screenshot_region_x} "
              f"y={config.screenshot_region_y} {width}x{height}")
        print("                 (window capture is more reliable: "
              "python tools/setup_capture.py)")
    print(f"Output         : {out_dir}\n")

    probe = grab()
    print(f"Captured       : {probe.size[0]}x{probe.size[1]}")
    if probe.convert('L').getextrema()[1] < 20:
        print("!! WARNING: the capture is almost entirely black — wrong window, "
              "or it is covered.\n")

    print("Capture every species on the route, plus 2-3 frames of the SAME species")
    print("(different levels ideally) so same-species variation can be measured.")
    print("Do not move the emulator window after this point.\n")

    if args.interval:
        count = run_interval(config, out_dir, args)
    else:
        count = run_hotkey(config, out_dir, args)

    print(f"\nDone — {count} frames in {out_dir}")
    if count < 10:
        print("That is on the thin side; aim for ~20 covering every species on the route.")


if __name__ == '__main__':
    main()

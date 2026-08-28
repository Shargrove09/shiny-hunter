"""Locate the emulator's GBA viewport on screen and write it into the config.

The capture region is currently derived from the Tk boundary widget in
cross_platform_app.py, which is not the same rectangle as the game. That leaves
app chrome and black letterbox inside every capture, which both inflates
correlations toward 1.0 and makes any fraction-based ROI meaningless.

This finds the actual game viewport by its 3:2 aspect ratio, writes an annotated
preview so the choice can be confirmed by eye, and optionally commits it.

Run from the repo root:

    python tools/find_region.py                 # detect + write preview
    python tools/find_region.py --write 1       # commit candidate #1 to config
    python tools/find_region.py --manual X Y W H  # skip detection, set it yourself
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                'src', 'shinyhunter'))

import cv2  # noqa: E402
import numpy as np  # noqa: E402
from PIL import Image  # noqa: E402

GBA_RATIO = 240 / 160  # 1.5
CONFIG_PATH = 'shinyhunter_config.json'


def grab_fullscreen():
    """Full-desktop grab, using the same backends the app uses."""
    try:
        import pyautogui
        return pyautogui.screenshot()
    except Exception:
        from PIL import ImageGrab
        return ImageGrab.grab()


def logical_screen_size():
    """Screen size in points — the coordinate space region captures use.

    On Retina these differ from the pixels a full-screen grab returns: macOS
    `screencapture -R` takes points, while an unbounded grab returns the physical
    framebuffer. Mixing the two puts the region at double the intended offset and
    size, which silently captures off-screen padding.
    """
    try:
        import pyautogui
        size = pyautogui.size()
        return int(size.width), int(size.height)
    except Exception:
        return None, None


def find_candidates(bgr, ratio_tol=0.12, min_width=200, black_level=24):
    """Find non-black rectangles whose aspect ratio is close to the GBA's 3:2.

    The emulator letterboxes the game with black bars, so the viewport shows up
    as a bright island in a dark frame.
    """
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    _, lit = cv2.threshold(gray, black_level, 255, cv2.THRESH_BINARY)
    lit = cv2.morphologyEx(lit, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))

    contours, _ = cv2.findContours(lit, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)

    screen_area = bgr.shape[0] * bgr.shape[1]

    out = []
    for contour in contours:
        x, y, w, h = cv2.boundingRect(contour)
        if w < min_width or h < min_width * 2 / 3:
            continue
        # The desktop itself is often near-3:2; it is never the viewport.
        if w * h > screen_area * 0.8:
            continue
        ratio = w / h
        error = abs(ratio - GBA_RATIO) / GBA_RATIO
        if error <= ratio_tol:
            out.append({'rect': (x, y, w, h), 'ratio': ratio, 'error': error, 'area': w * h})

    # Rank by how exactly the ratio matches first, then by size. A real viewport is
    # a near-integer scale of 240x160, so it sits at ~0% error; ranking by area alone
    # lets any large roughly-3:2 window outrank it.
    out.sort(key=lambda c: (round(c['error'] / 0.015), -c['area']))
    return out


def annotate(bgr, candidates, path, scale=1.0):
    """Draw candidates and save the preview at logical size.

    The preview is downscaled to points so that every coordinate the user reads
    off it is already in the same units the config stores.
    """
    canvas = bgr.copy()
    for i, cand in enumerate(candidates[:9], start=1):
        x, y, w, h = cand['logical']
        px, py, pw, ph = cand['rect']
        cv2.rectangle(canvas, (px, py), (px + pw, py + ph), (0, 0, 255), max(2, int(3 * scale)))
        cv2.putText(canvas, f"#{i} {x},{y} {w}x{h} r={cand['ratio']:.3f}",
                    (px + 6, max(int(24 * scale), py - 8)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7 * scale, (0, 0, 255), max(2, int(2 * scale)))

    if scale != 1.0:
        canvas = cv2.resize(canvas,
                            (int(round(canvas.shape[1] / scale)), int(round(canvas.shape[0] / scale))),
                            interpolation=cv2.INTER_AREA)
    cv2.imwrite(path, canvas)
    return path


def check_bounds(x, y, w, h, screen_w, screen_h):
    """Refuse a region that runs off screen — it captures padding, not pixels."""
    if not screen_w:
        return
    if x < 0 or y < 0 or x + w > screen_w or y + h > screen_h:
        print(f"\n!! Region ({x}, {y}, {w}x{h}) extends past the {screen_w}x{screen_h} "
              f"point screen.")
        print("   The capture would include off-screen padding. Refusing to write.")
        sys.exit(1)


def write_config(x, y, w, h):
    with open(CONFIG_PATH, 'r', encoding='utf-8') as handle:
        config = json.load(handle)

    before = (config.get('screenshot_region_x'), config.get('screenshot_region_y'),
              config.get('emulator_width'), config.get('emulator_height'))

    config['screenshot_region_x'] = int(x)
    config['screenshot_region_y'] = int(y)
    config['emulator_width'] = int(w)
    config['emulator_height'] = int(h)
    # An explicit crop override would fight the region we just set.
    config['screenshot_capture_width'] = 0
    config['screenshot_capture_height'] = 0

    with open(CONFIG_PATH, 'w', encoding='utf-8') as handle:
        json.dump(config, handle, indent=2)

    print(f"\nconfig updated: {before}  ->  ({x}, {y}, {w}, {h})")
    print("Existing calibration references and templates are now stale — recapture them.")


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--write', type=int, metavar='N',
                        help="Commit candidate N (1-based) to shinyhunter_config.json")
    parser.add_argument('--manual', nargs=4, type=int, metavar=('X', 'Y', 'W', 'H'),
                        help="Skip detection and write these absolute coords")
    parser.add_argument('--tolerance', type=float, default=0.12,
                        help="Aspect-ratio tolerance (default 0.12)")
    parser.add_argument('--preview', default='screenshots/region_preview.png')
    args = parser.parse_args()

    log_w, log_h = logical_screen_size()

    if args.manual:
        x, y, w, h = args.manual
        print(f"Manual region: x={x} y={y} {w}x{h}  ratio={w / h:.3f} (GBA is {GBA_RATIO:.3f})")
        check_bounds(x, y, w, h, log_w, log_h)
        write_config(x, y, w, h)
        return

    shot = grab_fullscreen()
    bgr = cv2.cvtColor(np.asarray(shot.convert('RGB')), cv2.COLOR_RGB2BGR)
    phys_w, phys_h = bgr.shape[1], bgr.shape[0]

    scale = 1.0
    if log_w:
        scale = phys_w / log_w
    print(f"Screen: {log_w}x{log_h} points, grabbed {phys_w}x{phys_h} pixels "
          f"(scale {scale:.2f}x)")
    if scale != 1.0:
        print("Retina display — detection runs on pixels, results are converted to points,")
        print("which is the space the capture region actually uses.")

    candidates = find_candidates(bgr, ratio_tol=args.tolerance)
    for cand in candidates:
        x, y, w, h = cand['rect']
        cand['logical'] = (int(round(x / scale)), int(round(y / scale)),
                           int(round(w / scale)), int(round(h / scale)))

    if not candidates:
        print("\nNo 3:2 region found. Either the emulator is not visible, or it is")
        print("stretched to a non-native aspect. Open the preview and read the")
        print("coordinates off it, then re-run with --manual X Y W H.")
        annotate(bgr, [], args.preview, scale)
        print(f"Preview (in points): {args.preview}")
        return

    print(f"\n{len(candidates)} candidate viewport(s), best ratio match first:")
    print("  (coordinates in POINTS — ready to use as-is)\n")
    for i, cand in enumerate(candidates[:9], start=1):
        x, y, w, h = cand['logical']
        flag = "" if cand['error'] < 0.02 else "   <- not a clean 3:2, likely window chrome"
        print(f"  #{i}  x={x:5d} y={y:5d}  {w:5d}x{h:<5d}  "
              f"ratio={cand['ratio']:.3f}  off-by {cand['error'] * 100:4.1f}%{flag}")

    os.makedirs(os.path.dirname(args.preview) or '.', exist_ok=True)
    annotate(bgr, candidates, args.preview, scale)
    print(f"\nAnnotated preview (in points): {args.preview}")

    if candidates[0]['error'] >= 0.02:
        print("\nNote: the best candidate is not a clean 3:2. Set the emulator to an")
        print("integer scale (2x/3x/4x) with no smoothing filter and re-run — the")
        print("viewport should then match 1.500 almost exactly.")

    if args.write:
        if not 1 <= args.write <= len(candidates):
            print(f"\nNo candidate #{args.write}.")
            sys.exit(1)
        x, y, w, h = candidates[args.write - 1]['logical']
        check_bounds(x, y, w, h, log_w, log_h)
        write_config(x, y, w, h)
    else:
        print("\nCheck the preview, then commit with:  "
              "python tools/find_region.py --write 1")


if __name__ == '__main__':
    main()

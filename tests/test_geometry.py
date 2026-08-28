"""Geometry must not depend on the size of the game window.

The bug this guards: the viewport and ROIs were stored as fractions, so resizing
the window re-mapped them onto a different slice of the game. Sprites landed at a
different scale and offset, a live Magneton scored 0.693 against its own library
entry, and the hunt reported it as SHINY.

    python tests/test_geometry.py
"""
import glob
import json
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'src', 'shinyhunter'))
os.chdir(REPO)

import cv2  # noqa: E402
import numpy as np  # noqa: E402

from image_processor import (ImageProcessor, crop, detect_game_viewport,  # noqa: E402
                             describe_scale, resolve_region, to_native,
                             validate_viewport)
from sprite_library import SpriteLibrary  # noqa: E402

FAILS = []


def check(label, cond, extra=''):
    print(('PASS' if cond else 'FAIL') + f'  {label} {extra}')
    if not cond:
        FAILS.append(label)


CFG = json.load(open('shinyhunter_config.json'))
def frame_viewport(frame):
    """Each stored frame's own viewport, not today's config.

    A sample is only interpretable through the geometry it was captured under;
    using the current one crops a different region of the game and every
    comparison silently becomes self-referential.
    """
    found = detect_game_viewport(frame)
    if found and validate_viewport(found[0]['pixels'])[0]:
        return found[0]['fraction']
    return CFG['game_viewport']


VIEWPORT = CFG['game_viewport']
SPRITE_ROI = CFG['enemy_sprite_roi']
DETECT_ROI = CFG['battle_detector_roi']
TEMPLATE = CFG['battle_detector_template']
BATTLE = sorted(glob.glob('sprite_library/powerplant/_samples/*.png'))
OVER = sorted(glob.glob('sprite_library/powerplant_overworld/_samples/*.png'))
LABELS = json.load(open('sprite_library/powerplant/_labels.json'))

print("=== ROIs are native pixels, not fractions ===")
check('enemy_sprite_roi is native px', SPRITE_ROI == [143, 8, 64, 64], str(SPRITE_ROI))
check('battle_detector_roi is native px', DETECT_ROI == [80, 136, 40, 20], str(DETECT_ROI))
check('resolve_region reads them as pixels',
      resolve_region(SPRITE_ROI, (160, 240, 3)) == (143, 8, 64, 64))

print("\n=== to_native always yields exactly 240x160 ===")
for path in BATTLE[:3]:
    frame = cv2.imread(path)
    native = to_native(frame, frame_viewport(frame))
    check(f'{os.path.basename(path)[:14]} -> 240x160',
          native.shape[:2] == (160, 240), str(native.shape[:2]))

# ---------------------------------------------------------------- the big one
print("\n=== a resized window must not change the native crop ===")
base = cv2.imread(BATTLE[0])
BASE_VP = frame_viewport(base)
reference = crop(to_native(base, BASE_VP), SPRITE_ROI)
print(f"  reference capture {base.shape[1]}x{base.shape[0]} -> sprite {reference.shape[:2]}")

for scale in (0.5, 0.75, 1.25, 1.5, 2.0):
    width = int(base.shape[1] * scale)
    height = int(base.shape[0] * scale)
    resized = cv2.resize(base, (width, height), interpolation=cv2.INTER_AREA)
    sprite = crop(to_native(resized, BASE_VP), SPRITE_ROI)
    diff = float(np.abs(sprite.astype(int) - reference.astype(int)).mean())
    # Resampling to and from a different size cannot be bit-exact, but it must be
    # far below the level that moves a match score.
    check(f'window x{scale:<4} ({width}x{height})', diff < 8.0, f'mean|diff|={diff:.2f}')

print("\n=== and a resized window must not change the verdict ===")
library = SpriteLibrary(os.path.join(REPO, 'sprite_library', 'powerplant'))
for path in BATTLE[:4]:
    species = LABELS[os.path.basename(path)]
    frame = cv2.imread(path)
    verdicts = set()
    for scale in (0.6, 1.0, 1.6):
        resized = cv2.resize(frame, (int(frame.shape[1] * scale), int(frame.shape[0] * scale)),
                             interpolation=cv2.INTER_AREA)
        result = library.identify(crop(to_native(resized, frame_viewport(frame)), SPRITE_ROI))
        verdicts.add((result.verdict, result.species))
    check(f'{species:10s} same verdict at every size', len(verdicts) == 1, str(verdicts))

# ------------------------------------------------------------------ detection
print("\n=== viewport validation: accept battle, reject overworld ===")
for path in BATTLE[:5]:
    candidates = detect_game_viewport(cv2.imread(path))
    ok, reason = validate_viewport(candidates[0]['pixels'] if candidates else None)
    check(f'battle    {os.path.basename(path)[:14]}', ok, reason)
for path in OVER[:5]:
    candidates = detect_game_viewport(cv2.imread(path))
    ok, reason = validate_viewport(candidates[0]['pixels'] if candidates else None)
    check(f'overworld {os.path.basename(path)[:14]} rejected', not ok, reason)

print("\n=== detector in native space beats the old raw-capture path ===")
processor = ImageProcessor()
native_battle, native_over = [], []
for path in BATTLE[:5]:
    frame = cv2.imread(path)
    _, score = processor.matches_template(to_native(frame, frame_viewport(frame)),
                                          TEMPLATE, region=DETECT_ROI, threshold=0.75)
    native_battle.append(score)
for path in OVER[:5]:
    frame = cv2.imread(path)
    _, score = processor.matches_template(to_native(frame, frame_viewport(frame)),
                                          TEMPLATE, region=DETECT_ROI, threshold=0.75)
    native_over.append(score)
margin = min(native_battle) - max(native_over)
check('battle scores ~1.000', min(native_battle) > 0.99, f'min={min(native_battle):.3f}')
check('overworld scores low', max(native_over) < 0.5, f'max={max(native_over):.3f}')
check('margin beats the old 0.935/0.307', margin > 0.63, f'margin={margin:.3f}')

print("\n=== scale reporting ===")
check('exact multiple reads as exact', 'exact' in describe_scale((0, 0, 1440, 960)))
check('non-integer is called out', 'not an integer' in describe_scale((0, 0, 1400, 933)))

print("\n" + ("ALL PASS" if not FAILS else f"FAILURES: {FAILS}"))
sys.exit(1 if FAILS else 0)

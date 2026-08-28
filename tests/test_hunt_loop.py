"""End-to-end checks for the random-encounter hunt loop.

Driven by the real captured frames in sprite_library/, with input and capture
stubbed, so the whole decision path runs without the game being present.

    python tests/test_hunt_loop.py
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

from image_processor import (to_native, detect_game_viewport,  # noqa: E402
                             validate_viewport)
from shiny_hunter_controller import (ShinyHunterController, Outcome,  # noqa: E402
                                     SHINY, NOT_SHINY, UNKNOWN_SPRITE,
                                     TIMEOUT, COMPLETE)

FAILS = []


def check(label, cond, extra=''):
    print(('PASS' if cond else 'FAIL') + f'  {label} {extra}')
    if not cond:
        FAILS.append(label)


# Snapshot evidence directories so cleanup can spare anything already there.
PRE_EXISTING_CROPS = set()
for _d in ('_shiny', '_unknown'):
    PRE_EXISTING_CROPS.update(glob.glob(f'sprite_library/powerplant/{_d}/*.png'))

SPEC = json.load(open('hunts/powerplant.json'))
CFG = json.load(open('shinyhunter_config.json'))
BATTLE = sorted(glob.glob('sprite_library/powerplant/_samples/*.png'))
OVER = sorted(glob.glob('sprite_library/powerplant_overworld/_samples/*.png'))
LABELS = json.load(open('sprite_library/powerplant/_labels.json'))


def build(frames):
    """Controller whose capture yields `frames` in order, holding the last."""
    c = ShinyHunterController(log_function=lambda m: None)
    c.startup_countdown = 0
    c.running = True
    state = {'i': 0, 'input': [], 'resets': 0}

    def grab():
        f = frames[min(state['i'], len(frames) - 1)]
        state['i'] += 1
        img = cv2.imread(f) if isinstance(f, str) else f
        return img

    def grab_native():
        # Detect each frame's own viewport. Stored samples were captured under
        # whatever geometry was current then; normalising them with today's
        # config crops a different region of the game entirely.
        img = grab()
        if img.shape[0] == 160 and img.shape[1] == 240:
            return img
        found = detect_game_viewport(img)
        viewport = (found[0]['fraction']
                    if found and validate_viewport(found[0]['pixels'])[0]
                    else CFG['game_viewport'])
        return to_native(img, viewport)

    c.screenshot_manager.grab_array = grab
    c.screenshot_manager.grab_native = grab_native
    c.screenshot_manager.take_screenshot = lambda n: f'screenshots/{n}'
    c.screenshot_manager.take_timestamped_screenshot = lambda p: f'screenshots/{p}_x.png'
    c.input_handler.ensure_window_focused = lambda: True
    c.input_handler.execute_input_step = lambda s: state['input'].append(s)
    c.input_handler.hold_key_for = lambda k, d: state['input'].append(('move', k))
    c.input_handler.press_keys_down = lambda ks: None
    c.input_handler.release_keys = lambda ks: None
    c.input_handler.restart_sequence = lambda: state.__setitem__('resets', state['resets'] + 1)
    c._alert = lambda t, m: None
    return c, state


def hue_rotate(bgr, degrees):
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV).astype(np.int16)
    hsv[:, :, 0] = (hsv[:, :, 0] + degrees // 2) % 180
    hsv[:, :, 1] = np.clip(hsv[:, :, 1] * 1.3, 0, 255)
    return cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2BGR)


CHECK_STEP = SPEC['encounter_sequence'][2]

print("=== check_library on real frames ===")
for path in BATTLE:
    species = LABELS[os.path.basename(path)]
    c, _ = build([path])
    out = c._step_check_library(dict(CHECK_STEP, samples=1), SPEC)
    ok = out == NOT_SHINY and out.detail['species'] == species
    check(f'{species:10s} -> normal', ok,
          f"got {out!r}"[:70] if not ok else f"shape={out.detail['shape_score']}")

print("\n=== a recoloured sprite is called shiny ===")
for path in (BATTLE[0], BATTLE[1], BATTLE[7]):
    species = LABELS[os.path.basename(path)]
    fake = hue_rotate(cv2.imread(path), 120)
    c, _ = build([fake])
    out = c._step_check_library(dict(CHECK_STEP, samples=1), SPEC)
    check(f'{species:10s} recoloured -> shiny', out == SHINY,
          f"{out!r}"[:60])
    if out == SHINY:
        check(f'  {species} shiny crop saved',
              out.detail.get('crop_path') and os.path.exists(out.detail['crop_path']))

print("\n=== an unseen species is unknown, not normal ===")
c, _ = build([BATTLE[0]])
lib = c._get_library(SPEC, CHECK_STEP)
saved = dict(lib.entries)
lib.entries = {k: v for k, v in saved.items() if k != 'magnemite'}
out = c._step_check_library(dict(CHECK_STEP, samples=1), SPEC)
check('held-out species is not "normal"', out != NOT_SHINY, f'{out!r}'[:60])
check('unknown crop saved for review',
      out != UNKNOWN_SPRITE or os.path.exists(out.detail.get('crop_path', '')))
lib.entries = saved

print("\n=== full encounter sequence: walk -> detect -> identify ===")
walk = dict(SPEC['encounter_sequence'][0], step_duration=0.0, max_steps=20, poll_every=2)
wait = dict(SPEC['encounter_sequence'][1], timeout=1.0, poll_interval=0.01)
c, st = build(OVER[:3] + [BATTLE[0]])
result = c._run_sequence([walk, wait, dict(CHECK_STEP, samples=1)], SPEC)
check('sequence reaches a verdict', result == NOT_SHINY, repr(result)[:70])
check('identified the species', result.detail.get('species') == 'magnemite')
check('walked before finding it', any(i == ('move', 'left') for i in st['input']))

print("\n=== flee waits for the command menu ===")
MENU_FRAMES = [p for p in BATTLE if os.path.basename(p) in
               {'006_20260818_164526_493.png', '007_20260818_164546_007.png',
                '008_20260818_164554_590.png'}]
APPEARED = [p for p in BATTLE if p not in MENU_FRAMES]

# Intro text showing, then the menu arrives: flee must not press into nothing.
c, st = build(APPEARED[:2] + MENU_FRAMES + OVER)
fast_flee = [dict(x, timeout=2.0, poll_interval=0.01) if x['type'] == 'wait_for_screen' else x
             for x in SPEC['flee_sequence']]
result = c._run_sequence(fast_flee, SPEC)
check('flee completes once the menu appears', result == COMPLETE, repr(result)[:60])
presses = [i.get('key') for i in st['input'] if isinstance(i, dict) and i['type'] == 'press']
check('navigated to RUN after waiting', presses[-3:] == ['right', 'down', 'x'], str(presses))

# Menu never appears: flee must fail rather than mash blindly.
c, st = build(APPEARED[:1])
result = c._run_sequence(fast_flee, SPEC)
check('flee fails when the menu never shows', result == TIMEOUT, repr(result)[:50])
presses = [i.get('key') for i in st['input'] if isinstance(i, dict) and i['type'] == 'press']
check('did not press direction keys blindly', 'right' not in presses, str(presses))

print("\n=== retry dispatch ===")
c, st = build([OVER[0]])
check('on_not_shiny=flee runs the flee sequence',
      c._handle_retry(SPEC) and st['resets'] == 0)

c, st = build([OVER[0]])
check("legacy hunts still default to reset",
      c._handle_retry({}) and st['resets'] == 1)

c, st = build([OVER[0]])
check('explicit empty reset_sequence does nothing',
      c._handle_retry({'reset_sequence': []}) and st['resets'] == 0)

print("\n=== flee that never clears escalates, then pauses ===")
c, st = build([BATTLE[0]])          # battle never goes away
spec = dict(SPEC, max_flee_attempts=2, max_consecutive_resets=2)
spec['flee_sequence'] = [dict(s, timeout=0.2, poll_interval=0.05) if s['type'] == 'wait_for_screen'
                         else s for s in SPEC['flee_sequence']]
c._handle_retry(spec)
check('escalated to a reset', st['resets'] >= 1, f"{st['resets']} resets")
c._handle_retry(spec)
check('pauses after repeated resets', c.paused, f'resets={c.consecutive_resets}')

print("\n=== unknown sprite pauses and points at the crop ===")
c, _ = build([BATTLE[0]])
seen = {}
c.unknown_sprite_callback = seen.update
stopped = c._handle_unknown(SPEC, {'crop_path': 'x.png', 'reason': 'test'})
check('returns False (do not continue)', stopped is False)
check('hunt paused', c.paused)
check('GUI callback fired', seen.get('reason') == 'test')

c, _ = build([BATTLE[0]])
c._handle_unknown(dict(SPEC, on_unknown_sprite='flee'), {'reason': 'test'})
check('on_unknown_sprite=flee does not pause', not c.paused)

print("\n=== shiny stops the hunt ===")
c, _ = build([BATTLE[0]])
c._handle_shiny_found({'species': 'pikachu', 'shape_score': 0.99,
                       'colour_distance': 0.8, 'crop_path': 'x.png'})
check('running cleared', c.running is False)

print("\n=== legacy Game Corner hunt is untouched ===")
c, st = build([OVER[0]])
c.image_processor.is_on_encounter_screen = lambda *a, **k: True
c.image_processor.is_shiny_found = lambda *a, **k: False
legacy = c._load_hunt_spec()
result = c._run_sequence(legacy['encounter_sequence'], legacy)
check('still returns not_shiny', result == NOT_SHINY, repr(result)[:60])

# Remove only the crops this run created. _shiny/ holds real evidence -- an
# earlier version of this cleanup deleted a genuine capture.
for d in ('_shiny', '_unknown'):
    for p in glob.glob(f'sprite_library/powerplant/{d}/*.png'):
        if p not in PRE_EXISTING_CROPS:
            os.unlink(p)

print("\n" + ("ALL PASS" if not FAILS else f"FAILURES: {FAILS}"))
sys.exit(1 if FAILS else 0)

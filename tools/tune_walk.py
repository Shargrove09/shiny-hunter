"""Tune the walk loop against the real game, without running a full hunt.

Walks until a battle is detected, reports steps and seconds per encounter, then
flees and repeats. Nothing is written to the sprite library, so this is safe to
interrupt at any point.

You are aiming for roughly 10-15 steps per encounter. Far more than that usually
means the character is turning in place rather than moving (raise
--step-duration), or is walking into a wall.

Run from the repo root, with the game in the hunting lane:

    python tools/tune_walk.py                       # 3 encounters, default timing
    python tools/tune_walk.py --step-duration 0.30 --rounds 5
    python tools/tune_walk.py --detect-only         # no movement, just poll the detector
"""
import argparse
import json
import os
import statistics
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                'src', 'shinyhunter'))

from shiny_hunter_controller import ShinyHunterController, TIMEOUT  # noqa: E402
from window_management import WindowManagerFactory  # noqa: E402

HUNT_PATH = 'hunts/powerplant.json'


def attach_window(controller, owner, allow_unfocused=False):
    """Point input at the game window, as the GUI's dropdown normally would.

    This must succeed. pynput types into whatever the OS has focused, so an
    unattached hunt sends arrow keys, x and z into the terminal it was launched
    from -- for hours. Failing loudly beats that.
    """
    manager = WindowManagerFactory.create()
    try:
        windows = manager.get_all_windows()
    except Exception as error:
        windows = []
        print(f"!! Could not enumerate windows: {error!r}")

    key = owner.lower()
    for window in windows:
        title = (window.title or '')
        if key in title.lower():
            controller.input_handler.set_target_window(window)
            if controller.input_handler.ensure_window_focused():
                print(f"input target : {title!r} (focused)")
                return True
            print(f"!! Matched {title!r} but could not focus it.")

    print(f"\n!! No focusable window matching {owner!r}.")
    if windows:
        print("   Visible windows: "
              + ', '.join(sorted({(w.title or '?') for w in windows})[:8]))
    else:
        print("   PyWinCtl returned nothing — grant Accessibility permission to your")
        print("   terminal in System Settings > Privacy & Security > Accessibility.")
    print("   Without a target window, keystrokes go to whatever is focused")
    print("   (probably this terminal). Refusing to start.")
    if allow_unfocused:
        print("   --allow-unfocused given; continuing anyway.")
        return False
    sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--hunt', default=HUNT_PATH)
    parser.add_argument('--rounds', type=int, default=3)
    parser.add_argument('--step-duration', type=float)
    parser.add_argument('--keys', help="Comma-separated, e.g. left,left,left,right,right,right")
    parser.add_argument('--poll-every', type=int)
    parser.add_argument('--max-steps', type=int, default=200)
    parser.add_argument('--no-run', action='store_true', help="Walk instead of holding B to run")
    parser.add_argument('--detect-only', action='store_true',
                        help="Send no input; just poll the battle detector for 20s")
    parser.add_argument('--countdown', type=int, default=5)
    parser.add_argument('--allow-unfocused', action='store_true',
                        help="Start even if the game window cannot be focused "
                             "(keystrokes will go to whatever is focused)")
    args = parser.parse_args()

    with open(args.hunt, encoding='utf-8') as handle:
        spec = json.load(handle)

    controller = ShinyHunterController(log_function=None)
    controller.startup_countdown = 0
    controller.running = True

    owner = controller.config.capture_window_owner or 'Playback'
    attach_window(controller, owner, args.allow_unfocused)

    step = dict(spec['encounter_sequence'][0])
    if args.step_duration:
        step['step_duration'] = args.step_duration
    if args.keys:
        step['keys'] = args.keys.split(',')
    if args.poll_every:
        step['poll_every'] = args.poll_every
    step['max_steps'] = args.max_steps
    if args.no_run:
        step['hold_keys'] = []

    template, region, threshold = controller._detector_for(step, spec)
    print(f"detector: {template}")
    print(f"          roi={region} threshold={threshold}")

    if args.detect_only:
        print("\nPolling the detector for 20s. Walk into a battle by hand and watch the score.")
        end = time.time() + 20
        while time.time() < end:
            matched, score = controller.image_processor.matches_template(
                controller.screenshot_manager.grab_native(), template,
                region=region, threshold=threshold)
            print(f"  {'BATTLE' if matched else '  ----'}  score={score:.3f}")
            time.sleep(0.4)
        return

    print(f"\nkeys={step['keys']}  step_duration={step['step_duration']}s  "
          f"hold={step.get('hold_keys')}  poll_every={step['poll_every']}")
    for remaining in range(args.countdown, 0, -1):
        print(f"  starting in {remaining}... (focus the game window)")
        time.sleep(1)

    flee = spec.get('flee_sequence', [])
    results = []
    try:
        for round_number in range(1, args.rounds + 1):
            print(f"\n--- round {round_number}/{args.rounds} ---")
            started = time.monotonic()
            outcome, taken = controller._step_walk_until_encounter(step, spec)
            elapsed = time.monotonic() - started

            if outcome is not None and outcome == TIMEOUT:
                print(f"  TIMEOUT after {taken} steps ({elapsed:.1f}s) — no battle detected.")
                print("  Character may be turning in place or walking into a wall.")
                break

            print(f"  encounter after {taken} steps, {elapsed:.1f}s "
                  f"({elapsed / max(taken, 1):.2f}s/step)")
            results.append((taken, elapsed))

            if flee and round_number < args.rounds:
                print("  fleeing...")
                result = controller._run_sequence(flee, spec)
                if result != 'complete':
                    print(f"  flee did not complete cleanly: {result!r}")
                    break
    except KeyboardInterrupt:
        print("\ninterrupted")
    finally:
        controller.running = False

    if results:
        steps = [r[0] for r in results]
        times = [r[1] for r in results]
        print(f"\n{len(results)} encounters")
        print(f"  steps  : {steps}   median {statistics.median(steps):.0f}")
        print(f"  seconds: {[round(t, 1) for t in times]}   median {statistics.median(times):.1f}")
        median = statistics.median(steps)
        if median > 25:
            print("\n  High. Likely turning in place — try a larger --step-duration,")
            print("  or longer runs in one direction (--keys left,left,left,left,right,right,right,right).")
        elif median < 5:
            print("\n  Suspiciously low. Check the detector is not firing on the overworld:")
            print("    python tools/tune_walk.py --detect-only")
        else:
            print("\n  In the expected range. Put this step_duration in hunts/powerplant.json.")


if __name__ == '__main__':
    main()

"""Run a hunt from the terminal, without the GUI.

For unattended overnight runs. Stops on a shiny, pauses on anything it cannot
identify, and prints a per-species tally as it goes.

Run from the repo root:

    python tools/run_hunt.py hunts/powerplant.json
    python tools/run_hunt.py hunts/powerplant.json --max-encounters 20
    python tools/run_hunt.py hunts/powerplant.json --dry-run    # no input sent

Ctrl+C stops cleanly.
"""
import argparse
import collections
import json
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                'src', 'shinyhunter'))

from shiny_hunter_controller import (ShinyHunterController, SHINY,  # noqa: E402
                                     NOT_SHINY, UNKNOWN_SPRITE, TIMEOUT,
                                     VERIFY_FAIL, ERROR)
from image_processor import describe_scale, resolve_region  # noqa: E402
from sprite_library import check_manifest  # noqa: E402
from window_management import WindowManagerFactory  # noqa: E402


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
    parser.add_argument('hunt', nargs='?', default='hunts/powerplant.json')
    parser.add_argument('--max-encounters', type=int, default=0, help="0 = unlimited")
    parser.add_argument('--countdown', type=int, default=5)
    parser.add_argument('--ignore-geometry', action='store_true',
                        help="Run even if capture geometry differs from the library")
    parser.add_argument('--allow-unfocused', action='store_true',
                        help="Start even if the game window cannot be focused "
                             "(keystrokes will go to whatever is focused)")
    parser.add_argument('--dry-run', action='store_true',
                        help="Detect and identify, but send no input and never flee")
    args = parser.parse_args()

    with open(args.hunt, encoding='utf-8') as handle:
        spec = json.load(handle)

    controller = ShinyHunterController()
    controller.startup_countdown = 0
    controller.config.sequence_config_path = args.hunt

    library = controller._get_library(spec)
    print(f"hunt         : {spec.get('hunt_name', args.hunt)}")
    print(f"library      : {len(library)} species — {', '.join(library.species) or '(EMPTY)'}")
    if library.background is None:
        print("!! No background plate. Run tools/build_library.py first — masks will be poor.")
    if not len(library):
        print("!! Library is empty: every encounter will pause as unknown.")

    probe = controller.screenshot_manager.grab_array()
    print(f"capture      : {probe.shape[1]}x{probe.shape[0]}")

    # Re-derive the viewport rather than trusting the stored fraction. Detection is
    # only reliable on a battle frame -- Gen 3's black map-edge fill reads as
    # letterbox -- so an unvalidated result is discarded rather than believed.
    detected, reason = controller.screenshot_manager.detect_viewport(probe)
    if detected:
        stored = resolve_region(controller.config.game_viewport, probe.shape)
        drift = max(abs(a - b) for a, b in zip(detected['pixels'], stored))
        print(f"viewport     : {detected['pixels']}  {describe_scale(detected['pixels'])}")
        if drift > 4:
            print(f"\n!! The game viewport has moved by {drift}px since setup.")
            print(f"   stored {stored}  ->  detected {detected['pixels']}")
            print("   Sprite crops will not line up with the library. Apply the")
            print("   corrected viewport with:")
            print(f"     python tools/setup_capture.py --owner "
                  f"{controller.config.capture_window_owner or 'Playback'} --write")
            if not args.ignore_geometry:
                sys.exit(1)
            print("   --ignore-geometry given; continuing anyway.")
    else:
        print(f"viewport     : not verifiable right now ({reason})")
        print("               — normal outside a battle; it is re-checked on the "
              "first encounter.")

    problems = check_manifest(library.directory, None,
                              controller.config.game_viewport,
                              controller.config.enemy_sprite_roi)
    if problems:
        print("\n!! Library does not match the current setup:")
        for problem in problems:
            print(f"   - {problem}")
        print(f"     python tools/build_library.py {spec.get('hunt_name','<hunt>')} --force")
        if not args.ignore_geometry:
            sys.exit(1)
        print("   --ignore-geometry given; continuing anyway.")

    attach_window(controller, controller.config.capture_window_owner or 'Playback',
                  args.allow_unfocused)

    if args.dry_run:
        print("\nDRY RUN — no input will be sent.")
        controller.input_handler.execute_input_step = lambda s: None
        controller.input_handler.hold_key_for = lambda k, d: None
        controller.input_handler.press_keys_down = lambda ks: None
        controller.input_handler.release_keys = lambda ks: None
        controller.input_handler.restart_sequence = lambda: None

    for remaining in range(args.countdown, 0, -1):
        print(f"  starting in {remaining}...")
        time.sleep(1)

    tally = collections.Counter()
    started = time.time()
    controller.running = True

    try:
        while controller.running:
            if args.max_encounters and controller.count >= args.max_encounters:
                print(f"\nreached --max-encounters {args.max_encounters}")
                break

            if controller.paused:
                print("\n*** HUNT PAUSED ***")
                print("  Look at the crop above. If it is a new species:")
                print(f"    python tools/add_species.py {spec.get('hunt_name','<hunt>')} <name>")
                print("  Then re-run this command to continue.")
                break

            result = controller._run_sequence(spec.get('encounter_sequence', []), spec)
            controller.increment_count()

            if result == NOT_SHINY:
                species = result.detail.get('species', '?')
                tally[species] += 1
                elapsed = time.time() - started
                print(f"[{controller.count:5d}] {species:12s} "
                      f"({elapsed / max(controller.count, 1):.1f}s/enc)  "
                      + '  '.join(f'{k}:{v}' for k, v in tally.most_common()))
                if not args.dry_run:
                    controller._handle_retry(spec)
                else:
                    print("       dry run — not fleeing; stopping here.")
                    break

            elif result == SHINY:
                controller._handle_shiny_found(result.detail)
                print("\n*** SHINY FOUND — hunt stopped ***")
                break

            elif result == UNKNOWN_SPRITE:
                controller._handle_unknown(spec, result.detail)

            elif result in (TIMEOUT, VERIFY_FAIL, ERROR):
                print(f"[{controller.count:5d}] {result!r}")
                if not args.dry_run:
                    controller._escalate(spec, result)
                else:
                    break

    except KeyboardInterrupt:
        print("\ninterrupted")
    finally:
        controller.running = False

    elapsed = time.time() - started
    print(f"\n{controller.count} encounters in {elapsed / 60:.1f} min")
    if controller.count:
        print(f"  {elapsed / controller.count:.1f}s per encounter")
    for species, count in tally.most_common():
        print(f"  {species:12s} {count:5d}  ({count / max(sum(tally.values()), 1) * 100:.0f}%)")


if __name__ == '__main__':
    main()

"""Score the sprite matcher against captured samples, before trusting it in a hunt.

You cannot wait for a real shiny to test shiny detection, so one is synthesised by
hue-rotating a known-normal sprite: same shape, different palette, which is exactly
what a shiny is.

Three things must hold, and the gaps matter more than the absolute numbers:

  same species      shape >= 0.85, with a clear gap to the runner-up species
  same palette      colour <= 0.45, with a clear gap to a different palette
  unseen species    no entry clears the shape threshold  -> 'unknown'

Run from the repo root:

    python tools/score_library.py powerplant
"""
import argparse
import glob
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                'src', 'shinyhunter'))

import cv2  # noqa: E402
import numpy as np  # noqa: E402

from config import ConfigManager  # noqa: E402
from image_processor import crop, to_native, viewport_for  # noqa: E402
from sprite_library import (SpriteLibrary, to_canonical, sprite_mask,  # noqa: E402
                            shape_signature, palette_histogram,
                            shape_score, colour_distance)



def capture_geometry():
    """Viewport and sprite ROI, via ConfigManager so defaults and the
    fraction-to-native migration both apply.

    Reading the JSON directly meant a config written before a key existed raised
    KeyError instead of falling back -- and an un-run setup would have silently
    used the whole window as the viewport, which is worse than stopping.
    """
    config = ConfigManager().get_config()
    viewport = list(config.game_viewport)
    sprite_roi = list(config.enemy_sprite_roi)

    if viewport == [0.0, 0.0, 1.0, 1.0]:
        print("No game viewport is configured — the whole window would be treated as")
        print("the game, and every crop would be wrong. Set it during a wild battle:")
        print("  python tools/setup_capture.py --owner <name> --write")
        sys.exit(1)

    return viewport, sprite_roi



def hue_rotate(bgr, degrees=90, mask=None):
    """Fake a shiny: rotate hue on sprite pixels, leaving the background alone."""
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV).astype(np.int16)
    shifted = hsv.copy()
    shifted[:, :, 0] = (shifted[:, :, 0] + degrees // 2) % 180
    shifted[:, :, 1] = np.clip(shifted[:, :, 1] * 1.3, 0, 255)
    out = cv2.cvtColor(shifted.astype(np.uint8), cv2.COLOR_HSV2BGR)
    if mask is not None:
        out = np.where(mask[:, :, None].astype(bool), out, bgr)
    return out


def load_sprites(hunt, config):
    viewport, sprite_roi = capture_geometry()
    paths = sorted(glob.glob(os.path.join('sprite_library', hunt, '_samples', '*.png')))
    out = []
    for path in paths:
        frame = cv2.imread(path)
        if frame is None:
            continue
        frame_viewport, _ = viewport_for(frame, viewport)
        out.append((os.path.basename(path), crop(to_native(frame, frame_viewport), sprite_roi)))
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('hunt')
    parser.add_argument('--labels', help="JSON mapping sample filename -> species")
    parser.add_argument('--shape-threshold', type=float, default=0.85)
    parser.add_argument('--colour-threshold', type=float, default=0.45)
    args = parser.parse_args()

    config = ConfigManager().get_config()
    samples = load_sprites(args.hunt, config)
    if not samples:
        print(f"No samples in sprite_library/{args.hunt}/_samples/")
        sys.exit(1)

    labels_path = args.labels or os.path.join('sprite_library', args.hunt, '_labels.json')
    if not os.path.exists(labels_path):
        print(f"Need labels at {labels_path}, mapping each sample to its species:")
        print(json.dumps({name: 'SPECIES' for name, _ in samples}, indent=2))
        sys.exit(1)

    with open(labels_path, encoding='utf-8') as handle:
        labels = {k: v.lower() for k, v in json.load(handle).items()}

    by_species = {}
    for name, sprite in samples:
        if name in labels:
            by_species.setdefault(labels[name], []).append((name, sprite))

    print(f"{len(samples)} samples, {len(by_species)} species: "
          f"{', '.join(f'{k}({len(v)})' for k, v in sorted(by_species.items()))}\n")

    work_dir = os.path.join('sprite_library', args.hunt, '_scoring')
    os.makedirs(work_dir, exist_ok=True)

    library = SpriteLibrary(work_dir)
    plate = library.build_background([s for _, s in samples],
                                     species=[labels.get(n) for n, _ in samples])
    print(f"background plate derived from {len(samples)} frames -> {plate}")

    # mask sanity: a sprite must actually be found, and not swallow the frame
    print("\n=== sprite masks ===")
    for name, sprite in samples:
        mask = sprite_mask(to_canonical(sprite), library.background)
        pct = mask.sum() / mask.size * 100
        flag = '' if 3 < pct < 60 else '   <- suspicious'
        print(f"  {name[:24]:26s} {labels.get(name,'?'):12s} sprite pixels {pct:5.1f}%{flag}")

    failures = []

    # ---- leave-one-out: every sample classified against a library built from the others
    print("\n=== leave-one-out identification ===")
    for species, items in sorted(by_species.items()):
        for held_name, held_sprite in items:
            for path in glob.glob(os.path.join(work_dir, '*.png')):
                if not os.path.basename(path).startswith('_'):
                    os.unlink(path)
            library.reload(force=True)

            for other_species, other_items in by_species.items():
                for name, sprite in other_items:
                    if name != held_name:
                        library.add(other_species, sprite)

            if species not in library.entries:
                print(f"  {held_name[:20]:22s} {species:12s} SKIP (only frame of this species)")
                continue

            result = library.identify(held_sprite, args.shape_threshold, args.colour_threshold)
            ok = result.verdict == 'normal' and result.species == species
            runner = f"{result.runner_up[0]} {result.runner_up[1]:.3f}" if result.runner_up else '-'
            gap = (result.shape_score - result.runner_up[1]) if result.runner_up else float('inf')
            print(f"  {'PASS' if ok else 'FAIL'}  {held_name[:20]:22s} {species:11s} "
                  f"-> {result.verdict:8s} {str(result.species):11s} "
                  f"shape={result.shape_score:.3f} (gap {gap:+.3f} over {runner})  "
                  f"colour={result.colour_distance:.3f}")
            if not ok:
                failures.append(f"leave-one-out {held_name} ({result.reason})")

    # ---- full library for the remaining checks
    for path in glob.glob(os.path.join(work_dir, '*.png')):
        if not os.path.basename(path).startswith('_'):
            os.unlink(path)
    library.reload(force=True)
    for species, items in by_species.items():
        for _, sprite in items:
            library.add(species, sprite)

    # A shiny classified 'unknown' still pauses the hunt and shows the user the
    # sprite, so it is a less precise verdict, not a lost shiny. Only 'normal' is
    # a real failure: that is the one verdict that flees and never tells anyone.
    print("\n=== synthetic shinies (hue-rotated: same shape, different palette) ===")
    precise = safe = 0
    for species, items in sorted(by_species.items()):
        name, sprite = items[0]
        canonical = to_canonical(sprite)
        mask = sprite_mask(canonical, library.background)
        for degrees in (60, 120, 180):
            fake = hue_rotate(canonical, degrees, mask)
            result = library.identify(fake, args.shape_threshold, args.colour_threshold)
            if result.verdict == 'shiny' and result.species == species:
                verdict, precise = 'PASS', precise + 1
            elif result.verdict == 'unknown':
                verdict, safe = 'SAFE', safe + 1
            else:
                verdict = 'LOST'
                failures.append(f"synthetic shiny {species} hue+{degrees} "
                                f"-> {result.verdict} ({result.reason})")
            print(f"  {verdict}  {species:11s} hue+{degrees:3d} -> "
                  f"{result.verdict:8s} {str(result.species):11s} "
                  f"shape={result.shape_score:.3f} colour={result.colour_distance:.3f}")
    print(f"  -> {precise} identified as shiny, {safe} fell to 'unknown' (still pauses "
          f"and shows you the sprite), {len(failures)} lost")

    print("\n=== unseen species must be 'unknown', never 'normal' ===")
    for held in sorted(by_species):
        for path in glob.glob(os.path.join(work_dir, '*.png')):
            if not os.path.basename(path).startswith('_'):
                os.unlink(path)
        library.reload(force=True)
        for species, items in by_species.items():
            if species == held:
                continue
            for _, sprite in items:
                library.add(species, sprite)

        name, sprite = by_species[held][0]
        result = library.identify(sprite, args.shape_threshold, args.colour_threshold)
        # 'shiny' here is a false alarm: it stops and shows the user a normal
        # sprite, costing one prompt. 'normal' is the dangerous one -- it flees
        # without telling anyone, and would do the same to a real shiny.
        if result.verdict == 'unknown':
            verdict = 'PASS'
        elif result.verdict == 'shiny':
            verdict = 'SAFE'
        else:
            verdict = 'LOST'
            failures.append(f"held-out {held} classified normal as {result.species}")
        print(f"  {verdict}  {held:11s} held out -> {result.verdict:8s} "
              f"best={str(result.species):11s} shape={result.shape_score:.3f}  ({result.reason})")

    print("\n" + "=" * 70)
    if failures:
        print(f"{len(failures)} FAILURE(S):")
        for failure in failures:
            print(f"  - {failure}")
        sys.exit(1)
    print("ALL PASS — matcher separates species by shape and palette by colour.")


if __name__ == '__main__':
    main()

"""Build a sprite library from labelled sample frames.

Reads sprite_library/<hunt>/_samples/*.png plus _labels.json, crops each frame to
the enemy sprite box, derives the background plate, and writes one entry per
species (extra frames of the same species become `<species>__altN.png`).

Run from the repo root:

    python tools/build_library.py powerplant
    python tools/build_library.py powerplant --force   # overwrite existing entries
"""
import argparse
import glob
import json
import os
import shutil
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                'src', 'shinyhunter'))

import cv2  # noqa: E402

from config import ConfigManager  # noqa: E402
from image_processor import crop, to_native, viewport_for  # noqa: E402
from sprite_library import (SpriteLibrary, to_canonical, sprite_mask,  # noqa: E402
                            write_manifest)



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



def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('hunt')
    parser.add_argument('--force', action='store_true',
                        help="Delete existing entries first")
    parser.add_argument('--one-frame-per-species', action='store_true',
                        help="Keep only the first frame of each species")
    args = parser.parse_args()

    hunt_dir = os.path.join('sprite_library', args.hunt)
    labels_path = os.path.join(hunt_dir, '_labels.json')
    if not os.path.exists(labels_path):
        print(f"No labels at {labels_path}. Label the samples first.")
        sys.exit(1)

    with open(labels_path, encoding='utf-8') as handle:
        labels = {k: v.lower() for k, v in json.load(handle).items()}

    viewport, sprite_roi = capture_geometry()

    crops, species = [], []
    for path in sorted(glob.glob(os.path.join(hunt_dir, '_samples', '*.png'))):
        name = os.path.basename(path)
        if name not in labels:
            print(f"  skipping unlabelled {name}")
            continue
        frame = cv2.imread(path)
        if frame is None:
            print(f"  could not read {name}")
            continue
        frame_viewport, source = viewport_for(frame, viewport, name)
        if source != 'detected':
            print(f"  {name}: viewport not detectable, using config")
        crops.append(crop(to_native(frame, frame_viewport), sprite_roi))
        species.append(labels[name])

    if not crops:
        print("No labelled samples found.")
        sys.exit(1)

    if args.force:
        for path in glob.glob(os.path.join(hunt_dir, '*.png')):
            os.unlink(path)

    library = SpriteLibrary(hunt_dir)

    # Balanced by species: a per-pixel median is only the background while no one
    # species covers a pixel in half the frames. Four Pikachu out of ten would
    # otherwise bake a Pikachu ghost into the plate.
    plate = library.build_background(crops, species=species)
    print(f"background plate <- {len(set(species))} species: {plate}")

    seen = set()
    for sprite, name in zip(crops, species):
        if args.one_frame_per_species and name in seen:
            continue
        seen.add(name)
        written = library.add(name, sprite)
        mask = sprite_mask(to_canonical(sprite), library.background)
        print(f"  {os.path.basename(written):24s} sprite pixels {mask.mean() * 100:5.1f}%")

    library.reload(force=True)

    sample_paths = sorted(glob.glob(os.path.join(hunt_dir, '_samples', '*.png')))
    if sample_paths:
        first = cv2.imread(sample_paths[0])
        manifest = write_manifest(hunt_dir, (first.shape[1], first.shape[0]),
                                  viewport, sprite_roi)
        print(f"manifest         -> {manifest} "
              f"(capture {first.shape[1]}x{first.shape[0]})")

    print(f"\n{len(library)} species: {', '.join(library.species)}")
    for name, frames in sorted(library.entries.items()):
        print(f"  {name:12s} {len(frames)} frame(s)")
    print(f"\nVerify with:  python tools/score_library.py {args.hunt}")


if __name__ == '__main__':
    main()

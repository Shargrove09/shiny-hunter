"""Add a species to a sprite library, so the hunt stops pausing on it.

When the hunt meets a sprite it cannot identify it pauses and saves the crop to
_unknown/. Look at it: if it is a shiny you are done, and if it is just a species
the library has not seen yet, add it here and resume.

Run from the repo root:

    python tools/add_species.py powerplant             # list pending unknowns
    python tools/add_species.py powerplant electrode   # add the oldest unknown
    python tools/add_species.py powerplant electrode --crop sprite_library/powerplant/_unknown/0003.png
"""
import argparse
import glob
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                'src', 'shinyhunter'))

import cv2  # noqa: E402

from sprite_library import SpriteLibrary, UNKNOWN_DIR  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('hunt')
    parser.add_argument('species', nargs='?', help="Name to file the sprite under")
    parser.add_argument('--crop', help="Specific crop to add (default: oldest unknown)")
    parser.add_argument('--keep', action='store_true',
                        help="Leave the crop in _unknown/ instead of consuming it")
    args = parser.parse_args()

    hunt_dir = os.path.join('sprite_library', args.hunt)
    if not os.path.isdir(hunt_dir):
        print(f"No library at {hunt_dir}")
        sys.exit(1)

    library = SpriteLibrary(hunt_dir)
    pending = sorted(glob.glob(os.path.join(hunt_dir, UNKNOWN_DIR, '*.png')))

    if not args.species:
        print(f"library: {len(library)} species — {', '.join(library.species) or '(empty)'}")
        if pending:
            print(f"\n{len(pending)} unidentified crop(s) waiting:")
            for path in pending:
                print(f"  {path}")
            print("\nLook at one, then:  python tools/add_species.py "
                  f"{args.hunt} <species> --crop <path>")
        else:
            print("\nNo unidentified crops pending.")
        return

    source = args.crop or (pending[0] if pending else None)
    if not source:
        print("No crop given and nothing waiting in _unknown/.")
        sys.exit(1)
    if not os.path.exists(source):
        print(f"No such crop: {source}")
        sys.exit(1)

    sprite = cv2.imread(source)
    if sprite is None:
        print(f"Could not read {source}")
        sys.exit(1)

    if library.background is None:
        print("Warning: this library has no _background.png, so sprite masks will be")
        print("         guessed from the crop border and matching will be less reliable.")
        print("         Build one with: python tools/build_library.py " + args.hunt)

    written = library.add(args.species, sprite)
    print(f"added {args.species!r} -> {written}")

    if not args.keep and not args.crop:
        os.unlink(source)
        print(f"consumed {source}")

    library.reload(force=True)
    print(f"library now holds {len(library)} species: {', '.join(library.species)}")
    print("\nResume the hunt — the library is re-read automatically, no restart needed.")


if __name__ == '__main__':
    main()

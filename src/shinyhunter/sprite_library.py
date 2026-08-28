"""Identify the wild Pokemon in a battle, and decide whether it is shiny.

Random encounters produce an unknown species every time, so the static-hunt trick
of correlating against one reference image cannot work. Instead the library holds
one crop per known-normal species and matching runs in two independent stages:

    shape  -> which species is this?   (identical for shiny and normal)
    colour -> is its palette the normal one?

Two stages rather than one because a single colour metric can only answer "is this
in the library", and a shiny is *by definition* not in the library — the same
bucket as a species never seen before. Splitting them makes a shiny of a known
species a positive identification instead of an absence.

Both stages ignore background pixels. The battle background is constant, so it is
captured once as a plate and subtracted; colour-keying would eat a grey Magnemite
against grey background stripes.
"""
import glob
import json
import logging
import os
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

import cv2
import numpy as np

logger = logging.getLogger(__name__)

# Sprites are matched at native GBA resolution. Captures are an integer multiple
# of this, so downscaling averages away resampling noise and makes every
# comparison cheap and resolution-independent.
SPRITE_SIZE = 64

# Capture alignment can drift by a pixel or two between sessions; every
# comparison searches this far for the best fit.
SEARCH_PAD = 4

BACKGROUND_PLATE = '_background.png'
MANIFEST = '_manifest.json'
UNKNOWN_DIR = '_unknown'
SHINY_DIR = '_shiny'


def write_manifest(directory: str, capture_size, viewport, sprite_roi) -> str:
    """Record the capture geometry a library was built under.

    Entries are only comparable to live crops taken through the same geometry.
    The viewport and ROI are stored as fractions, so resizing the game window
    silently re-maps them onto a different slice of the game: the sprite lands at
    a slightly different scale and offset, its shape score against its own
    species collapses, and every encounter reads as unknown or shiny.
    """
    payload = {
        'native_width': 240,
        'native_height': 160,
        'enemy_sprite_roi': [int(v) for v in sprite_roi],
        # Informational only: crops are normalised to native before matching, so
        # the capture size no longer affects correctness.
        'built_at_capture': [int(capture_size[0]), int(capture_size[1])] if capture_size else None,
    }
    path = os.path.join(directory, MANIFEST)
    with open(path, 'w', encoding='utf-8') as handle:
        json.dump(payload, handle, indent=2)
    return path


def check_manifest(directory: str, capture_size, viewport, sprite_roi):
    """Compare live geometry with the library's. Returns a list of complaints."""
    path = os.path.join(directory, MANIFEST)
    if not os.path.exists(path):
        return ["library has no _manifest.json — cannot verify capture geometry "
                "(rebuild with tools/build_library.py to add one)"]

    try:
        with open(path, encoding='utf-8') as handle:
            saved = json.load(handle)
    except (OSError, ValueError) as error:
        return [f"could not read _manifest.json: {error}"]

    problems = []
    # Only the sprite ROI matters now: every crop is normalised to native 240x160
    # first, so window size and viewport drift no longer change what a crop
    # contains. A changed ROI does.
    stored = saved.get('enemy_sprite_roi')
    if stored and sprite_roi and [int(v) for v in stored] != [int(v) for v in sprite_roi]:
        problems.append(f"enemy_sprite_roi changed: library {stored} vs current "
                        f"{[int(v) for v in sprite_roi]}")
    return problems


@dataclass
class Entry:
    """One library sprite, with everything precomputed for matching."""
    canonical: object
    mask: object
    shape: object
    silhouette: object
    palette: object


@dataclass
class MatchResult:
    verdict: str                                    # 'normal' | 'shiny' | 'unknown'
    species: Optional[str] = None
    shape_score: float = 0.0
    colour_distance: float = 1.0
    runner_up: Optional[Tuple[str, float]] = None
    reason: str = ''
    scores: List[tuple] = field(default_factory=list)

    def __str__(self):
        return (f"{self.verdict} species={self.species} shape={self.shape_score:.3f} "
                f"colour={self.colour_distance:.3f}")


def to_canonical(bgr):
    """Downscale a sprite crop to native GBA size."""
    if bgr.shape[0] == SPRITE_SIZE and bgr.shape[1] == SPRITE_SIZE:
        return bgr
    return cv2.resize(bgr, (SPRITE_SIZE, SPRITE_SIZE), interpolation=cv2.INTER_AREA)


def sprite_mask(canonical, background=None, threshold: int = 26):
    """Boolean mask of sprite (non-background) pixels.

    With a background plate this is a plain difference, which separates a sprite
    from a same-coloured background. Without one it falls back to keying out the
    colours found around the crop's border.
    """
    if background is not None:
        diff = np.abs(canonical.astype(np.int16) - background.astype(np.int16)).max(axis=2)
        mask = (diff > threshold).astype(np.uint8)
    else:
        border = np.concatenate([
            canonical[:3].reshape(-1, 3), canonical[-3:].reshape(-1, 3),
            canonical[:, :3].reshape(-1, 3), canonical[:, -3:].reshape(-1, 3),
        ])
        median = np.median(border, axis=0)
        distance = np.abs(canonical.astype(np.int16) - median).max(axis=2)
        mask = (distance > threshold).astype(np.uint8)

    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((2, 2), np.uint8))
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8))
    return mask


def shape_signature(canonical, mask, background=None):
    """Structural signature of the sprite: how far each pixel is from background.

    Continuous, with no threshold anywhere. `gray * binary_mask` was brittle for
    exactly that reason -- a capture differing by a mean of 3/255 flipped enough
    mask pixels to drop a same-species score from 1.000 to 0.852, below the
    identification threshold. A difference image degrades smoothly instead.

    Measured over the real captures (same species across frames / different
    species / a hue-rotated sprite against its own normal):

        gray x mask       same 0.852, cross 0.619, recoloured 0.800
        |crop - plate|    same 0.912, cross 0.725, recoloured 0.991   <- chosen

    The recoloured figure is what matters most: at 0.991 a shiny is still
    identified as its own species, so the colour stage gets to return a confident
    "shiny" instead of the sprite falling to "unknown".

    Falls back to the masked grayscale when no background plate exists.

    Canny edges were tested and rejected: they invert under sprite dithering
    noise, scoring shiny-vs-normal higher than same-sprite-different-frame.
    """
    if background is None:
        gray = cv2.cvtColor(canonical, cv2.COLOR_BGR2GRAY)
        return (gray * mask).astype(np.uint8)

    difference = np.abs(canonical.astype(np.int16) - background.astype(np.int16)).max(axis=2)
    return np.clip(difference, 0, 255).astype(np.uint8)


def silhouette_signature(canonical, mask):
    """Blurred sprite outline — identical for a shiny and its normal.

    Used only as a fallback when grayscale fails, because on its own it cannot
    separate similarly-shaped species (Magnemite vs Voltorb score 0.989). It
    recovers the case grayscale is worst at: a sprite whose palette shifted so far
    that its luminance no longer resembles the library entry.
    """
    return cv2.GaussianBlur((mask * 255).astype(np.uint8), (3, 3), 0)


def palette_histogram(canonical, mask):
    """Hue/saturation histogram over sprite pixels only, smoothed.

    A 64x64 sprite contributes only ~500 masked pixels. Spread over a fine
    histogram those land in mostly-empty bins, and Bhattacharyya then reacts to
    bin quantisation rather than to colour: resampling a capture by a few percent
    moved the distance from 0.000 to 0.50 and flipped a normal Magnemite to
    "shiny". Blurring the histogram spreads each pixel across neighbouring bins,
    so a one-bin shift barely registers.

    Measured over resamples of the real captures, same palette vs hue-rotated:

        30x32 raw     same <= 0.523, shiny >= 0.882   (same overshoots 0.45)
        16x16 raw     same <= 0.419, shiny >= 0.818
        16x16 blurred same <= 0.224, shiny >= 0.685   <- threshold 0.45 centred
    """
    hsv = cv2.cvtColor(canonical, cv2.COLOR_BGR2HSV)
    hist = cv2.calcHist([hsv], [0, 1], mask, [16, 16], [0, 180, 0, 256])
    hist = cv2.GaussianBlur(hist, (3, 3), 0)
    # Explicit division, not cv2.normalize(..., 0, 1, NORM_L1): for the L1/L2/INF
    # norm types OpenCV treats alpha as the target norm and ignores beta, so that
    # call normalises every histogram to sum to *zero* and every comparison
    # returns maximum distance.
    total = float(hist.sum())
    if total > 0:
        hist /= total
    return hist


def shape_score(probe_signature, entry_signature, search_pad: int = SEARCH_PAD) -> float:
    """Best normalised correlation over a small range of alignments, in [-1, 1].

    The probe is padded so matchTemplate can slide the entry across it. Without
    this both images are the same size, the result is a single value, and a
    one-pixel capture offset is enough to drop a same-species score from 1.000 to
    0.66 — which then reads as "different species" or, worse, as a shiny.
    """
    if search_pad:
        probe_signature = cv2.copyMakeBorder(probe_signature, search_pad, search_pad,
                                             search_pad, search_pad, cv2.BORDER_REPLICATE)
    return float(cv2.matchTemplate(probe_signature, entry_signature,
                                   cv2.TM_CCOEFF_NORMED).max())


def align_to_background(canonical, background, search_pad: int = SEARCH_PAD):
    """Shift a crop so its background lines up with the plate.

    The battle background is horizontal banding, so a one-pixel vertical offset
    misaligns every stripe edge and litters the mask with background pixels that
    are not sprite. Alignment is measured only on the left and right margins,
    which no sprite reaches.
    """
    if background is None or not search_pad:
        return canonical, (0, 0)

    width = canonical.shape[1]
    margin = max(4, width // 10)
    columns = list(range(margin)) + list(range(width - margin, width))

    reference = background[:, columns].astype(np.int16)
    best, offset = None, (0, 0)
    for dy in range(-search_pad, search_pad + 1):
        for dx in range(-search_pad, search_pad + 1):
            shifted = np.roll(np.roll(canonical, dy, axis=0), dx, axis=1)
            score = np.abs(shifted[:, columns].astype(np.int16) - reference).mean()
            if best is None or score < best:
                best, offset = score, (dx, dy)

    if offset == (0, 0):
        return canonical, offset
    return np.roll(np.roll(canonical, offset[1], axis=0), offset[0], axis=1), offset


def colour_distance(a_hist, b_hist) -> float:
    """Bhattacharyya distance, 0 = identical palette, 1 = disjoint.

    Not HISTCMP_CORREL: over sparse masked histograms it collapses toward zero
    for every dissimilar pair, giving no usable ranking.
    """
    return float(cv2.compareHist(a_hist, b_hist, cv2.HISTCMP_BHATTACHARYYA))


class SpriteLibrary:
    """Known-normal sprites for one hunt, keyed by species."""

    def __init__(self, directory: str, background=None):
        self.directory = directory
        self.background = background
        self.entries = {}       # species -> list of (canonical, mask, signature, hist)
        self._mtime = None
        self.reload()

    # ---------------------------------------------------------------- loading

    def _load_background(self):
        path = os.path.join(self.directory, BACKGROUND_PLATE)
        if os.path.exists(path):
            plate = cv2.imread(path)
            if plate is not None:
                self.background = to_canonical(plate)

    def _prepare(self, bgr):
        canonical, _ = align_to_background(to_canonical(bgr), self.background)
        mask = sprite_mask(canonical, self.background)
        return Entry(canonical=canonical, mask=mask,
                     shape=shape_signature(canonical, mask, self.background),
                     silhouette=silhouette_signature(canonical, mask),
                     palette=palette_histogram(canonical, mask))

    def reload(self, force: bool = False):
        """Re-read the library if it changed on disk."""
        if not os.path.isdir(self.directory):
            self.entries = {}
            return

        stamp = os.path.getmtime(self.directory)
        if not force and stamp == self._mtime and self.entries:
            return
        self._mtime = stamp

        if self.background is None:
            self._load_background()

        entries = {}
        for path in sorted(glob.glob(os.path.join(self.directory, '*.png'))):
            name = os.path.splitext(os.path.basename(path))[0]
            if name.startswith('_'):        # _background, and the _unknown/_shiny dirs
                continue
            species = name.split('__')[0]   # zubat__alt1.png groups under 'zubat'
            image = cv2.imread(path)
            if image is None:
                logger.warning("Could not read library entry %s", path)
                continue
            entries.setdefault(species, []).append(self._prepare(image))

        self.entries = entries

    @property
    def species(self) -> List[str]:
        return sorted(self.entries)

    def __len__(self):
        return len(self.entries)

    # --------------------------------------------------------------- matching

    def _rank(self, probe_signature, attribute: str):
        """Rank every species by its best-matching frame on one signature."""
        return sorted(
            ((species, max(shape_score(probe_signature, getattr(entry, attribute))
                           for entry in frames))
             for species, frames in self.entries.items()),
            key=lambda item: -item[1],
        )

    def identify(self, sprite_bgr, shape_threshold: float = 0.85,
                 colour_threshold: float = 0.45,
                 ambiguity_margin: float = 0.05,
                 silhouette_threshold: float = 0.92,
                 silhouette_margin: float = 0.05) -> MatchResult:
        """Classify a sprite crop as a known normal, a shiny, or an unknown species.

        Species is identified by masked grayscale first, which separates
        similarly-shaped species. If that is inconclusive the outline is tried,
        which is palette-independent and so recovers a sprite recoloured far
        enough that its luminance no longer matches — i.e. exactly a shiny. The
        outline pass keeps the same ambiguity guard, so lookalike species still
        fall through to 'unknown' rather than being guessed at.

        Thresholds are deliberately asymmetric. A borderline case must land in
        'unknown', which costs one prompt, never in 'normal', which costs a shiny
        you will never see again.
        """
        if not self.entries:
            return MatchResult('unknown', reason='library is empty')

        probe = self._prepare(sprite_bgr)

        if probe.mask.sum() < 20:
            return MatchResult('unknown', reason='no sprite found in crop')

        scores = self._rank(probe.shape, 'shape')
        best_species, best_shape = scores[0]
        runner_up = scores[1] if len(scores) > 1 else None
        matched_by = 'grayscale'

        confident = (best_shape >= shape_threshold
                     and (runner_up is None or best_shape - runner_up[1] >= ambiguity_margin))

        if not confident:
            outline = self._rank(probe.silhouette, 'silhouette')
            outline_best, outline_score = outline[0]
            outline_runner = outline[1] if len(outline) > 1 else None

            if (outline_score >= silhouette_threshold
                    and (outline_runner is None
                         or outline_score - outline_runner[1] >= silhouette_margin)):
                best_species, best_shape = outline_best, outline_score
                runner_up, scores, matched_by = outline_runner, outline, 'silhouette'
                confident = True

        if not confident:
            if best_shape < shape_threshold:
                reason = f'best shape {best_shape:.3f} < {shape_threshold}, outline inconclusive'
            else:
                reason = (f'ambiguous: {best_species} {best_shape:.3f} vs '
                          f'{runner_up[0]} {runner_up[1]:.3f}')
            return MatchResult('unknown', species=None, shape_score=best_shape,
                               runner_up=runner_up, scores=scores, reason=reason)

        distance = min(colour_distance(probe.palette, entry.palette)
                       for entry in self.entries[best_species])

        verdict = 'normal' if distance <= colour_threshold else 'shiny'
        return MatchResult(verdict, species=best_species, shape_score=best_shape,
                           colour_distance=distance, runner_up=runner_up, scores=scores,
                           reason=f'matched by {matched_by}; colour {distance:.3f} '
                                  f'vs threshold {colour_threshold}')

    # ---------------------------------------------------------------- writing

    def add(self, species: str, sprite_bgr) -> str:
        """Save a crop as a known-normal entry, adding a frame if the species exists."""
        os.makedirs(self.directory, exist_ok=True)
        species = ''.join(c for c in species.lower().strip() if c.isalnum() or c in '-_')
        if not species:
            raise ValueError("Species name must contain at least one alphanumeric character")

        path = os.path.join(self.directory, f'{species}.png')
        suffix = 1
        while os.path.exists(path):
            path = os.path.join(self.directory, f'{species}__alt{suffix}.png')
            suffix += 1

        cv2.imwrite(path, to_canonical(sprite_bgr))
        self.reload(force=True)
        return path

    def save_aside(self, sprite_bgr, subdir: str, label: str = '') -> str:
        """Save a crop into _unknown/ or _shiny/ for later review."""
        target = os.path.join(self.directory, subdir)
        os.makedirs(target, exist_ok=True)
        index = len(glob.glob(os.path.join(target, '*.png'))) + 1
        name = f'{index:04d}{"_" + label if label else ""}.png'
        path = os.path.join(target, name)
        cv2.imwrite(path, to_canonical(sprite_bgr))
        return path

    def build_background(self, sprite_crops, species=None) -> str:
        """Derive the constant battle background from several sprite crops.

        The per-pixel median keeps whatever does not move — the background — and
        discards the sprites, but only while no single species occupies a pixel in
        half the frames or more. Pass `species` to balance the input to one frame
        per species: otherwise a route where one Pokemon is four times commoner
        than the rest bakes a ghost of it into the plate, which then cancels
        itself out of its own mask and wrecks that species' shape score.
        """
        crops = list(sprite_crops)
        if species is not None:
            if len(species) != len(crops):
                raise ValueError("species must align with sprite_crops")
            unique = {}
            for name, crop_image in zip(species, crops):
                unique.setdefault(name, crop_image)
            crops = list(unique.values())

        if len(crops) < 3:
            raise ValueError(
                f"Need at least 3 distinct sprites to derive a background plate, got {len(crops)}")

        stack = np.stack([to_canonical(c).astype(np.float32) for c in crops])

        # A plain per-pixel median is only the background where most frames show
        # background, and every species sits in the middle of the box, so the
        # centre never qualifies. Battle backgrounds are horizontal bands, so
        # take each row's colour from the left and right margins -- which no
        # sprite reaches -- and extend it across the row.
        height, width = stack.shape[1], stack.shape[2]
        margin = max(4, width // 10)
        columns = list(range(margin)) + list(range(width - margin, width))
        plate = np.zeros((height, width, 3), np.uint8)
        for row in range(height):
            samples = stack[:, row, columns, :].reshape(-1, 3)
            plate[row, :, :] = np.median(samples, axis=0)

        os.makedirs(self.directory, exist_ok=True)
        path = os.path.join(self.directory, BACKGROUND_PLATE)
        cv2.imwrite(path, plate)
        self.background = plate
        self.reload(force=True)
        return path

import cv2
import logging
import os
from typing import List, Optional, Sequence, Tuple
import numpy as np
import statistics
from config import ConfigManager

logger = logging.getLogger(__name__)

GBA_RATIO = 240 / 160  # 1.5

# The GBA always renders 240x160. Normalising every frame to that makes window
# size, Retina scaling and letterbox into sampling details rather than
# correctness inputs, and lets regions be plain native pixel coordinates.
NATIVE_WIDTH = 240
NATIVE_HEIGHT = 160


def to_native(bgr, viewport=None):
    """Crop to the game viewport and resample to exactly 240x160.

    Area-averaged: captures are an integer multiple of native (6x here), so this
    is a clean box filter rather than a resampling that invents detail.
    """
    view = crop(bgr, viewport) if viewport is not None else bgr
    if view.shape[0] == NATIVE_HEIGHT and view.shape[1] == NATIVE_WIDTH:
        return view
    return cv2.resize(view, (NATIVE_WIDTH, NATIVE_HEIGHT), interpolation=cv2.INTER_AREA)


def validate_viewport(rect, ratio_tolerance: float = 0.01, scale_tolerance: float = 0.02):
    """Is this rectangle plausibly the game viewport? Returns (ok, reason).

    Detection must be validated rather than trusted. Gen 3 fills beyond the map
    boundary with black, which reads as letterbox, so an overworld frame yields a
    viewport truncated to the non-black part. Measured on real frames: battle
    frames give ratio 1.500 at exactly 6.00x native; overworld frames give
    0.85-1.45 at 3.4-5.8x.

    The integer-scale check is the load-bearing one — one overworld frame came in
    at 3.3% ratio error, which a loose aspect gate alone would have accepted while
    being 48 pixels too narrow.
    """
    if not rect:
        return False, "no viewport"

    _, _, width, height = rect
    if width <= 0 or height <= 0:
        return False, f"degenerate size {width}x{height}"

    ratio = width / height
    if abs(ratio - GBA_RATIO) / GBA_RATIO > ratio_tolerance:
        return False, (f"aspect {ratio:.3f} is not 3:2 "
                       f"({abs(ratio - GBA_RATIO) / GBA_RATIO * 100:.1f}% off)")

    scale = width / NATIVE_WIDTH
    nearest = round(scale)
    if nearest < 1 or abs(scale - nearest) > scale_tolerance * max(nearest, 1):
        return False, f"scale {scale:.2f}x native is not an integer multiple"

    return True, f"{scale:.2f}x native"


def describe_scale(rect):
    """Human-readable note about how cleanly a viewport maps to native."""
    if not rect:
        return "unknown"
    scale = rect[2] / NATIVE_WIDTH
    nearest = round(scale)
    if nearest >= 1 and abs(scale - nearest) <= 0.02 * nearest:
        return f"{scale:.2f}x native — exact"
    return (f"{scale:.2f}x native — not an integer multiple, so sprites are resampled "
            f"and match scores will be softer (nearest clean size: "
            f"{nearest * NATIVE_WIDTH}x{nearest * NATIVE_HEIGHT})")


def resolve_region(rect: Optional[Sequence[float]], shape) -> Optional[Tuple[int, int, int, int]]:
    """Turn a region into clamped pixel coords for an image of the given shape.

    A rect whose values are all <= 1.0 is read as fractions of the image, which
    is the safer default: fractions survive a change in capture resolution,
    pixels silently point somewhere else.
    """
    if rect is None:
        return None

    x, y, w, h = (float(v) for v in rect)
    height, width = shape[0], shape[1]

    if max(x, y, w, h) <= 1.0:
        x, y, w, h = x * width, y * height, w * width, h * height

    x, y = int(round(x)), int(round(y))
    w, h = int(round(w)), int(round(h))

    x, y = max(0, x), max(0, y)
    w, h = min(w, width - x), min(h, height - y)

    if w <= 0 or h <= 0:
        raise ValueError(f"Region {tuple(rect)} lies outside a {width}x{height} image")

    return x, y, w, h


def crop(image, rect: Optional[Sequence[float]] = None):
    """Crop an image to a fractional or pixel region. None returns it unchanged."""
    if rect is None:
        return image
    x, y, w, h = resolve_region(rect, image.shape)
    return image[y:y + h, x:x + w]


def _describe(x, y, w, h, width, height, source):
    ratio = w / h if h else 0.0
    return {
        'pixels': (int(x), int(y), int(w), int(h)),
        'fraction': [round(x / width, 5), round(y / height, 5),
                     round(w / width, 5), round(h / height, 5)],
        'ratio': ratio,
        'error': abs(ratio - GBA_RATIO) / GBA_RATIO,
        'source': source,
    }


def detect_game_viewport(bgr, ratio_tolerance: float = 0.25, black_level: int = 24):
    """Locate the game inside a captured window, as fractions of that image.

    Primary method is structural, not ratio-based: players letterbox the game
    with black bars, so the game is the bright island inside the largest dark
    region. Ratio matching is only a fallback, because a player that stretches
    the image to fill its window produces a viewport that is not 3:2 at all —
    and in that case the letterbox boundary scores *better* on ratio than the
    real game does.

    Returns a list of dicts with 'fraction', 'pixels', 'ratio', 'error' and
    'source', best first.
    """
    height, width = bgr.shape[0], bgr.shape[1]
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)

    out = []

    # --- structural: bright island inside the biggest dark region ---
    dark = (gray < black_level).astype(np.uint8)
    count, _, stats, _ = cv2.connectedComponentsWithStats(dark, 8)
    if count > 1:
        biggest = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
        lx, ly, lw, lh = (int(stats[biggest, i]) for i in range(4))

        if lw > width * 0.25 and lh > height * 0.25:
            inner = gray[ly:ly + lh, lx:lx + lw] >= black_level
            ys, xs = np.nonzero(inner)
            if len(xs) and len(ys):
                gx, gy = lx + int(xs.min()), ly + int(ys.min())
                gw = int(xs.max() - xs.min() + 1)
                gh = int(ys.max() - ys.min() + 1)
                if gw > width * 0.2 and gh > height * 0.2:
                    out.append(_describe(gx, gy, gw, gh, width, height, 'letterbox'))

    # --- fallback: contours whose aspect is close to the GBA's 3:2 ---
    _, lit = cv2.threshold(gray, black_level, 255, cv2.THRESH_BINARY)
    lit = cv2.morphologyEx(lit, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
    contours, _ = cv2.findContours(lit, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    ratio_hits = []
    for contour in contours:
        x, y, w, h = cv2.boundingRect(contour)
        if w < width * 0.2 or h < height * 0.2:
            continue
        candidate = _describe(x, y, w, h, width, height, 'ratio')
        if candidate['error'] <= ratio_tolerance:
            ratio_hits.append(candidate)

    ratio_hits.sort(key=lambda c: (round(c['error'] / 0.015), -(c['pixels'][2] * c['pixels'][3])))

    seen = {c['pixels'] for c in out}
    out.extend(c for c in ratio_hits if c['pixels'] not in seen)

    # Rank validity first. The structural candidate is usually right and is listed
    # first, but on an overworld frame the black map-edge fill truncates it, and a
    # 43%-off structural result must not outrank a clean 3:2 contour.
    for candidate in out:
        candidate['valid'], candidate['scale_note'] = validate_viewport(candidate['pixels'])

    out.sort(key=lambda c: (not c['valid'], c['source'] != 'letterbox', c['error']))
    return out

class ImageProcessor:
    def __init__(self):
        self.config = ConfigManager().get_config()

    @staticmethod
    def _as_bgr(source):
        """Accept a path or an already-loaded array."""
        if source is None:
            return None
        if isinstance(source, str):
            return cv2.imread(source)
        return source

    def matches_template(self, source, template_path: str, region=None,
                         threshold: float = None, search_pad: int = 3):
        """Strict template match: does `region` of `source` look like the template?

        Returns (matched, score). Unlike is_on_encounter_screen this returns
        (False, 0.0) when the template is missing rather than silently passing —
        a detector that answers "yes" when misconfigured would make a walk loop
        exit instantly, forever.

        A small search pad absorbs sub-pixel capture jitter without allowing the
        template to match somewhere entirely different.
        """
        threshold = self.config.screen_verification_threshold if threshold is None else threshold

        image = self._as_bgr(source)
        if image is None:
            logger.warning("matches_template: could not read source")
            return False, 0.0

        if not template_path or not os.path.exists(template_path):
            logger.warning("matches_template: template missing at %r", template_path)
            return False, 0.0

        template = cv2.imread(template_path)
        if template is None:
            logger.warning("matches_template: could not read template %r", template_path)
            return False, 0.0

        if region is not None:
            x, y, w, h = resolve_region(region, image.shape)
            pad = max(0, int(search_pad))
            y0, y1 = max(0, y - pad), min(image.shape[0], y + h + pad)
            x0, x1 = max(0, x - pad), min(image.shape[1], x + w + pad)
            image = image[y0:y1, x0:x1]

        # cv2.matchTemplate raises when the template is larger than the image,
        # which happens whenever the capture region shrinks.
        if template.shape[0] > image.shape[0] or template.shape[1] > image.shape[1]:
            logger.warning("matches_template: template %sx%s larger than search area %sx%s",
                           template.shape[1], template.shape[0], image.shape[1], image.shape[0])
            return False, 0.0

        score = float(cv2.matchTemplate(image, template, cv2.TM_CCOEFF_NORMED).max())
        return score >= threshold, score

    def is_on_encounter_screen(self, screenshot_path: str, template_path: str = None) -> bool:
        """Verify the current screen matches a template via template matching.

        Defaults to pre_encounter_template_path (overworld) when no template_path given.
        Returns True (skip validation) if the template file doesn't exist yet.
        """
        if not os.path.exists(screenshot_path):
            return False

        # Define template image that should appear on encounter screen
        encounter_template_path = template_path or self.config.pre_encounter_template_path
        if not os.path.exists(encounter_template_path):
            #TODO: Log warning about missing template 
            return True  # Skip validation if template doesn't exist
            
        screenshot = cv2.imread(screenshot_path)
        template = cv2.imread(encounter_template_path)
        
        if screenshot is None or template is None:
            return False
            
        # Template matching to find UI elements specific to encounter screen
        result = cv2.matchTemplate(screenshot, template, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, _ = cv2.minMaxLoc(result)
        
        return max_val > self.config.screen_verification_threshold
    
    def is_shiny_found(self, ref_img_path: str, screenshot_path: str) -> bool:
        """Check if a shiny Pokemon is found by comparing reference image to screenshot of current encounter."""
        if not os.path.exists(ref_img_path) or not os.path.exists(screenshot_path):
            return False

        correlation = self.get_correlation(ref_img_path, screenshot_path)
        effective_threshold = self.config.correlation_threshold - self.config.correlation_tolerance
        is_shiny = correlation < effective_threshold
        logger.debug(
            "Shiny check: correlation=%.6f, threshold=%.6f, tolerance=%.6f, effective_threshold=%.6f, shiny=%s",
            correlation, self.config.correlation_threshold, self.config.correlation_tolerance,
            effective_threshold, is_shiny,
        )
        return is_shiny
    
    def get_correlation(self, ref_img_path: str, screenshot_path: str) -> float:
        """Calculate correlation between reference and screenshot images."""
        ref_image = cv2.imread(ref_img_path)
        screenshot = cv2.imread(screenshot_path)
        
        if ref_image is None or screenshot is None:
            return 0.0
        
        # Convert to HSV color space
        reference_hsv = cv2.cvtColor(ref_image, cv2.COLOR_BGR2HSV)
        screenshot_hsv = cv2.cvtColor(screenshot, cv2.COLOR_BGR2HSV)
        
        # Calculate histograms
        reference_hist = cv2.calcHist([reference_hsv], [0, 1], None, [180, 256], [0, 180, 0, 256])
        screenshot_hist = cv2.calcHist([screenshot_hsv], [0, 1], None, [180, 256], [0, 180, 0, 256])
        
        # Normalize histograms
        cv2.normalize(reference_hist, reference_hist, 0, 1, cv2.NORM_MINMAX)
        cv2.normalize(screenshot_hist, screenshot_hist, 0, 1, cv2.NORM_MINMAX)
        
        # Compare histograms
        return cv2.compareHist(reference_hist, screenshot_hist, cv2.HISTCMP_CORREL)

    def suggest_threshold_from_normals(self, normal_correlations: List[float], tolerance: float) -> float:
        """Suggest a threshold from normal encounter correlations.

        Lower correlation means shiny, so threshold should be below normal values.
        """
        if not normal_correlations:
            raise ValueError("At least one normal correlation sample is required")

        clamped = [max(0.0, min(1.0, sample)) for sample in normal_correlations]

        if len(clamped) == 1:
            return max(0.0, clamped[0] - max(0.03, tolerance * 5))

        mean_value = statistics.mean(clamped)
        std_dev = statistics.pstdev(clamped)

        # Keep threshold below normal distribution with a guard band.
        guard_band = max(std_dev * 2.0, tolerance * 5)
        suggested = mean_value - guard_band
        return max(0.0, min(1.0, suggested))
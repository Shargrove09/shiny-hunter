"""Capture a specific window by id instead of a screen rectangle (macOS).

Grabbing a screen rectangle couples every capture to the window's position, the
display's Retina scale factor, and whatever happens to be on top. Capturing the
window itself removes all three: the image is the window's own content, at a
stable size, wherever it sits on screen.

Window ids are not stable across app restarts, so the window is resolved by
owner name each session and the id is re-resolved automatically if a capture
fails.

macOS only. Callers should fall back to region capture elsewhere.
"""
import logging
import os
import platform
import subprocess
import tempfile

logger = logging.getLogger(__name__)

IS_MACOS = platform.system() == 'Darwin'

try:
    import Quartz
    QUARTZ_AVAILABLE = True
except ImportError:
    QUARTZ_AVAILABLE = False
    Quartz = None


class WindowCaptureError(RuntimeError):
    """Raised when a window cannot be found or captured."""


def available() -> bool:
    return IS_MACOS and QUARTZ_AVAILABLE


def list_windows(min_width: int = 200, min_height: int = 150) -> list:
    """On-screen windows large enough to be a game window, biggest first.

    Menu-bar extras and helper windows are filtered out by layer and size.
    """
    if not available():
        raise WindowCaptureError("Window capture requires macOS with Quartz (pyobjc).")

    raw = Quartz.CGWindowListCopyWindowInfo(
        Quartz.kCGWindowListOptionOnScreenOnly | Quartz.kCGWindowListExcludeDesktopElements,
        Quartz.kCGNullWindowID,
    )

    out = []
    for entry in raw or []:
        if entry.get('kCGWindowLayer', 0) != 0:      # 0 == normal application window
            continue
        bounds = entry.get('kCGWindowBounds') or {}
        width, height = int(bounds.get('Width', 0)), int(bounds.get('Height', 0))
        if width < min_width or height < min_height:
            continue
        out.append({
            'id': int(entry.get('kCGWindowNumber', 0)),
            'owner': str(entry.get('kCGWindowOwnerName', '') or ''),
            'title': str(entry.get('kCGWindowName', '') or ''),
            'x': int(bounds.get('X', 0)),
            'y': int(bounds.get('Y', 0)),
            'width': width,
            'height': height,
        })

    out.sort(key=lambda w: -(w['width'] * w['height']))
    return out


def resolve_window(owner: str = '', title: str = '') -> dict:
    """Find a window by case-insensitive substring of its owner and/or title.

    Matching on owner rather than a stored id is deliberate: ids change every
    time the app restarts, and kCGWindowName is frequently empty on macOS.
    """
    windows = list_windows()
    if not windows:
        raise WindowCaptureError("No capturable windows found.")

    owner_key, title_key = owner.lower().strip(), title.lower().strip()

    matches = [
        w for w in windows
        if (not owner_key or owner_key in w['owner'].lower())
        and (not title_key or title_key in w['title'].lower())
    ]

    if not matches:
        names = ', '.join(sorted({w['owner'] for w in windows})) or 'none'
        raise WindowCaptureError(
            f"No window matching owner={owner!r} title={title!r}. Visible apps: {names}"
        )

    return matches[0]


def capture(window_id: int, include_shadow: bool = False):
    """Capture one window to a PIL Image.

    The drop shadow is excluded by default: it is translucent, varies with focus,
    and would shift the game's offset within the image.

    On a Retina display the image comes back at physical resolution — larger than
    the window's point size. That is fine and stable; use fractional regions so
    nothing depends on the absolute pixel count.
    """
    if not available():
        raise WindowCaptureError("Window capture requires macOS with Quartz (pyobjc).")

    from PIL import Image

    handle, path = tempfile.mkstemp('.png')
    os.close(handle)
    try:
        args = ['screencapture', '-l', str(window_id), '-x']
        if not include_shadow:
            args.append('-o')
        args.append(path)

        result = subprocess.run(args, capture_output=True, text=True)
        if result.returncode != 0 or not os.path.getsize(path):
            raise WindowCaptureError(
                f"screencapture failed for window {window_id} "
                f"(exit {result.returncode}): {result.stderr.strip() or 'no output'}. "
                "The window may be minimised, or Screen Recording permission may be missing."
            )

        image = Image.open(path)
        image.load()
        return image.convert('RGB')
    finally:
        if os.path.exists(path):
            os.unlink(path)


class WindowCapturer:
    """Captures one app's window, re-resolving its id when it goes stale."""

    def __init__(self, owner: str, title: str = ''):
        self.owner = owner
        self.title = title
        self._window_id = None
        self._last_size = None

    def resolve(self, force: bool = False) -> int:
        if self._window_id is None or force:
            window = resolve_window(self.owner, self.title)
            self._window_id = window['id']
            logger.info("Resolved capture window: %s (id %s)", window['owner'], window['id'])
        return self._window_id

    def grab(self):
        """Capture the window, retrying once with a fresh id if it has changed."""
        try:
            image = capture(self.resolve())
        except WindowCaptureError:
            image = capture(self.resolve(force=True))

        if self._last_size and image.size != self._last_size:
            logger.warning(
                "Capture size changed %s -> %s; the window was resized and any "
                "pixel-based regions are now stale.", self._last_size, image.size,
            )
        self._last_size = image.size
        return image

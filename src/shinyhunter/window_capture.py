"""Capture a specific window by id instead of a screen rectangle.

Grabbing a screen rectangle couples every capture to the window's position, the
display's Retina scale factor, and whatever happens to be on top. Capturing the
window itself removes all three: the image is the window's own content, at a
stable size, wherever it sits on screen.

Window ids are not stable across app restarts, so the window is resolved by
owner name each session and the id is re-resolved automatically if a capture
fails.

Two backends behind one interface: macOS via Quartz + `screencapture -l`, and
X11 via `wmctrl` + ImageMagick `import -window`. Callers fall back to region
capture where neither is available.

X11 has no equivalent of macOS's off-screen window buffer: without a compositing
manager, `import` on an obscured window returns whatever is drawn over it. Keep
the game window unobscured.
"""
import logging
import os
import platform
import shutil
import subprocess
import tempfile

logger = logging.getLogger(__name__)

IS_MACOS = platform.system() == 'Darwin'
IS_LINUX = platform.system() == 'Linux'

try:
    import Quartz
    QUARTZ_AVAILABLE = True
except ImportError:
    QUARTZ_AVAILABLE = False
    Quartz = None


class WindowCaptureError(RuntimeError):
    """Raised when a window cannot be found or captured."""


def _has(command: str) -> bool:
    return shutil.which(command) is not None


def backend() -> str:
    """Which capture backend this machine can use: 'quartz', 'x11' or ''."""
    if IS_MACOS and QUARTZ_AVAILABLE:
        return 'quartz'
    if IS_LINUX and _has('wmctrl') and _has('import'):
        return 'x11'
    return ''


def unavailable_reason() -> str:
    """Why window capture is not usable here, and what to install."""
    if IS_MACOS:
        return "macOS window capture needs pyobjc (Quartz): pip install pyobjc-framework-Quartz"
    if IS_LINUX:
        missing = [c for c in ('wmctrl', 'import') if not _has(c)]
        if missing:
            package = 'imagemagick' if 'import' in missing else 'wmctrl'
            return (f"X11 window capture needs {' and '.join(missing)}: "
                    f"sudo apt install wmctrl imagemagick  (missing: {package})")
        return "X11 window capture unavailable for an unknown reason"
    return f"Window capture is not implemented for {platform.system()}"


def available() -> bool:
    return backend() != ''


def parse_wmctrl(output: str, min_width: int = 200, min_height: int = 150) -> list:
    """Parse `wmctrl -lGx` into the same window dicts the Quartz path returns.

    Columns are: id, desktop, x, y, w, h, WM_CLASS, host, title. The title runs to
    end of line and may contain spaces, so the split is bounded at 8 fields.

    WM_CLASS is `instance.Class` -- the closest X11 analogue of macOS's owner
    name, and unlike a window title it is stable, which is what resolution keys on.
    """
    windows = []
    for line in output.splitlines():
        parts = line.split(None, 8)
        if len(parts) < 8:
            continue
        identifier, _desktop, x, y, width, height, wm_class, _host = parts[:8]
        title = parts[8] if len(parts) > 8 else ''
        try:
            x, y, width, height = int(x), int(y), int(width), int(height)
        except ValueError:
            continue
        if width < min_width or height < min_height:
            continue
        if x < -1000 or y < -1000:        # sticky/hidden windows park off-screen
            continue
        windows.append({
            'id': identifier,
            # WM_CLASS is "instance.Class"; split on the FIRST dot only, or a
            # class like "Gimp.Gimp-2.10" yields an owner of "10".
            'owner': wm_class.split('.', 1)[-1] if wm_class else '',
            'wm_class': wm_class,
            'title': title,
            'x': x, 'y': y, 'width': width, 'height': height,
        })
    windows.sort(key=lambda w: -(w['width'] * w['height']))
    return windows


def _list_windows_x11(min_width: int, min_height: int) -> list:
    try:
        result = subprocess.run(['wmctrl', '-lGx'], capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.SubprocessError) as error:
        raise WindowCaptureError(f"wmctrl failed: {error}") from error
    if result.returncode != 0:
        raise WindowCaptureError(
            f"wmctrl exited {result.returncode}: {result.stderr.strip() or 'no output'}. "
            "Is DISPLAY set and pointing at a running X session?")
    return parse_wmctrl(result.stdout, min_width, min_height)


def _capture_x11(window_id, include_frame: bool = False):
    """Capture one X11 window with ImageMagick."""
    from PIL import Image

    handle, path = tempfile.mkstemp('.png')
    os.close(handle)
    try:
        args = ['import', '-window', str(window_id)]
        if include_frame:
            args.append('-frame')
        args.append(path)

        result = subprocess.run(args, capture_output=True, text=True, timeout=20)
        if result.returncode != 0 or not os.path.getsize(path):
            raise WindowCaptureError(
                f"import failed for window {window_id} (exit {result.returncode}): "
                f"{result.stderr.strip() or 'no output'}. The window may be minimised, "
                "or DISPLAY may be wrong.")

        image = Image.open(path)
        image.load()
        return image.convert('RGB')
    finally:
        if os.path.exists(path):
            os.unlink(path)


def list_windows(min_width: int = 200, min_height: int = 150) -> list:
    """On-screen windows large enough to be a game window, biggest first.

    Menu-bar extras and helper windows are filtered out by layer and size.
    """
    if backend() == 'x11':
        return _list_windows_x11(min_width, min_height)
    if not available():
        raise WindowCaptureError(unavailable_reason())

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
        names = ', '.join(sorted({w['owner'] for w in windows if w['owner']})) or 'none'
        titles = ', '.join(sorted({w['title'] for w in windows if w['title']})[:6]) or 'none'
        raise WindowCaptureError(
            f"No window matching owner={owner!r} title={title!r}.\n"
            f"  visible owners: {names}\n"
            f"  visible titles: {titles}"
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
    if backend() == 'x11':
        return _capture_x11(window_id, include_shadow)
    if not available():
        raise WindowCaptureError(unavailable_reason())

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

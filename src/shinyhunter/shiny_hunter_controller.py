import time
import json
import os
import platform
import subprocess
import threading
import traceback

import numpy as np
from config import ConfigManager, project_path
from image_processor import ImageProcessor, crop
from sprite_library import SpriteLibrary, SHINY_DIR, UNKNOWN_DIR
from input_handler import InputHandler
from screenshot_manager import ScreenshotManager

# pyautogui is not needed in this module - removed unused import

# Fallbacks used until these land in ShinyHunterConfig.
DEFAULT_MAX_CONSECUTIVE_ERRORS = 5
DEFAULT_ERROR_BACKOFF_SECONDS = 5.0

# Sequence outcomes. 'not_shiny' replaces the old 'no_shiny'; nothing in the repo
# compared against the old spelling, so the rename is free.
SHINY = "shiny"
NOT_SHINY = "not_shiny"
UNKNOWN_SPRITE = "unknown_sprite"
VERIFY_FAIL = "verify_fail"
TIMEOUT = "timeout"
COMPLETE = "complete"
ERROR = "error"


STEP_FIELDS = {
    'press': {'type', 'key', 'delay_after', 'jitter'},
    'pause': {'type', 'duration', 'jitter'},
    'hold': {'type', 'key', 'duration', 'delay_after', 'jitter'},
    'combo': {'type', 'keys', 'hold_duration', 'delay_after', 'jitter'},
    'verify_screen': {'type', 'template', 'template_path'},
    'check_shiny': {'type', 'reference_path'},
    'wait_for_screen': {'type', 'template', 'template_path', 'roi', 'roi_rect', 'threshold',
                        'expect', 'timeout', 'poll_interval', 'on_timeout', 'on_timeout_result',
                        'delay_after', 'jitter'},
    'walk_until_encounter': {'type', 'keys', 'hold_keys', 'step_duration', 'gap', 'jitter',
                             'poll_every', 'max_steps', 'refocus_every', 'detect_template',
                             'detect_roi', 'threshold'},
    'check_library': {'type', 'roi', 'library', 'samples', 'sample_gap', 'shape_threshold',
                      'colour_threshold', 'ambiguity_margin', 'silhouette_threshold',
                      'stable_tolerance', 'stable_timeout', 'stable_interval'},
}


def unknown_fields(step: dict):
    """Fields a step type does not read.

    Steps are plain dicts, so a misplaced or misspelled key is otherwise a silent
    no-op -- a `delay_after` on a step that ignores it looks like it is waiting
    when it is not.
    """
    allowed = STEP_FIELDS.get(step.get('type'))
    return sorted(set(step) - allowed) if allowed else []


class Outcome(str):
    """A sequence result that also carries diagnostics.

    Subclasses str so it compares, formats and serialises exactly like the plain
    string it wraps — `result == "shiny"` keeps working at every existing call
    site — while `.detail` carries the scores and reasons needed to log, alert,
    or decide what to do next.
    """

    def __new__(cls, value, **detail):
        outcome = super().__new__(cls, value)
        outcome.detail = detail
        return outcome

    def __repr__(self):
        return f"Outcome({str(self)!r}, {self.detail!r})"


class ShinyHunterController:
    """Main driver for shiny hunt application."""

    def __init__(self, log_function=None):
        self.running = False
        self.paused = False
        self.thread = None
        self.startup_countdown = 3
        self.consecutive_errors = 0
        self.consecutive_resets = 0
        self._library = None
        self.unknown_sprite_callback = None   # GUI hook: show the crop, ask the user
        self._reset_count = 0  # Use a plain integer for the attempt counter
        self.log_function = log_function
        
        # Initialize components
        self.config = ConfigManager().get_config()
        self.image_processor = ImageProcessor()
        self.input_handler = InputHandler()
        self.screenshot_manager = ScreenshotManager()

    @property
    def count(self):
        return self._reset_count

    @count.setter
    def count(self, value):
        self._reset_count = int(value)

    def increment_count(self):
        self._reset_count += 1
        return self._reset_count
    
    def log(self, message: str):
        """Log message if log function is available."""
        if self.log_function:
            self.log_function(message)
        print(message)
    
    def countdown(self, seconds: int):
        """Countdown before starting hunt."""
        while seconds > 0:
            self.log(f"Starting in: {seconds}")
            time.sleep(1)
            seconds -= 1
    
    # ------------------------------------------------------------ name lookup

    def _named_region(self, spec: dict, name):
        """Resolve a region given as a name in the hunt spec, or inline."""
        if name is None:
            return None
        if isinstance(name, (list, tuple)):
            return list(name)
        region = (spec.get('rois') or {}).get(name)
        if region is None:
            region = getattr(self.config, f'{name}_roi', None)
        return region

    def _named_template(self, spec: dict, name):
        """Resolve a template path given as a name in the hunt spec, or inline."""
        if not name:
            return None
        if os.path.sep in name or name.endswith('.png'):
            return project_path(name)
        path = (spec.get('templates') or {}).get(name)
        if path is None:
            path = getattr(self.config, f'{name}_template', None)
        return project_path(path) if path else None

    # -------------------------------------------------------------- sequences

    def _step_wait_for_screen(self, step: dict, spec: dict):
        """Poll until a template appears or disappears, or time out.

        The polling variant of verify_screen. While walking, "not in battle yet"
        is the normal state, so a one-shot assertion cannot express it. Keying off
        a state transition also means one check covers many failures at once:
        waiting for the battle screen to *go away* after fleeing detects a failed
        escape, a trainer battle and an item pickup without recognising any of them.
        """
        template = self._named_template(spec, step.get('template') or step.get('template_path'))
        region = self._named_region(spec, step.get('roi') or step.get('roi_rect'))
        threshold = step.get('threshold', getattr(self.config, 'battle_detector_threshold', None))
        expect_present = step.get('expect', 'present') != 'absent'
        timeout = float(step.get('timeout', 15.0))
        interval = float(step.get('poll_interval', 0.35))

        deadline = time.monotonic() + timeout
        best = 0.0
        while True:
            # Native 240x160: the ROI and the template are both defined in that
            # space. Matching against the raw capture searched a rectangle six
            # times too large in the wrong place and only worked by luck.
            frame = self.screenshot_manager.grab_native()
            matched, score = self.image_processor.matches_template(
                frame, template, region=region, threshold=threshold)
            best = max(best, score)
            if matched == expect_present:
                return None, score

            if time.monotonic() >= deadline:
                wanted = 'appear' if expect_present else 'clear'
                return Outcome(step.get('on_timeout_result', TIMEOUT),
                               step='wait_for_screen', expected=wanted,
                               template=template, best_score=round(best, 4),
                               timeout=timeout), best
            time.sleep(interval)

    def _get_library(self, spec: dict, step: dict = None):
        """Sprite library for this hunt, cached and refreshed from disk.

        reload() is mtime-gated, so calling it every encounter costs nothing and
        picks up species added mid-hunt without a restart.
        """
        path = (step or {}).get('library') or spec.get('sprite_library')
        if not path:
            name = spec.get('hunt_name', 'default')
            path = os.path.join(self.config.sprite_library_root, name)
        path = project_path(path)

        if self._library is None or self._library.directory != path:
            self._library = SpriteLibrary(path)
        else:
            self._library.reload()
        return self._library

    def _await_stable_sprite(self, region, step: dict):
        """Block until the sprite box stops changing, or give up.

        The battle detector fires as soon as its own patch is drawn, which can be
        while the wild sprite is still sliding and scaling into place. Classifying
        a half-drawn sprite produces a confident wrong answer -- usually "shiny",
        because the shape still matches while the colours do not.

        Waiting for two consecutive frames to agree adapts to however long the
        animation actually takes, where a fixed delay is either too short on a slow
        frame or wasted time on every other encounter.
        """
        tolerance = float(step.get('stable_tolerance', 1.5))
        timeout = float(step.get('stable_timeout', 4.0))
        interval = float(step.get('stable_interval', 0.12))

        deadline = time.monotonic() + timeout
        previous = None
        while time.monotonic() < deadline:
            current = crop(self.screenshot_manager.grab_native(), region).astype(np.int16)
            if previous is not None and float(np.abs(current - previous).mean()) <= tolerance:
                return True
            previous = current
            time.sleep(interval)

        self.log(f"check_library: sprite still moving after {timeout}s — "
                 "classifying anyway, the verdict may be unreliable")
        return False

    def _step_check_library(self, step: dict, spec: dict) -> Outcome:
        """Identify the wild sprite and decide normal / shiny / unknown.

        Several samples are taken and the best-matching one wins, so a frame
        caught mid-animation cannot by itself demote a known species to unknown.
        """
        library = self._get_library(spec, step)
        region = self._named_region(spec, step.get('roi') or 'enemy_sprite')

        samples = max(1, int(step.get('samples', 2)))
        gap = float(step.get('sample_gap', 0.2))

        self._await_stable_sprite(region, step)

        best = None
        best_crop = None
        for index in range(samples):
            if index:
                time.sleep(gap)
            sprite = crop(self.screenshot_manager.grab_native(), region)
            result = library.identify(
                sprite,
                shape_threshold=step.get('shape_threshold', self.config.sprite_shape_threshold),
                colour_threshold=step.get('colour_threshold', self.config.sprite_colour_threshold),
                ambiguity_margin=step.get('ambiguity_margin', self.config.sprite_ambiguity_margin),
                silhouette_threshold=step.get('silhouette_threshold',
                                              self.config.sprite_silhouette_threshold),
            )
            if best is None or result.shape_score > best.shape_score:
                best, best_crop = result, sprite

        detail = {
            'species': best.species,
            'shape_score': round(best.shape_score, 4),
            'colour_distance': round(best.colour_distance, 4),
            'runner_up': best.runner_up,
            'reason': best.reason,
            'library_size': len(library),
        }

        if best.verdict == 'normal':
            self.log(f"check_library: {best.species} (normal) "
                     f"shape={best.shape_score:.3f} colour={best.colour_distance:.3f}")
            return Outcome(NOT_SHINY, **detail)

        if best.verdict == 'shiny':
            detail['crop_path'] = library.save_aside(best_crop, SHINY_DIR, best.species or 'shiny')
            self.log(f"*** SHINY {str(best.species).upper()} *** "
                     f"shape={best.shape_score:.3f} colour={best.colour_distance:.3f}")
            return Outcome(SHINY, **detail)

        detail['crop_path'] = library.save_aside(best_crop, UNKNOWN_DIR)
        self.log(f"check_library: UNKNOWN sprite — {best.reason}")
        self.log(f"  crop saved to {detail['crop_path']}")
        return Outcome(UNKNOWN_SPRITE, **detail)

    def _detector_for(self, step: dict, spec: dict):
        """Template, region and threshold for a step's screen detector."""
        template = self._named_template(
            spec, step.get('detect_template') or step.get('template') or 'battle_detector')
        region = self._named_region(
            spec, step.get('detect_roi') or step.get('roi') or 'battle_detector')
        threshold = step.get('threshold', self.config.battle_detector_threshold)
        return template, region, threshold

    def _step_walk_until_encounter(self, step: dict, spec: dict):
        """Walk a repeating pattern until a battle is detected, or give up.

        Returns (outcome, steps_taken). outcome is None when a battle was found.

        Encounters trigger after a random number of steps, so this is a poll loop
        rather than a fixed script. Movement holds each direction for a full tile:
        a tap spends its first ~8 frames turning in place, so short presses can
        pivot on the spot forever without ever changing tile.
        """
        keys = step.get('keys') or ['left', 'right']
        hold_keys = step.get('hold_keys') or []
        duration = float(step.get('step_duration', self.config.walk_step_duration))
        gap = float(step.get('gap', 0.0))
        jitter = step.get('jitter', self.config.walk_jitter)
        poll_every = max(1, int(step.get('poll_every', 4)))
        max_steps = int(step.get('max_steps', 200))
        refocus_every = int(step.get('refocus_every', 50))

        template, region, threshold = self._detector_for(step, spec)

        def battle_visible():
            matched, score = self.image_processor.matches_template(
                self.screenshot_manager.grab_native(), template,
                region=region, threshold=threshold)
            return matched, score

        taken = 0
        started = time.monotonic()

        with self.input_handler.fast_input():
            self.input_handler.press_keys_down(hold_keys)
            try:
                # Already in a battle before taking a step (e.g. resumed mid-battle).
                matched, score = battle_visible()
                if matched:
                    return None, 0

                while taken < max_steps:
                    if not self.running:
                        return Outcome(COMPLETE, step='walk_until_encounter',
                                       reason='stopped', steps=taken), taken

                    if self.paused:
                        # Do not walk while paused; drop the held keys so the game
                        # is not left running on the spot.
                        self.input_handler.release_keys(hold_keys)
                        while self.paused and self.running:
                            time.sleep(0.1)
                        if not self.running:
                            return Outcome(COMPLETE, step='walk_until_encounter',
                                           reason='stopped', steps=taken), taken
                        self.input_handler.press_keys_down(hold_keys)

                    self.input_handler.hold_key_for(keys[taken % len(keys)], duration)
                    taken += 1

                    if gap > 0:
                        self.input_handler._jittered_sleep(gap, jitter)

                    if refocus_every and taken % refocus_every == 0:
                        self.input_handler.ensure_window_focused()

                    if taken % poll_every == 0:
                        matched, score = battle_visible()
                        if matched:
                            elapsed = time.monotonic() - started
                            self.log(f"encounter after {taken} steps "
                                     f"({elapsed:.1f}s, {elapsed / max(taken, 1):.2f}s/step)")
                            return None, taken

                return Outcome(TIMEOUT, step='walk_until_encounter',
                               reason='no_encounter', steps=taken,
                               max_steps=max_steps), taken
            finally:
                # Never leave a direction or the run button held down.
                self.input_handler.release_keys(hold_keys)

    def _run_sequence(self, steps: list, spec: dict = None) -> Outcome:
        """Execute a full custom sequence (input + screenshot steps).

        Returns an Outcome: 'shiny' | 'not_shiny' | 'unknown_sprite' |
        'verify_fail' | 'timeout' | 'complete' | 'error'. Outcome subclasses str,
        so existing comparisons against the plain strings still work.
        """
        spec = spec or {}
        self.input_handler.ensure_window_focused()
        current = None

        try:
            for step in steps:
                current = step
                t = step.get("type")

                stray = unknown_fields(step)
                if stray:
                    self.log(f"Warning: {t} ignores {', '.join(stray)} — "
                             "check the field name, it is doing nothing")

                if t in ("press", "pause", "hold", "combo"):
                    self.input_handler.execute_input_step(step)

                elif t == "check_library":
                    return self._step_check_library(step, spec)

                elif t == "walk_until_encounter":
                    outcome, taken = self._step_walk_until_encounter(step, spec)
                    if outcome is not None:
                        if outcome == TIMEOUT:
                            self.log(f"walk_until_encounter: no battle in {taken} steps — "
                                     "stuck against a wall, wrong detector, or lost focus")
                        return outcome

                elif t == "wait_for_screen":
                    outcome, score = self._step_wait_for_screen(step, spec)
                    label = step.get('template', '?')
                    if outcome is not None:
                        self.log(f"wait_for_screen ({label}): timed out after "
                                 f"{step.get('timeout', 15.0)}s, best score {score:.3f}")
                        if step.get('on_timeout') == 'continue':
                            continue
                        return outcome
                    self.log(f"wait_for_screen ({label}): confirmed (score {score:.3f})")
                    settle = float(step.get('delay_after', 0) or 0)
                    if settle > 0:
                        self.input_handler._jittered_sleep(settle, step.get('jitter', 0))

                elif t == "verify_screen":
                    template_key = step.get("template", "pre_encounter")
                    if "template_path" in step:
                        resolved_template = step["template_path"]
                    elif template_key == "encounter":
                        resolved_template = self.config.encounter_template_path
                    else:
                        resolved_template = self.config.pre_encounter_template_path
                    path = self.screenshot_manager.take_screenshot('seq_verify.png')
                    if not self.image_processor.is_on_encounter_screen(path, resolved_template):
                        self.log(f"verify_screen ({template_key}): wrong screen — restarting")
                        return Outcome(VERIFY_FAIL, step='verify_screen', template=template_key)
                    self.log(f"verify_screen ({template_key}): screen confirmed")

                elif t == "check_shiny":
                    path = self.screenshot_manager.take_screenshot('current_screenshot.png')
                    ref = step.get("reference_path", self.config.calibration_reference_path)
                    if self.image_processor.is_shiny_found(ref, path):
                        return Outcome(SHINY, step='check_shiny')
                    self.log("check_shiny: no shiny — restarting")
                    return Outcome(NOT_SHINY, step='check_shiny')

                else:
                    self.log(f"Warning: unknown step type '{t}', skipping")

        except Exception as error:
            # Contained here as well as in the hunt loop so a failing step yields a
            # usable outcome with the offending step attached, rather than a
            # traceback with no context.
            self.log(f"ERROR in step {current!r}: {error!r}")
            return Outcome(ERROR, step=current, exception=repr(error),
                           traceback=traceback.format_exc())

        return Outcome(COMPLETE)

    def _load_hunt_spec(self) -> dict:
        """Load the whole hunt definition, not just its steps.

        The old loader returned only data["encounter_sequence"] and discarded
        every other key, which is what prevented hunts from carrying their own
        regions, templates, library and retry behaviour.
        """
        seq_path = project_path(self.config.sequence_config_path)
        with open(seq_path, 'r', encoding='utf-8') as f:
            spec = json.load(f)
        if not isinstance(spec, dict):
            raise ValueError(f"{seq_path} must contain a JSON object")
        return spec

    def _load_custom_sequence_steps(self):
        """Backwards-compatible accessor for just the encounter steps."""
        return self._load_hunt_spec().get("encounter_sequence", [])

    def attempt_encounter(self):
        """Main hunt loop - encounter, check, and reset.

        Runs on its own thread. A failing attempt must never kill this loop: an
        unattended overnight hunt that dies at 1am on a transient cv2 error is
        indistinguishable from one that simply never found anything. Errors pause
        the hunt instead, keeping the thread, the log and the counter alive.
        """
        if self.startup_countdown > 0:
            self.countdown(self.startup_countdown)

        self.consecutive_errors = 0

        while self.running:
            if self.paused:
                time.sleep(0.1)
                continue

            try:
                if self._run_one_attempt():
                    break
                self.consecutive_errors = 0
            except Exception as error:
                self._handle_loop_error(error)

        self.log("Hunt loop exited")

    def _run_one_attempt(self) -> bool:
        """Run a single encounter attempt. Returns True when the hunt should stop."""
        config = ConfigManager().get_config()
        self.log("Attempting encounter #{}".format(self.count + 1))

        if config.use_custom_sequence:
            # --- Custom sequence mode ---
            try:
                spec = self._load_hunt_spec()
            except Exception as error:
                self.log(f"ERROR: Could not load custom sequence — {error}")
                self.log("Hunt paused. Fix your sequence config, then press Resume.")
                self.paused = True
                return False

            result = self._run_sequence(spec.get("encounter_sequence", []), spec)
            self.increment_count()
            self.log(f"Attempt #{self.count}")

            if result == SHINY:
                self._handle_shiny_found(result.detail if isinstance(result, Outcome) else None)
                return True

            if result == UNKNOWN_SPRITE:
                self._handle_unknown(spec, result.detail)
                return False

            if result in (TIMEOUT, VERIFY_FAIL, ERROR):
                self._escalate(spec, result)
                return False

            # NOT_SHINY or COMPLETE
            self.consecutive_errors = 0
            self._handle_retry(spec)
            return False

        # --- Static mode ---
        if hasattr(self.input_handler, 'encounter_sequence_with_verification'):
            encounter_success = self.input_handler.encounter_sequence_with_verification(
                self.screenshot_manager, self.image_processor
            )
            print(f"Encounter success: {encounter_success}")
            if not encounter_success:
                self.log('Failed to reach encounter screen, restarting...')
                self.input_handler.restart_sequence()
                return False

            self.increment_count()
            self.log(f"Attempt #{self.count}")
        else:
            self.increment_count()
            self.log(f"Attempt #{self.count}")
            self.input_handler.encounter_sequence()

        screenshot_path = self.screenshot_manager.take_screenshot('current_screenshot.png')
        if self.image_processor.is_shiny_found(self.config.calibration_reference_path, screenshot_path):
            self._handle_shiny_found()
            return True

        self._handle_no_shiny()
        return False

    def _handle_loop_error(self, error: Exception):
        """Contain an unexpected error: back off, and pause if they keep coming.

        Never sets running = False — that is unrecoverable and would leave a dead
        app with no diagnosis in the morning.
        """
        self.consecutive_errors += 1
        limit = getattr(self.config, 'max_consecutive_errors', DEFAULT_MAX_CONSECUTIVE_ERRORS)

        self.log(f"ERROR in hunt loop: {error!r}")
        self.log(traceback.format_exc())

        if self.consecutive_errors >= limit:
            self.paused = True
            self.log(
                f"HUNT PAUSED after {self.consecutive_errors} consecutive errors — "
                "inspect the log above, then press Resume."
            )
            return

        backoff = getattr(self.config, 'error_backoff_seconds', DEFAULT_ERROR_BACKOFF_SECONDS)
        self.log(f"Retrying in {backoff:.1f}s ({self.consecutive_errors}/{limit})")
        time.sleep(backoff)

    # ------------------------------------------------------------ retry logic

    def _handle_retry(self, spec: dict) -> bool:
        """Do whatever this hunt does after a non-shiny encounter.

        Defaults to 'reset' so the existing Game Corner hunt, which has no
        on_not_shiny field and relies on the built-in FRLG soft reset, behaves
        exactly as before.
        """
        action = spec.get('on_not_shiny', 'reset')

        if action == 'none':
            return True
        if action == 'flee':
            return self._do_flee(spec)
        return self._do_reset(spec)

    def _do_flee(self, spec: dict) -> bool:
        """Run away and get back to walking, escalating if the escape fails.

        Every rung re-tests one predicate — has the battle screen cleared — so a
        failed escape, a trainer battle, an item pickup and a level-up dialogue
        are all handled without recognising any of them individually.
        """
        flee_sequence = spec.get('flee_sequence')
        if not flee_sequence:
            self.log("on_not_shiny is 'flee' but the hunt defines no flee_sequence")
            return self._do_reset(spec)

        attempts = int(spec.get('max_flee_attempts', self.config.max_flee_attempts))

        for attempt in range(1, attempts + 1):
            result = self._run_sequence(flee_sequence, spec)
            if result == COMPLETE:
                self.consecutive_resets = 0
                return True
            self.log(f"flee attempt {attempt}/{attempts} did not clear the battle ({result!r})")

        recover = spec.get('recover_sequence')
        if recover:
            self.log("running recover_sequence to clear any stuck dialogue")
            if self._run_sequence(recover, spec) == COMPLETE:
                cleared = self._battle_cleared(spec)
                if cleared:
                    self.consecutive_resets = 0
                    return True

        self.log("could not escape — escalating to reset")
        return self._do_reset(spec)

    def _battle_cleared(self, spec: dict) -> bool:
        """True when the battle screen is no longer showing."""
        probe = {'type': 'wait_for_screen', 'template': 'battle_detector',
                 'roi': 'battle_detector', 'expect': 'absent',
                 'timeout': 3.0, 'poll_interval': 0.3}
        outcome, _ = self._step_wait_for_screen(probe, spec)
        return outcome is None

    def _do_reset(self, spec: dict) -> bool:
        """Soft reset, via the hunt's own sequence or the built-in FRLG one.

        An absent reset_sequence means "use the built-in"; an empty one means
        "deliberately do nothing", so the two are kept distinct.
        """
        self.consecutive_resets += 1
        limit = int(spec.get('max_consecutive_resets', self.config.max_consecutive_resets))

        if self.consecutive_resets >= limit:
            self.paused = True
            self.log(f"HUNT PAUSED after {self.consecutive_resets} resets in a row — "
                     "the game is probably not where the hunt expects it. "
                     "Check the screen, then press Resume.")
            self._alert("Hunt paused", f"{self.consecutive_resets} resets in a row")
            return False

        sequence = spec.get('reset_sequence')
        if sequence:
            return self._run_sequence(sequence, spec) == COMPLETE
        if sequence == []:
            return True

        self.screenshot_manager.take_screenshot('emulator_screenshot.png')
        time.sleep(1)
        self.input_handler.restart_sequence()
        return True

    def _handle_unknown(self, spec: dict, detail: dict) -> bool:
        """React to a sprite that matched nothing in the library."""
        action = spec.get('on_unknown_sprite', 'pause')
        crop_path = detail.get('crop_path')

        if action == 'flee':
            self.log("unknown sprite — fleeing and continuing (on_unknown_sprite: flee)")
            return self._handle_retry(spec)

        self.paused = True
        self.log("HUNT PAUSED — unrecognised sprite. It may be a shiny, or a species "
                 "not yet in the library.")
        if crop_path:
            self.log(f"  crop: {crop_path}")
        self.log("  Add it with: python tools/add_species.py "
                 f"{spec.get('hunt_name', '<hunt>')} <species> --crop <path>")
        self._alert("Unknown sprite", detail.get('reason', ''))

        if self.unknown_sprite_callback:
            try:
                self.unknown_sprite_callback(detail)
            except Exception as error:
                self.log(f"unknown-sprite callback failed: {error!r}")
        return False

    def _escalate(self, spec: dict, result: Outcome) -> bool:
        """Recover from a timeout, a failed verify, or an error mid-sequence."""
        self.log(f"attempt ended as {result!r} — attempting recovery")

        if self._battle_cleared(spec):
            # Not stuck in a battle, so walking again is enough.
            return True

        return self._do_flee(spec) if spec.get('on_not_shiny') == 'flee' else self._do_reset(spec)

    def _alert(self, title: str, message: str):
        """Best-effort desktop notification and sound.

        A hunt that pauses at 3am is useless if nothing says so.
        """
        try:
            if platform.system() == 'Darwin':
                subprocess.run(['osascript', '-e',
                                f'display notification {json.dumps(message)} '
                                f'with title {json.dumps(title)} sound name "Glass"'],
                               capture_output=True, timeout=5)
        except Exception as error:
            print(f"Could not raise alert: {error}")

    def _handle_shiny_found(self, detail: dict = None):
        """Handle when a shiny is found."""
        self.log('*** SHINY FOUND ***')
        if detail:
            self.log(f"  species={detail.get('species')} "
                     f"shape={detail.get('shape_score')} colour={detail.get('colour_distance')}")
            if detail.get('crop_path'):
                self.log(f"  sprite crop: {detail['crop_path']}")
        path = self.screenshot_manager.take_timestamped_screenshot('shiny_found')
        self.log(f"  full screenshot: {path}")
        self._alert("SHINY FOUND", str((detail or {}).get('species', '')).upper())
        self.running = False
    
    def _handle_no_shiny(self):
        """Handle when no shiny is found."""
        self.log('No Shiny Found!')
        self.screenshot_manager.take_screenshot('emulator_screenshot.png')
        time.sleep(1)  # Brief pause before reset
        self.input_handler.restart_sequence()
    
    def set_running_status(self, status: bool):
        self.running = status

    def start_hunt(self):
        """Mark the hunt as running.

        The startup countdown runs on the hunt thread, not here — this is called
        from the GUI thread and a blocking countdown freezes the UI.
        """
        self.running = True
        self.paused = False
        self.consecutive_errors = 0
        self.log(f"Running Status set to: {self.running}")

    def pause_hunt(self):
        if self.running:
            self.paused = not self.paused
            self.log(f"Hunt {'paused' if self.paused else 'resumed'}")

    def stop_hunt(self):
        self.running = False
        self.paused = False

        thread = self.thread
        if thread and thread.is_alive() and thread is not threading.current_thread():
            thread.join(timeout=5.0)
            if thread.is_alive():
                self.log("Warning: hunt thread did not exit within 5s")
        self.thread = None

        self.log("Hunt stopped")

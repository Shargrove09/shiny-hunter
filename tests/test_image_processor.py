"""Tests for the ImageProcessor module."""

import pytest
from image_processor import ImageProcessor


class TestImageProcessor:
    """Verify ImageProcessor logic without requiring actual image files."""

    def test_init(self):
        processor = ImageProcessor()
        assert processor is not None

    def test_missing_screenshot_returns_false(self):
        """is_on_encounter_screen returns False for a nonexistent file."""
        processor = ImageProcessor()
        assert processor.is_on_encounter_screen("/nonexistent/path.png") is False

    def test_shiny_found_missing_files_returns_false(self):
        """is_shiny_found returns False when files do not exist."""
        processor = ImageProcessor()
        assert processor.is_shiny_found("/no/ref.png", "/no/shot.png") is False

    def test_get_correlation_missing_files(self):
        """get_correlation returns 0.0 when files do not exist."""
        processor = ImageProcessor()
        assert processor.get_correlation("/no/ref.png", "/no/shot.png") == 0.0

    def test_suggest_threshold_empty_raises(self):
        """suggest_threshold_from_normals raises on empty input."""
        processor = ImageProcessor()
        with pytest.raises(ValueError):
            processor.suggest_threshold_from_normals([], 0.0001)

    def test_suggest_threshold_single_sample(self):
        """With one sample the threshold is below the sample value."""
        processor = ImageProcessor()
        threshold = processor.suggest_threshold_from_normals([0.95], 0.0001)
        assert 0.0 <= threshold < 0.95

    def test_suggest_threshold_multiple_samples(self):
        """With multiple normal samples the threshold stays in [0, 1]."""
        processor = ImageProcessor()
        samples = [0.90, 0.92, 0.91, 0.93]
        threshold = processor.suggest_threshold_from_normals(samples, 0.0001)
        assert 0.0 <= threshold <= 1.0
        assert threshold < min(samples)

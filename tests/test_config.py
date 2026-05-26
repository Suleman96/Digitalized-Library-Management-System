# =============================================================================
# tests/test_config.py — Iqra Digital Library
# =============================================================================
# Unit tests for the config module.
# Run:  pytest tests/test_config.py -v
# =============================================================================

from __future__ import annotations

from pathlib import Path

import pytest

from config import settings


class TestSettings:
    """Verify the Settings dataclass properties are sane."""

    def test_base_dir_exists(self) -> None:
        assert settings.base_dir.is_dir(), "base_dir must point to an existing directory"

    def test_csv_path_is_path(self) -> None:
        assert isinstance(settings.csv_path, Path)

    def test_index_path_under_artifacts(self) -> None:
        assert "artifacts" in str(settings.index_path)

    def test_meta_path_under_artifacts(self) -> None:
        assert "artifacts" in str(settings.meta_path)

    def test_index_path_extension(self) -> None:
        assert settings.index_path.suffix == ".faiss"

    def test_meta_path_extension(self) -> None:
        assert settings.meta_path.suffix == ".pkl"

    def test_languages_contains_english(self) -> None:
        assert "English" in settings.languages
        assert settings.languages["English"] == "en"

    def test_languages_contains_arabic(self) -> None:
        assert "Arabic" in settings.languages
        assert settings.languages["Arabic"] == "ar"

    def test_search_modes_has_both(self) -> None:
        assert "Both" in settings.search_modes

    def test_search_modes_has_local_only(self) -> None:
        assert "Local Only" in settings.search_modes

    def test_sort_options_has_rating(self) -> None:
        assert "Rating" in settings.sort_options

    def test_sort_options_has_year(self) -> None:
        assert "Year" in settings.sort_options

    def test_server_port_is_int(self) -> None:
        assert isinstance(settings.server_port, int)

    def test_server_host_is_str(self) -> None:
        assert isinstance(settings.server_host, str)

    def test_gradio_share_is_bool(self) -> None:
        assert isinstance(settings.gradio_share, bool)


class TestFlatAliases:
    """The flat module-level aliases must exist and be the right type."""

    def test_csv_path_alias(self) -> None:
        from config import CSV_PATH
        assert isinstance(CSV_PATH, str)

    def test_index_path_alias(self) -> None:
        from config import INDEX_PATH
        assert isinstance(INDEX_PATH, str)

    def test_meta_path_alias(self) -> None:
        from config import META_PATH
        assert isinstance(META_PATH, str)

    def test_languages_alias(self) -> None:
        from config import LANGUAGES
        assert isinstance(LANGUAGES, dict)

    def test_search_modes_alias(self) -> None:
        from config import SEARCH_MODES
        assert isinstance(SEARCH_MODES, list)

    def test_sort_by_options_alias(self) -> None:
        from config import SORT_BY_OPTIONS
        assert isinstance(SORT_BY_OPTIONS, list)

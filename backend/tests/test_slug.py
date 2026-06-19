"""Unit tests for app.services.slug — shared slug validator.

Extracted from duplicated _validate_slug definitions in:
- app/api/constructor.py:53
- app/api/registry.py:36
"""
import pytest
from app.services.slug import validate_slug, is_valid_slug, SLUG_RE


class TestIsValidSlug:
    def test_simple_alphanumeric(self):
        assert is_valid_slug("nginx") is True
        assert is_valid_slug("postgresql-16") is True
        assert is_valid_slug("abc123") is True

    def test_max_length_62(self):
        # 62 chars: starts with a, ends with z, all in [a-z0-9-]
        assert is_valid_slug("a" + "b" * 60 + "z") is True

    def test_too_long_63_rejected(self):
        assert is_valid_slug("a" + "b" * 61 + "z") is False

    def test_too_short_single_char_rejected(self):
        # Pattern requires at least 2 chars: start + end
        assert is_valid_slug("a") is False

    def test_path_traversal_rejected(self):
        assert is_valid_slug("../etc/passwd") is False
        assert is_valid_slug("..") is False
        assert is_valid_slug("foo/../bar") is False
        assert is_valid_slug("foo\\bar") is False
        assert is_valid_slug("foo%2Fbar") is False  # url-encoded
        assert is_valid_slug("foo\x00bar") is False  # null byte

    def test_special_chars_rejected(self):
        assert is_valid_slug("foo_bar") is False
        assert is_valid_slug("FOO") is False  # uppercase
        assert is_valid_slug("foo.bar") is False
        assert is_valid_slug("foo@bar") is False
        assert is_valid_slug("foo bar") is False  # space
        assert is_valid_slug("") is False

    def test_cannot_start_or_end_with_hyphen(self):
        assert is_valid_slug("-foo") is False
        assert is_valid_slug("foo-") is False


class TestValidateSlug:
    """validate_slug() returns the slug on success, raises HTTPException on failure."""

    def test_returns_slug_on_valid(self):
        from fastapi import HTTPException
        assert validate_slug("nginx") == "nginx"
        assert validate_slug("postgresql-16") == "postgresql-16"

    def test_raises_400_on_invalid(self):
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            validate_slug("../etc/passwd")
        assert exc_info.value.status_code == 400
        assert "../etc/passwd" in str(exc_info.value.detail)

    def test_context_message_included(self):
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            validate_slug("Bad Slug", " in components list")
        assert "in components list" in str(exc_info.value.detail)


class TestSlugReExported:
    def test_slug_re_is_exposed(self):
        import re
        assert isinstance(SLUG_RE, re.Pattern)
        # Spot-check the pattern compiles and matches expected shape
        assert SLUG_RE.match("abc-123")
        assert not SLUG_RE.match("ABC")

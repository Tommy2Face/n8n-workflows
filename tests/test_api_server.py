#!/usr/bin/env python3
"""Tests for n8n-workflows api_server.py — FastAPI Search Engine."""

import os
import sys
import time
import pytest

# Add parent dir to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api_server import validate_filename, check_rate_limit, rate_limit_storage, ALLOWED_ORIGINS


# ─── validate_filename ───────────────────────────────────────────────────────


class TestValidateFilename:
    """Path traversal protection tests."""

    def test_valid_json_filename(self):
        assert validate_filename("workflow-123.json") is True

    def test_valid_with_underscores(self):
        assert validate_filename("my_workflow_v2.json") is True

    def test_valid_alphanumeric(self):
        assert validate_filename("Test123.json") is True

    # Path traversal attacks
    def test_rejects_parent_directory(self):
        assert validate_filename("../etc/passwd") is False

    def test_rejects_double_dot(self):
        assert validate_filename("..") is False

    def test_rejects_windows_traversal(self):
        assert validate_filename("..\\windows\\system32") is False

    def test_rejects_encoded_traversal(self):
        assert validate_filename("%2e%2e%2f") is False

    def test_rejects_double_encoded_traversal(self):
        assert validate_filename("%252e%252e%252f") is False

    def test_rejects_null_byte(self):
        assert validate_filename("file\x00.json") is False

    def test_rejects_newlines(self):
        assert validate_filename("file\n.json") is False
        assert validate_filename("file\r.json") is False

    # Absolute paths
    def test_rejects_absolute_unix_path(self):
        assert validate_filename("/etc/passwd") is False

    def test_rejects_absolute_windows_path(self):
        assert validate_filename("C:\\Windows\\System32") is False

    # Shell injection
    def test_rejects_semicolons(self):
        assert validate_filename("file;rm -rf.json") is False

    def test_rejects_ampersand(self):
        assert validate_filename("file&cmd.json") is False

    def test_rejects_pipe(self):
        assert validate_filename("file|cat.json") is False

    def test_rejects_dollar_sign(self):
        assert validate_filename("$HOME.json") is False

    def test_rejects_wildcards(self):
        assert validate_filename("*.json") is False
        assert validate_filename("?.json") is False

    # Extension checks
    def test_rejects_non_json(self):
        assert validate_filename("file.txt") is False
        assert validate_filename("file.py") is False

    def test_rejects_no_extension(self):
        assert validate_filename("filename") is False

    # Special characters
    def test_rejects_tilde(self):
        assert validate_filename("~/.ssh/id_rsa") is False

    def test_rejects_forward_slash(self):
        assert validate_filename("path/to/file.json") is False

    def test_rejects_backslash(self):
        assert validate_filename("path\\to\\file.json") is False

    def test_rejects_colon(self):
        assert validate_filename("C:file.json") is False

    def test_rejects_angle_brackets(self):
        assert validate_filename("<script>.json") is False
        assert validate_filename("redirect>.json") is False


# ─── check_rate_limit ────────────────────────────────────────────────────────


class TestCheckRateLimit:
    def setup_method(self):
        """Clear rate limit storage before each test."""
        rate_limit_storage.clear()

    def test_first_request_allowed(self):
        assert check_rate_limit("192.168.1.1") is True

    def test_multiple_requests_within_limit(self):
        for _ in range(10):
            assert check_rate_limit("192.168.1.2") is True

    def test_exceeds_limit(self):
        ip = "192.168.1.3"
        for _ in range(60):
            check_rate_limit(ip)
        assert check_rate_limit(ip) is False

    def test_different_ips_independent(self):
        ip1, ip2 = "10.0.0.1", "10.0.0.2"
        for _ in range(60):
            check_rate_limit(ip1)
        assert check_rate_limit(ip1) is False
        assert check_rate_limit(ip2) is True

    def test_old_entries_cleaned(self):
        ip = "10.0.0.3"
        # Add entries 61 seconds ago (expired)
        rate_limit_storage[ip] = [time.time() - 61 for _ in range(60)]
        # Should allow new request since old ones expired
        assert check_rate_limit(ip) is True


# ─── CORS configuration ─────────────────────────────────────────────────────


class TestCORSConfig:
    def test_localhost_origins_included(self):
        assert "http://localhost:3000" in ALLOWED_ORIGINS
        assert "http://localhost:8000" in ALLOWED_ORIGINS

    def test_no_wildcard_origin(self):
        assert "*" not in ALLOWED_ORIGINS

    def test_all_origins_are_urls(self):
        for origin in ALLOWED_ORIGINS:
            assert origin.startswith("http://") or origin.startswith("https://")

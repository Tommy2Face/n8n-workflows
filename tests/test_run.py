#!/usr/bin/env python3
"""Tests for n8n-workflows run.py — Search Engine Launcher."""

import os
import sys
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from run import check_requirements, setup_directories


# ─── check_requirements ─────────────────────────────────────────────────────


class TestCheckRequirements:
    def test_returns_true_when_deps_available(self):
        # In a valid venv with fastapi/uvicorn installed, this should pass
        result = check_requirements()
        assert result is True


# ─── setup_directories ──────────────────────────────────────────────────────


class TestSetupDirectories:
    def test_creates_expected_directories(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        setup_directories()
        assert (tmp_path / "database").is_dir()
        assert (tmp_path / "static").is_dir()
        assert (tmp_path / "workflows").is_dir()

    def test_idempotent(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        setup_directories()
        setup_directories()  # Should not error
        assert (tmp_path / "database").is_dir()

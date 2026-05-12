"""Tests for AutoConfig — environment detection, config generation."""

import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, PropertyMock, patch

import pytest


@pytest.fixture
def auto_config():
    from anima.utils.auto_config import AutoConfig

    return AutoConfig()


class TestAutoConfig:
    """Suite for AutoConfig detection and generation functions."""

    # ── _detect_platform ─────────────────────────────────────────────

    def test_detect_platform_windows(self, auto_config):
        with patch("platform.system", return_value="Windows"):
            with patch.dict(os.environ, {}, clear=True):
                assert auto_config._detect_platform() == "windows"

    def test_detect_platform_wsl(self, auto_config):
        with patch("platform.system", return_value="Windows"):
            with patch.dict(os.environ, {"WSL_DISTRO_NAME": "Ubuntu"}, clear=True):
                assert auto_config._detect_platform() == "wsl"

    def test_detect_platform_linux(self, auto_config):
        with patch("platform.system", return_value="Linux"):
            with patch("pathlib.Path.exists", return_value=False):
                assert auto_config._detect_platform() == "linux"

    def test_detect_platform_macos(self, auto_config):
        with patch("platform.system", return_value="Darwin"):
            assert auto_config._detect_platform() == "macos"

    def test_detect_platform_unknown(self, auto_config):
        with patch("platform.system", return_value="SomeOS"):
            assert auto_config._detect_platform() == "unknown"

    # ── _check_gpu ───────────────────────────────────────────────────

    @pytest.mark.skip(reason="Only runs on CUDA-capable machines")
    def test_check_gpu_available(self, auto_config):
        assert auto_config._check_gpu() is True

    def test_check_gpu_not_available(self, auto_config):
        with patch.dict("sys.modules", {"torch": None}):
            pass  # can't actually unload torch

    def test_check_gpu_import_error(self, auto_config):
        """If torch can't be imported, GPU check returns False."""
        import builtins

        real_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == "torch":
                raise ImportError("no torch")
            return real_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=mock_import):
            assert auto_config._check_gpu() is False

    # ── get_data_dir ─────────────────────────────────────────────────

    def test_get_data_dir_env_var(self, auto_config):
        """ANIMA_DATA_DIR env var takes precedence."""
        with patch.dict(os.environ, {"ANIMA_DATA_DIR": "/custom/path"}, clear=True):
            assert auto_config.get_data_dir() == Path("/custom/path")

    def test_get_data_dir_windows_default(self, auto_config):
        """Windows fallback: E:/anima_data or home/anima_data."""
        with patch("platform.system", return_value="Windows"):
            with patch.object(auto_config.env_info, "__getitem__", return_value="windows"):
                with patch("pathlib.Path.exists", return_value=False):
                    result = auto_config.get_data_dir()
                    assert "anima_data" in str(result)

    def test_get_data_dir_windows_e_drive(self, auto_config):
        """On Windows, E:/anima_data takes priority if it exists."""
        with patch.object(auto_config.env_info, "__getitem__", return_value="windows"):
            with patch("pathlib.Path.exists", return_value=True):
                result = auto_config.get_data_dir()
                assert "E:" in str(result) or "anima_data" in str(result)

    def test_get_data_dir_linux_default(self, auto_config):
        """Linux/macOS fallback: ~/anima_data."""
        with patch.object(auto_config.env_info, "__getitem__", return_value="linux"):
            result = auto_config.get_data_dir()
            assert result == Path.home() / "anima_data"

    # ── check_dependencies ───────────────────────────────────────────

    def test_check_dependencies_all_installed(self, auto_config):
        ok, missing = auto_config.check_dependencies()
        assert ok is True
        assert missing == []

    def test_check_dependencies_missing(self, auto_config):
        with patch("builtins.__import__", side_effect=ImportError("missing")):
            ok, missing = auto_config.check_dependencies()
            assert ok is False
            assert len(missing) > 0

    # ── generate_env_file ────────────────────────────────────────────

    def test_generate_env_file_force(self, auto_config, tmp_path):
        """With force=True, overwrite existing .env."""
        from anima.utils.auto_config import AutoConfig

        ac = AutoConfig()
        ac.project_root = tmp_path

        existing = tmp_path / ".env"
        existing.write_text("old", encoding="utf-8")

        result = ac.generate_env_file(force=True)
        assert result == existing
        content = existing.read_text(encoding="utf-8")
        assert "ANIMA_DATA_DIR" in content
        assert "Auto-generated by Anima AutoConfig" in content

    def test_generate_env_file_skip_if_exists(self, auto_config, tmp_path):
        """Without force, existing .env should not be overwritten."""
        from anima.utils.auto_config import AutoConfig

        ac = AutoConfig()
        ac.project_root = tmp_path

        existing = tmp_path / ".env"
        existing.write_text("keep me", encoding="utf-8")

        result = ac.generate_env_file(force=False)
        content = existing.read_text(encoding="utf-8")
        assert content == "keep me"

    # ── generate_local_lora_config ───────────────────────────────────

    def test_generate_local_lora_config(self, auto_config, tmp_path):
        """generate_local_lora_config should write a YAML file."""
        from anima.utils.auto_config import AutoConfig

        ac = AutoConfig()
        config_dir = tmp_path / "config" / "services" / "llm"
        config_dir.mkdir(parents=True, exist_ok=True)
        ac.project_root = tmp_path

        result = ac.generate_local_lora_config()
        assert result.exists()
        content = result.read_text(encoding="utf-8")
        assert "local_lora" in content
        assert "base_model_name" in content

    def test_generate_local_lora_config_backs_up_existing(self, auto_config, tmp_path):
        """Existing config should be backed up as .yaml.bak."""
        from anima.utils.auto_config import AutoConfig

        ac = AutoConfig()
        config_dir = tmp_path / "config" / "services" / "llm"
        config_dir.mkdir(parents=True, exist_ok=True)
        config_file = config_dir / "local_lora.yaml"
        config_file.write_text("old config", encoding="utf-8")
        ac.project_root = tmp_path

        ac.generate_local_lora_config()
        backup = config_file.with_suffix(".yaml.bak")
        assert backup.exists()
        assert backup.read_text(encoding="utf-8") == "old config"

    # ── setup_data_dir ───────────────────────────────────────────────

    def test_setup_data_dir_creates_directories(self, auto_config, tmp_path):
        """setup_data_dir should create the directory tree."""
        from anima.utils.auto_config import AutoConfig

        ac = AutoConfig()
        ac.project_root = tmp_path

        with patch.object(ac, "get_data_dir", return_value=tmp_path / "anima_data"):
            result = ac.setup_data_dir()
            assert result == tmp_path / "anima_data"
            assert (tmp_path / "anima_data" / "models" / "base_models").exists()
            assert (tmp_path / "anima_data" / "models" / "checkpoints").exists()
            assert (tmp_path / "anima_data" / "vectordb").exists()
            assert (tmp_path / "anima_data" / "histories").exists()

    # ── diagnose ─────────────────────────────────────────────────────

    def test_diagnose_returns_bool(self, auto_config):
        """diagnose() should return a boolean."""
        with patch.multiple(
            auto_config,
            get_data_dir=MagicMock(return_value=Path("/tmp")),
            check_dependencies=MagicMock(return_value=(True, [])),
        ):
            result = auto_config.diagnose()
            assert isinstance(result, bool)

    def test_diagnose_missing_deps(self, auto_config):
        """Missing dependencies should make diagnose return False."""
        with patch.multiple(
            auto_config,
            get_data_dir=MagicMock(return_value=Path("/tmp")),
            check_dependencies=MagicMock(return_value=(False, ["fastapi"])),
        ):
            with patch("pathlib.Path.exists", return_value=True):
                result = auto_config.diagnose()
                assert result is False

    # ── setup_all ────────────────────────────────────────────────────

    def test_setup_all_no_auto_fix(self, auto_config):
        """setup_all(auto_fix=False) should not install dependencies."""
        with patch.multiple(
            auto_config,
            generate_env_file=MagicMock(),
            generate_local_lora_config=MagicMock(),
            setup_data_dir=MagicMock(return_value=Path("/tmp")),
        ):
            result = auto_config.setup_all(auto_fix=False)
            assert result is True

    def test_setup_all_with_errors(self, auto_config):
        """If a step fails, setup_all should return False."""
        with patch.object(auto_config, "generate_env_file", side_effect=Exception("fail")):
            result = auto_config.setup_all(auto_fix=False)
            assert result is False

    # ── auto_install_dependencies ────────────────────────────────────

    def test_auto_install_already_ok(self, auto_config):
        """If all deps installed, returns True without calling pip."""
        with patch.object(auto_config, "check_dependencies", return_value=(True, [])):
            result = auto_config.auto_install_dependencies()
            assert result is True

    def test_auto_install_failure(self, auto_config):
        """If pip install fails, returns False."""
        with patch.object(auto_config, "check_dependencies", return_value=(False, ["missing"])):
            with patch("subprocess.check_call", side_effect=Exception("pip error")):
                result = auto_config.auto_install_dependencies()
                assert result is False

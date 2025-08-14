import importlib
import json

import utils.security as security


def test_allowed_command_not_blocked():
    assert not security.is_blocked("echo hello")


def test_blocked_command_is_blocked():
    assert security.is_blocked("rm -rf /")


def test_load_config_from_file(monkeypatch, tmp_path):
    config = {"allowed": [r"^foo$"], "suspicious": [r"bar"]}
    cfg_path = tmp_path / "security.json"
    cfg_path.write_text(json.dumps(config), encoding="utf-8")
    monkeypatch.setenv("SECURITY_CONFIG_PATH", str(cfg_path))
    importlib.reload(security)
    try:
        assert not security.is_blocked("foo")
        assert security.is_blocked("echo hello")
    finally:
        monkeypatch.delenv("SECURITY_CONFIG_PATH", raising=False)
        importlib.reload(security)

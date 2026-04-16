import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from src.main import app
from src.core.assistant import Assistant, ModelManager
from src.utils.config import load_config


class DummyOllama:
    def __init__(self, *args, **kwargs):
        pass

    def get_available_models_sync(self):
        return [
            {"name": "deepseek-r1:7b", "size": 7},
            {"name": "gemma3:4b", "size": 4},
        ]


def test_load_config_returns_default_when_file_missing():
    config = load_config("nonexistent-config.yaml")

    assert config["app"]["name"] == "Bayesian-AGI-Core"
    assert config["server"]["port"] == 8000
    assert config["memory"]["directory"] == "memory"


def test_load_config_reads_yaml_file(tmp_path: Path):
    content = """
app:
  name: Test Agent
  version: 2.0.0
server:
  host: 127.0.0.1
  port: 5555
"""
    config_file = tmp_path / "config_test.yaml"
    config_file.write_text(content, encoding="utf-8")

    config = load_config(str(config_file))

    assert config["app"]["name"] == "Test Agent"
    assert config["server"]["port"] == 5555


def test_model_manager_loads_ollama_models(monkeypatch):
    monkeypatch.setattr("src.core.assistant.OllamaLLM", lambda *args, **kwargs: DummyOllama())

    config = {
        "models": {
            "default": "deepseek-r1:7b",
            "ollama_url": "http://localhost:11434",
            "providers": {
                "ollama": {
                    "enabled": True,
                    "models": ["deepseek-r1:7b"],
                },
                "openai": {
                    "enabled": False,
                    "models": ["gpt-3.5-turbo"],
                },
            },
        }
    }

    manager = ModelManager()
    manager.load_from_config(config)
    model_names = [model["name"] for model in manager.get_models()]

    assert "deepseek-r1:7b" in model_names
    assert "gemma3:4b" in model_names


def test_assistant_register_and_get_service():
    assistant = Assistant()
    assistant.register_service("test", {"status": "ok"})

    assert assistant.get_service("test") == {"status": "ok"}


def test_root_route_is_registered():
    root_routes = [route for route in app.routes if getattr(route, "path", None) == "/" and "GET" in getattr(route, "methods", [])]

    assert len(root_routes) == 1
    assert root_routes[0].name == "root"

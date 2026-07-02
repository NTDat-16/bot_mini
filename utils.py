import os
from pathlib import Path

from dotenv import load_dotenv


def load_environment():
    load_dotenv()


def ensure_env_var(name: str) -> str:
    load_environment()
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def optional_env_var(name: str) -> str | None:
    load_environment()
    return os.getenv(name)


def ensure_positive_int(value, name: str):
    if value is None:
        raise ValueError(f"{name} must be provided")
    try:
        value = int(value)
    except (TypeError, ValueError):
        raise ValueError(f"{name} must be an integer")
    if value <= 0:
        raise ValueError(f"{name} must be a positive integer")
    return value


def ensure_path_exists(path, name: str):
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"{name} does not exist: {path}")
    return path

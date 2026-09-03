"""Atomic updates for the vendored trendpipe credentials file."""

import os
import re
import tempfile

from app.services.research_engine import TRENDPIPE_DIR

ENV_PATH = os.path.join(TRENDPIPE_DIR, ".env")
_ENV_KEY_PATTERN = re.compile(r"^[A-Z_][A-Z0-9_]*$")
ALLOWED_CREDENTIAL_KEYS = frozenset(
    {
        "APIFY_API_TOKEN",
        "BRAVE_API_KEY",
        "EXA_API_KEY",
        "GEMINI_API_KEY",
        "GITHUB_TOKEN",
        "GOOGLE_API_KEY",
        "GOOGLE_GENAI_API_KEY",
        "GROQ_API_KEY",
        "OPENAI_API_KEY",
        "OPENROUTER_API_KEY",
        "PARALLEL_API_KEY",
        "PERPLEXITY_API_KEY",
        "SCRAPECREATORS_API_KEY",
        "SERPER_API_KEY",
        "XAI_API_KEY",
        "XQUIK_API_KEY",
    }
)


def _read_lines() -> list[str]:
    if os.path.exists(ENV_PATH):
        with open(ENV_PATH, "r", encoding="utf-8") as env_file:
            return env_file.readlines()
    return []


def _atomic_write(lines: list[str]) -> None:
    env_dir = os.path.dirname(ENV_PATH)
    os.makedirs(env_dir, exist_ok=True)
    file_descriptor, temp_path = tempfile.mkstemp(dir=env_dir)
    try:
        with os.fdopen(file_descriptor, "w", encoding="utf-8") as temp_file:
            temp_file.writelines(lines)
            temp_file.flush()
            os.fsync(temp_file.fileno())
        os.chmod(temp_path, 0o600)
        os.replace(temp_path, ENV_PATH)
        os.chmod(ENV_PATH, 0o600)
    except Exception:
        if os.path.exists(temp_path):
            os.remove(temp_path)
        raise


def _parse_env_line(line: str) -> tuple[str, str] | None:
    stripped = line.strip()
    if not stripped or stripped.startswith("#") or "=" not in stripped:
        return None
    key, _, value = stripped.partition("=")
    return key.strip(), value


def write_credentials(values: dict[str, str]) -> None:
    """Replace submitted keys while preserving unrelated ``.env`` content."""
    for key, value in values.items():
        if not _ENV_KEY_PATTERN.fullmatch(key):
            raise ValueError(f"invalid credential key: {key}")
        if key not in ALLOWED_CREDENTIAL_KEYS:
            raise ValueError(f"unsupported credential key: {key}")
        if "\n" in value or "\r" in value:
            raise ValueError(f"credential value for {key} contains a newline")

    updated_keys = set(values)
    kept_lines: list[str] = []
    for line in _read_lines():
        parsed = _parse_env_line(line)
        if parsed is None or parsed[0] not in updated_keys:
            kept_lines.append(line)

    if kept_lines and not kept_lines[-1].endswith("\n"):
        kept_lines[-1] += "\n"
    new_lines = kept_lines + [f"{key}={value}\n" for key, value in values.items()]
    _atomic_write(new_lines)


def delete_credential(key: str) -> None:
    """Remove a single credential from the ``.env`` file, if present."""
    if key not in ALLOWED_CREDENTIAL_KEYS:
        raise ValueError(f"unsupported credential key: {key}")

    kept_lines = [
        line
        for line in _read_lines()
        if (parsed := _parse_env_line(line)) is None or parsed[0] != key
    ]
    _atomic_write(kept_lines)


def credential_presence() -> dict[str, bool]:
    """Report which allowed credential keys currently have a non-empty value."""
    values = dict(filter(None, (_parse_env_line(line) for line in _read_lines())))
    return {key: bool(values.get(key)) for key in ALLOWED_CREDENTIAL_KEYS}


def read_env_file() -> dict[str, str]:
    """Return every key/value pair in the ``.env`` file, unfiltered.

    Unlike ``credential_presence``, this isn't scoped to
    ``ALLOWED_CREDENTIAL_KEYS`` — the file also holds non-credential engine
    settings (e.g. ``TRENDPIPE_REASONING_PROVIDER``) that callers need too.
    """
    return dict(filter(None, (_parse_env_line(line) for line in _read_lines())))

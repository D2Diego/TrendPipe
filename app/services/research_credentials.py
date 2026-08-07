"""Atomic updates for the vendored last30days credentials file."""

import os
import re
import tempfile

from app.services.research_engine import LAST30DAYS_DIR

ENV_PATH = os.path.join(LAST30DAYS_DIR, ".env")
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


def write_credentials(values: dict[str, str]) -> None:
    """Replace submitted keys while preserving unrelated ``.env`` content."""
    for key, value in values.items():
        if not _ENV_KEY_PATTERN.fullmatch(key):
            raise ValueError(f"invalid credential key: {key}")
        if key not in ALLOWED_CREDENTIAL_KEYS:
            raise ValueError(f"unsupported credential key: {key}")
        if "\n" in value or "\r" in value:
            raise ValueError(f"credential value for {key} contains a newline")

    existing_lines: list[str] = []
    if os.path.exists(ENV_PATH):
        with open(ENV_PATH, "r", encoding="utf-8") as env_file:
            existing_lines = env_file.readlines()

    updated_keys = set(values)
    kept_lines: list[str] = []
    for line in existing_lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            kept_lines.append(line)
            continue
        key = stripped.split("=", 1)[0].strip()
        if key not in updated_keys:
            kept_lines.append(line)

    if kept_lines and not kept_lines[-1].endswith("\n"):
        kept_lines[-1] += "\n"
    new_lines = kept_lines + [f"{key}={value}\n" for key, value in values.items()]

    env_dir = os.path.dirname(ENV_PATH)
    os.makedirs(env_dir, exist_ok=True)
    file_descriptor, temp_path = tempfile.mkstemp(dir=env_dir)
    try:
        with os.fdopen(file_descriptor, "w", encoding="utf-8") as temp_file:
            temp_file.writelines(new_lines)
            temp_file.flush()
            os.fsync(temp_file.fileno())
        os.chmod(temp_path, 0o600)
        os.replace(temp_path, ENV_PATH)
        os.chmod(ENV_PATH, 0o600)
    except Exception:
        if os.path.exists(temp_path):
            os.remove(temp_path)
        raise

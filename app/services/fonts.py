import os

from app.services import video
from app.utils import utils

SUPPORTED_FONT_EXTENSIONS = (".ttf", ".ttc")


def list_fonts() -> list[str]:
    """Return the font filenames available to the generation pipeline."""
    directory = utils.font_dir()
    return sorted(
        filename
        for filename in os.listdir(directory)
        if os.path.isfile(os.path.join(directory, filename))
        and filename.lower().endswith(SUPPORTED_FONT_EXTENSIONS)
    )


def supports_text(font_name: str, text: str) -> bool:
    """Check glyph coverage for a known server-side font without accepting paths."""
    if font_name not in list_fonts():
        raise ValueError("unknown subtitle font")
    return video.subtitle_font_supports_text(utils.font_dir(font_name), text)

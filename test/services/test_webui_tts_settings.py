import json
from pathlib import Path
from unittest.mock import patch

from streamlit.testing.v1 import AppTest

from app.config import config
from app.services import voice


ROOT_DIR = Path(__file__).parent.parent.parent
WEBUI_MAIN = ROOT_DIR / "webui" / "Main.py"
I18N_DIR = ROOT_DIR / "webui" / "i18n"
LOCALES = ("de", "en", "es", "id", "pt", "ru", "tr", "vi", "zh")

# Each service provider maintains only one official entrance.Chatterbox It's self-care, no uniform. Key
# Retrieve the platform and therefore link to the actual compatible service configuration statement to avoid misleading users to register third-party accounts.
TTS_API_KEY_LABELS = {
    "Speech Key": "portal.azure.com",
    "SiliconFlow API Key": "cloud.siliconflow.cn/account/ak",
    "Gemini API Key": "aistudio.google.com/app/apikey",
    "MiMo API Key": "mimo.mi.com/docs/",
    "ElevenLabs API Key": "elevenlabs.io/app/settings/api-keys",
    "Chatterbox API Key": "github.com/travisvn/chatterbox-tts-api",
}

TTS_PROVIDER_WIDGETS = {
    "azure-tts-v2": ("azure_speech_key_input", "Speech Key"),
    "siliconflow": ("siliconflow_api_key_input", "SiliconFlow API Key"),
    "gemini-tts": ("gemini_tts_api_key_input", "Gemini API Key"),
    "mimo-tts": ("mimo_tts_api_key_input", "MiMo API Key"),
    "elevenlabs": ("elevenlabs_api_key_input", "ElevenLabs API Key"),
    "chatterbox": ("chatterbox_api_key_input", "Chatterbox API Key"),
}


def _load_translation(locale: str) -> dict:
    """Read the language file directly to ensure that the assertion covers the end of what the user actually sees Markdown Label."""
    data = json.loads((I18N_DIR / f"{locale}.json").read_text(encoding="utf-8"))
    return data["Translation"]


def _widget_by_key(elements, key: str):
    """Streamlit Control labels translate, use steady operations key Positions the real input box."""
    return next(
        item
        for item in elements
        if str(getattr(item, "key", "")) == key
        or str(getattr(item, "key", "")).startswith(f"{key}_")
    )


def test_all_tts_api_key_labels_include_an_official_configuration_link():
    """The name of the service provider and the clickable entry should be maintained in all languages to avoid loss of links in translation."""
    for locale in LOCALES:
        translations = _load_translation(locale)
        for label_key, expected_host in TTS_API_KEY_LABELS.items():
            label = translations[label_key]
            assert expected_host in label, f"{locale}: {label_key}"
            assert "](" in label, f"{locale}: {label_key}"


def test_tts_provider_inputs_render_the_standardized_labels():
    """Practically Switch Every TTS Provider，Confirms that the input box does not bypass the uniform translation label."""
    test_ui = dict(
        config.ui,
        voice_mode="tts",
        tts_server="azure-tts-v1",
        voice_name="",
    )
    translations = _load_translation("zh")

    with (
        patch.object(config, "ui", test_ui),
        patch.object(config, "save_config"),
        patch.object(voice, "get_all_azure_voices", return_value=[]),
        patch.object(voice, "get_siliconflow_voices", return_value=[]),
        patch.object(voice, "get_gemini_voices", return_value=[]),
        patch.object(voice, "get_mimo_voices", return_value=[]),
        patch.object(voice, "get_elevenlabs_voices", return_value=[]),
        patch.object(voice, "get_chatterbox_voices", return_value=[]),
    ):
        app = AppTest.from_file(str(WEBUI_MAIN), default_timeout=30)
        app.session_state["ui_language"] = "zh"
        app.run()

        for provider, (widget_key, label_key) in TTS_PROVIDER_WIDGETS.items():
            provider_select = _widget_by_key(app.selectbox, "tts_server_select")
            provider_select.set_value(provider).run()

            api_key_input = _widget_by_key(app.text_input, widget_key)
            assert api_key_input.label == translations[label_key]
            assert api_key_input.proto.type == api_key_input.proto.PASSWORD
            assert not getattr(api_key_input.proto, "help", "")

    assert [str(item.value) for item in app.exception] == []

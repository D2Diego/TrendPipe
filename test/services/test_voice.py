import asyncio
import base64
import os
import shutil
import unittest
import sys
import tempfile
import time
from datetime import timedelta
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

# add project root to python path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.utils import utils
from app.services import voice as vs
from app.services import task as task_service
from pydub import AudioSegment

temp_dir = utils.storage_dir("temp")

text_en = """
What is the meaning of life?
This question has puzzled philosophers, scientists, and thinkers of all kinds for centuries.
Throughout history, various cultures and individuals have come up with their interpretations and beliefs around the purpose of life.
Some say it's to seek happiness and self-fulfillment, while others believe it's about contributing to the welfare of others and making a positive impact in the world.
Despite the myriad of perspectives, one thing remains clear: the meaning of life is a deeply personal concept that varies from one person to another.
It's an existential inquiry that encourages us to reflect on our values, desires, and the essence of our existence.
"""

text_zh = """
Projected future 3 Cold air activity is high in Shenzhen, with light rain going on in the next two days, and good rain tools going out;
10-11 Days and suns have rain, temperatures are low and temperatures are high.13-17℃In between, the body is cold;
12(a) A brief improvement in the weather and early and cold;
"""

voice_rate=1.0
voice_volume=1.0
RUN_INTEGRATION_TESTS = os.environ.get("MPT_RUN_INTEGRATION_TESTS", "").lower() in {
    "1",
    "true",
    "yes",
}

class TestVoiceService(unittest.TestCase):
    def setUp(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

    def tearDown(self):
        self.loop.close()

    def test_get_all_azure_voices(self):
        voices = vs.get_all_azure_voices()
        # Data moved from inline string to azure_voices.json，Make sure it's still fully loaded.
        self.assertEqual(len(voices), 331)
        # The result should read "Name-Gender" Formatted and Sorted
        self.assertEqual(voices, sorted(voices))
        for v in voices:
            self.assertTrue(v.endswith("-Male") or v.endswith("-Female"))

    def test_get_all_azure_voices_filtered(self):
        filtered = vs.get_all_azure_voices(filter_locals=["zh-CN", "en-US"])
        self.assertTrue(len(filtered) > 0)
        self.assertTrue(
            all(v.startswith(("zh-CN", "en-US")) for v in filtered)
        )

    def test_no_voice_tts_generates_silent_audio_and_subtitle_timeline(self):
        """
        No voice mode without calling any externals TTS provider，Only silent audio is generated as a time axis.
        Here. mock FFmpeg，Validate request parameters, output files legacy Subtitles are structured to follow.
        Video synthesis link expected.
        """

        def fake_run(command, capture_output, text, check):
            self.assertEqual(command[0], "/tmp/fake-ffmpeg")
            self.assertIn("anullsrc=r=44100:cl=mono", command)
            Path(command[-1]).write_bytes(b"fake-silent-mp3")
            return SimpleNamespace(returncode=0, stdout="", stderr="")

        with tempfile.TemporaryDirectory() as tmp_dir, patch.object(
            vs.utils,
            "get_ffmpeg_binary",
            return_value="/tmp/fake-ffmpeg",
        ), patch.object(vs.subprocess, "run", side_effect=fake_run):
            voice_file = str(Path(tmp_dir) / "silent.mp3")
            sub_maker = vs.tts(
                text="First sentence.Second sentence.",
                voice_name=vs.NO_VOICE_NAME,
                voice_rate=1.0,
                voice_file=voice_file,
            )

            self.assertEqual(Path(voice_file).read_bytes(), b"fake-silent-mp3")

        self.assertIsNotNone(sub_maker)
        self.assertEqual(getattr(sub_maker, "subs", []), ["First sentence", "Second sentence"])
        self.assertEqual(len(getattr(sub_maker, "offset", [])), 2)
        self.assertGreater(vs.get_audio_duration(sub_maker), 0)

    def test_get_audio_duration_accepts_non_mp3_files(self):
        """
        Custom Audio custom_audio_file）Commonly m4a/wav/aac Wait! mp3 format.
        get_audio_duration The extension should not be .mp3 Report. "Invalid target type" And back 0，
        And it should be delivered. moviepy(ffmpeg) Read the real time.
        """
        for path in ("custom-audio.m4a", "voice.wav", "clip.aac"):
            with patch.object(vs.os.path, "exists", return_value=True), \
                    patch.object(vs, "AudioFileClip") as mock_afc:
                mock_afc.return_value.__enter__.return_value.duration = 28.89
                self.assertEqual(vs.get_audio_duration(path), 28.89)
                mock_afc.assert_called_once_with(path)

    def test_get_audio_duration_missing_file_returns_zero(self):
        """Return safely when audio files do not exist 0，Not to throw an anomaly or read a failure."""
        with patch.object(vs.os.path, "exists", return_value=False):
            self.assertEqual(vs.get_audio_duration("does-not-exist.m4a"), 0.0)

    def test_no_voice_alias_none_is_supported_temporarily(self):
        """
        Compatibility PR #981 Used none sentinel，Avoid a few direct calls API Other Organiser
        The upgrade will expire immediately. New UI Still using the new code. no-voice。
        """
        self.assertTrue(vs.is_no_voice("none"))
        self.assertTrue(vs.is_no_voice(vs.NO_VOICE_NAME))
        self.assertFalse(vs.is_no_voice(""))

    def test_no_voice_duration_estimates_non_ascii_languages(self):
        """
        No voice, no truth. TTS Audio, which can only be estimated on the basis of script text. Russian, Arabic,
        Japanese pseudonyms, Korean, etc. ASCII Texts must also be used to estimate, not all of which are short. 3 sec.
        """
        russian_text = (
            "Это длинный тестовый сценарий без озвучки. "
            "Он должен получить достаточно времени для чтения субтитров."
        )
        arabic_text = "هذا اختبار طويل بدون تعليق صوتي، ويجب أن يحصل على وقت كاف لقراءة الترجمة."

        self.assertGreater(vs.estimate_no_voice_duration(russian_text), 8.0)
        self.assertGreater(vs.estimate_no_voice_duration(arabic_text), 8.0)

    def test_generate_silent_audio_rejects_missing_output_file(self):
        """
        Even FFmpeg The process is successful and the output document is confirmed to be real and non-empty. That'll do.
        It's not normal. TTS The stage, not the subsequent video synthesis phase, is exposed.
        """
        with tempfile.TemporaryDirectory() as tmp_dir, patch.object(
            vs.utils,
            "get_ffmpeg_binary",
            return_value="/tmp/fake-ffmpeg",
        ), patch.object(
            vs.subprocess,
            "run",
            return_value=SimpleNamespace(returncode=0, stdout="", stderr=""),
        ):
            voice_file = str(Path(tmp_dir) / "missing-silent.mp3")

            self.assertFalse(vs.generate_silent_audio(3.0, voice_file))

    def test_empty_voice_name_does_not_enable_no_voice_mode(self):
        """
        Empty voice Usually means that the configuration is missing or the interface parameter is wrong and cannot automatically cut to a voiceless mode.
        Other Organiser TTS The configuration also provides a "successful" silent video, with higher positioning costs.
        """
        sentinel = object()

        with patch.object(vs, "azure_tts_v1", return_value=sentinel) as azure_tts_v1:
            result = vs.tts(
                text="empty voice should still use the default TTS path",
                voice_name="",
                voice_rate=1.0,
                voice_file="/tmp/empty-voice.mp3",
            )

        self.assertIs(result, sentinel)
        azure_tts_v1.assert_called_once()

    @unittest.skipUnless(
        RUN_INTEGRATION_TESTS,
        "MPT_RUN_INTEGRATION_TESTS not set",
    )
    def test_siliconflow(self):
        # SiliconFlow Yes. API Key Existence [siliconflow].api_key , runtime code from
        # config.siliconflow Read; here must be the same configuration source to avoid the correct configuration
        # The tests were still missed.
        if not vs.config.siliconflow.get("api_key"):
            self.skipTest("siliconflow_api_key is not configured")

        voice_name = "siliconflow:FunAudioLLM/CosyVoice2-0.5B:alex-Male"
        voice_name = vs.parse_voice_name(voice_name)

        async def _do():
            parts = voice_name.split(":")
            if len(parts) >= 3:
                model = parts[1]
                # Remove gender suffix, e.g. "alex-Male" -> "alex"
                voice_with_gender = parts[2]
                voice = voice_with_gender.split("-")[0]
                # Build Full voice Parameters, format as "model:voice"
                full_voice = f"{model}:{voice}"
                voice_file = f"{temp_dir}/tts-siliconflow-{voice}.mp3"
                subtitle_file = f"{temp_dir}/tts-siliconflow-{voice}.srt"
                sub_maker = vs.siliconflow_tts(
                    text=text_zh, model=model, voice=full_voice, voice_file=voice_file, voice_rate=voice_rate, voice_volume=voice_volume
                )
                if not sub_maker:
                    self.fail("siliconflow tts failed")
                vs.create_subtitle(sub_maker=sub_maker, text=text_zh, subtitle_file=subtitle_file)
                audio_duration = vs.get_audio_duration(sub_maker)
                print(f"voice: {voice_name}, audio duration: {audio_duration}s")
            else:
                self.fail("siliconflow invalid voice name")

        self.loop.run_until_complete(_do())

    @unittest.skipUnless(
        RUN_INTEGRATION_TESTS,
        "MPT_RUN_INTEGRATION_TESTS not set",
    )
    def test_azure_tts_v1(self):
        voice_name = "zh-CN-XiaoyiNeural-Female"
        voice_name = vs.parse_voice_name(voice_name)
        print(voice_name)

        voice_file = f"{temp_dir}/tts-azure-v1-{voice_name}.mp3"
        subtitle_file = f"{temp_dir}/tts-azure-v1-{voice_name}.srt"
        sub_maker = vs.azure_tts_v1(
            text=text_zh, voice_name=voice_name, voice_file=voice_file, voice_rate=voice_rate
        )
        if not sub_maker:
            self.fail("azure tts v1 failed")
        vs.create_subtitle(sub_maker=sub_maker, text=text_zh, subtitle_file=subtitle_file)
        audio_duration = vs.get_audio_duration(sub_maker)
        print(f"voice: {voice_name}, audio duration: {audio_duration}s")

    def test_azure_tts_v1_supports_legacy_edge_tts_without_boundary(self):
        """
        Authentication Azure TTS V1 In the old version. edge_tts Work could continue when relying on residuals.

        This is the same scene. Windows After the package upgrade failed, the scene was still in the old version.
        edge_tts Situation:
        1. `Communicate.__init__()` Not accepted `boundary`
        2. It's just a walk. `stream()`，Nothing. `stream_sync()`
        """

        class _LegacyCommunicate:
            def __init__(self, text, voice, rate="+0%"):
                self.text = text
                self.voice = voice
                self.rate = rate

            async def stream(self):
                yield {"type": "audio", "data": b"legacy-audio"}
                yield {
                    "type": "WordBoundary",
                    "offset": 0,
                    "duration": 10000000,
                    "text": "legacy",
                }

        class _FakeSubMaker:
            def __init__(self):
                self.events = []

            def feed(self, chunk):
                self.events.append(chunk)

            def get_srt(self):
                if not self.events:
                    return ""
                return "1\n00:00:00,000 --> 00:00:01,000\nlegacy\n"

        with tempfile.TemporaryDirectory() as tmp_dir, patch.object(
            vs.edge_tts, "Communicate", _LegacyCommunicate
        ), patch.object(vs.edge_tts, "SubMaker", _FakeSubMaker):
            voice_file = str(Path(tmp_dir) / "legacy-edge-tts.mp3")
            sub_maker = vs.azure_tts_v1(
                text="legacy edge tts compatibility",
                voice_name="zh-CN-XiaoyiNeural-Female",
                voice_file=voice_file,
                voice_rate=1.0,
            )

            self.assertIsNotNone(sub_maker)
            self.assertEqual(Path(voice_file).read_bytes(), b"legacy-audio")
            self.assertEqual(len(sub_maker.events), 1)
            self.assertEqual(sub_maker.events[0]["type"], "WordBoundary")

    def test_azure_tts_v1_times_out_hanging_stream_sync(self):
        """
        Authentication Azure TTS V1 Yes. edge_tts Synchronized stream can quickly fail when stuck.

        On the real scene, network anomalies, service restrictions,voice If the language does not match the text, it will not be possible.
        `stream_sync()` Possible prolonged non-return, resulting in WebUI The mission has been stopped.
        `start, voice name...`。It's blocked here. fake stream It's the same thing.
        Confirm that overtime protection ends and returns the function None。
        """

        class _HangingCommunicate:
            def __init__(self, text, voice, rate="+0%", boundary=None):
                self.text = text
                self.voice = voice
                self.rate = rate
                self.boundary = boundary

            def stream_sync(self):
                time.sleep(10)
                yield {"type": "audio", "data": b"unreachable"}

        class _FakeSubMaker:
            def feed(self, chunk):
                return None

            def get_srt(self):
                return ""

        with tempfile.TemporaryDirectory() as tmp_dir, patch.object(
            vs.edge_tts, "Communicate", _HangingCommunicate
        ), patch.object(vs.edge_tts, "SubMaker", _FakeSubMaker), patch.object(
            vs.config,
            "app",
            dict(vs.config.app, edge_tts_timeout=0.05),
        ):
            voice_file = Path(tmp_dir) / "hanging-edge-tts.mp3"
            started_at = time.monotonic()
            sub_maker = vs.azure_tts_v1(
                text="Help me create a flowering video.",
                voice_name="en-AU-NatashaNeural-Female",
                voice_file=str(voice_file),
                voice_rate=1.0,
            )
            elapsed = time.monotonic() - started_at
            self.assertFalse(voice_file.exists())

        self.assertIsNone(sub_maker)
        self.assertLess(elapsed, 2)

    @unittest.skipUnless(
        RUN_INTEGRATION_TESTS,
        "MPT_RUN_INTEGRATION_TESTS not set",
    )
    def test_azure_tts_v2(self):
        if not vs.config.azure.get("speech_key") or not vs.config.azure.get("speech_region"):
            self.skipTest("Azure speech key or region is not configured")

        voice_name = "zh-CN-XiaoxiaoMultilingualNeural-V2-Female"
        voice_name = vs.parse_voice_name(voice_name)
        print(voice_name)

        async def _do():
            voice_file = f"{temp_dir}/tts-azure-v2-{voice_name}.mp3"
            subtitle_file = f"{temp_dir}/tts-azure-v2-{voice_name}.srt"
            sub_maker = vs.azure_tts_v2(
                text=text_zh,
                voice_name=voice_name,
                voice_file=voice_file,
                voice_rate=1.0,
            )
            if not sub_maker:
                self.fail("azure tts v2 failed")
            vs.create_subtitle(sub_maker=sub_maker, text=text_zh, subtitle_file=subtitle_file)
            audio_duration = vs.get_audio_duration(sub_maker)
            print(f"voice: {voice_name}, audio duration: {audio_duration}s")

        self.loop.run_until_complete(_do())

    def test_azure_tts_v2_ssml_applies_rate_and_escapes_text(self):
        """Azure V2 It must be passed. SSML Use of terms quickly and avoid destruction of user files XML。"""
        ssml = vs._build_azure_v2_ssml(
            text='A < B & "quoted"',
            voice_name="zh-CN-XiaoxiaoMultilingualNeural",
            voice_rate=1.8,
        )

        self.assertIn('xml:lang="zh-CN"', ssml)
        self.assertIn('rate="1.8"', ssml)
        self.assertIn("A &lt; B &amp; \"quoted\"", ssml)

    def test_tts_forwards_rate_to_azure_v2(self):
        """Harmonization TTS The entrance cannot be distributed. Azure V2 Time lost voice_rate。"""
        voice_name = "zh-CN-XiaoxiaoMultilingualNeural-V2-Female"
        with patch.object(vs, "azure_tts_v2", return_value=object()) as mock_tts:
            result = vs.tts(
                text="Speed Test",
                voice_name=voice_name,
                voice_rate=1.8,
                voice_file="/tmp/azure-v2-rate.mp3",
            )

        self.assertIsNotNone(result)
        mock_tts.assert_called_once_with(
            "Speed Test",
            voice_name,
            "/tmp/azure-v2-rate.mp3",
            voice_rate=1.8,
        )

    def test_gemini_tts_uses_google_genai_and_compatible_submaker_fields(self):
        """
        Authentication Gemini TTS Yes. edge_tts 7.x The project's subtitling structure is still in place in the environment.
        And can be... `subtitle_provider=edge` It's a direct consumption of subtitles.
        Avoid retreating again Whisper。Use also non-existent embedded output directories, overwrite API or
        CLI Borders that do not create task catalogues in advance when directly calling.
        """

        class _InlineData:
            def __init__(self, data):
                self.data = data

        class _Part:
            def __init__(self, data):
                self.inline_data = _InlineData(data)

        class _Content:
            def __init__(self, data):
                self.parts = [_Part(data)]

        class _Candidate:
            def __init__(self, data):
                self.content = _Content(data)

        class _Response:
            def __init__(self, data):
                self.candidates = [_Candidate(data)]

        captured = {}

        class _FakeModels:
            def generate_content(self, **kwargs):
                captured.update(kwargs)
                tone = (
                    AudioSegment.silent(duration=1800)
                    .set_frame_rate(24000)
                    .set_channels(1)
                    .set_sample_width(2)
                )
                return _Response(tone.raw_data)

        class _FakeClient:
            def __init__(self, **kwargs):
                captured["client_kwargs"] = kwargs
                self.models = _FakeModels()

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc_value, traceback):
                captured["closed"] = True

        temp_root = Path(tempfile.mkdtemp(prefix="gemini-tts-output-"))
        self.addCleanup(shutil.rmtree, temp_root, True)
        output_dir = temp_root / "nested" / "audio"
        voice_file = str(output_dir / "tts-gemini-Zephyr.mp3")
        subtitle_file = str(output_dir / "tts-gemini-Zephyr.srt")
        text = "Gemini subtitle generation should work now. Testing multiple lines."

        self.assertFalse(output_dir.exists())

        with patch("google.genai.Client", _FakeClient), patch.object(
            vs.config,
            "app",
            dict(vs.config.app, gemini_api_key="test-key"),
        ):
            sub_maker = vs.gemini_tts(
                text=text,
                voice_name="Zephyr",
                voice_rate=1.0,
                voice_file=voice_file,
            )

        self.assertIsNotNone(sub_maker)
        self.assertTrue(Path(voice_file).is_file())
        self.assertEqual(
            getattr(sub_maker, "subs", []),
            ["Gemini subtitle generation should work now", "Testing multiple lines"],
        )
        self.assertEqual(len(getattr(sub_maker, "offset", [])), 2)
        self.assertEqual(sub_maker.offset[0][0], 0)
        self.assertLess(sub_maker.offset[0][1], sub_maker.offset[1][1])
        self.assertEqual(captured["client_kwargs"], {"api_key": "test-key"})
        self.assertEqual(captured["model"], "gemini-2.5-flash-preview-tts")
        self.assertEqual(captured["contents"], text)
        self.assertEqual(captured["config"].response_modalities, ["AUDIO"])
        voice_config = captured["config"].speech_config.voice_config
        self.assertEqual(
            voice_config.prebuilt_voice_config.voice_name,
            "Zephyr",
        )
        self.assertTrue(captured["closed"])

        vs.create_subtitle(sub_maker=sub_maker, text=text, subtitle_file=subtitle_file)
        subtitle_content = Path(subtitle_file).read_text(encoding="utf-8")
        self.assertIn("Gemini subtitle generation should work now", subtitle_content)
        self.assertIn("Testing multiple lines", subtitle_content)

    def test_mimo_tts_uses_openai_compatible_audio_response(self):
        """
        Authentication Xiaomi MiMo TTS It can be consumed. OpenAI-compatible The audio response structure.

        Here. fake OpenAI client and fake AudioSegment Overwrite Real Network with ffmpeg，
        Confirms that running time code will put the text to be synthesized assistant message，And they're going back.
        base64 WAV Audio is exported to the audio file used in the project follow-up process.
        """

        class _FakeAudio:
            def __init__(self):
                self.data = base64.b64encode(b"RIFF-fake-wav").decode("utf-8")

        class _FakeMessage:
            def __init__(self):
                self.audio = _FakeAudio()

        class _FakeChoice:
            def __init__(self):
                self.message = _FakeMessage()

        class _FakeCompletion:
            def __init__(self):
                self.choices = [_FakeChoice()]

        class _FakeCompletions:
            def create(self, **kwargs):
                self.kwargs = kwargs
                return _FakeCompletion()

        class _FakeAudioSegment:
            def __len__(self):
                return 1800

            def export(self, output_file, format):
                Path(output_file).write_bytes(b"fake-mp3")

        fake_completions = _FakeCompletions()
        fake_client = SimpleNamespace(
            chat=SimpleNamespace(completions=fake_completions)
        )

        with tempfile.TemporaryDirectory() as tmp_dir, patch.object(
            vs,
            "OpenAI",
            return_value=fake_client,
        ) as openai_client, patch(
            "pydub.AudioSegment.from_file",
            return_value=_FakeAudioSegment(),
        ), patch.object(
            vs.config,
            "app",
            dict(
                vs.config.app,
                mimo_api_key="mimo-key",
                mimo_base_url="https://api.xiaomimimo.com/v1",
                mimo_tts_model_name="mimo-v2.5-tts",
                mimo_tts_style_prompt="Read it in plain Chinese.",
            ),
        ):
            voice_file = str(Path(tmp_dir) / "mimo-tts.mp3")
            sub_maker = vs.mimo_tts(
                text="Mi speech synthesis test. The second sentence.",
                voice_name="\u51b0\u7cd6",
                voice_rate=1.0,
                voice_file=voice_file,
                voice_volume=1.0,
            )
            generated_audio = Path(voice_file).read_bytes()

        openai_client.assert_called_once_with(
            api_key="mimo-key",
            base_url="https://api.xiaomimimo.com/v1",
        )
        self.assertEqual(fake_completions.kwargs["model"], "mimo-v2.5-tts")
        self.assertEqual(
            fake_completions.kwargs["messages"],
            [
                {"role": "user", "content": "Read it in plain Chinese."},
                {"role": "assistant", "content": "Mi speech synthesis test. The second sentence."},
            ],
        )
        self.assertEqual(
            fake_completions.kwargs["audio"],
            {"format": "wav", "voice": "\u51b0\u7cd6"},
        )
        self.assertEqual(generated_audio, b"fake-mp3")
        self.assertIsNotNone(sub_maker)
        self.assertEqual(getattr(sub_maker, "subs", []), ["Mi speech synthesis test", "Second sentence"])
        self.assertEqual(len(getattr(sub_maker, "offset", [])), 2)

    def test_mimo_voice_labels_are_english_and_map_to_provider_ids(self):
        voices = vs.get_mimo_voices()

        self.assertIn("mimo:Rock Sugar-Female", voices)
        self.assertIn("mimo:White Birch-Male", voices)
        with patch.object(vs, "mimo_tts", return_value="subtitle") as mimo_tts:
            result = vs.tts(
                text="Voice mapping test.",
                voice_name="mimo:Rock Sugar-Female",
                voice_rate=1.0,
                voice_file="voice.mp3",
                voice_volume=1.0,
            )

        self.assertEqual(result, "subtitle")
        mimo_tts.assert_called_once_with(
            "Voice mapping test.",
            "\u51b0\u7cd6",
            1.0,
            "voice.mp3",
            1.0,
        )

    def test_chatterbox_voice_helpers(self):
        """is_chatterbox_voice / get_chatterbox_voices basics and normalisation."""
        self.assertTrue(vs.is_chatterbox_voice("chatterbox:default-Female"))
        self.assertFalse(vs.is_chatterbox_voice("elevenlabs:abc:Rachel"))
        self.assertFalse(vs.is_chatterbox_voice(""))
        self.assertFalse(vs.is_chatterbox_voice(None))

        # list entries are normalised to the chatterbox:<name> dispatcher format,
        # and entries that are already prefixed are left untouched
        with patch.object(
            vs.config,
            "chatterbox",
            {"voices": ["narrator-Male", "chatterbox:host"]},
        ):
            self.assertEqual(
                vs.get_chatterbox_voices(),
                ["chatterbox:narrator-Male", "chatterbox:host"],
            )

        # a comma-separated string is also accepted (TOML-friendly)
        with patch.object(vs.config, "chatterbox", {"voices": "alpha, beta ,"}):
            self.assertEqual(
                vs.get_chatterbox_voices(),
                ["chatterbox:alpha", "chatterbox:beta"],
            )

        # with nothing configured the dropdown still gets a usable default
        with patch.object(vs.config, "chatterbox", {}):
            self.assertEqual(vs.get_chatterbox_voices(), ["chatterbox:default-Female"])

    def test_chatterbox_tts_posts_to_openai_compatible_endpoint(self):
        """Success path: POST /audio/speech, write audio, return legacy SubMaker."""

        class _FakeResponse:
            status_code = 200
            content = b"RIFF-fake-wav"
            text = ""

        class _FakeClip:
            duration = 3.5

            def close(self):
                pass

        captured = {}

        def _fake_post(url, json=None, headers=None, timeout=None):
            captured["url"] = url
            captured["json"] = json
            captured["headers"] = headers
            return _FakeResponse()

        with tempfile.TemporaryDirectory() as tmp_dir, patch.object(
            vs.config,
            "chatterbox",
            {
                "base_url": "http://localhost:4123/v1/",
                "api_key": "secret",
                "model_id": "chatterbox",
            },
        ), patch.object(
            vs.requests, "post", side_effect=_fake_post
        ) as post, patch.object(
            vs, "AudioFileClip", return_value=_FakeClip()
        ):
            voice_file = str(Path(tmp_dir) / "chatterbox.mp3")
            sub_maker = vs.chatterbox_tts(
                text="Hello world. Second sentence.",
                voice="default",
                voice_file=voice_file,
                voice_rate=1.2,
                voice_volume=1.0,
            )
            generated_audio = Path(voice_file).read_bytes()

        post.assert_called_once()
        # trailing slash on base_url is stripped before appending /audio/speech
        self.assertEqual(captured["url"], "http://localhost:4123/v1/audio/speech")
        self.assertEqual(captured["json"]["model"], "chatterbox")
        self.assertEqual(captured["json"]["voice"], "default")
        self.assertEqual(captured["json"]["input"], "Hello world. Second sentence.")
        self.assertAlmostEqual(captured["json"]["speed"], 1.2)
        # api_key is forwarded as a bearer token
        self.assertEqual(captured["headers"].get("Authorization"), "Bearer secret")
        # volume is intentionally not part of the OpenAI speech payload
        self.assertNotIn("volume", captured["json"])
        self.assertEqual(generated_audio, b"RIFF-fake-wav")
        self.assertIsNotNone(sub_maker)
        self.assertTrue(getattr(sub_maker, "subs", []))

    def test_chatterbox_tts_requires_base_url(self):
        """Missing base_url short-circuits without any network call."""
        with patch.object(
            vs.config, "chatterbox", {"base_url": ""}
        ), patch.object(vs.requests, "post") as post:
            result = vs.chatterbox_tts(
                text="hi", voice="default", voice_file="unused.mp3"
            )
        self.assertIsNone(result)
        post.assert_not_called()

    def test_chatterbox_tts_returns_none_on_http_error(self):
        """A non-200 response is retried up to 3 times, then fails to None."""

        class _FakeResponse:
            status_code = 500
            content = b""
            text = "boom"

        with tempfile.TemporaryDirectory() as tmp_dir, patch.object(
            vs.config, "chatterbox", {"base_url": "http://localhost:4123/v1"}
        ), patch.object(
            vs.requests, "post", return_value=_FakeResponse()
        ) as post:
            voice_file = str(Path(tmp_dir) / "chatterbox.mp3")
            result = vs.chatterbox_tts(
                text="hi", voice="default", voice_file=voice_file
            )
        self.assertIsNone(result)
        self.assertEqual(post.call_count, 3)

    def test_generate_subtitle_keeps_edge_provider_for_gemini_legacy_submaker(self):
        """
        Authentication Gemini TTS Returned legacy Subtitle structure edge provider Direct output
        SRT，It's not like it's a match failure. Whisper。
        """
        script = "Gemini subtitle generation should work now. Testing multiple lines."
        sub_maker = vs.populate_legacy_submaker_with_full_text(
            vs.ensure_legacy_submaker_fields(vs.SubMaker()),
            script,
            2.4,
        )

        with tempfile.TemporaryDirectory() as tmp_dir, patch.object(
            task_service.config,
            "app",
            dict(task_service.config.app, subtitle_provider="edge"),
        ), patch("app.services.subtitle.create") as whisper_create, patch(
            "app.utils.utils.task_dir",
            lambda tid="": str(Path(tmp_dir) / tid) if tid else str(Path(tmp_dir)),
        ):
            task_id = "gemini-subtitle-edge-task"
            Path(tmp_dir, task_id).mkdir(parents=True, exist_ok=True)
            subtitle_path = task_service.generate_subtitle(
                task_id=task_id,
                params=type("Params", (), {"subtitle_enabled": True})(),
                video_script=script,
                sub_maker=sub_maker,
                audio_file="",
            )

            self.assertTrue(subtitle_path.endswith("subtitle.srt"))
            self.assertTrue(Path(subtitle_path).exists())
            self.assertFalse(whisper_create.called)
            subtitle_content = Path(subtitle_path).read_text(encoding="utf-8")
            self.assertIn("Gemini subtitle generation should work now", subtitle_content)
            self.assertIn("Testing multiple lines", subtitle_content)

    def test_script_split_keeps_thousand_separator_comma(self):
        """
        Edge TTS Yes. "1,000 years" returns as consecutive text. You can't take a script when it's off.
        The English commas in the middle of the numbers will be the sentence boundary, otherwise the subtitles will come together. issue #894
        Lee. sub_items Number less script_lines，And wrongly back Whisper。
        """
        text = (
            "It takes about 1,000 years for a single drop of water to finish "
            "the whole trip!"
        )

        self.assertEqual(
            utils.split_string_by_punctuations(text),
            [
                (
                    "It takes about 1,000 years for a single drop of water to finish "
                    "the whole trip"
                )
            ],
        )

    def test_edge_cue_aggregation_handles_thousand_separator_comma(self):
        """
        Revert issue #894 Critical form:Edge cues The last sentence returns as consecutive text.
        Organisation `1,000 years`。Script break must be cues The condensation is the same.
        Break two subtitles.
        """
        text = (
            "The ocean isn't just sitting stil, it moves around the world like a massive "
            "amusement park ride! Cold water at the North and South Poles sinks to the "
            "bottom because it is heavy and salty. At the same time, warm water from the "
            "sunny equator flows along the top to take its place. This creates a giant "
            "underwater conveyor belt that travels all the way around the Earth. It takes "
            "about 1,000 years for a single drop of water to finish the whole trip!"
        )
        script_lines = utils.split_string_by_punctuations(text)
        cues = []
        for index, line in enumerate(script_lines):
            # Edge Yes. cue content There's often no space in the script and no spot layout.
            # To simulate a more rigorous match scene.
            cues.append(
                SimpleNamespace(
                    content=line.replace(" ", ""),
                    start=timedelta(seconds=index),
                    end=timedelta(seconds=index + 0.8),
                )
            )
        sub_maker = SimpleNamespace(cues=cues)

        sub_items = vs._build_subtitle_items_from_edge_cues(sub_maker, script_lines)

        self.assertEqual(len(sub_items), len(script_lines))
        self.assertIn("1,000 years", sub_items[-1])

    def test_script_split_supports_arabic_punctuation(self):
        """
        Arabic scripts are common ، ؛ ؟ As a natural breakpoint. This must be identified during the break.
        Punctuation, otherwise edge-tts cue The paused boundary and the script line boundary will be mislocated.
        """
        text = "مرحبا بالعالم، كيف حالك؟ هذا اختبار؛ يعمل بشكل جيد."

        self.assertEqual(
            utils.split_string_by_punctuations(text),
            [
                "مرحبا بالعالم",
                "كيف حالك",
                "هذا اختبار",
                "يعمل بشكل جيد",
            ],
        )

    def test_match_script_line_normalizes_arabic_letter_forms(self):
        """
        edge-tts It's possible to homogenize different alphabetic forms in Arabic, or to return with transacting symbols,
        Tatweel Yes. cue text. It should be wrong to match, but eventually the subtitles remain the original script.
        """
        script_lines = ["أهلاً وسهلاً بك في المدرسة"]

        matched = vs._match_script_line(
            script_lines,
            "اهلا وسهلا بك في المدرسه",
            0,
        )

        self.assertEqual(matched, script_lines[0])

    def test_edge_cue_aggregation_handles_arabic_variant_forms(self):
        """
        Original Arabic subtitle failed core path: script contains أ/ة The letter form,edge cue
        Back ا/ه And when it's normalized, aggregates should produce complete subtitles and avoid retreating. Whisper。
        """
        text = "أهلاً وسهلاً بك في المدرسة؟ هذا اختبار رائع، شكراً لك."
        script_lines = utils.split_string_by_punctuations(text)
        cue_texts = [
            "اهلا وسهلا بك في المدرسه",
            "هذا اختبار رائع",
            "شكرا لك",
        ]
        sub_maker = SimpleNamespace(
            cues=[
                SimpleNamespace(
                    content=cue_text,
                    start=timedelta(seconds=index),
                    end=timedelta(seconds=index + 0.8),
                )
                for index, cue_text in enumerate(cue_texts)
            ]
        )

        sub_items = vs._build_subtitle_items_from_edge_cues(sub_maker, script_lines)

        self.assertEqual(len(sub_items), len(script_lines))
        self.assertIn("أهلاً وسهلاً بك في المدرسة", sub_items[0])
        self.assertIn("شكراً لك", sub_items[-1])

    def test_create_subtitle_ignores_markdown_separator_lines(self):
        """
        User Manual Script may contain `---` This one. Markdown separator.TTS Can't read.
        These symbol lines, subtitling, or subtitling, should not be used as target subtitles.
        The subtitles are stuck and back. Whisper。
        """
        text = "First paragraph\n---\n Second paragraph"
        sub_maker = SimpleNamespace(
            cues=[
                SimpleNamespace(
                    content="First paragraph",
                    start=timedelta(seconds=0),
                    end=timedelta(seconds=0.8),
                ),
                SimpleNamespace(
                    content="Second paragraph",
                    start=timedelta(seconds=1),
                    end=timedelta(seconds=1.8),
                ),
            ]
        )

        with tempfile.TemporaryDirectory() as tmp_dir:
            subtitle_file = Path(tmp_dir) / "subtitle.srt"
            vs.create_subtitle(
                sub_maker=sub_maker,
                text=text,
                subtitle_file=str(subtitle_file),
            )

            subtitle_content = subtitle_file.read_text(encoding="utf-8")

        self.assertIn("First paragraph", subtitle_content)
        self.assertIn("Second paragraph", subtitle_content)
        self.assertNotIn("---", subtitle_content)
        self.assertNotIn("00:00:00,000 --> 00:00:00,000", subtitle_content)

    def test_create_subtitle_ignores_markdown_underscore_marks(self):
        """
        `_` Often used by users Markdown Emphasis on marking, but TTS Returned cue Usually not included
        These formatholders. Ignore when matching `_`，Avoid creating empty subtitles or retreating back Whisper。
        """
        text = "This is..._a_Test."
        sub_maker = SimpleNamespace(
            cues=[
                SimpleNamespace(
                    content="This is...a Test",
                    start=timedelta(seconds=0),
                    end=timedelta(seconds=0.8),
                ),
            ]
        )

        with tempfile.TemporaryDirectory() as tmp_dir:
            subtitle_file = Path(tmp_dir) / "subtitle.srt"
            vs.create_subtitle(
                sub_maker=sub_maker,
                text=text,
                subtitle_file=str(subtitle_file),
            )

            subtitle_content = subtitle_file.read_text(encoding="utf-8")

        self.assertIn("This is...a Test", subtitle_content)
        self.assertNotIn("This is..._a_Test", subtitle_content)
        self.assertNotIn("00:00:00,000 --> 00:00:00,000", subtitle_content)

    def test_convert_rate_to_percent_signs_zero_rate(self):
        # Rates near but not exactly 1.0 round to 0 percent. edge-tts rejects
        # an unsigned "0%" (ValueError: Invalid rate '0%'), so the helper must
        # emit a sign-prefixed "+0%". Regression test for that crash.
        self.assertEqual(vs.convert_rate_to_percent(1.0), "+0%")
        self.assertEqual(vs.convert_rate_to_percent(1.004), "+0%")
        self.assertEqual(vs.convert_rate_to_percent(0.997), "+0%")
        self.assertEqual(vs.convert_rate_to_percent(1.5), "+50%")
        self.assertEqual(vs.convert_rate_to_percent(0.8), "-20%")

    def test_convert_rate_to_percent_invalid_values_default_to_normal(self):
        # API And batches of scripts might be able to pass the word out. 0、None or empty strings; none of these should be allowed
        # edge-tts Copy that. -100% Or trigger an anomaly, but be processed at normal speed.
        self.assertEqual(vs.convert_rate_to_percent(0), "+0%")
        self.assertEqual(vs.convert_rate_to_percent(0.0), "+0%")
        self.assertEqual(vs.convert_rate_to_percent(None), "+0%")
        self.assertEqual(vs.convert_rate_to_percent(""), "+0%")


class TestElevenLabsVoice(unittest.TestCase):

    def test_is_elevenlabs_voice_true(self):
        self.assertTrue(vs.is_elevenlabs_voice("elevenlabs:pNInz6obpgDQGcFmaJgB:Adam"))

    def test_is_elevenlabs_voice_false_azure(self):
        self.assertFalse(vs.is_elevenlabs_voice("zh-CN-XiaoxiaoNeural-Female"))

    def test_is_elevenlabs_voice_false_siliconflow(self):
        self.assertFalse(vs.is_elevenlabs_voice("siliconflow:model:voice-Male"))

    def test_is_elevenlabs_voice_empty(self):
        self.assertFalse(vs.is_elevenlabs_voice(""))

    def test_is_elevenlabs_voice_none(self):
        self.assertFalse(vs.is_elevenlabs_voice(None))

    def test_get_elevenlabs_voices_empty_api_key(self):
        result = vs.get_elevenlabs_voices("")
        self.assertEqual(result, [])

    @patch("app.services.voice.requests.get")
    def test_get_elevenlabs_voices_success(self, mock_get):
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {
            "voices": [
                {"voice_id": "abc123", "name": "Adam"},
                {"voice_id": "def456", "name": "Rachel"},
            ]
        }
        result = vs.get_elevenlabs_voices("fake-api-key")
        self.assertEqual(result, [
            "elevenlabs:abc123:Adam",
            "elevenlabs:def456:Rachel",
        ])
        mock_get.assert_called_once()
        call_kwargs = mock_get.call_args
        self.assertIn("xi-api-key", call_kwargs.kwargs.get("headers", {}))

    @patch("app.services.voice.requests.get")
    def test_get_elevenlabs_voices_http_error(self, mock_get):
        mock_get.return_value.status_code = 401
        mock_get.return_value.text = "Unauthorized"
        result = vs.get_elevenlabs_voices("bad-key")
        self.assertEqual(result, [])

    @patch("app.services.voice.requests.get")
    def test_get_elevenlabs_voices_network_error(self, mock_get):
        import requests as req_lib
        mock_get.side_effect = req_lib.exceptions.ConnectionError("timeout")
        result = vs.get_elevenlabs_voices("fake-key")
        self.assertEqual(result, [])

    @patch("app.services.voice.requests.post")
    @patch("app.services.voice.AudioFileClip")
    @patch("app.services.voice.config")
    def test_elevenlabs_tts_success(self, mock_config, mock_clip_cls, mock_post):
        mock_config.elevenlabs.get.return_value = "fake-api-key"
        mock_post.return_value.status_code = 200
        mock_post.return_value.content = b"fake-mp3-bytes"
        mock_clip_cls.return_value.duration = 3.0
        mock_clip_cls.return_value.close = lambda: None

        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
            out_path = f.name

        try:
            result = vs.elevenlabs_tts("Hello world", "abc123", out_path)
            self.assertIsNotNone(result)
            self.assertTrue(hasattr(result, "subs"))
            self.assertTrue(hasattr(result, "offset"))
        finally:
            if os.path.exists(out_path):
                os.remove(out_path)

    @patch("app.services.voice.config")
    def test_elevenlabs_tts_no_api_key(self, mock_config):
        mock_config.elevenlabs.get.return_value = ""
        result = vs.elevenlabs_tts("Hello", "abc123", "/tmp/test.mp3")
        self.assertIsNone(result)

    @patch("app.services.voice.config")
    def test_elevenlabs_tts_empty_text(self, mock_config):
        mock_config.elevenlabs.get.return_value = "fake-key"
        result = vs.elevenlabs_tts("  ", "abc123", "/tmp/test.mp3")
        self.assertIsNone(result)


if __name__ == "__main__":
    # python -m unittest test.services.test_voice.TestVoiceService.test_azure_tts_v1
    # python -m unittest test.services.test_voice.TestVoiceService.test_azure_tts_v2
    unittest.main()

import unittest
from unittest.mock import patch

from app.controllers.v1 import llm as llm_controller
from app.models.schema import (
    VideoScriptRequest,
    VideoSocialMetadataRequest,
    VideoTermsRequest,
)


class TestLlmController(unittest.TestCase):
    def test_preview_video_script_prompt_uses_the_same_builder_as_generation(self):
        body = VideoScriptRequest(video_subject="Coffee", video_language="en", paragraph_number=2)
        with patch.object(llm_controller.llm, "build_script_prompt", return_value="final prompt") as build:
            response = llm_controller.preview_video_script_prompt(None, body)
        self.assertEqual(response, {"status": 200, "data": {"prompt": "final prompt"}})
        build.assert_called_once_with(
            video_subject="Coffee",
            language="en",
            paragraph_number=2,
            video_script_prompt="",
            custom_system_prompt="",
        )

    def test_generate_video_script_forwards_all_prompt_fields(self):
        """The file interface cannot lose the number of advanced hints or paragraphs."""
        body = VideoScriptRequest(
            video_subject="Coffee",
            video_language="en",
            paragraph_number=2,
            video_script_prompt="Friendly tone",
            custom_system_prompt="Return narration only.",
        )

        with patch.object(
            llm_controller.llm,
            "generate_script",
            return_value="Generated script",
        ) as generate:
            response = llm_controller.generate_video_script(None, body)

        self.assertEqual(
            response,
            {"status": 200, "data": {"video_script": "Generated script"}},
        )
        generate.assert_called_once_with(
            video_subject="Coffee",
            language="en",
            paragraph_number=2,
            video_script_prompt="Friendly tone",
            custom_system_prompt="Return narration only.",
        )

    def test_generate_video_terms_forwards_order_matching_mode(self):
        """Material sequence matching switches must continue to pass to keyword generation services."""
        body = VideoTermsRequest(
            video_subject="Coffee",
            video_script="First beans, then brewing.",
            amount=4,
            match_materials_to_script=True,
        )

        with patch.object(
            llm_controller.llm,
            "generate_terms",
            return_value=["beans", "brewing"],
        ) as generate:
            response = llm_controller.generate_video_terms(None, body)

        self.assertEqual(
            response,
            {"status": 200, "data": {"video_terms": ["beans", "brewing"]}},
        )
        generate.assert_called_once_with(
            video_subject="Coffee",
            video_script="First beans, then brewing.",
            amount=4,
            match_script_order=True,
        )

    def test_generate_social_metadata_returns_service_payload(self):
        """The social platform metadata interface should maintain a responsive structure for service-level results."""
        body = VideoSocialMetadataRequest(
            video_subject="Coffee",
            video_script="Morning coffee.",
            language="en",
            platform="youtube_shorts",
        )
        metadata = {
            "title": "Morning Coffee",
            "caption": "Start the day.",
            "hashtags": ["#coffee"],
        }

        with patch.object(
            llm_controller.llm,
            "generate_social_metadata",
            return_value=metadata,
        ) as generate:
            response = llm_controller.generate_video_social_metadata(None, body)

        self.assertEqual(response, {"status": 200, "data": metadata})
        generate.assert_called_once_with(
            video_subject="Coffee",
            video_script="Morning coffee.",
            language="en",
            platform="youtube_shorts",
        )


if __name__ == "__main__":
    unittest.main()

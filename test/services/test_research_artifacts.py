import json
import unittest
from unittest.mock import patch

from app.services import research_artifacts


COMPLETED_RESEARCH = {
    "id": "r1",
    "topic": "cats",
    "status": "completed",
    "report_json": {
        "entities": [{
            "entity": "cats",
            "report": {
                "clusters": [{
                    "cluster_id": "cluster-1",
                    "title": "Cats are great",
                    "candidate_ids": ["candidate-1"],
                }],
                "ranked_candidates": [{
                    "candidate_id": "candidate-1",
                    "cluster_id": "cluster-1",
                    "title": "Evidence",
                    "snippet": "A useful snippet",
                    "metadata": {"top_comments": [{"body": "Strong comment"}]},
                }],
            },
        }],
    },
}


class TestArtifactChat(unittest.TestCase):
    def test_initial_turn_asks_a_question_without_persisting(self):
        response = json.dumps({"type": "question", "message": "Who is the audience?"})
        with patch.object(research_artifacts.research_store, "get_research", return_value=COMPLETED_RESEARCH), patch.object(
            research_artifacts.llm, "generate_response", return_value=response
        ), patch.object(research_artifacts.research_store, "upsert_artifact") as upsert:
            result = research_artifacts.chat(
                "r1", "cats", "cluster-1", ["video_subject", "video_script"], []
            )

        self.assertEqual(result["type"], "question")
        upsert.assert_not_called()

    def test_final_turn_validates_and_persists_only_selected_fields(self):
        response = json.dumps({
            "type": "final",
            "message": "Ready",
            "artifacts": {
                "video_subject": "Why cats are great",
                "video_script": "The script",
            },
        })
        saved = {"id": "a1", "video_subject": "Why cats are great"}
        with patch.object(research_artifacts.research_store, "get_research", return_value=COMPLETED_RESEARCH), patch.object(
            research_artifacts.llm, "generate_response", return_value=response
        ), patch.object(research_artifacts.research_store, "upsert_artifact", return_value=saved) as upsert:
            result = research_artifacts.chat(
                "r1", "cats", "cluster-1", ["video_subject", "video_script"],
                [{"role": "user", "content": "General audience, concise."}],
            )

        self.assertEqual(result["artifact"], saved)
        upsert.assert_called_once_with(
            "r1", "cats", "cluster-1",
            {"video_subject": "Why cats are great", "video_script": "The script"},
            ["video_script"],
        )

    def test_rejects_finalization_before_a_user_reply(self):
        response = json.dumps({
            "type": "final", "message": "Ready",
            "artifacts": {"video_subject": "Blind result"},
        })
        with patch.object(research_artifacts.research_store, "get_research", return_value=COMPLETED_RESEARCH), patch.object(
            research_artifacts.llm, "generate_response", return_value=response
        ):
            with self.assertRaises(research_artifacts.ArtifactAgentError):
                research_artifacts.chat(
                    "r1", "cats", "cluster-1", ["video_subject"], []
                )

    def test_rejects_missing_cluster_and_unselected_output(self):
        with patch.object(research_artifacts.research_store, "get_research", return_value=COMPLETED_RESEARCH):
            with self.assertRaises(research_artifacts.ArtifactNotFoundError):
                research_artifacts.chat(
                    "r1", "cats", "missing", ["video_subject"], []
                )

        response = json.dumps({
            "type": "final", "message": "Ready",
            "artifacts": {"video_subject": "Cats", "video_script": "Not selected"},
        })
        with patch.object(research_artifacts.research_store, "get_research", return_value=COMPLETED_RESEARCH), patch.object(
            research_artifacts.llm, "generate_response", return_value=response
        ):
            with self.assertRaises(research_artifacts.ArtifactAgentError):
                research_artifacts.chat(
                    "r1", "cats", "cluster-1", ["video_subject"],
                    [{"role": "user", "content": "General audience"}],
                )

    def test_prompt_contains_full_cluster_candidate_context(self):
        with patch.object(research_artifacts.research_store, "get_research", return_value=COMPLETED_RESEARCH), patch.object(
            research_artifacts.llm,
            "generate_response",
            return_value='{"type":"question","message":"Audience?"}',
        ) as generate:
            research_artifacts.chat(
                "r1", "cats", "cluster-1", ["video_subject"], []
            )

        prompt = generate.call_args.args[0]
        self.assertIn("A useful snippet", prompt)
        self.assertIn("Strong comment", prompt)

    def test_current_draft_is_fetched_only_when_has_draft_is_true(self):
        response = json.dumps({"type": "question", "message": "Anything else?"})
        existing = {
            "video_subject": "Why cats are great", "video_script": "Old script",
            "generated_fields": ["video_script"],
        }
        with patch.object(research_artifacts.research_store, "get_research", return_value=COMPLETED_RESEARCH), patch.object(
            research_artifacts.research_store, "get_artifact", return_value=existing
        ) as get_artifact, patch.object(
            research_artifacts.llm, "generate_response", return_value=response
        ) as generate:
            research_artifacts.chat(
                "r1", "cats", "cluster-1", ["video_subject", "video_script"],
                [{"role": "user", "content": "Make it shorter"}],
                has_draft=True,
            )

        get_artifact.assert_called_once_with("r1", "cats", "cluster-1")
        prompt = generate.call_args.args[0]
        self.assertIn("Old script", prompt)

    def test_current_draft_ignores_a_persisted_artifact_when_has_draft_is_false(self):
        response = json.dumps({"type": "question", "message": "Who is the audience?"})
        existing = {
            "video_subject": "Stale", "video_script": "Stale script",
            "generated_fields": ["video_script"],
        }
        with patch.object(research_artifacts.research_store, "get_research", return_value=COMPLETED_RESEARCH), patch.object(
            research_artifacts.research_store, "get_artifact", return_value=existing
        ) as get_artifact, patch.object(
            research_artifacts.llm, "generate_response", return_value=response
        ) as generate:
            research_artifacts.chat(
                "r1", "cats", "cluster-1", ["video_subject", "video_script"], [],
            )

        get_artifact.assert_not_called()
        prompt = generate.call_args.args[0]
        self.assertNotIn("Stale script", prompt)
        self.assertIn("none yet", prompt)

    def test_force_final_instructs_the_model_to_finish_now(self):
        response = json.dumps({
            "type": "final", "message": "Ready",
            "artifacts": {"video_subject": "Cats"},
        })
        with patch.object(research_artifacts.research_store, "get_research", return_value=COMPLETED_RESEARCH), patch.object(
            research_artifacts.llm, "generate_response", return_value=response
        ) as generate, patch.object(research_artifacts.research_store, "upsert_artifact", return_value={"id": "a1"}):
            research_artifacts.chat(
                "r1", "cats", "cluster-1", ["video_subject"],
                [{"role": "user", "content": "General audience"}],
                force_final=True,
            )

        prompt = generate.call_args.args[0]
        self.assertIn("without further questions", prompt)

    def test_a_second_final_turn_overwrites_the_same_artifact(self):
        response = json.dumps({
            "type": "final", "message": "Updated",
            "artifacts": {"video_subject": "Cats, but funnier"},
        })
        existing = {"video_subject": "Cats", "generated_fields": []}
        with patch.object(research_artifacts.research_store, "get_research", return_value=COMPLETED_RESEARCH), patch.object(
            research_artifacts.research_store, "get_artifact", return_value=existing
        ), patch.object(
            research_artifacts.llm, "generate_response", return_value=response
        ), patch.object(
            research_artifacts.research_store, "upsert_artifact", return_value={"id": "a1", "video_subject": "Cats, but funnier"}
        ) as upsert:
            research_artifacts.chat(
                "r1", "cats", "cluster-1", ["video_subject"],
                [{"role": "user", "content": "Make it funnier"}],
                has_draft=True,
            )

        upsert.assert_called_once_with("r1", "cats", "cluster-1", {"video_subject": "Cats, but funnier"}, [])


class TestRestoreParams(unittest.TestCase):
    def test_builds_complete_video_params_with_generated_overlay(self):
        artifact = {
            "video_subject": "Cats",
            "video_script": None,
            "video_script_prompt": "Be concise",
            "custom_system_prompt": None,
            "video_terms": None,
            "generated_fields": ["video_script_prompt"],
        }
        with patch.object(research_artifacts.research_store, "get_artifact", return_value=artifact):
            payload = research_artifacts.restore_params("r1", "cats", "cluster-1")

        self.assertEqual(payload["video_subject"], "Cats")
        self.assertEqual(payload["video_script_prompt"], "Be concise")
        self.assertIn("video_aspect", payload)
        self.assertEqual(payload["video_script"], "")


if __name__ == "__main__":
    unittest.main()

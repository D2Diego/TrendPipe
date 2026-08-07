import unittest
from types import SimpleNamespace
from unittest.mock import patch

from app.controllers.v1 import research as controller
from app.models.exception import HttpException
from app.router import root_api_router


class TestResearchController(unittest.TestCase):
    def test_routes_are_registered(self):
        paths = {route.path for route in root_api_router.routes}
        self.assertIn("/api/v1/researches", paths)
        self.assertIn("/api/v1/researches/{research_id}", paths)
        self.assertIn("/api/v1/research-settings", paths)
        self.assertIn(
            "/api/v1/researches/{research_id}/entities/{entity}/clusters/{cluster_id}/artifact-chat",
            paths,
        )
        self.assertIn(
            "/api/v1/researches/{research_id}/entities/{entity}/clusters/{cluster_id}/restore-params",
            paths,
        )

    def test_create_schedules_background_job(self):
        background_tasks = SimpleNamespace(add_task=lambda *args, **kwargs: None)
        with patch.object(
            controller.research,
            "create_research",
            return_value={"id": "r1", "status": "pending"},
        ), patch.object(background_tasks, "add_task") as add_task_mock:
            response = controller.create_research(
                SimpleNamespace(headers={}),
                controller.CreateResearchRequest(
                    topic="cats", depth="quick", sources=["reddit"]
                ),
                background_tasks,
            )

        self.assertEqual(response["data"]["id"], "r1")
        add_task_mock.assert_called_once_with(controller.research.run_research_job, "r1")

    def test_create_translates_validation_error_to_400(self):
        background_tasks = SimpleNamespace(add_task=lambda *args, **kwargs: None)
        with patch.object(
            controller.research,
            "create_research",
            side_effect=controller.research.ResearchValidationError("bad"),
        ):
            with self.assertRaises(HttpException) as ctx:
                controller.create_research(
                    SimpleNamespace(headers={}),
                    controller.CreateResearchRequest(topic="", sources=[]),
                    background_tasks,
                )
        self.assertEqual(ctx.exception.status_code, 400)

    def test_list_and_get_researches(self):
        with patch.object(
            controller.research_store, "list_researches", return_value=[{"id": "r1"}]
        ):
            response = controller.list_researches(SimpleNamespace(headers={}))
        self.assertEqual(response["data"]["researches"], [{"id": "r1"}])

        with patch.object(
            controller.research_store,
            "get_research",
            return_value={"id": "r1", "status": "completed"},
        ), patch.object(controller.research_store, "list_artifacts", return_value=[{"id": "a1"}]):
            response = controller.get_research(
                SimpleNamespace(headers={}), research_id="r1"
            )
        self.assertEqual(response["data"]["id"], "r1")
        self.assertEqual(response["data"]["artifacts"], [{"id": "a1"}])

    def test_get_returns_404_when_missing(self):
        with patch.object(controller.research_store, "get_research", return_value=None):
            with self.assertRaises(HttpException) as ctx:
                controller.get_research(
                    SimpleNamespace(headers={}), research_id="missing"
                )
        self.assertEqual(ctx.exception.status_code, 404)

    def test_delete_translates_conflict_and_missing(self):
        with patch.object(
            controller.research,
            "delete_research",
            side_effect=controller.research.ResearchConflictError("running"),
        ):
            with self.assertRaises(HttpException) as ctx:
                controller.delete_research(SimpleNamespace(headers={}), research_id="r1")
        self.assertEqual(ctx.exception.status_code, 409)

        with patch.object(controller.research, "delete_research", return_value=False):
            with self.assertRaises(HttpException) as ctx:
                controller.delete_research(SimpleNamespace(headers={}), research_id="missing")
        self.assertEqual(ctx.exception.status_code, 404)

    def test_delete_returns_success(self):
        with patch.object(controller.research, "delete_research", return_value=True):
            response = controller.delete_research(
                SimpleNamespace(headers={}), research_id="r1"
            )
        self.assertTrue(response["data"]["deleted"])

    def test_get_settings_returns_diagnosis(self):
        with patch.object(
            controller.research_engine,
            "run_diagnose",
            return_value={"available_sources": ["reddit"]},
        ):
            response = controller.get_research_settings(SimpleNamespace(headers={}))
        self.assertEqual(response["data"]["available_sources"], ["reddit"])

    def test_update_settings_writes_only_nonempty_allowed_values(self):
        with patch.object(controller.research_credentials, "write_credentials") as write_mock:
            controller.update_research_settings(
                SimpleNamespace(headers={}),
                controller.UpdateResearchSettingsRequest(
                    values={"OPENROUTER_API_KEY": "abc", "GOOGLE_API_KEY": ""}
                ),
            )
        write_mock.assert_called_once_with({"OPENROUTER_API_KEY": "abc"})

    def test_artifact_chat_and_restore(self):
        chat_result = {"type": "question", "message": "Audience?"}
        with patch.object(controller.research_artifacts, "chat", return_value=chat_result) as chat:
            response = controller.artifact_chat(
                SimpleNamespace(headers={}),
                controller.ArtifactChatRequest(
                    selected_fields=["video_subject"], messages=[]
                ),
                research_id="r1", entity="cats", cluster_id="cluster-1",
            )
        self.assertEqual(response["data"], chat_result)
        chat.assert_called_once_with("r1", "cats", "cluster-1", ["video_subject"], [])

        with patch.object(
            controller.research_artifacts,
            "restore_params",
            return_value={"video_subject": "Cats", "video_aspect": "9:16"},
        ):
            response = controller.get_artifact_restore_params(
                SimpleNamespace(headers={}),
                research_id="r1", entity="cats", cluster_id="cluster-1",
            )
        self.assertEqual(response["data"]["params"]["video_subject"], "Cats")

    def test_artifact_errors_are_translated(self):
        with patch.object(
            controller.research_artifacts,
            "chat",
            side_effect=controller.research_artifacts.ArtifactAgentError("bad output"),
        ):
            with self.assertRaises(HttpException) as ctx:
                controller.artifact_chat(
                    SimpleNamespace(headers={}),
                    controller.ArtifactChatRequest(
                        selected_fields=["video_subject"], messages=[]
                    ),
                    research_id="r1", entity="cats", cluster_id="cluster-1",
                )
        self.assertEqual(ctx.exception.status_code, 502)

    def test_delete_artifact_returns_404_or_success(self):
        with patch.object(controller.research_store, "delete_artifact", return_value=False):
            with self.assertRaises(HttpException) as ctx:
                controller.delete_artifact(
                    SimpleNamespace(headers={}),
                    research_id="r1", entity="cats", cluster_id="cluster-1",
                )
        self.assertEqual(ctx.exception.status_code, 404)

        with patch.object(controller.research_store, "delete_artifact", return_value=True):
            response = controller.delete_artifact(
                SimpleNamespace(headers={}),
                research_id="r1", entity="cats", cluster_id="cluster-1",
            )
        self.assertTrue(response["data"]["deleted"])


if __name__ == "__main__":
    unittest.main()

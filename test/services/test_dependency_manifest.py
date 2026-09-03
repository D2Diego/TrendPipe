import re
import tomllib
import unittest
from pathlib import Path


class TestDependencyManifest(unittest.TestCase):
    def test_container_runtime_supports_trendpipe_python_requirement(self):
        root = Path(__file__).resolve().parents[2]
        dockerfile = (root / "Dockerfile").read_text(encoding="utf-8")
        runtime_image = re.search(
            r"^FROM python:(\d+)\.(\d+)(?:[^\s]*)$", dockerfile, flags=re.MULTILINE
        )

        self.assertIsNotNone(runtime_image)
        version = tuple(int(part) for part in runtime_image.groups())
        self.assertGreaterEqual(version, (3, 12))

    def test_toml_runtime_dependency_is_declared_for_host_and_docker_installs(self):
        root = Path(__file__).resolve().parents[2]
        pyproject = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
        project_dependencies = pyproject["project"]["dependencies"]
        requirement_lines = (root / "requirements.txt").read_text(encoding="utf-8").splitlines()

        def dependency_names(entries):
            return {
                re.split(r"[<>=!~;\[]", entry, maxsplit=1)[0].strip().lower()
                for entry in entries
                if entry.strip() and not entry.lstrip().startswith("#")
            }

        self.assertIn("toml", dependency_names(project_dependencies))
        self.assertIn("toml", dependency_names(requirement_lines))


if __name__ == "__main__":
    unittest.main()

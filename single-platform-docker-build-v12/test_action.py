import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

import yaml


class ScanInputTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.steps = yaml.safe_load(
            Path(__file__).with_name("action.yaml").read_text()
        )["runs"]["steps"]
        cls.export = next(s for s in cls.steps if s.get("id") == "scan-input")
        cls.scan = next(s for s in cls.steps if s.get("id") == "scan-image")
        cls.cleanup = next(s for s in cls.steps if s["name"] == "Remove scan archive")

    def test_scan_uses_local_archive_before_push(self):
        self.assertEqual(
            self.export["env"]["IMAGE"],
            "${{ steps.build-image.outputs.full_image_tag }}",
        )
        self.assertEqual(
            self.scan["with"]["image"], "${{ steps.scan-input.outputs.image_archive }}"
        )
        self.assertEqual(self.export["if"], self.scan["if"])
        self.assertIn("always()", self.cleanup["if"])
        ids = [s.get("id") for s in self.steps]
        self.assertLess(ids.index("build-image"), ids.index("scan-input"))
        self.assertLess(ids.index("scan-input"), ids.index("scan-image"))
        self.assertLess(ids.index("scan-image"), ids.index("push-image"))

    def test_export_and_cleanup_even_after_save_failure(self):
        for save_exit_code in (0, 1):
            with self.subTest(save_exit_code=save_exit_code), tempfile.TemporaryDirectory() as tmp:
                work = Path(tmp)
                docker = work / "docker"
                docker.write_text(
                    "#!/usr/bin/env python3\n"
                    "import json, os, pathlib, sys\n"
                    "args = sys.argv[1:]\n"
                    "pathlib.Path(os.environ['DOCKER_LOG']).write_text(json.dumps(args))\n"
                    "assert len(args) == 5 and args[:3] == ['image', 'save', '--output']\n"
                    "pathlib.Path(args[3]).write_text('new local image')\n"
                    "sys.exit(int(os.environ['SAVE_EXIT_CODE']))\n"
                )
                docker.chmod(0o755)
                image = "123456789012.dkr.ecr.eu-central-1.amazonaws.com/prism:backend-main-arm64"
                output = work / "output"
                env = dict(
                    os.environ,
                    PATH=f"{work}{os.pathsep}{os.environ['PATH']}",
                    RUNNER_TEMP=str(work),
                    GITHUB_OUTPUT=str(output),
                    IMAGE=image,
                    DOCKER_LOG=str(work / "docker-log"),
                    SAVE_EXIT_CODE=str(save_exit_code),
                )
                result = subprocess.run(
                    ["bash", "-e", "-o", "pipefail", "-c", self.export["run"]],
                    env=env, capture_output=True, text=True,
                )
                self.assertEqual(result.returncode, save_exit_code, result.stderr)
                archive = Path(output.read_text().strip().split("=", 1)[1])
                self.assertEqual(archive.read_text(), "new local image")
                self.assertEqual(
                    json.loads((work / "docker-log").read_text()),
                    ["image", "save", "--output", str(archive), image],
                )
                subprocess.run(
                    ["bash", "-e", "-c", self.cleanup["run"]],
                    env=dict(env, IMAGE_ARCHIVE=str(archive)), check=True,
                )
                self.assertFalse(archive.parent.exists())


if __name__ == "__main__":
    unittest.main()

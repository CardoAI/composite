import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


ACTION = Path(__file__).resolve().parent
TRIVY = os.environ.get('TRIVY_BIN') or shutil.which('trivy')


@unittest.skipUnless(TRIVY, 'Set TRIVY_BIN or install Trivy to test dependency coverage')
class CoverageTest(unittest.TestCase):
    def check(self, results, expected='yarn.lock'):
        with tempfile.TemporaryDirectory() as temp:
            report = Path(temp) / 'trivy.json'
            report.write_text(json.dumps({'SchemaVersion': 2, 'ArtifactName': 'frontend', 'ArtifactType': 'filesystem', 'Results': results}))
            return subprocess.run(
                [TRIVY, 'convert', '--format', 'template',
                 '--template', f'@{ACTION / "check-coverage.tpl"}',
                 '--ignorefile', '', '--exit-code', '0',
                 '--output', '', str(report)],
                env={**os.environ, 'EXPECTED_LOCKFILE': expected}, cwd=temp,
                capture_output=True, text=True, timeout=15,
            )

    def result(self, **fields):
        return {
            'Target': 'yarn.lock', 'Class': 'lang-pkgs', 'Type': 'yarn',
            'Packages': [{'Name': 'example', 'Version': '1.0.0'}],
            **fields,
        }

    def test_clean_dependency_inventory_passes_without_vulnerabilities(self):
        result = self.check([self.result()])
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_missing_or_unresolved_dependency_inventory_fails(self):
        for results in [[], [self.result(Packages=[])], [self.result(Packages=[{'Name': 'example'}])]]:
            with self.subTest(results=results):
                result = self.check(results)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn('Dependency scan incomplete', result.stderr)

    def test_unrelated_lockfile_cannot_hide_unscanned_root_lockfile(self):
        for target in ['nested/yarn.lock', 'package-lock.json']:
            with self.subTest(target=target):
                result = self.check([self.result(Target=target)])
                self.assertNotEqual(result.returncode, 0)

    def test_supported_lockfile_types_have_coverage(self):
        for target, package_type in [('yarn.lock', 'yarn'), ('package-lock.json', 'npm'), ('pnpm-lock.yaml', 'pnpm'), ('bun.lock', 'bun')]:
            with self.subTest(target=target):
                result = self.check([self.result(Target=target, Type=package_type)], expected=target)
                self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == '__main__':
    unittest.main()

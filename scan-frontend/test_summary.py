import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


ACTION = Path(__file__).resolve().parent
TRIVY = os.environ.get('TRIVY_BIN') or shutil.which('trivy')


@unittest.skipUnless(TRIVY, 'Set TRIVY_BIN or install Trivy to test summary rendering')
class SummaryTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / 'trivy').symlink_to(Path(TRIVY).resolve())
        self.summary = self.root / 'github-summary.md'
        self.summary.write_text('Existing summary\n\n')
        self.report = self.root / 'trivy.json'
        (self.root / 'coverage-ok').touch()
        self.vulnerability_count = 0
        self.env = {
            **os.environ,
            'PATH': f"{self.root}{os.pathsep}{os.environ['PATH']}",
            'GITHUB_ACTION_PATH': str(ACTION),
            'GITHUB_STEP_SUMMARY': str(self.summary),
            'REPORT_DIRECTORY': str(self.root),
            'SCAN_OUTCOME': 'success',
        }

    def write_report(self, vulnerabilities):
        self.report.write_text(json.dumps({
            'SchemaVersion': 2,
            'ArtifactName': 'frontend',
            'ArtifactType': 'filesystem',
            'Results': [{
                'Target': 'yarn.lock', 'Class': 'lang-pkgs', 'Type': 'yarn',
                'Vulnerabilities': vulnerabilities,
            }],
        }))

    def vuln(self, severity='CRITICAL', fixed='2.0.0', **fields):
        self.vulnerability_count += 1
        return {
            'VulnerabilityID': f'CVE-TEST-{self.vulnerability_count}', 'Severity': severity,
            'PkgName': 'example', 'InstalledVersion': '1.0.0',
            'FixedVersion': fixed, **fields,
        }

    def render(self, **env):
        result = subprocess.run(
            ['bash', str(ACTION / 'write-summary.sh')],
            env={**self.env, **env}, cwd=self.root,
            capture_output=True, text=True, timeout=15,
        )
        return result, self.summary.read_text()

    def test_blocked_summary_has_counts_and_details(self):
        self.write_report([self.vuln('HIGH'), self.vuln(), self.vuln(fixed='')])
        result, summary = self.render(SCAN_OUTCOME='failed')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(summary.startswith('Existing summary\n\n'))
        self.assertIn('Build and deployment blocked', summary)
        self.assertIn('| 2 | 1 | 0 | 0 | 0 | 3 | 1 |', summary)
        self.assertIn('| example | 1.0.0 | 2.0.0 | yarn.lock | Yes |', summary)
        self.assertIn('No fix available', summary)
        self.assertLess(summary.index('| CRITICAL |'), summary.index('| HIGH |'))

    def test_unfixed_critical_and_fixable_high_do_not_claim_blocking(self):
        self.write_report([self.vuln(fixed=''), self.vuln('HIGH')])
        result, summary = self.render()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('Dependency gate passed', summary)
        self.assertIn('| 1 | 1 | 0 | 0 | 0 | 2 | 0 |', summary)
        self.assertNotIn('| Yes |', summary)

    def test_clean_scan(self):
        self.write_report([])
        result, summary = self.render()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('No dependency vulnerabilities detected', summary)
        self.assertIn('| 0 | 0 | 0 | 0 | 0 | 0 | 0 |', summary)
        self.assertNotIn('Download the full JSON report', summary)

    def test_summary_file_is_separate_from_rendered_fragment(self):
        self.write_report([])
        summary_path = self.root / 'summary.md'
        result, _ = self.render(GITHUB_STEP_SUMMARY=str(summary_path))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('No dependency vulnerabilities detected', summary_path.read_text())

    def test_scanner_error_is_visible_even_with_no_findings(self):
        self.write_report([])
        result, summary = self.render(SCAN_OUTCOME='failed')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('Build and deployment blocked', summary)
        self.assertNotIn('Dependency gate passed', summary)

    def test_unverified_dependency_coverage_is_never_shown_as_clean(self):
        self.write_report([])
        (self.root / 'coverage-ok').unlink()
        result, summary = self.render(SCAN_OUTCOME='failed')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('Scan incomplete', summary)
        self.assertNotIn('Dependency gate passed', summary)
        self.assertNotIn('No dependency vulnerabilities detected', summary)

    def test_missing_or_invalid_report_is_never_shown_as_clean(self):
        for content in (None, 'not valid json'):
            with self.subTest(content=content):
                if content is not None:
                    self.report.write_text(content)
                self.summary.write_text('')
                result, summary = self.render(SCAN_OUTCOME='failed')
                self.assertNotEqual(result.returncode, 0)
                self.assertNotIn('Dependency gate passed', summary)
                self.assertNotIn('No dependency vulnerabilities detected', summary)
                self.assertIn('Review the scan logs', summary)

    def test_untrusted_metadata_cannot_inject_table_rows_or_links(self):
        self.write_report([self.vuln(PkgName='<script>|[click](https://example.com)\nnext')])
        result, summary = self.render()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('&lt;script&gt;&#124;&#91;click&#93;', summary)
        self.assertNotIn('<script>', summary)
        self.assertNotIn('[click](https://example.com)', summary)
        self.assertNotIn('\nnext', summary)

    def test_large_reports_limit_details_but_keep_complete_counts(self):
        self.write_report([self.vuln(PkgName='x' * 2000) for _ in range(110)])
        result, summary = self.render()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('| 110 | 0 | 0 | 0 | 0 | 110 | 110 |', summary)
        self.assertEqual(sum(line.startswith('| CVE-TEST-') for line in summary.splitlines()), 100)
        self.assertIn('Showing the first 100 findings', summary)
        self.assertIn('See the scan logs for all findings', summary)
        self.assertNotIn('x' * 121, summary)
        self.assertLess(len(summary.encode()), 1024 * 1024)


if __name__ == '__main__':
    unittest.main()

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


SCRIPT = Path(__file__).with_name("scan.sh")


class FrontendScanTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.frontend = self.root / "frontend with spaces"
        self.frontend.mkdir()
        (self.frontend / "package.json").write_text('{"name":"frontend"}')
        (self.frontend / "yarn.lock").write_text("# yarn lockfile v1\n")
        self.report = self.root / "reports"
        self.report.mkdir()
        self.calls = self.root / "calls.jsonl"
        binary = self.root / "trivy"
        binary.write_text(
            f"#!{sys.executable}\n"
            "import json, os, pathlib, sys\n"
            "args = sys.argv[1:]\n"
            "with open(os.environ['CALLS'], 'a') as log:\n"
            "    log.write(json.dumps(args) + '\\n')\n"
            "if '--output' in args:\n"
            "    if os.environ.get('FAIL_REPORT'):\n"
            "        sys.exit(2)\n"
            "    pathlib.Path(args[args.index('--output') + 1]).write_text('{}')\n"
            "if '--ignore-unfixed' in args:\n"
            "    sys.exit(int(os.environ.get('GATE_STATUS', '0')))\n"
        )
        binary.chmod(0o755)
        self.env = {
            **os.environ,
            "PATH": f"{self.root}{os.pathsep}{os.environ['PATH']}",
            "WORKING_DIRECTORY": str(self.frontend),
            "REPORT_DIRECTORY": str(self.report),
            "CALLS": str(self.calls),
        }

    def run_scan(self, **env):
        return subprocess.run(
            ["bash", str(SCRIPT)], env={**self.env, **env},
            capture_output=True, text=True,
        )

    def commands(self):
        return [json.loads(line) for line in self.calls.read_text().splitlines()]

    def test_complete_report_and_fixable_critical_gate(self):
        result = self.run_scan()
        self.assertEqual(result.returncode, 0, result.stderr)
        report, console, gate = self.commands()
        self.assertIn('--ignore-unfixed=false', report)
        self.assertEqual(report[report.index('--exit-code') + 1], '0')
        self.assertEqual(report[report.index('--severity') + 1], 'UNKNOWN,LOW,MEDIUM,HIGH,CRITICAL')
        self.assertEqual(console[console.index('--format') + 1], 'table')
        self.assertNotIn('--table-mode', console)
        self.assertEqual(gate[gate.index('--scanners') + 1], 'vuln')
        self.assertEqual(gate[gate.index('--severity') + 1], 'CRITICAL')
        self.assertIn('--ignore-unfixed', gate)
        self.assertEqual(gate[gate.index('--exit-code') + 1], '1')
        for command in (report, gate):
            self.assertEqual(command[command.index('--scanners') + 1], 'vuln')
            self.assertIn('--include-dev-deps', command)
            self.assertEqual(command[-1], '.')

    def test_gate_failure_keeps_local_report_for_summary(self):
        result = self.run_scan(GATE_STATUS='1')
        self.assertEqual(result.returncode, 1)
        self.assertTrue((self.report / 'trivy.json').is_file())

    def test_gate_scanner_error_fails(self):
        self.assertEqual(self.run_scan(GATE_STATUS='2').returncode, 2)

    def test_report_scanner_error_stops_before_gate(self):
        result = self.run_scan(FAIL_REPORT='1')
        self.assertEqual(result.returncode, 2)
        self.assertEqual(len(self.commands()), 1)

    def test_missing_manifest_or_lockfile_fails_before_scan(self):
        for filename in ('package.json', 'yarn.lock'):
            with self.subTest(filename=filename):
                path = self.frontend / filename
                original = path.read_text()
                path.unlink()
                result = self.run_scan()
                self.assertNotEqual(result.returncode, 0)
                self.assertIn('::error::', result.stdout)
                self.assertFalse(self.calls.exists())
                path.write_text(original)

    def test_missing_working_directory_fails(self):
        result = self.run_scan(WORKING_DIRECTORY=str(self.root / 'missing'))
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(self.calls.exists())


if __name__ == '__main__':
    unittest.main()

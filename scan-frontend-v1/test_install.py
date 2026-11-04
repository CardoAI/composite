import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import tempfile
import unittest
import zipfile


ACTION = Path(__file__).resolve().parent
VERSION = '0.76.1'


class InstallTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / 'path with spaces'
        self.root.mkdir()
        self.action = self.root / 'action'
        self.action.mkdir()
        shutil.copyfile(ACTION / 'install-trivy.sh', self.action / 'install-trivy.sh')
        self.runner = self.root / 'runner'
        self.report = self.root / 'report'
        self.runner.mkdir()
        self.report.mkdir()
        self.github_path = self.root / 'github-path'
        self.calls = self.root / 'curl-calls.jsonl'
        self.executed = self.root / 'executed'
        self.bin = self.root / 'stub-bin'
        self.bin.mkdir()
        self.stub('curl', """
import json, os, pathlib, shutil, sys
args = sys.argv[1:]
with open(os.environ['CURL_CALLS'], 'a') as log:
    log.write(json.dumps(args) + '\\n')
output = pathlib.Path(args[args.index('--output') + 1])
if os.environ.get('CURL_FAILURE'):
    output.write_text('partial download')
    print('curl: (7) Failed to connect', file=sys.stderr)
    sys.exit(7)
shutil.copyfile(os.environ['DOWNLOAD_SOURCE'], output)
""")
        # Simulate Git Bash's path conversion for the Windows ZIP fixture.
        self.stub('cygpath', 'import sys\nprint(sys.argv[-1])\n')
        self.env = {
            **os.environ,
            'PATH': f'{self.bin}{os.pathsep}{os.environ["PATH"]}',
            'TRIVY_VERSION': VERSION,
            'RUNNER_OS': 'Linux',
            'RUNNER_ARCH': 'X64',
            'RUNNER_TEMP': str(self.runner),
            'REPORT_DIRECTORY': str(self.report),
            'GITHUB_ACTION_PATH': str(self.action),
            'GITHUB_PATH': str(self.github_path),
            'CURL_CALLS': str(self.calls),
            'INSTALL_EXECUTED': str(self.executed),
        }
        self.archive = self.fixture('Linux-64bit.tar.gz')

    def stub(self, name, script):
        path = self.bin / name
        path.write_text(f'#!{sys.executable}\n' + script)
        path.chmod(0o755)

    def fixture(self, target):
        asset = f'trivy_{VERSION}_{target}'
        archive = self.root / asset
        executable = 'trivy.exe' if target.endswith('.zip') else 'trivy'
        binary = (
            f'#!{sys.executable}\n'
            'import os, pathlib\n'
            'pathlib.Path(os.environ["INSTALL_EXECUTED"]).touch()\n'
            f'print("Version: {VERSION}")\n'
        ).encode()
        if target.endswith('.zip'):
            with zipfile.ZipFile(archive, 'w') as output:
                output.writestr(executable, binary)
        else:
            with tarfile.open(archive, 'w:gz') as output:
                member = tarfile.TarInfo(executable)
                member.size = len(binary)
                member.mode = 0o755
                output.addfile(member, io.BytesIO(binary))
        checksum = hashlib.sha256(archive.read_bytes()).hexdigest()
        (self.action / 'trivy-checksums.txt').write_text(f'{checksum}  {asset}\n')
        self.env['DOWNLOAD_SOURCE'] = str(archive)
        return archive

    def install(self, **env):
        return subprocess.run(
            ['bash', str(self.action / 'install-trivy.sh')],
            env={**self.env, **env}, text=True, capture_output=True, timeout=15,
        )

    def cache(self):
        directory = self.runner / 'frontend-trivy-download'
        directory.mkdir(exist_ok=True)
        cached = directory / self.archive.name
        shutil.copyfile(self.archive, cached)
        return cached

    def assert_not_installed(self):
        self.assertFalse(self.executed.exists())
        self.assertFalse(self.github_path.exists())

    def test_cold_install_downloads_directly_with_bounded_visible_errors(self):
        result = self.install()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(self.executed.exists())
        self.assertEqual(self.github_path.read_text(), f'{self.report}/trivy-bin\n')
        args, = [json.loads(line) for line in self.calls.read_text().splitlines()]
        self.assertEqual(args[-1], f'https://github.com/aquasecurity/trivy/releases/download/v{VERSION}/{self.archive.name}')
        for option in ('--fail', '--show-error', '--location', '--retry-all-errors'):
            self.assertIn(option, args)
        for option, value in (('--retry', '3'), ('--retry-max-time', '180'), ('--connect-timeout', '15'), ('--max-time', '120'), ('--proto', '=https'), ('--proto-redir', '=https')):
            self.assertEqual(args[args.index(option) + 1], value)

    def test_verified_cache_hit_needs_no_network(self):
        self.cache()
        result = self.install(CURL_FAILURE='1')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(self.calls.exists())
        self.assertTrue(self.executed.exists())

    def test_tampered_cache_is_rejected_before_execution(self):
        self.cache().write_text('tampered archive')
        result = self.install()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('checksum mismatch', result.stdout)
        self.assertFalse(self.calls.exists())
        self.assert_not_installed()

    def test_tampered_download_is_rejected_before_execution(self):
        self.archive.write_text('tampered download')
        result = self.install()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('checksum mismatch', result.stdout)
        self.assert_not_installed()

    def test_connection_failure_is_visible_and_partial_download_is_removed(self):
        result = self.install(CURL_FAILURE='1')
        self.assertEqual(result.returncode, 7)
        self.assertIn('curl: (7) Failed to connect', result.stderr)
        self.assertIn('Unable to download Trivy', result.stdout)
        self.assertEqual(list((self.runner / 'frontend-trivy-download').iterdir()), [])
        self.assert_not_installed()

    def test_unpinned_or_unsupported_targets_fail_without_network(self):
        for env in ({'TRIVY_VERSION': '9.9.9'}, {'RUNNER_OS': 'unknown'}, {'RUNNER_ARCH': 'unknown'}, {'RUNNER_OS': 'Windows', 'RUNNER_ARCH': 'ARM64'}):
            with self.subTest(env=env):
                result = self.install(**env)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn('::error::', result.stdout)
                self.assertFalse(self.calls.exists())
                self.assert_not_installed()

    def test_published_platform_assets_are_selected_and_extracted(self):
        platforms = (
            ('Linux', 'X86', 'Linux-32bit.tar.gz'),
            ('Linux', 'X64', 'Linux-64bit.tar.gz'),
            ('Linux', 'ARM', 'Linux-ARM.tar.gz'),
            ('Linux', 'ARM64', 'Linux-ARM64.tar.gz'),
            ('macOS', 'X64', 'macOS-64bit.tar.gz'),
            ('macOS', 'ARM64', 'macOS-ARM64.tar.gz'),
            ('Windows', 'X64', 'windows-64bit.zip'),
        )
        pins = (ACTION / 'trivy-checksums.txt').read_text()
        for os_name, arch, target in platforms:
            with self.subTest(os=os_name, arch=arch):
                self.archive = self.fixture(target)
                self.assertIn(self.archive.name, pins)
                result = self.install(RUNNER_OS=os_name, RUNNER_ARCH=arch)
                self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == '__main__':
    unittest.main()

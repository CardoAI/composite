import hashlib
import io
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import textwrap
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
stage = 'checksum' if args[-1].endswith('_checksums.txt') else 'archive'
if os.environ.get('CURL_FAILURE') and os.environ.get('CURL_FAILURE_STAGE', stage) == stage:
    output.write_text('partial download')
    status = int(os.environ.get('CURL_STATUS', '7'))
    print(f'curl: ({status}) Download failed', file=sys.stderr)
    sys.exit(status)
shutil.copyfile(os.environ['CHECKSUM_SOURCE' if stage == 'checksum' else 'DOWNLOAD_SOURCE'], output)
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

    def fixture(self, target, version=VERSION):
        asset = f'trivy_{version}_{target}'
        archive = self.root / asset
        executable = 'trivy.exe' if target.endswith('.zip') else 'trivy'
        binary = (
            f'#!{sys.executable}\n'
            'import os, pathlib\n'
            'pathlib.Path(os.environ["INSTALL_EXECUTED"]).touch()\n'
            f'print("Version: {version}")\n'
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
        checksums = self.root / 'remote-checksums.txt'
        checksums.write_text(f'{checksum}  {asset}\n')
        self.env['CHECKSUM_SOURCE'] = str(checksums)
        self.env['DOWNLOAD_SOURCE'] = str(archive)
        return archive

    def install(self, **env):
        return subprocess.run(
            ['bash', str(self.action / 'install-trivy.sh')],
            env={**self.env, **env}, text=True, capture_output=True, timeout=15,
        )

    def prepare(self, version):
        script = re.search(r'(?ms)^      run: \|\n(.*?)\n    - name:', (ACTION / 'action.yaml').read_text()).group(1)
        return subprocess.run(
            ['bash', '-euo', 'pipefail', '-c', textwrap.dedent(script)],
            env={**self.env, 'TRIVY_VERSION': version, 'GITHUB_OUTPUT': str(self.root / 'outputs')},
            text=True, capture_output=True, timeout=15,
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

    def test_prepare_normalizes_explicit_versions_before_cache_selection(self):
        for version in ('0.76.1', 'v0.76.1', '0.77.0', 'v0.77.0'):
            with self.subTest(version=version):
                output = self.root / 'outputs'
                output.unlink(missing_ok=True)
                result = self.prepare(version)
                self.assertEqual(result.returncode, 0, result.stderr)
                values = dict(line.split('=', 1) for line in output.read_text().splitlines())
                self.assertEqual(values['trivy-version'], version.removeprefix('v'))
                self.assertTrue(Path(values['directory']).is_dir())

    def test_invalid_versions_cannot_inject_outputs_or_shell_commands(self):
        payload = f'$(touch "{self.executed}")'
        for version in ('', 'latest', 'main', 'v0.77.0-rc1', '../0.76.1', '0.76.1\ninjected=true', payload):
            with self.subTest(version=version):
                result = self.prepare(version)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn('Trivy version must be a stable release', result.stdout)
                self.assertFalse((self.root / 'outputs').exists())
                self.assertFalse(self.executed.exists())
                self.assertEqual(list(self.runner.iterdir()), [])

    def test_cold_install_downloads_directly_with_bounded_visible_errors(self):
        result = self.install()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(self.executed.exists())
        self.assertEqual(self.github_path.read_text(), f'{self.report}/trivy-bin\n')
        calls = [json.loads(line) for line in self.calls.read_text().splitlines()]
        self.assertEqual([args[-1] for args in calls], [
            f'https://github.com/aquasecurity/trivy/releases/download/v{VERSION}/trivy_{VERSION}_checksums.txt',
            f'https://github.com/aquasecurity/trivy/releases/download/v{VERSION}/{self.archive.name}',
        ])
        for args in calls:
            for option in ('--fail', '--show-error', '--location', '--retry-all-errors'):
                self.assertIn(option, args)
            for option, value in (('--retry', '3'), ('--retry-max-time', '180'), ('--connect-timeout', '15'), ('--max-time', '120'), ('--proto', '=https'), ('--proto-redir', '=https')):
                self.assertEqual(args[args.index(option) + 1], value)

    def test_archive_cache_hit_fetches_fresh_official_checksums(self):
        self.cache()
        result = self.install(CURL_FAILURE='1', CURL_FAILURE_STAGE='archive')
        self.assertEqual(result.returncode, 0, result.stderr)
        calls = [json.loads(line) for line in self.calls.read_text().splitlines()]
        self.assertEqual(len(calls), 1)
        self.assertTrue(calls[0][-1].endswith(f'/trivy_{VERSION}_checksums.txt'))
        self.assertTrue(self.executed.exists())

    def test_tampered_cache_is_rejected_before_execution(self):
        cached = self.cache()
        cached.write_text('tampered archive')
        # A matching attacker-controlled checksum in the archive cache is ignored.
        fake_checksum = hashlib.sha256(cached.read_bytes()).hexdigest()
        (cached.parent / 'trivy-checksums.txt').write_text(f'{fake_checksum}  {cached.name}\n')
        result = self.install()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('checksum mismatch', result.stdout)
        calls = [json.loads(line) for line in self.calls.read_text().splitlines()]
        self.assertEqual(len(calls), 1)
        self.assertTrue(calls[0][-1].endswith('_checksums.txt'))
        self.assert_not_installed()

    def test_tampered_download_is_rejected_before_execution(self):
        self.archive.write_text('tampered download')
        result = self.install()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('checksum mismatch', result.stdout)
        self.assert_not_installed()

    def test_connection_failure_is_visible_and_partial_download_is_removed(self):
        for stage in ('checksum', 'archive'):
            for status in (7, 22):
                with self.subTest(stage=stage, status=status):
                    result = self.install(CURL_FAILURE='1', CURL_FAILURE_STAGE=stage, CURL_STATUS=str(status))
                    self.assertEqual(result.returncode, status)
                    self.assertIn(f'curl: ({status}) Download failed', result.stderr)
                    self.assertIn('Unable to download Trivy', result.stdout)
                    self.assertEqual(list((self.runner / 'frontend-trivy-download').iterdir()), [])
                    self.assertFalse((self.report / 'trivy-checksums.txt.part').exists())
                    self.assert_not_installed()

    def test_invalid_versions_or_platforms_fail_without_network(self):
        for env in ({'TRIVY_VERSION': 'latest'}, {'TRIVY_VERSION': '../0.76.1'}, {'RUNNER_OS': 'unknown'}, {'RUNNER_ARCH': 'unknown'}):
            with self.subTest(env=env):
                result = self.install(**env)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn('::error::', result.stdout)
                self.assertFalse(self.calls.exists())
                self.assert_not_installed()

    def test_missing_invalid_or_duplicate_checksums_stop_before_archive_download(self):
        valid = Path(self.env['CHECKSUM_SOURCE']).read_text()
        for content in ('', valid.replace(self.archive.name, 'different-asset.tar.gz'), f'bad-hash  {self.archive.name}\n', valid + valid):
            with self.subTest(content=content):
                self.calls.unlink(missing_ok=True)
                Path(self.env['CHECKSUM_SOURCE']).write_text(content)
                result = self.install()
                self.assertNotEqual(result.returncode, 0)
                self.assertIn('No valid SHA-256 checksum', result.stdout)
                calls = [json.loads(line) for line in self.calls.read_text().splitlines()]
                self.assertEqual(len(calls), 1)
                self.assertTrue(calls[0][-1].endswith('_checksums.txt'))
                self.assert_not_installed()

    def test_another_release_uses_its_own_archive_and_checksum(self):
        cached_default = self.cache()
        self.archive = self.fixture('Linux-64bit.tar.gz', version='0.76.0')
        result = self.install(TRIVY_VERSION='0.76.0')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('Version: 0.76.0', result.stdout)
        calls = [json.loads(line) for line in self.calls.read_text().splitlines()]
        self.assertEqual(len(calls), 2)
        for args in calls:
            self.assertIn('/v0.76.0/trivy_0.76.0_', args[-1])
        self.assertTrue(cached_default.is_file())

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
        for os_name, arch, target in platforms:
            with self.subTest(os=os_name, arch=arch):
                self.archive = self.fixture(target)
                result = self.install(RUNNER_OS=os_name, RUNNER_ARCH=arch)
                self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == '__main__':
    unittest.main()

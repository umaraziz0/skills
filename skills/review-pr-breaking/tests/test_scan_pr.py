import os
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path
from typing import Dict, Optional

SKILL = Path(__file__).resolve().parents[1]
SCANNER = SKILL / "scan_pr.py"


class ScannerTests(unittest.TestCase):
    def fake_gh(self, directory: Path) -> Path:
        fake = directory / "gh"
        fake.write_text("""#!/usr/bin/env python3
import os, sys
args = sys.argv[1:]
open(os.environ['FAKE_GH_LOG'], 'a').write(' '.join(args) + '\\n')
if args[:2] == ['auth', 'status']:
    sys.exit(0)
if args[:2] == ['pr', 'view']:
    print('{"url": "' + os.environ['FAKE_PR_URL'] + '"}')
    sys.exit(0)
if '--name-only' in args:
    print('src/app.py\\npackage.json\\nservices/api/package.json\\ndocs/notes.txt')
else:
    print('''diff --git a/docs/notes.txt b/docs/notes.txt\n+++ b/docs/notes.txt\n+"not-a-dependency": "secret"\ndiff --git a/services/api/package.json b/services/api/package.json\n+++ b/services/api/package.json\n+  "nested-package": "2.0.0"\ndiff --git a/package.json b/package.json\n+++ b/package.json\n+  "safe-package": "1.0.0"\n+process.env.DEPLOY_TOKEN\n+run `migrate`''')
""")
        fake.chmod(fake.stat().st_mode | stat.S_IXUSR)
        return fake

    def fake_git(self, directory: Path) -> Path:
        fake = directory / "git"
        fake.write_text("""#!/usr/bin/env python3
import os, sys
args = sys.argv[1:]
if args == ['rev-parse', '--show-toplevel']:
    print(os.getcwd())
    sys.exit(0)
if args[-1:] == ['remote']:
    print(os.environ['FAKE_REMOTES'])
    sys.exit(0)
if args[-4:-1] == ['remote', 'get-url', '--all']:
    print(os.environ['FAKE_REMOTE_' + args[-1].upper()])
    sys.exit(0)
sys.exit(1)
""")
        fake.chmod(fake.stat().st_mode | stat.S_IXUSR)
        return fake

    def run_scanner(self, reference: str, config: Optional[str] = None, verified: bool = False,
                    pr_url: str = "https://github.com/owner/repo/pull/7", remotes: Optional[Dict[str, str]] = None):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.fake_gh(root)
            if verified:
                self.fake_git(root)
            if config is not None:
                (root / ".github").mkdir()
                (root / ".github" / "pr-breaking.json").write_text(config)
            log = root / "gh.log"
            remote = pr_url.rsplit("/pull/", 1)[0] + ".git"
            remotes = remotes or {"origin": remote}
            remote_env = {f"FAKE_REMOTE_{name.upper()}": url for name, url in remotes.items()}
            env = os.environ | {"PATH": f"{root}:{os.environ['PATH']}", "FAKE_GH_LOG": str(log), "FAKE_PR_URL": pr_url, "FAKE_REMOTES": "\n".join(remotes), **remote_env}
            result = subprocess.run(["python3", str(SCANNER), reference], cwd=root, env=env, text=True, capture_output=True)
            return result, log.read_text() if log.exists() else ""

    def test_ghe_url_normalizes_and_keeps_raw_content_private(self):
        result, calls = self.run_scanner("https://ghe.example/owner/repo/pull/42", pr_url="https://ghe.example/owner/repo/pull/42")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("safe-package", result.stdout)
        self.assertIn("DEPLOY_TOKEN", result.stdout)
        self.assertNotIn("not-a-dependency", result.stdout)
        self.assertNotIn("secret", result.stdout)
        self.assertNotIn("docs/notes.txt", result.stdout)
        self.assertIn("auth status --hostname ghe.example", calls)
        self.assertIn("pr diff --name-only 42 --repo ghe.example/owner/repo", calls)

    def test_verified_config_extends_registry(self):
        result, _ = self.run_scanner("owner/repo#7", '{"detectors":{"dependency_manifests":{"paths":["docs/*.txt"]}}}', verified=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("not-a-dependency", result.stdout)

    def test_unverified_checkout_config_is_not_applied(self):
        result, _ = self.run_scanner("owner/repo#7", '{"detectors":{"dependency_manifests":{"paths":["docs/*.txt"]}}}')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn("not-a-dependency", result.stdout)

    def test_malformed_verified_config_fails(self):
        result, _ = self.run_scanner("owner/repo#7", '{"detectors":{"scripts":{"enabled":false}}}', verified=True)
        self.assertEqual(result.returncode, 78)
        self.assertIn("configuration is invalid", result.stderr)

    def test_ambiguous_matching_remotes_fail(self):
        result, _ = self.run_scanner("owner/repo#7", verified=True, remotes={"origin": "https://github.com/owner/repo.git", "upstream": "git@github.com:owner/repo.git"})
        self.assertEqual(result.returncode, 78)
        self.assertIn("multiple configured remotes", result.stderr)

    def test_nested_manifest_patch_extracts_identifier(self):
        result, _ = self.run_scanner("owner/repo#7")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("nested-package", result.stdout)

    def test_rejects_unsafe_pr_url(self):
        result, calls = self.run_scanner("https://ghe.example/owner/repo/pull/7?token=no")
        self.assertEqual(result.returncode, 64)
        self.assertNotIn("token=no", result.stderr)
        self.assertEqual(calls, "")


if __name__ == "__main__":
    unittest.main()

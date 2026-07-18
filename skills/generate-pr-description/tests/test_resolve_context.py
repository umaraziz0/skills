import json
import os
import subprocess
import sys
import tempfile
import unittest

SKILL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESOLVER = os.path.join(SKILL, "resolve_context.py")


def run(*args, cwd):
    return subprocess.run(args, cwd=cwd, check=True, text=True,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE)


class ResolveContextTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = self.tmp.name
        run("git", "init", "-q", "-b", "feature", cwd=self.repo)
        run("git", "config", "user.email", "test@example.com", cwd=self.repo)
        run("git", "config", "user.name", "Test", cwd=self.repo)
        with open(os.path.join(self.repo, "readme"), "w") as output:
            output.write("base\n")
        run("git", "add", ".", cwd=self.repo)
        run("git", "commit", "-qm", "base", cwd=self.repo)

    def tearDown(self):
        self.tmp.cleanup()

    def git(self, *args):
        return run("git", *args, cwd=self.repo).stdout.strip()

    def resolve(self, *args):
        output = run(sys.executable, RESOLVER, "--repo", self.repo, *args, cwd=self.repo)
        return json.loads(output.stdout)

    def test_no_base_uses_upstream_remote_head_not_feature_upstream(self):
        self.git("remote", "add", "central", "https://example.invalid/repository.git")
        self.git("update-ref", "refs/remotes/central/feature", "HEAD")
        self.git("update-ref", "refs/remotes/central/trunk", "HEAD")
        self.git("config", "branch.feature.remote", "central")
        self.git("config", "branch.feature.merge", "refs/heads/feature")
        self.git("symbolic-ref", "refs/remotes/central/HEAD", "refs/remotes/central/trunk")
        result = self.resolve()
        self.assertEqual("resolved", result["status"])
        self.assertEqual("refs/remotes/central/trunk", result["base"]["ref"])

    def test_explicit_upstream_uses_feature_upstream(self):
        self.git("remote", "add", "central", "https://example.invalid/repository.git")
        self.git("update-ref", "refs/remotes/central/feature", "HEAD")
        self.git("update-ref", "refs/remotes/central/trunk", "HEAD")
        self.git("config", "branch.feature.remote", "central")
        self.git("config", "branch.feature.merge", "refs/heads/feature")
        self.git("symbolic-ref", "refs/remotes/central/HEAD", "refs/remotes/central/trunk")
        self.assertEqual("refs/remotes/central/feature", self.resolve("upstream")["base"]["ref"])

    def test_simple_branch_ambiguity_requires_selection(self):
        self.git("branch", "main")
        self.git("update-ref", "refs/remotes/origin/main", "HEAD")
        result = self.resolve("main")
        self.assertEqual("selection_required", result["status"])
        self.assertEqual({"refs/heads/main", "refs/remotes/origin/main"},
                         {item["ref"] for item in result["base_candidates"]})

    def test_explicit_remote_branch_is_remote_neutral(self):
        self.git("remote", "add", "central", "https://example.invalid/repository.git")
        self.git("update-ref", "refs/remotes/central/trunk", "HEAD")
        self.assertEqual("refs/remotes/central/trunk", self.resolve("central trunk")["base"]["ref"])
        self.assertEqual("refs/remotes/central/trunk", self.resolve("central/trunk")["base"]["ref"])

    def test_template_directory_multiple_selection_and_symlink_safety(self):
        os.mkdir(os.path.join(self.repo, ".github"))
        os.mkdir(os.path.join(self.repo, ".github", "PULL_REQUEST_TEMPLATE"))
        directory_template = ".github/PULL_REQUEST_TEMPLATE/feature.md"
        with open(os.path.join(self.repo, directory_template), "w") as output:
            output.write("feature")
        os.symlink("/etc/hosts", os.path.join(self.repo, "PULL_REQUEST_TEMPLATE.md"))
        self.assertEqual(directory_template, self.resolve()["template"]["path"])
        with open(os.path.join(self.repo, "docs-template.md"), "w") as output:
            output.write("ignored")
        with open(os.path.join(self.repo, ".github", "pull_request_template.md"), "w") as output:
            output.write("default")
        result = self.resolve()
        self.assertEqual("selection_required", result["template"]["status"])
        self.assertEqual([".github/PULL_REQUEST_TEMPLATE/feature.md", ".github/pull_request_template.md"],
                         result["template"]["candidates"])
        self.assertEqual("Multiple safe PR templates were found; select one template path.",
                         result["template"]["reason"])
        self.assertIn(result["template"]["reason"], result["selection_reasons"])
        self.assertNotIn(None, result["selection_reasons"])
        self.assertEqual(directory_template, self.resolve("--template", directory_template)["template"]["path"])


if __name__ == "__main__":
    unittest.main()

import importlib.util
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


HELPER = Path(__file__).parents[1] / "ssh_helper.py"
SPEC = importlib.util.spec_from_file_location("ssh_helper", HELPER)
assert SPEC is not None
ssh_helper = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = ssh_helper
SPEC.loader.exec_module(ssh_helper)


class EnvSafetyTests(unittest.TestCase):
    def git_untracked(self, *args, **kwargs):
        return subprocess.CompletedProcess(args[0], 1, "", "")

    def test_env_parses_literal_target_values(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(ssh_helper.subprocess, "run", self.git_untracked):
            path = Path(directory, ".env")
            path.write_text('SSH_HOST="prod-app"\nexport SSH_PROD_FOLDER=/srv/app\nIGNORED=value\n')
            if os.name == "posix":
                path.chmod(0o600)
            self.assertEqual(ssh_helper.project_env(directory), {"SSH_HOST": "prod-app", "SSH_PROD_FOLDER": "/srv/app"})

    def test_credentialed_effective_config_uses_confirmed_username_for_match(self):
        output = "hostname example.test\nport 22\nhostkeyalias none\nuserknownhostsfile /tmp/known_hosts\n"
        with patch.object(ssh_helper.subprocess, "run", return_value=subprocess.CompletedProcess([], 0, output, "")) as run:
            effective = ssh_helper.ssh_effective("prod-app", "forge")
        self.assertEqual(effective["hostname"], "example.test")
        self.assertEqual(effective["hostkeyalias"], "example.test")
        self.assertEqual(run.call_args.args[0], ["ssh", "-G", "-l", "forge", "prod-app"])

    def test_tilde_identity_path_expands_before_validation_and_fingerprinting(self):
        with tempfile.TemporaryDirectory() as directory:
            ssh_directory = Path(directory, ".ssh")
            ssh_directory.mkdir()
            key = ssh_directory / "id_ed25519"
            key.write_text("private key")
            if os.name == "posix":
                key.chmod(0o600)
            account = type("Account", (), {"pw_dir": directory})()
            with patch.object(ssh_helper.pwd, "getpwuid", return_value=account):
                identity_file = ssh_helper.validate_credentials("deploy", "~/.ssh/id_ed25519")
            self.assertEqual(identity_file, str(key.resolve()))
            selected = ssh_helper.Target("prod-app", "example.test", "deploy", "22", "example.test", "/srv/app", "/tmp/known_hosts", "laravel", identity_file or "")
            without_identity = ssh_helper.Target("prod-app", "example.test", "deploy", "22", "example.test", "/srv/app", "/tmp/known_hosts", "laravel")
            self.assertNotEqual(ssh_helper.fingerprint(selected), ssh_helper.fingerprint(without_identity))

    def test_tilde_identity_path_rejects_unsafe_suffixes_and_shell_syntax(self):
        with tempfile.TemporaryDirectory() as directory:
            account = type("Account", (), {"pw_dir": directory})()
            invalid = ("~//absolute", "~/./id_ed25519", "~/.ssh/../id_ed25519", "~other/id_ed25519", "$HOME/.ssh/id_ed25519", "~/$HOME/id_ed25519", "~/$(id)", "~/`id`", "~/.ssh/id;whoami")
            with patch.object(ssh_helper.pwd, "getpwuid", return_value=account):
                for identity_file in invalid:
                    with self.subTest(identity_file=identity_file), self.assertRaises(SystemExit):
                        ssh_helper.validate_credentials("deploy", identity_file)

    @unittest.skipUnless(os.name == "posix", "POSIX symlink enforcement")
    def test_tilde_identity_path_rejects_parent_symlink_escaping_home(self):
        with tempfile.TemporaryDirectory() as home, tempfile.TemporaryDirectory() as outside:
            outside_key = Path(outside, "id_ed25519")
            outside_key.write_text("private key")
            outside_key.chmod(0o600)
            os.symlink(outside, Path(home, ".ssh"))
            account = type("Account", (), {"pw_dir": home})()
            with patch.object(ssh_helper.pwd, "getpwuid", return_value=account), self.assertRaises(SystemExit):
                ssh_helper.validate_credentials("deploy", "~/.ssh/id_ed25519")

    @unittest.skipUnless(os.name == "posix", "POSIX permission enforcement")
    def test_env_rejects_group_or_other_permissions(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(ssh_helper.subprocess, "run", self.git_untracked):
            path = Path(directory, ".env")
            path.write_text("SSH_HOST=prod-app\n")
            path.chmod(0o640)
            with self.assertRaises(SystemExit):
                ssh_helper.project_env(directory)

    @unittest.skipUnless(os.name == "posix", "POSIX permission enforcement")
    def test_env_repairs_unsafe_permissions_only_when_explicitly_requested(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(ssh_helper.subprocess, "run", self.git_untracked):
            path = Path(directory, ".env")
            path.write_text("SSH_HOST=prod-app\n")
            path.chmod(0o640)
            self.assertEqual(ssh_helper.project_env(directory, repair_env_permissions=True), {"SSH_HOST": "prod-app"})
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)

    @unittest.skipUnless(os.name == "posix", "POSIX permission enforcement")
    def test_env_repair_failure_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(ssh_helper.subprocess, "run", self.git_untracked):
            path = Path(directory, ".env")
            path.write_text("SSH_HOST=prod-app\n")
            path.chmod(0o640)
            with patch.object(Path, "chmod", side_effect=OSError):
                with self.assertRaises(SystemExit):
                    ssh_helper.project_env(directory, repair_env_permissions=True)

    def test_env_rejects_tracked_or_symlinked_file(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory, ".env")
            path.write_text("SSH_HOST=prod-app\n")
            if os.name == "posix":
                path.chmod(0o600)
            with patch.object(ssh_helper.subprocess, "run", return_value=subprocess.CompletedProcess([], 0, "", "")):
                with self.assertRaises(SystemExit):
                    ssh_helper.project_env(directory)
            path.unlink()
            os.symlink("missing", path)
            with self.assertRaises(SystemExit):
                ssh_helper.project_env(directory)

    @unittest.skipUnless(os.name == "posix", "POSIX permission enforcement")
    def test_env_never_repairs_tracked_file(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory, ".env")
            path.write_text("SSH_HOST=prod-app\n")
            path.chmod(0o640)
            tracked = subprocess.CompletedProcess([], 0, "", "")
            with patch.object(ssh_helper.subprocess, "run", return_value=tracked), patch.object(Path, "chmod") as chmod:
                with self.assertRaises(SystemExit):
                    ssh_helper.project_env(directory, repair_env_permissions=True)
            chmod.assert_not_called()

    def test_target_uses_env_host_folder_and_laravel_profile(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(ssh_helper, "project_root", return_value=directory), patch.object(ssh_helper.subprocess, "run", self.git_untracked), patch.object(ssh_helper, "ssh_effective", return_value={"hostname": "example.test", "user": "deploy", "port": "22", "hostkeyalias": "example.test", "userknownhostsfile": "/tmp/known_hosts"}) as effective:
            path = Path(directory, ".env")
            path.write_text("SSH_HOST=prod-app\nSSH_PROD_FOLDER=/srv/app\n")
            if os.name == "posix":
                path.chmod(0o600)
            selected = ssh_helper.target("prod")
            self.assertEqual((selected.alias, selected.folder, selected.profile), ("prod-app", "/srv/app", "laravel"))
            effective.assert_called_once_with("prod-app", None)

    def test_confirmed_username_overrides_local_config_username(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(ssh_helper, "project_root", return_value=directory), patch.object(ssh_helper.subprocess, "run", self.git_untracked), patch.object(ssh_helper, "ssh_effective", return_value={"hostname": "example.test", "user": "configured-user", "port": "22", "hostkeyalias": "example.test", "userknownhostsfile": "/tmp/known_hosts"}) as effective:
            path = Path(directory, ".env")
            path.write_text("SSH_HOST=prod-app\nSSH_PROD_FOLDER=/srv/app\n")
            if os.name == "posix":
                path.chmod(0o600)
            selected = ssh_helper.target("prod", ssh_user="confirmed-user", identity_file="/Users/test/.ssh/confirmed_key")
            argv = ssh_helper.ssh_argv(selected, "true")
            self.assertEqual(selected.user, "confirmed-user")
            self.assertEqual(argv[argv.index("-l") + 1], "confirmed-user")
            self.assertNotIn("configured-user", argv)
            effective.assert_called_once_with("prod-app", "confirmed-user")

    def test_supplied_identity_file_reaches_ssh_argv_with_identities_only(self):
        selected = ssh_helper.Target("prod-app", "example.test", "deploy", "22", "example.test", "/srv/app", "/tmp/known_hosts", "laravel", "/Users/test/.ssh/deploy_key")
        argv = ssh_helper.ssh_argv(selected, "true")
        self.assertEqual(argv[argv.index("-i") + 1], "/Users/test/.ssh/deploy_key")
        self.assertIn("IdentitiesOnly=yes", argv)
        self.assertIn("IdentityFile=none", argv)
        self.assertIn("IdentityAgent=none", argv)
        self.assertEqual(argv[argv.index("-F") + 1], "/dev/null")
        self.assertEqual(argv[-2], "example.test")

    def test_ssh_output_redacts_confirmed_identity_path(self):
        output = ssh_helper.clean_output(b"Load key /Users/test/.ssh/deploy_key: invalid\n", ("/Users/test/.ssh/deploy_key",))
        self.assertNotIn("/Users/test/.ssh/deploy_key", output)
        self.assertIn("[REDACTED]", output)

    def test_multiple_effective_known_hosts_paths_are_preserved_and_first_is_trust_target(self):
        selected = ssh_helper.Target("prod-app", "example.test", "deploy", "22", "example.test", "/srv/app", "/tmp/known_hosts /tmp/known_hosts2", "laravel", "/Users/test/.ssh/deploy_key")
        argv = ssh_helper.ssh_argv(selected, "true")
        self.assertIn("UserKnownHostsFile=/tmp/known_hosts /tmp/known_hosts2", argv)
        self.assertEqual(ssh_helper.host_key_persistence_target(selected), Path("/tmp/known_hosts"))


class ProfilePolicyTests(unittest.TestCase):
    def test_capabilities_are_complete_enforcement_descriptors(self):
        capabilities = ssh_helper.capability_descriptor("laravel")
        self.assertIn({"argv": ["php", "artisan", "cache:clear"], "confirmation": "required"}, capabilities["operations"])
        tail = next(item for item in capabilities["operations"] if item["argv"][0] == "tail")
        self.assertEqual(tail["line_count"], {"minimum": 1, "maximum": ssh_helper.MAX_LINES})
        self.assertEqual(tail["path_prefix"], "storage/logs/")
        self.assertEqual(capabilities["inspect_env"]["argv"], ["inspect-env", "<variable>", "..."])
        self.assertEqual(capabilities["inspect_config"]["confirmation"], "none")
        self.assertEqual(capabilities["inspect_config"]["safe_keys"], sorted(ssh_helper.LARAVEL_CONFIG_KEYS))
        generic = ssh_helper.capability_descriptor("generic")
        self.assertFalse(generic["inspect_env"]["allowed"])
        self.assertFalse(generic["inspect_config"]["allowed"])
        self.assertFalse(any(item["argv"][0] == "tail" for item in generic["operations"]))

    def test_generic_is_safe_read_only_only(self):
        self.assertEqual(ssh_helper.operation("generic", ["pwd"]), "read-only")
        self.assertEqual(ssh_helper.operation("generic", ["ls", "-la"]), "read-only")
        self.assertIsNone(ssh_helper.operation("generic", ["php", "artisan", "cache:clear"]))
        self.assertIsNone(ssh_helper.operation("generic", ["tail", "-n", "10", "storage/logs/app.log"]))

    def test_laravel_retains_existing_operations(self):
        self.assertEqual(ssh_helper.operation("laravel", ["php", "artisan", "cache:clear"]), "confirmed")
        self.assertEqual(ssh_helper.operation("laravel", ["tail", "-n", "200", "storage/logs/laravel.log"]), "read-only")

    def test_digest_is_stable_and_binds_selection(self):
        base = ssh_helper.Target("app", "example.test", "deploy", "22", "example.test", "/srv/app", "/tmp/known_hosts", "generic")
        laravel = ssh_helper.Target("app", "example.test", "deploy", "22", "example.test", "/srv/app", "/tmp/known_hosts", "laravel")
        changed_host = ssh_helper.Target("app", "other.test", "deploy", "22", "other.test", "/srv/app", "/tmp/known_hosts", "generic")
        changed_alias = ssh_helper.Target("other-app", "example.test", "deploy", "22", "example.test", "/srv/app", "/tmp/known_hosts", "generic")
        changed_known_hosts = ssh_helper.Target("app", "example.test", "deploy", "22", "example.test", "/srv/app", "/tmp/other_known_hosts", "generic")
        changed_identity = ssh_helper.Target("app", "example.test", "deploy", "22", "example.test", "/srv/app", "/tmp/known_hosts", "generic", "/tmp/other_key")
        self.assertEqual(ssh_helper.fingerprint(base), ssh_helper.fingerprint(base))
        self.assertNotEqual(ssh_helper.fingerprint(base), ssh_helper.fingerprint(laravel))
        self.assertNotEqual(ssh_helper.fingerprint(base), ssh_helper.fingerprint(changed_host))
        self.assertNotEqual(ssh_helper.fingerprint(base), ssh_helper.fingerprint(changed_alias))
        self.assertNotEqual(ssh_helper.fingerprint(base), ssh_helper.fingerprint(changed_known_hosts))
        self.assertNotEqual(ssh_helper.fingerprint(base), ssh_helper.fingerprint(changed_identity))


if __name__ == "__main__":
    unittest.main()

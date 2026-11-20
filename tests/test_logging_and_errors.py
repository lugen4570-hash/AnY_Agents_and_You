"""Structured logging, named constants, error hygiene, and build metadata tests."""
import logging
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from bridge import common, web


class LoggingTests(unittest.TestCase):
    def tearDown(self):
        if hasattr(common, "reset_logging"):
            common.reset_logging()

    def test_setup_logging_writes_bridge_log_and_rotates(self):
        with tempfile.TemporaryDirectory() as tmp:
            try:
                logger = common.setup_logging(
                    log_dir=tmp,
                    level=logging.INFO,
                    max_bytes=250,
                    backup_count=2,
                    force=True,
                )
                child = common.get_logger("bridge.test")
                self.assertEqual(logger.name, "bridge")
                for i in range(15):
                    child.info("structured-log-entry-%02d-%s", i, "x" * 30)
                for handler in logger.handlers:
                    handler.flush()
                log_file = Path(tmp) / common.LOG_FILENAME
                backup1 = Path(tmp) / (common.LOG_FILENAME + ".1")
                self.assertTrue(log_file.is_file())
                self.assertTrue(backup1.is_file())
                self.assertFalse((Path(tmp) / "cojam.log").exists())
            finally:
                if hasattr(common, "reset_logging"):
                    common.reset_logging()

    def test_setup_logging_is_idempotent_without_force(self):
        with tempfile.TemporaryDirectory() as tmp:
            try:
                logger = common.setup_logging(log_dir=tmp, force=True)
                count_first = len(logger.handlers)
                common.setup_logging(log_dir=tmp)
                self.assertEqual(len(logger.handlers), count_first)
            finally:
                if hasattr(common, "reset_logging"):
                    common.reset_logging()

    def test_setup_logging_handles_unwritable_directory(self):
        with patch.object(common.os, "makedirs", side_effect=OSError("read only")):
            logger = common.setup_logging(log_dir="Z:/nonexistent", force=True)
            logger.info("should-not-crash")
            self.assertTrue(any(isinstance(h, logging.NullHandler) for h in logger.handlers))

    def test_web_logs_listener_and_shutdown_failures(self):
        with tempfile.TemporaryDirectory() as tmp:
            try:
                common.setup_logging(log_dir=tmp, force=True)
                with patch.object(common, "lan_ipv4", return_value="127.0.0.1"), \
                        patch.object(web, "ExclusiveServer", side_effect=OSError("busy")), \
                        self.assertLogs("bridge.web", level="WARNING") as cm:
                    self.assertEqual(web.start_lan_listener(8766), (None, None))
                self.assertTrue(any("8766" in msg for msg in cm.output))

                bad_room = Mock()
                bad_room.lock = Mock(__enter__=Mock(side_effect=RuntimeError("boom")), __exit__=Mock(return_value=False))
                srv = Mock()
                with patch.object(web.R.rooms, "all", return_value=[bad_room]), \
                        patch.object(web.acp, "stop", side_effect=RuntimeError("acp-fail")), \
                        self.assertLogs("bridge.web", level="WARNING") as cm_stop:
                    web.stop_application(srv)
                self.assertGreaterEqual(len(cm_stop.output), 2)
                srv.shutdown.assert_called_once()
            finally:
                if hasattr(common, "reset_logging"):
                    common.reset_logging()


class ConstantsTests(unittest.TestCase):
    def test_limits_and_cache_bounds_exposed_as_named_constants(self):
        from bridge import acp, members, model_catalog, registry

        self.assertEqual(common.LOG_FILENAME, "bridge.log")
        self.assertEqual(common.LOG_MAX_BYTES, 2 * 1024 * 1024)
        self.assertEqual(common.LOG_BACKUP_COUNT, 3)
        self.assertEqual(members.MAX_ACTIVE_TASKS, 100)
        self.assertEqual(members.MAX_RETAINED_TASKS, 200)
        self.assertEqual(members.MAX_MEMBER_REPLY_BYTES, 48 * 1024)
        self.assertEqual(members.MAX_SESSION_ID_LEN, 200)
        self.assertEqual(model_catalog.MAX_CATALOG_ENTRIES, 128)
        self.assertEqual(registry.SHORTCUT_CACHE_MAX, 128)
        self.assertEqual(acp.STDERR_TAIL_BYTES, 1200)


class ErrorHygieneTests(unittest.TestCase):
    def test_no_unannotated_or_broad_silent_except_pass(self):
        import ast
        import glob

        root = Path(__file__).resolve().parents[1]
        violations = []
        for path in sorted(glob.glob(str(root / "bridge" / "**" / "*.py"), recursive=True)):
            rel = Path(path).relative_to(root).as_posix()
            if rel == "bridge/drivers.py":
                continue  # Pre-existing WIP preserved intentionally.
            src = Path(path).read_text(encoding="utf-8")
            lines = src.splitlines()
            tree = ast.parse(src, rel)
            for node in ast.walk(tree):
                if not isinstance(node, ast.ExceptHandler):
                    continue
                is_bare = node.type is None
                exc_name = ast.unparse(node.type) if node.type else "BARE"
                is_pass = len(node.body) == 1 and isinstance(node.body[0], ast.Pass)
                if is_bare:
                    violations.append(f"{rel}:{node.lineno} bare except")
                elif is_pass and exc_name == "Exception":
                    violations.append(f"{rel}:{node.lineno} silent except Exception: pass")
                elif is_pass:
                    snippet = "\n".join(lines[node.lineno - 1 : node.end_lineno])
                    if "# Expected:" not in snippet:
                        violations.append(f"{rel}:{node.lineno} silent except {exc_name}: pass missing '# Expected:'")
        self.assertEqual(violations, [])

    def test_corrupted_preset_and_native_jsonl_log_diagnostics(self):
        from bridge import discovery, native_session

        with tempfile.TemporaryDirectory() as tmp:
            bad_preset = Path(tmp) / "broken.json"
            bad_preset.write_text("{not json", encoding="utf-8")
            with patch.object(discovery, "PRESET_DIR", tmp), \
                    self.assertLogs("bridge.discovery", level="WARNING"):
                self.assertIsNone(discovery._preset_spec("broken"))

            log_path = Path(tmp) / "sess.jsonl"
            log_path.write_text('{"type":"session_meta","payload":{"cwd":"' + tmp.replace("\\", "/") + '"}}\n{corrupt\n', encoding="utf-8")
            with patch.object(native_session, "locate", return_value=str(log_path)), \
                    self.assertLogs("bridge.native_session", level="DEBUG"), \
                    self.assertRaises(ValueError):
                native_session.prove("codex", "abc", "nonce-1", tmp)


class PackagingCleanupTests(unittest.TestCase):
    def test_unused_npm_residue_removed_and_installer_version_synced(self):
        from bridge.version import VERSION

        root = Path(__file__).resolve().parents[1]
        self.assertFalse((root / "package.json").exists(), "unused package.json should be removed")
        self.assertFalse((root / "package-lock.json").exists(), "unused package-lock.json should be removed")

        iss_text = (root / "packaging" / "cojam.iss").read_text(encoding="utf-8")
        self.assertIn(f'#define MyAppVersion "{VERSION}"', iss_text)
        self.assertIn(f'#define OutputName "Cojam-Setup-{VERSION}-test"', iss_text)
        self.assertIn(f'#define OutputName "Cojam-Setup-{VERSION}"', iss_text)


if __name__ == "__main__":
    unittest.main()

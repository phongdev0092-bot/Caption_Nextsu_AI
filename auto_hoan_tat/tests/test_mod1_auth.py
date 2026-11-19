import json
import os
import tempfile
import unittest
from unittest.mock import MagicMock, patch

import core_login
from auto_hoan_tat.config import AutoHoanTatSettings
from auto_hoan_tat.mod1_auth import (
    FeatureDisabledError,
    ProfileBusyError,
    SessionExpiredError,
    create_inside_session,
)


class _FakeDriver:
    def __init__(self, url="http://inside.fpt.net/default.asp", title="FOX - Hệ thống Thông tin"):
        self.current_url = url
        self.title = title
        self.quit_called = False

    def quit(self):
        self.quit_called = True


class TestMod1Auth(unittest.TestCase):
    def setUp(self):
        core_login.release_inside_task()
        self._tmpdir = tempfile.TemporaryDirectory()
        self._lock_file = os.path.join(self._tmpdir.name, ".inside_profile.lock")

    def tearDown(self):
        core_login.release_inside_task()
        self._tmpdir.cleanup()

    def test_disabled_feature_flag_blocks_execution(self):
        cfg = AutoHoanTatSettings(enabled=False)
        with self.assertRaises(FeatureDisabledError):
            create_inside_session(settings=cfg, lock_file=self._lock_file, check_main_server=False)
        self.assertIsNone(core_login.get_running_inside_task())

    def test_in_process_profile_lock_conflict_raises_busy(self):
        ok, _ = core_login.try_acquire_inside_task("assign")
        self.assertTrue(ok)
        cfg = AutoHoanTatSettings(enabled=True)
        with self.assertRaises(ProfileBusyError):
            create_inside_session(settings=cfg, lock_file=self._lock_file, check_main_server=False)
        # Không làm mất khóa của tác vụ khác
        self.assertEqual(core_login.get_running_inside_task(), "assign")

    def test_cross_process_lock_conflict_raises_busy(self):
        with open(self._lock_file, "w", encoding="utf-8") as f:
            json.dump({"pid": 999999, "owner": "other_proc", "ts": 1.0}, f)

        cfg = AutoHoanTatSettings(enabled=True)
        with patch("auto_hoan_tat.mod1_auth._is_pid_running", return_value=True):
            with self.assertRaises(ProfileBusyError):
                create_inside_session(settings=cfg, lock_file=self._lock_file, check_main_server=False)
        self.assertIsNone(core_login.get_running_inside_task())

    def test_main_server_busy_blocks_profile_collision(self):
        cfg = AutoHoanTatSettings(enabled=True)
        with patch("auto_hoan_tat.mod1_auth._check_main_server_busy", return_value="Phân Công Tay"):
            with self.assertRaises(ProfileBusyError):
                create_inside_session(settings=cfg, lock_file=self._lock_file, check_main_server=True)
        self.assertIsNone(core_login.get_running_inside_task())

    def test_calls_core_login_and_releases_locks_on_close(self):
        fake_driver = _FakeDriver()
        logs = []
        cfg = AutoHoanTatSettings(enabled=True)

        with patch.object(core_login, "create_driver_with_retry", return_value=fake_driver) as mock_drv, \
             patch.object(core_login, "run_fpt_login", return_value=(True, fake_driver.current_url, fake_driver.title)) as mock_login:
            with create_inside_session(
                headless=True,
                log_cb=lambda m, l="info": logs.append((l, m)),
                settings=cfg,
                lock_file=self._lock_file,
                check_main_server=False,
            ) as sess:
                self.assertEqual(core_login.get_running_inside_task(), cfg.task_lock_name)
                self.assertTrue(os.path.exists(self._lock_file))
                self.assertTrue(sess.is_alive())
                sess.ensure_alive()

                # Giả lập phiên hết hạn (bị đẩy về login.fpt.net) -> phải báo SessionExpiredError, KHÔNG gọi lại run_fpt_login
                fake_driver.current_url = "http://login.fpt.net/?urlreturn=inside.fpt.net"
                self.assertFalse(sess.is_alive())
                with self.assertRaises(SessionExpiredError):
                    sess.ensure_alive()

            mock_drv.assert_called_once()
            mock_login.assert_called_once()
            self.assertTrue(fake_driver.quit_called)
            self.assertIsNone(core_login.get_running_inside_task())
            self.assertFalse(os.path.exists(self._lock_file))

    def test_login_failure_quits_driver_and_releases_all_locks(self):
        fake_driver = _FakeDriver()
        cfg = AutoHoanTatSettings(enabled=True)

        with patch.object(core_login, "create_driver_with_retry", return_value=fake_driver), \
             patch.object(core_login, "run_fpt_login", side_effect=RuntimeError("IAM timeout")):
            with self.assertRaises(RuntimeError):
                create_inside_session(settings=cfg, lock_file=self._lock_file, check_main_server=False)

        self.assertTrue(fake_driver.quit_called)
        self.assertIsNone(core_login.get_running_inside_task())
        self.assertFalse(os.path.exists(self._lock_file))


if __name__ == "__main__":
    unittest.main()

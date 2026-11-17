import json
import os
import tempfile
import threading
import unittest
from unittest.mock import patch

os.environ["TESTING"] = "1"

import core_login
import inside_assign
import inside_bypass
import inside_cls
import inside_mybae
import inside_signal
import server


class TestConcurrencyAndSafeguards(unittest.TestCase):
    def setUp(self):
        core_login.release_inside_task()
        self._orig_attempt_file = server.AUTO_ATTEMPT_FILE
        self._tmpdir = tempfile.TemporaryDirectory()
        server.AUTO_ATTEMPT_FILE = os.path.join(self._tmpdir.name, "auto_attempts.json")
        self._orig_cls_cache = dict(server.processed_cls_cache)
        server.processed_cls_cache.clear()
        self._orig_bypass_cache = dict(server.processed_bypass_cache)
        server.processed_bypass_cache.clear()

        for st in (
            server.assign_task_state,
            server.cls_task_state,
            server.bypass_task_state,
            server.clear_signal_task_state,
            server.reset_signal_task_state,
            server.mybae_task_state,
            server.spampool_task_state,
            server.bypass_nat_task_state,
            server.port_task_state,
            server.retrieval_task,
        ):
            st["is_running"] = False
        server.task_state["status"] = "idle"
        with server.radius_task_lock:
            server.radius_sync_busy["active"] = False
        with server.port_task_lock:
            server.port_sync_busy["active"] = False

    def tearDown(self):
        core_login.release_inside_task()
        server.AUTO_ATTEMPT_FILE = self._orig_attempt_file
        server.processed_cls_cache.clear()
        server.processed_cls_cache.update(self._orig_cls_cache)
        server.processed_bypass_cache.clear()
        server.processed_bypass_cache.update(self._orig_bypass_cache)
        with server.radius_task_lock:
            server.radius_sync_busy["active"] = False
        with server.port_task_lock:
            server.port_sync_busy["active"] = False
        self._tmpdir.cleanup()

    def test_inside_signal_automation_close_exists_and_callable(self):
        close_attr = getattr(inside_signal.InsideSignalAutomation, "close", None)
        self.assertTrue(callable(close_attr))
        bot = inside_signal.InsideSignalAutomation(signal_type="clear", headless=True, log_cb=lambda m, l="info": None)
        self.assertTrue(callable(bot.close))
        bot.close()

    def test_try_acquire_and_release_inside_task_exclusivity(self):
        ok1, owner1 = core_login.try_acquire_inside_task("task_alpha")
        self.assertTrue(ok1)
        self.assertEqual(owner1, "task_alpha")
        self.assertEqual(core_login.get_running_inside_task(), "task_alpha")

        ok2, owner2 = core_login.try_acquire_inside_task("task_beta")
        self.assertFalse(ok2)
        self.assertEqual(owner2, "task_alpha")

        # Wrong task name cannot release someone else's lock
        core_login.release_inside_task("task_beta")
        self.assertEqual(core_login.get_running_inside_task(), "task_alpha")

        # Exact owner releases cleanly
        core_login.release_inside_task("task_alpha")
        self.assertIsNone(core_login.get_running_inside_task())

        # Concurrent race: only 1 thread wins
        barrier = threading.Barrier(12)
        winners = []
        win_lock = threading.Lock()

        def racer(idx):
            barrier.wait()
            ok, _ = core_login.try_acquire_inside_task(f"racer_{idx}")
            if ok:
                with win_lock:
                    winners.append(f"racer_{idx}")

        threads = [threading.Thread(target=racer, args=(i,)) for i in range(12)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(len(winners), 1)
        core_login.release_inside_task()

    def test_inside_routes_return_409_when_locked(self):
        ok, _ = core_login.try_acquire_inside_task("busy_holder")
        self.assertTrue(ok)

        routes = [
            ("POST", "/api/login", {}),
            ("POST", "/api/retrieval/run", {}),
            ("GET",  "/api/session/check", None),
            ("POST", "/api/bypass/run", {}),
            ("POST", "/api/cls/run", {}),
            ("POST", "/api/assign/run", {}),
            ("POST", "/api/clear-signal/run", {}),
            ("POST", "/api/reset-signal/run", {}),
            ("POST", "/api/mybae/run", {}),
            ("POST", "/api/auto-import/run", {"dry_run": True}),
        ]
        with server.app.test_client() as client:
            for method, path, payload in routes:
                with self.subTest(path=path):
                    resp = client.get(path) if method == "GET" else client.post(path, json=payload)
                    self.assertEqual(resp.status_code, 409)
                    self.assertEqual(core_login.get_running_inside_task(), "busy_holder")

    def test_empty_pending_returns_200_empty_and_releases_lock(self):
        with server.app.test_client() as client:
            with patch.object(inside_cls, "fetch_sheet_data", return_value={
                "status": "ok",
                "records": [{"SHD": "CLS_DONE_1", "Kết Quả": "Đã xử lý", "Thao Tác": "Cập nhật thành công"}],
            }):
                resp = client.post("/api/cls/run", json={"headless": True})
                self.assertEqual(resp.status_code, 200)
                body = resp.get_json() or {}
                self.assertEqual(body.get("status"), "empty")
                self.assertEqual(body.get("count"), 0)
                self.assertIsNone(core_login.get_running_inside_task())

            with patch.object(inside_assign, "fetch_sheet_data", return_value={
                "status": "ok",
                "records": [{"SHD": "ASG_DONE_1", "Thao Tác": "Cập nhật thành công!"}],
            }):
                resp = client.post("/api/assign/run", json={"headless": True})
                self.assertEqual(resp.status_code, 200)
                body = resp.get_json() or {}
                self.assertEqual(body.get("status"), "empty")
                self.assertEqual(body.get("count"), 0)
                self.assertIsNone(core_login.get_running_inside_task())

            with patch.object(inside_signal, "fetch_sheet_data", return_value={
                "status": "ok",
                "records": [{"SHD": "CLR_DONE_1", "Kết Quả": "Đã xử lý"}],
            }):
                resp = client.post("/api/clear-signal/run", json={"headless": True, "manual": False})
                self.assertEqual(resp.status_code, 200)
                body = resp.get_json() or {}
                self.assertEqual(body.get("status"), "empty")
                self.assertEqual(body.get("count"), 0)
                self.assertIsNone(core_login.get_running_inside_task())

            with patch.object(inside_signal, "fetch_sheet_data", return_value={
                "status": "ok",
                "records": [{"SHD": "RST_DONE_1", "Kết Quả": "Thành công"}],
            }):
                resp = client.post("/api/reset-signal/run", json={"headless": True, "manual": False})
                self.assertEqual(resp.status_code, 200)
                body = resp.get_json() or {}
                self.assertEqual(body.get("status"), "empty")
                self.assertEqual(body.get("count"), 0)
                self.assertIsNone(core_login.get_running_inside_task())

            with patch.object(inside_bypass, "fetch_sheet_data", return_value={
                "status": "ok",
                "records": [{"SHD": "BYP_DONE_1", "Thao Tác": "Đã xử lý"}],
            }):
                resp = client.post("/api/bypass/run", json={"headless": True})
                self.assertEqual(resp.status_code, 400)
                self.assertIsNone(core_login.get_running_inside_task())

            with patch.object(inside_mybae, "fetch_sheet_data", return_value={
                "status": "ok",
                "records": [{"SHD": "MYB_DONE_1", "Kết Quả": "Đã xử lý", "Thao Tác": "Thành công"}],
            }):
                resp = client.post("/api/mybae/run", json={"headless": True})
                self.assertEqual(resp.status_code, 400)
                self.assertIsNone(core_login.get_running_inside_task())

    def test_radius_and_port_sync_busy_return_409(self):
        with server.app.test_client() as client:
            with server.radius_task_lock:
                server.radius_sync_busy["active"] = True
            for path in (
                "/api/spampool/login",
                "/api/spampool/test_single",
                "/api/spampool/start",
                "/api/bypass_nat/login",
                "/api/bypass_nat/test_single",
                "/api/bypass_nat/start",
            ):
                with self.subTest(path=path):
                    self.assertEqual(client.post(path, json={"shd": "SGAXX0001"}).status_code, 409)
            with server.radius_task_lock:
                server.radius_sync_busy["active"] = False

            with server.port_task_lock:
                server.port_sync_busy["active"] = True
            for path in ("/api/port/test_single", "/api/port/start"):
                with self.subTest(path=path):
                    self.assertEqual(client.post(path, json={"shd": "SGAXX0001"}).status_code, 409)

    def test_clear_all_sessions_resets_locks_flags_and_all_profiles(self):
        core_login.try_acquire_inside_task("bypass")
        server.spampool_task_state["is_running"] = True
        server.port_task_state["is_running"] = True
        server.retrieval_task["is_running"] = True
        server.task_state["status"] = "running"

        with patch.object(core_login, "clean_profile_locks_and_orphans") as mock_clean:
            with server.app.test_client() as client:
                resp = client.post("/api/session/clear-all")
                self.assertEqual(resp.status_code, 200)

        self.assertIsNone(core_login.get_running_inside_task())
        self.assertFalse(server.spampool_task_state["is_running"])
        self.assertFalse(server.port_task_state["is_running"])
        self.assertFalse(server.retrieval_task["is_running"])
        self.assertEqual(server.task_state["status"], "idle")
        self.assertEqual(mock_clean.call_count, 3)

    def test_atomic_write_json_10_threads_concurrent(self):
        target_path = os.path.join(self._tmpdir.name, "concurrent_cache.json")
        errors = []
        barrier = threading.Barrier(10)

        def writer(tid):
            try:
                barrier.wait()
                for seq in range(15):
                    core_login.atomic_write_json(target_path, {
                        "thread": tid,
                        "seq": seq,
                        "items": list(range(100)),
                    })
            except Exception as ex:
                errors.append(ex)

        threads = [threading.Thread(target=writer, args=(i,)) for i in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(errors, [])
        with open(target_path, "r", encoding="utf-8") as f:
            parsed = json.load(f)
        self.assertIsInstance(parsed, dict)
        self.assertIn("thread", parsed)
        leftovers = [name for name in os.listdir(self._tmpdir.name) if ".tmp" in name]
        self.assertEqual(leftovers, [])

    def test_testing_mode_does_not_spawn_background_loops(self):
        server.start_background_threads()
        targets = {getattr(t, "_target", None) for t in threading.enumerate()}
        self.assertNotIn(server._log_flusher_loop, targets)
        self.assertNotIn(server._auto_reset_after_clear_loop, targets)
        self.assertNotIn(server._auto_orchestrator_loop, targets)

    def test_auto_overview_and_task_logger_track_live_steps(self):
        server.bypass_task_state["is_running"] = True
        server.bypass_task_state["total"] = 3
        server.bypass_task_state["current_index"] = 0
        server.bypass_task_state["current_shd"] = "SGAAB001"
        task_log = server.make_task_logger(server.bypass_task_state, "bypass", "Auto Bypass")

        task_log("Đang khởi tạo Chrome và đăng nhập IAM...", "info")
        self.assertIn("[Chuẩn bị 3 HĐ]", server.bypass_task_state["message"])
        self.assertEqual(server.bypass_task_state["current_step"], "Đang khởi tạo Chrome và đăng nhập IAM...")

        server.bypass_task_state["current_index"] = 1
        task_log("Đang chọn Nguyên nhân 1 trên popup ByPass...", "info")
        self.assertIn("[1/3 • HĐ SGAAB001]", server.bypass_task_state["message"])
        self.assertEqual(len(server.bypass_task_state["recent_steps"]), 2)

        with server.app.test_client() as client:
            resp = client.get("/api/auto/overview")
            self.assertEqual(resp.status_code, 200)
            body = resp.get_json() or {}
            run = body.get("running") or {}
            self.assertEqual(run.get("tab"), "bypass")
            self.assertEqual(run.get("label"), "Bypass")
            self.assertEqual(run.get("name"), "Bypass")
            self.assertEqual(run.get("current"), 1)
            self.assertEqual(run.get("total"), 3)
            self.assertEqual(run.get("shd"), "SGAAB001")
            self.assertIn("Đang chọn Nguyên nhân 1", run.get("step", ""))
            self.assertEqual(len(run.get("recent_steps") or []), 2)
            logs = body.get("logs") or []
            self.assertTrue(any(l.get("task_id") == "bypass" and l.get("seq", 0) > 0 for l in logs))

    def test_clear_auto_attempts_removes_composite_shd_id_keys(self):
        seed = {
            "assign": {
                "SGAFX5364": 1794877428.0,
                "SGAFX5364_335": 1794877428.0,
                "SGAFY3733_336": 1794877428.0,
                "SGAFY4057_337": 1794877428.0,
            },
            "bypass": {
                "SGA1_10": 1794877428.0,
            },
            "_manual_locked": {
                "clear_signal": {
                    "SGA_LOCKED": {"ts": 1794877000.0, "reason": "login_or_server_error"}
                }
            },
        }
        core_login.atomic_write_json(server.AUTO_ATTEMPT_FILE, seed)

        server.clear_auto_attempts("assign", ["SGAFX5364"])
        with open(server.AUTO_ATTEMPT_FILE, "r", encoding="utf-8") as f:
            after_partial = json.load(f)

        self.assertNotIn("SGAFX5364", after_partial["assign"])
        self.assertNotIn("SGAFX5364_335", after_partial["assign"])
        self.assertIn("SGAFY3733_336", after_partial["assign"])
        self.assertIn("SGAFY4057_337", after_partial["assign"])
        self.assertIn("SGA_LOCKED", after_partial["_manual_locked"]["clear_signal"])

        to_process = [
            {"SHD": "SGAFY3733", "ID": "336"},
            {"SHD": "SGAFY4057", "ID": "337"},
        ]
        server._release_remaining_auto_attempts("assign", to_process, {"SGAFY3733"})
        with open(server.AUTO_ATTEMPT_FILE, "r", encoding="utf-8") as f:
            after_rem = json.load(f)
        self.assertIn("SGAFY3733_336", after_rem["assign"])
        self.assertNotIn("SGAFY4057_337", after_rem["assign"])
        self.assertIn("SGA_LOCKED", after_rem["_manual_locked"]["clear_signal"])

        server.clear_auto_attempts()
        with open(server.AUTO_ATTEMPT_FILE, "r", encoding="utf-8") as f:
            after_full = json.load(f)
        self.assertNotIn("assign", after_full)
        self.assertNotIn("bypass", after_full)
        self.assertIn("SGA_LOCKED", after_full["_manual_locked"]["clear_signal"])

    def test_assign_sheet_data_merges_processed_in_session(self):
        orig_session = list(server.assign_task_state.get("processed_in_session") or [])
        try:
            server.assign_task_state["processed_in_session"] = [{
                "shd": "SGAFX5364",
                "row_id": "335",
                "thao_tac": "Cập nhật thành công!",
                "is_success": True,
                "time": "17/11/2026 08:10:00",
            }]
            mock_sheet = {
                "status": "ok",
                "count": 2,
                "columns": ["ID", "SHD", "Ngày Cập Nhật", "Thao Tác"],
                "col_indices": {"shd": 1, "ngay": 2, "thao_tac": 3},
                "records": [
                    {"ID": "335", "SHD": "SGAFX5364", "Ngày Cập Nhật": "", "Thao Tác": ""},
                    {"ID": "340", "SHD": "SGAFX5364", "Ngày Cập Nhật": "", "Thao Tác": ""},
                ],
            }
            with server.app.test_client() as client:
                with patch.object(inside_assign, "fetch_sheet_data", return_value=mock_sheet):
                    resp = client.get("/api/assign/sheet-data")
                    self.assertEqual(resp.status_code, 200)
                    recs = (resp.get_json() or {}).get("records") or []
                    self.assertEqual(recs[0]["Thao Tác"], "Cập nhật thành công!")
                    self.assertEqual(recs[0]["Ngày Cập Nhật"], "17/11/2026 08:10:00")
                    self.assertEqual(recs[1]["Thao Tác"], "")
        finally:
            server.assign_task_state["processed_in_session"] = orig_session


if __name__ == "__main__":
    unittest.main()

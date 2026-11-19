"""
Unit tests cho giao diện Web độc lập (web_app.py - cổng 5002).
"""

import time
import unittest

from auto_hoan_tat.config import AutoHoanTatSettings
from auto_hoan_tat.orchestrator import BatchRunSummary
from auto_hoan_tat.web_app import create_app


class TestWebApp(unittest.TestCase):
    def setUp(self):
        self.sample_sheet = {
            "status": "ok",
            "columns": ["ID", "Tác Vụ", "SHD", "Kết Quả"],
            "count": 1,
            "records": [
                {
                    "row_id": "1",
                    "tac_vu": "Xác Minh Thông Tin",
                    "shd": "SGAFS1925",
                    "ma_phieu": "SGAFS1925",
                    "loai": "PBT",
                    "tab_dich": "BẢO TRÌ",
                    "loai_ly_do": "",
                    "ket_qua": "",
                    "raw": {},
                }
            ],
        }

    def test_index_and_config_and_sheet_endpoints(self):
        cfg = AutoHoanTatSettings(enabled=True, standalone_port=5002)
        app = create_app(settings=cfg, sheet_fetcher=lambda settings=None: self.sample_sheet)
        client = app.test_client()

        r_home = client.get("/")
        self.assertEqual(r_home.status_code, 200)
        self.assertIn("Auto Hoàn Tất PTC / PBT", r_home.get_data(as_text=True))

        r_cfg = client.get("/api/config").get_json()
        self.assertTrue(r_cfg["enabled"])
        self.assertTrue(r_cfg["dry_run_default"])
        self.assertEqual(r_cfg["standalone_port"], 5002)

        r_sheet = client.get("/api/sheet").get_json()
        self.assertEqual(r_sheet["status"], "ok")
        self.assertEqual(r_sheet["counts"]["total"], 1)
        self.assertEqual(r_sheet["counts"]["pbt"], 1)
        self.assertEqual(r_sheet["records"][0]["shd"], "SGAFS1925")

    def test_run_blocked_when_feature_flag_disabled(self):
        cfg = AutoHoanTatSettings(enabled=False)
        app = create_app(settings=cfg, sheet_fetcher=lambda settings=None: self.sample_sheet)
        client = app.test_client()

        resp = client.post("/api/run", json={"dry_run": True})
        self.assertEqual(resp.status_code, 403)

    def test_run_starts_dry_run_by_default_and_updates_status(self):
        captured = {}

        def _fake_runner(rows, dry_run, headless, settings, stop_event, log_cb, progress_cb):
            captured["dry_run"] = dry_run
            captured["count"] = len(rows)
            rec = {
                "ma_phieu": rows[0]["shd"],
                "status": "DRY_RUN_READY",
                "ket_qua": "DRY-RUN OK",
            }
            progress_cb(1, 1, rec)
            return BatchRunSummary(mode="DRY_RUN", total=1, dry_run_ready=1, results=[rec])

        cfg = AutoHoanTatSettings(enabled=True)
        app = create_app(
            settings=cfg,
            sheet_fetcher=lambda settings=None: self.sample_sheet,
            batch_runner=_fake_runner,
        )
        client = app.test_client()

        resp = client.post("/api/run", json={})
        self.assertEqual(resp.status_code, 200)
        body = resp.get_json()
        self.assertEqual(body["mode"], "DRY_RUN")

        # Chờ worker thread hoàn tất
        for _ in range(30):
            st = client.get("/api/status").get_json()
            if not st["running"]:
                break
            time.sleep(0.05)

        self.assertTrue(captured.get("dry_run"))
        self.assertEqual(captured.get("count"), 1)
        self.assertIn("SGAFS1925", st["results_by_shd"])
        self.assertEqual(st["results_by_shd"]["SGAFS1925"]["status"], "DRY_RUN_READY")


if __name__ == "__main__":
    unittest.main()

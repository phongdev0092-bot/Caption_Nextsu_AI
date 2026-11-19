"""
Unit tests cho Module 4 (mod4_executor.py) và Orchestrator (orchestrator.py).
Đảm bảo:
- DRY-RUN mặc định BẬT và không bấm nút thay đổi dữ liệu.
- Idempotent (bỏ qua phiếu đã hoàn tất).
- Thực thi đủ các bước Điều kiện 3 (Thông tin bảo trì) + Thông tin dịch vụ + Xác nhận + xác minh sau hoàn tất.
- Orchestrator dừng ngay sau N lỗi liên tiếp, ghi audit JSONL và xuất CSV.
"""

from contextlib import contextmanager
import json
import os
import tempfile
import unittest
from unittest.mock import patch

from auto_hoan_tat.config import AutoHoanTatSettings
from auto_hoan_tat.mod1_auth import InsideSession
from auto_hoan_tat.mod2_navigator import NavigationContext
from auto_hoan_tat.mod4_executor import (
    HI_FPT_TARGET,
    MY_BAO_TARGET,
    NGUYEN_NHAN_LOI_TARGET,
    STATUS_DRY_RUN_READY,
    STATUS_ERROR,
    STATUS_NOT_ELIGIBLE,
    STATUS_SKIPPED_ALREADY_DONE,
    STATUS_SUCCESS,
    execute_complete_ticket,
)
from auto_hoan_tat.orchestrator import run_batch


class _FakeDriverExec:
    def __init__(self, post_status: str = "Đã xử lý - 19/11/2026 14:40:00", hi_fpt: str = "Không chọn", my_bao: str = "Không chọn"):
        self.current_url = "https://fox-erp.fpt.net/app/tkbt/bt/ticket?q=test"
        self.current_window_handle = "WIN_FOX"
        self.window_handles = ["WIN_MAIN", "WIN_FOX"]
        self.post_status = post_status
        self.hi_fpt = hi_fpt
        self.my_bao = my_bao
        self.confirmed = False
        self.calls = []
        self.switch_to = self

    def window(self, handle):
        self.current_window_handle = handle

    def close(self):
        pass

    def execute_script(self, script: str, *args):
        if "has_ghi_nhan" in script:
            return {
                "has_ghi_nhan": True,
                "has_phan_cong": True,
                "has_thay_doi_tt": True,
                "ticket_status": self.post_status if self.confirmed else "Đã phân công",
            }
        if "Nguyên nhân chưa cài đặt Hi FPT" in script and "raw:" in script:
            return {"hi_fpt": self.hi_fpt, "my_bao": self.my_bao, "raw": ""}
        if "card: cardTitle" in script:
            self.calls.append(("pencil", args[0]))
            return {"clicked": True, "card": args[0]}
        if "wantLabel" in script:
            self.calls.append(("select_label", args[0], args[1]))
            return {"ok": True, "mode": "native_select", "selected": args[1]}
        if "wantCol" in script:
            self.calls.append(("select_table", args[0], args[1]))
            return {"ok": True, "mode": "native_select", "selected": args[1]}
        if "serviceText" in script:
            self.calls.append(("select_service", args[0]))
            return {"ok": True, "mode": "native_select", "selected": args[0]}
        if "titleKeyword" in script:
            return True
        if "withinModalOnly" in script:
            btn = args[0]
            self.calls.append(("click_btn", btn, args[1]))
            if btn == "Xác nhận":
                self.confirmed = True
            return {"clicked": True, "text": btn.lower()}
        return {}


class TestMod4Executor(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.cfg = AutoHoanTatSettings(
            enabled=True,
            dry_run_default=True,
            rate_limit_sec=0.0,
            max_consecutive_errors=2,
            log_dir=self.tmpdir.name,
        )
        self.driver = _FakeDriverExec()
        self.session = InsideSession(
            driver=self.driver,
            url=self.driver.current_url,
            title="FOX-ERP",
            task_lock_name="auto_hoan_tat",
        )
        self.nav_ctx = NavigationContext(
            shd="SGAFS1925",
            tac_vu="XÁC MINH THÔNG TIN",
            loai="PBT",
            tab_dich="BẢO TRÌ",
            url=self.driver.current_url,
            title="FOX-ERP",
            window_handle="WIN_FOX",
            main_handle="WIN_MAIN",
            adapter=object(),
            ticket_status="Đã phân công",
        )
        self.eligible_val = {
            "ma_phieu": "SGAFS1925",
            "tac_vu": "XÁC MINH THÔNG TIN",
            "loai": "PBT",
            "du_dieu_kien": True,
            "da_hoan_tat": False,
            "ly_do_neu_khong_du": "",
            "chi_tiet": {},
        }

    def tearDown(self):
        self.tmpdir.cleanup()

    def test_dry_run_default_never_clicks_mutating_buttons(self):
        res = execute_complete_ticket(
            session=self.session,
            nav_ctx=self.nav_ctx,
            validation=self.eligible_val,
            settings=self.cfg,
        )
        self.assertEqual(res.mode, "DRY_RUN")
        self.assertEqual(res.status, STATUS_DRY_RUN_READY)
        self.assertEqual(self.driver.calls, [])

    def test_idempotent_skips_already_completed(self):
        done_val = {
            "ma_phieu": "SGAFS1925",
            "tac_vu": "XÁC MINH THÔNG TIN",
            "loai": "PBT",
            "du_dieu_kien": False,
            "da_hoan_tat": True,
            "ly_do_neu_khong_du": "Phiếu đã hoàn tất trước đó.",
            "chi_tiet": {},
        }
        res = execute_complete_ticket(
            session=self.session,
            nav_ctx=self.nav_ctx,
            validation=done_val,
            dry_run=False,
            settings=self.cfg,
        )
        self.assertEqual(res.status, STATUS_SKIPPED_ALREADY_DONE)
        self.assertEqual(self.driver.calls, [])

    def test_not_eligible_returns_exact_reason_without_clicking(self):
        bad_val = {
            "ma_phieu": "SGAFS1925",
            "tac_vu": "XÁC MINH THÔNG TIN",
            "loai": "PBT",
            "du_dieu_kien": False,
            "da_hoan_tat": False,
            "ly_do_neu_khong_du": "Không thành công: Phiếu bảo trì chưa checkin. Vui lòng check in và thử lại",
            "chi_tiet": {},
        }
        res = execute_complete_ticket(
            session=self.session,
            nav_ctx=self.nav_ctx,
            validation=bad_val,
            dry_run=False,
            settings=self.cfg,
        )
        self.assertEqual(res.status, STATUS_NOT_ELIGIBLE)
        self.assertEqual(res.ket_qua, bad_val["ly_do_neu_khong_du"])
        self.assertEqual(self.driver.calls, [])

    def test_real_run_executes_full_flow_and_verifies_post_status(self):
        with patch("auto_hoan_tat.mod4_executor.time.sleep", return_value=None):
            res = execute_complete_ticket(
                session=self.session,
                nav_ctx=self.nav_ctx,
                validation=self.eligible_val,
                dry_run=False,
                settings=self.cfg,
            )
        self.assertEqual(res.mode, "REAL")
        self.assertEqual(res.status, STATUS_SUCCESS)
        self.assertIn("Đã xử lý", res.post_status)
        self.assertIn(("click_btn", "Thay đổi tình trạng", False), self.driver.calls)
        self.assertIn(("click_btn", "Đã xử lý", False), self.driver.calls)
        self.assertIn(("pencil", "Thông tin bảo trì"), self.driver.calls)
        self.assertIn(("select_label", "Nguyên nhân chưa cài đặt Hi FPT", HI_FPT_TARGET), self.driver.calls)
        self.assertIn(("select_label", "Nguyên nhân chưa nghiệm thu Mỹ Bảo", MY_BAO_TARGET), self.driver.calls)
        self.assertIn(("pencil", "Thông tin dịch vụ"), self.driver.calls)
        self.assertIn(("select_service", "Internet"), self.driver.calls)
        self.assertIn(("click_btn", "Thêm", True), self.driver.calls)
        self.assertIn(("select_table", "NGUYÊN NHÂN LỖI", NGUYEN_NHAN_LOI_TARGET), self.driver.calls)
        self.assertIn(("click_btn", "Xác nhận", True), self.driver.calls)

    def test_real_run_fails_if_post_status_not_updated(self):
        import itertools

        self.driver.post_status = "Đã phân công"
        with patch("auto_hoan_tat.mod4_executor.time.sleep", return_value=None), patch(
            "auto_hoan_tat.mod4_executor.time.monotonic",
            side_effect=itertools.count(0.0, 2.0),
        ):
            res = execute_complete_ticket(
                session=self.session,
                nav_ctx=self.nav_ctx,
                validation=self.eligible_val,
                dry_run=False,
                settings=self.cfg,
            )
        self.assertEqual(res.status, STATUS_ERROR)
        self.assertIn("chưa xác minh được trạng thái", res.ket_qua)

    def test_orchestrator_stops_after_n_consecutive_errors_and_exports_audit_and_csv(self):
        rows = [
            {"shd": "SGAERR01", "tac_vu": "XÁC MINH THÔNG TIN", "loai": "PBT", "tab_dich": "BẢO TRÌ", "ket_qua": ""},
            {"shd": "SGAERR02", "tac_vu": "XÁC MINH THÔNG TIN", "loai": "PBT", "tab_dich": "BẢO TRÌ", "ket_qua": ""},
            {"shd": "SGASKIP03", "tac_vu": "XÁC MINH THÔNG TIN", "loai": "PBT", "tab_dich": "BẢO TRÌ", "ket_qua": ""},
        ]

        @contextmanager
        def _fake_session_factory(**kwargs):
            yield self.session

        with patch("auto_hoan_tat.orchestrator._build_assign_adapter", return_value=object()), patch(
            "auto_hoan_tat.orchestrator.navigate_to_ticket",
            side_effect=RuntimeError("Mô phỏng lỗi mạng"),
        ):
            summary = run_batch(
                rows=rows,
                dry_run=True,
                settings=self.cfg,
                session_factory=_fake_session_factory,
            )

        self.assertTrue(summary.stopped_early)
        self.assertEqual(summary.errors, 2)
        self.assertEqual(len(summary.results), 2)  # Dừng trước phiếu thứ 3
        self.assertTrue(os.path.exists(summary.audit_log_path))
        self.assertTrue(os.path.exists(summary.csv_export_path))

        with open(summary.audit_log_path, "r", encoding="utf-8") as f:
            lines = [json.loads(line) for line in f if line.strip()]
        self.assertEqual(len(lines), 2)
        self.assertEqual(lines[0]["ma_phieu"], "SGAERR01")


if __name__ == "__main__":
    unittest.main()

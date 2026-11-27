"""
Unit tests cho Module 4 (mod4_executor.py) và Orchestrator (orchestrator.py)
theo luồng mới trực tiếp trên trang THÔNG TIN BẢO TRÌ (Inside):
- DRY-RUN mặc định BẬT và tuyệt đối không bấm nút thay đổi dữ liệu / không gửi Webhook.
- Idempotent (bỏ qua phiếu đã xử lý).
- Thực thi đủ Bước 4 (Xem thêm), 4a (Mỹ Bảo), 4b (Nguyên nhân lỗi -> Internet -> Thêm),
  4c (4 cột Tình trạng ban đầu / Phần tử lỗi / Nguyên nhân lỗi / Hướng xử lý),
  5 (Kết quả xử lý -> Đã xử lý -> Cập nhật) và xác minh sau hoàn tất.
- Orchestrator dừng ngay sau N lỗi liên tiếp, ghi audit JSONL và xuất CSV có cột Ghi Chú.
"""

from contextlib import contextmanager
import itertools
import json
import os
import tempfile
import unittest
from unittest.mock import patch

from auto_hoan_tat.config import AutoHoanTatSettings
from auto_hoan_tat.mod1_auth import InsideSession
from auto_hoan_tat.mod2_navigator import NavigationContext
from auto_hoan_tat.mod4_executor import (
    DICH_VU_TARGET,
    HUONG_XU_LY_TARGET,
    KET_QUA_XU_LY_TARGET,
    MY_BAO_TARGET,
    NGUYEN_NHAN_LOI_TARGET,
    PHAN_TU_LOI_TARGET,
    STATUS_DRY_RUN_READY,
    STATUS_ERROR,
    STATUS_NOT_ELIGIBLE,
    STATUS_SKIPPED_ALREADY_DONE,
    STATUS_SUCCESS,
    TINH_TRANG_BAN_DAU_TARGET,
    execute_complete_ticket,
)
from auto_hoan_tat.orchestrator import run_batch


class _FakeDriverExec:
    def __init__(self, post_status: str = "Đã xử lý", toast_ok: bool = False):
        self.current_url = "http://inside.fpt.net/bt/checklist?shd=SGAFS1925"
        self.current_window_handle = "WIN_BT"
        self.window_handles = ["WIN_MAIN", "WIN_BT"]
        self.post_status = post_status
        self.toast_ok = toast_ok
        self.updated = False
        self.calls = []
        self.switch_to = self

    def window(self, handle):
        self.current_window_handle = handle

    def close(self):
        pass

    def find_elements(self, *args, **kwargs):
        return []

    def execute_script(self, script: str, *args):
        if "has_tinh_trang_ban_dau" in script:
            return {
                "has_tinh_trang_ban_dau": True,
                "has_lich_su_nhan_nha": True,
                "has_thong_tin_bao_tri": True,
                "ticket_status": self.post_status if self.updated else "Đang xử lý",
            }
        if "already_expanded" in script:
            self.calls.append(("xem_them",))
            return {"already_expanded": False, "clicked": True, "text": "xem thêm"}
        if "wantSec" in script and "wantLabel" in script:
            self.calls.append(("select_label", args[0], args[1], args[2]))
            return {"ok": True, "mode": "native_select", "selected": args[1]}
        if "wantSec" in script and "wantBtn" in script:
            self.calls.append(("click_in_section", args[0], args[1]))
            if args[1] == "Cập nhật":
                self.updated = True
            return {"clicked": True, "text": args[1].lower(), "section": args[0]}
        if "wantCol" in script:
            self.calls.append(("select_table", args[0], args[1]))
            return {"ok": True, "mode": "native_select", "selected": args[1]}
        if "has_success_toast" in script:
            return {"has_success_toast": self.toast_ok}
        if "swal2-popup" in script:
            return False
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
            title="THÔNG TIN BẢO TRÌ",
            task_lock_name="auto_hoan_tat",
        )
        self.nav_ctx = NavigationContext(
            shd="SGAFS1925",
            tac_vu="Xác Minh Thông Tin",
            loai="PBT",
            tab_dich="BẢO TRÌ",
            url=self.driver.current_url,
            title="THÔNG TIN BẢO TRÌ",
            window_handle="WIN_BT",
            main_handle="WIN_MAIN",
            adapter=object(),
            ticket_status="Đang xử lý",
        )
        self.eligible_val = {
            "ma_phieu": "SGAFS1925",
            "tac_vu": "Xác Minh Thông Tin",
            "loai": "PBT",
            "du_dieu_kien": True,
            "da_hoan_tat": False,
            "ket_qua": "",
            "ghi_chu": "",
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
            "tac_vu": "Xác Minh Thông Tin",
            "loai": "PBT",
            "du_dieu_kien": False,
            "da_hoan_tat": True,
            "ket_qua": "Đã xử lý",
            "ghi_chu": "Phiếu đã hoàn tất trước đó.",
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

    def test_not_eligible_returns_ket_qua_and_ghi_chu_without_clicking(self):
        bad_val = {
            "ma_phieu": "SGAFS1925",
            "tac_vu": "Xác Minh Thông Tin",
            "loai": "PBT",
            "du_dieu_kien": False,
            "da_hoan_tat": False,
            "ket_qua": "Không Thành Công",
            "ghi_chu": "Vui lòng check in và thử lại",
            "ly_do_neu_khong_du": "Không Thành Công: Vui lòng check in và thử lại",
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
        self.assertEqual(res.ket_qua, "Không Thành Công")
        self.assertEqual(res.ghi_chu, "Vui lòng check in và thử lại")
        self.assertEqual(self.driver.calls, [])

    def test_real_run_executes_exact_steps_4_and_5_and_verifies_post_status(self):
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
        self.assertEqual(res.ket_qua, "Đã xử lý")
        self.assertIn(("xem_them",), self.driver.calls)
        self.assertIn(("select_label", "Nguyên nhân chưa nghiệm thu Mỹ Bảo", MY_BAO_TARGET, "Thông tin bảo trì"), self.driver.calls)
        self.assertIn(("select_label", "Dịch vụ", DICH_VU_TARGET, "Nguyên nhân lỗi"), self.driver.calls)
        self.assertIn(("click_in_section", "Nguyên nhân lỗi", "Thêm"), self.driver.calls)
        self.assertIn(("select_table", "Tình trạng ban đầu", TINH_TRANG_BAN_DAU_TARGET), self.driver.calls)
        self.assertIn(("select_table", "Phần tử lỗi", PHAN_TU_LOI_TARGET), self.driver.calls)
        self.assertIn(("select_table", "Nguyên nhân lỗi", NGUYEN_NHAN_LOI_TARGET), self.driver.calls)
        self.assertIn(("select_table", "Hướng xử lý", HUONG_XU_LY_TARGET), self.driver.calls)
        self.assertIn(("select_label", "Kết quả xử lý", KET_QUA_XU_LY_TARGET, "Cập nhật kết quả xử lý của phiếu"), self.driver.calls)
        self.assertIn(("click_in_section", "Cập nhật kết quả xử lý của phiếu", "Cập nhật"), self.driver.calls)

    def test_real_run_fails_if_post_status_not_updated(self):
        self.driver.post_status = "Đang xử lý"
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
        self.assertIn("chưa xác minh được trạng thái", res.ghi_chu)

    def test_orchestrator_stops_after_n_consecutive_errors_and_exports_audit_and_csv(self):
        rows = [
            {"shd": "SGAERR01", "tac_vu": "Xác Minh Thông Tin", "loai": "PBT", "tab_dich": "BẢO TRÌ", "ket_qua": "Chưa xử lý"},
            {"shd": "SGAERR02", "tac_vu": "Xác Minh Thông Tin", "loai": "PBT", "tab_dich": "BẢO TRÌ", "ket_qua": "Chưa xử lý"},
            {"shd": "SGASKIP03", "tac_vu": "Xác Minh Thông Tin", "loai": "PBT", "tab_dich": "BẢO TRÌ", "ket_qua": "Chưa xử lý"},
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
        self.assertEqual(len(summary.results), 2)
        self.assertTrue(os.path.exists(summary.audit_log_path))
        self.assertTrue(os.path.exists(summary.csv_export_path))

        with open(summary.csv_export_path, "r", encoding="utf-8-sig") as f:
            csv_text = f.read()
        self.assertIn("Ghi Chú", csv_text)

        with open(summary.audit_log_path, "r", encoding="utf-8") as f:
            lines = [json.loads(line) for line in f if line.strip()]
        self.assertEqual(len(lines), 2)
        self.assertEqual(lines[0]["ma_phieu"], "SGAERR01")


if __name__ == "__main__":
    unittest.main()

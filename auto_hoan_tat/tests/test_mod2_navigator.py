import json
import os
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from inside_assign import InsideAssignAutomation

from auto_hoan_tat.config import AutoHoanTatSettings
from auto_hoan_tat.mod1_auth import FeatureDisabledError, InsideSession, SessionExpiredError
from auto_hoan_tat.mod2_navigator import (
    UnsupportedTicketTypeError,
    WrongPageError,
    navigate_to_ticket,
    open_ticket_readonly,
    probe_ticket,
)


class _FakeDriver:
    def __init__(self, url="http://inside.fpt.net/default.asp", title="FOX Inside"):
        self.current_url = url
        self.title = title
        self.current_window_handle = "win-main"
        self.saved_screenshots = []
        self._iframe_url = "http://inside.fpt.net/tk/reportbacklog"
        self.switch_to = MagicMock()

    def execute_script(self, script, *args):
        if "return window.location.href" in script:
            return self._iframe_url
        if "has_ghi_nhan" in script:
            return {
                "has_ghi_nhan": True,
                "has_phan_cong": True,
                "has_thay_doi_tt": True,
                "has_thong_tin_chung": True,
                "ticket_status": "Đã phân công - 19/11/2026 13:29:37",
            }
        return {
            "url": self.current_url,
            "title": self.title,
            "headings": ["Phiếu Thi Công"],
            "buttons": [{"tag": "button", "text": "Hoàn tất", "id": "btnFinish", "disabled": False, "visible": True}],
            "inputs": [{"tag": "input", "type": "text", "id": "txtNote", "name": "note", "label": "Ghi chú", "placeholder": "", "value": "", "visible": True}],
            "selects": [],
            "status_chips": [{"id": "lblStatus", "cls": "badge", "text": "Đang xử lý"}],
            "iframes": [],
            "body_preview": "Nội dung phiếu thi công",
        }

    def find_elements(self, by, value):
        return []

    def save_screenshot(self, path):
        self.saved_screenshots.append(path)
        with open(path, "wb") as f:
            f.write(b"\x89PNG\r\n\x1a\n")
        return True

    def quit(self):
        pass


class _FakeAssignAdapter:
    """Giả lập InsideAssignAutomation để kiểm tra Module 2 gọi đúng các hàm điều hướng chỉ-đọc."""

    def __init__(self, driver):
        self.driver = driver
        self.main_handle = "win-main"
        self.calls = []

    def navigate_to_assign_page(self):
        self.calls.append("navigate_to_assign_page")

    def _return_to_main_form(self):
        self.calls.append("_return_to_main_form")

    def _click_tab_trien_khai(self):
        self.calls.append("_click_tab_trien_khai")
        self.driver._iframe_url = "http://inside.fpt.net/tk/reportbacklog"

    def _fill_dieu_kien_nhap(self, shd):
        self.calls.append(("_fill_dieu_kien_nhap", shd))

    def _open_ptc_window(self):
        self.calls.append("_open_ptc_window")
        self.driver.current_window_handle = "win-ptc"
        self.driver.current_url = "http://inside.fpt.net/tk/phieuthicong?shd=SGATEST001"
        self.driver.title = "Phiếu Thi Công"

    def _click_tab_bao_tri(self):
        self.calls.append("_click_tab_bao_tri")
        self.driver._iframe_url = "http://inside.fpt.net/bt/reportbacklog"

    def _fill_nhap_hop_dong(self, shd):
        self.calls.append(("_fill_nhap_hop_dong", shd))

    def _open_cl_window(self):
        self.calls.append("_open_cl_window")
        self.driver.current_window_handle = "win-bt"
        self.driver.current_url = "http://inside.fpt.net/bt/checklist?shd=SGATEST002"
        self.driver.title = "Checklist Bảo Trì"


class TestMod2Navigator(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.driver = _FakeDriver()
        self.session = InsideSession(
            driver=self.driver,
            url=self.driver.current_url,
            title=self.driver.title,
            task_lock_name="auto_hoan_tat",
        )
        self.adapter = _FakeAssignAdapter(self.driver)
        self.cfg = AutoHoanTatSettings(enabled=True, probe_output_dir=self._tmpdir.name)

    def tearDown(self):
        self._tmpdir.cleanup()

    def test_disabled_flag_raises(self):
        cfg = AutoHoanTatSettings(enabled=False)
        with self.assertRaises(FeatureDisabledError):
            open_ticket_readonly(self.session, "SGATEST001", "TRIỂN KHAI", settings=cfg, adapter=self.adapter)

    def test_expired_session_raises_without_navigation(self):
        self.driver.current_url = "http://login.fpt.net/?urlreturn=inside.fpt.net"
        with self.assertRaises(SessionExpiredError):
            open_ticket_readonly(self.session, "SGATEST001", "TRIỂN KHAI", settings=self.cfg, adapter=self.adapter)
        self.assertEqual(self.adapter.calls, [])

    def test_unknown_or_empty_tac_vu_raises_without_guessing(self):
        for bad_tv in ("", "   ", "Khảo sát lạ", "PTC"):
            with self.subTest(tac_vu=bad_tv):
                with self.assertRaises(UnsupportedTicketTypeError):
                    open_ticket_readonly(self.session, "SGATEST001", bad_tv, settings=self.cfg, adapter=self.adapter)
        self.assertEqual(self.adapter.calls, [])

    def test_open_ptc_reuses_inside_assign_trien_khai_flow(self):
        ctx = open_ticket_readonly(
            self.session, "SGATEST001", "  triển khai ", settings=self.cfg, adapter=self.adapter
        )
        self.assertEqual(ctx.loai, "PTC")
        self.assertEqual(ctx.tab_dich, "TRIỂN KHAI")
        self.assertEqual(
            self.adapter.calls,
            [
                "navigate_to_assign_page",
                "_click_tab_trien_khai",
                ("_fill_dieu_kien_nhap", "SGATEST001"),
                "_open_ptc_window",
            ],
        )

    def test_open_pbt_bao_tri_and_xac_minh_thong_tin_reuse_bao_tri_flow(self):
        for tv in ("BẢO TRÌ", "  Xác Minh   Thông Tin "):
            with self.subTest(tac_vu=tv):
                self.driver.current_url = "http://inside.fpt.net/default.asp"
                self.adapter.calls.clear()
                ctx = open_ticket_readonly(self.session, "SGATEST002", tv, settings=self.cfg, adapter=self.adapter)
                self.assertEqual(ctx.loai, "PBT")
                self.assertEqual(ctx.tab_dich, "BẢO TRÌ")
                self.assertEqual(
                    self.adapter.calls,
                    [
                        "navigate_to_assign_page",
                        "_click_tab_bao_tri",
                        ("_fill_nhap_hop_dong", "SGATEST002"),
                        "_open_cl_window",
                    ],
                )

    def test_wrong_tab_iframe_raises_wrong_page_error(self):
        def _wrong_click_tk():
            self.adapter.calls.append("_click_tab_trien_khai")
            self.driver._iframe_url = "http://inside.fpt.net/bt/reportbacklog"

        self.adapter._click_tab_trien_khai = _wrong_click_tk
        with self.assertRaises(WrongPageError):
            open_ticket_readonly(self.session, "SGATEST001", "TRIỂN KHAI", settings=self.cfg, adapter=self.adapter)

    def test_wrong_ticket_window_login_redirect_raises(self):
        def _open_login_redirect():
            self.driver.current_url = "http://login.fpt.net/?urlreturn=inside.fpt.net"

        self.adapter._open_ptc_window = _open_login_redirect
        with self.assertRaises(WrongPageError):
            open_ticket_readonly(self.session, "SGATEST001", "TRIỂN KHAI", settings=self.cfg, adapter=self.adapter)

    def test_probe_ticket_saves_screenshot_and_dom_dump_readonly(self):
        res = probe_ticket(
            session=self.session,
            shd="SGATEST001",
            tac_vu="TRIỂN KHAI",
            settings=self.cfg,
            adapter=self.adapter,
        )
        self.assertEqual(res.loai, "PTC")
        self.assertEqual(res.tab_dich, "TRIỂN KHAI")
        self.assertTrue(os.path.exists(res.screenshot_path))
        self.assertTrue(os.path.exists(res.dump_json_path))
        self.assertTrue(os.path.exists(res.dump_txt_path))

        with open(res.dump_json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.assertTrue(data["meta"]["readonly_probe"])
        self.assertEqual(data["meta"]["shd"], "SGATEST001")
        self.assertEqual(res.element_summary["buttons_visible"], 1)
        self.assertEqual(res.element_summary["inputs_visible"], 1)

    def test_navigate_to_ticket_pbt_verifies_markers_and_reads_status(self):
        ctx = navigate_to_ticket(
            session=self.session,
            shd="SGAEQ7509",
            tac_vu="XÁC MINH THÔNG TIN",
            settings=self.cfg,
            adapter=self.adapter,
        )
        self.assertEqual(ctx.loai, "PBT")
        self.assertEqual(ctx.tab_dich, "BẢO TRÌ")
        self.assertIn("Đã phân công", ctx.ticket_status)

    def test_navigate_to_ticket_pbt_missing_markers_raises_wrong_page(self):
        orig_exec = self.driver.execute_script

        def _missing_markers(script, *args):
            if "has_tinh_trang_ban_dau" in script:
                return {
                    "has_tinh_trang_ban_dau": False,
                    "has_lich_su_nhan_nha": False,
                    "has_thong_tin_bao_tri": False,
                    "has_ghi_nhan": False,
                    "has_phan_cong": False,
                    "has_thay_doi_tt": False,
                    "ticket_status": "",
                }
            return orig_exec(script, *args)

        self.driver.execute_script = _missing_markers
        with patch("auto_hoan_tat.mod2_navigator.time.sleep", return_value=None), patch(
            "auto_hoan_tat.mod2_navigator._wait_for_classic_pbt_ready",
            return_value=False,
        ):
            with self.assertRaises(WrongPageError):
                navigate_to_ticket(
                    session=self.session,
                    shd="SGAEQ7509",
                    tac_vu="XÁC MINH THÔNG TIN",
                    settings=self.cfg,
                    adapter=self.adapter,
                )

    def test_stays_on_classic_inside_pbt_without_clicking_fox_erp_banner(self):
        banner_clicked = {"called": False}
        orig_exec = self.driver.execute_script

        def _exec_spy(script, *args):
            if "phiên bản mới" in script:
                banner_clicked["called"] = True
            return orig_exec(script, *args)

        self.driver.execute_script = _exec_spy
        ctx = navigate_to_ticket(
            session=self.session,
            shd="SGAFS1925",
            tac_vu="XÁC MINH THÔNG TIN",
            settings=self.cfg,
            adapter=self.adapter,
        )
        self.assertFalse(banner_clicked["called"])
        self.assertIn("inside.fpt.net", ctx.url)

    def test_contract_inside_assign_methods_exist_and_callable(self):
        """Test hợp đồng: đảm bảo mọi phương thức của InsideAssignAutomation mà Module 2 gọi vẫn tồn tại."""
        required_methods = (
            "navigate_to_assign_page",
            "_return_to_main_form",
            "_click_tab_trien_khai",
            "_fill_dieu_kien_nhap",
            "_open_ptc_window",
            "_click_tab_bao_tri",
            "_fill_nhap_hop_dong",
            "_open_cl_window",
        )
        for method_name in required_methods:
            with self.subTest(method=method_name):
                self.assertTrue(
                    hasattr(InsideAssignAutomation, method_name),
                    f"InsideAssignAutomation bị thiếu phương thức '{method_name}' mà Module 2 đang gọi!",
                )
                self.assertTrue(
                    callable(getattr(InsideAssignAutomation, method_name)),
                    f"InsideAssignAutomation.{method_name} không còn gọi được (not callable)!",
                )


if __name__ == "__main__":
    unittest.main()

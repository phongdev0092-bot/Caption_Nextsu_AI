import unittest
from unittest.mock import patch

from auto_hoan_tat.config import AutoHoanTatSettings
from auto_hoan_tat.mod1_auth import FeatureDisabledError, InsideSession
from auto_hoan_tat.mod2_navigator import NavigationContext
from auto_hoan_tat.mod3_validator import (
    ERR_COND0_INITIAL_NOTE,
    ERR_COND1_NOT_CHECKED_IN,
    GHI_CHU_CHUA_CHECKIN,
    GHI_CHU_SAI_TINH_TRANG_BAN_DAU,
    KET_QUA_KHONG_THANH_CONG,
    REQUIRED_INITIAL_NOTE,
    evaluate_pbt_xac_minh_conditions,
    validate_ticket_readonly,
)


class _FakeValidatorDriver:
    def __init__(self, initial_note="", checkin_values=None):
        self.current_url = "http://inside.fpt.net/bt/checklist?shd=SGAEN6810"
        self.title = "THÔNG TIN BẢO TRÌ"
        self.initial_note = initial_note
        self.checkin_values = checkin_values or []
        self.clicked_buttons = []
        self.closed_popups = 0

    def execute_script(self, script, *args):
        if "tình trạng sự cố ban đầu" in script:
            return {"found_table": True, "values": [self.initial_note], "text": self.initial_note}
        if "thời gian checkin" in script:
            return {"found_table": True, "row_count": max(1, len(self.checkin_values)), "checkin_values": self.checkin_values}
        if "txt === 'đóng'" in script:
            self.closed_popups += 1
            return True
        if args:
            self.clicked_buttons.append(str(args[0]))
            return {"clicked": True, "text": str(args[0])}
        return {}


class TestMod3Validator(unittest.TestCase):
    def test_cond3a_fails_when_initial_status_does_not_match(self):
        res = evaluate_pbt_xac_minh_conditions(
            ma_phieu="SGAEN6810",
            initial_note_text="Có tín hiệu quang nhưng không ổn định / suy hao không đạt chuẩn",
            checkin_values=["27/11/2026 11:51:09"],
        )
        self.assertFalse(res["du_dieu_kien"])
        self.assertFalse(res["da_hoan_tat"])
        self.assertEqual(res["ket_qua"], KET_QUA_KHONG_THANH_CONG)
        self.assertEqual(res["ghi_chu"], GHI_CHU_SAI_TINH_TRANG_BAN_DAU)
        self.assertEqual(res["ly_do_neu_khong_du"], ERR_COND0_INITIAL_NOTE)

    def test_cond3b_fails_when_checkin_empty(self):
        res = evaluate_pbt_xac_minh_conditions(
            ma_phieu="SGAEN6810",
            initial_note_text=REQUIRED_INITIAL_NOTE,
            checkin_values=[],
        )
        self.assertFalse(res["du_dieu_kien"])
        self.assertEqual(res["ket_qua"], KET_QUA_KHONG_THANH_CONG)
        self.assertEqual(res["ghi_chu"], GHI_CHU_CHUA_CHECKIN)
        self.assertEqual(res["ly_do_neu_khong_du"], ERR_COND1_NOT_CHECKED_IN)

    def test_passes_when_both_3a_and_3b_met(self):
        res = evaluate_pbt_xac_minh_conditions(
            ma_phieu="SGAEN6810",
            initial_note_text=REQUIRED_INITIAL_NOTE,
            checkin_values=["27/11/2026 11:51:09"],
            ticket_status="Đang xử lý",
        )
        self.assertTrue(res["du_dieu_kien"])
        self.assertEqual(res["ly_do_neu_khong_du"], "")

    def test_idempotent_skips_already_completed_ticket(self):
        res = evaluate_pbt_xac_minh_conditions(
            ma_phieu="SGAEN6810",
            initial_note_text=REQUIRED_INITIAL_NOTE,
            checkin_values=["27/11/2026 11:51:09"],
            ticket_status="Đã xử lý",
        )
        self.assertFalse(res["du_dieu_kien"])
        self.assertTrue(res["da_hoan_tat"])

    @patch("auto_hoan_tat.mod3_validator.time.sleep", return_value=None)
    def test_validate_ticket_readonly_end_to_end_clicks_lich_su_nhan_nha_tuyen(self, _mock_sleep):
        drv = _FakeValidatorDriver(
            initial_note=REQUIRED_INITIAL_NOTE,
            checkin_values=["27/11/2026 11:51:09"],
        )
        sess = InsideSession(driver=drv, url=drv.current_url, title=drv.title, task_lock_name="auto_hoan_tat")
        ctx = NavigationContext(
            shd="SGAEN6810",
            tac_vu="Xác Minh Thông Tin",
            loai="PBT",
            tab_dich="BẢO TRÌ",
            url=drv.current_url,
            title=drv.title,
            window_handle="win-bt",
            main_handle="win-main",
            adapter=None,
            ticket_status="Đang xử lý",
        )
        res = validate_ticket_readonly(sess, ctx, settings=AutoHoanTatSettings(enabled=True))
        self.assertTrue(res["du_dieu_kien"])
        self.assertEqual(drv.clicked_buttons, ["lịch sử nhận/nhả tuyến"])
        self.assertEqual(drv.closed_popups, 1)

    def test_non_xac_minh_tac_vu_is_rejected_safely(self):
        drv = _FakeValidatorDriver()
        sess = InsideSession(driver=drv, url=drv.current_url, title=drv.title, task_lock_name="auto_hoan_tat")
        ctx = NavigationContext(
            shd="SGATEST001",
            tac_vu="TRIỂN KHAI",
            loai="PTC",
            tab_dich="TRIỂN KHAI",
            url=drv.current_url,
            title=drv.title,
            window_handle="win-ptc",
            main_handle="win-main",
            adapter=None,
        )
        res = validate_ticket_readonly(sess, ctx, settings=AutoHoanTatSettings(enabled=True))
        self.assertFalse(res["du_dieu_kien"])
        self.assertIn("Xác Minh Thông Tin", res["ly_do_neu_khong_du"])
        self.assertEqual(drv.clicked_buttons, [])

    def test_disabled_flag_raises(self):
        drv = _FakeValidatorDriver()
        sess = InsideSession(driver=drv, url=drv.current_url, title=drv.title, task_lock_name="auto_hoan_tat")
        ctx = NavigationContext(
            shd="SGAEN6810",
            tac_vu="Xác Minh Thông Tin",
            loai="PBT",
            tab_dich="BẢO TRÌ",
            url=drv.current_url,
            title=drv.title,
            window_handle="win-bt",
            main_handle="win-main",
            adapter=None,
        )
        with self.assertRaises(FeatureDisabledError):
            validate_ticket_readonly(sess, ctx, settings=AutoHoanTatSettings(enabled=False))


if __name__ == "__main__":
    unittest.main()

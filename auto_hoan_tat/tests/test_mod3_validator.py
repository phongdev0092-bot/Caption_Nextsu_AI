import unittest
from unittest.mock import patch

from auto_hoan_tat.config import AutoHoanTatSettings
from auto_hoan_tat.mod1_auth import FeatureDisabledError, InsideSession
from auto_hoan_tat.mod2_navigator import NavigationContext
from auto_hoan_tat.mod3_validator import (
    ERR_COND0_INITIAL_NOTE,
    ERR_COND1_NOT_CHECKED_IN,
    ERR_COND2_GIUC_TIEN_DO_OPEN,
    REQUIRED_INITIAL_NOTE,
    evaluate_pbt_xac_minh_conditions,
    parse_giuc_tien_do_count,
    validate_ticket_readonly,
)


class _FakeValidatorDriver:
    def __init__(self, initial_note="", checkin_values=None, giuc_btn_text="", giuc_status=""):
        self.current_url = "http://inside.fpt.net/bt/checklist?shd=SGAEQ7509"
        self.title = "Checklist Bảo Trì"
        self.initial_note = initial_note
        self.checkin_values = checkin_values or []
        self.giuc_btn_text = giuc_btn_text
        self.giuc_status = giuc_status
        self.clicked_buttons = []
        self.closed_popups = 0

    def execute_script(self, script, *args):
        if "ghi nhận ban đầu" in script and "headings" in script:
            return self.initial_note
        if "tg checkin" in script:
            return {"found_table": True, "checkin_values": self.checkin_values}
        if "giục tiến độ" in script and "found: true" in script:
            return {"found": bool(self.giuc_btn_text), "text": self.giuc_btn_text}
        if "Kết quả xử lý" in script:
            return {"found": bool(self.giuc_status), "status": self.giuc_status, "raw_text": self.giuc_status}
        if "txt === 'đóng'" in script:
            self.closed_popups += 1
            return True
        if args:
            self.clicked_buttons.append(str(args[0]))
            return {"clicked": True, "text": str(args[0])}
        return {}


class TestMod3Validator(unittest.TestCase):
    def test_parse_giuc_tien_do_count(self):
        self.assertEqual(parse_giuc_tien_do_count("Giục tiến độ (1 lần - Thường)"), 1)
        self.assertEqual(parse_giuc_tien_do_count("Giục tiến độ (3 lần - Khẩn)"), 3)
        self.assertEqual(parse_giuc_tien_do_count("Giục tiến độ (0 lần)"), 0)
        self.assertEqual(parse_giuc_tien_do_count(""), 0)

    def test_cond0_fails_when_initial_note_does_not_match(self):
        res = evaluate_pbt_xac_minh_conditions(
            ma_phieu="SGH587846",
            initial_note_text="Internet • Không có tín hiệu quang (mkn)",
            checkin_values=["19/11/2026 10:48"],
            giuc_count=0,
        )
        self.assertFalse(res["du_dieu_kien"])
        self.assertFalse(res["da_hoan_tat"])
        self.assertEqual(res["ly_do_neu_khong_du"], ERR_COND0_INITIAL_NOTE)

    def test_cond1_fails_when_tg_checkin_empty(self):
        res = evaluate_pbt_xac_minh_conditions(
            ma_phieu="SGH587846",
            initial_note_text=f"Internet • {REQUIRED_INITIAL_NOTE}",
            checkin_values=[],
            giuc_count=0,
        )
        self.assertFalse(res["du_dieu_kien"])
        self.assertEqual(res["ly_do_neu_khong_du"], ERR_COND1_NOT_CHECKED_IN)

    def test_cond2_fails_when_giuc_tien_do_still_dang_xu_ly(self):
        res = evaluate_pbt_xac_minh_conditions(
            ma_phieu="SGH707675",
            initial_note_text=f"Internet • {REQUIRED_INITIAL_NOTE}",
            checkin_values=["19/11/2026 10:48"],
            giuc_count=1,
            giuc_status="Đang xử lý",
        )
        self.assertFalse(res["du_dieu_kien"])
        self.assertEqual(res["ly_do_neu_khong_du"], ERR_COND2_GIUC_TIEN_DO_OPEN)

    def test_passes_when_all_conditions_met_with_giuc_da_xu_ly_or_zero(self):
        res_done = evaluate_pbt_xac_minh_conditions(
            ma_phieu="SGAEQ7509",
            initial_note_text=f"Internet • {REQUIRED_INITIAL_NOTE}",
            checkin_values=["19/11/2026 10:48"],
            giuc_count=1,
            giuc_status="Đã xử lý",
            ticket_status="Đã phân công",
        )
        self.assertTrue(res_done["du_dieu_kien"])
        self.assertEqual(res_done["ly_do_neu_khong_du"], "")

        res_zero = evaluate_pbt_xac_minh_conditions(
            ma_phieu="SGAEQ7509",
            initial_note_text=f"Internet • {REQUIRED_INITIAL_NOTE}",
            checkin_values=["19/11/2026 10:48"],
            giuc_count=0,
            ticket_status="Đã phân công",
        )
        self.assertTrue(res_zero["du_dieu_kien"])

    def test_idempotent_skips_already_completed_ticket(self):
        res = evaluate_pbt_xac_minh_conditions(
            ma_phieu="SGAEQ7509",
            initial_note_text=f"Internet • {REQUIRED_INITIAL_NOTE}",
            checkin_values=["19/11/2026 10:48"],
            giuc_count=0,
            ticket_status="Đã xử lý - 19/11/2026 14:00:00",
        )
        self.assertFalse(res["du_dieu_kien"])
        self.assertTrue(res["da_hoan_tat"])

    @patch("auto_hoan_tat.mod3_validator.time.sleep", return_value=None)
    def test_validate_ticket_readonly_end_to_end_never_mutates(self, _mock_sleep):
        drv = _FakeValidatorDriver(
            initial_note=f"Ghi nhận ban đầu Internet • {REQUIRED_INITIAL_NOTE}",
            checkin_values=["19/11/2026 10:48"],
            giuc_btn_text="Giục tiến độ (1 lần - Thường)",
            giuc_status="Đã xử lý",
        )
        sess = InsideSession(driver=drv, url=drv.current_url, title=drv.title, task_lock_name="auto_hoan_tat")
        ctx = NavigationContext(
            shd="SGAEQ7509",
            tac_vu="XÁC MINH THÔNG TIN",
            loai="PBT",
            tab_dich="BẢO TRÌ",
            url=drv.current_url,
            title=drv.title,
            window_handle="win-bt",
            main_handle="win-main",
            adapter=None,
            ticket_status="Đã phân công",
        )
        res = validate_ticket_readonly(sess, ctx, settings=AutoHoanTatSettings(enabled=True))
        self.assertTrue(res["du_dieu_kien"])
        self.assertEqual(drv.clicked_buttons, ["lịch sử phân công", "giục tiến độ"])
        self.assertEqual(drv.closed_popups, 2)

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
        self.assertIn("XÁC MINH THÔNG TIN", res["ly_do_neu_khong_du"])
        self.assertEqual(drv.clicked_buttons, [])

    def test_disabled_flag_raises(self):
        drv = _FakeValidatorDriver()
        sess = InsideSession(driver=drv, url=drv.current_url, title=drv.title, task_lock_name="auto_hoan_tat")
        ctx = NavigationContext(
            shd="SGAEQ7509",
            tac_vu="XÁC MINH THÔNG TIN",
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

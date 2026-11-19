import os
import unittest
import unicodedata

from auto_hoan_tat.config import AutoHoanTatSettings
from auto_hoan_tat.sheet_reader import (
    classify_ticket_type,
    fetch_sheet_from_file,
    normalize_nfc,
    parse_csv_text,
)

FIXTURE_CSV = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures", "sample_sheet.csv")


class TestSheetReader(unittest.TestCase):
    def test_normalize_nfc_converts_nfd_vietnamese(self):
        nfd_header = unicodedata.normalize("NFD", "Tác Vụ")
        self.assertNotEqual(nfd_header, unicodedata.normalize("NFC", "Tác Vụ"))
        self.assertEqual(normalize_nfc(nfd_header), unicodedata.normalize("NFC", "Tác Vụ"))
        self.assertEqual(normalize_nfc("nan"), "")
        self.assertEqual(normalize_nfc(None), "")

    def test_fixture_csv_parses_14_columns_and_classifies_3_confirmed_types(self):
        res = fetch_sheet_from_file(FIXTURE_CSV)
        self.assertEqual(res["status"], "ok")
        self.assertEqual(res["count"], 5)
        self.assertEqual(len(res["columns"]), 14)
        self.assertIn(unicodedata.normalize("NFC", "Tác Vụ"), res["columns"])

        recs = res["records"]
        # 1. TRIỂN KHAI -> PTC -> tab TRIỂN KHAI
        self.assertEqual(recs[0]["ma_phieu"], "SGATEST001")
        self.assertEqual(recs[0]["loai"], "PTC")
        self.assertEqual(recs[0]["tab_dich"], "TRIỂN KHAI")
        self.assertEqual(recs[0]["loai_ly_do"], "")

        # 2. BẢO TRÌ -> PBT -> tab BẢO TRÌ
        self.assertEqual(recs[1]["ma_phieu"], "SGATEST002")
        self.assertEqual(recs[1]["loai"], "PBT")
        self.assertEqual(recs[1]["tab_dich"], "BẢO TRÌ")
        self.assertEqual(recs[1]["loai_ly_do"], "")

        # 3. XÁC MINH THÔNG TIN (có khoảng trắng thừa + chữ thường) -> PBT -> tab BẢO TRÌ
        self.assertEqual(recs[2]["ma_phieu"], "SGATEST003")
        self.assertEqual(recs[2]["loai"], "PBT")
        self.assertEqual(recs[2]["tab_dich"], "BẢO TRÌ")
        self.assertEqual(recs[2]["ket_qua"], "Đã hoàn tất")

        # 4. Giá trị lạ -> loai=None, tab_dich=None, có lý do rõ ràng, không đoán
        self.assertEqual(recs[3]["ma_phieu"], "SGATEST004")
        self.assertIsNone(recs[3]["loai"])
        self.assertIsNone(recs[3]["tab_dich"])
        self.assertIn("Tác Vụ Lạ", recs[3]["loai_ly_do"])

        # 5. Giá trị rỗng -> loai=None, tab_dich=None, có lý do rõ ràng
        self.assertEqual(recs[4]["ma_phieu"], "SGATEST005")
        self.assertIsNone(recs[4]["loai"])
        self.assertIsNone(recs[4]["tab_dich"])
        self.assertIn("trống", recs[4]["loai_ly_do"].lower())

    def test_nfd_case_and_whitespace_insensitive_matching(self):
        cfg = AutoHoanTatSettings()
        nfd_tk = unicodedata.normalize("NFD", "  triển   khai ")
        nfd_bt = unicodedata.normalize("NFD", "  bảo  trì ")
        nfd_xm = unicodedata.normalize("NFD", " Xác   Minh Thông Tin ")

        self.assertEqual(classify_ticket_type(nfd_tk, cfg.ptc_values, cfg.pbt_values), ("PTC", "TRIỂN KHAI", ""))
        self.assertEqual(classify_ticket_type(nfd_bt, cfg.ptc_values, cfg.pbt_values), ("PBT", "BẢO TRÌ", ""))
        self.assertEqual(classify_ticket_type(nfd_xm, cfg.ptc_values, cfg.pbt_values), ("PBT", "BẢO TRÌ", ""))

        # Giá trị khác không được đoán
        loai, tab, reason = classify_ticket_type("PTC", cfg.ptc_values, cfg.pbt_values)
        self.assertIsNone(loai)
        self.assertIsNone(tab)
        self.assertTrue(reason)

    def test_parse_csv_text_handles_quoted_location(self):
        csv_text = (
            '"ID","Ta\u0301c Vu\u0323","Email","MSNV","Account Inside","SHD","Nguyên Nhân",'
            '"Hình ảnh","Ngày Cập Nhật","Kết Quả","Location","Address of Location","Địa chỉ KH","Đánh Giá Xác Thực"\n'
            '"10","TRIỂN KHAI","a@fpt.net","123","PNC01.A","SGAB9999","Lý do","https://img","","","10.8, 106.7","ĐC GPS","ĐC KH","Đạt"\n'
        )
        res = parse_csv_text(csv_text)
        self.assertEqual(res["count"], 1)
        r = res["records"][0]
        self.assertEqual(r["row_id"], "10")
        self.assertEqual(r["loai"], "PTC")
        self.assertEqual(r["tab_dich"], "TRIỂN KHAI")
        self.assertEqual(r["location"], "10.8, 106.7")
        self.assertEqual(r["address_of_location"], "ĐC GPS")
        self.assertEqual(r["dia_chi_kh"], "ĐC KH")
        self.assertEqual(r["danh_gia_xac_thuc"], "Đạt")


if __name__ == "__main__":
    unittest.main()

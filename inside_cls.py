import os
import sys
import time
import re
import unicodedata
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options

import core_login

DEFAULT_SHEET_ID = "1Sw-qSbLzvVdcW4rj7ywEZBEzKI6w5M82EQeYJUpdx7M"
GID_CLEAR_CLS = "987552880"

def normalize_nfc(text):
    if text is None:
        return ""
    return unicodedata.normalize('NFC', str(text)).strip()

def norm_lower(text):
    return normalize_nfc(text).lower()

def remove_accents(text):
    if text is None:
        return ""
    nfkd = unicodedata.normalize('NFD', str(text))
    no_tone = "".join([c for c in nfkd if unicodedata.category(c) != 'Mn'])
    return no_tone.replace("đ", "d").replace("Đ", "D").lower().strip()

def format_cls_thao_tac(tinh_trang, noi_dung):
    """
    Quy tắc chuẩn hóa kết quả Thao Tác cho Clear Cls:
    - Nếu thành công: 'Cập nhật thành công!'
    - Nếu không thành công: 'Không thành công : [Lý do]'
    """
    tt_lower = norm_lower(tinh_trang)
    nd_lower = norm_lower(noi_dung)

    # 1. Nhận diện THẤT BẠI trước nếu có từ khóa lỗi/từ chối rõ ràng
    has_explicit_fail = (
        "không thành công" in tt_lower or
        "thất bại" in tt_lower or
        "lỗi" in tt_lower or
        "không thành công" in nd_lower or
        "không tìm thấy" in nd_lower or
        "không có phiếu" in nd_lower or
        "từ chối" in nd_lower
    )

    # 2. Nhận diện THÀNH CÔNG:
    has_success_sign = (
        "cập nhật thành công" in nd_lower or
        ("thành công" in nd_lower and "không" not in nd_lower) or
        ("thành công" in tt_lower and "không" not in tt_lower) or
        ("đã đóng" in tt_lower and not has_explicit_fail) or
        ("hoàn tất" in tt_lower and not has_explicit_fail)
    )

    if has_success_sign and not has_explicit_fail:
        return True, "Cập nhật thành công!"

    # 3. Chuẩn hóa chuỗi lý do khi THẤT BẠI:
    detail = str(noi_dung or "").strip() or str(tinh_trang or "").strip()
    if not detail or norm_lower(detail) in ["không thành công", "thất bại", "lỗi", "đóng phiếu lỗi"]:
        detail = "Không tìm thấy phiếu tồn Bảo trì"

    # Lược bỏ tiền tố 'Không thành công :' nếu trong detail đã có sẵn để tránh bị lặp chuỗi
    clean_detail = re.sub(r"^không\s+thành\s+công\s*[:\-]?", "", detail, flags=re.IGNORECASE).strip()
    if not clean_detail:
        clean_detail = "Không tìm thấy phiếu tồn Bảo trì"

    return False, f"Không thành công : {clean_detail}"

def fetch_sheet_data(sheet_id=DEFAULT_SHEET_ID, gid=GID_CLEAR_CLS):
    """
    Đọc dữ liệu bảng tính Google Sheet Clear Cls có SR (GID 987552880).
    Cấu trúc sheet: ID | Tác Vụ | Email | MSNV | Account Inside | SHD | Nguyên Nhân 1 | Ngày Cập Nhật | Kết Quả | Thao Tác
    """
    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&gid={gid}&_t={int(time.time() * 1000)}"
    try:
        df = pd.read_csv(url, encoding="utf-8")
        df = df.fillna("")

        col_indices = {}
        for idx, c in enumerate(df.columns):
            c_no = remove_accents(c)
            if c_no == "shd" or "hop dong" in c_no:
                col_indices["shd"] = idx
            elif "thao tac" in c_no or "ghi chu" in c_no:
                col_indices["thao_tac"] = idx
            elif "ket qua" in c_no or "tinh trang" in c_no or "trang thai" in c_no:
                col_indices["ket_qua"] = idx
            elif "ngay" in c_no or "thoi gian" in c_no:
                col_indices["ngay"] = idx

        standard_records = []
        for raw in df.to_dict(orient="records"):
            rec = {}
            for k, v in raw.items():
                norm_k = normalize_nfc(k)
                norm_v = normalize_nfc(v) if isinstance(v, str) else str(v)
                rec[norm_k] = norm_v

                k_no = remove_accents(k)
                if k_no == "shd" or "hop dong" in k_no:
                    rec["SHD"] = norm_v
                elif "email" in k_no or "nvkt" in k_no:
                    rec["Email"] = norm_v
                elif "tac vu" in k_no:
                    rec["Tác Vụ"] = norm_v
                elif "nguyen nhan 1" in k_no or "nguyen nhan" in k_no or "ly do" in k_no:
                    rec["Nguyên Nhân 1"] = norm_v
                elif "ngay" in k_no or "thoi gian" in k_no:
                    rec["Ngày Cập Nhật"] = norm_v
                elif "ket qua" in k_no:
                    rec["Kết Quả"] = norm_v
                elif "thao tac" in k_no or "ghi chu" in k_no:
                    rec["Thao Tác"] = norm_v
                elif "msnv" in k_no:
                    rec["MSNV"] = norm_v
                elif "account" in k_no:
                    rec["Account Inside"] = norm_v
                elif k_no == "id":
                    rec["ID"] = norm_v

            standard_records.append(rec)

        cols = [normalize_nfc(c) for c in df.columns]
        return {
            "status": "ok",
            "count": len(standard_records),
            "columns": cols,
            "col_indices": col_indices,
            "records": standard_records
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Không thể đọc Google Sheet Clear Cls: {e}",
            "records": []
        }

class InsideClearClsAutomation:
    def __init__(self, headless=False, keep_open=True, log_cb=None):
        self.headless = headless
        self.keep_open = keep_open
        self.log_cb = log_cb or self._default_log
        self.driver = None

    def _default_log(self, msg, level="info"):
        try:
            print(f"[{level.upper()}] {msg}")
        except Exception:
            pass

    def log(self, msg, level="info"):
        try:
            self.log_cb(msg, level)
        except Exception:
            pass

    def init_driver(self):
        mode_str = "Chạy ngầm (Headless)" if self.headless else "Hiển thị trực tiếp (Visible)"
        self.log(f"Khởi tạo trình duyệt Chrome phiên Inside FPT ({mode_str})...", "info")
        self.driver = core_login.create_driver_with_retry(
            headless=self.headless,
            keep_open=self.keep_open,
            max_retries=2,
            log_cb=self.log_cb
        )
        return self.driver

    def _perform_auto_login(self):
        """Tự động đăng nhập: ưu tiên form trong Frame 1 nếu đang hiển thị, hoặc SSO login.fpt.net."""
        cfg = core_login.load_config()
        acc = core_login.get_active_account_info(cfg)

        # 1. Kiểm tra xem Frame 1 có form đăng nhập (như khi phiên hết hạn bên trong Inside)
        self.driver.switch_to.default_content()
        in_frame1 = False
        try:
            self.driver.switch_to.frame(1)
            if len(self.driver.find_elements(By.ID, "fUserName")) > 0 or len(self.driver.find_elements(By.ID, "fPassword")) > 0:
                in_frame1 = True
        except Exception:
            pass

        if in_frame1:
            self.log("Phát hiện form đăng nhập trong Frame 1. Đang tự động điền mật khẩu và mã OTP...", "info")
            try:
                u_elems = self.driver.find_elements(By.ID, "fUserName")
                if u_elems:
                    u_elems[0].clear()
                    u_elems[0].send_keys(acc["username"])

                p_elems = self.driver.find_elements(By.ID, "fPassword")
                if p_elems:
                    p_elems[0].clear()
                    p_elems[0].send_keys(acc["password"])

                cb = self.driver.find_elements(By.ID, "cbOTP")
                if cb and not cb[0].is_selected():
                    try:
                        cb[0].click()
                    except Exception:
                        self.driver.execute_script("arguments[0].click();", cb[0])

                self.driver.execute_script("""
                    var sp = document.getElementById('spOTP');
                    if (sp) sp.style.display = 'inline-block';
                    var cb = document.getElementById('cbOTP');
                    if (cb) cb.checked = true;
                """)

                otp_inps = self.driver.find_elements(By.ID, "fOTP")
                if otp_inps and acc.get("totp_secret"):
                    import pyotp
                    totp = pyotp.TOTP(acc["totp_secret"].strip().replace(" ", "").upper())
                    code = totp.now()
                    self.log(f"Đã tạo mã OTP tự động: {code}", "info")
                    otp_inps[0].clear()
                    otp_inps[0].send_keys(code)

                btn_login = self.driver.find_elements(
                    By.XPATH,
                    "//a[contains(., 'ĐĂNG NHẬP') and not(contains(., 'IAM'))] | "
                    "//button[contains(., 'ĐĂNG NHẬP') and not(contains(., 'IAM'))] | "
                    "//input[contains(@value, 'ĐĂNG NHẬP')]"
                )
                if btn_login:
                    self.log("Nhấn nút [ĐĂNG NHẬP] trong Frame 1...", "info")
                    self.driver.execute_script("arguments[0].click();", btn_login[0])
                    time.sleep(3.5)
                    self.driver.switch_to.default_content()
                    self.log("Đã hoàn tất đăng nhập Frame 1!", "success")
                    return True
            except Exception as e_frame:
                self.log(f"Đăng nhập Frame 1 gặp lỗi ({e_frame}), chuyển sang đăng nhập SSO chuẩn...", "warning")

        # 2. Đăng nhập chuẩn qua login.fpt.net
        self.driver.switch_to.default_content()
        try:
            self.driver.delete_all_cookies()
            self.log("Đã dọn dẹp cookie phiên cũ để làm mới.", "info")
        except Exception:
            pass

        core_login.run_fpt_login(
            driver=self.driver,
            username=acc["username"],
            password=acc["password"],
            secret=acc.get("totp_secret", ""),
            use_otp=acc.get("use_otp", False),
            log_callback=self.log_cb
        )
        time.sleep(1.5)
        self.driver.get("http://inside.fpt.net/default.asp")
        time.sleep(2)
        return True

    def check_and_ensure_login(self):
        """Luôn luôn tiến hành đăng nhập sạch 100% từ đầu qua SSO login.fpt.net."""
        self.log("Tiến hành đăng nhập mới từ đầu vào Inside FPT...", "info")
        cfg = core_login.load_config()
        acc = core_login.get_active_account_info(cfg)
        core_login.run_fpt_login(
            driver=self.driver,
            username=acc["username"],
            password=acc["password"],
            secret=acc.get("totp_secret", ""),
            use_otp=acc.get("use_otp", False),
            log_callback=self.log_cb
        )
        self.driver.switch_to.default_content()
        self.log("Phiên đăng nhập Inside FPT mới đã sẵn sàng!", "success")

    def close(self):
        """Khi hoàn tất 1 tác vụ: Đóng trình duyệt (nếu _session_broken thì xóa sạch phiên lỗi)."""
        if self.driver:
            if getattr(self, "_session_broken", False):
                self.log("Phát hiện phiên có lỗi giao diện/đăng nhập -> Hủy phiên để lần sau đăng nhập mới sạch 100%.", "warning")
                try:
                    self.driver.quit()
                except Exception:
                    pass
                core_login.invalidate_session(log_cb=self.log_cb)
            else:
                self.log("Hoàn tất tác vụ: Đang đóng trình duyệt và xóa sạch toàn bộ session cũ...", "info")
                core_login.close_driver_and_clear_session(self.driver, log_cb=self.log_cb)
            self.driver = None

    def navigate_to_general_info_page(self):
        """
        Dùng chung cho nhiều chức năng Auto:
        Đăng nhập >> Inside New V5 >> Hỗ trợ kỹ thuật >> Thông tin chung (kết thúc ở Frame 1 nội dung).
        """
        self.log("Đang điều hướng: Inside New V5 >> Thông tin chung...", "info")
        self.check_and_ensure_login()

        self.driver.switch_to.default_content()
        wait = WebDriverWait(self.driver, 25)

        # 1. Chuyển vào Frame menu bên trái (Frame 0)
        try:
            wait.until(EC.frame_to_be_available_and_switch_to_it(0))
        except Exception:
            self.driver.get("http://inside.fpt.net/default.asp")
            time.sleep(3)
            self.driver.switch_to.default_content()
            wait.until(EC.frame_to_be_available_and_switch_to_it(0))

        time.sleep(1)

        # 2. Mở rộng menu: Inside New -> Inside New V5 -> Hỗ trợ kỹ thuật -> Thông tin chung
        self.log("Đang mở menu cây: Inside New >> Inside New V5 >> Hỗ trợ kỹ thuật...", "info")

        # 2.1. Mở rộng 'Inside New' nếu đang đóng (hình plus.gif)
        inside_new_links = self.driver.find_elements(By.XPATH, "//a[@data-english-name='Inside New']")
        if inside_new_links:
            img_in = inside_new_links[0].find_elements(By.XPATH, ".//img")
            if img_in and "plus.gif" in img_in[0].get_attribute("src"):
                self.log("Mở rộng mục 'Inside New'...", "info")
                self.driver.execute_script("arguments[0].scrollIntoView(true);", inside_new_links[0])
                self.driver.execute_script("arguments[0].click();", inside_new_links[0])
                time.sleep(1)

        # 2.2. Nhấp mở 'Inside New V5' nếu đang đóng (hình plus.gif)
        v5_nodes = self.driver.find_elements(By.XPATH, "//a[@data-english-name='Inside New V5']")
        if not v5_nodes:
            v5_nodes = self.driver.find_elements(By.XPATH, "//a[contains(., 'Inside New V5')]")

        if not v5_nodes:
            raise RuntimeError("Không tìm thấy mục 'Inside New V5' trên menu!")

        v5_elem = v5_nodes[0]
        v5_img = v5_elem.find_elements(By.XPATH, ".//img")
        if v5_img and "plus.gif" in v5_img[0].get_attribute("src"):
            self.log("Nhấp mở mục 'Inside New V5'...", "info")
            self.driver.execute_script("arguments[0].scrollIntoView(true);", v5_elem)
            self.driver.execute_script("arguments[0].click();", v5_elem)
            time.sleep(1)
        else:
            self.log("Mục 'Inside New V5' đã mở sẵn.", "info")

        # 2.3. Nhấp mở 'Hỗ trợ kỹ thuật' thuộc Inside New V5 nếu đang đóng
        ho_tro = None
        try:
            v5_li = v5_elem.find_element(By.XPATH, "./ancestor::li[1]")
            ho_tro = v5_li.find_element(By.XPATH, ".//a[@data-english-name='Ho tro ky thuat']")
        except Exception:
            ho_tro_list = self.driver.find_elements(By.XPATH, "//li[contains(@id, '1000016473')]//a | //a[@data-english-name='Ho tro ky thuat']")
            ho_tro = ho_tro_list[-1] if ho_tro_list else None

        if ho_tro:
            ht_img = ho_tro.find_elements(By.XPATH, ".//img")
            if ht_img and "plus.gif" in ht_img[0].get_attribute("src"):
                self.log("Nhấp mở 'Hỗ trợ kỹ thuật' (Inside New V5)...", "info")
                self.driver.execute_script("arguments[0].scrollIntoView(true);", ho_tro)
                self.driver.execute_script("arguments[0].click();", ho_tro)
                time.sleep(1)
            else:
                self.log("Mục 'Hỗ trợ kỹ thuật' đã mở sẵn.", "info")

        # 2.4. Nhấp chọn 'Thông tin chung' thuộc Inside New V5
        tt_elem = None
        try:
            v5_li = v5_elem.find_element(By.XPATH, "./ancestor::li[1]")
            tt_elem = v5_li.find_element(By.XPATH, ".//a[@data-english-name='Thong tin chung']")
        except Exception:
            pass

        if not tt_elem:
            tt_list = self.driver.find_elements(By.XPATH, "//li[contains(@id, '1000016483')]//a | //a[@data-english-name='Thong tin chung']")
            if tt_list:
                tt_elem = tt_list[-1]

        if not tt_elem:
            raise RuntimeError("Không tìm thấy mục 'Thông tin chung' trên menu cây Inside!")

        self.log("Đã tìm thấy 'Thông tin chung'! Tiến hành mở trang...", "info")
        self.driver.execute_script("arguments[0].scrollIntoView(true);", tt_elem)
        self.driver.execute_script("arguments[0].click();", tt_elem)
        time.sleep(3)

        # 3. Chuyển sang Frame Content (Frame 1)
        self.driver.switch_to.default_content()
        wait.until(EC.frame_to_be_available_and_switch_to_it(1))
        self.log("Đã chuyển vào trang Thông tin chung (Frame 1).", "info")
        time.sleep(2)

        # Kiểm tra xem Frame 1 có bị yêu cầu đăng nhập lại không
        if len(self.driver.find_elements(By.ID, "fUserName")) > 0 or len(self.driver.find_elements(By.ID, "fPassword")) > 0:
            self.log("Phát hiện phiên Frame 1 yêu cầu xác thực (form đăng nhập). Đang tự động đăng nhập...", "warning")
            self._perform_auto_login()
            # Mở lại Thông tin chung sau khi đăng nhập thành công
            self.driver.switch_to.default_content()
            wait.until(EC.frame_to_be_available_and_switch_to_it(0))
            if tt_elem:
                self.driver.execute_script("arguments[0].click();", tt_elem)
                time.sleep(3)
            self.driver.switch_to.default_content()
            wait.until(EC.frame_to_be_available_and_switch_to_it(1))
            time.sleep(2)

    def navigate_to_clear_cls_page(self):
        """
        Điều hướng theo đúng yêu cầu:
        Inside New V5 >> Thông tin chung >> bấm qua tag Chức Năng Khác >> Đóng Bảo Trì (close-checklists)
        """
        self.navigate_to_general_info_page()

        # 4. Tìm và bấm tab 'CHỨC NĂNG KHÁC'
        self.log("Đang chuyển sang tab 'Chức Năng Khác'...", "info")
        tab_other = None
        for _ in range(15):
            elements = self.driver.find_elements(By.XPATH, "//*[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'chức năng khác')]")
            if elements:
                tab_other = elements[0]
                break
            time.sleep(1)

        if not tab_other:
            raise RuntimeError("Không tìm thấy tab 'Chức Năng Khác' trên trang Thông Tin Chung!")

        self.driver.execute_script("arguments[0].scrollIntoView(true);", tab_other)
        self.driver.execute_script("arguments[0].click();", tab_other)
        time.sleep(3)

        # 5. Chuyển vào iframe con 'close-checklists' (Đóng bảo trì)
        self.log("Đang chuyển vào khung con Đóng Bảo Trì (close-checklists)...", "info")
        target_iframe = None
        for _ in range(15):
            iframes = self.driver.find_elements(By.XPATH, "//iframe[contains(@src, 'close-checklists')]")
            if iframes:
                target_iframe = iframes[0]
                break
            time.sleep(1)

        if not target_iframe:
            raise RuntimeError("Không tìm thấy iframe chức năng Đóng Bảo Trì (close-checklists)!")

        self.driver.switch_to.frame(target_iframe)
        time.sleep(1.5)
        time.sleep(1.5)
        self.log("Đã sẵn sàng tại màn hình Đóng Bảo Trì (Clear Cls có SR)!", "success")

    def ensure_in_form_iframe(self):
        """Đảm bảo context của selenium luôn ở trong iframe close-checklists."""
        try:
            # Nếu tìm thấy nút XEM DANH SÁCH thì đang ở đúng frame
            btns = self.driver.find_elements(By.TAG_NAME, "button")
            for b in btns:
                if "xem danh sách" in norm_lower(b.text):
                    return
        except Exception:
            pass

        # Nếu chưa ở đúng frame thì chuyển từ default_content -> frame 1 -> iframe close-checklists
        self.driver.switch_to.default_content()
        self.driver.switch_to.frame(1)
        target_iframe = self.driver.find_element(By.XPATH, "//iframe[contains(@src, 'close-checklists')]")
        self.driver.switch_to.frame(target_iframe)
        time.sleep(1)

    def select_ly_do(self, target_reason="KH không có nhu cầu bảo trì"):
        """Chọn Lý do đóng phiếu trên dropdown MudSelect."""
        norm_target = norm_lower(target_reason) if target_reason else "kh không có nhu cầu bảo trì"
        self.log(f"Chọn lý do đóng phiếu: '{target_reason}'...", "info")

        try:
            select_boxes = self.driver.find_elements(By.XPATH, "//div[contains(@class, 'mud-select')]//div[contains(@class, 'mud-select-input')]")
            if not select_boxes:
                select_boxes = self.driver.find_elements(By.XPATH, "//*[contains(@class, 'mud-select-input')]")

            if not select_boxes:
                self.log("Không tìm thấy ô dropdown Lý do đóng phiếu!", "warning")
                return False

            select_box = select_boxes[0]
            cur_text = norm_lower(select_box.text)
            if norm_target in cur_text or (("không có nhu cầu" in norm_target or "khong co nhu cau" in norm_target) and "không có nhu cầu" in cur_text):
                self.log(f"Lý do đã được chọn sẵn: '{select_box.text}'", "info")
                return True

            # Mở dropdown
            self.driver.execute_script("arguments[0].click();", select_box)
            time.sleep(0.8)

            # Quét các mục lựa chọn trong popover
            items = self.driver.find_elements(By.XPATH, "//div[contains(@class, 'mud-popover-open')]//div[contains(@class, 'mud-list-item')] | //div[contains(@class, 'mud-list-item')]")
            matched = None
            for it in items:
                t = norm_lower(it.text)
                if norm_target in t or t in norm_target:
                    matched = it
                    break
                # Fuzzy fallback matching
                if "nhầm" in norm_target and "nhầm" in t:
                    matched = it
                    break
                if "chuyển địa điểm" in norm_target and "chuyển địa điểm" in t:
                    matched = it
                    break
                if "không có nhu cầu" in norm_target and "không có nhu cầu" in t:
                    matched = it
                    break

            if matched:
                self.driver.execute_script("arguments[0].click();", matched)
                time.sleep(0.5)
                self.log(f"Đã chọn lý do thành công: '{matched.text}'", "success")
                return True
            else:
                self.log(f"Không tìm thấy mục '{target_reason}' trong danh sách, giữ nguyên mặc định.", "warning")
                try:
                    self.driver.find_element(By.TAG_NAME, "body").click()
                except Exception:
                    pass
                return False
        except Exception as e:
            self.log(f"Lỗi khi chọn lý do đóng phiếu: {e}", "warning")
            return False

    def process_row(self, record):
        """
        Thực hiện quy trình xử lý cho một hợp đồng:
        1. Nhập Số hợp đồng vào ô input
        2. Bấm 'XEM DANH SÁCH'
        3. Chọn 'Lý do đóng phiếu' (theo cột 'Nguyên Nhân 1')
        4. Bấm 'ĐÓNG PHIẾU'
        5. Đọc kết quả từ bảng và trả về:
           - ket_qua: "Đã xử lý"
           - thao_tac: "Đã clear" (nếu thành công) hoặc "Không thành công : [Nội dung]" (nếu thất bại)
        """
        self.ensure_in_form_iframe()

        shd = str(record.get("SHD", "")).strip()
        reason = str(record.get("Nguyên Nhân 1", "")).strip() or "KH không có nhu cầu bảo trì"

        if not shd:
            return False, "Thiếu SHD", "Thiếu SHD", "Không thành công : Thiếu SHD"

        self.log(f"=== BẮT ĐẦU XỬ LÝ HỢP ĐỒNG: {shd} (Lý do: {reason}) ===", "info")

        # 1. Nhập Số hợp đồng vào ô input
        input_shd = None
        inputs = self.driver.find_elements(By.XPATH, "//input[contains(@placeholder, 'hợp đồng') or contains(@placeholder, 'Hợp đồng')]")
        if inputs:
            input_shd = inputs[0]
        else:
            all_inps = self.driver.find_elements(By.TAG_NAME, "input")
            for inp in all_inps:
                if inp.is_displayed() and inp.get_attribute("type") == "text":
                    input_shd = inp
                    break

        if not input_shd:
            raise RuntimeError("Không tìm thấy ô nhập Số hợp đồng!")

        input_shd.click()
        input_shd.clear()
        input_shd.send_keys(shd)
        input_shd.send_keys(Keys.TAB)
        # Kích hoạt sự kiện binding 2 chiều của Blazor
        self.driver.execute_script("""
            var el = arguments[0];
            el.dispatchEvent(new Event('input', { bubbles: true }));
            el.dispatchEvent(new Event('change', { bubbles: true }));
        """, input_shd)
        time.sleep(0.5)

        # 2. Bấm nút 'XEM DANH SÁCH'
        btn_xem = None
        for b in self.driver.find_elements(By.TAG_NAME, "button"):
            if "xem danh sách" in norm_lower(b.text):
                btn_xem = b
                break

        if not btn_xem:
            raise RuntimeError("Không tìm thấy nút 'XEM DANH SÁCH'!")

        self.log("Bấm nút 'XEM DANH SÁCH'...", "info")
        self.driver.execute_script("arguments[0].click();", btn_xem)
        time.sleep(3)

        # 3. Chọn 'Lý do đóng phiếu'
        self.select_ly_do(reason)
        time.sleep(0.5)

        # 4. Bấm nút 'ĐÓNG PHIẾU'
        btn_dong = None
        for b in self.driver.find_elements(By.TAG_NAME, "button"):
            if "đóng phiếu" in norm_lower(b.text):
                btn_dong = b
                break

        if not btn_dong:
            raise RuntimeError("Không tìm thấy nút 'ĐÓNG PHIẾU'!")

        self.log("Bấm nút 'ĐÓNG PHIẾU' và chờ hệ thống phản hồi...", "info")
        self.driver.execute_script("arguments[0].click();", btn_dong)

        # 5. Chờ kết quả hiển thị trên bảng
        tinh_trang = ""
        noi_dung = ""
        for sec in range(15):
            time.sleep(1)
            rows = self.driver.find_elements(By.XPATH, "//table//tbody//tr | //div[contains(@class, 'mud-table')]//tbody//tr | //table//tr[count(td)>=3]")
            if rows:
                cells = [c.text.strip() for c in rows[0].find_elements(By.XPATH, "./td")]
                if len(cells) >= 4:
                    # Cells: [0]=STT, [1]=Số hợp đồng, [2]=Thời gian tạo phiếu, [3]=Tình trạng đóng phiếu, [4]=Nội dung
                    cur_status = cells[3] if len(cells) > 3 else ""
                    cur_content = cells[4] if len(cells) > 4 else ""
                    if cur_status or cur_content:
                        tinh_trang = cur_status
                        noi_dung = cur_content
                        break

        self.log(f"Kết quả nhận được: Tình trạng='{tinh_trang}' | Nội dung='{noi_dung}'", "info")

        is_success, thao_tac_result = format_cls_thao_tac(tinh_trang, noi_dung)
        self.log(f"Đánh giá kết quả: {'Thành công' if is_success else 'Không thành công'} -> Thao tác: '{thao_tac_result}'", "success" if is_success else "warning")

        return is_success, tinh_trang, noi_dung, thao_tac_result

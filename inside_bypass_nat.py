# -*- coding: utf-8 -*-
"""
COMPONENT BACKEND: AUTO BYPASS NAT
Hệ thống: Radius Portal (http://radius-portal.fpt.net)
Google Sheet ID: 1Sw-qSbLzvVdcW4rj7ywEZBEzKI6w5M82EQeYJUpdx7M | GID: 1907537423
Cột: ID | Tác Vụ | Email | MSNV | Account Inside | SHD | Nguyên Nhân 1 | Ngày Cập Nhật | Kết Quả | Thao Tác

Quy trình tự động hóa Bypass NAT:
Bước 1: Tự đăng nhập vào trang radius (qua IAM & Azure AD SSO)
Bước 2: Mở trang 'Thông số kết nối' (http://radius-portal.fpt.net/networkConnection)
Bước 3: Điền SHD vào ô 'Nhập giá trị'
Bước 4: Bấm nút 'Tìm kiếm'
Bước 5: Bấm nút 'Chi tiết'
Bước 6: Popup 'Cập nhật thông tin kết nối' hiện lên
Bước 7: Tại mục 'Tình trạng NAT':
  - Nếu đã là 'ByPass NAT' -> Thao Tác = 'HD đã được Bypass NAT Trước Đó', Kết Quả = 'Đã xử lý'
  - Nếu chưa -> Bấm dropdown xổ ra và chọn 'ByPass NAT'
Bước 8: Tại ô 'Ghi chú' (ngay cạnh Tình trạng NAT): Điền thông tin 'Nguyên Nhân 1' từ Sheet vào
Bước 9: Bấm nút 'Kích hoạt' bên dưới popup
Bước 10:
  - Nếu hệ thống báo 'thành công' -> Thao Tác = 'thành công kết thúc', Kết Quả = 'Đã xử lý'
  - Nếu hệ thống báo 'Không có gì thay đổi' -> Thao Tác = 'HD đã được Bypass NAT Trước Đó', Kết Quả = 'Đã xử lý'
  - Đóng popup và cập nhật Webhook Google Sheet
"""

import os
import sys
import time
import json
import re
import urllib.request
import unicodedata
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

import core_login

DEFAULT_SHEET_ID = "1Sw-qSbLzvVdcW4rj7ywEZBEzKI6w5M82EQeYJUpdx7M"
GID_BYPASS_NAT = "1907537423"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BYPASS_NAT_CACHE_FILE = os.path.join(BASE_DIR, "bypass_nat_status_cache.json")

def get_radius_profile_dir():
    return core_login.get_radius_profile_dir()

def normalize_nfc(text):
    if text is None:
        return ""
    return unicodedata.normalize('NFC', str(text)).strip()

def remove_accents(input_str):
    if not input_str:
        return ""
    s1 = unicodedata.normalize('NFD', input_str)
    s2 = ''.join(c for c in s1 if unicodedata.category(c) != 'Mn')
    return s2.replace('đ', 'd').replace('Đ', 'D')

def load_cache():
    if os.path.exists(BYPASS_NAT_CACHE_FILE):
        try:
            with open(BYPASS_NAT_CACHE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_cache(data):
    try:
        with open(BYPASS_NAT_CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[CACHE ERROR] {e}")

def is_processed(ket_qua, thao_tac):
    """Kiểm tra hợp đồng đã được xử lý xong hay chưa."""
    kq = remove_accents(str(ket_qua or "")).lower().strip()
    tt = remove_accents(str(thao_tac or "")).lower().strip()
    if "thanh cong ket thuc" in tt or "da duoc bypass nat" in tt or "bypass nat truoc do" in tt:
        return True
    if "chua cap nhat" in tt or not tt or "chua xu ly" in tt:
        return False
    if "da xu ly" in kq and not ("chua" in tt or "loi" in tt or "khong thanh cong" in tt):
        return True
    return False

def is_pending(ket_qua, thao_tac):
    """Khi phát hiện có HD có Thao Tác hoặc Kết Quả là 'Chưa cập nhật' (hoặc rỗng, hoặc chưa xử lý)."""
    if is_processed(ket_qua, thao_tac):
        return False
    kq = remove_accents(str(ket_qua or "")).lower().strip()
    tt = remove_accents(str(thao_tac or "")).lower().strip()
    if "chua cap nhat" in tt or "chua cap nhat" in kq:
        return True
    if "chua xu ly" in tt or "chua xu ly" in kq:
        return True
    if not tt or not kq:
        return True
    return False

def fetch_sheet_data(sheet_id=DEFAULT_SHEET_ID, gid=GID_BYPASS_NAT):
    """Đọc dữ liệu từ Google Sheet qua gviz CSV."""
    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&gid={gid}&_t={int(time.time() * 1000)}"
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        content = urllib.request.urlopen(req, timeout=12).read().decode('utf-8', errors='ignore')
        import io
        df = pd.read_csv(io.StringIO(content))
        df = df.fillna("")

        cache = load_cache()
        records = []

        for raw in df.to_dict(orient="records"):
            rec = {}
            for k, v in raw.items():
                norm_k = normalize_nfc(k)
                norm_v = normalize_nfc(v) if isinstance(v, str) else v
                k_clean = remove_accents(norm_k).lower()

                if k_clean == "id":
                    rec["ID"] = norm_v
                elif "tac vu" in k_clean:
                    rec["Tác Vụ"] = norm_v
                elif "email" in k_clean:
                    rec["Email"] = norm_v
                elif "msnv" in k_clean:
                    rec["MSNV"] = norm_v
                elif "account" in k_clean:
                    rec["Account Inside"] = norm_v
                elif "shd" in k_clean or "hop dong" in k_clean:
                    rec["SHD"] = norm_v
                elif "nguyen nhan" in k_clean:
                    rec["Nguyên Nhân 1"] = norm_v
                elif "ngay" in k_clean:
                    rec["Ngày Cập Nhật"] = norm_v
                elif "ket qua" in k_clean:
                    rec["Kết Quả"] = norm_v
                elif "thao tac" in k_clean:
                    rec["Thao Tác"] = norm_v
                else:
                    rec[norm_k] = norm_v

            # Đồng bộ với local cache CHỈ khi vừa xử lý trong phiên gần đây (< 90 giây)
            # Không đè lên các hợp đồng mới thêm vào Google Sheet có trạng thái 'Chưa cập nhật'
            shd = str(rec.get("SHD", "")).strip()
            if shd and shd in cache:
                c_item = cache[shd]
                c_kq = c_item.get("ket_qua", "") if isinstance(c_item, dict) else ""
                c_tt = c_item.get("thao_tac", "") if isinstance(c_item, dict) else str(c_item)
                c_time = c_item.get("time", "") if isinstance(c_item, dict) else ""
                c_ts = c_item.get("timestamp_epoch", 0) if isinstance(c_item, dict) else 0

                current_kq = str(rec.get("Kết Quả", "")).strip()
                current_tt = str(rec.get("Thao Tác", "")).strip()

                is_sheet_raw_pending = ("chưa" in current_kq.lower() or "chưa" in current_tt.lower() or not current_kq or not current_tt)
                is_recent = (time.time() - c_ts < 90) if c_ts else False

                if is_recent and is_sheet_raw_pending:
                    rec["Kết Quả"] = c_kq or "Đã xử lý"
                    rec["Thao Tác"] = c_tt
                    if c_time and not rec.get("Ngày Cập Nhật"):
                        rec["Ngày Cập Nhật"] = c_time
                elif not is_sheet_raw_pending:
                    if not current_tt and c_tt:
                        rec["Thao Tác"] = c_tt

            records.append(rec)

        cols = [normalize_nfc(c) for c in df.columns]
        return {
            "status": "ok",
            "count": len(records),
            "columns": cols,
            "records": records
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Không thể đọc Google Sheet: {e}",
            "records": []
        }

class InsideBypassNatAutomation:
    def __init__(self, headless=False, keep_open=False, log_cb=None):
        self.headless = headless
        self.keep_open = keep_open
        self.log_cb = log_cb or self._default_log
        self.driver = None
        self._stop_requested = False

    def _default_log(self, msg, level="info"):
        try:
            print(f"[{level.upper()}] {msg}", flush=True)
        except Exception:
            try:
                safe_msg = str(msg).encode('ascii', errors='replace').decode()
                print(f"[{level.upper()}] {safe_msg}", flush=True)
            except Exception:
                pass

    def log(self, msg, level="info"):
        try:
            self.log_cb(msg, level)
        except Exception:
            pass

    def request_stop(self):
        self._stop_requested = True
        self.log("Đã nhận yêu cầu dừng tiến trình Bypass NAT!", "warning")

    def init_driver(self):
        self.log("Khởi tạo trình duyệt Chrome cho Radius Portal (Bypass NAT)...", "info")
        p_dir = get_radius_profile_dir()
        self.driver = core_login.create_driver_with_retry(
            headless=self.headless,
            profile_dir=p_dir,
            keep_open=self.keep_open,
            max_retries=2,
            log_cb=self.log_cb
        )
        return self.driver

    def check_and_ensure_login(self):
        """Đảm bảo đã đăng nhập vào hệ thống Radius Portal."""
        self.log("Kiểm tra và xác thực phiên đăng nhập Radius Portal...", "info")
        core_login.run_radius_login(
            driver=self.driver,
            headless=self.headless,
            keep_open=self.keep_open,
            log_callback=self.log_cb
        )

    def handle_logout_and_relogin(self):
        """Xử lý sự cố phiên hết hạn / màn hình trắng: Đăng xuất và đăng nhập lại."""
        self.log("Phát hiện lỗi phiên đăng nhập Radius! Đang đăng xuất và đăng nhập lại...", "warning")
        try:
            avatar_selectors = [
                "//header//*[contains(@class, 'rounded-full')]/ancestor::a[1]",
                "//header//svg[contains(@class, 'fill-current')]/ancestor::a[1]",
                "//header//*[contains(@class, 'ant-avatar')]",
                "//header//a[contains(@class, 'flex') and contains(@class, 'items-center')]",
                "//div[contains(@class, 'ant-dropdown-trigger')]"
            ]
            avatar_el = None
            for sel in avatar_selectors:
                elements = self.driver.find_elements(By.XPATH, sel)
                for el in elements:
                    if el.is_displayed():
                        avatar_el = el
                        break
                if avatar_el:
                    break

            if avatar_el:
                try:
                    ActionChains(self.driver).move_to_element(avatar_el).click().perform()
                except Exception:
                    self.driver.execute_script("arguments[0].click();", avatar_el)
                time.sleep(1.5)

                logout_selectors = [
                    "//div[contains(@class, 'relative')]//*[contains(text(), 'Đăng xuất')]",
                    "//li[contains(@class, 'ant-dropdown-menu-item') and contains(., 'Đăng xuất')]",
                    "//span[contains(text(), 'Đăng xuất')]"
                ]
                for sel in logout_selectors:
                    elements = self.driver.find_elements(By.XPATH, sel)
                    for el in elements:
                        if el.is_displayed():
                            self.driver.execute_script("arguments[0].click();", el)
                            time.sleep(3)
                            break
        except Exception:
            pass

        try:
            self.driver.delete_all_cookies()
            self.driver.execute_script("try { localStorage.clear(); sessionStorage.clear(); } catch(e){}")
        except Exception:
            pass

        self.log("Bắt đầu đăng nhập lại từ đầu vào Radius Portal qua IAM & Azure AD...", "info")
        core_login.run_radius_login(
            driver=self.driver,
            headless=self.headless,
            keep_open=self.keep_open,
            log_callback=self.log_cb,
            force=True
        )

    def check_and_handle_session_expired(self):
        """Kiểm tra và tự động xử lý khi có popup 'Phiên đăng nhập của bạn đã kết thúc'."""
        try:
            expired_btns = self.driver.find_elements(
                By.XPATH,
                "//button[contains(., 'ĐĂNG NHẬP LẠI') or contains(., 'Đăng nhập lại')] | "
                "//div[contains(., 'Phiên đăng nhập của bạn đã kết thúc') or contains(., 'kết thúc')]//button"
            )
            visible_btns = [b for b in expired_btns if b.is_displayed()]
            if visible_btns:
                self.log("⚠️ Phát hiện popup 'Phiên đăng nhập của bạn đã kết thúc' -> Tự động đăng nhập lại...", "warning")
                try:
                    self.driver.execute_script("arguments[0].click();", visible_btns[0])
                except Exception:
                    visible_btns[0].click()
                time.sleep(2)
                self.check_and_ensure_login()
                self.driver.get("http://radius-portal.fpt.net/networkConnection")
                time.sleep(2)
                return True
        except Exception as e:
            self.log(f"Lỗi kiểm tra popup hết phiên: {e}", "warning")
        return False

    def navigate_to_network_connection(self):
        """Mở trang Thông số kết nối (http://radius-portal.fpt.net/networkConnection)."""
        target_url = "http://radius-portal.fpt.net/networkConnection"
        self.log(f"Đang điều hướng đến trang Thông số kết nối: {target_url}", "info")
        self.driver.get(target_url)
        time.sleep(2)

        # Kiểm tra và xử lý popup hết hạn phiên trước
        self.check_and_handle_session_expired()

        curr = (self.driver.current_url or "").lower()
        if "login" in curr:
            self.log("Trang yêu cầu đăng nhập lại, đang thực hiện đăng nhập...", "info")
            self.check_and_ensure_login()
            self.driver.get(target_url)
            time.sleep(2)

        # Chờ trang tải các thành phần filter (tối đa 12s)
        content_ready = False
        for _ in range(12):
            self.check_and_handle_session_expired()
            elems = self.driver.find_elements(
                By.XPATH,
                "//span[contains(@class, 'custom-filter_placeholder')] | "
                "//span[contains(text(), 'Nhập giá trị')] | "
                "//div[contains(@class, 'custom-filter_inputContainer')]//input | "
                "//button[contains(., 'Tìm kiếm')]"
            )
            if any(e.is_displayed() for e in elems):
                content_ready = True
                break
            time.sleep(1)

        if not content_ready:
            self.log("⚠️ Phát hiện màn hình trắng / hết hạn phiên! Tiến hành Đăng Xuất và Đăng Nhập lại...", "warning")
            self.handle_logout_and_relogin()
            self.log(f"Mở lại trang Thông số kết nối sau khi đăng nhập mới: {target_url}", "info")
            self.driver.get(target_url)
            time.sleep(2)

        wait = WebDriverWait(self.driver, 20)
        wait.until(EC.presence_of_element_located((
            By.XPATH,
            "//span[contains(@class, 'custom-filter_placeholder')] | "
            "//span[contains(text(), 'Nhập giá trị')] | "
            "//div[contains(@class, 'custom-filter_inputContainer')]//input | "
            "//button[contains(., 'Tìm kiếm')]"
        )))
        self.log("Đã mở trang Thông số kết nối thành công và sẵn sàng thao tác!", "success")

    def process_bypass_nat_contract(self, shd, nguyen_nhan_1=""):
        """
        Quy trình xử lý Bypass NAT cho 1 Hợp đồng:
        Bước 1: Điền SHD vào ô Nhập giá trị
        Bước 2: Bấm nút Tìm kiếm
        Bước 3: Bấm nút Chi tiết
        Bước 4: Popup 'Cập nhật thông tin kết nối' hiện lên
        Bước 5: Tại mục 'Tình trạng NAT':
          - Nếu đã là 'ByPass NAT' -> Thao Tác = 'HD đã được Bypass NAT Trước Đó', Kết Quả = 'Đã xử lý'
          - Nếu chưa -> Bấm dropdown xổ ra và chọn 'ByPass NAT'
        Bước 6: Tại ô 'Ghi chú' (ngay cạnh Tình trạng NAT): Điền thông tin Nguyên Nhân 1 từ Sheet vào
        Bước 7: Bấm nút 'Kích hoạt' bên dưới popup
        Bước 8: Bắt thông báo hệ thống và trả về (is_success, thao_tac, ket_qua)
        """
        shd = str(shd).strip()
        note_text = str(nguyen_nhan_1 or "").strip()
        if not note_text:
            note_text = "ByPass NAT theo yeu cau"

        self.log(f"--- Bắt đầu xử lý Bypass NAT cho HĐ [{shd}] (Ghi chú: '{note_text}') ---", "info")
        wait = WebDriverWait(self.driver, 15)

        # 1. Kích hoạt và điền SHD vào ô "Nhập giá trị"
        self.log(f"Bước 1: Điền SHD [{shd}] vào ô 'Nhập giá trị'...", "info")
        target_input = None

        inps = self.driver.find_elements(By.XPATH, "//div[contains(@class, 'custom-filter_inputContainer')]//input")
        if not inps:
            placeholders = self.driver.find_elements(
                By.XPATH,
                "//span[contains(@class, 'custom-filter_placeholder')] | //span[contains(text(), 'Nhập giá trị')]"
            )
            if placeholders:
                try:
                    self.driver.execute_script("arguments[0].click();", placeholders[0])
                except Exception:
                    placeholders[0].click()
                time.sleep(0.5)

            try:
                target_input = wait.until(EC.presence_of_element_located((
                    By.XPATH, "//div[contains(@class, 'custom-filter_inputContainer')]//input | //input[not(@placeholder='Tìm menu ...') and not(@type='search') and not(@id='rc_select_0')]"
                )))
            except Exception:
                pass
        else:
            target_input = inps[0]

        if not target_input:
            self.log("⚠️ Không tìm thấy ô nhập liệu! Đang thử Đăng xuất và Đăng nhập lại...", "warning")
            self.handle_logout_and_relogin()
            self.navigate_to_network_connection()

            placeholders = self.driver.find_elements(
                By.XPATH,
                "//span[contains(@class, 'custom-filter_placeholder')] | //span[contains(text(), 'Nhập giá trị')]"
            )
            if placeholders:
                self.driver.execute_script("arguments[0].click();", placeholders[0])
                time.sleep(0.6)
            target_input = wait.until(EC.presence_of_element_located((
                By.XPATH, "//div[contains(@class, 'custom-filter_inputContainer')]//input | //input[not(@placeholder='Tìm menu ...') and not(@type='search')]"
            )))

        self.driver.execute_script("arguments[0].scrollIntoView(true);", target_input)
        try:
            target_input.click()
        except Exception as ex_click:
            self.log(f"Nhấp ô input bằng chuột bị chặn ({ex_click}), đang xử lý tự động...", "warning")
            if self.check_and_handle_session_expired():
                target_input = wait.until(EC.presence_of_element_located((
                    By.XPATH, "//div[contains(@class, 'custom-filter_inputContainer')]//input | //input[not(@placeholder='Tìm menu ...') and not(@type='search')]"
                )))
            self.driver.execute_script("arguments[0].focus(); arguments[0].click();", target_input)

        target_input.send_keys(Keys.CONTROL + "a")
        target_input.send_keys(Keys.BACKSPACE)
        target_input.send_keys(shd)
        time.sleep(0.5)

        # 2. Bấm nút Tìm kiếm
        self.log("Bước 2: Bấm nút [Tìm kiếm]...", "info")
        btn_search = wait.until(EC.element_to_be_clickable((
            By.XPATH, "//button[contains(., 'Tìm kiếm')]"
        )))
        self.driver.execute_script("arguments[0].click();", btn_search)
        time.sleep(2.5)

        # 3. Kiểm tra kết quả trong bảng
        no_data_elems = self.driver.find_elements(By.XPATH, "//div[contains(text(), 'No data')] | //*[text()='No data']")
        is_no_data = any(elem.is_displayed() for elem in no_data_elems)

        btn_details = self.driver.find_elements(
            By.XPATH,
            "//button[contains(., 'Chi tiết')] | //a[contains(., 'Chi tiết')] | //tbody//tr[1]//button"
        )

        if is_no_data or not btn_details:
            self.log(f"⚠️ Không tìm thấy thông tin hợp đồng [{shd}] trong hệ thống Radius!", "warning")
            return False, "Không tìm thấy hợp đồng trên hệ thống", "Lỗi"

        # 4. Bấm nút Chi tiết
        self.log(f"Bước 3: Bấm nút [Chi Tiết] cho HĐ [{shd}]...", "info")
        self.driver.execute_script("arguments[0].click();", btn_details[0])
        time.sleep(3)

        # 5. Chờ Popup "Cập nhật thông tin kết nối" xuất hiện
        self.log("Đang chờ popup 'Cập nhật thông tin kết nối'...", "info")
        modal = wait.until(EC.visibility_of_element_located((
            By.XPATH, "//div[contains(@class, 'ant-modal')]//div[contains(., 'Cập nhật thông tin kết nối')]/ancestor::div[contains(@class, 'ant-modal-content') or contains(@class, 'ant-modal')][1]"
        )))

        # 6. Tìm mục Tình trạng NAT
        self.log("Bước 4: Kiểm tra mục 'Tình trạng NAT' trong popup...", "info")
        time.sleep(1)

        nat_selects = self.driver.find_elements(
            By.XPATH,
            "//label[contains(text(), 'Tình trạng NAT')]/ancestor::div[1]/following-sibling::div[contains(@class, 'ant-select')] | "
            "//h2[contains(., 'Tình trạng NAT')]/following::div[contains(@class, 'ant-select')][1] | "
            "//div[contains(@class, 'ant-modal')]//*[text()='Tình trạng NAT']/ancestor::div[contains(@class, 'flex') or contains(@class, 'ant-form-item') or self::div][1]//div[contains(@class, 'ant-select')]"
        )

        if not nat_selects:
            raise RuntimeError("Không tìm thấy dropdown 'Tình trạng NAT' bên trong popup!")

        nat_select = nat_selects[0]

        # Kiểm tra giá trị hiện tại của Tình trạng NAT
        current_nat_text = ""
        try:
            val_items = nat_select.find_elements(By.XPATH, ".//span[contains(@class, 'ant-select-selection-item')]")
            if val_items:
                current_nat_text = val_items[0].text.strip()
            else:
                current_nat_text = nat_select.text.strip()
        except Exception:
            pass

        current_nat_val = remove_accents(current_nat_text).upper().replace(" ", "")
        self.log(f"Giá trị Tình trạng NAT hiện tại: '{current_nat_text}'", "info")

        is_already_bypass = ("BYPASSNAT" in current_nat_val)

        # 7. Nếu chưa phải ByPass NAT -> Chọn ByPass NAT từ dropdown
        if not is_already_bypass:
            self.log("Nhấp mở danh sách Tình trạng NAT để chọn 'ByPass NAT'...", "info")
            selector_el = nat_select.find_element(By.CLASS_NAME, "ant-select-selector")
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", selector_el)
            time.sleep(0.3)

            self.driver.execute_script("""
                var el = arguments[0];
                el.dispatchEvent(new MouseEvent('mousedown', {bubbles: true, cancelable: true, view: window}));
                el.dispatchEvent(new MouseEvent('mouseup', {bubbles: true, cancelable: true, view: window}));
                el.dispatchEvent(new MouseEvent('click', {bubbles: true, cancelable: true, view: window}));
            """, selector_el)
            time.sleep(1.2)

            dropdown = wait.until(EC.presence_of_element_located((
                By.XPATH, "//div[contains(@class, 'ant-select-dropdown') and not(contains(@class, 'ant-select-dropdown-hidden'))]"
            )))

            rendered_opts = dropdown.find_elements(
                By.XPATH,
                ".//div[contains(@class, 'ant-select-item-option') and (contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'bypass nat') or contains(translate(@title, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'bypass nat'))]"
            )
            if not rendered_opts:
                raise RuntimeError("Không tìm thấy tùy chọn 'ByPass NAT' trong danh sách xổ xuống!")

            target_opt = rendered_opts[0]
            self.log(f"Đã tìm thấy tùy chọn: '{target_opt.text.strip()}' -> Tiến hành chọn...", "info")
            self.driver.execute_script("""
                var el = arguments[0];
                el.scrollIntoView({block: 'center'});
                el.dispatchEvent(new MouseEvent('mousedown', {bubbles: true, cancelable: true, view: window}));
                el.dispatchEvent(new MouseEvent('mouseup', {bubbles: true, cancelable: true, view: window}));
                el.dispatchEvent(new MouseEvent('click', {bubbles: true, cancelable: true, view: window}));
            """, target_opt)
            time.sleep(1.2)
        else:
            self.log(f"Hợp đồng [{shd}] ĐÃ ĐƯỢC thiết lập 'ByPass NAT' từ trước đó!", "info")

        # 8. Điền Ghi chú (nguyên nhân 1 từ Sheet) vào ô Ghi chú của Tình trạng NAT
        self.log(f"Bước 5: Điền Ghi chú '{note_text}' vào ô Ghi chú của Tình trạng NAT...", "info")
        target_textarea = None
        textareas = self.driver.find_elements(
            By.XPATH,
            "//label[contains(text(), 'Tình trạng NAT')]/following::textarea[1] | "
            "//h2[contains(., 'Tình trạng NAT')]/following::textarea[1] | "
            "//label[contains(text(), 'Tình trạng NAT')]/ancestor::div[contains(@class, 'flex') or contains(@class, 'grid') or contains(@class, 'row') or self::div][1]//textarea"
        )
        if textareas:
            target_textarea = textareas[0]
        else:
            inps = self.driver.find_elements(By.XPATH, "//label[contains(text(), 'Tình trạng NAT')]/following::input[not(@type='search') and not(@type='hidden')][1]")
            if inps:
                target_textarea = inps[0]

        if target_textarea:
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", target_textarea)
            target_textarea.click()
            target_textarea.send_keys(Keys.CONTROL + "a")
            target_textarea.send_keys(Keys.BACKSPACE)
            time.sleep(0.2)
            target_textarea.send_keys(note_text)
            time.sleep(0.5)
            self.log(f"Đã điền thành công Ghi chú: '{note_text}'", "info")
        else:
            self.log("⚠️ Không tìm thấy ô Ghi chú của Tình trạng NAT!", "warning")

        # Nếu đã là ByPass NAT từ trước đó và không cần kích hoạt lại:
        if is_already_bypass:
            self.log(f"Hợp đồng [{shd}] ĐÃ ĐƯỢC thiết lập 'ByPass NAT' từ trước đó!", "success")
            self._close_modal_if_open()
            return True, "HD đã được Bypass NAT Trước Đó", "Đã xử lý"

        # 9. Bấm nút Kích hoạt bên dưới popup
        self.log("Bước 6: Bấm nút [Kích hoạt] bên dưới popup...", "info")
        btn_kich_hoat = wait.until(EC.element_to_be_clickable((
            By.XPATH,
            "//div[contains(@class, 'ant-modal')]//button[contains(., 'Kích hoạt')] | //button[contains(., 'Kích hoạt')]"
        )))
        self.driver.execute_script("arguments[0].click();", btn_kich_hoat)
        time.sleep(2.5)

        # Kiểm tra popup xác nhận nếu có
        try:
            btn_dong_y = WebDriverWait(self.driver, 3).until(EC.element_to_be_clickable((
                By.XPATH,
                "//div[contains(@class, 'ant-modal')]//button[contains(., 'Đồng ý')] | //button[contains(., 'Đồng ý')]"
            )))
            self.driver.execute_script("arguments[0].click();", btn_dong_y)
            time.sleep(1.5)
        except Exception:
            pass

        # 10. Đợi phản hồi thông báo hệ thống
        self.log("Bước 7: Đang chờ phản hồi thông báo từ hệ thống Radius...", "info")
        final_msg = ""
        for _ in range(10):
            msgs = self.driver.find_elements(
                By.XPATH,
                "//div[contains(@class, 'ant-message')]//span | //div[contains(@class, 'ant-notification-notice-description')] | //div[contains(@class, 'ant-notification-notice-message')]"
            )
            for m in msgs:
                if m.is_displayed():
                    txt = m.text.strip()
                    if txt:
                        final_msg = txt
                        break
            if final_msg:
                break
            time.sleep(0.8)

        self.log(f"Hệ thống thông báo: '{final_msg}'", "info")
        self._close_modal_if_open()

        msg_clean = remove_accents(final_msg).lower()
        if "khong co gi thay doi" in msg_clean:
            self.log(f"Kết quả HĐ [{shd}]: Không có gì thay đổi -> HD đã được Bypass NAT Trước Đó", "success")
            return True, "HD đã được Bypass NAT Trước Đó", "Đã xử lý"
        elif "thanh cong" in msg_clean:
            self.log(f"Kết quả HĐ [{shd}]: Cập nhật Bypass NAT thành công!", "success")
            return True, "thành công kết thúc", "Đã xử lý"
        elif final_msg:
            self.log(f"Kết quả HĐ [{shd}]: Thông báo khác: {final_msg}", "warning")
            return False, final_msg, "Lỗi"
        else:
            self.log(f"Đã hoàn tất thao tác Kích hoạt Bypass NAT cho HĐ [{shd}]!", "success")
            return True, "thành công kết thúc", "Đã xử lý"

    def _close_modal_if_open(self):
        """Đóng modal nếu còn hiển thị."""
        try:
            close_btns = self.driver.find_elements(
                By.XPATH,
                "//div[contains(@class, 'ant-modal')]//button[contains(@class, 'ant-modal-close') or contains(., 'Hủy')]"
            )
            for cb in close_btns:
                if cb.is_displayed():
                    self.driver.execute_script("arguments[0].click();", cb)
                    time.sleep(0.5)
        except Exception:
            pass

    def process_queue(self, records, update_sheet_cb=None):
        """Xử lý danh sách các hợp đồng cần Bypass NAT."""
        results = []
        cache = load_cache()

        try:
            self.init_driver()
            self.navigate_to_network_connection()

            pending_records = [r for r in records if is_pending(r.get("Kết Quả"), r.get("Thao Tác"))]
            if not pending_records:
                self.log("Không có hợp đồng nào có trạng thái 'Chưa cập nhật' cần xử lý!", "info")
                return []

            self.log(f"Bắt đầu xử lý {len(pending_records)} hợp đồng cần Bypass NAT...", "info")

            for idx, r in enumerate(pending_records):
                if self._stop_requested:
                    self.log("Đã dừng tiến trình theo yêu cầu của người dùng.", "warning")
                    break

                shd = str(r.get("SHD", "")).strip()
                nguyen_nhan_1 = str(r.get("Nguyên Nhân 1", "")).strip()
                if not shd:
                    continue

                self.log(f"\n▶ [{idx + 1}/{len(pending_records)}] Xử lý hợp đồng: {shd}", "info")

                try:
                    ok, thao_tac, ket_qua = self.process_bypass_nat_contract(shd, nguyen_nhan_1)
                    now_str = time.strftime("%d/%m/%Y %H:%M:%S")

                    r["Thao Tác"] = thao_tac
                    r["Kết Quả"] = ket_qua
                    r["Ngày Cập Nhật"] = now_str

                    cache[shd] = {
                        "ket_qua": ket_qua,
                        "thao_tac": thao_tac,
                        "time": now_str,
                        "timestamp_epoch": time.time()
                    }
                    save_cache(cache)

                    results.append({
                        "shd": shd,
                        "status": ket_qua,
                        "thao_tac": thao_tac,
                        "message": thao_tac
                    })

                    if update_sheet_cb:
                        try:
                            update_sheet_cb(r, thao_tac, ket_qua)
                        except Exception as ex_cb:
                            self.log(f"Lỗi callback Webhook Google Sheet: {ex_cb}", "warning")

                except Exception as ex_contract:
                    err_msg = str(ex_contract)[:80]
                    self.log(f"❌ Lỗi khi xử lý HĐ [{shd}]: {err_msg}", "error")
                    r["Thao Tác"] = f"Lỗi: {err_msg}"
                    r["Kết Quả"] = "Lỗi"
                    results.append({
                        "shd": shd,
                        "status": "Lỗi",
                        "thao_tac": f"Lỗi: {err_msg}",
                        "message": err_msg
                    })

                time.sleep(2)

            self.log(f"\n🎉 HOÀN TẤT TIẾN TRÌNH BYPASS NAT: Đã xử lý {len(results)} hợp đồng!", "success")
            return results

        except Exception as e:
            self.log(f"❌ Tiến trình Bypass NAT gặp sự cố: {e}", "error")
            raise e
        finally:
            self.close(force=True)

    def close(self, force=True, clear_session=False):
        p_dir = get_radius_profile_dir()
        if force or not self.keep_open:
            if self.driver:
                try:
                    self.driver.quit()
                except Exception:
                    pass
                self.driver = None
            try:
                if clear_session:
                    core_login.clear_inside_session(profile_dir=p_dir, log_cb=self.log_cb)
                else:
                    core_login.clean_profile_locks_and_orphans(profile_dir=p_dir, log_cb=self.log_cb)
            except Exception:
                pass
            self.log("Đã tắt trình duyệt Radius Portal (Bypass NAT).", "info")

if __name__ == "__main__":
    data = fetch_sheet_data()
    print(f"Sheet fetched: {data.get('count')} records")

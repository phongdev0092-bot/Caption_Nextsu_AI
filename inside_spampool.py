# -*- coding: utf-8 -*-
"""
COMPONENT BACKEND: AUTO SPAMPOOL & DEACTIVE IPV6
Hệ thống: Radius Portal (http://radius-portal.fpt.net)
Google Sheet GID: 2070394876 | Cột: ID | Tác Vụ | Email | MSNV | Account Inside | SHD | Nguyên Nhân 1 | Ngày Cập Nhật | Kết Quả | Thao Tác

Quy trình tự động hóa SpamPool:
Bước 1: Tự đăng nhập vào trang radius (qua IAM & Azure AD SSO)
Bước 2: Mở trang 'Thông số kết nối' (http://radius-portal.fpt.net/networkConnection)
Bước 3: Điền SHD vào ô 'Nhập giá trị'
Bước 4: Bấm nút 'Tìm kiếm'
Bước 5: Bấm nút 'Chi tiết'
Bước 6: Popup 'Cập nhật thông tin kết nối' hiện lên, tại SpamPool xổ ra chọn 'SAVECUS'
Bước 7: Popup nhỏ 'Xác nhận cập nhật spam pool' hiện lên -> Bấm 'Đồng ý'
Bước 8: Bấm nút 'Kích hoạt' bên dưới
Bước 9:
  - Nếu hệ thống báo 'Cập nhật SpamPool thành công' -> Thao Tác = 'thành công kết thúc', Kết Quả = 'Đã xử lý'
  - Nếu hệ thống báo 'Không có gì thay đổi' (hoặc đã là SAVECUS) -> Thao Tác = 'HD đã được SpamPool Trước Đó', Kết Quả = 'Đã xử lý'
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
GID_SPAMPOOL = "2070394876"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SPAMPOOL_CACHE_FILE = os.path.join(BASE_DIR, "spampool_status_cache.json")

def get_radius_profile_dir():
    radius_dir = os.path.join(BASE_DIR, "RadiusPortal_SessionProfile")
    if not os.path.exists(radius_dir):
        inside_dir = core_login.get_inside_profile_dir()
        if os.path.exists(inside_dir):
            try:
                import shutil
                os.makedirs(radius_dir, exist_ok=True)
                src_def = os.path.join(inside_dir, "Default")
                dst_def = os.path.join(radius_dir, "Default")
                if os.path.exists(src_def) and not os.path.exists(dst_def):
                    shutil.copytree(src_def, dst_def, ignore=shutil.ignore_patterns("*.lock", "Singleton*", "*Lock*", "DevToolsActivePort"))
            except Exception:
                pass
    return radius_dir

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
    if os.path.exists(SPAMPOOL_CACHE_FILE):
        try:
            with open(SPAMPOOL_CACHE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_cache(data):
    try:
        with open(SPAMPOOL_CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[CACHE ERROR] {e}")

def is_deactive_ip_task(tac_vu):
    """Kiểm tra tác vụ có phải là Deactive IP 0.0.0.0 hay không."""
    tv = remove_accents(str(tac_vu or "")).lower()
    return any(w in tv for w in ("0.0.0.0", "deactive", "deactivate", "ipv6 only"))

def is_processed(ket_qua, thao_tac):
    """Kiểm tra hợp đồng đã được xử lý xong hay chưa."""
    kq = remove_accents(str(ket_qua or "")).lower().strip()
    tt = remove_accents(str(thao_tac or "")).lower().strip()
    if any(w in tt for w in (
        "thanh cong ket thuc",
        "da duoc spampool", "spampool truoc do",
        "deactive ip", "deactivate ip", "0.0.0.0 truoc do"
    )):
        return True
    if "chua cap nhat" in tt or not tt or "chua xu ly" in tt:
        return False
    if "da xu ly" in kq and not ("chua" in tt or "loi" in tt or "khong thanh cong" in tt):
        return True
    return False

def is_pending(ket_qua, thao_tac):
    """
    Theo yêu cầu: Khi phát hiện có HD có Thao Tác hoặc Kết Quả là 'Chưa cập nhật' (hoặc rỗng, hoặc chưa xử lý)
    """
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

def fetch_sheet_data(sheet_id=DEFAULT_SHEET_ID, gid=GID_SPAMPOOL):
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
            row_id = str(rec.get("ID", "")).strip()
            tac_vu_raw = str(rec.get("Tác Vụ", "")).strip()
            tv_key = "deactive" if is_deactive_ip_task(tac_vu_raw) else "spampool"
            cache_key = None
            if f"{shd}_{row_id}" in cache:
                cache_key = f"{shd}_{row_id}"
            elif f"{shd}_{tv_key}" in cache:
                cache_key = f"{shd}_{tv_key}"
            elif shd in cache:
                # Chỉ lấy shd nếu task type trong cache khớp hoặc tương đồng
                c_data = cache[shd]
                c_tt_str = (c_data.get("thao_tac", "") if isinstance(c_data, dict) else str(c_data)).lower()
                c_is_deactive = ("deactive" in c_tt_str or "0.0.0.0" in c_tt_str)
                if (tv_key == "deactive" and c_is_deactive) or (tv_key == "spampool" and not c_is_deactive):
                    cache_key = shd

            if cache_key and cache_key in cache:
                c_item = cache[cache_key]
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

class InsideSpamPoolAutomation:
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
        self.log("Đã nhận yêu cầu dừng tiến trình SpamPool!", "warning")

    def init_driver(self):
        self.log("Khởi tạo trình duyệt Chrome cho Radius Portal...", "info")
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

    def handle_logout_and_relogin(self):
        """
        Xử lý sự cố phiên hết hạn / màn hình trắng như ảnh phản hồi người dùng:
        Nhấp vào Avatar / Mũi tên góc trên bên phải -> Chọn 'Đăng xuất' -> Đăng nhập lại 8 bước qua SSO Azure AD.
        """
        self.log("Phát hiện màn hình trắng / lỗi phiên đăng nhập! Đang bấm menu Đăng xuất...", "warning")
        try:
            # 1. Tìm avatar hoặc mũi tên góc trên bên phải
            avatar_selectors = [
                "//header//a[contains(@class, 'items-center') and .//span[contains(@class, 'rounded-full')]]",
                "//header//*[contains(@class, 'rounded-full')]/ancestor::a[1]",
                "//header//svg[contains(@class, 'fill-current')]/ancestor::a[1]",
                "//header//*[contains(@class, 'rounded-full')]",
                "//header//svg[contains(@class, 'fill-current')]",
                "//header//a[contains(@class, 'flex') and contains(@class, 'items-center')]",
                "//div[contains(@class, 'relative')]//a[contains(@class, 'flex')]",
                "//div[contains(@class, 'ant-dropdown-trigger')]",
                "//span[contains(@class, 'ant-avatar')]/..",
                "//header//*[contains(@class, 'ant-avatar')]",
                "//*[contains(@class, 'anticon-down')]",
                "//header//div[contains(@class, 'cursor-pointer')]"
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
                self.log("Đã tìm thấy Avatar/Mũi tên góc trên bên phải, đang nhấp mở menu...", "info")
                try:
                    ActionChains(self.driver).move_to_element(avatar_el).click().perform()
                except Exception:
                    self.driver.execute_script("arguments[0].click();", avatar_el)
                time.sleep(1.5)

                # 2. Tìm nút hoặc icon 'Đăng xuất'
                logout_selectors = [
                    "//div[contains(@class, 'relative')]//*[contains(text(), 'Đăng xuất')]",
                    "//div[contains(@class, 'relative')]//button[contains(., 'Đăng xuất')]",
                    "//div[contains(@class, 'relative')]//a[contains(., 'Đăng xuất')]",
                    "//*[text()='Đăng xuất' or contains(text(), 'Đăng xuất')]",
                    "//button[contains(., 'Đăng xuất')]",
                    "//a[contains(., 'Đăng xuất')]",
                    "//li[contains(@class, 'ant-dropdown-menu-item') and contains(., 'Đăng xuất')]",
                    "//div[contains(@class, 'ant-dropdown')]//*[contains(text(), 'Đăng xuất')]",
                    "//span[contains(text(), 'Đăng xuất')]"
                ]
                logout_el = None
                for sel in logout_selectors:
                    elements = self.driver.find_elements(By.XPATH, sel)
                    for el in elements:
                        if el.is_displayed():
                            logout_el = el
                            break
                    if logout_el:
                        break

                if logout_el:
                    self.log("Đã tìm thấy nút/icon [Đăng xuất], đang nhấn Đăng xuất...", "info")
                    try:
                        self.driver.execute_script("arguments[0].click();", logout_el)
                    except Exception:
                        logout_el.click()
                    time.sleep(3)
                else:
                    self.log("Không tìm thấy nút 'Đăng xuất' trong menu, dọn dẹp cookie và storage...", "warning")
            else:
                self.log("Không tìm thấy avatar trên thanh header, tiến hành xóa cookie/storage để đăng xuất...", "warning")
        except Exception as e_lo:
            self.log(f"Lỗi khi thực hiện bấm Đăng xuất: {e_lo}. Dọn dẹp cookie trình duyệt...", "warning")

        # Dọn sạch session và cookie để bảo đảm không bị dính token cũ
        try:
            self.driver.delete_all_cookies()
            self.driver.execute_script("try { localStorage.clear(); sessionStorage.clear(); } catch(e){}")
        except Exception:
            pass

        # 3. Chạy lại quy trình đăng nhập 8 bước chuẩn (buộc làm mới force=True)
        self.log("Bắt đầu đăng nhập lại từ đầu vào Radius Portal qua IAM & Azure AD...", "info")
        core_login.run_radius_login(
            driver=self.driver,
            headless=self.headless,
            keep_open=self.keep_open,
            log_callback=self.log_cb,
            force=True
        )

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

        # Chờ các thành phần sẵn sàng
        wait = WebDriverWait(self.driver, 20)
        wait.until(EC.presence_of_element_located((
            By.XPATH,
            "//span[contains(@class, 'custom-filter_placeholder')] | "
            "//span[contains(text(), 'Nhập giá trị')] | "
            "//div[contains(@class, 'custom-filter_inputContainer')]//input | "
            "//button[contains(., 'Tìm kiếm')]"
        )))
        self.log("Đã mở trang Thông số kết nối thành công và sẵn sàng thao tác!", "success")

    def process_spampool_contract(self, shd, tac_vu=""):
        """
        Thực hiện quy trình cho 1 Hợp đồng:
        Bước 3: Điền SHD vào ô Nhập giá trị
        Bước 4: Bấm nút Tìm kiếm
        Bước 5: Bấm nút Chi Tiết
        Bước 6:
          - Nếu Tác Vụ là 'Deactive IP 0.0.0.0':
              + Không thao tác gì ở Spam Pool
              + Tại 'IPv6 Only Status' drop xuống chọn 'Deactivate'
              + Bấm nút 'Kích hoạt' để kết thúc phiên làm việc Deactive IP 0.0.0.0
          - Nếu Tác Vụ là SpamPool thông thường:
              + Tại SpamPool xổ ra chọn 'SAVECUS'
              + Xác nhận popup nhỏ 'Đồng ý' (nếu có)
              + Bấm nút 'Kích hoạt' bên dưới
        Bước 9: Bắt thông báo hệ thống và trả về (is_success, thao_tac, ket_qua)
        """
        shd = str(shd).strip()
        if not tac_vu:
            try:
                sheet_data = fetch_sheet_data()
                recs = sheet_data.get("records", [])
                for r in recs:
                    if str(r.get("SHD", "")).strip().upper() == shd.upper() and is_pending(r.get("Kết Quả"), r.get("Thao Tác")):
                        tac_vu = str(r.get("Tác Vụ", "")).strip()
                        break
                if not tac_vu:
                    for r in recs:
                        if str(r.get("SHD", "")).strip().upper() == shd.upper():
                            tac_vu = str(r.get("Tác Vụ", "")).strip()
                            break
            except Exception:
                pass

        is_deactive_ip = is_deactive_ip_task(tac_vu)
        if is_deactive_ip:
            self.log(f"--- Bắt đầu xử lý DEACTIVE IP 0.0.0.0 cho HĐ [{shd}] (Tác vụ: '{tac_vu}') ---", "info")
        else:
            self.log(f"--- Bắt đầu xử lý SpamPool cho HĐ [{shd}] ---", "info")
        wait = WebDriverWait(self.driver, 15)

        # 1. Kích hoạt và điền SHD vào ô "Nhập giá trị"
        self.log(f"Bước 3: Điền SHD [{shd}] vào ô 'Nhập giá trị'...", "info")
        target_input = None

        # Kiểm tra nếu ô input đã xuất hiện
        inps = self.driver.find_elements(By.XPATH, "//div[contains(@class, 'custom-filter_inputContainer')]//input")
        if not inps:
            # Nhấp vào placeholder để kích hoạt ô input
            placeholders = self.driver.find_elements(
                By.XPATH,
                "//span[contains(@class, 'custom-filter_placeholder')] | //span[contains(text(), 'Nhập giá trị')]"
            )
            if placeholders:
                self.log("Nhấp mở ô nhập liệu 'Nhập giá trị'...", "info")
                try:
                    self.driver.execute_script("arguments[0].click();", placeholders[0])
                except Exception:
                    placeholders[0].click()
                time.sleep(0.5)

            # Chờ ô input xuất hiện
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

            # Thử lại lần nữa
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
        self.log("Bước 4: Bấm nút [Tìm kiếm]...", "info")
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
        self.log(f"Bước 5: Bấm nút [Chi Tiết] cho HĐ [{shd}]...", "info")
        self.driver.execute_script("arguments[0].click();", btn_details[0])
        time.sleep(3)

        # 5. Chờ Popup "Cập nhật thông tin kết nối" xuất hiện
        self.log("Đang chờ popup 'Cập nhật thông tin kết nối'...", "info")
        modal = wait.until(EC.visibility_of_element_located((
            By.XPATH, "//div[contains(@class, 'ant-modal')]//div[contains(., 'Cập nhật thông tin kết nối')]/ancestor::div[contains(@class, 'ant-modal-content') or contains(@class, 'ant-modal')][1]"
        )))

        # ==============================================================
        # NHÁNH XỬ LÝ 1: DEACTIVE IP 0.0.0.0 (THEO YÊU CẦU SHEET TÁC VỤ)
        # Không thao tác gì ở SpamPool. Tại IPv6 Only Status chọn 'Deactivate' và bấm Kích hoạt.
        # ==============================================================
        if is_deactive_ip:
            self.log(f"Thực hiện tác vụ DEACTIVE IP 0.0.0.0 cho HĐ [{shd}]...", "info")
            self.log("Bỏ qua SpamPool, chuyển đến mục 'IPv6 Only Status'...", "info")
            time.sleep(1)

            ipv6_selects = self.driver.find_elements(
                By.XPATH,
                "//label[contains(text(), 'IPv6 Only Status')]/following::div[contains(@class, 'ant-select')][1] | "
                "//label[contains(text(), 'IPv6 Only Status')]/ancestor::div[1]/following-sibling::div[contains(@class, 'ant-select')] | "
                "//div[contains(@class, 'ant-modal')]//*[contains(text(), 'IPv6 Only Status')]/ancestor::div[1]/following::div[contains(@class, 'ant-select')][1]"
            )
            if not ipv6_selects:
                raise RuntimeError("Không tìm thấy dropdown 'IPv6 Only Status' trong popup!")

            ipv6_select = ipv6_selects[0]
            current_ipv6_text = ""
            try:
                val_items = ipv6_select.find_elements(By.XPATH, ".//span[contains(@class, 'ant-select-selection-item')]")
                current_ipv6_text = val_items[0].text.strip() if val_items else ipv6_select.text.strip()
            except Exception:
                pass

            self.log(f"Giá trị IPv6 Only Status hiện tại: '{current_ipv6_text}'", "info")

            # KIỂM TRA TRẠNG THÁI TRƯỚC ĐÓ:
            # 1. Giá trị trong dropdown hiện tại đã là Deactivate
            # 2. Hoặc trên thẻ thông tin tóm tắt bên trái modal hiển thị IPv6 Only Status: Deactivate
            is_already_deactive = "deactivat" in current_ipv6_text.lower()
            if not is_already_deactive:
                try:
                    left_info = self.driver.find_elements(
                        By.XPATH,
                        "//div[contains(@class, 'ant-modal')]//*[contains(text(), 'IPv6 Only Status')]/ancestor::div[1]//*[contains(text(), 'Deactivate')] | "
                        "//div[contains(@class, 'ant-modal')]//div[contains(@class, 'ant-card') or contains(@class, 'col')]//*[contains(text(), 'IPv6 Only Status')]/..//*[contains(text(), 'Deactivate')]"
                    )
                    if any(e.is_displayed() for e in left_info):
                        is_already_deactive = True
                except Exception:
                    pass

            if is_already_deactive:
                self.log(f"Hợp đồng [{shd}] ĐÃ ĐƯỢC thiết lập Deactive IP 0.0.0.0 (IPv6 Only Status: Deactivate) từ trước đó!", "success")
                self._close_modal_if_open()
                return True, "Hợp đồng đã được Deactive IP 0.0.0.0 trước đó", "Đã xử lý"

            # Mở dropdown IPv6 Only Status
            selector_el = ipv6_select.find_element(By.CLASS_NAME, "ant-select-selector")
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", selector_el)
            time.sleep(0.3)
            self.driver.execute_script("""
                var el = arguments[0];
                el.dispatchEvent(new MouseEvent('mousedown', {bubbles: true, cancelable: true, view: window}));
                el.dispatchEvent(new MouseEvent('mouseup', {bubbles: true, cancelable: true, view: window}));
                el.dispatchEvent(new MouseEvent('click', {bubbles: true, cancelable: true, view: window}));
            """, selector_el)
            time.sleep(1)

            dropdown = wait.until(EC.presence_of_element_located((
                By.XPATH, "//div[contains(@class, 'ant-select-dropdown') and not(contains(@class, 'ant-select-dropdown-hidden'))]"
            )))
            opts = dropdown.find_elements(
                By.XPATH,
                ".//div[contains(@class, 'ant-select-item-option') and (.//div[text()='Deactivate'] or @title='Deactivate')]"
            )
            if not opts:
                opts = [o for o in dropdown.find_elements(By.XPATH, ".//div[contains(@class, 'ant-select-item-option')]")
                        if "deactivat" in o.text.lower() or "deactivat" in (o.get_attribute("title") or "").lower()]

            if not opts:
                raise RuntimeError("Không tìm thấy tùy chọn 'Deactivate' trong danh sách IPv6 Only Status!")

            target_opt = opts[0]
            self.log(f"Đã chọn tùy chọn: '{target_opt.text.strip()}'", "info")
            self.driver.execute_script("""
                var el = arguments[0];
                el.scrollIntoView({block: 'center'});
                el.dispatchEvent(new MouseEvent('mousedown', {bubbles: true, cancelable: true, view: window}));
                el.dispatchEvent(new MouseEvent('mouseup', {bubbles: true, cancelable: true, view: window}));
                el.dispatchEvent(new MouseEvent('click', {bubbles: true, cancelable: true, view: window}));
            """, target_opt)
            time.sleep(1)

            # Bấm nút Kích hoạt bên dưới popup
            self.log("Bấm nút [Kích hoạt] để hoàn tất phiên làm việc Deactive IP 0.0.0.0...", "info")
            btn_kich_hoat = wait.until(EC.element_to_be_clickable((
                By.XPATH,
                "//div[contains(@class, 'ant-modal')]//button[contains(., 'Kích hoạt')] | //button[contains(., 'Kích hoạt')]"
            )))
            self.driver.execute_script("arguments[0].click();", btn_kich_hoat)
            time.sleep(2.5)

            # Bắt phản hồi hệ thống
            self.log("Đang chờ phản hồi thông báo từ hệ thống Radius...", "info")
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
                self.log(f"Kết quả HĐ [{shd}]: Không có gì thay đổi -> Hợp đồng đã được Deactive IP 0.0.0.0 trước đó", "success")
                return True, "Hợp đồng đã được Deactive IP 0.0.0.0 trước đó", "Đã xử lý"
            elif "thanh cong" in msg_clean:
                self.log(f"Kết quả HĐ [{shd}]: Deactive IP 0.0.0.0 thành công!", "success")
                return True, "thành công kết thúc", "Đã xử lý"
            elif final_msg:
                if any(w in msg_clean for w in ("loi", "that bai", "error", "khong the")):
                    self.log(f"Kết quả HĐ [{shd}]: Thông báo lỗi: {final_msg}", "warning")
                    return False, final_msg, "Lỗi"
                return True, final_msg, "Đã xử lý"
            else:
                self.log(f"Đã hoàn tất thao tác Deactive IP 0.0.0.0 cho HĐ [{shd}]!", "success")
                return True, "thành công kết thúc", "Đã xử lý"

        # ==============================================================
        # NHÁNH XỬ LÝ 2: SPAMPOOL SAVECUS THÔNG THƯỜNG (GIỮ NGUYÊN)
        # ==============================================================
        # 6. Tìm ô chọn Spam Pool
        self.log("Bước 6: Kiểm tra mục Spam Pool trong popup...", "info")
        time.sleep(1)

        # Tìm dropdown Spam Pool qua sibling của label 'Spam Pool'
        spampool_selects = self.driver.find_elements(
            By.XPATH,
            "//label[contains(text(), 'Spam Pool')]/ancestor::div[1]/following-sibling::div[contains(@class, 'ant-select')] | "
            "//label[contains(text(), 'Spam Pool')]/ancestor::div[2]//div[contains(@class, 'ant-select')] | "
            "//div[contains(@class, 'ant-modal')]//*[text()='Spam Pool']/ancestor::div[contains(@class, 'flex') or self::div][1]//div[contains(@class, 'ant-select')]"
        )

        if not spampool_selects:
            raise RuntimeError("Không tìm thấy dropdown 'Spam Pool' bên trong popup!")

        spampool_select = spampool_selects[0]

        # Kiểm tra giá trị hiện tại của Spam Pool
        current_sp_text = ""
        try:
            val_items = spampool_select.find_elements(By.XPATH, ".//span[contains(@class, 'ant-select-selection-item')]")
            if val_items:
                current_sp_text = val_items[0].text.strip()
            else:
                current_sp_text = spampool_select.text.strip()
        except Exception:
            pass

        current_sp_val = current_sp_text.strip().upper()
        self.log(f"Giá trị Spam Pool hiện tại: '{current_sp_text}'", "info")

        # KIỂM TRA CHÍNH XÁC: Chỉ khi đúng chính xác 'SAVECUS' mới xem là đã cập nhật (SAVECUS_VIP != SAVECUS)
        if current_sp_val == "SAVECUS":
            self.log(f"Hợp đồng [{shd}] ĐÃ ĐƯỢC thiết lập SpamPool đúng 'SAVECUS' từ trước đó!", "success")
            self._close_modal_if_open()
            return True, "HD đã được SpamPool Trước Đó", "Đã xử lý"

        # Nhấp vào dropdown Spam Pool để xổ danh sách
        self.log("Nhấp mở danh sách Spam Pool để chọn SAVECUS...", "info")
        selector_el = spampool_select.find_element(By.CLASS_NAME, "ant-select-selector")
        self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", selector_el)
        time.sleep(0.3)

        self.driver.execute_script("""
            var el = arguments[0];
            el.dispatchEvent(new MouseEvent('mousedown', {bubbles: true, cancelable: true, view: window}));
            el.dispatchEvent(new MouseEvent('mouseup', {bubbles: true, cancelable: true, view: window}));
            el.dispatchEvent(new MouseEvent('click', {bubbles: true, cancelable: true, view: window}));
        """, selector_el)
        time.sleep(1.2)

        # Chờ dropdown hiển thị
        dropdown = wait.until(EC.presence_of_element_located((
            By.XPATH, "//div[contains(@class, 'ant-select-dropdown') and not(contains(@class, 'ant-select-dropdown-hidden'))]"
        )))
        holders = dropdown.find_elements(By.XPATH, ".//div[contains(@class, 'rc-virtual-list-holder')]")
        holder = holders[0] if holders else dropdown

        # Cuộn danh sách xuống để Ant Design mount item SAVECUS vào DOM (SAVECUS nằm dưới, sau SAVECUS_VIP)
        self.log("Cuộn danh sách xuống tìm đúng tùy chọn 'SAVECUS' (không phải SAVECUS_VIP)...", "info")
        target_opt = None
        for scroll_offset in [300, 200, 400, 150, 0]:
            self.driver.execute_script(f"arguments[0].scrollTop = {scroll_offset};", holder)
            time.sleep(0.6)

            rendered_opts = dropdown.find_elements(
                By.XPATH,
                ".//div[contains(@class, 'ant-select-item-option') and (.//div[text()='SAVECUS'] or @title='SAVECUS')]"
            )
            # Lọc CHÍNH XÁC chỉ lấy SAVECUS, TUYỆT ĐỐI không lấy SAVECUS_VIP
            exact_matches = [
                opt for opt in rendered_opts
                if opt.text.strip().upper() == "SAVECUS" or opt.get_attribute("title") == "SAVECUS"
            ]
            if exact_matches:
                target_opt = exact_matches[0]
                break

        if not target_opt:
            raise RuntimeError("Không tìm thấy tùy chọn 'SAVECUS' chính xác sau khi cuộn danh sách!")

        self.log(f"Đã tìm thấy tùy chọn chính xác: '{target_opt.text.strip()}' -> Tiến hành chọn...", "info")
        self.driver.execute_script("""
            var el = arguments[0];
            el.scrollIntoView({block: 'center'});
            el.dispatchEvent(new MouseEvent('mousedown', {bubbles: true, cancelable: true, view: window}));
            el.dispatchEvent(new MouseEvent('mouseup', {bubbles: true, cancelable: true, view: window}));
            el.dispatchEvent(new MouseEvent('click', {bubbles: true, cancelable: true, view: window}));
        """, target_opt)
        time.sleep(1.5)

        # Kiểm tra giá trị sau khi chọn
        try:
            val_after = spampool_select.text.strip()
            self.log(f"Giá trị Spam Pool sau khi chọn: '{val_after}'", "info")
        except Exception:
            pass

        # 7. Kiểm tra Popup nhỏ "Xác nhận cập nhật spam pool"
        self.log("Bước 7: Kiểm tra popup xác nhận 'Xác nhận cập nhật spam pool'...", "info")
        try:
            btn_dong_y = WebDriverWait(self.driver, 4).until(EC.element_to_be_clickable((
                By.XPATH,
                "//div[contains(., 'Xác nhận cập nhật spam pool') or contains(., 'savecus')]/ancestor::div[contains(@class, 'ant-modal')]//button[contains(., 'Đồng ý')] | //button[contains(., 'Đồng ý')]"
            )))
            self.log("Phát hiện popup xác nhận số lượng SAVECUS -> Bấm [Đồng ý]...", "info")
            self.driver.execute_script("arguments[0].click();", btn_dong_y)
            time.sleep(1.5)
        except Exception:
            self.log("Không xuất hiện popup cảnh báo xác nhận, tiếp tục...", "info")

        # 8. Bấm nút Kích hoạt bên dưới
        self.log("Bước 8: Bấm nút [Kích hoạt] bên dưới popup...", "info")
        btn_kich_hoat = wait.until(EC.element_to_be_clickable((
            By.XPATH,
            "//div[contains(@class, 'ant-modal')]//button[contains(., 'Kích hoạt')] | //button[contains(., 'Kích hoạt')]"
        )))
        self.driver.execute_script("arguments[0].click();", btn_kich_hoat)
        time.sleep(2.5)

        # 9. Đợi phản hồi thông báo hệ thống
        self.log("Bước 9: Đang chờ phản hồi thông báo từ hệ thống Radius...", "info")
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

        # Kiểm tra điều kiện thông báo
        if "khong co gi thay doi" in msg_clean:
            self.log(f"Kết quả HĐ [{shd}]: Không có gì thay đổi -> HD đã được SpamPool Trước Đó", "success")
            return True, "HD đã được SpamPool Trước Đó", "Đã xử lý"
        elif "thanh cong" in msg_clean:
            self.log(f"Kết quả HĐ [{shd}]: Cập nhật SpamPool thành công!", "success")
            return True, "thành công kết thúc", "Đã xử lý"
        elif final_msg:
            self.log(f"Kết quả HĐ [{shd}]: Thông báo khác: {final_msg}", "warning")
            return False, final_msg, "Lỗi"
        else:
            self.log(f"Đã hoàn tất thao tác Kích hoạt cho HĐ [{shd}]!", "success")
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
        """Xử lý danh sách các hợp đồng cần SpamPool."""
        results = []
        cache = load_cache()

        try:
            self.init_driver()
            self.navigate_to_network_connection()

            # Lọc các bản ghi cần xử lý: Chưa cập nhật hoặc chưa xử lý
            pending_records = [r for r in records if is_pending(r.get("Kết Quả"), r.get("Thao Tác"))]
            if not pending_records:
                self.log("Không có hợp đồng nào có trạng thái 'Chưa cập nhật' cần xử lý!", "info")
                return []

            self.log(f"Bắt đầu xử lý {len(pending_records)} hợp đồng cần SpamPool...", "info")

            for idx, r in enumerate(pending_records):
                if self._stop_requested:
                    self.log("Đã dừng tiến trình theo yêu cầu của người dùng.", "warning")
                    break

                shd = str(r.get("SHD", "")).strip()
                tac_vu = str(r.get("Tác Vụ", "")).strip()
                if not shd:
                    continue

                task_type_str = f" [Tác vụ: {tac_vu}]" if tac_vu else ""
                self.log(f"\n▶ [{idx + 1}/{len(pending_records)}] Xử lý hợp đồng: {shd}{task_type_str}", "info")

                try:
                    ok, thao_tac, ket_qua = self.process_spampool_contract(shd, tac_vu=tac_vu)
                    now_str = time.strftime("%d/%m/%Y %H:%M:%S")

                    r["Thao Tác"] = thao_tac
                    r["Kết Quả"] = ket_qua
                    r["Ngày Cập Nhật"] = now_str

                    # Cập nhật cache
                    cache_item = {
                        "ket_qua": ket_qua,
                        "thao_tac": thao_tac,
                        "time": now_str,
                        "timestamp_epoch": time.time()
                    }
                    cache[shd] = cache_item
                    row_id = str(r.get("ID", "")).strip()
                    if row_id:
                        cache[f"{shd}_{row_id}"] = cache_item
                    tv_k = "deactive" if is_deactive_ip_task(tac_vu) else "spampool"
                    cache[f"{shd}_{tv_k}"] = cache_item
                    save_cache(cache)

                    results.append({
                        "shd": shd,
                        "status": ket_qua,
                        "thao_tac": thao_tac,
                        "message": thao_tac
                    })

                    # Gửi Webhook cập nhật Google Sheet nếu có
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

            self.log(f"\n🎉 HOÀN TẤT TIẾN TRÌNH SPAMPOOL: Đã xử lý {len(results)} hợp đồng!", "success")
            return results

        except Exception as e:
            self.log(f"❌ Tiến trình SpamPool gặp sự cố: {e}", "error")
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
            self.log("Đã tắt trình duyệt Radius Portal.", "info")

if __name__ == "__main__":
    data = fetch_sheet_data()
    print(f"Sheet fetched: {data.get('count')} records")

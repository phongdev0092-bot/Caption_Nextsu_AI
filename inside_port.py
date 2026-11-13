# -*- coding: utf-8 -*-
"""
COMPONENT BACKEND: AUTO CẤP/THU HỒI PORT
Hệ thống: Port FPT (http://port.fpt.net) - Đăng nhập bằng tài khoản AM (IAM -> Azure AD SSO)
Google Sheet ID: 1Sw-qSbLzvVdcW4rj7ywEZBEzKI6w5M82EQeYJUpdx7M | GID: 1103185024
Cột: ID | Tác Vụ | Email | MSNV | Account Inside | Số Hợp Đồng | Tập Điểm | Port | Ngày Cập Nhật | Thao Tác

Quy trình tự động hóa Thu hồi Port:
Bước 1: Truy cập http://port.fpt.net -> Chuyển qua giao diện IAM -> Bấm Azure AD -> Đăng nhập tài khoản AM (như SpamPool)
Bước 2: Tại menu trái (leftFrame): Bấm FTTH NEW >> Hợp đồng >> Tìm kiếm
Bước 3: Tại màn hình chính (mainFrame):
  - Mục 'Tìm kiếm theo?' (#cbo_typeSearch): chọn 'Hợp đồng' (value='1')
  - Ô 'Hợp đồng' (#txtContract): điền Số Hợp Đồng (cột F từ Sheet)
  - Bấm nút 'Tìm kiếm' (#btnSearch)
Bước 4: Bảng kết quả (#kGrid) hiện ra -> Bấm vào Số Hợp Đồng (màu đỏ, class='link') để chuyển sang trang 'Cấp port Hợp đồng'
Bước 5: Tại trang 'Cấp port Hợp đồng':
  - Copy 'Thông số thi công: ...' (màu đỏ, #dvTSTC) dán vào ô 'Ghi chú' (#txtDescription)
  - Thay đổi 'Tình trạng port' (#cbo_statusPort) -> chọn 'Thu hồi port' (value='2')
  - Bấm nút 'Cập nhật' (#btnUpdate)
Bước 6: Kết thúc chu trình -> Cập nhật lại Google Sheet cột J (Thao Tác) = 'Đã xử lý'
"""

import os
import sys
import time
import json
import re
import shutil
import urllib.request
import unicodedata
import pandas as pd
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC

import core_login

DEFAULT_SHEET_ID = "1Sw-qSbLzvVdcW4rj7ywEZBEzKI6w5M82EQeYJUpdx7M"
GID_PORT = "966043489"
PORT_NO_SHD_MSG = (
    "Không thành công : Hệ thống hiện chỉ hỗ trợ thu hồi Port theo Số Hợp Đồng (SHD). "
    "Tính năng thu hồi theo Thông số thi công (Tập điểm/Port) đang được phát triển, "
    "vui lòng cung cấp SHD để được xử lý."
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PORT_CACHE_FILE = os.path.join(BASE_DIR, "port_status_cache.json")


def get_port_profile_dir():
    """Lấy đường dẫn thư mục lưu Profile phiên hệ thống Port (tách biệt để không xung đột lock với Radius)."""
    port_dir = os.path.join(BASE_DIR, "Port_SessionProfile")
    if not os.path.exists(port_dir):
        os.makedirs(port_dir, exist_ok=True)
        radius_dir = core_login.get_radius_profile_dir()
        if os.path.exists(radius_dir):
            try:
                src_def = os.path.join(radius_dir, "Default")
                dst_def = os.path.join(port_dir, "Default")
                if os.path.exists(src_def) and not os.path.exists(dst_def):
                    shutil.copytree(
                        src_def,
                        dst_def,
                        ignore=shutil.ignore_patterns("*.lock", "Singleton*", "*Lock*", "DevToolsActivePort")
                    )
            except Exception:
                pass
    return port_dir


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
    if os.path.exists(PORT_CACHE_FILE):
        try:
            with open(PORT_CACHE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def save_cache(data):
    try:
        with open(PORT_CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[CACHE ERROR] {e}")


def parse_tstc_info(tstc_text):
    """
    Tách Tập Điểm và Port chuẩn từ chuỗi Thông số thi công.
    Ví dụ: 'Thông số thi công: HCMP515.0195/HO-2/2-XGS'
      -> Tập điểm: 'HCMP515.0195/HO'
      -> Port (giá trị sau dấu /): '2'
    """
    if not tstc_text:
        return "", ""
    raw = str(tstc_text).strip()
    raw = re.sub(r'^.*?thông\s*số\s*thi\s*công\s*:\s*', '', raw, flags=re.IGNORECASE).strip()
    raw = re.sub(r'^.*?thong\s*so\s*thi\s*cong\s*:\s*', '', raw, flags=re.IGNORECASE).strip()
    if not raw:
        return "", ""

    # Mẫu chuẩn FTTH: <Tập điểm>-<Splitter>/<Port>-<Loại> (VD: HCMP515.0195/HO-2/2-XGS)
    m = re.match(r'^(.+?)-[^/-]+/(\d+)', raw)
    if m:
        return m.group(1).strip(), m.group(2).strip()

    # Fallback nếu có dấu /
    if "/" in raw:
        parts = raw.split("/")
        tap_diem = "/".join(parts[:-1]).split("-")[0].strip() if len(parts) > 1 else parts[0].strip()
        m_port = re.match(r'^(\d+)', parts[-1].strip())
        port_val = m_port.group(1) if m_port else parts[-1].split("-")[0].strip()
        return tap_diem, port_val

    return raw, ""


def is_thu_hoi_port_task(tac_vu):
    """Kiểm tra Tác Vụ có phải là 'Thu Hồi Port' hay không."""
    tv = remove_accents(str(tac_vu or "")).lower().strip()
    if not tv:
        return True
    return "thu hoi" in tv


def is_processed(ngay_cap_nhat, thao_tac):
    """Kiểm tra hợp đồng/port đã được xử lý xong hay chưa."""
    tt = remove_accents(str(thao_tac or "")).lower().strip()
    ng = remove_accents(str(ngay_cap_nhat or "")).lower().strip()

    if "chua cap nhat" in tt or "chua xu ly" in tt or "chua xu li" in tt or not tt:
        return False
    if any(w in tt for w in ("thanh cong", "da xu ly", "da xu li", "da cap", "da thu hoi", "hoan tat", "da cap nhat")):
        return True
    if any(w in tt for w in ("loi", "that bai", "khong thanh cong", "error", "khong tim thay", "chi ho tro", "dang duoc phat trien", "dang phat trien")):
        return True
    if "chua cap nhat" in ng or "chua xu ly" in ng or "chua xu li" in ng or not ng:
        return False
    return bool(tt and tt not in ("chua cap nhat", "chua xu ly", "chua xu li", "nan"))


def is_pending(ngay_cap_nhat, thao_tac):
    """
    Khi phát hiện Ngày Cập Nhật hoặc Thao Tác là 'Chưa cập nhật' (hoặc Chưa xử lý, rỗng)
    thì tự động xử lý.
    """
    if is_processed(ngay_cap_nhat, thao_tac):
        return False
    tt = remove_accents(str(thao_tac or "")).lower().strip()
    ng = remove_accents(str(ngay_cap_nhat or "")).lower().strip()
    if "chua cap nhat" in tt or "chua xu ly" in tt or "chua xu li" in tt or not tt:
        return True
    if "chua cap nhat" in ng or "chua xu ly" in ng or "chua xu li" in ng or not ng:
        return True
    return False


def fetch_sheet_data(sheet_id=DEFAULT_SHEET_ID, gid=GID_PORT):
    """Đọc dữ liệu từ Google Sheet qua gviz CSV."""
    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&gid={gid}&_t={int(time.time() * 1000)}"
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        content = urllib.request.urlopen(req, timeout=12).read().decode('utf-8', errors='ignore')
        import io
        df = pd.read_csv(io.StringIO(content), dtype=str)
        df = df.fillna("")

        cache = load_cache()
        records = []

        for raw in df.to_dict(orient="records"):
            rec = {}
            for k, v in raw.items():
                norm_k = normalize_nfc(k)
                norm_v = normalize_nfc(v) if isinstance(v, str) else str(v or "")
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
                elif "hop dong" in k_clean or "shd" in k_clean:
                    rec["Số Hợp Đồng"] = norm_v
                    rec["SHD"] = norm_v
                elif "tap diem" in k_clean:
                    rec["Tập Điểm"] = norm_v
                elif "port" in k_clean:
                    if norm_v.endswith(".0"):
                        norm_v = norm_v[:-2]
                    rec["Port"] = norm_v
                elif "nguyen nhan" in k_clean or "ly do" in k_clean:
                    rec["Nguyên Nhân 1"] = norm_v
                elif "ngay" in k_clean:
                    rec["Ngày Cập Nhật"] = norm_v
                elif "ket qua" in k_clean:
                    rec["Kết Quả"] = norm_v
                elif "thao tac" in k_clean:
                    rec["Thao Tác"] = norm_v
                else:
                    rec[norm_k] = norm_v

            if not rec.get("SHD") and rec.get("Số Hợp Đồng"):
                rec["SHD"] = rec["Số Hợp Đồng"]
            if not rec.get("Số Hợp Đồng") and rec.get("SHD"):
                rec["Số Hợp Đồng"] = rec["SHD"]

            # Đồng bộ với local cache nếu vừa xử lý trong phiên gần đây (< 90s) hoặc có force_override
            shd = str(rec.get("Số Hợp Đồng") or rec.get("SHD") or "").strip()
            row_id = str(rec.get("ID", "")).strip()
            cache_key = None
            if f"{shd}_{row_id}" in cache:
                cache_key = f"{shd}_{row_id}"
            elif row_id and f"ROW_{row_id}" in cache:
                cache_key = f"ROW_{row_id}"
            elif shd and shd in cache:
                cache_key = shd

            if cache_key and cache_key in cache:
                c_item = cache[cache_key]
                c_tt = c_item.get("thao_tac", "") if isinstance(c_item, dict) else str(c_item)
                c_kq = c_item.get("ket_qua", "") if isinstance(c_item, dict) else ""
                c_time = c_item.get("time", "") if isinstance(c_item, dict) else ""
                c_ts = c_item.get("timestamp_epoch", 0) if isinstance(c_item, dict) else 0
                c_td = c_item.get("tap_diem", "") if isinstance(c_item, dict) else ""
                c_port = c_item.get("port", "") if isinstance(c_item, dict) else ""
                force_ov = c_item.get("force_override", False) if isinstance(c_item, dict) else False

                current_tt = str(rec.get("Thao Tác", "")).strip()
                current_ng = str(rec.get("Ngày Cập Nhật", "")).strip()

                is_sheet_raw_pending = ("chưa" in current_tt.lower() or not current_tt or "chưa" in current_ng.lower() or not current_ng)
                is_recent = (time.time() - c_ts < 90) if c_ts else False

                if force_ov or (is_recent and is_sheet_raw_pending):
                    rec["Thao Tác"] = c_tt
                    if c_kq:
                        rec["Kết Quả"] = c_kq
                    if c_time:
                        rec["Ngày Cập Nhật"] = c_time
                    if c_td:
                        rec["Tập Điểm"] = c_td
                    if c_port:
                        rec["Port"] = c_port
                elif not is_sheet_raw_pending and not current_tt and c_tt:
                    rec["Thao Tác"] = c_tt
                    if c_kq:
                        rec["Kết Quả"] = c_kq

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
            "message": str(e),
            "count": 0,
            "records": []
        }


class InsidePortAutomation:
    def __init__(self, headless=False, keep_open=False, log_cb=None):
        self.headless = headless
        self.keep_open = keep_open
        self.log_cb = log_cb or self._default_log
        self.driver = None
        self._stop_requested = False
        self.last_tap_diem = ""
        self.last_port = ""
        self.last_tstc = ""

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
        self.log("Đã nhận yêu cầu dừng tiến trình Cấp/Thu Hồi Port!", "warning")

    def init_driver(self):
        self.log("Khởi tạo trình duyệt Chrome cho Hệ thống Port (port.fpt.net)...", "info")
        p_dir = get_port_profile_dir()
        self.driver = core_login.create_driver_with_retry(
            headless=self.headless,
            profile_dir=p_dir,
            keep_open=self.keep_open,
            max_retries=2,
            log_cb=self.log_cb
        )
        return self.driver

    def login_port_system(self, force=False):
        """
        Đăng nhập vào http://port.fpt.net bằng tài khoản AM (qua IAM & Microsoft Azure AD SSO):
        - Truy cập http://port.fpt.net
        - Chuyển sang giao diện IAM -> Bấm Azure AD
        - Điền tài khoản AM & mật khẩu -> Stay signed in (Yes)
        - Chờ về trang http://port.fpt.net/Index.aspx
        """
        config = core_login.load_config()
        am_acc = core_login.get_am_account_info(config)
        username = am_acc["username"]
        if "@" not in username:
            username = f"{username}@fpt.net"
        password = am_acc["password"]

        self.log("Bước 1: Điều hướng tới http://port.fpt.net ...", "info")
        self.driver.get("http://port.fpt.net")
        time.sleep(2.5)

        if force:
            self.log("Làm mới phiên đăng nhập Port (xóa cookie port.fpt.net & storage)...", "info")
            try:
                self.driver.delete_all_cookies()
                self.driver.execute_script("try { localStorage.clear(); sessionStorage.clear(); } catch(e){}")
            except Exception:
                pass
            self.driver.get("http://port.fpt.net")
            time.sleep(2.5)

        curr_url = (self.driver.current_url or "").lower()
        if not force and "port.fpt.net" in curr_url and "iam.fpt" not in curr_url and "loginpage" not in curr_url:
            # Kiểm tra xem bên trong leftFrame có bị redirect về IAM do hết hạn phiên không
            frame_expired = False
            iam_frame_url = ""
            try:
                self.driver.switch_to.default_content()
                self.driver.switch_to.frame("leftFrame")
                lf_url = (self.driver.execute_script("return window.location.href || '';") or "").lower()
                if "iam.fpt" in lf_url or "login" in lf_url:
                    frame_expired = True
                    iam_frame_url = lf_url
                else:
                    ftth_els = self.driver.find_elements(By.XPATH, "//a[normalize-space(text())='FTTH NEW']")
                    if not ftth_els:
                        frame_expired = True
            except Exception:
                frame_expired = True
            finally:
                try:
                    self.driver.switch_to.default_content()
                except Exception:
                    pass

            if not frame_expired:
                self.log(f"Đã đăng nhập sẵn vào hệ thống Port! ({self.driver.current_url})", "success")
                return True
            else:
                self.log("Phiên Port trong frame đã hết hạn -> Thực hiện đăng nhập lại...", "warning")
                if iam_frame_url and "iam.fpt" in iam_frame_url:
                    self.driver.get(iam_frame_url)
                else:
                    try:
                        self.driver.delete_all_cookies()
                    except Exception:
                        pass
                    self.driver.get("http://port.fpt.net")
                time.sleep(2.5)

        wait = WebDriverWait(self.driver, 15)

        # Nếu có nút đăng nhập IAM trên trang hoặc đã tự chuyển sang iam.fpt.net / iam.fpt.vn
        curr_url = (self.driver.current_url or "").lower()
        if "iam.fpt" not in curr_url and "login.microsoftonline.com" not in curr_url:
            iam_btns = self.driver.find_elements(
                By.XPATH,
                "//button[contains(., 'IAM')] | //a[contains(., 'IAM')] | //input[contains(@value, 'IAM')]"
            )
            disp_iam = [b for b in iam_btns if b.is_displayed()]
            if disp_iam:
                self.log("Nhấn nút đăng nhập IAM...", "info")
                self.driver.execute_script("arguments[0].click();", disp_iam[0])
                time.sleep(2.5)

        # Tại giao diện IAM -> Bấm Azure AD
        curr_url = (self.driver.current_url or "").lower()
        if "iam.fpt" in curr_url:
            self.log("Bước 2: Tại giao diện IAM, nhấn chọn [Azure AD]...", "info")
            btn_azure = wait.until(EC.element_to_be_clickable((
                By.XPATH,
                "//a[contains(., 'Azure AD')] | //button[contains(., 'Azure AD')] | //*[@id='zocial-azure-ad'] | //*[contains(text(), 'Azure AD')]"
            )))
            self.driver.execute_script("arguments[0].click();", btn_azure)
            time.sleep(2.5)

        # Chờ chuyển sang Microsoft hoặc đã vào thẳng port.fpt.net
        try:
            WebDriverWait(self.driver, 12).until(
                lambda d: "login.microsoftonline.com" in (d.current_url or "").lower() or (
                    "port.fpt.net" in (d.current_url or "").lower() and "iam.fpt" not in (d.current_url or "").lower()
                )
            )
        except Exception:
            pass

        curr_url = (self.driver.current_url or "").lower()
        if "login.microsoftonline.com" in curr_url:
            base_user = username.split("@")[0].lower()
            picker = self.driver.find_elements(
                By.XPATH,
                f"//div[contains(@data-test-id, '{username}') or contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{base_user}') or contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{username.lower()}') or contains(@data-username, '{username}')]"
            )
            displayed_pickers = [p for p in picker if p.is_displayed()]
            if displayed_pickers:
                self.log(f"Chọn tài khoản AM đã lưu: {username}", "info")
                try:
                    displayed_pickers[0].click()
                except Exception:
                    self.driver.execute_script("arguments[0].click();", displayed_pickers[0])
                time.sleep(2)
            else:
                emails = [e for e in self.driver.find_elements(By.XPATH, "//input[@type='email' or @name='loginfmt' or @id='i0116']") if e.is_displayed()]
                if emails:
                    self.log(f"Điền tài khoản AM: {username}", "info")
                    target_email = emails[0]
                    target_email.send_keys(Keys.CONTROL + "a")
                    target_email.send_keys(Keys.BACKSPACE)
                    time.sleep(0.2)
                    target_email.send_keys(username)
                    time.sleep(0.5)

                    btn_next = wait.until(EC.element_to_be_clickable((
                        By.XPATH, "//input[@type='submit' or @id='idSIButton9' or @value='Next'] | //button[@type='submit' or @id='idSIButton9']"
                    )))
                    self.driver.execute_script("arguments[0].click();", btn_next)
                    time.sleep(2.5)

            pass_elem = None
            for _ in range(12):
                curr = (self.driver.current_url or "").lower()
                if "port.fpt.net" in curr and "iam.fpt" not in curr:
                    break
                inps = [p for p in self.driver.find_elements(By.XPATH, "//input[@type='password' or @name='passwd' or @id='i0118']") if p.is_displayed()]
                if inps:
                    pass_elem = inps[0]
                    break
                btn_yes = [b for b in self.driver.find_elements(By.XPATH, "//input[@id='idSIButton9' or @value='Yes'] | //button[@id='idSIButton9' or contains(text(), 'Yes')]") if b.is_displayed()]
                if btn_yes:
                    break
                time.sleep(0.8)

            if pass_elem:
                self.log("Điền mật khẩu tài khoản AM...", "info")
                pass_elem.send_keys(Keys.CONTROL + "a")
                pass_elem.send_keys(Keys.BACKSPACE)
                time.sleep(0.2)
                pass_elem.send_keys(password)
                time.sleep(0.5)

                btn_signin = wait.until(EC.element_to_be_clickable((
                    By.XPATH, "//input[@type='submit' or @id='idSIButton9' or @value='Sign in'] | //button[@type='submit' or @id='idSIButton9']"
                )))
                self.driver.execute_script("arguments[0].click();", btn_signin)
                time.sleep(2.5)

            try:
                btn_yes = WebDriverWait(self.driver, 6).until(EC.element_to_be_clickable((
                    By.XPATH, "//input[@id='idSIButton9' or @value='Yes'] | //button[@id='idSIButton9' or contains(text(), 'Yes')]"
                )))
                self.log("Nhấn [Yes] duy trì đăng nhập...", "info")
                self.driver.execute_script("arguments[0].click();", btn_yes)
                time.sleep(2.5)
            except Exception:
                pass

        self.log("Đang chờ chuyển hướng vào trang chủ Port (port.fpt.net)...", "info")
        WebDriverWait(self.driver, 35).until(
            lambda d: "port.fpt.net" in (d.current_url or "").lower() and "iam.fpt" not in (d.current_url or "").lower() and "microsoftonline" not in (d.current_url or "").lower()
        )
        time.sleep(1.5)
        self.log(f"Đăng nhập thành công vào hệ thống Port! ({self.driver.current_url})", "success")
        return True

    def _open_ftth_search_from_menu(self):
        wait = WebDriverWait(self.driver, 10)
        self.driver.switch_to.default_content()
        wait.until(EC.frame_to_be_available_and_switch_to_it((By.NAME, "leftFrame")))

        # 1. Click FTTH NEW
        ftth_new = wait.until(EC.presence_of_element_located((
            By.XPATH, "//a[normalize-space(text())='FTTH NEW']"
        )))
        self.driver.execute_script("arguments[0].click();", ftth_new)
        time.sleep(1.2)

        # 2. Click Hợp đồng (dưới FTTH NEW)
        hop_dong = wait.until(EC.presence_of_element_located((
            By.XPATH, "//a[normalize-space(text())='Hợp đồng']"
        )))
        self.driver.execute_script("arguments[0].click();", hop_dong)
        time.sleep(1.2)

        # 3. Click Tìm kiếm (dưới Hợp đồng)
        tim_kiem = wait.until(EC.presence_of_element_located((
            By.XPATH, "//a[normalize-space(text())='Tìm kiếm']"
        )))
        self.driver.execute_script("arguments[0].click();", tim_kiem)
        time.sleep(2.5)

        # 4. Chuyển sang mainFrame
        self.driver.switch_to.default_content()
        wait.until(EC.frame_to_be_available_and_switch_to_it((By.NAME, "mainFrame")))
        wait.until(EC.presence_of_element_located((By.ID, "cbo_typeSearch")))
        wait.until(EC.presence_of_element_located((By.ID, "txtContract")))

    def navigate_to_ftth_new_search(self):
        """
        Điều hướng menu trái (leftFrame):
        Bấm FTTH NEW >> Hợp đồng >> Tìm kiếm
        Sau đó chuyển sang mainFrame chờ ô tìm kiếm sẵn sàng.
        """
        self.login_port_system()
        self.log("Chuyển sang menu trái (leftFrame): Chọn FTTH NEW >> Hợp đồng >> Tìm kiếm...", "info")
        try:
            self._open_ftth_search_from_menu()
        except Exception:
            self.log("Phiên Port đã hết hạn khi mở menu -> Đăng nhập lại và thử lại...", "warning")
            self.login_port_system(force=True)
            self._open_ftth_search_from_menu()
        self.log("Đã mở màn hình 'Tìm kiếm hợp đồng' thành công!", "success")

    def process_port_contract(self, shd, tac_vu="", tap_diem="", port_num=""):
        """
        Thực hiện chu trình Thu hồi Port cho 1 Số Hợp Đồng (SHD):
        1. Tại trang Tìm kiếm hợp đồng:
           - Tìm kiếm theo? (#cbo_typeSearch) -> chọn 'Hợp đồng' (value='1')
           - Điền SHD vào ô Hợp đồng (#txtContract)
           - Bấm nút Tìm kiếm (#btnSearch)
        2. Tại bảng kết quả (#kGrid):
           - Bấm vào Số Hợp Đồng (màu đỏ, class='link') để chuyển sang trang 'Cấp port Hợp đồng'
        3. Tại trang 'Cấp port Hợp đồng':
           - Copy 'Thông số thi công' (màu đỏ, #dvTSTC) dán vào ô 'Ghi chú' (#txtDescription)
           - Thay đổi 'Tình trạng port' (#cbo_statusPort) -> chọn 'Thu hồi port' (value='2')
           - Bấm nút 'Cập nhật' (#btnUpdate)
        4. Trả về (ok, thao_tac) với thao_tac = 'Đã xử lý' khi hoàn tất.
        """
        shd = str(shd or "").strip()
        if not shd:
            return False, PORT_NO_SHD_MSG

        self.log(f"--- Bắt đầu xử lý Thu hồi Port cho HĐ [{shd}] ---", "info")
        wait = WebDriverWait(self.driver, 15)

        # Đảm bảo đang ở trong mainFrame tại trang Tìm kiếm hợp đồng
        try:
            self.driver.switch_to.default_content()
            self.driver.switch_to.frame("mainFrame")
            inps = self.driver.find_elements(By.ID, "txtContract")
            if not inps:
                self.navigate_to_ftth_new_search()
        except Exception:
            self.navigate_to_ftth_new_search()

        # Bước 1: Chọn 'Tìm kiếm theo?' -> 'Hợp đồng' (value='1')
        self.log("Chọn 'Tìm kiếm theo?' -> 'Hợp đồng'...", "info")
        cbo_type = wait.until(EC.presence_of_element_located((By.ID, "cbo_typeSearch")))
        try:
            Select(cbo_type).select_by_value("1")
        except Exception:
            pass
        self.driver.execute_script("$('#cbo_typeSearch').val('1').trigger('change');")
        time.sleep(0.3)

        # Bước 2: Điền SHD vào ô Hợp đồng (#txtContract)
        self.log(f"Điền Số Hợp Đồng [{shd}] vào ô Hợp đồng...", "info")
        txt_contract = wait.until(EC.presence_of_element_located((By.ID, "txtContract")))
        txt_contract.click()
        txt_contract.send_keys(Keys.CONTROL + "a")
        txt_contract.send_keys(Keys.BACKSPACE)
        txt_contract.send_keys(shd)
        self.driver.execute_script("$('#txtContract').val(arguments[0]);", shd)
        time.sleep(0.3)

        # Bước 3: Bấm nút Tìm kiếm (#btnSearch)
        self.log("Bấm nút [Tìm kiếm]...", "info")
        btn_search = wait.until(EC.element_to_be_clickable((By.ID, "btnSearch")))
        self.driver.execute_script("arguments[0].click();", btn_search)
        time.sleep(1.5)

        # Xử lý nếu có alert bất ngờ khi tìm kiếm
        try:
            alert = self.driver.switch_to.alert
            alert_txt = alert.text
            alert.accept()
            self.log(f"Cảnh báo từ hệ thống khi tìm kiếm {shd}: {alert_txt}", "warning")
        except Exception:
            pass

        # Bước 4: Kiểm tra bảng kết quả (#kGrid) và bấm vào Số Hợp Đồng (màu đỏ)
        wait.until(EC.presence_of_element_located((By.ID, "kGrid")))
        grid_text = (self.driver.find_element(By.ID, "kGrid").text or "").strip()
        if "Không có dữ liệu tìm kiếm" in grid_text:
            self.log(f"❌ Không tìm thấy hợp đồng [{shd}] trên hệ thống Port!", "error")
            return False, "Không tìm thấy hợp đồng"

        contract_links = self.driver.find_elements(
            By.XPATH,
            "//div[@id='kGrid']//a[@class='link' or contains(@href, '/Contract/Insert/')]"
        )
        if not contract_links:
            self.log(f"❌ Không tìm thấy dòng kết quả hợp đồng [{shd}] trong bảng!", "error")
            return False, "Không tìm thấy hợp đồng"

        target_link = contract_links[0]
        for lnk in contract_links:
            if (lnk.text or "").strip().upper() == shd.upper():
                target_link = lnk
                break

        link_text = (target_link.text or shd).strip()
        self.log(f"Tìm thấy HĐ [{link_text}] trong bảng kết quả -> Bấm vào Số Hợp Đồng (màu đỏ) để chuyển trang...", "info")
        self.driver.execute_script("arguments[0].click();", target_link)
        time.sleep(2.0)

        # Bước 5: Tại trang 'Cấp port Hợp đồng'
        wait.until(EC.presence_of_element_located((By.ID, "txtDescription")))
        wait.until(EC.presence_of_element_located((By.ID, "cbo_statusPort")))
        wait.until(EC.presence_of_element_located((By.ID, "btnUpdate")))

        # 5a. Copy Thông số thi công (màu đỏ - #dvTSTC) dán vào ô Ghi Chú (#txtDescription)
        self.last_tap_diem = ""
        self.last_port = ""
        self.last_tstc = ""

        tstc_text = self.driver.execute_script("return ($('#dvTSTC').text() || '').trim();")
        if not tstc_text:
            # Fallback tìm theo thẻ chứa chữ 'Thông số thi công'
            tstc_els = self.driver.find_elements(By.XPATH, "//*[contains(text(), 'Thông số thi công')]")
            if tstc_els:
                tstc_text = (tstc_els[0].get_attribute("textContent") or "").strip()

        txt_desc = self.driver.find_element(By.ID, "txtDescription")
        existing_desc = (txt_desc.get_attribute("value") or "").strip()

        if tstc_text:
            self.log(f"Copy Thông số thi công (màu đỏ): '{tstc_text}' -> Dán vào ô Ghi chú...", "info")
            txt_desc.click()
            txt_desc.send_keys(Keys.CONTROL + "a")
            txt_desc.send_keys(Keys.BACKSPACE)
            txt_desc.send_keys(tstc_text)
            self.driver.execute_script("$('#txtDescription').val(arguments[0]).trigger('change');", tstc_text)
            source_tstc = tstc_text
        else:
            self.log(f"⚠️ Không thấy dòng Thông số thi công màu đỏ (có thể đã thu hồi trước đó). Giữ nguyên Ghi chú: '{existing_desc}'", "warning")
            source_tstc = existing_desc

        self.last_tstc = source_tstc
        parsed_td, parsed_port = parse_tstc_info(source_tstc)
        self.last_tap_diem = parsed_td
        self.last_port = parsed_port
        if parsed_td or parsed_port:
            self.log(f"📌 Đã tách chuẩn Tập điểm: '{parsed_td}' | Port: '{parsed_port}' (từ '{source_tstc}')", "info")

        time.sleep(0.4)

        # 5b. Thay đổi Tình trạng port (#cbo_statusPort) -> chọn 'Thu hồi port' (value='2')
        self.log("Thay đổi 'Tình trạng port' -> Chọn 'Thu hồi port'...", "info")
        cbo_status_port = self.driver.find_element(By.ID, "cbo_statusPort")
        try:
            Select(cbo_status_port).select_by_value("2")
        except Exception:
            try:
                Select(cbo_status_port).select_by_visible_text("Thu hồi port")
            except Exception:
                pass
        self.driver.execute_script("$('#cbo_statusPort').val('2').trigger('change');")
        time.sleep(0.5)

        # 5c. Hook hàm Message / alert trước khi bấm Cập nhật để bắt thông báo phản hồi
        self.driver.execute_script("""
            window._lastPortUpdateMsg = '';
            if (typeof window.Message === 'function' && !window._portMsgWrapped) {
                window._origPortMsgFn = window.Message;
                window.Message = function(msg, title) {
                    window._lastPortUpdateMsg = Array.isArray(msg) ? msg.join(' | ') : String(msg || '');
                    try { return window._origPortMsgFn.apply(this, arguments); } catch(e) {}
                };
                window._portMsgWrapped = true;
            }
        """)

        # 5d. Bấm nút Cập nhật (#btnUpdate)
        self.log("Bấm nút [Cập nhật]...", "info")
        btn_update = self.driver.find_element(By.ID, "btnUpdate")
        self.driver.execute_script("arguments[0].click();", btn_update)
        time.sleep(1.5)

        # Kiểm tra nếu có native alert xuất hiện
        alert_msg = ""
        try:
            alert = self.driver.switch_to.alert
            alert_msg = alert.text or ""
            alert.accept()
        except Exception:
            pass

        # Đọc thông báo từ window._lastPortUpdateMsg hoặc popup Message trên trang
        sys_msg = ""
        try:
            sys_msg = self.driver.execute_script("return window._lastPortUpdateMsg || '';") or alert_msg
        except Exception:
            sys_msg = alert_msg

        # Đóng popup thông báo (nếu Message tạo popup jQuery UI / Kendo)
        try:
            ok_btns = self.driver.find_elements(
                By.XPATH,
                "//button[normalize-space(.)='OK' or normalize-space(.)='Đóng' or normalize-space(.)='Close'] | //input[@value='OK'] | //span[contains(@class, 'ui-button-text') and (text()='OK' or text()='Đóng')]"
            )
            for b in ok_btns:
                if b.is_displayed():
                    self.driver.execute_script("arguments[0].click();", b)
        except Exception:
            pass

        if sys_msg:
            self.log(f"Phản hồi hệ thống Port cho HĐ [{shd}]: '{sys_msg}'", "success")
        else:
            self.log(f"Đã bấm Cập nhật Thu hồi port thành công cho HĐ [{shd}]!", "success")

        return True, "Đã xử lý"

    def close(self, force=False):
        if self.driver and (force or not self.keep_open):
            try:
                self.driver.quit()
            except Exception:
                pass
            self.driver = None


if __name__ == "__main__":
    data = fetch_sheet_data()
    print("Fetched Port Data:", data.get("count"), "records")

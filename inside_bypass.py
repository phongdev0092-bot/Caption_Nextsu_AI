import os
import sys
import time
import re
import urllib.request
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options

import core_login

DEFAULT_SHEET_ID = "1Sw-qSbLzvVdcW4rj7ywEZBEzKI6w5M82EQeYJUpdx7M"
GID_BYPASS = "0"
GID_PHAN_CONG = "909147347"

# Google Sheet phân quyền Roles (Cột AD = Roles; nếu Roles == Admin thì không bị giới hạn bất kỳ quyền/chức năng nào)
ADMIN_ROLES_SHEET_ID = "17QLc9SlfpPPrR-d1R2BkBxA7DmCI5ZCuhmQffP5F6pY"
ADMIN_ROLES_GID = "32204814"
ADMIN_CACHE_TTL_SEC = 300

import unicodedata
import datetime
import json

BYPASS_VIOLATION_WINDOW_DAYS = 14
BYPASS_VIOLATION_MIN_CONTRACTS = 2

_admin_roles_cache = {
    "last_fetch": 0.0,
    "emails": {"phuongnam.phongnh5@fpt.net", "phuongnam.phongnh5@inside.fpt.net"},
    "accounts": {"pnc01.phongnh5", "phuongnam.phongnh5"},
    "msnvs": {"110827", "00110827"}
}

def _normalize_msnv(val):
    s = str(val or "").strip().lower()
    if not s or s == "nan":
        return ""
    return s.lstrip("0") or s

def load_admin_staff_set(force_refresh=False):
    """
    Tải danh sách nhân sự có Roles = Admin từ Google Sheet 17QLc9SlfpPPrR-d1R2BkBxA7DmCI5ZCuhmQffP5F6pY (GID 32204814, Cột AD).
    Có bộ nhớ đệm TTL 5 phút và giữ danh sách Admin mặc định nếu mất kết nối tạm thời.
    """
    now = time.time()
    if not force_refresh and (now - _admin_roles_cache["last_fetch"] < ADMIN_CACHE_TTL_SEC):
        return _admin_roles_cache

    url = f"https://docs.google.com/spreadsheets/d/{ADMIN_ROLES_SHEET_ID}/gviz/tq?tqx=out:csv&gid={ADMIN_ROLES_GID}&_t={int(now * 1000)}"
    try:
        import io
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        content = urllib.request.urlopen(req, timeout=10).read().decode("utf-8", errors="ignore")
        df = pd.read_csv(io.StringIO(content), dtype=str).fillna("")
        emails = {"phuongnam.phongnh5@fpt.net", "phuongnam.phongnh5@inside.fpt.net"}
        accounts = {"pnc01.phongnh5", "phuongnam.phongnh5"}
        msnvs = {"110827", "00110827"}

        cols = list(df.columns)
        role_col = None
        email_col = None
        acc_col = None
        msnv_col = None

        for c in cols:
            cl = normalize_nfc(c).lower()
            if cl == "roles" or "role" in cl:
                role_col = c
            elif "email" in cl:
                email_col = c
            elif "inside" in cl or "account" in cl:
                acc_col = c
            elif "mã nv" in cl or "ma nv" in cl or "msnv" in cl:
                msnv_col = c

        # Fallback cột AD (index 29) nếu tên cột thay đổi
        if role_col is None and len(cols) >= 30:
            role_col = cols[29]

        if role_col is not None:
            for _, row in df.iterrows():
                role_val = normalize_nfc(row.get(role_col, "")).strip().lower()
                if role_val == "admin" or "admin" in role_val.split(","):
                    if email_col:
                        em = normalize_nfc(row.get(email_col, "")).strip().lower()
                        if em:
                            emails.add(em)
                    if acc_col:
                        ac = normalize_nfc(row.get(acc_col, "")).strip().lower()
                        if ac:
                            accounts.add(ac)
                    if msnv_col:
                        mv = normalize_nfc(row.get(msnv_col, "")).strip().lower()
                        if mv:
                            msnvs.add(mv)
                            msnvs.add(_normalize_msnv(mv))

        _admin_roles_cache["emails"] = emails
        _admin_roles_cache["accounts"] = accounts
        _admin_roles_cache["msnvs"] = msnvs
        _admin_roles_cache["last_fetch"] = now
    except Exception:
        # Giữ nguyên cache hiện tại nếu mạng lỗi tạm thời
        _admin_roles_cache["last_fetch"] = now - (ADMIN_CACHE_TTL_SEC - 30)

    return _admin_roles_cache

def is_admin_staff(record_or_email=None, email="", account_inside="", msnv=""):
    """
    Kiểm tra nhân sự có thuộc nhóm Roles = Admin hay không.
    Rule: Admin không bị giới hạn bất kỳ quyền nào hoặc bị giới hạn chức năng (ví dụ ByPass 14N vi phạm).
    """
    if isinstance(record_or_email, dict):
        email = email or record_or_email.get("Email") or record_or_email.get("NVKT") or ""
        account_inside = (
            account_inside
            or record_or_email.get("Account Inside")
            or record_or_email.get("Inside Account")
            or ""
        )
        msnv = msnv or record_or_email.get("MSNV") or record_or_email.get("Mã NV") or ""
    elif isinstance(record_or_email, str) and not email:
        email = record_or_email

    adm = load_admin_staff_set()
    em_clean = normalize_nfc(email).strip().lower()
    ac_clean = normalize_nfc(account_inside).strip().lower()
    mv_clean = normalize_nfc(msnv).strip().lower()
    mv_norm = _normalize_msnv(mv_clean)

    if em_clean and em_clean in adm["emails"]:
        return True
    if ac_clean and ac_clean in adm["accounts"]:
        return True
    if mv_clean and (mv_clean in adm["msnvs"] or mv_norm in adm["msnvs"]):
        return True
    return False

def normalize_nfc(text):
    if text is None:
        return ""
    return unicodedata.normalize('NFC', str(text)).strip()

def remove_accents(text):
    if text is None:
        return ""
    nfkd = unicodedata.normalize('NFD', str(text))
    no_tone = "".join([c for c in nfkd if unicodedata.category(c) != 'Mn'])
    return no_tone.replace("đ", "d").replace("Đ", "D").lower().strip()

def parse_bypass_date(val):
    """Trích xuất datetime.date từ chuỗi Ngày Cập Nhật trên Google Sheet."""
    if not val:
        return None
    s = str(val).strip()
    if not s or s.lower() in ("nan", "chưa cập nhật", "chưa xử lý"):
        return None
    m1 = re.match(r"^(\d{1,2})[\/\-](\d{1,2})[\/\-](\d{4})", s)
    if m1:
        try:
            return datetime.date(int(m1.group(3)), int(m1.group(2)), int(m1.group(1)))
        except ValueError:
            pass
    m2 = re.match(r"^(\d{4})[\/\-](\d{1,2})[\/\-](\d{1,2})", s)
    if m2:
        try:
            return datetime.date(int(m2.group(1)), int(m2.group(2)), int(m2.group(3)))
        except ValueError:
            pass
    return None

def is_bypass_final_status(status_val):
    """Kiểm tra trạng thái Thao Tác của Bypass đã hoàn tất.
    Chỉ coi là final nếu = 'Đã xử lý'. Vi phạm 14N giờ được lưu vào cột Ghi Chú riêng.
    """
    st = normalize_nfc(status_val).lower()
    if not st or st in ("nan", "chưa xử lý", "chưa cập nhật"):
        return False
    # Giữ tương thích ngược: cache cũ có thể còn chuỗi "vi phạm/từ chối"
    if st == "đã xử lý" or "vi phạm" in st or "từ chối" in st or "suy hao" in st:
        return True
    return False

def check_14d_hau_kiem_violation(
    target_record,
    all_records,
    min_violations=BYPASS_VIOLATION_MIN_CONTRACTS,
    window_days=BYPASS_VIOLATION_WINDOW_DAYS
):
    """
    Kiểm tra nếu Email NVKT trong vòng 14N tính từ Today-1 (khoảng [Today - 14, Today - 1])
    có từ min_violations (2) HĐ trở lên có Hậu Kiểm = Không Đạt
    (Nếu Không Đạt Mất Tín Hiệu tạm bỏ qua không tính vào)
    thì từ chối thực hiện Bypass và trả về thông báo:
    'Trong 14N vi phạm N Hợp đồng ( cụ thể:... ) Nhân sự thực hiện xử lý lại Suy Hao để được mở quyền Bypass'
    """
    if not isinstance(target_record, dict) or not all_records:
        return False, 0, [], ""

    # Rule: Nhân sự có Roles = Admin không bị giới hạn bất kỳ quyền hoặc chức năng nào (bỏ qua 14N vi phạm)
    if is_admin_staff(target_record):
        return False, 0, [], ""

    target_email = normalize_nfc(target_record.get("Email", "")).strip().lower()
    target_acc = normalize_nfc(target_record.get("Account Inside", "")).strip().lower()
    target_id = str(target_record.get("ID", "")).strip()
    if not target_email and not target_acc:
        return False, 0, [], ""

    today = datetime.datetime.now().date()
    end_date = today - datetime.timedelta(days=1)
    start_date = today - datetime.timedelta(days=window_days)

    violating_shds = []
    seen_shds = set()

    for rec in reversed(all_records):
        if not isinstance(rec, dict):
            continue
        rec_id = str(rec.get("ID", "")).strip()
        if target_id and rec_id and rec_id == target_id:
            continue

        rec_email = normalize_nfc(rec.get("Email", "")).strip().lower()
        rec_acc = normalize_nfc(rec.get("Account Inside", "")).strip().lower()
        same_staff = (target_email and rec_email == target_email) or (target_acc and rec_acc == target_acc)
        if not same_staff:
            continue

        raw_date = (
            rec.get("Ngày Cập Nhật")
            or rec.get("Ngày Cập Nhật")
            or rec.get("Ngày cập nhật")
            or rec.get("Thời gian")
            or ""
        )
        rec_date = parse_bypass_date(raw_date)
        if not rec_date or not (start_date <= rec_date <= end_date):
            continue

        hk_raw = normalize_nfc(rec.get("Hậu kiểm") or rec.get("Hậu Kiểm") or "")
        hk_clean = remove_accents(hk_raw)
        if "khong dat" not in hk_clean:
            continue

        suy_hao_raw = normalize_nfc(rec.get("Suy Hao Hậu Kiểm") or rec.get("Suy hao") or "")
        combined_clean = remove_accents(f"{hk_raw} {suy_hao_raw}")
        if "mat tin hieu" in combined_clean:
            continue

        rec_shd = normalize_nfc(rec.get("SHD") or rec.get("Số Hợp Đồng") or "").strip()
        if rec_shd:
            shd_key = rec_shd.upper()
            if shd_key not in seen_shds:
                seen_shds.add(shd_key)
                violating_shds.append(rec_shd)

    v_count = len(violating_shds)
    if v_count >= min_violations:
        shd_list_str = ", ".join(violating_shds)
        msg = (
            f"Không thành công : Trong 14N vi phạm {v_count} Hợp đồng ( cụ thể: {shd_list_str} ) "
            f"Nhân sự thực hiện xử lý lại Suy Hao để được mở quyền Bypass"
        )
        return True, v_count, violating_shds, msg

    return False, v_count, violating_shds, ""

def fetch_sheet_data(sheet_id=DEFAULT_SHEET_ID, gid=GID_BYPASS):
    """
    Đọc dữ liệu bảng tính từ Google Sheet công khai qua định dạng CSV gviz.
    Tự động chuẩn hóa Unicode NFC và ánh xạ tên cột chuẩn.
    """
    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&gid={gid}&_t={int(time.time() * 1000)}"
    try:
        import io
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        content = urllib.request.urlopen(req, timeout=12).read().decode("utf-8", errors="ignore")
        df = pd.read_csv(io.StringIO(content))
        df = df.fillna("")

        # Ánh xạ tên cột sang chuẩn
        standard_records = []
        for raw in df.to_dict(orient="records"):
            rec = {}
            for k, v in raw.items():
                norm_k = normalize_nfc(k)
                norm_v = normalize_nfc(v) if isinstance(v, str) else v
                rec[norm_k] = norm_v

                # Tạo thêm alias chuẩn nếu tên cột có dấu hoặc gõ khác nhau
                k_lower = norm_k.lower()
                if "shd" in k_lower or "hợp đồng" in k_lower:
                    rec["SHD"] = norm_v
                elif "email" in k_lower or "nvkt" in k_lower or "kỹ thuật" in k_lower:
                    rec["Email"] = norm_v
                elif "tác vụ" in k_lower:
                    rec["Tác Vụ"] = norm_v
                elif "nguyên nhân 1" in k_lower or "tình trạng" in k_lower:
                    rec["Nguyên Nhân 1"] = norm_v
                elif "nguyên nhân 2" in k_lower or "lý do" in k_lower:
                    rec["Nguyên Nhân 2"] = norm_v
                elif "ngày" in k_lower:
                    rec["Ngày Cập Nhật"] = norm_v
                elif "thao tác" in k_lower:
                    rec["Thao Tác"] = norm_v
                elif "msnv" in k_lower:
                    rec["MSNV"] = norm_v
                elif "account" in k_lower:
                    rec["Account Inside"] = norm_v
                elif k_lower == "id":
                    rec["ID"] = norm_v
                elif "hậu kiểm" in k_lower and "suy hao" not in k_lower:
                    rec["Hậu kiểm"] = norm_v
                    rec["Hậu Kiểm"] = norm_v
                elif "suy hao" in k_lower:
                    rec["Suy Hao Hậu Kiểm"] = norm_v
                    rec["Suy hao"] = norm_v
                elif "ghi chú" in k_lower or "ghi chu" in k_lower or "note" in k_lower:
                    rec["Ghi Chú"] = norm_v

            standard_records.append(rec)

        # Khắc phục việc Apps Script cũ ghi đè cùng 1 Ngày Cập Nhật / Thao Tác lên các dòng cũ trùng SHD:
        # Chỉ giữ Ngày Cập Nhật & Thao Tác mới nhất ở dòng có ID lớn nhất (dòng cuối cùng),
        # các dòng lịch sử cũ trước đó được khôi phục Ngày Cập Nhật theo dòng liền kề trên Sheet.
        shd_ts_groups = {}
        for idx, rec in enumerate(standard_records):
            shd_u = str(rec.get("SHD", "")).strip().upper()
            ngay_s = str(rec.get("Ngày Cập Nhật", "")).strip()
            if shd_u and ngay_s and ngay_s.lower() not in ("nan", "chưa cập nhật", "chưa xử lý"):
                shd_ts_groups.setdefault((shd_u, ngay_s), []).append(idx)

        overwritten_old_indices = set()
        for (_, _), idxs in shd_ts_groups.items():
            if len(idxs) > 1:
                for old_i in idxs[:-1]:
                    overwritten_old_indices.add(old_i)

        if overwritten_old_indices:
            for old_i in sorted(overwritten_old_indices):
                # Chỉ nội suy Ngày Cập Nhật từ dòng lân cận nếu dòng này ĐÃ có trạng thái hoàn tất;
                # tuyệt đối không gán ngày cũ lên dòng đang chờ xử lý.
                if not is_bypass_final_status(standard_records[old_i].get("Thao Tác", "")):
                    continue
                restored_date = ""
                for step in range(1, len(standard_records)):
                    for cand in (old_i - step, old_i + step):
                        if 0 <= cand < len(standard_records) and cand not in overwritten_old_indices:
                            cand_d = str(standard_records[cand].get("Ngày Cập Nhật", "")).strip()
                            if cand_d and cand_d.lower() not in ("nan", "chưa cập nhật", "chưa xử lý"):
                                restored_date = cand_d
                                break
                    if restored_date:
                        break
                if restored_date:
                    standard_records[old_i]["Ngày Cập Nhật"] = restored_date
                    standard_records[old_i]["Ngày Cập Nhật"] = restored_date

        cols = [normalize_nfc(c) for c in df.columns]
        return {
            "status": "ok",
            "count": len(standard_records),
            "columns": cols,
            "records": standard_records
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Không thể đọc Google Sheet: {e}",
            "records": []
        }

class InsideBypassAutomation:
    def __init__(self, headless=False, log_cb=None):
        self.headless = headless
        self.log_cb = log_cb or self._default_log
        self.driver = None

    def _default_log(self, msg, level="info"):
        print(f"[{level.upper()}] {msg}")

    def log(self, msg, level="info"):
        try:
            self.log_cb(msg, level)
        except Exception:
            pass

    def init_driver(self):
        self.log("Khởi tạo trình duyệt Chrome với profile phiên Inside FPT...", "info")
        self.driver = core_login.create_driver_with_retry(
            headless=self.headless,
            keep_open=False,
            max_retries=2,
            log_cb=self.log_cb
        )
        return self.driver

    def check_and_ensure_login(self):
        """Luôn luôn tiến hành đăng nhập sạch 100% từ đầu qua SSO login.fpt.net."""
        self.log("Bắt đầu đăng nhập mới từ đầu vào Inside FPT...", "info")
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
        """Khi hoàn tất 1 tác vụ: Đóng trình duyệt và xóa sạch toàn bộ session cũ."""
        if self.driver:
            self.log("Hoàn tất tác vụ: Đang đóng trình duyệt và xóa sạch toàn bộ session cũ...", "info")
            core_login.close_driver_and_clear_session(self.driver, log_cb=self.log_cb)
            self.driver = None

    def navigate_to_bypass_page(self):
        """
        Thao tác trên Inside FPT:
        Vào default.asp -> Frame menu trái (0) -> Hỗ trợ kỹ thuật -> Quản Lý Chất Lượng DVKH -> Quản Lý ByPass
        """
        self.log("Đang điều hướng menu: Hỗ trợ kỹ thuật >> Quản Lý Chất Lượng DVKH >> Quản Lý ByPass...", "info")
        self.check_and_ensure_login()

        self.driver.switch_to.default_content()
        wait = WebDriverWait(self.driver, 20)

        # Chuyển vào Frame menu bên trái (Frame 0)
        try:
            wait.until(EC.frame_to_be_available_and_switch_to_it(0))
        except Exception:
            self.log("Không thể chuyển vào Frame menu, tải lại trang default.asp...", "warning")
            self.driver.get("http://inside.fpt.net/default.asp")
            time.sleep(3)
            self.driver.switch_to.default_content()
            wait.until(EC.frame_to_be_available_and_switch_to_it(0))

        time.sleep(1)

        # 1. Mở menu 'Hỗ trợ kỹ thuật'
        try:
            ho_tro_nodes = self.driver.find_elements(By.XPATH, "//a[contains(text(), 'Hỗ trợ kỹ thuật') or contains(text(), 'Hỗ trợ Kỹ thuật')]")
            if ho_tro_nodes:
                self.log("Nhấp mở menu 'Hỗ trợ kỹ thuật'...", "info")
                self.driver.execute_script("arguments[0].scrollIntoView(true);", ho_tro_nodes[0])
                self.driver.execute_script("arguments[0].click();", ho_tro_nodes[0])
                time.sleep(1)
        except Exception as e:
            self.log(f"Lưu ý khi mở Hỗ trợ kỹ thuật: {e}", "warning")

        # 2. Mở menu con 'Quản Lý Chất Lượng DVKH'
        try:
            cl_nodes = self.driver.find_elements(By.XPATH, "//a[contains(text(), 'Quản Lý Chất Lượng DVKH') or contains(text(), 'Chất Lượng DVKH')]")
            if cl_nodes:
                self.log("Nhấp mở 'Quản Lý Chất Lượng DVKH'...", "info")
                self.driver.execute_script("arguments[0].scrollIntoView(true);", cl_nodes[0])
                self.driver.execute_script("arguments[0].click();", cl_nodes[0])
                time.sleep(1)
        except Exception as e:
            self.log(f"Lưu ý khi mở Quản Lý Chất Lượng DVKH: {e}", "warning")

        # 3. Nhấp chọn 'Quản Lý ByPass'
        bypass_nodes = wait.until(EC.presence_of_all_elements_located((
            By.XPATH, "//a[contains(text(), 'Quản Lý ByPass') or contains(text(), 'ByPass') or contains(text(), 'Bypass')]"
        )))
        if not bypass_nodes:
            raise RuntimeError("Không tìm thấy mục 'Quản Lý ByPass' trên menu cây Inside!")

        self.log("Đã tìm thấy 'Quản Lý ByPass'! Tiến hành mở trang...", "info")
        self.driver.execute_script("arguments[0].scrollIntoView(true);", bypass_nodes[0])
        self.driver.execute_script("arguments[0].click();", bypass_nodes[0])
        time.sleep(3)

        # 4. Chuyển sang Frame Content (Frame 1)
        self.driver.switch_to.default_content()
        try:
            wait.until(EC.frame_to_be_available_and_switch_to_it(1))
            self.log("Đã chuyển vào Content Frame của trang Quản Lý ByPass.", "info")
        except Exception:
            # Thử tìm iframe khác nếu có
            iframes = self.driver.find_elements(By.TAG_NAME, "iframe") + self.driver.find_elements(By.TAG_NAME, "frame")
            if len(iframes) > 1:
                self.driver.switch_to.frame(iframes[1])

        time.sleep(1.5)

    def open_import_tab_and_dismiss_help(self):
        """
        Tại trang Quản Lý ByPass:
        - Bấm tab Import
        - Chờ popup Trợ giúp tự động xuất hiện
        - Bấm dấu X để đóng popup
        """
        self.log("Đang chuyển sang tab 'Import'...", "info")
        wait = WebDriverWait(self.driver, 15)

        # Tìm tab Import (xem ảnh 2: nằm cạnh Thống kê, Export, Báo Cáo)
        import_tab = wait.until(EC.element_to_be_clickable((
            By.XPATH, "//a[normalize-space(text())='Import' or contains(text(), 'Import')] | //button[contains(text(), 'Import')] | //li[contains(text(), 'Import')] | //*[contains(@class, 'tab') and contains(text(), 'Import')]"
        )))
        try:
            import_tab.click()
        except Exception:
            self.driver.execute_script("arguments[0].click();", import_tab)
        time.sleep(1.5)

        # Xử lý Popup Trợ Giúp (xem ảnh 2: Popup có nút X ở góc trên bên phải)
        self.log("Chờ popup 'Trợ giúp' xuất hiện để đóng...", "info")
        try:
            # Thử tìm nút đóng X của popup dialog
            close_btn = None
            selectors = [
                "//div[contains(@class, 'ui-dialog') and .//*[contains(text(), 'Trợ giúp')]]//a[contains(@class, 'ui-dialog-titlebar-close')]",
                "//div[contains(@class, 'ui-dialog') and .//*[contains(text(), 'Trợ giúp')]]//button[contains(@class, 'close') or contains(text(), '×')]",
                "//span[contains(text(), 'Trợ giúp')]/following::a[contains(@class, 'close') or contains(@class, 'titlebar-close')][1]",
                "//a[contains(@class, 'ui-dialog-titlebar-close')]",
                "//button[contains(@class, 'close') and @data-dismiss='modal']",
                "//div[contains(@class, 'ui-dialog-titlebar')]//span[contains(@class, 'ui-icon-closethick')]/..",
            ]
            for sel in selectors:
                elements = self.driver.find_elements(By.XPATH, sel)
                if elements and elements[0].is_displayed():
                    close_btn = elements[0]
                    break

            if close_btn:
                try:
                    close_btn.click()
                except Exception:
                    self.driver.execute_script("arguments[0].click();", close_btn)
                self.log("Đã đóng popup 'Trợ giúp' thành công bằng nút [X]!", "success")
                time.sleep(1)
            else:
                # Dùng phím Escape hoặc javascript ẩn dialog nếu nút không click được
                self.driver.execute_script("""
                    var d = document.querySelectorAll('.ui-dialog');
                    d.forEach(function(el){
                        if(el.innerText.indexOf('Trợ giúp') !== -1 || el.innerText.indexOf('Nhân Viên Kỹ Thuật') !== -1){
                            var close = el.querySelector('.ui-dialog-titlebar-close');
                            if(close) close.click();
                            else el.style.display = 'none';
                        }
                    });
                """)
                self.log("Đã xử lý đóng popup Trợ giúp bằng script.", "info")
        except Exception as e:
            self.log(f"Lưu ý khi đóng popup Trợ giúp: {e}", "warning")

    def select_dropdown_cell(self, cell_el, target_keywords, cell_name="Dropdown", type_text=None, exact_only=False):
        """
        Bấm vào TRUNG TÂM của ô (như Chọn Loại), chờ menu xổ xuống và chọn mục theo target_keywords.
        target_keywords: danh sách từ khóa không dấu / chữ thường, ví dụ ['bo gong'] hoặc ['kh di day am tuong']
        type_text: text đầy đủ để gõ vào ô nếu là combobox filter (vd: 'Bo Gong')
        exact_only: chỉ chấp nhận khớp chính xác 100%, bỏ qua các chuỗi dài hơn như 'Bo Gong Tam va Phai Xu Ly Gong Lai'
        """
        self.log(f"Thao tác trên [{cell_name}]: Bấm vào trung tâm ô để mở danh sách...", "info")
        
        # 1. Cuộn vào trọng tâm màn hình
        self.driver.execute_script("arguments[0].scrollIntoView({block: 'center', inline: 'center'});", cell_el)
        time.sleep(0.3)

        # 2. Bấm vào TRUNG TÂM của ô bằng ActionChains và Dispatch MouseEvent tại tọa độ trọng tâm (cx, cy)
        try:
            ActionChains(self.driver).move_to_element(cell_el).click().perform()
        except Exception:
            pass

        self.driver.execute_script("""
            var el = arguments[0];
            var rect = el.getBoundingClientRect();
            var cx = rect.left + (rect.width / 2);
            var cy = rect.top + (rect.height / 2);
            var opts = { bubbles: true, cancelable: true, view: window, clientX: cx, clientY: cy };
            el.dispatchEvent(new MouseEvent('mousedown', opts));
            el.dispatchEvent(new MouseEvent('mouseup', opts));
            el.dispatchEvent(new MouseEvent('click', opts));
        """, cell_el)

        time.sleep(0.5)

        # 3. Quét tìm và click vào mục tương ứng trong danh sách xổ xuống (Polling trong 2.5s)
        selected = False

        # JS Universal DOM Matcher
        js_find_and_click = """
            var targets = arguments[0];
            var exactOnly = arguments[1] || false;

            function norm(t) {
                if (!t) return '';
                return t.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase().trim();
            }

            var all = Array.from(document.querySelectorAll('*'));
            var candidates = [];
            for (var i = 0; i < all.length; i++) {
                var el = all[i];
                var tag = el.tagName.toUpperCase();
                // Bỏ qua các thẻ container lớn, bảng và ĐẶC BIỆT LÀ THANH TAB ĐẦU TRANG
                if (tag === 'HTML' || tag === 'BODY' || tag === 'TABLE' || tag === 'TR' || tag === 'THEAD' || tag === 'TBODY') continue;
                if (el.closest('.nav-tabs, .tabs, nav, header, ul.nav') || el.classList.contains('nav-link')) continue;

                var rect = el.getBoundingClientRect();
                if (rect.width <= 0 || rect.height <= 0) continue;
                var style = window.getComputedStyle(el);
                if (style.display === 'none' || style.visibility === 'hidden' || style.opacity === '0') continue;

                var txt = norm(el.innerText || el.textContent);
                for (var k = 0; k < targets.length; k++) {
                    var kw = targets[k];
                    // Khớp chính xác tuyệt đối (loại bỏ chuỗi dài như 'Bo Gong Tam va Phai Xu Ly Gong Lai')
                    if (txt === kw || txt === ('1. ' + kw) || txt === ('2. ' + kw) || txt === ('3. ' + kw)) {
                        candidates.push({ el: el, len: txt.length, exact: true });
                        break;
                    }
                    if (!exactOnly && (txt.startsWith(kw) && txt.length <= kw.length + 3)) {
                        candidates.push({ el: el, len: txt.length, exact: false });
                        break;
                    }
                }
            }

            if (candidates.length > 0) {
                // Ưu tiên khớp chính xác và text ngắn nhất sát với kw
                candidates.sort(function(a, b) {
                    if (a.exact !== b.exact) return a.exact ? -1 : 1;
                    return a.len - b.len;
                });
                var target = candidates[0].el;
                var r = target.getBoundingClientRect();
                var cx = r.left + r.width / 2;
                var cy = r.top + r.height / 2;
                var opts = { bubbles: true, cancelable: true, view: window, clientX: cx, clientY: cy };
                target.dispatchEvent(new MouseEvent('mouseover', opts));
                target.dispatchEvent(new MouseEvent('mousedown', opts));
                target.dispatchEvent(new MouseEvent('mouseup', opts));
                target.dispatchEvent(new MouseEvent('click', opts));
                if (typeof target.click === 'function') target.click();
                return target;
            }
            return null;
        """

        # Lặp lại tìm kiếm qua JS trong 6 lần (mỗi lần 0.3s)
        for _ in range(6):
            try:
                matched_el = self.driver.execute_script(js_find_and_click, target_keywords, exact_only)
                if matched_el:
                    try:
                        ActionChains(self.driver).move_to_element(matched_el).click().perform()
                    except Exception:
                        pass
                    selected = True
                    self.log(f"Đã chọn [{cell_name}] = '{target_keywords[0]}' thành công qua DOM.", "info")
                    break
            except Exception as e_js:
                pass
            time.sleep(0.3)

        # Fallback XPath nếu chưa click được (loại trừ các tab header)
        if not selected:
            for kw in target_keywords:
                xpath_selectors = [
                    f"//li[not(contains(@class, 'tab'))][translate(normalize-space(.), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz')='{kw}']",
                    f"//*[contains(@class, 'item') or contains(@class, 'option')][translate(normalize-space(.), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz')='{kw}']",
                    f"//div[contains(@class, 'drop') or contains(@class, 'list')]//*[translate(normalize-space(.), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz')='{kw}']",
                    f"//span[translate(normalize-space(.), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz')='{kw}']",
                    f"//a[not(contains(@class, 'tab')) and not(contains(@href, '#'))][translate(normalize-space(.), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz')='{kw}']"
                ]
                for xp in xpath_selectors:
                    try:
                        elements = self.driver.find_elements(By.XPATH, xp)
                        for el in elements:
                            if el.is_displayed():
                                el_txt = el.text.strip().lower()
                                if exact_only and el_txt != kw and el_txt != "bó gồng":
                                    continue
                                try:
                                    ActionChains(self.driver).move_to_element(el).click().perform()
                                except Exception:
                                    self.driver.execute_script("arguments[0].click();", el)
                                selected = True
                                self.log(f"Đã chọn [{cell_name}] qua XPath: '{kw}'.", "info")
                                break
                        if selected:
                            break
                    except Exception:
                        pass
                if selected:
                    break

        # Fallback top document nếu popup render ở ngoài iframe
        if not selected:
            try:
                self.driver.switch_to.default_content()
                top_matched = self.driver.execute_script(js_find_and_click, target_keywords, exact_only)
                if top_matched:
                    try:
                        ActionChains(self.driver).move_to_element(top_matched).click().perform()
                    except Exception:
                        pass
                    selected = True
                    self.log(f"Đã chọn [{cell_name}] ở top document.", "info")
            except Exception:
                pass
            finally:
                try:
                    self.driver.switch_to.frame(1)
                except Exception:
                    pass

        # Fallback nhập trực tiếp bằng phím nếu có type_text và chưa chọn được
        if not selected and type_text:
            try:
                inps = cell_el.find_elements(By.TAG_NAME, "input")
                if inps and inps[0].is_displayed():
                    inps[0].clear()
                    inps[0].send_keys(type_text)
                    time.sleep(0.3)
                    inps[0].send_keys(Keys.ENTER)
                    selected = True
                    self.log(f"Đã gõ trực tiếp [{cell_name}] = '{type_text}' vào input.", "info")
                else:
                    ActionChains(self.driver).send_keys(type_text).pause(0.3).send_keys(Keys.ENTER).perform()
                    selected = True
                    self.log(f"Đã gửi phím gõ [{cell_name}] = '{type_text}'.", "info")
            except Exception:
                pass

        # Fallback Select tag nếu có
        try:
            select_elems = cell_el.find_elements(By.TAG_NAME, "select")
            if select_elems:
                s = Select(select_elems[0])
                for o in s.options:
                    t = o.text.lower()
                    if any(kw in t for kw in target_keywords):
                        o.click()
                        selected = True
                        break
                self.driver.execute_script("""
                    var el = arguments[0];
                    var e = document.createEvent('HTMLEvents');
                    e.initEvent('change', true, true);
                    el.dispatchEvent(e);
                    if (window.jQuery) { $(el).trigger('change'); }
                """, select_elems[0])
        except Exception:
            pass

        # Kiểm tra sau khi chọn: nếu ô bị dính 'Bo Gong Tam' hoặc 'Gong', tự động chọn lại đúng mục thứ 3 'Bo Gong'
        time.sleep(0.4)
        try:
            current_txt = cell_el.text.strip().lower()
            if type_text and "bo gong" in type_text.lower() and ("tam" in current_txt or current_txt == "gong" or "xu ly" in current_txt):
                self.log(f"Phát hiện ô đang mang giá trị '{cell_el.text}'. Đang chọn lại mục thứ 3 [Bo Gong]...", "warning")
                ActionChains(self.driver).move_to_element(cell_el).click().perform()
                time.sleep(0.4)
                self.driver.execute_script(js_find_and_click, target_keywords, 3, True)
                time.sleep(0.3)
        except Exception:
            pass

        time.sleep(0.5)
        return selected

    def get_active_cells(self):
        """Lấy danh sách các ô td của dòng đang nhập hiện tại, đảm bảo luôn tươi mới và không bị stale."""
        try:
            if not self.driver.find_elements(By.XPATH, "//button[contains(., 'Add row')] | //button[contains(., 'Save')] | //*[contains(text(), 'Add row')]"):
                self.driver.switch_to.default_content()
                self.driver.switch_to.frame(1)
        except Exception:
            pass

        rows = self.driver.find_elements(By.XPATH, """
            //tr[.//td[contains(., 'Hợp') or contains(., 'Chọn loại') or contains(., '-- Chọn')]]
            | //tbody//tr[count(td) >= 3]
        """)
        for r in rows:
            if r.is_displayed():
                tds = r.find_elements(By.TAG_NAME, "td")
                if len(tds) >= 3:
                    return tds
        all_tds = self.driver.find_elements(By.XPATH, "//tbody//tr[1]//td")
        return all_tds

    def input_bypass_row(self, record):
        """
        Điền thông tin hợp đồng vào lưới ByPass:
        1. Bấm '+ Add row' nếu chưa có dòng nhập.
        2. Click TRỌNG TÂM Ô 'Chọn loại' để mở dropdown và chọn 'Hợp đồng'.
        3. Điền Số hợp đồng/Tập điểm = SHD.
        4. Điền Nhân viên kỹ thuật = Email.
        5. Click TRỌNG TÂM Ô 'Tình trạng ByPass' -> chọn 'Bo Gong'.
        6. Click TRỌNG TÂM Ô 'Lý do ByPass' -> chọn 'KH di day am tuong'.
        7. Kiểm tra dữ liệu đã vào hàng trước khi bấm Save.
        8. Bấm nút Save và xác nhận lưu thành công.
        """
        shd = str(record.get("SHD", "")).strip()
        email = str(record.get("Email", "")).strip()

        self.log(f"Nhập liệu ByPass cho HĐ [{shd}]: NVKT={email}, Tình trạng=[Bo Gong], Lý do=[KH di day am tuong]...", "info")

        # 0. Luôn đảm bảo đang ở trong Content Frame (Frame 1)
        try:
            if not self.driver.find_elements(By.XPATH, "//button[contains(., 'Add row')] | //button[contains(., 'Save')] | //*[contains(text(), 'Add row')]"):
                self.driver.switch_to.default_content()
                self.driver.switch_to.frame(1)
        except Exception:
            pass

        # 1. Kiểm tra xem ô '-- Chọn loại --' hoặc ô dữ liệu đã xuất hiện chưa
        cells = self.get_active_cells()
        if not cells:
            self.log("Chưa thấy dòng nhập trên bảng, bấm nút '+ Add row'...", "info")
            add_btns = self.driver.find_elements(By.XPATH, "//button[contains(., 'Add row')] | //a[contains(., 'Add row')] | //*[contains(text(), 'Add row')]")
            for b in add_btns:
                if b.is_displayed():
                    try:
                        ActionChains(self.driver).move_to_element(b).click().perform()
                    except Exception:
                        self.driver.execute_script("arguments[0].click();", b)
                    time.sleep(1.5)
                    break
            cells = self.get_active_cells()

        if not cells:
            raise RuntimeError("Không tìm thấy dòng nhập liệu sau khi bấm Add row!")

        # 2 & 3. CHỌN MỤC [Hợp đồng] TẠI Ô LOẠI (CỘT 1)
        target_loai = cells[0]
        self.select_dropdown_cell(target_loai, ["hop dong", "hợp đồng"], "Loại (Hợp đồng)")
        time.sleep(0.5)

        # 4. ĐIỀN CỘT 2: Số hợp đồng/Tập điểm (SHD)
        self.log(f"BƯỚC 2: Điền Số hợp đồng/Tập điểm = [{shd}]...", "info")
        shd_filled = False
        try:
            cells = self.get_active_cells()
            cell_2 = cells[1] if len(cells) >= 2 else None
            if cell_2:
                try:
                    ActionChains(self.driver).move_to_element(cell_2).click().perform()
                except Exception:
                    pass
                time.sleep(0.3)
                inps_2 = cell_2.find_elements(By.TAG_NAME, "input")
                target_inp = inps_2[0] if inps_2 else None
            else:
                inps = self.driver.find_elements(By.XPATH, "//input[contains(@name, 'SHD') or contains(@id, 'SHD') or contains(@name, 'contract')]")
                target_inp = inps[0] if inps else None

            if target_inp:
                target_inp.clear()
                target_inp.send_keys(shd)
                target_inp.send_keys(Keys.TAB)
                shd_filled = True
            else:
                ActionChains(self.driver).send_keys(shd).send_keys(Keys.TAB).perform()
                shd_filled = True
            time.sleep(0.3)
        except Exception as e_shd:
            self.log(f"Lỗi nhập SHD: {e_shd}", "warning")

        # 5. ĐIỀN CỘT 3: Nhân viên kỹ thuật (Email)
        self.log(f"BƯỚC 3: Điền Nhân viên kỹ thuật = [{email}]...", "info")
        try:
            cells = self.get_active_cells()
            cell_3 = cells[2] if len(cells) >= 3 else None
            if cell_3:
                try:
                    ActionChains(self.driver).move_to_element(cell_3).click().perform()
                except Exception:
                    pass
                time.sleep(0.3)
                inps_3 = cell_3.find_elements(By.TAG_NAME, "input")
                target_inp3 = inps_3[0] if inps_3 else None
            else:
                inps = self.driver.find_elements(By.XPATH, "//input[contains(@name, 'Email') or contains(@id, 'Email') or contains(@name, 'NVKT')]")
                target_inp3 = inps[0] if inps else None

            if target_inp3:
                target_inp3.clear()
                target_inp3.send_keys(email)
                target_inp3.send_keys(Keys.TAB)
            else:
                ActionChains(self.driver).send_keys(email).send_keys(Keys.TAB).perform()
            time.sleep(0.3)
        except Exception as e_email:
            self.log(f"Lỗi nhập Email: {e_email}", "warning")

        # 6. CHỌN CỘT 4: Tình trạng ByPass -> Bấm vào trung tâm ô, chọn đúng 'Bo Gong'
        cells = self.get_active_cells()
        cell_4 = cells[3] if len(cells) >= 4 else None
        if cell_4:
            self.select_dropdown_cell(cell_4, ["bo gong", "bó gồng"], "Tình trạng ByPass (Bo Gong)", type_text="Bo Gong", exact_only=True)
        else:
            self.log("Không tìm thấy ô Tình trạng ByPass (cột 4)!", "warning")
        time.sleep(0.5)

        # 7. CHỌN CỘT 5: Lý do ByPass -> Bấm vào trung tâm ô, chọn 'KH di day am tuong'
        cells = self.get_active_cells()
        cell_5 = cells[4] if len(cells) >= 5 else None
        if cell_5:
            self.select_dropdown_cell(cell_5, ["kh di day am tuong", "kh đi dây âm tường", "di day am tuong", "dây âm tường"], "Lý do ByPass (KH di day am tuong)", type_text="KH di day am tuong", exact_only=True)
        else:
            self.log("Không tìm thấy ô Lý do ByPass (cột 5)!", "warning")
        time.sleep(0.5)

        # 8. KIỂM TRA DÒNG TRƯỚC KHI BẤM SAVE
        cells = self.get_active_cells()
        row_content = " ".join([c.text for c in cells]) if cells else ""
        self.log(f"Kiểm tra dòng trước khi Save: [{row_content}]", "info")
        has_shd = (shd.lower() in row_content.lower())
        if not has_shd and not shd_filled:
            raise RuntimeError(f"Chưa điền được hợp đồng [{shd}] vào lưới. Dừng lại để tránh lỗi 'Không có thông tin để lưu'.")



        # 9. BẤM NÚT SAVE (nút màu xanh dương đậm ở góc trên bên phải)
        self.log(f"BƯỚC 6: Bấm nút 'Save' để lưu ByPass HĐ [{shd}]...", "info")
        save_btn = None
        selectors = [
            "//button[contains(., 'Save') or contains(text(), 'Save')]",
            "//a[contains(., 'Save') or contains(text(), 'Save')]",
            "//input[@value='Save' or @id='btnSave']",
            "//*[contains(@class, 'btn') and contains(., 'Save')]"
        ]
        for sel in selectors:
            elements = self.driver.find_elements(By.XPATH, sel)
            if elements and elements[0].is_displayed():
                save_btn = elements[0]
                break

        if not save_btn:
            raise RuntimeError("Không tìm thấy nút 'Save' trên trang ByPass!")

        try:
            ActionChains(self.driver).move_to_element(save_btn).click().perform()
        except Exception:
            self.driver.execute_script("arguments[0].click();", save_btn)

        time.sleep(2)

        # 10. KIỂM TRA THÔNG BÁO THÀNH CÔNG HOẶC CẢNH BÁO TỪ HỆ THỐNG
        self.log("BƯỚC 7: Đang chờ phản hồi xác nhận lưu từ hệ thống...", "info")
        success = False
        msg_text = ""
        for _ in range(8):
            alerts = self.driver.find_elements(By.XPATH, "//*[contains(text(), 'Lưu thành công') or contains(text(), 'thành công') or contains(@class, 'success')]")
            for a in alerts:
                if a.is_displayed():
                    msg_text = a.text.strip()
                    if "lưu thành công" in msg_text.lower() or "thành công" in msg_text.lower():
                        success = True
                        break
            if success:
                break

            # Kiểm tra nếu xuất hiện popup lỗi màu đỏ (như 'Không có thông tin để lưu')
            err_alerts = self.driver.find_elements(By.XPATH, "//*[contains(text(), 'Không có thông tin') or contains(@class, 'error') or contains(@class, 'danger')]")
            for ea in err_alerts:
                if ea.is_displayed():
                    err_txt = ea.text.strip()
                    if "không có thông tin" in err_txt.lower():
                        raise RuntimeError(f"Hệ thống báo: {err_txt}")

            time.sleep(1)

        if success or msg_text:
            self.log(f"✅ THÀNH CÔNG: {msg_text or 'Đã lưu thành công ByPass cho HĐ ' + shd}!", "success")
            return True, msg_text
        else:
            self.log(f"⚠️ Đã bấm Save HĐ [{shd}], kiểm tra không thấy lỗi phát sinh.", "info")
            return True, "Đã gửi lưu thành công"

    def process_bypass_queue(self, records, update_sheet_cb=None, all_sheet_records=None):
        """
        Xử lý toàn bộ danh sách bản ghi ByPass từ Google Sheet.
        """
        results = []
        ref_records = all_sheet_records if all_sheet_records is not None else records
        driver_ready = False
        try:
            for idx, r in enumerate(records):
                shd = str(r.get("SHD", "")).strip()
                current_status = str(r.get("Thao Tác", "")).strip()

                if is_bypass_final_status(current_status):
                    self.log(f"⏩ Bỏ qua HĐ [{shd}] vì đã có trạng thái '{current_status}'.", "info")
                    results.append({"shd": shd, "status": current_status, "message": "Đã hoàn tất trước đó"})
                    continue

                is_violated, v_count, v_shds, reject_msg = check_14d_hau_kiem_violation(r, ref_records)
                if is_violated:
                    self.log(f"⛔ Từ chối ByPass HĐ [{shd}] ({r.get('Email', '')}): {reject_msg}", "warning")
                    r["Thao Tác"] = reject_msg
                    results.append({"shd": shd, "status": reject_msg, "message": reject_msg})
                    if update_sheet_cb:
                        try:
                            update_sheet_cb(r, reject_msg)
                        except TypeError:
                            update_sheet_cb(r)
                        except Exception as ex_cb:
                            self.log(f"Lỗi callback cập nhật sheet: {ex_cb}", "warning")
                    continue

                if not driver_ready:
                    self.init_driver()
                    self.navigate_to_bypass_page()
                    self.open_import_tab_and_dismiss_help()
                    driver_ready = True

                self.log(f"▶ Bắt đầu xử lý {idx + 1}/{len(records)}: HĐ [{shd}]...", "info")
                try:
                    ok, msg = self.input_bypass_row(r)
                    if ok:
                        r["Thao Tác"] = "Đã xử lý"
                        results.append({"shd": shd, "status": "Đã xử lý", "message": msg})
                        if update_sheet_cb:
                            try:
                                update_sheet_cb(r)
                            except Exception as ex_cb:
                                self.log(f"Lỗi callback cập nhật sheet: {ex_cb}", "warning")
                    else:
                        r["Thao Tác"] = "Lỗi"
                        results.append({"shd": shd, "status": "Lỗi", "message": msg})
                except Exception as ex_row:
                    self.log(f"❌ Lỗi xử lý HĐ [{shd}]: {ex_row}", "error")
                    r["Thao Tác"] = f"Lỗi: {str(ex_row)[:50]}"
                    results.append({"shd": shd, "status": "Lỗi", "message": str(ex_row)})

                time.sleep(1.5)

            self.log(f"🎉 Hoàn tất tiến trình Auto ByPass ({len(results)} bản ghi)!", "success")
            return results

        except Exception as e:
            self.log(f"❌ Tiến trình Auto ByPass bị dừng do lỗi: {e}", "error")
            raise e
        finally:
            if self.driver:
                try:
                    self.driver.quit()
                except Exception:
                    pass
                self.driver = None

if __name__ == "__main__":
    data = fetch_sheet_data()
    print("Fetched sheet data:", data["count"], "records")

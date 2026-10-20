import os
import sys
import time
import json
import urllib.request
import unicodedata
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

import core_login

DEFAULT_SHEET_ID = "1dXsWnon9myjDlcWM6BRLqDt_pxWBmTYFgb17k7R24vc"
GID_CLEAR_SIGNAL = "0"
GID_RESET_SIGNAL = "1100152201"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CLEAR_SIGNAL_CACHE_FILE = os.path.join(BASE_DIR, "clear_signal_status_cache.json")
RESET_SIGNAL_CACHE_FILE = os.path.join(BASE_DIR, "reset_signal_status_cache.json")

def normalize_nfc(text):
    if text is None:
        return ""
    return unicodedata.normalize('NFC', str(text)).strip()

def load_cache(cache_file):
    if os.path.exists(cache_file):
        try:
            with open(cache_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_cache(cache_file, data):
    try:
        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[CACHE ERROR] {e}")

def fetch_sheet_data(sheet_id=DEFAULT_SHEET_ID, gid=GID_CLEAR_SIGNAL, signal_type="clear"):
    """
    Đọc dữ liệu từ Google Sheet qua gviz/tq CSV.
    signal_type: 'clear' hoặc 'reset'
    """
    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&gid={gid}&_t={int(time.time() * 1000)}"
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        content = urllib.request.urlopen(req, timeout=12).read().decode('utf-8', errors='ignore')
        import io
        df = pd.read_csv(io.StringIO(content))
        df = df.fillna("")

        cache_file = CLEAR_SIGNAL_CACHE_FILE if signal_type == "clear" else RESET_SIGNAL_CACHE_FILE
        cache = load_cache(cache_file)

        records = []
        for raw in df.to_dict(orient="records"):
            rec = {}
            for k, v in raw.items():
                norm_k = normalize_nfc(k)
                norm_v = normalize_nfc(v) if isinstance(v, str) else v
                k_lower = norm_k.lower()

                if k_lower == "id":
                    rec["ID"] = norm_v
                elif "ho" in k_lower and "ten" in k_lower:
                    rec["Họ và Tên"] = norm_v
                elif "mail" in k_lower or "email" in k_lower:
                    rec["Email"] = norm_v
                elif "shd" in k_lower or "hợp đồng" in k_lower:
                    rec["SHD"] = norm_v
                elif "mac" in k_lower:
                    rec["MAC"] = norm_v
                elif "ket qua" in k_lower or "kết quả" in k_lower:
                    rec["Kết Quả"] = norm_v
                elif "ngay" in k_lower:
                    rec["Ngày Cập Nhật"] = norm_v
                else:
                    rec[norm_k] = norm_v

            # Merge with local cache if sheet has no status yet
            shd = str(rec.get("SHD", "")).strip()
            if shd and shd in cache:
                c_item = cache[shd]
                c_st = c_item.get("status", "") if isinstance(c_item, dict) else str(c_item)
                c_time = c_item.get("time", "") if isinstance(c_item, dict) else ""
                raw_kq = str(rec.get("Kết Quả", "")).strip().lower()
                if not rec.get("Kết Quả") or raw_kq in ["nan", "chưa xử lý", ""]:
                    rec["Kết Quả"] = c_st
                if c_time and (not rec.get("Ngày Cập Nhật") or str(rec.get("Ngày Cập Nhật")).lower() in ["nan", ""]):
                    rec["Ngày Cập Nhật"] = c_time

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
            "message": f"Lỗi đọc Google Sheet (GID {gid}): {e}",
            "records": [],
            "count": 0
        }

def is_final_status(kq_str):
    if not kq_str:
        return False
    k = normalize_nfc(kq_str).lower()
    return any(x in k for x in ["thành công", "đã xử lý", "đã clear", "đã cấp", "hoàn tất", "lỗi", "không thành công", "thất bại"])

def update_cache_record(signal_type, shd, status, update_time=None):
    cache_file = CLEAR_SIGNAL_CACHE_FILE if signal_type == "clear" else RESET_SIGNAL_CACHE_FILE
    cache = load_cache(cache_file)
    if not update_time:
        update_time = time.strftime("%d/%m/%Y %H:%M:%S")
    cache[shd] = {
        "status": status,
        "time": update_time
    }
    save_cache(cache_file, cache)
    return cache

class InsideSignalAutomation:
    """
    Module tự động hóa:
    1. Clear Tín Hiệu:
       - Đăng nhập inside.fpt.net
       - Menu trái: Quản lý Hợp đồng >> DSL & LLine >> Reset Mac >> Nhập SHD >> Tìm kiếm
       - Popup Reset MAC >> Xóa MAC cũ, dán MAC mới từ Sheet >> Bấm Cập nhật >> Bấm OK popup xác nhận >> Bấm OK popup thành công
       - Menu trái: Bấm Kill Session >> Nhập SHD vào Value >> Tìm kiếm >> Bấm Delete >> Bấm OK popup xác nhận
    2. Cấp Lại Tín Hiệu:
       - Đăng nhập inside.fpt.net
       - Đối soát và cấp lại tín hiệu đường truyền
    """
    def __init__(self, signal_type="clear", headless=True, log_cb=None):
        self.signal_type = signal_type
        self.headless = headless
        self.log_cb = log_cb or (lambda msg, lvl="info": print(f"[{lvl.upper()}] {msg}"))
        self.driver = None

    def log(self, msg, lvl="info"):
        try:
            self.log_cb(msg, lvl)
        except Exception:
            pass

    def init_driver(self):
        mode_str = "Chạy ngầm (Headless)" if self.headless else "Mở Chrome xem trực tiếp (Visible)"
        self.log(f"Khởi tạo trình duyệt Chrome phiên Inside FPT ({mode_str})...", "info")
        self.driver = core_login.create_driver_with_retry(
            headless=self.headless,
            keep_open=True,
            max_retries=2,
            log_cb=self.log_cb
        )
        self.check_and_ensure_login()
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

    def navigate_to_left_menu(self, menu_target="Reset Mac"):
        """
        Điều hướng trên Menu cây bên trái (Frame 0):
        Quản lý Hợp đồng >> DSL & LLine >> [menu_target]
        """
        self.driver.switch_to.default_content()
        wait = WebDriverWait(self.driver, 20)
        try:
            wait.until(EC.frame_to_be_available_and_switch_to_it(0))
        except Exception:
            self.driver.get("http://inside.fpt.net/default.asp")
            time.sleep(3)
            self.driver.switch_to.default_content()
            wait.until(EC.frame_to_be_available_and_switch_to_it(0))
        time.sleep(0.5)

        # 1. Mở rộng 'Quản lý Hợp đồng' nếu 'DSL & LLine' chưa hiển thị
        dsl_nodes = self.driver.find_elements(By.XPATH, "//a[contains(., 'DSL & LLine') or contains(., 'DSL & Lline') or contains(., 'DSL')]")
        if not any(el.is_displayed() for el in dsl_nodes):
            qlhd_nodes = self.driver.find_elements(By.XPATH, "//a[contains(., 'Quản lý Hợp đồng') or contains(., 'Quản lý hợp đồng') or contains(@data-english-name, 'Hop dong')]")
            if qlhd_nodes:
                qlhd = qlhd_nodes[0]
                plus_icons = qlhd.find_elements(By.XPATH, "./preceding-sibling::img | ./preceding-sibling::a/img | .//img | ../preceding-sibling::*//img")
                clicked = False
                for p in plus_icons:
                    if "plus" in (p.get_attribute("src") or ""):
                        self.log("Nhấp mở rộng 'Quản lý Hợp đồng'...", "info")
                        self.driver.execute_script("arguments[0].click();", p)
                        clicked = True
                        break
                if not clicked:
                    self.driver.execute_script("arguments[0].click();", qlhd)
                time.sleep(1)

        # 2. Mở rộng 'DSL & LLine' nếu menu_target chưa hiển thị
        target_nodes = self.driver.find_elements(By.XPATH, f"//a[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{menu_target.lower()}')]")
        if not any(el.is_displayed() for el in target_nodes):
            dsl_nodes = self.driver.find_elements(By.XPATH, "//a[contains(., 'DSL & LLine') or contains(., 'DSL & Lline') or contains(., 'DSL')]")
            if dsl_nodes:
                dsl = dsl_nodes[0]
                plus_icons = dsl.find_elements(By.XPATH, "./preceding-sibling::img | ./preceding-sibling::a/img | .//img | ../preceding-sibling::*//img")
                clicked = False
                for p in plus_icons:
                    if "plus" in (p.get_attribute("src") or ""):
                        self.log("Nhấp mở rộng 'DSL & LLine'...", "info")
                        self.driver.execute_script("arguments[0].click();", p)
                        clicked = True
                        break
                if not clicked:
                    self.driver.execute_script("arguments[0].click();", dsl)
                time.sleep(1)

        # 3. Bấm chọn menu_target
        target_nodes = self.driver.find_elements(By.XPATH, f"//a[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{menu_target.lower()}')]")
        vis_targets = [el for el in target_nodes if el.is_displayed()]
        btn = vis_targets[0] if vis_targets else (target_nodes[0] if target_nodes else None)
        if not btn:
            raise RuntimeError(f"Không tìm thấy mục '{menu_target}' trên menu cây Inside!")

        self.log(f"Bấm chọn menu: '{menu_target}'...", "info")
        self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", btn)
        self.driver.execute_script("arguments[0].click();", btn)
        time.sleep(2)

    def handle_modal_or_alert(self, expected_action="confirm", timeout=12):
        """
        Xử lý toàn diện cả alert JavaScript lẫn modal popup HTML (Kendo UI, EasyUI, Bootstrap, HTML generic) của Inside FPT:
        - expected_action: 'confirm' (xác nhận OK) hoặc 'alert' (thông báo kết quả OK)
        """
        ok_xpaths = [
            # 1. Kendo UI confirm / alert buttons (Đã xác định chính xác từ DOM Inside FPT)
            "//input[contains(@class, 'confirm_yes')]",
            "//button[contains(@class, 'confirm_yes')]",
            "//button[@id='btnAlertOk' or @id='btnConfirmOk']",
            "//input[@id='btnAlertOk' or @id='btnConfirmOk']",
            "//input[contains(@class, 'k-button') and (@value='OK' or @value='Ok' or @value='Đồng ý' or @value='Xác nhận')]",
            "//button[contains(@class, 'k-button') and (normalize-space()='OK' or normalize-space()='Ok' or normalize-space()='Đồng ý' or normalize-space()='Xác nhận')]",
            "//a[contains(@class, 'k-button') and (normalize-space()='OK' or normalize-space()='Ok' or normalize-space()='Đồng ý')]",

            # 2. Bên trong khung k-window hoặc popupMessage
            "//div[contains(@class, 'k-window')]//*[self::input or self::button or self::a][@value='OK' or @value='Ok' or normalize-space()='OK' or normalize-space()='Ok' or normalize-space()='Đồng ý' or normalize-space()='Xác nhận']",
            "//span[contains(@class, 'k-window-title')]/ancestor::div[contains(@class, 'k-window')]//*[self::input or self::button or self::a][@value='OK' or @value='Ok' or normalize-space()='OK']",
            "//div[contains(@class, 'popupMessage')]/ancestor::div[contains(@class, 'k-window')]//*[self::input or self::button or self::a][@value='OK' or @value='Ok' or normalize-space()='OK']",

            # 3. Specific element IDs
            "//input[@id='btnConfirmOk' or @id='btnAlertOk' or @id='btnOK' or @id='btnOk']",
            "//button[@id='btnConfirmOk' or @id='btnAlertOk' or @id='btnOK' or @id='btnOk']",

            # 4. Standard HTML inputs/buttons
            "//input[@type='button' and (@value='OK' or @value='Ok')]",
            "//input[@value='OK' or @value='Ok']",
            "//button[normalize-space()='OK' or normalize-space()='Ok' or normalize-space()='Đồng ý' or normalize-space()='Xác nhận']",
            "//a[normalize-space()='OK' or normalize-space()='Ok']",

            # 5. Generic modal/popup dialogs
            "//*[contains(@class, 'modal') or contains(@class, 'dialog') or contains(@class, 'popup') or contains(@class, 'messager')]//*[self::input or self::button or self::a][@value='OK' or @value='Ok' or normalize-space()='OK']"
        ]

        start = time.time()
        while time.time() - start < timeout:
            # 1. Thử alert JavaScript của trình duyệt
            try:
                alert = self.driver.switch_to.alert
                text = alert.text
                self.log(f"Popup trình duyệt alert ({expected_action}): '{text}' -> Bấm OK", "info")
                alert.accept()
                return True, f"native_alert: {text}"
            except Exception:
                pass

            # 2. Thử trong Frame hiện tại
            for xp in ok_xpaths:
                try:
                    found = self.driver.find_elements(By.XPATH, xp)
                    vis = [el for el in found if el.is_displayed()]
                    if vis:
                        target = vis[0]
                        tag_name = target.tag_name
                        val_attr = target.get_attribute("value") or target.text.strip()
                        cls_attr = target.get_attribute("class") or ""
                        id_attr = target.get_attribute("id") or ""

                        # Lấy nội dung thông báo nếu có
                        msg_txt = ""
                        try:
                            msgs = self.driver.find_elements(By.XPATH, "//div[contains(@class, 'popupMessage')] | //span[contains(@class, 'k-window-title')]")
                            msg_txt = " | ".join([m.text.strip() for m in msgs if m.is_displayed() and m.text.strip()])
                        except Exception:
                            pass

                        self.log(f"Phát hiện popup Inside FPT ({expected_action}): '{msg_txt or id_attr or val_attr}' -> Bấm OK ({tag_name})", "info")

                        try:
                            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", target)
                            self.driver.execute_script("arguments[0].focus();", target)
                            self.driver.execute_script("arguments[0].click();", target)
                            if self.driver.execute_script("return typeof window.jQuery !== 'undefined';"):
                                self.driver.execute_script("try { window.jQuery(arguments[0]).trigger('click'); } catch(e){}", target)
                        except Exception:
                            try:
                                target.click()
                            except Exception:
                                pass

                        # Chờ dialog đóng (hoặc phần tử trở thành stale)
                        for _ in range(12):
                            time.sleep(0.15)
                            try:
                                if not target.is_displayed():
                                    break
                            except Exception:
                                break

                        return True, f"in_frame: {tag_name}#{id_attr} (msg: {msg_txt})"
                except Exception:
                    pass

            # 3. Thử kiểm tra ở tầng top window (default_content) nếu không thấy trong Frame
            try:
                self.driver.switch_to.default_content()
                for xp in ok_xpaths:
                    found = self.driver.find_elements(By.XPATH, xp)
                    vis = [el for el in found if el.is_displayed()]
                    if vis:
                        target = vis[0]
                        tag_name = target.tag_name
                        self.log(f"Phát hiện popup tầng ngoài ({expected_action}) -> Bấm OK ({tag_name})", "info")
                        try:
                            self.driver.execute_script("arguments[0].click();", target)
                        except Exception:
                            target.click()
                        time.sleep(0.5)
                        self.driver.switch_to.frame(1)
                        return True, f"top_window: {tag_name}"
                self.driver.switch_to.frame(1)
            except Exception:
                try:
                    self.driver.switch_to.default_content()
                    self.driver.switch_to.frame(1)
                except Exception:
                    pass

            time.sleep(0.4)
        return False, "timeout"

    def execute_clear_mac(self, shd, mac_val=""):
        """
        Bước 2 & 3:
        Menu trái: Quản lý Hợp đồng >> DSL & LLine >> Reset Mac
        Nhập SHD vào ô fAgentName ('Nhập nội dung...') >> Tìm kiếm (btnSearch)
        Popup Reset MAC:
          - Nếu có mac_val (Clear tín hiệu): Xóa MAC cũ, điền MAC mới (fNewMAC)
          - Nếu không có mac_val (Cấp lại tín hiệu): Xóa trắng để trống chỗ MAC
        Cập nhật (btnChange)
        Xác nhận reset MAC ? >> Bấm OK
        Reset MAC thành công >> Bấm OK
        """
        self.navigate_to_left_menu("Reset Mac")

        # Chuyển sang Frame Content (Frame 1)
        self.driver.switch_to.default_content()
        wait = WebDriverWait(self.driver, 20)
        wait.until(EC.frame_to_be_available_and_switch_to_it(1))
        time.sleep(1)

        # 1. Tìm ô nhập Số Hợp Đồng trên khung Tìm kiếm: id='fAgentName' hoặc placeholder='Nhập nội dung...'
        inp_shd = None
        for _ in range(20):
            candidates = self.driver.find_elements(By.XPATH, "//input[@id='fAgentName'] | //input[@placeholder='Nhập nội dung...']")
            vis = [c for c in candidates if c.is_displayed()]
            if vis:
                inp_shd = vis[0]
                break
            time.sleep(0.5)

        if not inp_shd:
            inp_shd = wait.until(EC.visibility_of_element_located((By.XPATH, "//input[@id='fAgentName'] | //input[@placeholder='Nhập nội dung...']")))

        self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", inp_shd)
        self.driver.execute_script("arguments[0].focus();", inp_shd)
        inp_shd.clear()
        inp_shd.send_keys(Keys.CONTROL + "a")
        inp_shd.send_keys(Keys.BACKSPACE)
        inp_shd.send_keys(shd)
        self.driver.execute_script("arguments[0].value = arguments[1];", inp_shd, shd)
        self.driver.execute_script("arguments[0].dispatchEvent(new Event('input', { bubbles: true })); arguments[0].dispatchEvent(new Event('change', { bubbles: true }));", inp_shd)
        self.log(f"Đã nhập SHD '{shd}' vào ô tìm kiếm Reset MAC.", "info")
        time.sleep(0.5)

        # 2. Bấm nút Tìm kiếm (id='btnSearch')
        search_btns = self.driver.find_elements(By.XPATH, "//button[@id='btnSearch'] | //button[contains(., 'Tìm kiếm')] | //input[contains(@value, 'Tìm kiếm')]")
        vis_search = [b for b in search_btns if b.is_displayed()]
        btn_search = vis_search[0] if vis_search else (search_btns[0] if search_btns else None)
        if not btn_search:
            raise RuntimeError("Không tìm thấy nút 'Tìm kiếm' trên trang Reset MAC!")

        self.log("Bấm nút Tìm kiếm Reset MAC...", "info")
        self.driver.execute_script("arguments[0].click();", btn_search)
        time.sleep(2)

        # 3. Chờ POP-UP nhỏ tiêu đề 'Reset MAC' xuất hiện
        self.log("Chờ popup 'Reset MAC' xuất hiện...", "info")
        mac_input = None
        for _ in range(25):
            candidates = self.driver.find_elements(
                By.XPATH,
                "//input[@id='fNewMAC'] | "
                "//input[@placeholder='Nhập dữ liệu...'] | "
                "//input[@id='fMACAddress'] | "
                "//*[contains(text(), 'Địa chỉ MAC')]/following::input[@type='text'][1] | "
                "//div[contains(@class, 'modal')]//input[@type='text']"
            )
            vis = [c for c in candidates if c.is_displayed()]
            if vis:
                mac_input = vis[0]
                break
            time.sleep(0.5)

        if not mac_input:
            raise RuntimeError(f"Không tìm thấy popup 'Reset MAC' hoặc ô nhập MAC cho HĐ {shd}")

        # Xóa hết dữ liệu trong ô và dán dữ liệu MAC trên Sheet vào (hoặc để trống nếu Cấp lại tín hiệu)
        self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", mac_input)
        self.driver.execute_script("arguments[0].focus();", mac_input)
        mac_input.clear()
        mac_input.send_keys(Keys.CONTROL + "a")
        mac_input.send_keys(Keys.BACKSPACE)
        if mac_val:
            self.log(f"Tìm thấy popup Reset MAC. Xóa dữ liệu cũ, điền MAC mới: '{mac_val}'...", "info")
            mac_input.send_keys(mac_val)
            self.driver.execute_script("arguments[0].value = arguments[1];", mac_input, mac_val)
        else:
            self.log("Tìm thấy popup Reset MAC. Xóa trắng để trống chỗ MAC...", "info")
            self.driver.execute_script("arguments[0].value = '';", mac_input)
        self.driver.execute_script("arguments[0].dispatchEvent(new Event('input', { bubbles: true })); arguments[0].dispatchEvent(new Event('change', { bubbles: true }));", mac_input)
        time.sleep(0.5)

        # 4. Bấm nút 'Cập nhật' (id='btnChange')
        update_btns = self.driver.find_elements(
            By.XPATH,
            "//button[@id='btnChange'] | //button[contains(., 'Cập nhật')] | //input[contains(@value, 'Cập nhật')] | //a[contains(., 'Cập nhật')]"
        )
        vis_up = [u for u in update_btns if u.is_displayed()]
        btn_update = vis_up[0] if vis_up else (update_btns[0] if update_btns else None)
        if not btn_update:
            raise RuntimeError("Không tìm thấy nút 'Cập nhật' trong popup Reset MAC!")

        self.log("Bấm nút 'Cập nhật' Reset MAC...", "info")
        self.driver.execute_script("arguments[0].click();", btn_update)
        time.sleep(1)

        # 5. POP-UP 1: Xác nhận reset MAC ? >> Bấm OK
        self.log("Chờ popup 'Xác nhận reset MAC ?'...", "info")
        ok1, res1 = self.handle_modal_or_alert(expected_action="confirm", timeout=12)
        if ok1:
            self.log(f"Đã xác nhận reset MAC ({res1}).", "info")
        else:
            self.log("Không thấy popup xác nhận reset MAC, tiếp tục kiểm tra kết quả...", "warning")

        time.sleep(1.2)

        # 6. POP-UP 2: Reset MAC thành công >> Bấm OK
        self.log("Chờ thông báo kết quả Reset MAC...", "info")
        ok2, res2 = self.handle_modal_or_alert(expected_action="alert", timeout=12)
        if ok2:
            self.log(f"Đã đóng thông báo kết quả Reset MAC ({res2}).", "success")
        else:
            self.log("Không thấy thông báo kết quả Reset MAC (có thể hệ thống đã tự đóng hoặc xử lý xong).", "info")

        time.sleep(1)
        self.log(f"✅ Đã hoàn tất Reset MAC cho HĐ {shd}!", "success")

    def execute_kill_session(self, shd):
        """
        Bước 4:
        Menu trái: Bấm qua Kill Session >> Nhập SHD vào ô Value (id='inputValueSearch') >> Tìm kiếm (btnSearch)
        Bấm nút Delete >> POP-UP 'Bạn có chắc muốn xóa session này không?' >> Bấm OK
        """
        self.log(f"Chuyển sang chức năng Kill Session cho HĐ {shd}...", "info")
        self.navigate_to_left_menu("Kill Session")

        # Chuyển sang Frame Content (Frame 1)
        self.driver.switch_to.default_content()
        wait = WebDriverWait(self.driver, 20)
        wait.until(EC.frame_to_be_available_and_switch_to_it(1))
        time.sleep(1.5)

        # 1. Nhập SHD vào ô Value (id='inputValueSearch')
        val_input = None
        for _ in range(20):
            candidates = self.driver.find_elements(
                By.XPATH,
                "//input[@id='inputValueSearch'] | //input[@placeholder='Nhập nội dung...']"
            )
            vis = [c for c in candidates if c.is_displayed()]
            if vis:
                val_input = vis[0]
                break
            time.sleep(0.5)

        if not val_input:
            val_input = wait.until(EC.visibility_of_element_located((By.XPATH, "//input[@id='inputValueSearch'] | //input[@placeholder='Nhập nội dung...']")))

        self.log(f"Kill Session: Nhập SHD '{shd}' vào ô Value...", "info")
        self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", val_input)
        self.driver.execute_script("arguments[0].focus();", val_input)
        val_input.clear()
        val_input.send_keys(Keys.CONTROL + "a")
        val_input.send_keys(Keys.BACKSPACE)
        val_input.send_keys(shd)
        self.driver.execute_script("arguments[0].value = arguments[1];", val_input, shd)
        self.driver.execute_script("arguments[0].dispatchEvent(new Event('input', { bubbles: true })); arguments[0].dispatchEvent(new Event('change', { bubbles: true }));", val_input)
        time.sleep(0.5)

        # 2. Bấm nút Tìm kiếm (id='btnSearch')
        search_btns = self.driver.find_elements(
            By.XPATH,
            "//button[@id='btnSearch'] | //button[contains(., 'Tìm kiếm')] | //input[contains(@value, 'Tìm kiếm')]"
        )
        vis_search = [s for s in search_btns if s.is_displayed()]
        btn_search = vis_search[0] if vis_search else (search_btns[0] if search_btns else None)
        if btn_search:
            self.log("Bấm Tìm kiếm Kill Session...", "info")
            self.driver.execute_script("arguments[0].click();", btn_search)
            time.sleep(2.5)

        # 3. Kiểm tra bảng kết quả có nút Delete màu đỏ
        delete_btns = self.driver.find_elements(
            By.XPATH,
            "//button[contains(., 'Delete')] | //a[contains(., 'Delete')] | //input[contains(@value, 'Delete')]"
        )
        vis_del = [d for d in delete_btns if d.is_displayed()]

        if vis_del:
            self.log(f"Phát hiện session đang hoạt động cho HĐ {shd}. Bấm nút Delete...", "info")
            self.driver.execute_script("arguments[0].click();", vis_del[0])
            time.sleep(1)

            # 4. POPUP: Bạn có chắc muốn xóa session này không? >> Bấm OK
            self.log("Chờ popup xác nhận 'Bạn có chắc muốn xóa session này không?'...", "info")
            ok_del, res_del = self.handle_modal_or_alert(expected_action="confirm", timeout=12)
            if ok_del:
                self.log(f"Đã xác nhận xóa session ({res_del}).", "info")

            time.sleep(1.2)
            # Thông báo kết quả tiếp theo nếu có
            ok_res, res_info = self.handle_modal_or_alert(expected_action="alert", timeout=6)
            if ok_res:
                self.log(f"Đã đóng popup kết quả xóa session ({res_info}).", "info")
            self.log(f"✅ Đã xóa session thành công cho HĐ {shd}!", "success")
        else:
            self.log(f"HĐ {shd}: Không có session nào đang hoạt động cần xóa.", "info")

        time.sleep(1)

    def update_google_sheet(self, shd, record, kq_str="Đã xử lý", now_str=None):
        """
        Đẩy kết quả 'Đã xử lý' trực tiếp lên Google Sheet tương ứng qua Webhook Google Apps Script.
        """
        if not now_str:
            now_str = time.strftime("%d/%m/%Y %H:%M:%S")
        try:
            cfg = core_login.load_config()
            webhook_url = (
                cfg.get(f"{self.signal_type}_signal_webhook_url", "")
                or cfg.get("google_sheet_webhook_url", "")
                or "https://script.google.com/macros/s/AKfycbyX7gEztw78VM71U8HDFh1iUJAvkqV2fzlpUe5kAgrV9Io-R-kZuEeDYXwntlHkdr-M/exec"
            )
            gid = GID_CLEAR_SIGNAL if self.signal_type == "clear" else GID_RESET_SIGNAL
            payload = {
                "sheet_id": DEFAULT_SHEET_ID,
                "gid": gid,
                "row_id": record.get("ID") if isinstance(record, dict) else None,
                "shd": shd,
                "status": kq_str,
                "ket_qua": kq_str,
                "thao_tac": kq_str,
                "timestamp": now_str
            }
            req = urllib.request.Request(
                webhook_url,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"}
            )
            resp = urllib.request.urlopen(req, timeout=10).read().decode("utf-8", errors="ignore")
            self.log(f"Đã cập nhật trạng thái '{kq_str}' lên Google Sheet cho HĐ {shd} ({resp.strip()})", "success")
            return True
        except Exception as e:
            self.log(f"Không thể đẩy Webhook cập nhật Google Sheet cho HĐ {shd}: {e}", "warning")
            return False

    def process_row(self, record):
        """
        Thực thi quy trình xử lý theo yêu cầu cho từng dòng.
        """
        shd = str(record.get("SHD", "")).strip()
        mac = str(record.get("MAC", "")).strip()
        now_str = time.strftime("%d/%m/%Y %H:%M:%S")

        if not shd:
            raise ValueError("Bản ghi thiếu Số Hợp Đồng (SHD)")

        if self.signal_type == "clear":
            if not mac:
                raise ValueError(f"HĐ {shd} thiếu địa chỉ MAC trên Google Sheet")

            self.log(f"=== BẮT ĐẦU CLEAR TÍN HIỆU HĐ {shd} (MAC: {mac}) ===", "info")

            # 1. Thực hiện Reset MAC
            self.execute_clear_mac(shd, mac)

            # 2. Thực hiện Kill Session
            self.execute_kill_session(shd)

            status_str = "Đã xử lý"
            update_cache_record("clear", shd, status_str, now_str)
            # Cập nhật kết quả 'Đã xử lý' lên Google Sheet qua Webhook
            self.update_google_sheet(shd, record, status_str, now_str)
            self.log(f"🎉 HOÀN TẤT CLEAR TÍN HIỆU HĐ {shd}!", "success")
            return True, status_str, now_str
        else:
            # Cấp Lại Tín Hiệu: Thực hiện giống như Clear tín hiệu, nhưng xóa trắng để trống chỗ MAC và bấm reset MAC là kết thúc
            self.log(f"=== BẮT ĐẦU CẤP LẠI TÍN HIỆU HĐ {shd} (XÓA TRẮNG MAC) ===", "info")

            # 1. Thực hiện Reset MAC với ô MAC xóa trắng để trống
            self.execute_clear_mac(shd, mac_val="")

            status_str = "Đã xử lý"
            update_cache_record("reset", shd, status_str, now_str)
            # Cập nhật kết quả 'Đã xử lý' lên Google Sheet qua Webhook
            self.update_google_sheet(shd, record, status_str, now_str)
            self.log(f"🎉 HOÀN TẤT CẤP LẠI TÍN HIỆU HĐ {shd}!", "success")
            return True, status_str, now_str

    def close(self):
        """Khi hoàn tất 1 tác vụ: Đóng trình duyệt và xóa sạch toàn bộ session cũ."""
        if self.driver:
            self.log("Hoàn tất tác vụ: Đang đóng trình duyệt và xóa sạch toàn bộ session cũ...", "info")
            core_login.close_driver_and_clear_session(self.driver, log_cb=self.log_cb)
            self.driver = None

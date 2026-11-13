import os
import time
import json
import base64
import urllib.parse
import pyotp
from PIL import Image
from pyzbar.pyzbar import decode as decode_qr_codes
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

import sys
import subprocess

if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(BASE_DIR, "config.json")

def get_inside_profile_dir():
    """Lấy đường dẫn thư mục lưu Profile phiên Inside FPT trong thư mục dự án."""
    profile_dir = os.path.join(BASE_DIR, "InsideFPT_SessionProfile")
    os.makedirs(profile_dir, exist_ok=True)
    return profile_dir

def get_radius_profile_dir():
    """Lấy đường dẫn thư mục lưu Profile phiên Radius Portal."""
    radius_dir = os.path.join(BASE_DIR, "RadiusPortal_SessionProfile")
    os.makedirs(radius_dir, exist_ok=True)
    return radius_dir

def clear_inside_session(profile_dir=None, log_cb=None):
    """
    Xóa sạch toàn bộ session, cookie, cache của Inside FPT
    để phiên tiếp theo luôn bắt đầu đăng nhập lại từ đầu 100%.
    """
    if profile_dir is None:
        profile_dir = get_inside_profile_dir()

    def _log(msg, lvl="info"):
        if log_cb:
            try:
                log_cb(msg, lvl)
            except Exception:
                pass

    _log("Đang dọn dẹp và xóa sạch phiên session cũ...", "info")
    clean_profile_locks_and_orphans(profile_dir, log_cb=log_cb)

    targets = [
        os.path.join(profile_dir, "Default", "Network"),
        os.path.join(profile_dir, "Default", "Cookies"),
        os.path.join(profile_dir, "Default", "Cookies-journal"),
        os.path.join(profile_dir, "Default", "Session Storage"),
        os.path.join(profile_dir, "Default", "Local Storage"),
        os.path.join(profile_dir, "Default", "Sessions"),
        os.path.join(profile_dir, "Default", "Login Data"),
        os.path.join(profile_dir, "Default", "Login Data-journal"),
        os.path.join(profile_dir, "Default", "Web Data"),
        os.path.join(profile_dir, "Default", "Web Data-journal"),
        os.path.join(profile_dir, "Default", "Cache"),
        os.path.join(profile_dir, "Default", "Code Cache"),
    ]

    import shutil
    for t in targets:
        if os.path.exists(t):
            try:
                if os.path.isdir(t):
                    shutil.rmtree(t, ignore_errors=True)
                else:
                    os.remove(t)
            except Exception:
                pass

    _log("Đã dọn dẹp sạch sẽ toàn bộ phiên session cũ!", "success")

INSIDE_COOKIE_FILE = os.path.join(BASE_DIR, "inside_session_cookies.json")
INSIDE_SESSION_MAX_HOURS_DEFAULT = 0.75  # Tối đa 45 phút cho 1 Token SSO Inside FPT
INSIDE_SESSION_IDLE_MAX_MINUTES = 12     # Quá 12 phút không thao tác -> Token Inside New V5 (partner.fpt.net) dễ hết hạn ngầm, cần đăng nhập mới

def _cfg_keep_inside_session():
    """Mặc định GIỮ phiên Inside. Đặt "keep_inside_session": false trong config.json để quay về xóa phiên mỗi lần."""
    try:
        return bool(load_config().get("keep_inside_session", True))
    except Exception:
        return True

def _read_cookie_store():
    try:
        with open(INSIDE_COOKIE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, dict):
                return data
    except Exception:
        pass
    return {}

def save_inside_cookies(driver, new_login=False, log_cb=None):
    """Lưu cookie phiên Inside ra file (gộp cả inside.fpt.net và partner.fpt.net, tránh ghi đè mất cookie gốc khi đang ở cửa sổ phụ)."""
    old = _read_cookie_store()
    merged = {}
    if not new_login:
        for c in (old.get("cookies") or []):
            if isinstance(c, dict) and c.get("name"):
                key = (c.get("domain", ""), c.get("name", ""), c.get("path", "/"))
                merged[key] = c

    collected_any = False
    try:
        handles = list(driver.window_handles)
    except Exception:
        handles = []

    if handles:
        orig_handle = None
        try:
            orig_handle = driver.current_window_handle
        except Exception:
            pass
        for h in handles:
            try:
                driver.switch_to.window(h)
                for c in (driver.get_cookies() or []):
                    if isinstance(c, dict) and c.get("name"):
                        key = (c.get("domain", ""), c.get("name", ""), c.get("path", "/"))
                        merged[key] = c
                        collected_any = True
            except Exception:
                continue
        if orig_handle and orig_handle in handles:
            try:
                driver.switch_to.window(orig_handle)
            except Exception:
                pass
    else:
        try:
            for c in (driver.get_cookies() or []):
                if isinstance(c, dict) and c.get("name"):
                    key = (c.get("domain", ""), c.get("name", ""), c.get("path", "/"))
                    merged[key] = c
                    collected_any = True
        except Exception:
            pass

    if not collected_any and not merged:
        return

    now = time.time()
    login_at = now if (new_login or not old.get("login_at")) else old.get("login_at")
    try:
        with open(INSIDE_COOKIE_FILE, "w", encoding="utf-8") as f:
            json.dump({"login_at": login_at, "saved_at": now, "cookies": list(merged.values())}, f, ensure_ascii=False)
    except Exception:
        pass

def restore_inside_cookies(driver):
    store = _read_cookie_store()
    cookies = store.get("cookies") or []
    if not cookies:
        return False
    try:
        driver.get("http://inside.fpt.net/")
    except Exception:
        return False
    ok = 0
    for c in cookies:
        c = dict(c)
        dom = str(c.get("domain") or "").lower().lstrip(".")
        # Khi đang ở inside.fpt.net chỉ nạp cookie của inside.fpt.net (cookie partner.fpt.net nằm sẵn trong Chrome Profile)
        if dom and "inside.fpt.net" not in dom:
            continue
        if isinstance(c.get("expiry"), float):
            c["expiry"] = int(c["expiry"])
        c.pop("sameSite", None)
        try:
            driver.add_cookie(c)
            ok += 1
        except Exception:
            try:
                c.pop("domain", None)
                driver.add_cookie(c)
                ok += 1
            except Exception:
                pass
    return ok > 0 or bool(store.get("login_at"))

def invalidate_session(profile_dir=None, log_cb=None):
    """Hủy phiên đang giữ (khi nghi ngờ phiên chết/đơ) để lần sau đăng nhập mới 100%."""
    try:
        if os.path.exists(INSIDE_COOKIE_FILE):
            os.remove(INSIDE_COOKIE_FILE)
    except Exception:
        pass
    clear_inside_session(profile_dir=profile_dir, log_cb=log_cb)

def inside_session_healthy(driver, log_cb=None):
    """
    Kiểm tra phiên Inside còn dùng được, bắt cả 4 dạng lỗi:
    1) Thời gian không tương tác vượt quá 12 phút (Token SSO Inside New V5 / partner.fpt.net đã hết hạn ngầm dù menu ASP vẫn còn)
    2) Bị chuyển về login.fpt.net
    3) Khung đăng nhập nằm lọt trong sidebar/frame của inside.fpt.net
    4) Trang đơ / không nạp được menu (không mở nổi cửa sổ phiếu bảo trì, triển khai)
    """
    def _log(msg, lvl="info"):
        if log_cb:
            try:
                log_cb(msg, lvl)
            except Exception:
                pass

    max_h = INSIDE_SESSION_MAX_HOURS_DEFAULT
    idle_min = INSIDE_SESSION_IDLE_MAX_MINUTES
    try:
        cfg_loaded = load_config()
        max_h = float(cfg_loaded.get("inside_session_max_hours", max_h))
        idle_min = float(cfg_loaded.get("inside_session_idle_minutes", idle_min))
    except Exception:
        pass
    store = _read_cookie_store()
    now = time.time()
    if not store.get("login_at"):
        _log("Chưa có thông tin mốc đăng nhập hợp lệ -> làm mới đăng nhập.", "info")
        return False
    if (now - float(store["login_at"])) > max_h * 3600:
        _log(f"Phiên đã giữ quá {max_h * 60:.0f} phút -> làm mới đăng nhập.", "info")
        return False
    last_active = float(store.get("saved_at") or store.get("login_at") or 0)
    if last_active and (now - last_active) > idle_min * 60:
        _log(f"Phiên đã nghỉ {(now - last_active) / 60:.1f} phút (> {idle_min:g} phút, Token Inside V5 có thể đã hết hạn) -> làm mới đăng nhập.", "info")
        return False

    try:
        driver.set_page_load_timeout(30)
        driver.get("http://inside.fpt.net/default.asp")
    except Exception:
        _log("Trang Inside đơ/không nạp được trong 30s -> coi như phiên hỏng.", "warning")
        return False
    finally:
        try:
            driver.set_page_load_timeout(300)
        except Exception:
            pass

    time.sleep(2)
    try:
        curr = (driver.current_url or "").lower()
        if "login.fpt.net" in curr or "inside.fpt.net" not in curr:
            _log("Phiên hết hạn (bị chuyển về trang đăng nhập).", "info")
            return False

        def _has_login_form():
            for fid in ("fUserName", "fPassword"):
                for el in driver.find_elements(By.ID, fid):
                    try:
                        if el.is_displayed():
                            return True
                    except Exception:
                        pass
            for el in driver.find_elements(
                By.XPATH,
                "//button[contains(., 'ĐĂNG NHẬP VỚI IAM') or contains(., 'Đăng nhập với IAM')] | "
                "//a[contains(., 'ĐĂNG NHẬP VỚI IAM') or contains(., 'Đăng nhập với IAM')]",
            ):
                try:
                    if el.is_displayed():
                        return True
                except Exception:
                    pass
            return False

        driver.switch_to.default_content()
        _login_form_detected = _has_login_form()
        if not _login_form_detected:
            frames = driver.find_elements(By.TAG_NAME, "iframe") + driver.find_elements(By.TAG_NAME, "frame")
            for idx in range(len(frames)):
                try:
                    driver.switch_to.default_content()
                    driver.switch_to.frame(idx)
                    if _has_login_form():
                        _login_form_detected = True
                        break
                except Exception:
                    continue
            driver.switch_to.default_content()

        if _login_form_detected:
            _log("Phiên Inside hết hạn, cần đăng nhập lại (phát hiện khung đăng nhập trong trang).", "warning")
            return False

        driver.switch_to.default_content()
        menu_keywords = ("hỗ trợ kỹ thuật", "quản lý hợp đồng")

        def _menu_in_current_frame():
            try:
                txt = (driver.find_element(By.TAG_NAME, "body").text or "").lower()
            except Exception:
                return False
            return any(k in txt for k in menu_keywords)

        menu_ok = False
        deadline = time.time() + 15
        while time.time() < deadline and not menu_ok:
            try:
                driver.switch_to.default_content()
                if _menu_in_current_frame():
                    menu_ok = True
                    break
                n_fr = len(driver.find_elements(By.TAG_NAME, "iframe") + driver.find_elements(By.TAG_NAME, "frame"))
                for idx in range(n_fr):
                    try:
                        driver.switch_to.default_content()
                        driver.switch_to.frame(idx)
                        if _menu_in_current_frame():
                            menu_ok = True
                            break
                    except Exception:
                        continue
            except Exception:
                pass
            if not menu_ok:
                time.sleep(1)
        try:
            driver.switch_to.default_content()
        except Exception:
            pass
        if not menu_ok:
            _log("Không thấy menu 'Hỗ trợ kỹ thuật' (trang đơ/chưa nạp đủ) -> phiên hỏng.", "warning")
            return False
        return True
    except Exception as e:
        _log(f"Lỗi kiểm tra phiên: {e}", "warning")
        return False

def close_driver_and_clear_session(driver=None, profile_dir=None, log_cb=None):
    """
    Khi hoàn tất 1 tác vụ: đóng trình duyệt.
    - Mặc định GIỮ phiên (lưu cookie + giữ profile) để lần sau không phải đăng nhập lại.
    - Nếu config "keep_inside_session": false thì xóa sạch phiên như trước.
    """
    keep = _cfg_keep_inside_session()
    if driver is not None:
        if keep:
            save_inside_cookies(driver)
        else:
            try:
                driver.delete_all_cookies()
            except Exception:
                pass
        try:
            driver.quit()
        except Exception:
            pass
    if keep:
        if log_cb:
            try:
                log_cb("Đã đóng trình duyệt, GIỮ phiên Inside cho lần chạy sau.", "info")
            except Exception:
                pass
        clean_profile_locks_and_orphans(profile_dir, log_cb=log_cb)
    else:
        invalidate_session(profile_dir=profile_dir, log_cb=log_cb)

def clean_profile_locks_and_orphans(profile_dir=None, log_cb=None):
    """
    Dọn dẹp các tiến trình chromedriver/chrome treo đang giữ thư mục profile Inside FPT,
    đồng thời xóa các file lock (SingletonLock, DevToolsActivePort,...) để ngăn ngừa lỗi:
    'Chrome failed to start: crashed. (DevToolsActivePort file doesn't exist)'.
    Tuyệt đối giữ nguyên cookie và phiên đăng nhập.
    """
    if profile_dir is None:
        profile_dir = get_inside_profile_dir()

    def _log(msg, lvl="info"):
        if log_cb:
            try:
                log_cb(msg, lvl)
            except Exception:
                pass

    norm_profile = os.path.normpath(profile_dir).lower()

    if sys.platform.startswith("win"):
        try:
            cmd = [
                'powershell', '-NoProfile', '-Command',
                "Get-CimInstance Win32_Process -Filter \"Name = 'chrome.exe' or Name = 'chromedriver.exe'\" | Select-Object ProcessId, CommandLine | ConvertTo-Csv -NoTypeInformation"
            ]
            res = subprocess.check_output(cmd, text=True, errors='ignore')
            for line in res.splitlines():
                line_lower = line.lower()
                # CHỈ giải phóng các tiến trình đang khóa đúng thư mục profile này
                if norm_profile in line_lower:
                    parts = line.split(',')
                    if parts and parts[0].replace('"', '').isdigit():
                        pid = parts[0].replace('"', '')
                        _log(f"Đang giải phóng tiến trình treo PID {pid} cho {os.path.basename(profile_dir)}...", "warning")
                        subprocess.run(['taskkill', '/F', '/T', '/PID', pid], capture_output=True)
        except Exception as e:
            _log(f"Lưu ý khi dọn dẹp tiến trình cũ: {e}", "warning")
    else:
        try:
            subprocess.run(['pkill', '-f', os.path.basename(profile_dir)], capture_output=True)
        except Exception:
            pass

    lock_files = [
        "DevToolsActivePort",
        "SingletonLock",
        "SingletonCookie",
        "SingletonSocket",
        "lockfile"
    ]
    for lf in lock_files:
        p = os.path.join(profile_dir, lf)
        if os.path.exists(p):
            try:
                os.remove(p)
                _log(f"Đã giải phóng file khóa: {lf}", "info")
            except Exception:
                pass

def build_chrome_options(headless=False, profile_dir=None, keep_open=False):
    """
    Tạo Chrome Options chuẩn hóa, ổn định tối đa cho Windows,
    ngăn ngừa GPU crash và DevTools port conflict.
    """
    options = Options()
    if headless:
        options.add_argument('--headless=new')
    else:
        options.add_argument('--start-maximized')
    options.add_argument('--window-size=1920,1080')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.add_argument('--disable-software-rasterizer')
    options.add_argument('--disable-features=RendererCodeIntegrity,Crashpad,HttpsUpgrades,HttpsFirstBalancedModeAutoEnable')
    options.add_argument('--ignore-certificate-errors')
    options.add_argument('--ignore-ssl-errors=yes')
    options.add_argument('--allow-running-insecure-content')
    options.add_argument('--no-first-run')
    options.add_argument('--no-default-browser-check')
    options.add_argument('--disable-session-crashed-bubble')
    options.add_argument('--hide-crash-restore-bubble')
    options.add_argument('--disable-popup-blocking')
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)

    if (not headless) or keep_open:
        options.add_experimental_option("detach", True)

    if profile_dir is None:
        profile_dir = get_inside_profile_dir()
    options.add_argument(f"--user-data-dir={profile_dir}")

    return options, profile_dir

def create_driver_with_retry(headless=False, profile_dir=None, keep_open=False, max_retries=2, log_cb=None):
    """
    Khởi tạo Chrome Driver có cơ chế tự động dọn dẹp khóa và thử lại nếu gặp lỗi crash hoặc port.
    """
    if profile_dir is None:
        profile_dir = get_inside_profile_dir()

    clean_profile_locks_and_orphans(profile_dir, log_cb=log_cb)

    for attempt in range(1, max_retries + 1):
        try:
            options, _ = build_chrome_options(headless=headless, profile_dir=profile_dir, keep_open=keep_open)
            driver = webdriver.Chrome(options=options)
            return driver
        except Exception as e_launch:
            err_str = str(e_launch)
            if log_cb:
                try:
                    log_cb(f"Khởi động Chrome lần {attempt} gặp sự cố: {err_str[:90]}... Đang dọn dẹp và thử lại...", "warning")
                except Exception:
                    pass
            clean_profile_locks_and_orphans(profile_dir, log_cb=log_cb)
            time.sleep(1.5)
            if attempt == max_retries:
                raise e_launch

def init_chrome_driver(headless=False, keep_open=True, profile_dir=None, use_custom_profile=True, log_cb=None):
    """
    Alias tương thích ngược cho create_driver_with_retry.
    """
    return create_driver_with_retry(
        headless=headless,
        keep_open=keep_open,
        profile_dir=profile_dir,
        max_retries=2,
        log_cb=log_cb
    )

DEFAULT_ACCOUNT = {
    "username": "phuongnam.phongnh5",
    "password": "Benngo@@2026",
    "totp_secret": "J5MBXLD2IZJSJWADQU",
    "use_otp": True,
    "account_name": "Phuongnam.phongnh5@inside.fpt.net"
}

DEFAULT_AM_ACCOUNT = {
    "username": "phuongnam.phongnh5@fpt.net",
    "password": "Benngo@@20262027",
    "account_name": "phuongnam.phongnh5@fpt.net"
}

def load_config():
    cfg = {}
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                cfg = json.load(f)
        except Exception:
            cfg = {}

    # Ensure default_account (Inside FPT)
    if "default_account" not in cfg or not isinstance(cfg["default_account"], dict):
        cfg["default_account"] = DEFAULT_ACCOUNT.copy()
    else:
        # Guarantee default credentials are preserved
        if not cfg["default_account"].get("username"):
            cfg["default_account"]["username"] = DEFAULT_ACCOUNT["username"]
        if not cfg["default_account"].get("password"):
            cfg["default_account"]["password"] = DEFAULT_ACCOUNT["password"]
        if not cfg["default_account"].get("totp_secret"):
            cfg["default_account"]["totp_secret"] = DEFAULT_ACCOUNT["totp_secret"]
        cfg["default_account"]["use_otp"] = True

    # Ensure AM account (Radius Portal / SpamPool / Bypass NAT)
    if "am_account" not in cfg or not isinstance(cfg.get("am_account"), dict):
        cfg["am_account"] = DEFAULT_AM_ACCOUNT.copy()
    else:
        if not cfg["am_account"].get("username"):
            cfg["am_account"]["username"] = DEFAULT_AM_ACCOUNT["username"]
        if not cfg["am_account"].get("password"):
            cfg["am_account"]["password"] = DEFAULT_AM_ACCOUNT["password"]

    cfg["am_username"] = cfg["am_account"]["username"]
    cfg["am_password"] = cfg["am_account"]["password"]
    cfg["radius_username"] = cfg["am_account"]["username"]
    cfg["radius_password"] = cfg["am_account"]["password"]

    # Ensure custom_account
    if "custom_account" not in cfg or not isinstance(cfg["custom_account"], dict):
        cfg["custom_account"] = {
            "username": "",
            "password": "",
            "totp_secret": "",
            "use_otp": False,
            "account_name": ""
        }

    if "active_account" not in cfg:
        cfg["active_account"] = "default"

    active_key = "default_account" if cfg["active_account"] == "default" else "custom_account"
    active_data = cfg[active_key]

    # Backward compatibility fields at root level (Inside FPT account)
    cfg["username"] = active_data.get("username") or DEFAULT_ACCOUNT["username"]
    cfg["password"] = active_data.get("password") or DEFAULT_ACCOUNT["password"]
    cfg["totp_secret"] = active_data.get("totp_secret", "")
    cfg["use_otp"] = active_data.get("use_otp", True if cfg["active_account"] == "default" else False)
    cfg["account_name"] = active_data.get("account_name", "")

    return cfg

def get_am_account_info(cfg=None):
    if cfg is None:
        cfg = load_config()
    am = cfg.get("am_account") or cfg.get("radius_account") or {}
    u = am.get("username") or cfg.get("am_username") or cfg.get("radius_username") or DEFAULT_AM_ACCOUNT["username"]
    p = am.get("password") or cfg.get("am_password") or cfg.get("radius_password") or DEFAULT_AM_ACCOUNT["password"]
    return {
        "username": u.strip(),
        "password": p
    }

def get_active_account_info(cfg=None):
    if cfg is None:
        cfg = load_config()
    mode = cfg.get("active_account", "default")
    if mode == "custom":
        custom = cfg.get("custom_account", {})
        if custom.get("username"):
            has_secret = bool(custom.get("totp_secret", "").strip())
            use_otp = bool(custom.get("use_otp", False)) and has_secret
            return {
                "mode": "custom",
                "username": custom.get("username", "").strip(),
                "password": custom.get("password", ""),
                "totp_secret": custom.get("totp_secret", "").strip(),
                "use_otp": use_otp,
                "account_name": custom.get("account_name", "Tùy chỉnh")
            }
    # Default account
    default = cfg.get("default_account", DEFAULT_ACCOUNT)
    return {
        "mode": "default",
        "username": default.get("username", DEFAULT_ACCOUNT["username"]).strip(),
        "password": default.get("password", DEFAULT_ACCOUNT["password"]),
        "totp_secret": default.get("totp_secret", DEFAULT_ACCOUNT["totp_secret"]).strip(),
        "use_otp": True,
        "account_name": default.get("account_name", DEFAULT_ACCOUNT["account_name"])
    }

def save_config(config_data):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config_data, f, indent=2, ensure_ascii=False)

def get_totp_info(secret=None):
    """Returns (current_otp, seconds_remaining)"""
    if not secret:
        acc = get_active_account_info()
        secret = acc.get("totp_secret", DEFAULT_ACCOUNT["totp_secret"])
    
    # Clean secret
    secret = (secret or "").strip().replace(" ", "").upper()
    if not secret:
        return "------", 0
    try:
        totp = pyotp.TOTP(secret)
        current_code = totp.now()
        now = int(time.time())
        seconds_remaining = 30 - (now % 30)
        return current_code, seconds_remaining
    except Exception:
        return "------", 0

def parse_varint(data, offset):
    res = 0
    shift = 0
    while True:
        b = data[offset]
        offset += 1
        res |= (b & 0x7f) << shift
        if not (b & 0x80):
            break
        shift += 7
    return res, offset

def parse_proto(data):
    offset = 0
    fields = {}
    while offset < len(data):
        tag, offset = parse_varint(data, offset)
        field_num = tag >> 3
        wire_type = tag & 0x07
        if wire_type == 0:
            val, offset = parse_varint(data, offset)
        elif wire_type == 2:
            length, offset = parse_varint(data, offset)
            val = data[offset:offset+length]
            offset += length
        else:
            raise ValueError(f"Unsupported wire type {wire_type}")
        if field_num not in fields:
            fields[field_num] = []
        fields[field_num].append(val)
    return fields

def extract_secret_from_qr_image(image_path):
    """Decodes QR code and extracts the TOTP secret key."""
    img = Image.open(image_path)
    decoded_list = decode_qr_codes(img)
    if not decoded_list:
        raise ValueError("Không tìm thấy mã QR nào trong hình ảnh!")

    qr_text = decoded_list[0].data.decode("utf-8", errors="ignore")
    
    # Check if Google Authenticator Migration
    if qr_text.startswith("otpauth-migration://"):
        parsed = urllib.parse.urlsplit(qr_text)
        qs = urllib.parse.parse_qs(parsed.query)
        if "data" not in qs:
            raise ValueError("Mã QR Google Authenticator không chứa tham số data")
        raw = base64.b64decode(qs["data"][0])
        top = parse_proto(raw)
        params = top.get(1, [])
        if not params:
            raise ValueError("Không đọc được tham số OTP từ Google Authenticator data")
        item = parse_proto(params[0])
        sec = item.get(1, [b""])[0]
        sec_b32 = base64.b32encode(sec).decode("ascii").rstrip("=")
        name = item.get(2, [b""])[0].decode("utf-8", errors="ignore")
        return sec_b32, name
    elif qr_text.startswith("otpauth://"):
        parsed = urllib.parse.urlsplit(qr_text)
        qs = urllib.parse.parse_qs(parsed.query)
        sec = qs.get("secret", [""])[0]
        return sec, parsed.path
    else:
        raise ValueError(f"Định dạng QR không nhận diện được: {qr_text}")

def _should_use_iam_login(driver):
    """Kiem tra trang hien tai co yeu cau dang nhap qua IAM/AM hay khong."""
    curr = (driver.current_url or "").lower()
    if "iam.fpt." in curr or "login.microsoftonline.com" in curr:
        return True
    iam_btns = driver.find_elements(
        By.XPATH,
        "//button[contains(., 'ĐĂNG NHẬP VỚI IAM') or contains(., 'Đăng nhập với IAM')] | "
        "//a[contains(., 'ĐĂNG NHẬP VỚI IAM') or contains(., 'Đăng nhập với IAM')] | "
        "//input[contains(@value, 'IAM')]",
    )
    if any(b.is_displayed() for b in iam_btns):
        return True
    p_elems = driver.find_elements(By.ID, "fPassword")
    if p_elems and p_elems[0].get_attribute("disabled") is not None:
        return True
    return False


def _login_inside_via_iam_am(driver, config, log):
    """Dang nhap Inside bang nut DANG NHAP VOI IAM + tai khoan AM (Azure AD / Microsoft)."""
    am_acc = get_am_account_info(config)
    am_user = am_acc["username"]
    if "@" not in am_user:
        am_user = f"{am_user}@fpt.net"
    am_pass = am_acc["password"]
    wait = WebDriverWait(driver, 15)

    curr_url = (driver.current_url or "").lower()
    if "login.fpt.net" in curr_url or "inside.fpt.net" in curr_url:
        try:
            btn_iam = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((
                    By.XPATH,
                    "//button[contains(., 'ĐĂNG NHẬP VỚI IAM') or contains(., 'Đăng nhập với IAM')] | "
                    "//a[contains(., 'ĐĂNG NHẬP VỚI IAM') or contains(., 'Đăng nhập với IAM')] | "
                    "//input[contains(@value, 'IAM')]",
                ))
            )
            log("Đang bấm nút [ĐĂNG NHẬP VỚI IAM]...", "info")
            driver.execute_script("arguments[0].click();", btn_iam)
            WebDriverWait(driver, 10).until(
                lambda d: "iam.fpt." in (d.current_url or "").lower()
                or "login.microsoftonline.com" in (d.current_url or "").lower()
                or ("inside.fpt.net" in (d.current_url or "").lower() and "login.fpt.net" not in (d.current_url or "").lower())
            )
        except Exception:
            pass

    curr_url = (driver.current_url or "").lower()
    if "iam.fpt." in curr_url:
        try:
            btn_az = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((
                    By.XPATH,
                    "//a[contains(., 'Azure AD')] | //button[contains(., 'Azure AD')] | //*[@id='zocial-azure-ad'] | //*[contains(text(), 'Azure AD')]",
                ))
            )
            log("Đang chọn phương thức [Azure AD] trên IAM...", "info")
            driver.execute_script("arguments[0].click();", btn_az)
            time.sleep(2.5)
        except Exception:
            u_inps = [e for e in driver.find_elements(By.XPATH, "//input[@id='username' or @name='username' or @type='email']") if e.is_displayed()]
            p_inps = [e for e in driver.find_elements(By.XPATH, "//input[@type='password']") if e.is_displayed()]
            if u_inps and p_inps:
                log("Đang điền tài khoản AM trên trang IAM...", "info")
                u_inps[0].send_keys(Keys.CONTROL, "a")
                u_inps[0].send_keys(am_user)
                p_inps[0].send_keys(Keys.CONTROL, "a")
                p_inps[0].send_keys(am_pass)
                sub = driver.find_elements(By.XPATH, "//input[@type='submit'] | //button[@type='submit']")
                if sub:
                    driver.execute_script("arguments[0].click();", sub[0])
                time.sleep(2.5)

    try:
        WebDriverWait(driver, 15).until(
            lambda d: "login.microsoftonline.com" in (d.current_url or "").lower()
            or ("inside.fpt.net" in (d.current_url or "").lower() and "login.fpt.net" not in (d.current_url or "").lower())
        )
    except Exception:
        pass

    curr_url = (driver.current_url or "").lower()
    if "login.microsoftonline.com" in curr_url:
        base_user = am_user.split("@")[0].lower()
        picker = driver.find_elements(
            By.XPATH,
            f"//div[contains(@data-test-id, '{am_user}') or contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{base_user}') or contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{am_user.lower()}') or contains(@data-username, '{am_user}')]",
        )
        displayed_pickers = [p for p in picker if p.is_displayed()]
        if displayed_pickers:
            log(f"Chọn tài khoản AM đã lưu: {am_user}", "info")
            try:
                displayed_pickers[0].click()
            except Exception:
                driver.execute_script("arguments[0].click();", displayed_pickers[0])
            time.sleep(2.0)
        else:
            emails = [e for e in driver.find_elements(By.XPATH, "//input[@type='email' or @name='loginfmt' or @id='i0116']") if e.is_displayed()]
            if emails:
                log(f"Điền email tài khoản AM: {am_user}", "info")
                emails[0].send_keys(Keys.CONTROL, "a")
                emails[0].send_keys(Keys.BACKSPACE)
                time.sleep(0.2)
                emails[0].send_keys(am_user)
                time.sleep(0.5)
                btn_next = wait.until(EC.element_to_be_clickable((
                    By.XPATH, "//input[@type='submit' or @id='idSIButton9' or @value='Next'] | //button[@type='submit' or @id='idSIButton9']"
                )))
                driver.execute_script("arguments[0].click();", btn_next)
                time.sleep(2.5)

        pass_elem = None
        for _ in range(12):
            curr = (driver.current_url or "").lower()
            if "inside.fpt.net" in curr and "login.fpt.net" not in curr:
                break
            disp_pass = [p for p in driver.find_elements(By.XPATH, "//input[@type='password' or @name='passwd' or @id='i0118']") if p.is_displayed()]
            if disp_pass:
                pass_elem = disp_pass[0]
                break
            btn_yes = driver.find_elements(By.XPATH, "//input[@id='idSIButton9' or @value='Yes'] | //button[@id='idSIButton9' or contains(text(), 'Yes')]")
            if any(b.is_displayed() for b in btn_yes):
                break
            time.sleep(0.8)

        if pass_elem is not None:
            log("Đang điền mật khẩu tài khoản AM...", "info")
            pass_elem.send_keys(Keys.CONTROL, "a")
            pass_elem.send_keys(Keys.BACKSPACE)
            time.sleep(0.2)
            pass_elem.send_keys(am_pass)
            time.sleep(0.5)
            btn_signin = wait.until(EC.element_to_be_clickable((
                By.XPATH, "//input[@type='submit' or @id='idSIButton9' or @value='Sign in'] | //button[@type='submit' or @id='idSIButton9']"
            )))
            driver.execute_script("arguments[0].click();", btn_signin)
            time.sleep(2.5)

            err_boxes = driver.find_elements(By.XPATH, "//*[@id='passwordError'] | //*[contains(@class, 'error') and (contains(text(), 'incorrect') or contains(text(), 'không đúng'))]")
            for eb in err_boxes:
                if eb.is_displayed() and eb.text.strip():
                    raise RuntimeError(f"Sai mật khẩu hoặc tài khoản Microsoft AM: {eb.text.strip()}")

        try:
            btn_yes = WebDriverWait(driver, 8).until(EC.element_to_be_clickable((
                By.XPATH, "//input[@id='idSIButton9' or @value='Yes'] | //button[@id='idSIButton9' or contains(text(), 'Yes')]"
            )))
            log("Nhấn [YES] duy trì trạng thái đăng nhập...", "info")
            driver.execute_script("arguments[0].click();", btn_yes)
            time.sleep(2.5)
        except Exception:
            pass

    log("Đang chờ chuyển hướng vào inside.fpt.net (tối đa 45s)...", "info")
    WebDriverWait(driver, 45).until(
        lambda d: "inside.fpt.net" in (d.current_url or "").lower()
        and "login.fpt.net" not in (d.current_url or "").lower()
        and "iam.fpt." not in (d.current_url or "").lower()
        and "login.microsoftonline.com" not in (d.current_url or "").lower()
    )


def run_fpt_login(username=None, password=None, secret=None, use_otp=None, headless=False, keep_open=True, use_custom_profile=True, log_callback=None, driver=None):
    """
    Executes the automated login flow on login.fpt.net / inside.fpt.net.
    If driver is passed, reuses existing browser instance.
    """
    def log(msg, status="info"):
        if log_callback:
            try:
                log_callback(msg, status)
            except Exception:
                pass
        else:
            try:
                print(f"[{status.upper()}] {msg}")
            except Exception:
                try:
                    print(f"[{status.upper()}] {msg.encode('ascii', 'replace').decode('ascii')}")
                except Exception:
                    pass

    config = load_config()
    active_acc = get_active_account_info(config)

    username = username or active_acc["username"]
    password = password or active_acc["password"]
    if use_otp is None:
        use_otp = active_acc["use_otp"]
    secret = secret or active_acc["totp_secret"]
    login_url = config.get("login_url", "http://login.fpt.net/?urlreturn=inside.fpt.net")

    created_driver = False
    if driver is None:
        log("Đang khởi tạo trình duyệt Google Chrome...", "info")
        p_dir = get_inside_profile_dir() if use_custom_profile else None
        try:
            driver = create_driver_with_retry(
                headless=headless,
                profile_dir=p_dir,
                keep_open=keep_open,
                max_retries=2,
                log_cb=log_callback
            )
            created_driver = True
        except Exception as e:
            log(f"Lỗi khởi động Chrome: {e}", "error")
            raise e

    try:
        # Thử dùng lại phiên đã giữ (nếu bật) -> chỉ đăng nhập lại khi phiên chết/đơ/lỗi khung đăng nhập
        if _cfg_keep_inside_session():
            try:
                driver.get("http://inside.fpt.net/")
                restored = restore_inside_cookies(driver)
            except Exception:
                restored = False
            log("Đang kiểm tra phiên Inside đã giữ..." if restored else "Chưa có phiên đã lưu, kiểm tra phiên trong profile...", "info")
            if inside_session_healthy(driver, log_cb=log_callback):
                log("Phiên Inside còn hoạt động -> dùng lại, không cần đăng nhập!", "success")
                current_url = driver.current_url
                page_title = driver.title
                if created_driver and not keep_open:
                    save_inside_cookies(driver)
                    driver.quit()
                return True, current_url, page_title
            log("Phiên không dùng được -> đăng nhập mới.", "warning")

        # Xóa sạch cookie trước khi đăng nhập mới
        try:
            driver.delete_all_cookies()
        except Exception:
            pass

        log(f"Đang điều hướng đến trang xác thực: {login_url}", "info")
        driver.get(login_url)
        time.sleep(2)

        curr_url = (driver.current_url or "").lower()
        used_iam_login = False
        if "inside.fpt.net" in curr_url and "login.fpt.net" not in curr_url:
            log("Trình duyệt đã chuyển thẳng vào Inside FPT thành công!", "success")
        elif _should_use_iam_login(driver):
            _login_inside_via_iam_am(driver, config, log)
            used_iam_login = True
        else:
            # Wait for user input box
            wait = WebDriverWait(driver, 15)
            u_elem = wait.until(EC.presence_of_element_located((By.ID, "fUserName")))
            p_elem = wait.until(EC.presence_of_element_located((By.ID, "fPassword")))
            cb_otp = wait.until(EC.presence_of_element_located((By.ID, "cbOTP")))

            log(f"Đang điền thông tin đăng nhập [{active_acc['mode'].upper()}]: {username}", "info")
            u_elem.clear()
            u_elem.send_keys(username)

            p_elem.clear()
            p_elem.send_keys(password)

            otp_code = ""
            if use_otp and secret:
                log("Tùy chọn: Sử dụng mã OTP Google Authenticator...", "info")
                try:
                    driver.execute_script("""
                        if (window.$) {
                            $('#cbOTP').prop('checked', true);
                            if (typeof CheckUseOTP === 'function') CheckUseOTP();
                        }
                    """)
                    if not cb_otp.is_selected():
                        driver.execute_script("arguments[0].click();", cb_otp)
                except Exception:
                    pass
                time.sleep(0.5)

                otp_elem = wait.until(EC.presence_of_element_located((By.ID, "fOTP")))
                totp = pyotp.TOTP(secret.strip().replace(" ", "").upper())
                otp_code = totp.now()
                log(f"Đã tạo mã OTP tự động: {otp_code}", "info")

                otp_elem.clear()
                otp_elem.send_keys(otp_code)
                time.sleep(0.3)
            else:
                log("Tùy chọn: Không sử dụng OTP (bỏ chọn ô OTP)...", "info")
                try:
                    driver.execute_script("""
                        if (window.$) {
                            $('#cbOTP').prop('checked', false);
                            if (typeof CheckUseOTP === 'function') CheckUseOTP();
                        }
                    """)
                except Exception:
                    pass
                if cb_otp.is_selected():
                    try:
                        driver.execute_script("arguments[0].click();", cb_otp)
                    except Exception:
                        pass
                    time.sleep(0.3)

            # Đảm bảo chắc chắn dữ liệu đã vào các trường jQuery và DOM trước khi gửi
            try:
                driver.execute_script("""
                    if (window.$) {
                        $('#fUserName').val(arguments[0]);
                        $('#fPassword').val(arguments[1]);
                        if (arguments[2]) {
                            $('#fOTP').val(arguments[3]);
                        }
                    }
                """, username, password, bool(use_otp and secret), otp_code)
            except Exception:
                pass

            log("Đang gửi yêu cầu xác thực đăng nhập...", "info")
            login_success = False

            # Thực thi trực tiếp qua API xác thực /Login của login.fpt.net để đảm bảo 100% chính xác
            login_result = None
            try:
                login_result = driver.execute_script("""
                    var res = null;
                    try {
                        $.ajax({
                            url: '/Login',
                            type: 'POST',
                            async: false,
                            datatype: 'JSON',
                            data: {
                                UserName: $('#fUserName').val().trim(),
                                Password: $('#fPassword').val(),
                                OTP: $('#fOTP').val(),
                                Token: '',
                                IAM: false,
                                urlReturn: 'http://inside.fpt.net/'
                            },
                            success: function (data) {
                                res = data;
                            },
                            error: function (xhr, s, e) {
                                res = {status: -2, errDescription: (xhr.responseText || e)};
                            }
                        });
                    } catch (ex) {
                        res = {status: -3, errDescription: ex.toString()};
                    }
                    return res;
                """)
            except Exception as e_ajax:
                log(f"Lưu ý gọi API login: {e_ajax}", "warning")

            if login_result and isinstance(login_result, dict):
                log(f"Kết quả xác thực SSO: {login_result}", "info")
                if login_result.get("status") == 1:
                    token = login_result.get("token") or ""
                    target_url = "http://inside.fpt.net/"
                    if token:
                        target_url += f"?Token={token}"
                    log(f"Xác thực thành công! Đang chuyển hướng vào: {target_url}", "success")
                    driver.get(target_url)
                    time.sleep(2)
                    driver.get("http://inside.fpt.net/default.asp")
                    time.sleep(2)
                    login_success = True
                elif login_result.get("status") == -1:
                    err_desc = login_result.get("errDescription", "")
                    if err_desc == "Invalid user credentials":
                        raise ValueError("Thông tin tài khoản, mật khẩu hoặc mã OTP không chính xác!")
                    elif err_desc == "Account is not fully set up":
                        raise ValueError("Tài khoản cần cập nhật mật khẩu mới!")
                    elif err_desc == "Account disabled":
                        raise ValueError("Tài khoản đã bị khóa (disabled)!")
                    else:
                        raise ValueError(f"Đăng nhập thất bại: {err_desc}")

            if not login_success:
                log("Đang nhấn nút [ĐĂNG NHẬP]...", "info")
                # Kích hoạt sự kiện đăng nhập qua jQuery (vì login.fpt.net gắn handler qua $('#btnLogin').click)
                clicked = False
                try:
                    clicked = bool(driver.execute_script("""
                        if (window.$ && $('#btnLogin').length) {
                            $('#btnLogin').click();
                            return true;
                        }
                        return false;
                    """))
                except Exception:
                    pass

                if not clicked:
                    btn_login = None
                    for xpath in [
                        '//*[@id="btnLogin"]//a',
                        '//*[@id="btnLogin"]',
                        '//div[contains(@class,"loginBtn")]',
                        '//button[contains(text(),"ĐĂNG NHẬP")]',
                    ]:
                        try:
                            btn = driver.find_element(By.XPATH, xpath)
                            if btn.is_displayed():
                                btn_login = btn
                                break
                        except Exception:
                            pass

                    if btn_login:
                        try:
                            btn_login.click()
                        except Exception:
                            driver.execute_script("arguments[0].click();", btn_login)
                    else:
                        try:
                            driver.execute_script("$('#btnLogin').click();")
                        except Exception:
                            pass

                # Wait for redirect or alert
                log("Đang chờ phản hồi xác thực và chuyển hướng vào Inside FPT...", "info")
                for _ in range(25):
                    time.sleep(1)
                    try:
                        alert = driver.switch_to.alert
                        alert_text = alert.text
                        alert.accept()
                        raise ValueError(f"Đăng nhập thất bại: {alert_text}")
                    except Exception as e_alert:
                        if "Đăng nhập thất bại" in str(e_alert):
                            raise e_alert

                    curr = (driver.current_url or "").lower()
                    if ("inside.fpt.net" in curr or "default.asp" in curr) and "login.fpt.net" not in curr:
                        login_success = True
                        log("Đăng nhập thành công vào Inside FPT!", "success")
                        break

            if not login_success:
                curr_after = (driver.current_url or "").lower()
                if "login.fpt.net" in curr_after:
                    raise RuntimeError("Hệ thống không chuyển hướng được vào Inside FPT (Sai thông tin đăng nhập hoặc tài khoản bị khóa).")

        # Kiểm tra Frame 1 sau khi đăng nhập xong (chi ap dung cho form cu)
        time.sleep(2)
        try:
            driver.switch_to.default_content()
            driver.switch_to.frame(1)
            f_user = driver.find_elements(By.ID, "fUserName")
            f_pass = driver.find_elements(By.ID, "fPassword")
            if not used_iam_login and f_user and f_pass and f_pass[0].get_attribute("disabled") is None:
                log("Hoàn tất xác thực bổ sung bên trong Frame 1...", "info")
                f_user[0].clear()
                f_user[0].send_keys(username)
                f_pass[0].clear()
                f_pass[0].send_keys(password)

                cb_f1 = driver.find_elements(By.ID, "cbOTP")
                if cb_f1 and not cb_f1[0].is_selected():
                    try:
                        cb_f1[0].click()
                    except Exception:
                        driver.execute_script("arguments[0].click();", cb_f1[0])

                driver.execute_script("""
                    var sp = document.getElementById('spOTP');
                    if (sp) sp.style.display = 'inline-block';
                    var cb = document.getElementById('cbOTP');
                    if (cb) cb.checked = true;
                """)

                f_otp = driver.find_elements(By.ID, "fOTP")
                if f_otp and secret and use_otp:
                    totp2 = pyotp.TOTP(secret.strip().replace(" ", "").upper())
                    f_otp[0].clear()
                    f_otp[0].send_keys(totp2.now())

                btn_f1 = driver.find_elements(
                    By.XPATH,
                    "//a[contains(., 'ĐĂNG NHẬP') and not(contains(., 'IAM'))] | "
                    "//button[contains(., 'ĐĂNG NHẬP') and not(contains(., 'IAM'))] | "
                    "//input[contains(@value, 'ĐĂNG NHẬP')]"
                )
                if btn_f1:
                    driver.execute_script("arguments[0].click();", btn_f1[0])
                    time.sleep(2.5)
        except Exception:
            pass
        finally:
            try:
                driver.switch_to.default_content()
            except Exception:
                pass

        # F5 sau khi đăng nhập để ổn định trang (tránh trạng thái menu bị nhân đôi)
        try:
            log("Làm mới trang sau đăng nhập để ổn định giao diện...", "info")
            driver.switch_to.default_content()
            driver.refresh()
            time.sleep(3)
        except Exception:
            pass

        current_url = driver.current_url
        page_title = driver.title
        log(f"Trang hiện tại: {page_title} ({current_url})", "success")

        if _cfg_keep_inside_session():
            save_inside_cookies(driver, new_login=True)

        if created_driver:
            if keep_open:
                log("Trình duyệt Chrome vẫn được giữ mở để bạn tiếp tục thao tác.", "success")
            else:
                driver.quit()

        return True, current_url, page_title

    except Exception as e:
        log(f"Đã xảy ra lỗi: {e}", "error")
        if created_driver and not keep_open:
            try:
                driver.quit()
            except Exception:
                pass
        raise e

def run_radius_login(username=None, password=None, headless=False, keep_open=True, log_callback=None, driver=None, force=False):
    """
    Quy trình đăng nhập tự động vào Radius Portal (http://radius-portal.fpt.net/login)
    qua IAM và Microsoft Azure AD SSO:
    Bước 1: Truy cập http://radius-portal.fpt.net/login
    Bước 2: Bấm Đăng nhập bằng IAM
    Bước 3: Bấm Azure AD
    Bước 4: Điền email
    Bước 5: Bấm Next
    Bước 6: Điền mật khẩu
    Bước 7: Bấm Next (Sign in)
    Bước 8: Bấm Yes (Stay signed in)
    """
    def log(msg, status="info"):
        if log_callback:
            try:
                log_callback(msg, status)
            except Exception:
                pass
        else:
            try:
                print(f"[{status.upper()}] {msg}")
            except Exception:
                pass

    config = load_config()
    am_acc = get_am_account_info(config)

    # Email mặc định cho Radius Portal (Tài khoản AM: phuongnam.phongnh5@fpt.net)
    username = username or am_acc["username"]
    if "@" not in username:
        username = f"{username}@fpt.net"

    password = password or am_acc["password"]

    created_driver = False
    if driver is None:
        log("Đang khởi tạo trình duyệt Google Chrome cho Radius Portal...", "info")
        p_dir = get_radius_profile_dir()
        try:
            driver = create_driver_with_retry(
                headless=headless,
                profile_dir=p_dir,
                keep_open=keep_open,
                max_retries=2,
                log_cb=log_callback
            )
            created_driver = True
        except Exception as e:
            log(f"Lỗi khởi động Chrome: {e}", "error")
            raise e

    try:
        if force:
            log("Yêu cầu buộc đăng nhập lại từ đầu (force=True), dọn dẹp cookie và storage...", "info")
            try:
                driver.delete_all_cookies()
                driver.execute_script("try { localStorage.clear(); sessionStorage.clear(); } catch(e){}")
            except Exception:
                pass

        log("Bước 1: Điều hướng tới http://radius-portal.fpt.net/login...", "info")
        driver.get("http://radius-portal.fpt.net/login")
        time.sleep(2.5)

        curr_url = (driver.current_url or "").lower()
        if not force and "radius-portal.fpt.net" in curr_url and "login" not in curr_url:
            log(f"Đã đăng nhập sẵn vào Radius Portal! Trang: {driver.current_url}", "success")
            return True, driver.current_url, driver.title

        wait = WebDriverWait(driver, 15)

        # Bước 2: Bấm Đăng nhập bằng IAM
        log("Bước 2: Nhấn nút [Đăng nhập bằng IAM]...", "info")
        btn_iam = wait.until(EC.element_to_be_clickable((
            By.XPATH, "//button[contains(., 'Đăng nhập bằng IAM')] | //a[contains(., 'Đăng nhập bằng IAM')] | //*[contains(text(), 'Đăng nhập bằng IAM')]"
        )))
        driver.execute_script("arguments[0].click();", btn_iam)
        time.sleep(2.5)

        # Bước 3: Nếu đang ở trang IAM, bấm Azure AD
        curr_url = (driver.current_url or "").lower()
        if "iam.fpt.vn" in curr_url:
            log("Bước 3: Nhấn chọn phương thức [Azure AD]...", "info")
            btn_azure = wait.until(EC.element_to_be_clickable((
                By.XPATH, "//a[contains(., 'Azure AD')] | //button[contains(., 'Azure AD')] | //*[@id='zocial-azure-ad'] | //*[contains(text(), 'Azure AD')]"
            )))
            driver.execute_script("arguments[0].click();", btn_azure)
            time.sleep(2.5)

        # Chờ chuyển sang trang Microsoft hoặc đã vào Radius Portal
        try:
            WebDriverWait(driver, 12).until(
                lambda d: "login.microsoftonline.com" in (d.current_url or "").lower() or ("radius-portal.fpt.net" in (d.current_url or "").lower() and "login" not in (d.current_url or "").lower())
            )
        except Exception:
            pass

        # Microsoft Login flow
        curr_url = (driver.current_url or "").lower()
        if "login.microsoftonline.com" in curr_url:
            base_user = username.split("@")[0].lower()
            acc_name = (active_acc.get("account_name") or "").lower()

            # Kiểm tra xem có sẵn tài khoản dạng tile picker để click không
            picker = driver.find_elements(
                By.XPATH,
                f"//div[contains(@data-test-id, '{username}') or contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{base_user}') or contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{username.lower()}') or contains(@data-username, '{username}')]"
            )
            displayed_pickers = [p for p in picker if p.is_displayed()]
            if displayed_pickers:
                log(f"Chọn tài khoản đã lưu: {username}", "info")
                try:
                    displayed_pickers[0].click()
                except Exception:
                    driver.execute_script("arguments[0].click();", displayed_pickers[0])
                time.sleep(2)
            else:
                # Bước 4: Điền email nếu có ô input email
                emails = driver.find_elements(By.XPATH, "//input[@type='email' or @name='loginfmt' or @id='i0116']")
                displayed_emails = [e for e in emails if e.is_displayed()]
                if displayed_emails:
                    log(f"Bước 4: Điền email tài khoản: {username}", "info")
                    target_email = displayed_emails[0]
                    target_email.send_keys(Keys.CONTROL + "a")
                    target_email.send_keys(Keys.BACKSPACE)
                    time.sleep(0.2)
                    target_email.send_keys(username)
                    time.sleep(0.5)

                    log("Bước 5: Nhấn [Next]...", "info")
                    btn_next = wait.until(EC.element_to_be_clickable((
                        By.XPATH, "//input[@type='submit' or @id='idSIButton9' or @value='Next'] | //button[@type='submit' or @id='idSIButton9']"
                    )))
                    driver.execute_script("arguments[0].click();", btn_next)
                    time.sleep(2.5)

            # Chờ một chút để ô mật khẩu hoặc màn hình xác nhận xuất hiện
            pass_elem = None
            for _ in range(12):
                curr = (driver.current_url or "").lower()
                if "radius-portal.fpt.net" in curr and "login" not in curr:
                    break

                inps = driver.find_elements(By.XPATH, "//input[@type='password' or @name='passwd' or @id='i0118']")
                disp_pass = [p for p in inps if p.is_displayed()]
                if disp_pass:
                    pass_elem = disp_pass[0]
                    break

                # Kiểm tra nếu đã chuyển sang màn hình Stay signed in
                btn_yes = driver.find_elements(By.XPATH, "//input[@id='idSIButton9' or @value='Yes'] | //button[@id='idSIButton9' or contains(text(), 'Yes')]")
                if any(b.is_displayed() for b in btn_yes):
                    break

                time.sleep(0.8)

            # Bước 6: Điền mật khẩu nếu có ô nhập
            if pass_elem:
                log("Bước 6: Điền mật khẩu tài khoản mới...", "info")
                pass_elem.send_keys(Keys.CONTROL + "a")
                pass_elem.send_keys(Keys.BACKSPACE)
                time.sleep(0.2)
                pass_elem.send_keys(password)
                time.sleep(0.5)

                log("Bước 7: Nhấn [Next] / [Sign in]...", "info")
                btn_signin = wait.until(EC.element_to_be_clickable((
                    By.XPATH, "//input[@type='submit' or @id='idSIButton9' or @value='Sign in'] | //button[@type='submit' or @id='idSIButton9']"
                )))
                driver.execute_script("arguments[0].click();", btn_signin)
                time.sleep(2.5)

                # Kiểm tra lỗi sai mật khẩu
                err_boxes = driver.find_elements(By.XPATH, "//*[@id='passwordError'] | //*[contains(@class, 'error') and (contains(text(), 'incorrect') or contains(text(), 'không đúng'))]")
                for eb in err_boxes:
                    if eb.is_displayed() and eb.text.strip():
                        log(f"Cảnh báo Microsoft: {eb.text.strip()}", "error")
                        raise RuntimeError(f"Sai mật khẩu hoặc tài khoản Microsoft: {eb.text.strip()}")

            # Bước 8: Bấm YES trên màn hình "Stay signed in?" (Duy trì đăng nhập)
            try:
                btn_yes = WebDriverWait(driver, 8).until(EC.element_to_be_clickable((
                    By.XPATH, "//input[@id='idSIButton9' or @value='Yes'] | //button[@id='idSIButton9' or contains(text(), 'Yes')]"
                )))
                log("Bước 8: Nhấn [YES] để duy trì trạng thái đăng nhập...", "info")
                driver.execute_script("arguments[0].click();", btn_yes)
                time.sleep(3)
            except Exception:
                pass

        # Chờ chuyển hướng vào Radius Portal (nếu có 2FA / Authenticator, cho phép chờ tối đa 45 giây)
        log("Đang chờ chuyển hướng vào trang chủ Radius Portal (tối đa 45s)...", "info")
        WebDriverWait(driver, 45).until(
            lambda d: "radius-portal.fpt.net" in (d.current_url or "").lower() and "login" not in (d.current_url or "").lower()
        )

        final_url = driver.current_url
        final_title = driver.title
        log(f"Đăng nhập thành công vào Radius Portal! ({final_url})", "success")

        if created_driver:
            if keep_open:
                log("Trình duyệt Chrome vẫn được giữ mở để bạn tiếp tục thao tác.", "success")
            else:
                driver.quit()

        return True, final_url, final_title

    except Exception as e:
        log(f"Đã xảy ra lỗi khi đăng nhập Radius: {e}", "error")
        if created_driver and not keep_open:
            try:
                driver.quit()
            except Exception:
                pass
        raise e


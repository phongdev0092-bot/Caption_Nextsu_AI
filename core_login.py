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
    """Lấy đường dẫn thư mục lưu Profile phiên Inside FPT."""
    if sys.platform.startswith("win"):
        profile_base = os.environ.get("LOCALAPPDATA", os.path.expanduser("~"))
    else:
        profile_base = os.path.expanduser("~/.config")
    profile_dir = os.path.join(profile_base, "InsideFPT_SessionProfile")
    os.makedirs(profile_dir, exist_ok=True)
    return profile_dir

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

def close_driver_and_clear_session(driver=None, profile_dir=None, log_cb=None):
    """
    Khi hoàn tất 1 tác vụ: Đóng trình duyệt và xóa sạch toàn bộ session cũ
    để lần sau luôn bắt đầu đăng nhập lại từ đầu.
    """
    if driver is not None:
        try:
            driver.delete_all_cookies()
        except Exception:
            pass
        try:
            driver.quit()
        except Exception:
            pass
    clear_inside_session(profile_dir=profile_dir, log_cb=log_cb)

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

    if sys.platform.startswith("win"):
        try:
            cmd = [
                'powershell', '-NoProfile', '-Command',
                'Get-CimInstance Win32_Process | Select-Object ProcessId, CommandLine | ConvertTo-Csv -NoTypeInformation'
            ]
            res = subprocess.check_output(cmd, text=True, errors='ignore')
            norm_profile = os.path.normpath(profile_dir).lower()
            for line in res.splitlines():
                line_lower = line.lower()
                if ('chromedriver' in line_lower) or ('insidefpt_sessionprofile' in line_lower) or (norm_profile in line_lower):
                    parts = line.split(',')
                    if parts and parts[0].replace('"', '').isdigit():
                        pid = parts[0].replace('"', '')
                        _log(f"Đang giải phóng tiến trình treo PID {pid}...", "warning")
                        subprocess.run(['taskkill', '/F', '/PID', pid], capture_output=True)
        except Exception as e:
            _log(f"Lưu ý khi dọn dẹp tiến trình cũ: {e}", "warning")

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
    options.add_argument('--remote-debugging-port=0')
    options.add_argument('--disable-features=RendererCodeIntegrity,Crashpad')
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

def load_config():
    cfg = {}
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                cfg = json.load(f)
        except Exception:
            cfg = {}

    # Ensure default_account
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

    # Backward compatibility fields at root level
    cfg["username"] = active_data.get("username") or DEFAULT_ACCOUNT["username"]
    cfg["password"] = active_data.get("password") or DEFAULT_ACCOUNT["password"]
    cfg["totp_secret"] = active_data.get("totp_secret", "")
    cfg["use_otp"] = active_data.get("use_otp", True if cfg["active_account"] == "default" else False)
    cfg["account_name"] = active_data.get("account_name", "")

    return cfg

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
        # Xóa sạch cookie trước khi đăng nhập để luôn bắt đầu từ đầu 100%
        try:
            driver.delete_all_cookies()
        except Exception:
            pass

        log(f"Đang điều hướng đến trang xác thực: {login_url}", "info")
        driver.get(login_url)
        time.sleep(2)

        curr_url = (driver.current_url or "").lower()
        if "inside.fpt.net" in curr_url and "login.fpt.net" not in curr_url:
            log("Trình duyệt đã chuyển thẳng vào Inside FPT thành công!", "success")
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

            if use_otp and secret:
                log("Tùy chọn: Sử dụng mã OTP Google Authenticator...", "info")
                try:
                    if not cb_otp.is_selected():
                        cb_otp.click()
                except Exception:
                    driver.execute_script("arguments[0].click();", cb_otp)

                # Ensure spOTP is displayed
                driver.execute_script("""
                    var sp = document.getElementById('spOTP');
                    if (sp) sp.style.display = 'inline-block';
                    var cb = document.getElementById('cbOTP');
                    if (cb) cb.checked = true;
                """)
                time.sleep(0.3)

                otp_elem = wait.until(EC.presence_of_element_located((By.ID, "fOTP")))
                totp = pyotp.TOTP(secret.strip().replace(" ", "").upper())
                otp_code = totp.now()
                log(f"Đã tạo mã OTP tự động: {otp_code}", "info")

                otp_elem.clear()
                otp_elem.send_keys(otp_code)
            else:
                log("Tùy chọn: Không sử dụng OTP (bỏ chọn ô OTP)...", "info")
                if cb_otp.is_selected():
                    try:
                        cb_otp.click()
                    except Exception:
                        driver.execute_script("arguments[0].click();", cb_otp)
                    time.sleep(0.3)

            log("Đang nhấn nút [ĐĂNG NHẬP]...", "info")
            btn_login = wait.until(EC.presence_of_element_located((By.ID, "btnLogin")))
            try:
                btn_login.click()
            except Exception:
                driver.execute_script("arguments[0].click();", btn_login)

            # Wait for redirect or alert
            log("Đang chờ phản hồi xác thực và chuyển hướng vào Inside FPT...", "info")
            try:
                WebDriverWait(driver, 20).until(
                    lambda d: ("inside.fpt.net" in d.current_url.lower() or "default.asp" in d.current_url.lower()) and "login.fpt.net" not in d.current_url.lower()
                )
                log("Đăng nhập thành công vào Inside FPT!", "success")
            except Exception:
                # Check for alert popup if credentials failed
                try:
                    alert = driver.switch_to.alert
                    alert_text = alert.text
                    alert.accept()
                    raise ValueError(f"Đăng nhập thất bại: {alert_text}")
                except Exception as e_alert:
                    if "Đăng nhập thất bại" in str(e_alert):
                        raise e_alert

            curr_after = driver.current_url.lower()
            if "login.fpt.net" in curr_after:
                raise RuntimeError("Hệ thống không chuyển hướng được vào Inside FPT (Sai thông tin đăng nhập hoặc tài khoản bị khóa).")

        # Kiểm tra Frame 1 sau khi đăng nhập xong
        time.sleep(2)
        try:
            driver.switch_to.default_content()
            driver.switch_to.frame(1)
            f_user = driver.find_elements(By.ID, "fUserName")
            f_pass = driver.find_elements(By.ID, "fPassword")
            if f_user and f_pass:
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

        current_url = driver.current_url
        page_title = driver.title
        log(f"Trang hiện tại: {page_title} ({current_url})", "success")

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

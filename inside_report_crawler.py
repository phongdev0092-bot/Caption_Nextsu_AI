"""Crawler UI automation lay bao cao Trien Khai (.xlsx) tu inside.fpt.net.

Tai su dung co che dang nhap + TOTP + cookie cua core_login.py.
"""

from __future__ import annotations

import os
import shutil
import time
import uuid
from pathlib import Path
from typing import Callable, Optional, Tuple

from selenium import webdriver
from selenium.common.exceptions import TimeoutException, WebDriverException
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select, WebDriverWait

import core_login
from auto_import_config import (
    DOWNLOAD_ROOT_DIR,
    DOWNLOAD_TIMEOUT_SECONDS,
    MAX_CRAWL_RETRIES,
    MAX_LOGIN_ATTEMPTS,
    REPORT_LOAD_TIMEOUT_SECONDS,
    _parse_bool,
)


LogFn = Optional[Callable[[str, str], None]]


class SessionExpiredError(RuntimeError):
    """Bao hieu phien Inside da het han (hien khung dang nhap khi mo Bao cao)."""


def _emit_log(log_cb: LogFn, msg: str, level: str = "info") -> None:
    if log_cb:
        try:
            log_cb(msg, level)
            return
        except Exception:
            pass
    print(f"[{level.upper()}] {msg}", flush=True)


def _create_crawler_driver(download_dir: Path, headless: bool = False, log_cb: LogFn = None):
    """Khoi tao Chrome driver voi thu muc download rieng cho tung luot chay."""
    download_dir.mkdir(parents=True, exist_ok=True)
    profile_dir = core_login.get_inside_profile_dir()
    core_login.clean_profile_locks_and_orphans(profile_dir, log_cb=log_cb)

    options, _ = core_login.build_chrome_options(
        headless=headless,
        profile_dir=profile_dir,
        keep_open=False,
    )
    prefs = {
        "download.default_directory": str(download_dir.resolve()),
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "safebrowsing.enabled": True,
    }
    options.add_experimental_option("prefs", prefs)

    driver = webdriver.Chrome(options=options)
    try:
        driver.execute_cdp_cmd(
            "Page.setDownloadBehavior",
            {"behavior": "allow", "downloadPath": str(download_dir.resolve())},
        )
    except Exception:
        pass
    return driver


def _login_inside_with_limit(driver, log_cb: LogFn = None) -> None:
    """Dang nhap Inside co gioi han so lan thu de tranh khoa tai khoan."""
    username = os.environ.get("INSIDE_USERNAME") or None
    password = os.environ.get("INSIDE_PASSWORD") or None
    secret = os.environ.get("INSIDE_TOTP_SECRET") or None
    use_otp_env = os.environ.get("INSIDE_USE_OTP")
    use_otp = _parse_bool(use_otp_env, default=True) if use_otp_env is not None else None

    last_err = None
    for attempt in range(1, MAX_LOGIN_ATTEMPTS + 1):
        try:
            _emit_log(log_cb, f"Dang nhap Inside (lan {attempt}/{MAX_LOGIN_ATTEMPTS})...", "info")
            ok, url, _ = core_login.run_fpt_login(
                username=username,
                password=password,
                secret=secret,
                use_otp=use_otp,
                headless=False,
                keep_open=True,
                use_custom_profile=True,
                log_callback=log_cb,
                driver=driver,
            )
            if ok and "login.fpt.net" not in (url or "").lower():
                return
            last_err = RuntimeError("Dang nhap Inside khong thanh cong.")
        except Exception as exc:
            last_err = exc
            _emit_log(log_cb, f"Loi dang nhap Inside lan {attempt}: {exc}", "warning")
    raise RuntimeError(f"Vuot qua gioi han dang nhap ({MAX_LOGIN_ATTEMPTS} lan): {last_err}")


def _switch_to_frame_containing(driver, xpath: str, timeout: int = 20):
    """Tim element theo xpath o top-level hoac ben trong cac iframe/frame."""
    end_time = time.time() + timeout
    while time.time() < end_time:
        driver.switch_to.default_content()
        els = driver.find_elements(By.XPATH, xpath)
        visible = [e for e in els if e.is_displayed()]
        if visible:
            return visible[0]
        frames = driver.find_elements(By.CSS_SELECTOR, "iframe, frame")
        for idx in range(len(frames)):
            try:
                driver.switch_to.default_content()
                driver.switch_to.frame(idx)
                els = driver.find_elements(By.XPATH, xpath)
                visible = [e for e in els if e.is_displayed()]
                if visible:
                    return visible[0]
                nested = driver.find_elements(By.CSS_SELECTOR, "iframe, frame")
                for n_idx in range(len(nested)):
                    try:
                        driver.switch_to.frame(n_idx)
                        els_n = driver.find_elements(By.XPATH, xpath)
                        vis_n = [e for e in els_n if e.is_displayed()]
                        if vis_n:
                            return vis_n[0]
                    finally:
                        driver.switch_to.parent_frame()
            except Exception:
                continue
        time.sleep(0.5)
    driver.switch_to.default_content()
    raise TimeoutException(f"Khong tim thay element: {xpath}")


def _click_element_safe(driver, element) -> None:
    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
    time.sleep(0.2)
    try:
        element.click()
    except Exception:
        driver.execute_script("arguments[0].click();", element)


def _is_login_screen_present(driver) -> bool:
    """Kiem tra xem top-level hoac frame(1)/iframe con co dang hien form dang nhap hay khong."""
    login_xpath = (
        "//*[contains(normalize-space(.), 'Mời bạn điền thông tin để đăng nhập')] | "
        "//input[@type='password' and (preceding::*[contains(., 'Tên đăng nhập')] or following::*[contains(., 'ĐĂNG NHẬP')])]"
    )
    try:
        driver.switch_to.default_content()
        if "login.fpt.net" in (driver.current_url or "").lower():
            return True
        if any(e.is_displayed() for e in driver.find_elements(By.XPATH, login_xpath)):
            return True
        frames = driver.find_elements(By.CSS_SELECTOR, "iframe, frame")
        for idx in range(len(frames)):
            try:
                driver.switch_to.default_content()
                driver.switch_to.frame(idx)
                if any(e.is_displayed() for e in driver.find_elements(By.XPATH, login_xpath)):
                    return True
            except Exception:
                continue
    except Exception:
        pass
    finally:
        try:
            driver.switch_to.default_content()
        except Exception:
            pass
    return False


def _navigate_to_inside_v5_report(driver, log_cb: LogFn = None) -> None:
    """Buoc 2: Mo Inside New V5 >> Ho tro ky thuat >> Bao cao (theo dung DOM cua inside_cls.py)."""
    _emit_log(log_cb, "Mo menu Inside New V5 >> Ho tro ky thuat >> Bao cao...", "info")
    if "default.asp" not in (driver.current_url or "").lower():
        driver.get("http://inside.fpt.net/default.asp")
        time.sleep(2.0)

    driver.switch_to.default_content()
    wait = WebDriverWait(driver, 25)
    try:
        wait.until(EC.frame_to_be_available_and_switch_to_it(0))
    except Exception:
        driver.get("http://inside.fpt.net/default.asp")
        time.sleep(2.5)
        driver.switch_to.default_content()
        wait.until(EC.frame_to_be_available_and_switch_to_it(0))

    time.sleep(1.0)

    # 1. Tim va mo rong 'Inside New V5' neu dang dong (hinh plus.gif nam ben trong <a>)
    v5_nodes = driver.find_elements(By.XPATH, "//a[@data-english-name='Inside New V5']")
    if not v5_nodes:
        v5_nodes = driver.find_elements(By.XPATH, "//a[contains(., 'Inside New V5')]")
    if not v5_nodes:
        raise RuntimeError("Khong tim thay muc 'Inside New V5' tren menu trai!")

    v5_elem = v5_nodes[0]
    v5_img = v5_elem.find_elements(By.XPATH, ".//img")
    if v5_img and "plus.gif" in (v5_img[0].get_attribute("src") or "").lower():
        _emit_log(log_cb, "Dang mo rong muc 'Inside New V5'...", "info")
        driver.execute_script("arguments[0].scrollIntoView(true);", v5_elem)
        driver.execute_script("arguments[0].click();", v5_elem)
        time.sleep(1.0)

    # 2. Mo rong 'Hỗ trợ kỹ thuật' ben trong Inside New V5 neu dang dong
    v5_li = v5_elem.find_element(By.XPATH, "./ancestor::li[1]")
    ho_tro = None
    try:
        ho_tro = v5_li.find_element(By.XPATH, ".//a[@data-english-name='Ho tro ky thuat']")
    except Exception:
        ht_list = v5_li.find_elements(By.XPATH, ".//a[contains(., 'Hỗ trợ kỹ thuật')]")
        ho_tro = ht_list[0] if ht_list else None

    if ho_tro is not None:
        ht_img = ho_tro.find_elements(By.XPATH, ".//img")
        if ht_img and "plus.gif" in (ht_img[0].get_attribute("src") or "").lower():
            _emit_log(log_cb, "Dang mo rong muc 'Ho tro ky thuat' (Inside New V5)...", "info")
            driver.execute_script("arguments[0].scrollIntoView(true);", ho_tro)
            driver.execute_script("arguments[0].click();", ho_tro)
            time.sleep(1.0)

    # 3. Bam chon 'Báo cáo' ben trong Inside New V5
    bao_cao_elem = None
    for xp in (
        ".//a[@data-english-name='Bao cao']",
        ".//a[normalize-space(.)='Báo cáo']",
        ".//a[contains(., 'Báo cáo')]",
    ):
        found = v5_li.find_elements(By.XPATH, xp)
        if found:
            bao_cao_elem = found[0]
            break

    if bao_cao_elem is None:
        raise RuntimeError("Khong tim thay muc 'Báo cáo' ben trong 'Inside New V5'!")

    _emit_log(log_cb, "Dang bam mo trang 'Bao cao'...", "info")
    driver.execute_script("arguments[0].scrollIntoView(true);", bao_cao_elem)
    driver.execute_script("arguments[0].click();", bao_cao_elem)
    time.sleep(2.5)

    # Cho Man hinh bao cao, neu phat hien form dang nhap thi bao SessionExpiredError ngay
    end_wait = time.time() + 30
    while time.time() < end_wait:
        if _is_login_screen_present(driver):
            raise SessionExpiredError(
                "Hien man hinh dang nhap khi mo Bao cao -> can xoa session va dang nhap lai."
            )
        try:
            _switch_to_frame_containing(
                driver,
                "//*[contains(normalize-space(.), 'Màn hình báo cáo')]",
                timeout=3,
            )
            return
        except TimeoutException:
            time.sleep(0.5)

    raise TimeoutException("Khong tim thay 'Màn hình báo cáo' sau khi bam Bao cao.")


def _select_dropdown_near_label(driver, label_text: str, value_text: str) -> None:
    """Chon gia tri trong <select> hoac custom dropdown canh nhan label_text."""
    if not value_text:
        return

    # Uu tien tim <select> lien quan trong cung container
    select_xpath = (
        f"//*[normalize-space(.)='{label_text}' or contains(normalize-space(.), '{label_text}')]"
        f"/following::select[1]"
    )
    select_els = [e for e in driver.find_elements(By.XPATH, select_xpath) if e.is_displayed()]
    if select_els:
        sel = Select(select_els[0])
        current = sel.first_selected_option.text.strip() if sel.options else ""
        if current == value_text or value_text in current:
            return
        for opt in sel.options:
            if opt.text.strip() == value_text:
                sel.select_by_visible_text(opt.text)
                time.sleep(0.3)
                return
        for opt in sel.options:
            if value_text.lower() in opt.text.strip().lower():
                sel.select_by_visible_text(opt.text)
                time.sleep(0.3)
                return
        raise RuntimeError(f"Khong tim thay gia tri '{value_text}' trong dropdown '{label_text}'.")

    # Fallback cho custom dropdown (click mo danh sach va chon option)
    trigger_xpath = (
        f"//*[normalize-space(.)='{label_text}' or contains(normalize-space(.), '{label_text}')]"
        f"/following::*[self::button or self::div or self::span][@role='combobox' or contains(@class,'select') or contains(@class,'dropdown')][1]"
    )
    triggers = [e for e in driver.find_elements(By.XPATH, trigger_xpath) if e.is_displayed()]
    if not triggers:
        raise RuntimeError(f"Khong tim thay dropdown cho nhan '{label_text}'.")
    _click_element_safe(driver, triggers[0])
    time.sleep(0.4)
    opt_xpath = (
        f"//li[contains(normalize-space(.), '{value_text}')] | "
        f"//div[@role='option' and contains(normalize-space(.), '{value_text}')] | "
        f"//span[normalize-space(.)='{value_text}']"
    )
    opts = [e for e in driver.find_elements(By.XPATH, opt_xpath) if e.is_displayed()]
    if not opts:
        raise RuntimeError(f"Khong tim thay option '{value_text}' trong dropdown '{label_text}'.")
    _click_element_safe(driver, opts[0])
    time.sleep(0.3)


def _fill_date_range(driver, from_date: str, to_date: str) -> None:
    """Buoc 5: Dien khoang ngay Tu ngay - Den ngay (dd/mm/YYYY)."""
    inputs = [
        e
        for e in driver.find_elements(
            By.XPATH,
            "//*[contains(normalize-space(.), 'Từ ngày')]/following::input[not(@type='hidden')]",
        )
        if e.is_displayed()
    ]
    if not inputs:
        raise RuntimeError("Khong tim thay o nhap 'Từ ngày'.")

    first_val = (inputs[0].get_attribute("value") or "").strip()
    # Truong hop 1 o gop 'dd/mm/YYYY - dd/mm/YYYY'
    if " - " in first_val or (len(inputs) >= 1 and len(first_val) > 12):
        target_str = f"{from_date} - {to_date}"
        inputs[0].click()
        inputs[0].send_keys(Keys.CONTROL, "a")
        inputs[0].send_keys(target_str)
        inputs[0].send_keys(Keys.TAB)
        time.sleep(0.3)
        return

    # Truong hop 2 o rieng (Tu ngay, Den ngay)
    inputs[0].click()
    inputs[0].send_keys(Keys.CONTROL, "a")
    inputs[0].send_keys(from_date)
    inputs[0].send_keys(Keys.TAB)
    if len(inputs) >= 2:
        inputs[1].click()
        inputs[1].send_keys(Keys.CONTROL, "a")
        inputs[1].send_keys(to_date)
        inputs[1].send_keys(Keys.TAB)
    time.sleep(0.3)


def _wait_download_complete(download_dir: Path, timeout: int = DOWNLOAD_TIMEOUT_SECONDS) -> Path:
    """Cho file .xlsx tai xong hoan toan trong download_dir."""
    end_time = time.time() + timeout
    last_size = -1
    stable_ticks = 0

    while time.time() < end_time:
        files = list(download_dir.iterdir())
        in_progress = [
            f for f in files if f.name.endswith((".crdownload", ".tmp", ".part"))
        ]
        xlsx_files = [
            f for f in files if f.is_file() and f.suffix.lower() == ".xlsx"
        ]
        if xlsx_files and not in_progress:
            candidate = max(xlsx_files, key=lambda p: p.stat().st_mtime)
            size = candidate.stat().st_size
            if size > 0 and size == last_size:
                stable_ticks += 1
                if stable_ticks >= 2:
                    return candidate
            else:
                stable_ticks = 0
                last_size = size
        time.sleep(0.8)

    raise TimeoutException(f"Qua thoi gian cho tai file Excel ({timeout}s) tai {download_dir}")


def validate_downloaded_tk_excel(file_bytes: bytes, filename: str) -> Tuple[bool, str]:
    """Kiem tra toan ven file .xlsx tai ve truoc khi giao cho pipeline import."""
    if not filename or not filename.lower().endswith(".xlsx"):
        return False, f"Dinh dang file khong hop le: '{filename}' (yeu cau .xlsx)."
    if not file_bytes or len(file_bytes) < 100:
        return False, f"Dung luong file qua nho hoac rong ({len(file_bytes or b'')} bytes)."

    # Kiem tra nhanh tranh nhan nham trang HTML login / trang loi
    head_lower = file_bytes[:512].lstrip().lower()
    if head_lower.startswith((b"<html", b"<!doctype", b"<head", b"<script")):
        return False, "File tai ve la trang HTML (co the het phien login hoac trang loi), khong phai .xlsx."
    if not file_bytes.startswith(b"PK\x03\x04"):
        return False, "File khong co chu ky ZIP/XLSX hop le (PK\\x03\\x04)."

    return True, "OK"


def fetch_tk_report_excel(
    from_date: str,
    to_date: str,
    partner: str,
    filters: dict,
    headless: bool = False,
    log_cb: LogFn = None,
) -> Tuple[bytes, str]:
    """Thuc hien Buoc 1-9 tren UI Inside de lay file .xlsx Bao cao dung hen (Trien Khai)."""
    last_error = None
    relogin_used = 0
    total_budget = MAX_CRAWL_RETRIES + MAX_LOGIN_ATTEMPTS + 1
    for attempt in range(1, total_budget + 1):
        run_dir = DOWNLOAD_ROOT_DIR / f"run_{uuid.uuid4().hex[:8]}"
        driver = None
        session_expired = False
        try:
            _emit_log(
                log_cb,
                f"[Lan {attempt}] Khoi dong trinh duyet lay bao cao TK ({from_date} -> {to_date}, Doi tac={partner})...",
                "info",
            )
            driver = _create_crawler_driver(run_dir, headless=headless, log_cb=log_cb)

            # Buoc 1: Dang nhap Inside
            _login_inside_with_limit(driver, log_cb=log_cb)

            # Buoc 2: Inside New V5 >> Ho tro ky thuat >> Bao cao
            _navigate_to_inside_v5_report(driver, log_cb=log_cb)

            # Buoc 3: Chon bo loc top (Vung mien, Tinh thanh, Doi tac)
            _select_dropdown_near_label(driver, "Vùng miền", filters.get("vung_mien", ""))
            _select_dropdown_near_label(driver, "Tỉnh thành", filters.get("tinh_thanh", ""))
            _select_dropdown_near_label(driver, "Đối tác", partner)

            # Buoc 4: Chon tab TRIỂN KHAI
            tab_tk = _switch_to_frame_containing(
                driver,
                "//*[self::a or self::li or self::button or self::span][normalize-space(.)='TRIỂN KHAI']",
                timeout=15,
            )
            _click_element_safe(driver, tab_tk)
            time.sleep(0.8)

            # Buoc 5 & 6: Nhap ngay & chon Loai bao cao = Bao cao dung hen - dung han
            _fill_date_range(driver, from_date, to_date)
            _select_dropdown_near_label(driver, "Xem theo", filters.get("xem_theo", ""))
            _select_dropdown_near_label(driver, "Loại báo cáo", filters.get("loai_bao_cao", ""))
            _select_dropdown_near_label(
                driver, "Thuộc tính nhân viên", filters.get("thuoc_tinh_nhan_vien", "")
            )
            _select_dropdown_near_label(driver, "Báo cáo theo", filters.get("bao_cao_theo", ""))

            # Buoc 7: Bam Xem Bao Cao
            btn_xem = _switch_to_frame_containing(
                driver,
                "//button[contains(normalize-space(.), 'Xem Báo Cáo')] | //input[@value='Xem Báo Cáo']",
                timeout=15,
            )
            _click_element_safe(driver, btn_xem)

            # Buoc 8: Cho bang tong hop va bam vao so o cot Tong (dong dau tien / dong khu vuc)
            _emit_log(log_cb, "Dang cho bao cao tong hop tai xong...", "info")
            total_cell_xpath = (
                "//table[.//th[normalize-space(.)='Tổng']]//tbody/tr[1]"
                "//a[string-length(normalize-space(.)) > 0][last()]"
            )
            # Tim cot co chi so tuong ung voi header 'Tổng' de bam chinh xac
            WebDriverWait(driver, REPORT_LOAD_TIMEOUT_SECONDS).until(
                lambda d: len(
                    d.find_elements(By.XPATH, "//table[.//th[normalize-space(.)='Tổng']]//tbody/tr")
                )
                > 0
            )
            total_links = driver.find_elements(
                By.XPATH,
                "//table[.//th[normalize-space(.)='Tổng']]//tbody/tr[1]//a",
            )
            if total_links:
                # Bam link o cot Tong (neu co nhieu link, thu link co vi tri cot Tong hoac link gan cuoi)
                tong_col_idx = driver.execute_script(
                    """
                    const ths = Array.from(document.querySelectorAll('table th'));
                    const target = ths.find(th => th.innerText.trim() === 'Tổng');
                    if (!target) return -1;
                    return Array.from(target.parentElement.children).indexOf(target);
                    """
                )
                target_link = None
                if isinstance(tong_col_idx, int) and tong_col_idx >= 0:
                    row_tds = driver.find_elements(
                        By.XPATH,
                        "//table[.//th[normalize-space(.)='Tổng']]//tbody/tr[1]/td",
                    )
                    if tong_col_idx < len(row_tds):
                        anchors = row_tds[tong_col_idx].find_elements(By.TAG_NAME, "a")
                        if anchors:
                            target_link = anchors[0]
                if target_link is None:
                    target_link = total_links[-1]
                _click_element_safe(driver, target_link)
            else:
                cell = _switch_to_frame_containing(driver, total_cell_xpath, timeout=15)
                _click_element_safe(driver, cell)

            # Cho tab Chi tiet ('Bao cao dung hen : Danh sach chi tiet') load xong
            _emit_log(log_cb, "Dang cho danh sach chi tiet tai xong...", "info")
            _switch_to_frame_containing(
                driver,
                "//*[contains(normalize-space(.), 'Danh sách chi tiết')]",
                timeout=REPORT_LOAD_TIMEOUT_SECONDS,
            )
            WebDriverWait(driver, REPORT_LOAD_TIMEOUT_SECONDS).until(
                lambda d: len(
                    d.find_elements(
                        By.XPATH,
                        "//*[contains(normalize-space(.), 'Danh sách chi tiết')]/following::table[1]//tbody/tr",
                    )
                )
                > 0
            )

            # Xoa file cu trong run_dir truoc khi bam Xuat Excel
            for old_f in run_dir.iterdir():
                if old_f.is_file():
                    old_f.unlink(missing_ok=True)

            # Buoc 9: Bam Xuat Excel ben trong khu vuc Chi tiet
            btn_export = _switch_to_frame_containing(
                driver,
                "//*[contains(normalize-space(.), 'Danh sách chi tiết')]"
                "/following::*[self::button or self::a][contains(normalize-space(.), 'Xuất Excel')][1]",
                timeout=20,
            )
            _click_element_safe(driver, btn_export)
            _emit_log(log_cb, "Da bam Xuat Excel, dang cho tai file .xlsx...", "info")

            downloaded_path = _wait_download_complete(run_dir, timeout=DOWNLOAD_TIMEOUT_SECONDS)
            file_bytes = downloaded_path.read_bytes()
            filename = downloaded_path.name

            ok_valid, valid_msg = validate_downloaded_tk_excel(file_bytes, filename)
            if not ok_valid:
                raise RuntimeError(f"Kiem tra toan ven file that bai: {valid_msg}")

            _emit_log(
                log_cb,
                f"Tai thanh cong '{filename}' ({len(file_bytes):,} bytes).",
                "success",
            )
            return file_bytes, filename

        except SessionExpiredError as exc:
            session_expired = True
            last_error = exc
            relogin_used += 1
            _emit_log(
                log_cb,
                f"Phat hien dinh session cu khi mo Bao cao ({exc}). Xoa session & dang nhap lai ({relogin_used}/{MAX_LOGIN_ATTEMPTS})...",
                "warning",
            )
            if driver is not None:
                try:
                    driver.quit()
                except Exception:
                    pass
                driver = None
            core_login.invalidate_session(log_cb=log_cb)
            if relogin_used >= MAX_LOGIN_ATTEMPTS:
                break
            time.sleep(1.5)
        except (TimeoutException, WebDriverException, RuntimeError) as exc:
            last_error = exc
            _emit_log(log_cb, f"Crawler that bai o lan {attempt}: {exc}", "error")
            if attempt >= MAX_CRAWL_RETRIES + 1:
                break
            time.sleep(2.0)
        finally:
            if driver is not None:
                if not session_expired:
                    try:
                        core_login.save_inside_cookies(driver, new_login=False, log_cb=log_cb)
                    except Exception:
                        pass
                try:
                    driver.quit()
                except Exception:
                    pass
            shutil.rmtree(run_dir, ignore_errors=True)

    raise RuntimeError(f"Khong the lay bao cao TK tu Inside: {last_error}")

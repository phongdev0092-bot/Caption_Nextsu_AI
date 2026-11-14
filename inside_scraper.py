import os
import sys
import time
import re
from datetime import datetime
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import pyotp
import core_login

def extract_ptc_fields(html, contract_no):
    soup = BeautifulSoup(html, 'html.parser')
    text_content = soup.get_text('\n', strip=True)

    data = {
        'contract_no': contract_no,
        'customer_name': '',
        'customer_phone': '',
        'service_type': '',
        'contract_status': '',
        'address': '',
        'service_package': '',
        'materials': '',
        'deploy_type': '',
        'sales': '',
        'tech_params': '',
        'created_date': '',
        'status': 'Thành công',
        'error': ''
    }

    # 1. Customer Info
    m_name = re.search(r'Họ\s*tên\s*khách\s*hàng[:\s]+([^\n\|]+)', text_content, re.IGNORECASE)
    if m_name:
        val = m_name.group(1).strip()
        val = re.split(r'Đối tượng|Cá nhân|Doanh nghiệp', val)[0].strip()
        data['customer_name'] = val

    m_phone = re.search(r'SĐT\s*chính\s*chủ[:\s]+([0-9\s]+)', text_content, re.IGNORECASE)
    if m_phone:
        data['customer_phone'] = m_phone.group(1).strip()

    m_stype = re.search(r'Loại\s*dịch\s*vụ[:\s]+([^\n\|]+)', text_content, re.IGNORECASE)
    if m_stype:
        data['service_type'] = m_stype.group(1).strip()

    m_hstatus = re.search(r'Tình\s*trạng\s*HĐ[:\s]+([^\n\|]+)', text_content, re.IGNORECASE)
    if m_hstatus:
        data['contract_status'] = m_hstatus.group(1).strip()

    # 2. PTC Info - Address
    for d in soup.find_all(['div', 'p', 'span']):
        t = d.get_text(' ', strip=True)
        if t.startswith('Địa chỉ:') and 'sát nhập' not in t and len(t) < 180:
            val = t.replace('Địa chỉ:', '').strip()
            if val and not data['address']:
                data['address'] = val
                break

    m_tech = re.search(r'Thông\s*số\s*thi\s*công[:\s]+([^\n\|]+)', text_content, re.IGNORECASE)
    if m_tech:
        data['tech_params'] = m_tech.group(1).strip()

    # Parse Table 0 for services, materials, deploy_type, sales
    for table in soup.find_all('table'):
        for row in table.find_all('tr'):
            cells = [td.get_text(' | ', strip=True) for td in row.find_all('td')]
            if len(cells) >= 7 and any('internet' in c.lower() or 'gói' in c.lower() for c in cells):
                # Usually: [0]=Loại DV, [1]=Gói DV, [2]=Vật tư, [3]=Loại TK, [4]=Loại GD, [5]=Ngày tạo, [6]=Account Tạo
                data['service_package'] = cells[1]
                data['materials'] = cells[2]
                data['deploy_type'] = cells[3]
                if not data['created_date']:
                    data['created_date'] = cells[5]
                if not data['sales']:
                    data['sales'] = cells[6]
                break
        if data['service_package']:
            break

    # Extract all created dates from PTC cards to pick the one closest to today if needed
    ptc_dates = []
    for m in re.finditer(r'Ngày tạo[:\s]+([0-9]{2}/[0-9]{2}/[0-9]{4}\s+[0-9]{2}:[0-9]{2}:[0-9]{2})', text_content):
        dt_str = m.group(1)
        try:
            dt = datetime.strptime(dt_str, '%d/%m/%Y %H:%M:%S')
            ptc_dates.append((dt, dt_str))
        except Exception:
            pass

    if ptc_dates:
        now = datetime.now()
        ptc_dates.sort(key=lambda x: abs((now - x[0]).total_seconds()))
        data['created_date'] = ptc_dates[0][1]

    m_sales = re.search(r'Sales[:\s]+([a-zA-Z0-9\._]+)', text_content, re.IGNORECASE)
    if m_sales and not data['sales']:
        data['sales'] = m_sales.group(1).strip()

    # Validation: If empty, report No data
    if not data['customer_name'] and not data['service_package'] and not data['address']:
        data['status'] = 'Lỗi'
        data['error'] = 'No data'

    return data

def _default_logger(msg, level="info"):
    try:
        print(f"[{level.upper()}] {msg}")
    except Exception:
        try:
            print(f"[{level.upper()}] {msg}".encode("ascii", errors="replace").decode("ascii"))
        except Exception:
            pass

class InsideScraper:
    def __init__(self, headless=True, log_cb=None):
        self.headless = headless
        self.log_cb = log_cb or _default_logger
        self.driver = None

    def log(self, msg, level="info"):
        try:
            self.log_cb(msg, level)
        except Exception:
            try:
                self.log_cb(msg.encode("ascii", errors="replace").decode("ascii"), level)
            except Exception:
                pass

    def init_driver(self):
        self.log("Khởi tạo trình duyệt Chrome...", "info")
        self.driver = core_login.create_driver_with_retry(
            headless=self.headless,
            keep_open=False,
            max_retries=2,
            log_cb=self.log_cb
        )
        return self.driver

    def check_session_alive(self):
        """Kiểm tra xem phiên làm việc hiện tại có còn đăng nhập và truy cập được Inside FPT không."""
        if not self.driver:
            return False, "Trình duyệt chưa khởi động"
        try:
            self.driver.switch_to.default_content()
            curr_url = self.driver.current_url.lower()
            if "login.fpt.net" in curr_url or "iam.fpt." in curr_url or "login.microsoftonline.com" in curr_url:
                return False, "Phiên đã hết hạn (chuyển hướng về cổng đăng nhập)"
            if "inside.fpt.net" in curr_url or "partner.fpt.net" in curr_url:
                # Kiểm tra xem có form đăng nhập fUserName hoặc nút IAM hay không
                if len(self.driver.find_elements(By.ID, "fUserName")) > 0 or core_login._should_use_iam_login(self.driver):
                    return False, "Phiên chưa đăng nhập (hiển thị form login)"
                return True, "Phiên đăng nhập đang khả dụng"
            
            # Thử điều hướng đến default.asp để kiểm tra
            self.driver.get("http://inside.fpt.net/default.asp")
            time.sleep(1.5)
            curr_after = self.driver.current_url.lower()
            if "login.fpt.net" in curr_after or "iam.fpt." in curr_after or "login.microsoftonline.com" in curr_after or core_login._should_use_iam_login(self.driver):
                return False, "Phiên đã hết hạn (chuyển hướng về cổng đăng nhập)"
            return True, "Phiên đăng nhập đang khả dụng"
        except Exception as e:
            return False, f"Lỗi kiểm tra phiên: {e}"

    def check_and_ensure_logged_in(self):
        """Đảm bảo trình duyệt đã đăng nhập thành công vào Inside FPT, nếu chưa hoặc hết hạn thì tự động đăng nhập lại."""
        is_alive, msg = self.check_session_alive()
        if not is_alive:
            self.log(f"Kiểm tra phiên: {msg}. Tiến hành đăng nhập tự động với OTP...", "warning")
            self.login_inside()
        else:
            self.log(f"Kiểm tra phiên: {msg}", "success")

    def is_driver_healthy(self):
        """Kiểm tra kết nối tới driver còn sống hay đã bị crash/đóng."""
        if not self.driver:
            return False
        try:
            _ = self.driver.current_url
            _ = self.driver.window_handles
            return True
        except Exception:
            return False

    def is_kicked_to_login(self):
        """Kiểm tra xem tài khoản có bị văng ra cổng đăng nhập do thiết bị khác đăng nhập hay không."""
        if not self.is_driver_healthy():
            return True
        try:
            self.driver.switch_to.default_content()
            curr = self.driver.current_url.lower()
            if "login.fpt.net" in curr or "iam.fpt." in curr or "login.microsoftonline.com" in curr:
                return True
            if len(self.driver.find_elements(By.ID, "fUserName")) > 0 or core_login._should_use_iam_login(self.driver):
                return True
            return False
        except Exception:
            return True

    def reset_and_relogin(self, reason="Phiên bị văng hoặc tab trình duyệt bị đóng"):
        """Tự động đóng Chrome cũ, khởi động lại trình duyệt sạch sẽ và đăng nhập lại vào Inside FPT."""
        self.log(f"🔄 CẢNH BÁO: {reason}! Đang tự động reset trình duyệt và đăng nhập lại Inside FPT...", "warning")
        try:
            if self.driver:
                self.driver.quit()
        except Exception:
            pass
        self.driver = None
        time.sleep(2)

        for attempt in range(1, 4):
            try:
                self.log(f"Đang khởi động lại trình duyệt và đăng nhập lại (lần {attempt}/3)...", "info")
                self.init_driver()
                self.login_inside()
                self.navigate_to_deployment_search()
                self.log("✅ Đã reset trình duyệt, đăng nhập lại và khôi phục giao diện tra cứu thành công!", "success")
                return True
            except Exception as ex:
                self.log(f"Thử đăng nhập lại lần {attempt} thất bại: {ex}", "warning")
                try:
                    if self.driver:
                        self.driver.quit()
                except Exception:
                    pass
                self.driver = None
                time.sleep(3)

        self.log("❌ Không thể khôi phục phiên trình duyệt sau 3 lần thử.", "error")
        return False

    def login_inside(self):
        """Đăng nhập Inside qua core_login.run_fpt_login (hỗ trợ đầy đủ IAM / Azure AD / AM)."""
        cfg = core_login.load_config()
        acc = core_login.get_active_account_info(cfg)
        self.log("Đang đăng nhập Inside FPT qua SSO / IAM...", "info")
        core_login.run_fpt_login(
            driver=self.driver,
            username=acc["username"],
            password=acc["password"],
            secret=acc.get("totp_secret", ""),
            use_otp=acc.get("use_otp", False),
            log_callback=self.log_cb,
        )
        self.driver.switch_to.default_content()
        self.log("Đăng nhập thành công vào Inside FPT!", "success")

    def navigate_to_deployment_search(self):
        self.log("Đang mở menu: Inside New V5 -> Thông tin chung...", "info")
        self.check_and_ensure_logged_in()

        # Ensure we are on default.asp
        if "default.asp" not in self.driver.current_url.lower():
            self.driver.get("http://inside.fpt.net/default.asp")
            time.sleep(2)

        self.driver.switch_to.default_content()
        wait = WebDriverWait(self.driver, 25)

        # Switch to left frame (0)
        try:
            wait.until(EC.frame_to_be_available_and_switch_to_it(0))
        except Exception:
            self.log("Tải lại trang default.asp để định vị lại Frame Menu...", "warning")
            self.driver.get("http://inside.fpt.net/default.asp")
            time.sleep(3)
            self.driver.switch_to.default_content()
            wait.until(EC.frame_to_be_available_and_switch_to_it(0))

        # Click Thông tin chung directly via javascript
        tt_elem = wait.until(EC.presence_of_element_located((
            By.XPATH,
            "//a[@data-english-name='Thong tin chung' or contains(@onclick, 'par-transition') or contains(text(), 'Thông tin chung')]"
        )))
        self.driver.execute_script("arguments[0].click();", tt_elem)
        time.sleep(3)

        # Switch to Content Frame (1) and frameDeployment
        self.driver.switch_to.default_content()
        wait_content = WebDriverWait(self.driver, 25)
        wait_content.until(EC.frame_to_be_available_and_switch_to_it(1))
        time.sleep(1.5)

        # Switch into frameDeployment
        iframe = wait_content.until(EC.presence_of_element_located((By.ID, 'frameDeployment')))
        self.driver.switch_to.frame(iframe)
        time.sleep(1.5)

        # Wait until search box is ready
        wait_inner = WebDriverWait(self.driver, 20)
        wait_inner.until(EC.presence_of_element_located((By.XPATH, "//*[contains(text(), 'Điều kiện nhập')]")))
        self.log("Đã vào giao diện tìm kiếm Phiếu Thi Công thành công!", "success")

    def ensure_frame_deployment(self):
        """Đảm bảo scraper đang nằm trong iframe tìm kiếm phiếu thi công; nếu mất context thì tự động khôi phục."""
        try:
            if len(self.driver.find_elements(By.XPATH, "//*[contains(text(), 'Điều kiện nhập')]")) > 0:
                return True
        except Exception:
            pass

        try:
            self.driver.switch_to.default_content()
            self.driver.switch_to.frame(1)
            iframe = self.driver.find_element(By.ID, 'frameDeployment')
            self.driver.switch_to.frame(iframe)
            if len(self.driver.find_elements(By.XPATH, "//*[contains(text(), 'Điều kiện nhập')]")) > 0:
                return True
        except Exception:
            pass

        self.log("Khôi phục kết nối đến giao diện tìm kiếm...", "info")
        self.navigate_to_deployment_search()
        return True

    def _execute_fetch_contract(self, contract_no):
        """Thực thi chi tiết việc tìm kiếm và bóc tách dữ liệu một hợp đồng."""
        self.ensure_frame_deployment()

        # Find input box
        dkn_elem = self.driver.find_element(By.XPATH, "//*[contains(text(), 'Điều kiện nhập')]")
        input_box = dkn_elem.find_element(By.XPATH, "./following::input[1]")
        self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", input_box)
        self.driver.execute_script("arguments[0].focus();", input_box)

        # Clear and enter
        input_box.send_keys(Keys.CONTROL + "a")
        input_box.send_keys(Keys.BACKSPACE)
        input_box.send_keys(contract_no)
        time.sleep(0.5)
        input_box.send_keys(Keys.ENTER)
        time.sleep(0.5)

        # Find Phiếu thi công button
        ptc_btn = self.driver.find_element(By.XPATH, "//button[.//p[contains(text(), 'Phiếu thi công')] or contains(., 'Phiếu thi công')]")
        self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", ptc_btn)

        parent_handles = list(self.driver.window_handles)
        main_handle = parent_handles[0]
        self.driver.execute_script("arguments[0].click();", ptc_btn)

        # Wait for popup
        opened_win = None
        for _ in range(12):
            time.sleep(1)
            new_h = [h for h in self.driver.window_handles if h not in parent_handles]
            if new_h:
                opened_win = new_h[0]
                break

        if not opened_win:
            self.log(f"Không mở được phiếu thi công cho HĐ {contract_no} (No data)", "warning")
            return {
                'contract_no': contract_no,
                'customer_name': '',
                'customer_phone': '',
                'service_type': '',
                'contract_status': '',
                'address': '',
                'service_package': '',
                'materials': '',
                'deploy_type': '',
                'sales': '',
                'tech_params': '',
                'created_date': '',
                'status': 'Lỗi',
                'error': 'No data'
            }

        # Switch to popup window
        self.driver.switch_to.window(opened_win)
        time.sleep(3) # Wait for Blazor rendering
        popup_html = self.driver.page_source

        # Close popup and return to main window safely
        try:
            self.driver.close()
        except Exception:
            pass
        self.driver.switch_to.window(main_handle)

        # Switch back into frame 1 and frameDeployment for next search
        self.ensure_frame_deployment()

        # Parse fields
        data = extract_ptc_fields(popup_html, contract_no)
        if data['status'] == 'Thành công':
            self.log(f"Đã lấy thành công HĐ {contract_no}: {data['customer_name']} | {data['service_type']}", "success")
        else:
            self.log(f"HĐ {contract_no}: {data['error']}", "warning")
        return data

    def fetch_contract_info(self, contract_no, max_retries=2):
        """
        Lấy thông tin hợp đồng với cơ chế tự động phục hồi:
        Nếu tài khoản bị văng ra (do thiết bị khác đăng nhập) hoặc tab bị crash,
        hệ thống sẽ tự động reset trình duyệt, đăng nhập lại và thử lại hợp đồng đó.
        """
        contract_no = contract_no.strip()
        self.log(f"Đang tìm kiếm hợp đồng: {contract_no}...", "info")

        for attempt in range(max_retries + 1):
            # 1. Kiểm tra trạng thái trình duyệt trước khi cào
            if not self.is_driver_healthy() or self.is_kicked_to_login():
                self.log(f"⚠️ Phát hiện tài khoản bị văng ra (có thể do thiết bị khác đăng nhập). Đang chuẩn bị khôi phục...", "warning")
                relogin_ok = self.reset_and_relogin(f"Mất phiên trước khi xử lý {contract_no}")
                if not relogin_ok:
                    return {
                        'contract_no': contract_no,
                        'customer_name': '',
                        'customer_phone': '',
                        'service_type': '',
                        'contract_status': '',
                        'address': '',
                        'service_package': '',
                        'materials': '',
                        'deploy_type': '',
                        'sales': '',
                        'tech_params': '',
                        'created_date': '',
                        'status': 'Lỗi',
                        'error': 'Mất phiên Inside FPT (Tài khoản bị đăng xuất bởi thiết bị khác)'
                    }

            # 2. Dọn dẹp các tab popup còn sót lại nếu có
            try:
                handles = self.driver.window_handles
                if len(handles) > 1:
                    for h in handles[1:]:
                        self.driver.switch_to.window(h)
                        self.driver.close()
                    self.driver.switch_to.window(handles[0])
            except Exception:
                pass

            # 3. Thực thi lấy dữ liệu hợp đồng
            try:
                return self._execute_fetch_contract(contract_no)
            except Exception as e:
                err_str = str(e).lower()
                is_fatal = any(k in err_str for k in [
                    'tab crashed', 'no such window', 'window closed', 'session deleted',
                    'invalid session id', 'disconnected', 'not reachable', 'connection refused',
                    'session not created'
                ]) or self.is_kicked_to_login()

                if is_fatal and attempt < max_retries:
                    self.log(f"⚠️ Phiên bị ngắt khi xử lý HĐ {contract_no} ({e}). Đang reset trình duyệt và thử lại ngay (Lần {attempt + 1}/{max_retries})...", "warning")
                    if self.reset_and_relogin(f"Sự cố phiên tại HĐ {contract_no}"):
                        time.sleep(1)
                        continue # Thử lại hợp đồng này!

                # Nếu là lỗi No data hoặc đã hết số lần thử lại
                self.log(f"Lỗi khi xử lý HĐ {contract_no}: {e}", "error")
                try:
                    handles = self.driver.window_handles
                    if handles:
                        self.driver.switch_to.window(handles[0])
                    self.ensure_frame_deployment()
                except Exception:
                    pass

                return {
                    'contract_no': contract_no,
                    'customer_name': '',
                    'customer_phone': '',
                    'service_type': '',
                    'contract_status': '',
                    'address': '',
                    'service_package': '',
                    'materials': '',
                    'deploy_type': '',
                    'sales': '',
                    'tech_params': '',
                    'created_date': '',
                    'status': 'Lỗi',
                    'error': str(e)
                }

    def close(self):
        """Khi hoàn tất 1 tác vụ: Đóng trình duyệt và xóa sạch toàn bộ session cũ."""
        if self.driver:
            core_login.close_driver_and_clear_session(self.driver)
            self.driver = None

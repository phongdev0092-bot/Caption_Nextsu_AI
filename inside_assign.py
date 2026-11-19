"""
COMPONENT BACKEND: AUTO PHÂN CÔNG TAY
Google Sheet GID 909147347 | Cột: ID | Tác Vụ | Email | MSNV | Account Inside | SHD |
Loại Tác Vụ | Đối tác đến | Block Đến | Nhân Viên Đến | Ngày Cập Nhật | Thao Tác

Quy trình TRIỂN KHAI:
  Inside New V5 >> Hỗ trợ kỹ thuật >> Thông tin chung >> tag TRIỂN KHAI >> nhập SHD vào ô
  "Điều kiện nhập" >> bấm "Phiếu thi công" (mở cửa sổ mới) >> bấm "Phân tuyến" >> popup:
     Đối tác: Phuong Nam-01 | Block = Block Đến | Nhân viên = Nhân Viên Đến |
     Nguyên nhân phân công tay = "Phân công không đúng đối tượng" >> bấm "Cập nhật".

Quy trình BẢO TRÌ:
  Inside New V5 >> Hỗ trợ kỹ thuật >> Thông tin chung >> tab BẢO TRÌ >> nhập SHD vào ô
  "Nhập hợp đồng" >> bấm "Xem CL" (mở cửa sổ riêng) >> bấm "Phân tuyến" >> popup:
     Đối tác: Phuong Nam-01 | Thuộc block = Block Đến | Nhân viên = Nhân Viên Đến |
     Nguyên nhân phân công lại = "Không đúng đối tượng xử lý" >> bấm "Cập nhật".
"""
import re
import time

import pandas as pd
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    StaleElementReferenceException,
    NoSuchElementException,
    NoSuchWindowException,
    WebDriverException,
)

from inside_cls import (
    InsideClearClsAutomation,
    DEFAULT_SHEET_ID,
    normalize_nfc,
    norm_lower,
    remove_accents,
)

GID_ASSIGN = "909147347"
TASK_NAME = "Phân Công Tay"
REASON_REASSIGN_TK = "Phân công không đúng đối tượng"
REASON_REASSIGN_BT = "Không đúng đối tượng xử lý"
REASON_REASSIGN = REASON_REASSIGN_TK


def clean_str(s):
    if not s:
        return ""
    norm = remove_accents(str(s)).lower()
    return re.sub(r"[\s\-_/\\.:,;]+", "", norm)

# Khóa chuẩn hóa (không dấu) -> tên cột chuẩn trong record
_COLUMN_MAP = {
    "id": "ID",
    "tac vu": "Tác Vụ",
    "email": "Email",
    "msnv": "MSNV",
    "account inside": "Account Inside",
    "shd": "SHD",
    "loai tac vu": "Loại Tác Vụ",
    "doi tac den": "Đối tác đến",
    "block den": "Block Đến",
    "nhan vien den": "Nhân Viên Đến",
    "ngay cap nhat": "Ngày Cập Nhật",
    "thao tac": "Thao Tác",
}


def _canonical_column(raw_name):
    key = remove_accents(raw_name)
    key = re.sub(r"\s+", " ", key)
    if key in _COLUMN_MAP:
        return _COLUMN_MAP[key]
    # Fuzzy fallback (thứ tự quan trọng: cụm dài trước cụm ngắn)
    if "loai tac vu" in key:
        return "Loại Tác Vụ"
    if "doi tac" in key:
        return "Đối tác đến"
    if "block" in key:
        return "Block Đến"
    if "nhan vien" in key:
        return "Nhân Viên Đến"
    if "account" in key:
        return "Account Inside"
    if "ngay" in key or "thoi gian" in key:
        return "Ngày Cập Nhật"
    if "thao tac" in key or "ghi chu" in key:
        return "Thao Tác"
    if key == "shd" or "hop dong" in key:
        return "SHD"
    if "email" in key:
        return "Email"
    return None


def is_final_thao_tac(thao_tac):
    """Dòng đã có kết quả cuối cùng (chỉ thành công hoàn tất). Cho phép chạy lại các dòng lỗi/thất bại."""
    t = norm_lower(thao_tac)
    if not t or "không thành công" in t or "that bai" in t or "chưa" in t or "lỗi" in t or "error" in t:
        return False
    return "cập nhật thành công" in t or "thành công!" in t or "đã xử lý" in t


def format_assign_thao_tac(is_success, detail=""):
    if is_success:
        return "Cập nhật thành công!"
    clean = re.sub(r"^không\s+thành\s+công\s*[:\-]?", "", str(detail or "").strip(), flags=re.IGNORECASE).strip()
    return f"Không thành công : {clean or 'Không xác định'}"


def fetch_sheet_data(sheet_id=DEFAULT_SHEET_ID, gid=GID_ASSIGN):
    url = (f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq"
           f"?tqx=out:csv&gid={gid}&_t={int(time.time() * 1000)}")
    try:
        import io
        import urllib.request
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        content = urllib.request.urlopen(req, timeout=12).read().decode("utf-8", errors="ignore")
        df = pd.read_csv(io.StringIO(content)).fillna("")
        col_indices = {}
        mapping = {}
        for idx, c in enumerate(df.columns):
            canon = _canonical_column(c)
            mapping[c] = canon
            if canon == "SHD":
                col_indices["shd"] = idx
            elif canon == "Thao Tác":
                col_indices["thao_tac"] = idx
            elif canon == "Ngày Cập Nhật":
                col_indices["ngay"] = idx

        records = []
        for raw in df.to_dict(orient="records"):
            rec = {}
            for k, v in raw.items():
                val = normalize_nfc(v) if isinstance(v, str) else str(v)
                if val.lower() == "nan":
                    val = ""
                rec[normalize_nfc(k)] = val
                canon = mapping.get(k)
                if canon:
                    rec[canon] = val
            # Bỏ dòng trống hoàn toàn (không có SHD)
            if str(rec.get("SHD", "")).strip():
                records.append(rec)

        return {
            "status": "ok",
            "count": len(records),
            "columns": [normalize_nfc(c) for c in df.columns],
            "col_indices": col_indices,
            "records": records,
        }
    except Exception as e:
        return {"status": "error", "message": f"Không thể đọc Google Sheet Phân Công Tay: {e}", "records": []}


def _xp(text):
    """Escape chuỗi cho XPath literal."""
    if "'" not in text:
        return f"'{text}'"
    return "concat(" + ", \"'\", ".join(f"'{p}'" for p in text.split("'")) + ")"


class InsideAssignAutomation(InsideClearClsAutomation):
    """Tái sử dụng khởi tạo Chrome / đăng nhập / điều hướng menu của InsideClearClsAutomation."""

    # ------------------------------------------------------------------ helpers
    def _visible(self, elements):
        out = []
        for e in elements:
            try:
                if e.is_displayed():
                    out.append(e)
            except Exception:
                continue
        return out

    def _js_click(self, el):
        self.driver.execute_script("arguments[0].scrollIntoView({block:'center'});", el)
        self.driver.execute_script("arguments[0].click();", el)

    def _wait_find(self, xpath, timeout=15, visible=True):
        end = time.time() + timeout
        while time.time() < end:
            found = self.driver.find_elements(By.XPATH, xpath)
            if visible:
                found = self._visible(found)
            if found:
                return found[0]
            time.sleep(0.5)
        return None

    def _find_in_frames(self, xpath, timeout=15):
        """Tìm phần tử ở document hiện tại; nếu không có thì quét lần lượt các iframe."""
        end = time.time() + timeout
        while time.time() < end:
            self.driver.switch_to.default_content()
            found = self._visible(self.driver.find_elements(By.XPATH, xpath))
            if found:
                return found[0]
            frames = self.driver.find_elements(By.TAG_NAME, "iframe")
            for i in range(len(frames)):
                try:
                    self.driver.switch_to.default_content()
                    self.driver.switch_to.frame(i)
                    found = self._visible(self.driver.find_elements(By.XPATH, xpath))
                    if found:
                        return found[0]
                except Exception:
                    continue
            time.sleep(0.7)
        self.driver.switch_to.default_content()
        return None

    def _find_in_child_frames(self, xpath, timeout=12):
        """
        Tìm phần tử trong frame HIỆN TẠI (không jump ra default_content)
        và các iframe con bên trong frame hiện tại.
        Dùng khi đã switch_to.frame(1) và muốn tìm trong các sub-iframe.
        """
        end = time.time() + timeout

        # Lưu context hiện tại (Frame 1)
        # Thử tìm trong frame hiện tại trước
        found = self._visible(self.driver.find_elements(By.XPATH, xpath))
        if found:
            return found[0]

        while time.time() < end:
            # Lấy danh sách iframe trong frame hiện tại
            child_frames = self.driver.find_elements(By.TAG_NAME, "iframe")
            for i in range(len(child_frames)):
                try:
                    self.driver.switch_to.frame(i)   # vào sub-frame
                    found = self._visible(self.driver.find_elements(By.XPATH, xpath))
                    if found:
                        return found[0]
                    # Thử sâu hơn 1 cấp
                    sub_frames = self.driver.find_elements(By.TAG_NAME, "iframe")
                    for j in range(len(sub_frames)):
                        try:
                            self.driver.switch_to.frame(j)
                            found = self._visible(self.driver.find_elements(By.XPATH, xpath))
                            if found:
                                return found[0]
                            self.driver.switch_to.parent_frame()
                        except Exception:
                            self.driver.switch_to.parent_frame()
                    self.driver.switch_to.parent_frame()   # quay lại Frame 1
                except Exception:
                    try:
                        self.driver.switch_to.default_content()
                        self.driver.switch_to.frame(1)
                    except Exception:
                        pass
            time.sleep(0.7)
        return None

    # ------------------------------------------------------------------ navigation
    def _switch_to_frame1(self):
        """Chuyển context về Frame 1 (nơi chứa menu tab: TRIỂN KHAI, BẢO TRÌ...)."""
        self.driver.switch_to.default_content()
        WebDriverWait(self.driver, 15).until(
            EC.frame_to_be_available_and_switch_to_it(1)
        )
        time.sleep(0.3)

    def navigate_to_assign_page(self):
        """Inside New V5 >> Ho tro ky thuat >> Thong tin chung."""
        self.navigate_to_general_info_page()
        # navigate_to_general_info_page kết thúc ở Frame 1
        self._switch_to_frame1()
        self.main_handle = self.driver.current_window_handle
        self.log("Đã sẵn sàng tại Thông tin chung (Frame 1).", "success")

    def _switch_to_tk_child_iframe(self, timeout=15):
        """Tìm và chuyển vào iframe con của Triển Khai (/tk/reportbacklog hoặc iframe 0)."""
        self._switch_to_frame1()
        end = time.time() + timeout
        while time.time() < end:
            frames = self.driver.find_elements(By.TAG_NAME, "iframe")
            for f in frames:
                try:
                    src = f.get_attribute("src") or ""
                    if "/tk/" in src or "tk/reportbacklog" in src:
                        self.driver.switch_to.frame(f)
                        self.log("Đã vào iframe Triển Khai.", "info")
                        return
                except Exception:
                    continue
            time.sleep(0.5)

        self._switch_to_frame1()
        frames = self.driver.find_elements(By.TAG_NAME, "iframe")
        if frames:
            self.driver.switch_to.frame(0)

    def _switch_to_bt_child_iframe(self, timeout=15):
        """Tìm và chuyển vào iframe con của Bảo Trì (/bt/reportbacklog hoặc iframe mới nhất)."""
        self._switch_to_frame1()
        end = time.time() + timeout
        while time.time() < end:
            frames = self.driver.find_elements(By.TAG_NAME, "iframe")
            for f in frames:
                try:
                    src = f.get_attribute("src") or ""
                    if "/bt/" in src or "bt/reportbacklog" in src:
                        self.driver.switch_to.frame(f)
                        self.log("Đã vào iframe Bảo Trì.", "info")
                        return
                except Exception:
                    continue
            time.sleep(0.5)

        self._switch_to_frame1()
        frames = self.driver.find_elements(By.TAG_NAME, "iframe")
        if frames:
            self.driver.switch_to.frame(frames[-1])
            self.log(f"Đã chuyển vào iframe con cuối cùng (tổng {len(frames)} iframe).", "info")

    def _return_to_main_form(self):
        """Đóng các cửa sổ phụ, quay lại cửa sổ chính và về Frame 1."""
        try:
            handles = self.driver.window_handles
            for h in handles:
                if h != self.main_handle:
                    self.driver.switch_to.window(h)
                    self.driver.close()
        except Exception:
            pass
        self.driver.switch_to.window(self.main_handle)
        self._switch_to_frame1()

    # ------------------------------------------------------------------ form: TRIỂN KHAI
    def _click_tab_trien_khai(self):
        """Chuyển sang tab TRIỂN KHAI trong Frame 1 và vào child iframe Triển Khai."""
        self.log("Đang chuyển sang tab TRIỂN KHAI...", "info")
        self._switch_to_frame1()

        # Kiểm tra nếu Frame 1 có form đăng nhập do phiên hết hạn
        if len(self.driver.find_elements(By.ID, "fUserName")) > 0 or len(self.driver.find_elements(By.ID, "fPassword")) > 0:
            self.log("Phát hiện form đăng nhập trong Frame 1. Đang tự động đăng nhập...", "warning")
            self._perform_auto_login()
            self.navigate_to_assign_page()
            self._switch_to_frame1()

        # Chờ tab Blazor hiển thị (tối đa 20s)
        for _ in range(40):
            tabs = self.driver.find_elements(By.CLASS_NAME, "mud-tab")
            if tabs:
                break
            # Nếu trong lúc chờ xuất hiện form đăng nhập
            if len(self.driver.find_elements(By.ID, "fUserName")) > 0:
                self.log("Phát hiện yêu cầu đăng nhập trong Frame 1. Đang đăng nhập...", "warning")
                self._perform_auto_login()
                self.navigate_to_assign_page()
                self._switch_to_frame1()
            time.sleep(0.5)

        js_click_tk = """
            var tabs = Array.from(document.querySelectorAll('.mud-tab'));
            var target = tabs.find(function(t) {
                var txt = (t.innerText || t.textContent || '').trim().toLowerCase();
                return txt.indexOf('triển khai') !== -1 || txt.indexOf('trien khai') !== -1;
            });
            if (!target) return {success: false, error: 'Không tìm thấy tab Triển Khai trong Frame 1'};

            target.scrollIntoView({block: 'center', inline: 'center'});
            target.click();

            var r = target.getBoundingClientRect();
            var x = r.left + r.width / 2;
            var y = r.top + r.height / 2;
            ['pointerdown', 'mousedown', 'pointerup', 'mouseup', 'click'].forEach(function(evt) {
                target.dispatchEvent(new MouseEvent(evt, {
                    bubbles: true,
                    cancelable: true,
                    view: window,
                    clientX: x,
                    clientY: y
                }));
            });
            return {success: true, text: target.innerText};
        """
        res = self.driver.execute_script(js_click_tk)
        if not res or not res.get("success"):
            raise RuntimeError(f"Không thể click tab TRIỂN KHAI: {res}")
        time.sleep(2)
        self._switch_to_tk_child_iframe()
        self.log("Đã chọn tab TRIỂN KHAI.", "info")

    def _fill_dieu_kien_nhap(self, shd):
        """
        DEBUG confirmed: trang Inside V5 la MudBlazor.
        O 'Dieu kien nhap' = input[10] trong CHILD-IFRAME[0].
        Class: 'mud-input-slot mud-input-root mud-input-root-outlined mud-input-root-margin-dense'
        (khac voi cac dropdown co class 'mud-select-input').
        """
        # XPath chinh xac tu debug output:
        # input co class margin-dense va KHONG co mud-select-input
        xp_main = (
            "//input[contains(@class,'mud-input-root-margin-dense') "
            "and not(contains(@class,'mud-select-input'))]"
        )
        # Fallback: input mud-input-slot khong co placeholder 'Khong chon'
        # (cac dropdown co placeholder='Khong chon', o text field thi khong)
        xp_fallback = (
            "//input[@type='text' "
            "and contains(@class,'mud-input-slot') "
            "and not(contains(@class,'mud-select-input')) "
            "and (@placeholder='' or not(@placeholder))]"
        )

        inp = self._wait_find(xp_main, timeout=8)
        if not inp:
            self.log("Khong tim thay margin-dense input, thu fallback...", "warning")
            all_inputs = self.driver.find_elements(By.XPATH, xp_fallback)
            vis = self._visible(all_inputs)
            if vis:
                # Chon phan tu cuoi trong danh sach visible (o DKNhap thuong o cuoi)
                inp = vis[-1]

        if not inp:
            raise RuntimeError(
                "Khong tim thay o nhap SHD (MudTextField) trong child-iframe. "
                "Dam bao trang Thong tin chung da tai xong va tab TRIEN KHAI duoc chon."
            )

        self.log(f"Nhap SHD '{shd}' vao o Dieu kien nhap (MudBlazor)...", "info")
        self.driver.execute_script("arguments[0].scrollIntoView({block:'center'});", inp)
        try:
            inp.click()
        except Exception:
            self.driver.execute_script("arguments[0].focus();", inp)
        time.sleep(0.3)
        inp.clear()
        self.driver.execute_script("arguments[0].value = '';", inp)
        inp.send_keys(shd)
        time.sleep(0.4)
        # Trigger Blazor reactivity: dispatch input + change event
        self.driver.execute_script("""
            var el = arguments[0];
            el.dispatchEvent(new Event('input',  {bubbles: true}));
            el.dispatchEvent(new Event('change', {bubbles: true}));
        """, inp)
        time.sleep(0.5)
        self.log(f"Da nhap SHD '{shd}' thanh cong.", "success")

    def _open_ptc_window(self):
        """
        DEBUG confirmed: nut 'Phieu thi cong' la Blazor button (onclick=None),
        nam trong CHILD-IFRAME[0].
        """
        before = set(self.driver.window_handles)

        xp_ptc = (
            "//button[normalize-space(.)='Phi\u1ebfu thi c\u00f4ng'] | "
            "//button[contains(normalize-space(.),'Phi\u1ebfu thi c\u00f4ng')] | "
            "//button[.//*[contains(text(),'Phi\u1ebfu thi c\u00f4ng')]]"
        )
        btn = self._wait_find(xp_ptc, timeout=12)

        if not btn:
            raise RuntimeError(
                "Khong tim thay nut 'Phieu thi cong'. "
                "Kiem tra SHD hop le va trang da tai xong chua."
            )

        self.log("Bam nut 'Phieu thi cong' (mo cua so moi)...", "info")
        self._js_click(btn)
        try:
            WebDriverWait(self.driver, 30).until(
                lambda d: len(set(d.window_handles) - before) > 0
            )
        except Exception:
            raise RuntimeError("Cua so Phieu thi cong khong mo ra sau 30 giay. SHD co the khong co PTC.")

        new_handle = list(set(self.driver.window_handles) - before)[0]
        self.driver.switch_to.window(new_handle)
        time.sleep(3)
        self.log("Đã chuyển sang tab Phiếu thi công (Triển Khai).", "info")

    # ------------------------------------------------------------------ form: BẢO TRÌ
    def _click_tab_bao_tri(self):
        """Chuyển sang tab BẢO TRÌ trong Frame 1 và vào child iframe của Bảo Trì."""
        self.log("Đang chuyển sang tab BẢO TRÌ...", "info")
        self._switch_to_frame1()

        # Kiểm tra nếu Frame 1 có form đăng nhập do phiên hết hạn
        if len(self.driver.find_elements(By.ID, "fUserName")) > 0 or len(self.driver.find_elements(By.ID, "fPassword")) > 0:
            self.log("Phát hiện form đăng nhập trong Frame 1. Đang tự động đăng nhập...", "warning")
            self._perform_auto_login()
            self.navigate_to_assign_page()
            self._switch_to_frame1()

        # Chờ tab Blazor hiển thị (tối đa 20s)
        for _ in range(40):
            tabs = self.driver.find_elements(By.CLASS_NAME, "mud-tab")
            if tabs:
                break
            # Nếu trong lúc chờ xuất hiện form đăng nhập
            if len(self.driver.find_elements(By.ID, "fUserName")) > 0:
                self.log("Phát hiện yêu cầu đăng nhập trong Frame 1. Đang đăng nhập...", "warning")
                self._perform_auto_login()
                self.navigate_to_assign_page()
                self._switch_to_frame1()
            time.sleep(0.5)

        js_click_tab = """
            var tabs = Array.from(document.querySelectorAll('.mud-tab'));
            var target = tabs.find(function(t) {
                var txt = (t.innerText || t.textContent || '').trim().toLowerCase();
                return txt.indexOf('bảo trì') !== -1 || txt.indexOf('bao tri') !== -1;
            });
            if (!target) return {success: false, error: 'Không tìm thấy tab Bảo Trì trong Frame 1'};

            target.scrollIntoView({block: 'center', inline: 'center'});
            target.click();

            var r = target.getBoundingClientRect();
            var x = r.left + r.width / 2;
            var y = r.top + r.height / 2;
            ['pointerdown', 'mousedown', 'pointerup', 'mouseup', 'click'].forEach(function(evt) {
                target.dispatchEvent(new MouseEvent(evt, {
                    bubbles: true,
                    cancelable: true,
                    view: window,
                    clientX: x,
                    clientY: y
                }));
            });
            return {success: true, text: target.innerText};
        """
        res = self.driver.execute_script(js_click_tab)
        if not res or not res.get("success"):
            raise RuntimeError(f"Không thể click tab BẢO TRÌ: {res}")
        time.sleep(2)

        # Chuyển vào child iframe của BẢO TRÌ
        self._switch_to_bt_child_iframe()
        self.log("✅ Đã chuyển sang tab BẢO TRÌ và vào iframe Bảo Trì thành công.", "success")

    def _fill_nhap_hop_dong(self, shd):
        """
        Tab BẢO TRÌ: Điền SHD vào ô 'Nhập hợp đồng' (ngay cạnh nút 'Xem CL').
        """
        xp_list = [
            "//input[contains(@class,'mud-input-root-margin-dense') and not(contains(@class,'mud-select-input'))]",
            "//button[contains(normalize-space(.),'Xem CL')]/preceding::input[1]",
            "//*[contains(normalize-space(.),'Nhập hợp đồng')]/following::input[1]",
            "//input[contains(@placeholder,'hợp đồng') or contains(@placeholder,'hop dong')]",
        ]
        inp = None
        for xp in xp_list:
            found = self._wait_find(xp, timeout=4)
            if found:
                inp = found
                break

        if not inp:
            js_find_input = """
                var btn = Array.from(document.querySelectorAll('button, a')).find(function(el) {
                    return el.innerText && el.innerText.includes('Xem CL');
                });
                if (btn) {
                    var inputs = Array.from(document.querySelectorAll('input'));
                    for (var i = inputs.length - 1; i >= 0; i--) {
                        var pos = inputs[i].compareDocumentPosition(btn);
                        if (pos & Node.DOCUMENT_POSITION_FOLLOWING) {
                            return inputs[i];
                        }
                    }
                }
                return null;
            """
            inp = self.driver.execute_script(js_find_input)

        if not inp:
            raise RuntimeError(
                "Không tìm thấy ô 'Nhập hợp đồng' trong tab BẢO TRÌ. "
                "Đảm bảo đã ở trên tab BẢO TRÌ và nút 'Xem CL' đã hiển thị."
            )

        self.log(f"Nhập SHD '{shd}' vào ô Nhập hợp đồng (BẢO TRÌ)...", "info")
        self.driver.execute_script("arguments[0].scrollIntoView({block:'center'});", inp)
        try:
            inp.click()
        except Exception:
            self.driver.execute_script("arguments[0].focus();", inp)
        time.sleep(0.3)
        inp.clear()
        self.driver.execute_script("arguments[0].value = '';", inp)
        inp.send_keys(shd)
        time.sleep(0.4)
        # Dispatch Blazor events
        self.driver.execute_script("""
            var el = arguments[0];
            el.dispatchEvent(new Event('input',  {bubbles: true}));
            el.dispatchEvent(new Event('change', {bubbles: true}));
        """, inp)
        time.sleep(0.5)
        self.log(f"Đã nhập SHD '{shd}' vào ô Nhập hợp đồng thành công.", "success")

    def _open_cl_window(self):
        """
        Bấm nút 'Xem CL' để mở tab Checklist Bảo trì (mở tab riêng).
        """
        before = set(self.driver.window_handles)

        xp_cl = (
            "//button[normalize-space(.)='Xem CL'] | "
            "//button[contains(normalize-space(.),'Xem CL')] | "
            "//button[.//*[contains(text(),'Xem CL')]] | "
            "//a[contains(normalize-space(.),'Xem CL')]"
        )
        btn = self._wait_find(xp_cl, timeout=12)

        if not btn:
            raise RuntimeError(
                "Không tìm thấy nút 'Xem CL'. "
                "Kiểm tra SHD hợp lệ và tab BẢO TRÌ đã tải xong."
            )

        self.log("Bấm nút 'Xem CL' (mở cửa sổ riêng của Bảo trì)...", "info")
        self._click_element(btn)
        try:
            WebDriverWait(self.driver, 30).until(
                lambda d: len(set(d.window_handles) - before) > 0
            )
        except Exception:
            raise RuntimeError("Cửa sổ Xem CL không mở ra sau 30 giây. Hợp đồng có thể không có phiếu bảo trì.")

        new_handle = list(set(self.driver.window_handles) - before)[0]
        self.driver.switch_to.window(new_handle)
        time.sleep(3)
        self.log("Đã chuyển sang tab riêng của Checklist Bảo trì.", "info")

    def _click_phan_tuyen(self):
        """
        Cua so PTC la standalone window (khong phai iframe).
        KHONG dung _find_in_frames vi no goi switch_to.default_content()
        thoat khoi window PTC dang mo.
        Tim nut Phan tuyen TRONG cua so hien tai va cac sub-iframe cua no.
        """
        self.ptc_handle = self.driver.current_window_handle

        xp_btn = (
            "//button[normalize-space(.)='Ph\u00e2n tuy\u1ebfn'] | "
            "//button[contains(normalize-space(.),'Ph\u00e2n tuy\u1ebfn')] | "
            "//a[contains(normalize-space(.),'Ph\u00e2n tuy\u1ebfn')]"
        )

        btn = None
        end = time.time() + 30
        while time.time() < end:
            # Tim trong document chinh cua cua so PTC truoc
            self.driver.switch_to.default_content()
            els = self._visible(self.driver.find_elements(By.XPATH, xp_btn))
            if els:
                btn = els[0]
                break
            # Quet qua cac iframe BEN TRONG cua so PTC (1 cap)
            frames = self.driver.find_elements(By.TAG_NAME, "iframe")
            for i in range(len(frames)):
                try:
                    self.driver.switch_to.frame(i)
                    els = self._visible(self.driver.find_elements(By.XPATH, xp_btn))
                    if els:
                        btn = els[0]
                        break
                    self.driver.switch_to.default_content()
                except Exception:
                    try:
                        self.driver.switch_to.default_content()
                    except Exception:
                        pass
            if btn:
                break
            time.sleep(1.0)

        if not btn:
            raise RuntimeError(
                "Khong tim thay nut 'Phan tuyen' tren phieu thi cong. "
                "Kiem tra SHD co PTC hop le khong."
            )

        self.log("Bấm nút 'Phân tuyến'...", "info")
        self._js_click(btn)

        # Chờ popup mud-dialog hiện ra trong cửa sổ PTC (quét cả frame hiện tại và default_content)
        dialog = None
        end_d = time.time() + 15
        while time.time() < end_d:
            d_els = self._visible(self.driver.find_elements(By.XPATH, "//div[contains(@class,'mud-dialog')]"))
            if d_els:
                dialog = d_els[0]
                break
            try:
                self.driver.switch_to.default_content()
                d_els = self._visible(self.driver.find_elements(By.XPATH, "//div[contains(@class,'mud-dialog')]"))
                if d_els:
                    dialog = d_els[0]
                    break
            except Exception:
                pass
            time.sleep(0.5)

        if not dialog:
            raise RuntimeError("Popup 'Phân tuyến' không hiện ra sau khi bấm")
        time.sleep(1.0)
        self.log("Popup Phân tuyến đã mở thành công.", "info")

    # ------------------------------------------------------------------ popup fields
    _FIELD_CONFIGS = {
        "doi_tac": {
            "name": "Đối tác",
            "aliases": ["Đối tác", "Đối tác đến", "Đơn vị"],
            "keywords": ["doi tac", "doi tac den", "don vi"],
            "placeholder": "Chọn đối tác",
            "index": 0,
            "cascade_wait": 3.0,
        },
        "block": {
            "name": "Block",
            "aliases": ["Block", "Block đến", "Thuộc block", "Thuoc block"],
            "keywords": ["block", "block den", "thuoc block"],
            "placeholder": "Chọn Block",
            "index": 1,
            "cascade_wait": 2.5,
        },
        "nhan_vien": {
            "name": "Nhân viên",
            "aliases": ["Nhân viên", "Nhân viên đến", "Kỹ thuật", "NVKT"],
            "keywords": ["nhan vien", "nhan vien den", "ky thuat", "nvkt"],
            "placeholder": "Chọn nhân viên",
            "index": 2,
            "cascade_wait": 1.5,
        },
        "nguyen_nhan": {
            "name": "Nguyên nhân",
            "aliases": [
                "Nguyên nhân",
                "Nguyên nhân phân công tay",
                "Nguyên nhân phân công lại",
                "Lý do",
            ],
            "keywords": [
                "nguyen nhan",
                "nguyen nhan phan cong tay",
                "nguyen nhan phan cong lai",
                "ly do",
            ],
            "placeholder": "Chọn nguyên nhân",
            "index": 3,
            "cascade_wait": 1.0,
        },
    }

    def _resolve_field_config(self, label_or_key):
        k_clean = remove_accents(str(label_or_key)).lower().strip()
        for k, cfg in self._FIELD_CONFIGS.items():
            if k == label_or_key or k == k_clean:
                return k, cfg
            for alias in cfg["aliases"]:
                a_clean = remove_accents(alias).lower()
                if a_clean in k_clean or k_clean in a_clean:
                    return k, cfg
        return "block", self._FIELD_CONFIGS["block"]

    def _click_element(self, el):
        """Click phần tử an toàn, hỗ trợ cả native click và mouse event dispatch cho Blazor."""
        try:
            self.driver.execute_script("arguments[0].scrollIntoView({block:'center', inline:'nearest'});", el)
        except Exception:
            pass
        time.sleep(0.2)
        try:
            el.click()
        except Exception:
            try:
                self.driver.execute_script("""
                    var el = arguments[0];
                    var rect = el.getBoundingClientRect();
                    var x = rect.left + rect.width / 2;
                    var y = rect.top + rect.height / 2;
                    ['pointerdown', 'mousedown', 'pointerup', 'mouseup', 'click'].forEach(function(evt) {
                        el.dispatchEvent(new MouseEvent(evt, {
                            bubbles: true,
                            cancelable: true,
                            view: window,
                            clientX: x,
                            clientY: y
                        }));
                    });
                """, el)
            except Exception:
                self.driver.execute_script("arguments[0].click();", el)

    def _find_dialog_control(self, field_key, timeout=12):
        """
        Tìm MudInputControl cho field_key ('doi_tac', 'block', 'nhan_vien', 'nguyen_nhan').
        Hỗ trợ 3 lớp tìm kiếm:
        1. Tìm theo keyword trong label/input/placeholder bên trong control
        2. Tìm theo XPath nhãn bên ngoài control (ancestor / following)
        3. Positional fallback theo thứ tự các trường trên popup
        """
        key, cfg = self._resolve_field_config(field_key)
        end = time.time() + timeout
        while time.time() < end:
            controls = self._visible(
                self.driver.find_elements(By.XPATH, "//div[contains(@class,'mud-dialog')]//div[contains(@class,'mud-input-control')]")
            )
            if not controls:
                time.sleep(0.4)
                continue

            # 1. Tìm theo keyword bên trong control
            for ctrl in controls:
                full_text = remove_accents(ctrl.text or "").lower()
                inputs = ctrl.find_elements(By.XPATH, ".//input")
                for inp in inputs:
                    ph = remove_accents(inp.get_attribute("placeholder") or "").lower()
                    al = remove_accents(inp.get_attribute("aria-label") or "").lower()
                    full_text += f" {ph} {al}"

                for kw in cfg["keywords"]:
                    if kw in full_text:
                        return ctrl

            # 2. Tìm theo XPath nhãn
            for alias in cfg["aliases"]:
                xp_ancestor = (
                    f"//div[contains(@class,'mud-dialog')]//*[self::label or self::p or self::span]"
                    f"[contains(normalize-space(.),{_xp(alias)})]/ancestor::div[contains(@class,'mud-input-control')][1]"
                )
                els = self._visible(self.driver.find_elements(By.XPATH, xp_ancestor))
                if els:
                    return els[0]

                xp_following = (
                    f"//div[contains(@class,'mud-dialog')]//*[self::label or self::p or self::span]"
                    f"[contains(normalize-space(.),{_xp(alias)})]/following::div[contains(@class,'mud-input-control')][1]"
                )
                els = self._visible(self.driver.find_elements(By.XPATH, xp_following))
                if els:
                    return els[0]

            # 3. Positional fallback
            idx = cfg.get("index", -1)
            if 0 <= idx < len(controls):
                return controls[idx]

            time.sleep(0.5)
        return None

    def _get_control_value(self, control):
        if not control:
            return ""
        try:
            inputs = control.find_elements(By.XPATH, ".//input")
            for inp in inputs:
                v = (inp.get_attribute("value") or "").strip()
                if v:
                    return v
            txt = (control.text or "").strip()
            labels = control.find_elements(By.XPATH, ".//label")
            for lb in labels:
                lb_txt = (lb.text or "").strip()
                if lb_txt and txt.startswith(lb_txt):
                    txt = txt[len(lb_txt):].strip()
            return txt
        except Exception:
            return ""

    def _is_empty_or_placeholder(self, val):
        if not val or not val.strip():
            return True
        v_low = remove_accents(val).lower().strip()
        placeholders = [
            "chon", "chua chon", "select",
            "chon doi tac", "chon block", "chon nhan vien", "chon nguyen nhan",
            "doi tac", "block", "nhan vien", "nguyen nhan", "ly do"
        ]
        return any(v_low == p or v_low == f"chon {p}" for p in placeholders)

    def _is_value_matched(self, current_val, target_val, field_key=None):
        if self._is_empty_or_placeholder(current_val):
            return False
        c_clean = clean_str(current_val)
        t_clean = clean_str(target_val)
        if not c_clean or not t_clean:
            return False
        if c_clean == t_clean:
            return True
        if t_clean in c_clean or c_clean in t_clean:
            return True
        if field_key == "nguyen_nhan":
            if "khongdungdoituong" in c_clean or "doituong" in c_clean:
                return True
        return False

    def _wait_popover_items(self, timeout=12):
        """Chờ đến khi mud-popover có item thực sự (không phải đang loading)."""
        items_xp = (
            "//div[contains(@class,'mud-popover-open')]//*[contains(@class,'mud-list-item') or @role='option'] | "
            "//div[contains(@class,'mud-popover') and not(contains(@class,'mud-popover-hidden'))]//*[contains(@class,'mud-list-item') or @role='option']"
        )
        end = time.time() + timeout
        while time.time() < end:
            items = self._visible(self.driver.find_elements(By.XPATH, items_xp))
            real = []
            for it in items:
                try:
                    txt = (it.text or "").strip()
                    if txt and "loading" not in txt.lower():
                        real.append(it)
                except Exception:
                    continue
            if real:
                return real
            time.sleep(0.4)
        return []

    def _select_dialog_field(self, field_key, value):
        """
        Chọn giá trị 'value' cho trường 'field_key' trong Popup Phân Tuyến.
        field_key: 'doi_tac', 'block', 'nhan_vien', 'nguyen_nhan'
        """
        key, cfg = self._resolve_field_config(field_key)
        field_name = cfg["name"]
        value = str(value or "").strip()
        if not value:
            self.log(f"Bỏ qua '{field_name}': giá trị rỗng.", "warning")
            return

        self.log(f"Đang chọn {field_name}: '{value}'...", "info")
        target_clean = clean_str(value)

        # 1. Tìm control
        control = self._find_dialog_control(key, timeout=12)
        if not control:
            raise RuntimeError(f"Không tìm thấy ô '{field_name}' trong popup Phân tuyến")

        # 2. Nếu ô đã có đúng giá trị rồi thì bỏ qua
        cur_val = self._get_control_value(control)
        if self._is_value_matched(cur_val, value, key):
            self.log(f"'{field_name}' đã là '{cur_val}' (hợp lệ) - bỏ qua.", "info")
            return

        # 3. Mở dropdown
        clickable = control.find_elements(
            By.XPATH, ".//input | .//div[contains(@class,'mud-select-input')] | .//div[contains(@class,'mud-input')]"
        )
        target_el = clickable[0] if clickable else control
        self._click_element(target_el)
        time.sleep(0.5)

        # 4. Chờ popover items xuất hiện
        items = self._wait_popover_items(timeout=10)

        # Nếu không có items -> Thử gõ text để filter nếu là MudAutocomplete
        if not items:
            inputs = control.find_elements(By.XPATH, ".//input[@type='text']")
            for inp in inputs:
                ro = inp.get_attribute("readonly")
                if ro not in ("true", "readonly"):
                    try:
                        self._click_element(inp)
                        time.sleep(0.2)
                        inp.clear()
                        inp.send_keys(value)
                        time.sleep(1.5)
                        items = self._wait_popover_items(timeout=6)
                        break
                    except Exception:
                        pass

        # Thử click lại lần 2 nếu vẫn trống (refresh sau khi Blazor load xong)
        if not items:
            self.log(f"Dropdown '{field_name}' đang tải, thử mở lại...", "info")
            self._click_element(target_el)
            time.sleep(1.2)
            items = self._wait_popover_items(timeout=8)

        if not items:
            raise RuntimeError(
                f"Dropdown '{field_name}' không có tùy chọn nào sau thời gian chờ. "
                f"Kiểm tra Đối tác/Block đã được chọn đúng chưa."
            )

        # 5. Tìm option khớp
        matched = None
        # Ưu tiên 1: Khớp chính xác (clean)
        for it in items:
            try:
                t_it = clean_str(it.text)
                if t_it == target_clean:
                    matched = it
                    break
            except Exception:
                continue

        # Ưu tiên 2: Khớp một phần
        if not matched:
            for it in items:
                try:
                    t_it = clean_str(it.text)
                    if t_it and (target_clean in t_it or t_it in target_clean):
                        matched = it
                        break
                except Exception:
                    continue

        # Ưu tiên 3: Đối với Nguyên nhân phân công
        if not matched and key == "nguyen_nhan":
            for it in items:
                try:
                    t_it = clean_str(it.text)
                    if "khongdungdoituong" in t_it or "doituong" in t_it:
                        matched = it
                        break
                except Exception:
                    continue

        # Ưu tiên 4: Fallback theo từ khóa đầu tiên
        if not matched and " " in value:
            w1 = clean_str(value.split()[0])
            for it in items:
                try:
                    if w1 in clean_str(it.text):
                        matched = it
                        break
                except Exception:
                    continue

        if not matched:
            avail = []
            for it in items[:10]:
                try:
                    t = (it.text or "").strip()
                    if t:
                        avail.append(t)
                except Exception:
                    pass
            try:
                self.driver.find_element(By.TAG_NAME, "body").send_keys(Keys.ESCAPE)
            except Exception:
                pass
            raise RuntimeError(
                f"Không tìm thấy {field_name} '{value}' trong danh sách. "
                f"Các tùy chọn có sẵn ({len(items)} mục): {avail}"
            )

        # 6. Click chọn item
        matched_text = ""
        try:
            matched_text = matched.text.strip()
        except Exception:
            matched_text = value
        self._click_element(matched)
        time.sleep(0.5)

        # 7. Cascade wait để dropdown con cập nhật dữ liệu
        c_wait = cfg.get("cascade_wait", 1.5)
        self.log(f"Đã chọn {field_name}: '{matched_text}'. Chờ cascade {c_wait}s...", "success")
        time.sleep(c_wait)

    def _fill_and_verify_popup(self, record):
        """
        Quy trình chuẩn Phân Tuyến (áp dụng cho cả Triển Khai và Bảo Trì):
        - Đối tác: Phuong Nam-01 (hoặc lấy từ Sheet nếu có)
        - Block / Thuộc block: Block Đến trên Sheet
        - Nhân viên: Nhân Viên Đến trên Sheet
        - Nguyên nhân:
            + BẢO TRÌ: 'Không đúng đối tượng xử lý'
            + TRIỂN KHAI: 'Phân công không đúng đối tượng'
        - Kiểm tra kỹ toàn bộ form: Điền đủ form rồi mới bấm cập nhật!
        """
        shd = str(record.get("SHD", "")).strip()
        block = str(record.get("Block Đến", "")).strip()
        nhan_vien = str(record.get("Nhân Viên Đến", "")).strip()
        doi_tac = str(record.get("Đối tác đến", "")).strip() or "Phuong Nam-01"

        loai = remove_accents(record.get("Loại Tác Vụ", "")).lower()
        if "bao tri" in loai:
            nguyen_nhan = REASON_REASSIGN_BT  # "Không đúng đối tượng xử lý"
        else:
            nguyen_nhan = REASON_REASSIGN_TK  # "Phân công không đúng đối tượng"

        self.log(f"Bắt đầu điền Popup Phân Tuyến HĐ {shd} ({'BẢO TRÌ' if 'bao tri' in loai else 'TRIỂN KHAI'}):", "info")
        self.log(f"  • Đối tác: '{doi_tac}'", "info")
        self.log(f"  • Block (Thuộc block): '{block}'", "info")
        self.log(f"  • Nhân viên: '{nhan_vien}'", "info")
        self.log(f"  • Nguyên nhân: '{nguyen_nhan}'", "info")

        steps = [
            ("doi_tac", doi_tac),
            ("block", block),
            ("nhan_vien", nhan_vien),
            ("nguyen_nhan", nguyen_nhan),
        ]

        # Bước 1: Điền lần lượt 4 trường (cascade-aware)
        for f_key, f_val in steps:
            self._select_dialog_field(f_key, f_val)

        # Bước 2: KIỂM TRA ĐỦ FORM - ĐIỀN ĐỦ FORM RỒI MỚI BẤM CẬP NHẬT
        self.log("Kiểm tra xác nhận form đã điền đủ 4 trường...", "info")
        max_checks = 2
        for check_idx in range(max_checks):
            missing = []
            cur_summary = {}
            for f_key, f_val in steps:
                _, cfg = self._resolve_field_config(f_key)
                ctrl = self._find_dialog_control(f_key, timeout=5)
                val_now = self._get_control_value(ctrl) if ctrl else ""
                cur_summary[cfg["name"]] = val_now
                if self._is_empty_or_placeholder(val_now):
                    missing.append((f_key, f_val, cfg["name"]))

            if not missing:
                self.log(f"✅ Form đã điền đầy đủ và chính xác: {cur_summary}", "success")
                break
            else:
                m_names = [m[2] for m in missing]
                self.log(f"⚠️ Form chưa đủ, còn thiếu {m_names} (Giá trị hiện tại: {cur_summary}). Thử điền lại...", "warning")
                for f_key, f_val, _ in missing:
                    self._select_dialog_field(f_key, f_val)
                time.sleep(1.0)
        else:
            m_names = [m[2] for m in missing]
            raise RuntimeError(f"Chưa điền đủ form popup (còn thiếu {m_names}). Dừng lại không bấm Cập nhật.")

    def _click_cap_nhat_and_read_result(self):
        btn = self._wait_find(
            "//div[contains(@class,'mud-dialog')]//button[normalize-space(.)='Cập nhật' or "
            "contains(normalize-space(.),'Cập nhật')]", timeout=8)
        if not btn:
            raise RuntimeError("Không tìm thấy nút 'Cập nhật' trong popup")
        self.log("Bấm nút 'Cập nhật'...", "info")
        self._click_element(btn)

        end = time.time() + 20
        last_msg = ""
        while time.time() < end:
            time.sleep(0.8)
            try:
                # 1. Kiểm tra snackbars (thông báo nổi của MudBlazor) an toàn với StaleElement
                try:
                    snacks = self.driver.find_elements(By.XPATH, "//div[contains(@class,'mud-snackbar')]")
                    for s in self._visible(snacks):
                        try:
                            txt = (s.text or "").strip()
                            cls = (s.get_attribute("class") or "").lower()
                            if txt:
                                last_msg = txt
                                low = norm_lower(txt)
                                # Nếu snackbar báo thành công -> xác nhận thành công ngay
                                if any(k in low for k in ("thành công", "thanh cong", "hoàn tất", "hoan tat", "đã cập nhật", "da cap nhat")) or "success" in cls:
                                    self.log(f"Phát hiện thông báo thành công: '{txt}'", "success")
                                    return True, txt or "Cập nhật thành công!"
                                # Nếu snackbar báo lỗi thực sự từ hệ thống
                                if ("error" in cls or "warning" in cls or any(k in low for k in ("lỗi", "thất bại", "không thành công", "không thể"))) and not any(k in low for k in ("thành công", "thanh cong")):
                                    return False, txt
                        except (StaleElementReferenceException, Exception):
                            continue
                except (StaleElementReferenceException, Exception):
                    pass

                # 2. Kiểm tra popup mud-dialog đã đóng chưa
                # Trong MudBlazor: Popup CHỈ đóng khi Cập nhật thành công! (Nếu lỗi, popup luôn giữ nguyên để người dùng sửa)
                dialogs = []
                try:
                    d_found = self.driver.find_elements(By.XPATH, "//div[contains(@class,'mud-dialog')]")
                    dialogs = self._visible(d_found)
                except (StaleElementReferenceException, Exception):
                    # Nếu gặp lỗi DOM khi tìm dialog (popup đang bị gỡ bỏ khỏi DOM) -> coi như dialog đã đóng
                    dialogs = []

                if not dialogs:
                    self.log(f"Popup Phân tuyến đã đóng (Cập nhật thành công). Phản hồi: '{last_msg or 'Cập nhật thành công!'}'", "success")
                    return True, last_msg or "Cập nhật thành công!"

                # 3. Nếu popup vẫn mở -> kiểm tra xem có helper text báo lỗi nhập liệu không
                try:
                    err_els = self.driver.find_elements(
                        By.XPATH, "//div[contains(@class,'mud-dialog')]//*[contains(@class,'mud-input-helper-text') and contains(@class,'mud-input-error')]"
                    )
                    err_msgs = []
                    for e in self._visible(err_els):
                        try:
                            t = (e.text or "").strip()
                            if t:
                                err_msgs.append(t)
                        except (StaleElementReferenceException, Exception):
                            pass
                    if err_msgs:
                        return False, " | ".join(err_msgs)
                except (StaleElementReferenceException, Exception):
                    pass

            except StaleElementReferenceException:
                # Stale element reference trong khi theo dõi kết quả là dấu hiệu DOM đang re-render/hủy popup
                continue
            except Exception:
                continue

        # Hết timeout 20s -> kiểm tra lại lần cuối
        try:
            d_found = self.driver.find_elements(By.XPATH, "//div[contains(@class,'mud-dialog')]")
            if not self._visible(d_found):
                return True, last_msg or "Cập nhật thành công!"
        except Exception:
            return True, last_msg or "Cập nhật thành công!"

        return False, last_msg or "Hết thời gian chờ phản hồi sau khi bấm Cập nhật"

    # ------------------------------------------------------------------ public
    def process_row(self, record):
        """Tra ve (is_success, thao_tac)."""
        shd = str(record.get("SHD", "")).strip()
        loai = remove_accents(record.get("Loại Tác Vụ", "")).lower()
        if not shd:
            return False, format_assign_thao_tac(False, "Thiếu SHD")

        is_bao_tri = "bao tri" in loai
        is_trien_khai = "trien khai" in loai

        if not is_bao_tri and not is_trien_khai:
            return False, format_assign_thao_tac(
                False,
                f"Loại Tác Vụ không hợp lệ: '{record.get('Loại Tác Vụ', '')}' (chỉ hỗ trợ TRIỂN KHAI hoặc BẢO TRÌ)"
            )

        self.log(
            f"=== PHÂN CÔNG TAY HĐ {shd} (Loại: {'BẢO TRÌ' if is_bao_tri else 'TRIỂN KHAI'}) ===",
            "info"
        )

        block = str(record.get("Block Đến", "")).strip()
        nhan_vien = str(record.get("Nhân Viên Đến", "")).strip()
        if not block or not nhan_vien:
            return False, format_assign_thao_tac(False, "Thiếu Block Đến hoặc Nhân Viên Đến trên Sheet")

        self.ptc_handle = None  # reset
        ok, msg = False, "Chưa xử lý"
        last_err_str = ""

        try:
            for attempt in (1, 2):
                try:
                    # Dọn dẹp các cửa sổ phụ còn mở từ lần trước
                    if len(self.driver.window_handles) > 1:
                        self._return_to_main_form()
                    else:
                        self.driver.switch_to.window(self.main_handle)
                        self._switch_to_frame1()

                    if is_bao_tri:
                        self.log(f"--- BẮT ĐẦU QUY TRÌNH BẢO TRÌ HĐ {shd} ---", "info")
                        self._click_tab_bao_tri()
                        self._fill_nhap_hop_dong(shd)
                        self._open_cl_window()
                    else:
                        self.log(f"--- BẮT ĐẦU QUY TRÌNH TRIỂN KHAI HĐ {shd} ---", "info")
                        self._click_tab_trien_khai()
                        self._fill_dieu_kien_nhap(shd)
                        self._open_ptc_window()

                    # Cả hai loại tác vụ đều có nút Phân Tuyến và popup điền thông tin
                    self._click_phan_tuyen()

                    # Điền đủ form 4 trường và kiểm tra trước khi bấm Cập nhật
                    self._fill_and_verify_popup(record)

                    # Bấm cập nhật và đọc kết quả
                    ok, msg = self._click_cap_nhat_and_read_result()
                    self._session_broken = False
                    self.log(
                        f"Kết quả Phân tuyến HĐ {shd}: {'OK' if ok else 'LỖI'} - {msg}",
                        "success" if ok else "warning"
                    )
                    return ok, format_assign_thao_tac(ok, msg)

                except Exception as e_attempt:
                    err_str = str(e_attempt)
                    last_err_str = err_str
                    err_low = err_str.lower()

                    # Chốt chặn dự phòng: Nếu gặp lỗi stale element reference (do DOM thay đổi sau khi bấm Cập nhật),
                    # kiểm tra xem popup đã đóng chưa. Nếu popup đã đóng thì ca vụ đã được chuyển thành công!
                    if "stale element" in err_low:
                        try:
                            time.sleep(1)
                            d_found = self.driver.find_elements(By.XPATH, "//div[contains(@class,'mud-dialog')]")
                            if not self._visible(d_found):
                                self.log(f"Phát hiện popup đã đóng sau lỗi stale element -> Xác nhận Phân công thành công cho HĐ {shd}!", "success")
                                ok = True
                                msg = "Cập nhật thành công!"
                                self._session_broken = False
                                return True, format_assign_thao_tac(True, msg)
                        except Exception:
                            pass

                    # Nhận diện lỗi do phiên con Inside New V5 (partner.fpt.net) hết hạn ngầm hoặc chưa tải được form
                    is_session_ui_err = any(k in err_low for k in (
                        "không tìm thấy ô 'nhập hợp đồng'",
                        "khong tim thay o nhap shd",
                        "không tìm thấy tab",
                        "không thể click tab",
                        "không tìm thấy nút 'xem cl'",
                        "khong tim thay nut 'phieu thi cong'",
                        "no such frame",
                        "unable to switch to frame",
                    ))

                    if is_session_ui_err and attempt == 1:
                        self.log(
                            f"🔄 Phát hiện phiên Inside New V5 hết hạn ngầm hoặc chưa tải giao diện ({err_str[:80]}). "
                            f"Đang làm mới đăng nhập SSO và thử lại ngay cho HĐ {shd}...",
                            "warning"
                        )
                        try:
                            import core_login as _cl
                            _cl.invalidate_session(log_cb=self.log_cb)
                        except Exception:
                            pass
                        try:
                            self._perform_auto_login()
                            self.navigate_to_assign_page()
                            continue
                        except Exception as e_relogin:
                            self.log(f"Không thể đăng nhập lại tự động: {e_relogin}", "error")
                            self._session_broken = True
                            break
                    else:
                        if is_session_ui_err:
                            self._session_broken = True
                        raise e_attempt

            return False, format_assign_thao_tac(False, last_err_str[:80])

        except Exception as e:
            err_str = str(e)
            self.log(f"Lỗi Phân Công Tay HĐ {shd}: {err_str}", "error")
            return False, format_assign_thao_tac(False, err_str[:80])

        finally:
            if ok:
                # Chỉ đóng cửa sổ phụ khi ĐÃ CẬP NHẬT THÀNH CÔNG
                try:
                    for h in list(self.driver.window_handles):
                        if h != self.main_handle:
                            self.driver.switch_to.window(h)
                            self.driver.close()
                except Exception:
                    pass
                try:
                    self.driver.switch_to.window(self.main_handle)
                    self._switch_to_frame1()
                except Exception as e_back:
                    self.log(f"Không quay lại được form chính: {e_back}", "warning")
            else:
                # NẾU CÓ LỖI: GIỮ NGUYÊN TAB ĐỂ NGƯỜI DÙNG QUAN SÁT VÀ DEBUG
                self.log("⚠️ Quá trình chưa hoàn tất thành công. Giữ nguyên tab để kiểm tra màn hình.", "warning")


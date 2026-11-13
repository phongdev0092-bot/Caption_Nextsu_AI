"""
COMPONENT BACKEND: AUTO BYPASS MYBAE
Google Sheet GID 1795923064 | Cột: ID | Tác Vụ | Email | MSNV | Account Inside | SHD |
Nguyên Nhân 1 | Hình ảnh | Ngày Cập Nhật | Kết Quả | Thao Tác

Quy trình:
  Inside New V5 >> Hỗ trợ kỹ thuật >> Thông tin chung >> tab BẢO TRÌ >> nhập SHD vào ô
  "Nhập hợp đồng" >> bấm "Xem CL" (mở cửa sổ riêng, giống Phân Công Tay - Bảo Trì) >>
  bấm "Xem thêm" và cuộn xuống >> mục "Nguyên nhân chưa nghiệm thu MyBAE" chọn đúng
  giá trị cột "Nguyên Nhân 1" trên Sheet >> bấm "Cập nhật" cuối trang.

Kết quả ghi lại Sheet:
  - Thành công : Kết Quả = "Đã xử lý", Thao Tác = "Thành công"
  - Có lỗi     : Thao Tác = "Không thành công : <lý do>" (Kết Quả giữ nguyên để có thể chạy lại)
"""
import re
import time

import pandas as pd
from selenium.webdriver.common.by import By

from inside_assign import InsideAssignAutomation, clean_str
from inside_cls import (
    DEFAULT_SHEET_ID,
    normalize_nfc,
    norm_lower,
    remove_accents,
)

GID_MYBAE = "1795923064"
TASK_NAME = "Bypass MyBAE"
KET_QUA_DONE = "Đã xử lý"
THAO_TAC_OK = "Thành công"

_COLUMN_MAP = {
    "id": "ID",
    "tac vu": "Tác Vụ",
    "email": "Email",
    "msnv": "MSNV",
    "account inside": "Account Inside",
    "shd": "SHD",
    "nguyen nhan 1": "Nguyên Nhân 1",
    "hinh anh": "Hình ảnh",
    "ngay cap nhat": "Ngày Cập Nhật",
    "ket qua": "Kết Quả",
    "thao tac": "Thao Tác",
}


def _canonical_column(raw_name):
    key = re.sub(r"\s+", " ", remove_accents(raw_name))
    if key in _COLUMN_MAP:
        return _COLUMN_MAP[key]
    if "hinh anh" in key:
        return "Hình ảnh"
    if "nguyen nhan" in key or "ly do" in key:
        return "Nguyên Nhân 1"
    if "ket qua" in key:
        return "Kết Quả"
    if "thao tac" in key or "ghi chu" in key:
        return "Thao Tác"
    if "ngay" in key or "thoi gian" in key:
        return "Ngày Cập Nhật"
    if "tac vu" in key:
        return "Tác Vụ"
    if key == "shd" or "hop dong" in key:
        return "SHD"
    if "email" in key:
        return "Email"
    if "account" in key:
        return "Account Inside"
    if "msnv" in key:
        return "MSNV"
    return None


def is_final_row(record):
    """
    Dòng đã xử lý xong. Kết Quả luôn = 'Đã xử lý' (kể cả lỗi) nên phân biệt bằng Thao Tác:
    - Thao Tác báo thành công  -> xong
    - Thao Tác báo lỗi         -> chưa xong (được phép chạy lại)
    - Thao Tác trống nhưng Kết Quả = 'Đã xử lý' (nhập tay) -> xong
    """
    tt = norm_lower(record.get("Thao Tác", ""))
    if tt:
        return "thành công" in tt and "không" not in tt
    return norm_lower(record.get("Kết Quả", "")) == norm_lower(KET_QUA_DONE)


def format_mybae_thao_tac(is_success, detail=""):
    if is_success:
        return THAO_TAC_OK
    clean = re.sub(r"^không\s+thành\s+công\s*[:\-]?", "", str(detail or "").strip(), flags=re.IGNORECASE).strip()
    return f"Không thành công : {clean or 'Không xác định'}"


def fetch_sheet_data(sheet_id=DEFAULT_SHEET_ID, gid=GID_MYBAE):
    url = (f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq"
           f"?tqx=out:csv&gid={gid}&_t={int(time.time() * 1000)}")
    try:
        df = pd.read_csv(url, encoding="utf-8", dtype=str).fillna("")
        col_indices = {}
        mapping = {}
        for idx, c in enumerate(df.columns):
            canon = _canonical_column(c)
            mapping[c] = canon
            if canon == "SHD":
                col_indices["shd"] = idx
            elif canon == "Thao Tác":
                col_indices["thao_tac"] = idx
            elif canon == "Kết Quả":
                col_indices["ket_qua"] = idx
            elif canon == "Ngày Cập Nhật":
                col_indices["ngay"] = idx

        records = []
        for raw in df.to_dict(orient="records"):
            rec = {}
            for k, v in raw.items():
                val = normalize_nfc(v)
                if val.lower() == "nan":
                    val = ""
                rec[normalize_nfc(k)] = val
                canon = mapping.get(k)
                if canon:
                    rec[canon] = val
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
        return {"status": "error", "message": f"Không thể đọc Google Sheet Bypass MyBAE: {e}", "records": []}


# ---------------------------------------------------------------------- JS helpers
_JS_PRELUDE = r"""
var norm = function(s) {
  return (s || '').normalize('NFD').replace(/[\u0300-\u036f]/g, '')
    .replace(/đ/g, 'd').replace(/Đ/g, 'd').toLowerCase().replace(/\s+/g, ' ').trim();
};
var vis = function(e) {
  return !!(e && (e.offsetWidth || e.offsetHeight || e.getClientRects().length));
};
"""

# Tìm ô điều khiển nằm cạnh nhãn "Nguyên nhân chưa nghiệm thu MyBAE"
_JS_FIND_REASON_CONTROL = _JS_PRELUDE + r"""
var all = Array.from(document.querySelectorAll('td,th,label,span,div,p,b,strong,dt'));
var strict = [], loose = [];
all.forEach(function(e) {
  var t = norm(e.innerText || e.textContent);
  if (!t || t.length > 80 || !vis(e)) return;
  var c = t.replace(/ /g, '');
  if (c.indexOf('nghiemthu') === -1) return;
  if (c.indexOf('mybao') !== -1 || c.indexOf('mybae') !== -1) strict.push({e: e, n: t.length});
  else if (c.indexOf('chuanghiemthu') !== -1) loose.push({e: e, n: t.length});
});
var pool = strict.length ? strict : loose;
if (!pool.length) return null;
pool.sort(function(a, b) { return a.n - b.n; });
var lab = pool[0].e;
var node = lab;
for (var i = 0; i < 6 && node; i++) {
  var parent = node.parentElement;
  if (!parent) break;
  var ctrls = Array.from(parent.querySelectorAll(
    'select, .mud-select, .mud-input-control, input:not([type=hidden]), .select2-container, .selectize-control'));
  ctrls = ctrls.filter(function(c) {
    return !c.contains(lab) && !lab.contains(c) &&
      (lab.compareDocumentPosition(c) & Node.DOCUMENT_POSITION_FOLLOWING) && vis(c);
  });
  if (ctrls.length) return ctrls[0];
  node = parent;
}
return null;
"""

# Tìm nút "Xem thêm"
_JS_FIND_XEM_THEM = _JS_PRELUDE + r"""
var all = Array.from(document.querySelectorAll('button, a, span, div, p'));
var cands = [];
all.forEach(function(e) {
  var t = norm(e.innerText || e.textContent);
  if (!t || t.length > 20 || t.indexOf('xem them') !== 0 || !vis(e)) return;
  var pri = (e.tagName === 'BUTTON') ? 0 : (e.tagName === 'A' ? 1 : 2);
  cands.push({e: e, pri: pri, n: t.length});
});
if (!cands.length) return null;
cands.sort(function(a, b) { return a.pri - b.pri || a.n - b.n; });
return cands[0].e;
"""

# Tìm nút "Cập nhật" ở cuối trang (cạnh "Kết quả xử lý", mục "Cập nhật kết quả xử lý của phiếu")
_JS_FIND_UPDATE_BTN = _JS_PRELUDE + r"""
var btns = Array.from(document.querySelectorAll('button, a, input[type=button], input[type=submit]'))
  .filter(function(b) {
    var t = norm(b.innerText || b.value || b.textContent);
    return t === 'cap nhat' && vis(b);
  });
if (!btns.length) return null;
for (var i = 0; i < btns.length; i++) {
  var n = btns[i];
  for (var k = 0; k < 5 && n; k++, n = n.parentElement) {
    var t = norm(n.innerText || n.textContent);
    if (t.length < 500 && t.indexOf('ket qua xu ly') !== -1) return btns[i];
  }
}
return btns[btns.length - 1];
"""

_JS_FEEDBACK = _JS_PRELUDE + r"""
var sel = '.mud-snackbar,.toast,.toast-message,.swal2-popup,.noty_body,.notyf__toast,' +
          '.jconfirm-box,.ajs-message,#toast-container > div';
return Array.from(document.querySelectorAll(sel)).filter(vis).map(function(e) {
  return {
    text: (e.innerText || e.textContent || '').trim(),
    cls: ((e.className || '') + ' ' + (e.parentElement ? e.parentElement.className : '')).toString()
  };
});
"""

_JS_CLICK_SWAL_CONFIRM = r"""
var b = document.querySelector('.swal2-confirm, .jconfirm-buttons .btn');
if (b && (b.offsetWidth || b.offsetHeight)) { b.click(); return true; }
return false;
"""

_PLACEHOLDER_OPTIONS = ("khongchon", "chon", "chuachon")


def _pick_option(texts, target):
    """Trả về index của lựa chọn khớp nhất với target (hoặc -1)."""
    t = clean_str(target)
    if not t:
        return -1
    cleaned = [clean_str(x) for x in texts]
    for i, c in enumerate(cleaned):
        if c and c == t:
            return i
    for i, c in enumerate(cleaned):
        if c and c not in _PLACEHOLDER_OPTIONS and (t in c or c in t):
            return i
    words = [clean_str(w) for w in str(target).split() if len(w) >= 3]
    if words:
        for i, c in enumerate(cleaned):
            if c and c not in _PLACEHOLDER_OPTIONS and all(w in c for w in words):
                return i
    return -1


class InsideMyBaeAutomation(InsideAssignAutomation):
    """Kế thừa luồng điều hướng + tab Bảo Trì + 'Xem CL' từ InsideAssignAutomation."""

    def log(self, msg, level="info"):
        super().log(f"[MyBAE] {msg}", level)

    # ------------------------------------------------------------------ helpers
    def _run_js(self, script):
        try:
            return self.driver.execute_script(script)
        except Exception:
            return None

    def _in_all_contexts(self, finder, timeout=15):
        """
        Chạy finder() ở document hiện tại rồi lần lượt các iframe (1 cấp) của CỬA SỔ HIỆN TẠI.
        Khi tìm thấy sẽ giữ nguyên context frame chứa phần tử để thao tác tiếp.
        """
        end = time.time() + timeout
        while True:
            try:
                self.driver.switch_to.default_content()
            except Exception:
                pass
            res = finder()
            if res is not None:
                return res
            try:
                n_frames = len(self.driver.find_elements(By.TAG_NAME, "iframe"))
            except Exception:
                n_frames = 0
            for i in range(n_frames):
                try:
                    self.driver.switch_to.default_content()
                    self.driver.switch_to.frame(i)
                    res = finder()
                    if res is not None:
                        return res
                except Exception:
                    continue
            if time.time() >= end:
                break
            time.sleep(0.7)
        try:
            self.driver.switch_to.default_content()
        except Exception:
            pass
        return None

    def _scroll_to_bottom(self):
        try:
            self.driver.switch_to.default_content()
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        except Exception:
            pass

    # ------------------------------------------------------------------ cửa sổ Checklist Bảo Trì
    def _expand_more(self):
        """Bấm 'Xem thêm' và cuộn xuống cuối trang để lộ phần 'Thông tin báo trì'."""
        btn = self._in_all_contexts(lambda: self._run_js(_JS_FIND_XEM_THEM), timeout=8)
        if btn:
            self.log("Bấm nút 'Xem thêm' để mở rộng form...", "info")
            self._click_element(btn)
            time.sleep(1.5)
        else:
            self.log("Không thấy nút 'Xem thêm' (có thể form đã mở rộng sẵn), tiếp tục...", "warning")
        self._scroll_to_bottom()
        time.sleep(0.8)

    def _read_select_value(self, sel_el):
        try:
            return (self.driver.execute_script(
                "var s=arguments[0]; var o=s.options[s.selectedIndex]; return o ? o.textContent.trim() : '';",
                sel_el) or "").strip()
        except Exception:
            return ""

    def _select_native(self, sel_el, reason):
        texts = self.driver.execute_script(
            "return Array.from(arguments[0].options).map(function(o){return (o.textContent||'').trim();});",
            sel_el) or []
        idx = _pick_option(texts, reason)
        if idx < 0:
            raise RuntimeError(f"Không tìm thấy nguyên nhân '{reason}' trong danh sách. Các tùy chọn: {texts[:15]}")
        self.driver.execute_script("""
            var s = arguments[0]; s.selectedIndex = arguments[1];
            s.dispatchEvent(new Event('input',  {bubbles: true}));
            s.dispatchEvent(new Event('change', {bubbles: true}));
        """, sel_el, idx)
        time.sleep(0.8)
        return texts[idx]

    def _select_custom(self, ctrl, reason):
        """Dropdown dạng MudBlazor / custom: mở list rồi bấm vào mục khớp."""
        clickable = ctrl.find_elements(
            By.XPATH, ".//input | .//div[contains(@class,'mud-select-input')] | .//div[contains(@class,'mud-input')]")
        target_el = clickable[0] if clickable else ctrl
        self._click_element(target_el)
        time.sleep(0.6)
        items = self._wait_popover_items(timeout=8)
        if not items:
            self._click_element(target_el)
            time.sleep(1.0)
            items = self._wait_popover_items(timeout=8)
        if not items:
            raise RuntimeError("Dropdown 'Nguyên nhân chưa nghiệm thu MyBAE' không có tùy chọn nào")
        texts = [(it.text or "").strip() for it in items]
        idx = _pick_option(texts, reason)
        if idx < 0:
            raise RuntimeError(f"Không tìm thấy nguyên nhân '{reason}' trong danh sách. Các tùy chọn: {texts[:15]}")
        chosen = texts[idx]
        self._click_element(items[idx])
        time.sleep(1.0)
        return chosen

    def _select_nghiem_thu_reason(self, reason):
        self.log(f"Chọn 'Nguyên nhân chưa nghiệm thu MyBAE' = '{reason}'...", "info")
        ctrl = self._in_all_contexts(lambda: self._run_js(_JS_FIND_REASON_CONTROL), timeout=15)
        if not ctrl:
            raise RuntimeError("Không tìm thấy ô 'Nguyên nhân chưa nghiệm thu MyBAE' trên cửa sổ Checklist")
        try:
            self.driver.execute_script("arguments[0].scrollIntoView({block:'center'});", ctrl)
        except Exception:
            pass
        time.sleep(0.4)

        sel_el = ctrl if (ctrl.tag_name or "").lower() == "select" else None
        if sel_el is None:
            inner = ctrl.find_elements(By.XPATH, ".//select")
            if inner:
                sel_el = inner[0]

        if sel_el is not None:
            chosen = self._select_native(sel_el, reason)
            cur = self._read_select_value(sel_el)
        else:
            chosen = self._select_custom(ctrl, reason)
            cur = self._get_control_value(ctrl)

        if self._is_empty_or_placeholder(cur) or clean_str(cur) in _PLACEHOLDER_OPTIONS:
            raise RuntimeError(f"Chọn nguyên nhân '{reason}' nhưng ô vẫn đang trống/'Không chọn'")
        self.log(f"Đã chọn nguyên nhân: '{chosen}' (giá trị hiện tại: '{cur}').", "success")

    def _collect_feedback(self):
        """Gom thông báo (toast/snackbar/swal) ở document chính và các iframe của cửa sổ hiện tại."""
        out = []
        try:
            self.driver.switch_to.default_content()
            out.extend(self._run_js(_JS_FEEDBACK) or [])
            frames = self.driver.find_elements(By.TAG_NAME, "iframe")
            for i in range(len(frames)):
                try:
                    self.driver.switch_to.default_content()
                    self.driver.switch_to.frame(i)
                    out.extend(self._run_js(_JS_FEEDBACK) or [])
                except Exception:
                    continue
        except Exception:
            pass
        finally:
            try:
                self.driver.switch_to.default_content()
            except Exception:
                pass
        return out

    @staticmethod
    def _classify_message(text, cls=""):
        low = remove_accents(text)
        cl = (cls or "").lower()
        if any(k in cl for k in ("error", "danger", "swal2-icon-error")) or any(
                k in low for k in ("loi", "that bai", "khong thanh cong", "khong the", "error", "failed",
                                   "vui long", "khong hop le")):
            return "error"
        if any(k in cl for k in ("success",)) or any(
                k in low for k in ("thanh cong", "success", "da cap nhat", "cap nhat xong")):
            return "success"
        return "unknown"

    def _click_update_and_read_result(self):
        btn = self._in_all_contexts(lambda: self._run_js(_JS_FIND_UPDATE_BTN), timeout=12)
        if not btn:
            raise RuntimeError("Không tìm thấy nút 'Cập nhật' ở cuối trang")
        self.log("Bấm nút 'Cập nhật' ở cuối trang...", "info")
        self._click_element(btn)

        end = time.time() + 20
        last_msg = ""
        while time.time() < end:
            time.sleep(1)
            # Hộp thoại alert/confirm của trình duyệt
            try:
                alert = self.driver.switch_to.alert
                a_txt = (alert.text or "").strip()
                alert.accept()
                last_msg = a_txt or last_msg
                kind = self._classify_message(a_txt)
                if kind == "error":
                    return False, a_txt
                if kind == "success":
                    return True, a_txt
                continue
            except Exception:
                pass

            for fb in self._collect_feedback():
                txt = (fb.get("text") or "").strip()
                if not txt:
                    continue
                last_msg = txt
                kind = self._classify_message(txt, fb.get("cls", ""))
                if kind == "error":
                    return False, txt
                if kind == "success":
                    return True, txt

            # Hộp thoại xác nhận SweetAlert (nếu có) -> bấm OK
            try:
                self.driver.switch_to.default_content()
                self.driver.execute_script(_JS_CLICK_SWAL_CONFIRM)
            except Exception:
                pass

        if last_msg:
            return False, f"Phản hồi không rõ ràng: {last_msg[:80]}"
        self.log("Không thấy thông báo phản hồi sau khi bấm Cập nhật (không có lỗi) - coi là thành công.", "warning")
        return True, "Đã bấm Cập nhật (không có thông báo lỗi)"

    def ensure_driver_alive(self):
        """Kiểm tra và tự động khôi phục driver nếu Chrome bị ngắt kết nối hoặc crash."""
        alive = False
        try:
            if self.driver:
                _ = self.driver.window_handles
                alive = True
        except Exception:
            alive = False

        if not alive:
            self.log("Phát hiện kết nối Chrome bị đóng hoặc mất phiên. Đang dọn dẹp và kết nối lại...", "warning")
            try:
                if self.driver:
                    self.driver.quit()
            except Exception:
                pass
            self.driver = None
            import core_login
            core_login.clean_profile_locks_and_orphans(log_cb=self.log)
            self.init_driver()
            self.navigate_to_assign_page()
            self.log("Đã kết nối lại trình duyệt và sẵn sàng xử lý tiếp!", "success")

    # ------------------------------------------------------------------ public
    def process_row(self, record):
        """Trả về (is_success, thao_tac)."""
        shd = str(record.get("SHD", "")).strip()
        reason = str(record.get("Nguyên Nhân 1", "")).strip()
        if not shd:
            return False, format_mybae_thao_tac(False, "Thiếu SHD")
        if not reason:
            return False, format_mybae_thao_tac(False, "Thiếu Nguyên Nhân 1 trên Sheet")

        self.ensure_driver_alive()

        self.log(f"=== BYPASS MYBAE HĐ {shd} | Nguyên nhân: '{reason}' ===", "info")
        ok, msg = False, "Chưa xử lý"
        try:
            if len(self.driver.window_handles) > 1:
                self._return_to_main_form()
            else:
                self.driver.switch_to.window(self.main_handle)
                self._switch_to_frame1()

            self._click_tab_bao_tri()
            self._fill_nhap_hop_dong(shd)
            self._open_cl_window()

            self._expand_more()
            self._select_nghiem_thu_reason(reason)
            ok, msg = self._click_update_and_read_result()

            self.log(f"Kết quả Bypass MyBAE HĐ {shd}: {'OK' if ok else 'LỖI'} - {msg}",
                     "success" if ok else "warning")
            return ok, format_mybae_thao_tac(ok, msg)

        except Exception as e:
            self.log(f"Lỗi Bypass MyBAE HĐ {shd}: {e}", "error")
            err_str = str(e)
            if "HTTPConnectionPool" in err_str or "Max retries exceeded" in err_str or "refused" in err_str:
                try:
                    if self.driver:
                        self.driver.quit()
                except Exception:
                    pass
                self.driver = None
            return False, format_mybae_thao_tac(False, err_str[:100])

        finally:
            if ok:
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
                # Giữ nguyên tab khi lỗi để quan sát (tab sẽ tự đóng ở dòng kế tiếp)
                self.log("Chưa hoàn tất thành công. Giữ nguyên tab để kiểm tra màn hình.", "warning")

"""
Module 4 - Thực thi Hoàn Tất PBT (Xác Minh Thông Tin) trên giao diện mới FOX-ERP.

An toàn mặc định:
- DRY-RUN mặc định BẬT (dry_run=True): chỉ chạy kiểm tra điều kiện và mô phỏng bước 4,
  tuyệt đối KHÔNG bấm 'Thay đổi tình trạng', 'Cập nhật' hay 'Xác nhận'.
- Idempotent: phiếu đã 'Đã xử lý' / 'Đã hoàn tất' sẽ bỏ qua an toàn.
- Chạy thật (dry_run=False) chỉ thực thi khi Module 3 trả về du_dieu_kien=True:
  1. Bấm 'Thay đổi tình trạng' -> chọn 'Đã xử lý' -> mở popup 'Xác nhận chuyển tình trạng "Đã xử lý"'.
  2. Card 'Thông tin bảo trì' (Điều kiện 3):
     Nếu 'Nguyên nhân chưa cài đặt Hi FPT' hoặc 'Nguyên nhân chưa nghiệm thu Mỹ Bảo' đang là 'Không chọn':
     -> bấm cây bút ✏️ -> chọn:
        - Nguyên nhân chưa cài đặt Hi FPT   >> Không gặp chủ hợp đồng
        - Nguyên nhân chưa nghiệm thu Mỹ Bảo >> Không kết nối được wifi khách hàng
     -> bấm 'Cập nhật' trong card 'Thông tin bảo trì'.
  3. Card 'Thông tin dịch vụ':
     -> bấm cây bút ✏️ -> mở sub-popup 'Thông tin dịch vụ'
     -> chọn dropdown đầu tiên 'Internet' -> bấm '+ Thêm'
     -> nếu 'Phần tử lỗi' trống/Không chọn -> chọn 'Khách hàng'
     -> chọn 'Nguyên nhân lỗi' = 'Đến nhà khách hàng kiểm tra KH yêu cầu hủy hợp đồng'
     -> bấm 'Cập nhật' trong sub-popup 'Thông tin dịch vụ'.
  4. Bấm nút 'Xác nhận' màu xanh ở đáy popup 'Xác nhận chuyển tình trạng "Đã xử lý"'.
  5. Kiểm tra xác nhận lại trạng thái phiếu trên giao diện đã chuyển sang 'Đã xử lý'.
"""

from dataclasses import asdict, dataclass, field
import time
from typing import Callable, Dict, List, Optional

from .config import AutoHoanTatSettings, load_settings
from .mod1_auth import FeatureDisabledError, InsideSession
from .mod2_navigator import NavigationContext, _read_footer_ticket_status
from .mod3_validator import is_already_completed
from .sheet_reader import normalize_nfc

HI_FPT_TARGET = "Không gặp chủ hợp đồng"
MY_BAO_TARGET = "Không kết nối được wifi khách hàng"
DICH_VU_TARGET = "Internet"
PHAN_TU_LOI_TARGET = "Khách hàng"
NGUYEN_NHAN_LOI_TARGET = "Đến nhà khách hàng kiểm tra KH yêu cầu hủy hợp đồng"
HUONG_XU_LY_FALLBACK_PREFIX = "Tạo SR để DVKH hỗ trợ"

STATUS_SUCCESS = "SUCCESS"
STATUS_DRY_RUN_READY = "DRY_RUN_READY"
STATUS_NOT_ELIGIBLE = "NOT_ELIGIBLE"
STATUS_SKIPPED_ALREADY_DONE = "SKIPPED_ALREADY_DONE"
STATUS_ERROR = "ERROR"


@dataclass
class ExecutionResult:
    ma_phieu: str
    tac_vu: str
    loai: str
    mode: str  # "DRY_RUN" | "REAL"
    status: str  # SUCCESS | DRY_RUN_READY | NOT_ELIGIBLE | SKIPPED_ALREADY_DONE | ERROR
    ket_qua: str
    steps_performed: List[str] = field(default_factory=list)
    post_status: str = ""
    elapsed_ms: int = 0

    def to_dict(self) -> Dict:
        return asdict(self)


def _emit(log_cb: Optional[Callable[[str, str], None]], msg: str, level: str = "info") -> None:
    if log_cb:
        try:
            log_cb(msg, level)
        except Exception:
            pass


_JS_CLICK_BUTTON_BY_TEXT = """
(function(targetText, withinModalOnly) {
  function norm(s) { return String(s || '').replace(/\\s+/g, ' ').trim().toLowerCase(); }
  function isVis(el) {
    if (!el) return false;
    var st = window.getComputedStyle(el);
    if (st.display === 'none' || st.visibility === 'hidden' || st.opacity === '0') return false;
    var r = el.getBoundingClientRect();
    return r.width > 0 && r.height > 0;
  }
  var root = document;
  if (withinModalOnly) {
    var modals = Array.from(document.querySelectorAll('[role="dialog"], .modal, .mud-dialog, .ant-modal, .el-dialog'))
      .filter(isVis);
    if (modals.length > 0) root = modals[modals.length - 1];
  }
  var want = norm(targetText);
  var btns = Array.from(root.querySelectorAll('button, [role="button"], [role="menuitem"], li, a, .dropdown-item'))
    .filter(isVis);
  // Ưu tiên khớp chính xác trước, sau đó mới khớp contains
  for (var i = 0; i < btns.length; i++) {
    var t = norm(btns[i].innerText || btns[i].textContent);
    if (t === want) {
      btns[i].scrollIntoView({block: 'center'});
      btns[i].click();
      return { clicked: true, text: t };
    }
  }
  for (var j = 0; j < btns.length; j++) {
    var t2 = norm(btns[j].innerText || btns[j].textContent);
    if (t2 && t2.indexOf(want) !== -1 && t2.length <= want.length + 20) {
      btns[j].scrollIntoView({block: 'center'});
      btns[j].click();
      return { clicked: true, text: t2 };
    }
  }
  return { clicked: false, text: '' };
})(arguments[0], arguments[1]);
"""

_JS_CHECK_POPUP_VISIBLE = """
(function(titleKeyword) {
  function norm(s) { return String(s || '').replace(/\\s+/g, ' ').trim().toLowerCase(); }
  function isVis(el) {
    if (!el) return false;
    var st = window.getComputedStyle(el);
    if (st.display === 'none' || st.visibility === 'hidden' || st.opacity === '0') return false;
    var r = el.getBoundingClientRect();
    return r.width > 0 && r.height > 0;
  }
  var want = norm(titleKeyword);
  var modals = Array.from(document.querySelectorAll('[role="dialog"], .modal, .mud-dialog, .ant-modal, .el-dialog, div'))
    .filter(function(el) {
      if (!isVis(el)) return false;
      var t = norm(el.innerText || el.textContent);
      return t.indexOf(want) !== -1 && t.length < 6000;
    });
  return modals.length > 0;
})(arguments[0]);
"""

_JS_READ_BAO_TRI_CARD = """
(function() {
  function norm(s) { return String(s || '').replace(/\\s+/g, ' ').trim(); }
  function isVis(el) {
    if (!el) return false;
    var st = window.getComputedStyle(el);
    if (st.display === 'none' || st.visibility === 'hidden' || st.opacity === '0') return false;
    var r = el.getBoundingClientRect();
    return r.width > 0 && r.height > 0;
  }
  var modals = Array.from(document.querySelectorAll('[role="dialog"], .modal, .mud-dialog, .ant-modal, .el-dialog'))
    .filter(isVis);
  var root = modals.length > 0 ? modals[modals.length - 1] : document;
  var txt = norm(root.innerText || root.textContent);
  var hiMatch = txt.match(/Nguyên nhân chưa cài đặt Hi FPT\\s*:?\\s*([^\\n]+)/i);
  var mbMatch = txt.match(/Nguyên nhân chưa nghiệm thu Mỹ Bảo\\s*:?\\s*([^\\n]+)/i);
  var hiVal = hiMatch ? norm(hiMatch[1]).split(/Nguyên nhân|Mối nối|Độ ưu tiên/i)[0].trim() : '';
  var mbVal = mbMatch ? norm(mbMatch[1]).split(/Nguyên nhân|Mối nối|Độ ưu tiên/i)[0].trim() : '';
  return { hi_fpt: hiVal, my_bao: mbVal, raw: txt.slice(0, 1000) };
})();
"""

_JS_CLICK_CARD_PENCIL = """
(function(cardTitle) {
  function norm(s) { return String(s || '').replace(/\\s+/g, ' ').trim().toLowerCase(); }
  function isVis(el) {
    if (!el) return false;
    var st = window.getComputedStyle(el);
    if (st.display === 'none' || st.visibility === 'hidden' || st.opacity === '0') return false;
    var r = el.getBoundingClientRect();
    return r.width > 0 && r.height > 0;
  }
  var modals = Array.from(document.querySelectorAll('[role="dialog"], .modal, .mud-dialog, .ant-modal, .el-dialog'))
    .filter(isVis);
  var root = modals.length > 0 ? modals[modals.length - 1] : document;
  var want = norm(cardTitle);

  var headers = Array.from(root.querySelectorAll('div, header, section, h3, h4, h5, span')).filter(function(el) {
    if (!isVis(el)) return false;
    var t = norm(el.innerText || el.textContent);
    return t === want || (t.indexOf(want) !== -1 && t.length <= want.length + 12);
  });

  for (var i = 0; i < headers.length; i++) {
    var container = headers[i].parentElement;
    for (var depth = 0; depth < 4 && container; depth++) {
      var pencil = container.querySelector('button svg, [role="button"] svg, i[class*="edit"], i[class*="pencil"], button[title*="Sửa"], button[aria-label*="Sửa"], .fa-pencil, .fa-edit, svg[class*="pencil"], svg[class*="edit"]');
      if (pencil && isVis(pencil)) {
        var target = pencil.closest('button, [role="button"], a') || pencil;
        target.scrollIntoView({block: 'center'});
        target.click();
        return { clicked: true, card: cardTitle };
      }
      container = container.parentElement;
    }
  }
  return { clicked: false, card: cardTitle };
})(arguments[0]);
"""

_JS_SELECT_DROPDOWN_BY_LABEL = """
(function(labelText, optionText) {
  function norm(s) { return String(s || '').replace(/\\s+/g, ' ').trim().toLowerCase(); }
  function isVis(el) {
    if (!el) return false;
    var st = window.getComputedStyle(el);
    if (st.display === 'none' || st.visibility === 'hidden' || st.opacity === '0') return false;
    var r = el.getBoundingClientRect();
    return r.width > 0 && r.height > 0;
  }
  var modals = Array.from(document.querySelectorAll('[role="dialog"], .modal, .mud-dialog, .ant-modal, .el-dialog'))
    .filter(isVis);
  var root = modals.length > 0 ? modals[modals.length - 1] : document;
  var wantLabel = norm(labelText);
  var wantOpt = norm(optionText);

  var labels = Array.from(root.querySelectorAll('label, div, span')).filter(function(el) {
    if (!isVis(el)) return false;
    var t = norm(el.innerText || el.textContent);
    return t === wantLabel || (t.indexOf(wantLabel) !== -1 && t.length <= wantLabel.length + 15);
  });

  for (var i = 0; i < labels.length; i++) {
    var box = labels[i].parentElement;
    for (var d = 0; d < 3 && box; d++) {
      var sel = box.querySelector('select');
      if (sel && isVis(sel)) {
        var opts = Array.from(sel.options || []);
        for (var k = 0; k < opts.length; k++) {
          if (norm(opts[k].text).indexOf(wantOpt) !== -1) {
            sel.value = opts[k].value;
            sel.dispatchEvent(new Event('change', { bubbles: true }));
            return { ok: true, mode: 'native_select', selected: opts[k].text };
          }
        }
      }
      var custom = box.querySelector('[role="combobox"], .ant-select-selector, .mud-select-input, input[readonly], button[aria-haspopup]');
      if (custom && isVis(custom)) {
        custom.click();
        return { ok: true, mode: 'opened_custom_dropdown', selected: '' };
      }
      box = box.parentElement;
    }
  }
  return { ok: false, mode: 'not_found', selected: '' };
})(arguments[0], arguments[1]);
"""

_JS_CLICK_DROPDOWN_OPTION = """
(function(optionText) {
  function norm(s) { return String(s || '').replace(/\\s+/g, ' ').trim().toLowerCase(); }
  function isVis(el) {
    if (!el) return false;
    var st = window.getComputedStyle(el);
    if (st.display === 'none' || st.visibility === 'hidden' || st.opacity === '0') return false;
    var r = el.getBoundingClientRect();
    return r.width > 0 && r.height > 0;
  }
  var want = norm(optionText);
  var items = Array.from(document.querySelectorAll('[role="option"], .ant-select-item-option, .mud-list-item, li, .dropdown-item'))
    .filter(isVis);
  for (var i = 0; i < items.length; i++) {
    var t = norm(items[i].innerText || items[i].textContent);
    if (t === want || (t && t.indexOf(want) !== -1)) {
      items[i].scrollIntoView({block: 'center'});
      items[i].click();
      return { clicked: true, text: t };
    }
  }
  return { clicked: false, text: '' };
})(arguments[0]);
"""

_JS_SELECT_TABLE_CELL_DROPDOWN = """
(function(colHeaderText, optionText) {
  function norm(s) { return String(s || '').replace(/\\s+/g, ' ').trim().toLowerCase(); }
  function isVis(el) {
    if (!el) return false;
    var st = window.getComputedStyle(el);
    if (st.display === 'none' || st.visibility === 'hidden' || st.opacity === '0') return false;
    var r = el.getBoundingClientRect();
    return r.width > 0 && r.height > 0;
  }
  var modals = Array.from(document.querySelectorAll('[role="dialog"], .modal, .mud-dialog, .ant-modal, .el-dialog'))
    .filter(isVis);
  var root = modals.length > 0 ? modals[modals.length - 1] : document;
  var wantCol = norm(colHeaderText);
  var wantOpt = norm(optionText);

  var tables = Array.from(root.querySelectorAll('table')).filter(isVis);
  for (var t = 0; t < tables.length; t++) {
    var ths = Array.from(tables[t].querySelectorAll('thead th, tr:first-child th, tr:first-child td'));
    var colIdx = -1;
    for (var c = 0; c < ths.length; c++) {
      if (norm(ths[c].innerText || ths[c].textContent).indexOf(wantCol) !== -1) {
        colIdx = c;
        break;
      }
    }
    if (colIdx === -1) continue;
    var rows = Array.from(tables[t].querySelectorAll('tbody tr')).filter(isVis);
    if (rows.length === 0) continue;
    var lastRow = rows[rows.length - 1];
    var cells = Array.from(lastRow.querySelectorAll('td'));
    if (colIdx >= cells.length) continue;
    var cell = cells[colIdx];

    var sel = cell.querySelector('select');
    if (sel) {
      var opts = Array.from(sel.options || []);
      for (var k = 0; k < opts.length; k++) {
        if (norm(opts[k].text).indexOf(wantOpt) !== -1) {
          sel.value = opts[k].value;
          sel.dispatchEvent(new Event('change', { bubbles: true }));
          return { ok: true, mode: 'native_select', selected: opts[k].text };
        }
      }
    }
    var trigger = cell.querySelector('[role="combobox"], .ant-select-selector, .mud-select-input, input, button, div[class*="select"]');
    if (trigger && isVis(trigger)) {
      trigger.click();
      return { ok: true, mode: 'opened_custom_dropdown', current: norm(cell.innerText || cell.textContent) };
    }
  }
  return { ok: false, mode: 'not_found', current: '' };
})(arguments[0], arguments[1]);
"""

_JS_SELECT_TOP_SERVICE_DROPDOWN = """
(function(serviceText) {
  function norm(s) { return String(s || '').replace(/\\s+/g, ' ').trim().toLowerCase(); }
  function isVis(el) {
    if (!el) return false;
    var st = window.getComputedStyle(el);
    if (st.display === 'none' || st.visibility === 'hidden' || st.opacity === '0') return false;
    var r = el.getBoundingClientRect();
    return r.width > 0 && r.height > 0;
  }
  var modals = Array.from(document.querySelectorAll('[role="dialog"], .modal, .mud-dialog, .ant-modal, .el-dialog'))
    .filter(isVis);
  var root = modals.length > 0 ? modals[modals.length - 1] : document;
  var want = norm(serviceText);

  var sel = root.querySelector('select');
  if (sel && isVis(sel)) {
    var opts = Array.from(sel.options || []);
    for (var k = 0; k < opts.length; k++) {
      if (norm(opts[k].text) === want || norm(opts[k].text).indexOf(want) !== -1) {
        sel.value = opts[k].value;
        sel.dispatchEvent(new Event('change', { bubbles: true }));
        return { ok: true, mode: 'native_select', selected: opts[k].text };
      }
    }
  }
  var custom = root.querySelector('[role="combobox"], .ant-select-selector, .mud-select-input, button[aria-haspopup]');
  if (custom && isVis(custom)) {
    var cur = norm(custom.innerText || custom.textContent);
    if (cur === want) return { ok: true, mode: 'already_selected', selected: cur };
    custom.click();
    return { ok: true, mode: 'opened_custom_dropdown', selected: cur };
  }
  return { ok: false, mode: 'not_found', selected: '' };
})(arguments[0]);
"""


def _wait_for_popup(driver, keyword: str, timeout_sec: float = 8.0) -> bool:
    deadline = time.monotonic() + max(0.5, float(timeout_sec))
    while time.monotonic() < deadline:
        try:
            if driver.execute_script(_JS_CHECK_POPUP_VISIBLE, keyword):
                return True
        except Exception:
            pass
        time.sleep(0.25)
    return False


def _select_labeled_dropdown(driver, label_text: str, option_text: str) -> bool:
    res = driver.execute_script(_JS_SELECT_DROPDOWN_BY_LABEL, label_text, option_text) or {}
    if not isinstance(res, dict) or not res.get("ok"):
        return False
    if res.get("mode") == "native_select":
        return True
    time.sleep(0.35)
    pick = driver.execute_script(_JS_CLICK_DROPDOWN_OPTION, option_text) or {}
    return bool(isinstance(pick, dict) and pick.get("clicked"))


def _select_table_cell_dropdown(driver, col_header: str, option_text: str) -> bool:
    res = driver.execute_script(_JS_SELECT_TABLE_CELL_DROPDOWN, col_header, option_text) or {}
    if not isinstance(res, dict) or not res.get("ok"):
        return False
    if res.get("mode") == "native_select":
        return True
    time.sleep(0.35)
    pick = driver.execute_script(_JS_CLICK_DROPDOWN_OPTION, option_text) or {}
    return bool(isinstance(pick, dict) and pick.get("clicked"))


def _update_thong_tin_bao_tri_if_needed(
    driver,
    steps: List[str],
    log_cb: Optional[Callable[[str, str], None]] = None,
) -> None:
    """
    Điều kiện 3 trong popup 'Xác nhận chuyển tình trạng "Đã xử lý"':
    Kiểm tra card 'Thông tin bảo trì':
    - Nguyên nhân chưa cài đặt Hi FPT   (nếu 'Không chọn' -> 'Không gặp chủ hợp đồng')
    - Nguyên nhân chưa nghiệm thu Mỹ Bảo (nếu 'Không chọn' -> 'Không kết nối được wifi khách hàng')
    Nếu có trường là 'Không chọn' -> bấm cây bút ✏️ -> chọn giá trị -> bấm 'Cập nhật'.
    """
    card_info = driver.execute_script(_JS_READ_BAO_TRI_CARD) or {}
    hi_val = normalize_nfc(card_info.get("hi_fpt") or "").lower()
    mb_val = normalize_nfc(card_info.get("my_bao") or "").lower()

    need_hi = (not hi_val) or ("không chọn" in hi_val)
    need_mb = (not mb_val) or ("không chọn" in mb_val)

    if not need_hi and not need_mb:
        steps.append("Thông tin bảo trì: đã có đủ nguyên nhân Hi FPT & Mỹ Bảo (không cần sửa).")
        return

    _emit(log_cb, "Module 4: Sửa card 'Thông tin bảo trì' (Hi FPT / Mỹ Bảo đang là 'Không chọn')...", "info")
    pencil = driver.execute_script(_JS_CLICK_CARD_PENCIL, "Thông tin bảo trì") or {}
    if not (isinstance(pencil, dict) and pencil.get("clicked")):
        raise RuntimeError("Không tìm thấy biểu tượng cây bút (✏️) của card 'Thông tin bảo trì'.")
    time.sleep(0.4)

    if need_hi:
        if not _select_labeled_dropdown(driver, "Nguyên nhân chưa cài đặt Hi FPT", HI_FPT_TARGET):
            raise RuntimeError(f"Không chọn được 'Nguyên nhân chưa cài đặt Hi FPT' = '{HI_FPT_TARGET}'.")
        steps.append(f"Đã chọn Nguyên nhân chưa cài đặt Hi FPT = '{HI_FPT_TARGET}'.")

    if need_mb:
        if not _select_labeled_dropdown(driver, "Nguyên nhân chưa nghiệm thu Mỹ Bảo", MY_BAO_TARGET):
            raise RuntimeError(f"Không chọn được 'Nguyên nhân chưa nghiệm thu Mỹ Bảo' = '{MY_BAO_TARGET}'.")
        steps.append(f"Đã chọn Nguyên nhân chưa nghiệm thu Mỹ Bảo = '{MY_BAO_TARGET}'.")

    upd = driver.execute_script(_JS_CLICK_BUTTON_BY_TEXT, "Cập nhật", True) or {}
    if not (isinstance(upd, dict) and upd.get("clicked")):
        raise RuntimeError("Không bấm được nút 'Cập nhật' trong card 'Thông tin bảo trì'.")
    time.sleep(0.8)
    steps.append("Đã bấm 'Cập nhật' card Thông tin bảo trì.")


def _update_thong_tin_dich_vu(
    driver,
    steps: List[str],
    log_cb: Optional[Callable[[str, str], None]] = None,
) -> None:
    """
    Bước 4 (Card 'Thông tin dịch vụ'):
    - Bấm cây bút ✏️ ở card 'Thông tin dịch vụ' -> mở sub-popup 'Thông tin dịch vụ'.
    - Chọn dropdown đầu tiên 'Internet' -> bấm '+ Thêm'.
    - Chọn Phần tử lỗi = 'Khách hàng' (nếu cần), Nguyên nhân lỗi = 'Đến nhà khách hàng kiểm tra KH yêu cầu hủy hợp đồng'.
    - Bấm 'Cập nhật' trong sub-popup 'Thông tin dịch vụ'.
    """
    _emit(log_cb, "Module 4: Mở sub-popup 'Thông tin dịch vụ' để thêm nguyên nhân lỗi...", "info")
    pencil = driver.execute_script(_JS_CLICK_CARD_PENCIL, "Thông tin dịch vụ") or {}
    if not (isinstance(pencil, dict) and pencil.get("clicked")):
        raise RuntimeError("Không tìm thấy biểu tượng cây bút (✏️) của card 'Thông tin dịch vụ'.")

    if not _wait_for_popup(driver, "Thông tin dịch vụ", timeout_sec=6.0):
        raise RuntimeError("Sub-popup 'Thông tin dịch vụ' không hiển thị sau khi bấm cây bút.")
    time.sleep(0.3)

    # Chọn dropdown đầu tiên 'Internet'
    svc_res = driver.execute_script(_JS_SELECT_TOP_SERVICE_DROPDOWN, DICH_VU_TARGET) or {}
    if isinstance(svc_res, dict) and svc_res.get("mode") == "opened_custom_dropdown":
        time.sleep(0.3)
        driver.execute_script(_JS_CLICK_DROPDOWN_OPTION, DICH_VU_TARGET)
    steps.append(f"Đã chọn dịch vụ '{DICH_VU_TARGET}'.")

    # Bấm nút '+ Thêm'
    add_res = driver.execute_script(_JS_CLICK_BUTTON_BY_TEXT, "Thêm", True) or {}
    if not (isinstance(add_res, dict) and add_res.get("clicked")):
        raise RuntimeError("Không bấm được nút '+ Thêm' trong sub-popup 'Thông tin dịch vụ'.")
    time.sleep(0.5)
    steps.append("Đã bấm '+ Thêm' dòng dịch vụ Internet.")

    # Chọn Phần tử lỗi = Khách hàng (nếu chưa tự chọn)
    _select_table_cell_dropdown(driver, "PHẦN TỬ LỖI", PHAN_TU_LOI_TARGET)
    time.sleep(0.3)

    # Chọn Nguyên nhân lỗi = Đến nhà khách hàng kiểm tra KH yêu cầu hủy hợp đồng
    if not _select_table_cell_dropdown(driver, "NGUYÊN NHÂN LỖI", NGUYEN_NHAN_LOI_TARGET):
        raise RuntimeError(f"Không chọn được 'Nguyên nhân lỗi' = '{NGUYEN_NHAN_LOI_TARGET}'.")
    time.sleep(0.3)
    steps.append(f"Đã chọn Nguyên nhân lỗi = '{NGUYEN_NHAN_LOI_TARGET}'.")

    # Bấm 'Cập nhật' của sub-popup 'Thông tin dịch vụ'
    upd = driver.execute_script(_JS_CLICK_BUTTON_BY_TEXT, "Cập nhật", True) or {}
    if not (isinstance(upd, dict) and upd.get("clicked")):
        raise RuntimeError("Không bấm được nút 'Cập nhật' trong sub-popup 'Thông tin dịch vụ'.")
    time.sleep(0.8)
    steps.append("Đã bấm 'Cập nhật' sub-popup Thông tin dịch vụ.")


def execute_complete_ticket(
    session: InsideSession,
    nav_ctx: NavigationContext,
    validation: Dict,
    dry_run: Optional[bool] = None,
    settings: Optional[AutoHoanTatSettings] = None,
    log_cb: Optional[Callable[[str, str], None]] = None,
) -> ExecutionResult:
    """
    Thực thi hoàn tất 1 phiếu PBT (XÁC MINH THÔNG TIN) dựa trên kết quả kiểm tra của Module 3.
    Mặc định chạy ở chế độ DRY-RUN (không thay đổi dữ liệu).
    """
    t0 = time.monotonic()
    cfg = settings or load_settings()
    if not cfg.enabled:
        raise FeatureDisabledError("Chức năng 'Auto Hoàn Tất PTC/PBT' đang TẮT.")

    is_dry_run = cfg.dry_run_default if dry_run is None else bool(dry_run)
    mode_str = "DRY_RUN" if is_dry_run else "REAL"

    ma_phieu = normalize_nfc(validation.get("ma_phieu") or nav_ctx.shd)
    tac_vu = normalize_nfc(validation.get("tac_vu") or nav_ctx.tac_vu)
    loai = str(validation.get("loai") or nav_ctx.loai or "")
    da_hoan_tat = bool(validation.get("da_hoan_tat"))
    du_dieu_kien = bool(validation.get("du_dieu_kien"))
    ly_do = str(validation.get("ly_do_neu_khong_du") or "")

    if da_hoan_tat:
        return ExecutionResult(
            ma_phieu=ma_phieu,
            tac_vu=tac_vu,
            loai=loai,
            mode=mode_str,
            status=STATUS_SKIPPED_ALREADY_DONE,
            ket_qua=ly_do or "Phiếu đã hoàn tất trước đó (bỏ qua).",
            steps_performed=["Bỏ qua vì phiếu đã hoàn tất trước đó (idempotent)."],
            post_status=nav_ctx.ticket_status,
            elapsed_ms=int((time.monotonic() - t0) * 1000),
        )

    if not du_dieu_kien:
        return ExecutionResult(
            ma_phieu=ma_phieu,
            tac_vu=tac_vu,
            loai=loai,
            mode=mode_str,
            status=STATUS_NOT_ELIGIBLE,
            ket_qua=ly_do,
            steps_performed=["Dừng tại Module 3: không đủ điều kiện hoàn tất."],
            post_status=nav_ctx.ticket_status,
            elapsed_ms=int((time.monotonic() - t0) * 1000),
        )

    if is_dry_run:
        planned = [
            "[DRY-RUN] Sẽ bấm 'Thay đổi tình trạng' -> 'Đã xử lý'.",
            f"[DRY-RUN] Sẽ kiểm tra card 'Thông tin bảo trì' -> đặt Hi FPT='{HI_FPT_TARGET}', Mỹ Bảo='{MY_BAO_TARGET}' nếu đang 'Không chọn' -> bấm 'Cập nhật'.",
            f"[DRY-RUN] Sẽ mở 'Thông tin dịch vụ' -> chọn '{DICH_VU_TARGET}' -> '+ Thêm' -> Nguyên nhân lỗi='{NGUYEN_NHAN_LOI_TARGET}' -> bấm 'Cập nhật'.",
            "[DRY-RUN] Sẽ bấm nút 'Xác nhận' để chuyển tình trạng phiếu sang 'Đã xử lý'.",
        ]
        _emit(
            log_cb,
            f"Module 4 [DRY-RUN]: HĐ {ma_phieu} ĐỦ ĐIỀU KIỆN hoàn tất (không ghi dữ liệu).",
            "success",
        )
        return ExecutionResult(
            ma_phieu=ma_phieu,
            tac_vu=tac_vu,
            loai=loai,
            mode=mode_str,
            status=STATUS_DRY_RUN_READY,
            ket_qua="DRY-RUN: Đủ điều kiện hoàn tất (chưa thực thi ghi dữ liệu).",
            steps_performed=planned,
            post_status=nav_ctx.ticket_status,
            elapsed_ms=int((time.monotonic() - t0) * 1000),
        )

    # ===== CHẠY THẬT (REAL) =====
    session.ensure_alive()
    driver = session.driver
    steps: List[str] = []

    try:
        _emit(log_cb, f"Module 4 [REAL]: Bấm 'Thay đổi tình trạng' -> 'Đã xử lý' cho HĐ {ma_phieu}...", "info")
        btn_change = driver.execute_script(_JS_CLICK_BUTTON_BY_TEXT, "Thay đổi tình trạng", False) or {}
        if not (isinstance(btn_change, dict) and btn_change.get("clicked")):
            raise RuntimeError("Không tìm thấy hoặc không bấm được nút 'Thay đổi tình trạng'.")
        time.sleep(0.4)

        opt_done = driver.execute_script(_JS_CLICK_BUTTON_BY_TEXT, "Đã xử lý", False) or {}
        if not (isinstance(opt_done, dict) and opt_done.get("clicked")):
            raise RuntimeError("Không chọn được mục 'Đã xử lý' trong menu 'Thay đổi tình trạng'.")
        steps.append("Đã bấm 'Thay đổi tình trạng' -> 'Đã xử lý'.")

        if not _wait_for_popup(driver, "Xác nhận chuyển tình trạng", timeout_sec=8.0):
            raise RuntimeError("Popup 'Xác nhận chuyển tình trạng \"Đã xử lý\"' không hiển thị.")

        # Điều kiện 3: Card Thông tin bảo trì
        _update_thong_tin_bao_tri_if_needed(driver, steps, log_cb=log_cb)

        # Bước 4: Card Thông tin dịch vụ
        _update_thong_tin_dich_vu(driver, steps, log_cb=log_cb)

        # Nút Xác nhận cuối cùng
        _emit(log_cb, f"Module 4 [REAL]: Bấm nút 'Xác nhận' hoàn tất cho HĐ {ma_phieu}...", "info")
        confirm = driver.execute_script(_JS_CLICK_BUTTON_BY_TEXT, "Xác nhận", True) or {}
        if not (isinstance(confirm, dict) and confirm.get("clicked")):
            raise RuntimeError("Không bấm được nút 'Xác nhận' ở đáy popup.")
        steps.append("Đã bấm nút 'Xác nhận' chuyển tình trạng 'Đã xử lý'.")

        # Xác nhận lại trạng thái trên giao diện sau khi bấm Xác nhận
        post_status = ""
        deadline = time.monotonic() + 10.0
        while time.monotonic() < deadline:
            time.sleep(0.5)
            post_status = _read_footer_ticket_status(driver)
            if is_already_completed(post_status):
                break

        if not is_already_completed(post_status):
            return ExecutionResult(
                ma_phieu=ma_phieu,
                tac_vu=tac_vu,
                loai=loai,
                mode=mode_str,
                status=STATUS_ERROR,
                ket_qua=(
                    f"Đã bấm 'Xác nhận' nhưng chưa xác minh được trạng thái 'Đã xử lý' trên Inside "
                    f"(trạng thái hiện tại: '{post_status or 'Chưa rõ'}')."
                ),
                steps_performed=steps,
                post_status=post_status,
                elapsed_ms=int((time.monotonic() - t0) * 1000),
            )

        steps.append(f"Xác minh sau hoàn tất thành công: Tình trạng phiếu = '{post_status}'.")
        _emit(
            log_cb,
            f"Module 4 [REAL]: Hoàn tất thành công HĐ {ma_phieu} (Trạng thái: {post_status}).",
            "success",
        )
        return ExecutionResult(
            ma_phieu=ma_phieu,
            tac_vu=tac_vu,
            loai=loai,
            mode=mode_str,
            status=STATUS_SUCCESS,
            ket_qua="Thành công: Đã chuyển tình trạng phiếu sang Đã xử lý.",
            steps_performed=steps,
            post_status=post_status,
            elapsed_ms=int((time.monotonic() - t0) * 1000),
        )
    except Exception as exc:
        _emit(log_cb, f"Module 4 [REAL] Lỗi xử lý HĐ {ma_phieu}: {exc}", "error")
        return ExecutionResult(
            ma_phieu=ma_phieu,
            tac_vu=tac_vu,
            loai=loai,
            mode=mode_str,
            status=STATUS_ERROR,
            ket_qua=f"Lỗi thực thi: {exc}",
            steps_performed=steps,
            post_status=_read_footer_ticket_status(driver),
            elapsed_ms=int((time.monotonic() - t0) * 1000),
        )

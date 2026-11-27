"""
Module 4 - Thực thi đóng ca PBT (Xác Minh Thông Tin) trực tiếp trên trang THÔNG TIN BẢO TRÌ (Inside).

An toàn mặc định:
- DRY-RUN mặc định BẬT (dry_run=True): chỉ chạy kiểm tra điều kiện (Module 3) và mô phỏng bước 4-5,
  tuyệt đối KHÔNG bấm 'Thêm' hay 'Cập nhật' làm thay đổi dữ liệu.
- Idempotent: phiếu đã 'Đã xử lý' / 'Đã hoàn tất' sẽ bỏ qua an toàn.
- Chạy thật (dry_run=False) chỉ thực thi khi Module 3 trả về du_dieu_kien=True:
  Bước 4: Bấm nút 'Xem thêm' để mở rộng phần Thông tin bảo trì / Nguyên nhân lỗi / Cập nhật kết quả xử lý.
    4a. 'Nguyên nhân chưa nghiệm thu Mỹ Bảo' -> chọn 'Không kết nối được hệ thống Mỹ bảo'.
    4b. Trong khối 'Nguyên nhân lỗi': chọn Dịch vụ = 'Internet' -> bấm nút 'Thêm'.
    4c. Tại dòng mới trong bảng 'Nguyên nhân lỗi', chọn lần lượt 4 cột:
        - Tình trạng ban đầu: 'KH không cung cấp rõ tình trạng lỗi hoặc KH có khiếu nại RM'
        - Phần tử lỗi:        'Khách hàng'
        - Nguyên nhân lỗi:    'Đến nhà khách hàng kiểm tra KH yêu cầu hủy hợp đồng'
        - Hướng xử lý:        'Tạo SR để DVKH hỗ trợ, đóng CL'
  Bước 5: Trong khối 'Cập nhật kết quả xử lý của phiếu':
    - 'Kết quả xử lý' (đang là 'Đang xử lý') -> chọn 'Đã xử lý'
    - Bấm nút 'Cập nhật' của khối này.
  Sau đó xác minh lại trạng thái trên trang đã chuyển sang 'Đã xử lý'.
"""

from dataclasses import asdict, dataclass, field
import time
from typing import Callable, Dict, List, Optional

from .config import AutoHoanTatSettings, load_settings
from .mod1_auth import FeatureDisabledError, InsideSession
from .mod2_navigator import NavigationContext, _read_footer_ticket_status
from .mod3_validator import KET_QUA_KHONG_THANH_CONG, REQUIRED_INITIAL_NOTE, is_already_completed
from .sheet_reader import normalize_nfc

MY_BAO_TARGET = "Không kết nối được hệ thống Mỹ bảo"
DICH_VU_TARGET = "Internet"
TINH_TRANG_BAN_DAU_TARGET = REQUIRED_INITIAL_NOTE
PHAN_TU_LOI_TARGET = "Khách hàng"
NGUYEN_NHAN_LOI_TARGET = "Đến nhà khách hàng kiểm tra KH yêu cầu hủy hợp đồng"
HUONG_XU_LY_TARGET = "Tạo SR để DVKH hỗ trợ, đóng CL"
KET_QUA_XU_LY_TARGET = "Đã xử lý"

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
    ghi_chu: str = ""
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


_JS_CLICK_XEM_THEM_IF_NEEDED = """
(function() {
  function norm(s) {
    var str = String(s || '');
    return (str.normalize ? str.normalize('NFC') : str).replace(/\\s+/g, ' ').trim().toLowerCase();
  }
  function isVis(el) {
    if (!el) return false;
    try {
      var st = window.getComputedStyle(el);
      if (st.display === 'none' || st.visibility === 'hidden' || st.opacity === '0') return false;
      var r = el.getBoundingClientRect();
      return r.width > 0 && r.height > 0;
    } catch (e) { return false; }
  }

  // Nếu mục 'Nguyên nhân chưa nghiệm thu Mỹ Bảo' hoặc 'Cập nhật kết quả xử lý của phiếu' đã hiển thị -> đã mở rộng sẵn
  var bodyTxt = norm((document.body && (document.body.innerText || document.body.textContent)) || '');
  if (bodyTxt.indexOf('nguyên nhân chưa nghiệm thu mỹ bảo') !== -1 &&
      bodyTxt.indexOf('cập nhật kết quả xử lý của phiếu') !== -1) {
    return { already_expanded: true, clicked: false };
  }

  var els = Array.from(document.querySelectorAll('button, a, span, div, [role="button"]')).filter(isVis);
  for (var i = 0; i < els.length; i++) {
    var t = norm(els[i].innerText || els[i].textContent);
    if (t === 'xem thêm' || (t.indexOf('xem thêm') !== -1 && t.length <= 20)) {
      els[i].scrollIntoView({block: 'center'});
      els[i].click();
      return { already_expanded: false, clicked: true, text: t };
    }
  }
  return { already_expanded: false, clicked: false };
})();
"""

_JS_SELECT_ROW_DROPDOWN_BY_LABEL = """
(function(labelText, optionText, sectionHint) {
  function norm(s) {
    var str = String(s || '');
    return (str.normalize ? str.normalize('NFC') : str).replace(/\\s+/g, ' ').trim().toLowerCase();
  }
  function isVis(el) {
    if (!el) return false;
    try {
      var st = window.getComputedStyle(el);
      if (st.display === 'none' || st.visibility === 'hidden' || st.opacity === '0') return false;
      var r = el.getBoundingClientRect();
      return r.width > 0 && r.height > 0;
    } catch (e) { return false; }
  }
  function fireOpen(el) {
    el.scrollIntoView({block: 'center'});
    try { el.focus(); } catch (e) {}
    ['mousedown', 'mouseup', 'click'].forEach(function(ev) {
      el.dispatchEvent(new MouseEvent(ev, {bubbles: true, cancelable: true, view: window}));
    });
  }

  var wantLabel = norm(labelText);
  var wantOpt = norm(optionText);
  var wantSec = norm(sectionHint || '');

  function findScope() {
    if (!wantSec) return document;
    var headers = Array.from(document.querySelectorAll('div, section, h3, h4, h5, p, span, tr, th, td')).filter(function(el) {
      if (!isVis(el)) return false;
      var t = norm(el.innerText || el.textContent);
      return t === wantSec || (t.indexOf(wantSec) !== -1 && t.length <= wantSec.length + 25);
    });
    for (var i = 0; i < headers.length; i++) {
      var cur = headers[i];
      for (var d = 0; d < 5 && cur && cur.parentElement; d++) {
        cur = cur.parentElement;
        var ct = norm(cur.innerText || cur.textContent);
        if (ct.indexOf(wantLabel) !== -1 && ct.length < 5000) {
          return cur;
        }
      }
    }
    return document;
  }

  var root = findScope();

  // 1. Tìm ô td/label/div chứa đúng nhãn labelText rồi lấy ô kế tiếp hoặc container cha
  var nodes = Array.from(root.querySelectorAll('td, th, label, div, span')).filter(function(el) {
    if (!isVis(el)) return false;
    var t = norm(el.innerText || el.textContent);
    return t === wantLabel || (t.indexOf(wantLabel) !== -1 && t.length <= wantLabel.length + 18);
  });

  for (var i = 0; i < nodes.length; i++) {
    var candidates = [];
    if (nodes[i].nextElementSibling) candidates.push(nodes[i].nextElementSibling);
    if (nodes[i].parentElement) candidates.push(nodes[i].parentElement);
    if (nodes[i].parentElement && nodes[i].parentElement.parentElement) candidates.push(nodes[i].parentElement.parentElement);

    for (var c = 0; c < candidates.length; c++) {
      var box = candidates[c];
      if (!box) continue;

      var sel = box.querySelector('select');
      if (sel && isVis(sel)) {
        var opts = Array.from(sel.options || []);
        for (var k = 0; k < opts.length; k++) {
          var ot = norm(opts[k].text);
          if (ot === wantOpt || ot.indexOf(wantOpt) !== -1) {
            sel.value = opts[k].value;
            sel.dispatchEvent(new Event('input', {bubbles: true}));
            sel.dispatchEvent(new Event('change', {bubbles: true}));
            return { ok: true, mode: 'native_select', selected: opts[k].text };
          }
        }
      }

      var custom = box.querySelector(
        '[role="combobox"], .ant-select-selector, .el-select, .vs__dropdown-toggle, .select2-selection, .mud-select-input, .mud-input-control, .multiselect, input[readonly], button[aria-haspopup], .form-select'
      );
      if (custom && isVis(custom)) {
        var curTxt = norm(custom.innerText || custom.textContent || custom.value || '').replace(/\\s*[×x]\\s*$/i, '').trim();
        if (curTxt === wantOpt || (wantOpt.length > 4 && curTxt.indexOf(wantOpt) !== -1)) {
          return { ok: true, mode: 'already_selected', selected: curTxt };
        }
        fireOpen(custom);
        return { ok: true, mode: 'opened_custom_dropdown', current: curTxt };
      }

      var inp = box.querySelector('input:not([type="hidden"]):not([type="checkbox"]):not([type="radio"])');
      if (inp && isVis(inp)) {
        var iv = norm(inp.value || '');
        if (iv === wantOpt || (wantOpt.length > 4 && iv.indexOf(wantOpt) !== -1)) {
          return { ok: true, mode: 'already_selected', selected: iv };
        }
        fireOpen(inp);
        return { ok: true, mode: 'opened_custom_dropdown', current: iv };
      }
    }
  }
  return { ok: false, mode: 'not_found', selected: '' };
})(arguments[0], arguments[1], arguments[2]);
"""

_JS_CLICK_DROPDOWN_OPTION = """
(function(optionText) {
  function norm(s) {
    var str = String(s || '');
    return (str.normalize ? str.normalize('NFC') : str).replace(/\\s+/g, ' ').trim().toLowerCase();
  }
  function isVis(el) {
    if (!el) return false;
    try {
      var st = window.getComputedStyle(el);
      if (st.display === 'none' || st.visibility === 'hidden' || st.opacity === '0') return false;
      var r = el.getBoundingClientRect();
      return r.width > 0 && r.height > 0;
    } catch (e) { return false; }
  }
  var want = norm(optionText);
  var selector = [
    '[role="option"]',
    '.ant-select-item-option',
    '.ant-select-item-option-content',
    '.el-select-dropdown__item',
    '.vs__dropdown-option',
    '.select2-results__option',
    '.mud-list-item',
    '.multiselect__option',
    '.dropdown-item',
    'ul li',
    'div[class*="option"]'
  ].join(', ');
  var items = Array.from(document.querySelectorAll(selector)).filter(isVis);

  // Ưu tiên khớp chính xác trước
  for (var i = items.length - 1; i >= 0; i--) {
    var t = norm(items[i].innerText || items[i].textContent);
    if (t === want) {
      items[i].scrollIntoView({block: 'center'});
      items[i].click();
      return { clicked: true, text: t };
    }
  }
  // Tiếp theo là khớp contains (ưu tiên phần tử ngắn nhất để tránh click nhầm container cha)
  var best = null;
  var bestLen = 99999;
  for (var j = items.length - 1; j >= 0; j--) {
    var t2 = norm(items[j].innerText || items[j].textContent);
    if (t2 && t2.indexOf(want) !== -1 && t2.length < bestLen && t2.length <= want.length + 35) {
      best = items[j];
      bestLen = t2.length;
    }
  }
  if (best) {
    best.scrollIntoView({block: 'center'});
    best.click();
    return { clicked: true, text: norm(best.innerText || best.textContent) };
  }
  return { clicked: false, text: '' };
})(arguments[0]);
"""

_JS_CLICK_BUTTON_IN_SECTION = """
(function(sectionTitle, buttonText) {
  function norm(s) {
    var str = String(s || '');
    return (str.normalize ? str.normalize('NFC') : str).replace(/\\s+/g, ' ').trim().toLowerCase();
  }
  function isVis(el) {
    if (!el) return false;
    try {
      var st = window.getComputedStyle(el);
      if (st.display === 'none' || st.visibility === 'hidden' || st.opacity === '0') return false;
      var r = el.getBoundingClientRect();
      return r.width > 0 && r.height > 0;
    } catch (e) { return false; }
  }

  var wantSec = norm(sectionTitle);
  var wantBtn = norm(buttonText);

  var headers = Array.from(document.querySelectorAll('div, section, h3, h4, h5, p, span, tr, th, td')).filter(function(el) {
    if (!isVis(el)) return false;
    var t = norm(el.innerText || el.textContent);
    return t === wantSec || (t.indexOf(wantSec) !== -1 && t.length <= wantSec.length + 25);
  });

  for (var i = 0; i < headers.length; i++) {
    var cur = headers[i];
    for (var d = 0; d < 5 && cur && cur.parentElement; d++) {
      cur = cur.parentElement;
      var ct = norm(cur.innerText || cur.textContent);
      if (ct.length > 6000) break;
      var btns = Array.from(cur.querySelectorAll('button, input[type="button"], input[type="submit"], a, [role="button"]')).filter(isVis);
      for (var b = 0; b < btns.length; b++) {
        var bt = norm(btns[b].innerText || btns[b].textContent || btns[b].value || '');
        if (bt === wantBtn || (bt && bt.indexOf(wantBtn) !== -1 && bt.length <= wantBtn.length + 12)) {
          btns[b].scrollIntoView({block: 'center'});
          btns[b].click();
          return { clicked: true, text: bt, section: sectionTitle };
        }
      }
    }
  }
  return { clicked: false, text: '', section: sectionTitle };
})(arguments[0], arguments[1]);
"""

_JS_SELECT_ERROR_REASON_TABLE_CELL = """
(function(colHeaderText, optionText) {
  function norm(s) {
    var str = String(s || '');
    return (str.normalize ? str.normalize('NFC') : str).replace(/\\s+/g, ' ').trim().toLowerCase();
  }
  function isVis(el) {
    if (!el) return false;
    try {
      var st = window.getComputedStyle(el);
      if (st.display === 'none' || st.visibility === 'hidden' || st.opacity === '0') return false;
      var r = el.getBoundingClientRect();
      return r.width > 0 && r.height > 0;
    } catch (e) { return false; }
  }
  function fireOpen(el) {
    el.scrollIntoView({block: 'center'});
    try { el.focus(); } catch (e) {}
    ['mousedown', 'mouseup', 'click'].forEach(function(ev) {
      el.dispatchEvent(new MouseEvent(ev, {bubbles: true, cancelable: true, view: window}));
    });
  }

  var wantCol = norm(colHeaderText);
  var wantOpt = norm(optionText);

  // Tìm đúng bảng 'Nguyên nhân lỗi' có đầy đủ cột 'Phần tử lỗi' / 'Hướng xử lý'
  var tables = Array.from(document.querySelectorAll('table')).filter(isVis);
  for (var t = tables.length - 1; t >= 0; t--) {
    var tbl = tables[t];
    var ths = Array.from(tbl.querySelectorAll('thead th, tr:first-child th, tr:first-child td'));
    var headers = ths.map(function(h) { return norm(h.innerText || h.textContent); });
    if (!headers.some(function(h) { return h.indexOf('phần tử lỗi') !== -1 || h.indexOf('hướng xử lý') !== -1; })) {
      continue;
    }
    var colIdx = -1;
    for (var c = 0; c < headers.length; c++) {
      if (headers[c] === wantCol || headers[c].indexOf(wantCol) !== -1) {
        colIdx = c;
        break;
      }
    }
    if (colIdx === -1) continue;

    var rows = Array.from(tbl.querySelectorAll('tbody tr')).filter(isVis);
    if (!rows.length) {
      rows = Array.from(tbl.querySelectorAll('tr')).slice(1).filter(isVis);
    }
    if (!rows.length) {
      return { ok: false, mode: 'no_rows_yet', current: '' };
    }
    var lastRow = rows[rows.length - 1];
    var cells = Array.from(lastRow.querySelectorAll('td'));
    if (colIdx >= cells.length) continue;
    var cell = cells[colIdx];

    var sel = cell.querySelector('select');
    if (sel) {
      var opts = Array.from(sel.options || []);
      for (var k = 0; k < opts.length; k++) {
        var ot = norm(opts[k].text);
        if (ot === wantOpt || ot.indexOf(wantOpt) !== -1) {
          sel.value = opts[k].value;
          sel.dispatchEvent(new Event('input', {bubbles: true}));
          sel.dispatchEvent(new Event('change', {bubbles: true}));
          return { ok: true, mode: 'native_select', selected: opts[k].text };
        }
      }
    }

    var trigger = cell.querySelector(
      '[role="combobox"], .ant-select-selector, .el-select, .vs__dropdown-toggle, .select2-selection, .mud-select-input, .multiselect, input, button, div[class*="select"]'
    );
    if (trigger && isVis(trigger)) {
      var curTxt = norm(cell.innerText || cell.textContent || trigger.value || '');
      if (curTxt === wantOpt || (wantOpt.length > 6 && curTxt.indexOf(wantOpt) !== -1)) {
        return { ok: true, mode: 'already_selected', selected: curTxt };
      }
      fireOpen(trigger);
      return { ok: true, mode: 'opened_custom_dropdown', current: curTxt };
    }
  }
  return { ok: false, mode: 'not_found', current: '' };
})(arguments[0], arguments[1]);
"""

_JS_ACCEPT_CONFIRM_MODAL_IF_ANY = """
(function() {
  function norm(s) {
    var str = String(s || '');
    return (str.normalize ? str.normalize('NFC') : str).replace(/\\s+/g, ' ').trim().toLowerCase();
  }
  function isVis(el) {
    if (!el) return false;
    try {
      var st = window.getComputedStyle(el);
      if (st.display === 'none' || st.visibility === 'hidden' || st.opacity === '0') return false;
      var r = el.getBoundingClientRect();
      return r.width > 0 && r.height > 0;
    } catch (e) { return false; }
  }
  var modals = Array.from(document.querySelectorAll('[role="dialog"], .modal, .mud-dialog, .ant-modal, .swal2-popup, .el-message-box'))
    .filter(isVis);
  if (!modals.length) return false;
  var top = modals[modals.length - 1];
  var btns = Array.from(top.querySelectorAll('button, [role="button"]')).filter(isVis);
  for (var i = 0; i < btns.length; i++) {
    var t = norm(btns[i].innerText || btns[i].textContent);
    if (t === 'đồng ý' || t === 'xác nhận' || t === 'ok' || t === 'có' || t === 'yes') {
      btns[i].click();
      return true;
    }
  }
  return false;
})();
"""

_JS_READ_RESULT_SELECT_OR_TOAST = """
(function() {
  function norm(s) {
    var str = String(s || '');
    return (str.normalize ? str.normalize('NFC') : str).replace(/\\s+/g, ' ').trim();
  }
  var body = norm((document.body && (document.body.innerText || document.body.textContent)) || '');
  var low = body.toLowerCase();
  var hasSuccessToast = (
    low.indexOf('cập nhật thành công') !== -1 ||
    low.indexOf('thành công') !== -1
  );
  return { has_success_toast: hasSuccessToast };
})();
"""


def _select_labeled_dropdown(driver, label_text: str, option_text: str, section_hint: str = "") -> bool:
    res = driver.execute_script(_JS_SELECT_ROW_DROPDOWN_BY_LABEL, label_text, option_text, section_hint) or {}
    if not isinstance(res, dict) or not res.get("ok"):
        return False
    if res.get("mode") in ("native_select", "already_selected"):
        return True
    time.sleep(0.45)
    pick = driver.execute_script(_JS_CLICK_DROPDOWN_OPTION, option_text) or {}
    return bool(isinstance(pick, dict) and pick.get("clicked"))


def _select_error_table_cell(driver, col_header: str, option_text: str) -> bool:
    res = driver.execute_script(_JS_SELECT_ERROR_REASON_TABLE_CELL, col_header, option_text) or {}
    if not isinstance(res, dict) or not res.get("ok"):
        return False
    if res.get("mode") in ("native_select", "already_selected"):
        return True
    time.sleep(0.45)
    pick = driver.execute_script(_JS_CLICK_DROPDOWN_OPTION, option_text) or {}
    return bool(isinstance(pick, dict) and pick.get("clicked"))


def _step4_expand_xem_them(driver, steps: List[str], log_cb: Optional[Callable[[str, str], None]] = None) -> None:
    """Bước 4: Bấm nút 'Xem thêm' để hiển thị phần Thông tin bảo trì / Nguyên nhân lỗi / Cập nhật kết quả xử lý."""
    res = driver.execute_script(_JS_CLICK_XEM_THEM_IF_NEEDED) or {}
    if isinstance(res, dict) and res.get("already_expanded"):
        steps.append("Bước 4: Phần 'Xem thêm' đã mở rộng sẵn.")
        return
    if isinstance(res, dict) and res.get("clicked"):
        _emit(log_cb, "Module 4: Đã bấm nút 'Xem thêm' để mở rộng thông tin bảo trì.", "info")
        time.sleep(0.8)
        steps.append("Bước 4: Đã bấm 'Xem thêm'.")
        return
    raise RuntimeError("Không tìm thấy nút 'Xem thêm' để mở rộng phần Thông tin bảo trì.")


def _step4a_my_bao(driver, steps: List[str], log_cb: Optional[Callable[[str, str], None]] = None) -> None:
    """Bước 4a: Nguyên nhân chưa nghiệm thu Mỹ Bảo -> 'Không kết nối được hệ thống Mỹ bảo'."""
    _emit(log_cb, f"Module 4a: Chọn 'Nguyên nhân chưa nghiệm thu Mỹ Bảo' = '{MY_BAO_TARGET}'...", "info")
    if not _select_labeled_dropdown(driver, "Nguyên nhân chưa nghiệm thu Mỹ Bảo", MY_BAO_TARGET, "Thông tin bảo trì"):
        raise RuntimeError(f"Không chọn được 'Nguyên nhân chưa nghiệm thu Mỹ Bảo' = '{MY_BAO_TARGET}'.")
    time.sleep(0.35)
    steps.append(f"Bước 4a: Đã chọn Nguyên nhân chưa nghiệm thu Mỹ Bảo = '{MY_BAO_TARGET}'.")


def _step4bc_nguyen_nhan_loi(driver, steps: List[str], log_cb: Optional[Callable[[str, str], None]] = None) -> None:
    """
    Bước 4b & 4c:
    - Trong khối 'Nguyên nhân lỗi': chọn Dịch vụ = 'Internet' -> bấm nút 'Thêm'.
    - Chọn lần lượt 4 cột của dòng mới thêm:
      1. Tình trạng ban đầu = 'KH không cung cấp rõ tình trạng lỗi hoặc KH có khiếu nại RM'
      2. Phần tử lỗi        = 'Khách hàng'
      3. Nguyên nhân lỗi    = 'Đến nhà khách hàng kiểm tra KH yêu cầu hủy hợp đồng'
      4. Hướng xử lý        = 'Tạo SR để DVKH hỗ trợ, đóng CL'
    """
    _emit(log_cb, "Module 4b: Trong khối 'Nguyên nhân lỗi' chọn Dịch vụ 'Internet' và bấm 'Thêm'...", "info")
    if not _select_labeled_dropdown(driver, "Dịch vụ", DICH_VU_TARGET, "Nguyên nhân lỗi"):
        raise RuntimeError(f"Không chọn được Dịch vụ = '{DICH_VU_TARGET}' trong khối 'Nguyên nhân lỗi'.")
    time.sleep(0.3)

    add_res = driver.execute_script(_JS_CLICK_BUTTON_IN_SECTION, "Nguyên nhân lỗi", "Thêm") or {}
    if not (isinstance(add_res, dict) and add_res.get("clicked")):
        raise RuntimeError("Không bấm được nút 'Thêm' trong khối 'Nguyên nhân lỗi'.")
    time.sleep(0.7)
    steps.append("Bước 4b: Đã chọn Dịch vụ = 'Internet' và bấm 'Thêm' trong khối Nguyên nhân lỗi.")

    _emit(log_cb, "Module 4c: Điền 4 cột Tình trạng ban đầu / Phần tử lỗi / Nguyên nhân lỗi / Hướng xử lý...", "info")
    ordered_cols = [
        ("Tình trạng ban đầu", TINH_TRANG_BAN_DAU_TARGET),
        ("Phần tử lỗi", PHAN_TU_LOI_TARGET),
        ("Nguyên nhân lỗi", NGUYEN_NHAN_LOI_TARGET),
        ("Hướng xử lý", HUONG_XU_LY_TARGET),
    ]
    for col_name, target_val in ordered_cols:
        if not _select_error_table_cell(driver, col_name, target_val):
            raise RuntimeError(f"Không chọn được cột '{col_name}' = '{target_val}' trong bảng Nguyên nhân lỗi.")
        time.sleep(0.5)
        steps.append(f"Bước 4c: Đã chọn {col_name} = '{target_val}'.")


def _step5_cap_nhat_ket_qua(driver, steps: List[str], log_cb: Optional[Callable[[str, str], None]] = None) -> None:
    """Bước 5: Trong khối 'Cập nhật kết quả xử lý của phiếu' chỉnh 'Kết quả xử lý' -> 'Đã xử lý' và bấm 'Cập nhật'."""
    _emit(log_cb, "Module 5: Chỉnh 'Kết quả xử lý' sang 'Đã xử lý' và bấm 'Cập nhật'...", "info")
    if not _select_labeled_dropdown(
        driver,
        "Kết quả xử lý",
        KET_QUA_XU_LY_TARGET,
        "Cập nhật kết quả xử lý của phiếu",
    ):
        raise RuntimeError(f"Không chọn được 'Kết quả xử lý' = '{KET_QUA_XU_LY_TARGET}'.")
    time.sleep(0.35)
    steps.append(f"Bước 5: Đã chọn Kết quả xử lý = '{KET_QUA_XU_LY_TARGET}'.")

    upd = driver.execute_script(_JS_CLICK_BUTTON_IN_SECTION, "Cập nhật kết quả xử lý của phiếu", "Cập nhật") or {}
    if not (isinstance(upd, dict) and upd.get("clicked")):
        raise RuntimeError("Không bấm được nút 'Cập nhật' trong khối 'Cập nhật kết quả xử lý của phiếu'.")
    time.sleep(0.6)

    # Xử lý alert/confirm trình duyệt hoặc modal xác nhận nếu có
    try:
        alert = driver.switch_to.alert
        if alert:
            alert.accept()
            time.sleep(0.4)
    except Exception:
        pass
    try:
        driver.execute_script(_JS_ACCEPT_CONFIRM_MODAL_IF_ANY)
    except Exception:
        pass
    steps.append("Bước 5: Đã bấm nút 'Cập nhật' hoàn tất phiếu.")


def execute_complete_ticket(
    session: InsideSession,
    nav_ctx: NavigationContext,
    validation: Dict,
    dry_run: Optional[bool] = None,
    settings: Optional[AutoHoanTatSettings] = None,
    log_cb: Optional[Callable[[str, str], None]] = None,
) -> ExecutionResult:
    """
    Thực thi hoàn tất 1 phiếu PBT (Xác Minh Thông Tin) dựa trên kết quả kiểm tra của Module 3.
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
    val_ket_qua = str(validation.get("ket_qua") or "")
    val_ghi_chu = str(validation.get("ghi_chu") or "")
    ly_do = str(validation.get("ly_do_neu_khong_du") or "")

    if da_hoan_tat:
        return ExecutionResult(
            ma_phieu=ma_phieu,
            tac_vu=tac_vu,
            loai=loai,
            mode=mode_str,
            status=STATUS_SKIPPED_ALREADY_DONE,
            ket_qua="Đã xử lý",
            ghi_chu=val_ghi_chu or ly_do or "Phiếu đã hoàn tất trước đó (bỏ qua).",
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
            ket_qua=val_ket_qua or KET_QUA_KHONG_THANH_CONG,
            ghi_chu=val_ghi_chu or ly_do,
            steps_performed=["Dừng tại Module 3: không đủ điều kiện hoàn tất."],
            post_status=nav_ctx.ticket_status,
            elapsed_ms=int((time.monotonic() - t0) * 1000),
        )

    if is_dry_run:
        planned = [
            "[DRY-RUN] Bước 4: Sẽ bấm nút 'Xem thêm'.",
            f"[DRY-RUN] Bước 4a: Sẽ chọn 'Nguyên nhân chưa nghiệm thu Mỹ Bảo' = '{MY_BAO_TARGET}'.",
            f"[DRY-RUN] Bước 4b: Sẽ chọn Dịch vụ = '{DICH_VU_TARGET}' trong khối 'Nguyên nhân lỗi' -> bấm 'Thêm'.",
            (
                f"[DRY-RUN] Bước 4c: Sẽ chọn lần lượt Tình trạng ban đầu='{TINH_TRANG_BAN_DAU_TARGET}' / "
                f"Phần tử lỗi='{PHAN_TU_LOI_TARGET}' / Nguyên nhân lỗi='{NGUYEN_NHAN_LOI_TARGET}' / "
                f"Hướng xử lý='{HUONG_XU_LY_TARGET}'."
            ),
            f"[DRY-RUN] Bước 5: Sẽ chỉnh 'Kết quả xử lý' sang '{KET_QUA_XU_LY_TARGET}' và bấm nút 'Cập nhật'.",
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
            ket_qua="DRY-RUN: Đủ điều kiện hoàn tất",
            ghi_chu="Đã đạt đủ 2 điều kiện 3a & 3b (chưa bấm Cập nhật vì đang bật DRY-RUN).",
            steps_performed=planned,
            post_status=nav_ctx.ticket_status,
            elapsed_ms=int((time.monotonic() - t0) * 1000),
        )

    # ===== CHẠY THẬT (REAL) =====
    session.ensure_alive()
    driver = session.driver
    steps: List[str] = []

    try:
        _step4_expand_xem_them(driver, steps, log_cb=log_cb)
        _step4a_my_bao(driver, steps, log_cb=log_cb)
        _step4bc_nguyen_nhan_loi(driver, steps, log_cb=log_cb)
        _step5_cap_nhat_ket_qua(driver, steps, log_cb=log_cb)

        # Xác minh lại trạng thái trên giao diện sau khi bấm Cập nhật
        post_status = ""
        toast_ok = False
        deadline = time.monotonic() + 10.0
        while time.monotonic() < deadline:
            time.sleep(0.5)
            post_status = _read_footer_ticket_status(driver)
            if is_already_completed(post_status):
                break
            try:
                toast_info = driver.execute_script(_JS_READ_RESULT_SELECT_OR_TOAST) or {}
                if isinstance(toast_info, dict) and toast_info.get("has_success_toast"):
                    toast_ok = True
                    break
            except Exception:
                pass

        if not is_already_completed(post_status) and not toast_ok:
            return ExecutionResult(
                ma_phieu=ma_phieu,
                tac_vu=tac_vu,
                loai=loai,
                mode=mode_str,
                status=STATUS_ERROR,
                ket_qua=KET_QUA_KHONG_THANH_CONG,
                ghi_chu=(
                    f"Đã bấm 'Cập nhật' nhưng chưa xác minh được trạng thái 'Đã xử lý' trên Inside "
                    f"(trạng thái hiện tại: '{post_status or 'Chưa rõ'}')."
                ),
                steps_performed=steps,
                post_status=post_status,
                elapsed_ms=int((time.monotonic() - t0) * 1000),
            )

        steps.append(f"Xác minh sau hoàn tất thành công: Tình trạng phiếu = '{post_status or 'Đã xử lý'}'.")
        _emit(
            log_cb,
            f"Module 4 [REAL]: Hoàn tất thành công HĐ {ma_phieu} (Trạng thái: {post_status or 'Đã xử lý'}).",
            "success",
        )
        return ExecutionResult(
            ma_phieu=ma_phieu,
            tac_vu=tac_vu,
            loai=loai,
            mode=mode_str,
            status=STATUS_SUCCESS,
            ket_qua="Đã xử lý",
            ghi_chu="Hoàn tất thành công trên Inside.",
            steps_performed=steps,
            post_status=post_status or "Đã xử lý",
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
            ket_qua=KET_QUA_KHONG_THANH_CONG,
            ghi_chu=f"Lỗi thực thi: {exc}",
            steps_performed=steps,
            post_status=_read_footer_ticket_status(driver),
            elapsed_ms=int((time.monotonic() - t0) * 1000),
        )

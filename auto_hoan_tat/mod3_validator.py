"""
Module 3 - Kiểm tra điều kiện hoàn tất PTC/PBT (CHỈ ĐỌC, tuyệt đối không thay đổi dữ liệu).

Quy tắc đã xác nhận cho PBT - Tác Vụ "XÁC MINH THÔNG TIN":
- Kiểm tra Idempotent: Nếu trạng thái phiếu trên Inside hoặc cột Kết Quả trên Sheet đã là "Đã xử lý"/"Đã hoàn tất"
  -> bỏ qua (du_dieu_kien=False, da_hoan_tat=True).
- Điều kiện 0 (Tiên quyết): Card "Ghi nhận ban đầu" phải chứa:
  "KH không cung cấp rõ tình trạng lỗi hoặc KH có khiếu nại RM".
  Nếu không thỏa -> trả đúng thông báo:
  "Không thành công: Phiếu bảo trì có tình trạng ban đầu không thỏa: KH không cung cấp rõ tình trạng lỗi hoặc KH có khiếu nại RM"
- Điều kiện 1 (Check-in): Bấm nút "Lịch sử phân công" (chỉ mở popup xem bảng) -> kiểm tra cột "TG CHECKIN" có giá trị -> đóng popup.
  Nếu trống -> trả đúng thông báo:
  "Không thành công: Phiếu bảo trì chưa checkin. Vui lòng check in và thử lại"
- Điều kiện 2 (Giục tiến độ): Nếu nút "Giục tiến độ" có >= 1 lần -> bấm mở popup "Thông tin giục tiến độ" -> đọc "Kết quả xử lý" -> đóng popup.
  Nếu đang ở trạng thái "Đang xử lý" (chưa "Đã xử lý") -> trả đúng thông báo:
  "Không thành công: Phiếu bảo trì chưa đóng Giục Tiến Độ. Vui lòng cập nhật Giục Tiến Độ và thử lại"

Đầu ra mỗi phiếu:
  {
    "ma_phieu": str,
    "loai": "PTC" | "PBT" | None,
    "tac_vu": str,
    "du_dieu_kien": bool,
    "ly_do_neu_khong_du": str,
    "da_hoan_tat": bool,
    "chi_tiet": dict,
  }
"""

import re
import time
from typing import Callable, Dict, Optional

from .config import AutoHoanTatSettings, load_settings
from .mod1_auth import FeatureDisabledError, InsideSession
from .mod2_navigator import NavigationContext
from .sheet_reader import normalize_nfc

REQUIRED_INITIAL_NOTE = "KH không cung cấp rõ tình trạng lỗi hoặc KH có khiếu nại RM"

ERR_COND0_INITIAL_NOTE = (
    "Không thành công: Phiếu bảo trì có tình trạng ban đầu không thỏa: "
    "KH không cung cấp rõ tình trạng lỗi hoặc KH có khiếu nại RM"
)
ERR_COND1_NOT_CHECKED_IN = (
    "Không thành công: Phiếu bảo trì chưa checkin. Vui lòng check in và thử lại"
)
ERR_COND2_GIUC_TIEN_DO_OPEN = (
    "Không thành công: Phiếu bảo trì chưa đóng Giục Tiến Độ. Vui lòng cập nhật Giục Tiến Độ và thử lại"
)

_JS_READ_INITIAL_NOTE = """
(function() {
  function norm(s) { return String(s || '').replace(/\\s+/g, ' ').trim(); }
  var headings = Array.from(document.querySelectorAll('div, span, h1, h2, h3, h4, h5, h6, p'));
  var card = null;
  for (var i = 0; i < headings.length; i++) {
    var t = norm(headings[i].innerText || headings[i].textContent);
    if (t.toLowerCase() === 'ghi nhận ban đầu') {
      var cur = headings[i];
      for (var k = 0; k < 5 && cur && cur.parentElement; k++) {
        cur = cur.parentElement;
        var ct = norm(cur.innerText || cur.textContent);
        if (ct.length > t.length + 5 && ct.length < 2500) {
          card = cur;
          break;
        }
      }
      if (card) break;
    }
  }
  if (card) {
    return norm(card.innerText || card.textContent);
  }
  return norm((document.body && document.body.innerText) || '').slice(0, 4000);
})();
"""

_JS_CLICK_BUTTON_BY_TEXT = """
(function(needle) {
  function norm(s) { return String(s || '').replace(/\\s+/g, ' ').trim().toLowerCase(); }
  var targetKey = norm(needle);
  var btns = Array.from(document.querySelectorAll('button, a, [role="button"]'));
  for (var i = 0; i < btns.length; i++) {
    var el = btns[i];
    var txt = norm(el.innerText || el.textContent || el.value || '');
    if (!txt || txt.indexOf(targetKey) === -1) continue;
    var r = el.getBoundingClientRect();
    if (r.width <= 0 || r.height <= 0) continue;
    el.scrollIntoView({block: 'center'});
    el.click();
    return {clicked: true, text: txt};
  }
  return {clicked: false, text: ''};
})(arguments[0]);
"""

_JS_READ_ASSIGN_HISTORY_CHECKIN = """
(function() {
  function norm(s) { return String(s || '').replace(/\\s+/g, ' ').trim(); }
  var tables = Array.from(document.querySelectorAll('table'));
  for (var t = 0; t < tables.length; t++) {
    var tbl = tables[t];
    var ths = Array.from(tbl.querySelectorAll('thead th, tr:first-child th, tr:first-child td'));
    var checkinIdx = -1;
    for (var c = 0; c < ths.length; c++) {
      var h = norm(ths[c].innerText || ths[c].textContent).toLowerCase();
      if (h.indexOf('tg checkin') !== -1 || h.indexOf('tg check-in') !== -1 || h.indexOf('check in') !== -1) {
        checkinIdx = c;
        break;
      }
    }
    if (checkinIdx === -1) continue;
    var rows = Array.from(tbl.querySelectorAll('tbody tr'));
    if (!rows.length) {
      var allTr = Array.from(tbl.querySelectorAll('tr'));
      rows = allTr.slice(1);
    }
    var values = [];
    for (var r = 0; r < rows.length; r++) {
      var tds = rows[r].querySelectorAll('td');
      if (tds.length > checkinIdx) {
        var val = norm(tds[checkinIdx].innerText || tds[checkinIdx].textContent);
        if (val && val !== '-' && val !== '--' && val.toLowerCase() !== 'null') {
          values.push(val);
        }
      }
    }
    return {found_table: true, checkin_values: values};
  }
  return {found_table: false, checkin_values: []};
})();
"""

_JS_FIND_GIUC_TIEN_DO_BUTTON = """
(function() {
  function norm(s) { return String(s || '').replace(/\\s+/g, ' ').trim(); }
  var btns = Array.from(document.querySelectorAll('button, a, [role="button"]'));
  for (var i = 0; i < btns.length; i++) {
    var el = btns[i];
    var txt = norm(el.innerText || el.textContent || '');
    if (txt.toLowerCase().indexOf('giục tiến độ') !== -1) {
      var r = el.getBoundingClientRect();
      if (r.width > 0 && r.height > 0) {
        return {found: true, text: txt};
      }
    }
  }
  return {found: false, text: ''};
})();
"""

_JS_READ_GIUC_TIEN_DO_STATUS = """
(function() {
  function norm(s) { return String(s || '').replace(/\\s+/g, ' ').trim(); }
  var dialogs = Array.from(document.querySelectorAll('[role="dialog"], .mud-dialog, .modal, .ant-modal, .el-dialog'));
  var scope = dialogs.length ? dialogs[dialogs.length - 1] : document.body;
  var scopeText = norm((scope && (scope.innerText || scope.textContent)) || '');

  // Tìm select hoặc input gần nhãn "Kết quả xử lý"
  var selects = Array.from(scope.querySelectorAll('select'));
  for (var s = 0; s < selects.length; s++) {
    var sel = selects[s];
    if (sel.selectedIndex >= 0 && sel.options[sel.selectedIndex]) {
      var optTxt = norm(sel.options[sel.selectedIndex].text);
      if (optTxt.toLowerCase().indexOf('xử lý') !== -1) {
        return {found: true, status: optTxt, raw_text: scopeText.slice(0, 600)};
      }
    }
  }

  var inputs = Array.from(scope.querySelectorAll('input, .mud-select-input, .mud-input-slot, [role="combobox"]'));
  for (var i = 0; i < inputs.length; i++) {
    var val = norm(inputs[i].value || inputs[i].innerText || inputs[i].textContent || '');
    if (val.toLowerCase() === 'đang xử lý' || val.toLowerCase() === 'đã xử lý') {
      return {found: true, status: val, raw_text: scopeText.slice(0, 600)};
    }
  }

  var m = scopeText.match(/Kết quả xử lý\\s*:?\\s*(Đang xử lý|Đã xử lý)/i);
  if (m && m[1]) {
    return {found: true, status: norm(m[1]), raw_text: scopeText.slice(0, 600)};
  }
  return {found: false, status: '', raw_text: scopeText.slice(0, 600)};
})();
"""

_JS_CLOSE_POPUP_READONLY = """
(function() {
  function norm(s) { return String(s || '').replace(/\\s+/g, ' ').trim().toLowerCase(); }
  var btns = Array.from(document.querySelectorAll('button, a, [role="button"]'));
  for (var i = btns.length - 1; i >= 0; i--) {
    var el = btns[i];
    var txt = norm(el.innerText || el.textContent || el.getAttribute('aria-label') || '');
    var r = el.getBoundingClientRect();
    if (r.width <= 0 || r.height <= 0) continue;
    if (txt === 'đóng' || txt === 'close' || txt === '×' || txt === 'x') {
      el.click();
      return true;
    }
  }
  return false;
})();
"""


def _norm_ws_lower(text: str) -> str:
    return " ".join(normalize_nfc(text).split()).lower()


def _emit(log_cb: Optional[Callable[[str, str], None]], msg: str, level: str = "info") -> None:
    if log_cb:
        try:
            log_cb(msg, level)
        except Exception:
            pass


def is_already_completed(ticket_status: str = "", sheet_ket_qua: str = "") -> bool:
    """Kiểm tra dấu hiệu phiếu đã hoàn tất trước đó (idempotent)."""
    st = _norm_ws_lower(ticket_status)
    kq = _norm_ws_lower(sheet_ket_qua)
    done_markers = ("đã xử lý", "đã hoàn tất", "hoàn tất thành công")
    if any(m in st for m in done_markers):
        return True
    if kq and not any(err in kq for err in ("không thành công", "lỗi", "chưa")):
        if any(m in kq for m in done_markers):
            return True
    return False


def parse_giuc_tien_do_count(button_text: str) -> int:
    """Trích xuất số lần giục tiến độ từ text nút, ví dụ 'Giục tiến độ (1 lần - Thường)' -> 1."""
    raw = normalize_nfc(button_text)
    if not raw or "giục tiến độ" not in raw.lower():
        return 0
    m = re.search(r"(\d+)\s*lần", raw, flags=re.IGNORECASE)
    if m:
        return int(m.group(1))
    return 0


def evaluate_pbt_xac_minh_conditions(
    ma_phieu: str,
    initial_note_text: str,
    checkin_values: list,
    giuc_count: int,
    giuc_status: str = "",
    ticket_status: str = "",
    sheet_ket_qua: str = "",
) -> Dict:
    """
    Hàm thuần túy đánh giá đủ 4 bước (Idempotent + Điều kiện 0, 1, 2) cho PBT Xác Minh Thông Tin.
    Tách riêng khỏi Selenium để test độc lập cực nhanh và chính xác.
    """
    shd = normalize_nfc(ma_phieu)
    details = {
        "ticket_status": normalize_nfc(ticket_status),
        "sheet_ket_qua": normalize_nfc(sheet_ket_qua),
        "initial_note_text": normalize_nfc(initial_note_text),
        "checkin_values": [normalize_nfc(v) for v in (checkin_values or []) if normalize_nfc(v)],
        "giuc_count": int(giuc_count or 0),
        "giuc_status": normalize_nfc(giuc_status),
    }

    # 0. Idempotent: phiếu đã hoàn tất trước đó
    if is_already_completed(ticket_status=ticket_status, sheet_ket_qua=sheet_ket_qua):
        return {
            "ma_phieu": shd,
            "loai": "PBT",
            "tac_vu": "XÁC MINH THÔNG TIN",
            "du_dieu_kien": False,
            "da_hoan_tat": True,
            "ly_do_neu_khong_du": f"Phiếu đã hoàn tất trước đó (Trạng thái='{details['ticket_status'] or details['sheet_ket_qua']}').",
            "chi_tiet": details,
        }

    # Điều kiện 0: Ghi nhận ban đầu
    if _norm_ws_lower(REQUIRED_INITIAL_NOTE) not in _norm_ws_lower(initial_note_text):
        return {
            "ma_phieu": shd,
            "loai": "PBT",
            "tac_vu": "XÁC MINH THÔNG TIN",
            "du_dieu_kien": False,
            "da_hoan_tat": False,
            "ly_do_neu_khong_du": ERR_COND0_INITIAL_NOTE,
            "chi_tiet": details,
        }

    # Điều kiện 1: Lịch sử phân công -> TG CHECKIN có giá trị
    if not details["checkin_values"]:
        return {
            "ma_phieu": shd,
            "loai": "PBT",
            "tac_vu": "XÁC MINH THÔNG TIN",
            "du_dieu_kien": False,
            "da_hoan_tat": False,
            "ly_do_neu_khong_du": ERR_COND1_NOT_CHECKED_IN,
            "chi_tiet": details,
        }

    # Điều kiện 2: Giục tiến độ >= 1 lần -> Kết quả xử lý phải là Đã xử lý (nếu Đang xử lý -> NOK)
    if details["giuc_count"] >= 1:
        st_low = _norm_ws_lower(giuc_status)
        if st_low != "đã xử lý":
            return {
                "ma_phieu": shd,
                "loai": "PBT",
                "tac_vu": "XÁC MINH THÔNG TIN",
                "du_dieu_kien": False,
                "da_hoan_tat": False,
                "ly_do_neu_khong_du": ERR_COND2_GIUC_TIEN_DO_OPEN,
                "chi_tiet": details,
            }

    return {
        "ma_phieu": shd,
        "loai": "PBT",
        "tac_vu": "XÁC MINH THÔNG TIN",
        "du_dieu_kien": True,
        "da_hoan_tat": False,
        "ly_do_neu_khong_du": "",
        "chi_tiet": details,
    }


def validate_ticket_readonly(
    session: InsideSession,
    nav_ctx: NavigationContext,
    sheet_record: Optional[Dict] = None,
    settings: Optional[AutoHoanTatSettings] = None,
    log_cb: Optional[Callable[[str, str], None]] = None,
) -> Dict:
    """
    Module 3 - Kiểm tra điều kiện hoàn tất trực tiếp trên trang phiếu đã mở (CHỈ ĐỌC).
    Tuyệt đối không bấm 'Thay đổi tình trạng', 'Cập nhật', 'Lưu' hay bất kỳ nút ghi dữ liệu nào.
    """
    cfg = settings or load_settings()
    if not cfg.enabled:
        raise FeatureDisabledError("Chức năng 'Auto Hoàn Tất PTC/PBT' đang TẮT.")

    session.ensure_alive()

    shd = normalize_nfc(nav_ctx.shd)
    tac_vu = normalize_nfc(nav_ctx.tac_vu)
    sheet_kq = normalize_nfc((sheet_record or {}).get("ket_qua", ""))

    # Hiện tại chỉ áp dụng bộ điều kiện chi tiết cho PBT - XÁC MINH THÔNG TIN
    if _norm_ws_lower(tac_vu) != "xác minh thông tin" or nav_ctx.loai != "PBT":
        reason = f"Chưa cấu hình điều kiện hoàn tất cho tác vụ '{tac_vu}' (loại {nav_ctx.loai}). Chỉ áp dụng cho PBT - XÁC MINH THÔNG TIN."
        _emit(log_cb, f"Module 3 [{shd}]: Bỏ qua — {reason}", "warning")
        return {
            "ma_phieu": shd,
            "loai": nav_ctx.loai,
            "tac_vu": tac_vu,
            "du_dieu_kien": False,
            "da_hoan_tat": False,
            "ly_do_neu_khong_du": reason,
            "chi_tiet": {"ticket_status": nav_ctx.ticket_status, "sheet_ket_qua": sheet_kq},
        }

    # Kiểm tra sớm idempotent trước khi mở popup
    if is_already_completed(ticket_status=nav_ctx.ticket_status, sheet_ket_qua=sheet_kq):
        _emit(log_cb, f"Module 3 [{shd}]: Phiếu đã hoàn tất trước đó -> bỏ qua.", "info")
        return evaluate_pbt_xac_minh_conditions(
            ma_phieu=shd,
            initial_note_text="",
            checkin_values=[],
            giuc_count=0,
            giuc_status="",
            ticket_status=nav_ctx.ticket_status,
            sheet_ket_qua=sheet_kq,
        )

    driver = session.driver

    # Điều kiện 0: Đọc card "Ghi nhận ban đầu"
    _emit(log_cb, f"Module 3 [{shd}]: Kiểm tra Điều kiện 0 (Ghi nhận ban đầu)...", "info")
    initial_note_text = str(driver.execute_script(_JS_READ_INITIAL_NOTE) or "")
    if _norm_ws_lower(REQUIRED_INITIAL_NOTE) not in _norm_ws_lower(initial_note_text):
        _emit(log_cb, f"Module 3 [{shd}]: NOK Điều kiện 0.", "warning")
        return evaluate_pbt_xac_minh_conditions(
            ma_phieu=shd,
            initial_note_text=initial_note_text,
            checkin_values=[],
            giuc_count=0,
            giuc_status="",
            ticket_status=nav_ctx.ticket_status,
            sheet_ket_qua=sheet_kq,
        )

    # Điều kiện 1: Bấm "Lịch sử phân công" (chỉ đọc) -> kiểm tra cột "TG CHECKIN" -> đóng popup
    _emit(log_cb, f"Module 3 [{shd}]: Kiểm tra Điều kiện 1 (Lịch sử phân công -> TG CHECKIN)...", "info")
    checkin_values = []
    click_ls = driver.execute_script(_JS_CLICK_BUTTON_BY_TEXT, "lịch sử phân công") or {}
    if click_ls.get("clicked"):
        time.sleep(1.5)
        try:
            ls_info = driver.execute_script(_JS_READ_ASSIGN_HISTORY_CHECKIN) or {}
            checkin_values = ls_info.get("checkin_values") or []
        finally:
            driver.execute_script(_JS_CLOSE_POPUP_READONLY)
            time.sleep(0.5)

    if not checkin_values:
        _emit(log_cb, f"Module 3 [{shd}]: NOK Điều kiện 1 (chưa có TG CHECKIN).", "warning")
        return evaluate_pbt_xac_minh_conditions(
            ma_phieu=shd,
            initial_note_text=initial_note_text,
            checkin_values=[],
            giuc_count=0,
            giuc_status="",
            ticket_status=nav_ctx.ticket_status,
            sheet_ket_qua=sheet_kq,
        )

    # Điều kiện 2: Kiểm tra nút "Giục tiến độ" (>= 1 lần -> mở popup đọc Kết quả xử lý -> đóng popup)
    _emit(log_cb, f"Module 3 [{shd}]: Kiểm tra Điều kiện 2 (Giục tiến độ)...", "info")
    giuc_btn = driver.execute_script(_JS_FIND_GIUC_TIEN_DO_BUTTON) or {}
    giuc_count = parse_giuc_tien_do_count(giuc_btn.get("text", "")) if giuc_btn.get("found") else 0
    giuc_status = ""

    if giuc_count >= 1:
        click_g = driver.execute_script(_JS_CLICK_BUTTON_BY_TEXT, "giục tiến độ") or {}
        if click_g.get("clicked"):
            time.sleep(1.5)
            try:
                g_info = driver.execute_script(_JS_READ_GIUC_TIEN_DO_STATUS) or {}
                giuc_status = str(g_info.get("status") or "")
            finally:
                driver.execute_script(_JS_CLOSE_POPUP_READONLY)
                time.sleep(0.5)

    result = evaluate_pbt_xac_minh_conditions(
        ma_phieu=shd,
        initial_note_text=initial_note_text,
        checkin_values=checkin_values,
        giuc_count=giuc_count,
        giuc_status=giuc_status,
        ticket_status=nav_ctx.ticket_status,
        sheet_ket_qua=sheet_kq,
    )
    if result["du_dieu_kien"]:
        _emit(log_cb, f"Module 3 [{shd}]: ✅ ĐỦ ĐIỀU KIỆN hoàn tất PBT Xác Minh Thông Tin.", "success")
    else:
        _emit(log_cb, f"Module 3 [{shd}]: ⛔ KHÔNG ĐỦ ĐIỀU KIỆN — {result['ly_do_neu_khong_du']}", "warning")
    return result

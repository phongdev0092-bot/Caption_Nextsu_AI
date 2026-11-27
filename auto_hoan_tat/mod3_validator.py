"""
Module 3 - Kiểm tra điều kiện hoàn tất PBT trên màn hình THÔNG TIN BẢO TRÌ (CHỈ ĐỌC).

Quy tắc đã xác nhận cho PBT - Tác Vụ "Xác Minh Thông Tin" (cột J = "Chưa xử lý"):
- Idempotent: Nếu trạng thái phiếu trên Inside hoặc cột Kết Quả trên Sheet đã là "Đã xử lý" / "Đã hoàn tất"
  -> bỏ qua (du_dieu_kien=False, da_hoan_tat=True).
- Điều kiện 3a (Tình trạng ban đầu):
  Đọc bảng cột "Tình trạng ban đầu" (khối "Tình trạng sự cố ban đầu/Hiện tại"):
  Phải là "KH không cung cấp rõ tình trạng lỗi hoặc KH có khiếu nại RM".
  Nếu sai -> Kết Quả = "Không Thành Công",
  Ghi Chú = "Cập nhật lại tình trạng ban đầu KH không cung cấp rõ tình trạng lỗi hoặc KH có khiếu nại RM và thử lại".
- Điều kiện 3b (Lịch sử nhận/nhả tuyến -> Thời gian checkin):
  Bấm nút "Lịch sử nhận/nhả tuyến" -> đọc cột "Thời gian checkin" trong popup -> đóng popup.
  Nếu trống / chưa có giá trị -> Kết Quả = "Không Thành Công",
  Ghi Chú = "Vui lòng check in và thử lại".

Đầu ra mỗi phiếu:
  {
    "ma_phieu": str,
    "loai": "PTC" | "PBT" | None,
    "tac_vu": str,
    "du_dieu_kien": bool,
    "ket_qua": str,
    "ghi_chu": str,
    "ly_do_neu_khong_du": str,
    "da_hoan_tat": bool,
    "chi_tiet": dict,
  }
"""

import time
from typing import Callable, Dict, Optional

from .config import AutoHoanTatSettings, load_settings
from .mod1_auth import FeatureDisabledError, InsideSession
from .mod2_navigator import NavigationContext
from .sheet_reader import normalize_nfc

REQUIRED_INITIAL_NOTE = "KH không cung cấp rõ tình trạng lỗi hoặc KH có khiếu nại RM"

KET_QUA_KHONG_THANH_CONG = "Không Thành Công"

GHI_CHU_SAI_TINH_TRANG_BAN_DAU = (
    "Cập nhật lại tình trạng ban đầu KH không cung cấp rõ tình trạng lỗi hoặc KH có khiếu nại RM và thử lại"
)
GHI_CHU_CHUA_CHECKIN = "Vui lòng check in và thử lại"

ERR_COND0_INITIAL_NOTE = f"{KET_QUA_KHONG_THANH_CONG}: {GHI_CHU_SAI_TINH_TRANG_BAN_DAU}"
ERR_COND1_NOT_CHECKED_IN = f"{KET_QUA_KHONG_THANH_CONG}: {GHI_CHU_CHUA_CHECKIN}"

_JS_READ_INITIAL_STATUS_TABLE = """
(function() {
  function norm(s) {
    var str = String(s || '');
    return (str.normalize ? str.normalize('NFC') : str).replace(/\\s+/g, ' ').trim();
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

  // 1. Tìm bảng có cột 'Tình trạng ban đầu' (nhưng KHÔNG phải bảng dưới khối 'Nguyên nhân lỗi')
  var tables = Array.from(document.querySelectorAll('table')).filter(isVis);
  var foundValues = [];
  for (var t = 0; t < tables.length; t++) {
    var tbl = tables[t];
    var ths = Array.from(tbl.querySelectorAll('thead th, tr:first-child th, tr:first-child td'));
    var headers = ths.map(function(h) { return norm(h.innerText || h.textContent).toLowerCase(); });
    // Bỏ qua bảng 'Nguyên nhân lỗi' (có thêm cột 'phần tử lỗi' / 'hướng xử lý')
    if (headers.some(function(h) { return h.indexOf('phần tử lỗi') !== -1 || h.indexOf('hướng xử lý') !== -1; })) {
      continue;
    }
    var ttIdx = -1;
    for (var c = 0; c < headers.length; c++) {
      if (headers[c].indexOf('tình trạng ban đầu') !== -1) {
        ttIdx = c;
        break;
      }
    }
    if (ttIdx === -1) continue;

    var rows = Array.from(tbl.querySelectorAll('tbody tr'));
    if (!rows.length) {
      rows = Array.from(tbl.querySelectorAll('tr')).slice(1);
    }
    for (var r = 0; r < rows.length; r++) {
      var tds = rows[r].querySelectorAll('td');
      if (tds.length > ttIdx) {
        var cell = tds[ttIdx];
        var txt = norm(cell.innerText || cell.textContent);
        // Nếu cell chứa input/select thì đọc cả value
        if (!txt) {
          var inp = cell.querySelector('input, select, textarea');
          if (inp) txt = norm(inp.value || '');
        }
        // Bỏ dấu 'x' nút xóa chip nếu bị dính ở cuối
        txt = txt.replace(/\\s*[×x]\\s*$/i, '').trim();
        if (txt) foundValues.push(txt);
      }
    }
    if (foundValues.length) {
      return { found_table: true, values: foundValues, text: foundValues.join(' | ') };
    }
  }

  // 2. Fallback: tìm khu vực có nhãn 'Tình trạng sự cố ban đầu' hoặc 'Ghi nhận ban đầu'
  var allCells = Array.from(document.querySelectorAll('td, div, section')).filter(isVis);
  for (var i = 0; i < allCells.length; i++) {
    var ct = norm(allCells[i].innerText || allCells[i].textContent);
    var low = ct.toLowerCase();
    if ((low.indexOf('tình trạng sự cố ban đầu') !== -1 || low.indexOf('ghi nhận ban đầu') !== -1) && ct.length < 1500) {
      var next = allCells[i].nextElementSibling;
      var combined = next ? (ct + ' | ' + norm(next.innerText || next.textContent)) : ct;
      return { found_table: false, values: [combined], text: combined };
    }
  }

  return { found_table: false, values: [], text: '' };
})();
"""

_JS_CLICK_BUTTON_BY_TEXT = """
(function(needle) {
  function norm(s) {
    var str = String(s || '');
    return (str.normalize ? str.normalize('NFC') : str).replace(/\\s+/g, ' ').trim().toLowerCase();
  }
  var targetKey = norm(needle);
  var btns = Array.from(document.querySelectorAll('button, a, input[type="button"], input[type="submit"], [role="button"]'));
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
  function norm(s) {
    var str = String(s || '');
    return (str.normalize ? str.normalize('NFC') : str).replace(/\\s+/g, ' ').trim();
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

  var tables = Array.from(document.querySelectorAll('table')).filter(isVis);
  for (var t = tables.length - 1; t >= 0; t--) {
    var tbl = tables[t];
    var ths = Array.from(tbl.querySelectorAll('thead th, tr:first-child th, tr:first-child td'));
    var checkinIdx = -1;
    for (var c = 0; c < ths.length; c++) {
      var h = norm(ths[c].innerText || ths[c].textContent).toLowerCase();
      if (
        h.indexOf('thời gian checkin') !== -1 ||
        h.indexOf('thời gian check-in') !== -1 ||
        h.indexOf('thời gian check in') !== -1 ||
        h.indexOf('tg checkin') !== -1 ||
        h.indexOf('tg check-in') !== -1
      ) {
        checkinIdx = c;
        break;
      }
    }
    if (checkinIdx === -1) continue;

    var rows = Array.from(tbl.querySelectorAll('tbody tr'));
    if (!rows.length) {
      rows = Array.from(tbl.querySelectorAll('tr')).slice(1);
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
    return {found_table: true, row_count: rows.length, checkin_values: values};
  }
  return {found_table: false, row_count: 0, checkin_values: []};
})();
"""

_JS_CLOSE_POPUP_READONLY = """
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
  var modals = Array.from(document.querySelectorAll('[role="dialog"], .modal, .mud-dialog, .ant-modal, .el-dialog, .dx-popup-normal, .k-window'))
    .filter(isVis);
  var scope = modals.length ? modals[modals.length - 1] : document;

  var closeBtns = Array.from(scope.querySelectorAll('button, a, [role="button"], .close, .mud-dialog-close, .ant-modal-close'))
    .filter(isVis);
  for (var i = closeBtns.length - 1; i >= 0; i--) {
    var el = closeBtns[i];
    var txt = norm(el.innerText || el.textContent || el.getAttribute('aria-label') || el.getAttribute('title') || '');
    var cls = norm(el.className || '');
    if (txt === 'đóng' || txt === 'close' || txt === '×' || txt === 'x' || cls.indexOf('close') !== -1) {
      el.click();
      return true;
    }
  }
  try {
    document.dispatchEvent(new KeyboardEvent('keydown', {key: 'Escape', keyCode: 27, bubbles: true}));
  } catch (e) {}
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


def evaluate_pbt_xac_minh_conditions(
    ma_phieu: str,
    initial_note_text: str,
    checkin_values: list,
    ticket_status: str = "",
    sheet_ket_qua: str = "",
) -> Dict:
    """
    Hàm thuần túy đánh giá đủ các điều kiện cho PBT Xác Minh Thông Tin trên màn hình THÔNG TIN BẢO TRÌ:
    - Idempotent (đã xử lý/hoàn tất -> bỏ qua)
    - Điều kiện 3a: Tình trạng ban đầu == 'KH không cung cấp rõ tình trạng lỗi hoặc KH có khiếu nại RM'
    - Điều kiện 3b: Lịch sử nhận/nhả tuyến -> cột 'Thời gian checkin' có giá trị
    """
    shd = normalize_nfc(ma_phieu)
    details = {
        "ticket_status": normalize_nfc(ticket_status),
        "sheet_ket_qua": normalize_nfc(sheet_ket_qua),
        "initial_note_text": normalize_nfc(initial_note_text),
        "checkin_values": [normalize_nfc(v) for v in (checkin_values or []) if normalize_nfc(v)],
    }

    # 0. Idempotent: phiếu đã hoàn tất trước đó
    if is_already_completed(ticket_status=ticket_status, sheet_ket_qua=sheet_ket_qua):
        return {
            "ma_phieu": shd,
            "loai": "PBT",
            "tac_vu": "XÁC MINH THÔNG TIN",
            "du_dieu_kien": False,
            "da_hoan_tat": True,
            "ket_qua": "Đã xử lý",
            "ghi_chu": f"Phiếu đã hoàn tất trước đó (Trạng thái='{details['ticket_status'] or details['sheet_ket_qua']}').",
            "ly_do_neu_khong_du": f"Phiếu đã hoàn tất trước đó (Trạng thái='{details['ticket_status'] or details['sheet_ket_qua']}').",
            "chi_tiet": details,
        }

    # Điều kiện 3a: Tình trạng ban đầu
    if _norm_ws_lower(REQUIRED_INITIAL_NOTE) not in _norm_ws_lower(initial_note_text):
        return {
            "ma_phieu": shd,
            "loai": "PBT",
            "tac_vu": "XÁC MINH THÔNG TIN",
            "du_dieu_kien": False,
            "da_hoan_tat": False,
            "ket_qua": KET_QUA_KHONG_THANH_CONG,
            "ghi_chu": GHI_CHU_SAI_TINH_TRANG_BAN_DAU,
            "ly_do_neu_khong_du": ERR_COND0_INITIAL_NOTE,
            "chi_tiet": details,
        }

    # Điều kiện 3b: Lịch sử nhận/nhả tuyến -> Thời gian checkin có giá trị
    if not details["checkin_values"]:
        return {
            "ma_phieu": shd,
            "loai": "PBT",
            "tac_vu": "XÁC MINH THÔNG TIN",
            "du_dieu_kien": False,
            "da_hoan_tat": False,
            "ket_qua": KET_QUA_KHONG_THANH_CONG,
            "ghi_chu": GHI_CHU_CHUA_CHECKIN,
            "ly_do_neu_khong_du": ERR_COND1_NOT_CHECKED_IN,
            "chi_tiet": details,
        }

    return {
        "ma_phieu": shd,
        "loai": "PBT",
        "tac_vu": "XÁC MINH THÔNG TIN",
        "du_dieu_kien": True,
        "da_hoan_tat": False,
        "ket_qua": "",
        "ghi_chu": "",
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
    Module 3 - Kiểm tra 2 điều kiện hoàn tất trực tiếp trên trang THÔNG TIN BẢO TRÌ (CHỈ ĐỌC):
      3a. Cột 'Tình trạng ban đầu' == 'KH không cung cấp rõ tình trạng lỗi hoặc KH có khiếu nại RM'
      3b. Bấm 'Lịch sử nhận/nhả tuyến' -> kiểm tra cột 'Thời gian checkin' có giá trị -> đóng popup
    Tuyệt đối không bấm 'Cập nhật' hay thay đổi bất kỳ dữ liệu nào.
    """
    cfg = settings or load_settings()
    if not cfg.enabled:
        raise FeatureDisabledError("Chức năng 'Auto Hoàn Tất PTC/PBT' đang TẮT.")

    session.ensure_alive()

    shd = normalize_nfc(nav_ctx.shd)
    tac_vu = normalize_nfc(nav_ctx.tac_vu)
    sheet_kq = normalize_nfc((sheet_record or {}).get("ket_qua", ""))

    # Hiện tại chỉ áp dụng bộ điều kiện cho PBT - XÁC MINH THÔNG TIN
    if _norm_ws_lower(tac_vu) != "xác minh thông tin" or nav_ctx.loai != "PBT":
        reason = (
            f"Chưa cấu hình điều kiện hoàn tất cho tác vụ '{tac_vu}' (loại {nav_ctx.loai}). "
            "Chỉ áp dụng cho PBT - Xác Minh Thông Tin."
        )
        _emit(log_cb, f"Module 3 [{shd}]: Bỏ qua — {reason}", "warning")
        return {
            "ma_phieu": shd,
            "loai": nav_ctx.loai,
            "tac_vu": tac_vu,
            "du_dieu_kien": False,
            "da_hoan_tat": False,
            "ket_qua": KET_QUA_KHONG_THANH_CONG,
            "ghi_chu": reason,
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
            ticket_status=nav_ctx.ticket_status,
            sheet_ket_qua=sheet_kq,
        )

    driver = session.driver

    # Bước 3a: Đọc cột "Tình trạng ban đầu"
    _emit(log_cb, f"Module 3 [{shd}]: Kiểm tra 3a (Tình trạng ban đầu)...", "info")
    init_res = driver.execute_script(_JS_READ_INITIAL_STATUS_TABLE) or {}
    initial_note_text = str(init_res.get("text") or "") if isinstance(init_res, dict) else str(init_res)
    _emit(log_cb, f"Module 3 [{shd}]: Tình trạng ban đầu đọc được = '{initial_note_text[:120]}'", "info")

    if _norm_ws_lower(REQUIRED_INITIAL_NOTE) not in _norm_ws_lower(initial_note_text):
        _emit(log_cb, f"Module 3 [{shd}]: NOK bước 3a — {GHI_CHU_SAI_TINH_TRANG_BAN_DAU}", "warning")
        return evaluate_pbt_xac_minh_conditions(
            ma_phieu=shd,
            initial_note_text=initial_note_text,
            checkin_values=[],
            ticket_status=nav_ctx.ticket_status,
            sheet_ket_qua=sheet_kq,
        )

    # Bước 3b: Bấm nút "Lịch sử nhận/nhả tuyến" -> kiểm tra cột "Thời gian checkin" -> đóng popup
    _emit(log_cb, f"Module 3 [{shd}]: Kiểm tra 3b (Lịch sử nhận/nhả tuyến -> Thời gian checkin)...", "info")
    checkin_values = []
    click_ls = driver.execute_script(_JS_CLICK_BUTTON_BY_TEXT, "lịch sử nhận/nhả tuyến") or {}
    if not (isinstance(click_ls, dict) and click_ls.get("clicked")):
        # Fallback nếu label ngắn gọn hơn
        click_ls = driver.execute_script(_JS_CLICK_BUTTON_BY_TEXT, "lịch sử phân công") or {}

    if isinstance(click_ls, dict) and click_ls.get("clicked"):
        deadline = time.monotonic() + 6.0
        try:
            while time.monotonic() < deadline:
                time.sleep(0.4)
                ls_info = driver.execute_script(_JS_READ_ASSIGN_HISTORY_CHECKIN) or {}
                if isinstance(ls_info, dict) and ls_info.get("found_table"):
                    checkin_values = ls_info.get("checkin_values") or []
                    if checkin_values or ls_info.get("row_count", 0) > 0:
                        break
        finally:
            try:
                driver.execute_script(_JS_CLOSE_POPUP_READONLY)
                time.sleep(0.4)
            except Exception:
                pass
    else:
        _emit(log_cb, f"Module 3 [{shd}]: Không tìm thấy nút 'Lịch sử nhận/nhả tuyến'.", "warning")

    result = evaluate_pbt_xac_minh_conditions(
        ma_phieu=shd,
        initial_note_text=initial_note_text,
        checkin_values=checkin_values,
        ticket_status=nav_ctx.ticket_status,
        sheet_ket_qua=sheet_kq,
    )
    if result["du_dieu_kien"]:
        _emit(
            log_cb,
            f"Module 3 [{shd}]: ĐẠT cả 2 điều kiện (Tình trạng ban đầu khớp + Thời gian checkin={checkin_values[-1]}).",
            "success",
        )
    else:
        _emit(log_cb, f"Module 3 [{shd}]: NOK — {result['ly_do_neu_khong_du']}", "warning")
    return result


def _main_cli() -> int:
    """CLI chạy kiểm tra CHỈ-ĐỌC độc lập cho 1 SHD trên Inside."""
    import argparse
    import json
    import sys

    from .mod1_auth import create_inside_session
    from .mod2_navigator import navigate_to_ticket

    parser = argparse.ArgumentParser(description="Module 3 - Kiểm tra 2 điều kiện hoàn tất PBT (CHỈ-ĐỌC)")
    parser.add_argument("--shd", required=True, help="Số hợp đồng cần kiểm tra")
    parser.add_argument("--tac-vu", default="Xác Minh Thông Tin", help="Giá trị cột Tác Vụ")
    parser.add_argument("--visible", action="store_true", help="Mở Chrome để quan sát")
    args = parser.parse_args()

    def _print_log(msg: str, lvl: str = "info") -> None:
        print(f"[{time.strftime('%H:%M:%S')}] [{lvl.upper()}] {msg}")

    try:
        with create_inside_session(headless=not args.visible, keep_open=True, log_cb=_print_log) as sess:
            ctx = navigate_to_ticket(sess, shd=args.shd, tac_vu=args.tac_vu, log_cb=_print_log)
            res = validate_ticket_readonly(sess, ctx, log_cb=_print_log)
            print(json.dumps(res, ensure_ascii=False, indent=2))
        return 0
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(_main_cli())

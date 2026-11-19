"""
Module 2 - Điều hướng vào mục Hoàn Tất PTC/PBT & Chế độ Thăm dò CHỈ-ĐỌC.

Nguyên tắc:
- TÁI SỬ DỤNG trực tiếp InsideAssignAutomation từ inside_assign.py (import & gọi lại),
  KHÔNG sửa inside_assign.py và KHÔNG copy nguyên khối code điều hướng.
- Quy tắc chọn tab theo cột Tác Vụ (chuẩn hóa NFC, bỏ khoảng trắng thừa, không phân biệt hoa thường):
  - TRIỂN KHAI         -> loại PTC -> tab TRIỂN KHAI -> nút "Phiếu thi công"
  - BẢO TRÌ            -> loại PBT -> tab BẢO TRÌ    -> nút "Xem CL"
  - XÁC MINH THÔNG TIN -> loại PBT -> tab BẢO TRÌ    -> nút "Xem CL"
  - Giá trị khác/rỗng  -> dừng & báo lỗi rõ ràng, không đoán.
- Xác nhận đúng trang & đúng tab bằng dấu hiệu cụ thể; sai trang/sai tab -> dừng và báo WrongPageError.
- Chế độ thăm dò CHỈ-ĐỌC (probe_ticket): mở phiếu, chụp ảnh màn hình + dump danh sách phần tử ra
  auto_hoan_tat/probe_output/. Tuyệt đối KHÔNG bấm bất kỳ nút nào có tác dụng thay đổi dữ liệu.
"""

from dataclasses import dataclass
import json
import os
import re
import sys
import time
from typing import Callable, Dict, List, Optional

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from inside_assign import InsideAssignAutomation  # noqa: E402

from .config import AutoHoanTatSettings, load_settings  # noqa: E402
from .mod1_auth import (  # noqa: E402
    AuthError,
    FeatureDisabledError,
    InsideSession,
    SessionExpiredError,
    create_inside_session,
)
from .sheet_reader import classify_ticket_type, normalize_nfc  # noqa: E402

_LOGIN_URL_MARKERS = ("login.fpt.net", "iam.fpt.", "login.microsoftonline.com")
_ALLOWED_TICKET_HOSTS = ("inside.fpt.net", "partner.fpt.net", "fox-erp.fpt.net")
_FOX_ERP_HOST = "fox-erp.fpt.net"

_JS_DUMP_DOM_READONLY = """
(function() {
  function norm(s) {
    return String(s || '').replace(/\\s+/g, ' ').trim();
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
  function labelFor(el) {
    try {
      if (el.id) {
        var lbl = document.querySelector('label[for="' + el.id.replace(/"/g, '\\"') + '"]');
        if (lbl) return norm(lbl.innerText || lbl.textContent);
      }
      var p = el.closest('.mud-input-control, .form-group, td, tr');
      if (p) {
        var l2 = p.querySelector('label');
        if (l2) return norm(l2.innerText || l2.textContent);
      }
    } catch (e) {}
    return '';
  }

  var headings = Array.from(document.querySelectorAll('h1,h2,h3,h4,.mud-typography-h5,.mud-typography-h6,.card-title,.panel-title'))
    .filter(isVis)
    .map(function(e) { return norm(e.innerText || e.textContent); })
    .filter(Boolean)
    .slice(0, 30);

  var buttons = Array.from(document.querySelectorAll('button, input[type="button"], input[type="submit"], a.btn, a.mud-button-root'))
    .map(function(e) {
      return {
        tag: e.tagName.toLowerCase(),
        text: norm(e.innerText || e.value || e.getAttribute('title') || e.getAttribute('aria-label') || ''),
        id: e.id || '',
        name: e.name || '',
        type: e.type || '',
        disabled: !!e.disabled || e.getAttribute('aria-disabled') === 'true',
        visible: isVis(e),
        cls: norm(e.className || '').slice(0, 120)
      };
    })
    .filter(function(b) { return b.visible || b.text || b.id; })
    .slice(0, 120);

  var inputs = Array.from(document.querySelectorAll('input:not([type="hidden"]):not([type="button"]):not([type="submit"]), textarea'))
    .map(function(e) {
      return {
        tag: e.tagName.toLowerCase(),
        type: e.type || 'text',
        id: e.id || '',
        name: e.name || '',
        label: labelFor(e),
        placeholder: e.placeholder || '',
        value: (e.type === 'password') ? '***' : norm(e.value || '').slice(0, 120),
        checked: (e.type === 'checkbox' || e.type === 'radio') ? !!e.checked : null,
        disabled: !!e.disabled,
        readonly: !!e.readOnly,
        visible: isVis(e)
      };
    })
    .filter(function(i) { return i.visible || i.id || i.name; })
    .slice(0, 120);

  var selects = Array.from(document.querySelectorAll('select'))
    .map(function(e) {
      var opts = Array.from(e.options || []).map(function(o) { return norm(o.text); }).slice(0, 20);
      var sel = e.selectedIndex >= 0 && e.options[e.selectedIndex] ? norm(e.options[e.selectedIndex].text) : '';
      return {
        id: e.id || '',
        name: e.name || '',
        label: labelFor(e),
        selected: sel,
        options_sample: opts,
        options_count: (e.options || []).length,
        disabled: !!e.disabled,
        visible: isVis(e)
      };
    })
    .slice(0, 60);

  var status_chips = Array.from(document.querySelectorAll('.badge, .label, .mud-chip, [class*="status"], [id*="status"], [id*="Status"], [id*="TrangThai"]'))
    .filter(isVis)
    .map(function(e) { return { id: e.id || '', cls: norm(e.className || '').slice(0, 80), text: norm(e.innerText || e.textContent).slice(0, 120) }; })
    .filter(function(x) { return x.text; })
    .slice(0, 60);

  var iframes = Array.from(document.querySelectorAll('iframe, frame'))
    .map(function(f, idx) { return { index: idx, id: f.id || '', name: f.name || '', src: f.getAttribute('src') || '' }; });

  var body_preview = norm((document.body && document.body.innerText) || '').slice(0, 1500);

  return {
    url: window.location.href,
    title: document.title,
    headings: headings,
    buttons: buttons,
    inputs: inputs,
    selects: selects,
    status_chips: status_chips,
    iframes: iframes,
    body_preview: body_preview
  };
})();
"""


class NavigationError(RuntimeError):
    """Lỗi chung khi điều hướng ở Module 2."""


class UnsupportedTicketTypeError(NavigationError):
    """Cột Tác Vụ trống hoặc không nằm trong danh sách TRIỂN KHAI / BẢO TRÌ / XÁC MINH THÔNG TIN."""


class WrongPageError(NavigationError):
    """Không vào đúng trang hoặc sai tab mục tiêu trên Inside FPT."""


@dataclass
class NavigationContext:
    shd: str
    tac_vu: str
    loai: str
    tab_dich: str
    url: str
    title: str
    window_handle: str
    main_handle: str
    adapter: object
    ticket_status: str = ""


@dataclass
class ProbeResult:
    shd: str
    tac_vu: str
    loai: str
    tab_dich: str
    url: str
    title: str
    screenshot_path: str
    dump_json_path: str
    dump_txt_path: str
    element_summary: Dict


def _safe_filename(text: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "_", str(text or "unknown")).strip("_") or "unknown"


def _emit(log_cb: Optional[Callable[[str, str], None]], msg: str, level: str = "info") -> None:
    if log_cb:
        try:
            log_cb(msg, level)
        except Exception:
            pass


def _build_assign_adapter(
    session: InsideSession,
    log_cb: Optional[Callable[[str, str], None]] = None,
) -> InsideAssignAutomation:
    """
    Khởi tạo adapter tái sử dụng trực tiếp các hàm điều hướng của InsideAssignAutomation
    trên chính WebDriver đã đăng nhập từ Module 1 (không mở Chrome thứ 2).
    """
    adapter = InsideAssignAutomation(headless=True, keep_open=True, log_cb=log_cb)
    adapter.driver = session.driver
    try:
        adapter.main_handle = session.driver.current_window_handle
    except Exception:
        adapter.main_handle = None
    return adapter


def _verify_ticket_window(driver, shd: str, tab_dich: str) -> Dict[str, str]:
    """Xác nhận cửa sổ phiếu vừa mở hợp lệ (không bị đá về login, đúng host Inside/Partner)."""
    curr_url = str(getattr(driver, "current_url", "") or "")
    curr_title = str(getattr(driver, "title", "") or "")
    low_url = curr_url.lower()

    if not curr_url or any(m in low_url for m in _LOGIN_URL_MARKERS):
        raise WrongPageError(
            f"Phiếu '{shd}' (tab {tab_dich}) bị chuyển về trang đăng nhập hoặc URL trống: '{curr_url}'."
        )
    if not any(host in low_url for host in _ALLOWED_TICKET_HOSTS):
        raise WrongPageError(
            f"Phiếu '{shd}' (tab {tab_dich}) mở sai tên miền kỳ vọng (URL='{curr_url}')."
        )
    return {"url": curr_url, "title": curr_title}


def _verify_active_tab(driver, tab_dich: str) -> None:
    """
    Xác nhận đang ở đúng tab đích sau khi click tab trong Thông tin chung.
    Kiểm tra URL iframe hoặc nội dung đặc trưng của tab TRIỂN KHAI / BẢO TRÌ.
    """
    try:
        curr_url = str(driver.execute_script("return window.location.href || '';") or "").lower()
    except Exception:
        curr_url = str(getattr(driver, "current_url", "") or "").lower()

    if any(m in curr_url for m in _LOGIN_URL_MARKERS):
        raise WrongPageError(f"Bị chuyển về trang đăng nhập khi mở tab {tab_dich}: '{curr_url}'.")

    if tab_dich == "TRIỂN KHAI":
        if "/bt/" in curr_url:
            raise WrongPageError(
                f"Sai tab đích: cần 'TRIỂN KHAI' nhưng iframe đang trỏ sang Bảo Trì ('{curr_url}')."
            )
    elif tab_dich == "BẢO TRÌ":
        if "/tk/" in curr_url:
            raise WrongPageError(
                f"Sai tab đích: cần 'BẢO TRÌ' nhưng iframe đang trỏ sang Triển Khai ('{curr_url}')."
            )


def open_ticket_readonly(
    session: InsideSession,
    shd: str,
    tac_vu: str,
    settings: Optional[AutoHoanTatSettings] = None,
    adapter: Optional[InsideAssignAutomation] = None,
    already_on_general_info: bool = False,
    log_cb: Optional[Callable[[str, str], None]] = None,
) -> NavigationContext:
    """
    Điều hướng tới mục Thông tin chung >> chọn đúng tab (TRIỂN KHAI / BẢO TRÌ) >> mở phiếu CHỈ-ĐỌC.
    Tuyệt đối KHÔNG bấm các nút làm thay đổi dữ liệu (Phân tuyến / Cập nhật / Hoàn tất).
    """
    cfg = settings or load_settings()
    if not cfg.enabled:
        raise FeatureDisabledError("Chức năng 'Auto Hoàn Tất PTC/PBT' đang TẮT.")

    session.ensure_alive()

    clean_shd = normalize_nfc(shd)
    if not clean_shd:
        raise NavigationError("Mã phiếu / SHD bị trống.")

    loai, tab_dich, ly_do = classify_ticket_type(tac_vu, cfg.ptc_values, cfg.pbt_values)
    if not loai or not tab_dich:
        raise UnsupportedTicketTypeError(ly_do)

    nav = adapter or _build_assign_adapter(session, log_cb=log_cb)

    if already_on_general_info and getattr(nav, "main_handle", None):
        _emit(log_cb, f"Module 2: Quay về màn hình Thông tin chung để mở HĐ {clean_shd}...", "info")
        nav._return_to_main_form()
    else:
        _emit(log_cb, "Module 2: Điều hướng Inside New V5 >> Hỗ trợ kỹ thuật >> Thông tin chung...", "info")
        nav.navigate_to_assign_page()

    if tab_dich == "TRIỂN KHAI":
        _emit(log_cb, f"Module 2: Mở tab TRIỂN KHAI (PTC) cho HĐ {clean_shd}...", "info")
        nav._click_tab_trien_khai()
        _verify_active_tab(session.driver, tab_dich)
        nav._fill_dieu_kien_nhap(clean_shd)
        nav._open_ptc_window()
    elif tab_dich == "BẢO TRÌ":
        _emit(log_cb, f"Module 2: Mở tab BẢO TRÌ (PBT - {normalize_nfc(tac_vu)}) cho HĐ {clean_shd}...", "info")
        nav._click_tab_bao_tri()
        _verify_active_tab(session.driver, tab_dich)
        nav._fill_nhap_hop_dong(clean_shd)
        nav._open_cl_window()
        _switch_to_fox_erp_if_needed(session.driver, clean_shd, log_cb=log_cb)
    else:
        raise UnsupportedTicketTypeError(f"Tab đích không hỗ trợ: '{tab_dich}'")

    verified = _verify_ticket_window(session.driver, clean_shd, tab_dich)
    win_handle = str(getattr(session.driver, "current_window_handle", "") or "")
    main_handle = str(getattr(nav, "main_handle", "") or "")
    ticket_status = _read_footer_ticket_status(session.driver)

    _emit(
        log_cb,
        f"Module 2: Đã mở đúng cửa sổ phiếu {loai} ({tab_dich}) cho HĐ {clean_shd} | Trạng thái='{ticket_status or 'Chưa rõ'}' | URL={verified['url']}",
        "success",
    )
    return NavigationContext(
        shd=clean_shd,
        tac_vu=normalize_nfc(tac_vu),
        loai=loai,
        tab_dich=tab_dich,
        url=verified["url"],
        title=verified["title"],
        window_handle=win_handle,
        main_handle=main_handle,
        adapter=nav,
        ticket_status=ticket_status,
    )


_JS_CLICK_FOX_ERP_LINK = """
(function() {
  function norm(s) {
    var str = String(s || '');
    return (str.normalize ? str.normalize('NFC') : str).replace(/\\s+/g, ' ').trim().toLowerCase();
  }
  var candidates = Array.from(document.querySelectorAll('a, button, span[role="button"], [onclick]'));
  for (var i = 0; i < candidates.length; i++) {
    var el = candidates[i];
    var href = String(el.getAttribute('href') || '');
    var txt = norm(el.innerText || el.textContent);
    var parentTxt = norm((el.parentElement && (el.parentElement.innerText || el.parentElement.textContent)) || '');
    var grandTxt = norm((el.parentElement && el.parentElement.parentElement && (el.parentElement.parentElement.innerText || el.parentElement.parentElement.textContent)) || '');
    var ctx = parentTxt + ' ' + grandTxt;
    if (href.toLowerCase().indexOf('fox-erp.fpt.net') !== -1 ||
        (txt === 'đây' && (ctx.indexOf('fox-erp') !== -1 || ctx.indexOf('phiên bản mới') !== -1))) {
      el.scrollIntoView({block: 'center'});
      el.click();
      return { found: true, href: href, text: txt };
    }
  }
  return { found: false, href: '', text: '' };
})();
"""


def _try_click_fox_erp_banner(driver) -> Dict:
    """Tìm và bấm link 'Đây' trên top document hoặc bên trong các iframe con."""
    try:
        res = driver.execute_script(_JS_CLICK_FOX_ERP_LINK) or {}
        if isinstance(res, dict) and res.get("found"):
            return res
    except Exception:
        pass

    try:
        frames = driver.find_elements("tag name", "iframe")
    except Exception:
        frames = []

    for frame in frames:
        try:
            driver.switch_to.frame(frame)
            res = driver.execute_script(_JS_CLICK_FOX_ERP_LINK) or {}
            if isinstance(res, dict) and res.get("found"):
                return res
        except Exception:
            pass
        finally:
            try:
                driver.switch_to.default_content()
            except Exception:
                pass
    return {"found": False, "href": "", "text": ""}


def _switch_to_fox_erp_if_needed(
    driver,
    shd: str,
    timeout_sec: float = 45.0,
    banner_wait_sec: float = 6.0,
    post_click_wait_sec: float = 5.0,
    log_cb: Optional[Callable[[str, str], None]] = None,
) -> bool:
    """
    Bước 2 (chuyển giao diện mới FOX-ERP cho PBT):
    - Nếu URL đã ở fox-erp.fpt.net (hoặc hệ thống sau này tự mở thẳng giao diện mới) -> bỏ qua, đi tiếp luôn.
    - Chờ tối đa banner_wait_sec để trang cũ tải xong banner 'Đã có phiên bản mới trên FOX-ERP, nhấn vào Đây để sử dụng.'
      rồi bấm chữ 'Đây' (nếu cần fallback mở trực tiếp href) và chuyển sang tab/trang FOX-ERP mới.
    - Chờ tối đa timeout_sec để SPA FOX-ERP tải xong dữ liệu phiếu.
    """
    curr_url = str(getattr(driver, "current_url", "") or "").lower()
    if _FOX_ERP_HOST in curr_url:
        _emit(log_cb, f"Module 2: HĐ {shd} đã mở thẳng giao diện mới FOX-ERP.", "info")
        return False

    try:
        handles_before = list(getattr(driver, "window_handles", []) or [])
    except Exception:
        handles_before = []

    # Chờ tối đa banner_wait_sec để banner 'Đây' xuất hiện (ưu tiên kiểm tra banner trước)
    click_res: Dict = {"found": False, "href": "", "text": ""}
    banner_deadline = time.monotonic() + max(0.5, float(banner_wait_sec))
    while time.monotonic() < banner_deadline:
        now_url = str(getattr(driver, "current_url", "") or "").lower()
        if _FOX_ERP_HOST in now_url:
            _emit(log_cb, f"Module 2: HĐ {shd} đã tự chuyển sang FOX-ERP.", "info")
            return False

        click_res = _try_click_fox_erp_banner(driver)
        if click_res.get("found"):
            break

        try:
            markers = driver.execute_script(_JS_READ_PBT_MARKERS) or {}
            if isinstance(markers, dict) and markers.get("has_ghi_nhan") and markers.get("has_thay_doi_tt"):
                return False
        except Exception:
            pass
        time.sleep(0.4)

    if not click_res.get("found"):
        return False

    fox_href = str(click_res.get("href") or "").strip()
    _emit(log_cb, f"Module 2: Đã bấm link 'Đây' để chuyển HĐ {shd} sang giao diện mới FOX-ERP (chờ {post_click_wait_sec:.0f}s ổn định trang)...", "info")
    if post_click_wait_sec > 0:
        time.sleep(post_click_wait_sec)

    deadline = time.monotonic() + max(1.0, float(timeout_sec))
    last_log_t = time.monotonic()
    clicked_at = time.monotonic()
    fallback_navigated = False
    switched = False

    while time.monotonic() < deadline:
        try:
            handles_now = list(getattr(driver, "window_handles", []) or [])
            new_handles = [h for h in handles_now if h not in handles_before]
            if new_handles:
                target_h = new_handles[-1]
                if getattr(driver, "current_window_handle", None) != target_h:
                    driver.switch_to.window(target_h)
                    _emit(log_cb, f"Module 2: Đã chuyển sang tab FOX-ERP mới ({getattr(driver, 'current_url', '')}).", "info")
                switched = True
        except Exception:
            pass

        now_url = str(getattr(driver, "current_url", "") or "").lower()

        # Fallback: sau 3.5s nếu chưa mở tab mới và URL vẫn chưa sang fox-erp.fpt.net mà có href hợp lệ -> mở trực tiếp
        if (
            not switched
            and not fallback_navigated
            and _FOX_ERP_HOST not in now_url
            and fox_href.lower().startswith("http")
            and _FOX_ERP_HOST in fox_href.lower()
            and (time.monotonic() - clicked_at) >= 3.5
        ):
            fallback_navigated = True
            _emit(log_cb, f"Module 2: Mở trực tiếp link FOX-ERP cho HĐ {shd}...", "info")
            try:
                driver.get(fox_href)
            except Exception:
                pass

        if _FOX_ERP_HOST in now_url:
            switched = True
            info = _read_pbt_markers_any_frame(driver, keep_in_matching_frame=True)
            if info.get("has_ghi_nhan") or info.get("has_phan_cong") or info.get("has_thay_doi_tt"):
                _emit(log_cb, f"Module 2: Giao diện FOX-ERP cho HĐ {shd} đã tải xong.", "success")
                break

        if time.monotonic() - last_log_t >= 5.0:
            last_log_t = time.monotonic()
            _emit(
                log_cb,
                f"Module 2: Đang chờ FOX-ERP tải dữ liệu phiếu {shd}... (URL={getattr(driver, 'current_url', '')})",
                "info",
            )
        time.sleep(0.4)

    return switched


def close_extra_ticket_tabs(driver, main_handle: str) -> None:
    """Đóng các tab phụ (trang cũ + FOX-ERP) và quay lại cửa sổ chính Thông tin chung."""
    if not main_handle:
        return
    try:
        handles = list(getattr(driver, "window_handles", []) or [])
        for h in handles:
            if h != main_handle:
                try:
                    driver.switch_to.window(h)
                    driver.close()
                except Exception:
                    pass
        driver.switch_to.window(main_handle)
    except Exception:
        pass


_JS_READ_PBT_MARKERS = """
(function() {
  var body = (document.body && (document.body.innerText || document.body.textContent)) || '';
  var norm = body.normalize ? body.normalize('NFC').replace(/\\s+/g, ' ').trim() : body.replace(/\\s+/g, ' ').trim();
  var low = norm.toLowerCase();
  var statusText = '';
  var m = norm.match(/Tình trạng phiếu\\s*:\\s*([^\\n]+?)(?:Thay đổi tình trạng|$)/i);
  if (m && m[1]) {
    statusText = m[1].replace(/[•·]/g, '').trim();
  }
  return {
    has_ghi_nhan: low.indexOf('ghi nhận ban đầu') !== -1,
    has_phan_cong: low.indexOf('thông tin phân công') !== -1 || low.indexOf('lịch sử phân công') !== -1,
    has_thay_doi_tt: low.indexOf('thay đổi tình trạng') !== -1,
    has_thong_tin_chung: low.indexOf('thông tin chung') !== -1,
    ticket_status: statusText,
    body_preview: norm.slice(0, 180),
    ready_state: document.readyState || '',
    iframe_count: document.querySelectorAll('iframe').length
  };
})();
"""


def _read_pbt_markers_any_frame(driver, keep_in_matching_frame: bool = False) -> Dict:
    """
    Đọc dấu hiệu trang chi tiết PBT trên document hiện tại; nếu chưa thấy thì quét thêm các iframe con.
    Nếu keep_in_matching_frame=True và tìm thấy trong iframe con -> giữ driver ở đúng iframe đó để Module 3/4 thao tác.
    """
    top_info: Dict = {}
    try:
        raw = driver.execute_script(_JS_READ_PBT_MARKERS) or {}
        if isinstance(raw, dict):
            top_info = raw
    except Exception:
        top_info = {}

    if top_info.get("has_ghi_nhan") or top_info.get("has_phan_cong") or top_info.get("has_thay_doi_tt"):
        return top_info

    try:
        frames = driver.find_elements("tag name", "iframe")
    except Exception:
        frames = []

    for frame in frames:
        matched = False
        try:
            driver.switch_to.frame(frame)
            sub = driver.execute_script(_JS_READ_PBT_MARKERS) or {}
            if isinstance(sub, dict) and (
                sub.get("has_ghi_nhan") or sub.get("has_phan_cong") or sub.get("has_thay_doi_tt")
            ):
                matched = True
                if not keep_in_matching_frame:
                    driver.switch_to.default_content()
                return sub
        except Exception:
            pass
        finally:
            if not matched:
                try:
                    driver.switch_to.default_content()
                except Exception:
                    pass

    return top_info


def _read_footer_ticket_status(driver) -> str:
    """Đọc nhanh trạng thái phiếu ở thanh footer 'Tình trạng phiếu: ...' (chỉ-đọc)."""
    info = _read_pbt_markers_any_frame(driver, keep_in_matching_frame=False)
    return normalize_nfc(info.get("ticket_status") or "")


def _verify_pbt_detail_markers(driver, shd: str) -> Dict:
    """
    Xác nhận đã vào đúng màn hình chi tiết PBT trên FOX-ERP bằng các dấu hiệu đặc trưng:
    - Card 'Ghi nhận ban đầu'
    - Card 'Thông tin phân công' / nút 'Lịch sử phân công'
    - Footer 'Thay đổi tình trạng'
    Nếu thiếu toàn bộ dấu hiệu -> ném WrongPageError kèm URL & trích đoạn trang để chẩn đoán.
    """
    info = _read_pbt_markers_any_frame(driver, keep_in_matching_frame=True)
    if not isinstance(info, dict):
        return {"ticket_status": ""}

    if not (info.get("has_ghi_nhan") or info.get("has_phan_cong") or info.get("has_thay_doi_tt")):
        curr_url = str(getattr(driver, "current_url", "") or "")
        curr_title = str(getattr(driver, "title", "") or "")
        preview = normalize_nfc(info.get("body_preview") or "")
        iframe_cnt = info.get("iframe_count", 0)
        ready = info.get("ready_state", "")
        raise WrongPageError(
            f"Trang mở cho HĐ {shd} không có dấu hiệu màn hình chi tiết PBT "
            f"(thiếu 'Ghi nhận ban đầu', 'Thông tin phân công' và 'Thay đổi tình trạng'). "
            f"[URL={curr_url} | Title={curr_title} | ready={ready} | iframes={iframe_cnt} | Nội dung='{preview}']"
        )
    return info


def navigate_to_ticket(
    session: InsideSession,
    shd: str,
    tac_vu: str,
    settings: Optional[AutoHoanTatSettings] = None,
    adapter: Optional[InsideAssignAutomation] = None,
    already_on_general_info: bool = False,
    log_cb: Optional[Callable[[str, str], None]] = None,
) -> NavigationContext:
    """
    Hàm điều hướng chính thức của Module 2:
    - Vào đúng tab theo cột Tác Vụ (TRIỂN KHAI / BẢO TRÌ).
    - Mở phiếu theo SHD (chỉ-đọc).
    - Với PBT: xác nhận dấu hiệu màn hình chi tiết PBT ('Ghi nhận ban đầu', 'Thông tin phân công', 'Thay đổi tình trạng').
    """
    ctx = open_ticket_readonly(
        session=session,
        shd=shd,
        tac_vu=tac_vu,
        settings=settings,
        adapter=adapter,
        already_on_general_info=already_on_general_info,
        log_cb=log_cb,
    )
    if ctx.loai == "PBT":
        info = _verify_pbt_detail_markers(session.driver, ctx.shd)
        if info.get("ticket_status"):
            ctx.ticket_status = normalize_nfc(info["ticket_status"])
    return ctx


def _dump_dom_readonly(driver) -> Dict:
    """Thu thập toàn bộ phần tử hiển thị trên trang hiện tại và các iframe con cùng nguồn (chỉ-đọc)."""
    top_dump = driver.execute_script(_JS_DUMP_DOM_READONLY) or {}
    child_dumps: List[Dict] = []

    try:
        iframe_elems = driver.find_elements("tag name", "iframe")
    except Exception:
        iframe_elems = []

    for idx, frame_el in enumerate(iframe_elems):
        try:
            driver.switch_to.frame(frame_el)
            sub = driver.execute_script(_JS_DUMP_DOM_READONLY) or {}
            sub["iframe_index"] = idx
            child_dumps.append(sub)
        except Exception as exc:
            child_dumps.append({"iframe_index": idx, "error": f"Không đọc được iframe: {exc}"})
        finally:
            try:
                driver.switch_to.default_content()
            except Exception:
                pass

    top_dump["child_iframe_dumps"] = child_dumps
    return top_dump


def _format_probe_summary_txt(meta: Dict, dom_dump: Dict) -> str:
    lines = [
        f"=== THĂM DÒ CHỈ-ĐỌC PHIẾU {meta['loai']} ===",
        f"SHD       : {meta['shd']}",
        f"Tác Vụ    : {meta['tac_vu']}",
        f"Loại      : {meta['loai']}",
        f"Tab đích  : {meta['tab_dich']}",
        f"URL       : {dom_dump.get('url', meta['url'])}",
        f"Title     : {dom_dump.get('title', meta['title'])}",
        f"Thời gian : {meta['probed_at']}",
        "",
        "--- TIÊU ĐỀ (HEADINGS) ---",
    ]
    for h in dom_dump.get("headings") or []:
        lines.append(f"  - {h}")

    lines.append("")
    lines.append("--- CÁC NÚT (BUTTONS) ---")
    for b in dom_dump.get("buttons") or []:
        if b.get("visible"):
            lines.append(
                f"  - [{b.get('tag')}] text='{b.get('text')}' id='{b.get('id')}' disabled={b.get('disabled')}"
            )

    lines.append("")
    lines.append("--- CÁC Ô NHẬP (INPUTS / TEXTAREA) ---")
    for inp in dom_dump.get("inputs") or []:
        if inp.get("visible"):
            lines.append(
                f"  - [{inp.get('type')}] label='{inp.get('label')}' id='{inp.get('id')}' "
                f"name='{inp.get('name')}' placeholder='{inp.get('placeholder')}' value='{inp.get('value')}'"
            )

    lines.append("")
    lines.append("--- CÁC DROPDOWN (SELECT) ---")
    for sel in dom_dump.get("selects") or []:
        lines.append(
            f"  - label='{sel.get('label')}' id='{sel.get('id')}' selected='{sel.get('selected')}' "
            f"({sel.get('options_count')} lựa chọn)"
        )

    lines.append("")
    lines.append("--- TRẠNG THÁI / BADGE ---")
    for st in dom_dump.get("status_chips") or []:
        lines.append(f"  - id='{st.get('id')}' text='{st.get('text')}'")

    lines.append("")
    lines.append(f"--- IFRAMES ({len(dom_dump.get('iframes') or [])}) ---")
    for fr in dom_dump.get("iframes") or []:
        lines.append(f"  - [{fr.get('index')}] id='{fr.get('id')}' name='{fr.get('name')}' src='{fr.get('src')}'")

    return "\n".join(lines) + "\n"


def probe_ticket(
    session: InsideSession,
    shd: str,
    tac_vu: str,
    output_dir: Optional[str] = None,
    settings: Optional[AutoHoanTatSettings] = None,
    adapter: Optional[InsideAssignAutomation] = None,
    already_on_general_info: bool = False,
    log_cb: Optional[Callable[[str, str], None]] = None,
) -> ProbeResult:
    """
    Chế độ thăm dò CHỈ-ĐỌC:
    - Mở đúng tab và mở phiếu theo SHD.
    - Chụp ảnh màn hình (.png) và dump toàn bộ phần tử (.json, .txt) vào auto_hoan_tat/probe_output/.
    - Tuyệt đối KHÔNG bấm nút nào có tác dụng thay đổi dữ liệu.
    """
    cfg = settings or load_settings()
    out_dir = output_dir or cfg.probe_output_dir
    os.makedirs(out_dir, exist_ok=True)

    ctx = open_ticket_readonly(
        session=session,
        shd=shd,
        tac_vu=tac_vu,
        settings=cfg,
        adapter=adapter,
        already_on_general_info=already_on_general_info,
        log_cb=log_cb,
    )

    stamp = time.strftime("%Y%m%d_%H%M%S")
    base_name = f"{ctx.loai}_{_safe_filename(ctx.tac_vu)}_{_safe_filename(ctx.shd)}_{stamp}"
    screenshot_path = os.path.join(out_dir, f"{base_name}.png")
    dump_json_path = os.path.join(out_dir, f"{base_name}.json")
    dump_txt_path = os.path.join(out_dir, f"{base_name}.txt")

    _emit(log_cb, f"Module 2 (Thăm dò): Chụp ảnh màn hình và trích xuất phần tử phiếu {ctx.shd}...", "info")
    session.driver.save_screenshot(screenshot_path)
    dom_dump = _dump_dom_readonly(session.driver)

    meta = {
        "shd": ctx.shd,
        "tac_vu": ctx.tac_vu,
        "loai": ctx.loai,
        "tab_dich": ctx.tab_dich,
        "url": ctx.url,
        "title": ctx.title,
        "probed_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "readonly_probe": True,
    }
    payload = {"meta": meta, "dom": dom_dump}

    with open(dump_json_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    with open(dump_txt_path, "w", encoding="utf-8") as f:
        f.write(_format_probe_summary_txt(meta, dom_dump))

    summary = {
        "buttons_visible": sum(1 for b in (dom_dump.get("buttons") or []) if b.get("visible")),
        "inputs_visible": sum(1 for i in (dom_dump.get("inputs") or []) if i.get("visible")),
        "selects": len(dom_dump.get("selects") or []),
        "iframes": len(dom_dump.get("iframes") or []),
        "headings": dom_dump.get("headings") or [],
    }
    _emit(
        log_cb,
        f"Module 2 (Thăm dò): Đã lưu ảnh '{os.path.basename(screenshot_path)}' & dump phần tử '{os.path.basename(dump_txt_path)}'.",
        "success",
    )
    return ProbeResult(
        shd=ctx.shd,
        tac_vu=ctx.tac_vu,
        loai=ctx.loai,
        tab_dich=ctx.tab_dich,
        url=ctx.url,
        title=ctx.title,
        screenshot_path=screenshot_path,
        dump_json_path=dump_json_path,
        dump_txt_path=dump_txt_path,
        element_summary=summary,
    )


def _main_cli() -> int:
    """CLI chạy thăm dò CHỈ-ĐỌC độc lập cho 1 hoặc cả 3 loại phiếu (TRIỂN KHAI / BẢO TRÌ / XÁC MINH THÔNG TIN)."""
    import argparse

    parser = argparse.ArgumentParser(description="Module 2 - Thăm dò CHỈ-ĐỌC màn hình Hoàn Tất PTC/PBT")
    parser.add_argument("--tk", dest="shd_tk", default="", help="SHD thăm dò loại TRIỂN KHAI (PTC)")
    parser.add_argument("--bt", dest="shd_bt", default="", help="SHD thăm dò loại BẢO TRÌ (PBT)")
    parser.add_argument("--xm", dest="shd_xm", default="", help="SHD thăm dò loại XÁC MINH THÔNG TIN (PBT)")
    parser.add_argument("--visible", action="store_true", help="Mở Chrome xem trực tiếp")
    args = parser.parse_args()

    targets = []
    if args.shd_tk.strip():
        targets.append((args.shd_tk.strip(), "TRIỂN KHAI"))
    if args.shd_bt.strip():
        targets.append((args.shd_bt.strip(), "BẢO TRÌ"))
    if args.shd_xm.strip():
        targets.append((args.shd_xm.strip(), "XÁC MINH THÔNG TIN"))

    if not targets:
        print("Vui lòng truyền ít nhất 1 SHD: --tk <SHD> / --bt <SHD> / --xm <SHD>", file=sys.stderr)
        return 2

    def _print_log(msg: str, lvl: str = "info") -> None:
        print(f"[{time.strftime('%H:%M:%S')}] [{lvl.upper()}] {msg}")

    try:
        with create_inside_session(headless=not args.visible, keep_open=True, log_cb=_print_log) as sess:
            adapter = _build_assign_adapter(sess, log_cb=_print_log)
            for idx, (shd, tv) in enumerate(targets):
                res = probe_ticket(
                    session=sess,
                    shd=shd,
                    tac_vu=tv,
                    adapter=adapter,
                    already_on_general_info=(idx > 0),
                    log_cb=_print_log,
                )
                print(f"PROBED OK | {res.loai} ({res.tac_vu}) | SHD={res.shd} | PNG={res.screenshot_path} | TXT={res.dump_txt_path}")
        return 0
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(_main_cli())

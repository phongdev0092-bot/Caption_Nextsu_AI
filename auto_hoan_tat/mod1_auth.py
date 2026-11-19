"""
Module 1 - Đăng nhập hệ thống Inside FPT qua luồng AIM/IAM hiện có.

Nguyên tắc:
- Chỉ GỌI LẠI core_login.run_fpt_login(...) hiện có; KHÔNG sửa, KHÔNG viết lại luồng đăng nhập.
- Đảm bảo không 2 tiến trình nào dùng chung InsideFPT_SessionProfile cùng lúc:
  1) Khóa trong cùng tiến trình: core_login.try_acquire_inside_task(...)
  2) Khóa liên tiến trình bằng file lock nguyên tử (.inside_profile.lock)
  3) Kiểm tra nhanh trạng thái server chính (nếu đang chạy ở localhost:5001)
- Khi session hết hạn -> ném SessionExpiredError rõ ràng, KHÔNG tự retry vô hạn.
- Không bao giờ ghi tài khoản/mật khẩu/token/secret vào log.
"""

from dataclasses import dataclass, field
import json
import os
import sys
import time
import urllib.request
from typing import Callable, Optional

# Đảm bảo import được core_login từ thư mục gốc dự án mà không sửa sys.path vĩnh viễn nếu đã có
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

import core_login  # noqa: E402

from .config import AutoHoanTatSettings, PACKAGE_DIR, load_settings  # noqa: E402

CROSS_PROCESS_LOCK_FILE = os.path.join(PACKAGE_DIR, ".inside_profile.lock")
_AUTH_REDIRECT_MARKERS = ("login.fpt.net", "iam.fpt.", "login.microsoftonline.com")


class AuthError(RuntimeError):
    """Lỗi chung của Module 1."""


class FeatureDisabledError(AuthError):
    """Chức năng Auto Hoàn Tất PTC/PBT đang bị tắt qua cờ cấu hình."""


class ProfileBusyError(AuthError):
    """InsideFPT_SessionProfile đang được tiến trình khác sử dụng."""


class SessionExpiredError(AuthError):
    """Phiên đăng nhập Inside FPT đã hết hạn hoặc bị chuyển về trang đăng nhập."""


def _is_pid_running(pid: int) -> bool:
    """Kiểm tra PID có còn sống không (tương thích Windows/POSIX)."""
    if pid <= 0:
        return False
    if os.name == "nt":
        try:
            import ctypes
            kernel32 = ctypes.windll.kernel32
            PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
            handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, int(pid))
            if not handle:
                return False
            try:
                exit_code = ctypes.c_ulong()
                if kernel32.GetExitCodeProcess(handle, ctypes.byref(exit_code)):
                    return exit_code.value == 259  # STILL_ACTIVE
                return True
            finally:
                kernel32.CloseHandle(handle)
        except Exception:
            return False
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def _check_main_server_busy(overview_url: str) -> Optional[str]:
    """
    Kiểm tra không xâm lấn xem server.py (nếu đang chạy ở cổng 5001) có đang dùng
    InsideFPT_SessionProfile cho tác vụ nào không. Nếu server không chạy -> bỏ qua.
    """
    if not overview_url:
        return None
    try:
        req = urllib.request.Request(overview_url, headers={"User-Agent": "auto_hoan_tat/1.0"})
        with urllib.request.urlopen(req, timeout=1.5) as resp:
            data = json.loads(resp.read().decode("utf-8", errors="ignore"))
        running = data.get("running")
        if isinstance(running, dict) and running.get("tab"):
            # Chỉ các tác vụ dùng InsideFPT_SessionProfile mới xung đột profile
            non_inside_tabs = {"spampool", "bypass_nat", "port"}
            if running.get("tab") not in non_inside_tabs:
                return str(running.get("label") or running.get("tab"))
    except Exception:
        return None
    return None


def _acquire_cross_process_lock(lock_file: str, owner: str) -> None:
    """Tạo file lock nguyên tử (O_CREAT | O_EXCL); tự dọn nếu lock cũ thuộc PID đã chết."""
    os.makedirs(os.path.dirname(lock_file), exist_ok=True)
    payload = json.dumps({"pid": os.getpid(), "owner": owner, "ts": time.time()})
    for _ in range(2):
        try:
            fd = os.open(lock_file, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            try:
                os.write(fd, payload.encode("utf-8"))
            finally:
                os.close(fd)
            return
        except FileExistsError:
            try:
                with open(lock_file, "r", encoding="utf-8") as f:
                    info = json.load(f)
                existing_pid = int(info.get("pid") or 0)
                existing_owner = str(info.get("owner") or "unknown")
            except Exception:
                existing_pid = 0
                existing_owner = "unknown"

            if existing_pid and existing_pid != os.getpid() and _is_pid_running(existing_pid):
                raise ProfileBusyError(
                    f"InsideFPT_SessionProfile đang được dùng bởi tiến trình khác (PID={existing_pid}, tác vụ='{existing_owner}')."
                )
            # Lock cũ từ tiến trình đã kết thúc -> dọn an toàn rồi thử lại 1 lần
            try:
                os.remove(lock_file)
            except OSError as exc:
                raise ProfileBusyError(f"Không thể giải phóng file khóa cũ: {exc}") from exc
    raise ProfileBusyError("Không thể giành khóa độc quyền cho InsideFPT_SessionProfile.")


def _release_cross_process_lock(lock_file: str) -> None:
    try:
        if os.path.exists(lock_file):
            with open(lock_file, "r", encoding="utf-8") as f:
                info = json.load(f)
            if int(info.get("pid") or 0) == os.getpid():
                os.remove(lock_file)
    except Exception:
        pass


def _sanitize_log(msg: str) -> str:
    """Ẩn thông tin nhạy cảm nếu lỡ xuất hiện trong thông điệp log."""
    text = str(msg or "")
    for sensitive in ("password=", "passwd=", "secret=", "token="):
        if sensitive in text.lower():
            return "[ĐÃ ẨN THÔNG TIN NHẠY CẢM]"
    return text


@dataclass
class InsideSession:
    """Context phiên Inside FPT đã đăng nhập, truyền sang Module 2, 3, 4."""

    driver: object
    url: str
    title: str
    task_lock_name: str
    lock_file: str = CROSS_PROCESS_LOCK_FILE
    created_at: float = field(default_factory=time.time)
    log_cb: Optional[Callable[[str, str], None]] = None
    _closed: bool = field(default=False, init=False)

    def _emit(self, msg: str, level: str = "info") -> None:
        if self.log_cb:
            try:
                self.log_cb(_sanitize_log(msg), level)
            except Exception:
                pass

    def is_alive(self) -> bool:
        """Kiểm tra nhanh phiên còn đang ở inside.fpt.net và chưa bị đẩy về trang đăng nhập."""
        if self._closed or self.driver is None:
            return False
        try:
            curr = (self.driver.current_url or "").lower()
        except Exception:
            return False
        if not curr:
            return False
        if any(marker in curr for marker in _AUTH_REDIRECT_MARKERS):
            return False
        return "inside.fpt.net" in curr or "partner.fpt.net" in curr or "fox-erp.fpt.net" in curr

    def ensure_alive(self) -> None:
        """
        Xác nhận phiên còn sống. Nếu hết hạn -> báo lỗi SessionExpiredError ngay,
        tuyệt đối KHÔNG tự động đăng nhập lại / retry vô hạn.
        """
        if self._closed:
            raise SessionExpiredError("Phiên Inside FPT đã bị đóng.")
        if not self.is_alive():
            curr = ""
            try:
                curr = str(getattr(self.driver, "current_url", "") or "")
            except Exception:
                pass
            raise SessionExpiredError(
                f"Phiên đăng nhập Inside FPT đã hết hạn hoặc mất kết nối (URL hiện tại: '{curr}'). "
                "Vui lòng đăng nhập lại trước khi tiếp tục."
            )

    def close(self) -> None:
        """Đóng trình duyệt an toàn và giải phóng toàn bộ khóa profile."""
        if self._closed:
            return
        self._closed = True
        try:
            if self.driver is not None:
                try:
                    self.driver.quit()
                except Exception:
                    pass
                self.driver = None
        finally:
            _release_cross_process_lock(self.lock_file)
            core_login.release_inside_task(self.task_lock_name)
            self._emit("Đã đóng phiên Inside FPT và giải phóng khóa profile.", "info")

    def __enter__(self) -> "InsideSession":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()


def create_inside_session(
    headless: bool = True,
    keep_open: bool = True,
    log_cb: Optional[Callable[[str, str], None]] = None,
    settings: Optional[AutoHoanTatSettings] = None,
    lock_file: str = CROSS_PROCESS_LOCK_FILE,
    check_main_server: bool = True,
) -> InsideSession:
    """
    Khởi tạo Chrome trên InsideFPT_SessionProfile và gọi lại đúng luồng đăng nhập AIM/IAM
    của core_login.run_fpt_login (không tự viết lại login, không retry vô hạn).
    """
    cfg = settings or load_settings()
    if not cfg.enabled:
        raise FeatureDisabledError(
            "Chức năng 'Auto Hoàn Tất PTC/PBT' đang TẮT (AUTO_HOAN_TAT_ENABLED=false)."
        )

    def _safe_log(msg: str, level: str = "info") -> None:
        if log_cb:
            try:
                log_cb(_sanitize_log(msg), level)
            except Exception:
                pass

    # 1. Khóa trong cùng tiến trình
    ok_lock, owner = core_login.try_acquire_inside_task(cfg.task_lock_name)
    if not ok_lock:
        raise ProfileBusyError(
            f"InsideFPT_SessionProfile đang bận chạy tiến trình '{owner}'."
        )

    cross_locked = False
    driver = None
    try:
        # 2. Kiểm tra server.py (nếu đang chạy ở tiến trình khác)
        if check_main_server:
            busy_label = _check_main_server_busy(cfg.main_server_overview_url)
            if busy_label:
                raise ProfileBusyError(
                    f"Hệ thống chính đang chạy tác vụ '{busy_label}' trên InsideFPT_SessionProfile. "
                    "Vui lòng đợi tác vụ đó hoàn tất."
                )

        # 3. Khóa liên tiến trình bằng file lock nguyên tử
        _acquire_cross_process_lock(lock_file, cfg.task_lock_name)
        cross_locked = True

        # 4. Khởi tạo driver dùng đúng helper của core_login (không sửa core_login)
        profile_dir = core_login.get_inside_profile_dir()
        _safe_log("Module 1: Khởi tạo trình duyệt dùng InsideFPT_SessionProfile...", "info")
        driver = core_login.create_driver_with_retry(
            headless=headless,
            profile_dir=profile_dir,
            keep_open=keep_open,
            max_retries=1,
            log_cb=_safe_log,
        )

        # 5. Gọi lại trực tiếp luồng đăng nhập AIM/IAM hiện có
        _safe_log("Module 1: Gọi luồng đăng nhập Inside FPT (AIM/IAM) từ core_login...", "info")
        ok, final_url, page_title = core_login.run_fpt_login(
            headless=headless,
            keep_open=keep_open,
            use_custom_profile=True,
            log_callback=_safe_log,
            driver=driver,
        )

        if not ok:
            raise SessionExpiredError("Đăng nhập Inside FPT thất bại (run_fpt_login trả về False).")

        session = InsideSession(
            driver=driver,
            url=str(final_url or ""),
            title=str(page_title or ""),
            task_lock_name=cfg.task_lock_name,
            lock_file=lock_file,
            log_cb=_safe_log,
        )
        session.ensure_alive()
        _safe_log(f"Module 1: Đăng nhập thành công ({session.title or session.url}).", "success")
        return session

    except Exception:
        if driver is not None:
            try:
                driver.quit()
            except Exception:
                pass
        if cross_locked:
            _release_cross_process_lock(lock_file)
        core_login.release_inside_task(cfg.task_lock_name)
        raise


def _main_cli() -> int:
    """Cho phép chạy kiểm thử thực tế Module 1 độc lập từ dòng lệnh."""
    import argparse

    parser = argparse.ArgumentParser(description="Smoke-test Module 1 (Đăng nhập Inside FPT qua AIM/IAM)")
    parser.add_argument("--visible", action="store_true", help="Mở cửa sổ Chrome trực tiếp để quan sát")
    parser.add_argument("--keep-seconds", type=int, default=3, help="Giữ phiên mở N giây để kiểm tra rồi đóng")
    args = parser.parse_args()

    def _print_log(msg: str, lvl: str = "info") -> None:
        print(f"[{time.strftime('%H:%M:%S')}] [{lvl.upper()}] {msg}")

    try:
        with create_inside_session(headless=not args.visible, keep_open=True, log_cb=_print_log) as sess:
            sess.ensure_alive()
            print(f"OK | URL={sess.url} | TITLE={sess.title}")
            if args.keep_seconds > 0:
                time.sleep(args.keep_seconds)
        return 0
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(_main_cli())

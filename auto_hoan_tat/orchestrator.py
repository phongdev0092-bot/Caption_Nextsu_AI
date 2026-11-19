"""
Orchestrator điều phối toàn luồng Module 1 -> 2 -> 3 -> 4 cho "Auto Hoàn Tất PTC/PBT".

Tính năng an toàn bắt buộc:
- Mặc định DRY-RUN (dry_run=True), không ghi dữ liệu nếu không bật tường minh.
- Rate limit giữa các phiếu (cấu hình được trong settings.rate_limit_seconds).
- Dừng ngay khi gặp N lỗi liên tiếp (settings.max_consecutive_errors).
- Nhật ký audit theo từng phiếu (JSONL) trong auto_hoan_tat/logs/.
- Xuất kết quả CSV (UTF-8 BOM) mở đẹp trên Excel, KHÔNG tự ý ghi lên Google Sheet.
"""

import csv
from dataclasses import dataclass, field
import json
import os
import sys
import threading
import time
from typing import Callable, Dict, List, Optional

from .config import AutoHoanTatSettings, load_settings
from .mod1_auth import FeatureDisabledError, create_inside_session
from .mod2_navigator import (
    _build_assign_adapter,
    close_extra_ticket_tabs,
    navigate_to_ticket,
)
from .mod3_validator import validate_ticket_readonly
from .mod4_executor import (
    ExecutionResult,
    STATUS_DRY_RUN_READY,
    STATUS_ERROR,
    STATUS_NOT_ELIGIBLE,
    STATUS_SKIPPED_ALREADY_DONE,
    STATUS_SUCCESS,
    execute_complete_ticket,
)
from .sheet_reader import classify_ticket_type, fetch_sheet_data, fetch_sheet_from_file, normalize_nfc

STATUS_SKIPPED_UNSUPPORTED = "SKIPPED_UNSUPPORTED"


@dataclass
class BatchRunSummary:
    mode: str
    total: int = 0
    success: int = 0
    dry_run_ready: int = 0
    not_eligible: int = 0
    skipped: int = 0
    errors: int = 0
    stopped_early: bool = False
    stop_reason: str = ""
    audit_log_path: str = ""
    csv_export_path: str = ""
    results: List[Dict] = field(default_factory=list)


def _emit(log_cb: Optional[Callable[[str, str], None]], msg: str, level: str = "info") -> None:
    if log_cb:
        try:
            log_cb(msg, level)
        except Exception:
            pass


def _append_audit_jsonl(path: str, record: Dict) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def export_results_csv(results: List[Dict], csv_path: str) -> str:
    os.makedirs(os.path.dirname(csv_path), exist_ok=True)
    headers = [
        "Thời gian",
        "SHD",
        "Tác Vụ",
        "Loại",
        "Chế độ",
        "Trạng thái xử lý",
        "Kết Quả",
        "Trạng thái sau xử lý",
        "Thời lượng (ms)",
    ]
    with open(csv_path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        for r in results:
            writer.writerow(
                [
                    r.get("timestamp", ""),
                    r.get("ma_phieu", ""),
                    r.get("tac_vu", ""),
                    r.get("loai", ""),
                    r.get("mode", ""),
                    r.get("status", ""),
                    r.get("ket_qua", ""),
                    r.get("post_status", ""),
                    r.get("elapsed_ms", 0),
                ]
            )
    return csv_path


def run_batch(
    rows: List[Dict],
    dry_run: Optional[bool] = None,
    headless: bool = True,
    settings: Optional[AutoHoanTatSettings] = None,
    stop_event: Optional[threading.Event] = None,
    log_cb: Optional[Callable[[str, str], None]] = None,
    progress_cb: Optional[Callable[[int, int, Dict], None]] = None,
    session_factory: Callable = create_inside_session,
) -> BatchRunSummary:
    """
    Chạy lần lượt danh sách bản ghi phiếu (Dict từ sheet_reader) qua Module 1 -> 2 -> 3 -> 4.
    """
    cfg = settings or load_settings()
    if not cfg.enabled:
        raise FeatureDisabledError("Chức năng 'Auto Hoàn Tất PTC/PBT' đang TẮT.")

    is_dry_run = cfg.dry_run_default if dry_run is None else bool(dry_run)
    mode_str = "DRY_RUN" if is_dry_run else "REAL"

    stamp = time.strftime("%Y%m%d_%H%M%S")
    os.makedirs(cfg.log_dir, exist_ok=True)
    audit_path = os.path.join(cfg.log_dir, f"audit_{mode_str.lower()}_{stamp}.jsonl")
    csv_path = os.path.join(cfg.log_dir, f"ket_qua_{mode_str.lower()}_{stamp}.csv")
    run_log_path = os.path.join(cfg.log_dir, f"run_{mode_str.lower()}_{stamp}.log")

    def _tee_log(msg: str, level: str = "info") -> None:
        try:
            with open(run_log_path, "a", encoding="utf-8") as lf:
                lf.write(f"[{time.strftime('%H:%M:%S')}] [{level.upper()}] {msg}\n")
        except Exception:
            pass
        _emit(log_cb, msg, level)

    summary = BatchRunSummary(
        mode=mode_str,
        total=len(rows),
        audit_log_path=audit_path,
        csv_export_path=csv_path,
    )
    if not rows:
        export_results_csv([], csv_path)
        return summary

    consecutive_errors = 0
    _tee_log(
        f"Bắt đầu xử lý {len(rows)} phiếu | Chế độ: {mode_str} | Rate limit: {cfg.rate_limit_sec}s | Dừng sau {cfg.max_consecutive_errors} lỗi liên tiếp.",
        "info",
    )

    with session_factory(headless=headless, keep_open=True, settings=cfg, log_cb=_tee_log) as session:
        adapter = _build_assign_adapter(session, log_cb=_tee_log)
        navigated_once = False

        for idx, row in enumerate(rows, start=1):
            if stop_event and stop_event.is_set():
                summary.stopped_early = True
                summary.stop_reason = "Người dùng yêu cầu dừng tác vụ."
                _tee_log("Đã nhận lệnh DỪNG từ người dùng.", "warn")
                break

            shd = normalize_nfc(row.get("shd") or row.get("ma_phieu") or "")
            tac_vu = normalize_nfc(row.get("tac_vu") or "")
            loai = row.get("loai")
            if not loai and tac_vu:
                loai, _, _ = classify_ticket_type(tac_vu, cfg.ptc_values, cfg.pbt_values)

            # Bỏ qua ngay các phiếu không có SHD hoặc không thuộc loại hợp lệ
            if not shd or not loai:
                rec = {
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "ma_phieu": shd,
                    "tac_vu": tac_vu,
                    "loai": loai or "",
                    "mode": mode_str,
                    "status": STATUS_SKIPPED_UNSUPPORTED,
                    "ket_qua": row.get("loai_ly_do") or "Thiếu SHD hoặc Tác Vụ không hợp lệ.",
                    "post_status": "",
                    "elapsed_ms": 0,
                }
                summary.skipped += 1
                summary.results.append(rec)
                _append_audit_jsonl(audit_path, rec)
                if progress_cb:
                    progress_cb(idx, len(rows), rec)
                continue

            nav_ctx = None
            try:
                nav_ctx = navigate_to_ticket(
                    session=session,
                    shd=shd,
                    tac_vu=tac_vu,
                    settings=cfg,
                    adapter=adapter,
                    already_on_general_info=navigated_once,
                    log_cb=_tee_log,
                )
                navigated_once = True

                val = validate_ticket_readonly(
                    session=session,
                    nav_ctx=nav_ctx,
                    sheet_record=row,
                    settings=cfg,
                    log_cb=_tee_log,
                )
                exec_res: ExecutionResult = execute_complete_ticket(
                    session=session,
                    nav_ctx=nav_ctx,
                    validation=val,
                    dry_run=is_dry_run,
                    settings=cfg,
                    log_cb=_tee_log,
                )
                rec = exec_res.to_dict()
                rec["timestamp"] = time.strftime("%Y-%m-%d %H:%M:%S")
                rec["validation"] = val

                if exec_res.status == STATUS_SUCCESS:
                    summary.success += 1
                    consecutive_errors = 0
                elif exec_res.status == STATUS_DRY_RUN_READY:
                    summary.dry_run_ready += 1
                    consecutive_errors = 0
                elif exec_res.status == STATUS_NOT_ELIGIBLE:
                    summary.not_eligible += 1
                    consecutive_errors = 0
                elif exec_res.status == STATUS_SKIPPED_ALREADY_DONE:
                    summary.skipped += 1
                    consecutive_errors = 0
                else:
                    summary.errors += 1
                    consecutive_errors += 1

            except Exception as exc:
                summary.errors += 1
                consecutive_errors += 1
                rec = {
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "ma_phieu": shd,
                    "tac_vu": tac_vu,
                    "loai": loai or "",
                    "mode": mode_str,
                    "status": STATUS_ERROR,
                    "ket_qua": f"Lỗi: {exc}",
                    "post_status": "",
                    "elapsed_ms": 0,
                }
                _tee_log(f"Lỗi xử lý HĐ {shd}: {exc}", "error")
            finally:
                if nav_ctx and nav_ctx.main_handle:
                    close_extra_ticket_tabs(session.driver, nav_ctx.main_handle)

            summary.results.append(rec)
            _append_audit_jsonl(audit_path, rec)
            if progress_cb:
                progress_cb(idx, len(rows), rec)

            if consecutive_errors >= cfg.max_consecutive_errors:
                summary.stopped_early = True
                summary.stop_reason = (
                    f"Tự động dừng vì gặp {consecutive_errors} lỗi liên tiếp "
                    f"(ngưỡng cấu hình: {cfg.max_consecutive_errors})."
                )
                _tee_log(summary.stop_reason, "error")
                break

            if idx < len(rows) and cfg.rate_limit_sec > 0:
                time.sleep(cfg.rate_limit_sec)

    export_results_csv(summary.results, csv_path)
    _tee_log(
        f"Hoàn tất batch [{mode_str}]: Tổng={summary.total}, Thành công={summary.success}, "
        f"DryRunSẵnSàng={summary.dry_run_ready}, KhôngĐủĐK={summary.not_eligible}, "
        f"BỏQua={summary.skipped}, Lỗi={summary.errors}. CSV: {csv_path}",
        "success",
    )
    return summary


def _main_cli() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Auto Hoàn Tất PTC/PBT - Orchestrator CLI (Module 1->4)")
    parser.add_argument("--shd", default="", help="Chạy lẻ 1 SHD (mặc định Tác Vụ = XÁC MINH THÔNG TIN)")
    parser.add_argument("--tac-vu", default="XÁC MINH THÔNG TIN", help="Giá trị cột Tác Vụ khi dùng --shd")
    parser.add_argument("--csv", dest="csv_file", default="", help="Đọc danh sách phiếu từ file CSV cục bộ")
    parser.add_argument("--from-sheet", action="store_true", help="Đọc danh sách phiếu trực tiếp từ Google Sheet")
    parser.add_argument("--real", action="store_true", help="CHẠY THẬT (mặc định là DRY-RUN nếu không truyền cờ này)")
    parser.add_argument("--visible", action="store_true", help="Hiển thị cửa sổ Chrome để quan sát")
    args = parser.parse_args()

    cfg = load_settings()
    rows: List[Dict] = []

    if args.shd.strip():
        loai, tab_dich, loai_ly_do = classify_ticket_type(args.tac_vu, cfg.ptc_values, cfg.pbt_values)
        rows = [
            {
                "row_id": "CLI_1",
                "tac_vu": normalize_nfc(args.tac_vu),
                "shd": normalize_nfc(args.shd),
                "ma_phieu": normalize_nfc(args.shd),
                "loai": loai,
                "tab_dich": tab_dich,
                "loai_ly_do": loai_ly_do,
                "ket_qua": "",
            }
        ]
    elif args.csv_file.strip():
        data = fetch_sheet_from_file(args.csv_file.strip(), settings=cfg)
        rows = data.get("records") or []
    elif args.from_sheet:
        data = fetch_sheet_data(settings=cfg)
        rows = data.get("records") or []
    else:
        print("Vui lòng chọn nguồn: --shd <SHD> hoặc --csv <file> hoặc --from-sheet", file=sys.stderr)
        return 2

    def _print_log(msg: str, lvl: str = "info") -> None:
        print(f"[{time.strftime('%H:%M:%S')}] [{lvl.upper()}] {msg}")

    summary = run_batch(
        rows=rows,
        dry_run=not args.real,
        headless=not args.visible,
        settings=cfg,
        log_cb=_print_log,
    )
    print(json.dumps(summary.__dict__, ensure_ascii=False, indent=2))
    return 0 if summary.errors == 0 else 1


if __name__ == "__main__":
    raise SystemExit(_main_cli())

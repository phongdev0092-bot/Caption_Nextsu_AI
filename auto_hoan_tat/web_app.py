"""
Giao diện Web độc lập (Phương án A - cổng 5002) cho "Auto Hoàn Tất PTC/PBT".

Nguyên tắc cô lập tuyệt đối:
- Nằm hoàn toàn trong auto_hoan_tat/, KHÔNG sửa server.py, templates/ hay static/ của hệ thống cũ.
- Tái sử dụng CSS của hệ thống cũ (static/style.css, static/ui-polish.css) theo chế độ CHỈ-ĐỌC
  qua route /shared-static/<filename>.
- Mặc định chế độ DRY-RUN luôn BẬT; chế độ CHẠY THẬT yêu cầu xác nhận tường minh từ giao diện.
- Không bao giờ chạy trùng InsideFPT_SessionProfile nhờ cơ chế khóa 3 lớp ở Module 1.
"""

import os
import threading
import time
from typing import Any, Callable, Dict, List, Optional

from flask import Flask, jsonify, render_template, request, send_file, send_from_directory

from .config import AutoHoanTatSettings, load_settings
from .orchestrator import run_batch
from .sheet_reader import fetch_sheet_data, normalize_nfc

_PACKAGE_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.dirname(_PACKAGE_DIR)
_SHARED_STATIC_DIR = os.path.join(_PROJECT_ROOT, "static")


class _RunState:
    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.running: bool = False
        self.mode: str = "DRY_RUN"
        self.started_at: str = ""
        self.finished_at: str = ""
        self.total: int = 0
        self.processed: int = 0
        self.current_shd: str = ""
        self.stop_event: Optional[threading.Event] = None
        self.logs: List[Dict[str, str]] = []
        self.results_by_shd: Dict[str, Dict[str, Any]] = {}
        self.summary: Dict[str, Any] = {}
        self.csv_export_path: str = ""
        self.audit_log_path: str = ""
        self.error: str = ""

    def append_log(self, msg: str, level: str = "info") -> None:
        with self.lock:
            self.logs.append(
                {
                    "time": time.strftime("%H:%M:%S"),
                    "level": level,
                    "message": str(msg),
                }
            )
            if len(self.logs) > 400:
                self.logs = self.logs[-400:]

    def snapshot(self) -> Dict[str, Any]:
        with self.lock:
            return {
                "running": self.running,
                "mode": self.mode,
                "started_at": self.started_at,
                "finished_at": self.finished_at,
                "total": self.total,
                "processed": self.processed,
                "current_shd": self.current_shd,
                "logs": list(self.logs),
                "results_by_shd": dict(self.results_by_shd),
                "summary": dict(self.summary),
                "csv_export_path": self.csv_export_path,
                "audit_log_path": self.audit_log_path,
                "error": self.error,
            }


def create_app(
    settings: Optional[AutoHoanTatSettings] = None,
    sheet_fetcher: Callable = fetch_sheet_data,
    batch_runner: Callable = run_batch,
) -> Flask:
    app = Flask(
        __name__,
        template_folder=os.path.join(_PACKAGE_DIR, "templates"),
        static_folder=os.path.join(_PACKAGE_DIR, "static"),
        static_url_path="/hoan-tat-static",
    )

    state = _RunState()
    cached_rows: Dict[str, Any] = {"records": [], "fetched_at": ""}

    def _get_cfg() -> AutoHoanTatSettings:
        return settings or load_settings()

    @app.route("/shared-static/<path:filename>")
    def shared_static(filename: str):
        return send_from_directory(_SHARED_STATIC_DIR, filename)

    @app.route("/")
    def index():
        cfg = _get_cfg()
        return render_template(
            "hoan_tat_ptc_pbt.html",
            enabled=cfg.enabled,
            sheet_id=cfg.sheet_id,
            sheet_gid=cfg.sheet_gid,
            port=cfg.standalone_port,
        )

    @app.route("/api/config")
    def api_config():
        cfg = _get_cfg()
        return jsonify(
            {
                "enabled": cfg.enabled,
                "sheet_id": cfg.sheet_id,
                "sheet_gid": cfg.sheet_gid,
                "dry_run_default": cfg.dry_run_default,
                "rate_limit_sec": cfg.rate_limit_sec,
                "max_consecutive_errors": cfg.max_consecutive_errors,
                "standalone_port": cfg.standalone_port,
                "ptc_values": list(cfg.ptc_values),
                "pbt_values": list(cfg.pbt_values),
            }
        )

    @app.route("/api/sheet")
    def api_sheet():
        cfg = _get_cfg()
        data = sheet_fetcher(settings=cfg)
        if data.get("status") != "ok":
            return jsonify(data), 502

        records = data.get("records") or []
        cached_rows["records"] = records
        cached_rows["fetched_at"] = time.strftime("%H:%M:%S %d/%m/%Y")

        counts = {
            "total": len(records),
            "pbt": sum(1 for r in records if r.get("loai") == "PBT"),
            "ptc": sum(1 for r in records if r.get("loai") == "PTC"),
            "invalid": sum(1 for r in records if not r.get("loai")),
        }
        return jsonify(
            {
                "status": "ok",
                "fetched_at": cached_rows["fetched_at"],
                "columns": data.get("columns") or [],
                "counts": counts,
                "records": [{k: v for k, v in r.items() if k != "raw"} for r in records],
            }
        )

    @app.route("/api/status")
    def api_status():
        return jsonify(state.snapshot())

    @app.route("/api/logs/clear", methods=["POST"])
    def api_clear_logs():
        with state.lock:
            state.logs = []
        return jsonify({"status": "ok"})

    @app.route("/api/stop", methods=["POST"])
    def api_stop():
        with state.lock:
            if not state.running or state.stop_event is None:
                return jsonify({"status": "idle", "message": "Không có tác vụ nào đang chạy."})
            state.stop_event.set()
        state.append_log("Đã gửi yêu cầu DỪNG — hệ thống sẽ dừng an toàn sau phiếu hiện tại.", "warn")
        return jsonify({"status": "stopping", "message": "Đang dừng tác vụ..."})

    @app.route("/api/run", methods=["POST"])
    def api_run():
        cfg = _get_cfg()
        if not cfg.enabled:
            return (
                jsonify({"status": "error", "message": "Chức năng 'Auto Hoàn Tất PTC/PBT' đang TẮT (enabled=false)."}),
                403,
            )

        payload = request.get_json(silent=True) or {}
        dry_run = bool(payload.get("dry_run", True))
        visible = bool(payload.get("visible", False))
        selected_shds = payload.get("shds")
        rows_override = payload.get("rows")

        if isinstance(rows_override, list) and rows_override:
            target_rows = rows_override
        else:
            all_rows = cached_rows.get("records") or []
            if not all_rows:
                fetched = sheet_fetcher(settings=cfg)
                if fetched.get("status") == "ok":
                    all_rows = fetched.get("records") or []
                    cached_rows["records"] = all_rows
            if isinstance(selected_shds, list) and selected_shds:
                want = {normalize_nfc(s).upper() for s in selected_shds if normalize_nfc(s)}
                target_rows = [r for r in all_rows if normalize_nfc(r.get("shd") or "").upper() in want]
            else:
                target_rows = list(all_rows)

        if not target_rows:
            return jsonify({"status": "error", "message": "Không có phiếu nào để chạy. Hãy tải lại Google Sheet trước."}), 400

        with state.lock:
            if state.running:
                return jsonify({"status": "error", "message": "Đang có tác vụ Auto Hoàn Tất đang chạy."}), 409
            state.running = True
            state.mode = "DRY_RUN" if dry_run else "REAL"
            state.started_at = time.strftime("%H:%M:%S %d/%m/%Y")
            state.finished_at = ""
            state.total = len(target_rows)
            state.processed = 0
            state.current_shd = ""
            state.stop_event = threading.Event()
            state.results_by_shd = {}
            state.summary = {}
            state.csv_export_path = ""
            state.audit_log_path = ""
            state.error = ""
            stop_ev = state.stop_event

        state.append_log(
            f"Khởi chạy {len(target_rows)} phiếu | Chế độ: {'DRY-RUN (Mô phỏng)' if dry_run else 'CHẠY THẬT'}",
            "info",
        )

        def _worker() -> None:
            try:
                def _on_progress(idx: int, total: int, rec: Dict[str, Any]) -> None:
                    with state.lock:
                        state.processed = idx
                        state.total = total
                        shd_key = normalize_nfc(rec.get("ma_phieu") or "").upper()
                        state.current_shd = shd_key
                        if shd_key:
                            state.results_by_shd[shd_key] = rec

                summary = batch_runner(
                    rows=target_rows,
                    dry_run=dry_run,
                    headless=not visible,
                    settings=cfg,
                    stop_event=stop_ev,
                    log_cb=state.append_log,
                    progress_cb=_on_progress,
                )
                with state.lock:
                    state.summary = {
                        "mode": summary.mode,
                        "total": summary.total,
                        "success": summary.success,
                        "dry_run_ready": summary.dry_run_ready,
                        "not_eligible": summary.not_eligible,
                        "skipped": summary.skipped,
                        "errors": summary.errors,
                        "stopped_early": summary.stopped_early,
                        "stop_reason": summary.stop_reason,
                    }
                    state.csv_export_path = summary.csv_export_path
                    state.audit_log_path = summary.audit_log_path
            except Exception as exc:
                with state.lock:
                    state.error = str(exc)
                state.append_log(f"Lỗi nghiêm trọng khi chạy batch: {exc}", "error")
            finally:
                with state.lock:
                    state.running = False
                    state.finished_at = time.strftime("%H:%M:%S %d/%m/%Y")
                    state.current_shd = ""

        t = threading.Thread(target=_worker, daemon=True, name="auto-hoan-tat-worker")
        t.start()
        return jsonify({"status": "started", "mode": state.mode, "total": len(target_rows)})

    @app.route("/api/export-csv")
    def api_export_csv():
        with state.lock:
            csv_path = state.csv_export_path
        if not csv_path or not os.path.exists(csv_path):
            return jsonify({"status": "error", "message": "Chưa có file CSV kết quả nào. Hãy chạy ít nhất 1 lượt trước."}), 404
        return send_file(csv_path, as_attachment=True, download_name=os.path.basename(csv_path))

    return app

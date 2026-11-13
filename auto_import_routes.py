"""Flask Blueprint cho tab Auto Import TK trong giao dien Data Retrieval Tool."""

from __future__ import annotations

import json
import os
import threading
import uuid
from pathlib import Path
from typing import Any, Dict, List

from flask import Blueprint, jsonify, request

from auto_import_config import (
    AUDIT_LOG_FILE,
    DOWNLOAD_ROOT_DIR,
    ENV_FILE,
    get_dataset_config,
    get_default_date_range,
    is_auto_import_enabled,
)
from auto_import_service import run_auto_import, seed_test_table


auto_import_bp = Blueprint("auto_import_bp", __name__)

_state_lock = threading.Lock()
_run_state: Dict[str, Any] = {
    "is_running": False,
    "last_result": None,
}


def _read_recent_audit_logs(limit: int = 20) -> List[Dict[str, Any]]:
    if not AUDIT_LOG_FILE.exists():
        return []
    rows: List[Dict[str, Any]] = []
    try:
        with AUDIT_LOG_FILE.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rows.append(json.loads(line))
                except Exception:
                    continue
        return list(reversed(rows[-limit:]))
    except Exception:
        return []


def _update_env_flag(enabled: bool) -> None:
    val_str = "true" if enabled else "false"
    lines: List[str] = []
    found = False
    if ENV_FILE.exists():
        lines = ENV_FILE.read_text(encoding="utf-8").splitlines()
    new_lines: List[str] = []
    for line in lines:
        if line.strip().startswith("AUTO_IMPORT_ENABLED="):
            new_lines.append(f"AUTO_IMPORT_ENABLED={val_str}")
            found = True
        else:
            new_lines.append(line)
    if not found:
        new_lines.insert(0, f"AUTO_IMPORT_ENABLED={val_str}")
    ENV_FILE.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
    os.environ["AUTO_IMPORT_ENABLED"] = val_str


@auto_import_bp.route("/api/auto-import/status", methods=["GET"])
def api_auto_import_status():
    cfg = get_dataset_config("tk")
    from_d, to_d = get_default_date_range()
    with _state_lock:
        running = _run_state["is_running"]
        last_res = _run_state["last_result"]
    return jsonify(
        {
            "ok": True,
            "enabled": is_auto_import_enabled(),
            "is_running": running,
            "last_result": last_res,
            "config": {
                "dataset": cfg["dataset"],
                "target_table": cfg["target_table"],
                "allowed_partners": cfg["allowed_partners"],
                "default_from_date": from_d,
                "default_to_date": to_d,
            },
            "logs": _read_recent_audit_logs(20),
        }
    )


@auto_import_bp.route("/api/auto-import/toggle", methods=["POST"])
def api_auto_import_toggle():
    payload = request.get_json(silent=True) or {}
    enabled = bool(payload.get("enabled"))
    _update_env_flag(enabled)
    return jsonify({"ok": True, "enabled": is_auto_import_enabled()})


@auto_import_bp.route("/api/auto-import/seed", methods=["POST"])
def api_auto_import_seed():
    payload = request.get_json(silent=True) or {}
    target_table = (payload.get("target_table") or "").strip() or None
    with _state_lock:
        if _run_state["is_running"]:
            return jsonify({"ok": False, "error": "Dang co mot luot Auto Import khac dang chay."}), 409
    try:
        res = seed_test_table(dataset="tk", target_table=target_table)
        return jsonify(res)
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400


@auto_import_bp.route("/api/auto-import/run", methods=["POST"])
def api_auto_import_run():
    with _state_lock:
        if _run_state["is_running"]:
            return jsonify({"ok": False, "error": "Dang co mot luot Auto Import khac dang chay."}), 409
        _run_state["is_running"] = True

    uploaded_path: Path | None = None
    try:
        if request.content_type and "multipart/form-data" in request.content_type:
            dry_run = str(request.form.get("dry_run", "false")).lower() in {"1", "true", "yes"}
            from_date = (request.form.get("from_date") or "").strip() or None
            to_date = (request.form.get("to_date") or "").strip() or None
            partners_raw = (request.form.get("partners") or "").strip()
            target_table = (request.form.get("target_table") or "").strip() or None
            headless = str(request.form.get("headless", "false")).lower() in {"1", "true", "yes"}
            f = request.files.get("file")
            if f and f.filename:
                DOWNLOAD_ROOT_DIR.mkdir(parents=True, exist_ok=True)
                uploaded_path = DOWNLOAD_ROOT_DIR / f"ui_{uuid.uuid4().hex[:8]}_{Path(f.filename).name}"
                f.save(str(uploaded_path))
        else:
            payload = request.get_json(silent=True) or {}
            dry_run = bool(payload.get("dry_run", False))
            from_date = (payload.get("from_date") or "").strip() or None
            to_date = (payload.get("to_date") or "").strip() or None
            partners_raw = (payload.get("partners") or "").strip()
            target_table = (payload.get("target_table") or "").strip() or None
            headless = bool(payload.get("headless", False))

        partner_list = [p.strip() for p in partners_raw.split(",") if p.strip()] if partners_raw else None

        def _worker():
            try:
                res = run_auto_import(
                    dataset="tk",
                    dry_run=dry_run,
                    from_date=from_date,
                    to_date=to_date,
                    partners=partner_list,
                    target_table=target_table,
                    input_file=str(uploaded_path) if uploaded_path else None,
                    headless=headless,
                )
            except Exception as exc:
                res = {"status": "FAILED", "message": str(exc)}
            finally:
                if uploaded_path and uploaded_path.exists():
                    try:
                        uploaded_path.unlink(missing_ok=True)
                    except Exception:
                        pass
                with _state_lock:
                    _run_state["is_running"] = False
                    _run_state["last_result"] = res

        threading.Thread(target=_worker, daemon=True).start()
        return jsonify({"ok": True, "started": True})
    except Exception as exc:
        if uploaded_path and uploaded_path.exists():
            uploaded_path.unlink(missing_ok=True)
        with _state_lock:
            _run_state["is_running"] = False
        return jsonify({"ok": False, "error": str(exc)}), 400

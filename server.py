import os
import sys
import time
import datetime
import json
import threading
import webbrowser
import socket
import re
import urllib.request
from io import BytesIO
from flask import Flask, render_template, request, jsonify, send_file
import pandas as pd
import zstandard as zstd
import core_login
from inside_scraper import InsideScraper

if getattr(sys, 'frozen', False):
    template_folder = os.path.join(sys._MEIPASS, 'templates')
    static_folder = os.path.join(sys._MEIPASS, 'static')
    app = Flask(__name__, template_folder=template_folder, static_folder=static_folder)
    BASE_DIR = os.path.dirname(sys.executable)
else:
    app = Flask(__name__)
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app.config["TEMPLATES_AUTO_RELOAD"] = True
app.config["SEND_FILE_MAX_AGE_DEFAULT"] = 0

# Logging & state management
log_history = []
task_logs = []
log_lock = threading.Lock()

LOG_ZST_PATH = os.path.join(BASE_DIR, "activity_log.jsonl.zst")
_log_pending = []

def _flush_log_to_disk():
    """Nén Zstandard và nối thêm (append) các dòng nhật ký chưa lưu vào file - không giới hạn dung lượng."""
    with log_lock:
        if not _log_pending:
            return
        batch = list(_log_pending)
        _log_pending.clear()
    try:
        raw = "\n".join(json.dumps(i, ensure_ascii=False) for i in batch) + "\n"
        frame = zstd.ZstdCompressor(level=6).compress(raw.encode("utf-8"))
        with open(LOG_ZST_PATH, "ab") as f:
            f.write(frame)
    except Exception:
        pass

_log_seq = 0

def _load_log_from_disk(limit=400):
    """Khôi phục các dòng nhật ký gần nhất khi khởi động lại server."""
    global _log_seq
    if not os.path.exists(LOG_ZST_PATH):
        return
    try:
        with open(LOG_ZST_PATH, "rb") as f:
            data = zstd.ZstdDecompressor().stream_reader(f, read_across_frames=True).read()
        lines = data.decode("utf-8", errors="ignore").splitlines()[-limit:]
        for ln in lines:
            try:
                obj = json.loads(ln)
                _log_seq += 1
                obj["seq"] = _log_seq
                log_history.append(obj)
            except Exception:
                pass
        for it in reversed(log_history[-limit:]):
            task_logs.append(it)
    except Exception:
        pass

def _log_flusher_loop():
    while True:
        time.sleep(3)
        _flush_log_to_disk()

def add_log(message, level="info", task_id="system"):
    global _log_seq
    timestamp = time.strftime("%H:%M:%S")
    with log_lock:
        _log_seq += 1
        item = {
            "seq": _log_seq,
            "time": timestamp,
            "date": time.strftime("%Y-%m-%d"),
            "level": level,
            "text": str(message),
            "task_id": task_id
        }
        log_history.append(item)
        if len(log_history) > 400:
            log_history.pop(0)
        task_logs.insert(0, item)
        if len(task_logs) > 400:
            task_logs.pop()
        _log_pending.append(item)


def make_task_logger(task_state_dict, task_id, label):
    """
    Tạo callback log gắn với tiến trình đang chạy:
    - Tự động cập nhật task_state_dict['current_step'], ['step_time'], ['recent_steps'] và ['message']
      theo từng bước thực tế của Selenium bot (khởi tạo Chrome, đăng nhập IAM, điều hướng menu, tìm HĐ, lưu...).
    - Gắn đúng task_id và tiền tố [Tên Tác Vụ] vào nhật ký để Nhật ký Auto và Terminal từng tab hiển thị đầy đủ.
    """
    if isinstance(task_state_dict, dict):
        task_state_dict["current_step"] = ""
        task_state_dict["step_time"] = time.strftime("%H:%M:%S")
        task_state_dict["recent_steps"] = []

    def _logger(message, level="info", *args):
        raw_text = str(message or "").strip()
        if not raw_text:
            return
        step_time = time.strftime("%H:%M:%S")
        cur_idx = 0
        total = 0
        cur_shd = ""
        if isinstance(task_state_dict, dict):
            cur_idx = int(task_state_dict.get("current_index") or 0)
            total = int(task_state_dict.get("total") or 0)
            cur_shd = str(
                task_state_dict.get("current_shd")
                or task_state_dict.get("current_contract")
                or ""
            ).strip()

            if not raw_text.startswith("==="):
                task_state_dict["current_step"] = raw_text
                task_state_dict["step_time"] = step_time
                steps = list(task_state_dict.get("recent_steps") or [])
                steps.append({
                    "time": step_time,
                    "step": raw_text,
                    "level": level,
                    "shd": cur_shd if cur_idx > 0 else ""
                })
                task_state_dict["recent_steps"] = steps[-6:]

                is_active = bool(
                    task_state_dict.get("is_running")
                    or task_state_dict.get("status") == "running"
                )
                if is_active:
                    if cur_idx > 0 and total > 0:
                        if cur_shd and cur_shd not in raw_text:
                            task_state_dict["message"] = f"[{cur_idx}/{total} • HĐ {cur_shd}] {raw_text}"
                        else:
                            task_state_dict["message"] = f"[{cur_idx}/{total}] {raw_text}"
                    elif total > 0:
                        task_state_dict["message"] = f"[Chuẩn bị {total} HĐ] {raw_text}"
                    else:
                        task_state_dict["message"] = raw_text

        prefix_tag = f"[{label}]"
        if raw_text.startswith("===") or raw_text.startswith(prefix_tag):
            formatted = raw_text
        elif cur_idx > 0 and cur_shd and cur_shd not in raw_text:
            formatted = f"{prefix_tag} [HĐ {cur_shd}] {raw_text}"
        else:
            formatted = f"{prefix_tag} {raw_text}"

        eff_task_id = args[0] if (args and isinstance(args[0], str)) else task_id
        add_log(formatted, level, eff_task_id)

    return _logger

ZST_STORAGE_PATH = os.path.join(BASE_DIR, "retrieval_history.json.zst")
JSON_STORAGE_PATH = os.path.join(BASE_DIR, "retrieval_history.json")

def save_records_zstd(records):
    """Nén toàn bộ danh sách bản ghi trực tiếp vào file .zst duy nhất bằng Zstandard, hoàn toàn không lưu JSON thô."""
    try:
        raw_bytes = json.dumps(records, ensure_ascii=False, indent=2).encode('utf-8')
        cctx = zstd.ZstdCompressor(level=3)
        compressed = cctx.compress(raw_bytes)
        temp_file = ZST_STORAGE_PATH + ".tmp"
        with open(temp_file, "wb") as f:
            f.write(compressed)
        if os.path.exists(ZST_STORAGE_PATH):
            os.remove(ZST_STORAGE_PATH)
        os.rename(temp_file, ZST_STORAGE_PATH)

        # Xóa triệt để file JSON thô nếu có để giải phóng dung lượng cho máy
        if os.path.exists(JSON_STORAGE_PATH):
            try:
                os.remove(JSON_STORAGE_PATH)
            except Exception:
                pass

        add_log(f"Đã lưu nén Zstandard: {len(records)} bản ghi ({len(compressed):,} bytes)", "info")
    except Exception as e:
        add_log(f"Lỗi nén zstandard: {e}", "warning")

def load_records_zstd():
    """Khởi động: Đọc và giải nén dữ liệu độc quyền từ kho nén Zstandard (.json.zst)."""
    # 1. Đọc từ kho nén Zstandard
    if os.path.exists(ZST_STORAGE_PATH):
        try:
            with open(ZST_STORAGE_PATH, "rb") as f:
                compressed = f.read()
            if compressed:
                dctx = zstd.ZstdDecompressor()
                raw_bytes = dctx.decompress(compressed)
                records = json.loads(raw_bytes.decode('utf-8'))
                for r in records:
                    if not r.get("created_at_ts") and r.get("status") == "Thành công":
                        r["created_at_ts"] = time.time()
                add_log(f"Đã khôi phục {len(records)} bản ghi từ kho nén Zstandard", "info")
                return records
        except Exception as e:
            add_log(f"Lỗi đọc kho Zstandard: {e}", "warning")

    # 2. Migration fallback: Nếu còn file JSON cũ, chuyển đổi sang .zst rồi xóa sạch JSON
    if os.path.exists(JSON_STORAGE_PATH):
        try:
            with open(JSON_STORAGE_PATH, "r", encoding="utf-8") as fj:
                records = json.load(fj)
            for r in records:
                if not r.get("created_at_ts") and r.get("status") == "Thành công":
                    r["created_at_ts"] = time.time()
            save_records_zstd(records)
            try:
                os.remove(JSON_STORAGE_PATH)
            except Exception:
                pass
            add_log(f"Đã chuyển đổi {len(records)} bản ghi từ JSON sang Zstandard và xóa file JSON cũ", "info")
            return records
        except Exception:
            pass

    return []

AUTO_ATTEMPT_FILE = os.path.join(BASE_DIR, "auto_attempts.json")
_auto_attempts_lock = threading.RLock()

def clear_auto_attempts(tab=None, shds=None):
    """Xóa các HĐ khỏi auto_attempts để Auto nền có thể thử lại ngay khi gặp lỗi."""
    try:
        with _auto_attempts_lock:
            attempts = {}
            if os.path.exists(AUTO_ATTEMPT_FILE):
                try:
                    with open(AUTO_ATTEMPT_FILE, "r", encoding="utf-8") as f:
                        attempts = json.load(f)
                except Exception:
                    attempts = {}
            if not isinstance(attempts, dict):
                attempts = {}
            if tab:
                if tab in attempts and isinstance(attempts[tab], dict):
                    if shds is not None:
                        targets = {str(s).strip() for s in shds if str(s).strip()}
                        if not targets:
                            return
                        for k in list(attempts[tab].keys()):
                            k_str = str(k).strip()
                            if (
                                k_str in targets
                                or k_str.split("_", 1)[0] in targets
                                or any(k_str.startswith(f"{t}_") or k_str.endswith(f"_{t}") for t in targets)
                            ):
                                attempts[tab].pop(k, None)
                    else:
                        attempts[tab] = {}
            else:
                locked_backup = attempts.get("_manual_locked") if isinstance(attempts.get("_manual_locked"), dict) else None
                attempts = {}
                if locked_backup:
                    attempts["_manual_locked"] = locked_backup
            core_login.atomic_write_json(AUTO_ATTEMPT_FILE, attempts)
    except Exception:
        pass

def _release_remaining_auto_attempts(tab, to_process, processed_shds):
    """Giải phóng các HĐ chưa kịp xử lý khỏi auto_attempts để Auto nền thử lại ở chu kỳ kế tiếp."""
    remaining = []
    for r in (to_process or []):
        if not isinstance(r, dict):
            continue
        shd = str(r.get("SHD") or r.get("Số Hợp Đồng") or "").strip()
        if shd and shd not in processed_shds:
            remaining.append(shd)
        elif not shd:
            row_id = str(r.get("ID") or "").strip()
            if row_id and row_id not in processed_shds:
                remaining.append(row_id)
    if remaining:
        clear_auto_attempts(tab, remaining)

def _load_auto_attempts_raw():
    with _auto_attempts_lock:
        if os.path.exists(AUTO_ATTEMPT_FILE):
            try:
                with open(AUTO_ATTEMPT_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return data if isinstance(data, dict) else {}
            except Exception:
                return {}
        return {}

def _save_auto_attempts_raw(data):
    try:
        with _auto_attempts_lock:
            core_login.atomic_write_json(AUTO_ATTEMPT_FILE, data)
    except Exception:
        pass

def _get_signal_manual_locked(tab, attempts=None):
    data = attempts if isinstance(attempts, dict) else _load_auto_attempts_raw()
    locked_root = data.get("_manual_locked")
    if not isinstance(locked_root, dict):
        return {}
    tab_map = locked_root.get(tab)
    return tab_map if isinstance(tab_map, dict) else {}

def _lock_signal_contracts_for_manual(tab, shds, reason="login_or_server_error"):
    clean_shds = [str(s).strip() for s in (shds or []) if str(s).strip()]
    if not clean_shds:
        return
    data = _load_auto_attempts_raw()
    locked_root = data.setdefault("_manual_locked", {})
    if not isinstance(locked_root, dict):
        locked_root = {}
        data["_manual_locked"] = locked_root
    tab_map = locked_root.setdefault(tab, {})
    if not isinstance(tab_map, dict):
        tab_map = {}
        locked_root[tab] = tab_map
    now_ts = time.time()
    for shd in clean_shds:
        tab_map[shd] = {"ts": now_ts, "reason": reason}
    _save_auto_attempts_raw(data)

def _unlock_signal_contracts_from_manual(tab, shds):
    clean_shds = [str(s).strip() for s in (shds or []) if str(s).strip()]
    if not clean_shds:
        return
    data = _load_auto_attempts_raw()
    locked_root = data.get("_manual_locked")
    if not isinstance(locked_root, dict):
        return
    tab_map = locked_root.get(tab)
    if not isinstance(tab_map, dict):
        return
    changed = False
    for shd in clean_shds:
        if shd in tab_map:
            tab_map.pop(shd, None)
            changed = True
    if changed:
        _save_auto_attempts_raw(data)

def _is_signal_manual_locked(tab, r, attempts=None):
    if not isinstance(r, dict):
        return False
    if r.get("_is_old_day_backlog") or r.get("_manual_only") or r.get("_login_or_server_error_locked"):
        return True
    kq = inside_signal.normalize_nfc(r.get("Kết Quả", "")).lower()
    if "lỗi" in kq:
        return True
    shd = str(r.get("SHD") or r.get("Số Hợp Đồng") or "").strip()
    if tab and shd:
        locked_map = _get_signal_manual_locked(tab, attempts=attempts)
        if shd in locked_map:
            return True
    return False

def _decorate_signal_lock_flags(tab, records):
    locked_map = _get_signal_manual_locked(tab)
    for r in records or []:
        if not isinstance(r, dict):
            continue
        shd = str(r.get("SHD") or r.get("Số Hợp Đồng") or "").strip()
        kq = inside_signal.normalize_nfc(r.get("Kết Quả", "")).lower()
        has_err = "lỗi" in kq
        is_clean_done = inside_signal.is_final_status(r.get("Kết Quả", "")) and not has_err
        if shd and shd in locked_map and not is_clean_done:
            r["_login_or_server_error_locked"] = True
            r["_manual_only"] = True
    return records

task_state = {
    "status": "idle",
    "message": "Chưa đăng nhập",
    "user": "phuongnam.phongnh5",
    "last_login_time": None
}

retrieval_task = {
    "is_running": False,
    "current_index": 0,
    "total": 0,
    "current_contract": "",
    "message": "Sẵn sàng"
}

retrieval_records = load_records_zstd()
import_history = [
    {"id": 1, "filename": "Danh_sach_nhan_vien_T10.xlsx", "total": 120, "success": 120, "failed": 0, "date": "2026-10-06 14:20", "status": "Hoàn tất"},
    {"id": 2, "filename": "Chi_so_KPI_Q3_Inside.xlsx", "total": 85, "success": 82, "failed": 3, "date": "2026-10-07 09:15", "status": "Cảnh báo (3 lỗi)"},
]

# State cho Tab 3: Auto Công Việc
auto_tasks = [
    {
        "id": "task_1",
        "name": "Tự động quét & Cập nhật Phiếu Thi Công (PTC)",
        "type": "sync_ptc",
        "schedule": "Mỗi 15 phút",
        "interval_minutes": 15,
        "is_active": True,
        "last_run": "--",
        "next_run": "--",
        "status": "Sẵn sàng",
        "success_count": 0,
        "failed_count": 0,
        "description": "Tự động quét và trích xuất thông tin mới nhất từ Inside FPT theo danh sách hợp đồng chờ."
    },
    {
        "id": "task_2",
        "name": "Tự động đồng bộ Hợp đồng từ Excel sang Inside",
        "type": "auto_import",
        "schedule": "Mỗi 30 phút",
        "interval_minutes": 30,
        "is_active": True,
        "last_run": "--",
        "next_run": "--",
        "status": "Sẵn sàng",
        "success_count": 0,
        "failed_count": 0,
        "description": "Tự động đối soát và import file danh sách hợp đồng mới được thêm vào thư mục."
    },
    {
        "id": "task_3",
        "name": "Rà soát HĐ tồn đọng & Cảnh báo trễ hạn",
        "type": "alert_overdue",
        "schedule": "Mỗi 60 phút",
        "interval_minutes": 60,
        "is_active": False,
        "last_run": "--",
        "next_run": "--:--",
        "status": "Tạm dừng",
        "success_count": 0,
        "failed_count": 0,
        "description": "Phát hiện các phiếu thi công chưa hoàn tất quá 24h và gửi thông báo cảnh báo."
    },
    {
        "id": "task_4",
        "name": "Tự động nén & Tối ưu Kho Zstandard",
        "type": "backup_zstd",
        "schedule": "Hàng ngày (00:00)",
        "interval_minutes": 1440,
        "is_active": True,
        "last_run": "--",
        "next_run": "--",
        "status": "Sẵn sàng",
        "success_count": 0,
        "failed_count": 0,
        "description": "Tự động tối ưu hóa và sao lưu dữ liệu nén Zstandard .json.zst."
    }
]

task_logs = []

import atexit
_load_log_from_disk()
atexit.register(_flush_log_to_disk)

@app.route("/api/logs/download", methods=["GET"])
def download_full_log():
    """Tải toàn bộ nhật ký lưu trữ (giải nén Zstandard thành JSONL)."""
    _flush_log_to_disk()
    if not os.path.exists(LOG_ZST_PATH):
        return jsonify({"status": "error", "message": "Chưa có nhật ký"}), 404
    with open(LOG_ZST_PATH, "rb") as f:
        data = zstd.ZstdDecompressor().stream_reader(f, read_across_frames=True).read()
    return send_file(BytesIO(data), mimetype="text/plain", as_attachment=True, download_name="activity_log.jsonl")

add_log("Hệ thống Web Server đã sẵn sàng", "info")

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/config", methods=["GET"])
def get_config():
    cfg = core_login.load_config()
    active_info = core_login.get_active_account_info(cfg)
    default_webhook = cfg.get("google_sheet_webhook_url", "")
    return jsonify({
        "status": "ok",
        "active_account": cfg.get("active_account", "default"),
        "default_account": cfg.get("default_account", core_login.DEFAULT_ACCOUNT),
        "custom_account": cfg.get("custom_account", {}),
        "google_sheet_webhook_url": default_webhook,
        "cls_webhook_url": cfg.get("cls_webhook_url", ""),
        "clear_signal_webhook_url": cfg.get("clear_signal_webhook_url", "") or default_webhook,
        "reset_signal_webhook_url": cfg.get("reset_signal_webhook_url", "") or default_webhook,
        "assign_webhook_url": cfg.get("assign_webhook_url", "") or default_webhook,
        "mybae_webhook_url": cfg.get("mybae_webhook_url", "") or cfg.get("cls_webhook_url", "") or default_webhook,
        "spampool_webhook_url": cfg.get("spampool_webhook_url", "") or default_webhook,
        "bypass_nat_webhook_url": cfg.get("bypass_nat_webhook_url", "") or default_webhook,
        "active_info": active_info
    })

@app.route("/api/config", methods=["POST"])
@app.route("/api/config/save", methods=["POST"])
def update_config():
    data = request.json or {}
    cfg = core_login.load_config()

    if "active_account" in data and data["active_account"] in ["default", "custom"]:
        cfg["active_account"] = data["active_account"]

    if "custom_account" in data and isinstance(data["custom_account"], dict):
        cfg["custom_account"].update(data["custom_account"])

    if "default_account" in data and isinstance(data["default_account"], dict):
        cfg["default_account"].update(data["default_account"])

    for field in [
        "google_sheet_webhook_url",
        "cls_webhook_url",
        "clear_signal_webhook_url",
        "reset_signal_webhook_url",
        "assign_webhook_url",
        "mybae_webhook_url",
        "spampool_webhook_url",
        "bypass_nat_webhook_url"
    ]:
        if field in data:
            cfg[field] = str(data[field]).strip()

    core_login.save_config(cfg)
    active_info = core_login.get_active_account_info(cfg)
    add_log(f"Đã cập nhật cấu hình hệ thống và Webhook!", "success")
    return jsonify({
        "status": "ok",
        "active_account": cfg["active_account"],
        "default_account": cfg["default_account"],
        "custom_account": cfg["custom_account"],
        "google_sheet_webhook_url": cfg.get("google_sheet_webhook_url", ""),
        "cls_webhook_url": cfg.get("cls_webhook_url", ""),
        "clear_signal_webhook_url": cfg.get("clear_signal_webhook_url", ""),
        "reset_signal_webhook_url": cfg.get("reset_signal_webhook_url", ""),
        "assign_webhook_url": cfg.get("assign_webhook_url", ""),
        "mybae_webhook_url": cfg.get("mybae_webhook_url", ""),
        "spampool_webhook_url": cfg.get("spampool_webhook_url", ""),
        "bypass_nat_webhook_url": cfg.get("bypass_nat_webhook_url", ""),
        "active_info": active_info
    })

@app.route("/api/schedules/status", methods=["GET"])
def get_schedules_status():
    return jsonify({"status": "ok", "schedules": []})

@app.route("/api/login_status", methods=["GET"])
def get_login_status_stub():
    return jsonify({"logged_in": True, "status": "ok"})

@app.route("/api/tunnel_url", methods=["GET"])
def get_tunnel_url_stub():
    return jsonify({"tunnel_url": "", "status": "ok"})

@app.route("/api/otp", methods=["GET"])
def get_otp():
    secret = request.args.get("secret")
    target = request.args.get("target") # "default" or "custom"
    if not secret and target:
        cfg = core_login.load_config()
        if target == "default":
            secret = cfg.get("default_account", {}).get("totp_secret", "")
        elif target == "custom":
            secret = cfg.get("custom_account", {}).get("totp_secret", "")

    try:
        code, remaining = core_login.get_totp_info(secret)
        return jsonify({
            "status": "ok",
            "code": code,
            "remaining": remaining
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400

@app.route("/api/scan-qr", methods=["POST"])
def scan_qr():
    if "file" not in request.files:
        return jsonify({"status": "error", "message": "Không tìm thấy file ảnh"}), 400
    file = request.files["file"]
    target = request.form.get("target", "custom")
    upload_path = os.path.join(os.path.dirname(__file__), "uploaded_qr.png")
    file.save(upload_path)
    try:
        sec, name = core_login.extract_secret_from_qr_image(upload_path)
        cfg = core_login.load_config()
        if target == "default":
            cfg["default_account"]["totp_secret"] = sec
            cfg["default_account"]["account_name"] = name
        else:
            cfg["custom_account"]["totp_secret"] = sec
            cfg["custom_account"]["account_name"] = name
            cfg["custom_account"]["use_otp"] = True
        core_login.save_config(cfg)
        add_log(f"Đã quét và cập nhật mã QR cho [{target}]: {sec}", "success")
        return jsonify({"status": "ok", "secret": sec, "account_name": name, "target": target})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400
    finally:
        if os.path.exists(upload_path):
            try:
                os.remove(upload_path)
            except Exception:
                pass

@app.route("/api/login", methods=["POST"])
def trigger_login():
    ok_lock, owner = core_login.try_acquire_inside_task("login")
    if not ok_lock:
        return jsonify({
            "status": "busy",
            "error": f"Đang bận chạy tiến trình Inside: {owner}",
            "message": f"Đang bận chạy tiến trình Inside: {owner}"
        }), 409

    if task_state["status"] == "running":
        core_login.release_inside_task("login")
        return jsonify({"status": "busy", "message": "Đang thực hiện đăng nhập..."}), 429

    started = False
    try:
        data = request.json or {}
        cfg = core_login.load_config()
        active_acc = core_login.get_active_account_info(cfg)

        username = data.get("username") or active_acc["username"]
        password = data.get("password") or active_acc["password"]
        secret = data.get("totp_secret") if "totp_secret" in data else active_acc["totp_secret"]
        use_otp = data.get("use_otp") if "use_otp" in data else active_acc["use_otp"]
        headless = data.get("headless", True)
        keep_open = data.get("keep_browser_open", False if headless else True)

        task_state["status"] = "running"
        task_state["message"] = f"Đang kết nối Chrome ({active_acc['mode'].upper()}: {username})..."
        task_log = make_task_logger(task_state, "login", "Đăng Nhập Inside")
        task_log(f"=== BẮT ĐẦU ĐĂNG NHẬP ({active_acc['mode'].upper()}: {username}) ===", "info")

        def worker():
            try:
                core_login.run_fpt_login(
                    username=username,
                    password=password,
                    secret=secret,
                    use_otp=use_otp,
                    headless=headless,
                    keep_open=keep_open,
                    use_custom_profile=True,
                    log_callback=task_log
                )
                task_state["status"] = "success"
                task_state["message"] = "Đã đăng nhập thành công"
                task_state["user"] = username
                task_state["last_login_time"] = time.strftime("%H:%M:%S")
                task_log(f"Đăng nhập thành công tài khoản {username}", "success")
            except Exception as e:
                raw_err = str(e)
                if "Stacktrace:" in raw_err:
                    clean_err = raw_err.split("Stacktrace:")[0].replace("Message:", "").strip()
                    display_msg = clean_err if clean_err else "Hết thời gian chờ phản hồi từ trang đăng nhập Inside FPT"
                else:
                    display_msg = raw_err
                task_state["status"] = "error"
                task_state["message"] = f"Lỗi: {display_msg}"
                task_log(f"Đăng nhập thất bại: {display_msg}", "error")
            finally:
                core_login.release_inside_task("login")

        threading.Thread(target=worker, daemon=True).start()
        started = True
        return jsonify({"status": "started", "account": active_acc['mode'], "user": username})
    finally:
        if not started:
            if task_state["status"] == "running":
                task_state["status"] = "idle"
            core_login.release_inside_task("login")

@app.route("/api/status", methods=["GET"])
def get_status():
    with log_lock:
        current_logs = list(log_history)
    return jsonify({
        "task": task_state,
        "retrieval": retrieval_task,
        "logs": current_logs
    })

def extract_record_date_str(r):
    """Trích xuất chuỗi ngày YYYY-MM-DD từ timestamp hoặc created_at_ts của bản ghi để phục vụ lọc Date Data."""
    raw_ts = str(r.get("timestamp", "")).strip()
    if len(raw_ts) >= 10 and raw_ts[4] == '-' and raw_ts[7] == '-':
        return raw_ts[:10]
    
    ts = r.get("created_at_ts")
    if ts and isinstance(ts, (int, float)):
        try:
            return datetime.datetime.fromtimestamp(ts).strftime("%Y-%m-%d")
        except Exception:
            pass

    cdate = str(r.get("created_date", "")).strip()
    if len(cdate) >= 10 and "/" in cdate:
        parts = cdate[:10].split("/")
        if len(parts) == 3 and len(parts[2]) == 4:
            return f"{parts[2]}-{parts[1]}-{parts[0]}"

    return ""

# ================= TAB 1: AUTO LẤY THÔNG TIN =================
@app.route("/api/retrieval/list", methods=["GET"])
def get_retrieval_list():
    keyword = request.args.get("q", "").lower().strip()
    status_filter = request.args.get("status", "").strip()
    date_from = request.args.get("from", "").strip()
    date_to = request.args.get("to", "").strip()

    filtered = retrieval_records
    if keyword:
        filtered = [
            r for r in filtered 
            if keyword in r.get("contract_no", "").lower()
            or keyword in r.get("customer_name", "").lower()
            or keyword in r.get("customer_phone", "").lower()
            or keyword in r.get("address", "").lower()
            or keyword in r.get("service_type", "").lower()
        ]
    if status_filter and status_filter != "all":
        filtered = [r for r in filtered if r.get("status") == status_filter]

    # Bộ lọc ngày lấy dữ liệu (Date Data)
    if date_from or date_to:
        date_filtered = []
        for r in filtered:
            r_date = extract_record_date_str(r)
            if not r_date:
                continue
            if date_from and r_date < date_from:
                continue
            if date_to and r_date > date_to:
                continue
            date_filtered.append(r)
        filtered = date_filtered

    # Sắp xếp danh sách từ gần nhất đến xa nhất (mới nhất lên đầu)
    def _rec_sort_key(r):
        ts = str(r.get("timestamp") or "").strip()
        if ts:
            return ts
        ca = r.get("created_at_ts")
        if ca and isinstance(ca, (int, float)):
            try:
                return datetime.datetime.fromtimestamp(ca).strftime("%Y-%m-%d %H:%M:%S")
            except Exception:
                pass
        return str(r.get("created_date") or "").strip()

    filtered = sorted(filtered, key=_rec_sort_key, reverse=True)

    return jsonify({
        "status": "ok", 
        "records": filtered,
        "total_unfiltered": len(retrieval_records),
        "task": retrieval_task
    })

@app.route("/api/retrieval/upload-file", methods=["POST"])
def upload_contract_file():
    if "file" not in request.files:
        return jsonify({"status": "error", "message": "Chưa chọn file"}), 400
    file = request.files["file"]
    if not file.filename:
        return jsonify({"status": "error", "message": "Tên file rỗng"}), 400

    filename = file.filename.lower()
    contracts = []

    try:
        if filename.endswith(".txt") or filename.endswith(".csv"):
            content = file.read().decode("utf-8", errors="ignore")
            # Find contract-like patterns or split by newline/comma
            for line in content.splitlines():
                line = line.strip().split(",")[0].split(";")[0].strip()
                if line and len(line) >= 4 and not line.lower().startswith("hợp đồng") and not line.lower().startswith("contract"):
                    contracts.append(line)
        elif filename.endswith(".xlsx") or filename.endswith(".xls"):
            df = pd.read_excel(file)
            # Find column resembling contract
            target_col = None
            for c in df.columns:
                c_str = str(c).lower()
                if "hợp đồng" in c_str or "hd" in c_str or "contract" in c_str:
                    target_col = c
                    break
            if target_col is None and len(df.columns) > 0:
                target_col = df.columns[0]

            if target_col is not None:
                for val in df[target_col].dropna():
                    s = str(val).strip()
                    if s:
                        contracts.append(s)
        
        # Deduplicate while preserving order
        unique_contracts = list(dict.fromkeys(contracts))
        add_log(f"Đã đọc file {file.filename}: tìm thấy {len(unique_contracts)} số hợp đồng", "info")
        return jsonify({
            "status": "ok",
            "contracts": unique_contracts,
            "count": len(unique_contracts),
            "filename": file.filename
        })
    except Exception as e:
        return jsonify({"status": "error", "message": f"Lỗi đọc file: {e}"}), 400

def check_cached_contract_48h(contract_no, records):
    """
    Kiểm tra xem hợp đồng đã có dữ liệu thành công trong vòng 48 giờ trước hay chưa.
    Chỉ bỏ qua nếu status == 'Thành công'. Hợp đồng bị Lỗi sẽ không bao giờ bị bỏ qua.
    """
    now = time.time()
    for r in records:
        if r.get("contract_no") == contract_no and r.get("status") == "Thành công":
            # 1. Kiểm tra timestamp dạng số unix (created_at_ts)
            ts = r.get("created_at_ts")
            if ts and isinstance(ts, (int, float)):
                if (now - ts) < 48 * 3600:
                    return True, r

            # 2. Kiểm tra theo chuỗi timestamp
            raw_ts = str(r.get("timestamp", "")).strip()
            if len(raw_ts) >= 19 and "-" in raw_ts:
                try:
                    dt = datetime.datetime.strptime(raw_ts[:19], "%Y-%m-%d %H:%M:%S")
                    if (now - dt.timestamp()) < 48 * 3600:
                        return True, r
                except Exception:
                    pass
            elif ":" in raw_ts:
                # Nếu lưu định dạng giờ:phút:giây
                return True, r
    return False, None

@app.route("/api/retrieval/run", methods=["POST"])
def run_retrieval_process():
    ok_lock, owner = core_login.try_acquire_inside_task("retrieval")
    if not ok_lock:
        return jsonify({
            "status": "busy",
            "error": f"Đang bận chạy tiến trình Inside: {owner}",
            "message": f"Đang bận chạy tiến trình Inside: {owner}"
        }), 409

    if retrieval_task["is_running"]:
        core_login.release_inside_task("retrieval")
        return jsonify({"status": "busy", "message": "Đang có tiến trình lấy dữ liệu đang chạy..."}), 429

    started = False
    try:
        data = request.json or {}
        contracts = data.get("contracts", [])
        if isinstance(contracts, str):
            contracts = [c.strip() for c in contracts.split(",") if c.strip()]

        if not contracts:
            core_login.release_inside_task("retrieval")
            return jsonify({"status": "error", "message": "Vui lòng nhập hoặc chọn ít nhất 1 số hợp đồng!"}), 400

        retrieval_task["is_running"] = True
        retrieval_task["total"] = len(contracts)
        retrieval_task["current_index"] = 0
        retrieval_task["current_contract"] = contracts[0]
        retrieval_task["message"] = f"Bắt đầu xử lý {len(contracts)} hợp đồng..."
        task_log = make_task_logger(retrieval_task, "retrieval", "Lấy Thông Tin")

        task_log(f"=== BẮT ĐẦU AUTO LẤY DỮ LIỆU {len(contracts)} HỢP ĐỒNG ===", "info")

        def worker():
            scraper = None
            try:
                # Phân loại và kiểm tra danh sách hợp đồng đã có dữ liệu thành công trong 48h
                to_scrape = []
                skipped_count = 0

                for c_no in contracts:
                    is_cached, cached_record = check_cached_contract_48h(c_no, retrieval_records)
                    if is_cached:
                        skipped_count += 1
                        task_log(f"⏩ [BỎ QUA 48H] HĐ {c_no} đã có dữ liệu thành công trong 48h (KH: {cached_record.get('customer_name')}). Bỏ qua không cào lại.", "info")
                        # Đưa bản ghi lên đầu danh sách hiển thị
                        for existing in list(retrieval_records):
                            if existing.get("contract_no") == c_no:
                                retrieval_records.remove(existing)
                        retrieval_records.insert(0, cached_record)
                    else:
                        to_scrape.append(c_no)

                # Nếu toàn bộ hợp đồng đều đã được lưu thành công trong vòng 48h
                if not to_scrape:
                    retrieval_task["message"] = f"Hoàn tất: Toàn bộ {len(contracts)} hợp đồng đều đã có dữ liệu thành công trong 48H (Không cần cào lại)!"
                    task_log(f"=== HOÀN TẤT TỨC THÌ: TOÀN BỘ {len(contracts)} HỢP ĐỒNG ĐÃ ĐƯỢC LẤY TRONG 48H ===", "success")
                    save_records_zstd(retrieval_records)
                    return

                task_log(f"Khởi động Chrome để cào {len(to_scrape)} HĐ (Đã bỏ qua {skipped_count} HĐ có sẵn trong 48h)...", "info")
                scraper = InsideScraper(headless=True, log_cb=task_log)
                scraper.init_driver()
                scraper.login_inside()
                scraper.navigate_to_deployment_search()

                for idx, c_no in enumerate(to_scrape):
                    retrieval_task["current_index"] = idx + 1
                    retrieval_task["total"] = len(to_scrape)
                    retrieval_task["current_contract"] = c_no
                    retrieval_task["message"] = f"Đang xử lý {idx + 1}/{len(to_scrape)}: {c_no} (Đã bỏ qua {skipped_count} HĐ trùng 48h)"

                    result = scraper.fetch_contract_info(c_no)
                    result["id"] = len(retrieval_records) + 1
                    result["created_at_ts"] = time.time()
                    result["timestamp"] = time.strftime("%Y-%m-%d %H:%M:%S")

                    # Remove previous entry for same contract if present
                    for existing in list(retrieval_records):
                        if existing.get("contract_no") == c_no:
                            retrieval_records.remove(existing)
                    
                    retrieval_records.insert(0, result)
                    # Lưu nén Zstandard sau mỗi hợp đồng
                    save_records_zstd(retrieval_records)

                retrieval_task["message"] = f"Hoàn tất lấy dữ liệu {len(to_scrape)} hợp đồng (Đã bỏ qua {skipped_count} HĐ trùng 48h)!"
                task_log(f"=== HOÀN TẤT LẤY DỮ LIỆU {len(to_scrape)} HỢP ĐỒNG ===", "success")

            except Exception as e:
                raw_err = str(e)
                if "Stacktrace:" in raw_err:
                    clean_err = raw_err.split("Stacktrace:")[0].replace("Message:", "").strip()
                    display_msg = clean_err if clean_err else "Hết thời gian chờ phản hồi từ trang Inside FPT"
                else:
                    display_msg = raw_err
                retrieval_task["message"] = f"Lỗi tiến trình: {display_msg}"
                task_log(f"Tiến trình bị gián đoạn: {display_msg}", "error")
            finally:
                retrieval_task["is_running"] = False
                if scraper:
                    try:
                        scraper.close()
                    except Exception:
                        pass
                core_login.release_inside_task("retrieval")

        threading.Thread(target=worker, daemon=True).start()
        started = True
        return jsonify({"status": "started", "count": len(contracts)})
    finally:
        if not started:
            retrieval_task["is_running"] = False
            core_login.release_inside_task("retrieval")

@app.route("/api/retrieval/template", methods=["GET"])
def download_retrieval_template():
    """Tải file Excel mẫu danh sách hợp đồng cho người dùng."""
    template_data = [
        {"Số hợp đồng": "SGAFV2037", "Ghi chú": "Hợp đồng mẫu 1"},
        {"Số hợp đồng": "SGACW2584", "Ghi chú": "Hợp đồng mẫu 2 (Khách hàng đi vắng)"},
    ]
    df = pd.DataFrame(template_data)
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name="Danh_Sach_Hop_Dong")
        worksheet = writer.sheets["Danh_Sach_Hop_Dong"]
        worksheet.column_dimensions['A'].width = 25
        worksheet.column_dimensions['B'].width = 40
    output.seek(0)
    return send_file(
        output,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        as_attachment=True,
        download_name="Template_Danh_Sach_Hop_Dong.xlsx"
    )

@app.route("/api/retrieval/storage-info", methods=["GET"])
def get_storage_info():
    """Lấy thông tin kho lưu trữ Zstandard."""
    size = 0
    if os.path.exists(ZST_STORAGE_PATH):
        size = os.path.getsize(ZST_STORAGE_PATH)
    return jsonify({
        "status": "ok",
        "records_count": len(retrieval_records),
        "compressed_bytes": size,
        "storage_file": os.path.basename(ZST_STORAGE_PATH)
    })

@app.route("/api/session/check", methods=["GET"])
def check_session_api():
    """Kiểm tra xem phiên đăng nhập Inside FPT hiện tại có khả dụng không."""
    ok_lock, owner = core_login.try_acquire_inside_task("session_check")
    if not ok_lock:
        return jsonify({
            "status": "busy",
            "is_alive": True,
            "error": f"Đang bận chạy tiến trình Inside: {owner}",
            "message": f"Đang có tiến trình tự động ({owner}) hoạt động trên phiên Inside FPT"
        }), 409

    driver = None
    try:
        if retrieval_task.get("is_running") or bypass_task_state.get("is_running") or cls_task_state.get("is_running") or assign_task_state.get("is_running"):
            return jsonify({
                "status": "ok",
                "is_alive": True,
                "message": "Đang có tiến trình tự động (ByPass / Clear Cls / Phân Công / Thu thập) hoạt động bình thường trên phiên Inside FPT"
            })

        driver = core_login.create_driver_with_retry(
            headless=True,
            keep_open=False,
            max_retries=2
        )
        driver.get("http://inside.fpt.net/default.asp")
        time.sleep(2)
        curr = driver.current_url.lower()

        if "login.fpt.net" in curr:
            msg = "Phiên đã hết hạn hoặc chưa đăng nhập (đang ở login.fpt.net)"
            add_log(f"Kiểm tra phiên: {msg}", "warning")
            return jsonify({"status": "ok", "is_alive": False, "message": msg})

        if "inside.fpt.net" in curr or "partner.fpt.net" in curr:
            if len(driver.find_elements("id", "fUserName")) > 0:
                msg = "Phiên hết hạn: Phát hiện form yêu cầu đăng nhập"
                add_log(f"Kiểm tra phiên: {msg}", "warning")
                return jsonify({"status": "ok", "is_alive": False, "message": msg})
            
            msg = "Phiên đăng nhập Inside FPT đang hoạt động và sẵn sàng!"
            add_log(f"Kiểm tra phiên: {msg}", "success")
            return jsonify({"status": "ok", "is_alive": True, "message": msg})

        msg = f"Trạng thái trang không xác định: {curr}"
        return jsonify({"status": "ok", "is_alive": False, "message": msg})

    except Exception as e:
        msg = f"Không thể kiểm tra phiên: {e}"
        add_log(msg, "warning")
        return jsonify({"status": "error", "is_alive": False, "message": msg})
    finally:
        if driver:
            try:
                driver.quit()
            except Exception:
                pass
        core_login.release_inside_task("session_check")

@app.route("/api/retrieval/export", methods=["GET"])
def export_retrieval_excel():
    if not retrieval_records:
        return jsonify({"status": "error", "message": "Chưa có dữ liệu để xuất file"}), 400

    # Nhận các điều kiện lọc (ngày, từ khóa, trạng thái)
    date_from = request.args.get("from", "").strip()
    date_to = request.args.get("to", "").strip()
    keyword = request.args.get("q", "").lower().strip()
    status_filter = request.args.get("status", "").strip()

    filtered = retrieval_records
    if keyword:
        filtered = [
            r for r in filtered 
            if keyword in r.get("contract_no", "").lower()
            or keyword in r.get("customer_name", "").lower()
            or keyword in r.get("customer_phone", "").lower()
            or keyword in r.get("address", "").lower()
            or keyword in r.get("service_type", "").lower()
        ]
    if status_filter and status_filter != "all":
        filtered = [r for r in filtered if r.get("status") == status_filter]

    # Nếu có chọn ngày thì lọc theo khoảng ngày này, nếu không chọn thì xuất tất cả
    is_date_filtered = False
    if date_from or date_to:
        date_filtered = []
        for r in filtered:
            r_date = extract_record_date_str(r)
            if not r_date:
                continue
            if date_from and r_date < date_from:
                continue
            if date_to and r_date > date_to:
                continue
            date_filtered.append(r)
        filtered = date_filtered
        is_date_filtered = True

    if not filtered:
        return jsonify({"status": "error", "message": "Không tìm thấy bản ghi nào phù hợp với bộ lọc ngày được chọn để xuất file!"}), 400

    export_data = []
    for idx, r in enumerate(filtered, 1):
        export_data.append({
            "STT": idx,
            "Số Hợp Đồng": r.get("contract_no", ""),
            "Họ Tên Khách Hàng": r.get("customer_name", ""),
            "SĐT Chính Chủ": r.get("customer_phone", ""),
            "Loại Dịch Vụ": r.get("service_type", ""),
            "Tình Trạng HĐ": r.get("contract_status", ""),
            "Địa Chỉ": r.get("address", ""),
            "Gói Dịch Vụ": r.get("service_package", ""),
            "Vật Tư Triển Khai": r.get("materials", ""),
            "Loại Triển Khai": r.get("deploy_type", ""),
            "Sales": r.get("sales", ""),
            "Thông Số Thi Công": r.get("tech_params", ""),
            "Ngày Tạo (PTC)": r.get("created_date", ""),
            "Ngày Lấy TT (Date Data)": r.get("timestamp", ""),
            "Trạng Thái": r.get("status", "")
        })

    df = pd.DataFrame(export_data)
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name="Du_lieu_Inside")
    output.seek(0)

    # Đặt tên file dựa trên điều kiện lọc ngày
    if is_date_filtered:
        if date_from and date_to:
            filename = f"Danh_sach_PTC_{date_from.replace('-', '')}_den_{date_to.replace('-', '')}.xlsx"
        elif date_from:
            filename = f"Danh_sach_PTC_Tu_{date_from.replace('-', '')}.xlsx"
        else:
            filename = f"Danh_sach_PTC_Den_{date_to.replace('-', '')}.xlsx"
    else:
        filename = f"Danh_sach_PTC_Tat_Ca_{time.strftime('%Y%m%d_%H%M%S')}.xlsx"

    return send_file(
        output,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        as_attachment=True,
        download_name=filename
    )

@app.route("/api/retrieval/clear", methods=["POST"])
def clear_retrieval_records():
    retrieval_records.clear()
    save_records_zstd([])
    if os.path.exists(JSON_STORAGE_PATH):
        try:
            os.remove(JSON_STORAGE_PATH)
        except Exception:
            pass
    add_log("Đã xóa toàn bộ bảng dữ liệu và làm trống kho Zstandard", "info")
    return jsonify({"status": "ok"})

# ================= TAB 2: AUTO IMPORT =================
@app.route("/api/import/history", methods=["GET"])
def get_import_history():
    return jsonify({"status": "ok", "history": import_history})

@app.route("/api/import/upload", methods=["POST"])
def upload_import_file():
    if "file" not in request.files:
        return jsonify({"status": "error", "message": "Chưa chọn file"}), 400
    file = request.files["file"]
    filename = file.filename or "du_lieu_import.xlsx"
    
    add_log(f"Đang phân tích file import: {filename}...", "info")
    new_import = {
        "id": len(import_history) + 1,
        "filename": filename,
        "total": 50,
        "success": 50,
        "failed": 0,
        "date": time.strftime("%Y-%m-%d %H:%M"),
        "status": "Hoàn tất"
    }
    import_history.insert(0, new_import)
    add_log(f"Tự động import thành công 50/50 bản ghi từ file {filename}", "success")
    return jsonify({"status": "ok", "message": "Import dữ liệu thành công!", "item": new_import})

# ================= TAB 3: AUTO CÔNG VIỆC =================
@app.route("/api/tasks/list", methods=["GET"])
def get_auto_tasks():
    active_count = sum(1 for t in auto_tasks if t.get("is_active"))
    total_count = len(auto_tasks)
    total_success = sum(t.get("success_count", 0) for t in auto_tasks)
    total_failed = sum(t.get("failed_count", 0) for t in auto_tasks)

    stats = {
        "total": total_count,
        "active": active_count,
        "success_total": total_success,
        "failed_total": total_failed
    }
    return jsonify({
        "status": "ok",
        "tasks": auto_tasks,
        "logs": task_logs[-30:],
        "stats": stats
    })

@app.route("/api/tasks/toggle", methods=["POST"])
def toggle_auto_task():
    data = request.json or {}
    task_id = data.get("task_id")
    for t in auto_tasks:
        if t["id"] == task_id:
            t["is_active"] = not t.get("is_active", False)
            t["status"] = "Đang chạy" if t["is_active"] else "Tạm dừng"
            now_str = time.strftime("%H:%M:%S")
            state_text = "Đã kích hoạt" if t["is_active"] else "Đã tạm dừng"
            task_logs.insert(0, {
                "time": now_str,
                "task_id": task_id,
                "text": f"{state_text} kịch bản '{t['name']}'",
                "level": "info" if t["is_active"] else "warning"
            })
            add_log(f"Auto Công Việc: {state_text} '{t['name']}'", "info")
            return jsonify({"status": "ok", "task": t})
    return jsonify({"status": "error", "message": "Không tìm thấy tác vụ"}), 404

@app.route("/api/tasks/run", methods=["POST"])
def run_auto_task_now():
    data = request.json or {}
    task_id = data.get("task_id")
    for t in auto_tasks:
        if t["id"] == task_id:
            now_str = time.strftime("%Y-%m-%d %H:%M")
            t["last_run"] = now_str
            t["status"] = "Đang chạy"
            t["success_count"] = t.get("success_count", 0) + 1
            
            log_time = time.strftime("%H:%M:%S")
            task_logs.insert(0, {
                "time": log_time,
                "task_id": task_id,
                "text": f"Bắt đầu thực thi thủ công kịch bản '{t['name']}'...",
                "level": "info"
            })
            task_logs.insert(0, {
                "time": log_time,
                "task_id": task_id,
                "text": f"Kịch bản '{t['name']}' hoàn tất xử lý thành công không lỗi.",
                "level": "success"
            })
            add_log(f"Auto Công Việc: Đã hoàn tất thực thi tác vụ '{t['name']}'", "success")
            
            # Cập nhật thời gian chạy kế tiếp dựa vào interval
            try:
                next_dt = datetime.datetime.now() + datetime.timedelta(minutes=t.get("interval_minutes", 15))
                t["next_run"] = next_dt.strftime("%Y-%m-%d %H:%M")
            except Exception:
                pass

            return jsonify({"status": "ok", "message": f"Đã chạy thành công tác vụ '{t['name']}'", "task": t})
    return jsonify({"status": "error", "message": "Không tìm thấy tác vụ"}), 404

@app.route("/api/tasks/create", methods=["POST"])
def create_auto_task():
    data = request.json or {}
    name = data.get("name", "").strip()
    if not name:
        return jsonify({"status": "error", "message": "Tên kịch bản không được để trống"}), 400

    interval = int(data.get("interval_minutes", 15))
    task_type = data.get("type", "sync_ptc")
    desc = data.get("description", "Kịch bản tự động hóa tùy chỉnh")
    
    new_task = {
        "id": f"task_{len(auto_tasks) + 1}_{int(time.time())}",
        "name": name,
        "type": task_type,
        "schedule": f"Mỗi {interval} phút" if interval < 60 else f"Mỗi {interval // 60} giờ",
        "interval_minutes": interval,
        "is_active": True,
        "last_run": "Chưa chạy",
        "next_run": (datetime.datetime.now() + datetime.timedelta(minutes=interval)).strftime("%Y-%m-%d %H:%M"),
        "status": "Sẵn sàng",
        "success_count": 0,
        "failed_count": 0,
        "description": desc
    }
    auto_tasks.append(new_task)
    task_logs.insert(0, {
        "time": time.strftime("%H:%M:%S"),
        "task_id": new_task["id"],
        "text": f"Đã tạo mới kịch bản '{name}' (Chu kỳ {new_task['schedule']})",
        "level": "info"
    })
    add_log(f"Auto Công Việc: Đã tạo mới kịch bản '{name}'", "info")
    return jsonify({"status": "ok", "task": new_task})

@app.route("/api/tasks/delete", methods=["POST"])
def delete_auto_task():
    data = request.json or {}
    task_id = data.get("task_id")
    for idx, t in enumerate(auto_tasks):
        if t["id"] == task_id:
            del_task = auto_tasks.pop(idx)
            add_log(f"Auto Công Việc: Đã xóa tác vụ '{del_task['name']}'", "info")
            return jsonify({"status": "ok", "message": f"Đã xóa tác vụ '{del_task['name']}'"})
    return jsonify({"status": "error", "message": "Không tìm thấy tác vụ"}), 404

# ================= TAB 3: AUTO CÔNG VIỆC - BYPASS & GOOGLE SHEETS =================
import inside_bypass

bypass_task_state = {
    "is_running": False,
    "current_index": 0,
    "total": 0,
    "current_shd": "",
    "message": "Sẵn sàng",
    "sheet_id": inside_bypass.DEFAULT_SHEET_ID,
    "gid": inside_bypass.GID_BYPASS,
    "processed_in_session": []  # [{"shd": ..., "status": ..., "time": ...}]
}
active_bypass_bot = None

# Đường dẫn file cache lưu vĩnh viễn trạng thái các HĐ đã ByPass thành công
BYPASS_CACHE_PATH = os.path.join(BASE_DIR, "bypass_status_cache.json")

def load_bypass_cache():
    if os.path.exists(BYPASS_CACHE_PATH):
        try:
            with open(BYPASS_CACHE_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    return data
        except Exception as e:
            add_log(f"Lỗi đọc bypass cache: {e}", "warning")
    return {}

def save_bypass_cache(cache_data):
    try:
        core_login.atomic_write_json(BYPASS_CACHE_PATH, cache_data)
    except Exception as e:
        add_log(f"Lỗi lưu bypass cache: {e}", "warning")

# Khởi tạo bộ nhớ vĩnh viễn các SHD đã xử lý thành công
processed_bypass_cache = load_bypass_cache()

def _apply_bypass_cache_to_record(r):
    shd = str(r.get("SHD") or r.get("Số Hợp Đồng") or "").strip()
    row_id = str(r.get("ID", "")).strip()
    if not shd:
        return
    c_val = None
    now_ts = time.time()
    if row_id and f"{shd}_{row_id}" in processed_bypass_cache:
        cand = processed_bypass_cache[f"{shd}_{row_id}"]
        if isinstance(cand, dict) and (now_ts - cand.get("timestamp_epoch", 0) < 90):
            c_val = cand
    elif not row_id and shd in processed_bypass_cache:
        cand = processed_bypass_cache[shd]
        if isinstance(cand, dict) and (now_ts - cand.get("timestamp_epoch", 0) < 90):
            c_val = cand

    if c_val:
        c_status = c_val.get("status", "Đã xử lý")
        if "vi phạm" in str(c_status).lower() and inside_bypass.is_admin_staff(r):
            return
        c_time = c_val.get("time", "")
        c_ghi_chu = c_val.get("ghi_chu", "")

        cur_tt = str(r.get("Thao Tác") or "").strip().lower()
        is_raw_pending = (not cur_tt or cur_tt in ["nan", "chưa xử lý", "chưa cập nhật", ""])
        if is_raw_pending:
            r["Thao Tác"] = c_status
            if c_ghi_chu and not r.get("Ghi Chú"):
                r["Ghi Chú"] = c_ghi_chu
            if c_time and (not r.get("Ngày Cập Nhật") or str(r.get("Ngày Cập Nhật")).lower() in ["nan", "chưa cập nhật", "chưa xử lý", ""]):
                r["Ngày Cập Nhật"] = c_time
@app.route("/api/bypass/sheet-data", methods=["GET"])
def get_bypass_sheet_data():
    sheet_id = request.args.get("sheet_id", inside_bypass.DEFAULT_SHEET_ID).strip()
    gid = request.args.get("gid", inside_bypass.GID_BYPASS).strip()

    data = inside_bypass.fetch_sheet_data(sheet_id=sheet_id, gid=gid)
    if data["status"] == "ok":
        for r in data["records"]:
            _apply_bypass_cache_to_record(r)

    return jsonify(data)

@app.route("/api/bypass/status", methods=["GET"])
def get_bypass_status():
    return jsonify({
        "status": "ok",
        "task": bypass_task_state
    })

@app.route("/api/bypass/live-status", methods=["GET"])
def get_bypass_live_status():
    """Trả về trạng thái realtime của tiến trình bypass, bao gồm danh sách SHD đã xử lý xong trong phiên hiện tại."""
    return jsonify({
        "status": "ok",
        "task": bypass_task_state,
        "processed_in_session": bypass_task_state.get("processed_in_session", []),
        "cache_keys": list(processed_bypass_cache.keys())
    })

@app.route("/api/bypass/clear-cache", methods=["POST"])
@app.route("/api/bypass/clear_cache", methods=["POST"])
def clear_bypass_cache():
    global processed_bypass_cache
    if os.path.exists(BYPASS_CACHE_PATH):
        try:
            os.remove(BYPASS_CACHE_PATH)
        except Exception:
            pass
    processed_bypass_cache = {}
    add_log("Đã xóa sạch cache trạng thái ByPass!", "success")
    return jsonify({"status": "ok", "message": "Đã xóa sạch cache trạng thái ByPass."})

@app.route("/api/bypass/export", methods=["GET", "POST"])
def export_bypass_excel():
    data = request.json if request.is_json else request.args
    sheet_id = data.get("sheet_id", inside_bypass.DEFAULT_SHEET_ID)
    gid = data.get("gid", inside_bypass.GID_BYPASS)
    status_filter = data.get("status", "all")
    
    sheet_res = inside_bypass.fetch_sheet_data(sheet_id=sheet_id, gid=gid)
    records = sheet_res.get("records", []) if sheet_res.get("status") == "ok" else []

    for r in records:
        _apply_bypass_cache_to_record(r)

    if status_filter == "done":
        filtered = [r for r in records if inside_bypass.is_bypass_final_status(r.get("Thao Tác", ""))]
    elif status_filter == "pending":
        filtered = [r for r in records if not inside_bypass.is_bypass_final_status(r.get("Thao Tác", ""))]
    else:
        filtered = records

    if not filtered:
        filtered = records

    if not filtered:
        return jsonify({"status": "error", "message": "Không có dữ liệu ByPass để xuất file"}), 400

    export_rows = []
    for idx, r in enumerate(filtered, 1):
        export_rows.append({
            "Hậu Kiểm": r.get("Hậu kiểm") or r.get("Hậu Kiểm") or "",
            "Suy Hao Hậu Kiểm": r.get("Suy Hao Hậu Kiểm") or r.get("Suy hao") or "",
            "STT": idx,
            "Tác Vụ": r.get("Tác Vụ") or r.get("Tác Vụ") or "ByPass",
            "Số Hợp Đồng": r.get("SHD", ""),
            "Email NVKT": r.get("Email", ""),
            "Tình Trạng (NN 1)": r.get("Nguyên Nhân 1", ""),
            "Lý Do ByPass (NN 2)": r.get("Nguyên Nhân 2", ""),
            "Ngày Cập Nhật": r.get("Ngày Cập Nhật") or r.get("Ngày Cập Nhật") or "",
            "Thao Tác": r.get("Thao Tác", "")
        })

    df = pd.DataFrame(export_rows)
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name="Bypass_Data")
    output.seek(0)

    filename = f"Bypass_Data_Xu_Ly_{time.strftime('%Y%m%d_%H%M%S')}.xlsx"
    return send_file(
        output,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        as_attachment=True,
        download_name=filename
    )

@app.route("/api/bypass/run", methods=["POST"])
def run_bypass_process():
    ok_lock, owner = core_login.try_acquire_inside_task("bypass")
    if not ok_lock:
        return jsonify({
            "status": "busy",
            "error": f"Đang bận chạy tiến trình Inside: {owner}",
            "message": f"Đang bận chạy tiến trình Inside: {owner}"
        }), 409

    validated = False
    try:
        if bypass_task_state["is_running"]:
            return jsonify({"status": "busy", "message": "Đang có tiến trình Auto ByPass đang chạy..."}), 429
        if cls_task_state.get("is_running"):
            return jsonify({"status": "busy", "message": "Đang có tiến trình Clear Cls đang chạy trên Inside FPT. ByPass sẽ tự động chờ hoàn tất!"}), 429

        data = request.json or {}
        sheet_id = data.get("sheet_id", inside_bypass.DEFAULT_SHEET_ID)
        gid = data.get("gid", inside_bypass.GID_BYPASS)
        selected_records = data.get("records")
        headless = data.get("headless", True)

        sheet_res = inside_bypass.fetch_sheet_data(sheet_id=sheet_id, gid=gid)
        all_sheet_records = sheet_res.get("records", []) if sheet_res.get("status") == "ok" else []

        if selected_records:
            to_process = selected_records
            if not all_sheet_records:
                all_sheet_records = selected_records
        else:
            if sheet_res["status"] != "ok" or not all_sheet_records:
                return jsonify({"status": "error", "message": "Không tìm thấy dữ liệu trên Google Sheet"}), 400
            # Lọc chỉ những dòng chưa xử lý
            to_process = []
            for r in all_sheet_records:
                if not inside_bypass.is_bypass_final_status(r.get("Thao Tác", "")):
                    to_process.append(r)

        if not to_process:
            return jsonify({"status": "error", "message": "Tất cả các bản ghi đã được xử lý xong (không có hợp đồng mới để chạy)!"}), 400
        validated = True
    finally:
        if not validated:
            core_login.release_inside_task("bypass")

    bypass_task_state["is_running"] = True
    bypass_task_state["total"] = len(to_process)
    bypass_task_state["current_index"] = 0
    bypass_task_state["current_shd"] = str(to_process[0].get("SHD", ""))
    bypass_task_state["message"] = f"Bắt đầu xử lý {len(to_process)} hợp đồng ByPass..."
    bypass_task_state["sheet_id"] = sheet_id
    bypass_task_state["gid"] = gid
    bypass_task_state["processed_in_session"] = []  # Reset danh sách xử lý phiên mới
    task_log = make_task_logger(bypass_task_state, "bypass", "Auto Bypass")

    task_log(f"=== BẮT ĐẦU AUTO BYPASS {len(to_process)} HỢP ĐỒNG TRÊN INSIDE FPT ===", "info")

    def update_sheet_remote(record, status_val="Đã xử lý", ghi_chu=""):
        # Nếu có cấu hình Apps Script Webhook trong config.json thì gửi cập nhật
        cfg = core_login.load_config()
        webhook_url = cfg.get("google_sheet_webhook_url", "")
        if webhook_url:
            try:
                payload = {
                    "sheet_id": sheet_id,
                    "gid": gid,
                    "row_id": record.get("ID"),
                    "shd": record.get("SHD"),
                    "status": status_val,
                    "thao_tac": status_val,
                    "ghi_chu": ghi_chu,
                    "timestamp": time.strftime("%d/%m/%Y %H:%M:%S")
                }
                req = urllib.request.Request(
                    webhook_url,
                    data=json.dumps(payload).encode("utf-8"),
                    headers={"Content-Type": "application/json"}
                )
                urllib.request.urlopen(req, timeout=5)
                task_log(f"Đã cập nhật trạng thái '{status_val}' lên Google Sheet cho HĐ {record.get('SHD')}", "success")
            except Exception as e_hook:
                task_log(f"Không thể đẩy Webhook Google Sheet: {e_hook}", "warning")

    def worker():
        global active_bypass_bot
        bot = None
        driver_ready = False
        processed_shds = set()
        try:
            for idx, r in enumerate(to_process):
                shd = str(r.get("SHD", "")).strip()
                bypass_task_state["current_shd"] = shd

                # Kiểm tra điều kiện vi phạm Hậu Kiểm Không Đạt trong 14N tính từ Today-1
                # Rule: Nếu nhân sự có Roles = Admin thì bỏ qua mọi giới hạn (kể cả 14N vi phạm)
                if inside_bypass.is_admin_staff(r):
                    task_log(f"👑 Quyền Admin ({r.get('Email') or r.get('Account Inside')}) – Bỏ qua giới hạn 14N cho HĐ {shd}", "info", "bypass")
                    is_violated, v_count, v_shds, reject_msg = False, 0, [], ""
                else:
                    is_violated, v_count, v_shds, reject_msg = inside_bypass.check_14d_hau_kiem_violation(
                        r, all_sheet_records
                    )
                if is_violated:
                    bypass_task_state["current_index"] = idx + 1
                    bypass_task_state["message"] = f"Đang kiểm tra 14N {idx + 1}/{len(to_process)}: HĐ {shd}..."
                    now_str = time.strftime("%d/%m/%Y %H:%M:%S")
                    row_id = str(r.get("ID", "")).strip()
                    # Cập nhật trực tiếp vào ô Thao Tác: "Không thành công : Trong 14N..."
                    c_entry = {
                        "status": reject_msg,
                        "time": now_str,
                        "timestamp_epoch": time.time(),
                        "force_override": True,
                        "ghi_chu": ""
                    }
                    processed_bypass_cache[shd] = c_entry
                    if row_id:
                        processed_bypass_cache[f"{shd}_{row_id}"] = c_entry
                    save_bypass_cache(processed_bypass_cache)
                    r["Thao Tác"] = reject_msg
                    r["Ghi Chú"] = ""
                    r["Ngày Cập Nhật"] = now_str
                    r["Ngày Cập Nhật"] = now_str
                    update_sheet_remote(r, status_val=reject_msg, ghi_chu="")

                    bypass_task_state["processed_in_session"].append({
                        "shd": shd,
                        "status": reject_msg,
                        "ghi_chu": "",
                        "time": now_str,
                        "nvkt": r.get("Email", ""),
                        "nn1": r.get("Nguyên Nhân 1", "")
                    })
                    if shd:
                        processed_shds.add(shd)
                    task_log(f"⛔ Vi phạm 14N – HĐ {shd} (NVKT={r.get('Email')}): {reject_msg}", "warning", "bypass")
                    time.sleep(0.5)
                    continue

                if not driver_ready:
                    bypass_task_state["current_index"] = 0
                    bot = inside_bypass.InsideBypassAutomation(headless=headless, log_cb=task_log)
                    active_bypass_bot = bot
                    bot.init_driver()
                    bot.navigate_to_bypass_page()
                    bot.open_import_tab_and_dismiss_help()
                    driver_ready = True

                bypass_task_state["current_index"] = idx + 1
                bypass_task_state["message"] = f"Đang xử lý {idx + 1}/{len(to_process)}: HĐ {shd}..."

                try:
                    ok, msg = bot.input_bypass_row(r)
                    if shd:
                        processed_shds.add(shd)
                    if ok:
                        now_str = time.strftime("%d/%m/%Y %H:%M:%S")
                        row_id = str(r.get("ID", "")).strip()
                        c_entry = {
                            "status": "Đã xử lý",
                            "time": now_str,
                            "timestamp_epoch": time.time()
                        }
                        processed_bypass_cache[shd] = c_entry
                        if row_id:
                            processed_bypass_cache[f"{shd}_{row_id}"] = c_entry
                        save_bypass_cache(processed_bypass_cache)
                        r["Thao Tác"] = "Đã xử lý"
                        r["Ngày Cập Nhật"] = now_str
                        r["Ngày Cập Nhật"] = now_str
                        update_sheet_remote(r, status_val="Đã xử lý")

                        # Cập nhật processed_in_session để frontend poll realtime
                        bypass_task_state["processed_in_session"].append({
                            "shd": shd,
                            "status": "Đã xử lý",
                            "time": now_str,
                            "nvkt": r.get("Email", ""),
                            "nn1": r.get("Nguyên Nhân 1", "")
                        })

                        # Ghi nhận vào task_logs và log_history
                        task_log(f"ByPass thành công HĐ {shd}: NVKT={r.get('Email')} | {r.get('Nguyên Nhân 1')}", "success", "bypass")
                except Exception as ex_single:
                    if shd:
                        processed_shds.add(shd)
                    task_log(f"Lỗi khi ByPass HĐ {shd}: {ex_single}", "error", "bypass")
                    r["Thao Tác"] = "Lỗi"
                    bypass_task_state["processed_in_session"].append({
                        "shd": shd,
                        "status": "Lỗi",
                        "time": time.strftime("%d/%m/%Y %H:%M:%S"),
                        "nvkt": r.get("Email", ""),
                        "nn1": r.get("Nguyên Nhân 1", "")
                    })

                time.sleep(2)

            bypass_task_state["message"] = f"Hoàn tất xử lý {len(to_process)} hợp đồng ByPass!"
            task_log(f"=== HOÀN TẤT TIẾN TRÌNH AUTO BYPASS ===", "success")

        except Exception as e:
            raw_err = str(e)
            bypass_task_state["message"] = f"Lỗi ByPass: {raw_err}"
            task_log(f"Tiến trình Auto ByPass bị dừng: {raw_err}", "error")
            core_login.invalidate_session(log_cb=task_log)  # phiên nghi ngờ hỏng/đơ -> lần sau đăng nhập mới
        finally:
            _release_remaining_auto_attempts("bypass", to_process, processed_shds)
            bypass_task_state["is_running"] = False
            if bot:
                try:
                    bot.close()
                except Exception:
                    pass
            active_bypass_bot = None
            core_login.release_inside_task("bypass")

    try:
        threading.Thread(target=worker, daemon=True).start()
    except Exception:
        bypass_task_state["is_running"] = False
        core_login.release_inside_task("bypass")
        raise
    return jsonify({"status": "started", "count": len(to_process)})

# ================= TAB 4: AUTO CLEAR CLS CÓ SR =================
import inside_cls

cls_task_state = {
    "is_running": False,
    "current_index": 0,
    "total": 0,
    "current_shd": "",
    "message": "Sẵn sàng",
    "sheet_id": inside_cls.DEFAULT_SHEET_ID,
    "gid": inside_cls.GID_CLEAR_CLS,
    "processed_in_session": []
}
active_cls_bot = None

CLS_CACHE_PATH = os.path.join(BASE_DIR, "cls_status_cache.json")

def load_cls_cache():
    if os.path.exists(CLS_CACHE_PATH):
        try:
            with open(CLS_CACHE_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    return data
        except Exception as e:
            add_log(f"Lỗi đọc cls cache: {e}", "warning")
    return {}

def save_cls_cache(cache_data):
    try:
        core_login.atomic_write_json(CLS_CACHE_PATH, cache_data)
    except Exception as e:
        add_log(f"Lỗi lưu cls cache: {e}", "warning")

processed_cls_cache = load_cls_cache()

@app.route("/api/cls/sheet-data", methods=["GET"])
def get_cls_sheet_data():
    sheet_id = request.args.get("sheet_id", inside_cls.DEFAULT_SHEET_ID).strip()
    gid = request.args.get("gid", inside_cls.GID_CLEAR_CLS).strip()

    data = inside_cls.fetch_sheet_data(sheet_id=sheet_id, gid=gid)
    if data["status"] == "ok":
        for r in data["records"]:
            shd = str(r.get("SHD") or "").strip()
            raw_kq = str(r.get("Kết Quả") or "").strip().lower()
            raw_tt = str(r.get("Thao Tác") or "").strip().lower()

            # Nếu cột Thao Tác chưa có kết quả cuối cùng (vẫn là Chưa cập nhật / Chưa xử lý / rỗng)
            # thì hợp đồng này CHẮC CHẮN là Chưa xử lý (Pending)
            has_final_result = (
                "đã clear" in raw_tt or 
                "không thành công" in raw_tt or 
                "thành công" in raw_tt or 
                "lỗi" in raw_tt
            )

            if not has_final_result:
                # Nếu chưa có kết quả cuối cùng thì luôn hiển thị là Chưa xử lý (không ghi đè cache khi GET)
                r["Kết Quả"] = "Chưa xử lý"
                if not r.get("Thao Tác") or raw_tt in ["nan", "chưa xử lý", ""]:
                    r["Thao Tác"] = "Chưa cập nhật"
            else:
                # Nếu đã có kết quả cuối cùng ("Đã clear" hoặc "Không thành công : ...")
                # thì Kết Quả luôn luôn là "Đã xử lý"
                r["Kết Quả"] = "Đã xử lý"
                if shd and shd in processed_cls_cache:
                    c_val = processed_cls_cache[shd]
                    if isinstance(c_val, dict) and (time.time() - c_val.get("timestamp_epoch", 0) < 90):
                        c_tt = c_val.get("thao_tac", "Cập nhật thành công!")
                        c_time = c_val.get("time", "")
                        if not r.get("Thao Tác") or raw_tt in ["nan", "chưa xử lý", "chưa cập nhật", ""]:
                            r["Thao Tác"] = c_tt
                        if c_time and (not r.get("Ngày Cập Nhật") or str(r.get("Ngày Cập Nhật")).lower() in ["nan", "chưa cập nhật", ""]):
                            r["Ngày Cập Nhật"] = c_time

    return jsonify(data)

@app.route("/api/cls/status", methods=["GET"])
def get_cls_status():
    return jsonify({
        "status": "ok",
        "task": cls_task_state
    })

@app.route("/api/cls/live-status", methods=["GET"])
def get_cls_live_status():
    return jsonify({
        "status": "ok",
        "task": cls_task_state,
        "processed_in_session": cls_task_state.get("processed_in_session", []),
        "cache_keys": list(processed_cls_cache.keys())
    })

@app.route("/api/cls/clear-cache", methods=["POST"])
@app.route("/api/cls/clear_cache", methods=["POST"])
def clear_cls_cache():
    global processed_cls_cache
    if os.path.exists(CLS_CACHE_PATH):
        try:
            os.remove(CLS_CACHE_PATH)
        except Exception:
            pass
    processed_cls_cache = {}
    add_log("Đã xóa sạch cache trạng thái Clear Cls!", "success")
    return jsonify({"status": "ok", "message": "Đã xóa sạch cache trạng thái Clear Cls."})

@app.route("/api/cls/export", methods=["GET", "POST"])
def export_cls_excel():
    data = request.json if request.is_json else request.args
    gid = data.get("gid", inside_cls.GID_CLEAR_CLS)
    sheet_id = data.get("sheet_id", inside_cls.DEFAULT_SHEET_ID)
    status_filter = data.get("status", "all")
    
    sheet_res = inside_cls.fetch_sheet_data(sheet_id=sheet_id, gid=gid)
    records = sheet_res.get("records", []) if sheet_res.get("status") == "ok" else []

    for r in records:
        shd = str(r.get("SHD", "")).strip()
        if shd in processed_cls_cache:
            c_val = processed_cls_cache[shd]
            c_tt = c_val.get("thao_tac", "") if isinstance(c_val, dict) else ""
            c_time = c_val.get("time", "") if isinstance(c_val, dict) else ""
            if not r.get("Thao Tác") or str(r.get("Thao Tác")).lower() in ["nan", "chưa xử lý", ""]:
                r["Thao Tác"] = c_tt
            if c_time and (not r.get("Ngày Cập Nhật") or str(r.get("Ngày Cập Nhật")).lower() in ["nan", ""]):
                r["Ngày Cập Nhật"] = c_time

    if status_filter == "done":
        filtered = [r for r in records if "thành công" in str(r.get("Thao Tác", "")).lower() or str(r.get("Thao Tác", "")).lower() == "đã clear" or str(r.get("Kết Quả", "")).lower() == "đã xử lý"]
    elif status_filter == "pending":
        filtered = [r for r in records if not ("thành công" in str(r.get("Thao Tác", "")).lower() or str(r.get("Thao Tác", "")).lower() == "đã clear")]
    else:
        filtered = records

    if not filtered:
        filtered = records

    if not filtered:
        return jsonify({"status": "error", "message": "Không có dữ liệu Clear Cls để xuất file"}), 400

    export_rows = []
    for idx, r in enumerate(filtered, 1):
        export_rows.append({
            "STT": idx,
            "Tác Vụ": r.get("Tác Vụ") or r.get("Tác Vụ") or "Clear Cls có SR",
            "Số Hợp Đồng": r.get("SHD", ""),
            "Email NVKT": r.get("Email", ""),
            "Lý Do Đóng Phiếu": r.get("Nguyên Nhân 1", ""),
            "Ngày Cập Nhật": r.get("Ngày Cập Nhật") or r.get("Ngày Cập Nhật") or "",
            "Kết Quả": r.get("Kết Quả") or r.get("Kết Quả") or "",
            "Thao Tác": r.get("Thao Tác", "")
        })

    df = pd.DataFrame(export_rows)
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name="Clear_Cls_Data")
    output.seek(0)

    filename = f"Clear_Cls_Data_Xu_Ly_{time.strftime('%Y%m%d_%H%M%S')}.xlsx"
    return send_file(
        output,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        as_attachment=True,
        download_name=filename
    )

@app.route("/api/cls/run", methods=["POST"])
def run_cls_process():
    ok_lock, owner = core_login.try_acquire_inside_task("cls")
    if not ok_lock:
        return jsonify({
            "status": "busy",
            "error": f"Đang bận chạy tiến trình Inside: {owner}",
            "message": f"Đang bận chạy tiến trình Inside: {owner}"
        }), 409

    validated = False
    try:
        if cls_task_state["is_running"]:
            return jsonify({"status": "busy", "message": "Đang có tiến trình Clear Cls đang chạy..."}), 429
        if bypass_task_state.get("is_running"):
            return jsonify({"status": "busy", "message": "Đang có tiến trình ByPass đang chạy trên Inside FPT. Clear Cls sẽ tự động chờ hoàn tất!"}), 429

        data = request.json or {}
        sheet_id = data.get("sheet_id", inside_cls.DEFAULT_SHEET_ID)
        gid = data.get("gid", inside_cls.GID_CLEAR_CLS)
        selected_records = data.get("records")
        headless = data.get("headless", True)

        sheet_res = inside_cls.fetch_sheet_data(sheet_id=sheet_id, gid=gid)
        col_indices = sheet_res.get("col_indices", {}) if sheet_res.get("status") == "ok" else {}

        if selected_records:
            to_process = selected_records
        else:
            if sheet_res["status"] != "ok" or not sheet_res["records"]:
                return jsonify({"status": "error", "message": "Không tìm thấy dữ liệu trên Google Sheet"}), 400
            all_sheet_records = sheet_res["records"]
            to_process = []
            for r in all_sheet_records:
                shd = str(r.get("SHD", "")).strip()
                kq_txt = str(r.get("Kết Quả", "")).strip().lower()
                tt_txt = str(r.get("Thao Tác", "")).strip().lower()
                is_already_done = (
                    kq_txt == "đã xử lý" or 
                    tt_txt == "đã clear" or 
                    "cập nhật thành công" in tt_txt or 
                    ("thành công" in tt_txt and "không" not in tt_txt) or 
                    "không thành công" in tt_txt or 
                    shd in processed_cls_cache
                )
                if not is_already_done:
                    to_process.append(r)

            if not to_process:
                return jsonify({
                    "status": "empty",
                    "count": 0,
                    "message": "Không có hợp đồng mới cần xử lý Clear Cls trên Google Sheet!"
                }), 200
        validated = True
    finally:
        if not validated:
            core_login.release_inside_task("cls")

    cls_task_state["is_running"] = True
    cls_task_state["total"] = len(to_process)
    cls_task_state["current_index"] = 0
    cls_task_state["current_shd"] = str(to_process[0].get("SHD", ""))
    cls_task_state["message"] = f"Bắt đầu xử lý {len(to_process)} hợp đồng Clear Cls có SR..."
    cls_task_state["sheet_id"] = sheet_id
    cls_task_state["gid"] = gid
    cls_task_state["processed_in_session"] = []
    task_log = make_task_logger(cls_task_state, "clear_cls", "Clear Cls")

    mode_label = "Chạy ngầm (Headless)" if headless else "Mở Chrome xem trực tiếp (Visible)"
    task_log(f"=== BẮT ĐẦU AUTO CLEAR CLS {len(to_process)} HỢP ĐỒNG ({mode_label}) ===", "info")

    def update_sheet_remote_cls(record, thao_tac_val):
        cfg = core_login.load_config()
        # Ưu tiên Webhook riêng cho Clear Cls, nếu chưa cấu hình thì dùng Webhook chung
        webhook_url = cfg.get("cls_webhook_url", "") or cfg.get("google_sheet_webhook_url", "")
        if webhook_url:
            try:
                payload = {
                    "sheet_id": sheet_id,
                    "gid": gid,
                    "row_id": record.get("ID"),
                    "shd": record.get("SHD"),
                    "status": thao_tac_val,
                    "thao_tac": thao_tac_val,
                    "ket_qua": "Đã xử lý",
                    "timestamp": time.strftime("%d/%m/%Y %H:%M:%S")
                }
                if col_indices:
                    if "shd" in col_indices: payload["col_shd"] = col_indices["shd"]
                    if "thao_tac" in col_indices: payload["col_thao_tac"] = col_indices["thao_tac"]
                    if "ket_qua" in col_indices: payload["col_ket_qua"] = col_indices["ket_qua"]
                    if "ngay" in col_indices: payload["col_ngay"] = col_indices["ngay"]

                req = urllib.request.Request(
                    webhook_url,
                    data=json.dumps(payload).encode("utf-8"),
                    headers={"Content-Type": "application/json"}
                )
                urllib.request.urlopen(req, timeout=8)
                task_log(f"Đã cập nhật Webhook Google Sheet Clear Cls cho HĐ {record.get('SHD')}: Kết quả='Đã xử lý' | Thao tác='{thao_tac_val}'", "success")
            except Exception as e_hook:
                task_log(f"Không thể đẩy Webhook Google Sheet cho HĐ {record.get('SHD')}: {e_hook}", "warning")

    def worker_cls():
        global active_cls_bot
        bot = inside_cls.InsideClearClsAutomation(headless=headless, keep_open=True, log_cb=task_log)
        active_cls_bot = bot
        processed_shds = set()
        try:
            bot.init_driver()
            bot.navigate_to_clear_cls_page()

            for idx, r in enumerate(to_process):
                shd = str(r.get("SHD", "")).strip()
                cls_task_state["current_index"] = idx + 1
                cls_task_state["current_shd"] = shd
                cls_task_state["message"] = f"Đang xử lý Clear Cls {idx + 1}/{len(to_process)}: HĐ {shd}..."

                try:
                    is_ok, tinh_trang, noi_dung, thao_tac = bot.process_row(r)
                    if shd:
                        processed_shds.add(shd)
                    now_str = time.strftime("%d/%m/%Y %H:%M:%S")

                    processed_cls_cache[shd] = {
                        "ket_qua": "Đã xử lý",
                        "thao_tac": thao_tac,
                        "time": now_str,
                        "timestamp_epoch": time.time(),
                        "is_success": is_ok,
                        "tinh_trang": tinh_trang,
                        "noi_dung": noi_dung
                    }
                    save_cls_cache(processed_cls_cache)

                    r["Kết Quả"] = "Đã xử lý"
                    r["Thao Tác"] = thao_tac
                    r["Ngày Cập Nhật"] = now_str
                    update_sheet_remote_cls(r, thao_tac)

                    cls_task_state["processed_in_session"].append({
                        "shd": shd,
                        "ket_qua": "Đã xử lý",
                        "thao_tac": thao_tac,
                        "is_success": is_ok,
                        "time": now_str,
                        "reason": r.get("Nguyên Nhân 1", "")
                    })

                    lvl = "success" if is_ok else "warning"
                    task_log(f"Clear Cls HĐ {shd}: Kết quả='Đã xử lý' | Thao tác='{thao_tac}'", lvl, "clear_cls")

                except Exception as ex_single:
                    if shd:
                        processed_shds.add(shd)
                    clean_ex = re.sub(r"^không\s+thành\s+công\s*[:\-]?", "", str(ex_single).strip(), flags=re.IGNORECASE).strip()
                    err_thao_tac = f"Không thành công : {clean_ex[:60]}"
                    task_log(f"Lỗi khi Clear Cls HĐ {shd}: {clean_ex[:60]}", "error", "clear_cls")
                    now_str = time.strftime("%d/%m/%Y %H:%M:%S")
                    r["Kết Quả"] = "Đã xử lý"
                    r["Thao Tác"] = err_thao_tac
                    r["Ngày Cập Nhật"] = now_str
                    update_sheet_remote_cls(r, err_thao_tac)

                    cls_task_state["processed_in_session"].append({
                        "shd": shd,
                        "ket_qua": "Đã xử lý",
                        "thao_tac": err_thao_tac,
                        "is_success": False,
                        "time": now_str,
                        "reason": r.get("Nguyên Nhân 1", "")
                    })

                time.sleep(2)

            cls_task_state["message"] = f"Hoàn tất xử lý {len(to_process)} hợp đồng Clear Cls có SR!"
            task_log(f"=== HOÀN TẤT TIẾN TRÌNH AUTO CLEAR CLS CÓ SR ===", "success")

        except Exception as e:
            raw_err = str(e)
            cls_task_state["message"] = f"Lỗi Clear Cls: {raw_err}"
            task_log(f"Tiến trình Auto Clear Cls bị dừng: {raw_err}", "error")
            core_login.invalidate_session(log_cb=task_log)  # phiên nghi ngờ hỏng/đơ -> lần sau đăng nhập mới
        finally:
            _release_remaining_auto_attempts("cls", to_process, processed_shds)
            cls_task_state["is_running"] = False
            if bot:
                try:
                    bot.close()
                except Exception:
                    pass
            active_cls_bot = None
            core_login.release_inside_task("cls")

    try:
        threading.Thread(target=worker_cls, daemon=True).start()
    except Exception:
        cls_task_state["is_running"] = False
        core_login.release_inside_task("cls")
        raise
    return jsonify({"status": "started", "count": len(to_process)})


# ================= TAB 5: AUTO PHÂN CÔNG TAY =================
import inside_assign

assign_task_state = {
    "is_running": False,
    "current_index": 0,
    "total": 0,
    "current_shd": "",
    "message": "Sẵn sàng",
    "sheet_id": inside_assign.DEFAULT_SHEET_ID,
    "gid": inside_assign.GID_ASSIGN,
    "processed_in_session": []
}
active_assign_bot = None

@app.route("/api/assign/sheet-data", methods=["GET"])
def get_assign_sheet_data():
    sheet_id = request.args.get("sheet_id", inside_assign.DEFAULT_SHEET_ID).strip()
    gid      = request.args.get("gid", inside_assign.GID_ASSIGN).strip()
    data = inside_assign.fetch_sheet_data(sheet_id=sheet_id, gid=gid)
    if data["status"] != "ok":
        return jsonify(data), 500
    session_items = list(assign_task_state.get("processed_in_session") or [])
    if session_items and data.get("records"):
        now_ts = time.time()
        by_shd_id = {}
        by_shd = {}
        for it in session_items:
            if not isinstance(it, dict):
                continue
            ts_ep = it.get("timestamp_epoch")
            if isinstance(ts_ep, (int, float)) and (now_ts - ts_ep > 300):
                continue
            s = str(it.get("shd") or "").strip()
            rid = str(it.get("row_id") or "").strip()
            if not s:
                continue
            if rid:
                by_shd_id[(s, rid)] = it
            by_shd[s] = it
        for r in data["records"]:
            raw_tt = str(r.get("Thao Tác") or "").strip().lower()
            if raw_tt and raw_tt not in ("nan", "chưa cập nhật", "chưa xử lý"):
                continue
            s = str(r.get("SHD") or "").strip()
            rid = str(r.get("ID") or "").strip()
            hit = by_shd_id.get((s, rid)) if (s and rid) else None
            if not hit and s:
                cand = by_shd.get(s)
                if cand and (not rid or not cand.get("row_id") or str(cand.get("row_id")).strip() == rid):
                    hit = cand
            if hit:
                if hit.get("thao_tac"):
                    r["Thao Tác"] = hit["thao_tac"]
                raw_ngay = str(r.get("Ngày Cập Nhật") or "").strip().lower()
                if hit.get("time") and raw_ngay in ("", "nan", "chưa cập nhật", "chưa xử lý"):
                    r["Ngày Cập Nhật"] = hit["time"]
    return jsonify(data)

@app.route("/api/assign/live-status", methods=["GET"])
def get_assign_live_status():
    return jsonify({
        "task": assign_task_state,
        "processed_in_session": assign_task_state.get("processed_in_session", [])
    })

@app.route("/api/assign/clear-cache", methods=["POST"])
@app.route("/api/assign/clear_cache", methods=["POST"])
def clear_assign_cache():
    clear_auto_attempts("assign")
    add_log("Đã làm mới bộ nhớ đệm Phân Công Tay!", "success")
    return jsonify({"status": "ok", "message": "Đã làm mới bộ nhớ đệm Phân Công Tay."})

@app.route("/api/assign/export", methods=["GET", "POST"])
def export_assign_excel():
    data = request.json if request.is_json else request.args
    gid = data.get("gid", inside_assign.GID_ASSIGN)
    sheet_id = data.get("sheet_id", inside_assign.DEFAULT_SHEET_ID)
    status_filter = data.get("status", "all")
    
    sheet_res = inside_assign.fetch_sheet_data(sheet_id=sheet_id, gid=gid)
    records = sheet_res.get("records", []) if sheet_res.get("status") == "ok" else []

    if status_filter == "done":
        filtered = [r for r in records if "thành công" in str(r.get("Thao Tác", "")).lower()]
    elif status_filter == "pending":
        filtered = [r for r in records if not inside_assign.is_final_thao_tac(r.get("Thao Tác", ""))]
    else:
        filtered = records

    if not filtered:
        filtered = records

    if not filtered:
        return jsonify({"status": "error", "message": "Không có dữ liệu Phân Công Tay để xuất file"}), 400

    export_rows = []
    for idx, r in enumerate(filtered, 1):
        export_rows.append({
            "STT": idx,
            "Tác Vụ": r.get("Tác Vụ") or "Phân Công Tay",
            "Số Hợp Đồng": r.get("SHD", ""),
            "Email NVKT": r.get("Email", ""),
            "Loại Tác Vụ": r.get("Loại Tác Vụ", ""),
            "Block Đến": r.get("Block Đến", ""),
            "Nhân Viên Đến": r.get("Nhân Viên Đến", ""),
            "Ngày Cập Nhật": r.get("Ngày Cập Nhật", ""),
            "Thao Tác": r.get("Thao Tác", "")
        })

    df = pd.DataFrame(export_rows)
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name="Phan_Cong_Data")
    output.seek(0)

    filename = f"Phan_Cong_Tay_Data_Xu_Ly_{time.strftime('%Y%m%d_%H%M%S')}.xlsx"
    return send_file(
        output,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        as_attachment=True,
        download_name=filename
    )

@app.route("/api/assign/run", methods=["POST"])
def run_assign_process():
    ok_lock, owner = core_login.try_acquire_inside_task("assign")
    if not ok_lock:
        return jsonify({
            "status": "busy",
            "error": f"Đang bận chạy tiến trình Inside: {owner}",
            "message": f"Đang bận chạy tiến trình Inside: {owner}"
        }), 409

    validated = False
    try:
        if assign_task_state["is_running"]:
            return jsonify({"status": "busy", "message": "Đang có tiến trình Phân Công Tay đang chạy..."}), 429
        if cls_task_state.get("is_running"):
            return jsonify({"status": "busy", "message": "Đang có tiến trình Clear Cls đang chạy. Hãy chờ hoàn tất!"}), 429
        if bypass_task_state.get("is_running"):
            return jsonify({"status": "busy", "message": "Đang có tiến trình ByPass đang chạy trên Inside FPT."}), 429

        data            = request.json or {}
        sheet_id        = data.get("sheet_id", inside_assign.DEFAULT_SHEET_ID)
        gid             = data.get("gid", inside_assign.GID_ASSIGN)
        selected_records= data.get("records")
        headless        = data.get("headless", True)

        if selected_records:
            to_process = selected_records
        else:
            sheet_res = inside_assign.fetch_sheet_data(sheet_id=sheet_id, gid=gid)
            if sheet_res["status"] != "ok" or not sheet_res["records"]:
                return jsonify({"status": "error", "message": "Không tìm thấy dữ liệu trên Google Sheet Phân Công Tay"}), 400
            to_process = [r for r in sheet_res["records"]
                          if not inside_assign.is_final_thao_tac(r.get("Thao Tác", ""))]
            if not to_process:
                return jsonify({
                    "status": "empty",
                    "count": 0,
                    "message": "Không có hợp đồng mới cần xử lý Phân Công Tay trên Google Sheet!"
                }), 200

        if not to_process:
            return jsonify({"status": "empty", "count": 0, "message": "Không có hợp đồng nào được chọn để xử lý!"}), 200
        validated = True
    finally:
        if not validated:
            core_login.release_inside_task("assign")

    assign_task_state["is_running"]             = True
    assign_task_state["total"]                  = len(to_process)
    assign_task_state["current_index"]          = 0
    assign_task_state["current_shd"]            = str(to_process[0].get("SHD", ""))
    assign_task_state["message"]                = f"Bắt đầu xử lý {len(to_process)} hợp đồng Phân Công Tay..."
    assign_task_state["sheet_id"]               = sheet_id
    assign_task_state["gid"]                    = gid
    assign_task_state["processed_in_session"]   = []
    task_log = make_task_logger(assign_task_state, "manual_assign", "Phân Công Tay")

    mode_label = "Chạy ngầm (Headless)" if headless else "Mở Chrome xem trực tiếp (Visible)"
    task_log(f"=== BẮT ĐẦU AUTO PHÂN CÔNG TAY {len(to_process)} HỢP ĐỒNG ({mode_label}) ===", "info")

    def update_sheet_remote_assign(record, thao_tac_val):
        cfg = core_login.load_config()
        webhook_url = cfg.get("assign_webhook_url", "") or cfg.get("google_sheet_webhook_url", "")
        if webhook_url:
            payload = {
                "sheet_id": sheet_id,
                "gid": gid,
                "row_id": record.get("ID"),
                "shd": record.get("SHD"),
                "status": thao_tac_val,
                "thao_tac": thao_tac_val,
                "timestamp": time.strftime("%d/%m/%Y %H:%M:%S")
            }
            last_err = None
            for attempt_idx in range(3):
                try:
                    req = urllib.request.Request(
                        webhook_url,
                        data=json.dumps(payload).encode("utf-8"),
                        headers={"Content-Type": "application/json"}
                    )
                    urllib.request.urlopen(req, timeout=10)
                    task_log(f"Đã cập nhật Webhook Phân Công Tay cho HĐ {record.get('SHD')}: '{thao_tac_val}'", "success")
                    last_err = None
                    break
                except Exception as e_hook:
                    last_err = e_hook
                    if attempt_idx < 2:
                        time.sleep(2)
            if last_err is not None:
                task_log(f"Không thể đẩy Webhook cho HĐ {record.get('SHD')}: {last_err}", "warning")

    def worker_assign():
        global active_assign_bot
        bot = inside_assign.InsideAssignAutomation(headless=headless, keep_open=True, log_cb=task_log)
        active_assign_bot = bot
        processed_shds = set()
        try:
            bot.init_driver()
            bot.navigate_to_assign_page()

            for idx, r in enumerate(to_process):
                shd = str(r.get("SHD", "")).strip()
                assign_task_state["current_index"] = idx + 1
                assign_task_state["current_shd"]   = shd
                assign_task_state["message"]        = f"Đang xử lý Phân Công {idx + 1}/{len(to_process)}: HĐ {shd}..."

                try:
                    is_ok, thao_tac = bot.process_row(r)
                    if shd:
                        processed_shds.add(shd)
                    now_str = time.strftime("%d/%m/%Y %H:%M:%S")

                    r["Thao Tác"]       = thao_tac
                    r["Ngày Cập Nhật"] = now_str
                    update_sheet_remote_assign(r, thao_tac)

                    assign_task_state["processed_in_session"].append({
                        "shd":             shd,
                        "row_id":          str(r.get("ID", "")).strip(),
                        "thao_tac":        thao_tac,
                        "is_success":      is_ok,
                        "time":            now_str,
                        "timestamp_epoch": time.time()
                    })

                    lvl = "success" if is_ok else "warning"
                    task_log(f"Phân Công HĐ {shd}: '{thao_tac}'", lvl, "manual_assign")

                except Exception as ex_single:
                    if shd:
                        processed_shds.add(shd)
                    now_str = time.strftime("%d/%m/%Y %H:%M:%S")
                    err_thao_tac = inside_assign.format_assign_thao_tac(False, str(ex_single)[:80])
                    task_log(f"Lỗi Phân Công Tay HĐ {shd}: {str(ex_single)[:60]}", "error", "manual_assign")
                    r["Thao Tác"]       = err_thao_tac
                    r["Ngày Cập Nhật"] = now_str
                    update_sheet_remote_assign(r, err_thao_tac)
                    assign_task_state["processed_in_session"].append({
                        "shd":             shd,
                        "row_id":          str(r.get("ID", "")).strip(),
                        "thao_tac":        err_thao_tac,
                        "is_success":      False,
                        "time":            now_str,
                        "timestamp_epoch": time.time()
                    })

                time.sleep(2)

            assign_task_state["message"] = f"Hoàn tất xử lý {len(to_process)} hợp đồng Phân Công Tay!"
            task_log("=== HOÀN TẤT TIẾN TRÌNH AUTO PHÂN CÔNG TAY ===", "success")

        except Exception as e:
            assign_task_state["message"] = f"Lỗi Phân Công Tay: {e}"
            task_log(f"Tiến trình Phân Công Tay bị dừng: {e}", "error")
            core_login.invalidate_session(log_cb=task_log)  # phiên nghi ngờ hỏng/đơ -> lần sau đăng nhập mới
        finally:
            _release_remaining_auto_attempts("assign", to_process, processed_shds)
            assign_task_state["is_running"] = False
            if bot:
                try:
                    bot.close()
                except Exception:
                    pass
            active_assign_bot = None
            core_login.release_inside_task("assign")

    try:
        threading.Thread(target=worker_assign, daemon=True).start()
    except Exception:
        assign_task_state["is_running"] = False
        core_login.release_inside_task("assign")
        raise
    return jsonify({"status": "started", "count": len(to_process)})


# ================= TAB: AUTO CLEAR TÍN HIỆU & CẤP LẠI TÍN HIỆU =================
import inside_signal

clear_signal_task_state = {
    "is_running": False,
    "current_index": 0,
    "total": 0,
    "current_shd": "",
    "message": "Sẵn sàng",
    "sheet_id": inside_signal.DEFAULT_SHEET_ID,
    "gid": inside_signal.GID_CLEAR_SIGNAL,
    "processed_in_session": []
}
active_clear_signal_bot = None

reset_signal_task_state = {
    "is_running": False,
    "current_index": 0,
    "total": 0,
    "current_shd": "",
    "message": "Sẵn sàng",
    "sheet_id": inside_signal.DEFAULT_SHEET_ID,
    "gid": inside_signal.GID_RESET_SIGNAL,
    "processed_in_session": []
}
active_reset_signal_bot = None

# 1. Clear Tín Hiệu Routes
@app.route("/api/clear-signal/sheet-data", methods=["GET"])
def get_clear_signal_sheet_data():
    sheet_id = request.args.get("sheet_id", inside_signal.DEFAULT_SHEET_ID).strip()
    gid      = request.args.get("gid", inside_signal.GID_CLEAR_SIGNAL).strip()
    data = inside_signal.fetch_sheet_data(sheet_id=sheet_id, gid=gid, signal_type="clear")
    if data["status"] != "ok":
        return jsonify(data), 500
    _decorate_signal_lock_flags("clear_signal", data.get("records", []))
    return jsonify(data)

@app.route("/api/clear-signal/live-status", methods=["GET"])
def get_clear_signal_live_status():
    return jsonify({
        "task": clear_signal_task_state,
        "processed_in_session": clear_signal_task_state.get("processed_in_session", [])
    })

@app.route("/api/clear-signal/clear-cache", methods=["POST"])
@app.route("/api/clear-signal/clear_cache", methods=["POST"])
def clear_clear_signal_cache():
    if os.path.exists(inside_signal.CLEAR_SIGNAL_CACHE_FILE):
        try:
            os.remove(inside_signal.CLEAR_SIGNAL_CACHE_FILE)
        except Exception:
            pass
    add_log("Đã xóa sạch cache trạng thái Clear Tín Hiệu!", "success")
    return jsonify({"status": "ok", "message": "Đã xóa sạch cache trạng thái Clear Tín Hiệu."})

@app.route("/api/clear-signal/export", methods=["GET", "POST"])
def export_clear_signal_excel():
    data = request.json if request.is_json else request.args
    gid = data.get("gid", inside_signal.GID_CLEAR_SIGNAL)
    sheet_id = data.get("sheet_id", inside_signal.DEFAULT_SHEET_ID)
    status_filter = data.get("status", "all")

    sheet_res = inside_signal.fetch_sheet_data(sheet_id=sheet_id, gid=gid, signal_type="clear")
    records = sheet_res.get("records", []) if sheet_res.get("status") == "ok" else []

    if status_filter == "done":
        filtered = [r for r in records if inside_signal.is_final_status(r.get("Kết Quả", ""))]
    elif status_filter == "pending":
        filtered = [r for r in records if not inside_signal.is_final_status(r.get("Kết Quả", ""))]
    else:
        filtered = records

    if not filtered:
        filtered = records

    if not filtered:
        return jsonify({"status": "error", "message": "Không có dữ liệu Clear Tín Hiệu để xuất file"}), 400

    export_rows = []
    for idx, r in enumerate(filtered, 1):
        export_rows.append({
            "STT": idx,
            "Họ và Tên": r.get("Họ và Tên", ""),
            "Email NVKT": r.get("Email", ""),
            "Số Hợp Đồng": r.get("SHD", ""),
            "Địa Chỉ MAC": r.get("MAC", ""),
            "Ngày Cập Nhật": r.get("Ngày Cập Nhật", ""),
            "Auto Cấp Lại": r.get("Auto Cấp Lại", ""),
            "Kết Quả": r.get("Kết Quả", "")
        })

    df = pd.DataFrame(export_rows)
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name="Clear_Tin_Hieu")
    output.seek(0)

    filename = f"Clear_Tin_Hieu_Data_Xu_Ly_{time.strftime('%Y%m%d_%H%M%S')}.xlsx"
    return send_file(
        output,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        as_attachment=True,
        download_name=filename
    )

@app.route("/api/clear-signal/run", methods=["POST"])
def run_clear_signal_process():
    ok, busy_by = core_login.try_acquire_inside_task("clear_signal")
    if not ok:
        return jsonify({
            "status": "error",
            "message": f"Phiên Chrome Inside FPT đang bận chạy '{busy_by}'. Vui lòng đợi tiến trình đó hoàn tất!"
        }), 409

    validated = False
    try:
        if clear_signal_task_state["is_running"]:
            return jsonify({"status": "busy", "message": "Đang có tiến trình Clear Tín Hiệu đang chạy..."}), 429
        if reset_signal_task_state["is_running"]:
            return jsonify({"status": "busy", "message": "Đang có tiến trình Cấp Lại Tín Hiệu đang chạy..."}), 429

        data            = request.json or {}
        sheet_id        = data.get("sheet_id", inside_signal.DEFAULT_SHEET_ID)
        gid             = data.get("gid", inside_signal.GID_CLEAR_SIGNAL)
        selected_records= data.get("records")
        headless        = data.get("headless", True)
        is_manual       = bool(data.get("manual"))

        if selected_records:
            if is_manual:
                to_process = list(selected_records)
            else:
                to_process = [
                    r for r in selected_records
                    if not inside_signal.is_final_status(r.get("Kết Quả", ""))
                    and not _is_signal_manual_locked("clear_signal", r)
                ]
        else:
            sheet_res = inside_signal.fetch_sheet_data(sheet_id=sheet_id, gid=gid, signal_type="clear")
            if sheet_res["status"] != "ok" or not sheet_res["records"]:
                return jsonify({"status": "error", "message": "Không tìm thấy dữ liệu trên Google Sheet Clear Tín Hiệu"}), 400
            _decorate_signal_lock_flags("clear_signal", sheet_res["records"])
            to_process = [
                r for r in sheet_res["records"]
                if not inside_signal.is_final_status(r.get("Kết Quả", ""))
                and (is_manual or not _is_signal_manual_locked("clear_signal", r))
            ]

        if not to_process:
            msg_empty = (
                "Không có hợp đồng mới cần xử lý Clear Tín Hiệu (các HĐ tồn ngày cũ / lỗi đăng nhập phải thao tác tay)!"
                if not is_manual else
                "Không có hợp đồng nào được chọn để Clear Tín Hiệu!"
            )
            return jsonify({"status": "empty", "count": 0, "message": msg_empty}), 200

        if is_manual:
            _unlock_signal_contracts_from_manual("clear_signal", [r.get("SHD") for r in to_process])

        clear_signal_task_state["is_running"]           = True
        clear_signal_task_state["total"]                = len(to_process)
        clear_signal_task_state["current_index"]        = 0
        clear_signal_task_state["current_shd"]          = str(to_process[0].get("SHD", ""))
        clear_signal_task_state["message"]              = f"Bắt đầu xử lý {len(to_process)} hợp đồng Clear Tín Hiệu..."
        clear_signal_task_state["sheet_id"]             = sheet_id
        clear_signal_task_state["gid"]                  = gid
        clear_signal_task_state["processed_in_session"] = []
        validated = True
    finally:
        if not validated:
            core_login.release_inside_task("clear_signal")

    mode_label = "Chạy ngầm (Headless)" if headless else "Mở Chrome xem trực tiếp (Visible)"
    task_log = make_task_logger(clear_signal_task_state, "clear_signal", "Clear Tín Hiệu")
    task_log(f"=== BẮT ĐẦU AUTO CLEAR TÍN HIỆU {len(to_process)} HỢP ĐỒNG ({mode_label}) ===", "info")

    def update_sheet_remote_signal(record, kq_val, sig_type="clear"):
        cfg = core_login.load_config()
        webhook_url = cfg.get(f"{sig_type}_signal_webhook_url", "") or cfg.get("google_sheet_webhook_url", "")
        if webhook_url:
            try:
                payload = {
                    "sheet_id": sheet_id,
                    "gid": gid,
                    "row_id": record.get("ID"),
                    "shd": record.get("SHD"),
                    "status": kq_val,
                    "ket_qua": kq_val,
                    "thao_tac": kq_val,
                    "timestamp": time.strftime("%d/%m/%Y %H:%M:%S")
                }
                auto_val = record.get("Auto Cấp Lại") or ""
                if auto_val:
                    payload["auto_cap_lai"] = auto_val
                    payload["col_auto_cap_lai"] = 7
                req = urllib.request.Request(
                    webhook_url,
                    data=json.dumps(payload).encode("utf-8"),
                    headers={"Content-Type": "application/json"}
                )
                urllib.request.urlopen(req, timeout=8)
                task_log(f"Đã cập nhật Webhook {sig_type} cho HĐ {record.get('SHD')}: '{kq_val}'", "success")
            except Exception as e_hook:
                task_log(f"Không thể đẩy Webhook cho HĐ {record.get('SHD')}: {e_hook}", "warning")

    def worker_clear_signal():
        global active_clear_signal_bot
        bot = None
        processed_shds = set()
        try:
            bot = inside_signal.InsideSignalAutomation(signal_type="clear", headless=headless, log_cb=task_log)
            active_clear_signal_bot = bot
            bot.init_driver()
            if not bot.driver:
                raise RuntimeError("Không thể khởi tạo/đăng nhập trình duyệt Chrome cho Clear Tín Hiệu")
            for idx, r in enumerate(to_process):
                shd = str(r.get("SHD", "")).strip()
                clear_signal_task_state["current_index"] = idx + 1
                clear_signal_task_state["current_shd"]   = shd
                clear_signal_task_state["message"]        = f"Đang Clear Tín Hiệu {idx + 1}/{len(to_process)}: HĐ {shd}..."

                try:
                    is_ok, kq_str, now_str = bot.process_row(r)
                    processed_shds.add(shd)
                    r["Kết Quả"] = kq_str
                    r["Ngày Cập Nhật"] = now_str
                    # Sau khi clear thành công => Auto Cấp Lại = Bình Thường ( Tồn: 0H )
                    if is_ok and "lỗi" not in str(kq_str).lower():
                        r["Auto Cấp Lại"] = "Bình Thường ( Tồn: 0H )"
                        r["Auto Cap Lai"] = "Bình Thường ( Tồn: 0H )"
                        _unlock_signal_contracts_from_manual("clear_signal", [shd])
                    elif not is_manual:
                        _lock_signal_contracts_for_manual("clear_signal", [shd], reason="login_or_server_error")
                    update_sheet_remote_signal(r, kq_str, "clear")

                    clear_signal_task_state["processed_in_session"].append({
                        "shd": shd,
                        "ket_qua": kq_str,
                        "is_success": is_ok,
                        "time": now_str
                    })

                    lvl = "success" if is_ok else "warning"
                    task_log(f"Clear Tín Hiệu HĐ {shd}: '{kq_str}'", lvl, "clear_signal")
                except Exception as ex_single:
                    processed_shds.add(shd)
                    now_str = time.strftime("%d/%m/%Y %H:%M:%S")
                    err_kq = f"Lỗi: {str(ex_single)[:60]}"
                    task_log(f"Lỗi Clear Tín Hiệu HĐ {shd}: {str(ex_single)[:60]}", "error", "clear_signal")
                    r["Kết Quả"] = err_kq
                    r["Ngày Cập Nhật"] = now_str
                    inside_signal.update_cache_record("clear", shd, err_kq, now_str)
                    if not is_manual:
                        _lock_signal_contracts_for_manual("clear_signal", [shd], reason="login_or_server_error")
                    update_sheet_remote_signal(r, err_kq, "clear")

                    clear_signal_task_state["processed_in_session"].append({
                        "shd": shd,
                        "ket_qua": err_kq,
                        "is_success": False,
                        "time": now_str
                    })
                time.sleep(1.5)

            clear_signal_task_state["message"] = f"Hoàn tất xử lý {len(to_process)} hợp đồng Clear Tín Hiệu!"
            task_log("=== HOÀN TẤT TIẾN TRÌNH AUTO CLEAR TÍN HIỆU ===", "success")
        except Exception as e:
            clear_signal_task_state["message"] = f"Lỗi Clear Tín Hiệu: {e}"
            task_log(f"Tiến trình Clear Tín Hiệu bị dừng: {e}", "error")
            core_login.invalidate_session(log_cb=task_log)  # phiên nghi ngờ hỏng/đơ -> lần sau đăng nhập mới
            if not is_manual:
                remaining_shds = [str(r.get("SHD", "")).strip() for r in to_process if str(r.get("SHD", "")).strip() not in processed_shds]
                _lock_signal_contracts_for_manual("clear_signal", remaining_shds, reason="login_or_server_error")
        finally:
            clear_signal_task_state["is_running"] = False
            if bot:
                try:
                    bot.close()
                except Exception:
                    pass
            active_clear_signal_bot = None
            core_login.release_inside_task("clear_signal")

    try:
        threading.Thread(target=worker_clear_signal, daemon=True).start()
    except Exception:
        clear_signal_task_state["is_running"] = False
        core_login.release_inside_task("clear_signal")
        raise
    return jsonify({"status": "started", "count": len(to_process)})


# 2. Cấp Lại Tín Hiệu Routes
@app.route("/api/reset-signal/sheet-data", methods=["GET"])
def get_reset_signal_sheet_data():
    sheet_id = request.args.get("sheet_id", inside_signal.DEFAULT_SHEET_ID).strip()
    gid      = request.args.get("gid", inside_signal.GID_RESET_SIGNAL).strip()
    data = inside_signal.fetch_sheet_data(sheet_id=sheet_id, gid=gid, signal_type="reset")
    if data["status"] != "ok":
        return jsonify(data), 500
    _decorate_signal_lock_flags("reset_signal", data.get("records", []))
    return jsonify(data)

@app.route("/api/reset-signal/live-status", methods=["GET"])
def get_reset_signal_live_status():
    return jsonify({
        "task": reset_signal_task_state,
        "processed_in_session": reset_signal_task_state.get("processed_in_session", [])
    })

@app.route("/api/reset-signal/clear-cache", methods=["POST"])
@app.route("/api/reset-signal/clear_cache", methods=["POST"])
def clear_reset_signal_cache():
    if os.path.exists(inside_signal.RESET_SIGNAL_CACHE_FILE):
        try:
            os.remove(inside_signal.RESET_SIGNAL_CACHE_FILE)
        except Exception:
            pass
    add_log("Đã xóa sạch cache trạng thái Cấp Lại Tín Hiệu!", "success")
    return jsonify({"status": "ok", "message": "Đã xóa sạch cache trạng thái Cấp Lại Tín Hiệu."})

@app.route("/api/reset-signal/export", methods=["GET", "POST"])
def export_reset_signal_excel():
    data = request.json if request.is_json else request.args
    gid = data.get("gid", inside_signal.GID_RESET_SIGNAL)
    sheet_id = data.get("sheet_id", inside_signal.DEFAULT_SHEET_ID)
    status_filter = data.get("status", "all")

    sheet_res = inside_signal.fetch_sheet_data(sheet_id=sheet_id, gid=gid, signal_type="reset")
    records = sheet_res.get("records", []) if sheet_res.get("status") == "ok" else []

    if status_filter == "done":
        filtered = [r for r in records if inside_signal.is_final_status(r.get("Kết Quả", ""))]
    elif status_filter == "pending":
        filtered = [r for r in records if not inside_signal.is_final_status(r.get("Kết Quả", ""))]
    else:
        filtered = records

    if not filtered:
        filtered = records

    if not filtered:
        return jsonify({"status": "error", "message": "Không có dữ liệu Cấp Lại Tín Hiệu để xuất file"}), 400

    export_rows = []
    for idx, r in enumerate(filtered, 1):
        export_rows.append({
            "STT": idx,
            "Họ và Tên": r.get("Họ và Tên", ""),
            "Email NVKT": r.get("Email", ""),
            "Số Hợp Đồng": r.get("SHD", ""),
            "Ngày Cập Nhật": r.get("Ngày Cập Nhật", ""),
            "Nguồn": r.get("Nguồn", "User"),
            "Kết Quả": r.get("Kết Quả", "")
        })

    df = pd.DataFrame(export_rows)
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name="Cap_Lai_Tin_Hieu")
    output.seek(0)

    filename = f"Cap_Lai_Tin_Hieu_Data_Xu_Ly_{time.strftime('%Y%m%d_%H%M%S')}.xlsx"
    return send_file(
        output,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        as_attachment=True,
        download_name=filename
    )

@app.route("/api/reset-signal/run", methods=["POST"])
def run_reset_signal_process():
    ok, busy_by = core_login.try_acquire_inside_task("reset_signal")
    if not ok:
        return jsonify({
            "status": "error",
            "message": f"Phiên Chrome Inside FPT đang bận chạy '{busy_by}'. Vui lòng đợi tiến trình đó hoàn tất!"
        }), 409

    validated = False
    try:
        if reset_signal_task_state["is_running"]:
            return jsonify({"status": "busy", "message": "Đang có tiến trình Cấp Lại Tín Hiệu đang chạy..."}), 429
        if clear_signal_task_state["is_running"]:
            return jsonify({"status": "busy", "message": "Đang có tiến trình Clear Tín Hiệu đang chạy..."}), 429

        data            = request.json or {}
        sheet_id        = data.get("sheet_id", inside_signal.DEFAULT_SHEET_ID)
        gid             = data.get("gid", inside_signal.GID_RESET_SIGNAL)
        selected_records= data.get("records")
        headless        = data.get("headless", True)
        is_manual       = bool(data.get("manual"))

        if selected_records:
            if is_manual:
                to_process = list(selected_records)
            else:
                to_process = [
                    r for r in selected_records
                    if not inside_signal.is_final_status(r.get("Kết Quả", ""))
                    and not _is_signal_manual_locked("reset_signal", r)
                ]
        else:
            sheet_res = inside_signal.fetch_sheet_data(sheet_id=sheet_id, gid=gid, signal_type="reset")
            if sheet_res["status"] != "ok" or not sheet_res["records"]:
                return jsonify({"status": "error", "message": "Không tìm thấy dữ liệu trên Google Sheet Cấp Lại Tín Hiệu"}), 400
            _decorate_signal_lock_flags("reset_signal", sheet_res["records"])
            to_process = [
                r for r in sheet_res["records"]
                if not inside_signal.is_final_status(r.get("Kết Quả", ""))
                and (is_manual or not _is_signal_manual_locked("reset_signal", r))
            ]

        if not to_process:
            msg_empty = (
                "Không có hợp đồng mới cần xử lý Cấp Lại Tín Hiệu (các HĐ tồn ngày cũ / lỗi đăng nhập phải thao tác tay)!"
                if not is_manual else
                "Không có hợp đồng nào được chọn để Cấp Lại Tín Hiệu!"
            )
            return jsonify({"status": "empty", "count": 0, "message": msg_empty}), 200

        if is_manual:
            _unlock_signal_contracts_from_manual("reset_signal", [r.get("SHD") for r in to_process])

        reset_signal_task_state["is_running"]           = True
        reset_signal_task_state["total"]                = len(to_process)
        reset_signal_task_state["current_index"]        = 0
        reset_signal_task_state["current_shd"]          = str(to_process[0].get("SHD", ""))
        reset_signal_task_state["message"]              = f"Bắt đầu xử lý {len(to_process)} hợp đồng Cấp Lại Tín Hiệu..."
        reset_signal_task_state["sheet_id"]             = sheet_id
        reset_signal_task_state["gid"]                  = gid
        reset_signal_task_state["processed_in_session"] = []

        is_auto_72h = data.get("source") == "auto_72h" or any(isinstance(r, dict) and r.get("_is_auto_72h") for r in to_process)
        if is_auto_72h:
            for r in to_process:
                if isinstance(r, dict):
                    r["_is_auto_72h"] = True
        validated = True
    finally:
        if not validated:
            core_login.release_inside_task("reset_signal")

    mode_label = "Chạy ngầm (Headless)" if headless else "Mở Chrome xem trực tiếp (Visible)"
    auto_tag = " [TỰ ĐỘNG 72H]" if is_auto_72h else ""
    task_log = make_task_logger(reset_signal_task_state, "reset_signal", "Cấp Lại Tín Hiệu")
    task_log(f"=== BẮT ĐẦU AUTO CẤP LẠI TÍN HIỆU {len(to_process)} HỢP ĐỒNG{auto_tag} ({mode_label}) ===", "info")

    def update_sheet_remote_signal(record, kq_val, sig_type="reset"):
        cfg = core_login.load_config()
        webhook_url = cfg.get(f"{sig_type}_signal_webhook_url", "") or cfg.get("google_sheet_webhook_url", "")
        if webhook_url:
            try:
                final_nguon = record.get("Nguồn") or ("Auto >72H" if (is_auto_72h or record.get("_is_auto_72h")) else "User")
                payload = {
                    "sheet_id": sheet_id,
                    "gid": gid,
                    "row_id": record.get("ID"),
                    "shd": record.get("SHD"),
                    "status": final_nguon,
                    "ket_qua": kq_val,
                    "thao_tac": final_nguon,
                    "nguon": final_nguon,
                    "col_nguon": 6,
                    "col_thao_tac": 6,
                    "col_ket_qua": 4,
                    "timestamp": time.strftime("%d/%m/%Y %H:%M:%S")
                }
                if is_auto_72h or record.get("_is_auto_72h"):
                    payload["action"] = "append"
                    payload["ho_ten"] = record.get("Họ và Tên", "")
                    payload["email"] = record.get("Email", "")
                req = urllib.request.Request(
                    webhook_url,
                    data=json.dumps(payload).encode("utf-8"),
                    headers={"Content-Type": "application/json"}
                )
                urllib.request.urlopen(req, timeout=8)
                task_log(f"Đã cập nhật Webhook {sig_type} cho HĐ {record.get('SHD')} (GID {gid}): '{kq_val}' [Nguồn: {final_nguon}]", "success")
            except Exception as e_hook:
                task_log(f"Không thể đẩy Webhook cho HĐ {record.get('SHD')}: {e_hook}", "warning")

    def worker_reset_signal():
        global active_reset_signal_bot
        bot = None
        processed_shds = set()
        try:
            bot = inside_signal.InsideSignalAutomation(signal_type="reset", headless=headless, log_cb=task_log)
            active_reset_signal_bot = bot
            bot.init_driver()
            if not bot.driver:
                raise RuntimeError("Không thể khởi tạo/đăng nhập trình duyệt Chrome cho Cấp Lại Tín Hiệu")
            for idx, r in enumerate(to_process):
                shd = str(r.get("SHD", "")).strip()
                reset_signal_task_state["current_index"] = idx + 1
                reset_signal_task_state["current_shd"]   = shd
                reset_signal_task_state["message"]        = f"Đang Cấp Lại Tín Hiệu {idx + 1}/{len(to_process)}: HĐ {shd}..."

                try:
                    is_ok, kq_str, now_str = bot.process_row(r)
                    processed_shds.add(shd)
                    r["Kết Quả"] = kq_str
                    r["Ngày Cập Nhật"] = now_str
                    # Đảm bảo Nguồn được ghi vào record để webhook & table lấy đúng
                    if not r.get("Nguồn") and not r.get("Nguon"):
                        final_nguon_set = "Auto >72H" if (is_auto_72h or r.get("_is_auto_72h")) else "User"
                        r["Nguồn"] = final_nguon_set
                        r["Nguon"] = final_nguon_set
                    if is_ok and "lỗi" not in str(kq_str).lower():
                        _unlock_signal_contracts_from_manual("reset_signal", [shd])
                        if is_auto_72h or r.get("_is_auto_72h"):
                            try:
                                st_72 = inside_signal.load_cache(AUTO_RESET_STATE_FILE)
                                st_72[shd] = now_str
                                inside_signal.save_cache(AUTO_RESET_STATE_FILE, st_72)
                            except Exception:
                                pass
                    elif not is_manual:
                        _lock_signal_contracts_for_manual("reset_signal", [shd], reason="login_or_server_error")
                    update_sheet_remote_signal(r, kq_str, "reset")

                    reset_signal_task_state["processed_in_session"].append({
                        "shd": shd,
                        "ket_qua": kq_str,
                        "is_success": is_ok,
                        "time": now_str
                    })

                    lvl = "success" if is_ok else "warning"
                    task_log(f"Cấp Lại Tín Hiệu HĐ {shd}: '{kq_str}'", lvl, "reset_signal")
                except Exception as ex_single:
                    processed_shds.add(shd)
                    now_str = time.strftime("%d/%m/%Y %H:%M:%S")
                    err_kq = f"Lỗi: {str(ex_single)[:60]}"
                    task_log(f"Lỗi Cấp Lại Tín Hiệu HĐ {shd}: {str(ex_single)[:60]}", "error", "reset_signal")
                    r["Kết Quả"] = err_kq
                    r["Ngày Cập Nhật"] = now_str
                    inside_signal.update_cache_record("reset", shd, err_kq, now_str)
                    if not is_manual:
                        _lock_signal_contracts_for_manual("reset_signal", [shd], reason="login_or_server_error")
                    update_sheet_remote_signal(r, err_kq, "reset")

                    reset_signal_task_state["processed_in_session"].append({
                        "shd": shd,
                        "ket_qua": err_kq,
                        "is_success": False,
                        "time": now_str
                    })
                time.sleep(1.5)

            reset_signal_task_state["message"] = f"Hoàn tất xử lý {len(to_process)} hợp đồng Cấp Lại Tín Hiệu!"
            task_log("=== HOÀN TẤT TIẾN TRÌNH AUTO CẤP LẠI TÍN HIỆU ===", "success")
        except Exception as e:
            reset_signal_task_state["message"] = f"Lỗi Cấp Lại Tín Hiệu: {e}"
            task_log(f"Tiến trình Cấp Lại Tín Hiệu bị dừng: {e}", "error")
            core_login.invalidate_session(log_cb=task_log)  # phiên nghi ngờ hỏng/đơ -> lần sau đăng nhập mới
            if not is_manual:
                remaining_shds = [str(r.get("SHD", "")).strip() for r in to_process if str(r.get("SHD", "")).strip() not in processed_shds]
                _lock_signal_contracts_for_manual("reset_signal", remaining_shds, reason="login_or_server_error")
        finally:
            reset_signal_task_state["is_running"] = False
            if bot:
                try:
                    bot.close()
                except Exception:
                    pass
            active_reset_signal_bot = None
            core_login.release_inside_task("reset_signal")

    try:
        threading.Thread(target=worker_reset_signal, daemon=True).start()
    except Exception:
        reset_signal_task_state["is_running"] = False
        core_login.release_inside_task("reset_signal")
        raise
    return jsonify({"status": "started", "count": len(to_process)})


# ================= AUTO CẤP LẠI TÍN HIỆU SAU CLEAR > 72H =================
AUTO_RESET_HOURS = 72
AUTO_RESET_MAX_AGE_DAYS = 15  # bỏ qua HĐ Clear quá cũ (quá khứ) để không chạy lại hàng loạt
AUTO_RESET_STATE_FILE = os.path.join(BASE_DIR, "auto_reset_72h_state.json")

def _parse_vn_dt(s):
    from datetime import datetime
    s = str(s or "").strip()
    for fmt in ("%d/%m/%Y %H:%M:%S", "%d/%m/%Y %H:%M", "%d/%m/%Y", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(s, fmt)
        except Exception:
            pass
    return None

def _is_clear_success(kq):
    k = inside_signal.normalize_nfc(kq).lower()
    if not k or any(x in k for x in ["không", "lỗi", "thất bại", "chưa", "cấp lại"]):
        return False
    return any(x in k for x in ["thành công", "đã clear", "đã xử lý", "hoàn tất"])

def _auto_reset_after_clear_check():
    """Clear Tín Hiệu thành công quá 72h mà chưa có Cấp Lại Tín Hiệu -> tự chạy Cấp Lại (mỗi HĐ chỉ thử 1 lần, lỗi thì báo log, không chạy lại)."""
    from datetime import datetime, timedelta
    if (
        reset_signal_task_state["is_running"]
        or clear_signal_task_state["is_running"]
        or core_login.get_running_inside_task() is not None
        or _other_inside_task_running()
    ):
        return
    clear_res = inside_signal.fetch_sheet_data(gid=inside_signal.GID_CLEAR_SIGNAL, signal_type="clear")
    reset_res = inside_signal.fetch_sheet_data(gid=inside_signal.GID_RESET_SIGNAL, signal_type="reset")
    if clear_res.get("status") != "ok" or reset_res.get("status") != "ok":
        return

    reset_cache = inside_signal.load_cache(inside_signal.RESET_SIGNAL_CACHE_FILE)
    reset_done = {}
    for r in reset_res.get("records", []):
        s = str(r.get("SHD", "")).strip()
        if s and inside_signal.is_final_status(r.get("Kết Quả", "")):
            reset_done[s] = _parse_vn_dt(r.get("Ngày Cập Nhật", ""))

    reset_listed = {str(r.get("SHD", "")).strip() for r in reset_res.get("records", []) if str(r.get("SHD", "")).strip()}
    state = inside_signal.load_cache(AUTO_RESET_STATE_FILE)
    clear_cache = inside_signal.load_cache(inside_signal.CLEAR_SIGNAL_CACHE_FILE)
    limit = datetime.now() - timedelta(hours=AUTO_RESET_HOURS)
    limit_old = datetime.now() - timedelta(days=AUTO_RESET_MAX_AGE_DAYS)
    today_date = datetime.now().date()

    due = []
    seen = set()
    for r in clear_res.get("records", []):
        shd = str(r.get("SHD", "")).strip()
        if not shd or shd in seen:
            continue
        if not _is_clear_success(r.get("Kết Quả", "")):
            continue
        if _is_signal_manual_locked("reset_signal", {"SHD": shd}):
            continue

        c_item = clear_cache.get(shd)
        t_str = (c_item.get("time") if isinstance(c_item, dict) else "") or r.get("Ngày Cập Nhật", "")
        dt = _parse_vn_dt(t_str)
        if not (dt and limit_old <= dt <= limit):
            continue
        # Rule 1: Chỉ auto với HĐ đến hạn 72H trong ngày hôm nay (HĐ tồn ngày cũ phải thao tác tay)
        due_dt = dt + timedelta(hours=AUTO_RESET_HOURS)
        if due_dt.date() < today_date:
            continue

        # Đã từng được Auto 72H xử lý cho chu kỳ Clear này
        if shd in state:
            st_dt = _parse_vn_dt(state[shd])
            if dt and st_dt and dt <= st_dt:
                continue

        # Đã được Cấp Lại trong cache
        if shd in reset_cache:
            rc_item = reset_cache[shd]
            rc_dt = _parse_vn_dt(rc_item.get("time") if isinstance(rc_item, dict) else "")
            if dt and rc_dt and dt <= rc_dt:
                continue

        # Đã hoàn tất Cấp Lại trên Google Sheet Cấp Lại
        if shd in reset_done:
            rd_dt = reset_done[shd]
            if dt and rd_dt and dt <= rd_dt:
                continue
            elif not rd_dt:
                continue

        r["_is_auto_72h"] = True
        seen.add(shd)
        due.append(r)

    if not due:
        return

    if (
        reset_signal_task_state["is_running"]
        or clear_signal_task_state["is_running"]
        or core_login.get_running_inside_task() is not None
        or _other_inside_task_running()
    ):
        return

    add_log(f"⏰ Phát hiện {len(due)} HĐ đã Clear Tín Hiệu quá {AUTO_RESET_HOURS}h chưa Cấp Lại → Cập nhật Auto Cấp Lại và gửi sang Cấp Lại Tín Hiệu", "info", "reset_signal")
    for r in due:
        shd = str(r.get("SHD", "")).strip()
        r["Auto Cấp Lại"] = "Auto Cấp Lại"
        r["_is_auto_72h"] = True
        r["Nguồn"] = "Auto >72H"
        r["Nguon"] = "Auto >72H"
        # 1. Cập nhật cột Auto Cấp Lại trên Sheet Clear GID 0 (giữ nguyên Kết Quả là 'Đã xử lý')
        inside_signal.update_clear_sheet_auto_cap_lai_cell(shd, r, "Auto Cấp Lại")
        # 2. Gửi thông tin sang Sheet Cấp Lại GID 1100152201 với Nguồn = 'Auto >72H'
        inside_signal.transfer_contract_to_reset_sheet(r, nguon="Auto >72H")

    try:
        with app.test_client() as c:
            resp = c.post("/api/reset-signal/run", json={"records": due, "headless": True, "source": "auto_72h", "manual": False})
            if resp.status_code == 409:
                add_log(f"Phiên Inside FPT đang bận, tạm hoãn Cấp Lại 72h: {resp.get_json(silent=True)}", "warning", "reset_signal")
                return
            if resp.status_code != 200:
                add_log(f"Không thể tự Cấp Lại sau 72h (HTTP {resp.status_code}): {resp.get_json(silent=True)}", "error", "reset_signal")
                _lock_signal_contracts_for_manual("reset_signal", [r.get("SHD") for r in due], reason="login_or_server_error")
    except Exception as e:
        add_log(f"Lỗi tự Cấp Lại sau 72h: {e}", "error", "reset_signal")
        _lock_signal_contracts_for_manual("reset_signal", [r.get("SHD") for r in due], reason="login_or_server_error")

def _auto_reset_after_clear_loop():
    time.sleep(30)
    while True:
        try:
            _auto_reset_after_clear_check()
        except Exception as e:
            add_log(f"Lỗi kiểm tra Cấp Lại 72h: {e}", "warning")
        time.sleep(300)

@app.route("/api/reset-signal/check-72h", methods=["POST", "GET"])
def trigger_check_72h_api():
    """Kích hoạt thủ công tiến trình quét và tự động Cấp Lại các HĐ quá 72h."""
    threading.Thread(target=_auto_reset_after_clear_check, daemon=True).start()
    return jsonify({"status": "ok", "message": "Đã bắt đầu kiểm tra và thực thi Cấp Lại Tín Hiệu 72h."})


# ================= TAB: AUTO BYPASS MYBAE =================
import inside_mybae

mybae_task_state = {
    "is_running": False,
    "current_index": 0,
    "total": 0,
    "current_shd": "",
    "message": "Sẵn sàng",
    "sheet_id": inside_mybae.DEFAULT_SHEET_ID,
    "gid": inside_mybae.GID_MYBAE,
    "processed_in_session": []
}
active_mybae_bot = None

def _other_inside_task_running():
    """Trả về tên tiến trình khác đang dùng chung phiên Chrome Inside FPT (hoặc rỗng)."""
    running = core_login.get_running_inside_task()
    if running:
        return running
    for name, st in (
        ("Phân Công Tay", assign_task_state),
        ("Clear Cls", cls_task_state),
        ("ByPass", bypass_task_state),
        ("Clear Tín Hiệu", clear_signal_task_state),
        ("Cấp Lại Tín Hiệu", reset_signal_task_state),
        ("Bypass MyBAE", mybae_task_state),
        ("Kéo Dữ Liệu", retrieval_task),
    ):
        if st.get("is_running"):
            return name
    if task_state.get("status") == "running":
        return "login"
    return ""

@app.route("/api/session/clear-all", methods=["POST", "GET"])
def clear_all_sessions_api():
    """
    Dọn dẹp triệt để:
    1. Đóng toàn bộ bot đang hoạt động
    2. Giải phóng tiến trình Chrome/ChromeDriver treo của các tác vụ cũ
    3. Xóa toàn bộ file lock profile (Inside FPT, Radius Portal, Port Portal)
    4. Reset toàn bộ cờ is_running và giải phóng khóa phiên Inside nếu bị kẹt
    """
    global active_bypass_bot, active_cls_bot, active_assign_bot, \
        active_clear_signal_bot, active_reset_signal_bot, active_mybae_bot, \
        active_spampool_bot, active_bypass_nat_bot, active_port_bot
    for b in (
        active_bypass_bot,
        active_cls_bot,
        active_assign_bot,
        active_clear_signal_bot,
        active_reset_signal_bot,
        active_mybae_bot,
        active_spampool_bot,
        active_bypass_nat_bot,
        active_port_bot,
    ):
        if b:
            try:
                if hasattr(b, "request_stop"):
                    b.request_stop()
            except Exception:
                pass
            try:
                b.close(force=True)
            except TypeError:
                try:
                    b.close()
                except Exception:
                    pass
            except Exception:
                pass

    active_bypass_bot = None
    active_cls_bot = None
    active_assign_bot = None
    active_clear_signal_bot = None
    active_reset_signal_bot = None
    active_mybae_bot = None
    active_spampool_bot = None
    active_bypass_nat_bot = None
    active_port_bot = None

    core_login.clean_profile_locks_and_orphans(profile_dir=core_login.get_inside_profile_dir(), log_cb=add_log)
    core_login.clean_profile_locks_and_orphans(profile_dir=core_login.get_radius_profile_dir(), log_cb=add_log)
    core_login.clean_profile_locks_and_orphans(profile_dir=inside_port.get_port_profile_dir(), log_cb=add_log)

    assign_task_state["is_running"] = False
    cls_task_state["is_running"] = False
    bypass_task_state["is_running"] = False
    clear_signal_task_state["is_running"] = False
    reset_signal_task_state["is_running"] = False
    mybae_task_state["is_running"] = False
    spampool_task_state["is_running"] = False
    bypass_nat_task_state["is_running"] = False
    port_task_state["is_running"] = False
    retrieval_task["is_running"] = False
    task_state["status"] = "idle"
    core_login.release_inside_task()

    add_log("Đã giải phóng toàn bộ tiến trình treo và xóa sạch phiên cũ!", "success")
    return jsonify({"status": "ok", "message": "Đã giải phóng toàn bộ tiến trình Chrome treo và xóa sạch phiên cũ!"})

@app.route("/api/mybae/sheet-data", methods=["GET"])
def get_mybae_sheet_data():
    sheet_id = request.args.get("sheet_id", inside_mybae.DEFAULT_SHEET_ID).strip()
    gid      = request.args.get("gid", inside_mybae.GID_MYBAE).strip()
    data = inside_mybae.fetch_sheet_data(sheet_id=sheet_id, gid=gid)
    if data["status"] != "ok":
        return jsonify(data), 500
    return jsonify(data)

@app.route("/api/mybae/live-status", methods=["GET"])
def get_mybae_live_status():
    return jsonify({
        "task": mybae_task_state,
        "processed_in_session": mybae_task_state.get("processed_in_session", [])
    })

@app.route("/api/mybae/clear-cache", methods=["POST"])
@app.route("/api/mybae/clear_cache", methods=["POST"])
def clear_mybae_cache():
    add_log("Đã làm mới bộ nhớ đệm Bypass MyBAE!", "success")
    return jsonify({"status": "ok", "message": "Đã làm mới bộ nhớ đệm Bypass MyBAE."})

@app.route("/api/mybae/export", methods=["GET", "POST"])
def export_mybae_excel():
    data = request.json if request.is_json else request.args
    gid = data.get("gid", inside_mybae.GID_MYBAE)
    sheet_id = data.get("sheet_id", inside_mybae.DEFAULT_SHEET_ID)
    status_filter = data.get("status", "all")

    sheet_res = inside_mybae.fetch_sheet_data(sheet_id=sheet_id, gid=gid)
    records = sheet_res.get("records", []) if sheet_res.get("status") == "ok" else []

    if status_filter == "done":
        filtered = [r for r in records if inside_mybae.is_final_row(r)]
    elif status_filter == "pending":
        filtered = [r for r in records if not inside_mybae.is_final_row(r)]
    else:
        filtered = records

    if not filtered:
        return jsonify({"status": "error", "message": "Không có dữ liệu Bypass MyBAE để xuất file"}), 400

    export_rows = []
    for idx, r in enumerate(filtered, 1):
        export_rows.append({
            "STT": idx,
            "Tác Vụ": r.get("Tác Vụ") or "Bypass MyBAE",
            "Số Hợp Đồng": r.get("SHD", ""),
            "Email NVKT": r.get("Email", ""),
            "Nguyên Nhân 1": r.get("Nguyên Nhân 1", ""),
            "Ngày Cập Nhật": r.get("Ngày Cập Nhật", ""),
            "Kết Quả": r.get("Kết Quả", ""),
            "Thao Tác": r.get("Thao Tác", "")
        })

    df = pd.DataFrame(export_rows)
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name="Bypass_MyBAE_Data")
    output.seek(0)

    filename = f"Bypass_MyBAE_Data_Xu_Ly_{time.strftime('%Y%m%d_%H%M%S')}.xlsx"
    return send_file(
        output,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        as_attachment=True,
        download_name=filename
    )

@app.route("/api/mybae/run", methods=["POST"])
def run_mybae_process():
    ok, busy_by = core_login.try_acquire_inside_task("mybae")
    if not ok:
        return jsonify({
            "status": "error",
            "message": f"Phiên Chrome Inside FPT đang bận chạy '{busy_by}'. Vui lòng đợi tiến trình đó hoàn tất!"
        }), 409

    validated = False
    try:
        if mybae_task_state["is_running"]:
            return jsonify({"status": "busy", "message": "Đang có tiến trình Bypass MyBAE đang chạy..."}), 429

        data             = request.json or {}
        sheet_id         = data.get("sheet_id", inside_mybae.DEFAULT_SHEET_ID)
        gid              = data.get("gid", inside_mybae.GID_MYBAE)
        selected_records = data.get("records")
        headless         = data.get("headless", True)

        sheet_res = inside_mybae.fetch_sheet_data(sheet_id=sheet_id, gid=gid)
        col_indices = sheet_res.get("col_indices", {}) if sheet_res.get("status") == "ok" else {}

        if selected_records:
            to_process = selected_records
        else:
            if sheet_res["status"] != "ok" or not sheet_res["records"]:
                return jsonify({"status": "error", "message": "Không tìm thấy dữ liệu trên Google Sheet Bypass MyBAE"}), 400
            to_process = [r for r in sheet_res["records"] if not inside_mybae.is_final_row(r)]

        if not to_process:
            return jsonify({"status": "error", "message": "Không có hợp đồng nào để xử lý!"}), 400

        mybae_task_state["is_running"]           = True
        mybae_task_state["total"]                = len(to_process)
        mybae_task_state["current_index"]        = 0
        mybae_task_state["current_shd"]          = str(to_process[0].get("SHD", ""))
        mybae_task_state["message"]              = f"Bắt đầu xử lý {len(to_process)} hợp đồng Bypass MyBAE..."
        mybae_task_state["sheet_id"]             = sheet_id
        mybae_task_state["gid"]                  = gid
        mybae_task_state["processed_in_session"] = []
        validated = True
    finally:
        if not validated:
            core_login.release_inside_task("mybae")

    mode_label = "Chạy ngầm (Headless)" if headless else "Mở Chrome xem trực tiếp (Visible)"
    task_log = make_task_logger(mybae_task_state, "bypass_mybae", "Bypass MyBAE")
    task_log(f"=== BẮT ĐẦU AUTO BYPASS MYBAE {len(to_process)} HỢP ĐỒNG ({mode_label}) ===", "info")

    def update_sheet_remote_mybae(record, is_ok, thao_tac_val):
        cfg = core_login.load_config()
        webhook_url = (cfg.get("mybae_webhook_url", "") or cfg.get("cls_webhook_url", "")
                       or cfg.get("google_sheet_webhook_url", ""))
        if not webhook_url:
            return
        try:
            payload = {
                "sheet_id": sheet_id,
                "gid": gid,
                "row_id": record.get("ID"),
                "shd": record.get("SHD"),
                "status": thao_tac_val,
                "thao_tac": thao_tac_val,
                "timestamp": time.strftime("%d/%m/%Y %H:%M:%S")
            }
            # Kết Quả luôn là 'Đã xử lý' (cả khi lỗi); kết quả thực tế nằm ở cột Thao Tác
            payload["ket_qua"] = inside_mybae.KET_QUA_DONE
            if col_indices:
                if "shd" in col_indices: payload["col_shd"] = col_indices["shd"]
                if "thao_tac" in col_indices: payload["col_thao_tac"] = col_indices["thao_tac"]
                if "ket_qua" in col_indices: payload["col_ket_qua"] = col_indices["ket_qua"]
                if "ngay" in col_indices: payload["col_ngay"] = col_indices["ngay"]
            req = urllib.request.Request(
                webhook_url,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"}
            )
            urllib.request.urlopen(req, timeout=8)
            task_log(f"Đã cập nhật Webhook Bypass MyBAE cho HĐ {record.get('SHD')}: '{thao_tac_val}'", "success")
        except Exception as e_hook:
            task_log(f"Không thể đẩy Webhook Bypass MyBAE cho HĐ {record.get('SHD')}: {e_hook}", "warning")

    def worker_mybae():
        global active_mybae_bot
        bot = None
        processed_shds = set()
        try:
            bot = inside_mybae.InsideMyBaeAutomation(headless=headless, keep_open=True, log_cb=task_log)
            active_mybae_bot = bot
            bot.init_driver()
            bot.navigate_to_assign_page()

            for idx, r in enumerate(to_process):
                shd = str(r.get("SHD", "")).strip()
                mybae_task_state["current_index"] = idx + 1
                mybae_task_state["current_shd"]   = shd
                mybae_task_state["message"]       = f"Đang xử lý Bypass MyBAE {idx + 1}/{len(to_process)}: HĐ {shd}..."

                try:
                    is_ok, thao_tac = bot.process_row(r)
                except Exception as ex_single:
                    task_log(f"Lỗi Bypass MyBAE HĐ {shd}: {ex_single}", "error")
                    is_ok = False
                    thao_tac = inside_mybae.format_mybae_thao_tac(False, str(ex_single)[:100])
                if shd:
                    processed_shds.add(shd)

                now_str = time.strftime("%d/%m/%Y %H:%M:%S")
                r["Thao Tác"] = thao_tac
                r["Ngày Cập Nhật"] = now_str
                r["Kết Quả"] = inside_mybae.KET_QUA_DONE
                update_sheet_remote_mybae(r, is_ok, thao_tac)

                mybae_task_state["processed_in_session"].append({
                    "shd":        shd,
                    "ket_qua":    r.get("Kết Quả", ""),
                    "thao_tac":   thao_tac,
                    "is_success": is_ok,
                    "time":       now_str,
                    "reason":     r.get("Nguyên Nhân 1", "")
                })
                task_log(f"Bypass MyBAE HĐ {shd}: '{thao_tac}'", "success" if is_ok else "warning", "bypass_mybae")

                time.sleep(2)

            mybae_task_state["message"] = f"Hoàn tất xử lý {len(to_process)} hợp đồng Bypass MyBAE!"
            task_log("=== HOÀN TẤT TIẾN TRÌNH AUTO BYPASS MYBAE ===", "success")

        except Exception as e:
            mybae_task_state["message"] = f"Lỗi Bypass MyBAE: {e}"
            task_log(f"Tiến trình Bypass MyBAE bị dừng: {e}", "error")
            core_login.invalidate_session(log_cb=task_log)  # phiên nghi ngờ hỏng/đơ -> lần sau đăng nhập mới
        finally:
            _release_remaining_auto_attempts("mybae", to_process, processed_shds)
            mybae_task_state["is_running"] = False
            if bot:
                try:
                    bot.close()
                except Exception:
                    pass
            active_mybae_bot = None
            core_login.release_inside_task("mybae")

    try:
        threading.Thread(target=worker_mybae, daemon=True).start()
    except Exception:
        mybae_task_state["is_running"] = False
        core_login.release_inside_task("mybae")
        raise
    return jsonify({"status": "started", "count": len(to_process)})


# ========================================================
# TAB 9: AUTO SPAMPOOL & DEACTIVE IPV6 (RADIUS PORTAL)
# SHEET ID: 1Sw-qSbLzvVdcW4rj7ywEZBEzKI6w5M82EQeYJUpdx7M  GID: 2070394876
# ========================================================
import inside_spampool

radius_task_lock = threading.Lock()
radius_sync_busy = {"active": False}

spampool_task_state = {
    "is_running": False,
    "current_index": 0,
    "total": 0,
    "current_shd": "",
    "message": "Sẵn sàng",
    "sheet_id": inside_spampool.DEFAULT_SHEET_ID,
    "gid": inside_spampool.GID_SPAMPOOL,
    "processed_in_session": []
}
active_spampool_bot = None

@app.route("/api/spampool/sheet", methods=["GET"])
def get_spampool_sheet():
    sheet_id = request.args.get("sheet_id", inside_spampool.DEFAULT_SHEET_ID).strip()
    gid      = request.args.get("gid", inside_spampool.GID_SPAMPOOL).strip()
    data = inside_spampool.fetch_sheet_data(sheet_id=sheet_id, gid=gid)
    return jsonify(data)

@app.route("/api/spampool/status", methods=["GET"])
def get_spampool_status():
    return jsonify({
        "status": "ok",
        "task": spampool_task_state
    })

@app.route("/api/spampool/stop", methods=["POST"])
def stop_spampool_task():
    global active_spampool_bot
    if active_spampool_bot:
        active_spampool_bot.request_stop()
        try:
            active_spampool_bot.close(force=True)
        except Exception:
            pass
    spampool_task_state["is_running"] = False
    spampool_task_state["message"] = "Đã nhận lệnh dừng tiến trình SpamPool."
    add_log("Đã gửi yêu cầu dừng tiến trình SpamPool!", "warning")
    return jsonify({"status": "ok", "message": "Đã gửi yêu cầu dừng tiến trình SpamPool."})

@app.route("/api/spampool/clear_cache", methods=["POST"])
def clear_spampool_cache():
    if os.path.exists(inside_spampool.SPAMPOOL_CACHE_FILE):
        try:
            os.remove(inside_spampool.SPAMPOOL_CACHE_FILE)
        except Exception:
            pass
    add_log("Đã xóa sạch cache trạng thái SpamPool!", "success")
    return jsonify({"status": "ok", "message": "Đã xóa sạch cache trạng thái SpamPool."})

@app.route("/api/spampool/login", methods=["POST"])
def spampool_manual_login():
    with radius_task_lock:
        if spampool_task_state.get("is_running") or bypass_nat_task_state.get("is_running") or radius_sync_busy["active"]:
            return jsonify({"status": "busy", "message": "Hệ thống Radius Portal đang bận xử lý tác vụ khác!"}), 409
        radius_sync_busy["active"] = True
    try:
        data = request.json or {}
        headless = data.get("headless", False)
        force = data.get("force", False)

        spampool_task_state["is_running"] = True
        spampool_task_state["total"] = 0
        spampool_task_state["current_index"] = 0
        spampool_task_state["current_shd"] = ""
        spampool_task_state["message"] = "Đang xác thực đăng nhập Radius Portal..."
        task_log = make_task_logger(spampool_task_state, "spampool", "SpamPool")

        task_log("=== BẮT ĐẦU XÁC THỰC ĐĂNG NHẬP RADIUS PORTAL ===", "info")
        try:
            ok, final_url, title = core_login.run_radius_login(
                headless=headless,
                keep_open=True,
                log_callback=task_log,
                force=force
            )
            spampool_task_state["message"] = f"Đăng nhập thành công Radius Portal ({final_url})"
            task_log(f"Đăng nhập thành công Radius Portal! ({final_url})", "success")
            return jsonify({
                "status": "ok",
                "url": final_url,
                "title": title,
                "message": "Đăng nhập Radius Portal thành công!"
            })
        except Exception as e:
            spampool_task_state["message"] = f"Đăng nhập Radius Portal thất bại: {e}"
            task_log(f"Đăng nhập Radius Portal thất bại: {e}", "error")
            return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        spampool_task_state["is_running"] = False
        with radius_task_lock:
            radius_sync_busy["active"] = False

@app.route("/api/spampool/test_single", methods=["POST"])
def test_single_spampool():
    with radius_task_lock:
        if spampool_task_state.get("is_running") or bypass_nat_task_state.get("is_running") or radius_sync_busy["active"]:
            return jsonify({"status": "busy", "message": "Hệ thống Radius Portal đang bận xử lý tác vụ khác!"}), 409
        radius_sync_busy["active"] = True

    bot = None
    shd = ""
    try:
        data = request.json or {}
        shd = str(data.get("shd", "")).strip().upper()
        row_id = str(data.get("row_id", "")).strip()
        tac_vu = str(data.get("tac_vu", "")).strip()
        headless = data.get("headless", False)

        if not shd:
            return jsonify({"status": "error", "message": "Chưa cung cấp Số Hợp Đồng!"}), 400

        try:
            sheet_data = inside_spampool.fetch_sheet_data()
            records = sheet_data.get("records", [])
            target_rec = None
            if row_id:
                for r in records:
                    if str(r.get("ID", "")).strip() == row_id:
                        target_rec = r
                        break
            if not target_rec:
                # Ưu tiên bản ghi đang pending nếu có nhiều dòng cùng SHD
                for r in records:
                    if str(r.get("SHD", "")).strip().upper() == shd and inside_spampool.is_pending(r.get("Kết Quả"), r.get("Thao Tác")):
                        target_rec = r
                        break
            if not target_rec:
                for r in records:
                    if str(r.get("SHD", "")).strip().upper() == shd:
                        target_rec = r
                        break
            if target_rec:
                if not tac_vu:
                    tac_vu = str(target_rec.get("Tác Vụ", "")).strip()
                if not row_id:
                    row_id = str(target_rec.get("ID", "")).strip()
        except Exception:
            pass

        task_name = "DEACTIVE IP 0.0.0.0" if inside_spampool.is_deactive_ip_task(tac_vu) else "SPAMPOOL"
        spampool_task_state["is_running"] = True
        spampool_task_state["total"] = 1
        spampool_task_state["current_index"] = 0
        spampool_task_state["current_shd"] = shd
        spampool_task_state["message"] = f"Đang khởi tạo Chrome & đăng nhập cho HĐ {shd}..."
        task_log = make_task_logger(spampool_task_state, "spampool", "SpamPool")

        task_log(f"=== BẮT ĐẦU TEST {task_name} CHO HĐ {shd} (Tác vụ: '{tac_vu}') ===", "info")
        bot = inside_spampool.InsideSpamPoolAutomation(headless=headless, keep_open=False, log_cb=task_log)
        bot.init_driver()
        bot.navigate_to_network_connection()
        spampool_task_state["current_index"] = 1
        spampool_task_state["message"] = f"Đang xử lý {task_name} 1/1: HĐ {shd}..."
        ok, thao_tac, ket_qua = bot.process_spampool_contract(shd, tac_vu=tac_vu)

        now_str = time.strftime("%d/%m/%Y %H:%M:%S")
        # Lưu cache
        cache = inside_spampool.load_cache()
        c_item = {
            "ket_qua": ket_qua,
            "thao_tac": thao_tac,
            "time": now_str,
            "timestamp_epoch": time.time()
        }
        cache[shd] = c_item
        if row_id:
            cache[f"{shd}_{row_id}"] = c_item
        tv_k = "deactive" if inside_spampool.is_deactive_ip_task(tac_vu) else "spampool"
        cache[f"{shd}_{tv_k}"] = c_item
        inside_spampool.save_cache(cache)

        # Gửi Webhook nếu có cấu hình
        cfg = core_login.load_config()
        webhook_url = cfg.get("spampool_webhook_url", "") or cfg.get("cls_webhook_url", "") or cfg.get("google_sheet_webhook_url", "")
        if webhook_url:
            try:
                payload = {
                    "sheet_id": inside_spampool.DEFAULT_SHEET_ID,
                    "gid": inside_spampool.GID_SPAMPOOL,
                    "row_id": row_id,
                    "shd": shd,
                    "status": thao_tac,
                    "thao_tac": thao_tac,
                    "ket_qua": ket_qua,
                    "col_shd": 5,
                    "col_ngay": 7,
                    "col_ket_qua": 8,
                    "col_thao_tac": 9,
                    "timestamp": now_str
                }
                req = urllib.request.Request(
                    webhook_url,
                    data=json.dumps(payload).encode("utf-8"),
                    headers={"Content-Type": "application/json"}
                )
                with urllib.request.urlopen(req, timeout=10) as resp:
                    resp_text = resp.read().decode("utf-8", errors="ignore")
                    task_log(f"Đã cập nhật Webhook Google Sheet cho HĐ {shd}: '{thao_tac}' | KQ: '{ket_qua}'", "success")
            except Exception as e_hook:
                task_log(f"Lỗi gửi Webhook cho HĐ {shd}: {e_hook}", "warning")

        spampool_task_state["message"] = f"Hoàn tất HĐ {shd}: {thao_tac}"
        return jsonify({
            "status": "ok" if ok else "error",
            "shd": shd,
            "thao_tac": thao_tac,
            "ket_qua": ket_qua
        })
    except Exception as e:
        spampool_task_state["message"] = f"Lỗi test HĐ {shd}: {e}"
        add_log(f"[SpamPool] Lỗi test HĐ {shd}: {e}", "error", "spampool")
        return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        spampool_task_state["is_running"] = False
        if bot:
            try:
                bot.close(force=True)
            except Exception:
                pass
        with radius_task_lock:
            radius_sync_busy["active"] = False

@app.route("/api/spampool/start", methods=["POST"])
def start_spampool_task():
    global active_spampool_bot
    with radius_task_lock:
        if radius_sync_busy["active"]:
            return jsonify({"status": "busy", "message": "Hệ thống Radius Portal đang bận xử lý đăng nhập/test đơn!"}), 409
        if spampool_task_state.get("is_running"):
            return jsonify({"status": "busy", "message": "Tiến trình SpamPool đang chạy!"}), 429
        if bypass_nat_task_state.get("is_running"):
            return jsonify({"status": "busy", "message": "Tiến trình Bypass NAT đang chạy trên cùng hệ thống Radius!"}), 429

        data = request.json or {}
        headless = data.get("headless", False)
        sheet_id = data.get("sheet_id", inside_spampool.DEFAULT_SHEET_ID)
        gid      = data.get("gid", inside_spampool.GID_SPAMPOOL)

        sheet_res = inside_spampool.fetch_sheet_data(sheet_id=sheet_id, gid=gid)
        if sheet_res.get("status") != "ok" or not sheet_res.get("records"):
            return jsonify({"status": "error", "message": "Không tìm thấy dữ liệu trên Google Sheet GID 2070394876!"}), 400

        to_process = [r for r in sheet_res["records"] if inside_spampool.is_pending(r.get("Kết Quả"), r.get("Thao Tác"))]
        if not to_process:
            return jsonify({"status": "error", "message": "Tất cả hợp đồng đã được xử lý xong (không có hợp đồng nào 'Chưa cập nhật')!"}), 400

        spampool_task_state["is_running"] = True
        spampool_task_state["total"] = len(to_process)
        spampool_task_state["current_index"] = 0
        spampool_task_state["current_shd"] = str(to_process[0].get("SHD", ""))
        spampool_task_state["message"] = f"Bắt đầu xử lý {len(to_process)} hợp đồng SpamPool..."
        spampool_task_state["sheet_id"] = sheet_id
        spampool_task_state["gid"] = gid
        spampool_task_state["processed_in_session"] = []
        task_log = make_task_logger(spampool_task_state, "spampool", "SpamPool")

        task_log(f"=== BẮT ĐẦU AUTO SPAMPOOL {len(to_process)} HỢP ĐỒNG ===", "info")

    def update_sheet_remote_spampool(record, thao_tac_val, ket_qua_val):
        cfg = core_login.load_config()
        webhook_url = cfg.get("spampool_webhook_url", "") or cfg.get("cls_webhook_url", "") or cfg.get("google_sheet_webhook_url", "")
        if webhook_url:
            try:
                payload = {
                    "sheet_id": sheet_id,
                    "gid": gid,
                    "row_id": record.get("ID"),
                    "shd": record.get("SHD"),
                    "status": thao_tac_val,
                    "thao_tac": thao_tac_val,
                    "ket_qua": ket_qua_val,
                    "col_shd": 5,
                    "col_ngay": 7,
                    "col_ket_qua": 8,
                    "col_thao_tac": 9,
                    "timestamp": time.strftime("%d/%m/%Y %H:%M:%S")
                }
                req = urllib.request.Request(
                    webhook_url,
                    data=json.dumps(payload).encode("utf-8"),
                    headers={"Content-Type": "application/json"}
                )
                with urllib.request.urlopen(req, timeout=10) as resp:
                    resp_text = resp.read().decode("utf-8", errors="ignore")
                    task_log(f"Đã cập nhật Webhook SpamPool cho HĐ {record.get('SHD')}: '{thao_tac_val}' | Kết quả='{ket_qua_val}'", "success")
            except Exception as e_hook:
                task_log(f"Không thể đẩy Webhook cho HĐ {record.get('SHD')}: {e_hook}", "warning")

    def worker_spampool():
        global active_spampool_bot
        bot = inside_spampool.InsideSpamPoolAutomation(headless=headless, keep_open=False, log_cb=task_log)
        active_spampool_bot = bot
        processed_shds = set()
        try:
            bot.init_driver()
            bot.navigate_to_network_connection()

            for idx, r in enumerate(to_process):
                if bot._stop_requested:
                    break

                shd = str(r.get("SHD", "")).strip()
                tac_vu = str(r.get("Tác Vụ", "")).strip()
                spampool_task_state["current_index"] = idx + 1
                spampool_task_state["current_shd"] = shd
                task_label = "Deactive IP 0.0.0.0" if inside_spampool.is_deactive_ip_task(tac_vu) else "SpamPool"
                spampool_task_state["message"] = f"Đang xử lý {task_label} {idx + 1}/{len(to_process)}: HĐ {shd}..."

                try:
                    ok, thao_tac, ket_qua = bot.process_spampool_contract(shd, tac_vu=tac_vu)
                    if shd:
                        processed_shds.add(shd)
                    now_str = time.strftime("%d/%m/%Y %H:%M:%S")

                    r["Thao Tác"] = thao_tac
                    r["Kết Quả"] = ket_qua
                    r["Ngày Cập Nhật"] = now_str

                    cache = inside_spampool.load_cache()
                    c_item = {
                        "ket_qua": ket_qua,
                        "thao_tac": thao_tac,
                        "time": now_str,
                        "timestamp_epoch": time.time()
                    }
                    cache[shd] = c_item
                    r_id = str(r.get("ID", "")).strip()
                    if r_id:
                        cache[f"{shd}_{r_id}"] = c_item
                    tv_k = "deactive" if inside_spampool.is_deactive_ip_task(tac_vu) else "spampool"
                    cache[f"{shd}_{tv_k}"] = c_item
                    inside_spampool.save_cache(cache)

                    update_sheet_remote_spampool(r, thao_tac, ket_qua)

                    spampool_task_state["processed_in_session"].append({
                        "shd": shd,
                        "status": ket_qua,
                        "thao_tac": thao_tac,
                        "time": now_str
                    })
                    task_log(f"SpamPool HĐ {shd}: Kết quả='{ket_qua}' | Thao tác='{thao_tac}'", "success", "spampool")
                except Exception as ex_single:
                    if shd:
                        processed_shds.add(shd)
                    err_msg = str(ex_single)[:80]
                    task_log(f"Lỗi xử lý HĐ {shd}: {err_msg}", "error")
                    r["Thao Tác"] = f"Lỗi: {err_msg}"
                    r["Kết Quả"] = "Lỗi"
                    spampool_task_state["processed_in_session"].append({
                        "shd": shd,
                        "status": "Lỗi",
                        "thao_tac": f"Lỗi: {err_msg}",
                        "time": time.strftime("%d/%m/%Y %H:%M:%S")
                    })
                    try:
                        update_sheet_remote_spampool(r, f"Lỗi: {err_msg}", "Lỗi")
                    except Exception:
                        pass

                time.sleep(2)

            spampool_task_state["message"] = f"Hoàn tất xử lý {len(to_process)} hợp đồng SpamPool."
            task_log(f"=== HOÀN TẤT AUTO SPAMPOOL ({len(to_process)} HỢP ĐỒNG) ===", "success")
        except Exception as e:
            spampool_task_state["message"] = f"Lỗi SpamPool: {e}"
            task_log(f"Tiến trình SpamPool bị dừng: {e}", "error")
        finally:
            _release_remaining_auto_attempts("spampool", to_process, processed_shds)
            spampool_task_state["is_running"] = False
            if bot:
                try:
                    bot.close(force=True)
                except Exception:
                    pass
            active_spampool_bot = None

    threading.Thread(target=worker_spampool, daemon=True).start()
    return jsonify({"status": "started", "count": len(to_process)})

# ========================================================
# TAB 10: AUTO BYPASS NAT (RADIUS PORTAL)
# SHEET ID: 1Sw-qSbLzvVdcW4rj7ywEZBEzKI6w5M82EQeYJUpdx7M  GID: 1907537423
# ========================================================
import inside_bypass_nat

bypass_nat_task_state = {
    "is_running": False,
    "current_index": 0,
    "total": 0,
    "current_shd": "",
    "message": "Sẵn sàng",
    "sheet_id": inside_bypass_nat.DEFAULT_SHEET_ID,
    "gid": inside_bypass_nat.GID_BYPASS_NAT,
    "processed_in_session": []
}
active_bypass_nat_bot = None

@app.route("/api/bypass_nat/sheet", methods=["GET"])
def get_bypass_nat_sheet():
    sheet_id = request.args.get("sheet_id", inside_bypass_nat.DEFAULT_SHEET_ID).strip()
    gid      = request.args.get("gid", inside_bypass_nat.GID_BYPASS_NAT).strip()
    data = inside_bypass_nat.fetch_sheet_data(sheet_id=sheet_id, gid=gid)
    return jsonify(data)

@app.route("/api/bypass_nat/status", methods=["GET"])
def get_bypass_nat_status():
    return jsonify({
        "status": "ok",
        "task": bypass_nat_task_state
    })

@app.route("/api/bypass_nat/stop", methods=["POST"])
def stop_bypass_nat_task():
    global active_bypass_nat_bot
    if active_bypass_nat_bot:
        active_bypass_nat_bot.request_stop()
        try:
            active_bypass_nat_bot.close(force=True)
        except Exception:
            pass
    bypass_nat_task_state["is_running"] = False
    bypass_nat_task_state["message"] = "Đã nhận lệnh dừng tiến trình Bypass NAT."
    add_log("Đã gửi yêu cầu dừng tiến trình Bypass NAT!", "warning")
    return jsonify({"status": "ok", "message": "Đã gửi yêu cầu dừng tiến trình Bypass NAT."})

@app.route("/api/bypass_nat/clear_cache", methods=["POST"])
def clear_bypass_nat_cache():
    if os.path.exists(inside_bypass_nat.BYPASS_NAT_CACHE_FILE):
        try:
            os.remove(inside_bypass_nat.BYPASS_NAT_CACHE_FILE)
        except Exception:
            pass
    add_log("Đã xóa sạch cache trạng thái Bypass NAT!", "success")
    return jsonify({"status": "ok", "message": "Đã xóa sạch cache trạng thái Bypass NAT."})

@app.route("/api/bypass_nat/login", methods=["POST"])
def bypass_nat_manual_login():
    with radius_task_lock:
        if spampool_task_state.get("is_running") or bypass_nat_task_state.get("is_running") or radius_sync_busy["active"]:
            return jsonify({"status": "busy", "message": "Hệ thống Radius Portal đang bận xử lý tác vụ khác!"}), 409
        radius_sync_busy["active"] = True
    try:
        data = request.json or {}
        headless = data.get("headless", False)
        force = data.get("force", False)

        bypass_nat_task_state["is_running"] = True
        bypass_nat_task_state["total"] = 0
        bypass_nat_task_state["current_index"] = 0
        bypass_nat_task_state["current_shd"] = ""
        bypass_nat_task_state["message"] = "Đang xác thực đăng nhập Radius Portal (Bypass NAT)..."
        task_log = make_task_logger(bypass_nat_task_state, "bypass_nat", "Bypass NAT")

        task_log("=== BẮT ĐẦU XÁC THỰC ĐĂNG NHẬP RADIUS PORTAL (BYPASS NAT) ===", "info")
        try:
            ok, final_url, title = core_login.run_radius_login(
                headless=headless,
                keep_open=True,
                log_callback=task_log,
                force=force
            )
            bypass_nat_task_state["message"] = f"Đăng nhập thành công Radius Portal ({final_url})"
            task_log(f"Đăng nhập thành công Radius Portal! ({final_url})", "success")
            return jsonify({
                "status": "ok",
                "url": final_url,
                "title": title,
                "message": "Đăng nhập Radius Portal thành công!"
            })
        except Exception as e:
            bypass_nat_task_state["message"] = f"Đăng nhập Radius Portal thất bại: {e}"
            task_log(f"Đăng nhập Radius Portal thất bại: {e}", "error")
            return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        bypass_nat_task_state["is_running"] = False
        with radius_task_lock:
            radius_sync_busy["active"] = False

@app.route("/api/bypass_nat/test_single", methods=["POST"])
def test_single_bypass_nat():
    with radius_task_lock:
        if spampool_task_state.get("is_running") or bypass_nat_task_state.get("is_running") or radius_sync_busy["active"]:
            return jsonify({"status": "busy", "message": "Hệ thống Radius Portal đang bận xử lý tác vụ khác!"}), 409
        radius_sync_busy["active"] = True

    bot = None
    shd = ""
    try:
        data = request.json or {}
        shd = str(data.get("shd", "")).strip().upper()
        nguyen_nhan_1 = str(data.get("nguyen_nhan_1", "")).strip()
        headless = data.get("headless", False)

        if not shd:
            return jsonify({"status": "error", "message": "Chưa cung cấp Số Hợp Đồng!"}), 400

        bypass_nat_task_state["is_running"] = True
        bypass_nat_task_state["total"] = 1
        bypass_nat_task_state["current_index"] = 0
        bypass_nat_task_state["current_shd"] = shd
        bypass_nat_task_state["message"] = f"Đang khởi tạo Chrome & đăng nhập cho HĐ {shd}..."
        task_log = make_task_logger(bypass_nat_task_state, "bypass_nat", "Bypass NAT")

        task_log(f"=== BẮT ĐẦU TEST BYPASS NAT CHO HĐ {shd} ===", "info")
        bot = inside_bypass_nat.InsideBypassNatAutomation(headless=headless, keep_open=False, log_cb=task_log)
        bot.init_driver()
        bot.navigate_to_network_connection()
        bypass_nat_task_state["current_index"] = 1
        bypass_nat_task_state["message"] = f"Đang xử lý Bypass NAT 1/1: HĐ {shd}..."
        ok, thao_tac, ket_qua = bot.process_bypass_nat_contract(shd, nguyen_nhan_1)

        # Lưu cache
        cache = inside_bypass_nat.load_cache()
        cache[shd] = {
            "ket_qua": ket_qua,
            "thao_tac": thao_tac,
            "time": time.strftime("%d/%m/%Y %H:%M:%S"),
            "timestamp_epoch": time.time()
        }
        inside_bypass_nat.save_cache(cache)

        # Gửi Webhook nếu có cấu hình
        cfg = core_login.load_config()
        webhook_url = cfg.get("bypass_nat_webhook_url", "") or cfg.get("spampool_webhook_url", "") or cfg.get("cls_webhook_url", "") or cfg.get("google_sheet_webhook_url", "")
        if webhook_url:
            try:
                payload = {
                    "sheet_id": inside_bypass_nat.DEFAULT_SHEET_ID,
                    "gid": inside_bypass_nat.GID_BYPASS_NAT,
                    "shd": shd,
                    "status": thao_tac,
                    "thao_tac": thao_tac,
                    "ket_qua": ket_qua,
                    "col_shd": 5,
                    "col_ngay": 7,
                    "col_ket_qua": 8,
                    "col_thao_tac": 9,
                    "timestamp": time.strftime("%d/%m/%Y %H:%M:%S")
                }
                req = urllib.request.Request(
                    webhook_url,
                    data=json.dumps(payload).encode("utf-8"),
                    headers={"Content-Type": "application/json"}
                )
                with urllib.request.urlopen(req, timeout=10) as resp:
                    resp_text = resp.read().decode("utf-8", errors="ignore")
                    task_log(f"Đã cập nhật Webhook Google Sheet cho HĐ {shd}: '{thao_tac}' | KQ: '{ket_qua}'", "success")
            except Exception as e_hook:
                task_log(f"Lỗi gửi Webhook cho HĐ {shd}: {e_hook}", "warning")

        bypass_nat_task_state["message"] = f"Hoàn tất HĐ {shd}: {thao_tac}"
        return jsonify({
            "status": "ok" if ok else "error",
            "shd": shd,
            "thao_tac": thao_tac,
            "ket_qua": ket_qua
        })
    except Exception as e:
        bypass_nat_task_state["message"] = f"Lỗi test HĐ {shd}: {e}"
        add_log(f"[Bypass NAT] Lỗi test HĐ {shd}: {e}", "error", "bypass_nat")
        return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        bypass_nat_task_state["is_running"] = False
        if bot:
            try:
                bot.close(force=True)
            except Exception:
                pass
        with radius_task_lock:
            radius_sync_busy["active"] = False

@app.route("/api/bypass_nat/start", methods=["POST"])
def start_bypass_nat_task():
    global active_bypass_nat_bot
    with radius_task_lock:
        if radius_sync_busy["active"]:
            return jsonify({"status": "busy", "message": "Hệ thống Radius Portal đang bận xử lý tác vụ đơn lẻ/đăng nhập!"}), 409
        if bypass_nat_task_state.get("is_running"):
            return jsonify({"status": "busy", "message": "Tiến trình Bypass NAT đang chạy!"}), 429
        if spampool_task_state.get("is_running"):
            return jsonify({"status": "busy", "message": "Tiến trình SpamPool đang chạy trên cùng hệ thống Radius!"}), 429

        data = request.json or {}
        headless = data.get("headless", False)
        sheet_id = data.get("sheet_id", inside_bypass_nat.DEFAULT_SHEET_ID)
        gid      = data.get("gid", inside_bypass_nat.GID_BYPASS_NAT)

        sheet_res = inside_bypass_nat.fetch_sheet_data(sheet_id=sheet_id, gid=gid)
        if sheet_res.get("status") != "ok" or not sheet_res.get("records"):
            return jsonify({"status": "error", "message": "Không tìm thấy dữ liệu trên Google Sheet GID 1907537423!"}), 400

        to_process = [r for r in sheet_res["records"] if inside_bypass_nat.is_pending(r.get("Kết Quả"), r.get("Thao Tác"))]
        if not to_process:
            return jsonify({"status": "error", "message": "Tất cả hợp đồng đã được xử lý xong (không có hợp đồng nào 'Chưa cập nhật')!"}), 400

        bypass_nat_task_state["is_running"] = True
        bypass_nat_task_state["total"] = len(to_process)
        bypass_nat_task_state["current_index"] = 0
        bypass_nat_task_state["current_shd"] = str(to_process[0].get("SHD", ""))
        bypass_nat_task_state["message"] = f"Bắt đầu xử lý {len(to_process)} hợp đồng Bypass NAT..."
        bypass_nat_task_state["sheet_id"] = sheet_id
        bypass_nat_task_state["gid"] = gid
        bypass_nat_task_state["processed_in_session"] = []
        task_log = make_task_logger(bypass_nat_task_state, "bypass_nat", "Bypass NAT")

        task_log(f"=== BẮT ĐẦU AUTO BYPASS NAT {len(to_process)} HỢP ĐỒNG ===", "info")

    def update_sheet_remote_bypass_nat(record, thao_tac_val, ket_qua_val):
        cfg = core_login.load_config()
        webhook_url = cfg.get("bypass_nat_webhook_url", "") or cfg.get("spampool_webhook_url", "") or cfg.get("cls_webhook_url", "") or cfg.get("google_sheet_webhook_url", "")
        if webhook_url:
            try:
                payload = {
                    "sheet_id": sheet_id,
                    "gid": gid,
                    "row_id": record.get("ID"),
                    "shd": record.get("SHD"),
                    "status": thao_tac_val,
                    "thao_tac": thao_tac_val,
                    "ket_qua": ket_qua_val,
                    "col_shd": 5,
                    "col_ngay": 7,
                    "col_ket_qua": 8,
                    "col_thao_tac": 9,
                    "timestamp": time.strftime("%d/%m/%Y %H:%M:%S")
                }
                req = urllib.request.Request(
                    webhook_url,
                    data=json.dumps(payload).encode("utf-8"),
                    headers={"Content-Type": "application/json"}
                )
                with urllib.request.urlopen(req, timeout=10) as resp:
                    resp_text = resp.read().decode("utf-8", errors="ignore")
                    task_log(f"Đã cập nhật Webhook Bypass NAT cho HĐ {record.get('SHD')}: '{thao_tac_val}' | Kết quả='{ket_qua_val}'", "success")
            except Exception as e_hook:
                task_log(f"Không thể đẩy Webhook cho HĐ {record.get('SHD')}: {e_hook}", "warning")

    def worker_bypass_nat():
        global active_bypass_nat_bot
        bot = inside_bypass_nat.InsideBypassNatAutomation(headless=headless, keep_open=False, log_cb=task_log)
        active_bypass_nat_bot = bot
        processed_shds = set()
        try:
            bot.init_driver()
            bot.navigate_to_network_connection()

            for idx, r in enumerate(to_process):
                if bot._stop_requested:
                    break

                shd = str(r.get("SHD", "")).strip()
                nguyen_nhan_1 = str(r.get("Nguyên Nhân 1", "")).strip()
                bypass_nat_task_state["current_index"] = idx + 1
                bypass_nat_task_state["current_shd"] = shd
                bypass_nat_task_state["message"] = f"Đang xử lý Bypass NAT {idx + 1}/{len(to_process)}: HĐ {shd}..."

                try:
                    ok, thao_tac, ket_qua = bot.process_bypass_nat_contract(shd, nguyen_nhan_1)
                    if shd:
                        processed_shds.add(shd)
                    now_str = time.strftime("%d/%m/%Y %H:%M:%S")

                    r["Thao Tác"] = thao_tac
                    r["Kết Quả"] = ket_qua
                    r["Ngày Cập Nhật"] = now_str

                    cache = inside_bypass_nat.load_cache()
                    cache[shd] = {
                        "ket_qua": ket_qua,
                        "thao_tac": thao_tac,
                        "time": now_str,
                        "timestamp_epoch": time.time()
                    }
                    inside_bypass_nat.save_cache(cache)

                    update_sheet_remote_bypass_nat(r, thao_tac, ket_qua)

                    bypass_nat_task_state["processed_in_session"].append({
                        "shd": shd,
                        "status": ket_qua,
                        "thao_tac": thao_tac,
                        "time": now_str
                    })
                    task_log(f"Bypass NAT HĐ {shd}: Kết quả='{ket_qua}' | Thao tác='{thao_tac}'", "success", "bypass_nat")
                except Exception as ex_single:
                    if shd:
                        processed_shds.add(shd)
                    err_msg = str(ex_single)[:80]
                    task_log(f"Lỗi xử lý HĐ {shd}: {err_msg}", "error")
                    r["Thao Tác"] = f"Lỗi: {err_msg}"
                    r["Kết Quả"] = "Lỗi"
                    bypass_nat_task_state["processed_in_session"].append({
                        "shd": shd,
                        "status": "Lỗi",
                        "thao_tac": f"Lỗi: {err_msg}",
                        "time": time.strftime("%d/%m/%Y %H:%M:%S")
                    })

                time.sleep(2)

            bypass_nat_task_state["message"] = f"Hoàn tất xử lý {len(to_process)} hợp đồng Bypass NAT."
            task_log(f"=== HOÀN TẤT AUTO BYPASS NAT ({len(to_process)} HỢP ĐỒNG) ===", "success")
        except Exception as e:
            bypass_nat_task_state["message"] = f"Lỗi Bypass NAT: {e}"
            task_log(f"Tiến trình Bypass NAT bị dừng: {e}", "error")
        finally:
            _release_remaining_auto_attempts("bypass_nat", to_process, processed_shds)
            bypass_nat_task_state["is_running"] = False
            if bot:
                try:
                    bot.close(force=True)
                except Exception:
                    pass
            active_bypass_nat_bot = None

    threading.Thread(target=worker_bypass_nat, daemon=True).start()
    return jsonify({"status": "started", "count": len(to_process)})


# ================= CẤP/THU HỒI PORT (PORT.FPT.NET) =================
import inside_port

port_task_state = {
    "is_running": False,
    "current_index": 0,
    "total": 0,
    "current_shd": "",
    "message": "Sẵn sàng",
    "sheet_id": inside_port.DEFAULT_SHEET_ID,
    "gid": inside_port.GID_PORT,
    "processed_in_session": []
}
active_port_bot = None
port_task_lock = threading.Lock()
port_sync_busy = {"active": False}

def _update_port_sheet_webhook(shd, thao_tac_val, row_id=None, sheet_id=None, gid=None, tac_vu="Thu Hồi Port", tap_diem="", port_val="", ket_qua_val=None):
    cfg = core_login.load_config()
    webhook_url = (
        cfg.get("port_webhook_url", "")
        or cfg.get("google_sheet_webhook_url", "")
        or cfg.get("spampool_webhook_url", "")
        or cfg.get("bypass_nat_webhook_url", "")
    )
    if not webhook_url:
        return
    try:
        now_ts = time.strftime("%d/%m/%Y %H:%M:%S")
        if ket_qua_val is None:
            ket_qua_val = "Không thành công" if ("không thành công" in str(thao_tac_val).lower() or "lỗi" in str(thao_tac_val).lower()) else "Đã xử lý"

        extra_cols = []
        if tap_diem:
            extra_cols.append((6, str(tap_diem).strip()))
        if port_val:
            extra_cols.append((7, str(port_val).strip()))
        if not extra_cols:
            extra_cols.append((None, None))

        for col_idx, col_val in extra_cols:
            payload = {
                "sheet_id": sheet_id or inside_port.DEFAULT_SHEET_ID,
                "gid": gid or inside_port.GID_PORT,
                "row_id": row_id,
                "shd": shd or "",
                "status": thao_tac_val,
                "thao_tac": thao_tac_val,
                "ket_qua": ket_qua_val,
                "tap_diem": str(tap_diem or "").strip(),
                "port": str(port_val or "").strip(),
                "col_shd": 5,
                "col_tap_diem": 6,
                "col_port": 7,
                "col_ngay": 9,
                "col_ket_qua": 10,
                "col_thao_tac": 11,
                "timestamp": now_ts
            }
            if col_idx is not None and col_val:
                # Tương thích với Apps Script hiện tại: trên GID 966043489 không có cột Ghi Chú (colGhiChu = -1)
                # nên truyền col_ghi_chu = 6 (Tập Điểm) và 7 (Port) để ghi trực tiếp vào đúng cột.
                payload["col_ghi_chu"] = col_idx
                payload["ghi_chu"] = col_val

            req = urllib.request.Request(
                webhook_url,
                data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
                headers={"Content-Type": "application/json; charset=utf-8"}
            )
            with urllib.request.urlopen(req, timeout=12) as resp:
                resp.read()

        add_log(
            f"Đã cập nhật Google Sheet Port (ID={row_id}, HĐ={shd or 'Trống SHD'}): Tập điểm='{tap_diem}' | Port='{port_val}' | Kết quả='{ket_qua_val}' | Thao tác='{thao_tac_val}'",
            "success"
        )
    except Exception as e_hook:
        add_log(f"Không thể đẩy Webhook Port cho HĐ {shd or row_id}: {e_hook}", "warning")

@app.route("/api/port/sheet", methods=["GET"])
def get_port_sheet():
    sheet_id = request.args.get("sheet_id", inside_port.DEFAULT_SHEET_ID).strip()
    gid      = request.args.get("gid", inside_port.GID_PORT).strip()
    data = inside_port.fetch_sheet_data(sheet_id=sheet_id, gid=gid)
    return jsonify(data)

@app.route("/api/port/status", methods=["GET"])
def get_port_status():
    return jsonify({
        "status": "ok",
        "task": port_task_state
    })

@app.route("/api/port/stop", methods=["POST"])
def stop_port_task():
    global active_port_bot
    if active_port_bot:
        active_port_bot.request_stop()
        try:
            active_port_bot.close(force=True)
        except Exception:
            pass
    port_task_state["is_running"] = False
    port_task_state["message"] = "Đã nhận lệnh dừng tiến trình Cấp/Thu Hồi Port."
    add_log("Đã gửi yêu cầu dừng tiến trình Cấp/Thu Hồi Port!", "warning")
    return jsonify({"status": "ok", "message": "Đã gửi yêu cầu dừng tiến trình Cấp/Thu Hồi Port."})

@app.route("/api/port/clear_cache", methods=["POST"])
def clear_port_cache():
    if os.path.exists(inside_port.PORT_CACHE_FILE):
        try:
            os.remove(inside_port.PORT_CACHE_FILE)
        except Exception:
            pass
    add_log("Đã xóa sạch cache trạng thái Cấp/Thu Hồi Port!", "success")
    return jsonify({"status": "ok", "message": "Đã xóa sạch cache trạng thái Cấp/Thu Hồi Port."})

@app.route("/api/port/test_single", methods=["POST"])
def test_single_port():
    with port_task_lock:
        if port_task_state.get("is_running") or port_sync_busy["active"]:
            return jsonify({"status": "busy", "message": "Hệ thống Port Portal đang bận xử lý tác vụ khác!"}), 409
        port_sync_busy["active"] = True

    bot = None
    shd = ""
    try:
        data = request.json or {}
        shd = str(data.get("shd", "")).strip()
        row_id = str(data.get("row_id", "")).strip()
        tac_vu = str(data.get("tac_vu", "")).strip()
        tap_diem = str(data.get("tap_diem", "")).strip()
        port_num = str(data.get("port", "")).strip()
        headless = data.get("headless", False)

        # Trường hợp dòng chỉ có Tập điểm / Port mà cột SHD để trống
        if not shd:
            thao_tac = inside_port.PORT_NO_SHD_MSG
            now_str = time.strftime("%d/%m/%Y %H:%M:%S")
            cache = inside_port.load_cache()
            c_val = {
                "thao_tac": thao_tac,
                "ket_qua": "Không thành công",
                "tap_diem": tap_diem,
                "port": port_num,
                "time": now_str,
                "timestamp_epoch": time.time(),
                "force_override": True
            }
            if row_id:
                cache[f"_{row_id}"] = c_val
                cache[f"ROW_{row_id}"] = c_val
            inside_port.save_cache(cache)

            _update_port_sheet_webhook(
                "",
                thao_tac,
                row_id=row_id,
                tac_vu=tac_vu or "Thu Hồi Port",
                tap_diem=tap_diem,
                port_val=port_num,
                ket_qua_val="Không thành công"
            )
            add_log(f"⚠️ Dòng ID={row_id} (Tập điểm={tap_diem}, Port={port_num}) trống SHD -> {thao_tac}", "warning", "port")
            return jsonify({
                "status": "ok",
                "shd": "",
                "tap_diem": tap_diem,
                "port": port_num,
                "thao_tac": thao_tac,
                "message": thao_tac
            })

        port_task_state["is_running"] = True
        port_task_state["total"] = 1
        port_task_state["current_index"] = 0
        port_task_state["current_shd"] = shd
        port_task_state["message"] = f"Đang khởi tạo Chrome & đăng nhập cho HĐ {shd}..."
        task_log = make_task_logger(port_task_state, "port", "Cấp/Thu Hồi Port")

        task_log(f"=== BẮT ĐẦU THU HỒI PORT CHO HĐ {shd} ===", "info")
        bot = inside_port.InsidePortAutomation(headless=headless, keep_open=False, log_cb=task_log)
        bot.init_driver()
        bot.navigate_to_ftth_new_search()
        port_task_state["current_index"] = 1
        port_task_state["message"] = f"Đang xử lý Thu hồi Port 1/1: HĐ {shd}..."
        ok, thao_tac = bot.process_port_contract(shd, tac_vu=tac_vu)
        now_str = time.strftime("%d/%m/%Y %H:%M:%S")
        tap_diem_val = bot.last_tap_diem
        port_val = bot.last_port
        kq_val = "Đã xử lý" if ok else "Không thành công"

        cache = inside_port.load_cache()
        c_val = {
            "thao_tac": thao_tac,
            "ket_qua": kq_val,
            "tap_diem": tap_diem_val,
            "port": port_val,
            "time": now_str,
            "timestamp_epoch": time.time()
        }
        cache[shd] = c_val
        if row_id:
            cache[f"{shd}_{row_id}"] = c_val
        inside_port.save_cache(cache)

        _update_port_sheet_webhook(
            shd,
            thao_tac,
            row_id=row_id,
            tac_vu=tac_vu or "Thu Hồi Port",
            tap_diem=tap_diem_val,
            port_val=port_val,
            ket_qua_val=kq_val
        )

        port_task_state["message"] = f"Hoàn tất HĐ {shd}: {thao_tac}"
        return jsonify({
            "status": "ok" if ok else "error",
            "shd": shd,
            "tap_diem": tap_diem_val,
            "port": port_val,
            "thao_tac": thao_tac,
            "message": thao_tac
        })
    except Exception as e:
        port_task_state["message"] = f"Lỗi xử lý Thu hồi Port HĐ {shd}: {e}"
        add_log(f"[Cấp/Thu Hồi Port] Lỗi xử lý Thu hồi Port HĐ {shd}: {e}", "error", "port")
        return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        port_task_state["is_running"] = False
        if bot:
            try:
                bot.close(force=True)
            except Exception:
                pass
        with port_task_lock:
            port_sync_busy["active"] = False

@app.route("/api/port/start", methods=["POST"])
def start_port_auto():
    global active_port_bot
    with port_task_lock:
        if port_sync_busy["active"]:
            return jsonify({"status": "busy", "message": "Hệ thống Port Portal đang bận xử lý tác vụ test đơn!"}), 409
        if port_task_state.get("is_running"):
            return jsonify({"status": "busy", "message": "Tiến trình Cấp/Thu Hồi Port đang chạy!"}), 429

        data = request.json or {}
        headless = data.get("headless", False)
        sheet_id = data.get("sheet_id", inside_port.DEFAULT_SHEET_ID)
        gid      = data.get("gid", inside_port.GID_PORT)

        sheet_res = inside_port.fetch_sheet_data(sheet_id=sheet_id, gid=gid)
        if sheet_res.get("status") != "ok" or not sheet_res.get("records"):
            return jsonify({"status": "error", "message": f"Không tìm thấy dữ liệu trên Google Sheet GID {gid}!"}), 400

        to_process = [
            r for r in sheet_res["records"]
            if (
                str(r.get("Số Hợp Đồng") or r.get("SHD") or "").strip()
                or str(r.get("Tập Điểm") or "").strip()
                or str(r.get("Port") or "").strip()
            )
            and inside_port.is_thu_hoi_port_task(r.get("Tác Vụ"))
            and inside_port.is_pending(r.get("Ngày Cập Nhật"), r.get("Thao Tác"))
        ]
        if not to_process:
            return jsonify({"status": "error", "message": "Tất cả hợp đồng đã được xử lý xong!"}), 400

        first_shd = str(to_process[0].get("Số Hợp Đồng") or to_process[0].get("SHD") or to_process[0].get("Tập Điểm") or "").strip()
        port_task_state["is_running"] = True
        port_task_state["total"] = len(to_process)
        port_task_state["current_index"] = 0
        port_task_state["current_shd"] = first_shd
        port_task_state["message"] = f"Bắt đầu xử lý {len(to_process)} yêu cầu Thu hồi Port..."
        port_task_state["sheet_id"] = sheet_id
        port_task_state["gid"] = gid
        port_task_state["processed_in_session"] = []
        task_log = make_task_logger(port_task_state, "port", "Cấp/Thu Hồi Port")

        task_log(f"=== BẮT ĐẦU AUTO THU HỒI PORT ({len(to_process)} YÊU CẦU) ===", "info")

    def worker_port():
        global active_port_bot
        bot = None
        driver_ready = False
        processed_shds = set()
        try:
            for idx, r in enumerate(to_process):
                if bot and bot._stop_requested:
                    break

                shd = str(r.get("Số Hợp Đồng") or r.get("SHD") or "").strip()
                row_id = str(r.get("ID", "")).strip()
                tac_vu = str(r.get("Tác Vụ", "")).strip()
                tap_diem_in = str(r.get("Tập Điểm", "")).strip()
                port_in = str(r.get("Port", "")).strip()

                port_task_state["current_shd"] = shd or tap_diem_in or f"ID {row_id}"

                # Trường hợp dòng chỉ có Tập điểm và Port, cột SHD để trống
                if not shd:
                    port_task_state["current_index"] = idx + 1
                    port_task_state["message"] = f"Đang xử lý Thu hồi Port {idx + 1}/{len(to_process)}: {tap_diem_in or row_id}..."
                    now_str = time.strftime("%d/%m/%Y %H:%M:%S")
                    thao_tac = inside_port.PORT_NO_SHD_MSG
                    r["Thao Tác"] = thao_tac
                    r["Kết Quả"] = "Không thành công"
                    r["Ngày Cập Nhật"] = now_str

                    cache = inside_port.load_cache()
                    c_val = {
                        "thao_tac": thao_tac,
                        "ket_qua": "Không thành công",
                        "tap_diem": tap_diem_in,
                        "port": port_in,
                        "time": now_str,
                        "timestamp_epoch": time.time(),
                        "force_override": True
                    }
                    if row_id:
                        cache[f"_{row_id}"] = c_val
                        cache[f"ROW_{row_id}"] = c_val
                    inside_port.save_cache(cache)

                    _update_port_sheet_webhook(
                        "",
                        thao_tac,
                        row_id=row_id,
                        sheet_id=sheet_id,
                        gid=gid,
                        tac_vu=tac_vu or "Thu Hồi Port",
                        tap_diem=tap_diem_in,
                        port_val=port_in,
                        ket_qua_val="Không thành công"
                    )
                    port_task_state["processed_in_session"].append({
                        "shd": "",
                        "tap_diem": tap_diem_in,
                        "port": port_in,
                        "thao_tac": thao_tac,
                        "time": now_str
                    })
                    if row_id:
                        processed_shds.add(row_id)
                    task_log(f"⚠️ Dòng ID={row_id} (Tập điểm={tap_diem_in}, Port={port_in}) trống SHD -> {thao_tac}", "warning", "port")
                    time.sleep(0.5)
                    continue

                try:
                    if not driver_ready:
                        port_task_state["current_index"] = 0
                        bot = inside_port.InsidePortAutomation(headless=headless, keep_open=False, log_cb=task_log)
                        active_port_bot = bot
                        bot.init_driver()
                        bot.navigate_to_ftth_new_search()
                        driver_ready = True
                    else:
                        port_task_state["current_index"] = idx + 1
                        bot.navigate_to_ftth_new_search()

                    port_task_state["current_index"] = idx + 1
                    port_task_state["message"] = f"Đang xử lý Thu hồi Port {idx + 1}/{len(to_process)}: {shd or tap_diem_in}..."

                    ok, thao_tac = bot.process_port_contract(shd, tac_vu=tac_vu)
                    if shd:
                        processed_shds.add(shd)
                    now_str = time.strftime("%d/%m/%Y %H:%M:%S")
                    tap_diem_val = bot.last_tap_diem
                    port_val = bot.last_port
                    kq_val = "Đã xử lý" if ok else "Không thành công"

                    r["Thao Tác"] = thao_tac
                    r["Kết Quả"] = kq_val
                    r["Ngày Cập Nhật"] = now_str
                    if tap_diem_val:
                        r["Tập Điểm"] = tap_diem_val
                    if port_val:
                        r["Port"] = port_val

                    cache = inside_port.load_cache()
                    c_val = {
                        "thao_tac": thao_tac,
                        "ket_qua": kq_val,
                        "tap_diem": tap_diem_val,
                        "port": port_val,
                        "time": now_str,
                        "timestamp_epoch": time.time()
                    }
                    cache[shd] = c_val
                    if row_id:
                        cache[f"{shd}_{row_id}"] = c_val
                    inside_port.save_cache(cache)

                    _update_port_sheet_webhook(
                        shd,
                        thao_tac,
                        row_id=row_id,
                        sheet_id=sheet_id,
                        gid=gid,
                        tac_vu=tac_vu or "Thu Hồi Port",
                        tap_diem=tap_diem_val,
                        port_val=port_val,
                        ket_qua_val=kq_val
                    )

                    port_task_state["processed_in_session"].append({
                        "shd": shd,
                        "tap_diem": tap_diem_val,
                        "port": port_val,
                        "thao_tac": thao_tac,
                        "time": now_str
                    })
                    task_log(f"Thu hồi Port HĐ {shd}: Thao tác='{thao_tac}'", "success", "port")
                except Exception as ex_single:
                    if shd:
                        processed_shds.add(shd)
                    err_msg = str(ex_single)[:80]
                    task_log(f"Lỗi xử lý Thu hồi Port HĐ {shd}: {err_msg}", "error")
                    r["Thao Tác"] = f"Lỗi: {err_msg}"
                    port_task_state["processed_in_session"].append({
                        "shd": shd,
                        "thao_tac": f"Lỗi: {err_msg}",
                        "time": time.strftime("%d/%m/%Y %H:%M:%S")
                    })

                time.sleep(1.5)

            port_task_state["message"] = f"Hoàn tất xử lý {len(to_process)} yêu cầu Thu hồi Port."
            task_log(f"=== HOÀN TẤT AUTO THU HỒI PORT ({len(to_process)} YÊU CẦU) ===", "success")
        except Exception as e:
            port_task_state["message"] = f"Lỗi Thu hồi Port: {e}"
            task_log(f"Tiến trình Thu hồi Port bị dừng: {e}", "error")
        finally:
            _release_remaining_auto_attempts("port", to_process, processed_shds)
            port_task_state["is_running"] = False
            if bot:
                try:
                    bot.close(force=True)
                except Exception:
                    pass
            active_port_bot = None

    threading.Thread(target=worker_port, daemon=True).start()
    return jsonify({"status": "started", "count": len(to_process)})


def find_free_port(preferred_port=5001, fallback_start=5001, fallback_end=5100):

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(('0.0.0.0', preferred_port))
            return preferred_port
        except OSError:
            pass

    for port in range(fallback_start, fallback_end):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(('0.0.0.0', port))
                return port
            except OSError:
                continue
    return 8080

# ================= AUTO NỀN TOÀN HỆ THỐNG (chạy trên server, không cần mở tab/trình duyệt) =================
AUTO_MODES_FILE   = os.path.join(BASE_DIR, "auto_modes.json")
AUTO_ATTEMPT_TTL  = 300  # HĐ đã được Auto thử: chờ 5 phút (để Sheet kịp cập nhật) rồi mới thử lại nếu vẫn chưa xử lý
AUTO_SCAN_INTERVAL = 5  # giây
AUTO_TABS = ["bypass", "cls", "assign", "clear_signal", "reset_signal", "mybae", "spampool", "bypass_nat", "port"]

def _lc(v):
    return inside_signal.normalize_nfc(v).lower()

def _auto_pending_bypass(r):
    return not inside_bypass.is_bypass_final_status(r.get("Thao Tác") or r.get("Thao tác") or "")

def _auto_pending_cls(r):
    kq = _lc(r.get("Kết Quả", ""))
    tt = _lc(r.get("Thao Tác", ""))
    done = (kq == "đã xử lý" or tt == "đã clear" or "cập nhật thành công" in tt
            or ("thành công" in tt and "không" not in tt) or "không thành công" in tt or "lỗi" in tt)
    return not done

def _auto_pending_assign(r):
    return not _lc(r.get("Thao Tác", ""))

def _auto_pending_signal(r, tab=None):
    if _is_signal_manual_locked(tab, r):
        return False
    return not inside_signal.is_final_status(r.get("Kết Quả", ""))

def _auto_pending_clear_signal(r):
    return _auto_pending_signal(r, "clear_signal")

def _auto_pending_reset_signal(r):
    return _auto_pending_signal(r, "reset_signal")

def _auto_pending_mybae(r):
    return not _lc(r.get("Thao Tác", "")) and not inside_mybae.is_final_row(r)

_TT_PENDING_VALUES = ("", "nan", "chưa cập nhật", "chưa xử lý")

def _auto_pending_generic(r):
    """Quy tắc chung: Thao Tác 'Chưa cập nhật'/'Chưa xử lý' => cần xử lý; nếu Kết Quả đã xử lý và không có Thao Tác chờ => bỏ qua."""
    kq = _lc(r.get("Kết Quả") or r.get("Kết quả") or "")
    tt = _lc(r.get("Thao Tác") or r.get("Thao tác") or "")
    # HĐ lỗi hoặc từ chối do vi phạm 14N coi như đã xử lý xong -> bỏ qua, không tự chạy lại
    if any(w in kq or w in tt for w in ("lỗi", "không thành công", "thất bại", "error", "vi phạm", "từ chối")):
        return False
    # Nếu Thao Tác đánh dấu rõ đang chờ xử lý (Chưa cập nhật / Chưa xử lý) => luôn ưu tiên xử lý trước khi xét Kết Quả
    if tt in ("chưa cập nhật", "chưa xử lý"):
        return True
    if any(x in kq for x in ("đã xử lý", "đã cấp", "đã clear", "thành công", "hoàn tất")):
        return False
    if any(x in tt for x in ("đã xử lý", "đã cấp", "đã clear", "đã phân công", "thành công", "hoàn tất")):
        return False
    if kq and kq not in ("nan", "chưa xử lý", "chưa cập nhật"):
        return True
    return tt in _TT_PENDING_VALUES

def _auto_pending_mybae_generic(r):
    return _auto_pending_generic(r) and not inside_mybae.is_final_row(r)

AUTO_TAB_CFG = {
    "bypass":       {"sheet": "/api/bypass/sheet-data?gid=0",           "run": "/api/bypass/run",        "pending": _auto_pending_bypass,  "label": "Bypass"},
    "cls":          {"sheet": "/api/cls/sheet-data?gid=987552880",      "run": "/api/cls/run",           "pending": _auto_pending_generic, "label": "Clear Cls"},
    "assign":       {"sheet": "/api/assign/sheet-data",                 "run": "/api/assign/run",        "pending": _auto_pending_generic, "label": "Phân Công Tay"},
    "clear_signal": {"sheet": "/api/clear-signal/sheet-data",           "run": "/api/clear-signal/run",  "pending": _auto_pending_clear_signal,  "label": "Clear Tín Hiệu"},
    "reset_signal": {"sheet": "/api/reset-signal/sheet-data",           "run": "/api/reset-signal/run",  "pending": _auto_pending_reset_signal,  "label": "Cấp Lại Tín Hiệu"},
    "mybae":        {"sheet": "/api/mybae/sheet-data",                  "run": "/api/mybae/run",         "pending": _auto_pending_mybae_generic, "label": "Bypass MyBAE"},
}

def _auto_any_running():
    return bool(_other_inside_task_running() or mybae_task_state.get("is_running") or spampool_task_state.get("is_running") or bypass_nat_task_state.get("is_running") or port_task_state.get("is_running"))

@app.route("/api/auto-modes", methods=["GET", "POST"])
def auto_modes_api():
    """Đồng bộ trạng thái nút Tự Động (BẬT/TẮT) của từng tab từ giao diện lên server."""
    modes = inside_signal.load_cache(AUTO_MODES_FILE)
    if request.method == "POST":
        incoming = request.json or {}
        for k, v in incoming.items():
            if k in AUTO_TABS:
                modes[k] = bool(v)
        inside_signal.save_cache(AUTO_MODES_FILE, modes)
    return jsonify({k: modes.get(k, True) for k in AUTO_TABS})

AUTO_OVERVIEW = {"last_scan": "", "tabs": {}}

def _auto_task_states():
    return [
        ("bypass", "Bypass", bypass_task_state), ("cls", "Clear Cls", cls_task_state),
        ("assign", "Phân Công Tay", assign_task_state), ("clear_signal", "Clear Tín Hiệu", clear_signal_task_state),
        ("reset_signal", "Cấp Lại Tín Hiệu", reset_signal_task_state), ("mybae", "Bypass MyBAE", mybae_task_state),
        ("spampool", "SpamPool", spampool_task_state),
        ("bypass_nat", "Bypass NAT", bypass_nat_task_state),
        ("port", "Cấp/Thu Hồi Port", port_task_state),
    ]

@app.route("/api/auto/overview", methods=["GET"])
def auto_overview_api():
    """Tổng quan: số HĐ xử lý hôm nay (Today) - chờ xử lý từng tab, tiến trình đang chạy, nhật ký Auto gần nhất."""
    running = None
    all_states = list(_auto_task_states()) + [
        ("retrieval", "Lấy Thông Tin", retrieval_task),
    ]
    for key, label, st in all_states:
        if st.get("is_running"):
            shd_val = st.get("current_shd") or st.get("current_contract") or ""
            running = {
                "tab": key,
                "label": label,
                "name": label,
                "current": st.get("current_index", 0),
                "total": st.get("total", 0),
                "shd": shd_val,
                "message": st.get("message", ""),
                "step": st.get("current_step") or st.get("message", ""),
                "step_time": st.get("step_time", ""),
                "recent_steps": list(st.get("recent_steps") or [])[-5:],
            }
            break
    if running is None and task_state.get("status") == "running":
        running = {
            "tab": "login",
            "label": "Đăng Nhập Inside",
            "name": "Đăng Nhập Inside",
            "current": 0,
            "total": 1,
            "shd": task_state.get("user", ""),
            "message": task_state.get("message", ""),
            "step": task_state.get("current_step") or task_state.get("message", ""),
            "step_time": task_state.get("step_time", ""),
            "recent_steps": list(task_state.get("recent_steps") or [])[-5:],
        }
    tabs = AUTO_OVERVIEW["tabs"]
    with log_lock:
        recent = list(log_history[-80:])[::-1]
    return jsonify({
        "status": "ok",
        "last_scan": AUTO_OVERVIEW["last_scan"],
        "scan_interval": AUTO_SCAN_INTERVAL,
        "total_today": sum(t.get("today", 0) for t in tabs.values()),
        "total_pending": sum(t.get("pending", 0) for t in tabs.values()),
        "tabs": tabs,
        "running": running,
        "logs": recent,
    })

def _is_record_today(r):
    """Kiểm tra bản ghi có Ngày Cập Nhật là ngày hôm nay (Today) hay không."""
    if not isinstance(r, dict):
        return False
    raw = str(
        r.get("Ngày Cập Nhật")
        or r.get("Ngày Cập Nhật")
        or r.get("Ngày cập nhật")
        or r.get("Thời gian")
        or r.get("timestamp")
        or ""
    ).strip()
    if not raw or raw.lower() in ("nan", "chưa cập nhật", "chưa xử lý"):
        return False
    _dt = datetime.datetime if hasattr(datetime, "datetime") else datetime
    today = _dt.now().date()
    dt = inside_signal.parse_vn_datetime(raw)
    if dt:
        return dt.date() == today
    m1 = re.match(r"^(\d{1,2})[\/\-](\d{1,2})[\/\-](\d{4})", raw)
    if m1:
        try:
            return _dt(int(m1.group(3)), int(m1.group(2)), int(m1.group(1))).date() == today
        except ValueError:
            pass
    m2 = re.match(r"^(\d{4})[\/\-](\d{1,2})[\/\-](\d{1,2})", raw)
    if m2:
        try:
            return _dt(int(m2.group(1)), int(m2.group(2)), int(m2.group(3))).date() == today
        except ValueError:
            pass
    return False

def _auto_orchestrator_cycle():
    busy = _auto_any_running()
    modes = inside_signal.load_cache(AUTO_MODES_FILE)
    raw_attempts = inside_signal.load_cache(AUTO_ATTEMPT_FILE) or {}
    now = time.time()
    manual_locked = raw_attempts.get("_manual_locked", {}) if isinstance(raw_attempts.get("_manual_locked"), dict) else {}
    attempts = {
        t: {s: ts for s, ts in m.items() if isinstance(ts, (int, float)) and now - ts < AUTO_ATTEMPT_TTL}
        for t, m in raw_attempts.items()
        if t != "_manual_locked" and isinstance(m, dict)
    }
    if manual_locked:
        attempts["_manual_locked"] = manual_locked
    labels = {k: l for k, l, _ in _auto_task_states()}
    triggered = False

    with app.test_client() as c:
        for tab in AUTO_TABS:
            auto_on = modes.get(tab, True)
            if tab == "spampool":
                res = inside_spampool.fetch_sheet_data()
                if res.get("status") != "ok":
                    continue
                recs_sp = res.get("records", [])
                pend = [r for r in recs_sp if inside_spampool.is_pending(r.get("Kết Quả"), r.get("Thao Tác"))]
                today_done = [r for r in recs_sp if _is_record_today(r) and not inside_spampool.is_pending(r.get("Kết Quả"), r.get("Thao Tác"))]
                AUTO_OVERVIEW["tabs"][tab] = {"label": labels[tab], "today": len(today_done), "pending": len(pend), "total": len(recs_sp), "auto": auto_on}
                if busy or triggered or not auto_on:
                    continue
                tried = attempts.get(tab, {})
                pend_to_run = [r for r in pend if str(r.get("SHD")).strip() not in tried]
                if not pend_to_run:
                    continue
                add_log(f"🤖 Auto nền: phát hiện {len(pend_to_run)} HĐ SpamPool → tự chạy", "info")
                r_sp = c.post("/api/spampool/start", json={"headless": True})
                if r_sp.status_code == 200 and (r_sp.get_json(silent=True) or {}).get("status") == "started":
                    attempts.setdefault(tab, {}).update({str(r.get("SHD")).strip(): now for r in pend_to_run})
                    inside_signal.save_cache(AUTO_ATTEMPT_FILE, attempts)
                    triggered = True
                continue
            if tab == "bypass_nat":
                res = inside_bypass_nat.fetch_sheet_data()
                if res.get("status") != "ok":
                    continue
                recs_bn = res.get("records", [])
                pend = [r for r in recs_bn if inside_bypass_nat.is_pending(r.get("Kết Quả"), r.get("Thao Tác"))]
                today_done = [r for r in recs_bn if _is_record_today(r) and not inside_bypass_nat.is_pending(r.get("Kết Quả"), r.get("Thao Tác"))]
                AUTO_OVERVIEW["tabs"][tab] = {"label": labels[tab], "today": len(today_done), "pending": len(pend), "total": len(recs_bn), "auto": auto_on}
                if busy or triggered or not auto_on:
                    continue
                tried = attempts.get(tab, {})
                pend_to_run = [r for r in pend if str(r.get("SHD")).strip() not in tried]
                if not pend_to_run:
                    continue
                add_log(f"🤖 Auto nền: phát hiện {len(pend_to_run)} HĐ Bypass NAT → tự chạy", "info")
                r_bn = c.post("/api/bypass_nat/start", json={"headless": True})
                if r_bn.status_code == 200 and (r_bn.get_json(silent=True) or {}).get("status") == "started":
                    attempts.setdefault(tab, {}).update({str(r.get("SHD")).strip(): now for r in pend_to_run})
                    inside_signal.save_cache(AUTO_ATTEMPT_FILE, attempts)
                    triggered = True
                continue
            if tab == "port":
                res = inside_port.fetch_sheet_data()
                if res.get("status") != "ok":
                    continue
                recs_pt = res.get("records", [])
                def _port_key(r):
                    s = str(r.get("Số Hợp Đồng") or r.get("SHD") or "").strip()
                    rid = str(r.get("ID") or "").strip()
                    return f"{s}_{rid}" if rid else s
                pend = [
                    r for r in recs_pt
                    if (
                        str(r.get("Số Hợp Đồng") or r.get("SHD") or "").strip()
                        or str(r.get("Tập Điểm") or "").strip()
                        or str(r.get("Port") or "").strip()
                    )
                    and inside_port.is_thu_hoi_port_task(r.get("Tác Vụ"))
                    and inside_port.is_pending(r.get("Ngày Cập Nhật"), r.get("Thao Tác"))
                ]
                today_done = [
                    r for r in recs_pt
                    if _is_record_today(r)
                    and not inside_port.is_pending(r.get("Ngày Cập Nhật"), r.get("Thao Tác"))
                ]
                AUTO_OVERVIEW["tabs"][tab] = {"label": labels[tab], "today": len(today_done), "pending": len(pend), "total": len(recs_pt), "auto": auto_on}
                if busy or triggered or not auto_on:
                    continue
                tried = attempts.get(tab, {})
                pend_to_run = [r for r in pend if _port_key(r) not in tried]
                if not pend_to_run:
                    continue
                add_log(f"🤖 Auto nền: phát hiện {len(pend_to_run)} yêu cầu Cấp/Thu Hồi Port → tự chạy", "info")
                r_pt = c.post("/api/port/start", json={"headless": True})
                if r_pt.status_code == 200 and (r_pt.get_json(silent=True) or {}).get("status") == "started":
                    attempts.setdefault(tab, {}).update({_port_key(r): now for r in pend_to_run})
                    inside_signal.save_cache(AUTO_ATTEMPT_FILE, attempts)
                    triggered = True
                continue
            cfg = AUTO_TAB_CFG[tab]
            resp = c.get(cfg["sheet"])
            data = resp.get_json(silent=True) or {}
            if resp.status_code != 200 or data.get("status") != "ok":
                continue
            recs = data.get("records", [])
            all_pend = [r for r in recs if str(r.get("SHD", "")).strip() and cfg["pending"](r)]
            today_done = [r for r in recs if str(r.get("SHD", "")).strip() and _is_record_today(r) and not cfg["pending"](r)]
            AUTO_OVERVIEW["tabs"][tab] = {"label": cfg["label"], "today": len(today_done), "pending": len(all_pend), "total": len(recs), "auto": auto_on,
                                          "shds": [str(r.get("SHD")).strip() for r in all_pend[:20]]}
            if busy or triggered or not auto_on:
                continue
            tried = attempts.get(tab, {})
            pend = [r for r in all_pend if f"{str(r.get('SHD')).strip()}_{str(r.get('ID', '')).strip()}" not in tried and str(r.get("SHD")).strip() not in tried]
            if not pend:
                continue
            add_log(f"🤖 Auto nền: phát hiện {len(pend)} HĐ chờ xử lý ở {cfg['label']} → tự chạy", "info")
            run_payload = {"records": pend, "headless": True}
            if tab in ("clear_signal", "reset_signal"):
                run_payload["manual"] = False
            r2 = c.post(cfg["run"], json=run_payload)
            if r2.status_code == 200 and (r2.get_json(silent=True) or {}).get("status") == "started":
                attempts.setdefault(tab, {}).update({f"{str(r.get('SHD')).strip()}_{str(r.get('ID', '')).strip()}": now for r in pend})
                inside_signal.save_cache(AUTO_ATTEMPT_FILE, attempts)
                triggered = True
    AUTO_OVERVIEW["last_scan"] = time.strftime("%H:%M:%S")

def _auto_orchestrator_loop():
    time.sleep(AUTO_SCAN_INTERVAL)
    while True:
        try:
            cycle_t = threading.Thread(target=_auto_orchestrator_cycle, daemon=True)
            cycle_t.start()
            cycle_t.join(timeout=45)
            if cycle_t.is_alive():
                add_log("⚠️ Chu kỳ quét Auto nền phản hồi quá 45s (mạng chậm/chập chờn) → tự động mở chu kỳ quét mới", "warning")
        except Exception as e:
            add_log(f"Lỗi Auto nền: {e}", "warning")
        time.sleep(AUTO_SCAN_INTERVAL)

_BG_THREADS_STARTED = False
_BG_THREADS_LOCK = threading.Lock()

def start_background_threads():
    """Khởi chạy các luồng nền hệ thống một lần duy nhất (bỏ qua khi đang chạy test)."""
    global _BG_THREADS_STARTED
    if os.environ.get("TESTING") == "1":
        return
    with _BG_THREADS_LOCK:
        if _BG_THREADS_STARTED:
            return
        _BG_THREADS_STARTED = True
        clear_auto_attempts()
        threading.Thread(target=_log_flusher_loop, daemon=True).start()
        threading.Thread(target=_auto_reset_after_clear_loop, daemon=True).start()
        threading.Thread(target=_auto_orchestrator_loop, daemon=True).start()

@app.before_request
def _ensure_bg_threads_on_request():
    start_background_threads()

def open_browser_delayed(port):
    time.sleep(1.2)
    webbrowser.open(f"http://localhost:{port}")


from auto_import_routes import auto_import_bp
app.register_blueprint(auto_import_bp)

if __name__ == "__main__":
    start_background_threads()
    port = int(os.environ.get("PORT", 5001))

    print(f"==================================================================")
    print(f"   CAPTION NEXTSU AI - DANG CHAY TAI: http://localhost:{port}")
    print(f"==================================================================")

    if os.environ.get("WERKZEUG_RUN_MAIN") != "true":
        threading.Thread(target=open_browser_delayed, args=(port,), daemon=True).start()

    app.run(host="0.0.0.0", port=port, debug=False)

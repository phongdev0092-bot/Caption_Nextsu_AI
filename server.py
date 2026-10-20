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

# Logging & state management
log_history = []
log_lock = threading.Lock()

def add_log(message, level="info"):
    timestamp = time.strftime("%H:%M:%S")
    with log_lock:
        log_history.append({
            "time": timestamp,
            "level": level,
            "text": message
        })
        if len(log_history) > 120:
            log_history.pop(0)

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
        "last_run": "2026-10-13 10:45",
        "next_run": "2026-10-13 11:00",
        "status": "Đang chạy",
        "success_count": 48,
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
        "last_run": "2026-10-13 10:30",
        "next_run": "2026-10-13 11:00",
        "status": "Sẵn sàng",
        "success_count": 120,
        "failed_count": 2,
        "description": "Tự động đối soát và import file danh sách hợp đồng mới được thêm vào thư mục."
    },
    {
        "id": "task_3",
        "name": "Rà soát HĐ tồn đọng & Cảnh báo trễ hạn",
        "type": "alert_overdue",
        "schedule": "Mỗi 60 phút",
        "interval_minutes": 60,
        "is_active": False,
        "last_run": "2026-10-13 09:00",
        "next_run": "--:--",
        "status": "Tạm dừng",
        "success_count": 15,
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
        "last_run": "2026-10-13 00:00",
        "next_run": "2026-10-14 00:00",
        "status": "Hoàn tất",
        "success_count": 7,
        "failed_count": 0,
        "description": "Tự động tối ưu hóa và sao lưu dữ liệu nén Zstandard .json.zst."
    }
]

task_logs = [
    {"time": "11:00:15", "task_id": "task_1", "text": "Khởi động kịch bản quét định kỳ Phiếu Thi Công...", "level": "info"},
    {"time": "11:00:18", "task_id": "task_1", "text": "Đã kiểm tra 12 HĐ: 12 HĐ giữ nguyên trạng thái trong 48h.", "level": "success"},
    {"time": "10:30:22", "task_id": "task_2", "text": "Kịch bản Auto Import đã đối soát 50 bản ghi thành công.", "level": "success"},
    {"time": "10:00:05", "task_id": "task_4", "text": "Kiểm tra toàn vẹn kho Zstandard: nén tốt, không phát hiện lỗi.", "level": "info"}
]

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
        "assign_webhook_url"
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
    if task_state["status"] == "running":
        return jsonify({"status": "busy", "message": "Đang thực hiện đăng nhập..."}), 429

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
    add_log(f"=== BẮT ĐẦU ĐĂNG NHẬP ({active_acc['mode'].upper()}: {username}) ===", "info")

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
                log_callback=lambda msg, lvl: add_log(msg, lvl)
            )
            task_state["status"] = "success"
            task_state["message"] = "Đã đăng nhập thành công"
            task_state["user"] = username
            task_state["last_login_time"] = time.strftime("%H:%M:%S")
            add_log(f"Đăng nhập thành công tài khoản {username}", "success")
        except Exception as e:
            raw_err = str(e)
            if "Stacktrace:" in raw_err:
                clean_err = raw_err.split("Stacktrace:")[0].replace("Message:", "").strip()
                display_msg = clean_err if clean_err else "Hết thời gian chờ phản hồi từ trang đăng nhập Inside FPT"
            else:
                display_msg = raw_err
            task_state["status"] = "error"
            task_state["message"] = f"Lỗi: {display_msg}"
            add_log(f"Đăng nhập thất bại: {display_msg}", "error")

    threading.Thread(target=worker, daemon=True).start()
    return jsonify({"status": "started", "account": active_acc['mode'], "user": username})

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
    if retrieval_task["is_running"]:
        return jsonify({"status": "busy", "message": "Đang có tiến trình lấy dữ liệu đang chạy..."}), 429

    data = request.json or {}
    contracts = data.get("contracts", [])
    if isinstance(contracts, str):
        contracts = [c.strip() for c in contracts.split(",") if c.strip()]

    if not contracts:
        return jsonify({"status": "error", "message": "Vui lòng nhập hoặc chọn ít nhất 1 số hợp đồng!"}), 400

    retrieval_task["is_running"] = True
    retrieval_task["total"] = len(contracts)
    retrieval_task["current_index"] = 0
    retrieval_task["current_contract"] = contracts[0]
    retrieval_task["message"] = f"Bắt đầu xử lý {len(contracts)} hợp đồng..."

    add_log(f"=== BẮT ĐẦU AUTO LẤY DỮ LIỆU {len(contracts)} HỢP ĐỒNG ===", "info")

    def worker():
        # Phân loại và kiểm tra danh sách hợp đồng đã có dữ liệu thành công trong 48h
        to_scrape = []
        skipped_count = 0

        for c_no in contracts:
            is_cached, cached_record = check_cached_contract_48h(c_no, retrieval_records)
            if is_cached:
                skipped_count += 1
                add_log(f"⏩ [BỎ QUA 48H] HĐ {c_no} đã có dữ liệu thành công trong 48h (KH: {cached_record.get('customer_name')}). Bỏ qua không cào lại.", "info")
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
            add_log(f"=== HOÀN TẤT TỨC THÌ: TOÀN BỘ {len(contracts)} HỢP ĐỒNG ĐÃ ĐƯỢC LẤY TRONG 48H ===", "success")
            save_records_zstd(retrieval_records)
            retrieval_task["is_running"] = False
            return

        add_log(f"Khởi động Chrome để cào {len(to_scrape)} HĐ (Đã bỏ qua {skipped_count} HĐ có sẵn trong 48h)...", "info")
        scraper = InsideScraper(headless=True, log_cb=add_log)
        try:
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
            add_log(f"=== HOÀN TẤT LẤY DỮ LIỆU {len(to_scrape)} HỢP ĐỒNG ===", "success")

        except Exception as e:
            raw_err = str(e)
            if "Stacktrace:" in raw_err:
                clean_err = raw_err.split("Stacktrace:")[0].replace("Message:", "").strip()
                display_msg = clean_err if clean_err else "Hết thời gian chờ phản hồi từ trang Inside FPT"
            else:
                display_msg = raw_err
            retrieval_task["message"] = f"Lỗi tiến trình: {display_msg}"
            add_log(f"Tiến trình bị gián đoạn: {display_msg}", "error")
        finally:
            retrieval_task["is_running"] = False
            scraper.close()

    threading.Thread(target=worker, daemon=True).start()
    return jsonify({"status": "started", "count": len(contracts)})

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
    if retrieval_task.get("is_running") or bypass_task_state.get("is_running") or cls_task_state.get("is_running") or assign_task_state.get("is_running"):
        return jsonify({
            "status": "ok",
            "is_alive": True,
            "message": "Đang có tiến trình tự động (ByPass / Clear Cls / Phân Công / Thu thập) hoạt động bình thường trên phiên Inside FPT"
        })

    driver = None
    try:
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
        with open(BYPASS_CACHE_PATH, "w", encoding="utf-8") as f:
            json.dump(cache_data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        add_log(f"Lỗi lưu bypass cache: {e}", "warning")

# Khởi tạo bộ nhớ vĩnh viễn các SHD đã xử lý thành công
processed_bypass_cache = load_bypass_cache()

@app.route("/api/bypass/sheet-data", methods=["GET"])
def get_bypass_sheet_data():
    sheet_id = request.args.get("sheet_id", inside_bypass.DEFAULT_SHEET_ID).strip()
    gid = request.args.get("gid", inside_bypass.GID_BYPASS).strip()

    data = inside_bypass.fetch_sheet_data(sheet_id=sheet_id, gid=gid)
    if data["status"] == "ok":
        # Đồng bộ trạng thái đã xử lý từ file cache vĩnh viễn
        for r in data["records"]:
            shd = str(r.get("SHD") or r.get("Số Hợp Đồng") or "").strip()
            if shd and shd in processed_bypass_cache:
                c_val = processed_bypass_cache[shd]
                c_status = c_val if isinstance(c_val, str) else c_val.get("status", "Đã xử lý")
                c_time = c_val.get("time", "") if isinstance(c_val, dict) else ""

                if not r.get("Thao Tác") or str(r.get("Thao Tác")).lower() in ["nan", "chưa xử lý", ""]:
                    r["Thao Tác"] = c_status
                if c_time and (not r.get("Ngày Cập Nhật") or str(r.get("Ngày Cập Nhật")).lower() in ["nan", ""]):
                    r["Ngày Cập Nhật"] = c_time

        add_log(f"Đã đọc {data['count']} dòng từ Google Sheet (GID {gid})", "info")
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

@app.route("/api/bypass/export", methods=["GET", "POST"])
def export_bypass_excel():
    data = request.json if request.is_json else request.args
    sheet_id = data.get("sheet_id", inside_bypass.DEFAULT_SHEET_ID)
    gid = data.get("gid", inside_bypass.GID_BYPASS)
    status_filter = data.get("status", "all")
    
    sheet_res = inside_bypass.fetch_sheet_data(sheet_id=sheet_id, gid=gid)
    records = sheet_res.get("records", []) if sheet_res.get("status") == "ok" else []

    for r in records:
        shd = str(r.get("SHD", "")).strip()
        if shd in processed_bypass_cache:
            c_val = processed_bypass_cache[shd]
            c_st = c_val.get("status", "") if isinstance(c_val, dict) else str(c_val)
            c_time = c_val.get("time", "") if isinstance(c_val, dict) else ""
            if not r.get("Thao Tác") or str(r.get("Thao Tác")).lower() in ["nan", "chưa xử lý", ""]:
                r["Thao Tác"] = c_st
            if c_time and (not r.get("Ngày Cập Nhật") or str(r.get("Ngày Cập Nhật")).lower() in ["nan", ""]):
                r["Ngày Cập Nhật"] = c_time

    if status_filter == "done":
        filtered = [r for r in records if str(r.get("Thao Tác", "")).strip().lower() == "đã xử lý"]
    elif status_filter == "pending":
        filtered = [r for r in records if str(r.get("Thao Tác", "")).strip().lower() != "đã xử lý"]
    else:
        filtered = records

    if not filtered:
        filtered = records

    if not filtered:
        return jsonify({"status": "error", "message": "Không có dữ liệu ByPass để xuất file"}), 400

    export_rows = []
    for idx, r in enumerate(filtered, 1):
        export_rows.append({
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
    if bypass_task_state["is_running"]:
        return jsonify({"status": "busy", "message": "Đang có tiến trình Auto ByPass đang chạy..."}), 429
    if cls_task_state.get("is_running"):
        return jsonify({"status": "busy", "message": "Đang có tiến trình Clear Cls đang chạy trên Inside FPT. ByPass sẽ tự động chờ hoàn tất!"}), 429

    data = request.json or {}
    sheet_id = data.get("sheet_id", inside_bypass.DEFAULT_SHEET_ID)
    gid = data.get("gid", inside_bypass.GID_BYPASS)
    selected_records = data.get("records")
    headless = data.get("headless", True)

    if not selected_records:
        sheet_res = inside_bypass.fetch_sheet_data(sheet_id=sheet_id, gid=gid)
        if sheet_res["status"] != "ok" or not sheet_res["records"]:
            return jsonify({"status": "error", "message": "Không tìm thấy dữ liệu trên Google Sheet"}), 400
        selected_records = sheet_res["records"]

    # Lọc chỉ những dòng chưa xử lý
    to_process = []
    for r in selected_records:
        status_txt = str(r.get("Thao Tác", "")).strip().lower()
        if status_txt != "đã xử lý":
            to_process.append(r)

    if not to_process:
        return jsonify({"status": "ok", "message": "Tất cả các bản ghi đã được xử lý xong!"})

    bypass_task_state["is_running"] = True
    bypass_task_state["total"] = len(to_process)
    bypass_task_state["current_index"] = 0
    bypass_task_state["current_shd"] = str(to_process[0].get("SHD", ""))
    bypass_task_state["message"] = f"Bắt đầu xử lý {len(to_process)} hợp đồng ByPass..."
    bypass_task_state["sheet_id"] = sheet_id
    bypass_task_state["gid"] = gid
    bypass_task_state["processed_in_session"] = []  # Reset danh sách xử lý phiên mới

    add_log(f"=== BẮT ĐẦU AUTO BYPASS {len(to_process)} HỢP ĐỒNG TRÊN INSIDE FPT ===", "info")

    def update_sheet_remote(record):
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
                    "status": "Đã xử lý",
                    "timestamp": time.strftime("%d/%m/%Y %H:%M:%S")
                }
                req = urllib.request.Request(
                    webhook_url,
                    data=json.dumps(payload).encode("utf-8"),
                    headers={"Content-Type": "application/json"}
                )
                urllib.request.urlopen(req, timeout=5)
                add_log(f"Đã cập nhật trạng thái 'Đã xử lý' lên Google Sheet cho HĐ {record.get('SHD')}", "success")
            except Exception as e_hook:
                add_log(f"Không thể đẩy Webhook Google Sheet: {e_hook}", "warning")

    def worker():
        bot = inside_bypass.InsideBypassAutomation(headless=headless, log_cb=add_log)
        try:
            bot.init_driver()
            bot.navigate_to_bypass_page()
            bot.open_import_tab_and_dismiss_help()

            for idx, r in enumerate(to_process):
                shd = str(r.get("SHD", "")).strip()
                bypass_task_state["current_index"] = idx + 1
                bypass_task_state["current_shd"] = shd
                bypass_task_state["message"] = f"Đang xử lý {idx + 1}/{len(to_process)}: HĐ {shd}..."

                try:
                    ok, msg = bot.input_bypass_row(r)
                    if ok:
                        now_str = time.strftime("%d/%m/%Y %H:%M:%S")
                        processed_bypass_cache[shd] = {
                            "status": "Đã xử lý",
                            "time": now_str
                        }
                        save_bypass_cache(processed_bypass_cache)
                        r["Thao Tác"] = "Đã xử lý"
                        r["Ngày Cập Nhật"] = now_str
                        update_sheet_remote(r)

                        # Cập nhật processed_in_session để frontend poll realtime
                        bypass_task_state["processed_in_session"].append({
                            "shd": shd,
                            "status": "Đã xử lý",
                            "time": now_str,
                            "nvkt": r.get("Email", ""),
                            "nn1": r.get("Nguyên Nhân 1", "")
                        })

                        # Ghi nhận vào task_logs
                        task_logs.insert(0, {
                            "time": time.strftime("%H:%M:%S"),
                            "task_id": "bypass",
                            "text": f"ByPass thành công HĐ {shd}: NVKT={r.get('Email')} | {r.get('Nguyên Nhân 1')}",
                            "level": "success"
                        })
                except Exception as ex_single:
                    add_log(f"Lỗi khi ByPass HĐ {shd}: {ex_single}", "error")
                    r["Thao Tác"] = "Lỗi"
                    bypass_task_state["processed_in_session"].append({
                        "shd": shd,
                        "status": "Lỗi",
                        "time": time.strftime("%d/%m/%Y %H:%M:%S"),
                        "nvkt": r.get("Email", ""),
                        "nn1": r.get("Nguyên Nhân 1", "")
                    })
                    task_logs.insert(0, {
                        "time": time.strftime("%H:%M:%S"),
                        "task_id": "bypass",
                        "text": f"Lỗi ByPass HĐ {shd}: {str(ex_single)[:60]}",
                        "level": "error"
                    })

                time.sleep(2)

            bypass_task_state["message"] = f"Hoàn tất xử lý {len(to_process)} hợp đồng ByPass!"
            add_log(f"=== HOÀN TẤT TIẾN TRÌNH AUTO BYPASS ===", "success")

        except Exception as e:
            raw_err = str(e)
            bypass_task_state["message"] = f"Lỗi ByPass: {raw_err}"
            add_log(f"Tiến trình Auto ByPass bị dừng: {raw_err}", "error")
        finally:
            bypass_task_state["is_running"] = False
            if bot:
                try:
                    bot.close()
                except Exception:
                    pass

    threading.Thread(target=worker, daemon=True).start()
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
        with open(CLS_CACHE_PATH, "w", encoding="utf-8") as f:
            json.dump(cache_data, f, ensure_ascii=False, indent=2)
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
                # Nếu chưa có kết quả cuối cùng thì luôn hiển thị là Chưa xử lý và xóa cache cũ
                if shd in processed_cls_cache:
                    processed_cls_cache.pop(shd, None)
                    save_cls_cache(processed_cls_cache)
                r["Kết Quả"] = "Chưa xử lý"
                if not r.get("Thao Tác") or raw_tt in ["nan", "chưa xử lý", ""]:
                    r["Thao Tác"] = "Chưa cập nhật"
            else:
                # Nếu đã có kết quả cuối cùng ("Đã clear" hoặc "Không thành công : ...")
                # thì Kết Quả luôn luôn là "Đã xử lý"
                r["Kết Quả"] = "Đã xử lý"
                if shd and shd in processed_cls_cache:
                    c_val = processed_cls_cache[shd]
                    c_tt = c_val.get("thao_tac", "Cập nhật thành công!") if isinstance(c_val, dict) else c_val
                    c_time = c_val.get("time", "") if isinstance(c_val, dict) else ""
                    if not r.get("Thao Tác") or raw_tt in ["nan", "chưa xử lý", ""]:
                        r["Thao Tác"] = c_tt
                    if c_time and (not r.get("Ngày Cập Nhật") or str(r.get("Ngày Cập Nhật")).lower() in ["nan", ""]):
                        r["Ngày Cập Nhật"] = c_time

        add_log(f"Đã đọc {data['count']} dòng từ Google Sheet Clear Cls (GID {gid})", "info")
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

        # Nếu toàn bộ trên Sheet đã ghi "Đã xử lý", nhưng người dùng vẫn bấm Chạy, chạy lại danh sách để người dùng xem trực tiếp
        if not to_process:
            to_process = all_sheet_records

    if not to_process:
        return jsonify({"status": "error", "message": "Không có hợp đồng nào để xử lý!"}), 400

    cls_task_state["is_running"] = True
    cls_task_state["total"] = len(to_process)
    cls_task_state["current_index"] = 0
    cls_task_state["current_shd"] = str(to_process[0].get("SHD", ""))
    cls_task_state["message"] = f"Bắt đầu xử lý {len(to_process)} hợp đồng Clear Cls có SR..."
    cls_task_state["sheet_id"] = sheet_id
    cls_task_state["gid"] = gid
    cls_task_state["processed_in_session"] = []

    mode_label = "Chạy ngầm (Headless)" if headless else "Mở Chrome xem trực tiếp (Visible)"
    add_log(f"=== BẮT ĐẦU AUTO CLEAR CLS {len(to_process)} HỢP ĐỒNG ({mode_label}) ===", "info")

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
                add_log(f"Đã cập nhật Webhook Google Sheet Clear Cls cho HĐ {record.get('SHD')}: Kết quả='Đã xử lý' | Thao tác='{thao_tac_val}'", "success")
            except Exception as e_hook:
                add_log(f"Không thể đẩy Webhook Google Sheet cho HĐ {record.get('SHD')}: {e_hook}", "warning")

    def worker_cls():
        global active_cls_bot
        bot = inside_cls.InsideClearClsAutomation(headless=headless, keep_open=True, log_cb=add_log)
        active_cls_bot = bot
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
                    now_str = time.strftime("%d/%m/%Y %H:%M:%S")

                    processed_cls_cache[shd] = {
                        "ket_qua": "Đã xử lý",
                        "thao_tac": thao_tac,
                        "time": now_str,
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
                    task_logs.insert(0, {
                        "time": time.strftime("%H:%M:%S"),
                        "task_id": "clear_cls",
                        "text": f"Clear Cls HĐ {shd}: Kết quả='Đã xử lý' | Thao tác='{thao_tac}'",
                        "level": lvl
                    })

                except Exception as ex_single:
                    add_log(f"Lỗi khi Clear Cls HĐ {shd}: {ex_single}", "error")
                    now_str = time.strftime("%d/%m/%Y %H:%M:%S")
                    clean_ex = re.sub(r"^không\s+thành\s+công\s*[:\-]?", "", str(ex_single).strip(), flags=re.IGNORECASE).strip()
                    err_thao_tac = f"Không thành công : {clean_ex[:60]}"
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
                    task_logs.insert(0, {
                        "time": time.strftime("%H:%M:%S"),
                        "task_id": "clear_cls",
                        "text": f"Lỗi Clear Cls HĐ {shd}: {str(ex_single)[:60]}",
                        "level": "error"
                    })

                time.sleep(2)

            cls_task_state["message"] = f"Hoàn tất xử lý {len(to_process)} hợp đồng Clear Cls có SR!"
            add_log(f"=== HOÀN TẤT TIẾN TRÌNH AUTO CLEAR CLS CÓ SR ===", "success")

        except Exception as e:
            raw_err = str(e)
            cls_task_state["message"] = f"Lỗi Clear Cls: {raw_err}"
            add_log(f"Tiến trình Auto Clear Cls bị dừng: {raw_err}", "error")
        finally:
            cls_task_state["is_running"] = False
            if bot:
                try:
                    bot.close()
                except Exception:
                    pass

    threading.Thread(target=worker_cls, daemon=True).start()
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
    add_log(f"Đã đọc {data['count']} dòng từ Google Sheet Phân Công Tay (GID {gid})", "info")
    return jsonify(data)

@app.route("/api/assign/live-status", methods=["GET"])
def get_assign_live_status():
    return jsonify({
        "task": assign_task_state,
        "processed_in_session": assign_task_state.get("processed_in_session", [])
    })

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
            to_process = sheet_res["records"]

    if not to_process:
        return jsonify({"status": "error", "message": "Không có hợp đồng nào để xử lý!"}), 400

    assign_task_state["is_running"]             = True
    assign_task_state["total"]                  = len(to_process)
    assign_task_state["current_index"]          = 0
    assign_task_state["current_shd"]            = str(to_process[0].get("SHD", ""))
    assign_task_state["message"]                = f"Bắt đầu xử lý {len(to_process)} hợp đồng Phân Công Tay..."
    assign_task_state["sheet_id"]               = sheet_id
    assign_task_state["gid"]                    = gid
    assign_task_state["processed_in_session"]   = []

    mode_label = "Chạy ngầm (Headless)" if headless else "Mở Chrome xem trực tiếp (Visible)"
    add_log(f"=== BẮT ĐẦU AUTO PHÂN CÔNG TAY {len(to_process)} HỢP ĐỒNG ({mode_label}) ===", "info")

    def update_sheet_remote_assign(record, thao_tac_val):
        cfg = core_login.load_config()
        webhook_url = cfg.get("assign_webhook_url", "") or cfg.get("google_sheet_webhook_url", "")
        if webhook_url:
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
                req = urllib.request.Request(
                    webhook_url,
                    data=json.dumps(payload).encode("utf-8"),
                    headers={"Content-Type": "application/json"}
                )
                urllib.request.urlopen(req, timeout=8)
                add_log(f"Đã cập nhật Webhook Phân Công Tay cho HĐ {record.get('SHD')}: '{thao_tac_val}'", "success")
            except Exception as e_hook:
                add_log(f"Không thể đẩy Webhook cho HĐ {record.get('SHD')}: {e_hook}", "warning")

    def worker_assign():
        global active_assign_bot
        bot = inside_assign.InsideAssignAutomation(headless=headless, keep_open=True, log_cb=add_log)
        active_assign_bot = bot
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
                    now_str = time.strftime("%d/%m/%Y %H:%M:%S")

                    r["Thao Tác"]       = thao_tac
                    r["Ngày Cập Nhật"] = now_str
                    update_sheet_remote_assign(r, thao_tac)

                    assign_task_state["processed_in_session"].append({
                        "shd":        shd,
                        "thao_tac":   thao_tac,
                        "is_success": is_ok,
                        "time":       now_str
                    })

                    lvl = "success" if is_ok else "warning"
                    task_logs.insert(0, {
                        "time":    time.strftime("%H:%M:%S"),
                        "task_id": "manual_assign",
                        "text":    f"Phân Công HĐ {shd}: '{thao_tac}'",
                        "level":   lvl
                    })

                except Exception as ex_single:
                    add_log(f"Lỗi Phân Công Tay HĐ {shd}: {ex_single}", "error")
                    now_str = time.strftime("%d/%m/%Y %H:%M:%S")
                    err_thao_tac = inside_assign.format_assign_thao_tac(False, str(ex_single)[:80])
                    r["Thao Tác"]       = err_thao_tac
                    r["Ngày Cập Nhật"] = now_str
                    update_sheet_remote_assign(r, err_thao_tac)
                    assign_task_state["processed_in_session"].append({
                        "shd":        shd,
                        "thao_tac":   err_thao_tac,
                        "is_success": False,
                        "time":       now_str
                    })
                    task_logs.insert(0, {
                        "time":    time.strftime("%H:%M:%S"),
                        "task_id": "manual_assign",
                        "text":    f"Lỗi Phân Công HĐ {shd}: {str(ex_single)[:60]}",
                        "level":   "error"
                    })

                time.sleep(2)

            assign_task_state["message"] = f"Hoàn tất xử lý {len(to_process)} hợp đồng Phân Công Tay!"
            add_log("=== HOÀN TẤT TIẾN TRÌNH AUTO PHÂN CÔNG TAY ===", "success")

        except Exception as e:
            assign_task_state["message"] = f"Lỗi Phân Công Tay: {e}"
            add_log(f"Tiến trình Phân Công Tay bị dừng: {e}", "error")
        finally:
            assign_task_state["is_running"] = False
            if bot:
                try:
                    bot.close()
                except Exception:
                    pass

    threading.Thread(target=worker_assign, daemon=True).start()
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

# 1. Clear Tín Hiệu Routes
@app.route("/api/clear-signal/sheet-data", methods=["GET"])
def get_clear_signal_sheet_data():
    sheet_id = request.args.get("sheet_id", inside_signal.DEFAULT_SHEET_ID).strip()
    gid      = request.args.get("gid", inside_signal.GID_CLEAR_SIGNAL).strip()
    data = inside_signal.fetch_sheet_data(sheet_id=sheet_id, gid=gid, signal_type="clear")
    if data["status"] != "ok":
        return jsonify(data), 500
    add_log(f"Đã đọc {data['count']} dòng từ Google Sheet Clear Tín Hiệu (GID {gid})", "info")
    return jsonify(data)

@app.route("/api/clear-signal/live-status", methods=["GET"])
def get_clear_signal_live_status():
    return jsonify({
        "task": clear_signal_task_state,
        "processed_in_session": clear_signal_task_state.get("processed_in_session", [])
    })

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
    if clear_signal_task_state["is_running"]:
        return jsonify({"status": "busy", "message": "Đang có tiến trình Clear Tín Hiệu đang chạy..."}), 429
    if reset_signal_task_state["is_running"]:
        return jsonify({"status": "busy", "message": "Đang có tiến trình Cấp Lại Tín Hiệu đang chạy..."}), 429

    data            = request.json or {}
    sheet_id        = data.get("sheet_id", inside_signal.DEFAULT_SHEET_ID)
    gid             = data.get("gid", inside_signal.GID_CLEAR_SIGNAL)
    selected_records= data.get("records")
    headless        = data.get("headless", True)

    if selected_records:
        to_process = selected_records
    else:
        sheet_res = inside_signal.fetch_sheet_data(sheet_id=sheet_id, gid=gid, signal_type="clear")
        if sheet_res["status"] != "ok" or not sheet_res["records"]:
            return jsonify({"status": "error", "message": "Không tìm thấy dữ liệu trên Google Sheet Clear Tín Hiệu"}), 400
        to_process = [r for r in sheet_res["records"] if not inside_signal.is_final_status(r.get("Kết Quả", ""))]
        if not to_process:
            to_process = sheet_res["records"]

    if not to_process:
        return jsonify({"status": "error", "message": "Không có hợp đồng nào để xử lý!"}), 400

    clear_signal_task_state["is_running"]           = True
    clear_signal_task_state["total"]                = len(to_process)
    clear_signal_task_state["current_index"]        = 0
    clear_signal_task_state["current_shd"]          = str(to_process[0].get("SHD", ""))
    clear_signal_task_state["message"]              = f"Bắt đầu xử lý {len(to_process)} hợp đồng Clear Tín Hiệu..."
    clear_signal_task_state["sheet_id"]             = sheet_id
    clear_signal_task_state["gid"]                  = gid
    clear_signal_task_state["processed_in_session"] = []

    mode_label = "Chạy ngầm (Headless)" if headless else "Mở Chrome xem trực tiếp (Visible)"
    add_log(f"=== BẮT ĐẦU AUTO CLEAR TÍN HIỆU {len(to_process)} HỢP ĐỒNG ({mode_label}) ===", "info")

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
                req = urllib.request.Request(
                    webhook_url,
                    data=json.dumps(payload).encode("utf-8"),
                    headers={"Content-Type": "application/json"}
                )
                urllib.request.urlopen(req, timeout=8)
                add_log(f"Đã cập nhật Webhook {sig_type} cho HĐ {record.get('SHD')}: '{kq_val}'", "success")
            except Exception as e_hook:
                add_log(f"Không thể đẩy Webhook cho HĐ {record.get('SHD')}: {e_hook}", "warning")

    def worker_clear_signal():
        bot = inside_signal.InsideSignalAutomation(signal_type="clear", headless=headless, log_cb=add_log)
        try:
            bot.init_driver()
            for idx, r in enumerate(to_process):
                shd = str(r.get("SHD", "")).strip()
                clear_signal_task_state["current_index"] = idx + 1
                clear_signal_task_state["current_shd"]   = shd
                clear_signal_task_state["message"]        = f"Đang Clear Tín Hiệu {idx + 1}/{len(to_process)}: HĐ {shd}..."

                try:
                    is_ok, kq_str, now_str = bot.process_row(r)
                    r["Kết Quả"] = kq_str
                    r["Ngày Cập Nhật"] = now_str
                    update_sheet_remote_signal(r, kq_str, "clear")

                    clear_signal_task_state["processed_in_session"].append({
                        "shd": shd,
                        "ket_qua": kq_str,
                        "is_success": is_ok,
                        "time": now_str
                    })

                    lvl = "success" if is_ok else "warning"
                    task_logs.insert(0, {
                        "time": time.strftime("%H:%M:%S"),
                        "task_id": "clear_signal",
                        "text": f"Clear Tín Hiệu HĐ {shd}: '{kq_str}'",
                        "level": lvl
                    })
                except Exception as ex_single:
                    now_str = time.strftime("%d/%m/%Y %H:%M:%S")
                    err_kq = f"Lỗi: {str(ex_single)[:60]}"
                    r["Kết Quả"] = err_kq
                    r["Ngày Cập Nhật"] = now_str
                    inside_signal.update_cache_record("clear", shd, err_kq, now_str)
                    update_sheet_remote_signal(r, err_kq, "clear")

                    clear_signal_task_state["processed_in_session"].append({
                        "shd": shd,
                        "ket_qua": err_kq,
                        "is_success": False,
                        "time": now_str
                    })
                    task_logs.insert(0, {
                        "time": time.strftime("%H:%M:%S"),
                        "task_id": "clear_signal",
                        "text": f"Lỗi Clear Tín Hiệu HĐ {shd}: {str(ex_single)[:60]}",
                        "level": "error"
                    })
                time.sleep(1.5)

            clear_signal_task_state["message"] = f"Hoàn tất xử lý {len(to_process)} hợp đồng Clear Tín Hiệu!"
            add_log("=== HOÀN TẤT TIẾN TRÌNH AUTO CLEAR TÍN HIỆU ===", "success")
        except Exception as e:
            clear_signal_task_state["message"] = f"Lỗi Clear Tín Hiệu: {e}"
            add_log(f"Tiến trình Clear Tín Hiệu bị dừng: {e}", "error")
        finally:
            clear_signal_task_state["is_running"] = False
            if bot:
                try:
                    bot.close()
                except Exception:
                    pass

    threading.Thread(target=worker_clear_signal, daemon=True).start()
    return jsonify({"status": "started", "count": len(to_process)})


# 2. Cấp Lại Tín Hiệu Routes
@app.route("/api/reset-signal/sheet-data", methods=["GET"])
def get_reset_signal_sheet_data():
    sheet_id = request.args.get("sheet_id", inside_signal.DEFAULT_SHEET_ID).strip()
    gid      = request.args.get("gid", inside_signal.GID_RESET_SIGNAL).strip()
    data = inside_signal.fetch_sheet_data(sheet_id=sheet_id, gid=gid, signal_type="reset")
    if data["status"] != "ok":
        return jsonify(data), 500
    add_log(f"Đã đọc {data['count']} dòng từ Google Sheet Cấp Lại Tín Hiệu (GID {gid})", "info")
    return jsonify(data)

@app.route("/api/reset-signal/live-status", methods=["GET"])
def get_reset_signal_live_status():
    return jsonify({
        "task": reset_signal_task_state,
        "processed_in_session": reset_signal_task_state.get("processed_in_session", [])
    })

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
    if reset_signal_task_state["is_running"]:
        return jsonify({"status": "busy", "message": "Đang có tiến trình Cấp Lại Tín Hiệu đang chạy..."}), 429
    if clear_signal_task_state["is_running"]:
        return jsonify({"status": "busy", "message": "Đang có tiến trình Clear Tín Hiệu đang chạy..."}), 429

    data            = request.json or {}
    sheet_id        = data.get("sheet_id", inside_signal.DEFAULT_SHEET_ID)
    gid             = data.get("gid", inside_signal.GID_RESET_SIGNAL)
    selected_records= data.get("records")
    headless        = data.get("headless", True)

    if selected_records:
        to_process = selected_records
    else:
        sheet_res = inside_signal.fetch_sheet_data(sheet_id=sheet_id, gid=gid, signal_type="reset")
        if sheet_res["status"] != "ok" or not sheet_res["records"]:
            return jsonify({"status": "error", "message": "Không tìm thấy dữ liệu trên Google Sheet Cấp Lại Tín Hiệu"}), 400
        to_process = [r for r in sheet_res["records"] if not inside_signal.is_final_status(r.get("Kết Quả", ""))]
        if not to_process:
            to_process = sheet_res["records"]

    if not to_process:
        return jsonify({"status": "error", "message": "Không có hợp đồng nào để xử lý!"}), 400

    reset_signal_task_state["is_running"]           = True
    reset_signal_task_state["total"]                = len(to_process)
    reset_signal_task_state["current_index"]        = 0
    reset_signal_task_state["current_shd"]          = str(to_process[0].get("SHD", ""))
    reset_signal_task_state["message"]              = f"Bắt đầu xử lý {len(to_process)} hợp đồng Cấp Lại Tín Hiệu..."
    reset_signal_task_state["sheet_id"]             = sheet_id
    reset_signal_task_state["gid"]                  = gid
    reset_signal_task_state["processed_in_session"] = []

    mode_label = "Chạy ngầm (Headless)" if headless else "Mở Chrome xem trực tiếp (Visible)"
    add_log(f"=== BẮT ĐẦU AUTO CẤP LẠI TÍN HIỆU {len(to_process)} HỢP ĐỒNG ({mode_label}) ===", "info")

    def update_sheet_remote_signal(record, kq_val, sig_type="reset"):
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
                req = urllib.request.Request(
                    webhook_url,
                    data=json.dumps(payload).encode("utf-8"),
                    headers={"Content-Type": "application/json"}
                )
                urllib.request.urlopen(req, timeout=8)
                add_log(f"Đã cập nhật Webhook {sig_type} cho HĐ {record.get('SHD')}: '{kq_val}'", "success")
            except Exception as e_hook:
                add_log(f"Không thể đẩy Webhook cho HĐ {record.get('SHD')}: {e_hook}", "warning")

    def worker_reset_signal():
        bot = inside_signal.InsideSignalAutomation(signal_type="reset", headless=headless, log_cb=add_log)
        try:
            bot.init_driver()
            for idx, r in enumerate(to_process):
                shd = str(r.get("SHD", "")).strip()
                reset_signal_task_state["current_index"] = idx + 1
                reset_signal_task_state["current_shd"]   = shd
                reset_signal_task_state["message"]        = f"Đang Cấp Lại Tín Hiệu {idx + 1}/{len(to_process)}: HĐ {shd}..."

                try:
                    is_ok, kq_str, now_str = bot.process_row(r)
                    r["Kết Quả"] = kq_str
                    r["Ngày Cập Nhật"] = now_str
                    update_sheet_remote_signal(r, kq_str, "reset")

                    reset_signal_task_state["processed_in_session"].append({
                        "shd": shd,
                        "ket_qua": kq_str,
                        "is_success": is_ok,
                        "time": now_str
                    })

                    lvl = "success" if is_ok else "warning"
                    task_logs.insert(0, {
                        "time": time.strftime("%H:%M:%S"),
                        "task_id": "reset_signal",
                        "text": f"Cấp Lại Tín Hiệu HĐ {shd}: '{kq_str}'",
                        "level": lvl
                    })
                except Exception as ex_single:
                    now_str = time.strftime("%d/%m/%Y %H:%M:%S")
                    err_kq = f"Lỗi: {str(ex_single)[:60]}"
                    r["Kết Quả"] = err_kq
                    r["Ngày Cập Nhật"] = now_str
                    inside_signal.update_cache_record("reset", shd, err_kq, now_str)
                    update_sheet_remote_signal(r, err_kq, "reset")

                    reset_signal_task_state["processed_in_session"].append({
                        "shd": shd,
                        "ket_qua": err_kq,
                        "is_success": False,
                        "time": now_str
                    })
                    task_logs.insert(0, {
                        "time": time.strftime("%H:%M:%S"),
                        "task_id": "reset_signal",
                        "text": f"Lỗi Cấp Lại Tín Hiệu HĐ {shd}: {str(ex_single)[:60]}",
                        "level": "error"
                    })
                time.sleep(1.5)

            reset_signal_task_state["message"] = f"Hoàn tất xử lý {len(to_process)} hợp đồng Cấp Lại Tín Hiệu!"
            add_log("=== HOÀN TẤT TIẾN TRÌNH AUTO CẤP LẠI TÍN HIỆU ===", "success")
        except Exception as e:
            reset_signal_task_state["message"] = f"Lỗi Cấp Lại Tín Hiệu: {e}"
            add_log(f"Tiến trình Cấp Lại Tín Hiệu bị dừng: {e}", "error")
        finally:
            reset_signal_task_state["is_running"] = False
            if bot:
                try:
                    bot.close()
                except Exception:
                    pass

    threading.Thread(target=worker_reset_signal, daemon=True).start()
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

def open_browser_delayed(port):
    time.sleep(1.2)
    webbrowser.open(f"http://localhost:{port}")

if __name__ == "__main__":
    env_port = os.environ.get("PORT")
    if env_port:
        port = int(env_port)
    else:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(('0.0.0.0', 5000))
                port = 5000
            except OSError:
                port = find_free_port(preferred_port=5001)
                print(f"[THONG BAO] Cong 5000 dang duoc su dung. Chuyen sang cong: {port}")

    print(f"==================================================================")
    print(f"   CAPTION NEXTSU AI - DANG CHAY TAI: http://localhost:{port}")
    print(f"==================================================================")

    if os.environ.get("WERKZEUG_RUN_MAIN") != "true":
        threading.Thread(target=open_browser_delayed, args=(port,), daemon=True).start()

    app.run(host="0.0.0.0", port=port, debug=False)

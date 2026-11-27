"""
Cấu hình riêng cho package auto_hoan_tat (không phụ thuộc/không sửa config của hệ thống cũ).
Không lưu mật khẩu, token hay bí mật trong file này.
"""

from dataclasses import dataclass, field
import json
import os
import sys
from typing import Tuple

if getattr(sys, "frozen", False):
    RESOURCE_DIR = os.path.join(getattr(sys, "_MEIPASS", os.path.dirname(sys.executable)), "auto_hoan_tat")
    PACKAGE_DIR = os.path.join(os.path.dirname(sys.executable), "auto_hoan_tat_data")
else:
    RESOURCE_DIR = os.path.dirname(os.path.abspath(__file__))
    PACKAGE_DIR = RESOURCE_DIR

DEFAULT_SETTINGS_PATH = os.path.join(PACKAGE_DIR, "settings.json")

DEFAULT_SHEET_ID = "1Sw-qSbLzvVdcW4rj7ywEZBEzKI6w5M82EQeYJUpdx7M"
DEFAULT_SHEET_GID = "1668046687"


@dataclass
class AutoHoanTatSettings:
    enabled: bool = True
    sheet_id: str = DEFAULT_SHEET_ID
    sheet_gid: str = DEFAULT_SHEET_GID
    sheet_timeout_sec: int = 12
    dry_run_default: bool = True
    rate_limit_sec: float = 2.0
    max_consecutive_errors: int = 3
    standalone_port: int = 5002
    task_lock_name: str = "auto_hoan_tat"
    main_server_overview_url: str = "http://127.0.0.1:5001/api/auto/overview"
    # Giá trị phân loại PTC / PBT theo cột Tác Vụ (chuẩn hóa NFC, bỏ khoảng trắng thừa, không phân biệt hoa thường)
    ptc_values: Tuple[str, ...] = ("TRIỂN KHAI",)
    pbt_values: Tuple[str, ...] = ("BẢO TRÌ", "XÁC MINH THÔNG TIN")
    write_sheet_webhook: bool = False
    webhook_url: str = ""
    auto_enabled: bool = False
    auto_scan_interval_sec: int = 10
    log_dir: str = field(default_factory=lambda: os.path.join(PACKAGE_DIR, "logs"))
    probe_output_dir: str = field(default_factory=lambda: os.path.join(PACKAGE_DIR, "probe_output"))


def _parse_bool(val, default=True) -> bool:
    if isinstance(val, bool):
        return val
    if val is None:
        return default
    s = str(val).strip().lower()
    if s in ("1", "true", "yes", "on", "bat", "bật"):
        return True
    if s in ("0", "false", "no", "off", "tat", "tắt"):
        return False
    return default


def load_settings(settings_path: str = DEFAULT_SETTINGS_PATH) -> AutoHoanTatSettings:
    """Nạp cấu hình từ settings.json (nếu có) và ghi đè bằng biến môi trường."""
    cfg = AutoHoanTatSettings()
    if settings_path and os.path.exists(settings_path):
        try:
            with open(settings_path, "r", encoding="utf-8") as f:
                raw = json.load(f)
            if isinstance(raw, dict):
                if "enabled" in raw:
                    cfg.enabled = _parse_bool(raw["enabled"], cfg.enabled)
                if raw.get("sheet_id"):
                    cfg.sheet_id = str(raw["sheet_id"]).strip()
                if raw.get("sheet_gid"):
                    cfg.sheet_gid = str(raw["sheet_gid"]).strip()
                if "sheet_timeout_sec" in raw:
                    cfg.sheet_timeout_sec = max(3, int(raw["sheet_timeout_sec"]))
                if "dry_run_default" in raw:
                    cfg.dry_run_default = _parse_bool(raw["dry_run_default"], True)
                if "rate_limit_sec" in raw:
                    cfg.rate_limit_sec = max(0.0, float(raw["rate_limit_sec"]))
                if "max_consecutive_errors" in raw:
                    cfg.max_consecutive_errors = max(1, int(raw["max_consecutive_errors"]))
                if "standalone_port" in raw:
                    cfg.standalone_port = int(raw["standalone_port"])
                if isinstance(raw.get("ptc_values"), list):
                    cfg.ptc_values = tuple(str(x).strip().lower() for x in raw["ptc_values"] if str(x).strip())
                if isinstance(raw.get("pbt_values"), list):
                    cfg.pbt_values = tuple(str(x).strip().lower() for x in raw["pbt_values"] if str(x).strip())
                if "write_sheet_webhook" in raw:
                    cfg.write_sheet_webhook = _parse_bool(raw["write_sheet_webhook"], False)
                if "webhook_url" in raw:
                    cfg.webhook_url = str(raw["webhook_url"] or "").strip()
                if "auto_enabled" in raw:
                    cfg.auto_enabled = _parse_bool(raw["auto_enabled"], False)
                if "auto_scan_interval_sec" in raw:
                    cfg.auto_scan_interval_sec = max(5, int(raw["auto_scan_interval_sec"]))
        except Exception:
            pass

    if "AUTO_HOAN_TAT_ENABLED" in os.environ:
        cfg.enabled = _parse_bool(os.environ.get("AUTO_HOAN_TAT_ENABLED"), cfg.enabled)
    if "AUTO_HOAN_TAT_DRY_RUN" in os.environ:
        cfg.dry_run_default = _parse_bool(os.environ.get("AUTO_HOAN_TAT_DRY_RUN"), cfg.dry_run_default)

    return cfg


def save_settings(updates: dict, settings_path: str = DEFAULT_SETTINGS_PATH) -> AutoHoanTatSettings:
    """Lưu cấu hình an toàn (không chứa mật khẩu/token) vào auto_hoan_tat/settings.json."""
    existing = {}
    if settings_path and os.path.exists(settings_path):
        try:
            with open(settings_path, "r", encoding="utf-8") as f:
                raw = json.load(f)
            if isinstance(raw, dict):
                existing = raw
        except Exception:
            existing = {}

    allowed_keys = {
        "enabled",
        "sheet_id",
        "sheet_gid",
        "dry_run_default",
        "rate_limit_sec",
        "max_consecutive_errors",
        "write_sheet_webhook",
        "webhook_url",
        "auto_enabled",
        "auto_scan_interval_sec",
    }
    for k, v in (updates or {}).items():
        if k in allowed_keys:
            existing[k] = v

    os.makedirs(os.path.dirname(settings_path), exist_ok=True)
    with open(settings_path, "w", encoding="utf-8") as f:
        json.dump(existing, f, ensure_ascii=False, indent=2)
    return load_settings(settings_path)


def is_enabled(settings_path: str = DEFAULT_SETTINGS_PATH) -> bool:
    """Kiểm tra cờ bật/tắt chức năng Auto Hoàn Tất PTC/PBT."""
    return load_settings(settings_path).enabled

"""Cau hinh Auto Import cho du an Data Retrieval Tool.

Chi doc file .env trong thu muc Data Retrieval Tool (khong tro cheo sang Tool KPI).
"""

from __future__ import annotations

import datetime
import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple


BASE_DIR = Path(__file__).resolve().parent
ENV_FILE = BASE_DIR / ".env"
TOOL_KPI_BACKEND_DIR = Path(r"D:\Tool KPI\backend")

DOWNLOAD_ROOT_DIR = BASE_DIR / "tmp_auto_import"
LOG_DIR = BASE_DIR / "logs"
AUDIT_LOG_FILE = LOG_DIR / "auto_import_audit.jsonl"

LOCK_TABLE = "auto_import_locks"
AUDIT_TABLE = "auto_import_logs"

LOCK_TTL_SECONDS = 1800
MAX_LOGIN_ATTEMPTS = 2
MAX_CRAWL_RETRIES = 1
REPORT_LOAD_TIMEOUT_SECONDS = 90
DOWNLOAD_TIMEOUT_SECONDS = 120

PROTECTED_PROD_TABLES = frozenset(
    {"tk", "bt", "cll30n", "ton_tk", "ton_bt", "hr", "lt", "_system_flags"}
)


def load_local_env(env_path: Path = ENV_FILE) -> None:
    """Doc file .env cuc bo cua Data Retrieval Tool vao os.environ (khong ghi de bien da co)."""
    if not env_path.exists():
        return
    with env_path.open("r", encoding="utf-8") as f:
        for raw_line in f:
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, val = line.split("=", 1)
            key = key.strip()
            val = val.strip().strip("'\"")
            if key and key not in os.environ:
                os.environ[key] = val


load_local_env()


def _parse_bool(val: Optional[str], default: bool = False) -> bool:
    if val is None:
        return default
    return str(val).strip().lower() in {"1", "true", "yes", "on"}


def is_auto_import_enabled() -> bool:
    """Feature flag AUTO_IMPORT_ENABLED, mac dinh False."""
    load_local_env()
    return _parse_bool(os.environ.get("AUTO_IMPORT_ENABLED"), default=False)


def get_db_url() -> str:
    """Lay chuoi ket noi Supabase tu .env / env cua Data Retrieval Tool."""
    load_local_env()
    url = (
        os.environ.get("SUPABASE_DB_URL", "").strip()
        or os.environ.get("DATABASE_URL", "").strip()
    )
    if not url or "[YOUR-PASSWORD]" in url:
        raise RuntimeError(
            "Chua cau hinh SUPABASE_DB_URL / DATABASE_URL hop le trong .env cua Data Retrieval Tool."
        )
    return url


def _parse_partners(raw: Optional[str], default_partners: List[str]) -> List[str]:
    if not raw:
        return list(default_partners)
    items = [p.strip() for p in raw.split(",") if p.strip()]
    return items or list(default_partners)


def get_dataset_config(dataset: str = "tk") -> Dict:
    """Tra ve cau hinh cho dataset. Giai doan 1 chi ho tro dataset 'tk'."""
    load_local_env()
    ds = str(dataset or "").strip().lower()
    configs: Dict[str, Dict] = {
        "tk": {
            "dataset": "tk",
            "label": "Data Triển Khai (TK)",
            "prod_table": "tk",
            "target_table": os.environ.get("AUTO_IMPORT_TK_TABLE", "tk_auto_test").strip()
            or "tk_auto_test",
            "default_filters": {
                "vung_mien": os.environ.get("AUTO_IMPORT_VUNG_MIEN", "07.Hồ Chí Minh").strip(),
                "tinh_thanh": os.environ.get("AUTO_IMPORT_TINH_THANH", "Hồ Chí Minh").strip(),
                "doi_tac": os.environ.get("AUTO_IMPORT_DEFAULT_PARTNER", "Phương Nam-01").strip(),
                "tab_name": "TRIỂN KHAI",
                "xem_theo": os.environ.get("AUTO_IMPORT_XEM_THEO", "Hoàn tất phiếu thi công").strip(),
                "loai_bao_cao": os.environ.get(
                    "AUTO_IMPORT_LOAI_BAO_CAO", "Báo cáo đúng hẹn - đúng hạn"
                ).strip(),
                "thuoc_tinh_nhan_vien": os.environ.get("AUTO_IMPORT_THUOC_TINH_NV", "Chính").strip(),
                "bao_cao_theo": os.environ.get("AUTO_IMPORT_BAO_CAO_THEO", "Block").strip(),
            },
            "allowed_partners": _parse_partners(
                os.environ.get("AUTO_IMPORT_PARTNERS"),
                ["Phương Nam-01"],
            ),
        }
    }
    if ds not in configs:
        raise ValueError(
            f"Dataset '{dataset}' chua duoc ho tro trong giai doan 1 (chi ho tro: {list(configs.keys())})."
        )
    return configs[ds]


def get_default_date_range(today: Optional[datetime.date] = None) -> Tuple[str, str]:
    """Khoang ngay mac dinh: tu ngay 01 dau thang den hom nay (dd/mm/YYYY)."""
    ref = today or datetime.date.today()
    first_day = ref.replace(day=1)
    return first_day.strftime("%d/%m/%Y"), ref.strftime("%d/%m/%Y")


def validate_date_str(date_str: str) -> datetime.date:
    """Kiem tra dinh dang ngay dd/mm/YYYY."""
    return datetime.datetime.strptime(date_str.strip(), "%d/%m/%Y").date()

"""Service & CLI Auto Import dataset 'tk' vao Supabase (khong sua code Tool KPI).

Tai su dung cac ham read-only / chuan hoa / ghi Supabase cua KPIEngine
thong qua KPIEngine.__new__(KPIEngine) de tranh side effect cua __init__.
"""

from __future__ import annotations

import argparse
import datetime
import json
import sys
import threading
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
from sqlalchemy import text as sa_text

from auto_import_config import (
    AUDIT_LOG_FILE,
    AUDIT_TABLE,
    LOCK_TABLE,
    LOCK_TTL_SECONDS,
    LOG_DIR,
    PROTECTED_PROD_TABLES,
    TOOL_KPI_BACKEND_DIR,
    get_dataset_config,
    get_db_url,
    get_default_date_range,
    is_auto_import_enabled,
    validate_date_str,
)
from inside_report_crawler import fetch_tk_report_excel, validate_downloaded_tk_excel


class LockBusyError(RuntimeError):
    """Bao hieu dataset dang duoc giu lock boi tien trinh khac."""


def _import_kpi_engine_class():
    backend_str = str(TOOL_KPI_BACKEND_DIR)
    if backend_str not in sys.path:
        sys.path.insert(0, backend_str)
    from engine import KPIEngine

    return KPIEngine


def create_readonly_kpi_engine(db_url: Optional[str] = None):
    """Khoi tao KPIEngine khong chay __init__ -> 0 side effect len cache/Sheet/hr."""
    KPIEngine = _import_kpi_engine_class()
    eng = KPIEngine.__new__(KPIEngine)
    eng.DATABASE_URL = db_url or get_db_url()
    eng._db_engine = None
    eng._db_engine_url = None
    eng._sp_save_lock = threading.Lock()
    return eng


def ensure_infra_tables(db_engine) -> None:
    """Tao bang lock & audit log moi tren Supabase (khong dung bang cu)."""
    ddl_locks = f"""
    CREATE TABLE IF NOT EXISTS "{LOCK_TABLE}" (
        dataset TEXT PRIMARY KEY,
        owner_id TEXT NOT NULL,
        acquired_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        expires_at TIMESTAMPTZ NOT NULL
    )
    """
    ddl_logs = f"""
    CREATE TABLE IF NOT EXISTS "{AUDIT_TABLE}" (
        id BIGSERIAL PRIMARY KEY,
        timestamp TIMESTAMPTZ NOT NULL,
        dataset TEXT NOT NULL,
        source TEXT NOT NULL,
        dry_run BOOLEAN NOT NULL,
        target_table TEXT NOT NULL,
        rows_read INTEGER NOT NULL,
        rows_new INTEGER NOT NULL,
        rows_duplicate INTEGER NOT NULL,
        error_count INTEGER NOT NULL,
        status TEXT NOT NULL,
        message TEXT
    )
    """
    with db_engine.begin() as conn:
        conn.execute(sa_text(ddl_locks))
        conn.execute(sa_text(ddl_logs))


def acquire_db_lock(
    db_engine,
    dataset: str,
    owner_id: str,
    ttl_seconds: int = LOCK_TTL_SECONDS,
) -> None:
    """Giu lock muc DB tuong thich Supabase pooler 6543 (Transaction Mode)."""
    sql = sa_text(
        f"""
        INSERT INTO "{LOCK_TABLE}" (dataset, owner_id, acquired_at, expires_at)
        VALUES (:ds, :owner, NOW(), NOW() + (:ttl * INTERVAL '1 second'))
        ON CONFLICT (dataset) DO UPDATE
        SET owner_id = EXCLUDED.owner_id,
            acquired_at = EXCLUDED.acquired_at,
            expires_at = EXCLUDED.expires_at
        WHERE "{LOCK_TABLE}".expires_at < NOW()
        """
    )
    with db_engine.begin() as conn:
        res = conn.execute(sql, {"ds": dataset, "owner": owner_id, "ttl": int(ttl_seconds)})
        if res.rowcount != 1:
            raise LockBusyError(
                f"Dataset '{dataset}' dang bi khoa boi mot luot auto-import khac (chua het TTL)."
            )


def release_db_lock(db_engine, dataset: str, owner_id: str) -> None:
    """Nha lock neu thuoc ve owner_id hien tai."""
    sql = sa_text(
        f'DELETE FROM "{LOCK_TABLE}" WHERE dataset = :ds AND owner_id = :owner'
    )
    with db_engine.begin() as conn:
        conn.execute(sql, {"ds": dataset, "owner": owner_id})


def force_unlock_db(dataset: str = "tk", db_url: Optional[str] = None) -> Dict[str, Any]:
    """Xoa lock bi treo trong bang auto_import_locks (chi tac dong bang lock moi)."""
    cfg = get_dataset_config(dataset)
    eng = create_readonly_kpi_engine(db_url=db_url)
    db_engine = eng.get_db_engine()
    if db_engine is None:
        raise RuntimeError("Khong ket noi duoc Supabase.")
    ensure_infra_tables(db_engine)
    sql = sa_text(f'DELETE FROM "{LOCK_TABLE}" WHERE dataset = :ds')
    with db_engine.begin() as conn:
        res = conn.execute(sql, {"ds": cfg["dataset"]})
    return {"ok": True, "dataset": cfg["dataset"], "released": int(res.rowcount or 0)}


def write_audit_log(record: Dict[str, Any], db_engine=None) -> None:
    """Ghi audit log vao ca file JSONL cuc bo va bang Supabase auto_import_logs."""
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    with AUDIT_LOG_FILE.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")

    if db_engine is None:
        return
    try:
        sql = sa_text(
            f"""
            INSERT INTO "{AUDIT_TABLE}" (
                timestamp, dataset, source, dry_run, target_table,
                rows_read, rows_new, rows_duplicate, error_count, status, message
            ) VALUES (
                :timestamp, :dataset, :source, :dry_run, :target_table,
                :rows_read, :rows_new, :rows_duplicate, :error_count, :status, :message
            )
            """
        )
        with db_engine.begin() as conn:
            conn.execute(sql, record)
    except Exception as exc:
        print(f"[WARN] Khong ghi duoc audit log len Supabase: {exc}", flush=True)


def validate_and_parse_tk_file(
    eng, file_bytes: bytes, filename: str
) -> Tuple[pd.DataFrame, str, str]:
    """Ap dung dung quy tac doc file, guard & cot bat buoc cua KPIEngine cho tk."""
    df_incoming = eng._read_any_dataframe(file_bytes, filename)
    if df_incoming is None or df_incoming.empty:
        raise ValueError(f"File '{filename}' rong hoac khong doc duoc du lieu.")

    cols_lower = [str(c).strip().lower() for c in df_incoming.columns]
    col_hd = eng._get_required_col(df_incoming, ["Số hợp đồng", "Số HĐ", "so_hd"])
    col_nv = eng._get_required_col(df_incoming, ["Nhân viên", "Nhân sự", "nhan_vien"])

    # Cross-dataset guard BT -> TK (y nguyen engine.py)
    bt_signature_cols = ["ttscbđ", "tg hoàn tất", "tg tạo", "tồn giờ", "hạn còn lại"]
    tk_signature_cols = [
        "tg tạo ptc",
        "ngày tạo ptc",
        "tg hoàn tất ptc",
        "loại triển khai",
        "tin/pnc",
        "ptc",
    ]
    has_bt_sig = any(m in cols_lower for m in bt_signature_cols)
    has_tk_sig = any(m in cols_lower for m in tk_signature_cols)
    if has_bt_sig and not has_tk_sig:
        raise ValueError(
            "Cross-Dataset Guard: File mang dac trung Bao Tri (BT), tu choi nap vao Trien Khai (TK)."
        )

    missing_cols: List[str] = []
    if not col_hd:
        missing_cols.append("Số hợp đồng")
    if not col_nv:
        missing_cols.append("Nhân viên")
    col_dh = eng._get_required_col(df_incoming, ["Đúng hẹn", "dung_hen", "Đúng Hẹn"])
    if not col_dh:
        missing_cols.append("Đúng hẹn (cột xác định kết quả đúng/trễ hẹn)")
    if missing_cols:
        raise ValueError(
            f"Thieu cac cot bat buoc cua TK: [{', '.join(missing_cols)}]."
        )

    sample_hds = df_incoming[col_hd].dropna().astype(str).str.strip()
    if sample_hds.empty or (sample_hds.str.len() < 3).all():
        raise ValueError(
            "Cot 'Số hợp đồng' trong file rong hoac tat ca gia tri duoi 3 ky tu."
        )

    return df_incoming, col_hd, col_nv


def merge_tk_with_existing(
    eng,
    df_incoming: pd.DataFrame,
    existing_df: pd.DataFrame,
    col_hd: str,
    col_nv: str,
) -> Tuple[pd.DataFrame, int, int, int]:
    """Loc trung 5 cot va enrich dung logic MERGE_NO_OVERWRITE cua KPIEngine."""
    total_incoming = len(df_incoming)
    if existing_df is None or existing_df.empty:
        merged_df = eng._enrich_tk_df(df_incoming)
        return merged_df, total_incoming, total_incoming, 0

    ex_hd = eng._find_col(existing_df, ["Số hợp đồng", "Số HĐ"], default_idx=0)
    ex_nv = eng._find_col(existing_df, ["Nhân viên", "Nhân sự"], default_idx=1)
    ex_tg_ptc = eng._find_col(
        existing_df, ["TG tạo PTC", "Ngày tạo PTC", "TG Tạo PTC"], default_idx=None
    )
    ex_ht_ptc = eng._find_col(
        existing_df, ["Ngày hoàn tất PTC", "TG hoàn tất PTC", "TG Hoàn Tất PTC"], default_idx=None
    )
    ex_loai_gd = eng._find_col(
        existing_df, ["Loại giao dịch", "Loại Giao Dịch", "loai_giao_dich"], default_idx=None
    )

    def _make_key(df_ref: pd.DataFrame, row, c_hd, c_nv, c_ptc, c_ht, c_loai) -> str:
        hd = str(row[c_hd]).strip().upper() if c_hd else ""
        nv = str(row[c_nv]).strip().upper() if c_nv else ""
        ptc = str(row[c_ptc]).strip() if c_ptc and c_ptc in df_ref.columns else ""
        ht = str(row[c_ht]).strip() if c_ht and c_ht in df_ref.columns else ""
        loai = str(row[c_loai]).strip().upper() if c_loai and c_loai in df_ref.columns else ""
        return f"{hd}||{nv}||{ptc}||{ht}||{loai}"

    existing_keys = set(
        existing_df.apply(
            lambda r: _make_key(existing_df, r, ex_hd, ex_nv, ex_tg_ptc, ex_ht_ptc, ex_loai_gd),
            axis=1,
        )
    )

    col_tg_ptc = eng._find_col(
        df_incoming, ["TG tạo PTC", "Ngày tạo PTC", "TG Tạo PTC"], default_idx=None
    )
    col_ht_ptc = eng._find_col(
        df_incoming, ["Ngày hoàn tất PTC", "TG hoàn tất PTC", "TG Hoàn Tất PTC"], default_idx=None
    )
    col_loai_gd = eng._find_col(
        df_incoming, ["Loại giao dịch", "Loại Giao Dịch", "loai_giao_dich"], default_idx=None
    )

    incoming_keys = df_incoming.apply(
        lambda r: _make_key(df_incoming, r, col_hd, col_nv, col_tg_ptc, col_ht_ptc, col_loai_gd),
        axis=1,
    )
    new_rows = df_incoming[~incoming_keys.isin(existing_keys)].copy()
    added_count = len(new_rows)
    skipped_count = total_incoming - added_count

    if added_count == 0:
        return existing_df, total_incoming, 0, skipped_count

    merged_df = pd.concat([existing_df, new_rows], ignore_index=True)
    merged_df = eng._enrich_tk_df(merged_df)
    return merged_df, total_incoming, added_count, skipped_count


def seed_test_table(
    dataset: str = "tk",
    target_table: Optional[str] = None,
    db_url: Optional[str] = None,
) -> Dict[str, Any]:
    """Sao chep du lieu tu bang production (chi doc) sang bang test (vd tk_auto_test)."""
    cfg = get_dataset_config(dataset)
    dest_table = (target_table or cfg["target_table"]).strip()
    if dest_table.lower() in PROTECTED_PROD_TABLES:
        raise ValueError(
            f"Tu choi --seed-test-table: '{dest_table}' la bang production duoc bao ve."
        )

    eng = create_readonly_kpi_engine(db_url=db_url)
    db_engine = eng.get_db_engine()
    if db_engine is None:
        raise RuntimeError("Khong ket noi duoc Supabase.")

    prod_table = cfg["prod_table"]
    df_prod = eng._load_df_from_supabase(prod_table)
    if df_prod is None or df_prod.empty:
        raise RuntimeError(f"Bang nguon '{prod_table}' rong hoac khong doc duoc.")

    ok = eng._save_df_to_supabase(df_prod, dest_table)
    if not ok:
        raise RuntimeError(f"Ghi du lieu seed sang '{dest_table}' that bai.")

    return {
        "ok": True,
        "source_table": prod_table,
        "target_table": dest_table,
        "rows_seeded": len(df_prod),
    }


def run_auto_import(
    dataset: str = "tk",
    dry_run: bool = False,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    partners: Optional[List[str]] = None,
    target_table: Optional[str] = None,
    input_file: Optional[str] = None,
    headless: bool = False,
    db_url: Optional[str] = None,
) -> Dict[str, Any]:
    """Chay 1 luot Auto Import hoan chinh voi lock DB, validate & audit log."""
    ts_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
    cfg = get_dataset_config(dataset)
    dest_table = (target_table or cfg["target_table"]).strip()
    source_desc = f"local_file:{input_file}" if input_file else "inside.fpt.net"

    default_from, default_to = get_default_date_range()
    eff_from = (from_date or default_from).strip()
    eff_to = (to_date or default_to).strip()

    record: Dict[str, Any] = {
        "timestamp": ts_iso,
        "dataset": cfg["dataset"],
        "source": source_desc,
        "dry_run": bool(dry_run),
        "target_table": cfg["prod_table"] if dry_run else dest_table,
        "rows_read": 0,
        "rows_new": 0,
        "rows_duplicate": 0,
        "error_count": 0,
        "status": "FAILED",
        "message": "",
    }

    eng = None
    db_engine = None
    lock_acquired = False
    owner_id = f"{uuid.uuid4().hex}"

    try:
        if not is_auto_import_enabled():
            record["status"] = "SKIPPED_DISABLED"
            record["message"] = "Feature flag AUTO_IMPORT_ENABLED=false. Bo qua khong chay."
            write_audit_log(record, db_engine=None)
            return record

        validate_date_str(eff_from)
        validate_date_str(eff_to)
        if validate_date_str(eff_from) > validate_date_str(eff_to):
            raise ValueError(f"Khoang ngay khong hop le: {eff_from} > {eff_to}")

        eng = create_readonly_kpi_engine(db_url=db_url)
        db_engine = eng.get_db_engine()
        if db_engine is None:
            raise RuntimeError("Khong ket noi duoc Supabase.")

        ensure_infra_tables(db_engine)
        acquire_db_lock(db_engine, cfg["dataset"], owner_id, ttl_seconds=LOCK_TTL_SECONDS)
        lock_acquired = True

        # 1. Lay file dau vao (tu file local neu --input-file, hoac crawl Inside theo tung doi tac)
        parsed_frames: List[pd.DataFrame] = []
        col_hd_ref = ""
        col_nv_ref = ""

        if input_file:
            p = Path(input_file)
            if not p.exists():
                raise FileNotFoundError(f"Khong tim thay file dau vao: {p}")
            file_bytes = p.read_bytes()
            ok_v, msg_v = validate_downloaded_tk_excel(file_bytes, p.name)
            if not ok_v:
                raise ValueError(msg_v)
            df_part, col_hd_ref, col_nv_ref = validate_and_parse_tk_file(eng, file_bytes, p.name)
            parsed_frames.append(df_part)
        else:
            partner_list = partners or cfg["allowed_partners"]
            for partner in partner_list:
                file_bytes, fname = fetch_tk_report_excel(
                    from_date=eff_from,
                    to_date=eff_to,
                    partner=partner,
                    filters=cfg["default_filters"],
                    headless=headless,
                )
                df_part, col_hd_ref, col_nv_ref = validate_and_parse_tk_file(
                    eng, file_bytes, fname
                )
                parsed_frames.append(df_part)

        df_incoming_all = (
            pd.concat(parsed_frames, ignore_index=True)
            if len(parsed_frames) > 1
            else parsed_frames[0]
        )

        # 2. Tai du lieu hien co (dry-run doc bang tk that o che do read-only)
        compare_table = cfg["prod_table"] if dry_run else dest_table
        existing_raw = eng._load_df_from_supabase(compare_table)
        existing_df = (
            eng._enrich_tk_df(existing_raw)
            if existing_raw is not None and not existing_raw.empty
            else pd.DataFrame()
        )

        # 3. Loc trung 5 cot & enrich
        merged_df, rows_read, rows_new, rows_dup = merge_tk_with_existing(
            eng, df_incoming_all, existing_df, col_hd_ref, col_nv_ref
        )
        record["rows_read"] = rows_read
        record["rows_new"] = rows_new
        record["rows_duplicate"] = rows_dup

        # 4. Ghi Supabase (bo qua neu dry-run hoac rows_new == 0)
        if dry_run:
            record["status"] = "DRY_RUN_OK"
            record["message"] = (
                f"Dry-run doi chieu '{compare_table}' thanh cong: "
                f"doc {rows_read}, moi {rows_new}, trung {rows_dup} (khong ghi)."
            )
        elif rows_new == 0:
            record["status"] = "OK_NO_NEW_ROWS"
            record["message"] = (
                f"Khong co dong moi (doc {rows_read}, trung {rows_dup}). Bo qua ghi '{dest_table}'."
            )
        else:
            ok_save = eng._save_df_to_supabase(merged_df, dest_table)
            if not ok_save:
                raise RuntimeError(f"Ghi du lieu vao bang '{dest_table}' that bai.")
            record["status"] = "OK"
            record["message"] = (
                f"Import thanh cong vao '{dest_table}': "
                f"doc {rows_read}, moi {rows_new}, trung {rows_dup}, tong sau gop {len(merged_df)}."
            )

        write_audit_log(record, db_engine=db_engine)
        return record

    except Exception as exc:
        record["error_count"] = 1
        record["status"] = "LOCKED" if isinstance(exc, LockBusyError) else "FAILED"
        record["message"] = str(exc)
        write_audit_log(record, db_engine=db_engine)
        return record
    finally:
        if lock_acquired and db_engine is not None:
            try:
                release_db_lock(db_engine, cfg["dataset"], owner_id)
            except Exception as exc:
                print(f"[WARN] Khong nha duoc DB lock: {exc}", flush=True)


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Auto Import Data Trien Khai (tk) tu Inside FPT vao Supabase."
    )
    parser.add_argument("--dataset", default="tk", help="Ten dataset (mac dinh: tk)")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Chay kiem tra & doi chieu read-only voi bang tk that, khong ghi du lieu.",
    )
    parser.add_argument("--from-date", default=None, help="Tu ngay dd/mm/YYYY")
    parser.add_argument("--to-date", default=None, help="Den ngay dd/mm/YYYY")
    parser.add_argument(
        "--partners",
        default=None,
        help="Danh sach doi tac phan tach bang dau phay (vd: 'Phương Nam-01')",
    )
    parser.add_argument(
        "--target-table",
        default=None,
        help="Ten bang Supabase dich (mac dinh doc tu config: tk_auto_test)",
    )
    parser.add_argument(
        "--input-file",
        default=None,
        help="Duong dan file .xlsx co san (bo qua buoc mo trinh duyet crawl Inside).",
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Chay Chrome an (phu hop khi gan Windows Task Scheduler).",
    )
    parser.add_argument(
        "--seed-test-table",
        action="store_true",
        help="Sao chep du lieu tu bang tk production (read-only) sang bang test.",
    )
    parser.add_argument(
        "--unlock",
        action="store_true",
        help="Giai phong lock bi treo trong bang auto_import_locks cho dataset.",
    )
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = _build_arg_parser()
    args = parser.parse_args(argv)

    if args.unlock:
        res = force_unlock_db(dataset=args.dataset)
        print(json.dumps(res, ensure_ascii=False, indent=2))
        return 0

    if args.seed_test_table:
        res = seed_test_table(dataset=args.dataset, target_table=args.target_table)
        print(json.dumps(res, ensure_ascii=False, indent=2))
        return 0

    partner_list = (
        [p.strip() for p in args.partners.split(",") if p.strip()]
        if args.partners
        else None
    )
    res = run_auto_import(
        dataset=args.dataset,
        dry_run=args.dry_run,
        from_date=args.from_date,
        to_date=args.to_date,
        partners=partner_list,
        target_table=args.target_table,
        input_file=args.input_file,
        headless=args.headless,
    )
    print(json.dumps(res, ensure_ascii=False, indent=2))
    return 0 if res.get("status") in {"OK", "OK_NO_NEW_ROWS", "DRY_RUN_OK", "SKIPPED_DISABLED"} else 1


if __name__ == "__main__":
    sys.exit(main())

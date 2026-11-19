"""
Đọc và chuẩn hóa dữ liệu từ Google Sheet GID 1668046687 (hoặc file CSV fixture cục bộ).
- Luôn chuẩn hóa Unicode NFC cho toàn bộ tên cột và giá trị ô.
- Ánh xạ 14 cột đã được xác nhận sang các trường nghiệp vụ chuẩn.
- Phân loại PTC/PBT dựa vào cột Tác Vụ theo cấu hình; giá trị lạ/rỗng -> loai = None (không tự đoán).
- Chỉ ĐỌC, tuyệt đối không ghi lên Google Sheet thật.
"""

import csv
import io
import time
import unicodedata
import urllib.request
from typing import Dict, List, Optional, Tuple

from .config import AutoHoanTatSettings, load_settings


def normalize_nfc(value) -> str:
    """Chuẩn hóa chuỗi về dạng Unicode NFC và cắt khoảng trắng hai đầu."""
    if value is None:
        return ""
    text = unicodedata.normalize("NFC", str(value)).strip()
    if text.lower() == "nan":
        return ""
    return text


def _strip_accents_lower(text: str) -> str:
    nfkd = unicodedata.normalize("NFD", normalize_nfc(text))
    no_tone = "".join(ch for ch in nfkd if unicodedata.category(ch) != "Mn")
    return " ".join(no_tone.replace("đ", "d").replace("Đ", "D").lower().split())


# Bản đồ tên cột (sau chuẩn hóa bỏ dấu + chữ thường) -> trường nghiệp vụ chuẩn
COLUMN_TO_FIELD: Dict[str, str] = {
    "id": "row_id",
    "tac vu": "tac_vu",
    "email": "email_nvkt",
    "msnv": "msnv",
    "account inside": "account_inside",
    "shd": "shd",
    "nguyen nhan": "nguyen_nhan",
    "hinh anh": "hinh_anh",
    "ngay cap nhat": "ngay_cap_nhat",
    "ket qua": "ket_qua",
    "location": "location",
    "address of location": "address_of_location",
    "dia chi kh": "dia_chi_kh",
    "danh gia xac thuc": "danh_gia_xac_thuc",
}


def _norm_match_key(text: str) -> str:
    """Chuẩn hóa NFC, gộp khoảng trắng thừa và chuyển chữ thường để so khớp chính xác."""
    return " ".join(normalize_nfc(text).split()).lower()


def classify_ticket_type(
    tac_vu: str,
    ptc_values: Tuple[str, ...],
    pbt_values: Tuple[str, ...],
) -> Tuple[Optional[str], Optional[str], str]:
    """
    Phân loại phiếu thành ('PTC', 'TRIỂN KHAI') hoặc ('PBT', 'BẢO TRÌ') dựa vào cột Tác Vụ.
    So khớp sau khi chuẩn hóa NFC, bỏ khoảng trắng thừa, không phân biệt hoa thường.
    Không đoán nếu giá trị rỗng hoặc không khớp danh sách cấu hình.
    Trả về (loai_phieu, tab_dich, ly_do_neu_khong_xac_dinh).
    """
    raw = " ".join(normalize_nfc(tac_vu).split())
    if not raw:
        return None, None, "Cột Tác Vụ bị trống, không xác định được loại PTC/PBT"

    key = _norm_match_key(raw)
    ptc_keys = {_norm_match_key(v) for v in ptc_values if _norm_match_key(v)}
    pbt_keys = {_norm_match_key(v) for v in pbt_values if _norm_match_key(v)}

    is_ptc = key in ptc_keys
    is_pbt = key in pbt_keys

    if is_ptc and not is_pbt:
        return "PTC", "TRIỂN KHAI", ""
    if is_pbt and not is_ptc:
        return "PBT", "BẢO TRÌ", ""
    return None, None, f"Giá trị cột Tác Vụ không hợp lệ/chưa khai báo: '{raw}'"


def parse_csv_text(
    csv_text: str,
    settings: Optional[AutoHoanTatSettings] = None,
) -> Dict:
    """Phân tích nội dung CSV thành danh sách bản ghi chuẩn hóa NFC."""
    cfg = settings or load_settings()
    reader = csv.DictReader(io.StringIO(csv_text.lstrip("\ufeff")))
    raw_headers = reader.fieldnames or []
    nfc_headers = [normalize_nfc(h) for h in raw_headers]

    header_map: Dict[str, str] = {}
    for orig, nfc_h in zip(raw_headers, nfc_headers):
        field = COLUMN_TO_FIELD.get(_strip_accents_lower(nfc_h))
        if field:
            header_map[orig] = field

    records: List[Dict] = []
    for row in reader:
        rec: Dict = {field: "" for field in COLUMN_TO_FIELD.values()}
        raw_nfc: Dict[str, str] = {}
        for orig_k, orig_v in row.items():
            if orig_k is None:
                continue
            k_nfc = normalize_nfc(orig_k)
            v_nfc = normalize_nfc(orig_v)
            raw_nfc[k_nfc] = v_nfc
            mapped = header_map.get(orig_k)
            if mapped:
                rec[mapped] = v_nfc

        # Bỏ qua dòng hoàn toàn trống
        if not any(rec.values()):
            continue

        loai, tab_dich, loai_ly_do = classify_ticket_type(rec["tac_vu"], cfg.ptc_values, cfg.pbt_values)
        rec["ma_phieu"] = rec["shd"]
        rec["loai"] = loai
        rec["tab_dich"] = tab_dich
        rec["loai_ly_do"] = loai_ly_do
        rec["raw"] = raw_nfc
        records.append(rec)

    return {
        "status": "ok",
        "columns": nfc_headers,
        "count": len(records),
        "records": records,
    }


def fetch_sheet_from_file(
    csv_path: str,
    settings: Optional[AutoHoanTatSettings] = None,
) -> Dict:
    """Đọc dữ liệu từ file CSV cục bộ (dùng cho test / fixture)."""
    try:
        with open(csv_path, "r", encoding="utf-8") as f:
            content = f.read()
        result = parse_csv_text(content, settings=settings)
        result["source"] = csv_path
        return result
    except Exception as exc:
        return {
            "status": "error",
            "message": f"Không thể đọc file CSV '{csv_path}': {exc}",
            "columns": [],
            "count": 0,
            "records": [],
        }


def fetch_sheet_data(
    sheet_id: Optional[str] = None,
    gid: Optional[str] = None,
    settings: Optional[AutoHoanTatSettings] = None,
) -> Dict:
    """Đọc trực tiếp Google Sheet GID 1668046687 (có timeout tránh treo vô hạn)."""
    cfg = settings or load_settings()
    sid = (sheet_id or cfg.sheet_id).strip()
    sgid = (gid or cfg.sheet_gid).strip()
    url = (
        f"https://docs.google.com/spreadsheets/d/{sid}/gviz/tq"
        f"?tqx=out:csv&gid={sgid}&_t={int(time.time() * 1000)}"
    )
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=cfg.sheet_timeout_sec) as resp:
            content = resp.read().decode("utf-8", errors="ignore")
        result = parse_csv_text(content, settings=cfg)
        result["source"] = url
        return result
    except Exception as exc:
        return {
            "status": "error",
            "message": f"Không thể đọc Google Sheet (GID={sgid}): {exc}",
            "columns": [],
            "count": 0,
            "records": [],
        }

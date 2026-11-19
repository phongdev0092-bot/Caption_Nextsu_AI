"""
Điểm khởi chạy Giao diện Web độc lập (Phương án A - cổng 5002) cho Auto Hoàn Tất PTC/PBT.
Cách chạy:
    python -m auto_hoan_tat.run_standalone
"""

from .config import load_settings
from .web_app import create_app


def main() -> None:
    cfg = load_settings()
    app = create_app(settings=cfg)
    print(f"=== Auto Hoan Tat PTC/PBT (Standalone) ===")
    print(f"Mo trinh duyet tai: http://127.0.0.1:{cfg.standalone_port}")
    print(f"Trang thai co enabled={cfg.enabled} | Mac dinh DRY-RUN={cfg.dry_run_default}")
    app.run(host="127.0.0.1", port=cfg.standalone_port, debug=False, use_reloader=False)


if __name__ == "__main__":
    main()

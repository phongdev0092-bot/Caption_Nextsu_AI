"""
Giao diện Web độc lập (cổng 5002) cho "Auto Hoàn Tất PTC/PBT".
Dùng chung hoàn toàn Blueprint với server.py để tránh lặp code.
"""

from typing import Callable, Optional

from flask import Flask

from .blueprint import create_blueprint
from .config import AutoHoanTatSettings
from .orchestrator import run_batch
from .sheet_reader import fetch_sheet_data


def create_app(
    settings: Optional[AutoHoanTatSettings] = None,
    sheet_fetcher: Callable = fetch_sheet_data,
    batch_runner: Callable = run_batch,
) -> Flask:
    app = Flask(__name__)
    bp = create_blueprint(
        settings=settings,
        sheet_fetcher=sheet_fetcher,
        batch_runner=batch_runner,
        api_prefix="",
    )
    app.register_blueprint(bp, url_prefix="")
    return app

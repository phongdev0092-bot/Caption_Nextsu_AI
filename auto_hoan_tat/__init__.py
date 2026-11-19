"""
Package cô lập cho chức năng "Auto Hoàn Tất PTC/PBT".
- Không sửa bất kỳ file nào của hệ thống hiện hành.
- Có thể bật/tắt hoàn toàn qua biến môi trường AUTO_HOAN_TAT_ENABLED hoặc auto_hoan_tat/settings.json.
- Xóa thư mục auto_hoan_tat/ thì hệ thống cũ vẫn hoạt động bình thường.
"""

from .config import is_enabled, load_settings

__all__ = ["is_enabled", "load_settings"]

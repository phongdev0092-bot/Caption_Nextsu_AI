# Quy Tắc Phân Quyền Admin (Admin Privileges Rule)

## Nguồn Dữ Liệu Phân Quyền Admin
- **Google Sheet ID**: `17QLc9SlfpPPrR-d1R2BkBxA7DmCI5ZCuhmQffP5F6pY`
- **GID**: `32204814`
- **Cột phân quyền**: Cột `AD` (`Roles`, index 29)
- **Các cột định danh nhân sự**:
  - Cột `F` (`Mã NV` / `MSNV`, so khớp cả dạng có và không có số `0` ở đầu, ví dụ `00110827` và `110827`)
  - Cột `G` (`Inside Account` / `Account Inside`, ví dụ `PNC01.PHONGNH5`)
  - Cột `K` (`Email`, ví dụ `phuongnam.PhongNH5@fpt.net`)

## Quy Tắc Thực Thi
1. **Không giới hạn quyền hoặc chức năng đối với Admin**:
   - Bất kỳ nhân sự nào có giá trị cột `AD` (`Roles`) là `Admin` trên Sheet `17QLc9SlfpPPrR-d1R2BkBxA7DmCI5ZCuhmQffP5F6pY` (GID `32204814`) đều **không bị giới hạn bất kỳ quyền nào hoặc bị chặn bởi các điều kiện giới hạn chức năng**.
2. **Miễn trừ điều kiện ByPass 14N vi phạm Hậu Kiểm**:
   - Khi thực hiện chức năng **ByPass** (cả chế độ Tự Động và Chạy Lẻ), nếu nhân sự yêu cầu (`Email`, `Account Inside`, hoặc `MSNV`) thuộc nhóm `Roles = Admin`, hệ thống **bỏ qua hoàn toàn** bước kiểm tra vi phạm Hậu Kiểm Không Đạt trong 14 ngày (`check_14d_hau_kiem_violation`) và cho phép thực hiện ByPass bình thường.
3. **Áp dụng cho các tính năng mới trong tương lai**:
   - Mọi quy tắc giới hạn hạn mức, tần suất, hoặc điều kiện chặn theo lịch sử nhân sự khi thêm mới vào hệ thống đều phải kiểm tra `is_admin_staff()` và miễn trừ cho `Admin`.

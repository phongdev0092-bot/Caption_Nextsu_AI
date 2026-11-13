# FPT Data Retrieval Tool - Sidebar UI (Tailwind & MUI) & Auto Công Việc

Hệ thống tự động hóa khai thác dữ liệu hợp đồng, quản lý tiến trình công việc và phiếu thi công từ **inside.fpt.net** với giao diện **Sidebar hiện đại phong cách Tailwind CSS & Google Material Design (MUI)**.

---

## 🎨 Giao diện & Tính năng mới:

1. **Bố cục dạng SIDEBAR chuyên nghiệp**:
   * Sidebar điều hướng cố định bên trái, hỗ trợ thu gọn/mở rộng linh hoạt (Collapsible Drawer).
   * Tích hợp Tailwind CSS & Google Material UI: thẻ KPI trực quan, gradient tinh tế, font Google Sans sắc nét.
   * Thẻ quản lý tài khoản & theo dõi trạng thái phiên Inside FPT ngay trên sidebar.

2. **Tab "Auto Công Việc" (Auto Workflow Engine)**:
   * **Trung tâm kịch bản tự động**: Quét & cập nhật Phiếu Thi Công (PTC), tự động đồng bộ Import, rà soát cảnh báo chậm hạn và sao lưu nén Zstandard.
   * **Công tắc Switch On/Off**: Bật/tắt kịch bản tự động chỉ bằng một cú nhấp.
   * **Thực thi tức thì**: Nút *Chạy ngay* cho từng kịch bản.
   * **Tùy biến kịch bản**: Hỗ trợ thêm kịch bản mới với tần suất linh hoạt (5p, 15p, 30p, 1h, hàng ngày).
   * **Live Task Console**: Nhật ký sự kiện thời gian thực theo dõi tiến trình chạy ngầm.

3. **Auto Lấy Thông Tin (Retrieval)**:
   * Trích xuất thông tin khách hàng, số điện thoại, gói dịch vụ, vật tư và phiếu thi công gần nhất.
   * Bộ nhớ nén Zstandard (.json.zst) tối ưu dung lượng và tự động lọc trùng 48h.

4. **Auto Import**:
   * Đối soát và đẩy danh sách dữ liệu lên Inside FPT tự động.

---

## 🚀 Hướng dẫn sử dụng:

### 1. Khởi động ứng dụng

* **Cách 1 (Khuyên dùng - Chạy trực tiếp file .EXE)**:
  * Nhấp đúp chuột trực tiếp vào file:
    👉 **[FPT_Data_Retrieval_Tool.exe](file:///d:/Data%20Retrieval%20Tool/FPT_Data_Retrieval_Tool.exe)**
  * Ứng dụng đã được nén thành file thực thi độc lập (.exe duy nhất), tự động bật server và mở trình duyệt web lên mà không cần bất kỳ lệnh hay cài đặt gì thêm.

* **Cách 2 (Chạy qua file Batch)**:
  * Nhấp đúp chuột vào file:
    👉 **[run.bat](file:///d:/Data%20Retrieval%20Tool/run.bat)**

Hệ thống sẽ tự động bật web server trên localhost (cổng `5001` nếu cổng `5000` đang bận) và mở trình duyệt web lên.

### 2. Auto Lấy thông tin
* **Cách 1: Điền 1 hợp đồng**
  * Nhập mã hợp đồng vào ô (mặc định đã điền sẵn `SGAFV2037` để test).
  * Bấm nút **"🚀 Auto Lấy Thông Tin"**.
* **Cách 2: Gán file danh sách HĐ**
  * Chọn tab *Gán file HĐ (.xlsx, .txt)*.
  * Tải file chứa danh sách hợp đồng lên.
  * Bấm **"🚀 Auto Lấy Thông Tin"** để hệ thống tự động chạy lần lượt từng hợp đồng.

### 3. Quản lý 2 Chế Độ Tài Khoản (Mặc định & Tùy chỉnh)
* Bấm vào biểu tượng **⚙️ Cài đặt** (hoặc ô trạng thái tài khoản trên thanh tiêu đề):
  * **Tài khoản Mặc định**: Cố định `phuongnam.phongnh5` / `Benngo@@20262027`, tự động sinh mã OTP từ ảnh QR Google Authenticator.
  * **Tài khoản Tùy chỉnh**: Nhập tên đăng nhập & mật khẩu riêng. Có checkbox tùy chọn bật/tắt OTP (nếu bật có thể tải ảnh QR để quét tự động).
* Bấm **Lưu Cấu Hình** để chọn tài khoản bạn muốn sử dụng khi đăng nhập và tra cứu.

### 4. Xem chi tiết & Xuất Excel
* Bấm nút **"Chi tiết"** ở từng dòng để xem thẻ thông tin đầy đủ và sao chép nhanh.
* Bấm nút **"Xuất Excel"** ở góc phải để tải file bảng tính chứa toàn bộ kết quả.

---

## 🐧 Hướng dẫn sử dụng trên PC Ubuntu / Linux

### 1. Cách mở file dữ liệu trên Ubuntu:
* **Cách 1 (Mở trực tiếp không cần cài đặt)**:
  Ứng dụng đã tự động lưu sẵn bản JSON nguyên bản: [retrieval_history.json](file:///d:/Data%20Retrieval%20Tool/retrieval_history.json). Trên Ubuntu bạn chỉ cần nhấp đúp chuột để mở bằng **Text Editor**, **VS Code**, hoặc bất kỳ trình duyệt nào.
* **Cách 2 (Giải nén file Zstandard `.zst`)**:
  Ubuntu mặc định chưa cài công cụ Zstandard, bạn chỉ cần mở Terminal và gõ:
  ```bash
  sudo apt install zstd -y
  unzstd retrieval_history.json.zst
  ```
  Lệnh trên sẽ giải nén ra file `retrieval_history.json` ngay tức thì.

### 2. Cách chạy ứng dụng trên PC Ubuntu:
1. Giải nén gói mã nguồn: [FPT_Data_Retrieval_Tool_Linux_Ubuntu.zip](file:///d:/Data%20Retrieval%20Tool/FPT_Data_Retrieval_Tool_Linux_Ubuntu.zip).
2. Mở Terminal tại thư mục đó và chạy:
   ```bash
   chmod +x run.sh
   ./run.sh
   ```
   *Script `run.sh` sẽ tự động tạo môi trường ảo Python, cài đặt các thư viện cần thiết và khởi động máy chủ Web.*

---

## 🧩 Cấu trúc component (Frontend)

```
templates/
  index.html                      # CHỈ gắn component + khai báo STUB_TABS
  components/
    layout/   sidebar.html, topbar.html, banner.html, nav_stub_items.html
    tabs/     retrieval.html, import.html, bypass.html, clear_cls.html,
              stub_tab.html (macro khung chung), stub_tabs.html
    modals/   detail.html, create_task.html, settings.html, webhook_guide.html, snackbar.html
static/js/
  core/       dom.js (DOM refs + state), shell.js (session/toast), tabs.js (registerTab/switchTab)
  components/ retrieval.js, login.js, import.js, settings.js, bypass.js, clear_cls.js, stub_tabs.js
  main.js     # khởi tạo + polling (nạp cuối)
```

**Thêm chức năng mới:**
1. Tạo `templates/components/tabs/<ten>.html` (`<section class="tab-panel" id="tab-<ten>">`).
2. Tạo `static/js/components/<ten>.js`, gọi `registerTab('tab-<ten>', {title, onActivate})`.
3. Thêm nút sidebar có `data-tab="tab-<ten>"`, rồi `include` + `<script>` vào `index.html`.

5 tab mới (Phân Công Tay, Bypass MyBAE, Pool/Deactive IPv6, Hoàn Tất PTC/PBT, Cấp/Thu Hồi CCDC) hiện là khung UI sinh từ `STUB_TABS` trong `index.html`; khi làm thật thì tách ra file riêng và xóa khỏi danh sách này.


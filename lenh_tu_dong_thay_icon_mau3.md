# CÂU LỆNH (PROMPT) TỰ ĐỘNG THAY BIỂU TƯỢNG MẪU 3 TOÀN BỘ PHẦN MỀM PABT

> **Hướng dẫn**:
> 1. Nếu bạn muốn dùng ngay bộ tệp biểu tượng Mẫu 3 đã cắt tách nền trong suốt và đóng gói đủ 9 cỡ `.ico`, hãy giải nén `PABT_Icon_Mau3_Chuan_0987.zip` vào thư mục gốc `D:\APP AI PABT\PABT_PhanMem`.
> 2. Sau đó, sao chép toàn bộ câu lệnh trong khung dưới đây và dán vào **Claude Code** để AI tự động cập nhật toàn bộ mã nguồn, hình vẽ dự phòng, thanh tiêu đề, bộ cài đặt và bài kiểm thử tự động.

```markdown
Hãy thay thế và đồng bộ toàn bộ biểu tượng (App Icon) của phần mềm PABT sang thiết kế mới **Mẫu 3: "Lăng Kính Công Lý & Nhịp Cầu Đồng Thuận"** (tông màu tươi sáng: Xanh Lam Băng Sáng `#38BDF8`, Trắng Sứ `#F8FAFC` và Vàng Cam Hổ Phách `#F59E0B`, thay thế hoàn toàn tông xanh navy đậm cũ) trên toàn bộ phần mềm, từ cửa sổ giao diện, thanh tiêu đề, hình vẽ dự phòng, bộ cài đặt đến bài kiểm thử tự động.

Thực hiện chính xác theo 6 bước kỹ thuật dưới đây (tuân thủ 100% quy ước trong `CLAUDE.md`, tương thích cả Python 3.8 Win7 Qt5 và Python 3.14 Win10/11 Qt6):

======================================================================
BƯỚC 1: XỬ LÝ NGUỒN THIẾT KẾ & SINH TÀI NGUYÊN (`tao_bieu_tuong.py`, `pabt/ve_bieu_tuong.py`)
======================================================================
1. Kiểm tra tệp nguồn `pabt/bieu_tuong_thiet_ke.webp` (1024x1024 px):
   - Nếu tệp ảnh Mẫu 3 đã được chép vào `pabt/bieu_tuong_thiet_ke.webp` (hoặc đặt ở thư mục gốc), hãy đảm bảo phần nền trắng bên ngoài viền khung Squircle 3D được tách trong suốt hoàn toàn (`Alpha = 0` ở 4 góc ngoài khung), chỉ giữ lại khối Squircle 3D màu Xanh Băng Sáng (`#38BDF8` / `#E0F2FE`), Nhịp cầu + Cán cân + Dấu tích đồng thuận màu Vàng Cam (`#F59E0B`) và chữ `PABT` trắng viền vàng nổi 3D ở đáy.
   - Nếu chưa có tệp ảnh hoặc cần vẽ/chuẩn hóa lại bằng mã trong `tao_bieu_tuong.py` / `pabt/ve_bieu_tuong.py`: hãy cập nhật hàm dựng biểu tượng để tạo khung Squircle chuẩn trong vùng `KHUNG = (170, 853)` trên nền `1024x1024`, bo góc `BO_GOC`, trong suốt tuyệt đối ngoài góc bo.
2. Chạy quy trình thu nhỏ mượt từng nấc 1/2 (`thu_nho_muot`) bằng `QT_QPA_PLATFORM=windows` để xuất ra đúng 2 tệp đóng gói:
   - `pabt/bieu_tuong.png`: kích thước `512 x 512 px` RGBA sắc nét (dùng cho runtime của cả Qt6 và Qt5 vì Qt5 không cần plugin webp khi đọc png).
   - `pabt/bieu_tuong.ico`: chứa đầy đủ 9 kích thước chuẩn `(16, 20, 24, 32, 40, 48, 64, 128, 256)` — bắt buộc có cỡ `20` và `40` cho màn hình Windows tỷ lệ `125%`.

======================================================================
BƯỚC 2: CẬP NHẬT HÌNH VẼ DỰ PHÒNG `ve_mach` (`pabt/ve_bieu_tuong.py`)
======================================================================
Trong `pabt/ve_bieu_tuong.py`:
- Cập nhật hàm vẽ dự phòng `ve_mach` (dùng `QPainter` khi thiếu tệp `.png`) sang đúng bảng màu tươi sáng của **Mẫu 3**:
  - Nền Squircle: chuyển sắc (gradient) từ Trắng Sứ Băng (`#F0F9FF`) sang Xanh Lam Băng Sáng (`#38BDF8` / `#0284C7`), viền ngoài Trắng Ngọc Trai pha Xanh Băng sáng, tuyệt đối không dùng nền navy đậm `#0F3866` cũ.
  - Họa tiết bên trong: lưới tọa độ CAD sáng mờ, nhịp cầu vòm vàng kim (`#F59E0B`), cán cân công bằng pha lê kèm dấu tích đồng thuận màu cam vàng rực rỡ (`#F97316` -> `#FACC15`), và dòng chữ `PABT` màu trắng viền vàng kim ở phần đế.
- Đảm bảo `giao_dien.bieu_tuong()` gọi `ve_bieu_tuong.icon()` trả về `QIcon` nạp đủ các cỡ từ `pabt/bieu_tuong.png`.

======================================================================
BƯỚC 3: ĐỒNG BỘ MỌI VỊ TRÍ HIỂN THỊ TRÊN GIAO DIỆN (`pabt/thanh_tieu_de.py`, `pabt/giao_dien.py`, `pabt/app.py`)
======================================================================
1. Kiểm tra `pabt/thanh_tieu_de.py` (`ThanhTieuDe`) và `pabt/giao_dien.py` (`tao_banner_ten`, `KhungLogo`, `bang_to_chuc`, `HopGioiThieu`):
   - Đảm bảo ô chứa logo trên thanh tiêu đề (32px) và trên banner / hộp giới thiệu (46px–64px) có nền trong suốt (`background: transparent`), lấy đúng `bieu_tuong().pixmap(...)` theo tỷ lệ màn hình (`devicePixelRatioF`), không vẽ đè khung nền xanh tối hay viền cũ làm mất viền pha lê sáng của Mẫu 3.
2. Kiểm tra `pabt/app.py`:
   - Đảm bảo `dat_app_user_model_id()` được gọi ở đầu `app.main()` TRƯỚC khi tạo `QApplication`.
   - Đảm bảo cả `QApplication.setWindowIcon(giao_dien.bieu_tuong())` và `CuaSoChinh.setWindowIcon(giao_dien.bieu_tuong())` đều được gắn để mọi cửa sổ con (`QDialog`), thanh tiêu đề và nút trên Taskbar Windows đều hiện biểu tượng Mẫu 3.

======================================================================
BƯỚC 4: ĐỒNG BỘ BỘ CÀI ĐẶT, FILE .EXE & GÓI CẬP NHẬT (`PABT.spec`, `bo_cai_win/`)
======================================================================
1. Kiểm tra `PABT.spec` (bản Win10/11 64-bit) và `bo_cai_win/dung_exe38.py` (bản Win7/8 32-bit):
   - Đảm bảo tham số `--icon` trỏ tới `pabt\bieu_tuong.ico`.
   - Đảm bảo `pabt\bieu_tuong.png` có trong danh sách `datas` / `--add-data` và `pabt/bieu_tuong_thiet_ke.webp` KHÔNG bị đóng gói thừa vào bản phát hành.
2. Kiểm tra `bo_cai_win/dung_bo_cai_win.py` và `bo_cai_win/cai_dat.ps1`:
   - Đảm bảo `dung_bo_cai_win.doi_bieu_tuong` nhúng đúng `pabt/bieu_tuong.ico` mới vào vỏ `.exe` của IExpress (`PABT_Setup_Universal_<ver>.exe`).
   - Đảm bảo khi cài đặt, `PABT.ico` mới được chép vào thư mục cài đặt, lối tắt Desktop / Start Menu gắn đúng `System.AppUserModel.ID` (`$APP_ID` trùng với `app.APP_USER_MODEL_ID`), và gọi làm mới bộ đệm biểu tượng Windows (`ie4uinit.exe -show`) để máy người dùng đổi biểu tượng ngay lập tức mà không bị lưu đệm biểu tượng cũ.
3. Kiểm tra `pabt/cap_nhat.py` / `tao_cap_nhat.py`:
   - Đảm bảo `bieu_tuong.png` và `bieu_tuong.ico` nằm trong danh sách tài nguyên của gói cập nhật `.pabtcn` để các máy cập nhật qua `.pabtcn` cũng nhận được biểu tượng Mẫu 3 mới.

======================================================================
BƯỚC 5: CẬP NHẬT BÀI KIỂM THỬ TỰ ĐỘNG (`tests/test_giao_dien.py`)
======================================================================
Mở `tests/test_giao_dien.py` và kiểm tra bài test `test_bieu_tuong_duy_nhat_co_vien`:
- Bản 0.9.81 cũ đang kiểm tra màu nền theo hướng xanh hoàng gia đậm. Với **Mẫu 3 (Xanh Băng Pha Lê Sáng `#38BDF8` + Trắng Sứ + Vàng Cam `#F59E0B`)**, hãy cập nhật điều kiện kiểm tra trong `test_bieu_tuong_duy_nhat_co_vien` sao cho:
  1. Kiểm tra tệp `pabt/bieu_tuong.png` (512x512) và `pabt/bieu_tuong.ico` (đủ các cỡ chuẩn) tồn tại và nạp được qua `giao_dien.bieu_tuong()`.
  2. Kiểm tra 4 góc ngoài cùng `(0, 0)`, `(511, 0)`, `(0, 511)`, `(511, 511)` của `bieu_tuong.png` có `alpha == 0` (trong suốt ngoài góc bo squircle).
  3. Kiểm tra vùng có hình bên trong biểu tượng có **độ sáng trung bình cao (tông tươi sáng, trung bình R+G+B / 3 > 130, hoàn toàn không phải màu navy đậm tối)** và có cả các điểm ảnh tông Xanh Băng Sáng (`B > R` và `G > 140`) lẫn các điểm nhấn Vàng Cam (`R > 180` và `G > 120` và `B < 120`).

======================================================================
BƯỚC 6: CHẠY KIỂM THỬ XÁC NHẬN & DỰNG LẠI BẢN PHÁT HÀNH
======================================================================
1. Chạy tạo biểu tượng:
   `set QT_QPA_PLATFORM=windows` rồi `.venv\Scripts\python tao_bieu_tuong.py`
2. Chạy kiểm thử biểu tượng và giao diện trên cả 2 môi trường:
   - Qt6 (`.venv`): `set QT_QPA_PLATFORM=offscreen` rồi `.venv\Scripts\python -m unittest tests.test_giao_dien -v`
   - Qt5 (`venv38_32` nếu có): chạy `tests.test_giao_dien` để xác nhận Qt5 đọc tốt `bieu_tuong.png`.
3. Nếu tôi yêu cầu đóng gói ngay: chạy `DUNG_EXE.bat` (với `--clean` để PyInstaller xóa cache icon cũ) và `DUNG_CAP_NHAT.bat`, sau đó báo cáo kết quả kiểm tra kích thước, các cỡ trong `.ico` và kết quả chạy test.
```

# MASTER PROMPT: TỔNG RÀ SOÁT, TỐI ƯU HÓA & NÂNG CẤP TOÀN DIỆN PABT (v0.9.87)

> **Hướng dẫn sử dụng**: Sao chép toàn bộ nội dung dưới đây và dán trực tiếp vào **Claude Code** (tại thư mục gốc `D:\APP AI PABT\PABT_PhanMem`). Câu lệnh đã được thiết kế khớp 100% với kiến trúc `CLAUDE.md` và lịch sử `LICH_SU_PHAT_TRIEN.md` để AI tự động thực thi từ khâu kiểm toán mã nguồn, tích hợp tiện ích mới, tối ưu hóa tốc độ xử lý đến kiểm thử đóng gói mà không làm hỏng bất kỳ quy ước cũ nào.

```markdown
Đóng vai trò là Hội đồng Chuyên gia gồm: Kiến trúc sư Phần mềm (Software Architect), Kỹ sư Tối ưu hóa Hiệu năng (Performance Engineer), Kỹ sư Giao diện Qt (UI/UX Engineer), Chuyên gia Nghiệp vụ Bồi thường GPMB (Business Analyst) và Chuyên gia Kiểm định Chất lượng (QA/QC).

Hãy đọc kỹ `CLAUDE.md` (và tham chiếu `LICH_SU_PHAT_TRIEN.md` khi cần tra cứu lịch sử thiết kế) trong thư mục dự án `D:\APP AI PABT\PABT_PhanMem` để thực hiện đợt **Tổng rà soát, Tinh chỉnh, Sửa lỗi và Nâng cấp toàn diện lên phiên bản mới (0.9.87)** theo đúng 5 giai đoạn bắt buộc dưới đây.

======================================================================
I. KỶ LUẬT KIẾN TRÚC BẤT KHẢ XÂM PHẠM (TUYỆT ĐỐI TUÂN THỦ)
======================================================================
1. Tương thích kép Python 3.8 (Win7 32-bit, Qt5 PySide2) & Python 3.14 (Win10/11 64-bit, Qt6 PySide6):
   - Mọi file `.py` bắt buộc có `from __future__ import annotations` ở đầu file và đạt kiểm tra `vermin -t=3.8-`.
   - Tuyệt đối KHÔNG dùng cú pháp/API Python 3.9+ lúc chạy (không dùng `match/case`, không dùng `a | b` cho kiểu ngoài annotation, không dùng `dict1 | dict2`, không dùng `str.removeprefix` / `removesuffix`).
   - Không dùng emoji trên chữ của nút bấm, nhãn, tab (Windows 7 không có phông emoji -> hiện ô vuông); chỉ dùng `giao_dien.icon_ky_hieu` (Segoe Fluent Icons / MDL2).
   - Trong `_qt5_lam_qt6`: giữ nguyên `QMenu.exec = lambda self, *a: self.exec_(*a)` (không gán thẳng `QMenu.exec = QMenu.exec_` vì gây sập 0xC0000005 trên Qt5).
2. Quy ước đặt tên & Kiến trúc:
   - Giữ nguyên cấu trúc thư mục `pabt/` hiện hành (KHÔNG tái cấu trúc sang cây thư mục 4 tầng `pabt_app/`).
   - Mã nguồn, hàm, biến, bảng CSDL viết bằng tiếng Việt không dấu (`ma_ho`, `tinh_pa`, `doi_chieu`).
   - Toàn bộ số tiền, diện tích, số lượng lưu `TEXT` trong SQLite, tính toán bằng `Decimal` (`pabt/tien.py`: `D`, `doc_so_vn`, `lam_tron`, `so_luong_vn`). Không dùng `float`. Không dùng `D()` trực tiếp cho chuỗi người dùng gõ (phải qua `lap_pa.doc_so` / `tien.doc_so_vn`).
3. An toàn CSDL & Đóng gói:
   - Giữ `journal_mode=DELETE` và `synchronous=FULL` cho kết nối dự án đang mở (vì file `.pabt` thường lưu trên Google Drive / thư mục mạng LAN); chỉ dùng `synchronous=OFF` + `journal_mode=MEMORY` trên tệp tạm `.dang_tao` trong `csdl.tao_moi_tam` trước khi `fsync` + `os.replace`.
   - Mọi thao tác ghi vào `csdl.DANH_MUC` phải bọc trong `with con, csdl.mo_khoa_danh_muc(con):`.
   - Mọi thao tác mở `pabt/bo_don_gia.sqlite` qua `csdl.mo()` tuyệt đối KHÔNG được ghi hay tạo bảng/chỉ mục mới làm thay đổi mã băm SHA-256 của bộ đơn giá tích hợp.
   - Không thêm lại chữ ký số (`cap_nhat.sig`), không thêm quét virus chủ động, không đưa dữ liệu thật (`.pabt`, `.xlsm`, tên đơn vị/người ký thật) vào repo, `mau_in/` hay bộ cài.
   - Mọi hộp thoại (`QDialog`) mới bắt buộc có tham số `im_lang: bool = False` (hoặc `cho: bool = False`) để khi chạy test tự động không bật `QMessageBox` hay `QFileDialog` gây treo tiến trình test.
   - Lưu ý môi trường Claude Code trên Windows: Shell Bash nuốt dấu `\` trong heredoc; khi tạo/sửa file Python hãy dùng công cụ `Write`/`Edit` trực tiếp hoặc viết script `.py` bằng `Write` rồi chạy.

======================================================================
II. GIAI ĐOẠN 1: TÍCH HỢP CÁC CÔNG CỤ, TIỆN ÍCH & TINH CHỈNH MỚI (0.9.87)
======================================================================
Hãy tích hợp đầy đủ các module và tính năng sau vào hệ thống (nếu đã giải nén gói `PABT_BoCongCu_TuDong_0.9.87.zip` thì kiểm tra, hoàn thiện và móc nối sâu vào giao diện chính):

1. Hoàn thiện 3 chi tiết Bản in còn tồn đọng ở 0.9.85 (`pabt/in_an.py` & `pabt/chua_benh_csdl.py`):
   - Nhãn chủ sử dụng linh hoạt: Trong `in_an._thong_tin_ho` và `lap_chi_tiet`, kiểm tra nếu chủ sử dụng đất là Tổ chức (`la_to_chuc(ten, loai_doi_tuong)` nhận diện qua loại đối tượng hoặc từ khóa Công ty, UBND, Ban Quản lý, Hợp tác xã, Trung tâm, Nhà thờ, Chùa, Trường...) thì điền nhãn `"Tổ chức:"` thay cho `"Họ và tên:"`.
   - Gộp ô Ghi chú ở Mục 1 (Đất): Sau khi điền các dòng đất của Mục 1 trong `lap_chi_tiet`, tự động gộp dọc các ô cột Ghi chú của các dòng đất liên tiếp có cùng nội dung ghi chú (khác rỗng) bằng `in_an._gop_o` + `_dinh_dang_gop` (căn giữa dọc `vertical='center'`, `wrap_text=True`), không dùng `ws.merge_cells` trực tiếp để tránh độ phức tạp O(n²).
   - Chuẩn hóa tiêu đề Mục II: Đảm bảo tiêu đề mục II trên bản in chi tiết luôn chuẩn hóa thành `"II. Thông tin vị trí, nguồn gốc đất"`.

2. Đệm mẫu Excel trong RAM bằng `BytesIO` & Bộ dựng PDF dự phòng thuần Qt (`pabt/in_an.py`, `pabt/xem_truoc_tai_lieu.py`):
   - Đệm mẫu `.xlsx` trong RAM: Thay vì đọc đĩa và giải nén file mẫu `.xlsx` lặp lại cho từng hộ trong `lap_chi_tiet` / `lap_bang_tong_hop` (và tránh `pickle`/`deepcopy` vì làm hỏng `row_dimensions` và `IndexedList` của `openpyxl`), hãy dùng bộ đệm `nap_mau_bytes(duong_dan)` lưu `bytes` theo khóa `(str(path), st_mtime_ns, st_size)` và khởi tạo workbook bằng `openpyxl.load_workbook(io.BytesIO(raw_bytes))`. Khi người dùng gọi `cap_nhat_mau_in` hoặc cài gói `.pabtcfg` thì xóa bộ đệm này (`xoa_bo_nho_mau()`).
   - Dự phòng PDF thuần Qt khi máy thiếu MS Excel hoặc Excel bị treo: Trong `xem_truoc_tai_lieu.py` (`KhungXemTruocTaiLieu`) và `in_an.chay_excel`, nếu máy trạm không cài MS Excel hoặc `chay_excel` trả lỗi `LOI_TREO` / `OSError`, tự động chuyển sang hàm `man_hinh_chan_doan.xuat_pdf_du_phong_qt` (dùng `QPdfWriter` + `QTextDocument` vẽ bảng phương án chuẩn khổ A4) để tính năng Xem trước (`F4`) luôn hoạt động 100% trên mọi máy.

3. Bác sĩ Kỹ thuật CSDL, Chẩn đoán Máy trạm & Hộp đen Báo lỗi Ẩn danh (`pabt/chua_benh_csdl.py`, `pabt/man_hinh_chan_doan.py`, `pabt/giao_dien.py`, `pabt/app.py`):
   - Kiểm tra & sửa tệp `.pabt` (`kiem_tra_tep_pabt`, `sua_tep_pabt`): Tự động sao lưu trước khi sửa, gỡ tệp khóa `.pabt.khoa` bị kẹt, kiểm tra `PRAGMA integrity_check` & `PRAGMA foreign_key_check`, chạy `REINDEX` + `VACUUM`, và cứu dữ liệu qua `iterdump()` sang tệp mới nguyên tử nếu trang CSDL bị hỏng.
   - Đóng gói Hộp đen Ẩn danh (`an_danh_du_an`, `dong_goi_chan_doan`): Trong hộp thoại `HopChanDoanHeThong` và trong hộp báo lỗi tự động của `giao_dien.cai_bat_loi`, thêm nút `"Xuất gói chẩn đoán gửi tác giả (.zip)…"`. Khi bấm, tự động đóng gói `loi.log`, thông tin máy/DPI/OS, `pabt_profile.json` và một bản sao dự án `.pabt` đã ẩn danh hoàn toàn (đổi `ho.ten` thành `"Hộ kiểm thử 0001..."`, thay `cccd`, xóa `sdt`, ẩn danh người ký trong `du_an`, xóa `audit_logs`/`nhat_ky`, nhưng giữ nguyên 100% số liệu diện tích, đơn giá, loại đất, công thức).
   - Móc nối vào menu chính: Thêm lệnh `'Chẩn đoán & Sửa lỗi hệ thống…'` vào menu `Trợ giúp` trong `CuaSoChinh._thanh_menu` (`pabt/app.py`) để mở `HopChanDoanHeThong(self, file_pabt=self.file)`.

4. Phiếu Kiểm đếm Thực địa Offline & Tự động gắn ảnh hiện trạng (`pabt/phieu_kiem_dem.py`, `pabt/app.py`):
   - Cho phép xuất Phiếu kiểm đếm thực địa ra 1 tệp `.html` độc lập (`xuat_phieu_kiem_dem_html`) để cán bộ mở trên điện thoại ngoài thực địa không cần Internet, nhập kết quả kiểm đếm trả về từ tệp `.json` (`nhap_ket_qua_kiem_dem`) và tự động quét thư mục ảnh hiện trường gắn vào hộ theo Mã hộ / CCCD / Họ tên không dấu (`gan_anh_hien_trang`).
   - Thêm lệnh vào menu `Công cụ` hoặc `Dữ liệu` trên thanh menu chính (đảm bảo không trùng lệnh với menu trái).

5. Quy hoạch CSDL lên `PHIEN_BAN_CSDL = 16` (`pabt/csdl.py`, `pabt/schema.sql`):
   - Chuyển việc tạo bảng `nhat_ky_van_dong`, `audit_logs` (kèm 2 trigger `trg_audit_chan_sua` / `trg_audit_chan_xoa` dùng `RAISE(ABORT, ...)`) và chỉ mục `ix_ctdat_thua` vào `schema.sql` và `_NANG_CAP[15]` (`nang_cap_csdl_v16`), chỉ chạy khi tệp có bảng `ho` (không ghi vào `bo_don_gia.sqlite`).

======================================================================
III. GIAI ĐOẠN 2: RÀ SOÁT CẤU TRÚC, BẮT LỖI LẶP, BIẾN/LỆNH DƯ THỪA HOẶC LỖI
======================================================================
Thực hiện kiểm toán tĩnh và động trên toàn bộ các tệp `.py` trong `pabt/`, thư mục gốc và `tests/`:

1. Quét AST & Kiểm tra Tĩnh toàn bộ mã nguồn (`tao_ban_do_ma.py`):
   - Quét toàn bộ `.py` bằng `ast` để phát hiện và sửa triệt để:
     a) Hàm, phương thức hoặc lớp khai báo trùng tên trong cùng một phạm vi làm ghi đè nhau (`F811`).
     b) Biến cục bộ gán giá trị nhưng không bao giờ đọc (`F841`), hoặc đọc biến chưa khởi tạo ở một nhánh `if/else` (`F821`).
     c) Các câu lệnh `import` dư thừa không còn sử dụng (`F401`) hoặc `import` vòng tròn (circular imports).
     d) Các câu lệnh `from .to_chuc import TEN` (hoặc hằng số của `lap_pa`, `thoi_han`, `du_thao`) ở cấp module làm mất giá trị cập nhật động từ `dia_phuong.nap_lai()` (phải truy cập qua thuộc tính module lúc gọi hàm).
     e) Các khối `except:` trống không chỉ định `Exception` (`E722`) hoặc nuốt lỗi im lặng mà không ghi log / không trả lại con trỏ chuột (`giao_dien.con_tro_cho`).
     f) Các hàm/lớp "mã chết" (dead code) không còn bất kỳ nơi nào trong `pabt/` hay `tests/` gọi tới.
   - Xuất kết quả bản đồ kiến trúc mới nhất ra `BAN_DO_MA.md`.

2. Kiểm tra tính toàn vẹn của Hệ thống Lệnh, Menu & Giao diện (`test_khong_trung_lenh.py`):
   - Rà soát toàn bộ `CuaSoChinh.lenh` (`QAction`), `NHAN_MENU`, `LENH_CAN_DU_AN`, `menu_trai`, `_thanh_menu`, `_thanh_cong_cu_ds`, `_menu_ho` (chuột phải), `nut_chao` và `lien_ket_chan`:
     a) Nguyên tắc "Mỗi lệnh một chỗ": Menu trái và Thanh menu trên là hai nơi chính, tuyệt đối không lặp lại cùng một lệnh giữa hai nơi; không tạo `QPushButton` rời lặp lại lệnh đã có trên menu trái.
     b) Mọi nút công cụ, mục menu chuột phải và liên kết chân trang phải dùng chung hoặc kích hoạt qua `QAction` trong `self.lenh[...]` — tuyệt đối không gọi thẳng hàm làm mất kiểm soát trạng thái bật/tắt khi chưa mở dự án (`LENH_CAN_DU_AN`) hoặc khi đang mở dự án ở chế độ chỉ xem (`chi_doc=True`).
     c) Kiểm tra mọi ký hiệu icon trong `giao_dien.KY_HIEU`: đảm bảo mọi nhãn mới trong `NHAN_MENU` đều khớp từ khóa có biểu tượng (hoặc gắn `icon_trong` để khi thu gọn menu không bị lệch chữ).
     d) Kiểm tra bố cục và vùng bấm trên màn hình `1366x768` ở tỷ lệ DPI `100%`, `110%` và `125%`:
        - Mọi mục trên `QMenuBar` (`Tệp tin`, `Chỉnh sửa`, `Dữ liệu`, `Công cụ`, `Cài đặt`, `Trợ giúp`) phải nhận được cú bấm chuột tại tâm (`childAt` trả về `QMenuBar`, không bị bất kỳ widget ẩn nào như `KhungLamViecDaTab` che khuất).
        - Bề rộng tối thiểu (`minimumSizeHint`) của `CuaSoChinh` và mọi hộp thoại con (`la_cua_so_con_pabt`) không được vượt quá `1024 x 680` (hoặc vùng làm việc màn hình), có đầy đủ nút Thu nhỏ / Phóng to / Đóng (`chuan_hoa_cua_so_con`).
     e) Kiểm tra rò rỉ bộ nhớ giao diện: Đảm bảo `giao_dien.ap_dung(app)` không bao giờ cài chồng nhiều bộ lọc sự kiện `_BoToMau`; `don_hop_da_dong` xóa sạch các `QDialog` ẩn sau khi đóng; các `QTimer` và thư mục tạm `%TEMP%\pabt_preview` được dọn sạch khi đóng cửa sổ.

======================================================================
IV. GIAI ĐOẠN 3: TỐI ƯU HÓA THỜI GIAN XỬ LÝ TIẾN TRÌNH, PHẢN HỒI LỆNH & NẠP DỮ LIỆU THÔ (ẢNH, OFFICE, PDF)
======================================================================
Giải quyết triệt để các điểm nghẽn hiệu năng còn tồn đọng trong `CLAUDE.md` và `LICH_SU_PHAT_TRIEN.md` (mục "CHƯA làm" của 0.9.20, 0.9.22, 0.9.65):

1. Tối ưu thời gian nạp và bóc tách dữ liệu từ Ảnh & PDF Quét (`pabt/ocr.py`, `pabt/quan_ly.py`, `pabt/cap_nhat_gia_dat.py`):
   - Sửa `ocr._anh_trang_pdf` / `ocr.tung_trang`: KHÔNG dựng ảnh toàn bộ các trang PDF trước rồi mới hiện hộp tiến trình. Phải mở tài liệu PDF, hiện thanh tiến trình ngay lập tức, rồi dựng ảnh và nhận diện từng trang một trong vòng lặp (kiểm tra cờ Dừng sau mỗi trang, dừng sớm ngay khi đã hết mục xã hoặc tìm thấy dòng hộ cần tìm, và luôn gọi `QPdfDocument.close()` trong khối `finally`).
   - Khi phóng ảnh trang PDF/ảnh chụp cho Tesseract: chỉ phóng lên ~300 DPI nếu chiều rộng `< 2000 px`, dùng phép biến đổi nhanh để giảm thời gian tiền xử lý ảnh.

2. Tối ưu thời gian nạp dữ liệu từ PDF Quyết định có lớp chữ (`pabt/pdf_bang.py`, `pabt/quan_ly.py`):
   - Hiện tại khi đọc một tệp PDF quyết định phê duyệt, tệp bị mở và trích xuất văn bản lặp lại 2–3 lần (một lần lấy số/ngày QĐ và chữ ký số, một lần đếm số trường hợp, một lần bóc bảng tiền).
   - Hãy tạo hàm đọc một lần duy nhất (hoặc truyền danh sách dòng văn bản đã trích xuất / bộ nhớ đệm theo `(path, mtime_ns, size)`) để dùng chung cho `so_ngay_qd`, `chu_chu_ky`, `so_truong_hop` và `doc_quyet_dinh` -> giảm 50–65% thời gian nạp PDF quyết định.

3. Tối ưu thời gian nạp dữ liệu từ tệp Office (`.xlsx`, `.xlsm`, `.docx`, `.doc`, `.xls`):
   - Tệp Word `.docx` lớn (`pabt/nhap_don_gia.py`, `pabt/cap_nhat_gia_dat.py`): Khi đọc bảng/văn bản từ `word/document.xml` có kích thước lớn, tối ưu quá trình duyệt XML hoặc dùng `ET.iterparse` theo từng phần tử `<w:p>` / `<w:tbl>` rồi giải phóng bộ nhớ thay vì giữ toàn bộ cây DOM khổng lồ trong RAM (đặc biệt quan trọng cho bản 32-bit trên Windows 7).
   - Nhập phương án chi tiết hàng loạt (`pabt/nhap_chi_tiet.py` - hàm `ghi` vào dự án đang mở): Giữ thực thi trên luồng chính để bảo toàn trigger `HoanTac`, nhưng bọc trong `csdl.giao_dich(con)` và hiển thị `QProgressDialog` cập nhật sau mỗi 10–15 hộ (kèm `ExcludeUserInputEvents` hoặc nút Dừng an toàn) để giao diện phản hồi mượt mà, không bị đứng hình khi nhập hàng trăm sheet.
   - Bảng tổng hợp (`pabt/in_an.py` - `lap_bang_tong_hop`): Tái sử dụng phương án đã đọc hoặc kết quả từ `nghiep_vu.ket_qua_ho(con)` / `doc_tat_ca_phuong_an(con)` một lần duy nhất, bỏ lần gọi `doc_tat_ca_phuong_an` trùng lặp thứ hai.
   - Khởi động lười (Lazy Import): Đảm bảo `openpyxl`, `pypdf`, `urllib.request`, `difflib` tuyệt đối KHÔNG bị nạp lúc mở phần mềm (`chay.py` -> `app.main`) hay lúc mở tệp `.pabt` (`app.mo`), mà chỉ nạp bên trong hàm khi người dùng thực sự gọi lệnh xuất/nhập tương ứng.

4. Tối ưu thời gian phản hồi lệnh trên Giao diện (`pabt/giao_dien.py`, `pabt/man_hinh_du_toan.py`, `pabt/may_chu.py`):
   - `OTimChon` (`giao_dien.py`): Khi người dùng gõ từng phím tìm kiếm tài sản/cây trồng, chỉ lọc trên danh sách dữ liệu đã chuẩn hóa không dấu trong bộ nhớ và tái sử dụng các item hiển thị thay vì khởi tạo lại từ đầu ở mỗi phím gõ.
   - `KhungDuToan` (`man_hinh_du_toan.py`): Đảm bảo khi sửa số lượng, đơn giá, hệ số trên bảng dự toán chỉ tính và vẽ lại đúng dòng đang sửa + dòng chi phí mục 6 + thẻ tổng (`_ve_lai_dong`), không gọi `ve()` vẽ lại cả bảng.
   - `may_chu.ds_du_an` (`may_chu.py`): Đảm bảo đọc danh sách dự án trên máy chủ LAN qua chỉ mục `DuAn\danh_muc_du_an.json` (so khớp `mtime_ns` và `size`), chỉ mở tệp `.pabt` qua mạng khi tệp đó thực sự mới hoặc vừa thay đổi.

======================================================================
V. GIAI ĐOẠN 4: KIỂM ĐỊNH TOÀN DIỆN, ĐO ĐẠC SO SÁNH & BÁO CÁO KẾT QUẢ
======================================================================
Sau khi hoàn tất các chỉnh sửa trên:
1. Tăng `__version__` trong `pabt/__init__.py` và thêm mục cập nhật mới lên đầu `pabt/lich_su_cap_nhat.py` (`MUC`).
2. Chạy kiểm tra tĩnh & tương thích:
   - `.venv\Scripts\python tao_ban_do_ma.py` (đảm bảo 0 cảnh báo tĩnh AST).
   - `vermin -t=3.8- pabt/` (đảm bảo 100% tương thích Python 3.8).
3. Chạy toàn bộ kiểm thử tự động trên cả hai môi trường:
   - Qt6 (`.venv`): `set QT_QPA_PLATFORM=offscreen` rồi `.venv\Scripts\python -m unittest discover -s tests -t .` (chạy cả với biến `PABT_EXCEL` trỏ tới file `.xlsm` chuẩn).
   - Qt5 (`venv38_32`): chạy toàn bộ test trên môi trường Python 3.8 32-bit.
4. Chạy bộ đo tải lớn và kiểm tra giao diện tự động:
   - `.venv\Scripts\python ket_qua_kiem_tra\thu_that\do_tai_lon.py --so-ho 5000`
   - `KIEM_TRA_GIAO_DIEN.bat` (`kiem_tra_giao_dien.py`): bấm mọi nút, gõ mọi ô nhập, chọn mọi mục chọn, sửa ô bảng của mọi hộp thoại -> đảm bảo 0 lỗi, 0 đơ (> 5s), 0 treo, 0 hộp thoại rò rỉ.
   - `PHAN_TICH_PHIEN_BAN.bat` (`phan_tich_phien_ban.py --so-sanh G:\PABT_CapNhat_<bản_trước>.pabtcn`).
   - `KIEM_TRA_TOAN_BO.bat`.
5. Cập nhật `CLAUDE.md` và báo cáo tổng kết cho tôi kèm **Bảng số liệu đo đạc thực tế trước và sau khi tối ưu**:
   - Danh sách các lỗi lặp, biến/hàm dư thừa, lệnh lỗi hoặc nút trùng đã phát hiện và khắc phục.
   - Bảng so sánh tốc độ khởi động, mở dự án 5.000 hộ, lưu + tải lại 1 hộ, phản hồi tìm kiếm/lọc, thời gian in hàng loạt 50 hộ (nhờ đệm `BytesIO`), và thời gian nạp dữ liệu thô từ Ảnh (OCR) / Office (`.xlsx`, `.docx`) / PDF quyết định.
   - Kết quả chạy `KIEM_TRA_GIAO_DIEN.bat` và toàn bộ các bài `unittest`.
```

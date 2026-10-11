# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Tổng quan
PABT: phần mềm lập phương án bồi thường, hỗ trợ khi thu hồi đất (Python + PySide6, Windows). Mỗi dự án là một file `.pabt` (SQLite).
Mã nguồn, hàm, biến, bảng CSDL viết bằng tiếng Việt không dấu (`ma_ho`, `tinh_pa`, `doi_chieu`) — giữ quy ước này.
Hướng dẫn người dùng: `HUONG_DAN.md`. Phần mềm phát hành **không kèm dữ liệu** (không có `.pabt`, danh sách hộ, danh mục đơn giá; mẫu in
không ghi cố định tên đơn vị / người ký) — đừng đưa dữ liệu thật vào repo, `mau_in/` hay bộ cài.

## Quy trình MỖI LẦN sửa phiên bản (người dùng yêu cầu - bắt buộc)
- Tăng `__version__`; đối chiếu với gói cập nhật đã phát hành gần nhất trong `bo_cai\` (`cap_nhat.doc_goi`: SHA-256;
  so từng file với mã nguồn).
- Chạy `PHAN_TICH_PHIEN_BAN.bat` (= `phan_tich_phien_ban.py --so-sanh bo_cai\PABT_CapNhat_<bản trước>.pabtcn`): tốc độ mở / tắt,
  mở dự án, lưu + tải lại, lệnh dòng lệnh; module nạp lúc khởi động; mã lặp lại; file khác nhau -> `ket_qua_kiem_tra\PhanTich_*.md`.
- Chạy `KIEM_TRA_GIAO_DIEN.bat` (= `kiem_tra_giao_dien.py`): bấm mọi nút, gõ mọi ô nhập, chọn mọi mục chọn, sửa ô bảng của mọi
  hộp thoại (bản sao dự án; chặn in / Excel / Word / mạng) -> lỗi, chậm / đơ (> 5 s), treo -> `ket_qua_kiem_tra\GiaoDien_*.md`.
- Báo cáo cho người dùng KÈM phân tích: điểm nghẽn, lệnh lặp lại, cách gọi lệnh nhanh nhất / đường tắt, cách gọi gói (nạp module
  khi nào), tốc độ (thời gian mở tắt, chạy lệnh) - bảng so với bản trước; lỗi / đơ của nút bấm, ô nhập, mục chọn (đã sửa gì).
- Toàn bộ test (Qt6; Qt5 nếu có `venv38_32`), `vermin -t=3.8-` cho mã pabt/.

## Lệnh (chạy từ thư mục gốc, dùng `.venv`)
- Cài môi trường: `CAI_DAT.bat` (tạo `.venv`, cài `requirements.txt`: openpyxl, PySide6, chạy test)
- Mở giao diện: `.venv\Scripts\python chay.py [file.pabt]`
- Nhập Excel bằng dòng lệnh: `.venv\Scripts\python chay.py nhap <file.xlsx|xlsm> [<file.pabt>] [--ten "..."] [--danh-muc <cu.pabt>]`
- Đối chiếu: `.venv\Scripts\python chay.py doi-chieu <file.pabt>`
- Toàn bộ test: `set QT_QPA_PLATFORM=offscreen` rồi `.venv\Scripts\python -m unittest discover -s tests -t .`
- Kiểm tra toàn bộ khi có lỗi: `KIEM_TRA_TOAN_BO.bat [--nhanh] [--cai-thu]` (= `kiem_tra_toan_bo.py`, chỉ thư viện chuẩn): test Qt6 +
  Qt5, chạy thử nhập/đối chiếu file mẫu trên bản sao, `tu-kiem` dist\ và bản đã cài, bo_cai\ (đủ file, zip không có dữ liệu, gói
  .pabtcn đúng mã), bản cập nhật đang dùng (LOI.txt), máy chủ LAN → `ket_qua_kiem_tra\KiemTra_<giờ>.txt`.
- Một test: `.venv\Scripts\python -m unittest tests.test_ho_so.TestHoSo.test_gop_ho`
- Test so khớp với Excel thật cần `du_lieu\PABT.xlsm` hoặc biến `PABT_EXCEL`; không có thì tự bỏ qua (khoảng 34 bài).
- Dựng exe: `DUNG_EXE.bat` → `dist\PABT\PABT.exe` (PyInstaller onedir, kèm `pabt\schema.sql`, `mau_in\`).
- **Hai bộ cài** (người dùng yêu cầu tách, đừng gộp): `PABT_CaiDat_<ver>_Win10-11.exe` (Python 3.14 + PySide6, PyInstaller 6, `.venv`,
  KHÔNG kèm Visual C++ Redistributable - người dùng yêu cầu bỏ 25 MB: Win10/11 có UCRT, DLL VC++ cần thiết đã nằm trong bản dựng,
  kiểm bằng bảng import PE; `dung_bo_cai_win.BAN['win10']['vc'] = None`) và `PABT_CaiDat_<ver>_Win7-8.exe` (**32-bit**, chạy Win 7/8 32 & 64-bit và Win 10 32-bit: Python 3.8.10 32-bit + PySide2 5.15,
  PyInstaller 5, môi trường `%LOCALAPPDATA%\PABT_dev\venv38_32` tạo bằng `CAI_DAT_PHAT_HANH.bat` / `requirements38.txt`,
  UCRT Win 7 đóng sẵn (`bo_cai_win\ucrt_win7.py` lấy từ `vc_redist_win7.x86.exe` 14.29 - chỉ để dựng), vỏ IExpress 32-bit từ `SysWOW64` — `dung_bo_cai_win.IEXPRESS`, `kien_truc()` in x86/x64,
  dựng bằng `bo_cai_win\dung_exe38.py` từ bản chép ở thư mục tạm không dấu → `dist\PABT_Win7`). Mã dùng chung phải chạy Python 3.8 +
  Qt5: mỗi file có `from __future__ import annotations`, không dùng API Python 3.9+; `pabt/__init__._qt5_lam_qt6` đặt bí danh
  PySide6 → PySide2 (+ QAction/exec/QLibraryInfo.path, đường dẫn plugin Unicode); đọc PDF: QtPdf hoặc pypdf. Chạy test cả hai venv.
  `cai_dat.ps1` dùng chung (đọc `ban.txt` win10/win7 → `$KIEN` x64/x86; `vc_redist.exe` vắng mặt ở cả hai bộ cài từ 0.9.21 -
  `$CO_VC` = false), viết theo PowerShell 2.0 (không `$PSScriptRoot`, `-Raw`, `-in`, `-File`; gọi `-STA`). TIÊU CHUẨN CÀI ĐẶT
  0.9.21 (người dùng yêu cầu "máy nào cũng cài được"): xem mục 0.9.21 cuối file.
- Dựng bộ cài: `DUNG_BO_CAI.bat` (PyInstaller rồi `bo_cai_win\dung_bo_cai_win.py`: IExpress + `cai_dat.ps1`/`go_cai_dat.ps1`, cài
  mặc định vào `Program Files (x86)\PABT` - xem 0.9.22; từ chối quyền quản trị -> `%LOCALAPPDATA%\Programs\PABT`) → `bo_cai\PABT_CaiDat_<ver>.exe` + `bo_cai\PABT_ChayNgay_<ver>.zip`. KHÔNG dùng
  Inno Setup ≥ 6.5 (lỗi tạo thư mục tạm is-*.tmp trên Windows 11 build mới); phiên bản lấy từ `pabt/__init__.py` `__version__`. Lệnh PyInstaller phải kèm
  `--add-data "pabt\bo_don_gia.sqlite;pabt"`. Sau PyInstaller chạy `bo_cai_win\rut_gon.py` (giữ theo danh sách `GIU_MODULE`;
  bản Qt5 phải giữ `Qt5Qml.dll` vì `pyside2.abi3.dll` liên kết cứng - thiếu thì exe treo im lặng, không báo lỗi; rồi
  `kiem_dll` (mọi DLL nhập phải có trong bản dựng hoặc trong Windows đích, không thì dừng), rồi
  `PABT.exe tu-kiem <file>` = `chay.tu_kiem`, phải ra `KET QUA: DAT`).
  `cai_dat.ps1` là cửa sổ WinForms (`KiemTraMay` chặn / `CanhBaoMay` nhắc, tiến trình, tự kiểm tra), `-Im` cài im lặng. `KiemTraThuMuc`: chỉ xóa
  thư mục cài trống / có PABT.exe, không gốc ổ đĩa, không chứa .pabt/.pabtdt; `go_cai_dat.ps1` giữ file dự án trong thư mục cài. Từ PowerShell gọi .bat bằng đường dẫn đầy đủ (`& (Resolve-Path .\X.bat).Path`).
- Đóng gói lại bộ đơn giá tích hợp: `.venv\Scripts\python tao_bo_don_gia.py <PABT_CHUAN.xlsm> <YYYY.MM.DD>` → `pabt/bo_don_gia.sqlite`.
- Test cập nhật bộ đơn giá đặt `PABT_THU_MUC_MAY` (không ghi vào `%APPDATA%\PABT` thật). Hộp thoại mới có `im_lang = True` cho test —
  test GUI không được để QMessageBox hiện ra (sẽ treo).

## Kiến trúc
- `chay.py`: điểm vào; CLI (`nhap`, `doi-chieu`) hoặc mở GUI `pabt/app.py` (đối số `.pabt` / `.pabtcn` → mở GUI); `tu-kiem <file>` tự kiểm tra bản đóng gói.
- `pabt/csdl.py` + `pabt/schema.sql`: tạo/mở `.pabt`. Phiên bản lược đồ = `PRAGMA user_version` (`PHIEN_BAN_CSDL`). Đổi lược đồ: sửa
  `schema.sql` (file mới), tăng `PHIEN_BAN_CSDL`, thêm lệnh vào `_NANG_CAP[v_cũ]` (ADD COLUMN tự bỏ qua nếu cột đã có).
  `journal_mode=DELETE` (không WAL, vì file hay nằm trong Google Drive). `mo(..., chi_doc=True)` mở chỉ xem (URI `mode=ro`).
  `tao_moi()` **xóa file cũ** rồi tạo lại. Mọi thao tác ghi gọi `csdl.ghi_nhat_ky`.
- Mô hình: `ho` 1–n `thua`; phương án: `ct_dat` (mục 1) và `ct_khoan` (mục 2 nhà, 3 cây, 4 hỗ trợ; cột `muc`). Mục 5 (thưởng) tính từ
  `bieu_thuong`, không lưu. Danh mục: `dm_taisan`, `dm_hotro`, `dm_loaidat`, `gia_dat`, `dm_xa`, `tham_so`, `quy_uoc`, `van_ban`
  (`nhap_tho.DANH_MUC`). `tong_excel` để đối chiếu. `ho.luu_luc` trống = số liệu từ Excel chưa sửa trong phần mềm. `du_an` (1 dòng) có cả
  thông tin đơn vị / người ký dùng cho bản in (`nhap_tho.TRUONG_DON_VI`, giữ lại khi xóa trắng).
- **Danh mục cố định**: `csdl._dam_bao_khoa` tạo trigger chặn INSERT/UPDATE/DELETE trên `csdl.DANH_MUC` khi `khoa_dm.mo = 0`;
  mọi ghi danh mục phải nằm trong `with con, csdl.mo_khoa_danh_muc(con):` (nhap_excel, `csdl.chep_danh_muc`, `don_gia`, `du_an_moi`).
  Đơn giá dòng danh mục trong `BoSoan.sua_khoan` và giá đất theo bảng giá dự án trong `sua_dat` không sửa được (LoiNhap).
- `don_gia.py`: bộ đơn giá tích hợp `pabt/bo_don_gia.sqlite` (cùng lược đồ .pabt, không có hộ; `BANG_BO` = DANH_MUC trừ `gia_dat`);
  bản cập nhật ở `%APPDATA%\PABT`; dự án mới (`nhap_tho.nhap` file mới, `du_an_moi`) tự `ap_vao_du_an`. `du_an_moi.py`: dòng thô
  (`COT_THO`) → `gom` → `tao_du_an` (giá đất vào `gia_dat`, `tu_lap_phuong_an` dùng `BoSoan.them_thua` + `goi_y`) → `xuat_2_bang`.
- Dữ liệu thô của "Dự án mới" lưu nguyên ở bảng `tho_nhap` (không thuộc DANH_MUC, không khóa; `ma_ho`/`ma_thua` liên kết kết quả).
  `du_an_moi.COT_THO` là danh sách trường thô; ô Loại đất / Vị trí dùng `giao_dien.ChonXoXuong`. Tổ chức làm nhiệm vụ bồi thường
  (băng tiêu đề, giá trị điền sẵn) ở `pabt/to_chuc.py`. Đổi tên dòng danh mục mục 2/3 trong `BoSoan.sua_khoan` → dòng "tương đương",
  giữ đơn giá.
- Bản in: `in_an._thong_tin_du_an` lấy `to_chuc.MAC_DINH` cho ô đơn vị trống; đường kẻ (hình vẽ openpyxl làm mất) lưu ở
  `mau_in/<mẫu>.duong_ke.xml` (ghi trong `tao_mau_tu_excel`; mẫu sửa trong Excel còn hình vẽ: `duong_ke_cua_mau`) và chèn sau
  `wb.save` bằng `in_an.chen_duong_ke`.
- `gia_dat_nq28.py`: bảng giá đất NQ 28/2025 (4 địa bàn) từ `pabt/bang_gia_nq28.json` (giá nghìn đồng/m², 7 mức MT/T1-3/K1-3 mỗi
  đoạn); dùng ở bước 3 Dự án mới (`HopDuAnMoi.tra_gia_nq28`) và Bộ đơn giá. Biểu tượng vẽ bằng `tao_bieu_tuong.py` → `pabt/bieu_tuong.ico/.png`;
  PyInstaller cần `--icon pabt\bieu_tuong.ico`, `--add-data` cho `bang_gia_nq28.json`, `bieu_tuong.png` (dùng `--clean` khi đổi biểu tượng);
  `dung_bo_cai_win.doi_bieu_tuong` thay biểu tượng file IExpress.
- `nhap_don_gia.py`: cập nhật bộ đơn giá từ file bất kỳ (`doc_bang` xlsx/docx/pdf qua QtPdf/csv → `nhan_muc` → `so_khop` → `ap_dung`
  tạo bản mới trong `%APPDATA%\PABT` qua `don_gia.cai_bo`) hoặc web (`tai_ve`: file thẳng / trang HTML liệt kê liên kết / Google Drive).
  Biểu tượng Desktop dùng file `PABT.ico` riêng trong thư mục cài (tránh bộ đệm biểu tượng của Windows).
- `pabt/tien.py`: **số tiền, diện tích, số lượng lưu TEXT, tính bằng Decimal** (`D`, `chuoi`, `lam_tron` = ROUND của Excel, `vn`/`so_vn`
  hiển thị kiểu VN). Không dùng float. Số người dùng gõ đọc bằng `lap_pa.doc_so` (lỗi → `LoiNhap`, thông báo tiếng Việt).
- Nhập dữ liệu: `nhap_excel.py` (đúng mẫu PABT `.xlsm`, sheet DB_HO/DB_THUA/…, cột theo tên tiêu đề đã chuẩn hóa) và `nhap_tho.py`
  (Excel bất kỳ: tự tìm sheet/dòng tiêu đề, gán cột theo `MAU_COT`/`LOAI_TRU`, gom hộ theo CCCD hoặc tên+địa chỉ; ghi vào `.pabt` có sẵn
  bằng `xoa_trang` — xóa hồ sơ, giữ danh mục). `nhap_tho.la_file_pabt` chọn đường nhập; `nap_danh_muc` thay danh mục từ `.xlsm`.
- `nhap_chi_tiet.py` (+ `man_hinh_nhap_chi_tiet.HopNhapChiTiet`, `app.nhap_chi_tiet`, CLI `nhap-chi-tiet`): file Excel phương án
  chi tiết, mỗi sheet một hộ (bản in kiểu IN_CHITIET) -> `doc` (tìm dòng STT + cột theo tiêu đề, nhãn Họ và tên / CCCD… phía trên,
  "II… nguồn gốc", mục 1-5, TỔNG CỘNG, "Phương án tái định cư:"; sheet mẫu / #N/A / không họ tên: chon=False) -> `ghi(con, ds,
  trung='bo_qua'|'thay'|'them')` thêm vào dự án (không xóa hộ khác; trùng = `ho_trung` CCCD / họ tên). Mục 1 mỗi dòng = một thửa;
  chỉ lập ct_dat khi có đơn giá đất, không thì ghi chú đất -> `ho.phap_ly` (in_an in ở dòng thửa đầu khi hộ không có ct_dat).
  Mục 2/3: `_KhopDanhMuc` tên (bo_dau, giữ dấu câu: "Mái che, mái hiên" ≠ "…hiên.") + đơn giá -> danh mục / nhập tay.
  Trạng thái `TRANG_THAI`, luu_luc NULL (= da_lap), thanh_tien_excel + tong_excel để `doi_chieu`.
- `nghiep_vu.py`: quy tắc tính (`PhuongAn`, `BoiCanh` → `tinh_pa` → `KetQuaHo`), gợi ý hỗ trợ theo QĐ 42/2025, kiểm tra hộ.
- `lap_pa.py` (`BoSoan`): soạn/lưu phương án một hộ trong một giao dịch; `ho_so.py`: thêm/sửa/xóa hộ, thửa, gộp hộ, chuyển thửa.
  Logic nằm ở các module này; màn hình (`app.py`, `man_hinh.py`, `man_hinh_ho_so.py`) chỉ hiển thị. Hàm màn hình nhận tham số tùy chọn
  (`xac_nhan=`, `ma_ho_bo=`, `cho=False`…) để test không phải bấm hộp thoại.
- `doi_chieu.py`: so với `tong_excel`/`thanh_tien_excel`, xuất báo cáo xlsx. `in_an.py`: điền mẫu `mau_in/IN_CHITIET.xlsx`,
  `IN_BANGTONGHOP.xlsx` (ô `{ten}` thay bằng `_thong_tin_du_an` + thông tin hộ), xuất PDF/in qua Excel; bản đã cài đọc/ghi mẫu ở
  `%APPDATA%\PABT\mau_in`.
- Cập nhật không cài lại: gói `.pabtcn` (zip: `cap_nhat.json` + toàn bộ `pabt/*.py` và file dữ liệu, sha256) tạo bằng
  `tao_cap_nhat.py` / `DUNG_CAP_NHAT.bat`; `pabt/cap_nhat.py` (doc_goi/kiem_tra/cai/go/trang_thai) cài vào
  `<thư mục máy>\cap_nhat\<ver>_<giờ>` + `hien_hanh.txt`; `nap_cap_nhat.py` (gốc repo, đóng trong exe, KHÔNG cập nhật được: giữ
  gọn) gọi ở đầu `chay.py`, chỉ khi frozen: meta-path finder ưu tiên thư mục cập nhật cho `pabt*`, nạp thử mọi module, lỗi → `LOI.txt`
  + bản gốc; bộ đếm `dang_khoi_dong.txt` (≥2 → tắt), xóa bởi `khoi_dong_tot`. File dữ liệu gói pabt lấy qua `pabt.tai_nguyen()`
  (cạnh `__file__` trước, rồi `_MEIPASS`) để gói cập nhật thay được. Hộp thoại: `man_hinh_cap_nhat.HopCapNhat`.
- CSDL v7 (`_NANG_CAP[6]`): cột tiến độ trên `ho` (`dot_id`, `da_phe_duyet/qd_so/qd_ngay/qd_so_tien/qd_file`, `da_chi_tra/…`,
  `da_ban_giao/ban_giao_ngay`, `theo_doi`), bảng `dot_trinh`, `cai_dat` (`csdl.doc_cai_dat/ghi_cai_dat`: THU_MUC_HO_SO,
  TL_NGOAI_MAT_DO, TL_NGOAI_RANH), `quy_chuan_mat_do` — không thuộc DANH_MUC (không khóa). `nhap_tho.xoa_trang` xóa cả `dot_trinh`.
- `quan_ly.py` (+ `man_hinh_quan_ly.py`): đợt trình (`xuat_dot` → `<thư mục hồ sơ>/<Đợt N - k hộ>/` qua `in_an.xuat_hang_loat`, đổi tên
  thư mục cũ theo số hộ), `luu_thanh` (SQLite backup), trạng thái (`cap_nhat_trang_thai`, `TRUONG_TT`, `hop_trang_thai` cho bộ lọc),
  `doc_quyet_dinh` (dùng `nhap_don_gia.doc_bang`; khớp mã hộ / CCCD / họ tên `_ten_chuan`, tên trùng → `khong_khop`), `ap_quyet_dinh`,
  `xuat_bao_cao_tong_hop`. `kiem_loi.py`: `kiem_tra` → [Loi], `sua_tu_dong` (chỉ title-case khi `la_ho_ten_don`), `loi_font`.
  `du_toan.py` (+ `man_hinh_du_toan.py`, file `.pabtdt` JSON): `tu_du_an/tu_file_pabt/tu_excel_pabt/tu_ds_tho`, `ap_don_gia_hien_hanh`,
  mục 6 = % tổng mục 1-5. `cay_trong.py` (+ `man_hinh_cay.py`): `khoang_duong_kinh` (mẫu "(d >a-b cm)", "Đk thân"), `BangCayDK`
  (nhóm theo `ten_loai_dk`), mật độ từ ghi chú danh mục "Mật độ 1.111 cây/ha" (dấu chấm = nghìn), `tach_mat_do`, `tach_ranh`;
  `BoSoan.nhan_ban` chép dòng để tách phần ngoài mật độ / ngoài ranh. `tien.tien_bang_chu`.
- Cửa sổ chính: cột 13-17 (Đợt, Phê duyệt, Chi trả, Bàn giao, Ghi chú theo dõi — `COT_GHI_CHU` sửa trực tiếp qua `BangHo.setData`),
  lọc bằng `LocHo` (đợt / trạng thái / từ khóa không dấu).
- Giao diện (`giao_dien.py`): thanh lệnh `thanh_lenh` (thẻ nhóm, nút `nut_lenh(duoi=True)` biểu tượng trên chữ, nền nhạt
  `QToolButton[ribbon="1"]`), `menu_trai` (từ 0.9.3 là giao diện chính: `app.main` dùng `CuaSoChinh(menu_trai=True)`, `--menu-tren` quay về thanh nút trên;
  nút `menu="1"`; 0.9.3 chỉ phát hành gói .pabtcn trên nền bộ cài 0.9.2),
  biểu tượng `icon_ky_hieu` từ phông Segoe Fluent Icons / MDL2 (không có thì chỉ chữ – Win 7), `do_bong` (chỉ Qt6), form gọn
  `the_form` + `can_giua`, `_BoToMau` khi hiện cửa sổ: tô màu + icon nút, `vua_man_hinh` cho QDialog, ô chữ hiện từ đầu.
  Tên tài sản/cây viết hoa chữ đầu: `don_gia.viet_hoa_dau/chuan_ten_danh_muc` (bộ đơn giá, `nhap_excel`), `kiem_loi.sua_tu_dong`.
- Máy chủ LAN (0.9.2, không bắt buộc): `may_chu.py` (không Qt) — máy chủ = thư mục dùng chung có `pabt_may_chu.sqlite` (tài khoản
  PBKDF2, `gan_day`, `lay_ve`, `nhat_ky`), `DuAn\`, `SaoLuu\`; cấu hình máy ở `<thư mục máy>\may_chu.json`; `PHIEN` toàn cục,
  `dang_nhap` đặt `csdl.NGUOI_DUNG`/`khoa.NGUOI_DUNG`; `ghi_mo_du_an` (gọi trong `app.mo`, chỉ ghi file nằm trong máy chủ / UNC) →
  `du_an_cuoi` để tự mở lại ở máy khác; `lay_ve`/`dua_len` (xung đột theo mtime, sao lưu `SaoLuu`)/`huy_lay_ve`, bản offline ở
  `<thư mục máy>\offline`. Kiểm tra kết nối trong luồng có hạn giờ (`ket_noi_duoc`). Màn hình `man_hinh_may_chu.py`; `app.main` gọi
  `khoi_dong_may_chu` (không kết nối được → offline bình thường), nút tài khoản ở thanh trạng thái (`nut_tk`, `_menu_tai_khoan`).
  Test đặt `PABT_THU_MUC_MAY`.
- 0.9.4 nhập liệu: `CuaSoLapPA` = hồ sơ + phương án một cửa sổ (thẻ 0 `man_hinh_ho_so.KhungHoSo` với `an=('trang_thai',
  'tai_dinh_cu')`, thẻ 1-5 `BangMuc` (từ 0.9.21 thẻ != mục: `man_hinh.THE_MUC` / `the_cua(muc)`, `self.bang` theo MỤC); `hang_dieu_huong`/`sang_the` lưu hồ sơ khi rời thẻ 0; `HopHoSo` chỉ bọc
  KhungHoSo). Hàng nhập nhanh `giao_dien.OTimChon` (lọc không dấu) → `CuaSoLapPA.them_nhanh` (mục 3 kiểu 'dk'/'cv' →
  `cay_trong.gom_theo_kich_thuoc`). Ô thửa / vị trí mục 1: `XoXuongDong` → `BoSoan.doi_thua`, `ds_vi_tri_nq28`/`chon_vi_tri_nq28`;
  chữ dài: `ChuNhieuDong`. Công thức trong ô số: `tien.tinh_cong_thuc` qua `lap_pa.doc_so`; `doc_so_luong` làm tròn 1 chữ số (ha: 4).
  Tái định cư = `ho.tai_dinh_cu` (`lap_pa.TAI_DINH_CU`, `ThongTinHo.tai_dinh_cu`), HT11-13 (`MA_TDC`) không thêm thành dòng tiền.
  Thuê nhà / tự lo chỗ ở (`MA_THEO_NK`): một dòng, đơn giá tháng = `nghiep_vu.don_gia_theo_nhan_khau` (ngưỡng `cai_dat`
  NGUONG_NHAN_KHAU, mặc định 4), `BoSoan.dat_nhan_khau` cập nhật lại. `ho_so.luu_ho` sửa hộ chỉ ghi các trường có trong thong_tin.
  Bảng khái toán: `du_toan.xuat_khai_toan`. Kiểu chữ: QSS có bộ chọn (`QLabel {…}`, `#ten`) — kiểu không bộ chọn trên khung cha bị
  truyền sang tooltip (nền đen). Nút: chỉ nhóm `DAC` ('luu') nền đặc, nhóm khác nền nhạt (`_nut_qss`, `mau_chu_nut`).
- 0.9.5: CSDL v8 (`ct_khoan.cach_tinh`, `DongKhoan.cach_tinh`, `Dong.cach_tinh`): `in_an.dong_chi_tiet` mục 4 trả phần tử 3 thành
  phần (loại, giá trị, cách tính) → `lap_chi_tiet` gộp ô C:F; dòng HT09/HT10 tên "Thửa đất…" in dưới dòng tên chính sách (stt '-').
  `chinh_sach.py`: `loai`, `ten_ngan`, `dong_on_dinh` (ĐG = kg × giá gạo × tháng, tỷ lệ riêng), `dong_dao_tao` (theo thửa, tỷ lệ 150%),
  `dong_thue_nha`/`tinh_lai_thue_nha`; `BoSoan.them_dong_ho_tro`. `doc_ty_le` cho phép tới 500%. Đơn giá danh mục sửa được (dòng
  → nhập tay, `can_cu_gia` ghi giá danh mục). `nghiep_vu._dao_tao_theo_thua` tắt so khớp quy tắc gộp HT09. DT đất NN đang sử dụng
  trống = DT đất NN mục 1. Màn hình chính: `the_so` (thẻ số liệu), `bang_th` (thẻ tổng hợp, cột `COT_TONG_HOP`, chung
  selectionModel với `bang`). `OTimChon`: danh sách gợi ý là cửa sổ ToolTip không giữ bàn phím (bộ gõ tiếng Việt). Logo:
  `logo_PABT.png` → `tao_bieu_tuong.py` → `pabt/bieu_tuong.ico/.png` (biểu tượng exe đổi khi dựng lại bộ cài).
- 0.9.12: thẻ hồ sơ (`KhungHoSo`): cột vị trí ẩn (`COT_AN`, dữ liệu vẫn lưu), nguồn gốc giãn hết bề rộng (`ONguonGoc`: sửa nhiều
  dòng, ô dài tự thu nhỏ chữ / cắt "…"), dòng cao tối đa `CAO_DONG_TOI_DA`; thao tác thửa/hộ trong nút "+ Thêm thửa" + menu "Thao tác
  khác" (`self.nut` chứa QAction). Bản in: `in_an.dat_doan_van` (ô `{nguon_goc}` cao vừa số dòng chữ, quá 409 pt chia nhiều dòng),
  `vua_chu` (dòng "Dự án:" sát chữ, đường kẻ kéo lên theo), đo chữ bằng Qt (`_ham_do_chu`, không có Qt thì ước theo ký tự);
  `duong_ke_cua_mau` (mẫu sửa trong Excel còn hình vẽ thì lấy đường kẻ trong mẫu), `mau_de_sua`, `xem_truoc` (nút trong `HopIn`).
  Quyết định: `quan_ly.doc_van_ban` (PDF scan / ảnh → `ocr.py`, Tesseract tìm ở PABT_TESSERACT / `tesseract\` cạnh exe /
  `%APPDATA%\PABT\tesseract` / Program Files / PATH; ảnh <2000 px phóng lên ~300 dpi; Qt5 lấy luồng JPEG của trang bằng pypdf),
  `so_ngay_qd` (dòng "Số:" đầu văn bản, "Kèm theo Quyết định số…", bỏ qua dòng "Căn cứ"), `doc_qd_mot_ho` (dòng của hộ trong
  danh sách - bản scan so tên gần đúng `_tim_dong_ho`, kiểm tra cộng cột `_cong_khop`; QĐ 1 trường hợp = tổng QĐ), dùng trong
  `HopTrangThai.doc_quyet_dinh` (chọn file → hỏi → điền, chưa lưu). `HopNhapQD` cũng OCR bản scan.
- 0.9.12 (tiếp) CSDL v10: `quyet_dinh` + `qd_ho` (một hộ nhiều quyết định - phê duyệt bổ sung; tiền từng hạng mục, PA / QĐ chi
  tiết, chi trả theo từng QĐ: ngày, số tiền, `chung_tu`, `ly_do_chua_nhan`), `ho.ly_do_ban_giao/bien_ban_ban_giao`; `_NANG_CAP[9]`
  chuyển phê duyệt cũ thành quyết định ("@quyet_dinh" = phần cuối schema.sql). Logic `theo_doi.py` (`ghi_qd_ho`, `ghi_chi_tra`,
  `ghi_ban_giao`, `tong_hop` -> `TongHopHo`, `hop_loc`/`LOC_TIEN_DO`, `xuat_excel`); cột ho.da_phe_duyet/qd_*/da_chi_tra/chi_tra_*
  là tóm tắt (`dong_bo_ho`); `quan_ly.cap_nhat_trang_thai` / `ap_quyet_dinh` kiểu cũ đi qua `theo_doi.ghi_kieu_cu` /
  `nhap_tu_ket_qua`. Màn hình `man_hinh_theo_doi.py`: `KhungBangTongHop` (KhungTongQuat mỗi thửa một dòng, KhungQuyetDinh,
  KhungTongHopTien), `KhungTienDo`, `HopHoTheoDoi` (Trạng thái MỘT hộ; nhiều hộ vẫn `HopTrangThai`), `HopQDHo`. Cửa sổ chính:
  danh sách gọn 6 cột (`COT`, dòng dict có `ma_ho`), trang bên phải `self.trang` (QStackedWidget) chọn ở menu trái (`TRANG`,
  `mo_trang`); bỏ thẻ "Tổng hợp sau áp giá" và menu Quy chuẩn (lệnh `quy_chuan` còn giữ).
  Đọc quyết định: `pdf_bang.py` (PDF có chữ: pypdf layout, hàng đánh số cột 1..N -> cột, `loai_cot` phân loại cột tiền, `_gom_cot`
  gom họ tên nhiều dòng; `chu_chu_ky`/`dien_so_ky`: số, ngày đóng kèm chữ ký số), `quan_ly.khop_ten` (Ông A; bà B / thừa kế),
  `doc_quyet_dinh_nhieu` (QĐ + bảng kèm theo nhiều file), `so_truong_hop`. requirements.txt thêm pypdf.
  Hoàn tác: `hoan_tac.py` (TEMP trigger -> `_ht_nhat_ky`, bước = các COMMIT trong một thao tác (set_trace_callback + QTimer 0),
  tên từ `csdl.ghi_nhat_ky` qua `csdl.HOAN_TAC`); `giao_dien.xu_ly_hoan_tac` (Ctrl+Z/Y ngoài ô chữ: `hoan_tac_phim` của widget
  gần nhất), `BangHoanTac` (sửa ô QTableWidget), `CuaSoLapPA.hoan_tac` (lịch sử bản phương án chưa lưu trong `cap_nhat`).
  Tốc độ: `phong_to` gộp các nấc (áp kiểu một lần sau 220 ms, `cho_ms=0` áp ngay), `_bo_dau`/`_khoang_duong_kinh` lru_cache,
  `man_hinh.ds_chon_nhanh` nhớ trên DanhMuc + `lam_san` lúc rảnh. Dự toán: hàng "Thêm đất" (`HopDuToan.them_dat`, loại đất
  `loai_dat.ds_chon`), khái toán luôn có mục I đất, bỏ dòng "TỔNG DỰ ƯỚC KINH PHÍ: …" đầu bảng. `OTimChon.TOI_DA` 20000.
- 0.9.13 cập nhật từ web: `nhap_don_gia.quet` (đường dẫn / từ khóa -> `CONG_BAO_DONG_NAI` seek; vào trang chi tiết cùng máy chủ
  `cham_diem` >= 5, lấy file "Tải tập tin" `?download=1&id=0`) -> `TaiLieu` (`so_hieu`, `nhom`, `da_co` theo `van_ban_da_co`, tự `chon`);
  `man_hinh_quet_web.HopQuetWeb` tải -> `doc_bang_ocr` -> `phan_tich_van_ban` -> `HopNhapDonGia(dong=, van_ban=)` theo ngày ban hành.
  `loai_that` (theo nội dung: HTML giả .pdf, .doc/.xls OLE) -> `chuyen_office` (Word / Excel qua cscript VBS); `LoiPdfScan`.
  `nhan_muc` phân cấp (La Mã = nhóm, dòng không giá = cha, STT trống/-/a/* = con "Cha - Con", nhãn giá "Đông Xuân: x" -> "Tên (Đông
  Xuân)", bỏ "(Mật độ…)" khỏi cha), `Muc.nhom`; `so_khop(ds, None)` theo nhóm từng dòng + `_khoa_gon` + gần đúng `GAN_DUNG` cùng ĐVT.
  `ap_dung(..., van_ban=)` ghi số hiệu vào `van_ban`; văn bản đã có -> dòng mặc định không chọn (QĐ 48/2025 đã bị QĐ 66 sửa giá).
  Phần web (`cap_nhat_web.py` + `man_hinh_quet_web.py`) PHÁT HÀNH RIÊNG bằng gói .pabtcn: PyInstaller (DUNG_EXE/DUNG_BO_CAI.bat,
  `dung_exe38.LOAI_TRU_WEB`) `--exclude-module` hai module này + `--hidden-import html.parser urllib.request difflib`; bộ cài
  0.9.13 = gốc, gói 0.9.14 thêm web (`man_hinh_don_gia.cap_nhat_web` ImportError -> hướng dẫn cài gói). Đừng import
  `cap_nhat_web` từ module khác của bộ cài gốc.
- An toàn (`an_toan.py`, gọn từ 0.9.16 - người dùng bỏ màn hình "Kiểm tra an toàn", quét virus chủ động MpCmdRun / AMSI,
  toàn vẹn bản cài `toan_ven.json`, chữ ký số; ĐỪNG thêm lại): chỉ còn `ngu_canh_tls` (mọi urlopen), `kiem_tra_zip` /
  `kiem_tra_xml`, `LoiAnToan`. Gói cập nhật: `doc_goi`/`cai` kiểm tra SHA-256 từng file + zip; `nap_cap_nhat._kiem_ban` kiểm
  lại SHA-256 + file lạ, xóa `__pycache__`, `dont_write_bytecode`. tu-kiem bước "HTTPS". VBS Word/Excel: `AutomationSecurity = 3`
  (tắt macro - BẮT BUỘC giữ: Office tự động hóa mặc định cho chạy macro).
- In hàng loạt: `in_an.chay_excel(bao=)` Popen + VBS in "XONG\t<i>" mỗi file, file cờ dừng (đối số 2); canh giờ từng file
  `CHO_MOI_FILE` (+`CHO_KHOI_DONG` file đầu) -> `_tat_excel_tu_dong` (EXCEL.EXE -Embedding khởi động sau mốc); lỗi `DA_DUNG` /
  `LOI_TREO`. `xuat_hang_loat(bao_tien_do -> True = dừng, bao_excel)`; `HopIn.thuc_hien` QProgressDialog nút Dừng.
- "Đã lập phương án" = `in_an.phan_loai_lap` ('da_lap' / 'tu_lap' / 'chua'): `du_an_moi.tu_lap_phuong_an` lưu
  `BoSoan.luu(tu_dong=True)` -> trạng thái `lap_pa.TU_LAP`; file cũ: hộ lưu hàng loạt (>= `HANG_LOAT_TOI_THIEU` hộ, cách nhau <=
  `HANG_LOAT_GIAY`) = tự lập. Dùng ở `HopIn` (bảng `bang_ho` đánh dấu chọn, phạm vi 'chon'/'pa'/'tu_lap'/'co_pa'/'tat_ca'/
  'tu_chon', `ds_ho()` = hộ đang đánh dấu; `o_gop` -> `in_an.gop_pdf`, `o_so_ban` -> `chay_excel(so_ban)` VBS "in:N") và thẻ
  `da_pa` màn hình chính. `ho_co_phuong_an` (mọi hộ có dòng) vẫn dùng cho Dự án mới xuất 2 bảng.
- Băng tiêu đề `giao_dien.BangToChuc` (paintEvent: nền `MAU_BANG`, họa tiết `_luoi_thua`, thửa vàng `_THUA_THU_HOI`, vạch vàng).
  `bang_to_chuc(phai, nut=)`: dòng phụ chỉ "Trực thuộc … • địa chỉ" (bỏ chữ "Tổ chức làm nhiệm vụ bồi thường" - người dùng yêu cầu);
  nút Hoàn tác / Làm lại (`CuaSoChinh.nut_ht`, `vai="nut_bang"`) đặt cùng dòng tên phần mềm, không còn ở thanh trạng thái.
- Menu trái gọn: `menu_trai(nhom, xo=('Dự án',), dong_mac_dinh=app.NHOM_DONG_MAC_DINH)` - nhóm trong `xo` = một nút QMenu xổ
  (`khung.nut_xo`); nhóm khác có tiêu đề `NhanBam` (QLabel, không phải nút: `to_mau` không tô màu theo chữ) bấm đóng / mở
  (`khung.tieu_de_nhom[ten].bam()`, `khung.nhom_dong`), nhớ ở QSettings `KHOA_NHOM_DONG` (chuỗi nối "|", "|" = không nhóm nào
  đóng - tránh QSettings Qt5 trả list một phần tử thành str). Nút lệnh cao 32 px. App: `self.khung_menu`.
- Tốc độ (0.9.15): `csdl.mo` trả `csdl.KetNoi` (lớp con sqlite3.Connection có `bo_nho`); `csdl.nho(con, khoa, tao)` nhớ giá trị
  theo (total_changes, PRAGMA data_version) - tự đọc lại khi kết nối này / máy khác ghi; KHÔNG nhớ khi `con.in_transaction`
  (rollback không đổi total_changes). `BoiCanh.tu` dùng `nho` -> đối tượng DÙNG CHUNG: không sửa `bc.thua/ts/hotro...`; cần thửa
  của một hộ dùng `bc.thua_cua(ma_ho)` (chỉ mục dựng một lần, thứ tự thu_tu, ma_thua) thay vì duyệt cả `bc.thua`. Ghi mà không đụng
  bảng của bối cảnh (thua, tham_so, du_an, cai_dat, bieu_thuong, dm_loaidat, dm_hotro) thì giữ bộ nhớ: `truoc = csdl.trang_thai_nho(con)`
  trước khi ghi, `csdl.giu_nho(con, ('BoiCanh', BoiCanh), truoc)` sau khi ghi (như `BoSoan.luu`). `hoan_tac._tao_trigger` commit
  ngay (INSERT temp mở giao dịch ngầm - trước đây kết nối "giữa giao dịch" suốt phiên). `du_an_moi.tao_du_an`: `synchronous = OFF`
  trên kết nối file mới + `_ghi_xuong_dia` (fsync một lần). Bản in: gộp ô bằng `in_an._gop_o` (không dùng `ws.merge_cells`: openpyxl
  so vùng mới với mọi vùng đã có + băm viền từng ô - O(n²)); `_dinh_dang_gop` = `_clean_merge_range` + `MergedCellRange.format` có nhớ
  mã viền, kết quả giống hệt (tests/test_toc_do.py so với merge_cells). Đo: 1.000 hộ tạo dự án 13,2 s -> 0,9 s, bảng tổng hợp 13,3 s -> 2,0 s.
- Tải lớn (3.000 hộ / 5.000 thửa, `tests/test_toc_do.py`): tính / kiểm tra cả dự án dùng `nghiep_vu.doc_tat_ca_phuong_an(con,
  ds_ma_ho=None)` (3 truy vấn, cùng thứ tự dòng với `doc_phuong_an`; `tinh_tat_ca`, `doi_chieu` - đọc MỘT lần cho cả tinh_pa và
  kiem_tra_pa -, `in_an.lap_bang_tong_hop`, `theo_doi.tong_hop`, `quan_ly.du_lieu_tong_hop`) - đừng gọi `tinh_ho`/`doc_phuong_an`
  trong vòng lặp hộ. Bảng lớn: `horizontalHeader().setResizeContentsPrecision(300)` (canh cột đo mẫu); `man_hinh_theo_doi`:
  `_o` dùng hằng `_CANH_PHAI/_CANH_TRAI`, ô tìm `_Khung._tim_khi_go` (chờ `CHO_GO_MS` mới vẽ; `im_lang` vẽ ngay), chuỗi tìm
  không dấu nhớ trên đối tượng `_chuoi_tim`, `_loc_nho` (ve/dong/đếm lọc một lần), `KhungTienDo.nap` khi ẩn chỉ đánh dấu
  `_can_nap`, nạp ở showEvent. Việc nặng không đụng widget / kết nối của cửa sổ chạy nền bằng `giao_dien.chay_nen(cha, ham,
  chu)` (QEventLoop ExcludeUserInputEvents + hộp chờ sau `HIEN_CHO_SAU_MS`; ném lại lỗi): `HopDuAnMoi.tao` (tao_du_an),
  `app.nhap_excel` (nhap_tho/nhap_excel tự mở kết nối), `app.nhap_chi_tiet` (chỉ `doc`). KHÔNG chạy nền mã dùng Qt (in_an đo chữ
  bằng Qt, QtPdf) hay `self.con`. Nhập chi tiết: `nhap_chi_tiet.ChiMucTrung` (chỉ mục CCCD / tên một lần, `ghi_nhan` sau mỗi hộ
  thêm / thay) thay `ho_trung` trong vòng lặp. `quan_ly.khop_ten`: lọc cận trên (độ dài = real_quick_ratio, `_dem_ky_tu` =
  quick_ratio) >= `NGUONG_LOC` trước `SequenceMatcher.ratio()` - kết quả như cũ. `in_an._vung_gop` = MergedCellRange(ws, vùng)
  có nhớ viền. Không dùng `IN (?,?…)` với danh sách hộ (giới hạn tham số SQLite cũ). Đo 3.000 hộ / 5.000 thửa: xem HUONG_DAN 0.9.15.
- 0.9.16 trình phê duyệt (CSDL v11, `_NANG_CAP[10]`): `ho.so_pa/ngay_pa` (số / ngày PA chi tiết), `dot_trinh.loai_van_ban/
  so_pa_tong/ngay_pa_tong`; `quan_ly.Dot.van_ban_trinh`, `dat_so_pa`, `danh_so_pa`, `so_pa_cua_ho`; `theo_doi.ghi_qd_ho` hộ mới vào
  QĐ mang theo số PA. `in_an.dien_so_ngay` điền chỗ chừa "Số:      /" và "ngày … tháng … năm {nam}" (PA chi tiết: số của hộ;
  bảng tổng hợp: `lap_bang_tong_hop(so_pa_tong=, ngay_pa_tong=)` vào "Phương án số …/"). `van_ban_trinh.py`: mẫu TO_TRINH
  (.docx / .xlsx) + PA_TONG (.docx) ở `<thư mục máy>\mau_in` (mẫu riêng; không có -> mẫu mặc định dựng lại mỗi lần ở
  `mau_in\mac_dinh`, byte giống hệt để nhận ra), `them_mau` (.doc / PDF -> Word chuyển .docx: PDF dùng 'docx_hien' - Word hiện hộp
  hỏi, không tắt được bằng tự động hóa), `mau_de_sua`, `khoi_phuc_mac_dinh`, `du_lieu` (DS_CHO_TRONG, {ho.…} = mỗi hộ một dòng
  bảng), `dien_docx` (gom chỗ trống Word tách qua nhiều w:t - `_gom_doan`), `dien_xlsx`, `chay_word`, `xuat_bo_ho_so` (thư mục
  `PA CHI TIET` / `PA TONG`, chọn từng mẫu). `quan_ly.xuat_dot(..., chi_tiet, bang_tong_hop, to_trinh, pa_tong)`. Màn hình:
  `HopSuaDot` (văn bản trình, PA tổng), `HopDanhSo`, `HopDotTrinh` (cột Số PA chi tiết / Ngày PA sửa trực tiếp, khung mẫu, chọn
  mẫu xuất, bấm đúp đợt = sửa; chưa chọn đợt -> báo, không im lặng), `HopIn` (ô Đợt trình, o_tt/o_pat, `chon_mau`, o_chia 2 thư
  mục). `csdl.chep_danh_muc` chỉ ĐỌC file nguồn (chép theo cột chung) - không còn nâng cấp bộ đơn giá đóng gói tại chỗ.
  `giao_dien.cai_bat_loi` (gọi trong `app.main`): lỗi trong nút bấm -> hộp báo + `<thư mục máy>\loi.log`.
- Tốc độ (0.9.16): `csdl.DauVetHo` (TEMP trigger ghi mã hộ bị ghi vào `temp._dv_ho`, sổ chỉ thêm dòng; `lay()` ->
  set hộ đổi / None = nạp toàn bộ khi thêm-xóa-đổi thứ tự hộ, ghi bảng không có `ma_ho`, máy khác ghi - `PRAGMA data_version`) gắn
  trong `app.mo` (lỗi -> None, vẫn mở). `CuaSoChinh.tai_lai` = `_tai_lai_ho` (`doi_chieu(con, ds_ma_ho=)`, `BangHo.thay_dong`, ≤
  `TAI_LAI_HO_TOI_DA` hộ) hoặc `_tai_lai_toan_bo`, rồi `_sau_tai_lai`; dòng dựng ở `_so_lieu_dong` + `_dong_ho` (3.000 hộ: lưu 1 hộ
  rồi tải lại 0,58 s -> 0,05 s; `tests/test_tai_lai.py` so với nạp toàn bộ). Trong trigger TEMP không được viết `temp.` trước tên bảng.
  `BoiCanh.muc_thuong` (biểu thưởng đổi số + sắp xếp một lần). openpyxl không nạp lúc mở phần mềm / mở dự án: `app` nạp `doi_chieu`,
  `nhap_excel`, `nhap_tho` trong hàm; `doi_chieu` nạp openpyxl trong `xuat_bao_cao`; `man_hinh` nạp `in_an` trong `HopIn`;
  `phan_loai_lap` + `HANG_LOAT_*` chuyển sang `lap_pa` (in_an giữ tên). `lap_pa._bo_dau` = `str.translate(_BANG_BO_DAU)`, ký tự còn
  lại không "ổn định" (`_on_dinh`) thì tách dấu NFD như cũ - giống hệt (`TestBoDauNhanh`). `csdl.ten_may()` = `socket.gethostname()`
  thay `platform.node()` (cùng giá trị, không qua WMI). Kiểm tra máy chủ LAN qua `man_hinh_may_chu.ket_noi_duoc(cha, goc)`
  (`chay_nen`). Số người gõ / ô chữ trong file: `tien.doc_so_vn` (chấm ngăn nghìn chỉ khi nhóm đầu không bắt đầu bằng 0; "1,500,000"
  kiểu Anh) - dùng ở `lap_pa.doc_so`, công thức, `theo_doi._tien`, `nhap_tho._doc_dt`, `nhap_excel._so*`, mật độ cây, chi tiết QĐ;
  KHÔNG dùng `D()` cho chữ người gõ (D đọc chuỗi lưu CSDL: '1.07'). `nhap_don_gia.doc_gia` / `pdf_bang._so_tien` giữ nhận dạng riêng.
  Hộp thoại tạo với cha (cửa sổ chính / trang) KHÔNG tự xóa khi đóng (trước 0.9.16 mở cửa sổ lập PA 20 lần = 20 cửa sổ ẩn, ~5.800
  thành phần): lệnh cửa sổ chính (`self.lenh`, nút nhanh, bấm đúp, chuột phải) chạy qua `CuaSoChinh._chay_lenh` ->
  `don_hop_da_dong` (deleteLater hộp ẩn khi không còn hộp modal); hộp mở từ nút của trang bên phải được dọn ở lệnh kế tiếp. Đừng
  giữ hộp thoại làm thuộc tính để dùng lại (sẽ bị xóa). QMenu tạm sau `exec` -> `deleteLater`. `LocHo.dat`: Qt 6.10+ dùng
  `beginFilterChange/endFilterChange` (invalidateFilter lỗi thời), Qt5 vẫn `invalidateFilter`.
  `kiem_tra_giao_dien.py`: PySide6 6.11 KHÔNG cho gán đè `QMenu.exec` trên lớp (vẫn gọi hàm C++) -> bắt sự kiện Show của QMenu
  (bộ lọc sự kiện toàn ứng dụng) rồi chạy từng mục; thời gian CHẬM là thời gian riêng (trừ thao tác con); đếm hộp ẩn sau mỗi lệnh.
- 0.9.16 BẢN THỬ NGHIỆM (người dùng yêu cầu): `pabt.BAN_THU_NGHIEM` / `NHAN_THU_NGHIEM` -> nhãn vàng `QLabel[vai="thu_nghiem"]`
  dưới phiên bản trên `bang_to_chuc` (cả băng Dự án mới), `app.TIEU_DE_CUA_SO`, Giới thiệu, `tu-kiem`. Bản chính thức: False.
  CHỮ KÝ SỐ ĐÃ BỎ HẲN (người dùng yêu cầu "bỏ sạch hoàn toàn các lệnh chữ ký, bản vá cập nhật không check chữ ký"): không
  còn khóa, `ky`/`xac_minh`/`tao_khoa`, `tao_khoa_ky.py`, `cap_nhat.sig` (gói cũ có file này: bỏ qua). Đừng thêm lại chữ ký.
  Bản cài 0.9.13-0.9.15 (mã cũ đòi chữ ký) TỪ CHỐI gói mới -> cài bộ cài 0.9.16 một lần. Test: `test_cap_nhat.test_khong_chu_ky_so`,
  `test_an_toan.TestDaBo`. Chữ ký số trên PDF quyết định (`pdf_bang.chu_chu_ky`/`dien_so_ky`) là tính năng ĐỌC văn bản - giữ.
- Xóa hộ trên danh sách (0.9.16): lệnh `Xóa hộ…` (`CuaSoChinh.xoa_ho(ds_ma_ho=, xac_nhan=)`, menu trái nhóm Hồ sơ và
  phương án, chuột phải `_menu_ho`, phím Delete = QShortcut WidgetShortcut trên `self.bang`; tắt khi chỉ xem) -> hộ đang chọn
  (`ho_da_chon`) -> `ho_so.thong_tin_xoa` (số thửa, dòng PA, QĐ, đã nhận tiền - hiện trong hộp hỏi, tối đa `XOA_HIEN_TOI_DA` dòng)
  -> `ho_so.xoa_nhieu_ho` (một giao dịch = một bước Hoàn tác, `_danh_lai` một lần; `xoa_ho` gọi lại hàm này). Test:
  `test_ho_so.TestManHinhHoSo.test_xoa_nhieu_ho_tren_danh_sach`.
- Dựng trong Git Bash: PATH có `C:\Program Files\Git\mingw64\bin` -> PyInstaller từng kéo nhầm `libssl-3-x64.dll` /
  `libcrypto-3-x64.dll` của Git (+6,5 MB); `PABT.spec` lọc bỏ binary từ thư mục git / mingw64 / msys64; `dung_exe38.py` bỏ các
  thư mục đó khỏi PATH khi gọi PyInstaller 5.
- Qt5 (bản Win7): `QMenu.exec_` có cả dạng tĩnh lẫn dạng thường - bí danh `QMenu.exec = QMenu.exec_` làm phần mềm SẬP (0xC0000005)
  khi mở menu bật lên (chuột phải danh sách hộ, Tra cứu văn bản mới); `_qt5_lam_qt6` dùng `lambda self, *a: self.exec_(*a)`.
  Test `test_giao_dien.TestMenuBatLen` (chạy cả venv38_32). `kiem_tra_giao_dien.py` chạy được bằng venv38_32 (`import pabt` trước
  khi nạp Qt). Máy dựng đã có Python 3.8.10 32-bit ở `%LOCALAPPDATA%\Programs\Python\Python38-32` (vị trí thật). CHÚ Ý: ứng
  dụng Claude (MSIX) ảo hóa `%LOCALAPPDATA%` - venv38_32 tạo trong phiên Claude nằm thật ở
  `%LOCALAPPDATA%\Packages\Claude_pzs8sxrjxfjjc\LocalCache\Local\PABT_dev\venv38_32`, chỉ phiên Claude thấy; chạy DUNG_BO_CAI.bat
  ngoài Claude thì chạy CAI_DAT_PHAT_HANH.bat trước. Đừng xóa thư mục đó (không phải bản trùng).
- Dọn bản cũ (09/10/2026, người dùng yêu cầu): chỉ giữ bộ cài / gói mới nhất trong `bo_cai\`; bản cũ, sao lưu, file trung gian dựng
  -> Thùng rác (không xóa vĩnh viễn). Bỏ `THU_MENU_TRAI.bat`, `so_sanh_giao_dien\` (thử menu trái 0.9.3 - nay là mặc định).
- Git (từ 09/10/2026): repo cục bộ ở thư mục dự án, `.gitignore` loại `.venv`, sản phẩm dựng, `*.pabt*`, `*.xlsm`, `du_lieu/`,
  `bo_cai_win/*.exe`. Git for Windows ở `C:\Program Files\Git\cmd\git.exe` (PowerShell mở trước khi cài chưa có trong PATH).
- Thông báo có danh sách dài (kết quả nhập Excel / nhập chi tiết / Dự án mới, lỗi nhập): `giao_dien.hop_ket_qua(cha, tóm tắt,
  [dòng], tiêu đề danh sách, canh_bao=, hien=False khi test)` - ô cuộn, đủ mọi dòng, nút Chép / Đóng, `vua_man_hinh`; KHÔNG ghép
  danh sách vào QMessageBox (giãn theo chữ, đẩy nút OK ra ngoài màn hình). `nhap_chi_tiet.ket_qua(bc)` -> (tóm tắt, cảnh báo).
- Số lượng mục 2-4 trên bảng nhập: `tien.so_luong_vn` (luôn >= 1 chữ số thập phân "20,0"; số nhiều chữ số lẻ hơn hiện đủ, tối đa 4) ở
  `BoSoan.o_khoan` - người dùng yêu cầu "dạng kế toán". QĐ 31/2025/QĐ-UBND ngày 29/08/2025 (vật nuôi; Công báo còn một QĐ 31/2025
  ngày 10/04/2025 về canh tác hữu cơ - trước sáp nhập, trùng số; tìm theo số chỉ ra bản này, tìm "vật nuôi" mới ra bản đúng): từ 0.9.17
  bộ tích hợp (2026.10.09) có 17 mục `VN01`-`VN17` (nhóm 3, phân loại `don_gia.PHAN_LOAI_VAT_NUOI`, thẻ "Vật nuôi" của `HopBoDonGia`)
  thêm bằng `tao_bo_don_gia.py --bo-sung` (`BO_SUNG` / `SUA_VAN_BAN`; đóng gói lại từ Excel cũng tự thêm). Tên = đúng tên
  `muc_tu_loi_van` đọc văn bản thật (cập nhật lại từ web -> "giữ nguyên"; test `test_don_gia.test_vat_nuoi_qd31`). Giá Điều 4 đã
  theo thời gian nuôi (= 70% / 50% của Điều 3) - không nhân thêm. Số lượng ĐVT "ha/…" và đơn vị bội "100m3/vụ": 4 chữ số thập phân
  (`lap_pa.so_le_so_luong`; trước đây "ha/vụ" làm tròn 1 chữ số: 0,25 ha -> 0,3).
- Văn bản không có bảng giá (đơn giá viết trong điều khoản - QĐ 31/2025 vật nuôi): `HopNhapDonGia` không ra dòng từ `nhan_muc` thì
  `nhap_don_gia.muc_tu_loi_van(dong, nhom)` -> ([Muc], [câu cần xem]): `_khoan_van` ghép dòng PDF / đoạn Word thành khoản (tách ở
  Điều / 1. / a) / - và sau ; : .), `_RE_GIA_VAN` "<số> [triệu|nghìn] đồng/<ĐVT>[ mặt nước…]", tên = chữ trước số tiền (`_ten_gon` bỏ
  "Đơn giá bồi thường đối với…", "… là"), tiêu đề khoản không giá kết thúc ":" (hoặc phần trước ":" trong cùng khoản) -> "Tiêu đề -
  Mục"; khoảng giá "từ… đến…", tỷ lệ % -> danh sách xem (không tự lấy). `tu_loi_van`: sửa được Tên / ĐVT trên bảng (`_sua_o` -> so
  khớp lại). Văn bản `da_co`: chỉ bỏ chọn sẵn dòng ĐỔI GIÁ, mục mới vẫn chọn. `ap_dung` văn bản đã có -> UPDATE dòng `van_ban` cũ
  (không thêm dòng trùng). Test: `tests/test_nhap_don_gia.TestLoiVan` (văn bản GIẢ LẬP, không phải giá thật).
  0.9.17 (thử trên văn bản thật QĐ 31 - bản 0.9.15 chỉ thử văn bản giả lập, tên mục sai): điều kiện đứng SAU số tiền ("… là A
  đồng/ha/vụ đối với thủy sản nuôi dưới 50%…, B đồng/ha/vụ đối với …") -> `_dieu_kien` (hết ở dấu kết câu `_ket_cau` / dấu phẩy
  trước tên mới) ghi "(điều kiện)", mức giá nối tiếp dùng lại tên (`goc`); tiêu đề khoản không có ":" (`_la_tieu_de`: cấp 1-3, ngắn,
  không dấu kết câu, không giá) và `_khoan_van` tách sau dòng tiêu đề khi dòng kế bắt đầu chữ hoa (đoạn Word); `_RE_CAU_MOI` tách
  "<tiêu đề> Đối với … là" (dòng PDF ghép); `_RE_DAN_CHUNG` ("các hình thức nuôi như:") không làm tên nhóm; giá trần `_RE_TRAN`
  ("theo giá thị trường nhưng không quá") -> "(theo giá thị trường, tối đa)"; `_RE_DAU_KHOAN`: "50.000.000 đồng" đầu dòng không
  phải ký hiệu khoản "50.000.". `so_khop` gần đúng phải giống cả phần ngoài lẫn trong ngoặc (`_giong_tung_phan`; trước đây "tôm
  nước lợ - quảng canh (dưới 50%…)" khớp 93% "tôm nước ngọt - thâm canh (dưới 50%…)" -> ghi đè giá mục khác). Không có đơn giá ->
  `nhap_don_gia.LoiKhongCoGia` (HopNhapDonGia); `HopQuetWeb.tai_va_phan_tich` chỉ báo "không tìm thấy đơn giá" với lỗi này, LoiNhap
  khác báo đúng lý do (trước: mọi lỗi -> "không có bảng đơn giá"). `cap_nhat_web.quet` từ khóa có số hiệu ("31/2025"): liên kết
  mang đúng số đó luôn được mở (`so_tim`, không khớp 131/2025).
- Đơn giá riêng của dự án (`don_gia_rieng.py`, cửa sổ `man_hinh_don_gia_rieng.HopDonGiaRieng`, lệnh "Đơn giá riêng dự án…" /
  nút trong `HopBoDonGia`): KHÔNG đổi cấu trúc CSDL - dùng bảng `quy_uoc` của dự án. id < `ID_RIENG` (1.000.000) = dòng của bộ đơn giá;
  id >= ID_RIENG = dòng riêng (nhập tay / sửa từ dòng của bộ / thẩm định giá) -> `don_gia.ap_vao_du_an` giữ lại (`doc_rieng` trước,
  `tra_rieng` sau `chep_danh_muc`; dòng của bộ trùng tên thực tế với dòng riêng thì bỏ). Dòng thẩm định: `ten_tuong_duong =
  TD_THAM_DINH` ('Đơn giá thẩm định'), `can_cu` = `can_cu_tham_dinh(...)` (chứng thư, ngày, đơn vị, QĐ phê duyệt, "tài sản đặc biệt
  theo QĐ 18/2026/QĐ-UBND"). Ghi qua `luu` / `them_tham_dinh` (mo_khoa_danh_muc + ghi_nhat_ky). Đọc file: `doc_file_tham_dinh` =
  `nhap_don_gia.nhan_muc`, không bảng thì `muc_tu_loi_van`; `thong_tin_chung_thu` dò số chứng thư / ngày / đơn vị.
  `BoSoan.them_tu_danh_muc` nhận mục nguon 'quyuoc' (dòng tên thực tế + `ap_gia_tuong_duong`; thẩm định -> căn cứ "Đơn giá thẩm
  định: … ; <chứng thư>"). `man_hinh.ds_chon_nhanh` mục 2, 3: các dòng muc[9] đứng đầu, nhãn [Quy ước] / [Thẩm định]. Test:
  `tests/test_don_gia_rieng.py` (số liệu thẩm định GIẢ LẬP).
- Nguồn web (`cap_nhat_web`): `NOI_TIM` {mã: (tên, mẫu https có {q})} - dongnai / vbpl / tvpl; `NGUON_GOI_Y` (tên, nguồn) với nguồn
  "mã|từ khóa", từ khóa trơn (Công báo Đồng Nai) hoặc URL trang danh sách (vanban.chinhphu.vn, congbao.chinhphu.vn). `noi_tim()` /
  `nguon_goi_y()` cộng thêm `nguon_web.json` trong thư mục máy (`PABT_THU_MUC_MAY` / %APPDATA%\PABT); `duong_dan(nguon, noi)` ->
  URL; `quet(..., noi=)`. Mẫu tìm vbpl / tvpl CHƯA thử được từ môi trường phát triển (mạng chặn) - lỗi thì sửa bằng nguon_web.json.
  `cham_diem`: nhóm 0 mà có thu hồi đất / bồi thường / TĐC / luật đất đai -> nhóm 4 (văn bản chính sách: ghi `van_ban` theo dõi).
  `nhap_don_gia._RE_SO_VB` / `_RE_SO_TRONG` nhận NĐ, TT, TTLT, QH; `phan_tich_van_ban` cơ quan Quốc hội / Chính phủ / Bộ…, loại
  Luật / Nghị định / Thông tư. `man_hinh_quet_web`: ô "Từ khóa tìm trên" (`cb_noi`); lịch sử QSettings bỏ địa chỉ máy nội bộ
  (`_MAY_NOI_BO`, test chạy máy chủ 127.0.0.1 từng ghi vào). Test: `TestApDung.test_nguon_trung_uong`,
  `test_lich_su_khong_nho_may_noi_bo` (số hiệu văn bản mới là GIẢ LẬP).
- 0.9.17 (tải lớn 10.000 thửa, lỗi ẩn): `bang_ao.BangAo` (QTableView + `_MoHinhAo`, API giống QTableWidget: `dat_du_lieu(dong,
  du_lieu, kieu, gop, khoa)`, `item(r, c)` trả `_OAo`, tín hiệu `cellDoubleClicked`; chiều cao dòng ƯỚC theo chữ - xem 0.9.22)
  cho `KhungTongQuat` / `KhungTienDo` (nạp 980 -> 182 ms). `thong_bao.py`: `TEN_UD` (một nguồn), `chu_loi(viec, e)` = "Việc. Lý do /
  Cách xử lý (`giai_thich`: quyền, file khóa, đầy đĩa, CSDL hỏng…) + chi tiết kỹ thuật" - dùng thay `str(e)` trong hộp lỗi.
  `giao_dien.con_tro_cho` (with: con trỏ chờ luôn trả lại khi lỗi - đừng `setOverrideCursor` không finally), `dat_trang_thai(nhan,
  muc, chu)` + `MAU_TRANG_THAI` (dat / tin / canh_bao / loi). `kiem_loi` / `du_toan.tu_du_an` đọc `doc_tat_ca_phuong_an` một lần
  (15.009 -> ~10 truy vấn; test `test_toc_do.TestKhongTruyVanTungHo`). `HopBoDonGia`: thẻ Nhà, công trình / Cây trồng / Vật nuôi
  (theo `_VAT_NUOI`), hàng nút gọn - `b_cap` (QMenu: từ file / từ trang web / tra cứu văn bản), `b_gia_dat` (tra / xuất), `b_don`,
  `b_ap`, Đóng (người dùng: 7 nút một hàng "chưa phù hợp").
- 0.9.18 bố cục màn hình 1366x768 (theo bản audit người dùng gửi; đo bằng phông Windows, tỷ lệ 110%): `bang_to_chuc` gọn 112 ->
  63 px (logo 46, chữ 17/12 px, phiên bản + BẢN THỬ NGHIỆM cùng hàng; GIỮ tên đơn vị, "Trực thuộc… • địa chỉ", Hoàn tác / Làm lại
  cùng dòng tên phần mềm - người dùng yêu cầu trước đây); chữ dài trên băng = `giao_dien.NhanRutGon` (một dòng, rút gọn "…",
  tooltip đủ, `text()` trả chữ đầy đủ; sizePolicy Ignored - không ép cửa sổ rộng ra). Cửa sổ chính: `lb_du_an` một dòng (số hộ /
  tổng tiền đã có ở thẻ số), `_hang_thao_tac` = băng đối chiếu `lb_ket_qua` + 2 nút (Lập PA, Thêm hộ) một hàng - bỏ nút Bảng tổng
  hợp / Theo dõi tiến độ (trùng menu trái); `_xoa_ket_qua`. Bảng hộ 8 -> 12 dòng nhìn thấy; rộng tối thiểu 1449 -> 1020 px (băng
  tiêu đề + hàng nút trang Quyết định phê duyệt - nay `XepDong`). `CuaSoLapPA.o_cb` chỉ hiện khi có điểm cần xem lại, cao theo số
  dòng. Màu: `giao_dien.kieu_trang_thai(muc, loai)` (một nguồn với `dat_trang_thai`), thẻ số liệu: `MAU_THE_SO` + `_qss_the_so`
  trong QSS chung (thẻ gắn `vai="the_so"`, `the=<khóa>`, WA_StyledBackground) thay 18 setStyleSheet cục bộ. KHÔNG thêm chờ ngừng
  gõ (debounce) cho ô tìm danh sách hộ: đo 5.000 hộ 24-51 ms/phím (dưới ngưỡng cảm nhận ~100 ms) - chờ 250 ms làm chậm hơn. Vẽ
  `BangToChuc` 0,9 ms/lần: không cần đệm ảnh. Test `test_giao_dien.test_bo_cuc_gon_man_hinh_1366` kiểm tra CẤU TRÚC (px phụ thuộc
  phông: offscreen không phông Windows chữ rộng gần gấp đôi).
- 0.9.19 mỗi lệnh một chỗ (người dùng yêu cầu rà nút trùng; quét bằng AST: chữ nút -> hàm được gọi): bỏ nút nhanh "Lập phương án
  hộ đang chọn" / "Thêm hộ…" (gọi thẳng hàm nên KHÔNG tắt khi chỉ xem -> lỗi ghi CSDL chỉ đọc), lệnh ẩn "Hồ sơ hộ…", mục máy chủ
  lặp trong `_menu_tai_khoan`, nút "Lưu phương án hộ" cuối thẻ 4 (`hang_dieu_huong`), nút "Quyết định, chi trả, bàn giao của hộ…"
  (KhungTienDo), lệnh + hàm `nhap_quyet_dinh` (cùng HopNhapQD với `KhungQuyetDinh.nhap_file` - nay truyền thư mục hồ sơ, file dự án
  lấy từ `PRAGMA database_list`). Trang "Quyết định phê duyệt" ở nhóm Trình, theo dõi tiến độ; "Quy chuẩn cây, tài sản…" lại có
  trên menu (nhóm Đơn giá, dự toán). Chuột phải danh sách hộ dùng lại QAction của menu trái (`self.lenh[...]`) - ĐỪNG thêm nút /
  mục gọi thẳng hàm của lệnh đã có QAction (mất trạng thái tắt khi chỉ xem). `mo_lap_pa` / `mo_ho_so(moi=True)` tự chặn `chi_doc`.
  `ho_da_chon` / `ho_dang_chon` theo trang đang xem (`_khung_dang_xem`, `_Khung.ma_da_chon`). Test `test_giao_dien.
  test_bo_cuc_gon_man_hinh_1366` (không QPushButton nào lặp chữ lệnh menu trái), `test_lenh_menu_trai_theo_trang_dang_xem`.
- 0.9.20 rà soát tải lớn (làm trên đám mây 08/10 trên nền 0.9.15, ghép vào 0.9.19 ngày 10/10; `tests/test_toc_do.TestRaSoatTaiLon`):
  - KẾT QUẢ DÙNG CHUNG: `nghiep_vu.ket_qua_ho(con)` = {ma_ho: (KetQuaHo, [cảnh báo kiem_tra_pa])} nhớ bằng `csdl.nho` (khóa
    `KHOA_KQ`). `tinh_tat_ca`, `doi_chieu` (cả dự án; `ds_ma_ho` của DauVetHo: dùng `ket_qua_ho_san` nếu còn đúng, không thì
    tính riêng các hộ đó), `theo_doi.tong_hop(tinh_pa=True)`, `quan_ly.du_lieu_tong_hop`, `in_an.lap_bang_tong_hop`
    dùng nó (`kiem_loi`, `du_toan.tu_du_an`: chỉ `ket_qua_ho_san` khi bối cảnh đúng lớp `BoiCanh` - bảng nhớ cũ thì tính trên
    phương án vừa đọc, không đọc lại lần 2 - gọi `ket_qua_ho` ở đây làm Kiểm tra lỗi 3.000 hộ chậm 0,5 -> 0,64 s) - KHÔNG tự `tinh_pa` cả dự án, KHÔNG sửa đối tượng
    trả về. `BoSoan.luu` -> `giu_ket_qua_ho(con, [ma_ho], truoc)`: chỉ tính lại hộ vừa lưu (bản dict mới; hộ khác giữ nguyên đối
    tượng). `ket_qua_ho_san(con)`: lấy nếu đang nhớ (không tính). `hoan_tac._xoa` (xóa bảng temp) -> `csdl.giu_tat_ca` (total_changes
    đếm cả bảng tạm: trước đây sau 50 bước mọi lần lưu làm mất bộ nhớ đệm).
  - GIAO DỊCH LỒNG: `with con:` lồng trong `with con:` của sqlite3 COMMIT ngay ở tầng trong -> hàm ghi dùng chung (`theo_doi`
    ghi_qd_ho / ghi_chi_tra / ghi_ban_giao..., `quan_ly.cap_nhat_trang_thai`) dùng `csdl.giao_dich(con)` (chỉ tầng ngoài cùng commit /
    rollback); vòng lặp nhiều hộ bọc `csdl.giao_dich` (`quan_ly.ap_quyet_dinh`, `HopTrangThai.luu`, `theo_doi.them_ho_theo_pa`,
    `bo_cac_ho_khoi_qd`, `nhap_tu_ket_qua` đọc phương án một lượt). Nhập QĐ 3.000 hộ 5,8 s -> 0,5 s (HDD / ổ mạng: phút -> giây).
  - ĐÚNG SAI: `nhap_excel` đọc hết sheet THEO_DOI (trước: 400 dòng đầu -> dự án > ~395 hộ không được đối chiếu); `nhap_chi_tiet.doc_hang`
    đọc hết sheet hộ (trước: 600 dòng), dừng sau `TRONG_LIEN_TIEP` (200) dòng trống liền nhau.
  - Chỉ mục `ix_ctdat_thua` (khóa ngoại ct_dat.ma_thua): tạo trong `csdl.mo` khi chưa có và file có ct_dat (KHÔNG đổi PHIEN_BAN_CSDL;
    KHÔNG ghi vào bộ đơn giá / file chỉ danh mục - csdl.mo cũng mở các file đó; test so băm bộ đơn giá).
  - `tra_gia_dat`: bảng gia_dat theo loại đất nhớ trên bối cảnh (`bc.__dict__['_gia_dat_theo_loai']`), giá đã dùng gộp GROUP BY.
    `tien.D(chuỗi)` nhớ `_d_chuoi` (lru 65.536). `nhap_don_gia.so_khop`: khớp gần đúng
    nhớ `_NHO_GAN` theo (file bộ đơn giá + mtime + size, nhóm, ĐVT, tên gốc - vì `_giong_tung_phan` so tên gốc) - đổi nhóm / sửa ô so lại 4 s -> 0,06 s, kết quả như cũ.
  - Giao diện: `giao_dien.vua_dong(bang)` thay resizeRowsToContents (chỉ đo dòng có chữ dài / nhiều dòng); `_o` (theo dõi) chỉ gắn
    tooltip khi chữ > 25 ký tự; `_loc_nho` so `self.ds is` (không so id); Kiểm tra lỗi: tìm chờ ngừng gõ 300 ms, chuỗi không dấu
    tính một lần; `HopNhapChiTiet.chon_tat_ca` chặn itemChanged.
  - Luồng nền / tiến trình: báo cáo tổng hợp (`quan_ly.du_lieu_bao_cao` ở luồng giao diện + `ghi_bao_cao_tong_hop` chạy nền), báo
    cáo đối chiếu, cài gói cập nhật, ghi chi tiết vào file dự án khác (`ghi_file`). `lap_bang_tong_hop(..., bao_tien_do)` (mỗi 100
    hộ; `van_ban_trinh.xuat_bo_ho_so` / `xuat_hang_loat` truyền tiếp); `HopIn.thuc_hien` lỗi lạ: đóng hộp tiến trình rồi ném
    lên `cai_bat_loi`; Dự án mới xuất bản in có hộp tiến trình + Dừng.
    Máy chủ: `ghi_mo_du_an` chạy luồng riêng, `dang_xuat` lúc đóng chờ tối đa 3 s.
  - Web: `cap_nhat_web._lay(file_ra=)` ghi file từng khối 64 KB (không giữ cả file trong RAM 32-bit), `chi_html=True` khi quét (liên
    kết là file thì không tải phần thân); thư mục tạm tải về được xóa; nút Quét khóa khi đang quét.
  - Dọn: `in_an._don_xem_truoc_cu` (thư mục in thử > 12 giờ), file `.tmp` khi ghi lỗi (`chen_duong_ke`, `khoa._ghi`); `ho_so._danh_lai`
    chỉ ghi hộ đổi số thứ tự; Thêm hộ tải lại một lần.
  - Phần trùng với 0.9.16-0.9.19 KHÔNG ghép (đã có cách làm riêng): biểu thưởng (`BoiCanh.muc_thuong`), lọc Bộ đơn giá
    (`_khoa_the`), nút Sửa / Xóa đợt khi chưa chọn đợt (`HopDotTrinh`), `chep_danh_muc` chỉ đọc file nguồn.
  - CHƯA làm (ghi để làm tiếp): OCR dựng ảnh từng trang trước khi hiện tiến trình (`ocr._anh_trang_pdf`); `.docx` lớn đọc cả XML
    (`ET.fromstring`); danh sách dự án máy chủ mở từng file qua mạng; `HopDuToan` vẽ lại cả bảng mỗi lần sửa ô; PDF quyết định đọc
    2-3 lần; `OTimChon` dựng lại danh sách mỗi phím; `lap_chi_tiet` nạp lại mẫu mỗi hộ khi in hàng loạt; tạo dự án ghi đè xóa file
    cũ trước (nên tạo file tạm rồi os.replace); `nhap_chi_tiet.ghi` vào dự án đang mở vẫn ở luồng giao diện (giữ được hoàn tác).
- 0.9.20 (tiếp, yêu cầu người dùng 10/10/2026):
  - Kinh phí tổ chức thực hiện (QĐ 08/2025/QĐ-UBND ngày 10/02/2025 Đồng Nai: theo tuyến <= 3,5%, cụm / vùng / khác <= 2,5%):
    `lap_pa.LOAI_KINH_PHI`, `loai_kinh_phi_tu_ten` ("Khu / Cụm / Vùng" trong 3 từ đầu -> khác; đường, tuyến, kênh, đường dây… ->
    tuyến), `kinh_phi_to_chuc(con)` -> (loại, tỷ lệ, tự nhận?) từ `cai_dat` LOAI_KINH_PHI / TL_KINH_PHI, `luu_kinh_phi_to_chuc` (không
    vượt mức tối đa). `in_an.lap_bang_tong_hop` thay % trong chữ dòng "Kinh phí đảm bảo…" + ghi căn cứ; dòng 85% / 15% giữ theo mẫu.
    `HopDuAn` ô loại / tỷ lệ; `du_toan.them_chi_phi_mac_dinh` theo tên dự toán.
  - Mẫu in: `in_an.tao_mau_tu_excel(file, thu_muc, loai=, ten_mau=)` lấy sheet nào có (không đòi đủ IN_CHITIET + IN_BANGTONGHOP);
    file mẫu đã sửa (có `{…}`) một sheet .xlsx -> chép nguyên zip, đổi tên sheet trong workbook.xml (giữ hình vẽ); không nhận ra loại
    -> `LoiChuaRoMau` (màn hình hỏi). Mẫu riêng `<TEN>__<tên>.xlsx` (`TACH_MAU`), `ds_mau`, `file_mau(mau, ten)` (mau = thư mục hoặc
    file); `duong_ke_cua_mau` theo stem của mẫu; mẫu cũ chép vào `mau_in\cu\`. `HopIn.cb_mau_ct / cb_mau_bth` ->
    `van_ban_trinh.xuat_bo_ho_so(mau_ct=, mau_bth=)`. Lệnh `app.cap_nhat_mau_in(file, ten_mau=, loai=, cho=)`.
    Mẫu riêng đóng kèm (`mau_in\IN_CHITIET__Du thao.xlsx` - bản có "(DỰ THẢO)"; mẫu chính bỏ chữ này) đặt tên KHÔNG dấu: bộ cài Win7
    giải nén PABT.zip bằng Shell.Application (zip Windows 7 không đọc tên UTF-8; từ 0.9.21 không giải nén zip khi cài nhưng
    tên file trong bản dựng vẫn phải ASCII - IExpress / cmd).
  - Menu: `app.NHAN_MENU` chữ ngắn (khóa `self.lenh` giữ tên đầy đủ = gợi ý), tên nhóm mới, `giao_dien.TEN_NHOM_CU` đổi tên nhóm đã
    nhớ trong QSettings; nút xổ "Dự án" kiểu `QToolButton[xo="1"]` nền xanh đậm + vạch vàng, chữ "DỰ ÁN ▾". "Đối chiếu với file
    Excel…" ở nút Dự án.
  - Đợt trình: `quan_ly.NHOM_HO_DOT` / `ho_theo_nhom(con, loai, dot_id)` (da_lap / gan_nhat / chua_xep / chua_duyet; 'chon' do màn
    hình), `HopDotTrinh.cb_nhom_ho` + `b_dua` (`dua_nhom`). Nút "Mã điền tự động {…}…" (trước: "Chỗ trống dùng trong mẫu…").
  - Biểu tượng: `logo_PABT_nen_trang.png` (chữ PABT tách khỏi ảnh nền của logo_PABT.png, nền trắng sữa #FBF7EE) ưu tiên trong
    `tao_bieu_tuong.py`; khung logo băng tiêu đề nền #FBF7EE, viền vàng giữ.
  - Bộ cài (`cai_dat.ps1`): lối tắt qua `IShellLinkW` (C# Add-Type, chạy .NET 2.0) - WScript.Shell đổi tên sang ANSI: Windows tiếng
    Anh / tên người dùng có dấu -> "Unable to save shortcut …L?p…" làm hỏng cả lần cài; dự phòng WScript tên "PABT.lnk"; lối tắt lỗi
    chỉ cảnh báo. Tự kiểm tra sau cài `WaitForExit(180000)`. Máy phát triển bật UTF-8 toàn hệ thống nên không tái hiện được lỗi ANSI.
  - `in_an.ten_file_ho` cắt họ tên ở " là chủ / người / đại diện / đồng…".
- 0.9.21 (yêu cầu người dùng 10/10/2026):
  - VẬT NUÔI MỤC RIÊNG: mã bên trong `nghiep_vu.MUC_VN = 7` (6 là "Chi phí khác" của dự toán); thứ tự `THU_TU_MUC` (1, 2, 3, 7, 4, 5),
    số in `SO_MUC` / `so_muc(muc)`: 4 vật nuôi, 5 hỗ trợ, 6 thưởng; `MUC_KHOAN` = (2, 3, 7, 4) - ĐỪNG viết `(2, 3, 4)` cho vòng lặp
    khoản. Bảng / cột cố định 5 mục (tong_excel, quyết định tien_*, báo cáo, bảng tổng hợp cột 18, mẫu văn bản trình {tien_cay}) gộp
    vật nuôi vào cây trồng qua `muc_5_cot` (nhãn "Cây trồng, vật nuôi"). Danh mục: dm_taisan nhóm 3 có phan_loai "vật nuôi"
    (`la_vat_nuoi`) -> `DanhMuc.muc[MUC_VN]`. CSDL v12 (`_NANG_CAP[11]` = "@ct_khoan_vat_nuoi" -> `csdl._dung_lai_ct_khoan`: dựng lại
    ct_khoan theo schema.sql (CHECK muc IN (2, 3, 4, 7); đoạn CREATE hết ở "\n);" - chú thích có dấu ";") + `chuyen_vat_nuoi`
    (lọc phan_loai bằng Python: lower() SQLite chỉ ASCII); `nhap_excel` gọi `chuyen_vat_nuoi` sau khi ghi. `pabt/bo_don_gia.sqlite`
    đã nâng lên v12 (mở bằng csdl.mo không được ghi bộ đơn giá đóng gói - test so băm). Dự toán: vật nuôi gộp mục 3
    (`du_toan.muc_du_toan`). `nhap_chi_tiet.muc_theo_ten`: chỉ vật nuôi -> MUC_VN, "cây trồng, vật nuôi" -> 3; kiểu số: mục theo tên,
    tên lạ theo số (bản in mới `_MUC_THEO_SO`). `phan_loai_tai_san.LOAI[VAT_NUOI]` = MUC_VN.
  - LƯU KHI BẰNG 0: `BoSoan.loi_chan_luu` chỉ chặn diện tích ÂM (0 = tài sản trên đất người khác); người dùng Lưu -> luôn
    `nghiep_vu.DA_LAP_LUU` "(lưu …)" kể cả không dòng nào (`KetQuaHo.da_luu` -> `co_phuong_an`); tự lập (Dự án mới) không dòng
    vẫn "Chưa lập". `kiem_tra_pa` bỏ "chưa có giá bảng giá" / "chưa có số lượng, đơn giá" và lệch DT khi DT mục 1 = 0 - các dòng 0
    đồng ở `dong_bang_0` (chỉ Kiểm tra lỗi, chỉ hộ chưa lưu). Nút Lưu bật khi hộ chưa lưu lần nào (xác nhận phương án 0 đồng).
  - Vị trí NQ 28 ở mục 1: `gia_dat_nq28.theo_dia_ban` - ĐỦ các địa bàn (dự án qua nhiều xã), địa bàn dự án đứng đầu, nhãn có tên xã
    (`ten_ngan_xa`); `XoXuongDong.setEditorData` chữ không thuộc danh sách -> mở từ dòng đầu (trước: chỉ số -1 mở ở CUỐI danh sách,
    người dùng tưởng thiếu tuyến). Bảng NQ 28 hiện có 4 địa bàn, đối chiếu bản PDF quét `FILE NQ28 BẢN FULL.pdf` (3.206 trang, không
    có lớp chữ; dựng ảnh trang bằng QtPdf): Trị An đủ TT 1-427 (trang 2700-2742). Địa bàn khác phải chép thêm từ PDF.
  - `nhap_chi_tiet` đọc kiểu La Mã (I. II. … / A. B.) theo tên mục; `phan_loai_tai_san.py` + `man_hinh_phan_loai.HopDanTaiSan`
    ("Dán danh sách tài sản…" trong CuaSoLapPA): khớp danh mục -> từ đầu -> luật từ khóa + ĐVT.
  - Test GUI: đóng CuaSoLapPA còn sửa đổi thì hỏi lưu (hộp thoại treo test) - `bo_thay_doi()` trước `close()`.
  - TIÊU CHUẨN CÀI ĐẶT (người dùng: "bộ cài Win 7/8 và Win 10/11 phải cài được trên tất cả các máy khác, quy về 1 tiêu chuẩn"):
    (1) cài cho người dùng hiện tại (từ 0.9.22 mặc định Program Files (x86): chỉ bước chép file hỏi quyền quản trị; từ chối -> thư
    mục không cần quyền), KHÔNG cài gì vào Windows - Visual C++ và UCRT nằm trong bản dựng
    (Win7: `ucrt_win7.chep_ucrt` gọi trong `dung_exe38.py`; UCRT 10.0.10240 bản Windows 7 trong KB2999226 của vc_redist, giải
    nén bằng expand.exe), `rut_gon.kiem_dll` chặn dựng nếu thiếu DLL (`HE_THONG_WIN7` / `HE_THONG_WIN10`; Win7 cho phép các
    nhóm `rut_gon.API_WIN7` - không phải mọi l1-1-0: core-path chỉ từ Win 8); (2) khởi chạy `bo_cai_win\CAI_DAT.cmd` (CHỈ ASCII) -> `powershell -Command "& ([scriptblock]::Create(
    ReadAllText($env:PABT_GOC + 'cai_dat.ps1')))"` - KHÔNG `-File` (ExecutionPolicy / Group Policy Restricted chặn -File: đã
    thử); gỡ cài (UninstallString) cũng `-Command` + `go_cai_dat.ps1 -Dich`; (3) không giải nén zip khi cài: file phẳng
    `f001_<tên>` trong IExpress + `danh_sach.txt` (nguồn, đích, cỡ, SHA-256) -> `cai_dat.ChepFile` chép rồi kiểm từng file (báo
    rõ file bị diệt virus chặn); tên file trong bản dựng phải ASCII; (4) `PABT_ChayNgay_*.zip` = cây chương trình + CAI_DAT.cmd
    (cài dự phòng khi .exe không chạy: tên người dùng có dấu làm IExpress (ANSI) lỗi, diệt virus chặn exe); (5) điều kiện máy: bộ
    cài Win10-11 cần Windows 10 1809 (build 17763)+ 64-bit (Qt 6); bộ cài Win7-8 chạy MỌI Windows từ 7 SP1 (cả 10/11 64-bit: chỉ
    nhắc). Python 3.8 trên Windows 7 cần bản cập nhật KB2533623 (gộp trong KB3063858): `ThieuKbWin7` (kernel32.dll <
    6.1.7601.17651). Bộ cài Win7-8 KÈM `Windows6.1-KB3063858-x86.msu` / `-x64.msu` (người dùng đồng ý tải 10/10/2026; Update Catalog
    chỉ còn bản Vista -> tải từ download.microsoft.com, chữ ký số Microsoft, SHA-256 trong `dung_bo_cai_win.KB_WIN7` - đóng gói
    kiểm băm; file ở `bo_cai_win\*.msu`, KHÔNG đưa vào git). `cai_dat.CaiKbWin7`: chọn theo kiến trúc WINDOWS, `wusa` qua
    `Sysnative` (PowerShell 32-bit trên Windows 64-bit), `-Verb RunAs` (chỉ máy Win 7 còn thiếu mới hỏi quyền quản trị); mã 0 /
    3010 / 2359302 (đã có, chờ khởi động lại) -> `KB_CHO_KHOI_DONG` (cửa sổ: "KHỞI ĐỘNG LẠI MÁY rồi mở PABT", ẩn nút Mở PABT; -Im
    thoát mã 3010); từ chối / lỗi -> `KB_LOI`. Thử logic bằng giả lập wusa (máy phát triển là Win 11, chưa thử Win 7 thật).
    Kiểm bộ cài: `kiem_tra_toan_bo.py` (zip đủ file cài, danh_sach.txt khớp mã băm), `--cai-thu`; `tests/test_bo_cai.py`.
  - Shell Bash của Claude Code nuốt dấu "\" trong heredoc: script Python sửa file nên ghi bằng công cụ Write rồi chạy.
  - Nguồn gốc - gạch đầu dòng thụt lề treo (người dùng yêu cầu 10/10/2026, màn hình + bản in): `ho_so.dau_dong(doan)` nhận "- ",
    "– ", "+ ", "• ", "* ", "a) ", "1. ", "1) ". Màn hình: `man_hinh_ho_so._bo_tri_chu` đặt x dòng tràn = bề rộng ký hiệu
    (`QTextLine.setPosition`, draw() cộng x); CHÚ Ý chữ ô từ `initStyleOption` đổi '\n' thành U+2028 - phải tách cả hai (trước
    đây cả ô thành một đoạn). Bản in: `in_an._ngat` trả dòng tràn đánh dấu `TREO` (có sẵn khoảng trắng thụt = bề rộng ký hiệu /
    bề rộng dấu cách), `dat_doan_van` xuống dòng cứng trước dòng TREO (Excel không có thụt lề treo trong ô).
  - Đường kẻ dưới tên đơn vị / tiêu ngữ / "Dự án" (người dùng 10/10/2026: "gần sát chữ, nằm giữa từng nội dung, hở chút xíu
    để không che dấu"): `in_an.can_duong_ke(ws, xml)` chạy SAU khi điền mẫu, trước `chen_duong_ke(file, dk, xml)`: mỗi đường
    tìm ô chữ phía trên (dòng trên / cùng dòng / dòng kế, ô gộp phủ tâm đường) có chân dòng chữ cuối gần nhất (`_dong_chu_o`:
    ngắt dòng `ngat_dong`, khoảng dòng 1,107 cỡ chữ, canh top +1 pt / center / bottom sát đáy), đặt y = chân + cỡ chữ x
    `DK_CO_DAU_DUOI` (0,33 - dòng có dấu nặng / chữ có chân `_DAU_DUOI`) hoặc `DK_KHONG_DAU_DUOI` (0,12), căn giữa theo chữ; độ
    dài: tiêu ngữ = cả dòng tiêu ngữ, đường khác giữ độ dài mẫu nhưng không dài hơn dòng chữ. Hằng số đo trên PDF Excel in ra
    (đo ảnh: khe 5-6 px chi tiết, 3 px bảng tổng hợp; lệch tâm <= 3 px). Cột: `_px_cot` / `_bien_cot` / `_rong_vung` tính CỘT ẨN = 0
    và khai báo theo dải cột (<col min max>) - bảng tổng hợp có cột L, M, O ẩn (trước đây đường kẻ lệch ~100 pt, ngắt dòng chữ
    cũng sai); `_neo` không neo vào cột rộng 0. Bảng tổng hợp có `mau_in/IN_BANGTONGHOP.duong_ke.xml` (3 đường) + dòng 6
    "Dự án" 34 pt; không có file đường kẻ (máy cập nhật bằng .pabtcn - gói không mang mau_in) -> `dk_mac_dinh` tự tạo,
    `lap_bang_tong_hop` nới dòng Dự án >= 1,7 cỡ chữ. Test `tests/test_in_vua_chu.TestDuongKe` dùng hàm đo chữ cố định (phông
    offscreen khác Windows).
- 0.9.22 rà soát (người dùng 10-11/10/2026 - "rà soát toàn diện, tối ưu, lược bỏ bất hợp lý"; chỉ sửa điều đã đo / tái hiện):
  - Bảng tổng hợp: thẻ con <-> menu trái đồng bộ - `KhungBangTongHop.the_da_doi(i)` (bấm thẳng thẻ hoặc `mo_the`) ->
    `app._danh_dau_trang` (tiêu đề `lb_trang` + dấu chọn QAction checkable của `TRANG`); tên thẻ một nguồn `thong_bao.THE_TONG_HOP`
    (`app.TRANG = ['Danh sách hộ', *THE_TONG_HOP, 'Theo dõi tiến độ']`).
  - `man_hinh_theo_doi`: cả 4 trang danh sách dùng `BangAo` (thẻ Quyết định 3.000 hộ 1.637 -> 161 ms: trước đây `nap` dựng bảng
    HAI lần - setCurrentRow phát currentRowChanged -> chon + gọi chon thẳng; nay chọn lại khi đang blockSignals). Mã chung ở
    `_Khung`: `mo_ho` Signal (trước khai báo 4 lần), `_mo_ho_dong`, `ma_da_chon` (= `BangAo.ma_da_chon`), `_da_ghi(kq)` (nạp lại +
    `da_doi`), `_xuat(file, tiêu đề hộp, tên file, ghi)` (bắt OSError - trước đây Tổng hợp tiền / Tiến độ chưa bắt), `_ten_du_an`;
    `_bao` / `_hoi` dùng chung `_Hop` + `_Khung`; `_o_tim`, `_nut`, `_chu` (chuỗi hiển thị), `_so_hoac_trong`, `THUA_TRONG`.
    `_bang` / `_o` (QTableWidget) chỉ còn cho hộp thoại một hộ (`HopHoTheoDoi`). Tổng hợp tiền: cột hạng mục KHÔNG đánh số (bản
    in: 4 vật nuôi, 5 hỗ trợ, 6 thưởng - bảng 5 cột gộp cây + vật nuôi), sắp xếp theo GIÁ TRỊ (QTableWidget cũ sắp cột tiền theo chữ).
    Tiến độ: bỏ hàng 6 thẻ số (trùng hàng thẻ số cửa sổ chính) - số hộ từng điều kiện trong ô Lọc (`theo_doi.dem_loc` một lượt,
    `_dieu_kien` dùng chung với `hop_loc`; đếm lại khi nạp / đổi quyết định đánh dấu, không khi đổi Lọc / gõ tìm); `TEN_LOC`.
  - `bang_ao`: `BangAo(sap_xep=True)` sắp theo `khoa` (giá trị từng ô, None cuối, giữ cách sắp khi nạp lại; bảng có gộp ô không sắp),
    `tu_cao=False` (bảng không chữ xuống dòng), `ma_dong(r)`, `ma_da_chon()`, `currentRow()`; chiều cao dòng `_vua_dong` ƯỚC số dòng
    chữ (dòng "\n" + độ dài / ký tự vừa cột x `DU_RONG`, tối đa `SO_DONG_CHU_TOI_DA`) rồi resizeSection - trước đây
    resizeRowsToContents (~105 lần hỏi data mỗi dòng; Tiến độ đổi bộ lọc 514 -> 87 ms) và bảng > 2.000 dòng không chỉnh cao.
  - Bản in: `in_an._o_chu(ws, den_dong)` duyệt `ws._cells` (ô có chữ, thứ tự dòng-cột) thay `ws.iter_rows` (TẠO ô rỗng mọi vị trí
    vùng sheet - file in ra thêm ~700 ô rỗng / hộ, ghi chậm) ở `vi_tri_cho`, `o_tieu_ngu`, `dien_so_ngay`, `_thay_cho_trong`; in 50
    hộ 4,1 -> 3,0 s, file in ra giống hệt (so từng ô, ô gộp, cao dòng, rộng cột, đường kẻ). `_chi_muc_gop(ws)` {dòng: [vùng gộp]} cho
    `can_duong_ke` / `_dong_chu_o` / `_vung_tron(..., chi_muc)` (bảng tổng hợp 26.000 vùng gộp). KHÔNG giữ mẫu bằng pickle
    (openpyxl `row_dimensions` mất hàm tạo mặc định -> KeyError khi chèn dòng; đã thử).
  - Dự án mới 3.000 hộ 8,5 -> 3,4 s: `tao_du_an` đặt `PRAGMA journal_mode = MEMORY` (cùng `synchronous = OFF`; không lưu vào file,
    csdl.mo đặt lại DELETE) - journal DELETE tạo / xóa file "-journal" mỗi hộ tự lập; `BoSoan.mo` giữ `_pa_goc` (bản lúc mở: tổng
    cũ cho nhật ký khi lưu không đọc lại CSDL), `BoSoan.luu(mo_lai=False)` cho `tu_lap_phuong_an` (không đọc lại phương án vừa lưu).
  - Mã chết bỏ: `chinh_sach.la_dao_tao_theo_thua`, `in_an.luu_duong_ke` / `ho_da_lap`, `HopDanTaiSan.dat_loai`, `nghiep_vu.lamtron_du_an`
    + 1 thuộc tính, `BoPhanLoai.phan_loai_ds`, `quan_ly.mo_ta_trang_thai` / `tien_vn`, `theo_doi.lay_qd` / `tien_vn`, import thừa.
  - Bộ cài MẶC ĐỊNH `$MAC_DINH` = `${env:ProgramFiles(x86)}\PABT` (Windows 32-bit: ProgramFiles; người dùng 11/10/2026), thư mục
    không cần quyền `$KHONG_QT` = %LOCALAPPDATA%\Programs\PABT: từ chối UAC (`$script:TU_CHOI`) -> cửa sổ chuyển sẵn sang đó, `-Im`
    không -ThuMuc thì tự cài vào đó; `GoBanCu` gỡ bản cũ ở thư mục khác (InstallLocation HKCU cũ; chỉ khi có PABT.exe, không .pabt).
  - Bộ cài vào Program Files / Program Files (x86) (người dùng 11/10/2026; trước: "Access … denied" và nút Cài đặt khóa luôn):
    `cai_dat.GhiDuoc` (thử ghi file tạm ở thư mục / thư mục cha gần nhất); không ghi được -> hỏi Có (cài đây) / Không (thư mục mặc
    định `$MAC_DINH`) / Hủy -> `ChepQuyenQuanTri`: chạy lại cai_dat.ps1 `-Verb RunAs` với `-ChiChep <file kết quả> -ThuMuc -Goc`
    (biến môi trường không sang tiến trình quản trị), CHỈ `ChepVao` (kiểm thư mục, gỡ bản cũ, chép + kiểm SHA-256); tiến độ qua
    `<kết quả>.tien_do`, nhật ký `<kết quả>.log` ghép vào nhật ký chính; lối tắt / HKCU / mục gỡ cài / tu-kiem vẫn quyền người
    dùng. Lỗi -> mở lại nút Cài đặt / Chọn… / ô thư mục. `go_cai_dat.ps1`: thư mục không ghi được -> lệnh xóa `$XOA_HET` /
    `$XOA_GIU` (một dòng, không ngoặc kép, `$d` = thư mục) chạy `-Verb RunAs -Wait`; từ chối -> báo xóa tay. Phần mềm không ghi vào
    thư mục cài (mẫu in / cập nhật ở %APPDATA%\PABT). Test `test_bo_cai.test_cai_vao_program_files`.
  - `chay.tu_kiem` bước "Lập và in thử (dữ liệu giả lập)": tạo dự án 3 hộ + tự lập, `van_ban_trinh.xuat_bo_ho_so` (chi tiết, bảng
    tổng hợp, tờ trình, phương án tổng - mẫu đóng kèm, không cần Excel / Word), khái toán, nhập Excel thô - chạy lúc dựng và ngay
    sau khi cài trên máy đích. Đã thử giả lập máy trắng (APPDATA / LOCALAPPDATA / TEMP / USERPROFILE trỏ thư mục trống, bản cài
    chép bằng `-ChiChep`): ĐẠT, chỉ tạo %APPDATA%\PABT\mau_in\mac_dinh.
  - Test: `tests/test_ra_soat_0922.py`, `test_giao_dien.test_bam_the_bang_tong_hop_dong_bo_menu`. Bộ đo dùng lại: dự án giả lập
    `tests.test_toc_do._du_an(td, N)` + 3 quyết định (`theo_doi.luu_qd`, `them_ho_theo_pa`, `ghi_chi_tra`).
  - CHƯA làm: lap_bang_tong_hop đọc `doc_tat_ca_phuong_an` 2 lần (một lần trong ket_qua_ho, ~0,08 s / 3.000 hộ); ghi xlsx của
    openpyxl (bảng tổng hợp 3.000 hộ ~4 s, 150.000 ô) - giới hạn thư viện; các mục CHƯA làm của 0.9.20 vẫn còn.
- 0.9.23 theo lộ trình người dùng (`lo_trinh_huong_dan_pabt.txt` trên Desktop, 11/10/2026 - "chuẩn thương mại"):
  - Thanh menu `CuaSoChinh._thanh_menu` (Tệp tin / Dữ liệu / Công cụ / Trợ giúp, dùng chính QAction của `self.lenh`; phím tắt
    Ctrl+N / Ctrl+O / Ctrl+Shift+O / Ctrl+Shift+S / F1); lệnh mới 'Đóng dự án' (`dong_du_an_lenh`), 'Thoát', 'Bảng giá đất NQ 28…'
    (`bang_gia_dat` = HopTraNQ28), 'Hướng dẫn sử dụng' (`huong_dan`: QTextBrowser.setMarkdown của `file_huong_dan()` - HUONG_DAN.md
    đóng gói: `PABT.spec` datas + `dung_exe38` CHEP / --add-data; tu-kiem bước "Hướng dẫn sử dụng"). Bỏ nút xổ "DỰ ÁN ▾" của menu
    trái (QMenu đè các nút dưới) và hai nút góc dưới Cập nhật / Giới thiệu (nay ở Trợ giúp). `kiem_tra_giao_dien` bỏ qua 'Thoát'.
  - Menu trái 5 nhóm (`nhom` trong `__init__`): Dự án & dự toán / Bảng giá & chính sách / Lập phương án / Tổng hợp & trình duyệt /
    Tiến độ & bàn giao; `NHOM_DONG_MAC_DINH`; khóa QSettings mới `giao_dien.KHOA_NHOM_DONG = 'giao_dien/menu_trai_dong_2'`. Thêm hộ
    / Xóa hộ không còn ở menu trái: `_thanh_cong_cu_ds` (nut_lenh của QAction Thêm hộ, Lập phương án, Xóa hộ + bộ lọc một hàng;
    `hang_chon` "Đã chọn N hộ" khi chọn >= 2), `_cap_nhat_chon` (selectionChanged; Xóa hộ chỉ bật khi chọn hộ và không chỉ xem).
    Bộ đếm lọc `lb_loc` sang hàng kết quả đối chiếu (1366 px: hàng công cụ + lọc quá chật). `&` trong chữ QAction là phím tắt gạch
    dưới: TRANG có "&" -> setText với "&&".
  - TRANG thêm 'Dự toán & khái toán' (`TRANG_DU_TOAN` = 5, ô 3 của QStackedWidget `self.trang_dt`; `KhungDuToan` tạo khi mở lần
    đầu `_dam_bao_du_toan`; `dat_du_an(con, file)` khi mở / đóng dự án; `du_toan(cho)` trả khung). `man_hinh_du_toan.KhungDuToan`
    (QWidget, thẻ Khái toán / So sánh với thực tế áp giá); `HopDuToan` = vỏ QDialog (`__getattr__` chuyển sang khung, `im_lang`
    property). Sửa ô: `_ve_lai_dong` (dòng đó + dòng % mục 6 + tổng; đổi mục thì `ve()` vì sắp theo mục). `du_toan.so_sanh(goc,
    thuc_te)` (mục 6 của thực tế theo tỷ lệ khái toán; `vuot`). Trang Dự toán ẩn hàng thẻ số liệu (chỗ cho bảng).
  - Màn hình chào (`TRANG_CHAO` = ô 4; `_trang_chao`, `_hien_trang_chao`, `nut_chao`): chưa mở dự án thì trang 0-4 hiện màn hình
    chào, ẩn `lb_du_an` / `hang_the`; dự án gần đây `doc_gan_day` / `ghi_gan_day` = `<thư mục máy>\du_an_gan_day.json` (tối đa
    `GAN_DAY_TOI_DA`, hiện 5 file còn tồn tại). `mo()` về trang đang chọn `self._i_trang` (đặt trong `_danh_dau_trang`).
  - Thẻ số liệu `TheSo` (QWidget có tín hiệu bam) -> `bam_the_so(k)` lọc `cb_tt` theo `LOC_THE` (Số hộ / Tổng = bỏ lọc); tổng
    tiền `tien.vn_gon` ("185,4 tỷ", tooltip đủ số). Băng tiêu đề theo dự án: `giao_dien.dat_to_chuc(khung, ten, phu)` (khung
    `nhan_to_chuc` / `nhan_phu`) từ `du_an.don_vi_lap` / `don_vi_cap_tren` trong `_sau_tai_lai`; trống / đóng dự án = to_chuc.
  - KHÔNG làm (ghi rõ với người dùng): bỏ Excel / Word (VBS) cho PDF / in - chưa có cách dựng PDF đúng mẫu Excel bằng Python
    (tạo xlsx / docx vốn thuần Python); thay "BẢN THỬ NGHIỆM" bằng bản quyền - chưa có hệ thống bản quyền; bỏ Win7/8 + gộp một
    bộ cài + Inno Setup - trái yêu cầu giữ 2 bộ cài, Inno >= 6.5 lỗi Windows 11; nạp sẵn các trang lúc rảnh (bảng Qt dựng ở luồng
    giao diện: cửa sổ khựng sau khi mở dự án). Chuyển trang đã nạp 13-19 ms (3.000 / 10.000 hộ); lần đầu mở trang 0,17-0,33 s
    (3.000 hộ), 0,6-1 s (10.000 hộ).
  - Test: `tests/test_yeu_cau_0923.py`; `test_giao_dien.test_menu_trai_gon_va_bang_tieu_de` viết lại theo menu mới.
- 0.9.24 theo đặc tả ARCH-PABT-2026-V4 (`lo_trinh_huong_dan_pabt3.txt` trên Desktop, 11/10/2026; mã mục = mục đặc tả):
  - 3 token: `giao_dien.TOKEN` (chinh #0F3866, chinh_nhat, nhan #F59E0B, phu #107C41, nguy_hiem #D83B01, chu #202124, chu_phu,
    vach, nen #F8F9FA, khung) - CHINH, MAU['luu' / 'xoa'], MAU_BANG, vạch vàng, bảng màu `ap_dung`; `CAO_NUT_MENU` 36,
    `CAO_DONG_BANG` 32 (`_BoToMau` nâng defaultSectionSize khi cửa sổ hiện). Phông giữ Segoe UI 9,5 pt x phóng to (110% ~10,5 pt).
  - 6.1 `KieuNut` (CHINH / PHU / LUU / NGUY_HIEM) + `ap_kieu_nut` (setProperty bien_the + unpolish / polish; nền đặc -> biểu tượng
    trắng, gắn lại sau action.changed); QSS `_qss_kieu_nut` đặt CUỐI; MỌI chỗ đặt bảng kiểu dùng `_qss_day_du()` (phong_to từng dựng
    lại thiếu phần biến thể). Màu đoán theo chữ (LUAT) giữ cho nút chưa khai báo - KieuNut thắng. 6.2 `OTimKiemThongMinh`
    (chuoi_da_doi sau CHO_MS 200; `phat_ngay()`) cho ô tìm danh sách hộ - thay quyết định 0.9.18 (người dùng yêu cầu: bộ gõ tiếng
    Việt); trang theo dõi / kiểm tra lỗi chờ 200 ms. 6.3 `chan_tin_hieu(w)`. 6.4 WA_DeleteOnClose: KHÔNG áp hàng loạt (mã đọc
    thuộc tính hộp sau exec) - đã có `don_hop_da_dong`, quét giao diện 0 hộp rò rỉ.
  - 4.2 / 12.2: `pabt/ban_quyen.py` (`kiem_tra_ban_quyen()` luôn True, `mo_ta()` 'Bản Tiêu chuẩn · Sử dụng nội bộ'; `app.main`
    gọi lúc khởi động; gói .pabtcn sau này thay module) - `BAN_THU_NGHIEM = False`, băng tiêu đề nhãn `vai="ban_quyen"`.
    Thanh menu thêm Cài đặt (Thông tin dự án, Kết nối máy chủ LAN, Phóng to / Thu nhỏ / 100%), Tệp tin → Lưu dự án Ctrl+S
    (`luu_du_an_lenh`: commit + fsync, báo giờ - dữ liệu vốn ghi ngay mỗi thao tác); góc phải `lb_co_quan` "Cơ quan: …"
    (`_dat_co_quan`); thanh trạng thái `lb_tom_tat` "Sẵn sàng · Tổng cộng: N hộ | Đã chọn: k hộ" (KHÔNG showMessage cố định - che
    widget trái), đèn LAN gộp vào `nut_tk` ("● LAN: Trực tuyến · Tài khoản…" / "Ngoại tuyến (Offline)" / "Máy đơn"), phiên bản chỉ
    ở băng tiêu đề. Màn hình chào thêm nút Hướng dẫn sử dụng.
  - 7.1 ghi nguyên tử: `csdl.tao_moi_tam(p)` -> (con, '<tên>.dang_tao'), `hoan_tat_tao_moi(tam, p)` (fsync + os.replace),
    `huy_tao_moi(tam)` - dùng ở `du_an_moi.tao_du_an`, `nhap_excel.nhap`, `nhap_chi_tiet.ghi_file` (file mới); lỗi giữa chừng file
    cũ còn nguyên. `quan_ly.luu_thanh` fsync + os.replace. `csdl.tao_moi` (xóa trước) còn cho chỗ khác.
  - 7.2 giữ mẫu Excel trong RAM: KHÔNG làm được an toàn - pickle (0.9.22) và deepcopy (0.9.24) đều làm hỏng openpyxl
    (row_dimensions mất hàm tạo; deepcopy còn lệch chỉ mục bảng kiểu IndexedList -> IndexError khi ghi). In 50 hộ ~3 s (0.9.22).
  - 7.4 `may_chu.ds_du_an`: chỉ mục `DuAn\danh_muc_du_an.json` ({đường dẫn tương đối: ten, mtime ns, size}, ghi tmp + os.replace;
    `_doc_chi_muc` / `_ghi_chi_muc`) - file không đổi không mở qua mạng.
  - 8.1 `an_toan.che_cccd` (12 số giữ 6 đầu "075092******", từ 9 số giữ nửa đầu), `can_che_cccd(con)` = cai_dat `CHE_CCCD`
    ('1'); HopIn ô `o_che_cccd` (`_luu_che_cccd`: ghi cai_dat + ghi_nhat_ky; chỉ xem -> báo, không in); `in_an._thong_tin_ho` (che
    số, bỏ ngày / nơi cấp), `van_ban_trinh.du_lieu` {ho.cccd}. KHÔNG mã hóa trường cccd trong CSDL (phá khớp quyết định theo CCCD,
    tìm kiếm; không có quản lý khóa), KHÔNG RBAC 4 vai trò / nhật ký giá trị cũ-mới (cần quyết định nghiệp vụ) - ghi rõ với người dùng.
  - 9 bộ cài: tên `PABT_CaiDat_<ver>_Win10-11_x64.exe`, `PABT_CaiDat_<ver>_Win7-8-10_x86.exe`, `PABT_ChayNgay_<ver>_x64.zip` /
    `_x86.zip` (`BAN[...]['ten' / 'zip']`), thêm `PABT_Setup_Universal_<ver>.exe` (`dong_goi_pho_quat`: cả hai bản, file phẳng
    a###_ / b###_, `danh_sach_x64.txt` / `danh_sach_x86.txt`, ban.txt 'universal', KB3063858, vỏ IExpress 32-bit) - `cai_dat.ps1`
    ban 'universal' chọn: Win10 build >= 17763 VÀ 64-bit -> win10 / x64, còn lại win7 / x86 (`$DANH_SACH`, `$PHO_QUAT`). Hàm chung
    `_ds_chuong_trinh` (không thêm HUONG_DAN.md khi bản dựng đã có - zip x86 0.9.23 trùng tên), `_chep_phang`, `_chep_cai_dat`,
    `_chep_kb`, `_iexpress`. `kiem_tra_toan_bo` theo tên mới.
  - 13 bỏ Office (VBS) / 5 tái cấu trúc 4 tầng: KHÔNG làm (xem 0.9.23; logic đã tách khỏi Qt ở nghiep_vu / lap_pa / csdl /
    theo_doi... - dùng chung Qt5 / Qt6, kiểm thử độc lập; viết lại 26.000 dòng thành 4 tầng: rủi ro hồi quy lớn, không lợi ích
    người dùng thấy). Test: `tests/test_dac_ta_v4.py`.
- `khoa.py`: khóa nhiều máy bằng file `<x>.pabt.khoa` (làm mới 60 s, hết hạn 180 s); `app.mo()` hỏi mở chỉ xem / vẫn sửa.
- `giao_dien.py`: QSS + tô màu nút tự động theo chữ trên nút (`LUAT` → `MAU`, property `nhom`), nhãn dùng property `vai`
  (`nhan`, `tieu_de`, `bang_ten`). Nút mới tự có màu nếu chữ khớp luật; thêm nhóm thì sửa `LUAT`/`MAU`.

## Môi trường làm việc
- Dự án ở `D:\APP AI PABT\PABT_PhanMem` (đường dẫn không dấu; trước 07/10/2026 là `D:\Thư mục mới\…` dạng NFD). File thật của người
  dùng (`DT762.pabt`, `PABT_CHUAN_06-10-2026_QD42.xlsm` – dùng cho `PABT_EXCEL`) ở thư mục cha: chỉ đọc / thử trên bản sao.
- Windows PowerShell 5.1; `.venv` dùng Python 3.14. `build/`, `dist/`, `bo_cai/` là sản phẩm dựng.

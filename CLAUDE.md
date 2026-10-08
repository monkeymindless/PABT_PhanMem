# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Tổng quan
PABT: phần mềm lập phương án bồi thường, hỗ trợ khi thu hồi đất (Python + PySide6, Windows). Mỗi dự án là một file `.pabt` (SQLite).
Mã nguồn, hàm, biến, bảng CSDL viết bằng tiếng Việt không dấu (`ma_ho`, `tinh_pa`, `doi_chieu`) — giữ quy ước này.
Hướng dẫn người dùng: `HUONG_DAN.md`. Phần mềm phát hành **không kèm dữ liệu** (không có `.pabt`, danh sách hộ, danh mục đơn giá; mẫu in
không ghi cố định tên đơn vị / người ký) — đừng đưa dữ liệu thật vào repo, `mau_in/` hay bộ cài.

## Quy trình MỖI LẦN sửa phiên bản (người dùng yêu cầu - bắt buộc)
- Tăng `__version__`; đối chiếu với gói cập nhật đã phát hành gần nhất trong `bo_cai\` (`cap_nhat.doc_goi`: chữ ký + SHA-256;
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
  `vc_redist_win7.x86.exe` 14.29, vỏ IExpress 32-bit từ `SysWOW64` — `dung_bo_cai_win.IEXPRESS`, `kien_truc()` in x86/x64,
  dựng bằng `bo_cai_win\dung_exe38.py` từ bản chép ở thư mục tạm không dấu → `dist\PABT_Win7`). Mã dùng chung phải chạy Python 3.8 +
  Qt5: mỗi file có `from __future__ import annotations`, không dùng API Python 3.9+; `pabt/__init__._qt5_lam_qt6` đặt bí danh
  PySide6 → PySide2 (+ QAction/exec/QLibraryInfo.path, đường dẫn plugin Unicode); đọc PDF: QtPdf hoặc pypdf. Chạy test cả hai venv.
  `cai_dat.ps1` dùng chung (đọc `ban.txt` win10/win7 → `$KIEN` x64/x86, bộ VC++ đóng gói tên `vc_redist.exe` - vắng mặt thì `$CO_VC` = false, bỏ bước cài VC++, chặn cài nhầm), viết theo PowerShell 2.0 (không `$PSScriptRoot`, `-Raw`, `-in`,
  `-File`; giải nén bằng Shell.Application khi không có .NET 4.5; gọi `powershell -STA`).
- Dựng bộ cài: `DUNG_BO_CAI.bat` (PyInstaller rồi `bo_cai_win\dung_bo_cai_win.py`: IExpress + `cai_dat.ps1`/`go_cai_dat.ps1`, cài
  per-user vào `%LOCALAPPDATA%\Programs\PABT`) → `bo_cai\PABT_CaiDat_<ver>.exe` + `bo_cai\PABT_ChayNgay_<ver>.zip`. KHÔNG dùng
  Inno Setup ≥ 6.5 (lỗi tạo thư mục tạm is-*.tmp trên Windows 11 build mới); phiên bản lấy từ `pabt/__init__.py` `__version__`. Lệnh PyInstaller phải kèm
  `--add-data "pabt\bo_don_gia.sqlite;pabt"`. Sau PyInstaller chạy `bo_cai_win\rut_gon.py` (giữ theo danh sách `GIU_MODULE`;
  bản Qt5 phải giữ `Qt5Qml.dll` vì `pyside2.abi3.dll` liên kết cứng - thiếu thì exe treo im lặng, không báo lỗi; rồi
  `PABT.exe tu-kiem <file>` = `chay.tu_kiem`, phải ra `KET QUA: DAT`). Bộ cài Win7-8 kèm `vc_redist_win7.x86.exe` (cài nếu thiếu);
  `cai_dat.ps1` là cửa sổ WinForms (kiểm tra Win10/11 x64, tiến trình, tự kiểm tra), `-Im` cài im lặng. `KiemTraThuMuc`: chỉ xóa
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
  `mau_in/<mẫu>.duong_ke.xml` (`in_an.luu_duong_ke`, gọi trong `tao_mau_tu_excel`) và chèn sau `wb.save` bằng `in_an.chen_duong_ke`.
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
  'tai_dinh_cu')`, thẻ 1-4 `BangMuc`; chỉ số thẻ = số mục; `hang_dieu_huong`/`sang_the` lưu hồ sơ khi rời thẻ 0; `HopHoSo` chỉ bọc
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
- An toàn (`an_toan.py`, 0.9.13): `quet_file`/`chan_ma_doc` (MpCmdRun đường dẫn tuyệt đối, đọc báo cáo "found N threats" - mã 2
  dùng chung cho lỗi; rồi AMSI ctypes) ở `cap_nhat_web.tai_ve`, `nhap_don_gia.chuyen_office`, `cap_nhat.cai`; `ngu_canh_tls`
  (mọi urlopen); `kiem_tra_zip`/`kiem_tra_xml`; `toan_ven.json` (rut_gon.py ghi sau tu-kiem) -> `kiem_tra_toan_ven` (app nền +
  tu-kiem "An toàn"); chữ ký RSA-3072 PKCS#1 v1.5 tự viết (`ky`/`xac_minh` so cả khối): khóa bí mật
  `%LOCALAPPDATA%\PABT_dev\khoa_ky_cap_nhat.json` (`tao_khoa_ky.py`, KHÔNG đưa vào repo / bộ cài), khóa công khai
  `an_toan.KHOA_CONG_KHAI`; `cap_nhat.tao_goi(khoa=None -> khóa máy, False -> không ký)` ghi `cap_nhat.sig`; `doc_goi`/`cai` bắt
  buộc chữ ký; `nap_cap_nhat._kiem_chu_ky` kiểm lại chữ ký + SHA-256 + file lạ, xóa `__pycache__`, `dont_write_bytecode`.
  Test dùng khóa thử (`test_cap_nhat.KHOA_THU`, tiến trình con `TIN_KHOA_THU`). Màn hình `man_hinh_an_toan.HopAnToan`.
  VBS Word/Excel: `AutomationSecurity = 3` (tắt macro).
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
- Git (từ 09/10/2026): repo cục bộ ở thư mục dự án, `.gitignore` loại `.venv`, sản phẩm dựng, `*.pabt*`, `*.xlsm`, `du_lieu/`,
  khóa ký, `bo_cai_win/*.exe`. Git for Windows ở `C:\Program Files\Git\cmd\git.exe` (PowerShell mở trước khi cài chưa có trong PATH).
- Thông báo có danh sách dài (kết quả nhập Excel / nhập chi tiết / Dự án mới, lỗi nhập): `giao_dien.hop_ket_qua(cha, tóm tắt,
  [dòng], tiêu đề danh sách, canh_bao=, hien=False khi test)` - ô cuộn, đủ mọi dòng, nút Chép / Đóng, `vua_man_hinh`; KHÔNG ghép
  danh sách vào QMessageBox (giãn theo chữ, đẩy nút OK ra ngoài màn hình). `nhap_chi_tiet.ket_qua(bc)` -> (tóm tắt, cảnh báo).
- Số lượng mục 2-4 trên bảng nhập: `tien.so_luong_vn` (luôn >= 1 chữ số thập phân "20,0"; số nhiều chữ số lẻ hơn hiện đủ, tối đa 4) ở
  `BoSoan.o_khoan` - người dùng yêu cầu "dạng kế toán". QĐ 31/2025/QĐ-UBND (đơn giá vật nuôi): bộ đơn giá tích hợp CHƯA có mục vật
  nuôi (chỉ ghi văn bản ở `van_ban`); nhập bằng "Cập nhật từ trang web / từ file" (nhóm 3) - kết quả nằm ở `%APPDATA%\PABT` của máy.
- Văn bản không có bảng giá (đơn giá viết trong điều khoản - QĐ 31/2025 vật nuôi): `HopNhapDonGia` không ra dòng từ `nhan_muc` thì
  `nhap_don_gia.muc_tu_loi_van(dong, nhom)` -> ([Muc], [câu cần xem]): `_khoan_van` ghép dòng PDF / đoạn Word thành khoản (tách ở
  Điều / 1. / a) / - và sau ; : .), `_RE_GIA_VAN` "<số> [triệu|nghìn] đồng/<ĐVT>[ mặt nước…]", tên = chữ trước số tiền (`_ten_gon` bỏ
  "Đơn giá bồi thường đối với…", "… là"), tiêu đề khoản không giá kết thúc ":" (hoặc phần trước ":" trong cùng khoản) -> "Tiêu đề -
  Mục"; khoảng giá "từ… đến…", tỷ lệ % -> danh sách xem (không tự lấy). `tu_loi_van`: sửa được Tên / ĐVT trên bảng (`_sua_o` -> so
  khớp lại). Văn bản `da_co`: chỉ bỏ chọn sẵn dòng ĐỔI GIÁ, mục mới vẫn chọn. `ap_dung` văn bản đã có -> UPDATE dòng `van_ban` cũ
  (không thêm dòng trùng). Test: `tests/test_nhap_don_gia.TestLoiVan` (văn bản GIẢ LẬP, không phải giá thật).
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
- `khoa.py`: khóa nhiều máy bằng file `<x>.pabt.khoa` (làm mới 60 s, hết hạn 180 s); `app.mo()` hỏi mở chỉ xem / vẫn sửa.
- `giao_dien.py`: QSS + tô màu nút tự động theo chữ trên nút (`LUAT` → `MAU`, property `nhom`), nhãn dùng property `vai`
  (`nhan`, `tieu_de`, `bang_ten`). Nút mới tự có màu nếu chữ khớp luật; thêm nhóm thì sửa `LUAT`/`MAU`.

## Môi trường làm việc
- Dự án ở `D:\APP AI PABT\PABT_PhanMem` (đường dẫn không dấu; trước 07/10/2026 là `D:\Thư mục mới\…` dạng NFD). File thật của người
  dùng (`DT762.pabt`, `PABT_CHUAN_06-10-2026_QD42.xlsm` – dùng cho `PABT_EXCEL`) ở thư mục cha: chỉ đọc / thử trên bản sao.
- Windows PowerShell 5.1; `.venv` dùng Python 3.14. `build/`, `dist/`, `bo_cai/` là sản phẩm dựng.

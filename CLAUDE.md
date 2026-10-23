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
- **MỘT bộ cài phát hành** (người dùng 11/10/2026 đổi ý: "tối giản chỉ 1 bộ cài cho mọi Windows" - thay yêu cầu tách cũ):
 `PABT_Setup_Universal_<ver>.exe` + `PABT_ChayNgay_<ver>_Universal.zip` (`dung_bo_cai_win.MAC_DINH`; zip: `x64\` + `x86\`,
 danh_sach_x64/x86.txt nguồn `x64\…`, ban.txt universal, DOC_TRUOC.txt). Vẫn dựng HAI bản chương trình (dưới đây) - Universal
 chứa cả hai, cai_dat.ps1 tự chọn. Bộ riêng chỉ khi cần: `dung_bo_cai_win.py win10 win7`. Hai bản chương trình:
 `PABT_CaiDat_<ver>_Win10-11.exe` (Python 3.14 + PySide6, PyInstaller 6, `.venv`,
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
  từ 0.9.96 LUÔN lập ct_dat (kể cả đơn giá 0); ghi chú đất vẫn -> `ho.phap_ly` khi không có tiền đất. Sheet nhiều phương án: tach_phuong_an.
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
  `logo_PABT_nen_trang.png` → `tao_bieu_tuong.py` → `pabt/bieu_tuong.ico/.png` (biểu tượng exe đổi khi dựng lại bộ cài; từ 0.9.27
  là nguồn DUY NHẤT - logo_PABT.png nền xanh đã bỏ).
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
  Hoàn tác / Làm lại (`CuaSoChinh.nut_ht`): từ 0.9.25 là QAction ở menu "Chỉnh sửa" trên thanh menu (người dùng 11/10/2026 - như
 phần mềm khác; trước đó nút trên băng tiêu đề), xem mục 0.9.25.
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
- TỪ 14/10/2026 (0.9.87, người dùng): dựng bộ cài GIỮ các bộ cài / gói cũ trong `bo_cai\`, KHÔNG xóa, KHÔNG chuyển sang `G:\` (bỏ qua ổ G:) - thay quy định cũ dưới đây.
  `rut_gon.HE_THONG_WIN7` có `msvcrt` (openblas của numpy, đi kèm ezdxf). Dựng bằng chuỗi lệnh: dừng khi một bước lỗi (`set -e` trong subshell có `||` KHÔNG dừng - 0.9.87 đã đóng gói nhầm bản Win7 chưa tự kiểm).
- Dọn bản cũ (09/10/2026, người dùng yêu cầu): chỉ giữ bộ cài / gói mới nhất trong `bo_cai\`. TỪ 14/10/2026 (người dùng đổi): sau khi chạy
  test + dựng bộ cài mới, CHUYỂN các bộ cài / gói cũ (`PABT_Setup_*`, `PABT_ChayNgay_*`, `PABT_CapNhat_*`) sang THƯ MỤC GỐC `G:\` (người
  dùng tự khôi phục các bản 0.9.65-0.9.80 từ Thùng rác vào đó) - KHÔNG đưa vào Thùng rác nữa; trùng tên trên G: thì bỏ qua, không ghi đè.
  Gói `.pabtcn` của bản trước (mốc `phan_tich_phien_ban.py --so-sanh`) vì thế nằm ở `G:\`. File trung gian dựng / sao lưu khác vẫn -> Thùng rác. Bỏ `THU_MENU_TRAI.bat`, `so_sanh_giao_dien\` (thử menu trái 0.9.3 - nay là mặc định).
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
  63 px (logo 46, chữ 17/12 px, phiên bản + BẢN THỬ NGHIỆM cùng hàng; GIỮ tên đơn vị, "Trực thuộc… • địa chỉ" - người dùng
  yêu cầu trước đây; Hoàn tác / Làm lại từ 0.9.25 ở menu Chỉnh sửa); chữ dài trên băng = `giao_dien.NhanRutGon` (một dòng, rút gọn "…",
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
  - Biểu tượng: `logo_PABT_nen_trang.png` (chữ PABT tách khỏi ảnh nền của logo_PABT.png, nền trắng sữa #FBF7EE) - từ 0.9.27
    nguồn duy nhất, xem mục 0.9.27.
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
    (`luu_du_an_lenh`: commit + fsync, báo giờ - dữ liệu vốn ghi ngay mỗi thao tác); thanh trạng thái `lb_tom_tat`
    "Sẵn sàng · Tổng cộng: N hộ | Đã chọn: k hộ" (KHÔNG showMessage cố định - che
    widget trái), đèn LAN gộp vào `nut_tk` ("● LAN: Trực tuyến · Tài khoản…" / "Ngoại tuyến (Offline)" / "Máy đơn"), phiên bản chỉ
    ở băng tiêu đề. Màn hình chào: liên kết nhỏ Hướng dẫn sử dụng (F1) góc dưới phải, không cạnh 3 nút bắt đầu.
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
- 0.9.25 (người dùng 11/10/2026):
  - Mẫu in tìm THEO TỪNG MẪU: `in_an.thu_muc_mau(ten=TEN_CT)` (thư mục đầu tiên có `<ten>.xlsx`), `file_mau(None, ten)`,
    `ds_mau`, `mau_de_sua` (chép mẫu còn thiếu). Trước đây chọn thư mục theo IN_CHITIET: "Cập nhật mẫu in" từ file một sheet
    để %APPDATA%\PABT\mau_in chỉ có một mẫu -> bảng tổng hợp FileNotFoundError (tu-kiem "Lập và in thử" LOI trên máy người
    dùng), mẫu bảng tổng hợp đã sửa bị bỏ qua. `xuat_hang_loat` bảng tổng hợp truyền mau=None. Test `tests/test_mau_in_mot_loai.py`.
  - Vật nuôi: dự án lập trước bộ đơn giá có vật nuôi (QĐ 31/2025) không có dòng nào -> thẻ Vật nuôi trống. `don_gia.bo_sung_vat_nuoi`
    (chỉ thêm mã còn thiếu, mo_khoa_danh_muc + ghi_nhat_ky), thẻ Vật nuôi `khung_thieu_vn` + nút "Bổ sung vật nuôi từ bộ đơn giá"
    (`CuaSoLapPA.bo_sung_vat_nuoi`, cập nhật `bo.dm` và `dm` cửa sổ chính). dự án thật lập trước đó: 0 -> 17 mục.
  - Ô Nhân khẩu: `giao_dien.OSoChuaNhap` (QSpinBox có specialValueText "chưa nhập": bấm / Tab / gõ phím thì chữ mất - trước đây
    gõ số dính vào chữ "ch1ưa nhập"). Test `tests/test_vat_nuoi_nhan_khau.py`.
  - Test chạy với file Excel mẫu (`PABT_EXCEL` = `PABT_CHUAN_06-10-2026_QD42.xlsm` NẰM TRONG thư mục dự án, `kiem_tra_toan_bo.py
    --mau`): 9 bài cũ chưa cập nhật theo 0.9.17-0.9.24 (số lượng "130,0", 6 thẻ, tuyến 3,5%, tiêu đề mục vật nuôi, DT 0 cho lưu,
    ô tìm chờ 200 ms) - đã sửa. Bài GUI lỗi giữa chừng để CuaSoLapPA mở -> tiến trình TREO khi thoát (hộp hỏi lưu): chạy test
    bằng Start-Process có hạn giờ. Ngoài phiên Claude: venv38_32 ở `%LOCALAPPDATA%\Packages\Claude_pzs8sxrjxfjjc\LocalCache\
    Local\PABT_dev` - dựng Win7 bằng `dung_exe38.py` với LOCALAPPDATA đặt tạm thư mục đó (chỉ tiến trình dựng).
  - `kiem_tra_giao_dien.py` chạy được trên màn hình thật: `QT_QPA_PLATFORM=windows` (mặc định offscreen).
  - Thử MÁY TRẮNG sau khi đóng gói (không cài đè bản thật như `--cai-thu`): `ket_qua_kiem_tra\thu_that\thu_may_trang.ps1`
    (chạy bằng -Command ReadAllText UTF8 như CAI_DAT.cmd): giải nén từng bộ cài (`/C /T:`), chép bằng `cai_dat.ps1 -ChiChep`
    (kiểm SHA-256) vào %TEMP%, `PABT.exe tu-kiem` với môi trường trống (ProcessStartInfo: APPDATA / LOCALAPPDATA / TEMP /
    USERPROFILE mới, PATH chỉ thư mục hệ thống). 0.9.25: cả 3 bộ cài DAT, chỉ tạo %APPDATA%\PABT\mau_in\mac_dinh.
    `donggoi.pdf` người dùng gửi (PyQt + Inno Setup + onefile + cài VC++ Redistributable): KHÔNG theo các điểm đó (Inno >= 6.5 lỗi
    Win 11, VC++ đã nằm trong bản dựng + kiem_dll, onedir mở nhanh hơn); phần còn lại (loại module Qt, dữ liệu ở %APPDATA%, thử
    máy sạch) đã có trong quy trình.
  - Hoàn tác / Làm lại: menu "Chỉnh &sửa" (sau Tệp tin) = `self.nut_ht` (QAction, chữ "Hoàn tác: <thao tác>\tCtrl+Z" như Office,
    `_cap_nhat_nut_ht`); băng tiêu đề không còn nút. KHÔNG gắn setShortcut Ctrl+Z / Ctrl+Y cho QAction: phím tắt QAction chạy trước
    KeyPress -> bỏ qua `giao_dien.xu_ly_hoan_tac` (Ctrl+Z theo khung / cửa sổ đang làm việc); chữ sau "\t" chỉ để hiện.
- 0.9.26 (người dùng 11/10/2026):
  - Lỗi hình góc trên bên phải khi mở (máy 2 màn hình, 125%): `showMaximized()` ngay lúc tạo -> kiểu áp lúc Show (`_BoToMau`)
    làm bề rộng tối thiểu tăng (1380 -> 1414 điểm) > kích thước thường 1360 -> Qt ép lại kích thước SAU khi phóng to: Windows ghi
    "phóng to" nhưng cửa sổ 1414 x 760, phần màn hình còn lại hiện cửa sổ phía sau. `app.hien_cua_so(w)`: setGeometry = vùng làm
    việc của màn hình rồi showMaximized (KHÔNG show() rồi QTimer phóng to: khung đầu đen). Đo / giả lập:
    `ket_qua_kiem_tra\thu_that\do_khoi_dong.py [--cu] [--ep]` (QT thật, in Qt size x dpr so với GetClientRect; --ep ép bề rộng
    tối thiểu 1414 trong sự kiện Show).
  - Bề rộng tối thiểu cửa sổ chính 1414 / 1443 -> 1020 điểm (màn hình 1366): hàng công cụ danh sách hộ = `giao_dien.XepDong`
    hai khối (nút | bộ lọc Đợt / Trạng thái / Tìm - hẹp thì xuống dòng); `lb_ket_qua` (đối chiếu, ~980 điểm) setWordWrap.
    Thêm widget vào hàng một dòng: đo `w.minimumSizeHint()` trên dự án thật (offscreen phông khác - test chỉ kiểm cấu trúc).
  - Nút "Xuất" (thanh công cụ danh sách hộ) = QAction `Xuất danh sách hộ…` (iconText 'Xuất', cũng ở menu Dữ liệu, bật khi chỉ
    xem) -> `CuaSoChinh.xuat_danh_sach`: hộ đang chọn (>= 2) hoặc đang lọc -> `bao_cao_tong_hop(ds=, dieu_kien=, ten_file=,
    tieu_de=, hoi=)` (cùng bảng Báo cáo tổng hợp; tên file `DanhSachHo_<đợt>_<trạng thái>_<giờ>.xlsx` ở thư mục hồ sơ).
  - `kiem_tra_toan_bo.CAI`: tìm bản cài ở Program Files (x86) / Program Files rồi %LOCALAPPDATA%\Programs (trước: chỉ chỗ cũ).
    Bước 6 / 10 theo bộ Universal + zip Universal (kiểm cả danh_sach_x64 / x86 khớp SHA-256). `thu_may_trang.ps1`: mỗi gói
    (exe, zip) thử nhánh tự chọn + nhánh x86 ép (ban.txt = win7, danh_sach_x86 -> danh_sach.txt) - máy dựng là Win 11 64-bit.
  - Test `test_giao_dien.test_mo_phong_to_va_khong_ep_rong`, `test_xuat_danh_sach_ho`.
- 0.9.27 (người dùng 11/10/2026):
  - MỘT biểu tượng (bỏ logo_PABT.png nền xanh - Thùng rác - và hình vẽ dự phòng `ve()` cũ): `tao_bieu_tuong.py` lấy khung chữ
    (điểm khác màu nền > 14) của logo_PABT_nen_trang.png, làm nét (unsharp: ảnh mờ = thu 1/3 rồi phóng lại, k = LAM_NET), đặt
    giữa ô lề LE_CHU (trước: cắt vuông nguyên ảnh - chữ P / T bị góc bo cắt), thu nhỏ từng nấc 1/2, viền ngoài #0F3866 (3%) +
    đường vàng #F2B705 (1,2%, từ 24 px). Băng tiêu đề: ô logo trong suốt, pixmap 46 px (viền nằm sẵn trong ảnh). Xem trước:
    `ket_qua_kiem_tra\thu_that\xem_bieu_tuong.py`. Test `test_giao_dien.test_bieu_tuong_duy_nhat_co_vien`.
  - Menu trái: lệnh không có ký hiệu (hoặc máy không có phông biểu tượng) -> `nut_menu` gắn biểu tượng TRỐNG lên QAction (nút
    lấy lại biểu tượng của lệnh mỗi khi lệnh đổi), `icon_trong`: thu gọn menu vẫn hiện chữ - trước đây Qt căn chữ ra giữa ("Bảng
    giá đất"). KY_HIEU thêm 'bang gia dat' (0xE707), 'trang chu' (0xE80F).
  - Lệnh "Màn hình chính" (đầu nhóm Dự án & dự toán; trước là "Trang chủ") -> `CuaSoChinh.ve_trang_chu`: trang TRANG_CHAO, dự án
    vẫn mở, dấu chọn `_danh_dau_trang_chu`; `lb_chao` đổi chữ theo dự án đang mở (`_nap_gan_day`). Test `test_trang_chu_va_bieu_tuong_menu`.
- 0.9.29 (người dùng 11/10/2026):
  - Bộ đơn giá: `quan_tri_bo` (mật khẩu PBKDF2 ở `<thư mục máy>/quan_tri_bo.json`; tài khoản quản trị máy chủ LAN được sửa
    không cần mật khẩu; người dùng máy chủ thường bị chặn). `HopBoDonGia` nút **Sửa bộ đơn giá** (thêm / sửa / xóa / thay
    thế một mục + đổi mật khẩu); `don_gia.them_dong/sua_dong/xoa_dong/thay_the_dong` ghi bản máy (`dam_bao_ban_sua`). Cập
    nhật cả bộ (file / web) cũng cần mở khóa. Thẻ Quy ước khi có dự án mở đọc `con_du_an` (nhãn "· dự án");
    `don_gia_rieng` sau khi lưu gọi `nap()` — xóa ở Đơn giá riêng thì danh sách thẻ đổi theo.
  - Màn hình chính: nút Đóng dự án / Xóa dự án (Tệp tin + hàng nút khi có dự án); dưới danh sách gần đây: Mở đã chọn, Xóa khỏi
    danh sách, Xóa file `.pabt` (`xoa_du_an`, `bo_gan_day`). Không thoát phần mềm. Test `tests/test_yeu_cau_0929.py`.
    Hướng dẫn trên trang chào = `lk_huong_dan` (NhanBam, góc dưới phải), không còn nút cạnh 3 lệnh bắt đầu.
- 0.9.30 (người dùng 11/10/2026): liên kết Hướng dẫn chân trang chào; bỏ chữ "Cơ quan: …" góc phải thanh menu
  (`lb_co_quan` / `_dat_co_quan`).
- 0.9.31 ARCH-PABT-2026-V5: ẩn `bang_tieu_de` (tiết kiệm ~65 px); menu bar 38 px navy + logo + `lb_du_an_nho` / `lb_lan_nho`;
  `thanh_tab` (QTabBar document mode, Ctrl+Tab) trên `QStackedWidget` giữ chỉ số trang cũ; welcome: thẻ 3 nút, `QTableWidget`
  dự án gần đây (5 cột), chân trang 3 liên kết; TOKEN accent `#2563EB`, menu trái vạch trái 3 px khi chọn. KHÔNG làm: viết lại
  4 tầng, đệm mẫu Excel trong RAM, bỏ Office/VBS, WA_DeleteOnClose hàng loạt, tab Bộ đơn giá / CuaSoLapPA (vẫn hộp thoại).
  Test `tests/test_dac_ta_v5.py`.
- 0.9.32 V5 đủ: `tao_thanh_tieu_de_hop_nhat`, `KhungLamViecDaTab`, `TheChao` + `QSS_THE_CHAO`; tab **Hộ: …** (`CuaSoLapPA`
  nhúng, `nhung_tab`) và **Bộ đơn giá**; ghim `du_an_ghim.json`; chân trang QĐ 08/2025 + NQ 28; `VANG` = `#2563EB` (bỏ neon);
  icon menu trái đơn sắc `TOKEN['chinh']`. `cho=False` vẫn trả hộp thoại (test). 0.9.33: Ctrl+S trên tab hộ gọi `luu` rồi fsync (tắt shortcut Save của hộp nhúng để khỏi trùng phím); tab `setMovable`; chân trang thêm Cài đặt. 0.9.34: `tao_dai_nhan_dien` 48px (logo, tên phần mềm, `to_chuc.TEN` / `don_vi_lap`, dự án, LAN) dưới menu 26px; `kiem_loi` không báo lỗi họ tên có chữ số. KHÔNG làm: frameless (giữ title bar Windows - từ 0.9.65 thay bằng thanh hợp nhất giữ khung Windows, xem 0.9.65),
  viết lại 4 tầng, đệm Excel, bỏ VBS, khóa phần cứng. Test `tests/test_dac_ta_v5.py`.
- 0.9.38: đường kẻ in cách chữ (`DK_CACH` 5 pt); tiêu đề `QGroupBox` không bị khung cắt. Ô Loại đất = `loai_dat.ds_chon` (đủ Thông tư 08/2024, kể cả RDD). Ô Vị trí = `HopXo` (popup trong màn hình, thanh cuộn) + `ds_vi_tri_nq28` luôn đủ 4 địa bàn kể cả loại đất không có cột giá. Mẫu "Dự thảo (áp giá trước niêm yết)" tooltip Luật Đất đai 2024 / NĐ 88/2024. Menu bar cao cố định 32 px + vạch 1 px (hết lệch vùng bấm). Màn hình chào ẩn Đóng/Xóa dự án; nút Mở căn giữa, viền `#2563EB`.
- 0.9.40: dự thảo PABT (`du_thao.py`, `man_hinh_du_thao.py`, CSDL v13). Không dùng số liệu mẫu. Phễu trên `ho` thật. Ba tỷ lệ: theo đợt / lũy kế đã niêm yết / bao phủ cả dự án. Hộ `ma_vuong` V1–V5 không vào đợt. Niêm yết +10 ngày, đối thoại +30 ngày. Menu Lập phương án → Dự thảo PABT. `bo_don_gia.sqlite` nâng v13 (bảng trống, không hộ).
- 0.9.39: bảng giá đất thay được (`gia_dat_nq28.ghi_thay` / `xoa_thay`, file `%APPDATA%\PABT\bang_gia_dat.json`). Lệnh **Thay bảng giá đất…** đọc Excel (mỗi sheet một địa bàn) và bỏ 4 xã gắn sẵn khỏi tra cứu / ô Vị trí. **Dùng lại bảng giá gắn sẵn** khôi phục. `tat_ca()` đọc file thay nếu có (cache theo đường + mtime). Test `tests/test_gia_dat_nq28.py`.
- 0.9.46: `in_an.nap_mau_in` nhận Excel/PDF, không ném lỗi (không đọc được thì giữ file gốc và dùng mẫu chuẩn). `doc_ty_le('')` = None, `hien_ty_le` để trống, `he_so(None)` vẫn = 1. Danh sách hộ: trạng thái bắt đầu bằng "Đã lập" hoặc có dòng `ct_dat`/`ct_khoan` = đã lập, kể cả 0 đồng. `ho_so.chuan_nguon_goc` tách " - " thành dòng `- `; ô nguồn gốc và bản in thụt lề treo.
- 0.9.47: bỏ mục menu **Quy chuẩn cây** (`Quy chuẩn cây, tài sản…` không còn trong `self.lenh`). Mật độ cây khi **Tính mật độ…** vẫn đọc ghi chú bộ đơn giá. `quy_chuan()` còn để test.
- 0.9.48: `cap_nhat_gia_dat` — web (`tim_tren_web`, LoiWeb thì chọn file) và `doc_file` Excel/Word/PDF/CSV. `ap_dung` = `ghi_thay` (bỏ 4 xã gắn sẵn). Menu **Cập nhật bảng giá đất…** thay **Thay bảng giá đất…** và **Dùng lại bảng giá gắn sẵn** (khôi phục nằm trong hộp).
- 0.9.49: `cap_nhat_web` đóng trong bộ cài (`PABT.spec` / `dung_exe38` không còn `--exclude-module` module này). Thiếu module thì `LoiWeb` tiếng Việt, không hiện `cannot import`. `man_hinh_quet_web` vẫn loại khỏi bản dựng.
- 0.9.50: `tim_tren_web` mở trang chi tiết Công báo (từ khóa ngắn "bảng giá đất"), tải phụ lục .docx, `phan_tich_nghi_quyet` bóc mục xã/phường (MT/T/K) rồi `loc_xa`. Không gán cả tỉnh vào tên xã khi không nhận ra mục.
- 0.9.51: ô địa bàn chỉ cần tên (`ten_gon` bỏ xã/phường/tỉnh/thành phố). Đồng Nai mở thẳng nghị quyết 28/2025; tiêu đề mục dạng `53. Xã Trị An`. PDF ảnh / ảnh: `ocr.tung_trang` từng trang, nút Dừng, dừng sớm khi hết mục xã. Menu Tệp tin: bộ lọc `_BamMenu` mở khi thả chuột. `cap_nhat_mau_in` hỏi mẫu chi tiết hoặc tổng hợp, lưu riêng `%APPDATA%\PABT\mau_in`.
- 0.9.52: menu mở bằng `QTimer.singleShot` sau cú thả chuột. `tim_tren_web` xóa thư mục tạm và dừng khi đã có đất ở lẫn nông nghiệp. `QPdfDocument.close` sau khi đọc. Cột giá trên hộp cập nhật hiện giá nông nghiệp khi đất ở bằng 0.
- 0.9.53: chân trang chào `Lịch sử cập nhật phần mềm` (`lich_su_cap_nhat.MUC`, mục mới ở đầu, cùng số `__version__`). Không chép các bản trước 0.9.53. F1 vẫn mở `HUONG_DAN.md`.
- 0.9.54: bỏ “Cập nhật bảng giá đất…” khỏi nút Giá đất của `HopBoDonGia`. Lệnh cập nhật chỉ còn menu trái (`Cập nhật giá đất`).
- 0.9.55: banner `tao_dai_nhan_dien` cao 42px, logo `KhungLogo` 32px bo 6. Menu `#081226` chữ 13px `#CBD5E1`. Tên phần mềm 11,5px `#F8FAFC`, cơ quan 10px `#93C5FD`. Chip trạng thái, đèn `#10B981`.
- 0.9.56: `setMenuWidget` gộp logo, chữ PABT và `QMenuBar` một hàng cao 52px. Tiêu đề cửa sổ là `PABT`. Không xếp `dai_nhan_dien` thêm một lần trong layout.
- 0.9.57: thanh menu chỉ logo + mục menu, cao 40px. Không hiện chữ PABT / tên cơ quan / chip trên thanh đó.
- 0.9.58: menu nằm trên hàng tiêu đề (cửa sổ không khung), cao 60px, cạnh logo. Không hiện chữ PABT trên hàng đó. Nút thu nhỏ / phóng to / đóng ở cuối hàng.
- 0.9.59: `tao_dai_nhan_dien` hiện lại tên phần mềm và tên cơ quan, cả hai 13px.
- 0.9.60: menu trắng chữ `#1E293B`. Banner xanh `tao_banner_ten` phía dưới: tên phần mềm trắng, cơ quan `#67E8F9`.
- 0.9.61: `MAU_BANG` navy sâu hơn, `VIEN_DAY` `#2563EB` dày 2px, tên cơ quan `MAU_PHU_DE` `#E2E8F0`. Tên phần mềm 12px, cơ quan 11px.
- 0.9.65 thanh tiêu đề hợp nhất kiểu VS Code (người dùng 12/10/2026 - thay quyết định "giữ title bar Windows"): `pabt/thanh_tieu_de.py`
  `ThanhTieuDe` (logo, QMenuBar `CuaSoChinh._mb_rieng` - `menuBar()` ghi đè trả nó, Hoàn tác / Làm lại theo `nut_ht`, tiêu đề giữa =
  windowTitle, Hướng dẫn, Cài đặt, nút cửa sổ `nut_cua_so` property `nut_cua_so` - kiem_tra_giao_dien bỏ qua) qua `setMenuWidget`.
  `_KhungWin32`: FramelessWindowHint + thêm lại WS_CAPTION | WS_THICKFRAME… + thay WNDPROC bằng ctypes (Qt 6.11 xử lý
  WM_NCCALCSIZE / WM_NCHITTEST TRƯỚC nativeEvent và QAbstractNativeEventFilter - đã thử, không nhận được); NCCALCSIZE trả 0, phóng
  to thu client bằng bề dày khung (không thì tràn ~9 px); NCHITTEST: mép `VIEN_KEO` đổi cỡ, `la_vung_keo` = HTCAPTION (Aero Snap,
  bấm đúp, menu hệ thống do Windows làm). Đừng gọi `winId()` trong thủ tục / nativeEvent (tạo lại cửa sổ -> đệ quy, sập).
  Qt 6.11 `ExpandedClientAreaHint` trên Windows tự vẽ thanh tiêu đề, không đặt widget lên được - không dùng. Dự phòng
  `dung_thanh_hop_nhat()` False (bản Qt 5 Win7, `--khung-windows`, `PABT_KHUNG_WINDOWS`) hoặc gắn lỗi -> `dung_khung_windows`.
  Banner `tao_banner_ten`: `goc_phai` (Fixed) giữ ô dự án `NutRutGon` (≤ `RONG_O_DU_AN`, rút "…"), máy đơn, phiên bản, tem; chữ
  trái NhanRutGon (Ignored). `vua_cao_menu` = max(`CAO_MENU`, sizeHint): ép 28 px ở DPI 125% làm Qt dồn mọi mục vào "»".
  Bỏ `gan_nut_cua_so` (nút tự vẽ thời không khung). Test `tests/test_dac_ta_v5.py`.
- 0.9.65 tải lớn: `ket_qua_kiem_tra/thu_that/do_tai_lon.py --so-ho 5000` (nhập: Dự án mới, Excel thô, .xlsm, nhập tay 1 hộ, doc_so;
  lệnh: mở, trang, lọc, lập PA, lưu + tải lại, tính nguội / có đệm, kiểm tra lỗi, đối chiếu, xuất xlsx, xóa / hoàn tác; cProfile
  bước > 400 ms). `kiem_loi.loi_font` đường tắt regex `_RE_KY_TU_LA` (×12, nhánh đầy đủ `_loi_font_day_du` - test so 30.000 chuỗi);
  `doi_chieu.xuat_bao_cao` `_kieu`: chép StyleArray thay gán Border / Fill từng ô (×2,3, so 55.105 ô giống hệt). openpyxl
  StyleProxy KHÔNG so bằng nội dung (`x.font == y.font` luôn False giữa hai ô) - so `._StyleProxy__target`. Còn chậm: bảng tổng hợp
  5.000 hộ ~5 s (ghi xlsx của openpyxl + gộp ô), Dự án mới ~3,8 s, nhập Excel thô 10.000 dòng ~1,6 s (cần chế độ đầy đủ vì ô gộp).
  `in_an.la_mau_du_thao` bỏ dấu (mẫu riêng "Dự thảo" có dấu bị coi là bản chính thức, chữ DỰ THẢO bị xóa).
- 0.9.65 giá đất web (`pabt/nguon_gia_dat.py`, khảo sát `ket_qua_kiem_tra/GiaDat_NguonWeb_0.9.65.md`): KHÔNG có nguồn chính thức đọc
  bằng máy cho 34 tỉnh (Công báo chỉ Đồng Nai / Tây Ninh chung nền tảng; vbpl.vn mới = Next.js Server Actions, không API ổn định;
  thuvienphapluat 403, thuviennhadat 500). `tim_tren_web(tinh, xa, url=, tham_khao=True)`: (1) url dán + danh bạ
  `danh_ba_gia_dat.json` (thư mục máy, `DANH_BA_GAN_SAN` Đồng Nai) - đọc được thì `ghi_danh_ba`; file phụ lục tải thẳng, không lọc
  < 80 KB; (2) tìm Công báo / vbpl; (3) `doc_guland` (9 tỉnh `GULAND`, VT1-4, `tham_khao=True`, `NHAN_THAM_KHAO` vào căn cứ).
  `chuan_tinh` 34 tỉnh + tỉnh cũ (NQ 202/2025/QH15). `an_toan.nap_goc_ca_windows`: Python chỉ đọc gốc CA đã có trong kho Windows
  -> lỗi CERTIFICATE_VERIFY_FAILED thì cho .NET kết nối thử (Windows tự tải gốc, vẫn xác minh) rồi `_mo` thử lại MỘT lần.
  Test `tests/test_nguon_gia_dat.py` (trang GIẢ LẬP, không mạng). Phụ lục tỉnh khác Đồng Nai: thử trên file THẬT trước khi thêm mẫu.
- Dựng 0.9.65 trong phiên Claude: `dung_bo_cai_win._goi_moi` lỗi FileExistsError - `PABT_dev\goi_universal` THẬT (lần dựng trước)
  còn sau rmtree vì MSIX ảo hóa %LOCALAPPDATA% -> nay tạo tên phụ `goi_<ban>_<pid>` (dọn ở lần sau). Kiểm máy trắng:
  `thu_may_trang.ps1` chạy bằng `[scriptblock]::Create(ReadAllText(UTF8))` (4 trường hợp exe / zip × x64 / x86 ĐẠT).
- 0.9.66 mỗi lệnh một chỗ (người dùng 12/10/2026: "menu trái hoặc thanh menu đã có thì bỏ lệnh trùng"): menu trái + thanh menu
  là hai chỗ chính, KHÔNG lặp nhau (Dữ liệu bỏ Báo cáo tổng hợp / Xuất báo cáo đối chiếu, Công cụ bỏ Bộ đơn giá, Cài đặt bỏ Thông
  tin dự án); không lặp thành nút: thanh tiêu đề chỉ 3 nút cửa sổ (bỏ Hoàn tác / Làm lại / Hướng dẫn / Cài đặt), thanh công cụ danh
  sách hộ chỉ Thêm hộ / Xóa hộ (`nut_ds`), bỏ `hang_chon` (số hộ chọn ở `lb_tom_tat`), bỏ `hang_dong_xoa` / `nut_chao_du_an` (luôn
  ẩn), chân trang chào chỉ "Lịch sử cập nhật phần mềm" (bỏ `lk_cai_dat`, liên kết NQ 28). GIỮ: thẻ bắt đầu màn hình chào
  (`nut_chao`), menu chuột phải (dùng QAction), nút "Xuất Excel…" của từng trang (mỗi trang xuất bảng riêng). Thêm nút / mục mới:
  `tests/test_khong_trung_lenh.py` chặn trùng. Kiểm kê lệnh: `kiem_ke_lenh.py` trong phiên Claude (QAction -> các chỗ đặt).
- 0.9.67 nhập tài sản DÙNG CHUNG phương án hộ + dự toán (người dùng 12/10/2026): `pabt/nhap_tai_san.py` (không Qt) -
  `them_mot(dich, muc, m, ten, so_luong, ty_le, kieu, ghi_chu)` -> (i, thông báo, tự do?) (danh mục / tên tự do / cây theo
  đường kính - chu vi `_them_theo_do`), `them_dong_tho` (một dòng hộp Dán danh sách); đích `DichPhuongAn(bo)` (BoSoan) /
  `DichDuToan(dt, dm)` (DongDT, vật nuôi gộp mục 3, tỷ lệ = he_so, quy cách -> ghi_chu) cùng giao diện them_danh_muc / them_tu_do /
  dat_so_luong / dat_ty_le / dat_ghi_chu / dat_quy_cach / dat_dvt. `pabt/hang_nhap_nhanh.py`: `HangNhapNhanh(them, muc=|chon_muc=)`
  (+ `ds_chon_nhanh` / `lam_san` / `KIEU_SL` chuyển từ man_hinh - man_hinh xuất lại tên cũ), `sau_chon(m)` -> True = đã đặt con trỏ
  (BangMuc mục 4 `_sau_chon`: ô theo cách tính ổn định / đào tạo / thuê nhà - riêng hộ, KHÔNG có trong dự toán). BangMuc: `self.hang`
  + bí danh o_chon / o_sl / o_tl / o_gc / cb_kieu / nut['Thêm vào bảng']. `HopDanTaiSan(cua_so, chu, dich=)` gọi
  `cua_so.sau_khi_dan_tai_san(n, muc)`. KhungDuToan: `hang` (cb_muc Nhà / Cây / Vật nuôi / Hỗ trợ / Thưởng), `them_nhanh(**thay)`,
  `dan_tai_san`, `lb_tb` (ẩn khi trống), bỏ `b_hm` "Thêm hạng mục" + `them_tu_nhom`; `them_danh_muc(m)` đi qua DichDuToan. Test
  `tests/test_nhap_tai_san.py` (cùng thao tác trên hai đích ra cùng tên / SL / ĐG / tỷ lệ / ghi chú). `cb_kieu` chỉ tạo khi hàng
  có mục 3 (None ở thẻ khác): luôn tạo làm mở cửa sổ lập PA chậm 4-9 ms (đo riêng 15 lần, máy rảnh). PhanTich chạy cùng lúc dựng
  bộ cài cho số nhiễu ±20-30% - nghi chậm thì đo riêng trước khi kết luận.
- 0.9.68 "Tệp tin" không bấm được (người dùng 12/10/2026): `KhungLamViecDaTab` (bộ điều khiển tab, cha = cửa sổ chính, KHÔNG nằm
  trong bố cục - bar / stack_phu xếp chỗ khác) HIỆN ở góc (0, 0) 100 x 30 trong suốt, nuốt cú bấm vào mục menu đầu (từ 0.9.32;
  0.9.51 / 0.9.52 tưởng DPI nên thêm `_BamMenu` mở menu khi thả chuột - nguyên nhân thật là khung này). Nay `setVisible(False)` +
  WA_TransparentForMouseEvents. Widget con của cửa sổ chính không nằm trong bố cục = phải ẩn. Test `test_khong_trung_lenh.
  test_moi_muc_menu_bam_duoc` (childAt tâm mọi mục menu = QMenuBar, cả khung Windows). Thử bấm thật: SendInput với INPUT 40 byte
  (x64) - khai 48 byte thì SendInput trả 0, lỗi 87, không cú bấm nào tới cửa sổ.
- 0.9.69 (người dùng 12/10/2026, 18 mục):
  - MÃ TÀI SẢN (CSDL v14, `_NANG_CAP[13]` = cột `du_an.chu_dau_tu` + "@doi_ma_tai_san"): nhà TS1…, cây CT1… (= TS140… cũ, `ma_tai_san.
    CAY_TS_DAU`), vật nuôi VN1… (VN01 cũ), chính sách hỗ trợ CS1… (HT01 cũ), thưởng TH1… (`ma_thuong(i)` - biểu thưởng không lưu mã,
    đánh theo thứ tự mức). `ma_tai_san.chuyen_csdl(con)`: đổi dm_taisan / dm_hotro (hai bước qua mã tạm), ct_khoan.ma / ma_tuong_duong,
    BỎ dm_taisan nhóm 4 / 5 (dòng HT / TH lẫn vào thẻ Nhà - trùng dm_hotro / bieu_thuong); chạy lại không đổi thêm. Gọi khi nâng cấp
    CSDL, sau `nhap_excel` (file PABT Excel vẫn mã cũ), `tao_bo_don_gia.chuan_hoa` (`--chuan-hoa`), `don_gia._nang_cap_ban_may` (bản
    bộ đơn giá ở %APPDATA% của phiên bản cũ). Mã mới khi thêm mục: `ma_tai_san.ma_tiep` / `tien_to`. Mã cố định trong nguồn (HTnn ->
    CSn, VN0n -> VNn) đã đổi bằng script; dm_hotro sắp `ORDER BY LENGTH(ma), ma` (CS10 sau CS9). Dự toán `.pabtdt` cũ: `du_toan._doi_ma_dong`.
  - QUY ƯỚC: bộ đơn giá đóng gói không còn dòng quy_uoc (0 dòng); quy ước chỉ do người dùng tạo ở Đơn giá đặc biệt (id >= ID_RIENG),
    thẻ Quy ước của HopBoDonGia bỏ (`I_QUY_UOC = -1`). `ds_chon_nhanh` bỏ quy ước id < ID_RIENG của dự án cũ.
  - Menu: Dự thảo PABT -> "Niêm yết & Lấy ý kiến" (tab `TEN_TAB` dùng "&&"), Đợt trình -> "Trình phê duyệt", Bộ đơn giá -> "Đơn giá
    bồi thường", Đơn giá riêng -> "Đơn giá đặc biệt"; bỏ "Tổng quát hộ" khỏi menu trái (vẫn là thẻ đầu Bảng tổng hợp). Khóa `self.lenh`
    giữ tên cũ (test, kiem_tra_giao_dien). Mở / nhập dự án -> `mo_trang(0)` (Danh sách hộ), không về trang đang chọn.
  - Thẻ Vật nuôi: danh sách trống (dự án cũ chưa có VN) -> `OTimChon.khi_trong` -> `CuaSoLapPA.bo_sung_vat_nuoi(hoi=True)`.
  - Bản in: đường kẻ dưới "Dự án" dài `in_an.DK_DU_AN_CM` (7 cm), giữa dòng chữ; ô nguồn gốc ngang justify, dọc center; mục đất / thưởng
    0 đồng để trống SL / ĐG / tỷ lệ; thưởng: thành tiền in đậm, ĐVT trống.
  - Thông tin dự án: `chu_dau_tu` (TRUONG_DU_AN, `doc_du_an` chịu được file chỉ xem < v14); kinh phí chỉ ô Loại dự án (bỏ `o_tl_kp`,
    tỷ lệ '' = mức tối đa của loại).
  - Trình phê duyệt: mẫu mặc định TO_TRINH = văn bản đề nghị thẩm định, phê duyệt PA và quyết định thu hồi đất theo file người dùng gửi
    ("VĂN BẢN THẨM ĐỊNH & PHÊ DUYỆT.doc" ở thư mục dự án - KHÔNG đóng gói, có số liệu thật), dựng trong mã `_noi_dung_to_trinh` (không
    tên đơn vị / dự án / người ký thật; QĐ phê duyệt dự án, thông báo thu hồi đất = dòng chấm; căn cứ chung QĐ 30/2025, 42/2025,
    18/2026 giữ). Không có bảng hộ (bảng tổng hợp đính kèm). Chỗ trống mới: chu_dau_tu (trống -> "Chủ đầu tư"), don_vi_cap_tren,
    cap_dia_ban_thuong, so_ho_02, KY_THAY ("KT. GIÁM ĐỐC" khi chức vụ ký bắt đầu "Phó"). `_bang(doc=, lech=)`, `_p(trai=, phai=, dong=)`.
    BỎ mẫu Phương án tổng: `LOAI` chỉ 'to_trinh', không còn `pa_tong=` ở `xuat_bo_ho_so` / `quan_ly.xuat_dot`, `o_pat` ở HopIn /
    HopDotTrinh (số / ngày PA tổng của đợt vẫn dùng ở bảng tổng hợp + tờ trình). `HopDotTrinh.xoa_so` (nút "Xóa số PA chi tiết").
  - Chọn hộ niêm yết (mục 9): lệnh 'Chọn hộ niêm yết…' (nút thanh công cụ danh sách hộ + chuột phải; không ở menu trái / menu trên) ->
    `man_hinh_du_thao.HopChonNiemYet` (hộ đang chọn >= 2, không thì cả dự án): `du_thao.danh_gia_niem_yet` (đã lập - tự lập chưa soát
    KHÔNG đạt, họ tên, nguồn gốc mọi thửa, không tranh chấp, không vướng V1-V5; `can_xem` = cảnh báo kiem_tra_pa, không chặn; đọc gộp,
    167 hộ 17 ms) tích sẵn -> `ghi_danh_dau` (ho.du_dieu_kien, hộ vướng bỏ qua) + tùy chọn `dua_ho_vao_dot`. Test `tests/test_yeu_cau_0969.py`.
- 0.9.70 đặc tả ARCH-PABT-2026-V7 (`phuong_an_tich_hop_du_thao_va_y_kien_dan.txt` ở thư mục dự án, người dùng 12/10/2026):
  - Menu trái: nhóm tên None/'' = nút độc lập + vạch ngăn (`menu_trai`; `thanh_lenh` thẻ không chữ) -> "Màn hình chính" trên
    cùng, rồi 6 nhóm '1. Khái toán & dự toán' (Dự toán & khái toán, lệnh mới 'So sánh với thực tế' = `so_sanh_du_toan`: trang dự
    toán thẻ 1) / '2. Dự án triển khai' / '3. Đơn giá & bảng giá' / '4. Lập phương án' / '5. Tổng hợp & trình duyệt' / '6. Phê
    duyệt & bàn giao'. Nhãn mới qua NHAN_MENU (khóa self.lenh GIỮ tên cũ; TRANG có '&' trong NHAN_MENU không bị vòng '&&' ghi đè);
    `lb_trang` / `_ten_tab` dùng nhãn NHAN_MENU. Rời menu trái: 'Cập nhật bảng giá đất…' -> menu Công cụ, 'Trạng thái hộ…' ->
    menu Dữ liệu (+ chuột phải). KHOA_NHOM_DONG '..._3', NHOM_DONG_MAC_DINH nhóm 1, 3, 6. KY_HIEU thêm mẫu cho nhãn mới (so
    sánh 0xE8AB, đơn giá bồi thường / đặc biệt, niêm yết, theo dõi chi trả, báo cáo tiến độ) - nhãn mới phải có biểu tượng.
    KPI `the_so` (6 thẻ) giữ nguyên.
  - Khái toán: `du_toan.TRUONG_CHUAN_BI` / `NHAN_CHUAN_BI` (ten, chu_dau_tu, nguon_von (`NGUON_VON`), dia_ban, quy_mo_dt,
    so_thua_dk, so_ho_dk - chữ, lưu trong .pabtdt; file cũ thiếu khóa -> ''). `KhungDuToan._khoi_chuan_bi` (QFrame#khoi_chuan_bi,
    `o_cb` {khóa: ô}) thay hàng Dự án / Địa bàn / Địa chỉ (bỏ ô Địa chỉ; `dia_chi` vẫn đọc / ghi, bảng khái toán in `dia_chi or
    dia_ban`). `lay()` giữ các ô đã gõ, chỉ điền ô trống từ nguồn khối lượng. Bảng dự toán / các nút bên dưới không đổi.
  - Niêm yết & Lấy ý kiến 4 thẻ: '1. Niêm yết công khai' (QSplitter: bảng niêm yết + khung "Hộ vướng / chưa đủ điều kiện" - thẻ 5
    cũ, giữ đánh dấu V1-V5 / xuất đôn đốc), '2. Lấy ý kiến nhân dân', '3. Đối thoại && Tiếp thu', '4. Tổng hợp kết quả ý kiến';
    tên thẻ không ghi số ngày (chữ chú thích dùng `du_thao.SO_NGAY_*`). KHÔNG thêm bảng dot_niem_yet / y_kien_niem_yet của đặc tả
    (đã có dot_du_thao / y_kien_du_thao từ v13). Test `tests/test_yeu_cau_0970.py`.
- 0.9.71 (người dùng 12/10/2026):
  - Ô Khối lượng: `HangNhapNhanh.o_do` (số đo đường kính / chu vi, chỉ hiện ở kiểu dk / cv - `kieu()`, `_doi_kieu`) tách khỏi
    `o_sl` (Khối lượng, luôn hiện; kiểu dk / cv = số cây MỖI số đo, trống = 1); `gia_tri()['so_do']`; `o_do` chỉ tạo khi hàng có mục 3 (None ở thẻ khác - tạo ở mọi thẻ làm mở lại cửa sổ lập PA
    133 -> 147 ms); `nhap_tai_san.them_mot(...,
    so_do='')` - không có so_do thì so_luong là các số đo (cách gọi cũ: hộp Dán danh sách, test); `_them_theo_do(so_cay=)` nhân số
    cây (nguyên > 0). Enter trên nút: `setAutoDefault(True)` (ngoài QDialog nút Qt chỉ nhận Space); Enter ở ô Loại đất -> Diện tích.
  - Bố cục Khái toán theo `bo_cuc_khai_toan.txt` + mã mẫu `KhungDuToanTinhChinh` người dùng gửi (file .crdownload tải dở - chỉ đọc
    làm tham khảo, KHÔNG dùng lớp mẫu vì không có logic): giữ `KhungDuToan` và mọi đối tượng logic, xếp lại - tiêu đề + chế độ
    (`rd_khai_toan` / `rd_so_sanh`, `nhom_che_do` <-> `self.tab` thanh thẻ ẩn), `_khoi_chuan_bi` + `cb_kp` (Kinh phí QĐ08:
    `activated` -> `_doi_kinh_phi` -> `them_chi_phi(loai)`; `DuToan.loai_kinh_phi` lưu .pabtdt; bỏ nút "Chi phí bồi thường QĐ
    08/2025"), thanh nhập nhanh `thanh_nhap_nhanh` (`b_lay` QMenu: 4 nguồn + Áp đơn giá hiện hành - `b_tu_du_an` nay là QAction;
    `cb_muc_nhap` 1 Đất..6 Thưởng -> `ngan_nhap` QStackedWidget: trang đất / `self.hang` (cb_muc + nut_them của hàng ẨN);
    `b_tra_nq28` chỉ hiện ở Đất, Dán Excel, `b_them` = `them_tu_thanh`, `b_them_dat` bí danh), hàng tiêu đề bảng (Thêm dòng / Tra
    giá đất dòng chọn / Xóa dòng; chuột phải bảng `_menu_bang`), thẻ tổng `lb_tong` (QLabel#the_tong_khai_toan, rich text: tổng +
    bằng chữ + từng mục), hàng đáy (Mở tệp, `tao_moi`, `b_xuat` QMenu 3 loại, `b_luu`). Ctrl+S: `app.luu_du_an_lenh` đang ở trang
    dự toán (`trang` ô 3) -> `khung_du_toan.luu()` (KHÔNG thêm QShortcut Ctrl+S riêng: trùng phím thì Qt không chạy cái nào). Không
    dùng emoji trong chữ nút (Win 7 không có phông emoji; biểu tượng theo `ky_hieu_nut`). Test `tests/test_yeu_cau_0971.py`.
  - Thanh nhập nhanh MỘT hàng (người dùng 13/10/2026): `khoi_nut_nhap` (Tra NQ 28, "Dán danh sách…" `b_dan`, Thêm vào bảng) cuối
    `_h_d1`; ô của `hang` cố định o_sl 90 / o_tl 60 / o_gc 120-180 / o_do 100-150, kiểu ô gọn (`nhap` = '0', không phải kiểu ô nhập
    lớn 14 px); ô chọn rộng theo số ký tự `_co_theo_ky_tu` (cb_muc_nhap, cb_kieu, cb_kp, cb_loai_dat - không theo mục dài nhất);
    `KIEU_SL` chữ ngắn "Đường kính" / "Chu vi" (cm ở chữ gợi ý ô số đo). Thanh `thanh_nhap` sizePolicy ngang Ignored + `eventFilter`
    Resize -> `_xep_thanh_nhap`: rộng >= `can_mot_hang()` thì một hàng, hẹp thì cụm nút sang `_h_d2` - trang tối thiểu ~950 điểm
    (một hàng cần ~1.200 / 1.310 điểm kiểu Đường kính: ép làm bề rộng tối thiểu thì cửa sổ rộng hơn màn hình 1366, lỗi 0.9.26).
    Hàng 2 thông tin: nhãn ngắn `NHAN_NGAN` (Địa bàn / DT dự kiến / Số thửa / Số hộ / Kinh phí QĐ08; tên đầy đủ ở chú thích), ô
    DT 130, Số thửa / Số hộ 75. Test `TestThanhMotHang` (kiểm theo `can_mot_hang`, phông offscreen rộng hơn Windows).
- 0.9.72 (người dùng 13/10/2026): CSDL v15 (`_NANG_CAP[14]`): `du_an.co_quan_tham_dinh`, `dot_trinh.ky_hieu_so`; bộ đơn giá
  đóng gói nâng v15 (`tao_bo_don_gia.py --chuan-hoa 2026.10.12`).
  - `lap_pa.TRUONG_DU_AN` bỏ ten_day_du / so_phuong_an / ky_hieu_so (cột CSDL giữ: file cũ, nhập Excel, in_an); `luu_du_an` ghi
    ten_day_du = ten (trừ khi nơi gọi đưa riêng) - một tên dự án; ĐỪNG đọc `doc_du_an(con)['ten_day_du']` (không còn khóa).
    `co_quan_tham_dinh_mac_dinh(cap, ten)`: phường -> Phòng Kinh tế, Hạ tầng và Đô thị; xã / đặc khu -> Phòng Kinh tế. HopDuAn:
    ô Cơ quan thẩm định = QComboBox sửa được (gợi ý theo cấp / tên địa bàn `_goi_y_tham_dinh`); kinh phí 2 mục (không còn "Tự
    nhận"), `_kp_tu_dong` chọn theo `loai_kinh_phi_tu_ten` khi sửa tên tới khi người dùng `activated`; lưu '' khi còn tự chọn.
  - Ký hiệu số theo đợt: `quan_ly.Dot.ky_hieu_so`, `tao_dot(ky_hieu_so=None -> ky_hieu_mac_dinh: đợt gần nhất, không thì
    du_an / to_chuc)`, `sua_dot(ky_hieu_so=)`, `HopSuaDot.o_ky_hieu`; in: `in_an.ky_hieu_cua_ho(con, ma_ho, mặc định)` trong
    `lap_chi_tiet`, `lap_bang_tong_hop(ky_hieu_so=)`, `van_ban_trinh.du_lieu` (dot.ky_hieu_so trước). Tờ trình: `_PHONG` =
    `{co_quan_tham_dinh}` (trống -> mặc định theo cấp).
  - Danh sách hộ: `ho_so.rut_gon_dia_chi(dia_chi, ten_dia_ban)` cắt từ đoạn trùng xã / phường dự án (bỏ tiền tố xã / phường / thị
    trấn, so không dấu) - xã khác giữ nguyên; `_so_lieu_dong` trả thêm địa bàn; dòng có `dia_chi` đầy đủ (chú thích cột 2, tìm kiếm).
  - CuaSoLapPA: QShortcut Ctrl+Left / Ctrl+Right (+ Ctrl+PgUp / PgDn) -> `sang_ho`; ô chữ vẫn nhảy từng từ (ShortcutOverride).
  - Mật độ: `cay_trong._mat_do_gan_dung` (bỏ chữ "cây" đầu tên, trùng hẳn trước rồi tên dài nhất; nguon 'gần đúng'),
    `mat_do_thuc_te`; `man_hinh_cay.canh_bao_mat_do(bo, i)` (chỉ nhắc, không đổi số liệu; bỏ qua dòng đã tách "mật độ") gọi trong
    `CuaSoLapPA.sua_o` (mục 3, cột so_luong) và `_sau_khi_them` (mục 3); HopMatDo thêm dòng "Mật độ thực tế".
    Test `tests/test_yeu_cau_0972.py`.
- 0.9.73 (người dùng 13/10/2026) nhóm 3 Đơn giá & bảng giá:
  - `HopBoDonGia`: `lb` = dải 28 px (QLabel#dai_bo_don_gia: tên bộ + phiên bản + "QĐ n/yyyy" lấy từ van_ban "…/QĐ-UBND" bỏ dòng "Dự
    thảo" + `trang_thai_khoa()`; mô tả đầy đủ ở chú thích). `b_cap` = Nạp từ file (cap_nhat_file - vẫn nhận Word / PDF) / Sao lưu
    (`sao_luu` -> `don_gia.sao_luu_bo`: .sqlite = sqlite backup API, .xlsx = mỗi BANG_BO một sheet). `b_qt` (= `b_sua`) "Quản trị
    bảo mật": mở khóa, đổi mật khẩu, `khoi_phuc_goc` -> `don_gia.khoi_phuc_bo_goc` (bản máy đổi tên `.truoc_khoi_phuc_<giờ>.sqlite`,
    KHÔNG xóa; cần quyền). Thêm / sửa / thay / xóa mục: `_menu_bang` (chuột phải mọi bảng thẻ). BỎ nút Giá đất / Đơn giá riêng và
    hàm `xem_gia_dat` / `xuat_gia_dat` / `don_gia_rieng` / `cap_nhat_web` / `cap_nhat_mang` của hộp, `don_gia.TRA_CUU` (menu trái có
    Bảng giá đất, Đơn giá đặc biệt; web không dùng được - người dùng). `man_hinh_quet_web` không còn đường mở từ hộp này.
  - `HopDonGiaRieng`: tiêu đề "Đơn giá đặc biệt…", mô tả một dòng (đầy đủ ở chú thích), `b_luu` "Lưu thay đổi" KieuNut.LUU (chỉ bật
    khi có thay đổi); thẻ thẩm định: thanh trên cùng b_file | lb_file | b_dua (KieuNut.CHINH), 6 ô chứng thư QGridLayout 3 hàng x 2
    cặp (Chứng thư số | QĐ phê duyệt giá / Ngày | Căn cứ / Đơn vị | Áp dụng theo). Test `tests/test_yeu_cau_0973.py` (QMenu giả cho
    menu chuột phải - exec chặn kiểm thử).
- 0.9.74 (người dùng 13/10/2026) biểu tượng "PABT Fluent Isometric 3D": nguồn = ảnh thiết kế `pabt/bieu_tuong_thiet_ke.webp` (1024 px,
  người dùng gửi; KHÔNG đóng gói). `tao_bieu_tuong.py` (QT_QPA_PLATFORM=windows, Qt6) -> `ve_bieu_tuong.cat_squircle` (cắt khung 170-853,
  bo góc `BO_GOC`, trong suốt ngoài góc) -> `pabt/bieu_tuong.png` 512 + `bieu_tuong.ico` 9 cỡ (16, 20, 24, 32, 40, 48, 64, 128, 256 - 20 / 40
  cho màn hình 125%), thu nhỏ từng nấc `thu_nho_muot`. Runtime: `giao_dien.bieu_tuong()` = `ve_bieu_tuong.icon()` (QIcon nhiều cỡ từ
  png 512 - Qt5 không cần plugin webp vì chỉ đọc png); `ve_mach` (hình vẽ bằng QPainter) chỉ là dự phòng khi thiếu png. Đổi biểu tượng:
  thay ảnh, chạy lệnh trên, dựng lại bộ cài `--clean` (exe / Desktop / IExpress lấy .ico; gói .pabtcn mang bieu_tuong.png). `app.
  dat_app_user_model_id()` gọi ĐẦU `app.main` TRƯỚC `QApplication` (AppUserModelID `gov.pabt.boithuong.enterprise.2026`; không có
  `main.py` - điểm vào là `chay.py` -> `app.main`). Test `test_giao_dien.test_bieu_tuong_duy_nhat_co_vien` / `test_app_user_model_id`.
- 0.9.87 biểu tượng "Mẫu 3 - Lăng kính công lý & nhịp cầu đồng thuận" (người dùng 15/10/2026, `lenh_tu_dong_thay_icon_mau3.md`): ảnh
  `pabt/bieu_tuong_thiet_ke.webp` là khối pha lê NGHIÊNG 3D trên nền gần trắng -> `tao_bieu_tuong.tach_nen` (loang từ mép ảnh qua điểm
  chênh màu nền < `NGUONG_NEN`, làm mịn mép, cắt vuông theo khung vật thể + `LE`; numpy - chỉ lúc tạo) thay `cat_squircle` / `KHUNG`
  (đã bỏ - cắt khung cố định xén viền khối nghiêng). `ve_mach` dự phòng vẽ cùng tông (xanh băng #38BDF8, trắng sứ, vàng #F59E0B, cam
  #F97316). `KhungLogo` không cắt bo góc nữa, ảnh theo devicePixelRatioF. Gói .pabtcn mang bieu_tuong.png (biểu tượng TRONG phần mềm);
  biểu tượng exe / lối tắt / bộ cài chỉ đổi khi cài bộ cài mới. Test `test_giao_dien.test_bieu_tuong_duy_nhat_co_vien`.
- 0.9.88 nguồn gốc đất bản in (người dùng 15/10/2026, ảnh Excel căn đều): ô căn đều (`_can_nguon_goc` 'justify', mặc định) -> `dat_doan_van`
  gọi `_chia_doan_van(..., treo=False)` / `_ngat(treo=False)`: KHÔNG thụt lề treo gạch đầu dòng (thụt lề treo cần xuống dòng cứng mỗi dòng
  tràn - Excel không căn đều dòng kết thúc bằng xuống dòng cứng -> bên phải lởm chởm); xuống dòng cứng chỉ giữa các đoạn. Màn hình (ô
  nguồn gốc của KhungHoSo) vẫn thụt lề treo. `ho_so.chuan_nguon_goc`: " - " chỉ thành mục mới khi sau dấu kết câu / hai chấm
  (`_RE_GACH_MUC`) hoặc cả dòng là danh sách ngắn >= 2 gạch, mọi đoạn <= `DS_NGAN_TU` từ (`_tach_ds_ngan`, yêu cầu 0.9.46 "đất ở - đất
  lúa"); gạch trong ngoặc đơn / gạch nối tên riêng ("Khu Bảo tồn thiên nhiên - Văn hoá Đồng Nai") giữ nguyên. Dữ liệu đã lưu bị tách sai
  trước đây (chuan_nguon_goc chạy cả khi lưu thửa) KHÔNG tự nối lại - người dùng sửa tay.
- 0.9.88 bảng chi tiết (người dùng 15/10/2026, ảnh mẫu): dòng thưởng bàn giao mặt bằng ('R') chỉ tên + thành tiền (bỏ ĐVT / SL / ĐG /
  tỷ lệ trong `dong_chi_tiet`), tên gộp cột Tên..Tỷ lệ; dòng TỔNG CỘNG ('T') gộp cột STT..Tỷ lệ, căn giữa, đậm - `lap_chi_tiet` (chỉ khi
  các cột liền nhau; chiều cao đo trên bề rộng vùng gộp). `nhap_chi_tiet` dò "TỔNG CỘNG" ở cột STT lẫn cột Tên nên vẫn đọc bản in mới.
- 0.9.88 thứ tự nhóm menu trái (người dùng 15/10/2026): 1 Khái toán & dự toán, 2 Dự án triển khai, 3 Lập phương án, 4 Tổng hợp & trình
  duyệt, 5 Phê duyệt & bàn giao, 6 Đơn giá & bảng giá (trước: Đơn giá là nhóm 3). Khóa `self.lenh` / NHAN_MENU giữ nguyên; tên nhóm cũ -> mới
  trong `giao_dien.TEN_NHOM_CU`, `KHOA_NHOM_DONG` '..._4'; `NHOM_DONG_MAC_DINH` = 1, 5, 6. `LENH_CAN_DU_AN` thêm 'Đơn giá riêng dự án…'
  (Đơn giá bồi thường, Bảng giá đất vẫn bật khi chưa mở dự án - liên kết màn hình chào). Các mục "nhóm 4 / 5 / 6" ghi ở các bản cũ bên
  dưới là số nhóm CŨ. `csdl.uri_chi_doc(p)` thay `Path.as_uri()` (nạp urllib.request ~40 ms lúc màn hình chào đọc dự án gần đây).
- 0.9.88 thanh tiêu đề hợp nhất (người dùng 15/10/2026, màn hình 125%: chữ menu cao hơn chữ tiêu đề 4-5 px): QMenuBar trong `ThanhTieuDe`
  có property `trong_thanh_td` -> `giao_dien.vua_cao_menu` đặt cao ĐÚNG `sizeHint` (QMenuBar vẽ mục sát mép trên, cao dư dồn xuống dưới),
  bố cục canh giữa; menu ngoài thanh hợp nhất vẫn tối thiểu `CAO_MENU`.
- 0.9.75 (người dùng 13/10/2026) nhóm 4 Lập phương án (mã ở `man_hinh_du_thao.py` / `man_hinh.py` / `man_hinh_ho_so.py` - không có file
  `man_hinh_niem_yet.py` / `cua_so_lap_pa.py`):
  - `KhungDuThao`: `b_dua` = nút xổ "Đưa hộ vào đợt" (Thêm toàn bộ hộ đủ điều kiện = `_dua`, Chọn hộ từ danh sách = `_them_ho`; BỎ `b_them` và
    nút "Thêm hộ vào đợt…" lặp ở các thẻ), `b_hop` "Ngày họp dân"; dải `dai_tien_do_ny` một dòng (`lb_dot` "Tiến độ đợt|lũy kế: Đồng thuận a/b (p%)
    · Không đồng ý · Ý kiến khác · Chưa lấy ý kiến", `lb_luy`, `lb_phu` = `NhanRutGon`); thẻ 1 `self.tach` QSplitter dọc (không thu gập, tay
    cầm 10 px); `_nut` {chữ nút: QPushButton} - nút Xuất tắt khi chưa chọn đợt / không dữ liệu. Thẻ 2: cột Ý kiến "● <loại>" màu `MAU_Y_KIEN`,
    `cellClicked` cột 2 / QShortcut Space (WidgetShortcut) -> `_doi_nhanh` -> `du_thao.doi_y_kien_nhanh` (vòng `VONG_Y_KIEN`: chua -> dong_y ->
    khong_dong_y -> y_kien_khac -> chua; giữ dòng chọn); bấm đúp: cột 4 Nội dung -> `HopNoiDung` (`cap_nhat_y_kien(noi_dung=)`), cột 2 bỏ qua (hai
    cú bấm = hai lần đổi), cột khác -> HopYKien đủ. Thẻ 3: lọc sẵn khong_dong_y / y_kien_khac, nút "Chuyển hộ sang đợt sau" + "Xuất biên bản
    đối thoại" (`du_thao.xuat_doi_thoai`: mỗi lần đối thoại một dòng). Thẻ 4: `du_thao.tong_hop_nhom` (nhóm lý do: hộ kiến nghị / đã đồng thuận
    / chưa / % ; dòng "Toàn đợt"), `xuat_y_kien` thêm trang "Theo nhóm lý do".
  - CuaSoLapPA: `tra_gia_dat_nq28(i=None, dong=None)` + nút 'Tra giá đất NQ 28…' ở hàng nhập mục 1 (`HopTraNQ28.dong` = dòng bảng giá đã chọn ->
    `BoSoan.chon_vi_tri_nq28`); `man_hinh_ho_so.HopNguonGoc` + `ONguonGoc.editorEvent` (bấm đúp ô Nguồn gốc mở hộp riêng, trả True để Qt không tạo
    khung sửa tràn - tránh vỡ chiều cao dòng; chỉ xem thì không mở; gõ phím vẫn sửa trong ô). Ctrl+←/→ đã có từ 0.9.72. Test `tests/test_yeu_cau_0975.py`.
- 0.9.76 (người dùng 13/10/2026, Mục IV QĐ 18/2026 - đặc tả `phuong_an_tich_hop_du_thao_va_y_kien_dan.txt` có ma trận 16 bước) Nhóm 5 - 6. Tên file /
  lớp trong yêu cầu (`man_hinh_tong_hop.py`, `KhungTongHopKinhPhi`, `man_hinh_quyet_dinh.py`, `man_hinh_chi_tra.py`, `KhungQuanLyDotTrinh`) KHÔNG tồn tại: làm
  trên `man_hinh_theo_doi.py`, `man_hinh_quan_ly.py` (`HopDotTrinh` là hộp thoại, không phải trang) và file mới `man_hinh_bao_cao.py`.
  - CẤU TRÚC TRANG (`app.py`): `TRANG` = [Danh sách hộ, Tổng hợp tiền theo phương án, Quyết định phê duyệt, Theo dõi tiến độ, Báo cáo tổng hợp…, Dự toán & khái
    toán] (hằng `TRANG_DS` … `TRANG_DU_TOAN` = 0…5; `TRANG_DU_TOAN` vẫn 5). `self.trang` (QStackedWidget) thêm trang CUỐI để giữ chỉ số cũ: 0 danh sách, 1 bảng tổng
    hợp, 2 theo dõi, 3 dự toán, 4 chào (`TRANG_CHAO`), 5 quyết định, 6 báo cáo tiến độ; `STACK_CUA_TRANG` = (0, 1, 5, 2, 6, 3) đổi chỉ số TRANG -> chỉ số stack
    (đừng nhầm hai không gian chỉ số: `mo_trang(i)` nhận chỉ số TRANG). `self.khung_trang` {chỉ số stack: khung} (bảng tổng hợp, tiến độ, quyết định, báo cáo)
    dùng chung ở `mo` / `dong_du_an` / `_sau_tai_lai` / `_khung_dang_xem`. Bỏ `THE_TONG_HOP` khỏi TRANG (nay chỉ là tên 3 thẻ trong `thong_bao`); bỏ lệnh
    `Thông tin tổng quát hộ` và lớp `KhungTongQuat`; dòng nhắc "◀ bấm Danh sách hộ… ở menu trái" trên tiêu đề trang đã BỎ ở mọi trang (`_danh_dau_trang`).
    Lệnh `Báo cáo tổng hợp…` nay mở TRANG_BAO_CAO (Excel danh sách hộ vẫn qua `bao_cao_tong_hop` / `xuat_danh_sach`, nút "Xuất danh sách đầy đủ các hộ…").
  - NGHIỆP VỤ không Qt (mỗi module có test trong `tests/test_yeu_cau_0976.py`): `thoi_han.py` (mốc thời hạn lưu `cai_dat` SO_NGAY_THAM_DINH 15 / THU_HOI_NN 60 /
    THU_HOI_PNN 120 / VAN_DONG 10 + NGAY_THONG_BAO_THU_HOI - KHÔNG gán cứng, đặc tả "zero-hardcode"; ngày dương lịch; `han_tham_dinh`, `phan_nhom_dat`: mã không
    có trong `loai_dat.LOAI_DAT` / trống -> 'khong_ro' tính như đất phi NN; `moc_thu_hoi_tat_ca`), `van_dong.py` (sổ nhật ký, quy tắc cưỡng chế, xuất Excel),
    `kinh_phi_du_an.py` (cơ cấu kinh phí + đối soát khái toán, nhớ file `.pabtdt` ở cai_dat FILE_KHAI_TOAN), `bao_cao_gpmb.py` (dashboard), `bao_cao_y_kien.py`
    (báo cáo tiếp thu ý kiến .docx dựng bằng `van_ban_trinh._p/_r/_bang/_goi_docx` rồi `dien_docx` điền chỗ trống chung với tờ trình), `du_thao.dot_niem_yet_xong` /
    `ho_niem_yet_xong`, `quan_ly.kiem_tra_xuat_dot`, `xuat_dot(..., bao_cao_y_kien=)` -> `van_ban_trinh.xuat_bo_ho_so(..., bao_cao_y_kien=)` (file
    `PA TONG\BAO_CAO_TIEP_THU_Y_KIEN.docx`, tính vào `kq['word']`).
  - SỔ NHẬT KÝ VẬN ĐỘNG: bảng `nhat_ky_van_dong` (FK ho CASCADE) KHÔNG đổi `PHIEN_BAN_CSDL` (vẫn 15; file cũ / bản cũ mở được, bộ đơn giá đóng gói không bị ghi):
    có trong `schema.sql` (dự án mới), `csdl.mo` tạo khi file có hộ (để `hoan_tac` - liệt kê bảng lúc khởi tạo - theo dõi được), `van_dong.dam_bao_bang` tạo khi
    ghi buổi đầu, `nhap_tho.xoa_trang` gọi `van_dong.xoa_het`. Quy tắc: thời điểm = buổi vận động ĐẦU TIÊN của (hộ, việc); "quá" = số ngày đã qua > hạn; việc
    'tien' áp dụng khi hộ có QĐ mà còn QĐ chưa nhận tiền, 'mat_bang' khi có QĐ mà chưa bàn giao; hết áp dụng -> 'hoan_thanh'; hộ chưa QĐ -> 'chua_ap_dung';
    hộ chưa có buổi nào KHÔNG phát sinh trạng thái. Kết quả 'dong_y' chỉ đổi chữ trong hạn - hết hạn vẫn đủ điều kiện cưỡng chế.
  - GIAO DIỆN: `KhungBangTongHop` 3 thẻ `co_cau` / `tien` / `doi_soat` (`KhungCoCau`, `KhungTongHopTien`, `KhungDoiSoat`; `doi_soat.nguon_dang_mo` do `app` gắn
    = `_khai_toan_dang_mo`), tên thẻ 2 ghi số hộ thật, tín hiệu `di_den_phe_duyet`; `KhungQuyetDinh` là trang riêng (lazy nap như `KhungTienDo`, `lb_khop`
    = `dat_trang_thai`); `KhungTienDo.COT` 15 cột - hằng `C_MOC, C_VD, C_QD, C_TONG, C_NHAN, C_NGAY, C_CHUA, C_BIEN_LAI, C_BG` (mốc thu hồi + vận động đặt ngay
    sau Địa chỉ để không phải cuộn ngang; tests dùng hằng, đừng viết số), lọc thêm `dang_vd` / `du_cuong_che` (ngoài `theo_doi.LOC_TIEN_DO`), hàng ngày thông báo
    + `HopMocThoiHan`, `HopNhatKyVanDong`; `KhungBaoCaoTienDo` (`man_hinh_bao_cao.py`, thẻ `_TheKPI`); `HopDotTrinh`: QSplitter 2 cột, `lb_han`,
    `b_niem_yet` (QToolButton + `menu_ny` dựng lại ở `aboutToShow`), `lb_kiem`, `o_bc`. Emoji KHÔNG dùng trong chữ (Win 7): tab dùng `icon_ky_hieu`.
  - CHƯA XÁC MINH văn bản gốc (chỉ theo đặc tả + lời người dùng): "Khoản 8 Mục IV QĐ 18" (chữ trên nhãn thẩm định, `thoi_han.CAN_CU_THAM_DINH`), 15 / 60 / 120 / 10
    ngày, "Điều 89" (Luật Đất đai 2024 - cưỡng chế thu hồi đất), thẩm định tính ngày dương lịch kể từ ngày trình. Điều kiện tiên quyết ban hành QĐ cưỡng chế
    (đã có QĐ thu hồi đất, đủ mốc thông báo) chỉ HIỆN ở cột "Mốc thu hồi đất" / file xuất, KHÔNG chặn.
  - Test cũ đã sửa theo cấu trúc mới: `test_theo_doi.test_bang_tong_hop_quyet_dinh_tien_do`, `test_giao_dien` (`test_bang_tong_hop_3_the_va_lien_ket_phe_duyet`
    thay `test_bam_the_bang_tong_hop_dong_bo_menu`), `test_van_ban_trinh.test_sua_dot_va_so_pa` (xuất trọn gói mặc định có báo cáo tiếp thu ý kiến).
- 0.9.77 đặc tả V10 (`BAN_BO_CUC_CHUAN_XUAT_XUONG_THUONG_MAI_PABT_2026.pdf` = `phuong_an_tich_hop_du_thao_va_y_kien_dan.txt` bản V10; so sánh ở
  `ket_qua_kiem_tra/SoSanh_DacTa_V10_0.9.77.md`; người dùng 13/10/2026). Chỉ làm phần chưa có / sai lệch, KHÔNG viết lại 4 tầng:
  - Tỷ lệ kinh phí: `kinh_phi_du_an.co_cau` gốc 100% = CỘNG bồi thường (đất + tài sản + cây + hỗ trợ + thưởng); kinh phí tổ chức = tỷ lệ % của gốc (2,5 / 3,5),
    tổng = 100 + tl (trước: tính trên tổng kinh phí -> 2,4% / 3,4%). Hiển thị `man_hinh_theo_doi._ty_le` ("2,5", "100,0", "102,5").
  - Cửa sổ chính 1024 x 680 tối thiểu (`giao_dien.TOI_THIEU_CUA_SO`, `dat_toi_thieu_cua_so`: không lớn hơn vùng làm việc màn hình), kích thước thường
    1200 x 740 canh giữa (`kich_thuoc_thuong`; `hien_cua_so` đặt rồi showMaximized; `ThanhTieuDe._ve_kich_thuoc_thuong` khi Thu về mà kích thước thường ~ cả màn hình).
  - CỬA SỔ CON (`giao_dien.chuan_hoa_cua_so_con`, gọi từ bộ lọc sự kiện toàn ứng dụng `_BoToMau` ở sự kiện POLISH - trước khi hiện, đổi cờ không chớp): mọi
    QDialog của gói `pabt` (`la_cua_so_con_pabt`; QMessageBox / QFileDialog của Qt không đụng) có Thu nhỏ + Phóng to + Đóng, bỏ nút "?", tay nắm co giãn;
    hộp cố định kích thước (min = max) giữ nguyên. Kích thước nhớ ở QSettings('PABT','PABT') khóa `cua_so/<TênLớp>` (lưu ở sự kiện Hide; offscreen / kiểm thử
    KHÔNG đọc / ghi - `_cai_dat_cua_so()` trả None). Cờ cửa sổ PySide6: `~flag` làm mất bit chưa có tên -> tính bằng số nguyên (`int(getattr(x, 'value', x))`).
  - Niêm yết & Lấy ý kiến: `du_thao.xoa_dot` / `thong_tin_xoa_dot` (xóa đợt: ý kiến + đối thoại của đợt mất, hộ về danh sách chờ hoặc đợt gần nhất còn lại,
    phương án KHÔNG đổi, có nhật ký -> Hoàn tác được) + nút `b_xoa_dot`; nút `b_in_du_thao` -> `CuaSoChinh.in_xuat(ma_ho=, che_do='du_thao')`.
  - TRUNG TÂM XUẤT BẢN DUY NHẤT = `man_hinh.HopIn(che_do='du_thao'|'chinh_thuc', dot_id=)` (tiêu đề "Xuất hồ sơ & Bản in"): Dự thảo = mẫu "Dự thảo…" (chữ DỰ THẢO),
    che CCCD, chỉ phương án chi tiết + bảng tổng hợp; Chính thức = mẫu chính, che CCCD theo cài đặt dự án, trọn bộ (thêm tờ trình + `o_bc` báo cáo tiếp thu ý kiến);
    chọn theo đợt -> thư mục `<thư mục hồ sơ>/<Đợt N - k hộ>` (`quan_ly.thu_muc_cua_dot` đổi tên khi số hộ đổi, `dat_thu_muc_dot` ghi nhớ). `HopDotTrinh` KHÔNG còn
    xuất file (bỏ `o_tt/o_bth/o_ct/o_bc/o_pdf`, `xuat`): chân trang có `lb_kiem` (danh sách kiểm tra, đạt a/5) + MỘT nút `b_xuat` "Xuất bản hồ sơ đợt này →"
    -> `xuat_ban()` đặt `mo_xuat_dot` rồi accept; `app.dot_trinh` mở `in_xuat(dot_id=, che_do='chinh_thuc')`. `quan_ly.xuat_dot` giữ làm logic dùng chung.
  - Số PA mặc định 2 chữ số (`man_hinh_quan_ly.SO_CHU_SO_PA`, HopDanhSo): 01, 02, 03 (gọi từ mã không truyền `so_chu_so` vẫn không thêm số 0).
  - Sai lệch đặc tả đã ghi rõ với người dùng: PDF và txt đặt tên thẻ 3 Bảng tổng hợp khác nhau ("Đối soát dự toán Pre-F/S" giữ); ma trận nhắc "7. Trung tâm Xuất bản"
    nhưng menu trái chỉ 6 nhóm (Trung tâm Xuất bản là hộp `HopIn` mở từ nút / lệnh, không thêm nhóm); chiều cao tối thiểu 680 bị kẹp theo màn hình nhỏ (1366x768 @125%).
  - Test: `tests/test_yeu_cau_0977.py`; đã sửa `test_quan_ly`, `test_van_ban_trinh`, `test_giao_dien.test_mo_phong_to_va_khong_ep_rong`, `test_yeu_cau_0976`.
- 0.9.78 (người dùng 13/10/2026): nút "Dán danh sách tài sản… (Ctrl+Shift+V)" của `CuaSoLapPA` - NÚT ĐÃ CÓ từ 0.9.21 (`b_dan`, hàng nút đầu cửa sổ, hiện ở mọi
  thẻ), chỉ nâng cấp, KHÔNG thêm nút thứ hai ở từng `BangMuc` (trùng lệnh - `test_khong_trung_lenh`): `b_dan` = `btn_dan_ts` (QSS có bộ chọn
  `QSS_NUT_DAN_TS`: #0284C7 / hover #0369A1, cao 32, bo 6; `khong_icon` để `to_mau` không đè biểu tượng; không emoji - Win 7 - dùng `icon_ky_hieu(0xE77F)`),
  QShortcut `Ctrl+Shift+V` trong `self._phim`, `mo_dan_tai_san(cho=True, clip=None)` = đọc `QApplication.clipboard()` -> có bảng (> 5 ký tự, có xuống dòng
  / Tab, <= `CLIP_TOI_DA` 200.000) thì `dan_tai_san(chu=clip)` (HopDanTaiSan tự Phân loại khi có `chu`), không thì hộp trống; `dan_tai_san` giữ làm
  lõi (test, KhungDuToan). Thêm vào phương án / tính lại tổng: sẵn có (`sau_khi_dan_tai_san` -> `cap_nhat`). `cb_ho` tối thiểu 320 -> 200 để chữ nút
  dài không làm hàng nút rộng thêm (màn hình 1366 @125% chỉ ~1093 điểm). Test `tests/test_yeu_cau_0978.py`.
- 0.9.79 (người dùng 13/10/2026) thẻ chào đón: `TheChao` + `QSS_THE_CHAO` nằm ở `giao_dien.py` (không phải `man_hinh.py`), thẻ dựng ở `app._trang_chao`.
  Thẻ cố định `KICH_THE_CHAO` 210 x 135, bo 12px, khoảng cách 20; `TheChao(loai='moi'|'mo'|'excel')` + `MAU_THE_CHAO` (nền, viền, nền / viền khi rê chuột,
  màu icon); `dat_noi_dung(nut, phu)` xếp nút lệnh `the_chao_nut` (icon `CO_ICON_THE_CHAO` 38px TÔ MÀU THEO LOẠI, vẽ lại khi QAction đổi - Qt chép lại biểu tượng
  của lệnh) + nhãn mô tả TRONG thẻ (trong suốt với chuột); `mouseReleaseEvent` bấm cả thẻ = `nut.click()` (lệnh tắt thì không chạy). Nút GIỮ `defaultAction`
  (lệnh dùng chung với menu - đừng tự `setIcon` lên QAction: đổi biểu tượng menu; tests dùng `w.nut_chao`, `w.the_chao`). Kiểu: QSS chọn theo
  `QFrame[vai="the_chao"][loai=…]` (bộ chọn theo tên lớp Python `TheChao` Qt KHÔNG hiểu), `QToolButton#the_chao_nut` (bộ chọn #id thắng các
  `[ribbon][nhom]`), tên lệnh 14,5pt đậm #0F172A, mô tả 10,5pt #64748B. Qt làm tròn viền `1.5px` lên 2px -> ghi `2px`. Nhãn biểu tượng `QLabel#icon_moi`
  của yêu cầu không dùng (biểu tượng là của QToolButton). Test (bấm thẻ): ngắt slot thật của QAction trước khi bấm (lệnh mở hộp chọn file -> treo test).
  Test `tests/test_yeu_cau_0979.py`.
- 0.9.80 (người dùng 13/10/2026, 7 mục màn hình chào): (1) banner `tao_banner_ten` BỎ `lb_lan` / `giao_dien.dat_den_lan` / `app.lb_lan_nho` - trạng thái máy đơn / LAN
  chỉ ở `nut_tk` (thanh trạng thái); (2) thẻ chào đã làm ở 0.9.79; (3) bảng dự án gần đây nằm trong `self.ngan_gan_day` (QStackedWidget: 0 = `ds_gan_day`,
  1 = `_trang_trong_gan_day`), `_hien_trong_gan_day` gọi cuối `_nap_gan_day`; (4) cụm nút `khung_nut_gan` (Mở đã chọn, Xóa khỏi danh sách, Xóa file dự án - nút thứ ba
  yêu cầu không nêu, giữ cùng cụm cho khỏi mồ côi ở đáy) trên đầu bảng cùng hàng với tiêu đề và `o_tim_gan` (ẩn / tắt khi bảng trống); ô tìm khớp tên file + tên dự án +
  địa bàn (`_tom_tat_pabt` nay trả 3 giá trị, UserRole + 1); (5) `LENH_CAN_DU_AN` (nhóm 4, 5, 6) + `_cap_nhat_lenh_theo_du_an` gọi ở cuối `__init__`, `mo`, `dong_du_an`
  (QAction.setEnabled - dùng chung với thanh menu; Lập phương án hộ vẫn tắt khi chỉ xem); QSS `QToolButton[menu="1"]:disabled`; CHÚ Ý `QAction.trigger()` trên lệnh tắt
  không chạy gì - test cần dự án mở trước; (6) chân trang `lien_ket_chan` {huong_dan, bang_gia_dat, quy_trinh, lich_su} (`_lien_ket_icon`; `lk_huong_dan` giữ tên cũ = lịch
  sử cập nhật) - liên kết gọi lại QAction của lệnh (đừng gọi thẳng hàm), `quy_trinh_16_buoc` -> `man_hinh_quy_trinh.HopQuyTrinh` (dữ liệu `quy_trinh_qd18.BUOC`, ma trận
  đặc tả; bước 11 ghi "Xuất hồ sơ & Bản in" vì menu không có nhóm 7); (7) tên đơn vị `MAU_DON_VI_BANNER` #FCD34D, A− / A+ `QSS_NUT_ZOOM` (objectName `nut_zoom`).
  Biểu tượng chân trang / trạng thái trống dùng `icon_ky_hieu` (Segoe MDL2: Help E897, bảng giá E707, danh sách E8FD, lịch sử E81C, thư mục E8B7), KHÔNG emoji (Win 7 không có
  phông emoji; máy không có phông thì chỉ hiện chữ). QSS cục bộ bị `phong_to` nhân theo tỷ lệ (6px -> 7px ở 110%): test dùng regex. Test `tests/test_yeu_cau_0980.py`.
  BỘ TEST "TREO" (thật ra chậm bậc hai): `giao_dien.ap_dung(app)` mỗi lần gọi từng CÀI THÊM một `_BoToMau` (bộ cũ không gỡ) + đặt lại bảng kiểu toàn
  ứng dụng; test gọi trong setUp -> sau ~17 lần mọi sự kiện xử lý 17 lần, mọi widget của mọi cửa sổ tồn đọng (cửa sổ test chỉ close, không hủy: 13 cửa sổ
  cấp cao / lần) tô lại kiểu -> toàn bộ test > 25 phút. Nay `ap_dung` gọi lại không làm gì (đã có `app._bo_to_mau`); gỡ cho test = `giao_dien.bo_ap_dung(app)`
  (đừng tự removeEventFilter rồi để lại `_bo_to_mau`). 60 bài GUI: 163 s / 21 bài -> 29,6 s / 60 bài. Test `test_ap_dung_goi_lai_khong_chong_bo_loc`.
- 0.9.81 (người dùng 14/10/2026) biểu tượng mới "PABT 3D 2026" (nền xanh hoàng gia sáng hơn bản 0.9.74): thay `pabt/bieu_tuong_thiet_ke.webp` (khung squircle
  đo lại: viền ~175-850 / 1024 px như bản cũ -> `ve_bieu_tuong.KHUNG` (170, 853) giữ nguyên) rồi `tao_bieu_tuong.py` (QT_QPA_PLATFORM=windows). Yêu cầu nêu
  `pabt/tai_nguyen/PABT.ico` / `main.py` - KHÔNG có: file là `pabt/bieu_tuong.ico` (9 cỡ ⊇ 7 cỡ yêu cầu; bộ cài chép thành `PABT.ico` trong thư mục cài),
  điểm vào `chay.py` -> `app.main` (AppUserModelID đặt trước QApplication từ 0.9.74). MỚI: lối tắt bộ cài mang `System.AppUserModel.ID` (`cai_dat.ps1`
  `$APP_ID` - PHẢI trùng `app.APP_USER_MODEL_ID`; C# `IPropertyStore` + PKEY {9F4C2855-…}, 5, VT_LPWSTR; lỗi thì bỏ qua) - trước đây lối tắt không có ID
  -> ghim taskbar có thể tách nút / mất biểu tượng. Đã thử thật: PowerShell x64 + x86 đọc lại đúng ID, biên dịch được bằng csc .NET 2.0 (Windows 7).
  Test `test_giao_dien.test_app_user_model_id` (so `$APP_ID`), `test_bieu_tuong_duy_nhat_co_vien` (nền: xanh dương chiếm ưu thế, không còn "navy đậm").
  Dán danh sách tài sản (cùng `phan_loai_tai_san.doc_danh_sach` cho CuaSoLapPA và KhungDuToan): dòng gõ tay "Tên ␣ ĐVT ␣ Số lượng [␣ Tỷ lệ %]" ->
  `_tach_dau_cach` đọc TỪ CUỐI (ô có % = tỷ lệ; các ô `_RE_O_PHEP_TINH` liền nhau ở cuối = số lượng, ghép lại "4 x 5" -> "4x5"; 1-2 ô ngay trước khớp
  `re_dvt` = ĐVT; còn lại = tên); không có ĐVT trước số -> kiểu cũ "Tên SL ĐVT", không thì cả dòng là tên ("Nhà cấp 4" KHÔNG thành SL 4). Số lượng phép
  tính -> `_tinh_so_luong` (tien.tinh_cong_thuc, hiện "20", `cong_thuc` ở chú thích ô); ô Excel là phép tính cũng nhận (`_la_so_hoac_phep_tinh`: phải bắt
  đầu bằng số / "(" / "=" - "B40", "D110" không phải). Chữ mẫu `man_hinh_phan_loai.VI_DU` theo quy tắc mới (trước đây chữ mẫu ghi "Nhà… m2 45" nhưng gõ
  y như vậy thì cả dòng thành tên). ĐVT lưu theo bộ đơn giá (m2 -> m²). Test `tests/test_yeu_cau_0981.py`.
- 0.9.82 (người dùng 14/10/2026; rà soát đặc tả V10 5 trụ cột - báo cáo `ket_qua_kiem_tra/RaSoat_DacTa_V10_0.9.82.md`):
  - MỘT BỘ MẪU IN: chữ DỰ THẢO do CHẾ ĐỘ PHÁT HÀNH quyết định, không do tên file mẫu. `in_an.lap_chi_tiet / lap_bang_tong_hop / xem_truoc(du_thao=)`,
    `van_ban_trinh.xuat_bo_ho_so(du_thao=)` (HopIn truyền `che_do() == 'du_thao'`; None = theo tên mẫu `la_mau_du_thao` như cũ - xuat_hang_loat / Dự án mới):
    `ap_che_do_du_thao` -> dự thảo `dat_dau_du_thao` (mẫu có chữ DỰ THẢO -> giữ; chưa có -> "(DỰ THẢO)" dòng dưới "Số:" chi tiết / cuối tiêu đề "BẢNG TỔNG HỢP")
    + để trống số / ngày PA; chính thức `_an_du_thao`. `HopIn._chon_mau_theo`: cả hai chế độ "Mẫu chính" (mẫu riêng vẫn chọn tay). Lỗi cũ: chế độ Dự thảo tìm
    mục bắt đầu "Dự thảo" - mẫu riêng tên không dấu, mẫu IN_CHITIET_DT nằm ở thư mục cài còn máy đã sửa mẫu chính ở %APPDATA% -> "Chưa có mẫu Dự thảo"; mẫu
    chính có sẵn dòng DỰ THẢO thì bị xóa vì tên file không phải dự thảo.
  - `giao_dien.loc_khi_ngung_go(o, ham)`: ô tìm QLineEdit có sẵn (đơn giá, cây, chọn hộ in, giá đất, theo dõi…) - có con trỏ thì chờ 200 ms, setText bằng mã thì
    lọc ngay (test không phải chờ); kính lúp (0xE721) + nút xóa; `OTimKiemThongMinh` cũng có kính lúp. `thanh_tieu_de.CAO` 36 -> 38, `CAO_BANNER` 60 -> 48.
  - ĐÃ ĐO, KHÔNG LÀM (giữ quyết định cũ): WAL / synchronous NORMAL (file trên Google Drive / thư mục mạng; DELETE + FULL an toàn mất điện), cache_size 64 MB
    (5.000 hộ: -4%, nhiễu; bản 32-bit thiếu bộ nhớ), chỉ mục ho(dot_id) (0,3 -> 0,0 ms), WA_DeleteOnClose hàng loạt (đã có `don_hop_da_dong`, quét giao diện
    0 hộp rò rỉ), emoji trên chữ nút (Win 7). Chuyển trang đã nạp ~70 ms ở 125% (Python ~2 ms, còn lại Qt dựng bố cục / vẽ) - trang vẫn giữ trong RAM.
  - Test `tests/test_yeu_cau_0982.py`; sửa `test_yeu_cau_0977` (chế độ Dự thảo dùng Mẫu chính).
- 0.9.83 (người dùng 14/10/2026, ảnh Format Cells + bảng tính dính viền) bản in `in_an`: ô bảng mục III (cột 1-8, cả hàng tiêu đề) và
  ô dữ liệu bảng tổng hợp (cột 1-25 + dòng tổng / kinh phí) `_can_giua_doc` (vertical center + wrap, giữ căn ngang mẫu - đặt ở dòng mẫu
  trước `_chep_kieu_dong`). Chiều cao `cao_dong_bang(so_dong, co)` = max(24, số dòng x `dong_chu_bang(co)` + 8); `dong_chu_bang` =
  max(16,5 x co/14 (yêu cầu), 1,3 x co) - ĐO Excel AutoFit ở màn hình 125%: Times New Roman 12/14/16/20 = 15,6/18/21/25,2 pt mỗi dòng,
  16,5 chỉ đúng màn hình 100% (ô gộp bảng tổng hợp bị cắt dòng cuối - đã xuất PDF thử). Số dòng ĐO bằng `_ngat` (`so_dong_o`), không
  ước theo ký tự (`_uoc_cao` cũ thiếu dòng). Hàng tiêu đề cột `CAO_TIEU_DE_BANG` 28 pt (tiêu đề nhiều dòng cao theo chữ - mẫu có
  "Thành tiền\n(đồng)"). VBS PDF: AutoFit + 8, không thấp hơn chiều cao phần mềm đặt (AutoFit bỏ qua ô gộp C:F cách tính), tối thiểu 24.
  Nguồn gốc: `CAO_DOAN_TOI_DA` 350 pt, `_chia_doan_van` cắt CHỮ ở chỗ hết câu / đoạn muộn nhất (tìm nhị phân, khối >= nửa) rồi ngắt dòng
  lại (cắt theo dòng đã ngắt gần như không gặp dấu chấm cuối dòng). Bảng tổng hợp: `cao_can_ho_bth` > số dòng x 409 -> thêm dòng cho hộ
  (`_doi_dong`, ô thửa cuối gộp xuống, `dong_them` dời dòng tổng), `_vua_cao_ho_bth` chia phần thiếu không vượt 409 / dòng.
  `DK_CACH` 1,6 -> 5 pt; `vua_chu` mặc định them = DK_CACH + 3 (đường kẻ dưới "Dự án" nằm trong dòng). Test `tests/test_yeu_cau_0983.py`.
  Tốc độ: đo chữ bảng tổng hợp nhớ theo (chữ, cột, phông) trong một lần lập (`nho`), `so_dong_o` vừa một dòng thì đo một lần;
  3.000 hộ 4,9-5,2 s (0.9.82) -> 5,3-5,6 s.
- 0.9.84 (người dùng 14/10/2026) xem trước A4 trong cửa sổ: `pabt/xem_truoc_tai_lieu.py` `KhungXemTruocTaiLieu` (thanh công cụ 3 cụm
  trong XepDong: + / − / Vừa trang | Trang ◀ k / N ▶ | In nhanh; QPdfView MultiPage zoom Custom - FitInView của Qt chỉ vừa bề ngang, vừa
  trang tự tính `_he_so_vua`; không có QtPdfWidgets -> `_TrangAnh` vẽ trang bằng QPdfDocument + bóng đổ; Qt5 không QtPdf -> báo + mở
  ngoài). `yeu_cau(khoa, tao_xlsx, ten)`: `tao_xlsx(thu_muc)` (lap_chi_tiet, luồng giao diện) rồi `chuyen_pdf` (in_an.chay_excel) ở
  threading.Thread + QTimer `_kiem_nen`; chỉ giữ yêu cầu MỚI NHẤT, chờ ngừng bấm CHO_MS, nhớ theo khóa (`xoa_nho`). PDF nạp từ BỘ NHỚ
  (QBuffer): `doc.load(đường dẫn)` giữ khóa file sau `close()` -> thư mục tạm không xóa được. Thư mục `%TEMP%\pabt_preview\<pid>_<n>`
  xóa ở `don_dep` (HopIn.done, CuaSoLapPA.done / closeEvent), khi khung bị hủy (tab hộ deleteLater), atexit, `don_thu_muc_cu` (> 12 giờ).
  Offscreen KHÔNG mở Excel (`dung_duoc_excel`; PABT_XEM_TRUOC_EXCEL=1 để cho) - test thay `chuyen_pdf` bằng chép PDF giả lập.
  `in_an.lap_chi_tiet(pa=, che_cccd=)` / `dong_chi_tiet(pa=)` / `_thong_tin_ho(che=)`: phương án trong bộ nhớ (BoSoan.pa), che CCCD theo ô
  chưa lưu. HopIn: QSplitter (trái QScrollArea tùy chọn - không ép hộp rộng hơn màn hình; phải khung min 520), 50/50 tới khi người dùng
  kéo (`_da_keo`), `xem_dong` (currentCellChanged / cellClicked), khóa `khoa_xem_truoc` (hộ, dự thảo, mẫu, che CCCD); BỎ nút "Xem trước
  bản in…" (mở file ngoài) - `xem_truoc()` nay xem trong khung. CuaSoLapPA: `btn_toggle_preview` (checkable, QSS_NUT_XEM_TRUOC navy /
  #2563EB, icon View 0xE890 - không emoji), QShortcut F4 trong `_phim`, `bat_tat_xem_truoc`, `lam_moi_xem_truoc` (pa=bo.pa, khóa None),
  `cap_nhat` hẹn `CHO_XEM_SAU_SUA_MS`; màn hình hẹp hạ tối thiểu khung (`_vua_xem_truoc`, >= RONG_XEM_TOI_THIEU 320). Hàng trên cùng
  `thanh_tren` = XepDong 3 khối: tối thiểu 1.419 (một hàng cứng, trước 0.9.84) -> 1.010 điểm (Windows 125%). `rut_gon.GIU_MODULE` +
  'PdfWidgets', PABT.spec hiddenimports PySide6.QtPdfWidgets (dựng lại bộ cài mới có QPdfView). Đo: Excel lập 1 bản 1,5 - 1,9 s.
  Test `tests/test_yeu_cau_0984.py`.
- 0.9.85 hồ sơ địa phương + gói mẫu (người dùng 14/10/2026 yêu cầu "Configurable Rules & Template Engine" với file mới vn_filters.py /
  template_engine.py / updater.py, %APPDATA%\PABT_Enterprise - người dùng CHỌN "tích hợp vào hệ thống cũ", không viết động cơ in thứ
  hai; chỉ đổi nguồn gốc đất canh TRÊN; GIỮ kinh phí theo loại dự án QĐ 08/2025, MỘT bộ mẫu (0.9.82), %APPDATA%\PABT):
  - `pabt/pabt_profile.json` (mặc định Đồng Nai, đóng gói: PABT.spec / dung_exe38 DU_LIEU / cap_nhat.DU_LIEU) + `pabt/dia_phuong.py`
    (`doc` trộn sâu file máy `<thư mục máy>\pabt_profile.json` lên mặc định, nhớ theo mtime; `kiem_tra` -> danh sách lỗi tiếng Việt;
    file máy sai -> `loi()` + dùng mặc định, app.main báo; `lay('a.b')`, `ty_le_kinh_phi`, `phan_bo_kinh_phi`, `cot_mau`, `ghi_may`,
    `dang_ky(ham)` / `nap_lai()`). Module đọc lúc nạp ĐĂNG KÝ để cập nhật biến module: to_chuc (TEN, TRUC_THUOC, DIA_CHI, VAI_TRO,
    MAC_DINH - TAC_GIA giữ mã), lap_pa (LOAI_KINH_PHI, CAN_CU_KINH_PHI), thoi_han (MOC mặc định + căn cứ, CAN_CU_THAM_DINH), du_thao
    (SO_NGAY_NIEM_YET / DOI_THOAI). Nơi dùng đọc thuộc tính module LÚC GỌI - đừng `from .to_chuc import TEN` ở cấp module (mất giá trị
    mới). van_ban_trinh `_noi_dung_to_trinh` căn cứ chung = `can_cu_phap_ly.to_trinh` (mặc định byte giống hệt 0.9.82 - đã so).
  - in_an: `_cot_ct()` / `TRUONG_CT` (cột bảng chi tiết, cột loại dòng, chữ "STT"), `lap_bang_tong_hop` cột `K = cot_mau`, dòng đầu,
    `cot_cong` (G..M, P..V - trước đây cộng cả N vị trí), `cot_cuoi`, làm tròn `lam_tron_den`, phân bổ: dòng có "%" dưới dòng kinh phí
    thứ j lấy `phan_bo[j]`, THAY số % trong chữ mẫu cho khớp công thức. `_can_nguon_goc()` (mặc định justify / top). `lap_chi_tiet`:
    che_cccd None + dự thảo -> che theo `ban_in.che_cccd_ban_du_thao`. `cao_can_ho_bth` / `_vua_cao_ho_bth(cot_ho=, cot_thua=)`.
    `tien.tien_bang_chu(x, cham=True)` -> "… đồng." (mặc định không chấm - nơi gọi cũ tự thêm).
  - `pabt/goi_mau.py` gói `.pabtcfg` (zip: goi_mau.json danh sách + SHA-256, pabt_profile.json đầy đủ, mau_in/<mẫu .xlsx/.docx/.xml>):
    `tao_goi`, `doc_goi` (an_toan.kiem_tra_zip / kiem_tra_xml, chỉ file khai báo, tên an toàn, không macro vbaProject.bin, hồ sơ hợp lệ -
    kiểm XONG mới ghi), `cai` (sao lưu `<thư mục máy>\sao_luu_mau\<giờ>`, giữ 10; ghi tmp + os.replace; nap_lai), `thu_muc_mau_cai`
    (bản đóng gói = in_an.thu_muc_mau_ghi; mã nguồn / PABT_THU_MUC_MAY = `<thư mục máy>\mau_in` - KHÔNG ghi đè mau_in của repo).
    App: lệnh 'Xuất gói mẫu in & cấu hình…' / 'Nhập gói mẫu in & cấu hình…' (CHỈ menu Công cụ), app.main nhận `.pabtcfg` (chay.py),
    cai_dat.ps1 HKCU `.pabtcfg` -> PABT.MauIn, go_cai_dat.ps1 gỡ. tu-kiem bước "Hồ sơ địa phương, gói mẫu in".
  - mau_in\ có `MAU PA CHI TIET 1.pdf` (phương án THẬT - tên người ký, dự án): PABT.spec / dung_exe38 nay chỉ đóng `mau_in\*.xlsx|*.xml`.
  - CHƯA làm (so với PDF phương án thật): gộp ô Ghi chú các dòng đất cùng nội dung, nhãn "Tổ chức:" thay "Họ và tên:" khi chủ sử dụng là
    tổ chức, tiêu đề "II. Thông tin vị trí, nguồn gốc đất". Test `tests/test_yeu_cau_0985.py`.
- 0.9.86 Cụm 1 + 2 (người dùng 14/10/2026 - đặc tả "PABT Enterprise" muốn cây pabt_app/ mới + smart_clipboard / bulk_importer /
  rule_checker / audit_trail; đã hỏi: KHÔNG tái cấu trúc, làm từng cụm trong pabt/):
  - `pabt/kiem_toan.py` nhật ký kiểm toán: bảng `audit_logs` (tên người dùng chọn) KHÔNG đổi PHIEN_BAN_CSDL - schema.sql (file mới) +
    csdl.mo tạo khi file có hộ và không chỉ xem; 2 trigger LƯU TRONG FILE chặn UPDATE / DELETE (RAISE ABORT) - đừng viết mã xóa / sửa
    bảng này; `hoan_tac.BO_QUA` có 'audit_logs'. Ghi vết: TRIGGER TẠM (`gan(con)` trong app.mo sau HoanTac / DauVetHo; người / máy ở
    bảng tạm `_kt_phien` - `dat_phien` sau đăng nhập LAN) trên ho, thua (thêm / sửa từng trường THEO_DOI / xóa), gia_dat, dm_taisan,
    dm_hotro (chỉ sửa - nạp cả bộ đơn giá là thay hàng loạt). Phương án: BoSoan.luu xóa + chèn lại -> `ghi_thay_doi_pa` so `_pa_goc` với
    bản lưu (mục 1 ghép theo (thửa, loại đất), mục 2-4 theo mã / tên; dòng cùng khóa theo thứ tự), không ghi khi tu_dong. Kết nối riêng
    (Dự án mới, nhập Excel, nhập chi tiết vào file khác) không gắn trigger = số liệu gốc. Đo 3.000 hộ: UPDATE theo dõi 11 -> 40 ms.
    `csdl.nguoi_dung()` (dùng chung với ghi_nhat_ky). Màn hình `man_hinh_kiem_toan.HopKiemToan` (lệnh 'Nhật ký kiểm toán…' menu Dữ liệu
    + chuột phải, LENH_CAN_DU_AN), `kiem_toan.xuat_excel`.
  - Bác sĩ hồ sơ: `kiem_loi.BAC_SI` nhóm mới - DT mục 1 > DT thu hồi (LỖI, thay cảnh báo "khác" của kiem_tra_pa cho thửa đó), tỷ lệ mục
    1 / 2 / 3 / vật nuôi > `quy_tac_kiem_tra.ty_le_toi_da_tai_san` (mục 4 hỗ trợ không xét), nhân khẩu (thiếu khi có MA_ON_DINH /
    MA_THEO_NK; dòng ổn định khác nhân khẩu; > `nhan_khau_canh_bao`), hạn mức đất ở `han_muc_dat_o_m2` theo cap_dia_ban (mặc định null =
    không kiểm - CHƯA có số liệu hạn mức của tỉnh, người dùng tự điền). Trùng CCCD đã có từ trước (nhóm Thông tin hộ).
  - Cụm 1: dán danh sách tài sản đã có (phan_loai_tai_san - 500 dòng 0,13 s). Nhập hàng loạt: `csdl.tao_moi_tam` đặt synchronous OFF +
    journal MEMORY (file tạm, fsync + os.replace ở hoan_tat_tao_moi); `nhap_excel.chuan_hoa` lru_cache. 20.000 dòng / 10.000 hộ 3,1 ->
    2,8 s - ~90% là openpyxl đọc xlsx (giới hạn thư viện). Test `tests/test_yeu_cau_0986.py`.
- 0.9.87 (người dùng 14/10/2026 + `master_prompt_pabt_0987.md`; gói `PABT_BoCongCu_TuDong_0.9.87.zip` người dùng giải nén vào dự án
  đã GHI ĐÈ `pabt/__init__.py` thành tệp 2 dòng (mất tai_nguyen / _qt5_lam_qt6) - khôi phục từ gói .pabtcn 0.9.82; mã trong zip giả
  định sai lược đồ (ho.ten / sdt / ma_ho TEXT) nên VIẾT LẠI, không dùng; TU_DONG_NANG_CAP_0987.py / .bat (chèn import tên không tồn tại
  vào in_an / csdl) đã đưa vào Thùng rác - thư mục `PABT_BoCongCu_TuDong_0.9.87\` vẫn còn bản gốc, ĐỪNG chạy):
  - CSDL v16 (`_NANG_CAP[15]` = "@bang_phu_v16" -> `csdl._tao_bang_phu`, CHỈ file có hộ): nhat_ky_van_dong, audit_logs (+ 2 trigger
    chặn sửa / xóa, tên `audit_logs_khong_sua/_xoa` giữ như 0.9.86), thua_ban_do, anh_hien_trang, chỉ mục ix_ctdat_thua; schema.sql
    có đủ. File v16 tạo khi chưa có hộ: csdl.mo tạo bảng phụ khi đã có hộ (dấu hiệu: thiếu anh_hien_trang). `bo_don_gia.sqlite`
    nâng v16 bằng `tao_bo_don_gia.py --chuan-hoa 2026.10.12` (không bảng phụ). Bản ≤ 0.9.86 KHÔNG mở được file v16 (báo "mới hơn").
    `csdl.mo` lỗi giữa chừng -> đóng kết nối (`_mo_tiep`; trước đây file bị giữ khóa tới khi Python dọn rác).
  - Cấu hình nghiệp vụ: `man_hinh_cau_hinh.HopCauHinhNghiepVu` (Cài đặt) ghi `dia_phuong.luu_cau_hinh` (chỉ phần khác mặc định),
    `khoi_phuc_mac_dinh`; `quy_trinh_qd18.sla_buoc` / `MOC_CUA_BUOC`. "Xôi đỗ" -> "thửa chưa bàn giao mặt bằng (còn vướng mắc)".
  - CAD: `ban_do_cad.py` (ezdxf, nạp trong hàm; hình học thuần Python: diện tích, giao với ranh thu hồi Sutherland-Hodgman + tam
    giác hóa; `boc_nhan` nhãn "12\n245,6\nONT"; nhãn nhiều dòng là MTEXT), `man_hinh_ban_do.HopNhapCad` / `HopBanDo` (QGraphicsView,
    `view.tim`, bấm thửa -> mo_ho). Lệnh 'Bản đồ thửa đất' (menu trái nhóm 4), 'Nhập bản vẽ CAD (.dxf)…' (Dữ liệu). requirements:
    ezdxf 1.4.4 (Py3.14) / 1.1.4 (Py3.8); PABT.spec / dung_exe38 gom module con + dữ liệu ezdxf; tu-kiem bước "Bản vẽ CAD (.dxf)".
  - OCR giấy tờ: `ocr_ho_so.boc_tach` (GCN / biên bản: họ tên, CCCD, địa chỉ, thửa, dòng tài sản) + `man_hinh_ocr.HopQuetGiayTo`
    (cửa sổ lập PA `quet_giay_to`, KhungDuToan). `ocr.py`: Qt5 đọc từng trang (`_anh_trang_pypdf` generator), ảnh chuyển xám TRƯỚC
    khi phóng, file tạm ở thư mục tạm (trước đây `_xl.png` ghi cạnh ảnh của người dùng), không xoay đè ảnh gốc.
  - Bản in: `ho_so.la_to_chuc` (tên BẮT ĐẦU bằng loại tổ chức / có TNHH, cổ phần; không dùng từ trùng họ người: "trường" phải kèm
    cấp học, không có "đinh") -> `in_an.dat_nhan_chu_su_dung` ("Tổ chức:"); `in_an.gop_ghi_chu_dat` (mục 1, dòng 'I' liền nhau cùng
    ghi chú, `_gop_o`); `chuan_tieu_de_muc_ii` -> `TIEU_DE_MUC_II`. Đệm mẫu `in_an.nap_mau_bytes` / `mo_mau` (bytes theo mtime_ns +
    cỡ, mỗi hộ load_workbook(BytesIO) - workbook độc lập), `xoa_bo_nho_mau` ở nap_mau_in / goi_mau.cai.
  - PDF dự phòng `pdf_du_phong.py`: file bản in .xlsx đã điền -> HTML (rộng cột theo % SỐ NGUYÊN - Qt bỏ qua số lẻ; hàng định cỡ cao 0
    vì phần đầu mẫu toàn ô gộp; viền theo từng cạnh px; định dạng số Excel `_so_vn` có điều kiện "[=0]0;#,##0.0#"; tỷ lệ in / vừa bề
    ngang -> `he_so` nhân cỡ chữ, cao dòng; khổ A3/A4) -> QTextDocument.print_ ra QPdfWriter, khổ trang đặt theo pt x 96/72. Luồng
    giao diện. `KhungXemTruocTaiLieu._du_phong` khi `dung_duoc_excel()` báo lý do hoặc Excel lỗi -> nhãn `lb_gan_dung`. Offscreen không
    có phông (ô vuông): xem bằng QT_QPA_PLATFORM=windows.
  - Chẩn đoán: `chua_benh_csdl.py` (không Qt: kiem_tra_tep_pabt chỉ đọc, sua_tep_pabt - sao lưu `SaoLuu_SuaLoi`, gỡ khóa HẾT HẠN
    (khóa còn hiệu lực -> LoiSuaTep), REINDEX + VACUUM; trang hỏng -> `_cuu_du_lieu` chép TỪNG BẢNG (lược đồ trước, đọc xuôi rồi ngược
    quanh trang hỏng; iterdump dừng ở lỗi đầu tiên làm mất các bảng sau), an_danh_du_an (backup API, bỏ trigger trên bản sao, xóa /
    thay chữ cá nhân giữ độ dài, xóa tho_nhap / nhat_ky / audit_logs / anh_hien_trang), dong_goi_chan_doan, kiem_tra_moi_truong,
    thong_tin_may), `man_hinh_chan_doan.HopChanDoanHeThong(file_pabt, dong_du_an, mo_lai)` (lệnh Trợ giúp, sửa file đang mở: đóng
    -> sửa -> mở lại), `xuat_goi_chan_doan`; `giao_dien.hop_ket_qua(nut_them=[(chữ, hàm(hộp))])` - hộp lỗi của cai_bat_loi có nút gói.
  - Phiếu kiểm đếm: `phieu_kiem_dem.py` (HTML một file, JSON nhúng chống "</script>", localStorage; nhập .json qua BoPhanLoai +
    `nhap_tai_san.them_dong_tho` / `them_mot(('nhom', tên))` cho số đo cây, BoSoan.luu mỗi hộ; ảnh -> anh_hien_trang theo CCCD / họ
    tên / HO<stt>), `man_hinh_kiem_dem.HopKiemDem`; lệnh 'Phiếu kiểm đếm thực địa…' (Công cụ, LENH_CAN_DU_AN).
  - Kiểm tra tĩnh `tao_ban_do_ma.py` (viết lại; ruff F811/F841/F821/F401/E722 + thiếu __future__, import vòng cấp module, `from .X import
    TÊN` của biến dia_phuong.dang_ky, mã chết theo tên (bỏ qua phương thức Qt / HTMLParser ghi đè, hàm có decorator, `GIU_LAI`)) ->
    BAN_DO_MA.md, mã thoát 1 khi còn cảnh báo; test đòi 0. Đã gỡ 7 hàm chết + import thừa (ruff --fix).
  - Tốc độ: `pdf_bang._nho` (PdfReader / layout / chữ ký số theo đường dẫn + mtime_ns + cỡ, 4 file) - đọc lại QĐ 300 hộ 10,6 -> 0,8 s;
    `quan_ly.doc_quyet_dinh` tên ≥ 2 từ tính trước (`ten_nhieu_tu`; 8 triệu str.split mỗi lần đọc); `nhap_don_gia._doc_docx` iterparse
    theo hàng bảng cấp ngoài (11,8 MB XML: đỉnh RAM 152 -> 26 MB, kết quả giống hệt); `lap_bang_tong_hop` đọc phương án một lần
    (`ket_qua_ho(con, tat_ca)`); `OTimChon._hien` không dựng lại khi kết quả lọc không đổi; `nhap_chi_tiet.ghi(bao_tien_do=)` mỗi
    `BAO_MOI` hộ + `DaDung` (app `_ghi_chi_tiet_co_tien_do`, Dừng = hoàn tác cả lô); `may_chu.ds_du_an` stat một lần. Test
    `tests/test_yeu_cau_0987.py`.
- 0.9.90 biểu tượng (người dùng 15/10/2026): ảnh thiết kế mới `pabt/bieu_tuong_thiet_ke.webp` 2000 px (ô vuông xanh viền
  vàng, lưới địa chính, nhịp cầu, sách "Luật Đất đai 2024", chữ PABT) -> `tao_bieu_tuong.py` (tach_nen, như 0.9.87) -> png 512 + ico 9 cỡ.
  Exe / lối tắt / bộ cài chỉ đổi khi dựng lại bộ cài (PyInstaller --clean); gói .pabtcn chỉ đổi biểu tượng trong phần mềm.
- 0.9.93 dán tài sản viết tự nhiên (người dùng 15/10/2026): `pabt/hieu_tai_san.py` (không Qt) dùng chung cho hộp "Dán danh sách
  tài sản" (phương án hộ + Khái toán) và nhập Phiếu kiểm đếm. `tach_dong` ("Xoài: 16 cây, 17 năm tuổi", "Tràm: 1453 cây, đường kính
  28cm", "Tràm cây 1500 d28", "Nhà tạm: 46m2", "Ao nuôi cá ghép: 1,5ha, 1 năm 1 vụ") -> tên, ĐVT, số lượng, so_do + kieu dk / cv,
  tuoi, tỷ lệ, ghi chú; chỉ dùng khi `la_dong_tu_nhien` (có ":" / số dính đơn vị / đường kính, chu vi, tuổi, vụ) - còn lại quy tắc
  cũ "Tên ␣ ĐVT ␣ Số lượng" (`_tach_dau_cach`). "d" trơn chỉ là đường kính khi đứng SAU số lượng ("Đường ống D110" là tên); không ":"
  thì số trơn phải kèm đơn vị / số đo / tuổi ("Nhà cấp 4" không phải số lượng 4). `bo_sung(bo, dm, d, kq)` sau BoPhanLoai.phan_loai:
  "… tính bằng / tương đương <mục>" áp giá theo <mục> + ghi chú "Thực tế: …" (`ten_ap_gia`); cây có số đo -> `loai_cay_dk`
  (so CÓ DẤU trước: "tràm" -> "Keo lá tràm", không "Trám đen"; cây gỗ trước cây cảnh) -> `them_mot(..., ('nhom', loai_cay), kieu,
  so_do)`; năm tuổi -> `chon_theo_tuoi` (`khoang_tuoi`: "(Năm thứ 4,5,6)", "Năm 1", "trở đi", "Từ năm thứ a đến b", "Trên / dưới N
  năm tuổi"); `khop_theo_tu` (mọi từ của tên có trong tên mục, ít từ thừa nhất; vật nuôi luôn nền vàng - nhiều mức thời gian nuôi).
  `KetQua` thêm kieu / loai_cay / so_do / ghi_them (`ten_loai` là property sẵn có - đừng đặt trùng). HopDanTaiSan cột 9 "Quy cách".
  Test `tests/test_hieu_tai_san.py`.
- 0.9.93 cập nhật đơn giá (người dùng 15/10/2026, phương án điều chỉnh `ma_tinh_chinh_don_gia.md` - giữ CSDL): `nhap_don_gia.NHOM_VN` = 7
  CHỈ khi phân tích / chọn (nhom_theo_chu: vật nuôi, thủy sản, lồng bè, thâm canh… -> 7 trừ khi có cả cây trồng -> 3; mồ mả -> 2, di
  dời mồ mả -> 4; `_nhom_dong` ĐVT con / kg / m² mặt nước / ha/vụ / 100m3/vụ -> 7); `ap_dung` ghi nhom 7 thành dm_taisan nhom 3 +
  phân loại vật nuôi + mã VN; `_phan_loai(con, …)` lấy ĐÚNG chuỗi phân loại bộ đang dùng (`_phan_loai_dang_dung` - trước đây "2. Nhà,
  công trình xây dựng" / "3. Cây trồng, vật nuôi" lệch bộ); trả `theo_nhom`. `so_khop` nhóm 7 = dòng nhóm 3 có mã VN / phân loại vật
  nuôi. `TIEN_TO`, `dong_tu_chu` (chữ dán: Tab -> ô; không Tab -> một ô, `ocr.sua_so`). `cap_nhat_web` nhận nhóm 7. HopNhapDonGia:
  `nhom_uu_tien` (thẻ đang xem, dùng khi văn bản không ghi nhóm), bộ chọn 5 mục, cột Mã "TS… (mới)", sửa Tên / ĐVT / Đơn giá mọi dòng
  (`C_TEN / C_DVT / C_GIA`). HopBoDonGia: `THE_NHOM_CAP_NHAT` {0: 2, 1: 3, 2: 7, 3: 4}, `dan_don_gia` (menu + QShortcut Ctrl+Shift+V
  ngữ cảnh WidgetWithChildrenShortcut - trùng phím Dán tài sản của CuaSoLapPA khi cùng cửa sổ; Clipboard chỉ có ảnh -> OCR),
  `xu_ly_pdf_scan` (cài gói tiếng Việt / dán / chọn file khác), `sau_cap_nhat` (nạp lại + chuyển thẻ nhóm thay đổi nhiều nhất).
  OCR (`ocr.py`): Windows OCR (`Windows.Media.Ocr` qua powershell.exe 5.1 -Command, mã `_PS_OCR`; trả từ + toạ độ -> `gom_dong` theo
  hàng ngang; ~0,7 s / trang) ưu tiên khi có tiếng Việt, rồi Tesseract (`may_doc`, PABT_OCR = windows / tesseract để ép);
  `trang_thai_windows` (san_sang / thieu_tieng_viet / khong_co, nhớ trong tiến trình), `cai_tieng_viet_windows` (Add-WindowsCapability
  Language.OCR~~~vi-VN qua RunAs - CHỈ khi người dùng bấm; KHÔNG chạy trên máy phát triển: thay đổi hệ thống), `sua_so` ("3.500.ooo").
  Máy phát triển (Windows 11 tiếng Anh) chỉ có OCR en-US: đường Windows OCR kiểm bằng en-US (`test_windows_ocr_that` - ảnh vẽ ở tiến
  trình QT_QPA_PLATFORM=windows: offscreen không có phông). Test `tests/test_don_gia_15_10.py`.
- 0.9.93 bản in chi tiết (người dùng 15/10/2026): nguồn gốc đất `in_an.cao_doan_van` (khoảng dòng `dong_chu_bang`, đệm
  `DEM_DOAN_VAN` 3 pt - không đệm 8 pt / tối thiểu 24 pt như ô bảng), dòng thừa của vùng gộp mẫu A13:H15 ẨN (trước: 4 pt mỗi dòng)
  -> hết khoảng hở tới "III."; hỗ trợ đào tạo theo thửa: dòng tên chính sách chỉ tên + căn cứ (ĐVT / SL / thành tiền ở dòng "-"
  thửa - nhap_chi_tiet._gop_dong_con vẫn lấy số ở dòng con); dòng IV `_nhan_dam(o, NHAN_TDC)`: CellRichText "Tái định cư:" đậm +
  nội dung thường (openpyxl 3.1.5 cả hai venv; đọc lại cần `load_workbook(rich_text=True)` mới thấy từng khối). Xem thật: lập bằng
  QT_QPA_PLATFORM=windows (offscreen đo chữ rộng -> dòng bảng cao bất thường) rồi `in_an.chay_excel` ra PDF. Test
  `tests/test_ban_in_15_10.py`.
- 0.9.92 tên LARC + đuôi .larc (người dùng 15/10/2026): TÊN BÊN NGOÀI = LARC - lối tắt Desktop `LARC.lnk`, Start Menu / mô tả /
  Cài đặt > Ứng dụng "LARC - Bồi thường, hỗ trợ, tái định cư" (`cai_dat.ps1` `$TEN` / `$TEN_NGAN`, Publisher LARC, gỡ lối tắt tên cũ
  `$LOI_TAT_CU`), bộ cài `LARC_Setup_Universal_<ver>.exe` (FriendlyName "LARC - Cai dat"); zip `PABT_ChayNgay_*`, gói `PABT_CapNhat_*`,
  PABT.exe, thư mục cài `PABT`, khóa registry Uninstall\PABT, AppUserModelID GIỮ tên cũ. Biểu tượng lối tắt: file MANG SỐ PHIÊN BẢN
  `LARC_<ver>.ico` trong thư mục cài (`dung_bo_cai_win._ds_chuong_trinh`) - Windows giữ ảnh theo ĐƯỜNG DẪN nên PABT.ico chung mọi bản
  làm Desktop / taskbar hiện biểu tượng cũ sau khi đổi; lối tắt đã ghim (User Pinned) trỏ PABT.exe được đổi biểu tượng
  (`PabtLoiTat.DoiBieuTuong`), rồi `SHChangeNotify` (`LamMoi`). Đuôi file dự án: `csdl.DUOI_DU_AN` = ".larc", `DUOI_MO` (.larc +
  .pabt cũ), `LOC_LUU` / `LOC_MO`, `la_file_du_an`, `duoi_du_an` (lưu mới / lưu thành -> .larc; .pabt cũ giữ đuôi); máy chủ LAN liệt kê
  cả hai; bộ cài gắn .larc và .pabt; gỡ cài giữ .larc / .pabt / .pabtdt. Gọi bộ cài IExpress từ Git Bash: "/Q" bị đổi thành đường dẫn
  ("Command line option syntax error") - chạy bằng PowerShell / subprocess.
- 0.9.91 biểu tượng "3D LARC" (người dùng 15/10/2026): ảnh 1024 px nhà + chìa
  khóa vàng, chữ LARC (tên trên biểu tượng là LARC, phần mềm vẫn tên PABT). `tao_bieu_tuong.tach_nen` thêm `XAM_SAC` / `XAM_SANG`:
  bóng đổ xám trung tính nối liền mép ảnh cũng là nền (trước: vệt sáng quanh biểu tượng trên nền tối). Test `test_bieu_tuong_duy_nhat_co_vien`
  theo mẫu LARC (xanh > 40%, vàng, trắng, không mảng đỏ, mép trong suốt).
- 0.9.89 rà soát lỗi (người dùng 15/10/2026 "check lại toàn bộ mã nguồn"; thử các hàm đọc dữ liệu người gõ / dán bằng giá trị khó):
  `phan_loai_tai_san._co_the_la_ty_le` (số sau số lượng là tỷ lệ chỉ khi có % hoặc <= 500 - cột Đơn giá / Thành tiền dán từ Excel
  bỏ qua); `nhap_excel.chuan_cccd` (ô số 11 chữ số -> thêm 0 đầu; ô số 8 chữ số = CMND -> 9) dùng ở nhap_excel / nhap_tho / du_an_moi.gom
  / nhap_chi_tiet._doc_cccd; `quan_ly.chuan_ngay` năm 3 chữ số / ngoài 1900-2100 -> LoiNhap; `tien._d_chuoi_goc` chặn NaN / Infinity /
  "1_000" (Decimal nhận); `quan_ly._thu_muc_dot` tìm thư mục cũ đúng "<tên đã làm sạch> - <số> hộ" (bỏ `glob_an_toan`);
  `lap_chi_tiet` ghi chú đất gộp ô: chiều cao từng dòng theo cột khác, thiếu thì chia đều cho đủ ô gộp; `ho_so._tach_ds_ngan` bỏ
  qua gạch giữa hai số; `tien.vn_gon` làm tròn lên ngưỡng tỷ. Sửa file bằng script Python: GIỮ kiểu xuống dòng của file (git
  ls-files --eol; Path.write_text đổi LF thành CRLF). Rò rỉ kết nối: chỉ trong test (`tests/test_don_gia.py`, …), phần mềm không.
- 0.9.94 số lượng kiểu kế toán (người dùng 15/10/2026): tài sản (mục 2 nhà, công trình) "*,00", đất / cây / vật nuôi / hỗ trợ /
  khác "*,0"; số nhiều chữ số lẻ hơn hiện đủ, tối đa 4 (ha 0,0325). MỘT nguồn `tien.le_so_luong(muc)` / `dinh_dang_so_luong(muc)`
  (Excel '#,##0.00##' / '#,##0.0###') / `so_luong_vn(x, muc)` - dùng ở BoSoan.o_dat (diện tích) / o_khoan, KhungDuToan, du_toan
  xuat_excel / xuat_khai_toan, in_an.lap_chi_tiet (mục theo dòng tiêu đề 'H'), doi_chieu. Trước: khái toán '#,##0.##' in "46,".
  Trang Khái toán bỏ tiêu đề "KHÁI TOÁN KINH PHÍ…" + nút Chế độ (trùng menu trái; `mo_trang(TRANG_DU_TOAN)` chọn thẻ 0, lb_trang ẩn).
- 0.9.94 bỏ thanh tab ngang (người dùng 15/10/2026): `thanh_tab` KHÔNG xếp vào bố cục, `KhungLamViecDaTab.bar` là con của
  khung ẩn, `_hien_thanh` luôn ẩn - khung_tab chỉ còn giữ danh sách trang / hộ / bộ đơn giá / niêm yết trong RAM (Ctrl+Tab vẫn
  đi vòng). Chuyển trang: menu trái / thanh menu, Ctrl+1..6 = 6 mục TRANG (QAction có `self.addAction`). `lb_du_an` đã bỏ (tên
  dự án chỉ ở tiêu đề - xem dưới). Mở hộ mới -> đóng tab hộ khác KHÔNG có thay đổi chưa lưu (không
  còn dấu X của tab: hộ thoát bằng nút Đóng `b_dong` của CuaSoLapPA). Đo 1161 x 741: thẻ số y 141 -> 94, bảng 383 -> 290, 6 -> 8 dòng.
  Test `tests/test_bo_thanh_tab.py`. Tên dự án MỘT chỗ (người dùng 15/10/2026): `CuaSoChinh.dat_tieu_de` = "PABT - <ten> · <ten_dia_ban>
  (<file>)" (chưa mở: "PABT - " + `MO_TA_UD`; gọi cuối `_sau_tai_lai` nên sửa Thông tin dự án đổi theo), ThanhTieuDe rút "…" ở GIỮA;
  đã BỎ `lb_du_an` (dòng dưới banner), ô banner "Dự án: …" (`NutRutGon`, `RONG_O_DU_AN`, `lb_du_an_nho`) - góc phải banner chỉ phiên bản + tem.
  `_dam_bao_tab` mở trang phụ (hộ / Niêm yết / Đơn giá) ẩn `hang_the` (trước: Niêm yết hiện hai hàng thẻ số).
- 0.9.94 tên LARC (người dùng 15/10/2026 "sửa toàn bộ chữ PABT thành LARC"): chữ HIỂN THỊ = LARC - `thong_bao.TEN_UD`,
  `app.TIEU_DE_CUA_SO` ("LARC - <tên dự án> · <địa bàn> (<file>)"), hộp thông báo, máy chủ LAN, báo cáo đối chiếu, mô tả loại file
  `.pabtcn` / `.pabtcfg` (cai_dat.ps1). File phát hành: `LARC_CapNhat_<ver>.pabtcn` (tao_cap_nhat), `LARC_ChayNgay_<ver>_*.zip`,
  `LARC_CaiDat_<ver>_*.exe`, `LARC_Setup_Universal_<ver>.exe`; `phan_tich_phien_ban` tìm mốc cả LARC_CapNhat_* lẫn PABT_CapNhat_*
  (gói <= 0.9.93). GIỮ tên nội bộ: PABT.exe, thư mục cài / `%APPDATA%\PABT`, QSettings('PABT','PABT'), applicationName, khóa đăng ký
  (PABT.DuAn, Uninstall\PABT), `cap_nhat.UNG_DUNG` = 'PABT' (bản cài cũ kiểm mã này), gói pabt/, đuôi .pabt / .pabtcn / .pabtdt, thư mục
  Documents\PABT - Hồ sơ PA, "file PABT Excel" (tên mẫu Excel PABT_CHUAN.xlsm của người dùng), khóa self.lenh 'Dự thảo PABT…'.
- 0.9.94 dự án gần đây (người dùng 15/10/2026 "bảng không hiện"): NGUYÊN NHÂN là bộ test - 5 bài `test_giao_dien` gỡ hẳn
  PABT_THU_MUC_MAY trong `finally` -> các bài sau ghi file tạm vào `%APPDATA%\PABT\du_an_gan_day.json` thật, đẩy hết dự án thật ra
  (GAN_DAY_TOI_DA 8), file tạm bị xóa -> bảng trống. Bài tự đặt biến phải TRẢ LẠI giá trị của tests/__init__ (`_tra_thu_muc_may`), không
  pop. `app.ghi_gan_day` bỏ file không còn (`_con_tren_dia`: ổ / thư mục dùng chung truy cập được mà không có file; ổ mạng ngắt thì giữ).
  Nhập Excel / Dự án mới / nhập chi tiết vào file mới đều qua `mo()` -> đã ghi gần đây.
- 0.9.94 Niêm yết (`man_hinh_du_thao`): `_bang(cot, rong=, gian=)` bề rộng chuẩn + MỘT cột Stretch, `san_tieu_de(b)` (cột >= chữ tiêu đề +
  `DEM_TIEU_DE` 26, minimumSectionSize 60; gọi cuối `nap` và `showEvent`); nút `b_xuat_ny` "Xuất bảng niêm yết" trên hàng nút đợt (`_nut`
  khóa mới), thẻ không nút: bảng sát thanh thẻ; tiêu đề cột "CCCD" (dữ liệu vẫn `cccd_che`); thanh 4 thẻ QSS cục bộ padding 4px 12px, 12px
  (đo 29 px); `_The` 2 hàng (nhãn | số + chữ phụ) 45 px. Nút toàn phần mềm: QSS padding 4px 10px, bo 5px (QPushButton đo 29 px); nút
  thanh công cụ danh sách hộ min 28 / max 30 (nut_lenh mặc định 32 - menu trái giữ); thẻ số màn hình chính lề 2, cách 6, số 16px (44 px).
  `gian_cach` (nâng khoảng cách hàng ngang < 10 lên 10 khi cửa sổ hiện) bỏ qua layout có property `giu_khoang_cach` (2 hàng thẻ KPI 6 px).
  `lb_trang` (tiêu đề trang) KHÔNG hiện ở trang nào (người dùng 16/10/2026: Quyết định phê duyệt "trùng tiêu đề mục") - chữ vẫn đặt.
  Tên hộ trong ô / danh sách chọn hộ, tiêu đề hộp một hộ: KHÔNG kèm "(mã n)" (người dùng 16/10/2026) - mã hộ ở itemData / UserRole.
  Test `tests/test_yeu_cau_0994.py`.
- 0.9.95 "Ultra-Compact" (người dùng 16/10/2026, đặc tả dán trong phiên):
  - `CuaSoChinh._cap_nhat_hien_hang_the` (nối `trang.currentChanged` / `ngan_lv.currentChanged`, gọi cuối mo_trang / _dam_bao_tab /
    _tab_doi_khoa / _hien_trang_chao / ve_trang_chu / _sau_tai_lai): `hang_the` CHỈ khi có dự án + trang Danh sách hộ (không tab phụ);
    `banner_ten` CHỈ ở màn hình chào / chưa mở dự án. Đừng tự `hang_the.setVisible` ở chỗ khác. Thẻ số `TheSo` một dòng (QHBoxLayout số +
    nhãn, max 32, số 13,5px, cách 4). Menu trái: `CAO_NUT_MENU` 27, lề 4, cách 2, icon 18, chữ 12px; bề rộng `rong_mo()` = max(RONG_MENU_TRAI
    175, lệnh dài nhất + 18) <= RONG_MENU_TOI_DA 248 (đo lại ở Show / StyleChange / FontChange - `_VuaRongMenu`): "Theo dõi chi trả & Bàn
    giao" cần ~210 px ở 125% nên thực tế ~228 (175 cứng thì cắt chữ); tên nhóm `setWordWrap`.
  - CuaSoLapPA: hàng trên `thanh_tren` XepDong 4 khối (chọn hộ | Dán, Quét, Gợi ý | Lưu, Bỏ | Xem A4, In, Đóng), nút `CAO_NUT_TREN` 27,
    `cb_ho` 190-270, `b_truoc` / `b_sau` = "◀" / "▶" (chú thích Ctrl+Left / Right) - một hàng từ ~1.270 điểm (Full HD 125%), 1366 x 768
    hai hàng. `hang_dieu_huong()` = MỘT hàng đáy: `lb_tong` + `b_tro_lai` / `b_tiep_theo` (chữ theo thẻ, `_cap_nhat_dieu_huong`) - BangMuc
    KHÔNG còn nút điều hướng riêng. BangMuc: mục 1 nút dòng + "Cộng mục 1" cùng hàng chọn thửa (cb_thua >= 260), không khung viền hàng nhập,
    nút dòng `CAO_NUT_DONG` 24, lề (6, 4, 6, 4); cột `RONG_COT_GON` + `COT_GIAN` Stretch; `giao_dien.san_tieu_de(b, rieng)` (đo phông ĐẬM
    + `DEM_TIEU_DE` 30; dùng chung Niêm yết). b_dan chữ "Dán danh sách tài sản…" (phím tắt ở chú thích).
  - KhungDuToan: `h_day` = `lb_tong` (một dòng rich text, chi tiết từng mục ở chú thích) + 4 nút, cao `CAO_HANG_DAY` 34; `b_an_tt` /
    `an_thong_tin_chung` (`_than_chuan_bi`); o_dt_dat >= 105, o_gia_dat >= 115; `can_mot_hang` đặt min width nút = sizeHint + 8; so sánh:
    tô màu ô chỉ khi khái toán (kt) khác 0. KhungDuThao: `_The` một dòng (NhanRutGon nhãn | số, chữ phụ ở chú thích, max 32); nút của thẻ 2-4
    ở `tabs.cornerWidget` (`_nut_goc`, `_hien_nut_goc`); `bang_th` cột 0 >= 185 (property `the_tong_hop`).
  - `app._tom_tat_pabt` -> (số hộ, tổng, chữ tìm, tên hiển thị "Tên · Địa bàn (file)"): tổng = sum(KetQuaHo.tong) như danh sách hộ (có
    thưởng, làm tròn), nhớ ở `<thư mục máy>\tong_du_an.json` theo mtime_ns + cỡ (`ghi_tong_nho` - gọi cả khi đóng dự án / nạp màn hình chào
    với số vừa tính). 3.000 hộ: lần đầu 0,27 s, sau 0,008 s. HopDuAn 1080 x 500.
  - Quét giấy tờ (`man_hinh_ocr`): `KhungXemFile` (QScrollArea, trang xếp dọc nền #475569, `nap` / `nap_anh`, `phong_to`, `vua_khung`, `xoay`,
    `sang_trang` - kích hoạt bố cục + resize vùng trong trước khi cuộn, Ctrl + lăn, kéo) + `anh_cac_trang(files)` (QtPdf; Qt5: ảnh scan trong
    PDF qua `ocr._anh_trang_pypdf`; tối đa TRANG_TOI_DA). `ngan_trai` 0 = xem trước (mặc định), 1 = `o_chu` (nút `b_doi_xem` "Chữ OCR").
    Phải: o_nk, o_ng (nguồn gốc -> cột nguon_goc thửa thêm mới), o_tdc; `o_luu_dinh_kem` -> `luu_dinh_kem` (anh_hien_trang, khop_theo 'quet');
    `b_tron_bo` -> `nhap_tron_bo` (dien_ho_thua + dien_nhan_khau_tdc + đính kèm + dan_tai_san). Chưa làm: OCR trả ảnh trang để khỏi dựng
    PDF hai lần (xem trước dựng bằng QtPdf nhanh: 48 trang 3,9 s).
  - `ocr_ho_so`: `doc_chu` nối ô bằng TAB; `boc_tach` loại 'pa_chi_tiet' ("phương án chi tiết" / "bảng tính toán bồi thường") -> `_bang_pa`
    (`_dong_logic`: bảng III từ "STT" tới "TỔNG CỘNG", nối dòng bị ngắt, "m" + "2" của m²; `_o_dong`: có Tab theo ô, không Tab theo ĐVT;
    `_MUC_THEO_TEN` THỨ TỰ quan trọng - "Bồi thường, hỗ trợ về nhà" có "hỗ trợ", "bồi thường" có "thường"; tỷ lệ ô Excel 1 = 100%; hỗ trợ có
    câu cách tính -> chỉ tên, nhân khẩu lấy từ câu). `nhan_khau`, `nguon_goc` (`_doan_sau_tieu_de`), `tai_dinh_cu` ("Tái định cư:"), nhãn "Tổ
    chức:", `_sua_so_ocr` (O / l -> 0 / 1) + chuan_cccd. `_sau_nhan` bỏ Tab / ":" ngay sau nhãn. Thử file thật `mau_in\MAU PA CHI TIET 1.pdf`
    (KHÔNG đưa vào test): 180 thửa đúng, nguồn gốc, TĐC; họ tên trống (lớp chữ PDF đặt giá trị xa nhãn).
  - `ocr.gom_dong`: khoảng trống > `CACH_COT` 2,2 x cao chữ -> Tab. `ocr._chay`: đọc stdout / stderr bằng luồng SONG SONG - trước đây kết quả >
    ~64 KB (trang scan bảng giá) làm đầy ống, hết 180 s báo "quá lâu" (thử file người dùng "VBHN cây trồng.pdf" 48 trang: nay 0,6 s / trang).
    Máy phát triển chỉ có OCR en-US (không gói vi) - đường tiếng Việt chưa thử thật.
  Test `tests/test_yeu_cau_0995.py` (bản in chi tiết GIẢ LẬP qua in_an.lap_chi_tiet).
- 0.9.96 (người dùng 16/10/2026, 7 mục; số liệu thật "ÁP GIÁ-37 thửa.xlsx" ở thư mục dự án chỉ để thử tay - KHÔNG đưa vào test / git):
  - Chiều cao dòng bảng phương án: `giao_dien.vua_dong(b, cao_chuan=32, cao_toi_da=88)` đo chữ thật (`cao_can_dong`: QFontMetrics.boundingRect
    trên bề rộng cột - cột < 100 lấy max(160, sizeHint tiêu đề); ô trống / chữ ngắn không làm dòng cao; một dòng 32-36, nhiều dòng
    min(88, chữ + 10)); `dat_dong_gon` (verticalHeader không giãn dòng cuối, Interactive, min 30 / mặc định 32). BangMuc dùng thay
    resizeRowsToContents (dòng trống cao 60-90 px vì cột giãn / tiêu đề dài), đo lại sau 50 ms khi đổi cỡ / kéo cột (`_hen_vua`);
    `_ve_dong` một dòng = `cao_can_dong`. Theo dõi (HopHoTheoDoi) gọi `vua_dong(b, None, None)` như cũ. ChuNhieuDong: khung sửa cao theo
    chữ, >= 32, <= max(64, cao dòng). Cột: Ghi chú / Quy cách / Căn cứ giá GỌN (RONG_COT_GON), chỉ Tên / Cách tính / Vị trí giãn.
  - Nút "Quét hồ sơ…" (`b_ocr`) của CuaSoLapPA chỉ báo `man_hinh.TB_QUET_HO_SO` ("Tiện ích đang trong quá trình hoàn thiện"); mã quét
    cho lập phương án đã BỎ (HopQuetGiayTo không còn dien_nhan_khau_tdc / luu_dinh_kem / nhap_tron_bo / o_luu_dinh_kem / b_tron_bo -
    chỉ còn đích Khái toán 'du_toan').
  - Loại đất: `loai_dat.LOAI_DAT` thêm LUN, LNK, RTS (ký hiệu cũ), DHN, DCK (tên DHN / RTS chưa đối chiếu văn bản gốc); `chuan_ma_loai_dat`
    ('rdd', 'R.D.D', 'ĐGT', tên đầy đủ, 'ONT,CLN' -> mã; dùng ở ho_so.chuan_loai_dat, nhap_chi_tiet, du_an_moi.khoa_gia, BoSoan.sua_dat),
    `nhom_mac_dinh`. `BoiCanh.loai_dat` = đủ LOAI_DAT + dm_loaidat (dm ghi đè nhóm) -> "RDD không có trong danh mục" hết;
    `du_an_moi.ds_loai_dat` / `loai_dat_biet` cũng đủ. `BoSoan.them_thua`: mã không có trong danh mục vẫn GIỮ (giá 0 / nhập tay).
  - `nhap_chi_tiet`: mục 1 LUÔN tạo ct_dat cho mọi thửa (kể cả đơn giá 0 / trống; trước: chỉ khi có tiền đất, không thì ghi chú vào
    ho.phap_ly - phap_ly vẫn ghi như cũ); `tach_phuong_an` (sheet nhiều phương án nối tiếp: mỗi bảng STT một phương án, ranh = dòng quốc
    hiệu / "PHƯƠNG ÁN CHI TIẾT" / "Số:" sau TỔNG CỘNG của bảng trước; tên "<sheet> - PA <số>"), `doc_sheet(…, lech)` giữ số dòng Excel
    thật; `_thua_tu_ten` gộp khoảng trắng, `_so_hieu` ('--', '-', trống -> ''), loại đất chữ thường / "ONT, CLN". `_tim_tieu_de(hang, tu,
    den)`. File thật: một sheet -> hai phương án (37 + 142 thửa), đọc 0,13 s.
  - `nhap_tho`: `_gia_tri_luoi` dừng sau `TRONG_LIEN_TIEP` 100 dòng trống, bỏ cột trống bên phải (bề rộng = cột có chữ cuối trong
    `DONG_TIM_COT` 40 dòng đầu - sheet TỔNG 237 cột); DT thu hồi ưu tiên "… trong dự án / ranh / phạm vi" (10 điểm), loại "Tổng diện tích
    thửa", "diện tích thửa"; dòng đánh số cột cho thiếu số; ô 'NaN' / '--' = trống (`_khong_gia_tri`) -> dòng tiếp của hộ trên; tiêu đề lặp
    (>= 2 ô trùng tiêu đề); dòng chữ gộp ngang (họ tên = STT / tờ / thửa / địa chỉ) bỏ qua. File thật sheet TỔNG: 1 tổ chức / 183 thửa.
  - Nhiều thửa: `BoSoan.them_nhieu_thua(ds_ma_thua=None, bo_qua_da_co=True)`, `xoa_nhieu_dat(ds_chi_so)`; thẻ 1. Đất nút
    `b_them_tat_ca_thua` / `b_chon_nhieu_thua` -> `CuaSoLapPA.them_tat_ca_thua` / `chon_nhieu_thua` (`man_hinh.HopChonNhieuThua`: đánh dấu,
    lọc Tờ / Loại đất, Ctrl+A = đánh dấu thửa đang hiện); bảng mục 1 ExtendedSelection: `xoa_dong` xóa cả loạt, sửa ô thuộc
    `AP_NHIEU_DONG` (loại đất, vị trí, giá, K, tỷ lệ, ghi chú) / chọn vị trí NQ 28 khi đang chọn nhiều dòng -> áp cho mọi dòng chọn.
    Hàng nhập mục 1 = 3 khối XepDong (một hàng cứng ~1.480 điểm). KhungHoSo (thẻ 0): chọn nhiều thửa -> "Xóa thửa" xóa cả loạt.
  - Hồ sơ scan + hoàn tất CTBT: `pabt/ho_so_scan.py` (không Qt; đường dẫn file ở bảng `anh_hien_trang` có sẵn, `khop_theo = 'ho_so_scan'`,
    KHÔNG đổi lược đồ; `them_file` / `ds_file` / `bo_file` (không xóa file) / `dem_theo_ho`; `hoan_tat(x)` = có QĐ + đã bàn giao (nhận tiền
    hay chưa không xét), `ten_dot_theo_ho`, `ds_hoan_tat`, `xuat_excel_hoan_tat_ctbt` - CHỈ Excel). `man_hinh_ho_so_scan.py`: `NutHoSoScan`
    (menu đính kèm / mở từng file / thư mục / bỏ đính kèm) ở KhungHoSo (`nut_scan`, cạnh "+ Thêm thửa") và HopHoTheoDoi; KhungTienDo thêm
    cột `C_HOAN_TAT` "Hoàn tất CTBT (theo đợt)" + `C_SCAN` "Hồ sơ scan" (bấm đúp: một file mở luôn, nhiều -> menu `mo_nhanh`), nút "Hộ hoàn
    tất CTBT…" -> `HopHoanTatCTBT` (xem + Xuất Excel). Test `tests/test_yeu_cau_0996.py` (lớp `_Co.tearDown` gọi doCleanups TRƯỚC khi xóa
    thư mục tạm - addCleanup chạy sau tearDown, file .pabt còn mở thì Windows không xóa được).
- Sau 0.9.96 (người dùng 16/10/2026, ảnh màn hình):
  - LỖI: mở Lập phương án, sang Niêm yết, bấm lại Lập phương án vẫn thấy Niêm yết - `KhungLamViecDaTab.dam_bao` với khóa đã có và
    widget=None chỉ đổi tab ẨN (thanh tab bỏ từ 0.9.94); nay `stack_phu.setCurrentWidget(self.widget[khoa])`. Lệnh LENH_CAN_DU_AN xóa
    statusTip "Mở hoặc tạo dự án…" khi đã có dự án (trước giữ mãi trên thanh trạng thái).
  - Menu chuột phải bảng mục (`BangMuc.menu_dong(pos)`; pos None = chỉ dựng menu cho kiểm thử): thêm (mục 1: thửa / tất cả / chọn nhiều;
    mục khác: ô nhập nhanh), `CuaSoLapPA.nhan_ban_dong` (mục 1 replace DongDat id=None; khoản `bo.nhan_ban`), xóa (cả loạt), lên / xuống,
    `chep_o`; mục 1 chọn mọi dòng + Tra NQ 28, mục 2 kiểm tra DT xây dựng + tách ranh, mục 3 tính mật độ.
  - Bản in: `in_an.chuan_dong_ngay` (sau dien_so_ngay, trước _thay_cho_trong; chi tiết + tổng hợp): địa danh dòng ngày CỐ ĐỊNH = hồ sơ địa
    phương `ban_in.dia_danh_ngay` (pabt_profile.json "Trị An" - nơi đặt cơ quan, không theo xã dự án), chỗ trống -> "ngày ...... tháng .....
    năm"; `dat_nhan_chu_su_dung` tổ chức -> ẨN dòng "Số CCCD:"; `viet_hoa_du_an` "Dự án: X" -> "DỰ ÁN X" (chỉ phương án chi tiết).
  - HopIn: nút `b_xem_bth` "Xem trước bảng tổng hợp" -> `xem_truoc_bang_tong_hop` (hộ đang đánh dấu, khóa ('bth', hộ, dự thảo?, mẫu)).
  - Gói cập nhật đổi đuôi `.pabtcn` -> `.larcud` (người dùng 16/10/2026): `cap_nhat.DUOI` = '.larcud', `DUOI_NHAN` (.larcud + .pabtcn cũ -
    hộp chọn file, nhấp đúp, chay.py); bộ cài gắn cả hai đuôi, gỡ cài gỡ cả hai; tao_cap_nhat ra `LARC_CapNhat_<ver>.larcud`;
    phan_tich_phien_ban tìm cả .larcud / .pabtcn. Bản cài <= 0.9.96 chỉ lọc *.pabtcn trong hộp chọn: đổi đuôi gói thành .pabtcn để cài.
  - Bảng tổng hợp kinh phí: lề trong mỗi thẻ `man_hinh_theo_doi.LE_THE` 8 px; cột Nhóm khoản vừa chữ dài nhất (240-420 px).
  Test `tests/test_yeu_cau_1610.py`.
- Hàng nút CuaSoLapPA (người dùng 16/10/2026, sau 0.9.97): BỎ nút "Gợi ý hỗ trợ…" (`b_goi_y`; hàm `goi_y` còn cho test), chữ nút
  "Dán tài sản" (`b_dan`), "SCAN" (`b_ocr`), "Xem trước (F4)" (`btn_toggle_preview`); ô chọn hộ `RONG_O_HO` (300, 560) AdjustToContents,
  `_hien_ten_ho` (chữ hiện từ đầu tên - ô sửa được mặc định cuộn về cuối; chú thích tên đầy đủ), khối chọn hộ có stretch cuối (nhãn
  "Hộ:" không giãn). Một hàng cần ~1.430 điểm, hẹp hơn khối Xem trước / In / Đóng xuống hàng 2.
- Đợt tổng kiểm toán 16/10/2026 (người dùng: "Hội đồng 5 chuyên gia", báo cáo `ket_qua_kiem_tra/KiemToan_2026-10-16.md`):
  - `kiem_toan_lenh.py` (gốc repo): kiểm kê QAction của `CuaSoChinh.lenh` (chỗ đặt: menu trái / thanh menu / nút / chuột phải - nguồn
    `_menu_ho`), nút không nối tín hiệu (receivers clicked/toggled/pressed = 0; nút có menu / defaultAction / nút nội bộ Qt bỏ qua;
    lớp con đặt thuộc tính `menu` trùng tên -> gọi `QPushButton.menu(b)`), widget con của cửa sổ chính ngoài bố cục mà vẫn hiện (che vùng
    bấm), phím tắt trùng ngữ cảnh cửa sổ (đếm MỘT lần - cửa sổ chính chứa sẵn trang nhúng; chỉ phím đang bật), bật / tắt LENH_CAN_DU_AN
    theo 4 trạng thái -> `ket_qua_kiem_tra/KiemToanLenh_*.md`, mã thoát 1 khi còn vấn đề. Kết quả: 0 / 0 / 0 / 0.
  - `kiem_tra_giao_dien.py --trang-thai du_an|chua_mo|trang|chi_doc|tat_ca` (mặc định tat_ca): mọi lệnh ở 4 trạng thái biên (dự án trắng
    = `du_an_trang`), sau mỗi lệnh thử trang nhúng đang hiện (`thu_trang_nhung`: CuaSoLapPA / KhungDuThao / Đơn giá + menu chuột phải
    từng `BangMuc.menu_dong`), báo cáo lỗi theo trạng thái. 0 lỗi, 0 chậm, 0 hộp rò rỉ.
  - Tốc độ: `he_so_k._da_doc` nhớ NHO_GIAY 2 s (khóa PABT_THU_MUC_MAY; `ghi` / `xoa` gọi `_quen`) + `_ChiMuc.vt_xa` (trước: mỗi thửa
    stat 2 file + duyệt cả bảng ở nhánh xã khác); `BoSoan(con, ma, dm, bc)` - `du_an_moi.tu_lap_phuong_an` dùng MỘT BoiCanh cho cả loạt;
    `theo_doi.tong_hop(ds_ma_ho)` lọc `IN (?…)` trong SQL khi <= `LOC_SQL_TOI_DA` 400 hộ ([] -> []), dài hơn đọc cả bảng như cũ - lưu 1
    hộ + tải lại 5.000 hộ 118-134 -> 59-77 ms; `giao_dien.cao_can_dong(nho=)` dùng chung QFontMetrics / bề rộng cột một lượt, ô ngắn
    (len x maxWidth <= cột) khỏi đo; `BangMuc._vua_neu_doi_rong` chỉ đo lại khi bề rộng cột đổi (vua_dong 300 dòng 75 -> 47 ms);
    `in_an.can_khoi_ky` một lượt `_o_chu` + vùng gộp chỉ các dòng quanh khối chữ ký (22 -> 3 ms / hộ; trước đó `ws.cell` mọi cột x 12 dòng
    còn tạo ô rỗng thừa). Đã đo, KHÔNG làm: xóa hộ tải lại toàn bộ (số hộ đổi - DauVetHo trả None; 5.000 hộ ~2 s, thao tác hiếm), ghi xlsx
    của openpyxl (bảng tổng hợp 5.000 hộ ~9 s - giới hạn thư viện), mở dự án 5.000 hộ 1,2 s (đối chiếu + dựng bảng).
  - Còn ẩn / chờ quyết định: nút "Quét hồ sơ…" (TB_QUET_HO_SO), `man_hinh_quet_web.HopQuetWeb` (không còn đường mở từ 0.9.73, chỉ test),
    `CuaSoChinh.quy_chuan` (lệnh bỏ 0.9.47, giữ cho test), `bang_tieu_de` / `KhungLamViecDaTab` (ẩn, trong suốt chuột - còn dùng làm
    nơi giữ dữ liệu).
- Khối chữ ký bản in (người dùng 16/10/2026, ảnh PDF: họ tên người kiểm tra lệch dưới "KIỂM TRA"): `in_an.can_khoi_ky(ws)` gọi TRƯỚC
  `_thay_cho_trong` ở `lap_chi_tiet` / `lap_bang_tong_hop` - ô `{nguoi_lap}` / `{nguoi_kiem_tra}` / `{nguoi_ky}` tìm chức danh gần nhất
  phía trên phủ cột giữa, bỏ dấu cách thừa của chức danh (mẫu IN_CHITIET ghi "   KIỂM TRA     " - Excel căn giữa tính cả dấu cách),
  ô họ tên gộp đúng các cột của chức danh (mẫu người dùng sửa lệch), căn giữa indent 0; ô khác có chữ trong vùng thì chỉ căn giữa.
  Đã xuất PDF bằng Excel kiểm (chi tiết + tổng hợp). Test `tests/test_khoi_ky.py`.
- Hệ số K (người dùng 16/10/2026) = hệ số điều chỉnh giá đất QĐ 03/2026/QĐ-UBND ngày 11/5/2026 UBND thành phố Đồng Nai: giá = giá bảng
  giá NQ 28 × K Phụ lục I (biến động thị trường: I.1 PNN 3 cột đất ở / TMDV / SX phi NN; I.2 NN một cột; I.3 loại còn lại theo loại
  tương ứng) × Phụ lục II (quy hoạch) × III (yếu tố khác) - phần mềm tự áp Phụ lục I; II, III người dùng nhân thêm ở ô Hệ số K.
  Bảng Phụ lục I mỗi xã một bảng, mỗi TT một dòng TRÙNG số TT bảng giá NQ 28 (QĐ ghi "Phường Trị An", bảng giá "Xã Trị An" - so tên bỏ
  Xã / Phường). GẮN SẴN `pabt/he_so_k_qd03.json` (4 địa bàn của bảng giá gắn sẵn, 1.127 TT x 4 nhóm; đóng gói như bang_gia_nq28.json:
  PABT.spec, dung_exe38.DU_LIEU, cap_nhat.DU_LIEU) dựng từ PDF Phụ lục người dùng gửi (thư mục E:\…\03: Bảng 8 Tân Triều, 53 Trị An, 54
  Tân An, 55 Phú Lý trong file PNN / NN) bằng `doc_phu_luc` + `noi_bang_gia` (tên đường / đoạn / vị trí lấy theo dòng cùng TT của bảng
  giá; đủ mọi TT, 0 lệch). Hệ số trong Phụ lục luôn 2 chữ số lẻ ("1,24"): số 1 chữ số lẻ cuối dòng là chữ tên đoạn ("Khu tái định cư 3,8
  ha"). Người dùng nhập / sửa -> `<thư mục máy>\he_so_k.json` thay bảng gắn sẵn (`dang_thay`; `xoa` = dùng lại). Dòng: dia_ban, tt,
  loai_dat (nhóm cột NQ 28 + `nn` / `pnn`, hoặc mã 'ONT,ODT'), vi_tri, tuyen_duong, diem_dau, diem_cuoi, he_so, ghi_chu; file gộp một
  TT nhiều nhóm thành {'k': {nhóm: hệ số}} (`_gon` / `_mo_rong`). `tra(xa, loai_dat, vi_tri, tuyen, tt=)`: có TT -> dòng (xã, TT); không
  -> dòng có TT khớp mã vị trí + tên đường + điểm đầu + điểm cuối trong chữ vị trí (do chon_vi_tri_nq28 ghi; xã dự án trước, rồi xã
  khác), rồi dòng chung (không TT); chỉ mục `_ChiMuc`. Loại đất -> nhóm `nhom_cho_ma` (OTC = đất ở, RPH / RDD = rừng sx, NN khác = cây
  lâu năm, PNN còn lại = SX phi NN, CQP / CAN không tự áp). `doc_file`: PDF -> chữ từng trang (pypdf; ít chữ thì `ocr.tung_trang`) ->
  `la_phu_luc` ? `doc_phu_luc` (chỉ địa bàn ô Địa bàn, trống = `nq.ds_xa()`) : doc_bang / `phan_tich` (bảng / chữ văn bản khác). Giao diện:
  `HopTraNQ28(xem=True, the=)` (lệnh Bảng giá đất) thẻ "Bảng giá đất 2026" (cột Hệ số K, Giá × K) | "Hệ số K (QĐ 03/2026/QĐ-UBND)"
  (`man_hinh_he_so_k.KhungHeSoK`: bảng dựng khi thẻ hiện lần đầu, đọc NHIỀU file một lần (gộp, dòng cùng khóa thay), dán chữ, lọc,
  Lấy / sửa ô, Lưu, Dùng lại bảng gắn sẵn); khái toán `_gia_nhan_k`. Lập PA: `BoSoan._ap_he_so_k` trong `_dien_gia_dat` và
  `chon_vi_tri_nq28` (xã + vị trí + tên đường + TT): khớp -> `he_so_k` + "Hệ số K theo QĐ 03/2026/QĐ-UBND" ở Ghi chú; hết khớp -> bỏ căn
  cứ, K về 1. Hỗ trợ đào tạo: `chinh_sach.ds_thua_nn`, `nghiep_vu.de_xuat_dao_tao_pa` dùng giá × K. Test `tests/test_he_so_k.py` (chữ Phụ
  lục GIẢ LẬP + kiểm bảng gắn sẵn khớp bảng giá; bài ghi he_so_k.json dùng thư mục máy riêng).
- Sau 0.9.97 (người dùng 16/10/2026, CHƯA tăng phiên bản):
  - Nút / cột "HS đính kèm" (`man_hinh_ho_so_scan.TEN_NUT`; trước "Hồ sơ scan").
  - Bảng tổng hợp: `bo_can_cu_kinh_phi` (bỏ "(theo Quyết định số 08…)" ở dòng kinh phí); `vua_cot_chu_bth` (cột Vị trí <= 4 dòng chữ,
    gọi TRƯỚC khi tính cao dòng), `vua_cot_so_bth` (chỉ nới cột số cho số dài nhất + dòng TỔNG CỘNG theo định dạng kế toán - hết
    "#####"); `ngat_trang_bth`: Excel BỎ QUA ngắt trang tay khi fitToPage -> tự tính `scale` vừa bề ngang, tắt fitToPage, ngắt ở
    RANH GIỚI HỘ (`khoi_ho`), khối cuối = dòng tổng + khối chữ ký (không tách sang trang riêng). `DU_PHONG_TRANG` 0,96.
  - Phương án chi tiết: `ngat_trang_ct` - dòng "III." + hàng tiêu đề cột rơi cuối trang mà không kèm được dòng số liệu nào -> ngắt
    trước dòng III (bỏ qua khi fitToPage). Dòng thưởng ('R') KHÔNG gộp ô nữa - ngắt dòng như mục 2-5 (thành tiền vẫn đậm); chỉ
    TỔNG CỘNG ('T') gộp STT..Tỷ lệ.
  - Hộp chọn máy in (như Word / Excel): `xem_truoc_tai_lieu.b_in_hop` "In…" + Ctrl+P (cạnh "In nhanh") -> `in_co_hop_thoai`
    (QPrintDialog: máy in, số bản, khoảng trang) -> `in_tai_lieu` vẽ trang QPdfDocument lên QPrinter (fullPage, ảnh <= `DPI_IN_TOI_DA`
    300, hướng giấy theo từng trang, máy in không tự in nhiều bản thì lặp). Chỉ Qt 6 (`co_hop_in`; Qt 5 không có QtPdf -> "In
    nhanh" qua Excel). Bản dựng giữ QtPrintSupport (`rut_gon.GIU_MODULE`, PABT.spec hiddenimports).
  - Đổi tỷ lệ giao diện: `dat_ty_le` hiện con trỏ chờ, `phong_to` chờ 150 ms. Còn ~0,4-1,1 s mỗi nấc: `app.setStyleSheet` tô lại
    MỌI widget đã polish (cả trang / tab ẩn) - giảm thật cần bỏ cỡ chữ px khỏi QSS (dùng font ứng dụng) hoặc bớt trang giữ trong RAM.
  - Test `tests/test_in_16_10.py` (máy in = QPrinter ghi file PDF).
  - Nguồn gốc đất (phương án chi tiết): mỗi đoạn THỤT ĐẦU DÒNG bằng chuỗi NBSP (`in_an.NBSP`; Excel căn đều không giãn / không
    ngắt ở NBSP - dấu cách thường sẽ bị giãn), dài `thut_dau_nguon_goc()` = hồ sơ địa phương `ban_in.nguon_goc.thut_dau_cm` (mặc định
    1,0; 0 = không thụt). `_ngat(thut_dau=, noi_tiep=)`, `_chia_doan_van(thut_dau=)`: khối Excel bắt đầu giữa đoạn (cắt ở chỗ hết
    câu) không thụt. Căn đều / căn trên giữ nguyên; nhập lại bản in (`nhap_chi_tiet._doan`) tự bỏ NBSP. Màn hình không đổi.
  - HopIn (người dùng 16/10/2026 - một lệnh một chỗ): BỎ `cb_mau_ct` / `cb_mau_bth` (luôn mẫu chính, mau=None; chữ DỰ THẢO do
    Chế độ phát hành), `lb_che_do` (mô tả ở chú thích nút chọn - `man_hinh.MO_TA_CHE_DO`), `o_bc` (Xuất hồ sơ & Bản in không xuất
    báo cáo tiếp thu ý kiến: bao_cao_y_kien=False; `quan_ly.xuat_dot` / `van_ban_trinh` vẫn có tùy chọn). `_chon_mau_theo`,
    `_ghi_chu_che_do` đã bỏ. Mẫu riêng (`in_an.ds_mau`) không còn chọn được trong HopIn.
- 0.9.99 (người dùng 16/10/2026; trước khi tăng phiên bản ghi là "Sau 0.9.98"):
  - CuaSoLapPA: BỎ nút SCAN (`b_ocr`), `quet_giay_to`, `TB_QUET_HO_SO` (Khái toán vẫn có "Quét giấy tờ…" riêng). Hàng trên cùng
    `thanh_tren` = MỘT QHBoxLayout (không còn XepDong 4 khối): Hộ [cb_ho] ◀ ▶ Dán tài sản | Lưu, Bỏ thay đổi | Xem trước, In / Xuất,
    Đóng. `cb_ho` AdjustToMinimumContentsLengthWithIcon + Expanding, `RONG_O_HO` (160, 560) - co / giãn thay cho xuống dòng (đo
    Windows 125%: hàng tối thiểu ~1.030 điểm, màn hình 1366 còn ~1.090).
  - Bảng tổng hợp bản DỰ THẢO: `dat_dau_du_thao(ws, TEN_BTH)` thêm "(DỰ THẢO)" thành DÒNG RIÊNG dưới tiêu đề "BẢNG TỔNG HỢP…" (cùng
    ô, wrap, dòng cao `cao_dong_chu(số dòng)`) - trước nối cuối tiêu đề, người dùng không thấy trên A3.
  - DÀN TRANG THÍCH ỨNG cả hai bản in (người dùng 16/10/2026, 6 hạng mục; `in_an` mục "dàn trang thích ứng"): `chuan_le_trang(ws,
    'chi_tiet'|'tong_hop')` (`LE_TRANG`, hồ sơ địa phương `ban_in.le_trang` ghi đè - `dia_phuong.kiem_tra` kiểm), `dat_ti_le_vua_ngang`
    (scale vừa bề ngang, TẮT fitToPage - Excel bỏ qua ngắt tay khi bật; `RONG_DU_PHONG` 0,96: đo bằng xuất PDF, bảng 683 pt ở 75% = 512 pt
    vẫn bị Excel tách cột Ghi chú sang trang riêng trên khổ in 523 pt, 73% thì không), `cao_trang_in` (`DU_PHONG_TRANG` 0,98), `xep_trang`
    (cụm 'tu_do' / 'lien' / 'lon'; ĐO bằng Excel thật: sức chứa trang = đúng chiều cao vùng in, dòng tiêu đề lặp chỉ in ở trang BẮT ĐẦU
    SAU dòng tiêu đề), `co_gian_vua_trang` (NÉN KHÍT khi nội dung trang cuối tràn khỏi trang áp chót <= `NEN_TOI_DA` 14%: dòng bảng hai
    trang cuối đệm 8 -> 4,5 pt, không dưới `san` (chữ + 4,5) / `CAO_NEN_TOI_THIEU` 20,5, vùng gộp `san_khoi`; GIÃN CÂN ĐỐI trang hở 8-22%:
    +<= 3 pt mỗi dòng), `ghi_ngat_trang` (ngắt tay cuối MỌI trang). Đã nén -> tên `PABT_DEM_DONG` / `PABT_CAO_MIN` (phần mười pt): VBS xuất
    PDF AutoFit vùng PABT_TU_GIAN_DONG dùng đệm / tối thiểu đó (mặc định 8 / 24). `ngat_trang_ct(ws, dau, loai, cuoi_bang, san, san_khoi,
    nhom_gc, cot_gc, co)`: đặt `print_title_rows` = hàng tiêu đề cột (`_doi_dong` / insert_rows KHÔNG dời dòng tiêu đề lặp của mẫu - nguồn
    gốc dài chèn dòng làm lặp nhầm dòng), cụm "III." + tiêu đề cột + mục 1. + dòng số liệu đầu, dòng mục + dòng con, cụm cuối (dòng số liệu
    cuối + TỔNG CỘNG + IV + ngày + chữ ký); vùng gộp ghi chú đất (`gop_ghi_chu_dat` <= `GHI_CHU_TOI_DA` 12 dòng) qua ranh trang tách đôi,
    chữ lặp (`_tach_gop_doc`). Nguồn gốc: `CAO_DOAN_TOI_DA` 90 pt, `DEM_DOAN_VAN` 1,5 + `DEM_DOAN_CUOI` 4 (dòng trước III, `cao_doan_van(
    cuoi=)`); `_chia_doan_van` cắt ở RANH GIỚI DÒNG đã ngắt (hết đoạn muộn nhất, rồi dòng kết thúc dấu hết câu, rồi đủ khối) - KHÔNG cắt
    giữa dòng sau dấu chấm (xuống dòng sớm giữa đoạn, đã thấy trên PDF). `ngat_trang_bth(ws, khoi_ho, tong, n_cot, cuoi, (9, 12), san,
    san_khoi, cam, tach_ho)`: hộ <= `HO_LON` 45% trang không tách; hộ nhiều thửa không đẩy cả hộ khi trang còn >= `CON_CHO_HO_LON` 85 pt,
    tách ở ranh dòng thửa (`cam`: dòng nối dài ô thửa khi chữ > 409 pt - không ngắt sau), `tach_ho` (trong lap_bang_tong_hop) tách MỌI
    vùng gộp dọc qua ranh, lặp STT / họ tên / địa chỉ, chia chữ nguồn gốc theo chỗ phần trên (đo bằng `so_dong_o` như chỗ tính cao), số
    tiền ở phần đầu (SUM không đổi), phần sau thiếu cao thì giãn rồi xếp lại; cụm tổng cộng + kinh phí + chữ ký đứng trơ một trang -> ghép
    với đoạn cuối hộ cuối. Hộ cần dòng thêm (chữ > 409 pt) chừa một dòng chữ + đệm mỗi dòng (`tran`) cho lúc tách. `can_bang_cot_bth`
    (trước khi tính cao: cột số dư > 15% so với số lớn nhất dự kiến - tổng tiền / tổng DT - thu về +5%, phần thừa chia cho họ tên / địa chỉ /
    vị trí; tổng bề rộng giữ). Bảng tổng hợp in ~25% (mẫu rộng 2.922 pt): một trang ~55 dòng thửa. Đã xuất PDF bằng Excel kiểm (chi tiết 90
    thửa + nguồn gốc 10 đoạn: 8 trang = 7 ngắt; tổng hợp tổ chức 90 thửa + 12 hộ: 3 trang). Test `tests/test_in_16_10.TestDanTrangThichUng`.
- Máy cấu hình yếu (người dùng 16/10/2026, phát hành ở 0.9.99; đo `ket_qua_kiem_tra` / phiên Claude):
  - Cửa sổ chính: trang Bảng tổng hợp / Theo dõi tiến độ / Quyết định / Báo cáo tiến độ TẠO KHI MỞ LẦN ĐẦU (`_dam_bao_trang(ô)`;
    `self._cho_trang` = khung trống giữ chỉ số trong `self.trang`; `self.khung_trang` chỉ chứa trang đã tạo; `bang_tong_hop` / `tien_do`
    / `quyet_dinh` / `bao_cao` là property - tạo khi hỏi tới). So sánh trang theo chỉ số (`STACK_TONG_HOP`), ĐỪNG `k is
    self.bang_tong_hop` (tạo trang ngoài ý muốn). Khung tạo sau khi cửa sổ hiện: `giao_dien.ap_kieu_cay(k)` (màu / biểu tượng nút,
    dòng bảng 32 px, khoảng cách, co giãn tỷ lệ) - `_BoToMau` chỉ áp lúc CỬA SỔ hiện lần đầu (`_da_to_mau`; hiện lại chỉ `to_mau`).
    `TRANG_THAI` (bộ lọc) chuyển sang `thong_bao` (quan_ly re-export) - mở phần mềm không nạp quan_ly. Màn hình chào: `tong_du_an.json`
    nhớ cả số hộ, chữ tìm, tên hiển thị (`ghi_tong_nho(…, chu_tim, hien)`) - file không đổi thì `_tom_tat_pabt` không mở SQLite.
  - CuaSoLapPA: khung xem trước A4 tạo khi bật lần đầu (`w_preview` property, `_w_preview`, `_dang_xem_truoc`); `nap_ho` chỉ vẽ
    bảng thẻ đang hiện, thẻ khác `BangMuc.ve_sau()` - vẽ ở showEvent hoặc khi đọc `BangMuc.bang` (property). `ve()` GIỮ cờ `_dang_ve`
    của nơi gọi (vẽ lười chạy giữa `_ve_dong` từng làm cellChanged gọi lại sua_o + hộp báo lỗi). `sua_o` vẫn chỉ vẽ lại dòng sửa.
  - `giao_dien.do_bong`: TẮT mặc định (`PABT_HIEU_UNG_BONG=1` để bật). `csdl._mo_tiep`: `PRAGMA temp_store = MEMORY` (thiết lập kết
    nối, không ghi file). `kiem_toan._trigger`: `AFTER UPDATE OF <trường theo dõi> … WHEN <có trường đổi>` (cập nhật cột tiến độ
    3.000 hộ 13,3 -> 9,4 ms, như không có trigger).
  - `nap_cap_nhat`: sau MỘT lần kiểm đủ (SHA-256 + nạp thử mọi module) biên dịch .pyc + ghi `<bản>/.da_kiem_tot` (dấu = tên / cỡ /
    mtime mọi file pabt\ kể cả __pycache__ + cap_nhat.json + cache_tag); lần mở sau (`dang_khoi_dong` = 0, dấu khớp) chỉ gắn thư mục
    cập nhật, dùng .pyc. Lần trước chưa tới cửa sổ chính / file đổi -> kiểm đủ lại. Đo: 2.209 -> ~240 ms mỗi lần mở (máy dựng).
    Chỉ có hiệu lực ở bản cài dựng từ mã này (nap_cap_nhat nằm trong exe, gói .larcud không thay được). Test `test_cap_nhat.
    test_duong_nhanh_sau_lan_kiem_du`.
  - Bản vẽ CAD: `pabt/dxf_thuan.py` (Python thuần: DXF ASCII, LWPOLYLINE / POLYLINE 2D, TEXT / MTEXT / ATTRIB / chữ trong khối
    theo điểm chèn + tỷ lệ + góc, mã hóa AC1021+ UTF-8 hoặc $DWGCODEPAGE + NFC, \U+XXXX, bỏ paper space; DXF nhị phân -> LoiDxf;
    `viet` ghi DXF R12 tối thiểu cho tu-kiem / test) thay ezdxf trong `ban_do_cad._mo`. ezdxf 1.4 KHÔNG nạp được khi thiếu numpy
    (ezdxf.math import numpy). PABT.spec `LOAI_TRU` / dung_exe38: loại numpy, scipy, matplotlib, PIL, tkinter, unittest, pydoc,
    doctest, ezdxf, fontTools. ezdxf trong requirements chỉ để kiểm thử. Test `tests/test_may_yeu.py`.
- 0.9.99 sửa in đậm nhầm dòng (người dùng 16/10/2026, ảnh PDF): đề mục / TỔNG CỘNG bản in chi tiết đậm nhờ ĐỊNH DẠNG CÓ ĐIỀU KIỆN
  của mẫu (`=OR($AD18="H",$AD18="T")`, công thức tính theo ô trên cùng bên trái vùng). Nguồn gốc dài chèn dòng phía trên bảng
  (`CAO_DOAN_TOI_DA` 90 pt) -> `_doi_dong` / `_vung_cf` dời vùng mà công thức vẫn "$AD18" -> đậm lệch dòng. Nay `in_an._them_cf`
  dời công thức (openpyxl Translator) theo góc vùng mới. Test `test_in_16_10.TestChiTiet.test_dinh_dang_dam_dung_dong_khi_nguon_goc_dai`.
- 0.9.99 Tesseract OCR ĐÓNG KÈM, THAY Windows OCR (người dùng 16/10/2026: "cài tesseract đọc file pdf ảnh, thay thế window OCR";
  Windows tiếng Anh thiếu gói OCR tiếng Việt). `pabt/ocr.py` chỉ còn Tesseract (bỏ `_PS_OCR`, `trang_thai_windows`,
  `cai_tieng_viet_windows`, `doc_anh_windows`; `may_doc()` -> ('tesseract', đường dẫn) / ('', None); HopBoDonGia.xu_ly_pdf_scan bỏ nút
  cài gói Windows). Đầu ra TSV (`tu_tsv`) -> `gom_dong` (cột cách Tab như Windows OCR trước đây); `--tessdata-dir` khi tessdata cạnh exe;
  `ngon_ngu` nhớ theo (đường dẫn, mtime). Tiền xử lý: ảnh xám nguyên cỡ, đọc, đo chiều cao chữ (trung vị khung từ) -> `he_so_phong`
  (< `CAO_CHU_TOI_THIEU` 24 px thì phóng tới 36 px, tối đa x4) rồi đọc lại - KHÔNG phóng chữ đã đủ lớn (đo: ảnh 42 px phóng x3 đọc
  "Giếng" -> "Giêng", "1" -> "J"; quy tắc cũ "cạnh ngắn < 2000 px thì phóng" làm ảnh chụp nhỏ đọc sai). `sua_dvt` ("m°" -> "m²").
  `nhap_don_gia.doc_bang_ocr` tách Tab thành ô (`dong_tu_chu`). Đóng gói: `bo_cai_win/chuan_bi_tesseract.py <giải nén> <tessdata>` ->
  `bo_cai_win/tesseract/` (gitignore): bản Windows 64-bit 5.4.0 của UB Mannheim (GitHub, giải nén bằng 7-Zip - KHÔNG chạy bộ cài),
  chỉ tesseract.exe + DLL theo bảng import PE, cắt section `.debug_*` cuối file (`cat_debug`: libtesseract 101 -> 3,3 MB), tessdata
  vie + osd (tessdata_best) + configs tsv / txt, LICENSE; 42,7 MB. `rut_gon.main` chép cạnh PABT.exe cả HAI bản (thiếu -> dừng dựng),
  `kiem_dll` kiểm luôn; bộ cài phổ quát dùng chung file phẳng Tesseract (`_chep_phang(da_co=)` theo SHA-256 + đích). Tesseract 64-bit
  không nhập hàm nào chỉ có từ Windows 8 (đã kiểm bảng import) -> bản x86 trên Windows 64-bit (cả Win 7) dùng được; Windows 32-bit:
  `ocr.windows_64bit()` False -> báo dán chữ; tu-kiem bước "Nhận dạng chữ bản scan" (32-bit: DAT kèm ghi chú). Đo: trang ~1 s,
  PDF scan A4 150 dpi bảng giá 2,5 s. Test `test_don_gia_15_10.TestOCR` (đọc thật), `test_doc_quyet_dinh.TestOCRThat` (trước đây vẽ ảnh
  bằng Qt offscreen - không phông, chỉ "đạt" vì bị bỏ qua; nay vẽ ở tiến trình QT_QPA_PLATFORM=windows).
- 1.0.00 GỘP "Báo cáo tiến độ GPMB" VÀO "Tiến độ chi trả & Bàn giao" (người dùng 16/10/2026, phân tích Hội đồng chuyên gia: hai
  trang trùng ~70% dữ liệu - mốc thu hồi, vận động / cưỡng chế, lý do còn vướng - và 3 nút trùng lệnh: Xuất DS đề nghị cưỡng chế, Xuất
  danh sách đầy đủ các hộ, Mở theo dõi chi trả). `TRANG` còn 5 mục (`TRANG_BAO_CAO`, `STACK_BAO_CAO`, lệnh `'Báo cáo tổng hợp…'`,
  property `bao_cao` ĐÃ BỎ; `TRANG_DU_TOAN` = 4, Ctrl+1..5; `STACK_CUA_TRANG` = (0, 1, 5, 2, 3) - self.trang 6 ô). Khóa lệnh trang vẫn
  `'Theo dõi tiến độ'`, nhãn `NHAN_MENU` "Tiến độ chi trả & Bàn giao". `man_hinh_bao_cao.py` chỉ còn thành phần: `DaiKPI` (4 `_TheKPI`
  gọn ~64 px, bấm -> `bam(khóa)`, chưa có QĐ / diện tích -> `KHONG_SO` "—" + lời nhắc) và `BangThuaVuong` (cb_muc, BangAo, `lb_trong` +
  `chu_trong()` khi bảng trống, `ma_da_chon` bỏ trùng hộ). `KhungTienDo`: `kpi` + nút chế độ ghép đôi (`nut_che_do`, `QSS_CHE_DO` cục bộ -
  thắng tô màu theo chữ; `che_do()` / `dat_che_do('ho'|'thua')`, `ngan_xem`), `KPI_LOC` (bấm thẻ -> chế độ + bộ lọc), `lb_moc` một dòng
  (đủ chữ ở chú thích) + nút "Mốc pháp lý…" = `HopMocThoiHan(ngay_thong_bao=True)` (ô ngày + số ngày; `mo_moc(gia_tri=, ngay=)`; bỏ
  `o_ngay_tb` / "Lưu ngày thông báo"; `luu_ngay_thong_bao(chu)` giữ), `w_qd` (ô quyết định ẩn khi 0 QĐ, cao theo số QĐ `QD_CAO_DONG`),
  MỘT nút "Xuất" (`menu_xuat`, `hanh_dong_xuat`, `XUAT`: xuat / xuat_bao_cao / xuat_cuong_che). `nap` tính tong_hop + van_dong + mốc
  MỘT lần -> `_ve_tong_quan` -> `bao_cao_gpmb.tong_quan(con, ds=, tt=, moc=)`. `ma_da_chon` theo chế độ đang xem. Test
  `tests/test_yeu_cau_1000.py` (cả bài chặn cùng chữ nút ở 2 trang trở lên, trừ "Xuất Excel…" - mỗi trang xuất bảng riêng).
- 1.0.01 (người dùng 16/10/2026) QUY ƯỚC TƯƠNG ĐƯƠNG ĐỂ TRỐNG ("xóa toàn bộ, để máy trắng - khi nào có tài
  sản thì nhập bổ sung sau"): `don_gia_rieng.bo_quy_uoc_cu(con)` bỏ dòng id < ID_RIENG (mẫu của bộ đơn giá trước 0.9.69 / sheet
  QUY_UOC_TUONG_DUONG của Excel PABT; nhật ký "Bỏ quy ước tương đương mẫu", hoàn tác được) - gọi trong `app.mo` khi mở để sửa (chỉ xem:
  không ghi). `nhap_excel` KHÔNG nhập sheet QUY_UOC_TUONG_DUONG (bỏ khỏi `so_danh_muc`); `nhap_tho.nap_danh_muc` giữ dòng riêng
  (`doc_rieng` / `tra_rieng` như `don_gia.ap_vao_du_an` - trước đây nạp danh mục từ Excel xóa luôn quy ước riêng của dự án). Phương án
  đã lập không đổi (dòng lưu sẵn tên / giá / căn cứ). Đã xóa 5 dòng trong một dự án thật của người dùng (sao lưu
  `ket_qua_kiem_tra\sao_luu\`). Test `tests/test_quy_uoc_trong.py`, `test_lap_pa.test_quy_uoc_tuong_duong` (tự thêm dòng riêng).
- 1.0.01 GIAO DIỆN "Hybrid Enterprise Navy" (người dùng 17/10/2026, đặc tả 6 bước):
  - Menu trái (`giao_dien.menu_trai`, `_qss_menu_trai`): khung `vai="menu_trai"` sát mép trái cửa sổ (nền #F8FAFC, viền phải 1 px;
    lề nội dung chuyển sang `phai` của app), nút "Thu gọn menu" (`khung.nut_thu_gon`, `#nut_thu_gon`) ở HÀNG RIÊNG `khung.hang_gon`
    (`#hang_gon_menu`, cao `CAO_HANG_GON` 32, vạch dưới) TRÊN vùng cuộn `khung.vung_cuon` (`#cuon_menu`, thanh cuộn 6 px) - người
    dùng thấy nút đè tiêu đề nhóm đầu. `CAO_NUT_MENU` 27 -> 32 (min = max); biểu tượng hai trạng thái `icon_hai_trang_thai` (#475569
    / đang chọn navy - QIcon State On / Off, gắn lên QAction dùng chung với thanh menu); tiêu đề nhóm 11 px #64748B, cách trên 10 dưới 4;
    mục chọn nền #EFF6FF + vạch trái 3 px navy. Cỡ chữ QSS mới viết bằng px (phong_to chỉ nhân px, không nhân pt).
  - Thẻ KPI (`CuaSoChinh._hang_the_so`, `THE_SO` nay Tổng kinh phí CUỐI hàng): cao `CAO_THE_SO` 56, cách 8, tên trên (`NhanRutGon`),
    số + chữ phụ dưới (`the_phu`: "hộ" / `tien.phan_tram(k, N)` "81,7%" (tổng 0 -> "0%", Decimal) / "VNĐ"; số đủ "k / N hộ" ở chú
    thích), `the_khung[k]` property `dang_loc` theo `cb_tt` (`_cap_nhat_loc_the`, gọi ở `_dem_loc` / `_cap_nhat_the_so`). Màu viền
    trái `MAU_THE_SO`. `the_so[k].text()` vẫn là SỐ (test cũ đọc).
  - Hàng công cụ danh sách hộ: Thêm hộ `KieuNut.CHINH` (navy), Xóa hộ `NGUY_HIEM` (nay nền trắng viền #FECACA chữ #B91C1C, tắt mờ
    #94A3B8), Chọn hộ niêm yết `PHU` (trắng viền #CBD5E1) - đổi màu biến thể chung `_qss_kieu_nut`; không thêm nút Xuất (mỗi lệnh một
    chỗ: menu Dữ liệu). Mọi ô cao `CAO_DAI_CONG_CU` 32; bỏ nhãn "Đợt:" / "Trạng thái:" / "Tìm:" - mục đầu ô chọn `TAT_CA_DOT` "Đợt: Tất
    cả" / `TAT_CA_TRANG_THAI` (data '' - mo_ta_loc / tên file xuất không lẫn chữ này); `lb_loc` = huy hiệu `vai="huy_hieu_loc"` cuối hàng
    "Đang lọc: <b>k</b> / N hộ" (rich text). Ô tìm tìm cả CCCD (`ho.so_cccd`) và tờ/thửa "12/45" (`_so_lieu_dong` đọc thửa từng dòng,
    DT cộng Decimal - trước SUM(CAST AS REAL)).
  - Bảng: QSS chung `QHeaderView::section:horizontal` nền navy chữ trắng (min-height `CAO_TIEU_DE_BANG` - 10; dọc giữ nền nhạt),
    `QHeaderView { color: #FFFFFF }` để mũi tên sắp xếp của Fusion trắng (không thì xám đậm trên navy), dòng lẻ #F8FAFC, lưới
    #E2E8F0, chọn #DBEAFE / #0F172A; `CAO_DONG_BANG` 30. Danh sách hộ KHÔNG xuống dòng (`setWordWrap(False)`: `_gian_bang` khi đổi cỡ
    chữ giãn bảng xuống dòng thành ~41 px), STT #0284C7, họ tên DemiBold (`BangHo._phong` nhớ theo phông ứng dụng), cột Trạng thái =
    `THANH_NAC[nac]` (■ □ U+25A0 / U+25A1 - không emoji) + chữ gốc, màu `MAU_NAC`; `nac` trong dòng tính từ CÙNG các cờ bộ lọc dùng
    (da_ban_giao / da_chi_tra / da_phe_duyet / đã lập); `d['o'][5]` giữ chữ gốc (lọc, tìm); sắp xếp theo nấc rồi chữ. TextAlignmentRole
    trả SỐ NGUYÊN (`CAN_PHAI` / `CAN_TRAI` như bang_ao) - PySide2 bỏ qua cờ ghép enum (bản Win7 cột số canh trái-trên từ trước).
    Dải cộng `DaiCong` (`self.dai_cong_ds`, `#dai_cong_ds`, ngay dưới bảng): `cong_dai_cong(dòng đang hiện)` Decimal (đất = mục 1, Tài
    sản & Cây = 2 + 3 + MUC_VN, Hỗ trợ & Thưởng = 4 + 5, TỔNG = cộng `tong` từng hộ) -> `chu_dai_cong` (đầy đủ, gọn); `DaiCong._chon`
    đo chữ: hẹp (1366) dùng chữ gọn `NHAN_GON_CONG` + `vn_gon`, chú thích luôn đủ số. Ẩn khi chưa có hộ.
  - Màn hình chào: `MAU_THE_CHAO` cả 3 thẻ nền trắng viền #E2E8F0, rê chuột #F0F6FF + viền màu biểu tượng (navy / #0284C7 / #0F766E);
    bảng gần đây cột 1-4 ResizeToContents (tiêu đề đậm navy không cắt "Tổng kinh phí"), nút Mở `QSS_NUT_MO_GAN` (#nut_mo_gan), nút ghim
    dùng biểu tượng MDL2 0xE841 / 0xE718 (bỏ emoji ghim - Win7 ô vuông). `thanh_tieu_de.CAO` 38 -> 34, `CAO_BANNER` 48 -> 42 (chữ 14 / 11 px).
  - Ảnh thật (QT_QPA_PLATFORM=windows, 125%): 1366x728 và 1916x1020, Qt6 + Qt5 (Qt5: ký tự ■ □ hiện đúng). Test
    `tests/test_giao_dien_navy.py`; sửa theo đặc tả mới `test_yeu_cau_0979` (màu thẻ chào đọc từ MAU_THE_CHAO), `0994`, `0995`.
- 1.0.02 CỬA SỔ CON / TRANG NHÚNG theo chuẩn Hybrid Enterprise Navy (người dùng 17/10/2026, 7 hạng mục + ẢNH MẪU cửa sổ lập phương án):
  - QSS chung (`giao_dien._qss`): màu nút theo VAI TRÒ - `MAU` không còn cam / tím / xanh lá (MAU[n][0] = màu biểu tượng: navy / slate
    / teal; xóa #B91C1C); `_qss_nut_loai(loại, nhóm…)` dùng chung QPushButton / QToolButton / ribbon: nhóm DAC ('luu') nền navy chữ
    trắng, 'xoa' = `NUT_XOA` (trắng, viền #FECACA, chữ #B91C1C), nhóm khác = `NUT_PHU` (trắng, viền #CBD5E1, chữ #0F172A, rê chuột
    #F1F5F9), tắt `NUT_TAT`. LUAT 'luu' thêm "tao du an", "xuat ban ho so". KieuNut.LUU ('success') = navy như CHINH (bỏ xanh lá).
    QTabBar::tab theo `THE_TAB` (nền #F1F5F9 chữ #475569, chọn nền trắng chữ navy 700 + vạch TRÊN 2 px navy, rê chuột #E2E8F0), QGroupBox
    viền #E2E8F0 bo 6 (tiêu đề kiểu thẻ trong vùng margin-top 22px - không bị cắt), QSplitter::handle #E2E8F0 / hover #94A3B8, QDialog
    nền #F8FAFC, `QLabel[vai="tieu_de"]` slate + vạch navy, MAU_TRANG_THAI['tin'] = thanh thông báo #F0F9FF viền #BAE6FD.
    PHÔNG THẺ khai ở MỨC QTabBar (`QTabBar { font-weight: 600; font-size: 13px }`), KHÔNG trong `::tab` / `::tab:selected`: Qt5 đo bề
    rộng thẻ theo phông của thanh thẻ, phông trong ::tab chỉ dùng lúc vẽ -> chữ cắt hai đầu (bản Win7, kiểm ảnh thật Qt5); px nguyên.
    Thẻ đang chọn cùng độ đậm (màu + vạch phân biệt). Kiểu thẻ riêng: property trên QTabBar + QSS chung (`QSS_THE_GACH_CHAN`,
    vai="gach_chan" của CuaSoLapPA) - KHÔNG setStyleSheet trên QTabWidget (chậm) hay trên chính QTabBar (Qt5 cắt chữ).
  - CuaSoLapPA (theo ảnh mẫu người dùng gửi trong phiên): `thanh_tren` objectName 'thanh_tren_lap_pa' (`QSS_THANH_TREN`: nền #F8FAFC,
    vạch dưới, lề 8,4,8,4), `cb_ho` #o_chon_ho chữ đậm, ◀ ▶ #nut_ho_truoc / #nut_ho_sau, `CAO_NUT_TREN` 28; Dán tài sản nền trắng viền
    slate (rê chuột xanh băng / #0284C7); Lưu ap_kieu_nut LUU (navy); Xem trước (F4) tắt = trắng chữ navy, BẬT = nền #EFF6FF viền
    navy (ảnh mẫu - không nền navy đặc); thẻ mục `QSS_THE_LAP_PA` kiểu gạch chân (documentMode) đặt trên `tab.tabBar()`; `hang_dieu_huong()` dựng khung
    `dai_dieu_huong` (QSS_DAI_DIEU_HUONG: nền #F1F5F9, vạch trên 2 px #CBD5E1, lb_tong #tong_pa navy đậm) - trả layout của khung, nơi
    gọi xếp `self.dai_dieu_huong`. Nút "Thêm thửa vào mục 1" và `HangNhapNhanh.nut_them` = KieuNut.CHINH. `HangNhapNhanh`: `CAO_HANG`
    30 cho mọi ô + nút, property hang_nhap="1" + `giao_dien.QSS_HANG_NHAP` trong QSS chung (bộ chọn con cháu thắng `QLineEdit[nhap="1"]`).
    HIỆU NĂNG: KHÔNG setStyleSheet trên KHUNG CHỨA (QTabWidget, hàng nhập, khung tùy chọn HopIn): Qt tính lại kiểu cả cây con - kiểu
    thẻ đặt trên QTabWidget + kiểu 4 hàng nhập làm mở cửa sổ lập PA 340 -> 505 ms (phan_tich_phien_ban: +36% / +78%); đưa vào QSS
    chung theo property / objectName (HopIn #the_tuy_chon_in) hoặc đặt trên widget lá -> ~355 ms. Đo: mở CuaSoLapPA 6 lần, offscreen.
    `KhungXemTruocTaiLieu`: `MAU_NEN` #334155 (vùng trang), thanh `xt_thanh` nền #F8FAFC vạch dưới #CBD5E1, nút sáng cao `CAO_NUT_XT` 28,
    biểu tượng `MAU_ICON_XT` navy.
  - Niêm yết: `_The` property vai="the_ny" + `QSS_THE_NY` (trắng, viền, vạch trái 3 px `MAU_THE_NY`, số #the_ny_so), dai_tien_do_ny bo 5,
    thanh tiến độ navy. Bảng tổng hợp: `man_hinh_theo_doi.DONG_NOI` {cong, kinh_phi, tong: (nền, chữ)} cho KhungCoCau và dòng TỔNG CỘNG
    KhungDoiSoat (BangAo kiểu `mau_chu`); `CAO_O_CONG_CU` 30 cho `_nut` / `_o_tim` / cb_loc / lb_moc. HopDotTrinh: b_xuat KieuNut.CHINH,
    splitter handle 6. HopIn: khung tùy chọn #the_tuy_chon_in (thẻ trắng), Thực hiện KieuNut.CHINH.
  - Tiến độ: `man_hinh_bao_cao._TheKPI` cao `CAO_THE_KPI` 58, vạch trái `MAU_THE` (navy / teal / slate / đỏ trầm), `dat_dang_loc` /
    `dang_loc` (property dang_loc, nền #EFF6FF viền navy); `DaiKPI.dat_loc(khóa)`; `KhungTienDo.the_kpi_dang_loc()` (KPI_LOC khớp chế
    độ + cb_loc) -> `_danh_dau_kpi` gọi ở `ve()` và `dat_che_do`. Nút chế độ = viên thuốc: `khung_che_do` (QFrame #khung_che_do nền
    #E2E8F0 bo 6) chứa hai nút, `QSS_CHE_DO` (chọn navy chữ trắng, không chọn trong suốt). lb_moc #lb_moc nền #F8FAFC viền. HopNhatKyVanDong
    1000 x 640 (<= 1024 x 680).
  - Khái toán: thanh_nhap_nhanh nền trắng viền #CBD5E1, ô / nút `CAO_O_NHAP` 30; lb_tong #the_tong_khai_toan nền #F0F6FF viền #BAE6FD
    chữ navy đậm; b_an_tt #nut_an_tt phẳng. #dai_bo_don_gia nền #F1F5F9 viền #CBD5E1. Cột Hệ số K (`giao_dien.kieu_o_he_so_k`: giữa,
    đậm #0284C7) và Giá × K (`kieu_o_gia_k`: phải, đậm navy) ở HopTraNQ28 + KhungHeSoK.
  - Sửa file CRLF bằng script: KHÔNG dùng `sed -i` của Git Bash (đổi cả file sang LF - đã gặp ở man_hinh.py). Test
    `tests/test_giao_dien_navy_con.py`; `test_yeu_cau_0978` theo màu nút Dán mới, cao 28.
- Bàn giao mặt bằng khi hộ CHƯA có quyết định phê duyệt (người dùng 17/10/2026: một dự án thật cả 170 hộ "Đã bàn giao MB", thẻ 100% - nhật
  ký file: 16/10/2026 11:30 "Bàn giao mặt bằng 170 hộ" = một lần chọn cả bảng, hộp tích sẵn): `theo_doi.ho_chua_phe_duyet`,
  `HopBanGiao(so_chua_qd=)` - có hộ chưa phê duyệt thì KHÔNG tích sẵn "Đã bàn giao" + cảnh báo `lb_canh_bao`; Kiểm tra lỗi (Tiến độ) báo
  "Đã đánh dấu bàn giao mặt bằng nhưng chưa có quyết định phê duyệt" (thay "chưa ghi chi trả" cho hộ đó). KHÔNG chặn cứng: bàn giao
  trước khi phê duyệt là trường hợp có thật. Không tự sửa dữ liệu khi mở dự án. Test `tests/test_ban_giao_chua_qd.py`.
- TIẾN ĐỘ PHÂN TÍCH TỰ ĐỘNG (người dùng 17/10/2026: "đã phê duyệt tăng nấc phê duyệt, đã bàn giao tăng nấc bàn giao, tự động chạy";
  chọn TUẦN TỰ, bàn giao cần chứng cứ; "biên bản không có số, chỉ có ngày"): `theo_doi.phan_tich_tien_do(x)` -> `TienDoHo(nac, da_lap,
  da_pd, da_ct, da_bg, canh_bao)`, `TongHopHo.tien_do` (tính mỗi lần đọc, không lưu): nấc 2 = hộ có trong quyết định (qd_ho), 3 = mọi QĐ
  đã nhận tiền, 4 = đã chi trả + `co_bien_ban_ban_giao` (đã tích + có NGÀY biên bản; file scan không bắt buộc). Tích tay thiếu bước /
  thiếu ngày: không tăng nấc, `canh_bao` ("đã tích bàn giao, chưa phê duyệt / chưa có ngày biên bản") nối vào `TongHopHo.trang_thai`.
  `app._dong_ho` lấy nac + GHI ĐÈ da_phe_duyet / da_chi_tra / da_ban_giao của dòng bằng kết quả phân tích -> thẻ số liệu, bộ lọc trạng thái
  (quan_ly.hop_trang_thai) cùng một nguồn; ô Trạng thái nền vàng + chú thích khi có canh_bao. Cột ho.da_phe_duyet / da_chi_tra /
  da_ban_giao vẫn là dữ liệu nhập (trang Tiến độ nhập / lọc theo cột thật; cột Bàn giao ghi "(chưa có ngày biên bản)", nền vàng).
  `HopBanGiao`: KHÔNG điền sẵn ngày hôm nay (nhãn "Ngày biên bản bàn giao", tích mà trống ngày -> `accept` báo, không đóng); "File biên
  bản" không bắt buộc, nhiều hộ (`nhieu_ho`) dùng chung MỘT đường dẫn (không chép file), ô trống = giữ file đã ghi của từng hộ.
  Trang Tiến độ (KPI mặt bằng sạch, bộ lọc da_bg của trang đó) CHƯA chuyển sang kết quả phân tích - vẫn theo cột tích.
- Menu (người dùng 18/10/2026): "Bản đồ thửa đất" bỏ khỏi menu trái, nằm ở thanh menu Dữ liệu sau "Nhập bản vẽ CAD (.dxf)…" (bỏ hẳn tính
  năng chỉ bớt ~42 KB mỗi bản - ezdxf / numpy đã loại khỏi bản dựng từ 0.9.99).
- Bảng mục CuaSoLapPA (người dùng 18/10/2026, ảnh mẫu): nút "Xóa dòng" thay bằng cột THÙNG RÁC cuối mỗi dòng - `BangMuc.c_xoa` =
  len(self.cot) (cột ngoài self.cot: mọi chỗ dùng self.cot[c] phải bỏ qua c >= len(self.cot), như `_doi_o`), `NutXoaDong` (delegate vẽ
  biểu tượng 0xE74D giữa ô, rê chuột đỏ, Win7 không phông: ký tự ×, không mở khung sửa), `RONG_COT_XOA` 34 cố định, `_bam_o` bấm ô
  thùng rác -> `man.xoa_dong(muc, r)` (đúng dòng đó, kể cả đang chọn nhiều dòng); phím Delete (`_phim_xoa`, WidgetShortcut trên bảng)
  và menu chuột phải vẫn xóa dòng đang chọn. Test `tests/test_xoa_dong_thung_rac.py`.
- 1.0.03 "Enterprise Financial Desktop" (người dùng 18/10/2026, 8 hạng mục; GIỮ tên hàm / thuộc tính / khóa self.lenh / item.text()):
  - `bang_ao._MoHinhAo` ForegroundRole (ô không có mau_chu riêng): chữ trong `SO_KHONG` ('0', '0,0', '0,0%', '-'…) xám `MAU_SO_KHONG`;
    cột tiêu đề có "tổng" / "thành tiền" (`la_cot_tien`, `cot_tien`) chữ số navy. Chỉ BangAo (QTableWidget không đổi).
  - `giao_dien.VeOBangChuyenNghiep` (QStyledItemDelegate, KHÔNG đổi DisplayRole): kieu 'vien_thuoc' (viên thuốc màu `MAU_VIEN_THUOC`
    theo chữ bỏ dấu - THỨ TỰ quan trọng: "khong dong y"/"chua dong thuan" trước "dong y"; thanh nấc "■□" đầu chữ -> 4 vạch; "●" bỏ),
    kieu 'ty_le' (thanh 3 px dưới ô theo `so_ty_le`). Gắn: `gan_vien_thuoc(bang, *cot)` (danh sách hộ cột 5, Niêm yết bang_yk 2 /
    bang_vm 3), `gan_thanh_ty_le` (KhungCoCau cột 6, bang_th cột 4). `gan_chu_khi_trong(bang, chính, phụ)` = lớp phủ `_ChuKhiTrong` trong
    suốt chuột trên viewport + bộ lọc Resize / Show / Paint; tín hiệu mô hình nối PHƯƠNG THỨC `phu.cap_nhat` (lambda giữ bảng -> "already
    deleted" khi bảng bị hủy). Dùng ở BangMuc, KhungDuToan, KhungHoSo, Niêm yết, Quyết định, Tổng hợp tiền, Cơ cấu, Tiến độ.
  - `TheKpiGon` / `HangKpi([(khóa, tên, màu[, gợi ý])])` (54 px, 2 tầng, vạch trái 3 px bo 3) + `DaiCongBang` (32 px; `dat(phan, tong,
    phan_gon, tong_gon)` - 3 mức chữ theo bề rộng: đủ / gọn / chỉ tổng). KhungBangTongHop `hang_kpi` (quy_mo, cong, kinh_phi, tong) dùng
    `_lay_cc` (co_cau tính MỘT lần, KhungCoCau.nguon_cc), KhungQuyetDinh `hang_kpi` (so_qd, luot_ho, tien_qd, chenh = tổng QĐ - PA hiện tại
    qua `nghiep_vu.ket_qua_ho`) + `dai_cong`; KhungTongHopTien tiêu đề 2 dòng, `_vua_cot_tien` (số dài nhất / dòng tiêu đề dài nhất + 18 -
    ResizeToContents tính cả mũi tên sắp xếp, tràn), Họ tên Stretch, `dai_cong`; KhungTienDo chân trang QHBoxLayout `dai_cong_td` (giãn) +
    4 nút Maximum; Mốc / Vận động 155 / 160 px.
  - Bàn giao THỐNG NHẤT với danh sách hộ: `theo_doi._dieu_kien` (chua_bg / da_nhan_chua_bg / da_bg) và `bao_cao_gpmb.tong_quan` (dt_ban_giao,
    so_ho_ban_giao, thửa còn vướng, tờ đã giải tỏa) dùng `x.tien_do.da_bg` (QĐ + nhận đủ + ngày biên bản), không ô tích.
  - Menu trái: `LENH_DANH_DAU_PHU` checkable; `_dong_bo_menu_trai(khoa=None)` (None: `_lenh_dang_xem` suy từ ngan_lv / stack_phu / thẻ dự
    toán) gọi ở `_danh_dau_trang`, `_danh_dau_trang_chu`, `_dam_bao_tab`, `_tab_doi_khoa`, `so_sanh_du_toan`, tab dự toán currentChanged,
    và SAU MỌI LỆNH (`_chay_lenh` - QAction checkable tự đảo dấu khi bấm mà không mở gì).
  - QSS: QGroupBox phẳng (margin-top 6, padding-top 26, title subcontrol-origin border, không viền "tai"), QTableCornerButton navy, header
    dọc slate, `QTableView { outline: 0 }`, menu trái `outline: none`, `QSS_O_TIM_CHON` (OTimChon spacing 0, nút ▼ `nut_xo_tim_chon`
    `RONG_NUT_XO` x `CAO_NUT_XO`, icon 0xE70D).
  - Danh sách hộ: `COT_GIUA` {0, 3} căn giữa (tiêu đề qua headerData), `RONG_COT_DS`, `COT_GIAN_DS` (1, 2) Stretch, stretchLast False -
    cỡ chữ 110-125% vẫn không cuộn ngang. HopDuAn `KICH_THUOC_HOP_DU_AN` 1180 x 535, `_dau_dong_va_goi_y`. CuaSoLapPA `NhanTongPA` +
    `chu_tong_pa(kq)` (4 mức; `text()` trả chữ ĐẦY ĐỦ), cột phụ tiêu đề 2 dòng ('Nguồn\ngiá', 'Quy\ncách', 'Ghi chú (quy định,\ncách
    tính)', 'Căn cứ\ngiá'). KhungHoSo `the_chu_ho` + `lb_tom_tat_thua` (`tom_tat_thua`: số thửa, số tờ, DT thu hồi Decimal).
  - Niêm yết `_The` 2 tầng `CAO_THE_NY` 54 (QSS_THE_NY ở man_hinh_du_thao - góc trái bo 3), `_pt` (% dấu phẩy), hàng đợt `XepDong`.
    KhungDuToan: thanh nhập gọn (`RONG_LOAI_DAT_KY_TU` 9, `RONG_O_CHON_TOI_THIEU` 100, `CACH_THANH_NHAP` 4, nhãn Mục ẩn, nút padding 7) -
    `can_mot_hang` bỏ widget ẩn; một hàng ở ~1.180 px (Full HD 125%); kiểu Đường kính vẫn có thể xuống hàng. `chu_the_tong` 2 dòng
    (`CAO_THE_TONG_KT` 48). HopDotTrinh `HUY_HIEU_KIEM`; HopBoDonGia `lb_loc` + đổi thẻ lọc lại.
  - Ảnh nghiệm thu: `ket_qua_kiem_tra/thu_that/chup_giao_dien.py [--ty-le 1.25] [--co 1536x824]` (QT_QPA_PLATFORM=windows, dự án GIẢ
    LẬP, PABT_THU_MUC_MAY tạm; QSettings cỡ chữ 110% của máy vẫn áp) -> `ket_qua_kiem_tra/anh_<ver>_<cỡ>_<tỷ lệ>/`.
  - Heredoc của Bash trong phiên Claude NUỐT dấu "\" kể cả với <<'EOF' (đã làm hỏng '\n' thành xuống dòng thật 3 lần): script Python sửa
    file PHẢI ghi bằng Write rồi chạy, hoặc dùng Edit.
- 1.0.04 (người dùng 19/10/2026, 7 nhóm; test `tests/test_yeu_cau_1004.py`):
  - BỎ HẲN che CCCD (thay quyết định NĐ 13/2023 của 0.9.24 / 0.9.85): `an_toan.che_cccd` trả nguyên chuỗi, `can_che_cccd` luôn False
    (khóa cai_dat CHE_CCCD cũ bỏ qua), `pabt_profile.json` `ban_in.che_cccd_ban_du_thao = false`; `in_an._thong_tin_ho(che=)` /
    `lap_chi_tiet(che_cccd=)` giữ tham số nhưng bỏ qua; `HopIn.o_che_cccd` ẩn + luôn tắt (thuộc tính giữ cho mã cũ), bỏ `_luu_che_cccd`;
    ô che trong Cấu hình nghiệp vụ ẩn. ĐỪNG thêm lại che CCCD.
  - Phương án chi tiết: tổ chức (`ho_so.la_to_chuc`) -> `dat_nhan_chu_su_dung` đổi "Họ và tên:" -> "Tổ chức:", "Địa chỉ thường trú:" ->
    `NHAN_DIA_CHI_TO_CHUC` "Địa chỉ:", ẩn dòng Số CCCD + Số điện thoại. Nguồn gốc (`dat_doan_van`): MỖI ĐOẠN MỘT DÒNG Excel
    (`_chia_doan_van(moi_doan=True)`), thụt đầu `so_nbsp_nguon_goc()` = 4 NBSP (hồ sơ `ban_in.nguon_goc.thut_dau_nbsp`, 0 = theo
    thut_dau_cm), căn đều + giữa dọc (mặc định `can_doc` nay "center"), U+2028 = xuống đoạn; `bo_lap_mo_dau` khử cụm mở đầu "…:" lặp hai lần.
    Mục 1 (`dong_chi_tiet`): `dien_tich_dong_dat(dt dòng, thửa)` (ct_dat -> dt_boi_thuong -> dt_thu_hoi; bảng thua chưa có cột
    dt_boi_thuong - tự bỏ qua); dt > 0 luôn in "m²" + SL, đơn giá 0 thì trống ĐG / tỷ lệ và tên gọn `mo_ta_thua(..., None)`; dt 0 trống ĐVT /
    SL; thành tiền 0 vẫn in (bỏ quy tắc 12/10/2026 "đất 0 đồng bỏ số lượng"). `gop_ghi_chu_dat` căn giữa hai chiều.
  - Bảng tổng hợp (`lap_bang_tong_hop`): cột Vị trí đất (N, số cột 11) ẨN (`vua_cot_chu_bth` đã bỏ); cột tiền >= `RONG_COT_TIEN_BTH` 14;
    `can_bang_cot_bth` chỉ chuyển dư từ cột diện tích sang họ tên / địa chỉ; căn lề: nguồn gốc justify, họ tên / địa chỉ / TĐC / ghi chú
    center; số 0 dòng hộ `dinh_dang_so_gach` ("-"), 5 dòng tổng `dinh_dang_so_khong` ("0") - `_chia_dinh_dang` tách theo ";". Hộ nhiều
    thửa: STT / họ tên / địa chỉ lặp mỗi dòng (bỏ khỏi gộp - `cot_lap_thua_bth`), nguồn gốc riêng từng thửa khi `tach_nguon_goc_theo_thua`
    tách được (chữ các thửa khác nhau, hoặc chữ chung có đoạn nhắc số thửa cho MỌI thửa - `nguon_goc_cua_thua`), không thì gộp một ô như
    cũ; hộ một thửa giữ đủ chữ (chỉ khử lặp). Dòng 85%: `{don_vi_lap}` -> `rut_gon_don_vi` ("… - Chi nhánh X" -> "TTPTQĐ Chi nhánh X",
    không ghi cố định tên đơn vị). Dự thảo: `dat_dau_du_thao(TEN_BTH)` đặt "(DỰ THẢO)" dòng ngay dưới ô tên đơn vị (cột A, dòng 3 mẫu) và ẩn
    dòng "(Đính kèm Phương án số …)"; `ap_che_do_du_thao` gọi SAU `_dat_duong_ke` (chữ mới không làm đường kẻ neo nhầm). VBS `chay_excel`:
    sau AutoFit còn ngắt trang TỰ ĐỘNG (HPageBreaks Type <> -4135) thì giảm Zoom 2% (tối đa 6 lần), không hết thì trả Zoom cũ - KHÔNG
    dùng FitToPagesTall (Excel bỏ ngắt tay khi bật).
  - `kiem_loi`: `la_ho_tai_san_tren_dat(ho, thua, pa, map_thua)` ((a) cùng tờ/thửa có hồ sơ khác dt > 0, (b) có dòng mục 2-4 mà tiền đất 0
    - `tien_dat_cua`, (c) từ khóa `TU_KHOA_TAI_SAN_TREN_DAT` không dấu) -> không báo "diện tích thu hồi bằng 0"; `la_quan_he_chu_dat_va_
    tai_san(nhóm)` (<= 1 hồ sơ có dt / tiền đất) -> không cảnh báo trùng thửa cho cả nhóm. `doc_tat_ca_phuong_an` đọc TRƯỚC phần thửa
    (một lần, dùng lại cho phần phương án).
  - `HopDuAn`: bỏ `can_giua` (lưới `QGridLayout` 2 cột giãn; kinh phí + `the_phap_ly` trải hai cột), ô Cơ quan thẩm định / loại kinh phí
    `AdjustToMinimumContentsLengthWithIcon` (không ép hộp rộng gấp đôi); khung `the_phap_ly` (`lb_pl` quy mô / căn cứ / trạng thái,
    `b_phap_ly` -> `mo_tiep_nhan`). `kinh_phi_du_an.co_cau`: dòng kinh_phi có cả tien_pd / chua_pd (= cộng x tỷ lệ), thêm 2 dòng
    `loai='phan_bo'` (`dong_phan_bo`: "  - Tổ chức làm nhiệm vụ bồi thường (<đơn vị lập>) 85%:", "  - Cơ quan phối hợp thực hiện (<xã>)
    15%:" theo `dia_phuong.phan_bo_kinh_phi`) - KhungCoCau 10 dòng.
  - Sao chép trên MỌI bảng (`giao_dien.cho_phep_sao_chep_bang`, gắn tự động ở `ap_kieu_cay` cho mọi QTableView khi cửa sổ / khung hiện):
    `_BoSaoChep` bắt Ctrl+C (ShortcutOverride + KeyPress: một ô = ô hiện tại; nhiều ô / dòng = Tab + xuống dòng) / Ctrl+Shift+C (cả dòng);
    bảng không có menu riêng -> CustomContextMenu `menu_sao_chep`; bảng có menu riêng (danh sách hộ `_menu_ho`, `BangMuc.menu_dong` - bỏ
    mục "Chép nội dung ô", Đơn giá `_menu_bang`, Khái toán `_menu_bang`) gọi `them_muc_sao_chep(menu, bang, pos)` (đưa 2 mục lên đầu). Ô sửa
    QLineEdit mở bằng chuột / F2 -> selectAll (mở bằng gõ phím thì không - cờ `_go_phim`). Bảng mới có menu chuột phải riêng: gọi
    them_muc_sao_chep.
  - `KhungHoSo`: `nhan_o`, `NHAN_HO`, `cap_nhat_nhan_to_chuc` (tổ chức: "Tổ chức:" / "Địa chỉ:", ẩn `AN_KHI_TO_CHUC`), `dt_theo_loai` vào dải
    chân bảng thửa; `HopNguonGoc.cb_mau` + `chen_mau` (`MAU_CAU_NGUON_GOC`, chỗ trống "…", không số liệu thật). Bảng thô: `giao_dien.
    gan_o_loc_bang` / `loc_dong_bang` / `to_dong_bang` (`MAU_DONG_CANH_BAO` vàng, `MAU_DONG_LOI` đỏ); `HopDuAnMoi.o_tim_tho`, `loi_dong_tho`
    (thiếu tờ / thửa / loại đất, sai ký hiệu TT 08), `kiem_tra_bang_tho`, `dien_san(gt)`; `HopNhapChiTiet.o_tim` + tô dòng lỗi / cảnh báo.
    Không có `HopNhapTho` (nhap_tho không có hộp thoại).
  - Tiếp nhận & kiểm tra pháp lý (`tiep_nhan_phap_ly.py` không Qt + `man_hinh_tiep_nhan.HopTiepNhanPhapLy(con=None, file_du_an, parent,
    im_lang, khoi_tao, du_lieu)`): dict JSON (`moi` / `chuan`), file `.pabtpl` (`luu_file` tmp + os.replace / `mo_file`), trong dự án ở
    cai_dat `KHOA_DU_AN` (`doc_du_an` / `ghi_du_an`, có nhật ký); `LOAI_CDT` (4), `CAN_CU` (Điều 78 / 79 / 122 / 127), `NHOM_HO_SO` 5 nhóm
    = 32 mục `(mã, nội dung, điều kiện)` - `ap_dung` theo loại CĐT / căn cứ, `BAT_BUOC`; `KY_THUAT` 10 tiêu chí (`ket_qua_ky_thuat` lấy kết
    quả `quet_excel` = `nhap_tho.doc` chỉ đọc); `kiem_tra_thoi_han` (hạn chủ trương, NQ HĐND quá `NAM_HIEU_LUC_NQ` 2 năm), `trach_nhiem`,
    `tong_hop` (da_co / con_thieu / can_bo_sung, đủ điều kiện / đúng tiến độ tự động + `xac_nhan` của người dùng), `trang_thai`,
    `tom_tat_du_an`, `tu_khai_toan` (.pabtdt), `tu_du_an`, `xuat_phieu_xlsx`, `xuat_cong_van_docx` (thể thức NĐ 30/2020 bằng
    `van_ban_trinh._p/_r/_o/_bang/_goi_docx`; chưa có đơn vị: dòng chấm), `du_lieu_du_an_moi`. App: lệnh 'Tiếp nhận & Kiểm tra pháp lý dự
    án…' (NHAN_MENU 'Tiếp nhận hồ sơ pháp lý', Ctrl+Shift+L, menu trái nhóm 1 sau So sánh, KY_HIEU 'tiep nhan'), KHÔNG thuộc
    LENH_CAN_DU_AN; thẻ thứ 4 màn hình chào (`MAU_THE_CHAO['phap_ly']`, cùng QAction); `tiep_nhan_phap_ly(cho)`, `du_an_moi(dien_san=)`.
    Số điều / khoản (Khoản 27 Điều 79, Khoản 7 Điều 76, Điều 60 / 62 NĐ 102, Điểm b Khoản 2 Điều 127) theo yêu cầu người dùng - CHƯA đối
    chiếu văn bản gốc trong phần mềm.
  - `from __future__ import annotations` đứng SAU docstring module (Python bắt buộc; "dòng đầu" của yêu cầu = câu lệnh đầu).
- 1.0.05 MỘT HỘ NHIỀU LẦN LẬP PHƯƠNG ÁN (người dùng 19/10/2026: "hộ A 4 phương án, 4 quyết định, không mất dữ liệu lần trước, cộng
  dồn"; test `tests/test_nhieu_lan_pa.py`). CSDL v17 (`_NANG_CAP[16]`): `ct_dat.lan`, `ct_khoan.lan` (mặc định 1 - dòng cũ = lần 1),
  `qd_ho.lan` (0 = trước v17, coi là lần 1), bảng `pa_lan` (ma_ho, lan, ten, ngay_lap, so_pa, ngay_pa, trang_thai dang_lap /
  da_phe_duyet / mo_khoa, khoa, ghi_chu; UNIQUE(ma_ho, lan)); `@pa_lan_v17` = `csdl._tao_pa_lan` (hộ đã có QĐ: lần 1 khóa). Bộ đơn
  giá đóng gói nâng v17 (`tao_bo_don_gia.py --chuan-hoa 2026.10.12`). Bản <= 1.0.04 không mở được file v17.
  - `nghiep_vu.doc_phuong_an(con, ma_ho, lan=, den_lan=, ngoai_lan=)`: MẶC ĐỊNH CỘNG DỒN mọi lần - mọi nơi tính tổng hộ (danh sách,
    ket_qua_ho, đối chiếu, kiểm lỗi, theo_doi, kinh phí) không đổi; `co_cot_lan(con)` (nhớ trên thuộc tính kết nối - KHÔNG đặt vào
    `con.bo_nho`: giu_tat_ca giải nén từng giá trị thành (tt, gt)); `gop_phuong_an`, `tinh_pa_lan(pa_lan, pa_truoc, bc)` (thưởng của
    lần = thưởng lũy kế tới lần - thưởng các lần trước: cộng các lần = tổng hộ), `tinh_lan(con, ma_ho, lan)`.
  - `lan_pa.py` (không Qt): `ds_lan` -> [LanPA] (luôn có lần 1; lần có QĐ -> đã phê duyệt + khóa trừ MO_KHOA), `lan_mac_dinh` (lần
    chưa khóa muộn nhất, mọi lần khóa: lần cuối), `lan_moi_nhat` (lần muộn nhất có dòng - in), `lan_chua_duyet`, `tao_lan_moi`,
    `sua_lan` (lần 1 ghi cả ho.so_pa / ngay_pa), `mo_khoa_sua`, `xoa_lan` (chỉ lần >= 2 chưa QĐ), `gan_qd` / `bo_qd`, `tong_hop_ho`,
    `ho_nhieu_lan`.
  - `BoSoan(con, ma_ho, dm, bc, lan=None)`: `lan`, `khoa`, `pa` = dòng của lần, `pa_truoc`, `pa_khac`; `ket_qua` = riêng lần,
    `ket_qua_cong_don`; `luu` CHỈ xóa / ghi dòng `lan = self.lan` (khóa -> LoiNhap); `lap_bo_sung`; `thua_cua_ho` DT còn lại trừ cả
    các lần khác. `bo.mo(ma_ho)` không truyền lần -> lần mặc định (giữ lần đang soạn: `bo.mo(ma, bo.lan)`).
  - `theo_doi.ghi_qd_ho`: hộ MỚI vào QĐ -> gắn lần chưa duyệt sớm nhất (`gan_qd`, số PA của lần bổ sung); `them_ho_theo_pa` hộ đã có QĐ
    / nhiều lần lấy tiền `tinh_lan` (mọi lần đã duyệt: bỏ qua, không trùng tiền); bỏ hộ khỏi QĐ -> `bo_qd` mở khóa. `TongHopHo.so_lan /
    lan_chua_duyet / muc_pa_duyet` (chỉ tính cho `ho_nhieu_lan`), `phan_tich_tien_do` cảnh báo "PA bổ sung lần k chưa phê duyệt";
    `kinh_phi_du_an.co_cau` dùng `muc_pa_duyet` cho cột lệch / chưa phê duyệt.
  - Bản in: `in_an.lap_chi_tiet(lan=None|'moi_nhat'|'cong_don'|số)` (`chon_lan_in`; mặc định lần mới nhất có dòng - hộ một lần không
    đổi), `dong_chi_tiet(pa_truoc=)`, `dat_tieu_de_bo_sung` ("PHƯƠNG ÁN CHI TIẾT BỔ SUNG LẦN k"), số / ngày PA của lần;
    `lap_bang_tong_hop(lan='cong_don')` (mặc định cộng dồn; 'moi_nhat': hộ nhiều lần chỉ tiền + thửa của lần); `van_ban_trinh.
    xuat_bo_ho_so(lan='moi_nhat')`; `HopIn.cb_lan` / `lan_in()` (chỉ hiện khi dự án có hộ nhiều lần), khóa xem trước thêm lần.
  - Đặc tả 6 bước người dùng 19/10/2026 (cùng bản 1.0.05): tên API theo đặc tả là BÍ DANH của hàm đã có - `lan_pa.lan_hien_tai` (=
    lan_mac_dinh dạng LanPA), `mo_khoa_lan(con, ma_ho, lan, ly_do)` (= mo_khoa_sua + lý do vào nhật ký "CẢNH BÁO - Mở khóa…"), `khoa_lai`,
    `tong_hop_cac_lan` (so_lan, so_da_duyet, tien_tung_lan {lần: Decimal}, tong_cong_don, chua_duyet), `BoSoan.tinh_cong_don()`,
    `nghiep_vu.tinh_pa_lan` HAI cách gọi (PhuongAn, pa_truoc, bc) | (con, ma_ho, lan, bc), `CuaSoLapPA.chuyen_lan` / `_ap_trang_thai_khoa`.
    `LanPA.nhan_trang_thai`; lần 1 tên `TEN_LAN_GOC` 'Phương án gốc'; `KhungQuyetDinh.them_ho(lan='hoi')` -> `_hoi_lan` (QInputDialog chọn
    lần phê duyệt); tiêu đề in "PHƯƠNG ÁN CHI TIẾT BỔ SUNG (LẦN k)" (k = số lần, đậm). Khác đặc tả: pa_lan khóa id + UNIQUE(ma_ho, lan),
    FK ho(ma_ho) (không có ho.id); qd_ho.lan 0 = trước v17; ds_lan trả lần 1 ẢO (không ghi khi đọc - khỏi mất bộ nhớ đệm / bước hoàn
    tác); không emoji 🔒 (Win 7). Test kịch bản 150 + 50 + 10 = 210 triệu: `test_nhieu_lan_pa.TestKichBan210`.
  - Giao diện: `CuaSoLapPA` dải `dai_lan` (`QSS_DAI_LAN`, property khoa): nhãn "Lần lập PA:", `cb_lan`, `b_lan_moi` "+ Lập phương án bổ sung"
    (KieuNut.CHINH), `lb_trang_thai_lan`, `lb_tong_cong_don` (= lb_lan), `b_sua_lan`
    (`HopLanPA`), `b_mo_khoa`, `b_xoa_lan`, `lb_lan` (`_chu_lan`: cộng dồn, đã phê duyệt k/n); `chon_lan`, `lap_bo_sung(ten)`,
    `sua_lan(gia_tri)`, `mo_khoa_lan(xac_nhan)`, `xoa_lan(xac_nhan)`; `_ap_khoa` (lần khóa: bảng mục NoEditTriggers, ô / nút nhập tắt,
    Lưu tắt). `man_hinh_theo_doi.so_pa_lan(q)` ghi "PA bổ sung lần k" ở cột Số PA.
- 1.0.06 (người dùng 20/10/2026, đặc tả 4 hạng mục + ẢNH MẪU) thẻ "Thông tin hộ, thửa đất" (`man_hinh_ho_so.KhungHoSo`):
  - Bảng `thua` thêm `dt_nguyen_thua`, `so_gcn` (TEXT, '' = chưa nhập) KHÔNG đổi PHIEN_BAN_CSDL: schema.sql (file mới), `csdl.mo` thêm khi
    file có hộ (TRƯỚC khi Hoàn tác liệt kê cột - hoan_tac lấy cột bằng PRAGMA lúc gắn), `ho_so.luu_ho` -> `csdl.dam_bao_cot_thua` khi ghi
    (dự án trống). `csdl.COT_THUA_THEM`, `co_cot_thua` (nhớ trên kết nối). `ho_so.TRUONG_THUA` thêm 2 trường CUỐI; `chuan_hoa_thua`: DT thu
    hồi > DT nguyên thửa -> LoiNhap. Bản cũ mở file vẫn được (cột thừa); bộ đơn giá đóng gói không bị ghi (không có hộ).
  - Khối I `#khung_chu_ho` (`self.the_chu_ho`): lưới 3 cột `O_LUOI_HO` (hàng 1 Họ tên | CCCD | Ngày cấp + Nơi cấp chung ô; hàng 2 Địa chỉ |
    Điện thoại | Tình trạng pháp lý; hàng 3 Ghi chú | Tranh chấp | Hồ sơ đính kèm = `nut_scan`) THEO ẢNH (đặc tả chữ ghi địa chỉ trải 2
    cột - ảnh thắng); bí danh `BI_DANH_O` (lb_ten / o_ten, lb_cccd / o_cccd, lb_ngay_cap / o_ngay_cap, lb_dia_chi / o_dia_chi, lb_sdt / o_sdt,
    lb_ghi_chu / o_ghi_chu, lb_tinh_trang / o_phap_ly); thẻ nhỏ `QLabel[the_nho=vang|xanh|do|lam|xam|loai]` (QSS_HO_SO_HO): loại đối tượng,
    `kiem_cccd()` ('du' / 'thieu' / 'trung' hộ khác / 'cmnd' 9 số / ''; ô `o_cccd[hop_le="0"]` viền đỏ), gợi ý sao chép.
  - Bảng thửa `COT_THUA` 11 cột + cột ẩn `vi_tri` (mô tả - dòng 1 ô nguồn gốc): STT (giữ ma_thua ở UserRole, đánh lại trong
    `_cap_nhat_o_tinh`), DT còn lại (= DT nguyên thửa - tổng DT thu hồi các dòng cùng tờ / thửa; âm: đỏ), Vị trí đất (= `ct_dat.vi_tri`
    của thửa ở mục 1, chỉ xem, `OVienThuoc`), Loại đất `OLoaiDat` (viên màu `MAU_LOAI_DAT`), Thao tác `OThaoTac` (Sửa = `sua_dong`, thùng rác
    = `xoa_dong(r)`). Ô tính đặt trong blockSignals + CHỈ khi đổi (đặt mãi -> dataChanged -> hẹn tính lại -> vòng lặp khi rảnh). Dòng cao
    cố định `CAO_DONG_THUA` 44; `ONguonGoc` vẽ "• Vị trí: …" / "• Nguồn gốc: … [Xem/Sửa đủ ↗]" (`vung_lien_ket`), bấm đúp / bấm liên kết /
    Enter / Sửa -> `mo_hop` -> `HopNguonGoc(vi_tri=)` sửa cả vị trí. Chọn TỪNG Ô (SelectItems; xóa thửa = mọi dòng có ô chọn), `menu_bang`
    (Sao chép ô / "Sao chép cả dòng thửa", mở hộp nguồn gốc, thêm / tách / xóa). Tiêu đề 2 dòng `TIEU_DE_HAI_DONG` (chữ đủ ở chú thích),
    `vua_tieu_de` (showEvent / FontChange). Dùng `self.cot.index(khóa)` - ĐỪNG viết số cột.
  - Dải `#thanh_tom_tat_thua`: `lb_tom_tat_thua` ("Tổng hợp địa chính hộ: …", `tom_tat_dia_chinh()`: DT nguyên thửa một thửa nhiều dòng tính
    một lần) + thẻ `co_cau_loai()` theo `NHOM_THE_LOAI` (chỉ nhóm có thửa, rồi "Loại khác"). Ảnh: `ket_qua_kiem_tra/thu_that/chup_ho_so.py`
    (QT_QPA_PLATFORM=windows, `--ty-le 1.25`, `--do` in vị trí khối). Test `tests/test_ho_so_khung_2010.py`.
  - `lb_tb` của CuaSoLapPA ẩn khi trống (`thong_bao(tb)` đặt chữ + setVisible) - hết khoảng trống trên dải điều hướng.
- 1.0.06 (tiếp, người dùng 20/10/2026, đặc tả 5 phần + 4 ẢNH MẪU) đồng bộ các màn hình còn lại:
  - CuaSoLapPA: `dai_dinh_danh` (38 px `CAO_DAI_DINH_DANH`, `dd` {ten, cccd, dia_chi, dot: (nhãn, giá trị)}, `lb_tong_dd` khung vàng = tổng
    CỘNG DỒN mọi lần; `_nap_dinh_danh` trong nap_ho, `_dat_tong_dinh_danh` trong cap_nhat; tổ chức: "Tổ chức:", ẩn CCCD); tên thẻ mục
    "1. Đất (n · 1,4 triệu)" (`vn_gon`); BangMuc chọn TỪNG Ô (SelectItems + Extended; `cac_dong_chon` = dòng của mọi ô chọn), dòng
    `CAO_DONG_MUC` 36, số / tiền phông `PHONG_SO` Consolas (`_phong_so` nhớ theo cỡ chữ), dải chân `dai_cong_muc` (`lb_dem` "Tổng số: nn
    hạng mục · Ctrl+C…" + `lb_tong` "CỘNG MỤC k (TÊN): … đồng" - mọi mục, kể cả mục 1), `vua_tieu_de` (tiêu đề 2 dòng không cắt);
    HangNhapNhanh `CAO_HANG` 29. QSS `QSS_LAP_PA_DAI` (giao_dien, QSS chung).
  - Bảng tổng hợp kinh phí: `kinh_phi_du_an.co_cau(con, chi_tiet_dat=False)` - mọi dòng có `stt` (I-V nhóm, ★ cộng, VI kinh phí, - phân
    bổ) + `can_cu` (`CAN_CU_CO_CAU` mặc định, hồ sơ địa phương `can_cu_phap_ly.co_cau` {"1": …} ghi đè - `can_cu_co_cau()`); dòng phân bổ có
    `ten_phan_bo` / `ty_le_phan_bo`; `chi_tiet_dat=True` (chỉ màn hình: `KhungBangTongHop._lay_cc`) chèn dòng 'nhom_con' sau nhóm I theo
    `NHOM_DAT_CON` (đất ở / nông nghiệp / khác - `tien_dat_theo_nhom` từ `doc_tat_ca_phuong_an` + `thanh_tien_dong_dat`). Mặc định KHÔNG có
    nhom_con (test / tu-kiem đếm loại dòng). `danh_gia_chenh(kt, tt)` ("Tiết kiệm x%" / "Trong hạn mức" / "Tăng x%"), `ket_luan_doi_soat(ss)`.
    `KhungCoCau.COT` 9 cột (STT, Khoản mục…, căn cứ pháp lý áp dụng; `C_TEN` / `C_CHENH` / `C_TY_LE`), `KhungDoiSoat` cột "Đánh giá",
    `KhungAnToanVon` (thẻ 1 bên phải: `KhungBangTongHop.the_1` QSplitter 7:3 cơ cấu | an toàn nguồn vốn; tóm tắt từ `doi_soat.ss`, nút "Xem
    đối soát chi tiết" -> thẻ 3; `_nap_the(0)` nạp luôn doi_soat). 5 KPI `cong / kinh_phi / pb_0 / pb_1 / tong` (tên thẻ phân bổ theo
    `dia_phuong.phan_bo_kinh_phi` - mặc định "UBND cấp xã nơi có đất thu hồi", KHÔNG ghi "cơ quan thẩm định" như ảnh mẫu); số tiền một
    mình một hàng (chữ phụ -> chú thích: 5 thẻ ở 1366 cắt số); `lb_chan` "Cập nhật số liệu tự động… Lần tính toán gần nhất". `bang_ao`
    kiểu ô `can_giua`. `giao_dien.dat_the_nho(lb, loai)` (thẻ nhỏ QLabel[the_nho]); `QSS_TONG_HOP_KP`.
  - Tiến độ: `DaiKPI` 6 thẻ `tong_ho / phe_duyet / giai_ngan (Đã chi trả) / mat_bang (Đã bàn giao) / van_dong / cuong_che` - số "n hộ (x%)"
    trên TỔNG số hộ, `dat(tq, so_ngay, so_dang_vd)`; thẻ "Thửa còn vướng" bỏ (nút chế độ vẫn có); `_TheKPI` tối thiểu 118, tiêu đề
    NhanRutGon, số 16px. `KPI_LOC` mới; `the_kpi_dang_loc` bỏ thẻ lọc '' (xem tất cả: không thẻ nào đánh dấu). `van_dong.danh_gia_cuong_che(x,
    buoi, n, hom_nay, moc_ho)` -> {du, dong [(đạt, chữ)] 4 điều kiện: có QĐ, buổi đầu quá hạn, đủ mốc thông báo thu hồi (moc None = chưa
    kiểm được), hộ vẫn chưa nhận tiền / chưa bàn giao; ket_luan, can_cu} - CHỈ HIỆN, không chặn; "Điều 89" (khoản cụ thể CHƯA đối chiếu).
    `KhungSoVanDong` (bên phải bảng, `KhungTienDo.tach_vd` 8:3, không thu gập - nút mở sổ ở trong): thông tin hộ, dòng thời gian buổi vận
    động, `lb_kl` (`chu_ket_luan_cuong_che`, property du), `b_mo` = `nut['Sổ nhật ký vận động…']` (đã bỏ khỏi chân trang - một chỗ);
    `_doi_ho_chon` theo selectionModel của bảng hộ / thửa. `HopNhatKyVanDong.lb_kl` cùng ô kết luận.
  - Trung tâm xuất bản `HopIn`: `the_che_do` (QTabBar 2 thẻ `THE_CHE_DO`) <-> `r_du_thao` / `r_chinh_thuc` (ẨN, vẫn là nguồn che_do()),
    `lb_quy_tac` (`QUY_TAC_CHE_DO`), `khung_tai_lieu` 4 dòng ô chọn + thẻ nhỏ (`the_tai_lieu`): o_ct "Mẫu chuẩn", o_bth "Tách 85/15 QĐ 08"
    (theo phan_bo), o_tt, `o_bc` "Báo cáo tiếp thu && giải trình ý kiến (.docx)" - THÊM LẠI (đặc tả "trọn bộ 4 tài liệu"; nơi DUY NHẤT xuất
    .docx này: HopDotTrinh bỏ từ 0.9.77) -> `bao_cao_y_kien` của xuat_bo_ho_so. Dự thảo: o_tt / o_bc TẮT + bỏ chọn ("Chỉ mở ở Chính thức");
    chính thức: chọn trọn bộ (`_ap_tai_lieu`, `chon_mau` bỏ qua ô tắt). `b_thuc_hien` "Bắt đầu Xuất bản && In hàng loạt (n hộ)". KHÔNG che
    CCCD (ảnh mẫu ghi che 6 số - trái quyết định 1.0.04). Chữ "&" trên QCheckBox / QPushButton phải viết "&&" (không thì thành phím tắt "_").
    bang_ho cột 50 / 260 / 150 / 120 (trước 820 px: khung trái cuộn ngang, thẻ nhỏ khuất).
  - Bác sĩ CSDL `HopChanDoanHeThong` (tiêu đề "Bác sĩ kỹ thuật CSDL & chẩn đoán máy trạm"): trái = `CHI_SO` 5 chỉ số (`the_chi_so`,
    `chi_so()`: tệp khóa / integrity_check / foreign_key_check / lược đồ `v{PHIEN_BAN_CSDL}` THẬT (không ghi cứng v16) / Excel + QtPdf) +
    bảng máy trạm `bang` (kiem_tra_moi_truong); phải = `NUT_BAO_TRI` 4 nút một cột (`nut_bao_tri`, bật / tắt theo kết quả kiểm tra) ->
    `bao_tri(viec)` -> `chua_benh_csdl.sua_tep_pabt(f, viec=)` (`VIEC_SUA`: 'tat_ca' như cũ = `sua_file`; 'go_khoa' chỉ gỡ khóa HẾT HẠN, không
    sao lưu; 'toi_uu' REINDEX + VACUUM (trang hỏng -> LoiSuaTep); 'cuu' `_cuu_du_lieu` (file tốt -> LoiSuaTep); 'nang_cap' csdl.mo khi v < mới
    nhất) + hộp đen `#khung_hop_den` + `b_goi` (`NUT_GOI` "Xuất gói chẩn đoán ẩn danh gửi tác giả (.zip)…"). Hộp tối thiểu <= 1024 px (nhãn
    xuống dòng, nút tối thiểu 120).
  - Ảnh: `ket_qua_kiem_tra/thu_that/chup_giao_dien.py` thêm 17/18 (xuất bản dự thảo / chính thức), 19 (bác sĩ CSDL); cỡ nhỏ `--co 1093x600
    --ty-le 1.25` (~ màn hình 1366x768 @125%). Test `tests/test_giao_dien_2010.py`; đã sửa `test_yeu_cau_0977` / `test_van_ban_trinh` (chính
    thức theo đợt có BAO_CAO_TIEP_THU_Y_KIEN.docx), `test_theo_doi` (nhom_con), `test_yeu_cau_0976` / `1000` / `test_giao_dien_navy_con` (6 thẻ).
- 1.0.06 bản in chi tiết - "trang 2 mồ côi" (người dùng 20/10/2026; module người dùng nhắc `canh_trang_in_an.py` KHÔNG có
  sẵn - viết mới, KHÔNG phải bộ dàn trang thứ hai): `pabt/canh_trang_in_an.BoCanhTrangInAn` gọi trong `in_an.ngat_trang_ct` SAU
  co_gian_vua_trang, TRƯỚC tách ô gộp ghi chú / ghi ngắt tay: `tu_dong_chinh_trang(ws, trang, cap, tieu_de, dong_muc)` -> (1) `gom_mot_trang`:
  tổng nội dung tràn một trang <= `NGUONG_DU_1_TRANG_PT` 120 pt -> fitToPage 1 x 1, bỏ ngắt tay, `ws._print_rows = None` (setter
  print_title_rows của openpyxl BỎ QUA None); tràn nhiều hơn giữ 2 trang (co cả trang chữ quá nhỏ); (2) `can_bang_hai_trang`: 2 trang mà trang
  2 bắt đầu giữa mục -> ngắt trước dòng 'H' gần nhất (trang 2 vừa, trang 1 >= `TRANG_1_TOI_THIEU` 50%). `an_dong_trong_khoi_i` (gọi trong
  lap_chi_tiet sau dat_nhan_chu_su_dung): dòng "Số CCCD:" / "Số điện thoại:" trống -> ẩn (cả hộ gia đình). Lề chi tiết 0,35 / 0,35 / 0,55
  / 0,40" (`LE_TRANG` VÀ `pabt_profile.json` ban_in.le_trang - hồ sơ đóng gói ghi đè LE_TRANG). Đệm dòng bảng `DEM_DONG` 8 -> 4 pt, tối
  thiểu 24 -> 20 (VBS xuất PDF `dem` / `cmin` cùng số; NEN_DEM = DEM / 2, CAO_NEN_TOI_THIEU 19): người dùng yêu cầu +2 nhưng ĐO xuất PDF
  bằng Excel: 2 pt làm dòng chữ đầu chạm đường kẻ ô (lỗi 14/10) - chọn 4. dự án thật 170 hộ (Excel thật): 209 -> 202 trang, 7 hộ bớt trang
  (trang cuối ~32% -> gom), hộ 1 vẫn 2 trang (nội dung ~1,6 trang: mục 5 có 3 chính sách) - trang 2 bắt đầu trọn mục 5.
  Script đo: scratchpad (không trong repo). Test `tests/test_canh_trang_in_an.py`, `test_in_16_10.test_gom_mot_trang_khi_tran_it`; `_trang`
  của test_in_16_10 hết ở dòng cuối VÙNG IN (dòng trống khối chữ ký mẫu ngoài vùng in).
- 1.0.06 tìm nhanh / cảnh báo tức thời / phông số (người dùng 20/10/2026; test `tests/test_tim_nhanh_2010.py`):
  - Ctrl+K = QAction 'Tìm nhanh…' (menu Chỉnh sửa - một chỗ) -> `CuaSoChinh.tim_nhanh(cho)` -> `man_hinh_tim_nhanh.HopTimKiemNhanh(cua_so,
    im_lang)`: ô gõ + QListWidget phẳng; `ds_muc` = hộ (`mo_hinh.dong`: STT. họ tên, chữ `tim` có CCCD + tờ/thửa "12/45", CCCD đọc từ ho) +
    mọi QAction của `self.lenh` (chữ NHAN_MENU, tên đầy đủ, phím). Chưa gõ: chỉ chức năng. `Muc.diem`: 0 tên chứa TRỌN cụm gõ theo từ, 1 từ
    có chữ số khớp trọn (mã, CCCD, tờ/thửa), 2 tên bắt đầu bằng chữ gõ, 3 chỉ chứa ("Ấp 1"). Lệnh tắt: xám, không chọn được. Hộp chỉ CHỌN
    (`ket_qua()` ('ho', mã) / ('lenh', tên)); `thuc_hien_tim_nhanh` chạy SAU khi hộp đóng: lệnh = `QAction.trigger()` (lệnh tắt không chạy),
    hộ = `chon_ho_tren_danh_sach` (về Danh sách hộ, bỏ lọc nếu hộ bị lọc ẩn, chọn + cuộn) rồi `mo_chi_tiet` (như bấm đúp).
  - Phím số `app.PHIM_NHANH`: Ctrl+1 Danh sách hộ, Ctrl+2 Khái toán & Dự toán, Ctrl+3 'Bộ đơn giá…' (tab Đơn giá bồi thường), Ctrl+4 'Dự
    thảo PABT…' (tab Niêm yết & Lấy ý kiến), Ctrl+5 Tiến độ & Bàn giao; Tổng hợp tiền / Quyết định phê duyệt KHÔNG còn phím số (menu trái /
    Ctrl+K). Mọi QAction có phím trong PHIM_NHANH gắn `self.addAction` (chạy cả khi menu chưa mở). Đừng gán lại Ctrl+i theo thứ tự TRANG.
  - Cảnh báo tức thời KHÔNG chặn, màu hổ phách một nguồn `giao_dien.MAU_CANH_BAO_NEN / _VIEN / _CHU`, `kieu_o_canh_bao(it, chu)`,
    `qss_canh_bao(loai)`: mục 1 `BoSoan.canh_bao_dien_tich(i)` (tổng DT mục 1 của thửa ở MỌI lần > DT thu hồi; DT dòng > `thua.dt_nguyen_thua`)
    -> `BangMuc._ve_dong` tô ô DT + chú thích, `CuaSoLapPA.sua_o` nối "Cần xem lại diện tích: …" vào `lb_tb` và vẽ lại mọi dòng cùng thửa.
    KhungHoSo DT còn lại âm: chữ nâu + nền hổ phách (trước đỏ). `HopBanGiao`: `lb_nhac_ngay` (`NHAC_NGAY_BAN_GIAO`, nêu Điều 89 - khoản cụ
    thể CHƯA đối chiếu) + viền ô ngày hiện NGAY khi tích mà trống ngày (`thieu_ngay`, `_nhac_ngay`); `accept` vẫn chặn như 17/10.
  - Phông số MỘT nguồn ở `giao_dien`: `PHONG_SO` Consolas + `PHONG_SO_DU_PHONG` Segoe UI Semibold (`setFamilies`), `phong_so(goc=None, dam)`
    nhớ theo `QFont.key()` (Phóng to / Thu nhỏ tự dựng lại), `mau_so(chu, tien, vuot)` (0 / gạch `MAU_SO_KHONG` #94A3B8, tiền `MAU_SO_TIEN`
    #0F3866, vượt `MAU_SO_VUOT` #B91C1C), `but_so`, `kieu_o_so(it, tien, vuot, goc, dam)`, `SO_KHONG`, `CAN_SO`. Dùng ở BangHo (cột DT),
    BangAo (FontRole mọi cột `can_phai`; `bang_ao.MAU_SO_KHONG / SO_KHONG` nhập lại từ giao_dien), BangMuc (`_phong_so` + màu), KhungDuToan
    (`_ve_dong`, bảng so sánh: chênh dương đỏ). Gán theo ô / vai trò mô hình - KHÔNG setStyleSheet khung chứa.
  - Ảnh: `chup_giao_dien.py` thêm 20 / 20b (Tìm nhanh), 21 (cảnh báo DT mục 1).
- 1.0.07 (người dùng 20/10/2026, hai bản đặc tả "Hội đồng chuyên gia" 5 + 6 giai đoạn; test `tests/test_yeu_cau_1007.py`):
  - MẪU NHÚNG: `tao_mau_nhung.py` (gốc repo) -> `pabt/mau_in_nhung.py` (TỰ SINH: zlib 9 + Base64, `BYTES_MAU_CHI_TIET / _DU_THAO /
    _TONG_HOP`, `XML_DUONG_KE_CT / _BTH`, `SHA256`, `lay_bytes_mau`, `lay_duong_ke`, `co_mau`). Sửa mẫu chuẩn mau_in\ -> CHẠY LẠI script
    (`TestMauNhung.test_ban_nhung_khop_file_mau` báo lệch). `in_an.thu_muc_mau(ten)` không thấy file nào -> `THU_MUC_NHUNG` (thư mục ẢO
    `pabt/_mau_in_nhung`, KHÔNG tạo trên đĩa): `la_mau_nhung`, `nap_mau_bytes` / `_doc_dk` lấy bytes trong RAM, `duong_ke_cua_mau` không
    ghi đĩa, `mau_de_sua` / `_nhan_mau_mac_dinh` / `goi_mau.ds_mau_hien_hanh` ghi bản nhúng ra (`ghi_mau_nhung`). `PABT_CHI_MAU_NHUNG=1`
    = giả lập máy trắng. PABT.spec / dung_exe38 hidden-import `pabt.mau_in_nhung`.
  - Mẫu tùy chỉnh: `in_an.thu_muc_mau_tuy_chinh()` (bản cài %APPDATA%\PABT\mau_in; mã nguồn / kiểm thử <thư mục máy>\mau_in - từ 1.0.07
    `thu_muc_mau` mã nguồn đọc ở đây TRƯỚC mau_in\ của repo). Hộp `man_hinh_quan_ly_mau.HopQuanLyMauIn` (lệnh 'Quản lý Mẫu in & Bản in…',
    Ctrl+Shift+M, menu Công cụ - thay lệnh "Cập nhật mẫu in…" + hàm `cap_nhat_mau_in`, đã bỏ): `MAU_QUAN_LY` (IN_CHITIET,
    `TEN_DT_QL` 'IN_CHITIET__Du thao', IN_BANGTONGHOP), `trang_thai_mau` (NHUNG / TUY_CHINH - so SHA-256 với bản nhúng), `thay_mau`
    (tao_mau_tu_excel ở thư mục tạm -> `ap_chuan_trang_mau` (đường kẻ lưu .duong_ke.xml TRƯỚC khi openpyxl ghi lại) -> mẫu cũ `_sao_luu_mau`
    vào cu\ -> `xoa_bo_nho_mau`), `xuat_mau`, `khoi_phuc_mau`. Mẫu dự thảo tùy chỉnh: `lap_chi_tiet(mau=None, du_thao=True)` dùng nó; chưa
    thay thì như 0.9.82 (mẫu chính + chữ DỰ THẢO). openpyxl `load_workbook(read_only=True)` GIỮ file mở tới khi `close()`.
  - Phương án chi tiết: A4 dọc, tỷ lệ cố định `TI_LE_CT` 72 (`dat_ti_le_co_dinh` trong `ngat_trang_ct`; bảng rộng hơn khổ in mới nhỏ hơn),
    lề `LE_TRANG['chi_tiet']` 0,8 / 0,3 / 1,0 / 0,8 cm (`CM`; pabt_profile.json ban_in.le_trang ghi đè - đã sửa cùng số). Gom 1 trang
    (`canh_trang_in_an.gom_mot_trang`): KHÔNG còn fitToPage - thu `scale` (>= `TI_LE_CT_MIN` 70) cho vừa, không vừa thì giữ 2 trang.
    `chuan_co_chu_ct` (ô đậm phía trên mục I, tiêu đề mục `_RE_TIEU_DE_MUC`, hàng tiêu đề bảng -> `CO_TIEU_DE` 16 đậm; còn lại `CO_NOI_DUNG`
    14), `vua_cot_theo_tieu_de` ("STT" 16 pt không vỡ - bớt cột Ghi chú), `chuan_muc_i` (mục I: bỏ viền, nhãn "…:" đậm / nội dung thường,
    ô {cccd} {dien_thoai} '@' + `chen_duong_ke(bo_qua=)` -> `<ignoredErrors numberStoredAsText>` - openpyxl không ghi phần này), cột Ghi chú
    `CO_GHI_CHU_CT` 11,5 (số dòng quy về cỡ 14 khi tính cao), `vua_cao_chu` phần đầu + dòng tiêu đề mục, `TIEU_DE_MUC_II` có ":", nguồn gốc
    `SO_NBSP_NGUON_GOC` 8 (hồ sơ thut_dau_nbsp 8) + bỏ khoảng trắng đầu đoạn. Dự thảo: `an_khoi_ky` (ẩn từ dòng chức danh `_RE_CHUC_DANH_KY`
    xuống cuối). GIỮ `CAO_DOAN_TOI_DA` 90 pt (đặc tả ghi 300 - 90 ngắt trang tốt hơn, đã có từ 16/10).
  - Bảng tổng hợp: A3 ngang `KHO_GIAY_BTH` 8, `TI_LE_BTH` 55 (`dat_kho_a3`, `chuan_co_chu_bth`: trên dòng dữ liệu đầu ô đậm 16 / thường 14,
    từ dòng dữ liệu 14; mẫu chữ to (20 pt cũ) thu cột + dòng theo 14 / cỡ cũ), `vua_ngang_a3_bth` (cột số đủ số lớn nhất, cột chữ co / giãn
    vừa `rong_in_a3`, không dưới từ dài nhất tiêu đề (`vua_cot_theo_tieu_de`) / nửa bề rộng cũ), `vua_cao_chu` tiêu đề, `ngat_trang_bth(
    ti_le=)` -> `dat_ti_le_co_dinh` (min(55, vừa ngang) - số quá lớn / phông offscreen thì nhỏ hơn). Tên `TEN_GIU_TI_LE` 'PABT_GIU_TI_LE' =
    tỷ lệ tối thiểu VBS được thu khi Excel tự ngắt trang (chi tiết 70, tổng hợp `TI_LE_BTH_MIN` 50). Phông offscreen rộng ~2 lần: test
    offscreen của bảng tổng hợp chạy ở ~32-40%; số đo thật xem bằng QT_QPA_PLATFORM=windows + Excel xuất PDF.
  - Màn hình chính khi ĐÃ mở dự án = tổng quan (`man_hinh_tong_quan.KhungTongQuanDuAn`, số liệu `tong_quan_du_an` không Qt): `app.ngan_chao`
    (ô 0 màn hình chào `_trang_chao_bat_dau`, ô 1 `self.tong_quan` tạo khi cần - `_nap_tong_quan`, gọi cuối `_nap_gan_day` khi trang =
    TRANG_CHAO). Thẻ khởi tạo = QAction (`the_khoi_tao` - test_khong_trung_lenh cho phép như nut_chao), `HangKpi` 4 thẻ, bảng hộ chưa phê duyệt
    (tối đa `HO_DANG_LAM_TOI_DA`, nút "Lập PA →" -> `mo_ho` -> mo_lap_pa), đồng hồ pháp lý (đợt niêm yết còn n ngày, V1-V5, vận động /
    cưỡng chế qua theo_doi.tong_hop - "Điều 87 / 89" theo lời người dùng, CHƯA đối chiếu khoản).
  - Bảng (`giao_dien.cho_phep_sao_chep_bang` - mọi bảng qua ap_kieu_cay; BangAo tự gọi): `cuon_muot` (ScrollPerPixel, `BUOC_CUON` 20),
    `gan_enter_xuong` (closeEditor SubmitModelCache -> `o_duoi`; `nhap_bang_phim` cũng vậy - TRƯỚC 1.0.07 Enter sang ô kế bên phải, `o_ke`
    đã bỏ), Ctrl+D `dien_xuong` (trong `_BoSaoChep`, không khi đang sửa ô). Hộp thoại pabt cao hơn vùng làm việc: `cuon_than_hop` (ở Show
    trong _BoToMau; thân -> QScrollArea #than_cuon_hop thanh 6 px, hàng nút cuối giữ ngoài; chỉ bố cục dọc có hàng nút ở cuối) - offscreen
    KHÔNG tự bọc (`_nen_cuon_hop`, PABT_CUON_HOP=1 để thử). `ThongBaoNoiHUD` / `thong_bao_noi(cửa sổ, chữ, loai)` góc dưới phải (Ctrl+S
    `luu_du_an_lenh`, Ctrl+Z / Y `hoan_tac` của cửa sổ chính và CuaSoLapPA).
  - Test cũ sửa theo: test_in_vua_chu (16 pt), test_yeu_cau_1004 (8 NBSP), test_in_16_10 (dò mốc trang rộng hơn; gom 1 trang offscreen ngưỡng
    400), test_khong_trung_lenh (thẻ tổng quan). `test_giao_dien.test_bieu_tuong_duy_nhat_co_vien` lỗi vì `logo_PABT.png` (file của người dùng,
    chưa theo dõi git) lại nằm ở gốc repo - không phải lỗi mã.
- 1.0.08 (người dùng 20/10/2026, máy cấu hình yếu; test `tests/test_yeu_cau_1008.py`):
  - `csdl.la_may_yeu()` (RAM vật lý `ram_vat_ly_mb` qua GlobalMemoryStatusEx < `NGUONG_RAM_MAY_YEU_MB` 4200 hoặc cpu_count <= 2; nhớ trong
    tiến trình `_MAY_YEU`; PABT_MAY_YEU=1 / 0 ép), giao_dien xuất lại tên. Máy yếu: `do_bong` không bật dù PABT_HIEU_UNG_BONG=1; `ocr._chay`
    env `moi_truong_ocr()` (OMP_THREAD_LIMIT `LUONG_OCR_MAY_YEU` '1'); xem trước `xem_truoc_tai_lieu.he_so_xem_toi_da()` (QPdfView: phóng / vừa
    trang không quá `DPI_XEM_MAY_YEU` 120 dpi; `_TrangAnh` cũng chặn) - in vẫn DPI_IN_TOI_DA; `csdl.giai_phong_bo_nho()` (gc.collect CHỈ máy
    yếu, `luon=True` ép) sau CuaSoLapPA.done / closeEvent (QTimer 0), cuối `in_an.xuat_hang_loat`, `van_ban_trinh.xuat_bo_ho_so`.
  - A+ / A−: chi phí là `app.setStyleSheet` áp lại MỌI widget còn sống (~1,2 ms / widget, cả trang ẩn - không hoãn được trong Qt). Nay
    `giao_dien.TRUOC_DOI_TY_LE` (hàm gọi trước khi áp kiểu, rồi sendPostedEvents DeferredDelete) -> `CuaSoChinh._bo_trang_an`: bỏ khung
    khung_trang không đang xem (tạo lại ở `_dam_bao_trang`) và tab phụ ẩn không có thay đổi chưa lưu (khung_tab.bo; lệnh mở tạo lại). GIỮ
    danh sách hộ, Khái toán, tab hộ sửa dở. 300 hộ / 1.331 widget: 1,70 -> ~0,46 - 0,52 s mỗi nấc (offscreen).
  - Kéo thả: `CuaSoChinh.setAcceptDrops(True)`, `_file_keo` (đuôi `DUOI_KEO_THA`), dropEvent -> QTimer 0 -> `mo_file_keo(p)` (mo /
    cap_nhat_phan_mem / nhap_goi_mau / nhap_excel qua `_chay_lenh`).
  - Sao lưu tự động: `csdl.sao_luu_tu_dong(con, file)` - `con.backup` trên CHÍNH kết nối đang mở (kết nối thứ hai đọc sẽ giữ khóa SHARED,
    journal DELETE làm lần ghi của phần mềm báo "database is locked"), ghi .tmp + os.replace, tên `<stem>_<sha1 đường dẫn 6>_<giờ><đuôi>`
    ở `<thư mục máy>\sao_luu_tu_dong`, giữ `SAO_LUU_GIU` 5; bỏ qua khi in_transaction / file nằm sẵn trong thư mục đó. `app.mo` (không chỉ
    xem) hẹn `SAO_LUU_SAU_MS` 1500 ms -> `_sao_luu_tu_dong` (lỗi chỉ báo thanh trạng thái).
  - `in_an.ap_chuan_trang_mau` áp cả cỡ chữ (`chuan_co_chu_ct` / `chuan_co_chu_bth`). `logo_PABT.png` ở gốc repo (làm hỏng test biểu tượng)
    đã đưa vào Thùng rác theo yêu cầu người dùng.
- 1.0.09 (người dùng 20/10/2026: "máy cá nhân khác xem trước / in chi tiết mất toàn bộ khung bảng mục III, Tỷ lệ 0,8, Đơn giá
  720000"; test `tests/test_yeu_cau_1008.TestKhungBangMucIII`): NGUYÊN NHÂN = mẫu IN_CHITIET cũ trong thư mục máy (%APPDATA%\PABT\mau_in -
  thường từ file Excel PABT: khung / định dạng số do định dạng có điều kiện hoặc dòng mẫu dưới STT không viền + General); PDF dự phòng
  (máy không Excel) không đọc định dạng có điều kiện. Đã tái hiện (mẫu chuẩn: đủ khung). Sửa: `in_an.dam_bao_khung_bang_ct(ws, dòng
  STT, dòng TỔNG CỘNG, cot, loai_dong)` gọi CUỐI `lap_chi_tiet` (sau ngat_trang_ct): viền thin mọi ô, hàng tiêu đề trên / dưới medium, bao
  ngoài medium; ô số mất định dạng -> `DINH_DANG_TIEN_CT` '#,##0' / `DINH_DANG_TY_LE_CT` '0%' / số lượng General -> dinh_dang_so_luong (giữ
  định dạng có sẵn như '[=0]0;[<10]0.0##;#,##0'). Ô gộp: Excel / openpyxl chỉ giữ CẠNH NGOÀI vùng gộp (test kiểm theo vùng gộp).
  `chuan_muc_i`: chặn xóa viền tại dòng STT (`min(r_ii, den_dong)` - mẫu thiếu dòng "II." trước đây xóa tới I + 6). Mẫu thư mục máy:
  `dung_mau_may(file, ten)` (nhớ theo mtime / cỡ) = người dùng thay qua HopQuanLyMauIn (`FILE_DANH_DAU_MAU` '.quan_ly_mau.json' {tên:
  SHA-256} - `ghi_danh_dau_mau` ở thay_mau / khoi_phuc_mau) HOẶC `mau_bang_hop_le` (dòng dưới STT >= 6 / 8 ô có viền + Thành tiền không
  General; mẫu bảng tổng hợp luôn hợp lệ); không -> `thu_muc_mau` bỏ qua (cả nhánh PABT_CHI_MAU_NHUNG và mẫu dự thảo riêng). Gói .pabtcfg /
  mau_de_sua không ghi dấu: mẫu đủ khung vẫn dùng. `pdf_du_phong`: `_chuan_bang_qt` (QTextTableFormat cellSpacing 0, border 0, borderCollapse,
  bút đen - KHÔNG border="1" cả bảng: cả trang là MỘT bảng HTML, lưới sẽ trùm quốc hiệu / mục I), khung = CSS viền từng ô (Qt 5.14+ vẽ;
  test đếm leftBorder ô cả Qt5), `_chu_trang` (rgb FFFFFF / theme 0 - ô {ma_ho} chữ màu nền, trước hiện "2" dưới dòng dự án).
  Cùng 1.0.09 (người dùng: "nhập thêm hộ - chỉ tài sản, không tờ thửa - nhưng dự án không cập nhật hộ đó"): lõi (ho_so.luu_ho,
  nhap_chi_tiet.ghi, nhap_tho) ĐỀU tạo hộ không thửa; lỗi là giao diện - CuaSoLapPA nhúng tab, danh sách hộ chỉ tải lại khi ĐÓNG cửa sổ
  hộ (`_tab_dong`; tham số `truoc` của mo_lap_pa không dùng). `CuaSoChinh._tai_lai_neu_doi` (so `con.total_changes` với `_tc_nap` đặt cuối
  `tai_lai`) gọi đầu `mo_trang` (trừ Dự toán) và `ve_trang_chu`. Nhập chi tiết: hộ TRÙNG họ tên / CCCD mặc định 'bo_qua' (báo trong hộp kết
  quả) - chọn "thêm thành hộ mới" nếu là hộ khác. Test `test_yeu_cau_1008.TestThemHoCapNhatDanhSach`.
- 1.0.10 Dán tài sản - kích thước = diện tích (người dùng 20/10/2026; test `tests/test_hieu_tai_san.TestKichThuocDienTich`):
  `hieu_tai_san._RE_KICH_THUOC` (phần 'kt' của `_PHAN`, trước 'sl'): "4,7x3,0" / "4,7*3,0" / "3,7m x 4,3m" / "3,7mx4,3m" / "3,7 x 4,3 m2"
  -> số lượng = phép tính (dấu nhân như người gõ; doc_danh_sach tính 15,91, giữ `cong_thuc`), ĐVT m2 (không ghi đơn vị: `dvt_ngam` - tên
  có đơn vị cuối "Nhà tạm m2 4x5" / cột ĐVT thắng); ba thừa số hoặc đơn vị khác sau ("2x3x1,5 m3", "3x4 cây") để quy tắc số lượng cũ.
  Phần 'ngoac' "42m2 (thửa 123)": ngoặc SAU số liệu -> ghi chú (ngoặc trong tên giữ). `_RE_TU_NHIEN` nhận "số x số"; `tach_dong` không tách
  ở số đứng sau toán tử / số ("Sân m2 3+2*4" vẫn đi quy tắc cũ). Ô Excel: `doc_kich_thuoc(o)` ("3,7m x 4,3m", "42m2").
- 1.0.11 Chọn vùng ô + bộ đếm kiểu Excel (người dùng 21/10/2026, kèm ảnh mẫu; test `tests/test_yeu_cau_2110.py`):
  - `giao_dien.cho_phep_sao_chep_bang` (mọi bảng qua `ap_kieu_cay`, `BangAo.__init__`, `app.bang` trong `__init__`) -> `cho_chon_vung_o`
    (SelectItems + ExtendedSelection; NoSelection giữ; bảng SingleSelection cũng thành Extended khi hiện - trước khi hiện vẫn kiểu cũ: Qt
    `selectRow` KHÔNG chạy với SingleSelection + SelectItems) + `gan_bo_dem` -> `_BoChonVung` (con của bảng): bấm ô cột STT chọn cả dòng
    (Ctrl / Shift), `_VienVungChon` (viền xanh lá quanh từng vùng chọn - con của BẢNG phủ viewport, không phải con viewport:
    viewport.scroll dời widget con), bộ đếm. Lệnh theo hộ đọc dòng bằng `giao_dien.cac_dong_da_chon(bang, hien_tai=True)` (dòng có ô
    chọn; trống -> dòng ô hiện tại; hien_tai=False cho lệnh "không chọn thì cả đợt") - ĐỪNG dùng `selectedRows()` (chỉ dòng chọn trọn).
  - `thong_ke_vung_chon(bang)` -> so_dem / so_so / tong / trung_binh (Decimal) / so_le / chuoi ("Trung bình: …     Tổng số đếm: n     Tổng:
    …"; dưới 2 ô có chữ: ''): `doc_so_o` (tien.doc_so_vn, bỏ hậu tố đ / đồng / m² / ha / % / cây / hộ / thửa, '-' = 0), cột định danh
    `COT_DINH_DANH` / `TU_DAU_DINH_DANH` hoặc property `cot_dinh_danh` = [cột] chỉ đếm không cộng ("Số thửa" của danh sách hộ là SỐ
    LƯỢNG - cộng), ô gộp một lần (`_goc_gop` theo visualRect), `so_bo_dem` giữ số chữ số lẻ của dữ liệu ("1.128,0"). Cửa sổ có hàm
    `cap_nhat_bo_dem(bang, tk)` tự hiện (CuaSoChinh: `lb_bo_dem_excel` = `NhanBoDem` trái A− / A+, chỉ bảng đang hiện, đổi trang xóa -
    `_xoa_bo_dem_neu_an`; HopThongKeDiaChinh: góc dưới trái); hộp khác: `NhanBoDem` nổi góc dưới phải BẢNG (không đè hàng nút của hộp).
    Bấm nhãn = chép Tổng + thong_bao_noi.
  - Thẻ KPI: `the_phu` = huy hiệu (% số hộ; Tổng kinh phí: tổng ha - property co ''/'1'/'ha'), `the_don_vi` (hộ / VNĐ), `the_dia_chinh`
    (rich text "n thửa" / "dt m²") theo `app.nhom_dia_chinh(dong, lap)`; dòng BangHo có `so_thua` (`so_thua_dong`, `dia_chinh`, `so_ha`).
    `lb_loc` = NhanBam "Lọc: k/N hộ · t thửa ↗" -> QAction `LENH_THONG_KE` 'Thống kê Hộ · Thửa · Diện tích…' (Ctrl+Shift+T, menu Dữ liệu,
    LENH_CAN_DU_AN) -> `man_hinh_thong_ke.HopThongKeDiaChinh(dong, ten_dot, ten, parent, im_lang, lap)` (7 trạng thái `thong_ke_trang_thai`,
    đợt `thong_ke_dot`, "Sao chép tóm tắt báo cáo"). Dải cộng "CỘNG (n HỘ · t THỬA) | Tổng DT: … m² (… ha) | Đất | Tài sản & Cây | HT &
    Thưởng | TỔNG CỘNG"; `lb_tom_tat` "Sẵn sàng · Dự án: N hộ · T thửa · DT m² | Đang chọn: k hộ (t thửa · dt m²)".
- 1.0.11 Trang 1 bản in chi tiết không hở (người dùng 21/10/2026: ngắt ngay sau 1.1, mục 2-6 dồn sang trang 2; test
  `tests/test_trang_1_khong_ho.py` - đo chữ cố định như test_in_vua_chu): `ngat_trang_ct` dòng 'H' chỉ dính dòng kế khi đó là 'I' (mục
  không dòng con = 'tu_do' - trước ghép "mục 2 + mục 3"…); cụm cuối 'lien' từ TỔNG CỘNG tới HẾT VÙNG IN (vùng in thừa một dòng sau chữ
  ký), chỉ khi TỔNG CỘNG rơi đầu trang cuối mới kèm dòng trước (thưởng); `dong_muc` của canh trang gồm 'R'. `canh_trang_in_an`:
  `TRANG_1_TOI_THIEU` 0,5 -> 0,85, `NGUONG_DU_1_TRANG_PT` 120 -> 160, `gom_mot_trang(dong_nen, san, san_khoi)`: chỉ thu tỷ lệ chưa đủ
  thì `thay_nen_gom` (dòng bảng = chữ + `DEM_GOM` 2,5 pt, >= CAO_NEN_TOI_THIEU) + tỷ lệ >= 70%, `_dat_ten_vbs(ws, True, DEM_GOM)` (VBS
  PABT_DEM_DONG = 25); `tong_noi_dung` tới hết vùng in. Ẩn chữ ký dự thảo / dòng trống mục I vốn đã TRƯỚC ngat_trang_ct. Đã xuất PDF bằng
  Excel: đệm 2,5 pt chữ không chạm viền. Còn lại (không thuộc lỗi này): nguồn gốc dài làm cụm "III." + tiêu đề + 1.1 (ghi chú dài) sang
  trang 2 thì trang 1 có thể ~78-85% - bản Word (dưới) cắt được dòng qua trang.
- 1.0.11 Bảng tổng hợp A3 + bản Word chi tiết (người dùng 21/10/2026; test `tests/test_in_an_2110.py`):
  - Cột số toàn 0 (`COT_THU_BTH`, `tong_cot_bth`) -> `thu_cot_khong_bth`: thu tới `RONG_COT_KHONG_BTH` 7 nhưng không hẹp hơn số 0 dòng tổng
    (`_rong_can_so`), từ dài nhất tiêu đề x `HE_SO_TU_TIEU_DE` (rong_td - không bẻ từ), không thêm dòng chữ tiêu đề; phần thu được cộng HẾT
    vào cột nguồn gốc, trả lại phần nhích do làm tròn px (tỷ lệ in giữ 55). Gọi sau vua_ngang_a3_bth, trước vua_cao_chu.
  - KẾ HOẠCH DÒNG trong `lap_bang_tong_hop`: nội dung từng hộ / thửa tính trước (`_tien_ho_bth`, `_dt_thua_bth`), chữ riêng thửa / chữ
    gộp hộ cao hơn `CAO_KHOI_BTH` 180 pt chia nhiều dòng Excel gộp ô, cấp phát dòng MỘT lần (_doi_dong từng hộ là O(n²)). Trước đây
    dòng thửa vượt 409 pt bị Excel chặn - mất chữ (`cao_dong_bang(..., None)` để không chặn khi tính). `_vua_cao_ho_bth(nhom=)`.
  - `ngat_trang_bth`: MỖI DÒNG là đơn vị tự do (bỏ 'lien' theo hộ, bỏ HO_LON); ngắt giữa hộ -> tach_ho (lặp STT / họ tên, chia
    chữ nguồn gốc). Chữ ký liền dòng TỔNG CỘNG cuối (`r_tc`); kéo dòng hộ vào trang cuối chỉ khi trang trước vẫn >= `TRANG_DAY` 85%.
    Nén khít bảng tổng hợp gần như không còn bớt trang (trang đã sát) - test_in_16_10.test_bth_nen_khit_bot_trang đổi thành kiểm 85%.
    KHÔNG bật fitToWidth / fitToPage (Excel bỏ ngắt tay): bề ngang vừa A3 nhờ tỷ lệ cố định (dat_ti_le_co_dinh) như cũ.
  - `pabt/in_word.py` `xuat_chi_tiet_docx(con, ma_ho, file, bc, du_thao, pa, lan)`: XML thuần qua `van_ban_trinh._goi_docx(than, sect)`
    (KHÔNG python-docx - không có trong môi trường / bộ cài): A4, lề `LE_MM` 30/15/20/20 mm, bảng mục III tblHeader, cantSplit 0 cho
    dòng chữ dài (`DAI_CHO_TACH`), 1 cho đề mục / thưởng / TỔNG CỘNG / IV / chữ ký (+ keepNext), ghi chú mục 1 trùng gộp vMerge. Cùng
    số liệu với lap_chi_tiet (dong_chi_tiet, _thong_tin_ho, lần PA, dự thảo: "(DỰ THẢO)", không chữ ký). ~6 ms / hộ.
    `xuat_bo_ho_so(chi_tiet_word=)`: lưu .docx cạnh .xlsx, PDF / in lấy từ bản Word (Excel chi tiết vào kq['excel'] sau bước PDF).
    HopIn `o_word` "Xuất bản Word (.docx) chuẩn Nghị định 30" (dưới o_ct, chỉ bật khi o_ct). PABT.spec / dung_exe38 hidden-import.
  - Tốc độ (phân tích phiên bản 1.0.11: bảng tổng hợp 3.000 hộ 5,5 -> 21,6 s): tach_ho mỗi ranh trang dò vùng gộp từng cột qua
    `_vung_tron` không chỉ mục + `ws.unmerge_cells` (openpyxl kiểm "đã gộp" bằng duyệt ~20.000 vùng). Nay `in_an._bo_gop(ws, m)` (bỏ
    thẳng khỏi tập ranges + ô MergedCell) và tach_ho dựng chỉ mục vùng phủ dòng e MỘT lượt -> 5,8 s, file ra giống hệt (so từng ô,
    vùng gộp, cao dòng, ngắt trang). ĐỪNG gọi `ws.unmerge_cells` / `_vung_tron` không chỉ mục trong vòng lặp trên bảng tổng hợp.
  - Lô Word (người dùng 21/10/2026, "1.000 hộ không thao tác tay"): HopIn `o_word` TÍCH SẴN, nhớ ở QSettings `KHOA_WORD_CT`
    'in_an/dung_word_chi_tiet' qua `giao_dien.cai_dat_nho()` (offscreen -> None: kiểm thử không ghi máy thật; `doc_bool` đọc 'true'
    của Qt5). Mã chạy Word ở `van_ban_trinh` (không phải in_word / in_an): `chay_word(viec, cho_moi_file, bao)` = Popen + theo dõi "XONG"
    từng file (`_chay_word_mot_lan`, VBS có file cờ dừng - đối số 2), quá hạn -> kill + `in_an._tat_excel_tu_dong(…, 'WINWORD.EXE')`,
    BỎ QUA file đó, mở lại Word làm tiếp; `TREO_LIEN_TOI_DA` 2 lần liên tiếp không xong file nào -> bỏ phần còn lại. xuat_bo_ho_so:
    phương án chi tiết `CHO_WORD_MOI_HO` 15 s / hộ (in ra máy `CHO_WORD_IN_MOI_HO` 60), file đầu mỗi lần mở Word + `CHO_KHOI_DONG_WORD`
    45; tờ trình / báo cáo 180 s; không có Word không còn ném LoiNhap (thành dòng lỗi); hộ thiếu PDF -> `pdf_du_phong_chi_tiet` (Qt từ
    bản .xlsx cùng tên - lề theo mẫu Excel, không phải NĐ 30) -> `kq['du_phong']`, HopIn báo số hộ dự phòng. Gộp vẫn ở
    `HopIn.thuc_hien` (`in_an.gop_pdf` các PDF 'PA_*' theo thứ tự hộ). Test `tests/test_xuat_word_lo.py` (Word GIẢ LẬP = chương trình
    Python thay `_lenh_word`, đọc khổ / lề từ .docx; `TestWordThat` chạy Word thật khi có).
  - Mục II cụt chữ giữa câu + cỡ chữ NĐ 30 (người dùng 21/10/2026): nguyên nhân = xuống dòng cứng GIỮA CÂU trong dữ liệu nguồn gốc (ô
    Excel Alt+Enter, chữ dán) - bản Word mỗi "\n" một đoạn, bản Excel mỗi đoạn một dòng Excel. `ho_so.lam_sach_doan_van` (nối dòng khi
    dòng trước chưa hết câu . ; : ! ? và dòng sau không là mục `dau_dong`; dòng trống / U+2028 = đoạn mới) gọi trong
    `in_an._thong_tin_ho` TỪNG THỬA (đừng làm sạch lại chữ đã nối các thửa: đoạn cuối thửa trước không dấu chấm sẽ dính thửa sau) -
    dùng chung Word / Excel; dữ liệu đã lưu không đổi. in_word: mỗi đoạn một w:p (both, line 276 after 100, firstLine 567 / gạch đầu
    dòng left 360 hanging 360), không w:br; cỡ chữ `CO_CO_QUAN` 12 (cơ quan, quốc hiệu, số, "(DỰ THẢO)" không đậm), tiêu ngữ 13 đậm
    `w:u` (gạch đúng độ dài chữ - bỏ dòng "____"), ngày 13 nghiêng, `CO_TEN_LOAI` 14, `TRICH_YEU` "… HỖ TRỢ VÀ TÁI ĐỊNH CƯ …",
    `CO_GHI_CHU` 11,5. Excel: `in_an.chuan_trich_yeu` (lap_chi_tiet; mẫu chuẩn A4 có "&", mẫu nhúng KHÔNG sửa); `_chia_doan_van(
    toi_da_cung=)` (dat_doan_van): đoạn quá `CAO_DOAN_TOI_DA` chỉ cắt sau dấu hết câu `_RE_HET_CAU_CHAM` (. ! ? - KHÔNG ; :) ở cuối
    dòng hoặc GIỮA dòng (`_RE_CAU_GIUA_DONG`: cắt chữ, phần còn lại ngắt lại `_ngat(noi_tiep=True)` không thụt), tìm trong nửa sau
    khối, rồi câu kế tiếp tới `CAO_DOAN_CAU_TOI_DA` 180 pt (không tới trần 409: dòng Excel không cắt qua trang -> hở trang), rồi bất
    kỳ trong khối; câu dài hơn mới cắt ở ranh giới dòng. Test `tests/test_in_an_2110.TestLamSachDoanVan / TestNghiDinh30CoChu`; sửa
    theo quy tắc mới test_yeu_cau_0983, test_in_16_10 (<= 180 pt), test_ban_in_15_10 (đếm dòng có NBSP thụt đầu).
  - 22/10/2026 (người dùng): bảng tổng hợp A3 lề trái 2,0 / phải 1,0 / trên, dưới 1,5 cm (`LE_TRANG['tong_hop']` VÀ pabt_profile.json
    ban_in.le_trang.tong_hop - hồ sơ đóng gói ghi đè). `lap_day_ngang_a3_bth` (sau thu_cot_khong_bth, TRƯỚC khi tính chiều cao dòng):
    phần hụt so với vùng in ở tỷ lệ sẽ dùng (55, hoặc nhỏ hơn khi bảng vốn quá khổ) cộng 70% nguồn gốc / 15% họ tên / 15% địa chỉ
    (`CHIA_BU_NGANG_BTH`), chừa `CHUA_SAU_BTH` 3 pt; `RONG_DU_PHONG_BTH` 0,97 (ĐO bằng Excel xuất PDF: 0,99 / 0,98 -> Excel tách cột
    sang trang riêng, 4 trang thay 2; 0,975 vừa đủ) - KHÔNG đặt 100% dù người dùng yêu cầu. `dat_ti_le_co_dinh / dat_ti_le_vua_ngang(
    du_phong=)` (ngat_trang_bth dùng RONG_DU_PHONG_BTH, chi tiết giữ 0,96). `vua_cot_so_bth` chỉ đo số tổng khi dòng TỔNG CỘNG có số /
    công thức (trước: cột STT nới theo tổng các số thứ tự -> bảng quá khổ, tỷ lệ tụt 54%). `chuan_trich_yeu` cả bảng tổng hợp.
    `lam_sach_doan_van`: hết đoạn chỉ sau . ! ? (dòng kết thúc ; : mà dòng sau không phải mục -> nối), gộp khoảng trắng. PDF dự phòng
    phương án chi tiết `xuat_pdf_du_phong_qt(le_mm=)` lề NĐ 30 (`in_word.LE_MM`). Test `test_in_an_2110.TestLeA3VaLapDayNgang`.
- 1.0.12 (22/10/2026) "Ultra-Compact + UI/UX Pro Max" (người dùng; bố cục / chiều cao KHÔNG đổi): navy `TOKEN['chinh']`
  '#0F294A' (thay '#0F3866' ở MỌI file pabt/ - kể cả màu viết thẳng), rê chuột `CHINH_RE` '#1E3A5F'; chinh_nhat #EFF6FF, phu #059669
  (= `MAU_VIEN_CHON` viền vùng chọn), chu #0F172A, chu_phu #475569. Vòng focus ô nhập: thường 1px #CBD5E1, `:focus` 2px #2563EB + padding
  BỚT 1 px (3px 7px; `[nhap="1"]` 3px 9px; hàng nhập / loc_ds / o_chon_ho / o_tim_gan cùng quy tắc) - chữ không nhảy. Tiêu đề bảng ngang:
  vạch phải #1E3A5F, vạch dưới 2px #2563EB. Thẻ gạch chân chọn: chữ / vạch dưới 3px #2563EB nền trắng (thẻ thường vạch 3px trong suốt,
  padding dưới 4 px - không đổi cao). `#tong_dinh_danh` nền #FEF3C7 viền #F59E0B. Logo / biểu tượng không đổi. Test `tests/test_giao_dien_pro_max.py`.
- 1.0.13 Tiêu đề Mục I phương án chi tiết (người dùng 22/10/2026, Phương án 2): `in_an.tieu_de_muc_i(to_chuc)` =
  `TIEU_DE_MUC_I_TO_CHUC` "I. Thông tin tổ chức" / `TIEU_DE_MUC_I_HO` "I. Thông tin hộ gia đình, cá nhân" (theo `ho_so.la_to_chuc`; thay
  "I. Tổ chức và hộ gia đình, cá nhân bị thu hồi đất…" của mẫu - mẫu mau_in\ không đổi). Excel: `dat_tieu_de_muc_i(ws, dòng STT, to_chuc)`
  gọi đầu `lap_chi_tiet` TRƯỚC chuan_co_chu_ct / chuan_muc_i (chúng dò mục I theo "I. "); DÒ ô (trên "II.": bắt đầu "I.", không có thì ô
  chữ chứa từ khóa `_TU_KHOA_MUC_I` giữa dòng "Dự án" và nhãn "Họ và tên:") - không viết số dòng; in đậm. Nhãn / ẩn dòng CCCD, SĐT vẫn ở
  `dat_nhan_chu_su_dung` + `an_dong_trong_khoi_i`. Word: cùng chữ, 13 pt đậm, cách trên 120 / dưới 60 twip; tổ chức 2 dòng (Tổ chức,
  Địa chỉ), hộ 4 dòng (dòng CCCD / SĐT trống thì bỏ như bản Excel ẩn). Test `test_in_an_2110.TestTieuDeMucI`.
- 1.0.14 (người dùng 22/10/2026):
  - Bảng tổng hợp hộ nhiều thửa GỘP DỌC (thay cách lặp mỗi dòng của 1.0.04, `cot_lap_thua_bth` đã bỏ): STT / họ tên / địa chỉ / tổng /
    TĐC / ghi chú một ô cả hộ (STT căn giữa hai chiều); riêng từng dòng thửa: tờ, thửa, loại đất, diện tích, nguồn gốc (khi
    `tach_nguon_goc_theo_thua` tách được), TIỀN ĐẤT (`tien_dat_theo_thua_bth`: None - giữ ô gộp hộ - khi có dòng đất không thuộc thửa
    nào của hộ / cộng các thửa khác `kq.muc[1]`). Tài sản, cây, hỗ trợ, thưởng: ô gộp hộ (ct_khoan KHÔNG có mã thửa - không chia theo
    thửa được). Hộ vắt qua ranh trang: tach_ho lặp STT / họ tên / địa chỉ như cũ. Lề A3 2 / 1 / 1,5 cm, `RONG_DU_PHONG_BTH` 0,97 GIỮ
    (người dùng lại yêu cầu khít 100% - Excel tách cột sang trang riêng, đã đo).
  - Bản Word chi tiết: cơ quan / quốc hiệu / số 13 (`CO_CO_QUAN`), tiêu ngữ / ngày / trích yếu / dự án / nội dung / bảng / ghi chú / chữ
    ký 14 (`CO_CHU`, `CO_BANG`, `CO_GHI_CHU`), tên loại 15; Mục II `DONG_DOAN` 240 + `SAU_DOAN` 120 (6 pt); tiêu đề Mục III bỏ keepNext.
    Đo Times New Roman (Word xuất PDF): quốc hiệu 13 đậm ~269 pt -> cột `TY_LE_COT_QUOC_HIEU` 61% (59% vẫn "VIỆT / NAM"), dòng tên cơ quan
    dài hơn cột -> `_ngat_can_bang` (hai dòng cân nhau, ước bề rộng `_rong_uoc` - không cần Qt); trích yếu 14 đậm ~480 pt > vùng chữ 468
    -> `TRICH_YEU_DONG` hai dòng; bảng 14 pt: `TY_LE_COT` phần nghìn (70, 205, 75, 100, 145, 80, 185, 140), lề ô `LE_O` 2 pt - "STT",
    "ĐVT", "25.000.000", "1.234.567.890" một dòng. KHỐI CHỮ KÝ = DÒNG CUỐI của bảng mục III (ẩn viền trái / phải / dưới, `_o(an_vien=)`):
    bảng chữ ký riêng sau bảng thì Word BỎ QUA keepNext - chữ ký trơ một trang (đã thấy trên PDF). Xem thật: script scratchpad
    `thu_in.py` (QT_QPA_PLATFORM=windows, Excel / Word xuất PDF, QtPdf dựng ảnh).
  - BẢN WORD LÀ MẪU CHUẨN DUY NHẤT của phương án chi tiết (người dùng 22/10/2026 - chỉ thị 4 giai đoạn + PDF mẫu PA_01 / PA_002 /
    PA_003): `van_ban_trinh.xuat_bo_ho_so(chi_tiet_word=True)` MẶC ĐỊNH, KHÔNG ghi bản Excel chi tiết (kq['excel'] chỉ còn bảng tổng
    hợp); Word lỗi / không có Word -> `pdf_du_phong_chi_tiet(viec, loi, tao_xlsx)` lập Excel TẠM (thư mục tạm, xóa sau) dựng PDF gần
    đúng; in ra máy không có Word mà có Excel -> in bản Excel tạm (kq['du_phong']). `in_an.xuat_hang_loat` (Dự án mới) ủy quyền
    xuat_bo_ho_so(chia_thu_muc=False, chi_tiet_word=word). `chi_tiet_word=False` / `in_an.lap_chi_tiet` còn (dự phòng, test, tu-kiem).
    Xem trước: `xem_truoc_tai_lieu` nhận file .docx (`la_word`, `dung_duoc_word` - offscreen không mở Word trừ PABT_XEM_TRUOC_EXCEL=1,
    `chuyen_pdf` -> `chay_word`, In nhanh .docx qua Word), `yeu_cau(..., tao_du_phong=)` -> `_du_phong` dựng từ Excel (lề NĐ 30);
    CuaSoLapPA.lam_moi_xem_truoc / HopIn._lam_moi_xem_truoc tạo .docx (bảng tổng hợp vẫn .xlsx). HopIn: `o_word` luôn tích + ẨN (thuộc
    tính giữ cho mã cũ), bỏ QSettings KHOA_WORD_CT / `giao_dien.doc_bool`. Test mock preview phải patch CẢ `dung_duoc_excel` và
    `dung_duoc_word`. Mẫu Excel IN_CHITIET tùy chỉnh (HopQuanLyMauIn) chỉ còn ảnh hưởng bản gần đúng. Đo dự án thật (3 hộ): lập bản Word
    7 ms / hộ (Excel lap_chi_tiet 276 ms), Word xuất PDF một hộ 1,8 s (Excel 2,2 s) - xem trước F4 không chậm hơn.
  - in_word sau xuất thử dự án thật: bảng đầu văn bản LẤN LỀ (`LAN_LE_DAU_MM` 12 / 8 mm, `_bang(lui=)` -> tblInd âm + jc left,
    `rong_bang_dau`, cột quốc hiệu cố định `RONG_QUOC_HIEU` 5700 twip) - 13 pt trong vùng chữ 468 pt thì "TRUNG TÂM PHÁT TRIỂN QUỸ ĐẤT"
    bẻ 3 dòng; Mục I nhãn thường, giá trị hàng đầu (tên) đậm, ô canh trên. Bảng mục III `rong_cot(_chu_cac_cot(dong, …))` THEO NỘI DUNG:
    cột STT / ĐVT / SL / ĐG / tỷ lệ / thành tiền = max(`COT_TOI_THIEU`, từ dài nhất tiêu đề, chữ dài nhất x `DU_RONG`) (`_rong_chu`:
    chữ số 0,5 em…), phần còn lại tên : ghi chú chọn trong 30-70% cho TỔNG BÌNH PHƯƠNG số dòng ước nhỏ nhất (chỉ tổng số dòng thì ô ghi
    chú dài bị dồn 19 dòng); rong_cot() không đối số = `TY_LE_COT` cũ. Chữ 14 pt GIỮ - bảng 8 cột A4 vẫn chật (ghi chú dài ~11 dòng).
    Chưa làm: STT hộ không hiện (mẫu không hiện); bảng tổng hợp chia nguồn gốc theo thửa còn lệch khi một đoạn nhắc nhiều thửa (dữ liệu
    nguồn gốc ghép "1. Thửa 17 … 2. Thửa 16" trong một đoạn).
- 1.0.14 giao diện (người dùng 22/10/2026: hero màn hình chào; "nâng cấp toàn bộ giao diện - đơn giản, không lòe loẹt, không nhợt
  nhạt"; ảnh trước / sau bằng `ket_qua_kiem_tra/thu_that/chup_giao_dien.py`). Nguyên tắc: MỘT kiểu cho một loại thành phần, KHÔNG cắt
  chữ, bớt điểm nhấn thừa.
  - Màn hình chào: dải hero (HeroChao) đã làm rồi BỎ theo yêu cầu người dùng (cùng ngày) - giữ tiêu đề + `lb_chao` căn giữa như cũ;
    ĐỪNG thêm lại. Giữ: `TheChao` rộng `RONG_THE_CHAO_TOI_THIEU` 168 - 210 (trước cố định 210: 1366 @125% 4 thẻ chồng nhau), cao cố định.
  - Ô chọn: `_qss_o_chon` - ::drop-down trong suốt, chevron vẽ bằng QPainter `_anh_mui_ten` (PNG 1x / @2x ở %TEMP%\pabt_qss; đặt kiểu
    ::drop-down thì Qt BỎ mũi tên gốc của Fusion - cần ảnh). Không tạo được ảnh thì giữ kiểu cũ.
  - Thẻ số liệu (4 loại: TheSo, TheKpiGon, _The niêm yết, _TheKPI tiến độ): số MỘT màu `MAU_SO_THE` #0F172A, màu nhận diện chỉ ở vạch
    trái / thanh tiến độ; tên thẻ chữ thường kiểu câu (`TIEU_DE_THE` tiến độ). Danh sách hộ: `TEN_THE_GON` (Đã lập PA, Đã bàn giao; tên
    đủ ở chú thích), thẻ Tổng kinh phí co giãn 7 : 6. Niêm yết: chữ phụ chỉ tỷ lệ "75,0%" (câu đủ ở chú thích).
  - Tiêu đề khung / mục chữ thường kiểu câu (sổ vận động, đối soát, "Các quyết định phê duyệt", mục I / II thẻ hồ sơ - test đọc
    "(3 thửa)"); QGroupBox có "&" phải viết "&&" (lộ "_").
  - Bảng: `giao_dien.giu_cot_gian(bang, cot, toi_thieu)` - cột Stretch không bị bóp dưới `RONG_GIAN_TOI_THIEU` 150 (chuyển Interactive,
    cuộn ngang); chỉ tác động khi bảng ĐÃ HIỆN (lúc tạo vẫn Stretch). BangMuc (cột Vị trí / Tên), bảng thửa KhungHoSo (Nguồn gốc 220).
    Cơ cấu kinh phí `tu_cao=False` (căn cứ pháp lý một dòng, đủ ở chú thích), cột số đo bằng `phong_so` đậm. Tiến độ cột mốc thu hồi
    `chu_gon` (thoi_han.moc_thu_hoi_ho; file xuất `dong(day_du=True)` vẫn chữ đủ).
  - Cửa sổ lập PA: thẻ "Thông tin hộ, thửa đất" trong QScrollArea `cuon_ho_so` (cửa sổ thấp cuộn, không ép bẹp ô nhập / bảng thửa);
    dải lần PA: trạng thái là thẻ nhỏ không kèm số QĐ (đủ ở chú thích), chữ nút gọn "+ Lập PA bổ sung" / "Sửa lần…" / "Mở khóa…" /
    "Xóa lần". Tổng quan: nút "Lập PA →" viền mảnh (không nền đặc).
  - CHƯA làm (còn thấy trên ảnh): HopIn khung tùy chọn bên trái cuộn ngang ở 1536 @125%; bảng Quyết định dòng cao không đều; thẻ KPI
    bảng tổng hợp tên dài vẫn rút "…"; tiêu đề bảng navy + vạch xanh 2 px giữ (quyết định 1.0.12).
- 1.0.16 khung sườn Word theo PDF mẫu PA_01 (người dùng 22/10/2026; MỘT hàm `in_word.noi_dung_chi_tiet` dựng cả ba mẫu chi tiết / bổ sung / điều
  chỉnh): `LE_MM` trái 15 / phải, trên, dưới 10 mm (`LAN_LE_DAU_MM` = (0, 0): bảng đầu không lấn lề nữa); bảng đầu 2 hàng - hàng 1 cơ quan (2 dòng
  cấp trên thường + dòng 3 `DON_VI_TIEU_DE` đậm GẠCH CHÂN thật, bỏ dòng "____") | quốc hiệu + tiêu ngữ, hàng 2 "Số: …" | "địa danh, ngày …" cùng
  cỡ 14, cùng `truoc`, canh trên (ngang nhau); `TRICH_YEU` một dòng, chữ "&" như mẫu (bản NĐ 30 "VÀ" của 1.0.14 bỏ); `_duong_ke_du_an()` = đoạn
  rỗng viền dưới, thụt hai bên cho dài `DK_DU_AN_MM` 70; mục II mọi đoạn `firstLine` 567 (bỏ thụt lề treo gạch đầu dòng). Dòng "CHI NHÁNH …" lấy từ
  dữ liệu `du_an.don_vi_tieu_de` (mặc định hồ sơ địa phương "Chi nhánh Vĩnh Cửu"), KHÔNG ghi cứng trong mã. Test `test_in_an_2110.test_khung_suon_mau_pa_01`.
  - THÔNG SỐ MẪU WORD nhúng trong hồ sơ địa phương `ban_in.mau_word` (`pabt_profile.json`; `dia_phuong.kiem_tra_mau_word`): `le_mm`, `co_chu`
    (co_quan / quoc_hieu 13, tieu_ngu 14, so_ngay + du_thao 13, ten_loai / trich_yeu / du_an 14, thong_tin + de_muc 14, nguon_goc 13, bang 13,
    ghi_chu 11, chu_ky 15), `trich_yeu`, `thut_dau_dong_mm`, `gach_chan_ho_pt`, `duong_ke_du_an_mm`. `in_word._ap_mau` (đăng ký `dia_phuong.dang_ky`)
    đặt biến module LE_MM / CO_* / TRICH_YEU / THUT_DAU / HO_GACH_PT lúc nạp và sau mỗi `nap_lai` - nơi dùng đọc `in_word.CO_BANG`… LÚC GỌI
    (đừng `from .in_word import CO_BANG` ở cấp module). Đổi quy cách khi có quy định mới KHÔNG cần bản cập nhật: `in_word.xuat_thong_so` /
    `nhap_thong_so` / `khoi_phuc_thong_so` / `trang_thai_thong_so` (hộp Quản lý Mẫu in & Bản in: 3 nút "… thông số mẫu Word"), gói `.pabtcfg`
    (mang cả hồ sơ), hoặc sửa pabt_profile.json của máy; `dia_phuong.dat_muc_may(('ban_in','mau_word'), giá trị | None)` chỉ ghi phần khác mặc định.
  - Gạch chân HỞ: `in_word._p_gach` = viền dưới của đoạn (`w:space` = `HO_GACH_PT`, khe giữa chân chữ và gạch), thụt hai bên cho dài bằng chữ
    (đo bằng Qt `in_an._ham_do_chu` khi có, không thì ước `_rong_chu`; `KHE_GACH_PT` chừa 4 pt kẻo Word bẻ dòng) - KHÔNG dùng gạch chân chữ
    (`w:u`) sát nét chữ. Cột bảng: `rong_cot(chu_cot, do=)` đo chữ thật (cột số thu vừa chữ + `KHE_COT_PT`, không có ghi chú -> cột Ghi chú vừa tiêu đề).
  - BẢN CÀI KHÔNG ĐÓNG thư mục `mau_in` (PABT.spec / dung_exe38 bỏ): mẫu in Excel chuẩn nhúng ở `pabt/mau_in_nhung.py` (sinh bằng
    `tao_mau_nhung.py` từ `mau_in/` của mã nguồn - đó chỉ là NGUỒN để sinh), `in_an.thu_muc_mau` bản cài chỉ tìm mẫu người dùng chủ động thay
    (%APPDATA%\PABT\mau_in) rồi mẫu nhúng. Test `tests/test_mau_word.py`.
  - MÀU CHỦ ĐẠO (người dùng 22/10/2026 "navy quá đậm", ảnh thử `ket_qua_kiem_tra/thu_mau/`): `TOKEN['chinh']` navy #0F294A -> cobalt dịu #2F5F9E
    (hover / vạch cột `CHINH_RE` #264E83; banner `MAU_BANG` #2F5F9E / #3A6FB0 / #4A82C2), thay bằng script ở MỌI file pabt/ + tests/ (trừ
    ve_bieu_tuong.py, phieu_kiem_dem.py); gộp màu bão hòa: xanh #3B6FCE / #2F5DB5 / #1F76A6 / #1A5C85, đỏ #B83A3A / #C94545, lá #2F7D54 / #276348,
    teal #1F6F66, hổ phách #9A5A12 / #7C4A12 / #E5A93A. Bộ đo `ket_qua_kiem_tra/thu_that/danh_gia_ui.py` (chữ cắt, vùng bấm, Tab, tương phản QSS, màu bão hòa).
  - CỬA SỔ LẠ (người dùng 22/10/2026: cửa sổ rỗng có nút thu nhỏ / phóng to / đóng, tiêu đề "PABT", nhấp nháy khi lập PA): widget CHƯA CÓ CHA mà
    `setVisible(True)` / `show()` hiện thành cửa sổ cấp cao riêng. Gặp ở `xem_truoc_tai_lieu` (b_in, b_in_hop), `HopBanGiao` (lb_canh_bao, lb_chung),
    `HopBanDo` (b_nhap): gọi setVisible SAU khi đã addWidget / addRow. `kiem_tra_giao_dien.py` có bộ dò (mục "Cửa sổ lạ", mã thoát 1) + test
    `tests/test_cua_so_la.py`. Thêm widget mới: ẩn / hiện SAU khi vào bố cục.
- 1.0.19 (người dùng 23/10/2026; test `tests/test_an_toan_excel_1019.py`, `test_in_an_2110.TestDocxSangPdf`, `test_chu_de_1017.py`): PHƯƠNG ÁN
  CHI TIẾT CHỈ CÒN BẢN WORD - đã BỎ HẲN mẫu Excel IN_CHITIET: `in_an.lap_chi_tiet` + ~1.200 dòng hàm phụ (dàn trang, đường kẻ, nguồn gốc),
  `canh_trang_in_an.py`, `mau_in\IN_CHITIET*.xlsx` / `.duong_ke.xml`, mẫu nhúng chi tiết (`tao_mau_nhung.DS` chỉ còn IN_BANGTONGHOP),
  mục `mau_in.IN_CHITIET` của hồ sơ địa phương (hồ sơ cũ còn mục này vẫn hợp lệ - bỏ qua), mục chi tiết trong `in_an.MAU_QUAN_LY` / gói mẫu.
  Mọi ghi chú cũ ở trên nhắc `in_an.lap_chi_tiet`, IN_CHITIET Excel, dàn trang chi tiết Excel là LỊCH SỬ (không còn mã). Bảng tổng hợp
  VẪN là Excel (IN_BANGTONGHOP, người dùng chọn). `pabt/du_lieu_in.py` (không Excel / Word / Qt): `dong_chi_tiet`, `_thong_tin_ho`,
  `_thong_tin_du_an`, tiêu đề mục, `ten_file_ho`, `chon_lan_in`... - `in_word`, `bang_dieu_chinh`, `van_ban_trinh`, `man_hinh` gọi trực
  tiếp `du_lieu_in.X`; `in_an` chỉ nhập lại vài tên cho bảng tổng hợp. `pabt/docx_sang_pdf.py`: PDF dự phòng khi máy không có Word =
  QTextDocument từ chính file .docx (hiểu phần OpenXML do in_word / van_ban_trinh sinh: đoạn, chạy chữ, bảng gộp ô, viền ô, viền dưới đoạn
  = bảng một ô); `van_ban_trinh.pdf_du_phong_chi_tiet(viec, loi)` và `xem_truoc_tai_lieu._du_phong` dùng nó; `xuat_bo_ho_so` không còn
  tham số `chi_tiet_word`; in ra máy khi không có Word -> PDF dự phòng + lỗi 'KHONG_CO_WORD'. AN TOÀN EXCEL: mọi file xuất cho người
  dùng lưu bằng `an_toan.luu_xlsx(wb, đường dẫn)` (`khu_cong_thuc`: công thức không thuộc dạng SUM / ROUND + ô / số bị ép thành chữ,
  quotePrefix) - ĐỪNG gọi `wb.save` trực tiếp ở nơi xuất file (`test_an_toan_excel_1019.TestMotCongLuu` chặn; chỉ in_an lưu lại file MẪU).
  `in_an._thay_cho_trong`: thay `{trường}` MỘT lượt (giá trị chứa `{khác}` không bị thay tiếp). Giao diện 2.0 nền tảng: `pabt/chu_de.py`
  (không Qt: mật độ bảng gon / chuan / thoang, tương phản cao theo Windows, `PABT_MAT_DO` / `PABT_TUONG_PHAN_CAO`) + `giao_dien.dat_mat_do`
  + `man_hinh_giao_dien.HopGiaoDien` (Cài đặt > Giao diện…). CHƯA có nền tối (màu còn viết cứng ở nhiều nơi). KHÔNG dùng `sed -i` (đổi
  CRLF sang LF) - đã lặp lại nhiều lần.
  MẪU WORD CHI TIẾT theo PDF người dùng gửi `mau_in\MAU IN CHI TIET WORD.pdf` (23/10/2026; file PDF có dữ liệu thật - KHÔNG đóng gói / KHÔNG
  vào git): `ban_in.mau_word` mặc định lề 9 / 7 / 10 / 10 mm, co_chu 10,5 (mọi chữ thân) / bảng 10 / ghi chú 7,5 (đo trực tiếp cỡ chữ trong PDF - nếu
  file Word gốc dùng cỡ lớn hơn rồi thu nhỏ khi in PDF thì tăng lại bằng Quản lý Mẫu in > Nhập thông số mẫu Word); `du_lieu_in` tiêu đề mục I (một
  tiêu đề cho hộ và tổ chức) / II / `NHAN_TDC` "Phương án tái định cư:"; tên dự án "Dự án <tên>" chữ thường đậm + `_duong_ke_du_an()` (đoạn rỗng
  cao 6 pt có viền dưới, DK_DU_AN_MM 50 - GIỮ, người dùng yêu cầu cách chữ, không sát); (DỰ THẢO) đậm; bảng III `_bang(ngoai_sz=12)` viền ngoài đậm;
  CHỮ KÝ = dòng cuối bảng III, MỘT ô gộp cả lưới chứa BẢNG LỒNG ba cột bằng nhau (`tong // 3`), chữ giữa từng cột - đọc bảng bằng
  `findall(tr)` / `find(tblGrid)` (iter() lẫn bảng lồng). `docx_sang_pdf._bang`: dòng chỉ có bảng lồng dựng thành bảng SAU bảng ngoài (Qt nới đều
  cột khi gặp bảng lồng cỡ cả bề rộng). Offscreen KHÔNG có phông thật: bề rộng cột đo ra sai - xem ảnh bằng QT_QPA_PLATFORM=windows.
  `pabt/openxml_word.py` (1.0.19): BỘ CÔNG CỤ dựng .docx bằng mã (chỉ thư viện chuẩn, Python 3.8): `chay` / `doan` / `doan_gach_ho` /
  `bang` + `hang` + `o` (gộp ô) / `sect_pr` / `dien_cho_trong` (một lượt, thoát XML) / `goi_docx` / `luu` / `doc_than`, mẫu khung
  `mau_khung()`; hướng dẫn `mau_word\HUONG_DAN.md` + `mau_word\MAU_KHUNG.docx` (thư mục KHÔNG đóng vào bộ cài). in_word / van_ban_trinh vẫn dùng
  bản trợ giúp riêng (chưa chuyển sang module này). `.doc` nhị phân không dựng được. `tests/test_khuon_word.py` = bộ kiểm KHUÔN bằng
  Microsoft Word thật (PDF -> đo vị trí chữ: lề, "Số" / "ngày" cùng hàng, CHI NHÁNH, không trang chỉ có chữ ký; bỏ qua khi không có Word).
- 1.0.22 (người dùng 24/10/2026): XEM TRƯỚC GỘP NHIỀU HỘ ở `HopIn` - nút `b_xem_nhieu` (hàng "Phương án chi tiết" của khung tài liệu) ->
  `xem_truoc_nhieu_ho` (hộ đang đánh dấu, tối đa `man_hinh.XEM_NHIEU_TOI_DA` 30; khóa ('nhieu', hộ, dự thảo, lần)); `xem_truoc_tai_lieu`:
  `yeu_cau(khoa, tao, ...)` nhận `tao(thu_muc)` trả LIST [(file .docx / .xlsx, nhãn)] -> `chuyen_pdf_nhieu` (luồng nền: Word / Excel xuất PDF từng
  file trong MỘT lần mở ứng dụng rồi `gop_pdf_muc` pypdf), mục lục `muc_luc` [(nhãn, trang đầu)], ô `cb_muc` "Nhảy tới hộ" (`den_muc`, `sang_trang(
  tuyet_doi=)`), `xlsx` = None khi xem nhiều hộ (nút In nhanh tắt, dùng "In…" in cả bản), cache `_nho_muc`; không có Word: `_du_phong(muc=)` dựng PDF
  gần đúng từng file bằng Qt rồi gộp. Đo Word thật: 4 hộ 3,9 s. Test `tests/test_yeu_cau_2411.py`. Đã sửa luôn `xem_truoc_bang_tong_hop` (còn truyền
  tham số `mau` thừa từ 1.0.20). Phân tích giao diện in (24/10): xem báo cáo trong phiên - đề xuất chưa làm: bỏ "Chọn tất cả mẫu / Bỏ chọn mẫu", gộp
  3 cách chọn phạm vi, đưa bảng hộ giãn cao, bộ đếm nổi che cột tiền, nhớ lựa chọn đầu ra, ô nhập lề bảng tổng hợp trong Cài đặt.
- 1.0.21 (người dùng 24/10/2026, ảnh PDF Word chi tiết + bảng tổng hợp):
  - TIÊU ĐỀ MỤC I THEO CHỦ SỬ DỤNG LÀ YÊU CẦU CỦA NGƯỜI DÙNG (22/10: Phương án 2): `du_lieu_in.TIEU_DE_MUC_I_TO_CHUC` "I. Thông tin về tổ chức" /
    `TIEU_DE_MUC_I_HO` "I. Thông tin về hộ gia đình, cá nhân" (người dùng 24/10 viết "về"; bản 1.0.13 ghi không có "về"). 1.0.19 từng ghi đè bằng tiêu đề
    chung của PDF mẫu "I. Tổ chức và hộ gia đình, cá nhân bị thu hồi đất…" - LỖI: PDF mẫu chỉ cho quy cách (lề, cỡ chữ, bố cục), KHÔNG được đổi chữ
    người dùng đã chỉ định bằng yêu cầu riêng; khi chỉnh theo mẫu mới, đối chiếu lại các yêu cầu chữ cũ (CLAUDE.md các mục trước) rồi mới sửa.
  - Word: `in_word.CHU_KY_LECH_TRAI_MM` 3,4 (khối chữ ký: 4 cột [a-2s, a+2s, a-2s, đệm] - tâm ba phần cách đều nhau, lùi s; Word BỎ QUA tblInd âm của
    bảng lồng); `_p_gach(..., ngan_mm=)` đường gạch NGẮN hơn chữ = đoạn rỗng riêng (viền dưới của đoạn chữ thụt vào làm chữ bẻ dòng "CHI NHÁNH VĨNH / CỬU") -
    `CHI_NHANH_NGAN_MM` 10, `HE_SO_DO_QT` 0,96 (Qt đo rộng hơn Word); tiêu ngữ `KHE_TIEU_NGU_PT` 1,5 (đo bằng Word thật: -2 làm "Hạnh / phúc" bẻ dòng);
    `DK_DU_AN_KHE_PT` 3 (đoạn rỗng mang đường kẻ dưới tên dự án; trước 6). `du_lieu_in.nhan_du_an(ten)`: tên dự án toàn chữ in hoa -> "DỰ ÁN", còn lại "Dự án"
    (Word + bảng tổng hợp ô A6 `{nhan_du_an} {du_an}`).
  - Bảng tổng hợp: `lap_bang_tong_hop` dùng `in_word.dong_co_quan(da)` -> A1 = cơ quan chủ quản (một dòng; thêm "THÀNH PHỐ …" của dự án cũ ghi vào ô tên đơn vị),
    A2 = "CHI NHÁNH …"; `can_duong_ke`: đường kẻ dưới tên đơn vị = chữ - `DK_CHI_NHANH_NGAN_CM` 1 cm; dưới Dự án `DK_CACH_DU_AN` 3 pt (đường khác `DK_CACH` 5).
    Lề A3 hiện hành (hồ sơ pabt_profile.json ban_in.le_trang.tong_hop): trên / dưới 0,5906 in (1,5 cm), trái 0,7874 in (2,0 cm), phải 0,3937 in (1,0 cm), header / footer 0,20 in.
    Test `tests/test_yeu_cau_2410.py`.
- 1.0.20 (người dùng 23/10/2026, phương án B): BẢNG TỔNG HỢP cũng KHÔNG còn file mẫu Excel - `pabt/mau_bang_tong_hop.py` (TỰ SINH một lần từ
  IN_BANGTONGHOP.xlsx rồi sửa tay được: `KIEU` / `CELLS` / `MERGES` / `RONG_COT` / `COT_AN` / `CAO_DONG` / `LE_TRANG`, `tao_workbook()`: cột có
  `min = max` như mẫu đọc từ file - `in_an._px_cot` cần; phông mặc định Arial 11 qua `wb._fonts` - `_mdw` đo theo nó) thay file; `in_an.lap_bang_tong_hop(con,
  file_ra, ds_ma_ho, so_pa_tong, ngay_pa_tong, ...)` bỏ tham số `mau`; `du_thao` là bool (không suy theo tên mẫu). Đã so từng ô / ô gộp / bề rộng /
  cao dòng / tỷ lệ in / ngắt trang với bản đọc từ file: giống hệt. ĐÃ XÓA: `mau_in\IN_BANGTONGHOP.*`, `IN_TONGHOP_DT.*`, `mau_in_nhung.py`,
  `tao_mau_nhung.py`, ~540 dòng quản lý mẫu Excel trong in_an (`thu_muc_mau*`, `file_mau`, `ds_mau`, `tao_mau_tu_excel`, `nap_mau_in`, `thay_mau`,
  `xuat_mau`, `khoi_phuc_mau`, `nap_mau_bytes`, `la_mau_du_thao`, `duong_ke_cua_mau`...). `in_an.chen_duong_ke(file_xlsx, xml='', bo_qua='')` (đường kẻ
  luôn do `dk_mac_dinh` tạo - không còn file .duong_ke.xml). `man_hinh_quan_ly_mau.HopQuanLyMauIn` chỉ còn thông số mẫu Word; HopIn bỏ nút "Sửa mẫu in
  trong Excel…". `goi_mau.ds_mau_hien_hanh` chỉ còn mẫu tờ trình trong thư mục mẫu. Mọi ghi chú cũ ở trên nhắc mẫu Excel IN_BANGTONGHOP / IN_TONGHOP_DT /
  mau_in_nhung / tao_mau_tu_excel / Quản lý Mẫu in thay mẫu Excel là LỊCH SỬ. Sửa bố cục bảng tổng hợp: sửa `mau_bang_tong_hop.py` (không còn file Excel để sửa).
- `khoa.py`: khóa nhiều máy bằng file `<x>.pabt.khoa` (làm mới 60 s, hết hạn 180 s); `app.mo()` hỏi mở chỉ xem / vẫn sửa.
- `giao_dien.py`: QSS + tô màu nút tự động theo chữ trên nút (`LUAT` → `MAU`, property `nhom`), nhãn dùng property `vai`
  (`nhan`, `tieu_de`, `bang_ten`). Nút mới tự có màu nếu chữ khớp luật; thêm nhóm thì sửa `LUAT`/`MAU`.

## Môi trường làm việc
- Dự án ở `D:\APP AI PABT\PABT_PhanMem` (đường dẫn không dấu; trước 07/10/2026 là `D:\Thư mục mới\…` dạng NFD). File thật của người
  dùng (file dự án `.pabt` thật, `PABT_CHUAN_06-10-2026_QD42.xlsm` – dùng cho `PABT_EXCEL`) ở thư mục cha: chỉ đọc / thử trên bản sao.
- Windows PowerShell 5.1; `.venv` dùng Python 3.14. `build/`, `dist/`, `bo_cai/` là sản phẩm dựng.
- 1.0.15 (chưa tăng `__version__`, chưa commit) PHƯƠNG ÁN ĐIỀU CHỈNH (người dùng 22/10/2026): `pa_lan.loai` ('chinh' / 'bo_sung' / 'dieu_chinh') + `thay_the` (lần bị thay) thêm bằng `csdl.dam_bao_cot_pa_lan` (KHÔNG đổi PHIEN_BAN_CSDL). `lan_pa.tao_lan_dieu_chinh` chép lần gốc sang lần mới; `nghiep_vu.doc_phuong_an` / `doc_tat_ca_phuong_an` bỏ lần bị thay khỏi tổng hộ, `tinh_chenh_lech_lan` = QĐ điều chỉnh ghi CHÊNH LỆCH (`theo_doi.them_ho_theo_pa`). `BoSoan.lap_dieu_chinh` / `CuaSoLapPA.lap_dieu_chinh` (nút "+ Lập PA điều chỉnh"). Mẫu in tạo bằng mã (không file mẫu): `in_word.noi_dung_chi_tiet` chọn mẫu chi tiết / bổ sung / điều chỉnh (A đã duyệt, B đề nghị, C chênh lệch) theo `pa_lan.loai`; `bang_dieu_chinh.lap` bảng tổng hợp điều chỉnh A3 (`xuat_bo_ho_so(bang_dieu_chinh=True)`, ô `HopIn.o_bth_dc` chỉ hiện khi dự án có hộ điều chỉnh). Test `tests/test_dieu_chinh.py`.

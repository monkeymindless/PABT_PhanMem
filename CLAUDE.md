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
- Chạy `PHAN_TICH_PHIEN_BAN.bat` (= `phan_tich_phien_ban.py --so-sanh bo_cai\LARC_CapNhat_<bản trước>.larcud`): tốc độ mở / tắt,
  mở dự án, lưu + tải lại, lệnh dòng lệnh; module nạp lúc khởi động; mã lặp lại; file khác nhau -> `ket_qua_kiem_tra\PhanTich_*.md`.
- Chạy `KIEM_TRA_GIAO_DIEN.bat` (= `kiem_tra_giao_dien.py`): bấm mọi nút, gõ mọi ô nhập, chọn mọi mục chọn, sửa ô bảng của mọi
  hộp thoại (bản sao dự án; chặn in / Excel / Word / mạng) -> lỗi, chậm / đơ (> 5 s), treo -> `ket_qua_kiem_tra\GiaoDien_*.md`.
- Báo cáo cho người dùng KÈM phân tích: điểm nghẽn, lệnh lặp lại, cách gọi lệnh nhanh nhất / đường tắt, cách gọi gói (nạp module
  khi nào), tốc độ (thời gian mở tắt, chạy lệnh) - bảng so với bản trước; lỗi / đơ của nút bấm, ô nhập, mục chọn (đã sửa gì).
- Toàn bộ test (Qt6; Qt5 nếu có `venv38_32`), `vermin -t=3.8-` cho mã pabt/.
- TỰ LÀM TRỌN GÓI, KHÔNG HỎI LẠI (người dùng 30/10/2026): sửa lỗi / nâng cấp / tinh chỉnh theo yêu cầu cho tới xong, test đạt thì TỰ
  commit, tăng phiên bản, dựng bộ cài (DUNG_BO_CAI chuỗi lệnh + gói .larcud), thử máy trắng (`thu_may_trang.ps1`), đồng bộ LARC Mobile
  cùng số phiên bản (dựng --url, đẩy Pages) - không dừng hỏi "commit?", "dựng bộ cài?". Chỉ hỏi khi yêu cầu mơ hồ thật sự.

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
- `khoa.py`: khóa nhiều máy bằng file `<x>.pabt.khoa` (làm mới 60 s, hết hạn 180 s); `app.mo()` hỏi mở chỉ xem / vẫn sửa.
- `giao_dien.py`: QSS + tô màu nút tự động theo chữ trên nút (`LUAT` → `MAU`, property `nhom`), nhãn dùng property `vai`
  (`nhan`, `tieu_de`, `bang_ten`). Nút mới tự có màu nếu chữ khớp luật; thêm nhóm thì sửa `LUAT`/`MAU`.


## Quy tắc đang hiệu lực (tóm từ lịch sử - chi tiết, lý do, số đo: `docs/LICH_SU_PHAT_TRIEN.md`)
Lịch sử từng phiên bản (0.9.4 - nay) nằm ở `docs/LICH_SU_PHAT_TRIEN.md` (chép nguyên văn từ CLAUDE.md ngày 03/11/2026). TRƯỚC KHI SỬA một
module / hàm / màn hình: `grep` tên đó trong file lịch sử để biết quyết định cũ của người dùng và cái bẫy đã gặp. Ghi chú phiên bản mới:
thêm vào CUỐI file lịch sử; chỉ quy tắc mới có hiệu lực lâu dài mới thêm vào mục này.

### Dữ liệu, CSDL
- Tiền / diện tích / số lượng lưu TEXT, tính `Decimal` (`tien.D`, `lam_tron` = ROUND của Excel). Chữ người gõ / ô file: `tien.doc_so_vn` /
  `lap_pa.doc_so` (không dùng `D()` cho chữ người gõ). Số lượng gõ trực tiếp giữ nguyên (tối đa 4 chữ số lẻ), kết quả công thức làm tròn
  `so_le_so_luong` (2; ha / đơn vị bội 4). Không float.
- Đổi lược đồ chính thức: `schema.sql` + tăng `PHIEN_BAN_CSDL` + `_NANG_CAP[v_cũ]`. Thêm cột / bảng / chỉ mục KHÔNG đổi phiên bản: một
  dòng trong `csdl.MO_RONG` (hàm kiểm + hàm làm; `dam_bao_mo_rong` chạy một giao dịch, chỉ file có hộ). Phần mở rộng làm bản cũ GHI SAI dữ
  liệu: tăng `csdl.GHI_TOI_THIEU`. Bộ đơn giá đóng gói `pabt/bo_don_gia.sqlite` KHÔNG được bị ghi khi mở (test so băm) - nâng bằng
  `tao_bo_don_gia.py --chuan-hoa <nhãn>`.
- `journal_mode=DELETE` (không WAL - file hay nằm trên Google Drive / thư mục mạng). Tạo file mới: `csdl.tao_moi_tam` + `hoan_tat_tao_moi`
  (ghi nguyên tử); `tao_moi` XÓA file cũ trước.
- Mọi ghi: `csdl.ghi_nhat_ky`; ghi danh mục trong `with ..., csdl.mo_khoa_danh_muc(con)`; hàm ghi dùng chung bọc `csdl.giao_dich(con)` (lồng
  được; `with con:` lồng COMMIT ở tầng trong). Không `IN (?,?…)` với danh sách hộ dài (trừ <= `theo_doi.LOC_SQL_TOI_DA`).
- Ghi bộ đơn giá / bảng giá đất / hệ số K (1.0.56): hàm ghi gọi `quan_tri_bo.kiem_quyen(...)` ĐẦU và `quan_tri_bo.sau_khi_sua()`
  CUỐI (don_gia `_mo_sua` / `cai_bo` / `khoi_phuc_bo_goc`, nhap_don_gia.ap_dung, gia_dat_nq28 ghi_thay / xoa_thay, he_so_k ghi / xoa).
  Máy có may_chu.json: chỉ quản trị máy chủ đang đăng nhập; máy đơn: mật khẩu (`mo_khoa_phien`). Màn hình khác hộp Bộ đơn giá hỏi bằng
  `man_hinh_don_gia.xin_quyen_sua`. Cài bộ nhận từ máy chủ trong `quan_tri_bo.cho_phep_dong_bo()` (dong_bo_don_gia). Hàm ghi mới: thêm cả hai.
- Phân quyền 6 vai trò (1.0.57, `phan_quyen`): vai trò gắn trên kết nối (`con._vai_tro`, app.mo theo `vai_tro_cho_file`); hàm ghi
  gọi `lap_pa.kiem_quyen(con, '<quyền>')` ngay sau kiểm hộ nhận việc; BoSoan.luu `phan_quyen.kiem_pa`; trigger tạm `_pq_*`
  (`gan_chan_csdl`). Hàm ghi MỚI: thêm kiem_quyen. Vai trò None (máy đơn / file riêng) = mọi quyền; 'quan_tri' / 'nguoi_dung' cũ giữ quyền.
- Hàm ghi theo hộ gọi `lap_pa.kiem_ho_nhan_viec` / `kiem_ds_ho_nhan_viec` ở đầu (bản offline nhận việc theo hộ; trigger tạm
  `gan_chan_ho_nhan_viec` là lớp chặn cuối). Bảng `audit_logs`: không viết mã sửa / xóa.
- Đối tượng nhớ dùng chung (`BoiCanh.tu`, `nghiep_vu.ket_qua_ho`, `theo_doi.tong_hop`, `csdl.nho`): KHÔNG sửa đối tượng trả về. Cả dự án:
  `nghiep_vu.doc_tat_ca_phuong_an` - đừng gọi `tinh_ho` / `doc_phuong_an` trong vòng lặp hộ.
- Nhiều lần phương án: `doc_phuong_an` mặc định CỘNG DỒN các lần (bỏ lần đã bị thay); `BoSoan.luu` chỉ ghi lần đang mở; lần khóa không sửa.
- Khu vực giá (1.0.57, `khu_vuc_gia`): bộ đơn giá tách Phụ lục I / II theo khu vực - lưu ở tham_so `KVMUC:<mã>` / `KVXA:<xã>` / `KVTEN:<kv>`
  (không đổi lược đồ; mục không có KVMUC dùng mọi khu vực). Dự án: `khu_vuc_du_an` (cai_dat KHU_VUC_GIA hoặc xã du_an.ten_dia_ban);
  `lap_pa.DanhMuc` ẩn mục khu vực khác (`an`, `bi_khoa`; `lay` vẫn trả để đọc dòng cũ). Văn bản nhiều khu vực: `so_khop_khu_vuc` (so từng
  khu vực với mục cùng khu vực, `chi_ma`), `ap_dung(khu_vuc=…)`. Thêm cách đọc / ghi danh mục mới theo mã: nhớ lọc theo khu vực.
- Văn bản chính sách (1.0.60): dòng `Muc.can_cu` đọc theo Điều / khoản (`muc_chinh_sach_tu_dieu_khoan`), khớp `_khop_chinh_sach`, giữ tên mục của bộ; nhóm 4 chế độ thay thế: mục dẫn chiếu (`la_muc_dan_chieu`) "giữ nguyên", không "bỏ". Chữ lớp hoa dùng `_HOA` (khoảng À-Ỹ gồm cả chữ thường).
- Mã tài sản: nhà TS, cây CT, vật nuôi VN, chính sách CS, thưởng TH (`ma_tai_san`). Quy ước tương đương do người dùng tự nhập (bộ đơn giá
  không có).

- Nhật ký kiểm toán: chuỗi băm ở bảng RIÊNG `audit_bam` (id = audit_logs.id; trigger TẠM `_kt_ky` AFTER INSERT từng dòng của
  `kiem_toan.gan_ky`, hàm SQLite `_kt_bam` = `kiem_toan.tinh_bam`; đừng thêm cột vào audit_logs - bảng cấm UPDATE, INSERT … SELECT nhiều
  dòng tính trước cả lô nên không nối được). `audit_bam` có trong `hoan_tac.BO_QUA`, `DauVetHo.BO_QUA`, `chua_benh_csdl._XOA_BANG` -
  bảng mới bị trigger cấm xóa phải thêm vào cả ba (không thì Ctrl+Z lỗi / danh sách hộ tải lại toàn bộ mỗi lần lưu).
- Bản sao lưu tự động / mốc thời gian: NÉN zlib (`an_toan.DAU_SAO_LUU`, KHÔNG mã hóa - người dùng chọn 03/11/2026: phải khôi phục được
  sau khi cài lại Windows). Mở: `csdl.mo` tự giải nén ra file tạm, luôn chỉ xem (`KetNoi.close` xóa file tạm); `khoi_phuc` giải nén. Đừng
  mở file sao lưu bằng `sqlite3.connect` thẳng.

### Tương thích Python 3.8 + Qt5 (bản Win7 32-bit)
- Mỗi file `pabt/` có `from __future__ import annotations` (sau docstring), không API Python 3.9+ (`vermin -t=3.8-`). Chạy test cả
  `venv38_32`. Enum viết kiểu `Qt.AlignmentFlag.X`; `TextAlignmentRole` trả SỐ NGUYÊN; `QMenu.exec` bí danh bằng lambda (`_qt5_lam_qt6`).
- Không emoji trong chữ giao diện (Win7 không có phông): biểu tượng `giao_dien.icon_ky_hieu` (Segoe MDL2). Tên file trong bản dựng ASCII.
- `cai_dat.ps1` / `go_cai_dat.ps1` viết theo PowerShell 2.0, gọi bằng `-Command` + ReadAllText (không `-File`).
- Không chạy ở luồng nền mã dùng Qt (đo chữ, QtPdf) hay `self.con` của cửa sổ: `giao_dien.chay_nen*` chỉ cho việc thuần Python.

### Giao diện
- Màu: `TOKEN`, `dat_kieu_theo_tong(w, qss)` (kiểu riêng đổi theo tông nền), `mau_o_theo_tong(globals(), TEN='#…')` (hằng QColor của
  màn hình), `mau_theo_tong` / `qmau_theo_tong` (màu trong mô hình bảng / rich text). Không `setStyleSheet` có `#RRGGBB` trực tiếp; số mã
  màu mỗi file có mốc (`tests/test_p1_giao_dien.MOC_MAU`). Không `setStyleSheet` trên KHUNG CHỨA (Qt tính lại cả cây - chậm): QSS chung
  theo property / objectName, hoặc đặt trên widget lá.
- Cỡ chữ QSS theo `giao_dien.THANG_CO_CHU` (11-12-13-14-16-18 px). Thẻ số liệu cửa sổ chính cao 62 px - không nới.
- MỖI LỆNH MỘT CHỖ: menu trái và thanh menu không lặp nhau; nút / chuột phải dùng lại QAction của `self.lenh` (`pabt/lenh.py`, lambda gọi lúc
  bấm), không gọi thẳng hàm (mất trạng thái tắt khi chỉ xem / chưa mở dự án - `LENH_CAN_DU_AN`). `tests/test_khong_trung_lenh.py` chặn.
- Widget chưa vào bố cục mà `setVisible(True)` = CỬA SỔ LẠ: ẩn / hiện SAU khi addWidget; widget con của cửa sổ chính ngoài bố cục phải ẩn
  (từng nuốt cú bấm menu). Sau khi đổi bố cục hộp thoại: chạy `kiem_tra_giao_dien.py` (mục "Cửa sổ lạ").
- Hộp thoại tạo với cha, dọn bằng `don_hop_da_dong`; không `WA_DeleteOnClose` hàng loạt, không giữ hộp làm thuộc tính để dùng lại; QMenu tạm
  `deleteLater`; KHÔNG `takeAt(...).layout().deleteLater()` (hủy hai lần - sập) - thay cả widget chứa. QGraphicsItem không phải QObject.
- Danh sách dài: `giao_dien.hop_ket_qua` (không ghép vào QMessageBox). Hộp thoại mới có `im_lang` / `cho=False` cho test.
- Bảng: chiều cao dòng `giao_dien.vua_dong` (không `resizeRowsToContents`); bảng lớn `bang_ao.BangAo`; lệnh theo hộ đọc dòng bằng
  `cac_dong_da_chon` (không `selectedRows`); cột theo tên (`self.cot.index(khóa)`), không viết số cột. Chữ "&" trên nút / thẻ: `chu_hien`.
- Cửa sổ lập phương án (1.0.58): phím Ctrl+B (`bat_tat_ds_ho`), Space trên bảng mục (`BangMuc.bat_tat_chi_tiet`), F4 vẫn là xem trước A4. Khung
  phụ `man_hinh_phu_lap_pa` dựng khi dùng lần đầu; khung chi tiết ghi qua ĐÚNG ô của bảng (`setText` -> `sua_o`), đừng ghi thẳng vào `bo.pa`.
- Phím tắt trùng cùng ngữ cảnh: Qt không chạy cái nào. Không gắn Ctrl+Z / Ctrl+Y lên QAction (`giao_dien.xu_ly_hoan_tac` xử lý).
  F2 là phím sửa ô của bảng - không gán lệnh khác (giải trình dòng phương án dùng Ctrl+I).
- Duyệt bố cục: KHÔNG lấy QLayoutItem (`itemAt` / `itemAtPosition` / `takeAt`) chỉ để đọc - vỏ Python của mục bố cục (QSpacerItem,
  QWidgetItem: không phải QObject) sống lâu hơn đối tượng C++; widget mới cấp phát trùng địa chỉ bị PySide trả NHẦM vỏ cũ
  (`'QSpacerItem' object has no attribute …`, có lúc sập 0xC0000005 / mã thoát 139 giữa lượt test). Dùng `lo.indexOf(widget)`,
  `getItemPosition(i)`, `labelForField(w)` (1.0.55 - lỗi do `gan_nhan_o_nhap` của 1.0.54).
- Test KHÔNG đổi bảng kiểu / bảng màu của QApplication thật (`ap_dung`, `dat_tong_nen(ap_lai=True)`, `dat_ty_le`): mỗi lần hàng chục giây
  cho cả lượt. Gỡ bộ lọc: `giao_dien.bo_ap_dung(app)`.

### Bản in
- Phương án chi tiết CHỈ bản Word (`in_word`, XML thuần - không python-docx); bảng tổng hợp Excel dựng bằng mã `mau_bang_tong_hop.py`
  (không còn file mẫu Excel). PDF: Word -> LibreOffice -> `docx_sang_pdf` (Qt). Thông số mẫu Word ở hồ sơ địa phương `ban_in.mau_word`.
- Mọi file Excel xuất cho người dùng qua `an_toan.luu_xlsx` (khử công thức lạ) - không `wb.save` trực tiếp. VBS Office giữ
  `AutomationSecurity = 3`.
- Viền đen RGB / Word `sz 8 color 000000` (WPS / LibreOffice / chế độ tối không mất khung). Bảng lớn: không `ws.merge_cells` /
  `unmerge_cells` / `iter_rows` (dùng `in_an._gop_o`, `_bo_gop`, `_o_chu`). Không bật fitToPage khi có ngắt trang tay; giữ
  `RONG_DU_PHONG_BTH` 0,97 (đã đo: khít 100% Excel tách cột sang trang riêng).
- Bảng mục III (1.0.57): `du_lieu_in.an_muc_trong` ẩn mục 2-6 không tiền + không dòng, ĐÁNH LẠI số mục - nhận mục theo TÊN
  (`in_word._theo_muc`, `du_lieu_in.la_muc_nha`, `TEN_MUC_DAT`), đừng so số mục cố định (`so_muc`) trên dòng in.
- Địa danh dòng ngày = `du_lieu_in.dia_danh_ngay` (nơi đơn vị công tác, không phải xã dự án). Tiêu đề mục I theo chủ sử dụng (tổ chức / hộ)
  - chữ người dùng chỉ định thắng PDF mẫu. Không ghi cố định tên đơn vị / người ký; hồ sơ địa phương mặc định trung tính.

### Phát hành, bộ cài
- Một bộ cài `LARC_Setup_Universal_<ver>.exe` + zip Universal + gói `LARC_CapNhat_<ver>.larcud`; vẫn dựng hai bản chương trình (Win10-11
  Qt6 x64, Win7-8 Qt5 x86). Không Inno Setup >= 6.5. Giữ bộ cài cũ trong `bo_cai\`. Chuỗi lệnh dựng dừng khi một bước lỗi. Thử máy trắng
  `thu_may_trang.ps1`. LARC Mobile đồng bộ số phiên bản (`di_dong/dung.py --url`, đẩy Pages bằng `gh auth git-credential`).
- Không đóng gói dữ liệu thật (.pabt, PDF phương án thật trong mau_in\, danh sách hộ). Tên nội bộ GIỮ PABT (PABT.exe, `%APPDATA%\PABT`,
  QSettings, `cap_nhat.UNG_DUNG`, khóa đăng ký); chữ hiển thị LARC. AppUserModelID = `$APP_ID` của cai_dat.ps1.
- `rut_gon.GIU_MODULE`: giữ Qt5Qml.dll, Qt*Network.dll; Tesseract đóng kèm giữ `vie` best + `osd` (người dùng quyết định - không đề xuất bỏ).
- Không chữ ký số gói cập nhật, không màn hình "Kiểm tra an toàn" (người dùng bỏ - đừng thêm lại).

### Quyết định của người dùng (không đề xuất lại nếu người dùng không hỏi)
- Không viết lại 4 tầng; không bỏ Office / VBS; không WAL; không đệm mẫu Excel bằng pickle / deepcopy (hỏng openpyxl).
- Che CCCD chỉ là TÙY CHỌN cho bản niêm yết (1.0.52); tờ trình / quyết định in đủ số. Trợ lý AI luôn ẩn danh; không gửi ảnh / dữ liệu biên
  bản lên dịch vụ AI / OCR ngoài. OCR = Tesseract trên máy.
- Nút Lưu xanh lục (`MAU_LUU`); thanh tab ngang đã bỏ; tên dự án chỉ ở tiêu đề cửa sổ.

### Môi trường phiên Claude
- Ứng dụng Claude (MSIX) ảo hóa `%LOCALAPPDATA%`: venv38_32 thật ở `%LOCALAPPDATA%\Packages\Claude_pzs8sxrjxfjjc\LocalCache\Local\PABT_dev`.
- Heredoc của Bash NUỐT dấu "\": script Python sửa file ghi bằng Write rồi chạy. Không `sed -i` (đổi CRLF sang LF; lỗi trong scratchpad).
  Sửa file bằng script: GIỮ kiểu xuống dòng của file (`git ls-files --eol`).
- Git: `git -c safe.directory=* …` (không sửa cấu hình global). Console cp1252: chạy test / script in tiếng Việt với `PYTHONIOENCODING=utf-8`.
- Đo tốc độ riêng (không chạy cùng lúc dựng bộ cài / bộ test - nhiễu ±20-30%).

## Môi trường làm việc
- Dự án ở `D:\APP AI PABT\PABT_PhanMem` (đường dẫn không dấu; trước 07/10/2026 là `D:\Thư mục mới\…` dạng NFD). File thật của người
  dùng (file dự án `.pabt` thật, `PABT_CHUAN_06-10-2026_QD42.xlsm` – dùng cho `PABT_EXCEL`) ở thư mục cha: chỉ đọc / thử trên bản sao.
- Windows PowerShell 5.1; `.venv` dùng Python 3.14. `build/`, `dist/`, `bo_cai/` là sản phẩm dựng.
- Máy dựng có Microsoft Word VÀ LibreOffice 26.8.2 (người dùng cho cài 03/11/2026, winget `TheDocumentFoundation.LibreOffice`): tầng PDF thứ
  hai `van_ban_trinh.chuyen_pdf_libreoffice` đã chạy thật - 4 hộ 9,6 s, bố cục trùng bản Word (khung, ngắt trang, chữ ký). Kiểm thử chạy
  qua đường Word / LibreOffice thật khi có; muốn thử nhánh "không Office" thì giả lập (`tim_libreoffice` / `co_word`), đừng gỡ phần mềm.

## graphify

This project has a knowledge graph at graphify-out/ with god nodes, community structure, and cross-file relationships.

Rules:
- When graphify-out/graph.json exists, run `graphify query "<question>"` before your first grep, search or source-file read for a codebase question, and put this rule in every subagent prompt that explores code. Read raw files only for lines the graph or an earlier read already located. Use `graphify path "<A>" "<B>"` for relationships and `graphify explain "<concept>"` for focused concepts. These return a scoped subgraph, usually much smaller than GRAPH_REPORT.md or raw grep output.
- If graphify-out/wiki/index.md exists, use it for broad navigation instead of raw source browsing.
- Read graphify-out/GRAPH_REPORT.md only for broad architecture review or when query/path/explain do not surface enough context.
- After modifying code, run `graphify update .` to keep the graph current (AST-only, no API cost).
- A committed graphify-out/graph.json is rewritten whole on every build, so a large diff to it in a pull request is expected. Do not flag it as churn or suggest skipping the graph rebuild or its hooks.

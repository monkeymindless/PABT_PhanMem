# Rà soát cấu trúc mã nguồn PABT/LARC - 05/11/2026

Số liệu đo lúc cây làm việc ở 1.0.61 chưa commit (`HEAD` là 1.0.60), nhánh `kiem-tra/bien-va-chuan-giao-dien`; sau đó đã lên 1.0.67, số dòng các file có thể đã đổi.

Chỉ đọc và phân tích, chưa sửa mã. Số liệu: `ast` trên `pabt/*.py`, graphify (12.085 nút, 357 cộng đồng).

**Phạm vi:** đây là rà soát CẤU TRÚC (kích thước, phụ thuộc, hàm trùng y hệt, thư mục gốc). CHƯA đọc logic từng module, CHƯA chạy test / `KIEM_TRA_GIAO_DIEN` / `PHAN_TICH_PHIEN_BAN`, nên chưa kết luận gì về lỗi nghiệp vụ, an toàn dữ liệu hay tốc độ. Chưa đo `di_dong/`, `bo_cai_win/`, `tests/` ngoài số dòng.

## 1. Quy mô
- `pabt/`: 153 module, 83.645 dòng. `tests/`: 164 file, 33.135 dòng. Repo theo dõi 386 file.
- 42 module `man_hinh_*` (màn hình), còn lại là nghiệp vụ / dữ liệu / tiện ích - tất cả nằm phẳng trong một thư mục.

## 2. Phát hiện
### A. Thư mục gốc lộn xộn (rủi ro thấp, lợi ích cao)
- `PABT_PhanMem/` lồng bên trong (49 MB, chưa theo dõi): chỉ có `.claude`, `.git`, `.gitignore`, `.ruff_cache`, `.venv`, KHÔNG có mã nguồn; `.git` hỏng (`fatal: bad object HEAD`, nhánh `main`). Trông như tàn dư, nhưng chưa xem `.claude` bên trong và không khôi phục được lịch sử để so; người dùng quyết định trước khi xóa.
- Thư mục icon / bộ công cụ (`LARC_Icon_3D_*`, `PABT_Icon_3D_*`, `PABT_BoCongCu_*`) cùng file zip, `.rar`, ảnh `.jpg/.png`, `.docx`, `.pdf`, `.tsx`, `.html`, `*.md` prompt rải ở gốc (chưa theo dõi bởi git).
- Đề xuất: gom vào `tai_nguyen_ngoai/` (ngoài git) hoặc `.gitignore`; file nháp `Phuong an cap nhat gia dat.py` đưa vào `cong_cu/`.
- `.venv\pyvenv.cfg` trỏ tới `C:\Users\phant\AppData\Local\Programs\Python\Python314\python.exe`; từ phiên Claude này không thấy file đó nên `.venv\Scripts\python` không chạy (báo cáo này dùng `C:\Program Files\Python314`). Chưa rõ Python đó đã gỡ thật hay do ứng dụng Claude (MSIX) ảo hóa `%LOCALAPPDATA%` - cần thử `.venv\Scripts\python --version` ở Terminal ngoài. Nếu hỏng thật: dựng lại bằng `CAI_DAT.bat`. Việc này chặn chạy test trong phiên.

### B. Hàm quá dài (khó test, khó sửa)
| Dòng | Vị trí |
|---|---|
| 404 | `nhap_don_gia.so_khop` |
| 383 / 288 / 241 | ba `__init__` trong `man_hinh.py` |
| 356 | `in_an.lap_bang_tong_hop` |
| 346 | `man_hinh_nhap_don_gia.__init__` |
| 315 | một `__init__` trong `app.py` |
| 292 | `bang_dieu_chinh.lap` |
| 279 | `nhap_excel._nhap` |
| 266 | `kiem_loi.kiem_tra` |

Hướng: `__init__` chia thành `_dung_*` theo khối giao diện; `so_khop` / `kiem_tra` chia theo quy tắc (bảng quy tắc + vòng lặp).

### C. File lớn
`giao_dien.py` 5.276, `app.py` 4.372, `man_hinh.py` 4.220, `nhap_don_gia.py` 3.384, `man_hinh_theo_doi.py` 2.693, `in_an.py` 2.269. `giao_dien.py` gộp QSS, token màu, biểu tượng, bảng, menu trái - tách được thành gói con (`giao_dien/mau.py`, `qss.py`, `bang.py`, `menu.py`) giữ nguyên `from pabt.giao_dien import ...` bằng `__init__` tái xuất.

### D. Phụ thuộc
- Trung tâm: `lap_pa` (83 nơi nhập), `tien` (70), `csdl` (56), `giao_dien` (42), `an_toan` (36) - ổn, đúng kiến trúc.
- `app` nhập 67 module (8 mức module, 59 trong hàm), `man_hinh` 34 (7 + 27): phần lớn đã nạp trễ, đúng hướng tốc độ khởi động.
- **Không có vòng nhập nào ở mức module** (đã đo: 362 cạnh mức module, 505 cạnh chỉ trong hàm), nên không có lỗi nhập vòng khi nạp. Chỉ khi gộp cả nhập trong hàm mới có vòng: `dia_phuong` <-> `toa_do`, `cap_nhat_gia_dat` <-> `nguon_gia_dat`, `man_hinh_bao_cao` <-> `man_hinh_theo_doi`, `chu_de` / `giao_dien` / `man_hinh_chan_doan` / `xem_truoc_tai_lieu`, `app` / `lenh` / `man_hinh_du_thao` / `man_hinh_tim_nhanh`, và một cụm 52 module (gồm `csdl`, `don_gia`, `an_toan`...). Đây là khớp nối logic, không phải lỗi; cụm 52 module là điểm đáng chú ý nhất vì tầng dữ liệu (`csdl`) có đường gọi ngược lên tầng trên - chưa truy cạnh cụ thể nào tạo ra cụm này.

### D2. Mã lặp
Hàm >= 8 dòng trùng Y HỆT (cùng cây cú pháp) giữa các module: chỉ 1 nhóm - `app.so_thua_dong` = `man_hinh_thong_ke._thua` (10 dòng). Phép đo này KHÔNG bắt được hàm gần giống (khác tên biến, khác vài dòng), nên chưa kết luận repo ít lặp; `PHAN_TICH_PHIEN_BAN.bat` có mục mã lặp riêng, chưa chạy.

### E. Gói hóa (đề xuất dài hạn)
Chia `pabt/` thành gói con theo tiền tố: `man_hinh/` (42), `nhap/` (`nhap_*`), `ban_in/` (`in_*`, `mau_*`, `van_ban_*`; không đặt tên `in` vì là từ khóa Python), `ban_do/`, `cap_nhat/`, `du_lieu/` (`csdl`, `tien`, `don_gia`...). Rủi ro cao: gói cập nhật `.pabtcn` / `.larcud`, `nap_cap_nhat`, PyInstaller `PABT.spec`, bộ Win7 (Python 3.8) và test đều phụ thuộc đường dẫn phẳng. Chỉ làm sau khi có bí danh tương thích và chạy đủ bộ test + `kiem_tra_toan_bo`.

## 3. Lộ trình đề xuất (từ an toàn đến rủi ro)
0. Commit phần 1.0.61 đang dở trên nhánh hiện tại; xác định `.venv` chạy được để có mốc test TRƯỚC khi sắp xếp.
1. Dọn thư mục gốc (người dùng duyệt danh sách; `PABT_PhanMem/` lồng và file tài liệu có thể chứa dữ liệu thật không tự xóa).
2. Chia các hàm > 250 dòng (không đổi hành vi, test đủ trước/sau).
3. Tách `giao_dien.py` thành gói con có tái xuất.
4. Truy cụm 52 module, gỡ đường gọi ngược từ tầng dữ liệu nếu có (không gấp: không gây lỗi nạp).
5. Gói hóa `pabt/` (chỉ khi 1-4 xong và bộ cài thử trên máy trắng; xem xét có cần làm không - lợi ích chủ yếu là dễ tìm file, rủi ro cao).

Mỗi bước theo quy trình bắt buộc của CLAUDE.md (tăng phiên bản, `PHAN_TICH_PHIEN_BAN`, `KIEM_TRA_GIAO_DIEN`, test Qt6 + Qt5, `vermin`).

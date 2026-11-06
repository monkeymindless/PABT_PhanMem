#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
cai_dat_bo_dieu_phoi_claude.py — Kịch bản tự động cài đặt Bộ Điều Phối Nhóm Mô Hình AI Khép Kín
(5 Subagents + 3 Slash Commands + 1 Skill) vào thẳng thư mục `.claude/` cho Claude Code.

Đặt tệp này tại thư mục gốc dự án (`D:\\APP AI PABT\\PABT_PhanMem\\`) cùng với `larc_ai_khep_kin.py`
và chạy:
    .venv\\Scripts\\python cai_dat_bo_dieu_phoi_claude.py
"""
from __future__ import annotations

import argparse
import datetime as _dt
import shutil
import sys
from pathlib import Path
from typing import Dict, List


# ==============================================================================
# ĐỊNH NGHĨA 5 SUBAGENTS CHUYÊN TRÁCH CHO CLAUDE CODE (.claude/agents/*.md)
# ==============================================================================

AGENTS: Dict[str, str] = {
    "larc-hunter-kien-truc.md": """---
name: larc-hunter-kien-truc
description: "Subagent Giai đoạn 0 (Kiến trúc & Dọn dẹp): Truy tìm vòng lặp import ngầm (SCC), hàm chết không có caller, tệp rác ở thư mục gốc và skill trùng lặp. Đảm bảo giữ nguyên 100% cấu trúc pabt/ và tests/."
---

Bạn là **Agent-0 (Kiến trúc & Dọn dẹp Sạch)** trong hệ thống AI Khép Kín của phần mềm LARC (PABT).

### Quy tắc bắt buộc:
1. Khi `graphify-out/graph.json` tồn tại, LUÔN chạy `graphify query "<câu hỏi>"` hoặc `graphify path "<A>" "<B>"` trước khi dùng grep hoặc đọc file mã nguồn.
2. Tuyệt đối KHÔNG đổi tên, KHÔNG di chuyển và KHÔNG xóa bất kỳ mô-đun nào trong `pabt/` (165 tệp), `tests/`, `chay.py` và các công cụ kiểm tra ở gốc repo.
3. Mọi tệp câu lệnh nháp cũ ở thư mục gốc (`master_prompt_*.md`, `lenh_claude_*.md`, `h_ng_d_n_*.md`, `pabt_version_and_valuation_engine.py.py`, `Phuong an cap nhat gia dat.py`, thư mục lồng `PABT_PhanMem/`) và các skill trùng/lệch hệ sinh thái (`ra-soat-giao-dien-nang-cap`, `ui-ux-pro-max`, `frontend-design`) chỉ được di chuyển an toàn vào `_luu_tru_don_dep/` qua lệnh:
   `.venv\\Scripts\\python larc_ai_khep_kin.py --don-dep --thuc-thi`
4. Truy tìm các hàm nội bộ (`_ten_ham`) trong `pabt/` không có bất kỳ lời gọi nào (hàm có decorator như `@atexit.register` KHÔNG phải hàm chết: đọc dòng trên `def` trước khi kết luận) và các điểm import ngược từ tầng nền (`an_toan.py`, `phan_quyen.py`, `csdl.py`) lên tầng nghiệp vụ cao (`lap_pa.py`, `may_chu.py`).
""",
    "larc-hunter-duong-lenh.md": """---
name: larc-hunter-duong-lenh
description: "Subagent Giai đoạn 1 (Đường lệnh, Tín hiệu & Quyền ghi): Truy tìm nút chết, lệnh QAction ẩn, đường lệnh đi lòng vòng qua parentWidget() làm sập CuaSoLapPA, và các hàm ghi CSDL thiếu kiem_quyen."
---

Bạn là **Agent-1 (Truy tìm Đường lệnh & Quyền ghi CSDL)** trong hệ thống AI Khép Kín của phần mềm LARC (PABT).

### Quy tắc bắt buộc:
1. Khi `graphify-out/graph.json` tồn tại, LUÔN chạy `graphify query` hoặc `graphify path` trước khi grep hoặc đọc file.
2. Trước khi sửa bất kỳ đường lệnh nào, kiểm tra `docs/LICH_SU_PHAT_TRIEN.md` và `CLAUDE.md` để nắm quy tắc:
   - Mỗi lệnh một chỗ (`pabt/lenh.py`), nút/menu dùng chung `QAction` của `self.lenh`.
   - Không đưa các nút ẩn giữ trạng thái (`b_bo`, `b_dan`, `btn_toggle_preview`, `dai_dinh_danh`, `dai_cong`) lên lại giao diện `CuaSoLapPA`.
3. Các trọng tâm truy tìm và xử lý:
   - **Chặn đường lệnh đi lòng vòng qua `parentWidget()`**: Tại `pabt/giao_dien.py` (`_BoChonVung.dem()`), vòng lặp `while cha is not None:` phải dừng ở biên cửa sổ (`if cha.isWindow(): break`) để bảng `_BangDong` (`QTableView`) trong hộp thoại con `HopTinhGiaDat` không gọi nhầm `CuaSoLapPA.cap_nhat_bo_dem`.
   - **Bảo vệ tương thích `QTableView` & đối tượng C++ đã hủy**: Tại `pabt/man_hinh.py` (`_tinh_vung_chon`, `_xoa_chon_vung`), kiểm tra `hasattr(bang, "horizontalHeaderItem")` (nếu không có thì lấy `bang.model().headerData(ix.column(), Qt.Orientation.Horizontal)`) và bọc `try...except RuntimeError:` khi truy cập `self._chu_vung`.
   - **Kiểm quyền đường ghi CSDL**: Mọi hàm ghi công khai (`nhap_chi_tiet.ghi`, `kiem_loi.sua_tu_dong`, `ban_do_cad.luu`, `ban_do_luu.*`, `du_thao.*`, `quan_ly.*`, `theo_doi.*`) phải có `kiem_quyen` / `kiem_ho_nhan_viec` và `ghi_nhat_ky`.
""",
    "larc-hunter-bao-mat-so-lieu.md": """---
name: larc-hunter-bao-mat-so-lieu
description: "Subagent Giai đoạn 2 & 3 (Bảo mật & Số liệu Decimal): Truy tìm lỗ hổng trigger .pabt, SQL IN quá 999 biến, ép kiểu float/round() sai quy tắc làm tròn ROUND_HALF_UP, và gọi lặp doc_phuong_an."
---

Bạn là **Agent-2 (Bảo mật & Số liệu Nghiệp vụ)** trong hệ thống AI Khép Kín của phần mềm LARC (PABT).

### Quy tắc bắt buộc:
1. Khi `graphify-out/graph.json` tồn tại, LUÔN chạy `graphify query` trước khi grep hoặc đọc file.
2. **Bảo mật (Giai đoạn 2)**:
   - Tại `pabt/csdl.py` (`go_trigger_la`): Không chỉ kiểm tra tên trigger bắt đầu bằng `khoa_`, `_pq_`, `_ht_`, `_kt_`, mà phải đối chiếu cả nội dung cột `sql` trong `sqlite_master` chỉ chứa biểu thức `SELECT RAISE(ABORT,` hợp lệ để chống tệp `.pabt` cài trigger độc hại giả mạo tiền tố.
   - Tại `pabt/app.py:1648`: Chia nhỏ danh sách mã hộ trong mệnh đề `WHERE ma_ho IN (...)` theo từng lô <= 500 phần tử để không vượt ngưỡng 999 tham số của SQLite trên bản Win7 Python 3.8.
   - Tại `pabt/an_toan.py` (`kiem_tra_xml`) và `pabt/khoa.py` (`mo_ta`): Quét toàn diện khai báo `<!ENTITY` và bắt ngoại lệ `ValueError` khi tệp `.khoa` bị hỏng.
3. **Số liệu Decimal (Giai đoạn 3)**:
   - Mọi số tiền, diện tích, số lượng, tỷ lệ phải tính bằng `Decimal` (`pabt/tien.py`: `D`, `doc_so_vn`, `lam_tron` = `ROUND_HALF_UP`).
   - `round()` trên tọa độ, điểm ảnh, tỷ lệ phần trăm hiển thị không phải lỗi; chỉ xử lý khi là tiền / diện tích / số lượng của nghiệp vụ.
   - Không đổi `int(float(...))` sang `int(Decimal(...))` khi `except` chỉ bắt `ValueError`: ô chữ sẽ ném `InvalidOperation`.
""",
    "larc-hunter-giao-dien-qt5.md": """---
name: larc-hunter-giao-dien-qt5
description: "Subagent Giai đoạn 4, 5 & 6 (Giao diện WCAG Sáng/Tối, Bố cục 1093x614, Tương thích Python 3.8 + Qt5 & Chống rò rỉ): Truy tìm màu hex cứng trong HTML/QSS, chữ bị cắt, nút đè nhau và hộp thoại rò rỉ."
---

Bạn là **Agent-3 (Giao diện WCAG/TOKEN, Tương thích Qt5 & Tốc độ)** trong hệ thống AI Khép Kín của phần mềm LARC (PABT).

### Quy tắc bắt buộc:
1. Khi `graphify-out/graph.json` tồn tại, LUÔN chạy `graphify query` trước khi grep hoặc đọc file.
2. **Màu sắc & Tương phản Sáng/Tối (WCAG AA >= 4.5:1)**:
   - Cấm viết mã màu `#RRGGBB` trực tiếp trong `setStyleSheet` hoặc trong chuỗi HTML `setText("<b style='color:#1E3A5F'>...")`.
   - Thay toàn bộ 23 điểm màu hex cứng trong `pabt/app.py`, `pabt/man_hinh.py`, `pabt/man_hinh_cap_nhat.py`, `pabt/man_hinh_cay.py`, `pabt/man_hinh_ghep_cot.py`, `pabt/man_hinh_theo_doi.py` bằng bảng màu động theo tông nền (`TOKEN` / `bang_mau(che_do_toi_hien_tai())` / `mau_theo_tong`). Nếu số mã màu giảm, cập nhật lại `tests/test_p1_giao_dien.MOC_MAU`.
3. **Bố cục ở `1093x614` (`1366x768 @ 125% DPI`)**:
   - Không đổi chiều cao 62px của thẻ KPI cửa sổ chính; bật rút gọn chữ (`…`) kèm `setToolTip` đầy đủ cho dòng phụ thẻ KPI và tiêu đề bộ đơn giá trong `man_hinh_don_gia.py`.
   - Nới `minimumWidth` cho nút `"Thuộc tính máy in"`, `"Thiết lập trang"` trong `HopIn` và nút `"▾"` trong `CuaSoLapPA` để triệt tiêu lỗi `CHAT_NGANG` trong `bo_cuc.tsv`.
   - Mọi nút bị khóa (`setEnabled(False)`) phải có `toolTip` giải thích rõ lý do khóa.
4. **Tương thích Python 3.8 + Qt5 & Chống rò rỉ**:
   - Mọi tệp trong `pabt/` phải có `from __future__ import annotations`.
   - Thêm tiền tố `r\"\"\"` cho docstring của `kiem_tra_bo_cuc.py` để xóa `SyntaxWarning: "\\S"`.
   - Trong `kiem_tra_giao_dien.py`, chụp ảnh hộp thoại đang mở qua `QApplication.activeModalWidget() or w`.
   - Đảm bảo `HopDoiChieu` và các hộp thoại tạm được dọn qua `don_hop_da_dong` / `_thung_cho_xoa` để `kiem_tra_ro_ri.py` báo 0 rò rỉ.
""",
    "larc-gatekeeper.md": """---
name: larc-gatekeeper
description: "Subagent Giai đoạn 7 & 8 (Cổng Gác Chất Lượng & Tự Động Rollback): Chụp snapshot trước khi sửa, kiểm tra 6 Cổng Gác, chạy unittest Qt6/Qt5, xuất đủ 7 báo cáo Đại Phẫu và tự động rollback nếu có lỗi."
---

Bạn là **Agent-4 (Gatekeeper — Cổng Gác Chất Lượng & Tự Động Rollback)** trong hệ thống AI Khép Kín của phần mềm LARC (PABT).

### Quy trình thực thi bắt buộc cho mọi đợt chỉnh sửa:
1. **Trước khi sửa**:
   Chạy `.venv\\Scripts\\python larc_ai_khep_kin.py --chup-snapshot --ten-dot <ten_dot>`
2. **Sau khi sửa**:
   - Chạy kiểm tra 6 Cổng Gác tự động:
     `.venv\\Scripts\\python larc_ai_khep_kin.py --kiem-cong --ten-dot <ten_dot> --tu-khoi-phuc`
   - Chạy kiểm thử tự động (với `QT_QPA_PLATFORM=offscreen` và `PYTHONIOENCODING=utf-8`):
     `.venv\\Scripts\\python -m unittest discover -s tests -t .`
   - Chạy bộ công cụ kiểm toán chuyên sâu:
     - `.venv\\Scripts\\python kiem_toan_lenh.py`
     - `.venv\\Scripts\\python kiem_tra_bo_cuc.py ket_qua_kiem_tra\\bo_cuc.tsv 1093,614`
     - `.venv\\Scripts\\python kiem_tra_ro_ri.py ket_qua_kiem_tra\\ro_ri.tsv`
3. **Xuất bộ 7 báo cáo Đại Phẫu**:
   - Chạy `.venv\\Scripts\\python larc_ai_khep_kin.py --dai-phau` để ghi đủ 7 tệp (`00_tong_ket.md` -> `06_tuong_thich_toc_do.md`) vào `ket_qua_kiem_tra\\DaiPhau_<giờ>\\`.
   - Sau khi mọi cổng đều XANH, chạy `graphify update .` để đồng bộ đồ thị mã nguồn.
""",
}


# ==============================================================================
# ĐỊNH NGHĨA 3 LỆNH SLASH COMMANDS CHO CLAUDE CODE (.claude/commands/*.md)
# ==============================================================================

COMMANDS: Dict[str, str] = {
    "truy-tim-loi.md": """---
description: "Kích hoạt Đội Truy Tìm 4 Subagents quét toàn diện 9 giai đoạn Đại Phẫu (Kiến trúc, Đường lệnh, Bảo mật, Số liệu, Giao diện Sáng/Tối, Qt5, Rò rỉ) và xuất đủ 7 báo cáo mà không sửa mã nguồn."
---

Hãy đóng vai trò là **BỘ ĐIỀU PHỐI TRUY TÌM LỖI KHÉP KÍN (READ-ONLY HUNTER ORCHESTRATOR)** cho phần mềm LARC.
Trong lệnh này, bạn CHỈ ĐỌC, ĐO ĐẠC và CHẠY CÔNG CỤ KIỂM TOÁN, **tuyệt đối không sửa mã nguồn trong `pabt/`**.

Hãy thực hiện tuần tự hoặc gọi song song các Subagents (`larc-hunter-kien-truc`, `larc-hunter-duong-lenh`, `larc-hunter-bao-mat-so-lieu`, `larc-hunter-giao-dien-qt5`):
1. Sử dụng `graphify query` trước khi đọc file mã nguồn.
2. Chạy `.venv\\Scripts\\python larc_ai_khep_kin.py --dai-phau` để quét tĩnh toàn bộ 165 mô-đun và sinh 7 tệp báo cáo chuẩn vào `ket_qua_kiem_tra\\DaiPhau_<giờ>\\`.
3. Chạy tiếp các công cụ đo đạc thực tế (với `QT_QPA_PLATFORM=offscreen`, `PYTHONIOENCODING=utf-8`):
   - `.venv\\Scripts\\python kiem_toan_lenh.py`
   - `.venv\\Scripts\\python kiem_tra_bo_cuc.py ket_qua_kiem_tra\\bo_cuc.tsv 1093,614`
   - `.venv\\Scripts\\python kiem_tra_ro_ri.py ket_qua_kiem_tra\\ro_ri.tsv`
4. Tổng hợp toàn bộ phát hiện (nút chết, lệnh ẩn, đường lệnh đi lòng vòng qua `parentWidget()`, hàm ghi thiếu `kiem_quyen`, màu hex cứng gây tàng hình ở chế độ tối, chữ bị cắt ở `1093x614`, tệp rác ở gốc) thành bảng ưu tiên P0 -> P3 kèm tọa độ `tệp:dòng` chính xác.
""",
    "dai-phau-khep-kin.md": """---
description: "Chạy vòng lặp Đại Phẫu Khép Kín toàn trình (Giai đoạn 0-8): Dọn dẹp tệp rác an toàn, chụp Snapshot, điều phối 5 Subagents sửa 4 đợt (P0-P3), kiểm tra 6 Cổng Gác và tự động Rollback nếu lỗi."
---

Bạn là **ĐIỀU PHỐI VIÊN TRUNG TÂM (CLOSED-LOOP ORCHESTRATOR)** của phần mềm LARC.
Hãy điều phối 5 Subagents (`larc-hunter-kien-truc`, `larc-hunter-duong-lenh`, `larc-hunter-bao-mat-so-lieu`, `larc-hunter-giao-dien-qt5`, `larc-gatekeeper`) thực hiện quy trình Đại Phẫu Khép Kín:

1. **Giai đoạn 0 (Dọn dẹp an toàn — giữ nguyên 100% `pabt/` và `tests/`)**:
   - Chạy `.venv\\Scripts\\python larc_ai_khep_kin.py --don-dep --thuc-thi` để đưa các tệp prompt nháp cũ ở gốc và 3 skill trùng/lệch (`ra-soat-giao-dien-nang-cap`, `ui-ux-pro-max`, `frontend-design`) vào `_luu_tru_don_dep/`.
2. **Giai đoạn 1–6 (Thực thi 4 Đợt Sửa Khép Kín có khóa Snapshot & Tự động Rollback)**:
   - **Đợt 1 (`dot_1_duong_lenh`)**: Chụp snapshot -> Sửa `_BoChonVung.dem()` dừng tại `isWindow()` trong `pabt/giao_dien.py:4978`, sửa `_tinh_vung_chon` & `_xoa_chon_vung` hỗ trợ `QTableView` và chống C++ deleted trong `pabt/man_hinh.py:2362-2400`, dọn rò rỉ `HopDoiChieu` -> Chạy `--kiem-cong --ten-dot dot_1_duong_lenh --tu-khoi-phuc` + unittest.
   - **Đợt 2 (`dot_2_giao_dien`)**: Chụp snapshot -> Thay 23 điểm màu hex cứng trong HTML label sang bảng màu động theo tông nền (`TOKEN`/`bang_mau`), nới chiều rộng các nút bị cắt chữ ở `1093x614`, thêm `r\"\"\"` vào `kiem_tra_bo_cuc.py`, sửa chụp hộp thoại modal trong `kiem_tra_giao_dien.py` -> Chạy `--kiem-cong --ten-dot dot_2_giao_dien --tu-khoi-phuc` + unittest.
   - **Đợt 3 (`dot_3_bao_mat_so_lieu`)**: Chụp snapshot -> Siết kiểm tra thân SQL trong `csdl.go_trigger_la`, bổ sung `kiem_quyen` cho các đường ghi phụ (`nhap_chi_tiet.ghi`, `kiem_loi.sua_tu_dong`, `ban_do_cad.luu`, `ban_do_luu.*`, `du_thao.*`, `quan_ly.*`, `theo_doi.*`), chia lô 500 mã hộ cho `WHERE ma_ho IN` tại `pabt/app.py:1648` -> Chạy `--kiem-cong --ten-dot dot_3_bao_mat_so_lieu --tu-khoi-phuc` + unittest.
   - **Đợt 4 (`dot_4_kien_truc`)**: Chụp snapshot -> Chỉ xóa hàm nội bộ đã xác minh không có lời gọi, không decorator, không nối tín hiệu theo tên -> Chạy `--kiem-cong --ten-dot dot_4_kien_truc --tu-khoi-phuc` + toàn bộ unittest.
3. **Giai đoạn 7 & 8 (Tổng kết & Đồng bộ đồ thị)**:
   - Chạy `.venv\\Scripts\\python larc_ai_khep_kin.py --dai-phau` để xuất bộ 7 báo cáo mới nhất vào `ket_qua_kiem_tra\\DaiPhau_<giờ>\\`.
   - Chạy `graphify update .` và báo cáo bảng kết quả trước/sau cho người dùng.
""",
    "sua-khep-kin.md": """---
description: "Tinh chỉnh phẫu thuật 1 màn hình, 1 nút bấm hoặc 1 câu lệnh bất kỳ theo quy trình 5 bước có khóa Snapshot và 6 Cổng Gác chống hỏng dây chuyền."
---

Yêu cầu cần tinh chỉnh: **$ARGUMENTS**

Hãy thực hiện nghiêm ngặt **QUY TRÌNH KHÉP KÍN 5 BƯỚC CHỐNG HỎNG DÂY CHUYỀN**:
1. **Bước 1 (Truy vết lịch sử & Đồ thị)**:
   - Chạy `graphify query` và `grep` tên màn hình/hàm liên quan trong `docs/LICH_SU_PHAT_TRIEN.md` và `CLAUDE.md` để nắm toàn bộ quyết định cũ của người dùng.
   - Liệt kê các hộp thoại/lớp dùng chung widget hoặc tín hiệu với vị trí sắp sửa.
2. **Bước 2 (Chụp Snapshot khóa trạng thái)**:
   - Chạy `.venv\\Scripts\\python larc_ai_khep_kin.py --chup-snapshot --ten-dot sua_khep_kin`
3. **Bước 3 (Phẫu thuật tối thiểu)**:
   - Chỉ sửa đúng dòng cần thiết, giữ nguyên 100% cấu trúc lớp, chữ ký hàm, thuộc tính và kiểu xuống dòng của tệp.
4. **Bước 4 (Kiểm định qua 6 Cổng Gác & Unittest)**:
   - Chạy `.venv\\Scripts\\python larc_ai_khep_kin.py --kiem-cong --ten-dot sua_khep_kin --tu-khoi-phuc`
   - Chạy unittest của mô-đun liên quan với `QT_QPA_PLATFORM=offscreen` và `PYTHONIOENCODING=utf-8`.
5. **Bước 5 (Kết luận)**:
   - Chỉ hoàn tất khi cả 6 Cổng Gác đều XANH; chạy `graphify update .` và báo cáo rõ những dòng đã sửa.
""",
}


SKILL_CONTENT = """---
name: larc-khep-kin
description: "Hệ thống điều phối nhóm mô hình AI khép kín (Closed-Loop Multi-Agent Orchestrator) chuyên biệt cho phần mềm LARC (PABT) trên Claude Code. Tự động kích hoạt khi người dùng yêu cầu rà soát, đại phẫu, truy tìm điểm chết, sửa lỗi giao diện, tinh chỉnh câu lệnh hoặc dọn dẹp mã nguồn."
---

# Quy Trình Điều Phối AI Khép Kín LARC (9 Giai Đoạn Đại Phẫu & 6 Cổng Gác)

Mỗi khi thực hiện rà soát, tinh chỉnh giao diện hoặc sửa lỗi trên phần mềm LARC, bạn BẮT BUỘC tuân thủ:
1. **Truy vấn `graphify` trước**: Chạy `graphify query` hoặc `graphify path` trước khi grep/đọc file thô.
2. **Đọc lịch sử quyết định**: Kiểm tra `CLAUDE.md` và `docs/LICH_SU_PHAT_TRIEN.md` trước khi chạm vào bất kỳ màn hình nào.
3. **Chụp Snapshot trước khi sửa**:
   `.venv\\Scripts\\python larc_ai_khep_kin.py --chup-snapshot --ten-dot <ten_dot>`
4. **Kiểm tra 6 Cổng Gác tự động sau khi sửa (kèm tự động Rollback nếu vi phạm)**:
   `.venv\\Scripts\\python larc_ai_khep_kin.py --kiem-cong --ten-dot <ten_dot> --tu-khoi-phuc`
5. **Bảo toàn 100% kiến trúc**: Tuyệt đối không xóa/đổi tên bất kỳ tệp nào trong `pabt/`, `tests/`, `chay.py` và các công cụ kiểm tra ở gốc repo.
"""


SKILL_GAY_NHIEU = ["ra-soat-giao-dien-nang-cap", "ui-ux-pro-max", "frontend-design"]
THU_MUC_SAO_LUU = "_sao_luu_dieu_phoi"
TEP_PHU_THUOC = ["larc_ai_khep_kin.py", "chay.py", "pabt/__init__.py"]


def _danh_sach_tep(tm_claude: Path) -> Dict[Path, str]:
    """Toàn bộ tệp bộ điều phối sẽ cài: đường dẫn đích -> nội dung."""
    ds: Dict[Path, str] = {}
    for ten, nd in AGENTS.items():
        ds[tm_claude / "agents" / ten] = nd
    for ten, nd in COMMANDS.items():
        ds[tm_claude / "commands" / ten] = nd
    ds[tm_claude / "skills" / "larc-khep-kin" / "SKILL.md"] = SKILL_CONTENT
    return ds


def _doc(duong_dan: Path) -> str:
    return duong_dan.read_bytes().decode("utf-8").replace("\r\n", "\n")


def _ghi(duong_dan: Path, noi_dung: str) -> None:
    duong_dan.parent.mkdir(parents=True, exist_ok=True)
    duong_dan.write_bytes(noi_dung.encode("utf-8"))


def kiem_phu_thuoc(goc: Path) -> int:
    """Số lỗi chặn: thiếu tệp nền của dự án hoặc larc_ai_khep_kin.py không biên dịch được."""
    loi = 0
    for t in TEP_PHU_THUOC:
        if not (goc / t).is_file():
            print(f"  ✗ THIẾU {t} - '{goc}' không phải thư mục gốc PABT_PhanMem")
            loi += 1
    if loi == 0:
        try:  # chỉ biên dịch trong bộ nhớ, không ghi __pycache__
            compile(_doc(goc / "larc_ai_khep_kin.py"), "larc_ai_khep_kin.py", "exec")
            print("  ✓ larc_ai_khep_kin.py biên dịch được")
        except SyntaxError as e:
            print(f"  ✗ larc_ai_khep_kin.py lỗi cú pháp dòng {e.lineno}: {e.msg}")
            loi += 1
    # Chỉ cảnh báo (không chặn)
    if not (goc / ".venv" / "Scripts" / "python.exe").is_file():
        print("  ! Chưa có .venv (chạy CAI_DAT.bat) - các lệnh .venv\\Scripts\\python sẽ không chạy")
    if shutil.which("graphify") is None:
        print("  ! Không thấy 'graphify' trên PATH - quy tắc graphify query sẽ không dùng được")
    elif not (goc / "graphify-out" / "graph.json").is_file():
        print("  ! Chưa có graphify-out/graph.json - chạy 'graphify update .' để dựng đồ thị")
    return loi


def kiem_tra(goc: Path) -> int:
    """Đối chiếu tệp đã cài với bản chuẩn. Trả 0 nếu đủ và khớp."""
    ds = _danh_sach_tep(goc / ".claude")
    thieu = lech = 0
    for dd, nd in ds.items():
        rel = dd.relative_to(goc).as_posix()
        if not dd.is_file():
            print(f"  ✗ thiếu : {rel}")
            thieu += 1
        elif _doc(dd) != nd.replace("\r\n", "\n"):
            print(f"  ~ khác bản chuẩn: {rel}")
            lech += 1
        else:
            print(f"  ✓ khớp  : {rel}")
    print(f"Tổng {len(ds)} tệp: thiếu {thieu}, khác {lech}.")
    return 0 if thieu == 0 and lech == 0 else 1


def cai_dat(goc: Path, cach_ly_skill: bool = False) -> int:
    tm_claude = goc / ".claude"
    print("=" * 72)
    print("CÀI ĐẶT BỘ ĐIỀU PHỐI TRUY TÌM & CỔNG GÁC KHÉP KÍN CHO CLAUDE CODE")
    print(f"Thư mục dự án: {goc}")
    print("=" * 72)
    if kiem_phu_thuoc(goc):
        print("DỪNG: chưa đủ điều kiện cài. Không ghi gì.")
        return 2

    gio = _dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    tm_sao_luu = tm_claude / THU_MUC_SAO_LUU / gio
    moi = cap_nhat = giu = 0
    for dd, nd in _danh_sach_tep(tm_claude).items():
        rel = dd.relative_to(goc).as_posix()
        if dd.is_file():
            if _doc(dd) == nd.replace("\r\n", "\n"):
                giu += 1
                print(f"  = giữ nguyên : {rel}")
                continue
            sl = tm_sao_luu / dd.relative_to(tm_claude)  # sao lưu bản người dùng đã sửa
            sl.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(dd, sl)
            _ghi(dd, nd)
            cap_nhat += 1
            print(f"  ↻ cập nhật   : {rel}  (bản cũ -> {sl.relative_to(goc).as_posix()})")
        else:
            _ghi(dd, nd)
            moi += 1
            print(f"  + tạo mới    : {rel}")

    if cach_ly_skill:
        # Chỉ khi người dùng yêu cầu rõ (--cach-ly-skill): chuyển, không xóa.
        tm_lt = goc / "_luu_tru_don_dep" / f"dot_{gio[:8]}" / "05_skills_trung_hoac_web"
        for ten in SKILL_GAY_NHIEU:
            nguon = tm_claude / "skills" / ten
            if nguon.exists():
                dich = tm_lt / ten
                tm_lt.mkdir(parents=True, exist_ok=True)
                if dich.exists():
                    dich = tm_lt / f"{ten}_{gio}"
                shutil.move(str(nguon), str(dich))
                print(f"  > cách ly skill: {ten} -> {dich.relative_to(goc).as_posix()}")
    else:
        con = [t for t in SKILL_GAY_NHIEU if (tm_claude / "skills" / t).exists()]
        if con:
            print(f"  i Còn skill dễ trùng: {', '.join(con)} (thêm --cach-ly-skill nếu muốn chuyển đi, không xóa)")

    print("-" * 72)
    print(f"Mới {moi}, cập nhật {cap_nhat}, giữ nguyên {giu}. Không đụng tới pabt/, tests/, settings.json.")
    print("Mở LẠI Claude Code tại thư mục dự án (để nạp agent/lệnh mới) rồi gõ:")
    print("  • /truy-tim-loi          : quét 9 giai đoạn Đại Phẫu, chỉ đọc, không sửa mã")
    print("  • /dai-phau-khep-kin     : dọn dẹp + sửa 4 đợt có Snapshot / 6 Cổng Gác / rollback")
    print("  • /sua-khep-kin <mô tả>  : sửa 1 màn hình / nút / lệnh có Cổng Gác bảo vệ")
    print("Kiểm lại bất cứ lúc nào: CAI_DAT_BO_DIEU_PHOI.bat --kiem-tra   |   Gỡ: --go")
    print("=" * 72)
    return 0


def go_cai_dat(goc: Path) -> int:
    """Gỡ đúng các tệp bộ này tạo ra (chỉ khi còn khớp bản chuẩn; bản đã sửa thì giữ lại)."""
    tm_claude = goc / ".claude"
    for dd, nd in _danh_sach_tep(tm_claude).items():
        rel = dd.relative_to(goc).as_posix()
        if not dd.is_file():
            continue
        if _doc(dd) != nd.replace("\r\n", "\n"):
            print(f"  ! giữ lại (đã bị sửa tay): {rel}")
            continue
        dd.unlink()
        print(f"  - đã gỡ: {rel}")
        try:
            dd.parent.rmdir()  # chỉ xóa thư mục rỗng; agents/commands/skills dùng chung sẽ không rỗng
        except OSError:
            pass
    return 0


def main(argv: List[str]) -> int:
    for luong in (sys.stdout, sys.stderr):  # console cp1252 không in được ✓ / tiếng Việt
        try:
            luong.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
        except Exception:
            pass
    ap = argparse.ArgumentParser(description="Cài Bộ Điều Phối Truy Tìm & Cổng Gác Khép Kín (Claude Code) cho PABT_PhanMem")
    ap.add_argument("thu_muc", nargs="?", default=None, help="Thư mục gốc dự án (mặc định: thư mục chứa tệp này)")
    ap.add_argument("--kiem-tra", action="store_true", help="Chỉ kiểm tra tệp đã cài, không ghi gì")
    ap.add_argument("--go", action="store_true", help="Gỡ các tệp bộ điều phối đã cài (giữ bản sửa tay)")
    ap.add_argument("--cach-ly-skill", action="store_true", help="Chuyển 3 skill dễ trùng vào _luu_tru_don_dep (không xóa)")
    a = ap.parse_args(argv)
    goc = Path(a.thu_muc).resolve() if a.thu_muc else Path(__file__).resolve().parent
    if a.kiem_tra:
        return max(kiem_phu_thuoc(goc), kiem_tra(goc))
    if a.go:
        return go_cai_dat(goc)
    return cai_dat(goc, a.cach_ly_skill)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

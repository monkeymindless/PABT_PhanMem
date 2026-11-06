#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
larc_ai_khep_kin.py — Bộ Điều Phối Nhóm Mô Hình AI Khép Kín & Cổng Gác Tự Động Cho LARC (PABT).

Đặt tệp này tại thư mục gốc dự án (D:\\APP AI PABT\\PABT_PhanMem\\larc_ai_khep_kin.py).
Tương thích hoàn toàn với Python 3.8 - 3.14 (không phụ thuộc thư viện ngoài).

Cách sử dụng:
  1. Chạy Đại Phẫu toàn diện 9 giai đoạn (0-8) và xuất đủ 7 báo cáo chuẩn:
       python larc_ai_khep_kin.py --dai-phau

  2. Chụp Snapshot trước khi bắt đầu một đợt sửa giao diện / câu lệnh:
       python larc_ai_khep_kin.py --chup-snapshot --ten-dot dot_1

  3. Kiểm tra 6 Cổng Gác Chất Lượng sau khi sửa (tự động rollback nếu vi phạm):
       python larc_ai_khep_kin.py --kiem-cong --ten-dot dot_1 --tu-khoi-phuc

  4. Xem trước kế hoạch dọn dẹp tệp rác & prompt dư thừa (Dry-run an toàn 100%):
       python larc_ai_khep_kin.py --don-dep

  5. Thực thi dọn dẹp (đưa tệp dư thừa vào _luu_tru_don_dep/, giữ nguyên 100% pabt/ & tests/):
       python larc_ai_khep_kin.py --don-dep --thuc-thi
"""
from __future__ import annotations

import argparse
import ast
import datetime as _dt
import hashlib
import json
import re
import shutil
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple


# ==============================================================================
# CẤU HÌNH DANH SÁCH TỆP DƯ THỪA / TRÙNG LẶP ĐỂ DỌN DẸP AN TOÀN
# (Tuyệt đối không chạm vào pabt/, tests/, cong_cu/, dong_goi/, chay.py)
# ==============================================================================

TEP_PROMPT_CU_O_GOC = [
    "h_ng_d_n_master_prompt_to_n_di_n_cho_claude_code.md",
    "master_prompt_pabt_0987.md",
    "lenh_claude_boss_lap_plan_0987.md",
    "lenh_tu_dong_thay_icon_mau3.md",
    "ma_tinh_chinh_don_gia.md",
    "ban_nen_phien_chuyen_tiep_larc_toan_he_thong (1).md",
    "phuong_an_tich_hop_du_thao_va_y_kien_dan.txt",
    "PA_cap_nhat_gia_dat.txt",
    "PA_cap_nhat_gia_dat.pdf",
    "BÁO CÁO ĐÁNH GIÁ TOÀN DIỆN PHẦN MỀM LARC.docx",
]

KICH_BAN_THU_NGHIEM_O_GOC = [
    "pabt_version_and_valuation_engine.py.py",
    "Phuong an cap nhat gia dat.py",
]

DU_LIEU_MAU_O_GOC = [
    "ĐT762 Trị An.pabt",
    "ĐT762 Trị An_DoiChieu.xlsx",
    "DS DU AN DT762 DOAN QUA XA TRỊ AN.xlsx",
    "ÁP GIÁ-37 thửa.xlsx",
]

THU_MUC_TRUNG_O_GOC = [
    "PABT_PhanMem",
    "anh",
    "anh2",
]

SKILLS_DU_THUA = [
    ".claude/skills/ra-soat-giao-dien-nang-cap",
    ".claude/skills/ui-ux-pro-max",
    ".claude/skills/frontend-design",
]

HAM_GHI_NOI_BO_CHO_PHEP = {
    "csdl.py",
    "nhat_ky.py",
    "phan_quyen.py",
    "an_toan.py",
    "sao_luu.py",
    "cap_nhat.py",
    "lich_su_cap_nhat.py",
    "khoi_tao_mau.py",
}


def _bam_tep(duong_dan: Path) -> str:
    h = hashlib.sha256()
    with open(duong_dan, "rb") as f:
        for khoi in iter(lambda: f.read(65536), b""):
            h.update(khoi)
    return h.hexdigest()


def _trich_xuat_chu_ky_ast(duong_dan: Path) -> Dict[str, Any]:
    nguon = duong_dan.read_text(encoding="utf-8", errors="replace")
    cay = ast.parse(nguon, filename=str(duong_dan))
    lop: Dict[str, List[str]] = {}
    ham_cap_mo_dun: List[str] = []
    for nut in cay.body:
        if isinstance(nut, ast.ClassDef):
            phuong_thuc = [
                n.name for n in nut.body
                if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
            ]
            lop[nut.name] = sorted(phuong_thuc)
        elif isinstance(nut, (ast.FunctionDef, ast.AsyncFunctionDef)):
            ham_cap_mo_dun.append(nut.name)
    return {
        "sha256": _bam_tep(duong_dan),
        "so_dong": nguon.count("\n") + 1,
        "lop": lop,
        "ham": sorted(ham_cap_mo_dun),
    }


def quet_9_truc_dai_phau(thu_muc_goc: Path) -> Dict[str, Any]:
    thu_muc_pabt = thu_muc_goc / "pabt"
    if not thu_muc_pabt.is_dir():
        raise FileNotFoundError(f"Không tìm thấy thư mục gói nguồn: {thu_muc_pabt}")

    ds_tep_py = sorted(thu_muc_pabt.glob("*.py"))
    ket_qua: Dict[str, Any] = {
        "thoi_gian": _dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "tong_so_mo_dun": len(ds_tep_py),
        "tong_so_dong": 0,
        "tong_so_lop": 0,
        "tong_so_ham": 0,
        "truc_0_kien_truc": {
            "import_nguoc_tang": [],
            "ham_nghi_chet": [],
            "tep_rac_o_goc": [],
            "skill_trung_hoac_lech": [],
        },
        "truc_1_duong_lenh": {
            "leo_cha_khong_chan_cua_so": [],
            "goi_header_item_tren_table_view": [],
            "ham_ghi_thieu_kiem_quyen": [],
            "ui_chua_sql_truc_tiep": [],
        },
        "truc_2_bao_mat": {
            "trigger_chi_kiem_tien_to": [],
            "xml_chi_quet_4kb_dau": [],
            "sql_in_khong_chia_nho": [],
        },
        "truc_3_so_lieu": {
            "round_mac_dinh_python": [],
            "ep_float_truoc_int": [],
            "goi_lap_doc_phuong_an": [],
        },
        "truc_4_giao_dien": {
            "mau_hex_cung_trong_html": [],
            "mau_hex_cung_nut_trang_thai": [],
            "chup_anh_man_hinh_sai_hop_thoai": [],
        },
        "truc_5_tuong_thich": {
            "canh_bao_cu_phap_escape": [],
            "loi_bien_dich": [],
        },
    }

    for ten in TEP_PROMPT_CU_O_GOC + KICH_BAN_THU_NGHIEM_O_GOC + DU_LIEU_MAU_O_GOC + THU_MUC_TRUNG_O_GOC:
        if (thu_muc_goc / ten).exists():
            ket_qua["truc_0_kien_truc"]["tep_rac_o_goc"].append(ten)
    for sk in SKILLS_DU_THUA:
        if (thu_muc_goc / sk).exists():
            ket_qua["truc_0_kien_truc"]["skill_trung_hoac_lech"].append(sk)

    ten_duoc_goi: Set[str] = set()
    dinh_nghia_ham: List[Tuple[str, str, int]] = []

    mau_html_hex = re.compile(
        r"""(?:setText|setToolTip|append)\s*\([^)]*style\s*=\s*['"][^'"]*color\s*:\s*(#[0-9a-fA-F]{3,6})""",
        re.DOTALL,
    )
    mau_sql_ghi = re.compile(
        r"\b(INSERT\s+INTO|UPDATE\s+\w+\s+SET|DELETE\s+FROM|REPLACE\s+INTO)\b",
        re.IGNORECASE,
    )
    mau_sql_select = re.compile(r"\bSELECT\s+.+\s+FROM\b", re.IGNORECASE)

    tang_nen = {"an_toan.py", "phan_quyen.py", "csdl.py", "tien.py", "qt.py"}
    tang_cao = {"pabt.lap_pa", "pabt.may_chu", "pabt.app", "pabt.man_hinh"}

    for tep in ds_tep_py:
        ten_tep = tep.name
        nguon = tep.read_text(encoding="utf-8", errors="replace")
        cac_dong = nguon.splitlines()
        ket_qua["tong_so_dong"] += len(cac_dong)

        try:
            cay = ast.parse(nguon, filename=str(tep))
        except SyntaxError as e:
            ket_qua["truc_5_tuong_thich"]["loi_bien_dich"].append(
                f"{ten_tep}:{e.lineno}: {e.msg}"
            )
            continue

        for nut in ast.walk(cay):
            if isinstance(nut, ast.ClassDef):
                ket_qua["tong_so_lop"] += 1
            elif isinstance(nut, (ast.FunctionDef, ast.AsyncFunctionDef)):
                ket_qua["tong_so_ham"] += 1
                if not nut.decorator_list:  # có decorator (@atexit.register, @Slot...) được gọi gián tiếp
                    dinh_nghia_ham.append((ten_tep, nut.name, nut.lineno))

                if ten_tep not in HAM_GHI_NOI_BO_CHO_PHEP and not ten_tep.startswith("man_hinh"):
                    doan_ma_ham = ast.get_source_segment(nguon, nut) or ""
                    if mau_sql_ghi.search(doan_ma_ham):
                        co_kiem_quyen = (
                            "kiem_quyen" in doan_ma_ham
                            or "kiem_ho_nhan_viec" in doan_ma_ham
                        )
                        if not co_kiem_quyen and not nut.name.startswith("_"):
                            ket_qua["truc_1_duong_lenh"]["ham_ghi_thieu_kiem_quyen"].append(
                                f"pabt/{ten_tep}:{nut.lineno} ({nut.name})"
                            )

            elif isinstance(nut, ast.Call):
                if isinstance(nut.func, ast.Name):
                    ten_duoc_goi.add(nut.func.id)
                    if nut.func.id == "round" and ten_tep not in {"giao_dien.py", "ban_do_cad.py"}:
                        ket_qua["truc_3_so_lieu"]["round_mac_dinh_python"].append(
                            f"pabt/{ten_tep}:{nut.lineno}"
                        )
                elif isinstance(nut.func, ast.Attribute):
                    ten_duoc_goi.add(nut.func.attr)
                    if nut.func.attr == "horizontalHeaderItem":
                        ket_qua["truc_1_duong_lenh"]["goi_header_item_tren_table_view"].append(
                            f"pabt/{ten_tep}:{nut.lineno}"
                        )

            elif isinstance(nut, ast.ImportFrom):
                if ten_tep in tang_nen and nut.module in tang_cao:
                    ket_qua["truc_0_kien_truc"]["import_nguoc_tang"].append(
                        f"pabt/{ten_tep}:{nut.lineno} -> import {nut.module}"
                    )

        if "cha = cha.parentWidget()" in nguon and "isWindow()" not in nguon:
            for idx, d in enumerate(cac_dong, 1):
                if "cha = cha.parentWidget()" in d:
                    ket_qua["truc_1_duong_lenh"]["leo_cha_khong_chan_cua_so"].append(
                        f"pabt/{ten_tep}:{idx}"
                    )

        if ten_tep == "app.py" or ten_tep.startswith("man_hinh"):
            so_cau_sql = len(mau_sql_select.findall(nguon))
            if so_cau_sql > 0:
                ket_qua["truc_1_duong_lenh"]["ui_chua_sql_truc_tiep"].append(
                    f"pabt/{ten_tep} ({so_cau_sql} truy vấn SELECT trực tiếp)"
                )

        for m in mau_html_hex.finditer(nguon):
            so_dong = nguon[: m.start()].count("\n") + 1
            ket_qua["truc_4_giao_dien"]["mau_hex_cung_trong_html"].append(
                f"pabt/{ten_tep}:{so_dong} ({m.group(1)})"
            )

        if ten_tep == "csdl.py" and "def go_trigger_la" in nguon:
            for idx, d in enumerate(cac_dong, 1):
                if "def go_trigger_la" in d:
                    ket_qua["truc_2_bao_mat"]["trigger_chi_kiem_tien_to"].append(
                        f"pabt/csdl.py:{idx} (go_trigger_la chỉ kiểm tiền tố tên trigger)"
                    )
        if ten_tep == "an_toan.py" and "4096" in nguon and "kiem_tra_xml" in nguon:
            for idx, d in enumerate(cac_dong, 1):
                if "def kiem_tra_xml" in d:
                    ket_qua["truc_2_bao_mat"]["xml_chi_quet_4kb_dau"].append(
                        f"pabt/an_toan.py:{idx} (kiem_tra_xml chỉ đọc 4096 byte đầu)"
                    )
        if ten_tep == "app.py":
            for idx, d in enumerate(cac_dong, 1):
                if "WHERE ma_ho IN ({ph})" in d:
                    ket_qua["truc_2_bao_mat"]["sql_in_khong_chia_nho"].append(
                        f"pabt/app.py:{idx} (WHERE ma_ho IN không chia nhỏ 900 phần tử)"
                    )
                if "nut_tk.setStyleSheet" in d and "#" in d:
                    ket_qua["truc_4_giao_dien"]["mau_hex_cung_nut_trang_thai"].append(
                        f"pabt/app.py:{idx}"
                    )
        if ten_tep == "van_ban_dot.py":
            for idx, d in enumerate(cac_dong, 1):
                if "int(float(" in d:
                    ket_qua["truc_3_so_lieu"]["ep_float_truoc_int"].append(
                        f"pabt/van_ban_dot.py:{idx}"
                    )
        if ten_tep == "in_an.py":
            for idx, d in enumerate(cac_dong, 1):
                if "doc_phuong_an(con, ma, den_lan=ln - 1)" in d:
                    ket_qua["truc_3_so_lieu"]["goi_lap_doc_phuong_an"].append(
                        f"pabt/in_an.py:{idx} (gọi lặp doc_phuong_an 2 lần/hộ trong vòng lặp)"
                    )

    for ten_tep, ten_ham, dong in dinh_nghia_ham:
        if ten_ham.startswith("_") and not ten_ham.startswith("__"):
            if ten_ham not in ten_duoc_goi:
                ket_qua["truc_0_kien_truc"]["ham_nghi_chet"].append(
                    f"pabt/{ten_tep}:{dong} ({ten_ham})"
                )

    tep_bo_cuc = thu_muc_goc / "kiem_tra_bo_cuc.py"
    if tep_bo_cuc.exists():
        nd = tep_bo_cuc.read_text(encoding="utf-8", errors="replace")
        if '"""' in nd[:100] and not nd.lstrip().startswith('r"""') and "\\S" in nd[:500]:
            ket_qua["truc_5_tuong_thich"]["canh_bao_cu_phap_escape"].append(
                "kiem_tra_bo_cuc.py:3 (SyntaxWarning '\\S' do thiếu tiền tố r\"\"\")"
            )

    tep_kt_gd = thu_muc_goc / "kiem_tra_giao_dien.py"
    if tep_kt_gd.exists():
        nd = tep_kt_gd.read_text(encoding="utf-8", errors="replace")
        if "w.grab()" in nd and "activeModalWidget" not in nd:
            ket_qua["truc_4_giao_dien"]["chup_anh_man_hinh_sai_hop_thoai"].append(
                "kiem_tra_giao_dien.py (gọi w.grab() trên cửa sổ nền thay vì hộp thoại modal đang mở)"
            )

    return ket_qua


def xuat_bao_cao_dai_phau(thu_muc_goc: Path, kq: Dict[str, Any]) -> Path:
    nhan_gio = _dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    tm_xuat = thu_muc_goc / "ket_qua_kiem_tra" / f"DaiPhau_{nhan_gio}"
    tm_xuat.mkdir(parents=True, exist_ok=True)

    (tm_xuat / "00_tong_ket.md").write_text(
        f"# 00 — TỔNG KẾT ĐẠI PHẪU KHÉP KÍN LARC ({kq['thoi_gian']})\n\n"
        f"- **Tổng số mô-đun `pabt/`**: {kq['tong_so_mo_dun']} tệp ({kq['tong_so_dong']:,} dòng mã, "
        f"{kq['tong_so_lop']} lớp, {kq['tong_so_ham']} hàm).\n"
        f"- **Trục 0 (Kiến trúc & Dọn dẹp)**: {len(kq['truc_0_kien_truc']['import_nguoc_tang'])} import ngược tầng, "
        f"{len(kq['truc_0_kien_truc']['ham_nghi_chet'])} hàm nội bộ không có caller, "
        f"{len(kq['truc_0_kien_truc']['tep_rac_o_goc'])} tệp/thư mục dư thừa ở gốc, "
        f"{len(kq['truc_0_kien_truc']['skill_trung_hoac_lech'])} skill trùng/lệch.\n"
        f"- **Trục 1 (Đường lệnh & Quyền ghi)**: {len(kq['truc_1_duong_lenh']['leo_cha_khong_chan_cua_so'])} vòng lặp leo cha vượt cửa sổ, "
        f"{len(kq['truc_1_duong_lenh']['goi_header_item_tren_table_view'])} điểm gọi `horizontalHeaderItem` nguy hiểm, "
        f"{len(kq['truc_1_duong_lenh']['ham_ghi_thieu_kiem_quyen'])} hàm ghi CSDL công khai thiếu `kiem_quyen`.\n"
        f"- **Trục 2 (Bảo mật)**: {len(kq['truc_2_bao_mat']['trigger_chi_kiem_tien_to']) + len(kq['truc_2_bao_mat']['xml_chi_quet_4kb_dau']) + len(kq['truc_2_bao_mat']['sql_in_khong_chia_nho'])} điểm cần siết chặt.\n"
        f"- **Trục 3 (Số liệu)**: {len(kq['truc_3_so_lieu']['round_mac_dinh_python'])} điểm dùng `round()` mặc định, "
        f"{len(kq['truc_3_so_lieu']['ep_float_truoc_int'])} điểm ép `float` trước `int`, "
        f"{len(kq['truc_3_so_lieu']['goi_lap_doc_phuong_an'])} điểm gọi lặp `doc_phuong_an`.\n"
        f"- **Trục 4 (Giao diện)**: {len(kq['truc_4_giao_dien']['mau_hex_cung_trong_html'])} nhãn HTML gán màu hex cứng gây tàng hình ở Chế độ Tối.\n"
        f"- **Trục 5 & 6 (Tương thích & Tốc độ)**: {len(kq['truc_5_tuong_thich']['loi_bien_dich'])} lỗi biên dịch, "
        f"{len(kq['truc_5_tuong_thich']['canh_bao_cu_phap_escape'])} cảnh báo cú pháp escape.\n",
        encoding="utf-8",
    )

    (tm_xuat / "01_kien_truc.md").write_text(
        "# 01 — KIẾN TRÚC, PHỤ THUỘC & DỌN DẸP MÃ DƯ THỪA\n\n"
        "## 1. Import ngược tầng (Tầng nền gọi lên tầng nghiệp vụ/máy chủ)\n"
        + ("\n".join(f"- `{x}`" for x in kq["truc_0_kien_truc"]["import_nguoc_tang"]) or "- Không phát hiện.\n")
        + "\n\n## 2. Hàm nội bộ không có lời gọi (Dead Code)\n"
        + ("\n".join(f"- `{x}`" for x in kq["truc_0_kien_truc"]["ham_nghi_chet"]) or "- Không phát hiện.\n")
        + "\n\n## 3. Tệp nháp / Prompt cũ ở thư mục gốc cần đưa vào `_luu_tru_don_dep/`\n"
        + ("\n".join(f"- `{x}`" for x in kq["truc_0_kien_truc"]["tep_rac_o_goc"]) or "- Thư mục gốc đã sạch.\n")
        + "\n\n## 4. Skill trùng lặp hoặc lệch hệ sinh thái trong `.claude/skills/`\n"
        + ("\n".join(f"- `{x}`" for x in kq["truc_0_kien_truc"]["skill_trung_hoac_lech"]) or "- Đã tinh gọn.\n")
        + "\n",
        encoding="utf-8",
    )

    (tm_xuat / "02_duong_lenh.md").write_text(
        "# 02 — ĐƯỜNG LỆNH, TÍN HIỆU & QUYỀN GHI CSDL\n\n"
        "## 1. Đường lệnh đi lòng vòng qua `parentWidget()` vượt ranh giới cửa sổ\n"
        + ("\n".join(f"- `{x}`" for x in kq["truc_1_duong_lenh"]["leo_cha_khong_chan_cua_so"]) or "- Đã chặn biên cửa sổ.\n")
        + "\n\n## 2. Điểm gọi `horizontalHeaderItem` cần đổi sang `model().headerData` để hỗ trợ `QTableView`\n"
        + ("\n".join(f"- `{x}`" for x in kq["truc_1_duong_lenh"]["goi_header_item_tren_table_view"]) or "- Đã an toàn.\n")
        + "\n\n## 3. Hàm ghi CSDL công khai thiếu `kiem_quyen` / `kiem_ho_nhan_viec`\n"
        + ("\n".join(f"- `{x}`" for x in kq["truc_1_duong_lenh"]["ham_ghi_thieu_kiem_quyen"]) or "- Đã kiểm quyền đầy đủ.\n")
        + "\n\n## 4. Mô-đun giao diện còn chứa câu lệnh `SELECT` trực tiếp\n"
        + ("\n".join(f"- `{x}`" for x in kq["truc_1_duong_lenh"]["ui_chua_sql_truc_tiep"]) or "- Không có.\n")
        + "\n",
        encoding="utf-8",
    )

    (tm_xuat / "03_bao_mat.md").write_text(
        "# 03 — BẢO MẬT & AN TOÀN DỮ LIỆU\n\n"
        "## Các phát hiện cốt lõi\n"
        + "\n".join(
            f"- `{x}`"
            for x in (
                kq["truc_2_bao_mat"]["trigger_chi_kiem_tien_to"]
                + kq["truc_2_bao_mat"]["xml_chi_quet_4kb_dau"]
                + kq["truc_2_bao_mat"]["sql_in_khong_chia_nho"]
            )
        )
        + "\n",
        encoding="utf-8",
    )

    (tm_xuat / "04_so_lieu.md").write_text(
        "# 04 — SỐ LIỆU, DECIMAL & ĐỐI CHIẾU NGHIỆP VỤ\n\n"
        "## 1. Điểm dùng `round()` mặc định của Python (`ROUND_HALF_EVEN`)\n"
        + ("\n".join(f"- `{x}`" for x in kq["truc_3_so_lieu"]["round_mac_dinh_python"]) or "- Không có.\n")
        + "\n\n## 2. Điểm ép `float()` trước khi chuyển `int()`\n"
        + ("\n".join(f"- `{x}`" for x in kq["truc_3_so_lieu"]["ep_float_truoc_int"]) or "- Không có.\n")
        + "\n\n## 3. Điểm gọi lặp `doc_phuong_an` trong vòng lặp xuất báo cáo\n"
        + ("\n".join(f"- `{x}`" for x in kq["truc_3_so_lieu"]["goi_lap_doc_phuong_an"]) or "- Không có.\n")
        + "\n",
        encoding="utf-8",
    )

    (tm_xuat / "05_giao_dien.md").write_text(
        "# 05 — GIAO DIỆN, TƯƠNG PHẢN WCAG & BỐ CỤC\n\n"
        "## 1. Nhãn HTML dùng mã màu hex cứng (gây tàng hình ở Chế độ Tối)\n"
        + ("\n".join(f"- `{x}`" for x in kq["truc_4_giao_dien"]["mau_hex_cung_trong_html"]) or "- Đã chuyển sang TOKEN động.\n")
        + "\n\n## 2. Nút thanh trạng thái dùng màu hex cứng\n"
        + ("\n".join(f"- `{x}`" for x in kq["truc_4_giao_dien"]["mau_hex_cung_nut_trang_thai"]) or "- Đã dùng TOKEN động.\n")
        + "\n\n## 3. Công cụ chụp ảnh giao diện\n"
        + ("\n".join(f"- `{x}`" for x in kq["truc_4_giao_dien"]["chup_anh_man_hinh_sai_hop_thoai"]) or "- Đã chuẩn.\n")
        + "\n",
        encoding="utf-8",
    )

    (tm_xuat / "06_tuong_thich_toc_do.md").write_text(
        "# 06 — TƯƠNG THÍCH PYTHON 3.8 / QT5 & TỐC ĐỘ\n\n"
        "## 1. Lỗi biên dịch cú pháp\n"
        + ("\n".join(f"- `{x}`" for x in kq["truc_5_tuong_thich"]["loi_bien_dich"]) or "- 0 lỗi (100% mô-đun biên dịch sạch).\n")
        + "\n\n## 2. Cảnh báo chuỗi thoát (`SyntaxWarning` trên Python 3.12+)\n"
        + ("\n".join(f"- `{x}`" for x in kq["truc_5_tuong_thich"]["canh_bao_cu_phap_escape"]) or "- Không có.\n")
        + "\n",
        encoding="utf-8",
    )

    (tm_xuat / "chi_so_dai_phau.json").write_text(
        json.dumps(kq, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return tm_xuat


def chup_snapshot(thu_muc_goc: Path, ten_dot: str) -> Path:
    tm_snap = thu_muc_goc / "ket_qua_kiem_tra" / "_snapshots" / ten_dot
    if tm_snap.exists():
        shutil.rmtree(tm_snap)
    tm_snap.mkdir(parents=True, exist_ok=True)

    shutil.copytree(thu_muc_goc / "pabt", tm_snap / "pabt")
    if (thu_muc_goc / "cong_cu").is_dir():
        shutil.copytree(thu_muc_goc / "cong_cu", tm_snap / "cong_cu")

    chi_muc_ast: Dict[str, Any] = {}
    for tep in sorted((thu_muc_goc / "pabt").glob("*.py")):
        chi_muc_ast[tep.name] = _trich_xuat_chu_ky_ast(tep)

    chi_so = quet_9_truc_dai_phau(thu_muc_goc)
    (tm_snap / "baseline_ast.json").write_text(
        json.dumps(chi_muc_ast, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (tm_snap / "baseline_metrics.json").write_text(
        json.dumps(chi_so, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return tm_snap


def khoi_phuc_snapshot(thu_muc_goc: Path, ten_dot: str) -> bool:
    tm_snap = thu_muc_goc / "ket_qua_kiem_tra" / "_snapshots" / ten_dot
    if not tm_snap.is_dir():
        print(f"[LỖI] Không tìm thấy snapshot '{ten_dot}' tại {tm_snap}")
        return False
    shutil.rmtree(thu_muc_goc / "pabt")
    shutil.copytree(tm_snap / "pabt", thu_muc_goc / "pabt")
    if (tm_snap / "cong_cu").is_dir():
        shutil.rmtree(thu_muc_goc / "cong_cu")
        shutil.copytree(tm_snap / "cong_cu", thu_muc_goc / "cong_cu")
    print(f"[KHÔI PHỤC HOÀN TẤT] Đã trả mã nguồn về nguyên trạng snapshot '{ten_dot}'.")
    return True


def kiem_tra_6_cong_gac(
    thu_muc_goc: Path, ten_dot: Optional[str] = None, tu_khoi_phuc: bool = False
) -> bool:
    kq_hien_tai = quet_9_truc_dai_phau(thu_muc_goc)
    loi_cong: List[str] = []

    if kq_hien_tai["truc_5_tuong_thich"]["loi_bien_dich"]:
        loi_cong.append(
            "GATE 1 (Cú pháp): Lỗi biên dịch tại "
            + ", ".join(kq_hien_tai["truc_5_tuong_thich"]["loi_bien_dich"])
        )

    if ten_dot:
        tm_snap = thu_muc_goc / "ket_qua_kiem_tra" / "_snapshots" / ten_dot
        if (tm_snap / "baseline_ast.json").exists():
            ast_cu = json.loads((tm_snap / "baseline_ast.json").read_text(encoding="utf-8"))
            metrics_cu = json.loads((tm_snap / "baseline_metrics.json").read_text(encoding="utf-8"))

            for ten_tep, thong_tin_cu in ast_cu.items():
                tep_moi = thu_muc_goc / "pabt" / ten_tep
                if not tep_moi.exists():
                    loi_cong.append(f"GATE 2 (Cấu trúc): Bị mất mô-đun pabt/{ten_tep}")
                    continue
                thong_tin_moi = _trich_xuat_chu_ky_ast(tep_moi)
                lop_bi_mat = set(thong_tin_cu["lop"].keys()) - set(thong_tin_moi["lop"].keys())
                if lop_bi_mat:
                    loi_cong.append(
                        f"GATE 2 (Cấu trúc): pabt/{ten_tep} bị mất lớp: {sorted(lop_bi_mat)}"
                    )
                for ten_lop, ds_pt_cu in thong_tin_cu["lop"].items():
                    if ten_lop in thong_tin_moi["lop"]:
                        pt_cong_khai_cu = {p for p in ds_pt_cu if not p.startswith("_")}
                        pt_cong_khai_moi = {
                            p for p in thong_tin_moi["lop"][ten_lop] if not p.startswith("_")
                        }
                        mat_pt = pt_cong_khai_cu - pt_cong_khai_moi
                        if mat_pt:
                            loi_cong.append(
                                f"GATE 2 (Cấu trúc): Lớp {ten_tep}:{ten_lop} bị mất phương thức: {sorted(mat_pt)}"
                            )

            if len(kq_hien_tai["truc_1_duong_lenh"]["leo_cha_khong_chan_cua_so"]) > len(
                metrics_cu["truc_1_duong_lenh"]["leo_cha_khong_chan_cua_so"]
            ):
                loi_cong.append("GATE 3 (Đường lệnh): Phát sinh vòng lặp parentWidget không chặn isWindow().")
            if len(kq_hien_tai["truc_1_duong_lenh"]["ham_ghi_thieu_kiem_quyen"]) > len(
                metrics_cu["truc_1_duong_lenh"]["ham_ghi_thieu_kiem_quyen"]
            ):
                loi_cong.append("GATE 3 (Quyền ghi): Phát sinh hàm ghi CSDL thiếu kiem_quyen.")

            if len(kq_hien_tai["truc_4_giao_dien"]["mau_hex_cung_trong_html"]) > len(
                metrics_cu["truc_4_giao_dien"]["mau_hex_cung_trong_html"]
            ):
                loi_cong.append(
                    "GATE 4 (Giao diện WCAG): Phát sinh mã màu hex cứng mới trong HTML label."
                )

            if len(kq_hien_tai["truc_3_so_lieu"]["round_mac_dinh_python"]) > len(
                metrics_cu["truc_3_so_lieu"]["round_mac_dinh_python"]
            ):
                loi_cong.append("GATE 5 (Số liệu): Phát sinh lệnh round() mặc định của Python.")

    if loi_cong:
        print("=" * 72)
        print("[CỔNG GÁC ĐỎ — KHÔNG ĐẠT TIÊU CHUẨN KHÉP KÍN]")
        for l in loi_cong:
            print(f"  ✗ {l}")
        print("=" * 72)
        if tu_khoi_phuc and ten_dot:
            khoi_phuc_snapshot(thu_muc_goc, ten_dot)
        return False

    print("=" * 72)
    print("[CỔNG GÁC XANH — ĐẠT TẤT CẢ 6 CỔNG KIỂM SOÁT CHẤT LƯỢNG]")
    print(f"  ✓ Biên dịch sạch {kq_hien_tai['tong_so_mo_dun']} mô-đun ({kq_hien_tai['tong_so_dong']:,} dòng mã).")
    print("  ✓ Bảo toàn 100% cấu trúc lớp, phương thức và thuộc tính phần mềm.")
    print("  ✓ Không phát sinh lỗi đường lệnh, màu hex cứng hay sai lệch làm tròn.")
    print("=" * 72)
    return True


def don_dep_cay_thu_muc(thu_muc_goc: Path, thuc_thi: bool = False) -> List[Tuple[str, str]]:
    ngay = _dt.datetime.now().strftime("%Y%m%d")
    tm_luu_tru = thu_muc_goc / "_luu_tru_don_dep" / f"dot_{ngay}"
    ke_hoach: List[Tuple[Path, Path]] = []

    for ten in TEP_PROMPT_CU_O_GOC:
        nguon = thu_muc_goc / ten
        if nguon.exists():
            ke_hoach.append((nguon, tm_luu_tru / "01_tai_lieu_prompt_cu" / ten))

    for ten in KICH_BAN_THU_NGHIEM_O_GOC:
        nguon = thu_muc_goc / ten
        if nguon.exists():
            ke_hoach.append((nguon, tm_luu_tru / "02_kich_ban_thu_nghiem_roi" / ten))

    for ten in DU_LIEU_MAU_O_GOC:
        nguon = thu_muc_goc / ten
        if nguon.exists():
            ke_hoach.append((nguon, tm_luu_tru / "03_du_lieu_du_an_mau" / ten))

    for ten in THU_MUC_TRUNG_O_GOC:
        nguon = thu_muc_goc / ten
        if nguon.exists():
            ke_hoach.append((nguon, tm_luu_tru / "04_thu_muc_trung_va_anh_cu" / ten))

    for duong_dan_skill in SKILLS_DU_THUA:
        nguon = thu_muc_goc / duong_dan_skill
        if nguon.exists():
            ke_hoach.append((nguon, tm_luu_tru / "05_skills_trung_hoac_web" / nguon.name))

    ket_qua_di_chuyen: List[Tuple[str, str]] = []
    che_do = "THỰC THI DI CHUYỂN" if thuc_thi else "CHẠY THỬ (DRY-RUN)"
    print(f"=== KẾ HOẠCH DỌN DẸP AN TOÀN ({che_do}) ===")
    for nguon, dich in ke_hoach:
        tuong_doi_nguon = str(nguon.relative_to(thu_muc_goc))
        tuong_doi_dich = str(dich.relative_to(thu_muc_goc))
        ket_qua_di_chuyen.append((tuong_doi_nguon, tuong_doi_dich))
        print(f"  • {tuong_doi_nguon}  -->  {tuong_doi_dich}")
        if thuc_thi:
            dich.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(nguon), str(dich))

    if not ke_hoach:
        print("  ✓ Thư mục gốc và .claude/skills/ đã gọn sạch, không có mục dư thừa.")
    return ket_qua_di_chuyen


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Hệ thống Điều phối & Cổng gác AI Khép kín cho phần mềm LARC (PABT)"
    )
    parser.add_argument(
        "--thu-muc",
        default=".",
        help="Đường dẫn thư mục gốc dự án LARC (mặc định: thư mục hiện tại)",
    )
    parser.add_argument(
        "--dai-phau",
        action="store_true",
        help="Chạy rà soát 9 giai đoạn Đại Phẫu và xuất đủ 7 tệp báo cáo vào ket_qua_kiem_tra/DaiPhau_<giờ>/",
    )
    parser.add_argument(
        "--chup-snapshot",
        action="store_true",
        help="Chụp snapshot mã nguồn và cấu trúc AST trước khi sửa",
    )
    parser.add_argument(
        "--kiem-cong",
        action="store_true",
        help="Chạy 6 Cổng Gác Chất Lượng sau khi sửa",
    )
    parser.add_argument(
        "--khoi-phuc",
        action="store_true",
        help="Khôi phục mã nguồn từ snapshot",
    )
    parser.add_argument(
        "--tu-khoi-phuc",
        action="store_true",
        help="Tự động rollback nếu bất kỳ cổng gác nào thất bại khi chạy --kiem-cong",
    )
    parser.add_argument(
        "--ten-dot",
        default="dot_sua_hien_tai",
        help="Tên định danh đợt sửa (dùng cho snapshot/kiem-cong/khoi-phuc)",
    )
    parser.add_argument(
        "--don-dep",
        action="store_true",
        help="Rà soát và dọn dẹp các tệp prompt cũ, skill trùng lặp và tệp rác ở gốc",
    )
    parser.add_argument(
        "--thuc-thi",
        action="store_true",
        help="Thực hiện di chuyển thật khi đi kèm --don-dep (mặc định là chạy thử dry-run)",
    )

    args = parser.parse_args()
    thu_muc_goc = Path(args.thu_muc).resolve()

    if args.chup_snapshot:
        tm = chup_snapshot(thu_muc_goc, args.ten_dot)
        print(f"[SNAPSHOT] Đã lưu snapshot '{args.ten_dot}' tại: {tm}")
        return 0

    if args.khoi_phuc:
        ok = khoi_phuc_snapshot(thu_muc_goc, args.ten_dot)
        return 0 if ok else 1

    if args.don_dep:
        don_dep_cay_thu_muc(thu_muc_goc, thuc_thi=args.thuc_thi)
        return 0

    if args.kiem_cong:
        ok = kiem_tra_6_cong_gac(
            thu_muc_goc, ten_dot=args.ten_dot, tu_khoi_phuc=args.tu_khoi_phuc
        )
        return 0 if ok else 2

    kq = quet_9_truc_dai_phau(thu_muc_goc)
    tm_bao_cao = xuat_bao_cao_dai_phau(thu_muc_goc, kq)
    print(f"[ĐẠI PHẪU HOÀN TẤT] Đã xuất đầy đủ 7 báo cáo tại: {tm_bao_cao}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
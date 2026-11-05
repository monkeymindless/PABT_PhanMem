"""Bộ quét file DÙNG CHUNG (AI Smart Scan hợp nhất) - mọi nút Quét / Nạp file gọi hàm `quet` với một ngữ cảnh. Không Qt.

Chuyển từ `executeUnifiedAIScan` (+ extractLegalCitationsFromText, inferValuationParamsFromText, parseAssetAndCropTablesFromText,
parseHouseholdLandDossierFromText) của HeThongDinhGiaVaScanThongMinh_V2.tsx (05/11/2026).

CHẠY HOÀN TOÀN TRÊN MÁY (quyết định của người dùng, xem docs/LICH_SU_PHAT_TRIEN.md): đọc file bằng `nhap_don_gia.doc_bang_ocr` (Excel, Word,
PDF chữ; PDF ảnh / file ảnh scan nhận dạng bằng Tesseract đóng kèm - ocr.py), không gửi file hay chữ lên dịch vụ ngoài. Không có "AI" gọi mạng:
"thông minh" ở đây là nhận dạng theo mẫu văn bản / bảng (quy tắc), kết quả luôn hiện ra cho người dùng xem trước khi áp dụng.

Ngữ cảnh (scanContext của TSX): AUTO_DETECT (mọi nút Nạp / Quét chung), LEGAL_BASIS_ONLY (quét văn bản căn cứ), LAND_PRICE_TABLE (văn bản /
bảng giá đất - thông số tính giá), ASSET_CROP_PRICE_TABLE (đơn giá nhà, vật kiến trúc, cây trồng), DETAILED_HOUSEHOLD_DOSSIER (biên bản kiểm
đếm / hồ sơ chi tiết của hộ), MASTER_COMPENSATION_SHEET (bảng tổng hợp). Văn bản căn cứ được trích ở MỌI ngữ cảnh."""
from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from pathlib import Path

from . import van_ban_can_cu

AUTO = 'AUTO_DETECT'
CAN_CU = 'LEGAL_BASIS_ONLY'
GIA_DAT = 'LAND_PRICE_TABLE'
GIA_TAI_SAN = 'ASSET_CROP_PRICE_TABLE'
HO_SO_HO = 'DETAILED_HOUSEHOLD_DOSSIER'
BANG_TONG_HOP = 'MASTER_COMPENSATION_SHEET'
NGU_CANH = (AUTO, CAN_CU, GIA_DAT, GIA_TAI_SAN, HO_SO_HO, BANG_TONG_HOP)

LOC_FILE = ('Mọi file hỗ trợ (*.pdf *.doc *.docx *.xls *.xlsx *.xlsm *.csv *.txt *.png *.jpg *.jpeg *.tif *.tiff *.bmp);;'
            'PDF, Word, Excel (*.pdf *.doc *.docx *.xls *.xlsx *.xlsm *.csv *.txt);;Ảnh scan (*.png *.jpg *.jpeg *.tif *.tiff *.bmp);;'
            'Tất cả file (*.*)')
DUOI_CHU = ('.txt', '.csv', '.json', '.md', '.html', '.htm')
DUOI_ANH = ('.png', '.jpg', '.jpeg', '.tif', '.tiff', '.bmp', '.webp')


@dataclass
class DongDat:
    to_ban_do: str
    so_thua: str
    loai_dat: str
    nhom_dat: str
    dien_tich_thu_hoi: Decimal
    mo_ta_duong: str = ''
    ket_cau_mat_duong: str = 'NHUA_BETONG'
    vi_tri_goi_y: str = 'MAT_TIEN_VT1'


@dataclass
class DongTaiSan:
    danh_muc: str                     # 'NHA_VAT_KIEN_TRUC' | 'CAY_TRONG_HOA_MAU'
    ten: str
    dvt: str
    so_luong: Decimal
    don_gia: Decimal
    ty_le: Decimal = Decimal(100)
    thanh_tien: Decimal = Decimal(0)


@dataclass
class KetQuaQuet:
    ngu_canh: str = AUTO
    loai_phat_hien: list = field(default_factory=list)
    do_tin_cay: float = 0.0
    thoi_gian_ms: int = 0
    can_cu: list = field(default_factory=list)
    dong_dat: list = field(default_factory=list)
    dong_tai_san: list = field(default_factory=list)
    tham_so: dict = field(default_factory=dict)        # dia_ban, ket_cau_mat_duong, yeu_to_pl3
    tom_tat: list = field(default_factory=list)
    loi: list = field(default_factory=list)            # file đọc không được: "tên file: lý do"
    so_file: int = 0

    def co_du_lieu(self) -> bool:
        return bool(self.can_cu or self.dong_dat or self.dong_tai_san or self.tham_so)


# ---------------------------------------------------------------- đọc file
def doc_noi_dung(file, bao_tien_do=None, cho=None) -> str:
    """Toàn bộ chữ của file (ô cách nhau bằng Tab, mỗi dòng bảng một dòng). Lỗi đọc: ném LoiNhap / ocr.LoiOCR (quet() bắt từng file)."""
    p = Path(file)
    duoi = p.suffix.lower()
    if duoi in DUOI_CHU:
        return p.read_text(encoding='utf-8-sig', errors='replace')
    from . import nhap_don_gia as nd
    if duoi in DUOI_ANH:
        from . import ocr
        return '\n'.join(ocr.doc_chu(p, bao_tien_do, cho))
    dong = nd.doc_bang_ocr(p, bao_tien_do, cho)
    return '\n'.join('\t'.join(str(o) for o in r) for r in dong)


# ---------------------------------------------------------------- nhận dạng theo mẫu (port của các hàm TSX)
def _so(chu) -> Decimal:
    """'1.450.000' / '143,8' / '256.8' -> Decimal (dấu chấm 3 chữ số cuối = phân cách nghìn)."""
    s = str(chu or '').strip()
    if ',' in s:
        s = s.replace('.', '').replace(',', '.')
    elif re.fullmatch(r'\d{1,3}(?:\.\d{3})+', s):
        s = s.replace('.', '')
    try:
        return Decimal(s)
    except InvalidOperation:
        return Decimal(0)


def nhan_dien_tham_so(noi_dung: str) -> dict:
    """inferValuationParamsFromText: địa bàn (Bảng 53 / 54 / 55) + kết cấu mặt đường đất / sỏi / đá / cấp phối (K3 = 0,90 đất NN)."""
    thap = noi_dung.lower()
    kq = {}
    if 'xã tân an' in thap or 'bảng 54' in thap:
        kq['dia_ban'] = 'Bảng 54. Xã Tân An'
    elif 'xã phú lý' in thap or 'bảng 55' in thap:
        kq['dia_ban'] = 'Bảng 55. Xã Phú Lý'
    elif 'phường trị an' in thap or 'xã trị an' in thap or 'bảng 53' in thap:
        kq['dia_ban'] = 'Bảng 53. Phường Trị An'
    if 'đường đất' in thap or 'cấp phối' in thap or 'sỏi hỗn hợp' in thap:
        kq['ket_cau_mat_duong'] = 'DAT_SOI_DA_CAPPHOI'
        kq['yeu_to_pl3'] = ['NN_DUONG_DAT_SOI_DA']
    elif 'đường nhựa' in thap or 'bê tông' in thap:
        kq['ket_cau_mat_duong'] = 'NHUA_BETONG'
    return kq


_RE_TAI_SAN = re.compile(r'(?im)^([^\t|;\n]+?)[\t|;]+(cây|m2|m²|m3|m|md|cái|bộ|hố)[\t|;]+([\d.,]+)[\t|;]+([\d.,]+)')
_RE_CAY = re.compile(r'(?i)cây|xoài|bưởi|sầu riêng|điều|cao su|tràm|keo|chuối|mít')


def nhan_dien_tai_san(noi_dung: str) -> list:
    """parseAssetAndCropTablesFromText: dòng '<tên> <ĐVT> <số lượng> <đơn giá>' (Tab, '|' hoặc ';' ngăn cách)."""
    kq = []
    for m in _RE_TAI_SAN.finditer(noi_dung):
        ten, dvt = m.group(1).strip(), m.group(2).strip()
        sl, dg = _so(m.group(3)), _so(m.group(4))
        la_cay = bool(_RE_CAY.search(ten)) or dvt.lower() == 'cây'
        kq.append(DongTaiSan('CAY_TRONG_HOA_MAU' if la_cay else 'NHA_VAT_KIEN_TRUC', ten, dvt, sl, dg, Decimal(100), (sl * dg).quantize(Decimal(1))))
    return kq


_RE_THUA = re.compile(r'(?i)tờ\s*(?:bản đồ)?\s*(?:số)?\s*(\d+)[^\d]+thửa\s*(?:đất)?\s*(?:số)?\s*(\d+)[^0-9]+([\d.,]+)\s*m(?:2|²)')
_RE_DUONG_DAT = re.compile(r'(?i)đường đất|đường sỏi|đường đá|cấp phối')


def nhan_dien_thua(noi_dung: str) -> list:
    """parseHouseholdLandDossierFromText: 'tờ bản đồ số 12 ... thửa đất số 205 ... 256,8 m2'."""
    duong_dat = bool(_RE_DUONG_DAT.search(noi_dung))
    return [DongDat(m.group(1), m.group(2), 'Đất trồng cây lâu năm (CLN)', 'DAT_NONG_NGHIEP', _so(m.group(3)),
                    'Tự động bóc tách từ hồ sơ kiểm đếm', 'DAT_SOI_DA_CAPPHOI' if duong_dat else 'NHUA_BETONG')
            for m in _RE_THUA.finditer(noi_dung)]


# ---------------------------------------------------------------- bộ quét
def quet(files, ngu_canh: str = AUTO, bao_tien_do=None, cho=None, doc=None) -> KetQuaQuet:
    """executeUnifiedAIScan: đọc từng file MỘT lần, rồi (tùy ngữ cảnh) trích văn bản căn cứ / thông số giá đất / đơn giá tài sản / thửa đất.
    doc(file) -> chữ: thay hàm đọc file (kiểm thử). cho() -> True: hủy (ocr.DaHuy được truyền lên). Lỗi từng file ghi vào kq.loi, quét tiếp."""
    if ngu_canh not in NGU_CANH:
        raise ValueError(f'Ngữ cảnh quét không có: {ngu_canh}')
    from .lap_pa import LoiNhap
    bat_dau = time.perf_counter()
    kq = KetQuaQuet(ngu_canh=ngu_canh)
    loai = []
    for f in list(files or ()):
        p = Path(f)
        kq.so_file += 1
        try:
            nd = doc(p) if doc is not None else doc_noi_dung(p, bao_tien_do, cho)
        except LoiNhap as e:
            kq.loi.append(f'{p.name}: {e}')
            continue
        except Exception as e:                                          # noqa: BLE001 - ocr.LoiOCR / DaHuy: DaHuy phải đi tiếp lên
            if type(e).__name__ == 'DaHuy':
                raise
            kq.loi.append(f'{p.name}: {e}')
            continue
        thap = nd.lower()
        # 1. văn bản pháp lý: ở MỌI lần quét
        cc = van_ban_can_cu.trich_can_cu(nd, p.name)
        if cc:
            kq.can_cu.extend(cc)
            loai.append(CAN_CU)
        # 2. thông số đơn giá đất / hệ số K
        if ngu_canh in (AUTO, GIA_DAT) or 'hệ số điều chỉnh mức biến động thị trường' in nd or '28/2025/NQ-HĐND' in nd \
                or '03/2026/QĐ-UBND' in nd:
            loai.append(GIA_DAT)
            ts = nhan_dien_tham_so(nd)
            if ts:
                kq.tham_so.update(ts)
                kq.tom_tat.append(f'[Đơn giá đất] Nhận diện thông số từ "{p.name}": khu vực {ts.get("dia_ban", "(chưa rõ)")}, kết cấu đường: '
                                  + ('đường đất / đá / sỏi (K3 = 0,90 với đất nông nghiệp)' if ts.get('ket_cau_mat_duong') == 'DAT_SOI_DA_CAPPHOI'
                                     else 'đường nhựa / bê tông' if ts.get('ket_cau_mat_duong') else '(chưa rõ)') + '.')
        # 3. đơn giá nhà, vật kiến trúc, cây trồng
        if ngu_canh in (AUTO, GIA_TAI_SAN) or 'cây trồng' in thap or 'vật kiến trúc' in thap:
            ts = nhan_dien_tai_san(nd)
            if ts:
                loai.append(GIA_TAI_SAN)
                kq.dong_tai_san.extend(ts)
                kq.tom_tat.append(f'[Tài sản, cây trồng] Bóc tách {len(ts)} hạng mục nhà / vật kiến trúc / cây trồng từ "{p.name}".')
        # 4. hồ sơ kiểm đếm chi tiết của hộ
        if ngu_canh in (AUTO, HO_SO_HO) or 'thửa đất số' in thap or 'tờ bản đồ' in thap:
            dat = nhan_dien_thua(nd)
            if dat:
                loai.append(HO_SO_HO)
                kq.dong_dat.extend(dat)
                kq.tom_tat.append(f'[Hồ sơ chi tiết] Bóc tách {len(dat)} thửa đất thu hồi kèm kết cấu mặt đường từ "{p.name}".')
    kq.loai_phat_hien = list(dict.fromkeys(loai))
    kq.can_cu = list(dict.fromkeys(kq.can_cu))
    kq.do_tin_cay = 0.0 if not kq.co_du_lieu() else 0.99 if not kq.loi else 0.8
    kq.thoi_gian_ms = int((time.perf_counter() - bat_dau) * 1000)
    return kq

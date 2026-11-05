"""Bộ quét file DÙNG CHUNG (AI Smart Scan hợp nhất) - mọi nút Quét / Nạp file gọi hàm `quet` với một ngữ cảnh. Không Qt.

Chuyển từ `executeUnifiedAIScan` (+ extractLegalCitationsFromText, inferValuationParamsFromText, parseAssetAndCropTablesFromText,
parseHouseholdLandDossierFromText) của HeThongDinhGiaVaScanThongMinh_V2.tsx (05/11/2026).

CHẠY HOÀN TOÀN TRÊN MÁY (quyết định của người dùng, xem docs/LICH_SU_PHAT_TRIEN.md): đọc file bằng `nhap_don_gia.doc_bang_ocr` (Excel, Word,
PDF chữ; PDF ảnh / file ảnh scan nhận dạng bằng Tesseract đóng kèm - ocr.py), không gửi file hay chữ lên dịch vụ ngoài. Không có "AI" gọi mạng:
"thông minh" ở đây là nhận dạng theo mẫu văn bản / bảng (quy tắc), kết quả luôn hiện ra cho người dùng xem trước khi áp dụng.

BỘ ĐỊNH TUYẾN (1.0.62): `nhan_loai` nhận loại TỪNG file -> màn hình chuyên trách đã có (DICH): Excel PABT / danh sách hộ -> nhập dự án, Excel mỗi
sheet một hộ -> nhập phương án chi tiết, Phụ lục hệ số K, bảng giá đất, bảng đơn giá nhà / cây -> Bộ đơn giá, biên bản kiểm đếm / sổ đỏ -> phương
án của hộ. Không viết bộ đọc thứ hai: thửa bóc bằng ocr_ho_so.boc_tach, tài sản đưa qua hộp "Dán danh sách tài sản" (khớp danh mục đơn giá).
Nút có đầu ra riêng (đọc quyết định của một hộ, kết quả niêm yết theo đợt, đính file văn bản) giữ đường đọc riêng vì cần kết quả riêng.

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

# loại file -> màn hình xử lý tiếp
D_DU_AN, D_CHI_TIET, D_HE_SO_K, D_BANG_GIA, D_DON_GIA, D_HO_SO, D_CAN_CU, D_KHAC = (
    'du_an_excel', 'pa_chi_tiet', 'he_so_k', 'bang_gia_dat', 'don_gia', 'ho_so_ho', 'can_cu', 'khac')
DICH = (
    (D_DU_AN, 'File dự án / danh sách hộ, thửa', 'Nhập vào dự án'),
    (D_CHI_TIET, 'Phương án chi tiết (mỗi sheet một hộ)', 'Nhập phương án chi tiết'),
    (D_HE_SO_K, 'Phụ lục hệ số K', 'Mở thẻ Hệ số K'),
    (D_BANG_GIA, 'Bảng giá đất', 'Mở thẻ Cập nhật bảng giá đất'),
    (D_DON_GIA, 'Bảng đơn giá nhà, cây, chính sách', 'Mở Bộ đơn giá'),
    (D_HO_SO, 'Biên bản kiểm đếm / giấy tờ của hộ', 'Đưa vào phương án của hộ'),
    (D_CAN_CU, 'Văn bản căn cứ', 'Ghi vào mục Văn bản căn cứ'),
    (D_KHAC, 'Chưa nhận ra', 'Không xử lý'),
)
TEN_LOAI = {m: t for m, t, _ in DICH}
VIEC_LOAI = {m: v for m, _, v in DICH}
DUOI_EXCEL = ('.xlsx', '.xlsm')
TOI_THIEU_MUC_GIA = 3             # ít nhất chừng này dòng có đơn giá thì coi là bảng đơn giá


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
    tung_file: list = field(default_factory=list)      # [{'file': Path, 'loai': mã DICH}]
    dong_dan: list = field(default_factory=list)       # dòng tài sản đã lọc, đưa vào hộp "Dán danh sách tài sản"
    ho_ten: str = ''                                   # chủ sử dụng đọc được từ giấy tờ (tim_ho)
    so_cccd: str = ''

    def co_du_lieu(self) -> bool:
        return bool(self.can_cu or self.dong_dat or self.dong_tai_san or self.tham_so or self.dong_dan
                    or any(f['loai'] != D_KHAC for f in self.tung_file))

    def co_du_lieu_ho(self) -> bool:
        return bool(self.dong_dat or self.dong_dan or self.dong_tai_san)


# ---------------------------------------------------------------- đọc file
def doc_noi_dung(file, bao_tien_do=None, cho=None) -> str:
    """Toàn bộ chữ của file (ô cách nhau bằng Tab, mỗi dòng bảng một dòng). Lỗi đọc: ném LoiNhap / ocr.LoiOCR (quet() bắt từng file)."""
    p = Path(file)
    duoi = p.suffix.lower()
    if duoi in DUOI_CHU:
        return p.read_text(encoding='utf-8-sig', errors='replace')
    from .quan_ly import doc_van_ban                    # 1.0.63: cùng một lõi với Đọc kết quả từ file, đọc quyết định
    return '\n'.join('\t'.join(str(o) for o in r) for r in doc_van_ban(p, bao_tien_do, cho)[0])


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


# ---------------------------------------------------------------- nhận loại file, ghi vào hộ
def _loai_excel(p: Path) -> str:
    """Excel dạng dự án (mẫu PABT) / phương án chi tiết: nhận theo cấu trúc, không cần đọc hết các sheet."""
    if p.suffix.lower() not in DUOI_EXCEL or not p.is_file():
        return ''
    from . import nhap_chi_tiet, nhap_tho
    try:
        if nhap_tho.la_file_pabt(p):
            return D_DU_AN
        if nhap_chi_tiet.la_file_chi_tiet(p):
            return D_CHI_TIET
    except Exception:                                                   # noqa: BLE001 - không nhận được: đọc như file thường
        return ''
    return ''


_RE_TIEU_DE_HO = re.compile(r'bien ban (?:kiem ke|kiem dem|dieu tra|xac minh hien trang)|phieu kiem (?:ke|dem)|giay chung nhan\s+quyen su dung')
_RE_PA_HO = re.compile(r'phuong an (?:chi tiet|boi thuong)')       # dùng .match: phải đứng đầu dòng
_RE_CHU_HO = re.compile(r'ho va ten|chu ho|chu su dung|ho ong|ong \(ba\)')
GIAY_TO_NGAN = 20000              # ký tự: giấy tờ của một hộ ngắn; cẩm nang, báo cáo có nhắc "tờ ... thửa ... m2" thì dài hơn nhiều


def la_giay_to_ho(nd: str) -> bool:
    '''Giấy tờ của MỘT hộ: tiêu đề giấy tờ ngay phần đầu file (biên bản kiểm kê, sổ đỏ; phương án kèm tên chủ hộ), hoặc văn bản ngắn có "tờ ... thửa
    ... m2". Không xét từ khóa trong toàn văn: cẩm nang, báo cáo, văn bản thẩm định đều có nhắc "biên bản kiểm kê" (đã đo trên file thật).'''
    from .lap_pa import bo_dau
    dong = [bo_dau(x.strip()) for x in str(nd or '').splitlines()[:30] if x.strip()]
    dau = ' '.join(dong)
    if _RE_TIEU_DE_HO.search(dau):
        return True
    # phương án của hộ: dòng TIÊU ĐỀ bắt đầu bằng "phương án ..." (báo cáo chỉ nhắc tới trong câu), có chủ hộ và có thửa / bảng tài sản
    if any(_RE_PA_HO.match(x) for x in dong) and _RE_CHU_HO.search(dau) and ('thua' in dau or 'ten tai san' in bo_dau(str(nd)[:5000])):
        return True
    return len(nd) <= GIAY_TO_NGAN and bool(_RE_THUA.search(nd))


def nhan_loai(p, noi_dung: str, ngu_canh: str = AUTO) -> str:
    """Loại của một file theo nội dung đã đọc (DICH). Quét riêng văn bản căn cứ: luôn là căn cứ."""
    from . import he_so_k, nhap_don_gia
    from .lap_pa import bo_dau
    p = Path(p)
    if ngu_canh == CAN_CU:
        return D_CAN_CU
    nd = str(noi_dung or '')
    if nd.strip():
        if he_so_k.la_phu_luc([nd]):
            return D_HE_SO_K
        thap = bo_dau(nd[:200000])
        if 'bang gia dat' in thap and ('diem dau' in thap and 'diem cuoi' in thap or any(he_so_k._RE_BANG.match(d) for d in nd.splitlines())):
            return D_BANG_GIA
        if p.suffix.lower() in DUOI_EXCEL:
            dau = bo_dau('\n'.join(nd.splitlines()[:40]))
            if ('ho ten' in dau or 'ho va ten' in dau or 'chu su dung' in dau) and 'thua' in dau:
                return D_DU_AN
        if la_giay_to_ho(nd):
            return D_HO_SO
        n_gia = 0
        # báo cáo đối chiếu (bảng tiền có số, có chữ đơn giá) không phải bảng đơn giá; tên file phần mềm tự đặt: "<dự án>_DoiChieu"
        if 'don gia' in thap and 'doichieu' not in bo_dau(p.stem).replace(' ', '').replace('_', '') and 'doi chieu' not in bo_dau(' '.join(nd.splitlines()[:8])):
            try:
                n_gia = sum(1 for m in nhap_don_gia.nhan_muc([r.split('\t') for r in nd.splitlines()]) if getattr(m, 'don_gia', None))
            except Exception:                                           # noqa: BLE001 - không phải bảng đơn giá
                n_gia = 0
        if n_gia >= TOI_THIEU_MUC_GIA:
            return D_DON_GIA
        if van_ban_can_cu.trich_can_cu(nd, p.name):
            return D_CAN_CU
    return {GIA_DAT: D_BANG_GIA, GIA_TAI_SAN: D_DON_GIA, HO_SO_HO: D_HO_SO}.get(ngu_canh, D_KHAC)


def _boc_ho_so(nd: str, kq: KetQuaQuet, ten_file: str) -> None:
    """Giấy tờ của hộ: chủ sử dụng, thửa (ocr_ho_so.boc_tach; không có thì mẫu 'tờ ... thửa ... m2'), dòng tài sản đã lọc."""
    from . import ocr_ho_so
    bt = ocr_ho_so.boc_tach(nd)
    kq.ho_ten = kq.ho_ten or bt.ho_ten
    kq.so_cccd = kq.so_cccd or bt.so_cccd
    duong_dat = bool(_RE_DUONG_DAT.search(nd))
    dat = [DongDat(str(t.get('so_to') or ''), str(t.get('so_thua') or ''), str(t.get('loai_dat') or ''), 'DAT_NONG_NGHIEP',
                   _so(t.get('dt_thu_hoi')), 'Bóc tách từ giấy tờ của hộ', 'DAT_SOI_DA_CAPPHOI' if duong_dat else 'NHUA_BETONG')
           for t in bt.thua if t.get('so_thua')] or nhan_dien_thua(nd)
    if dat:
        kq.dong_dat.extend(dat)
        kq.tom_tat.append(f'[Hồ sơ chi tiết] Bóc tách {len(dat)} thửa đất từ "{ten_file}".')
    loc = ocr_ho_so.dong_dua_vao_dan(nd)
    if loc.giu:
        kq.dong_dan.extend(loc.giu)
        kq.tom_tat.append(f'[Hồ sơ chi tiết] {loc.ly_do or f"Lấy {len(loc.giu)} dòng tài sản."}')


def tim_ho(con, kq: KetQuaQuet):
    """Hộ khớp giấy tờ vừa quét: số CCCD, không có thì họ tên trùng DUY NHẤT. None: không chắc - người dùng tự chọn."""
    from .lap_pa import bo_dau
    if kq.so_cccd:
        ds = con.execute('SELECT ma_ho FROM ho WHERE so_cccd = ?', (kq.so_cccd,)).fetchall()
        if len(ds) == 1:
            return ds[0][0]
    if kq.ho_ten:
        ten = bo_dau(kq.ho_ten)
        ds = [r[0] for r in con.execute('SELECT ma_ho, ho_ten FROM ho') if bo_dau(r[1]) == ten]
        if len(ds) == 1:
            return ds[0]
    return None


def _so_thua(x) -> str:
    return str(x or '').strip().lstrip('0') or '0'


def ghi_thua_vao_ho(bo, ds_dat) -> tuple:
    """Thêm dòng mục 1 (BoSoan - CHƯA lưu) cho các thửa quét được, khớp theo tờ + thửa của hộ; diện tích theo giấy tờ; đường đất ghi vào
    Ghi chú để người lập chọn K3 ở bảng tính giá. Trả (số dòng thêm, [thửa không có trong hồ sơ hộ], [thửa đã có dòng])."""
    from .tien import so_vn
    theo = {(_so_thua(t['so_to']), _so_thua(t['so_thua'])): t['ma_thua'] for t in bo.bc.thua_cua(bo.ma_ho)}
    da_co = {d.ma_thua for d in bo.pa.dat}
    them, thieu, trung = 0, [], []
    for d in ds_dat:
        ten = f'tờ {d.to_ban_do} thửa {d.so_thua}'
        ma = theo.get((_so_thua(d.to_ban_do), _so_thua(d.so_thua)))
        if ma is None:
            thieu.append(ten)
        elif ma in da_co:
            trung.append(ten)
        else:
            i, _ = bo.them_thua(ma)
            if d.dien_tich_thu_hoi > 0:
                bo.sua_dat(i, 'dien_tich', so_vn(d.dien_tich_thu_hoi))
            if d.ket_cau_mat_duong == 'DAT_SOI_DA_CAPPHOI':
                cu = bo.pa.dat[i].ghi_chu
                bo.pa.dat[i].ghi_chu = ((cu + '; ') if cu else '') + 'Giấy tờ ghi tiếp giáp đường đất, sỏi, đá, cấp phối: xem K3 (Phụ lục III QĐ 03)'
            da_co.add(ma)
            them += 1
    return them, thieu, trung


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
        if doc is None and ngu_canh != CAN_CU:                          # file dự án lớn: nhận theo cấu trúc, không đọc hết các sheet
            loai_x = _loai_excel(p)
            if loai_x:
                kq.tung_file.append({'file': p, 'loai': loai_x})
                kq.tom_tat.append(f'"{p.name}": {TEN_LOAI[loai_x]}.')
                continue
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
        loai_f = nhan_loai(p, nd, ngu_canh)
        kq.tung_file.append({'file': p, 'loai': loai_f})
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
        if loai_f == D_HO_SO:
            loai.append(HO_SO_HO)
            _boc_ho_so(nd, kq, p.name)
    kq.loai_phat_hien = list(dict.fromkeys(loai))
    kq.can_cu = list(dict.fromkeys(kq.can_cu))
    kq.do_tin_cay = 0.0 if not kq.co_du_lieu() else 0.99 if not kq.loi else 0.8
    kq.thoi_gian_ms = int((time.perf_counter() - bat_dau) * 1000)
    return kq

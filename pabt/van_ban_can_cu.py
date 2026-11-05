"""Mục "Văn bản căn cứ": khử trùng lặp và sắp xếp theo 13 bậc hiệu lực pháp lý (Trung ương -> địa phương). Không Qt.

Chuyển từ `mergeAndSortLegalBases` / `classifyAndParseLegalDocument` / `extractLegalCitationsFromText` của
HeThongDinhGiaVaScanThongMinh_V2.tsx (05/11/2026). 13 bậc theo file đặc tả QuyChuan_DinhGiaDat_NQ28_QD03 (Phần 4):
 1 Hiến pháp | 2 Bộ luật, Luật | 3 Nghị quyết Quốc hội | 4 Pháp lệnh, NQ UBTV Quốc hội | 5 Lệnh, QĐ Chủ tịch nước | 6 Nghị định, NQ Chính phủ
 | 7 QĐ, CT Thủ tướng | 8 Thông tư | 9 Văn bản hợp nhất | 10 Văn bản hướng dẫn Chính phủ / Bộ, ngành TW | 11 NQ HĐND tỉnh, thành phố
 | 12 QĐ, CT UBND tỉnh, thành phố | 13 Văn bản Sở, ban, ngành và chính quyền cấp cơ sở.
Trong cùng bậc: năm ban hành rồi số thứ tự văn bản tăng dần. Mỗi lần quét thêm văn bản thì gộp + sắp xếp lại.

Khác bản TSX ở CÁCH NHẬN BẬC (không đổi 13 bậc, thứ tự sắp xếp, cách khử trùng) - sửa hai lỗi nhận biết, kiểm bằng
tests/test_van_ban_can_cu.py:
 - bản TSX tìm từ khóa trên TOÀN CÂU nên "Nghị quyết 254/2025/QH15 ... thi hành Luật Đất đai" rơi vào bậc 2, "Nghị định 49/2026 ...
   Nghị quyết ... của Quốc hội" vào bậc 3, VB 1201/SNNMT "triển khai Quyết định ..." vào bậc 12: nay nhận theo hậu tố số hiệu (QH, NĐ-CP,
   QĐ-UBND, SNNMT...) và phần ĐẦU câu (loại văn bản của chính văn bản đó);
 - bản TSX lấy MÃ SỐ ĐẦU TIÊN trong câu làm khóa khử trùng: văn bản không có số hiệu ("Văn bản hướng dẫn ngày 29/5/2026 ... theo Nghị
   quyết số 28/2025/NQ-HĐND") bị coi là NQ 28 và ghi đè mất NQ 28: nay lấy số hiệu đứng sau chữ "số" của chính văn bản, không có thì
   khóa theo ngày + cơ quan ban hành."""
from __future__ import annotations

import re
from dataclasses import dataclass

TEN_BAC = {
    1: 'Hiến pháp',
    2: 'Bộ luật, Luật của Quốc hội',
    3: 'Nghị quyết của Quốc hội',
    4: 'Pháp lệnh, Nghị quyết của Ủy ban Thường vụ Quốc hội; Lệnh, Quyết định của Chủ tịch nước',
    5: 'Nghị định, Nghị quyết của Chính phủ',
    6: 'Quyết định, Chỉ thị của Thủ tướng Chính phủ',
    7: 'Thông tư, Thông tư liên tịch',
    8: 'Văn bản hợp nhất',
    9: 'Văn bản hướng dẫn của Chính phủ, Bộ ngành Trung ương',
    10: 'Nghị quyết của HĐND tỉnh, thành phố',
    11: 'Quyết định, Chỉ thị của UBND tỉnh, thành phố',
    12: 'Văn bản hướng dẫn của Sở, ngành tỉnh, thành phố',
    13: 'Văn bản cấp xã, phường và đơn vị cơ sở',
}

# danh sách căn cứ mặc định của cửa sổ tính giá đất (theo TSX DEFAULT_LEGAL_BASES)
CAN_CU_MAC_DINH = (
    'Luật Đất đai số 31/2024/QH15 ngày 18/01/2024 của Quốc hội (được sửa đổi, bổ sung năm 2024, 2025)',
    'Nghị quyết số 254/2025/QH15 của Quốc hội quy định một số cơ chế, chính sách tháo gỡ khó khăn, vướng mắc trong tổ chức thi hành '
    'Luật Đất đai',
    'Nghị định số 49/2026/NĐ-CP của Chính phủ quy định chi tiết và hướng dẫn thi hành một số điều của Nghị quyết số 254/2025/QH15 của '
    'Quốc hội',
    'Nghị quyết số 27/2025/NQ-HĐND của HĐND tỉnh Đồng Nai quy định về tiêu chí xác định khu vực, vị trí đất trong Bảng giá đất trên địa '
    'bàn tỉnh Đồng Nai',
    'Nghị quyết số 28/2025/NQ-HĐND ngày 10/5/2025 của HĐND tỉnh Đồng Nai quy định Bảng giá đất lần đầu trên địa bàn tỉnh Đồng Nai '
    'năm 2026',
    'Quyết định số 03/2026/QĐ-UBND ngày 11/5/2026 của UBND thành phố Đồng Nai quy định hệ số điều chỉnh giá đất trên địa bàn thành '
    'phố Đồng Nai năm 2026',
    'Văn bản số 1201/SNNMT-ĐĐ ngày 20/5/2026 của Sở Nông nghiệp và Môi trường về việc triển khai Quyết định số 03/2026/QĐ-UBND',
    'Văn bản hướng dẫn ngày 29/5/2026 của Sở Nông nghiệp và Môi trường về việc xác định giá đất nông nghiệp theo Nghị quyết số '
    '28/2025/NQ-HĐND và Quyết định số 03/2026/QĐ-UBND',
)

_MA = r'(\d+[A-Za-z]?)\s*/\s*(?:(\d{4})\s*/\s*)?([\w\-]+)'
_RE_SO = re.compile(r'(?i)\bsố\s*:?\s*' + _MA)
_RE_MA_DAU = re.compile(r'^\W{0,3}(?:[^\d/]{0,40}?)' + _MA)
_RE_NGAY = re.compile(r'(?i)ngày\s*(\d{1,2})\s*[/\-]\s*(\d{1,2})\s*[/\-]\s*(\d{4})')
_RE_HET_DAU = re.compile(r'(?i)\b(?:ngày|của|về|theo|quy định)\b')
_RE_NAM = re.compile(r'\b(19\d{2}|20\d{2})\b')
_RE_CO_QUAN = re.compile(r'(?i)\bcủa\s+(.+?)(?:\s+(?:về|quy định|hướng dẫn|ban hành|triển khai)\b|[,.;]|$)')


@dataclass
class VanBan:
    chu: str
    so_hieu: str
    loai: str
    bac: int
    nam: int
    stt: int

    @property
    def khoa(self) -> str:
        return re.sub(r'\s+', '', self.so_hieu).upper()


def _bac_theo_hau_to(hau: str, dau: str, truoc_ubnd_cap_co_so: bool) -> int:
    """Bậc theo hậu tố số hiệu (phần sau năm: QH15, NĐ-CP, QĐ-UBND, SNNMT-ĐĐ...) và loại văn bản ở phần đầu câu."""
    h = hau.upper()
    if 'UBTVQH' in h or h.startswith(('L-CTN', 'QĐ-CTN', 'QD-CTN')):
        return 4
    if h.startswith('QH'):
        return 3 if 'nghị quyết' in dau else 2
    if h.startswith(('NĐ-CP', 'ND-CP', 'NQ-CP')):
        return 5
    if h.startswith(('QĐ-TTG', 'QD-TTG', 'CT-TTG')):
        return 6
    if h.startswith(('TTLT', 'TT-')):
        return 7
    if h.startswith('VBHN'):
        return 8
    if h.startswith(('NQ-HĐND', 'NQ-HDND')):
        return 13 if truoc_ubnd_cap_co_so else 10
    if h.startswith(('QĐ-UBND', 'QD-UBND', 'CT-UBND', 'QĐ-', 'QD-')):
        return 13 if truoc_ubnd_cap_co_so else 11
    if h.startswith(('BNNMT', 'BTNMT', 'BNN', 'BTC', 'BXD', 'BTP', 'BKHĐT', 'VPCP', 'BNV')):
        return 9
    if h.startswith(('SNN', 'STNMT', 'SXD', 'STC', 'SGTVT', 'SKHĐT', 'S')) and not truoc_ubnd_cap_co_so and h != 'UBND':
        return 12
    return 0


def _bac_theo_chu_dau(dau: str, cap_co_so: bool) -> int:
    """Bậc theo từ khóa trong phần ĐẦU câu (loại văn bản + cơ quan ban hành)."""
    if 'hiến pháp' in dau:
        return 1
    if re.search(r'\b(bộ )?luật\b', dau):
        return 2
    if 'nghị quyết' in dau and 'quốc hội' in dau and 'ủy ban thường vụ' not in dau:
        return 3
    if 'pháp lệnh' in dau or 'chủ tịch nước' in dau or ('nghị quyết' in dau and ('ủy ban thường vụ quốc hội' in dau or 'ubtvqh' in dau)):
        return 4
    if 'nghị định' in dau or ('nghị quyết' in dau and 'chính phủ' in dau):
        return 5
    if ('quyết định' in dau or 'chỉ thị' in dau) and 'thủ tướng' in dau:
        return 6
    if 'thông tư' in dau:
        return 7
    if 'văn bản hợp nhất' in dau:
        return 8
    if re.search(r'\bchính phủ\b|\bbộ (nông nghiệp|tài nguyên|tài chính|xây dựng|tư pháp|nội vụ|kế hoạch)', dau):
        return 9
    if cap_co_so:
        return 13
    if 'nghị quyết' in dau and ('hđnd' in dau or 'hội đồng nhân dân' in dau):
        return 10
    if ('quyết định' in dau or 'chỉ thị' in dau) and 'ubnd' in dau:
        return 11
    if re.search(r'\bsở\b|\bban quản lý\b', dau):
        return 12
    return 13


def phan_loai(chu: str) -> VanBan:
    """Một dòng căn cứ -> VanBan (số hiệu, bậc, năm, số thứ tự)."""
    s = str(chu or '').strip()
    s = re.sub(r'^\d+[.)]\s*', '', s)
    s = re.sub(r'^[-•+]\s*', '', s)
    s = re.sub(r';$', '', s).strip()
    thap = s.lower()
    m_ngay = _RE_NGAY.search(s)
    gioi = _RE_HET_DAU.search(s)
    m = _RE_SO.search(s)
    if m is None:                                       # "Quyết định 03/2026/QĐ-UBND ..." (không có chữ "số"): mã nằm ngay đầu câu
        m = _RE_MA_DAU.match(s)
    if m is not None and gioi is not None and m.start(1) > gioi.start() and (m.start(1) > 12 or m.re is _RE_SO):
        m = None                                        # số nằm trong thân câu ("... theo Nghị quyết số 28/2025/..."): không phải của văn bản này
    # phần đầu: từ đầu câu tới chữ "số" / mã số / "ngày" / "của" đầu tiên = loại văn bản của CHÍNH văn bản này
    diem = [x for x in (m.start() if m else -1, m_ngay.start() if m_ngay else -1) if x >= 0]
    cat = min(diem) if diem else len(s)
    dau = thap[:cat] if cat > 0 else thap
    m_cq = re.search(r'\bcủa\s+(.*)$', thap[cat:] if cat < len(thap) else '')
    co_quan = m_cq.group(1)[:60] if m_cq else ''
    cap_co_so = bool(re.search(r'\bubnd\s+(xã|phường|thị trấn)|\bủy ban nhân dân\s+(xã|phường|thị trấn)', thap))
    if co_quan:
        dau = dau + ' ' + co_quan
    if m:
        stt = int(re.sub(r'\D', '', m.group(1)) or 0) if m.group(1) else 9999
        nam = int(m.group(2)) if m.group(2) else (int(m_ngay.group(3)) if m_ngay else _nam_dau(s))
        hau = m.group(3)
        so_hieu = f'{m.group(1)}/' + (f'{m.group(2)}/' if m.group(2) else '') + hau
        bac = _bac_theo_hau_to(hau, thap[:cat] if cat > 0 else thap, cap_co_so) or _bac_theo_chu_dau(dau, cap_co_so)
    else:                                               # không số hiệu (văn bản hướng dẫn "ngày 29/5/2026 của Sở ..."): khóa theo ngày + cơ quan
        stt = 9999
        nam = int(m_ngay.group(3)) if m_ngay else _nam_dau(s)
        ngay = '/'.join(m_ngay.groups()) if m_ngay else str(nam)
        mc = _RE_CO_QUAN.search(s)
        so_hieu = f'VB-{ngay}-{(mc.group(1) if mc else s[:30]).strip()}'
        bac = _bac_theo_chu_dau(dau, cap_co_so)
    return VanBan(s, so_hieu, TEN_BAC[bac], bac, nam, stt)


def _nam_dau(s: str) -> int:
    m = _RE_NAM.search(s)
    return int(m.group(1)) if m else 2026


def gop_va_sap_xep(hien_co, moi=()) -> tuple:
    """Gộp các khối chữ (mỗi dòng / dấu ';' một văn bản), khử trùng theo số hiệu (giữ bản dài hơn), sắp theo (bậc, năm, số).
    Trả (chữ đã đánh số "1. …;" mỗi văn bản một dòng, danh sách VanBan)."""
    cac = []
    for khoi in list(hien_co or ()) + list(moi or ()):
        for dong in re.split(r'\r?\n|;', str(khoi or '')):
            d = dong.strip()
            if len(d) > 5 and not d.endswith('...'):
                cac.append(d)
    theo_ma = {}
    for d in cac:
        v = phan_loai(d)
        cu = theo_ma.get(v.khoa)
        if cu is None or len(v.chu) > len(cu.chu):
            theo_ma[v.khoa] = v
    ds = sorted(theo_ma.values(), key=lambda v: (v.bac, v.nam, v.stt))
    return '\n'.join(f'{i + 1}. {v.chu};' for i, v in enumerate(ds)), ds


# ---------------------------------------------------------------- trích dẫn văn bản trong nội dung một file
_RE_CAN_CU = re.compile(r'(?i)^căn cứ\s+(luật|bộ luật|nghị quyết|nghị định|thông tư|quyết định|văn bản|công văn)')
_CO_DINH = (
    (r'31/2024/QH15', 'Luật Đất đai số 31/2024/QH15 ngày 18/01/2024 của Quốc hội (được sửa đổi, bổ sung năm 2024, 2025)'),
    (r'254/2025/QH15', 'Nghị quyết số 254/2025/QH15 của Quốc hội quy định một số cơ chế, chính sách tháo gỡ khó khăn, vướng mắc trong tổ '
                       'chức thi hành Luật Đất đai'),
    (r'49/2026/NĐ-CP', 'Nghị định số 49/2026/NĐ-CP của Chính phủ quy định chi tiết và hướng dẫn thi hành một số điều của Nghị quyết số '
                       '254/2025/QH15 của Quốc hội'),
    (r'27/2025/NQ-HĐND', 'Nghị quyết số 27/2025/NQ-HĐND của HĐND tỉnh Đồng Nai quy định về tiêu chí xác định khu vực, vị trí đất trong '
                         'Bảng giá đất trên địa bàn tỉnh Đồng Nai'),
    (r'28/2025/NQ-HĐND', 'Nghị quyết số 28/2025/NQ-HĐND ngày 10/5/2025 của HĐND tỉnh Đồng Nai quy định Bảng giá đất lần đầu trên địa '
                         'bàn tỉnh Đồng Nai năm 2026'),
    (r'03/2026/QĐ-UBND', 'Quyết định số 03/2026/QĐ-UBND ngày 11/5/2026 của UBND thành phố Đồng Nai quy định hệ số điều chỉnh giá đất '
                         'trên địa bàn thành phố Đồng Nai năm 2026'),
    (r'1201/SNNMT-ĐĐ', 'Văn bản số 1201/SNNMT-ĐĐ ngày 20/5/2026 của Sở Nông nghiệp và Môi trường về việc triển khai Quyết định số '
                       '03/2026/QĐ-UBND ngày 11/5/2026 của UBND thành phố Đồng Nai'),
)
_VB_29_5 = ('Văn bản hướng dẫn ngày 29/5/2026 của Sở Nông nghiệp và Môi trường về việc xác định giá đất nông nghiệp theo Nghị quyết số '
            '28/2025/NQ-HĐND và Quyết định số 03/2026/QĐ-UBND')


def trich_can_cu(noi_dung: str, ten_file: str = '') -> list:
    """Các văn bản căn cứ trong nội dung file: dòng "Căn cứ Luật / Nghị quyết / …" + các văn bản chuẩn của bộ quy chuẩn nhận ra theo
    số hiệu (hoặc tên file như bản gốc: '03.pdf', '...1201...')."""
    kq = []
    for dong in str(noi_dung or '').splitlines():
        d = dong.strip()
        if _RE_CAN_CU.match(d):
            kq.append(re.sub(r';$', '', re.sub(r'(?i)^căn cứ\s+', '', d)).strip())
    gop = f'{ten_file} \n {noi_dung}'
    ten = str(ten_file or '')
    for ma, chu in _CO_DINH:
        if re.search(ma, gop, re.I) or (ma.startswith('03/2026') and ten.startswith('03.')) or (ma.startswith('1201') and '1201' in ten):
            kq.append(chu)
    if 'apdunghesotrongtinhgiadat' in ten.lower() or re.search(r'(?i)đường đất,\s*sỏi,\s*đá,\s*cấp phối', gop):
        kq.append(_VB_29_5)
    return list(dict.fromkeys(kq))


# ---------------------------------------------------------------- lưu theo dự án (bảng cai_dat - không thuộc danh mục khóa)
MA_CAI_DAT = 'VB_CAN_CU_GIA_DAT'


def doc_can_cu_du_an(con) -> str:
    """Văn bản căn cứ của dự án (đã sắp 13 bậc); chưa có thì danh sách mặc định của bộ quy chuẩn NQ 28 / QĐ 03."""
    from . import csdl
    chu = csdl.doc_cai_dat(con, MA_CAI_DAT, '') if con is not None else ''
    return gop_va_sap_xep([chu] if chu else CAN_CU_MAC_DINH)[0]


def ghi_can_cu_du_an(con, chu: str) -> str:
    """Gộp + sắp xếp rồi lưu vào dự án; trả chữ đã lưu. Gọi sau khi người dùng bấm Lưu / Áp (không ghi khi chỉ xem)."""
    from . import csdl
    from .lap_pa import kiem_quyen
    kiem_quyen(con, 'sua_gia', 'ghi văn bản căn cứ giá đất')
    kq, ds = gop_va_sap_xep([chu])
    with csdl.giao_dich(con):
        csdl.ghi_cai_dat(con, MA_CAI_DAT, kq)
        csdl.ghi_nhat_ky(con, 'Cập nhật văn bản căn cứ giá đất', f'{len(ds)} văn bản, sắp theo 13 bậc hiệu lực')
    return kq

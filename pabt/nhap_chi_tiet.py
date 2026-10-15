"""Nhập phương án chi tiết từng hộ từ file Excel kiểu bản in "PHƯƠNG ÁN CHI TIẾT" (mỗi sheet một hộ, như mẫu IN_CHITIET):
thông tin hộ (Họ và tên / Số CCCD / Địa chỉ / Số điện thoại), "II. Thông tin nguồn gốc đất", bảng STT / Tên tài sản / ĐVT /
Số lượng / Đơn giá / Tỷ lệ / Thành tiền / Ghi chú theo mục 1 (đất) - 2 (nhà, công trình) - 3 (cây trồng) - 4 (hỗ trợ) - 5
(thưởng, phần mềm tự tính), dòng TỔNG CỘNG.

doc(file) -> KetQuaDoc (danh sách HoChiTiet, mỗi sheet một hộ; sheet mẫu / lỗi công thức / không có họ tên thì chon = False)
ghi(con, ds_ho, trung=...) -> BaoCaoNhap: thêm hộ, thửa, dòng phương án vào dự án đang có (không xóa hộ khác).

Dòng mục 2, 3 so khớp tên với bộ đơn giá của dự án: cùng tên và cùng đơn giá -> dòng danh mục (có mã); cùng tên khác giá ->
nhập tay (ghi giá danh mục ở Căn cứ giá); không có trong danh mục -> nhập tay theo đơn giá của file. Thành tiền của file lưu
vào thanh_tien_excel và tổng từng mục vào tong_excel để đối chiếu (Lập phương án → Đối chiếu file Excel).
"""
from __future__ import annotations
import re
from bisect import insort
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path

from . import csdl
from .ho_so import chuan_loai_dat
from .nhap_excel import chuan_cccd
from .lap_pa import DanhMuc, LoiNhap, bo_dau, doc_so
from .nghiep_vu import (MUC_KHOAN, MUC_VN, NGUON_DM, NGUON_TAY, SO_MUC, BoiCanh, DongDat, DongKhoan, so_muc, thanh_tien_dong,
                        thanh_tien_dong_dat)
from .tien import D, KHONG, chuoi, so_vn, vn

TRANG_THAI = 'Đã lập phương án (nhập từ Excel chi tiết)'
LOI_EXCEL = ('#N/A', '#VALUE!', '#REF!', '#DIV/0!', '#NAME?', '#NUM!', '#NULL!')
# tiêu đề cột bảng tính toán (chữ không dấu, so đầu chuỗi)
COT = {'stt': ('stt',), 'ten': ('ten tai san', 'noi dung', 'hang muc', 'ten'), 'dvt': ('dvt', 'don vi'),
       'sl': ('so luong', 'khoi luong', 'dien tich'), 'dg': ('don gia',), 'tl': ('ty le',), 'tt': ('thanh tien',),
       'gc': ('ghi chu',)}
NHAN = {'ho_ten': ('ho va ten', 'ho ten', 'ten to chuc', 'to chuc', 'chu ho', 'chu su dung'),
        'cccd': ('so cccd', 'cccd', 'so cmnd', 'cmnd', 'can cuoc', 'chung minh', 'so dinh danh', 'dinh danh'),
        'dia_chi': ('dia chi',),
        'dien_thoai': ('so dien thoai', 'dien thoai', 'sdt')}


@dataclass
class DongBang:
    """Một dòng trong bảng tính toán của file."""
    dong: int                       # số dòng Excel
    stt: str
    ten: str
    dvt: str = ''
    so_luong: object = None         # Decimal / None (ô trống)
    don_gia: object = None
    ty_le: object = None
    thanh_tien: object = None
    ghi_chu: str = ''
    con: bool = False               # dòng con ("-", "+") của dòng phía trên


@dataclass
class HoChiTiet:
    sheet: str
    ho_ten: str = ''
    so_cccd: str = ''
    ngay_cap: str = ''
    noi_cap: str = ''
    dia_chi: str = ''
    dien_thoai: str = ''
    nguon_goc: str = ''
    tai_dinh_cu: str = ''
    dat: list = field(default_factory=list)                                   # [DongBang] mục 1
    khoan: dict = field(default_factory=lambda: {m: [] for m in MUC_KHOAN})   # {mục: [DongBang]} (vật nuôi = MUC_VN)
    tong: dict = field(default_factory=dict)                                  # {1..5, 'tong'}: số trên dòng mục / TỔNG CỘNG
    canh_bao: list = field(default_factory=list)
    loi: list = field(default_factory=list)                                   # lỗi chặn (ô #N/A...): mặc định không nhập
    chon: bool = True
    ly_do: str = ''                                                           # lý do mặc định không chọn

    @property
    def ten_ngan(self) -> str:
        """Họ tên (bỏ phần "là chủ sở hữu…")."""
        return re.split(r'\s+là\s+', self.ho_ten, maxsplit=1)[0].strip(' ,.')

    @property
    def so_dong(self) -> int:
        return sum(len(v) for v in self.khoan.values())


@dataclass
class KetQuaDoc:
    file: str
    ho: list = field(default_factory=list)                                    # [HoChiTiet]
    du_an: dict = field(default_factory=dict)                                 # thông tin dự án đọc từ đầu trang
    bo_qua: list = field(default_factory=list)                                # sheet không phải phương án chi tiết


@dataclass
class BaoCaoNhap:
    them: list = field(default_factory=list)          # [(mã hộ, họ tên)]
    thay: list = field(default_factory=list)
    bo_qua: list = field(default_factory=list)        # [(sheet, lý do)]
    so_thua: int = 0
    so_dong: int = 0
    canh_bao: list = field(default_factory=list)

    @property
    def so_ho(self) -> int:
        return len(self.them) + len(self.thay)


# ---------------------------------------------------------------- đọc ô
def _nfc(v) -> str:
    return unicodedata.normalize('NFC', str(v)).replace('_x000D_', '').replace('\r', '')


def _txt(v) -> str:
    """Chữ một dòng (gộp khoảng trắng, xuống dòng)."""
    return ' '.join(_nfc(v).split()) if v is not None else ''


def _doan(v) -> str:
    """Chữ nhiều đoạn: giữ xuống dòng, bỏ thụt đầu dòng."""
    return '\n'.join(' '.join(x.split()) for x in _nfc(v if v is not None else '').split('\n') if x.strip())


def _la_loi(v) -> bool:
    return isinstance(v, str) and v.strip().upper() in LOI_EXCEL


def _so(v):
    """Ô số -> Decimal (số thực của Excel làm tròn 6 chữ số lẻ: 14,399999999 -> 14,4); trống -> None; lỗi -> ValueError."""
    if v is None or isinstance(v, bool) or (isinstance(v, str) and not v.strip()):
        return None
    if isinstance(v, int):
        return D(v)
    if isinstance(v, float):
        return D(round(v, 6))
    if _la_loi(v):
        raise ValueError(f'ô lỗi {v.strip()}')
    try:
        return doc_so(_txt(v), 'Ô số')
    except LoiNhap:
        raise ValueError(f'"{_txt(v)}" không phải là số') from None


def _ty_le(v):
    """Tỷ lệ: 0,8 / '80%' / 80 -> 0,8; trống -> None (= 100%)."""
    x = _so(v)
    if x is None:
        return None
    return x / 100 if x > 5 else x


def _bat_dau(s: str, mau: tuple) -> bool:
    return any(s == m or s.startswith(m + ' ') or s.startswith(m + ':') or s.startswith(m + '(') for m in mau)


# ---------------------------------------------------------------- nhận sheet
def _tim_tieu_de(hang: list):
    """(chỉ số dòng tiêu đề STT, {khóa: cột}) hoặc None."""
    for i, r in enumerate(hang[:80]):
        chu = [bo_dau(_txt(v)).rstrip(':') for v in r]
        if 'stt' not in chu:
            continue
        cot = {}
        for c, s in enumerate(chu):
            if not s:
                continue
            for k, mau in COT.items():
                if k not in cot and (s in mau or any(s.startswith(m) for m in mau if m not in ('ten', 'dvt'))):
                    cot[k] = c
                    break
        if {'ten', 'sl', 'tt'} <= set(cot):
            return i, cot
    return None


def _gia_tri_sau(r: list, c: int) -> str:
    for v in r[c + 1:]:
        if v not in (None, '') and _txt(v):
            return _doan(v)
    return ''


def _doc_cccd(s: str) -> tuple:
    """'092075012345 - ngày 29/9/2021 - Nơi cấp: Cục CS QLHC về TTXH.' -> (số, ngày cấp, nơi cấp)."""
    # ô có hai người (chồng / vợ): "030056005715\n030158008419" hoặc "… ; …" -> số đầu (ghép lại thành 24 chữ số là sai)
    s = re.split(r'\n|;|\s-\s(?=\d)|\svà\s', _nfc(s).strip())[0]
    s = _txt(s).rstrip('.')
    m = re.match(r'([\d\s.]{9,20})', s)
    so = re.sub(r'\D', '', m.group(1)) if m else ''
    so = chuan_cccd(so)                                  # ô số Excel mất số 0 đầu (11 chữ số)
    if not so or len(so) < 9:
        return '', '', ''
    ngay = re.search(r'(?:ngày\s*(?:cấp)?\s*:?\s*)?(\d{1,2}/\d{1,2}/\d{4})', s, re.I)
    noi = re.search(r'nơi\s*cấp\s*:?\s*(.+)$', s, re.I)
    return so, ngay.group(1) if ngay else '', noi.group(1).strip(' .-') if noi else ''


def _thua_tu_ten(ten: str) -> dict:
    """'Thửa đất số 168, tờ bản đồ số 156, loại đất RPD, phường Trị An (Vị trí 1)' / 'Thửa 457 tờ 35 - đất LUK (VT 1: phạm
    vi 2)' -> so_thua, so_to, loai_dat, vi_tri."""
    t = _txt(ten)
    so_thua = re.search(r'thửa(?:\s+đất)?\s+số\s*:?\s*([^,(]+)', t, re.I)
    if so_thua and re.search(r'\stờ\s', so_thua.group(1), re.I):          # "Thửa đất số 457 tờ 35…": số thửa là một cụm
        so_thua = re.search(r'thửa(?:\s+đất)?\s+số\s*:?\s*(\d[^\s,(]*)', t, re.I)
    so_thua = so_thua or re.search(r'thửa(?:\s+đất)?\s*:?\s*(\d[^\s,(]*)', t, re.I)      # "Thửa 457 tờ 35 - đất LUK"
    so_to = re.search(r'tờ(?:\s+bản\s+đồ)?(?:\s+địa\s+chính)?(?:\s+số)?\s*:?\s*([^,(]+)', t, re.I)
    if so_to and not re.fullmatch(r'[\w./-]+', so_to.group(1).strip(' .')):
        so_to = re.search(r'tờ(?:\s+bản\s+đồ)?(?:\s+địa\s+chính)?(?:\s+số)?\s*:?\s*(\d[^\s,(]*)', t, re.I)
    ld = re.search(r'loại\s+đất\s*:?\s*([A-ZĐ]{2,4}(?:\s*\+\s*[A-ZĐ]{2,4})*)', t) or \
        re.search(r'(?:^|[\s-])đất\s+([A-ZĐ]{2,4}(?:\s*\+\s*[A-ZĐ]{2,4})*)\b', t)                  # "- đất LUK"
    vt = re.search(r'\((?:vị\s+trí|vt)\s*:?\s*([^)]+)\)', t, re.I)
    return dict(so_thua=so_thua.group(1).strip(' .') if so_thua else '', so_to=so_to.group(1).strip(' .') if so_to else '',
                loai_dat=chuan_loai_dat(ld.group(1)) if ld else '', vi_tri=vt.group(1).strip() if vt else '',
                mot_phan=bool(re.match(r'một\s+phần', t, re.I)))


def muc_theo_ten(ten: str) -> int:
    """Mục theo tên dòng mục ("Bồi thường đất", "…vật kiến trúc", "…cây trồng", "…vật nuôi", "Hỗ trợ các loại", "Thưởng…"):
    1, 2, 3, MUC_VN (chỉ vật nuôi; "cây trồng, vật nuôi" = 3), 4, 5; 0 = không rõ."""
    k = bo_dau(ten)
    if k.startswith('thuong') or 'ban giao' in k and 'truoc thoi han' in k:
        return 5
    if re.search(r'cay trong|hoa mau|cay coi', k):
        return 3
    if re.search(r'vat nuoi|thuy san', k):
        return MUC_VN
    if re.search(r'vat kien truc|\bnha\b|cong trinh|tai san', k):
        return 2
    if re.search(r'(boi thuong|ve) dat\b|dat dai', k):
        return 1
    if k.startswith('ho tro') or 'chinh sach ho tro' in k:
        return 4
    return 0


_LA_MA = {'i': 1, 'ii': 2, 'iii': 3, 'iv': 4, 'v': 5}
_MUC_THEO_SO = {v: k for k, v in SO_MUC.items()}           # bản in từ 0.9.21: 4 vật nuôi, 5 hỗ trợ, 6 thưởng
_MUC_TONG = (1, 2, 3, MUC_VN, 4, 5)


def doc_sheet(ten_sheet: str, hang: list):
    """Một sheet (danh sách dòng giá trị) -> HoChiTiet, hoặc None nếu không có bảng tính toán kiểu phương án chi tiết."""
    td = _tim_tieu_de(hang)
    if td is None:
        return None
    i0, cot = td
    h = HoChiTiet(ten_sheet)
    # thông tin hộ, nguồn gốc đất (phía trên bảng)
    ng, trong_ng = [], False
    for r in hang[:i0]:
        chu = [(c, _txt(v)) for c, v in enumerate(r) if v not in (None, '') and _txt(v)]
        if not chu:
            continue
        c0, s0 = chu[0]
        k0 = bo_dau(s0)
        if re.match(r'(ii|2)[.)]?\s', k0) and 'nguon goc' in k0:
            trong_ng = True
            continue
        if re.match(r'(iii|3)[.)]?\s', k0) or k0 in ('iii', 'iii.'):
            trong_ng = False
            continue
        if trong_ng:
            if not re.match(r'theo (chi tiet|bang)', k0):          # "Theo chi tiết sau:" (dẫn vào bảng) không phải nguồn gốc
                ng.append(' '.join(_doan(r[c]) for c, _ in chu))
            continue
        for c, s in chu[:3]:
            k = bo_dau(s).rstrip(':').strip()
            if len(k) > 40:
                continue
            for truong, mau in NHAN.items():
                if _bat_dau(k, mau) and not getattr(h, truong if truong != 'cccd' else 'so_cccd'):
                    gt = _gia_tri_sau(r, c)
                    if truong == 'cccd':
                        h.so_cccd, h.ngay_cap, h.noi_cap = _doc_cccd(gt)
                        so_khac = [x for x in re.findall(r'\d{9,12}', re.sub(r'[ .]', '', gt)) if x != h.so_cccd]
                        if h.so_cccd and so_khac:
                            h.canh_bao.append(f'Ô CCCD có nhiều số: lấy {h.so_cccd}, số khác ({", ".join(so_khac)}) '
                                              'ghi vào hồ sơ hộ nếu cần.')
                        if gt and not h.so_cccd:
                            h.canh_bao.append(f'Số CCCD "{_txt(gt)}" không đọc được, để trống.')
                    elif truong == 'ho_ten':
                        h.ho_ten = _txt(gt)
                    else:
                        setattr(h, truong, _txt(gt).rstrip('.'))
                    break
    h.nguon_goc = '\n'.join(x for x in ng if x)
    # bảng tính toán
    muc, loi_o = 0, []

    def o(r, k):
        c = cot.get(k)
        return r[c] if c is not None and c < len(r) else None

    # hai kiểu đánh số: mẫu IN_CHITIET (mục 1, 2… / dòng 1.1, 2.3…) hoặc mục La Mã I, II… (nhóm A / B) với dòng 1, 2, 3…
    # (bảng kiểu "Phương án bồi thường bằng tiền" - áp giá NĐC). Kiểu La Mã: mục lấy theo TÊN dòng mục (muc_theo_ten).
    la_ma = any(re.fullmatch(r'[ivx]+\.?', bo_dau(_txt(o(r, 'stt')))) and muc_theo_ten(_txt(o(r, 'ten')))
                for r in hang[i0 + 1:])

    for i in range(i0 + 1, len(hang)):
        r = hang[i]
        if not any(v not in (None, '') for v in r):
            continue
        sa, ten = _txt(o(r, 'stt')), _doan(o(r, 'ten'))
        ka, kt = bo_dau(sa), bo_dau(ten)
        if any(_la_loi(v) for v in r[:max(cot.values()) + 1]):
            loi_o.append(i + 1)
            continue
        try:
            tt = _so(o(r, 'tt'))
        except ValueError:
            tt = None
        if ka.startswith('tong cong') or kt.startswith('tong cong'):
            h.tong['tong'] = tt
            continue
        if kt.startswith('phuong an tai dinh cu') or kt.startswith('tai dinh cu'):
            h.tai_dinh_cu = _txt(ten.split(':', 1)[1] if ':' in ten else '')
            continue
        if la_ma:
            if re.fullmatch(r'[ivx]+\.?', ka):          # dòng mục: theo tên, không rõ thì theo số La Mã
                muc = muc_theo_ten(ten) or _LA_MA.get(ka.rstrip('.'), 9)
                if muc in _MUC_TONG:
                    h.tong[muc] = tt
                continue
            if re.fullmatch(r'[a-z]\.?', ka):           # nhóm A (phương án bằng tiền) / B…: không phải dòng tiền
                continue
            if muc not in h.khoan and muc != 1 or not ten:
                continue
            la_con = not re.fullmatch(r'\d+(\.\d+)*\.?', ka)
            if la_con and ka not in ('', '-', '+', '*', '.') and not re.fullmatch(r'[a-z]\)', ka):
                continue
        else:
            if re.fullmatch(r'[ivx]+\.?', ka):
                muc = 9                                 # IV, V…: phần sau bảng
                continue
            if re.fullmatch(r'\d+\.?', ka):
                # mục theo tên (bản in 0.9.21: 4 vật nuôi, 5 hỗ trợ, 6 thưởng; bản cũ: 4 hỗ trợ, 5 thưởng); tên lạ: theo số
                so = int(ka.rstrip('.'))
                muc = muc_theo_ten(ten) or (_MUC_THEO_SO.get(so, 9) if MUC_VN in h.tong else so)
                if muc in _MUC_TONG:
                    h.tong[muc] = tt
                continue
            if muc not in h.khoan and muc != 1 or not ten:
                continue
            la_con = not re.fullmatch(r'\d+\.\d+\.?', ka)
            if la_con and ka not in ('', '-', '+', '*', '.') and not re.fullmatch(r'[a-z]\)?', ka):
                continue
        d = DongBang(i + 1, sa, ten, _txt(o(r, 'dvt')), ghi_chu=_doan(o(r, 'gc')), thanh_tien=tt, con=la_con)
        for k, ham in (('so_luong', _so), ('don_gia', _so), ('ty_le', _ty_le)):
            try:
                setattr(d, k, ham(o(r, {'so_luong': 'sl', 'don_gia': 'dg', 'ty_le': 'tl'}[k])))
            except ValueError as e:
                h.canh_bao.append(f'Dòng {i + 1} ({ten[:40]}): {e}, coi như trống.')
        (h.dat if muc == 1 else h.khoan[muc]).append(d)
    if loi_o:
        h.loi.append(f'Ô lỗi công thức (#N/A…) ở dòng {", ".join(map(str, loi_o[:8]))}{"…" if len(loi_o) > 8 else ""}.')
    for m in MUC_KHOAN:
        h.khoan[m] = _gop_dong_con(h.khoan[m])
    if not h.ho_ten:
        h.chon, h.ly_do = False, 'không có họ tên'
    elif h.loi:
        h.chon, h.ly_do = False, 'có ô lỗi công thức'
    elif re.match(r'mau\b', bo_dau(ten_sheet)) or 'kiem tra' in bo_dau(ten_sheet):
        h.chon, h.ly_do = False, 'sheet mẫu / kiểm tra'
    elif not h.dat and not h.so_dong:
        h.chon, h.ly_do = False, 'bảng tính toán trống'
    _kiem_cong(h)
    return h


def _gop_dong_con(ds: list) -> list:
    """Dòng k.n có dòng con ("-") bên dưới: con có số liệu thì thay dòng cha bằng các dòng con (tên "Cha - Con"),
    không thì bỏ dòng con. Dòng con đứng đầu mục (không có cha) giữ như dòng thường."""
    kq, i = [], 0
    while i < len(ds):
        d = ds[i]
        if d.con:
            d.con = False
            kq.append(d)
            i += 1
            continue
        j = i + 1
        while j < len(ds) and ds[j].con:
            j += 1
        con = ds[i + 1:j]
        if any(x.so_luong or x.thanh_tien for x in con):
            for x in con:
                if not bo_dau(x.ten).startswith(bo_dau(d.ten)):
                    x.ten = f'{d.ten} - {x.ten}'
                x.ghi_chu = x.ghi_chu or d.ghi_chu
                x.con = False
                kq.append(x)
        else:
            kq.append(d)
        i = j
    return kq


def _kiem_cong(h: HoChiTiet) -> None:
    """Cộng thành tiền các dòng so với dòng mục: lệch thì cảnh báo (dòng trùng / sót khi đọc)."""
    for m in MUC_KHOAN:
        if h.tong.get(m) is None:
            continue
        cong = sum((d.thanh_tien or KHONG for d in h.khoan[m]), KHONG)
        if cong != h.tong[m]:
            h.canh_bao.append(f'Mục {so_muc(m)}: cộng các dòng {vn(cong)} đ khác dòng mục {vn(h.tong[m])} đ.')


def _thong_tin_du_an(hang: list) -> dict:
    """Tên dự án, đơn vị, ký hiệu số, địa bàn, năm ở đầu trang phương án chi tiết."""
    da = {}
    for i, r in enumerate(hang[:12]):
        for c, v in enumerate(r):
            if v in (None, ''):
                continue
            s = _doan(v)
            k = bo_dau(s)
            dong = s.split('\n')
            if 'phuong an chi tiet' in k:
                for j, x in enumerate(dong):
                    if bo_dau(x).startswith('du an'):
                        da['ten'] = _txt(' '.join(dong[j:]))
                        break
            elif k.startswith('du an') and 'ten' not in da:
                da['ten'] = _txt(s)
            elif k.startswith('so:') or k.startswith('so :'):
                m = re.search(r'/\s*([^\s(]+)', dong[0])
                if m:
                    da['ky_hieu_so'] = m.group(1).strip()
            elif ', ngay' in k and 'nam' in k:
                da['ten_dia_ban'] = _txt(s.split(',')[0])
                m = re.search(r'năm\s+(20\d\d)', s)
                if m:
                    da['nam'] = m.group(1)
            elif c == 0 and i == 0 and 'cong hoa' not in k:
                da['don_vi_cap_tren'] = _txt(s)
            elif c == 0 and i == 1 and 'doc lap' not in k:
                da['don_vi_tieu_de'] = _txt(s)
    if da.get('ten'):
        da['ten'] = re.sub(r'(?i)^dự án\s*:?\s*', '', da['ten']).strip().rstrip('.')
    return da


def _mo(file):
    import openpyxl
    return openpyxl.load_workbook(file, read_only=True, data_only=True)


TRONG_LIEN_TIEP = 200      # đọc tới hết dữ liệu: dừng sau ngần này dòng trống liền nhau (sheet định dạng sẵn tới dòng 1.048.576)


def doc_hang(ws, trong_lien_tiep: int = TRONG_LIEN_TIEP) -> list:
    """Mọi dòng có dữ liệu của sheet (không giới hạn số dòng; trước đây cắt ở dòng 600 - hộ nhiều cây / công trình mất dòng
    cuối và dòng TỔNG CỘNG). Dòng trống ở giữa giữ nguyên; bỏ phần trống cuối sheet."""
    hang, trong = [], 0
    for r in ws.iter_rows(values_only=True):
        r = list(r)
        hang.append(r)
        if any(v is not None and str(v).strip() for v in r):
            trong = 0
        else:
            trong += 1
            if trong >= trong_lien_tiep:
                break
    while hang and not any(v is not None and str(v).strip() for v in hang[-1]):
        hang.pop()
    return hang


def la_file_chi_tiet(file) -> bool:
    """File có ít nhất một sheet phương án chi tiết (bảng STT / Tên tài sản / Số lượng / Thành tiền và dòng Họ và tên)."""
    try:
        wb = _mo(file)
    except Exception:
        return False
    try:
        for ws in wb.worksheets[:40]:
            hang = [list(r) for r in ws.iter_rows(max_row=80, values_only=True)]
            td = _tim_tieu_de(hang)
            if td and any(_bat_dau(bo_dau(_txt(v)).rstrip(':'), NHAN['ho_ten']) for r in hang[:td[0]] for v in r[:3]):
                return True
        return False
    finally:
        wb.close()


def doc(file) -> KetQuaDoc:
    """Đọc mọi sheet phương án chi tiết của file Excel (chỉ đọc, không sửa file)."""
    kq = KetQuaDoc(str(file))
    wb = _mo(file)
    try:
        for ws in wb.worksheets:
            hang = doc_hang(ws)
            h = doc_sheet(ws.title, hang)
            if h is None:
                kq.bo_qua.append(ws.title)
                continue
            kq.ho.append(h)
            if h.chon and not kq.du_an:
                kq.du_an = _thong_tin_du_an(hang)
    finally:
        wb.close()
    # trùng hộ trong file (cùng CCCD hoặc cùng họ tên): cảnh báo
    gap = {}
    for h in kq.ho:
        if not h.chon:
            continue
        k = h.so_cccd or bo_dau(h.ten_ngan)
        if k in gap:
            h.canh_bao.append(f'Trùng hộ ở sheet "{gap[k]}" ({"cùng CCCD" if h.so_cccd else "cùng họ tên"}).')
        gap.setdefault(k, h.sheet)
    if kq.du_an and not kq.du_an.get('cap_dia_ban') and kq.du_an.get('ten_dia_ban'):
        tdb = bo_dau(kq.du_an['ten_dia_ban'])
        for h in kq.ho:
            m = re.search(r'\b(xa|phuong|thi tran|dac khu) ' + re.escape(tdb), bo_dau(h.dia_chi + ' ' + h.nguon_goc))
            if m:
                kq.du_an['cap_dia_ban'] = {'xa': 'Xã', 'phuong': 'Phường', 'thi tran': 'Thị trấn', 'dac khu': 'Đặc khu'}[m.group(1)]
                break
    return kq


# ---------------------------------------------------------------- ghi vào dự án
def _khoa_ten(ho_ten) -> str:
    return bo_dau(re.split(r'\s+là\s+', ho_ten or '', maxsplit=1)[0].strip(' ,.'))


class ChiMucTrung:
    """Như ho_trung nhưng dựng chỉ mục CCCD / họ tên MỘT lần (ho_trung quét cả bảng hộ cho mỗi hộ nhập: 3.000 hộ có sẵn x 3.000 hộ
    nhập = 9 triệu lần so tên). Cùng kết quả: hộ đứng trước (mã nhỏ hơn) thắng; ghi_nhan sau mỗi hộ thêm / thay để hộ vừa ghi
    trong cùng lần nhập cũng được nhận ra (như truy vấn lại CSDL)."""

    def __init__(self, con):
        self.cccd, self.ten, self.khoa = {}, {}, {}
        for r in con.execute('SELECT ma_ho, ho_ten, so_cccd FROM ho ORDER BY ma_ho'):
            self.ghi_nhan(r['ma_ho'], r['ho_ten'], r['so_cccd'])

    def ghi_nhan(self, ma, ho_ten, so_cccd) -> None:
        for bang, k in self.khoa.pop(ma, ()):
            ds = bang.get(k, [])
            if ma in ds:
                ds.remove(ma)
        khoa = [(b, k) for b, k in ((self.cccd, str(so_cccd or '').replace(' ', '')), (self.ten, _khoa_ten(ho_ten))) if k]
        for bang, k in khoa:                            # khóa rỗng (không CCCD / tên): tim() không tra, không gom vào một danh sách dài
            insort(bang.setdefault(k, []), ma)
        self.khoa[ma] = khoa

    def tim(self, h: HoChiTiet):
        ds = self.cccd.get(h.so_cccd) if h.so_cccd else self.ten.get(bo_dau(h.ten_ngan))
        return ds[0] if ds else None


def ho_trung(con, h: HoChiTiet):
    """Mã hộ đã có trong dự án trùng với hộ của file (cùng CCCD; không có CCCD thì cùng họ tên), hoặc None.
    Nhiều hộ: dùng ChiMucTrung."""
    if h.so_cccd:
        r = con.execute("SELECT ma_ho FROM ho WHERE REPLACE(so_cccd, ' ', '') = ?", (h.so_cccd,)).fetchone()
        if r:
            return r[0]
        return None
    ten = bo_dau(h.ten_ngan)
    for r in con.execute('SELECT ma_ho, ho_ten, so_cccd FROM ho'):
        if bo_dau(re.split(r'\s+là\s+', r['ho_ten'] or '', maxsplit=1)[0].strip(' ,.')) == ten:
            return r['ma_ho']
    return None


class _KhopDanhMuc:
    """Tìm mục danh mục cùng tên (không dấu, giữ dấu câu; rồi bỏ dấu chấm cuối) cho dòng mục 2, 3."""

    def __init__(self, con):
        self.dm = DanhMuc(con)
        self.ten, self.gon = {}, {}
        for nhom in (2, 3, MUC_VN):
            for m in self.dm.muc[nhom]:
                self.ten.setdefault((nhom, bo_dau(m.ten)), []).append(m)
                self.gon.setdefault((nhom, self._gon(m.ten)), []).append(m)

    @staticmethod
    def _gon(s) -> str:
        return re.sub(r'\s*([,.;:()\-])\s*', r'\1', bo_dau(s)).strip(' .')

    def tim(self, muc: int, ten: str, don_gia) -> tuple:
        """(mục khớp cả tên lẫn giá, mục cùng tên khác giá). File chưa có đơn giá: tên khớp các mục cùng một giá -> mục đó."""
        ds = self.ten.get((muc, bo_dau(ten))) or self.gon.get((muc, self._gon(ten))) or []
        if don_gia is None:
            gia = {m.don_gia for m in ds}
            return (ds[0] if len(gia) == 1 and None not in gia else None), None
        dung = next((m for m in ds if m.don_gia is not None and m.don_gia == don_gia), None)
        return dung, (ds[0] if ds and dung is None else None)


def _dong_khoan(muc: int, d: DongBang, khop: _KhopDanhMuc, nguon: str) -> tuple:
    """DongBang -> (DongKhoan, cảnh báo)."""
    dg = d.don_gia if d.don_gia is not None else KHONG
    k = DongKhoan(muc=muc, ten=d.ten, dvt=d.dvt, so_luong=d.so_luong or KHONG, don_gia=dg,
                  ty_le=d.ty_le if d.ty_le is not None else D(1), ghi_chu=d.ghi_chu, nguon_gia=NGUON_TAY,
                  thanh_tien_excel=d.thanh_tien)
    cb = ''
    if muc in (2, 3, MUC_VN):
        dung, gan = khop.tim(muc, d.ten, d.don_gia)
        if dung is not None:
            k.ma, k.nguon_gia = dung.ma, NGUON_DM
            if d.don_gia is None:
                k.don_gia = dung.don_gia
                return k, (f'{muc}.x "{d.ten[:50]}": file chưa có đơn giá, lấy theo bộ đơn giá {dung.ma} '
                           f'{vn(dung.don_gia)} đ/{dung.dvt}' + (', tỷ lệ trống tính 100%' if d.ty_le is None else '') + '.')
        elif gan is not None:
            k.ma_tuong_duong = gan.ma
            k.can_cu_gia = (f'Đơn giá nhập tay (đơn giá {gan.ma}: '
                            f'{vn(gan.don_gia) if gan.don_gia is not None else "chưa có"} đ/{gan.dvt}); theo {nguon}')
        else:
            k.can_cu_gia = f'Đơn giá theo {nguon}'
    else:
        k.can_cu_gia = f'Theo {nguon}'
    if d.don_gia is None and (d.thanh_tien or (muc in (2, 3, MUC_VN) and d.so_luong)):
        cb = f'{muc}.x "{d.ten[:50]}": chưa có đơn giá trong file.'
    return k, cb


BAO_MOI = 10                    # ghi vào dự án đang mở: báo tiến độ (hộp tiến trình) sau mỗi chừng này hộ


class DaDung(LoiNhap):
    """Người dùng bấm Dừng khi đang ghi: cả lô được hoàn tác (không hộ nào được ghi)."""


def ghi(con, ds_ho: list, trung: str = 'bo_qua', nguon: str = 'file Excel', du_an: dict | None = None,
        bao_tien_do=None) -> BaoCaoNhap:
    """Ghi các hộ (HoChiTiet có chon = True) vào dự án, một giao dịch (một bước Hoàn tác).
    bao_tien_do(i, n) -> True để dừng: gọi mỗi BAO_MOI hộ (hộp tiến trình vẽ lại, không "Không phản hồi"); dừng -> DaDung, hoàn
    tác cả lô.
    trung: 'bo_qua' (hộ đã có trong dự án - cùng CCCD / họ tên - thì bỏ qua), 'thay' (thay hồ sơ, thửa, phương án của hộ đó;
    giữ mã hộ, đợt trình, quyết định), 'them' (vẫn thêm thành hộ mới). du_an: điền các ô thông tin dự án còn trống."""
    if trung not in ('bo_qua', 'thay', 'them'):
        raise ValueError(trung)
    bc = BaoCaoNhap()
    khop = _KhopDanhMuc(con)
    ctx = BoiCanh.tu(con)
    n_ho = len(ds_ho)
    with csdl.giao_dich(con):
        if du_an:
            cu = con.execute('SELECT * FROM du_an WHERE id = 1').fetchone()
            for k, v in du_an.items():
                if k in cu.keys() and v and not str(cu[k] or '').strip():
                    con.execute(f'UPDATE du_an SET {k} = ? WHERE id = 1', (int(v) if k == 'nam' else v,))
            if not str(cu['nguon_nhap'] or '').strip():
                con.execute("UPDATE du_an SET nguon_nhap = ?, ngay_nhap = datetime('now', 'localtime') WHERE id = 1",
                            (f'Phương án chi tiết: {nguon}',))
        chi_muc = ChiMucTrung(con) if trung != 'them' else None
        tiep = None                                     # mã / thứ tự hộ mới kế tiếp: đọc MAX một lần (thu_tu không có chỉ mục)
        for i_ho, h in enumerate(ds_ho):
            if bao_tien_do is not None and i_ho % BAO_MOI == 0 and bao_tien_do(i_ho, n_ho):
                raise DaDung('Đã dừng: không hộ nào được ghi (dữ liệu dự án giữ nguyên như trước khi nhập).')
            if not h.chon or not h.ho_ten:
                bc.bo_qua.append((h.sheet, h.ly_do or ('không có họ tên' if not h.ho_ten else 'không chọn')))
                continue
            ma = chi_muc.tim(h) if chi_muc is not None else None
            if ma is not None and trung == 'bo_qua':
                bc.bo_qua.append((h.sheet, f'trùng hộ {ma} đã có trong dự án'))
                continue
            ten_ho = f'Sheet "{h.sheet}" ({h.ten_ngan})'
            dat_tinh = any((d.don_gia or KHONG) > 0 or (d.thanh_tien or KHONG) > 0 for d in h.dat)
            ghi_chu_dat = '; '.join(dict.fromkeys(d.ghi_chu for d in h.dat if d.ghi_chu))
            tdc = '' if re.match(r'sau khi ubnd', bo_dau(h.tai_dinh_cu)) else h.tai_dinh_cu
            tt = dict(ho_ten=h.ho_ten, so_cccd=h.so_cccd, ngay_cap=h.ngay_cap, noi_cap=h.noi_cap, dia_chi=h.dia_chi,
                      dien_thoai=h.dien_thoai, phap_ly='' if dat_tinh else ghi_chu_dat, tai_dinh_cu=tdc, trang_thai=TRANG_THAI)
            if ma is None:
                if tiep is None:
                    tiep = tuple(con.execute('SELECT COALESCE(MAX(ma_ho), 0) + 1, COALESCE(MAX(thu_tu), 0) + 1 FROM ho').fetchone())
                ma, thu_tu = tiep
                tiep = (ma + 1, thu_tu + 1)
                con.execute(f'INSERT INTO ho (ma_ho, thu_tu, {", ".join(tt)}) VALUES (?, ?, {", ".join("?" * len(tt))})',
                            (ma, thu_tu, *tt.values()))
                bc.them.append((ma, h.ten_ngan))
                if chi_muc is not None:
                    chi_muc.ghi_nhan(ma, tt['ho_ten'], tt['so_cccd'])
            else:
                con.execute(f'UPDATE ho SET {", ".join(k + " = ?" for k in tt)}, luu_luc = NULL WHERE ma_ho = ?',
                            (*tt.values(), ma))
                for bang in ('ct_dat', 'ct_khoan', 'thua'):
                    con.execute(f'DELETE FROM {bang} WHERE ma_ho = ?', (ma,))
                bc.thay.append((ma, h.ten_ngan))
                if chi_muc is not None:
                    chi_muc.ghi_nhan(ma, tt['ho_ten'], tt['so_cccd'])
            # thửa (mỗi dòng mục 1 một thửa) + mục 1 khi có tính tiền đất
            for k, d in enumerate(h.dat, start=1):
                t = _thua_tu_ten(d.ten)
                if not (t['so_thua'] or t['so_to']):
                    bc.canh_bao.append(f'{ten_ho}: dòng 1.{k} "{d.ten[:50]}" không đọc được số tờ, số thửa.')
                if t['loai_dat'] and t['loai_dat'].split('+')[0] not in ctx.loai_dat:
                    bc.canh_bao.append(f'{ten_ho}: thửa {t["so_thua"]} loại đất {t["loai_dat"]} không có trong danh mục loại đất.')
                mt = con.execute('SELECT COALESCE(MAX(ma_thua), 0) + 1 FROM thua').fetchone()[0]
                con.execute('''INSERT INTO thua (ma_thua, ma_ho, so_to, so_thua, loai_dat, dt_thu_hoi, nguon_goc, vi_tri, thu_tu)
                               VALUES (?,?,?,?,?,?,?,?,?)''',
                            (mt, ma, t['so_to'], t['so_thua'], t['loai_dat'], chuoi(d.so_luong or KHONG), h.nguon_goc,
                             t['vi_tri'], k))
                bc.so_thua += 1
                if dat_tinh:
                    ld = t['loai_dat'].split('+')[0] if t['loai_dat'] else ''
                    dd = DongDat(ma_thua=mt, loai_dat=ld, nhom_dat=ctx.loai_dat.get(ld, ''), dien_tich=d.so_luong or KHONG,
                                 vi_tri=t['vi_tri'], gia_bang_gia=d.don_gia or KHONG,
                                 ty_le=d.ty_le if d.ty_le is not None else D(1), ghi_chu=d.ghi_chu, thanh_tien_excel=d.thanh_tien)
                    if not ld:
                        bc.canh_bao.append(f'{ten_ho}: dòng 1.{k} chưa có loại đất (chọn loại đất khi mở lập phương án).')
                    _so_sanh(bc, ten_ho, f'1.{k}', thanh_tien_dong_dat(dd, ctx), d.thanh_tien)
                    con.execute('''INSERT INTO ct_dat (ma_ho, ma_thua, thu_tu, loai_dat, nhom_dat, dien_tich, vi_tri, gia_bang_gia,
                                   he_so_k, ty_le, ghi_chu, thanh_tien_excel) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)''',
                                (ma, mt, k, dd.loai_dat, dd.nhom_dat, chuoi(dd.dien_tich), dd.vi_tri, chuoi(dd.gia_bang_gia),
                                 '1', chuoi(dd.ty_le), dd.ghi_chu, _chuoi(d.thanh_tien)))
                    bc.so_dong += 1
            for muc in MUC_KHOAN:
                sm = so_muc(muc)
                for k, d in enumerate(h.khoan[muc], start=1):
                    dk, cb = _dong_khoan(muc, d, khop, f'{nguon}, sheet "{h.sheet}"')
                    if cb:
                        bc.canh_bao.append(f'{ten_ho}: {cb.replace(f"{muc}.x", f"{sm}.{k}")}')
                    _so_sanh(bc, ten_ho, f'{sm}.{k}', thanh_tien_dong(dk, ctx), d.thanh_tien)
                    con.execute('''INSERT INTO ct_khoan (muc, ma_ho, thu_tu, ma, ten, dvt, so_luong, don_gia, ty_le, quy_cach,
                                   ghi_chu, nguon_gia, ma_tuong_duong, can_cu_gia, thanh_tien_excel)
                                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',
                                (muc, ma, k, dk.ma, dk.ten, dk.dvt, chuoi(dk.so_luong), chuoi(dk.don_gia), chuoi(dk.ty_le),
                                 dk.quy_cach, dk.ghi_chu, dk.nguon_gia, dk.ma_tuong_duong, dk.can_cu_gia, _chuoi(d.thanh_tien)))
                    bc.so_dong += 1
            g = dict(h.tong)
            if g.get(MUC_VN) is not None:                   # tong_excel 5 cột: cây trồng gồm cả vật nuôi
                g[3] = (g.get(3) or KHONG) + g[MUC_VN]
            con.execute('INSERT OR REPLACE INTO tong_excel VALUES (?,?,?,?,?,?,?)',
                        (ma, *(_chuoi(g.get(m) if g.get(m) is not None else (KHONG if g.get('tong') is not None else None))
                               for m in (1, 2, 3, 4, 5)), _chuoi(g.get('tong'))))
            bc.canh_bao += [f'{ten_ho}: {x}' for x in h.canh_bao]
        csdl.ghi_nhat_ky(con, 'Nhập phương án chi tiết từ Excel',
                         f'{nguon}: thêm {len(bc.them)} hộ, thay {len(bc.thay)} hộ, {bc.so_thua} thửa, {bc.so_dong} dòng')
    return bc


def _chuoi(x):
    return chuoi(x) if x is not None else None


def _so_sanh(bc: BaoCaoNhap, ten_ho: str, stt: str, tinh, excel) -> None:
    if excel is not None and tinh != excel:
        bc.canh_bao.append(f'{ten_ho}: dòng {stt} phần mềm tính {vn(tinh)} đ, file ghi {vn(excel)} đ.')


def ghi_file(kq: KetQuaDoc, file_pabt, trung: str = 'bo_qua') -> BaoCaoNhap:
    """Ghi các hộ đã chọn của kq vào file dự án; file chưa có thì tạo mới (bộ đơn giá tích hợp, thông tin dự án đọc từ file)."""
    from . import don_gia, lap_pa
    if not any(h.chon and h.ho_ten for h in kq.ho):
        raise LoiNhap('Không có sheet phương án chi tiết nào để nhập '
                      '(cần bảng STT / Tên tài sản / Số lượng / Thành tiền và dòng "Họ và tên").')
    p = Path(file_pabt)
    tam = None
    if p.exists():
        con = csdl.mo(p)
    else:                                               # file mới: dựng ở file tạm, xong mới đặt tên (nguyên tử)
        con, tam = csdl.tao_moi_tam(p)
    xong = False
    try:
        if tam is not None:
            don_gia.ap_vao_du_an(con)
            da = dict(kq.du_an)
            lap_pa.luu_du_an(con, dict(da, ten=da.get('ten') or Path(kq.file).stem, ten_day_du=da.get('ten') or '',
                                       cap_dia_ban=da.get('cap_dia_ban') or 'Phường'))
        bc = ghi(con, kq.ho, trung, Path(kq.file).name, kq.du_an)
        xong = True
    finally:
        con.close()
        if tam is not None and not xong:
            csdl.huy_tao_moi(tam)
    if tam is not None:
        csdl.hoan_tat_tao_moi(tam, p)
    return bc


def nhap(file_excel, file_pabt, trung: str = 'bo_qua', ten_sheet: list | None = None) -> BaoCaoNhap:
    """Đọc file Excel rồi ghi vào file dự án (chưa có thì tạo mới). ten_sheet: chỉ nhập các sheet này."""
    kq = doc(file_excel)
    if ten_sheet is not None:
        chon = set(ten_sheet)
        for h in kq.ho:
            h.chon = h.sheet in chon and not h.loi
    return ghi_file(kq, file_pabt, trung)


def ket_qua(bc: BaoCaoNhap) -> tuple:
    """(tóm tắt ngắn, [mọi điểm cần xem lại]) cho hộp kết quả có ô cuộn (giao_dien.hop_ket_qua)."""
    t = [f'Đã nhập {bc.so_ho} hộ ({len(bc.them)} hộ mới' + (f', thay {len(bc.thay)} hộ đã có' if bc.thay else '') +
         f'), {bc.so_thua} thửa, {bc.so_dong} dòng phương án.']
    if bc.bo_qua:
        t.append('Không nhập: ' + '; '.join(f'sheet "{s}" ({ly_do})' for s, ly_do in bc.bo_qua[:15]) +
                 ('…' if len(bc.bo_qua) > 15 else '') + '.')
    t.append('So tổng tiền phần mềm tính với file: lệnh "Lập phương án → Đối chiếu file Excel".')
    return '\n\n'.join(t), list(bc.canh_bao)


def tom_tat(bc: BaoCaoNhap, toi_da: int = 15) -> str:
    """Báo cáo sau khi nhập (hiện cho người dùng)."""
    t = [f'Đã nhập {bc.so_ho} hộ ({len(bc.them)} hộ mới' + (f', thay {len(bc.thay)} hộ đã có' if bc.thay else '') +
         f'), {bc.so_thua} thửa, {bc.so_dong} dòng phương án.']
    if bc.bo_qua:
        t.append('Không nhập: ' + '; '.join(f'sheet "{s}" ({ly_do})' for s, ly_do in bc.bo_qua[:toi_da]) +
                 ('…' if len(bc.bo_qua) > toi_da else '') + '.')
    if bc.canh_bao:
        t.append(f'Cần xem lại ({len(bc.canh_bao)}):\n' + '\n'.join('- ' + x for x in bc.canh_bao[:toi_da]) +
                 (f'\n- … và {len(bc.canh_bao) - toi_da} điểm khác' if len(bc.canh_bao) > toi_da else ''))
    t.append('So tổng tiền phần mềm tính với file: lệnh "Lập phương án → Đối chiếu file Excel".')
    return '\n\n'.join(t)


def mo_ta(h: HoChiTiet) -> str:
    """Một dòng tóm tắt hộ để xem trước."""
    dt = sum((d.so_luong or KHONG for d in h.dat), KHONG)
    return (f'{len(h.dat)} thửa ({so_vn(dt)} m²), {len(h.khoan[2])} dòng nhà/công trình, {len(h.khoan[3])} dòng cây trồng, '
            f'{len(h.khoan[4])} dòng hỗ trợ')

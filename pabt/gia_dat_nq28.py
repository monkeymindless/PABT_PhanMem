"""Bảng giá đất theo Nghị quyết 28/2025/NQ-HĐND của HĐND tỉnh Đồng Nai (áp dụng từ 01/01/2026) - trích các địa bàn
Xã Trị An, Xã Tân An, Xã Phú Lý, Phường Tân Triều; đất phi nông nghiệp (Phụ lục III) và nông nghiệp (Phụ lục I).

Dữ liệu (pabt/bang_gia_nq28.json): mỗi đoạn đường 7 dòng - mặt tiền (MT); T1-T3: đường đấu nối trực tiếp ra đường;
K1-K3: đường không đấu nối trực tiếp và thông ra đường. Giá lưu theo nghìn đồng/m² như văn bản; hàm trả đồng/m².
Chép từ bản PDF đóng dấu của Nghị quyết, kiểm tra chéo bằng nhận dạng chữ; khi dùng chính thức cần đối chiếu văn bản gốc.
"""
from __future__ import annotations
import json
import re
from functools import lru_cache
from pathlib import Path

from . import an_toan as _an_toan
from .tien import lam_tron
from .lap_pa import bo_dau

VAN_BAN = 'Nghị quyết 28/2025/NQ-HĐND ngày 10/12/2025 của HĐND tỉnh Đồng Nai (bảng giá đất áp dụng từ 01/01/2026)'
COT = [('dat_o', 'Đất ở'), ('tmdv', 'Đất thương mại, dịch vụ'), ('sxkd', 'Đất SX-KD phi NN, khoáng sản'),
       ('nn_cay', 'Đất trồng cây lâu năm, cây hằng năm'), ('nn_rung_nts', 'Đất rừng sản xuất, nuôi trồng thủy sản')]
TEN_VT = {'MT': 'Mặt tiền đường', 'T1': 'Đường đấu nối trực tiếp - mức 1', 'T2': 'Đường đấu nối trực tiếp - mức 2',
          'T3': 'Đường đấu nối trực tiếp - mức 3', 'K1': 'Đường không đấu nối trực tiếp - mức 1',
          'K2': 'Đường không đấu nối trực tiếp - mức 2', 'K3': 'Đường không đấu nối trực tiếp - mức 3',
          'VT1': 'Vị trí 1', 'VT2': 'Vị trí 2', 'VT3': 'Vị trí 3', 'VT4': 'Vị trí 4',
          'KV1': 'Khu vực 1', 'KV2': 'Khu vực 2', 'KV3': 'Khu vực 3'}
# Mô hình mã vị trí của bảng giá đất từng địa phương (hồ sơ địa phương bang_gia_dat.mo_hinh_vi_tri): Đồng Nai NQ 28/2025 (mặt tiền /
# đấu nối trực tiếp / không đấu nối, 7 mức), vị trí 1-4 theo tuyến đường (phần lớn các tỉnh), khu vực x vị trí (nông thôn theo khu vực)
MO_HINH_VI_TRI = {
    'DONG_NAI_NQ28': ('MT', 'T1', 'T2', 'T3', 'K1', 'K2', 'K3'),
    'VI_TRI_1_4': ('VT1', 'VT2', 'VT3', 'VT4'),
    'KHU_VUC_VI_TRI': tuple(f'KV{k}-VT{v}' for k in (1, 2, 3) for v in (1, 2, 3, 4)),
}
MO_HINH_MAC_DINH = 'DONG_NAI_NQ28'


def mo_hinh_vi_tri() -> str:
    """Mô hình vị trí bảng giá đất của địa phương (khóa của MO_HINH_VI_TRI); hồ sơ chưa ghi / ghi sai -> DONG_NAI_NQ28."""
    from . import dia_phuong
    mh = str(dia_phuong.lay('bang_gia_dat.mo_hinh_vi_tri', MO_HINH_MAC_DINH) or MO_HINH_MAC_DINH).strip().upper()
    return mh if mh in MO_HINH_VI_TRI else MO_HINH_MAC_DINH


def ds_ma_vi_tri(mo_hinh: str | None = None) -> tuple:
    """Các mã vị trí chuẩn theo mô hình (None: mô hình của hồ sơ địa phương đang dùng)."""
    mh = (mo_hinh or mo_hinh_vi_tri()).strip().upper()
    return MO_HINH_VI_TRI.get(mh, MO_HINH_VI_TRI[MO_HINH_MAC_DINH])


def la_mo_hinh_mac_dinh() -> bool:
    """Hồ sơ địa phương dùng mô hình Đồng Nai NQ 28 (7 mức) - mọi màn hình giữ nguyên như trước 1.0.29."""
    return mo_hinh_vi_tri() == MO_HINH_MAC_DINH


def ten_vi_tri(ma: str) -> str:
    """Tên đọc được của mã vị trí ('T1' -> 'Đường đấu nối trực tiếp - mức 1', 'KV2-VT3' -> 'Khu vực 2, Vị trí 3'); mã lạ: giữ nguyên."""
    ma = str(ma or '').strip().upper()
    if ma in TEN_VT:
        return TEN_VT[ma]
    phan = ma.split('-')
    return ', '.join(TEN_VT[x] for x in phan) if len(phan) > 1 and all(x in TEN_VT for x in phan) else ma
# mã loại đất -> cột giá
COT_LOAI = {'ONT': 'dat_o', 'ODT': 'dat_o', 'TMD': 'tmdv', 'SKC': 'sxkd', 'SKS': 'sxkd', 'SKN': 'sxkd',
            'CLN': 'nn_cay', 'HNK': 'nn_cay', 'BHK': 'nn_cay', 'LUC': 'nn_cay', 'LUK': 'nn_cay', 'LUA': 'nn_cay', 'CHN': 'nn_cay',
            'NHK': 'nn_cay', 'RSX': 'nn_rung_nts', 'NTS': 'nn_rung_nts'}


def _file() -> Path:
    from . import tai_nguyen
    return tai_nguyen('bang_gia_nq28.json')


TEN_FILE_THAY = 'bang_gia_dat.json'    # bảng người dùng thay (một hoặc nhiều xã / tỉnh), trong thư mục máy


class LoiBangGia(ValueError):
    """File bảng giá không đọc được."""


def file_thay() -> Path:
    """File bảng giá đất người dùng đã thay trên máy này (PABT_THU_MUC_MAY / %APPDATA%\\PABT)."""
    from .may_chu import thu_muc_may
    return thu_muc_may() / TEN_FILE_THAY


def _nguon() -> tuple:
    """(đường file đang dùng, đã thay bảng gắn sẵn?)."""
    p = file_thay()
    if p.is_file():
        return p, True
    return _file(), False


@lru_cache(maxsize=4)
def _doc(duong: str, mtime: int) -> tuple:
    try:
        data = json.loads(Path(duong).read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return (), ''
    if isinstance(data, dict):
        return tuple(data.get('dong') or ()), str(data.get('van_ban') or '')
    if isinstance(data, list):
        return tuple(data), ''
    return (), ''


NHO_GIAY = 2.0              # kiểm lại file bảng giá (stat 2-3 file) tối đa mỗi chừng này giây - như he_so_k (1.0.31)
_NHO_DOC = {'t': -1e9, 'khoa': None, 'gt': None}


def _quen() -> None:
    """Bỏ bộ nhớ: lần đọc sau kiểm lại file (gọi sau khi ghi / xóa bảng thay)."""
    _NHO_DOC['t'] = -1e9


def _da_doc() -> tuple:
    """(dòng, văn bản, đã thay?) của bảng đang dùng. Nhớ NHO_GIAY giây theo thư mục máy (trước: mỗi lần tat_ca / tim / theo_dia_ban
    stat 2-3 file)."""
    import os
    import time
    khoa = os.environ.get('PABT_THU_MUC_MAY', '')
    bay_gio = time.monotonic()
    if _NHO_DOC['khoa'] == khoa and bay_gio - _NHO_DOC['t'] < NHO_GIAY:
        return _NHO_DOC['gt']
    p, thay = _nguon()
    try:
        m = p.stat().st_mtime_ns
    except OSError:
        gt = ((), '', False)
    else:
        dong, vb = _doc(str(p), m)
        gt = (dong, vb, thay)
    _NHO_DOC.update(t=bay_gio, khoa=khoa, gt=gt)
    return gt


def tat_ca() -> list:
    return list(_da_doc()[0])


def dang_thay() -> bool:
    """True: máy này đang dùng bảng giá người dùng nhập, không còn 4 địa bàn gắn sẵn."""
    return _da_doc()[2]


def van_ban_dang_dung() -> str:
    if dang_thay():
        return _da_doc()[1] or 'Bảng giá đất'
    return VAN_BAN


def tom_tat() -> str:
    xs = ds_xa()
    if dang_thay():
        gan = xa_gan_san()
        if gan and all(x in xs for x in gan):
            return f'Bảng giá đang dùng (gắn sẵn + bổ sung): {", ".join(xs)} — {len(tat_ca())} dòng'
        return f'Bảng giá đang dùng (đã thay bảng gắn sẵn): {", ".join(xs)} — {len(tat_ca())} dòng'
    return 'Bảng gắn sẵn: ' + ', '.join(xs)


def ds_xa() -> list:
    return list(dict.fromkeys(r['xa'] for r in tat_ca()))


def mo_ta_vi_tri(r: dict) -> str:
    """Điều kiện của dòng (bề rộng, khoảng cách tới đường giao thông) theo văn bản."""
    vt = r.get('vi_tri') or ''
    if r.get('dieu_kien'):
        return str(r['dieu_kien'])
    if r.get('tinh_tu'):                                   # vị trí dựng theo hướng dẫn trong lời văn (quy_tac_vi_tri)
        return f'{ten_vi_tri(vt)}: {r["tinh_tu"]}'
    if vt == 'MT':
        return f'Mặt tiền {r["ten_duong"]}'
    if len(vt) == 2 and vt[0] in 'TK' and vt[1] in '123':
        a, b = (r.get('nguong') or [1000, 500])[:2]
        loai = 'đấu nối trực tiếp ra' if vt[0] == 'T' else 'không đấu nối trực tiếp và thông ra'
        dk = {'1': f'rộng ≥5m cách đường ≤{a:,}m; rộng 3-<5m cách ≤{b:,}m',
              '2': f'rộng ≥5m cách >{a:,}m; rộng 3-<5m cách >{b:,}m đến ≤{a:,}m; rộng <3m cách ≤200m',
              '3': f'rộng 3-<5m cách >{a:,}m; rộng <3m cách >200m'}[vt[1]]
        return f'Đường nhựa, BTXM {loai} {r["ten_duong"]}: {dk}'.replace(',', '.')
    return vt or r.get('ten_duong') or ''


def cot_cua_loai(loai_dat: str) -> str | None:
    for p in re.split(r'[+,;/ ]+', (loai_dat or '').upper()):
        if p in COT_LOAI:
            return COT_LOAI[p]
    return None


def khop_xa(ten: str, r_xa: str) -> bool:
    t = bo_dau(ten or '')
    t = re.sub(r'^(xa|phuong|thi tran)\s+', '', t)
    return bool(t) and t in bo_dau(r_xa)


def tim(xa: str = '', tu_khoa: str = '', vi_tri: str = '') -> list:
    """Lọc theo địa bàn (bỏ qua nếu không khớp địa bàn nào), mã vị trí (vi_tri: 'VT2', 'KV1-VT3'… - '' = mọi vị trí) và từ khóa
    không dấu (tên đường, điểm đầu / cuối, mã vị trí)."""
    ds = tat_ca()
    theo_xa = [r for r in ds if khop_xa(xa, r['xa'])]
    if theo_xa:
        ds = theo_xa
    if vi_tri:
        vt = str(vi_tri).strip().upper()
        ds = [r for r in ds if str(r.get('vi_tri') or '').upper() == vt]
    k = bo_dau(tu_khoa).split()
    if k:
        kq = []
        for r in ds:
            chu_tim = bo_dau(' '.join((r['ten_duong'], r['diem_dau'], r['diem_cuoi'], r['vi_tri'])))   # một lần mỗi dòng
            if all(x in chu_tim for x in k):
                kq.append(r)
        ds = kq
    return ds


def theo_dia_ban(xa: str = '') -> list:
    """Mọi dòng của bảng (đủ các địa bàn - dự án có thể đi qua nhiều xã, phường), địa bàn của dự án đứng đầu."""
    ds = tat_ca()
    return [r for r in ds if khop_xa(xa, r['xa'])] + [r for r in ds if not khop_xa(xa, r['xa'])]


def ten_ngan_xa(r_xa: str) -> str:
    """"Xã Trị An" -> "Trị An"."""
    return re.sub(r'^(Xã|Phường|Thị trấn)\s+', '', r_xa or '')


def gia_dong(r: dict, cot: str) -> int:
    """Giá đồng/m² của một dòng theo cột (văn bản ghi nghìn đồng)."""
    return int(r[cot]) * 1000


def can_cu(r: dict, cot: str) -> str:
    vb = (r.get('van_ban') or van_ban_dang_dung()) if dang_thay() else 'NQ 28/2025/NQ-HĐND'
    ten_vt = ten_vi_tri(r['vi_tri'])
    return (f'{vb}: {r["xa"]}, {r["ten_duong"]} (từ {r["diem_dau"]} đến {r["diem_cuoi"]}), '
            f'{ten_vt}, TT {r["tt"]}, {dict(COT)[cot]}' + (f' ({r["tinh_tu"]})' if r.get('tinh_tu') else ''))


def xuat_excel(file_ra) -> Path:
    """Xuất bảng giá ra Excel: mỗi địa bàn một sheet, giá đồng/m²."""
    import openpyxl
    from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
    wb = openpyxl.Workbook()
    wb.remove(wb.active)
    ke = Side(style='thin', color='999999')
    for xa in ds_xa():
        ws = wb.create_sheet(re.sub(r'[\\/*?:\[\]]', '', xa)[:31])
        ws['A1'] = f'BẢNG GIÁ ĐẤT - {xa.upper()}'
        ws['A1'].font = Font(bold=True, size=13, color='1F4E79')
        ws['A2'] = VAN_BAN + '. Đơn vị: đồng/m².'
        ws['A2'].font = Font(italic=True)
        tieu_de = ['TT', 'Tên đường', 'Điểm đầu', 'Điểm cuối', 'Vị trí', 'Điều kiện vị trí'] + [t for _, t in COT] + ['Trang PL III / PL I']
        ws.append([])
        ws.append(tieu_de)
        for c in ws[4]:
            c.font = Font(bold=True, color='FFFFFF')
            c.fill = PatternFill('solid', fgColor='1F4E79')
            c.alignment = Alignment(wrap_text=True, vertical='center', horizontal='center')
            c.border = Border(left=ke, right=ke, top=ke, bottom=ke)
        for r in [r for r in tat_ca() if r['xa'] == xa]:
            ws.append([r['tt'], r['ten_duong'], r['diem_dau'], r['diem_cuoi'], r['vi_tri'], mo_ta_vi_tri(r)]
                      + [gia_dong(r, k) for k, _ in COT] + [f'{r["trang"]["pl3"]} / {r["trang"]["pl1"]}'])
            dong = ws.max_row
            for c in ws[dong]:
                c.border = Border(left=ke, right=ke, top=ke, bottom=ke)
                c.alignment = Alignment(wrap_text=True, vertical='top')
            for c in ws[dong][6:11]:
                c.number_format = '#,##0'
            if r['vi_tri'] == 'MT':
                for c in ws[dong]:
                    c.font = Font(bold=True)
                    c.fill = PatternFill('solid', fgColor='DDEBF7')
        for col, w in zip('ABCDEFGHIJKL', (6, 26, 26, 30, 7, 48, 12, 12, 12, 13, 13, 14)):
            ws.column_dimensions[col].width = w
        ws.freeze_panes = 'C5'
    file_ra = Path(file_ra)
    _an_toan.luu_xlsx(wb, file_ra)
    return file_ra


def _chuan_vi_tri(chu: str) -> str:
    t = bo_dau(chu or '').strip()
    if t in ('mt', 'mat tien', 'mat tien duong', 'm'):
        return 'MT'
    m = re.fullmatch(r'(?:kv|khu vuc)\s*([1-3])\s*[-,;/ ]*\s*(?:vt|vi tri)\s*([1-5])', t)      # mô hình khu vực - vị trí (1.0.29)
    if m:
        return f'KV{m.group(1)}-VT{m.group(2)}'
    m = re.fullmatch(r'([tk])\s*([123])', t)
    if m:
        return m.group(1).upper() + m.group(2)
    if t in ('1', '2', '3', '4', '5'):
        return 'VT' + t
    m = re.search(r'(?:vi tri|vt)\s*([1-5])$', t)
    if m:
        return 'VT' + m.group(1)
    goc = (chu or '').strip()
    return (goc[:16] or 'MT')


def _so_gia(v) -> int:
    if v is None or v == '':
        return 0
    if isinstance(v, bool):
        return 0
    if isinstance(v, (int, float)):
        return int(lam_tron(v))
    from .tien import doc_so_vn
    try:
        return int(lam_tron(doc_so_vn(str(v))))
    except (ValueError, ArithmeticError):
        return 0


_COT_EXCEL = (
    ('dat_o', ('dat o',)),
    ('tmdv', ('thuong mai', 'tmd')),
    ('sxkd', ('sx-kd', 'sxkd', 'khoang san', 'san xuat kinh doanh')),
    ('nn_cay', ('cay lau nam', 'cay hang nam')),
    ('nn_rung_nts', ('rung san xuat', 'thuy san', 'nuoi trong')),
)


def _tieu_de(ws):
    for i in range(1, 16):
        o = {}
        for c in range(1, min(ws.max_column or 1, 24) + 1):
            chu = bo_dau(str(ws.cell(i, c).value or '')).strip()
            if chu:
                o[c] = chu
        if any('ten duong' in v or v in ('duong', 'tuyen duong', 'tuyen') for v in o.values()):
            return i, o
    return None, {}


def _cot(o: dict, *mau: str):
    for c, chu in o.items():
        if any(m in chu for m in mau):
            return c
    return None


def doc_excel(file) -> tuple:
    """Đọc file Excel bảng giá đất. Trả (danh sách dòng, tên văn bản, câu đơn vị đã hiểu).

    Mỗi sheet một địa bàn (tên sheet), hoặc một cột Địa bàn. Cột giá ghi đồng/m² (file xuất từ phần mềm)
    hoặc nghìn đồng/m² nếu dòng tiêu đề ghi "nghìn". Cột tối thiểu: Tên đường và một cột giá (Đất ở hoặc Đơn giá).
    """
    import openpyxl
    __import__('pabt.an_toan').an_toan.kiem_excel(file)
    wb = openpyxl.load_workbook(file, data_only=True)
    dong, van_ban = [], ''
    thay_don_vi = []
    try:
        for ws in wb.worksheets:
            hang, o = _tieu_de(ws)
            if hang is None:
                continue
            phan_dau = ' '.join(str(ws.cell(i, 1).value or '') for i in range(1, hang))
            if not van_ban:
                a1 = str(ws.cell(1, 1).value or '').strip()
                if a1 and 'bang gia' not in bo_dau(a1):
                    van_ban = a1
                else:
                    a2 = re.sub(r'\.?\s*[Đđ]ơn vị:.*', '', str(ws.cell(2, 1).value or '')).strip()
                    van_ban = a2
            khoa = bo_dau(phan_dau)
            if 'nghin' in khoa:
                don_vi = 'nghin'
            elif 'dong/m' in khoa:
                don_vi = 'dong'
            else:
                don_vi = ''
            c_ten = _cot(o, 'ten duong', 'tuyen duong') or _cot(o, 'duong')
            c_dau = _cot(o, 'diem dau') or _cot(o, 'tu ')
            c_cuoi = _cot(o, 'diem cuoi') or _cot(o, 'den')
            c_vt = _cot(o, 'vi tri')
            c_xa = _cot(o, 'dia ban', 'xa/phuong', 'xa phuong') or _cot(o, 'xa', 'phuong')
            c_tt = _cot(o, 'tt', 'stt')
            c_gia = {}
            for khoa_cot, mau in _COT_EXCEL:
                c = _cot(o, *mau)
                if c:
                    c_gia[khoa_cot] = c
            if not c_gia:
                c = _cot(o, 'don gia', 'gia dat') or _cot(o, 'gia')
                if c:
                    c_gia['dat_o'] = c
            if not c_gia:
                raise LoiBangGia(f'Sheet "{ws.title}": chưa thấy cột giá. Cần cột "Đất ở" hoặc "Đơn giá" (đồng/m²).')
            ten_sheet = re.sub(r'(?i)^bảng giá đất\s*-\s*', '', ws.title).strip() or ws.title
            dem = 0
            so_duong = []
            bat = len(dong)
            for row in ws.iter_rows(min_row=hang + 1, max_col=min(ws.max_column or 1, 24), values_only=True):
                def o_cot(c, row=row):
                    return row[c - 1] if c and c - 1 < len(row) else None
                ten = str(o_cot(c_ten) or '').strip()
                if not ten or ten.lower() in ('none', 'tên đường'):
                    continue
                dem += 1
                xa = str(o_cot(c_xa) or '').strip() if c_xa else ''
                if not xa or xa.lower() == 'none':
                    xa = ten_sheet
                vt = _chuan_vi_tri('' if o_cot(c_vt) is None else str(o_cot(c_vt)))
                gia = {k: _so_gia(o_cot(c_gia.get(k))) for k, _ in COT}
                so_duong.extend(v for v in gia.values() if v)
                tt = _so_gia(o_cot(c_tt)) or dem
                dong.append(dict(xa=xa, tt=tt, ten_duong=ten,
                                 diem_dau=str(o_cot(c_dau) or '').strip(),
                                 diem_cuoi=str(o_cot(c_cuoi) or '').strip(),
                                 vi_tri=vt, nguong=[1000, 500],
                                 trang={'pl3': '', 'pl1': ''}, **gia))
            if so_duong and not don_vi:
                don_vi = 'dong' if max(so_duong) >= 1_000_000 else 'nghin'
            thay_don_vi.append(don_vi or 'nghin')
            if don_vi == 'dong':
                for r in dong[bat:]:
                    for k, _ in COT:
                        r[k] = int(lam_tron(r[k], -3)) // 1000
    finally:
        wb.close()
    if not dong:
        raise LoiBangGia('Không thấy bảng giá. Dòng tiêu đề cần có cột "Tên đường" và một cột giá.')
    chu = 'Giá hiểu theo đồng/m².' if 'dong' in thay_don_vi and 'nghin' not in thay_don_vi else (
        'Giá hiểu theo nghìn đồng/m² (như văn bản).' if 'dong' not in thay_don_vi else
        'Một số sheet theo đồng/m², một số theo nghìn đồng/m².')
    return dong, van_ban, chu


def ghi_thay(dong: list, van_ban: str = '', nguon: str = '') -> Path:
    """Ghi đè bảng giá đất của máy này. Bốn địa bàn gắn sẵn không còn hiện cho đến khi khôi phục. 1.0.56: cần quyền quản trị."""
    import os
    from . import quan_tri_bo
    quan_tri_bo.kiem_quyen('cập nhật bảng giá đất')
    p = file_thay()
    p.parent.mkdir(parents=True, exist_ok=True)
    tam = p.with_suffix('.json.tmp')
    tam.write_text(json.dumps({'van_ban': van_ban, 'nguon': str(nguon), 'dong': dong}, ensure_ascii=False),
                   encoding='utf-8')
    os.replace(tam, p)
    _quen()
    quan_tri_bo.sau_khi_sua()
    return p


def ghi_bo_sung(dong: list, van_ban: str = '', nguon: str = '') -> Path:
    """BỔ SUNG bảng giá (người dùng 30/10/2026: "thêm mục để bổ sung thêm giá đất vào phần mềm"): địa bàn của `dong` thay dòng cùng địa
    bàn (khop_xa) của bảng đang dùng, địa bàn khác giữ nguyên - kể cả bốn địa bàn gắn sẵn. Mỗi dòng mang văn bản căn cứ của mình
    ('van_ban') để căn cứ in đúng nguồn."""
    cu, vb_cu, thay = _da_doc()
    vb_cu = vb_cu if thay else 'NQ 28/2025/NQ-HĐND'
    xa_moi = list(dict.fromkeys(r.get('xa', '') for r in dong))
    giu = []
    for r in cu:
        if any(khop_xa(x, r.get('xa', '')) or khop_xa(r.get('xa', ''), x) for x in xa_moi if x):
            continue
        r = dict(r)
        r.setdefault('van_ban', vb_cu)
        giu.append(r)
    moi = []
    for r in dong:
        r = dict(r)
        r.setdefault('van_ban', van_ban or 'Bảng giá đất bổ sung')
        moi.append(r)
    return ghi_thay(giu + moi, van_ban or vb_cu, nguon)


@lru_cache(maxsize=1)
def xa_gan_san() -> tuple:
    """Tên các địa bàn của bảng gắn sẵn (đóng kèm)."""
    p = _file()
    try:
        dong, _ = _doc(str(p), p.stat().st_mtime_ns)
    except OSError:
        return ()
    return tuple(dict.fromkeys(r['xa'] for r in dong))


def xoa_thay() -> bool:
    """Xóa bảng người dùng: phần mềm trở lại 4 địa bàn gắn sẵn. False nếu đang không thay."""
    from . import quan_tri_bo
    quan_tri_bo.kiem_quyen('đổi bảng giá đất')
    p = file_thay()
    if not p.is_file():
        return False
    p.unlink()
    _quen()
    quan_tri_bo.sau_khi_sua()
    return True

"""Cập nhật bảng giá đất cho địa bàn ngoài 4 xã gắn sẵn (Đồng Nai).

Hai đường, không bịa đơn giá:
1. Tìm văn bản trên Công báo / cơ sở dữ liệu văn bản, tải file và bóc bảng giá.
2. Đọc file Excel, Word, PDF hoặc CSV có sẵn trên máy khi web không ra bảng giá.

Ghi bằng gia_dat_nq28.ghi_thay: bảng gắn sẵn (Trị An, Tân An, Phú Lý, Tân Triều) không còn
hiện ở ô Vị trí và tra cứu cho đến khi dùng lại bảng gắn sẵn.
"""
from __future__ import annotations
import re
import shutil
import tempfile
import urllib.parse
import zipfile
from pathlib import Path

from . import gia_dat_nq28 as nq
from .tien import lam_tron
from .lap_pa import bo_dau


class LoiWeb(Exception):
    """Web không trả được bảng đơn giá. Màn hình chuyển sang chọn file."""


# Nghị quyết bảng giá đất Đồng Nai 2026 trên Công báo. Trang tìm kiếm chỉ ra văn bản này khi từ khóa là "bảng giá đất";
# thêm tên xã thì trang tìm trả rỗng — nên mở thẳng địa chỉ này khi tỉnh là Đồng Nai.
URL_BANG_GIA_DONG_NAI = (
    'https://congbao.dongnai.gov.vn/vi/vanban/detail/'
    'Nghi-quyet-so-28-2025-NQ-HDND-Ban-hanh-Quy-dinh-Bang-gia-dat-lan-dau-tren-dia-ban-tinh-Dong-Nai-nam-2026-9508/')


def ten_gon(s: str) -> str:
    """'Xã Trị An' / 'Thành phố Hồ Chí Minh' / 'TP. Vũng Tàu' / 'TP.HCM' -> tên không tiền tố."""
    t = re.sub(r'(?i)^(xã|phường|thị\s*trấn|tỉnh|thành\s*phố|tp\.?)\s+', '', (s or '').strip()).strip()
    khoa = bo_dau(t).replace(' ', '').replace('.', '')
    if khoa in ('hcm', 'tphcm'):
        return 'Hồ Chí Minh'
    return t


def _la_dong_nai(tinh: str) -> bool:
    t = bo_dau(ten_gon(tinh))
    return (not t) or ('dong nai' in t)


def _cot(o: dict, *mau: str):
    for c, chu in o.items():
        if any(m in chu for m in mau):
            return c
    return None


def _tach_dong(cac_dong: list) -> list:
    """PDF thường là một ô cả dòng: tách khi có nhiều khoảng trắng hoặc tab."""
    ra = []
    for r in cac_dong:
        if not r:
            continue
        if len(r) == 1 and re.search(r'\s{2,}|\t', str(r[0])):
            ra.append([x.strip() for x in re.split(r'\s{2,}|\t', str(r[0])) if x.strip()])
        else:
            ra.append([str(x).strip() for x in r])
    return ra


def _dong_tu_o(cac_dong: list, ten_file: str, xa: str) -> tuple:
    """Bảng chữ (Word, PDF, CSV) -> (dòng giá, câu đơn vị). Cùng cấu trúc với doc_excel."""
    chuan = _tach_dong(cac_dong)
    hang, o = None, {}
    for i, r in enumerate(chuan[:40]):
        m = {c: bo_dau(v) for c, v in enumerate(r) if v}
        if any('ten duong' in v or v in ('duong', 'tuyen duong', 'tuyen') for v in m.values()):
            hang, o = i, m
            break
    if hang is None:
        raise nq.LoiBangGia(
            f'Không thấy dòng tiêu đề trong {ten_file}. Cần cột "Tên đường" và cột "Đất ở" hoặc "Đơn giá".')
    c_ten = _cot(o, 'ten duong', 'tuyen duong') or _cot(o, 'duong')
    c_dau = _cot(o, 'diem dau') or _cot(o, 'tu ')
    c_cuoi = _cot(o, 'diem cuoi') or _cot(o, 'den')
    c_vt = _cot(o, 'vi tri')
    c_xa = _cot(o, 'dia ban', 'xa/phuong', 'xa phuong') or _cot(o, 'xa', 'phuong')
    c_tt = _cot(o, 'tt', 'stt')
    c_gia = {}
    for khoa, mau in nq._COT_EXCEL:
        c = _cot(o, *mau)
        if c is not None:
            c_gia[khoa] = c
    if not c_gia:
        c = _cot(o, 'don gia', 'gia dat') or _cot(o, 'gia')
        if c is not None:
            c_gia['dat_o'] = c
    if c_ten is None or not c_gia:
        raise nq.LoiBangGia(f'{ten_file}: thiếu cột Tên đường hoặc cột giá.')
    # đơn vị giá: chỉ xét vài dòng ngay trên tiêu đề + chính dòng tiêu đề ("ĐVT: 1.000 đồng/m²") - lời văn phía trên (câu "không thấp
    # hơn 150.000 đồng/m²" của quy tắc vị trí) không phải đơn vị của bảng
    dau = ' '.join(' '.join(r) for r in chuan[max(0, hang - 3):hang + 1])
    khoa = bo_dau(dau)
    if 'nghin' in khoa or re.search(r'\b1[.,]?000\s*(?:dong|d\b|vnd)', khoa):
        don_vi = 'nghin'
    elif 'dong/m' in khoa or 'dong / m' in khoa:
        don_vi = 'dong'
    else:
        don_vi = ''
    def o_cot(r, c):
        return r[c] if c is not None and c < len(r) else ''

    dong, so = [], []
    dem = 0
    for r in chuan[hang + 1:]:
        ten = o_cot(r, c_ten).strip()
        if not ten or bo_dau(ten) in ('ten duong', 'tong', 'tong cong'):
            continue
        dem += 1
        ten_xa = o_cot(r, c_xa).strip() if c_xa is not None else ''
        if not ten_xa:
            ten_xa = xa.strip() or Path(ten_file).stem
        gia = {k: nq._so_gia(o_cot(r, c_gia.get(k))) for k, _ in nq.COT}
        so.extend(v for v in gia.values() if v)
        dong.append(dict(xa=ten_xa, tt=nq._so_gia(o_cot(r, c_tt)) or dem, ten_duong=ten,
                         diem_dau=o_cot(r, c_dau).strip(), diem_cuoi=o_cot(r, c_cuoi).strip(),
                         vi_tri=nq._chuan_vi_tri(o_cot(r, c_vt)), nguong=[1000, 500],
                         trang={'pl3': '', 'pl1': ''}, **gia))
    if not dong:
        raise nq.LoiBangGia(f'{ten_file}: có tiêu đề nhưng không có dòng giá.')
    if not don_vi:
        don_vi = 'dong' if max(so or [0]) >= 1_000_000 else 'nghin'
    if don_vi == 'dong':
        for r in dong:
            for k, _ in nq.COT:
                r[k] = int(lam_tron(r[k], -3)) // 1000
    chu = 'Giá hiểu theo đồng/m².' if don_vi == 'dong' else 'Giá hiểu theo nghìn đồng/m².'
    return dong, chu


def _ten_ao(ten: str) -> bool:
    t = bo_dau(ten)
    return t in ('', 'sheet', 'sheet1', 'sheet2', 'bang gia dat') or t.startswith('sheet')


def loc_xa(dong: list, xa: str) -> list:
    """Giữ dòng đúng xã người dùng nhập. File không ghi tên xã thì gán tên đó. Không đổi tên xã khác."""
    if not str(xa or '').strip():
        return dong
    co_ten = [r for r in dong if (r.get('xa') or '').strip()]
    khop = [r for r in co_ten if nq.khop_xa(xa, r['xa'])]
    if khop:
        return khop
    ten = {r['xa'] for r in co_ten}
    if not ten or all(_ten_ao(x) for x in ten):          # file không ghi tên địa bàn: gán tên người dùng nhập
        for r in dong:
            r['xa'] = xa.strip()
        return dong
    raise nq.LoiBangGia(
        f'Không thấy "{xa}" trong file. Các địa bàn đọc được: {", ".join(sorted(x for x in ten if x)) or "(không có tên)"}.')


def doc_scan(file, xa: str = '', bao=None, cho=None, chu_ra: list | None = None) -> list:
    """PDF ảnh hoặc file ảnh: nhận dạng từng trang, dừng khi đã đọc xong mục địa bàn (file lớn không đọc hết).
    chu_ra: danh sách nhận các dòng chữ đã nhận dạng (đọc quy tắc vị trí 2-4 trong lời văn - quy_tac_vi_tri)."""
    from . import ocr
    xa = (xa or '').strip()
    tim = ten_gon(xa)
    dong_chu = []
    da_thay = False
    for chu in ocr.tung_trang(file, bao, cho, dpi=200):
        if cho and cho():
            break
        dong_chu += [x.strip() for x in chu.splitlines() if x.strip()]
        if not tim:
            continue
        if bo_dau(tim) in bo_dau(chu):
            da_thay = True
            continue
        # Chỉ dừng ở DÒNG tiêu đề địa bàn khác. Chữ "xã" trong câu giáp ranh không được cắt mất các trang sau.
        if da_thay and any(
                re.fullmatch(r'(?:\d+\.\s*)?(?:Xã|Phường|Thị trấn)\s+\S.{0,40}', d.strip(), re.I)
                and bo_dau(tim) not in bo_dau(d) for d in chu.splitlines()):
            break
    if chu_ra is not None:
        chu_ra += dong_chu
    tach = []
    for d in dong_chu:
        if re.search(r'\s{2,}|\t', d):
            tach.append([x.strip() for x in re.split(r'\s{2,}|\t', d) if x.strip()])
        else:
            tach.append([d])
    return phan_tich_nghi_quyet(tach) or _dong_tu_o(tach, Path(file).name, xa)[0]


def _gan_tinh(dong: list, tinh: str, xa: str, vb: str, chu: str) -> tuple:
    """Một lối ra cho mọi loại file: lọc đúng địa bàn, gắn tỉnh, đặt tên văn bản khi file không có tiêu đề."""
    dong = loc_xa(dong, xa)
    if tinh.strip():
        for r in dong:
            r['tinh'] = tinh.strip()
    if not vb:
        vb = f'Bảng giá đất {xa}'.strip()
    return dong, vb, chu


def doc_file(file, tinh: str = '', xa: str = '', bao=None, cho=None) -> tuple:
    """Đọc Excel / Word / PDF (kể cả PDF ảnh) / ảnh / CSV. Trả (dòng, văn bản, câu đơn vị). Văn bản có hướng dẫn tính vị trí 2-4 trong
    lời văn (quy_tac_vi_tri) thì dòng các vị trí đó được dựng thêm từ vị trí 1 và câu đơn vị ghi rõ."""
    kq = doc_file_day_du(file, tinh, xa, bao, cho)
    dong, them = ap_quy_tac_file(kq)
    return dong, kq['van_ban'], kq['chu'] + chu_quy_tac(kq['quy_tac'], them)


def ap_quy_tac_file(kq: dict, quy_tac: list | None = None) -> tuple:
    """(dòng sau khi dựng vị trí theo quy tắc, số dòng thêm). quy_tac None = quy tắc đọc được trong file (kq['quy_tac'])."""
    from .quy_tac_vi_tri import ap_quy_tac
    return ap_quy_tac(kq['dong_goc'], kq['quy_tac'] if quy_tac is None else quy_tac)


def chu_quy_tac(quy_tac: list, them: int) -> str:
    if not quy_tac:
        return ''
    from .quy_tac_vi_tri import tom_tat
    return (f' Văn bản có hướng dẫn tính vị trí ngoài bảng ({tom_tat(quy_tac)}): đã dựng thêm {them} dòng - kiểm tra lại ở bảng '
            '"Quy tắc vị trí".')


def doc_file_day_du(file, tinh: str = '', xa: str = '', bao=None, cho=None) -> dict:
    """Như doc_file nhưng CHƯA dựng vị trí theo quy tắc: {'dong_goc': dòng của bảng, 'quy_tac': [QuyTac] đọc trong lời văn,
    'van_ban', 'chu'} - màn hình cho người dùng sửa quy tắc rồi tính lại (ap_quy_tac_file)."""
    from .quy_tac_vi_tri import doc_quy_tac, doc_toan_van_nghi_quyet, la_van_ban_toan_van_nq28
    chu_vb = []
    toan_van = None
    try:
        dong, vb, chu = _doc_file(file, tinh, xa, bao, cho, chu_vb)
    except nq.LoiBangGia:
        # 1.0.81: toàn văn Nghị quyết (Điều 1 -> 10, không có bảng Tên đường): không báo lỗi - đọc quy tắc trong lời văn, bảng phía
        # trên là bảng giá đường đang dùng của địa bàn đang chọn
        if not la_van_ban_toan_van_nq28(chu_vb):
            raise
        dong = [dict(r) for r in nq.tat_ca() if xa and nq.khop_xa(xa, r['xa'])]
        vb, chu = Path(file).stem, ('Toàn văn nghị quyết (không có bảng Tên đường): đã đọc quy tắc trong lời văn; bảng phía trên là '
                                   f'bảng giá đường đang dùng của {xa or "địa bàn đang chọn (chưa nhập xã)"}.')
    if la_van_ban_toan_van_nq28(chu_vb):
        try:
            toan_van = doc_toan_van_nghi_quyet(chu_vb, luu=True)
            chu += f' Toàn văn: {len(toan_van["quy_tac"])} quy tắc ở {len(toan_van["dieu"])} điều (lưu {toan_van["file"]}).'
        except Exception:                               # noqa: BLE001 - lời văn lạ không làm hỏng việc đọc bảng
            toan_van = None
    try:
        qt = doc_quy_tac(chu_vb)
    except Exception:                                   # noqa: BLE001 - lời văn lạ không được làm hỏng việc đọc bảng
        qt = []
    return {'dong_goc': dong, 'quy_tac': qt, 'van_ban': vb, 'chu': chu, 'toan_van': toan_van}


def _doc_file(file, tinh: str, xa: str, bao, cho, chu_vb: list) -> tuple:
    from . import ocr
    from .nhap_don_gia import LoiPdfScan, doc_bang
    p = Path(file)
    if not p.is_file():
        raise nq.LoiBangGia(f'Không thấy file {p.name}.')
    xa, tinh = (xa or '').strip(), ten_gon(tinh)
    duoi = p.suffix.lower()
    if duoi in ('.xlsx', '.xlsm'):
        dong, vb, chu = nq.doc_excel(p)
        try:                                            # ghi chú / sheet hướng dẫn trong file Excel (quy tắc vị trí)
            chu_vb += doc_bang(p)[:5000]
        except Exception:                               # noqa: BLE001
            pass
    elif duoi in ocr.DUOI_ANH:
        try:
            dong = doc_scan(p, xa, bao, cho, chu_vb)
        except Exception as e:
            raise nq.LoiBangGia(str(e)) from None
        vb, chu = p.stem, 'Đọc từ ảnh, nhận dạng chữ.'
        if not dong:
            dong = _gia_tu_loi_van(chu_vb, xa)
            if dong:
                chu += ' Đọc thêm từ lời văn.'
    else:
        try:
            o = doc_bang(p)
        except LoiPdfScan:
            try:
                dong = doc_scan(p, xa, bao, cho, chu_vb)
            except Exception as e:
                raise nq.LoiBangGia(str(e)) from None
            vb, chu = p.stem, 'PDF ảnh: nhận dạng từng trang.'
            if not dong:
                dong = _gia_tu_loi_van(chu_vb, xa)
                if dong:
                    chu += ' Đọc thêm từ lời văn.'
            return _gan_tinh(dong, tinh, xa, vb, chu)
        except Exception as e:
            raise nq.LoiBangGia(str(e)) from None
        chu_vb += o
        if duoi == '.docx':
            dong = phan_tich_nghi_quyet(o)
            if not any((r.get('xa') or '').strip() for r in dong):
                # bảng không chia mục theo xã (một địa bàn, có cột Điểm đầu / Điểm cuối): đọc theo cột như Excel; không được thì giữ
                try:
                    dong = _dong_tu_o(o, p.name, xa)[0]
                except nq.LoiBangGia:
                    if not dong:
                        raise
            chu = 'Giá trong văn bản.'
        else:
            try:
                dong, chu = _dong_tu_o(o, p.name, xa)
            except nq.LoiBangGia:
                dong = _gia_tu_loi_van(o, xa)
                chu = 'Giá đọc từ lời văn nghị quyết (không có bảng cột chuẩn).'
                if not dong:
                    raise
        vb = ''
        for r in o[:8]:
            d = ' '.join(str(x) for x in r).strip()
            if d and 'ten duong' not in bo_dau(d):
                vb = d[:180]
                break
    return _gan_tinh(dong, tinh, xa, vb, chu)


def ap_dung(dong: list, van_ban: str = '', nguon: str = '', bo_sung: bool = False) -> list:
    """Ghi bảng này vào bảng giá đang dùng. bo_sung=False: THAY toàn bộ (bốn địa bàn gắn sẵn không còn hiện); bo_sung=True: thêm vào
    bảng đang dùng, địa bàn trùng tên thì thay, địa bàn khác (cả bốn địa bàn gắn sẵn) giữ nguyên (gia_dat_nq28.ghi_bo_sung)."""
    if not dong:
        raise nq.LoiBangGia('Không có dòng giá để ghi.')
    if bo_sung:
        nq.ghi_bo_sung(dong, van_ban, nguon)
    else:
        nq.ghi_thay(dong, van_ban, nguon)
    return nq.ds_xa()


def _module_web():
    """Module tìm web. Bộ cài gốc trước 0.9.49 loại trừ module này -> ImportError, không được hiện chữ tiếng Anh."""
    try:
        from . import cap_nhat_web
    except ImportError:
        raise LoiWeb(
            'Bản đang chạy không kèm phần tìm bảng giá trên web. '
            'Chọn file Excel, Word hoặc PDF có cột Tên đường và cột Đất ở hoặc Đơn giá.') from None
    return cap_nhat_web


def _loai_gia(chu: str):
    k = bo_dau(chu)
    if 'thuong mai' in k:
        return 'tmdv'
    if re.search(r'\brung\b', k) or 'thuy san' in k:      # 1.0.81: trước 'san xuat' - "Đất rừng sản xuất" từng bị nhận là SX-KD
        return 'nn_rung_nts'
    if 'san xuat' in k or 'khoang san' in k:
        return 'sxkd'
    if 'cay lau' in k or 'cay hang' in k:
        return 'nn_cay'
    if re.search(r'dat o\b', k):
        return 'dat_o'
    return None


def _so_nghin(s) -> int:
    """'15.300' trong nghị quyết = 15.300 nghìn đồng/m². Số từ 1 triệu trở lên hiểu là đồng/m²."""
    t = str(s or '').strip()
    if not re.search(r'\d', t):
        return 0
    from .tien import doc_so_vn
    try:
        n = int(doc_so_vn(t))          # Decimal, không float: 15.300 nghìn giữ đúng 15300
    except (ValueError, ArithmeticError):
        return 0
    return n // 1000 if n >= 1_000_000 else n


def _vi_tri_dong(ten: str, dem: dict) -> str:
    """Dòng tên đường = mặt tiền. Các dòng 'đấu nối' / 'không đấu nối' kế tiếp = T1–T3 / K1–K3."""
    bd = bo_dau(ten)
    if 'khong dau noi' in bd:
        dem['k'] += 1
        dem['t'] = 0
        return 'K' + str(min(dem['k'], 3))
    if 'dau noi' in bd:
        dem['t'] += 1
        dem['k'] = 0
        return 'T' + str(min(dem['t'], 3))
    dem['t'] = dem['k'] = 0
    return 'MT'


def _gia_tu_loi_van(cac_dong: list, xa: str = '') -> list:
    """Không có bảng cột chuẩn: bóc mục xã / tuyến / mức giá trong lời văn nghị quyết. Trả [] nếu không đọc được."""
    dong = phan_tich_nghi_quyet(cac_dong)
    xa = (xa or '').strip()
    if xa:
        for r in dong:
            if not (r.get('xa') or '').strip():
                r['xa'] = xa
    return dong


def phan_tich_nghi_quyet(cac_dong: list) -> list:
    """Bảng Word/PDF kiểu Nghị quyết bảng giá đất: mỗi địa bàn một mục, 7 mức vị trí một tuyến."""
    xa, cot_gia, dong = '', [], []
    dem = {'t': 0, 'k': 0}
    duong = ''
    for r in cac_dong:
        o = [str(x or '').strip() for x in r]
        chu = [x for x in o if x]
        gop = ' '.join(chu)
        # "Xã Trị An" hoặc "53. Xã Trị An" (mục trong phụ lục). Không nhận câu "Giáp ranh xã …".
        tieu = re.fullmatch(r'(?:\d+\.\s*)?((?:Xã|Phường|Thị trấn)\s+.+)', gop.strip(), re.I)
        if tieu and len(gop) < 60 and not re.search(r'(?i)đường|giáp|tuyến', gop):
            xa = tieu.group(1).strip()
            cot_gia = []
            duong = ''
            continue
        loai = [(_loai_gia(x), x) for x in o]
        if any(x[0] for x in loai) and any('ten duong' in bo_dau(x) for x in o):
            cot_gia = [k for k, _ in loai if k]
            continue
        if not chu or not re.fullmatch(r'\d+', chu[0]):
            continue
        so = []
        chu_ten = ''
        for x in chu[1:]:
            n = _so_nghin(x)
            if n and re.fullmatch(r'[\d.\s]+', x):
                so.append(n)
            elif len(x) > len(chu_ten):
                chu_ten = x
        if not chu_ten or not so:
            continue
        vt = _vi_tri_dong(chu_ten, dem)
        if vt == 'MT':
            duong = chu_ten
        gia = {k: 0 for k, _ in nq.COT}
        for k, n in zip(cot_gia, so):
            gia[k] = n
        dong.append(dict(xa=xa or '', tt=int(chu[0]), ten_duong=duong or chu_ten,
                         diem_dau='', diem_cuoi='', vi_tri=vt, dieu_kien='' if vt == 'MT' else chu_ten,
                         nguong=[1000, 500], trang={'pl3': '', 'pl1': ''}, **gia))
    return dong


def _gop_dong(ds: list) -> list:
    """Nhiều phụ lục (đất ở / nông nghiệp) cùng một tuyến: gộp cột giá."""
    thu, gop = [], {}
    for r in ds:
        k = (bo_dau(r.get('xa') or ''), bo_dau(r.get('ten_duong') or ''), r.get('vi_tri') or '')
        cu = gop.get(k)
        if cu is None:
            gop[k] = dict(r)
            thu.append(k)
            continue
        for cot, _ in nq.COT:
            if r.get(cot) and not cu.get(cot):
                cu[cot] = r[cot]
    return [gop[k] for k in thu]


def _doc_docx_gia(p: Path) -> list:
    from .nhap_don_gia import _doc_docx
    return phan_tich_nghi_quyet(_doc_docx(p))


def _trang_gia_dat(html: str, url: str) -> list:
    """Các trang chi tiết 'bảng giá đất' trên cùng máy chủ. Công báo ghi điểm thấp hơn ngưỡng quét đơn giá bồi thường."""
    from . import cap_nhat_web
    p = cap_nhat_web._Link()
    p.feed(html)
    may = urllib.parse.urlparse(url).netloc
    ds, da = [], {url.split('#')[0]}
    for chu, href in p.ds:
        if 'gia dat' not in bo_dau(chu) and 'bang gia' not in bo_dau(chu):
            continue
        dich = urllib.parse.urljoin(url, (href or '').strip()).split('#')[0]
        if urllib.parse.urlparse(dich).netloc != may or dich in da:
            continue
        da.add(dich)
        ds.append((chu, dich))
    def _uu(x):
        u = bo_dau(x[0] + ' ' + x[1])
        if 'bang gia dat lan dau' in u or 'bang-gia-dat-lan-dau' in u:
            return 0
        if 'bang gia dat' in u:
            return 1
        return 2
    ds.sort(key=_uu)
    return [u for _, u in ds[:4]]


def _tep_co_dia_ban(p: Path, xa: str) -> bool:
    """Địa bàn có trong file Word không. Chữ có thể bị tách bởi thẻ XML nên ghép phần chữ trước khi so."""
    if p.suffix.lower() != '.docx' or not xa.strip():
        return True
    try:
        # Đóng zip ngay: để mở thì Windows khóa file, thư mục tạm không xóa được.
        with zipfile.ZipFile(p) as z:
            xml = z.read('word/document.xml').decode('utf-8', 'replace')
    except (OSError, zipfile.BadZipFile, KeyError, UnicodeError):
        return False
    chu = bo_dau(re.sub(r'<[^>]+>', ' ', xml))
    return bo_dau(ten_gon(xa)) in chu


def tim_tren_web(tinh: str, xa: str, thu_muc=None, url: str = '', tham_khao: bool = True) -> tuple:
    """Tìm bảng giá đất của xã / phường, thứ tự nguồn (0.9.65 - nguon_gia_dat):
    1. url người dùng dán (trang văn bản hoặc file phụ lục) + danh bạ văn bản chính thức của tỉnh (đã đọc được lần trước);
    2. tìm trên Công báo (Đồng Nai, Tây Ninh) / vbpl;
    3. tham_khao: giá tham khảo guland.vn (9 tỉnh) - nhãn rõ trong văn bản / căn cứ, không phải căn cứ pháp lý.
    Tên tỉnh cũ (Bình Phước, Bình Dương…) đổi sang tỉnh hiện hành. Đọc được từ url -> nhớ vào danh bạ. Không có giá -> LoiWeb."""
    from . import nguon_gia_dat as ng
    cap_nhat_web = _module_web()
    xa, tinh_go = ten_gon(xa), ten_gon(tinh)
    tinh = ng.chuan_tinh(tinh_go) or tinh_go
    url = (url or '').strip()
    if url and not url.lower().startswith('https://'):
        raise LoiWeb('Đường dẫn phải bắt đầu bằng https:// (trang văn bản hoặc file phụ lục bảng giá đất).')
    if not xa:
        raise LoiWeb('Nhập tên địa bàn, ví dụ Trị An, Trảng Bom, Nhơn Trạch, Vũng Tàu.')
    tu_tao = thu_muc is None
    thu = Path(thu_muc) if thu_muc else Path(tempfile.mkdtemp(prefix='pabt_gia_dat_'))
    thu.mkdir(parents=True, exist_ok=True)
    try:
        try:
            kq = _tim_va_boc(cap_nhat_web, tinh, xa, thu, url)
        except LoiWeb:
            if url or not tham_khao:
                raise
            try:
                tk = ng.doc_guland(tinh, xa)
            except Exception:                   # noqa: BLE001 - trang tham khảo lỗi: báo lỗi của nguồn chính thức
                tk = []
            if not tk:
                raise
            return (tk, ng.NHAN_THAM_KHAO,
                    'Giá tham khảo (Vị trí 1-4), nghìn đồng/m². Đối chiếu nghị quyết bảng giá đất của tỉnh trước khi dùng.',
                    tk[0].get('nguon_url') or ng.GULAND_GOC)
        if url and tinh:
            ng.ghi_danh_ba(tinh, url, kq[1])
        return kq
    finally:
        if tu_tao:
            shutil.rmtree(thu, ignore_errors=True)


def _du_hai_loai(dong: list, xa: str) -> bool:
    """Đã có cả đất ở và nông nghiệp của đúng địa bàn: không tải thêm phụ lục."""
    khop = [r for r in dong if nq.khop_xa(xa, r.get('xa') or '')]
    return any(r.get('dat_o') for r in khop) and any(r.get('nn_cay') or r.get('nn_rung_nts') for r in khop)


def _tim_va_boc(cap_nhat_web, tinh: str, xa: str, thu: Path, url: str = '') -> tuple:
    from . import nguon_gia_dat as ng
    noi = 'dongnai' if _la_dong_nai(tinh) else 'vbpl'
    # Đồng Nai: từ khóa ngắn + địa chỉ nghị quyết đã biết. Tỉnh khác: tìm "bảng giá đất" + tên tỉnh trên vbpl.
    cau = ['bảng giá đất'] if noi == 'dongnai' else [f'bảng giá đất {tinh}'.strip(), f'bảng giá đất {xa} {tinh}'.strip()]
    # đường dẫn dán + danh bạ của tỉnh: file phụ lục tải thẳng, trang văn bản đọc liên kết file; có rồi thì không tìm nữa
    vb_db, ds_db = ng.url_danh_ba(tinh) if tinh else ('', [])
    truc_tiep = list(dict.fromkeys(([url] if url else []) + ds_db))
    tep_truoc = [u for u in truc_tiep if cap_nhat_web._duoi(u) in ('.docx', '.xlsx', '.xlsm', '.pdf', '.csv')]
    trang, da_url = [u for u in truc_tiep if u not in tep_truoc], set(truc_tiep)
    loi = []
    if truc_tiep:
        cau = []
    for q in cau:
        try:
            url = cap_nhat_web.duong_dan(q, noi)
            du, that, loai, _ten, bm = cap_nhat_web._lay(url, 25, chi_html=True)
        except Exception as e:
            loi.append(str(e))
            continue
        if du and (b'<html' in du[:300].lower() or b'<!doctype' in du[:300].lower()):
            html = cap_nhat_web._html(du, bm)
            for u in _trang_gia_dat(html, that):
                if u not in da_url:
                    da_url.add(u)
                    trang.append(u)
    if _la_dong_nai(tinh) and URL_BANG_GIA_DONG_NAI not in da_url:
        trang.insert(0, URL_BANG_GIA_DONG_NAI)
        da_url.add(URL_BANG_GIA_DONG_NAI)
    if not trang and not tep_truoc:
        q = urllib.parse.quote(f'bảng giá đất {tinh}'.strip())
        raise LoiWeb(f'Không thấy văn bản bảng giá đất của {xa}' + (f', {tinh}' if tinh else '') +
                     ('.\n' + loi[0] if loi else '.') +
                     '\nTìm nghị quyết bảng giá đất của tỉnh trên Công báo / cổng thông tin tỉnh hoặc '
                     f'https://vbpl.vn/van-ban/dia-phuong?keyword={q} rồi dán đường dẫn trang văn bản (hoặc file phụ lục) vào ô '
                     '"Đường dẫn văn bản" - phần mềm nhớ cho lần sau.')
    tep, da_tep = list(tep_truoc), set(tep_truoc)
    van_ban = vb_db
    for u in trang[:3]:
        try:
            du, that, loai, _ten, bm = cap_nhat_web._lay(u, 25, chi_html=True)
        except Exception as e:
            loi.append(str(e))
            continue
        html = cap_nhat_web._html(du or b'', bm)
        if not van_ban:
            van_ban = cap_nhat_web._tieu_de(html) or u
        for chu, link in cap_nhat_web.lien_ket_file(html, that):
            if link in da_tep:
                continue
            # file .doc cần Word; phụ lục bảng giá là .docx / .xlsx / .pdf hoặc nút tải ?download=
            if re.search(r'\.doc(\?|$)', chu, re.I) and '.docx' not in chu.lower():
                continue
            da_tep.add(link)
            tep.append(link)
    dong = []
    for link in tep[:12]:
        try:
            kq = cap_nhat_web.tai_ve(link, thu)
        except Exception as e:
            loi.append(str(e))
            continue
        f = Path(kq['file']) if kq.get('file') else None
        if f is None or f.suffix.lower() == '.doc':
            continue
        if f.stat().st_size < 80_000 and link not in tep_truoc:     # tệp nhỏ trên trang văn bản: tờ trình, quyết định... bỏ qua;
            continue                                                 # file người dùng dán / danh bạ: luôn đọc
        if not _tep_co_dia_ban(f, xa):
            continue
        try:
            if f.suffix.lower() == '.docx':
                them = _doc_docx_gia(f)
                if not them:
                    them, _, _ = doc_file(f, tinh, '')
            else:
                them, _, _ = doc_file(f, tinh, '')
        except nq.LoiBangGia as e:
            loi.append(str(e))
            continue
        dong.extend(them)
        # Phụ lục đất ở và nông nghiệp là hai file. Đủ cả hai thì dừng, không tải nốt các xã khác.
        if _du_hai_loai(dong, xa):
            break
    dong = _gop_dong(dong)
    try:
        dong = loc_xa(dong, xa)
    except nq.LoiBangGia as e:
        raise LoiWeb(str(e) + '\nĐã thấy văn bản bảng giá đất nhưng không bóc được mục này. Chọn file Excel nếu bạn có bảng riêng.') from None
    if not dong:
        cuoi = '\n'.join(loi[:2])
        raise LoiWeb('Đã mở văn bản bảng giá đất nhưng không có dòng đơn giá đọc được.' + (f'\n{cuoi}' if cuoi else ''))
    if tinh:
        for r in dong:
            r['tinh'] = tinh
    return dong, van_ban or f'Bảng giá đất {xa}', 'Giá trong văn bản, nghìn đồng/m².', (trang or tep)[0]

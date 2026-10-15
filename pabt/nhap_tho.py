"""Nhập danh sách hộ / thửa từ một file Excel BẤT KỲ (không theo mẫu PABT) vào file dự án .pabt.

Tự tìm sheet và dòng tiêu đề (kể cả tiêu đề 2 dòng có ô gộp), tự nhận cột theo tên (họ tên, địa chỉ, tờ, thửa,
diện tích thu hồi, loại đất, CCCD, điện thoại, ghi chú...), bỏ dòng trống / dòng cộng / dòng đánh số cột,
gom các dòng cùng người (CCCD, hoặc họ tên + địa chỉ) thành một hộ, mỗi dòng có tờ / thửa là một thửa.

Ghi vào file .pabt: XÓA TRẮNG hồ sơ cũ (hộ, thửa, phương án, tổng Excel, thông tin dự án, nhật ký) nhưng
GIỮ danh mục đơn giá, tham số, biểu thưởng của file; tất cả trong một giao dịch.
"""
from __future__ import annotations
import re
import tempfile
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import openpyxl

from . import csdl, nhap_excel
from .lap_pa import LoiNhap
from .nhap_excel import BaoCaoNhap, _txt, chuan_cccd, chuan_hoa
from .tien import D, chuoi, doc_so_vn

# trường -> [(mẫu regex trên tiêu đề đã chuẩn hóa, điểm)]; mẫu loại trừ đặt trong LOAI_TRU
MAU_COT = {
    'stt': [(r'^(stt|tt|so tt|so thu tu|thu tu)$', 10)],
    'ho_ten': [(r'\bho (va )?ten\b', 10), (r'\bten (chu|nguoi|ho)\b', 9), (r'\bchu (su dung|so huu|ho|dat)\b', 9),
               (r'\bnguoi (su dung|bi thu hoi|co dat)\b', 8), (r'^ten$', 6), (r'\bho so kiem (dem|ke)\b', 5)],
    'dia_chi': [(r'\bdia chi\b', 10), (r'\bnoi (cu tru|o|thuong tru)\b', 9), (r'\bthuong tru\b', 8), (r'\bcho o\b', 6)],
    'so_cccd': [(r'\b(cccd|cmnd|cmt)\b', 10), (r'\bcan cuoc\b', 10), (r'\bdinh danh\b', 9), (r'\bchung minh\b', 9)],
    'ngay_cap': [(r'\bngay cap\b', 10)],
    'noi_cap': [(r'\bnoi cap\b', 10)],
    'dien_thoai': [(r'\bdien thoai\b', 10), (r'\b(sdt|so dt|dt lien he)\b', 9)],
    'so_to': [(r'\bto (ban do|bd|so)\b', 10), (r'\bso to\b', 10), (r'^to$', 9), (r'\bto\b', 5)],
    'so_thua': [(r'\bthua (dat )?so\b', 10), (r'\bso thua\b', 10), (r'^thua( dat)?$', 9), (r'\bthua\b', 5)],
    'dt_thu_hoi': [(r'\b(dien tich|dt)\b.*\bthu hoi\b', 10), (r'\bthu hoi\b.*\b(dien tich|dt|m2)\b', 9),
                   (r'^(dien tich|dt)( \(?m2\)?)?$', 6), (r'\bdien tich\b', 4)],
    'dt_ban_do': [(r'\b(dien tich|dt)\b.*\bban do\b', 11)],
    'loai_dat': [(r'\bloai dat\b', 10), (r'\bmuc dich( su dung)?\b', 9), (r'\bmdsd\b', 9), (r'\bky hieu\b', 6)],
    'nguon_goc': [(r'\bnguon goc\b', 10)],
    'vi_tri': [(r'\bvi tri\b', 10)],
    'ghi_chu': [(r'\bghi chu\b', 10)],
    'nhan_khau': [(r'\b(so )?nhan khau\b', 10), (r'\bso (khau|nguoi)\b', 8)],
}
LOAI_TRU = {
    'ho_ten': r'\bdia chi\b|\bdat\b.*\bloai\b',
    'so_to': r'\btong\b|\bdan pho\b|\bdia chi\b|\bho ten\b',
    'so_thua': r'\bdien tich\b|\bdt\b|\bloai\b|\bthu hoi\b',
    'dt_thu_hoi': r'\bban do\b|\bcon lai\b|\bngoai\b|\bthua dat\b.*\btong\b',
    'dia_chi': r'\bthua\b|\bdat\b',
}
BAT_BUOC = ('ho_ten',)
CAN_MOT = ('so_to', 'so_thua', 'dt_thu_hoi')        # phải có ít nhất một trong số này
# "Tổng cộng", "Cộng: 25 hộ"... nhưng không bắt họ Tống ("tong van a")
DONG_CONG = re.compile(r'^(tong cong|cong tong|tong so|tong|cong)\s*[:.]?\s*(\d.*|\(.*|(so )?(ho|thua|dien tich|dt)\b.*)?$')


@dataclass
class BoCot:
    sheet: str
    dong_tieu_de: list                 # số dòng (1-based) của khối tiêu đề
    cot: dict                          # trường -> chỉ số cột (0-based)
    tieu_de: dict = field(default_factory=dict)   # trường -> tên cột gốc
    diem: int = 0


def _gia_tri_luoi(ws):
    """Đọc sheet thành lưới giá trị, ô gộp được điền giá trị ô đầu (tiêu đề gộp, họ tên gộp nhiều thửa)."""
    luoi = [list(r) for r in ws.iter_rows(values_only=True)]
    rong = max((len(r) for r in luoi), default=0)
    for r in luoi:
        r.extend([None] * (rong - len(r)))
    gop = {}
    for vung in ws.merged_cells.ranges:
        v = luoi[vung.min_row - 1][vung.min_col - 1] if vung.min_row - 1 < len(luoi) else None
        for i in range(vung.min_row, min(vung.max_row, len(luoi)) + 1):
            for j in range(vung.min_col, vung.max_col + 1):
                luoi[i - 1][j - 1] = v
                gop[(i, j)] = vung.max_col - vung.min_col + 1
    return luoi, gop, rong


def _diem_cot(text: str):
    """Tiêu đề một cột -> {trường: điểm}."""
    kq = {}
    if not text:
        return kq
    for truong, mau in MAU_COT.items():
        if truong in LOAI_TRU and re.search(LOAI_TRU[truong], text) and truong != 'dt_ban_do':
            continue
        d = max((dm for m, dm in mau if re.search(m, text)), default=0)
        if d:
            kq[truong] = d
    return kq


def _gan_cot(tieu_de: list):
    """Gán mỗi trường một cột (điểm cao trước, mỗi cột một trường)."""
    ung = sorted(((d, -j, truong, j) for j, t in enumerate(tieu_de) for truong, d in _diem_cot(t).items()), reverse=True)
    cot, da_dung = {}, set()
    for d, _, truong, j in ung:
        if truong not in cot and j not in da_dung:
            cot[truong] = j
            da_dung.add(j)
    return cot


def _tieu_de_khoi(luoi, gop, rong, dau: int, so_dong: int):
    """Ghép tiêu đề cột của khối dòng dau..dau+so_dong-1 (bỏ ô gộp rộng như tên bảng)."""
    td = []
    for j in range(rong):
        phan = []
        for i in range(dau, dau + so_dong):
            if gop.get((i, j + 1), 1) > max(3, rong * 0.6):
                continue
            t = chuan_hoa(luoi[i - 1][j]) if luoi[i - 1][j] is not None else ''
            if t and t not in phan:
                phan.append(t)
        td.append(' '.join(phan))
    return td


def tim_cot(wb, so_dong_quet: int = 30) -> BoCot | None:
    """Tìm sheet + khối tiêu đề có điểm cao nhất."""
    tot = None
    for ws in wb.worksheets:
        if ws.sheet_state != 'visible':
            continue
        luoi, gop, rong = _gia_tri_luoi(ws)
        for dau in range(1, min(so_dong_quet, len(luoi)) + 1):
            for so_dong in (1, 2, 3):
                if dau + so_dong - 1 > len(luoi):
                    break
                td = _tieu_de_khoi(luoi, gop, rong, dau, so_dong)
                cot = _gan_cot(td)
                if not all(k in cot for k in BAT_BUOC) or not any(k in cot for k in CAN_MOT):
                    continue
                diem = sum(_diem_cot(td[j])[k] for k, j in cot.items()) - so_dong   # ưu tiên khối ngắn khi bằng điểm
                if tot is None or diem > tot.diem:
                    goc = {k: ' '.join(' '.join(str(luoi[i - 1][j] or '') for i in range(dau, dau + so_dong)).split())
                           for k, j in cot.items()}
                    tot = BoCot(ws.title, list(range(dau, dau + so_dong)), cot, goc, diem)
    return tot


def _la_dong_danh_so(r) -> bool:
    """Dòng đánh số cột (1), (2), (3)... hoặc 1, 2, 3... ngay dưới tiêu đề."""
    so = []
    for v in r:
        if v in (None, ''):
            continue
        if isinstance(v, float) and v.is_integer():
            v = int(v)
        m = re.fullmatch(r'\(?(\d{1,2})\)?', str(v).strip())
        if not m:
            return False
        so.append(int(m.group(1)))
    return len(so) >= 3 and so == sorted(so) and so[-1] - so[0] == len(so) - 1


def _ma_so(v) -> str:
    """Số tờ / số thửa: 35 -> '35'; '382\\n(164 cũ)' -> '382 (164 cũ)'."""
    return ' '.join(_txt(v).split())


def _doc_dt(v):
    """Diện tích: số, '1.070,5', '215,1 m2' -> Decimal; rỗng -> None; không đọc được -> ValueError."""
    if v is None or (isinstance(v, str) and not v.strip()):
        return None
    if isinstance(v, (int, float)):
        return D(v)
    s = re.sub(r'(m2|m²|ha)\s*$', '', str(v).strip(), flags=re.I).strip()
    return doc_so_vn(s)                             # '1.070' = 1.070 m² (trước đây đọc thành 1,07)


@dataclass
class KetQuaDoc:
    bo_cot: BoCot | None
    ho: list = field(default_factory=list)
    thua: list = field(default_factory=list)
    loi: list = field(default_factory=list)
    canh_bao: list = field(default_factory=list)
    tieu_de_bang: str = ''


def doc(file_excel) -> KetQuaDoc:
    """Đọc file Excel bất kỳ -> danh sách hộ, thửa (chưa ghi gì)."""
    wb = openpyxl.load_workbook(str(file_excel), data_only=True)
    try:
        bc = tim_cot(wb)
        kq = KetQuaDoc(bc)
        if bc is None:
            kq.loi.append('Không tìm thấy bảng có cột HỌ TÊN và cột TỜ / THỬA / DIỆN TÍCH THU HỒI trong file.')
            return kq
        ws = wb[bc.sheet]
        luoi, _, _ = _gia_tri_luoi(ws)
    finally:
        wb.close()
    c = bc.cot
    # tên bảng (dòng chữ phía trên tiêu đề) -> tên dự án: ưu tiên dòng có chữ "dự án"
    dong_tren = []
    for i in range(1, bc.dong_tieu_de[0]):
        chu = [' '.join(str(v).split()) for v in luoi[i - 1] if isinstance(v, str) and v.strip()]
        if chu and chu[0] not in dong_tren:
            dong_tren.append(chu[0])
    kq.tieu_de_bang = next((t for t in dong_tren if 'du an' in chuan_hoa(t)), dong_tren[0] if dong_tren else '')
    g = lambda r, k: r[c[k]] if k in c and c[k] < len(r) else None

    theo_khoa, truoc = {}, None
    for i in range(bc.dong_tieu_de[-1] + 1, len(luoi) + 1):
        r = luoi[i - 1]
        if not any(v not in (None, '') and str(v).strip() for v in r):
            continue
        if _la_dong_danh_so(r):
            continue
        ten = ' '.join(_txt(g(r, 'ho_ten')).split())
        to, thua, dt_tho = _ma_so(g(r, 'so_to')), _ma_so(g(r, 'so_thua')), g(r, 'dt_thu_hoi')
        if any(DONG_CONG.match(chuan_hoa(v)) for v in r if isinstance(v, str)):
            continue
        if chuan_hoa(ten) == chuan_hoa(bc.tieu_de.get('ho_ten', '')):          # tiêu đề lặp lại giữa bảng
            continue
        co_thua = bool(to or thua or _txt(dt_tho))
        if not ten:
            if co_thua and truoc is not None:                                # dòng tiếp theo của hộ phía trên
                h = truoc
            else:
                continue
        else:
            stt = _txt(g(r, 'stt'))
            if not co_thua and not _txt(g(r, 'dia_chi')) and stt and not stt.isdigit():
                continue                                                     # dòng nhóm: "I", "A", "Ấp 8"...
            cccd = chuan_cccd(g(r, 'so_cccd'))
            dc = ' '.join(_txt(g(r, 'dia_chi')).split())
            khoa = ('cccd', cccd) if cccd else ('ten', chuan_hoa(ten), chuan_hoa(dc))
            h = theo_khoa.get(khoa)
            if h is None:
                h = dict(ma_ho=len(kq.ho) + 1, ho_ten=ten, so_cccd=cccd, ngay_cap=_txt(g(r, 'ngay_cap')),
                         noi_cap=_txt(g(r, 'noi_cap')), dia_chi=dc, dien_thoai=_txt(g(r, 'dien_thoai')),
                         nhan_khau=_txt(g(r, 'nhan_khau')), ghi_chu=[], dong=i)
                theo_khoa[khoa] = h
                kq.ho.append(h)
            else:
                h['dien_thoai'] = h['dien_thoai'] or _txt(g(r, 'dien_thoai'))
        truoc = h
        gc = ' '.join(_txt(g(r, 'ghi_chu')).split())
        if gc and gc not in h['ghi_chu']:
            h['ghi_chu'].append(gc)
        if not co_thua:
            kq.canh_bao.append(f'Dòng {i}: {ten} - không có tờ, thửa, diện tích (chỉ tạo hộ, chưa có thửa).')
            continue
        try:
            dt = _doc_dt(dt_tho)
        except ValueError:
            kq.canh_bao.append(f'Dòng {i}: {h["ho_ten"]} - không đọc được diện tích {_txt(dt_tho)!r}, ghi 0.')
            dt = None
        dt_bd = None
        try:
            dt_bd = _doc_dt(g(r, 'dt_ban_do'))
        except ValueError:
            pass
        if dt is None and dt_bd is not None:
            dt = dt_bd
            kq.canh_bao.append(f'Dòng {i}: {h["ho_ten"]} tờ {to} thửa {thua} - không có DT thu hồi, lấy DT bản đồ {chuoi(dt_bd)}.')
        elif dt_bd is not None and dt_bd != dt:
            h['ghi_chu'].append(f'Tờ {to} thửa {thua}: DT thu hồi bản đồ {chuoi(dt_bd)} m²')
        if dt is None:
            kq.canh_bao.append(f'Dòng {i}: {h["ho_ten"]} tờ {to} thửa {thua} - chưa có diện tích thu hồi (ghi 0).')
        loai = re.sub(r'\s*\+\s*', '+', ' '.join(_txt(g(r, 'loai_dat')).split()))
        if not loai:
            kq.canh_bao.append(f'Dòng {i}: {h["ho_ten"]} tờ {to} thửa {thua} - chưa có loại đất.')
        if not to or not thua:
            kq.canh_bao.append(f'Dòng {i}: {h["ho_ten"]} - thiếu {"số tờ" if not to else "số thửa"}.')
        kq.thua.append(dict(ma_thua=len(kq.thua) + 1, ma_ho=h['ma_ho'], so_to=to, so_thua=thua, loai_dat=loai,
                            dt_thu_hoi=chuoi(dt) if dt is not None else '0', nguon_goc=_txt(g(r, 'nguon_goc')),
                            vi_tri=' '.join(_txt(g(r, 'vi_tri')).split()), thu_tu=len(kq.thua) + 1, dong=i))

    # kiểm tra
    if not kq.ho:
        kq.loi.append(f'Sheet {bc.sheet}: không có dòng hộ nào dưới tiêu đề (dòng {bc.dong_tieu_de[-1]}).')
    theo_ten = {}
    for h in kq.ho:
        theo_ten.setdefault(chuan_hoa(h['ho_ten']), []).append(h)
    for ds in theo_ten.values():
        if len(ds) > 1 and len({chuan_hoa(h['dia_chi']) for h in ds}) > 1:
            kq.canh_bao.append(f'{ds[0]["ho_ten"]}: cùng họ tên, khác địa chỉ -> tách {len(ds)} hộ (mã '
                               + ', '.join(str(h['ma_ho']) for h in ds) + '); gộp lại nếu là một người.')
    theo_thua = {}
    for t in kq.thua:
        if t['so_to'] and t['so_thua']:
            theo_thua.setdefault((t['so_to'], t['so_thua']), []).append(t)
    ten = {h['ma_ho']: h['ho_ten'] for h in kq.ho}
    for (to, so), ds in theo_thua.items():
        if len({t['ma_ho'] for t in ds}) > 1:
            kq.canh_bao.append(f'Tờ {to} thửa {so} có {len(ds)} hộ: ' + ', '.join(ten[t['ma_ho']] for t in ds)
                               + ' (đồng sử dụng hoặc trùng - xem lại).')
    return kq


def la_file_pabt(file_excel) -> bool:
    """File theo mẫu PABT Excel (.xlsm có DB_HO, DB_THUA...) thì nhập bằng nhap_excel, còn lại nhập bằng module này."""
    wb = openpyxl.load_workbook(str(file_excel), read_only=True)
    try:
        return all(s in wb.sheetnames for s in ('DB_HO', 'DB_THUA', 'DB_DATCT'))
    finally:
        wb.close()


def mo_ta_cot(bo: BoCot) -> str:
    ten = dict(stt='STT', ho_ten='Họ tên', dia_chi='Địa chỉ', so_cccd='CCCD', ngay_cap='Ngày cấp', noi_cap='Nơi cấp',
               dien_thoai='Điện thoại', so_to='Tờ', so_thua='Thửa', dt_thu_hoi='DT thu hồi', dt_ban_do='DT bản đồ',
               loai_dat='Loại đất', nguon_goc='Nguồn gốc', vi_tri='Vị trí', ghi_chu='Ghi chú')
    return (f'sheet "{bo.sheet}", tiêu đề dòng {bo.dong_tieu_de[0]}'
            + (f'-{bo.dong_tieu_de[-1]}' if len(bo.dong_tieu_de) > 1 else '') + ': '
            + '; '.join(f'{ten.get(k, k)} = "{bo.tieu_de[k]}"' for k in sorted(bo.cot, key=bo.cot.get)))


def dia_ban_tu_ten(ten: str) -> tuple:
    """'Dự án ĐT762 đoạn qua xã Bàu Hàm' -> ('Xã', 'Bàu Hàm'); không thấy thì ('Phường', '')."""
    m = re.search(r'\b(xã|phường|thị trấn)\s+([^,;()\n]+)', ten, re.I)
    if not m:
        return 'Phường', ''
    return m.group(1).capitalize(), ' '.join(m.group(2).split())


DU_LIEU_HO = ('doi_thoai_ho', 'y_kien_du_thao', 'dot_du_thao', 'qd_ho', 'quyet_dinh', 'ct_dat', 'ct_khoan', 'thua', 'ho',
              'tong_excel', 'nhat_ky', 'tho_nhap', 'dot_trinh')


TRUONG_DON_VI = csdl.TRUONG_DON_VI


def xoa_trang(con) -> None:
    """Xóa toàn bộ hồ sơ dự án (hộ, thửa, phương án, tổng Excel, nhật ký, thông tin dự án);
    giữ danh mục, tham số và thông tin đơn vị lập, người ký."""
    giu = TRUONG_DON_VI + ('phien_ban_gia',)          # thông tin đơn vị, người ký, phiên bản bộ đơn giá đang áp
    dv = con.execute(f'SELECT {", ".join(giu)} FROM du_an WHERE id = 1').fetchone()
    from . import van_dong
    van_dong.xoa_het(con)                              # sổ nhật ký vận động (bảng tạo khi cần) - xóa trước hộ
    for b in DU_LIEU_HO:
        con.execute(f'DELETE FROM {b}')
    con.execute('DELETE FROM du_an')
    con.execute('INSERT INTO du_an (id) VALUES (1)')
    if dv is not None:
        con.execute(f'UPDATE du_an SET {", ".join(k + " = ?" for k in giu)} WHERE id = 1', tuple(dv))


def nhap(file_excel, file_pabt, ten_du_an: str = '', danh_muc=None) -> BaoCaoNhap:
    """Đọc file Excel bất kỳ và ghi vào file_pabt (xóa trắng hồ sơ cũ, giữ danh mục).

    file_pabt chưa có: tạo mới; nếu có danh_muc (một file .pabt khác) thì chép danh mục, tham số từ đó.
    Có lỗi chặn thì không ghi gì.
    """
    kq = doc(file_excel)
    bc = BaoCaoNhap(file_excel=str(file_excel), file_pabt=str(file_pabt), loi=kq.loi, canh_bao=kq.canh_bao)
    if kq.loi:
        return bc
    p = Path(file_pabt)
    moi = not p.exists()
    con = csdl.mo(p, tao=True)
    try:
        if moi and danh_muc:
            _chep_danh_muc(con, danh_muc)
        elif moi:
            from . import don_gia
            from .to_chuc import MAC_DINH
            don_gia.ap_vao_du_an(con)
            with con:
                con.execute(f'UPDATE du_an SET {", ".join(k + " = ?" for k in MAC_DINH)} WHERE id = 1', tuple(MAC_DINH.values()))
        with con:
            xoa_trang(con)
            ten = ten_du_an or kq.tieu_de_bang or Path(file_excel).stem
            cap, dia_ban = dia_ban_tu_ten(ten)
            con.execute('UPDATE du_an SET ten=?, ten_day_du=?, cap_dia_ban=?, ten_dia_ban=?, nguon_nhap=?, ngay_nhap=? WHERE id=1',
                        (ten, ten, cap, dia_ban, Path(file_excel).name, datetime.now().isoformat(timespec='seconds')))
            for i, h in enumerate(kq.ho, start=1):
                con.execute('''INSERT INTO ho (ma_ho, thu_tu, ho_ten, so_cccd, ngay_cap, noi_cap, dia_chi, dien_thoai, ghi_chu)
                               VALUES (?,?,?,?,?,?,?,?,?)''',
                            (h['ma_ho'], i, h['ho_ten'], h['so_cccd'], h['ngay_cap'], h['noi_cap'], h['dia_chi'],
                             h['dien_thoai'], '; '.join(h['ghi_chu'])))
            con.executemany('''INSERT INTO thua (ma_thua, ma_ho, so_to, so_thua, loai_dat, dt_thu_hoi, nguon_goc, vi_tri, thu_tu)
                               VALUES (:ma_thua,:ma_ho,:so_to,:so_thua,:loai_dat,:dt_thu_hoi,:nguon_goc,:vi_tri,:thu_tu)''', kq.thua)
            bo = kq.bo_cot
            csdl.ghi_nhat_ky(con, 'Nhập danh sách Excel (tự nhận cột)',
                             f'{Path(file_excel).name}: {len(kq.ho)} hộ, {len(kq.thua)} thửa; {mo_ta_cot(bo)}')
    finally:
        con.close()
    bc.so_ho, bc.so_thua = len(kq.ho), len(kq.thua)
    bc.so_dong = {1: 0, 2: 0, 3: 0, 4: 0}
    bc.nhan_cot = mo_ta_cot(kq.bo_cot)
    return bc


DANH_MUC = csdl.DANH_MUC
_chep_danh_muc = csdl.chep_danh_muc


def nap_danh_muc(file_pabt, file_excel) -> dict:
    """Nạp danh mục đơn giá, tham số, biểu thưởng, giá đất… từ một file PABT Excel (.xlsm) vào file dự án:
    thay danh mục cũ, GIỮ NGUYÊN hồ sơ hộ, thửa, phương án. Trả số mục từng danh mục."""
    if not la_file_pabt(file_excel):
        raise LoiNhap('File không theo mẫu PABT Excel (cần các sheet DM_HOTRO, DG_NHANUOC, THAM_SO…).')
    with tempfile.TemporaryDirectory() as td:
        tam = Path(td) / 'danh_muc.pabt'
        bc = nhap_excel.nhap(file_excel, tam)
        if bc.loi:
            raise LoiNhap('Không đọc được danh mục:\n' + '\n'.join(bc.loi))
        con = csdl.mo(file_pabt)
        try:
            _chep_danh_muc(con, tam, don_vi=False)
            dem = {b: con.execute(f'SELECT COUNT(*) FROM {b}').fetchone()[0] for b in DANH_MUC}
            with con:
                csdl.ghi_nhat_ky(con, 'Nạp danh mục đơn giá', f'{Path(file_excel).name}: ' +
                                 ', '.join(f'{b} {n}' for b, n in dem.items()))
        finally:
            con.close()
    return dem

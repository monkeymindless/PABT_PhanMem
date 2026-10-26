"""Dự thảo phương án bồi thường: đợt niêm yết, lấy ý kiến, đối thoại, hộ vướng pháp lý.

Niêm yết công khai 10 ngày, đối thoại không quá 30 ngày (Luật Đất đai 2024, Nghị định 88/2024/NĐ-CP,
Quyết định 18/2026/QĐ-UBND). Hộ chưa đủ điều kiện hoặc đang vướng không đưa vào đợt lấy ý kiến.
Ba tỷ lệ đồng thuận tách riêng: theo đợt đang chọn, lũy kế các đợt đã niêm yết, độ bao phủ cả dự án.
"""
from __future__ import annotations
from datetime import datetime, timedelta
from pathlib import Path

from . import an_toan as _an_toan
from .lap_pa import LoiNhap, ho_nhan_viec, kiem_ds_ho_nhan_viec, kiem_ho_nhan_viec
from .tien import vn

# số ngày niêm yết / đối thoại: hồ sơ địa phương (pabt_profile.json mục thoi_han.niem_yet / doi_thoai - mặc định 10 / 30)
SO_NGAY_NIEM_YET = 10
SO_NGAY_DOI_THOAI = 30


def _ap_ho_so(hs: dict) -> None:
    global SO_NGAY_NIEM_YET, SO_NGAY_DOI_THOAI
    SO_NGAY_NIEM_YET = hs['thoi_han']['niem_yet']['so_ngay']
    SO_NGAY_DOI_THOAI = hs['thoi_han']['doi_thoai']['so_ngay']


def _dang_ky_ho_so() -> None:
    from . import dia_phuong
    dia_phuong.dang_ky(_ap_ho_so)


_dang_ky_ho_so()
NHOM_VUONG = (
    ('V1', 'Chờ UBND cấp xã xác nhận nguồn gốc đất'),
    ('V2', 'Tranh chấp ranh giới thửa'),
    ('V3', 'Thừa kế chưa phân chia, chưa có người đại diện'),
    ('V4', 'Sai lệch hồ sơ đo đạc, chờ đo lại'),
    ('V5', 'Tài sản đặc biệt chờ thẩm định giá'),
)
TEN_VUONG = dict(NHOM_VUONG)
LOAI_Y_KIEN = (
    ('chua', 'Chưa lấy ý kiến'),
    ('dong_y', 'Đồng ý'),
    ('y_kien_khac', 'Ý kiến khác'),
    ('khong_dong_y', 'Không đồng ý'),
)
TEN_LOAI = dict(LOAI_Y_KIEN)
NHOM_KIEN_NGHI = (
    ('', ''),
    ('gia_dat', 'Đơn giá đất'),
    ('nha', 'Nhà, công trình'),
    ('cay', 'Cây trồng, mật độ'),
    ('ho_tro', 'Chính sách hỗ trợ'),
    ('tai_dinh_cu', 'Suất tái định cư'),
    ('khac', 'Khác'),
)
TEN_NHOM = dict(NHOM_KIEN_NGHI)


def doc_ngay(chu: str) -> datetime:
    s = (chu or '').strip()
    for fmt in ('%Y-%m-%d', '%d/%m/%Y', '%d-%m-%Y'):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    raise LoiNhap('Ngày không đúng. Gõ theo dạng 11/10/2026.')


def ngay_iso(d: datetime) -> str:
    return d.strftime('%Y-%m-%d')


def hien_ngay(iso: str) -> str:
    if not iso:
        return ''
    try:
        return doc_ngay(iso).strftime('%d/%m/%Y')
    except LoiNhap:
        return iso


def ngay_ket_thuc(ngay_bat_dau: str) -> str:
    return ngay_iso(doc_ngay(ngay_bat_dau) + timedelta(days=SO_NGAY_NIEM_YET))


def han_doi_thoai(ngay_hop: str) -> str:
    return ngay_iso(doc_ngay(ngay_hop) + timedelta(days=SO_NGAY_DOI_THOAI))


def _pt(tu: int, mau: int) -> float:
    return (tu / mau * 100) if mau else 0.0


def ds_dot(con) -> list:
    return [dict(r) for r in con.execute('SELECT * FROM dot_du_thao ORDER BY id')]


def thong_ke_phieu(con) -> dict:
    """Sáu mắt xích của cả dự án. Mẫu số của mọi tỷ lệ là tổng số hộ."""
    tong = con.execute('SELECT COUNT(*) FROM ho').fetchone()[0]
    du = con.execute('SELECT COUNT(*) FROM ho WHERE du_dieu_kien = 1').fetchone()[0]
    vuong = con.execute("SELECT COUNT(*) FROM ho WHERE TRIM(ma_vuong) <> ''").fetchone()[0]
    da_dt = con.execute('SELECT COUNT(DISTINCT ma_ho) FROM y_kien_du_thao').fetchone()[0]
    pd = con.execute('SELECT COUNT(*) FROM ho WHERE da_phe_duyet = 1').fetchone()[0]
    bg = con.execute('SELECT COUNT(*) FROM ho WHERE da_ban_giao = 1').fetchone()[0]
    return dict(tong=tong, du_dieu_kien=du, vuong=vuong, da_du_thao=da_dt, phe_duyet=pd, ban_giao=bg,
                pt_du=_pt(du, tong), pt_vuong=_pt(vuong, tong), pt_du_thao=_pt(da_dt, tong),
                pt_phe_duyet=_pt(pd, tong), pt_ban_giao=_pt(bg, tong))


def thong_ke_y_kien(con, dot_id=None) -> dict:
    """Ba góc nhìn: đợt đang chọn, lũy kế hộ đã đưa ra niêm yết, độ bao phủ trên tổng hộ của dự án.

    Hộ trong đợt mới tạo có loại 'chua' — không tính là đồng ý. Tỷ lệ đợt = số đồng ý / số hộ của đợt.
    """
    tong_da = con.execute('SELECT COUNT(*) FROM ho').fetchone()[0]
    if dot_id:
        dem_rows = con.execute('SELECT loai, COUNT(*) FROM y_kien_du_thao WHERE dot_id = ? GROUP BY loai', (dot_id,))
        n_dot = con.execute('SELECT COUNT(*) FROM y_kien_du_thao WHERE dot_id = ?', (dot_id,)).fetchone()[0]
    else:
        dem_rows = con.execute('SELECT loai, COUNT(*) FROM y_kien_du_thao GROUP BY loai')
        n_dot = con.execute('SELECT COUNT(*) FROM y_kien_du_thao').fetchone()[0]
    dem = {r[0]: r[1] for r in dem_rows}
    dong = dem.get('dong_y', 0)
    khac = dem.get('y_kien_khac', 0)
    khong = dem.get('khong_dong_y', 0)
    chua = dem.get('chua', 0)
    luy_dong = con.execute("SELECT COUNT(DISTINCT ma_ho) FROM y_kien_du_thao WHERE loai = 'dong_y'").fetchone()[0]
    luy_ny = con.execute('SELECT COUNT(DISTINCT ma_ho) FROM y_kien_du_thao').fetchone()[0]
    return dict(dong_y=dong, y_kien_khac=khac, khong_dong_y=khong, chua=chua, so_ho_dot=n_dot,
                pt_dot=_pt(dong, n_dot), luy_dong=luy_dong, luy_ny=luy_ny, pt_luy=_pt(luy_dong, luy_ny),
                tong_du_an=tong_da, pt_bao_phu=_pt(luy_dong, tong_da))


def goi_y_du_dieu_kien(con) -> int:
    """Đánh dấu đủ điều kiện các hộ đã có tên, nguồn gốc thửa, không ghi tranh chấp, không đang vướng, và đã có phương án.
    Đây là gợi ý để rà — người dùng vẫn đối chiếu 4 điều kiện pháp lý trước khi niêm yết."""
    from . import csdl
    ds = [r[0] for r in con.execute('''
        SELECT h.ma_ho FROM ho h
        WHERE h.du_dieu_kien = 0 AND TRIM(h.ma_vuong) = '' AND TRIM(h.ho_ten) <> '' AND TRIM(h.tranh_chap) = ''
          AND EXISTS (SELECT 1 FROM thua t WHERE t.ma_ho = h.ma_ho AND TRIM(t.nguon_goc) <> '')
          AND (TRIM(IFNULL(h.luu_luc, '')) <> '' OR EXISTS (SELECT 1 FROM ct_dat d WHERE d.ma_ho = h.ma_ho))
    ''')]
    if not ds:
        return 0
    with csdl.giao_dich(con):
        for ma in ds:
            con.execute('UPDATE ho SET du_dieu_kien = 1 WHERE ma_ho = ?', (ma,))
        csdl.ghi_nhat_ky(con, 'Gợi ý đủ điều kiện dự thảo', f'{len(ds)} hộ')
    return len(ds)


def ghi_phap_ly(con, ma_ho: int, du_dieu_kien: int, ma_vuong: str, ghi_chu: str) -> None:
    from . import csdl
    kiem_ho_nhan_viec(con, ma_ho)
    ma_vuong = (ma_vuong or '').strip().upper()
    if ma_vuong and ma_vuong not in TEN_VUONG:
        raise LoiNhap('Nhóm vướng không đúng. Chọn V1 đến V5, hoặc để trống nếu hết vướng.')
    if ma_vuong:
        du_dieu_kien = 0
    with csdl.giao_dich(con):
        con.execute('UPDATE ho SET du_dieu_kien = ?, ma_vuong = ?, ghi_chu_phap_ly = ? WHERE ma_ho = ?',
                    (1 if du_dieu_kien else 0, ma_vuong, (ghi_chu or '').strip(), ma_ho))
        csdl.ghi_nhat_ky(con, 'Rà soát pháp lý dự thảo', f'Hộ {ma_ho}: {"đủ điều kiện" if du_dieu_kien and not ma_vuong else TEN_VUONG.get(ma_vuong, "chưa đủ")}')


def tao_dot(con, ten: str, ngay_bat_dau: str, dia_diem: str) -> int:
    from . import csdl
    ten = (ten or '').strip()
    if not ten:
        raise LoiNhap('Nhập tên đợt dự thảo.')
    bd = ngay_iso(doc_ngay(ngay_bat_dau))
    kt = ngay_ket_thuc(bd)
    with csdl.giao_dich(con):
        cur = con.execute('''INSERT INTO dot_du_thao (ten, ngay_bat_dau, ngay_ket_thuc, dia_diem, trang_thai)
                             VALUES (?, ?, ?, ?, 'dang_niem_yet')''', (ten, bd, kt, (dia_diem or '').strip()))
        csdl.ghi_nhat_ky(con, 'Tạo đợt dự thảo', f'{ten}: niêm yết {hien_ngay(bd)} – {hien_ngay(kt)}')
        return cur.lastrowid


def dat_ngay_hop(con, dot_id: int, ngay_hop: str) -> str:
    from . import csdl
    han = han_doi_thoai(ngay_hop)
    hop = ngay_iso(doc_ngay(ngay_hop))
    with csdl.giao_dich(con):
        con.execute("UPDATE dot_du_thao SET ngay_hop = ?, han_doi_thoai = ?, trang_thai = 'da_hop' WHERE id = ?",
                    (hop, han, dot_id))
        csdl.ghi_nhat_ky(con, 'Ngày họp lấy ý kiến', f'Đợt {dot_id}: {hien_ngay(hop)}, hạn đối thoại {hien_ngay(han)}')
    return han


def ds_de_them(con, dot_id: int, loc: str, dot_nguon: int | None = None) -> list:
    """Hộ có thể thêm thủ công vào đợt đang chọn (chưa nằm trong đợt đó).

    loc: 'du' đủ điều kiện; 'dot' hộ của một đợt khác; 'chua' chưa lấy ý kiến;
    'khong_dong_y' chưa đồng thuận; 'y_kien_khac' có ý kiến khác.
    """
    da_co = {r[0] for r in con.execute('SELECT ma_ho FROM y_kien_du_thao WHERE dot_id = ?', (dot_id,))}
    if loc == 'du':
        rows = con.execute('''SELECT ma_ho, thu_tu, ho_ten, ma_vuong FROM ho
            WHERE du_dieu_kien = 1 AND TRIM(ma_vuong) = '' ORDER BY thu_tu, ma_ho''')
        nhan = 'Đủ điều kiện'
    elif loc == 'dot':
        rows = con.execute('''SELECT h.ma_ho, h.thu_tu, h.ho_ten, h.ma_vuong
            FROM y_kien_du_thao y JOIN ho h ON h.ma_ho = y.ma_ho
            WHERE y.dot_id = ? ORDER BY h.thu_tu, h.ma_ho''', (dot_nguon,))
        ten = con.execute('SELECT ten FROM dot_du_thao WHERE id = ?', (dot_nguon,)).fetchone()
        nhan = ten['ten'] if ten else 'Đợt khác'
    elif loc == 'chua':
        rows = con.execute('''SELECT ma_ho, thu_tu, ho_ten, ma_vuong FROM ho h
            WHERE NOT EXISTS (
                SELECT 1 FROM y_kien_du_thao y WHERE y.ma_ho = h.ma_ho AND y.loai <> 'chua')
            ORDER BY thu_tu, ma_ho''')
        nhan = 'Chưa lấy ý kiến'
    elif loc == 'khong_dong_y':
        rows = con.execute('''SELECT DISTINCT h.ma_ho, h.thu_tu, h.ho_ten, h.ma_vuong
            FROM y_kien_du_thao y JOIN ho h ON h.ma_ho = y.ma_ho
            WHERE y.loai = 'khong_dong_y' ORDER BY h.thu_tu, h.ma_ho''')
        nhan = 'Chưa đồng thuận'
    elif loc == 'y_kien_khac':
        rows = con.execute('''SELECT DISTINCT h.ma_ho, h.thu_tu, h.ho_ten, h.ma_vuong
            FROM y_kien_du_thao y JOIN ho h ON h.ma_ho = y.ma_ho
            WHERE y.loai = 'y_kien_khac' ORDER BY h.thu_tu, h.ma_ho''')
        nhan = 'Ý kiến khác'
    else:
        return []
    kq = []
    for r in rows:
        if r['ma_ho'] in da_co:
            continue
        kq.append(dict(ma_ho=r['ma_ho'], ho_ten=r['ho_ten'], thua=_thua(con, r['ma_ho']),
                       vuong=(r['ma_vuong'] or '').strip(), nhan=nhan))
    return kq


def them_thu_cong(con, dot_id: int, ds_ma_ho: list) -> tuple:
    """Thêm đúng các hộ đã chọn vào đợt. Hộ đang vướng hoặc đã có trong đợt thì bỏ qua. Trả (thêm, bỏ qua)."""
    from . import csdl
    kiem_ds_ho_nhan_viec(con, ds_ma_ho)
    them, bo = 0, 0
    gio = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    with csdl.giao_dich(con):
        for ma in ds_ma_ho:
            h = con.execute('SELECT ma_vuong FROM ho WHERE ma_ho = ?', (ma,)).fetchone()
            if h is None or (h['ma_vuong'] or '').strip():
                bo += 1
                continue
            if con.execute('SELECT 1 FROM y_kien_du_thao WHERE dot_id = ? AND ma_ho = ?', (dot_id, ma)).fetchone():
                bo += 1
                continue
            con.execute('''INSERT INTO y_kien_du_thao (dot_id, ma_ho, loai, ngay_cap_nhat) VALUES (?, ?, 'chua', ?)''',
                        (dot_id, ma, gio))
            con.execute('UPDATE ho SET dot_du_thao_id = ? WHERE ma_ho = ?', (dot_id, ma))
            them += 1
        csdl.ghi_nhat_ky(con, 'Thêm hộ vào đợt dự thảo', f'Đợt {dot_id}: thêm {them} hộ, bỏ qua {bo}')
    return them, bo


def dua_ho_vao_dot(con, dot_id: int, ds_ma_ho=None) -> tuple:
    """Đưa hộ đủ điều kiện, không vướng, chưa có trong đợt. Trả (số thêm, số bỏ qua)."""
    from . import csdl
    if ds_ma_ho is None:
        ds_ma_ho = [r[0] for r in con.execute('SELECT ma_ho FROM ho ORDER BY thu_tu, ma_ho')]
        nhan = ho_nhan_viec(con)            # bản offline theo hộ: "Thêm toàn bộ hộ đủ điều kiện" = các hộ đã nhận việc
        if nhan is not None:
            ds_ma_ho = [m for m in ds_ma_ho if m in nhan]
    kiem_ds_ho_nhan_viec(con, ds_ma_ho)
    them, bo = 0, 0
    gio = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    with csdl.giao_dich(con):
        for ma in ds_ma_ho:
            h = con.execute('SELECT du_dieu_kien, ma_vuong FROM ho WHERE ma_ho = ?', (ma,)).fetchone()
            if h is None or not h['du_dieu_kien'] or (h['ma_vuong'] or '').strip():
                bo += 1
                continue
            if con.execute('SELECT 1 FROM y_kien_du_thao WHERE dot_id = ? AND ma_ho = ?', (dot_id, ma)).fetchone():
                bo += 1
                continue
            con.execute('''INSERT INTO y_kien_du_thao (dot_id, ma_ho, loai, ngay_cap_nhat) VALUES (?, ?, 'chua', ?)''',
                        (dot_id, ma, gio))
            con.execute('UPDATE ho SET dot_du_thao_id = ? WHERE ma_ho = ?', (dot_id, ma))
            them += 1
        csdl.ghi_nhat_ky(con, 'Đưa hộ vào đợt dự thảo', f'Đợt {dot_id}: thêm {them} hộ, bỏ qua {bo}')
    return them, bo


def ghi_y_kien(con, dot_id: int, ma_ho: int, loai: str, nhom: str, noi_dung: str,
               huong: str = '', tien_chenh: str = '0', ket_qua: str = '') -> None:
    from . import csdl
    from .tien import doc_so_vn
    kiem_ho_nhan_viec(con, ma_ho)
    if loai not in TEN_LOAI or loai == '':
        raise LoiNhap('Chọn loại ý kiến.')
    if nhom and nhom not in TEN_NHOM:
        raise LoiNhap('Nhóm kiến nghị không đúng.')
    try:
        tien = str(doc_so_vn(tien_chenh or '0'))
    except (ValueError, ArithmeticError):
        raise LoiNhap('Số tiền chênh lệch không đúng.')
    gio = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    with csdl.giao_dich(con):
        n = con.execute('''UPDATE y_kien_du_thao SET loai = ?, nhom = ?, noi_dung = ?, huong_xu_ly = ?,
                           so_tien_chenh = ?, ket_qua_doi_thoai = ?, ngay_cap_nhat = ?
                           WHERE dot_id = ? AND ma_ho = ?''',
                        (loai, nhom or '', noi_dung or '', huong or '', tien, ket_qua or '', gio, dot_id, ma_ho)).rowcount
        if not n:
            raise LoiNhap('Hộ chưa nằm trong đợt dự thảo này.')
        csdl.ghi_nhat_ky(con, 'Ghi ý kiến dự thảo', f'Hộ {ma_ho}, đợt {dot_id}: {TEN_LOAI[loai]}')


def ghi_doi_thoai(con, dot_id: int, ma_ho: int, ngay: str, dia_diem: str, ket_luan: str, dien_bien: str = '') -> None:
    from . import csdl
    kiem_ho_nhan_viec(con, ma_ho)
    n = ngay_iso(doc_ngay(ngay))
    lan = con.execute('SELECT COALESCE(MAX(lan), 0) + 1 FROM doi_thoai_ho WHERE dot_id = ? AND ma_ho = ?',
                      (dot_id, ma_ho)).fetchone()[0]
    with csdl.giao_dich(con):
        con.execute('''INSERT INTO doi_thoai_ho (dot_id, ma_ho, lan, ngay, dia_diem, dien_bien, ket_luan)
                       VALUES (?, ?, ?, ?, ?, ?, ?)''',
                    (dot_id, ma_ho, lan, n, dia_diem or '', dien_bien or '', ket_luan or ''))
        con.execute('UPDATE y_kien_du_thao SET ket_qua_doi_thoai = ?, ngay_cap_nhat = ? WHERE dot_id = ? AND ma_ho = ?',
                    (ket_luan or '', datetime.now().strftime('%Y-%m-%d %H:%M:%S'), dot_id, ma_ho))
        csdl.ghi_nhat_ky(con, 'Biên bản đối thoại', f'Hộ {ma_ho}, đợt {dot_id}, lần {lan}')


def chuyen_sang_dot(con, dot_id: int, ds_ma_ho: list, dot_moi: int) -> int:
    """Đưa hộ chưa đồng ý sang đợt sau để tiếp tục vận động. Ý kiến ở đợt cũ giữ nguyên."""
    from . import csdl
    if dot_moi == dot_id:
        raise LoiNhap('Chọn một đợt khác đợt đang xem.')
    kiem_ds_ho_nhan_viec(con, ds_ma_ho)
    gio = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    n = 0
    with csdl.giao_dich(con):
        for ma in ds_ma_ho:
            y = con.execute('SELECT loai FROM y_kien_du_thao WHERE dot_id = ? AND ma_ho = ?', (dot_id, ma)).fetchone()
            if y is None or y['loai'] == 'dong_y':
                continue
            con.execute('UPDATE y_kien_du_thao SET chuyen_dot_id = ? WHERE dot_id = ? AND ma_ho = ?', (dot_moi, dot_id, ma))
            if not con.execute('SELECT 1 FROM y_kien_du_thao WHERE dot_id = ? AND ma_ho = ?', (dot_moi, ma)).fetchone():
                con.execute('''INSERT INTO y_kien_du_thao (dot_id, ma_ho, loai, ngay_cap_nhat) VALUES (?, ?, 'chua', ?)''',
                            (dot_moi, ma, gio))
            con.execute('UPDATE ho SET dot_du_thao_id = ? WHERE ma_ho = ?', (dot_moi, ma))
            n += 1
        csdl.ghi_nhat_ky(con, 'Chuyển hộ sang đợt dự thảo sau', f'{n} hộ từ đợt {dot_id} sang đợt {dot_moi}')
    return n


def _thua(con, ma_ho: int) -> str:
    ds = [f'{r["so_thua"] or "…"} (tờ {r["so_to"] or "…"})' for r in
          con.execute('SELECT so_thua, so_to FROM thua WHERE ma_ho = ? ORDER BY thu_tu, ma_thua', (ma_ho,))]
    return '; '.join(ds)


def ds_ho_dot(con, dot_id: int) -> list:
    from .an_toan import che_cccd
    tien = _tien_ho(con)
    kq = []
    for r in con.execute('''SELECT y.*, h.ho_ten, h.so_cccd, h.dia_chi, h.thu_tu
                            FROM y_kien_du_thao y JOIN ho h ON h.ma_ho = y.ma_ho
                            WHERE y.dot_id = ? ORDER BY h.thu_tu, h.ma_ho''', (dot_id,)):
        d = dict(r)
        d['thua'] = _thua(con, r['ma_ho'])
        d['cccd_che'] = che_cccd(r['so_cccd'] or '')
        d['tien'] = tien.get(r['ma_ho'])
        d['lan_dt'] = con.execute('SELECT COUNT(*) FROM doi_thoai_ho WHERE dot_id = ? AND ma_ho = ?',
                                  (dot_id, r['ma_ho'])).fetchone()[0]
        kq.append(d)
    return kq


def ds_vuong(con) -> list:
    kq = []
    for r in con.execute('''SELECT ma_ho, thu_tu, ho_ten, ma_vuong, ghi_chu_phap_ly, du_dieu_kien
                            FROM ho WHERE TRIM(ma_vuong) <> '' OR du_dieu_kien = 0
                            ORDER BY thu_tu, ma_ho'''):
        d = dict(r)
        d['thua'] = _thua(con, r['ma_ho'])
        d['ten_vuong'] = TEN_VUONG.get(r['ma_vuong'], 'Chưa đánh dấu đủ điều kiện' if not r['du_dieu_kien'] else '')
        kq.append(d)
    return kq


def _tien_ho(con) -> dict:
    try:
        from .nghiep_vu import ket_qua_ho
        return {m: kq.tong for m, (kq, _) in ket_qua_ho(con).items()}
    except Exception:
        return {}


def _ghi_excel(file, sheets: list) -> 'Path':
    import openpyxl
    from openpyxl.styles import Font, PatternFill
    from pathlib import Path
    wb = openpyxl.Workbook()
    wb.remove(wb.active)
    for ten, tieu_de, dong in sheets:
        ws = wb.create_sheet(ten[:31])
        ws['A1'] = tieu_de
        ws['A1'].font = Font(bold=True, size=13, color='0F3866')
        if not dong:
            continue
        ws.append([])
        ws.append(list(dong[0].keys()))
        for c in ws[3]:
            c.font = Font(bold=True, color='FFFFFF')
            c.fill = PatternFill('solid', fgColor='0F3866')
        for r in dong:
            ws.append(list(r.values()))
        ws.freeze_panes = 'A4'
    p = Path(file)
    _an_toan.luu_xlsx(wb, p)
    return p


def xuat_niem_yet(con, dot_id: int, file) -> 'Path':
    """Bảng niêm yết: CCCD đã che. Kèm mốc 10 ngày của đợt."""
    dot = con.execute('SELECT * FROM dot_du_thao WHERE id = ?', (dot_id,)).fetchone()
    if dot is None:
        raise LoiNhap('Chưa chọn đợt dự thảo.')
    dong = []
    for i, h in enumerate(ds_ho_dot(con, dot_id), 1):
        dong.append({
            'STT': i, 'Mã hộ': h['ma_ho'], 'Họ và tên': h['ho_ten'], 'CCCD': h['cccd_che'],
            'Địa chỉ': h['dia_chi'], 'Thửa': h['thua'],
            'Tổng tiền dự thảo': vn(h['tien']) if h['tien'] is not None else '',
            'Địa điểm niêm yết': dot['dia_diem'],
        })
    tieu = (f'DỰ THẢO PHƯƠNG ÁN BỒI THƯỜNG, HỖ TRỢ, TÁI ĐỊNH CƯ — {dot["ten"]}. '
            f'Niêm yết {hien_ngay(dot["ngay_bat_dau"])} đến {hien_ngay(dot["ngay_ket_thuc"])} '
            f'({SO_NGAY_NIEM_YET} ngày).')
    return _ghi_excel(file, [('Niêm yết', tieu, dong)])


def xuat_y_kien(con, dot_id: int, file) -> 'Path':
    dot = con.execute('SELECT * FROM dot_du_thao WHERE id = ?', (dot_id,)).fetchone()
    if dot is None:
        raise LoiNhap('Chưa chọn đợt dự thảo.')
    tk = thong_ke_y_kien(con, dot_id)
    dong = []
    for h in ds_ho_dot(con, dot_id):
        dong.append({
            'Mã hộ': h['ma_ho'], 'Họ và tên': h['ho_ten'], 'Ý kiến': TEN_LOAI.get(h['loai'], h['loai']),
            'Nhóm': TEN_NHOM.get(h['nhom'], h['nhom']), 'Nội dung': h['noi_dung'],
            'Hướng xử lý': h['huong_xu_ly'], 'Chênh lệch': h['so_tien_chenh'],
            'Đối thoại': h['ket_qua_doi_thoai'],
        })
    tieu = (f'Báo cáo ý kiến dự thảo — {dot["ten"]}. Đồng ý {tk["dong_y"]}/{tk["so_ho_dot"]} '
            f'({tk["pt_dot"]:.1f}% trong đợt). Lũy kế {tk["luy_dong"]}/{tk["luy_ny"]} hộ đã niêm yết '
            f'({tk["pt_luy"]:.1f}%). Bao phủ {tk["luy_dong"]}/{tk["tong_du_an"]} hộ cả dự án ({tk["pt_bao_phu"]:.1f}%).')
    nhom = [{'Nhóm lý do': x['ten'], 'Số hộ kiến nghị': x['so_ho'], 'Đã đồng thuận': x['dong_y'],
             'Chưa đồng thuận': x['chua_dong_y'], 'Tỷ lệ đồng thuận (%)': round(x['pt_dong_y'], 1),
             'Nội dung tiêu biểu': x['noi_dung']} for x in tong_hop_nhom(con, dot_id)]
    return _ghi_excel(file, [('Ý kiến', tieu, dong or [{'Mã hộ': '', 'Ghi chú': 'Chưa có ý kiến khác đồng ý'}]),
                             ('Theo nhóm lý do', 'Tỷ lệ đồng thuận theo nhóm lý do kiến nghị - hồ sơ trình thẩm định (Bước 8)',
                              nhom)])


def xuat_don_doc(con, file) -> 'Path':
    """Danh sách hộ V1, V2 để đôn đốc UBND cấp xã / cơ quan đo đạc — không thay công văn ký số."""
    dong = []
    for h in ds_vuong(con):
        if h['ma_vuong'] not in ('V1', 'V2'):
            continue
        dong.append({
            'Mã hộ': h['ma_ho'], 'Họ và tên': h['ho_ten'], 'Thửa': h['thua'],
            'Nhóm': f'{h["ma_vuong"]} — {h["ten_vuong"]}', 'Ghi chú': h['ghi_chu_phap_ly'],
            'Cơ quan': 'UBND cấp xã' if h['ma_vuong'] == 'V1' else 'Tổ hòa giải / cơ quan đăng ký đất đai',
        })
    tieu = 'Danh sách hộ cần đôn đốc (V1 chờ xác nhận nguồn gốc, V2 tranh chấp ranh). Dùng để lập công văn gửi UBND cấp xã.'
    return _ghi_excel(file, [('Đôn đốc', tieu, dong or [{'Mã hộ': '', 'Ghi chú': 'Không có hộ nhóm V1, V2'}])])


# ---------------------------------------------------------------- chọn hộ niêm yết từ danh sách hộ (0.9.69)
DIEU_KIEN_NIEM_YET = (
    'Đã lập phương án (người dùng lập / lưu, hoặc nhập từ file) - phương án phần mềm tự lập phải mở soát và lưu trước',
    'Có họ tên chủ sử dụng',
    'Mọi thửa thu hồi đã ghi nguồn gốc đất',
    'Không ghi tranh chấp',
    'Không thuộc nhóm vướng pháp lý V1-V5',
)


def danh_gia_niem_yet(con, ds_ma_ho=None) -> list:
    """Xét từng hộ theo DIEU_KIEN_NIEM_YET -> [dict(ma_ho, thu_tu, ho_ten, tien, du (đủ điều kiện), ly_do [chưa đạt],
    can_xem [cảnh báo của kiểm tra phương án - không chặn], da_danh_dau, vuong, dot (tên đợt niêm yết đã vào))].
    ds_ma_ho None = cả dự án. Đọc gộp (một truy vấn mỗi bảng) - dự án 5.000 hộ không truy vấn từng hộ."""
    from .lap_pa import phan_loai_lap
    from .nghiep_vu import ket_qua_ho
    kq_ho = ket_qua_ho(con)
    lap = phan_loai_lap(con, {m: k.co_phuong_an for m, (k, _) in kq_ho.items()})
    thua = {}
    for r in con.execute("SELECT ma_ho, COUNT(*), SUM(TRIM(IFNULL(nguon_goc, '')) = '') FROM thua GROUP BY ma_ho"):
        thua[r[0]] = (r[1], r[2] or 0)
    dot = {r[0]: r[1] for r in con.execute('''SELECT y.ma_ho, GROUP_CONCAT(d.ten, '; ') FROM y_kien_du_thao y
                                               JOIN dot_du_thao d ON d.id = y.dot_id GROUP BY y.ma_ho''')}
    chon = None if ds_ma_ho is None else set(ds_ma_ho)
    kq = []
    for r in con.execute('''SELECT ma_ho, thu_tu, ho_ten, tranh_chap, du_dieu_kien, ma_vuong FROM ho
                            ORDER BY thu_tu, ma_ho'''):
        m = r['ma_ho']
        if chon is not None and m not in chon:
            continue
        ly_do = []
        loai = lap.get(m, 'chua')
        if loai == 'chua':
            ly_do.append('Chưa lập phương án')
        elif loai == 'tu_lap':
            ly_do.append('Phương án phần mềm tự lập, chưa mở soát và lưu')
        if not (r['ho_ten'] or '').strip():
            ly_do.append('Thiếu họ tên')
        n, thieu = thua.get(m, (0, 0))
        if not n:
            ly_do.append('Chưa có thửa đất')
        elif thieu:
            ly_do.append(f'{thieu}/{n} thửa chưa ghi nguồn gốc')
        if (r['tranh_chap'] or '').strip():
            ly_do.append('Đang tranh chấp')
        vuong = (r['ma_vuong'] or '').strip()
        if vuong:
            ly_do.append(f'Vướng {vuong}: {TEN_VUONG.get(vuong, "")}'.rstrip(': '))
        k, canh_bao = kq_ho.get(m, (None, []))
        kq.append(dict(ma_ho=m, thu_tu=r['thu_tu'], ho_ten=r['ho_ten'] or '', tien=k.tong if k is not None else None,
                       du=not ly_do, ly_do=ly_do, can_xem=list(canh_bao or []), da_danh_dau=bool(r['du_dieu_kien']),
                       vuong=vuong, dot=dot.get(m, '')))
    return kq


def ghi_danh_dau(con, danh_dau: dict) -> tuple:
    """{ma_ho: True / False} -> ho.du_dieu_kien (một giao dịch = một bước Hoàn tác). Hộ đang vướng V1-V5 không đánh dấu đủ
    điều kiện được (bỏ qua). Trả (số hộ đổi, số hộ bỏ qua vì vướng)."""
    from . import csdl
    hien = {r[0]: (bool(r[1]), (r[2] or '').strip()) for r in con.execute('SELECT ma_ho, du_dieu_kien, ma_vuong FROM ho')}
    doi, bo = [], 0
    for m, co in danh_dau.items():
        if m not in hien:
            continue
        cu, vuong = hien[m]
        if co and vuong:
            bo += 1
            continue
        if bool(co) != cu:
            doi.append((1 if co else 0, m))
    kiem_ds_ho_nhan_viec(con, [m for _, m in doi])         # chỉ hộ thật sự đổi đánh dấu (hộp chọn gửi cả dự án)
    if doi:
        with csdl.giao_dich(con):
            con.executemany('UPDATE ho SET du_dieu_kien = ? WHERE ma_ho = ?', doi)
            them = sum(1 for c, _ in doi if c)
            csdl.ghi_nhat_ky(con, 'Chọn hộ niêm yết', f'Đánh dấu đủ điều kiện {them} hộ, bỏ đánh dấu {len(doi) - them} hộ')
    return len(doi), bo


# ---------------------------------------------------------------- tương tác nhanh, tổng hợp theo nhóm lý do, biên bản đối thoại (0.9.75)
VONG_Y_KIEN = ('chua', 'dong_y', 'khong_dong_y', 'y_kien_khac')      # một chạm: Chưa lấy ý kiến -> Đồng ý -> Không đồng ý -> Ý kiến khác


def loai_ke_tiep(loai: str) -> str:
    """Loại ý kiến kế tiếp trong vòng một chạm (loại lạ -> bắt đầu lại từ 'dong_y')."""
    if loai not in VONG_Y_KIEN:
        return VONG_Y_KIEN[1]
    return VONG_Y_KIEN[(VONG_Y_KIEN.index(loai) + 1) % len(VONG_Y_KIEN)]


def cap_nhat_y_kien(con, dot_id: int, ma_ho: int, **thay) -> str:
    """Đổi một phần ý kiến của hộ trong đợt (loai, nhom, noi_dung, huong_xu_ly, so_tien_chenh, ket_qua_doi_thoai), giữ các trường
    còn lại. Trả loại ý kiến sau khi đổi."""
    r = con.execute('SELECT * FROM y_kien_du_thao WHERE dot_id = ? AND ma_ho = ?', (dot_id, ma_ho)).fetchone()
    if r is None:
        raise LoiNhap('Hộ chưa nằm trong đợt dự thảo này.')
    gt = dict(loai=r['loai'], nhom=r['nhom'], noi_dung=r['noi_dung'], huong_xu_ly=r['huong_xu_ly'],
              so_tien_chenh=r['so_tien_chenh'], ket_qua_doi_thoai=r['ket_qua_doi_thoai'])
    gt.update(thay)
    ghi_y_kien(con, dot_id, ma_ho, gt['loai'], gt['nhom'], gt['noi_dung'], huong=gt['huong_xu_ly'],
               tien_chenh=gt['so_tien_chenh'], ket_qua=gt['ket_qua_doi_thoai'])
    return gt['loai']


def doi_y_kien_nhanh(con, dot_id: int, ma_ho: int) -> str:
    """Một chạm: chuyển ý kiến của hộ sang loại kế tiếp trong VONG_Y_KIEN. Trả loại mới."""
    kiem_ho_nhan_viec(con, ma_ho)
    r = con.execute('SELECT loai FROM y_kien_du_thao WHERE dot_id = ? AND ma_ho = ?', (dot_id, ma_ho)).fetchone()
    if r is None:
        raise LoiNhap('Hộ chưa nằm trong đợt dự thảo này.')
    return cap_nhat_y_kien(con, dot_id, ma_ho, loai=loai_ke_tiep(r['loai']))


NHOM_TONG_HOP = ('gia_dat', 'nha', 'cay', 'tai_dinh_cu', 'ho_tro', 'khac')


def tong_hop_nhom(con, dot_id) -> list:
    """Tỷ lệ đồng thuận theo nhóm lý do kiến nghị (giá đất, tài sản = nhà / công trình, cây trồng, tái định cư, hỗ trợ, khác) của đợt
    (dot_id None: lũy kế các đợt). Mỗi nhóm: hộ có kiến nghị nhóm đó, trong đó đã đồng ý, chưa đồng thuận, tỷ lệ đồng thuận (%),
    nội dung tiêu biểu. Dòng cuối 'Toàn đợt': mọi hộ (kể cả hộ chưa lấy ý kiến). [dict(nhom, ten, so_ho, dong_y, chua_dong_y,
    pt_dong_y, noi_dung)]"""
    if dot_id:
        rows = con.execute('SELECT ma_ho, loai, nhom, noi_dung FROM y_kien_du_thao WHERE dot_id = ?', (dot_id,)).fetchall()
    else:
        rows = con.execute('SELECT ma_ho, loai, nhom, noi_dung FROM y_kien_du_thao').fetchall()
    kq = []
    gom = {}
    for r in rows:
        if r['nhom']:
            gom.setdefault(r['nhom'], []).append(r)
    for k in (*NHOM_TONG_HOP, *sorted(set(gom) - set(NHOM_TONG_HOP))):
        ds = gom.get(k, [])
        if not ds and k not in NHOM_TONG_HOP[:4]:
            continue                                         # nhóm chính luôn hiện (kể cả 0 hộ); hỗ trợ / khác chỉ khi có
        dong = sum(1 for r in ds if r['loai'] == 'dong_y')
        nd = next((r['noi_dung'] for r in ds if r['noi_dung']), '')
        kq.append(dict(nhom=k, ten=TEN_NHOM.get(k, k), so_ho=len(ds), dong_y=dong, chua_dong_y=len(ds) - dong,
                       pt_dong_y=_pt(dong, len(ds)) if ds else 0.0, noi_dung=nd))
    tong = len(rows)
    dong = sum(1 for r in rows if r['loai'] == 'dong_y')
    kq.append(dict(nhom='', ten='Toàn đợt' if dot_id else 'Toàn bộ các đợt', so_ho=tong, dong_y=dong, chua_dong_y=tong - dong,
                   pt_dong_y=_pt(dong, tong), noi_dung=''))
    return kq


def xuat_doi_thoai(con, dot_id: int, file) -> 'Path':
    """Biên bản đối thoại, giải trình: hộ Không đồng ý / Ý kiến khác của đợt, từng lần đối thoại (ngày, địa điểm, diễn biến, kết
    luận) và hướng xử lý. Dùng để lập biên bản ký (không thay biên bản có chữ ký)."""
    dot = con.execute('SELECT * FROM dot_du_thao WHERE id = ?', (dot_id,)).fetchone()
    if dot is None:
        raise LoiNhap('Chưa chọn đợt dự thảo.')
    dong = []
    for h in ds_ho_dot(con, dot_id):
        if h['loai'] not in ('khong_dong_y', 'y_kien_khac'):
            continue
        lan = con.execute('SELECT * FROM doi_thoai_ho WHERE dot_id = ? AND ma_ho = ? ORDER BY lan', (dot_id, h['ma_ho'])).fetchall()
        goc = {'Mã hộ': h['ma_ho'], 'Họ và tên': h['ho_ten'], 'Thửa': h['thua'], 'Ý kiến': TEN_LOAI.get(h['loai'], ''),
               'Nhóm kiến nghị': TEN_NHOM.get(h['nhom'], h['nhom']), 'Nội dung kiến nghị': h['noi_dung']}
        if not lan:
            dong.append({**goc, 'Lần': '', 'Ngày': '', 'Địa điểm': '', 'Diễn biến': '', 'Kết luận, tiếp thu': h['ket_qua_doi_thoai'],
                         'Hướng xử lý': h['huong_xu_ly']})
        for x in lan:
            dong.append({**goc, 'Lần': x['lan'], 'Ngày': hien_ngay(x['ngay']), 'Địa điểm': x['dia_diem'],
                         'Diễn biến': x['dien_bien'], 'Kết luận, tiếp thu': x['ket_luan'], 'Hướng xử lý': h['huong_xu_ly']})
    tieu = (f'BIÊN BẢN ĐỐI THOẠI, GIẢI TRÌNH - {dot["ten"]}. Họp dân {hien_ngay(dot["ngay_hop"]) if dot["ngay_hop"] else "(chưa đặt)"}'
            f', hạn đối thoại {hien_ngay(dot["han_doi_thoai"]) if dot["han_doi_thoai"] else "(chưa đặt)"}. Hộ không đồng ý hoặc có '
            'ý kiến khác.')
    return _ghi_excel(file, [('Đối thoại', tieu, dong or [{'Mã hộ': '', 'Ghi chú': 'Chưa có hộ không đồng ý / ý kiến khác'}])])


# ---------------------------------------------------------------- hộ đã niêm yết xong (lấy vào đợt trình thẩm định - Bước 8)
def _han_xong(iso: str):
    from .thoi_han import doc_ngay as _doc
    return _doc(iso)


def dot_niem_yet_xong(con, hom_nay=None) -> list:
    """Các đợt niêm yết ĐÃ HẾT thời hạn (ngày kết thúc <= hôm nay) và có hộ: [dict(id, ten, ngay_ket_thuc, so_ho, so_dong_y)] -
    chỉ tính hộ không vướng pháp lý (ma_vuong trống). Dùng cho nút "Lấy hộ đã niêm yết xong" ở Đợt trình thẩm định."""
    from .thoi_han import hom_nay_hoac
    nay = hom_nay_hoac(hom_nay)
    kq = []
    for d in ds_dot(con):
        han = _han_xong(d['ngay_ket_thuc'])
        if han is None or han > nay:
            continue
        r = con.execute("""SELECT COUNT(*), SUM(CASE WHEN y.loai = 'dong_y' THEN 1 ELSE 0 END)
                           FROM y_kien_du_thao y JOIN ho h ON h.ma_ho = y.ma_ho
                           WHERE y.dot_id = ? AND TRIM(h.ma_vuong) = ''""", (d['id'],)).fetchone()
        if r[0]:
            kq.append(dict(id=d['id'], ten=d['ten'], ngay_ket_thuc=hien_ngay(d['ngay_ket_thuc']), so_ho=r[0], so_dong_y=r[1] or 0))
    return kq


def ho_niem_yet_xong(con, hom_nay=None, chi_dong_y: bool = False, dot_id: int | None = None) -> list:
    """Mã hộ (theo thứ tự hộ) của các hộ đã niêm yết xong: hộ nằm trong đợt niêm yết đã hết thời hạn (hoặc đợt dot_id), không
    vướng pháp lý. Hộ có mặt ở nhiều đợt: tính theo ý kiến của đợt GẦN NHẤT đã hết hạn. chi_dong_y: chỉ hộ đã đồng ý."""
    xong = {d['id'] for d in dot_niem_yet_xong(con, hom_nay)}
    if dot_id is not None:
        xong &= {dot_id}
    moi_nhat = {}
    for r in con.execute('''SELECT y.ma_ho, y.dot_id, y.loai, h.thu_tu, h.ma_vuong FROM y_kien_du_thao y
                            JOIN ho h ON h.ma_ho = y.ma_ho ORDER BY y.dot_id, y.id'''):
        if r['dot_id'] in xong and not (r['ma_vuong'] or '').strip():
            moi_nhat[r['ma_ho']] = (r['thu_tu'], r['loai'])
    return [m for m, (_, loai) in sorted(moi_nhat.items(), key=lambda kv: (kv[1][0], kv[0])) if not chi_dong_y or loai == 'dong_y']


# ---------------------------------------------------------------- xóa đợt dự thảo (đặc tả V10 mục IV.1)
def thong_tin_xoa_dot(con, dot_id: int) -> dict:
    """Điều sẽ mất khi xóa đợt: số hộ, số hộ đã có ý kiến (khác "chưa lấy ý kiến"), số lần đối thoại. Để hộp xác nhận nói rõ."""
    r = con.execute('SELECT ten FROM dot_du_thao WHERE id = ?', (dot_id,)).fetchone()
    if r is None:
        raise LoiNhap('Đợt dự thảo không còn trong dự án.')
    so_ho, co_y = con.execute("SELECT COUNT(*), SUM(CASE WHEN loai <> 'chua' THEN 1 ELSE 0 END) FROM y_kien_du_thao WHERE dot_id = ?",
                              (dot_id,)).fetchone()
    dt = con.execute('SELECT COUNT(*) FROM doi_thoai_ho WHERE dot_id = ?', (dot_id,)).fetchone()[0]
    return dict(ten=r['ten'], so_ho=so_ho or 0, co_y_kien=co_y or 0, so_doi_thoai=dt)


def xoa_dot(con, dot_id: int) -> dict:
    """Xóa một đợt niêm yết / lấy ý kiến: các hộ của đợt trở về danh sách chờ (vẫn "đủ điều kiện", chưa thuộc đợt nào - hoặc thuộc đợt
    gần nhất còn lại của hộ); ý kiến và biên bản đối thoại GHI TRONG ĐỢT NÀY bị xóa theo đợt. Phương án, thửa, hồ sơ hộ giữ nguyên 100%.
    Trả thong_tin_xoa_dot (số liệu trước khi xóa)."""
    from . import csdl
    tt = thong_tin_xoa_dot(con, dot_id)
    with csdl.giao_dich(con):
        ds = [r[0] for r in con.execute('SELECT ma_ho FROM y_kien_du_thao WHERE dot_id = ?', (dot_id,))]
        con.execute('DELETE FROM doi_thoai_ho WHERE dot_id = ?', (dot_id,))
        con.execute('DELETE FROM y_kien_du_thao WHERE dot_id = ?', (dot_id,))
        con.execute('UPDATE y_kien_du_thao SET chuyen_dot_id = NULL WHERE chuyen_dot_id = ?', (dot_id,))
        con.execute('DELETE FROM dot_du_thao WHERE id = ?', (dot_id,))
        for ma in ds:                                       # hộ còn ở đợt khác: trỏ về đợt gần nhất; không còn: về danh sách chờ
            con.execute('UPDATE ho SET dot_du_thao_id = (SELECT MAX(dot_id) FROM y_kien_du_thao WHERE ma_ho = ?) WHERE ma_ho = ?',
                        (ma, ma))
        csdl.ghi_nhat_ky(con, 'Xóa đợt dự thảo', f'{tt["ten"]}: {tt["so_ho"]} hộ về danh sách chờ, {tt["co_y_kien"]} ý kiến, '
                                                  f'{tt["so_doi_thoai"]} biên bản đối thoại')
    return tt

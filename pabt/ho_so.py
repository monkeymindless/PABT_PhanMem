"""Hồ sơ kiểm kê (giai đoạn 4): thêm / sửa / xóa hộ và thửa, gộp hộ, chuyển thửa sang hộ khác.

Mỗi thao tác ghi trong một giao dịch và có nhật ký. Số liệu sai thì báo LoiNhap (thông báo tiếng Việt).
"""
from __future__ import annotations
import re
from datetime import datetime

from . import csdl
from .lap_pa import LoiNhap, bo_dau, doc_so
from .tien import chuoi, so_vn

TRUONG_HO = [('ho_ten', 'Họ và tên'), ('so_cccd', 'Số CCCD'), ('ngay_cap', 'Ngày cấp'), ('noi_cap', 'Nơi cấp'),
             ('dia_chi', 'Địa chỉ'), ('dien_thoai', 'Điện thoại'), ('phap_ly', 'Pháp lý'), ('tranh_chap', 'Tranh chấp'),
             ('tai_dinh_cu', 'Tái định cư'), ('trang_thai', 'Trạng thái'), ('ghi_chu', 'Ghi chú')]
TRUONG_THUA = [('so_to', 'Tờ'), ('so_thua', 'Thửa'), ('loai_dat', 'Loại đất'), ('dt_thu_hoi', 'DT thu hồi (m²)'),
               ('nguon_goc', 'Nguồn gốc'), ('vi_tri', 'Vị trí')]


def _gon(v) -> str:
    return ' '.join(str(v if v is not None else '').split())


def chuan_nguon_goc(v) -> str:
    """Giữ xuống dòng. Gạch đầu dòng viết liền trong câu ('... - đất ở') tách thành dòng riêng bắt đầu bằng '- '
    để màn hình và bản in thụt lề treo."""
    s = str(v or '').replace('\r\n', '\n').replace('\r', '\n')
    s = re.sub(r'[ \t]+([•*])[ \t]+', r'\n\1 ', s)
    s = re.sub(r'[ \t]+([-–])[ \t]+', r'\n- ', s)
    dong = [' '.join(x.split()) for x in s.split('\n')]
    return '\n'.join(x for x in dong if x)


# ký hiệu đầu dòng của một đoạn nguồn gốc: "- ", "– ", "+ ", "• ", "* ", "a) ", "1. ", "1) "
_RE_DAU_DONG = re.compile(r'^\s*(?:[-–+•*]|[a-zđ]\)|\d{1,2}[.)])\s+', re.I)


_RE_CAP_XA = re.compile(r'^(xa|phuong|thi tran|dac khu|p\.?|x\.?|tt\.?)\s+')


def rut_gon_dia_chi(dia_chi: str, ten_dia_ban: str) -> str:
    """Địa chỉ hiển thị gọn trên danh sách hộ (người dùng 13/10/2026): bỏ đoạn xã / phường trùng địa bàn dự án và các cấp sau nó
    ("Ấp 1, xã Trị An, huyện Vĩnh Cửu, tỉnh Đồng Nai" + địa bàn "Trị An" -> "Ấp 1"). Xã / phường khác, hoặc chỉ có một đoạn: giữ
    nguyên (địa chỉ đầy đủ ở chú thích của ô)."""
    chu = ' '.join(str(dia_chi or '').split())
    xa = _RE_CAP_XA.sub('', bo_dau(ten_dia_ban or '').strip())
    if not chu or not xa:
        return chu
    doan = [d.strip() for d in re.split(r'[,;]', chu)]
    for i in range(1, len(doan)):
        if _RE_CAP_XA.sub('', bo_dau(doan[i]).strip()) == xa:
            gon = ', '.join(d for d in doan[:i] if d)
            return gon or chu
    return chu


# chủ sử dụng là tổ chức (0.9.87 - bản in ghi "Tổ chức:" thay "Họ và tên:"): tên BẮT ĐẦU bằng loại tổ chức (so không dấu). Không
# dùng từ trùng họ người ("trường" = Trương, "đinh" = Đinh): trường học phải có cấp học đi kèm.
_DAU_TO_CHUC = ('cong ty', 'tong cong ty', 'doanh nghiep', 'dntn', 'hop tac xa', 'htx', 'uy ban nhan dan', 'ubnd',
                'ban quan ly', 'bql', 'trung tam', 'chi nhanh', 'tap doan', 'xi nghiep', 'nha may', 'nong truong', 'lam truong',
                'nha tho', 'chua', 'tinh xa', 'tinh that', 'thanh that', 'giao xu', 'giao ho', 'hoi thanh',
                'truong mam non', 'truong mau giao', 'truong tieu hoc', 'truong thcs', 'truong thpt', 'truong trung hoc',
                'truong cao dang', 'truong dai hoc', 'benh vien', 'tram y te', 'ngan hang', 'kho bac', 'co quan', 'to chuc',
                'cong an', 'ban chi huy', 'bo chi huy', 'dang uy', 'mat tran to quoc', 'hoi nong dan', 'hoi cuu chien binh',
                'hoi lien hiep phu nu', 'hoi chu thap do', 'van phong', 'cong doan', 'quy tin dung')
_RE_TO_CHUC = re.compile(r'^(?:' + '|'.join(re.escape(x) for x in _DAU_TO_CHUC) + r')\b|\b(?:tnhh|co phan|cp|mtv)\b')
_RE_LA_NGUOI = re.compile(r'^(?:ong|ba|ho ong|ho ba|ho gia dinh|anh|chi|cu)\b')


def la_to_chuc(ten: str, loai: str = '') -> bool:
    """Chủ sử dụng đất là tổ chức: loai ('to_chuc' / 'Tổ chức'…) nếu có, không thì theo tên (Công ty…, UBND…, Ban quản lý…,
    Hợp tác xã, Trung tâm, Nhà thờ, Chùa, Trường tiểu học…, hoặc có TNHH / cổ phần). "Ông / Bà / Hộ …" luôn là hộ, cá nhân."""
    lo = bo_dau(loai or '').strip().replace('_', ' ')
    if lo:
        return lo in ('to chuc', 'tc', 'doanh nghiep', 'co quan')
    s = ' '.join(bo_dau(ten or '').split())
    return bool(s) and not _RE_LA_NGUOI.match(s) and bool(_RE_TO_CHUC.search(s))


def dau_dong(doan: str) -> str:
    """Phần ký hiệu đầu dòng (cả khoảng trắng sau) của đoạn, '' nếu đoạn không bắt đầu bằng gạch đầu dòng. Dòng tràn của đoạn
    có ký hiệu thì thụt vào thẳng chữ sau ký hiệu (thụt lề treo - màn hình hồ sơ và bản in, người dùng yêu cầu)."""
    m = _RE_DAU_DONG.match(doan or '')
    return m.group(0) if m else ''


def chuan_loai_dat(v) -> str:
    """' ont + cln ' -> 'ONT+CLN'"""
    return '+'.join(p.strip().upper() for p in _gon(v).split('+') if p.strip())


def doc_ho(con, ma_ho: int) -> dict:
    """Thông tin hộ + danh sách thửa (mỗi thửa có 'so_dong_pa' = số dòng mục 1 đang gắn với thửa)."""
    r = con.execute('SELECT * FROM ho WHERE ma_ho = ?', (ma_ho,)).fetchone()
    if r is None:
        raise LoiNhap(f'Không có hộ mã {ma_ho}.')
    ho = dict(r)
    ho['thua'] = [dict(t) for t in con.execute(
        '''SELECT t.*, (SELECT COUNT(*) FROM ct_dat d WHERE d.ma_thua = t.ma_thua) AS so_dong_pa
           FROM thua t WHERE t.ma_ho = ? ORDER BY t.thu_tu, t.ma_thua''', (ma_ho,))]
    ho['so_dong_pa'] = con.execute('SELECT (SELECT COUNT(*) FROM ct_dat WHERE ma_ho = ?) + '
                                   '(SELECT COUNT(*) FROM ct_khoan WHERE ma_ho = ?)', (ma_ho, ma_ho)).fetchone()[0]
    return ho


def chuan_hoa_thua(ds: list) -> list:
    """Kiểm tra và làm gọn danh sách thửa người dùng nhập; bỏ dòng trống hoàn toàn."""
    kq, da_co = [], set()
    for i, t in enumerate(ds, start=1):
        g = {k: _gon(t.get(k)) for k, _ in TRUONG_THUA}
        g['nguon_goc'] = chuan_nguon_goc(t.get('nguon_goc'))
        g['loai_dat'] = chuan_loai_dat(g['loai_dat'])
        if not any(g.values()):
            continue
        ten = f'Thửa {g["so_thua"] or "?"} tờ {g["so_to"] or "?"}'
        if not g['so_to'] and not g['so_thua']:
            raise LoiNhap(f'Dòng thửa {i}: chưa nhập số tờ, số thửa.')
        g['dt_thu_hoi'] = chuoi(doc_so(g['dt_thu_hoi'], f'{ten}: DT thu hồi'))
        khoa = (g['so_to'], g['so_thua'], g['loai_dat'])
        if khoa in da_co:
            raise LoiNhap(f'{ten} ({g["loai_dat"] or "chưa có loại đất"}) bị nhập hai lần.')
        da_co.add(khoa)
        g['ma_thua'] = t.get('ma_thua')
        kq.append(g)
    return kq


def thua_trung_ho_khac(con, ma_ho: int) -> list:
    """Thửa của hộ này cũng có trong hộ khác (đồng sử dụng hoặc nhập trùng)."""
    return [f'Thửa {r["so_thua"]} tờ {r["so_to"]} cũng có ở hộ {r["ma_ho"]} - {r["ho_ten"]}'
            for r in con.execute('''SELECT DISTINCT a.so_to, a.so_thua, h.ma_ho, h.ho_ten FROM thua a
                                     JOIN thua b ON b.so_to = a.so_to AND b.so_thua = a.so_thua AND b.ma_ho <> a.ma_ho
                                     JOIN ho h ON h.ma_ho = b.ma_ho WHERE a.ma_ho = ? ORDER BY h.ma_ho''', (ma_ho,))]


def luu_ho(con, ma_ho, thong_tin: dict, ds_thua: list) -> int:
    """Thêm hộ mới (ma_ho = None) hoặc sửa hộ: thông tin + toàn bộ danh sách thửa (thêm / sửa / xóa). Trả mã hộ."""
    moi = ma_ho is None
    # sửa hộ: chỉ ghi các trường có trong thong_tin (màn hình không hiện trường nào thì giữ nguyên trường đó)
    tt = {k: _gon(thong_tin.get(k)) for k, _ in TRUONG_HO if moi or k in thong_tin}
    if not tt.get('ho_ten'):
        raise LoiNhap('Họ và tên không được để trống.')
    if moi or 'trang_thai' in tt:
        tt['trang_thai'] = tt.get('trang_thai') or 'Chưa lập phương án'
    if 'so_cccd' in tt:
        tt['so_cccd'] = re.sub(r'\s', '', tt['so_cccd'])
        if tt['so_cccd'] and not tt['so_cccd'].isdigit():
            raise LoiNhap(f'Số CCCD "{tt["so_cccd"]}" chỉ gồm chữ số.')
    ds = chuan_hoa_thua(ds_thua)
    with con:
        if moi:
            ma_ho, thu_tu = con.execute('SELECT COALESCE(MAX(ma_ho), 0) + 1, COALESCE(MAX(thu_tu), 0) + 1 FROM ho').fetchone()
            con.execute(f'''INSERT INTO ho (ma_ho, thu_tu, {', '.join(tt)}) VALUES (?, ?, {', '.join('?' * len(tt))})''',
                        (ma_ho, thu_tu, *tt.values()))
        else:
            if con.execute('SELECT 1 FROM ho WHERE ma_ho = ?', (ma_ho,)).fetchone() is None:
                raise LoiNhap(f'Không có hộ mã {ma_ho}.')
            con.execute(f'''UPDATE ho SET {', '.join(k + ' = ?' for k in tt)} WHERE ma_ho = ?''', (*tt.values(), ma_ho))
        cu = {r[0] for r in con.execute('SELECT ma_thua FROM thua WHERE ma_ho = ?', (ma_ho,))}
        giu = set()
        for i, t in enumerate(ds, start=1):
            gt = (t['so_to'], t['so_thua'], t['loai_dat'], t['dt_thu_hoi'], t['nguon_goc'], t['vi_tri'], i)
            if t['ma_thua'] in cu:
                con.execute('''UPDATE thua SET so_to=?, so_thua=?, loai_dat=?, dt_thu_hoi=?, nguon_goc=?, vi_tri=?, thu_tu=?
                               WHERE ma_thua = ?''', (*gt, t['ma_thua']))
                giu.add(t['ma_thua'])
            else:
                mt = con.execute('SELECT COALESCE(MAX(ma_thua), 0) + 1 FROM thua').fetchone()[0]
                con.execute('''INSERT INTO thua (ma_thua, ma_ho, so_to, so_thua, loai_dat, dt_thu_hoi, nguon_goc, vi_tri, thu_tu)
                               VALUES (?,?,?,?,?,?,?,?,?)''', (mt, ma_ho, *gt))
                t['ma_thua'] = mt
        bo = cu - giu
        for mt in bo:
            con.execute('DELETE FROM thua WHERE ma_thua = ?', (mt,))      # dòng mục 1 gắn thửa này: ma_thua -> NULL
        csdl.ghi_nhat_ky(con, 'Thêm hộ' if moi else 'Sửa hồ sơ hộ',
                         f'Hộ {ma_ho} {tt["ho_ten"]}: {len(ds)} thửa' + (f', xóa {len(bo)} thửa' if bo else ''))
    return ma_ho


def _danh_lai(con) -> None:
    # chỉ ghi các hộ đổi số thứ tự (trước đây ghi lại cả 3.000 hộ - mỗi dòng còn một dòng nhật ký hoàn tác)
    doi = [(i, m) for i, (m, tt) in enumerate(con.execute('SELECT ma_ho, thu_tu FROM ho ORDER BY thu_tu, ma_ho').fetchall(),
                                              start=1) if tt != i]
    con.executemany('UPDATE ho SET thu_tu = ? WHERE ma_ho = ?', doi)


def xoa_ho(con, ma_ho: int) -> str:
    return xoa_nhieu_ho(con, [ma_ho])


def thong_tin_xoa(con, ds_ma_ho) -> list:
    """Hỏi trước khi xóa: [dict(ma_ho, thu_tu, ho_ten, so_thua, so_dong_pa, so_qd, da_nhan_tien)] theo thứ tự hộ trong danh sách
    (mã không còn trong dự án: bỏ qua)."""
    kq = []
    for m in dict.fromkeys(ds_ma_ho):
        r = con.execute(
            '''SELECT ma_ho, thu_tu, ho_ten,
                      (SELECT COUNT(*) FROM thua t WHERE t.ma_ho = h.ma_ho),
                      (SELECT COUNT(*) FROM ct_dat d WHERE d.ma_ho = h.ma_ho) + (SELECT COUNT(*) FROM ct_khoan k WHERE k.ma_ho = h.ma_ho),
                      (SELECT COUNT(*) FROM qd_ho q WHERE q.ma_ho = h.ma_ho),
                      (SELECT COUNT(*) FROM qd_ho q WHERE q.ma_ho = h.ma_ho AND q.da_chi_tra)
               FROM ho h WHERE ma_ho = ?''', (m,)).fetchone()
        if r is not None:
            kq.append(dict(zip(('ma_ho', 'thu_tu', 'ho_ten', 'so_thua', 'so_dong_pa', 'so_qd', 'da_nhan_tien'), r)))
    return sorted(kq, key=lambda x: (x['thu_tu'] or 0, x['ma_ho']))


def xoa_nhieu_ho(con, ds_ma_ho) -> str:
    """Xóa các hộ cùng thửa, phương án, quyết định / chi trả của hộ (CASCADE) trong MỘT giao dịch - một bước hoàn tác; đánh
    lại số thứ tự một lần."""
    ds = thong_tin_xoa(con, ds_ma_ho)
    if not ds:
        raise LoiNhap('Không có hộ nào để xóa (hộ đã bị xóa hoặc chưa chọn hộ).')
    thua, dong = sum(x['so_thua'] for x in ds), sum(x['so_dong_pa'] for x in ds)
    with con:
        for x in ds:
            con.execute('DELETE FROM ho WHERE ma_ho = ?', (x['ma_ho'],))     # thửa, phương án, qd_ho xóa theo (CASCADE)
            con.execute('DELETE FROM tong_excel WHERE ma_ho = ?', (x['ma_ho'],))
        _danh_lai(con)
        if len(ds) == 1:
            tb = f'Đã xóa hộ {ds[0]["ma_ho"]} {ds[0]["ho_ten"]} ({thua} thửa, {dong} dòng phương án).'
        else:
            ten = ', '.join(f'{x["ma_ho"]} {x["ho_ten"]}' for x in ds[:5]) + (f' và {len(ds) - 5} hộ khác' if len(ds) > 5 else '')
            tb = f'Đã xóa {len(ds)} hộ ({thua} thửa, {dong} dòng phương án): {ten}.'
        csdl.ghi_nhat_ky(con, 'Xóa hộ', tb)
    return tb


def gop_ho(con, giu: int, bo: int) -> str:
    """Gộp hộ `bo` vào hộ `giu`: chuyển thửa, dòng phương án; ô trống của hộ giữ lấy từ hộ bỏ; xóa hộ bỏ."""
    if giu == bo:
        raise LoiNhap('Chọn hai hộ khác nhau để gộp.')
    a, b = doc_ho(con, giu), doc_ho(con, bo)
    with con:
        cap = {}
        for k, _ in TRUONG_HO:
            if k == 'ghi_chu':
                cap[k] = '; '.join(x for x in (a[k], b[k]) if x)
            elif k != 'trang_thai' and not a[k] and b[k]:
                cap[k] = b[k]
        if cap:
            con.execute(f'''UPDATE ho SET {', '.join(k + ' = ?' for k in cap)} WHERE ma_ho = ?''', (*cap.values(), giu))
        for bang in ('thua', 'ct_dat', 'ct_khoan'):
            n = con.execute(f'SELECT COALESCE(MAX(thu_tu), 0) FROM {bang} WHERE ma_ho = ?', (giu,)).fetchone()[0]
            con.execute(f'UPDATE {bang} SET ma_ho = ?, thu_tu = thu_tu + ? WHERE ma_ho = ?', (giu, n, bo))
        if b['so_dong_pa']:
            con.execute('UPDATE ho SET luu_luc = ? WHERE ma_ho = ?', (datetime.now().isoformat(timespec='seconds'), giu))
        # quyết định của hộ bỏ chuyển sang hộ giữ (cùng một quyết định: cộng số tiền)
        for r in con.execute('SELECT qd_id, so_tien FROM qd_ho WHERE ma_ho = ?', (bo,)).fetchall():
            cu = con.execute('SELECT so_tien FROM qd_ho WHERE qd_id = ? AND ma_ho = ?', (r[0], giu)).fetchone()
            if cu is None:
                con.execute('UPDATE qd_ho SET ma_ho = ? WHERE qd_id = ? AND ma_ho = ?', (giu, r[0], bo))
            elif str(r[1] or '').strip():
                from .tien import D, chuoi
                con.execute('UPDATE qd_ho SET so_tien = ? WHERE qd_id = ? AND ma_ho = ?',
                            (chuoi(D(cu[0] or 0) + D(r[1])), r[0], giu))
        con.execute('DELETE FROM tong_excel WHERE ma_ho IN (?, ?)', (giu, bo))
        con.execute('DELETE FROM ho WHERE ma_ho = ?', (bo,))
        from .theo_doi import dong_bo_ho
        dong_bo_ho(con, giu)
        _danh_lai(con)
        tb = (f'Đã gộp hộ {bo} {b["ho_ten"]} ({len(b["thua"])} thửa, {b["so_dong_pa"]} dòng phương án) '
              f'vào hộ {giu} {a["ho_ten"]}.')
        csdl.ghi_nhat_ky(con, 'Gộp hộ', tb)
    return tb


def chuyen_thua(con, ma_thua: int, ma_ho_moi: int) -> str:
    """Chuyển một thửa (kèm các dòng mục 1 gắn với thửa) sang hộ khác."""
    t = con.execute('SELECT * FROM thua WHERE ma_thua = ?', (ma_thua,)).fetchone()
    if t is None:
        raise LoiNhap(f'Không có thửa mã {ma_thua}.')
    moi = doc_ho(con, ma_ho_moi)
    if t['ma_ho'] == ma_ho_moi:
        raise LoiNhap('Thửa đã thuộc hộ này.')
    with con:
        n = con.execute('SELECT COALESCE(MAX(thu_tu), 0) + 1 FROM thua WHERE ma_ho = ?', (ma_ho_moi,)).fetchone()[0]
        con.execute('UPDATE thua SET ma_ho = ?, thu_tu = ? WHERE ma_thua = ?', (ma_ho_moi, n, ma_thua))
        so = con.execute('UPDATE ct_dat SET ma_ho = ? WHERE ma_thua = ?', (ma_ho_moi, ma_thua)).rowcount
        if so:
            bay_gio = datetime.now().isoformat(timespec='seconds')
            con.execute('UPDATE ho SET luu_luc = ? WHERE ma_ho IN (?, ?)', (bay_gio, t['ma_ho'], ma_ho_moi))
        tb = (f'Đã chuyển thửa {t["so_thua"]} tờ {t["so_to"]} ({so_vn(t["dt_thu_hoi"])} m²) từ hộ {t["ma_ho"]} '
              f'sang hộ {ma_ho_moi} {moi["ho_ten"]}' + (f', kèm {so} dòng bồi thường đất.' if so else '.'))
        csdl.ghi_nhat_ky(con, 'Chuyển thửa', tb)
    return tb


def goi_y_gop(con, ma_ho: int) -> list:
    """Các hộ khác xếp theo mức giống (cùng tên trước): [(ma_ho, mô tả, cùng_tên)]."""
    ho = doc_ho(con, ma_ho)
    ten = bo_dau(ho['ho_ten'])
    kq = []
    for r in con.execute('''SELECT h.ma_ho, h.ho_ten, h.dia_chi, COUNT(t.ma_thua) AS so_thua FROM ho h
                            LEFT JOIN thua t ON t.ma_ho = h.ma_ho WHERE h.ma_ho <> ? GROUP BY h.ma_ho
                            ORDER BY h.thu_tu''', (ma_ho,)):
        cung = bo_dau(r['ho_ten']) == ten
        kq.append((r['ma_ho'], f'{r["ma_ho"]} - {r["ho_ten"]} - {r["dia_chi"]} ({r["so_thua"]} thửa)', cung))
    kq.sort(key=lambda x: not x[2])
    return kq

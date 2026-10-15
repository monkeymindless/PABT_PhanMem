"""Lập dự án mới từ dữ liệu thô (giao diện "Dự án mới"): thông tin dự án + danh sách hộ, thửa + bảng giá đất dự án
-> tạo file .pabt (lấy bộ đơn giá tích hợp) -> tự lập phương án từng hộ (mục 1 từ thửa, hỗ trợ theo gợi ý) -> 2 bảng in.

Dữ liệu thô là các dòng dict theo COT_THO (mỗi dòng một thửa; họ tên để trống = thửa tiếp của hộ phía trên).
"""
from __future__ import annotations
from pathlib import Path

from . import csdl, don_gia, in_an, lap_pa, nhap_tho
from .ho_so import chuan_loai_dat
from .nhap_excel import chuan_cccd
from .lap_pa import BoSoan, DanhMuc, LoiNhap, bo_dau, doc_so
from .nghiep_vu import MUC_KHOAN, so_vi_tri, tinh_tat_ca
from .tien import KHONG, chuoi, so_vn

COT_THO = [('ho_ten', 'Họ và tên'), ('dia_chi', 'Địa chỉ'), ('so_cccd', 'Số CCCD'), ('ngay_cap', 'Ngày cấp'),
           ('noi_cap', 'Nơi cấp'), ('dien_thoai', 'Số điện thoại'), ('so_to', 'Số tờ bản đồ'), ('so_thua', 'Số thửa đất'),
           ('dt_thu_hoi', 'Diện tích thu hồi (m²)'), ('loai_dat', 'Loại đất thu hồi'), ('vi_tri', 'Vị trí đất'),
           ('nhan_khau', 'Nhân khẩu'), ('nguon_goc', 'Nguồn gốc'), ('ghi_chu', 'Ghi chú')]
VI_TRI = ['1', '2', '3', '4', '5']                     # vị trí đất theo bảng giá đất (chọn hoặc gõ tay)


def ds_loai_dat() -> list:
    """Danh sách chọn loại đất: [(mã, tên, nhóm)] theo bộ đơn giá."""
    con = csdl.mo(don_gia.file_dang_dung(), chi_doc=True)
    try:
        return [(r[0], r[1], r[2]) for r in con.execute('SELECT ma, ten, nhom FROM dm_loaidat ORDER BY nhom DESC, ma')]
    finally:
        con.close()


def _gon(v) -> str:
    return ' '.join(str(v if v is not None else '').split())


def dong_tu_excel(file_excel) -> tuple:
    """Đọc file Excel bất kỳ (tự nhận cột) thành các dòng thô. Trả (dòng, KetQuaDoc)."""
    kq = nhap_tho.doc(file_excel)
    dong = []
    ho = {h['ma_ho']: h for h in kq.ho}
    co_thua = set()
    for t in sorted(kq.thua, key=lambda x: x['dong']):
        h = ho[t['ma_ho']]
        dau = t['ma_ho'] not in co_thua
        co_thua.add(t['ma_ho'])
        dong.append(dict(ho_ten=h['ho_ten'], dia_chi=h['dia_chi'], so_cccd=h['so_cccd'], ngay_cap=h['ngay_cap'],
                         noi_cap=h['noi_cap'], dien_thoai=h['dien_thoai'],
                         nhan_khau=h.get('nhan_khau', '') if dau else '', so_to=t['so_to'], so_thua=t['so_thua'],
                         loai_dat=t['loai_dat'], dt_thu_hoi=so_vn(t['dt_thu_hoi']) if t['dt_thu_hoi'] != '0' else '',
                         vi_tri=t['vi_tri'], nguon_goc=t['nguon_goc'], ghi_chu='; '.join(h['ghi_chu']) if dau else ''))
    for h in kq.ho:
        if h['ma_ho'] not in co_thua:
            dong.append(dict(ho_ten=h['ho_ten'], dia_chi=h['dia_chi'], so_cccd=h['so_cccd'], ngay_cap=h['ngay_cap'],
                             noi_cap=h['noi_cap'], dien_thoai=h['dien_thoai'],
                             nhan_khau=h.get('nhan_khau', ''), ghi_chu='; '.join(h['ghi_chu'])))
    return dong, kq


def gom(dong: list) -> tuple:
    """Dòng thô -> (hộ, thửa, lỗi chặn, cảnh báo). Cùng CCCD (hoặc cùng họ tên + địa chỉ) là một hộ."""
    ho, thua, loi, cb = [], [], [], []
    theo_khoa, truoc = {}, None
    for i, r in enumerate(dong, start=1):
        g = {k: _gon(r.get(k)) for k, _ in COT_THO}
        if not any(g.values()):
            continue
        if g['ho_ten']:
            cccd = chuan_cccd(g['so_cccd'])
            khoa = ('cccd', cccd) if cccd else ('ten', bo_dau(g['ho_ten']), bo_dau(g['dia_chi']))
            h = theo_khoa.get(khoa)
            if h is None:
                h = dict(ma_ho=len(ho) + 1, ho_ten=g['ho_ten'], dia_chi=g['dia_chi'], so_cccd=cccd, ngay_cap=g['ngay_cap'],
                         noi_cap=g['noi_cap'], dien_thoai=g['dien_thoai'], nhan_khau=None, ghi_chu=[])
                theo_khoa[khoa] = h
                ho.append(h)
        elif truoc is not None:
            h = truoc
        else:
            loi.append(f'Dòng {i}: chưa có họ tên.')
            continue
        truoc = h
        r['_ma_ho'] = h['ma_ho']                         # liên kết dòng thô -> hộ (lưu vào vùng tho_nhap)
        if g['nhan_khau']:
            try:
                nk = doc_so(g['nhan_khau'], f'Dòng {i}: nhân khẩu', toi_da=200)
                if nk != int(nk):
                    raise LoiNhap(f'Dòng {i}: nhân khẩu phải là số nguyên.')
                h['nhan_khau'] = int(nk) or None
            except LoiNhap as e:
                loi.append(str(e))
        if g['ghi_chu'] and g['ghi_chu'] not in h['ghi_chu']:
            h['ghi_chu'].append(g['ghi_chu'])
        if not (g['so_to'] or g['so_thua'] or g['dt_thu_hoi']):
            continue
        try:
            dt = doc_so(g['dt_thu_hoi'], f'Dòng {i}: DT thu hồi')
        except LoiNhap as e:
            loi.append(str(e))
            continue
        if dt <= 0:
            cb.append(f'Dòng {i}: {h["ho_ten"]} tờ {g["so_to"]} thửa {g["so_thua"]} chưa có diện tích thu hồi.')
        if not g['loai_dat']:
            cb.append(f'Dòng {i}: {h["ho_ten"]} tờ {g["so_to"]} thửa {g["so_thua"]} chưa có loại đất.')
        r['_ma_thua'] = len(thua) + 1
        thua.append(dict(ma_thua=len(thua) + 1, ma_ho=h['ma_ho'], so_to=g['so_to'], so_thua=g['so_thua'],
                         loai_dat=chuan_loai_dat(g['loai_dat']), dt_thu_hoi=chuoi(dt), nguon_goc=g['nguon_goc'],
                         vi_tri=g['vi_tri'], thu_tu=len(thua) + 1))
    if not ho:
        loi.append('Chưa có hộ nào (cần ít nhất cột Họ và tên).')
    return ho, thua, loi, cb


def loai_dat_biet() -> dict:
    """Mã loại đất trong bộ đơn giá -> nhóm đất."""
    con = csdl.mo(don_gia.file_dang_dung(), chi_doc=True)
    try:
        return {r[0].upper(): r[1] for r in con.execute('SELECT ma, nhom FROM dm_loaidat')}
    finally:
        con.close()


def khoa_gia(loai_dat: str, vi_tri: str, biet: dict) -> tuple:
    """(loại đất dùng tra giá, vị trí): thửa ghi nhiều loại thì lấy loại đầu tiên có trong danh mục (như khi lập mục 1)."""
    ds = [x.strip().upper() for x in str(loai_dat or '').replace(',', '+').split('+') if x.strip()]
    return next((x for x in ds if x in biet), ''), so_vi_tri(vi_tri)


def bang_gia_can_nhap(dong: list, biet: dict | None = None) -> list:
    """Các cặp (loại đất, vị trí) cần giá đất: [dict(loai_dat, vi_tri, nhom, so_thua, ghi_chu)]."""
    biet = loai_dat_biet() if biet is None else biet
    _, thua, _, _ = gom(dong)
    dem, ghep = {}, {}
    for t in thua:
        k = khoa_gia(t['loai_dat'], t['vi_tri'], biet)
        dem[k] = dem.get(k, 0) + 1
        if '+' in t['loai_dat']:
            ghep[k] = ghep.get(k, 0) + 1
    kq = []
    for (ld, vt), n in sorted(dem.items()):
        gc = []
        if not ld:
            gc.append('loại đất không có trong danh mục')
        if not vt:
            gc.append('chưa có vị trí')
        if ghep.get((ld, vt)):
            gc.append(f'{ghep[(ld, vt)]} thửa ghi loại đất ghép: nên tách diện tích theo từng loại')
        kq.append(dict(loai_dat=ld, vi_tri=vt, nhom=biet.get(ld, ''), so_thua=n, ghi_chu='; '.join(gc)))
    return kq


def tao_du_an(file_pabt, thong_tin: dict, dong: list, bang_gia: list, tu_lap: bool = True, nguon: str = '') -> dict:
    """Tạo file dự án từ dữ liệu thô. bang_gia: [dict(loai_dat, vi_tri, gia, he_so_k)].
    Trả báo cáo dict(so_ho, so_thua, so_ho_co_pa, tong, canh_bao). Lỗi dữ liệu thì báo LoiNhap, không tạo file."""
    dong = [dict(r) for r in dong]
    ho, thua, loi, cb = gom(dong)
    if loi:
        raise LoiNhap('Dữ liệu thô còn lỗi:\n' + '\n'.join('- ' + x for x in loi[:30]))
    gia = []
    for g in bang_gia:
        vt = so_vi_tri(g.get('vi_tri')) or so_vi_tri(g.get('vi_tri_ap'))
        if not g.get('loai_dat') or not vt or not _gon(g.get('gia')):
            continue
        g = dict(g, vi_tri=vt)
        ten = f'Giá {g["loai_dat"]} vị trí {vt}'
        gt = doc_so(g['gia'], ten)
        k = doc_so(g.get('he_so_k') or '1', f'{ten}: hệ số K') or 1
        if gt > 0:
            cc = _gon(g.get('ghi_chu')) if str(g.get('ghi_chu', '')).startswith('NQ 28/2025') else 'Nhập khi lập dự án'
            gia.append((g['loai_dat'], str(g['vi_tri']), chuoi(gt), chuoi(k), cc))
    # thửa chưa ghi vị trí: gán "vị trí áp dụng" người lập nhập ở bảng giá đất
    biet = loai_dat_biet()
    ap = {g['loai_dat']: so_vi_tri(g.get('vi_tri_ap')) for g in bang_gia
          if not g.get('vi_tri') and so_vi_tri(g.get('vi_tri_ap'))}
    for t in thua:
        ld, vt = khoa_gia(t['loai_dat'], t['vi_tri'], biet)
        if not vt and ap.get(ld):
            t['vi_tri'] = ap[ld]
    tt = {k: _gon(thong_tin.get(k)) for k, _ in lap_pa.TRUONG_DU_AN}
    if not tt['ten']:
        raise LoiNhap('Tên dự án không được để trống.')
    p = Path(file_pabt)
    con, tam = csdl.tao_moi_tam(p)                     # nguyên tử: dựng ở file tạm, xong mới thay file đích (file cũ không mất)
    xong = False
    # file mới đang tạo: không ép ghi đĩa sau mỗi hộ (tự lập N hộ = N lần ghi, chậm trên ổ HDD / thư mục Google Drive); ép ghi một
    # lần khi xong (csdl.hoan_tat_tao_moi). Mất điện giữa chừng chỉ hỏng file đang tạo dở - tạo lại; file dự án đang dùng không ảnh hưởng.
    con.execute('PRAGMA synchronous = OFF')
    # nhật ký giao dịch trong RAM (vẫn rollback được): journal_mode DELETE tạo rồi xóa file "-journal" mỗi giao dịch = mỗi hộ tự
    # lập (3.000 hộ: 1,5 s chỉ cho việc này). Không lưu vào file - lần mở sau csdl.mo đặt lại DELETE.
    con.execute('PRAGMA journal_mode = MEMORY')
    try:
        don_gia.ap_vao_du_an(con)
        lap_pa.luu_du_an(con, dict(tt, ten_day_du=tt.get('ten_day_du') or tt['ten'], cap_dia_ban=tt['cap_dia_ban'] or 'Xã'))
        with con, csdl.mo_khoa_danh_muc(con):
            for i, h in enumerate(ho, start=1):
                con.execute('''INSERT INTO ho (ma_ho, thu_tu, ho_ten, so_cccd, ngay_cap, noi_cap, dia_chi, dien_thoai, ghi_chu,
                               nhan_khau) VALUES (?,?,?,?,?,?,?,?,?,?)''',
                            (h['ma_ho'], i, h['ho_ten'], h['so_cccd'], h['ngay_cap'], h['noi_cap'], h['dia_chi'], h['dien_thoai'],
                             '; '.join(h['ghi_chu']), h['nhan_khau']))
            con.executemany('''INSERT INTO thua (ma_thua, ma_ho, so_to, so_thua, loai_dat, dt_thu_hoi, nguon_goc, vi_tri, thu_tu)
                               VALUES (:ma_thua,:ma_ho,:so_to,:so_thua,:loai_dat,:dt_thu_hoi,:nguon_goc,:vi_tri,:thu_tu)''', thua)
            con.executemany('''INSERT INTO gia_dat (xa_phuong, loai_dat, vi_tri, gia, he_so_k, can_cu)
                               VALUES (?, ?, ?, ?, ?, ?)''', [(tt['ten_dia_ban'], *g) for g in gia])
            con.executemany(f'''INSERT INTO tho_nhap (dong, nguon, {', '.join(k for k, _ in COT_THO)}, ma_ho, ma_thua)
                               VALUES (?, ?, {', '.join('?' * len(COT_THO))}, ?, ?)''',
                            [(i, nguon, *(_gon(r.get(k)) for k, _ in COT_THO), r.get('_ma_ho'), r.get('_ma_thua'))
                             for i, r in enumerate(dong, start=1) if any(_gon(r.get(k)) for k, _ in COT_THO)])
            con.execute('UPDATE du_an SET nguon_nhap = ?, ngay_nhap = datetime(\'now\', \'localtime\') WHERE id = 1',
                        (nguon or 'Nhập thô (Dự án mới)',))
            csdl.ghi_nhat_ky(con, 'Lập dự án mới', f'{len(ho)} hộ, {len(thua)} thửa, {len(gia)} giá đất')
        if tu_lap:
            cb += tu_lap_phuong_an(con)
        kq = tinh_tat_ca(con)
        bao_cao = dict(file=str(p), so_ho=len(ho), so_thua=len(thua), so_ho_co_pa=sum(1 for k in kq if k.tong > 0),
                       tong=sum((k.tong for k in kq), KHONG), canh_bao=cb)
        xong = True
    finally:
        con.close()
        if not xong:
            csdl.huy_tao_moi(tam)
    csdl.hoan_tat_tao_moi(tam, p)                      # fsync một lần + os.replace (thay _ghi_xuong_dia)
    return bao_cao


def tu_lap_phuong_an(con, ds_ma_ho: list | None = None) -> list:
    """Mỗi hộ: mục 1 = từng thửa (DT, loại đất, vị trí, giá theo bảng giá đất), mục 4 = áp dụng gợi ý hỗ trợ; lưu.
    Hộ đã có phương án thì bỏ qua. Trả danh sách cảnh báo."""
    dm = DanhMuc(con)
    cb = []
    ds = ds_ma_ho or [r[0] for r in con.execute('SELECT ma_ho FROM ho ORDER BY thu_tu, ma_ho')]
    for ma in ds:
        bo = BoSoan(con, ma, dm)
        if bo.pa.dat or any(bo.pa.khoan[m] for m in MUC_KHOAN):
            continue
        ten = f'Hộ {ma} {bo.pa.ho.ho_ten}'
        for mt, mo_ta, con_lai in bo.thua_cua_ho():
            if con_lai <= 0:
                continue
            i, tb = bo.them_thua(mt)
            d = bo.pa.dat[i]
            if not d.loai_dat:
                bo.xoa(1, i)
                cb.append(f'{ten}: {bo.ten_thua(mt)} loại đất không có trong danh mục, chưa đưa vào mục 1.')
            elif d.gia_bang_gia <= 0:
                cb.append(f'{ten}: {bo.ten_thua(mt)} chưa có giá {d.loai_dat} vị trí {d.vi_tri or "?"}.')
            elif tb.startswith('Kiểm kê ghi'):
                cb.append(f'{ten}: {tb}')
        de_xuat, _ = bo.goi_y()
        bo.ap_dung_goi_y(de_xuat)
        if bo.pa.dat or any(bo.pa.khoan[m] for m in MUC_KHOAN):
            bo.luu(tu_dong=True, mo_lai=False)  # "Phương án tự lập - chưa soát": chưa tính là đã lập (in_an.phan_loai_lap)
    return cb


def xuat_2_bang(con, thu_muc, pdf: bool = False, bao_tien_do=None, bao_excel=None) -> dict:
    """Xuất phương án chi tiết từng hộ (IN_CHITIET) và bảng tổng hợp (IN_BANGTONGHOP). bao_tien_do(i, n) / bao_excel(i, n):
    báo tiến độ, trả True để dừng (như in_an.xuat_hang_loat)."""
    ds = in_an.ho_co_phuong_an(con)
    if not ds:
        raise LoiNhap('Chưa có hộ nào có phương án để in.')
    return in_an.xuat_hang_loat(con, ds, thu_muc, pdf=pdf, bang_tong_hop=True, bao_tien_do=bao_tien_do, bao_excel=bao_excel)

"""Báo cáo tiến độ giải phóng mặt bằng (Nhóm 6, Bước 16): số liệu cho bảng điều hành (Dashboard).

  * Tỷ lệ giải ngân tiền bồi thường = tiền hộ đã nhận / tổng tiền đã phê duyệt;
  * Tỷ lệ diện tích mặt bằng sạch đã bàn giao = diện tích thu hồi của hộ đã bàn giao / tổng diện tích thu hồi;
  * Thửa chưa bàn giao mặt bằng (còn vướng mắc) cần giải tỏa gấp: thửa của hộ ĐÃ có quyết định phê duyệt mà chưa bàn giao mặt bằng, xếp mức ưu tiên:
      gap       hộ đủ điều kiện cưỡng chế (vận động quá hạn), hoặc đã nhận đủ tiền mà chưa bàn giao và cùng tờ bản đồ với
                thửa đã giải tỏa xong (thửa bị bao quanh bởi mặt bằng sạch);
      cao       đã nhận đủ tiền chưa bàn giao, hoặc đang trong thời gian vận động;
      theo_doi  còn lại (đã phê duyệt, chưa nhận tiền).
Không phụ thuộc Qt.
"""
from __future__ import annotations

from . import thoi_han, van_dong
from .tien import D, KHONG

MUC = ('gap', 'cao', 'theo_doi')
TEN_MUC = dict(gap='Gấp', cao='Cao', theo_doi='Theo dõi')


def _pt(a, b) -> float:
    return float(a * 100 / b) if b else 0.0


def _so(v):
    s = str(v if v is not None else '').strip()
    return D(s) if s else KHONG


def tong_quan(con, hom_nay=None, ds=None, tt=None, moc=None) -> dict:
    """ds / tt / moc: tổng hợp hộ (theo_doi.tong_hop), trạng thái vận động, mốc thu hồi đã tính sẵn - trang Tiến độ chi trả & Bàn
    giao (1.0.00) tính MỘT lần cho cả bảng theo hộ lẫn thẻ chỉ số / bảng thửa còn vướng."""
    from . import theo_doi
    nay = thoi_han.hom_nay_hoac(hom_nay)
    ds = theo_doi.tong_hop(con, tinh_pa=False) if ds is None else ds
    tt = van_dong.tinh_trang_tat_ca(con, ds, nay) if tt is None else tt
    moc = thoi_han.moc_thu_hoi_tat_ca(con, None, nay) if moc is None else moc
    tong_pd = sum((x.tong_phe_duyet for x in ds), KHONG)
    da_chi = sum((x.da_nhan for x in ds), KHONG)
    dt_tong = sum((x.dt for x in ds), KHONG)
    dt_bg = sum((x.dt for x in ds if x.da_ban_giao), KHONG)
    # theo tờ bản đồ: (số thửa đã giải tỏa, tổng số thửa) - thửa chưa bàn giao nằm trong tờ đã giải tỏa phần lớn là thửa còn vướng mắc xen kẹt
    to = {}
    for x in ds:
        for t in x.thua:
            k = to.setdefault(t['so_to'] or '', [0, 0])
            k[1] += 1
            k[0] += bool(x.da_ban_giao)
    thua = []
    for x in ds:
        if not x.qd or x.da_ban_giao:
            continue
        nhan_du = not x.qd_chua_nhan
        ma_tt, chu_tt = van_dong.trang_thai_chung(tt.get(x.ma_ho, []))
        so_ngay = max((t.da_qua for t in tt.get(x.ma_ho, []) if t.ma in ('dang_van_dong', 'du_dk_cuong_che')), default=0)
        ly_do = []
        if x.qd_chua_nhan:
            ly_do.append('Chưa nhận tiền: ' + '; '.join(
                f'QĐ {q["so_qd"]}' + (f' ({q["ly_do_chua_nhan"]})' if q['ly_do_chua_nhan'] else '') for q in x.qd_chua_nhan))
        ly_do.append('Chưa bàn giao' + (f': {x.ly_do_ban_giao}' if x.ly_do_ban_giao else ''))
        for t in (x.thua or [dict(so_to='', so_thua='', dt_thu_hoi='', loai_dat='')]):
            gt = to.get(t['so_to'] or '', [0, 0])
            bao_quanh = gt[0] > 0
            if ma_tt == 'du_dk_cuong_che' or (nhan_du and bao_quanh):
                muc = 'gap'
            elif nhan_du or ma_tt == 'dang_van_dong':
                muc = 'cao'
            else:
                muc = 'theo_doi'
            thua.append(dict(ma_ho=x.ma_ho, thu_tu=x.thu_tu, ho_ten=x.ho_ten, so_to=t['so_to'], so_thua=t['so_thua'],
                             dt=_so(t['dt_thu_hoi']), loai_dat=t['loai_dat'], muc=muc, ly_do='; '.join(ly_do),
                             van_dong=chu_tt, ma_van_dong=ma_tt, so_ngay_van_dong=so_ngay,
                             cung_to=f'{gt[0]}/{gt[1]} thửa đã giải tỏa' if t['so_to'] and gt[1] else '',
                             moc_thu_hoi=moc.get(x.ma_ho, {}).get('chu', '')))
    thua.sort(key=lambda r: (MUC.index(r['muc']), -r['so_ngay_van_dong'], r['thu_tu'], r['ma_ho']))
    cuong_che = {r['ma_ho'] for r in thua if r['ma_van_dong'] == 'du_dk_cuong_che'}
    return dict(
        hom_nay=nay, so_ho=len(ds), so_ho_phe_duyet=sum(1 for x in ds if x.qd), so_ho_chua_pd=sum(1 for x in ds if not x.qd),
        so_ho_nhan_du=sum(1 for x in ds if x.qd and not x.qd_chua_nhan), so_ho_ban_giao=sum(1 for x in ds if x.da_ban_giao),
        tong_pd=tong_pd, da_chi=da_chi, con_lai=tong_pd - da_chi, pt_giai_ngan=_pt(da_chi, tong_pd),
        dt_tong=dt_tong, dt_ban_giao=dt_bg, pt_mat_bang=_pt(dt_bg, dt_tong),
        thua=thua, dem={m: sum(1 for r in thua if r['muc'] == m) for m in MUC}, so_ho_cuong_che=len(cuong_che))


def xuat_excel(con, file, hom_nay=None):
    """Excel báo cáo tiến độ GPMB: chỉ số điều hành + danh sách thửa còn vướng."""
    from . import theo_doi
    from .tien import so_vn, vn
    tq = tong_quan(con, hom_nay)
    da = con.execute('SELECT ten FROM du_an WHERE id = 1').fetchone()
    cot = ['STT', 'Mức ưu tiên', 'Mã hộ', 'Họ và tên', 'Tờ', 'Thửa', 'DT thu hồi (m²)', 'Loại đất', 'Lý do còn vướng',
           'Vận động / cưỡng chế', 'Cùng tờ bản đồ', 'Mốc thu hồi đất']
    dong = [[i, TEN_MUC[r['muc']], r['ma_ho'], r['ho_ten'], r['so_to'], r['so_thua'], r['dt'], r['loai_dat'], r['ly_do'],
             r['van_dong'], r['cung_to'], r['moc_thu_hoi']] for i, r in enumerate(tq['thua'], start=1)]
    tieu = (f'BÁO CÁO TIẾN ĐỘ GIẢI PHÓNG MẶT BẰNG - giải ngân {tq["pt_giai_ngan"]:.1f}% ({vn(tq["da_chi"])} / {vn(tq["tong_pd"])} đ), '
            f'mặt bằng sạch {tq["pt_mat_bang"]:.1f}% ({so_vn(tq["dt_ban_giao"])} / {so_vn(tq["dt_tong"])} m²)')
    return theo_doi.xuat_excel(file, tieu, cot, dong, [5, 10, 7, 24, 6, 7, 12, 12, 40, 36, 20, 36], None, da['ten'] if da else '')

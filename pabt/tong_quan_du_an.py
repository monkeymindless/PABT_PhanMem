"""Số liệu màn hình tổng quan dự án (1.0.07 - "Executive Project Cockpit", người dùng 20/10/2026): hiện ở Màn hình chính khi ĐÃ mở dự
án. Không Qt. Nguồn: các dòng danh sách hộ (CuaSoChinh.mo_hinh.dong - cùng nguồn với thẻ số liệu, nấc tiến độ phân tích tự động
theo_doi.phan_tich_tien_do), bảng dot_du_thao (niêm yết), ho.ma_vuong (V1-V5), van_dong (cưỡng chế). Số tiền / diện tích Decimal.
"""
from __future__ import annotations

from datetime import date, datetime

from .tien import D, phan_tram

HO_DANG_LAM_TOI_DA = 200        # danh sách hộ đang làm dở: hiện tối đa chừng này hộ (dự án 10.000 hộ không dựng 10.000 nút)


def _hom_nay(hom_nay=None) -> date:
    if hom_nay is None:
        return date.today()
    return hom_nay.date() if isinstance(hom_nay, datetime) else hom_nay


def quy_mo(dong: list) -> dict:
    """Số hộ, số thửa, diện tích thu hồi (m², ha)."""
    so_thua = sum(int(d['o'][3] or 0) for d in dong if d.get('o'))
    dt = sum((D(d.get('dt') or 0) for d in dong), D(0))
    return dict(so_ho=len(dong), so_thua=so_thua, dt_m2=dt, dt_ha=dt / D(10000))


def kinh_phi(dong: list) -> dict:
    """Tổng kinh phí phương án; tách đất (mục 1) và tài sản, hỗ trợ, thưởng (phần còn lại)."""
    tong = sum((D(d.get('tong') or 0) for d in dong), D(0))
    dat = sum((D((d.get('muc') or {}).get(1) or 0) for d in dong), D(0))
    return dict(tong=tong, dat=dat, con_lai=tong - dat)


def tien_do(dong: list) -> dict:
    n = len(dong)
    pd = sum(1 for d in dong if d.get('da_phe_duyet'))
    bg = sum(1 for d in dong if d.get('da_ban_giao'))
    lap = sum(1 for d in dong if d.get('da_lap'))
    return dict(n=n, da_lap=lap, da_pd=pd, da_bg=bg, pt_pd=phan_tram(pd, n) if n else '0%', pt_bg=phan_tram(bg, n) if n else '0%')


def ho_dang_lam(dong: list, toi_da: int = HO_DANG_LAM_TOI_DA) -> list:
    """Hộ chưa có quyết định phê duyệt: chưa lập phương án trước, rồi đã lập chưa duyệt; theo thứ tự danh sách. Mỗi phần tử: dict
    (ma_ho, stt, ho_ten, trang_thai, tong, da_lap)."""
    kq = []
    for d in dong:
        if d.get('da_phe_duyet'):
            continue
        o = d.get('o') or [None, '', '', 0, 0, '', '']
        kq.append(dict(ma_ho=d['ma_ho'], stt=o[0], ho_ten=o[1] or '', trang_thai=o[5] or '', tong=D(d.get('tong') or 0),
                       da_lap=bool(d.get('da_lap'))))
    kq.sort(key=lambda x: (x['da_lap'], x['stt'] if isinstance(x['stt'], int) else 0))
    return kq[:toi_da]


def niem_yet(con, hom_nay=None) -> dict | None:
    """Đợt niêm yết đang chạy (hoặc đợt gần nhất): tên, ngày kết thúc, số ngày còn (âm = đã quá), hạn đối thoại. None: chưa có đợt."""
    from . import du_thao
    nay = _hom_nay(hom_nay)
    try:
        ds = du_thao.ds_dot(con)
    except Exception:                                   # file cũ chưa có bảng đợt niêm yết
        return None
    if not ds:
        return None
    dang = [x for x in ds if x.get('trang_thai') == 'dang_niem_yet'] or ds
    x = dang[-1]
    kq = dict(ten=x.get('ten') or f'Đợt {x["id"]}', ngay_bat_dau=x.get('ngay_bat_dau') or '', ngay_ket_thuc=x.get('ngay_ket_thuc') or '',
              han_doi_thoai=x.get('han_doi_thoai') or '', con_ngay=None, con_ngay_doi_thoai=None,
              so_ngay=du_thao.SO_NGAY_NIEM_YET)
    for k, ra in (('ngay_ket_thuc', 'con_ngay'), ('han_doi_thoai', 'con_ngay_doi_thoai')):
        try:
            kq[ra] = (du_thao.doc_ngay(kq[k]).date() - nay).days if kq[k] else None
        except (ValueError, TypeError):
            kq[ra] = None
    return kq


def so_ho_vuong(con) -> int:
    """Số hộ đánh dấu vướng V1-V5 (không đủ điều kiện niêm yết)."""
    try:
        return int(con.execute("SELECT COUNT(*) FROM ho WHERE TRIM(COALESCE(ma_vuong, '')) <> ''").fetchone()[0])
    except Exception:
        return 0


def cuong_che(con, hom_nay=None) -> dict:
    """Vận động / cưỡng chế (Điều 89 Luật Đất đai 2024): số hộ đang vận động, số hộ đủ điều kiện đề nghị cưỡng chế."""
    from . import theo_doi, van_dong
    try:
        ds = theo_doi.tong_hop(con, tinh_pa=False)
        tt = van_dong.tinh_trang_tat_ca(con, ds, hom_nay)
    except Exception:
        return dict(dang_vd=0, du_cc=0)
    dang = du = 0
    for v in tt.values():
        ma, _ = van_dong.trang_thai_chung(v)
        dang += ma == 'dang_van_dong'
        du += ma == 'du_dk_cuong_che'
    return dict(dang_vd=dang, du_cc=du)


def tinh(con, dong: list, hom_nay=None) -> dict:
    return dict(quy_mo=quy_mo(dong), kinh_phi=kinh_phi(dong), tien_do=tien_do(dong), ho_dang_lam=ho_dang_lam(dong),
                so_ho_dang_lam=sum(1 for d in dong if not d.get('da_phe_duyet')),
                niem_yet=niem_yet(con, hom_nay), so_ho_vuong=so_ho_vuong(con), cuong_che=cuong_che(con, hom_nay))

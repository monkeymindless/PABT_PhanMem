"""Đối chiếu phương án hai hộ (1.0.58, Gói 3 đề án V2.0: "đối chiếu giữa các hộ dân") - chỉ đọc, không Qt.

Đề án muốn mở song song nhiều tab soạn; thanh tab đã bỏ từ 0.9.94 và hai cửa sổ cùng soạn một file dễ ghi đè nhau, nên đối chiếu là
bảng CHỈ ĐỌC theo số liệu ĐÃ LƯU: ghép dòng cùng mục + tên + ĐVT, cùng tài sản mà khác đơn giá thì báo (lỗi hay gặp khi rà soát)."""
from __future__ import annotations

from .lap_pa import bo_dau
from .nghiep_vu import MUC_VN, TEN_MUC_NGAN, BoiCanh, doc_phuong_an, he_so, thanh_tien_dong, thanh_tien_dong_dat, tinh_pa, so_muc
from .tien import D

THU_TU_MUC = (1, 2, 3, MUC_VN, 4)


def _dong_hien(bc, muc: int, d) -> dict:
    if muc == 1:
        ten = ' - '.join(x for x in (d.loai_dat, d.vi_tri) if x) or 'Đất'
        return dict(ten=ten, dvt='m²', so_luong=D(d.dien_tich), don_gia=D(d.gia_bang_gia) * he_so(d.he_so_k), ty_le=he_so(d.ty_le),
                    thanh_tien=thanh_tien_dong_dat(d, bc))
    return dict(ten=d.ten, dvt=d.dvt, so_luong=D(d.so_luong), don_gia=D(d.don_gia), ty_le=he_so(d.ty_le),
                thanh_tien=thanh_tien_dong(d, bc))


def _theo_khoa(bc, pa) -> dict:
    """{(mục, tên bỏ dấu, ĐVT bỏ dấu, lần xuất hiện): dòng} - dòng cùng tên ghi hai lần ghép theo thứ tự."""
    kq, dem = {}, {}
    for muc in THU_TU_MUC:
        for d in (pa.dat if muc == 1 else pa.khoan[muc]):
            x = _dong_hien(bc, muc, d)
            k = (muc, ' '.join(bo_dau(x['ten']).split()), bo_dau(x['dvt'] or ''))
            n = dem.get(k, 0)
            dem[k] = n + 1
            kq[(*k, n)] = x
    return kq


def so_sanh(con, ma_a: int, ma_b: int) -> dict:
    """{'dong': [{muc, so_muc, ten_muc, ten, dvt, a, b, khac_gia, khac_sl, khac_tien, chi_mot}], 'ten_a', 'ten_b', 'tong_a', 'tong_b',
    'so_khac_gia'} - a / b: dòng của hộ (None = hộ không có dòng này). Thứ tự: theo mục, trong mục theo thứ tự hộ A rồi phần riêng hộ B."""
    bc = BoiCanh.tu(con)
    pa_a, pa_b = doc_phuong_an(con, ma_a), doc_phuong_an(con, ma_b)
    a, b = _theo_khoa(bc, pa_a), _theo_khoa(bc, pa_b)
    dong = []
    for k in [*a, *[x for x in b if x not in a]]:
        xa, xb = a.get(k), b.get(k)
        goc = xa or xb
        co_hai = xa is not None and xb is not None
        dong.append(dict(muc=k[0], so_muc=so_muc(k[0]), ten_muc=TEN_MUC_NGAN.get(k[0], ''), ten=goc['ten'], dvt=goc['dvt'], a=xa, b=xb,
                         khac_gia=co_hai and xa['don_gia'] != xb['don_gia'],
                         khac_sl=co_hai and xa['so_luong'] != xb['so_luong'],
                         khac_tien=not co_hai or xa['thanh_tien'] != xb['thanh_tien'],
                         chi_mot='' if co_hai else ('a' if xa is not None else 'b')))
    dong.sort(key=lambda x: THU_TU_MUC.index(x['muc']))         # sort ổn định: giữ thứ tự trong từng mục
    return dict(dong=dong, ten_a=pa_a.ho.ho_ten, ten_b=pa_b.ho.ho_ten, tong_a=tinh_pa(pa_a, bc).tong, tong_b=tinh_pa(pa_b, bc).tong,
                so_khac_gia=sum(1 for x in dong if x['khac_gia']))

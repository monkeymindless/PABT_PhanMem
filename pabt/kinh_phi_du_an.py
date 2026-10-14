"""Bảng tổng hợp kinh phí dự án (Nhóm 5, Bước 8): cơ cấu kinh phí theo nhóm khoản, đối soát với Bảng khái toán ban đầu (Pre-F/S).

Cơ cấu: Đất / Nhà, công trình / Cây trồng, vật nuôi / Hỗ trợ / Thưởng (số theo phương án, đối chiếu số đã phê duyệt trong các
quyết định), cộng bồi thường - hỗ trợ - tái định cư, kinh phí tổ chức thực hiện bồi thường (QĐ 08/2025/QĐ-UBND: theo tuyến tối
đa 3,5%, loại khác 2,5% - lap_pa.kinh_phi_to_chuc), tổng kinh phí dự án. Không phụ thuộc Qt.
"""
from __future__ import annotations

from pathlib import Path

from . import csdl, theo_doi
from .tien import D, KHONG, lam_tron

# (mã mục của nghiep_vu.muc_5_cot, tên hiển thị, cột tương ứng trong qd_ho)
NHOM_KINH_PHI = (
    (1, 'Tiền bồi thường về đất', 'tien_dat'),
    (2, 'Tiền bồi thường tài sản (nhà, công trình)', 'tien_tai_san'),
    (3, 'Cây trồng, vật nuôi', 'tien_cay'),
    (4, 'Các khoản hỗ trợ, tái định cư', 'tien_ho_tro'),
    (5, 'Thưởng bàn giao mặt bằng', 'tien_thuong'),
)
KHOA_FILE_KHAI_TOAN = 'FILE_KHAI_TOAN'          # cai_dat: đường dẫn file .pabtdt dùng đối soát (nhớ theo dự án)


def _so(v):
    s = str(v if v is not None else '').strip()
    return D(s) if s else KHONG


def _pt(a, tong) -> float:
    return float(a * 100 / tong) if tong else 0.0


def co_cau(con) -> dict:
    """Cơ cấu kinh phí của dự án. dong: [dict(loai, ma, ten, tien_pa, tien_pd, chua_pd, chenh, ty_trong, so_ho, ghi_chu)]; loai là
    'nhom' (5 nhóm khoản) / 'cong' (cộng bồi thường, hỗ trợ, TĐC) / 'kinh_phi' (tổ chức thực hiện) / 'tong' (tổng kinh phí).
    tien_pa: theo phương án của MỌI hộ; tien_pd: số đã phê duyệt trong các quyết định; chua_pd: phương án của các hộ CHƯA có quyết
    định nào; chenh: phương án của các hộ ĐÃ có quyết định - số phê duyệt (so cùng tập hộ; khác 0 = quyết định ghi khác phương án).
    ty_trong (đặc tả V10 - sửa lỗi hiện 2,4% / 3,4%): GỐC 100% là "Cộng bồi thường, hỗ trợ, tái định cư" - 5 nhóm cộng lại 100%, dòng
    cộng 100%, dòng kinh phí tổ chức thực hiện = ĐÚNG tỷ lệ QĐ 08/2025 (2,5% / 3,5%), dòng tổng kinh phí = 100% + tỷ lệ đó (102,5% /
    103,5%). Trước đây lấy mẫu số là tổng kinh phí nên ra 2,4% / 97,6%."""
    from .lap_pa import CAN_CU_KINH_PHI, LOAI_KINH_PHI, kinh_phi_to_chuc
    ds = theo_doi.tong_hop(con)
    pa = {m: KHONG for m, _, _ in NHOM_KINH_PHI}
    pa_duyet = dict(pa)                                    # phương án của các hộ đã có quyết định (cùng tập hộ với số phê duyệt)
    so_ho = dict.fromkeys(pa, 0)
    for x in ds:
        for m in pa:
            v = x.muc_pa.get(m, KHONG)
            pa[m] += v
            so_ho[m] += v > 0
            if x.qd:
                pa_duyet[m] += v
    pd = {m: KHONG for m in pa}
    cot = [c for _, _, c in NHOM_KINH_PHI]
    for r in con.execute(f'SELECT {", ".join(cot)} FROM qd_ho'):
        for (m, _, _), v in zip(NHOM_KINH_PHI, r):
            pd[m] += _so(v)
    cong_pa, cong_pd, cong_duyet = sum(pa.values(), KHONG), sum(pd.values(), KHONG), sum(pa_duyet.values(), KHONG)
    loai, tl, tu_nhan = kinh_phi_to_chuc(con)
    kp = lam_tron(cong_pa * tl / 100, -3)
    tong = cong_pa + kp
    dong = [dict(loai='nhom', ma=m, ten=ten, tien_pa=pa[m], tien_pd=pd[m], chua_pd=pa[m] - pa_duyet[m], chenh=pa_duyet[m] - pd[m],
                 ty_trong=_pt(pa[m], cong_pa), so_ho=so_ho[m], ghi_chu='') for m, ten, _ in NHOM_KINH_PHI]
    dong.append(dict(loai='cong', ma=0, ten='Cộng bồi thường, hỗ trợ, tái định cư', tien_pa=cong_pa, tien_pd=cong_pd,
                     chua_pd=cong_pa - cong_duyet, chenh=cong_duyet - cong_pd, ty_trong=100.0 if cong_pa else 0.0,
                     so_ho=sum(1 for x in ds if x.tong_pa > 0), ghi_chu=''))
    dong.append(dict(loai='kinh_phi', ma=-1, ten=f'Kinh phí tổ chức thực hiện bồi thường ({str(tl).replace(".", ",")}%)',
                     tien_pa=kp, tien_pd=None, chua_pd=None, chenh=None, ty_trong=float(tl), so_ho=None,
                     ghi_chu=f'{LOAI_KINH_PHI[loai][0]}{" - tự nhận theo tên dự án" if tu_nhan else ""}. {CAN_CU_KINH_PHI}'))
    dong.append(dict(loai='tong', ma=-2, ten='TỔNG KINH PHÍ DỰ ÁN', tien_pa=tong, tien_pd=None, chua_pd=None, chenh=None, ty_trong=100.0 + float(tl),
                     so_ho=None, ghi_chu='Cộng bồi thường, hỗ trợ, tái định cư + kinh phí tổ chức thực hiện'))
    return dict(dong=dong, loai_kp=loai, tl_kp=tl, tu_nhan=tu_nhan, so_ho=len(ds), so_ho_da_lap=sum(1 for x in ds if x.da_lap),
                so_ho_phe_duyet=sum(1 for x in ds if x.qd), tong=tong, cong=cong_pa, kinh_phi=kp)


# ---------------------------------------------------------------- đối soát với bảng khái toán (Pre-F/S)
def file_khai_toan(con) -> str:
    return csdl.doc_cai_dat(con, KHOA_FILE_KHAI_TOAN, '')


def dat_file_khai_toan(con, file) -> None:
    """Nhớ file khái toán (.pabtdt) dùng đối soát cho dự án; '' = bỏ."""
    p = str(file or '')
    if p == file_khai_toan(con):
        return
    with csdl.giao_dich(con):
        csdl.ghi_cai_dat(con, KHOA_FILE_KHAI_TOAN, p)
        csdl.ghi_nhat_ky(con, 'File khái toán đối soát', Path(p).name if p else '(bỏ)')


def doi_soat(con, goc) -> dict:
    """Khái toán `goc` (du_toan.DuToan) so với thực tế áp giá của dự án đang mở - du_toan.so_sanh, cùng cơ sở mục 6."""
    from . import du_toan
    return du_toan.so_sanh(goc, du_toan.tu_du_an(con))


def mo_khai_toan(file):
    """Mở file khái toán .pabtdt; không đọc được -> LoiNhap (câu tiếng Việt)."""
    from . import du_toan
    from .lap_pa import LoiNhap
    try:
        return du_toan.DuToan.mo(file)
    except FileNotFoundError:
        raise LoiNhap(f'Không thấy file khái toán:\n{file}') from None
    except (OSError, ValueError, KeyError, TypeError) as e:
        raise LoiNhap(f'Không đọc được file khái toán (không phải file .pabtdt của PABT?):\n{file}') from e

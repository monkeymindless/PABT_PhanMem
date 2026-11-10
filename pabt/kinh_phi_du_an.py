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
# 20/10/2026 (ảnh mẫu người dùng): STT La Mã của bảng cơ cấu (I-V nhóm khoản, VI kinh phí tổ chức thực hiện) và căn cứ áp dụng từng
# nhóm - MẶC ĐỊNH theo các văn bản phần mềm đang dùng; hồ sơ địa phương (pabt_profile.json can_cu_phap_ly.co_cau {"1": …}) ghi đè
STT_NHOM = {1: 'I', 2: 'II', 3: 'III', 4: 'IV', 5: 'V'}
CAN_CU_CO_CAU = {
    1: 'Bảng giá đất (Nghị quyết 28/2025/NQ-HĐND) × hệ số K (Quyết định 03/2026/QĐ-UBND)',
    2: 'Đơn giá nhà, công trình xây dựng của bộ đơn giá đang áp dụng',
    3: 'Đơn giá cây trồng của bộ đơn giá; vật nuôi theo Quyết định 31/2025/QĐ-UBND',
    4: 'Chính sách hỗ trợ theo Quyết định 42/2025/QĐ-UBND (ổn định đời sống, đào tạo chuyển đổi nghề, thuê nhà…)',
    5: 'Biểu thưởng bàn giao mặt bằng của dự án',
}
# dòng con của nhóm I (tiền đất) theo nhóm loại đất - chỉ bảng cơ cấu trên màn hình (co_cau(chi_tiet_dat=True))
NHOM_DAT_CON = (('dat_o', '• Đất ở tại nông thôn (ONT) & đô thị (ODT)'), ('nong_nghiep', '• Đất nông nghiệp (CLN, LUK, HNK, NTS…)'),
                ('khac', '• Đất phi nông nghiệp khác, đất chưa phân loại'))


def can_cu_co_cau() -> dict:
    """{nhóm 1-5: căn cứ áp dụng} - mặc định CAN_CU_CO_CAU, hồ sơ địa phương can_cu_phap_ly.co_cau ghi đè từng nhóm."""
    from . import dia_phuong
    kq = dict(CAN_CU_CO_CAU)
    try:
        rieng = dia_phuong.lay('can_cu_phap_ly.co_cau') or {}
    except Exception:                                   # hồ sơ không có khóa này
        rieng = {}
    for k, v in dict(rieng).items():
        try:
            kq[int(k)] = str(v)
        except (TypeError, ValueError):
            pass
    return kq


def _nhom_dat_con(loai_dat: str, nhom_dat: str) -> str:
    from .loai_dat import nhom_mac_dinh
    ma = (str(loai_dat or '').upper().replace(',', '+').split('+')[0]).strip()
    nhom = nhom_mac_dinh(ma) or str(nhom_dat or '')
    from .lap_pa import bo_dau
    n = bo_dau(nhom).lower()
    if 'dat o' in n or ma in ('ONT', 'ODT', 'OTC'):
        return 'dat_o'
    if 'nong nghiep' in n and 'phi' not in n:
        return 'nong_nghiep'
    return 'khac'


def tien_dat_theo_nhom(con) -> dict:
    """{khóa NHOM_DAT_CON: (tiền Decimal, số hộ)} - thành tiền các dòng mục 1 (mọi hộ, mọi lần lập phương án)."""
    from .nghiep_vu import BoiCanh, doc_tat_ca_phuong_an, thanh_tien_dong_dat
    bc = BoiCanh.tu(con)
    tien = {k: KHONG for k, _ in NHOM_DAT_CON}
    ho = {k: set() for k, _ in NHOM_DAT_CON}
    for ma, pa in doc_tat_ca_phuong_an(con).items():
        for d in pa.dat:
            k = _nhom_dat_con(d.loai_dat, d.nhom_dat)
            v = thanh_tien_dong_dat(d, bc)
            tien[k] += v
            if v > 0:
                ho[k].add(ma)
    return {k: (tien[k], len(ho[k])) for k in tien}


def _so(v):
    s = str(v if v is not None else '').strip()
    return D(s) if s else KHONG


def _pt(a, tong) -> float:
    return float(a * 100 / tong) if tong else 0.0


def co_cau(con, chi_tiet_dat: bool = False) -> dict:
    """Cơ cấu kinh phí của dự án. dong: [dict(loai, ma, ten, tien_pa, tien_pd, chua_pd, chenh, ty_trong, so_ho, ghi_chu)]; loai là
    'nhom' (5 nhóm khoản) / 'cong' (cộng bồi thường, hỗ trợ, TĐC) / 'kinh_phi' (tổ chức thực hiện) / 'tong' (tổng kinh phí).
    tien_pa: theo phương án của MỌI hộ; tien_pd: số đã phê duyệt trong các quyết định; chua_pd: phương án của các hộ CHƯA có quyết
    định nào; chenh: phương án của các hộ ĐÃ có quyết định - số phê duyệt (so cùng tập hộ; khác 0 = quyết định ghi khác phương án).
    ty_trong (đặc tả V10 - sửa lỗi hiện 2,4% / 3,4%): GỐC 100% là "Cộng bồi thường, hỗ trợ, tái định cư" - 5 nhóm cộng lại 100%, dòng
    cộng 100%, dòng kinh phí tổ chức thực hiện = ĐÚNG tỷ lệ QĐ 08/2025 (2,5% / 3,5%), dòng tổng kinh phí = 100% + tỷ lệ đó (102,5% /
    103,5%). Trước đây lấy mẫu số là tổng kinh phí nên ra 2,4% / 97,6%.
    20/10/2026: mỗi dòng có thêm 'stt' (I-V, ★ cộng, VI kinh phí, - phân bổ) và 'can_cu' (can_cu_co_cau / QĐ 08/2025);
    chi_tiet_dat=True: sau nhóm I thêm dòng 'nhom_con' (đất ở / đất nông nghiệp / đất khác - chỉ số theo phương án)."""
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
            if x.muc_pa_duyet is not None:              # 1.0.05: nhiều lần PA - chỉ các lần đã có quyết định
                pa_duyet[m] += x.muc_pa_duyet.get(m, KHONG)
            elif x.qd:
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
    cc = can_cu_co_cau()
    dong = []
    for m, ten, _ in NHOM_KINH_PHI:
        dong.append(dict(loai='nhom', ma=m, ten=ten, tien_pa=pa[m], tien_pd=pd[m], chua_pd=pa[m] - pa_duyet[m], chenh=pa_duyet[m] - pd[m],
                         ty_trong=_pt(pa[m], cong_pa), so_ho=so_ho[m], ghi_chu='', stt=STT_NHOM[m], can_cu=cc.get(m, '')))
        if m == 1 and chi_tiet_dat:
            con_dat = tien_dat_theo_nhom(con)
            for j, (k, nhan) in enumerate(NHOM_DAT_CON, start=1):
                v, n = con_dat[k]
                if v or k != 'khac':
                    dong.append(dict(loai='nhom_con', ma=100 + j, ten=nhan, tien_pa=v, tien_pd=None, chua_pd=None, chenh=None,
                                     ty_trong=_pt(v, cong_pa), so_ho=n, ghi_chu='', stt=str(j),
                                     can_cu=f'{n} trường hợp thu hồi {nhan[2:].split(" (")[0].lower()}'))
    dong.append(dict(loai='cong', ma=0, ten='Cộng bồi thường, hỗ trợ, tái định cư', tien_pa=cong_pa, tien_pd=cong_pd,
                     chua_pd=cong_pa - cong_duyet, chenh=cong_duyet - cong_pd, ty_trong=100.0 if cong_pa else 0.0,
                     so_ho=sum(1 for x in ds if x.tong_pa > 0), ghi_chu='', stt='★', can_cu='Tổng cộng các mục I + II + III + IV + V'))
    kp_pd = lam_tron(cong_pd * tl / 100, -3)
    kp_chua = lam_tron((cong_pa - cong_duyet) * tl / 100, -3)
    dong.append(dict(loai='kinh_phi', ma=-1, ten=f'Kinh phí tổ chức thực hiện bồi thường ({str(tl).replace(".", ",")}%)',
                     tien_pa=kp, tien_pd=kp_pd, chua_pd=kp_chua, chenh=None, ty_trong=float(tl), so_ho=None,
                     ghi_chu=f'{LOAI_KINH_PHI[loai][0]}{" - tự nhận theo tên dự án" if tu_nhan else ""}. {CAN_CU_KINH_PHI}',
                     stt='VI', can_cu=f'{CAN_CU_KINH_PHI} ({LOAI_KINH_PHI[loai][0]})'))
    # 1.0.04 (người dùng 19/10/2026): hai dòng con phân bổ kinh phí tổ chức thực hiện như bảng tổng hợp in (mặc định 85% / 15% -
    # hồ sơ địa phương kinh_phi_to_chuc.phan_bo)
    dong.extend(dong_phan_bo(con, tl, kp, kp_pd, kp_chua))
    dong.append(dict(loai='tong', ma=-2, ten='TỔNG KINH PHÍ DỰ ÁN', tien_pa=tong, tien_pd=None, chua_pd=None, chenh=None, ty_trong=100.0 + float(tl),
                     so_ho=None, ghi_chu='Cộng bồi thường, hỗ trợ, tái định cư + kinh phí tổ chức thực hiện', stt='',
                     can_cu='Cộng bồi thường, hỗ trợ, tái định cư (★) + kinh phí tổ chức thực hiện (VI)'))
    return dict(dong=dong, loai_kp=loai, tl_kp=tl, tu_nhan=tu_nhan, so_ho=len(ds), so_ho_da_lap=sum(1 for x in ds if x.da_lap),
                so_ho_phe_duyet=sum(1 for x in ds if x.qd), tong=tong, cong=cong_pa, kinh_phi=kp)


def dong_phan_bo(con, tl, kp, kp_pd, kp_chua) -> list:
    """Dòng con 'phan_bo' dưới dòng kinh phí tổ chức thực hiện: "  - Tổ chức làm nhiệm vụ bồi thường (<đơn vị lập>) 85%:",
    "  - Cơ quan phối hợp thực hiện (<xã, phường>) 15%:" - tỷ lệ theo dia_phuong.phan_bo_kinh_phi(); số tiền = kinh phí x tỷ lệ
    (làm tròn nghìn đồng) ở cả ba cột phương án / đã phê duyệt / chưa phê duyệt; cột tỷ lệ tính trên dòng cộng (100%)."""
    from . import dia_phuong
    from .lap_pa import CAN_CU_KINH_PHI, doc_du_an
    try:
        da = doc_du_an(con)
    except Exception:                                   # file chỉ xem phiên bản cũ
        da = {}
    don_vi = ' '.join(str(da.get('don_vi_lap') or '').split())
    xa = ' '.join(f'{da.get("cap_dia_ban") or ""} {da.get("ten_dia_ban") or ""}'.split())
    kq = []
    for j, (ten, ty_le) in enumerate(dia_phuong.phan_bo_kinh_phi()):
        so = str(ty_le).replace('.', ',')
        if j == 0:
            nhan = f'  - Tổ chức làm nhiệm vụ bồi thường{f" ({don_vi})" if don_vi else ""} {so}%:'
        elif j == 1:
            nhan = f'  - Cơ quan phối hợp thực hiện{f" ({xa})" if xa else ""} {so}%:'
        else:
            nhan = f'  - {ten} {so}%:'

        def pb(v):
            return None if v is None else lam_tron(v * ty_le / 100, -3)
        kq.append(dict(loai='phan_bo', ma=-10 - j, ten=nhan, tien_pa=pb(kp), tien_pd=pb(kp_pd), chua_pd=pb(kp_chua), chenh=None,
                       ty_trong=float(tl * ty_le / 100), so_ho=None,
                       ghi_chu=f'{so}% kinh phí tổ chức thực hiện ({ten}) - {CAN_CU_KINH_PHI}', stt='-',
                       can_cu=f'{so}% kinh phí tổ chức thực hiện - {CAN_CU_KINH_PHI}', ten_phan_bo=ten, ty_le_phan_bo=ty_le))
    return kq


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
    return du_toan.so_sanh(goc, du_toan.tu_du_an_nho(con))


def danh_gia_chenh(khai_toan, thuc_te) -> tuple:
    """Đánh giá một hạng mục đối soát: (chữ, mức 'dat' / 'loi' / 'tin'). Thực tế < khái toán: "Tiết kiệm x%"; bằng: "Trong hạn mức";
    lớn hơn: "Tăng x%"; khái toán 0 mà thực tế có tiền: "Chưa có trong khái toán"."""
    a, b = D(khai_toan or 0), D(thuc_te or 0)
    if not a:
        return ('Chưa có trong khái toán', 'loi') if b else ('—', 'tin')
    t = (b - a) * 100 / a
    so = f'{abs(t):.1f}'.replace('.', ',')
    if b < a:
        return f'Tiết kiệm {so}%', 'dat'
    if b == a:
        return 'Trong hạn mức', 'dat'
    return f'Tăng {so}%', 'loi'


def ket_luan_doi_soat(ss) -> tuple:
    """(mức, chữ kết luận) cho cả đối soát (du_toan.so_sanh): nằm trong / vượt tổng mức khái toán, tỷ lệ tiết kiệm nguồn vốn."""
    from .tien import vn
    if ss is None:
        return 'tin', ''
    a, b, c, t = ss['tong']
    if not a:
        return 'canh_bao', 'Bảng khái toán ban đầu chưa có số tiền nào - không có hạn mức để đối soát.'
    pt = f'{abs(t or 0):.2f}'.replace('.', ',')
    if ss['vuot']:
        return 'loi', (f'Kết luận kiểm toán: tổng kinh phí phương án {vn(b)} đ VƯỢT tổng mức khái toán {vn(a)} đ là {vn(c)} đ '
                       f'(+{pt}%). Cần báo cáo cấp có thẩm quyền xem xét điều chỉnh khái toán / chủ trương đầu tư trước khi trình.')
    return 'dat', (f'Kết luận kiểm toán: tổng kinh phí phương án {vn(b)} đ KHÔNG vượt tổng mức khái toán {vn(a)} đ; tiết kiệm '
                   f'{vn(-c)} đ ({pt}% nguồn vốn). Không phải điều chỉnh khái toán vì lý do kinh phí.')


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

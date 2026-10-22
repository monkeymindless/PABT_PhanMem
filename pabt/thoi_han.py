"""Mốc thời hạn pháp lý của các bước giai đoạn thẩm định - bàn giao (Mục IV Quyết định 18/2026/QĐ-UBND, đặc tả ARCH-PABT-2026-V7).

Không gán cứng số ngày vào mã nguồn nghiệp vụ: mỗi mốc có GIÁ TRỊ MẶC ĐỊNH theo đặc tả nhưng lưu ở `cai_dat` của dự án
(sửa được ở hộp "Mốc thời hạn…" của trang Theo dõi chi trả & Bàn giao) - luật mới đổi số ngày thì chỉ đổi cài đặt.

    tham_dinh    15 ngày  Bước 8: thời hạn thẩm định phương án kể từ ngày trình
    thu_hoi_nn   60 ngày  Bước 13: thông báo thu hồi đất NÔNG NGHIỆP trước khi ban hành quyết định thu hồi đất
    thu_hoi_pnn 120 ngày  Bước 13: thông báo thu hồi đất PHI NÔNG NGHIỆP
    van_dong     10 ngày  Bước 14, 15: thời gian vận động hộ không nhận tiền / không bàn giao mặt bằng

Ngày tính theo NGÀY DƯƠNG LỊCH. Không phụ thuộc Qt.
"""
from __future__ import annotations

import re
from datetime import date, datetime, timedelta

from . import csdl
from .lap_pa import LoiNhap

# khóa -> (khóa trong cai_dat, mặc định, nhãn, căn cứ)
MOC = {
    'tham_dinh': ('SO_NGAY_THAM_DINH', 15, 'Thời hạn thẩm định phương án', 'Bước 8 Mục IV QĐ 18/2026/QĐ-UBND'),
    'thu_hoi_nn': ('SO_NGAY_THU_HOI_NN', 60, 'Đã thông báo thu hồi đất nông nghiệp tối thiểu', 'Bước 13 Mục IV QĐ 18/2026/QĐ-UBND'),
    'thu_hoi_pnn': ('SO_NGAY_THU_HOI_PNN', 120, 'Đã thông báo thu hồi đất phi nông nghiệp tối thiểu',
                    'Bước 13 Mục IV QĐ 18/2026/QĐ-UBND'),
    'van_dong': ('SO_NGAY_VAN_DONG', 10, 'Thời gian vận động trước khi cưỡng chế', 'Bước 14, 15 Mục IV QĐ 18/2026/QĐ-UBND'),
}
KHOA_NGAY_THONG_BAO = 'NGAY_THONG_BAO_THU_HOI'          # ngày thông báo thu hồi đất của dự án (dd/mm/yyyy)
CAN_CU_THAM_DINH = 'Khoản 8 Mục IV QĐ 18'               # chữ hiện ở nhãn đếm ngược thẩm định


def _ap_ho_so(hs: dict) -> None:
    """0.9.85: số ngày MẶC ĐỊNH (dự án chưa tự đặt ở cai_dat) và căn cứ lấy từ hồ sơ địa phương (pabt_profile.json mục thoi_han,
    can_cu_phap_ly.tham_dinh) - địa phương khác không sửa mã."""
    global CAN_CU_THAM_DINH
    th = hs['thoi_han']
    for k, (ma, _, nhan, _) in list(MOC.items()):
        MOC[k] = (ma, th[k]['so_ngay'], nhan, th[k]['can_cu'])
    CAN_CU_THAM_DINH = hs['can_cu_phap_ly']['tham_dinh']


def _dang_ky_ho_so() -> None:
    from . import dia_phuong
    dia_phuong.dang_ky(_ap_ho_so)


_dang_ky_ho_so()
SAP_HET_HAN = 3                                         # còn tối đa bấy nhiêu ngày thì cảnh báo vàng


# ---------------------------------------------------------------- ngày
def doc_ngay(chu) -> date | None:
    """'05/03/2026', '5-3-2026', '2026-03-05', date / datetime -> date; trống / không đọc được -> None (không ném lỗi)."""
    if isinstance(chu, datetime):
        return chu.date()
    if isinstance(chu, date):
        return chu
    s = str(chu or '').strip()
    if not s:
        return None
    m = re.fullmatch(r'(\d{4})-(\d{1,2})-(\d{1,2})(?:[ T].*)?', s)
    if m:
        y, mo, d = (int(x) for x in m.groups())
    else:
        m = re.fullmatch(r'(\d{1,2})\s*[/.\-]\s*(\d{1,2})\s*[/.\-]\s*(\d{4})', s)
        if not m:
            return None
        d, mo, y = (int(x) for x in m.groups())
    try:
        return date(y, mo, d)
    except ValueError:
        return None


def hien_ngay(d: date | None) -> str:
    return d.strftime('%d/%m/%Y') if d else ''


def hom_nay_hoac(hom_nay) -> date:
    return doc_ngay(hom_nay) if hom_nay is not None and doc_ngay(hom_nay) else date.today()


# ---------------------------------------------------------------- số ngày của từng mốc
def so_ngay(con, khoa: str) -> int:
    ma, mac_dinh, _, _ = MOC[khoa]
    try:
        n = int(str(csdl.doc_cai_dat(con, ma, '')).strip() or mac_dinh)
    except ValueError:
        return mac_dinh
    return n if n >= 1 else mac_dinh


def tat_ca_so_ngay(con) -> dict:
    return {k: so_ngay(con, k) for k in MOC}


def dat_so_ngay(con, gia_tri: dict) -> bool:
    """Ghi các mốc (khóa MOC -> số ngày nguyên 1..3650). Sai -> LoiNhap, không ghi gì. True nếu có mốc nào đổi."""
    moi = {}
    for k, v in gia_tri.items():
        if k not in MOC:
            raise KeyError(k)
        try:
            n = int(str(v).strip())
        except ValueError:
            raise LoiNhap(f'"{MOC[k][2]}": nhập số ngày là số nguyên (ví dụ {MOC[k][1]}).') from None
        if not 1 <= n <= 3650:
            raise LoiNhap(f'"{MOC[k][2]}": số ngày từ 1 đến 3650.')
        moi[k] = n
    doi = {k: n for k, n in moi.items() if n != so_ngay(con, k)}
    if not doi:
        return False
    with csdl.giao_dich(con):
        for k, n in doi.items():
            csdl.ghi_cai_dat(con, MOC[k][0], n)
        csdl.ghi_nhat_ky(con, 'Mốc thời hạn', ', '.join(f'{MOC[k][2]}: {n} ngày' for k, n in doi.items()))
    return True


def ngay_thong_bao(con) -> date | None:
    return doc_ngay(csdl.doc_cai_dat(con, KHOA_NGAY_THONG_BAO, ''))


def dat_ngay_thong_bao(con, chu) -> str:
    """Ghi ngày thông báo thu hồi đất (trống = xóa). Sai ngày -> LoiNhap. Trả chuỗi dd/mm/yyyy đã chuẩn hóa ('' nếu xóa)."""
    s = str(chu or '').strip()
    d = doc_ngay(s)
    if s and d is None:
        raise LoiNhap(f'Ngày "{s}" không đúng dạng ngày/tháng/năm (ví dụ 05/03/2026) hoặc không có thật.')
    moi = hien_ngay(d)
    if moi == csdl.doc_cai_dat(con, KHOA_NGAY_THONG_BAO, ''):
        return moi
    with csdl.giao_dich(con):
        csdl.ghi_cai_dat(con, KHOA_NGAY_THONG_BAO, moi)
        csdl.ghi_nhat_ky(con, 'Ngày thông báo thu hồi đất', moi or '(xóa)')
    return moi


# ---------------------------------------------------------------- Bước 8: đếm ngược thời hạn thẩm định của đợt trình
def han_tham_dinh(con, dot, hom_nay=None, da_phe_duyet: bool = False) -> dict:
    """Đếm ngược thẩm định của một đợt trình (quan_ly.Dot: ngày trình = ngay_trinh).

    muc: 'chua_trinh' (chưa có ngày trình) / 'da_xong' (cả đợt đã có quyết định phê duyệt) / 'con_han' / 'sap_het' (còn
    <= SAP_HET_HAN ngày, kể cả đúng hạn cuối) / 'qua_han'. con_lai âm = số ngày đã quá. chu: dòng hiển thị trên nhãn."""
    n = so_ngay(con, 'tham_dinh')
    trinh = doc_ngay(getattr(dot, 'ngay_trinh', '') if dot is not None else '')
    kq = dict(so_ngay=n, ngay_trinh=trinh, han=None, con_lai=None, muc='chua_trinh', can_cu=CAN_CU_THAM_DINH)
    if da_phe_duyet:
        kq.update(muc='da_xong', chu=f'Hạn thẩm định: đợt đã có quyết định phê duyệt ({CAN_CU_THAM_DINH}: {n} ngày).')
        return kq
    if trinh is None:
        kq['chu'] = f'Hạn thẩm định: chưa có ngày trình - nhập ngày tờ trình để đếm ngược / {n} ngày ({CAN_CU_THAM_DINH}).'
        return kq
    han = trinh + timedelta(days=n)
    con_lai = (han - hom_nay_hoac(hom_nay)).days
    con_lai = min(con_lai, n)                             # ngày trình ở tương lai: chưa bắt đầu đếm
    kq.update(han=han, con_lai=con_lai)
    if con_lai < 0:
        kq.update(muc='qua_han', chu=f'Hạn thẩm định: QUÁ HẠN {-con_lai} ngày so với {n} ngày ({CAN_CU_THAM_DINH}) - hạn là '
                                      f'{hien_ngay(han)}.')
    else:
        kq.update(muc='sap_het' if con_lai <= SAP_HET_HAN else 'con_han',
                  chu=f'Hạn thẩm định: Còn {con_lai} / {n} ngày ({CAN_CU_THAM_DINH}) - hạn {hien_ngay(han)}.')
    return kq


# ---------------------------------------------------------------- Bước 13: mốc ban hành quyết định thu hồi đất
def phan_nhom_dat(loai_dat: str) -> str:
    """'nn' (mọi thành phần là đất nông nghiệp) / 'pnn' (có đất phi nông nghiệp, ví dụ ONT+CLN) / 'khong_ro' (trống hoặc có mã
    chưa có trong danh mục loại đất - loai_dat.LOAI_DAT: mốc thu hồi lấy theo đất phi nông nghiệp, thời hạn dài hơn, cho an toàn)."""
    from .loai_dat import LOAI_DAT, NONG_NGHIEP, PHI_NONG_NGHIEP
    nhom = {ma: g for ma, _, g in LOAI_DAT}
    ma_ds = [m for m in re.split(r'[\s+,;/&-]+', str(loai_dat or '').upper()) if m]
    if not ma_ds:
        return 'khong_ro'
    g = [nhom.get(m) for m in ma_ds]
    if any(x == PHI_NONG_NGHIEP for x in g):
        return 'pnn'
    if all(x == NONG_NGHIEP for x in g):
        return 'nn'
    return 'khong_ro'


def nhom_dat_ho(ds_loai_dat: list) -> str:
    """Nhóm đất của hộ theo các thửa: có thửa phi nông nghiệp / không rõ -> 'pnn' (khong_ro nếu chỉ vì không rõ); toàn nông nghiệp -> 'nn'."""
    g = [phan_nhom_dat(x) for x in ds_loai_dat] or ['khong_ro']
    if 'pnn' in g:
        return 'pnn'
    if 'khong_ro' in g:
        return 'khong_ro'
    return 'nn'


def moc_thu_hoi_ho(nhom: str, tb: date | None, n_nn: int, n_pnn: int, hom_nay: date) -> dict:
    """Kiểm tra mốc cho một hộ: du True / False / None (chưa có ngày thông báo). chu: chữ đầy đủ (chú thích, file xuất); chu_gon:
    chữ ngắn trong ô bảng Tiến độ (22/10/2026 - câu dài làm mỗi dòng bảng cao 4 dòng chữ)."""
    yeu_cau = n_nn if nhom == 'nn' else n_pnn
    ten = 'đất nông nghiệp' if nhom == 'nn' else 'đất phi nông nghiệp' if nhom == 'pnn' else 'chưa rõ loại đất - tính như đất phi nông nghiệp'
    kq = dict(nhom=nhom, yeu_cau=yeu_cau, ngay_tb=tb, da_qua=None, du=None, con_lai=None)
    if tb is None:
        kq['chu'] = f'Chưa có ngày thông báo thu hồi đất (cần {yeu_cau} ngày - {ten})'
        kq['chu_gon'] = 'Chưa có ngày TB'
        return kq
    da_qua = (hom_nay - tb).days
    kq.update(da_qua=da_qua, du=da_qua >= yeu_cau, con_lai=max(0, yeu_cau - da_qua))
    kq['chu'] = (f'Đủ mốc: đã thông báo {da_qua}/{yeu_cau} ngày ({ten})' if kq['du'] else
                 f'Chưa đủ mốc: mới {max(da_qua, 0)}/{yeu_cau} ngày, còn {kq["con_lai"]} ngày ({ten})')
    kq['chu_gon'] = (f'Đủ mốc · {da_qua}/{yeu_cau} ngày' if kq['du'] else
                     f'Chưa đủ mốc · {max(da_qua, 0)}/{yeu_cau} ngày')
    return kq


def moc_thu_hoi_tat_ca(con, ds_ma_ho: list | None = None, hom_nay=None) -> dict:
    """{ma_ho: moc_thu_hoi_ho} - một truy vấn thửa cho cả dự án."""
    chon = set(ds_ma_ho) if ds_ma_ho is not None else None
    loai = {}
    for r in con.execute('SELECT ma_ho, loai_dat FROM thua'):
        loai.setdefault(r['ma_ho'], []).append(r['loai_dat'])
    tb, nn, pnn, nay = ngay_thong_bao(con), so_ngay(con, 'thu_hoi_nn'), so_ngay(con, 'thu_hoi_pnn'), hom_nay_hoac(hom_nay)
    return {r['ma_ho']: moc_thu_hoi_ho(nhom_dat_ho(loai.get(r['ma_ho'], [])), tb, nn, pnn, nay)
            for r in con.execute('SELECT ma_ho FROM ho') if chon is None or r['ma_ho'] in chon}

"""Tính đơn giá đất bồi thường theo NQ 28/2025/NQ-HĐND (bảng giá đất) x QĐ 03/2026/QĐ-UBND (hệ số K1 / K2 / K3). Không Qt.

Chuyển (port) từ `calculateStandardLandPrice` của HeThongDinhGiaVaScanThongMinh_V2.tsx (người dùng cung cấp 05/11/2026) sang Python,
GIỮ NGUYÊN công thức và quy tắc pháp lý của bản gốc:

    Đơn giá = ROUND(G_NQ28 x K1 x K2 x K3 x K_khác)               (ROUND kiểu Excel = tien.lam_tron)
    K1: Phụ lục I.1 (đất ở / TMDV / SX-KD phi NN, khoáng sản) hoặc I.2 (đất nông nghiệp) - theo ĐOẠN đường (điểm đầu -> điểm cuối)
    K2: Phụ lục II - chỉ khi dự án đầu tư có hệ số sử dụng đất (FAR); mặc định 1,00
    K3: Phụ lục III - PNN: x1,05 (<=200 m TTTM / TT hành chính / siêu thị), x0,95 (<=100 m nghĩa trang...), x0,95 (<=50 m hành lang
        đường sắt / cao tốc / hầm chui); NN: x0,90 khi tiếp giáp đường đất, đá, cuội, sỏi, cấp phối - NHƯNG khóa 1,00 nếu tuyến đã có
        quy định riêng ở Phụ lục I.2 (VB 1201/SNNMT-ĐĐ và VB 29/5/2026 của Sở NN&MT: chống nhân trùng)
    Chuyển tiếp (khoản 3 Điều 4 QĐ 03): có giá đất cụ thể đã phê duyệt / thẩm định: giá cụ thể >= giá tính thì giữ giá cụ thể.

Làm tròn trung gian giống bản gốc: tổng hệ số 6 chữ số lẻ, giá chưa làm tròn 4 chữ số lẻ, rồi ROUND về đồng. Số tiền / hệ số là Decimal
(không float). Dữ liệu 106 đoạn đường (Trị An, Tân An, Phú Lý) ở `pabt/gia_dat_qd03.json`; giá G_NQ28 tự tra từ `gia_dat_nq28`
(cụm 7 dòng / đoạn: TT = tt_bat_dau + 0..6 = MT, T1, T2, T3, K1, K2, K3)."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from decimal import ROUND_HALF_UP, Decimal
from functools import lru_cache

from .tien import D, lam_tron, vn

TEN_FILE = 'gia_dat_qd03.json'
MOT = Decimal(1)

# nhóm đất của QĐ 03 -> (mã nhóm, tên hiển thị, phụ lục K1)
NHOM_DAT = (
    ('DAT_NONG_NGHIEP', 'Đất nông nghiệp (CLN, BHK, LUC, RSX, NTS) - PL I.2'),
    ('DAT_O', 'Đất ở (ONT, ODT) - PL I.1'),
    ('DAT_TMDV', 'Đất thương mại, dịch vụ (TMD) - PL I.1'),
    ('DAT_SXKD_KHOANGSAN', 'Đất cơ sở SX phi nông nghiệp & Khoáng sản (SKC, SKS) - PL I.1'),
)
TEN_NHOM = dict(NHOM_DAT)
# nhóm đất -> khóa hệ số K1 của đoạn đường
K1_CUA_NHOM = {'DAT_O': 'k1_dat_o', 'DAT_TMDV': 'k1_tmdv', 'DAT_SXKD_KHOANGSAN': 'k1_sxkd', 'DAT_NONG_NGHIEP': 'k1_nong_nghiep'}
# nhóm đất -> cột bảng giá NQ 28 (gia_dat_nq28.COT); đất nông nghiệp có thêm cột rừng sản xuất / nuôi trồng thủy sản
COT_BANG_GIA = {'DAT_O': 'dat_o', 'DAT_TMDV': 'tmdv', 'DAT_SXKD_KHOANGSAN': 'sxkd', 'DAT_NONG_NGHIEP': 'nn_cay'}
COT_NN_RUNG_NTS = 'nn_rung_nts'

KET_CAU = (
    ('NHUA_BETONG', 'Đường nhựa, bê tông xi măng (K3 = 1,00)'),
    ('DAT_SOI_DA_CAPPHOI', 'Đường đất, đá, cuội, sỏi hỗn hợp, cấp phối (Đất NN: K3 = 0,90)'),
)
# cụm 7 dòng chuẩn / đoạn (NQ 27 + NQ 28): (mã, vị trí trong bảng giá NQ 28, mô tả)
VI_TRI_KET_NOI = (
    ('MAT_TIEN_VT1', 'MT', 'Dòng 1 (VT1): Mặt tiền đường chính'),
    ('DAU_NOI_TRUC_TIEP_M1', 'T1', 'Dòng 2: Đấu nối trực tiếp - Mức 1 (Rộng ≥5m cách ≤1000m; 3-<5m cách ≤500m)'),
    ('DAU_NOI_TRUC_TIEP_M2', 'T2', 'Dòng 3: Đấu nối trực tiếp - Mức 2 (Rộng ≥5m cách >1000m; 3-<5m cách 500-1000m; <3m cách ≤200m)'),
    ('DAU_NOI_TRUC_TIEP_M3', 'T3', 'Dòng 4: Đấu nối trực tiếp - Mức 3 (Rộng 3-<5m cách >1000m; <3m cách >200m)'),
    ('KHONG_DAU_NOI_M1', 'K1', 'Dòng 5: Không đấu nối trực tiếp - Mức 1'),
    ('KHONG_DAU_NOI_M2', 'K2', 'Dòng 6: Không đấu nối trực tiếp - Mức 2'),
    ('KHONG_DAU_NOI_M3', 'K3', 'Dòng 7: Không đấu nối trực tiếp - Mức 3'),
)
VI_TRI_THEO_MA = {m: (i, vt) for i, (m, vt, _) in enumerate(VI_TRI_KET_NOI)}

# Phụ lục III: yếu tố ảnh hưởng (mã -> (hệ số, nhóm áp dụng: 'pnn' | 'nn', mô tả ngắn))
K3_PNN_TTTM = Decimal('1.05')
K3_PNN_95 = Decimal('0.95')
K3_NN_DUONG_DAT = Decimal('0.90')
YEU_TO_PL3 = (
    ('PNN_TTTM_200M', K3_PNN_TTTM, 'pnn', 'Đất PNN trong phạm vi ≤200m từ mép ngoài TTTM, trung tâm hành chính, siêu thị (×1,05)'),
    ('PNN_NGHIATRANG_100M', K3_PNN_95, 'pnn', 'Đất PNN trong phạm vi ≤100m từ mép ngoài nghĩa trang, nghĩa địa, nhà tang lễ, hỏa táng (×0,95)'),
    ('PNN_HANHLANG_50M', K3_PNN_95, 'pnn', 'Đất PNN trong phạm vi ≤50m từ mép ngoài hành lang an toàn đường sắt, cao tốc, hầm chui (×0,95)'),
    ('NN_DUONG_DAT_SOI_DA', K3_NN_DUONG_DAT, 'nn', 'Đất NN tiếp giáp mặt đường đất, đá, cuội, sỏi hỗn hợp, cấp phối (×0,90)'),
)
MA_PNN = tuple(m for m, _, n, _ in YEU_TO_PL3 if n == 'pnn')


# ---------------------------------------------------------------- dữ liệu 106 đoạn đường
@lru_cache(maxsize=1)
def _doc() -> dict:
    from . import tai_nguyen
    with open(str(tai_nguyen(TEN_FILE)), 'r', encoding='utf-8') as f:
        return json.load(f)


def du_lieu() -> dict:
    return _doc()


def ds_dia_ban() -> list:
    """Tên khóa bảng của QĐ 03: 'Bảng 53. Phường Trị An', 'Bảng 54. Xã Tân An', 'Bảng 55. Xã Phú Lý'."""
    return list(_doc()['danh_muc_doan_duong_rut_gon_106_tuyen'].keys())


def ten_ngan(dia_ban: str) -> str:
    """'Bảng 53. Phường Trị An' -> 'Phường Trị An'."""
    s = str(dia_ban or '')
    return s.split('. ', 1)[1] if s.startswith('Bảng') and '. ' in s else s


def ds_doan(dia_ban: str) -> list:
    return list(_doc()['danh_muc_doan_duong_rut_gon_106_tuyen'].get(dia_ban, ()))


def so_doan() -> int:
    return sum(len(v) for v in _doc()['danh_muc_doan_duong_rut_gon_106_tuyen'].values())


def tim_doan(dia_ban: str, ma_doan: str) -> dict | None:
    return next((r for r in ds_doan(dia_ban) if r['ma_doan_duong'] == ma_doan), None)


def nhan_doan(r: dict) -> str:
    """'[TT 1-7] Đường Xóm Huế: Đường tỉnh 768 → Đường Hóc Lai'."""
    return f'[TT {r["tt_bat_dau"]}-{r["tt_ket_thuc"]}] {r["ten_duong"]}: {r["diem_dau"]} → {r["diem_cuoi"]}'


def dia_ban_theo_ten(ten: str) -> str:
    """Tên xã / phường bất kỳ ('Trị An', 'xã Tân An'...) -> khóa bảng của QĐ 03 ('' nếu không phải 3 địa bàn có dữ liệu)."""
    from .lap_pa import bo_dau
    t = bo_dau(ten or '')
    for p in ('xa ', 'phuong ', 'thi tran '):
        if t.startswith(p):
            t = t[len(p):]
    if not t:
        return ''
    for k in ds_dia_ban():
        if t in bo_dau(ten_ngan(k)):
            return k
    return ''


def gia_bang_gia(dia_ban: str, doan: dict | None, nhom_dat: str, ma_vi_tri: str, cot: str = '') -> Decimal | None:
    """Giá G_NQ28 (đồng/m²) tra từ bảng giá đất đang dùng (gia_dat_nq28): dòng TT = tt_bat_dau + thứ tự của vị trí kết nối trong cụm 7
    dòng. None: bảng giá đang dùng không có dòng khớp (đã thay bảng, khác tên đường) - người dùng nhập tay."""
    if doan is None or ma_vi_tri not in VI_TRI_THEO_MA:
        return None
    from . import gia_dat_nq28 as nq
    from .lap_pa import bo_dau
    thu_tu, vt = VI_TRI_THEO_MA[ma_vi_tri]
    cot = cot or COT_BANG_GIA.get(nhom_dat, '')
    if not cot:
        return None
    tt = int(doan['tt_bat_dau']) + thu_tu
    for r in nq.tat_ca():
        if r.get('tt') == tt and nq.khop_xa(ten_ngan(dia_ban), r['xa']) and r.get('vi_tri') == vt \
                and bo_dau(r['ten_duong']) == bo_dau(doan['ten_duong']):
            try:
                return D(nq.gia_dong(r, cot))
            except (KeyError, TypeError, ValueError):
                return None
    return None


# ---------------------------------------------------------------- tính đơn giá
@dataclass
class DauVao:
    dia_ban: str = ''
    nhom_dat: str = 'DAT_NONG_NGHIEP'
    ma_doan_duong: str = ''
    loai_ket_noi_vi_tri: str = 'MAT_TIEN_VT1'
    ket_cau_mat_duong: str = 'NHUA_BETONG'
    don_gia_bang_gia: Decimal = field(default_factory=lambda: Decimal(0))     # G_NQ28 (đồng/m²)
    he_so_k1: Decimal | None = None                  # dùng khi không có đoạn đường; có đoạn thì lấy theo Phụ lục
    ap_dung_quy_hoach_pl2: bool = False
    he_so_quy_hoach_k2: Decimal = field(default_factory=lambda: Decimal(1))
    yeu_to_pl3: list = field(default_factory=list)
    he_so_khac: Decimal = field(default_factory=lambda: Decimal(1))
    gia_dat_cu_the: Decimal = field(default_factory=lambda: Decimal(0))       # chuyển tiếp khoản 3 Điều 4 QĐ 03
    co_quy_dinh_rieng_duong_dat_pl1: bool = False


@dataclass
class KetQua:
    don_gia_nq28: Decimal
    k1: Decimal
    k2: Decimal
    k3: Decimal
    k_khac: Decimal
    tong_he_so: Decimal
    don_gia_chua_lam_tron: Decimal
    don_gia_da_lam_tron: Decimal
    don_gia_ap_dung: Decimal                         # đã xét chuyển tiếp Điều 4
    ap_dung_chuyen_tiep: bool
    cong_thuc: str
    canh_bao: list
    buoc_lap_luan: list                              # nhật ký giải trình từng bước (in vào thuyết minh / hiện ở ô đơn giá)


def _q(x, so_le: int) -> Decimal:
    """toFixed(n) của bản gốc: làm tròn nửa lên."""
    return D(x).quantize(Decimal(1).scaleb(-so_le), rounding=ROUND_HALF_UP)


def _he(x) -> str:
    """Hệ số trong câu chữ: 1,24 ; 1 ; 0,9 (bỏ số 0 thừa)."""
    x = D(x)
    s = format(x.normalize(), 'f')
    return s.replace('.', ',')


def _hai(x) -> str:
    return format(_q(x, 2), 'f').replace('.', ',')


def tinh_don_gia(v: DauVao, doan: dict | None = None) -> KetQua:
    """Port của calculateStandardLandPrice (xem docstring module). doan: dòng của ds_doan (None: dùng v.he_so_k1)."""
    canh_bao, lap_luan = [], []
    g = max(D(0), D(v.don_gia_bang_gia))
    lap_luan.append(f'Bước 1 (Bảng giá đất NQ 28/2025/NQ-HĐND): Xác định đơn giá gốc theo khu vực ({v.dia_ban}) và vị trí kết nối '
                    f'({v.loai_ket_noi_vi_tri}) = {vn(g)} đ/m².')

    # Bước 2: K1 (Phụ lục I.1 / I.2)
    k1 = D(v.he_so_k1) if v.he_so_k1 is not None and D(v.he_so_k1) != 0 else MOT
    if doan:
        khoa = K1_CUA_NHOM.get(v.nhom_dat)
        if khoa:
            k1 = D(doan[khoa])
        lap_luan.append(f'Bước 2 (Phụ lục {"I.2" if v.nhom_dat == "DAT_NONG_NGHIEP" else "I.1"} QĐ 03/2026/QĐ-UBND): Tuyến '
                        f'"{doan["ten_duong"]}" (Đoạn từ "{doan["diem_dau"]}" đến "{doan["diem_cuoi"]}"), nhóm đất {v.nhom_dat} -> '
                        f'Hệ số biến động thị trường K1 = {_hai(k1)}.')
    else:
        lap_luan.append(f'Bước 2 (Hệ số biến động thị trường K1 - QĐ 03/2026/QĐ-UBND): K1 = {_hai(k1)}.')

    # Bước 3: K2 (Phụ lục II)
    k2 = MOT
    if v.ap_dung_quy_hoach_pl2 and D(v.he_so_quy_hoach_k2) > 0:
        k2 = D(v.he_so_quy_hoach_k2)
        lap_luan.append('Bước 3 (Phụ lục II QĐ 03/2026/QĐ-UBND): Khu đất thực hiện dự án đầu tư có thông tin hệ số sử dụng đất (FAR) '
                        f'-> Áp dụng hệ số điều chỉnh theo quy hoạch K2 = {_hai(k2)}.')
    else:
        lap_luan.append('Bước 3 (Phụ lục II QĐ 03/2026/QĐ-UBND): Theo Văn bản 1201/SNNMT-ĐĐ, trường hợp không phải dự án đầu tư xác '
                        'định theo hệ số sử dụng đất (FAR) -> Không áp dụng Phụ lục II (K2 = 1,00).')

    # Bước 4: K3 (Phụ lục III)
    k3 = MOT
    la_nn = v.nhom_dat == 'DAT_NONG_NGHIEP'
    co_rieng = bool(v.co_quy_dinh_rieng_duong_dat_pl1) or bool(doan and doan.get('co_quy_dinh_rieng_duong_dat_tai_pl1'))
    ds = list(v.yeu_to_pl3 or [])
    if la_nn:
        tiep_giap_duong_dat = v.ket_cau_mat_duong == 'DAT_SOI_DA_CAPPHOI' or 'NN_DUONG_DAT_SOI_DA' in ds
        if tiep_giap_duong_dat:
            if co_rieng:
                k3 = MOT
                canh_bao.append('Cảnh báo chống nhân trùng (Văn bản 1201 & Văn bản 29/5/2026): Tuyến đường này đã được quy định hệ số K '
                                'riêng cho đường đất/sỏi/đá (hoặc các tuyến đường còn lại) tại Phụ lục I.2, nên KHÔNG nhân thêm hệ '
                                'số 0,90 tại Phụ lục III (K3 = 1,00).')
                lap_luan.append('Bước 4 (Phụ lục III QĐ 03/2026/QĐ-UBND): Tuyến đường đã có hệ số riêng cho đường đất tại Phụ lục I.2 '
                                '-> Giữ nguyên K3 = 1,00.')
            else:
                k3 = K3_NN_DUONG_DAT
                lap_luan.append('Bước 4 (Mục II.1 Phụ lục III QĐ 03 & Văn bản hướng dẫn ngày 29/5/2026 của Sở NN&MT): Đất nông nghiệp '
                                'tiếp giáp mặt đường bằng đất, đá, cuội, sỏi hỗn hợp, đường cấp phối (chưa quy định riêng tại Phụ lục '
                                'I.2) -> Áp dụng quy trình 3 bước, nhân hệ số K3 = 0,90.')
        else:
            lap_luan.append('Bước 4 (Phụ lục III QĐ 03/2026/QĐ-UBND): Đất nông nghiệp tiếp giáp đường nhựa, bê tông xi măng -> K3 = 1,00.')
        if any(c in MA_PNN for c in ds):
            canh_bao.append('Lưu ý pháp lý: Các hệ số 1,05 (phạm vi 200m TTTM) và 0,95 (phạm vi 100m nghĩa trang / 50m hành lang đường '
                            'sắt, cao tốc) tại Mục I Phụ lục III chỉ áp dụng cho Đất phi nông nghiệp, hệ thống đã tự động loại trừ '
                            'khỏi Đất nông nghiệp.')
    else:
        ap_dung = []
        if 'PNN_TTTM_200M' in ds:
            k3 = _q(k3 * K3_PNN_TTTM, 6)
            ap_dung.append('Phạm vi ≤200m TTTM/TTHC/Siêu thị (×1,05)')
        if 'PNN_NGHIATRANG_100M' in ds:
            k3 = _q(k3 * K3_PNN_95, 6)
            ap_dung.append('Phạm vi ≤100m Nghĩa trang/Nhà tang lễ/Hỏa táng (×0,95)')
        if 'PNN_HANHLANG_50M' in ds:
            k3 = _q(k3 * K3_PNN_95, 6)
            ap_dung.append('Phạm vi ≤50m Hành lang đường sắt/Cao tốc/Hầm chui (×0,95)')
        if 'NN_DUONG_DAT_SOI_DA' in ds:
            canh_bao.append('Lưu ý pháp lý: Hệ số 0,90 (mặt đường đất, đá, sỏi, cấp phối tại Mục II.1 Phụ lục III) chỉ áp dụng cho '
                            'Đất nông nghiệp, hệ thống đã tự động loại trừ khỏi Đất phi nông nghiệp.')
        if ap_dung:
            lap_luan.append(f'Bước 4 (Mục I Phụ lục III QĐ 03/2026/QĐ-UBND): Áp dụng yếu tố ảnh hưởng đất phi nông nghiệp '
                            f'[{"; ".join(ap_dung)}] -> Hệ số K3 = {_he(k3)}.')
        else:
            lap_luan.append('Bước 4 (Phụ lục III QĐ 03/2026/QĐ-UBND): Không có yếu tố ảnh hưởng đặc biệt tại Mục I Phụ lục III -> K3 = 1,00.')

    k_khac = D(v.he_so_khac) if D(v.he_so_khac) > 0 else MOT
    tong = _q(k1 * k2 * k3 * k_khac, 6)
    chua_tron = _q(g * k1 * k2 * k3 * k_khac, 4)
    da_tron = lam_tron(chua_tron, 0)

    cuoi, chuyen_tiep = da_tron, False
    if D(v.gia_dat_cu_the) > 0:
        g_ct = lam_tron(D(v.gia_dat_cu_the), 0)
        if g_ct >= da_tron:
            cuoi, chuyen_tiep = g_ct, True
            lap_luan.append(f'Bước 5 (Quy định chuyển tiếp - Tiết 2 Điểm a Khoản 3 Điều 4 QĐ 03/2026/QĐ-UBND): Giá đất cụ thể đã phê '
                            f'duyệt/thẩm định ({vn(g_ct)} đ/m²) ≥ Giá tính theo Bảng giá đất × Hệ số K ({vn(da_tron)} đ/m²) -> Tiếp '
                            f'tục áp dụng theo Giá đất cụ thể đã phê duyệt/thẩm định = {vn(g_ct)} đ/m².')
        else:
            lap_luan.append(f'Bước 5 (Quy định chuyển tiếp - Tiết 1 Điểm a Khoản 3 Điều 4 QĐ 03/2026/QĐ-UBND): Giá đất cụ thể đã phê '
                            f'duyệt/thẩm định ({vn(g_ct)} đ/m²) < Giá tính theo Bảng giá đất × Hệ số K ({vn(da_tron)} đ/m²) -> Chuyển '
                            f'sang áp dụng theo QĐ 03/2026/QĐ-UBND = {vn(da_tron)} đ/m².')

    cong_thuc = (f'{vn(g)} × {_he(k1)} (K1) × {_he(k2)} (K2) × {_he(k3)} (K3)'
                 + (f' × {_he(k_khac)} (K_khác)' if k_khac != 1 else '') + f' = {vn(da_tron)} VNĐ/m²')
    return KetQua(g, k1, k2, k3, k_khac, tong, chua_tron, da_tron, cuoi, chuyen_tiep, cong_thuc, canh_bao, lap_luan)


def ghi_chu_ap_gia(kq: KetQua, doan: dict | None = None, dia_ban: str = '') -> str:
    """Câu căn cứ ghi vào ô Ghi chú của dòng đất khi áp đơn giá."""
    d = f'{dia_ban}, ' if dia_ban else ''
    t = f'{doan["ten_duong"]} ({doan["diem_dau"]} - {doan["diem_cuoi"]}), ' if doan else ''
    return f'Đơn giá đất theo NQ 28/2025/NQ-HĐND × QĐ 03/2026/QĐ-UBND: {d}{t}{kq.cong_thuc}' + \
           (' (giữ giá đất cụ thể đã phê duyệt - khoản 3 Điều 4 QĐ 03)' if kq.ap_dung_chuyen_tiep else '')

"""Tính đơn giá đất bồi thường theo BỘ QUY TẮC (goi_gia_dat.py): công thức, hệ số, yếu tố ảnh hưởng, câu giải trình đều đọc từ gói, không viết cố định trong mã. Không Qt.

Gói gắn sẵn QĐ 03/2026/QĐ-UBND giữ nguyên quy tắc port từ HeThongDinhGiaVaScanThongMinh_V2.tsx (05/11/2026); tests/vang_gia_dat_qd03.json chụp kết quả + câu chữ của bản viết cố định trước đó, mỗi lần test so từng ca:

    Đơn giá = ROUND(G_NQ28 x K1 x K2 x K3 x K_khác)               (ROUND kiểu Excel = tien.lam_tron)
    K1 theo ĐOẠN đường; K2 chỉ khi dự án đầu tư có hệ số sử dụng đất (FAR); K3 theo các yếu tố của gói (NN đường đất 0,90, tự khóa 1,00 nếu tuyến đã có quy định riêng ở Phụ lục I.2)
    Chuyển tiếp (khoản 3 Điều 4): giá đất cụ thể >= giá tính thì giữ giá cụ thể.

Làm tròn trung gian theo gói (gắn sẵn: tổng hệ số 6, giá chưa làm tròn 4 chữ số lẻ). Số tiền / hệ số là Decimal (không float). Giá G tự tra từ `gia_dat_nq28` theo cụm vị trí của gói.
K1: gói gắn sẵn mà máy đã nhập bảng hệ số K mới (thẻ Hệ số K) thì theo bảng đã nhập và ghi rõ trong giải trình: chỉ MỘT nguồn K có hiệu lực, không âm thầm tính theo số cũ. Gói riêng mang K của nó."""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import ROUND_HALF_UP, Decimal

from . import goi_gia_dat as gg
from .tien import D, lam_tron, vn

MOT = Decimal(1)


def _goi(goi=None) -> dict:
    return goi or gg._gan_san()


# ---------------------------------------------------------------- dữ liệu đoạn đường
def du_lieu() -> dict:
    return gg.du_lieu_goc()


def ds_dia_ban(goi=None) -> list:
    """Tên khóa bảng của gói: 'Bảng 53. Phường Trị An', …"""
    return list(_goi(goi)['dia_ban'].keys())


def ten_ngan(dia_ban: str) -> str:
    """'Bảng 53. Phường Trị An' -> 'Phường Trị An'."""
    s = str(dia_ban or '')
    return s.split('. ', 1)[1] if s.startswith('Bảng') and '. ' in s else s


def ds_doan(dia_ban: str, goi=None) -> list:
    return list(_goi(goi)['dia_ban'].get(dia_ban, ()))


def so_doan(goi=None) -> int:
    return sum(len(v) for v in _goi(goi)['dia_ban'].values())


def tim_doan(dia_ban: str, ma_doan: str, goi=None) -> dict | None:
    return next((r for r in ds_doan(dia_ban, goi) if r['ma_doan_duong'] == ma_doan), None)


def nhan_doan(r: dict) -> str:
    """'[TT 1-7] Đường Xóm Huế: Đường tỉnh 768 → Đường Hóc Lai'."""
    return f'[TT {r["tt_bat_dau"]}-{r["tt_ket_thuc"]}] {r["ten_duong"]}: {r["diem_dau"]} → {r["diem_cuoi"]}'


def dia_ban_theo_ten(ten: str, goi=None) -> str:
    """Tên xã / phường bất kỳ ('Trị An', 'xã Tân An'...) -> khóa bảng của gói ('' nếu gói không có)."""
    from .lap_pa import bo_dau
    t = bo_dau(ten or '')
    for p in ('xa ', 'phuong ', 'thi tran '):
        if t.startswith(p):
            t = t[len(p):]
    if not t:
        return ''
    for k in ds_dia_ban(goi):
        if t in bo_dau(ten_ngan(k)):
            return k
    return ''


def nhom_cua(goi: dict, nhom_dat: str, cot: str = '') -> dict | None:
    """Dòng nhóm đất của gói; cùng mã nhiều dòng (nông nghiệp: cây lâu năm / rừng, NTS) thì theo cột bảng giá."""
    ds = [x for x in goi['nhom_dat'] if x['ma'] == nhom_dat]
    return next((x for x in ds if x['cot_gia'] == cot), ds[0] if ds else None)


def gia_bang_gia(dia_ban: str, doan: dict | None, nhom_dat: str, ma_vi_tri: str, cot: str = '', goi=None) -> Decimal | None:
    """Giá G (đồng/m²) từ bảng giá đất đang dùng (gia_dat_nq28): dòng TT = tt_bat_dau + thứ tự vị trí trong cụm của gói. None: bảng giá không có dòng khớp (đã thay bảng, khác tên đường) - người dùng nhập tay."""
    goi = _goi(goi)
    ds_vt = goi['vi_tri']
    i = next((k for k, x in enumerate(ds_vt) if x['ma'] == ma_vi_tri), None)
    if doan is None or i is None:
        return None
    from . import gia_dat_nq28 as nq
    from .lap_pa import bo_dau
    vt = ds_vt[i].get('vi_tri', '')
    if not cot:
        n = nhom_cua(goi, nhom_dat)
        cot = n['cot_gia'] if n else ''
    if not cot:
        return None
    tt = int(doan['tt_bat_dau']) + i
    for r in nq.tat_ca():
        if r.get('tt') == tt and nq.khop_xa(ten_ngan(dia_ban), r['xa']) and r.get('vi_tri') == vt and bo_dau(r['ten_duong']) == bo_dau(doan['ten_duong']):
            try:
                return D(nq.gia_dong(r, cot))
            except (KeyError, TypeError, ValueError):
                return None
    return None


def nhom_theo_loai_dat(loai_dat: str, goi=None) -> dict | None:
    """Dòng nhóm đất của gói ứng với loại đất của dòng phương án (CLN, ONT...): theo cột bảng giá của loại đất. None: gói không có nhóm này."""
    from . import gia_dat_nq28 as nq
    cot = nq.cot_cua_loai(loai_dat)
    return next((x for x in _goi(goi)['nhom_dat'] if x['cot_gia'] == cot), None) if cot else None


def mo_ta_vi_tri(doan: dict | None, ma_vi_tri: str, goi=None) -> str:
    """Chữ ghi vào cột Vị trí của dòng đất, cùng kiểu BoSoan.chon_vi_tri_nq28. Không có đoạn đường: ''."""
    if not doan:
        return ''
    from . import gia_dat_nq28 as nq
    vt = next((x.get('vi_tri', '') for x in _goi(goi)['vi_tri'] if x['ma'] == ma_vi_tri), '')
    ten = 'Mặt tiền' if vt == 'MT' else nq.ten_vi_tri(vt)
    return f'{ten} {doan["ten_duong"]} (đoạn từ {doan["diem_dau"]} đến {doan["diem_cuoi"]})'


# ---------------------------------------------------------------- tính đơn giá
@dataclass
class DauVao:
    dia_ban: str = ''
    nhom_dat: str = 'DAT_NONG_NGHIEP'
    ma_doan_duong: str = ''
    loai_ket_noi_vi_tri: str = 'MAT_TIEN_VT1'
    ket_cau_mat_duong: str = 'NHUA_BETONG'
    don_gia_bang_gia: Decimal = field(default_factory=lambda: Decimal(0))     # G (đồng/m²)
    he_so_k1: Decimal | None = None                  # dùng khi không có đoạn đường; có đoạn thì lấy theo gói
    ap_dung_quy_hoach_pl2: bool = False
    he_so_quy_hoach_k2: Decimal = field(default_factory=lambda: Decimal(1))
    yeu_to_pl3: list = field(default_factory=list)
    he_so_khac: Decimal = field(default_factory=lambda: Decimal(1))
    gia_dat_cu_the: Decimal = field(default_factory=lambda: Decimal(0))       # chuyển tiếp
    co_quy_dinh_rieng_duong_dat_pl1: bool = False
    he_so_them: dict = field(default_factory=dict)   # hệ số gói khai báo thêm: {'K4': Decimal}
    cot_gia: str = ''                                # cột bảng giá của mục nhóm đất đang chọn


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
    don_gia_ap_dung: Decimal                         # đã xét chuyển tiếp
    ap_dung_chuyen_tiep: bool
    cong_thuc: str
    canh_bao: list
    buoc_lap_luan: list                              # nhật ký giải trình từng bước (in vào thuyết minh / hiện ở ô đơn giá)
    goi_ma: str = ''
    can_cu_ngan: str = ''                            # 'NQ 28/2025/NQ-HĐND × QĐ 03/2026/QĐ-UBND': ghi vào Ghi chú dòng đất
    ghi_chu_ct: str = ''
    he_so_them: dict = field(default_factory=dict)
    nguon_k1: str = ''                               # '' (gói) | văn bản của bảng hệ số K đã nhập


def _q(x, so_le: int) -> Decimal:
    """Làm tròn nửa lên (toFixed của bản gốc)."""
    return D(x).quantize(Decimal(1).scaleb(-so_le), rounding=ROUND_HALF_UP)


def _he(x) -> str:
    """Hệ số trong câu chữ: 1,24 ; 1 ; 0,9 (bỏ số 0 thừa)."""
    return format(D(x).normalize(), 'f').replace('.', ',')


def _hai(x) -> str:
    return format(_q(x, 2), 'f').replace('.', ',')


def he_hien(x) -> str:
    """Hệ số trên màn hình, công thức: 2 chữ số lẻ kiểu VN (1,45 ; 1,00 ; 0,90); hệ số lẻ hơn (0,9025) giữ đủ, không làm tròn mất giá trị pháp lý."""
    d = D(x)
    return _hai(d) if _q(d, 2) == d else format(d.normalize(), 'f').replace('.', ',')


def _tuyen_co_quy_dinh_rieng(doan: dict | None) -> bool:
    """Chốt chặn nhân trùng K3 (Văn bản hướng dẫn 29/05/2026 của Sở NN&MT): Phụ lục I.2 đã có K1 riêng cho tuyến đường đất, sỏi, đá, cấp phối hoặc "các tuyến đường giao thông còn lại".
    Dấu trong gói quyết định; gói mới chưa đánh dấu thì nhận theo tên tuyến."""
    if not doan:
        return False
    if doan.get('co_quy_dinh_rieng_duong_dat_tai_pl1'):
        return True
    from .lap_pa import bo_dau
    t = bo_dau(doan.get('ten_duong', ''))
    return t.startswith(('duong dat', 'duong soi', 'duong cap phoi')) or 'con lai' in t


def _k1_bang_nhap(goi: dict, v: DauVao, doan: dict, nhom: dict | None) -> tuple:
    """K1 theo bảng hệ số K máy đã nhập (thẻ Hệ số K): chỉ khi đang dùng gói gắn sẵn và máy đã thay bảng. (hệ số hoặc None, văn bản của bảng, có thay không)."""
    from . import he_so_k as hk
    if not goi.get('gan_san') or not hk.dang_thay():
        return None, '', False
    i = next((k for k, x in enumerate(goi['vi_tri']) if x['ma'] == v.loai_ket_noi_vi_tri), 0)
    cot = v.cot_gia or (nhom['cot_gia'] if nhom else '')
    k, _ = hk.tra(ten_ngan(v.dia_ban), cot, goi['vi_tri'][i].get('vi_tri', ''), doan['ten_duong'], tt=int(doan['tt_bat_dau']) + i)
    return k, hk.van_ban_ngan(), True


def _dien(mau: str, **gt) -> str:
    """Điền ô {ten} bằng thay chuỗi: mẫu đến từ file gói nên không dùng str.format (đọc được thuộc tính đối tượng)."""
    for k, x in gt.items():
        mau = mau.replace('{' + k + '}', str(x))
    return mau


def tinh_don_gia(v: DauVao, doan: dict | None = None, goi: dict | None = None) -> KetQua:
    """Đơn giá theo gói quy tắc (mặc định gói gắn sẵn). doan: dòng của ds_doan (None: dùng v.he_so_k1)."""
    goi = _goi(goi)
    ct = goi['cong_thuc']
    so_hieu, bang_gia = goi['so_hieu'], goi['bang_gia']
    mau = goi.get('cau_chu') or {}
    mau_goc = gg._gan_san()['cau_chu']

    def cau(khoa, **gt):
        return _dien(mau.get(khoa) or mau_goc[khoa], so_hieu=so_hieu, bang_gia=bang_gia, **gt)

    canh_bao, lap_luan = [], []
    g = max(D(0), D(v.don_gia_bang_gia))
    lap_luan.append(cau('buoc_1', dia_ban=v.dia_ban, vi_tri=v.loai_ket_noi_vi_tri, gia=vn(g)))

    # Bước 2: K1
    nhom = nhom_cua(goi, v.nhom_dat, v.cot_gia)
    k1 = D(v.he_so_k1) if v.he_so_k1 is not None and D(v.he_so_k1) != 0 else MOT
    nguon_k1 = ''
    if doan:
        if nhom is not None:
            if nhom['cot_k1'] in doan:
                k1 = D(doan[nhom['cot_k1']])
            else:
                canh_bao.append(f'Đoạn đường này chưa có hệ số K1 cho "{nhom["ten"]}" trong gói: đang tính với K1 = {_hai(k1)}, cần kiểm tra lại.')
        lap_luan.append(cau('buoc_2_doan', phu_luc=(nhom or {}).get('phu_luc', ''), ten_duong=doan['ten_duong'], diem_dau=doan['diem_dau'], diem_cuoi=doan['diem_cuoi'], nhom=v.nhom_dat, k1=_hai(k1)))
        k_nhap, vb_nhap, co_nhap = _k1_bang_nhap(goi, v, doan, nhom)
        if k_nhap is not None:
            nguon_k1 = vb_nhap
            if k_nhap != k1:
                lap_luan.append(f'Bước 2 (bổ sung): Bảng hệ số K đã nhập ({vb_nhap}) ghi K1 = {_hai(k_nhap)}, thay {_hai(k1)} của gói.')
            k1 = k_nhap
        elif co_nhap:
            canh_bao.append(f'Bảng hệ số K đã nhập ({vb_nhap}) không có dòng khớp đoạn đường, vị trí này: đang dùng K1 = {_hai(k1)} của gói, cần kiểm tra lại.')
    else:
        lap_luan.append(cau('buoc_2_tay', k1=_hai(k1)))

    # Bước 3: K2
    k2 = MOT
    if v.ap_dung_quy_hoach_pl2 and D(v.he_so_quy_hoach_k2) > 0:
        k2 = D(v.he_so_quy_hoach_k2)
        lap_luan.append(cau('k2_co', k2=_hai(k2)))
    else:
        lap_luan.append(cau('k2_khong'))

    # Bước 4: K3 theo các yếu tố của gói
    k3 = MOT
    la_nn = bool(nhom['la_nong_nghiep']) if nhom else False
    nhom_nay = 'nn' if la_nn else 'pnn'
    co_rieng = bool(v.co_quy_dinh_rieng_duong_dat_pl1) or _tuyen_co_quy_dinh_rieng(doan)
    ds = list(v.yeu_to_pl3 or [])
    ap, co_khoa, loai_tru = [], False, False
    for y in goi.get('yeu_to', ()):
        tich = y['ma'] in ds
        if not tich and not (y.get('kich_hoat_ket_cau') and y['kich_hoat_ket_cau'] == v.ket_cau_mat_duong):
            continue
        if y['ap_cho'] not in (nhom_nay, 'ca'):
            loai_tru = loai_tru or tich
            continue
        if y.get('khoa_neu_quy_dinh_rieng') and co_rieng:
            co_khoa = True
            continue
        k3 = _q(k3 * D(y['he_so']), 6)
        ap.append(y.get('dien_giai') or y['ten'])
    if co_khoa:
        canh_bao.append(cau('canh_bao_khoa'))
    if ap:
        lap_luan.append(cau('k3_nn_co' if la_nn else 'k3_pnn_co', yeu_to='; '.join(ap), k3=_he(k3), k3_2=_hai(k3)))
    elif co_khoa:
        lap_luan.append(cau('k3_khoa'))
    else:
        lap_luan.append(cau('k3_nn_khong' if la_nn else 'k3_pnn_khong'))
    if loai_tru:
        canh_bao.append(cau('loai_tru_nn' if la_nn else 'loai_tru_pnn'))

    k_khac = D(v.he_so_khac) if D(v.he_so_khac) > 0 else MOT
    gia_tri = {'K1': k1, 'K2': k2, 'K3': k3, 'K_KHAC': k_khac}
    them = {}
    for i, x in enumerate(goi.get('he_so_them') or (), 1):
        tu_nhap = (v.he_so_them or {}).get(x['ma'])
        gt = D(tu_nhap) if tu_nhap is not None and D(tu_nhap) > 0 else D(str(x.get('mac_dinh', 1)))
        gia_tri[x['ma']] = them[x['ma']] = gt
        lap_luan.append(f'Bước 4.{i} ({x.get("can_cu", "") or so_hieu}): {x.get("ten") or x["ma"]} -> {x["ma"]} = {_he(gt)}.')

    tich_he_so = MOT
    for ma in ct['he_so']:
        tich_he_so *= gia_tri.get(ma, MOT)
    tong = _q(tich_he_so, ct['lam_tron_he_so'])
    chua_tron = _q(g * tich_he_so, ct['lam_tron_tam'])
    da_tron = lam_tron(chua_tron, ct['lam_tron'])

    cuoi, chuyen_tiep = da_tron, False
    if (goi.get('chuyen_tiep') or {}).get('bat') and D(v.gia_dat_cu_the) > 0:
        g_ct = lam_tron(D(v.gia_dat_cu_the), 0)
        if g_ct >= da_tron:
            cuoi, chuyen_tiep = g_ct, True
            lap_luan.append(cau('ct_cao', gia_cu_the=vn(g_ct), gia_tinh=vn(da_tron)))
        else:
            lap_luan.append(cau('ct_thap', gia_cu_the=vn(g_ct), gia_tinh=vn(da_tron)))

    nhan = {'K_KHAC': 'K_khác'}
    cong_thuc = vn(g) + ''.join(f' × {he_hien(gia_tri.get(m, MOT))} ({nhan.get(m, m)})' for m in ct['he_so'] if not (m == 'K_KHAC' and k_khac == 1)) + f' = {vn(da_tron)} đ/m²'
    return KetQua(g, k1, k2, k3, k_khac, tong, chua_tron, da_tron, cuoi, chuyen_tiep, cong_thuc, canh_bao, lap_luan, goi.get('ma', ''), f'{bang_gia} × {so_hieu}', mau.get('ghi_chu_ct') or mau_goc['ghi_chu_ct'], them, nguon_k1)


def cong_thuc_gon(kq: KetQua) -> str:
    """Công thức một dòng cho ngăn áp giá nhanh: '230.000 × 1,45 × 1,00 × 1,00 = 333.500 đ/m²' (K khác chỉ khi khác 1). Có giá cụ thể chuyển tiếp thì ghi giá đang dùng."""
    he = [kq.k1, kq.k2, kq.k3] + ([kq.k_khac] if D(kq.k_khac) != 1 else []) + list(kq.he_so_them.values())
    chu = vn(kq.don_gia_nq28) + ''.join(f' × {he_hien(x)}' for x in he)
    return (f'{chu} = {vn(kq.don_gia_da_lam_tron)} đ/m²' if not kq.ap_dung_chuyen_tiep
            else f'Giá cụ thể {vn(kq.don_gia_ap_dung)} đ/m²')


def chi_tiet_ap_gia(kq: KetQua) -> dict:
    """Thông tin pháp lý lưu kèm dòng đất khi áp giá (số dạng chữ, không float): đọc lại được từng hệ số, không phải tách từ câu ghi chú."""
    from .tien import chuoi
    return dict(don_gia=chuoi(kq.don_gia_ap_dung), gia_bang_gia_nq28=chuoi(kq.don_gia_nq28), he_so_k1=chuoi(kq.k1), he_so_k2=chuoi(kq.k2), he_so_k3=chuoi(kq.k3), he_so_k_khac=chuoi(kq.k_khac),
                cong_thuc_dien_giai=kq.cong_thuc, goi=kq.goi_ma, can_cu=kq.can_cu_ngan, chuyen_tiep=bool(kq.ap_dung_chuyen_tiep))


def ghi_chu_ap_gia(kq: KetQua, doan: dict | None = None, dia_ban: str = '') -> str:
    """Câu căn cứ ghi vào ô Ghi chú của dòng đất khi áp đơn giá: nêu rõ văn bản đã dùng, để có gói mới vẫn biết số này tính theo gì."""
    d = f'{dia_ban}, ' if dia_ban else ''
    t = f'{doan["ten_duong"]} ({doan["diem_dau"]} - {doan["diem_cuoi"]}), ' if doan else ''
    return f'Đơn giá đất theo {kq.can_cu_ngan}: {d}{t}{kq.cong_thuc}' + (f' ({kq.ghi_chu_ct})' if kq.ap_dung_chuyen_tiep else '')

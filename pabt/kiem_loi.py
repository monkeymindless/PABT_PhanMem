"""Kiểm tra lỗi sau khi áp giá, trước khi trình: thông tin hộ (họ tên, địa chỉ, CCCD, ngày cấp, lỗi font), thửa đất, phương án
(số lượng, đơn giá, căn cứ, đơn giá khác danh mục, diện tích xây dựng vượt DT thu hồi, cây vượt mật độ), tổng tiền, tiến độ
(phê duyệt / chi trả / bàn giao), thông tin dự án. Sửa tự động được các lỗi trình bày (khoảng trắng, chữ hoa, chữ tổ hợp).
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from datetime import datetime

from . import an_toan as _an_toan
from . import csdl
from .lap_pa import DanhMuc, bo_dau, ra_soat_gia
from .nghiep_vu import (MUC_KHOAN, MUC_VN, BoiCanh, doc_phuong_an, doc_tat_ca_phuong_an, dong_bang_0,
                        he_so, ket_qua_ho_san, kiem_tra_pa, so_muc, tap_ma_on_dinh, tap_ma_theo_nk, tinh_pa)
from .tien import D, KHONG, so_vn, vn

LOI, CANH_BAO = 'Lỗi', 'Cảnh báo'
# 'Bác sĩ hồ sơ' (0.9.86): DT bồi thường > thu hồi, tỷ lệ chất lượng > 100%, nhân khẩu, hạn mức đất ở (trùng CCCD: 'Thông tin hộ')
BAC_SI = 'Bác sĩ hồ sơ'
NHOM = ['Thông tin dự án', 'Thông tin hộ', 'Font chữ', 'Thửa đất', 'Phương án', BAC_SI, 'Đơn giá', 'Số liệu, tổng tiền', 'Tiến độ']


@dataclass
class Loi:
    muc_do: str
    nhom: str
    noi_dung: str
    ma_ho: int | None = None
    ho_ten: str = ''
    sua_duoc: bool = False


# ---------------------------------------------------------------- chữ tiếng Việt, font
def _chu_viet() -> set:
    kq = set('đĐ')
    dau = ['', '́', '̀', '̉', '̃', '̣']
    for nguyen_am in 'aăâeêioôơuưyAĂÂEÊIOÔƠUƯY':
        for d in dau:
            kq.add(unicodedata.normalize('NFC', nguyen_am + d))
    return kq


CHU_VIET = _chu_viet()
KY_TU_HOP_LE = set(' !"#$%&\'()*+,-./0123456789:;<=>?@[\\]^_`{|}~\t\n') | set('–—‘’“”…²³≤≥×°½¼¾±•·№≈≠÷‰−ΦφΔ∅') \
    | set('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ') | CHU_VIET


_RE_KY_TU_LA = re.compile('[^' + ''.join(re.escape(c) for c in sorted(KY_TU_HOP_LE)) + ']')


def loi_font(s) -> str:
    """Mô tả lỗi font / mã hóa trong chuỗi, hoặc '' nếu ổn."""
    s = str(s or '')
    if not s:
        return ''
    # đường tắt (0.9.65 - 5.000 hộ: 40.000 chuỗi, ~1 triệu vòng Python/ký tự): mọi ký tự hợp lệ -> không lỗi. KY_TU_HOP_LE không
    # chứa dấu tổ hợp (NFC) nên kết quả giống hệt nhánh đầy đủ bên dưới (tests/test_ra_soat_0965.TestLoiFontNhanh)
    if _RE_KY_TU_LA.search(s) is None:
        return ''
    return _loi_font_day_du(s)


def _loi_font_day_du(s: str) -> str:
    """Nhánh đầy đủ của loi_font (trước 0.9.65 là toàn bộ hàm): dấu tổ hợp, ký hiệu đường kính, ký tự lạ."""
    if not s:
        return ''
    if any(unicodedata.combining(c) for c in s):
        return 'chữ dạng tổ hợp (Unicode tổ hợp / NFD) – nên chuẩn hóa'
    s = re.sub(r'[ØøΦφ∅]\s*\d', '', s)                  # ký hiệu đường kính: Ø114, Φ90
    la = sorted({c for c in s if c not in KY_TU_HOP_LE})
    if la:
        goi_y = ' (nghi văn bản gõ bằng font TCVN3/VNI)' if any(c in 'µ¸¶·¹¨©ª«®¬»¼½¾ÆÇËÌÎÏÒÓÔÕÖ×ØÜÝÞßçêîïòóôõö÷øùúûýþ' for c in la) else ''
        return f'ký tự lạ {"".join(la)[:12]!r}{goi_y}'
    return ''


def chuan_chu(s) -> str:
    """NFC + gộp khoảng trắng."""
    return ' '.join(unicodedata.normalize('NFC', str(s or '')).split())


def chuan_ho_ten(s) -> str:
    """Chuẩn hóa họ tên: NFC, gộp khoảng trắng, viết hoa chữ đầu mỗi từ ('nguyễn  văn a' -> 'Nguyễn Văn A')."""
    return ' '.join(w[:1].upper() + w[1:].lower() for w in chuan_chu(s).split())


def la_ho_ten_don(s) -> bool:
    """Chuỗi chỉ là một họ tên người (2-6 từ, chỉ chữ cái): mới tự sửa chữ hoa. Tên kèm mô tả ('… được cấp giấy - …',
    '(bà)', vợ chồng 'A - B') giữ nguyên cách viết."""
    t = chuan_chu(s)
    return bool(re.fullmatch(r"[^\W\d_]+(?: [^\W\d_]+){1,5}", t))


# ---------------------------------------------------------------- tài sản trên đất của tổ chức / hộ khác (1.0.04)
# từ khóa (so không dấu, chữ thường) cho biết hồ sơ chỉ có tài sản / cây trồng trên đất người khác quản lý / sử dụng
TU_KHOA_TAI_SAN_TREN_DAT = ('chu so huu tai san', 'tai san gan lien voi', 'tren dat', 'dat do ubnd', 'ubnd xa', 'lam truong',
                            'khu bao ton', 'quan ly', 'giao khoan', 'nhan khoan', 'hop dong khoan', 'muon dat', 'thue dat',
                            'tao lap tai san')


def _gia_tri(x, k, mac=''):
    try:
        return x[k]
    except (KeyError, IndexError, TypeError):
        return getattr(x, k, mac)


def tien_dat_cua(pa, ma_thua=None) -> bool:
    """Phương án có tiền bồi thường đất (> 0) - cả hộ, hoặc chỉ thửa ma_thua. Không cần bối cảnh: dấu của tích DT x giá x K x tỷ lệ."""
    if pa is None:
        return False
    for d in getattr(pa, 'dat', ()) or ():
        if ma_thua is not None and d.ma_thua != ma_thua:
            continue
        if d.dien_tich > 0 and d.gia_bang_gia > 0 and d.he_so_k > 0 and d.ty_le > 0:
            return True
    return False


def la_ho_tai_san_tren_dat(ho, thua, pa, map_thua_du_an) -> bool:
    """Thửa có dt_thu_hoi = 0 của hồ sơ chỉ có tài sản / cây trồng trên đất của tổ chức / hộ khác (1.0.04 - người dùng 19/10/2026)
    khi có ÍT NHẤT MỘT trong ba dấu hiệu: (a) cùng (tờ, thửa) có hồ sơ khác khai dt_thu_hoi > 0 (chủ đất / UBND xã quản lý);
    (b) phương án có dòng tài sản / cây / vật nuôi / hỗ trợ và tiền đất bằng 0; (c) họ tên, pháp lý, nguồn gốc thửa hoặc ghi chú
    dòng đất có từ khóa TU_KHOA_TAI_SAN_TREN_DAT. map_thua_du_an: {(tờ, thửa): [thửa dict]} cả dự án."""
    to, so = str(_gia_tri(thua, 'so_to') or '').strip(), str(_gia_tri(thua, 'so_thua') or '').strip()
    mt = _gia_tri(thua, 'ma_thua', None)
    if to and so:
        for t in (map_thua_du_an or {}).get((to, so), ()):
            if _gia_tri(t, 'ma_thua', None) != mt and _gia_tri(t, 'ma_ho', None) != _gia_tri(thua, 'ma_ho', None) \
                    and D(_gia_tri(t, 'dt_thu_hoi') or 0) > 0:
                return True
    if pa is not None and any(pa.khoan.get(m) for m in MUC_KHOAN) and not tien_dat_cua(pa):
        return True
    chu = [_gia_tri(ho, 'ho_ten'), _gia_tri(ho, 'phap_ly'), _gia_tri(thua, 'nguon_goc')]
    if pa is not None:
        chu += [d.ghi_chu for d in pa.dat if mt is None or d.ma_thua == mt]
    s = ' '.join(bo_dau(str(x or '')).lower() for x in chu)
    s = ' '.join(s.split())
    return any(k in s for k in TU_KHOA_TAI_SAN_TREN_DAT)


def la_quan_he_chu_dat_va_tai_san(ds_ho_thua_cung_cap) -> bool:
    """Một (tờ, thửa) có ở >= 2 hồ sơ: True khi TỐI ĐA MỘT hồ sơ có dt_thu_hoi > 0 hoặc tiền đất > 0 (chủ đất / UBND xã quản lý) và
    mọi hồ sơ còn lại đều dt_thu_hoi = 0 và tiền đất = 0 (chỉ tài sản / cây trên đất) - không phải đồng sử dụng / trùng hồ sơ.
    ds: [{'dt_thu_hoi': …, 'tien_dat': bool / số}] mỗi hồ sơ (1.0.04)."""
    co_dat = 0
    for x in ds_ho_thua_cung_cap:
        dt = D(_gia_tri(x, 'dt_thu_hoi') or 0)
        td = _gia_tri(x, 'tien_dat') or 0
        td = td if isinstance(td, bool) else D(td) > 0
        if dt > 0 or td:
            co_dat += 1
    return co_dat <= 1


# ---------------------------------------------------------------- kiểm tra
def kiem_tra(con, dm: DanhMuc | None = None) -> list:
    """Toàn bộ lỗi / cảnh báo của dự án (danh sách Loi), sắp theo hộ."""
    from .cay_trong import DongMatDo, phan_bo_mat_do, quy_chuan_mat_do, ten_goc
    kq = []
    bc = BoiCanh.tu(con)
    dm = dm or DanhMuc(con)

    def them(muc_do, nhom, nd, ma=None, ten='', sua=False):
        kq.append(Loi(muc_do, nhom, nd, ma, ten, sua))

    # ---- thông tin dự án
    da = con.execute('SELECT * FROM du_an WHERE id = 1').fetchone()
    if da is not None:
        for k, ten in (('ten', 'Tên dự án'), ('ten_dia_ban', 'Tên xã, phường'), ('nguoi_ky', 'Người ký'),
                       ('chuc_vu_ky', 'Chức vụ người ký'), ('don_vi_lap', 'Đơn vị lập')):
            if k in da.keys() and not str(da[k] or '').strip():
                them(CANH_BAO, 'Thông tin dự án', f'{ten} còn trống (in trên bản in).')
        for k in ('ten', 'ten_day_du', 'don_vi_lap', 'ten_dia_ban'):
            if k in da.keys() and loi_font(da[k]):
                them(LOI, 'Font chữ', f'Thông tin dự án ({k}): {loi_font(da[k])}.')
    # ---- hộ
    ho = [dict(r) for r in con.execute('SELECT * FROM ho ORDER BY thu_tu, ma_ho')]
    cccd = {}
    ten_dc = {}
    for h in ho:
        ma, ten = h['ma_ho'], h['ho_ten']
        t = str(ten or '')
        if not t.strip():
            them(LOI, 'Thông tin hộ', 'Họ tên trống.', ma, ten)
        else:
            # tên chủ được có chữ số (hộ số 2, thửa số 168, "là chủ sở hữu … thửa đất số 12")
            if t != t.strip() or '  ' in t:
                them(CANH_BAO, 'Thông tin hộ', 'Họ tên có khoảng trắng thừa.', ma, ten, True)
            if not loi_font(t) and la_ho_ten_don(t) and chuan_ho_ten(t) != chuan_chu(t):
                them(CANH_BAO, 'Thông tin hộ', f'Họ tên chưa viết hoa đúng: "{t}" -> "{chuan_ho_ten(t)}".', ma, ten, True)
            if len(t.split()) < 2:
                them(CANH_BAO, 'Thông tin hộ', f'Họ tên chỉ có một từ: "{t}".', ma, ten)
        if not str(h['dia_chi'] or '').strip():
            them(CANH_BAO, 'Thông tin hộ', 'Địa chỉ trống.', ma, ten)
        for k, nhan in (('ho_ten', 'Họ tên'), ('dia_chi', 'Địa chỉ'), ('noi_cap', 'Nơi cấp'), ('ghi_chu', 'Ghi chú'),
                        ('theo_doi', 'Ghi chú theo dõi')):
            lf = loi_font(h.get(k))
            if lf:
                them(LOI, 'Font chữ', f'{nhan}: {lf}.', ma, ten, 'tổ hợp' in lf)
        so = str(h['so_cccd'] or '').strip()
        if so:
            chi_so = re.sub(r'\D', '', so)
            if chi_so != so.replace(' ', ''):
                them(CANH_BAO, 'Thông tin hộ', f'Số CCCD có ký tự khác chữ số: "{so}".', ma, ten, True)
            if len(chi_so) not in (9, 12):
                them(CANH_BAO, 'Thông tin hộ', f'Số CCCD "{so}" có {len(chi_so)} chữ số (CCCD 12, CMND 9).', ma, ten)
            if chi_so:
                cccd.setdefault(chi_so, []).append(h)
        if str(h['ngay_cap'] or '').strip():
            try:
                from .quan_ly import chuan_ngay
                ng = datetime.strptime(chuan_ngay(h['ngay_cap']), '%d/%m/%Y')
                if ng > datetime.now():
                    them(LOI, 'Thông tin hộ', f'Ngày cấp {h["ngay_cap"]} sau ngày hôm nay.', ma, ten)
            except Exception:
                them(CANH_BAO, 'Thông tin hộ', f'Ngày cấp "{h["ngay_cap"]}" không đúng dạng ngày/tháng/năm.', ma, ten)
        dt = re.sub(r'\D', '', str(h['dien_thoai'] or ''))
        if dt and len(dt) not in (10, 11):
            them(CANH_BAO, 'Thông tin hộ', f'Số điện thoại "{h["dien_thoai"]}" có {len(dt)} chữ số.', ma, ten)
        ten_dc.setdefault((bo_dau(chuan_chu(t)), bo_dau(chuan_chu(h['dia_chi']))), []).append(h)
    for so, ds in cccd.items():
        if len(ds) > 1:
            for h in ds:
                them(CANH_BAO, 'Thông tin hộ', f'Trùng số CCCD {so} với hộ ' +
                     ', '.join(f'{x["thu_tu"]}. {x["ho_ten"]}' for x in ds if x is not h) + ' (cân nhắc gộp hộ).',
                     h['ma_ho'], h['ho_ten'])
    for (t, _), ds in ten_dc.items():
        if t and len(ds) > 1:
            for h in ds:
                them(CANH_BAO, 'Thông tin hộ', 'Trùng họ tên và địa chỉ với hộ ' +
                     ', '.join(f'{x["thu_tu"]}. {x["ho_ten"]}' for x in ds if x is not h) + '.', h['ma_ho'], h['ho_ten'])
    ten_ho = {h['ma_ho']: h['ho_ten'] for h in ho}
    ho_theo_ma = {h['ma_ho']: h for h in ho}
    # đọc phương án cả dự án một lần (3 truy vấn) - trước đây doc_phuong_an mỗi hộ: 5.000 hộ = 15.000 truy vấn. 1.0.04: đọc TRƯỚC
    # phần thửa (quy tắc tài sản trên đất của tổ chức / hộ khác cần phương án)
    tat_ca = doc_tat_ca_phuong_an(con)
    # ---- thửa
    vi_tri_thua = {}
    thua_theo_vi_tri = {}
    for t in bc.thua.values():
        if str(t['so_thua'] or '').strip() and str(t['so_to'] or '').strip():
            thua_theo_vi_tri.setdefault((str(t['so_to']).strip(), str(t['so_thua']).strip()), []).append(t)
    for mt, t in bc.thua.items():
        ma, ten = t['ma_ho'], ten_ho.get(t['ma_ho'], '')
        mo_ta = f'Thửa {t["so_thua"] or "?"} tờ {t["so_to"] or "?"}'
        # QUY TẮC 1 (1.0.04): hồ sơ chỉ có tài sản / cây trên đất của tổ chức / hộ khác - DT thu hồi 0 là đúng, không báo lỗi
        if D(t['dt_thu_hoi'] or 0) <= 0 and \
                not la_ho_tai_san_tren_dat(ho_theo_ma.get(ma, {}), t, tat_ca.get(ma), thua_theo_vi_tri):
            them(LOI, 'Thửa đất', f'{mo_ta}: diện tích thu hồi bằng 0.', ma, ten)
        if not str(t['so_thua'] or '').strip() or not str(t['so_to'] or '').strip():
            them(CANH_BAO, 'Thửa đất', f'{mo_ta}: thiếu số thửa / số tờ.', ma, ten)
        ld = [x.strip().upper() for x in str(t['loai_dat'] or '').replace(',', '+').split('+') if x.strip()]
        if not ld:
            them(CANH_BAO, 'Thửa đất', f'{mo_ta}: chưa có loại đất.', ma, ten)
        elif bc.loai_dat and any(x not in bc.loai_dat for x in ld):
            them(CANH_BAO, 'Thửa đất', f'{mo_ta}: loại đất "{t["loai_dat"]}" không có trong danh mục loại đất.', ma, ten)
        if str(t['so_thua'] or '').strip() and str(t['so_to'] or '').strip():
            vi_tri_thua.setdefault((str(t['so_to']).strip(), str(t['so_thua']).strip()), set()).add(ma)
    for (to, so), ds in vi_tri_thua.items():
        if len(ds) > 1:
            # QUY TẮC 2 (1.0.04): chủ đất (tối đa một hồ sơ có DT thu hồi / tiền đất) + các hồ sơ chỉ có tài sản trên đất -> không
            # phải đồng sử dụng / trùng hồ sơ: không cảnh báo cho hồ sơ nào trong nhóm
            nhom = [dict(dt_thu_hoi=sum((D(t['dt_thu_hoi'] or 0) for t in thua_theo_vi_tri.get((to, so), ()) if t['ma_ho'] == m),
                                        KHONG),
                         tien_dat=any(tien_dat_cua(tat_ca.get(m), t['ma_thua']) for t in thua_theo_vi_tri.get((to, so), ())
                                      if t['ma_ho'] == m)) for m in ds]
            if la_quan_he_chu_dat_va_tai_san(nhom):
                continue
            for ma in ds:
                them(CANH_BAO, 'Thửa đất', f'Thửa {so} tờ {to} cũng có ở hộ khác ({", ".join(ten_ho.get(x, "") for x in ds if x != ma)}): '
                     'kiểm tra đồng sử dụng / trùng hồ sơ.', ma, ten_ho.get(ma, ''))
    # ---- phương án từng hộ
    da_sua = {r[0] for r in con.execute('SELECT ma_ho FROM ho WHERE luu_luc IS NOT NULL')}
    # phương án cả dự án đã đọc một lần ở trên (tat_ca)
    # kết quả tính + kiểm tra đang nhớ (dùng chung) nếu còn đúng; không thì tính ngay trên phương án vừa đọc (không đọc lại lần 2)
    kqh = (ket_qua_ho_san(con) or {}) if type(bc) is BoiCanh else {}
    mat_do = {}                                         # quy chuẩn mật độ theo loại cây: tra một lần
    # ngưỡng của "Bác sĩ hồ sơ" (0.9.86) - hồ sơ địa phương mục quy_tac_kiem_tra
    from . import dia_phuong
    from .lap_pa import bo_dau as _bd
    qt = dia_phuong.lay('quy_tac_kiem_tra') or {}
    tl_toi_da = D(str(qt.get('ty_le_toi_da_tai_san', '100'))) / 100
    nk_canh_bao = int(qt.get('nhan_khau_canh_bao', 20))
    cap = str((con.execute('SELECT cap_dia_ban FROM du_an WHERE id = 1').fetchone() or [''])[0] or '').strip()
    khoa_cap = {'xa': 'xa', 'phuong': 'phuong', 'dac khu': 'dac_khu'}.get(_bd(cap).lower(), '')
    v = (qt.get('han_muc_dat_o_m2') or {}).get(khoa_cap)
    han_muc = D(str(v)) if v is not None else None
    for h in ho:
        ma, ten = h['ma_ho'], h['ho_ten']
        pa = tat_ca.get(ma) or doc_phuong_an(con, ma)
        k, ds_kt = kqh[ma] if ma in kqh else (tinh_pa(pa, bc), kiem_tra_pa(pa, bc))
        if ma not in da_sua:                                # hộ chưa sửa trong phần mềm: so thành tiền với file Excel lúc nhập
            for d in k.dong:
                if d.thanh_tien_excel is not None and d.thanh_tien_excel != d.thanh_tien:
                    them(CANH_BAO, 'Số liệu, tổng tiền', f'Dòng {d.stt} ({d.ten[:40]}): thành tiền phần mềm {vn(d.thanh_tien)}, '
                         f'file Excel {vn(d.thanh_tien_excel)}.', ma, ten)
        co_thua = bool(bc.thua_cua(ma))
        if co_thua and not k.co_phuong_an:
            them(CANH_BAO, 'Phương án', 'Hộ có thửa thu hồi nhưng chưa lập phương án.', ma, ten)
        # DT bồi thường mục 1 LỚN HƠN DT thu hồi của thửa: lỗi (kiem_tra_pa chỉ báo "khác" - lệch nhỏ hơn có thể do không bồi thường hết)
        dt_mot = {}
        for d in pa.dat:
            dt_mot[d.ma_thua] = dt_mot.get(d.ma_thua, KHONG) + d.dien_tich
        vuot = {}
        for t in bc.thua_cua(ma):
            dtt = dt_mot.get(t['ma_thua'], KHONG)
            if dtt > D(t['dt_thu_hoi'] or 0):
                vuot[f'Thửa {t["so_thua"]} tờ {t["so_to"]}: tổng DT ở mục 1'] = (t, dtt)
        for x in ds_kt:
            khop = next((k for k in vuot if x.startswith(k)), None)
            if khop:
                t, dtt = vuot[khop]
                them(LOI, BAC_SI, f'Thửa {t["so_thua"]} tờ {t["so_to"]}: diện tích bồi thường ở mục 1 ({so_vn(dtt)} m²) LỚN HƠN '
                     f'diện tích thu hồi ({so_vn(t["dt_thu_hoi"])} m²).', ma, ten)
                continue
            them(LOI if 'chưa có' in x or 'không gắn' in x else CANH_BAO, 'Phương án', x, ma, ten)
        # tỷ lệ chất lượng còn lại / tỷ lệ bồi thường của đất, nhà, công trình, cây, vật nuôi không quá ngưỡng (mặc định 100%)
        for i, d in enumerate(pa.dat, start=1):
            if d.ty_le is not None and he_so(d.ty_le) > tl_toi_da:
                them(LOI, BAC_SI, f'Dòng 1.{i}: tỷ lệ {so_vn(he_so(d.ty_le) * 100)}% vượt {so_vn(tl_toi_da * 100)}%.', ma, ten)
        for muc in (2, 3, MUC_VN):
            for i, d in enumerate(pa.khoan[muc], start=1):
                if d.ty_le is not None and he_so(d.ty_le) > tl_toi_da:
                    them(LOI, BAC_SI, f'Dòng {so_muc(muc)}.{i} ({d.ten[:40]}): tỷ lệ chất lượng / bồi thường '
                         f'{so_vn(he_so(d.ty_le) * 100)}% vượt {so_vn(tl_toi_da * 100)}%.', ma, ten)
        # nhân khẩu: hỗ trợ tính theo nhân khẩu mà hộ chưa nhập / khác số nhân khẩu; số nhân khẩu bất thường
        nk = h['nhan_khau']
        od, tnk = tap_ma_on_dinh(), tap_ma_theo_nk()
        theo_nk = [d for d in pa.khoan[4] if d.ma in od or d.ma in tnk]
        if theo_nk and not nk:
            them(LOI, BAC_SI, f'Có hỗ trợ tính theo nhân khẩu ({theo_nk[0].ten[:40]}) nhưng hộ chưa nhập số nhân khẩu.', ma, ten)
        elif nk:
            for d in pa.khoan[4]:
                if d.ma in od and d.so_luong != D(nk):
                    them(CANH_BAO, BAC_SI, f'Hỗ trợ ổn định đời sống tính {so_vn(d.so_luong)} nhân khẩu, hồ sơ hộ ghi {nk} nhân '
                         'khẩu.', ma, ten)
            if int(nk) > nk_canh_bao:
                them(CANH_BAO, BAC_SI, f'Số nhân khẩu {nk} lớn bất thường (trên {nk_canh_bao}): kiểm tra lại hộ khẩu / xác nhận '
                     'của UBND cấp xã.', ma, ten)
        # hạn mức đất ở (theo hồ sơ địa phương - chưa cấu hình thì không kiểm tra)
        if han_muc is not None:
            dt_o = sum((d.dien_tich for d in pa.dat if d.nhom_dat == 'Đất ở'), KHONG)
            if dt_o > han_muc:
                them(CANH_BAO, BAC_SI, f'Diện tích đất ở bồi thường {so_vn(dt_o)} m² vượt hạn mức đất ở {so_vn(han_muc)} m² '
                     f'({cap or "địa bàn"} - hồ sơ địa phương): xác định phần trong / ngoài hạn mức theo quy định.', ma, ten)
        if not k.da_luu:                                    # người dùng đã lưu: số 0 là cố ý (không bồi thường mục đó)
            for x in dong_bang_0(pa):
                them(CANH_BAO, 'Phương án', x, ma, ten)
        for muc in MUC_KHOAN:
            sm = so_muc(muc)
            for i, d in enumerate(pa.khoan[muc], start=1):
                for nhan, v in (('tên', d.ten), ('ghi chú', d.ghi_chu), ('quy cách', d.quy_cach)):
                    lf = loi_font(v)
                    if lf:
                        them(LOI, 'Font chữ', f'Dòng {sm}.{i} ({nhan}): {lf}.', ma, ten, 'tổ hợp' in lf)
                if d.so_luong < 0 or d.don_gia < 0:
                    them(LOI, 'Số liệu, tổng tiền', f'Dòng {sm}.{i} ({d.ten[:40]}): số âm.', ma, ten)
        for i, d in enumerate(pa.dat, start=1):
            if d.dien_tich < 0:
                them(LOI, 'Số liệu, tổng tiền', f'Dòng 1.{i}: diện tích âm.', ma, ten)
            tl = he_so(d.ty_le)
            if tl < 1 and not (d.ghi_chu or '').strip():
                them(CANH_BAO, 'Phương án', f'Dòng 1.{i}: tỷ lệ bồi thường {so_vn(tl * 100)}% chưa ghi lý do ở ghi chú.', ma, ten)
        # diện tích xây dựng (m²) mục 2 so với DT thu hồi của hộ
        dt_thu_hoi = sum((D(t['dt_thu_hoi'] or 0) for t in bc.thua_cua(ma)), KHONG)
        dt_xd = sum((d.so_luong for d in pa.khoan[2] if d.dvt.replace('2', '²').strip() == 'm²' and he_so(d.ty_le) > 0
                     and re.search(r'(?i)nhà|kiot|ki ốt|mái|sân|nền|chuồng|nhà xưởng|công trình', d.ten)), KHONG)
        if dt_thu_hoi > 0 and dt_xd > dt_thu_hoi:
            them(CANH_BAO, 'Phương án', f'Diện tích nhà, công trình ở mục 2 ({so_vn(dt_xd)} m²) lớn hơn DT thu hồi '
                 f'({so_vn(dt_thu_hoi)} m²): kiểm tra phần nằm ngoài ranh thu hồi.', ma, ten)
        # cây vượt mật độ trên diện tích đất nông nghiệp thu hồi
        dt_nn = sum((d.dien_tich for d in pa.dat if (bc.loai_dat.get(d.loai_dat.upper(), '') or '').lower().startswith('nông')
                     or d.loai_dat.upper() in ('CLN', 'HNK', 'LUC', 'LUK', 'BHK', 'NHK', 'RSX', 'NTS', 'CHN')), KHONG)
        # 30/10/2026: mọi loại cây cùng chia diện tích - cây đơn giá cao tính trước (cay_trong.phan_bo_mat_do); dòng đã tách "Ngoài mật độ"
        # không tính
        dong_md = []
        for d in pa.khoan[3]:
            if d.dvt.strip().lower() != 'cây' or he_so(d.ty_le) == 0 or d.so_luong != int(d.so_luong) \
                    or (d.quy_cach or '').startswith('Ngoài mật độ ('):
                continue
            m = dm.lay(d.ma or d.ma_tuong_duong)
            kq_md = (ten_goc(d.ten), m.ten if m else d.ten, m.can_cu if m else '')
            q = mat_do.get(kq_md)
            if q is None:
                q = mat_do[kq_md] = quy_chuan_mat_do(con, *kq_md)
            dong_md.append(DongMatDo(kq_md[0], int(d.so_luong), q.mat_do, d.don_gia))
        if dt_nn > 0 and any(x.mat_do for x in dong_md):
            phan_bo_mat_do(dong_md, dt_nn)
            vuot = {}
            for x in dong_md:
                if x.ngoai:
                    vuot[x.ten] = vuot.get(x.ten, 0) + x.ngoai
            if vuot:
                them(CANH_BAO, 'Phương án', 'Cây vượt mật độ trên ' + f'{so_vn(dt_nn)} m² đất NN thu hồi (cây đơn giá cao tính trước): '
                     + ', '.join(f'{g} {n} cây' for g, n in vuot.items()) + ' - dùng "Tính mật độ…" để tách cây vượt mật độ.', ma, ten)
        # tiến độ
        if h.get('da_chi_tra') and not h.get('da_phe_duyet'):
            them(LOI, 'Tiến độ', 'Đã chi trả nhưng chưa ghi phê duyệt phương án.', ma, ten)
        if h.get('da_ban_giao') and not h.get('da_phe_duyet'):
            them(CANH_BAO, 'Tiến độ', 'Đã đánh dấu bàn giao mặt bằng nhưng chưa có quyết định phê duyệt. Nếu hộ chưa bàn giao thật: '
                 'Tiến độ chi trả & Bàn giao, chọn hộ, "Bàn giao mặt bằng các hộ đã chọn…", bỏ tích "Đã bàn giao mặt bằng".', ma, ten)
        elif h.get('da_ban_giao') and not h.get('da_chi_tra'):
            them(CANH_BAO, 'Tiến độ', 'Đã bàn giao mặt bằng nhưng chưa ghi chi trả.', ma, ten)
        if h.get('da_phe_duyet') and str(h.get('qd_so_tien') or '').strip() and D(h['qd_so_tien']) != k.tong:
            them(CANH_BAO, 'Tiến độ', f'Số tiền phê duyệt {vn(h["qd_so_tien"])} khác tổng phương án hiện tại {vn(k.tong)} '
                 '(phương án sửa sau khi phê duyệt?).', ma, ten)
        if h.get('da_chi_tra') and str(h.get('chi_tra_so_tien') or '').strip() and str(h.get('qd_so_tien') or '').strip() \
                and D(h['chi_tra_so_tien']) != D(h['qd_so_tien']):
            them(CANH_BAO, 'Tiến độ', f'Số tiền đã chi {vn(h["chi_tra_so_tien"])} khác số tiền phê duyệt {vn(h["qd_so_tien"])}.',
                 ma, ten)
        if h.get('da_phe_duyet') and not str(h.get('qd_so') or '').strip():
            them(CANH_BAO, 'Tiến độ', 'Đã phê duyệt nhưng chưa ghi số quyết định.', ma, ten)
    # ---- đơn giá (dòng áp giá tương đương / nhập tay / khác danh mục)
    for x in ra_soat_gia(con, dm):
        muc_do = LOI if 'chưa ghi căn cứ' in x['ghi_chu_ra_soat'] or 'không có trong danh mục' in x['ghi_chu_ra_soat'] else CANH_BAO
        them(muc_do, 'Đơn giá', f'Dòng {x["stt"]} ({str(x["ten"])[:50]}): {x["ghi_chu_ra_soat"]}.', x['ma_ho'], x['ho_ten'])
    # ---- đối chiếu Excel (dự án nhập từ PABT Excel)
    thu_tu = {h['ma_ho']: h['thu_tu'] for h in ho}
    kq.sort(key=lambda l: (thu_tu.get(l.ma_ho, -1) if l.ma_ho is not None else -1, NHOM.index(l.nhom) if l.nhom in NHOM else 99,
                           l.muc_do != LOI))
    return kq


def sua_tu_dong(con) -> int:
    """Sửa lỗi trình bày: họ tên (khoảng trắng, chữ hoa, chữ tổ hợp), địa chỉ / nơi cấp / ghi chú (khoảng trắng, chữ tổ hợp),
    số CCCD (bỏ ký tự khác số), tên / ghi chú / quy cách các dòng phương án (chữ tổ hợp, khoảng trắng). Trả số ô đã sửa."""
    n = 0
    with con:
        for h in con.execute('SELECT ma_ho, ho_ten, dia_chi, noi_cap, ghi_chu, so_cccd FROM ho').fetchall():
            ten = chuan_chu(h['ho_ten'])
            moi = dict(ho_ten=chuan_ho_ten(ten) if la_ho_ten_don(ten) and not loi_font(ten) else ten,
                       dia_chi=chuan_chu(h['dia_chi']), noi_cap=chuan_chu(h['noi_cap']), ghi_chu=chuan_chu(h['ghi_chu']),
                       so_cccd=re.sub(r'\D', '', h['so_cccd'] or '') if re.sub(r'\D', '', h['so_cccd'] or '') else (h['so_cccd'] or ''))
            doi = {k: v for k, v in moi.items() if v != (h[k] or '')}
            if doi:
                con.execute(f'UPDATE ho SET {", ".join(k + " = ?" for k in doi)} WHERE ma_ho = ?', (*doi.values(), h['ma_ho']))
                n += len(doi)
        for r in con.execute('SELECT id, ten, ghi_chu, quy_cach FROM ct_khoan').fetchall():
            moi = {k: chuan_chu(r[k]) for k in ('ten', 'ghi_chu', 'quy_cach')}
            moi['ten'] = moi['ten'][:1].upper() + moi['ten'][1:]          # 'cây xoài…' -> 'Cây xoài…'
            doi = {k: v for k, v in moi.items() if v != (r[k] or '')}
            if doi:
                con.execute(f'UPDATE ct_khoan SET {", ".join(k + " = ?" for k in doi)} WHERE id = ?', (*doi.values(), r['id']))
                n += len(doi)
        csdl.ghi_nhat_ky(con, 'Sửa lỗi trình bày tự động', f'{n} ô')
    return n


def xuat_excel(ds: list, file_ra, ten_du_an: str = '') -> None:
    import openpyxl
    from openpyxl.styles import Alignment, Font, PatternFill
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = 'Kiem tra loi'
    ws.cell(1, 1, f'KẾT QUẢ KIỂM TRA LỖI - {ten_du_an}').font = Font(bold=True, size=13)
    ws.cell(2, 1, f'Lập lúc {datetime.now():%H:%M %d/%m/%Y}: {sum(1 for x in ds if x.muc_do == LOI)} lỗi, '
                  f'{sum(1 for x in ds if x.muc_do == CANH_BAO)} cảnh báo')
    dau = ['STT', 'Mức độ', 'Nhóm', 'Mã hộ', 'Họ và tên', 'Nội dung']
    for c, t in enumerate(dau, start=1):
        o = ws.cell(4, c, t)
        o.font = Font(bold=True, color='FFFFFF')
        o.fill = PatternFill('solid', fgColor='1F4E79')
    do = PatternFill('solid', fgColor='F8CBAD')
    for i, x in enumerate(ds, start=1):
        for c, v in enumerate([i, x.muc_do, x.nhom, x.ma_ho, x.ho_ten, x.noi_dung], start=1):
            o = ws.cell(4 + i, c, v)
            if c == 6:
                o.alignment = Alignment(wrap_text=True, vertical='top')
            if x.muc_do == LOI and c == 2:
                o.fill = do
    for c, w in zip('ABCDEF', (6, 10, 18, 8, 26, 100)):
        ws.column_dimensions[c].width = w
    ws.freeze_panes = 'A5'
    ws.auto_filter.ref = f'A4:F{4 + len(ds)}'
    _an_toan.luu_xlsx(wb, file_ra)

"""Dữ liệu bản in phương án bồi thường (1.0.19, tách khỏi in_an.py): các dòng bảng mục III, thông tin hộ / dự án, tiêu đề mục,
tên file. KHÔNG phụ thuộc Excel / Word / Qt - bản Word (in_word), bảng tổng hợp Excel (in_an) và bảng điều chỉnh cùng dùng."""
from __future__ import annotations
import re
import sqlite3
from datetime import date
from decimal import Decimal

from . import nghiep_vu
from .nghiep_vu import BoiCanh, doc_phuong_an, tinh_pa
from .tien import D, KHONG

NHAN_TDC = 'Phương án tái định cư:'


def nhan_du_an(ten: str) -> str:
    """Nhãn đứng trước tên dự án (24/10/2026): tên dự án gõ IN HOA -> "DỰ ÁN", còn lại (viết hoa chữ đầu / viết thường) -> "Dự án"."""
    chu = [c for c in str(ten or '') if c.isalpha()]
    return 'DỰ ÁN' if chu and all(c.isupper() for c in chu) else 'Dự án'


def _hai_dong(s: str) -> str:
    """'<TÊN CƠ QUAN> THÀNH PHỐ X' -> xuống dòng trước 'THÀNH PHỐ' / 'TỈNH' (tiêu đề cơ quan 2 dòng)."""
    return re.sub(r'\s+((THÀNH PHỐ|TỈNH|HUYỆN|QUẬN|THỊ XÃ) .+)$', r'\n\1', s) if len(s) > 30 else s


def _dung_nho(con) -> bool:
    """In hàng loạt: bảng nhỏ đọc MỘT lần cho cả dự án (csdl.nho - tự đọc lại khi dữ liệu đổi) thay vì một câu SELECT mỗi hộ. Đang
    giữa giao dịch / kết nối không có bộ nhớ đệm (sqlite3.Connection thường): đọc riêng từng hộ như cũ."""
    return getattr(con, 'bo_nho', None) is not None and not con.in_transaction


def _ho_dong(con, ma_ho: int):
    """Dòng bảng ho của hộ (sqlite3.Row) hoặc None."""
    if _dung_nho(con):
        from .csdl import nho
        return nho(con, 'in.ho', lambda: {r['ma_ho']: r for r in con.execute('SELECT * FROM ho')}).get(ma_ho)
    return con.execute('SELECT * FROM ho WHERE ma_ho = ?', (ma_ho,)).fetchone()


DIA_DANH_TRONG = '……………'          # chưa nhập địa danh nơi đơn vị công tác: để chỗ trống (KHÔNG lấy xã có đất của dự án)


def dia_danh_ngay(dia_danh_don_vi: str = '') -> str:
    """Địa danh đầu dòng ngày tháng của bản in ("<địa danh>, ngày … tháng … năm …") = NƠI ĐƠN VỊ CÔNG TÁC (người dùng 26/10/2026), không
    phải xã / phường có đất của dự án: ô "Địa danh nơi đơn vị công tác" của Thông tin dự án -> hồ sơ địa phương ban_in.dia_danh_ngay ->
    chỗ trống DIA_DANH_TRONG."""
    from . import dia_phuong
    return (' '.join(str(dia_danh_don_vi or '').split()) or str(dia_phuong.lay('ban_in.dia_danh_ngay', '') or '').strip()
            or DIA_DANH_TRONG)


def _thong_tin_du_an(con) -> dict:
    from .csdl import nho
    from .to_chuc import MAC_DINH
    goc = nho(con, 'in.du_an', lambda: dict(con.execute('SELECT * FROM du_an WHERE id = 1').fetchone()))
    da = dict(goc)                                 # bản riêng: nơi gọi sửa (ky_hieu_so…) không đụng bản nhớ
    for k, v in MAC_DINH.items():                  # ô thông tin đơn vị còn trống: dùng thông tin tổ chức mặc định
        if not (da.get(k) or '').strip():
            da[k] = v
    cap = (da['cap_dia_ban'] or '').strip()
    return dict(du_an=' '.join(str(da['ten'] or '').split()), ten_day_du=da['ten_day_du'] or '', cap_dia_ban=cap,
                cap_dia_ban_thuong=cap.lower(), ten_dia_ban=(da['ten_dia_ban'] or '').strip(),
                nam=da['nam'] or date.today().year, so_phuong_an=da['so_phuong_an'] or '', don_vi_lap=da['don_vi_lap'] or '',
                don_vi_cap_tren=da['don_vi_cap_tren'] or '', DON_VI_CAP_TREN=(da['don_vi_cap_tren'] or '').upper(),
                DON_VI_CAP_TREN_2DONG=_hai_dong((da['don_vi_cap_tren'] or '').upper()),
                DON_VI_TIEU_DE=(da['don_vi_tieu_de'] or da['don_vi_lap'] or '').upper(),
                DON_VI_LAP=(da['don_vi_lap'] or '').upper(), ky_hieu_so=da['ky_hieu_so'] or '', nguoi_lap=da['nguoi_lap'] or '',
                nguoi_kiem_tra=da['nguoi_kiem_tra'] or '', nguoi_ky=da['nguoi_ky'] or '',
                CHUC_VU_KY=(da['chuc_vu_ky'] or '').upper(), dia_danh_ngay=dia_danh_ngay(da.get('dia_danh_don_vi')))


def ky_hieu_cua_ho(con, ma_ho: int, mac_dinh: str = '') -> str:
    """Ký hiệu số phương án của hộ: theo đợt trình của hộ (v15), đợt chưa đặt / hộ chưa vào đợt -> mac_dinh (của dự án)."""
    try:
        if _dung_nho(con):
            from .csdl import nho
            bang = nho(con, 'in.ky_hieu_dot', lambda: {r[0]: (r[1] or '').strip() for r in con.execute(
                'SELECT h.ma_ho, d.ky_hieu_so FROM ho h JOIN dot_trinh d ON d.id = h.dot_id')})
            return bang.get(ma_ho) or mac_dinh
        r = con.execute('''SELECT d.ky_hieu_so FROM ho h JOIN dot_trinh d ON d.id = h.dot_id WHERE h.ma_ho = ?''',
                        (ma_ho,)).fetchone()
    except sqlite3.OperationalError:                     # file chỉ xem phiên bản cũ (< v15)
        return mac_dinh
    return ((r[0] or '').strip() if r else '') or mac_dinh


def ghi_chu_in(con, ma, gc) -> str:
    """Ghi chú in ra phương án: bỏ các câu giải thích tự động (giống bản Excel)."""
    s = str(gc or '').strip()
    if not s or s.startswith(('SL = ', 'ĐG = ', 'T = đ')) or 'chưa có dòng đất nông nghiệp' in s:
        return ''
    if ma:
        if _dung_nho(con):
            from .csdl import nho
            cach = nho(con, 'in.cach_tinh_ho_tro', lambda: {r['ma']: (r['cach_tinh'] or '') for r in con.execute(
                'SELECT ma, cach_tinh FROM dm_hotro')})
            if ma in cach and s == cach[ma]:
                return ''
            return s
        r = con.execute('SELECT cach_tinh FROM dm_hotro WHERE ma = ?', (ma,)).fetchone()
        if r and s == (r['cach_tinh'] or ''):
            return ''
    return s


def dien_tich_dong_dat(dt_dong, thua) -> Decimal:
    """Diện tích in ở dòng đất mục 1 (1.0.04): diện tích của dòng phương án (> 0), không thì dt_boi_thuong (> 0) rồi dt_thu_hoi
    của thửa. thua: dict / sqlite3.Row của bảng thua (hoặc rỗng)."""
    def _gt(k):
        try:
            return D(thua[k] or 0)
        except (KeyError, IndexError, TypeError, ArithmeticError, ValueError):
            return KHONG
    dt = dt_dong if dt_dong is not None else KHONG
    if dt > 0:
        return dt
    bt = _gt('dt_boi_thuong')
    return bt if bt > 0 else max(_gt('dt_thu_hoi'), KHONG)


def dong_chi_tiet(con, ma_ho: int, bc: BoiCanh | None = None, pa=None, pa_truoc=None) -> tuple:
    """Các dòng bảng in của một hộ: (danh sách (loại, [A..H]), KetQuaHo). Loại: H mục, I dòng, R thưởng, T tổng.
    pa: phương án đang soạn trong bộ nhớ (BoSoan.pa - xem trước khi chưa lưu); None = đọc từ CSDL (cộng dồn mọi lần).
    pa_truoc (1.0.05): các lần lập phương án trước của hộ - pa là MỘT lần, thưởng = phần tăng thêm (nghiep_vu.tinh_pa_lan)."""
    bc = bc or BoiCanh.tu(con)
    pa = pa if pa is not None else doc_phuong_an(con, ma_ho)
    kq = tinh_pa(pa, bc) if pa_truoc is None else nghiep_vu.tinh_pa_lan(pa, pa_truoc, bc)
    dong = []
    # 1. đất
    d1 = [d for d in kq.dong if d.muc == 1]
    dong.append(['H', ['1', 'Bồi thường đất', None, None, None, None, None, None]])
    hdr = dong[-1][1]
    if d1:
        # 1.0.04 (người dùng 19/10/2026): mỗi dòng in diện tích thật của thửa (ct_dat -> dt_boi_thuong -> dt_thu_hoi); đơn giá 0 thì
        # tên gọn (bỏ "(Vị trí: …)" dài), để trống Đơn giá / Tỷ lệ; DT 0 (tài sản trên đất người khác) thì trống cả ĐVT / Số lượng
        tong_dt = KHONG
        for d, r in zip(d1, pa.dat):
            t = bc.thua.get(r.ma_thua) or {}
            dt = dien_tich_dong_dat(d.so_luong, t)
            ten = d.ten
            if d.don_gia == 0:
                ten = nghiep_vu.mo_ta_thua(t.get('so_to', ''), t.get('so_thua', ''), r.loai_dat, bc.cap_dia_ban,
                                           bc.ten_dia_ban, None)
            gt = [d.stt, ten, 'm²' if dt > 0 else None, dt if dt > 0 else None, d.don_gia if d.don_gia else None,
                  d.ty_le if d.don_gia else None, d.thanh_tien, ghi_chu_in(con, '', d.ghi_chu)]
            dong.append(['I', gt])
            tong_dt += dt
        hdr[3] = tong_dt if tong_dt > 0 else None
        hdr[6] = kq.muc[1]
    else:
        # hộ chưa lập giá đất: liệt kê các thửa thu hồi theo hồ sơ kiểm kê; dòng đầu ghi pháp lý của hộ (vd "Đất do … quản lý,
        # không tính toán bồi thường về đất…" khi nhập phương án chi tiết từ Excel)
        k = 0
        tong_dt = KHONG
        r = _ho_dong(con, ma_ho)
        phap_ly = ' '.join(str(r['phap_ly'] or '').split()) if r else ''
        for t in bc.thua_cua(ma_ho):
            k += 1
            # chưa lập giá: tên gọn (không vị trí), diện tích > 0 vẫn in m² + số lượng; trống đơn giá / tỷ lệ (1.0.04)
            mo_ta = nghiep_vu.mo_ta_thua(t['so_to'], t['so_thua'], t['loai_dat'], bc.cap_dia_ban, bc.ten_dia_ban, None)
            dt = dien_tich_dong_dat(KHONG, t)
            dong.append(['I', [f'1.{k}', mo_ta, 'm²' if dt > 0 else None, dt if dt > 0 else None, None, None, KHONG,
                               phap_ly if k == 1 else '']])
            tong_dt += dt
        hdr[3] = tong_dt if tong_dt > 0 else None
        hdr[6] = KHONG
    # 2 nhà, 3 cây trồng, 4 vật nuôi (0.9.20: mục riêng, in dưới cây trồng - mã bên trong MUC_VN)
    for muc in (2, 3, nghiep_vu.MUC_VN):
        dong.append(['H', [str(nghiep_vu.so_muc(muc)), nghiep_vu.TEN_MUC[muc], None, None, None, None, kq.muc[muc], None]])
        for d in (x for x in kq.dong if x.muc == muc):
            dong.append(['I', [d.stt, d.ten, d.dvt, d.so_luong, d.don_gia, d.ty_le, d.thanh_tien, ghi_chu_in(con, d.ma, d.ghi_chu)]])
    # 5 các chính sách hỗ trợ: dòng có cách tính in gộp ô ĐVT..tỷ lệ; hỗ trợ đào tạo nhập theo từng thửa có dòng tên chính sách
    # đứng đầu nhóm
    from .chinh_sach import ten_ngan
    s4 = nghiep_vu.so_muc(4)
    dong.append(['H', [str(s4), nghiep_vu.TEN_MUC[4], None, None, None, None, kq.muc[4], None]])
    ds4 = [x for x in kq.dong if x.muc == 4]
    k = i = 0
    while i < len(ds4):
        d = ds4[i]
        k += 1
        if d.ma in ('CS9', 'CS10') and d.ten.startswith('Thửa đất'):
            j = i
            while j < len(ds4) and ds4[j].ma == d.ma and ds4[j].ten.startswith('Thửa đất'):
                j += 1
            nhom = ds4[i:j]
            ten = ten_ngan((bc.hotro.get(d.ma) or {}).get('ten', ''), d.ma) or 'Hỗ trợ đào tạo, chuyển đổi nghề và tìm kiếm việc làm'
            # dòng tên chính sách chỉ ghi tên + căn cứ; diện tích, đơn giá, tỷ lệ, thành tiền ở các dòng thửa bên dưới (người dùng
            # 15/10/2026: trước đây dòng tên lặp lại diện tích + thành tiền của dòng thửa - một thửa thì hai ô trùng số)
            dong.append(['I', [f'{s4}.{k}', ten, None, None, None, None, None, ghi_chu_in(con, d.ma, d.ghi_chu)]])
            for x in nhom:
                dong.append(['I', ['-', x.ten, x.dvt, x.so_luong, x.don_gia, x.ty_le, x.thanh_tien, None]])
            i = j
            continue
        gt = [f'{s4}.{k}', d.ten, d.dvt, d.so_luong, d.don_gia, d.ty_le, d.thanh_tien, ghi_chu_in(con, d.ma, d.ghi_chu)]
        dong.append(['I', gt, d.cach_tinh] if d.cach_tinh else ['I', gt])
        i += 1
    # 6. thưởng (chỉ khi có bồi thường về đất): chỉ tên + thành tiền - bỏ ĐVT, số lượng, đơn giá, tỷ lệ (người dùng 15/10/2026: tên
    # gộp ô sang hết các cột đó trong lap_chi_tiet; trước đây "1,0 | 20.000.000 | 100%"); thành tiền in đậm
    dong.append(['R', [str(nghiep_vu.so_muc(5)), nghiep_vu.TEN_MUC[5], None, None, None, None, kq.muc[5], None]])
    dong.append(['T', [None, 'TỔNG CỘNG', None, None, None, None, kq.tong, None]])
    return dong, kq


_RE_SO_DAU_DOAN = re.compile(r'^(\s*(?:\d+|[a-zđ])[.)]\s*)?')


def bo_lap_mo_dau(doan: str) -> str:
    """Đoạn nguồn gốc mở đầu bằng một cụm kết thúc ":" lặp lại hai lần liền nhau (nhập từ Excel / dán: "1. Thửa đất số 17, tờ bản
    đồ số 39, xã Phú Lý: Thửa đất số 17, tờ bản đồ số 39, xã Phú Lý: …") -> giữ một lần (1.0.04). So không dấu, bỏ khoảng trắng thừa."""
    from .lap_pa import bo_dau
    s = str(doan or '')
    m = _RE_SO_DAU_DOAN.match(s)
    so = m.group(0) if m else ''
    con_lai = s[len(so):]

    def chuan(x):
        return ' '.join(bo_dau(x).lower().split())
    while True:
        i = con_lai.find(':')
        if i <= 0:
            break
        cum = con_lai[:i + 1]
        sau = con_lai[i + 1:].lstrip()
        if not chuan(cum) or not chuan(sau).startswith(chuan(cum)):
            break
        # bỏ lần lặp đầu (giữ lần sau - đúng chữ / dấu của dữ liệu)
        n = len(cum.strip())
        k, dem = 0, 0
        while k < len(sau) and dem < len(chuan(cum)):
            k += 1
            dem = len(chuan(sau[:k]))
        if not chuan(sau[:k]) == chuan(cum):
            break
        con_lai = sau
        if n == 0:
            break
    return so + con_lai


def _nguon_goc_cac_thua(con, ma_ho: int) -> list:
    """Chữ nguồn gốc các thửa có nguồn gốc của hộ, theo thứ tự thửa."""
    sql = "SELECT {} nguon_goc FROM thua WHERE {} TRIM(nguon_goc) <> '' ORDER BY {} thu_tu, ma_thua"
    if _dung_nho(con):
        from .csdl import nho

        def tao():
            kq = {}
            for r in con.execute(sql.format('ma_ho,', '', 'ma_ho,')):
                kq.setdefault(r[0], []).append(r[1])
            return kq
        return nho(con, 'in.nguon_goc_thua', tao).get(ma_ho, [])
    return [r[0] for r in con.execute(sql.format('', 'ma_ho = ? AND', ''), (ma_ho,))]


def _thong_tin_ho(con, ma_ho: int, da: dict, che: bool | None = None) -> dict:
    h = _ho_dong(con, ma_ho)
    ten = ' '.join(str(h['ho_ten'] or '').split())
    if ' là ' in ten:
        ten = ten.split(' là ')[0].strip()
    cccd = (h['so_cccd'] or '').strip()
    if (h['ngay_cap'] or '').strip() and h['ngay_cap'] != '0':
        cccd += f' - Ngày cấp: {h["ngay_cap"].strip()}'
    if (h['noi_cap'] or '').strip():
        cccd += f' - Nơi cấp: {h["noi_cap"].strip()}'
    # 1.0.04: luôn in đủ số CCCD + ngày / nơi cấp (bỏ che CCCD; tham số che giữ cho mã gọi cũ)
    from .ho_so import chuan_nguon_goc, lam_sach_doan_van
    ng = []                                     # nguồn gốc các thửa (bỏ trùng, giữ thứ tự): mỗi nội dung một đoạn
    for nguon_goc in _nguon_goc_cac_thua(con, ma_ho):
        # 21/10/2026: xuống dòng cứng giữa câu (ô Excel nhập vào, chữ dán) nối lại - bản in Word / Excel không cụt chữ giữa câu
        chu = '\n'.join(bo_lap_mo_dau(x) for x in lam_sach_doan_van(chuan_nguon_goc(nguon_goc)))
        if chu and chu not in ng:
            ng.append(chu)
    from .lap_pa import cau_tai_dinh_cu
    tdc = cau_tai_dinh_cu(h['tai_dinh_cu']) or \
        f'Sau khi UBND {da["cap_dia_ban_thuong"] or "xã, phường"} xác nhận điều kiện tái định cư (nếu có).'
    dt = (h['dien_thoai'] or '').strip()
    k = h.keys()
    return dict(ma_ho=ma_ho, ho_ten=ten, cccd=cccd.strip(' -'), dia_chi=(h['dia_chi'] or '').strip(),
                dien_thoai='' if dt == '0' else dt, nguon_goc='\n'.join(ng), tai_dinh_cu=tdc,
                so_pa=(h['so_pa'] or '').strip() if 'so_pa' in k else '', ngay_pa=(h['ngay_pa'] or '') if 'ngay_pa' in k else '')


TIEU_DE_MUC_II = 'II. Thông tin nguồn gốc đất:'      # 0.9.87: tiêu đề mục II thống nhất (1.0.07: có dấu hai chấm)


NHAN_TO_CHUC = 'Tổ chức:'                                  # chủ sử dụng là tổ chức: thay nhãn "Họ và tên:"


NHAN_DIA_CHI_TO_CHUC = 'Địa chỉ:'                          # 1.0.04: tổ chức thay nhãn "Địa chỉ thường trú:"


# 24/10/2026 (người dùng nhắc lại yêu cầu 22/10): tiêu đề mục I THEO CHỦ SỬ DỤNG - tổ chức: "Thông tin về tổ chức"; hộ gia đình, cá nhân:
# "Thông tin về hộ gia đình, cá nhân". 1.0.19 đã ghi đè bằng tiêu đề chung của PDF mẫu ("I. Tổ chức và hộ gia đình, cá nhân bị thu hồi đất…") - SAI,
# mẫu PDF chỉ cho quy cách (lề, cỡ chữ), không đổi tiêu đề người dùng đã chỉ định.
TIEU_DE_MUC_I_HO = 'I. Thông tin về hộ gia đình, cá nhân'


TIEU_DE_MUC_I_TO_CHUC = 'I. Thông tin về tổ chức'


def tieu_de_muc_i(to_chuc: bool) -> str:
    return TIEU_DE_MUC_I_TO_CHUC if to_chuc else TIEU_DE_MUC_I_HO


def chon_lan_in(con, ma_ho: int, lan=None):
    """Lần phương án sẽ in (1.0.05): None / 'moi_nhat' = lần muộn nhất có dòng; 'cong_don' = None (mọi lần cộng dồn); số = lần đó."""
    if lan == 'cong_don':
        return None
    if lan is None or lan == 'moi_nhat':
        from .lan_pa import lan_moi_nhat
        return lan_moi_nhat(con, ma_ho)
    return int(lan)


def ten_file_ho(con, ma_ho: int) -> str:
    h = _ho_dong(con, ma_ho)
    ten = ' '.join(str(h['ho_ten'] or '').split())
    # "Nguyễn Văn A là chủ sở hữu tài sản gắn liền với thửa đất số…" (họ tên nhập kèm diễn giải): tên file chỉ lấy phần họ tên
    ten = re.split(r'\s+là\s+(?:chủ|người|đại diện|đồng)\b', ten, maxsplit=1, flags=re.I)[0]
    ten = re.sub(r'[\\/:*?"<>|\r\n\t]+', ' ', ten)[:60].strip()
    return f'PA_{h["thu_tu"]:03d}_ma{ma_ho}_{ten}'

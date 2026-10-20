"""Lập phương án một hộ trong phần mềm (giai đoạn 2).

BoSoan giữ phương án đang soạn trong bộ nhớ: thêm / sửa / xóa dòng, chọn từ danh mục, hạng mục ngoài danh mục
áp giá tương đương hoặc nhập tay, gợi ý các khoản hỗ trợ, rồi LƯU trong một giao dịch SQLite (tất cả hoặc không).
Màn hình chỉ hiển thị và chuyển thao tác của người dùng vào đây, nên mọi quy tắc đều kiểm thử được không cần cửa sổ.
"""
from __future__ import annotations
import copy
import functools
import re
import sqlite3
import unicodedata
from dataclasses import dataclass, replace
from datetime import datetime

from . import csdl
from .nghiep_vu import (DA_LAP_LUU, MA_ON_DINH, MA_TDC, MA_THEO_NK, MUC_KHOAN, MUC_VN, NGUON_DM, NGUON_TAY, NGUON_TD, BoiCanh,
                        DongDat, DongKhoan, PhuongAn, la_vat_nuoi, so_muc,
                        de_xuat_dao_tao_pa, doc_phuong_an, giu_ket_qua_ho, goi_y_ho_tro, goi_y_khoan, ket_qua_ho_san,
                        kiem_tra_pa, so_vi_tri, thanh_tien_dong, thanh_tien_dong_dat, tinh_pa)
from .loai_dat import chuan_ma_loai_dat
from .tien import D, KHONG, chuoi, so_luong_vn, so_vn, vn


class LoiNhap(ValueError):
    """Giá trị người dùng nhập không hợp lệ (thông báo tiếng Việt, hiện nguyên cho người dùng)."""


def bo_dau(s) -> str:
    return _bo_dau(str(s or ''))


def _bang_bo_dau() -> dict:
    """Ký tự Latin có dấu (gồm mọi chữ tiếng Việt) -> chữ không dấu, dựng MỘT lần: str.translate thay cho tách dấu NFD từng ký tự
    (danh mục 5.668 mục: 0,2 giây -> vài chục ms mỗi lần mở dự án / cửa sổ lập phương án)."""
    bang = {}
    for i in list(range(0xC0, 0x250)) + list(range(0x1E00, 0x1F00)):
        c = chr(i)
        k = ''.join(x for x in unicodedata.normalize('NFD', c) if unicodedata.category(x) != 'Mn')
        if k != c:
            bang[i] = k
    bang[ord('đ')], bang[ord('Đ')] = 'd', 'D'
    return bang


_BANG_BO_DAU = _bang_bo_dau()
_RE_NGOAI_ASCII = re.compile(r'[^\x00-\x7f]')
_ON_DINH = {}          # ký tự ngoài ASCII -> True nếu tách dấu không đổi nó (², ×, –, Ø...: không có dạng tách, không phải dấu)


def _on_dinh(c: str) -> bool:
    v = _ON_DINH.get(c)
    if v is None:
        v = _ON_DINH[c] = (unicodedata.normalize('NFD', c) == c and unicodedata.category(c) != 'Mn'
                           and unicodedata.combining(c) == 0)
    return v


@functools.lru_cache(maxsize=65536)
def _bo_dau(s: str) -> str:
    """Chữ thường không dấu (nhớ kết quả: danh mục vài nghìn mục được tìm / lọc nhiều lần mỗi khi mở cửa sổ)."""
    t = s.translate(_BANG_BO_DAU)
    if not t.isascii() and not all(_on_dinh(c) for c in _RE_NGOAI_ASCII.findall(t)):
        # còn dấu rời (chữ dạng NFD) / ký tự có dạng tách ngoài bảng: tách dấu như cũ - kết quả giống hệt
        t = unicodedata.normalize('NFD', t).replace('đ', 'd').replace('Đ', 'D')
        t = ''.join(c for c in t if unicodedata.category(c) != 'Mn')
    return ' '.join(t.lower().split())


def doc_so(text, ten_o: str, cho_phep_trong: bool = True, toi_thieu=KHONG, toi_da=None):
    """Đọc số người dùng gõ ('1.480.500', '143,8', '100%') hoặc công thức ('=4,2*5,7', '12x3+1,5'); sai thì báo LoiNhap."""
    from .tien import la_cong_thuc, tinh_cong_thuc
    s = str(text if text is not None else '').strip()
    if s and la_cong_thuc(s):
        try:
            v = tinh_cong_thuc(s)
        except ValueError as e:
            raise LoiNhap(f'{ten_o}: công thức "{text}" không tính được ({e}).') from None
        s = None
    else:
        phan_tram = s.endswith('%')
        s = s.rstrip('%').strip()
    if s == '':
        if cho_phep_trong:
            return KHONG
        raise LoiNhap(f'{ten_o}: chưa nhập.')
    if s is not None:
        from .tien import doc_so_vn
        try:
            v = doc_so_vn(s)                        # kiểu Việt Nam: 1.000 = một nghìn (số lẻ dùng dấu phẩy: 2,125)
        except ValueError:
            raise LoiNhap(f'{ten_o}: "{text}" không phải là số.') from None
        if phan_tram:
            v = v / 100
    if v < toi_thieu:
        raise LoiNhap(f'{ten_o}: không được nhỏ hơn {so_vn(toi_thieu)}.')
    if toi_da is not None and v > toi_da:
        raise LoiNhap(f'{ten_o}: không được lớn hơn {so_vn(toi_da)}.')
    return v


def _cong_thuc(text) -> str:
    """Chuỗi công thức người dùng gõ (để hiện lại khi sửa ô); gõ số thường thì trả rỗng."""
    from .tien import la_cong_thuc
    s = ' '.join(str(text or '').split())
    return ('=' + s.lstrip('=').strip()) if s and la_cong_thuc(s) else ''


def so_le_so_luong(dvt: str) -> int:
    """Số chữ số thập phân của số lượng theo ĐVT: ha (cả "ha/vụ", "ha/năm" - vật nuôi QĐ 31/2025) và đơn vị bội ("100m3/vụ":
    lồng 25 m³ = 0,25) giữ 4 chữ số; đơn vị khác 1 chữ số."""
    d = bo_dau(dvt).split('/')[0].strip()
    return 4 if d == 'ha' or d[:1].isdigit() else 1


def doc_so_luong(text, dvt: str = '', ten_o: str = 'Số lượng'):
    """Số lượng mục 2, 3, 4 (gõ số hoặc công thức): làm tròn 1 chữ số thập phân; ĐVT ha giữ 4 chữ số (so_le_so_luong)."""
    from .tien import lam_tron
    v = doc_so(text, ten_o)
    return lam_tron(v, so_le_so_luong(dvt))


def doc_ty_le(text):
    """Tỷ lệ gõ dạng phần trăm: '100' / '100%' / '70' -> 1 / 1 / 0,7. Ô để trống = None (màn hình không hiện 100; khi tính tiền vẫn lấy 100%)."""
    s = str(text or '').strip().rstrip('%').strip()
    if s == '':
        return None
    # hỗ trợ đào tạo, chuyển đổi nghề tính 150% giá đất: tỷ lệ được vượt 100% (tối đa 500%)
    return doc_so(s, 'Tỷ lệ', toi_da=D(500)) / 100


def hien_ty_le(v) -> str:
    if v is None or str(v).strip() == '':
        return ''
    return so_vn(D(v) * 100)


# ---------------------------------------------------------------- danh mục đơn giá
@dataclass
class MucDanhMuc:
    nguon: str          # 'taisan' / 'hotro' / 'quyuoc'
    ma: str
    ten: str
    dvt: str
    don_gia: object     # Decimal hoặc None (chưa có giá trong danh mục)
    phan_loai: str = ''
    can_cu: str = ''
    nhom: int = 0
    _khoa: str = ''


NHOM_TIM = {2: 'Nhà, công trình', 3: 'Cây trồng', MUC_VN: 'Vật nuôi', 4: 'Hỗ trợ', 9: 'Quy ước tương đương'}
TU_LAP = 'Phương án tự lập - chưa soát'       # trạng thái hộ: phương án phần mềm tự lập lúc tạo Dự án mới, người dùng chưa mở soát
HANG_LOAT_GIAY, HANG_LOAT_TOI_THIEU = 3, 5


def phan_loai_lap(con, co_pa: dict | None = None) -> dict:
    """ma_ho -> 'da_lap' (người dùng đã lập / lưu, hoặc nhập từ Excel) | 'tu_lap' (phần mềm tự lập lúc tạo Dự án mới, chưa soát)
    | 'chua' (chưa có dòng nào). co_pa: {ma_ho: có phương án} đã tính sẵn (không thì tính lại).

    Từ 0.9.13 phương án tự lập mang trạng thái TU_LAP. File dự án tạo trước đó: phương án tự lập cũng ghi "Đã lập phương
    án" - nhận ra vì được lưu hàng loạt (>= 5 hộ, mỗi hộ cách hộ trước <= 3 giây) lúc tạo dự án; hộ người dùng lập lưu rời rạc.
    (Trước 0.9.16 nằm ở in_an - in_an vẫn giữ tên này.)"""
    from datetime import datetime as _dt
    if co_pa is None:
        from .nghiep_vu import tinh_tat_ca
        co_pa = {k.ma_ho: k.co_phuong_an for k in tinh_tat_ca(con)}
    ho = con.execute('SELECT ma_ho, trang_thai, luu_luc FROM ho').fetchall()
    luc = []
    for r in ho:
        if co_pa.get(r['ma_ho']) and r['luu_luc']:
            try:
                luc.append((_dt.fromisoformat(str(r['luu_luc'])), r['ma_ho']))
            except ValueError:
                pass
    luc.sort()
    hang_loat, dot = set(), []
    for i, (t, m) in enumerate(luc):
        if dot and (t - luc[i - 1][0]).total_seconds() > HANG_LOAT_GIAY:
            if len(dot) >= HANG_LOAT_TOI_THIEU:
                hang_loat.update(dot)
            dot = []
        dot.append(m)
    if len(dot) >= HANG_LOAT_TOI_THIEU:
        hang_loat.update(dot)
    kq = {}
    for r in ho:
        m = r['ma_ho']
        tt = str(r['trang_thai'] or '')
        # "Đã lập…" kể cả chưa có dòng tiền (ô đất / tài sản / hỗ trợ bỏ trống). Tự lập vẫn tách riêng.
        if not co_pa.get(m) and not tt.startswith('Đã lập'):
            kq[m] = 'chua'
        elif tt.startswith(TU_LAP) or m in hang_loat:
            kq[m] = 'tu_lap'
        else:
            kq[m] = 'da_lap'
    return kq


class DanhMuc:
    """Danh mục đơn giá của dự án (DG_NHANUOC, DM_HOTRO, quy ước tương đương) để tìm theo từ khóa không dấu."""

    def __init__(self, con):
        self.muc = {2: [], 3: [], MUC_VN: [], 4: [], 9: []}
        for r in con.execute('SELECT * FROM dm_taisan WHERE nhom IN (2, 3) ORDER BY rowid'):
            nhom = MUC_VN if r['nhom'] == 3 and la_vat_nuoi(r['phan_loai']) else r['nhom']    # vật nuôi: mục riêng (0.9.20)
            m = MucDanhMuc('taisan', r['ma'], r['ten'], r['dvt'], D(r['don_gia']) if r['don_gia'] not in (None, '') else None,
                           r['phan_loai'], r['ghi_chu'], nhom)
            self.muc[nhom].append(m)
        for r in con.execute('SELECT * FROM dm_hotro ORDER BY LENGTH(ma), ma'):    # CS2 trước CS10 (mã 0.9.69 không có số 0)
            self.muc[4].append(MucDanhMuc('hotro', r['ma'], r['ten'], r['dvt'],
                                          D(r['don_gia']) if r['don_gia'] not in (None, '') else None,
                                          r['cach_tinh'], r['can_cu'], 4))
        for r in con.execute('SELECT * FROM quy_uoc ORDER BY id'):
            self.muc[9].append(MucDanhMuc('quyuoc', f'QU{r["id"]}', r['ten_thuc_te'], r['dvt'],
                                          D(r['don_gia']) if r['don_gia'] not in (None, '') else None,
                                          r['ten_tuong_duong'], r['can_cu'], 9))
        self.theo_ma = {}
        for ds in self.muc.values():
            for m in ds:
                m._khoa = bo_dau(f'{m.ma} {m.ten} {m.phan_loai}')
                self.theo_ma.setdefault(m.ma, m)

    def tim(self, nhom: int, tu_khoa: str = '', toi_da: int = 300) -> list:
        tu = bo_dau(tu_khoa).split()
        ds = [m for m in self.muc.get(nhom, []) if all(t in m._khoa for t in tu)]
        if tu:
            dau = tu[0]
            ds.sort(key=lambda m: (not bo_dau(m.ten).startswith(dau), not bo_dau(m.ma).startswith(dau), len(m.ten)))
        return ds[:toi_da]

    def lay(self, ma: str):
        return self.theo_ma.get(ma)


def tra_gia_dat(con, bc: BoiCanh, loai_dat: str, vi_tri: str):
    """Giá bảng giá cho loại đất + vị trí: bảng GIA_DAT của dự án, không có thì giá đã dùng trong dự án.
    Trả (giá, hệ số K, nguồn) hoặc (None, None, '')."""
    ld, vt = (loai_dat or '').upper(), so_vi_tri(vi_tri)
    if not ld or not vt:
        return None, None, ''
    # bảng GIA_DAT theo loại đất: dựng một lần trên bối cảnh (bối cảnh đọc lại khi dữ liệu đổi; lưu phương án giữ bối cảnh
    # nhưng không đổi gia_dat) - tự lập phương án 5.000 thửa trước đây quét cả bảng gia_dat cho từng thửa
    bang = bc.__dict__.get('_gia_dat_theo_loai')
    if bang is None:
        bang = {}
        for r in con.execute('SELECT * FROM gia_dat ORDER BY id'):
            bang.setdefault((r['loai_dat'] or '').upper(), []).append(r)
        bc.__dict__['_gia_dat_theo_loai'] = bang
    for r in bang.get(ld, ()):
        if so_vi_tri(r['vi_tri']) == vt and r['gia'] not in (None, '') and (
                not r['xa_phuong'] or bo_dau(bc.ten_dia_ban) in bo_dau(r['xa_phuong'])):
            return D(r['gia']), D(r['he_so_k']) if r['he_so_k'] not in (None, '') else D(1), 'bảng giá đất'
    dem = {}
    # giá đã dùng: gộp trong SQL (mỗi bộ giá / hệ số / vị trí một dòng) thay vì đổi số từng dòng ct_dat bằng Python
    for r in con.execute('''SELECT gia_bang_gia, he_so_k, vi_tri, COUNT(*) AS n FROM ct_dat WHERE upper(loai_dat) = ?
                            GROUP BY gia_bang_gia, he_so_k, vi_tri''', (ld,)):
        if so_vi_tri(r['vi_tri']) == vt and D(r['gia_bang_gia']) > 0:
            k = (D(r['gia_bang_gia']), D(r['he_so_k'] or 1))
            dem[k] = dem.get(k, 0) + r['n']
    if dem:
        (g, k), _ = max(dem.items(), key=lambda t: t[1])
        return g, k, 'giá đã dùng trong dự án'
    return None, None, ''


# ---------------------------------------------------------------- soạn phương án một hộ
COT_DAT = ['thua', 'loai_dat', 'dien_tich', 'vi_tri', 'gia_bang_gia', 'he_so_k', 'ty_le', 'thanh_tien', 'ghi_chu']
COT_KHOAN = ['ma', 'ten', 'dvt', 'so_luong', 'don_gia', 'ty_le', 'thanh_tien', 'nguon', 'quy_cach', 'can_cu_gia', 'ghi_chu']
MA_HE_SO = ('CS7', 'CS9', 'CS10', 'CS11', 'CS12', 'CS13')   # cột Đơn giá danh mục là hệ số: đơn giá tính theo hộ
SUA_DUOC_DAT = {'thua', 'loai_dat', 'dien_tich', 'vi_tri', 'gia_bang_gia', 'he_so_k', 'ty_le', 'ghi_chu'}
SUA_DUOC_KHOAN = {'ten', 'dvt', 'so_luong', 'don_gia', 'ty_le', 'quy_cach', 'can_cu_gia', 'ghi_chu', 'cach_tinh'}
# tình trạng tái định cư của hộ (thay các dòng CS11-CS13 không có đơn giá tiền)
TAI_DINH_CU = ['Không có',
               'Không đủ điều kiện tái định cư',
               'Đủ điều kiện theo khoản 4 Điều 111 Luật Đất đai năm 2024',
               'Đủ điều kiện theo khoản 5 Điều 111 Luật Đất đai năm 2024',
               'Đủ điều kiện theo khoản 4 Điều 111 Luật Đất đai năm 2024 (hộ gia đình có nhiều thế hệ hoặc có nhiều cặp vợ chồng '
               'cùng chung sống trên một thửa đất đủ điều kiện để tách thành từng hộ gia đình riêng theo quy định của pháp luật '
               'về cư trú)']


def cau_tai_dinh_cu(tinh_trang: str) -> str:
    """Câu in ra phương án: 'Đủ điều kiện theo khoản 4 Điều 111…' -> 'Đủ điều kiện bố trí một (01) suất tái định cư theo quy
    định tại khoản 4 Điều 111 Luật Đất đai năm 2024.'; nội dung khác in nguyên (thêm dấu chấm)."""
    t = ' '.join(str(tinh_trang or '').split()).rstrip('.')
    if not t:
        return ''
    m = re.match(r'(?i)đủ điều kiện (?:tái định cư )?theo (?:quy định tại )?(khoản .+)$', t)
    if m:
        return f'Đủ điều kiện bố trí một (01) suất tái định cư theo quy định tại {m.group(1)}.'
    return t + '.'


def _dang_luu(pa: PhuongAn):
    """Dạng so sánh để biết phương án đã thay đổi chưa."""
    return (pa.ho.nhan_khau, pa.ho.phai_di_chuyen, pa.ho.dt_nn_dang_dung, pa.ho.tai_dinh_cu,
            [replace(d, id=None, thanh_tien_excel=None) for d in pa.dat],
            {m: [replace(d, id=None, thanh_tien_excel=None) for d in ds] for m, ds in pa.khoan.items()})


def _mot_lan_chua_duyet(con, ma_ho: int) -> bool:
    """Hộ chỉ có lần 1, chưa có quyết định, lần 1 không khóa tay (một câu truy vấn)."""
    try:
        r = con.execute('''SELECT (SELECT COUNT(*) FROM qd_ho WHERE ma_ho = ?),
                                  (SELECT COUNT(*) FROM pa_lan WHERE ma_ho = ? AND (lan > 1 OR khoa = 1 OR trang_thai <> 'dang_lap')),
                                  (SELECT COUNT(*) FROM ct_dat WHERE ma_ho = ? AND lan > 1),
                                  (SELECT COUNT(*) FROM ct_khoan WHERE ma_ho = ? AND lan > 1)''', (ma_ho,) * 4).fetchone()
    except sqlite3.OperationalError:                    # file chỉ xem bản cũ: không có pa_lan / cột lan
        return not con.execute('SELECT 1 FROM qd_ho WHERE ma_ho = ? LIMIT 1', (ma_ho,)).fetchone()
    return not any(r)


class BoSoan:
    """Soạn phương án MỘT LẦN của một hộ (1.0.05: hộ có nhiều lần lập phương án - lần đầu + bổ sung, lan_pa). self.pa = dòng của lần
    đang soạn; các lần khác giữ nguyên khi lưu. Lần đã có quyết định phê duyệt: self.khoa (chỉ xem - lưu báo LoiNhap)."""

    def __init__(self, con, ma_ho: int, danh_muc: DanhMuc | None = None, bc: BoiCanh | None = None, lan: int | None = None,
                 mot_lan: bool = False):
        self.con = con
        self._mot_lan = mot_lan     # nơi gọi biết hộ chỉ có lần 1, chưa quyết định (dự án vừa tạo) - bỏ truy vấn kiểm tra
        self.dm = danh_muc or DanhMuc(con)
        # bc: bối cảnh dùng chung cả loạt hộ (tự lập phương án Dự án mới - lưu phương án không đổi thửa / danh mục nên bối cảnh còn
        # đúng); không truyền: lấy theo csdl.nho (mỗi lần mở 1 truy vấn PRAGMA data_version - 3.000 hộ ~0,25 s)
        self._bc_chung = bc
        self.mo(ma_ho, lan)

    # ---------------------------------------------- mở / trạng thái
    def mo(self, ma_ho: int, lan: int | None = None):
        from . import lan_pa
        self.bc = self._bc_chung if self._bc_chung is not None else BoiCanh.tu(self.con)
        if lan in (None, 1) and (getattr(self, '_mot_lan', False) or _mot_lan_chua_duyet(self.con, ma_ho)):
            # đường tắt (hầu hết các hộ - tự lập Dự án mới 3.000 hộ): một lần, chưa quyết định -> một lần đọc như trước 1.0.05
            self.lan, self.khoa = 1, False
            self.pa = doc_phuong_an(self.con, ma_ho)
            self.pa_truoc = PhuongAn(ho=self.pa.ho)
            self.pa_khac = PhuongAn(ho=self.pa.ho)
        else:
            self.lan = int(lan) if lan else lan_pa.lan_mac_dinh(self.con, ma_ho)
            self.khoa = lan_pa.dang_khoa(self.con, ma_ho, self.lan)
            self.pa = doc_phuong_an(self.con, ma_ho, lan=self.lan)
            self.pa_truoc = doc_phuong_an(self.con, ma_ho, den_lan=self.lan - 1)     # các lần trước (thưởng lũy kế)
            self.pa_khac = doc_phuong_an(self.con, ma_ho, ngoai_lan=self.lan)        # mọi lần khác (cộng dồn, DT đã dùng)
        self._pa_goc = copy.deepcopy(self.pa)           # bản lúc mở: so thay đổi, tổng cũ khi lưu (không đọc lại CSDL)
        self._goc = _dang_luu(self._pa_goc)

    def ds_lan(self) -> list:
        from . import lan_pa
        return lan_pa.ds_lan(self.con, self.ma_ho)

    def lap_bo_sung(self, ten: str = '', ghi_chu: str = '') -> int:
        """Lập phương án BỔ SUNG cho hộ (lần mới, rỗng) rồi mở lần đó. Phương án đang soạn còn thay đổi chưa lưu: LoiNhap."""
        if self.co_thay_doi:
            raise LoiNhap('Lưu hoặc bỏ thay đổi của lần đang soạn trước khi lập phương án bổ sung.')
        from . import lan_pa
        lan = lan_pa.tao_lan_moi(self.con, self.ma_ho, ten, ghi_chu)
        self.mo(self.ma_ho, lan)
        return lan

    @property
    def ket_qua_cong_don(self):
        """Kết quả CỘNG DỒN mọi lần của hộ (lần đang soạn lấy số liệu chưa lưu)."""
        from .nghiep_vu import gop_phuong_an
        return tinh_pa(gop_phuong_an(self.pa_khac, self.pa), self.bc)

    def tinh_cong_don(self):
        """KetQuaHo cộng dồn mọi lần của hộ (= ket_qua_cong_don)."""
        return self.ket_qua_cong_don

    @property
    def ma_ho(self) -> int:
        return self.pa.ho.ma_ho

    @property
    def co_thay_doi(self) -> bool:
        return _dang_luu(self.pa) != self._goc

    @property
    def ket_qua(self):
        """Kết quả của LẦN đang soạn (thưởng = phần tăng thêm so với các lần trước - nghiep_vu.tinh_pa_lan)."""
        from .nghiep_vu import tinh_pa_lan
        return tinh_pa_lan(self.pa, self.pa_truoc, self.bc)

    @property
    def canh_bao(self) -> list:
        return kiem_tra_pa(self.pa, self.bc)

    def danh_sach_ho(self) -> list:
        return [(r['ma_ho'], r['thu_tu'], r['ho_ten']) for r in self.con.execute('SELECT ma_ho, thu_tu, ho_ten FROM ho ORDER BY thu_tu, ma_ho')]

    def ho_ke(self, buoc: int):
        ds = [x[0] for x in self.danh_sach_ho()]
        i = ds.index(self.ma_ho) + buoc
        return ds[i] if 0 <= i < len(ds) else None

    def thua_cua_ho(self) -> list:
        """Các thửa của hộ: (ma_thua, mô tả, DT còn chưa đưa vào mục 1)."""
        kq = []
        for t in self.bc.thua_cua(self.ma_ho):
            mt = t['ma_thua']
            # DT đã đưa vào mục 1 ở MỌI lần (lần bổ sung không bồi thường lại phần đất đã có ở lần trước)
            da_dung = sum((d.dien_tich for d in self.pa.dat + self.pa_khac.dat if d.ma_thua == mt), KHONG)
            con_lai = max(D(t['dt_thu_hoi']) - da_dung, KHONG)
            kq.append((mt, f'Thửa {t["so_thua"]} tờ {t["so_to"]} – {t["loai_dat"] or "?"} – {so_vn(t["dt_thu_hoi"])} m²',
                       con_lai))
        return kq

    def canh_bao_dien_tich(self, i: int) -> str:
        """Cảnh báo tức thời KHÔNG chặn (20/10/2026) cho diện tích dòng đất i: tổng DT mục 1 của thửa (mọi lần lập) lớn hơn DT thu
        hồi, hoặc DT dòng lớn hơn DT nguyên thửa (thua.dt_nguyen_thua - cột có thể chưa có ở file cũ). '' = không có gì."""
        if not 0 <= i < len(self.pa.dat):
            return ''
        d = self.pa.dat[i]
        t = self.bc.thua.get(d.ma_thua) if d.ma_thua is not None else None
        if t is None or not d.dien_tich:
            return ''

        def so(x):
            try:
                return D(x) if x not in (None, '') else None
            except (ArithmeticError, ValueError):
                return None
        loi = []
        th = so(t.get('dt_thu_hoi'))
        if th:
            tong = sum((x.dien_tich for x in self.pa.dat + self.pa_khac.dat if x.ma_thua == d.ma_thua), KHONG)
            if tong > th:
                con = max(th - (tong - d.dien_tich), KHONG)
                loi.append(f'Tổng DT mục 1 của thửa ({so_vn(tong)} m²) lớn hơn DT thu hồi ({so_vn(th)} m²) - dòng này chỉ còn '
                           f'{so_vn(con)} m²')
        ng = so(t.get('dt_nguyen_thua'))
        if ng and d.dien_tich > ng:
            loi.append(f'DT dòng ({so_vn(d.dien_tich)} m²) lớn hơn DT nguyên thửa ({so_vn(ng)} m²)')
        return '; '.join(loi)

    def ten_thua(self, ma_thua) -> str:
        t = self.bc.thua.get(ma_thua)
        return f'Thửa {t["so_thua"]} tờ {t["so_to"]}' if t else '(không gắn thửa)'

    # ---------------------------------------------- thông tin hộ
    def dat_nhan_khau(self, text):
        """Nhân khẩu; các dòng tính theo nhân khẩu cập nhật theo (ổn định đời sống: SL; thuê nhà / tự lo chỗ ở: đơn giá)."""
        v = doc_so(text, 'Nhân khẩu', toi_da=D(200))
        if v != int(v):
            raise LoiNhap('Nhân khẩu: phải là số nguyên.')
        from . import chinh_sach as cs
        cu = self.pa.nhan_khau
        self.pa.ho.nhan_khau = int(v) or None
        nk = self.pa.ho.nhan_khau
        if not nk:
            return
        for d in self.pa.dong_ho_tro(*MA_ON_DINH):
            if d.nguon_gia == NGUON_DM and (not d.so_luong or d.so_luong == (cu or 0)):
                cs.doi_nhan_khau_on_dinh(d, nk)
                d.thanh_tien_excel = None
        if not self.pa.dong_ho_tro('CS21', 'CS22', 'CS25', 'CS26'):
            for d in self.pa.dong_ho_tro(*MA_THEO_NK):
                if d.nguon_gia == NGUON_DM:
                    cs.tinh_lai_thue_nha(d, self.bc, nk)
                    d.thanh_tien_excel = None

    def them_dong_ho_tro(self, ds: list) -> int:
        """Thêm các dòng mục 4 dựng sẵn theo cách tính (chinh_sach.dong_…). Trả chỉ số dòng cuối."""
        if not ds:
            raise LoiNhap('Chưa có dòng nào để thêm.')
        self.pa.khoan[4].extend(ds)
        return len(self.pa.khoan[4]) - 1

    def dat_tai_dinh_cu(self, text) -> None:
        """Tình trạng tái định cư: một trong TAI_DINH_CU hoặc nội dung gõ tay ("Không có" = để trống)."""
        t = ' '.join(str(text or '').split())
        self.pa.ho.tai_dinh_cu = '' if bo_dau(t) in ('', 'khong co') else t

    def dat_phai_di_chuyen(self, co: bool):
        self.pa.ho.phai_di_chuyen = bool(co)

    def dat_dt_nn_dang_dung(self, text):
        v = doc_so(text, 'DT đất nông nghiệp đang sử dụng')
        self.pa.ho.dt_nn_dang_dung = v if v > 0 else None

    def ty_le_thu_hoi_nn(self):
        from .nghiep_vu import dt_nn_thu_hoi
        dt = dt_nn_thu_hoi(self.pa)
        dung = self.pa.ho.dt_nn_dang_dung or dt          # chưa nhập: lấy DT đất nông nghiệp đã nhập ở mục 1
        return dt / dung if dung and dung > 0 else None

    # ---------------------------------------------- mục 1
    def nhom_dat(self, loai_dat: str) -> str:
        return self.bc.loai_dat.get((loai_dat or '').upper(), '')

    def them_thua(self, ma_thua) -> tuple:
        """Thêm dòng mục 1 cho một thửa: tự điền loại đất (nếu kiểm kê ghi một loại có trong danh mục), DT còn lại,
        vị trí và giá. Trả (chỉ số dòng, thông báo)."""
        t = self.bc.thua.get(ma_thua)
        if t is None or t['ma_ho'] != self.ma_ho:
            raise LoiNhap('Thửa không thuộc hộ đang lập.')
        con_lai = next((x[2] for x in self.thua_cua_ho() if x[0] == ma_thua), KHONG)
        ds_ld = [x for x in chuan_ma_loai_dat(t['loai_dat']).split('+') if x]
        # mã có trong danh mục trước; không có thì vẫn giữ mã kiểm kê ghi (đơn giá 0 / nhập tay - không mất loại đất)
        ld = next((x for x in ds_ld if x in self.bc.loai_dat), ds_ld[0] if ds_ld else '')
        d = DongDat(ma_thua=ma_thua, loai_dat=ld, nhom_dat=self.nhom_dat(ld), dien_tich=con_lai,
                    vi_tri=so_vi_tri(t['vi_tri']))
        tb = self._dien_gia_dat(d)
        if len(ds_ld) > 1:
            tb = (f'Kiểm kê ghi {t["loai_dat"]}: đã chọn {ld or "(chưa)"} cho dòng này; nếu thửa có nhiều loại đất, '
                  f'sửa diện tích rồi thêm dòng nữa cho loại còn lại. ' + tb).strip()
        self.pa.dat.append(d)
        return len(self.pa.dat) - 1, tb

    def _dien_gia_dat(self, d: DongDat) -> str:
        g, k, nguon = tra_gia_dat(self.con, self.bc, d.loai_dat, d.vi_tri)
        if g is None:
            return (f'Chưa có giá {d.loai_dat or ""} vị trí {d.vi_tri or "?"}: nhập giá theo bảng giá đất.'
                    + self._ap_he_so_k(d, self.bc.ten_dia_ban, d.vi_tri)).strip()
        d.gia_bang_gia, d.he_so_k = g, k
        return f'Giá {vn(g)} đ/m² lấy theo {nguon}.' + self._ap_he_so_k(d, self.bc.ten_dia_ban, d.vi_tri)

    def _ap_he_so_k(self, d: DongDat, dia_ban: str, vi_tri: str, tuyen_duong: str = '', tt=None) -> str:
        """Hệ số K theo bảng hệ số của máy (he_so_k.py - QĐ 03/2026/QĐ-UBND): có dòng khớp địa bàn / loại đất / vị trí / tuyến
        thì ghi hệ số + căn cứ vào Ghi chú; không khớp thì bỏ hệ số / căn cứ đã ghi trước đó (giữ hệ số của bảng giá dự án)."""
        from . import he_so_k as hk
        cu = re.search(r'Hệ số K theo [^;]*', d.ghi_chu or '')
        k, r = hk.tra(dia_ban, d.loai_dat, vi_tri, tuyen_duong, tt=tt)
        bo = re.sub(r'\s*;?\s*Hệ số K theo [^;]*', '', d.ghi_chu or '').strip(' ;')
        if k is None:
            if cu:
                d.ghi_chu = bo
                if d.he_so_k != 1 and not tra_gia_dat(self.con, self.bc, d.loai_dat, d.vi_tri)[1]:
                    d.he_so_k = D(1)
            return ''
        d.he_so_k = k
        cc = hk.can_cu()
        d.ghi_chu = (bo + '; ' if bo else '') + cc
        d.thanh_tien_excel = None
        return f' Hệ số K = {so_vn(k)} ({cc}).'

    def sua_dat(self, i: int, cot: str, text) -> str:
        if cot not in SUA_DUOC_DAT:
            raise LoiNhap('Ô này tự tính, không sửa được.')
        d = self.pa.dat[i]
        tb = ''
        if cot == 'thua':
            return self.doi_thua(i, text)
        if cot == 'loai_dat':
            ld = chuan_ma_loai_dat(text)
            if ld and any(x not in self.bc.loai_dat for x in ld.split('+')):
                raise LoiNhap(f'Loại đất "{ld}" không có trong danh mục loại đất (Thông tư 08/2024 hoặc bảng giá dự án).')
            d.loai_dat, d.nhom_dat = ld, self.nhom_dat(ld)
            tb = self._dien_gia_dat(d)
        elif cot == 'vi_tri':
            d.vi_tri = str(text or '').strip()
            tb = self._dien_gia_dat(d)
        elif cot == 'dien_tich':
            d.dien_tich = doc_so_luong(text, 'm²', 'Diện tích')
            d.cong_thuc = _cong_thuc(text)
        elif cot == 'gia_bang_gia':
            v = doc_so(text, 'Giá bảng giá')
            g = tra_gia_dat(self.con, self.bc, d.loai_dat, d.vi_tri)[0]
            if v != d.gia_bang_gia and g is not None and v != g and 'nhập tay' not in d.ghi_chu:
                tb = (f'Đơn giá đất nhập tay {vn(v)} đ/m² (bảng giá dự án {d.loai_dat} vị trí {d.vi_tri}: {vn(g)} đ/m²): '
                      'ghi căn cứ ở cột Ghi chú.')
                d.ghi_chu = ('Giá đất nhập tay' + (f'; {d.ghi_chu}' if d.ghi_chu else '')).strip()
            d.gia_bang_gia = v
        elif cot == 'he_so_k':
            v = doc_so(text, 'Hệ số K')
            d.he_so_k = v if v > 0 else D(1)
        elif cot == 'ty_le':
            d.ty_le = doc_ty_le(text)
        elif cot == 'ghi_chu':
            d.ghi_chu = str(text or '').strip()
        d.thanh_tien_excel = None
        return tb

    def doi_thua(self, i: int, ma_thua) -> str:
        """Gắn dòng mục 1 với thửa khác của hộ (mã thửa, hoặc chữ 'Thửa 394 tờ 35' như trên ô)."""
        d = self.pa.dat[i]
        ds = self.thua_cua_ho()
        if not isinstance(ma_thua, int):
            t = bo_dau(str(ma_thua or ''))
            ma_thua = next((mt for mt, mo_ta, _ in ds if bo_dau(self.ten_thua(mt)) == t or bo_dau(mo_ta).startswith(t)), None)
            if ma_thua is None:
                if t == bo_dau(self.ten_thua(d.ma_thua)):
                    return ''
                raise LoiNhap('Chọn một thửa của hộ trong danh sách (thêm thửa mới ở thẻ Thông tin hộ, thửa đất).')
        if ma_thua == d.ma_thua:
            return ''
        t = self.bc.thua.get(ma_thua)
        if t is None or t['ma_ho'] != self.ma_ho:
            raise LoiNhap('Thửa không thuộc hộ đang lập.')
        d.ma_thua = ma_thua
        ds_ld = [x.strip().upper() for x in str(t['loai_dat'] or '').replace(',', '+').split('+') if x.strip()]
        tb = ''
        if ds_ld and d.loai_dat not in ds_ld:
            ld = next((x for x in ds_ld if x in self.bc.loai_dat), '')
            if ld:
                d.loai_dat, d.nhom_dat = ld, self.nhom_dat(ld)
                tb = self._dien_gia_dat(d)
        if not d.dien_tich:
            d.dien_tich = next((x[2] for x in self.thua_cua_ho() if x[0] == ma_thua), KHONG)
        d.thanh_tien_excel = None
        return (f'Đã gắn dòng 1.{i + 1} với {self.ten_thua(ma_thua)}. ' + tb).strip()

    def ds_vi_tri_nq28(self, i: int) -> list:
        """Các vị trí tuyến đường theo bảng giá NQ 28/2025, giá theo loại đất của dòng: [(nhãn, dòng bảng giá, giá đồng/m²)].
        Đủ mọi địa bàn có trong bảng (dự án đi qua nhiều xã: thửa ở xã khác vẫn chọn được), địa bàn của dự án đứng đầu, nhãn
        ghi tên xã / phường. Loại đất không có cột giá: vẫn đủ danh sách, giá để trống (nhập tay)."""
        from . import gia_dat_nq28 as nq
        d = self.pa.dat[i]
        cot = nq.cot_cua_loai(d.loai_dat)
        kq = []
        for r in nq.theo_dia_ban(self.bc.ten_dia_ban):
            goc = (f'{nq.ten_ngan_xa(r["xa"])} · {r["vi_tri"]} · {r["ten_duong"]} '
                   f'(từ {r["diem_dau"]} đến {r["diem_cuoi"]})')
            if cot:
                g = nq.gia_dong(r, cot)
                kq.append((f'{goc} · {vn(g)} đ/m²', r, g))
            else:
                kq.append((f'{goc} · chưa có cột giá cho loại đất này', r, None))
        return kq

    def chon_vi_tri_nq28(self, i: int, r: dict) -> str:
        """Vị trí theo một dòng bảng giá NQ 28: ghi mô tả vị trí, điền giá đất theo loại đất của dòng (vẫn sửa tay được)."""
        from . import gia_dat_nq28 as nq
        d = self.pa.dat[i]
        cot = nq.cot_cua_loai(d.loai_dat)
        ten_vt = nq.TEN_VT.get(r['vi_tri'], r['vi_tri'])
        d.vi_tri = f'{ten_vt} {r["ten_duong"]} (đoạn từ {r["diem_dau"]} đến {r["diem_cuoi"]})' if r['vi_tri'] != 'MT' else \
            f'Mặt tiền {r["ten_duong"]} (đoạn từ {r["diem_dau"]} đến {r["diem_cuoi"]})'
        if not cot:
            d.thanh_tien_excel = None
            self._ap_he_so_k(d, r['xa'], r['vi_tri'], r['ten_duong'], r.get('tt'))
            return (f'Đã ghi vị trí theo {r["xa"]}. Loại đất "{d.loai_dat or "(chưa chọn)"}" không có cột giá trong bảng đang dùng: '
                    'nhập đơn giá bằng tay.')
        d.gia_bang_gia = D(nq.gia_dong(r, cot))
        d.thanh_tien_excel = None
        return f'Giá {vn(d.gia_bang_gia)} đ/m² theo {nq.can_cu(r, cot)}.' + self._ap_he_so_k(d, r['xa'], r['vi_tri'], r['ten_duong'], r.get('tt'))

    def o_dat(self, i: int) -> dict:
        d = self.pa.dat[i]
        return dict(thua=self.ten_thua(d.ma_thua), loai_dat=d.loai_dat, dien_tich=so_luong_vn(d.dien_tich, 1), vi_tri=d.vi_tri,
                    gia_bang_gia=vn(d.gia_bang_gia), he_so_k=so_vn(d.he_so_k), ty_le=hien_ty_le(d.ty_le),
                    thanh_tien=vn(thanh_tien_dong_dat(d, self.bc)), ghi_chu=d.ghi_chu, cong_thuc=d.cong_thuc)

    # ---------------------------------------------- mục 2, 3, 4
    def them_tu_danh_muc(self, muc: int, m: MucDanhMuc) -> tuple:
        """Thêm dòng theo một mục danh mục; khoản hỗ trợ được gợi ý SL / ĐG. Trả (chỉ số dòng, thông báo).
        Mục quy ước tương đương / đơn giá thẩm định (nguon 'quyuoc'): dòng mang tên thực tế, giá theo quy ước."""
        if m.nguon == 'quyuoc':
            i = self.them_hang_muc_khac(muc, m.ten)
            self.ap_gia_tuong_duong(muc, i, m)
            return i, ''
        d = DongKhoan(muc=muc, ma=m.ma, ten=m.ten, dvt=m.dvt, don_gia=m.don_gia or KHONG, so_luong=D(1) if muc == 4 else KHONG,
                      quy_cach=(m.can_cu if muc == 4 else ''), nguon_gia=NGUON_DM)
        tb = ''
        if muc == 4:
            if m.ma in MA_TDC:
                raise LoiNhap('Tái định cư không phải khoản tiền: chọn tình trạng ở ô "Tái định cư" (đủ điều kiện theo khoản… '
                              'Điều 111 / không đủ điều kiện / không có).')
            # mã CS9/CS10, CS7: cột Đơn giá của danh mục là hệ số, không phải tiền
            if m.ma in MA_HE_SO:
                d.don_gia = KHONG
            from . import chinh_sach as cs
            co_dong_them = bool(self.pa.dong_ho_tro('CS21', 'CS22', 'CS25', 'CS26'))
            self.pa.khoan[4].append(d)
            g = goi_y_khoan(self.pa, self.bc, m.ma)
            if g.so_luong is not None:
                d.so_luong = g.so_luong
            if g.don_gia is not None:
                d.don_gia = g.don_gia
            if g.dvt:
                d.dvt = g.dvt
            tb = g.thong_bao
            # tên chính sách theo câu chữ quy định, căn cứ ở Ghi chú, cách tính in thay ĐVT / SL / ĐG / tỷ lệ
            k = cs.loai(m.ma)
            moi = None
            if k == 'tn' and not co_dong_them:
                moi = cs.dong_thue_nha(m, self.bc, self.pa.nhan_khau, d.so_luong or D(6))
            elif k == 'od' and self.pa.nhan_khau:
                dm = cs.mac_dinh_on_dinh(self.bc, m.ten)
                moi = cs.dong_on_dinh(m, self.pa.nhan_khau, dm['gia_gao'], dm['kg'], dm['thang'], dm['ty_le'])
            if moi is not None:
                moi.quy_cach = m.can_cu
                self.pa.khoan[4][-1] = d = moi
            else:
                d.ten, d.ghi_chu = cs.ten_ngan(m.ten, m.ma), cs.can_cu_ghi_chu(m.can_cu)
        else:
            self.pa.khoan[muc].append(d)
            if m.don_gia is None:
                tb = 'Mục này chưa có đơn giá trong danh mục: nhập đơn giá và căn cứ.'
        return len(self.pa.khoan[muc]) - 1, tb

    def them_hang_muc_khac(self, muc: int, ten: str) -> int:
        """Hạng mục không có trong quy định: tên gõ tự do, đơn giá chọn tương đương hoặc nhập tay."""
        ten = ' '.join(str(ten or '').split())
        if not ten:
            raise LoiNhap('Nhập tên hoặc mô tả hạng mục.')
        self.pa.khoan[muc].append(DongKhoan(muc=muc, ten=ten, so_luong=D(1) if muc == 4 else KHONG, nguon_gia=NGUON_TAY))
        return len(self.pa.khoan[muc]) - 1

    def ap_gia_tuong_duong(self, muc: int, i: int, m: MucDanhMuc) -> None:
        """Áp đơn giá, ĐVT của mục tương đương; tên in ra vẫn là tên đã gõ."""
        if m.don_gia is None:
            raise LoiNhap(f'{m.ma} chưa có đơn giá trong danh mục, không áp giá tương đương được.')
        d = self.pa.khoan[muc][i]
        ma_td = m.ma
        if m.nguon == 'quyuoc':
            ten_td = m.phan_loai
            ma_td = ''
        else:
            ten_td = m.ten
        d.dvt, d.don_gia, d.nguon_gia, d.ma_tuong_duong = m.dvt, m.don_gia, NGUON_TD, ma_td
        if m.nguon == 'quyuoc' and bo_dau(ten_td).startswith('don gia tham dinh'):
            # đơn giá thẩm định giá được phê duyệt (tài sản đặc biệt): căn cứ là chứng thư / quyết định phê duyệt
            d.can_cu_gia = f'{ten_td}: {vn(m.don_gia)} đ/{m.dvt}' + (f'; {m.can_cu}' if m.can_cu else '')
        else:
            d.can_cu_gia = (f'Áp giá tương đương: {(ma_td + " - ") if ma_td else ""}{ten_td} ({vn(m.don_gia)} đ/{m.dvt})'
                            + (f'; {m.can_cu}' if m.can_cu else ''))
        d.thanh_tien_excel = None

    def sua_khoan(self, muc: int, i: int, cot: str, text) -> str:
        if cot not in SUA_DUOC_KHOAN:
            raise LoiNhap('Ô này không sửa trực tiếp được (mã và nguồn giá đổi bằng các nút chọn danh mục / giá tương đương).')
        d = self.pa.khoan[muc][i]
        tb = ''
        if cot == 'so_luong':
            d.so_luong = doc_so_luong(text, d.dvt)
            d.cong_thuc = _cong_thuc(text)
        elif cot == 'don_gia':
            v = doc_so(text, 'Đơn giá')
            m = self.dm.lay(d.ma_tuong_duong if d.nguon_gia == NGUON_TD else d.ma)
            if d.nguon_gia in (NGUON_DM, NGUON_TD) and m is not None and m.don_gia is not None \
                    and d.ma not in MA_HE_SO and muc != 4 and v != d.don_gia:
                # giá thực tế khác bộ đơn giá (thẩm định giá, báo giá…): dòng chuyển sang "nhập tay", ghi giá danh mục để rà soát
                d.ma_tuong_duong, d.ma, d.nguon_gia = m.ma, '', NGUON_TAY
                d.can_cu_gia = (f'Đơn giá nhập tay (đơn giá {m.ma}: {vn(m.don_gia)} đ/{m.dvt})' +
                                (f'; {d.can_cu_gia}' if d.can_cu_gia and not d.can_cu_gia.startswith('Áp giá') else ''))
                tb = f'Đơn giá nhập tay {vn(v)} đ (bộ đơn giá {m.ma}: {vn(m.don_gia)} đ): ghi căn cứ ở cột Căn cứ giá / Ghi chú.'
            d.don_gia = v
        elif cot == 'ty_le':
            d.ty_le = doc_ty_le(text)
        elif cot == 'ten':
            v = ' '.join(str(text or '').split())
            if not v:
                raise LoiNhap('Tên không được để trống.')
            m = self.dm.lay(d.ma) if d.ma else None
            if muc in (2, 3, MUC_VN) and d.nguon_gia == NGUON_DM and m is not None and m.don_gia is not None and v != d.ten:
                # tài sản thực tế không có trong đơn giá: giữ đơn giá của mục danh mục làm giá tương đương, tên in là tên mới
                d.ma, d.ma_tuong_duong, d.nguon_gia = '', m.ma, NGUON_TD
                d.can_cu_gia = (f'Áp giá tương đương: {m.ma} - {m.ten} ({vn(m.don_gia)} đ/{m.dvt})'
                                + (f'; {m.can_cu}' if m.can_cu else ''))
                tb = (f'Tài sản "{v}" không có trong đơn giá: giữ đơn giá {vn(d.don_gia)} đ/{d.dvt} của {m.ma} '
                      f'({m.ten}) làm giá tương đương.')
            d.ten = v
        else:
            setattr(d, cot, str(text or '').strip())
        if cot in ('so_luong', 'don_gia', 'ty_le'):
            d.thanh_tien_excel = None
        return tb

    def o_khoan(self, muc: int, i: int) -> dict:
        d = self.pa.khoan[muc][i]
        nguon = d.nguon_gia + (f': {d.ma_tuong_duong}' if d.nguon_gia != NGUON_DM and d.ma_tuong_duong else '')
        return dict(ma=d.ma, ten=d.ten, dvt=d.dvt, so_luong=so_luong_vn(d.so_luong, muc), don_gia=vn(d.don_gia), ty_le=hien_ty_le(d.ty_le),
                    thanh_tien=vn(thanh_tien_dong(d, self.bc)), nguon=nguon, quy_cach=d.quy_cach, can_cu_gia=d.can_cu_gia,
                    ghi_chu=d.ghi_chu, cach_tinh=d.cach_tinh, cong_thuc=d.cong_thuc)

    # ---------------------------------------------- chung
    def ds(self, muc: int) -> list:
        return self.pa.dat if muc == 1 else self.pa.khoan[muc]

    def xoa(self, muc: int, i: int) -> None:
        del self.ds(muc)[i]

    def them_nhieu_thua(self, ds_ma_thua=None, bo_qua_da_co: bool = True) -> int:
        """Thêm dòng mục 1 cho nhiều thửa của hộ (ds_ma_thua None = mọi thửa) theo thứ tự thửa; bo_qua_da_co: thửa đã có dòng mục 1
        thì không thêm lần nữa. Mỗi dòng như them_thua (loại đất, DT còn lại, vị trí, giá; giá 0 vẫn giữ loại đất). Trả số dòng thêm."""
        chon = None if ds_ma_thua is None else set(ds_ma_thua)
        da_co = {d.ma_thua for d in self.pa.dat}
        n = 0
        for mt, _, _ in self.thua_cua_ho():
            if (chon is not None and mt not in chon) or (bo_qua_da_co and mt in da_co):
                continue
            self.them_thua(mt)
            n += 1
        return n

    def xoa_nhieu_dat(self, ds_chi_so) -> int:
        """Xóa nhiều dòng mục 1 (chỉ số dòng; trùng / ngoài phạm vi bỏ qua). Trả số dòng đã xóa."""
        ds = sorted({int(i) for i in ds_chi_so if 0 <= int(i) < len(self.pa.dat)}, reverse=True)
        for i in ds:
            del self.pa.dat[i]
        return len(ds)

    def nhan_ban(self, muc: int, i: int) -> int:
        """Chép dòng mục 2-4 thành dòng mới ngay dưới (dùng tách phần ngoài mật độ / ngoài ranh thu hồi). Trả chỉ số dòng mới."""
        ds = self.pa.khoan[muc]
        ds.insert(i + 1, replace(ds[i], id=None, thanh_tien_excel=None))
        return i + 1

    def di_chuyen(self, muc: int, i: int, buoc: int) -> int:
        ds = self.ds(muc)
        j = i + buoc
        if not (0 <= i < len(ds) and 0 <= j < len(ds)):
            return i
        ds[i], ds[j] = ds[j], ds[i]
        return j

    def goi_y(self) -> tuple:
        return goi_y_ho_tro(self.pa, self.bc)

    def ap_dung_goi_y(self, de_xuat: list) -> None:
        from . import chinh_sach as cs
        for x in de_xuat:
            if x.viec in ('sửa', 'thay') and x.dong_cu is not None and x.dong_cu in self.pa.khoan[4]:
                d = x.dong_cu
                m = self.dm.lay(x.ma)
                if cs.loai(x.ma) == 'od' and d.cach_tinh and x.viec == 'sửa' and x.so_luong is not None:
                    cs.doi_nhan_khau_on_dinh(d, x.so_luong)
                    d.thanh_tien_excel = None
                    continue
                if m is not None and cs.loai(x.ma) == 'od' and x.viec == 'thay' and self.pa.nhan_khau:
                    # ổn định đời sống theo cách tính: dựng lại dòng theo khoản mới (số tháng, tỷ lệ theo khoản)
                    mdd = cs.mac_dinh_on_dinh(self.bc, m.ten)
                    moi = cs.dong_on_dinh(m, self.pa.nhan_khau, mdd['gia_gao'], mdd['kg'], mdd['thang'], mdd['ty_le'])
                    moi.quy_cach = m.can_cu
                    self.pa.khoan[4][self.pa.khoan[4].index(d)] = moi
                    continue
                if cs.loai(d.ma) == 'tn' and d.cach_tinh:
                    cs.tinh_lai_thue_nha(d, self.bc, self.pa.nhan_khau)
                    d.thanh_tien_excel = None
                    continue
                if x.viec == 'thay':
                    m = self.dm.lay(x.ma)
                    if m is not None:
                        d.ma, d.ten, d.dvt, d.quy_cach = m.ma, m.ten, m.dvt, m.can_cu
                if x.so_luong is not None:
                    d.so_luong = x.so_luong
                if x.don_gia is not None:
                    d.don_gia = x.don_gia
                d.thanh_tien_excel = None
                continue
            m = self.dm.lay(x.ma)
            if m is None:
                continue
            i, _ = self.them_tu_danh_muc(4, m)
            d = self.pa.khoan[4][i]
            if d.cach_tinh:
                continue                                # dòng dựng theo cách tính (ổn định đời sống, thuê nhà): giữ nguyên
            if x.so_luong is not None:
                d.so_luong = x.so_luong
            if x.don_gia is not None:
                d.don_gia = x.don_gia

    # ---------------------------------------------- lưu
    def loi_chan_luu(self) -> list:
        loi = []
        for k, d in enumerate(self.pa.dat, start=1):
            if not d.loai_dat:
                loi.append(f'Dòng 1.{k}: chưa chọn loại đất.')
            if d.dien_tich < 0:                          # = 0: không bồi thường đất (tài sản trên đất người khác) - cho lưu
                loi.append(f'Dòng 1.{k}: diện tích không được âm.')
        for muc in MUC_KHOAN:
            for k, d in enumerate(self.pa.khoan[muc], start=1):
                if not d.ten.strip():
                    loi.append(f'Dòng {so_muc(muc)}.{k}: chưa có tên.')
        return loi

    def luu(self, tu_dong: bool = False, mo_lai: bool = True) -> str:
        """Lưu phương án đang soạn (một giao dịch). Trả mô tả để hiện cho người dùng.
        tu_dong: phương án phần mềm tự lập (Dự án mới) - trạng thái TU_LAP, chỉ thành "Đã lập" khi người dùng mở ra soát và Lưu.
        mo_lai=False: không đọc lại phương án vừa lưu (bộ soạn bỏ đi ngay - tự lập hàng loạt)."""
        if self.khoa:
            raise LoiNhap(f'Phương án lần {self.lan} đã có Quyết định phê duyệt và đã được khóa bảo vệ. Không thể chỉnh sửa trực '
                          'tiếp (sửa sẽ làm sai quyết định đã ban hành).\nBổ sung tài sản / chính sách mới: bấm "+ Lập phương án bổ '
                          'sung". Cần điều chỉnh lần này: "Mở khóa sửa…".')
        loi = self.loi_chan_luu()
        if loi:
            raise LoiNhap('Chưa lưu được:\n' + '\n'.join('- ' + x for x in loi))
        con, pa = self.con, self.pa
        from . import lan_pa
        from .nghiep_vu import co_cot_lan, tinh_pa_lan
        co_lan = co_cot_lan(con)
        san = ket_qua_ho_san(con) if not (self.pa_khac.dat or any(self.pa_khac.khoan[m] for m in MUC_KHOAN)) else None
        cu = san[self.ma_ho][0].tong if san and self.ma_ho in san else tinh_pa_lan(self._pa_goc, self.pa_truoc, self.bc).tong
        moi = self.ket_qua
        co_dong = any(pa.dat) or any(pa.khoan[m] for m in MUC_KHOAN)
        luc = datetime.now()
        # người dùng Lưu: luôn là đã lập phương án - mục không có / bỏ trống tính 0 đồng (0.9.21; trước: không dòng nào = chưa lập)
        trang_thai = f'{DA_LAP_LUU} {luc:%d/%m/%Y %H:%M})' if not tu_dong else TU_LAP if co_dong else 'Chưa lập phương án'
        truoc = csdl.trang_thai_nho(con)
        with con:
            con.execute('''UPDATE ho SET nhan_khau = ?, phai_di_chuyen = ?, dt_nn_dang_dung = ?, trang_thai = ?, luu_luc = ?,
                           tai_dinh_cu = ? WHERE ma_ho = ?''',
                        (pa.ho.nhan_khau, int(pa.ho.phai_di_chuyen),
                         chuoi(pa.ho.dt_nn_dang_dung) if pa.ho.dt_nn_dang_dung is not None else None,
                         trang_thai, luc.isoformat(timespec='seconds'), pa.ho.tai_dinh_cu, self.ma_ho))
            # 1.0.05: chỉ xóa / ghi lại dòng của LẦN đang soạn - các lần khác (đã phê duyệt) giữ nguyên
            loc, ts = (' AND lan = ?', (self.ma_ho, self.lan)) if co_lan else ('', (self.ma_ho,))
            con.execute(f'DELETE FROM ct_dat WHERE ma_ho = ?{loc}', ts)
            con.execute(f'DELETE FROM ct_khoan WHERE ma_ho = ?{loc}', ts)
            cot_lan, gt_lan = (', lan', (self.lan,)) if co_lan else ('', ())
            for k, d in enumerate(pa.dat, start=1):
                con.execute(f'''INSERT INTO ct_dat (ma_ho, ma_thua, thu_tu, loai_dat, nhom_dat, dien_tich, vi_tri, gia_bang_gia,
                               he_so_k, ty_le, ghi_chu, thanh_tien_excel, cong_thuc{cot_lan})
                               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?{",?" if co_lan else ""})''',
                            (self.ma_ho, d.ma_thua, k, d.loai_dat, d.nhom_dat, chuoi(d.dien_tich), d.vi_tri, chuoi(d.gia_bang_gia),
                             chuoi(d.he_so_k), '' if d.ty_le is None else chuoi(d.ty_le), d.ghi_chu,
                             chuoi(d.thanh_tien_excel) if d.thanh_tien_excel is not None else None, d.cong_thuc, *gt_lan))
            for muc in MUC_KHOAN:
                for k, d in enumerate(pa.khoan[muc], start=1):
                    con.execute(f'''INSERT INTO ct_khoan (muc, ma_ho, thu_tu, ma, ten, dvt, so_luong, don_gia, ty_le, quy_cach, ghi_chu,
                                   nguon_gia, ma_tuong_duong, can_cu_gia, thanh_tien_excel, cach_tinh, cong_thuc{cot_lan})
                                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?{",?" if co_lan else ""})''',
                                (muc, self.ma_ho, k, d.ma, d.ten, d.dvt, chuoi(d.so_luong), chuoi(d.don_gia),
                                 '' if d.ty_le is None else chuoi(d.ty_le),
                                 d.quy_cach, d.ghi_chu, d.nguon_gia, d.ma_tuong_duong, d.can_cu_gia,
                                 chuoi(d.thanh_tien_excel) if d.thanh_tien_excel is not None else None, d.cach_tinh,
                                 d.cong_thuc, *gt_lan))
            # tự lập lần 1 (Dự án mới, hàng nghìn hộ): không ghi pa_lan - ds_lan trả lần 1 ảo; dòng tạo khi người dùng Lưu
            if (not tu_dong or self.lan > 1) and lan_pa.co_bang(con):
                lan_pa._dam_bao_dong(con, self.ma_ho, self.lan)   # ngày lập của lần = lần lưu gần nhất
                con.execute('UPDATE pa_lan SET ngay_lap = ? WHERE ma_ho = ? AND lan = ?',
                            (luc.strftime('%d/%m/%Y'), self.ma_ho, self.lan))
            csdl.ghi_nhat_ky(con, 'Lưu phương án hộ',
                             f'Hộ {self.ma_ho} {pa.ho.ho_ten}' + (f' (lần {self.lan})' if self.lan > 1 else '') +
                             f': tổng {vn(cu)} -> {vn(moi.tong)} đ; '
                             f'{len(pa.dat)} dòng đất, {sum(len(pa.khoan[m]) for m in MUC_KHOAN)} dòng khoản')
            if not tu_dong:                             # nhật ký kiểm toán: từng dòng / trường cũ -> mới (phần mềm tự lập: số liệu gốc)
                from .kiem_toan import ghi_thay_doi_pa
                ten_thua = {t['ma_thua']: f'{t["so_thua"]} tờ {t["so_to"]}' for t in self.bc.thua_cua(self.ma_ho)}
                ghi_thay_doi_pa(con, self.ma_ho, self._pa_goc, pa, ten_thua)
        csdl.giu_nho(con, ('BoiCanh', type(self.bc)), truoc)      # chỉ ghi ho / ct_dat / ct_khoan / nhật ký: bối cảnh không đổi
        if type(self.bc) is BoiCanh:
            giu_ket_qua_ho(con, [self.ma_ho], truoc)            # kết quả cả dự án: chỉ tính lại hộ vừa lưu
        if mo_lai:
            self.mo(self.ma_ho, self.lan)
        if self.lan > 1 or self.pa_khac.dat or any(self.pa_khac.khoan[m] for m in MUC_KHOAN):
            return (f'Đã lưu hộ {self.ma_ho} – {pa.ho.ho_ten}, lần {self.lan}: {vn(moi.tong)} đồng (cộng dồn mọi lần: '
                    f'{vn(self.ket_qua_cong_don.tong)} đồng).')
        return f'Đã lưu hộ {self.ma_ho} – {pa.ho.ho_ten}: tổng {vn(moi.tong)} đồng.'


# ---------------------------------------------------------------- dự án, rà soát giá
# 0.9.72 (người dùng 13/10/2026): bỏ Tên đầy đủ (luu_du_an ghi ten_day_du = ten), Số phương án, Ký hiệu số (theo đợt trình:
# dot_trinh.ky_hieu_so) khỏi hộp Thông tin dự án - cột CSDL giữ cho file cũ / nhập Excel
TRUONG_DU_AN = [('ten', 'Tên dự án'), ('chu_dau_tu', 'Chủ đầu tư'), ('co_quan_tham_dinh', 'Cơ quan thẩm định'),
                ('don_vi_cap_tren', 'Đơn vị cấp trên'),
                ('don_vi_tieu_de', 'Tên đơn vị trên tiêu đề bản in (dòng 2)'), ('don_vi_lap', 'Đơn vị lập phương án'),
                ('cap_dia_ban', 'Cấp địa bàn (Xã / Phường)'), ('ten_dia_ban', 'Tên xã, phường'), ('nam', 'Năm'),
                ('nguoi_lap', 'Người lập biểu'), ('nguoi_kiem_tra', 'Người kiểm tra'), ('chuc_vu_ky', 'Chức vụ người ký'),
                ('nguoi_ky', 'Người ký')]


def co_quan_tham_dinh_mac_dinh(cap: str, ten: str) -> str:
    """Cơ quan thẩm định theo cấp địa bàn (QĐ 18/2026): phường -> Phòng Kinh tế, Hạ tầng và Đô thị; xã -> Phòng Kinh tế."""
    cap, ten = ' '.join(str(cap or '').split()), ' '.join(str(ten or '').split())
    phong = 'Phòng Kinh tế' if bo_dau(cap) in ('xa', 'dac khu') else 'Phòng Kinh tế, Hạ tầng và Đô thị'
    return ' '.join(x for x in (phong, cap.lower(), ten) if x)


def doc_du_an(con) -> dict:
    r = con.execute('SELECT * FROM du_an WHERE id = 1').fetchone()
    co = set(r.keys())                                  # file chỉ xem phiên bản cũ (< v14): chưa có cột chu_dau_tu
    return {k: ('' if k not in co or r[k] is None else str(r[k])) for k, _ in TRUONG_DU_AN}


def luu_du_an(con, gia_tri: dict) -> None:
    gt = {k: ' '.join(str(gia_tri.get(k, '') or '').split()) for k, _ in TRUONG_DU_AN}
    if not gt['ten']:
        raise LoiNhap('Tên dự án không được để trống.')
    if gt['cap_dia_ban'] not in ('Xã', 'Phường', 'Thị trấn', 'Đặc khu'):
        raise LoiNhap('Cấp địa bàn: chọn Xã, Phường, Thị trấn hoặc Đặc khu.')
    nam = None
    if gt['nam']:
        if not gt['nam'].isdigit() or not 2000 <= int(gt['nam']) <= 2100:
            raise LoiNhap('Năm: nhập 4 chữ số, ví dụ 2026.')
        nam = int(gt['nam'])
    cu = doc_du_an(con)
    with con:
        gt_ghi = dict(gt, nam=nam)
        # một tên dự án (0.9.72): ten_day_du (cột cũ, nhận loại kinh phí / kiểm lỗi) đi theo ten, trừ khi nơi gọi đưa riêng
        ten_day_du = ' '.join(str(gia_tri.get('ten_day_du') or '').split()) or gt['ten']
        con.execute(f'''UPDATE du_an SET {', '.join(k + ' = ?' for k, _ in TRUONG_DU_AN)}, ten_day_du = ? WHERE id = 1''',
                    [gt_ghi[k] for k, _ in TRUONG_DU_AN] + [ten_day_du])
        doi = [f'{ten}: "{cu[k]}" -> "{gt[k]}"' for k, ten in TRUONG_DU_AN if cu[k] != (gt[k] if k != 'nam' else (str(nam) if nam else ''))]
        csdl.ghi_nhat_ky(con, 'Sửa thông tin dự án', '; '.join(doi))


# ---------------------------------------------------------------- kinh phí bảo đảm tổ chức thực hiện bồi thường
# QĐ 08/2025/QĐ-UBND ngày 10/02/2025 của UBND tỉnh Đồng Nai (hiệu lực 21/02/2025): dự án, tiểu dự án hạ tầng theo tuyến không quá
# 3,5%; dự án còn lại (cụm, vùng, khu...) không quá 2,5% tổng kinh phí bồi thường, hỗ trợ, tái định cư. Lưu ở cai_dat của dự án:
# LOAI_KINH_PHI ('' = tự nhận theo tên dự án / 'tuyen' / 'khac'), TL_KINH_PHI ('' = mức tối đa của loại).
# 0.9.85: tên loại, mức tối đa, căn cứ lấy từ hồ sơ địa phương (pabt_profile.json mục kinh_phi_to_chuc / can_cu_phap_ly)
CAN_CU_KINH_PHI = ''
LOAI_KINH_PHI: dict = {}


def _ap_ho_so_kinh_phi(hs: dict) -> None:
    global CAN_CU_KINH_PHI, LOAI_KINH_PHI
    from . import dia_phuong
    CAN_CU_KINH_PHI = hs['can_cu_phap_ly']['kinh_phi_to_chuc']
    LOAI_KINH_PHI = dia_phuong.ty_le_kinh_phi()


def _dang_ky_ho_so() -> None:
    from . import dia_phuong
    dia_phuong.dang_ky(_ap_ho_so_kinh_phi)


_dang_ky_ho_so()
_RE_CUM_VUNG = re.compile(r'^(?:\S+\s+){0,2}?(khu|cum|vung)\b')        # "Xây dựng khu…", "Dự án cụm…"
_RE_TUYEN = re.compile(r'\b(duong|tuyen|kenh|muong|cao toc|quoc lo|tinh lo|huong lo|duong day|duong ong|truc)\b')


def loai_kinh_phi_tu_ten(ten: str) -> str:
    """'tuyen' / 'khac' theo tên dự án: "Khu / Cụm / Vùng …" trong 3 từ đầu -> khác (kể cả "Khu tái định cư đường …");
    có đường, tuyến, kênh, mương, cao tốc, quốc lộ, đường dây, đường ống… -> theo tuyến; còn lại -> khác."""
    t = bo_dau(ten or '')
    if _RE_CUM_VUNG.search(t):
        return 'khac'
    return 'tuyen' if _RE_TUYEN.search(t) else 'khac'


def kinh_phi_to_chuc(con) -> tuple:
    """(loại, tỷ lệ % Decimal, tự nhận theo tên?) của kinh phí tổ chức thực hiện bồi thường cho dự án đang mở."""
    loai = csdl.doc_cai_dat(con, 'LOAI_KINH_PHI', '')
    tu_nhan = loai not in LOAI_KINH_PHI
    if tu_nhan:
        da = con.execute('SELECT ten, ten_day_du FROM du_an WHERE id = 1').fetchone()
        loai = loai_kinh_phi_tu_ten(' '.join(str(x or '') for x in da) if da else '')
    tl = csdl.doc_cai_dat(con, 'TL_KINH_PHI', '')
    try:
        tl = D(tl) if tl else LOAI_KINH_PHI[loai][1]
    except Exception:
        tl = LOAI_KINH_PHI[loai][1]
    return loai, tl, tu_nhan


def luu_kinh_phi_to_chuc(con, loai: str, ty_le: str = '') -> None:
    """loai '' (tự nhận theo tên) / 'tuyen' / 'khac'; ty_le '' = mức tối đa của loại, không được vượt mức tối đa."""
    if loai and loai not in LOAI_KINH_PHI:
        raise LoiNhap('Loại dự án (kinh phí tổ chức thực hiện) không hợp lệ.')
    tl = ''
    if str(ty_le or '').strip():
        so = doc_so(ty_le, 'Tỷ lệ kinh phí tổ chức thực hiện')
        da = con.execute('SELECT ten, ten_day_du FROM du_an WHERE id = 1').fetchone()
        that = loai or loai_kinh_phi_tu_ten(' '.join(str(x or '') for x in da) if da else '')
        toi_da = LOAI_KINH_PHI[that][1]
        if not 0 < so <= toi_da:
            raise LoiNhap(f'Tỷ lệ kinh phí tổ chức thực hiện: từ trên 0 đến {so_vn(toi_da)}% '
                          f'({LOAI_KINH_PHI[that][0]} - {CAN_CU_KINH_PHI}).')
        tl = chuoi(so)
    cu = (csdl.doc_cai_dat(con, 'LOAI_KINH_PHI', ''), csdl.doc_cai_dat(con, 'TL_KINH_PHI', ''))
    if cu == (loai, tl):
        return
    with con:
        csdl.ghi_cai_dat(con, 'LOAI_KINH_PHI', loai)
        csdl.ghi_cai_dat(con, 'TL_KINH_PHI', tl)
        csdl.ghi_nhat_ky(con, 'Kinh phí tổ chức thực hiện', f'loại "{loai or "tự nhận"}", tỷ lệ "{tl or "mức tối đa"}"')


def ra_soat_gia(con, dm: DanhMuc | None = None) -> list:
    """Các dòng mục 2-4 cần rà soát trước khi trình: áp giá tương đương, nhập tay, hoặc đơn giá khác danh mục.
    Mỗi phần tử: dict(ma_ho, ho_ten, stt, ten, dvt, don_gia, nguon, ma_tuong_duong, can_cu_gia, ghi_chu_ra_soat)."""
    dm = dm or DanhMuc(con)
    kq = []
    ten_ho = {r['ma_ho']: r['ho_ten'] for r in con.execute('SELECT ma_ho, ho_ten FROM ho')}
    for muc in MUC_KHOAN:
        dem = {}
        for r in con.execute('SELECT * FROM ct_khoan WHERE muc = ? ORDER BY ma_ho, thu_tu, id', (muc,)):
            dem[r['ma_ho']] = dem.get(r['ma_ho'], 0) + 1
            stt = f'{so_muc(muc)}.{dem[r["ma_ho"]]}'
            nguon = r['nguon_gia'] or NGUON_DM
            note = ''
            if nguon == NGUON_DM:
                m = dm.lay(r['ma']) if r['ma'] else None
                if m is None:
                    note = 'Mã không có trong danh mục hiện hành'
                elif m.don_gia is not None and muc != 4 and D(r['don_gia']) != m.don_gia:
                    note = f'Đơn giá khác danh mục ({vn(m.don_gia)} đ)'
                if not note:
                    continue
            else:
                note = 'Áp giá tương đương' if nguon == NGUON_TD else 'Đơn giá nhập tay'
                if not (r['can_cu_gia'] or '').strip():
                    note += ' – chưa ghi căn cứ'
            kq.append(dict(ma_ho=r['ma_ho'], ho_ten=ten_ho.get(r['ma_ho'], ''), stt=stt, ten=r['ten'], dvt=r['dvt'],
                           don_gia=D(r['don_gia']), nguon=nguon, ma_tuong_duong=r['ma_tuong_duong'],
                           can_cu_gia=r['can_cu_gia'], ghi_chu_ra_soat=note))
    kq.sort(key=lambda x: (x['ma_ho'], x['stt']))
    return kq


__all__ = ['BoSoan', 'DanhMuc', 'MucDanhMuc', 'LoiNhap', 'NHOM_TIM', 'COT_DAT', 'COT_KHOAN', 'MA_ON_DINH',
           'tra_gia_dat', 'doc_so', 'doc_ty_le', 'luu_du_an', 'doc_du_an', 'ra_soat_gia', 'TRUONG_DU_AN', 'de_xuat_dao_tao_pa']

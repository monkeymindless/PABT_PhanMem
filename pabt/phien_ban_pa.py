"""Đa phiên bản phương án của một hộ theo quy trình niêm yết: V0 -> V1 -> V2.n -> V3 (1.0.63, người dùng 05/11/2026). Không Qt.

V0  bản đang lập = chính các dòng ct_dat / ct_khoan hiện hành (không lưu thêm).
V1  dự thảo niêm yết: ảnh chụp từ V0 lúc in / xuất niêm yết, KHÓA: in lại không ghi đè. Người dùng tự mở khóa được để sửa (dat_khoa, 05/11/2026), bản đã chốt giữ riêng ở V1.goc, trả về được.
V2.n  dự thảo sau ý kiến / đối thoại: nhân bản từ V1 (hoặc V2 khác), sửa được, không đụng V1.
V3  chính thức trình thẩm định, phê duyệt: lấy nguyên từ V1 / V2.n hoặc ghép từng nhóm. Đặt V3 thì GHI LUÔN vào dòng hiện hành để danh sách hộ,
    bảng tổng hợp, quyết định, chi trả (đều đọc ct_*) khớp số trình; V1, V2.n vẫn nguyên.

Khác `lan_pa`: lần phương án là các đợt PHÁP LÝ (gốc, bổ sung, điều chỉnh sau phê duyệt), cộng dồn tiền; phiên bản là các BẢN THẢO của MỘT lần trước
phê duyệt, không cộng dồn. Ảnh chụp thuộc lần đang mở của hộ (cột lan).

Ý nghiệp vụ từ pabt_version_and_valuation_engine.py của người dùng; viết lại vì bản đó tính tiền float + round() (làm tròn kiểu ngân hàng) và amount không
qua nghiep_vu nên lệch số bản in. Ở đây: số lưu chuỗi Decimal (tien.chuoi), tiền tính bằng nghiep_vu (ROUND Excel, làm tròn nghìn của dự án).
Giá dân đề xuất KHÔNG tự ghi vào dòng nào của V2 (bản engine ghi vào dòng đầu tiên): chỉ ghi ở Ghi chú, người lập sửa đúng dòng.

Bảng `pa_phien_ban`, `ho_uuid` thêm bằng csdl.MO_RONG: file cũ tự có khi mở để ghi, file mở chỉ xem chưa có bảng thì coi như chưa có phiên bản."""
from __future__ import annotations

import json
import re
import sqlite3
import uuid
from dataclasses import fields
from datetime import datetime
from decimal import Decimal

from . import csdl
from .lap_pa import LoiNhap, kiem_ho_nhan_viec, kiem_quyen
from .nghiep_vu import (MUC_KHOAN, MUC_VN, BoiCanh, DongDat, DongKhoan, PhuongAn, doc_phuong_an, thanh_tien_dong, thanh_tien_dong_dat,
                        tinh_pa_lan)
from .tien import D, KHONG, chuoi

V0, V1, V3 = 'V0', 'V1', 'V3'
V1_GOC = 'V1.goc'             # bản V1 lúc mới chốt, tạo khi mở khóa lần đầu; không hiện trong ds_phien_ban
LOAI = {V1: 'niem_yet', V3: 'trinh_duyet'}
TEN_NGAN = {V0: 'V0: Bản nháp đang lập', V1: 'V1: PA Dự thảo Niêm yết (đã khóa)', V3: 'V3: PA Chính thức Trình thẩm định, phê duyệt'}
# nhóm hạng mục để ghép V3; thưởng (mục 5) luôn tự tính từ tổng, không ghép
DAT, NHA, CAY, HO_TRO = 'DAT', 'NHA_VKT', 'CAY_TRONG', 'CHINH_SACH_HO_TRO'
NHOM = ((DAT, '1. Bồi thường về đất'), (NHA, '2. Nhà, vật kiến trúc'), (CAY, '3. Cây trồng, vật nuôi'), (HO_TRO, '4. Chính sách hỗ trợ'))
TEN_NHOM = dict(NHOM)
TEN_THUONG = '5. Thưởng (tự tính)'
MUC_CUA_NHOM = {NHA: (2,), CAY: (3, MUC_VN), HO_TRO: (4,)}
TINH_LAI = 'TINH_LAI'         # nguồn của nhóm hỗ trợ: giữ các khoản rồi tính lại theo số liệu đã ghép
_RE_V2 = re.compile(r'^V2\.(\d+)$')
_THU_TU = {V1: (1, 0), V3: (3, 0)}

_SO_DAT = ('dien_tich', 'gia_bang_gia', 'he_so_k', 'ty_le', 'thanh_tien_excel')
_SO_KHOAN = ('so_luong', 'don_gia', 'ty_le', 'thanh_tien_excel')


def co_bang(con) -> bool:
    return bool(con.execute("SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'pa_phien_ban'").fetchone())


# ---------------------------------------------------------------- chuyển PhuongAn <-> JSON
def _dong_ra(d) -> dict:
    kq = {}
    for f in fields(d):
        if f.name == 'id':
            continue
        v = getattr(d, f.name)
        kq[f.name] = chuoi(v) if isinstance(v, Decimal) else v
    return kq


def _dong_vao(lop, r: dict, truong_so: tuple):
    co = {f.name for f in fields(lop)}
    tt = {k: v for k, v in r.items() if k in co}                         # bản sau thêm trường: ảnh chụp cũ dùng mặc định, bản trước bỏ qua
    for k in truong_so:
        if k in tt:
            tt[k] = None if tt[k] in (None, '') else D(tt[k])
    return lop(**tt)


def pa_ra_json(pa: PhuongAn) -> str:
    h = pa.ho
    return json.dumps({'ho': {'nhan_khau': h.nhan_khau, 'phai_di_chuyen': bool(h.phai_di_chuyen),
                              'dt_nn_dang_dung': None if h.dt_nn_dang_dung is None else chuoi(h.dt_nn_dang_dung), 'tai_dinh_cu': h.tai_dinh_cu},
                       'dat': [_dong_ra(d) for d in pa.dat],
                       'khoan': {str(m): [_dong_ra(d) for d in ds] for m, ds in pa.khoan.items()}}, ensure_ascii=False)


def pa_tu_json(con, ma_ho: int, chu: str) -> PhuongAn:
    """PhuongAn từ ảnh chụp (thông tin hộ mới nhất, số nhân khẩu / di chuyển / TĐC theo ảnh chụp)."""
    from dataclasses import replace
    d = json.loads(chu)
    goc = doc_phuong_an(con, ma_ho, den_lan=0)
    h = d.get('ho') or {}
    ho = replace(goc.ho, nhan_khau=h.get('nhan_khau'), phai_di_chuyen=bool(h.get('phai_di_chuyen')),
                 dt_nn_dang_dung=None if h.get('dt_nn_dang_dung') in (None, '') else D(h['dt_nn_dang_dung']), tai_dinh_cu=h.get('tai_dinh_cu') or '')
    pa = PhuongAn(ho=ho)
    pa.dat = [_dong_vao(DongDat, r, _SO_DAT) for r in d.get('dat', ())]
    for m, ds in (d.get('khoan') or {}).items():
        pa.khoan[int(m)] = [_dong_vao(DongKhoan, r, _SO_KHOAN) for r in ds]
    return pa


def dat_tu_json(chu: str) -> list:
    """Các dòng đất của ảnh chụp, không đọc thông tin hộ (danh sách dòng đất cả dự án)."""
    return [_dong_vao(DongDat, r, _SO_DAT) for r in json.loads(chu).get('dat', ())]


# ---------------------------------------------------------------- đọc
def _khoa_sap(ma: str) -> tuple:
    m = _RE_V2.match(ma)
    return (2, int(m.group(1))) if m else _THU_TU.get(ma, (9, 0))


def ds_phien_ban(con, ma_ho: int) -> list:
    """Các phiên bản đã có của hộ, theo thứ tự V1, V2.1, V2.2…, V3 (dict: ma, loai, nhan, tao_luc, nguoi_tao, khoa, cha, ghi_chu, nguon_nhom, lan). Chưa có V0."""
    if not co_bang(con):
        return []
    kq = [dict(r) for r in con.execute('''SELECT ma, lan, loai, nhan, tao_luc, nguoi_tao, khoa, cha, ghi_chu, nguon_nhom FROM pa_phien_ban
                                          WHERE ma_ho = ? AND ma <> ?''', (ma_ho, V1_GOC))]
    return sorted(kq, key=lambda x: _khoa_sap(x['ma']))


def lay(con, ma_ho: int, ma: str) -> dict | None:
    if not co_bang(con):
        return None
    r = con.execute('SELECT * FROM pa_phien_ban WHERE ma_ho = ? AND ma = ?', (ma_ho, ma)).fetchone()
    return dict(r) if r is not None else None


def doc_pa(con, ma_ho: int, ma: str) -> PhuongAn:
    """PhuongAn của phiên bản; V0 = dòng hiện hành của lần đang mở."""
    if ma == V0:
        return doc_phuong_an(con, ma_ho, lan=_lan_mo(con, ma_ho))
    r = lay(con, ma_ho, ma)
    if r is None:
        raise LoiNhap(f'Hộ {ma_ho} chưa có phiên bản {ma}.')
    return pa_tu_json(con, ma_ho, r['du_lieu'])


def _lan_mo(con, ma_ho: int) -> int:
    from . import lan_pa
    return lan_pa.lan_mac_dinh(con, ma_ho) if lan_pa.co_bang(con) else 1


def _pa_truoc(con, ma_ho: int, lan: int, pa: PhuongAn) -> PhuongAn:
    return PhuongAn(ho=pa.ho) if int(lan or 1) <= 1 else doc_phuong_an(con, ma_ho, den_lan=int(lan) - 1)


def ket_qua(con, ma_ho: int, ma: str, bc=None):
    """KetQuaHo của phiên bản (cùng phép tính với phương án thật: làm tròn, thưởng)."""
    bc = bc or BoiCanh.tu(con)
    r = lay(con, ma_ho, ma) if ma != V0 else None
    lan = r['lan'] if r else _lan_mo(con, ma_ho)
    pa = doc_pa(con, ma_ho, ma)
    return tinh_pa_lan(pa, _pa_truoc(con, ma_ho, lan, pa), bc)


def tong(con, ma_ho: int, ma: str, bc=None) -> Decimal:
    return ket_qua(con, ma_ho, ma, bc).tong


def v2_moi_nhat(con, ma_ho: int) -> str:
    ds = [x['ma'] for x in ds_phien_ban(con, ma_ho) if _RE_V2.match(x['ma'])]
    return ds[-1] if ds else ''


# ---------------------------------------------------------------- ghi
def _nguoi() -> str:
    return getattr(csdl, 'NGUOI_DUNG', '') or ''


def _ghi(con, ma_ho: int, ma: str, lan: int, pa: PhuongAn, loai: str, nhan: str, khoa: int, cha: str, ghi_chu: str, nguon_nhom: dict | None = None) -> None:
    if not co_bang(con):                                # file vừa tạo trong phiên này: MO_RONG mới chạy khi mở file có hộ
        csdl._tao_bang_phien_ban(con)
    con.execute('''INSERT INTO pa_phien_ban (ma_ho, ma, lan, loai, nhan, tao_luc, nguoi_tao, khoa, cha, ghi_chu, nguon_nhom, du_lieu)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
                   ON CONFLICT(ma_ho, ma) DO UPDATE SET lan = excluded.lan, loai = excluded.loai, nhan = excluded.nhan, tao_luc = excluded.tao_luc,
                       nguoi_tao = excluded.nguoi_tao, cha = excluded.cha, ghi_chu = excluded.ghi_chu, nguon_nhom = excluded.nguon_nhom,
                       du_lieu = excluded.du_lieu''',
                (ma_ho, ma, lan, loai, nhan, datetime.now().strftime('%d/%m/%Y %H:%M:%S'), _nguoi(), khoa, cha, ghi_chu,
                 json.dumps(nguon_nhom or {}, ensure_ascii=False), pa_ra_json(pa)))


def khoa_v1(con, ma_ho: int, ten_dot: str = '') -> bool:
    """Chốt V1 từ số liệu hiện hành; đã có V1 thì GIỮ NGUYÊN (không bao giờ ghi đè). True: vừa tạo. Tạo kèm V3 theo V1 (ảnh chụp, không đổi số hiện hành)."""
    if lay(con, ma_ho, V1) is not None:
        return False
    kiem_ho_nhan_viec(con, ma_ho)
    kiem_quyen(con, 'niem_yet', 'chốt phương án niêm yết')
    lan = _lan_mo(con, ma_ho)
    pa = doc_phuong_an(con, ma_ho, lan=lan)
    with csdl.giao_dich(con):
        _ghi(con, ma_ho, V1, lan, pa, LOAI[V1], f'V1 - PA Dự thảo Niêm yết{" (" + ten_dot + ")" if ten_dot else ""}', 1, V0,
             f'Chốt niêm yết công khai{" " + ten_dot if ten_dot else ""}: giữ nguyên làm chứng cứ.')
        if lay(con, ma_ho, V3) is None:
            _ghi(con, ma_ho, V3, lan, pa, LOAI[V3], 'V3 - PA Chính thức Trình duyệt (theo V1)', 0, V1, 'Mặc định theo V1.', {k: V1 for k, _ in NHOM})
        csdl.ghi_nhat_ky(con, 'Chốt phương án niêm yết (V1)', f'Hộ {ma_ho}')
    return True


def khoa_v1_nhieu(con, ds_ma_ho, ten_dot: str = '') -> int:
    """Chốt V1 cho các hộ (bấm In PA dự thảo / Xuất bảng niêm yết). File mở chỉ xem: không ghi, trả 0 (in theo dữ liệu đang có)."""
    n = 0
    try:
        with csdl.giao_dich(con):
            for ma in ds_ma_ho:
                n += 1 if khoa_v1(con, ma, ten_dot) else 0
    except sqlite3.OperationalError:
        return 0
    return n


def tao_v2(con, ma_ho: int, ghi_chu: str = '', nguon: str = V1) -> str:
    """Nhánh dự thảo mới (V2.1, V2.2…) nhân bản từ nguồn, không đụng nguồn. Chưa có V1: chốt V1 từ số hiện hành trước. Trả mã nhánh."""
    kiem_ho_nhan_viec(con, ma_ho)
    kiem_quyen(con, 'sua_gia', 'tạo phương án dự thảo sau ý kiến')
    with csdl.giao_dich(con):
        khoa_v1(con, ma_ho)
        if nguon != V1 and lay(con, ma_ho, nguon) is None:
            raise LoiNhap(f'Không có phiên bản nguồn {nguon}.')
        goc = lay(con, ma_ho, nguon)
        cac = [int(m.group(1)) for x in ds_phien_ban(con, ma_ho) for m in [_RE_V2.match(x['ma'])] if m]
        so = max(cac, default=0) + 1
        ma = f'V2.{so}'
        _ghi(con, ma_ho, ma, goc['lan'], pa_tu_json(con, ma_ho, goc['du_lieu']), f'doi_thoai_{so}', f'{ma} - PA Dự thảo sau Ý kiến / Đối thoại (lần {so})', 0, nguon,
             ghi_chu or f'Nhân bản từ {nguon}.')
        csdl.ghi_nhat_ky(con, f'Tạo phương án dự thảo {ma}', f'Hộ {ma_ho}, từ {nguon}: {ghi_chu}'[:300])
    return ma


def tao_v2_tu_y_kien(con, ma_ho: int, noi_dung: str) -> str:
    """Hộ có ý kiến khác phương án: tạo nhánh V2 sẵn để người lập sửa. Cùng nội dung đã có nhánh (đọc lại file): không tạo thêm. Trả mã nhánh, '' nếu đã có."""
    ghi_chu = f'Ý kiến của hộ: {noi_dung}'.strip()
    if any(x['ghi_chu'] == ghi_chu for x in ds_phien_ban(con, ma_ho) if _RE_V2.match(x['ma'])):
        return ''
    return tao_v2(con, ma_ho, ghi_chu)


def sua(con, ma_ho: int, ma: str, pa: PhuongAn, ghi_chu: str | None = None) -> None:
    """Ghi nội dung đã sửa của phiên bản đang mở khóa; đang khóa: báo lỗi. V3: ghi luôn vào số hiện hành."""
    r = lay(con, ma_ho, ma)
    if r is None:
        raise LoiNhap(f'Hộ {ma_ho} chưa có phiên bản {ma}.')
    if r['khoa']:
        raise LoiNhap(f'{ma} đang khóa: bấm Mở khóa để sửa' + (', hoặc tạo nhánh V2 mới để giữ nguyên V1.' if ma == V1 else '.'))
    kiem_ho_nhan_viec(con, ma_ho)
    kiem_quyen(con, 'sua_gia', f'sửa phương án {ma}')
    with csdl.giao_dich(con):
        con.execute('UPDATE pa_phien_ban SET du_lieu = ?, ghi_chu = ? WHERE ma_ho = ? AND ma = ?',
                    (pa_ra_json(pa), r['ghi_chu'] if ghi_chu is None else ghi_chu, ma_ho, ma))
        csdl.ghi_nhat_ky(con, f'Sửa phương án {ma}', f'Hộ {ma_ho}')
        if ma == V3:
            _ap_hien_hanh(con, ma_ho, pa, r['lan'])


def dat_khoa(con, ma_ho: int, ma: str, khoa: bool, ly_do: str = '') -> None:
    """Bật / tắt khóa một phiên bản. Mở khóa V1 lần đầu: giữ bản đã chốt ở V1.goc để trả về được (tra_v1_ve_goc). Khóa của lần đã phê duyệt là việc khác: lan_pa.mo_khoa_lan."""
    r = lay(con, ma_ho, ma)
    if r is None:
        raise LoiNhap(f'Hộ {ma_ho} chưa có phiên bản {ma}.')
    if bool(r['khoa']) == bool(khoa):
        return
    kiem_ho_nhan_viec(con, ma_ho)
    kiem_quyen(con, 'sua_gia', f'{"khóa" if khoa else "mở khóa"} phương án {ma}')
    with csdl.giao_dich(con):
        if not khoa and ma == V1 and lay(con, ma_ho, V1_GOC) is None:
            con.execute('''INSERT INTO pa_phien_ban (ma_ho, ma, lan, loai, nhan, tao_luc, nguoi_tao, khoa, cha, ghi_chu, nguon_nhom, du_lieu)
                           SELECT ma_ho, ?, lan, loai, nhan, tao_luc, nguoi_tao, 1, cha, ghi_chu, nguon_nhom, du_lieu FROM pa_phien_ban WHERE ma_ho = ? AND ma = ?''', (V1_GOC, ma_ho, V1))
        con.execute('UPDATE pa_phien_ban SET khoa = ? WHERE ma_ho = ? AND ma = ?', (1 if khoa else 0, ma_ho, ma))
        csdl.ghi_nhat_ky(con, f'{"Khóa" if khoa else "Mở khóa"} phương án {ma}', f'Hộ {ma_ho}. {ly_do}'.strip()[:300])


def v1_da_sua(con, ma_ho: int) -> bool:
    """V1 đã khác bản lúc chốt (sau khi mở khóa, sửa)."""
    g, r = lay(con, ma_ho, V1_GOC), lay(con, ma_ho, V1)
    return bool(g and r and g['du_lieu'] != r['du_lieu'])


def tra_v1_ve_goc(con, ma_ho: int) -> None:
    """V1 về đúng bản lúc chốt và khóa lại. Không có bản giữ riêng (chưa mở khóa lần nào): không làm gì."""
    g = lay(con, ma_ho, V1_GOC)
    if g is None:
        return
    kiem_ho_nhan_viec(con, ma_ho)
    kiem_quyen(con, 'sua_gia', 'trả V1 về bản đã chốt')
    with csdl.giao_dich(con):
        con.execute('UPDATE pa_phien_ban SET du_lieu = ?, khoa = 1 WHERE ma_ho = ? AND ma = ?', (g['du_lieu'], ma_ho, V1))
        csdl.ghi_nhat_ky(con, 'Trả V1 về bản đã chốt', f'Hộ {ma_ho}')


def _kiem_v3_mo(con, ma_ho: int) -> None:
    r = lay(con, ma_ho, V3)
    if r is not None and r['khoa']:
        raise LoiNhap('V3 đang khóa: bấm Mở khóa rồi chốt lại.')


def _ap_hien_hanh(con, ma_ho: int, pa: PhuongAn, lan: int) -> None:
    """Ghi nội dung V3 vào dòng hiện hành qua BoSoan (khóa lần đã duyệt, phân quyền, nhật ký kiểm toán như mọi lần lưu)."""
    from .lap_pa import BoSoan
    bo = BoSoan(con, ma_ho, lan=lan)
    bo.pa.dat = list(pa.dat)
    bo.pa.khoan = {m: list(pa.khoan.get(m, ())) for m in MUC_KHOAN}
    bo.pa.ho.nhan_khau, bo.pa.ho.phai_di_chuyen = pa.ho.nhan_khau, pa.ho.phai_di_chuyen
    bo.pa.ho.dt_nn_dang_dung, bo.pa.ho.tai_dinh_cu = pa.ho.dt_nn_dang_dung, pa.ho.tai_dinh_cu
    if bo.co_thay_doi:
        bo.luu(mo_lai=False)


def dat_v3(con, ma_ho: int, nguon: str = V1, ly_do: str = '') -> None:
    """Khôi phục / chốt một chạm: V3 lấy nguyên từ V1 hoặc V2.n, không phải nhập lại. V1, V2.n giữ nguyên; số hiện hành theo V3."""
    goc = lay(con, ma_ho, nguon)
    if goc is None:
        raise LoiNhap(f'Hộ {ma_ho} không có phiên bản {nguon}.')
    kiem_ho_nhan_viec(con, ma_ho)
    kiem_quyen(con, 'sua_gia', 'chốt phương án trình duyệt')
    _kiem_v3_mo(con, ma_ho)
    pa = pa_tu_json(con, ma_ho, goc['du_lieu'])
    with csdl.giao_dich(con):
        _ghi(con, ma_ho, V3, goc['lan'], pa, LOAI[V3], f'V3 - PA Chính thức Trình duyệt (theo {nguon})', 0, nguon,
             ly_do or f'Trình theo {nguon}.', {k: nguon for k, _ in NHOM})
        csdl.ghi_nhat_ky(con, 'Chốt phương án trình duyệt (V3)', f'Hộ {ma_ho}: theo {nguon}. {ly_do}'[:300])
        _ap_hien_hanh(con, ma_ho, pa, goc['lan'])


def ghep_v3(con, ma_ho: int, nguon_nhom: dict, ly_do: str = '') -> None:
    """V3 ghép từng nhóm (đất theo V1, nhà, cây theo V2.1…). Nhóm hỗ trợ nguồn TINH_LAI: giữ khoản của V1 rồi tính lại theo số liệu đã ghép."""
    kiem_ho_nhan_viec(con, ma_ho)
    kiem_quyen(con, 'sua_gia', 'ghép phương án trình duyệt')
    _kiem_v3_mo(con, ma_ho)
    goc1 = lay(con, ma_ho, V1) or {}
    lan = goc1.get('lan') or _lan_mo(con, ma_ho)

    def nguon_cua(nhom):
        ma = nguon_nhom.get(nhom, V1)
        return doc_pa(con, ma_ho, V1 if ma == TINH_LAI else ma)
    pa = PhuongAn(ho=nguon_cua(DAT).ho)
    pa.dat = list(nguon_cua(DAT).dat)
    for nhom, cac_muc in MUC_CUA_NHOM.items():
        p = nguon_cua(nhom)
        for m in cac_muc:
            pa.khoan[m] = list(p.khoan.get(m, ()))
    if nguon_nhom.get(HO_TRO) == TINH_LAI:
        pa = _tinh_lai_ho_tro(con, ma_ho, lan, pa)
    with csdl.giao_dich(con):
        ten = '; '.join(f'{TEN_NHOM[k]}: {"tính lại" if nguon_nhom.get(k) == TINH_LAI else nguon_nhom.get(k, V1)}' for k, _ in NHOM)
        _ghi(con, ma_ho, V3, lan, pa, LOAI[V3], 'V3 - PA Chính thức Trình duyệt (ghép)', 0, 'GHEP', ly_do or f'Ghép: {ten}', dict(nguon_nhom))
        csdl.ghi_nhat_ky(con, 'Ghép phương án trình duyệt (V3)', f'Hộ {ma_ho}: {ten}'[:300])
        _ap_hien_hanh(con, ma_ho, pa, lan)


def _tinh_lai_ho_tro(con, ma_ho: int, lan: int, pa: PhuongAn) -> PhuongAn:
    """Sửa các khoản hỗ trợ đã có theo số liệu mới (BoSoan.goi_y): chỉ 'sửa' / 'thay'; khoản đề xuất THÊM mới để người lập quyết định."""
    from .lap_pa import BoSoan
    bo = BoSoan(con, ma_ho, lan=lan)
    bo.pa = pa
    bo.tinh_lai_ho_tro()
    return bo.pa


def ap_dong_loat(con, ds_ma_ho, nguon: str = V1, ly_do: str = '') -> tuple:
    """Trả V3 của nhiều hộ về nguồn. Lỗi hộ nào (lần đã duyệt, chưa có V1…) ghi hộ đó, các hộ khác vẫn áp. Trả (số hộ, [lỗi])."""
    n, loi = 0, []
    for ma in ds_ma_ho:
        try:
            dat_v3(con, ma, nguon, ly_do)
            n += 1
        except LoiNhap as e:
            loi.append(f'Hộ {ma}: {e}')
    return n, loi


# ---------------------------------------------------------------- mã định danh hộ (nhúng vào file xuất, khớp lại khi đọc kết quả)
def uuid_ho(con, ma_ho: int) -> str:
    """Mã định danh cố định của hộ; file mở chỉ xem chưa có mã: ''."""
    try:
        if not co_bang(con):
            csdl._tao_bang_phien_ban(con)
        r = con.execute('SELECT uuid FROM ho_uuid WHERE ma_ho = ?', (ma_ho,)).fetchone()
        if r is not None:
            return r[0]
        m = str(uuid.uuid4())
        with csdl.giao_dich(con):
            con.execute('INSERT INTO ho_uuid (ma_ho, uuid) VALUES (?, ?)', (ma_ho, m))
        return m
    except sqlite3.OperationalError:
        return ''


def bang_uuid(con) -> dict:
    """{uuid: ma_ho}."""
    try:
        return {r[0]: r[1] for r in con.execute('SELECT uuid, ma_ho FROM ho_uuid')}
    except sqlite3.OperationalError:
        return {}


# ---------------------------------------------------------------- đối chiếu V1 | V2.n | V3
def _cac_dong(pa: PhuongAn, bc) -> dict:
    """{khóa dòng: (nhóm, tên, đvt, số lượng, đơn giá sau hệ số, thành tiền)}; dòng trùng khóa (cùng mã nhiều dòng) đánh số."""
    kq, dem = {}, {}

    def them(k, gt):
        dem[k] = dem.get(k, 0) + 1
        kq[k + (dem[k],)] = gt
    ten_thua = {t['ma_thua']: f'Thửa {t["so_thua"]} tờ {t["so_to"]}' for t in bc.thua.values()}
    for d in pa.dat:
        don_gia = D(d.gia_bang_gia) * D(d.he_so_k if d.he_so_k not in (None, '') else 1)
        them((DAT, d.ma_thua, d.loai_dat), (DAT, f'{ten_thua.get(d.ma_thua, "Thửa ?")} - {d.loai_dat}', 'm²', d.dien_tich, don_gia, thanh_tien_dong_dat(d, bc)))
    for nhom, cac_muc in MUC_CUA_NHOM.items():
        for m in cac_muc:
            for d in pa.khoan.get(m, ()):
                them((nhom, d.ma or d.ten), (nhom, d.ten, d.dvt, d.so_luong, d.don_gia, thanh_tien_dong(d, bc)))
    return kq


def _trang_thai(d1, d2) -> str:
    if d1 == 0 and d2 == 0:
        return 'Không biến động'
    if d1 != 0 and d2 == 0:
        return 'Có ý kiến nhưng giữ theo V1'
    if d1 == d2:
        return 'Chấp thuận điều chỉnh theo V2'
    return 'Điều chỉnh một phần'


def doi_chieu_ho(con, ma_ho: int, v2: str = '', bc=None) -> dict:
    """{'dong': [dict từng dòng V1 / V2 / V3, Δ1 = V2 - V1, Δ2 = V3 - V1], 'tong': {V1, V2, V3, d1, d2}, 'v2': mã nhánh, 'ly_do': căn cứ của V3}."""
    bc = bc or BoiCanh.tu(con)
    v2 = v2 or v2_moi_nhat(con, ma_ho)
    co = {x['ma'] for x in ds_phien_ban(con, ma_ho)}
    nguon1 = V1 if V1 in co else V0
    k1 = ket_qua(con, ma_ho, nguon1, bc)
    k2 = ket_qua(con, ma_ho, v2, bc) if v2 in co else k1
    k3 = ket_qua(con, ma_ho, V3, bc) if V3 in co else k1
    p1, p2, p3 = (_cac_dong(doc_pa(con, ma_ho, m), bc) for m in (nguon1, v2 if v2 in co else nguon1, V3 if V3 in co else nguon1))
    r3 = lay(con, ma_ho, V3) or {}
    dong = []
    trong = (None, '', '', KHONG, KHONG, KHONG)
    for k in list(p1) + [x for x in p2 if x not in p1] + [x for x in p3 if x not in p1 and x not in p2]:
        a, b, c = p1.get(k, trong), p2.get(k, trong), p3.get(k, trong)
        ref = next(x for x in (c, b, a) if x[0] is not None)
        d1, d2 = b[5] - a[5], c[5] - a[5]
        dong.append(dict(nhom=ref[0], ten=ref[1], dvt=ref[2], sl1=a[3], dg1=a[4], tt1=a[5], sl2=b[3], dg2=b[4], tt2=b[5], d1=d1,
                         sl3=c[3], dg3=c[4], tt3=c[5], d2=d2, trang_thai=_trang_thai(d1, d2), dg_d1=b[4] - a[4]))
    t5 = (k1.muc.get(5, KHONG), k2.muc.get(5, KHONG), k3.muc.get(5, KHONG))
    if any(t5):
        d1, d2 = t5[1] - t5[0], t5[2] - t5[0]
        dong.append(dict(nhom='THUONG', ten=TEN_THUONG, dvt='', sl1=KHONG, dg1=KHONG, tt1=t5[0], sl2=KHONG, dg2=KHONG, tt2=t5[1], d1=d1,
                         sl3=KHONG, dg3=KHONG, tt3=t5[2], d2=d2, trang_thai=_trang_thai(d1, d2), dg_d1=KHONG))
    return dict(dong=dong, v2=v2 if v2 in co else '', tong={V1: k1.tong, 'V2': k2.tong, V3: k3.tong, 'd1': k2.tong - k1.tong, 'd2': k3.tong - k1.tong},
                ly_do=r3.get('ghi_chu') or '', co_v1=V1 in co, co_v3=V3 in co)


def doi_chieu_dot(con, ds_ma_ho, bc=None) -> list:
    """Tổng hợp toàn đợt: mỗi hộ một dòng (V1, V2 mới nhất, V3, Δ1, Δ2, lý do)."""
    bc = bc or BoiCanh.tu(con)
    kq = []
    ten = {r[0]: r[1] for r in con.execute('SELECT ma_ho, ho_ten FROM ho')}
    for ma in ds_ma_ho:
        d = doi_chieu_ho(con, ma, bc=bc)
        t = d['tong']
        kq.append(dict(ma_ho=ma, ho_ten=ten.get(ma, ''), v2=d['v2'], tong_v1=t[V1], tong_v2=t['V2'], tong_v3=t[V3], d1=t['d1'], d2=t['d2'], ly_do=d['ly_do'], co_v1=d['co_v1']))
    return kq

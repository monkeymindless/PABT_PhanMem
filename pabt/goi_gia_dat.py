"""Bộ quy tắc giá đất: mỗi văn bản (QĐ 03/2026/QĐ-UBND, quyết định thay thế sau này…) là MỘT GÓI DỮ LIỆU có ngày hiệu lực, phần mềm đọc gói mà tính (1.0.64, người dùng 05/11/2026). Không Qt.

Quy định đổi: cán bộ quản trị nhập gói mới, xem khác gì gói cũ rồi lưu; không sửa mã, không cài lại. Trong gói:
  ma, ten, so_hieu, bang_gia, van_ban_can_cu, hieu_luc_tu, hieu_luc_den      căn cứ và thời gian áp dụng
  cong_thuc      he_so (thứ tự nhân, VD ["K1", "K2", "K3", "K_KHAC"]), lam_tron_he_so, lam_tron_tam, lam_tron (0: đồng; -3: nghìn)
  he_so_them     hệ số mới văn bản đặt ra: [{ma: "K4", ten, mac_dinh, can_cu}]
  nhom_dat       ma, ten, cot_k1 (khóa trong đoạn đường), cot_gia (cột bảng giá), phu_luc, la_nong_nghiep
  vi_tri, ket_cau, yeu_to (K3: he_so, ap_cho nn | pnn | ca, kich_hoat_ket_cau, khoa_neu_quy_dinh_rieng, can_cu, dien_giai)
  chuyen_tiep    bat; cau_chu: các câu giải trình theo mẫu, ô {so_hieu}, {k1}… (bảng CAU_CHU)
  dia_ban        {tên bảng: [đoạn đường: ma_doan_duong, tt_bat_dau, tt_ket_thuc, ten_duong, diem_dau, diem_cuoi, các cột K1, co_quy_dinh_rieng_duong_dat_tai_pl1]}

CÔNG THỨC LÀ DỮ LIỆU KHAI BÁO, KHÔNG PHẢI MÃ: chỉ gồm danh sách hệ số được nhân và số chữ số làm tròn, không eval / exec; câu chữ điền bằng thay chuỗi (không str.format), nên nhận file lạ không chạy được lệnh gì (kiem_goi kiểm từng trường).
Giới hạn cố ý: công thức khác dạng tích (bậc thang, phụ thuộc diện tích, cộng trừ) vẫn cần sửa mã, phát hành qua gói cập nhật .larcud.

Gói gắn sẵn: khóa "goi" trong pabt/gia_dat_qd03.json (không sửa, không xóa được). Gói của máy gộp một file <thư mục máy>/quy_tac_gia_dat.json để dong_bo_don_gia phát hành qua máy chủ LAN như bảng giá, hệ số K.
Quyền ghi: quan_tri_bo.kiem_quyen / sau_khi_sua (như bảng giá đất, hệ số K). Số đã áp vào hộ KHÔNG tự đổi khi có gói mới: dòng đất lưu đơn giá + tên gói ở Ghi chú, V1 giữ ảnh chụp; dự án nhớ gói đã chọn (cai_dat)."""
from __future__ import annotations

import copy
import json
import os
import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from functools import lru_cache

MA_GAN_SAN = 'QD03_2026_DONG_NAI'
TEN_FILE = 'quy_tac_gia_dat.json'
FILE_GAN_SAN = 'gia_dat_qd03.json'
KHOA_DOAN = 'danh_muc_doan_duong_rut_gon_106_tuyen'
HE_SO_CO_SAN = ('K1', 'K2', 'K3', 'K_KHAC')
CO_TOI_DA = 20 * 2 ** 20
TRUONG_DOAN = ('ma_doan_duong', 'tt_bat_dau', 'tt_ket_thuc', 'ten_duong', 'diem_dau', 'diem_cuoi')
CAI_DAT_DU_AN = 'GOI_GIA_DAT'
# câu chữ của gói: (khóa, nhãn trên màn hình Bộ quy tắc). Ô điền: {so_hieu} {bang_gia} và ô riêng của từng câu
CAU_CHU = (
    ('buoc_1', 'Bước 1: giá bảng giá. Ô: {dia_ban} {vi_tri} {gia}'),
    ('buoc_2_doan', 'Bước 2: K1 theo đoạn đường. Ô: {phu_luc} {ten_duong} {diem_dau} {diem_cuoi} {nhom} {k1}'),
    ('buoc_2_tay', 'Bước 2: K1 nhập tay. Ô: {k1}'),
    ('k2_co', 'Bước 3: có K2. Ô: {k2}'),
    ('k2_khong', 'Bước 3: không có K2'),
    ('k3_khoa', 'Bước 4: tuyến có quy định riêng, khóa K3'),
    ('k3_nn_co', 'Bước 4: đất nông nghiệp có yếu tố. Ô: {yeu_to} {k3} {k3_2}'),
    ('k3_nn_khong', 'Bước 4: đất nông nghiệp không có yếu tố'),
    ('k3_pnn_co', 'Bước 4: đất phi nông nghiệp có yếu tố. Ô: {yeu_to} {k3} {k3_2}'),
    ('k3_pnn_khong', 'Bước 4: đất phi nông nghiệp không có yếu tố'),
    ('canh_bao_khoa', 'Cảnh báo chống nhân trùng hệ số'),
    ('loai_tru_nn', 'Lưu ý: yếu tố PNN bị loại khỏi đất NN'),
    ('loai_tru_pnn', 'Lưu ý: yếu tố NN bị loại khỏi đất PNN'),
    ('ct_cao', 'Bước 5: giữ giá đất cụ thể. Ô: {gia_cu_the} {gia_tinh}'),
    ('ct_thap', 'Bước 5: chuyển sang giá tính. Ô: {gia_cu_the} {gia_tinh}'),
    ('ghi_chu_ct', 'Ghi chú dòng đất khi giữ giá cụ thể'),
    ('nhan_k2', 'Nhãn ô đánh dấu K2'),
    ('nhan_rieng', 'Nhãn ô "tuyến có quy định riêng"'),
    ('nhan_cu_the', 'Chữ mờ ô giá đất cụ thể'),
)


class LoiGoi(ValueError):
    """Gói quy tắc không hợp lệ (thông báo tiếng Việt)."""


# ---------------------------------------------------------------- đọc, lưu
@lru_cache(maxsize=1)
def du_lieu_goc() -> dict:
    """Nội dung pabt/gia_dat_qd03.json. Dùng chung: không sửa đối tượng trả về."""
    from . import tai_nguyen
    with open(str(tai_nguyen(FILE_GAN_SAN)), 'r', encoding='utf-8') as f:
        return json.load(f)


@lru_cache(maxsize=1)
def _gan_san() -> dict:
    """Gói gắn sẵn. Dùng chung: không sửa đối tượng trả về (tao_goi_tu chép sâu)."""
    d = du_lieu_goc()
    goi = dict(d['goi'])
    goi['dia_ban'] = d[KHOA_DOAN]
    goi['gan_san'] = True
    return goi


def file_may():
    from .may_chu import thu_muc_may
    return thu_muc_may() / TEN_FILE


def _quen() -> None:
    _NHO.clear()


_NHO = {}


def _doc_may() -> list:
    p = file_may()
    try:
        m = p.stat().st_mtime_ns
    except OSError:
        return []
    if _NHO.get('m') != (str(p), m):
        try:
            ds = json.loads(p.read_text(encoding='utf-8')).get('goi') or []
        except (OSError, ValueError, AttributeError):   # file hỏng: dùng gói gắn sẵn, không làm chết cửa sổ tính giá
            ds = []
        _NHO.update(m=(str(p), m), ds=[g for g in ds if isinstance(g, dict) and not kiem_goi(g)])
    return _NHO['ds']


def ds_goi() -> list:
    """Mọi gói: gắn sẵn trước, rồi gói của máy theo ngày hiệu lực giảm dần."""
    may = sorted(_doc_may(), key=lambda g: g.get('hieu_luc_tu', ''), reverse=True)
    return [_gan_san()] + may


def lay_goi(ma: str) -> dict | None:
    return next((g for g in ds_goi() if g.get('ma') == ma), None)


def _ngay(s) -> str:
    """'dd/mm/yyyy' hoặc 'yyyy-mm-dd' -> 'yyyy-mm-dd'; không hợp lệ: ''."""
    s = str(s or '').strip()
    for mau in ('%Y-%m-%d', '%d/%m/%Y'):
        try:
            return datetime.strptime(s, mau).strftime('%Y-%m-%d')
        except ValueError:
            continue
    return ''


def ngay_vn(s) -> str:
    """'yyyy-mm-dd' -> 'dd/mm/yyyy' để hiện."""
    n = _ngay(s)
    return f'{n[8:10]}/{n[5:7]}/{n[:4]}' if n else ''


def nhan_goi(g: dict) -> str:
    return f'{g.get("ten", "")} - từ {ngay_vn(g.get("hieu_luc_tu"))}' + (f' đến {ngay_vn(g["hieu_luc_den"])}' if g.get('hieu_luc_den') else '')


def _ten_xa_chuan(xa: str) -> str:
    from .lap_pa import bo_dau
    return re.sub(r'^(xa|phuong|thi tran|dac khu)\s+', '', bo_dau(xa or ''))


def co_dia_ban(goi: dict, xa: str) -> bool:
    from .lap_pa import bo_dau
    t = _ten_xa_chuan(xa)
    return bool(t) and any(t in bo_dau(k) for k in goi.get('dia_ban', ()))


def _trong_hieu_luc(g: dict, n: str) -> bool:
    return g.get('hieu_luc_tu', '') <= n and (not g.get('hieu_luc_den') or n <= g['hieu_luc_den'])


def chon_goi(ngay=None, xa: str = '') -> dict:
    """Gói áp dụng tại ngày (mặc định hôm nay): đang hiệu lực, hiệu lực từ muộn nhất; có xã thì ưu tiên gói có xã đó. Không gói nào hợp: gói gắn sẵn."""
    n = _ngay(ngay) or date.today().strftime('%Y-%m-%d')
    hop = sorted((g for g in ds_goi() if _trong_hieu_luc(g, n)), key=lambda g: g.get('hieu_luc_tu', ''), reverse=True)
    co_xa = [g for g in hop if xa and co_dia_ban(g, xa)]
    return (co_xa or hop or [_gan_san()])[0]


def goi_du_an(con, xa: str = '') -> dict:
    """Gói dự án đã chọn (cai_dat); chưa chọn hoặc gói đã mất: theo ngày hôm nay."""
    if con is not None:
        from . import csdl
        g = lay_goi(csdl.doc_cai_dat(con, CAI_DAT_DU_AN, ''))
        if g is not None:
            return g
    return chon_goi(None, xa)


def nho_goi_du_an(con, ma: str) -> None:
    """Dự án giữ nguyên gói đã áp, có gói mới cũng không tự đổi."""
    from . import csdl
    from .lap_pa import kiem_quyen
    kiem_quyen(con, 'sua_gia', 'ghi gói quy tắc giá đất của dự án')
    if csdl.doc_cai_dat(con, CAI_DAT_DU_AN, '') == ma:
        return
    with csdl.giao_dich(con):
        csdl.ghi_cai_dat(con, CAI_DAT_DU_AN, ma)
        csdl.ghi_nhat_ky(con, 'Chọn gói quy tắc giá đất', ma)


def canh_bao_goi(goi: dict, xa: str = '', ngay=None) -> list:
    """Những điều người tính cần biết về gói đang dùng: dự án ở xã gói chưa có; hôm nay gói khác mới là gói đang hiệu lực."""
    kq = []
    if xa and not co_dia_ban(goi, xa):
        kq.append(f'Dự án ở {xa} nhưng gói "{goi.get("ten", "")}" chưa có địa bàn này: đoạn đường đang chọn KHÔNG thuộc dự án. Vào Bộ quy tắc, tạo gói từ bảng hệ số K hoặc nhập gói mới.')
    n = _ngay(ngay) or date.today().strftime('%Y-%m-%d')
    moi = chon_goi(n, xa)
    if moi.get('ma') != goi.get('ma'):
        kq.append(f'Theo ngày hôm nay, gói đang hiệu lực là "{moi.get("ten", "")}"; bảng đang tính theo gói "{goi.get("ten", "")}".')
    return kq


# ---------------------------------------------------------------- kiểm tra
def _la_so_duong(x) -> bool:
    if isinstance(x, bool):
        return False
    try:
        d = Decimal(str(x))
        return d.is_finite() and d > 0
    except InvalidOperation:
        return False


def _la_int(x, tu: int, den: int) -> bool:
    return isinstance(x, int) and not isinstance(x, bool) and tu <= x <= den


def _kiem_doan(k: str, ds, cot: set, loi: list) -> None:
    if not isinstance(ds, list) or not ds:
        loi.append(f'{k}: chưa có đoạn đường.')
        return
    tt = 0
    for r in ds:
        if not isinstance(r, dict) or any(t not in r for t in TRUONG_DOAN):
            loi.append(f'{k}: đoạn đường thiếu trường.')
            return
        for c in cot:
            if c in r and not _la_so_duong(r[c]):
                loi.append(f'{k}, {r.get("ma_doan_duong")}: hệ số {c} phải là số lớn hơn 0.')
        if not any(c in r for c in cot):
            loi.append(f'{k}, {r.get("ma_doan_duong")}: không có cột K1 nào.')
        if not _la_int(r.get('tt_bat_dau'), 1, 10 ** 6) or r['tt_bat_dau'] <= tt:
            loi.append(f'{k}, {r.get("ma_doan_duong")}: số TT phải tăng dần.')
            return
        tt = r['tt_bat_dau']


def kiem_goi(g) -> list:
    """Danh sách lỗi (rỗng: dùng được). Kiểm từng trường, từ chối giá trị lạ; không gói nào có thể chứa mã chạy được."""
    if not isinstance(g, dict):
        return ['Gói không đúng dạng.']
    loi = []
    if not re.fullmatch(r'[A-Za-z0-9_.\-]{1,60}', str(g.get('ma') or '')):
        loi.append('Mã gói chỉ gồm chữ không dấu, số, "_", "-", ".".')
    for k, ten in (('ten', 'tên gói'), ('so_hieu', 'số hiệu văn bản'), ('bang_gia', 'bảng giá đất áp dụng')):
        if not str(g.get(k) or '').strip():
            loi.append(f'Thiếu {ten}.')
    if not _ngay(g.get('hieu_luc_tu')):
        loi.append('Thiếu hoặc sai ngày hiệu lực từ.')
    if g.get('hieu_luc_den') and (not _ngay(g['hieu_luc_den']) or _ngay(g['hieu_luc_den']) < _ngay(g.get('hieu_luc_tu'))):
        loi.append('Ngày hiệu lực đến phải sau ngày hiệu lực từ.')
    ct = g.get('cong_thuc') if isinstance(g.get('cong_thuc'), dict) else {}
    them = g.get('he_so_them') or []
    ma_them = []
    if not isinstance(them, list):
        loi.append('he_so_them phải là danh sách.')
        them = []
    for x in them:
        if not isinstance(x, dict) or not re.fullmatch(r'K_?[A-Z0-9]{1,8}', str(x.get('ma') or '')) or x.get('ma') in HE_SO_CO_SAN or not _la_so_duong(x.get('mac_dinh', 1)):
            loi.append(f'Hệ số thêm không hợp lệ: {x.get("ma") if isinstance(x, dict) else x} (mã dạng K4, mặc định lớn hơn 0).')
        else:
            ma_them.append(x['ma'])
    hs = ct.get('he_so')
    if not isinstance(hs, list) or 'K1' not in hs or len(set(map(str, hs))) != len(hs):
        loi.append('Công thức phải là danh sách hệ số, có K1, không lặp.')
    else:
        loi += [f'Công thức có hệ số chưa khai báo: {x}' for x in hs if x not in HE_SO_CO_SAN and x not in ma_them]
        loi += [f'Hệ số {x} đã khai báo nhưng chưa có trong công thức.' for x in ma_them if x not in hs]
    for k, tu, den in (('lam_tron', -6, 4), ('lam_tron_tam', 0, 10), ('lam_tron_he_so', 0, 10)):
        if not _la_int(ct.get(k), tu, den):
            loi.append(f'Công thức: {k} phải là số nguyên từ {tu} đến {den}.')
    nhom = g.get('nhom_dat')
    if not isinstance(nhom, list) or not nhom:
        loi.append('Thiếu nhóm đất.')
        nhom = []
    cot = set()
    for x in nhom:
        if not isinstance(x, dict) or not x.get('ma') or not x.get('cot_k1') or not x.get('cot_gia') or not x.get('ten'):
            loi.append('Nhóm đất thiếu trường (ma, ten, cot_k1, cot_gia).')
        else:
            cot.add(x['cot_k1'])
    for ten in ('vi_tri', 'ket_cau'):
        if not isinstance(g.get(ten), list) or not g[ten] or not all(isinstance(x, dict) and x.get('ma') and x.get('ten') for x in g[ten]):
            loi.append(f'Thiếu hoặc sai danh sách {ten}.')
    yt = g.get('yeu_to') or []
    if not isinstance(yt, list):
        loi.append('Danh sách yếu tố không đúng dạng.')
        yt = []
    ma_yt = set()
    for y in yt:
        if not isinstance(y, dict) or not y.get('ma') or not y.get('ten') or not _la_so_duong(y.get('he_so')) or y.get('ap_cho') not in ('nn', 'pnn', 'ca'):
            loi.append(f'Yếu tố K3 không hợp lệ: {y.get("ma") if isinstance(y, dict) else y} (cần mã, tên, hệ số lớn hơn 0, áp cho nn / pnn / ca).')
        elif y['ma'] in ma_yt:
            loi.append(f'Yếu tố K3 trùng mã: {y["ma"]}')
        else:
            ma_yt.add(y['ma'])
    cc = g.get('cau_chu')
    if cc is not None and (not isinstance(cc, dict) or not all(isinstance(v, str) and len(v) <= 4000 for v in cc.values())):
        loi.append('Câu chữ của gói không đúng dạng.')
    db = g.get('dia_ban')
    if not isinstance(db, dict) or not db:
        loi.append('Thiếu địa bàn, đoạn đường.')
        db = {}
    for k, ds in db.items():
        _kiem_doan(k, ds, cot, loi)
        if len(loi) > 30:
            return loi[:30] + ['… và nhiều lỗi khác.']
    return loi


# ---------------------------------------------------------------- ghi (quyền như bảng giá đất, hệ số K)
def ghi_goi(g: dict) -> None:
    """Thêm / thay gói của máy, ghi nguyên tử. Gói gắn sẵn không thay được; hỏng: LoiGoi, không ghi gì."""
    from . import quan_tri_bo
    quan_tri_bo.kiem_quyen('cập nhật bộ quy tắc giá đất')
    g = {k: v for k, v in g.items() if k != 'gan_san'}
    if g.get('ma') == MA_GAN_SAN:
        raise LoiGoi('Gói gắn sẵn không sửa được: đặt mã gói khác để tạo gói mới.')
    loi = kiem_goi(g)
    if loi:
        raise LoiGoi('Gói chưa hợp lệ:\n' + '\n'.join(loi[:12]))
    _ghi_may([x for x in _doc_may() if x.get('ma') != g['ma']] + [g])
    quan_tri_bo.sau_khi_sua()


def xoa_goi(ma: str) -> None:
    from . import quan_tri_bo
    quan_tri_bo.kiem_quyen('xóa gói quy tắc giá đất')
    if ma == MA_GAN_SAN:
        raise LoiGoi('Gói gắn sẵn không xóa được.')
    _ghi_may([x for x in _doc_may() if x.get('ma') != ma])
    quan_tri_bo.sau_khi_sua()


def _ghi_may(ds: list) -> None:
    p = file_may()
    p.parent.mkdir(parents=True, exist_ok=True)
    tam = p.with_suffix('.json.tmp')
    tam.write_text(json.dumps({'goi': ds}, ensure_ascii=False, indent=1), encoding='utf-8')
    os.replace(tam, p)
    _quen()


def doc_file_goi(file) -> dict:
    """Gói từ file .json người dùng chọn: chỉ đọc dữ liệu, kiểm đủ trường. Lỗi: LoiGoi. Chưa lưu."""
    from pathlib import Path
    p = Path(file)
    try:
        if p.stat().st_size > CO_TOI_DA:
            raise LoiGoi('File gói quá lớn.')
        g = json.loads(p.read_text(encoding='utf-8-sig'))
    except (OSError, ValueError) as e:
        if isinstance(e, LoiGoi):
            raise
        raise LoiGoi(f'Không đọc được file gói: {e}') from None
    if isinstance(g, dict) and 'goi' in g and 'cong_thuc' not in g:             # gói dạng tệp gắn sẵn
        d = g['goi'] if isinstance(g['goi'], dict) else {}
        g = dict(d, dia_ban=g.get(KHOA_DOAN) or d.get('dia_ban'))
    loi = kiem_goi(g)
    if loi:
        raise LoiGoi('File không phải gói quy tắc hợp lệ:\n' + '\n'.join(loi[:12]))
    return g


def xuat_file_goi(g: dict, file) -> None:
    from pathlib import Path
    Path(file).write_text(json.dumps({k: v for k, v in g.items() if k != 'gan_san'}, ensure_ascii=False, indent=1), encoding='utf-8')


def tao_goi_tu(goc: dict, ma: str, ten: str, hieu_luc_tu: str) -> dict:
    """Gói mới chép quy tắc từ gói gốc (K3, công thức, đoạn đường) để sửa; hiệu lực riêng."""
    g = copy.deepcopy({k: v for k, v in goc.items() if k != 'gan_san'})
    g.update(ma=ma, ten=ten, so_hieu=ten, hieu_luc_tu=_ngay(hieu_luc_tu), hieu_luc_den='', goc=goc.get('ma', ''), van_ban_can_cu=[])     # căn cứ của văn bản cũ không theo sang
    return g


def tao_goi_tu_he_so_k(goc: dict, ma: str, ten: str, hieu_luc_tu: str) -> dict:
    """Gói mới: quy tắc của gói gốc, đoạn đường + K1 lấy từ bảng hệ số K đang dùng (thẻ Hệ số K đã nhập từ văn bản), thêm được xã mới như Tân Triều.
    Mỗi nhóm đất một cột K1 riêng (bảng có thể cho rừng / NTS khác cây lâu năm). Hệ số một nhóm khác nhau trong cùng đoạn (theo vị trí): từ chối, vì gói tính K1 theo đoạn."""
    from . import he_so_k
    g = tao_goi_tu(goc, ma, ten, hieu_luc_tu)
    for x in g['nhom_dat']:
        x['cot_k1'] = 'k1_' + x['cot_gia']
    cot_co = {x['cot_gia'] for x in g['nhom_dat']}
    db = {}
    for r in he_so_k.tat_ca():
        if r.get('tt') in ('', None) or not r.get('tuyen_duong') or not r.get('dia_ban'):
            continue
        ds = db.setdefault(r['dia_ban'], {})
        khoa = (r['tuyen_duong'], r.get('diem_dau', ''), r.get('diem_cuoi', ''))
        d = ds.setdefault(khoa, dict(ten_duong=khoa[0], diem_dau=khoa[1], diem_cuoi=khoa[2], tt_bat_dau=int(r['tt']), tt_ket_thuc=int(r['tt']), co_quy_dinh_rieng_duong_dat_tai_pl1=False))
        d['tt_bat_dau'] = min(d['tt_bat_dau'], int(r['tt']))
        d['tt_ket_thuc'] = max(d['tt_ket_thuc'], int(r['tt']))
        ld = r.get('loai_dat') or ''
        hs = str(r['he_so'])
        for c in (cot_co if not ld else he_so_k.NHOM_CHUNG.get(ld, (ld,))):             # dòng chung 'nn' / 'pnn' / trống: cho mọi nhóm thuộc nó
            if c not in cot_co:
                continue
            if 'k1_' + c in d and Decimal(d['k1_' + c]) != Decimal(hs):
                raise LoiGoi(f'{r["dia_ban"]}, {khoa[0]}: hệ số K của {c} khác nhau theo vị trí trong cùng đoạn ({d["k1_" + c]}; {hs}). Dùng trực tiếp bảng hệ số K ở gói gắn sẵn.')
            d['k1_' + c] = hs
    kq = {}
    for xa, ds in db.items():
        hang = sorted(ds.values(), key=lambda x: x['tt_bat_dau'])
        hang = [d for d in hang if any(k.startswith('k1_') for k in d)]
        for i, d in enumerate(hang, 1):
            d['ma_doan_duong'] = f'{re.sub(r"[^A-Za-z0-9]+", "_", _khong_dau(xa))}_DOAN_{i:02d}'
        if hang:
            kq[xa] = hang
    if not kq:
        raise LoiGoi('Bảng hệ số K đang dùng không có dòng theo đoạn đường (TT, tuyến đường).')
    g['dia_ban'] = kq
    return g


def _khong_dau(s: str) -> str:
    from .lap_pa import bo_dau
    return bo_dau(s)


# ---------------------------------------------------------------- so sánh hai gói
def _chu_so(x) -> str:
    return format(Decimal(str(x)).normalize(), 'f').replace('.', ',')


def _khac_duong(ten_xa: str, ds_cu: list, ds_moi: list, cap_cot: list) -> list:
    # khóa theo TT + tên đường: chữ điểm đầu / điểm cuối mỗi nguồn ghi một kiểu, không phải đoạn khác
    ca = {(r['tt_bat_dau'], _khong_dau(r['ten_duong'])): r for r in ds_cu}
    cb = {(r['tt_bat_dau'], _khong_dau(r['ten_duong'])): r for r in ds_moi}
    them, bo = [x for x in cb if x not in ca], [x for x in ca if x not in cb]
    kq = []
    if them:
        kq.append(f'{ten_xa}: thêm {len(them)} đoạn đường, ví dụ {cb[them[0]]["ten_duong"]}')
    if bo:
        kq.append(f'{ten_xa}: bỏ {len(bo)} đoạn đường, ví dụ {ca[bo[0]]["ten_duong"]}')
    doi = [(x, t, ca[x][u], cb[x][v]) for x in cb if x in ca for t, u, v in cap_cot if u in ca[x] and v in cb[x] and Decimal(str(ca[x][u])) != Decimal(str(cb[x][v]))]
    if doi:
        x, t, u, v = doi[0]
        kq.append(f'{ten_xa}: đổi K1 {len(doi)} chỗ, ví dụ {cb[x]["ten_duong"]}, {t}: {_chu_so(u)} -> {_chu_so(v)}')
    return kq


def so_sanh(cu: dict, moi: dict) -> list:
    """Các điểm khác của gói mới so với gói cũ (chữ dễ đọc), để người duyệt xem trước khi lưu."""
    kq = []
    for k, ten in (('ten', 'Tên'), ('so_hieu', 'Số hiệu'), ('bang_gia', 'Bảng giá đất'), ('hieu_luc_tu', 'Hiệu lực từ'), ('hieu_luc_den', 'Hiệu lực đến')):
        if (cu.get(k) or '') != (moi.get(k) or ''):
            a, b = (ngay_vn(cu.get(k)), ngay_vn(moi.get(k))) if k.startswith('hieu_luc') else (cu.get(k), moi.get(k))
            kq.append(f'{ten}: {a or "(trống)"} -> {b or "(trống)"}')
    a, b = cu.get('cong_thuc', {}), moi.get('cong_thuc', {})
    if a.get('he_so') != b.get('he_so'):
        kq.append(f'CÔNG THỨC: {" × ".join(a.get("he_so", []))} -> {" × ".join(b.get("he_so", []))}')
    for k, ten in (('lam_tron', 'Làm tròn đơn giá'), ('lam_tron_tam', 'Làm tròn trung gian'), ('lam_tron_he_so', 'Làm tròn hệ số')):
        if a.get(k) != b.get(k):
            kq.append(f'{ten}: {a.get(k)} -> {b.get(k)}')
    ya, yb = {y['ma']: y for y in cu.get('yeu_to', [])}, {y['ma']: y for y in moi.get('yeu_to', [])}
    for m in yb:
        if m not in ya:
            kq.append(f'Thêm yếu tố K3 {yb[m]["ten"]}: ×{_chu_so(yb[m]["he_so"])}')
        elif Decimal(str(ya[m]['he_so'])) != Decimal(str(yb[m]['he_so'])):
            kq.append(f'Yếu tố K3 {yb[m]["ten"]}: ×{_chu_so(ya[m]["he_so"])} -> ×{_chu_so(yb[m]["he_so"])}')
    kq += [f'Bỏ yếu tố K3 {ya[m]["ten"]}' for m in ya if m not in yb]
    ma_cu = {y['ma'] for y in cu.get('he_so_them') or []}
    kq += [f'Thêm hệ số {x["ma"]} ({x.get("ten", "")})' for x in moi.get('he_so_them') or [] if x['ma'] not in ma_cu]
    if bool((cu.get('chuyen_tiep') or {}).get('bat')) != bool((moi.get('chuyen_tiep') or {}).get('bat')):
        kq.append(f'Quy định chuyển tiếp: {"bật" if (moi.get("chuyen_tiep") or {}).get("bat") else "tắt"}')
    doi_cau = [t for k, t in CAU_CHU if (cu.get('cau_chu') or {}).get(k) != (moi.get('cau_chu') or {}).get(k)]
    if doi_cau:
        kq.append(f'Đổi {len(doi_cau)} câu giải trình, ví dụ: {doi_cau[0]}')
    da, db = cu.get('dia_ban', {}), moi.get('dia_ban', {})
    kq += [f'Thêm địa bàn {k} ({len(db[k])} đoạn)' for k in db if k not in da]
    theo_gia = {x['cot_gia']: x['cot_k1'] for x in cu.get('nhom_dat', [])}
    cap_cot = [(x['cot_gia'], theo_gia[x['cot_gia']], x['cot_k1']) for x in moi.get('nhom_dat', []) if x['cot_gia'] in theo_gia]
    # gói từ bảng hệ số K đặt tên xã không có "Bảng 53.": so theo tên xã, không báo nhầm bỏ / thêm
    theo_ten = {_ten_xa_chuan(k.split('. ', 1)[-1]): k for k in da}
    con_cu = set(da)
    for k in db:
        ku = k if k in da else theo_ten.get(_ten_xa_chuan(k.split('. ', 1)[-1]))
        if ku is None:
            continue
        kq[:] = [x for x in kq if x != f'Thêm địa bàn {k} ({len(db[k])} đoạn)']
        con_cu.discard(ku)
        kq += _khac_duong(k, da[ku], db[k], cap_cot)
    kq += [f'Bỏ địa bàn {k}' for k in sorted(con_cu)]
    return kq

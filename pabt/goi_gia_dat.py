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
    ('buoc_1_vt', 'Bước 1a: tỷ lệ Vị trí, Phạm vi, trần sàn'),
    ('vt_ngan', 'Dòng phép tính Vị trí, Phạm vi trên màn hình và Ghi chú'),
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


def chuan_so_hieu(s) -> str:
    """Khóa so số hiệu văn bản (1.1.06 - đọc văn bản trùng gói đã có thì không tạo gói nháp): bỏ khoảng trắng, chữ "Số", chữ hoa,
    QD = QĐ ("QĐ 03/2026/QĐ-UBND" = "03/2026/QD-UBND")."""
    t = re.sub(r'\s+', '', str(s or '')).upper().replace('QD', 'QĐ')
    t = re.sub(r'^(SỐ:?|QĐ|NQ)(?=\d)', '', t)
    return t


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
    from .lap_pa import cung_dia_ban
    return bool(_ten_xa_chuan(xa)) and any(cung_dia_ban(xa, k) for k in goi.get('dia_ban', ()))


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
    tt, duong = 0, set()
    for r in ds:
        if not isinstance(r, dict) or any(t not in r for t in TRUONG_DOAN):
            loi.append(f'{k}: đoạn đường thiếu trường.')
            return
        for c in cot:
            if c in r and not _la_so_duong(r[c]):
                loi.append(f'{k}, {r.get("ma_doan_duong")}: hệ số {c} phải là số lớn hơn 0.')
        if not any(c in r for c in cot):
            loi.append(f'{k}, {r.get("ma_doan_duong")}: không có cột K1 nào.')
        tv = r.get('k1_theo_vt')
        if tv is not None and (not isinstance(tv, dict) or not all(
                isinstance(v, str) and isinstance(hs, dict) and all(c in cot and _la_so_duong(x) for c, x in hs.items()) for v, hs in tv.items())):
            loi.append(f'{k}, {r.get("ma_doan_duong")}: K1 theo vị trí (k1_theo_vt) không đúng dạng.')
        # 1.0.90: số TT không giảm; cùng số TT đầu chỉ được khi khác tuyến (bảng giá một xã có hai bảng con đánh số chồng nhau)
        if not _la_int(r.get('tt_bat_dau'), 1, 10 ** 6) or r['tt_bat_dau'] < tt:
            loi.append(f'{k}, {r.get("ma_doan_duong")}: số TT phải tăng dần.')
            return
        if r['tt_bat_dau'] != tt:
            duong = set()
        ten = _chu_doan(r.get('ten_duong'))
        if ten in duong:
            loi.append(f'{k}, {r.get("ma_doan_duong")}: hai đoạn cùng tuyến cùng số TT {r["tt_bat_dau"]} (đoạn bị tách đôi).')
            return
        duong.add(ten)
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
    g = gop_doan_trung(g)
    loi = kiem_goi(g)
    if loi:
        raise LoiGoi('File không phải gói quy tắc hợp lệ:\n' + '\n'.join(loi[:12]))
    return g


def xuat_file_goi(g: dict, file) -> None:
    from pathlib import Path
    Path(file).write_text(json.dumps({k: v for k, v in g.items() if k != 'gan_san'}, ensure_ascii=False, indent=1), encoding='utf-8')


# ---------------------------------------------------------------- gói cài (quy tắc + đơn giá đất + hệ số K theo xã)
LOAI_GOI_CAI = 'goi_cai_gia_dat'
DUOI_GOI_CAI = '.larcgia'
CO_GOI_CAI = 400 * 2 ** 20


def _khoa_xa(xa: str) -> str:
    """Khóa xã giữ dấu (1.0.90): "Xã Lộc Thành" và "Xã Lộc Thạnh" là hai xã, trước gộp một dòng khi chọn xã xuất gói cài."""
    from .lap_pa import khoa_dia_ban
    return khoa_dia_ban(xa)


def ds_xa_cho_goi_cai() -> list:
    """Danh sách địa bàn để chọn khi xuất gói cài: [{ten, so_gia, so_k, du}]. Chỉ xã đủ cả đơn giá và hệ số K mới chọn được."""
    from . import gia_dat_nq28 as nq, he_so_k as hk
    gia, k = {}, {}
    for r in nq.tat_ca():
        xa = (r.get('xa') or '').strip()
        if xa:
            gia[_khoa_xa(xa)] = gia.get(_khoa_xa(xa), 0) + 1
            gia.setdefault('_ten:' + _khoa_xa(xa), xa)
    for r in hk.tat_ca():
        xa = (r.get('dia_ban') or '').strip()
        if xa and xa != 'Toàn tỉnh':
            k[_khoa_xa(xa)] = k.get(_khoa_xa(xa), 0) + 1
            k.setdefault('_ten:' + _khoa_xa(xa), xa)
    ra = []
    for khoa in sorted(set(x for x in list(gia) + list(k) if not str(x).startswith('_ten:'))):
        ten = gia.get('_ten:' + khoa) or k.get('_ten:' + khoa) or khoa
        sg, sk = gia.get(khoa, 0), k.get(khoa, 0)
        ra.append(dict(ten=ten, khoa=khoa, so_gia=sg, so_k=sk, du=bool(sg and sk)))
    return ra


def _goi_cho_xa(goc: dict, ds_xa: list) -> dict:
    """Quy tắc gói gốc + đoạn đường / K1 chỉ của các xã đã chọn (từ bảng hệ số K)."""
    from datetime import date as _date
    khoa = {_khoa_xa(x) for x in ds_xa}
    ten = ', '.join(ds_xa[:4]) + ('…' if len(ds_xa) > 4 else '')
    ma = 'CAI_' + re.sub(r'[^A-Za-z0-9]+', '_', _khong_dau('_'.join(ds_xa[:3])))[:48].strip('_')
    try:
        g = tao_goi_tu_he_so_k(goc, ma or 'CAI_GIA_DAT', f'Gói cài giá đất ({ten})', _date.today().strftime('%d/%m/%Y'), chi_xa=ds_xa)
    except LoiGoi:
        g = tao_goi_tu(goc, ma or 'CAI_GIA_DAT', f'Gói cài giá đất ({ten})', _date.today().strftime('%d/%m/%Y'))
        db = {}
        for k, ds in (goc.get('dia_ban') or {}).items():
            if _khoa_xa(k) in khoa or any(_khoa_xa(x) in _khoa_xa(k) or _khoa_xa(k) in _khoa_xa(x) for x in ds_xa):
                db[k] = copy.deepcopy(ds)
        if db:
            g['dia_ban'] = db
    return g


def xuat_goi_cai(file, ds_xa: list, goi: dict | None = None) -> str:
    """Xuất file .larcgia (zip): bộ quy tắc + đơn giá đất + hệ số K của đúng các xã đã chọn. Đơn giá và hệ số K luôn đi cùng.
    Trả đường file đã ghi. Lỗi: LoiGoi."""
    import zipfile
    from pathlib import Path
    from . import gia_dat_nq28 as nq, he_so_k as hk
    ds_xa = [str(x).strip() for x in ds_xa if str(x).strip()]
    if not ds_xa:
        raise LoiGoi('Chọn ít nhất một xã / phường có đủ đơn giá đất và hệ số K.')
    bang = ds_xa_cho_goi_cai()
    theo = {_khoa_xa(x['ten']): x for x in bang}
    thieu = []
    for xa in ds_xa:
        tt = theo.get(_khoa_xa(xa))
        if tt is None or not tt['du']:
            thieu.append(xa)
    if thieu:
        raise LoiGoi('Các địa bàn sau thiếu đơn giá đất hoặc hệ số K (hai phần phải đi cùng nhau):\n- ' + '\n- '.join(thieu))
    khoa = {_khoa_xa(x) for x in ds_xa}
    ten_gia = {x['ten'] for x in bang if x['khoa'] in khoa}
    dong_gia = [dict(r) for r in nq.tat_ca() if _khoa_xa(r.get('xa') or '') in khoa
                or any(nq.khop_xa(t, r.get('xa') or '') for t in ten_gia)]
    dong_k = [dict(r) for r in hk.tat_ca() if _khoa_xa(r.get('dia_ban') or '') in khoa
              or any(hk.khop_dia_ban(r.get('dia_ban') or '', t) for t in ten_gia)]
    if not dong_gia or not dong_k:
        raise LoiGoi('Không lấy được đủ dòng đơn giá đất và hệ số K của các xã đã chọn.')
    goc = goi or _gan_san()
    goi_ra = _goi_cho_xa(goc, [theo[k]['ten'] for k in khoa if k in theo])
    p = Path(file)
    if p.suffix.lower() != DUOI_GOI_CAI:
        p = p.with_suffix(DUOI_GOI_CAI)
    mo_ta = dict(loai=LOAI_GOI_CAI, xa=sorted(ten_gia), so_gia=len(dong_gia), so_k=len(dong_k),
                 goi_ma=goi_ra.get('ma', ''), goi_ten=goi_ra.get('ten', ''))
    tep = {
        'goi.json': json.dumps({k: v for k, v in goi_ra.items() if k != 'gan_san'}, ensure_ascii=False, indent=1),
        'bang_gia_dat.json': json.dumps(dict(van_ban=nq.van_ban_dang_dung(), nguon='goi_cai', dong=dong_gia), ensure_ascii=False),
        'he_so_k.json': json.dumps(dict(van_ban=hk.van_ban(), nguon='goi_cai', dong=hk._gon(dong_k)),
                                   ensure_ascii=False, separators=(',', ':')).replace('},{', '},\n{'),
    }
    # 1.1.03: mã băm SHA-256 từng phần (kiem_dinh_don_gia.niemphong_sha256) - máy nhập so lại, gói bị sửa / hỏng sau khi xuất thì từ chối.
    # Mã ĐỐI CHIẾU, không phải chữ ký số
    from .kiem_dinh_don_gia import niemphong_sha256
    mo_ta['niem_phong'] = {ten: niemphong_sha256(x.encode('utf-8')) for ten, x in tep.items()}
    with zipfile.ZipFile(p, 'w', compression=zipfile.ZIP_DEFLATED) as z:
        z.writestr('mo_ta.json', json.dumps(mo_ta, ensure_ascii=False, indent=1))
        for ten, x in tep.items():
            z.writestr(ten, x.encode('utf-8'))
    return str(p)


def doc_goi_cai(file) -> dict:
    """Đọc file .larcgia -> {mo_ta, goi, bang_gia: {van_ban, dong}, he_so_k: {van_ban, dong}}. Lỗi: LoiGoi."""
    import zipfile
    from pathlib import Path
    p = Path(file)
    try:
        if p.stat().st_size > CO_GOI_CAI:
            raise LoiGoi('File gói cài quá lớn.')
        with zipfile.ZipFile(p) as z:
            ten = set(z.namelist())
            for bat in ('mo_ta.json', 'goi.json', 'bang_gia_dat.json', 'he_so_k.json'):
                if bat not in ten:
                    raise LoiGoi(f'File gói cài thiếu {bat}.')
            mo = json.loads(z.read('mo_ta.json').decode('utf-8-sig'))
            if mo.get('loai') != LOAI_GOI_CAI:
                raise LoiGoi('File không phải gói cài giá đất / hệ số K của LARC.')
            tho = {t: z.read(t) for t in ('goi.json', 'bang_gia_dat.json', 'he_so_k.json')}
            np = mo.get('niem_phong')
            if isinstance(np, dict) and np:               # gói từ 1.1.03 có mã băm từng phần; gói cũ không có: vẫn nhận
                from .kiem_dinh_don_gia import kiem_niem_phong
                sai = [t for t in tho if not kiem_niem_phong(tho[t], np.get(t, ''))]
                if sai:
                    raise LoiGoi('Gói cài đã bị sửa hoặc hỏng sau khi xuất (mã băm SHA-256 không khớp: ' + ', '.join(sai) +
                                 '). Xin lại file gói từ người đã thẩm định.')
                mo['niem_phong_khop'] = True
            goi = json.loads(str(tho['goi.json'], 'utf-8-sig'))
            bg = json.loads(str(tho['bang_gia_dat.json'], 'utf-8-sig'))
            hk = json.loads(str(tho['he_so_k.json'], 'utf-8-sig'))
    except LoiGoi:
        raise
    except (OSError, ValueError, KeyError, zipfile.BadZipFile) as e:
        raise LoiGoi(f'Không đọc được gói cài: {e}') from None
    goi = gop_doan_trung(goi)                           # 1.0.90: gói xuất từ bản trước có đoạn tách đôi cùng số TT
    loi = kiem_goi(goi)
    if loi:
        raise LoiGoi('Bộ quy tắc trong gói cài chưa hợp lệ:\n' + '\n'.join(loi[:8]))
    if not isinstance(bg, dict) or not bg.get('dong'):
        raise LoiGoi('Gói cài thiếu bảng giá đất.')
    if not isinstance(hk, dict) or not hk.get('dong'):
        raise LoiGoi('Gói cài thiếu hệ số K.')
    return dict(mo_ta=mo, goi=goi, bang_gia=bg, he_so_k=hk)


def _cua_xa(ten_xa: str, chon: list) -> bool:
    """Địa bàn ten_xa thuộc danh sách chọn (khóa giữ dấu - "Lộc Thành" khác "Lộc Thạnh")."""
    k = _khoa_xa(ten_xa or '')
    return bool(k) and any(k == _khoa_xa(x) for x in chon)


def thong_ke_goi_cai(xem: dict) -> list:
    """1.1.06 (hộp nhập gói cài): mỗi xã trong gói (doc_goi_cai) - [{ten, so_gia, so_k, gia_may, k_may}]: số dòng đơn giá / hệ số K
    trong gói và đang có trên máy (0 = xã mới, sẽ thêm; > 0 = xã trùng, sẽ thay sạch)."""
    from . import gia_dat_nq28 as nq, he_so_k as hk
    dong_k = hk._mo_rong(xem['he_so_k'].get('dong'))
    ten = list(dict.fromkeys([str(x) for x in (xem['mo_ta'].get('xa') or [])] +
                             [(r.get('xa') or '').strip() for r in xem['bang_gia']['dong'] if (r.get('xa') or '').strip()]))
    gia_may, k_may = {}, {}
    for r in nq.tat_ca():
        gia_may[_khoa_xa(r.get('xa') or '')] = gia_may.get(_khoa_xa(r.get('xa') or ''), 0) + 1
    for r in hk.tat_ca():
        k_may[_khoa_xa(r.get('dia_ban') or '')] = k_may.get(_khoa_xa(r.get('dia_ban') or ''), 0) + 1
    ra, da = [], set()
    for x in ten:
        k = _khoa_xa(x)
        if not k or k in da:
            continue
        da.add(k)
        ra.append(dict(ten=x, so_gia=sum(1 for r in xem['bang_gia']['dong'] if _khoa_xa(r.get('xa') or '') == k),
                       so_k=sum(1 for r in dong_k if _khoa_xa(r.get('dia_ban') or '') == k),
                       gia_may=gia_may.get(k, 0), k_may=k_may.get(k, 0)))
    return ra


def nhap_goi_cai(file, bo_sung: bool = True, chi_xa: list | None = None) -> dict:
    """Cài gói: lưu bộ quy tắc + ghi đơn giá đất + hệ số K của các xã trong gói. bo_sung=True: giữ xã khác trên máy, xã trùng tên
    thay sạch; False: bảng giá đất và hệ số K của máy chỉ còn các xã của gói. chi_xa (1.1.06): chỉ cài các xã này (đơn giá, hệ số K
    và đoạn đường riêng của gói đều lọc theo xã); None = mọi xã trong gói. Trả {xa, so_gia, so_k, goi_ma}. Cần quyền quản trị."""
    from . import gia_dat_nq28 as nq, he_so_k as hk, quan_tri_bo
    quan_tri_bo.kiem_quyen('cài gói giá đất và hệ số K')
    goi_cai = doc_goi_cai(file)
    goi, bg, bang_k = goi_cai['goi'], goi_cai['bang_gia'], goi_cai['he_so_k']
    dong_gia, dong_k = list(bg['dong']), hk._mo_rong(bang_k.get('dong'))
    mo = goi_cai['mo_ta']
    xa_cai = list(mo.get('xa') or [])
    if chi_xa is not None:
        chi_xa = [str(x).strip() for x in chi_xa if str(x).strip()]
        if not chi_xa:
            raise LoiGoi('Chưa chọn xã / phường nào để cài.')
        dong_gia = [r for r in dong_gia if _cua_xa(r.get('xa'), chi_xa)]
        dong_k = [r for r in dong_k if _cua_xa(r.get('dia_ban'), chi_xa)]
        if not dong_gia and not dong_k:
            raise LoiGoi('Gói không có dòng đơn giá / hệ số K nào của các xã đã chọn.')
        goi = dict(goi)
        if isinstance(goi.get('dia_ban'), dict):         # đoạn đường / K1 riêng theo xã của gói: chỉ xã đã chọn
            goi['dia_ban'] = {k: v for k, v in goi['dia_ban'].items() if _cua_xa(k, chi_xa)}
        xa_cai = [x for x in xa_cai if _cua_xa(x, chi_xa)] or chi_xa
    if goi.get('ma') == MA_GAN_SAN:
        goi = dict(goi)
        goi['ma'] = (goi.get('ma') or 'CAI') + '_MAY'
    ghi_goi(goi)
    if bo_sung:
        if dong_gia:
            nq.ghi_bo_sung(dong_gia, bg.get('van_ban') or '', str(file))
        if dong_k:
            cu = hk.tat_ca()
            xa_moi = {_khoa_xa(r.get('dia_ban') or '') for r in dong_k}
            giu = [r for r in cu if _khoa_xa(r.get('dia_ban') or '') not in xa_moi]
            hk.ghi(giu + dong_k, bang_k.get('van_ban') or hk.VAN_BAN, str(file))
    else:
        nq.ghi_thay(dong_gia, bg.get('van_ban') or '', str(file))
        hk.ghi(dong_k, bang_k.get('van_ban') or hk.VAN_BAN, str(file))
    return dict(xa=xa_cai, so_gia=len(dong_gia) if chi_xa is not None else int(mo.get('so_gia') or len(dong_gia)),
                so_k=len(dong_k) if chi_xa is not None else int(mo.get('so_k') or 0), goi_ma=goi.get('ma', ''),
                niem_phong=bool(mo.get('niem_phong_khop')))


def tao_goi_tu(goc: dict, ma: str, ten: str, hieu_luc_tu: str) -> dict:
    """Gói mới chép quy tắc từ gói gốc (K3, công thức, đoạn đường) để sửa; hiệu lực riêng."""
    g = copy.deepcopy({k: v for k, v in goc.items() if k != 'gan_san'})
    g.update(ma=ma, ten=ten, so_hieu=ten, hieu_luc_tu=_ngay(hieu_luc_tu), hieu_luc_den='', goc=goc.get('ma', ''), van_ban_can_cu=[])     # căn cứ của văn bản cũ không theo sang
    return g


def tao_goi_tu_he_so_k(goc: dict, ma: str, ten: str, hieu_luc_tu: str, chi_xa: list | None = None) -> dict:
    """Gói mới: quy tắc của gói gốc, đoạn đường + K1 lấy từ bảng hệ số K đang dùng (thẻ Hệ số K đã nhập từ văn bản), thêm được xã mới như Tân Triều.
    Mỗi nhóm đất một cột K1 riêng (bảng có thể cho rừng / NTS khác cây lâu năm). chi_xa: chỉ lấy các xã / phường này (gói cài); None = mọi địa bàn.
    1.0.90: đoạn đường khóa theo chữ đã bỏ dấu câu (Phụ lục I.1 ghi "…xã Trị An", I.2 ghi "…xã Trị An." - trước tách một đoạn làm hai cùng số TT,
    nhập lại gói báo "số TT phải tăng dần"); hai đoạn cùng tuyến chồng số TT gộp một. K1 một nhóm khác nhau theo vị trí trong cùng đoạn (Tam Hiệp,
    Lê Thoa: MT 1,19; T1 1,31): K1 của đoạn = vị trí đầu, vị trí khác ghi ở k1_theo_vt (trước: từ chối cả gói)."""
    from . import he_so_k
    g = tao_goi_tu(goc, ma, ten, hieu_luc_tu)
    for x in g['nhom_dat']:
        x['cot_k1'] = 'k1_' + x['cot_gia']
    cot_co = {x['cot_gia'] for x in g['nhom_dat']}
    db = {}
    for r in he_so_k.tat_ca():
        if r.get('tt') in ('', None) or not r.get('tuyen_duong') or not r.get('dia_ban'):
            continue
        if chi_xa and not any(he_so_k.khop_dia_ban(r['dia_ban'], x) for x in chi_xa):
            continue
        khoa = (_chu_doan(r['tuyen_duong']), _chu_doan(r.get('diem_dau')), _chu_doan(r.get('diem_cuoi')))
        db.setdefault(r['dia_ban'], {}).setdefault(khoa, []).append(r)
    kq = {}
    for xa, theo_khoa in db.items():
        doan = []
        for ds_r in theo_khoa.values():
            # cùng chữ tuyến + điểm đầu / cuối nhưng ở hai dải TT xa nhau (bảng con khác): hai đoạn, tách theo dải TT liên tiếp
            # hoặc hai đoạn liền nhau ghi cùng chữ (Hố Nai, Bắc Sơn - Long Thành TT 281-287 và 288-294): gặp lại một mã vị trí là đoạn mới
            vt_cua = {}
            for r in ds_r:
                if r.get('vi_tri'):
                    vt_cua.setdefault(int(r['tt']), r['vi_tri'])
            dai, hien, da_vt = {}, None, set()
            for t in sorted({int(r['tt']) for r in ds_r}):
                vt = vt_cua.get(t, '')
                if hien is None or t > hien[1] + 1 or (vt and vt in da_vt):
                    hien, da_vt = [t, t], set()
                hien[1] = t
                if vt:
                    da_vt.add(vt)
                dai[t] = hien
            cum = {}
            for r in ds_r:
                tt = int(r['tt'])
                bd, kt = dai[tt]
                d = cum.get(bd)
                if d is None:
                    d = cum[bd] = dict(ten_duong=r['tuyen_duong'], diem_dau=r.get('diem_dau', ''), diem_cuoi=r.get('diem_cuoi', ''),
                                       tt_bat_dau=bd, tt_ket_thuc=kt, co_quy_dinh_rieng_duong_dat_tai_pl1=False, _k={}, _tt_vt={})
                vt = r.get('vi_tri') or ''
                if vt:
                    d['_tt_vt'][vt] = min(tt, d['_tt_vt'].get(vt, tt))
                ld = r.get('loai_dat') or ''
                for c in (cot_co if not ld else he_so_k.NHOM_CHUNG.get(ld, (ld,))):     # dòng chung 'nn' / 'pnn' / trống: cho mọi nhóm thuộc nó
                    if c in cot_co:
                        d['_k'].setdefault(c, []).append((vt, str(r['he_so']), r))
            doan += cum.values()
        hang = []
        for d in sorted(doan, key=lambda x: (x['tt_bat_dau'], x['tt_ket_thuc'])):
            truoc = hang[-1] if hang else None
            if truoc is not None and _chu_doan(truoc['ten_duong']) == _chu_doan(d['ten_duong']) and d['tt_bat_dau'] <= truoc['tt_ket_thuc']:
                truoc['tt_ket_thuc'] = max(truoc['tt_ket_thuc'], d['tt_ket_thuc'])           # cùng tuyến, chồng TT: một đoạn ghi hai kiểu chữ
                for c, ds_k in d['_k'].items():
                    truoc['_k'].setdefault(c, []).extend(ds_k)
                for vt, t in d['_tt_vt'].items():
                    truoc['_tt_vt'][vt] = min(t, truoc['_tt_vt'].get(vt, t))
                continue
            hang.append(d)
        ra = []
        for d in hang:
            theo_vt = {}
            for c, ds_k in d.pop('_k').items():
                gia_tri = {}
                for vt, hs, r in ds_k:
                    if vt in gia_tri and Decimal(gia_tri[vt]) != Decimal(hs):
                        raise LoiGoi(f'{xa}, {d["ten_duong"]}, TT {r["tt"]}: hệ số K của {c} ở vị trí {vt or "(mọi vị trí)"} ghi hai số khác nhau '
                                     f'({gia_tri[vt]}; {hs}). Sửa bảng hệ số K rồi tạo lại gói.')
                    gia_tri[vt] = hs
                thu_tu = sorted(gia_tri, key=lambda v: d['_tt_vt'].get(v, 0) if v else -1)
                goc_k = gia_tri[thu_tu[0]]
                d['k1_' + c] = goc_k
                for vt in thu_tu[1:]:
                    if vt and Decimal(gia_tri[vt]) != Decimal(goc_k):
                        theo_vt.setdefault(vt, {})['k1_' + c] = gia_tri[vt]
            d.pop('_tt_vt')
            if theo_vt:
                d['k1_theo_vt'] = theo_vt
            if any(k.startswith('k1_') for k in d):
                ra.append(d)
        for i, d in enumerate(ra, 1):
            d['ma_doan_duong'] = f'{re.sub(r"[^A-Za-z0-9]+", "_", _khong_dau(xa))}_DOAN_{i:02d}'
        if ra:
            kq[xa] = ra
    if not kq:
        raise LoiGoi('Bảng hệ số K đang dùng không có dòng theo đoạn đường (TT, tuyến đường).')
    g['dia_ban'] = kq
    return g


def _khong_dau(s: str) -> str:
    from .lap_pa import bo_dau
    return bo_dau(s)


def _chu_doan(s) -> str:
    """Chữ tên đường / điểm đầu / điểm cuối để so: bỏ dấu, bỏ dấu câu và khoảng trắng thừa ("số 9," = "số 9.")."""
    return ' '.join(re.sub(r'[^a-z0-9]+', ' ', _khong_dau(s or '')).split())


def gop_doan_trung(g: dict) -> dict:
    """Gói đã xuất trước 1.0.90 (hoặc gói ngoài) có đoạn đường bị tách đôi: CÙNG tuyến, CÙNG số TT đầu (một nửa mang K1 đất phi nông
    nghiệp, nửa kia K1 đất nông nghiệp). Gộp hai nửa thành một đoạn (giữ mã đoạn của nửa đầu - dự án đã áp có thể nhắc mã đó) để
    nhập lại được. Hai nửa có cùng cột K1 mà khác số: không gộp, kiem_goi báo lỗi. Trả bản chép; không phải gói: trả nguyên."""
    if not isinstance(g, dict) or not isinstance(g.get('dia_ban'), dict):
        return g
    moi_db, doi = {}, False
    for k, ds in g['dia_ban'].items():
        if not isinstance(ds, list) or not all(isinstance(r, dict) and _la_int(r.get('tt_bat_dau'), 1, 10 ** 6) for r in ds):
            moi_db[k] = ds
            continue
        hang = []
        for r in ds:
            truoc = hang[-1] if hang else None
            if (truoc is not None and truoc['tt_bat_dau'] == r['tt_bat_dau']
                    and _chu_doan(truoc.get('ten_duong')) == _chu_doan(r.get('ten_duong'))):
                k1 = [c for c in r if c.startswith('k1_') and c != 'k1_theo_vt']
                if all(c not in truoc or str(truoc[c]) == str(r[c]) for c in k1):
                    for c in k1:
                        truoc.setdefault(c, r[c])
                    if _la_int(r.get('tt_ket_thuc'), 1, 10 ** 6) and _la_int(truoc.get('tt_ket_thuc'), 1, 10 ** 6):
                        truoc['tt_ket_thuc'] = max(truoc['tt_ket_thuc'], r['tt_ket_thuc'])
                    if isinstance(r.get('k1_theo_vt'), dict):
                        tv = truoc.setdefault('k1_theo_vt', {})
                        for vt, hs in r['k1_theo_vt'].items():
                            if isinstance(hs, dict):
                                tv.setdefault(vt, {}).update({c: x for c, x in hs.items() if c not in tv.get(vt, {})})
                    truoc['co_quy_dinh_rieng_duong_dat_tai_pl1'] = bool(truoc.get('co_quy_dinh_rieng_duong_dat_tai_pl1')
                                                                        or r.get('co_quy_dinh_rieng_duong_dat_tai_pl1'))
                    doi = True
                    continue
            hang.append(copy.deepcopy(r))
        moi_db[k] = hang
    if not doi:
        return g
    g = dict(g)
    g['dia_ban'] = moi_db
    return g


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


class DynamicRegulationEngine:
    """Động cơ quy tắc: một gói (mọi hệ số, yếu tố, công thức, làm tròn, câu chữ là dữ liệu JSON), không có quy tắc pháp lý trong mã. Lớp mỏng trên các hàm của module và gia_dat_qd03.tinh_don_gia.
    Mặc định gói gắn sẵn; tu_file nạp + kiểm gói .json mới."""

    def __init__(self, goi: dict | None = None):
        self.goi = goi or _gan_san()

    @classmethod
    def tu_ma(cls, ma: str):
        g = lay_goi(ma)
        if g is None:
            raise ValueError(f'Không có gói quy tắc {ma}.')
        return cls(g)

    @classmethod
    def tu_file(cls, file):
        return cls(doc_file_goi(file))

    def tra_doan(self, xa: str, ma_doan: str):
        from . import gia_dat_qd03 as g
        return g.tim_doan(g.dia_ban_theo_ten(xa, self.goi), ma_doan, self.goi)

    def tinh(self, dau_vao, doan: dict | None = None):
        from . import gia_dat_qd03 as g
        return g.tinh_don_gia(dau_vao, doan, self.goi)

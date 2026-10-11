"""Quản lý hồ sơ trình phương án: đợt trình (thư mục "Đợt 1 - 25 hộ" chứa PA chi tiết từng hộ + bảng tổng hợp), thư mục hồ sơ
dự án, lưu file dự án sang chỗ khác, trạng thái xử lý từng hộ (phê duyệt, chi trả, bàn giao mặt bằng, ghi chú theo dõi), nhập
quyết định / danh sách chi trả từ file (Excel, Word, PDF, CSV) và báo cáo tổng hợp theo bộ lọc.

Không phụ thuộc Qt (màn hình ở man_hinh_quan_ly.py).
"""
from __future__ import annotations

import functools
import re
import shutil
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from . import csdl
from .lap_pa import LoiNhap, bo_dau
from .pdf_bang import loai_cot
from .nghiep_vu import muc_5_cot
from .tien import D, KHONG, chuoi, doc_so_vn, vn

# ---------------------------------------------------------------- trạng thái xử lý
TRANG_THAI = [            # (khóa lọc, nhãn)
    ('chua_pa', 'Chưa lập phương án'), ('co_pa', 'Đã lập phương án'),
    ('chua_dot', 'Chưa xếp đợt trình'), ('co_dot', 'Đã xếp đợt trình'),
    ('chua_pd', 'Chưa phê duyệt'), ('da_pd', 'Đã phê duyệt'),
    ('chua_ct', 'Đã phê duyệt, chưa chi trả'), ('da_ct', 'Đã chi trả'),
    ('chua_bg', 'Đã chi trả, chưa bàn giao'), ('da_bg', 'Đã bàn giao mặt bằng'),
    ('co_ghi_chu', 'Có ghi chú theo dõi'),
]
TRUONG_TT = ('da_phe_duyet', 'qd_so', 'qd_ngay', 'qd_so_tien', 'qd_file', 'da_chi_tra', 'chi_tra_ngay', 'chi_tra_so_tien',
             'da_ban_giao', 'ban_giao_ngay', 'theo_doi', 'ly_do_ban_giao', 'bien_ban_ban_giao')


def hop_trang_thai(h: dict, khoa: str) -> bool:
    """h: dict có tong, dot_id, da_phe_duyet, da_chi_tra, da_ban_giao, theo_doi."""
    co_pa = h.get('tong', KHONG) > 0
    return {
        'chua_pa': not co_pa, 'co_pa': co_pa,
        'chua_dot': not h.get('dot_id'), 'co_dot': bool(h.get('dot_id')),
        'chua_pd': not h.get('da_phe_duyet'), 'da_pd': bool(h.get('da_phe_duyet')),
        'chua_ct': bool(h.get('da_phe_duyet')) and not h.get('da_chi_tra'), 'da_ct': bool(h.get('da_chi_tra')),
        'chua_bg': bool(h.get('da_chi_tra')) and not h.get('da_ban_giao'), 'da_bg': bool(h.get('da_ban_giao')),
        'co_ghi_chu': bool((h.get('theo_doi') or '').strip()),
    }.get(khoa, True)


def chuan_ngay(text) -> str:
    """'5/3/2026', '05-03-2026', '2026-03-05', datetime -> '05/03/2026'; rỗng -> ''. Sai -> LoiNhap."""
    if text is None or str(text).strip() == '':
        return ''
    if isinstance(text, datetime):
        return text.strftime('%d/%m/%Y')
    s = str(text).strip()
    m = re.fullmatch(r'(\d{4})-(\d{1,2})-(\d{1,2})(?:[ T].*)?', s)
    if m:
        y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
    else:
        m = re.fullmatch(r'(\d{1,2})\s*[/.\-]\s*(\d{1,2})\s*[/.\-]\s*(\d{2,4})', s)
        if not m:
            raise LoiNhap(f'Ngày "{s}" không đúng dạng ngày/tháng/năm (ví dụ 05/03/2026).')
        d, mo, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
        if y < 100:
            y += 2000
    try:
        return datetime(y, mo, d).strftime('%d/%m/%Y')
    except ValueError as e:
        raise LoiNhap(f'Ngày "{s}" không có thật.') from e


def doc_trang_thai(con, ma_ho: int) -> dict:
    r = con.execute(f'SELECT ma_ho, {", ".join(TRUONG_TT)}, dot_id FROM ho WHERE ma_ho = ?', (ma_ho,)).fetchone()
    if r is None:
        raise KeyError(f'không có hộ mã {ma_ho}')
    return dict(r)


def cap_nhat_trang_thai(con, ds_ma_ho: list, gia_tri: dict) -> int:
    """Ghi các trường trạng thái có trong gia_tri cho các hộ (trường vắng mặt: giữ nguyên). Trả số hộ đã ghi."""
    gt = {}
    for k, v in gia_tri.items():
        if k not in TRUONG_TT:
            raise KeyError(k)
        if k.startswith('da_'):
            gt[k] = 1 if v else 0
        elif k.endswith('_ngay'):
            gt[k] = chuan_ngay(v)
        elif k.endswith('_so_tien'):
            gt[k] = chuoi(D(v)) if str(v or '').strip() else ''
        else:
            gt[k] = ' '.join(str(v or '').split()) if k != 'theo_doi' else str(v or '').strip()
    if not gt or not ds_ma_ho:
        return 0
    from .theo_doi import ghi_kieu_cu
    kieu_qd = ('da_phe_duyet', 'qd_so', 'qd_ngay', 'qd_so_tien', 'qd_file', 'da_chi_tra', 'chi_tra_ngay', 'chi_tra_so_tien')
    with csdl.giao_dich(con):
        for ma in ds_ma_ho:
            rieng = {k: v for k, v in gt.items() if k not in kieu_qd}
            x = {k: v for k, v in gt.items() if k in kieu_qd}
            if x:                                       # từ v10: phê duyệt, chi trả ghi theo quyết định (theo_doi)
                rieng.update(ghi_kieu_cu(con, ma, x))
            if rieng:
                con.execute(f'UPDATE ho SET {", ".join(k + " = ?" for k in rieng)} WHERE ma_ho = ?', (*rieng.values(), ma))
        csdl.ghi_nhat_ky(con, 'Cập nhật trạng thái hộ', f'{len(ds_ma_ho)} hộ: ' + ', '.join(f'{k}={v}' for k, v in gt.items())[:400])
    return len(ds_ma_ho)


# ---------------------------------------------------------------- đợt trình
LOAI_VAN_BAN = ('Tờ trình', 'Văn bản')            # văn bản trình phê duyệt của đợt (gõ được loại khác)


@dataclass
class Dot:
    id: int
    so: int
    ten: str
    ngay_trinh: str = ''
    so_to_trinh: str = ''
    ghi_chu: str = ''
    thu_muc: str = ''
    so_ho: int = 0
    loai_van_ban: str = 'Tờ trình'      # v11: Tờ trình / Văn bản (số: so_to_trinh, ngày: ngay_trinh)
    so_pa_tong: str = ''                # v11: số / ngày phương án tổng của đợt (in vào bảng tổng hợp, mẫu PA tổng)
    ngay_pa_tong: str = ''

    @property
    def ten_thu_muc(self) -> str:
        return ten_thu_muc_dot(self.ten, self.so_ho)

    @property
    def van_ban_trinh(self) -> str:
        """'Tờ trình số 113/TTr-… ngày 10/10/2026' (trống nếu chưa có số / ngày)."""
        if not (self.so_to_trinh or self.ngay_trinh):
            return ''
        return ' '.join(x for x in (self.loai_van_ban or 'Tờ trình', f'số {self.so_to_trinh}' if self.so_to_trinh else '',
                                    f'ngày {self.ngay_trinh}' if self.ngay_trinh else '') if x)


def ten_thu_muc_dot(ten: str, so_ho: int) -> str:
    t = re.sub(r'[\\/:*?"<>|\r\n\t]+', ' ', ' '.join(str(ten or '').split())).strip() or 'Đợt'
    return f'{t} - {so_ho} hộ'


def ds_dot(con) -> list:
    dem = {r[0]: r[1] for r in con.execute('SELECT dot_id, COUNT(*) FROM ho WHERE dot_id IS NOT NULL GROUP BY dot_id')}
    kq = []
    for r in con.execute('SELECT * FROM dot_trinh ORDER BY so, id'):
        k = r.keys()                                     # file chỉ xem phiên bản cũ (v10) chưa có các cột v11
        kq.append(Dot(r['id'], r['so'], r['ten'], r['ngay_trinh'], r['so_to_trinh'], r['ghi_chu'], r['thu_muc'],
                      dem.get(r['id'], 0), (r['loai_van_ban'] if 'loai_van_ban' in k else '') or 'Tờ trình',
                      r['so_pa_tong'] if 'so_pa_tong' in k else '', r['ngay_pa_tong'] if 'ngay_pa_tong' in k else ''))
    return kq


def lay_dot(con, dot_id: int) -> Dot:
    for d in ds_dot(con):
        if d.id == dot_id:
            return d
    raise LoiNhap('Đợt trình không còn trong dự án.')


def _truong_dot(ngay_trinh, so_to_trinh, ghi_chu, loai_van_ban, so_pa_tong, ngay_pa_tong) -> tuple:
    """Chuẩn hóa các trường của đợt (ngày sai -> LoiNhap) theo thứ tự cột ghi."""
    return (chuan_ngay(ngay_trinh), ' '.join(str(so_to_trinh or '').split()), str(ghi_chu or '').strip(),
            ' '.join(str(loai_van_ban or '').split()) or 'Tờ trình', ' '.join(str(so_pa_tong or '').split()),
            chuan_ngay(ngay_pa_tong))


def tao_dot(con, ten: str = '', ngay_trinh: str = '', so_to_trinh: str = '', ghi_chu: str = '', loai_van_ban: str = 'Tờ trình',
            so_pa_tong: str = '', ngay_pa_tong: str = '') -> int:
    so = (con.execute('SELECT MAX(so) FROM dot_trinh').fetchone()[0] or 0) + 1
    ten = ' '.join(str(ten or '').split()) or f'Đợt {so}'
    if con.execute('SELECT 1 FROM dot_trinh WHERE ten = ?', (ten,)).fetchone():
        raise LoiNhap(f'Đã có đợt "{ten}".')
    gt = _truong_dot(ngay_trinh, so_to_trinh, ghi_chu, loai_van_ban, so_pa_tong, ngay_pa_tong)
    with csdl.giao_dich(con):
        cur = con.execute('''INSERT INTO dot_trinh (so, ten, ngay_trinh, so_to_trinh, ghi_chu, loai_van_ban, so_pa_tong,
                             ngay_pa_tong) VALUES (?,?,?,?,?,?,?,?)''', (so, ten, *gt))
        csdl.ghi_nhat_ky(con, 'Tạo đợt trình', ten)
    return cur.lastrowid


def sua_dot(con, dot_id: int, ten: str, ngay_trinh: str = '', so_to_trinh: str = '', ghi_chu: str = '',
            loai_van_ban: str = 'Tờ trình', so_pa_tong: str = '', ngay_pa_tong: str = '') -> None:
    ten = ' '.join(str(ten or '').split())
    if not ten:
        raise LoiNhap('Tên đợt không được để trống.')
    if con.execute('SELECT 1 FROM dot_trinh WHERE ten = ? AND id <> ?', (ten, dot_id)).fetchone():
        raise LoiNhap(f'Đã có đợt "{ten}".')
    gt = _truong_dot(ngay_trinh, so_to_trinh, ghi_chu, loai_van_ban, so_pa_tong, ngay_pa_tong)
    with csdl.giao_dich(con):
        con.execute('''UPDATE dot_trinh SET ten = ?, ngay_trinh = ?, so_to_trinh = ?, ghi_chu = ?, loai_van_ban = ?, so_pa_tong = ?,
                       ngay_pa_tong = ? WHERE id = ?''', (ten, *gt, dot_id))
        csdl.ghi_nhat_ky(con, 'Sửa đợt trình', ten)


# ---------------------------------------------------------------- số phương án chi tiết từng hộ (v11)
def so_pa_cua_ho(con, ds_ma_ho: list) -> dict:
    """{ma_ho: (số PA chi tiết, ngày)}."""
    chon = set(ds_ma_ho)
    try:
        return {r[0]: (r[1], r[2]) for r in con.execute('SELECT ma_ho, so_pa, ngay_pa FROM ho') if r[0] in chon}
    except sqlite3.OperationalError:                # file chỉ xem phiên bản cũ (v10): chưa có cột số phương án
        return {}


def dat_so_pa(con, ds: list) -> int:
    """Ghi số / ngày phương án chi tiết: ds = [(ma_ho, số, ngày)] (ngày sai -> LoiNhap, không ghi gì). Trả số hộ."""
    gt = [(' '.join(str(so or '').split()), chuan_ngay(ngay), m) for m, so, ngay in ds]
    if not gt:
        return 0
    with csdl.giao_dich(con):
        for so, ngay, m in gt:
            con.execute('UPDATE ho SET so_pa = ?, ngay_pa = ? WHERE ma_ho = ?', (so, ngay, m))
        csdl.ghi_nhat_ky(con, 'Số phương án chi tiết', '; '.join(f'hộ {m}: {so} {ngay}'.strip() for so, ngay, m in gt)[:400])
    return len(gt)


def danh_so_pa(con, ds_ma_ho: list, bat_dau, ngay: str = '', chi_ho_chua_co: bool = False, so_chu_so: int = 0) -> list:
    """Đánh số phương án chi tiết liên tục cho các hộ (theo thứ tự đưa vào): bat_dau, bat_dau+1...; so_chu_so: thêm số 0 phía
    trước (2 -> 01, 02...). chi_ho_chua_co: hộ đã có số giữ nguyên (không tính vào dãy). Trả [(ma_ho, số, ngày)] đã ghi."""
    try:
        n = int(str(bat_dau).strip())
    except ValueError:
        raise LoiNhap(f'Số bắt đầu "{bat_dau}" phải là số nguyên.') from None
    if n < 0:
        raise LoiNhap('Số bắt đầu không được âm.')
    co = so_pa_cua_ho(con, ds_ma_ho)
    ds = []
    for m in ds_ma_ho:
        if chi_ho_chua_co and (co.get(m) or ('', ''))[0]:
            continue
        ds.append((m, str(n).zfill(max(0, int(so_chu_so or 0))), ngay))
        n += 1
    dat_so_pa(con, ds)
    return [(m, so, chuan_ngay(ng)) for m, so, ng in ds]


def xoa_dot(con, dot_id: int) -> int:
    """Xóa đợt; các hộ của đợt trở về "chưa xếp đợt" (hồ sơ, thư mục đã xuất giữ nguyên). Trả số hộ được bỏ ra."""
    with csdl.giao_dich(con):
        n = con.execute('UPDATE ho SET dot_id = NULL WHERE dot_id = ?', (dot_id,)).rowcount
        con.execute('DELETE FROM dot_trinh WHERE id = ?', (dot_id,))
        csdl.ghi_nhat_ky(con, 'Xóa đợt trình', f'id {dot_id}, {n} hộ')
    return n


def gan_dot(con, ds_ma_ho: list, dot_id) -> int:
    """Đưa các hộ vào đợt (dot_id None: bỏ khỏi đợt). Trả số hộ."""
    if dot_id is not None and not con.execute('SELECT 1 FROM dot_trinh WHERE id = ?', (dot_id,)).fetchone():
        raise LoiNhap('Đợt trình không còn trong dự án.')
    with csdl.giao_dich(con):
        for ma in ds_ma_ho:
            con.execute('UPDATE ho SET dot_id = ? WHERE ma_ho = ?', (dot_id, ma))
        csdl.ghi_nhat_ky(con, 'Xếp đợt trình', f'{len(ds_ma_ho)} hộ -> đợt {dot_id}')
    return len(ds_ma_ho)


def ho_cua_dot(con, dot_id) -> list:
    """Mã hộ của đợt theo thứ tự hộ (dot_id None: các hộ chưa xếp đợt)."""
    if dot_id is None:
        return [r[0] for r in con.execute('SELECT ma_ho FROM ho WHERE dot_id IS NULL ORDER BY thu_tu, ma_ho')]
    return [r[0] for r in con.execute('SELECT ma_ho FROM ho WHERE dot_id = ? ORDER BY thu_tu, ma_ho', (dot_id,))]


# nhóm hộ đưa vào đợt trình (ô chọn của cửa sổ Đợt trình); 'chon' = hộ đang chọn ở danh sách (màn hình truyền vào)
NHOM_HO_DOT = [('da_lap', 'Hộ đã lập phương án, chưa xếp đợt'),
               ('gan_nhat', 'Hộ vừa lưu phương án gần nhất (cùng ngày lưu), chưa xếp đợt'),
               ('chua_xep', 'Mọi hộ chưa xếp đợt'),
               ('chua_duyet', 'Hộ đã trình đợt khác nhưng chưa phê duyệt (trình lại)'),
               ('chon', 'Hộ đang chọn ở danh sách hộ')]


def ho_theo_nhom(con, loai: str, dot_id=None) -> list:
    """Mã hộ (thứ tự hộ) của một nhóm NHOM_HO_DOT để đưa vào đợt dot_id ('chon' do màn hình tự lấy -> [])."""
    ho = con.execute('SELECT ma_ho, dot_id, luu_luc, da_phe_duyet FROM ho ORDER BY thu_tu, ma_ho').fetchall()
    if loai == 'chua_xep':
        return [h['ma_ho'] for h in ho if h['dot_id'] is None]
    if loai == 'da_lap':
        from .lap_pa import phan_loai_lap
        lap = phan_loai_lap(con)
        return [h['ma_ho'] for h in ho if h['dot_id'] is None and lap.get(h['ma_ho']) == 'da_lap']
    if loai == 'gan_nhat':
        ngay = max((str(h['luu_luc'])[:10] for h in ho if h['luu_luc'] and h['dot_id'] is None), default=None)
        return [h['ma_ho'] for h in ho if ngay and h['dot_id'] is None and str(h['luu_luc'] or '')[:10] == ngay]
    if loai == 'chua_duyet':
        return [h['ma_ho'] for h in ho if h['dot_id'] is not None and h['dot_id'] != dot_id and not h['da_phe_duyet']]
    return []


# ---------------------------------------------------------------- thư mục hồ sơ dự án
def thu_muc_ho_so(con, file_du_an=None) -> Path:
    """Thư mục gốc lưu hồ sơ trình (các thư mục đợt); mặc định: '<tên file dự án> - Hồ sơ PA' cạnh file .pabt."""
    tm = csdl.doc_cai_dat(con, 'THU_MUC_HO_SO', '')
    if tm:
        return Path(tm)
    if file_du_an:
        f = Path(file_du_an)
        return f.parent / f'{f.stem} - Hồ sơ PA'
    return Path.home() / 'Documents' / 'PABT - Hồ sơ PA'


def dat_thu_muc_ho_so(con, thu_muc) -> None:
    with csdl.giao_dich(con):
        csdl.ghi_cai_dat(con, 'THU_MUC_HO_SO', str(Path(thu_muc)))
        csdl.ghi_nhat_ky(con, 'Thư mục hồ sơ', str(thu_muc))


def _thu_muc_dot(goc: Path, dot: Dot) -> Path:
    """Thư mục của đợt trong thư mục gốc: dùng lại thư mục cũ của đợt (đổi tên theo số hộ mới) nếu có."""
    dich = goc / dot.ten_thu_muc
    cu = [p for p in goc.glob(f'{glob_an_toan(dot.ten)} - * hộ') if p.is_dir()] if goc.exists() else []
    if dot.thu_muc and Path(dot.thu_muc).is_dir() and Path(dot.thu_muc).parent == goc:
        cu.insert(0, Path(dot.thu_muc))
    for p in cu:
        if p != dich and not dich.exists():
            try:
                p.rename(dich)
            except OSError:
                return p                    # đang mở trong Explorer / Excel: ghi vào thư mục cũ
            break
    return dich


def glob_an_toan(s: str) -> str:
    return re.sub(r'([\[\]*?])', r'[\1]', s)


def xuat_dot(con, dot_id: int, goc, pdf: bool = False, bao_tien_do=None, bao_excel=None, chi_tiet: bool = True,
             bang_tong_hop: bool = True, to_trinh: bool = False, pa_tong: bool = False) -> dict:
    """Xuất hồ sơ một đợt: <gốc>/<Đợt N - k hộ>/PA CHI TIET/ (phương án chi tiết từng hộ, số PA chi tiết của hộ) + PA TONG/
    (bảng tổng hợp có số phương án tổng, tờ trình / văn bản trình, phương án tổng) (+ PDF). Trả dict của
    van_ban_trinh.xuat_bo_ho_so + thu_muc (thư mục đợt)."""
    from . import van_ban_trinh
    dot = lay_dot(con, dot_id)
    ds = ho_cua_dot(con, dot_id)
    if not ds:
        raise LoiNhap(f'{dot.ten} chưa có hộ nào.')
    goc = Path(goc)
    goc.mkdir(parents=True, exist_ok=True)
    tm = _thu_muc_dot(goc, dot)
    kq = van_ban_trinh.xuat_bo_ho_so(con, ds, tm, dot=dot, chi_tiet=chi_tiet, bang_tong_hop=bang_tong_hop, to_trinh=to_trinh,
                                     pa_tong=pa_tong, pdf=pdf, bao_tien_do=bao_tien_do, bao_excel=bao_excel)
    with csdl.giao_dich(con):
        con.execute('UPDATE dot_trinh SET thu_muc = ? WHERE id = ?', (str(tm), dot_id))
        csdl.ghi_nhat_ky(con, 'Xuất hồ sơ đợt', f'{dot.ten}: {len(ds)} hộ -> {tm}')
    kq['thu_muc'] = tm
    return kq


def luu_thanh(con, dich) -> Path:
    """Chép toàn bộ file dự án đang mở sang đường dẫn mới (SQLite backup, an toàn cả khi đang mở)."""
    dich = Path(dich)
    if dich.suffix.lower() != '.pabt':
        dich = dich.with_suffix('.pabt')
    dich.parent.mkdir(parents=True, exist_ok=True)
    tam = dich.with_name(dich.name + '.tam')
    if tam.exists():
        tam.unlink()
    moi = sqlite3.connect(str(tam))
    try:
        con.backup(moi)
    finally:
        moi.close()
    if dich.exists():
        dich.unlink()
    tam.rename(dich)
    return dich


# ---------------------------------------------------------------- nhập quyết định / danh sách chi trả từ file
LOAI_NHAP = {'pd': 'Quyết định phê duyệt phương án', 'ct': 'Danh sách chi trả', 'bg': 'Biên bản bàn giao mặt bằng'}


@dataclass
class DongKhop:
    ma_ho: int | None
    ho_ten: str
    so_tien: object = None              # Decimal hoặc None
    tong_pa: object = None
    so_qd: str = ''
    ngay: str = ''
    nguon: str = ''                     # dòng gốc trong file
    cach_khop: str = ''
    chon: bool = True
    chi_tiet: dict = field(default_factory=dict)      # tiền từng hạng mục trong file: tien_dat, tien_tai_san, tien_cay...

    @property
    def lech_tien(self) -> bool:
        return self.so_tien is not None and self.tong_pa is not None and self.so_tien != self.tong_pa


@dataclass
class KetQuaDocQD:
    so_qd: str = ''
    ngay: str = ''
    dong: list = field(default_factory=list)          # [DongKhop]
    khong_khop: list = field(default_factory=list)    # dòng có vẻ là hộ nhưng không tìm được


def _ten_chuan(s) -> str:
    s = bo_dau(s)
    s = re.sub(r'^(ong|ba|ho ong|ho ba|ho)\s+', '', s)
    return ' '.join(re.sub(r'[^a-z0-9 ]', ' ', s).split())


def _so_tien_trong(s: str):
    """Số tiền lớn nhất trong chuỗi (≥ 1.000), hoặc None."""
    best = None
    for m in re.finditer(r'\d{1,3}(?:[.,]\d{3})+(?![\d])|\d{4,}', s):
        t = m.group(0)
        if re.fullmatch(r'\d{1,2}/\d{1,2}/\d{4}', t) or re.fullmatch(r'(19|20)\d{2}', t):
            continue
        try:
            v = D(re.sub(r'[.,]', '', t))
        except ValueError:
            continue
        if v >= 1000 and (best is None or v > best):
            best = v
    return best


_RE_QD = re.compile(r'(?i)(?:quyết định|qđ)\s*(?:số)?\s*:?\s*(\d+[\w./-]*/[\w./-]*(?:QĐ|QD)[\w./-]*)')
_RE_NGAY = re.compile(r'(?i)ngày\s*(\d{1,2})\s*(?:/|-|tháng)\s*(\d{1,2})\s*(?:/|-|năm)\s*(\d{4})')


# số / ngày ở đầu quyết định: "Số: 123 /QĐ-UBND        Xã A, ngày 01 tháng 10 năm 2026"
_RE_SO_DAU = re.compile(r'(?i)\bS[ốo]\s*:\s*(\d+)\s*/\s*((?:QĐ|QD)[\w.Đđ-]*)')
# tiêu đề danh sách đính kèm: "(Kèm theo  (bản scan hay mất chữ K đầu) Quyết định số 456/QĐ-UBND ngày 25 tháng 12 năm 2024 của ...)"
_RE_KEM_THEO = re.compile(r'(?i)[èe]m\s+theo\s+quy[ếe]t\s+[đd][ịi]nh\s+s[ốo]\s*(\d+)\s*/\s*((?:QĐ|QD)[\w.Đđ-]*)\s*'
                          r'ng[àa]y\s*(\d{1,2})\s*(?:/|-|th[áa]ng)\s*(\d{1,2})\s*(?:/|-|n[ăa]m)\s*(\d{4})')


def _ngay(d, m, y) -> str:
    try:
        return chuan_ngay(f'{d}/{m}/{y}')
    except LoiNhap:
        return ''


def so_ngay_qd(toan_van: str) -> tuple:
    """(số quyết định, ngày ký) trong văn bản. Ưu tiên dòng "Số: …" ở đầu và ngày ký cùng dòng đó (không lấy nhầm ngày của
    các văn bản căn cứ); bản scan đầu trang bị dấu mộc che thì lấy ở tiêu đề danh sách "Kèm theo Quyết định số … ngày …"."""
    so = ngay = ''
    m = _RE_SO_DAU.search(toan_van)
    if m:
        so = f'{m.group(1)}/{m.group(2)}'.strip(' .,;')
        mn = _RE_NGAY.search(toan_van[m.end(): m.end() + 250])
        if mn:
            ngay = _ngay(*mn.groups())
    mk = _RE_KEM_THEO.search(toan_van)
    if mk:
        if not so or not re.fullmatch(r'\d+/(QĐ|QD)[\w.Đđ-]*', so):
            so = f'{mk.group(1)}/{mk.group(2)}'
        ngay = ngay or _ngay(*mk.groups()[2:])
    # còn thiếu: tìm ở phần đầu văn bản, trước các dòng "Căn cứ ..." (số, ngày ở đó là của văn bản khác)
    dau = re.split(r'(?im)^\W*c[ăa]n\s+c[ứu]\b', toan_van, maxsplit=1)[0]
    if not so:
        m = _RE_QD.search(dau)
        if m:
            so = m.group(1).strip(' .,;')
    if not ngay:
        m = _RE_NGAY.search(dau)
        if m:
            ngay = _ngay(*m.groups())
    return so, ngay


def doc_van_ban(file, bao_tien_do=None, cho=None) -> tuple:
    """Các dòng (danh sách ô) của file quyết định và cờ đã phải nhận dạng chữ (OCR). PDF ảnh scan / file ảnh: OCR."""
    from .nhap_don_gia import doc_bang
    from . import ocr
    p = Path(file)
    if p.suffix.lower() in ocr.DUOI_ANH:
        return [[x] for x in ocr.doc_chu(p, bao_tien_do, cho)], True
    try:
        dong = doc_bang(p)
        if p.suffix.lower() == '.pdf':
            from .pdf_bang import dien_so_ky
            dong = dien_so_ky(dong, p)                  # số, ngày đóng kèm chữ ký số (không nằm trong lớp chữ)
        return dong, False
    except LoiNhap:
        if p.suffix.lower() != '.pdf':
            raise
    try:
        return [[x] for x in ocr.doc_chu(p, bao_tien_do, cho)], True
    except ocr.DaHuy:
        raise
    except ocr.LoiOCR as e:
        raise LoiNhap(f'PDF là ảnh scan (không có lớp chữ). {e}') from e


def doc_quyet_dinh_nhieu(con, files, tong_pa: dict | None = None, bao_tien_do=None, cho=None) -> KetQuaDocQD:
    """Quyết định và bảng danh sách kèm theo ở nhiều file (thường: file quyết định + file bảng tổng hợp): số, ngày lấy ở
    file đầu tiên có; các hộ khớp gộp lại (một hộ chỉ lấy một lần)."""
    files = [files] if isinstance(files, (str, Path)) else list(files)
    kq = KetQuaDocQD()
    da = set()
    for f in files:
        dong, _ = doc_van_ban(f, bao_tien_do, cho)
        r = doc_quyet_dinh(con, f, tong_pa, dong)
        kq.so_qd = kq.so_qd or r.so_qd
        kq.ngay = kq.ngay or r.ngay
        for d in r.dong:
            if d.ma_ho not in da:
                da.add(d.ma_ho)
                kq.dong.append(d)
        kq.khong_khop += r.khong_khop
    for d in kq.dong:
        d.so_qd, d.ngay = d.so_qd or kq.so_qd, d.ngay or kq.ngay
    return kq


NGUONG_LOC = 0.86                                     # khop_ten: bỏ qua tên có cận trên tỉ lệ giống thấp hơn


@functools.lru_cache(maxsize=65536)
def _dem_ky_tu(s: str) -> dict:
    d = {}
    for c in s:
        d[c] = d.get(c, 0) + 1
    return d


def khop_ten(ten_file: str, ho: list, theo_ten: dict) -> tuple:
    """Hộ của dự án ứng với họ tên trong file (có thể ghi "Ông A; bà B", "… (nhận thừa kế của hộ ông C)"):
    (hộ, cách khớp) / (None, lý do). Trùng tên hoặc nhiều hộ cùng có trong ô: không tự chọn."""
    import difflib
    t = _ten_chuan(ten_file)
    if not t:
        return None, ''
    ung = theo_ten.get(t, [])
    if len(ung) == 1:
        return ung[0], 'họ tên'
    if len(ung) > 1:
        return None, f'trùng tên {len(ung)} hộ: chọn tay'
    bao = [x for k, ds in theo_ten.items() if len(k.split()) >= 2 and f' {k} ' in f' {t} ' for x in ds]
    if len(bao) == 1:
        return bao[0], 'họ tên (trong ô có nhiều người)'
    if len(bao) > 1:
        return None, f'ô có tên {len(bao)} hộ của dự án: chọn tay'
    # gần đúng: chỉ tính ratio() (chậm) cho tên có cận trên real_quick_ratio / quick_ratio >= NGUONG_LOC - tên thấp hơn không thể
    # là kết quả (cần >= 0,9) cũng không chặn kết quả (tên thứ hai chỉ chặn khi >= tốt nhất - 0,04 >= 0,86). 3.000 hộ: x50 nhanh hơn.
    diem = []
    lt = len(t)
    dem_t = _dem_ky_tu(t)
    for k in theo_ten:
        lk = len(k)
        # = real_quick_ratio(), tính thẳng từ độ dài - không dựng SequenceMatcher cho tên lệch độ dài
        if 2.0 * min(lt, lk) / (lt + lk) < NGUONG_LOC or len(k.split()) < 2:
            continue
        # = quick_ratio() (2 x số ký tự chung theo bội / tổng độ dài), bảng đếm ký tự của tên dự án nhớ lại giữa các dòng
        dem_k = _dem_ky_tu(k)
        if 2.0 * sum(min(n, dem_k.get(c, 0)) for c, n in dem_t.items()) / (lt + lk) >= NGUONG_LOC:
            diem.append((difflib.SequenceMatcher(None, t, k).ratio(), k))
    diem.sort(reverse=True)
    if diem and diem[0][0] >= 0.9 and (len(diem) == 1 or diem[1][0] < diem[0][0] - 0.04) and len(theo_ten[diem[0][1]]) == 1:
        return theo_ten[diem[0][1]][0], f'họ tên gần đúng ({round(diem[0][0] * 100)}%)'
    return None, ''


def _khop_bang(kq: KetQuaDocQD, bang: list, ho: list, theo_ten: dict, tong_pa) -> KetQuaDocQD:
    """Dòng bảng (pdf_bang.DongBang) -> DongKhop theo họ tên."""
    da = set()
    for r in bang:
        h, cach = khop_ten(r.ten, ho, theo_ten)
        nguon = f'STT {r.stt}: {r.ten}' + (f' - {r.dia_chi}' if r.dia_chi else '')
        if h is None or h['ma_ho'] in da:
            kq.khong_khop.append(nguon[:150] + (f'  ({cach})' if cach else ''))
            continue
        da.add(h['ma_ho'])
        tien = r.tien.get('so_tien')
        if tien is None:
            tien = sum((v for k, v in r.tien.items()), KHONG) or None
        d = DongKhop(h['ma_ho'], h['ho_ten'], tien, (tong_pa or {}).get(h['ma_ho']), kq.so_qd, kq.ngay, nguon[:200], cach,
                     chi_tiet={k: v for k, v in r.tien.items() if k != 'so_tien'})
        d.khop_tong = r.khop_tong
        kq.dong.append(d)
    thu_tu = {h['ma_ho']: h['thu_tu'] for h in ho}
    kq.dong.sort(key=lambda d: thu_tu.get(d.ma_ho, 0))
    return kq


def doc_quyet_dinh(con, file, tong_pa: dict | None = None, dong: list | None = None) -> KetQuaDocQD:
    """Đọc file quyết định / danh sách (xlsx, docx, pdf có chữ, csv): tìm số, ngày quyết định và khớp từng dòng với hộ
    (theo mã hộ, số CCCD, rồi họ tên không dấu). tong_pa: {mã hộ: tổng tiền phương án} để so số tiền.
    dong: các dòng đã đọc sẵn (doc_van_ban) thì không đọc lại file."""
    dong = doc_van_ban(file)[0] if dong is None else dong
    kq = KetQuaDocQD()
    toan_van = '\n'.join(' '.join(c for c in r if c) for r in dong)
    kq.so_qd, kq.ngay = so_ngay_qd(toan_van)
    ho = [dict(r) for r in con.execute('SELECT ma_ho, thu_tu, ho_ten, so_cccd, dia_chi FROM ho')]
    theo_ten = {}
    for h in ho:
        theo_ten.setdefault(_ten_chuan(h['ho_ten']), []).append(h)
    # PDF có lớp chữ (xuất từ Excel / Word) có bảng đánh số cột: tách bảng theo vị trí cột (họ tên nhiều dòng, tiền từng mục)
    if file is not None and Path(file).suffix.lower() == '.pdf':
        from .pdf_bang import doc_bang_pdf
        bang = doc_bang_pdf(file)
        if bang:
            return _khop_bang(kq, bang, ho, theo_ten, tong_pa)
    theo_cccd = {re.sub(r'\D', '', h['so_cccd']): h for h in ho if len(re.sub(r'\D', '', h['so_cccd'] or '')) >= 9}
    theo_ma = {h['ma_ho']: h for h in ho}
    # dòng tiêu đề: tìm cột họ tên, mã hộ, CCCD, số tiền, số QĐ, ngày
    cot = {}
    for r in dong[:60]:
        o = [bo_dau(c) for c in r]
        c_ten = next((i for i, t in enumerate(o) if re.search(r'ho (va )?ten|ten chu|chu su dung|ho gia dinh|ten ho', t)), None)
        if c_ten is not None and len(r) > 1:
            cot = dict(ten=c_ten,
                       ma=next((i for i, t in enumerate(o) if re.fullmatch(r'ma( ho)?|ma so ho', t.strip())), None),
                       cccd=next((i for i, t in enumerate(o) if re.search(r'cccd|cmnd|can cuoc|chung minh', t)), None),
                       tien=next((i for i, t in enumerate(o) if re.search(r'tong (cong|tien|kinh phi|so tien)|tong$', t)),
                                 next((i for i, t in enumerate(o) if re.search(r'so tien|thanh tien|kinh phi|gia tri', t)),
                                      None)),
                       # các cột tiền từng hạng mục (đất, nhà / vật kiến trúc, cây, hỗ trợ, thưởng)
                       chi_tiet={i: k for i, k in ((i, loai_cot(t)) for i, t in enumerate(r))
                                 if k not in ('', 'dien_tich', 'so_tien')},
                       qd=next((i for i, t in enumerate(o) if re.search(r'so (qd|quyet dinh)|quyet dinh', t)), None),
                       ngay=next((i for i, t in enumerate(o) if re.search(r'^ngay|ngay (ky|qd|chi|ban giao)', t)), None))
            break
    da = set()
    for r in dong:
        text = ' '.join(c for c in r if c)
        if not text.strip():
            continue
        h, cach = None, ''
        if cot and len(r) > cot['ten']:
            if cot.get('ma') is not None and cot['ma'] < len(r) and re.fullmatch(r'\d+', r[cot['ma']].strip() or 'x'):
                h = theo_ma.get(int(r[cot['ma']].strip()))
                cach = 'mã hộ' if h else ''
            if h is None and cot.get('cccd') is not None and cot['cccd'] < len(r):
                h = theo_cccd.get(re.sub(r'\D', '', r[cot['cccd']]))
                cach = 'số CCCD' if h else ''
            if h is None:
                ung = theo_ten.get(_ten_chuan(r[cot['ten']]), [])
                if len(ung) == 1:
                    h, cach = ung[0], 'họ tên'
                elif len(ung) > 1:
                    kq.khong_khop.append(f'{text[:150]}  (trùng tên {len(ung)} hộ: chọn tay)')
                    continue
        if h is None:
            # văn bản không có bảng (PDF): CCCD trong dòng, hoặc họ tên đầy đủ (≥ 2 từ) xuất hiện trong dòng
            so = re.findall(r'\d{9,12}', text)
            h = next((theo_cccd[s] for s in so if s in theo_cccd), None)
            cach = 'số CCCD' if h else ''
            if h is None:
                t = ' ' + _ten_chuan(text) + ' '
                ung = [x for k, ds in theo_ten.items() if len(k.split()) >= 2 and f' {k} ' in t for x in ds]
                if len(ung) == 1:
                    h, cach = ung[0], 'họ tên'
                elif len(ung) > 1:
                    kq.khong_khop.append(f'{text[:150]}  (khớp nhiều hộ: chọn tay)')
                    continue
        if h is None:
            continue
        if h['ma_ho'] in da:
            continue
        da.add(h['ma_ho'])
        tien = None
        if cot and cot.get('tien') is not None and cot['tien'] < len(r):
            try:
                v = D(r[cot['tien']]) if r[cot['tien']].strip() else None
                tien = v if v is not None and v > 0 else None
            except ValueError:
                tien = None
        if tien is None:
            tien = _so_tien_trong(text)
        so_qd = r[cot['qd']].strip() if cot and cot.get('qd') is not None and cot['qd'] < len(r) else ''
        ngay = ''
        if cot and cot.get('ngay') is not None and cot['ngay'] < len(r):
            try:
                ngay = chuan_ngay(r[cot['ngay']])
            except LoiNhap:
                ngay = ''
        chi_tiet = {}
        for i, k in (cot.get('chi_tiet') or {}).items() if cot else ():
            if i < len(r) and i != cot.get('tien') and str(r[i]).strip() not in ('', '-'):
                try:
                    chi_tiet[k] = chi_tiet.get(k, KHONG) + doc_so_vn(str(r[i]).strip())
                except (ValueError, ArithmeticError):
                    pass
        kq.dong.append(DongKhop(h['ma_ho'], h['ho_ten'], tien, (tong_pa or {}).get(h['ma_ho']), so_qd or kq.so_qd,
                                ngay or kq.ngay, text[:200], cach, chi_tiet=chi_tiet))
    thu_tu = {}
    for h in ho:
        thu_tu.setdefault(h['ma_ho'], h['thu_tu'])
    kq.dong.sort(key=lambda d: thu_tu.get(d.ma_ho, 0))
    return kq


# ---------------------------------------------------------------- số tiền phê duyệt của một hộ từ file quyết định
# Dòng tổng của quyết định phê duyệt, ưu tiên từ trên xuống (so khớp trên chữ không dấu: chịu được lỗi dấu của bản scan).
_SO = r'(\d{1,3}(?:[.,]\d{3})+|\d+)'
_MAU_TONG = [
    r'tong cong gia tri boi thuong[^:\n]{0,80}:\s*' + _SO + r'\s*do?ng',
    r'kinh phi boi thuong, ho tro(?:, tai dinh cu)?\s*:\s*' + _SO + r'\s*do?ng',
    r'tong (?:cong )?kinh phi[^:\n]{0,120}:\s*' + _SO + r'\s*do?ng',
    r'tong so tien boi thuong[^:\n]{0,80}:\s*' + _SO + r'\s*do?ng',
    r'tong cong\s*:?\s*' + _SO + r'\s*do?ng',
]
_MAU_KHOAN = re.compile(r'^\s*-\s*[^:\n]{3,120}:\s*' + _SO + r'\s*do?ng', re.M)
_TIEN = re.compile(r'(?<![\d.,])\d{1,3}(?:[.,]\d{3}){2,}(?![\d.,])')
_SO_SCAN = re.compile(r'(?<!\d)\d[\d.,]{4,}\d(?!\d)')       # bản scan: dấu chấm phân cách hay mất / thừa / lệch chỗ


def _so_nguyen(t: str):
    return D(re.sub(r'[.,\s]', '', t))


def _cac_so_tien(dong: str, scan: bool) -> list:
    """Các số tiền (≥ 100.000 đ) trên một dòng, trái sang phải. Bản scan: bỏ mọi dấu phân cách (12.000000 = 12000000)."""
    ds = [_so_nguyen(x) for x in (_SO_SCAN if scan else _TIEN).findall(dong.replace('|', ' '))]
    return [x for x in ds if x >= 100000]


def _cong_khop(so: list) -> bool:
    """Số cuối là tổng của một dãy liền trước nó (các cột thành phần), ví dụ đất + nhà + cây + hỗ trợ + thưởng = tổng."""
    if len(so) < 2:
        return False
    t = KHONG
    for x in reversed(so[:-1]):
        t += x
        if t == so[-1]:
            return True
    return False


@dataclass
class KetQuaQDHo:
    so_qd: str = ''
    ngay: str = ''
    so_tien: object = None              # Decimal: số tiền phê duyệt của hộ (None: không xác định được)
    cach: str = ''                      # lấy từ đâu: 'dòng của hộ' / 'tổng quyết định (1 trường hợp)'
    chac_chan: bool = False             # đã kiểm tra chéo (cộng các khoản = tổng) - không chắc thì cần người xem lại
    nguon: str = ''                     # đoạn chữ trong file chứa số tiền
    tong_qd: object = None              # tổng giá trị bồi thường, hỗ trợ của cả quyết định
    tong_qd_khop: object = None         # True/False: các khoản thành phần cộng lại = tổng (None: không có khoản)
    so_truong_hop: int | None = None
    ocr: bool = False                   # bản scan, đã nhận dạng chữ
    chi_tiet: dict = field(default_factory=dict)       # tiền từng hạng mục của hộ (bảng đính kèm có các cột)
    ghi_chu: list = field(default_factory=list)


def _khong_dau(s: str) -> str:
    """Bỏ dấu, chữ thường, giữ nguyên độ dài và xuống dòng (vị trí trong chuỗi kết quả = vị trí trong chuỗi NFC gốc)."""
    import unicodedata
    return ''.join((''.join(x for x in unicodedata.normalize('NFD', c) if unicodedata.category(x) != 'Mn') or c)[:1]
                   .replace('đ', 'd').replace('Đ', 'D').lower() for c in s)


def so_truong_hop(toan_van: str):
    """Số trường hợp (hộ, tổ chức) của quyết định: "Tổng số trường hợp …: 20 hộ", "Tổng số 07 trường hợp", "(Đợt 02 - 01 trường
    hợp/ …)". Không lấy số của từng loại ("Bồi thường bổ sung: 01 trường hợp")."""
    k = bo_dau(toan_van)
    for mau in (r'tong so (?:truong hop|ho)[^:\n]{0,80}:\s*(\d+)', r'tong so\s+(\d+)\s*(?:truong hop|ho)',
                r'dot\s*\d+\s*-\s*(\d+)\s*truong hop', r'(\d+)\s*truong hop'):
        m = re.search(mau, k)
        if m:
            return int(m.group(1))
    return None


def _tong_quyet_dinh(toan_van: str) -> tuple:
    """(tổng tiền, đoạn chữ, các khoản cộng có khớp tổng không) của dòng tổng trong quyết định."""
    import unicodedata
    toan_van = unicodedata.normalize('NFC', toan_van)
    k = _khong_dau(toan_van)
    for mau in _MAU_TONG:
        ds = list(re.finditer(mau, k, re.S))
        if not ds:
            continue
        m = ds[-1] if 'tong cong gia tri' in mau else ds[0]
        tong = _so_nguyen(m.group(1))
        sau = k[m.end(): m.end() + 1200]
        doan = re.split(r'\n\s*(?:\d+(?:\.\d+)*\.\s|trong do|\(dinh kem)', sau, maxsplit=1)[0]
        khoan = [_so_nguyen(x.group(1)) for x in _MAU_KHOAN.finditer(doan)]
        khop = (sum(khoan, KHONG) == tong) if khoan else None
        return tong, ' '.join(toan_van[m.start():m.end()].split())[:200], khop
    return None, '', None


def _tim_dong_ho(dong_chu: list, ten: str) -> tuple:
    """Bảng danh sách đọc từ bản scan: tên trong ô thường bị ngắt 2-3 dòng, chữ có lỗi nhận dạng. So từng từ của họ tên
    (gần đúng) trên cửa sổ 3 dòng; tên gọi (từ cuối) phải khớp gần như đúng cả từ. Trả (chỉ số dòng, độ khớp) hoặc (None, 0)."""
    import difflib
    tu = _ten_chuan(ten).split()
    if not tu:
        return None, 0
    def giong(w: str, cua_so: set, ca_tu: bool) -> float:
        tot = max((difflib.SequenceMatcher(None, w, x).ratio() for x in cua_so), default=0)
        if not ca_tu and len(w) >= 3:           # chữ dính liền khi scan ("PhạmThị"): so với một đoạn của từ dài hơn
            for x in cua_so:
                for j in range(len(x) - len(w) + 1 if len(x) > len(w) else 0):
                    tot = max(tot, 0.98 * difflib.SequenceMatcher(None, w, x[j:j + len(w)]).ratio())
        return tot
    tot, vt = 0.0, None
    for i in range(len(dong_chu)):
        cua_so = set(_ten_chuan(' '.join(dong_chu[max(0, i - 1): i + 2])).split())
        diem = [giong(w, cua_so, j == len(tu) - 1) for j, w in enumerate(tu)]
        if diem[-1] >= 0.95 and sum(diem) / len(diem) > tot:
            tot, vt = sum(diem) / len(diem), i
    return (vt, tot) if tot >= 0.9 else (None, 0)


def _tien_dong(dong_chu: list, vt: int) -> tuple:
    """Số tiền 'tổng cộng' của hộ quanh dòng vt: số cuối cùng trên dòng có nhiều số tiền nhất; chắc chắn khi các số đứng
    trước nó trên dòng cộng lại đúng bằng nó."""
    ung = []
    for d in dong_chu[max(0, vt - 3): vt + 4]:
        so = _cac_so_tien(d, True)
        if so:
            ung.append((_cong_khop(so), len(so), so, d))
    if not ung:
        return None, False, ''
    khop, _, so, d = max(ung, key=lambda x: (x[0], x[1]))
    return so[-1], khop, d


def doc_qd_mot_ho(con, file, ma_ho: int, tong_pa=None, bao_tien_do=None, cho=None) -> KetQuaQDHo:
    """Đọc file quyết định phê duyệt (PDF có chữ / scan, Word, Excel, ảnh) cho một hộ: số, ngày quyết định và số tiền phê
    duyệt của hộ - lấy ở dòng của hộ trong danh sách đính kèm; quyết định chỉ có 1 trường hợp thì lấy tổng quyết định.
    tong_pa: tổng phương án của hộ để so. Không ghi gì vào CSDL (người dùng xác nhận rồi mới lưu).
    file: một file hoặc danh sách file (file quyết định + file bảng tổng hợp kèm theo)."""
    files = [file] if isinstance(file, (str, Path)) else list(file)
    tai = [(f, *doc_van_ban(f, bao_tien_do, cho)) for f in files]
    dong = [r for _, d, _ in tai for r in d]
    la_ocr = any(o for _, _, o in tai)
    kq = KetQuaQDHo(ocr=la_ocr)
    nguon_tong = ''
    for _, d, _ in tai:
        tv = '\n'.join(' '.join(c for c in r if c) for r in d)
        so, ng = so_ngay_qd(tv)
        kq.so_qd, kq.ngay = kq.so_qd or so, kq.ngay or ng
        if kq.tong_qd is None:
            kq.tong_qd, nguon_tong, kq.tong_qd_khop = _tong_quyet_dinh(tv)
            if kq.tong_qd is not None:
                kq.so_truong_hop = so_truong_hop(tv)
    if kq.so_truong_hop is None:
        kq.so_truong_hop = so_truong_hop('\n'.join(' '.join(c for c in r if c) for r in dong))
    h = con.execute('SELECT ho_ten FROM ho WHERE ma_ho = ?', (ma_ho,)).fetchone()
    ten = h['ho_ten'] if h else ''
    # 1. dòng của hộ trong bảng / danh sách (cột số tiền, hoặc số tiền lớn nhất trên dòng)
    ds_khop = [d for f, dd, _ in tai for d in doc_quyet_dinh(con, f, {ma_ho: tong_pa} if tong_pa is not None else None, dd).dong]
    for d in ds_khop:
        if d.ma_ho == ma_ho and d.so_tien is not None:
            kq.so_tien, kq.cach, kq.nguon = D(d.so_tien), f'dòng của hộ trong danh sách (khớp theo {d.cach_khop})', d.nguon
            kq.chi_tiet = dict(d.chi_tiet)
            khop = getattr(d, 'khop_tong', None)
            kq.chac_chan = bool(khop) if khop is not None else (not la_ocr or _cong_khop(_cac_so_tien(d.nguon, True)))
            break
    # 2. bản scan: họ tên bị ngắt dòng / sai dấu -> so gần đúng
    if kq.so_tien is None and la_ocr and ten:
        dong_chu = [' '.join(c for c in r if c) for r in dong]
        vt, diem = _tim_dong_ho(dong_chu, ten)
        if vt is not None:
            tien, chac, d = _tien_dong(dong_chu, vt)
            if tien is not None:
                kq.so_tien, kq.chac_chan, kq.nguon = tien, chac, d
                kq.cach = f'dòng của hộ trong danh sách (bản scan, tên khớp {round(diem * 100)}%)'
    # 3. quyết định chỉ có một trường hợp (và không có bảng nhiều hộ): số tiền của hộ = tổng quyết định
    if kq.so_tien is None and kq.tong_qd is not None and kq.so_truong_hop == 1 and len(ds_khop) <= 1:
        kq.so_tien, kq.cach, kq.nguon = kq.tong_qd, 'tổng quyết định (quyết định 1 trường hợp)', nguon_tong
        kq.chac_chan = kq.tong_qd_khop is not False and not la_ocr or bool(kq.tong_qd_khop)
    if kq.so_tien is None:
        if kq.tong_qd is not None:
            kq.ghi_chu.append(f'Không tìm thấy dòng của hộ "{ten}" trong danh sách đính kèm. Tổng quyết định '
                              f'{vn(kq.tong_qd)} đ' + (f' cho {kq.so_truong_hop} trường hợp' if kq.so_truong_hop else '') +
                              (': chọn thêm file bảng tổng hợp kèm theo quyết định (chọn cùng lúc 2 file), hoặc nhập số tiền '
                               'của hộ bằng tay.' if not ds_khop else ': nhập số tiền của hộ bằng tay.'))
        else:
            kq.ghi_chu.append('Không tìm thấy số tiền phê duyệt trong file: nhập bằng tay.')
    elif not kq.chac_chan:
        kq.ghi_chu.append('Số tiền đọc từ bản scan, các cột thành phần cộng lại chưa khớp (chữ mờ / dấu mộc): '
                          'đối chiếu với văn bản trước khi lưu.' if la_ocr else
                          'Chưa kiểm tra chéo được số tiền: đối chiếu với văn bản trước khi lưu.')
    if kq.so_tien is not None and tong_pa is not None and D(kq.so_tien) != D(tong_pa):
        kq.ghi_chu.append(f'Số tiền trong quyết định khác tổng phương án hiện tại ({vn(tong_pa)} đ).')
    if kq.tong_qd_khop is False:
        kq.ghi_chu.append('Các khoản thành phần của quyết định cộng lại không bằng dòng tổng: kiểm tra lại văn bản.')
    return kq


def ap_quyet_dinh(con, loai: str, ds: list, so_qd: str = '', ngay: str = '', file_goc=None, thu_muc_luu=None) -> dict:
    """Ghi trạng thái cho các dòng đã chọn. loai: 'pd' phê duyệt / 'ct' chi trả / 'bg' bàn giao.
    Số QĐ / ngày chung dùng khi dòng không có riêng. file_goc + thu_muc_luu: chép file quyết định vào hồ sơ dự án."""
    if loai not in LOAI_NHAP:
        raise KeyError(loai)
    ngay = chuan_ngay(ngay)
    luu = ''
    ds_file = [f for f in (file_goc if isinstance(file_goc, (list, tuple)) else [file_goc]) if f]
    file_goc = ds_file[0] if ds_file else None                  # nhiều file (quyết định + bảng kèm theo): ghi file đầu
    if ds_file and thu_muc_luu:
        tm = Path(thu_muc_luu) / {'pd': 'Quyết định phê duyệt', 'ct': 'Chi trả', 'bg': 'Bàn giao mặt bằng'}[loai]
        tm.mkdir(parents=True, exist_ok=True)
        for i, f in enumerate(ds_file):
            dich = tm / Path(f).name
            if Path(f).resolve() != dich.resolve():
                shutil.copy2(f, dich)
            if i == 0:
                luu = str(dich)
    with csdl.giao_dich(con):                           # cả lô một giao dịch, một lần ghi đĩa
        return _ghi_ket_qua(con, loai, ds, so_qd, ngay, luu, file_goc)


def _ghi_ket_qua(con, loai, ds, so_qd, ngay, luu, file_goc) -> dict:
    from . import theo_doi
    chon = [d for d in ds if d.chon and d.ma_ho is not None]
    n = 0
    if loai == 'pd':
        # từ v10: mỗi số quyết định là một quyết định (một hộ có thể thuộc nhiều quyết định - phê duyệt bổ sung)
        nhom = {}
        for d in chon:
            nhom.setdefault((d.so_qd or so_qd, d.ngay or ngay), []).append(d)
        qd_id = None
        for (so, ng), ds_ho in nhom.items():
            if so:
                kq = theo_doi.nhap_tu_ket_qua(con, so, ng, ds_ho, luu or file_goc or '')
                n += kq['so_ho']
                qd_id = kq['qd_id']
                continue
            for d in ds_ho:                         # không có số quyết định: ghi kiểu cũ (tóm tắt trên hộ)
                gt = dict(da_phe_duyet=True, qd_ngay=ng, qd_so_tien=d.so_tien if d.so_tien is not None else (d.tong_pa or ''))
                if luu or file_goc:
                    gt['qd_file'] = luu or str(file_goc)
                cap_nhat_trang_thai(con, [d.ma_ho], gt)
                n += 1
        return dict(so_ho=n, file_luu=luu, qd_id=qd_id)
    for d in chon:
        ng = d.ngay or ngay
        if loai == 'ct':
            qd = [x for x in theo_doi.doc_qd_ho(con, d.ma_ho) if not x['da_chi_tra']]
            so = d.so_qd or so_qd
            if so:
                qd = [x for x in qd if theo_doi._khoa_so(x['so_qd']) == theo_doi._khoa_so(so)] or qd
            if d.so_tien is not None and len(qd) > 1:   # nhiều quyết định chưa nhận: lấy quyết định đúng số tiền
                qd = [x for x in qd if str(x['so_tien']).strip() and D(x['so_tien']) == d.so_tien] or qd
            if qd:
                with csdl.giao_dich(con):
                    for x in qd:
                        theo_doi.ghi_qd_ho(con, x['qd_id'], d.ma_ho, dict(
                            da_chi_tra=1, chi_tra_ngay=ng, chung_tu=luu or (str(file_goc) if file_goc else x['chung_tu']),
                            ly_do_chua_nhan='', chi_tra_so_tien=d.so_tien if d.so_tien is not None and len(qd) == 1
                            else (x['chi_tra_so_tien'] or x['so_tien'])))
            else:
                cap_nhat_trang_thai(con, [d.ma_ho], dict(da_chi_tra=True, chi_tra_ngay=ng, chi_tra_so_tien=d.so_tien
                                                          if d.so_tien is not None else (d.tong_pa or '')))
        else:
            gt = dict(da_ban_giao=True, ban_giao_ngay=ng)
            if luu or file_goc:
                gt['bien_ban_ban_giao'] = luu or str(file_goc)
            theo_doi.ghi_ban_giao(con, [d.ma_ho], gt)
        n += 1
    return dict(so_ho=n, file_luu=luu)


# ---------------------------------------------------------------- báo cáo tổng hợp
COT_BAO_CAO = ['STT', 'Mã hộ', 'Họ và tên', 'Địa chỉ', 'Đợt trình', 'Số thửa', 'DT thu hồi (m²)', '1. Đất', '2. Nhà, CT',
               '3. Cây trồng, vật nuôi', '4. Hỗ trợ', '5. Thưởng', 'TỔNG CỘNG', 'Phê duyệt (QĐ số, ngày)', 'Số tiền phê duyệt',
               'Chi trả (ngày)', 'Số tiền đã chi', 'Bàn giao MB (ngày)', 'Ghi chú theo dõi']


def du_lieu_tong_hop(con, ds_ma_ho: list | None = None) -> list:
    """Dòng báo cáo tổng hợp (dict) theo thứ tự hộ; ds_ma_ho None = mọi hộ."""
    from .nghiep_vu import ket_qua_ho
    kqh = ket_qua_ho(con)                               # kết quả dùng chung trên kết nối (không tính lại cả dự án)
    dot = {d.id: d.ten for d in ds_dot(con)}
    thua = {r[0]: (r[1], D(r[2] or 0)) for r in con.execute(
        'SELECT ma_ho, COUNT(*), SUM(CAST(dt_thu_hoi AS REAL)) FROM thua GROUP BY ma_ho')}
    chon = set(ds_ma_ho) if ds_ma_ho is not None else None
    kq = []
    for h in con.execute('SELECT * FROM ho ORDER BY thu_tu, ma_ho'):
        if chon is not None and h['ma_ho'] not in chon:
            continue
        k = kqh[h['ma_ho']][0]
        st, dt = thua.get(h['ma_ho'], (0, KHONG))
        kq.append(dict(ma_ho=h['ma_ho'], thu_tu=h['thu_tu'], ho_ten=h['ho_ten'], dia_chi=h['dia_chi'],
                       dot=dot.get(h['dot_id'], ''), dot_id=h['dot_id'], so_thua=st, dt=dt, muc=muc_5_cot(k.muc), tong=k.tong,
                       **{t: h[t] for t in TRUONG_TT}))
    return kq


def xuat_bao_cao_tong_hop(con, file_ra, ds_ma_ho: list | None = None, tieu_de: str = '', dieu_kien: str = '') -> Path:
    """Báo cáo tổng hợp (Excel): sheet danh sách hộ theo bộ lọc + sheet tổng hợp theo đợt và theo tiến độ."""
    return ghi_bao_cao_tong_hop(du_lieu_bao_cao(con, ds_ma_ho), file_ra, tieu_de, dieu_kien)


def du_lieu_bao_cao(con, ds_ma_ho: list | None = None) -> dict:
    """Số liệu của báo cáo tổng hợp (đọc CSDL - luồng giao diện); ghi_bao_cao_tong_hop chỉ ghi Excel (chạy nền được)."""
    da = con.execute('SELECT ten, cap_dia_ban, ten_dia_ban FROM du_an WHERE id = 1').fetchone()
    return dict(ds=du_lieu_tong_hop(con, ds_ma_ho), da=dict(da) if da else None,
                thu_tu_dot=[d.ten for d in ds_dot(con)] + ['(chưa xếp đợt)'])


def ghi_bao_cao_tong_hop(so_lieu: dict, file_ra, tieu_de: str = '', dieu_kien: str = '') -> Path:
    import openpyxl
    from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
    from openpyxl.utils import get_column_letter
    ds, da = so_lieu['ds'], so_lieu['da']
    xuong = Alignment(wrap_text=True, vertical='top')   # một đối tượng kiểu dùng chung (không tạo mới cho từng ô)
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = 'Danh sach'
    mong = Side(style='thin', color='808080')
    vien = Border(left=mong, right=mong, top=mong, bottom=mong)
    dam = Font(bold=True)
    nen = PatternFill('solid', fgColor='1F4E79')
    so_cot = len(COT_BAO_CAO)
    ws.cell(1, 1, tieu_de or 'BÁO CÁO TỔNG HỢP TIẾN ĐỘ BỒI THƯỜNG, HỖ TRỢ').font = Font(bold=True, size=14)
    ws.cell(2, 1, f'Dự án: {da["ten"] if da else ""}  -  {(da["cap_dia_ban"] + " " + da["ten_dia_ban"]) if da else ""}')
    ws.cell(3, 1, f'Điều kiện lọc: {dieu_kien or "tất cả hộ"}  -  lập lúc {datetime.now():%H:%M %d/%m/%Y}  -  {len(ds)} hộ')
    for i in (1, 2, 3):
        ws.merge_cells(start_row=i, start_column=1, end_row=i, end_column=so_cot)
    h0 = 5
    for c, t in enumerate(COT_BAO_CAO, start=1):
        o = ws.cell(h0, c, t)
        o.font = Font(bold=True, color='FFFFFF')
        o.fill = nen
        o.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
        o.border = vien
    so_fmt = '#,##0'
    tong = {'dt': KHONG, 'tong': KHONG, 'pd': KHONG, 'ct': KHONG, 1: KHONG, 2: KHONG, 3: KHONG, 4: KHONG, 5: KHONG}
    for i, x in enumerate(ds, start=1):
        r = h0 + i
        pd = (f'{x["qd_so"]}' + (f' ngày {x["qd_ngay"]}' if x['qd_ngay'] else '')) if x['da_phe_duyet'] else ''
        if x['da_phe_duyet'] and not pd:
            pd = 'Đã phê duyệt'
        gia = [i, x['ma_ho'], x['ho_ten'], x['dia_chi'], x['dot'], x['so_thua'], float(x['dt']),
               *(float(x['muc'][m]) for m in (1, 2, 3, 4, 5)), float(x['tong']), pd,
               float(D(x['qd_so_tien'])) if x['qd_so_tien'] else None,
               (x['chi_tra_ngay'] or 'Đã chi trả') if x['da_chi_tra'] else '',
               float(D(x['chi_tra_so_tien'])) if x['chi_tra_so_tien'] else None,
               (x['ban_giao_ngay'] or 'Đã bàn giao') if x['da_ban_giao'] else '', x['theo_doi']]
        for c, v in enumerate(gia, start=1):
            o = ws.cell(r, c, v)
            o.border = vien
            if isinstance(v, float):
                o.number_format = '#,##0.0' if c == 7 else so_fmt
            if c in (3, 4, 14, 19):
                o.alignment = xuong
        tong['dt'] += x['dt']
        tong['tong'] += x['tong']
        for m in (1, 2, 3, 4, 5):
            tong[m] += x['muc'][m]
        tong['pd'] += D(x['qd_so_tien'] or 0)
        tong['ct'] += D(x['chi_tra_so_tien'] or 0)
    r = h0 + len(ds) + 1
    ws.cell(r, 3, 'TỔNG CỘNG').font = dam
    for c, v in ((7, tong['dt']), (8, tong[1]), (9, tong[2]), (10, tong[3]), (11, tong[4]), (12, tong[5]), (13, tong['tong']),
                 (15, tong['pd']), (17, tong['ct'])):
        o = ws.cell(r, c, float(v))
        o.font = dam
        o.number_format = '#,##0.0' if c == 7 else so_fmt
    for c in range(1, so_cot + 1):
        ws.cell(r, c).border = vien
    from .tien import tien_bang_chu
    ws.cell(r + 1, 3, f'Bằng chữ (tổng cộng): {tien_bang_chu(tong["tong"])}.').font = Font(italic=True)
    for c, w in enumerate([6, 7, 26, 30, 14, 7, 11, 14, 14, 14, 14, 12, 16, 24, 15, 13, 15, 13, 34], start=1):
        ws.column_dimensions[get_column_letter(c)].width = w
    ws.freeze_panes = ws.cell(h0 + 1, 4)
    ws.auto_filter.ref = f'A{h0}:{get_column_letter(so_cot)}{h0 + len(ds)}'
    ws.page_setup.orientation = 'landscape'
    ws.page_setup.paperSize = ws.PAPERSIZE_A3
    ws.page_setup.fitToWidth = 1
    ws.page_setup.fitToHeight = 0
    ws.sheet_properties.pageSetUpPr.fitToPage = True
    ws.print_title_rows = f'{h0}:{h0}'
    # ---- tổng hợp theo đợt và theo tiến độ
    t2 = wb.create_sheet('Tong hop')
    t2.cell(1, 1, 'TỔNG HỢP THEO ĐỢT TRÌNH VÀ TIẾN ĐỘ').font = Font(bold=True, size=13)
    dau = ['Đợt trình', 'Số hộ', 'Tổng tiền phương án', 'Số hộ đã phê duyệt', 'Số tiền phê duyệt', 'Số hộ đã chi trả',
           'Số tiền đã chi', 'Số hộ đã bàn giao']
    for c, t in enumerate(dau, start=1):
        o = t2.cell(3, c, t)
        o.font = Font(bold=True, color='FFFFFF')
        o.fill = nen
        o.alignment = Alignment(horizontal='center', wrap_text=True)
        o.border = vien
    nhom = {}
    for x in ds:
        g = nhom.setdefault(x['dot'] or '(chưa xếp đợt)', [0, KHONG, 0, KHONG, 0, KHONG, 0])
        g[0] += 1
        g[1] += x['tong']
        if x['da_phe_duyet']:
            g[2] += 1
            g[3] += D(x['qd_so_tien'] or 0)
        if x['da_chi_tra']:
            g[4] += 1
            g[5] += D(x['chi_tra_so_tien'] or 0)
        if x['da_ban_giao']:
            g[6] += 1
    thu_tu = so_lieu['thu_tu_dot']
    r = 4
    cong = [0, KHONG, 0, KHONG, 0, KHONG, 0]
    for ten in thu_tu:
        if ten not in nhom:
            continue
        g = nhom[ten]
        for c, v in enumerate([ten] + g, start=1):
            o = t2.cell(r, c, float(v) if isinstance(v, type(KHONG)) else v)
            o.border = vien
            if c in (3, 5, 7):
                o.number_format = so_fmt
        cong = [a + b for a, b in zip(cong, g)]
        r += 1
    for c, v in enumerate(['CỘNG'] + cong, start=1):
        o = t2.cell(r, c, float(v) if isinstance(v, type(KHONG)) else v)
        o.font = dam
        o.border = vien
        if c in (3, 5, 7):
            o.number_format = so_fmt
    for c, w in enumerate([24, 9, 20, 14, 20, 14, 20, 14], start=1):
        t2.column_dimensions[get_column_letter(c)].width = w
    p = Path(file_ra)
    p.parent.mkdir(parents=True, exist_ok=True)
    wb.save(p)
    return p


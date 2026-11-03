r"""Làm việc qua máy chủ trong mạng nội bộ (LAN): tài khoản người dùng, dự án dùng chung, mang dự án về làm offline.

"Máy chủ" là một thư mục dùng chung trên máy chủ của đơn vị (ví dụ \\MAYCHU\PABT hoặc ổ mạng Z:\PABT) - không cần cài phần mềm
máy chủ riêng. Cấu trúc:
    <máy chủ>\pabt_may_chu.sqlite   tài khoản (mật khẩu băm PBKDF2), dự án gần đây của từng người, dự án đang lấy về, nhật ký
    <máy chủ>\DuAn\*.larc          các file dự án dùng chung (khóa nhiều máy bằng khoa.py như khi mở file bất kỳ)
    <máy chủ>\SaoLuu\               bản cũ được sao lưu trước khi ghi đè lúc đưa dự án offline lên lại
Không thiết lập máy chủ (hoặc máy chủ không truy cập được) thì phần mềm làm việc offline với file trên máy như trước.
Quyền đọc / ghi thư mục dùng chung do Windows cấp; đăng nhập trong phần mềm để biết ai làm việc gì và nối tiếp dự án ở máy bất kỳ.
Không phụ thuộc Qt (màn hình ở man_hinh_may_chu.py).
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
import secrets
import shutil
import sqlite3
import threading
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from . import csdl

TEN_CSDL = 'pabt_may_chu.sqlite'
THU_MUC_DU_AN = 'DuAn'
THU_MUC_SAO_LUU = 'SaoLuu'
LAP_BAM = 120000                       # số vòng PBKDF2-HMAC-SHA256
QUAN_TRI, NGUOI_DUNG = 'quan_tri', 'nguoi_dung'
TEN_VAI_TRO = {QUAN_TRI: 'Quản trị', NGUOI_DUNG: 'Người dùng (mọi việc lập phương án)'}
# 1.0.57: 6 vai trò nghiệp vụ (phan_quyen - đề án LARC V2.0); quản trị = quan_tri hoặc lãnh đạo
TEN_VAI_TRO.update({'lanh_dao': 'Lãnh đạo (phê duyệt, mở khóa)', 'tham_dinh': 'Thẩm định viên',
                    'chuyen_vien': 'Chuyên viên lập phương án', 'kiem_dem': 'Kiểm đếm viên', 'ke_toan': 'Kế toán chi trả',
                    'thanh_tra': 'Thanh tra, kiểm toán (chỉ xem)'})
VAI_TRO_QUAN_TRI = (QUAN_TRI, 'lanh_dao')

_LUOC_DO = '''
CREATE TABLE IF NOT EXISTS nguoi_dung (
    tai_khoan TEXT PRIMARY KEY, ho_ten TEXT NOT NULL DEFAULT '', chuc_vu TEXT NOT NULL DEFAULT '',
    vai_tro TEXT NOT NULL DEFAULT 'nguoi_dung', bam TEXT NOT NULL, muoi TEXT NOT NULL, khoa INTEGER NOT NULL DEFAULT 0,
    tao_luc TEXT NOT NULL DEFAULT '', dang_nhap_cuoi TEXT NOT NULL DEFAULT '', may_cuoi TEXT NOT NULL DEFAULT '',
    sai_lien_tiep INTEGER NOT NULL DEFAULT 0);
CREATE TABLE IF NOT EXISTS gan_day (
    tai_khoan TEXT NOT NULL, duong_dan TEXT NOT NULL, luc TEXT NOT NULL, PRIMARY KEY (tai_khoan, duong_dan));
CREATE TABLE IF NOT EXISTS lay_ve (
    duong_dan TEXT PRIMARY KEY, tai_khoan TEXT NOT NULL, may TEXT NOT NULL DEFAULT '', luc TEXT NOT NULL DEFAULT '',
    sua_goc REAL NOT NULL DEFAULT 0);
CREATE TABLE IF NOT EXISTS lay_ve_ho (
    duong_dan TEXT NOT NULL, ma_ho INTEGER NOT NULL, tai_khoan TEXT NOT NULL,
    may TEXT NOT NULL DEFAULT '', luc TEXT NOT NULL DEFAULT '',
    PRIMARY KEY (duong_dan, ma_ho));
CREATE TABLE IF NOT EXISTS nhat_ky (
    id INTEGER PRIMARY KEY, luc TEXT NOT NULL, tai_khoan TEXT NOT NULL DEFAULT '', may TEXT NOT NULL DEFAULT '',
    viec TEXT NOT NULL DEFAULT '', chi_tiet TEXT NOT NULL DEFAULT '');
CREATE TABLE IF NOT EXISTS thong_tin (ma TEXT PRIMARY KEY, gia_tri TEXT NOT NULL DEFAULT '');
'''


class LoiMayChu(Exception):
    pass


class LoiXungDot(LoiMayChu):
    """Gộp theo hộ: các hộ đã bị sửa trên máy chủ sau lúc nhận về. ds = [(mã hộ, họ tên)] để màn hình liệt kê và hỏi ghi đè."""

    def __init__(self, chu: str, ds: list):
        super().__init__(chu)
        self.ds = list(ds)


@dataclass
class Phien:
    """Phiên đăng nhập đang dùng."""
    goc: Path
    tai_khoan: str
    ho_ten: str
    vai_tro: str
    chuc_vu: str = ''

    @property
    def la_quan_tri(self) -> bool:
        return self.vai_tro in VAI_TRO_QUAN_TRI

    @property
    def ten_hien(self) -> str:
        return f'{self.ho_ten} ({self.tai_khoan})' if self.ho_ten else self.tai_khoan


PHIEN = None                            # Phien đang đăng nhập (None: làm việc offline / chưa đăng nhập)


def _bay_gio() -> str:
    return datetime.now().isoformat(timespec='seconds')


def _may() -> str:
    from .csdl import ten_may
    return ten_may()


# ---------------------------------------------------------------- cấu hình trên máy này
def thu_muc_may() -> Path:
    return Path(os.environ.get('PABT_THU_MUC_MAY') or Path(os.environ.get('APPDATA') or Path.home()) / 'PABT')


def _file_cau_hinh() -> Path:
    return thu_muc_may() / 'may_chu.json'


def doc_cau_hinh() -> dict:
    """{'may_chu': đường dẫn thư mục máy chủ, 'tai_khoan': tài khoản nhớ lần trước}."""
    try:
        return json.loads(_file_cau_hinh().read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return {}


def ghi_cau_hinh(**gt) -> dict:
    ch = doc_cau_hinh()
    ch.update({k: v for k, v in gt.items()})
    ch = {k: v for k, v in ch.items() if v not in (None, '')}
    f = _file_cau_hinh()
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(json.dumps(ch, ensure_ascii=False, indent=1), encoding='utf-8')
    return ch


# ---------------------------------------------------------------- máy chủ
def chuan_goc(goc) -> Path:
    s = str(goc or '').strip().strip('"')
    if not s:
        raise LoiMayChu('Chưa nhập đường dẫn thư mục máy chủ.')
    return Path(s)


def ket_noi_duoc(goc, cho: float = 4.0) -> bool:
    """Máy chủ có truy cập được không (kiểm tra trong luồng riêng: đường dẫn mạng không tới được có thể treo rất lâu)."""
    kq = []

    def thu():
        try:
            kq.append((Path(goc) / TEN_CSDL).is_file())
        except OSError:
            kq.append(False)
    t = threading.Thread(target=thu, daemon=True)
    t.start()
    t.join(cho)
    return bool(kq and kq[0])


def thu_muc_ton_tai(goc, cho: float = 4.0) -> bool:
    kq = []

    def thu():
        try:
            kq.append(Path(goc).is_dir())
        except OSError:
            kq.append(False)
    t = threading.Thread(target=thu, daemon=True)
    t.start()
    t.join(cho)
    return bool(kq and kq[0])


def _mo(goc) -> sqlite3.Connection:
    p = Path(goc) / TEN_CSDL
    if not p.is_file():
        raise LoiMayChu(f'Thư mục {goc} chưa được khởi tạo làm máy chủ PABT.')
    con = sqlite3.connect(str(p), timeout=15)
    con.row_factory = sqlite3.Row
    con.execute('PRAGMA journal_mode = DELETE')      # file trên thư mục mạng: không dùng WAL
    con.executescript(_LUOC_DO)
    return con


def _ghi_nhat_ky(con, tai_khoan: str, viec: str, chi_tiet: str = '') -> None:
    con.execute('INSERT INTO nhat_ky (luc, tai_khoan, may, viec, chi_tiet) VALUES (?,?,?,?,?)',
                (_bay_gio(), tai_khoan, _may(), viec, chi_tiet[:500]))


def bam_mat_khau(mat_khau: str, muoi: str | None = None) -> tuple:
    muoi = muoi or secrets.token_hex(16)
    bam = hashlib.pbkdf2_hmac('sha256', str(mat_khau).encode('utf-8'), bytes.fromhex(muoi), LAP_BAM).hex()
    return bam, muoi


def _kiem_mat_khau(mk: str) -> None:
    if len(str(mk or '')) < 6:
        raise LoiMayChu('Mật khẩu cần ít nhất 6 ký tự.')


def _kiem_tai_khoan(tk: str) -> str:
    tk = str(tk or '').strip().lower()
    if not re.fullmatch(r'[a-z0-9._-]{3,32}', tk):
        raise LoiMayChu('Tài khoản 3-32 ký tự, chỉ gồm chữ không dấu, số, dấu chấm, gạch dưới, gạch ngang (ví dụ: vinh.pt).')
    return tk


def khoi_tao(goc, tai_khoan: str, mat_khau: str, ho_ten: str = 'Quản trị hệ thống') -> Path:
    """Khởi tạo thư mục máy chủ mới với tài khoản quản trị đầu tiên."""
    goc = chuan_goc(goc)
    if (goc / TEN_CSDL).exists():
        raise LoiMayChu('Thư mục này đã là máy chủ LARC: chọn "Kết nối" thay vì khởi tạo.')
    tk = _kiem_tai_khoan(tai_khoan)
    _kiem_mat_khau(mat_khau)
    try:
        goc.mkdir(parents=True, exist_ok=True)
        (goc / THU_MUC_DU_AN).mkdir(exist_ok=True)
        (goc / THU_MUC_SAO_LUU).mkdir(exist_ok=True)
        con = sqlite3.connect(str(goc / TEN_CSDL))
    except OSError as e:
        raise LoiMayChu(f'Không tạo được thư mục máy chủ (kiểm tra quyền ghi thư mục dùng chung): {e}') from e
    con.executescript(_LUOC_DO)
    bam, muoi = bam_mat_khau(mat_khau)
    with con:
        con.execute('INSERT INTO nguoi_dung (tai_khoan, ho_ten, vai_tro, bam, muoi, tao_luc) VALUES (?,?,?,?,?,?)',
                    (tk, ho_ten.strip(), QUAN_TRI, bam, muoi, _bay_gio()))
        con.execute("INSERT OR REPLACE INTO thong_tin VALUES ('tao_luc', ?)", (_bay_gio(),))
        con.execute('INSERT INTO nhat_ky (luc, tai_khoan, may, viec) VALUES (?,?,?,?)', (_bay_gio(), tk, _may(), 'Khởi tạo máy chủ'))
    con.close()
    return goc


def dang_nhap(goc, tai_khoan: str, mat_khau: str) -> Phien:
    """Kiểm tra tài khoản; đúng thì đặt PHIEN và trả phiên. Sai 5 lần liền: tài khoản bị khóa (quản trị mở lại)."""
    global PHIEN
    goc = chuan_goc(goc)
    tk = str(tai_khoan or '').strip().lower()
    con = _mo(goc)
    try:
        r = con.execute('SELECT * FROM nguoi_dung WHERE tai_khoan = ?', (tk,)).fetchone()
        if r is None:
            raise LoiMayChu('Sai tài khoản hoặc mật khẩu.')
        if r['khoa']:
            raise LoiMayChu('Tài khoản đang bị khóa: liên hệ người quản trị.')
        bam, _ = bam_mat_khau(mat_khau, r['muoi'])
        if not hmac.compare_digest(bam, r['bam']):
            sai = r['sai_lien_tiep'] + 1
            with con:
                con.execute('UPDATE nguoi_dung SET sai_lien_tiep = ?, khoa = ? WHERE tai_khoan = ?', (sai, 1 if sai >= 5 else 0, tk))
                _ghi_nhat_ky(con, tk, 'Đăng nhập sai', f'lần {sai}')
            raise LoiMayChu('Sai tài khoản hoặc mật khẩu.' + (' Tài khoản đã bị khóa do nhập sai 5 lần.' if sai >= 5 else ''))
        with con:
            con.execute('UPDATE nguoi_dung SET sai_lien_tiep = 0, dang_nhap_cuoi = ?, may_cuoi = ? WHERE tai_khoan = ?',
                        (_bay_gio(), _may(), tk))
            _ghi_nhat_ky(con, tk, 'Đăng nhập')
        PHIEN = Phien(goc, tk, r['ho_ten'], r['vai_tro'], r['chuc_vu'])
    finally:
        con.close()
    _dat_nguoi_ghi(PHIEN)
    ghi_cau_hinh(may_chu=str(goc), tai_khoan=tk)
    return PHIEN


def dang_xuat() -> None:
    global PHIEN
    if PHIEN is not None:
        try:
            con = _mo(PHIEN.goc)
            with con:
                _ghi_nhat_ky(con, PHIEN.tai_khoan, 'Đăng xuất')
            con.close()
        except (LoiMayChu, sqlite3.Error, OSError):
            pass
    PHIEN = None
    _dat_nguoi_ghi(None)


def _dat_nguoi_ghi(phien) -> None:
    """Nhật ký file dự án và khóa file ghi tên người đăng nhập thay cho tài khoản Windows."""
    from . import csdl, khoa
    ten = phien.ten_hien if phien else None
    csdl.NGUOI_DUNG = ten
    khoa.NGUOI_DUNG = ten


def _can_quan_tri(phien) -> None:
    if phien is None or not phien.la_quan_tri:
        raise LoiMayChu('Chỉ tài khoản quản trị mới làm được việc này.')


# ---------------------------------------------------------------- tài khoản
def ds_nguoi_dung(goc) -> list:
    con = _mo(goc)
    try:
        return [dict(r) for r in con.execute('SELECT tai_khoan, ho_ten, chuc_vu, vai_tro, khoa, tao_luc, dang_nhap_cuoi, may_cuoi '
                                             'FROM nguoi_dung ORDER BY vai_tro DESC, tai_khoan')]
    finally:
        con.close()


def them_nguoi_dung(phien, tai_khoan: str, ho_ten: str, mat_khau: str, vai_tro: str = NGUOI_DUNG, chuc_vu: str = '') -> str:
    _can_quan_tri(phien)
    tk = _kiem_tai_khoan(tai_khoan)
    _kiem_mat_khau(mat_khau)
    if not str(ho_ten or '').strip():
        raise LoiMayChu('Nhập họ tên người dùng.')
    if vai_tro not in TEN_VAI_TRO:
        raise LoiMayChu('Vai trò không hợp lệ.')
    con = _mo(phien.goc)
    try:
        if con.execute('SELECT 1 FROM nguoi_dung WHERE tai_khoan = ?', (tk,)).fetchone():
            raise LoiMayChu(f'Đã có tài khoản "{tk}".')
        bam, muoi = bam_mat_khau(mat_khau)
        with con:
            con.execute('INSERT INTO nguoi_dung (tai_khoan, ho_ten, chuc_vu, vai_tro, bam, muoi, tao_luc) VALUES (?,?,?,?,?,?,?)',
                        (tk, ho_ten.strip(), chuc_vu.strip(), vai_tro, bam, muoi, _bay_gio()))
            _ghi_nhat_ky(con, phien.tai_khoan, 'Thêm tài khoản', tk)
    finally:
        con.close()
    return tk


def sua_nguoi_dung(phien, tai_khoan: str, ho_ten: str | None = None, chuc_vu: str | None = None, vai_tro: str | None = None,
                   khoa: bool | None = None) -> None:
    _can_quan_tri(phien)
    con = _mo(phien.goc)
    try:
        r = con.execute('SELECT * FROM nguoi_dung WHERE tai_khoan = ?', (tai_khoan,)).fetchone()
        if r is None:
            raise LoiMayChu(f'Không có tài khoản "{tai_khoan}".')
        if tai_khoan == phien.tai_khoan and (khoa or (vai_tro and vai_tro not in VAI_TRO_QUAN_TRI)):
            raise LoiMayChu('Không tự khóa hoặc bỏ quyền quản trị của chính mình.')
        gt = {}
        if ho_ten is not None:
            gt['ho_ten'] = ho_ten.strip()
        if chuc_vu is not None:
            gt['chuc_vu'] = chuc_vu.strip()
        if vai_tro is not None:
            if vai_tro not in TEN_VAI_TRO:
                raise LoiMayChu('Vai trò không hợp lệ.')
            gt['vai_tro'] = vai_tro
        if khoa is not None:
            gt['khoa'] = 1 if khoa else 0
            if not khoa:
                gt['sai_lien_tiep'] = 0
        if not gt:
            return
        with con:
            con.execute(f'UPDATE nguoi_dung SET {", ".join(k + " = ?" for k in gt)} WHERE tai_khoan = ?', (*gt.values(), tai_khoan))
            _ghi_nhat_ky(con, phien.tai_khoan, 'Sửa tài khoản', f'{tai_khoan}: {gt}')
    finally:
        con.close()


def dat_lai_mat_khau(phien, tai_khoan: str, mat_khau_moi: str) -> None:
    _can_quan_tri(phien)
    _kiem_mat_khau(mat_khau_moi)
    _doi_bam(phien, tai_khoan, mat_khau_moi, 'Đặt lại mật khẩu')


def doi_mat_khau(phien, mat_khau_cu: str, mat_khau_moi: str) -> None:
    if phien is None:
        raise LoiMayChu('Chưa đăng nhập.')
    _kiem_mat_khau(mat_khau_moi)
    con = _mo(phien.goc)
    try:
        r = con.execute('SELECT bam, muoi FROM nguoi_dung WHERE tai_khoan = ?', (phien.tai_khoan,)).fetchone()
    finally:
        con.close()
    if r is None or not hmac.compare_digest(bam_mat_khau(mat_khau_cu, r['muoi'])[0], r['bam']):
        raise LoiMayChu('Mật khẩu hiện tại không đúng.')
    _doi_bam(phien, phien.tai_khoan, mat_khau_moi, 'Đổi mật khẩu')


def _doi_bam(phien, tai_khoan, mk, viec):
    bam, muoi = bam_mat_khau(mk)
    con = _mo(phien.goc)
    try:
        with con:
            n = con.execute('UPDATE nguoi_dung SET bam = ?, muoi = ?, sai_lien_tiep = 0, khoa = 0 WHERE tai_khoan = ?',
                            (bam, muoi, tai_khoan)).rowcount
            if not n:
                raise LoiMayChu(f'Không có tài khoản "{tai_khoan}".')
            _ghi_nhat_ky(con, phien.tai_khoan, viec, tai_khoan)
    finally:
        con.close()


# ---------------------------------------------------------------- dự án trên máy chủ
def thu_muc_du_an(goc=None) -> Path:
    goc = Path(goc) if goc else (PHIEN.goc if PHIEN else None)
    if goc is None:
        raise LoiMayChu('Chưa đăng nhập máy chủ.')
    return goc / THU_MUC_DU_AN


def thu_muc_mac_dinh() -> Path:
    """Nơi đề xuất khi mở / lưu dự án: thư mục dự án trên máy chủ nếu đang đăng nhập, không thì Documents."""
    if PHIEN is not None:
        try:
            tm = thu_muc_du_an()
            if tm.is_dir():
                return tm
        except OSError:
            pass
    return Path.home() / 'Documents'


def _tuong_doi(goc: Path, file) -> str:
    """Đường dẫn lưu trên máy chủ: tương đối với thư mục máy chủ nếu file nằm trong đó (mọi máy dùng chung), không thì tuyệt đối."""
    p = Path(file)
    try:
        return p.resolve().relative_to(Path(goc).resolve()).as_posix()
    except (ValueError, OSError):
        return str(p)


def _tuyet_doi(goc: Path, duong_dan: str) -> Path:
    p = Path(duong_dan)
    return p if p.is_absolute() else Path(goc) / p


def ghi_mo_du_an(file) -> None:
    """Ghi dự án vừa mở vào danh sách gần đây của người đang đăng nhập (để máy khác nối tiếp)."""
    if PHIEN is None:
        return
    dd = _tuong_doi(PHIEN.goc, file)
    if Path(dd).is_absolute() and not dd.startswith('\\\\'):
        return                                # file riêng trên ổ đĩa máy này (kể cả bản offline): máy khác không mở được
    try:
        con = _mo(PHIEN.goc)
        try:
            with con:
                con.execute('INSERT OR REPLACE INTO gan_day (tai_khoan, duong_dan, luc) VALUES (?,?,?)',
                            (PHIEN.tai_khoan, dd, _bay_gio()))
                con.execute('DELETE FROM gan_day WHERE tai_khoan = ? AND duong_dan NOT IN (SELECT duong_dan FROM gan_day '
                            'WHERE tai_khoan = ? ORDER BY luc DESC LIMIT 15)', (PHIEN.tai_khoan, PHIEN.tai_khoan))
        finally:
            con.close()
    except (LoiMayChu, sqlite3.Error, OSError):
        pass                                  # mất kết nối máy chủ: không chặn việc mở dự án


def ds_gan_day(phien=None) -> list:
    """[(Path, lúc mở)] dự án gần đây của người dùng, mới nhất trước."""
    phien = phien or PHIEN
    if phien is None:
        return []
    con = _mo(phien.goc)
    try:
        return [(_tuyet_doi(phien.goc, r['duong_dan']), r['luc'])
                for r in con.execute('SELECT duong_dan, luc FROM gan_day WHERE tai_khoan = ? ORDER BY luc DESC', (phien.tai_khoan,))]
    finally:
        con.close()


def du_an_cuoi(phien=None):
    """Dự án người dùng mở gần nhất (còn tồn tại), để tự mở lại khi đăng nhập ở máy bất kỳ."""
    for p, _ in ds_gan_day(phien):
        if csdl.la_file_du_an(p) and p.exists():
            return p
    return None


def ds_du_an(goc=None) -> list:
    """Các dự án trong thư mục DuAn của máy chủ: dict(file, ten, sua_luc, kich_thuoc, dang_mo, lay_ve)."""
    from . import csdl, khoa
    goc = Path(goc) if goc else (PHIEN.goc if PHIEN else None)
    if goc is None:
        return []
    con = _mo(goc)
    try:
        lay = {r['duong_dan']: dict(r) for r in con.execute('SELECT * FROM lay_ve')}
    finally:
        con.close()
    kq = []
    tm = goc / THU_MUC_DU_AN
    cu = _doc_chi_muc(tm)
    moi = {}
    ds = []
    for f in (x for duoi in csdl.DUOI_MO for x in tm.rglob('*' + duoi)):                        # stat MỘT lần mỗi file (thư mục mạng: mỗi lần một vòng hỏi máy chủ)
        try:
            ds.append((f, f.stat()))
        except OSError:
            pass
    for f, st in sorted(ds, key=lambda x: x[1].st_mtime, reverse=True):
        k = f.relative_to(tm).as_posix()
        e = cu.get(k)
        if e and e.get('mtime') == st.st_mtime_ns and e.get('size') == st.st_size:
            ten = e.get('ten') or f.stem                # file không đổi: tên dự án lấy ở chỉ mục, không mở file qua mạng
        else:
            ten = f.stem
            try:
                c = sqlite3.connect(csdl.uri_chi_doc(f), uri=True, timeout=3)
                try:
                    r = c.execute('SELECT ten FROM du_an WHERE id = 1').fetchone()
                finally:
                    c.close()                           # file lỗi: không giữ khóa file trên máy chủ
                ten = (r[0] or f.stem) if r else f.stem
            except sqlite3.Error:
                pass
        moi[k] = dict(ten=ten, mtime=st.st_mtime_ns, size=st.st_size)
        kh = khoa.KhoaFile(f).nguoi_khac()
        kq.append(dict(file=f, ten=ten, sua_luc=datetime.fromtimestamp(st.st_mtime).strftime('%H:%M %d/%m/%Y'),
                       kich_thuoc=st.st_size, dang_mo=khoa.mo_ta(kh) if kh else '', lay_ve=lay.get(_tuong_doi(goc, f))))
    if moi != cu:
        _ghi_chi_muc(tm, moi)
    return kq


CHI_MUC = 'danh_muc_du_an.json'


def _doc_chi_muc(thu_muc: Path) -> dict:
    """Chỉ mục nhẹ của thư mục dự án trên máy chủ (đặc tả ARCH-PABT-2026-V4 mục 7.4): {đường dẫn tương đối: {ten, mtime, size}}.
    Liệt kê dự án chỉ đọc một file JSON vài KB thay vì mở từng file SQLite qua SMB (ổ mạng chậm: mỗi file vài trăm ms);
    file nào đổi (mtime / cỡ) mới mở lại để đọc tên. Hỏng / không đọc được: coi như chưa có (tự dựng lại)."""
    import json
    try:
        d = json.loads((Path(thu_muc) / CHI_MUC).read_text(encoding='utf-8'))
        return d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


def _ghi_chi_muc(thu_muc: Path, d: dict) -> None:
    import json
    f = Path(thu_muc) / CHI_MUC
    tam = f.with_name(f.name + '.tam')
    try:
        tam.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding='utf-8')
        os.replace(tam, f)                              # nguyên tử: máy khác đang đọc không gặp file ghi dở
    except OSError:                                     # thư mục chỉ đọc / mạng chập chờn: bỏ qua, lần sau dựng lại
        pass


# ---------------------------------------------------------------- mang dự án về làm offline / đưa lên lại
def thu_muc_offline() -> Path:
    return thu_muc_may() / 'offline'


def _so_lay_ve() -> Path:
    return thu_muc_offline() / 'lay_ve.json'


def ds_lay_ve_cuc_bo() -> list:
    """Dự án đã mang về máy này: [dict(ban_sao, goc, file_goc, tai_khoan, luc, sua_goc)]."""
    try:
        ds = json.loads(_so_lay_ve().read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return []
    return [x for x in ds if Path(x['ban_sao']).exists()]


def _ghi_so(ds: list) -> None:
    _so_lay_ve().parent.mkdir(parents=True, exist_ok=True)
    _so_lay_ve().write_text(json.dumps(ds, ensure_ascii=False, indent=1), encoding='utf-8')


def lay_ve(file, phien=None) -> Path:
    """Chép dự án trên máy chủ về máy này để làm offline; máy chủ ghi "đang được <người> lấy về" để người khác biết."""
    from . import khoa
    phien = phien or PHIEN
    if phien is None:
        raise LoiMayChu('Đăng nhập máy chủ trước khi mang dự án về.')
    f = Path(file)
    rel = _tuong_doi(phien.goc, f)
    con = _mo(phien.goc)
    try:
        r = con.execute('SELECT * FROM lay_ve WHERE duong_dan = ?', (rel,)).fetchone()
        if r is not None and r['tai_khoan'] != phien.tai_khoan:
            raise LoiMayChu(f'Dự án đang được "{r["tai_khoan"]}" mang về máy {r["may"]} từ {r["luc"]}: chờ người đó đưa lên lại.')
        khac = sorted({x['tai_khoan'] for x in con.execute('SELECT tai_khoan FROM lay_ve_ho WHERE duong_dan = ?', (rel,))
                       if x['tai_khoan'] != phien.tai_khoan})
        if khac:                                        # mang cả dự án về rồi đưa lên sẽ ghi đè các hộ người khác đang làm
            raise LoiMayChu(f'Một số hộ của dự án đang được {", ".join(khac)} nhận làm offline: chờ gộp lên lại, hoặc chỉ nhận '
                            'các hộ khác về làm.')
        k = khoa.KhoaFile(f).nguoi_khac()
        if k:
            raise LoiMayChu(f'Dự án đang được sửa trên {khoa.mo_ta(k)}: chờ đóng rồi mới mang về.')
        dich = thu_muc_offline() / f'{f.stem}__{phien.tai_khoan}{f.suffix}'
        dich.parent.mkdir(parents=True, exist_ok=True)
        _chep_nhat_quan(f, dich)                        # sqlite backup: ảnh chụp nhất quán kể cả khi máy khác đang ghi (copy2 thì không)
        sua = f.stat().st_mtime
        with con:
            con.execute('INSERT OR REPLACE INTO lay_ve (duong_dan, tai_khoan, may, luc, sua_goc) VALUES (?,?,?,?,?)',
                        (rel, phien.tai_khoan, _may(), _bay_gio(), sua))
            _ghi_nhat_ky(con, phien.tai_khoan, 'Mang dự án về làm offline', rel)
    finally:
        con.close()
    ds = [x for x in ds_lay_ve_cuc_bo() if x['ban_sao'] != str(dich)]
    ds.append(dict(ban_sao=str(dich), goc=str(phien.goc), file_goc=str(f), tai_khoan=phien.tai_khoan, luc=_bay_gio(), sua_goc=sua,
                   vai_tro=phien.vai_tro))
    _ghi_so(ds)
    return dich


def _muc_cuc_bo(ban_sao) -> dict:
    x = next((x for x in ds_lay_ve_cuc_bo() if Path(x['ban_sao']) == Path(ban_sao)), None)
    if x is None:
        raise LoiMayChu('File này không phải dự án đã mang về từ máy chủ.')
    return x


def dua_len(ban_sao, phien=None, ep: bool = False) -> Path:
    """Đưa bản làm offline lên lại máy chủ: sao lưu bản trên máy chủ vào SaoLuu rồi ghi đè; bỏ đánh dấu "lấy về".
    Bản trên máy chủ đã bị người khác sửa sau lúc lấy về thì báo xung đột (ep=True: vẫn ghi đè, bản kia vẫn có trong SaoLuu)."""
    from . import khoa
    phien = phien or PHIEN
    if phien is None:
        raise LoiMayChu('Đăng nhập máy chủ trước khi đưa dự án lên.')
    x = _muc_cuc_bo(ban_sao)
    if x.get('ds_ma_ho'):                               # bản nhận theo hộ: chỉ gộp các hộ đó, không ghi đè cả file
        return gop_ho_tu_ban_offline(ban_sao, phien=phien, ep=ep)['file']
    goc, f = Path(x['goc']), Path(x['file_goc'])
    if not ket_noi_duoc(goc):
        raise LoiMayChu('Chưa kết nối được máy chủ: đưa lên sau khi có mạng.')
    k = khoa.KhoaFile(f).nguoi_khac()
    if k:
        raise LoiMayChu(f'Bản trên máy chủ đang được mở trên {khoa.mo_ta(k)}: chờ đóng rồi đưa lên.')
    if f.exists() and abs(f.stat().st_mtime - float(x['sua_goc'])) > 2 and not ep:
        raise LoiMayChu('XUNG ĐỘT: bản trên máy chủ đã được sửa sau lúc mang về. Chọn "Vẫn đưa lên" để ghi đè '
                        '(bản trên máy chủ được sao lưu vào thư mục SaoLuu), hoặc liên hệ người đã sửa.')
    if f.exists():
        sl = goc / THU_MUC_SAO_LUU / f'{f.stem}_{datetime.now():%Y%m%d_%H%M%S}{f.suffix}'
        sl.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(f, sl)
    f.parent.mkdir(parents=True, exist_ok=True)
    tam = f.with_name(f.name + '.dang_dua_len')
    shutil.copy2(ban_sao, tam)
    os.replace(tam, f)
    con = _mo(goc)
    try:
        with con:
            con.execute('DELETE FROM lay_ve WHERE duong_dan = ?', (_tuong_doi(goc, f),))
            _ghi_nhat_ky(con, phien.tai_khoan, 'Đưa dự án offline lên máy chủ', _tuong_doi(goc, f))
    finally:
        con.close()
    _ghi_so([y for y in ds_lay_ve_cuc_bo() if Path(y['ban_sao']) != Path(ban_sao)])
    try:
        Path(ban_sao).unlink()
    except OSError:
        pass
    return f


def huy_lay_ve(ban_sao, phien=None) -> None:
    """Bỏ bản làm offline (không đưa lên): xóa đánh dấu trên máy chủ (nếu kết nối được) và bản sao trên máy."""
    x = _muc_cuc_bo(ban_sao)
    goc = Path(x['goc'])
    if ket_noi_duoc(goc):
        con = _mo(goc)
        try:
            with con:
                rel = _tuong_doi(goc, x['file_goc'])
                if x.get('ds_ma_ho'):
                    con.executemany('DELETE FROM lay_ve_ho WHERE duong_dan = ? AND ma_ho = ? AND tai_khoan = ?',
                                    [(rel, int(m), x['tai_khoan']) for m in x['ds_ma_ho']])
                else:
                    con.execute('DELETE FROM lay_ve WHERE duong_dan = ? AND tai_khoan = ?', (rel, x['tai_khoan']))
                _ghi_nhat_ky(con, x['tai_khoan'], 'Hủy mang về', x['file_goc'])
        finally:
            con.close()
    _ghi_so([y for y in ds_lay_ve_cuc_bo() if Path(y['ban_sao']) != Path(ban_sao)])
    try:
        Path(ban_sao).unlink()
    except OSError:
        pass


def nhat_ky_may_chu(goc, so_dong: int = 300) -> list:
    con = _mo(goc)
    try:
        return [dict(r) for r in con.execute('SELECT * FROM nhat_ky ORDER BY id DESC LIMIT ?', (so_dong,))]
    finally:
        con.close()


# ---------------------------------------------------------------- nhận / gộp THEO HỘ (nhiều chuyên viên cùng một dự án)
# Mỗi chuyên viên nhận một NHÓM HỘ của dự án trên máy chủ về làm offline (bảng lay_ve_ho khóa từng mã hộ - không khóa cả dự án) rồi
# gộp đúng các hộ đó lên lại: dòng của hộ ở bảng ho và các bảng theo hộ được thay bằng bản offline, hộ của người khác giữ nguyên.
# Bảng chung của dự án (danh mục, quyết định, đợt trình, đợt niêm yết) KHÔNG gộp: dòng theo hộ trỏ tới quyết định / đợt chưa có trên
# máy chủ bị bỏ qua (báo trong kết quả). Hộ bị sửa trên máy chủ sau lúc nhận về (so dấu vết nội dung) -> báo xung đột như dua_len.
BANG_CON_HO = ('thua', 'ct_dat', 'ct_khoan', 'pa_lan', 'qd_ho', 'nhat_ky_van_dong', 'anh_hien_trang', 'y_kien_du_thao',
               'doi_thoai_ho', 'tong_excel')
# cột của bảng theo hộ trỏ tới bảng chung: dòng trỏ tới dòng chưa có trên máy chủ không gộp được
_TRO_BANG_CHUNG = {'qd_ho': ('qd_id', 'quyet_dinh'), 'y_kien_du_thao': ('dot_id', 'dot_du_thao'),
                   'doi_thoai_ho': ('dot_id', 'dot_du_thao')}
_TRO_HO = (('dot_id', 'dot_trinh'), ('dot_du_thao_id', 'dot_du_thao'))      # cột của ho trỏ tới bảng chung
# cột trỏ bảng chung mà dòng VẪN gộp được khi bảng chung chưa có dòng đó: đặt NULL (lần PA giữ, chỉ bỏ gắn đợt trình) - rà soát 31/10/2026
_TRO_DAT_NULL = {'pa_lan': ('dot_trinh_id', 'dot_trinh')}
NHOM_MA_HO = 400                     # số mã hộ mỗi câu IN (...) - giới hạn tham số của SQLite cũ là 999


def _cot(con, bang: str) -> list:
    try:
        return [r[1] for r in con.execute(f'PRAGMA table_info({bang})')]
    except sqlite3.Error:
        return []


def _nhom(ds: list):
    for i in range(0, len(ds), NHOM_MA_HO):
        yield ds[i:i + NHOM_MA_HO]


def _cac_ma_ho(ds_ma_ho) -> list:
    return sorted({int(m) for m in (ds_ma_ho or ()) if int(m) > 0})


def dau_vet_ho(con, ds_ma_ho) -> dict:
    """{ma_ho: chuỗi băm} nội dung hộ ở bảng ho và các bảng theo hộ (BANG_CON_HO). So lúc gộp: khác lúc nhận về = hộ đã bị sửa
    trên máy chủ (mở trực tiếp file dự án) trong lúc chuyên viên làm offline."""
    cac = _cac_ma_ho(ds_ma_ho)
    bam = {m: hashlib.sha1() for m in cac}
    for bang in ('ho',) + BANG_CON_HO:
        cot = _cot(con, bang)
        if 'ma_ho' not in cot:
            continue
        i = cot.index('ma_ho')
        for nhom in _nhom(cac):
            for r in con.execute(f'SELECT * FROM {bang} WHERE ma_ho IN ({",".join("?" * len(nhom))}) ORDER BY rowid', nhom):
                bam[r[i]].update(repr((bang, tuple(r))).encode('utf-8'))
    return {m: h.hexdigest() for m, h in bam.items()}


def _mo_doc(f) -> sqlite3.Connection:
    """Kết nối chỉ đọc thuần (không qua csdl.mo: không nâng cấp / không tạo bảng phụ - dấu vết hai phía đọc cùng một cách)."""
    return sqlite3.connect(csdl.uri_chi_doc(f), uri=True, timeout=15)


def _chep_nhat_quan(f: Path, dich: Path) -> None:
    """Chép file dự án bằng sqlite backup (ảnh chụp nhất quán kể cả khi máy khác đang ghi - shutil.copy có thể chép giữa giao dịch)."""
    tam = dich.with_name(dich.name + '.tam')
    nguon = _mo_doc(f)
    try:
        dst = sqlite3.connect(str(tam))
        try:
            nguon.backup(dst)
        finally:
            dst.close()
        os.replace(tam, dich)
    finally:
        nguon.close()
        if tam.exists():
            tam.unlink()


def ds_ho_dang_lay_ve(file, goc=None) -> dict:
    """{ma_ho: dict(tai_khoan, may, luc)} các hộ của dự án file đang được chuyên viên nhận làm offline."""
    goc = Path(goc) if goc else (PHIEN.goc if PHIEN else None)
    if goc is None:
        return {}
    rel = _tuong_doi(goc, Path(file))
    con = _mo(goc)
    try:
        return {int(r['ma_ho']): dict(tai_khoan=r['tai_khoan'], may=r['may'], luc=r['luc'])
                for r in con.execute('SELECT * FROM lay_ve_ho WHERE duong_dan = ?', (rel,))}
    except sqlite3.Error:
        return {}
    finally:
        con.close()


def lay_ve_theo_ho(file, ds_ma_ho, phien=None) -> Path:
    """Nhận các hộ ds_ma_ho của dự án trên máy chủ về làm offline: chỉ khóa các mã hộ này (lay_ve_ho) - chuyên viên khác vẫn nhận
    và gộp được các hộ khác của cùng dự án. Bản offline là bản chép đủ dự án (để tính / in đúng bối cảnh) nhưng khi gộp chỉ các hộ đã
    nhận được ghi lên. Mỗi lần nhận một bản offline riêng (nhận nhóm thứ hai không ghi đè bản của nhóm thứ nhất)."""
    phien = phien or PHIEN
    if phien is None:
        raise LoiMayChu('Đăng nhập máy chủ trước khi nhận hộ về làm offline.')
    cac_ho = _cac_ma_ho(ds_ma_ho)
    if not cac_ho:
        raise LoiMayChu('Chọn ít nhất một hộ để nhận về làm offline.')
    f = Path(file)
    rel = _tuong_doi(phien.goc, f)
    luc, may = _bay_gio(), _may()
    con = _mo(phien.goc)
    try:
        con.execute('BEGIN IMMEDIATE')                  # kiểm + ghi một giao dịch: hai người bấm cùng lúc không cùng nhận một hộ
        try:
            r = con.execute('SELECT * FROM lay_ve WHERE duong_dan = ?', (rel,)).fetchone()
            if r is not None and r['tai_khoan'] != phien.tai_khoan:
                raise LoiMayChu(f'Toàn bộ dự án đang được "{r["tai_khoan"]}" mang về máy {r["may"]} từ {r["luc"]}: chờ người đó '
                                'đưa lên lại.')
            giu = {int(x['ma_ho']): x['tai_khoan'] for x in con.execute('SELECT * FROM lay_ve_ho WHERE duong_dan = ?', (rel,))
                   if x['tai_khoan'] != phien.tai_khoan}
            trung = [m for m in cac_ho if m in giu]
            if trung:
                nguoi = ', '.join(f'"{x}"' for x in sorted({giu[m] for m in trung}))
                raise LoiMayChu(f'{len(trung)} hộ (mã {", ".join(map(str, trung[:10]))}{"…" if len(trung) > 10 else ""}) đang được '
                                f'{nguoi} nhận làm: chọn hộ khác.')
            con.executemany('INSERT OR REPLACE INTO lay_ve_ho (duong_dan, ma_ho, tai_khoan, may, luc) VALUES (?,?,?,?,?)',
                            [(rel, m, phien.tai_khoan, may, luc) for m in cac_ho])
            _ghi_nhat_ky(con, phien.tai_khoan, 'Nhận hộ làm offline', f'{rel} ({len(cac_ho)} hộ)')
            con.commit()
        except BaseException:
            con.rollback()
            raise
        # chép SAU khi đã giữ chỗ (chép qua mạng có thể lâu - không giữ khóa ghi CSDL máy chủ trong lúc đó)
        try:
            dich = thu_muc_offline() / f'{f.stem}__{phien.tai_khoan}_ho_{datetime.now():%Y%m%d_%H%M%S}{f.suffix}'
            k = 2
            while dich.exists():
                dich = dich.with_name(f'{dich.stem.rsplit("~", 1)[0]}~{k}{f.suffix}')
                k += 1
            dich.parent.mkdir(parents=True, exist_ok=True)
            _chep_nhat_quan(f, dich)
            c = _mo_doc(dich)
            try:
                co = {x[0] for x in c.execute('SELECT ma_ho FROM ho')}
                thieu = [m for m in cac_ho if m not in co]
                if thieu:
                    raise LoiMayChu(f'Dự án không có hộ mã {", ".join(map(str, thieu[:10]))}.')
                dau_vet = dau_vet_ho(c, cac_ho)
                audit = c.execute('SELECT MAX(id) FROM audit_logs').fetchone()[0] if 'id' in _cot(c, 'audit_logs') else None
                nk = c.execute('SELECT MAX(id) FROM nhat_ky').fetchone()[0] if 'id' in _cot(c, 'nhat_ky') else None
            finally:
                c.close()
        except BaseException:
            with con:
                con.executemany('DELETE FROM lay_ve_ho WHERE duong_dan = ? AND ma_ho = ? AND tai_khoan = ? AND luc = ?',
                                [(rel, m, phien.tai_khoan, luc) for m in cac_ho])
            try:
                dich.unlink()
            except (OSError, NameError):
                pass
            raise
    finally:
        con.close()
    ds = ds_lay_ve_cuc_bo()
    ds.append(dict(ban_sao=str(dich), goc=str(phien.goc), file_goc=str(f), tai_khoan=phien.tai_khoan, luc=luc,
                   sua_goc=f.stat().st_mtime, ds_ma_ho=cac_ho, dau_vet={str(m): v for m, v in dau_vet.items()},
                   audit_max=audit or 0, nhat_ky_max=nk or 0, vai_tro=phien.vai_tro))
    _ghi_so(ds)
    return dich


def _gop_ho(con_n, con_d, cac_ho: list, audit_tu=None, nhat_ky_tu=None) -> dict:
    """Ghi các hộ cac_ho từ bản offline (con_n) lên file máy chủ (con_d), trong giao dịch của nơi gọi. Thửa: giữ mã thửa nếu trên máy
    chủ chưa dùng; trùng (máy khác đã cấp cùng mã cho thửa mới của hộ khác) -> cấp mã mới, dòng mục 1 trỏ theo mã mới.
    audit_tu: mã dòng nhật ký kiểm toán lớn nhất lúc nhận về - các dòng sau đó của các hộ này được chép thêm (bảng chỉ cho thêm).
    nhat_ky_tu: mã dòng nhật ký thao tác lớn nhất lúc nhận về - các dòng làm offline sau đó được chép thêm (ghi "[offline]").
    Rà soát 31/10/2026: gộp xong tính lại cột tóm tắt phê duyệt / chi trả của hộ (theo_doi.dong_bo_ho) - dòng qd_ho trỏ tới quyết định
    chưa có trên máy chủ bị bỏ thì cột tóm tắt chép từ bản offline sai lệch; pa_lan.dot_trinh_id trỏ đợt chưa có -> NULL."""
    kq = dict(so_ho=0, khong_co=[], bo_dong=[])
    cot_d = {b: set(_cot(con_d, b)) for b in ('ho',) + BANG_CON_HO}
    cot_ho = [c for c in _cot(con_n, 'ho') if c in cot_d['ho']]
    bang = {}
    for b in BANG_CON_HO:
        cn = _cot(con_n, b)
        if 'ma_ho' not in cn:
            continue
        if 'ma_ho' not in cot_d[b]:
            if any(con_n.execute(f'SELECT 1 FROM {b} WHERE ma_ho IN ({",".join("?" * len(nhom))}) LIMIT 1', nhom).fetchone()
                   for nhom in _nhom(cac_ho)):
                kq['bo_dong'].append(f'{b}: file trên máy chủ chưa có bảng này - không gộp được dòng của bảng')
            continue
        bang[b] = [c for c in cn if c in cot_d[b] and (c != 'id' or b == 'thua')]
    nho_id = {}

    def co_dong(bc: str, gt) -> bool:
        if bc not in nho_id:
            nho_id[bc] = {r[0] for r in con_d.execute(f'SELECT id FROM {bc}')} if 'id' in _cot(con_d, bc) else set()
        return gt in nho_id[bc]

    def chen(b: str, d: dict) -> None:
        con_d.execute(f'INSERT INTO {b} ({", ".join(d)}) VALUES ({",".join("?" * len(d))})', tuple(d.values()))

    dung_thua = {r[0] for r in con_d.execute('SELECT ma_thua FROM thua')} if 'thua' in bang else set()
    doi_thua = {}
    for ma_ho in cac_ho:
        r = con_n.execute(f'SELECT {", ".join(cot_ho)} FROM ho WHERE ma_ho = ?', (ma_ho,)).fetchone()
        if r is None:
            kq['khong_co'].append(ma_ho)                # hộ đã xóa trên bản offline: không xóa trên máy chủ (báo để xử lý tay)
            continue
        gt = dict(zip(cot_ho, r))
        giu = ['thu_tu'] + [c for c, _ in _TRO_HO if c in gt]
        cu = con_d.execute(f'SELECT {", ".join(giu)} FROM ho WHERE ma_ho = ?', (ma_ho,)).fetchone()
        cu = dict(zip(giu, cu)) if cu is not None else {}
        for c, bc in _TRO_HO:
            if c in gt and gt[c] is not None and not co_dong(bc, gt[c]):
                kq['bo_dong'].append(f'hộ {ma_ho}: {c} = {gt[c]} chưa có trên máy chủ - giữ giá trị trên máy chủ')
                gt[c] = cu.get(c)
        if cu:
            gt['thu_tu'] = cu['thu_tu']                 # số thứ tự hiển thị theo máy chủ (máy khác có thể đã đánh lại)
            sua = [c for c in gt if c != 'ma_ho']
            con_d.execute(f'UPDATE ho SET {", ".join(c + " = ?" for c in sua)} WHERE ma_ho = ?', (*[gt[c] for c in sua], ma_ho))
        else:
            chen('ho', gt)
        for b in bang:                                  # dòng cũ của hộ: bảng trỏ tới thửa trước, thửa sau cùng
            if b != 'thua':
                con_d.execute(f'DELETE FROM {b} WHERE ma_ho = ?', (ma_ho,))
        if 'thua' in bang:
            for (m,) in con_d.execute('SELECT ma_thua FROM thua WHERE ma_ho = ?', (ma_ho,)).fetchall():
                dung_thua.discard(m)
            con_d.execute('DELETE FROM thua WHERE ma_ho = ?', (ma_ho,))
            for x in con_n.execute(f'SELECT {", ".join(bang["thua"])} FROM thua WHERE ma_ho = ? ORDER BY rowid', (ma_ho,)).fetchall():
                d = dict(zip(bang['thua'], x))
                if d['ma_thua'] in dung_thua:
                    moi = max(dung_thua) + 1
                    doi_thua[d['ma_thua']] = moi
                    d['ma_thua'] = moi
                dung_thua.add(d['ma_thua'])
                chen('thua', d)
        for b, cot in bang.items():
            if b == 'thua':
                continue
            tro = _TRO_BANG_CHUNG.get(b)
            for x in con_n.execute(f'SELECT {", ".join(cot)} FROM {b} WHERE ma_ho = ? ORDER BY rowid', (ma_ho,)).fetchall():
                d = dict(zip(cot, x))
                if tro and tro[0] in d and not co_dong(tro[1], d[tro[0]]):
                    kq['bo_dong'].append(f'hộ {ma_ho}: {b} trỏ tới {tro[1]} {d[tro[0]]} chưa có trên máy chủ - không gộp dòng này')
                    continue
                tn = _TRO_DAT_NULL.get(b)
                if tn and d.get(tn[0]) is not None and not co_dong(tn[1], d[tn[0]]):
                    kq['bo_dong'].append(f'hộ {ma_ho}: {b}.{tn[0]} = {d[tn[0]]} chưa có trên máy chủ - bỏ gắn, giữ dòng')
                    d[tn[0]] = None
                if b == 'ct_dat' and d.get('ma_thua') is not None:
                    d['ma_thua'] = doi_thua.get(d['ma_thua'], d['ma_thua'])
                    if d['ma_thua'] not in dung_thua:
                        d['ma_thua'] = None
                chen(b, d)
        kq['so_ho'] += 1
    if audit_tu is not None and 'id' in _cot(con_n, 'audit_logs'):
        cot = [c for c in _cot(con_n, 'audit_logs') if c != 'id' and c in set(_cot(con_d, 'audit_logs'))]
        if 'ma_ho' in cot:
            for nhom in _nhom(cac_ho):
                for x in con_n.execute(f'SELECT {", ".join(cot)} FROM audit_logs WHERE id > ? AND ma_ho IN '
                                       f'({",".join("?" * len(nhom))}) ORDER BY id', (int(audit_tu), *nhom)).fetchall():
                    d = dict(zip(cot, x))
                    if d.get('ma_thua') in doi_thua:
                        d['ma_thua'] = doi_thua[d['ma_thua']]
                    chen('audit_logs', d)
    if nhat_ky_tu is not None and 'id' in _cot(con_n, 'nhat_ky') and 'id' in _cot(con_d, 'nhat_ky'):
        cot = [c for c in _cot(con_n, 'nhat_ky') if c != 'id' and c in set(_cot(con_d, 'nhat_ky'))]
        for x in con_n.execute(f'SELECT {", ".join(cot)} FROM nhat_ky WHERE id > ? ORDER BY id', (int(nhat_ky_tu),)).fetchall():
            d = dict(zip(cot, x))
            if 'viec' in d:
                d['viec'] = f'[offline] {d["viec"]}'
            chen('nhat_ky', d)
    from .theo_doi import dong_bo_ho as dong_bo_tom_tat
    if 'da_phe_duyet' in cot_d['ho'] and 'qd_ho' in bang:
        for ma_ho in cac_ho:
            if ma_ho not in kq['khong_co']:
                dong_bo_tom_tat(con_d, ma_ho)
    kq['doi_ma_thua'] = doi_thua
    return kq


def gop_ho_tu_ban_offline(ban_sao, ds_ma_ho=None, phien=None, file_goc=None, ep: bool = False, giu: bool = False) -> dict:
    """Gộp các hộ ds_ma_ho (mặc định: mọi hộ đã nhận cùng bản offline này) từ bản offline lên file dự án trên máy chủ, KHÔNG ghi đè
    các hộ khác. Bản không có trong sổ nhận về của máy này: phải đưa file_goc (file trên máy chủ) và ds_ma_ho. Sao lưu file máy chủ
    vào SaoLuu trước khi ghi; một giao dịch (lỗi giữa chừng -> file máy chủ như cũ). Hộ bị sửa trên máy chủ sau lúc nhận về -> báo
    XUNG ĐỘT (ep=True: vẫn gộp). Gộp một phần: các hộ còn lại vẫn nhận, bản offline giữ lại.
    giu=True (đồng bộ - 30/10/2026, dong_bo_ho): gộp xong VẪN GIỮ các hộ (không trả khóa, giữ bản offline), mốc so xung đột (dấu
    vết hộ trên máy chủ, nhật ký kiểm toán đã chép) dời tới lúc đồng bộ - lần sau chỉ báo xung đột khi có người sửa sau lần này.
    Trả dict(file, so_ho, ma_ho, khong_co, bo_dong, doi_ma_thua, sao_luu)."""
    from . import khoa
    phien = phien or PHIEN
    if phien is None:
        raise LoiMayChu('Đăng nhập máy chủ trước khi gộp hộ lên.')
    muc = next((x for x in ds_lay_ve_cuc_bo() if Path(x['ban_sao']) == Path(ban_sao)), None)
    if muc is not None:
        goc, f = Path(muc['goc']), Path(muc['file_goc'])
        cac_ho = _cac_ma_ho(ds_ma_ho or muc.get('ds_ma_ho'))
    elif giu:
        raise LoiMayChu('Chỉ đồng bộ được bản offline theo hộ đã nhận về trên máy này.')
    else:
        if not ds_ma_ho or not file_goc:
            raise LoiMayChu('Bản này không có trong sổ nhận về của máy: cần chỉ rõ file dự án trên máy chủ và các hộ cần gộp.')
        goc, f, cac_ho = phien.goc, Path(file_goc), _cac_ma_ho(ds_ma_ho)
    if not cac_ho:
        raise LoiMayChu('Không có hộ nào để gộp lên máy chủ.')
    if Path(ban_sao).resolve() == f.resolve():
        raise LoiMayChu('Bản offline trùng file dự án trên máy chủ.')
    if not ket_noi_duoc(goc):
        raise LoiMayChu('Chưa kết nối được máy chủ: gộp sau khi có mạng.')
    tk = muc['tai_khoan'] if muc is not None else phien.tai_khoan
    rel = _tuong_doi(goc, f)
    con_mc = _mo(goc)
    try:
        r = con_mc.execute('SELECT * FROM lay_ve WHERE duong_dan = ?', (rel,)).fetchone()
        if r is not None and r['tai_khoan'] != tk:
            raise LoiMayChu(f'Toàn bộ dự án đang được "{r["tai_khoan"]}" mang về làm offline: chờ người đó đưa lên lại.')
        nguoi_khac = {int(x['ma_ho']): x['tai_khoan'] for x in con_mc.execute('SELECT * FROM lay_ve_ho WHERE duong_dan = ?', (rel,))
                      if x['tai_khoan'] != tk}
    finally:
        con_mc.close()
    trung = [m for m in cac_ho if m in nguoi_khac]
    if trung:
        raise LoiMayChu(f'{len(trung)} hộ (mã {", ".join(map(str, trung[:10]))}) đang được người khác nhận làm: không gộp đè.')
    k = khoa.KhoaFile(f).nguoi_khac()
    if k:
        raise LoiMayChu(f'Dự án trên máy chủ đang được mở trực tiếp trên {khoa.mo_ta(k)}: chờ đóng rồi gộp.')
    dv_cu = (muc or {}).get('dau_vet') or {}
    if dv_cu and not ep:
        c = _mo_doc(f)
        try:
            dv = dau_vet_ho(c, cac_ho)
        finally:
            c.close()
        doi = [m for m in cac_ho if str(m) in dv_cu and dv.get(m) != dv_cu[str(m)]]
        if doi:
            c = _mo_doc(f)
            try:
                ten = dict(c.execute('SELECT ma_ho, ho_ten FROM ho').fetchall())
            finally:
                c.close()
            raise LoiXungDot(f'XUNG ĐỘT: {len(doi)} hộ (mã {", ".join(map(str, doi[:10]))}) đã được sửa trên máy chủ sau lúc nhận về. '
                             'Chọn "Vẫn gộp" để ghi đè các hộ này (file trên máy chủ được sao lưu vào thư mục SaoLuu), hoặc liên hệ '
                             'người đã sửa.', [(m, ten.get(m, '')) for m in doi])
    sl = goc / THU_MUC_SAO_LUU / f'{f.stem}_truoc_gop_{datetime.now():%Y%m%d_%H%M%S}{f.suffix}'
    sl.parent.mkdir(parents=True, exist_ok=True)
    _chep_nhat_quan(f, sl)
    con_n = _mo_doc(ban_sao)
    con_d = csdl.mo(f)
    try:
        with csdl.giao_dich(con_d):
            kq = _gop_ho(con_n, con_d, cac_ho, (muc or {}).get('audit_max'), (muc or {}).get('nhat_ky_max'))
            csdl.ghi_nhat_ky(con_d, 'Gộp hộ từ bản offline',
                             f'{kq["so_ho"]} hộ của {tk}: {", ".join(map(str, cac_ho[:15]))}{"…" if len(cac_ho) > 15 else ""}')
    finally:
        con_n.close()
        con_d.close()
    con_mc = _mo(goc)
    try:
        with con_mc:
            if giu:
                _ghi_nhat_ky(con_mc, phien.tai_khoan, 'Đồng bộ hộ offline lên máy chủ (vẫn giữ hộ)', f'{rel} ({kq["so_ho"]} hộ)')
            else:
                con_mc.executemany('DELETE FROM lay_ve_ho WHERE duong_dan = ? AND ma_ho = ? AND tai_khoan = ?',
                                   [(rel, m, tk) for m in cac_ho])
                _ghi_nhat_ky(con_mc, phien.tai_khoan, 'Gộp hộ offline lên máy chủ', f'{rel} ({kq["so_ho"]} hộ)')
    finally:
        con_mc.close()
    if giu:                                             # mốc mới: dấu vết các hộ trên máy chủ sau khi gộp + nhật ký kiểm toán đã chép
        c, cn = _mo_doc(f), _mo_doc(ban_sao)
        try:
            dv = dau_vet_ho(c, cac_ho)
            audit = cn.execute('SELECT MAX(id) FROM audit_logs').fetchone()[0] if 'id' in _cot(cn, 'audit_logs') else None
            nk = cn.execute('SELECT MAX(id) FROM nhat_ky').fetchone()[0] if 'id' in _cot(cn, 'nhat_ky') else None
        finally:
            c.close()
            cn.close()
        moc = dict(muc.get('dau_vet') or {})
        moc.update({str(m): v for m, v in dv.items()})
        ds = [dict(y, dau_vet=moc, audit_max=audit or y.get('audit_max') or 0, dong_bo_luc=_bay_gio(),
                   **({'nhat_ky_max': nk} if nk is not None and y.get('nhat_ky_max') is not None else {}))
              if Path(y['ban_sao']) == Path(ban_sao) else y for y in ds_lay_ve_cuc_bo()]
        _ghi_so(ds)
    elif muc is not None:
        con_lai = [m for m in _cac_ma_ho(muc.get('ds_ma_ho')) if m not in set(cac_ho)]
        ds = [y for y in ds_lay_ve_cuc_bo() if Path(y['ban_sao']) != Path(ban_sao)]
        if con_lai:                                     # gộp một phần: bản offline còn giữ các hộ chưa gộp
            muc = dict(muc, ds_ma_ho=con_lai, dau_vet={k: v for k, v in (muc.get('dau_vet') or {}).items() if int(k) in con_lai})
            ds.append(muc)
        _ghi_so(ds)
        if not con_lai:
            try:
                Path(ban_sao).unlink()
            except OSError:
                pass
    return dict(file=f, ma_ho=cac_ho, sao_luu=sl, **kq)


def dong_bo_ho(ban_sao, phien=None, ep: bool = False) -> dict:
    """Đồng bộ bản offline theo hộ lên máy chủ mà VẪN GIỮ các hộ để làm tiếp (30/10/2026, phương án đột phá 5): người khác mở dự án
    trên máy chủ thấy ngay số liệu mới, không phải chờ trả hộ. Xung đột như gop_ho_tu_ban_offline (LoiXungDot; ep=True ghi đè)."""
    return gop_ho_tu_ban_offline(ban_sao, phien=phien, ep=ep, giu=True)


def tu_dong_bo_khi_luu() -> bool:
    """Cài đặt máy: tự đồng bộ bản offline theo hộ lên máy chủ mỗi lần bấm Lưu (Ctrl+S). Mặc định tắt."""
    return bool(doc_cau_hinh().get('tu_dong_bo'))


def huy_lay_ve_ho(file, ds_ma_ho=None, phien=None) -> int:
    """Trả lại các hộ đã nhận làm offline trên máy chủ (ds_ma_ho None: mọi hộ của tài khoản này trên dự án file). Bản offline trên
    máy (nếu có) không bị xóa - dùng huy_lay_ve(bản offline) để bỏ cả bản. Trả số hộ đã trả lại."""
    phien = phien or PHIEN
    if phien is None:
        return 0
    rel = _tuong_doi(phien.goc, Path(file))
    con = _mo(phien.goc)
    try:
        with con:
            if ds_ma_ho is None:
                n = con.execute('DELETE FROM lay_ve_ho WHERE duong_dan = ? AND tai_khoan = ?', (rel, phien.tai_khoan)).rowcount
            else:
                n = sum(con.execute('DELETE FROM lay_ve_ho WHERE duong_dan = ? AND ma_ho = ? AND tai_khoan = ?',
                                    (rel, m, phien.tai_khoan)).rowcount for m in _cac_ma_ho(ds_ma_ho))
            if n:
                _ghi_nhat_ky(con, phien.tai_khoan, 'Trả lại hộ đã nhận làm offline', f'{rel} ({n} hộ)')
            return n
    finally:
        con.close()




def ban_theo_ho(file) -> dict | None:
    """Mục sổ nhận về của bản offline THEO HỘ đang là file (None: không phải bản theo hộ của máy này)."""
    try:
        f = Path(file).resolve()
    except OSError:
        return None
    for x in ds_lay_ve_cuc_bo():
        try:
            if x.get('ds_ma_ho') and Path(x['ban_sao']).resolve() == f:
                return x
        except OSError:
            continue
    return None


def ho_nhan_viec(file) -> frozenset | None:
    """Mã các hộ đã nhận làm offline nếu file là bản offline theo hộ - chỉ các hộ này được gộp lên máy chủ; None: file thường."""
    x = ban_theo_ho(file)
    return frozenset(int(m) for m in x['ds_ma_ho']) if x else None


_RE_AP = re.compile(r'^\s*((?:ấp|khu phố|kp\.?|tổ|thôn|xóm|khu)\s*[^,;]+)', re.I)


def ap_cua(dia_chi: str) -> str:
    """Ấp / khu phố / tổ / thôn đầu địa chỉ ("Ấp 3, xã Trị An" -> "Ấp 3"); không có: ''."""
    m = _RE_AP.match(str(dia_chi or ''))
    return ' '.join(m.group(1).split()) if m else ''


def ds_ho_de_chon(file, goc=None, tai_khoan: str | None = None) -> list:
    """Các hộ của dự án trên máy chủ để chọn nhận theo hộ: dict(ma_ho, stt, ho_ten, cccd, dia_chi, ap, to_thua, dot, giu) - giu:
    None (chưa ai nhận) / dict(tai_khoan, may, luc, cua_toi). Đọc file dự án chỉ đọc (không khóa). goc=False: không hỏi máy chủ (đọc
    bản offline trên máy - giu luôn None)."""
    goc = None if goc is False else (Path(goc) if goc else (PHIEN.goc if PHIEN else None))
    tk = tai_khoan if tai_khoan is not None else (PHIEN.tai_khoan if PHIEN else '')
    giu = ds_ho_dang_lay_ve(file, goc) if goc else {}
    c = _mo_doc(file)
    c.row_factory = sqlite3.Row
    try:
        dot = {}
        if 'id' in _cot(c, 'dot_trinh'):
            dot = {r['id']: (r['ten'] or f'Đợt {r["so"]}') for r in c.execute('SELECT id, so, ten FROM dot_trinh')}
        thua = {}
        for r in c.execute('SELECT ma_ho, so_to, so_thua FROM thua ORDER BY ma_ho, thu_tu, ma_thua'):
            thua.setdefault(r[0], []).append(f'{r[1]}/{r[2]}')
        co_dot = 'dot_id' in _cot(c, 'ho')
        kq = []
        for r in c.execute('SELECT * FROM ho ORDER BY thu_tu, ma_ho'):
            g = giu.get(r['ma_ho'])
            kq.append(dict(ma_ho=r['ma_ho'], stt=r['thu_tu'], ho_ten=r['ho_ten'] or '', cccd=r['so_cccd'] or '',
                           dia_chi=r['dia_chi'] or '', ap=ap_cua(r['dia_chi']), to_thua=', '.join(thua.get(r['ma_ho'], [])),
                           dot=dot.get(r['dot_id'], '') if co_dot else '',
                           giu=dict(g, cua_toi=g['tai_khoan'] == tk) if g else None))
        return kq
    finally:
        c.close()

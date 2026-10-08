r"""Làm việc qua máy chủ trong mạng nội bộ (LAN): tài khoản người dùng, dự án dùng chung, mang dự án về làm offline.

"Máy chủ" là một thư mục dùng chung trên máy chủ của đơn vị (ví dụ \\MAYCHU\PABT hoặc ổ mạng Z:\PABT) - không cần cài phần mềm
máy chủ riêng. Cấu trúc:
    <máy chủ>\pabt_may_chu.sqlite   tài khoản (mật khẩu băm PBKDF2), dự án gần đây của từng người, dự án đang lấy về, nhật ký
    <máy chủ>\DuAn\*.pabt           các file dự án dùng chung (khóa nhiều máy bằng khoa.py như khi mở file bất kỳ)
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

TEN_CSDL = 'pabt_may_chu.sqlite'
THU_MUC_DU_AN = 'DuAn'
THU_MUC_SAO_LUU = 'SaoLuu'
LAP_BAM = 120000                       # số vòng PBKDF2-HMAC-SHA256
QUAN_TRI, NGUOI_DUNG = 'quan_tri', 'nguoi_dung'
TEN_VAI_TRO = {QUAN_TRI: 'Quản trị', NGUOI_DUNG: 'Người dùng'}

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
CREATE TABLE IF NOT EXISTS nhat_ky (
    id INTEGER PRIMARY KEY, luc TEXT NOT NULL, tai_khoan TEXT NOT NULL DEFAULT '', may TEXT NOT NULL DEFAULT '',
    viec TEXT NOT NULL DEFAULT '', chi_tiet TEXT NOT NULL DEFAULT '');
CREATE TABLE IF NOT EXISTS thong_tin (ma TEXT PRIMARY KEY, gia_tri TEXT NOT NULL DEFAULT '');
'''


class LoiMayChu(Exception):
    pass


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
        return self.vai_tro == QUAN_TRI

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
        raise LoiMayChu('Thư mục này đã là máy chủ PABT: chọn "Kết nối" thay vì khởi tạo.')
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
        if tai_khoan == phien.tai_khoan and (khoa or (vai_tro and vai_tro != QUAN_TRI)):
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
        if p.suffix.lower() == '.pabt' and p.exists():
            return p
    return None


def ds_du_an(goc=None) -> list:
    """Các dự án trong thư mục DuAn của máy chủ: dict(file, ten, sua_luc, kich_thuoc, dang_mo, lay_ve)."""
    from . import khoa
    goc = Path(goc) if goc else (PHIEN.goc if PHIEN else None)
    if goc is None:
        return []
    con = _mo(goc)
    try:
        lay = {r['duong_dan']: dict(r) for r in con.execute('SELECT * FROM lay_ve')}
    finally:
        con.close()
    kq = []
    for f in sorted((goc / THU_MUC_DU_AN).rglob('*.pabt'), key=lambda x: x.stat().st_mtime, reverse=True):
        ten = f.stem
        try:
            c = sqlite3.connect(f.resolve().as_uri() + '?mode=ro', uri=True, timeout=3)
            r = c.execute('SELECT ten FROM du_an WHERE id = 1').fetchone()
            c.close()
            ten = (r[0] or f.stem) if r else f.stem
        except sqlite3.Error:
            pass
        k = khoa.KhoaFile(f).nguoi_khac()
        st = f.stat()
        kq.append(dict(file=f, ten=ten, sua_luc=datetime.fromtimestamp(st.st_mtime).strftime('%H:%M %d/%m/%Y'),
                       kich_thuoc=st.st_size, dang_mo=khoa.mo_ta(k) if k else '', lay_ve=lay.get(_tuong_doi(goc, f))))
    return kq


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
        k = khoa.KhoaFile(f).nguoi_khac()
        if k:
            raise LoiMayChu(f'Dự án đang được sửa trên {khoa.mo_ta(k)}: chờ đóng rồi mới mang về.')
        dich = thu_muc_offline() / f'{f.stem}__{phien.tai_khoan}.pabt'
        dich.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(f, dich)
        sua = f.stat().st_mtime
        with con:
            con.execute('INSERT OR REPLACE INTO lay_ve (duong_dan, tai_khoan, may, luc, sua_goc) VALUES (?,?,?,?,?)',
                        (rel, phien.tai_khoan, _may(), _bay_gio(), sua))
            _ghi_nhat_ky(con, phien.tai_khoan, 'Mang dự án về làm offline', rel)
    finally:
        con.close()
    ds = [x for x in ds_lay_ve_cuc_bo() if x['ban_sao'] != str(dich)]
    ds.append(dict(ban_sao=str(dich), goc=str(phien.goc), file_goc=str(f), tai_khoan=phien.tai_khoan, luc=_bay_gio(), sua_goc=sua))
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
        sl = goc / THU_MUC_SAO_LUU / f'{f.stem}_{datetime.now():%Y%m%d_%H%M%S}.pabt'
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
                con.execute('DELETE FROM lay_ve WHERE duong_dan = ? AND tai_khoan = ?', (_tuong_doi(goc, x['file_goc']), x['tai_khoan']))
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



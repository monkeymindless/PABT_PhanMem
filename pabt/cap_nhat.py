"""Gói cập nhật phần mềm (.pabtcn): sửa lỗi, thêm tính năng mà không phải cài lại bộ cài.

Gói là file zip: cap_nhat.json (ung_dung, phien_ban, ban_goc_toi_thieu, ngay, mo_ta, file: {đường dẫn: sha256}) và toàn bộ
pabt/*.py cùng file dữ liệu của gói pabt. Tạo bằng tao_cap_nhat.py; cài vào thư mục máy (nap_cap_nhat.thu_muc), có hiệu lực từ
lần mở phần mềm sau (nap_cap_nhat.nap kiểm tra lại mã SHA-256 từng file, file lạ trước khi nạp). Không dùng chữ ký số (người
dùng yêu cầu bỏ từ 0.9.16): file cap_nhat.sig trong gói cũ (0.9.14, 0.9.15) được bỏ qua.
Gói chỉ thay mã PABT, không thay Python / Qt / thư viện đóng trong bộ cài: thay đổi cần thư viện mới thì dựng bộ cài mới.
"""
from __future__ import annotations
import datetime
import hashlib
import json
import os
import py_compile
import re
import shutil
import tempfile
import zipfile
from pathlib import Path

from . import __version__, an_toan

DUOI = '.pabtcn'
UNG_DUNG = 'PABT'
BAN_GOC_TOI_THIEU = '0.8.0'          # bản cài đầu tiên chạy Python 3.8 + Qt5 (Win 7 - 11)
DU_LIEU = ('schema.sql', 'bo_don_gia.sqlite', 'bang_gia_nq28.json', 'bieu_tuong.png', 'pabt_profile.json')


class LoiCapNhat(Exception):
    pass


def _nap():
    try:
        import nap_cap_nhat
        return nap_cap_nhat
    except ImportError:
        return None


def so(phien_ban) -> tuple:
    return tuple(int(x) for x in re.findall(r'\d+', str(phien_ban or '')))


def thu_muc() -> Path:
    n = _nap()
    if n:
        return n.thu_muc()
    goc = os.environ.get('PABT_THU_MUC_MAY') or Path(os.environ.get('APPDATA') or Path.home()) / 'PABT'
    return Path(goc) / 'cap_nhat'


def ban_goc() -> str:
    """Phiên bản bản cài gốc (khác __version__ khi đang chạy bản cập nhật)."""
    n = _nap()
    return (n.BAN_GOC if n else None) or __version__


def _bam(du: bytes) -> str:
    return hashlib.sha256(du).hexdigest()


def tao_goi(goc, file_ra, mo_ta: str = '', toi_thieu: str = BAN_GOC_TOI_THIEU) -> dict:
    """Đóng gói pabt/ trong thư mục mã nguồn `goc` thành gói cập nhật (phiên bản lấy từ pabt/__init__.py)."""
    th = Path(goc) / 'pabt'
    m = re.search(r"__version__\s*=\s*'([^']+)'", (th / '__init__.py').read_text(encoding='utf-8'))
    if not m:
        raise LoiCapNhat('Không thấy __version__ trong pabt/__init__.py.')
    ds = sorted(th.glob('*.py')) + [th / x for x in DU_LIEU if (th / x).exists()]
    with tempfile.TemporaryDirectory() as td:
        for f in ds:
            if f.suffix == '.py':
                try:
                    py_compile.compile(str(f), cfile=str(Path(td) / 'x.pyc'), doraise=True)
                except py_compile.PyCompileError as e:
                    raise LoiCapNhat(f'Lỗi cú pháp, không đóng gói: {e.msg}') from e
    tt = dict(ung_dung=UNG_DUNG, phien_ban=m.group(1), ban_goc_toi_thieu=toi_thieu,
              ngay=datetime.date.today().strftime('%d/%m/%Y'), mo_ta=mo_ta, file={})
    Path(file_ra).parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(file_ra, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for f in ds:
            du = f.read_bytes()
            tt['file']['pabt/' + f.name] = _bam(du)
            z.writestr('pabt/' + f.name, du)
        z.writestr('cap_nhat.json', json.dumps(tt, ensure_ascii=False, indent=1).encode('utf-8'))
    return tt


def _doc_json(z) -> tuple:
    """(thông tin, nội dung cap_nhat.json gốc) của gói đang mở."""
    try:
        jb = z.read('cap_nhat.json')
        return json.loads(jb.decode('utf-8')), jb
    except (KeyError, ValueError) as e:
        raise LoiCapNhat('Gói cập nhật thiếu hoặc hỏng cap_nhat.json.') from e


def doc_goi(file) -> dict:
    """Đọc và kiểm tra gói: file nén an toàn, nguyên vẹn từng file (SHA-256); trả thông tin cap_nhat.json."""
    try:
        an_toan.kiem_tra_zip(file, toi_da=100 * 2 ** 20)
    except an_toan.LoiAnToan as e:
        raise LoiCapNhat(f'File không phải gói cập nhật LARC hợp lệ: {e}') from None
    try:
        z = zipfile.ZipFile(file)
    except (OSError, zipfile.BadZipFile) as e:
        raise LoiCapNhat('File không phải gói cập nhật LARC (không đọc được).') from e
    with z:
        m, _ = _doc_json(z)
        if m.get('ung_dung') != UNG_DUNG or not so(m.get('phien_ban')):
            raise LoiCapNhat('File không phải gói cập nhật LARC.')
        ds = m.get('file') or {}
        if 'pabt/__init__.py' not in ds:
            raise LoiCapNhat('Gói cập nhật thiếu pabt/__init__.py.')
        for ten, bam in ds.items():
            if not re.fullmatch(r'pabt/[\w.-]+', ten) or '..' in ten:
                raise LoiCapNhat(f'Tên file không hợp lệ trong gói: {ten}')
            try:
                du = z.read(ten)
            except KeyError as e:
                raise LoiCapNhat(f'Gói cập nhật thiếu file {ten}.') from e
            if _bam(du) != bam:
                raise LoiCapNhat(f'File {ten} trong gói bị hỏng (sai mã kiểm tra) - tải / chép lại gói.')
    return m


def kiem_tra(m: dict) -> None:
    pb, goc = m['phien_ban'], ban_goc()
    if so(pb) <= so(__version__):
        raise LoiCapNhat(f'Phần mềm đang ở phiên bản {__version__}; gói cập nhật {pb} không mới hơn.')
    if so(m.get('ban_goc_toi_thieu')) > so(goc):
        raise LoiCapNhat(f'Gói {pb} cần bản cài từ {m.get("ban_goc_toi_thieu")} trở lên (máy đang cài {goc}): '
                         'hãy cài bộ cài đầy đủ mới.')


def _don(d: Path, giu: str = '') -> None:
    """Xóa các bản cập nhật cũ (bỏ qua bản đang được dùng, sẽ xóa ở lần sau)."""
    for x in d.iterdir() if d.exists() else ():
        if x.is_dir() and x.name != giu:
            shutil.rmtree(x, ignore_errors=True)


def cai(file) -> dict:
    """Kiểm tra rồi cài gói; có hiệu lực từ lần mở phần mềm sau."""
    m = doc_goi(file)
    kiem_tra(m)
    d = thu_muc()
    ten = f'{m["phien_ban"]}_{datetime.datetime.now():%Y%m%d%H%M%S}'
    dich = d / ten
    try:
        (dich / 'pabt').mkdir(parents=True)
        with zipfile.ZipFile(file) as z:
            m, jb = _doc_json(z)                        # đọc lại từ file (không tin bản đã kiểm tra trước: file có thể đã đổi)
            for f, bam in m['file'].items():
                du = z.read(f)
                if not re.fullmatch(r'pabt/[\w.-]+', f) or _bam(du) != bam:
                    raise LoiCapNhat(f'File {f} trong gói bị đổi trong lúc cài: không cài.')
                (dich / f).write_bytes(du)
        (dich / 'cap_nhat.json').write_bytes(jb)        # mã SHA-256 từng file: kiểm tra lại mỗi lần khởi động
        (d / 'hien_hanh.txt').write_text(ten, encoding='utf-8')
        (d / 'dang_khoi_dong.txt').unlink(missing_ok=True)
    except LoiCapNhat:
        shutil.rmtree(dich, ignore_errors=True)
        raise
    except OSError as e:
        shutil.rmtree(dich, ignore_errors=True)
        raise LoiCapNhat(f'Không ghi được bản cập nhật vào {d}: {e}') from e
    _don(d, ten)
    return m


def go() -> bool:
    """Bỏ bản cập nhật, quay về bản cài gốc từ lần mở sau. Trả False nếu không có bản cập nhật."""
    d = thu_muc()
    hh = d / 'hien_hanh.txt'
    if not hh.exists():
        return False
    hh.unlink()
    (d / 'dang_khoi_dong.txt').unlink(missing_ok=True)
    _don(d)
    return True


def trang_thai() -> dict:
    tt = dict(dang_chay=__version__, ban_goc=ban_goc(), da_cai=None, ngay='', mo_ta='', loi='')
    d = thu_muc()
    try:
        ten = (d / 'hien_hanh.txt').read_text(encoding='utf-8').strip()
        m = json.loads((d / ten / 'cap_nhat.json').read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return tt
    tt.update(da_cai=m.get('phien_ban'), ngay=m.get('ngay', ''), mo_ta=m.get('mo_ta', ''))
    if (d / ten / 'LOI.txt').exists():
        tt['loi'] = (d / ten / 'LOI.txt').read_text(encoding='utf-8')
    return tt

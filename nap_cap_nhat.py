r"""Nạp bản cập nhật PABT (gói .pabtcn đã cài) thay cho gói `pabt` đóng trong PABT.exe - gọi ở đầu chay.py, trước mọi
`import pabt`.

Bản cập nhật ở <thư mục máy>\cap_nhat (thư mục máy = %APPDATA%\PABT, hoặc biến PABT_THU_MUC_MAY):
  hien_hanh.txt               tên thư mục bản đang dùng
  <tên>\cap_nhat.json, <tên>\pabt\*.py + file dữ liệu của gói pabt
Chỉ dùng khi bản cập nhật mới hơn bản cài gốc và bản gốc đủ mới (ban_goc_toi_thieu). Bản cập nhật lỗi - không nạp được, hoặc
2 lần khởi động liền không tới được cửa sổ chính - tự tắt (ghi <tên>\LOI.txt), phần mềm chạy bản gốc.
File này nằm trong bản cài gốc, gói cập nhật không thay được: giữ thật gọn, chỉ dùng thư viện chuẩn.
"""
from __future__ import annotations
import importlib
import importlib.machinery
import json
import os
import re
import sys
import traceback
from pathlib import Path

BAN_GOC = None        # phiên bản gói pabt đóng trong bản cài (None: chưa gọi nap)
DANG_DUNG = None      # phiên bản cập nhật đang dùng (None: bản gốc)
FILE_HIEN_HANH = 'hien_hanh.txt'
FILE_DEM = 'dang_khoi_dong.txt'
FILE_LOI = 'LOI.txt'
FILE_DA_KIEM = '.da_kiem_tot'     # dấu "đã kiểm đủ + nạp thử tốt" (máy yếu, 16/10/2026): lần mở sau khỏi băm / nạp thử lại


def thu_muc() -> Path:
    goc = os.environ.get('PABT_THU_MUC_MAY') or Path(os.environ.get('APPDATA') or Path.home()) / 'PABT'
    return Path(goc) / 'cap_nhat'


def so(phien_ban) -> tuple:
    return tuple(int(x) for x in re.findall(r'\d+', str(phien_ban or '')))


def thu_muc_hien_hanh():
    """Thư mục bản cập nhật đã cài (chưa xét có dùng được không), hoặc None."""
    d = thu_muc()
    try:
        ten = (d / FILE_HIEN_HANH).read_text(encoding='utf-8').strip()
    except (OSError, ValueError):               # ValueError: file rác không phải UTF-8 - không được làm sập lúc khởi động
        return None
    # chỉ nhận tên MỘT thư mục con của cap_nhat\: chặn '..', đường dẫn tuyệt đối, ổ đĩa khác, thư mục lồng
    if not ten or any(k in ten for k in ('/', '\\', ':')) or set(ten) <= {'.'}:
        return None
    return d / ten if (d / ten / 'cap_nhat.json').exists() else None


class _TimTruoc:
    """Tìm gói pabt trong thư mục cập nhật, trước bộ nạp của PyInstaller."""

    def __init__(self, goc):
        self.goc = str(goc)

    def find_spec(self, ten, path=None, target=None):
        if ten == 'pabt':
            return importlib.machinery.PathFinder.find_spec(ten, [self.goc])
        if ten.startswith('pabt.'):
            return importlib.machinery.PathFinder.find_spec(ten, [str(Path(self.goc) / 'pabt')])
        return None

    def invalidate_caches(self):
        pass


def _bo_pabt():
    for k in [k for k in sys.modules if k == 'pabt' or k.startswith('pabt.')]:
        del sys.modules[k]
    sys.meta_path[:] = [f for f in sys.meta_path if not isinstance(f, _TimTruoc)]


def _ghi(p: Path, noi_dung: str):
    try:
        p.write_text(noi_dung, encoding='utf-8')
    except OSError:
        pass


def _kiem_ban(d: Path, m: dict) -> str:
    """'' nếu bản cập nhật đã cài còn nguyên: đúng mã SHA-256 từng file trong cap_nhat.json, không có file lạ (không dùng chữ ký
    số - người dùng yêu cầu bỏ từ 0.9.16)."""
    import hashlib
    ds = m.get('file') or {}
    # .pyc cũ / giả trong __pycache__ được Python ưu tiên nạp thay file .py đã kiểm tra: xóa, và không ghi lại (nap)
    import shutil
    shutil.rmtree(d / 'pabt' / '__pycache__', ignore_errors=True)
    try:
        la = [f.name for f in (d / 'pabt').iterdir() if f'pabt/{f.name}' not in ds]
    except OSError:
        la = []
    if la:
        return f'có file lạ không thuộc gói cập nhật: {", ".join(la[:5])}.'
    for ten, bam in ds.items():
        if not re.fullmatch(r'pabt/[\w.-]+', ten) or '..' in ten:
            return f'tên file không hợp lệ: {ten}'
        try:
            if hashlib.sha256((d / ten).read_bytes()).hexdigest() != bam:
                return f'file {ten} đã bị sửa sau khi cài.'
        except OSError:
            return f'thiếu file {ten}.'
    return ''


def _dau(d: Path) -> str:
    """Dấu của bản cập nhật đã cài: tên + cỡ + thời điểm sửa mọi file trong pabt\\ (cả .pyc đã biên dịch) và cap_nhat.json, phiên bản
    Python. File nào đổi / thêm / bớt -> dấu khác -> kiểm tra đầy đủ lại."""
    import hashlib
    import hmac
    phan = [sys.implementation.cache_tag or '']
    for p in [d / 'cap_nhat.json'] + sorted(x for x in (d / 'pabt').rglob('*') if x.is_file()):
        st = p.stat()
        phan.append(f'{p.relative_to(d).as_posix()}|{st.st_size}|{st.st_mtime_ns}')
    return hmac.new(_khoa_may(), '\n'.join(phan).encode('utf-8'), hashlib.sha256).hexdigest()


def _khoa_may() -> bytes:
    """1.0.55: khóa HMAC của dấu .da_kiem_tot gắn với máy + bản cài (MachineGuid của Windows, tên máy, đường dẫn PABT.exe): dấu tính /
    chép từ máy khác không khớp -> kiểm đủ lại. Không phải bí mật với người đã vào được máy (cùng tài khoản đọc được các giá trị này)."""
    import hashlib
    guid = ''
    try:
        import winreg
        k = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r'SOFTWARE\Microsoft\Cryptography', 0,
                           winreg.KEY_READ | getattr(winreg, 'KEY_WOW64_64KEY', 0))    # Python 32-bit trên Windows 64-bit: nhánh 64-bit
        guid = str(winreg.QueryValueEx(k, 'MachineGuid')[0])
        winreg.CloseKey(k)
    except (ImportError, OSError):
        pass
    try:
        exe = str(Path(sys.executable).resolve()).lower()
    except OSError:
        exe = sys.executable.lower()
    return hashlib.sha256('|'.join(('LARC_DA_KIEM_1', guid, os.environ.get('COMPUTERNAME', ''), exe)).encode('utf-8')).digest()


def _da_kiem(d: Path) -> bool:
    try:
        return (d / FILE_DA_KIEM).read_text(encoding='utf-8').strip() == _dau(d)
    except (OSError, ValueError):
        return False


def _danh_dau(d: Path) -> None:
    """Sau một lần kiểm đủ (SHA-256 từng file) + nạp thử mọi module tốt: biên dịch sẵn .pyc rồi ghi dấu - các lần mở sau dùng .pyc,
    không băm / nạp thử lại (máy yếu: trước đây mỗi lần mở biên dịch lại ~46.000 dòng mã từ nguồn)."""
    try:
        import compileall
        compileall.compile_dir(str(d / 'pabt'), quiet=1)
        _ghi(d / FILE_DA_KIEM, _dau(d))
    except Exception:                                   # noqa: BLE001 - không ghi được dấu: lần sau kiểm đầy đủ như cũ
        pass


def nap(bat_buoc=False):
    """Trả phiên bản cập nhật đang dùng hoặc None. Chạy từ mã nguồn thì bỏ qua (trừ bat_buoc, dùng khi kiểm thử)."""
    global BAN_GOC, DANG_DUNG
    import pabt
    BAN_GOC = pabt.__version__
    if not (getattr(sys, 'frozen', False) or bat_buoc):
        return None
    d = thu_muc_hien_hanh()
    if d is None or (d / FILE_LOI).exists():
        return None
    try:
        m = json.loads((d / 'cap_nhat.json').read_bytes().decode('utf-8'))
    except (OSError, ValueError):
        return None
    pb = m.get('phien_ban')
    if so(pb) <= so(BAN_GOC) or so(m.get('ban_goc_toi_thieu')) > so(BAN_GOC):
        return None                                  # bộ cài mới hơn bản cập nhật, hoặc bản cài quá cũ
    dem = d.parent / FILE_DEM
    try:
        lan = int(dem.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        lan = 0
    # đường nhanh: đã kiểm đủ ở lần trước, không file nào đổi, lần mở trước tới được cửa sổ chính -> chỉ gắn thư mục cập nhật
    nhanh = lan == 0 and _da_kiem(d)
    if not nhanh:
        try:
            (d / FILE_DA_KIEM).unlink(missing_ok=True)
        except OSError:
            pass
        loi = _kiem_ban(d, m)
        if loi:                                      # bị sửa sau khi cài (mã độc / người khác chép đè): không nạp
            _ghi(d / FILE_LOI, f'Bản cập nhật {pb} không được nạp, dùng bản gốc {BAN_GOC}: {loi}')
            return None
    if lan >= 2:
        _ghi(d / FILE_LOI, f'Bản cập nhật {pb} không khởi động được {lan} lần liền: đã tắt, dùng bản gốc {BAN_GOC}.')
        _ghi(dem, '0')
        return None
    _ghi(dem, str(lan + 1))
    if not nhanh:
        sys.dont_write_bytecode = True               # lần kiểm đủ: không để .pyc chưa kiểm lại trong thư mục cập nhật (xem _kiem_ban)
    _bo_pabt()
    sys.meta_path.insert(0, _TimTruoc(d))
    try:
        importlib.import_module('pabt')
        if not nhanh:                                # nạp thử mọi module (đường nhanh: module nạp khi cần, dùng .pyc đã biên dịch)
            for f in sorted((d / 'pabt').glob('*.py')):
                if f.stem != '__init__':
                    importlib.import_module('pabt.' + f.stem)
    except BaseException:
        _ghi(d / FILE_LOI, f'Không nạp được bản cập nhật {pb}, dùng bản gốc {BAN_GOC}:\n{traceback.format_exc()}')
        _bo_pabt()
        importlib.import_module('pabt')
        return None
    if not nhanh:
        sys.dont_write_bytecode = False
        _danh_dau(d)
    DANG_DUNG = pb
    return pb


def khoi_dong_tot():
    """Phần mềm đã chạy tới cửa sổ chính (hoặc lệnh xong): xóa bộ đếm lần khởi động hỏng."""
    try:
        (thu_muc() / FILE_DEM).unlink(missing_ok=True)
    except OSError:
        pass

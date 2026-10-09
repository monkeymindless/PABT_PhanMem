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
    except OSError:
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
    loi = _kiem_ban(d, m)
    if loi:                                          # bị sửa sau khi cài (mã độc / người khác chép đè): không nạp
        _ghi(d / FILE_LOI, f'Bản cập nhật {pb} không được nạp, dùng bản gốc {BAN_GOC}: {loi}')
        return None
    dem = d.parent / FILE_DEM
    try:
        lan = int(dem.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        lan = 0
    if lan >= 2:
        _ghi(d / FILE_LOI, f'Bản cập nhật {pb} không khởi động được {lan} lần liền: đã tắt, dùng bản gốc {BAN_GOC}.')
        _ghi(dem, '0')
        return None
    _ghi(dem, str(lan + 1))
    sys.dont_write_bytecode = True                   # không để lại .pyc trong thư mục cập nhật (xem _kiem_ban)
    _bo_pabt()
    sys.meta_path.insert(0, _TimTruoc(d))
    try:
        importlib.import_module('pabt')
        for f in sorted((d / 'pabt').glob('*.py')):
            if f.stem != '__init__':
                importlib.import_module('pabt.' + f.stem)
    except BaseException:
        _ghi(d / FILE_LOI, f'Không nạp được bản cập nhật {pb}, dùng bản gốc {BAN_GOC}:\n{traceback.format_exc()}')
        _bo_pabt()
        importlib.import_module('pabt')
        return None
    DANG_DUNG = pb
    return pb


def khoi_dong_tot():
    """Phần mềm đã chạy tới cửa sổ chính (hoặc lệnh xong): xóa bộ đếm lần khởi động hỏng."""
    try:
        (thu_muc() / FILE_DEM).unlink(missing_ok=True)
    except OSError:
        pass

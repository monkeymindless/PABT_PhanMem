"""Gói cập nhật phần mềm (.pabtcn): sửa lỗi, thêm tính năng mà không phải cài lại bộ cài.

Gói là file zip: cap_nhat.json (ung_dung, phien_ban, ban_goc_toi_thieu, ngay, mo_ta, file: {đường dẫn: sha256}), chữ ký số
cap_nhat.sig (RSA-3072 của cap_nhat.json, an_toan.ky) và toàn bộ pabt/*.py cùng file dữ liệu của gói pabt. Tạo bằng
tao_cap_nhat.py (máy dựng có khóa bí mật - tao_khoa_ky.py); cài vào thư mục máy (nap_cap_nhat.thu_muc), có hiệu lực từ lần mở
phần mềm sau (nap_cap_nhat.nap kiểm tra lại chữ ký và mã từng file trước khi nạp). Phần mềm có khóa công khai
(an_toan.KHOA_CONG_KHAI) thì gói thiếu / sai chữ ký bị từ chối: gói giả mạo không chạy được mã trên máy người dùng.
Bản thử nghiệm 0.9.16 đã xóa khóa (KHOA_CONG_KHAI rỗng): gói không ký; bản cài 0.9.13-0.9.15 (có khóa) từ chối gói không ký.
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
FILE_CHU_KY = 'cap_nhat.sig'
UNG_DUNG = 'PABT'
BAN_GOC_TOI_THIEU = '0.8.0'          # bản cài đầu tiên chạy Python 3.8 + Qt5 (Win 7 - 11)
DU_LIEU = ('schema.sql', 'bo_don_gia.sqlite', 'bang_gia_nq28.json', 'bieu_tuong.png')


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


def tao_goi(goc, file_ra, mo_ta: str = '', toi_thieu: str = BAN_GOC_TOI_THIEU, khoa: dict | None = None) -> dict:
    """Đóng gói pabt/ trong thư mục mã nguồn `goc` thành gói cập nhật (phiên bản lấy từ pabt/__init__.py), ký bằng khóa bí
    mật của máy dựng (khoa, mặc định an_toan.doc_khoa_bi_mat())."""
    if khoa is None:                                    # khoa=False: không ký
        # phần mềm không có khóa công khai (bản thử nghiệm): không ký, kể cả khi máy dựng còn khóa bí mật cũ
        khoa = an_toan.doc_khoa_bi_mat() if an_toan.KHOA_CONG_KHAI else False
    if an_toan.KHOA_CONG_KHAI and not khoa:
        raise LoiCapNhat(f'Máy này không có khóa ký gói cập nhật ({an_toan.file_khoa_bi_mat()}): gói không chữ ký sẽ bị '
                         'phần mềm từ chối. Chép khóa bí mật dự phòng về đúng chỗ này rồi tạo lại.')
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
        jb = json.dumps(tt, ensure_ascii=False, indent=1).encode('utf-8')
        z.writestr('cap_nhat.json', jb)
        if khoa:
            ck = an_toan.ky(jb, khoa)
            if an_toan.KHOA_CONG_KHAI and not an_toan.xac_minh(jb, ck):
                raise LoiCapNhat('Khóa bí mật trên máy dựng không khớp khóa công khai trong phần mềm (an_toan.KHOA_CONG_KHAI).')
            z.writestr(FILE_CHU_KY, ck)
    return tt


def _doc_ky(z) -> tuple:
    """(thông tin, nội dung cap_nhat.json gốc, chữ ký) của gói đang mở; kiểm tra chữ ký số khi phần mềm có khóa công khai."""
    try:
        jb = z.read('cap_nhat.json')
        m = json.loads(jb.decode('utf-8'))
    except (KeyError, ValueError) as e:
        raise LoiCapNhat('Gói cập nhật thiếu hoặc hỏng cap_nhat.json.') from e
    try:
        ck = z.read(FILE_CHU_KY).decode('ascii', 'replace')
    except KeyError:
        ck = ''
    if an_toan.KHOA_CONG_KHAI:
        if not ck:
            raise LoiCapNhat('Gói cập nhật không có chữ ký số của nhà phát triển PABT: không cài (có thể là gói giả mạo).')
        if not an_toan.xac_minh(jb, ck):
            raise LoiCapNhat('Chữ ký số của gói cập nhật KHÔNG HỢP LỆ: gói không do nhà phát triển PABT phát hành hoặc đã bị '
                             'sửa. Không cài.')
    return m, jb, ck


def doc_goi(file) -> dict:
    """Đọc và kiểm tra gói: file nén an toàn, chữ ký số, nguyên vẹn từng file; trả thông tin cap_nhat.json."""
    try:
        an_toan.kiem_tra_zip(file, toi_da=100 * 2 ** 20)
    except an_toan.LoiAnToan as e:
        raise LoiCapNhat(f'File không phải gói cập nhật PABT hợp lệ: {e}') from None
    try:
        z = zipfile.ZipFile(file)
    except (OSError, zipfile.BadZipFile) as e:
        raise LoiCapNhat('File không phải gói cập nhật PABT (không đọc được).') from e
    with z:
        m, _, _ = _doc_ky(z)
        if m.get('ung_dung') != UNG_DUNG or not so(m.get('phien_ban')):
            raise LoiCapNhat('File không phải gói cập nhật PABT.')
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
    try:
        an_toan.chan_ma_doc(file, xoa=False)            # Defender / phần mềm diệt virus quét gói trước khi cài
    except an_toan.LoiAnToan as e:
        raise LoiCapNhat(str(e)) from None
    d = thu_muc()
    ten = f'{m["phien_ban"]}_{datetime.datetime.now():%Y%m%d%H%M%S}'
    dich = d / ten
    try:
        (dich / 'pabt').mkdir(parents=True)
        with zipfile.ZipFile(file) as z:
            m, jb, ck = _doc_ky(z)                      # đọc lại từ file (không tin bản đã kiểm tra trước: file có thể đã đổi)
            for f, bam in m['file'].items():
                du = z.read(f)
                if not re.fullmatch(r'pabt/[\w.-]+', f) or _bam(du) != bam:
                    raise LoiCapNhat(f'File {f} trong gói bị đổi trong lúc cài: không cài.')
                (dich / f).write_bytes(du)
        (dich / 'cap_nhat.json').write_bytes(jb)        # giữ nguyên bản đã ký để kiểm tra lại mỗi lần khởi động
        if ck:
            (dich / FILE_CHU_KY).write_text(ck, encoding='ascii')
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

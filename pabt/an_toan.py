"""An toàn dữ liệu: các lớp bảo vệ ở những chỗ phần mềm nhận dữ liệu từ bên ngoài.

PABT không phải phần mềm diệt virus: việc phát hiện mã độc nhờ Microsoft Defender / phần mềm diệt virus đang cài trên máy
(qua MpCmdRun hoặc AMSI - giao diện quét chuẩn của Windows). Module này:
  - quet_file: quét file tải từ web / gói cập nhật / file Word, Excel cũ trước khi mở bằng Word / Excel (có mã độc -> không mở);
  - ngu_canh_tls: kết nối HTTPS bắt buộc kiểm tra chứng chỉ, TLS >= 1.2 (chặn chứng chỉ giả / hết hạn / tự ký);
  - kiem_tra_zip / kiem_tra_xml: chặn file nén "bom" (giải nén ra hàng GB) và XML có thực thể (tấn công "billion laughs");
  - toàn vẹn bản cài: toan_ven.json (SHA-256 mọi file, tạo khi dựng) -> phát hiện file bị sửa / DLL, EXE lạ chèn vào thư mục cài;
  - tinh_trang_diet_virus: phần mềm diệt virus của máy (Trung tâm bảo mật Windows) có bật, có cập nhật không.
Chỉ dùng thư viện chuẩn (chạy cả Python 3.8 bản Windows 7/8).
"""
from __future__ import annotations
import ctypes
import hashlib
import json
import os
import re
import ssl
import subprocess
import sys
import zipfile
from dataclasses import dataclass
from pathlib import Path

TEN_TOAN_VEN = 'toan_ven.json'
DUOI_THUC_THI = ('.exe', '.dll', '.pyd', '.ocx', '.cpl', '.scr', '.com', '.bat', '.cmd', '.ps1', '.vbs', '.js')
_KHONG_CUA_SO = getattr(subprocess, 'CREATE_NO_WINDOW', 0)


class LoiAnToan(Exception):
    pass


# ---------------------------------------------------------------- quét mã độc (Defender / AMSI)
@dataclass
class KetQuaQuet:
    ket_luan: str           # 'sach' | 'doc' (có mã độc) | 'khong_ro' (máy không có bộ quét / quét lỗi)
    mo_ta: str = ''
    cach: str = ''          # 'Microsoft Defender' / 'AMSI' / ''

    @property
    def co_ma_doc(self) -> bool:
        return self.ket_luan == 'doc'


def _mpcmdrun() -> Path | None:
    """MpCmdRun.exe của Microsoft Defender (Windows 8-11) / Microsoft Security Essentials (Windows 7), bản mới nhất."""
    ds = []
    pd = os.environ.get('ProgramData')
    if pd:
        nen = Path(pd) / 'Microsoft' / 'Windows Defender' / 'Platform'
        try:
            ds += sorted((d / 'MpCmdRun.exe' for d in nen.iterdir() if d.is_dir()), reverse=True)
        except OSError:
            pass
    for bien in ('ProgramFiles', 'ProgramW6432'):
        if os.environ.get(bien):
            ds += [Path(os.environ[bien]) / 'Windows Defender' / 'MpCmdRun.exe',
                   Path(os.environ[bien]) / 'Microsoft Security Client' / 'MpCmdRun.exe']
    return next((p for p in ds if p.is_file()), None)


def _quet_defender(p: Path, cho: int = 180) -> KetQuaQuet | None:
    exe = _mpcmdrun()
    if exe is None:
        return None
    try:
        # đường dẫn tuyệt đối: MpCmdRun không hiểu đường dẫn tương đối (báo lỗi 0x80508023)
        r = subprocess.run([str(exe), '-Scan', '-ScanType', '3', '-File', str(p.resolve()), '-DisableRemediation'],
                           capture_output=True, timeout=cho, creationflags=_KHONG_CUA_SO)
    except (OSError, subprocess.TimeoutExpired):
        return None
    # mã thoát 2 dùng chung cho "có mối đe dọa" và lỗi quét (không tìm thấy file, Defender tắt...): đọc nội dung báo cáo
    chu = r.stdout.decode('oem', 'replace')
    so = re.search(r'found (\d+) threats?', chu)
    if r.returncode == 0 and re.search(r'found no threats', chu):
        return KetQuaQuet('sach', 'Microsoft Defender không phát hiện mối đe dọa.', 'Microsoft Defender')
    if r.returncode == 2 and (so and int(so.group(1)) > 0 or 'LIST OF DETECTED THREATS' in chu):
        m = re.search(r'Threat\s*:\s*(.+)', chu)
        return KetQuaQuet('doc', f'Microsoft Defender phát hiện mã độc{": " + m.group(1).strip() if m else ""}.',
                          'Microsoft Defender')
    return None                                         # lỗi quét / Defender tắt (máy dùng phần mềm diệt virus khác): thử AMSI


AMSI_PHAT_HIEN = 32768


def quet_bo_nho(du: bytes, ten: str = 'PABT') -> int | None:
    """Quét nội dung bằng AMSI (Windows 10+): trả AMSI_RESULT (>= 32768 = mã độc) hoặc None nếu máy không có AMSI."""
    if sys.platform != 'win32':
        return None
    try:
        amsi = ctypes.WinDLL('amsi.dll')
    except OSError:
        return None                                     # Windows 7 / 8: không có AMSI
    vp = ctypes.c_void_p
    amsi.AmsiInitialize.argtypes = [ctypes.c_wchar_p, ctypes.POINTER(vp)]
    amsi.AmsiOpenSession.argtypes = [vp, ctypes.POINTER(vp)]
    amsi.AmsiScanBuffer.argtypes = [vp, ctypes.c_char_p, ctypes.c_ulong, ctypes.c_wchar_p, vp, ctypes.POINTER(ctypes.c_int)]
    amsi.AmsiCloseSession.argtypes = [vp, vp]
    amsi.AmsiUninitialize.argtypes = [vp]
    ctx, ses, kq = vp(), vp(), ctypes.c_int(0)
    if amsi.AmsiInitialize('PABT', ctypes.byref(ctx)) != 0:
        return None
    try:
        if amsi.AmsiOpenSession(ctx, ctypes.byref(ses)) != 0:
            return None
        try:
            if amsi.AmsiScanBuffer(ctx, du, len(du), ten, ses, ctypes.byref(kq)) != 0:
                return None
        finally:
            amsi.AmsiCloseSession(ctx, ses)
    finally:
        amsi.AmsiUninitialize(ctx)
    return kq.value


def quet_file(p, cho: int = 180) -> KetQuaQuet:
    """Quét một file bằng Microsoft Defender (quét sâu cả file nén / Office), không được thì AMSI (phần mềm diệt virus khác)."""
    p = Path(p)
    kq = _quet_defender(p, cho)
    if kq is not None:
        return kq
    try:
        if p.stat().st_size <= 64 * 2 ** 20:
            ma = quet_bo_nho(p.read_bytes(), p.name)
            if ma is not None:
                if ma >= AMSI_PHAT_HIEN:
                    return KetQuaQuet('doc', 'Phần mềm diệt virus (AMSI) phát hiện mã độc.', 'AMSI')
                return KetQuaQuet('sach', 'Phần mềm diệt virus (AMSI) không phát hiện mối đe dọa.', 'AMSI')
    except OSError as e:
        return KetQuaQuet('khong_ro', f'Không đọc được file để quét: {e}')
    return KetQuaQuet('khong_ro', 'Máy không có Microsoft Defender / AMSI để quét file (Windows 7 chưa cài phần mềm diệt virus?).')


def chan_ma_doc(p, xoa: bool = True) -> KetQuaQuet:
    """Quét file; có mã độc thì xóa (file tải về) và báo LoiAnToan. Không quét được thì cho qua (trả kết quả 'khong_ro')."""
    kq = quet_file(p)
    if kq.co_ma_doc:
        if xoa:
            try:
                Path(p).unlink()
            except OSError:
                pass
        raise LoiAnToan(f'ĐÃ CHẶN file "{Path(p).name}": {kq.mo_ta} File {"đã bị xóa" if xoa else "không được mở"}.')
    return kq


# ---------------------------------------------------------------- mạng: HTTPS kiểm tra chứng chỉ, TLS >= 1.2
def ngu_canh_tls() -> ssl.SSLContext:
    ctx = ssl.create_default_context()                  # kiểm tra chứng chỉ + tên máy chủ (chặn chứng chỉ giả, tự ký, hết hạn)
    ctx.check_hostname = True
    ctx.verify_mode = ssl.CERT_REQUIRED
    try:
        ctx.minimum_version = ssl.TLSVersion.TLSv1_2
    except (AttributeError, ValueError):
        ctx.options |= getattr(ssl, 'OP_NO_TLSv1', 0) | getattr(ssl, 'OP_NO_TLSv1_1', 0)
    return ctx


# ---------------------------------------------------------------- file nén, XML độc
def kiem_tra_zip(p, toi_da: int = 400 * 2 ** 20, ti_le: int = 250, so_muc: int = 20000) -> None:
    """File Office (.xlsx / .docx) / gói .pabtcn là file nén: chặn "bom nén" (giải nén ra quá lớn) và tên file vượt thư mục."""
    try:
        with zipfile.ZipFile(p) as z:
            ds = z.infolist()
    except (zipfile.BadZipFile, OSError) as e:
        raise LoiAnToan(f'File nén "{Path(p).name}" hỏng: {e}') from None
    if len(ds) > so_muc:
        raise LoiAnToan(f'File "{Path(p).name}" chứa quá nhiều mục ({len(ds)}): nghi file độc, không mở.')
    tong = sum(x.file_size for x in ds)
    nen = max(1, sum(x.compress_size for x in ds))
    if tong > toi_da or tong / nen > ti_le and tong > 50 * 2 ** 20:
        raise LoiAnToan(f'File "{Path(p).name}" giải nén ra {tong / 2 ** 20:.0f} MB (nén {nen / 2 ** 20:.1f} MB): nghi "bom nén", '
                        'không mở.')
    for x in ds:
        if x.filename.startswith(('/', '\\')) or '..' in Path(x.filename).parts or ':' in x.filename:
            raise LoiAnToan(f'File "{Path(p).name}" có đường dẫn nguy hiểm bên trong ({x.filename}): không mở.')


def kiem_tra_xml(du: bytes, ten: str = '') -> None:
    """Chặn XML có khai báo DOCTYPE / ENTITY (tấn công mở rộng thực thể, đọc file máy qua thực thể ngoài)."""
    dau = du[:4096].upper()
    if b'<!DOCTYPE' in dau or b'<!ENTITY' in du.upper():
        raise LoiAnToan(f'Nội dung XML {ten} có khai báo DOCTYPE / ENTITY: nghi file độc, không mở.')


# ---------------------------------------------------------------- toàn vẹn bản cài
def _bam_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for khoi in iter(lambda: f.read(1 << 20), b''):
            h.update(khoi)
    return h.hexdigest()


def tao_toan_ven(goc) -> Path:
    """Ghi <goc>/toan_ven.json: SHA-256 mọi file của bản dựng (gọi khi dựng, sau rut_gon)."""
    goc = Path(goc)
    ds = {f.relative_to(goc).as_posix(): _bam_file(f) for f in sorted(goc.rglob('*'))
          if f.is_file() and f.name != TEN_TOAN_VEN}
    ra = goc / TEN_TOAN_VEN
    ra.write_text(json.dumps(dict(file=ds), ensure_ascii=False, indent=0), encoding='utf-8')
    return ra


def thu_muc_cai() -> Path | None:
    return Path(sys.executable).parent if getattr(sys, 'frozen', False) else None


def kiem_tra_toan_ven(goc=None) -> dict:
    """So file trong thư mục cài với toan_ven.json. Trả dict(co_ban_ghi, so_file, sai=[...], thieu=[...], la=[...]):
    sai = file bị sửa, thieu = file bị xóa, la = file thực thi (.exe/.dll/.pyd...) lạ chèn vào thư mục cài."""
    goc = Path(goc) if goc else thu_muc_cai()
    kq = dict(co_ban_ghi=False, so_file=0, sai=[], thieu=[], la=[])
    if goc is None:
        return kq
    try:
        ds = json.loads((goc / TEN_TOAN_VEN).read_text(encoding='utf-8'))['file']
    except (OSError, ValueError, KeyError):
        return kq
    kq.update(co_ban_ghi=True, so_file=len(ds))
    for ten, bam in ds.items():
        f = goc / ten
        try:
            if _bam_file(f) != bam:
                kq['sai'].append(ten)
        except OSError:
            kq['thieu'].append(ten)
    for f in goc.rglob('*'):
        ten = f.relative_to(goc).as_posix()
        if f.is_file() and f.suffix.lower() in DUOI_THUC_THI and ten not in ds and f.name != 'go_cai_dat.ps1':
            kq['la'].append(ten)
    return kq


def mo_ta_toan_ven(kq: dict) -> tuple:
    """(đạt: bool | None, câu mô tả)."""
    if not kq['co_ban_ghi']:
        return None, 'Chạy từ mã nguồn hoặc bản dựng cũ: không có bản ghi toàn vẹn (toan_ven.json).'
    if not (kq['sai'] or kq['thieu'] or kq['la']):
        return True, f'{kq["so_file"]} file cài đặt nguyên vẹn (đúng mã SHA-256 lúc phát hành).'
    phan = []
    for k, ten in (('sai', 'bị sửa'), ('thieu', 'bị xóa'), ('la', 'thực thi lạ chèn thêm')):
        if kq[k]:
            phan.append(f'{len(kq[k])} file {ten} ({", ".join(kq[k][:3])}{"…" if len(kq[k]) > 3 else ""})')
    return False, 'CẢNH BÁO: ' + '; '.join(phan) + '. Quét virus toàn máy rồi cài lại PABT bằng bộ cài chính thức.'


# ---------------------------------------------------------------- phần mềm diệt virus của máy
def tinh_trang_diet_virus() -> list:
    """[(tên, đang bật, đã cập nhật)] theo Trung tâm bảo mật Windows (root/SecurityCenter2, Windows 7 - 11 bản máy trạm)."""
    if sys.platform != 'win32':
        return []
    lenh = ("Get-WmiObject -Namespace root/SecurityCenter2 -Class AntiVirusProduct | "
            "ForEach-Object { $_.displayName + '|' + $_.productState }")
    try:
        r = subprocess.run(['powershell', '-NoProfile', '-Command', lenh], capture_output=True, timeout=30,
                           creationflags=_KHONG_CUA_SO)
    except (OSError, subprocess.TimeoutExpired):
        return []
    ds = []
    for dong in r.stdout.decode('utf-8', 'replace').splitlines():
        if '|' not in dong:
            continue
        ten, tt = dong.rsplit('|', 1)
        try:
            tt = int(tt.strip())
        except ValueError:
            continue
        ds.append((ten.strip(), (tt >> 12) & 0xF in (1, 3), (tt >> 4) & 0xF == 0))
    return ds


def tong_quan() -> list:
    """Các dòng (mục, đạt: True / False / None, mô tả) cho màn hình "Kiểm tra an toàn"."""
    kq = []
    av = tinh_trang_diet_virus()
    if av:
        bat = [t for t in av if t[1]]
        kq.append(('Phần mềm diệt virus', bool(bat) and all(t[2] for t in bat),
                   '; '.join(f'{t[0]}: {"đang bật" if t[1] else "TẮT"}, {"đã cập nhật" if t[2] else "CHƯA CẬP NHẬT"}' for t in av)))
    else:
        kq.append(('Phần mềm diệt virus', None, 'Không đọc được Trung tâm bảo mật Windows (máy chủ Windows / bị chặn).'))
    co_mp = _mpcmdrun() is not None
    co_amsi = quet_bo_nho(b'PABT kiem tra AMSI', 'kiem_tra') is not None
    kq.append(('Quét file tải về, gói cập nhật', True if (co_mp or co_amsi) else None,
               ', '.join(x for x, c in (('Microsoft Defender', co_mp), ('AMSI', co_amsi)) if c) or
               'Không có bộ quét: file vẫn mở được nhưng không được quét.'))
    kq.append(('Kết nối mạng', True, 'HTTPS kiểm tra chứng chỉ và tên máy chủ, TLS từ 1.2 (chặn chứng chỉ giả, tự ký, hết hạn).'))
    kq.append(('Mở file Word / Excel cũ, xuất PDF', True, 'Word / Excel tự động hóa với macro TẮT (AutomationSecurity = 3).'))
    kq.append(('File nén, XML', True, 'Chặn "bom nén", đường dẫn vượt thư mục, XML có DOCTYPE / ENTITY.'))
    dat, mt = mo_ta_toan_ven(kiem_tra_toan_ven())
    kq.append(('Toàn vẹn bản cài đặt', dat, mt))
    kq.append(('Gói cập nhật (.pabtcn)', None, 'Kiểm tra mã SHA-256 từng file (gói hỏng / bị sửa dở thì không cài) và quét virus '
               'trước khi cài - chỉ cài gói nhận trực tiếp từ người phát triển.'))
    return kq

"""Đóng gói bộ cài PABT bằng IExpress (có sẵn trong Windows) -> thư mục bo_cai\\.

Từ 0.9.26 (người dùng 11/10/2026: "tối giản chỉ 1 bộ cài cho mọi Windows") mặc định chỉ phát hành MỘT bộ cài:
    LARC_Setup_Universal_<ver>.exe  + LARC_ChayNgay_<ver>_Universal.zip (cài dự phòng / chạy ngay; tên bộ cài LARC - người dùng
    15/10/2026, phần mềm bên trong vẫn PABT)
chứa cả dist\\PABT (Python 3.14 + Qt6, 64-bit) và dist\\PABT_Win7 (Python 3.8 + Qt5, 32-bit); cai_dat.ps1 tự chọn theo máy.
Hai bộ riêng (trước 0.9.26) vẫn dựng được khi cần: tham số win10 / win7
    LARC_CaiDat_<ver>_Win10-11_x64.exe  + LARC_ChayNgay_<ver>_x64.zip
    LARC_CaiDat_<ver>_Win7-8-10_x86.exe + LARC_ChayNgay_<ver>_x86.zip

MỘT TIÊU CHUẨN CÀI ĐẶT cho cả hai bản (người dùng yêu cầu: máy nào cũng cài được):
  - cài cho người dùng hiện tại, KHÔNG cần quyền quản trị, KHÔNG cài thêm gì vào Windows: thư viện Visual C++ và UCRT (bản
    Win7-8, ucrt_win7.py) nằm sẵn trong bản dựng - rut_gon.kiem_dll chặn dựng nếu còn DLL ngoài danh sách DLL có sẵn của
    Windows đích (Win7-8: Windows 7 SP1; Win10-11: Windows 10 1809);
  - trình khởi chạy CAI_DAT.cmd (chỉ chữ ASCII) -> PowerShell -Command đọc cai_dat.ps1 thành khối lệnh: không bị
    ExecutionPolicy / Group Policy chặn như -File; PowerShell 2.0 (Windows 7) trở lên;
  - không giải nén zip khi cài: file chương trình nằm phẳng trong bộ cài (f001_<tên> - IExpress không giữ thư mục) +
    danh_sach.txt (nguồn, đích, cỡ, SHA-256): cai_dat.ps1 chép rồi kiểm lại từng file;
  - gói LARC_ChayNgay_*.zip: giải nén là chạy được PABT.exe, HOẶC bấm CAI_DAT.cmd để cài như bộ cài .exe (dùng khi máy
    không chạy được file .exe: diệt virus chặn, tên người dùng có dấu làm vỏ IExpress lỗi…).
Vỏ Win7-8 dựng bằng iexpress 32-bit (SysWOW64) để chạy được trên Windows 32-bit. `LARC_CaiDat_....exe /Q` = cài im lặng.

    .venv\\Scripts\\python bo_cai_win\\dung_bo_cai_win.py [universal] [win10] [win7]     (mặc định: universal)
Cần chạy sau PyInstaller + rut_gon.py (DUNG_BO_CAI.bat). Dùng .venv (cần PyInstaller 6 để đổi biểu tượng vỏ IExpress).
"""
from __future__ import annotations
import hashlib
import os
import re
import shutil
import struct
import subprocess
import sys
import time
import zipfile
from pathlib import Path

GOC = Path(__file__).resolve().parent.parent
BC = GOC / 'bo_cai_win'
RA = GOC / 'bo_cai'
DEV = Path(os.environ['LOCALAPPDATA']) / 'PABT_dev'
WIN = Path(os.environ.get('SystemRoot', r'C:\Windows'))
IEXPRESS = WIN / 'SysWOW64' / 'iexpress.exe'       # vỏ 32-bit: chạy được trên mọi Windows
IEXPRESS_64 = WIN / 'System32' / 'iexpress.exe'
# Bản cập nhật Windows 7 KB3063858 (MS15-063, kernel32 6.1.7601.18847 có AddDllDirectory = nội dung KB2533623) - tải từ
# download.microsoft.com (Update Catalog chỉ còn bản Vista), chữ ký số Microsoft, mã SHA-256 như bản Microsoft phát hành
KB_WIN7 = {
    'Windows6.1-KB3063858-x86.msu': 'a95dda6b57b8012b0ada9543ba667f48a99de8fe93030a8fe8c9d5c2e5c038c1',
    'Windows6.1-KB3063858-x64.msu': '6fec4e38cdcbdaa334937a2ef38bad6800e9c80cb513183451b4049e84479a85',
}

BAN = {
    # Win10-11 không kèm Visual C++ Redistributable (25 MB): Windows 10/11 có sẵn UCRT, DLL Visual C++ PABT cần
    # (vcruntime140, msvcp140...) đã nằm trong bản dựng PyInstaller.
    # tên theo đặc tả ARCH-PABT-2026-V4 mục 9.1 (0.9.24): LARC_CaiDat_<ver>_Win10-11_x64.exe / LARC_ChayNgay_<ver>_x64.zip
    'win10': dict(dist='PABT', ten='Win10-11_x64', zip='x64', vc=None, kien='x64', iexpress=IEXPRESS_64, kb=()),
    # Win7-8: UCRT + Visual C++ đóng sẵn trong bản dựng (ucrt_win7.py) -> không kèm / không cài vc_redist (cần quyền quản trị).
    # Kèm bản cập nhật Windows 7 KB3063858 (có KB2533623 - Python 3.8 cần): cai_dat.ps1 chỉ cài trên Windows 7 còn thiếu.
    # chạy Win 7 SP1 / 8 / 8.1 / Windows 10 32-bit (và cả 64-bit): LARC_CaiDat_<ver>_Win7-8-10_x86.exe / LARC_ChayNgay_<ver>_x86.zip
    'win7': dict(dist='PABT_Win7', ten='Win7-8-10_x86', zip='x86', vc=None, kien='x86', iexpress=IEXPRESS, kb=tuple(KB_WIN7)),
}
MAC_DINH = ('universal',)           # 0.9.26: một bộ cài cho mọi Windows (hai bộ riêng: tham số win10 / win7)
# không bao giờ đóng dữ liệu thật vào bộ cài (CLAUDE.md)
DU_LIEU_CAM = re.compile(r'\.(larc|pabt|pabtdt|xlsm)$|^DS |PABT_CHUAN', re.I)


def phien_ban() -> str:
    m = re.search(r"__version__\s*=\s*'([^']+)'", (GOC / 'pabt' / '__init__.py').read_text(encoding='utf-8'))
    return m.group(1)


def kien_truc(exe) -> str:
    """'x86' / 'x64' theo trường Machine của PE header."""
    with open(exe, 'rb') as f:
        du = f.read(4096)
    pe = struct.unpack_from('<I', du, 0x3C)[0]
    may = struct.unpack_from('<H', du, pe + 4)[0]
    return {0x14C: 'x86', 0x8664: 'x64', 0xAA64: 'arm64'}.get(may, hex(may))


def doi_bieu_tuong(exe: Path, ico: Path) -> None:
    """Gắn biểu tượng PABT cho vỏ IExpress (nhóm biểu tượng id 1 đứng trước biểu tượng gốc của IExpress)."""
    from PyInstaller.utils.win32.icon import CopyIcons_FromIco
    CopyIcons_FromIco(str(exe), [str(ico)])


def _sed(goi: Path, ra: Path, file: list) -> str:
    # ".\" tường minh: máy bật NoDefaultCurrentDirectoryInExePath (chính sách bảo mật) thì cmd không tìm lệnh trong thư mục
    # hiện tại - "cmd /c CAI_DAT.cmd" báo "not recognized" và bộ cài thoát im lặng sau 2 giây (đã gặp khi thử)
    lenh = 'cmd.exe /c .\\CAI_DAT.cmd'
    # ShowInstallProgramWindow=1: ẩn cửa sổ cmd (cửa sổ cài đặt WinForms vẫn hiện)
    dong = ['[Version]', 'Class=IEXPRESS', 'SEDVersion=3', '[Options]', 'PackagePurpose=InstallApp',
            'ShowInstallProgramWindow=1', 'HideExtractAnimation=1', 'UseLongFileName=1', 'InsideCompressed=0',
            'CAB_FixedSize=0', 'CAB_ResvCodeSigning=0', 'RebootMode=N', 'InstallPrompt=%InstallPrompt%',
            'DisplayLicense=%DisplayLicense%', 'FinishMessage=%FinishMessage%', 'TargetName=%TargetName%',
            'FriendlyName=%FriendlyName%', 'AppLaunched=%AppLaunched%', 'PostInstallCmd=%PostInstallCmd%',
            'AdminQuietInstCmd=%AdminQuietInstCmd%', 'UserQuietInstCmd=%UserQuietInstCmd%', 'SourceFiles=SourceFiles',
            '[Strings]', 'InstallPrompt=', 'DisplayLicense=', 'FinishMessage=', f'TargetName={ra}',
            'FriendlyName=LARC - Cai dat', f'AppLaunched={lenh}', 'PostInstallCmd=<None>',
            f'AdminQuietInstCmd={lenh} -Im', f'UserQuietInstCmd={lenh} -Im']
    dong += [f'FILE{i}="{f}"' for i, f in enumerate(file)]
    dong += ['[SourceFiles]', f'SourceFiles0={goi}\\', '[SourceFiles0]'] + [f'%FILE{i}%=' for i in range(len(file))]
    return '\r\n'.join(dong) + '\r\n'


def _ds_chuong_trinh(ban: str) -> list:
    """[(đường dẫn trong thư mục cài, file nguồn)] của bản dựng: chương trình + hướng dẫn + biểu tượng riêng cho lối tắt
    (tránh bộ đệm biểu tượng của Windows). Chặn: chưa dựng / sai kiến trúc / có file dữ liệu / tên có dấu."""
    c = BAN[ban]
    dist = GOC / 'dist' / c['dist']
    exe = dist / 'PABT.exe'
    if not exe.exists():
        raise SystemExit(f'Chưa có {exe}: dựng exe trước (DUNG_BO_CAI.bat).')
    if kien_truc(exe) != c['kien']:
        raise SystemExit(f'{exe} là {kien_truc(exe)}, bộ cài {c["ten"]} cần {c["kien"]}.')
    ct = [(f.relative_to(dist).as_posix(), f) for f in sorted(dist.rglob('*')) if f.is_file()]
    co = {t.lower() for t, _ in ct}
    # PyInstaller 5 (bản Win7) đặt file dữ liệu ở thư mục gốc: HUONG_DAN.md đã có - không thêm lần nữa (0.9.23 trùng tên trong zip)
    # LARC_<ver>.ico: lối tắt trỏ file mang số phiên bản - bộ đệm biểu tượng của Windows giữ ảnh theo đường dẫn (PABT.ico chung mọi
    # bản: đổi biểu tượng mà Desktop / taskbar vẫn hiện ảnh cũ)
    ct += [(t, f) for t, f in (('HUONG_DAN.md', GOC / 'HUONG_DAN.md'), ('PABT.ico', GOC / 'pabt' / 'bieu_tuong.ico'),
                               (f'LARC_{phien_ban()}.ico', GOC / 'pabt' / 'bieu_tuong.ico'))
           if t.lower() not in co]
    for ten, _ in ct:
        if DU_LIEU_CAM.search(ten.rsplit('/', 1)[-1]):
            raise SystemExit(f'Bản dựng có file dữ liệu, không đóng gói: {ten}')
        if not ten.isascii():
            raise SystemExit(f'Tên file có dấu (vỏ IExpress / zip của Windows 7 đọc sai): {ten}')
    return ct


def _chep_phang(goi: Path, ct: list, tien_to: str) -> tuple:
    """Chép phẳng các file vào thư mục gói (IExpress không giữ thư mục): ([tên phẳng], [dòng danh sách exe], [dòng danh sách zip])."""
    phang, ds_exe, ds_zip = [], [], []
    for i, (ten, f) in enumerate(ct, start=1):
        p = f'{tien_to}{i:03d}_{f.name}'            # tên duy nhất, giữ tên gốc cho dễ đọc nhật ký
        shutil.copy2(f, goi / p)
        co, bam = f.stat().st_size, hashlib.sha256(f.read_bytes()).hexdigest()
        dich = ten.replace('/', '\\')
        ds_exe.append(f'{p}\t{dich}\t{co}\t{bam}')
        ds_zip.append(f'{dich}\t{dich}\t{co}\t{bam}')
        phang.append(p)
    return phang, ds_exe, ds_zip


def _ghi_ds(f: Path, dong: list) -> None:
    f.write_bytes(('\r\n'.join(dong) + '\r\n').encode('utf-8'))


def _goi_moi(ten: str) -> Path:
    for cu in DEV.glob(f'goi_{ten}_*'):                 # gói tên phụ của lần dựng trước
        if cu.is_dir():
            shutil.rmtree(cu, ignore_errors=True)
    goi = DEV / f'goi_{ten}'
    if goi.exists():
        shutil.rmtree(goi, ignore_errors=True)
    try:
        goi.mkdir(parents=True)
    except FileExistsError:
        # chạy trong ứng dụng Claude (MSIX ảo hóa %LOCALAPPDATA%): thư mục thật còn đó dù bản ảo đã xóa (12/10/2026) -> tên mới
        goi = DEV / f'goi_{ten}_{os.getpid()}'
        goi.mkdir(parents=True)
    if not str(goi).isascii():
        raise SystemExit(f'IExpress cần đường dẫn không dấu: {goi}')
    return goi


def _chep_cai_dat(goi: Path, ban: str, pb: str) -> list:
    """Script cài / gỡ, ban.txt, phien_ban.txt, biểu tượng vào gói. Trả tên các file đó."""
    for ten, nd in (('ban.txt', ban), ('phien_ban.txt', pb)):
        (goi / ten).write_text(nd, encoding='ascii')
    if not (BC / 'CAI_DAT.cmd').read_bytes().isascii():
        raise SystemExit('CAI_DAT.cmd chỉ được có chữ ASCII (cmd đọc theo bảng mã OEM).')
    for ten in ('CAI_DAT.cmd', 'cai_dat.ps1', 'go_cai_dat.ps1'):
        shutil.copy2(BC / ten, goi / ten)
    shutil.copy2(GOC / 'pabt' / 'bieu_tuong.ico', goi / 'PABT.ico')
    shutil.copy2(GOC / 'pabt' / 'bieu_tuong.png', goi / 'bieu_tuong.png')
    return ['CAI_DAT.cmd', 'cai_dat.ps1', 'go_cai_dat.ps1', 'ban.txt', 'phien_ban.txt', 'PABT.ico', 'bieu_tuong.png']


def _chep_kb(goi: Path, kb: tuple) -> list:
    """Bản cập nhật Windows 7 KB3063858 (bộ cài x86 / phổ quát): kiểm mã băm trước khi đóng gói."""
    for ten in kb:
        f = BC / ten
        if not f.exists():
            raise SystemExit(f'Thiếu {f} (bản cập nhật Windows 7 đóng kèm bộ cài x86): xem KB_WIN7.')
        if hashlib.sha256(f.read_bytes()).hexdigest() != KB_WIN7[ten]:
            raise SystemExit(f'{f.name} sai mã SHA-256: không phải bản Microsoft phát hành.')
        shutil.copy2(f, goi / ten)
    return list(kb)


def _iexpress(goi: Path, file: list, ten_vo: str, iexpress: Path, ra_ten: str) -> Path:
    vo = DEV / f'{ten_vo}.exe'
    vo.unlink(missing_ok=True)
    sed = DEV / f'{ten_vo}.sed'
    sed.write_text(_sed(goi, vo, file), encoding='mbcs')
    subprocess.run([str(iexpress), '/N', '/Q', str(sed)], check=True)
    for _ in range(180):                            # iexpress có thể trả về trước khi ghi xong
        if vo.exists() and time.time() - vo.stat().st_mtime > 2:
            break
        time.sleep(1)
    if not vo.exists():
        raise SystemExit(f'IExpress không tạo được {vo}')
    doi_bieu_tuong(vo, GOC / 'pabt' / 'bieu_tuong.ico')
    RA.mkdir(exist_ok=True)
    dich = RA / ra_ten
    shutil.copy2(vo, dich)
    return dich


def dong_goi(ban: str, pb: str) -> Path:
    c = BAN[ban]
    ct = _ds_chuong_trinh(ban)
    goi = _goi_moi(ban)
    phang, ds_exe, ds_zip = _chep_phang(goi, ct, 'f')
    _ghi_ds(goi / 'danh_sach.txt', ds_exe)
    file = _chep_cai_dat(goi, ban, pb) + ['danh_sach.txt'] + phang
    if c['vc']:
        shutil.copy2(BC / c['vc'], goi / 'vc_redist.exe')
        file.append('vc_redist.exe')
    file += _chep_kb(goi, c['kb'])
    dich = _iexpress(goi, file, f'LARC_CaiDat_{ban}', c['iexpress'], f'LARC_CaiDat_{pb}_{c["ten"]}.exe')
    # gói chạy ngay / cài dự phòng: cây thư mục chương trình (PABT.exe chạy được ngay - giải nén ra USB / ổ D: là dùng) + bộ cài
    # (CAI_DAT.cmd; danh sách: nguồn = đường dẫn trong gói)
    with zipfile.ZipFile(RA / f'LARC_ChayNgay_{pb}_{c["zip"]}.zip', 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for ten, f in ct:
            z.write(f, ten)
        z.writestr('danh_sach.txt', ('\r\n'.join(ds_zip) + '\r\n').encode('utf-8'))
        for ten in ('CAI_DAT.cmd', 'cai_dat.ps1', 'go_cai_dat.ps1', 'ban.txt', 'phien_ban.txt', 'bieu_tuong.png', *c['kb']):
            z.write(goi / ten, ten)
    print(f'{dich.name}: {dich.stat().st_size / 2**20:.1f} MB, vỏ {kien_truc(dich)}, {len(ct)} file')
    return dich


def dong_goi_pho_quat(pb: str) -> Path:
    """PABT_Setup_Universal_<ver>.exe (đặc tả ARCH-PABT-2026-V4 mục 9.2): CẢ HAI bản trong một vỏ IExpress 32-bit (chạy được
    trên Windows 7 32-bit). cai_dat.ps1 (ban.txt = 'universal') tự chọn: Windows 10 1809+ / 11 64-bit -> bản Qt6 x64
    (danh_sach_x64.txt); Windows 7 / 8 / 8.1 / Windows 32-bit -> bản Qt5 x86 (danh_sach_x86.txt) + KB3063858 khi Win 7 còn thiếu.
    Cài như hai bộ cài riêng (cùng cai_dat.ps1): mặc định Program Files (x86), không có quyền quản trị thì thư mục người dùng."""
    goi = _goi_moi('universal')
    file = []
    n, cay, ds_zip = {}, {}, {}
    for ban, tien_to, ten_ds in (('win10', 'a', 'danh_sach_x64.txt'), ('win7', 'b', 'danh_sach_x86.txt')):
        ct = _ds_chuong_trinh(ban)
        phang, ds_exe, dz = _chep_phang(goi, ct, tien_to)
        _ghi_ds(goi / ten_ds, ds_exe)
        file += [ten_ds] + phang
        n[ban], cay[ban] = len(ct), ct
        ds_zip[ten_ds] = [f'{BAN[ban]["zip"]}\\{d}' for d in dz]          # nguồn trong zip: x64\… / x86\…
    file = _chep_cai_dat(goi, 'universal', pb) + file + _chep_kb(goi, BAN['win7']['kb'])
    dich = _iexpress(goi, file, 'LARC_Setup_Universal', IEXPRESS, f'LARC_Setup_Universal_{pb}.exe')
    print(f'{dich.name}: {dich.stat().st_size / 2**20:.1f} MB, vỏ {kien_truc(dich)}, x64 {n["win10"]} + x86 {n["win7"]} file')
    # gói zip dự phòng (máy không chạy được .exe của bộ cài): x64\ và x86\ chạy ngay PABT.exe; CAI_DAT.cmd cài như bộ cài .exe
    # (ban.txt 'universal' -> cai_dat.ps1 tự chọn danh_sach_x64 / x86)
    z_ten = RA / f'LARC_ChayNgay_{pb}_Universal.zip'
    with zipfile.ZipFile(z_ten, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for ban in ('win10', 'win7'):
            for ten, f in cay[ban]:
                z.write(f, f'{BAN[ban]["zip"]}/{ten}')
        for ten_ds, dong in ds_zip.items():
            z.writestr(ten_ds, ('\r\n'.join(dong) + '\r\n').encode('utf-8'))
        for ten in ('CAI_DAT.cmd', 'cai_dat.ps1', 'go_cai_dat.ps1', 'ban.txt', 'phien_ban.txt', 'bieu_tuong.png', 'PABT.ico',
                    *BAN['win7']['kb']):
            z.write(goi / ten, ten)
        z.writestr('DOC_TRUOC.txt', DOC_TRUOC.format(pb=pb).replace('\n', '\r\n').encode('utf-8-sig'))
    print(f'{z_ten.name}: {z_ten.stat().st_size / 2**20:.1f} MB')
    return dich


DOC_TRUOC = """PABT {pb} - goi cai du phong / chay ngay (dung khi file LARC_Setup_Universal_{pb}.exe bi chan)

CÀI ĐẶT: bấm đúp CAI_DAT.cmd - cùng cửa sổ cài như bộ cài .exe, tự chọn bản hợp với máy.
CHẠY NGAY (không cài):
  - Windows 10 (bản 1809 trở lên) / Windows 11, 64-bit: chạy x64\\PABT.exe
  - Windows 7 SP1 / 8 / 8.1, Windows 32-bit: chạy x86\\PABT.exe
Không cần Python, Visual C++ hay kết nối mạng.
"""


def main(argv) -> int:
    pb = phien_ban()
    for ban in (argv or MAC_DINH):
        if ban == 'universal':
            dong_goi_pho_quat(pb)
        else:
            dong_goi(ban, pb)
    return 0


if __name__ == '__main__':
    for luong in (sys.stdout, sys.stderr):
        try:
            luong.reconfigure(encoding='utf-8')
        except (AttributeError, ValueError):
            pass
    sys.exit(main(sys.argv[1:]))

"""Đóng gói 2 bộ cài PABT bằng IExpress (có sẵn trong Windows) -> thư mục bo_cai\\:

    PABT_CaiDat_<ver>_Win10-11.exe  + PABT_ChayNgay_<ver>_Win10-11.zip   (dist\\PABT: Python 3.14 + Qt6, 64-bit)
    PABT_CaiDat_<ver>_Win7-8.exe    + PABT_ChayNgay_<ver>_Win7-8.zip     (dist\\PABT_Win7: Python 3.8 + Qt5, 32-bit)

MỘT TIÊU CHUẨN CÀI ĐẶT cho cả hai bản (người dùng yêu cầu: máy nào cũng cài được):
  - cài cho người dùng hiện tại, KHÔNG cần quyền quản trị, KHÔNG cài thêm gì vào Windows: thư viện Visual C++ và UCRT (bản
    Win7-8, ucrt_win7.py) nằm sẵn trong bản dựng - rut_gon.kiem_dll chặn dựng nếu còn DLL ngoài danh sách DLL có sẵn của
    Windows đích (Win7-8: Windows 7 SP1; Win10-11: Windows 10 1809);
  - trình khởi chạy CAI_DAT.cmd (chỉ chữ ASCII) -> PowerShell -Command đọc cai_dat.ps1 thành khối lệnh: không bị
    ExecutionPolicy / Group Policy chặn như -File; PowerShell 2.0 (Windows 7) trở lên;
  - không giải nén zip khi cài: file chương trình nằm phẳng trong bộ cài (f001_<tên> - IExpress không giữ thư mục) +
    danh_sach.txt (nguồn, đích, cỡ, SHA-256): cai_dat.ps1 chép rồi kiểm lại từng file;
  - gói PABT_ChayNgay_*.zip: giải nén là chạy được PABT.exe, HOẶC bấm CAI_DAT.cmd để cài như bộ cài .exe (dùng khi máy
    không chạy được file .exe: diệt virus chặn, tên người dùng có dấu làm vỏ IExpress lỗi…).
Vỏ Win7-8 dựng bằng iexpress 32-bit (SysWOW64) để chạy được trên Windows 32-bit. `PABT_CaiDat_....exe /Q` = cài im lặng.

    .venv\\Scripts\\python bo_cai_win\\dung_bo_cai_win.py [win10] [win7]     (mặc định cả hai)
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
    'win10': dict(dist='PABT', ten='Win10-11', vc=None, kien='x64', iexpress=IEXPRESS_64, kb=()),
    # Win7-8: UCRT + Visual C++ đóng sẵn trong bản dựng (ucrt_win7.py) -> không kèm / không cài vc_redist (cần quyền quản trị).
    # Kèm bản cập nhật Windows 7 KB3063858 (có KB2533623 - Python 3.8 cần): cai_dat.ps1 chỉ cài trên Windows 7 còn thiếu.
    'win7': dict(dist='PABT_Win7', ten='Win7-8', vc=None, kien='x86', iexpress=IEXPRESS, kb=tuple(KB_WIN7)),
}
# không bao giờ đóng dữ liệu thật vào bộ cài (CLAUDE.md)
DU_LIEU_CAM = re.compile(r'\.(pabt|pabtdt|xlsm)$|^DS |PABT_CHUAN', re.I)


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
            'FriendlyName=PABT - Cai dat', f'AppLaunched={lenh}', 'PostInstallCmd=<None>',
            f'AdminQuietInstCmd={lenh} -Im', f'UserQuietInstCmd={lenh} -Im']
    dong += [f'FILE{i}="{f}"' for i, f in enumerate(file)]
    dong += ['[SourceFiles]', f'SourceFiles0={goi}\\', '[SourceFiles0]'] + [f'%FILE{i}%=' for i in range(len(file))]
    return '\r\n'.join(dong) + '\r\n'


def dong_goi(ban: str, pb: str) -> Path:
    c = BAN[ban]
    dist = GOC / 'dist' / c['dist']
    exe = dist / 'PABT.exe'
    if not exe.exists():
        raise SystemExit(f'Chưa có {exe}: dựng exe trước (DUNG_BO_CAI.bat).')
    if kien_truc(exe) != c['kien']:
        raise SystemExit(f'{exe} là {kien_truc(exe)}, bộ cài {c["ten"]} cần {c["kien"]}.')
    goi = DEV / f'goi_{ban}'
    if goi.exists():
        shutil.rmtree(goi)
    goi.mkdir(parents=True)
    if not str(goi).isascii():
        raise SystemExit(f'IExpress cần đường dẫn không dấu: {goi}')
    # file chương trình: bản dựng + hướng dẫn + biểu tượng riêng cho lối tắt (tránh bộ đệm biểu tượng của Windows)
    ct = [(f.relative_to(dist).as_posix(), f) for f in sorted(dist.rglob('*')) if f.is_file()]
    ct += [('HUONG_DAN.md', GOC / 'HUONG_DAN.md'), ('PABT.ico', GOC / 'pabt' / 'bieu_tuong.ico')]
    for ten, _ in ct:
        if DU_LIEU_CAM.search(ten.rsplit('/', 1)[-1]):
            raise SystemExit(f'Bản dựng có file dữ liệu, không đóng gói: {ten}')
        if not ten.isascii():
            raise SystemExit(f'Tên file có dấu (vỏ IExpress / zip của Windows 7 đọc sai): {ten}')
    phang, ds_exe, ds_zip = [], [], []
    for i, (ten, f) in enumerate(ct, start=1):
        p = f'f{i:03d}_{f.name}'                    # IExpress chép phẳng: tên duy nhất, giữ tên gốc cho dễ đọc nhật ký
        shutil.copy2(f, goi / p)
        co, bam = f.stat().st_size, hashlib.sha256(f.read_bytes()).hexdigest()
        dich = ten.replace('/', '\\')
        ds_exe.append(f'{p}\t{dich}\t{co}\t{bam}')
        ds_zip.append(f'{dich}\t{dich}\t{co}\t{bam}')
        phang.append(p)
    n = len(ct)
    (goi / 'danh_sach.txt').write_bytes(('\r\n'.join(ds_exe) + '\r\n').encode('utf-8'))
    for ten, nd in (('ban.txt', ban), ('phien_ban.txt', pb)):
        (goi / ten).write_text(nd, encoding='ascii')
    if not (BC / 'CAI_DAT.cmd').read_bytes().isascii():
        raise SystemExit('CAI_DAT.cmd chỉ được có chữ ASCII (cmd đọc theo bảng mã OEM).')
    for ten in ('CAI_DAT.cmd', 'cai_dat.ps1', 'go_cai_dat.ps1'):
        shutil.copy2(BC / ten, goi / ten)
    shutil.copy2(GOC / 'pabt' / 'bieu_tuong.ico', goi / 'PABT.ico')
    shutil.copy2(GOC / 'pabt' / 'bieu_tuong.png', goi / 'bieu_tuong.png')
    file = ['CAI_DAT.cmd', 'cai_dat.ps1', 'go_cai_dat.ps1', 'danh_sach.txt', 'ban.txt', 'phien_ban.txt', 'PABT.ico',
            'bieu_tuong.png'] + phang
    if c['vc']:
        shutil.copy2(BC / c['vc'], goi / 'vc_redist.exe')
        file.append('vc_redist.exe')
    for ten in c['kb']:                             # bản cập nhật Windows (Win7-8): kiểm mã băm trước khi đóng gói
        f = BC / ten
        if not f.exists():
            raise SystemExit(f'Thiếu {f} (bản cập nhật Windows 7 đóng kèm bộ cài Win7-8): xem KB_WIN7.')
        if hashlib.sha256(f.read_bytes()).hexdigest() != KB_WIN7[ten]:
            raise SystemExit(f'{f.name} sai mã SHA-256: không phải bản Microsoft phát hành.')
        shutil.copy2(f, goi / ten)
        file.append(ten)
    vo = DEV / f'PABT_CaiDat_{ban}.exe'
    vo.unlink(missing_ok=True)
    sed = DEV / f'goi_{ban}.sed'
    sed.write_text(_sed(goi, vo, file), encoding='mbcs')
    subprocess.run([str(c['iexpress']), '/N', '/Q', str(sed)], check=True)
    for _ in range(120):                            # iexpress có thể trả về trước khi ghi xong
        if vo.exists() and time.time() - vo.stat().st_mtime > 2:
            break
        time.sleep(1)
    if not vo.exists():
        raise SystemExit(f'IExpress không tạo được {vo}')
    doi_bieu_tuong(vo, GOC / 'pabt' / 'bieu_tuong.ico')
    RA.mkdir(exist_ok=True)
    dich = RA / f'PABT_CaiDat_{pb}_{c["ten"]}.exe'
    shutil.copy2(vo, dich)
    # gói chạy ngay / cài dự phòng: cây thư mục chương trình (PABT.exe chạy được ngay) + bộ cài (CAI_DAT.cmd; danh sách: nguồn =
    # đường dẫn trong gói)
    with zipfile.ZipFile(RA / f'PABT_ChayNgay_{pb}_{c["ten"]}.zip', 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for ten, f in ct:
            z.write(f, ten)
        z.writestr('danh_sach.txt', ('\r\n'.join(ds_zip) + '\r\n').encode('utf-8'))
        for ten in ('CAI_DAT.cmd', 'cai_dat.ps1', 'go_cai_dat.ps1', 'ban.txt', 'phien_ban.txt', 'bieu_tuong.png', *c['kb']):
            z.write(goi / ten, ten)
    print(f'{dich.name}: {dich.stat().st_size / 2**20:.1f} MB, vỏ {kien_truc(dich)}, {n} file')
    return dich


def main(argv) -> int:
    pb = phien_ban()
    for ban in (argv or list(BAN)):
        dong_goi(ban, pb)
    return 0


if __name__ == '__main__':
    for luong in (sys.stdout, sys.stderr):
        try:
            luong.reconfigure(encoding='utf-8')
        except (AttributeError, ValueError):
            pass
    sys.exit(main(sys.argv[1:]))

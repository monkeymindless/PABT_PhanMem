"""Đóng gói 2 bộ cài PABT bằng IExpress (có sẵn trong Windows) -> thư mục bo_cai\\:

    PABT_CaiDat_<ver>_Win10-11.exe  + PABT_ChayNgay_<ver>_Win10-11.zip   (dist\\PABT: Python 3.14 + Qt6, 64-bit)
    PABT_CaiDat_<ver>_Win7-8.exe    + PABT_ChayNgay_<ver>_Win7-8.zip     (dist\\PABT_Win7: Python 3.8 + Qt5, 32-bit)

Bộ cài = vỏ IExpress giải nén vào thư mục tạm rồi chạy cai_dat.ps1 (cửa sổ WinForms, PowerShell 2.0 trở lên):
PABT.zip (bản dựng + HUONG_DAN.md + PABT.ico), cai_dat.ps1, go_cai_dat.ps1, vc_redist.exe (chỉ Win7-8), ban.txt (win10 / win7),
phien_ban.txt, so_file.txt, PABT.ico, bieu_tuong.png. Vỏ Win7-8 dựng bằng iexpress 32-bit (SysWOW64) để chạy được trên
Windows 32-bit. `PABT_CaiDat_....exe /Q` = cài im lặng (cai_dat.ps1 -Im).

    .venv\\Scripts\\python bo_cai_win\\dung_bo_cai_win.py [win10] [win7]     (mặc định cả hai)
Cần chạy sau PyInstaller + rut_gon.py (DUNG_BO_CAI.bat). Dùng .venv (cần PyInstaller 6 để đổi biểu tượng vỏ IExpress).
"""
from __future__ import annotations
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

BAN = {
    # Win10-11 không kèm Visual C++ Redistributable (25 MB): Windows 10/11 có sẵn UCRT, DLL Visual C++ PABT cần
    # (vcruntime140, msvcp140...) đã nằm trong bản dựng PyInstaller. Win7-8 vẫn kèm (Windows 7 thiếu UCRT).
    'win10': dict(dist='PABT', ten='Win10-11', vc=None, kien='x64', iexpress=IEXPRESS_64),
    'win7': dict(dist='PABT_Win7', ten='Win7-8', vc='vc_redist_win7.x86.exe', kien='x86', iexpress=IEXPRESS),
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
    lenh = 'powershell.exe -NoProfile -ExecutionPolicy Bypass -STA -WindowStyle Hidden -File cai_dat.ps1'
    dong = ['[Version]', 'Class=IEXPRESS', 'SEDVersion=3', '[Options]', 'PackagePurpose=InstallApp',
            'ShowInstallProgramWindow=0', 'HideExtractAnimation=1', 'UseLongFileName=1', 'InsideCompressed=0',
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
    # PABT.zip: bản dựng + hướng dẫn + biểu tượng riêng cho lối tắt (tránh bộ đệm biểu tượng của Windows)
    them = {'HUONG_DAN.md': GOC / 'HUONG_DAN.md', 'PABT.ico': GOC / 'pabt' / 'bieu_tuong.ico'}
    n = 0
    with zipfile.ZipFile(goi / 'PABT.zip', 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for f in sorted(dist.rglob('*')):
            if f.is_file():
                ten = f.relative_to(dist).as_posix()
                if DU_LIEU_CAM.search(f.name):
                    raise SystemExit(f'Bản dựng có file dữ liệu, không đóng gói: {ten}')
                z.write(f, ten)
                n += 1
        for ten, f in them.items():
            z.write(f, ten)
            n += 1
    for ten, nd in (('ban.txt', ban), ('phien_ban.txt', pb), ('so_file.txt', str(n))):
        (goi / ten).write_text(nd, encoding='ascii')
    shutil.copy2(BC / 'cai_dat.ps1', goi / 'cai_dat.ps1')
    shutil.copy2(BC / 'go_cai_dat.ps1', goi / 'go_cai_dat.ps1')
    shutil.copy2(GOC / 'pabt' / 'bieu_tuong.ico', goi / 'PABT.ico')
    shutil.copy2(GOC / 'pabt' / 'bieu_tuong.png', goi / 'bieu_tuong.png')
    file = ['cai_dat.ps1', 'go_cai_dat.ps1', 'PABT.zip', 'ban.txt', 'phien_ban.txt', 'so_file.txt', 'PABT.ico', 'bieu_tuong.png']
    if c['vc']:
        shutil.copy2(BC / c['vc'], goi / 'vc_redist.exe')
        file.append('vc_redist.exe')
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
    shutil.copy2(goi / 'PABT.zip', RA / f'PABT_ChayNgay_{pb}_{c["ten"]}.zip')
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

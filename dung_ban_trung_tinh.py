r"""Dựng bộ cài BẢN TRUNG TÍNH (24/10/2026): hồ sơ địa phương không có tên đơn vị / địa phương nào (pabt_profile_trung_tinh.json) - để bán cho đơn vị khác.

Chạy DUNG_BAN_TRUNG_TINH.bat (hoặc .venv\Scripts\python dung_ban_trung_tinh.py). Làm như DUNG_BO_CAI.bat nhưng đặt PABT_BAN_TRUNG_TINH=1; kết quả vào
bo_cai\trung_tinh\ (tên thêm _TrungTinh). Bộ cài / gói của chính bạn cùng số phiên bản trong bo_cai\ được cất tạm rồi trả lại nguyên vẹn
(kể cả khi dựng lỗi). Chạy tao_ho_so_trung_tinh.py trước nếu pabt_profile.json vừa đổi cấu trúc.
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

GOC = Path(__file__).resolve().parent
PY = GOC / '.venv' / 'Scripts' / 'python.exe'
BO_CAI = GOC / 'bo_cai'
CHUOI = (
    [str(PY), '-m', 'PyInstaller', '--noconfirm', '--clean', 'PABT.spec'],
    [str(PY), 'bo_cai_win/rut_gon.py', 'dist/PABT'],
    [str(PY), 'bo_cai_win/dung_exe38.py'],
    [str(PY), 'bo_cai_win/rut_gon.py', 'dist/PABT_Win7'],
    [str(PY), 'bo_cai_win/dung_bo_cai_win.py'],
    [str(PY), 'tao_cap_nhat.py', '--mo-ta', 'Bản trung tính'],
)


def phien_ban() -> str:
    m = re.search(r"__version__\s*=\s*'([^']+)'", (GOC / 'pabt' / '__init__.py').read_text(encoding='utf-8'))
    return m.group(1)


def file_cua_ban(ver: str) -> list:
    r"""Các file bộ cài / gói trong bo_cai\ của phiên bản ver (LARC_Setup_Universal_<ver>.exe, LARC_ChayNgay_<ver>_Universal.zip, LARC_CapNhat_<ver>.larcud)."""
    if not BO_CAI.is_dir():
        return []
    mau = re.compile(rf'^LARC_.*_{re.escape(ver)}(_.*)?\.(exe|zip|larcud)$')
    return sorted(f for f in BO_CAI.iterdir() if f.is_file() and mau.match(f.name))


def main() -> int:
    if not PY.exists():
        print('Chưa có .venv: chạy CAI_DAT.bat trước.')
        return 1
    if not (GOC / 'pabt' / 'pabt_profile_trung_tinh.json').exists():
        print('Thiếu pabt\\pabt_profile_trung_tinh.json: chạy tao_ho_so_trung_tinh.py trước.')
        return 1
    ver = phien_ban()
    cat = BO_CAI / '_tam_ban_noi_bo'
    ra = BO_CAI / 'trung_tinh'
    cat.mkdir(parents=True, exist_ok=True)
    ra.mkdir(parents=True, exist_ok=True)
    da_cat = []
    for f in file_cua_ban(ver):                          # cất bản của chính bạn (cùng số phiên bản) - dựng sẽ ghi đè cùng tên
        shutil.move(str(f), str(cat / f.name))
        da_cat.append(f.name)
    ma = 1
    try:
        env = dict(os.environ, PABT_BAN_TRUNG_TINH='1', PYTHONIOENCODING='utf-8')
        for lenh in CHUOI:
            print('>', ' '.join(Path(x).name if i == 0 else x for i, x in enumerate(lenh)), flush=True)
            if subprocess.run(lenh, cwd=str(GOC), env=env).returncode:
                print('Dựng lỗi - dừng.')
                return 1
        for f in file_cua_ban(ver):
            dich = ra / (f.stem + '_TrungTinh' + f.suffix)
            if dich.exists():
                dich.unlink()
            shutil.move(str(f), str(dich))
            print('Đã tạo', dich)
        ma = 0
    finally:
        for ten in da_cat:                               # trả bản của bạn về chỗ cũ
            shutil.move(str(cat / ten), str(BO_CAI / ten))
        try:
            cat.rmdir()
        except OSError:
            pass
    return ma


if __name__ == '__main__':
    sys.exit(main())

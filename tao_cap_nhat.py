r"""Tạo gói cập nhật PABT (.pabtcn) từ mã nguồn hiện tại - sửa lỗi / thêm tính năng cho máy đã cài, không cần cài lại.

  1. Sửa mã trong pabt/, chạy kiểm thử; tăng __version__ trong pabt/__init__.py (phải lớn hơn bản đang cài ở máy dùng).
  2. .venv\Scripts\python tao_cap_nhat.py [--mo-ta "Sửa lỗi ..."] [--toi-thieu 0.8.0] [--ghi-de]
     -> bo_cai\LARC_CapNhat_<phiên bản>.larcud   (đã có gói cùng phiên bản thì dừng, trừ khi có --ghi-de)
  3. Gửi file cho máy dùng: bấm đúp file, hoặc nút "Cập nhật phần mềm" (góc dưới bên phải) > "Cập nhật từ file…".
Một gói dùng cho cả bản Windows 10/11 và Windows 7/8. Gói chỉ chứa mã và dữ liệu gói pabt (không có dự án / hồ sơ). Cần thư viện mới (Python, Qt...) thì dựng bộ cài mới.
"""
from __future__ import annotations
import sys
from pathlib import Path

GOC = Path(__file__).resolve().parent
sys.path.insert(0, str(GOC))

from pabt import cap_nhat  # noqa: E402


def main(argv) -> int:
    ghi_de = '--ghi-de' in argv
    argv = [x for x in argv if x != '--ghi-de']
    tc, i = {}, 0
    while i < len(argv):
        if argv[i].startswith('--') and i + 1 < len(argv):
            tc[argv[i][2:]] = argv[i + 1]
            i += 2
        else:
            i += 1
    import re
    pb = re.search(r"__version__\s*=\s*'([^']+)'", (GOC / 'pabt' / '__init__.py').read_text(encoding='utf-8')).group(1)
    ra = GOC / 'bo_cai' / f'LARC_CapNhat_{pb}{cap_nhat.DUOI}'      # 0.9.94: tên như bộ cài LARC_Setup (trước: PABT_CapNhat)
    if ra.exists() and not ghi_de:
        # hai gói khác nội dung cùng số phiên bản: máy đã cài gói trước sẽ KHÔNG nhận gói sau (so phiên bản bằng nhau)
        print(f'KHÔNG TẠO GÓI: đã có {ra.name}. Tăng __version__ trong pabt/__init__.py, hoặc thêm --ghi-de nếu gói cũ '
              'chưa gửi cho máy nào.')
        return 1
    # gói dùng chung cho bản Windows 10/11 (Python 3.14) và Windows 7/8 (Python 3.8): mã phải dịch được bằng Python 3.8
    import os
    import subprocess
    py38 = Path(os.environ.get('LOCALAPPDATA') or Path.home()) / 'PABT_dev' / 'venv38_32' / 'Scripts' / 'python.exe'
    if py38.exists():
        ds = [str(f) for f in sorted((GOC / 'pabt').glob('*.py'))]
        r = subprocess.run([str(py38), '-c', "import sys\nfor f in sys.argv[1:]: compile(open(f, encoding='utf-8').read(), f, 'exec')",
                            *ds], capture_output=True, text=True, encoding='utf-8', errors='replace')
        if r.returncode:
            print('KHÔNG TẠO ĐƯỢC GÓI: mã không chạy được trên bản Windows 7/8 (Python 3.8):\n' + r.stderr[-1500:])
            return 1
    else:
        print('Chú ý: chưa có môi trường Python 3.8 (CAI_DAT_PHAT_HANH.bat) - chưa kiểm tra được cho bản Windows 7/8.')
    try:
        m = cap_nhat.tao_goi(GOC, ra, tc.get('mo-ta', ''), tc.get('toi-thieu', cap_nhat.BAN_GOC_TOI_THIEU))
        cap_nhat.doc_goi(ra)
    except cap_nhat.LoiCapNhat as e:
        print('KHÔNG TẠO ĐƯỢC GÓI:', e)
        return 1
    print(f'Gói cập nhật: {ra} ({ra.stat().st_size / 1024:.0f} KB, {len(m["file"])} file)')
    print(f'Phiên bản {m["phien_ban"]}, dùng cho bản cài từ {m["ban_goc_toi_thieu"]} trở lên.')
    return 0


if __name__ == '__main__':
    for luong in (sys.stdout, sys.stderr):
        luong.reconfigure(encoding='utf-8')
    sys.exit(main(sys.argv[1:]))

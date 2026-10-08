r"""Tạo cặp khóa ký số gói cập nhật PABT (.pabtcn) - CHỈ chạy một lần trên máy dựng phần mềm.

  .venv\Scripts\python tao_khoa_ky.py            tạo khóa (đã có thì báo, không ghi đè)
  .venv\Scripts\python tao_khoa_ky.py --in       in khóa công khai đang có (để dán vào pabt/an_toan.py KHOA_CONG_KHAI)

Khóa bí mật lưu ở %LOCALAPPDATA%\PABT_dev\khoa_ky_cap_nhat.json - KHÔNG đưa vào mã nguồn, bộ cài, Google Drive dùng chung;
chép dự phòng ra USB cất riêng. Mất khóa bí mật: không ký được gói cập nhật cho các máy đã cài (phải phát hành bộ cài mới có
khóa công khai mới). Lộ khóa bí mật: người khác ký được gói cập nhật giả - tạo khóa mới và phát hành bộ cài mới.
"""
from __future__ import annotations
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from pabt import an_toan  # noqa: E402


def main(argv) -> int:
    f = an_toan.file_khoa_bi_mat()
    if '--in' not in argv:
        if f.exists():
            print(f'Đã có khóa: {f} (không ghi đè).')
        else:
            print('Đang tạo khóa RSA-3072 (vài giây)…')
            k = an_toan.tao_khoa(3072)
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_text(json.dumps(k), encoding='utf-8')
            print(f'Đã tạo khóa bí mật: {f}\nCHÉP DỰ PHÒNG file này ra USB cất riêng; không chia sẻ.')
    k = an_toan.doc_khoa_bi_mat()
    if not k:
        print('Không đọc được khóa.')
        return 1
    print("KHOA_CONG_KHAI = {'n': '" + k['n'] + "', 'e': " + str(k['e']) + '}')
    return 0


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.exit(main(sys.argv[1:]))

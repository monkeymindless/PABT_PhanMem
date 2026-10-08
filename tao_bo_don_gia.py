"""Đóng gói bộ đơn giá tích hợp pabt/bo_don_gia.sqlite từ file PABT Excel chuẩn (chạy trên máy phát triển, trước khi dựng exe).

  .venv\\Scripts\\python tao_bo_don_gia.py <PABT_CHUAN.xlsm> [phiên bản YYYY.MM.DD]

Chỉ lấy danh mục, tham số, biểu thưởng, quy ước, văn bản căn cứ - không lấy hồ sơ hộ, giá đất, danh sách xã của dự án nguồn.
"""
from __future__ import annotations
import sys
from pathlib import Path

from pabt import don_gia

THEO_DOI = [
    ('Dự thảo Quyết định sửa đổi, bổ sung QĐ 42/2025/QĐ-UBND (lấy ý kiến 25/6/2026 - 04/7/2026)', 'UBND thành phố Đồng Nai',
     'Sửa đổi quy định bồi thường, hỗ trợ, tái định cư để thực hiện NQ 254/2025/QH15', 'Theo dõi - chưa thấy ban hành (06/10/2026)'),
]

if __name__ == '__main__':
    for luong in (sys.stdout, sys.stderr):
        luong.reconfigure(encoding='utf-8')
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(2)
    tt = don_gia.tao_bo_tu_excel(sys.argv[1], don_gia.file_goc(), sys.argv[2] if len(sys.argv) > 2 else '',
                                 'QĐ 42/2025, 18/2026 (sửa đổi bởi 53/2026), 48/2025 (sửa đổi bởi 66/2025), 31/2025 của UBND '
                                 'tỉnh (nay là thành phố) Đồng Nai; Luật Đất đai 2024; NĐ 88/2024', THEO_DOI)
    print(f'Đã tạo {tt["file"]}: phiên bản {tt["phien_ban"]}, nguồn {tt["nguon"]}')
    for b, n in tt['dem'].items():
        print(f'  {b}: {n}')

"""Đóng gói bộ đơn giá tích hợp pabt/bo_don_gia.sqlite từ file PABT Excel chuẩn (chạy trên máy phát triển, trước khi dựng exe).

  .venv\\Scripts\\python tao_bo_don_gia.py <PABT_CHUAN.xlsm> [phiên bản YYYY.MM.DD]
  .venv\\Scripts\\python tao_bo_don_gia.py --bo-sung [phiên bản YYYY.MM.DD]   (chỉ thêm BO_SUNG vào bộ đang đóng gói)

Chỉ lấy danh mục, tham số, biểu thưởng, quy ước, văn bản căn cứ - không lấy hồ sơ hộ, giá đất, danh sách xã của dự án nguồn.
Sau đó thêm các mục KHÔNG có trong file Excel nguồn (BO_SUNG: đơn giá vật nuôi QĐ 31/2025/QĐ-UBND - văn bản ghi giá trong điều
khoản, đọc bằng nhap_don_gia.muc_tu_loi_van) và sửa dòng văn bản căn cứ cùng số hiệu (SUA_VAN_BAN).
"""
from __future__ import annotations
import re
import shutil
import sys
import tempfile
from datetime import datetime
from pathlib import Path

from pabt import csdl, don_gia

THEO_DOI = [
    ('Dự thảo Quyết định sửa đổi, bổ sung QĐ 42/2025/QĐ-UBND (lấy ý kiến 25/6/2026 - 04/7/2026)', 'UBND thành phố Đồng Nai',
     'Sửa đổi quy định bồi thường, hỗ trợ, tái định cư để thực hiện NQ 254/2025/QH15', 'Theo dõi - chưa thấy ban hành (06/10/2026)'),
]

# ---------------------------------------------------------------- đơn giá vật nuôi - QĐ 31/2025/QĐ-UBND ngày 29/08/2025
# Tên = đúng tên nhap_don_gia.muc_tu_loi_van đọc từ văn bản (cập nhật lại từ web / file -> "giữ nguyên", không thêm dòng trùng).
# Mã VN.. riêng (mã TS.. do file Excel nguồn đánh số, tránh trùng khi Excel thêm mục). Mục 3 (cây trồng, vật nuôi) của phương án.
_VB31 = 'QĐ 31/2025/QĐ-UBND'
_DK = ('nuôi dưới 50% định mức KT-KT thời gian nuôi', 'nuôi từ 50% đến 80% định mức KT-KT thời gian nuôi')
_GHI_TS = (f' {_VB31}. Mức giá theo thời gian nuôi (dưới 50% / từ 50% đến 80% định mức kinh tế - kỹ thuật thời gian nuôi '
           'trồng thủy sản) ghi tại Điều 4, tương ứng tỷ lệ bồi thường 70% / 50% tại Điều 3')
PHAN_LOAI_VAT_NUOI = f'{don_gia.PHAN_LOAI_VAT_NUOI} ({_VB31})'


def _hai_muc(ten: str, dvt: str, gia: tuple, dieu: str) -> list:
    return [(f'{ten} ({dk})', dvt, g, f'Điều 4 {dieu}{_GHI_TS}') for dk, g in zip(_DK, gia)]


_TOM_LO = 'Ao nuôi tôm nước lợ, cua, kết hợp tôm – cua, nuôi hàu treo giàn bè'
VAT_NUOI_QD31 = (
    _hai_muc(f'{_TOM_LO} - Nuôi quảng canh cải tiến', 'ha/vụ', (20300000, 14500000), 'khoản 1 điểm a')
    + _hai_muc(f'{_TOM_LO} - Nuôi hàu treo giàn bè, nuôi cua, nuôi kết hợp tôm – cua', 'ha/vụ', (20300000, 14500000),
               'khoản 1 điểm a')
    + _hai_muc(f'{_TOM_LO} - Nuôi thâm canh', 'ha/vụ', (145936000, 104240000), 'khoản 1 điểm b')
    + _hai_muc('Ao nuôi tôm nước ngọt - Nuôi quảng canh cải tiến', 'ha/vụ', (20300000, 14500000), 'khoản 2 điểm a')
    + _hai_muc('Ao nuôi tôm nước ngọt - Nuôi thâm canh', 'ha/vụ', (105420000, 75300000), 'khoản 2 điểm b')
    + _hai_muc('Ao nuôi cá - Nuôi ghép cá các loại', 'ha/vụ', (121590000, 86000000), 'khoản 3 điểm a')
    + _hai_muc('Ao nuôi cá - Nuôi thâm canh', 'ha/vụ', (621600000, 440000000), 'khoản 3 điểm b')
    + _hai_muc('Cá nuôi lồng bè', '100m3/vụ', (119650000, 85500000), 'khoản 4')
    + [('Chim yến (theo giá thị trường, tối đa)', 'kg yến thô', 18500000,
        f'Điều 6 {_VB31}: theo giá thị trường nhưng không quá 18.500.000 đ/kg yến thô; giá trị = tổng sản lượng tổ yến một năm '
        '(3 lần thu hoạch) của mỗi nhà nuôi × đơn giá; chỉ tính tổ không có trứng, chim non (Điều 5: cơ sở đã kê khai theo '
        'Điều 54 Luật Chăn nuôi)')])
BO_SUNG = [(f'VN{i}', 3, PHAN_LOAI_VAT_NUOI, ten, dvt, str(gia), ghi)
           for i, (ten, dvt, gia, ghi) in enumerate(VAT_NUOI_QD31, start=1)]
# (số hiệu để tìm dòng cũ, số hiệu, cơ quan, nội dung, trạng thái)
SUA_VAN_BAN = [
    ('31/2025/QĐ-UBND', 'Quyết định 31/2025/QĐ-UBND ngày 29/08/2025 (hiệu lực 10/9/2025)', 'UBND tỉnh (nay là thành phố) Đồng Nai',
     'Đơn giá bồi thường thiệt hại vật nuôi là thủy sản (Điều 4: 16 mức theo hình thức nuôi và thời gian nuôi, ĐVT ha/vụ, '
     '100 m³/vụ) và chim yến (Điều 6) - mã VN1 - VN17; thay thế QĐ 61/2024/QĐ-UBND', 'Đã đưa vào bộ đơn giá (09/10/2026)'),
]


def bo_sung(file, phien_ban: str = '') -> dict:
    """Thêm / thay BO_SUNG vào bộ đơn giá file, sửa văn bản căn cứ theo SUA_VAN_BAN, ghi phiên bản (nếu có)."""
    from pabt.nhap_don_gia import chuan_so_hieu
    con = csdl.mo(file)
    try:
        with con, csdl.mo_khoa_danh_muc(con):
            con.executemany('INSERT OR REPLACE INTO dm_taisan (ma, nhom, phan_loai, ten, dvt, don_gia, ghi_chu) '
                            'VALUES (?,?,?,?,?,?,?)', BO_SUNG)
            for tim, so_hieu, co_quan, noi_dung, trang_thai in SUA_VAN_BAN:
                k = chuan_so_hieu(tim)
                cu = next((r[0] for r in con.execute('SELECT id, so_hieu FROM van_ban ORDER BY id').fetchall()
                           if re.search(r'(?<!\d)' + re.escape(k), chuan_so_hieu(r[1]))), None)
                if cu is None:
                    con.execute('INSERT INTO van_ban (so_hieu, co_quan, noi_dung, trang_thai) VALUES (?,?,?,?)',
                                (so_hieu, co_quan, noi_dung, trang_thai))
                else:
                    con.execute('UPDATE van_ban SET so_hieu = ?, co_quan = ?, noi_dung = ?, trang_thai = ? WHERE id = ?',
                                (so_hieu, co_quan, noi_dung, trang_thai, cu))
            if phien_ban:
                con.execute('UPDATE du_an SET phien_ban_gia = ?, ngay_nhap = ? WHERE id = 1',
                            (phien_ban, datetime.now().isoformat(timespec='seconds')))
        con.execute('VACUUM')
    finally:
        con.close()
    return don_gia.kiem_tra_bo(file)


def chuan_hoa(file, phien_ban: str = '') -> dict:
    """0.9.69 (người dùng 12/10/2026): mã TS / CT / VN / CS (ma_tai_san - bỏ dòng HT / TH trùng của dm_taisan), bỏ quy ước giá
    tương đương gắn sẵn (quy ước tùy biến từng máy / dự án ở Đơn giá đặc biệt). csdl.mo (ghi) nâng lược đồ lên phiên bản mới."""
    from pabt import ma_tai_san, ten_cay_lam_nghiep
    con = csdl.mo(file)
    try:
        kq = ma_tai_san.chuyen_csdl(con)               # đã nâng cấp lúc mở thì không đổi thêm
        kq['ten_khac'] = ten_cay_lam_nghiep.ap_ten_khac(con, ghi_nhat_ky=False)    # 26/10/2026: tên khác cây lâm nghiệp (Phụ lục VI QĐ 48)
        with con, csdl.mo_khoa_danh_muc(con):
            kq['bo_quy_uoc'] = con.execute('DELETE FROM quy_uoc').rowcount
            if phien_ban:
                con.execute('UPDATE du_an SET phien_ban_gia = ?, ngay_nhap = ? WHERE id = 1',
                            (phien_ban, datetime.now().isoformat(timespec='seconds')))
        con.execute('VACUUM')
    finally:
        con.close()
    return kq


def _in(tt: dict):
    print(f'Đã tạo {tt["file"]}: phiên bản {tt["phien_ban"]}, nguồn {tt["nguon"]}')
    for b, n in tt['dem'].items():
        print(f'  {b}: {n}')


if __name__ == '__main__':
    for luong in (sys.stdout, sys.stderr):
        luong.reconfigure(encoding='utf-8')
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(2)
    pb = sys.argv[2] if len(sys.argv) > 2 else ''
    if sys.argv[1] == '--chuan-hoa':                    # đổi mã 0.9.69 + bỏ quy ước gắn sẵn trên bộ đang đóng gói
        goc = don_gia.file_goc()
        with tempfile.TemporaryDirectory() as td:
            tam = Path(td) / goc.name
            shutil.copyfile(goc, tam)
            print(chuan_hoa(tam, pb or datetime.now().strftime('%Y.%m.%d')))
            shutil.copyfile(tam, goc)
        _in(don_gia.thong_tin(goc))
        sys.exit(0)
    if sys.argv[1] == '--bo-sung':                      # thêm vào bộ đang đóng gói (không cần file Excel nguồn)
        goc = don_gia.file_goc()
        with tempfile.TemporaryDirectory() as td:
            tam = Path(td) / goc.name
            shutil.copyfile(goc, tam)
            bo_sung(tam, pb or datetime.now().strftime('%Y.%m.%d'))
            shutil.copyfile(tam, goc)
        _in(don_gia.thong_tin(goc))
        sys.exit(0)
    tt = don_gia.tao_bo_tu_excel(sys.argv[1], don_gia.file_goc(), pb,
                                 'QĐ 42/2025, 18/2026 (sửa đổi bởi 53/2026), 48/2025 (sửa đổi bởi 66/2025), 31/2025 của UBND '
                                 'tỉnh (nay là thành phố) Đồng Nai; Luật Đất đai 2024; NĐ 88/2024', THEO_DOI)
    bo_sung(tt['file'])
    chuan_hoa(tt['file'])
    _in(don_gia.thong_tin(tt['file']))

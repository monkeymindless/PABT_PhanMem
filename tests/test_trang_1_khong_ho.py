"""Dữ liệu GIẢ LẬP dùng chung của test bản Word phương án chi tiết (một hộ, một thửa ghi chú dài). Từ 1.0.19 các test dàn trang Excel
(trang 1 không hở, căn trang) đã bỏ cùng mẫu Excel chi tiết."""
from __future__ import annotations
import os
from pathlib import Path

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

from pabt import csdl                                                            # noqa: E402



GHI_CHU = ('Thửa đất giả lập do hộ gia đình sử dụng ổn định, không tranh chấp, phù hợp quy hoạch, được bồi thường theo quy định '
           'hiện hành; chữ ghi chú dài khoảng năm dòng trên bản in để dòng 1.1 cao như trường hợp thật.')
NGUON = 'Đất giả lập do hộ gia đình khai phá, sử dụng ổn định, không tranh chấp, đã kê khai đăng ký. '


def _du_an(td: Path) -> Path:
    """Một hộ, một thửa (ghi chú dài), mục 2, 3, 4 bằng 0 (không dòng con), mục 5 một dòng 5.1, thưởng."""
    from pabt import du_an_moi
    p = td / 'th.pabt'
    dong = [dict(ho_ten='Nguyễn Văn Thử', dia_chi='Ấp 1', so_to='5', so_thua='101', loai_dat='CLN', dt_thu_hoi='120',
                 vi_tri='1')]
    du_an_moi.tao_du_an(p, dict(ten='Thử', cap_dia_ban='Xã', ten_dia_ban='Mẫu', nam='2026'), dong,
                        [dict(loai_dat='CLN', vi_tri='1', gia='250000')])
    con = csdl.mo(p)
    try:
        with con:
            con.execute('UPDATE ct_dat SET ghi_chu = ?', (GHI_CHU,))
            con.execute('DELETE FROM ct_khoan')
            con.execute("INSERT INTO ct_khoan (muc, ma_ho, thu_tu, ma, ten, dvt, so_luong, don_gia, ty_le, cach_tinh) "
                        "VALUES (4, 1, 1, 'CS3', 'Hỗ trợ ổn định đời sống', 'nhân khẩu', '4', '1500000', '1', "
                        "'4 nhân khẩu x 30 kg gạo x 6 tháng x 15.000 đ')")
    finally:
        con.close()
    return p

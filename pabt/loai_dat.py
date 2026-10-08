"""Danh mục loại đất và ký hiệu: phân loại theo Điều 9 Luật Đất đai năm 2024; ký hiệu theo Thông tư 08/2024/TT-BTNMT
(thống kê, kiểm kê đất đai, lập bản đồ hiện trạng sử dụng đất - nay thuộc Bộ Nông nghiệp và Môi trường), kèm một số ký hiệu
còn gặp trên hồ sơ, bảng giá đất (BHK, NHK). Dùng làm danh sách xổ xuống ô Loại đất của thửa (vẫn gõ tay được, vd ONT+CLN).
Đối chiếu văn bản gốc khi có thay đổi. Không phụ thuộc Qt.
"""
from __future__ import annotations

NONG_NGHIEP, PHI_NONG_NGHIEP, CHUA_SU_DUNG = 'Nông nghiệp', 'Phi nông nghiệp', 'Chưa sử dụng'

LOAI_DAT = [
    # ---- nhóm đất nông nghiệp (NNP)
    ('CHN', 'Đất trồng cây hằng năm', NONG_NGHIEP),
    ('LUA', 'Đất trồng lúa', NONG_NGHIEP),
    ('LUC', 'Đất chuyên trồng lúa', NONG_NGHIEP),
    ('LUK', 'Đất trồng lúa còn lại', NONG_NGHIEP),
    ('HNK', 'Đất trồng cây hằng năm khác', NONG_NGHIEP),
    ('BHK', 'Đất bằng trồng cây hằng năm khác', NONG_NGHIEP),
    ('NHK', 'Đất nương rẫy trồng cây hằng năm khác', NONG_NGHIEP),
    ('CLN', 'Đất trồng cây lâu năm', NONG_NGHIEP),
    ('LNP', 'Đất lâm nghiệp', NONG_NGHIEP),
    ('RDD', 'Đất rừng đặc dụng', NONG_NGHIEP),
    ('RPH', 'Đất rừng phòng hộ', NONG_NGHIEP),
    ('RSX', 'Đất rừng sản xuất', NONG_NGHIEP),
    ('NTS', 'Đất nuôi trồng thủy sản', NONG_NGHIEP),
    ('CNT', 'Đất chăn nuôi tập trung', NONG_NGHIEP),
    ('LMU', 'Đất làm muối', NONG_NGHIEP),
    ('NKH', 'Đất nông nghiệp khác', NONG_NGHIEP),
    # ---- nhóm đất phi nông nghiệp (PNN)
    ('OTC', 'Đất ở', PHI_NONG_NGHIEP),
    ('ONT', 'Đất ở tại nông thôn', PHI_NONG_NGHIEP),
    ('ODT', 'Đất ở tại đô thị', PHI_NONG_NGHIEP),
    ('TSC', 'Đất xây dựng trụ sở cơ quan', PHI_NONG_NGHIEP),
    ('CQP', 'Đất quốc phòng', PHI_NONG_NGHIEP),
    ('CAN', 'Đất an ninh', PHI_NONG_NGHIEP),
    ('DSN', 'Đất xây dựng công trình sự nghiệp', PHI_NONG_NGHIEP),
    ('DTS', 'Đất xây dựng trụ sở của tổ chức sự nghiệp', PHI_NONG_NGHIEP),
    ('DVH', 'Đất xây dựng cơ sở văn hóa', PHI_NONG_NGHIEP),
    ('DXH', 'Đất xây dựng cơ sở dịch vụ xã hội', PHI_NONG_NGHIEP),
    ('DYT', 'Đất xây dựng cơ sở y tế', PHI_NONG_NGHIEP),
    ('DGD', 'Đất xây dựng cơ sở giáo dục và đào tạo', PHI_NONG_NGHIEP),
    ('DTT', 'Đất xây dựng cơ sở thể dục, thể thao', PHI_NONG_NGHIEP),
    ('DKH', 'Đất xây dựng cơ sở khoa học và công nghệ', PHI_NONG_NGHIEP),
    ('DMT', 'Đất xây dựng cơ sở môi trường', PHI_NONG_NGHIEP),
    ('DKT', 'Đất xây dựng cơ sở khí tượng thủy văn', PHI_NONG_NGHIEP),
    ('DNG', 'Đất xây dựng cơ sở ngoại giao', PHI_NONG_NGHIEP),
    ('DSK', 'Đất xây dựng công trình sự nghiệp khác', PHI_NONG_NGHIEP),
    ('CSK', 'Đất sản xuất, kinh doanh phi nông nghiệp', PHI_NONG_NGHIEP),
    ('SKK', 'Đất khu công nghiệp', PHI_NONG_NGHIEP),
    ('SKN', 'Đất cụm công nghiệp', PHI_NONG_NGHIEP),
    ('TMD', 'Đất thương mại, dịch vụ', PHI_NONG_NGHIEP),
    ('SKC', 'Đất cơ sở sản xuất phi nông nghiệp', PHI_NONG_NGHIEP),
    ('SKS', 'Đất sử dụng cho hoạt động khoáng sản', PHI_NONG_NGHIEP),
    ('SKX', 'Đất sản xuất vật liệu xây dựng, làm đồ gốm', PHI_NONG_NGHIEP),
    ('CCC', 'Đất sử dụng vào mục đích công cộng', PHI_NONG_NGHIEP),
    ('DGT', 'Đất công trình giao thông', PHI_NONG_NGHIEP),
    ('DTL', 'Đất công trình thủy lợi', PHI_NONG_NGHIEP),
    ('DNL', 'Đất công trình năng lượng, chiếu sáng công cộng', PHI_NONG_NGHIEP),
    ('DBV', 'Đất công trình bưu chính, viễn thông, công nghệ thông tin', PHI_NONG_NGHIEP),
    ('DCH', 'Đất chợ dân sinh, chợ đầu mối', PHI_NONG_NGHIEP),
    ('DKV', 'Đất khu vui chơi, giải trí công cộng, sinh hoạt cộng đồng', PHI_NONG_NGHIEP),
    ('DRA', 'Đất công trình xử lý chất thải', PHI_NONG_NGHIEP),
    ('DDT', 'Đất có di tích lịch sử - văn hóa', PHI_NONG_NGHIEP),
    ('DDL', 'Đất danh lam thắng cảnh', PHI_NONG_NGHIEP),
    ('TON', 'Đất tôn giáo', PHI_NONG_NGHIEP),
    ('TIN', 'Đất tín ngưỡng', PHI_NONG_NGHIEP),
    ('NTD', 'Đất nghĩa trang, nhà tang lễ, cơ sở hỏa táng; đất cơ sở lưu giữ tro cốt', PHI_NONG_NGHIEP),
    ('SON', 'Đất có mặt nước là sông, ngòi, kênh, rạch, suối', PHI_NONG_NGHIEP),
    ('MNC', 'Đất có mặt nước chuyên dùng', PHI_NONG_NGHIEP),
    ('PNK', 'Đất phi nông nghiệp khác', PHI_NONG_NGHIEP),
    # ---- nhóm đất chưa sử dụng (CSD)
    ('BCS', 'Đất bằng chưa sử dụng', CHUA_SU_DUNG),
    ('DCS', 'Đất đồi núi chưa sử dụng', CHUA_SU_DUNG),
    ('NCS', 'Núi đá không có rừng cây', CHUA_SU_DUNG),
]
TEN = {ma: ten for ma, ten, _ in LOAI_DAT}


def ds_chon(con=None) -> list:
    """[(mã, 'MÃ – tên')] cho ô xổ xuống. con: thêm các mã riêng của danh mục dự án (dm_loaidat) chưa có trong danh sách."""
    ds = [(ma, f'{ma} – {ten}') for ma, ten, _ in LOAI_DAT]
    if con is not None:
        co = {ma for ma, _, _ in LOAI_DAT}
        for r in con.execute('SELECT ma, ten FROM dm_loaidat ORDER BY ma'):
            if r['ma'].upper() not in co:
                ds.append((r['ma'].upper(), f'{r["ma"].upper()} – {r["ten"]}'))
    return ds


def ds_co_gia(con) -> list:
    """[(mã, 'MÃ – tên')] các loại đất có trong danh mục giá của dự án (dùng ở mục 1 - bồi thường về đất)."""
    return [(r['ma'].upper(), f'{r["ma"].upper()} – {r["ten"]}') for r in con.execute('SELECT ma, ten FROM dm_loaidat')]

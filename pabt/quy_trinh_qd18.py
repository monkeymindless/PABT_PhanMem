"""Quy trình 16 bước thu hồi đất, bồi thường, hỗ trợ theo Mục IV QĐ 18/2026/QĐ-UBND và chỗ thực hiện từng bước trong phần mềm
(ma trận trong đặc tả ARCH-PABT-2026-V10, người dùng 13/10/2026). Chưa đối chiếu văn bản gốc: thứ tự và tên bước lấy theo đặc tả."""
from __future__ import annotations

# (bước, công việc, chỗ làm trong phần mềm, tài liệu / kết quả)
BUOC = (
    (1, 'Xây dựng kế hoạch thu hồi đất', '1. Khái toán & dự toán', 'Bảng khái toán tổng mức, kế hoạch vốn'),
    (2, 'Họp dân trong khu vực thu hồi đất', '2. Dự án triển khai', 'Biên bản họp dân phổ biến chủ trương'),
    (3, 'Thông báo thu hồi đất, gửi thông báo', '2. Dự án triển khai', 'Danh sách trích xuất thông báo thu hồi'),
    (4, 'Điều tra, khảo sát, đo đạc, kiểm đếm', '2. Dự án triển khai', 'Danh sách hộ và thửa đất kiểm kê'),
    (5, 'Lập phương án bồi thường, hỗ trợ', '3. Lập phương án', 'Phương án chi tiết từng hộ, bảng áp giá'),
    (6, 'Niêm yết công khai phương án', '3. Lập phương án - Niêm yết & Lấy ý kiến (thẻ 1)', 'Bản dự thảo niêm yết'),
    (7, 'Lấy ý kiến phương án, tổ chức đối thoại', '3. Lập phương án - Niêm yết & Lấy ý kiến (thẻ 2, 3, 4)',
     'Phiếu lấy ý kiến từng hộ, biên bản đối thoại, tổng hợp ý kiến'),
    (8, 'Thẩm định phương án bồi thường', '4. Tổng hợp & trình duyệt', 'Tờ trình thẩm định, bảng tổng hợp kinh phí'),
    (9, 'Quyết định phê duyệt phương án', '5. Phê duyệt & bàn giao', 'Nhập quyết định, phân bổ tiền từng hộ'),
    (10, 'Công khai quyết định phê duyệt', '5. Phê duyệt & bàn giao', 'Bảng niêm yết công khai quyết định phê duyệt'),
    (11, 'Gửi phương án đã duyệt đến từng hộ', '4. Tổng hợp & trình duyệt - Xuất hồ sơ & Bản in', 'Bản chính thức phương án gửi từng hộ'),
    (12, 'Chi trả tiền bồi thường, giao tái định cư', '5. Phê duyệt & bàn giao', 'Danh sách chi trả tiền, biên bản giao tái định cư'),
    (13, 'Ban hành quyết định thu hồi đất', '5. Phê duyệt & bàn giao', 'Danh sách phục vụ quyết định thu hồi đất (mốc 60 / 120 ngày)'),
    (14, 'Xử lý hộ không nhận tiền, không chấp hành', '5. Phê duyệt & bàn giao', 'Sổ nhật ký vận động (10 ngày), danh sách đề nghị cưỡng chế'),
    (15, 'Xử lý hộ không bàn giao mặt bằng', '5. Phê duyệt & bàn giao', 'Biên bản vận động, danh sách cưỡng chế'),
    (16, 'Quản lý mặt bằng sạch đã thu hồi', '5. Phê duyệt & bàn giao', 'Báo cáo tiến độ GPMB (mặt bằng sạch đã bàn giao)'),
)

# bước -> các mốc thời hạn (khóa hồ sơ địa phương thoi_han.*) áp dụng ở bước đó
MOC_CUA_BUOC = {6: ('niem_yet',), 7: ('doi_thoai',), 8: ('tham_dinh',), 13: ('thu_hoi_nn', 'thu_hoi_pnn'), 14: ('van_dong',),
                15: ('van_dong',)}
NHAN_MOC = {'niem_yet': 'Niêm yết công khai', 'doi_thoai': 'Lấy ý kiến, đối thoại', 'tham_dinh': 'Thẩm định phương án',
            'thu_hoi_nn': 'Thông báo thu hồi đất nông nghiệp', 'thu_hoi_pnn': 'Thông báo thu hồi đất phi nông nghiệp',
            'van_dong': 'Vận động trước cưỡng chế (Điều 89)'}


def sla_buoc(buoc: int, ho_so: dict | None = None) -> str:
    """Thời hạn (SLA) của bước theo hồ sơ địa phương, vd "10 ngày"; "" nếu bước không có mốc."""
    from . import dia_phuong
    th = (ho_so or dia_phuong.doc())['thoi_han']
    ds = MOC_CUA_BUOC.get(buoc, ())
    if len(ds) == 2:                                   # bước 13: đất nông nghiệp / phi nông nghiệp
        return f'NN {th[ds[0]]["so_ngay"]} / PNN {th[ds[1]]["so_ngay"]} ngày'
    return f'{th[ds[0]]["so_ngay"]} ngày' if ds else ''


GHI_CHU = ('Thứ tự và tên bước theo ma trận của đặc tả phần mềm; đối chiếu văn bản Quyết định 18/2026/QĐ-UBND (Mục IV) trước khi '
           'dùng làm căn cứ pháp lý. Số ngày (SLA) theo hồ sơ địa phương - sửa ở "Cài đặt → Cấu hình nghiệp vụ…"; dự án đặt riêng '
           'ở "Theo dõi tiến độ → Mốc thời hạn…" thì theo dự án.')

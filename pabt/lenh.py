"""Bảng lệnh cửa sổ chính (tên QAction). CuaSoChinh chỉ gắn tín hiệu — không khai báo lệnh rải trong __init__.

Hàm là lambda gọi lúc bấm (không gắn sẵn bound method): kiểm thử mock.patch.object trên cửa sổ vẫn chặn đúng lệnh.
"""
from __future__ import annotations


# ---------------------------------------------------------------- siêu dữ liệu lệnh (1.0.96: chuyển từ app.py; app nhập lại)
# các trang bên phải cửa sổ chính (chọn ở menu trái). 0.9.76 (Mục IV QĐ 18/2026, Nhóm 5 - 6): Bảng tổng hợp kinh phí là MỘT trang 3 thẻ
# (cơ cấu, chi tiết hộ, đối soát khái toán); Quyết định phê duyệt; Tiến độ chi trả & Bàn giao (1.0.00: gộp trang "Báo cáo tiến độ
# GPMB" - thẻ chỉ số + chế độ xem "Thửa còn vướng" - vào trang theo dõi; man_hinh_theo_doi.KhungTienDo); Dự toán / khái toán (0.9.23 -
# lộ trình người dùng: mục tiêu tài chính của DỰ ÁN, trang trong cửa sổ chính). Ctrl+1..5 theo thứ tự này
TRANG = ['Danh sách hộ', 'Tổng hợp tiền theo phương án', 'Quyết định phê duyệt', 'Theo dõi tiến độ', 'Dự toán & khái toán']
TRANG_DS, TRANG_TONG_HOP, TRANG_QUYET_DINH, TRANG_THEO_DOI, TRANG_DU_TOAN = range(5)
# phím tắt nhanh (người dùng 20/10/2026): Ctrl+1 Danh sách hộ, Ctrl+2 Khái toán & Dự toán, Ctrl+3 Đơn giá bồi thường (tab bộ đơn
# giá), Ctrl+4 Niêm yết & Lấy ý kiến (tab), Ctrl+5 Tiến độ & Bàn giao; Ctrl+K Tìm nhanh (CCCD, mã hộ, họ tên, tờ/thửa, chức năng).
# Tổng hợp tiền / Quyết định phê duyệt không có phím số - mở bằng menu trái hoặc Ctrl+K
PHIM_NHANH = (('Danh sách hộ', 'Ctrl+1'), ('Dự toán & khái toán', 'Ctrl+2'), ('Bộ đơn giá…', 'Ctrl+3'),
              ('Dự thảo PABT…', 'Ctrl+4'), ('Theo dõi tiến độ', 'Ctrl+5'), ('Tìm nhanh…', 'Ctrl+K'))
# phím tắt của lệnh (ngoài Ctrl+số): MỘT bảng - tests/test_dot4_lenh kiểm tên lệnh thật và không trùng phím. 1.0.95 (kiểm toán
# 09/11/2026): thêm Thêm hộ, Tính đơn giá đất, Xuất danh sách hộ (thao tác hằng ngày phải qua 2-3 lần bấm menu)
PHIM_LENH = (('Dự án mới…', 'Ctrl+N'), ('Mở dự án…', 'Ctrl+O'), ('Dự án trên máy chủ…', 'Ctrl+Shift+O'), ('Lưu dự án', 'Ctrl+S'),
             ('Lưu dự án thành…', 'Ctrl+Shift+S'), ('Hướng dẫn sử dụng', 'F1'),
             ('Tiếp nhận & Kiểm tra pháp lý dự án…', 'Ctrl+Shift+L'), ('Quản lý Mẫu in & Bản in…', 'Ctrl+Shift+M'),
             ('Thống kê Hộ · Thửa · Diện tích…', 'Ctrl+Shift+T'), ('Thêm hộ…', 'Ctrl+Shift+H'), ('Tính đơn giá đất…', 'Ctrl+Shift+G'),
             ('Xuất danh sách hộ…', 'Ctrl+Shift+E'))
# 0.9.80: chưa mở dự án thì các lệnh của dự án bị làm mờ (QAction tắt); mở / đóng dự án thì bật / tắt lại. Từ 0.9.88 (thứ tự nhóm
# mới): nhóm 3 (Lập phương án), 4 (Tổng hợp & trình duyệt), 5 (Phê duyệt & bàn giao) + Đơn giá đặc biệt của nhóm 6. Nhóm 1 (khái
# toán), 2, Đơn giá bồi thường, Bảng giá đất và Màn hình chính vẫn dùng được khi chưa có dự án
LENH_CAN_DU_AN = ('Lập phương án hộ…', 'Dự thảo PABT…', 'Kiểm tra lỗi…', 'Xuất báo cáo đối chiếu…',
                  'Tổng hợp tiền theo phương án', 'Đợt trình…', 'In / Xuất…',
                  'Quyết định phê duyệt', 'Theo dõi tiến độ', 'Nhật ký kiểm toán…', 'Xem hộ trên bản đồ…',
                  # nhóm 6 Đơn giá & bảng giá: Đơn giá đặc biệt là của DỰ ÁN (tắt khi chưa mở); Đơn giá bồi thường, Bảng giá đất vẫn
                  # bật (liên kết chân màn hình chào, tra cứu khi chưa có dự án)
                  'Đơn giá riêng dự án…',
                  # 21/10/2026: thống kê Hộ · Thửa · Diện tích (menu Dữ liệu + huy hiệu "Lọc:" cuối hàng lọc danh sách hộ)
                  'Thống kê Hộ · Thửa · Diện tích…',
                  # 30/10/2026: mốc khôi phục của dự án đang mở (menu Tệp tin)
                  'Cỗ máy thời gian (mốc khôi phục)…',
                  'Chọn hộ niêm yết…')
LENH_THONG_KE = 'Thống kê Hộ · Thửa · Diện tích…'
# chữ ngắn trên menu (khóa = tên lệnh đầy đủ trong self.lenh, hiện ở gợi ý khi rê chuột)
NHAN_MENU = {'Lập phương án hộ…': 'Lập phương án chi tiết', 'Thêm hộ…': 'Thêm hộ', 'Xóa hộ…': 'Xóa hộ',
             'Tiếp nhận & Kiểm tra pháp lý dự án…': 'Tiếp nhận hồ sơ pháp lý',
             'Kiểm tra lỗi…': 'Kiểm tra lỗi pháp lý',
             # 0.9.70 (đặc tả ARCH-PABT-2026-V7, người dùng 12/10/2026): chữ trên menu trái theo 6 nhóm nghiệp vụ
             'Dự toán & khái toán': 'Lập khái toán & Dự toán', 'Danh sách hộ': 'Danh sách hộ và Thửa',
             'Theo dõi tiến độ': 'Tiến độ chi trả & Bàn giao',
             'Bộ đơn giá…': 'Đơn giá bồi thường', 'Đơn giá riêng dự án…': 'Đơn giá đặc biệt', 'Rà soát giá…': 'Rà soát giá',
             'Thông tin dự án…': 'Thông tin dự án',
             'Bảng giá đất NQ 28…': 'Bảng giá đất',
             'Cập nhật bảng giá đất…': 'Cập nhật giá đất',
             'Tính đơn giá đất…': 'Tính đơn giá đất',
             'Dự thảo PABT…': 'Niêm yết & Lấy ý kiến',
             'Tổng hợp tiền theo phương án': 'Bảng tổng hợp kinh phí',
             'Quyết định phê duyệt': 'Quyết định phê duyệt', 'Đợt trình…': 'Đợt trình thẩm định',
             'Trạng thái hộ…': 'Trạng thái hộ',
             'In / Xuất…': 'In / Xuất hồ sơ', 'Quản lý Mẫu in & Bản in…': 'Quản lý Mẫu in & Bản in…',
             'Xuất báo cáo đối chiếu…': 'Đối chiếu số liệu'}
# 1.1.07: bỏ lệnh "Nhập bản vẽ CAD (.dxf)…" - từ 05/11/2026 nhập bản đồ ở cửa sổ Bản đồ thửa đất (nút Mở bản đồ, thẻ Nhập vào dự án),
# lệnh cũ chỉ còn lọt ở Tìm nhanh Ctrl+K. Hàm CuaSoChinh.nhap_ban_ve_cad giữ (mở cửa sổ bản đồ ở thẻ Nhập).
# 0.9.69 (người dùng 12/10/2026 đổi tên): gợi ý khi rê chuột theo tên mới (khóa self.lenh giữ tên cũ - mã / test gọi theo khóa)
GOI_Y_MENU = {'Bộ đơn giá…': 'Đơn giá bồi thường (bộ đơn giá nhà, cây, vật nuôi, chính sách hỗ trợ)',
              'Đơn giá riêng dự án…': 'Đơn giá đặc biệt của dự án (nhập tay, thẩm định giá)',
              'Dự thảo PABT…': 'Niêm yết công khai dự thảo phương án và lấy ý kiến',
              'Đợt trình…': 'Đợt trình thẩm định: đợt trình, số phương án, văn bản trình',
              'Dự toán & khái toán': 'Lập khái toán & dự toán (giai đoạn chuẩn bị đầu tư - file .pabtdt riêng)',
              'So sánh với thực tế': 'So sánh khái toán đã duyệt với số liệu áp giá thực tế của dự án',
              'Tiếp nhận & Kiểm tra pháp lý dự án…': 'Tiếp nhận & kiểm tra pháp lý hồ sơ đầu vào (32 mục, thời hạn chủ trương, '
                                                      'kỹ thuật địa chính) - dùng được khi chưa có dự án (Ctrl+Shift+L)',
              'Danh sách hộ': 'Danh sách hộ và thửa đất của dự án',
              'Tổng hợp tiền theo phương án': 'Bảng tổng hợp kinh phí: cơ cấu, chi tiết từng hộ, đối soát khái toán',
              'Xuất báo cáo đối chiếu…': 'Đối chiếu số liệu với file Excel kiểm đếm (xuất báo cáo)',
              'In / Xuất…': 'Xuất hồ sơ & bản in: phương án chi tiết, bảng tổng hợp, tờ trình',
              'Theo dõi tiến độ': 'Tiến độ chi trả & bàn giao: tỷ lệ giải ngân, mặt bằng sạch, thửa còn vướng, mốc thu hồi đất, vận '
                                  'động và cưỡng chế; báo cáo tiến độ GPMB',
              'Quyết định phê duyệt': 'Quản lý quyết định phê duyệt phương án và các hộ của từng quyết định'}
# 1.0.03: lệnh menu trái mở trang nhúng / chế độ - đánh dấu khi đang xem (cùng TRANG và 'Màn hình chính'; app._dong_bo_menu_trai)
LENH_DANH_DAU_PHU = ('Lập phương án hộ…', 'Dự thảo PABT…', 'Bộ đơn giá…', 'So sánh với thực tế')


def ds_lenh(cua) -> list:
    """[(tên QAction, hàm không đối số)]. Thứ tự giữ như cửa sổ chính (menu trái / thanh menu / phím tắt)."""
    return [
        ('Dự án mới…', lambda: cua.du_an_moi()),
        ('Nhập file Excel…', lambda: cua.nhap_excel()),
        ('Mở dự án…', lambda: cua.mo_du_an()),
        ('Nhập phương án chi tiết…', lambda: cua.nhap_chi_tiet()),
        ('Thêm hộ…', lambda: cua.mo_ho_so(moi=True)),
        ('Xóa hộ…', lambda: cua.xoa_ho()),
        ('Lập phương án hộ…', lambda: cua.mo_lap_pa()),
        ('Thông tin dự án…', lambda: cua.sua_du_an()),
        ('Rà soát giá…', lambda: cua.ra_soat_gia()),
        ('In / Xuất…', lambda: cua.in_xuat()),
        ('Quản lý Mẫu in & Bản in…', lambda: cua.quan_ly_mau_in()),
        ('Bộ đơn giá…', lambda: cua.bo_don_gia()),
        ('Đơn giá riêng dự án…', lambda: cua.don_gia_rieng()),
        ('Xuất báo cáo đối chiếu…', lambda: cua.xuat_bao_cao()),
        ('Cập nhật phần mềm…', lambda: cua.cap_nhat_phan_mem()),
        ('Giới thiệu', lambda: cua.gioi_thieu()),
        ('Lưu dự án thành…', lambda: cua.luu_du_an_thanh()),
        ('Đợt trình…', lambda: cua.dot_trinh()),
        ('Cỗ máy thời gian (mốc khôi phục)…', lambda: cua.co_may_thoi_gian()),
        ('Trợ lý (giải thích, soạn nháp)…', lambda: cua.tro_ly()),
        ('Trạng thái hộ…', lambda: cua.trang_thai_ho()),
        ('Kiểm tra lỗi…', lambda: cua.kiem_tra_loi()),
        ('Xuất danh sách hộ…', lambda: cua.xuat_danh_sach()),
        ('Màn hình chính', lambda: cua.ve_trang_chu()),
        ('Bảng giá đất NQ 28…', lambda: cua.bang_gia_dat()),
        ('Dự thảo PABT…', lambda: cua.mo_du_thao()),
        ('So sánh với thực tế', lambda: cua.so_sanh_du_toan()),
        ('Chọn hộ niêm yết…', lambda: cua.chon_ho_niem_yet()),
        ('Cập nhật bảng giá đất…', lambda: cua.cap_nhat_bang_gia_dat()),
        ('Tính đơn giá đất…', lambda: cua.tinh_don_gia_dat()),
        ('Quét file thông minh…', lambda: cua.quet_thong_minh()),
        ('Đóng dự án', lambda: cua.dong_du_an_lenh()),
        ('Xóa dự án…', lambda: cua.xoa_du_an()),
        ('Thoát', lambda: cua.close()),
        ('Hướng dẫn sử dụng', lambda: cua.huong_dan()),
        ('Lưu dự án', lambda: cua.luu_du_an_lenh()),
        ('Kết nối máy chủ LAN…', lambda: cua.thiet_lap_may_chu()),
        ('Phóng to chữ', lambda: cua._phong_to(1)),
        ('Thu nhỏ chữ', lambda: cua._phong_to(-1)),
        ('Cỡ chữ 100%', lambda: cua._phong_to(0)),
        ('Dự án trên máy chủ…', lambda: cua.du_an_may_chu()),
        ('Xuất gói mẫu in & cấu hình…', lambda: cua.xuat_goi_mau()),
        ('Nhập gói mẫu in & cấu hình…', lambda: cua.nhap_goi_mau()),
        ('Tạo gói cấu hình cho nhiều đơn vị…', lambda: cua.tao_goi_don_vi()),
        ('Nhật ký kiểm toán…', lambda: cua.nhat_ky_kiem_toan()),
        ('Cấu hình nghiệp vụ…', lambda: cua.cau_hinh_nghiep_vu()),
        ('Giao diện…', lambda: cua.giao_dien_tuy_chinh()),
        ('Bản đồ thửa đất', lambda: cua.ban_do_thua()),
        ('Xem hộ trên bản đồ…', lambda: cua.xem_ho_tren_ban_do()),
        ('Chẩn đoán & sửa lỗi hệ thống…', lambda: cua.chan_doan_he_thong()),
        ('Phiếu kiểm đếm thực địa…', lambda: cua.phieu_kiem_dem()),
        ('Tiếp nhận & Kiểm tra pháp lý dự án…', lambda: cua.tiep_nhan_phap_ly()),
        ('Tìm nhanh…', lambda: cua.tim_nhanh()),
        (LENH_THONG_KE, lambda: cua.thong_ke_dia_chinh()),
        *((t, (lambda i=i: cua.mo_trang(i))) for i, t in enumerate(TRANG)),
    ]

"""Câu SQL tạo các bảng phụ của file dự án (nhật ký vận động, thửa trên bản đồ, ảnh hiện trạng). Module LÁ (1.1.04): không nhập
module nào của pabt - csdl._tao_bang_phu lấy câu lệnh ở đây thay vì nhập ngược van_dong / ban_do_cad / phieu_kiem_dem (tầng dữ
liệu không kéo tầng nghiệp vụ). Tên cũ van_dong.BANG / _SQL_TAO, ban_do_cad.BANG / SQL_BANG, phieu_kiem_dem.BANG_ANH / SQL_BANG_ANH
vẫn dùng được (cùng đối tượng). Sửa câu lệnh: sửa TẠI ĐÂY."""
from __future__ import annotations

BANG_VAN_DONG = 'nhat_ky_van_dong'
SQL_VAN_DONG = (f'''CREATE TABLE IF NOT EXISTS {BANG_VAN_DONG} (
    id INTEGER PRIMARY KEY,
    ma_ho INTEGER NOT NULL REFERENCES ho(ma_ho) ON UPDATE CASCADE ON DELETE CASCADE,
    viec TEXT NOT NULL, ngay TEXT NOT NULL, hinh_thuc TEXT NOT NULL DEFAULT '', thanh_phan TEXT NOT NULL DEFAULT '',
    noi_dung TEXT NOT NULL DEFAULT '', ket_qua TEXT NOT NULL DEFAULT 'chua_dong_y', bien_ban TEXT NOT NULL DEFAULT '',
    ghi_chu TEXT NOT NULL DEFAULT '')''', f'CREATE INDEX IF NOT EXISTS ix_van_dong_ho ON {BANG_VAN_DONG}(ma_ho, viec)')

BANG_BAN_DO = 'thua_ban_do'
SQL_BAN_DO = f'''CREATE TABLE IF NOT EXISTS {BANG_BAN_DO} (
    id INTEGER PRIMARY KEY,
    so_to TEXT NOT NULL,
    so_thua TEXT NOT NULL,
    loai_dat TEXT NOT NULL DEFAULT '',
    dt_ban_ve TEXT,                     -- diện tích ghi trên nhãn bản vẽ (m²)
    dt_hinh TEXT,                       -- diện tích tính theo hình (m²)
    dt_trong_ranh TEXT,                 -- diện tích nằm trong ranh thu hồi (m²) - trống: không có lớp ranh
    toa_do TEXT NOT NULL,               -- JSON [[x, y], …] hệ tọa độ bản vẽ
    nhan TEXT NOT NULL DEFAULT '',      -- chữ nhãn gốc trong thửa
    lop TEXT NOT NULL DEFAULT '',
    nguon TEXT NOT NULL DEFAULT '',     -- tên file .dxf
    luc TEXT NOT NULL,
    chi_tiet TEXT NOT NULL DEFAULT '',  -- JSON (bản vẽ đường - ban_do_ghep): đối chiếu với nhãn, các phần DT, mốc, ghi chú
    UNIQUE (so_to, so_thua)
)'''

BANG_ANH = 'anh_hien_trang'
SQL_ANH = f'''CREATE TABLE IF NOT EXISTS {BANG_ANH} (
    id INTEGER PRIMARY KEY,
    ma_ho INTEGER NOT NULL REFERENCES ho(ma_ho) ON UPDATE CASCADE ON DELETE CASCADE,
    duong_dan TEXT NOT NULL,             -- đường dẫn đầy đủ của ảnh lúc gắn
    ten_file TEXT NOT NULL,
    khop_theo TEXT NOT NULL DEFAULT '',  -- cccd / ho_ten / stt
    luc TEXT NOT NULL,
    UNIQUE (ma_ho, duong_dan)
)'''

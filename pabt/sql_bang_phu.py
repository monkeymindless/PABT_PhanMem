"""Câu SQL tạo các bảng phụ của file dự án (nhật ký vận động, thửa trên bản đồ, ảnh hiện trạng). Module LÁ (1.1.04): không nhập
module nào của pabt - csdl._tao_bang_phu lấy câu lệnh ở đây thay vì nhập ngược van_dong / ban_do_cad / phieu_kiem_dem (tầng dữ
liệu không kéo tầng nghiệp vụ). Tên cũ van_dong.BANG / _SQL_TAO, ban_do_cad.BANG / SQL_BANG, phieu_kiem_dem.BANG_ANH / SQL_BANG_ANH
vẫn dùng được (cùng đối tượng). Sửa câu lệnh: sửa TẠI ĐÂY."""
from __future__ import annotations

import sqlite3

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

# ---- nhật ký kiểm toán (1.1.05, từ kiem_toan): bảng audit_logs + trigger chặn sửa / xóa, bảng chuỗi băm audit_bam. Tên trigger và
# thân lệnh phải đúng mẫu csdl.trigger_hop_le (trigger bền khác bị gỡ khi mở file) - sửa ở đây thì sửa cả mẫu đó.
BANG_KIEM_TOAN = 'audit_logs'
SQL_KIEM_TOAN = f'''
CREATE TABLE IF NOT EXISTS {BANG_KIEM_TOAN} (
    id        INTEGER PRIMARY KEY,
    luc       TEXT NOT NULL,                 -- ngày giờ máy (YYYY-MM-DDTHH:MM:SS)
    nguoi     TEXT,                          -- tài khoản máy chủ LAN / tài khoản Windows
    may       TEXT,                          -- tên máy tính
    hanh_dong TEXT NOT NULL CHECK (hanh_dong IN ('them', 'sua', 'xoa')),
    bang      TEXT NOT NULL,                 -- ho / thua / ct_dat / ct_khoan / gia_dat / dm_taisan / dm_hotro
    khoa      TEXT,                          -- khóa dòng (mã hộ, mã thửa, mã danh mục…)
    ma_ho     INTEGER,
    ma_thua   INTEGER,
    doi_tuong TEXT,                          -- mô tả người đọc được: họ tên, "Thửa 12 tờ 5", "2.3 Nhà cấp 4"…
    truong    TEXT,                          -- tên cột (sửa); trống khi thêm / xóa cả dòng
    cu        TEXT,
    moi       TEXT,
    thao_tac  TEXT                           -- thao tác (vd "Lưu phương án hộ")
);
CREATE INDEX IF NOT EXISTS ix_audit_logs_ho ON {BANG_KIEM_TOAN}(ma_ho, luc);
CREATE INDEX IF NOT EXISTS ix_audit_logs_luc ON {BANG_KIEM_TOAN}(luc);
CREATE TRIGGER IF NOT EXISTS {BANG_KIEM_TOAN}_khong_sua BEFORE UPDATE ON {BANG_KIEM_TOAN}
BEGIN SELECT RAISE(ABORT, 'Nhật ký kiểm toán không được sửa.'); END;
CREATE TRIGGER IF NOT EXISTS {BANG_KIEM_TOAN}_khong_xoa BEFORE DELETE ON {BANG_KIEM_TOAN}
BEGIN SELECT RAISE(ABORT, 'Nhật ký kiểm toán không được xóa.'); END;
'''

BANG_BAM = 'audit_bam'
SQL_BAM = '''
CREATE TABLE IF NOT EXISTS audit_bam (
    id   INTEGER PRIMARY KEY,                -- = audit_logs.id của dòng được ký
    bam  TEXT NOT NULL                       -- SHA-256 (32 ký tự đầu) nối chuỗi: băm dòng ký trước + nội dung dòng nhật ký
);
CREATE TRIGGER IF NOT EXISTS audit_bam_khong_sua BEFORE UPDATE ON audit_bam
BEGIN SELECT RAISE(ABORT, 'Chuỗi băm kiểm toán không được sửa.'); END;
CREATE TRIGGER IF NOT EXISTS audit_bam_khong_xoa BEFORE DELETE ON audit_bam
BEGIN SELECT RAISE(ABORT, 'Chuỗi băm kiểm toán không được xóa.'); END;
'''


def cau_lenh(sql: str) -> list:
    """Tách script thành câu lệnh (trigger có ';' bên trong BEGIN … END)."""
    kq, dang = [], ''
    for dong in sql.strip().splitlines():
        if dong.strip().startswith('--'):
            continue
        dang += dong + '\n'
        if sqlite3.complete_statement(dang):
            kq.append(dang.strip())
            dang = ''
    return kq


def co_bang(con, ten: str) -> bool:
    return con.execute("SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?", (ten,)).fetchone() is not None

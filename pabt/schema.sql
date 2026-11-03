-- Cơ sở dữ liệu phần mềm PABT (một file .pabt cho mỗi dự án).
-- Số tiền, diện tích, số lượng, đơn giá lưu dạng TEXT (chuỗi số thập phân) để tính bằng Decimal, không sai số.
PRAGMA foreign_keys = ON;

-- ---------------------------------------------------------------- dự án (1 dòng)
CREATE TABLE IF NOT EXISTS du_an (
    id               INTEGER PRIMARY KEY CHECK (id = 1),
    ten              TEXT NOT NULL DEFAULT '',
    ten_day_du       TEXT NOT NULL DEFAULT '',
    don_vi_cap_tren  TEXT NOT NULL DEFAULT '',
    don_vi_lap       TEXT NOT NULL DEFAULT '',
    cap_dia_ban      TEXT NOT NULL DEFAULT 'Phường',   -- Xã / Phường / Thị trấn
    ten_dia_ban      TEXT NOT NULL DEFAULT '',
    so_phuong_an     TEXT NOT NULL DEFAULT '',
    nam              INTEGER,
    can_cu_dinh_kem  TEXT NOT NULL DEFAULT '',
    phien_ban_gia    TEXT NOT NULL DEFAULT '',          -- phiên bản danh mục đơn giá áp dụng
    nguon_nhap       TEXT NOT NULL DEFAULT '',          -- file Excel đã nhập (nếu có)
    ngay_nhap        TEXT NOT NULL DEFAULT '',
    -- in trên bản in (mẫu in không chứa tên đơn vị, người ký cố định)
    ky_hieu_so       TEXT NOT NULL DEFAULT '',          -- phần sau "Số: …/", ví dụ PA-TTPTQĐ
    nguoi_lap        TEXT NOT NULL DEFAULT '',
    nguoi_kiem_tra   TEXT NOT NULL DEFAULT '',
    chuc_vu_ky       TEXT NOT NULL DEFAULT '',
    nguoi_ky         TEXT NOT NULL DEFAULT '',
    don_vi_tieu_de   TEXT NOT NULL DEFAULT '',          -- dòng 2 tiêu đề cơ quan trên bản in, ví dụ CHI NHÁNH VĨNH CỬU
    chu_dau_tu       TEXT NOT NULL DEFAULT '',          -- v14: chủ đầu tư dự án (văn bản trình: nơi nhận)
    co_quan_tham_dinh TEXT NOT NULL DEFAULT '',         -- v15: cơ quan thẩm định phương án (văn bản trình: kính gửi, đề nghị)
    dia_danh_don_vi  TEXT NOT NULL DEFAULT ''           -- 1.0.29: địa danh nơi đơn vị công tác ("Trị An, ngày … tháng …"), không phải xã có đất
);

-- ---------------------------------------------------------------- hồ sơ kiểm kê
CREATE TABLE IF NOT EXISTS ho (
    ma_ho        INTEGER PRIMARY KEY,                 -- mã hộ cố định
    thu_tu       INTEGER NOT NULL,                    -- số thứ tự hiển thị (đánh lại không đổi mã)
    ho_ten       TEXT NOT NULL DEFAULT '',
    so_cccd      TEXT NOT NULL DEFAULT '',
    ngay_cap     TEXT NOT NULL DEFAULT '',
    noi_cap      TEXT NOT NULL DEFAULT '',
    dia_chi      TEXT NOT NULL DEFAULT '',
    dien_thoai   TEXT NOT NULL DEFAULT '',
    phap_ly      TEXT NOT NULL DEFAULT '',
    tranh_chap   TEXT NOT NULL DEFAULT '',
    tai_dinh_cu  TEXT NOT NULL DEFAULT '',
    ghi_chu      TEXT NOT NULL DEFAULT '',
    trang_thai   TEXT NOT NULL DEFAULT 'Chưa lập phương án',
    -- chính sách theo QĐ 42/2025 (dùng cho gợi ý hỗ trợ ở giai đoạn 2)
    phai_di_chuyen  INTEGER NOT NULL DEFAULT 0,
    nhan_khau       INTEGER,
    dt_nn_dang_dung TEXT,                             -- DT đất NN đang sử dụng (tính tỷ lệ thu hồi)
    luu_luc         TEXT,                             -- lần lưu phương án gần nhất trong phần mềm (trống = số liệu nhập từ Excel)
    -- đợt trình và tiến độ xử lý (v7)
    dot_id          INTEGER,                          -- đợt trình phương án (dot_trinh.id); trống = chưa xếp đợt
    da_phe_duyet    INTEGER NOT NULL DEFAULT 0,
    qd_so           TEXT NOT NULL DEFAULT '',         -- quyết định phê duyệt: số, ngày, số tiền, file đính kèm
    qd_ngay         TEXT NOT NULL DEFAULT '',
    qd_so_tien      TEXT NOT NULL DEFAULT '',
    qd_file         TEXT NOT NULL DEFAULT '',
    da_chi_tra      INTEGER NOT NULL DEFAULT 0,
    chi_tra_ngay    TEXT NOT NULL DEFAULT '',
    chi_tra_so_tien TEXT NOT NULL DEFAULT '',
    da_ban_giao     INTEGER NOT NULL DEFAULT 0,
    ban_giao_ngay   TEXT NOT NULL DEFAULT '',
    theo_doi        TEXT NOT NULL DEFAULT '',         -- ghi chú theo dõi tiến độ (danh sách tổng hợp)
    ly_do_ban_giao  TEXT NOT NULL DEFAULT '',         -- v10: lý do chưa bàn giao mặt bằng
    bien_ban_ban_giao TEXT NOT NULL DEFAULT '',        -- v10: file biên bản bàn giao
    so_pa           TEXT NOT NULL DEFAULT '',         -- v11: số phương án chi tiết của hộ (phần trước "/ký hiệu")
    ngay_pa         TEXT NOT NULL DEFAULT '',         -- v11: ngày phương án chi tiết
    du_dieu_kien    INTEGER NOT NULL DEFAULT 0,       -- v13: 1 = đủ điều kiện đưa vào dự thảo lấy ý kiến
    ma_vuong        TEXT NOT NULL DEFAULT '',         -- v13: V1..V5 nhóm vướng pháp lý (trống = không vướng)
    ghi_chu_phap_ly TEXT NOT NULL DEFAULT '',
    dot_du_thao_id  INTEGER                           -- v13: đợt dự thảo gần nhất
);

CREATE TABLE IF NOT EXISTS thua (
    ma_thua      INTEGER PRIMARY KEY,
    ma_ho        INTEGER NOT NULL REFERENCES ho(ma_ho) ON UPDATE CASCADE ON DELETE CASCADE,
    so_to        TEXT NOT NULL DEFAULT '',
    so_thua      TEXT NOT NULL DEFAULT '',
    loai_dat     TEXT NOT NULL DEFAULT '',
    dt_thu_hoi   TEXT NOT NULL DEFAULT '0',
    nguon_goc    TEXT NOT NULL DEFAULT '',
    vi_tri       TEXT NOT NULL DEFAULT '',             -- mô tả vị trí đầy đủ
    thu_tu       INTEGER NOT NULL DEFAULT 0,
    dt_nguyen_thua TEXT NOT NULL DEFAULT '',           -- DT nguyên thửa (m²; trống = chưa nhập) - thêm 20/10/2026, không đổi phiên bản
    so_gcn       TEXT NOT NULL DEFAULT ''              -- số Giấy chứng nhận / số phát hành
);
CREATE INDEX IF NOT EXISTS ix_thua_ho ON thua(ma_ho);

-- ---------------------------------------------------------------- phương án từng hộ
-- Mục 1: bồi thường về đất
CREATE TABLE IF NOT EXISTS ct_dat (
    id           INTEGER PRIMARY KEY,
    ma_ho        INTEGER NOT NULL REFERENCES ho(ma_ho) ON UPDATE CASCADE ON DELETE CASCADE,
    ma_thua      INTEGER REFERENCES thua(ma_thua) ON UPDATE CASCADE ON DELETE SET NULL,
    thu_tu       INTEGER NOT NULL DEFAULT 0,
    loai_dat     TEXT NOT NULL DEFAULT '',
    nhom_dat     TEXT NOT NULL DEFAULT '',
    dien_tich    TEXT NOT NULL DEFAULT '0',
    vi_tri       TEXT NOT NULL DEFAULT '',
    gia_bang_gia TEXT NOT NULL DEFAULT '0',
    he_so_k      TEXT NOT NULL DEFAULT '1',
    ty_le        TEXT NOT NULL DEFAULT '1',
    ghi_chu      TEXT NOT NULL DEFAULT '',
    thanh_tien_excel TEXT,                             -- thành tiền đọc từ file Excel (để đối chiếu)
    cong_thuc    TEXT NOT NULL DEFAULT '',             -- công thức đã gõ ra diện tích
    lan          INTEGER NOT NULL DEFAULT 1            -- v17: lần lập phương án của hộ (1 = lần đầu, 2.. = bổ sung) - pa_lan
);
CREATE INDEX IF NOT EXISTS ix_ctdat_ho ON ct_dat(ma_ho);
CREATE INDEX IF NOT EXISTS ix_ctdat_thua ON ct_dat(ma_thua);

-- Mục 2 (nhà, công trình), mục 3 (cây trồng), mục 7 (vật nuôi - in là mục 4), mục 4 (hỗ trợ - in là mục 5): cùng cấu trúc
CREATE TABLE IF NOT EXISTS ct_khoan (
    id           INTEGER PRIMARY KEY,
    muc          INTEGER NOT NULL CHECK (muc IN (2, 3, 4, 7)),
    ma_ho        INTEGER NOT NULL REFERENCES ho(ma_ho) ON UPDATE CASCADE ON DELETE CASCADE,
    thu_tu       INTEGER NOT NULL DEFAULT 0,
    ma           TEXT NOT NULL DEFAULT '',             -- mã TS / mã hỗ trợ (trống nếu nhập tay)
    ten          TEXT NOT NULL DEFAULT '',
    dvt          TEXT NOT NULL DEFAULT '',
    so_luong     TEXT NOT NULL DEFAULT '0',
    don_gia      TEXT NOT NULL DEFAULT '0',
    ty_le        TEXT NOT NULL DEFAULT '1',
    quy_cach     TEXT NOT NULL DEFAULT '',             -- mục 2, 3: quy cách; mục 4: căn cứ
    ghi_chu      TEXT NOT NULL DEFAULT '',
    nguon_gia    TEXT NOT NULL DEFAULT 'danh mục',     -- danh mục / tương đương / nhập tay
    ma_tuong_duong TEXT NOT NULL DEFAULT '',
    can_cu_gia   TEXT NOT NULL DEFAULT '',             -- căn cứ đơn giá khi áp giá tương đương / nhập tay
    thanh_tien_excel TEXT,
    cach_tinh    TEXT NOT NULL DEFAULT '',             -- mô tả cách tính (in thay ĐVT / SL / ĐG / tỷ lệ), vd khoản hỗ trợ
    cong_thuc    TEXT NOT NULL DEFAULT '',             -- công thức đã gõ ra số lượng (=4,2*5,7), hiện lại khi sửa ô
    lan          INTEGER NOT NULL DEFAULT 1            -- v17: lần lập phương án của hộ
);
CREATE INDEX IF NOT EXISTS ix_ctkhoan_ho ON ct_khoan(ma_ho, muc);
CREATE INDEX IF NOT EXISTS ix_ctdat_lan ON ct_dat(ma_ho, lan);
CREATE INDEX IF NOT EXISTS ix_ctkhoan_lan ON ct_khoan(ma_ho, lan);

-- ---------------------------------------------------------------- danh mục, tham số
CREATE TABLE IF NOT EXISTS dm_taisan (
    ma        TEXT PRIMARY KEY,
    nhom      INTEGER NOT NULL,                        -- 2 nhà, công trình; 3 cây trồng; 4, 5 khác
    phan_loai TEXT NOT NULL DEFAULT '',
    ten       TEXT NOT NULL DEFAULT '',
    dvt       TEXT NOT NULL DEFAULT '',
    don_gia   TEXT,
    ghi_chu   TEXT NOT NULL DEFAULT ''
);
CREATE TABLE IF NOT EXISTS dm_hotro (
    ma        TEXT PRIMARY KEY,
    ten       TEXT NOT NULL DEFAULT '',
    dvt       TEXT NOT NULL DEFAULT '',
    don_gia   TEXT,
    can_cu    TEXT NOT NULL DEFAULT '',
    cach_tinh TEXT NOT NULL DEFAULT '',
    trang_thai TEXT NOT NULL DEFAULT ''
);
CREATE TABLE IF NOT EXISTS dm_loaidat (
    ma TEXT PRIMARY KEY, ten TEXT NOT NULL DEFAULT '', nhom TEXT NOT NULL DEFAULT '', can_cu TEXT NOT NULL DEFAULT ''
);
CREATE TABLE IF NOT EXISTS gia_dat (
    id INTEGER PRIMARY KEY, xa_phuong TEXT NOT NULL DEFAULT '', loai_dat TEXT NOT NULL DEFAULT '',
    vi_tri TEXT NOT NULL DEFAULT '', tuyen_duong TEXT NOT NULL DEFAULT '', gia TEXT, he_so_k TEXT, can_cu TEXT NOT NULL DEFAULT ''
);
CREATE TABLE IF NOT EXISTS dm_xa (
    ma INTEGER PRIMARY KEY, ten TEXT NOT NULL DEFAULT '', loai TEXT NOT NULL DEFAULT '',
    don_vi_cu TEXT NOT NULL DEFAULT '', can_cu TEXT NOT NULL DEFAULT '', trang_thai TEXT NOT NULL DEFAULT ''
);
CREATE TABLE IF NOT EXISTS tham_so (
    ma TEXT PRIMARY KEY, ten TEXT NOT NULL DEFAULT '', gia_tri TEXT, dvt TEXT NOT NULL DEFAULT '',
    can_cu TEXT NOT NULL DEFAULT '', trang_thai TEXT NOT NULL DEFAULT ''
);
CREATE TABLE IF NOT EXISTS bieu_thuong (
    tu   TEXT PRIMARY KEY,                             -- tổng bồi thường, hỗ trợ từ (đồng)
    muc  TEXT NOT NULL                                 -- mức thưởng (đồng/hộ)
);
CREATE TABLE IF NOT EXISTS quy_uoc (
    id INTEGER PRIMARY KEY, ten_thuc_te TEXT NOT NULL DEFAULT '', ten_tuong_duong TEXT NOT NULL DEFAULT '',
    dvt TEXT NOT NULL DEFAULT '', don_gia TEXT, can_cu TEXT NOT NULL DEFAULT ''
);
CREATE TABLE IF NOT EXISTS van_ban (
    id INTEGER PRIMARY KEY, so_hieu TEXT NOT NULL DEFAULT '', co_quan TEXT NOT NULL DEFAULT '',
    noi_dung TEXT NOT NULL DEFAULT '', trang_thai TEXT NOT NULL DEFAULT '', lien_ket TEXT NOT NULL DEFAULT ''
);

-- tổng từng hộ theo file Excel lúc nhập (THEO_DOI) - để đối chiếu khi chạy song song với Excel
CREATE TABLE IF NOT EXISTS tong_excel (
    ma_ho INTEGER PRIMARY KEY, dat TEXT, nha TEXT, cay TEXT, ho_tro TEXT, thuong TEXT, tong TEXT
);

-- ---------------------------------------------------------------- dữ liệu thô đầu vào (vùng riêng, không thuộc vùng đơn giá)
-- giữ nguyên các dòng nhập ở "Dự án mới" (từ Excel hoặc gõ tay) để đối chiếu; ma_ho / ma_thua: hộ, thửa tạo ra từ dòng
CREATE TABLE IF NOT EXISTS tho_nhap (
    id INTEGER PRIMARY KEY, dong INTEGER NOT NULL DEFAULT 0, nguon TEXT NOT NULL DEFAULT '',
    ho_ten TEXT NOT NULL DEFAULT '', dia_chi TEXT NOT NULL DEFAULT '', so_cccd TEXT NOT NULL DEFAULT '',
    ngay_cap TEXT NOT NULL DEFAULT '', noi_cap TEXT NOT NULL DEFAULT '', dien_thoai TEXT NOT NULL DEFAULT '',
    so_to TEXT NOT NULL DEFAULT '', so_thua TEXT NOT NULL DEFAULT '', dt_thu_hoi TEXT NOT NULL DEFAULT '',
    loai_dat TEXT NOT NULL DEFAULT '', vi_tri TEXT NOT NULL DEFAULT '', nhan_khau TEXT NOT NULL DEFAULT '',
    nguon_goc TEXT NOT NULL DEFAULT '', ghi_chu TEXT NOT NULL DEFAULT '', ma_ho INTEGER, ma_thua INTEGER
);

-- ---------------------------------------------------------------- đợt trình, cài đặt dự án, quy chuẩn (v7; không thuộc danh mục khóa)
CREATE TABLE IF NOT EXISTS dot_trinh (
    id INTEGER PRIMARY KEY, so INTEGER NOT NULL DEFAULT 0, ten TEXT NOT NULL DEFAULT '',
    ngay_trinh TEXT NOT NULL DEFAULT '', so_to_trinh TEXT NOT NULL DEFAULT '', ghi_chu TEXT NOT NULL DEFAULT '',
    thu_muc TEXT NOT NULL DEFAULT '',                 -- thư mục hồ sơ đợt đã xuất gần nhất
    loai_van_ban TEXT NOT NULL DEFAULT 'Tờ trình',    -- v11: văn bản trình: Tờ trình / Văn bản (số, ngày: so_to_trinh, ngay_trinh)
    so_pa_tong TEXT NOT NULL DEFAULT '',              -- v11: số phương án tổng của đợt (in vào bảng tổng hợp)
    ngay_pa_tong TEXT NOT NULL DEFAULT '',            -- v11: ngày phương án tổng
    ky_hieu_so TEXT NOT NULL DEFAULT ''               -- v15: ký hiệu số phương án của đợt (phần sau "Số: …/"); trống = của dự án
);
CREATE TABLE IF NOT EXISTS cai_dat (ma TEXT PRIMARY KEY, gia_tri TEXT NOT NULL DEFAULT '');
-- mật độ cây trồng dùng tách cây trong / ngoài mật độ (mặc định đọc từ ghi chú danh mục "Mật độ N cây/ha")
CREATE TABLE IF NOT EXISTS quy_chuan_mat_do (
    ten_cay TEXT PRIMARY KEY, mat_do TEXT NOT NULL DEFAULT '', ty_le_ngoai TEXT NOT NULL DEFAULT '0', can_cu TEXT NOT NULL DEFAULT ''
);

-- ---------------------------------------------------------------- nhật ký
CREATE TABLE IF NOT EXISTS nhat_ky (
    id INTEGER PRIMARY KEY, thoi_gian TEXT NOT NULL, may TEXT NOT NULL DEFAULT '', nguoi_dung TEXT NOT NULL DEFAULT '',
    viec TEXT NOT NULL DEFAULT '', chi_tiet TEXT NOT NULL DEFAULT ''
);

-- ---------------------------------------------------------------- quyết định phê duyệt, chi trả (v10)
-- một quyết định (tổng / bổ sung) phê duyệt nhiều hộ; một hộ có thể có nhiều quyết định (phê duyệt bổ sung).
-- Các cột da_phe_duyet, qd_*, da_chi_tra, chi_tra_* của bảng ho là phần tóm tắt, tính lại từ qd_ho (theo_doi.dong_bo_ho).
CREATE TABLE IF NOT EXISTS quyet_dinh (
    id INTEGER PRIMARY KEY,
    so TEXT NOT NULL DEFAULT '', ngay TEXT NOT NULL DEFAULT '',
    trich_yeu TEXT NOT NULL DEFAULT '',               -- "Phê duyệt PA đợt 2", "Phê duyệt bổ sung"...
    tong_tien TEXT NOT NULL DEFAULT '',               -- tổng kinh phí ghi trong quyết định (để đối chiếu)
    file TEXT NOT NULL DEFAULT '', ghi_chu TEXT NOT NULL DEFAULT ''
);
CREATE TABLE IF NOT EXISTS qd_ho (
    id INTEGER PRIMARY KEY,
    qd_id INTEGER NOT NULL REFERENCES quyet_dinh(id) ON DELETE CASCADE,
    ma_ho INTEGER NOT NULL REFERENCES ho(ma_ho) ON UPDATE CASCADE ON DELETE CASCADE,
    so_tien TEXT NOT NULL DEFAULT '',                 -- số tiền phê duyệt của hộ trong quyết định
    tien_dat TEXT NOT NULL DEFAULT '', tien_tai_san TEXT NOT NULL DEFAULT '', tien_cay TEXT NOT NULL DEFAULT '',
    tien_ho_tro TEXT NOT NULL DEFAULT '', tien_thuong TEXT NOT NULL DEFAULT '',
    so_pa TEXT NOT NULL DEFAULT '', ngay_pa TEXT NOT NULL DEFAULT '',          -- phương án chi tiết số, ngày
    qd_ct_so TEXT NOT NULL DEFAULT '', qd_ct_ngay TEXT NOT NULL DEFAULT '',    -- quyết định chi tiết số, ngày ban hành
    da_chi_tra INTEGER NOT NULL DEFAULT 0, chi_tra_ngay TEXT NOT NULL DEFAULT '', chi_tra_so_tien TEXT NOT NULL DEFAULT '',
    chung_tu TEXT NOT NULL DEFAULT '',                -- file biên lai / biên bản chi trả
    ly_do_chua_nhan TEXT NOT NULL DEFAULT '', ghi_chu TEXT NOT NULL DEFAULT '',
    lan INTEGER NOT NULL DEFAULT 0,                   -- v17: lần phương án được quyết định này phê duyệt (0 = trước v17: cả hộ)
    UNIQUE (qd_id, ma_ho)
);
CREATE INDEX IF NOT EXISTS qd_ho_ma_ho ON qd_ho (ma_ho);
-- v17: các lần lập phương án chi tiết của một hộ (lần đầu + bổ sung) - mỗi lần một bộ dòng ct_dat / ct_khoan (cột lan), số / ngày
-- phương án riêng, khóa sau khi có quyết định phê duyệt (sửa lần đã duyệt làm sai quyết định cũ)
CREATE TABLE IF NOT EXISTS pa_lan (
    id INTEGER PRIMARY KEY,
    ma_ho INTEGER NOT NULL REFERENCES ho(ma_ho) ON UPDATE CASCADE ON DELETE CASCADE,
    lan INTEGER NOT NULL,
    ten TEXT NOT NULL DEFAULT '',
    ngay_lap TEXT NOT NULL DEFAULT '',
    so_pa TEXT NOT NULL DEFAULT '', ngay_pa TEXT NOT NULL DEFAULT '',
    trang_thai TEXT NOT NULL DEFAULT 'dang_lap',      -- dang_lap / da_phe_duyet
    khoa INTEGER NOT NULL DEFAULT 0,                  -- 1: chỉ xem (đã có quyết định)
    ghi_chu TEXT NOT NULL DEFAULT '',
    loai TEXT NOT NULL DEFAULT 'bo_sung',             -- 1.0.15: chinh (lần đầu) / bo_sung / dieu_chinh (sửa sai lần đã duyệt)
    thay_the INTEGER NOT NULL DEFAULT 0,              -- lần điều chỉnh: số lần bị thay thế (0 = không thay lần nào)
    dot_trinh_id INTEGER,                             -- 30/10/2026: đợt trình thẩm định của LẦN này (ho.dot_id = đợt gần nhất của hộ)
    UNIQUE (ma_ho, lan)
);

-- ---------------------------------------------------------------- dự thảo phương án, niêm yết, lấy ý kiến (v13)
-- Niêm yết 10 ngày, đối thoại không quá 30 ngày. Hộ vướng pháp lý không đưa vào đợt.
CREATE TABLE IF NOT EXISTS dot_du_thao (
    id INTEGER PRIMARY KEY,
    ten TEXT NOT NULL DEFAULT '',
    ngay_bat_dau TEXT NOT NULL DEFAULT '',
    ngay_ket_thuc TEXT NOT NULL DEFAULT '',
    dia_diem TEXT NOT NULL DEFAULT '',
    so_bb_bat_dau TEXT NOT NULL DEFAULT '',
    so_bb_ket_thuc TEXT NOT NULL DEFAULT '',
    ngay_hop TEXT NOT NULL DEFAULT '',
    han_doi_thoai TEXT NOT NULL DEFAULT '',
    trang_thai TEXT NOT NULL DEFAULT 'dang_niem_yet',
    ghi_chu TEXT NOT NULL DEFAULT ''
);
CREATE TABLE IF NOT EXISTS y_kien_du_thao (
    id INTEGER PRIMARY KEY,
    dot_id INTEGER NOT NULL REFERENCES dot_du_thao(id) ON DELETE CASCADE,
    ma_ho INTEGER NOT NULL REFERENCES ho(ma_ho) ON UPDATE CASCADE ON DELETE CASCADE,
    loai TEXT NOT NULL DEFAULT 'chua',
    nhom TEXT NOT NULL DEFAULT '',
    noi_dung TEXT NOT NULL DEFAULT '',
    huong_xu_ly TEXT NOT NULL DEFAULT '',
    so_tien_chenh TEXT NOT NULL DEFAULT '0',
    ket_qua_doi_thoai TEXT NOT NULL DEFAULT '',
    chuyen_dot_id INTEGER,
    ngay_cap_nhat TEXT NOT NULL DEFAULT '',
    lan INTEGER,                                      -- 30/10/2026: lần phương án được niêm yết (NULL = dòng cũ = lần 1)
    UNIQUE (dot_id, ma_ho)
);
CREATE TABLE IF NOT EXISTS doi_thoai_ho (
    id INTEGER PRIMARY KEY,
    dot_id INTEGER NOT NULL REFERENCES dot_du_thao(id) ON DELETE CASCADE,
    ma_ho INTEGER NOT NULL,
    lan INTEGER NOT NULL DEFAULT 1,
    ngay TEXT NOT NULL DEFAULT '',
    dia_diem TEXT NOT NULL DEFAULT '',
    thanh_phan TEXT NOT NULL DEFAULT '',
    dien_bien TEXT NOT NULL DEFAULT '',
    ket_luan TEXT NOT NULL DEFAULT '',
    bien_ban_so TEXT NOT NULL DEFAULT ''
);
CREATE INDEX IF NOT EXISTS ix_ykien_dot_ho ON y_kien_du_thao(dot_id, ma_ho);
CREATE INDEX IF NOT EXISTS ix_doithoai_ho ON doi_thoai_ho(dot_id, ma_ho);

-- ---------------------------------------------------------------- sổ nhật ký vận động (Bước 14, 15 Mục IV QĐ 18/2026)
-- Từ v16 (0.9.87) các bảng phụ dưới đây là một bước nâng cấp chính thức (csdl._NANG_CAP[15] -> _tao_bang_phu, chỉ file có hộ).
CREATE TABLE IF NOT EXISTS nhat_ky_van_dong (
    id INTEGER PRIMARY KEY,
    ma_ho INTEGER NOT NULL REFERENCES ho(ma_ho) ON UPDATE CASCADE ON DELETE CASCADE,
    viec TEXT NOT NULL,                               -- 'tien' (không nhận tiền) / 'mat_bang' (không bàn giao mặt bằng)
    ngay TEXT NOT NULL,                               -- dd/mm/yyyy
    hinh_thuc TEXT NOT NULL DEFAULT '', thanh_phan TEXT NOT NULL DEFAULT '', noi_dung TEXT NOT NULL DEFAULT '',
    ket_qua TEXT NOT NULL DEFAULT 'chua_dong_y',      -- chua_dong_y / vang_mat / dong_y
    bien_ban TEXT NOT NULL DEFAULT '', ghi_chu TEXT NOT NULL DEFAULT ''
);
CREATE INDEX IF NOT EXISTS ix_van_dong_ho ON nhat_ky_van_dong(ma_ho, viec);

-- nhật ký kiểm toán (0.9.86, kiem_toan.py): ai sửa, lúc nào, trường nào cũ -> mới; trigger chặn sửa / xóa dòng nhật ký
CREATE TABLE IF NOT EXISTS audit_logs (
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
CREATE INDEX IF NOT EXISTS ix_audit_logs_ho ON audit_logs(ma_ho, luc);
CREATE INDEX IF NOT EXISTS ix_audit_logs_luc ON audit_logs(luc);
CREATE TRIGGER IF NOT EXISTS audit_logs_khong_sua BEFORE UPDATE ON audit_logs
BEGIN SELECT RAISE(ABORT, 'Nhật ký kiểm toán không được sửa.'); END;
CREATE TRIGGER IF NOT EXISTS audit_logs_khong_xoa BEFORE DELETE ON audit_logs
BEGIN SELECT RAISE(ABORT, 'Nhật ký kiểm toán không được xóa.'); END;
-- 1.0.55: chuỗi băm kiểm toán (kiem_toan.SQL_BAM)
CREATE TABLE IF NOT EXISTS audit_bam (
    id   INTEGER PRIMARY KEY,                -- = audit_logs.id của dòng được ký
    bam  TEXT NOT NULL                       -- SHA-256 (32 ký tự đầu) nối chuỗi: băm dòng ký trước + nội dung dòng nhật ký
);
CREATE TRIGGER IF NOT EXISTS audit_bam_khong_sua BEFORE UPDATE ON audit_bam
BEGIN SELECT RAISE(ABORT, 'Chuỗi băm kiểm toán không được sửa.'); END;
CREATE TRIGGER IF NOT EXISTS audit_bam_khong_xoa BEFORE DELETE ON audit_bam
BEGIN SELECT RAISE(ABORT, 'Chuỗi băm kiểm toán không được xóa.'); END;

-- bản đồ thửa từ bản vẽ địa chính CAD .dxf (0.9.87, ban_do_cad.py): số tờ, số thửa, diện tích, tọa độ ranh thửa
CREATE TABLE IF NOT EXISTS thua_ban_do (
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
    UNIQUE (so_to, so_thua)
);

-- ảnh hiện trạng gắn vào hộ (0.9.87, phieu_kiem_dem.gan_anh_hien_trang): theo CCCD / họ tên / HO<số thứ tự> trong tên file ảnh
CREATE TABLE IF NOT EXISTS anh_hien_trang (
    id INTEGER PRIMARY KEY,
    ma_ho INTEGER NOT NULL REFERENCES ho(ma_ho) ON UPDATE CASCADE ON DELETE CASCADE,
    duong_dan TEXT NOT NULL,             -- đường dẫn đầy đủ của ảnh lúc gắn
    ten_file TEXT NOT NULL,
    khop_theo TEXT NOT NULL DEFAULT '',  -- cccd / ho_ten / stt
    luc TEXT NOT NULL,
    UNIQUE (ma_ho, duong_dan)
);

"""Mở / tạo file dự án .pabt (SQLite)."""
from __future__ import annotations
import getpass
import os
import re
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

PHIEN_BAN_CSDL = 16
# đuôi file dự án (người dùng 15/10/2026: ".larc"); file .pabt của các bản trước vẫn mở / nhận như cũ (cùng CSDL SQLite)
DUOI_DU_AN = '.larc'
DUOI_DU_AN_CU = ('.pabt',)
DUOI_MO = (DUOI_DU_AN,) + DUOI_DU_AN_CU
LOC_LUU = 'Dự án LARC (*.larc)'                          # hộp lưu: luôn .larc
LOC_MO = 'Dự án LARC (*.larc *.pabt)'                    # hộp mở: cả file .pabt cũ


def la_file_du_an(p) -> bool:
    return Path(str(p)).suffix.lower() in DUOI_MO


def duoi_du_an(p) -> Path:
    """Đường dẫn file dự án: giữ .larc / .pabt đã có, còn lại (không đuôi / đuôi khác) đổi sang .larc."""
    p = Path(p)
    return p if p.suffix.lower() in DUOI_MO else p.with_suffix(DUOI_DU_AN)
# bảng danh mục, tham số: cố định (trigger chặn sửa); chỉ nạp / cập nhật bộ đơn giá mới mở khóa (mo_khoa_danh_muc)
DANH_MUC = ('dm_taisan', 'dm_hotro', 'dm_loaidat', 'gia_dat', 'dm_xa', 'tham_so', 'bieu_thuong', 'quy_uoc', 'van_ban')
THONG_BAO_KHOA = 'Danh mục đơn giá, tham số được cố định theo bộ đơn giá; chỉ cập nhật bằng lệnh Bộ đơn giá.'

# nâng cấp file dự án tạo bằng phiên bản cũ: {phiên bản cũ: [lệnh SQL]}
_NANG_CAP = {
    1: ["ALTER TABLE ho ADD COLUMN luu_luc TEXT",
        "ALTER TABLE ct_khoan ADD COLUMN can_cu_gia TEXT NOT NULL DEFAULT ''"],
    2: [f"ALTER TABLE du_an ADD COLUMN {c} TEXT NOT NULL DEFAULT ''"
        for c in ('ky_hieu_so', 'nguoi_lap', 'nguoi_kiem_tra', 'chuc_vu_ky', 'nguoi_ky')],
    3: [],                                          # v4: khóa danh mục (tạo trong _dam_bao_khoa)
    4: ['''CREATE TABLE IF NOT EXISTS tho_nhap (
            id INTEGER PRIMARY KEY, dong INTEGER NOT NULL DEFAULT 0, nguon TEXT NOT NULL DEFAULT '',
            ho_ten TEXT NOT NULL DEFAULT '', dia_chi TEXT NOT NULL DEFAULT '', so_cccd TEXT NOT NULL DEFAULT '',
            ngay_cap TEXT NOT NULL DEFAULT '', noi_cap TEXT NOT NULL DEFAULT '', dien_thoai TEXT NOT NULL DEFAULT '',
            so_to TEXT NOT NULL DEFAULT '', so_thua TEXT NOT NULL DEFAULT '', dt_thu_hoi TEXT NOT NULL DEFAULT '',
            loai_dat TEXT NOT NULL DEFAULT '', vi_tri TEXT NOT NULL DEFAULT '', nhan_khau TEXT NOT NULL DEFAULT '',
            nguon_goc TEXT NOT NULL DEFAULT '', ghi_chu TEXT NOT NULL DEFAULT '', ma_ho INTEGER, ma_thua INTEGER)'''],
    5: ["ALTER TABLE du_an ADD COLUMN don_vi_tieu_de TEXT NOT NULL DEFAULT ''"],
    6: ["ALTER TABLE ho ADD COLUMN dot_id INTEGER"]
       + [f"ALTER TABLE ho ADD COLUMN {c} INTEGER NOT NULL DEFAULT 0" for c in ('da_phe_duyet', 'da_chi_tra', 'da_ban_giao')]
       + [f"ALTER TABLE ho ADD COLUMN {c} TEXT NOT NULL DEFAULT ''"
          for c in ('qd_so', 'qd_ngay', 'qd_so_tien', 'qd_file', 'chi_tra_ngay', 'chi_tra_so_tien', 'ban_giao_ngay', 'theo_doi')]
       + ['''CREATE TABLE IF NOT EXISTS dot_trinh (
            id INTEGER PRIMARY KEY, so INTEGER NOT NULL DEFAULT 0, ten TEXT NOT NULL DEFAULT '',
            ngay_trinh TEXT NOT NULL DEFAULT '', so_to_trinh TEXT NOT NULL DEFAULT '', ghi_chu TEXT NOT NULL DEFAULT '',
            thu_muc TEXT NOT NULL DEFAULT '')''',
          "CREATE TABLE IF NOT EXISTS cai_dat (ma TEXT PRIMARY KEY, gia_tri TEXT NOT NULL DEFAULT '')",
          '''CREATE TABLE IF NOT EXISTS quy_chuan_mat_do (
            ten_cay TEXT PRIMARY KEY, mat_do TEXT NOT NULL DEFAULT '', ty_le_ngoai TEXT NOT NULL DEFAULT '0',
            can_cu TEXT NOT NULL DEFAULT '')'''],
    7: ["ALTER TABLE ct_khoan ADD COLUMN cach_tinh TEXT NOT NULL DEFAULT ''"],
    8: ["ALTER TABLE ct_khoan ADD COLUMN cong_thuc TEXT NOT NULL DEFAULT ''",
        "ALTER TABLE ct_dat ADD COLUMN cong_thuc TEXT NOT NULL DEFAULT ''"],
    # v10: nhiều quyết định phê duyệt / hộ, chi trả theo từng quyết định; chuyển phê duyệt, chi trả cũ (1 QĐ / hộ) sang
    9: ["ALTER TABLE ho ADD COLUMN ly_do_ban_giao TEXT NOT NULL DEFAULT ''",
        "ALTER TABLE ho ADD COLUMN bien_ban_ban_giao TEXT NOT NULL DEFAULT ''",
        "@quyet_dinh",                              # tạo bảng quyet_dinh, qd_ho theo schema.sql
        """INSERT INTO quyet_dinh (so, ngay, file)
           SELECT qd_so, qd_ngay, MAX(qd_file) FROM ho WHERE da_phe_duyet = 1 OR TRIM(qd_so) <> '' GROUP BY qd_so, qd_ngay""",
        """INSERT OR IGNORE INTO qd_ho (qd_id, ma_ho, so_tien, da_chi_tra, chi_tra_ngay, chi_tra_so_tien)
           SELECT q.id, h.ma_ho, h.qd_so_tien, h.da_chi_tra, h.chi_tra_ngay, h.chi_tra_so_tien
           FROM ho h JOIN quyet_dinh q ON q.so = h.qd_so AND q.ngay = h.qd_ngay
           WHERE h.da_phe_duyet = 1 OR TRIM(h.qd_so) <> ''"""],
    # v11: trình phê duyệt - số, ngày phương án chi tiết từng hộ; văn bản trình, số / ngày phương án tổng của đợt
    10: ["ALTER TABLE ho ADD COLUMN so_pa TEXT NOT NULL DEFAULT ''",
         "ALTER TABLE ho ADD COLUMN ngay_pa TEXT NOT NULL DEFAULT ''",
         "ALTER TABLE dot_trinh ADD COLUMN loai_van_ban TEXT NOT NULL DEFAULT 'Tờ trình'",
         "ALTER TABLE dot_trinh ADD COLUMN so_pa_tong TEXT NOT NULL DEFAULT ''",
         "ALTER TABLE dot_trinh ADD COLUMN ngay_pa_tong TEXT NOT NULL DEFAULT ''"],
    # 0.9.20: mục Vật nuôi riêng (ct_khoan.muc = 7): dựng lại bảng (ràng buộc CHECK), dòng vật nuôi đang ở mục cây / nhà -> 7
    11: ["@ct_khoan_vat_nuoi"],
    # v16 (0.9.87): sổ nhật ký vận động, nhật ký kiểm toán (+ trigger chặn sửa / xóa), bản đồ thửa CAD, chỉ mục ct_dat(ma_thua)
    # - trước đây tạo khi mở file không đổi phiên bản; nay là bước nâng cấp chính thức (chỉ file có hộ: _tao_bang_phu)
    15: ["@bang_phu_v16"],
    # v14 (0.9.69): chủ đầu tư; mã tài sản mới TS / CT / VN / CS (ma_tai_san.chuyen_csdl - bỏ dòng HT / TH trùng của dm_taisan)
    14: ["ALTER TABLE du_an ADD COLUMN co_quan_tham_dinh TEXT NOT NULL DEFAULT ''",
         "ALTER TABLE dot_trinh ADD COLUMN ky_hieu_so TEXT NOT NULL DEFAULT ''"],
    13: ["ALTER TABLE du_an ADD COLUMN chu_dau_tu TEXT NOT NULL DEFAULT ''", "@doi_ma_tai_san"],
    # v13: dự thảo phương án — đủ điều kiện / 5 nhóm vướng, đợt niêm yết, ý kiến, đối thoại
    12: ["ALTER TABLE ho ADD COLUMN du_dieu_kien INTEGER NOT NULL DEFAULT 0",
         "ALTER TABLE ho ADD COLUMN ma_vuong TEXT NOT NULL DEFAULT ''",
         "ALTER TABLE ho ADD COLUMN ghi_chu_phap_ly TEXT NOT NULL DEFAULT ''",
         "ALTER TABLE ho ADD COLUMN dot_du_thao_id INTEGER",
         '''CREATE TABLE IF NOT EXISTS dot_du_thao (
            id INTEGER PRIMARY KEY, ten TEXT NOT NULL DEFAULT '', ngay_bat_dau TEXT NOT NULL DEFAULT '',
            ngay_ket_thuc TEXT NOT NULL DEFAULT '', dia_diem TEXT NOT NULL DEFAULT '',
            so_bb_bat_dau TEXT NOT NULL DEFAULT '', so_bb_ket_thuc TEXT NOT NULL DEFAULT '',
            ngay_hop TEXT NOT NULL DEFAULT '', han_doi_thoai TEXT NOT NULL DEFAULT '',
            trang_thai TEXT NOT NULL DEFAULT 'dang_niem_yet', ghi_chu TEXT NOT NULL DEFAULT '')''',
         '''CREATE TABLE IF NOT EXISTS y_kien_du_thao (
            id INTEGER PRIMARY KEY, dot_id INTEGER NOT NULL REFERENCES dot_du_thao(id) ON DELETE CASCADE,
            ma_ho INTEGER NOT NULL REFERENCES ho(ma_ho) ON UPDATE CASCADE ON DELETE CASCADE,
            loai TEXT NOT NULL DEFAULT 'chua', nhom TEXT NOT NULL DEFAULT '', noi_dung TEXT NOT NULL DEFAULT '',
            huong_xu_ly TEXT NOT NULL DEFAULT '', so_tien_chenh TEXT NOT NULL DEFAULT '0',
            ket_qua_doi_thoai TEXT NOT NULL DEFAULT '', chuyen_dot_id INTEGER, ngay_cap_nhat TEXT NOT NULL DEFAULT '',
            UNIQUE (dot_id, ma_ho))''',
         '''CREATE TABLE IF NOT EXISTS doi_thoai_ho (
            id INTEGER PRIMARY KEY, dot_id INTEGER NOT NULL REFERENCES dot_du_thao(id) ON DELETE CASCADE,
            ma_ho INTEGER NOT NULL, lan INTEGER NOT NULL DEFAULT 1, ngay TEXT NOT NULL DEFAULT '',
            dia_diem TEXT NOT NULL DEFAULT '', thanh_phan TEXT NOT NULL DEFAULT '', dien_bien TEXT NOT NULL DEFAULT '',
            ket_luan TEXT NOT NULL DEFAULT '', bien_ban_so TEXT NOT NULL DEFAULT '')''',
         "CREATE INDEX IF NOT EXISTS ix_ykien_dot_ho ON y_kien_du_thao(dot_id, ma_ho)",
         "CREATE INDEX IF NOT EXISTS ix_doithoai_ho ON doi_thoai_ho(dot_id, ma_ho)"],
}


def _bang_quyet_dinh() -> str:
    """Các lệnh tạo bảng quyết định (phần cuối schema.sql) - dùng khi nâng cấp file cũ lên v10."""
    s = _SCHEMA.read_text(encoding='utf-8')
    # tách theo ';' (nơi gọi) - dừng trước nhật ký kiểm toán (trigger có ';' trong BEGIN … END; bảng đó csdl.mo tạo sau khi nâng cấp)
    het = s.find('-- nhật ký kiểm toán')
    return s[s.index('CREATE TABLE IF NOT EXISTS quyet_dinh'):het if het > 0 else None]
_SCHEMA = Path(__file__).with_name('schema.sql')


def _dung_lai_ct_khoan(con) -> None:
    """Nâng cấp v11 -> v12: bảng ct_khoan theo schema.sql mới (CHECK muc IN (2, 3, 4, 7)), giữ nguyên mọi dòng / id; dòng có mã
    danh mục thuộc nhóm vật nuôi (dm_taisan.phan_loai "… vật nuôi …") chuyển sang mục 7 (Vật nuôi)."""
    s = _SCHEMA.read_text(encoding='utf-8')
    i = s.index('CREATE TABLE IF NOT EXISTS ct_khoan')
    tao = s[i:s.index('\n);', i) + 3]                # hết ở ");" đầu dòng: chú thích trong bảng có dấu ";"
    tao = tao.replace('CREATE TABLE IF NOT EXISTS ct_khoan', 'CREATE TABLE ct_khoan_moi', 1)
    con.execute('DROP TABLE IF EXISTS ct_khoan_moi')
    con.execute(tao)
    cu = [r[1] for r in con.execute('PRAGMA table_info(ct_khoan)')]
    moi = {r[1] for r in con.execute('PRAGMA table_info(ct_khoan_moi)')}
    cot = ', '.join(c for c in cu if c in moi)
    con.execute(f'INSERT INTO ct_khoan_moi ({cot}) SELECT {cot} FROM ct_khoan')
    con.execute('DROP TABLE ct_khoan')
    con.execute('ALTER TABLE ct_khoan_moi RENAME TO ct_khoan')
    con.execute('CREATE INDEX IF NOT EXISTS ix_ctkhoan_ho ON ct_khoan(ma_ho, muc)')
    chuyen_vat_nuoi(con)


def chuyen_vat_nuoi(con) -> int:
    """Dòng mục 2 / 3 có mã danh mục nhóm vật nuôi (dm_taisan.phan_loai có "vật nuôi") -> mục 7 (Vật nuôi). Trả số dòng đổi."""
    # lower() của SQLite chỉ đổi chữ ASCII ("VẬT NUÔI" không khớp): lọc bằng Python
    import unicodedata
    vn = [r[0] for r in con.execute('SELECT ma, phan_loai FROM dm_taisan')
          if r[0] and 'vật nuôi' in unicodedata.normalize('NFC', str(r[1] or '')).lower()]
    n = 0
    for ma in vn:
        n += con.execute("UPDATE ct_khoan SET muc = 7 WHERE muc IN (2, 3) AND ma = ?", (ma,)).rowcount
    return n


def tao_moi(duong_dan) -> sqlite3.Connection:
    """Tạo file .pabt mới (ghi đè nếu đã có). Tạo dự án / nhập vào file mới: dùng tao_moi_tam + hoan_tat_tao_moi (nguyên tử)."""
    p = Path(duong_dan)
    if p.exists():
        p.unlink()
    con = mo(p, tao=True)
    return con


def tao_moi_tam(duong_dan) -> tuple:
    """Tạo file dự án mới GHI NGUYÊN TỬ (đặc tả ARCH-PABT-2026-V4 mục 7.1): CSDL dựng ở '<tên>.dang_tao' cạnh file đích (cùng ổ
    đĩa - os.replace thay tức thời). Trả (kết nối, file tạm). Xong: đóng kết nối rồi hoan_tat_tao_moi; lỗi: huy_tao_moi.
    Trước 0.9.24 tao_moi() XÓA file cũ trước khi ghi: lỗi / mất điện giữa chừng mất cả file cũ lẫn file mới."""
    p = Path(duong_dan)
    tam = p.with_name(p.name + '.dang_tao')
    huy_tao_moi(tam)
    con = mo(tam, tao=True)
    # nhập hàng loạt (0.9.86 - Cụm 1): file tạm chỉ thành file dự án sau fsync + os.replace (hoan_tat_tao_moi) - mất điện giữa chừng
    # chỉ hỏng file tạm, file cũ còn nguyên: không cần SQLite fsync mỗi giao dịch, nhật ký giao dịch trong RAM (vẫn rollback được)
    con.execute('PRAGMA synchronous = OFF')
    con.execute('PRAGMA journal_mode = MEMORY')
    return con, tam


def huy_tao_moi(tam) -> None:
    for f in (Path(tam), Path(str(tam) + '-journal')):
        try:
            f.unlink()
        except FileNotFoundError:
            pass


def hoan_tat_tao_moi(tam, duong_dan) -> Path:
    """Kết nối tới file tạm đã đóng: ép ghi xuống đĩa (fsync) rồi os.replace thay file đích (thao tác nguyên tử trên NTFS).
    File đích đang mở ở chương trình khác (Excel, PABT khác…): PermissionError - file cũ còn nguyên, file tạm bị xóa."""
    import os
    tam, p = Path(tam), Path(duong_dan)
    try:
        with open(tam, 'rb+') as f:
            os.fsync(f.fileno())
        os.replace(tam, p)
    except OSError:
        huy_tao_moi(tam)
        raise
    return p


class KetNoi(sqlite3.Connection):
    """Kết nối file dự án có bộ nhớ đệm (nho): số liệu dùng chung (bối cảnh tính toán...) đọc một lần, dùng lại tới khi dữ liệu đổi."""

    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        self.bo_nho = {}


def _trang_thai(con) -> tuple:
    """Dấu hiệu dữ liệu đổi: total_changes (kết nối này ghi, kể cả trigger) + data_version (kết nối / máy khác ghi vào file)."""
    return con.total_changes, con.execute('PRAGMA data_version').fetchone()[0]


def nho(con, khoa, tao):
    """Giá trị tao() nhớ trên kết nối con theo khoa; tự đọc lại khi dữ liệu đổi. Không nhớ khi đang giữa giao dịch chưa ghi
    (rollback không làm đổi total_changes - sẽ giữ nhầm số liệu đã hủy) hoặc con không phải KetNoi (kết nối mở ngoài csdl.mo)."""
    bo = getattr(con, 'bo_nho', None)
    if bo is None or con.in_transaction:
        return tao()
    tt = _trang_thai(con)
    cu = bo.get(khoa)
    if cu is not None and cu[0] == tt:
        return cu[1]
    gt = tao()
    bo[khoa] = (tt, gt)
    return gt


def trang_thai_nho(con):
    """Dấu hiệu dữ liệu hiện tại (gọi TRƯỚC một lần ghi, rồi đưa cho giu_nho sau khi ghi xong); None nếu con không có bộ nhớ đệm."""
    return _trang_thai(con) if getattr(con, 'bo_nho', None) is not None and not con.in_transaction else None


def giu_nho(con, khoa, truoc) -> None:
    """Giữ giá trị đã nhớ (khoa) sau một lần ghi KHÔNG đụng tới số liệu của nó (vd. lưu phương án một hộ không đổi bảng thửa, danh
    mục): chỉ giữ khi giá trị đó còn đúng ngay trước lần ghi (truoc = trang_thai_nho trước khi ghi) - không có thay đổi nào khác chen vào."""
    bo = getattr(con, 'bo_nho', None)
    if bo is None or truoc is None or con.in_transaction:
        return
    cu = bo.get(khoa)
    if cu is not None and cu[0] == truoc:
        bo[khoa] = (_trang_thai(con), cu[1])


def giu_tat_ca(con, truoc) -> None:
    """Giữ mọi giá trị đã nhớ sau một lần ghi KHÔNG đụng dữ liệu dự án (bảng tạm temp.* của hoàn tác): total_changes đếm cả
    bảng tạm - không giữ thì bộ nhớ đệm (bối cảnh, kết quả 3.000 hộ) bị bỏ mỗi lần hoàn tác dọn bước cũ."""
    bo = getattr(con, 'bo_nho', None)
    if bo is None or truoc is None or con.in_transaction:
        return
    moi = _trang_thai(con)
    for k, (tt, gt) in list(bo.items()):
        if tt == truoc:
            bo[k] = (moi, gt)


def uri_chi_doc(duong_dan) -> str:
    """URI SQLite mở chỉ đọc ("file:///D:/thư mục/a.pabt?mode=ro"). Không dùng Path.as_uri(): nó nạp urllib.request (~40 ms - màn
    hình chào đọc tóm tắt các dự án gần đây lúc khởi động, 0.9.88). Chữ có dấu giữ nguyên (SQLite nhận UTF-8); %, ?, #, khoảng
    trắng mã hóa; đường dẫn mạng \\\\máy\\thư mục -> file:////máy/thư mục."""
    s = str(Path(duong_dan).resolve()).replace('\\', '/')
    s = s.replace('%', '%25').replace('?', '%3f').replace('#', '%23').replace(' ', '%20')
    return ('file://' + s if s.startswith('/') else 'file:///' + s) + '?mode=ro'


def mo(duong_dan, tao: bool = False, chi_doc: bool = False) -> sqlite3.Connection:
    """Mở file dự án (tự nâng cấp file cũ). chi_doc: mở chỉ xem, mọi lệnh ghi đều bị SQLite từ chối."""
    p = Path(duong_dan)
    if not tao and not p.exists():
        raise FileNotFoundError(str(p))
    if chi_doc:
        con = sqlite3.connect(uri_chi_doc(p), uri=True, factory=KetNoi)
        con.row_factory = sqlite3.Row
        ver = con.execute('PRAGMA user_version').fetchone()[0]
        if not 3 <= ver <= PHIEN_BAN_CSDL:
            con.close()
            raise RuntimeError(f'File dự án phiên bản CSDL v{ver} cần được mở để sửa một lần (nâng cấp) trước khi mở chỉ xem.')
        return con
    con = sqlite3.connect(str(p), factory=KetNoi)
    try:
        return _mo_tiep(con, tao)
    except BaseException:
        con.close()                                     # không để file bị giữ (Windows khóa file tới khi Python dọn rác)
        raise


def _mo_tiep(con, tao: bool):
    """Phần sau khi kết nối của mo (nâng cấp lược đồ, khóa danh mục, bảng phụ)."""
    con.row_factory = sqlite3.Row
    con.execute('PRAGMA foreign_keys = ON')
    # file dự án có thể nằm trong thư mục Google Drive: không dùng WAL (Drive đồng bộ kém các file -wal, -shm)
    con.execute('PRAGMA journal_mode = DELETE')
    ver = con.execute('PRAGMA user_version').fetchone()[0]
    if ver == 0:
        con.executescript(_SCHEMA.read_text(encoding='utf-8'))
        con.execute(f'PRAGMA user_version = {PHIEN_BAN_CSDL}')
        con.execute("INSERT OR IGNORE INTO du_an (id) VALUES (1)")
        con.commit()
    elif ver < PHIEN_BAN_CSDL:
        with con:
            for v in range(ver, PHIEN_BAN_CSDL):
                for lenh in _NANG_CAP.get(v, []):
                    m = re.match(r'ALTER TABLE (\w+) ADD COLUMN (\w+)', lenh)
                    if m and m.group(2) in [r[1] for r in con.execute(f'PRAGMA table_info({m.group(1)})')]:
                        continue                         # cột đã có (file nâng cấp dở dang): bỏ qua
                    if lenh == '@quyet_dinh':
                        for x in _bang_quyet_dinh().split(';'):
                            if x.strip():
                                con.execute(x)
                        continue
                    if lenh == '@ct_khoan_vat_nuoi':
                        _dung_lai_ct_khoan(con)
                        continue
                    if lenh == '@bang_phu_v16':
                        _tao_bang_phu(con)
                        continue
                    if lenh == '@doi_ma_tai_san':
                        from .ma_tai_san import chuyen_csdl
                        chuyen_csdl(con)
                        continue
                    con.execute(lenh)
            con.execute(f'PRAGMA user_version = {PHIEN_BAN_CSDL}')
    elif ver > PHIEN_BAN_CSDL:
        raise RuntimeError(f'File dự án được tạo bằng phiên bản phần mềm mới hơn (CSDL v{ver}); hãy cập nhật phần mềm.')
    _dam_bao_khoa(con)
    # file v16 nâng cấp lúc CHƯA có hộ (dự án trống) không có bảng phụ: tạo khi đã có hộ - trước khi Hoàn tác liệt kê bảng
    # (bộ đơn giá / file chỉ có danh mục không có hộ: không bị ghi)
    if not con.execute("SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'anh_hien_trang'").fetchone() \
            and con.execute('SELECT 1 FROM ho LIMIT 1').fetchone():
        try:
            with con:
                _tao_bang_phu(con)
        except sqlite3.OperationalError:                # file đang bị khóa: các hàm dùng bảng phụ tự tạo khi ghi
            pass
    return con


def _tao_bang_phu(con) -> bool:
    """Bảng phụ của file dự án (v16): nhat_ky_van_dong, audit_logs (+ 2 trigger chặn sửa / xóa), thua_ban_do, anh_hien_trang, chỉ mục
    ix_ctdat_thua. Chỉ file có hộ - bộ đơn giá đóng gói (cùng lược đồ, không hộ) không bị ghi. Chạy trong giao dịch của nơi gọi."""
    if not con.execute('SELECT 1 FROM ho LIMIT 1').fetchone():
        return False
    from . import ban_do_cad, kiem_toan, van_dong
    for lenh in van_dong._SQL_TAO:
        con.execute(lenh)
    if not kiem_toan.co_bang(con):
        for cau in kiem_toan._cau(kiem_toan.SQL_BANG):
            con.execute(cau)
    con.execute(ban_do_cad.SQL_BANG)
    from .phieu_kiem_dem import SQL_BANG_ANH
    con.execute(SQL_BANG_ANH)
    con.execute('CREATE INDEX IF NOT EXISTS ix_ctdat_thua ON ct_dat(ma_thua)')
    return True


def _dam_bao_khoa(con) -> None:
    """Tạo bảng cờ khoa_dm và trigger chặn thêm / sửa / xóa trên các bảng danh mục (nếu chưa có)."""
    if con.execute("SELECT 1 FROM sqlite_master WHERE type = 'trigger' AND name = 'khoa_van_ban_DELETE'").fetchone():
        return
    with con:
        con.execute('CREATE TABLE IF NOT EXISTS khoa_dm (id INTEGER PRIMARY KEY CHECK (id = 1), mo INTEGER NOT NULL DEFAULT 0)')
        con.execute('INSERT OR IGNORE INTO khoa_dm (id, mo) VALUES (1, 0)')
        for b in DANH_MUC:
            for viec in ('INSERT', 'UPDATE', 'DELETE'):
                con.execute(f'''CREATE TRIGGER IF NOT EXISTS khoa_{b}_{viec} BEFORE {viec} ON {b}
                                WHEN (SELECT mo FROM khoa_dm WHERE id = 1) = 0
                                BEGIN SELECT RAISE(ABORT, '{THONG_BAO_KHOA}'); END''')


_SAU_GD = {}              # id(kết nối) -> số tầng giao_dich đang mở


@contextmanager
def giao_dich(con):
    """Như `with con:` nhưng lồng được: chỉ tầng ngoài cùng COMMIT / ROLLBACK. `with con:` lồng trong `with con:` của sqlite3
    COMMIT ngay khi tầng trong kết thúc - vòng lặp gọi hàm ghi từng hộ thành mỗi hộ một lần ghi đĩa (chậm trên HDD / ổ mạng,
    lỗi giữa chừng để lại dữ liệu ghi dở). Hàm ghi dùng chung (ghi_qd_ho, ghi_ban_giao...) dùng giao_dich; vòng lặp bọc ngoài
    cũng dùng giao_dich -> cả lô một giao dịch."""
    k = id(con)
    sau = _SAU_GD.get(k, 0)
    _SAU_GD[k] = sau + 1
    try:
        if sau:
            yield con
        else:
            with con:
                yield con
    finally:
        if sau:
            _SAU_GD[k] = sau
        else:
            _SAU_GD.pop(k, None)


@contextmanager
def mo_khoa_danh_muc(con):
    """Cho phép ghi danh mục trong khối lệnh (dùng bên trong `with con:` để cùng một giao dịch)."""
    con.execute('UPDATE khoa_dm SET mo = 1 WHERE id = 1')
    try:
        yield con
    finally:
        con.execute('UPDATE khoa_dm SET mo = 0 WHERE id = 1')


def _cot(con, so_do: str, bang: str) -> list:
    return [r[1] for r in con.execute(f'PRAGMA {so_do}.table_info("{bang}")')]


def chep_danh_muc(con, file_nguon, don_vi: bool = True, bang=DANH_MUC) -> None:
    """Chép các bảng danh mục (và thông tin đơn vị lập, người ký nếu don_vi) từ một file .pabt / bộ đơn giá khác.
    File nguồn chỉ được ĐỌC (trước 0.9.16 được mở ghi để nâng cấp lược đồ: bộ đơn giá đóng gói / trong gói cập nhật bị sửa ->
    sai mã SHA-256, gói cập nhật tự tắt; file dự án khác bị nâng cấp ngầm). Chép theo các cột có ở cả hai bên - cột nguồn cũ
    chưa có lấy giá trị mặc định; bảng nguồn chưa có thì giữ nguyên danh mục đó của dự án."""
    con.execute('ATTACH DATABASE ? AS nguon', (str(file_nguon),))
    try:
        co = {r[0] for r in con.execute("SELECT name FROM nguon.sqlite_master WHERE type = 'table'")}
        with con, mo_khoa_danh_muc(con):
            for b in bang:
                if b not in co:
                    continue
                nguon = set(_cot(con, 'nguon', b))
                ds = ', '.join(f'"{c}"' for c in _cot(con, 'main', b) if c in nguon)
                con.execute(f'DELETE FROM {b}')
                con.execute(f'INSERT INTO {b} ({ds}) SELECT {ds} FROM nguon.{b}')
            if don_vi and 'du_an' in co:
                nguon = set(_cot(con, 'nguon', 'du_an'))
                cot = ', '.join(c for c in TRUONG_DON_VI if c in nguon)
                if cot:
                    con.execute(f'UPDATE du_an SET ({cot}) = (SELECT {cot} FROM nguon.du_an WHERE id = 1) WHERE id = 1')
    finally:
        con.execute('DETACH DATABASE nguon')


# thông tin đơn vị lập, người ký: thuộc về đơn vị chứ không thuộc dự án -> giữ khi xóa trắng, chép khi tạo dự án mới
TRUONG_DON_VI = ('don_vi_cap_tren', 'don_vi_tieu_de', 'don_vi_lap', 'ky_hieu_so', 'nguoi_lap', 'nguoi_kiem_tra', 'chuc_vu_ky',
                 'nguoi_ky')


class DauVetHo:
    """Ghi lại các hộ có dữ liệu bị thêm / sửa / xóa trên một kết nối (trigger TẠM - chỉ sống trong phiên, không ghi vào file
    .pabt), để màn hình chỉ tính và vẽ lại các hộ đó thay vì cả dự án (3.000 hộ: ~0,6 giây mỗi lần lưu một hộ).

    lay(): tập mã hộ đã đổi kể từ lần lấy trước; None = phải nạp lại toàn bộ: thêm / xóa hộ, đổi thứ tự / mã hộ, ghi bảng không
    theo hộ (danh mục, dự án, quyết định, đợt trình, cài đặt...), hoặc kết nối / máy khác đã ghi vào file (PRAGMA data_version).
    Sổ ghi chỉ thêm dòng (không xóa sau mỗi lần lấy) để việc lấy không mở giao dịch, không làm đổi total_changes (csdl.nho)."""
    BO_QUA = ('nhat_ky', 'khoa_dm', 'sqlite_sequence', 'tho_nhap')   # không ảnh hưởng số liệu hiển thị của hộ
    TOI_DA = 200000                                                  # sổ dài quá thì dọn (một lần, khi lấy)

    def __init__(self, con):
        self.con = con
        con.execute('CREATE TEMP TABLE IF NOT EXISTS _dv_ho (seq INTEGER PRIMARY KEY, ma_ho INTEGER)')
        bang = [r[0] for r in con.execute("SELECT name FROM main.sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'")
                if r[0] not in self.BO_QUA]
        for b in bang:
            cot = [r[1] for r in con.execute(f'PRAGMA main.table_info("{b}")')]
            if b == 'ho':                                            # thêm / xóa hộ, đổi thứ tự / mã hộ: nạp lại toàn bộ
                than = {'them': 'VALUES (NULL)', 'xoa': 'VALUES (NULL)',
                        'sua': 'VALUES (CASE WHEN old.thu_tu IS NOT new.thu_tu OR old.ma_ho IS NOT new.ma_ho THEN NULL '
                               'ELSE new.ma_ho END)'}
                lenh = {k: f'INSERT INTO _dv_ho (ma_ho) {v};' for k, v in than.items()}
            elif 'ma_ho' in cot:
                lenh = {'them': 'INSERT INTO _dv_ho (ma_ho) SELECT new.ma_ho WHERE new.ma_ho IS NOT NULL;',
                        'xoa': 'INSERT INTO _dv_ho (ma_ho) SELECT old.ma_ho WHERE old.ma_ho IS NOT NULL;',
                        'sua': 'INSERT INTO _dv_ho (ma_ho) SELECT old.ma_ho WHERE old.ma_ho IS NOT NULL; '
                               'INSERT INTO _dv_ho (ma_ho) SELECT new.ma_ho WHERE new.ma_ho IS NOT NULL '
                               'AND new.ma_ho IS NOT old.ma_ho;'}
            else:
                lenh = dict.fromkeys(('them', 'xoa', 'sua'), 'INSERT INTO _dv_ho (ma_ho) VALUES (NULL);')
            for k, viec in (('them', 'INSERT'), ('xoa', 'DELETE'), ('sua', 'UPDATE')):
                con.execute(f'CREATE TEMP TRIGGER IF NOT EXISTS _dv_{b}_{k} AFTER {viec} ON main."{b}" BEGIN {lenh[k]} END')
        self._moc = self._max()
        self._dv = self._data_version()

    def _max(self) -> int:
        return self.con.execute('SELECT COALESCE(MAX(seq), 0) FROM temp._dv_ho').fetchone()[0]

    def _data_version(self) -> int:
        return self.con.execute('PRAGMA data_version').fetchone()[0]

    def lay(self):
        """Mã hộ đã đổi từ lần lấy trước (set), hoặc None nếu phải nạp lại toàn bộ."""
        try:
            dv = self._data_version()
            moc, so_null = self.con.execute('SELECT MAX(seq), SUM(ma_ho IS NULL) FROM temp._dv_ho WHERE seq > ?',
                                            (self._moc,)).fetchone()
            ds = {r[0] for r in self.con.execute('SELECT DISTINCT ma_ho FROM temp._dv_ho WHERE seq > ? AND ma_ho IS NOT NULL',
                                                  (self._moc,))}
        except sqlite3.Error:                           # kết nối đã đóng / bảng tạm mất: coi như phải nạp lại
            return None
        khac = dv != self._dv
        self._dv = dv
        if moc is not None:
            self._moc = moc
            if moc > self.TOI_DA and not self.con.in_transaction:
                self.con.execute('DELETE FROM temp._dv_ho')
                self.con.commit()
                self._moc = 0
        return None if khac or so_null else ds


NGUOI_DUNG = None          # tên người đăng nhập máy chủ (may_chu.dang_nhap); None = tài khoản Windows
HOAN_TAC = {}              # id(kết nối) -> hoan_tac.HoanTac (ghi_nhat_ky báo tên thao tác cho bước hoàn tác)


def nguoi_dung() -> str:
    """Người ghi nhật ký: tài khoản đăng nhập máy chủ LAN, không thì tài khoản Windows."""
    if NGUOI_DUNG:
        return NGUOI_DUNG
    try:
        return getpass.getuser()
    except Exception:
        return os.environ.get('USERNAME', '')


def ghi_nhat_ky(con: sqlite3.Connection, viec: str, chi_tiet: str = '') -> None:
    ht = HOAN_TAC.get(id(con))
    if ht is not None:
        ht.dat_ten(viec)
    con.execute('INSERT INTO nhat_ky (thoi_gian, may, nguoi_dung, viec, chi_tiet) VALUES (?,?,?,?,?)',
                (datetime.now().isoformat(timespec='seconds'), ten_may(), nguoi_dung(), viec, chi_tiet))


def ten_may() -> str:
    """Tên máy tính (ghi nhật ký, khóa file, máy chủ LAN). Bằng đúng platform.node() - hàm đó cũng gọi socket.gethostname() - nhưng
    không qua platform.uname(): từ Python 3.12 uname() đọc thông tin Windows qua WMI, lần gọi đầu mất ~50 ms."""
    import socket
    try:
        return socket.gethostname()
    except OSError:
        return ''


def tham_so(con: sqlite3.Connection) -> dict:
    return {r['ma']: r['gia_tri'] for r in con.execute('SELECT ma, gia_tri FROM tham_so')}


def doc_cai_dat(con: sqlite3.Connection, ma: str, mac_dinh: str = '') -> str:
    """Cài đặt riêng của dự án (thư mục hồ sơ, tỷ lệ mặc định...): bảng cai_dat, không thuộc danh mục khóa."""
    try:
        r = con.execute('SELECT gia_tri FROM cai_dat WHERE ma = ?', (ma,)).fetchone()
    except sqlite3.OperationalError:                # file chỉ xem phiên bản cũ chưa có bảng
        return mac_dinh
    return r[0] if r is not None and r[0] != '' else mac_dinh


def ghi_cai_dat(con: sqlite3.Connection, ma: str, gia_tri) -> None:
    con.execute('INSERT INTO cai_dat (ma, gia_tri) VALUES (?, ?) ON CONFLICT(ma) DO UPDATE SET gia_tri = excluded.gia_tri',
                (ma, str(gia_tri)))

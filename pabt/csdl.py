"""Mở / tạo file dự án .pabt (SQLite)."""
from __future__ import annotations
import getpass
import os
import platform
import re
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

PHIEN_BAN_CSDL = 10
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
}


def _bang_quyet_dinh() -> str:
    """Các lệnh tạo bảng quyết định (phần cuối schema.sql) - dùng khi nâng cấp file cũ lên v10."""
    s = _SCHEMA.read_text(encoding='utf-8')
    return s[s.index('CREATE TABLE IF NOT EXISTS quyet_dinh'):]
_SCHEMA = Path(__file__).with_name('schema.sql')


def tao_moi(duong_dan) -> sqlite3.Connection:
    """Tạo file .pabt mới (ghi đè nếu đã có)."""
    p = Path(duong_dan)
    if p.exists():
        p.unlink()
    con = mo(p, tao=True)
    return con


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


def mo(duong_dan, tao: bool = False, chi_doc: bool = False) -> sqlite3.Connection:
    """Mở file dự án (tự nâng cấp file cũ). chi_doc: mở chỉ xem, mọi lệnh ghi đều bị SQLite từ chối."""
    p = Path(duong_dan)
    if not tao and not p.exists():
        raise FileNotFoundError(str(p))
    if chi_doc:
        con = sqlite3.connect(p.resolve().as_uri() + '?mode=ro', uri=True, factory=KetNoi)
        con.row_factory = sqlite3.Row
        ver = con.execute('PRAGMA user_version').fetchone()[0]
        if not 3 <= ver <= PHIEN_BAN_CSDL:
            con.close()
            raise RuntimeError(f'File dự án phiên bản CSDL v{ver} cần được mở để sửa một lần (nâng cấp) trước khi mở chỉ xem.')
        return con
    con = sqlite3.connect(str(p), factory=KetNoi)
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
                    con.execute(lenh)
            con.execute(f'PRAGMA user_version = {PHIEN_BAN_CSDL}')
    elif ver > PHIEN_BAN_CSDL:
        con.close()
        raise RuntimeError(f'File dự án được tạo bằng phiên bản phần mềm mới hơn (CSDL v{ver}); hãy cập nhật phần mềm.')
    _dam_bao_khoa(con)
    return con


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


@contextmanager
def mo_khoa_danh_muc(con):
    """Cho phép ghi danh mục trong khối lệnh (dùng bên trong `with con:` để cùng một giao dịch)."""
    con.execute('UPDATE khoa_dm SET mo = 1 WHERE id = 1')
    try:
        yield con
    finally:
        con.execute('UPDATE khoa_dm SET mo = 0 WHERE id = 1')


def chep_danh_muc(con, file_nguon, don_vi: bool = True, bang=DANH_MUC) -> None:
    """Chép các bảng danh mục (và thông tin đơn vị lập, người ký nếu don_vi) từ một file .pabt / bộ đơn giá khác."""
    try:
        mo(file_nguon).close()                      # nâng cấp file nguồn cũ nếu cần
    except (sqlite3.Error, OSError):
        pass                                        # nguồn chỉ đọc (bộ đơn giá trong thư mục cài): bảng danh mục không đổi
    con.execute('ATTACH DATABASE ? AS nguon', (str(file_nguon),))
    try:
        with con, mo_khoa_danh_muc(con):
            for b in bang:
                con.execute(f'DELETE FROM {b}')
                con.execute(f'INSERT INTO {b} SELECT * FROM nguon.{b}')
            if don_vi:
                cot = ', '.join(TRUONG_DON_VI)
                con.execute(f'UPDATE du_an SET ({cot}) = (SELECT {cot} FROM nguon.du_an WHERE id = 1) WHERE id = 1')
    finally:
        con.execute('DETACH DATABASE nguon')


# thông tin đơn vị lập, người ký: thuộc về đơn vị chứ không thuộc dự án -> giữ khi xóa trắng, chép khi tạo dự án mới
TRUONG_DON_VI = ('don_vi_cap_tren', 'don_vi_tieu_de', 'don_vi_lap', 'ky_hieu_so', 'nguoi_lap', 'nguoi_kiem_tra', 'chuc_vu_ky',
                 'nguoi_ky')


NGUOI_DUNG = None          # tên người đăng nhập máy chủ (may_chu.dang_nhap); None = tài khoản Windows
HOAN_TAC = {}              # id(kết nối) -> hoan_tac.HoanTac (ghi_nhat_ky báo tên thao tác cho bước hoàn tác)


def ghi_nhat_ky(con: sqlite3.Connection, viec: str, chi_tiet: str = '') -> None:
    ht = HOAN_TAC.get(id(con))
    if ht is not None:
        ht.dat_ten(viec)
    nguoi = NGUOI_DUNG
    if not nguoi:
        try:
            nguoi = getpass.getuser()
        except Exception:
            nguoi = os.environ.get('USERNAME', '')
    con.execute('INSERT INTO nhat_ky (thoi_gian, may, nguoi_dung, viec, chi_tiet) VALUES (?,?,?,?,?)',
                (datetime.now().isoformat(timespec='seconds'), platform.node(), nguoi, viec, chi_tiet))


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

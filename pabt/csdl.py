"""Mở / tạo file dự án .pabt (SQLite)."""
from __future__ import annotations
import getpass
import os
import re
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

PHIEN_BAN_CSDL = 17
# đuôi file dự án (người dùng 15/10/2026: ".larc"); file .pabt của các bản trước vẫn mở / nhận như cũ (cùng CSDL SQLite)
DUOI_DU_AN = '.larc'
DUOI_DU_AN_CU = ('.pabt',)
DUOI_MO = (DUOI_DU_AN,) + DUOI_DU_AN_CU
LOC_LUU = 'Dự án LARC (*.larc)'                          # hộp lưu: luôn .larc
LOC_MO = 'Dự án LARC (*.larc *.pabt)'                    # hộp mở: cả file .pabt cũ


# ---------------------------------------------------------------- máy cấu hình yếu (1.0.08)
NGUONG_RAM_MAY_YEU_MB = 4200    # RAM vật lý dưới chừng này (máy 4 GB báo ~3.9 GB) hoặc CPU <= 2 nhân = máy yếu
NGUONG_NHAN_MAY_YEU = 2
_MAY_YEU = {}


def ram_vat_ly_mb() -> int | None:
    """RAM vật lý (MB) qua GlobalMemoryStatusEx (Windows); không đọc được -> None."""
    try:
        import ctypes

        class _MS(ctypes.Structure):
            _fields_ = [('dwLength', ctypes.c_ulong), ('dwMemoryLoad', ctypes.c_ulong), ('ullTotalPhys', ctypes.c_ulonglong),
                        ('ullAvailPhys', ctypes.c_ulonglong), ('ullTotalPageFile', ctypes.c_ulonglong),
                        ('ullAvailPageFile', ctypes.c_ulonglong), ('ullTotalVirtual', ctypes.c_ulonglong),
                        ('ullAvailVirtual', ctypes.c_ulonglong), ('ullAvailExtendedVirtual', ctypes.c_ulonglong)]
        m = _MS()
        m.dwLength = ctypes.sizeof(_MS)
        if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m)):
            return None
        return int(m.ullTotalPhys // (1024 * 1024))
    except Exception:                                   # không phải Windows / ctypes lỗi
        return None


def la_may_yeu() -> bool:
    """Máy cấu hình yếu: RAM vật lý < NGUONG_RAM_MAY_YEU_MB hoặc <= NGUONG_NHAN_MAY_YEU nhân CPU. PABT_MAY_YEU=1 / 0 ép (kiểm thử,
    người dùng). Kết quả nhớ trong tiến trình (biến môi trường đọc lại mỗi lần)."""
    ep = os.environ.get('PABT_MAY_YEU')
    if ep in ('0', '1'):
        return ep == '1'
    if 'kq' not in _MAY_YEU:
        ram = ram_vat_ly_mb()
        nhan = os.cpu_count() or 1
        _MAY_YEU['kq'] = bool((ram is not None and ram < NGUONG_RAM_MAY_YEU_MB) or nhan <= NGUONG_NHAN_MAY_YEU)
    return _MAY_YEU['kq']


def giai_phong_bo_nho(luon: bool = False) -> int:
    """Máy yếu (hoặc luon): gc.collect() ngay - Workbook openpyxl / cửa sổ vừa đóng trả RAM sớm (bản 32-bit). Trả số đối tượng thu."""
    if not (luon or la_may_yeu()):
        return 0
    import gc
    return gc.collect()


# ---------------------------------------------------------------- sao lưu tự động khi mở dự án để sửa (1.0.08)
THU_MUC_SAO_LUU_TU_DONG = 'sao_luu_tu_dong'
SAO_LUU_GIU = 5                 # mỗi dự án giữ chừng này bản gần nhất


def thu_muc_sao_luu_tu_dong() -> Path:
    from .dia_phuong import thu_muc_may
    return thu_muc_may() / THU_MUC_SAO_LUU_TU_DONG


def _goc_sao_luu(file) -> str:
    """Tiền tố tên bản sao lưu: tên file + 6 ký tự băm đường dẫn đầy đủ (hai dự án cùng tên ở hai thư mục không lẫn)."""
    import hashlib
    p = Path(file)
    try:
        dd = str(p.resolve()).lower()
    except OSError:
        dd = str(p).lower()
    return f'{p.stem}_{hashlib.sha1(dd.encode("utf-8")).hexdigest()[:6]}'


def ds_sao_luu_tu_dong(file) -> list:
    """Các bản sao lưu tự động của dự án file, mới nhất trước."""
    tm = thu_muc_sao_luu_tu_dong()
    if not tm.is_dir():
        return []
    goc = _goc_sao_luu(file)
    return sorted((f for f in tm.iterdir() if f.is_file() and f.name.startswith(goc + '_') and not f.name.endswith(('.tmp', '.tmp.nen'))),
                  key=lambda f: f.name, reverse=True)


def bo_anh_ban_do_ban_sao(dc) -> None:
    """Trên BẢN SAO (sao lưu tự động, mốc khôi phục): bỏ ô ảnh nền bản đồ đã lưu (ban_do_luu.BANG_O - tải lại được) rồi VACUUM, để mỗi
    bản sao không chép thêm vài MB ảnh (rà soát 31/10/2026: 5 bản sao lưu + tới 80 mốc). Lớp KML (nhỏ) giữ. Lỗi: giữ bản sao nguyên."""
    try:
        if dc.execute("SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'ban_do_o'").fetchone() and \
                dc.execute('SELECT 1 FROM ban_do_o LIMIT 1').fetchone():
            dc.execute('DELETE FROM ban_do_o')
            dc.commit()
            dc.execute('VACUUM')
    except sqlite3.Error:
        pass


def sao_luu_tu_dong(con, file, giu: int = SAO_LUU_GIU) -> Path | None:
    """Bản sao nguyên tử file dự án đang mở (SQLite backup API trên chính kết nối - không tranh khóa với kết nối khác) vào
    <thư mục máy>\\sao_luu_tu_dong\\<tên>_<băm>_<giờ><đuôi>; giữ giu bản gần nhất. Bỏ qua khi đang giữa giao dịch hoặc file nằm
    sẵn trong thư mục sao lưu. Trả file đã ghi (None nếu bỏ qua)."""
    file = Path(file)
    tm = thu_muc_sao_luu_tu_dong()
    try:
        if con.in_transaction or file.resolve().parent == tm.resolve():
            return None
    except OSError:
        return None
    tm.mkdir(parents=True, exist_ok=True)
    dich = tm / f'{_goc_sao_luu(file)}_{datetime.now():%Y%m%d_%H%M%S}{file.suffix or DUOI_DU_AN}'
    tam = dich.with_name(dich.name + '.tmp')
    dc = sqlite3.connect(str(tam))
    try:
        con.backup(dc)
        dc.commit()
        bo_anh_ban_do_ban_sao(dc)
        kt = dc.execute('PRAGMA quick_check').fetchone()     # 1.0.97: không giữ bản sao lưu hỏng (tưởng có mà khôi phục không được)
    finally:
        dc.close()
    if not kt or kt[0] != 'ok':
        try:
            tam.unlink()
        except OSError:
            pass
        raise sqlite3.DatabaseError(f'Bản sao lưu tự động không qua kiểm tra toàn vẹn ({kt[0] if kt else "không rõ"}) - đã bỏ.')
    from .an_toan import dong_goi_file_sao_luu
    dong_goi_file_sao_luu(tam)                          # 1.0.55: nén zlib (không mã hóa - người dùng chọn)
    os.replace(tam, dich)
    for cu in ds_sao_luu_tu_dong(file)[max(1, giu):]:
        try:
            cu.unlink()
        except OSError:
            pass
    return dich


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
    # v17 (1.0.05): nhiều lần lập phương án / hộ - ct_dat, ct_khoan cột lan (dòng cũ = lần 1), qd_ho.lan (0 = cả hộ, trước v17),
    # bảng pa_lan (lan_pa.py); hộ đã có quyết định: lần 1 khóa
    16: ["ALTER TABLE ct_dat ADD COLUMN lan INTEGER NOT NULL DEFAULT 1",
         "ALTER TABLE ct_khoan ADD COLUMN lan INTEGER NOT NULL DEFAULT 1",
         "ALTER TABLE qd_ho ADD COLUMN lan INTEGER NOT NULL DEFAULT 0",
         "@pa_lan_v17"],
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
        self._file_tam = None

    def __exit__(self, t, v, tb):
        """1.0.58: Python 3.8 (bản Win7) không rollback khi COMMIT lỗi ('database is locked'): giao dịch còn mở, giữ khóa ghi, thao tác
        đã báo lỗi lại được ghi ở lần commit sau."""
        try:
            return super().__exit__(t, v, tb)
        except sqlite3.Error:
            if self.in_transaction:
                try:
                    self.rollback()
                except sqlite3.Error:
                    pass
            raise

    def close(self):
        """Đóng; bản sao lưu nén mở chỉ xem: xóa file tạm đã giải nén (1.0.55)."""
        super().close()
        tam, self._file_tam = getattr(self, '_file_tam', None), None
        if tam is not None:
            try:
                Path(tam).unlink()
            except OSError:
                pass


def _file_tam_sao_luu(goc_file: Path, du: bytes) -> Path:
    """Ghi nội dung SQLite đã giải nén ra %TEMP%\\pabt_sao_luu_mo\\<tên>_<số>.<đuôi> (xóa khi đóng kết nối; sót lại thì dọn lần sau)."""
    import tempfile
    import time
    tm = Path(tempfile.gettempdir()) / 'pabt_sao_luu_mo'
    tm.mkdir(parents=True, exist_ok=True)
    for cu in tm.iterdir():                             # bản tạm của lần trước quên đóng (> 1 ngày)
        try:
            if time.time() - cu.stat().st_mtime > 86400:
                cu.unlink()
        except OSError:
            pass
    fd, ten = tempfile.mkstemp(prefix=goc_file.stem[:40] + '_', suffix=goc_file.suffix or DUOI_DU_AN, dir=str(tm))
    with os.fdopen(fd, 'wb') as fo:                      # đóng ngay: Windows không xóa được file còn mở
        fo.write(du)
    f = Path(ten)
    return f


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


CHO_KHOA_GIAY = 30.0       # 1.0.90: chờ khóa file (máy khác / Google Drive đang ghi) tối đa chừng này giây rồi mới báo "database is locked"


def journal_do_dang(file) -> bool:
    """File -journal của dự án là giao dịch dở (máy kia mất điện giữa lúc ghi). File -journal 0 byte (công cụ / bản khác dùng chế độ TRUNCATE
    hoặc PERSIST để lại) không phải giao dịch dở: chỉ file có nội dung mới là (SQLite cũng chỉ coi journal có nội dung là "hot journal")."""
    try:
        return Path(str(file) + '-journal').stat().st_size > 0
    except OSError:
        return False


def giai_phong_khoa_treo(con) -> None:
    """Giao dịch ngầm còn mở trên kết nối (lệnh ghi chưa COMMIT, ngoài mọi khối giao_dich) giữ khóa file làm máy khác / kết nối khác chờ:
    ghi hẳn xuống như nút Lưu (app.luu cũng COMMIT giao dịch ngầm). Đang trong giao_dich thì không đụng. Lỗi: hủy giao dịch ngầm."""
    if con is None or _SAU_GD.get(id(con), 0) > 0 or not getattr(con, 'in_transaction', False):
        return
    try:
        con.commit()
    except sqlite3.Error:
        try:
            con.rollback()
        except sqlite3.Error:
            pass


def _la_loi_khoa(e: Exception) -> bool:
    s = str(e).lower()
    return isinstance(e, sqlite3.OperationalError) and ('locked' in s or 'busy' in s)


def mo(duong_dan, tao: bool = False, chi_doc: bool = False) -> sqlite3.Connection:
    """Mở file dự án (tự nâng cấp file cũ). chi_doc: mở chỉ xem, mọi lệnh ghi đều bị SQLite từ chối."""
    p = Path(duong_dan)
    if not tao and not p.exists():
        raise FileNotFoundError(str(p))
    tam = None
    if not tao and p.is_file():
        from .an_toan import mo_goi_file_sao_luu_ra_bytes
        goc = mo_goi_file_sao_luu_ra_bytes(p)           # 1.0.55: bản sao lưu / mốc nén - giải nén ra file tạm, luôn mở CHỈ XEM
        if goc is not None:
            tam = _file_tam_sao_luu(p, goc)
            p, chi_doc = tam, True
    if chi_doc:
        con = sqlite3.connect(uri_chi_doc(p), uri=True, factory=KetNoi, timeout=CHO_KHOA_GIAY)
        con._file_tam = tam
        try:
            con.row_factory = sqlite3.Row
            con.execute('PRAGMA trusted_schema = OFF')  # 1.0.97: như nhánh mở để sửa (_mo_tiep)
            ver = con.execute('PRAGMA user_version').fetchone()[0]
            if not 3 <= ver <= PHIEN_BAN_CSDL:
                raise RuntimeError(f'File dự án phiên bản CSDL v{ver} cần được mở để sửa một lần (nâng cấp) trước khi mở chỉ xem.')
            _kiem_luoc_do(con)                          # 1.0.97: lược đồ hỏng -> báo ngay, không văng UnicodeDecodeError về sau
        except BaseException:
            con.close()                                 # file hỏng / không phải CSDL: không để Windows giữ khóa file (26/10/2026)
            raise
        return con
    con = sqlite3.connect(str(p), factory=KetNoi, timeout=CHO_KHOA_GIAY)
    try:
        return _mo_tiep(con, tao)
    except BaseException:
        con.close()                                     # không để file bị giữ (Windows khóa file tới khi Python dọn rác)
        raise


def _mo_tiep(con, tao: bool):
    """Phần sau khi kết nối của mo (nâng cấp lược đồ, khóa danh mục, bảng phụ)."""
    con.row_factory = sqlite3.Row
    con.execute(f'PRAGMA busy_timeout = {int(CHO_KHOA_GIAY * 1000)}')
    con.execute('PRAGMA foreign_keys = ON')
    con.execute('PRAGMA trusted_schema = OFF')          # 1.0.91: trigger / view trong file ngoài không gọi được hàm SQL không "vô hại"
    # file dự án có thể nằm trong thư mục Google Drive: không dùng WAL (Drive đồng bộ kém các file -wal, -shm).
    # 1.0.90: GIỮ DELETE. Đã thử TRUNCATE (yêu cầu đại phẫu): kết nối TRUNCATE giữ mở file -journal, kết nối khác ở chế độ DELETE (bản cũ ở máy
    # khác cùng thư mục Drive / LAN, may_chu, co_may_thoi_gian, chua_benh_csdl mở sqlite3.connect thẳng) không xóa được journal khi COMMIT
    # -> "disk I/O error" (tests/test_toc_do.test_may_khac_ghi_vao_file, test_tai_lai). Chống khóa bằng busy_timeout 30 s + giao_dich thử lại.
    con.execute('PRAGMA journal_mode = DELETE')
    # bảng tạm của Hoàn tác (_ht_nhat_ky), dấu vết hộ (_dv_ho), kiểm toán (_kt_phien) nằm trên RAM - không ghi file tạm ra đĩa mỗi lần
    # lưu (máy yếu, ổ HDD - 16/10/2026). Thiết lập của kết nối, không ghi vào file
    con.execute('PRAGMA temp_store = MEMORY')
    ver = con.execute('PRAGMA user_version').fetchone()[0]
    if ver != 0:
        _kiem_luoc_do(con)
    da_go = _go_trigger_la_som(con) if ver != 0 else []      # trước mọi lần ghi bên dưới (nâng cấp, mở rộng, ghi tối thiểu)
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
                    if lenh == '@pa_lan_v17':
                        _tao_pa_lan(con)
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
    # P2 (03/11/2026): các phần mở rộng lược đồ KHÔNG đổi PHIEN_BAN_CSDL (bảng phụ, cột thêm, chỉ mục) - một sổ MO_RONG, chỉ file có hộ
    # (bộ đơn giá / file chỉ danh mục không bị ghi), một giao dịch cho mọi phần còn thiếu (trước: tối đa 6 lần ghi đĩa mỗi lần mở)
    dam_bao_mo_rong(con)
    dat_ghi_toi_thieu(con)                              # CLI / nhập / GUI: cùng một chỗ (bộ đơn giá đóng gói tự bỏ)
    if da_go:                                           # nhật ký sau khi lược đồ đủ bảng (không ghi được: bỏ qua, trigger đã gỡ)
        try:
            ghi_nhat_ky(con, 'Gỡ trigger lạ trong file dự án', ', '.join(da_go))
            con.commit()
        except sqlite3.Error:
            pass
    return con


# 1.0.52 (người dùng 02/11/2026): chỉ mục cho dự án lớn (10.000 - 50.000 hộ). KHÔNG đổi PHIEN_BAN_CSDL: tạo ở csdl.mo khi file có hộ
# (bộ đơn giá đóng gói không hộ - không bị ghi); bản cũ mở file vẫn được (chỉ mục thừa vô hại). Đo 5.000 hộ: dòng công thức 1,1 ->
# 0,2 ms, danh sách hộ theo thứ tự 2,8 -> 1,8 ms, tra thửa theo tờ / số 0,36 -> 0,04 ms mỗi lần
CHI_MUC_THEM = (
    ('ix_ho_dot', 'CREATE INDEX IF NOT EXISTS ix_ho_dot ON ho(dot_id)'),
    ('ix_ho_dot_dt', 'CREATE INDEX IF NOT EXISTS ix_ho_dot_dt ON ho(dot_du_thao_id)'),
    ('ix_thua_to_thua', 'CREATE INDEX IF NOT EXISTS ix_thua_to_thua ON thua(so_to, so_thua, ma_ho)'),
    ('ix_pa_lan_dot_trinh', 'CREATE INDEX IF NOT EXISTS ix_pa_lan_dot_trinh ON pa_lan(dot_trinh_id, ma_ho, lan)'),
    ('ix_ct_dat_cong_thuc', "CREATE INDEX IF NOT EXISTS ix_ct_dat_cong_thuc ON ct_dat(ma_ho, lan) WHERE cong_thuc <> ''"),
    ('ix_ct_khoan_cong_thuc', "CREATE INDEX IF NOT EXISTS ix_ct_khoan_cong_thuc ON ct_khoan(ma_ho, lan) WHERE cong_thuc <> ''"),
    ('ix_ho_thutu', 'CREATE INDEX IF NOT EXISTS ix_ho_thutu ON ho(thu_tu, ma_ho)'),        # cuối: dấu hiệu đã tạo đủ
    ('ix_ykien_ho', 'CREATE INDEX IF NOT EXISTS ix_ykien_ho ON y_kien_du_thao(ma_ho)'),  # cuối: dấu hiệu đã tạo đủ
)


def dam_bao_chi_muc(con) -> int:
    """Tạo các chỉ mục CHI_MUC_THEM còn thiếu (cột chưa có ở file cũ -> bỏ qua chỉ mục đó). Chạy trong giao dịch của nơi gọi."""
    n = 0
    for _ten, sql in CHI_MUC_THEM:
        try:
            con.execute(sql)
            n += 1
        except sqlite3.OperationalError:                # file cũ thiếu cột (pa_lan.dot_trinh_id, cong_thuc, lan...)
            continue
    return n


# cột thêm vào bảng thua KHÔNG đổi PHIEN_BAN_CSDL (20/10/2026 - thẻ Thông tin hộ, thửa đất): file mới có sẵn (schema.sql); file cũ
# thêm ở csdl.mo khi đã có hộ (trước khi Hoàn tác liệt kê cột) hoặc lúc ghi thửa (ho_so.luu_ho). Bản cũ mở file vẫn được (cột thừa)
COT_THUA_THEM = (('dt_nguyen_thua', "TEXT NOT NULL DEFAULT ''"), ('so_gcn', "TEXT NOT NULL DEFAULT ''"))


def co_cot_ghi_chu_ten(con) -> bool:
    """1.0.78: cột ho.ghi_chu_ten (dòng ghi chú hiện dưới tên hộ)."""
    return any(r[1] == 'ghi_chu_ten' for r in con.execute('PRAGMA table_info(ho)'))


def dam_bao_cot_ghi_chu_ten(con) -> None:
    if not co_cot_ghi_chu_ten(con):
        con.execute("ALTER TABLE ho ADD COLUMN ghi_chu_ten TEXT NOT NULL DEFAULT ''")


def sql_ghi_chu_ten(con, bang: str = '') -> str:
    """Biểu thức SELECT an toàn với file chưa có cột (mở chỉ xem file cũ)."""
    if not co_cot_ghi_chu_ten(con):
        return "'' AS ghi_chu_ten"
    return f'{bang}.ghi_chu_ten' if bang else 'ghi_chu_ten'


def co_cot_thua(con) -> bool:
    """Bảng thua đã có các cột COT_THUA_THEM (nhớ trên kết nối khi đã có)."""
    if getattr(con, '_co_cot_thua', False):
        return True
    co = {r[1] for r in con.execute('PRAGMA table_info(thua)')}
    kq = all(k in co for k, _ in COT_THUA_THEM)
    if kq:
        try:
            con._co_cot_thua = True
        except AttributeError:                          # sqlite3.Connection thường (không phải KetNoi)
            pass
    return kq


def dam_bao_cot_thua(con) -> bool:
    """Thêm các cột COT_THUA_THEM còn thiếu (trong giao dịch của nơi gọi nếu có). Trả True khi bảng có đủ cột."""
    if co_cot_thua(con):
        return True
    co = {r[1] for r in con.execute('PRAGMA table_info(thua)')}
    if not co:
        return False
    for k, kieu in COT_THUA_THEM:
        if k not in co:
            con.execute(f'ALTER TABLE thua ADD COLUMN {k} {kieu}')
    return co_cot_thua(con)


# 1.0.15 (phương án ĐIỀU CHỈNH): pa_lan thêm loai / thay_the - KHÔNG đổi PHIEN_BAN_CSDL (như cột thua): file mới có sẵn (schema.sql),
# file cũ thêm ở csdl.mo khi đã có hộ hoặc lúc ghi lần (lan_pa). Bản cũ mở file vẫn được (cột thừa).
COT_PA_LAN_THEM = (('loai', "TEXT NOT NULL DEFAULT 'bo_sung'"), ('thay_the', 'INTEGER NOT NULL DEFAULT 0'),
                   ('dot_trinh_id', 'INTEGER'))           # 30/10/2026: đợt trình theo LẦN phương án (phễu tiến độ theo hộ)


def co_cot_pa_lan(con) -> bool:
    """pa_lan chưa có (bộ đơn giá, file cũ chưa nâng) hoặc đã có đủ cột COT_PA_LAN_THEM: True (không cần thêm)."""
    co = {r[1] for r in con.execute('PRAGMA table_info(pa_lan)')}
    return not co or all(k in co for k, _ in COT_PA_LAN_THEM)


def dam_bao_cot_pa_lan(con) -> None:
    """Thêm cột loai / thay_the / dot_trinh_id cho pa_lan; lần 1 của mọi hộ là 'chinh'. Trong giao dịch của nơi gọi.
    dot_trinh_id vừa thêm: chép ho.dot_id CHỈ cho hộ có đúng một lần phương án (không nhầm được lần nào đã trình); hộ nhiều lần để
    trống - phễu tiến độ dùng ho.dot_id cho lần đang mở như trước."""
    co = {r[1] for r in con.execute('PRAGMA table_info(pa_lan)')}
    for k, kieu in COT_PA_LAN_THEM:
        if k not in co:
            con.execute(f'ALTER TABLE pa_lan ADD COLUMN {k} {kieu}')
    con.execute("UPDATE pa_lan SET loai = 'chinh' WHERE lan = 1 AND loai = 'bo_sung'")
    if 'dot_trinh_id' not in co:
        con.execute('''UPDATE pa_lan SET dot_trinh_id = (SELECT h.dot_id FROM ho h WHERE h.ma_ho = pa_lan.ma_ho)
                       WHERE (SELECT COUNT(*) FROM pa_lan p2 WHERE p2.ma_ho = pa_lan.ma_ho) = 1''')


# 30/10/2026: lần phương án của dòng ý kiến niêm yết - KHÔNG đổi PHIEN_BAN_CSDL; NULL = dòng cũ (trước khi có cột) = lần 1
COT_Y_KIEN_THEM = (('lan', 'INTEGER'),
                   # 1.0.91 (người dùng 09/11/2026): ý kiến của hộ SAU đối thoại ('' = chưa đối thoại; ý kiến hiệu lực = cột này, không thì loai)
                   ('y_kien_doi_thoai', "TEXT NOT NULL DEFAULT ''"))
COT_DOI_THOAI_THEM = (('y_kien', "TEXT NOT NULL DEFAULT ''"),)      # 1.0.91: ý kiến của hộ ở từng lần đối thoại


def _cot_cua(con, bang: str) -> set:
    return {r[1] for r in con.execute(f'PRAGMA table_info({bang})')}


def co_cot_y_kien(con) -> bool:
    """y_kien_du_thao / doi_thoai_ho chưa có (file cũ) hoặc đã đủ cột thêm: True (không cần thêm)."""
    co, dt = _cot_cua(con, 'y_kien_du_thao'), _cot_cua(con, 'doi_thoai_ho')
    return (not co or all(k in co for k, _ in COT_Y_KIEN_THEM)) and (not dt or all(k in dt for k, _ in COT_DOI_THOAI_THEM))


def dam_bao_cot_y_kien(con) -> None:
    """Thêm cột còn thiếu của y_kien_du_thao, doi_thoai_ho (trong giao dịch của nơi gọi). Bảng chưa có: không làm gì."""
    for bang, ds in (('y_kien_du_thao', COT_Y_KIEN_THEM), ('doi_thoai_ho', COT_DOI_THOAI_THEM)):
        co = _cot_cua(con, bang)
        for k, kieu in ds:
            if co and k not in co:
                con.execute(f'ALTER TABLE {bang} ADD COLUMN {k} {kieu}')


def _tao_pa_lan(con) -> None:
    """Nâng cấp v16 -> v17: bảng pa_lan (theo schema.sql) + lần 1 cho mọi hộ đã có dòng phương án / quyết định; hộ đã có quyết
    định phê duyệt: lần 1 khóa (đã phê duyệt), quyết định cũ (lan 0) coi là phê duyệt lần 1. Bộ đơn giá (không hộ): chỉ tạo bảng."""
    s = _SCHEMA.read_text(encoding='utf-8')
    i = s.index('CREATE TABLE IF NOT EXISTS pa_lan')
    con.execute(s[i:s.index('\n);', i) + 3])
    con.execute('CREATE INDEX IF NOT EXISTS ix_ctdat_lan ON ct_dat(ma_ho, lan)')
    con.execute('CREATE INDEX IF NOT EXISTS ix_ctkhoan_lan ON ct_khoan(ma_ho, lan)')
    if not con.execute('SELECT 1 FROM ho LIMIT 1').fetchone():
        return
    con.execute("""INSERT OR IGNORE INTO pa_lan (ma_ho, lan, ten, ngay_lap, so_pa, ngay_pa, trang_thai, khoa)
                   SELECT h.ma_ho, 1, 'Phương án gốc', COALESCE(substr(h.luu_luc, 1, 10), ''), h.so_pa, h.ngay_pa,
                          CASE WHEN EXISTS (SELECT 1 FROM qd_ho q WHERE q.ma_ho = h.ma_ho) THEN 'da_phe_duyet' ELSE 'dang_lap' END,
                          CASE WHEN EXISTS (SELECT 1 FROM qd_ho q WHERE q.ma_ho = h.ma_ho) THEN 1 ELSE 0 END
                   FROM ho h
                   WHERE EXISTS (SELECT 1 FROM ct_dat d WHERE d.ma_ho = h.ma_ho)
                      OR EXISTS (SELECT 1 FROM ct_khoan k WHERE k.ma_ho = h.ma_ho)
                      OR EXISTS (SELECT 1 FROM qd_ho q WHERE q.ma_ho = h.ma_ho)""")


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
    if not kiem_toan.co_bang_bam(con):
        for cau in kiem_toan._cau(kiem_toan.SQL_BAM):
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


@contextmanager
def tam_tat_gc():
    """Tắt dọn rác của Python trong một thao tác hàng loạt (đo 3.000 hộ: mở dự án -10%, bảng tổng hợp -11%: dữ liệu vừa tạo còn dùng tiếp,
    dọn rác chỉ duyệt lại nó nhiều lần). Lồng được, trả lại trạng thái cũ kể cả khi lỗi. Dùng làm with hoặc @decorator."""
    import gc
    bat = gc.isenabled()
    gc.disable()
    try:
        yield
    finally:
        if bat:
            gc.enable()


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
            try:
                yield con
            except BaseException:
                con.rollback()
                raise
            # như `with con:` nhưng COMMIT bị từ chối NGAY vì khóa (SQLite không chờ được - hai bên cùng đợi nhau) thì thử lại vài lần, giao
            # dịch vẫn còn nguyên. Đã chờ hết busy_timeout (30 s) mà vẫn khóa: không thử lại, tránh treo vài phút
            import time
            for lan in range(5):
                bat_dau = time.monotonic()
                try:
                    con.commit()
                    break
                except sqlite3.OperationalError as e:
                    if not _la_loi_khoa(e) or lan == 4 or time.monotonic() - bat_dau > 2:
                        con.rollback()
                        raise
                    time.sleep(0.15 * (lan + 1))
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


_RE_TRIGGER_HOP_LE = re.compile(r'^(audit_logs_khong_(sua|xoa)|audit_bam_khong_(sua|xoa)|khoa_\w+_(INSERT|UPDATE|DELETE))$')
# 1.0.91 (kiểm toán 09/11/2026): kiểm TOÀN BỘ câu lệnh, neo đầu và cuối - trước chỉ `.search` phần "BEGIN SELECT RAISE… END" ở cuối nên thân
# `UPDATE ho SET tien='0'; -- BEGIN SELECT RAISE(ABORT,'x'); <xuống dòng> END` (lệnh thật + chú thích giả) lọt qua. Hai dạng hợp lệ duy nhất:
# trigger khóa danh mục (có WHEN đọc khoa_dm) và trigger nhật ký (không WHEN); thân chỉ là SELECT RAISE(ABORT, '<chữ>').
_RE_TRIGGER_NGUYEN_VAN = re.compile(
    r'^\s*CREATE\s+TRIGGER\s+(?:IF\s+NOT\s+EXISTS\s+)?"?(?P<ten>\w+)"?\s+BEFORE\s+(?P<viec>INSERT|UPDATE|DELETE)\s+ON\s+"?(?P<bang>\w+)"?\s+'
    r'(?:WHEN\s+\(\s*SELECT\s+mo\s+FROM\s+khoa_dm\s+WHERE\s+id\s*=\s*1\s*\)\s*=\s*0\s+)?'
    r"BEGIN\s+SELECT\s+RAISE\s*\(\s*ABORT\s*,\s*'[^']*'\s*\)\s*;\s*END\s*;?\s*$", re.I)
_RE_TRIGGER_KHOA_DM = re.compile(r'^khoa_(?P<bang>\w+)_(?P<viec>INSERT|UPDATE|DELETE)$')
_RE_TRIGGER_NHAT_KY = re.compile(r'^(?P<bang>audit_logs|audit_bam)_khong_(?P<viec>sua|xoa)$')


def trigger_hop_le(ten: str, sql) -> bool:
    """Trigger do chính phần mềm tạo: tên đúng mẫu, bảng và biến cố khớp tên, thân nguyên văn (xem _RE_TRIGGER_NGUYEN_VAN)."""
    m = _RE_TRIGGER_NGUYEN_VAN.match(sql or '')
    if m is None or m.group('ten') != ten:
        return False
    viec, bang, co_when = m.group('viec').upper(), m.group('bang'), bool(re.search(r'\bWHEN\b', sql, re.I))
    k = _RE_TRIGGER_KHOA_DM.match(ten)
    if k is not None:
        return co_when and k.group('bang') == bang and bang in DANH_MUC and k.group('viec') == viec
    n = _RE_TRIGGER_NHAT_KY.match(ten)
    if n is not None:
        return (not co_when) and n.group('bang') == bang and viec == ('UPDATE' if n.group('viec') == 'sua' else 'DELETE')
    return False


def trigger_la(con) -> list:
    """Tên các trigger trong file KHÔNG phải do phần mềm tạo (chỉ đọc, không ghi gì)."""
    return [r[0] for r in con.execute("SELECT name, sql FROM main.sqlite_master WHERE type = 'trigger'")
            if not trigger_hop_le(r[0], r[1])]


def go_trigger_la(con) -> list:
    """1.0.58: phần mềm chỉ tạo các trigger bền trên; file nhận từ ngoài có trigger khác có thể âm thầm đổi tiền mỗi lần lưu: gỡ + ghi nhật ký.
    Mở chỉ xem: không ghi được, bỏ qua (không có lần ghi nào để trigger chạy). Trả tên đã gỡ."""
    # tên đúng chưa đủ: file ngoài có thể đặt tên giống trigger của phần mềm nhưng thân làm việc khác -> kiểm cả thân (1.0.91: nguyên văn)
    la = trigger_la(con)
    if la:
        try:
            with giao_dich(con):
                for t in la:
                    con.execute('DROP TRIGGER main."{}"'.format(t.replace('"', '""')))
                ghi_nhat_ky(con, 'Gỡ trigger lạ trong file dự án', ', '.join(la))
        except sqlite3.OperationalError:
            return []
    return la


def _kiem_luoc_do(con) -> None:
    """1.0.97 (thử file hỏng ngẫu nhiên): lược đồ có byte hỏng làm MỌI câu lệnh sau ném UnicodeDecodeError (Python không giải mã được
    thông báo lỗi của SQLite) - không phải sqlite3.Error nên các hộp thoại không bắt, phần mềm văng. Đọc trọn lược đồ (vài KB) ngay khi
    mở: hỏng -> sqlite3.DatabaseError có lời rõ ràng."""
    try:
        con.execute('SELECT type, name, tbl_name, sql FROM main.sqlite_master').fetchall()
        try:                                            # câu chạm bảng: SQLite mới PHÂN TÍCH lược đồ (đọc sqlite_master thì chưa)
            con.execute('SELECT 1 FROM main.ho LIMIT 0').fetchall()
        except sqlite3.OperationalError as e:
            if 'no such table' not in str(e):           # file chỉ danh mục / bộ đơn giá không có bảng ho: lược đồ vẫn đọc được
                raise
    except (UnicodeDecodeError, sqlite3.DatabaseError) as e:
        raise sqlite3.DatabaseError('File dự án bị hỏng (không đọc được cấu trúc bảng). Mở bản sao lưu tự động hoặc Cỗ máy thời gian '
                                    'để khôi phục.') from e


def _go_trigger_la_som(con) -> list:
    """1.0.91: gỡ trigger lạ NGAY khi mở (trước nâng cấp lược đồ / mở rộng / ghi tối thiểu - những lần ghi đầu tiên mà trigger lạ có thể
    can thiệp; trước đây chỉ GUI quét, sau khi csdl.mo đã ghi: CLI nhập / đối chiếu, máy chủ LAN, chữa bệnh không quét). Không ghi nhật ký ở
    đây (file cũ có thể chưa có bảng nhật ký): trả tên để nơi gọi ghi sau. Mở chỉ xem: không gỡ được, trả []."""
    la = trigger_la(con)
    if not la:
        return []
    try:
        con.execute('BEGIN IMMEDIATE')
        for t in la:
            con.execute('DROP TRIGGER main."{}"'.format(t.replace('"', '""')))
        con.execute('COMMIT')
    except sqlite3.OperationalError:
        try:
            con.execute('ROLLBACK')
        except sqlite3.OperationalError:
            pass
        return []
    return la


def chep_danh_muc(con, file_nguon, don_vi: bool = True, bang=DANH_MUC, trong_gd=None) -> None:
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
            if trong_gd is not None:                    # 1.0.58: việc phải cùng giao dịch với chép (ATTACH thì phải ngoài giao dịch)
                trong_gd()
    finally:
        con.execute('DETACH DATABASE nguon')


# thông tin đơn vị lập, người ký: thuộc về đơn vị chứ không thuộc dự án -> giữ khi xóa trắng, chép khi tạo dự án mới
TRUONG_DON_VI = ('don_vi_cap_tren', 'don_vi_tieu_de', 'don_vi_lap', 'dia_danh_don_vi', 'ky_hieu_so', 'nguoi_lap', 'nguoi_kiem_tra',
                 'chuc_vu_ky', 'nguoi_ky')
# cột thêm vào du_an KHÔNG đổi PHIEN_BAN_CSDL (như cột thua): file mới có sẵn (schema.sql), file cũ thêm khi lưu Thông tin dự án (lap_pa.luu_du_an)
# hoặc khi mở file có hộ (csdl.mo) - không ghi vào bộ đơn giá đóng gói (không có hộ). Bản cũ mở file vẫn được (cột thừa)
COT_DU_AN_THEM = (('dia_danh_don_vi', "TEXT NOT NULL DEFAULT ''"),)


def dam_bao_cot_du_an(con) -> None:
    """Thêm các cột COT_DU_AN_THEM còn thiếu (trong giao dịch của nơi gọi nếu có)."""
    co = {r[1] for r in con.execute('PRAGMA table_info(du_an)')}
    for k, kieu in COT_DU_AN_THEM:
        if co and k not in co:
            con.execute(f'ALTER TABLE du_an ADD COLUMN {k} {kieu}')


# P2 (03/11/2026): sổ mở rộng lược đồ KHÔNG đổi PHIEN_BAN_CSDL (file mới có sẵn từ schema.sql; file cũ có hộ thêm ở csdl.mo). Thêm phần mở
# rộng mới: viết hàm kiểm (con) -> True khi ĐÃ CÓ và hàm làm (con) chạy trong giao dịch của nơi gọi, rồi thêm một dòng vào đây (thứ tự =
# thứ tự chạy: chỉ mục cuối vì cần cột). Bản cũ mở file có phần mở rộng vẫn được (bảng / cột thừa vô hại); phần nào làm bản cũ GHI SAI
# dữ liệu thì tăng GHI_TOI_THIEU.
def co_cot_ap_gia(con) -> bool:
    return 'ap_gia' in {r[1] for r in con.execute('PRAGMA table_info(ct_dat)')}


MO_RONG = (
    ('cot_ghi_chu_ten', lambda con: co_cot_ghi_chu_ten(con), lambda con: dam_bao_cot_ghi_chu_ten(con)),      # 1.0.78
    ('cot_ap_gia', lambda con: co_cot_ap_gia(con), lambda con: con.execute("ALTER TABLE ct_dat ADD COLUMN ap_gia TEXT NOT NULL DEFAULT ''")),   # 1.0.69: giá gốc, K1, K2, K3 của dòng đất
    ('bang_phu', lambda con: bool(con.execute("SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'anh_hien_trang'").fetchone()),
     lambda con: _tao_bang_phu(con)),
    ('bang_bam', lambda con: _co_bang_bam_kt(con), lambda con: _tao_bang_bam_kt(con)),        # 1.0.55: chuỗi băm kiểm toán
    ('cot_pa_lan', lambda con: co_cot_pa_lan(con), lambda con: dam_bao_cot_pa_lan(con)),
    ('cot_y_kien', lambda con: co_cot_y_kien(con), lambda con: dam_bao_cot_y_kien(con)),
    ('cot_thua', lambda con: co_cot_thua(con), lambda con: dam_bao_cot_thua(con)),
    ('cot_du_an', lambda con: all(k in {r[1] for r in con.execute('PRAGMA table_info(du_an)')} for k, _ in COT_DU_AN_THEM),
     lambda con: dam_bao_cot_du_an(con)),
    ('phien_ban_pa', lambda con: bool(con.execute("SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'pa_phien_ban'").fetchone()),
     lambda con: _tao_bang_phien_ban(con)),                                                    # 1.0.63: V1, V2.n, V3
    ('cot_ban_do', lambda con: _co_cot_ban_do(con), lambda con: con.execute("ALTER TABLE thua_ban_do ADD COLUMN chi_tiet TEXT NOT NULL DEFAULT ''")),
    ('chi_muc', lambda con: bool(con.execute("SELECT 1 FROM sqlite_master WHERE type = 'index' AND name = ?",
                                             (CHI_MUC_THEM[-1][0],)).fetchone()), lambda con: dam_bao_chi_muc(con)),
)


def _co_cot_ban_do(con) -> bool:
    """Bảng thua_ban_do chưa có (file chưa có hộ / bảng phụ chưa tạo - tạo sẽ đủ cột) hoặc đã có cột chi_tiet (ban_do_ghep)."""
    cot = {r[1] for r in con.execute('PRAGMA table_info(thua_ban_do)')}
    return not cot or 'chi_tiet' in cot


def _tao_bang_phien_ban(con) -> None:
    """Ảnh chụp phiên bản phương án (phien_ban_pa.py) + mã định danh hộ nhúng vào file xuất."""
    con.execute('''CREATE TABLE IF NOT EXISTS pa_phien_ban (
        id INTEGER PRIMARY KEY, ma_ho INTEGER NOT NULL REFERENCES ho(ma_ho) ON UPDATE CASCADE ON DELETE CASCADE, ma TEXT NOT NULL, lan INTEGER NOT NULL DEFAULT 1,
        loai TEXT NOT NULL DEFAULT '', nhan TEXT NOT NULL DEFAULT '', tao_luc TEXT NOT NULL DEFAULT '', nguoi_tao TEXT NOT NULL DEFAULT '', khoa INTEGER NOT NULL DEFAULT 0,
        cha TEXT NOT NULL DEFAULT '', ghi_chu TEXT NOT NULL DEFAULT '', nguon_nhom TEXT NOT NULL DEFAULT '{}', du_lieu TEXT NOT NULL, UNIQUE (ma_ho, ma))''')
    con.execute('''CREATE TABLE IF NOT EXISTS ho_uuid (
        ma_ho INTEGER PRIMARY KEY REFERENCES ho(ma_ho) ON UPDATE CASCADE ON DELETE CASCADE, uuid TEXT NOT NULL UNIQUE)''')


def _co_bang_bam_kt(con) -> bool:
    """Đủ khi đã có audit_bam, hoặc file chưa có audit_logs (bảng phụ chưa tạo - bang_phu tạo cả hai)."""
    ten = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type = 'table' AND name IN ('audit_logs', 'audit_bam')")}
    return 'audit_bam' in ten or 'audit_logs' not in ten


def _tao_bang_bam_kt(con) -> None:
    from . import kiem_toan
    for cau in kiem_toan._cau(kiem_toan.SQL_BAM):
        con.execute(cau)


def thieu_mo_rong(con) -> list:
    """Tên các phần mở rộng lược đồ (MO_RONG) file còn thiếu - chỉ đọc (Bác sĩ CSDL, kiểm thử)."""
    return [ten for ten, kiem, _lam in MO_RONG if not kiem(con)]


def dam_bao_mo_rong(con) -> list:
    """Thêm các phần mở rộng còn thiếu của file có hộ, MỘT giao dịch. Trả tên phần đã thêm ([] khi đủ / không có hộ / chỉ xem, file
    khóa - các hàm ghi tự thêm phần của mình khi cần)."""
    thieu = thieu_mo_rong(con)
    if not thieu or not con.execute('SELECT 1 FROM ho LIMIT 1').fetchone():
        return []
    lam = {ten: f for ten, _k, f in MO_RONG}
    try:
        with con:
            if not con.in_transaction:                  # sqlite3 không tự mở giao dịch trước ALTER / CREATE: mở tay cho cả lô
                con.execute('BEGIN')                    # (một lần ghi đĩa; lỗi giữa chừng không để file nửa cũ nửa mới)
            for ten in thieu:
                lam[ten](con)
    except sqlite3.OperationalError:                    # chỉ xem / file khóa: lần mở sau
        return []
    return thieu


class DauVetHo:
    """Ghi lại các hộ có dữ liệu bị thêm / sửa / xóa trên một kết nối (trigger TẠM - chỉ sống trong phiên, không ghi vào file
    .pabt), để màn hình chỉ tính và vẽ lại các hộ đó thay vì cả dự án (3.000 hộ: ~0,6 giây mỗi lần lưu một hộ).

    lay(): tập mã hộ đã đổi kể từ lần lấy trước; None = phải nạp lại toàn bộ: thêm / xóa hộ, đổi thứ tự / mã hộ, ghi bảng không
    theo hộ (danh mục, dự án, quyết định, đợt trình, cài đặt...), hoặc kết nối / máy khác đã ghi vào file (PRAGMA data_version).
    Sổ ghi chỉ thêm dòng (không xóa sau mỗi lần lấy) để việc lấy không mở giao dịch, không làm đổi total_changes (csdl.nho)."""
    BO_QUA = ('nhat_ky', 'khoa_dm', 'sqlite_sequence', 'tho_nhap', 'audit_bam')   # không ảnh hưởng số liệu hiển thị của hộ
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


_TEN_MAY: list = []


def ten_may() -> str:
    """Tên máy tính (ghi nhật ký, khóa file, máy chủ LAN). Bằng đúng platform.node() - hàm đó cũng gọi socket.gethostname() - nhưng
    không qua platform.uname(): từ Python 3.12 uname() đọc thông tin Windows qua WMI, lần gọi đầu mất ~50 ms."""
    if _TEN_MAY:
        return _TEN_MAY[0]
    import socket
    try:
        _TEN_MAY.append(socket.gethostname())
    except OSError:
        return ''
    return _TEN_MAY[0]


def tham_so(con: sqlite3.Connection) -> dict:
    return {r['ma']: r['gia_tri'] for r in con.execute('SELECT ma, gia_tri FROM tham_so')}


def doc_cai_dat(con: sqlite3.Connection, ma: str, mac_dinh: str = '') -> str:
    """Cài đặt riêng của dự án (thư mục hồ sơ, tỷ lệ mặc định...): bảng cai_dat, không thuộc danh mục khóa."""
    try:
        r = con.execute('SELECT gia_tri FROM cai_dat WHERE ma = ?', (ma,)).fetchone()
    except sqlite3.OperationalError:                # file chỉ xem phiên bản cũ chưa có bảng
        return mac_dinh
    return r[0] if r is not None and r[0] != '' else mac_dinh


# Phần mềm ghi tối thiểu (rà soát kiến trúc 01/11/2026): lược đồ được mở rộng NHIỀU LẦN mà không đổi PHIEN_BAN_CSDL (bảng / cột thêm
# - bản cũ vẫn MỞ được) nhưng bản cũ GHI thì không giữ các bất biến mới (vd. y_kien_du_thao.lan NULL = lần 1). Phần mềm mở để sửa ghi
# số phiên bản tối thiểu vào cai_dat; bản thấp hơn số đó (từ bản này trở đi - bản cũ hơn không biết khóa này) tự mở CHỈ XEM.
# Tăng GHI_TOI_THIEU khi thêm cột / bảng mở rộng mà bản trước ghi sẽ làm sai dữ liệu.
KHOA_GHI_TOI_THIEU = 'PHAN_MEM_GHI_TOI_THIEU'
GHI_TOI_THIEU = '1.0.41'            # lần đầu ghi cờ: bản 1.0.40 đã phát hành chưa biết khóa này
TEN_BO_DON_GIA = 'bo_don_gia.sqlite'


def so_phien_ban(s) -> tuple:
    """'1.0.40' -> (1, 0, 40); chữ lạ -> ()."""
    try:
        return tuple(int(x) for x in str(s or '').strip().split('.') if x != '')
    except ValueError:
        return ()


def phan_mem_ghi_toi_thieu(con) -> str:
    return doc_cai_dat(con, KHOA_GHI_TOI_THIEU, '')


def qua_cu_de_ghi(con, phien_ban: str) -> str:
    """Phiên bản tối thiểu file yêu cầu nếu phien_ban THẤP hơn (phải mở chỉ xem); '' nếu được ghi."""
    yc = phan_mem_ghi_toi_thieu(con)
    return yc if yc and so_phien_ban(yc) > so_phien_ban(phien_ban) else ''


def duong_goi_y(con, ten_file: str = '') -> str:
    """Nơi lưu gợi ý cho hộp "Lưu thành": thư mục chứa file dự án + ten_file (người dùng 05/11/2026). Dự án trong bộ nhớ,
    bản sao lưu đang mở (file giải nén tạm): chỉ trả ten_file, để Windows tự chọn thư mục."""
    try:
        dd = con.execute('PRAGMA database_list').fetchone()
    except sqlite3.Error:
        dd = None
    if not dd or not dd[2] or getattr(con, '_file_tam', None):
        return ten_file
    goc = Path(dd[2]).parent
    return str(goc / ten_file) if ten_file else str(goc)


def dat_ghi_toi_thieu(con) -> bool:
    """Ghi GHI_TOI_THIEU vào file (chỉ khi file đang ghi số thấp hơn / chưa có). True nếu đã ghi. File chỉ đọc / bộ đơn giá
    đóng gói / không có bảng cai_dat / lỗi: False. Không ghi nhật ký (chạy lúc mở, trước Hoàn tác)."""
    if so_phien_ban(phan_mem_ghi_toi_thieu(con)) >= so_phien_ban(GHI_TOI_THIEU):
        return False
    try:
        dd = con.execute('PRAGMA database_list').fetchone()
        if Path(dd[2] if dd else '').name.lower() == TEN_BO_DON_GIA:
            return False
        if not con.execute("SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'cai_dat'").fetchone():
            return False
        with giao_dich(con):
            ghi_cai_dat(con, KHOA_GHI_TOI_THIEU, GHI_TOI_THIEU)
    except sqlite3.Error:
        return False
    return True


def ghi_cai_dat(con: sqlite3.Connection, ma: str, gia_tri) -> None:
    con.execute('INSERT INTO cai_dat (ma, gia_tri) VALUES (?, ?) ON CONFLICT(ma) DO UPDATE SET gia_tri = excluded.gia_tri',
                (ma, str(gia_tri)))

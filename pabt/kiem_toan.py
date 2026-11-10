"""Nhật ký kiểm toán (0.9.86 - người dùng 14/10/2026, Cụm 2 "audit trail"): ghi vết AI sửa, LÚC NÀO, trên MÁY nào, hộ / thửa nào,
trường nào, giá trị CŨ -> MỚI (đơn giá, diện tích, số lượng, tỷ lệ, thông tin hộ, thửa) để bảo vệ cán bộ khi thanh tra, kiểm toán.

Bảng audit_logs nằm trong file dự án (.pabt) - không đổi PHIEN_BAN_CSDL (như nhat_ky_van_dong): schema.sql tạo cho file mới,
csdl.mo tạo cho file cũ đã có hộ (bộ đơn giá / file chỉ danh mục không bị ghi). Hai trigger LƯU TRONG FILE chặn sửa / xóa dòng nhật
ký (kể cả công cụ SQLite khác mở file); Hoàn tác (hoan_tac.BO_QUA) không đụng bảng này - thao tác hoàn tác cũng được ghi vết.

Ghi vết bằng hai cách:
- TRIGGER TẠM của kết nối (gan(con) - app.mo, như hoan_tac / DauVetHo): bảng ho, thua (thêm / sửa từng trường / xóa), gia_dat,
  dm_taisan, dm_hotro (chỉ SỬA - nạp lại cả bộ đơn giá là thay hàng loạt, đã có trong nhat_ky). Trigger tạm không nằm trong file: bản
  PABT cũ / công cụ khác mở file vẫn ghi được (không cần hàm riêng); người / máy lấy từ bảng tạm _kt_phien (đổi khi đăng nhập LAN).
- So sánh phương án khi Lưu (ghi_thay_doi_pa - lap_pa.BoSoan.luu): phương án lưu bằng xóa rồi chèn lại mọi dòng nên trigger không
  ghép được cũ / mới; so bản lúc mở (_pa_goc) với bản lưu theo từng dòng (mục 1 theo thửa + loại đất, mục 2-4 theo mã / tên).
Dữ liệu nhập hàng loạt khi TẠO dự án (Dự án mới, nhập Excel - kết nối riêng, không gắn trigger) là số liệu gốc, không ghi từng dòng.
"""
from __future__ import annotations
import hashlib
import sqlite3
from datetime import datetime

from . import an_toan as _an_toan
from . import csdl

BANG = 'audit_logs'
SQL_BANG = f'''
CREATE TABLE IF NOT EXISTS {BANG} (
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
CREATE INDEX IF NOT EXISTS ix_audit_logs_ho ON {BANG}(ma_ho, luc);
CREATE INDEX IF NOT EXISTS ix_audit_logs_luc ON {BANG}(luc);
CREATE TRIGGER IF NOT EXISTS {BANG}_khong_sua BEFORE UPDATE ON {BANG}
BEGIN SELECT RAISE(ABORT, 'Nhật ký kiểm toán không được sửa.'); END;
CREATE TRIGGER IF NOT EXISTS {BANG}_khong_xoa BEFORE DELETE ON {BANG}
BEGIN SELECT RAISE(ABORT, 'Nhật ký kiểm toán không được xóa.'); END;
'''

# 1.0.55 (người dùng 03/11/2026): CHUỖI BĂM - mỗi dòng audit_logs ghi qua phần mềm được ký SHA-256 nối với dòng ký trước (kiểu
# blockchain), lưu ở bảng riêng audit_bam (audit_logs chặn UPDATE; trigger nhiều dòng INSERT … SELECT tính trước cả lô nên không nối
# được từng dòng trong cùng câu lệnh - trigger AFTER INSERT từng dòng ghi sang bảng riêng thì nối đúng thứ tự). Sửa / xóa dòng nhật ký
# bằng công cụ SQLite ngoài phần mềm (sau khi DROP trigger chặn) làm chuỗi gãy -> kiem_tra_toan_ven báo đúng dòng. Giới hạn: không dùng
# khóa bí mật (file dùng chung nhiều máy / Google Drive) - người biết thuật toán vẫn tính lại được cả chuỗi; xóa các dòng CUỐI cùng
# không để lại dấu (so với bản in / bản xuất Excel nhật ký đã nộp). Dòng ghi bằng bản cũ / kết nối không gắn ký: "chưa ký", không phải lỗi.
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
COT_BAM = ('id', 'luc', 'nguoi', 'may', 'hanh_dong', 'bang', 'khoa', 'ma_ho', 'ma_thua', 'doi_tuong', 'truong', 'cu', 'moi', 'thao_tac')
MUOI_BAM = 'LARC_AUDIT_2026|'


def tinh_bam(bam_truoc, *gia_tri) -> str:
    """Băm một dòng nhật ký: SHA-256 của băm dòng ký trước + các cột COT_BAM (None -> ''), lấy 32 ký tự hex đầu."""
    chuoi = '|'.join('' if x is None else str(x) for x in (bam_truoc, *gia_tri))
    return hashlib.sha256((MUOI_BAM + chuoi).encode('utf-8')).hexdigest()[:32]


def co_bang_bam(con) -> bool:
    return con.execute("SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?", (BANG_BAM,)).fetchone() is not None


def gan_ky(con) -> bool:
    """Hàm _kt_bam + trigger TẠM ký từng dòng audit_logs của kết nối (gọi lại được; trong giao dịch của nơi gọi). False nếu file chưa có
    bảng nhật ký / bảng băm (file cũ chỉ xem)."""
    if not co_bang(con) or not co_bang_bam(con):
        return False
    con.create_function('_kt_bam', len(COT_BAM) + 1, tinh_bam)
    gt = ', '.join(f'NEW."{c}"' for c in COT_BAM)
    con.execute(f'''CREATE TEMP TRIGGER IF NOT EXISTS _kt_ky AFTER INSERT ON main.{BANG} BEGIN
                    INSERT INTO {BANG_BAM} (id, bam) VALUES (NEW.id, _kt_bam(COALESCE((SELECT bam FROM main.{BANG_BAM}
                    ORDER BY id DESC LIMIT 1), ''), {gt})); END''')
    return True


def kiem_tra_toan_ven(con) -> dict:
    """Đối chiếu chuỗi băm (đọc, không ghi): hop_le, so_dong (nhật ký), so_dong_da_ky, so_chua_ky (ghi bằng bản cũ / kết nối không ký),
    loi [chữ] - dòng bị sửa (băm không khớp), dòng ký bị xóa (băm dòng sau không khớp / băm mồ côi), khoảng trống id. Dòng chưa ký ở
    đầu bảng (trước 1.0.55) là mốc khởi đầu hợp lệ."""
    kq = dict(hop_le=True, so_dong=0, so_dong_da_ky=0, so_chua_ky=0, loi=[])
    if not co_bang(con):
        return kq
    bam = {}
    if co_bang_bam(con):
        bam = dict(con.execute(f'SELECT id, bam FROM {BANG_BAM}').fetchall())
    truoc, id_truoc, da_ky = '', None, False
    cot = ', '.join(f'"{c}"' for c in COT_BAM)
    for r in con.execute(f'SELECT {cot} FROM {BANG} ORDER BY id'):
        kq['so_dong'] += 1
        i = r[0]
        if da_ky and id_truoc is not None and i != id_truoc + 1:
            kq['loi'].append(f'Thiếu dòng nhật ký số {id_truoc + 1}' + (f' - {i - 1}' if i - 1 > id_truoc + 1 else '') +
                             ' (bị xóa ngoài phần mềm).')
        id_truoc = i
        b = bam.pop(i, None)
        if b is None:
            kq['so_chua_ky'] += 1
            continue
        da_ky = True
        kq['so_dong_da_ky'] += 1
        if tinh_bam(truoc, *r) != b:
            kq['loi'].append(f'Dòng nhật ký số {i} ({r[1]}) không khớp chuỗi băm: nội dung dòng này hoặc một dòng đã ký ngay trước nó '
                             'bị sửa / xóa ngoài phần mềm.')
        truoc = b
    for i in sorted(bam):
        kq['loi'].append(f'Có mã băm của dòng nhật ký số {i} nhưng dòng đó không còn (bị xóa ngoài phần mềm).')
    kq['loi'] += kiem_tra_neo(con)              # 1.0.97: cắt đuôi / tính lại cả chuỗi so với điểm neo ngoài file
    kq['hop_le'] = not kq['loi']
    return kq


# ---------------------------------------------------------------- 1.0.97: ĐIỂM NEO ngoài file (kiểm toán bảo mật 09/11/2026)
# Chuỗi băm nằm trong file nên người sửa được file tính lại được cả chuỗi, và xóa các dòng CUỐI không để lại dấu. Mỗi lần mở / đóng dự
# án trên máy này phần mềm nhớ (dòng ký cuối, băm của nó) ở thư mục máy - ngoài file. Lần sau: dòng neo phải còn trong file với đúng
# băm, nếu không -> báo nhật ký đã bị cắt đuôi hoặc tính lại sau lần làm việc trước TRÊN MÁY NÀY. Chuỗi nhận diện bằng dòng ký ĐẦU tiên
# (không theo đường dẫn: file chép / đổi tên vẫn khớp). Không khóa bí mật (quyết định 1.0.55: file dùng chung nhiều máy).
FILE_NEO = 'neo_kiem_toan.json'
NEO_TOI_DA = 500                                # số chuỗi (dự án) nhớ trên một máy


def _duong_neo():
    from .dia_phuong import thu_muc_may
    return thu_muc_may() / FILE_NEO


def _doc_neo() -> dict:
    import json
    try:
        d = json.loads(_duong_neo().read_text(encoding='utf-8'))
        return d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


def khoa_chuoi(con) -> str | None:
    """Nhận diện chuỗi băm: id + băm của dòng ký đầu tiên. None: file chưa có dòng ký."""
    if not co_bang_bam(con):
        return None
    r = con.execute(f'SELECT id, bam FROM {BANG_BAM} ORDER BY id LIMIT 1').fetchone()
    return f'{r[0]}:{r[1]}' if r else None


def kiem_tra_neo(con) -> list:
    """Lỗi so với điểm neo của máy này (đọc, không ghi). [] khi chưa có neo / khớp."""
    k = khoa_chuoi(con)
    neo = _doc_neo().get(k) if k else None
    if not neo:
        return []
    try:
        i, bam_neo = int(neo['id']), str(neo['bam'])
    except (KeyError, TypeError, ValueError):
        return []
    r = con.execute(f'SELECT bam FROM {BANG_BAM} WHERE id = ?', (i,)).fetchone()
    luc = str(neo.get('luc', ''))
    if r is None:
        return [f'Nhật ký kiểm toán bị CẮT ĐUÔI: máy này đã thấy tới dòng số {i} (lúc {luc}) nhưng file không còn dòng đó.']
    if r[0] != bam_neo:
        return [f'Chuỗi băm nhật ký bị TÍNH LẠI: dòng số {i} khác mã băm máy này ghi nhận lúc {luc}.']
    return []


def ghi_neo(con) -> bool:
    """Nhớ dòng ký cuối của chuỗi vào thư mục máy. CHỈ ghi khi chuỗi khớp neo cũ và không lùi (không xóa dấu vết khi file đã bị sửa).
    Lỗi ghi (thư mục không ghi được): bỏ qua."""
    import json
    from datetime import datetime as _dt
    k = khoa_chuoi(con)
    if not k or kiem_tra_neo(con):
        return False
    r = con.execute(f'SELECT id, bam FROM {BANG_BAM} ORDER BY id DESC LIMIT 1').fetchone()
    d = _doc_neo()
    cu = d.get(k) or {}
    try:
        if int(cu.get('id', -1)) > r[0]:
            return False
    except (TypeError, ValueError):
        pass
    d[k] = dict(id=r[0], bam=r[1], luc=_dt.now().strftime('%d/%m/%Y %H:%M'))
    if len(d) > NEO_TOI_DA:                     # bỏ chuỗi lâu nhất (thứ tự chèn của dict)
        for x in list(d)[:len(d) - NEO_TOI_DA]:
            d.pop(x, None)
    try:
        p = _duong_neo()
        p.parent.mkdir(parents=True, exist_ok=True)
        tam = p.with_suffix('.tmp')
        tam.write_text(json.dumps(d, ensure_ascii=False), encoding='utf-8')
        tam.replace(p)
        return True
    except OSError:
        return False


# bảng theo dõi bằng trigger tạm: (khóa, mã hộ, mã thửa, mô tả đối tượng - biểu thức SQL trên dòng R, ghi thêm / xóa?, [trường])
THEO_DOI = {
    'ho': ('R.ma_ho', 'R.ma_ho', 'NULL', 'R.ho_ten', True,
           ('ho_ten', 'so_cccd', 'ngay_cap', 'noi_cap', 'dia_chi', 'dien_thoai', 'phap_ly', 'tranh_chap', 'tai_dinh_cu', 'ghi_chu',
            'phai_di_chuyen', 'nhan_khau', 'dt_nn_dang_dung', 'ma_vuong', 'ghi_chu_phap_ly')),
    'thua': ('R.ma_thua', 'R.ma_ho', 'R.ma_thua', "'Thửa ' || COALESCE(R.so_thua, '') || ' tờ ' || COALESCE(R.so_to, '')", True,
             ('ma_ho', 'so_to', 'so_thua', 'loai_dat', 'dt_thu_hoi', 'nguon_goc', 'vi_tri')),
    'gia_dat': ('R.id', 'NULL', 'NULL',
                "COALESCE(R.xa_phuong, '') || ' - ' || COALESCE(R.loai_dat, '') || ' - ' || COALESCE(R.tuyen_duong, '') || ' VT ' "
                "|| COALESCE(R.vi_tri, '')", False, ('gia', 'he_so_k', 'can_cu', 'tuyen_duong', 'vi_tri')),
    'dm_taisan': ('R.ma', 'NULL', 'NULL', "R.ma || ' ' || COALESCE(R.ten, '')", False, ('ten', 'dvt', 'don_gia', 'ghi_chu')),
    'dm_hotro': ('R.ma', 'NULL', 'NULL', "R.ma || ' ' || COALESCE(R.ten, '')", False, ('ten', 'dvt', 'don_gia', 'cach_tinh', 'can_cu')),
    # rà soát kiến trúc 31/10/2026: tiền quyết định phê duyệt và chi trả của từng hộ (phần thanh tra hỏi nhiều nhất) - thêm / bỏ hộ khỏi
    # quyết định và mọi lần sửa số tiền, đã chi trả, ngày, số tiền nhận
    'qd_ho': ('R.id', 'R.ma_ho', 'NULL', "'Quyết định ' || COALESCE((SELECT so FROM quyet_dinh WHERE id = R.qd_id), R.qd_id)", True,
              ('so_tien', 'tien_dat', 'tien_tai_san', 'tien_cay', 'tien_ho_tro', 'tien_thuong', 'qd_ct_so', 'qd_ct_ngay', 'da_chi_tra',
               'chi_tra_ngay', 'chi_tra_so_tien', 'ly_do_chua_nhan')),
}

NHAN_TRUONG = {
    'ho_ten': 'Họ tên', 'so_cccd': 'Số CCCD', 'ngay_cap': 'Ngày cấp', 'noi_cap': 'Nơi cấp', 'dia_chi': 'Địa chỉ',
    'dien_thoai': 'Điện thoại', 'phap_ly': 'Pháp lý', 'tranh_chap': 'Tranh chấp', 'tai_dinh_cu': 'Tái định cư', 'ghi_chu': 'Ghi chú',
    'phai_di_chuyen': 'Phải di chuyển chỗ ở', 'nhan_khau': 'Nhân khẩu', 'dt_nn_dang_dung': 'DT đất NN đang sử dụng',
    'ma_vuong': 'Vướng mắc', 'ghi_chu_phap_ly': 'Ghi chú pháp lý', 'ma_ho': 'Thuộc hộ (mã)', 'so_to': 'Số tờ', 'so_thua': 'Số thửa',
    'loai_dat': 'Loại đất', 'dt_thu_hoi': 'DT thu hồi (m²)', 'nguon_goc': 'Nguồn gốc', 'vi_tri': 'Vị trí', 'gia': 'Giá đất',
    'he_so_k': 'Hệ số K', 'can_cu': 'Căn cứ', 'tuyen_duong': 'Tuyến đường', 'ten': 'Tên', 'dvt': 'ĐVT', 'don_gia': 'Đơn giá',
    'cach_tinh': 'Cách tính', 'dien_tich': 'Diện tích (m²)', 'gia_bang_gia': 'Giá theo bảng giá', 'ty_le': 'Tỷ lệ',
    'so_luong': 'Số lượng', 'ma_tuong_duong': 'Mã tương đương', 'quy_cach': 'Quy cách', 'can_cu_gia': 'Căn cứ giá',
    'so_tien': 'Số tiền phê duyệt', 'tien_dat': 'Tiền đất', 'tien_tai_san': 'Tiền tài sản', 'tien_cay': 'Tiền cây trồng, vật nuôi',
    'tien_ho_tro': 'Tiền hỗ trợ', 'tien_thuong': 'Tiền thưởng', 'qd_ct_so': 'QĐ chi tiết số', 'qd_ct_ngay': 'QĐ chi tiết ngày',
    'da_chi_tra': 'Đã chi trả', 'chi_tra_ngay': 'Ngày chi trả', 'chi_tra_so_tien': 'Số tiền đã nhận', 'ly_do_chua_nhan': 'Lý do chưa nhận',
}
HANH_DONG = {'them': 'Thêm', 'sua': 'Sửa', 'xoa': 'Xóa'}


# ---------------------------------------------------------------- bảng
def co_bang(con) -> bool:
    return con.execute("SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?", (BANG,)).fetchone() is not None


def dam_bao_bang(con) -> bool:
    """Tạo bảng + trigger chặn sửa / xóa (nếu chưa có), cả bảng chuỗi băm. False nếu không ghi được (file chỉ xem / đang khóa)."""
    if co_bang(con) and co_bang_bam(con):
        return True
    try:
        with csdl.giao_dich(con):
            for cau in ([] if co_bang(con) else _cau(SQL_BANG)) + _cau(SQL_BAM):
                con.execute(cau)
    except sqlite3.OperationalError:                    # file chỉ đọc / đang khóa
        return False
    return True


def _cau(sql: str) -> list:
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


# ---------------------------------------------------------------- người, phiên
def nguoi_dung() -> str:
    return csdl.nguoi_dung()


def ghi_su_kien(con, viec: str, chi_tiet: str = '', bang: str = 'du_an') -> None:
    """1.0.58: một dòng nhật ký kiểm toán cho thao tác đổi cả khối số liệu (hoàn tác, khôi phục mốc). File chưa có bảng: bỏ qua."""
    from datetime import datetime
    try:
        con.execute("INSERT INTO audit_logs (luc, nguoi, may, hanh_dong, bang, doi_tuong, moi, thao_tac) VALUES (?,?,?,'sua',?,?,?,?)",
                    (datetime.now().isoformat(timespec='seconds'), nguoi_dung(), csdl.ten_may(), bang, 'Cả dự án', chi_tiet or viec, viec))
    except sqlite3.OperationalError:
        pass


def dat_phien(con, nguoi: str | None = None, may: str | None = None) -> None:
    """Người / máy ghi vào nhật ký kiểm toán của kết nối (đăng nhập LAN đổi người: gọi lại)."""
    con.execute('CREATE TEMP TABLE IF NOT EXISTS _kt_phien (id INTEGER PRIMARY KEY CHECK (id = 1), nguoi TEXT, may TEXT)')
    con.execute('INSERT OR REPLACE INTO temp._kt_phien (id, nguoi, may) VALUES (1, ?, ?)',
                (nguoi if nguoi is not None else nguoi_dung(), may if may is not None else csdl.ten_may()))
    con.commit()


# ---------------------------------------------------------------- trigger tạm
_LUC = "strftime('%Y-%m-%dT%H:%M:%S', 'now', 'localtime')"
_AI = '(SELECT nguoi FROM _kt_phien WHERE id = 1), (SELECT may FROM _kt_phien WHERE id = 1)'


def _trigger(bang: str) -> list:
    khoa, ho, thua, dt, them_xoa, truong = THEO_DOI[bang]
    cot = 'luc, nguoi, may, hanh_dong, bang, khoa, ma_ho, ma_thua, doi_tuong, truong, cu, moi'

    def theo(dong: str, x: str) -> str:
        return x.replace('R.', f'{dong}.')
    ds = ' UNION ALL '.join(f"SELECT '{t}' AS t, CAST(OLD.\"{t}\" AS TEXT) AS c, CAST(NEW.\"{t}\" AS TEXT) AS m" for t in truong)
    # máy yếu (16/10/2026): trigger chỉ chạy khi câu UPDATE có ghi một trường được theo dõi (UPDATE OF …) VÀ trường đó đổi giá trị
    # (WHEN) - cập nhật cột theo dõi tiến độ (phê duyệt, chi trả, bàn giao…) của 3.000 hộ không còn so 15 trường mỗi dòng
    cot_of = ', '.join(f'"{t}"' for t in truong)
    doi = ' OR '.join(f'OLD."{t}" IS NOT NEW."{t}"' for t in truong)
    kq = [f'''CREATE TEMP TRIGGER IF NOT EXISTS _kt_{bang}_sua AFTER UPDATE OF {cot_of} ON main."{bang}" WHEN {doi} BEGIN
              INSERT INTO {BANG} ({cot}) SELECT {_LUC}, {_AI}, 'sua', '{bang}', {theo('NEW', khoa)}, {theo('NEW', ho)},
              {theo('NEW', thua)}, {theo('NEW', dt)}, t, c, m FROM ({ds}) WHERE c IS NOT m; END''']
    if them_xoa:
        kq.append(f'''CREATE TEMP TRIGGER IF NOT EXISTS _kt_{bang}_them AFTER INSERT ON main."{bang}" BEGIN
                      INSERT INTO {BANG} ({cot}) VALUES ({_LUC}, {_AI}, 'them', '{bang}', {theo('NEW', khoa)}, {theo('NEW', ho)},
                      {theo('NEW', thua)}, {theo('NEW', dt)}, NULL, NULL, NULL); END''')
        kq.append(f'''CREATE TEMP TRIGGER IF NOT EXISTS _kt_{bang}_xoa BEFORE DELETE ON main."{bang}" BEGIN
                      INSERT INTO {BANG} ({cot}) VALUES ({_LUC}, {_AI}, 'xoa', '{bang}', {theo('OLD', khoa)}, {theo('OLD', ho)},
                      {theo('OLD', thua)}, {theo('OLD', dt)}, NULL, NULL, NULL); END''')
    return kq


def gan(con, nguoi: str | None = None) -> bool:
    """Bật ghi vết cho kết nối dự án đang mở (app.mo; file chỉ xem không gắn). False nếu file không có bảng nhật ký / chỉ đọc."""
    if not dam_bao_bang(con):
        return False
    dat_phien(con, nguoi)
    co = {r[0] for r in con.execute("SELECT name FROM main.sqlite_master WHERE type = 'table'")}
    for bang in THEO_DOI:
        if bang in co:
            cot = {r[1] for r in con.execute(f'PRAGMA main.table_info("{bang}")')}
            if all(t in cot for t in THEO_DOI[bang][5]):
                for cau in _trigger(bang):
                    con.execute(cau)
    gan_ky(con)                                 # 1.0.55: ký chuỗi băm từng dòng nhật ký
    ghi_neo(con)                                # 1.0.97: điểm neo ngoài file (chỉ ghi khi chuỗi còn khớp neo cũ)
    con.commit()                                # tạo bảng / trigger tạm mở giao dịch ngầm: chốt ngay (như hoan_tac)
    return True


# ---------------------------------------------------------------- so sánh phương án khi Lưu
def _chu(x) -> str | None:
    if x is None:
        return None
    from decimal import Decimal
    if isinstance(x, Decimal):
        from .tien import chuoi
        return chuoi(x)
    if isinstance(x, bool):
        return '1' if x else '0'
    return str(x)


TRUONG_DAT = ('dien_tich', 'loai_dat', 'vi_tri', 'gia_bang_gia', 'he_so_k', 'ty_le', 'ghi_chu')
TRUONG_KHOAN = ('ten', 'dvt', 'so_luong', 'don_gia', 'ty_le', 'quy_cach', 'ghi_chu', 'ma_tuong_duong', 'can_cu_gia')


def _ghep(cu: list, moi: list, khoa) -> tuple:
    """Ghép dòng cũ / mới theo khóa (dòng cùng khóa ghép theo thứ tự xuất hiện). Trả ([(cũ, mới)], [cũ còn lại], [mới còn lại])."""
    con_lai = {}
    for d in cu:
        con_lai.setdefault(khoa(d), []).append(d)
    cap, them = [], []
    for d in moi:
        ds = con_lai.get(khoa(d))
        if ds:
            cap.append((ds.pop(0), d))
        else:
            them.append(d)
    xoa = [d for ds in con_lai.values() for d in ds]
    return cap, xoa, them


def thay_doi_pa(pa_cu, pa_moi) -> list:
    """Các dòng thay đổi giữa hai phương án của một hộ: [(hanh_dong, bang, ma_thua, doi_tuong, truong, cu, moi)]."""
    from .nghiep_vu import MUC_KHOAN, so_muc
    kq = []
    ten_thua = {}

    def mo_ta_dat(d) -> str:
        return f'Mục 1 - thửa {ten_thua.get(d.ma_thua, d.ma_thua)} ({d.loai_dat})'

    def tom_tat_dat(d) -> str:
        return f'{_chu(d.dien_tich)} m² x {_chu(d.gia_bang_gia)} đ' + (f' x {_chu(d.ty_le)}' if d.ty_le is not None else '')
    cap, xoa, them = _ghep(pa_cu.dat, pa_moi.dat, lambda d: (d.ma_thua, d.loai_dat))
    for c, m in cap:
        for t in TRUONG_DAT:
            a, b = _chu(getattr(c, t, None)), _chu(getattr(m, t, None))
            if a != b:
                kq.append(('sua', 'ct_dat', m.ma_thua, mo_ta_dat(m), t, a, b))
    kq += [('xoa', 'ct_dat', d.ma_thua, mo_ta_dat(d), None, tom_tat_dat(d), None) for d in xoa]
    kq += [('them', 'ct_dat', d.ma_thua, mo_ta_dat(d), None, None, tom_tat_dat(d)) for d in them]
    for muc in MUC_KHOAN:
        def mo_ta(d) -> str:
            return f'Mục {so_muc(muc)} - {d.ten}'

        def tom_tat(d) -> str:
            return f'{_chu(d.so_luong)} {d.dvt or ""} x {_chu(d.don_gia)} đ' + (f' x {_chu(d.ty_le)}' if d.ty_le is not None else '')
        cap, xoa, them = _ghep(pa_cu.khoan[muc], pa_moi.khoan[muc], lambda d: (d.ma or '', d.ten if not d.ma else ''))
        for c, m in cap:
            for t in TRUONG_KHOAN:
                a, b = _chu(getattr(c, t, None)), _chu(getattr(m, t, None))
                if a != b:
                    kq.append(('sua', 'ct_khoan', None, mo_ta(m), t, a, b))
        kq += [('xoa', 'ct_khoan', None, mo_ta(d), None, tom_tat(d), None) for d in xoa]
        kq += [('them', 'ct_khoan', None, mo_ta(d), None, None, tom_tat(d)) for d in them]
    return kq


def ghi_thay_doi_pa(con, ma_ho: int, pa_cu, pa_moi, ten_thua: dict | None = None, thao_tac: str = 'Lưu phương án hộ') -> int:
    """Ghi các thay đổi phương án (trong giao dịch của nơi gọi). Không có bảng nhật ký (file cũ chỉ xem): bỏ qua. Trả số dòng ghi."""
    if not co_bang(con):
        return 0
    ds = thay_doi_pa(pa_cu, pa_moi)
    if not ds:
        return 0
    phien = None
    try:
        phien = con.execute('SELECT nguoi, may FROM temp._kt_phien WHERE id = 1').fetchone()
    except sqlite3.OperationalError:
        pass
    nguoi, may = (phien[0], phien[1]) if phien else (nguoi_dung(), csdl.ten_may())
    luc = datetime.now().isoformat(timespec='seconds')
    gan_ky(con)                                 # kết nối chưa gắn ghi vết (gan) vẫn ký dòng phương án
    if ten_thua:
        ds = [(h, b, mt, dt.replace(f'thửa {mt} (', f'thửa {ten_thua[mt]} (') if mt in ten_thua else dt, t, c, m)
              for h, b, mt, dt, t, c, m in ds]
    con.executemany(f'''INSERT INTO {BANG} (luc, nguoi, may, hanh_dong, bang, khoa, ma_ho, ma_thua, doi_tuong, truong, cu, moi,
                       thao_tac) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)''',
                    [(luc, nguoi, may, h, b, str(ma_ho), ma_ho, mt, dt, t, c, m, thao_tac) for h, b, mt, dt, t, c, m in ds])
    return len(ds)


# ---------------------------------------------------------------- đọc, xuất
def doc(con, ma_ho: int | None = None, tu_khoa: str = '', tu_ngay: str = '', den_ngay: str = '', gioi_han: int = 20000) -> list:
    """Dòng nhật ký mới nhất trước (dict). tu_ngay / den_ngay: 'YYYY-MM-DD'. tu_khoa: khớp không dấu đối tượng / người / giá trị."""
    if not co_bang(con):
        return []
    dk, ts = [], []
    if ma_ho is not None:
        dk.append('ma_ho = ?')
        ts.append(ma_ho)
    if tu_ngay:
        dk.append('luc >= ?')
        ts.append(tu_ngay)
    if den_ngay:
        dk.append('luc < ?')
        ts.append(den_ngay + 'T99')
    sql = f'SELECT * FROM {BANG}' + (' WHERE ' + ' AND '.join(dk) if dk else '') + ' ORDER BY id DESC'
    ds = [dict(r) for r in con.execute(sql, ts)]
    if tu_khoa.strip():
        from .lap_pa import bo_dau
        k = bo_dau(tu_khoa).split()
        ds = [d for d in ds if all(x in bo_dau(' '.join(str(d[c] or '') for c in ('doi_tuong', 'nguoi', 'may', 'truong', 'cu', 'moi',
                                                                                     'thao_tac'))) for x in k)]
    return ds[:gioi_han]


def nhan(d: dict) -> str:
    return NHAN_TRUONG.get(d.get('truong') or '', d.get('truong') or '')


def xuat_excel(ds: list, file_ra, ten_du_an: str = '') -> None:
    """Xuất nhật ký kiểm toán ra Excel (A4 ngang) để nộp đoàn thanh tra / kiểm toán."""
    import openpyxl
    from openpyxl.styles import Alignment, Border, Font, Side
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = 'NhatKyKiemToan'
    ws['A1'] = 'NHẬT KÝ THAY ĐỔI SỐ LIỆU (KIỂM TOÁN)'
    ws['A1'].font = Font(bold=True, size=13)
    ws['A2'] = f'Dự án: {ten_du_an}' if ten_du_an else ''
    ws['A3'] = f'Xuất lúc {datetime.now():%d/%m/%Y %H:%M} - {len(ds)} dòng'
    tieu_de = ['STT', 'Thời gian', 'Người sửa', 'Máy', 'Thao tác', 'Mã hộ', 'Đối tượng', 'Trường', 'Giá trị cũ', 'Giá trị mới', 'Ghi chú']
    vien = Border(*(Side(style='thin'),) * 4)
    for c, t in enumerate(tieu_de, start=1):
        o = ws.cell(5, c, t)
        o.font = Font(bold=True)
        o.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
        o.border = vien
    for i, d in enumerate(ds, start=1):
        luc = str(d['luc'] or '')
        hien = f'{luc[8:10]}/{luc[5:7]}/{luc[:4]} {luc[11:19]}' if len(luc) >= 19 else luc
        dong = [i, hien, d['nguoi'], d['may'], HANH_DONG.get(d['hanh_dong'], d['hanh_dong']), d['ma_ho'], d['doi_tuong'], nhan(d),
                d['cu'], d['moi'], d['thao_tac']]
        for c, v in enumerate(dong, start=1):
            o = ws.cell(5 + i, c, v)
            o.border = vien
            o.alignment = Alignment(vertical='center', wrap_text=True)
    for c, w in enumerate((6, 18, 16, 14, 9, 8, 40, 18, 22, 22, 22), start=1):
        ws.column_dimensions[openpyxl.utils.get_column_letter(c)].width = w
    ws.print_title_rows = '5:5'
    ws.page_setup.orientation = 'landscape'
    ws.page_setup.paperSize = 9
    ws.sheet_properties.pageSetUpPr.fitToPage = True
    ws.page_setup.fitToWidth, ws.page_setup.fitToHeight = 1, 0
    _an_toan.luu_xlsx(wb, file_ra)

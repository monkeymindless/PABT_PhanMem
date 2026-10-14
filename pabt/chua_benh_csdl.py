"""Bác sĩ kỹ thuật file dự án .pabt và gói chẩn đoán gửi tác giả (0.9.87).

- kiem_tra_tep_pabt: mở CHỈ ĐỌC, integrity_check / foreign_key_check, phiên bản CSDL, số hộ / thửa, khóa nhiều máy.
- sua_tep_pabt: sao lưu trước, gỡ khóa .pabt.khoa ĐÃ HẾT HẠN (khóa còn hiệu lực = máy khác đang sửa: không gỡ), REINDEX + VACUUM;
  trang CSDL hỏng thì cứu dữ liệu bằng iterdump sang file tạm rồi os.replace (file gốc còn ở bản sao lưu).
  File phải ĐÓNG ở phần mềm trước khi sửa (nơi gọi đóng dự án - man_hinh_chan_doan).
- an_danh_du_an / dong_goi_chan_doan: bản sao dự án đã xóa thông tin cá nhân (họ tên, CCCD, điện thoại, địa chỉ, nguồn gốc ghi tên
  người, ý kiến dân, nhật ký) nhưng GIỮ số liệu (diện tích, loại đất, đơn giá, công thức, tỷ lệ) để tái hiện lỗi.
Không Qt (chạy được trong kiểm thử / tu-kiem)."""
from __future__ import annotations
import json
import os
import platform
import shutil
import sqlite3
import sys
import tempfile
import time
import zipfile
from datetime import datetime
from pathlib import Path

DUOI_KHOA = '.khoa'


def _con_ro(p: Path):
    return sqlite3.connect(p.resolve().as_uri() + '?mode=ro', uri=True, timeout=5)


def _co_bang(con, ten: str) -> bool:
    return con.execute("SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?", (ten,)).fetchone() is not None


def khoa_cua(file_pabt) -> dict | None:
    """Khóa nhiều máy (khoa.KhoaFile) của file: {'con_hieu_luc': bool, 'mo_ta': str, …} hoặc None nếu không có."""
    from . import khoa
    k = khoa.KhoaFile(file_pabt)
    du = k.doc()
    if du is None:
        return None if not k.p.exists() else dict(con_hieu_luc=False, mo_ta='file khóa hỏng', file=str(k.p))
    con = time.time() - float(du.get('cap_nhat', 0) or 0) <= khoa.HET_HAN
    return dict(du, con_hieu_luc=con, mo_ta=khoa.mo_ta(du), file=str(k.p))


# ---------------------------------------------------------------- kiểm tra
def kiem_tra_tep_pabt(file_pabt) -> dict:
    """{'ton_tai', 'hop_le', 'phien_ban', 'so_ho', 'so_thua', 'loi_toan_ven' [..], 'loi_khoa_ngoai' [..], 'khoa' (dict|None),
    'thong_bao'} - không ghi gì vào file."""
    from . import csdl
    p = Path(file_pabt)
    kq = dict(duong_dan=str(p), ton_tai=p.is_file(), hop_le=False, phien_ban=0, so_ho=0, so_thua=0, loi_toan_ven=[],
              loi_khoa_ngoai=[], khoa=None, thong_bao='')
    if not p.is_file():
        kq['thong_bao'] = 'Không tìm thấy file dự án.'
        return kq
    kq['khoa'] = khoa_cua(p)
    try:
        con = _con_ro(p)
        try:
            kq['phien_ban'] = con.execute('PRAGMA user_version').fetchone()[0]
            tv = [r[0] for r in con.execute('PRAGMA integrity_check')]
            if tv != ['ok']:
                kq['loi_toan_ven'] = tv[:50]
            kq['loi_khoa_ngoai'] = [f'Bảng {r[0]} dòng {r[1]} trỏ tới {r[2]} không còn' for r in
                                    con.execute('PRAGMA foreign_key_check').fetchall()[:50]]
            if _co_bang(con, 'ho'):
                kq['so_ho'] = con.execute('SELECT COUNT(*) FROM ho').fetchone()[0]
            if _co_bang(con, 'thua'):
                kq['so_thua'] = con.execute('SELECT COUNT(*) FROM thua').fetchone()[0]
        finally:
            con.close()
    except sqlite3.DatabaseError as e:
        kq['loi_toan_ven'] = [f'Không đọc được cấu trúc SQLite: {e}']
    kq['hop_le'] = not kq['loi_toan_ven'] and not kq['loi_khoa_ngoai']
    moi_hon = kq['phien_ban'] > csdl.PHIEN_BAN_CSDL
    if kq['hop_le']:
        kq['thong_bao'] = f'File tốt: CSDL v{kq["phien_ban"]}, {kq["so_ho"]} hộ, {kq["so_thua"]} thửa.'
        if moi_hon:
            kq['thong_bao'] += ' File tạo bằng phiên bản phần mềm mới hơn - hãy cập nhật phần mềm.'
    else:
        kq['thong_bao'] = (f'Phát hiện {len(kq["loi_toan_ven"])} lỗi toàn vẹn, {len(kq["loi_khoa_ngoai"])} lỗi liên kết '
                           f'(dòng trỏ tới hộ / thửa đã xóa).')
    k = kq['khoa']
    if k and k['con_hieu_luc']:
        kq['thong_bao'] += f' Đang được mở để sửa ở {k["mo_ta"]}.'
    elif k:
        kq['thong_bao'] += ' Còn file khóa cũ (máy kia tắt đột ngột) - "Sửa file" sẽ gỡ.'
    return kq


# ---------------------------------------------------------------- sửa
class LoiSuaTep(RuntimeError):
    """Không sửa được (thông báo tiếng Việt)."""


def sao_luu(p: Path, thu_muc=None) -> Path:
    tm = Path(thu_muc) if thu_muc else p.parent / 'SaoLuu_SuaLoi'
    tm.mkdir(parents=True, exist_ok=True)
    dich = tm / f'{p.stem}_truoc_sua_{datetime.now().strftime("%Y%m%d_%H%M%S")}{p.suffix}'
    shutil.copy2(p, dich)
    return dich


def sua_tep_pabt(file_pabt, thu_muc_sao_luu=None) -> dict:
    """Sao lưu rồi sửa file (đã ĐÓNG ở phần mềm). Trả {'thanh_cong', 'ban_sao_luu', 'hanh_dong' [..], 'kiem_tra_sau'}.
    Khóa còn hiệu lực (máy khác đang sửa) -> LoiSuaTep. Lỗi liên kết (dòng phương án trỏ tới hộ / thửa đã xóa) chỉ báo, không
    tự xóa dòng (người dùng xem rồi quyết định); lỗi toàn vẹn trang -> cứu dữ liệu sang file mới."""
    from . import csdl
    p = Path(file_pabt).resolve()
    if not p.is_file():
        raise LoiSuaTep(f'Không tìm thấy file: {p}')
    k = khoa_cua(p)
    if k and k['con_hieu_luc']:
        raise LoiSuaTep(f'File đang được mở để sửa ở {k["mo_ta"]}. Đóng phần mềm ở máy đó rồi sửa lại.')
    truoc = kiem_tra_tep_pabt(p)
    if truoc['phien_ban'] > csdl.PHIEN_BAN_CSDL:
        raise LoiSuaTep('File tạo bằng phiên bản phần mềm mới hơn: hãy cập nhật phần mềm, không sửa bằng bản này.')
    bs = sao_luu(p, thu_muc_sao_luu)
    hanh_dong = [f'Đã sao lưu bản gốc: {bs}']
    if k:
        try:
            Path(k['file']).unlink()
            hanh_dong.append('Đã gỡ file khóa cũ (.pabt.khoa) của lần mở trước bị tắt đột ngột.')
        except OSError as e:
            hanh_dong.append(f'Không gỡ được file khóa cũ: {e}')
    trang_hong = [x for x in truoc['loi_toan_ven']]
    if not trang_hong:
        con = sqlite3.connect(str(p), timeout=10)
        try:
            con.execute('REINDEX')
            con.commit()
            con.execute('VACUUM')
        finally:
            con.close()
        hanh_dong.append('Đã dựng lại chỉ mục (REINDEX) và nén gọn file (VACUUM).')
    else:
        hong = _cuu_du_lieu(p)
        hanh_dong.append('Trang dữ liệu hỏng: đã chép mọi dòng đọc được sang file mới (bản cũ ở thư mục sao lưu).' +
                         (f' Bảng có trang hỏng (có thể mất một số dòng - kiểm tra lại): {", ".join(hong)}.' if hong else ''))
    if truoc['loi_khoa_ngoai']:
        hanh_dong.append(f'Còn {len(truoc["loi_khoa_ngoai"])} dòng trỏ tới hộ / thửa không còn - kiểm tra trong phần mềm '
                         '(Kiểm tra lỗi), không tự xóa.')
    sau = kiem_tra_tep_pabt(p)
    try:                                                # mở bằng phần mềm một lần: nâng cấp lược đồ, trigger khóa danh mục
        csdl.mo(p).close()
    except (sqlite3.DatabaseError, RuntimeError) as e:
        hanh_dong.append(f'Mở lại bằng phần mềm báo lỗi: {e}')
    return dict(thanh_cong=not sau['loi_toan_ven'], ban_sao_luu=str(bs), hanh_dong=hanh_dong, kiem_tra_sau=sau)


def _doc_bang(cu, ten: str):
    """Các dòng đọc được của bảng: đọc xuôi theo rowid tới trang hỏng, rồi đọc ngược từ cuối để lấy phần sau trang hỏng."""
    dong, loi = {}, False
    try:
        for r in cu.execute(f'SELECT rowid, * FROM "{ten}" ORDER BY rowid'):
            dong[r[0]] = r[1:]
    except sqlite3.DatabaseError:
        loi = True
        try:
            for r in cu.execute(f'SELECT rowid, * FROM "{ten}" ORDER BY rowid DESC'):
                if r[0] in dong:
                    break
                dong[r[0]] = r[1:]
        except sqlite3.DatabaseError:
            pass
    return [dong[k] for k in sorted(dong)], loi


def _cuu_du_lieu(p: Path) -> list:
    """Chép từng bảng sang file tạm: lược đồ (sqlite_master) trước, dòng đọc được của từng bảng (trang hỏng chỉ mất phần trong
    trang đó, bảng khác nguyên vẹn - iterdump dừng hẳn ở lỗi đầu tiên), rồi chỉ mục / trigger. fsync + os.replace. Trả
    [bảng có trang hỏng]. Lỗi -> file gốc giữ nguyên."""
    tam = p.with_name(p.name + '.cuu_tam')
    if tam.exists():
        tam.unlink()
    cu = sqlite3.connect(str(p))
    moi = sqlite3.connect(str(tam))
    hong = []
    try:
        try:
            ver = cu.execute('PRAGMA user_version').fetchone()[0]
        except sqlite3.DatabaseError:
            ver = 0
        lenh = cu.execute("SELECT type, name, sql FROM sqlite_master WHERE sql IS NOT NULL AND name NOT LIKE 'sqlite_%'").fetchall()
        moi.execute('PRAGMA foreign_keys = OFF')
        for loai, ten, sql in lenh:
            if loai == 'table':
                moi.execute(sql)
        for loai, ten, sql in lenh:
            if loai != 'table':
                continue
            dong, loi = _doc_bang(cu, ten)
            if loi:
                hong.append(ten)
            if dong:
                dau = ', '.join('?' * len(dong[0]))
                moi.executemany(f'INSERT OR IGNORE INTO "{ten}" VALUES ({dau})', dong)
        for loai, ten, sql in lenh:
            if loai in ('index', 'trigger', 'view'):
                try:
                    moi.execute(sql)
                except sqlite3.Error:                   # chỉ mục UNIQUE gặp dòng trùng do trang hỏng: bỏ chỉ mục đó
                    pass
        moi.execute(f'PRAGMA user_version = {int(ver)}')
        moi.commit()
    except Exception:
        moi.close()
        cu.close()
        try:
            tam.unlink()
        except OSError:
            pass
        raise
    cu.close()
    moi.close()
    with open(tam, 'rb+') as f:
        os.fsync(f.fileno())
    os.replace(tam, p)
    return hong


# ---------------------------------------------------------------- ẩn danh + gói chẩn đoán
# cột chữ có thông tin cá nhân -> giá trị thay ('' = để trống); {i} = số thứ tự hộ
_AN_DANH_HO = {'ho_ten': 'Hộ kiểm thử {i:04d}', 'so_cccd': '', 'ngay_cap': '', 'noi_cap': '', 'dia_chi': 'Ấp kiểm thử {i}',
               'dien_thoai': '', 'ghi_chu': '', 'theo_doi': '', 'ly_do_ban_giao': '', 'bien_ban_ban_giao': '',
               'ghi_chu_phap_ly': '', 'qd_file': '', 'phap_ly': None, 'tranh_chap': None}
_XOA_CHU = {'thua': ('nguon_goc',), 'ct_dat': ('ghi_chu',), 'ct_khoan': ('ghi_chu',),
            'y_kien_du_thao': ('noi_dung', 'huong_xu_ly', 'ket_qua_doi_thoai'),
            'doi_thoai_ho': ('thanh_phan', 'dien_bien', 'ket_luan', 'dia_diem'),
            'qd_ho': ('chung_tu', 'ly_do_chua_nhan', 'ghi_chu'), 'quyet_dinh': ('file',), 'dot_trinh': ('thu_muc',),
            'nhat_ky_van_dong': ('thanh_phan', 'noi_dung', 'ghi_chu', 'bien_ban')}
_XOA_BANG = ('tho_nhap', 'nhat_ky', 'audit_logs', 'anh_hien_trang')
_XOA_CAI_DAT = ('THU_MUC_HO_SO', 'FILE_KHAI_TOAN')


def _chu_thay(chu, nhan: str) -> str:
    """Chữ cùng độ dài, cùng số dòng (tái hiện lỗi ngắt dòng / chiều cao ô) nhưng không còn nội dung."""
    if not chu:
        return chu
    mau = nhan + ' '
    return '\n'.join((mau * (len(d) // len(mau) + 1))[:len(d)].rstrip() for d in str(chu).split('\n'))


def an_danh_du_an(file_goc, file_dich) -> dict:
    """Chép file dự án sang file_dich rồi xóa thông tin cá nhân (xem đầu module). Trả {'so_ho', 'bang_xoa'}."""
    goc, dich = Path(file_goc), Path(file_dich)
    nguon = _con_ro(goc)
    ra = sqlite3.connect(str(dich))
    try:
        nguon.backup(ra)                                # bản sao nhất quán kể cả khi file đang mở ở phần mềm
    finally:
        nguon.close()
    try:
        for (t,) in ra.execute("SELECT name FROM sqlite_master WHERE type = 'trigger'").fetchall():
            ra.execute(f'DROP TRIGGER IF EXISTS "{t}"')  # khóa danh mục, chặn sửa nhật ký kiểm toán: chỉ trên bản sao
        bang = {r[0] for r in ra.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
        so_ho = 0
        if 'ho' in bang:
            cot = {r[1] for r in ra.execute('PRAGMA table_info(ho)')}
            for i, (ma, phap_ly, tranh_chap) in enumerate(
                    ra.execute('SELECT ma_ho, phap_ly, tranh_chap FROM ho ORDER BY thu_tu, ma_ho').fetchall(), 1):
                gt = {}
                for c, v in _AN_DANH_HO.items():
                    if c not in cot:
                        continue
                    gt[c] = _chu_thay(phap_ly if c == 'phap_ly' else tranh_chap, 'Ghi chú') if v is None else v.format(i=i)
                ra.execute(f'UPDATE ho SET {", ".join(c + " = ?" for c in gt)} WHERE ma_ho = ?', (*gt.values(), ma))
                so_ho += 1
        for b, cac_cot in _XOA_CHU.items():
            if b not in bang:
                continue
            cot = {r[1] for r in ra.execute(f'PRAGMA table_info({b})')}
            for c in cac_cot:
                if c not in cot:
                    continue
                for rid, v in ra.execute(f'SELECT rowid, {c} FROM {b} WHERE {c} IS NOT NULL AND {c} <> \'\'').fetchall():
                    ra.execute(f'UPDATE {b} SET {c} = ? WHERE rowid = ?',
                               (_chu_thay(v, 'Nguồn gốc' if c == 'nguon_goc' else 'Nội dung'), rid))
        if 'du_an' in bang:                             # tên người lập / kiểm tra / ký bản in
            cot = {r[1] for r in ra.execute('PRAGMA table_info(du_an)')}
            for c in ('nguoi_lap', 'nguoi_kiem_tra', 'nguoi_ky'):
                if c in cot:
                    ra.execute(f"UPDATE du_an SET {c} = ''")
        xoa = []
        for b in _XOA_BANG:
            if b in bang:
                ra.execute(f'DELETE FROM {b}')
                xoa.append(b)
        if 'cai_dat' in bang:
            ra.executemany('DELETE FROM cai_dat WHERE ma = ?', [(x,) for x in _XOA_CAI_DAT])
        ra.commit()
        ra.execute('VACUUM')
    finally:
        ra.close()
    return dict(so_ho=so_ho, bang_xoa=xoa)


def thong_tin_may() -> dict:
    """Hệ điều hành, Python, Qt, màn hình / DPI (khi đang có QApplication) - không có tên máy / tên người dùng."""
    from . import __version__
    tt = dict(phan_mem=__version__, luc=datetime.now().isoformat(timespec='seconds'), he_dieu_hanh=platform.platform(),
              kien_truc=platform.machine(), python=platform.python_version(), dong_goi=bool(getattr(sys, 'frozen', False)))
    try:
        from PySide6 import QtCore
        tt['qt'] = QtCore.qVersion()
        from PySide6.QtWidgets import QApplication
        app = QApplication.instance()
        if app is not None:
            tt['nen_tang'] = app.platformName()
            tt['man_hinh'] = [dict(ten=s.name(), rong=s.size().width(), cao=s.size().height(),
                                   ty_le=round(s.devicePixelRatio(), 3), dpi=round(s.logicalDotsPerInch(), 1))
                              for s in app.screens()]
    except Exception as e:                              # noqa: BLE001 - chỉ là thông tin phụ
        tt['qt'] = f'không đọc được: {e}'
    return tt


def kiem_tra_moi_truong(thu_muc_may=None) -> list:
    """[{ma, ten, muc ('dat' / 'canh_bao' / 'loi'), chi_tiet, cach_xu_ly}] - thư mục máy, dung lượng đĩa, Excel, Tesseract, HTTPS."""
    from . import dia_phuong, in_an
    kq = []

    def them(ma, ten, muc, chi_tiet, cach=''):
        kq.append(dict(ma=ma, ten=ten, muc=muc, chi_tiet=chi_tiet, cach_xu_ly=cach))
    tm = Path(thu_muc_may) if thu_muc_may else dia_phuong.thu_muc_may()
    try:
        tm.mkdir(parents=True, exist_ok=True)
        thu = tm / f'.thu_ghi_{os.getpid()}.tmp'
        thu.write_text('ok', encoding='utf-8')
        thu.unlink()
        them('thu_muc_may', 'Thư mục dữ liệu của máy', 'dat', f'Ghi được: {tm}')
    except OSError as e:
        them('thu_muc_may', 'Thư mục dữ liệu của máy', 'loi', f'Không ghi được {tm}: {e}',
             'Kiểm tra quyền thư mục %APPDATA%\\PABT hoặc phần mềm diệt virus.')
    try:
        trong = shutil.disk_usage(str(tm if tm.exists() else Path.home())).free // (1024 * 1024)
        muc = 'dat' if trong >= 500 else 'canh_bao' if trong >= 100 else 'loi'
        them('o_dia', 'Dung lượng ổ đĩa trống', muc, f'Còn {trong:,} MB'.replace(',', '.'),
             '' if muc == 'dat' else 'Dọn bớt ổ đĩa (nên còn ít nhất 500 MB).')
    except OSError as e:
        them('o_dia', 'Dung lượng ổ đĩa trống', 'canh_bao', str(e))
    co = in_an.co_excel()
    them('excel', 'Microsoft Excel (xuất PDF, in)', 'dat' if co else 'canh_bao',
         'Có Microsoft Excel' if co else 'Không thấy Microsoft Excel',
         '' if co else 'Xem trước A4 dùng bộ dựng PDF dự phòng (bản gần đúng); in / xuất PDF chính thức cần Excel.')
    try:
        from . import ocr
        t = ocr.tim_tesseract()
    except Exception:                                   # noqa: BLE001
        t = None
    them('tesseract', 'Đọc văn bản scan (Tesseract OCR)', 'dat' if t else 'canh_bao',
         f'Có: {t}' if t else 'Chưa cài Tesseract', '' if t else 'Chỉ cần khi đọc quyết định / giấy tờ là bản scan, ảnh chụp.')
    try:
        import ssl
        n = len(ssl.create_default_context().get_ca_certs())
        them('https', 'Chứng chỉ HTTPS (cập nhật từ web)', 'dat' if n else 'canh_bao', f'{n} chứng chỉ gốc trong kho của máy')
    except Exception as e:                              # noqa: BLE001
        them('https', 'Chứng chỉ HTTPS (cập nhật từ web)', 'canh_bao', str(e))
    return kq


def dong_goi_chan_doan(file_zip, file_pabt=None, thu_muc_may=None, loi_text: str = '') -> Path:
    """Gói .zip gửi tác giả: thong_tin_may.json (máy, màn hình, kiểm tra môi trường), loi_vua_gap.txt, loi.log, pabt_profile.json,
    du_an_an_danh.pabt (an_danh_du_an). Ghi file tạm rồi os.replace."""
    from . import dia_phuong
    tm = Path(thu_muc_may) if thu_muc_may else dia_phuong.thu_muc_may()
    ra = Path(file_zip)
    ra.parent.mkdir(parents=True, exist_ok=True)
    tt = thong_tin_may()
    tt['kiem_tra_moi_truong'] = kiem_tra_moi_truong(tm)
    if file_pabt and Path(file_pabt).is_file():
        tt['file_du_an'] = kiem_tra_tep_pabt(file_pabt)
        tt['file_du_an'].pop('duong_dan', None)
        tt['file_du_an'].pop('khoa', None)
    tam = ra.with_name(ra.name + '.tmp')
    with tempfile.TemporaryDirectory() as td:
        with zipfile.ZipFile(tam, 'w', zipfile.ZIP_DEFLATED) as z:
            z.writestr('thong_tin_may.json', json.dumps(tt, ensure_ascii=False, indent=2))
            if loi_text:
                z.writestr('loi_vua_gap.txt', loi_text)
            for ten in ('loi.log', dia_phuong.TEN_FILE):
                f = tm / ten
                if f.is_file():
                    z.write(f, ten)
            if file_pabt and Path(file_pabt).is_file():
                ad = Path(td) / 'du_an_an_danh.pabt'
                an_danh_du_an(file_pabt, ad)
                z.write(ad, ad.name)
    os.replace(tam, ra)
    return ra

"""Bộ đơn giá tích hợp: danh mục đơn giá, chính sách hỗ trợ, tham số, biểu thưởng, văn bản căn cứ của UBND
tỉnh (nay là thành phố) Đồng Nai, đóng gói sẵn trong phần mềm (pabt/bo_don_gia.sqlite).

- Dự án mới tự lấy bộ đơn giá này; danh mục trong dự án bị khóa (csdl._dam_bao_khoa).
- Cập nhật: từ file PABT Excel chuẩn (.xlsm) hoặc gói bộ đơn giá (.sqlite), hoặc tải qua Internet theo một
  "địa chỉ cập nhật" (file JSON: phien_ban, tai_ve, sha256, ghi_chu) do đơn vị quản lý. Bộ mới lưu ở %APPDATA%\\PABT.
- Dự án đã lập KHÔNG tự đổi đơn giá: người lập chọn "Áp bộ đơn giá vào dự án" khi cần.
"""
from __future__ import annotations
import hashlib
import json
import os
import shutil
import tempfile
import urllib.request
from datetime import datetime
from pathlib import Path

from . import an_toan, csdl, nhap_excel
from .lap_pa import LoiNhap

TEN_FILE = 'bo_don_gia.sqlite'
TEN_BO = 'BỘ ĐƠN GIÁ BỒI THƯỜNG, HỖ TRỢ, TÁI ĐỊNH CƯ - ĐỒNG NAI'
# bộ đơn giá không chứa giá đất từng dự án: giá đất nhập ở bước "Bảng giá đất" khi lập dự án
BANG_BO = tuple(b for b in csdl.DANH_MUC if b != 'gia_dat')
# phân loại dòng vật nuôi trong dm_taisan (nhóm 3 như cây trồng): bộ tích hợp mã VN.. (QĐ 31/2025/QĐ-UBND), mục cập nhật từ văn
# bản vật nuôi (nhap_don_gia.ap_dung); màn hình Bộ đơn giá có thẻ "Vật nuôi" riêng theo phân loại này
PHAN_LOAI_VAT_NUOI = '3. Bồi thường thiệt hại về vật nuôi'


def file_goc() -> Path:
    """Bộ đơn giá đóng gói kèm phần mềm."""
    from . import tai_nguyen
    return tai_nguyen(TEN_FILE)


def file_cap_nhat() -> Path:
    """Bộ đơn giá đã cập nhật trên máy này (biến môi trường PABT_THU_MUC_MAY đổi thư mục, dùng khi kiểm thử)."""
    goc = os.environ.get('PABT_THU_MUC_MAY') or Path(os.environ.get('APPDATA') or Path.home()) / 'PABT'
    return Path(goc) / TEN_FILE


def thong_tin(p=None) -> dict:
    """Phiên bản, nguồn, số mục từng danh mục, văn bản căn cứ của một bộ đơn giá."""
    p = Path(p) if p else file_dang_dung()
    con = csdl.mo(p, chi_doc=True)
    try:
        da = con.execute('SELECT * FROM du_an WHERE id = 1').fetchone()
        dem = {b: con.execute(f'SELECT COUNT(*) FROM {b}').fetchone()[0] for b in BANG_BO}
        so_ho = con.execute('SELECT COUNT(*) FROM ho').fetchone()[0]
        vb = [dict(r) for r in con.execute('SELECT so_hieu, co_quan, noi_dung, trang_thai FROM van_ban ORDER BY id')]
    finally:
        con.close()
    return dict(file=str(p), ten=da['ten'], phien_ban=da['phien_ban_gia'], nguon=da['nguon_nhap'], ngay=da['ngay_nhap'],
                ghi_chu=da['can_cu_dinh_kem'], dem=dem, so_ho=so_ho, van_ban=vb)


def kiem_tra_bo(p) -> dict:
    """Bộ đơn giá hợp lệ: đúng cấu trúc, có danh mục, KHÔNG chứa hồ sơ hộ. Sai thì báo LoiNhap."""
    try:
        tt = thong_tin(p)
    except Exception as e:
        raise LoiNhap(f'File không phải bộ đơn giá PABT: {e}') from None
    if tt['so_ho']:
        raise LoiNhap('File có hồ sơ hộ, không phải bộ đơn giá (bộ đơn giá chỉ gồm danh mục, tham số).')
    if not tt['dem']['dm_taisan'] or not tt['dem']['dm_hotro'] or not tt['phien_ban']:
        raise LoiNhap('Bộ đơn giá thiếu danh mục tài sản / hỗ trợ hoặc chưa ghi phiên bản.')
    return tt


_DA_NANG_CAP = set()


def _nang_cap_ban_may(p: Path) -> None:
    """Bản bộ đơn giá trên máy (đã cập nhật / sửa) tạo bằng phiên bản cũ: mở GHI một lần để nâng cấp lược đồ - CSDL v14 đổi mã
    tài sản sang TS / CT / VN / CS (ma_tai_san). Không thì mã cũ (HT01…) trong bộ không khớp quy tắc tính của phần mềm."""
    k = str(p)
    if k in _DA_NANG_CAP:
        return
    _DA_NANG_CAP.add(k)
    try:
        import sqlite3
        c = sqlite3.connect(k)
        try:
            ver = c.execute('PRAGMA user_version').fetchone()[0]
        finally:
            c.close()
        if 0 < ver < csdl.PHIEN_BAN_CSDL:
            csdl.mo(p).close()
        # 26/10/2026: bản máy (cập nhật / sửa trước bản này) chưa có tên khác của cây lâm nghiệp (Phụ lục VI QĐ 48/2025) - thêm một lần
        from .chuan_ten_cay import chuan_ten
        from .ten_cay_lam_nghiep import ap_ten_khac, them_ten_khac
        c = sqlite3.connect(k)
        try:
            can = any(them_ten_khac(chuan_ten(r[0])) != r[0] for r in c.execute('SELECT ten FROM dm_taisan WHERE nhom = 3'))
        finally:
            c.close()
        if can:
            c = csdl.mo(p)
            try:
                ap_ten_khac(c)
            finally:
                c.close()
    except Exception:                                   # noqa: BLE001 - file khóa / hỏng: kiem_tra_bo xử lý tiếp như cũ
        pass


def file_dang_dung() -> Path:
    """Bộ đơn giá mới nhất: bản đã cập nhật (nếu hợp lệ và mới hơn) hoặc bản đóng gói."""
    goc, moi = file_goc(), file_cap_nhat()
    if moi.exists():
        _nang_cap_ban_may(moi)
        try:
            if kiem_tra_bo(moi)['phien_ban'] >= kiem_tra_bo(goc)['phien_ban']:
                return moi
        except LoiNhap:
            pass
    return goc


def ap_vao_du_an(con) -> dict:
    """Thay danh mục, tham số, biểu thưởng, văn bản của dự án bằng bộ đơn giá đang dùng (giữ giá đất, hồ sơ và quy ước /
    đơn giá thẩm định riêng của dự án)."""
    p = file_dang_dung()
    tt = thong_tin(p)
    from . import don_gia_rieng
    rieng = don_gia_rieng.doc_rieng(con)          # quy ước, đơn giá thẩm định riêng của dự án: giữ lại
    csdl.chep_danh_muc(con, p, don_vi=False, bang=BANG_BO)
    with con, csdl.mo_khoa_danh_muc(con):
        don_gia_rieng.tra_rieng(con, rieng)
    with con:
        con.execute('UPDATE du_an SET phien_ban_gia = ? WHERE id = 1', (tt['phien_ban'],))
        csdl.ghi_nhat_ky(con, 'Áp bộ đơn giá', f'Phiên bản {tt["phien_ban"]} ({tt["nguon"]})')
    return tt


def bo_sung_vat_nuoi(con) -> int:
    """Dự án lập trước khi bộ đơn giá có vật nuôi (QĐ 31/2025/QĐ-UBND, bộ 2026.10.09): thêm các dòng vật nuôi của bộ đơn giá
    đang dùng mà danh mục dự án chưa có (theo mã) - không đổi dòng nào khác (khác "Áp bộ đơn giá": thay cả danh mục).
    Trả số dòng đã thêm."""
    from .nghiep_vu import la_vat_nuoi
    bo = csdl.mo(file_dang_dung(), chi_doc=True)
    try:
        ds = [dict(r) for r in bo.execute('SELECT * FROM dm_taisan WHERE nhom = 3 ORDER BY rowid') if la_vat_nuoi(r['phan_loai'])]
    finally:
        bo.close()
    cot = {r[1] for r in con.execute('PRAGMA table_info(dm_taisan)')}
    co = {r[0] for r in con.execute('SELECT ma FROM dm_taisan')}
    moi = [r for r in ds if r['ma'] not in co]
    if not moi:
        return 0
    with con, csdl.mo_khoa_danh_muc(con):
        for r in moi:
            k = [c for c in r if c in cot]
            con.execute(f'INSERT INTO dm_taisan ({", ".join(k)}) VALUES ({", ".join("?" * len(k))})', [r[c] for c in k])
        csdl.ghi_nhat_ky(con, 'Bổ sung vật nuôi', f'{len(moi)} mục từ bộ đơn giá {file_dang_dung().name}')
    return len(moi)


def viet_hoa_dau(s: str) -> str:
    """'cây xoài - Năm thứ 1' -> 'Cây xoài - Năm thứ 1' (chỉ chữ cái đầu tiên)."""
    s = ' '.join(str(s or '').split())
    return s[:1].upper() + s[1:] if s[:1].islower() else s


def chuan_ten_danh_muc(con) -> int:
    """Viết hoa chữ đầu tên tài sản, cây trồng trong danh mục (gọi bên trong `with con, csdl.mo_khoa_danh_muc(con)`)."""
    n = 0
    for r in con.execute('SELECT ma, ten FROM dm_taisan').fetchall():
        moi = viet_hoa_dau(r['ten'])
        if moi != r['ten']:
            con.execute('UPDATE dm_taisan SET ten = ? WHERE ma = ?', (moi, r['ma']))
            n += 1
    return n


def tao_bo_tu_excel(file_excel, file_ra, phien_ban: str = '', ghi_chu: str = '', theo_doi: list = ()) -> dict:
    """Đóng gói danh mục của một file PABT Excel chuẩn (.xlsm) thành bộ đơn giá (không lấy hồ sơ hộ, giá đất dự án).
    theo_doi: [(số hiệu, cơ quan, nội dung, trạng thái)] văn bản cần theo dõi thêm."""
    from .nhap_tho import la_file_pabt
    if not la_file_pabt(file_excel):
        raise LoiNhap('File không theo mẫu PABT Excel (cần các sheet DB_HO, DM_HOTRO, DG_NHANUOC, THAM_SO…).')
    file_ra = Path(file_ra)
    with tempfile.TemporaryDirectory() as td:
        tam = Path(td) / 'nguon.pabt'
        bc = nhap_excel.nhap(file_excel, tam)
        if bc.loi:
            raise LoiNhap('Không đọc được danh mục:\n' + '\n'.join(bc.loi))
        ra = Path(td) / TEN_FILE
        con = csdl.tao_moi(ra)
        try:
            csdl.chep_danh_muc(con, tam, don_vi=False, bang=BANG_BO)
            with con, csdl.mo_khoa_danh_muc(con):
                con.execute('DELETE FROM dm_xa')            # danh sách xã, phường của dự án nguồn: không đưa vào bộ
                chuan_ten_danh_muc(con)                     # 'cây xoài' -> 'Cây xoài'
                con.executemany('INSERT INTO van_ban (so_hieu, co_quan, noi_dung, trang_thai) VALUES (?,?,?,?)', list(theo_doi))
                con.execute('UPDATE du_an SET ten = ?, ten_day_du = ?, phien_ban_gia = ?, nguon_nhap = ?, ngay_nhap = ?, '
                            'can_cu_dinh_kem = ? WHERE id = 1',
                            (TEN_BO, TEN_BO, phien_ban or datetime.now().strftime('%Y.%m.%d'), Path(file_excel).name,
                             datetime.now().isoformat(timespec='seconds'), ghi_chu))
            con.execute('VACUUM')
        finally:
            con.close()
        kiem_tra_bo(ra)
        file_ra.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ra, file_ra)
    return thong_tin(file_ra)


def cai_bo(p) -> dict:
    """Cài một bộ đơn giá (đã kiểm tra) làm bộ đang dùng trên máy này."""
    tt = kiem_tra_bo(p)
    dich = file_cap_nhat()
    dich.parent.mkdir(parents=True, exist_ok=True)
    tam = dich.with_suffix('.tai')
    shutil.copyfile(p, tam)
    os.replace(tam, dich)
    return dict(tt, file=str(dich))


def sao_luu_bo(dich) -> Path:
    """Sao lưu bộ đơn giá đang dùng ra file (0.9.73): .sqlite = bản sao đầy đủ (nạp lại được bằng "Nạp từ file"), .xlsx = mỗi
    danh mục một sheet (xem / gửi đi). Không đổi bộ đang dùng."""
    import sqlite3
    dich = Path(dich)
    nguon = file_dang_dung()
    dich.parent.mkdir(parents=True, exist_ok=True)
    if dich.suffix.lower() in ('.xlsx', '.xlsm'):
        import openpyxl
        con = csdl.mo(nguon, chi_doc=True)
        try:
            wb = openpyxl.Workbook()
            wb.remove(wb.active)
            for b in BANG_BO:
                cur = con.execute(f'SELECT * FROM {b}')
                ws = wb.create_sheet(b[:31])
                ws.append([c[0] for c in cur.description])
                for r in cur:
                    ws.append(list(r))
            tam = dich.with_name(dich.name + '.tmp')
            an_toan.luu_xlsx(wb, tam)
            os.replace(tam, dich)
        finally:
            con.close()
        return dich
    if dich.suffix.lower() != '.sqlite':
        dich = dich.with_suffix('.sqlite')
    tam = dich.with_name(dich.name + '.tmp')
    nguon_con = sqlite3.connect(csdl.uri_chi_doc(nguon), uri=True)
    ra = sqlite3.connect(str(tam))
    try:
        nguon_con.backup(ra)                         # bản sao nhất quán (không chép giữa lúc đang ghi)
    finally:
        ra.close()
        nguon_con.close()
    os.replace(tam, dich)
    return dich


def khoi_phuc_bo_goc() -> dict:
    """Dùng lại bộ đơn giá chuẩn đóng gói kèm phần mềm (0.9.73): bản đã cập nhật / sửa trên máy KHÔNG xóa - đổi tên thành
    "<tên>.truoc_khoi_phuc_<giờ>.sqlite" cạnh đó (lấy lại được). Trả thông tin bộ gốc + file đã cất (hoặc '' nếu chưa có bản máy)."""
    moi = file_cap_nhat()
    cat = ''
    if moi.exists():
        dich = moi.with_name(f'{moi.stem}.truoc_khoi_phuc_{datetime.now():%Y%m%d_%H%M%S}.sqlite')
        os.replace(moi, dich)
        cat = str(dich)
    return dict(kiem_tra_bo(file_goc()), cat=cat)


def cap_nhat_tu_file(p, phien_ban: str = '') -> dict:
    """Cập nhật bộ đơn giá từ file PABT Excel chuẩn (.xlsm/.xlsx) hoặc gói bộ đơn giá (.sqlite)."""
    p = Path(p)
    if p.suffix.lower() in ('.xlsm', '.xlsx'):
        with tempfile.TemporaryDirectory() as td:
            ra = Path(td) / TEN_FILE
            tao_bo_tu_excel(p, ra, phien_ban)
            return cai_bo(ra)
    return cai_bo(p)


def kiem_tra_mang(url: str, timeout: int = 20) -> dict | None:
    """Đọc thông báo cập nhật (JSON) tại url; trả thông báo nếu có phiên bản mới hơn bộ đang dùng, không thì None."""
    if not url:
        raise LoiNhap('Chưa có địa chỉ cập nhật. Nhập địa chỉ file thông báo (JSON) do đơn vị quản lý bộ đơn giá cung cấp.')
    try:
        from .an_toan import ngu_canh_tls
        with urllib.request.urlopen(url, timeout=timeout, context=ngu_canh_tls()) as r:
            tb = json.loads(r.read(2 ** 20).decode('utf-8'))
    except Exception as e:
        raise LoiNhap(f'Không đọc được thông báo cập nhật:\n{e}') from None
    if not isinstance(tb, dict) or not tb.get('phien_ban') or not tb.get('tai_ve'):
        raise LoiNhap('Thông báo cập nhật không đúng dạng (cần phien_ban, tai_ve).')
    return tb if str(tb['phien_ban']) > thong_tin()['phien_ban'] else None


def tai_va_cai(tb: dict, timeout: int = 120) -> dict:
    """Tải bộ đơn giá theo thông báo cập nhật, kiểm tra mã SHA-256 (nếu có) rồi cài."""
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / TEN_FILE
        try:
            from .an_toan import ngu_canh_tls
            with urllib.request.urlopen(tb['tai_ve'], timeout=timeout, context=ngu_canh_tls()) as r, open(p, 'wb') as f:
                shutil.copyfileobj(r, f)
        except Exception as e:
            raise LoiNhap(f'Không tải được bộ đơn giá:\n{e}') from None
        if tb.get('sha256') and hashlib.sha256(p.read_bytes()).hexdigest().lower() != str(tb['sha256']).lower():
            raise LoiNhap('File tải về sai mã kiểm tra (SHA-256): không cài.')
        return cai_bo(p)


# ---------------------------------------------------------------- sửa từng mục (quyền quản trị — man_hinh_don_gia + quan_tri_bo)
# khóa từng bảng: mã (dm_*) / tu (biểu thưởng) / id (quy_uoc, van_ban)
COT_SUA = {
    'dm_taisan': ('ma', 'nhom', 'phan_loai', 'ten', 'dvt', 'don_gia', 'ghi_chu'),
    'dm_hotro': ('ma', 'ten', 'dvt', 'don_gia', 'can_cu', 'cach_tinh'),
    'tham_so': ('ma', 'ten', 'gia_tri', 'dvt', 'can_cu', 'trang_thai'),
    'bieu_thuong': ('tu', 'muc'),
    'quy_uoc': ('ten_thuc_te', 'ten_tuong_duong', 'dvt', 'don_gia', 'can_cu'),
    'van_ban': ('so_hieu', 'co_quan', 'noi_dung', 'trang_thai'),
}
KHOA_SUA = {
    'dm_taisan': 'ma', 'dm_hotro': 'ma', 'tham_so': 'ma',
    'bieu_thuong': 'tu', 'quy_uoc': 'id', 'van_ban': 'id',
}
_COT_GIA = ('don_gia', 'gia_tri', 'muc', 'tu')


def dam_bao_ban_sua() -> Path:
    """Bản bộ đơn giá ghi được trên máy này (%APPDATA% / PABT_THU_MUC_MAY). Bản đóng gói không ghi; chưa có bản máy thì chép ra."""
    dich = file_cap_nhat()
    dang = file_dang_dung()
    if dang.resolve() == dich.resolve() and dich.exists():
        return dich
    dich.parent.mkdir(parents=True, exist_ok=True)
    tam = dich.with_suffix('.chep')
    shutil.copyfile(dang, tam)
    os.replace(tam, dich)
    return dich


def _sach_gia(k: str, v) -> str:
    s = ' '.join(str(v if v is not None else '').split())
    if k not in _COT_GIA or not s:
        return s
    from . import don_gia_rieng as dgr
    return dgr.chuan_gia(s)


def _sach_dong(bang: str, gt: dict, nhom=None) -> dict:
    if bang not in COT_SUA:
        raise LoiNhap(f'Không sửa bảng "{bang}" trong bộ đơn giá.')
    ra = {}
    for k in COT_SUA[bang]:
        if k == 'nhom':
            n = gt.get('nhom', nhom)
            try:
                n = int(n)
            except (TypeError, ValueError):
                raise LoiNhap('Nhóm danh mục phải là 2 (nhà, công trình) hoặc 3 (cây trồng, vật nuôi).') from None
            if n not in (2, 3):
                raise LoiNhap('Nhóm danh mục phải là 2 (nhà, công trình) hoặc 3 (cây trồng, vật nuôi).')
            ra[k] = n
            continue
        ra[k] = _sach_gia(k, gt.get(k, ''))
    if bang == 'dm_taisan':
        if not ra['ma']:
            raise LoiNhap('Chưa có mã mục.')
        if not ra['ten']:
            raise LoiNhap('Chưa có tên mục.')
        if not ra['dvt']:
            raise LoiNhap('Chưa có đơn vị tính.')
        if not ra['don_gia']:
            raise LoiNhap('Chưa có đơn giá.')
        ra['ma'] = ra['ma'].upper() if ra['ma'][:2].upper() in ('TS', 'CT', 'VN', 'HT', 'CS', 'TH') else ra['ma']
    elif bang == 'dm_hotro':
        if not ra['ma'] or not ra['ten']:
            raise LoiNhap('Chưa có mã / tên khoản hỗ trợ.')
    elif bang == 'tham_so':
        if not ra['ma'] or not ra['ten']:
            raise LoiNhap('Chưa có mã / tên tham số.')
    elif bang == 'bieu_thuong':
        if not ra['tu'] or not ra['muc']:
            raise LoiNhap('Chưa có mốc tổng bồi thường / mức thưởng.')
    elif bang == 'quy_uoc':
        if not ra['ten_thuc_te'] or not ra['dvt'] or not ra['don_gia']:
            raise LoiNhap('Quy ước tương đương cần tên thực tế, ĐVT và đơn giá.')
    elif bang == 'van_ban':
        if not ra['so_hieu']:
            raise LoiNhap('Chưa có số hiệu văn bản.')
    return ra


def _mo_sua():
    """Mở bản máy, khóa danh mục. Gọi: `with _mo_sua() as con:`."""
    from contextlib import contextmanager

    @contextmanager
    def _trong():
        p = dam_bao_ban_sua()
        con = csdl.mo(p)
        try:
            with con, csdl.mo_khoa_danh_muc(con):
                yield con
        finally:
            con.close()

    return _trong()


def doc_dong(bang: str, khoa, p=None) -> dict | None:
    """Một dòng bộ đơn giá (hoặc None)."""
    if bang not in KHOA_SUA:
        raise LoiNhap(f'Không đọc bảng "{bang}".')
    con = csdl.mo(p or file_dang_dung(), chi_doc=True)
    try:
        r = con.execute(f'SELECT * FROM {bang} WHERE {KHOA_SUA[bang]} = ?', (khoa,)).fetchone()
        return dict(r) if r is not None else None
    finally:
        con.close()


def them_dong(bang: str, gt: dict, nhom=None) -> dict:
    """Thêm một mục vào bộ đơn giá đang dùng (ghi bản máy). Trả dòng đã ghi."""
    d = _sach_dong(bang, gt, nhom)
    ck = KHOA_SUA[bang]
    with _mo_sua() as con:
        if ck != 'id' and con.execute(f'SELECT 1 FROM {bang} WHERE {ck} = ?', (d[ck],)).fetchone():
            raise LoiNhap(f'Đã có mục {ck} = "{d[ck]}" trong bộ đơn giá.')
        cot = list(d)
        con.execute(f'INSERT INTO {bang} ({", ".join(cot)}) VALUES ({", ".join("?" * len(cot))})',
                    [d[c] for c in cot])
        if ck == 'id':
            d['id'] = con.execute('SELECT last_insert_rowid()').fetchone()[0]
        csdl.ghi_nhat_ky(con, 'Sửa bộ đơn giá: thêm mục', f'{bang} {d.get(ck, d.get("ten") or d.get("ten_thuc_te") or "")}')
    return d


def sua_dong(bang: str, khoa, gt: dict, nhom=None) -> dict:
    """Sửa mục đang có (khóa không đổi, trừ quy_uoc/van_ban không có mã)."""
    d = _sach_dong(bang, gt, nhom)
    ck = KHOA_SUA[bang]
    with _mo_sua() as con:
        if con.execute(f'SELECT 1 FROM {bang} WHERE {ck} = ?', (khoa,)).fetchone() is None:
            raise LoiNhap(f'Không thấy mục {ck} = "{khoa}" để sửa.')
        if ck != 'id' and ck in d and str(d[ck]) != str(khoa):
            raise LoiNhap('Đổi mã / khóa thì dùng "Thay thế" (không sửa tại chỗ thành mã khác).')
        cot = [c for c in d if c != ck]
        con.execute(f'UPDATE {bang} SET {", ".join(c + " = ?" for c in cot)} WHERE {ck} = ?',
                    [d[c] for c in cot] + [khoa])
        d[ck] = khoa
        csdl.ghi_nhat_ky(con, 'Sửa bộ đơn giá: sửa mục', f'{bang} {khoa}')
    return d


def xoa_dong(bang: str, khoa) -> dict:
    """Xóa một mục khỏi bộ đơn giá đang dùng."""
    if bang not in KHOA_SUA:
        raise LoiNhap(f'Không xóa bảng "{bang}".')
    ck = KHOA_SUA[bang]
    with _mo_sua() as con:
        r = con.execute(f'SELECT * FROM {bang} WHERE {ck} = ?', (khoa,)).fetchone()
        if r is None:
            raise LoiNhap(f'Không thấy mục {ck} = "{khoa}" để xóa.')
        con.execute(f'DELETE FROM {bang} WHERE {ck} = ?', (khoa,))
        csdl.ghi_nhat_ky(con, 'Sửa bộ đơn giá: xóa mục', f'{bang} {khoa}')
        return dict(r)


def thay_the_dong(bang: str, khoa, gt: dict, nhom=None) -> dict:
    """Thay một mục bằng nội dung mới (được đổi mã). Mục cũ bị xóa."""
    d = _sach_dong(bang, gt, nhom)
    ck = KHOA_SUA[bang]
    with _mo_sua() as con:
        if con.execute(f'SELECT 1 FROM {bang} WHERE {ck} = ?', (khoa,)).fetchone() is None:
            raise LoiNhap(f'Không thấy mục {ck} = "{khoa}" để thay thế.')
        moi_khoa = d.get(ck, khoa)
        if ck != 'id' and str(moi_khoa) != str(khoa):
            if con.execute(f'SELECT 1 FROM {bang} WHERE {ck} = ?', (moi_khoa,)).fetchone():
                raise LoiNhap(f'Đã có mục {ck} = "{moi_khoa}", không thay được.')
        con.execute(f'DELETE FROM {bang} WHERE {ck} = ?', (khoa,))
        cot = list(d)
        if ck == 'id':
            d['id'] = khoa
            if 'id' not in cot:
                cot = ['id'] + cot
        con.execute(f'INSERT INTO {bang} ({", ".join(cot)}) VALUES ({", ".join("?" * len(cot))})',
                    [d[c] for c in cot])
        if ck == 'id':
            d['id'] = khoa
        csdl.ghi_nhat_ky(con, 'Sửa bộ đơn giá: thay thế mục', f'{bang} {khoa} → {d.get(ck, "")}')
    return d

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

from . import csdl, nhap_excel
from .lap_pa import LoiNhap

TEN_FILE = 'bo_don_gia.sqlite'
TEN_BO = 'BỘ ĐƠN GIÁ BỒI THƯỜNG, HỖ TRỢ, TÁI ĐỊNH CƯ - ĐỒNG NAI'
# bộ đơn giá không chứa giá đất từng dự án: giá đất nhập ở bước "Bảng giá đất" khi lập dự án
BANG_BO = tuple(b for b in csdl.DANH_MUC if b != 'gia_dat')
# phân loại dòng vật nuôi trong dm_taisan (nhóm 3 như cây trồng): bộ tích hợp mã VN.. (QĐ 31/2025/QĐ-UBND), mục cập nhật từ văn
# bản vật nuôi (nhap_don_gia.ap_dung); màn hình Bộ đơn giá có thẻ "Vật nuôi" riêng theo phân loại này
PHAN_LOAI_VAT_NUOI = '3. Bồi thường thiệt hại về vật nuôi'
TRA_CUU = [
    ('Công báo Đồng Nai (văn bản quy phạm mới)', 'https://congbao.dongnai.gov.vn/'),
    ('Góp ý dự thảo - Cổng thông tin Đồng Nai', 'https://dongnai.gov.vn/vi/gop-y-du-thao/'),
    ('Thư viện pháp luật: Đồng Nai bồi thường, hỗ trợ, tái định cư',
     'https://thuvienphapluat.vn/page/tim-van-ban.aspx?keyword=%C4%90%E1%BB%93ng%20Nai%20b%E1%BB%93i%20th%C6%B0%E1%BB%9Dng%20h%E1%BB%97%20tr%E1%BB%A3%20t%C3%A1i%20%C4%91%E1%BB%8Bnh%20c%C6%B0&sort=1'),
    ('Thư viện pháp luật: Đồng Nai đơn giá bồi thường',
     'https://thuvienphapluat.vn/page/tim-van-ban.aspx?keyword=%C4%90%E1%BB%93ng%20Nai%20%C4%91%C6%A1n%20gi%C3%A1%20b%E1%BB%93i%20th%C6%B0%E1%BB%9Dng&sort=1'),
]


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


def file_dang_dung() -> Path:
    """Bộ đơn giá mới nhất: bản đã cập nhật (nếu hợp lệ và mới hơn) hoặc bản đóng gói."""
    goc, moi = file_goc(), file_cap_nhat()
    if moi.exists():
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

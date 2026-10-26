"""Sổ nhật ký vận động (Bước 14, 15 Mục IV QĐ 18/2026/QĐ-UBND): ghi các buổi vận động hộ không nhận tiền bồi thường hoặc không
bàn giao mặt bằng; quá thời hạn vận động (`thoi_han`: mặc định 10 ngày) mà hộ vẫn chưa nhận tiền / chưa bàn giao thì hộ chuyển
sang "Đủ điều kiện cưỡng chế thu hồi đất theo Điều 89" (Luật Đất đai 2024) và vào danh sách đề nghị ban hành quyết định cưỡng chế.

Quy tắc (thời điểm tính = ngày vận động ĐẦU TIÊN của việc đó; "quá" = số ngày đã qua LỚN HƠN thời hạn):
  * 'tien'      áp dụng khi hộ có quyết định phê duyệt mà còn quyết định chưa nhận tiền;
  * 'mat_bang'  áp dụng khi hộ có quyết định phê duyệt mà chưa bàn giao mặt bằng.
  * Việc hết áp dụng (đã nhận tiền / đã bàn giao) -> 'hoan_thanh', không còn tính cưỡng chế; hộ chưa có quyết định -> 'chua_ap_dung'.
  * Hộ chưa có buổi vận động nào: không phát sinh trạng thái (tránh báo hàng loạt hộ đang trong tiến độ bình thường).

Bảng `nhat_ky_van_dong` tạo khi cần (CREATE TABLE IF NOT EXISTS) - KHÔNG đổi PHIEN_BAN_CSDL, file cũ / bản phần mềm cũ vẫn mở được.
Không phụ thuộc Qt.
"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

from . import csdl, thoi_han
from .lap_pa import LoiNhap, kiem_ho_nhan_viec
from .quan_ly import chuan_ngay

BANG = 'nhat_ky_van_dong'
VIEC = {'tien': 'Không nhận tiền bồi thường', 'mat_bang': 'Không bàn giao mặt bằng'}
KET_QUA = (('chua_dong_y', 'Chưa đồng ý'), ('vang_mat', 'Vắng mặt / không gặp được'), ('dong_y', 'Đồng ý, chờ thực hiện'))
TEN_KET_QUA = dict(KET_QUA)
HINH_THUC = ('Gặp trực tiếp tại hộ', 'Họp tổ vận động', 'Gửi giấy mời / thông báo', 'Điện thoại', 'Khác')
CHU_CUONG_CHE = 'Đủ điều kiện cưỡng chế thu hồi đất theo Điều 89'
CAN_CU_CUONG_CHE = 'Điều 89 Luật Đất đai 2024; Mục IV Quyết định 18/2026/QĐ-UBND (Bước 14, 15)'
# thứ tự nặng -> nhẹ khi gộp trạng thái của một hộ
THU_TU_TT = ('du_dk_cuong_che', 'dang_van_dong', 'hoan_thanh')

_SQL_TAO = (f'''CREATE TABLE IF NOT EXISTS {BANG} (
    id INTEGER PRIMARY KEY,
    ma_ho INTEGER NOT NULL REFERENCES ho(ma_ho) ON UPDATE CASCADE ON DELETE CASCADE,
    viec TEXT NOT NULL, ngay TEXT NOT NULL, hinh_thuc TEXT NOT NULL DEFAULT '', thanh_phan TEXT NOT NULL DEFAULT '',
    noi_dung TEXT NOT NULL DEFAULT '', ket_qua TEXT NOT NULL DEFAULT 'chua_dong_y', bien_ban TEXT NOT NULL DEFAULT '',
    ghi_chu TEXT NOT NULL DEFAULT '')''', f'CREATE INDEX IF NOT EXISTS ix_van_dong_ho ON {BANG}(ma_ho, viec)')


def co_bang(con) -> bool:
    return con.execute("SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?", (BANG,)).fetchone() is not None


def dam_bao_bang(con) -> bool:
    """Tạo bảng nếu chưa có (file cũ). False khi không tạo được (file mở chỉ xem): các hàm đọc coi như chưa có buổi nào."""
    if co_bang(con):
        return True
    try:
        with con:
            for lenh in _SQL_TAO:
                con.execute(lenh)
    except sqlite3.OperationalError:
        return False
    return True


def xoa_het(con) -> None:
    """Xóa toàn bộ nhật ký (nhap_tho.xoa_trang: xóa trắng hồ sơ dự án)."""
    if co_bang(con):
        con.execute(f'DELETE FROM {BANG}')


# ---------------------------------------------------------------- ghi / đọc các buổi vận động
def ghi_buoi(con, ma_ho: int, viec: str, ngay: str, hinh_thuc: str = '', thanh_phan: str = '', noi_dung: str = '',
             ket_qua: str = 'chua_dong_y', bien_ban: str = '', ghi_chu: str = '', buoi_id: int | None = None) -> int:
    """Thêm (buoi_id None) hoặc sửa một buổi vận động. Trả id."""
    kiem_ho_nhan_viec(con, ma_ho)
    if viec not in VIEC:
        raise LoiNhap('Chọn việc vận động: không nhận tiền bồi thường hoặc không bàn giao mặt bằng.')
    if ket_qua not in TEN_KET_QUA:
        raise LoiNhap('Chọn kết quả buổi vận động.')
    if not str(ngay or '').strip():
        raise LoiNhap('Nhập ngày vận động (ví dụ 12/10/2026).')
    ngay = chuan_ngay(ngay)
    if not con.execute('SELECT 1 FROM ho WHERE ma_ho = ?', (ma_ho,)).fetchone():
        raise LoiNhap('Hộ không còn trong dự án.')
    if not dam_bao_bang(con):
        raise LoiNhap('Dự án đang mở chỉ xem: không ghi được nhật ký vận động.')
    gt = (viec, ngay, ' '.join(str(hinh_thuc or '').split()), str(thanh_phan or '').strip(), str(noi_dung or '').strip(),
          ket_qua, str(bien_ban or '').strip(), str(ghi_chu or '').strip())
    with csdl.giao_dich(con):
        if buoi_id is None:
            buoi_id = con.execute(f'INSERT INTO {BANG} (ma_ho, viec, ngay, hinh_thuc, thanh_phan, noi_dung, ket_qua, bien_ban, '
                                  'ghi_chu) VALUES (?,?,?,?,?,?,?,?,?)', (ma_ho, *gt)).lastrowid
            csdl.ghi_nhat_ky(con, 'Vận động hộ', f'Hộ {ma_ho}: {VIEC[viec]}, {ngay}, {TEN_KET_QUA[ket_qua]}')
        else:
            if not con.execute(f'SELECT 1 FROM {BANG} WHERE id = ?', (buoi_id,)).fetchone():
                raise LoiNhap('Buổi vận động không còn trong nhật ký.')
            con.execute(f'UPDATE {BANG} SET viec = ?, ngay = ?, hinh_thuc = ?, thanh_phan = ?, noi_dung = ?, ket_qua = ?, '
                        'bien_ban = ?, ghi_chu = ? WHERE id = ?', (*gt, buoi_id))
            csdl.ghi_nhat_ky(con, 'Sửa buổi vận động', f'Hộ {ma_ho}: {VIEC[viec]}, {ngay}')
    return buoi_id


def xoa_buoi(con, buoi_id: int) -> int:
    if not co_bang(con):
        return 0
    r = con.execute(f'SELECT ma_ho, ngay FROM {BANG} WHERE id = ?', (buoi_id,)).fetchone()
    if r is not None:
        kiem_ho_nhan_viec(con, r['ma_ho'])
    with csdl.giao_dich(con):
        n = con.execute(f'DELETE FROM {BANG} WHERE id = ?', (buoi_id,)).rowcount
        if n and r:
            csdl.ghi_nhat_ky(con, 'Xóa buổi vận động', f'Hộ {r["ma_ho"]}, {r["ngay"]}')
    return n


def ds_buoi(con, ma_ho: int | None = None, viec: str | None = None) -> list:
    """Các buổi vận động theo thứ tự ngày (cũ trước), mỗi buổi một dict."""
    if not co_bang(con):
        return []
    dk, tham = [], []
    if ma_ho is not None:
        dk.append('ma_ho = ?')
        tham.append(ma_ho)
    if viec is not None:
        dk.append('viec = ?')
        tham.append(viec)
    sql = f'SELECT * FROM {BANG}' + (' WHERE ' + ' AND '.join(dk) if dk else '')
    kq = [dict(r) for r in con.execute(sql, tham)]
    kq.sort(key=lambda b: (thoi_han.doc_ngay(b['ngay']) or date.min, b['id']))
    return kq


# ---------------------------------------------------------------- trạng thái từng hộ
@dataclass
class TinhTrang:
    viec: str
    ma: str                       # 'du_dk_cuong_che' / 'dang_van_dong' / 'hoan_thanh' / 'chua_ap_dung' (hộ chưa có quyết định)
    chu: str
    so_buoi: int
    ngay_dau: date | None
    da_qua: int                   # số ngày kể từ buổi vận động đầu tiên
    con_lai: int                  # số ngày còn lại của thời hạn vận động (0 khi đã quá)
    han: date | None              # hết thời hạn vận động
    ket_qua_cuoi: str = ''


def viec_ap_dung(x) -> list:
    """Các việc cần vận động của hộ x (theo_doi.TongHopHo): chưa nhận đủ tiền / chưa bàn giao - chỉ khi đã có quyết định."""
    if not x.qd:
        return []
    kq = []
    if x.qd_chua_nhan:
        kq.append('tien')
    if not x.da_ban_giao:
        kq.append('mat_bang')
    return kq


def tinh_trang_ho(x, buoi: list, n_van_dong: int, hom_nay: date) -> list:
    """Trạng thái từng việc của hộ x (chỉ các việc ĐÃ có buổi vận động)."""
    ap = set(viec_ap_dung(x))
    kq = []
    for viec in VIEC:
        b = [y for y in buoi if y['viec'] == viec]
        if not b:
            continue
        dau = thoi_han.doc_ngay(b[0]['ngay'])
        da_qua = max(0, (hom_nay - dau).days) if dau else 0
        con_lai = max(0, n_van_dong - da_qua)
        han = dau + timedelta(days=n_van_dong) if dau else None
        cuoi = b[-1]['ket_qua']
        if viec not in ap and not x.qd:
            ma, chu = 'chua_ap_dung', 'Hộ chưa có quyết định phê duyệt - chưa áp dụng thời hạn vận động'
        elif viec not in ap:
            ma, chu = 'hoan_thanh', 'Đã hoàn tất sau vận động' + (' (đã nhận tiền)' if viec == 'tien' else ' (đã bàn giao)')
        elif da_qua > n_van_dong:
            ma, chu = 'du_dk_cuong_che', CHU_CUONG_CHE
        else:
            ma = 'dang_van_dong'
            # da_qua == thời hạn: hôm nay là ngày hết hạn (trước đây hiện "ngày 11/10, còn 0 ngày")
            chu = ((f'Đang vận động: ngày {da_qua + 1}/{n_van_dong}, còn {con_lai} ngày' if con_lai else
                    f'Đang vận động: hôm nay hết hạn {n_van_dong} ngày') +
                   ('; hộ đã đồng ý, chờ thực hiện' if cuoi == 'dong_y' else ''))
        kq.append(TinhTrang(viec, ma, chu, len(b), dau, da_qua, con_lai, han, cuoi))
    return kq


def danh_gia_cuong_che(x, buoi: list, n_van_dong: int, hom_nay: date, moc_ho: dict | None = None) -> dict:
    """Đánh giá điều kiện lập hồ sơ ban hành quyết định cưỡng chế thu hồi đất của hộ x (theo_doi.TongHopHo) - ô kết luận của Sổ nhật
    ký vận động (20/10/2026). dict(du, dong=[(đạt?, chữ)], ket_luan). Các điều kiện (theo dữ liệu phần mềm có):
      1. đã có quyết định phê duyệt phương án;
      2. đã vận động và đã qua thời hạn vận động (n_van_dong ngày) kể từ buổi đầu tiên;
      3. đủ mốc thời gian thông báo thu hồi đất (thoi_han.moc_thu_hoi_tat_ca - None: chưa có ngày thông báo thì chưa kiểm được);
      4. hộ vẫn chưa nhận tiền / chưa bàn giao mặt bằng.
    Không chặn - chỉ hiện (căn cứ: CAN_CU_CUONG_CHE)."""
    from .thoi_han import hien_ngay
    dong = []
    co_qd = bool(x.qd)
    dong.append((co_qd, 'Đã có quyết định phê duyệt phương án' + (f' ({"; ".join(q["so_qd"] for q in x.qd)})' if co_qd else '')
                 if co_qd else 'Chưa có quyết định phê duyệt phương án'))
    dau = thoi_han.doc_ngay(buoi[0]['ngay']) if buoi else None
    if dau is None:
        dong.append((False, 'Chưa có buổi vận động nào'))
        qua = False
    else:
        da_qua = max(0, (hom_nay - dau).days)
        qua = da_qua > n_van_dong
        dong.append((qua, f'Buổi vận động đầu tiên: {hien_ngay(dau)} (đã qua {da_qua} ngày ' +
                     (f'> {n_van_dong} ngày theo thời hạn vận động)' if qua else f'- chưa quá {n_van_dong} ngày)')))
    if moc_ho is None:
        dong.append((False, 'Chưa kiểm được mốc thông báo thu hồi đất (chưa nhập ngày thông báo - nút "Mốc pháp lý…")'))
        du_moc = False
    else:
        du_moc = bool(moc_ho.get('du'))
        dong.append((du_moc, ('Đã đủ thời gian thông báo thu hồi đất' if du_moc else 'Chưa đủ thời gian thông báo thu hồi đất') +
                     (f' ({moc_ho["chu"]})' if moc_ho.get('chu') else '')))
    ap = viec_ap_dung(x)
    dong.append((bool(ap), ('Hộ vẫn ' + ' và '.join(VIEC[v].lower() for v in ap)) if ap
                 else 'Hộ đã nhận tiền và đã bàn giao mặt bằng - không cần cưỡng chế'))
    du = co_qd and qua and du_moc and bool(ap)
    kl = ('ĐỦ ĐIỀU KIỆN LẬP HỒ SƠ BAN HÀNH QUYẾT ĐỊNH CƯỠNG CHẾ THU HỒI ĐẤT' if du else
          'CHƯA ĐỦ ĐIỀU KIỆN CƯỠNG CHẾ - tiếp tục vận động / bổ sung điều kiện còn thiếu')
    return dict(du=du, dong=dong, ket_luan=kl, can_cu=CAN_CU_CUONG_CHE)


def tinh_trang_tat_ca(con, ds_tong_hop: list | None = None, hom_nay=None) -> dict:
    """{ma_ho: [TinhTrang]} của các hộ đã có buổi vận động. ds_tong_hop: kết quả theo_doi.tong_hop (tránh đọc lại)."""
    buoi = ds_buoi(con)
    if not buoi:
        return {}
    theo_ho = {}
    for b in buoi:
        theo_ho.setdefault(b['ma_ho'], []).append(b)
    if ds_tong_hop is None:
        from . import theo_doi
        ds_tong_hop = theo_doi.tong_hop(con, list(theo_ho), tinh_pa=False)
    nay, n = thoi_han.hom_nay_hoac(hom_nay), thoi_han.so_ngay(con, 'van_dong')
    kq = {}
    for x in ds_tong_hop:
        if x.ma_ho in theo_ho:
            tt = tinh_trang_ho(x, theo_ho[x.ma_ho], n, nay)
            if tt:
                kq[x.ma_ho] = tt
    return kq


def trang_thai_chung(ds_tt: list):
    """Trạng thái nặng nhất của hộ -> (mã, chữ); không có -> ('', '')."""
    for ma in THU_TU_TT:
        ds = [t for t in ds_tt if t.ma == ma]
        if ds:
            if ma == 'du_dk_cuong_che':
                return ma, CHU_CUONG_CHE + ' (' + '; '.join(VIEC[t.viec].lower() for t in ds) + ')'
            return ma, '; '.join(f'{VIEC[t.viec]}: {t.chu}' for t in ds)
    return '', ''


# ---------------------------------------------------------------- Bước 15: danh sách đề nghị ban hành quyết định cưỡng chế
def ds_cuong_che(con, hom_nay=None, ds_tong_hop: list | None = None) -> list:
    """Mỗi (hộ, việc) đủ điều kiện cưỡng chế một dòng: thông tin hộ, thửa, quyết định, buổi vận động, mốc thu hồi đất."""
    from . import theo_doi
    ds = ds_tong_hop if ds_tong_hop is not None else theo_doi.tong_hop(con, tinh_pa=False)
    tt = tinh_trang_tat_ca(con, ds, hom_nay)
    moc = thoi_han.moc_thu_hoi_tat_ca(con, list(tt), hom_nay)
    kq = []
    for x in ds:
        for t in tt.get(x.ma_ho, []):
            if t.ma != 'du_dk_cuong_che':
                continue
            kq.append(dict(ma_ho=x.ma_ho, ho_ten=x.ho_ten, dia_chi=x.dia_chi, viec=VIEC[t.viec],
                           thua='; '.join(f'{c["so_thua"] or "…"} (tờ {c["so_to"] or "…"})' for c in x.thua),
                           dt=x.dt, loai_dat='; '.join(sorted({c['loai_dat'] for c in x.thua if c['loai_dat']})),
                           qd='; '.join(sorted({q['so_qd'] for q in x.qd})),
                           so_buoi=t.so_buoi, ngay_dau=thoi_han.hien_ngay(t.ngay_dau), han=thoi_han.hien_ngay(t.han),
                           qua_han=t.da_qua - thoi_han.so_ngay(con, 'van_dong'), ket_qua_cuoi=TEN_KET_QUA.get(t.ket_qua_cuoi, ''),
                           moc_thu_hoi=moc.get(x.ma_ho, {}).get('chu', '')))
    return kq


COT_CUONG_CHE = ['STT', 'Mã hộ', 'Họ và tên', 'Địa chỉ', 'Thửa đất', 'DT thu hồi (m²)', 'Loại đất', 'Quyết định phê duyệt',
                 'Lý do cưỡng chế', 'Số buổi vận động', 'Vận động từ ngày', 'Hết hạn vận động', 'Quá hạn (ngày)',
                 'Kết quả buổi gần nhất', 'Mốc thu hồi đất']


def xuat_ds_cuong_che(con, file, hom_nay=None) -> Path:
    """Excel danh sách đề nghị ban hành quyết định cưỡng chế thu hồi đất. Không có hộ nào đủ điều kiện -> LoiNhap."""
    from . import theo_doi
    ds = ds_cuong_che(con, hom_nay)
    if not ds:
        raise LoiNhap('Chưa có hộ nào đủ điều kiện cưỡng chế (cần vận động quá '
                      f'{thoi_han.so_ngay(con, "van_dong")} ngày mà hộ vẫn chưa nhận tiền / chưa bàn giao mặt bằng).')
    dong = [[i, d['ma_ho'], d['ho_ten'], d['dia_chi'], d['thua'], d['dt'], d['loai_dat'], d['qd'], d['viec'], d['so_buoi'],
             d['ngay_dau'], d['han'], d['qua_han'], d['ket_qua_cuoi'], d['moc_thu_hoi']] for i, d in enumerate(ds, start=1)]
    da = con.execute('SELECT ten FROM du_an WHERE id = 1').fetchone()
    return theo_doi.xuat_excel(file, 'DANH SÁCH ĐỀ NGHỊ BAN HÀNH QUYẾT ĐỊNH CƯỠNG CHẾ THU HỒI ĐẤT', COT_CUONG_CHE, dong,
                               [5, 7, 24, 26, 20, 12, 12, 20, 26, 9, 13, 13, 9, 20, 40], None,
                               ((da['ten'] if da else '') + f' - Căn cứ: {CAN_CU_CUONG_CHE}').strip(' -'))

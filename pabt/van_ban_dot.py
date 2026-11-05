"""Văn bản, biên bản theo từng mục của đợt niêm yết (1.0.58, người dùng 04/11/2026: Thông báo niêm yết trong mục Niêm yết, Giấy mời trong mục
Lấy ý kiến, Giấy mời / Thông báo trong mục Đối thoại, các Biên bản…) và đọc KẾT QUẢ từ file scan / Word / Excel (dùng quan_ly.doc_van_ban:
PDF ảnh, ảnh qua Tesseract trên máy) để ghi ý kiến / kết luận đối thoại của từng hộ. Không Qt.

Bảng van_ban_dot tạo khi ghi lần đầu (CREATE IF NOT EXISTS: file cũ mở được, bản cũ bỏ qua bảng lạ). File đính kèm: giữ đường dẫn đầy đủ như HS đính kèm."""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from . import csdl, du_thao
from .lap_pa import LoiNhap, bo_dau, kiem_quyen

BANG = '''CREATE TABLE IF NOT EXISTS van_ban_dot (
    id INTEGER PRIMARY KEY,
    dot_id INTEGER NOT NULL REFERENCES dot_du_thao(id) ON DELETE CASCADE,
    muc TEXT NOT NULL,
    loai TEXT NOT NULL DEFAULT '',
    so_hieu TEXT NOT NULL DEFAULT '',
    ngay TEXT NOT NULL DEFAULT '',
    noi_dung TEXT NOT NULL DEFAULT '',
    duong_dan TEXT NOT NULL DEFAULT '',
    luc TEXT NOT NULL DEFAULT ''
)'''
# theo thứ tự thẻ của màn hình Niêm yết
MUC = (('niem_yet', 'Niêm yết công khai'), ('y_kien', 'Lấy ý kiến nhân dân'), ('doi_thoai', 'Đối thoại & Tiếp thu'), ('tong_hop', 'Tổng hợp kết quả ý kiến'))
TEN_MUC = dict(MUC)
LOAI_THEO_MUC = {
    'niem_yet': ('Thông báo niêm yết công khai', 'Biên bản niêm yết công khai', 'Biên bản kết thúc niêm yết', 'Văn bản khác'),
    'y_kien': ('Giấy mời lấy ý kiến', 'Biên bản lấy ý kiến', 'Phiếu lấy ý kiến', 'Văn bản khác'),
    'doi_thoai': ('Giấy mời đối thoại', 'Thông báo đối thoại', 'Biên bản đối thoại', 'Văn bản khác'),
    'tong_hop': ('Báo cáo tổng hợp ý kiến', 'Biên bản tổng hợp ý kiến', 'Văn bản khác'),
}
DUOI_FILE = ('.pdf', '.jpg', '.jpeg', '.png', '.bmp', '.tif', '.tiff', '.webp', '.doc', '.docx', '.xls', '.xlsx', '.xlsm')


def _co_bang(con) -> bool:
    return bool(con.execute("SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'van_ban_dot'").fetchone())


def ds(con, dot_id: int, muc: str | None = None) -> list:
    """[sqlite3.Row] văn bản của đợt (của một mục nếu có muc), cũ trước."""
    if not _co_bang(con):
        return []
    if muc:
        return con.execute('SELECT * FROM van_ban_dot WHERE dot_id = ? AND muc = ? ORDER BY id', (dot_id, muc)).fetchall()
    return con.execute('SELECT * FROM van_ban_dot WHERE dot_id = ? ORDER BY id', (dot_id,)).fetchall()


def dem(con, dot_id: int) -> dict:
    if not _co_bang(con):
        return {}
    return {r[0]: r[1] for r in con.execute('SELECT muc, COUNT(*) FROM van_ban_dot WHERE dot_id = ? GROUP BY muc', (dot_id,))}


def _kiem_file(duong_dan: str) -> str:
    duong_dan = str(duong_dan or '').strip()
    if not duong_dan:
        return ''
    from .an_toan import LoiAnToan, kiem_tra_magic_bytes
    p = Path(duong_dan)
    if p.suffix.lower() not in DUOI_FILE:
        raise LoiNhap(f'File "{p.name}" không phải loại văn bản (PDF, ảnh, Word, Excel).')
    try:
        if p.is_file():
            kiem_tra_magic_bytes(p)
    except LoiAnToan as e:
        raise LoiNhap(str(e)) from None
    return str(p.resolve())


def luu(con, dot_id: int, muc: str, loai: str, so_hieu: str = '', ngay: str = '', noi_dung: str = '', duong_dan: str = '', id_: int | None = None) -> int:
    """Thêm (id_ None) / sửa một văn bản. ngay: dd/mm/yyyy hoặc trống. Trả id."""
    kiem_quyen(con, 'niem_yet')
    if muc not in TEN_MUC:
        raise LoiNhap('Mục không hợp lệ.')
    loai = ' '.join(str(loai or '').split())
    if not loai:
        raise LoiNhap('Chọn hoặc gõ loại văn bản.')
    n = du_thao.ngay_iso(du_thao.doc_ngay(ngay)) if str(ngay or '').strip() else ''
    f = _kiem_file(duong_dan)
    gt = (loai, ' '.join(str(so_hieu or '').split()), n, str(noi_dung or '').strip(), f)
    with csdl.giao_dich(con):
        con.execute(BANG)
        if id_ is None:
            id_ = con.execute('INSERT INTO van_ban_dot (dot_id, muc, loai, so_hieu, ngay, noi_dung, duong_dan, luc) VALUES (?,?,?,?,?,?,?,?)',
                              (dot_id, muc, *gt, datetime.now().strftime('%Y-%m-%d %H:%M:%S'))).lastrowid
        else:
            con.execute('UPDATE van_ban_dot SET loai = ?, so_hieu = ?, ngay = ?, noi_dung = ?, duong_dan = ? WHERE id = ?', (*gt, id_))
        csdl.ghi_nhat_ky(con, f'{TEN_MUC[muc]}: lưu văn bản', f'Đợt {dot_id}: {loai} {gt[1]}')
    return id_


def xoa(con, id_: int) -> None:
    kiem_quyen(con, 'niem_yet')
    with csdl.giao_dich(con):
        con.execute('DELETE FROM van_ban_dot WHERE id = ?', (id_,))
        csdl.ghi_nhat_ky(con, 'Xóa văn bản của đợt niêm yết', str(id_))


def doc_thong_tin(file, bao_tien_do=None, cho=None) -> dict:
    """Đọc file văn bản (PDF ảnh, ảnh, Word, Excel): {'so_hieu', 'ngay', 'noi_dung'} để điền sẵn."""
    from .nhap_don_gia import phan_tich_van_ban
    from .quan_ly import doc_van_ban
    dong, _ = doc_van_ban(file, bao_tien_do, cho)
    vb = phan_tich_van_ban(dong, str(file).replace('\\', '/').rsplit('/', 1)[-1])
    return dict(so_hieu=vb.get('so_hieu', ''), ngay=vb.get('ngay', ''), noi_dung=vb.get('trich_yeu', ''))


# ---------------------------------------------------------------- đọc kết quả từng hộ
@dataclass
class KetQuaDong:
    ma_ho: int
    ho_ten: str
    loai: str               # dong_y / khong_dong_y / y_kien_khac / '' = không nhận ra
    noi_dung: str
    nguon: str              # dòng gốc để đối chiếu
    khop_theo: str
    chon: bool = True
    v2: str = ''            # nhánh V2 tự tạo khi ghi (hộ có ý kiến khác phương án)


def phan_loai(chu: str) -> str:
    k = bo_dau(chu)
    if re.search(r'khong (dong y|nhat tri|thong nhat)', k):
        return 'khong_dong_y'
    if re.search(r'y kien khac|kien nghi|de nghi|khieu nai|phan anh', k):
        return 'y_kien_khac'
    if re.search(r'dong y|nhat tri|thong nhat', k):
        return 'dong_y'
    return ''


def _ten_chuan(s) -> str:
    from .quan_ly import _ten_chuan as f
    return f(s)


_RE_UUID = re.compile(r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}', re.I)
_RE_THUA_TO = re.compile(r'([\d][\d,;\s]*?)\s*\(\s*t[ờo]\s*(?:b[ảa]n\s*đ[ồo]\s*)?(?:s[ốo]\s*)?(\d+)\s*\)', re.I)
_RE_THUA_TO_2 = re.compile(r'th[ửu]a\s*(?:đ[ấa]t\s*)?(?:s[ốo]\s*)?(\d+)\s*[,;\-\s]*t[ờo]\s*(?:b[ảa]n\s*đ[ồo]\s*)?(?:s[ốo]\s*)?(\d+)', re.I)
# hậu tố trong cột tên / trong tên hộ của phần mềm: "... là chủ sở hữu", "UBND xã ... quản lý." (trên chữ đã bỏ dấu)
_RE_HAU_TO = re.compile(r'\s+(?:la chu so huu|la chu su dung|la nguoi su dung|dai dien|cung vo|cung chong|thua ke)\b.*$|\s+quan ly\s*$')


def chuan_cccd(x) -> str:
    """Chữ số của CCCD / CMND; Excel cắt mất số 0 đầu (11 số) thì bù lại."""
    so = re.sub(r'\D', '', str(x or ''))
    return '0' + so if len(so) == 11 else so


def ten_sach(x) -> str:
    """Tên để so: không dấu, bỏ "Ông / Bà", bỏ hậu tố "là chủ sở hữu…", "quản lý."."""
    return _RE_HAU_TO.sub('', _ten_chuan(x)).strip()


def cap_thua_to(chu) -> list:
    """Các cặp (số thửa, số tờ) trong một ô: "17 (tờ 39)", "11, 21 (tờ 19)", "Thửa 16 tờ 39", "thửa đất số 16, tờ bản đồ số 39"."""
    kq = []
    for m in _RE_THUA_TO.finditer(str(chu or '')):
        kq += [(t.lstrip('0') or '0', m.group(2).lstrip('0') or '0') for t in re.findall(r'\d+', m.group(1))]
    for m in _RE_THUA_TO_2.finditer(str(chu or '')):
        kq.append((m.group(1).lstrip('0') or '0', m.group(2).lstrip('0') or '0'))
    return kq


class _KhopHo:
    """Khớp một dòng file với hộ TRONG ĐỢT, 4 tầng: mã định danh -> CCCD -> thửa + tờ (nhiều hộ cùng thửa: thêm tên) -> họ tên (trùng tên: thêm STT trong đợt).
    Không chắc thì KHÔNG ghép (đoán nhầm hộ tệ hơn bỏ sót - bản engine lấy hộ đầu tiên, so chuỗi con: "An" khớp "Thanh An")."""

    def __init__(self, con, dot_id: int):
        from . import phien_ban_pa as pb
        self.ho = [dict(r) for r in con.execute('SELECT h.ma_ho, h.ho_ten, h.so_cccd FROM y_kien_du_thao y JOIN ho h ON h.ma_ho = y.ma_ho '
                                                'WHERE y.dot_id = ? ORDER BY h.thu_tu, h.ma_ho', (dot_id,))]
        self.theo_ma, self.theo_cccd, self.theo_ten, self.theo_thua, self.stt = {}, {}, {}, {}, {}
        for i, h in enumerate(self.ho, 1):
            self.theo_ma[h['ma_ho']] = h
            self.stt[h['ma_ho']] = i
            c = chuan_cccd(h['so_cccd'])
            if len(c) >= 9:
                self.theo_cccd.setdefault(c, []).append(h)
            k = ten_sach(h['ho_ten'])
            if len(k.split()) >= 2:
                self.theo_ten.setdefault(k, []).append(h)
        for r in con.execute('SELECT t.ma_ho, t.so_thua, t.so_to FROM thua t JOIN y_kien_du_thao y ON y.ma_ho = t.ma_ho WHERE y.dot_id = ?', (dot_id,)):
            for cap in cap_thua_to(f'{r["so_thua"]} (tờ {r["so_to"]})'):
                self.theo_thua.setdefault(cap, []).append(self.theo_ma[r['ma_ho']])
        self.uuid = {u: self.theo_ma[m] for u, m in pb.bang_uuid(con).items() if m in self.theo_ma}

    def _theo_stt(self, cac: list, ds: list):
        """Nhiều hộ trùng khóa: số đầu dòng là STT trong đợt thì chọn được đúng hộ."""
        so = next((c.strip() for c in cac if re.fullmatch(r'\s*\d{1,4}[.)]?\s*', c)), '')
        so = so.rstrip('.)')
        if so:
            x = [h for h in ds if self.stt[h['ma_ho']] == int(so)]
            if len(x) == 1:
                return x[0]
        return None

    def _theo_ten(self, cac: list, chu: str, ds: list | None = None) -> tuple:
        """(hộ, cách): ô trùng đúng tên -> hàng đầu; tên nằm trong dòng (tên dài nhất). ds: chỉ xét trong các hộ này."""
        cho = {h['ma_ho'] for h in ds} if ds is not None else None
        hop = []
        for c in cac:
            hop += self.theo_ten.get(ten_sach(c), [])
        if not hop:
            k = f' {_ten_chuan(chu)} '
            trung = [(t, x) for t, x in self.theo_ten.items() if f' {t} ' in k]
            if trung:
                hop = max(trung, key=lambda x: len(x[0]))[1]
        if cho is not None:
            hop = [h for h in hop if h['ma_ho'] in cho]
        hop = list({h['ma_ho']: h for h in hop}.values())
        if len(hop) == 1:
            return hop[0], 'họ tên'
        if len(hop) > 1:
            h = self._theo_stt(cac, hop)
            if h is not None:
                return h, 'họ tên + STT'
        return None, ''

    def khop(self, cac: list) -> tuple:
        chu = ' '.join(cac)
        m = _RE_UUID.search(chu)
        if m and m.group(0).lower() in self.uuid:
            return self.uuid[m.group(0).lower()], 'mã định danh'
        # theo TỪNG Ô: nối cả dòng rồi bỏ dấu cách sẽ dính STT vào CCCD ("1 75200000001" -> sai số). Ô số Excel có thể là "75200000001.0"
        for x in (y for c in cac for y in re.findall(r'(?<!\d)\d{9}(?:\d{2,3})?(?!\d)', re.sub(r'(?<=\d)[ .\-](?=\d)', '', re.sub(r'\.0$', '', c.strip())))):
            ds = self.theo_cccd.get(chuan_cccd(x), [])
            if len(ds) == 1:
                return ds[0], 'CCCD'
            if len(ds) > 1:
                h = self._theo_ten(cac, chu, ds)[0]
                if h is not None:
                    return h, 'CCCD + họ tên'
        cap = [x for c in cac for x in cap_thua_to(c)]
        if cap:
            ds = list({h['ma_ho']: h for x in cap for h in self.theo_thua.get(x, [])}.values())
            if len(ds) == 1:
                return ds[0], 'thửa, tờ'
            if len(ds) > 1:
                h = self._theo_ten(cac, chu, ds)[0]
                if h is not None:
                    return h, 'thửa, tờ + họ tên'
        return self._theo_ten(cac, chu)


def doc_ket_qua(con, dot_id: int, files, bao_tien_do=None, cho=None) -> dict:
    """Đọc các file kết quả, ghép từng dòng với hộ TRONG ĐỢT (_KhopHo: 4 tầng). Hộ nhiều dòng (mỗi thửa một dòng): lấy dòng có kết quả đầu tiên.
    {'dong': [KetQuaDong], 'tong_dong': số dòng file, 'scan': có nhận dạng chữ, 'so_ho_dot': số hộ trong đợt, 'khong_khop': [dòng có chữ không ghép được]}. Không ghi gì."""
    from .quan_ly import doc_van_ban
    kh = _KhopHo(con, dot_id)
    kq, da, tong, scan, sot = [], {}, 0, False, []
    for f in ([files] if isinstance(files, (str, Path)) else files):
        dong, s = doc_van_ban(f, bao_tien_do, cho)
        scan = scan or bool(s)
        for r in dong:
            cac = [str(c) for c in r if str(c or '').strip()]
            if not cac:
                continue
            tong += 1
            chu = ' '.join(cac)
            h, cach = kh.khop(cac)
            if h is None:
                if re.search(r'[^\W\d_]{2}', chu):
                    sot.append(chu[:80])
                continue
            loai = phan_loai(chu)
            cu = da.get(h['ma_ho'])
            if cu is not None and (cu.loai or not loai):
                continue
            bo_ten = [c for c in cac if ten_sach(c) != ten_sach(h['ho_ten']) and not cap_thua_to(c) and not _RE_UUID.search(c) and re.search(r'[^\W\d_]{2}', c)]
            nd = max(bo_ten, key=len, default='') if len(cac) > 1 else re.sub(re.escape(h['ho_ten'] or ''), '', chu, flags=re.I).strip(' .:-')
            # nhận ra được hộ nhưng không rõ kết quả: hiện để đối chiếu, không chọn sẵn
            moi = KetQuaDong(h['ma_ho'], h['ho_ten'], loai, nd, chu, cach, chon=bool(loai))
            if cu is not None:
                kq[kq.index(cu)] = moi
            else:
                kq.append(moi)
            da[h['ma_ho']] = moi
    return dict(dong=kq, tong_dong=tong, scan=scan, so_ho_dot=len(kh.ho), khong_khop=sot)


def ap_dung(con, dot_id: int, muc: str, dong: list, ngay: str = '', dia_diem: str = '') -> int:
    """Ghi các dòng chon: mục Đối thoại -> biên bản đối thoại (kết luận = nội dung đọc được); mục khác -> ý kiến của hộ. Trả số hộ."""
    kiem_quyen(con, 'niem_yet')
    n = 0
    with csdl.giao_dich(con):
        for d in dong:
            if not d.chon:
                continue
            if muc == 'doi_thoai':
                du_thao.ghi_doi_thoai(con, dot_id, d.ma_ho, ngay or datetime.now().strftime('%d/%m/%Y'), dia_diem, d.noi_dung)
            else:
                thay = dict(noi_dung=d.noi_dung)
                if d.loai:
                    thay['loai'] = d.loai
                du_thao.cap_nhat_y_kien(con, dot_id, d.ma_ho, **thay)
                if d.loai in ('khong_dong_y', 'y_kien_khac'):   # giữ V1 nguyên, tạo sẵn nhánh dự thảo để điều chỉnh theo ý kiến
                    from . import phien_ban_pa
                    d.v2 = phien_ban_pa.tao_v2_tu_y_kien(con, d.ma_ho, d.noi_dung)
            n += 1
        csdl.ghi_nhat_ky(con, f'{TEN_MUC.get(muc, muc)}: nhập kết quả từ file', f'Đợt {dot_id}: {n} hộ')
    return n

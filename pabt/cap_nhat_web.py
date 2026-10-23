"""Cập nhật đơn giá, chính sách bồi thường từ trang web. Từ 0.9.49 module này nằm trong bộ cài (nút Tải từ web của bảng giá đất).
(Màn hình quét web riêng đã xóa ở 1.0.27: không còn đường mở từ 0.9.73.)

Quét trang web / tìm trên Công báo thành phố Đồng Nai (quet -> [TaiLieu]: số hiệu, nhóm, đã có trong bộ đơn giá chưa), tải file
(tai_ve: Google Drive / Sheets / Docs, trang HTML có liên kết, nút "Tải tập tin" không đuôi; loại file theo nội dung; quét mã độc).
Đọc, phân tích, áp dụng dùng nhap_don_gia (doc_bang_ocr, phan_tich_van_ban, nhan_muc, so_khop, ap_dung).
"""
from __future__ import annotations
import re
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path

from .lap_pa import LoiNhap, bo_dau
from .nhap_don_gia import _RE_SO_TRONG, DUOI_LIEN_KET, da_co, loai_that, nhom_theo_chu, van_ban_da_co

# ---------------------------------------------------------------- tải từ trang web
# chữ của liên kết / nút tải (không dấu): trang cổng thông tin hay để "Tải về" trỏ tới download.aspx?id=... không có đuôi file
_CHU_TAI = re.compile(r'\b(tai ve|tai xuong|tai file|tai tep|tai tap tin|tap tin|download|dinh kem|tep dinh kem|file dinh kem|'
                      r'van ban goc)\b')
_TEN_FILE_TRONG_CHU = re.compile(r'\.(docx?|xlsx?|xlsm|pdf|csv)\b', re.I)   # "Tải tập tin : 48-2025-qd.doc"
# thuộc tính có thể chứa đường dẫn file (ngoài href): khung xem PDF, nút tải dựng bằng JavaScript
_THUOC_TINH = ('href', 'src', 'data', 'data-href', 'data-url', 'data-src', 'data-file', 'data-link', 'data-download')
_RE_URL_FILE = re.compile(r'''["'(=]\s*((?:https?:)?[^"'\s<>()]*?\.(?:xlsx|xlsm|xls|docx|doc|pdf|csv)(?:\?[^"'\s<>()]*)?)\s*["')]''',
                          re.I)


class _Link(HTMLParser):
    """Các (chữ, đường dẫn) trên trang: thẻ <a> (cả chữ bên trong), khung <iframe>/<embed>/<object>, thuộc tính data-*."""

    def __init__(self):
        super().__init__()
        self.ds, self._href, self._chu = [], None, []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == 'a':
            self._href, self._chu = a.get('href') or a.get('data-href') or a.get('data-url'), []
            if a.get('title'):
                self._chu.append(a['title'] + ' ')
            return
        for k in _THUOC_TINH:
            if a.get(k) and (tag in ('iframe', 'embed', 'object', 'source') or k.startswith('data-')):
                self.ds.append((a.get('title') or a.get('aria-label') or '', a[k]))

    def handle_data(self, data):
        if self._href is not None:
            self._chu.append(data)

    def handle_endtag(self, tag):
        if tag == 'a' and self._href:
            self.ds.append((' '.join(''.join(self._chu).split()), self._href))
            self._href = None


def _mo(url: str, timeout: int = 60):
    from . import an_toan
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) PABT',
                                               'Accept': '*/*', 'Accept-Language': 'vi,en;q=0.8'})
    # HTTPS: bắt buộc chứng chỉ hợp lệ, đúng tên máy chủ, TLS >= 1.2 (an_toan.ngu_canh_tls)
    try:
        return urllib.request.urlopen(req, timeout=timeout, context=an_toan.ngu_canh_tls())
    except urllib.error.URLError as e:
        # CA gốc chưa có trong kho Windows (Windows tải khi chính nó kiểm chứng chỉ): nạp rồi thử lại, vẫn xác minh đầy đủ
        if isinstance(e, urllib.error.HTTPError) or not an_toan.la_loi_chung_chi(e) or not an_toan.nap_goc_ca_windows(url):
            raise
    return urllib.request.urlopen(req, timeout=timeout, context=an_toan.ngu_canh_tls())


TOI_DA_TAI = 200 * 2 ** 20          # file tải về tối đa 200 MB (văn bản đơn giá chỉ vài MB)


def _duoi(url: str) -> str:
    """Đuôi file của đường dẫn: phần đường dẫn, không có thì tên file trong tham số (download.aspx?file=bang_gia.pdf)."""
    u = urllib.parse.urlparse(url)
    d = Path(urllib.parse.unquote(u.path)).suffix.lower()
    if d in DUOI_LIEN_KET:
        return d
    for _, gt in urllib.parse.parse_qsl(u.query):
        d2 = Path(gt).suffix.lower()
        if d2 in DUOI_LIEN_KET:
            return d2
    return d


def _google(url: str) -> str:
    """Đường dẫn Google Drive / Docs / Sheets dùng để xem -> đường dẫn tải được bằng phần mềm."""
    m = (re.search(r'drive\.google\.com/file/d/([\w-]+)', url) or re.search(r'drive\.google\.com/(?:open|uc)\?(?:.*&)?id=([\w-]+)', url))
    if m:
        return f'https://drive.usercontent.google.com/download?id={m.group(1)}&export=download&confirm=t'
    m = re.search(r'docs\.google\.com/spreadsheets/d/([\w-]+)', url)
    if m:
        return f'https://docs.google.com/spreadsheets/d/{m.group(1)}/export?format=xlsx'
    m = re.search(r'docs\.google\.com/document/d/([\w-]+)', url)
    if m:
        return f'https://docs.google.com/document/d/{m.group(1)}/export?format=docx'
    m = re.search(r'drive\.google\.com/drive/(?:u/\d+/)?folders/([\w-]+)', url)
    if m:                                               # trang thư mục dựng bằng JavaScript; bản "nhúng" có sẵn liên kết
        return f'https://drive.google.com/embeddedfolderview?id={m.group(1)}#list'
    return url


def _la_lien_ket_file(dich: str, chu: str) -> bool:
    if _duoi(dich) in DUOI_LIEN_KET:
        return True
    if re.search(r'drive\.google\.com/(file/d/|open\?|uc\?)|docs\.google\.com/(spreadsheets|document)/d/', dich):
        return True
    if dich.lower().startswith(('javascript:', 'mailto:', '#')):
        return False
    return bool(_CHU_TAI.search(bo_dau(chu)) or _TEN_FILE_TRONG_CHU.search(chu or ''))


def lien_ket_file(html: str, url: str) -> list:
    """[(chữ, đường dẫn đầy đủ)] các file đơn giá trên trang web (không trùng, giữ thứ tự)."""
    p = _Link()
    p.feed(html)
    ung_vien = list(p.ds) + [('', m.group(1)) for m in _RE_URL_FILE.finditer(html)]   # đường dẫn trong mã JavaScript
    ds, da = [], set()
    for chu, href in ung_vien:
        href = (href or '').strip().replace('\\/', '/').replace('&amp;', '&')
        if not href or href.startswith('#'):
            continue
        dich = urllib.parse.urljoin(url, href)
        if not dich.lower().startswith(('http://', 'https://')) or not _la_lien_ket_file(dich, chu):
            continue
        khoa = dich.split('#')[0]
        if khoa in da:
            # cùng file: giữ chữ dễ đọc hơn (liên kết có chữ thay cho đường dẫn tìm trong mã)
            ds = [(c or chu, u) if u.split('#')[0] == khoa else (c, u) for c, u in ds]
            continue
        da.add(khoa)
        ten = chu or Path(urllib.parse.unquote(urllib.parse.urlparse(dich).path)).name or dich
        ds.append((ten, dich))
    return ds


def _lay(url: str, timeout: int = 60, file_ra=None, chi_html: bool = False) -> tuple:
    """Tải một đường dẫn: (nội dung, đường dẫn thật sau chuyển hướng, Content-Type, tên file, bảng mã). Lỗi -> LoiNhap.
    file_ra: ghi thẳng ra file từng khối 64 KB (nội dung trả về None) - không giữ cả file trong bộ nhớ (Python 32-bit).
    chi_html: chỉ cần trang web - máy chủ báo không phải HTML thì không tải phần thân (nội dung b'')."""
    try:
        r = _mo(url, timeout)
        try:
            loai = r.headers.get('Content-Type', '')
            ten = r.headers.get_filename() or Path(urllib.parse.unquote(urllib.parse.urlparse(r.geturl()).path)).name
            try:
                dai = int(r.headers.get('Content-Length') or 0)
            except ValueError:
                dai = 0
            qua_lon = f'File tải về lớn hơn {TOI_DA_TAI // 2 ** 20} MB: không phải văn bản đơn giá, đã dừng tải.'
            if dai > TOI_DA_TAI:
                raise LoiNhap(qua_lon)
            if chi_html and loai and 'html' not in loai.lower():
                return b'', r.geturl(), loai, ten, r.headers.get_content_charset()
            if file_ra is not None:
                n = 0
                with open(file_ra, 'wb') as f:
                    while True:
                        khoi = r.read(65536)
                        if not khoi:
                            break
                        n += len(khoi)
                        if n > TOI_DA_TAI:
                            raise LoiNhap(qua_lon)
                        f.write(khoi)
                return None, r.geturl(), loai, ten, r.headers.get_content_charset()
            du = r.read(TOI_DA_TAI + 1)
            if len(du) > TOI_DA_TAI:
                raise LoiNhap(qua_lon)
            return du, r.geturl(), loai, ten, r.headers.get_content_charset()
        finally:
            r.close()
    except LoiNhap:
        raise
    except urllib.error.HTTPError as e:
        e.close()
        goi_y = {401: 'cần đăng nhập', 403: 'không có quyền xem (file chưa chia sẻ công khai?)', 404: 'không có trang / file này',
                 429: 'máy chủ tạm chặn vì truy cập nhiều'}.get(e.code, '')
        raise LoiNhap(f'Không mở được đường dẫn: máy chủ trả lỗi {e.code}' + (f' - {goi_y}' if goi_y else '') + '.') from None
    except Exception as e:
        tb = str(getattr(e, 'reason', e))
        if 'CERTIFICATE' in tb.upper():
            tb += ('\n\nTrang web có chứng chỉ bảo mật không hợp lệ / thiếu. Mở trang bằng trình duyệt, tải file về máy rồi dùng '
                   '"Cập nhật bộ đơn giá từ file…".')
        raise LoiNhap(f'Không mở được đường dẫn:\n{tb}') from None


# ---------------------------------------------------------------- quét trang web tìm văn bản đơn giá, chính sách bồi thường
CONG_BAO_DONG_NAI = 'https://congbao.dongnai.gov.vn/vi/seek/?q='
# nơi tìm theo từ khóa: mã -> (tên, mẫu đường dẫn, {q} = từ khóa đã mã hóa). Trang đổi cấu trúc thì sửa / thêm bằng file
# nguon_web.json trong thư mục dữ liệu máy (%APPDATA%\PABT): {"tim": {"mã": ["tên", "mẫu {q}"]}, "goi_y": [["tên", "nguồn"]]}
NOI_TIM = {
    'dongnai': ('Công báo thành phố Đồng Nai (UBND, HĐND thành phố)', CONG_BAO_DONG_NAI + '{q}'),
    'vbpl': ('Cơ sở dữ liệu quốc gia về văn bản pháp luật - vbpl.vn (Quốc hội, Chính phủ, Bộ ngành, địa phương)',
             'https://vbpl.vn/pages/vbpq-timkiem.aspx?type=0&s=1&SearchIn=Title,Title1&Keyword={q}'),
    'tvpl': ('Thư viện pháp luật - thuvienphapluat.vn', 'https://thuvienphapluat.vn/page/tim-van-ban.aspx?keyword={q}&match=True&area=0'),
}
# nguồn gợi ý: (tên hiện trên ô chọn, nguồn). Nguồn: "mã|từ khóa" (tìm trên NOI_TIM), từ khóa trơn (Công báo Đồng Nai) hoặc
# đường dẫn trang web (trang danh sách văn bản mới: phần mềm quét các văn bản liên quan bồi thường, hỗ trợ, tái định cư)
NGUON_GOI_Y = [
    ('Công báo Đồng Nai: đơn giá bồi thường (cây trồng, vật nuôi, nhà, công trình)', 'đơn giá bồi thường'),
    ('Công báo Đồng Nai: bồi thường, hỗ trợ, tái định cư khi thu hồi đất', 'bồi thường, hỗ trợ, tái định cư'),
    ('Công báo Đồng Nai: bảng giá đất, hệ số điều chỉnh giá đất', 'giá đất'),
    ('Trung ương - CSDL quốc gia văn bản pháp luật (vbpl.vn): bồi thường, hỗ trợ, tái định cư',
     'vbpl|bồi thường, hỗ trợ, tái định cư'),
    ('Trung ương - CSDL quốc gia văn bản pháp luật (vbpl.vn): thu hồi đất', 'vbpl|thu hồi đất'),
    ('Trung ương - CSDL quốc gia văn bản pháp luật (vbpl.vn): Luật Đất đai, giá đất', 'vbpl|đất đai'),
    ('Chính phủ - Hệ thống văn bản (vanban.chinhphu.vn): văn bản mới ban hành', 'https://vanban.chinhphu.vn/'),
    ('Chính phủ - Công báo (congbao.chinhphu.vn): văn bản mới đăng công báo', 'https://congbao.chinhphu.vn/'),
    ('Thư viện pháp luật: bồi thường, hỗ trợ, tái định cư', 'tvpl|bồi thường, hỗ trợ, tái định cư'),
    ('Thư viện pháp luật: thu hồi đất', 'tvpl|thu hồi đất'),
]


def _cau_hinh() -> dict:
    """nguon_web.json trong thư mục dữ liệu máy (không có / hỏng -> {})."""
    import json
    import os
    goc = os.environ.get('PABT_THU_MUC_MAY') or Path(os.environ.get('APPDATA') or Path.home()) / 'PABT'
    try:
        d = json.loads((Path(goc) / 'nguon_web.json').read_text(encoding='utf-8-sig'))
        return d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


def noi_tim() -> dict:
    """NOI_TIM + nơi tìm thêm / sửa trong nguon_web.json (mẫu phải là https và có {q})."""
    ds = dict(NOI_TIM)
    for k, v in (_cau_hinh().get('tim') or {}).items():
        if isinstance(v, (list, tuple)) and len(v) == 2 and str(v[1]).lower().startswith('https://') and '{q}' in str(v[1]):
            ds[str(k)] = (str(v[0]), str(v[1]))
    return ds


def nguon_goi_y() -> list:
    """NGUON_GOI_Y + nguồn thêm trong nguon_web.json."""
    ds = list(NGUON_GOI_Y)
    for v in _cau_hinh().get('goi_y') or []:
        if isinstance(v, (list, tuple)) and len(v) == 2 and all(isinstance(x, str) and x.strip() for x in v) \
                and not any(v[0] == t for t, _ in ds):
            ds.append((v[0].strip(), v[1].strip()))
    return ds


def duong_dan(nguon: str, noi: str = 'dongnai') -> str:
    """Nguồn -> đường dẫn trang cần quét: đường dẫn giữ nguyên; "mã|từ khóa" tìm trên nơi tìm có mã đó; từ khóa trơn tìm trên
    nơi tìm noi (mặc định Công báo Đồng Nai)."""
    nguon = nguon.strip()
    if re.match(r'^https?://', nguon, re.I):
        return nguon
    ds = noi_tim()
    m = re.match(r'^(\w+)\|(.*)$', nguon, re.S)
    if m and m.group(1) in ds:
        noi, nguon = m.group(1), m.group(2).strip()
    mau = ds.get(noi, ds['dongnai'])[1]
    return mau.replace('{q}', urllib.parse.quote_plus(nguon))
TEN_NHOM_VB = {2: 'Nhà, công trình', 3: 'Cây trồng, vật nuôi', 7: 'Vật nuôi, thủy sản', 4: 'Chính sách hỗ trợ', 1: 'Giá đất',
               0: 'Khác'}
_DIEM = ((r'don gia', 3), (r'boi thuong', 3), (r'tai dinh cu', 2), (r'thu hoi dat', 2), (r'\bho tro\b', 1),
         (r'cay trong|vat nuoi|thuy san|cong trinh xay dung|vat kien truc|nha o', 2), (r'gia dat|he so dieu chinh', 2),
         (r'dong nai', 1), (r'quyet dinh|nghi quyet|nghi dinh|thong tu|\bluat\b', 1),
         (r'dat dai|giai phong mat bang', 2), (r'luat dat dai', 2))
_TRU = r'tuyen dung|dau thau|lich cong tac|ho chieu|bien che|van tai|to chuc va hoat dong|thi dua|khen thuong|hoc phi|y te'


@dataclass
class TaiLieu:
    ten: str                    # tên văn bản (tiêu đề trang / chữ liên kết)
    url: str                    # đường dẫn tải file
    tep: str = ''               # tên file (chữ của nút tải)
    trang: str = ''             # trang chứa liên kết
    so_hieu: str = ''
    nhom: int = 0               # TEN_NHOM_VB
    diem: int = 0               # mức liên quan tới đơn giá / chính sách bồi thường
    da_co: bool = False         # số hiệu đã có trong danh mục văn bản căn cứ của bộ đơn giá
    chon: bool = False


def cham_diem(chu: str) -> tuple:
    """(điểm liên quan, nhóm) của một tên văn bản / liên kết."""
    k = bo_dau(chu)
    d = sum(s for mau, s in _DIEM if re.search(mau, k))
    if re.search(_TRU, k):
        d -= 6
    nhom = nhom_theo_chu(chu)
    if not nhom and re.search(r'thu hoi dat|boi thuong|tai dinh cu|giai phong mat bang|luat dat dai', k):
        nhom = 4                                        # luật, nghị định, thông tư về bồi thường, hỗ trợ, TĐC: theo dõi văn bản
    if re.search(r'gia dat|he so dieu chinh', k) and not re.search(r'cay trong|vat nuoi|cong trinh|don gia boi thuong', k):
        nhom = 1
    return d, nhom


def _tieu_de(html: str) -> str:
    import html as h
    m = re.search(r'<title[^>]*>(.*?)</title>', html, re.S | re.I)
    return ' '.join(h.unescape(m.group(1)).split()) if m else ''


def _html(du: bytes, bang_ma) -> str:
    return du.decode(bang_ma or 'utf-8', errors='replace')


def quet(nguon: str, toi_da_trang: int = 20, bao=None, noi: str = 'dongnai') -> list:
    """Quét một trang web (hoặc từ khóa: tìm trên nơi tìm noi / "mã|từ khóa", mặc định Công báo Đồng Nai) -> [TaiLieu] các
    file văn bản, xếp theo mức liên quan.
    Đi thêm một tầng: trang chi tiết văn bản (cùng máy chủ, tên liên quan bồi thường / đơn giá) để lấy file đính kèm.
    bao(i, n, chữ) báo tiến độ, trả True để dừng."""
    nguon = nguon.strip()
    if not nguon:
        raise LoiNhap('Nhập đường dẫn trang web hoặc từ khóa cần tìm.')
    # tìm theo số hiệu ("31/2025", "31/2025/QĐ-UBND"): trang văn bản mang đúng số đó luôn được mở, kể cả khi tiêu đề chung chung
    # ("Quyết định số 31/2025/QĐ-UBND của Ủy ban nhân dân tỉnh" - điểm liên quan thấp)
    m_so = None if re.match(r'^https?://', nguon, re.I) else re.search(r'(?<!\d)(\d+[a-zA-Z]?)\s*/\s*(\d{4})(?!\d)', nguon)
    so_tim = re.compile(rf'(?<!\d){m_so.group(1)}\s*/\s*{m_so.group(2)}(?!\d)', re.I) if m_so else None
    nguon = duong_dan(nguon, noi)
    url = _google(nguon)
    du, that_url, loai, ten, bang_ma = _lay(url, 30, chi_html=True)   # đường dẫn thẳng tới file: không tải cả file ở bước quét
    kq = []
    if not ('html' in loai.lower() or du.lstrip()[:200].lower().startswith((b'<!doctype', b'<html'))):
        kq.append(TaiLieu(ten=ten or url, url=nguon, tep=ten))         # đường dẫn thẳng tới file
    else:
        html = _html(du, bang_ma)
        tieu = _tieu_de(html)
        kq += [TaiLieu(ten=c, url=u, tep=c, trang=that_url) for c, u in lien_ket_file(html, that_url)]
        p = _Link()
        p.feed(html)
        may = urllib.parse.urlparse(that_url).netloc
        file_url = {t.url for t in kq}
        trang, da = [], {that_url.split('#')[0]}
        for c, h in p.ds:
            dich = urllib.parse.urljoin(that_url, (h or '').strip()).split('#')[0]
            if urllib.parse.urlparse(dich).netloc != may or dich in da or dich in file_url or not c:
                continue
            da.add(dich)
            diem, _ = cham_diem(c)
            if so_tim and so_tim.search(c):
                diem = max(diem, 5)
            if diem >= 5:
                trang.append((diem, c, dich))
        trang.sort(key=lambda x: -x[0])
        trang = trang[:toi_da_trang]
        for i, (_, c, dich) in enumerate(trang, start=1):
            if bao and bao(i, len(trang), c):
                break
            try:
                du2, u2, loai2, ten2, bm2 = _lay(dich, 30, chi_html=True)     # liên kết là file: không tải cả file chỉ để xem loại
            except LoiNhap:
                continue
            if 'html' not in loai2.lower():
                kq.append(TaiLieu(ten=c, url=dich, tep=ten2, trang=that_url))
                continue
            h2 = _html(du2, bm2)
            ten_vb = _tieu_de(h2) or c
            if len(c) > len(ten_vb) or bo_dau(ten_vb) in bo_dau(tieu):  # tiêu đề trang chung chung: dùng chữ liên kết
                ten_vb = c
            kq += [TaiLieu(ten=ten_vb, url=u, tep=t, trang=u2) for t, u in lien_ket_file(h2, u2)]
    # gộp trùng, chấm điểm, đối chiếu danh mục văn bản đã có
    try:
        co = van_ban_da_co()
    except Exception:                                   # bộ đơn giá không đọc được: không đối chiếu
        co = []
    ds, da = [], set()
    for t in kq:
        if t.url in da:
            continue
        da.add(t.url)
        mt = re.search(r'[\w.()-]+\.(?:docx?|xlsx?|xlsm|pdf|csv)\b', t.tep or '', re.I)
        if mt:                                          # "Tải tập tin 48-2025-qd.doc Tải tập tin : ..." -> "48-2025-qd.doc"
            t.tep = mt.group(0)
        m = _RE_SO_TRONG.search(t.ten) or _RE_SO_TRONG.search(t.tep)
        t.so_hieu = re.sub(r'\s+', '', m.group(1)) if m else ''
        t.diem, t.nhom = cham_diem(f'{t.ten} {t.tep}')
        t.da_co = da_co(t.so_hieu, co)
        t.chon = t.diem >= 5 and not t.da_co and t.nhom in (2, 3, 4, 7)
        ds.append(t)
    ds.sort(key=lambda t: (not t.chon, -t.diem))
    return ds


def tai_ve(url: str, thu_muc) -> dict:
    """Mở đường dẫn. Là file đơn giá -> tải về: dict(file=...). Là trang web -> dict(lien_ket=[(chữ, url)]) các file
    đơn giá tìm thấy trên trang (Excel, Word, PDF...). Đường dẫn Google Drive (file, thư mục), Google Sheets / Docs được
    đổi sang đường dẫn tải trực tiếp. Loại file xác định theo nội dung tải về (không tin đuôi / Content-Type)."""
    url = url.strip()
    if not re.match(r'^https?://', url, re.I):
        raise LoiNhap('Nhập đường dẫn bắt đầu bằng http:// hoặc https://')
    goc, url = url, _google(url)
    tam = Path(thu_muc) / f'_dang_tai_{abs(hash(url))}'
    try:
        _, that_url, loai, ten, bang_ma = _lay(url, file_ra=tam)     # ghi thẳng ra file, không giữ trong bộ nhớ
    except BaseException:
        if tam.exists():
            tam.unlink()
        raise
    f = Path(thu_muc) / (re.sub(r'[\\/:*?"<>|]+', '_', ten) or 'don_gia')
    if f.exists():
        f.unlink()
    tam.replace(f)
    that = loai_that(f)
    if that == '.html' or (not that and 'html' in loai.lower()):
        du = f.read_bytes()
        ds = [x for x in lien_ket_file(du.decode(bang_ma or 'utf-8', errors='replace'), that_url)
              if x[1].split('#')[0] not in (url.split('#')[0], goc.split('#')[0])]
        f.unlink()
        if not ds:
            if 'google.com' in that_url:
                raise LoiNhap('Google Drive không cho tải file này: chia sẻ file / thư mục ở chế độ "Bất kỳ ai có đường liên kết" '
                              'rồi thử lại.')
            raise LoiNhap('Trang web không có liên kết tới file đơn giá (Excel, Word, PDF) mà phần mềm đọc được: trang có thể tạo '
                          'liên kết bằng JavaScript hoặc cần đăng nhập.\n\nCách khác: mở trang bằng trình duyệt, bấm chuột phải '
                          'vào nút / liên kết tải file -> "Sao chép địa chỉ liên kết" rồi dán vào đây; hoặc tải file về máy rồi '
                          'dùng "Cập nhật bộ đơn giá từ file…".')
        return dict(lien_ket=ds)
    if that and that != '.html' and f.suffix.lower() != that and not (that == '.xlsx' and f.suffix.lower() == '.xlsm'):
        f = f.replace(f.with_name(f.stem + that))      # tên tải về không có đuôi / sai đuôi: đặt theo nội dung
    elif not f.suffix:
        d = {'pdf': '.pdf', 'sheet': '.xlsx', 'word': '.docx', 'csv': '.csv'}.get(
            next((k for k in ('pdf', 'sheet', 'word', 'csv') if k in loai), ''), '')
        if d:
            f = f.replace(f.with_name(f.name + d))
    return dict(file=str(f))

"""Nguồn bảng giá đất của 34 tỉnh, thành phố (0.9.65, người dùng 12/10/2026: lấy giá đất mọi xã / phường trên cả nước).

Khảo sát thật 12/10/2026 (ket_qua_kiem_tra/GiaDat_NguonWeb_0.9.65.md):
  - KHÔNG có cơ sở dữ liệu giá đất quốc gia công khai, đọc được bằng máy. Mỗi tỉnh ban hành nghị quyết HĐND riêng (Luật Đất
    đai 2024, bảng giá đất lần đầu áp dụng từ 01/01/2026), phụ lục Word / PDF / Excel, mỗi tỉnh một kiểu bảng.
  - Công báo tỉnh: chỉ Đồng Nai, Tây Ninh dùng chung nền tảng tìm kiếm `/vi/seek/`; các tỉnh khác nền tảng khác / 404.
  - vbpl.vn (CSDL quốc gia): trang mới dùng Next.js Server Actions (mã hành động đổi mỗi lần triển khai) - không có API ổn định.
  - Doanh nghiệp: thuvienphapluat.vn chặn truy cập tự động (403), thuviennhadat.vn (500); guland.vn có bảng theo tỉnh -> xã ->
    tuyến đường (Vị trí 1-4, đồng/m²) cho 9 tỉnh, ghi rõ "không cấu thành tư vấn pháp lý" -> chỉ là giá THAM KHẢO.
Nên: (1) danh bạ đường dẫn văn bản chính thức theo tỉnh - người dùng dán một lần, phần mềm nhớ (`ghi_danh_ba`), dùng chung qua
file `danh_ba_gia_dat.json` trong thư mục máy; (2) tìm Công báo / vbpl; (3) Guland tham khảo (`doc_guland`), có nhãn trong căn cứ.
"""
from __future__ import annotations

import json
import re
import time
from pathlib import Path

from .lap_pa import bo_dau

# 34 tỉnh, thành phố từ 01/07/2025 (Nghị quyết 202/2025/QH15): (tên, các tỉnh cũ nhập vào)
TINH = (
    ('Hà Nội', ()), ('Huế', ('Thừa Thiên Huế',)), ('Lai Châu', ()), ('Điện Biên', ()), ('Sơn La', ()), ('Lạng Sơn', ()),
    ('Quảng Ninh', ()), ('Thanh Hóa', ()), ('Nghệ An', ()), ('Hà Tĩnh', ()), ('Cao Bằng', ()),
    ('Tuyên Quang', ('Hà Giang',)), ('Lào Cai', ('Yên Bái',)), ('Thái Nguyên', ('Bắc Kạn',)),
    ('Phú Thọ', ('Vĩnh Phúc', 'Hòa Bình')), ('Bắc Ninh', ('Bắc Giang',)), ('Hưng Yên', ('Thái Bình',)),
    ('Hải Phòng', ('Hải Dương',)), ('Ninh Bình', ('Hà Nam', 'Nam Định')), ('Quảng Trị', ('Quảng Bình',)),
    ('Đà Nẵng', ('Quảng Nam',)), ('Quảng Ngãi', ('Kon Tum',)), ('Gia Lai', ('Bình Định',)), ('Khánh Hòa', ('Ninh Thuận',)),
    ('Lâm Đồng', ('Đắk Nông', 'Bình Thuận')), ('Đắk Lắk', ('Phú Yên',)),
    ('Hồ Chí Minh', ('Bình Dương', 'Bà Rịa - Vũng Tàu', 'Bà Rịa Vũng Tàu', 'Vũng Tàu')),
    ('Đồng Nai', ('Bình Phước',)), ('Tây Ninh', ('Long An',)), ('Cần Thơ', ('Sóc Trăng', 'Hậu Giang')),
    ('Vĩnh Long', ('Bến Tre', 'Trà Vinh')), ('Đồng Tháp', ('Tiền Giang',)), ('Cà Mau', ('Bạc Liêu',)),
    ('An Giang', ('Kiên Giang',)),
)
# đường dẫn guland.vn/bang-gia-dat/<mã> - tỉnh có bảng giá trên Guland (đọc ô chọn tỉnh của trang, 12/10/2026)
GULAND = {'Hà Nội': 'ha-noi', 'Hồ Chí Minh': 'tp-ho-chi-minh', 'Đà Nẵng': 'da-nang', 'Hải Phòng': 'hai-phong', 'Cà Mau': 'ca-mau',
          'Thái Nguyên': 'thai-nguyen', 'Thanh Hóa': 'thanh-hoa', 'Tây Ninh': 'tay-ninh', 'Lai Châu': 'lai-chau'}
GULAND_GOC = 'https://guland.vn/bang-gia-dat/'
GULAND_TOI_DA_TRANG = 40           # một xã ~1-10 trang (mỗi trang ~50 dòng); dừng khi trang không thêm dòng mới
GULAND_NGHI = 0.4                  # giây nghỉ giữa hai trang - truy cập lịch sự, không dồn máy chủ
NHAN_THAM_KHAO = 'Giá THAM KHẢO từ guland.vn (doanh nghiệp) - chưa phải căn cứ pháp lý, đối chiếu nghị quyết bảng giá đất của tỉnh'
# danh bạ chính thức gắn sẵn (đã thử mở được). Tỉnh khác: người dùng dán đường dẫn một lần -> ghi_danh_ba
DANH_BA_GAN_SAN = {
    'Đồng Nai': dict(van_ban='Nghị quyết 28/2025/NQ-HĐND ngày 10/12/2025 của HĐND tỉnh Đồng Nai', url=[
        'https://congbao.dongnai.gov.vn/vi/vanban/detail/'
        'Nghi-quyet-so-28-2025-NQ-HDND-Ban-hanh-Quy-dinh-Bang-gia-dat-lan-dau-tren-dia-ban-tinh-Dong-Nai-nam-2026-9508/']),
}
TEN_FILE_DANH_BA = 'danh_ba_gia_dat.json'


def _khoa(s: str) -> str:
    t = bo_dau(s or '').lower()
    t = re.sub(r'^(tinh|thanh pho|tp\.?)\s+', '', t.strip())
    return re.sub(r'[^a-z0-9]+', '', t)


def chuan_tinh(ten: str) -> str:
    """Tên tỉnh người dùng gõ (kể cả tỉnh cũ trước sắp xếp, "TP.HCM", không dấu) -> tên tỉnh hiện hành, '' nếu không nhận ra."""
    k = _khoa(ten)
    if not k:
        return ''
    if k in ('hcm', 'tphcm', 'saigon', 'hochiminh'):
        return 'Hồ Chí Minh'
    for moi, cu in TINH:
        if k == _khoa(moi) or any(k == _khoa(x) for x in cu):
            return moi
    return ''


def tinh_cu(ten: str) -> tuple:
    """Các tỉnh cũ đã nhập vào tỉnh này (từ khóa tìm văn bản cũ / tên địa bàn trong phụ lục)."""
    moi = chuan_tinh(ten)
    return next((cu for t, cu in TINH if t == moi), ())


# ---------------------------------------------------------------- danh bạ đường dẫn văn bản chính thức (người dùng dán một lần)
def file_danh_ba() -> Path:
    from .may_chu import thu_muc_may
    return thu_muc_may() / TEN_FILE_DANH_BA


def doc_danh_ba() -> dict:
    """{tỉnh: {van_ban, url: [...]}} = gắn sẵn + file trong thư mục máy (file thắng)."""
    kq = {k: dict(v, url=list(v['url'])) for k, v in DANH_BA_GAN_SAN.items()}
    try:
        du = json.loads(file_danh_ba().read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return kq
    for k, v in (du.items() if isinstance(du, dict) else ()):
        t = chuan_tinh(k) or k
        if isinstance(v, dict) and isinstance(v.get('url'), list):
            cu = kq.get(t, dict(van_ban='', url=[]))
            url = list(dict.fromkeys([str(u) for u in v['url'] if str(u).startswith('https://')] + cu['url']))
            kq[t] = dict(van_ban=str(v.get('van_ban') or cu['van_ban']), url=url)
    return kq


def ghi_danh_ba(tinh: str, url: str, van_ban: str = '') -> None:
    """Nhớ đường dẫn văn bản / phụ lục đã đọc được giá của tỉnh (đầu danh sách). Chỉ https."""
    t = chuan_tinh(tinh) or (tinh or '').strip()
    if not t or not str(url).startswith('https://'):
        return
    f = file_danh_ba()
    try:
        du = json.loads(f.read_text(encoding='utf-8'))
        if not isinstance(du, dict):
            du = {}
    except (OSError, ValueError):
        du = {}
    cu = du.get(t) if isinstance(du.get(t), dict) else {}
    ds = [str(url)] + [u for u in cu.get('url', []) if u != url]
    du[t] = dict(van_ban=van_ban or cu.get('van_ban', ''), url=ds[:10], cap_nhat=time.strftime('%d/%m/%Y'))
    f.parent.mkdir(parents=True, exist_ok=True)
    tam = f.with_suffix('.tmp')
    tam.write_text(json.dumps(du, ensure_ascii=False, indent=1), encoding='utf-8')
    import os
    os.replace(tam, f)


def url_danh_ba(tinh: str) -> tuple:
    """(văn bản, [đường dẫn]) của tỉnh trong danh bạ."""
    d = doc_danh_ba().get(chuan_tinh(tinh) or tinh, {})
    return d.get('van_ban', ''), list(d.get('url', []))


# ---------------------------------------------------------------- guland.vn (tham khảo)
def _slug(ten: str) -> str:
    return re.sub(r'[^a-z0-9]+', '-', bo_dau(ten or '').lower()).strip('-')


def _chu_o(o: str) -> str:
    import html
    return ' '.join(html.unescape(re.sub(r'<[^>]+>', ' ', o)).split())


def _tim_trang_xa(html_tinh: str, ma_tinh: str, xa: str) -> str:
    """Đường dẫn trang xã / phường trong trang tỉnh của Guland (khớp tên không dấu, bỏ "xã / phường")."""
    from .cap_nhat_gia_dat import ten_gon
    muc = _slug(ten_gon(xa))
    if not muc:
        return ''
    ds = dict.fromkeys(re.findall(r'href="(?:https://guland\.vn)?/bang-gia-dat/%s/([a-z0-9-]+)"' % re.escape(ma_tinh), html_tinh))
    khop = [m for m in ds if re.sub(r'^(xa|phuong|thi-tran|dac-khu)-', '', m) == muc]
    if not khop:
        khop = [m for m in ds if m.endswith('-' + muc) or m == muc]
    return f'{GULAND_GOC}{ma_tinh}/{khop[0]}' if khop else ''


def phan_tich_guland(html_trang: str) -> list:
    """Bảng của một trang xã: [(địa bàn, tên đường / đoạn, loại đất, [giá VT1..VT4 đồng/m²])]."""
    i = html_trang.find('<table')
    j = html_trang.find('</table>', i)
    if i < 0 or j < 0:
        return []
    ra = []
    for tr in re.findall(r'<tr[^>]*>(.*?)</tr>', html_trang[i:j], re.S):
        o = [_chu_o(x) for x in re.findall(r'<td[^>]*>(.*?)</td>', tr, re.S)]
        if len(o) < 4:
            continue
        gia = []
        for x in o[3:7]:
            so = re.sub(r'[^\d]', '', x)
            gia.append(int(so) if so else 0)
        if not any(gia):
            continue
        ra.append((o[0], o[1], o[2], gia))
    return ra


def _loai_cot(loai: str):
    from .cap_nhat_gia_dat import _loai_gia
    k = _loai_gia(loai)
    if k:
        return k
    b = bo_dau(loai)
    if 'nong nghiep' in b or 'trong lua' in b or 'cay' in b:
        return 'nn_cay'
    return None


def doc_guland(tinh: str, xa: str, lay=None, nghi: float = GULAND_NGHI) -> list:
    """Giá tham khảo một xã / phường trên guland.vn -> dòng kiểu bảng giá (giá nghìn đồng/m², vị trí VT1-VT4). [] = không có.
    lay(url) -> html (mặc định cap_nhat_web._lay; test truyền hàm giả)."""
    t = chuan_tinh(tinh)
    ma = GULAND.get(t)
    if not ma:
        return []
    if lay is None:
        from . import cap_nhat_web

        def lay(u):
            du, _that, _loai, _ten, bm = cap_nhat_web._lay(u, 25)
            return cap_nhat_web._html(du or b'', bm)
    from .cap_nhat_gia_dat import ten_gon
    muc = _slug(ten_gon(xa))
    if not muc:
        return []
    # trang tỉnh chỉ liệt kê một phần xã / phường: thử liên kết tìm được trước, rồi đường dẫn dựng theo quy tắc của trang
    try:
        thay = _tim_trang_xa(lay(GULAND_GOC + ma), ma, xa)
    except Exception:                       # noqa: BLE001 - trang tỉnh lỗi: vẫn thử đường dẫn dựng sẵn
        thay = ''
    ung_vien = list(dict.fromkeys([u for u in [thay] if u] +
                                  [f'{GULAND_GOC}{ma}/{tien_to}-{muc}' for tien_to in ('phuong', 'xa', 'dac-khu', 'thi-tran')]))
    trang_xa, dau = '', []
    for u in ung_vien:
        try:
            dau = phan_tich_guland(lay(u))
        except Exception:                   # noqa: BLE001 - 404: không có xã / phường này với tiền tố đó
            dau = []
        if dau:
            trang_xa = u
            break
    if not trang_xa:
        return []
    dong, da = [], set()
    for so in range(1, GULAND_TOI_DA_TRANG + 1):
        u = trang_xa if so == 1 else f'{trang_xa}?page={so}'
        moi = [r for r in (dau if so == 1 else phan_tich_guland(lay(u))) if (r[1], r[2]) not in da]
        if not moi:
            break
        for r in moi:
            da.add((r[1], r[2]))
        dong.extend(moi)
        if nghi:
            time.sleep(nghi)
    return _thanh_dong(dong, t, trang_xa)


def _thanh_dong(dong: list, tinh: str, nguon: str) -> list:
    """Gộp các loại đất cùng tuyến đường thành dòng bảng giá: mỗi tuyến 4 dòng VT1-VT4 (giá nghìn đồng/m²)."""
    from . import gia_dat_nq28 as nq
    gop, thu = {}, []
    for dia_ban, duong, loai, gia in dong:
        cot = _loai_cot(loai)
        if not cot:
            continue
        xa = re.sub(r'^(TP\.|Tỉnh|Thành phố)?\s*' + re.escape(tinh) + r'\s*', '', dia_ban, flags=re.I).strip() or dia_ban
        for k, g in enumerate(gia, 1):
            if not g:
                continue
            khoa = (xa, duong, k)
            r = gop.get(khoa)
            if r is None:
                r = dict(xa=xa, tt=len(thu) // 4 + 1, ten_duong=duong.title() if duong.isupper() else duong, diem_dau='',
                         diem_cuoi='', vi_tri=f'VT{k}', dieu_kien=f'Vị trí {k}', nguong=[1000, 500],
                         trang={'pl3': '', 'pl1': ''}, tham_khao=True, nguon_url=nguon, **{c: 0 for c, _ in nq.COT})
                gop[khoa] = r
                thu.append(khoa)
            if not r.get(cot):
                r[cot] = g // 1000 if g >= 1000 else g
    return [gop[k] for k in thu]

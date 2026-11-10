"""Phân tích văn bản đơn giá bằng AI (Claude) - TÙY CHỌN (1.0.56, người dùng 03/11/2026: "công cụ hiểu như một người thật, phân tích toàn
văn bản… có thể dựa vào công cụ AI để phân tích và phân loại"). Không Qt.

Phần mềm vẫn đọc / so khớp trên máy như cũ (nhap_don_gia + quy_dinh_van_ban); AI chỉ là LỚP KIỂM TRA THỨ HAI:
- đọc TOÀN VĂN văn bản (chữ đã đọc / OCR - không gửi ảnh, không gửi dữ liệu dự án / hộ dân: văn bản đơn giá là văn bản công khai);
- xác minh các dòng phần mềm đánh dấu cần xem (mới, đổi giá, đổi tên, giá bản scan nghi ngờ, khớp gần đúng): tên / ĐVT / đơn giá đúng như
  văn bản không -> 'dung' (giá khớp: bỏ nghi ngờ, chọn sẵn) / 'sai' (AI đọc giá khác: KHÔNG chọn sẵn, ghi giá AI đọc để người dùng đối chiếu)
  / 'khong_thay';
- liệt kê quy định cách tính trong lời văn (bổ sung cho quy định phần mềm đã trích) và quan hệ văn bản (sửa đổi / thay thế).
Không bao giờ tự đổi đơn giá theo AI. Chỉ chạy khi người dùng đã BẬT Trợ lý trực tuyến (tro_ly: khóa API, mô hình); máy không có thư viện
"anthropic" (bản Windows 7) thì không dùng được.
"""
from __future__ import annotations

import json
import re

from .lap_pa import bo_dau

CHU_TOI_DA = 300_000                     # ký tự văn bản gửi đi (dài hơn: cắt, báo)
DONG_XAC_MINH_TOI_DA = 250               # dòng cần xem gửi AI xác minh mỗi lần
GIOI_HAN_GIAY = 300
TOKEN_RA_TOI_DA = 32000

HE_THONG = ('Bạn là chuyên viên pháp chế về bồi thường, hỗ trợ, tái định cư khi Nhà nước thu hồi đất ở Việt Nam. Bạn đọc văn bản quy phạm '
            '(quyết định của UBND tỉnh về đơn giá bồi thường nhà, công trình, vật kiến trúc, cây trồng, vật nuôi, chính sách hỗ trợ) như một '
            'cán bộ thẩm định: đọc cả lời văn các điều khoản lẫn bảng giá, hiểu quan hệ sửa đổi / thay thế giữa các văn bản. Văn bản có thể '
            'là chữ nhận dạng từ bản scan (OCR) nên có lỗi chữ / số: suy luận theo ngữ cảnh nhưng KHÔNG bịa số liệu không có trong văn bản. '
            'Trả lời đúng định dạng JSON được yêu cầu, chữ tiếng Việt có dấu.')

LUOC_DO = {
    'type': 'object',
    'properties': {
        'van_ban': {
            'type': 'object',
            'properties': {
                'so_hieu': {'type': 'string'},
                'ngay': {'type': 'string'},
                'trich_yeu': {'type': 'string'},
                'nhom': {'type': 'array', 'items': {'type': 'integer', 'enum': [2, 3, 4, 7]}},
                'sua_doi_boi': {'type': 'array', 'items': {'type': 'string'}},
                'thay_the': {'type': 'array', 'items': {'type': 'string'}},
            },
            'required': ['so_hieu', 'ngay', 'trich_yeu', 'nhom', 'sua_doi_boi', 'thay_the'],
            'additionalProperties': False,
        },
        'quy_dinh': {
            'type': 'array',
            'items': {
                'type': 'object',
                'properties': {
                    'chu': {'type': 'string'},
                    'nhom': {'type': 'integer', 'enum': [0, 2, 3, 4, 7]},
                    'dieu': {'type': 'string'},
                    'pham_vi': {'type': 'string'},
                },
                'required': ['chu', 'nhom', 'dieu', 'pham_vi'],
                'additionalProperties': False,
            },
        },
        'xac_minh': {
            'type': 'array',
            'items': {
                'type': 'object',
                'properties': {
                    'stt': {'type': 'integer'},
                    'ket_luan': {'type': 'string', 'enum': ['dung', 'sai', 'khong_thay']},
                    'ten': {'type': 'string'},
                    'dvt': {'type': 'string'},
                    'don_gia': {'type': 'integer'},
                    'ghi_chu': {'type': 'string'},
                },
                'required': ['stt', 'ket_luan', 'ten', 'dvt', 'don_gia', 'ghi_chu'],
                'additionalProperties': False,
            },
        },
    },
    'required': ['van_ban', 'quy_dinh', 'xac_minh'],
    'additionalProperties': False,
}


class LoiAI(Exception):
    pass


def dung_duoc() -> tuple:
    """(được dùng?, lý do nếu không)."""
    from . import tro_ly
    if not tro_ly.co_thu_vien():
        return False, 'Máy này chưa có thư viện "anthropic" (bản Windows 10/11): chỉ đọc văn bản trên máy.'
    if not tro_ly.doc_cai_dat().get('bat'):
        return False, 'Trợ lý trực tuyến đang TẮT: bật ở Công cụ > Trợ lý > thẻ Cài đặt (nhập khóa API) để dùng phân tích AI.'
    return True, ''


def chu_van_ban(dong: list) -> tuple:
    """(chữ toàn văn bản - hàng bảng nối ô bằng " | ", đã cắt?)."""
    ra = []
    for r in dong:
        if isinstance(r, str):
            x = ' '.join(r.split())
        else:
            x = ' | '.join(' '.join(str(c).split()) for c in r if str(c or '').strip())
        if x:
            ra.append(x)
    chu = '\n'.join(ra)
    return (chu[:CHU_TOI_DA], True) if len(chu) > CHU_TOI_DA else (chu, False)


def dong_can_xac_minh(ds: list, can_xu_ly) -> list:
    """[(stt, Muc)] các dòng cần xem (theo can_xu_ly của hộp thoại), tối đa DONG_XAC_MINH_TOI_DA; stt = chỉ số trong ds."""
    return [(i, m) for i, m in enumerate(ds) if can_xu_ly(m) and not m.bo_cu and not m.phu][:DONG_XAC_MINH_TOI_DA]


def noi_dung_gui(dong: list, ds: list, can_xu_ly, nhom: int = 0) -> tuple:
    """(chữ gửi đi, số dòng xác minh, đã cắt văn bản?)."""
    chu, cat = chu_van_ban(dong)
    xm = dong_can_xac_minh(ds, can_xu_ly)
    dong_xm = '\n'.join(f'{i}\t{m.ten}\t{m.dvt}\t{m.he_so or m.don_gia}\t{m.trang_thai}'
                        + (f'\tgiá đọc được trên bản scan: "{m.nghi_gia}"' if m.nghi_gia else '') for i, m in xm)
    yeu_cau = (
        'Nhiệm vụ:\n'
        '1. van_ban: số hiệu, ngày ban hành, trích yếu; nhóm tài sản văn bản quy định (2 nhà / công trình / vật kiến trúc, 3 cây trồng, '
        '7 vật nuôi / thủy sản, 4 chính sách hỗ trợ); các văn bản đã sửa đổi, bổ sung văn bản này (bản hợp nhất ghi rõ) và các văn bản bị '
        'văn bản này thay thế / bãi bỏ (số hiệu đầy đủ).\n'
        '2. quy_dinh: MỌI quy định cách tính trong lời văn và ghi chú bảng (mật độ, cây trồng xen, phần vượt mật độ, tỷ lệ %, năm tuổi, '
        'đường kính, trường hợp không bồi thường / chỉ hỗ trợ, chi phí di chuyển, giá trị còn lại, hệ số…) - mỗi quy định một câu đầy đủ ý, '
        'ghi Điều / khoản / điểm (hoặc "Phụ lục …"), nhóm (0 nếu chung) và phạm vi tài sản áp dụng (rỗng nếu chung). Bỏ phần căn cứ, hiệu '
        'lực, tổ chức thực hiện.\n'
        '3. xac_minh: với TỪNG dòng trong danh sách dưới (stt, tên, ĐVT, đơn giá phần mềm đọc, trạng thái), tìm trong văn bản và kết luận: '
        '"dung" nếu tên / ĐVT / đơn giá đúng như văn bản; "sai" nếu văn bản ghi khác (ghi tên, ĐVT, đơn giá ĐÚNG theo văn bản vào các ô); '
        '"khong_thay" nếu không thấy trong văn bản. don_gia là số nguyên đồng (văn bản ghi nghìn đồng thì đổi ra đồng); ghi_chu ngắn gọn lý '
        'do (dòng nào, chữ OCR sai thế nào).\n'
        + (f'\nNhóm đang cập nhật: {nhom}.\n' if nhom else '')
        + ('\nVăn bản dài, chỉ gửi phần đầu.\n' if cat else '')
        + f'\nDANH SÁCH DÒNG CẦN XÁC MINH (stt, tên, ĐVT, đơn giá, trạng thái):\n{dong_xm or "(không có)"}\n'
        + f'\nVĂN BẢN:\n{chu}')
    return yeu_cau, len(xm), cat


def goi_ai(noi_dung: str, khach=None, gioi_han: float = GIOI_HAN_GIAY) -> dict:
    """Gửi tới Claude (cài đặt / khóa của Trợ lý), trả dict theo LUOC_DO. Lỗi -> LoiAI (tiếng Việt)."""
    from . import tro_ly
    cd = tro_ly.doc_cai_dat()
    noi_dung = tro_ly.an_danh(noi_dung)           # 1.0.91: luôn che dữ liệu cá nhân trước khi gửi (CCCD, SĐT, tọa độ, tên chủ hộ đã chụp) - trước đây gửi nguyên
    if khach is None:
        ok, ly_do = dung_duoc()
        if not ok:
            raise LoiAI(ly_do)
        import anthropic
        khoa = tro_ly._khoa_da_luu()
        giay = max(float(gioi_han or GIOI_HAN_GIAY), 10)
        khach = anthropic.Anthropic(api_key=khoa, timeout=giay) if khoa else anthropic.Anthropic(timeout=giay)
        loi_api = (anthropic.APIStatusError, anthropic.APIConnectionError)
    else:
        anthropic, loi_api = None, ()
    try:
        with khach.beta.messages.stream(
                model=cd.get('mo_hinh') or tro_ly.MO_HINH_MAC_DINH, max_tokens=TOKEN_RA_TOI_DA, system=HE_THONG,
                thinking={'type': 'adaptive'},
                output_config={'effort': 'high', 'format': {'type': 'json_schema', 'schema': LUOC_DO}},
                betas=['server-side-fallback-2026-06-01'], fallbacks=[{'model': tro_ly.DU_PHONG}],
                messages=[{'role': 'user', 'content': noi_dung}]) as s:
            tl = s.get_final_message()
    except loi_api as e:
        if anthropic is not None and isinstance(e, anthropic.AuthenticationError):
            raise LoiAI('Khóa API không hợp lệ: nhập lại ở thẻ Cài đặt của cửa sổ Trợ lý.') from None
        if anthropic is not None and isinstance(e, anthropic.RateLimitError):
            raise LoiAI('Gửi quá nhiều yêu cầu: chờ một lát rồi thử lại.') from None
        if anthropic is not None and isinstance(e, anthropic.APIConnectionError):
            raise LoiAI('Không kết nối được máy chủ Anthropic (mất mạng / tường lửa).') from None
        raise LoiAI(f'Máy chủ Anthropic báo lỗi: {getattr(e, "message", e)}') from None
    if getattr(tl, 'stop_reason', None) == 'refusal':
        raise LoiAI('Mô hình từ chối phân tích văn bản này.')
    if getattr(tl, 'stop_reason', None) == 'max_tokens':
        raise LoiAI('Văn bản quá dài cho một lần phân tích (kết quả bị cắt): cập nhật từng phần (từng phụ lục) rồi thử lại.')
    chu = next((b.text for b in tl.content if getattr(b, 'type', '') == 'text'), '')
    try:
        kq = json.loads(chu)
    except ValueError:
        raise LoiAI('Kết quả AI không đúng định dạng.') from None
    if not isinstance(kq, dict):
        raise LoiAI('Kết quả AI không đúng định dạng.')
    return kq


def _khoa(chu: str) -> str:
    return re.sub(r'[^a-z0-9%]+', '', bo_dau(chu or ''))


def _khoa_dong(m) -> tuple:
    return (m.ten, m.dvt, m.nguon_dong)


def gan_khoa(ds: list, kq: dict) -> dict:
    """Ngay khi AI trả lời: gắn khóa dòng (tên, ĐVT, dòng gốc) cho từng kết quả xác minh - so khớp lại (đổi nhóm / cách cập nhật) thêm /
    bỏ dòng phụ làm chỉ số stt lệch."""
    for x in kq.get('xac_minh') or ():
        try:
            i = int(x.get('stt'))
        except (TypeError, ValueError):
            continue
        if 0 <= i < len(ds):
            x['_khoa'] = _khoa_dong(ds[i])
    return kq


def ap_xac_minh(ds: list, kq: dict) -> dict:
    """Đánh dấu kết quả xác minh lên các dòng (gọi sau mỗi lần so_khop - so khớp lại làm mất trạng thái chọn). Không đổi đơn giá.
    Trả số dòng {'dung', 'sai', 'khong_thay'}."""
    from .nhap_don_gia import TRANG_THAI_GHI
    dem = {'dung': 0, 'sai': 0, 'khong_thay': 0}
    theo = {}
    for m in ds:
        theo.setdefault(_khoa_dong(m), m)
    for x in kq.get('xac_minh') or ():
        m = theo.get(x.get('_khoa'))
        if m is None or m.he_so:                         # 1.0.60: dòng hệ số (1,5 lần giá đất): kết quả AI là số tiền nguyên, không so được
            continue
        kl = x.get('ket_luan')
        gia = x.get('don_gia')
        if kl == 'dung' and isinstance(gia, int) and gia == m.don_gia:
            dem['dung'] += 1
            m.nghi_gia = ''
            m.cach_khop = '; '.join(c for c in (m.cach_khop, 'AI xác nhận') if c)
            if m.trang_thai in TRANG_THAI_GHI:
                m.chon = True
        elif kl in ('sai', 'dung'):
            dem['sai'] += 1
            doc = f'{gia:,}'.replace(',', '.') if isinstance(gia, int) and gia else '?'
            m.nghi_gia = m.nghi_gia or str(m.don_gia)
            m.cach_khop = '; '.join(c for c in (m.cach_khop, f'AI đọc: {x.get("ten") or m.ten} - {x.get("dvt") or m.dvt} - {doc} đ'
                                                + (f' ({x["ghi_chu"]})' if x.get('ghi_chu') else '')) if c)
            m.chon = False                               # không tự đổi giá theo AI: người dùng đối chiếu văn bản
        elif kl == 'khong_thay':
            dem['khong_thay'] += 1
            m.cach_khop = '; '.join(c for c in (m.cach_khop, 'AI không thấy trong văn bản') if c)
            m.chon = False
    return dem


def gop_quy_dinh(qd: list, kq: dict) -> int:
    """Thêm quy định AI tìm thấy mà phần mềm chưa trích (nguon 'AI'). Trả số quy định thêm."""
    da = [_khoa(q['chu']) for q in qd]
    them = 0
    for x in kq.get('quy_dinh') or ():
        chu = ' '.join(str(x.get('chu') or '').split())
        k = _khoa(chu)
        if len(k) < 15 or any(k in d or d in k for d in da if len(d) > 15):
            continue
        da.append(k)
        nhom = x.get('nhom') if x.get('nhom') in (0, 2, 3, 4, 7) else 0
        qd.append(dict(chu=chu[:500], nhom=nhom, dieu=str(x.get('dieu') or ''), pham_vi=str(x.get('pham_vi') or ''), nguon='AI'))
        them += 1
    return them


def tom_tat(kq: dict, dem: dict, them_qd: int, so_xm: int, cat: bool) -> str:
    vb = kq.get('van_ban') or {}
    phan = [f'AI đã đọc văn bản {vb.get("so_hieu") or ""}'.strip() + '.']
    if vb.get('sua_doi_boi'):
        phan.append('Được sửa đổi, bổ sung bởi: ' + ', '.join(vb['sua_doi_boi']) + '.')
    if vb.get('thay_the'):
        phan.append('Thay thế / bãi bỏ: ' + ', '.join(vb['thay_the']) + '.')
    phan.append(f'Xác minh {so_xm} dòng cần xem: {dem["dung"]} đúng (chọn sẵn), {dem["sai"]} AI đọc khác (bỏ chọn - đối chiếu văn bản), '
                f'{dem["khong_thay"]} không thấy trong văn bản (bỏ chọn).')
    if them_qd:
        phan.append(f'Thêm {them_qd} quy định cách tính AI tìm thấy trong lời văn.')
    if cat:
        phan.append('Văn bản dài: AI chỉ đọc phần đầu.')
    return ' '.join(phan)

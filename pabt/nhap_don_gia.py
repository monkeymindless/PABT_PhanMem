"""Cập nhật bộ đơn giá từ file bất kỳ (Excel .xlsx/.xlsm/.xls, Word .docx/.doc, PDF có chữ / scan, CSV). Phần tải từ trang
web nằm ở cap_nhat_web.py (phát hành riêng bằng gói cập nhật).

Quy trình: đọc bảng -> nhận các dòng (tên, ĐVT, đơn giá, mã nếu có) -> so khớp với bộ đơn giá đang dùng
(theo mã, rồi theo tên không dấu) -> người dùng xem / bỏ chọn -> áp dụng: tạo phiên bản bộ đơn giá mới và cài
(bộ cũ không bị sửa; dự án đã lập giữ đơn giá cũ cho tới khi "Áp bộ đơn giá vào dự án").
"""
from __future__ import annotations
import os
import re
import shutil
import tempfile
from dataclasses import dataclass
from datetime import datetime
from functools import lru_cache
from pathlib import Path

from . import csdl, don_gia
from .lap_pa import LoiNhap, bo_dau
from .tien import D, chuoi, lam_tron

DUOI_HO_TRO = ('.xlsx', '.xlsm', '.docx', '.pdf', '.csv', '.txt', '.sqlite')
DUOI_LIEN_KET = DUOI_HO_TRO + ('.xls', '.doc')     # liên kết trên trang web đáng đưa vào danh sách chọn
# nhóm danh mục khi cập nhật đơn giá. 7 = vật nuôi (= nghiep_vu.MUC_VN) CHỈ dùng khi phân tích / chọn trên màn hình - ghi vào bộ
# đơn giá là nhom 3 + phân loại vật nuôi + mã VN (cấu trúc CSDL không đổi: dm_taisan.nhom 2 / 3, chính sách ở bảng dm_hotro)
NHOM_VN = 7
NHOM = {2: 'Nhà, công trình, vật kiến trúc (mã TS)', 3: 'Cây trồng, hoa màu (mã CT)', NHOM_VN: 'Vật nuôi, thủy sản (mã VN)',
        4: 'Chính sách hỗ trợ (mã CS)'}
TIEN_TO = {2: 'TS', 3: 'CT', NHOM_VN: 'VN', 4: 'CS'}
# phân loại mặc định khi bộ đơn giá chưa có dòng nào của nhóm (bình thường lấy đúng chuỗi đang dùng trong bộ - _phan_loai)
PHAN_LOAI_MAC_DINH = {2: '2. Bồi thường, hỗ trợ về nhà và công trình xây dựng', 3: '3. Bồi thường, hỗ trợ về cây trồng'}
_DVT_GOC = (r'm²\s*sàn|m2\s*sàn|(?:m|mét)\s*/\s*sợi|m²|m2|m³|m3|md|mét|met|m|cây|cay|bụi|bui|khóm|hố|ha|kg|cái|chiếc|bộ|hộ|'
            r'khẩu|nhân khẩu|tháng|ngôi|mộ|con|đơn vị|lần|ô|gốc|trụ|cánh|sợi|lít|tấm|bồn')
# ĐVT trong dòng chữ (bản scan đọc theo dòng): "mét", "trụ", "cánh", "Đồng/m2" (bảng ghi đơn giá kèm "đồng/<đơn vị>") - 02/11/2026
DVT = rf'(?:(?:đồng|đ)\s*/\s*)?(?:{_DVT_GOC})'


@dataclass
class Muc:
    ten: str
    dvt: str
    don_gia: int
    ma: str = ''
    nguon_dong: str = ''          # dòng gốc (để người dùng đối chiếu)
    chon: bool = True
    trang_thai: str = ''          # mới / cập nhật / giữ nguyên
    ma_khop: str = ''
    gia_cu: int | None = None
    nhom: int = 0                 # 2 nhà, công trình / 3 cây trồng / 7 vật nuôi / 4 hỗ trợ (0: chưa xác định)
    khop_gan: float = 0.0         # so khớp tên gần đúng (tỷ lệ giống); 0 = khớp đúng mã / tên
    ghi_chu: str = ''             # quy cách văn bản ghi kèm (mật độ của loài cây: "Mật độ 1.111 cây/ha")
    ten_cu: str = ''              # tên / ghi chú mục đang khớp trong bộ đơn giá (so_khop)
    ghi_chu_cu: str = ''
    ten_thay: str = ''            # chế độ thay thế: tên / ghi chú sẽ ghi vào mục cũ theo cách ghi của văn bản mới ('' = không đổi)
    ghi_chu_thay: str = ''
    bo_cu: bool = False           # dòng do so_khop thêm: mục cũ cùng nhóm không còn trong văn bản (chế độ thay thế)
    nhom_loai: str = ''           # cây lâm nghiệp: khóa nhóm loài của bảng giá theo nhóm ('quy hiem', '1'…'8'; khoa_nhom_loai)
    duong_kinh: str = ''          # "(d >6-9 cm)" - cỡ đường kính của dòng bảng giá theo nhóm / dòng đã tách theo loài
    ten_loai: str = ''            # dòng đã tách theo loài: tên loài (không tên khác) - so khớp với bộ đơn giá
    ma_moi: str = ''              # mã sẽ cấp cho mục mới (so_khop; ap_dung dùng đúng mã này)
    cha: str = ''                 # dòng cha (không giá) của dòng con "- …" - nhận dòng chung nhiều tài sản (chu_the_chung)
    muc_gia: str = ''             # ô giá ghi khoảng "a - b": 'thap' / 'cao' (hai mục cùng tên, mục cao có dấu chấm cuối tên)
    khoang: str = ''              # chữ khoảng giá gốc "259.000 - 720.000"
    cach_khop: str = ''           # cách so_khop đã khớp ngoài tên: 'đặc trưng', 'dòng chung', 'khoảng giá: mức thấp' / 'mức cao'
    phu: bool = False             # dòng so_khop thêm cho dòng chung (một giá cho nhiều mục) - so lại thì bỏ
    nghi_gia: str = ''            # chữ ô giá bản scan không đúng dạng số tiền ("S27.312", "729/009"): giá đã sửa đoán - không chọn sẵn
    tach_tu: str = ''             # dòng văn bản ghi nhiều loài ("Cây cải xanh, cải ngọt, cải thìa") đã tách theo bộ đơn giá
    khu_vuc: str = ''             # 1.0.57: văn bản nhiều khu vực giá ("PHỤ LỤC II … KHU VỰC 2") - số khu vực của phụ lục chứa dòng
    he_so: str = ''               # 1.0.60: mức là HỆ SỐ, không phải số tiền ("1.5" lần giá đất nông nghiệp): don_gia = 0, ghi chữ này
    he_so_cu: str = ''            # hệ số đang dùng trong bộ đơn giá (so_khop)
    can_cu: str = ''              # 1.0.60: "Điểm a khoản 1 Điều 8" - dòng đọc từ điều khoản (khớp mục hỗ trợ theo Điều / giá / nghiệp vụ)
    ngu_canh: str = ''            # tiêu đề Điều + câu dẫn khoản của dòng (nhận nhóm nghiệp vụ)




class LoiKhongCoGia(LoiNhap):
    """Văn bản đọc được nhưng không có đơn giá (không bảng giá, không câu "<số> đồng/<ĐVT>"): văn bản quy định chính sách.
    Tách khỏi LoiNhap khác để màn hình không báo nhầm lỗi đọc / so khớp thành "không có đơn giá"."""


# 1.0.96: phần đọc file ở pabt/nhap_don_gia_doc.py (không Qt); nhập lại tên cũ
from .nhap_don_gia_doc import (DongScan, LoiPdfScan, _KieuDocx, _RE_PHONG_CU, _VBS_CHUYEN, _W, _chuyen_libreoffice, _doc_docx, _doc_pdf, _phong_cua, chuyen_office, doc_bang, doc_bang_ocr, dong_tu_chu, loai_that)  # noqa: E402,F401


# ---------------------------------------------------------------- nhận biết văn bản: số, ngày, cơ quan ban hành, trích yếu
# loại văn bản trong số hiệu: QĐ, NQ, CT (địa phương); NĐ (nghị định), TT / TTLT (thông tư), QH15 (luật, nghị quyết Quốc hội)
_LOAI_SO = r'(?:QĐ|QD|NQ|CT|NĐ|ND|TTLT|TT|QH|VBHN)'
_RE_SO_VB = re.compile(r'(?i)\bs[ốoôơó]\s*(?:hi[ệe]u)?\s*:?\s*(\d+[a-z]?\s*/\s*(?:\d{4}\s*/\s*)?' + _LOAI_SO + r'[\w.Đđ-]*)')
_RE_SO_TRONG = re.compile(r'(?i)\b(\d+[a-z]?\s*/\s*(?:\d{4}\s*/\s*)?(?:(?:QĐ|QD|NQ|NĐ|ND|TTLT|TT|VBHN)-[\wĐđ.]+|QH\d+))')
_TIEU_DE_LOAI = ('quyet dinh', 'nghi quyet', 'nghi dinh', 'thong tu', 'thong tu lien tich', 'luat')
_RE_NGAY_VB = re.compile(r'(?i)ngày\s*(\d{1,2})\s*(?:/|-|tháng)\s*(\d{1,2})\s*(?:/|-|năm)\s*(\d{4})')
# 1.0.60: trên chữ đã bỏ dấu (bản OCR hay đọc "nắm", "thảng"): chỉ lấy số
_RE_NGAY_KD = re.compile(r'\bngay\s*(\d{1,2})\s*(?:/|-|\.|thang)\s*(\d{1,2})\s*(?:/|-|\.|nam)\s*(\d{4})')
_RE_NGAY_KY = re.compile(r'\bky\s*:?\s*(\d{1,2})[./-](\d{1,2})[./-](\d{4})')          # chữ ký số: "Thời gian ký: 02.10.2025 05:08:38"
_RE_KEM_THEO = re.compile(r'(?i)kèm\s+theo\s+(?:Quyết\s+định|Nghị\s+quyết|Thông\s+tư|Nghị\s+định)\s+(?:số\s*:?\s*)?(\d+[a-z]?\s*/\s*(?:\d{4}\s*/\s*)?'
                          + _LOAI_SO + r'[\w.Đđ-]*)')


def chuan_chu_so_hieu(x: str) -> str:
    """1.0.60 - sửa số hiệu văn bản bản OCR đọc rời trong chữ: "NĐ. CP", "NĐ- CP", "QĐ- UBND", "QH 15", "42 /2025/ QĐ-UBND"
    -> "NĐ-CP", "QĐ-UBND", "QH15", "42/2025/QĐ-UBND". Chữ khác giữ nguyên."""
    x = re.sub(r'(?i)\b(QĐ|QD|NĐ|ND|NQ|TTLT|TT|VBHN)\s*[.\-–—]\s*(?=(?:UBND|HĐND|HDND|CP|TTg|BTNMT|BNNMT|BTC|BXD|BNN|UBTVQH)\b)', r'\1-', x)
    x = re.sub(r'\b(QH)\s+(\d{2})\b', r'\1\2', x)
    return re.sub(r'\b(\d{1,4}[a-z]?)\s*/\s*(\d{4})\s*/\s*(?=' + _LOAI_SO + r')', r'\1/\2/', x)


def _so_hieu_sach(so: str) -> str:
    """Số hiệu bắt được -> dạng ghi: bỏ khoảng trắng, dấu cuối; "QD-UBND" (OCR mất dấu) -> "QĐ-UBND", "ND-CP" -> "NĐ-CP"."""
    so = re.sub(r'\s+', '', so).strip('.,;:')
    return re.sub(r'(?i)/ND-', '/NĐ-', re.sub(r'(?i)/QD-', '/QĐ-', so))


def so_hieu_tu_ten_file(ten: str) -> str:
    """Số hiệu suy từ tên file khi phần đầu văn bản không đọc được: "42_QDQPPL_QPPL_2025 thay thế 58, 62.pdf",
    "31_2025_QD-UBND_673864.docx", "QD42-2025-QD-UBND 02-10-2025 ….docx" -> "42/2025/QĐ-UBND"; không suy được -> ''."""
    k = bo_dau(re.split(r'[\\/]', str(ten or ''))[-1]).upper()
    m = re.search(r'(?<!\d)(\d{1,4})[_ -]+(\d{4})[_ -]+VBHN', k)
    if m:
        return f'{m.group(1)}/{m.group(2)}/VBHN-UBND'
    m = re.search(r'(?<!\d)(\d{1,4})[_ -]+(\d{4})[_ -]+QD[_ -]+(?:UBND|QPPL)', k) or re.search(r'\bQD[_ -]*(\d{1,4})[_ -]+(\d{4})[_ -]+QD', k)
    if m:
        return f'{m.group(1)}/{m.group(2)}/QĐ-UBND'
    m = re.search(r'(?<!\d)(\d{1,4})[_ -]+QD\w*[_ -]+(?:QPPL[_ -]+)?(\d{4})(?!\d)', k)
    if m:
        return f'{m.group(1)}/{m.group(2)}/QĐ-UBND'
    m = re.search(r'(?<!\d)(\d{1,4})[_ -]+(\d{4})[_ -]+NQ[_ -]+HDND', k)
    return f'{m.group(1)}/{m.group(2)}/NQ-HĐND' if m else ''


def _ngay_tu(m) -> str:
    d, t, n = int(m.group(1)), int(m.group(2)), int(m.group(3))
    return f'{d:02d}/{t:02d}/{n}' if 1 <= d <= 31 and 1 <= t <= 12 and 1950 <= n <= 2100 else ''


def _phan_dau(dau: list) -> list:
    """Các dòng phần đầu văn bản: trước tiêu đề loại văn bản ("QUYẾT ĐỊNH") hoặc dòng "Căn cứ" đầu tiên; không có các dòng đó (bảng,
    trích đoạn) -> 30 dòng đầu."""
    for i, x in enumerate(dau):
        k = bo_dau(x)
        if i and k.rstrip(' :') in _TIEU_DE_LOAI:
            return dau[:i]
        if k.startswith(('can cu ', 'xet de nghi', 'theo de nghi')):
            return dau[:i]
    return dau[:30]


# cụm dẫn chiếu "được sửa đổi, bổ sung (một số điều) bởi (các) Luật số …, Nghị định số …" - văn bản KHÁC sửa văn bản được dẫn, không phải nội
# dung sửa đổi; chỉ ăn các số hiệu ngay sau "bởi" (phần còn lại của câu giữ nguyên). Chữ bản OCR hay sai: sửa/sủa/sứa, đổi/đôi/đối, bổ/bô/bố
_RE_DAN_CHIEU = re.compile(r'(?i),?\s*(?:đã\s+|đang\s+)?(?:được|bị)\s+s[ửủứu]a\s+đ[ổôốồỗo]i\s*,?\s*(?:và\s+)?b[ổôốồỗo]\s+sung(?:\s+một\s+s[ốô]\s+điều)?\s+'
                           r'(?:bởi|tại|theo)(?:\s*(?:,|\||và(?=\s+(?:s[ốô]|Luật|Nghị|\d))|các\b\.?|Luật\b|Nghị\s+định\b|Thông\s+tư\b|Quyết\s+định\b|s[ốô](?=\s*\d)|s[ốô]\b|\d+/\d{4}/[\w.Đđ-]*[\wĐđ]))+')
_RE_THAY_THE = re.compile(r'(?:^|\b(?:quyet dinh|nghi quyet|nghi dinh|thong tu|van ban)(?: nay)?\s+)(?:va\s+)?(thay the|bai bo|sua doi|bo sung|ngung ap dung)\b')
_RE_CAU_HIEU_LUC = re.compile(r'\b(thay the|bai bo|het hieu luc|ngung ap dung)\b')
_RE_BI_THAY = re.compile(r'(?i)\b(\d{1,4}[a-z]?/\d{4}/(?:QĐ|QD|NQ|NĐ|ND)-[\wĐđ.]*[\wĐđ])')
_RE_DOI_TUONG = re.compile(r'\b(?:quyet dinh|nghi quyet|nghi dinh|thong tu|van ban|dieu|khoan|diem|muc|phu luc|bang|quy dinh)\b')


def bo_dan_chieu(x: str) -> str:
    """Chữ bỏ cụm "được sửa đổi, bổ sung bởi …" (số hiệu đọc rời hai dòng "NĐ-" + "CP" nối lại trước)."""
    return _RE_DAN_CHIEU.sub('', chuan_chu_so_hieu(x))


def khoan_hieu_luc(dong: list) -> tuple:
    """1.0.60: (các khoản về việc sửa đổi / thay thế / bãi bỏ của CHÍNH văn bản, [số hiệu văn bản bị thay thế]). Bỏ phần "Căn cứ …" và cụm
    dẫn chiếu "được sửa đổi, bổ sung bởi Luật số …". Khoản dẫn "… thay thế các Quy định sau:" kéo theo các điểm a), b), c) ngay dưới
    (Điều 2 QĐ 42/2025: thay thế QĐ 58/2024, Điều 4 và khoản 3 Điều 5 QĐ 62/2024, QĐ 05/2025)."""
    van = dong_loi_van(dong)
    i0 = next((i for i, x in enumerate(van) if re.match(r'(?:quyet dinh|quyet nghi)\s*:$|dieu\s+\d+\s*[.:]', bo_dau(x))), 0)
    can_xem, bi_thay = [], []
    dan = False

    def them_so(chu):
        for m in _RE_BI_THAY.finditer(bo_dan_chieu(chu)):
            so = _so_hieu_sach(m.group(1))
            if so not in bi_thay:
                bi_thay.append(so)
    for c in _khoan_van(van[i0:]):
        k = bo_dau(c)
        if k.startswith(('can cu ', 'theo de nghi', 'xet de nghi')) or re.match(r'n\w{0,2}i nhan|tm\.|kt\.', k):
            dan = False
            continue
        cap, than = _bo_dau_khoan(c)
        if dan and cap == 3:                            # điểm a), b), c) của khoản dẫn
            can_xem.append(c[:300])
            them_so(c)
            continue
        dan = False
        than_k = bo_dau(bo_dan_chieu(than))
        m = _RE_THAY_THE.search(than_k[:120])
        if m and (_RE_DOI_TUONG.search(than_k) or re.search(r'\d', than_k)):
            can_xem.append(c[:300])
            if m.group(1) not in ('sua doi', 'bo sung') or than.rstrip().endswith(':'):
                them_so(c)
            dan = than.rstrip().endswith(':')
        elif _RE_CAU_HIEU_LUC.search(than_k) and _RE_BI_THAY.search(bo_dan_chieu(than)) and \
                re.search(r'(?:quyet dinh|nghi quyet)\s+(?:so\b|nay\b)', than_k):
            # "Quyết định này có hiệu lực từ … và thay thế Quyết định số …", "Quyết định số … hết hiệu lực kể từ …"
            can_xem.append(c[:300])
            them_so(c)
    return can_xem, bi_thay


def van_ban_cu_theo_so_hieu(so_hieu: list | tuple) -> list:
    """[(id, số hiệu, nội dung)] các dòng văn bản căn cứ của bộ đơn giá đang dùng ứng với số hiệu trong danh sách, còn hiệu lực."""
    ks = [chuan_so_hieu(x) for x in so_hieu or () if x]
    if not ks:
        return []
    con = csdl.mo(don_gia.file_dang_dung(), chi_doc=True)
    try:
        ds = [tuple(r) for r in con.execute('SELECT id, so_hieu, noi_dung, trang_thai FROM van_ban')]
    finally:
        con.close()
    return [(i, sh, nd) for i, sh, nd, tt in ds if 'het hieu luc' not in bo_dau(tt)
            and any(re.search(r'(?<!\d)' + re.escape(k), chuan_so_hieu(sh)) for k in ks)]


def chuan_so_hieu(s: str) -> str:
    """'48 / 2025 / QĐ-UBND' -> '48/2025/QD-UBND' (so sánh số hiệu văn bản)."""
    return re.sub(r'\s+', '', bo_dau(s or '')).upper()


def phan_tich_van_ban(dong: list, ten_goi: str = '') -> dict:
    """Số hiệu, ngày ban hành, cơ quan, loại, trích yếu của văn bản (các dòng đầu đọc từ Word / PDF / OCR) và tên gọi trên
    trang web (nếu có); nhom: nhóm danh mục đoán theo trích yếu (3 cây trồng, vật nuôi / 2 nhà, công trình / 4 hỗ trợ);
    dong_nai: văn bản của Đồng Nai; sua_doi: văn bản sửa đổi, bổ sung."""
    dau = [chuan_chu_so_hieu(' '.join(' '.join(str(c) for c in r if c).split())) for r in dong[:150]]
    toan = '\n'.join(x for x in dau if x)
    # 1.0.60 (QĐ 42/2025 bản scan): số hiệu, ngày CHỈ ở phần đầu văn bản (dòng "Căn cứ Luật … số 72/2025/QH15" là văn bản khác); phần đầu
    # không đọc được (OCR "Số: 4à /2025/QĐ-UBND"): câu "Ban hành kèm theo Quyết định số … ngày …", tên trên trang web, tên file; ngày thêm:
    # chữ ký số "Thời gian ký: 02.10.2025"
    chu_dau = '\n'.join(x for x in _phan_dau(dau) if x)
    so = ngay = ''
    mso = _RE_SO_VB.search(chu_dau)
    kem = None
    for x in dau:
        if not bo_dau(x).startswith('can cu'):
            kem = _RE_KEM_THEO.search(x)
            if kem:
                break
    if mso:
        so = _so_hieu_sach(mso.group(1))
    elif kem:
        so = _so_hieu_sach(kem.group(1))
    else:
        mt = _RE_SO_TRONG.search(chuan_chu_so_hieu(ten_goi or ''))
        so = _so_hieu_sach(mt.group(1)) if mt else so_hieu_tu_ten_file(ten_goi)
    mn = _RE_NGAY_KD.search(bo_dau(chu_dau))
    if mn is None and kem is not None:
        mn = _RE_NGAY_KD.search(bo_dau(kem.string[kem.end():]))
    if mn is None:
        mn = _RE_NGAY_KY.search(bo_dau(chu_dau))
    if mn is None and so:
        mn = _RE_NGAY_KY.search(bo_dau(toan)) or _RE_NGAY_KD.search(bo_dau(ten_goi or ''))
    if mn and so:
        ngay = _ngay_tu(mn)
    kd = bo_dau(toan[:1500])
    co_quan = ''
    # bản OCR đọc hai cột chung dòng: "ỦY BAN NHÂN DÂN CỘNG HÒA XÃ HỘI…" / "TỈNH ĐỒNG NAI Độc lập - Tự do…": bỏ quốc hiệu, tiêu ngữ
    kd_cq = re.sub(r'cong hoa xa hoi chu nghia viet nam|doc lap\s*[-–—.]?\s*tu do\s*[-–—.]?\s*hanh phuc', ' ', kd)
    mc = re.search(r'(uy ban nhan dan|hoi dong nhan dan)\W+(tinh|thanh pho)\W+dong nai', kd_cq)
    if mc:
        co_quan = ('Ủy ban nhân dân ' if mc.group(1).startswith('uy') else 'Hội đồng nhân dân ') + \
            ('tỉnh' if mc.group(2) == 'tinh' else 'thành phố') + ' Đồng Nai'
    else:                                               # văn bản Trung ương: cơ quan ở các dòng đầu
        for x in dau[:8]:
            k = bo_dau(x)
            if k in ('quoc hoi', 'chinh phu', 'thu tuong chinh phu'):
                co_quan = {'quoc hoi': 'Quốc hội', 'chinh phu': 'Chính phủ', 'thu tuong chinh phu': 'Thủ tướng Chính phủ'}[k]
                break
            if re.fullmatch(r'bo [a-z ,]{4,60}', k):     # "BỘ NÔNG NGHIỆP VÀ MÔI TRƯỜNG" -> "Bộ Nông nghiệp và môi trường"
                ten = x[3:].strip().lower()
                co_quan = 'Bộ ' + ten[:1].upper() + ten[1:]
                break
    su = bo_dau(so).upper()
    loai = ('Văn bản hợp nhất' if 'VBHN' in su else 'Nghị quyết' if 'NQ' in su else 'Quyết định' if re.search(r'Q[D]', su) else 'Nghị định' if re.search(r'/N[D]', su)
            else 'Thông tư liên tịch' if 'TTLT' in su else 'Thông tư' if re.search(r'/TT', su) else '')
    trich = []
    for i, x in enumerate(dau):
        k = bo_dau(x)
        if not loai and 'QH' in su and re.match(r'(luat|nghi quyet)\b', k):
            loai = 'Luật' if k.startswith('luat') else 'Nghị quyết'
        if k.startswith('luat ') and len(x) <= 120 and 'QH' in su and not re.search(r'\d', x):
            trich = [x]                                 # "LUẬT ĐẤT ĐAI": tên luật trên cùng dòng
            break
        if k in _TIEU_DE_LOAI:
            for y in dau[i + 1: i + 5]:
                if not y or re.match(r'(can cu|uy ban nhan dan|hoi dong nhan dan|chu tich|quyet dinh:|quyet nghi|chinh phu ban hanh|'
                                     r'bo truong|quoc hoi ban hanh)', bo_dau(y)):
                    break
                trich.append(y)
            if trich:
                break
    if 'QH' in su and not loai:
        loai = 'Luật'
    trich_yeu = ' '.join(trich)
    if not trich_yeu and ten_goi:                       # tên trên trang web: "Quyết định số 48/2025/QĐ-UBND ban hành ..."
        trich_yeu = re.sub(r'(?i)^.*?\b(q[uđ]y[ếe]t\s+[đd][ịi]nh|ngh[ịi]\s+quy[ếe]t|ngh[ịi]\s+[đd][ịi]nh|th[ôo]ng\s+t[ưu](?:\s+li[êe]n\s+t[ịi]ch)?|'
                           r'lu[ậa]t)\s+s[ốo]\s*\S+\s*', '', ten_goi).strip()
    goc = bo_dau(trich_yeu + ' ' + (ten_goi or ''))
    # câu sửa đổi / bãi bỏ của chính văn bản: phần mềm chỉ áp dụng bảng giá, các nội dung này người dùng tự xem
    can_xem, thay_the_vb = khoan_hieu_luc(dong)
    can_xem = [x for x in can_xem if x not in trich]
    thay_the_vb = [x for x in thay_the_vb if chuan_so_hieu(x) != chuan_so_hieu(so)]
    return dict(so_hieu=so, ngay=ngay, co_quan=co_quan, loai_vb=loai, trich_yeu=trich_yeu,
                dong_nai='dong nai' in kd or 'dong nai' in bo_dau(ten_goi or ''),
                nhom=nhom_theo_chu(trich_yeu or ten_goi or ''),
                sua_doi=bool(re.search(r'sua doi|bo sung|thay the|bai bo', goc)), can_xem=can_xem[:30], thay_the_vb=thay_the_vb)


def van_ban_da_co() -> list:
    """Số hiệu (chuẩn hóa) các văn bản căn cứ đã có trong bộ đơn giá đang dùng (bảng van_ban)."""
    con = csdl.mo(don_gia.file_dang_dung(), chi_doc=True)
    try:
        return [chuan_so_hieu(r[0]) for r in con.execute('SELECT so_hieu FROM van_ban')]
    finally:
        con.close()


def da_co(so_hieu: str, ds_co: list | None = None) -> bool:
    k = chuan_so_hieu(so_hieu)
    if not k:
        return False
    ds_co = van_ban_da_co() if ds_co is None else ds_co
    # "48/2025/QD-UBND" nằm trong "QUYETDINH48/2025/QD-UBND(SUADOIBOIQD66/2025/QD-UBND)"; tránh 8/2025 khớp nhầm 48/2025
    return any(re.search(r'(?<!\d)' + re.escape(k), x) for x in ds_co)


# ---------------------------------------------------------------- nhận dòng đơn giá
def doc_gia(v) -> int | None:
    """'1.480.500' / '9.445' (nghìn kiểu VN) / '9445000' / 1480500.0 -> int đồng; không phải số tiền -> None."""
    s = str(v or '').strip().replace(' ', '').replace('đ', '').replace('đồng', '')
    if not s:
        return None
    if re.fullmatch(r'\d{1,3}(\.\d{3})+', s) or re.fullmatch(r'\d{1,3}(,\d{3})+', s):
        s = re.sub(r'[.,]', '', s)
    try:
        g = D(s)
    except ValueError:
        return None
    return int(g) if g > 0 and g == int(g) else (int(lam_tron(g)) if g >= 1000 else None)


def _cot(tieu_de: list, *mau) -> int | None:
    for i, t in enumerate(tieu_de):
        if any(re.search(m, t) for m in mau):
            return i
    return None


_LA_MA = re.compile(r'^(?:[IVXL]+|[A-H])\.?$')          # STT tiêu đề nhóm: I, II, ... / A, B
_CON = re.compile(r'^(?:[-+–•*]+|[a-zđ][).]?|\d+\.\d+\.?)$', re.I)   # STT dòng con: -, +, *, a, a), 1.1


_RE_VAT_NUOI = re.compile(r'vat nuoi|thuy san|thuy hai san|chan nuoi|gia suc|gia cam|long be|long, be|tham canh|quang canh|'
                         r'ao nuoi|nuoi trong|chim yen|\bca (giong|thit)\b|\btom\b')
_RE_CAY = re.compile(r'cay trong|hoa mau|cay an qua|cay lau nam|cay hang nam|cay canh|\brau\b|\bcay\b')


def nhom_theo_chu(chu: str) -> int:
    """Nhóm danh mục theo chữ (tiêu đề văn bản / tiêu đề nhóm / tên mục): 3 cây trồng, hoa màu; 7 vật nuôi, thủy sản (chỉ khi
    không nói tới cây trồng - "cây trồng, vật nuôi" là 3, từng dòng tự phân); 2 nhà, công trình, vật kiến trúc, mồ mả; 4 chính sách
    hỗ trợ (kể cả di dời mồ mả); 0 không rõ."""
    k = re.sub(r'nha nuoc|uy ban nhan dan|nhan dan', ' ', bo_dau(chu))     # "khi Nhà nước thu hồi đất" không phải nhà ở
    co_vn, co_cay = _RE_VAT_NUOI.search(k), _RE_CAY.search(k)
    if co_vn and not co_cay:
        return NHOM_VN
    if co_cay or co_vn:
        return 3
    if re.search(r'(di doi|boc|cai tang|dao,? boc).{0,12}mo', k):        # "Hỗ trợ đào, bốc, di dời mồ mả": chính sách hỗ trợ
        return 4
    if re.search(r'\bnha\b|cong trinh|vat kien truc|nha o|xay dung|mo ma|\bmo (xay|dat|da)\b', k):
        return 2
    if re.search(r'ho tro|on dinh doi song|dao tao|chuyen doi nghe|tai dinh cu|thue nha', k):
        return 4
    return 0


def _nhom_dong(ten: str, dvt: str) -> int:
    """Nhóm của một dòng khi văn bản / tiêu đề nhóm không cho biết."""
    n = nhom_theo_chu(ten)
    if n:
        return n
    d = ' '.join(bo_dau(dvt).replace('/', ' / ').split())
    # vật nuôi: con, kg, m² mặt nước, ha/vụ, 100m³/vụ, lồng; cây trồng: cây, bụi, gốc, ha (hoa màu)
    if d in ('con', 'kg', 'kg yen tho', 'long', 'be', 'dan', 'o') or re.search(r'mat nuoc|/ vu$|100 ?m[3³]', d):
        return NHOM_VN
    if d in ('cay', 'bui', 'khom', 'goc', 'ha', 'chau', 'hoc'):
        return 3
    if d in ('nhan khau', 'khau', 'ho', 'thang', 'lan'):
        return 4
    return 2


def _tach_gia(o: str):
    """'24.880.000' -> (24880000, ''); 'Đông Xuân: 24.880.000' -> (24880000, 'Đông Xuân')."""
    g = doc_gia(o)
    if g:
        return g, ''
    m = re.match(r'^([^\d:]{1,40}?)\s*:\s*([\d][\d.,]*)\s*(?:đ|đồng)?$', ' '.join(str(o or '').split()))
    if m:
        g = doc_gia(m.group(2))
        if g:
            return g, m.group(1).strip()
    return None, ''


_RE_GIA_SACH = re.compile(r'\d{1,3}(?:[.,]\d{3})*')
_RE_NHAN_GIA = re.compile(r'([^\d:;|]{2,60}?)\s*:\s*(\d{1,3}(?:[.,]\d{3})+)')
_SUA_SO_OCR = str.maketrans({'S': '5', 's': '5', 'O': '0', 'o': '0', 'l': '1', 'I': '1', 'B': '8', 'g': '9', '/': '.', ',': '.'})


def tach_nhieu_gia(o: str) -> list:
    """Ô giá ghi nhiều mức có nhãn: "Đông Xuân: 37.050.000 Hè Thu, Mùa: 25.500.000" -> [('Đông Xuân', 37050000), ('Hè Thu, Mùa',
    25500000)] (bản scan còn mẩu chữ rác trước nhãn: bỏ tới chữ hoa đầu tiên có chữ thường theo sau). Ít hơn hai nhãn: []."""
    kq = []
    for m in _RE_NHAN_GIA.finditer(' '.join(str(o or '').split())):
        nhan = m.group(1)
        dau = next((i for i in range(len(nhan) - 1) if nhan[i].isupper() and nhan[i + 1].islower()), None)
        nhan = nhan[dau:].strip(' ,;-') if dau is not None else ''
        g = doc_gia(m.group(2))
        if nhan and g:
            kq.append((nhan, g))
    return kq if len(kq) >= 2 else []


def doc_gia_ocr(o) -> int | None:
    """Ô giá bản scan đọc sai chữ số ("S27.312" -> 527312, "729/009" -> 729009, "2360909") - giá ĐOÁN, nơi gọi đánh dấu cần xem."""
    s = re.sub(r'\s+', '', str(o or ''))
    if not s or len(s) > 16 or not re.search(r'\d', s):
        return None
    t = s.translate(_SUA_SO_OCR)
    if re.fullmatch(r'\d{1,3}(?:\.\d{3})+', t):
        return doc_gia(t)
    if re.fullmatch(r'\d{4,9}', t):
        return int(t)
    return None


def chuan_dvt(d: str) -> str:
    """ĐVT theo cách ghi của bộ đơn giá: "Đồng/m2" -> "m²", "mét" -> "m", "mét/sợi" -> "m/sợi", "m3" -> "m³"."""
    d = ' '.join(str(d or '').split())
    d = re.sub(r'(?i)^(?:đồng|đông|dông|dồng|đ)\s*/\s*', '', d)       # văn bản gõ sai "dông/m2" (QĐ 18/2026 Phụ lục IIb)
    d = re.sub(r'(?i)^m[ée]t\b', 'm', d)
    d = re.sub(r'(?i)\bm2\b', 'm²', re.sub(r'(?i)\bm3\b', 'm³', d))
    return re.sub(r'\s*/\s*', '/', d)


@lru_cache(maxsize=4096)
def _dvt_khoa(d: str) -> str:
    return bo_dau(chuan_dvt(d)).replace(' ', '')


def doc_khoang_gia(o) -> tuple | None:
    """Ô giá ghi khoảng "259.000 - 720.000" -> (259000, 720000) (thấp < cao); không phải khoảng giá -> None."""
    m = re.fullmatch(r'\s*(\d[\d.,]*)\s*(?:đồng|đ)?\s*[-–—]\s*(\d[\d.,]*)\s*(?:đồng|đ)?\s*', str(o or ''))
    if not m:
        return None
    a, b = doc_gia(m.group(1)), doc_gia(m.group(2))
    return (a, b) if a and b and a < b and a >= GIA_TOI_THIEU else None


GIA_TOI_THIEU = 500      # đơn giá đọc theo dòng chữ nhỏ hơn mức này là số khác ("ngày 25 tháng 10") - không phải tiền
_RE_QUY_TAC = re.compile(r'\d\s*%|phan tram|tinh them|duoc tinh|tinh bang|xac dinh (?:theo|nhu sau)|bang \d+ ?%|'
                         r'tro di duoc|duoc ap dung|ap dung (?:muc|don gia)|khong (?:vuot qua|tinh)')


def la_quy_tac(chu: str) -> bool:
    """Dòng không có đơn giá là QUY ĐỊNH CÁCH TÍNH ("Giếng sâu từ 10m trở lên thì mét thứ 10 trở đi được tính thêm 50% mức giá trên",
    "Đơn giá gác lửng bằng 40% đơn giá…", "xác định theo loại kết cấu nhà có…") - không phải dòng cha / mục đơn giá."""
    return bool(_RE_QUY_TAC.search(bo_dau(chu)))


_RE_MAT_DO_TEN = re.compile(r'(?i)\s*[(“"«]\s*(?:m[ậa]t\s*[đd][ộo](?:\s+chu[ẩa]n)?\s*:?\s*)?(?:(\d[\d.,]*)\s*(cây|cay|khóm|khom|bụi|bui|'
                            r'hố|ho|gốc|goc)\s*/\s*ha|[^)]*)\s*\)')
_LA_MA_SO = {'i': 1, 'ii': 2, 'iii': 3, 'iv': 4, 'v': 5, 'vi': 6, 'vii': 7, 'viii': 8, 'ix': 9, 'x': 10}


def khoa_nhom_loai(chu: str) -> str:
    """Khóa nhóm loài cây lâm nghiệp trong bảng giá / danh sách loài: "Nhóm quý hiếm gồm 45 loài", "Bảng 1: Nhóm loài cây quý hiếm"
    -> 'quy hiem'; "Nhóm I gồm 13 loài", "Bảng 4: Loài cây nhóm III", "nhóm 4" -> '1' / '3' / '4'. Không nhận ra: ''."""
    k = ' '.join(bo_dau(chu or '').lower().split())
    if 'quy hiem' in k:
        return 'quy hiem'
    m = re.search(r'\bnhom\s+(?:loai\s+)?([ivx]+|\d+)\b', k)
    if not m:
        # bản scan: số La Mã đọc sai ("nhóm IJI", "nhóm Il", "nhóm 1V") - j / l / 1 / | thay chữ I
        m = re.search(r'\bnhom\s+(?:loai\s+)?([ivxjl1|]+)(?![\w])', k)
        if not m or not re.search(r'[ivx]', m.group(1)):
            return ''
        g = re.sub(r'[jl1|]', 'i', m.group(1))
        return str(_LA_MA_SO[g]) if g in _LA_MA_SO else ''
    g = m.group(1)
    return str(int(g)) if g.isdigit() else str(_LA_MA_SO.get(g, '')) if g in _LA_MA_SO else ''


def chuan_duong_kinh(chu: str) -> str:
    """Ô cỡ đường kính thân -> phần tên như bộ đơn giá: "≤3" -> "(d ≤3 cm)", ">3 - 6" -> "(d >3-6 cm)", "> 42" -> "(d >42 cm)"; ô
    không có số: ''."""
    s = ' '.join(str(chu or '').replace('–', '-').split())
    m = re.search(r'(<=|>=|[<>≤≥])?\s*(\d+(?:[.,]\d+)?)\s*(?:cm)?\s*(?:-\s*(\d+(?:[.,]\d+)?))?', s)
    if not m:
        return ''
    dau = {'<=': '≤', '>=': '≥'}.get(m.group(1), m.group(1) or '')
    return f'(d {dau}{m.group(2)}{"-" + m.group(3) if m.group(3) else ""} cm)'


def doc_nhom_loai(dong: list) -> dict:
    """Danh sách loài theo nhóm (Phụ lục VI của văn bản cây lâm nghiệp): dòng "Bảng k: Loài cây nhóm III" / "Bảng 1: Nhóm loài cây quý
    hiếm" rồi bảng có cột "Tên Việt Nam" (+ "Tên Việt Nam khác") -> {khóa nhóm: [(tên loài, (tên khác…))]}."""
    kq, khoa, ten_c, khac_c = {}, '', None, None
    for r in dong:
        o = [' '.join(bo_dau(c).lower().split()) for c in r]
        chu = ' '.join(x for x in o if x)
        if re.search(r'\bbang\s*\d+\b', chu) and 'nhom' in chu and sum(1 for x in o if x) <= 2:
            khoa, ten_c, khac_c = khoa_nhom_loai(chu), None, None
            continue
        if not khoa:
            continue
        tc = _cot(o, r'^ten viet nam$', r'^ten (loai|cay|viet)(?! nam khac)')
        if tc is not None and not any(re.fullmatch(r'\d+', x) for x in o):
            ten_c, khac_c = tc, _cot(o, r'^ten (viet nam )?khac', r'ten viet nam khac')
            continue
        if ten_c is None or ten_c >= len(r):
            continue
        ten = ' '.join(r[ten_c].split()).strip(' .;')
        if not ten or re.fullmatch(r'[\d\W]+', ten) or re.search(r'bai bo', bo_dau(ten)):   # "(Được bãi bỏ)": loài đã bỏ
            continue
        khac = r[khac_c] if khac_c is not None and khac_c < len(r) else ''
        ds_khac = tuple(x.strip() for x in re.split(r'[.;,]\s*', khac) if sum(c.isalpha() for c in x) >= 2)
        kq.setdefault(khoa, []).append((ten, ds_khac))
    return kq


def _loai_trong_bo(dm_nhom3: list) -> dict:
    """Bộ đơn giá đang dùng: {tên loài (không tên khác): {khóa cỡ đường kính: dòng}} của các dòng "Loài (…) (d …)"."""
    from .ten_cay_lam_nghiep import bo_ten_khac
    kq = {}
    for x in dm_nhom3:
        m = re.search(r'\(\s*d\b[^)]*\)\s*$', x['ten'])
        if not m:
            continue
        loai = bo_ten_khac(x['ten'])[:].rsplit('(', 1)[0].strip()
        kq.setdefault(loai, {})[_khoa(m.group(0))] = x
    return kq


NGUONG_SUA_TEN_MOT = 0.45         # như trên khi nhóm chỉ còn MỘT loài của bộ chưa được văn bản nhận
NGUONG_SUA_TEN_NHOM = 0.6         # như trên, chỉ trong các loài của bộ đơn giá cùng bảng giá với nhóm mà văn bản chưa nhận
NGUONG_SUA_TEN_LOAI = 0.72         # độ giống (bỏ dấu, SequenceMatcher) tối thiểu để sửa tên loài đọc sai về tên loài đã biết


def sua_ten_loai(ten: str, khac: tuple, biet: dict, tranh: frozenset | set = frozenset()) -> tuple:
    """Tên loài đọc từ bản scan (OCR hay sai dấu / sai chữ: "Câmlai", "Bò'i lời giấy") -> (tên đúng, tên khác). biet = {tên loài đã
    biết: (tên khác)} - danh sách Phụ lục VI gắn sẵn (ten_cay_lam_nghiep.TEN_KHAC) + loài trong bộ đơn giá đang dùng. Tên trùng hẳn
    (bỏ dấu) giữ nguyên; giống >= NGUONG_SUA_TEN_LOAI (cộng điểm tên khác giống nhau) thì lấy tên đã biết; không thì giữ chữ đọc được."""
    from difflib import SequenceMatcher

    def k(x):
        return ' '.join(re.sub(r"[^\w ]+", ' ', bo_dau(x).lower()).split())
    kt = k(ten)
    if not kt:
        return ten, khac
    kk = k(' '.join(khac))
    thuong = ' '.join(ten.lower().split())
    for t in biet:
        if t.lower() == thuong:                         # trùng hẳn (có dấu)
            return t, biet[t] or khac

    def khac_dau(t):
        """Bỏ dấu giống nhưng chữ có dấu khác và tên khác không giống: hai loài khác nhau ("Sữa" / "Sưa")."""
        tk = k(' '.join(biet[t]))
        return t.lower() != thuong and kk and tk and SequenceMatcher(None, kk, tk).ratio() < 0.5
    for t in biet:
        if k(t) == kt and t not in tranh and not khac_dau(t):
            return t, biet[t] or khac
    tot, diem = None, 0.0
    for t, tk in biet.items():
        if t in tranh or khac_dau(t):
            continue
        d = SequenceMatcher(None, kt, k(t)).ratio()
        if kk and tk:
            d = max(d, 0.6 * d + 0.4 * SequenceMatcher(None, kk, k(' '.join(tk))).ratio())
        if d > diem:
            tot, diem = t, d
    if tot is not None and diem >= NGUONG_SUA_TEN_LOAI:
        return tot, biet[tot]
    return ten, khac


def _loai_cung_gia(dong: list, bo: dict, da_ghi: set) -> list:
    """Loài của bộ đơn giá có bảng giá theo cỡ trùng (>= 70% số cỡ chung, >= 3 cỡ) với nhóm trong văn bản, mà văn bản chưa ghi tên."""
    gia = {_khoa(m.duong_kinh): m.don_gia for m in dong}
    kq = []
    for loai, co in (bo or {}).items():
        chung = [c for c in gia if c in co]
        bang = sum(1 for c in chung if doc_gia(co[c]['don_gia']) == gia[c])
        if len(chung) >= 3 and bang >= 0.7 * len(chung) and \
                ' '.join(re.sub(r"[^\w ]+", ' ', bo_dau(loai).lower()).split()) not in da_ghi:
            kq.append(loai)
    return kq


def _sua_ten_nhom(ds: list, biet: dict, tranh: set, uu: list) -> list:
    """Sửa tên loài đọc sai của MỘT nhóm theo cấu trúc bộ đơn giá (02/11/2026): (1) tên trùng hẳn giữ; (2) loài của bộ có cùng bảng
    giá theo cỡ với nhóm mà văn bản chưa ghi đúng tên - ghép một-một theo độ giống từ cao xuống ("Sc đỏ" -> "Re đỏ", "Suổi" -> "Ruổi");
    còn đúng một tên đọc sai và một loài của bộ thì ghép khi giống >= NGUONG_SUA_TEN_MOT ("Vý" -> "Mý"); (3) còn lại sua_ten_loai."""
    from difflib import SequenceMatcher

    def k(x):
        return ' '.join(re.sub(r"[^\w ]+", ' ', bo_dau(x).lower()).split())
    kq = list(ds)
    dung, cho = set(), []
    for i, (t, khac) in enumerate(ds):
        t2 = next((x for x in biet if x.lower() == ' '.join(t.lower().split())), None)
        if t2 is not None:
            kq[i] = (t2, biet[t2] or khac)
            dung.add(k(t2))
        else:
            cho.append(i)
    con_lai = [x for x in uu if k(x) not in dung]
    cap = sorted(((SequenceMatcher(None, k(ds[i][0]), k(x)).ratio(), i, x) for i in cho for x in con_lai), key=lambda c: -c[0])
    ghep_i, ghep_x = set(), set()
    for d, i, x in cap:
        if d >= NGUONG_SUA_TEN_NHOM and i not in ghep_i and x not in ghep_x:
            kq[i] = (x, biet.get(x) or ds[i][1])
            ghep_i.add(i)
            ghep_x.add(x)
    cho = [i for i in cho if i not in ghep_i]
    con_lai = [x for x in con_lai if x not in ghep_x]
    if len(cho) >= 1 and len(con_lai) == 1:
        tot = max(cho, key=lambda i: SequenceMatcher(None, k(ds[i][0]), k(con_lai[0])).ratio())
        if SequenceMatcher(None, k(ds[tot][0]), k(con_lai[0])).ratio() >= NGUONG_SUA_TEN_MOT and \
                sua_ten_loai(ds[tot][0], ds[tot][1], biet, tranh)[0] == ds[tot][0]:
            kq[tot] = (con_lai[0], biet.get(con_lai[0]) or ds[tot][1])
            cho.remove(tot)
    for i in cho:
        kq[i] = sua_ten_loai(ds[i][0], ds[i][1], biet, tranh)   # 30/10/2026: tên loài bản scan đọc sai -> tên đã biết
    return kq


def tach_theo_loai(ds: list, nhom_loai: dict | None = None) -> tuple:
    """Dòng bảng giá theo NHÓM loài cây lâm nghiệp ("Nhóm IV gồm … loài" x cỡ đường kính) -> mỗi loài trong nhóm một dòng mỗi cỡ:
    "Bồ đề (d >6-9 cm)", "Trường (…) (d >6-9 cm)"… (người dùng 30/10/2026: "tách từng loại cây"). Loài của nhóm: danh sách trong văn
    bản (doc_nhom_loai - Phụ lục VI); văn bản không có danh sách thì suy từ bộ đơn giá đang dùng: các loài có ĐÚNG bảng giá theo cỡ của
    nhóm (giá không đổi). Trả (ds mới, [nhóm không tách được])."""
    nhom_loai = nhom_loai or {}
    theo_nhom = {}
    for m in ds:
        if m.nhom_loai:
            theo_nhom.setdefault(m.nhom_loai, []).append(m)
    if not theo_nhom:
        return ds, []
    con = csdl.mo(don_gia.file_dang_dung(), chi_doc=True)
    try:
        bo = _loai_trong_bo([dict(r) for r in con.execute('SELECT ma, ten, dvt, don_gia FROM dm_taisan WHERE nhom = 3 ORDER BY rowid')])
    finally:
        con.close()
    from .ten_cay_lam_nghiep import TEN_KHAC, ten_khac
    biet = {t: ten_khac(t) for t in bo}
    biet.update(TEN_KHAC)
    loai_nhom, khong = {}, []

    def kk(x):
        return ' '.join(re.sub(r"[^\w ]+", ' ', bo_dau(x).lower()).split())
    da_ghi = {kk(t) for v in nhom_loai.values() for t, _ in v}       # loài văn bản đã ghi (đọc được tên)
    for k, dong in theo_nhom.items():
        if nhom_loai.get(k):
            ds_loai = []
            # tên loài đọc đúng ở nhóm khác của văn bản: không sửa tên sai chữ thành tên đó ("Sc đỏ" nhóm III không phải "Sấu đỏ" nhóm IV)
            tranh = {t for k2, v in nhom_loai.items() if k2 != k for t, _ in v}
            ds_loai = _sua_ten_nhom(nhom_loai[k], biet, tranh, _loai_cung_gia(dong, bo, da_ghi))
            loai_nhom[k] = [(t, khac or ten_khac(t)) for t, khac in ds_loai]
            continue
        gia = {_khoa(m.duong_kinh): m.don_gia for m in dong}
        cung = [loai for loai, co in (bo or {}).items()
                if set(co) == set(gia) and all(doc_gia(co[c]['don_gia']) == g for c, g in gia.items())]
        if cung:
            loai_nhom[k] = [(t, ten_khac(t)) for t in cung]
        else:
            khong.append(dong[0].ten.rsplit('(', 1)[0].strip())
    kq = []
    for m in ds:
        ds_loai = loai_nhom.get(m.nhom_loai) if m.nhom_loai else None
        if not ds_loai:
            kq.append(m)
            continue
        for t, khac in ds_loai:
            ten = f'{t} ({", ".join(khac)}) {m.duong_kinh}' if khac else f'{t} {m.duong_kinh}'
            kq.append(Muc(ten, m.dvt, m.don_gia, '', m.nguon_dong, nhom=m.nhom, ghi_chu=m.ghi_chu, duong_kinh=m.duong_kinh,
                          ten_loai=t, nghi_gia=m.nghi_gia))
    # thứ tự như bộ đơn giá: từng loài đủ các cỡ đường kính (văn bản ghi từng nhóm theo cỡ)
    vt = {id(m): i for i, m in enumerate(kq)}
    dau = {}
    for m in kq:
        if m.ten_loai:
            dau.setdefault(m.ten_loai, vt[id(m)])
    kq.sort(key=lambda m: (dau[m.ten_loai], vt[id(m)]) if m.ten_loai else (vt[id(m)], 0))
    return kq, khong


def tach_mat_do_ten(ten: str) -> tuple:
    """"Cây cam (Mật độ 1.111 cây/ha)" / "Cây vải thiều (330 cây/ha)" -> ("Cây cam", "Mật độ 1.111 cây/ha"). Ngoặc khác giữ trong
    tên ("Cây mận (roi) (Mật độ 493 cây/ha)" -> "Cây mận (roi)"). Không có mật độ: (tên, '')."""
    for m in _RE_MAT_DO_TEN.finditer(ten):
        if m.group(1) or re.match(r'(?i)\s*[(“"«]\s*m[ậa]t\s*[đd][ộo]', m.group(0)):
            so, dv = m.group(1), m.group(2)
            gc = f'Mật độ {so} {dv}/ha' if so else ' '.join(m.group(0).strip(' ()').split())
            return ' '.join((ten[:m.start()] + ' ' + ten[m.end():]).split()), gc
    return ten, ''


_RE_STT_DONG = re.compile(r'^(?:(?P<stt>\d{1,3}[a-z]?|[IVXL]{1,5})[.)]?\s+(?=\S)|(?P<chu>[a-zđ])[.)]\s+|(?P<ma>[A-Z]{1,3}\d+)\s+)')
_RE_GACH = re.compile(r'^[-–—+•*]+\s*')
# "<tên> <ĐVT> <giá>" / "<tên> <ĐVT> <giá thấp> - <giá cao>" (ĐVT có thể kèm "đồng/": "Đồng/m2 581.000")
_RE_DONG_GIA = re.compile(rf'^(?P<ten>.+?)\s+(?P<dvt>{DVT})\s+(?P<g1>\d[\d.,]*)(?:\s*[-–—]\s*(?P<g2>\d[\d.,]*))?\s*(?:đồng|đ)?\.?$',
                          re.I)
# không có ĐVT: giá phải có dấu ngăn nghìn ("Hồ chứa … 259.000 - 576.000")
_RE_DONG_GIA_TRON = re.compile(r'^(?P<ten>.+?)\s+(?P<g1>\d{1,3}(?:[.,]\d{3})+)(?:\s*[-–—]\s*(?P<g2>\d{1,3}(?:[.,]\d{3})+))?\s*'
                               r'(?:đồng|đ)?\.?$')
_RE_DVT_CUOI = re.compile(rf'\s+(?:{DVT})$', re.I)
_RE_TIEU_DE_VB = re.compile(r'^(?:\(?\s*ban hanh kem theo|phu luc\b|quyet dinh so|dieu \d|chuong\s+(?:[ivxl]+|\d+)\b|'
                            r'(?:stt|tt)\b.*(?:ten|don gia)|'
                            r'ten (?:tai san|cay|cong trinh).*don gia)')
# "muc" = Mục (bỏ dấu) - không phải "Mức bồi thường / hỗ trợ / giá…" (1.0.57)
_RE_TIEU_DE_NHOM = re.compile(r'^(?:nhom|phan|muc(?!\s+(?:boi|ho tro|gia|chi|thuong))|phu luc)\b')
# 1.0.57 (người dùng 03/11/2026, QĐ 18/2026 hợp nhất - PDF có chữ): bảng đơn giá nhà đọc theo dòng: "Đồng/m²" một dòng, "sàn 9.445.000"
# dòng sau (trước: thành mục tên "Đồng/m² sàn"); giá nằm cuối khối mô tả kết cấu, tên ở dòng nhóm + dòng "* Kết cấu loại 1:"
_RE_CHI_DVT = re.compile(rf'(?:(?:đồng|đ)\s*/\s*(?:{_DVT_GOC})|m²|m2|m³|m3)(?:\s+sàn(?:\s+xây\s+dựng)?)?', re.I)
_RE_CHI_GIA = re.compile(rf'(?P<ten>(?:sàn(?:\s+xây\s+dựng)?|(?:đồng|đ)\s*/\s*(?:{_DVT_GOC})(?:\s+sàn)?)\s+)?'
                         r'(?P<g1>\d{1,3}(?:[.,]\d{3})+)\s*(?:đồng|đ)?\.?', re.I)


_RE_MO_TA = re.compile(r'(?:^|\s)\*?\s*(Kết cấu(?:\s+loại\s+\d+)?|Vật liệu hoàn thiện)\s*:\s*', re.I)


def _tach_mo_ta(ten: str) -> tuple:
    """Ô tên bảng đơn giá nhà (bản Word) lẫn mô tả kết cấu: "1.1 * Kết cấu loại 1: - Khung cột: …" / "Kết cấu: Móng…" / "Nhà bán kiên
    cố Kết cấu: Cột gỗ…" -> (phần tên đứng trước, "Kết cấu…: mô tả", "Kết cấu loại 1" hoặc ''). Không có mô tả: (ten, '', '')."""
    s = re.sub(r'^\d+(?:\.\d+)+\s+', '', ten or '').lstrip('* ').strip()
    m = _RE_MO_TA.search(s)
    if not m:
        return ten, '', ''
    truoc = s[:m.start()].strip(' -–:;,*')
    nhan = ' '.join(m.group(1).split())
    sau = s[m.end():].strip()
    loai = nhan[:1].upper() + nhan[1:] if re.search(r'(?i)loại\s+\d', nhan) else ''
    return truoc, f'{nhan}: {sau}'.strip(' :'), loai


def _dvt_nha(d: str) -> str:
    """"Đồng/m² sàn" -> "m²" (bộ đơn giá ghi ĐVT nhà là m²)."""
    d = re.sub(r'(?i)\s+sàn(?:\s+xây\s+dựng)?$', '', chuan_dvt(d)).strip()
    return '' if bo_dau(d).startswith('san') else d
# chú thích cuối trang của văn bản hợp nhất: "Mục này được sửa đổi theo quy định tại khoản 2 Điều 3…", "UBND, có hiệu lực kể từ ngày…"
_RE_CHU_THICH_TRANG = re.compile(r'(?:muc|phu luc|dieu|khoan|diem) nay (?:duoc|da)|co hieu luc ke tu|hieu luc k\w? tu ngay|'
                                 r'theo quy dinh tai khoan \d+ dieu')
_RE_STT_HOP_LE = re.compile(r'[(\s]*(?:\d{1,3}[a-z]?|[IVXLHJÏ]{1,6}|[a-zđ]|[-+–•*]+|\d+\.\d+)[.):\'"’”°,]*\s*')


# 1.0.58 - Phụ lục II bản PDF đọc theo dòng (QĐ 18/2026): ĐVT xuống dòng ("… đồng/m" + "sâu 631.000", "đồng/giế" + "ng" + "277.000"); bảng
# "Loại | Quy mô, kết cấu": tên ở dòng "Nhà …", mô tả nhiều dòng, số loại rơi lẫn vào dòng mô tả, giá một dòng riêng
_RE_DVT_MO = re.compile(r'^(?P<ten>.*?)\s*(?:đồng|đ)\s*/\s*(?P<dv>[^\s/]+)$', re.I)
_RE_SO_TIEN = re.compile(r'\d{1,3}(?:[.,]\d{3})+')
_RE_NOI_DVT_GIA = re.compile(r'(?P<du>[^\d/]{1,12}?)\s+(?P<g>\d{1,3}(?:[.,]\d{3})+)')
_RE_NOI_DVT = re.compile(r'[^\W\d_]+(?: [^\W\d_]+)?')
_RE_LOI_GIA_THEM = re.compile(r'(?i)(?:tính thêm|tăng thêm|giảm trừ|giảm)\s*$')     # "… thì tính thêm 110.000" (đồng/m² ở dòng sau): lời văn
_RE_TEN_LOAI = re.compile(r'^(?:Nhà|Công trình|Biệt thự)\b')
_RE_MO_TA_LOAI = re.compile(r'^(?:Kết cấu|Vật liệu hoàn thiện|Phần diện tích)\b')


def _tu_dau_chu(ten: str) -> str:
    m = re.match(r'\W*(\w+)', bo_dau(ten or ''))
    return m.group(1) if m else ''


def _la_ma_ocr(stt: str) -> bool:
    """STT tiêu đề nhóm số La Mã kể cả bản scan đọc sai ("IH", "VHI", "Ï")."""
    return bool(re.fullmatch(r'[IVXLHJÏ]{1,6}\.?', stt)) and bool(re.search(r'[IVX]', stt))


def _tieu_de_van_ban(chu: str) -> bool:
    """Dòng chữ ngoài bảng giá: tiêu đề phụ lục / điều / dòng tiêu đề cột / chữ IN HOA - không làm dòng cha của mục giá."""
    k = bo_dau(chu).strip()
    chu_cai = [c for c in chu if c.isalpha()]
    return bool(_RE_TIEU_DE_VB.match(k)) or bool(_RE_CHU_THICH_TRANG.search(k)) or (len(chu_cai) >= 6 and all(c.isupper() for c in chu_cai)) or len(chu) > 220


class _DocDong:
    """Đọc từng DÒNG CHỮ (bản scan đọc theo dòng, bảng dán không có tiêu đề cột, PDF có chữ không bảng) - 02/11/2026 (người dùng: văn
    bản hợp nhất đơn giá nhà, công trình; bản scan đọc mất tên dòng cha, khoảng giá "259.000 - 720.000", ĐVT "mét", "Đồng/m2").

    - Dòng không giá: dòng cha của các dòng con sau nó; dòng quy định cách tính ("…được tính thêm 50% mức giá trên") -> quy_tac;
      dòng chữ thường / bắt đầu bằng số đo ("2,2 m") nối vào dòng trước (ô tên xuống dòng).
    - Dòng con: bắt đầu "-", "+", "•" hoặc chữ thường -> "Cha - Con"; dòng cha chưa kết thúc (dấu phẩy, chưa có dòng con) mà dòng
      sau chữ thường có giá -> cùng một tên (ô tên xuống dòng, giá nằm giữa ô).
    - STT ô gộp dọc nằm giữa nhóm (bản scan đặt số vào dòng giữa): dòng có STT không cắt nhóm khi dòng cha không có STT và đứng sau
      STT gần nhất.
    - Khoảng giá "a - b": hai mục cùng tên - mức cao tên có dấu chấm cuối (quy ước của bộ đơn giá: "Mái che, mái hiên" / "Mái che,
      mái hiên.")."""

    def __init__(self, kq: list, nhom: int, quy_tac: list | None):
        self.kq, self.nhom, self.quy_tac = kq, nhom, quy_tac
        self.nhom_muc = 0
        self.cuoi = None                  # ('muc', [Muc]) / ('cha',) / ('th',) / ('qt', i) / ('mo_ta',)
        self.duoi = ''                    # dấu phẩy / chấm phẩy cuối tên mục vừa đọc (ô tên xuống dòng: nối giữ dấu)
        self.dvt_cho = ''                 # 1.0.57: dòng chỉ có ĐVT ("Đồng/m²") - ĐVT của dòng giá kế tiếp ("sàn 9.445.000")
        self.dvt_bang = ''                # ĐVT ghi ở dòng tiêu đề bảng ("Đơn giá (đồng/m2 sàn)")
        self.dvt_mo = False               # 1.0.58: ĐVT vừa đọc có thể còn phần ở dòng sau ("đồng/m" + "sâu 631.000")
        self.bang_stt = False             # 1.0.58: bảng "STT | Danh mục | ĐVT | Đơn giá": mỗi mục một STT, dòng không STT là ô tên xuống dòng
        self.bang_loai = None             # 1.0.58: bảng "Loại | Quy mô, kết cấu | Đơn giá" (_doc_bang_loai)
        self.loai_stt = None              # {id(Muc): số loại} - nhan_muc._ten_theo_loai
        self._bo_cha()

    def _bo_cha(self):
        self.cha = self.th = self.cha_ket = self.kieu_con = self.mat_do = self.cha_ngu_canh = ''
        self.so_con = 0
        self.cha_sau_stt = False
        self.mo_ta = False                # 1.0.57: đang đọc phần mô tả kết cấu ("* Kết cấu loại 1:" / "Kết cấu:" + các dòng "- Khung cột…")

    def _ten_ngu_canh(self) -> str:
        """Tên mục khi dòng giá không ghi tên (bảng đơn giá nhà: tên ở dòng nhóm + dòng kết cấu, giá ở dòng cuối khối mô tả)."""
        return ' - '.join(x for x in (self.cha, self.th) if x)

    def _tieu_de_bang(self, s: str) -> bool:
        """1.0.57 - dòng tiêu đề bảng của PDF có chữ đọc theo dòng (QĐ 18/2026 Phụ lục Ia: "STT Nhà từ 05 tầng trở lên Đơn vị" - ô tên
        của dòng nhóm đầu bảng nằm chung dòng tiêu đề; Phụ lục Ib "STT Loại biệt thự Đơn giá (đồng/m2"); mảnh tiêu đề xuống dòng ("tính
        Đơn giá", "sàn)"). Trả True = đã xử lý dòng."""
        k = bo_dau(s)
        if self.bang_loai is not None and self.bang_loai['tieu_de']:      # mảnh tiêu đề "Đơn giá bồi / thường (đồng/m2 / sàn xây dựng)"
            md = re.search(r'dong\s*/\s*(m2|m²|m3|m³|m)\b', k)
            if md:
                self.dvt_bang = chuan_dvt(md.group(1))
            if re.fullmatch(r'[\d\s]+', s):                 # hàng số cột "1 2 3": hết tiêu đề
                self.bang_loai['tieu_de'] = False
            return True
        if re.match(r'loai\s+quy mo', k):
            self.bang_loai = dict(tieu_de=True, dem=0, ten='', mo_ta=[], da_gia=False, muc=None)
            self.bang_stt, self.dvt_bang = False, ''
            self._bo_cha()
            self.cuoi = None
            return True
        if re.fullmatch(r'(?:stt|tt)\s+danh muc', k):       # tiêu đề xuống dòng: "STT Danh mục" / "Đơn vị" / "tính Đơn giá"
            self.bang_stt, self.dvt_bang = True, ''
            self._bo_cha()
            self.cuoi = None
            return True
        if re.fullmatch(r'(?:tinh|don vi(?: tinh)?|dvt|don gia|\(?dong\)?|san\)?|xay dung\)?|[\s().,/])+', k):
            return True                                     # mảnh tiêu đề cột xuống dòng
        m = re.match(r'(?:stt|tt)\s+(.*?)\s*(?:don vi(?: tinh)?|dvt|don gia)\b(.*)$', k)
        if not m or re.search(r'\d{1,3}(?:[.,]\d{3})+', s):
            return False
        giua = s[len(s) - len(k) + k.index(m.group(1)):][:len(m.group(1))].strip() if m.group(1) else ''
        md = re.search(r'dong\s*/\s*(m2|m²|m3|m³|m)\b', m.group(2))
        self.dvt_bang = chuan_dvt(md.group(1)) if md else ''    # mỗi bảng một tiêu đề: không mang ĐVT bảng trước sang
        self._bo_cha()
        self.cuoi = None
        kg = bo_dau(giua)
        if not giua or re.match(r'(ten|noi dung|hang muc|danh muc)\b', kg):
            self.bang_stt = kg.startswith('danh muc')
            return True
        if kg.startswith('loai '):                          # "Loại biệt thự" -> dòng cha "Biệt thự" (tên mục "Biệt thự Song lập")
            giua = giua[5:].strip()
            giua = giua[:1].upper() + giua[1:]
            self.kieu_con = 'noi'
        self.cha = giua.rstrip(' .;:')
        self.cha_sau_stt = True
        self.cuoi = ('cha',)
        return True

    def _ghi_quy_tac(self, chu: str, ngu_canh: str = ''):
        if self.quy_tac is None:
            self.cuoi = None
            return
        self.quy_tac.append(f'{ngu_canh}: {chu}' if ngu_canh else chu)
        self.cuoi = ('qt', len(self.quy_tac) - 1)

    def _noi_dvt(self, du: str) -> None:
        """Phần ĐVT ở dòng sau: "m" + "sâu" -> "m sâu"; "giế" + "ng" -> "giếng"."""
        self.dvt_cho = f'{self.dvt_cho} {du}' if len(self.dvt_cho) <= 2 else self.dvt_cho + du

    def _doc_bang_stt(self, s: str) -> str | None:
        """Bảng mỗi mục một STT (1.0.58): dòng không STT, không giá là ô tên xuống dòng (kể cả chữ hoa, "(…)"); giá trong ngoặc chưa đóng
        không phải giá của mục. Trả None = đã xử lý xong dòng; chữ = dòng còn lại để đọc tiếp."""
        if _RE_TIEU_DE_VB.match(bo_dau(s)) and not _RE_STT_DONG.match(s):
            self.bang_stt = False
            return s
        if re.fullmatch(r'\d{1,3}', s):                     # STT đứng riêng / số trang: hết mục trước
            self._bo_cha()
            self.dvt_cho, self.dvt_mo, self.cuoi = '', False, None
            return None
        dang_ten = self.cha and self.cuoi and self.cuoi[0] == 'cha'
        if dang_ten and (f'{self.cha} {s}'.count('(') > f'{self.cha} {s}'.count(')')
                         or (s[0] in ');' and self.cha.count('(') > self.cha.count(')'))):
            self._noi_ten(s)
            return None
        if self.dvt_mo and self.cha:
            m = _RE_NOI_DVT_GIA.fullmatch(s)
            if m:
                self._noi_dvt(m.group('du'))
                self._gia_ngu_canh('', m.group('g'), s)
                return None
            if len(s) <= 12 and _RE_NOI_DVT.fullmatch(s):
                self._noi_dvt(s)
                return None
        m = _RE_DVT_MO.match(s)
        if m and not _RE_SO_TIEN.search(m.group('ten')):
            self.dvt_cho, self.dvt_mo = chuan_dvt(m.group('dv')), True
            s = m.group('ten').strip()
            if not s:
                return None
        if dang_ten and not self.so_con and not _RE_SO_TIEN.search(s[-12:]) and not _RE_STT_DONG.match(s) and not _RE_GACH.match(s):
            self._noi_ten(s)
            return None
        return s

    def _noi_ten(self, s: str) -> None:
        ket = self.cha_ket if self.cha_ket in ('.', ';', ',') and not self.cha.endswith(self.cha_ket) else ''
        self.cha = f'{self.cha}{ket}{s}' if s[0] in ');' else f'{self.cha}{ket} {s}'
        self.cha_ket = s.rstrip()[-1:]

    def _doc_bang_loai(self, s: str) -> bool:
        """Bảng "Loại | Quy mô, kết cấu công trình | Đơn giá" đọc theo dòng (1.0.58): tên ở dòng "Nhà …", mô tả "Kết cấu: …", "Vật liệu hoàn
        thiện: …" nhiều dòng -> ghi chú; số loại nằm giữa ô rơi vào đầu / cuối một dòng bất kỳ và lẫn với số trang -> bỏ, số loại = thứ tự
        mục trong nhóm A / B; giá một dòng riêng hoặc cuối dòng tên / mô tả. False = hết bảng (dòng đọc tiếp như thường)."""
        L = self.bang_loai
        if _RE_TIEU_DE_VB.match(bo_dau(s)):
            self._ket_loai()
            self.bang_loai = None
            return False
        if re.fullmatch(r'\d{1,2}', s):
            return True
        if re.match(r'^[A-ZĐ]\.\s+\w', s):                 # "A. Nhà, nhà ở" / "B. Nhà xưởng"
            self._ket_loai()
            L['dem'] = 0
            self.nhom_muc = nhom_theo_chu(s) or self.nhom_muc
            return True
        s = re.sub(r'^\d{1,2}\s+(?=\S)', '', s)
        if not _RE_TEN_LOAI.match(s):                   # "Nhà tạm 1": số thuộc tên
            s = re.sub(r'\s+\d{1,2}$', '', s)
        mg = re.search(r'(?:^|\s)(\d{1,3}(?:[.,]\d{3})+)\s*$', s)
        than = s[:mg.start()].strip() if mg else s
        if than:
            self._chu_loai(than)
        if mg and L['ten'] and not L['da_gia']:
            L['dem'] += 1
            self._them(L['ten'].rstrip(' .;:'), self.dvt_bang, doc_gia(mg.group(1)), None, '', s, '', '; '.join(L['mo_ta']), '')
            L['muc'], L['da_gia'] = self.kq[-1], True
            if self.loai_stt is not None:
                self.loai_stt[id(L['muc'])] = str(L['dem'])
        return True

    def _chu_loai(self, than: str) -> None:
        L = self.bang_loai
        if _RE_TEN_LOAI.match(than):
            self._ket_loai()
            m = re.search(r'\s(?=Kết cấu\b|Vật liệu hoàn thiện\b)', than)     # "Nhà nuôi yến Kết cấu khung chịu lực …": tên + mô tả một dòng
            ten, mo_ta = (than[:m.start()], than[m.end():]) if m else (than, '')
            L.update(ten=ten, mo_ta=[mo_ta] if mo_ta else [], da_gia=False, muc=None)
        elif _RE_MO_TA_LOAI.match(than):
            L['mo_ta'].append(than)
        elif L['mo_ta']:
            L['mo_ta'][-1] = f'{L["mo_ta"][-1]} {than}'
        elif L['ten'] and not L['da_gia']:
            L['ten'] = f'{L["ten"]} {than}'
        if L['muc'] is not None and not _RE_TEN_LOAI.match(than):
            L['muc'].ghi_chu = '; '.join(L['mo_ta'])

    def _ket_loai(self) -> None:
        """Hết một tên: tên không có giá mà có mô tả ("Nhà nuôi yến kết hợp ở: Phần diện tích để ở …") là quy định cách tính."""
        L = self.bang_loai
        if L['ten'] and not L['da_gia'] and L['mo_ta'] and self.quy_tac is not None:
            self.quy_tac.append(f'{L["ten"]}: {" ".join(L["mo_ta"])}')
        L.update(ten='', mo_ta=[], da_gia=False, muc=None)

    def doc(self, s: str):
        s = ' '.join(str(s or '').split())
        if not s:
            return
        s = re.sub(r'(?i)\bdông\s*/', 'đồng/', s)           # văn bản gõ sai "dông/m2"
        if self.bang_stt:
            s = self._doc_bang_stt(s)
            if s is None:
                return
        if self._tieu_de_bang(s):
            return
        if self.bang_loai is not None and self._doc_bang_loai(s):
            return
        if _RE_CHI_DVT.fullmatch(s):                        # dòng chỉ có ĐVT ("Đồng/m²"): ĐVT của dòng giá kế tiếp
            self.dvt_cho = _dvt_nha(s)
            return
        mgt = _RE_CHI_GIA.fullmatch(s)
        if mgt and (self.mo_ta or self.dvt_cho or (mgt.group('ten') and self.so_con == 0)) and self.cha:
            # dòng chỉ có giá ("sàn 9.445.000", "đồng/m3 42.000"), tên ở dòng nhóm / kết cấu / ô tên nhiều dòng phía trên
            self._gia_ngu_canh(mgt.group('ten') or '', mgt.group('g1'), s)
            return
        stt = ma = ''
        m = _RE_STT_DONG.match(s)
        if m and len(s) > m.end():
            stt, ma = m.group('stt') or m.group('chu') or '', m.group('ma') or ''
            s = s[m.end():]
        gach = bool(_RE_GACH.match(s))
        than = _RE_GACH.sub('', s).strip()
        if not than:
            return
        mg = _RE_DONG_GIA.match(than) or _RE_DONG_GIA_TRON.match(than)
        g1 = g2 = None
        if mg:
            if mg.group('g2'):
                k = doc_khoang_gia(f"{mg.group('g1')} - {mg.group('g2')}")
                g1, g2 = k if k else (None, None)
            else:
                g1 = doc_gia(mg.group('g1'))
            if g1 is not None and g1 < GIA_TOI_THIEU:
                g1 = None
        if g1 and mg.group('ten').rstrip().endswith(':'):      # lời văn "Cá thịt: 45.000" (ĐVT ở dòng sau) - không phải dòng bảng
            g1 = None
        if g1 and not mg.groupdict().get('dvt') and _RE_LOI_GIA_THEM.search(mg.group('ten')):
            g1 = None
        ten = mg.group('ten').strip(' -–:;,') if g1 else ''
        self.duoi = (re.search(r'[,;]\s*$', mg.group('ten')) or [''])[0].strip() if g1 else ''
        if not g1 or not ten or re.fullmatch(r'[\d\W]+', ten):
            self._sao = s.startswith('*')
            self._khong_gia(than, stt, gach)
            return
        dvt = chuan_dvt(mg.groupdict().get('dvt') or '') or self.dvt_bang
        thuong = ten[:1].islower()
        con = gach or thuong
        if self.cha:
            if self.kieu_con == 'noi':
                giu = True                                  # "Loại biệt thự": 1 Song lập, 2 Đơn lập… cùng dòng cha
            elif stt and not self.cha_sau_stt:
                giu = False
            else:
                giu = con or self.so_con == 0 or self.kieu_con == 'tron'
            if not giu:
                self._bo_cha()
        if stt:
            self.cha_sau_stt = False
        cha_cua, gc = '', ''
        if self.cha and self.kieu_con == 'noi':
            cha_cua, ten = self.cha, f'{self.cha} {ten}'
            self.so_con += 1
        elif self.cha:
            if not gach and self.so_con == 0 and ((thuong and self.cha_ket not in (':', ')')) or self.bang_stt):
                ten = f'{self.cha} {ten}'                           # dòng cha xuống dòng: cùng một mục
                gc = self.mat_do
                self._bo_cha()
            else:
                cha_cua, gc = self.cha, self.mat_do
                if gach and not self.th and bo_dau(ten).split()[:1] == bo_dau(self.cha).split()[:1]:
                    pass                                    # dòng con tự đủ tên ("- Chuồng gà, vịt thô sơ" dưới "Chuồng heo, …:")
                elif self.th and thuong and not gach and self.cuoi and self.cuoi[0] == 'th':
                    # dòng con xuống dòng: "- Xây gạch cao 1m, nền bê tông kiên cố, lợp" / "ngói hoặc tole fibro ciment m² 961.000"
                    ten = f'{self.cha} - {self.th} {ten}'
                    self.th = ''
                else:
                    ten = ' - '.join(x for x in (self.cha, self.th, ten) if x)
                self.so_con += 1
                self.kieu_con = self.kieu_con or ('gach' if con else 'tron')
        else:
            ten, gc = tach_mat_do_ten(ten)
        self._them(ten, dvt, g1, g2, ma, s, cha_cua, gc,
                   f"{mg.group('g1')} - {mg.group('g2')}" if g2 else '')

    def _gia_ngu_canh(self, duoi: str, g1s: str, nguon: str):
        """Dòng chỉ có giá ("sàn 9.445.000", "7.052.000") cuối khối mô tả: tên = dòng nhóm + dòng kết cấu, ĐVT ở dòng trên / tiêu đề."""
        g = doc_gia(g1s)
        if g is None or g < GIA_TOI_THIEU:
            return
        dvt = self.dvt_cho or (_dvt_nha(duoi) if re.search(r'[^\W\d_]', duoi) else '') or self.dvt_bang
        ten = self._ten_ngu_canh()
        self._them(ten, dvt, g, None, '', f'{self.cha} | {self.th} | {nguon}'.replace(' |  | ', ' | '), self.cha if self.th else '', '', '')
        self.so_con += 1
        self.th = ''

    def _them(self, ten, dvt, g1, g2, ma, nguon, cha, gc, khoang):
        self.mo_ta = False
        self.dvt_cho = ''
        self.dvt_mo = False
        nh = self.nhom or self.nhom_muc or _nhom_dong(ten, dvt)
        if g2:
            ds = [Muc(ten, dvt, g1, ma, nguon, nhom=nh, ghi_chu=gc, cha=cha, muc_gia='thap', khoang=khoang),
                  Muc(ten + '.', dvt, g2, '', nguon, nhom=nh, ghi_chu=gc, cha=cha, muc_gia='cao', khoang=khoang)]
        else:
            ds = [Muc(ten, dvt, g1, ma, nguon, nhom=nh, ghi_chu=gc, cha=cha)]
        self.kq.extend(ds)
        self.cuoi = ('muc', ds)

    def _khong_gia(self, than: str, stt: str, gach: bool):
        # 1.0.57: khối mô tả kết cấu của bảng đơn giá nhà - "* Kết cấu loại 1:" (tên phụ của mục), "Kết cấu:" + "- Khung cột: …",
        # "Vật liệu hoàn thiện: …": không phải tên mục / dòng cha (trước: mỗi dòng "- Khung cột" thay tên phụ, dòng hoa thành dòng cha)
        sao, self._sao = getattr(self, '_sao', False), False
        k0 = bo_dau(than)
        if self.cha and sao and not stt:
            self.th = than.rstrip(' .;:')
            self.mo_ta = True
            self.cuoi = ('mo_ta',)
            return
        if self.cha and re.match(r'ket cau(?: chinh)?\s*:', k0) and not stt:
            self.mo_ta = True
            self.cuoi = ('mo_ta',)
            return
        if self.mo_ta and (not stt or than[:1].islower()):
            self.cuoi = ('mo_ta',)
            return
        noi = not stt and not gach and (than[:1].islower() or re.match(r'\d+(?:[.,]\d+)?\s*(?:m|cm|mm|m²|m³|mét)\b', than))
        if not noi:
            than = _RE_DVT_CUOI.sub('', than).strip()      # dòng hướng dẫn ghi kèm ĐVT ("… mức giá trên mét")
        if not than:
            return
        k = bo_dau(than)
        if _tieu_de_van_ban(than) or _LA_MA.match(stt) or (not stt and _RE_TIEU_DE_NHOM.match(k)):
            if _LA_MA.match(stt) or _RE_TIEU_DE_NHOM.match(k):
                self.nhom_muc = nhom_theo_chu(than) or self.nhom_muc
            self._bo_cha()
            self.cuoi = ('tieu_de',)                        # 1.0.57: dòng chữ thường sau tiêu đề là phần tiêu đề xuống dòng
            return
        if not stt and not gach and not noi and re.match(r'(muc (boi thuong|ho tro)|truong hop)\b', k) and len(than.split()) > 8:
            # 1.0.57: câu dẫn nhóm ("Mức bồi thường, hỗ trợ chi phí di dời … trong trường hợp di dời mồ mả đến vị trí mới …" - QĐ 18/2026)
            # không phải tên dòng cha của các mục bên dưới (trước: thành tiền tố "dời mồ mả … - Mộ xây ốp đá hoa cương")
            self._bo_cha()
            self.cuoi = ('tieu_de',)
            return
        if noi and self.cuoi:                               # ô tên xuống dòng: nối vào dòng trước
            loai = self.cuoi[0]
            if loai in ('tieu_de', 'mo_ta'):
                return
            if loai == 'muc':
                for x in self.cuoi[1]:
                    goc = x.ten[:-1] if x.muc_gia == 'cao' else x.ten
                    x.ten = f'{goc}{self.duoi} {than.rstrip(" .;:")}' + ('.' if x.muc_gia == 'cao' else '')
                    x.nguon_dong += ' ' + than
                self.duoi = ''
                return
            if loai == 'qt':
                self.quy_tac[self.cuoi[1]] += ' ' + than
                return
            if loai == 'th':
                self.th = f'{self.th} {than}'.strip(' .;:')
                return
            self.cha = f'{self.cha} {than}'
            self.cha_ket = than.rstrip()[-1:]
            self.cha, self.mat_do = tach_mat_do_ten(self.cha.rstrip(' .;:'))
            if la_quy_tac(self.cha):                        # câu hướng dẫn xuống dòng, không phải dòng cha
                c, ngu = self.cha, self.cha_ngu_canh
                self._bo_cha()
                self._ghi_quy_tac(c, ngu)
            return
        if re.fullmatch(r'[\d\W]+', than):                  # mẩu số / dấu lạc (STT, số trang)
            return
        muc_truoc = self.cuoi[1][0].ten if self.cuoi and self.cuoi[0] == 'muc' else ''
        if la_quy_tac(than):
            ngu = muc_truoc if gach else self.cha
            self._ghi_quy_tac(than.rstrip(' ;'), ngu)
            return
        if gach and self.cha and not stt:                   # "29 - Chuồng heo, chuồng bò, gà, vịt:" (có STT) là dòng cha mới
            self.th = than.rstrip(' .;:')
            self.cuoi = ('th',)
            return
        self._bo_cha()
        self.cha, self.mat_do = tach_mat_do_ten(than.rstrip(' .;:'))
        self.cha_ket = than.rstrip()[-1:]
        self.cha_sau_stt = not stt
        self.cha_ngu_canh = muc_truoc if gach else ''      # dòng gạch đầu dòng sau mục: có thể là câu hướng dẫn của mục đó
        self.cuoi = ('cha',)


class _HangGia:
    """Một hàng của bảng đơn giá đã bóc: tên, STT, ô giá."""
    __slots__ = ('r', 'stt', 'ten', 'ten_o_stt', 'gc_mt', 'la_mo_ta', 'gach', 'g', 'nhan_gia', 'khoang', 'nhieu', 'nghi', 'o_gia', 'dk')


class _DocBangGia:
    """Trạng thái đọc bảng đơn giá theo cột của nhan_muc: tiêu đề cột đang dùng, dòng cha, dòng con, mục vừa đọc."""

    def __init__(self, nhom: int, quy_tac: list | None):
        self.nhom, self.quy_tac = nhom, quy_tac
        self.kq, self.tieu_de, self.nhan = [], None, 1
        self.cha = self.truong_hop = self.truoc = self.dvt_mac_dinh = self.mat_do = self.mat_do_bang = self.nhom_dk = ''
        self.nhom_muc = self.so_cot = 0
        self.stt_cha = self.con_truoc = self.dk_truoc = ''
        self.doc_dong = _DocDong(self.kq, nhom, quy_tac)
        self.kv, self.n_kv = '', 0
        self.mo_ta_cho = self.tien_to_bang = ''  # 1.0.57: mô tả kết cấu chờ gắn vào mục kế tiếp; tiền tố tên ("Biệt thự")
        self.la_loai_bang, self.n_cha, self.loai_stt = False, 0, {}
        self.doc_dong.loai_stt = self.loai_stt

    def gan_khu_vuc(self, r) -> None:
        for m_ in self.kq[self.n_kv:]:                    # 1.0.57: khu vực giá của phụ lục chứa dòng (tiêu đề "… KHU VỰC 2 …")
            m_.khu_vuc = m_.khu_vuc or self.kv
        self.n_kv = len(self.kq)
        mk = _RE_KHU_VUC.search(' '.join(str(c) for c in r if c))
        if mk:
            self.kv = mk.group(1)

    def doc_tieu_de(self, r, o) -> bool:
        """Hàng tiêu đề cột: ghi nhận cột, đặt lại dòng cha. True = hàng này đã xử lý xong."""
        kq = self.kq
        ten_c = _cot(o, r'^(ten|loai|noi dung|hang muc|danh muc|tai san|cay trong|nhom loai)', r'\bten (tai san|cay|cong trinh|khoan)')
        gia_c = _cot(o, r'^(don gia|gia|muc (ho tro|boi thuong)|muc gia)', r'don gia')
        stt_cot = _cot(o, r'^\s*(s\s?t\s?t|st|s[il1|f]t|stl|tt|so tt|so thu tu)\W*$')
        if ten_c is not None and gia_c is None and stt_cot is not None and len(r) >= 3 and ten_c < len(r) - 1 \
                and sum(1 for x in o if x.strip()) == len(r):
            gia_c = len(r) - 1                              # bản scan đọc sai chữ tiêu đề cột giá ("Đnn CÓ ác")
        # 1.0.57 (bản Word QĐ 18/2026): tiêu đề "Loại | Quy mô, kết cấu công trình | Đơn giá" - cột "Loại" là số loại nhà (STT), tên ở
        # cột "Quy mô…"; tiêu đề "STT | Nhà từ 05 tầng trở lên | Đơn vị tính | Đơn giá" - ô tên tiêu đề là dòng nhóm đầu bảng
        cha_dau, tien_to, la_loai = '', '', False
        if ten_c is not None and o[ten_c].strip() == 'loai':
            k2 = _cot(o[ten_c + 1:], r'^(quy mo|ket cau|ten|noi dung|danh muc|hang muc)')
            if k2 is not None:
                stt_cot, ten_c, la_loai = ten_c, ten_c + 1 + k2, True
        if ten_c is None and stt_cot is not None and gia_c is not None and gia_c > stt_cot + 1:
            dvt_t = _cot(o, r'^(dvt|don vi)', r'don vi tinh')
            giua = [i for i in range(stt_cot + 1, gia_c) if i != dvt_t and o[i].strip()]
            if len(giua) == 1 and not re.search(r'\d{1,3}(?:[.,]\d{3})+', r[giua[0]]):
                ten_c = giua[0]
                cha_dau = ' '.join(r[ten_c].split()).rstrip(' .;:')
        if ten_c is not None and gia_c is not None and ten_c != gia_c:
            mt = re.match(r'(?i)loại\s+(\w.*)$', ' '.join(r[ten_c].split()))
            if mt and not la_loai and not cha_dau and len(mt.group(1).split()) >= 2 and not re.match(
                    r'(cay|tai san|cong trinh|vat nuoi|ho tro|dat|nha cua|chinh sach)(\s|$)', bo_dau(mt.group(1))):
                # "Loại biệt thự" -> tên mục "Biệt thự Song lập" (không: "Loại cây", "Loại tài sản" - tiêu đề chung)
                tien_to = mt.group(1).strip()
                tien_to = tien_to[:1].upper() + tien_to[1:]
            dvt_c = _cot(o, r'^(dvt|don vi)', r'don vi tinh')
            ma_c = _cot(o, r'^(ma|ma so|ma ts|ma ho tro|ky hieu)$')
            stt_c = stt_cot
            if stt_c is None and ten_c > 0 and 0 not in (dvt_c, ma_c, gia_c):
                stt_c = 0                                   # cột đầu trước cột tên: STT (tiêu đề đọc sai "SIT")
            self.so_cot = len(r)
            # bảng giá cây lâm nghiệp theo nhóm loài x cỡ đường kính (bản scan hay dính chữ: "Đườngkính")
            dk_c = _cot(o, r'^duong ?kinh', r'^(d|dk|co)\s*\(?cm\)?$')
            if dk_c in (ten_c, gia_c):
                dk_c = None
            self.tieu_de = (ten_c, gia_c, dvt_c, ma_c, stt_c, dk_c)
            self.nhan = 1000 if any(re.search(r'nghin|1\.?000 ?d', x) for x in o) else 1
            # bảng không có cột ĐVT, đơn vị ghi ở tiêu đề cột giá: "Đơn giá bồi thường (đồng/ha)"
            md = re.search(r'(?i)(?:đồng|đ)\s*/\s*([^)]+)\)', r[gia_c])
            self.dvt_mac_dinh = md.group(1).strip() if md else ''
            # mật độ ghi ở tiêu đề cột tên: "Nhóm loài cây gỗ trồng trên cạn (mật độ chuẩn 833 cây/ha)"
            self.mat_do_bang = tach_mat_do_ten(' '.join(r[ten_c].split()))[1]
            self.cha = self.truong_hop = self.truoc = self.nhom_dk = self.mo_ta_cho = ''
            self.cha, self.tien_to_bang, self.la_loai_bang, self.n_cha = cha_dau, tien_to, la_loai, len(kq)
            if cha_dau:
                self.stt_cha = self.con_truoc = ''
            self.dvt_mac_dinh = _dvt_nha(self.dvt_mac_dinh) or self.dvt_mac_dinh if re.search(r'(?i)\bsàn', self.dvt_mac_dinh) else self.dvt_mac_dinh
            self.doc_dong._bo_cha()
            return True
        if stt_cot is not None and gia_c is None and len(r) >= 2 and not any(re.search(r'\d{1,3}(?:[.,]\d{3})+', str(c)) for c in r) \
                and o[stt_cot].strip() and not o[stt_cot].strip().isdigit():
            # 1.0.57: tiêu đề bảng khác không có cột giá ("STT | Kết cấu | Tỷ lệ còn lại", "STT | TÊN PHỤ LỤC") - hết bảng giá trước
            # (trước: các dòng của bảng mới đọc theo cột của bảng giá cũ -> mục rác "Kết cấu - 5 | 6 | 7")
            self.tieu_de = None
            self.cha = self.truong_hop = self.truoc = self.nhom_dk = ''
            self.doc_dong._bo_cha()
            return True
        return False

    def _boc_ten(self, r) -> _HangGia | None:
        """Bóc STT, tên, mô tả kết cấu của hàng. None = hàng là tiêu đề nhóm, đã xử lý xong."""
        ten_c, gia_c, dvt_c, ma_c, stt_c, dk_c = self.tieu_de
        if self.so_cot and len(r) > self.so_cot:                       # bản scan: mẩu chữ rác thành ô thừa bên trái - giữ ô đầu + các ô cuối
            r = [r[0]] + list(r[len(r) - self.so_cot + 1:])
        r = list(r) + [''] * (max(c for c in self.tieu_de if c is not None) + 1 - len(r))   # ô gộp: hàng ít ô hơn tiêu đề
        stt = r[stt_c].strip() if stt_c is not None else ''
        ten = ' '.join(r[ten_c].split()).rstrip(' .;:')
        ten_o_stt = False
        if stt and not _RE_STT_HOP_LE.fullmatch(stt):    # STT bản scan thành chữ rác ("—— h ị", "1ö")
            s_ = ' '.join(stt.split())
            if re.match(r'^[A-ZĐ]\.\s+\w', s_) and not any(re.search(r'\d{1,3}(?:[.,]\d{3})+', str(c)) for c in r[1:]):
                # 1.0.57: "A. Nhà, nhà ở" / "B. Nhà xưởng" ghi ở cột Loại - tiêu đề nhóm, không phải dòng cha
                self.nhom_muc = nhom_theo_chu(s_) or self.nhom_muc
                self.cha = self.truong_hop = self.truoc = self.mo_ta_cho = ''
                return None
            if stt_c != ten_c and len(re.findall(r'[^\W\d_]{2,}', s_)) >= 2:
                # 1.0.57: tên ghi ở cột Loại, cột tên là mô tả ("Nhà bán kiên cố | Kết cấu: Cột gỗ… | 1.660.000")
                ten_o_stt, mo_ta_o = True, ten
                ten = s_.rstrip(' .;:')
            stt = ''
        stt = stt.strip('( ')
        gc_mt, la_mo_ta = '', False
        if ten_o_stt:
            gc_mt = mo_ta_o
            self.cha = self.truong_hop = self.mo_ta_cho = ''
        else:
            truoc_mt, mo_ta_, loai_kc = _tach_mo_ta(ten)
            if mo_ta_:
                # 1.0.57: ô tên lẫn mô tả kết cấu ("* Kết cấu loại 1: - Khung cột: …", "Kết cấu: Móng…", "Vật liệu hoàn thiện: …")
                # -> tên "Kết cấu loại 1" (dưới dòng cha "Nhà từ 05 tầng trở lên"), mô tả vào ghi chú
                ten = ' - '.join(x for x in (truoc_mt, loai_kc) if x)
                gc_mt, la_mo_ta = mo_ta_, not ten
        if stt and self.cha and (stt == self.stt_cha or (self.con_truoc and _tu_dau_chu(ten) == self.con_truoc)):
            stt = ''                                    # STT ô gộp đọc lặp ở dòng con / vắt trang
        gach = bool(_RE_GACH.match(ten)) and not _CON.match(ten)
        if gach:                                        # dòng con ghi gạch đầu dòng trong ô tên ("- Ống 1 m Φ1m")
            ten = _RE_GACH.sub('', ten)
        d = _HangGia()
        d.r, d.stt, d.ten, d.ten_o_stt, d.gc_mt, d.la_mo_ta, d.gach = r, stt, ten, ten_o_stt, gc_mt, la_mo_ta, gach
        return d

    def _doc_o_gia(self, d: _HangGia) -> None:
        """Đọc ô giá (một giá, khoảng, nhiều mùa vụ, bản scan) và ô cỡ đường kính của hàng."""
        ten_c, gia_c, dvt_c, ma_c, stt_c, dk_c = self.tieu_de
        r = d.r
        g, nhan_gia = _tach_gia(r[gia_c])
        khoang = doc_khoang_gia(r[gia_c]) if not g else None
        nhieu = tach_nhieu_gia(r[gia_c]) if not g and not khoang else []
        nghi = ''
        o_gia = re.sub(r'^.{1,40}?:\s*', '', ' '.join(r[gia_c].split())) if nhan_gia else ' '.join(r[gia_c].split())
        if not g and re.fullmatch(r"[\W_]{1,4}\s*\d{1,3}(?:[.,]\d{3})+\s*[\W_]{0,3}", o_gia):
            o_gia = o_gia.strip(" !'.,:;`|_-")             # mẩu dấu rác của bản scan quanh số tiền
            g = doc_gia(o_gia)
        if g and not _RE_GIA_SACH.fullmatch(o_gia):
            nghi = o_gia                                # "5272.219": số đọc được nhưng sai dạng số tiền
        if not g and not khoang and not nhieu and o_gia and (dvt_c is None or r[dvt_c].strip()):
            g = doc_gia_ocr(o_gia)
            nghi = o_gia if g else ''
        dk = chuan_duong_kinh(r[dk_c]) if dk_c is not None else ''
        if dk_c is not None and not dk and g and r[dk_c].strip() and self.dk_truoc:
            mk = re.fullmatch(r'\(d >(\d+)-(\d+) cm\)', self.dk_truoc)
            if mk:                                      # bản scan đọc hỏng ô cỡ (">18-21" -> "> ni"): cỡ kế tiếp cùng bước
                a_, b_ = int(mk.group(1)), int(mk.group(2))
                dk = f'(d >{b_}-{2 * b_ - a_} cm)'
                nghi = f'cỡ đường kính đọc "{r[dk_c].strip()}" - suy là {dk} theo thứ tự'
        if dk:
            self.dk_truoc = dk
        d.g, d.nhan_gia, d.khoang, d.nhieu, d.nghi, d.o_gia, d.dk = g, nhan_gia, khoang, nhieu, nghi, o_gia, dk

    def _hang_duong_kinh(self, d: _HangGia) -> bool:
        """Bảng nhóm loài x cỡ đường kính. True = hàng đã xử lý xong."""
        ten_c, gia_c, dvt_c, ma_c, stt_c, dk_c = self.tieu_de
        r, ten, g, dk, nghi = d.r, d.ten, d.g, d.dk, d.nghi
        if dk_c is not None and (ten or dk):
            # bảng nhóm loài: ô nhóm gộp nhiều hàng (chỉ hàng đầu có chữ) - các hàng sau là cỡ đường kính của nhóm đó
            # bản scan: ô nhóm gộp vắt sang trang sau còn mẩu chữ đọc sai ("nem", "Ị") ở hàng cỡ tiếp theo (">27-30") - vẫn là
            # nhóm cũ; nhóm mới bắt đầu ở cỡ nhỏ nhất ("<3", "≤2") hoặc tên có chữ "Nhóm …"
            if ten and not re.fullmatch(r'[\d\W]+', ten) and \
                    (not self.nhom_dk or not dk or khoa_nhom_loai(ten) or re.match(r'\(d [<≤]', dk) or len(ten) > 12):
                self.nhom_dk = ten
            if dk and g and self.nhom_dk:
                ten_nhom = ' '.join(re.sub(r'\([^)]*(?:danh s[áa]ch|ph[ụu] l[ụu]c)[^)]*\)', ' ', self.nhom_dk).split())
                dvt = (r[dvt_c].strip() if dvt_c is not None else '') or self.dvt_mac_dinh or 'cây'
                dvt = chuan_dvt(dvt)
                self.kq.append(Muc(f'{ten_nhom} {dk}', dvt, g * self.nhan, '', ' | '.join(c for c in r if c), nhom=self.nhom or 3,
                                   ghi_chu=self.mat_do_bang, nhom_loai=khoa_nhom_loai(self.nhom_dk), duong_kinh=dk, nghi_gia=nghi))
                return True
            if not g:
                return True
        return False

    def _hang_khong_gia(self, d: _HangGia) -> None:
        """Hàng không đọc được giá: ghi chú, quy tắc, tiêu đề nhóm, dòng cha / dòng con."""
        ten_c, gia_c, dvt_c, ma_c, stt_c, dk_c = self.tieu_de
        r, stt, ten, ten_o_stt, gc_mt, la_mo_ta, gach, o_gia = d.r, d.stt, d.ten, d.ten_o_stt, d.gc_mt, d.la_mo_ta, d.gach, d.o_gia
        kq, quy_tac = self.kq, self.quy_tac
        if la_mo_ta:                                # dòng mô tả không giá: ghi chú của mục vừa đọc / mục kế tiếp
            if len(kq) > self.n_cha:
                for x in kq[-2 if kq[-1].muc_gia == 'cao' else -1:]:
                    x.ghi_chu = '; '.join(y for y in (x.ghi_chu, gc_mt) if y)
            else:
                self.mo_ta_cho = '; '.join(y for y in (self.mo_ta_cho, gc_mt) if y)
            return
        if ten_o_stt:                               # "Nhà nuôi yến kết hợp ở | Phần diện tích để ở được áp giá …"
            if quy_tac is not None and gc_mt:
                quy_tac.append(f'{ten}: {gc_mt}')
            return
        if not ten:
            return
        if la_quy_tac(ten):                         # "- Giếng sâu từ 10m trở lên thì … tính thêm 50% mức giá trên"
            if quy_tac is not None:
                quy_tac.append(f'{self.truoc}: {ten}' if self.truoc and gach else ten)
            return
        if o_gia and dvt_c is not None and r[dvt_c].strip():
            # có ĐVT, ô giá có chữ nhưng không đọc được ("Á A"): dòng giá hỏng - báo, không làm dòng cha
            if quy_tac is not None:
                quy_tac.append(f'KHÔNG ĐỌC ĐƯỢC ĐƠN GIÁ (bản scan): {" - ".join(x for x in (self.cha, ten) if x)} | '
                               f'{r[dvt_c].strip()} | "{o_gia}" - nhập tay nếu cần')
            return
        if _LA_MA.match(stt) or _la_ma_ocr(stt) or (not stt and re.match(r'(?i)^(nhom|phan|muc|phu luc)\b', bo_dau(ten))):
            self.nhom_muc = nhom_theo_chu(ten) or self.nhom_muc        # tiêu đề nhóm
            self.cha = self.truong_hop = self.truoc = ''
        elif self.cha and not stt and re.match(r'^[a-zđ]\)\s*\w', ten):
            self.truong_hop = ten[2:].strip()       # "a) Bồn nhựa" dưới "Di dời bồn nước": một cấp, không nối vào mục trên
        elif not stt and not gach and ten[:1].islower() and kq and self.truoc and kq[-1].ten.startswith(self.truoc):
            for x in kq[-2 if kq[-1].muc_gia == 'cao' else -1:]:   # ô tên xuống dòng thành hàng riêng: nối vào mục trên
                x.ten = f'{x.ten[:-1]} {ten}.' if x.muc_gia == 'cao' else f'{x.ten} {ten}'
            self.truoc = f'{self.truoc} {ten}'
        elif stt.startswith('*'):
            self.truong_hop = ten
        elif (_CON.match(stt) or gach) and self.cha:
            self.truong_hop = ten                           # dòng con không giá: thêm một cấp
        else:
            # mật độ ghi ở ghi chú danh mục, không ở tên: "Cây bưởi (Mật độ 210 cây/ha)" / "Cây vải thiều (330 cây/ha)"
            # -> "Cây bưởi" + ghi chú "Mật độ 210 cây/ha" cho các dòng con
            self.cha, self.mat_do = tach_mat_do_ten(ten)
            self.truong_hop, self.stt_cha, self.con_truoc = '', stt, ''
            self.truoc, self.mo_ta_cho, self.n_cha = '', '', len(kq)

    def _them_muc(self, d: _HangGia) -> None:
        """Hàng có giá: dựng tên đầy đủ theo dòng cha, thêm mục (một giá / khoảng / nhiều mùa vụ)."""
        ten_c, gia_c, dvt_c, ma_c, stt_c, dk_c = self.tieu_de
        r, stt, ten, gc_mt, la_mo_ta, gach, g = d.r, d.stt, d.ten, d.gc_mt, d.la_mo_ta, d.gach, d.g
        nhan_gia, khoang, nhieu, nghi = d.nhan_gia, d.khoang, d.nhieu, d.nghi
        kq, nhom, nhan = self.kq, self.nhom, self.nhan
        gc, cha_cua = '', ''
        if la_mo_ta and self.cha:                               # "Kết cấu: … | 7.052.000" dưới "1 | Nhà 6 đến 8 tầng": tên = dòng cha
            ten = ' - '.join(x for x in (self.cha, self.truong_hop) if x)
            gc = self.mat_do
        elif not ten:                                           # tiếp tục mục ngay trên (ô tên gộp)
            ten, gc = self.truoc, self.mat_do if self.cha else ''
        elif _CON.match(stt) or stt.startswith('*') or (not stt and self.cha) or ((gach or ten[:1].islower()) and self.cha):
            # dòng con (STT -, a)... hoặc để trống; ô tên có gạch đầu dòng / chữ thường - kể cả khi bản scan đặt STT ô gộp vào dòng con)
            cha_cua = self.cha
            self.con_truoc = _tu_dau_chu(ten)
            if gach and not self.truong_hop and self.con_truoc and self.con_truoc == _tu_dau_chu(self.cha):
                pass                                    # dòng con tự đủ tên ("- Chuồng heo, bò lợp lá" dưới "Chuồng heo, chuồng bò…")
            else:
                ten = ' - '.join(x for x in (self.cha, self.truong_hop, ten) if x)
            gc = self.mat_do if self.cha else ''
        else:
            self.cha = self.truong_hop = self.mat_do = ''
            ten, gc = tach_mat_do_ten(ten)
        if self.tien_to_bang and ten and not bo_dau(ten).startswith(bo_dau(self.tien_to_bang)):
            ten = f'{self.tien_to_bang} {ten}'
        gc = '; '.join(y for y in (gc, self.mo_ta_cho, gc_mt) if y)
        self.mo_ta_cho = ''
        self.truoc = ten
        if not ten or re.fullmatch(r'[\d\W]+', ten):
            return
        ten_day = f'{ten} ({nhan_gia})' if nhan_gia else ten
        dvt = chuan_dvt((r[dvt_c].strip() if dvt_c is not None else '') or self.dvt_mac_dinh)    # "đồng/bụi" -> "bụi"
        if re.search(r'(?i)\bsàn', dvt):
            dvt = _dvt_nha(dvt) or dvt                  # "Đồng/m² sàn" -> "m²" (bộ đơn giá ghi ĐVT nhà là m²)
        ma = r[ma_c].strip() if ma_c is not None else ''
        nh = nhom or self.nhom_muc or _nhom_dong(ten_day, dvt)
        nguon = ' | '.join(c for c in r if c)
        if nhieu:                                       # "Đông Xuân: … Hè Thu, Mùa: …" -> một mục mỗi mùa vụ
            for nh_, g_ in nhieu:
                kq.append(Muc(f'{ten} ({nh_})', dvt, g_ * nhan, ma, nguon, nhom=nhom or self.nhom_muc or _nhom_dong(ten, dvt),
                              ghi_chu=gc, cha=cha_cua))
        elif khoang:
            kq.append(Muc(ten_day, dvt, khoang[0] * nhan, ma, nguon, nhom=nh, ghi_chu=gc, cha=cha_cua, muc_gia='thap',
                          khoang=' '.join(r[gia_c].split())))
            kq.append(Muc(ten_day + '.', dvt, khoang[1] * nhan, '', nguon, nhom=nh, ghi_chu=gc, cha=cha_cua, muc_gia='cao',
                          khoang=' '.join(r[gia_c].split())))
        else:
            kq.append(Muc(ten_day, dvt, g * nhan, ma, nguon, nhom=nh, ghi_chu=gc, cha=cha_cua, nghi_gia=nghi))
            if self.la_loai_bang and (stt or self.stt_cha).isdigit():
                self.loai_stt[id(kq[-1])] = stt or self.stt_cha

    def doc_hang(self, r) -> None:
        """Một hàng dưới tiêu đề cột."""
        d = self._boc_ten(r)
        if d is None:
            return
        self._doc_o_gia(d)
        if self._hang_duong_kinh(d):
            return
        if not d.g and not d.khoang and not d.nhieu:
            self._hang_khong_gia(d)
            return
        self._them_muc(d)


def nhan_muc(dong: list, nhom: int = 0, quy_tac: list | None = None) -> list:
    """Dòng bảng -> các mục đơn giá. Có dòng tiêu đề (Tên, ĐVT, Đơn giá) thì theo cột; không có thì đọc từng dòng chữ (_DocDong:
    '<mã> <tên> <ĐVT> <đơn giá>', dòng cha / dòng con, khoảng giá).

    Bảng phân cấp như văn bản UBND: dòng nhóm (I, II...) không có giá; dòng mục (1, 2...) không có giá là "cha" của các dòng
    con (-, +, a)...) -> tên "Cha - Con" như bộ đơn giá; dòng '*' là trường hợp chen giữa; ô giá có nhãn
    ("Đông Xuân: 24.880.000") -> "Tên (Đông Xuân)"; ô giá khoảng "a - b" -> hai mục (mức cao: tên có dấu chấm cuối); dòng tên trống
    tiếp tục mục ngay trên. nhom: nhóm mặc định (theo văn bản). quy_tac: danh sách nhận các dòng quy định cách tính không có giá."""
    # 1.0.60: số tiền trong "Ví dụ" không phải đơn giá; văn bản chính sách: lời văn trong Điều do muc_chinh_sach_tu_dieu_khoan đọc
    dong = bo_vi_du(dong)
    if nhom == 4 and co_dieu_khoan(dong):
        dong = bo_loi_van_dieu(dong)
    p = _DocBangGia(nhom, quy_tac)
    for r in dong:
        p.gan_khu_vuc(r)
        if p.doc_tieu_de(r, [bo_dau(c) for c in r]):
            continue
        if p.tieu_de and len(r) >= 2:
            p.doc_hang(r)
            continue
        if len(r) == 1 or not p.tieu_de:                  # dòng chữ (PDF / Word không bảng, bản scan đọc theo dòng, bảng dán)
            p.doc_dong.doc(' '.join(str(c) for c in r if str(c or '').strip()))
    for m_ in p.kq[p.n_kv:]:
        m_.khu_vuc = m_.khu_vuc or p.kv
    _ten_theo_loai(p.kq, p.loai_stt)
    return p.kq


def _ten_theo_loai(kq: list, loai_stt: dict) -> None:
    """1.0.57 - bảng "Loại | Quy mô, kết cấu | Đơn giá" (QĐ 18/2026 Phụ lục IIa): nhà loại 4…8 cùng tên "Nhà 01 tầng, chiều cao từ 3m
    đến 4m…", khác kết cấu và giá -> tên thêm "(nhà loại N)" (phần ghi chú văn bản gọi "Nhà loại 1, 2, 3…") để không trùng mục."""
    nhom = {}
    for m in kq:
        if id(m) in loai_stt:
            nhom.setdefault((bo_dau(m.ten), m.dvt, m.khu_vuc), []).append(m)
    for ds in nhom.values():
        if len(ds) > 1 and len({m.don_gia for m in ds}) > 1:
            for m in ds:
                m.ten = f'{m.ten} (nhà loại {loai_stt[id(m)]})'


_RE_KHU_VUC = re.compile(r'\bKHU VỰC\s+(\d{1,2})\b')       # chữ HOA: tiêu đề phụ lục (lời văn "khu vực 1" chữ thường không tính)


def cac_khu_vuc(ds: list) -> list:
    """1.0.57: [(khu vực, số dòng)] khi văn bản có từ 2 khu vực giá trở lên (QĐ 18/2026 hợp nhất: Phụ lục I khu vực 1, Phụ lục II khu
    vực 2) - bộ đơn giá chỉ một mức giá mỗi mục, người dùng chọn khu vực của bộ đơn giá. Ít hơn 2: []."""
    dem = {}
    for m in ds:
        if m.khu_vuc:
            dem[m.khu_vuc] = dem.get(m.khu_vuc, 0) + 1
    return sorted(dem.items(), key=lambda x: int(x[0])) if len(dem) >= 2 else []


def khu_vuc_khop_nhat(ds: list, nhom: int | None = None) -> str:
    """Khu vực có nhiều dòng khớp mục đang có của bộ đơn giá nhất (giá giống / mục cùng tên) - mặc định khi văn bản nhiều khu vực."""
    import copy
    kv = cac_khu_vuc(ds)
    if not kv:
        return ''
    tot, chon = -1, kv[0][0]
    for k, _n in kv:
        thu = so_khop([copy.copy(m) for m in ds if m.khu_vuc == k], nhom)
        diem = sum(2 if m.trang_thai == 'giữ nguyên' else 1 for m in thu if m.trang_thai not in ('mới', 'bỏ'))
        if diem > tot:
            tot, chon = diem, k
    return chon


def loc_khu_vuc(ds: list, kv: str) -> list:
    """Dòng của khu vực kv (và dòng không thuộc khu vực nào)."""
    return [m for m in ds if not m.khu_vuc or m.khu_vuc == kv] if kv else list(ds)


# ---------------------------------------------------------------- đơn giá ghi trong lời văn (văn bản không có bảng)
# "25.000 đồng/m² mặt nước", "1,5 triệu đồng/con", "30 nghìn đồng/kg", "3.000.000 đ/hộ"
_RE_GIA_VAN = re.compile(
    r'(?P<so>\d{1,3}(?:[.,]\d{3})+(?:,\d+)?|\d+(?:,\d+)?)\.?\s*(?P<boi>triệu|trieu|nghìn|nghin|ngàn|ngan)?\s*(?:đồng|đông|đổng|đ)(?![\w])'
    r'\s*(?:\([^)]{0,40}\)\s*)?(?:/\s*(?:01\s+|1\s+|một\s+)?|trên\s+(?:một|01|1)\s+)'
    r'(?P<dvt>nh[âa]n\s+kh[ẩâa]u(?:\s*/\s*[^\s;,.():]+)?|đơn\s+vị\s+vật\s+nuôi|m[ée]t\s+d[àa]i|[^\s;,.():]+'
    r'(?:\s+(?:mặt\s+nước|nuôi|thả\s+nuôi|ao|lồng|bè|sàn|năm|tháng|yến(?:\s+thô)?))?)',
    re.I)
_RE_KHOANG = re.compile(r'(?i)(?:từ|tu)\s+[\d.,]+\s*(?:triệu|nghìn|ngàn)?\s*(?:đồng|đ)?\s*(?:đến|tới|-|–)\s*$')
# "1." / "1.1." là ký hiệu khoản; "50.000.000 đồng…" (dòng PDF bắt đầu bằng số tiền) thì không: sau dấu chấm không được là chữ số
_RE_DAU_KHOAN = re.compile(r'^\s*(?:(?P<dieu>Điều\s+\d+[a-zđ]?\.?)|(?P<so>\d+(?:\.\d+)*\.)(?!\d)|(?P<chu>[a-zđ]\))|'
                           r'(?P<gach>[-+•–*]))\s*', re.I)
# cụm đầu / cuối tên không mang nghĩa: "Đơn giá bồi thường đối với ...", "Giá trị và đơn giá bồi thường đối với ...",
# "Bồi thường thiệt hại ngừng sản xuất đối với ...", "... là", "mức hỗ trợ bằng", "... nhưng không quá"
_RE_DAU_TEN = re.compile(r'(?i)^(?:(?:quy\s+định\s+)?(?:giá\s+trị\s+và\s+)?(?:đơn\s+giá|mức(?:\s+giá)?)'
                         r'(?:\s+(?:bồi\s+thường|hỗ\s+trợ|thiệt\s+hại))*(?:\s+(?:đối\s+với|cho|về|của))?\s+|'
                         r'(?:bồi\s+thường|hỗ\s+trợ)(?:\s+thiệt\s+hại)?(?:\s+(?:ngừng|ngưng)\s+sản\s+xuất)?\s+(?:đối\s+với|cho|về)\s+|'
                         r'(?:đối\s+với|trường\s+hợp|về)\s+)')
_RE_CUOI_TEN = re.compile(r'(?i)(?:\s*[:,]\s*|\s+(?:là|bằng|với\s+mức|ở\s+mức|tương\s+đương|được\s+bồi\s+thường|được\s+hỗ\s+trợ|'
                          r'được\s+tính|tính|mức|đơn\s+giá|(?:nhưng\s+)?không\s+(?:vượt\s+)?quá|tối\s+đa))+\s*$')
# giá trần: "theo giá thị trường nhưng không quá 18.500.000 đồng/kg" -> tên ghi "(theo giá thị trường, tối đa)"
_RE_TRAN = re.compile(r'(?i)(?:nhưng\s+)?(?:không\s+(?:vượt\s+)?quá|tối\s+đa)\s*$')
_RE_THI_TRUONG = re.compile(r'(?i)\s*theo\s+giá\s+thị\s+trường\s*$')
# điều kiện áp dụng đứng SAU số tiền: "… là 20.300.000 đồng/ha/vụ đối với thủy sản nuôi dưới 50% định mức…, 14.500.000 đồng/ha/vụ
# đối với thủy sản nuôi từ 50% đến 80%…" (QĐ 31/2025/QĐ-UBND) - mỗi mức giá một dòng "Tên (điều kiện)"
_RE_DIEU_KIEN = re.compile(r'(?i)^[\s,]*(?:đối\s+với|áp\s+dụng\s+(?:cho|đối\s+với)|khi|trường\s+hợp|nếu)\s+')
# câu mới bắt đầu giữa đoạn (Word / PDF ghép dòng tiêu đề khoản với câu ghi giá): "… cá nuôi lồng bè Đối với cá nuôi lồng bè là …"
_RE_CAU_MOI = re.compile(r'(?<=\S)\s+(?=(?:Đối\s+với|Trường\s+hợp|Riêng)\s)')
# chữ dẫn chung trước dấu ":" không làm tên nhóm: "Đối với các hình thức nuôi như: nuôi hàu…" (giữ tên nhóm của khoản)
_RE_DAN_CHUNG = re.compile(r'(?:\bnhu|\bgom|\bsau|\bbao gom)$')


def _bo_dau_khoan(x: str) -> tuple:
    """(cấp, chữ bỏ ký hiệu đầu khoản): Điều = 0, 1. = 1, 1.1. = 2, a) = 3, -/+ = 4; không có ký hiệu = 9."""
    m = _RE_DAU_KHOAN.match(x)
    if not m:
        return 9, x.strip()
    if m.group('dieu'):
        cap = 0
    elif m.group('so'):
        cap = m.group('so').count('.')
    elif m.group('chu'):
        cap = 3
    else:
        cap = 4
    return cap, x[m.end():].strip()


def _ten_gon(x: str) -> str:
    x = ' '.join(x.split()).strip(' ;:,.')
    for _ in range(3):
        x = _RE_CUOI_TEN.sub('', _RE_DAU_TEN.sub('', x)).strip(' ;:,.')
    return x[:1].upper() + x[1:] if x else ''


def _la_tieu_de(x: str) -> bool:
    """Khoản không ghi giá, ngắn, không có dấu kết câu: tiêu đề cho các khoản bên dưới (Word không có dấu ":" cuối tiêu đề -
    "1. Bồi thường thiệt hại ngừng sản xuất đối với ao nuôi cá")."""
    return len(x) <= 160 and not x.endswith(('.', ';', ',')) and not _RE_GIA_VAN.search(x)


def _ket_cau(s: str, tu: int = 0) -> int:
    """Vị trí ngay sau dấu kết câu đầu tiên của s (từ vị trí tu): dấu ; hoặc dấu . đứng trước chữ hoa / cuối chuỗi
    ("50.000" không phải kết câu). Không có -> len(s)."""
    for m in re.finditer(r'[;.]', s[tu:]):
        i = tu + m.end()
        sau = s[i:].lstrip()
        if m.group() == ';' or not sau or sau[0].isupper():
            return i
    return len(s)


def _cau_cuoi(s: str) -> str:
    """Vế câu cuối của s (sau dấu ; hoặc dấu . kết câu)."""
    tu = 0
    while True:
        i = _ket_cau(s, tu)
        if i >= len(s):
            return s[tu:]
        tu = i


def _dieu_kien(sau: str) -> tuple:
    """Điều kiện áp dụng đứng ngay sau số tiền ("đối với thủy sản nuôi dưới 50% định mức…") -> (điều kiện gọn, số ký tự của sau
    đã dùng). Hết điều kiện ở dấu kết câu, hoặc ở dấu phẩy mà phần sau là tên mục mới (", nuôi cua là …")."""
    m = _RE_DIEU_KIEN.match(sau)
    if not m:
        return '', 0
    het = _ket_cau(sau, m.end())
    for p in re.finditer(',', sau[m.end():het]):
        i = m.end() + p.start()
        if re.search(r'(?i)(?:\s(?:là|bằng)|:)\s*$', sau[i + 1:het]):
            het = i
            break
    dk = ' '.join(sau[m.end():het].split()).strip(' ,;.')
    dk = re.sub(r'(?i)định\s+mức\s+kinh\s+tế\s*-?\s*kỹ\s+thuật', 'định mức KT-KT', dk)
    dk = re.sub(r'(?i)thời\s+gian\s+nuôi\s+trồng\s+(?:thủy|thuỷ)\s+sản', 'thời gian nuôi', dk)
    dk = re.sub(r'(?i)^(?:thủy|thuỷ)\s+sản\s+(?=nuôi\b)', '', dk)          # "thủy sản nuôi dưới 50%…" -> "nuôi dưới 50%…"
    return dk, het


def _khoan_van(dong: list) -> list:
    """Dòng chữ (đoạn Word / dòng PDF bị ngắt giữa câu) -> các khoản: ghép dòng nối tiếp, tách ở đầu khoản (Điều, 1., a), -),
    sau dấu ; hoặc : cuối dòng, và sau dòng tiêu đề khoản khi dòng kế bắt đầu bằng chữ hoa (đoạn Word riêng)."""
    kq, dang = [], ''
    for r in dong:
        x = r if isinstance(r, str) else (r[0] if len(r) == 1 else '')
        x = ' '.join(str(x or '').split())
        if not x:
            continue
        if dang and (_RE_DAU_KHOAN.match(x) or dang.endswith((';', ':', '.')) or
                     (x[:1].isupper() and _RE_DAU_KHOAN.match(dang) and _la_tieu_de(dang)
                      and not _RE_NOI_TIEU_DE.search(bo_dau(dang)))):     # "… bổ sung bởi" + "Nghị định số …": chưa hết câu
            kq.append(dang)
            dang = x
        else:
            dang = f'{dang} {x}'.strip()
    if dang:
        kq.append(dang)
    return kq


def muc_tu_loi_van(dong: list, nhom: int = 0) -> tuple:
    """Văn bản không có bảng giá (đơn giá viết trong điều khoản, như QĐ 31/2025/QĐ-UBND vật nuôi): tìm các cụm "<số> đồng/<ĐVT>"
    trong từng khoản; tên mục = chữ đứng trước số tiền (bỏ "Đơn giá bồi thường đối với…", "… là"), dòng tiêu đề khoản phía trên
    (không giá: kết thúc ":" hoặc khoản ngắn không dấu kết câu) làm tên nhóm "Tiêu đề - Mục"; điều kiện đứng sau số tiền
    ("… đối với thủy sản nuôi dưới 50%…") ghi trong ngoặc, các mức giá nối tiếp cùng câu dùng lại tên. Trả ([Muc], [câu cần xem
    lại: khoảng giá "từ… đến…", tỷ lệ %, không ra tên]). Người dùng đối chiếu từng dòng trên HopNhapDonGia trước khi áp dụng
    (câu gốc ở Muc.nguon_dong)."""
    ds, xem, tieu_de = [], [], {}
    for khoan in _khoan_van(bo_vi_du(dong_loi_van(dong))):
        cap, than = _bo_dau_khoan(khoan)
        if cap == 0:
            tieu_de.clear()
        gia = list(_RE_GIA_VAN.finditer(than))
        if not gia and re.search(r'\d\s*%', than) and re.search(r'(?i)bồi\s+thường|hỗ\s+trợ', than):
            xem.append(f'Quy định theo tỷ lệ % (không phải đơn giá - phần mềm không tự đổi cách tính): {khoan[:250]}')
        if not gia:
            if than.endswith(':') or cap == 0 or (cap in (1, 2, 3) and _la_tieu_de(than)):   # tiêu đề cho các khoản bên dưới
                for k in [k for k in tieu_de if k >= cap]:
                    del tieu_de[k]
                t = _ten_gon(re.sub(r'(?i)^(?:quy\s+định\s+)?', '', than))
                if t and len(t) <= 160:
                    tieu_de[cap] = t
            continue
        cha = next((tieu_de[k] for k in sorted(tieu_de, reverse=True) if k < cap), '')
        pos, goc = 0, None            # goc: (tên nhóm, tên, ghi chú) của mức giá trước - mức giá nối tiếp dùng lại
        for j, m in enumerate(gia):
            truoc = than[pos:m.start()]
            dk, dung = _dieu_kien(than[m.end():gia[j + 1].start() if j + 1 < len(gia) else len(than)])
            pos = m.end() + dung      # điều kiện của mức giá này không làm tên cho mức giá sau
            if _RE_KHOANG.search(truoc):
                xem.append(f'Khoảng giá (không tự lấy): {khoan[:250]}')
                continue
            boi = (m.group('boi') or '').lower()
            so = m.group('so')
            if boi:
                g = D(so.replace('.', '').replace(',', '.')) * (1000000 if boi.startswith('tri') else 1000)
                g = int(g) if g == int(g) else None
            else:
                g = doc_gia(so)
            if not g:
                continue
            if goc and not re.sub(r'(?i)\b(?:và|hoặc)\b|[\s,;]', '', truoc):
                cha_m, ten, ghi = goc[0], goc[1], list(goc[2])   # "…, 14.500.000 đồng/ha/vụ đối với …": cùng tên, khác điều kiện
            else:
                # tên: phần chữ ngay trước số tiền trong cùng vế câu (sau dấu ; / dấu chấm kết câu). "Đối với nuôi tôm: tôm thẻ
                # 60.000 đồng/m²" - phần trước ":" là tiêu đề trong dòng, dùng cho cả các giá sau trong khoản
                ve = _bo_dau_khoan(_cau_cuoi(truoc))[1]
                moi = list(_RE_CAU_MOI.finditer(ve))
                if moi:                                 # "<tiêu đề khoản> Đối với cá nuôi lồng bè là …" (dòng PDF ghép)
                    cha = _ten_gon(ve[:moi[-1].start()]) or cha
                    ve = ve[moi[-1].end():]
                tran = bool(_RE_TRAN.search(ve.strip(' ,;:')))
                if ':' in ve:
                    trai, phai = ve.rsplit(':', 1)
                    if _ten_gon(phai):
                        t = _ten_gon(_bo_dau_khoan(trai)[1])
                        if t and not _RE_DAN_CHUNG.search(bo_dau(t)):    # "Đối với các hình thức nuôi như:" giữ tên nhóm
                            cha = t
                        ve = phai
                    else:
                        ve = trai
                ten, ghi = _ten_gon(ve), []
                if tran:                                # giá trần: "theo giá thị trường nhưng không quá …"
                    mt = _RE_THI_TRUONG.search(ten)
                    if mt:
                        ten = ten[:mt.start()]
                    ghi.append('theo giá thị trường, tối đa' if mt else 'tối đa')
                cha_m = cha
                if len(ten) < 2:
                    ten, cha_m = cha, ''
                if not ten:
                    xem.append(f'Có số tiền nhưng không rõ tên mục: {khoan[:250]}')
                    continue
                goc = (cha_m, ten, tuple(ghi))
            if dk:
                ghi.append(dk)
            ten_day = f'{cha_m} - {ten}' if cha_m and bo_dau(cha_m) not in bo_dau(ten) else ten
            if ghi:
                ten_day += f' ({"; ".join(ghi)})'
            dvt = _chuan_dvt_van(m.group('dvt'))
            ds.append(Muc(ten_day[:200], dvt, g, '', khoan[:300], nhom=nhom or _nhom_dong(ten_day, dvt)))
    return ds, xem


# ---------------------------------------------------------------- 1.0.60: toàn văn văn bản chính sách (bản OCR, Word, PDF chữ)
_RE_O_GIA = re.compile(r'^\W*\d{1,3}(?:[.,]\d{3})+\W*(?:đồng|đông|đ)?\W*$', re.I)
_HOA = 'A-ZĐÀÁẢÃẠĂẮẰẲẴẶÂẤẦẨẪẬÈÉẺẼẸÊẾỀỂỄỆÌÍỈĨỊÒÓỎÕỌÔỐỒỔỖỘƠỚỜỞỠỢÙÚỦŨỤƯỨỪỬỮỰỲÝỶỸỴ'      # khoảng À-Ỹ của Unicode gồm cả chữ thường ("đ")
_RE_RAC_DAU_DONG = re.compile(r'^[\s.…_~=|‘’\'"`^„]+(?=\S)')
_RE_DIEU_THAT = re.compile(r'^(?:Điều|ĐIỀU|Dieu|Điêu|Điểu|Diều|Điếu)\s+(\d+[a-zđ]?)\s*(?:[.:]\s*|\s(?=[' + _HOA + r'])(?!Luật|Nghị|Quyết|Bộ|Thông))(.*)$')
_RE_HET_DIEU = re.compile(r'n\w{0,2}i nhan\b|tm\.|kt\.')
_RE_HEADING_MUC = re.compile(r'(?:chuong|muc)\s*[\divxlh]{0,6}\s*$')
_RE_NOI_TIEU_DE = re.compile(r'(?:\bso|\bboi|\btai|\bva|\bcua|\btheo|\bkhoan|\bdieu|\bnghi|\bsua|\bbo|,|-)$')
_RE_DIEU_HANH_CHINH = re.compile(r'hieu luc|to chuc thuc hien|trach nhiem|pham vi dieu chinh|doi tuong ap dung|chuyen tiep|thi hanh|^sua doi, bo sung$')


def _chu_dong_van(r, scan: bool = False) -> str:
    """Một dòng doc_bang / OCR -> chữ lời văn. Dòng một ô: đoạn văn. Bản scan: dòng căn đều bị tách nhiều ô ("Luật || số 43/2024/QH15, || …"),
    ô rác ("|") -> nối; dòng có ô giá là hàng bảng (biểu thưởng) -> ''. Word / Excel: hàng nhiều ô là bảng -> ''."""
    if isinstance(r, str):
        return ' '.join(r.split())
    o = [' '.join(str(c).split()) for c in r if str(c or '').strip()]
    if len(o) <= 1:
        return o[0] if o else ''
    that = [x for x in o if len(re.findall(r'\w', x)) >= 2]
    if len(that) <= 1:
        return that[0] if that else ''
    if scan and not any(_RE_O_GIA.match(x) for x in o):
        return ' '.join(o)
    return ''


def sach_dong_ocr(x: str) -> str:
    """Bỏ rác đầu dòng bản OCR, sửa ký hiệu khoản: ". Điều 16.", "_..2. Trường hợp", "1, Đối với" (-> "1. Đối với"); số hiệu đọc rời."""
    x = _RE_RAC_DAU_DONG.sub('', chuan_chu_so_hieu(x))
    return re.sub(r'^(\d{1,2}),\s+(?=[' + _HOA + r'])', r'\1. ', x)


def dong_loi_van(dong: list) -> list:
    """Các dòng lời văn đã làm sạch: bỏ số trang, mảnh rác dưới 3 ký tự; giữ thứ tự (chữ nối dòng do _khoan_van)."""
    scan = isinstance(dong, DongScan)
    kq = []
    for r in dong:
        x = sach_dong_ocr(_chu_dong_van(r, scan))
        if x and len(re.findall(r'\w', x)) >= 3 and not re.fullmatch(r'\W*\d{1,3}\W*', x):
            kq.append(x)
    return kq


def _la_dau_khoan_moi(x: str) -> bool:
    return bool(_RE_DIEU_THAT.match(x) or re.match(r'\d{1,2}[.,]\s+[' + _HOA + ']', x) or re.match(r'(?:chuong|muc\s*\d|phu luc)\b', bo_dau(x)))


VI_DU_TOI_DA = 40                  # phòng "Ví dụ" không có khoản sau: không nuốt phần còn lại của văn bản


def bo_vi_du(dong: list) -> list:
    """Bỏ đoạn "Ví dụ: …" (và các gạch đầu dòng tính thử dưới nó) tới khoản / Điều mới: số tiền trong ví dụ không phải đơn giá. Giữ kiểu danh
    sách (DongScan). Mỗi phần tử là chuỗi hoặc hàng nhiều ô."""
    kq, dem = [], -1
    for r in dong:
        x = sach_dong_ocr(' '.join(str(c) for c in ([r] if isinstance(r, str) else r) if c))
        if dem < 0 and re.match(r'vi du\b', bo_dau(x)):
            dem = 0
            continue
        if dem >= 0:
            dem += 1
            if not _la_dau_khoan_moi(x) and dem <= VI_DU_TOI_DA:
                continue
            dem = -1
        kq.append(r)
    return DongScan(kq) if isinstance(dong, DongScan) else kq


def co_dieu_khoan(dong: list, toi_thieu: int = 3) -> bool:
    """Văn bản viết theo Điều (từ toi_thieu Điều trở lên)."""
    return sum(1 for x in dong_loi_van(dong) if _RE_DIEU_THAT.match(x)) >= toi_thieu


def bo_loi_van_dieu(dong: list) -> list:
    """Văn bản chính sách: chỉ giữ cho bộ đọc bảng (nhan_muc) phần ngoài các Điều (phụ lục) và bảng có tiêu đề cột trong Điều - lời văn trong
    Điều do muc_chinh_sach_tu_dieu_khoan đọc, không để bộ đọc theo dòng cắt vụn."""
    kq, trong, bang = [], False, False
    scan = isinstance(dong, DongScan)
    for r in dong:
        chu = ' '.join(str(c) for c in ([r] if isinstance(r, str) else r) if c)
        x = sach_dong_ocr(chu)
        k = bo_dau(x)
        if _RE_DIEU_THAT.match(x):
            trong, bang = True, False
            kq.append(['']) if False else None
            continue
        if re.match(r'phu luc\b', k) or _RE_HET_DIEU.match(k):
            trong, bang = False, False
        elif trong and re.search(r'\b(?:stt|tt)\b', k) and re.search(r'don gia|muc ho tro|muc boi thuong', k):
            bang = True
        if not trong or bang:
            kq.append(r)
    return DongScan(kq) if scan else kq


def van_theo_dieu(dong: list) -> list:
    """Lời văn theo Điều: [dict(so, ten, dong)] - ten: trọn tiêu đề Điều (nhiều dòng, kể cả "… được sửa đổi, bổ sung bởi Nghị định số …"),
    dong: các dòng thân Điều. Bỏ tiêu đề Chương / Mục, dòng chữ hoa, phần "Nơi nhận" / chữ ký. dong đã qua dong_loi_van."""
    kq, cur, dang_ten = [], None, False
    for x in dong:
        k = bo_dau(x)
        md = _RE_DIEU_THAT.match(x)
        if md:
            cur = dict(so=md.group(1), ten=md.group(2).strip(), dong=[])
            kq.append(cur)
            dang_ten = True
            continue
        if _RE_HET_DIEU.match(k):
            cur, dang_ten = None, False
            continue
        if cur is None or _RE_HEADING_MUC.match(k) or (x == x.upper() and len(x) > 5 and not re.search(r'\d', x)):
            continue
        if dang_ten:
            t = bo_dau(cur['ten'])
            if not _la_dau_khoan_moi(x) and not re.match(r'[a-zđ]\)|[-–+•]', x) and not t.endswith((':', '.')) and (
                    not x[:1].isupper() or re.match(r'(?:Nghị|Luật|Điều|Bộ|CP\b)', x) or _RE_NOI_TIEU_DE.search(t)):
                cur['ten'] = f'{cur["ten"]} {x}'
                continue
            dang_ten = False
        cur['dong'].append(x)
    return kq


_RE_CAT_TEN_DIEU = re.compile(r'(?i)\s+(?:quy\s+định\s+tại|(?:được|bị)\s+s[ửủứu]a\s+đ|đối\s+với\s+trường\s+hợp\s+không\s+có|khi\s+Nhà\s+nước\s+thu\s+h[ồôố]i)')


def ten_dieu_gon(ten: str) -> str:
    """Tiêu đề Điều -> cụm chính, vế đầu: "Xác định chi phí đầu tư vào đất còn lại đối với trường hợp không có hồ sơ … quy định tại …" ->
    "Chi phí đầu tư vào đất còn lại"."""
    x = ' '.join(str(ten or '').split())
    m = _RE_CAT_TEN_DIEU.search(x)
    x = x[:m.start()] if m else x
    x = re.sub(r'(?i)^xác\s+định\s+', '', x.split(';')[0]).strip(' ,.;:')
    return x[:1].upper() + x[1:] if x else ''


def cac_khoan_dieu(d: dict) -> list:
    """Thân một Điều -> [(số khoản, chữ điểm, phần chữ bỏ ký hiệu, chữ khoản đầy đủ, câu dẫn của khoản)]. Sửa chữ điểm OCR đọc nhầm theo thứ
    tự ("e)" sau "b)" là "c)"); khoản mất số ("2." đọc thành ".") nhận ra vì mở đầu giống khoản trước."""
    kq = []
    khoan, diem, dan, mo_dau = '', '', '', ''
    for c in _khoan_van(d['dong']):
        cap, than = _bo_dau_khoan(c)
        if cap == 1 or cap == 2:
            m = re.match(r'\s*(\d+)', c)
            khoan, diem, dan = m.group(1), '', than
            mo_dau = re.sub(r'\W', '', bo_dau(than))[:14]
        elif cap == 3:
            chu = c.strip()[:1].lower()
            mong = chr(ord(diem) + 1) if diem else 'a'
            diem = mong if (chu != mong and chu in 'eê' and mong == 'c') else chu
        elif cap == 9 and mo_dau and khoan.isdigit() and len(than) > 40 and re.sub(r'\W', '', bo_dau(than))[:14] == mo_dau:
            khoan, diem, dan = str(int(khoan) + 1), '', than
        kq.append((khoan, diem, than, c, dan))
    return kq


_RE_CUM_CHINH = re.compile(r'(?i)(?:h[ỗôốổ]\s+tr[ợơ]|b[ồôố]i\s+th[ưu][ờơ]ng)\b[^.;:]{8,140}')
_RE_CUOI_MUC = re.compile(r'(?i)(?:[,;:]?\s*m[ứu]c\s+(?:h[ỗôốổ]\s+tr[ợơ]|b[ồôố]i\s+th[ưu][ờơ]ng)(?:\s+là)?\s*:?\s*$)|'
                          r'(?:(?:\s+thì)?\s+được\s+(?:tính\s+)?(?:h[ỗôốổ]\s+tr[ợơ]|b[ồôố]i\s+th[ưu][ờơ]ng)\s*$)')
_RE_CAU_RIENG = re.compile(r'(?<=[.])\s+(?=[' + _HOA + '])')
_SUA_OCR = ((r'chỉ phí', 'chi phí'), (r'di chuyên\b', 'di chuyển'), (r'hô trợ', 'hỗ trợ'), (r'bôi thường', 'bồi thường'), (r'thập (?=hơn|dưới)', 'thấp '),
            (r'tìm đường', 'tim đường'), (r'\bđên\b', 'đến'), (r'\bđ[ắâ]t\b', 'đất'), (r'\bnăm trong\b', 'nằm trong'), (r'mồ má\b', 'mồ mả'),
            (r'mô mả\b', 'mồ mả'), (r'\bbăng\b', 'bằng'), (r'\bquyêt\b', 'quyết'), (r'\bđôi với\b', 'đối với'), (r'trực tiệp', 'trực tiếp'),
            (r'\bđê (?=tháo|di|xác|thực|sử)', 'để '), (r'\btiên\b', 'tiền'), (r'\bsô\b', 'số'), (r'\bđiêu\b', 'điều'), (r'sửa đôi', 'sửa đổi'), (r'\bbô sung', 'bổ sung'))


def sua_chu_ocr(x: str) -> str:
    """Sửa lỗi dấu hay gặp của bản OCR tiếng Việt trong lời văn pháp lý (giữ chữ hoa đầu): "Chỉ phí" -> "Chi phí", "di chuyên" -> "di chuyển"."""
    for mau, moi in _SUA_OCR:
        x = re.sub(mau, lambda m, n=moi: n[:1].upper() + n[1:] if m.group()[:1].isupper() else n, x, flags=re.I)
    return x


def _cum_chinh(chu: str) -> str:
    """Câu dẫn khoản -> cụm "hỗ trợ / bồi thường …" cuối cùng: "… không được bồi thường mà được hỗ trợ để tháo dỡ, phá dỡ, di dời, như sau:" ->
    "Hỗ trợ để tháo dỡ, phá dỡ, di dời"."""
    kq = ''
    for m in _RE_CUM_CHINH.finditer(chu or ''):
        x = m.group()
        cuoi = list(re.finditer(r'(?i)h[ỗôốổ]\s+tr[ợơ]|b[ồôố]i\s+th[ưu][ờơ]ng', x))
        x = x[cuoi[-1].start():]                        # "bồi thường mà được hỗ trợ để tháo dỡ" -> "hỗ trợ để tháo dỡ"
        x = re.split(r'(?i)\s+(?:như\s+sau|khi\s+Nhà\s+nước|theo\s+quy\s+định)\b', x)[0].strip(' ,;:.')
        if len(x) >= 15:
            kq = x
    return kq[:1].upper() + kq[1:]


def _chuan_dvt_van(d: str) -> str:
    """ĐVT trong lời văn (kể cả chữ OCR): "mét dài" -> "md"; "m”", "m®" -> "m²"; "nhân khâu/tháng" -> "nhân khẩu/tháng"."""
    d = ' '.join(str(d or '').split()).strip(' :')
    if re.fullmatch(r'(?i)m[”"“®°\'’*²2]+', d):
        return 'm²'
    if re.fullmatch(r'(?i)m[ée]t\s+d[àa]i', d):
        return 'md'
    return re.sub(r'(?i)nh[âa]n\s+kh[âa]u', 'nhân khẩu', re.sub(r'\s*/\s*', '/', d))


def _so_tien_van(m) -> int | None:
    boi = (m.group('boi') or '').lower()
    so = m.group('so')
    if boi:
        g = D(so.replace('.', '').replace(',', '.')) * (1000000 if boi.startswith('tri') else 1000)
        return int(g) if g == int(g) else None
    return doc_gia(so)


_RE_THUONG = re.compile(r'\b(duoi|tu)\s+(\d{1,4})\s+trieu\s+dong[^|]*?(?:\|\s*|\s)\W*(\d{1,3}(?:[.,]\d{3}){2})\s*(?:dong|d)?\W*$')


def doc_bieu_thuong(dong: list) -> list:
    """Biểu thưởng bàn giao mặt bằng trước hạn (Điều 15 khoản 4 QĐ 42/2025): "Dưới 20 triệu đồng | 2.000.000 đồng" … "Từ 500 triệu đồng trở
    lên | 20.000.000 đồng" -> [(từ mức đồng, mức thưởng đồng)] (cùng dạng bảng bieu_thuong). Không phải đơn giá hỗ trợ: không thành dòng mục."""
    kq, tha = [], 0
    for r in dong:
        o = [str(c) for c in ([r] if isinstance(r, str) else r) if str(c or '').strip()]
        k = bo_dau(' | '.join(o))
        if re.search(r'muc thuong|duoc thuong', k):
            tha = 12
            continue
        if tha <= 0:
            continue
        m = _RE_THUONG.search(k)
        if m:
            g = doc_gia(m.group(3))
            if g:
                kq.append((0 if m.group(1) == 'duoi' else int(m.group(2)) * 1000000, g))
                tha = 3
                continue
        tha -= 1
    return kq if len(kq) >= 2 else []


def so_bieu_thuong(bieu: list) -> str:
    """Biểu thưởng đọc từ văn bản so với bộ đơn giá đang dùng: '' = trùng; khác -> chữ nêu mức khác."""
    con = csdl.mo(don_gia.file_dang_dung(), chi_doc=True)
    try:
        cu = {int(D(str(r[0]))): int(D(str(r[1]))) for r in con.execute('SELECT tu, muc FROM bieu_thuong')}
    finally:
        con.close()
    moi = dict(bieu)
    khac = [f'từ {t:,} đ: {cu.get(t, 0):,} -> {moi.get(t, 0):,} đ'.replace(',', '.') for t in sorted(set(cu) | set(moi)) if cu.get(t) != moi.get(t)]
    return '; '.join(khac)


def muc_chinh_sach_tu_dieu_khoan(dong: list, nhom: int = 4) -> tuple:
    """Toàn văn văn bản chính sách bồi thường, hỗ trợ, tái định cư -> (ds Muc, câu cần xem, biểu thưởng). Đọc theo cấu trúc Điều / khoản / điểm:
    - điểm a) b) c) kèm câu dẫn của khoản ("Di chuyển trong địa bàn cấp xã: 10.000.000 đồng/hộ"; Điều 12 khoản 2 không trùng tên Điều 8);
    - ma trận xã / phường x nhân khẩu ("6.000.000 đồng/hộ/tháng tại địa bàn xã, 8.000.000 đồng/hộ/tháng tại địa bàn phường…");
    - hệ số ("bằng 1,5 lần giá đất nông nghiệp": Muc.he_so, không phải số tiền);
    - mức cụ thể (đồng/m², đồng/mộ, đồng/đơn vị vật nuôi, đồng/mét dài, đồng trên một hộ).
    Bỏ đoạn "Ví dụ", Điều hiệu lực / tổ chức thực hiện. Mục dẫn chiếu Luật / Nghị định (ổn định đời sống: "30 kg gạo") không có số tiền trong
    văn bản: không tạo dòng, so_khop giữ nguyên mục cũ."""
    ds, xem, da = [], [], set()
    van = bo_vi_du(dong_loi_van(dong))
    for d in van_theo_dieu(van):
        ten_d = sua_chu_ocr(ten_dieu_gon(bo_dan_chieu(d['ten'])))
        kd_ten = bo_dau(ten_d)
        if _RE_DIEU_HANH_CHINH.search(kd_ten):
            continue
        toan_dieu = bo_dau(' '.join(d['dong']))
        don_vi_kg = re.search(r'tuong duong\s*(\d+)\s*kg\s*khoi luong', toan_dieu)
        for khoan, diem, than, goc, dan in cac_khoan_dieu(d):
            can_cu = ' '.join(x for x in (f'Điểm {diem}' if diem else '', f'khoản {khoan}' if khoan else '', f'Điều {d["so"]}') if x)
            can_cu = can_cu[:1].upper() + can_cu[1:]
            nguon = f'[{can_cu}] {goc[:300]}'
            k_than = bo_dau(than)
            for mh in re.finditer(r'\bbang\s+(\d+(?:[.,]\d+)?)\s+lan\s+gia\s+dat\s+nong\s+nghiep', k_than):
                if re.search(r'dao tao|chuyen doi nghe', kd_ten):
                    hs = mh.group(1).replace(',', '.')
                    if ('hs', hs) not in da:
                        da.add(('hs', hs))
                        ds.append(Muc(f'Hỗ trợ đào tạo, chuyển đổi nghề và tìm kiếm việc làm (hệ số {hs.replace(".", ",")})', 'm²', 0, '', nguon,
                                      nhom=nhom, he_so=hs, can_cu=can_cu, ngu_canh=ten_d,
                                      ghi_chu='Lần giá đất nông nghiệp cùng loại trong bảng giá đất của địa phương'))
            mg = re.search(r'tuong duong\s*(\d+)\s*kg\s*gao', k_than)
            if mg:
                xem.append(f'{can_cu}: tính bằng tiền tương đương {mg.group(1)} kg gạo - giữ các mục ổn định đời sống của bộ đơn giá, tính theo giá gạo.')
            gia = list(_RE_GIA_VAN.finditer(than))
            pos = 0
            for j, m in enumerate(gia):
                truoc = than[pos:m.start()]
                pos = m.end()
                g = _so_tien_van(m)
                dvt = _chuan_dvt_van(m.group('dvt'))
                if not g:
                    continue
                if dvt == 'm' and 'dau tu vao dat' in kd_ten:      # OCR mất "²": "30.000 đồng/m,"
                    dvt = 'm²'
                sau = bo_dau(than[m.end():gia[j + 1].start() if j + 1 < len(gia) else len(than)])
                mb = re.match(r'\W*(?:tai|tren|o)\s+dia\s+ban\s+(xa|phuong)\b', sau)
                ghi = ''
                if mb:                                  # ma trận xã / phường x nhân khẩu
                    xa = 'xã' if mb.group(1) == 'xa' else 'phường'
                    n = re.search(r'tu\s+0?(\d+)\s+nhan khau tro xuong', k_than)
                    n = n.group(1) if n else '4'
                    ten = f'{ten_d} - địa bàn {xa}' + (f': cộng thêm từ nhân khẩu thứ {int(n) + 1}' if 'khau' in bo_dau(dvt) else f' (hộ đến {n} nhân khẩu)')
                else:
                    ve = _RE_CAU_RIENG.split(truoc)[-1]
                    ve = _RE_CUOI_MUC.sub('', ve.strip(' ,;:'))
                    leaf = sua_chu_ocr(_ten_gon(bo_dan_chieu(ve)))
                    ctx = sua_chu_ocr(_cum_chinh(bo_dan_chieu(dan))) if (dan and (diem or dan.rstrip().endswith(':') or 'nhu sau' in bo_dau(dan))) else ''
                    if not ctx and (len(leaf) < 3 or (len(leaf.split()) < 6 and not re.search(r'h[oô] tr|boi thuong', bo_dau(leaf)))):
                        ctx = ten_d
                    kl, kc = bo_dau(leaf), bo_dau(ctx)
                    if not leaf or kl in kc:
                        ten = ctx
                    elif not ctx or kc in kl:
                        ten = leaf
                    else:
                        ten = f'{ctx} - {leaf}'
                if not ten:
                    xem.append(f'{can_cu}: có số tiền nhưng không rõ tên mục: {goc[:200]}')
                    continue
                if 'dau tu vao dat' in kd_ten and 'thoi han su dung dat con lai' in k_than:
                    ghi = f'P = ({g:,} / T1) x T2; T1: thời hạn sử dụng đất; T2: thời hạn sử dụng đất còn lại'.replace(',', '.')
                elif 'vat nuoi' in bo_dau(dvt) and don_vi_kg:
                    ghi = f'Mỗi đơn vị vật nuôi tương đương {don_vi_kg.group(1)} kg khối lượng vật nuôi sống'
                khoa_da = (d['so'], khoan, diem, g, dvt)
                if khoa_da in da:                       # công thức nhắc lại số tiền
                    continue
                da.add(khoa_da)
                ds.append(Muc(ten[:200], dvt, g, '', nguon, nhom=nhom, can_cu=can_cu, ngu_canh=f'{ten_d} {dan[:160]}', ghi_chu=ghi))
    return ds, xem, doc_bieu_thuong(dong)


# ---------------------------------------------------------------- so khớp với bộ đơn giá đang dùng
@lru_cache(maxsize=200000)
def _khoa(ten: str) -> str:
    return ' '.join(re.sub(r'[^\w ]', ' ', bo_dau(ten)).split())


def _khoa_gon(ten: str) -> str:
    """Khóa tên bỏ phần trong ngoặc: "Năm thu hoạch thứ 1-5 (Năm thứ 4,5,6,7,8)" ~ "Năm thu hoạch thứ 1 - 5"."""
    return _khoa(re.sub(r'\([^)]*\)', ' ', ten))


def _bo_ngoac_cuoi(ten: str) -> str:
    """"Miếu thờ dọc đường, bàn thiên (Vào nghĩa trang quy hoạch)" -> "Miếu thờ dọc đường, bàn thiên"."""
    return re.sub(r'\s*\([^()]*\)\s*\.?\s*$', '', str(ten or ''))


def _khoa_quy_cach(ten: str) -> str:
    """Khóa gọn thêm bỏ chữ "thứ" trước số: "Năm 1" (bộ đơn giá cũ) ~ "Năm thứ 1" (văn bản mới), "Năm thu hoạch thứ 1-3 (Năm thứ
    3,4,5)" ~ "Năm thu hoạch thứ 1 - 3"."""
    return ' '.join(re.sub(r'\bthu (?=\d)', '', _khoa_gon(ten)).split())


def ten_thay_the(ten_moi: str, ten_cu: str) -> str:
    """Tên ghi vào mục cũ khi thay thế: ĐÚNG cách ghi của văn bản mới. 30/10/2026 (người dùng: văn bản không có chú thích "(Năm thứ
    3, 4, 5)"): không còn giữ chú thích quy đổi tuổi của tên cũ - năm tuổi tính theo cấu trúc (hieu_tai_san.bang_tuoi)."""
    return ten_moi


_RE_GHI_CHU_VAN_BAN_CU = re.compile(r'quyet dinh|nghi quyet|\bqd\b|/qd|\bsua doi\b|\bbo sung\b|cap nhat tu')


def ghi_chu_thay_the(gc_cu: str, gc_moi: str, ten_moi: str) -> str:
    """Ghi chú mục cũ khi văn bản mới thay thế văn bản cũ: mật độ theo văn bản mới (bỏ mật độ cũ), bỏ ghi chú thuộc văn bản cũ ("Sửa
    đổi, bổ sung tại Quyết định số 66/2025…", "Cập nhật từ …") và đoạn trùng chữ trong ngoặc của tên mới (bộ cũ từng ghi "roi" của
    "Cây mận (roi)" vào ghi chú); ghi chú khác giữ."""
    ngoac = {_khoa(x) for x in re.findall(r'\(([^)]*)\)', ten_moi)}
    giu = []
    for d in (gc_cu or '').split(';'):
        d = d.strip()
        k = bo_dau(d)
        if not d or _khoa(d) in ngoac or (gc_moi and k.startswith('mat do')) or _RE_GHI_CHU_VAN_BAN_CU.search(k):
            continue
        giu.append(d)
    return '; '.join(([gc_moi] if gc_moi else []) + giu)


NHOM_PHAM_VI = {2: 'nhà, công trình, vật kiến trúc', 3: 'cây trồng', NHOM_VN: 'vật nuôi, thủy sản', 4: 'chính sách hỗ trợ'}
# từ khóa nhận văn bản cũ của nhóm trong danh sách văn bản căn cứ (đoán sẵn văn bản bị thay thế)
_TU_NHOM_VB = {2: r'nha, cong trinh|nha va cong trinh|cong trinh xay dung|vat kien truc', 3: r'cay trong|hoa mau',
               NHOM_VN: r'vat nuoi|thuy san', 4: r'ho tro|tai dinh cu'}


def van_ban_cu_cua_nhom(nhom_ds: set) -> list:
    """[(id, số hiệu, nội dung)] văn bản trong danh sách văn bản căn cứ của bộ đơn giá đang dùng có nội dung về nhóm (để chọn văn bản
    bị thay thế). Bỏ văn bản sửa đổi / dự thảo / đã hết hiệu lực."""
    con = csdl.mo(don_gia.file_dang_dung(), chi_doc=True)
    try:
        ds = con.execute('SELECT id, so_hieu, noi_dung, trang_thai FROM van_ban ORDER BY id').fetchall()
    finally:
        con.close()
    mau = '|'.join(_TU_NHOM_VB[n] for n in sorted(nhom_ds) if n in _TU_NHOM_VB)
    kq = []
    for i, sh, nd, tt in ds:
        k = bo_dau(f'{sh} {nd}')
        if mau and re.search(mau, k) and not re.search(r'du thao|het hieu luc|^sua doi', bo_dau(f'{nd} {tt}')) \
                and re.search(r'quyet dinh|\bqd\b', bo_dau(sh)):
            kq.append((i, sh, nd))
    return kq


GAN_DUNG = 0.9          # tên giống >= 90% (cùng ĐVT) thì coi là cùng mục; hiện "gần đúng" để người dùng xem lại


def _giong_tung_phan(a: str, b: str) -> bool:
    """Tên gần đúng phải giống cả phần ngoài ngoặc lẫn phần trong ngoặc (>= GAN_DUNG): điều kiện dài trong ngoặc giống hệt nhau
    làm cả tên giống 93% dù là mục khác ("Ao nuôi tôm nước lợ - Nuôi quảng canh (nuôi dưới 50% định mức…)" ~ "Ao nuôi tôm
    nước ngọt - Nuôi thâm canh (nuôi dưới 50% định mức…)") - ghép nhầm sẽ ghi đè giá của mục khác."""
    import difflib

    def ngoac(s):
        return _khoa(' '.join(re.findall(r'\(([^)]*)\)', s)))
    return all(difflib.SequenceMatcher(None, x, y).ratio() >= GAN_DUNG
               for x, y in ((_khoa_gon(a), _khoa_gon(b)), (ngoac(a), ngoac(b))))


_NHO_GAN = {}


NGUONG_KHOP_THEO_GIA = 0.55        # tên giống tối thiểu khi khớp theo đơn giá trùng (so_khop, bước sau cùng)

# ---------------------------------------------------------------- so khớp theo ĐẶC TRƯNG (02/11/2026)
# Văn bản ghi tên khác bộ đơn giá ("Giếng thả ống ciment (kể cả lắp đặt) - Ống 1 m Φ1,2 m" ~ "Giếng thả ống ciment Φ1,2m (ống 1m)" +
# ghi chú "Kể cả lắp đặt"): so cỡ Φ / D, số đo có đơn vị, vật liệu kết cấu chính, ĐVT và các từ - không so chuỗi tên.
_RE_PHI = re.compile(r'[φϕø∅®©]\s*(\d+(?:[.,]\d+)?)\s*(mm|cm|m)?(?![\w²³])')
_RE_D_ONG = re.compile(r'\bd\s?(\d{2,3})\b')
_TU_BO = frozenset('va cac loai co cua bang ke ca thi tu tro len duoc the khac tai san hoac mot cho theo tren duoi voi la gom ket '
                   'cau kem trong so m mm cm'.split())
NGUONG_PHU = 0.6        # tỷ lệ từ của tên văn bản có trong mục (tên + ghi chú) tối thiểu
NGUONG_PHU_MUC = 0.5    # tỷ lệ từ của tên mục có trong tên văn bản tối thiểu (0,3 khi cùng cỡ Φ)
CACH_DAC_TRUNG, CACH_DONG_CHUNG = 'đặc trưng', 'dòng chung'
CACH_THAP, CACH_CAO = 'khoảng giá: mức thấp', 'khoảng giá: mức cao'


def _chuoi_so(v) -> str:
    return str(int(v)) if v == int(v) else format(v.normalize(), 'f')


def _ket_cau_chinh(k: str) -> str:
    """Vật liệu kết cấu chính (chữ không dấu): 'kct' bê tông không cốt thép, 'ct' cốt thép / BTCT, 'xay' xây gạch, xây đá, 'bt' bê
    tông (không nói cốt thép); '' không rõ. Hai tên cùng có mà khác nhau -> hai mục khác nhau."""
    if re.search(r'khong (?:co )?cot thep', k):
        return 'kct'
    if re.search(r'cot thep|\bbtct\b', k):
        return 'ct'
    if re.search(r'xay gach|gach xay|xay da|\bxay\b', k):
        return 'xay'
    if 'be tong' in k:
        return 'bt'
    return ''


def dac_trung(ten: str) -> tuple:
    """(cỡ Φ / D quy về mm, số đo có đơn vị {'1m', '10cm'}, kết cấu chính, số trơn, các từ) của một tên."""
    return _dac_trung(str(ten or ''))


def _dac_trung_goc(ten: str) -> tuple:
    from decimal import Decimal, InvalidOperation
    k = re.sub(r'\bmet\b', 'm', bo_dau(ten))
    phi = set()

    def lay(mt):
        try:
            v = Decimal(mt.group(1).replace(',', '.'))
        except InvalidOperation:
            return ' '
        dv = mt.group(2) or ''
        if dv == 'm' or (not dv and v < 10):            # "Φ0,8" (không đơn vị, nhỏ hơn 10) là mét; "Φ60" là mm
            v *= 1000
        elif dv == 'cm':
            v *= 10
        phi.add(_chuoi_so(v))
        return ' '
    k = _RE_PHI.sub(lay, k)
    k = _RE_D_ONG.sub(lambda mt: phi.add(str(int(mt.group(1)))) or ' ', k)
    k = re.sub(r'(\d)\s+(mm|cm|m)\b', r'\1\2', k)
    so_do = frozenset(re.findall(r'\d+(?:,\d+)?(?:mm|cm|m)\b', k))
    tu = [re.sub(r'^0+(?=\d)', '', t) for t in re.findall(r'[a-z0-9][a-z0-9,]*', k)]
    tu = frozenset(t.rstrip(',') for t in tu if t not in _TU_BO)
    so = frozenset(t for t in tu if re.fullmatch(r'[\d,]+', t))
    return frozenset(phi), so_do, _ket_cau_chinh(k), so, tu


try:
    from functools import lru_cache as _lru
    _dac_trung = _lru(maxsize=50000)(_dac_trung_goc)
except ImportError:                                      # pragma: no cover
    _dac_trung = _dac_trung_goc


def _cung_dvt(a: str, b: str) -> bool:
    return not a or not b or _dvt_khoa(a) == _dvt_khoa(b)


def diem_dac_trung(ten: str, dvt: str, x: dict) -> float | None:
    """Độ giống theo đặc trưng giữa tên văn bản và một mục bộ đơn giá (dict ten, dvt, ghi_chu); None = khác mục (khác ĐVT, khác cỡ Φ,
    số đo mâu thuẫn, khác kết cấu chính, khác số năm / số trơn, quá ít từ chung)."""
    if not _cung_dvt(dvt, x.get('dvt') or ''):
        return None
    p1, s1, c1, n1, w1 = dac_trung(ten)
    p2, s2, c2, n2, w2 = dac_trung(x['ten'])
    if p1 != p2 or (c1 and c2 and c1 != c2) or (s1 and s2 and not (s1 <= s2 or s2 <= s1)) or (n1 and n2 and n1 != n2):
        return None
    if not w1 or not w2:
        return None
    wg = w2 | dac_trung(x.get('ghi_chu') or '')[4]
    phu = len(w1 & wg) / len(w1)
    phu_x = len(w1 & w2) / len(w2)
    if phu < NGUONG_PHU or (phu_x < NGUONG_PHU_MUC and not (p1 and phu_x >= 0.3)):
        return None
    return round((phu + phu_x) / 2, 3)


def _tu_dau(ten: str) -> str:
    t = dac_trung(ten)[4]
    for w in re.findall(r'[a-z0-9][a-z0-9,]*', re.sub(r'\bmet\b', 'm', bo_dau(ten))):
        if w in t and not w.isdigit():
            return w
    return ''


def _cung_tu_dau(a: str, b: str) -> bool:
    """Khớp theo đặc trưng: từ có nghĩa đầu tiên của hai tên trùng nhau ("Giếng …" / "Giếng …"), trừ khi cùng có cỡ Φ (dòng con mất tên
    cha: "Ống 1 m Φ1m" ~ "Giếng thả ống Φ1m (ống 1m)")."""
    pa = dac_trung(a)[0]
    return (pa and pa == dac_trung(b)[0]) or _tu_dau(a) == _tu_dau(b)


def _chon_dau(ds_x, m):
    """Nhiều mục cùng tên bỏ dấu: mục có chữ có dấu khớp tên văn bản (mục sau cùng nếu nhiều); không mục nào khớp dấu -> None."""
    if not ds_x:
        return None
    cung = [x for x in ds_x if not _dau_khac(m, x)]
    if len(cung) > 1:
        # 1.0.57: chỉ khác ký hiệu so sánh ("Ống bi bê tông đường kính < 1m" / "… ≥ 1m" - khóa tên bỏ ký hiệu): mục ghi đúng ký hiệu
        def ky(s):
            return ' '.join(re.sub(r'[^\w<>≤≥=]', ' ', str(s or '').lower()).split()).replace(' ', '')
        dung = [x for x in cung if ky(x['ten']) == ky(m.ten_loai or m.ten)]
        if dung:
            return dung[-1]
    return cung[-1] if cung else None


def _dau_khac(m, x) -> bool:
    """Tên văn bản và tên mục chỉ giống khi bỏ dấu ("Sữa (Mò cua)" / "Sưa (Mò cua)")."""
    from .ten_cay_lam_nghiep import bo_ten_khac

    def k(s):
        return ' '.join(re.sub(r'[^\w ]', ' ', s.lower()).split())
    a = k(m.ten_loai or m.ten)
    return not any(k(t).startswith(a) for t in (x['ten'], bo_ten_khac(x['ten'])))


def chu_the_chung(cha: str) -> tuple | None:
    """Dòng cha nêu NHIỀU tài sản dùng chung các mức giá con ("Trụ cổng, bờ kè và các loại tài sản khác có kết cấu:" + "- Bằng bê
    tông cốt thép …") -> ([chủ thể không dấu: 'tru cong', 'bo ke'], có "các loại … khác"); không phải -> None."""
    k = ' '.join(bo_dau(cha or '').split())
    if not k:
        return None
    khac = bool(re.search(r'cac loai\b.{0,40}\bkhac\b|\bva cac\b', k))
    dau = re.split(r'\b(?:va cac|cac loai|co ket cau|ket cau|bang)\b|[(:]', k)[0]
    chu_the = [s.strip() for s in re.split(r',|\bva\b|/', dau) if len(s.strip()) >= 3]
    if len(chu_the) >= 2 or (khac and chu_the):
        return chu_the, khac
    return None


CACH_TACH_LOAI = 'tách loài'
_RE_DS_LOAI_NGAN = re.compile(r'[,;.](?!\d)')


def ds_loai_trong_ten(ten: str) -> list:
    """Tên văn bản ghi NHIỀU loài cùng một giá ("Cây cải xanh, cải ngọt, cải thìa (họ cải các loại)", "Cây Bã đậu, Phượng, Phi lao",
    "Si cảnh, Sanh cảnh, Sung cảnh. Lộc vừng") -> [tên từng loài theo cách bộ đơn giá ghi: "Cây cải xanh", "Cây cải ngọt"…] (loài sau
    mang tiền tố "Cây" / "Cỏ" của loài đầu, viết hoa chữ đầu như loài đầu). Không phải danh sách: []."""
    goc = ' '.join(re.sub(r'\([^)]*\)', ' ', ten or '').split()).strip(' .;:')
    phan = [x.strip(' .') for x in _RE_DS_LOAI_NGAN.split(goc) if x.strip(' .')]
    if len(phan) < 2 or any(len(x.split()) > 5 or re.search(r'\d', x) for x in phan):
        return []
    tien_to = ''
    m = re.match(r'(?i)(cây|cỏ)\s+', phan[0])
    if m:
        tien_to = m.group(1)
    kq = [phan[0]]
    for x in phan[1:]:
        if tien_to and not re.match(rf'(?i){tien_to}\b', x):
            x = f'{tien_to} {x}'
        elif not tien_to:
            x = x[:1].upper() + x[1:]
        kq.append(x)
    return kq


def _dau_giong(dau: str, ds_: list, nho: dict) -> set:
    """Các tên loài (phần đầu tên mục, không dấu) của bộ giống `dau` >= GAN_DUNG_LOAI - tính một lần mỗi tên trong một lần so khớp."""
    import difflib
    if dau not in nho:
        if '_dau' not in nho:
            nho['_dau'] = {_dau_ten(x['ten']) for x in ds_}
        kq = set()
        sm = difflib.SequenceMatcher(None, dau)        # cùng chiều so sánh như trước (a = tên văn bản, b = tên bộ)
        for h in nho['_dau']:
            if abs(len(h) - len(dau)) > 3:
                continue
            sm.set_seq2(h)
            if sm.real_quick_ratio() >= GAN_DUNG_LOAI and sm.quick_ratio() >= GAN_DUNG_LOAI and sm.ratio() >= GAN_DUNG_LOAI:
                kq.add(h)
        nho[dau] = kq
    return nho[dau]


def _tim_loai(t: str, duoi: str, m, n: int, bang_n: tuple, ds_: list, da_khop: set, nho: dict | None = None):
    """Mục bộ đơn giá của một loài tách từ dòng nhiều loài: tên đúng / quy cách, có hoặc không tiền tố "Cây"; tên bỏ ngoặc (bộ ghi
    "Cây Liễu (mức 79.000 đ/cây)", "Ti gôn (trồng theo cụm…)") - nhiều mục thì mục cùng giá; gần đúng cùng loài (bản scan: "Liêu",
    "Đk thân kỐ 10cm")."""
    import difflib
    _, theo_ten, _, _, qc, cung_gon = bang_n
    thu = [t, re.sub(r'(?i)^cây\s+', '', t), f'Cây {t}']
    for s in thu:
        x = theo_ten.get(_khoa(s + duoi)) or qc.get(_khoa_quy_cach(s + duoi))
        if x is not None and (n, x['ma']) not in da_khop:
            return x
    for s in thu:
        ung = [x for x in cung_gon.get(_khoa_gon(s + duoi), ()) if (n, x['ma']) not in da_khop and _cung_dvt(m.dvt, x['dvt'] or '')]
        cung = [x for x in ung if doc_gia(x['don_gia']) == m.don_gia]
        if len(cung) == 1 or len(ung) == 1:
            return (cung or ung)[0]
    tot, diem = None, 0.0
    nho = {} if nho is None else nho
    for s in thu:
        dau, dich = _khoa(s).replace(' ', ''), _khoa(s + duoi).replace(' ', '')
        for x in ds_:
            k = _khoa(x['ten']).replace(' ', '')
            if not k.startswith(dau) and _dau_ten(x['ten']) not in _dau_giong(dau, ds_, nho):
                continue
            if (n, x['ma']) in da_khop or not _cung_dvt(m.dvt, x['dvt'] or '') or _mau_thuan(s + duoi, x['ten']):
                continue
            d = difflib.SequenceMatcher(None, dich, k).ratio() + (0.02 if doc_gia(x['don_gia']) == m.don_gia else 0)
            if d > diem:
                tot, diem = x, d
    return tot if diem >= GAN_DUNG_LOAI else None


@lru_cache(maxsize=50000)
def _dau_ten(ten: str) -> str:
    """Tên loài (phần trước " - " / ngoặc) không dấu, bỏ khoảng trắng."""
    return _khoa(re.split(r' - |\(', ten)[0]).replace(' ', '')


GAN_DUNG_LOAI = 0.85        # tách loài: tên loài + quy cách giống tối thiểu (bản scan sai dấu / ký hiệu)


def _mau_thuan(a: str, b: str) -> bool:
    """Hai tên khác số đo / cỡ Φ / số năm: không cùng mục dù chữ giống ("(d >42 cm)" / "(d <2 cm)")."""
    p1, s1, _, n1, _ = dac_trung(a)
    p2, s2, _, n2, _ = dac_trung(b)
    return (p1 and p2 and p1 != p2) or (s1 and s2 and not (s1 <= s2 or s2 <= s1)) or (n1 and n2 and n1 != n2)


_NHAM_SO = {frozenset(x) for x in ('17', '18', '58', '56', '68', '38', '08', '06', '09', '89', '14', '35', '27', '36', '23', '45')}


def nham_chu_so(a: int, b: int) -> bool:
    """Hai số tiền chỉ khác 1-4 chữ số, mỗi chữ số đều là cặp hay bị nhận dạng nhầm ("157.000" / "187.000") hoặc chênh quá xa (thiếu chữ số: "7.000" /
    "377.000") - giá đọc từ bản scan có thể sai."""
    if not a or not b:
        return False
    if a * 5 < b * 2 or a * 2 > b * 5:
        return True
    x, y = str(a), str(b)
    if len(x) != len(y):
        return False
    khac = [(c, d) for c, d in zip(x, y) if c != d]
    return 0 < len(khac) <= 4 and all(frozenset(t) in _NHAM_SO for t in khac)


# ---------------------------------------------------------------- 1.0.60: khớp dòng chính sách với mục hỗ trợ (dm_hotro)
# nhóm nghiệp vụ (theo thứ tự: nhóm hẹp trước), trên chữ bỏ dấu
_NHOM_CS = (('on_dinh', r'on dinh doi song'), ('dau_tu', r'dau tu vao dat'), ('vat_nuoi', r'vat nuoi'),
            ('gpxd', r'giay phep|thao do, pha do'), ('mo_ma', r'mo ma'),
            ('di_chuyen', r'di chuyen tai san|thao do, di chuyen|di chuyen trong|di chuyen ngoai'),
            ('dao_tao', r'dao tao|chuyen doi nghe'), ('tu_lo', r'tu lo cho o'), ('thue_nha', r'thue nha|tam cu'),
            ('cao_do', r'cao do|cai tao lai'), ('chinh_sach', r'liet si|thuong binh|benh binh|ho ngheo|dan toc thieu so|ho chinh sach'))
_RE_DIEU_CAN_CU = re.compile(r'(?:khoan\s+(\d+)\s+)?dieu\s+(\d+)\s+qd')
_RE_DIEU_MUC = re.compile(r'(?:khoan\s+(\d+)\s+)?dieu\s+(\d+)\b')
CACH_CHINH_SACH = 'theo điều khoản'
CACH_CUNG_MUC = 'cùng mức với mục đã khớp'
CACH_DAN_CHIEU = 'được dẫn chiếu trong văn bản'


def nhom_chinh_sach(chu: str) -> str:
    k = bo_dau(chu)
    return next((t for t, mau in _NHOM_CS if re.search(mau, k)), '')


def _dvt_cs(d: str) -> str:
    k = bo_dau(d)
    return 'nk' if 'khau' in k else 'thang' if 'thang' in k else _dvt_khoa(d)


def _vi_tri_cs(k: str) -> str:
    """Phạm vi trong tên mục: trong xã / sang xã khác / ngoài tỉnh; địa bàn xã / phường."""
    if re.search(r'ngoai tinh|ngoai thanh pho', k):
        return 'ngoai_tinh'
    if re.search(r'ngoai dia ban|sang xa', k):
        return 'ngoai_xa'
    if re.search(r'trong (?:dia ban|pham vi|xa)', k):
        return 'trong_xa'
    return ''


def _xa_phuong(k: str) -> str:
    m = re.search(r'dia ban (xa|phuong)\b', k)
    return m.group(1) if m else ''


def _khop_chinh_sach(m, ds_hotro_cu: list, da_ma: set) -> tuple:
    """Mục hỗ trợ của bộ đơn giá ứng với dòng đọc từ điều khoản -> (dòng dm_hotro, dùng lại?) hoặc (None, False). Cùng nhóm nghiệp vụ là bắt
    buộc; chấm điểm theo (a) Điều / khoản trong cột căn cứ, (b) đơn giá + ĐVT, (c) phạm vi xã / phường, trong xã / ngoài xã / ngoài tỉnh.
    Khớp 1-1; hết mục chưa khớp mà cùng nhóm, cùng giá với mục đã khớp (Điều 17 cùng mức Điều 14; hộ nghèo cùng mức thương binh 21-60%) ->
    dùng lại mục đó, không sinh mã mới. Khác giá chỉ nhận khi không còn mục cùng giá và ứng viên rõ ràng (đổi giá thật)."""
    nhom = nhom_chinh_sach(m.ten) or nhom_chinh_sach(m.ngu_canh)
    if not nhom:
        return None, False
    k_m = bo_dau(f'{m.ten}')
    he_moi = D(m.he_so) if m.he_so else None
    md = _RE_DIEU_MUC.search(bo_dau(m.can_cu))
    dv = _dvt_cs(m.dvt)
    vt, xp = _vi_tri_cs(k_m), _xa_phuong(k_m)
    ung = []
    for x in ds_hotro_cu:
        k_x = bo_dau(x['ten'])
        if nhom_chinh_sach(x['ten']) != nhom:
            continue
        if xp and _xa_phuong(k_x) and xp != _xa_phuong(k_x):
            continue
        if vt and _vi_tri_cs(k_x) and vt != _vi_tri_cs(k_x):
            continue
        dvx = _dvt_cs(x['dvt'] or '')
        if dv and dvx and dv != dvx:
            continue
        cu = x['don_gia']
        if m.he_so:
            try:
                cung_gia = D(str(cu)) == he_moi
            except ValueError:
                cung_gia = False
        else:
            cung_gia = doc_gia(cu) == m.don_gia if cu not in (None, '') else False
        diem = 4 if cung_gia else 0
        if md:
            for mx in _RE_DIEU_CAN_CU.finditer(bo_dau(x.get('can_cu') or '')):
                if mx.group(2) == md.group(2):
                    diem += 2 + (1 if mx.group(1) and mx.group(1) == md.group(1) else 0)
                    break
        ung.append((diem, cung_gia, x))
    if not ung:
        return None, False
    ung.sort(key=lambda t: -t[0])
    chua = [t for t in ung if t[2]['ma'] not in da_ma]
    gia_chua = [t for t in chua if t[1]]
    if gia_chua:
        return gia_chua[0][2], False
    gia_da = [t for t in ung if t[1] and t[2]['ma'] in da_ma]
    if gia_da:
        return gia_da[0][2], True
    # đổi giá: chỉ một ứng viên chưa khớp, hoặc ứng viên hơn hẳn theo Điều / khoản
    if chua and (len(chua) == 1 or chua[0][0] > chua[1][0]) and (vt or xp or len(chua) == 1 or chua[0][0] >= 2):
        return chua[0][2], False
    return None, False


def la_muc_dan_chieu(x: dict) -> bool:
    """Mục hỗ trợ không phải mức tiền do chính văn bản ấn định (dẫn chiếu Luật / Nghị định, hệ số, nhập theo dự án): văn bản chính sách
    không ghi số tiền thì giữ nguyên, không phải "bỏ"."""
    from .nghiep_vu import MA_DAO_TAO, MA_ON_DINH, MA_TDC
    g = doc_gia(x['don_gia']) if x['don_gia'] not in (None, '') else None
    return x['ma'] in MA_ON_DINH or x['ma'] in MA_TDC or x['ma'] in MA_DAO_TAO or not g or g < GIA_TOI_THIEU


def _doc_bo_hien_hanh(chi_ma: set | None) -> tuple:
    """Bộ đơn giá đang dùng: ({nhóm: [mục]}, dấu phiên bản của bộ (khóa nhớ khớp gần đúng), {tiền tố mã: số lớn nhất} của CẢ bộ)."""
    f = don_gia.file_dang_dung()
    try:
        ban = (str(f), os.path.getmtime(f), os.path.getsize(f))   # bộ đơn giá đổi (cập nhật) -> khóa nhớ khác
    except OSError:
        ban = (str(f), 0, 0)
    con = csdl.mo(f, chi_doc=True)
    try:
        hien = {4: [dict(r) for r in con.execute("SELECT ma, ten, dvt, don_gia, can_cu, '' AS ghi_chu FROM dm_hotro")]}
        for n in (2, 3):
            hien[n] = [dict(r) for r in con.execute('SELECT ma, ten, dvt, don_gia, phan_loai, ghi_chu FROM dm_taisan WHERE nhom = ? '
                                                    'ORDER BY rowid', (n,))]
        # vật nuôi (nhóm 7 khi phân tích): các dòng nhóm 3 có mã VN / phân loại vật nuôi - nhóm 3 vẫn gồm cả hai (giữ cách khớp cũ)
        from .nghiep_vu import la_vat_nuoi
        hien[NHOM_VN] = [x for x in hien[3] if str(x['ma']).upper().startswith('VN') or la_vat_nuoi(x['phan_loai'])]
    finally:
        con.close()
    lon_bo = _so_lon_nhat(hien)                         # mã mới: số tiếp theo của CẢ bộ (kể cả mục khu vực khác)
    if chi_ma is not None:
        hien = {n: [x for x in v if x['ma'] in chi_ma] for n, v in hien.items()}
        ban = ban + (len(chi_ma), hash(frozenset(chi_ma)))
    return hien, ban, lon_bo


def _lap_bang_tra(hien: dict) -> tuple:
    """Bảng tra theo từng nhóm: bang[n] = (theo mã, theo tên, theo ĐVT + tên, tên bỏ ngoặc, quy cách, cùng tên bỏ ngoặc); trung_dau[n]: tên bỏ dấu trùng nhiều mục."""
    from .ten_cay_lam_nghiep import bo_ten_khac
    bang, trung_dau = {}, {}
    for n, ds_ in hien.items():
        theo_dvt, gon, qc = {}, {}, {}
        for x in ds_:
            theo_dvt.setdefault(_dvt_khoa(x['dvt'] or ''), {})[_khoa(x['ten'])] = x
            gon.setdefault(_khoa_gon(x['ten']), []).append(x)
            qc.setdefault(_khoa_quy_cach(x['ten']), []).append(x)
        gon = {k: v[0] for k, v in gon.items() if len(v) == 1}       # bỏ ngoặc mà trùng nhiều mục: không dùng
        qc = {k: v[0] for k, v in qc.items() if len(v) == 1}
        theo_ten = {_khoa(x['ten']): x for x in ds_}
        cung_gon = {}
        for x in ds_:                   # tên bỏ ngoặc trùng nhiều mục khác ĐVT ("Cây chuối" ha / m²): chọn theo giá khi văn bản không ghi ĐVT
            cung_gon.setdefault(_khoa_gon(x['ten']), []).append(x)
        for x in ds_:                   # 26/10/2026: tên cây lâm nghiệp có tên khác ("Bách xanh (Tùng hương) (d …)") vẫn khớp tên văn bản
            theo_ten.setdefault(_khoa(bo_ten_khac(x['ten'])), x)
        bang[n] = ({x['ma'].upper(): x for x in ds_}, theo_ten, theo_dvt, gon, qc, cung_gon)
        ten_ds = {}                     # tên bỏ dấu trùng nhiều mục ("Sưa" / "Sữa"): giữ cả, chọn theo chữ có dấu
        for x in ds_:
            for kh in {_khoa(x['ten']), _khoa(bo_ten_khac(x['ten']))}:
                ten_ds.setdefault(kh, []).append(x)
        trung_dau[n] = {k: v for k, v in ten_ds.items() if len(v) > 1}
    return bang, trung_dau


class _PhienKhop:
    """Trạng thái một lượt so_khop, dùng chung giữa các bước khớp."""

    def __init__(self, hien: dict, ban: tuple, nhom: int | None, thay_the: bool):
        self.hien, self.ban, self.nhom, self.thay_the = hien, ban, nhom, thay_the
        self.bang, self.trung_dau = _lap_bang_tra(hien)
        self.da_khop = set()            # (nhóm, mã) đã có dòng khớp
        self.chi_muc = {}               # nhóm -> {từ: [vị trí mục]} - lọc ứng viên so theo đặc trưng
        self.xong = set()               # id(dòng) đã xử lý ở một bước trước, các bước sau bỏ qua

    def nhom_cua(self, m) -> int:
        return self.nhom or m.nhom or 3

    def ung_vien(self, ten, dvt, n, bo_khop=True):
        """[(điểm, mục)] theo đặc trưng, điểm giảm dần."""
        hien, da_khop, chi_muc = self.hien, self.da_khop, self.chi_muc
        if n not in chi_muc:
            cm = {}
            for i, x in enumerate(hien[n]):
                for t in dac_trung(x['ten'])[4] | dac_trung(x['ghi_chu'] or '')[4]:
                    cm.setdefault(t, []).append(i)
            chi_muc[n] = cm
        w = dac_trung(ten)[4]
        dem = {}
        for t in w:
            for i in chi_muc[n].get(t, ()):
                dem[i] = dem.get(i, 0) + 1
        can = NGUONG_PHU * len(w)
        kq = []
        for i, c in dem.items():
            x = hien[n][i]
            if c < can or (bo_khop and (n, x['ma']) in da_khop):
                continue
            d = diem_dac_trung(ten, dvt, x)
            if d is not None:
                kq.append((d, i, x))
        kq.sort(key=lambda t: (-t[0], t[1]))
        return [(d, x) for d, _, x in kq]

    def ghi_khop(self, m, r, n):
        """Ghi kết quả khớp mục r (None = mục mới) vào dòng m: trạng thái, giá cũ; thay_the: tên / ghi chú thay."""
        m.ten_thay = m.ghi_chu_thay = ''
        if r is None:
            m.trang_thai, m.ma_khop, m.gia_cu, m.ten_cu, m.ghi_chu_cu = 'mới', '', None, '', ''
            return
        m.ma_khop, m.ten_cu, m.ghi_chu_cu = r['ma'], r['ten'], r['ghi_chu'] or ''
        self.da_khop.add((n, r['ma']))
        m.gia_cu = doc_gia(r['don_gia']) if r['don_gia'] not in (None, '') else None
        m.trang_thai = 'giữ nguyên' if m.gia_cu == m.don_gia else 'cập nhật'
        if m.he_so:                                     # 1.0.60: hệ số (Điều 13 QĐ 42/2025) so theo số, không theo tiền
            m.he_so_cu = str(r['don_gia'] or '')
            try:
                m.trang_thai = 'giữ nguyên' if D(m.he_so_cu) == D(m.he_so) else 'cập nhật'
            except ValueError:
                m.trang_thai = 'cập nhật'
            m.gia_cu = None
        if m.can_cu:                                    # dòng đọc từ điều khoản: tên mục giữ theo bộ đơn giá (mã, phương án đã lập không đổi)
            return
        if self.thay_the and m.cach_khop != CACH_DONG_CHUNG:   # dòng chung: tên văn bản là của cả nhóm tài sản - giữ tên từng mục
            ten = ten_thay_the(m.ten, r['ten'])
            gc = ghi_chu_thay_the(m.ghi_chu_cu, m.ghi_chu, ten) if n != 4 else ''
            if ten != r['ten'] or (n != 4 and gc != m.ghi_chu_cu):
                m.ten_thay, m.ghi_chu_thay = ten, gc
                if m.trang_thai == 'giữ nguyên':
                    m.trang_thai = 'đổi quy cách'


def _khop_tach_loai(ds: list, p: _PhienKhop) -> None:
    """Bước 0. Dòng ghi nhiều loài cùng giá -> từng loài theo bộ đơn giá (bộ ghi "Cây cải xanh", "Cây cải ngọt"… cùng giá); loài bộ chưa có:
    mục mới. Chỉ tách khi cả tên không khớp mục nào mà ít nhất một loài khớp."""
    them_loai, nho_loai = {}, {}
    for m in ds:
        n = p.nhom_cua(m)
        theo_ma, theo_ten, _, _, qc, _ = p.bang[n]
        if m.can_cu or m.ma or m.muc_gia or m.ten_loai or theo_ten.get(_khoa(m.ten)) or qc.get(_khoa_quy_cach(m.ten)):
            continue
        nguon_ds, duoi = m.ten, ''
        if m.duong_kinh and m.ten.endswith(m.duong_kinh):
            nguon_ds, duoi = m.ten[:-len(m.duong_kinh)].strip(), ' ' + m.duong_kinh
        elif m.cha and m.ten.startswith(m.cha):           # danh sách nằm ở dòng cha: "Si cảnh, Sanh cảnh… - 5cm < Đk thân…"
            nguon_ds, duoi = m.cha, m.ten[len(m.cha):]
        loai = ds_loai_trong_ten(nguon_ds)
        if not loai:
            continue
        ten_loai = []
        for t in loai:
            ten_loai.append((t + duoi, _tim_loai(t, duoi, m, n, p.bang[n], p.hien[n], p.da_khop, nho_loai.setdefault(n, {}))))
        if not any(x for _, x in ten_loai):
            continue
        goc_ten = m.ten
        phu = []
        for i, (t, x) in enumerate(ten_loai):
            y = m if i == 0 else Muc(t, m.dvt, m.don_gia, '', m.nguon_dong, nhom=m.nhom, ghi_chu=m.ghi_chu, cha=m.cha, phu=True,
                                     nghi_gia=m.nghi_gia)
            y.ten, y.tach_tu, y.cach_khop = t, goc_ten, CACH_TACH_LOAI
            p.ghi_khop(y, x, n)
            if x is not None:
                y.khop_gan = 0.0
            p.xong.add(id(y))
            if i:
                phu.append(y)
        them_loai[id(m)] = phu
    if them_loai:
        ds[:] = [y for m in ds for y in [m] + them_loai.get(id(m), [])]


def _khop_khoang_gia(ds: list, p: _PhienKhop) -> None:
    """Bước 1. Khoảng giá "a - b": cặp mục cùng tên (mục cao có dấu chấm cuối tên)."""
    hien, da_khop, xong = p.hien, p.da_khop, p.xong
    for i in range(len(ds) - 1):
        a, b = ds[i], ds[i + 1]
        if a.muc_gia != 'thap' or b.muc_gia != 'cao' or id(a) in xong:
            continue
        n = p.nhom_cua(a)
        k = _khoa(a.ten)
        cap = [x for x in hien[n] if _khoa(x['ten']) == k and _cung_dvt(a.dvt, x['dvt'] or '') and (n, x['ma']) not in da_khop]
        if not cap:
            # 1.0.57: tên văn bản dài hơn tên mục ("Chuồng heo, bò lợp lá, bán kiên cố" / bộ "Chuồng heo, bò lợp lá" + "…lợp lá.") và
            # đúng CẶP giá thấp / cao của hai mục -> cặp đó
            gia2 = {a.don_gia, b.don_gia}
            theo_k = {}
            for x in hien[n]:
                kx = _khoa(x['ten'])
                if kx and len(kx) >= 8 and k.startswith(kx) and _cung_dvt(a.dvt, x['dvt'] or '') and (n, x['ma']) not in da_khop:
                    theo_k.setdefault(kx, []).append(x)
            for kx in sorted(theo_k, key=len, reverse=True):
                if {doc_gia(x['don_gia']) for x in theo_k[kx]} == gia2 and len(theo_k[kx]) == len(gia2):
                    cap = theo_k[kx]
                    break
        diem = 0.0
        if not cap:
            uv = p.ung_vien(a.ten, a.dvt, n)
            if uv:
                diem, k0 = uv[0][0], _khoa(uv[0][1]['ten'])
                cap = [x for d, x in uv if _khoa(x['ten']) == k0 and d >= diem - 0.001]
        cap.sort(key=lambda x: (x['ten'].rstrip().endswith('.'), doc_gia(x['don_gia']) or 0))
        if len(cap) == 1 and cap[0]['ten'].rstrip().endswith('.'):
            cap = [None, cap[0]]
        for m, x, cach in ((a, cap[0] if cap else None, CACH_THAP), (b, cap[1] if len(cap) > 1 else None, CACH_CAO)):
            m.cach_khop = cach
            p.ghi_khop(m, x, n)
            m.khop_gan = diem if x is not None else 0.0
            m.chon = x is not None                          # mục mới của khoảng giá: đề xuất, không chọn sẵn
            if x is None:
                m.ghi_chu = (f'{"Mức cao" if m is b else "Mức thấp"} của khoảng giá {a.khoang or ""} '
                             f'(mức {"thấp" if m is b else "cao"}: {(a if m is b else b).ten})').replace('  ', ' ')
            xong.add(id(m))


def _mo_rong_tai_san_khac(con_: list, gan: dict, vt: dict, muc: list, n: int, da_khop: set) -> None:
    """"các loại tài sản khác": thêm vào gan các mục liền khối cùng ĐVT, đang cùng giá với nhóm của một giá con."""
    theo_gia = {}
    for m in con_:
        for x in gan.get(id(m), ()):
            theo_gia.setdefault(doc_gia(x['don_gia']), set()).add(id(m))
    theo_gia = {g: next(iter(v)) for g, v in theo_gia.items() if g and len(v) == 1}
    co = sorted(vt[id(x)] for v in gan.values() for x in v)
    if co and theo_gia:
        da = {id(x) for v in gan.values() for x in v}
        for buoc, j in ((1, co[-1] + 1), (-1, co[0] - 1)):
            while 0 <= j < len(muc):
                x = muc[j]
                g = doc_gia(x['don_gia']) if x['don_gia'] not in (None, '') else None
                if (n, x['ma']) in da_khop or g not in theo_gia:
                    break
                mm = next(m for m in con_ if id(m) == theo_gia[g])
                if id(x) not in da and _cung_dvt(mm.dvt, x['dvt'] or ''):
                    gan[theo_gia[g]].append(x)
                    da.add(id(x))
                j += buoc
            # khối giữa các mục chủ thể (thứ tự bộ đơn giá xen kẽ)
        for j in range(co[0], co[-1] + 1):
            x = muc[j]
            g = doc_gia(x['don_gia']) if x['don_gia'] not in (None, '') else None
            if id(x) not in da and g in theo_gia and (n, x['ma']) not in da_khop:
                gan[theo_gia[g]].append(x)
                da.add(id(x))


def _khop_dong_chung(ds: list, p: _PhienKhop) -> None:
    """Bước 2. Dòng chung: giá con của dòng cha nêu nhiều tài sản -> mọi mục cùng kết cấu của các tài sản đó."""
    hien, da_khop, xong = p.hien, p.da_khop, p.xong
    them_sau = {}
    nhom_cha = {}
    for m in ds:
        if m.cha and id(m) not in xong and chu_the_chung(m.cha):
            nhom_cha.setdefault((m.cha, p.nhom_cua(m)), []).append(m)
    for (cha, n), con_ in nhom_cha.items():
        chu_the, khac = chu_the_chung(cha)
        gan = {}
        for m in con_:
            kc = _ket_cau_chinh(bo_dau(m.ten[len(cha):] if m.ten.startswith(cha) else m.ten))
            if not kc:
                continue
            gan[id(m)] = [x for x in hien[n] if (n, x['ma']) not in da_khop and _cung_dvt(m.dvt, x['dvt'] or '')
                          and _ket_cau_chinh(bo_dau(x['ten'])) == kc and any(bo_dau(x['ten']).startswith(s) for s in chu_the)]
        if not any(gan.values()):
            continue
        # 1.0.57: hai dòng con cùng trỏ một mục (QĐ 18/2026 "Chuồng heo, chuồng bò, gà, vịt:" - "Xây gạch cao 1m…" / "Xây cao 1m…" đều
        # là kết cấu gạch) -> không phải dòng chung (mỗi dòng con là một mục riêng): để bước khớp tên / giá xử lý
        dem_x = {}
        for v in gan.values():
            for x in v:
                dem_x[id(x)] = dem_x.get(id(x), 0) + 1
        if any(c > 1 for c in dem_x.values()):
            continue
        vt = {id(x): i for i, x in enumerate(hien[n])}
        if khac:
            _mo_rong_tai_san_khac(con_, gan, vt, hien[n], n, da_khop)
        for m in con_:
            ds_x = sorted(gan.get(id(m), ()), key=lambda x: vt[id(x)])
            if not ds_x:
                continue
            m.cach_khop = CACH_DONG_CHUNG
            p.ghi_khop(m, ds_x[0], n)
            xong.add(id(m))
            phu = []
            for x in ds_x[1:]:
                q = Muc(m.ten, m.dvt, m.don_gia, '', m.nguon_dong, nhom=m.nhom, cha=m.cha, phu=True, cach_khop=CACH_DONG_CHUNG,
                        chon=m.chon)
                p.ghi_khop(q, x, n)
                xong.add(id(q))
                phu.append(q)
            them_sau[id(m)] = phu
    if them_sau:
        ds[:] = [y for m in ds for y in [m] + them_sau.get(id(m), [])]


def _khop_dieu_khoan(ds: list, p: _PhienKhop) -> None:
    """Bước 2b (1.0.60). Dòng đọc từ điều khoản văn bản chính sách: theo Điều / khoản, đơn giá + ĐVT, nhóm nghiệp vụ - không qua khớp tên gần đúng."""
    for m in ds:
        if id(m) in p.xong or not m.can_cu or p.nhom_cua(m) != 4:
            continue
        r, dung_lai = _khop_chinh_sach(m, p.hien[4], {ma for nh, ma in p.da_khop if nh == 4})
        p.xong.add(id(m))
        if r is None:
            p.ghi_khop(m, None, 4)
        else:
            m.cach_khop = CACH_CUNG_MUC if dung_lai else CACH_CHINH_SACH
            p.ghi_khop(m, r, 4)


def _khop_ten(ds: list, p: _PhienKhop) -> None:
    """Bước 3. Mã, tên, quy cách, tên gần đúng."""
    import difflib
    for m in ds:
        if id(m) in p.xong:
            continue
        n = p.nhom_cua(m)
        theo_ma, theo_ten, theo_dvt, gon, qc, cung_gon = p.bang[n]
        r = theo_ma.get(m.ma.upper()) if m.ma else None
        r = r or _chon_dau(p.trung_dau[n].get(_khoa(m.ten)), m) or theo_ten.get(_khoa(m.ten))
        if r is None and m.ten_loai:                    # dòng tách theo loài: tên khác của văn bản ghi khác bộ đơn giá
            k_ = _khoa(f'{m.ten_loai} {m.duong_kinh}')
            r = _chon_dau(p.trung_dau[n].get(k_), m) or theo_ten.get(k_)
        if r is not None and (n, r['ma']) in p.da_khop and not m.ma and _dau_khac(m, r):
            r = None                                    # mục đã khớp dòng khác cùng tên bỏ dấu, chữ có dấu khác: loài khác
        if r is not None and not m.dvt and doc_gia(r['don_gia']) != m.don_gia:
            khac = [x for x in cung_gon.get(_khoa_gon(m.ten), ()) if x is not r and doc_gia(x['don_gia']) == m.don_gia]
            if len(khac) == 1:
                r = khac[0]
        for khoa_, bang_ in ((_khoa_gon, gon), (_khoa_quy_cach, qc)):
            if r is None:
                x = bang_.get(khoa_(m.ten))
                r = x if x is not None and _dvt_khoa(x['dvt'] or '') == _dvt_khoa(m.dvt) else None
        if r is None:
            k, dv = _khoa(m.ten), _dvt_khoa(m.dvt)
            cung = theo_dvt.get(dv, {})
            # khớp gần đúng (difflib, so với hàng nghìn tên): nhớ theo bộ đơn giá + nhóm + ĐVT + tên - đổi nhóm, sửa một ô rồi
            # so lại cả bảng không phải tính lại các dòng cũ
            kn = (p.ban, n, dv, m.ten)
            if kn not in _NHO_GAN:
                gan_ = None
                for g in difflib.get_close_matches(k, list(cung), n=3, cutoff=GAN_DUNG):
                    if _giong_tung_phan(m.ten, cung[g]['ten']) and not _mau_thuan(m.ten, cung[g]['ten']):
                        gan_ = (g, difflib.SequenceMatcher(None, k, g).ratio())
                        break
                if len(_NHO_GAN) > 50000:
                    _NHO_GAN.clear()
                _NHO_GAN[kn] = gan_
            if _NHO_GAN[kn] is not None and _NHO_GAN[kn][0] in cung:
                r, m.khop_gan = cung[_NHO_GAN[kn][0]], _NHO_GAN[kn][1]
        p.ghi_khop(m, r, n)


def _khop_dac_trung(ds: list, p: _PhienKhop) -> None:
    """Bước 4 (02/11/2026). Tên văn bản ghi khác bộ - cỡ Φ, số đo, kết cấu, ĐVT, từ; nhiều mục ngang điểm thì thôi (trừ khi đơn giá trùng một mục)."""
    for m in ds:
        if id(m) in p.xong or m.trang_thai != 'mới' or m.ten_loai:
            continue
        n = p.nhom_cua(m)
        uv = [t for t in p.ung_vien(m.ten, m.dvt, n) if _cung_tu_dau(m.ten, t[1]['ten'])]
        if not uv:
            continue
        cung_gia = [t for t in uv if t[0] >= uv[0][0] - 0.05 and doc_gia(t[1]['don_gia']) == m.don_gia]
        if len(uv) > 1 and uv[0][0] - uv[1][0] < 0.05:
            if len(cung_gia) != 1:
                continue
            uv = cung_gia
        m.cach_khop = CACH_DAC_TRUNG
        p.ghi_khop(m, uv[0][1], n)
        m.khop_gan = uv[0][0]


def _khop_cung_gia(ds: list, p: _PhienKhop) -> None:
    """Bước 5. Còn là mục mới mà ĐƠN GIÁ trùng một mục chưa khớp cùng nhóm: 3 mức từ chặt tới rộng."""
    import difflib
    hien, da_khop, xong = p.hien, p.da_khop, p.xong
    # 30/10/2026 (công cụ scan): tên đọc từ bản scan sai chữ ("Cây sori" / "Cây Sơ ri", "Lekina" / "Lekima") nhưng ĐƠN GIÁ trùng một mục
    # cũ chưa khớp cùng nhóm và tên giống nhau một phần -> cùng mục (giá đúng từng đồng hiếm khi trùng ngẫu nhiên)
    for m in ds:
        if m.trang_thai != 'mới' or not m.don_gia or id(m) in xong:
            continue
        n = p.nhom_cua(m)
        k = _khoa_quy_cach(m.ten)
        ung = []
        for x in hien[n]:
            if (n, x['ma']) in da_khop or x['don_gia'] in (None, '') or doc_gia(x['don_gia']) != m.don_gia:
                continue
            ung.append((difflib.SequenceMatcher(None, k, _khoa_quy_cach(x['ten'])).ratio(), x))
        ung.sort(key=lambda t: -t[0])
        if ung and ung[0][0] >= NGUONG_KHOP_THEO_GIA and (len(ung) == 1 or ung[0][0] - ung[1][0] >= 0.1):
            m.khop_gan = ung[0][0]
            p.ghi_khop(m, ung[0][1], n)
    # 1.0.57 (QĐ 18/2026 "Công đào (ao nuôi trồng thủy sản hoặc làm hầm chứa nước, …)" / bộ "Công đào ao/ hầm chứa nước/ cải tạo đầm
    # phá, hố bom"): cùng ĐƠN GIÁ, cùng ĐVT, cùng từ đầu tên và chỉ MỘT mục chưa khớp như vậy -> cùng mục (tên diễn đạt khác)
    for m in ds:
        if m.trang_thai != 'mới' or not m.don_gia or not m.dvt or id(m) in xong or m.muc_gia:
            continue
        n = p.nhom_cua(m)
        dau = _khoa(m.ten).split()[:1]
        ung = [x for x in hien[n] if (n, x['ma']) not in da_khop and x['don_gia'] not in (None, '')
               and doc_gia(x['don_gia']) == m.don_gia and _dvt_khoa(x['dvt'] or '') == _dvt_khoa(m.dvt)
               and _khoa(x['ten']).split()[:1] == dau]
        if len(ung) == 1:
            m.khop_gan = difflib.SequenceMatcher(None, _khoa(m.ten), _khoa(ung[0]['ten'])).ratio()
            m.cach_khop = '; '.join(c for c in (m.cach_khop, 'cùng giá, cùng ĐVT') if c)
            p.ghi_khop(m, ung[0], n)
    # 1.0.57 (QĐ 18/2026: "Miếu thờ dọc đường, bàn thiên" ghi hai lần - trường hợp vào nghĩa trang quy hoạch / tự thu xếp; bộ đơn giá
    # ghi hai mục "… (Vào nghĩa trang quy hoạch)", "… (Tự thu xếp ngoài nghĩa trang)"): tên văn bản = tên mục bỏ ngoặc cuối, cùng
    # giá, cùng ĐVT, nhiều mục ngang nhau -> gán lần lượt theo thứ tự bộ đơn giá (dòng văn bản trước - mục trước)
    for m in ds:
        if m.trang_thai != 'mới' or not m.don_gia or id(m) in xong:
            continue
        n = p.nhom_cua(m)
        k = _khoa_gon(m.ten)
        ung = [x for x in hien[n] if (n, x['ma']) not in da_khop and x['don_gia'] not in (None, '')
               and doc_gia(x['don_gia']) == m.don_gia and _khoa_gon(_bo_ngoac_cuoi(x['ten'])) == k
               and (not m.dvt or _dvt_khoa(x['dvt'] or '') == _dvt_khoa(m.dvt))]
        if ung:
            m.cach_khop = '; '.join(c for c in (m.cach_khop, 'tên bỏ chú thích cuối') if c)
            p.ghi_khop(m, ung[0], n)


def _them_dong_bo(ds: list, p: _PhienKhop, scan: bool) -> None:
    """thay_the: mục cũ CÙNG NHÓM không còn trong văn bản -> thêm dòng 'bỏ'."""
    hien = p.hien
    khop_ma = {ma for _, ma in p.da_khop}
    vn_ma = {x['ma'] for x in hien[NHOM_VN]}
    for n in pham_vi_thay_the(ds, p.nhom):
        for x in hien[n]:
            if x['ma'] in khop_ma or (n == 3 and x['ma'] in vn_ma):
                continue
            g = doc_gia(x['don_gia']) if x['don_gia'] not in (None, '') else 0
            # 1.0.60: văn bản chính sách dẫn chiếu Luật / Nghị định, không ghi số tiền của mục này: giữ nguyên, không báo "bỏ"
            if n == 4 and la_muc_dan_chieu(x):
                ds.append(Muc(x['ten'], x['dvt'] or '', g or 0, trang_thai='giữ nguyên', ma_khop=x['ma'], gia_cu=g, nhom=n, ten_cu=x['ten'],
                              bo_cu=True, chon=False, cach_khop=CACH_DAN_CHIEU, nguon_dong='Văn bản không ấn định lại mức tiền của mục này: giữ nguyên'))
                continue
            ds.append(Muc(x['ten'], x['dvt'] or '', g or 0, trang_thai='bỏ', ma_khop=x['ma'], gia_cu=g, nhom=n,
                          ten_cu=x['ten'], ghi_chu_cu=x['ghi_chu'] or '', bo_cu=True, chon=not scan,
                          nguon_dong=f'Mục {NHOM_PHAM_VI.get(n, "")} trong bộ đơn giá đang dùng nhưng văn bản mới không có'))


def so_khop(ds: list, nhom: int | None = None, thay_the: bool = False, scan: bool = False, chi_ma: set | None = None) -> list:
    """So với bộ đơn giá đang dùng: theo mã, tên (không dấu), tên bỏ ngoặc, quy cách ("Năm 1" ~ "Năm thứ 1"), rồi tên gần đúng cùng
    ĐVT, rồi theo ĐẶC TRƯNG (cỡ Φ, số đo, kết cấu, ĐVT, từ - diem_dac_trung), rồi theo đơn giá trùng. nhom None / 0: mỗi dòng theo
    nhóm của dòng (Muc.nhom); có nhom thì cả bảng theo nhóm đó.

    Khoảng giá (Muc.muc_gia thap / cao): cặp mục cùng tên trong bộ (mục cao có dấu chấm cuối tên - quy ước của bộ đơn giá) - thấp
    gán mục thấp, cao gán mục cao; bộ chưa có cặp thì đề xuất mục mới (không chọn sẵn).
    Dòng chung (dòng cha chu_the_chung + dòng con có kết cấu): mỗi giá con cập nhật MỌI mục của các tài sản nêu ở dòng cha cùng kết
    cấu, cùng ĐVT; "các loại tài sản khác" thêm các mục liền khối cùng ĐVT đang cùng giá với nhóm đó - thêm dòng phụ (phu), không
    thêm mục mới.

    thay_the (30/10/2026, người dùng: "thay thế toàn bộ văn bản cũ bằng văn bản mới, để đúng với toàn bộ nội dung theo văn bản mới"):
    danh mục các nhóm có trong văn bản (cây trồng / nhà, công trình / vật nuôi / hỗ trợ) theo đúng văn bản - mục khớp có tên / mật độ /
    ghi chú khác văn bản -> ten_thay / ghi_chu_thay (giá không đổi: trạng thái 'đổi quy cách'); mục cũ CÙNG NHÓM không còn trong văn
    bản -> thêm dòng 'bỏ' (bo_cu, chọn sẵn). Cây trồng và vật nuôi cùng nhom 3 trong CSDL: văn bản cây trồng không bỏ vật nuôi.

    chi_ma (1.0.57 - so_khop_khu_vuc): chỉ so với các mục có mã trong tập này (mục của một khu vực giá); mã mới vẫn tính theo cả bộ.

    Thứ tự các bước quyết định kết quả (bước trước giữ mục, bước sau không dùng lại): đừng đổi."""
    for m in ds:
        if m.tach_tu and not m.phu:                     # so lại: dòng tách loài về lại dòng văn bản ban đầu
            m.ten, m.tach_tu = m.tach_tu, ''
    ds[:] = [m for m in ds if not m.bo_cu and not m.phu]
    hien, ban, lon_bo = _doc_bo_hien_hanh(chi_ma)
    p = _PhienKhop(hien, ban, nhom, thay_the)
    for m in ds:
        m.khop_gan, m.cach_khop = 0.0, ''
        if m.nghi_gia.startswith('nghi đọc sai'):
            m.nghi_gia = ''
    _khop_tach_loai(ds, p)
    _khop_khoang_gia(ds, p)
    _khop_dong_chung(ds, p)
    _khop_dieu_khoan(ds, p)
    _khop_ten(ds, p)
    _khop_dac_trung(ds, p)
    _khop_cung_gia(ds, p)
    # giá bản scan đọc sai dạng ("S27.312") / đổi giá mà chỉ khác chữ số hay đọc nhầm, chênh quá xa: không chọn sẵn, người dùng xem lại
    for m in ds:
        if scan and not m.nghi_gia and m.trang_thai == 'cập nhật' and m.gia_cu and nham_chu_so(m.don_gia, m.gia_cu):
            m.nghi_gia = 'nghi đọc sai chữ số so với giá hiện hành'
        if m.nghi_gia and m.trang_thai != 'giữ nguyên':
            m.chon = False
    # mã cho mục mới (người dùng 30/10/2026: "tự tạo mã cây trồng theo văn bản mới") - số tiếp theo của bộ đơn giá, theo thứ tự văn
    # bản; ap_dung cấp đúng mã này (mã của mục bị bỏ không dùng lại: dự án cũ còn ghi mã đó)
    _cap_ma_moi(ds, nhom, lon_bo)
    if thay_the:
        _them_dong_bo(ds, p, scan)
    return ds


def _cap_ma_moi(ds: list, nhom: int | None, lon: dict) -> None:
    """Muc.ma_moi cho mục mới: số tiếp theo của bộ đơn giá (lon: {tiền tố: số lớn nhất}), theo thứ tự văn bản."""
    from .ma_tai_san import tien_to
    lon = dict(lon)
    for m in ds:
        m.ma_moi = ''
        if m.trang_thai == 'mới' and not m.ma and not m.bo_cu:
            n = nhom or m.nhom or 3
            tt = 'CS' if n == 4 else tien_to(3 if n == NHOM_VN else n, n == NHOM_VN)
            lon[tt] = lon.get(tt, 0) + 1
            m.ma_moi = f'{tt}{lon[tt]}'


KV_CA_HAI = '*'                     # 1.0.57: nhập mọi khu vực giá của văn bản vào bộ đơn giá (tách theo khu vực)


def so_khop_khu_vuc(ds: list, nhom: int | None = None, thay_the: bool = False, scan: bool = False) -> list:
    """1.0.57 (người dùng 04/11/2026: "thêm đủ 2 bộ phụ lục vào phần mềm … tách bạch để khi áp giá không bị chồng chéo"): văn bản nhiều
    khu vực giá -> so khớp TỪNG khu vực với các mục của khu vực đó trong bộ đơn giá (khu_vuc_gia KVMUC). Mục chưa gắn khu vực (bộ chưa
    tách) thuộc khu vực "gốc" = khu vực khớp bộ nhiều nhất (khu_vuc_khop_nhat) - bộ cũ một khu vực vẫn khớp đủ, khu vực kia thành mục
    mới. Mã mới cấp liên tiếp trên cả văn bản. Văn bản một khu vực: như so_khop."""
    kvs = [k for k, _ in cac_khu_vuc(ds)]
    if not kvs:
        return so_khop(ds, nhom, thay_the, scan)
    from . import khu_vuc_gia
    con = csdl.mo(don_gia.file_dang_dung(), chi_doc=True)
    try:
        kvd = khu_vuc_gia.doc(con)
        tat_ca = {r[0] for b in ('dm_taisan', 'dm_hotro') for r in con.execute(f'SELECT ma FROM {b}')}
    finally:
        con.close()
    for m in ds:
        if m.tach_tu and not m.phu:
            m.ten, m.tach_tu = m.tach_tu, ''
    goc = [m for m in ds if not m.bo_cu and not m.phu]
    chua_gan = tat_ca - set(kvd['muc'])
    kv_goc = khu_vuc_khop_nhat(goc, nhom) if chua_gan else ''
    kq = []
    for k in kvs:
        phan = [m for m in goc if m.khu_vuc == k or (not m.khu_vuc and k == (kv_goc or kvs[0]))]
        chi = {ma for ma, v in kvd['muc'].items() if v == k} | (chua_gan if k == kv_goc else set())
        so_khop(phan, nhom, thay_the, scan, chi_ma=chi)
        for m in phan:
            if (m.bo_cu or m.phu) and not m.khu_vuc:    # dòng "bỏ" (thay thế) / dòng phụ của dòng chung: khu vực đang so
                m.khu_vuc = k
        kq.extend(phan)
    ds[:] = kq
    con = csdl.mo(don_gia.file_dang_dung(), chi_doc=True)
    try:
        lon = _so_lon_nhat({0: [dict(ma=r[0]) for b in ('dm_taisan', 'dm_hotro') for r in con.execute(f'SELECT ma FROM {b}')]})
    finally:
        con.close()
    _cap_ma_moi(ds, nhom, lon)
    return ds


def _so_lon_nhat(hien: dict) -> dict:
    """{tiền tố mã: số lớn nhất đang dùng} (TS / CT / VN / CS) trong các dòng danh mục đã đọc."""
    lon = {}
    for ds_ in hien.values():
        for x in ds_:
            m = re.fullmatch(r'([A-Za-z]+)(\d+)', str(x['ma'] or '').strip())
            if m:
                k = m.group(1).upper()
                lon[k] = max(lon.get(k, 0), int(m.group(2)))
    return lon


def pham_vi_thay_the(ds: list, nhom: int | None = None) -> list:
    """Các nhóm danh mục văn bản thay thế (nhóm của các dòng đọc được từ văn bản, không tính dòng 'bỏ')."""
    return sorted({nhom or m.nhom or 3 for m in ds if not m.bo_cu})


def _phan_loai_dang_dung(con, vat_nuoi: bool, nhom: int) -> str:
    """Chuỗi phân loại bộ đơn giá đang dùng nhiều nhất cho nhóm (vật nuôi / không) - mục mới cùng phân loại với mục cũ, không tách
    thành nhóm lạ trên các thẻ / bảng in. Bộ chưa có dòng nào: mặc định."""
    from .nghiep_vu import la_vat_nuoi
    dem = {}
    for pl, n in con.execute('SELECT phan_loai, COUNT(*) FROM dm_taisan WHERE nhom = ? GROUP BY phan_loai', (nhom,)):
        if pl and bool(la_vat_nuoi(pl)) == vat_nuoi:
            dem[pl] = n
    if dem:
        return max(dem, key=dem.get)
    return don_gia.PHAN_LOAI_VAT_NUOI if vat_nuoi else PHAN_LOAI_MAC_DINH.get(nhom, '')


def _phan_loai(con, nm: int, ten: str, van_ban: dict | None) -> str:
    """Phân loại dòng mới của dm_taisan theo ĐÚNG chuỗi bộ đơn giá đang dùng (trước 15/10/2026 ghi "2. Nhà, công trình xây dựng" /
    "3. Cây trồng, vật nuôi" - lệch với phân loại của bộ). Nhóm 7 (vật nuôi) hoặc nhóm 3 mà tên / trích yếu văn bản chỉ nói vật
    nuôi, thủy sản -> phân loại vật nuôi (thẻ "Vật nuôi" của Bộ đơn giá)."""
    if nm == NHOM_VN:
        return _phan_loai_dang_dung(con, True, 3)
    if nm == 3:
        vb = bo_dau((van_ban or {}).get('trich_yeu', ''))
        if re.search(r'vat nuoi|thuy san|chan nuoi|chim yen', bo_dau(ten)) or \
                (re.search(r'vat nuoi|thuy san', vb) and not re.search(r'cay trong|hoa mau', vb)):
            return _phan_loai_dang_dung(con, True, 3)
    return _phan_loai_dang_dung(con, False, nm)


def _ma_cap(con, m, bang: str, tt: str, da_cap: dict, dung: set) -> str:
    """Mã của mục mới: mã đã hiện trên bảng (so_khop - Muc.ma_moi) khi còn trống, không thì số tiếp theo."""
    from .ma_tai_san import ma_tiep
    if m.ma_moi and m.ma_moi.upper().startswith(tt) and m.ma_moi not in dung:
        dung.add(m.ma_moi)
        so = int(m.ma_moi[len(tt):])
        da_cap[tt] = max(da_cap.get(tt, 0), so)
        return m.ma_moi
    while True:
        ma = ma_tiep(con, bang, tt, da_cap)
        if ma not in dung:
            dung.add(ma)
            return ma


TRANG_THAI_GHI = ('mới', 'cập nhật', 'đổi quy cách', 'bỏ')
CHU_TRANG_THAI = {'mới': 'mục mới', 'cập nhật': 'mục đổi giá', 'đổi quy cách': 'mục đổi tên / quy cách', 'bỏ': 'mục bỏ'}


def ap_dung(ds: list, nhom: int | None, nguon: str, phien_ban: str = '', van_ban: dict | None = None,
            van_ban_cu: list | tuple = (), quy_dinh: list | None = None, khu_vuc: dict | None = None) -> dict:
    """Tạo bộ đơn giá mới (bộ đang dùng + các mục được chọn) và cài. Trả thông tin bộ mới + số mục.
    nhom None / 0: mỗi dòng theo Muc.nhom. van_ban: kết quả phan_tich_van_ban (ghi vào danh mục văn bản căn cứ).
    van_ban_cu: id các dòng văn bản căn cứ bị văn bản này thay thế (chế độ thay thế) -> trạng thái "Hết hiệu lực - thay thế bởi …".
    quy_dinh: quy định cách tính trích từ văn bản (quy_dinh_van_ban.trich_quy_dinh) -> tham_so QDCT:… + ghi chú mục liên quan (1.0.56).
    khu_vuc (1.0.57, văn bản nhiều khu vực giá nhập cả hai - so_khop_khu_vuc): {'xa': {kv: [xã]}, 'ten': {kv: 'Phụ lục II'}} - mỗi mục
    khớp / thêm của dòng có Muc.khu_vuc được gắn khu vực đó (khu_vuc_gia: dự án chỉ dùng mục của khu vực xã dự án)."""
    from . import quan_tri_bo
    quan_tri_bo.kiem_quyen('cập nhật bộ đơn giá')      # 1.0.56: báo ngay, trước khi chép / ghi (cai_bo kiểm lại)
    chon = [m for m in ds if m.chon and m.trang_thai in TRANG_THAI_GHI]
    if not chon and not (van_ban and van_ban.get('so_hieu')) and not quy_dinh and not khu_vuc:
        raise LoiNhap('Không có mục nào mới, đổi giá, đổi quy cách hoặc bỏ để cập nhật.')
    # không có dòng giá nhưng có văn bản (văn bản chính sách): chỉ ghi vào danh mục văn bản căn cứ để theo dõi
    goc = don_gia.file_dang_dung()
    tt_cu = don_gia.thong_tin(goc)
    with tempfile.TemporaryDirectory() as td:
        moi = Path(td) / don_gia.TEN_FILE
        shutil.copyfile(goc, moi)
        con = csdl.mo(moi)
        try:
            pb = phien_ban or datetime.now().strftime('%Y.%m.%d.%H%M')
            if pb <= tt_cu['phien_ban']:
                pb = tt_cu['phien_ban'] + '.1'
            so = {k: 0 for k in TRANG_THAI_GHI}
            theo_nhom = {}
            with con, csdl.mo_khoa_danh_muc(con):
                # mã mục mới theo quy ước 0.9.69 (ma_tai_san): CS (hỗ trợ), TS (nhà), CT (cây), VN (vật nuôi) - số tiếp theo
                from .ma_tai_san import doi_ma, ma_tiep, tien_to
                from .nghiep_vu import la_vat_nuoi
                # số cuối từng tiền tố lấy TRƯỚC khi xóa dòng 'bỏ' - mã của mục bị bỏ không cấp lại cho mục khác
                da_cap = {tt: max(n - 1, 0) for tt, n in ((tt, int(ma_tiep(con, b, tt)[len(tt):])) for b, tt in
                          (('dm_hotro', 'CS'), ('dm_taisan', 'TS'), ('dm_taisan', 'CT'), ('dm_taisan', 'VN')))}
                dung = {r_[0] for b in ('dm_hotro', 'dm_taisan') for r_ in con.execute(f'SELECT ma FROM {b}')}
                ma_ghi = {}                             # id(Muc) -> mã đã thêm (gắn khu vực)
                for m in chon:
                    nm = nhom or m.nhom or 3
                    bang = 'dm_hotro' if nm == 4 else 'dm_taisan'
                    if m.trang_thai == 'bỏ':
                        con.execute(f'DELETE FROM {bang} WHERE ma = ?', (m.ma_khop,))
                    elif m.trang_thai in ('cập nhật', 'đổi quy cách'):
                        con.execute(f'UPDATE {bang} SET don_gia = ? WHERE ma = ?', (m.he_so or chuoi(m.don_gia), m.ma_khop))
                        if m.ten_thay:              # thay thế theo cách ghi của văn bản mới: tên, mật độ (mã giữ nguyên)
                            con.execute(f'UPDATE {bang} SET ten = ? WHERE ma = ?', (m.ten_thay, m.ma_khop))
                            if bang == 'dm_taisan':
                                con.execute('UPDATE dm_taisan SET ghi_chu = ? WHERE ma = ?', (m.ghi_chu_thay, m.ma_khop))
                    elif nm == 4:
                        ma = doi_ma(m.ma, 4) if m.ma else _ma_cap(con, m, 'dm_hotro', 'CS', da_cap, dung)
                        cc = ' '.join(x for x in (m.can_cu, (van_ban or {}).get('so_hieu', '')) if x) or nguon
                        con.execute('INSERT INTO dm_hotro (ma, ten, dvt, don_gia, can_cu, cach_tinh, trang_thai) VALUES (?,?,?,?,?,?,?)',
                                    (ma, m.ten, m.dvt, m.he_so or chuoi(m.don_gia), cc, m.ghi_chu, 'Cập nhật từ file'))
                        ma_ghi[id(m)] = ma
                    else:
                        nhom_db = 3 if nm == NHOM_VN else nm          # vật nuôi: nhom 3 + phân loại vật nuôi (CSDL không có nhom 7)
                        pl = _phan_loai(con, nm, m.ten, van_ban)
                        vn = nhom_db == 3 and la_vat_nuoi(pl)
                        ma = doi_ma(m.ma, nhom_db, vn) if m.ma else _ma_cap(con, m, 'dm_taisan', tien_to(nhom_db, vn), da_cap, dung)
                        con.execute('INSERT INTO dm_taisan (ma, nhom, phan_loai, ten, dvt, don_gia, ghi_chu) VALUES (?,?,?,?,?,?,?)',
                                    (ma, nhom_db, pl, m.ten, m.dvt, chuoi(m.don_gia),
                                     '; '.join(x for x in (m.ghi_chu, f'Cập nhật từ {nguon}') if x)))
                        ma_ghi[id(m)] = ma
                    so[m.trang_thai] += 1
                    theo_nhom.setdefault(nm, {k: 0 for k in TRANG_THAI_GHI})[m.trang_thai] += 1
                # mới / đổi giá luôn ghi (như trước); đổi quy cách / bỏ chỉ ghi khi có
                tom_tat = '; '.join(f'{NHOM[k]}: ' + ', '.join(f'{v[t]} {chu}' for t, chu in CHU_TRANG_THAI.items()
                                                               if v[t] or t in ('mới', 'cập nhật'))
                                    for k, v in sorted(theo_nhom.items())) or 'Văn bản chính sách: cần đối chiếu quy tắc tính'
                vb = van_ban or {}
                so_hieu = vb.get('so_hieu') and ' '.join(x for x in (vb.get('loai_vb', ''), vb['so_hieu'],
                                                                      f'ngày {vb["ngay"]}' if vb.get('ngay') else '') if x)
                trang_thai = f'Cập nhật {datetime.now():%d/%m/%Y}' + (f' từ {nguon}' if so_hieu else '')
                k = chuan_so_hieu(vb.get('so_hieu', ''))
                cu = next((r for r in con.execute('SELECT id, noi_dung, so_hieu FROM van_ban').fetchall()
                           if k and re.search(r'(?<!\d)' + re.escape(k), chuan_so_hieu(r[2]))), None)
                if cu is not None:                      # văn bản đã có tên trong danh sách: cập nhật dòng đó, không thêm dòng trùng
                    con.execute('UPDATE van_ban SET noi_dung = ?, trang_thai = ? WHERE id = ?',
                                (' | '.join(x for x in (cu[1], tom_tat) if x), trang_thai, cu[0]))
                else:
                    con.execute('INSERT INTO van_ban (so_hieu, co_quan, noi_dung, trang_thai) VALUES (?,?,?,?)',
                                (so_hieu or f'Cập nhật đơn giá từ {nguon}', vb.get('co_quan', ''),
                                 (vb.get('trich_yeu', '') + ' - ' if vb.get('trich_yeu') else '') + tom_tat, trang_thai))
                ten_moi = so_hieu or nguon
                for i in van_ban_cu:
                    if cu is None or i != cu[0]:
                        con.execute('UPDATE van_ban SET trang_thai = ? WHERE id = ?',
                                    (f'Hết hiệu lực - thay thế bởi {ten_moi} (cập nhật {datetime.now():%d/%m/%Y})', i))
                so_kv = 0
                if khu_vuc:                             # 1.0.57: khu vực giá của từng mục + danh sách xã / phường của mỗi khu vực
                    from . import khu_vuc_gia
                    muc_kv = {}
                    for m in ds:
                        if not m.khu_vuc or m.trang_thai == 'bỏ':
                            continue
                        ma = ma_ghi.get(id(m)) or (m.ma_khop if m.trang_thai != 'mới' else '')
                        if ma:
                            muc_kv[ma] = m.khu_vuc
                    so_kv = khu_vuc_gia.ghi(con, muc_kv, khu_vuc.get('xa'), khu_vuc.get('ten'), so_hieu or nguon)
                    if muc_kv:
                        csdl.ghi_nhat_ky(con, 'Gắn khu vực giá', f'{len(muc_kv)} mục theo {so_hieu or nguon}')
                kq_qd = {}
                if quy_dinh:                            # 1.0.56: quy định cách tính của văn bản (tham_so QDCT:…, ghi chú mục)
                    from .quy_dinh_van_ban import ghi_quy_dinh
                    kq_qd = ghi_quy_dinh(con, vb, quy_dinh, nguon)
                con.execute('UPDATE du_an SET phien_ban_gia = ?, nguon_nhap = ?, ngay_nhap = ? WHERE id = 1',
                            (pb, nguon, datetime.now().isoformat(timespec='seconds')))
        finally:
            con.close()
        tt = don_gia.cai_bo(moi)
    return dict(tt, so_moi=so['mới'], so_cap_nhat=so['cập nhật'], so_quy_cach=so['đổi quy cách'], so_bo=so['bỏ'],
                theo_nhom=theo_nhom, so_quy_dinh=kq_qd.get('so_quy_dinh', 0), so_muc_ghi_chu=kq_qd.get('so_muc_ghi_chu', 0),
                so_khu_vuc=so_kv)

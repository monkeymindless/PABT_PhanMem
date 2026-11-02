"""Trợ lý (phương án đột phá 9, người dùng 30/10/2026). Không Qt.

NGOẠI TUYẾN (mặc định, không cần mạng): giai_thich_ho - vì sao số tiền của một hộ khác quyết định phê duyệt / số liệu Excel / giữa các
lần lập phương án (theo từng hạng mục); nhap_to_trinh - bản nháp tờ trình từ số liệu dự án.
TRỰC TUYẾN (TÙY CHỌN, mặc định TẮT): hoi_claude gửi câu hỏi + số liệu tới Claude (Anthropic) qua thư viện chính thức `anthropic`
(nạp khi dùng - thư viện cần Python >= 3.10, không có ở bản Windows 7) để diễn giải, đọc văn bản dán vào, viết lại bản nháp.
Dữ liệu cá nhân (họ tên chủ hộ, CCCD, số điện thoại) được THAY bằng mã ("Hộ #12", "[CCCD]") trước khi gửi, trừ khi người dùng bật
"gửi dữ liệu cá nhân" (an_danh). Khóa API: biến môi trường ANTHROPIC_API_KEY / hồ sơ `ant auth login` (thư viện tự đọc), hoặc người
dùng tự nhập trong cửa sổ Trợ lý - lưu mã hóa bằng Windows DPAPI (chỉ tài khoản Windows đó giải được) ở <thư mục máy>\\tro_ly_ai.json."""
from __future__ import annotations

import base64
import json
import re
from dataclasses import dataclass, field

MO_HINH = ('claude-opus-5-5', 'claude-sonnet-5-5', 'claude-haiku-5-5')
MO_HINH_MAC_DINH = 'claude-opus-5-5'
DU_PHONG = 'claude-opus-4-8'                       # mô hình chạy thay khi bộ lọc an toàn từ chối (fallbacks phía máy chủ)
FILE_CAI_DAT = 'tro_ly_ai.json'
MUC = ((1, 'Đất'), (2, 'Nhà, công trình'), (3, 'Cây trồng'), (7, 'Vật nuôi'), (4, 'Hỗ trợ'), (5, 'Thưởng'))
COT_QD = ((1, 'tien_dat'), (2, 'tien_tai_san'), (3, 'tien_cay'), (4, 'tien_ho_tro'), (5, 'tien_thuong'))   # cây gồm cả vật nuôi
COT_EXCEL = ((1, 'dat'), (2, 'nha'), (3, 'cay'), (4, 'ho_tro'), (5, 'thuong'))
HE_THONG = ('Bạn là trợ lý nghiệp vụ bồi thường, hỗ trợ, tái định cư khi Nhà nước thu hồi đất ở Việt Nam, giúp cán bộ lập phương án. '
            'Trả lời bằng tiếng Việt, ngắn gọn, đúng số liệu được cung cấp; không bịa số, không suy đoán văn bản pháp luật không '
            'có trong câu hỏi - khi cần căn cứ chưa có thì nói rõ cần kiểm tra. Số tiền viết dạng 1.234.567 đồng.')


class LoiTroLy(Exception):
    pass


# ---------------------------------------------------------------- ngoại tuyến: giải thích số tiền của hộ
@dataclass
class GiaiThich:
    ma_ho: int
    ho_ten: str
    dong: list = field(default_factory=list)       # câu giải thích
    so_lieu: dict = field(default_factory=dict)    # số liệu (không dữ liệu cá nhân) - gửi kèm khi hỏi Claude

    @property
    def chu(self) -> str:
        return '\n'.join(self.dong)


def _d(x):
    from .tien import D
    try:
        return D(x) if x not in (None, '') else D(0)
    except (ArithmeticError, ValueError, TypeError):
        return D(0)


def _gop5(muc: dict) -> dict:
    """Hạng mục theo 5 cột (cây gồm vật nuôi) - như quyết định / bảng Excel."""
    return {1: _d(muc.get(1)), 2: _d(muc.get(2)), 3: _d(muc.get(3)) + _d(muc.get(7)), 4: _d(muc.get(4)), 5: _d(muc.get(5))}


def giai_thich_ho(con, ma_ho: int) -> GiaiThich:
    from . import lan_pa, theo_doi
    from .nghiep_vu import ket_qua_ho, tinh_lan
    from .tien import vn
    ten_muc5 = {1: 'Đất', 2: 'Nhà, công trình', 3: 'Cây trồng, vật nuôi', 4: 'Hỗ trợ', 5: 'Thưởng'}
    r = con.execute('SELECT ho_ten FROM ho WHERE ma_ho = ?', (ma_ho,)).fetchone()
    if r is None:
        raise LoiTroLy(f'Không có hộ mã {ma_ho}.')
    g = GiaiThich(ma_ho, r[0] or '')
    kq = ket_qua_ho(con).get(ma_ho)
    muc = dict(kq[0].muc) if kq else {}
    tong = kq[0].tong if kq else _d(0)
    g.so_lieu['phuong_an_hien_tai'] = dict({ten: str(_d(muc.get(m))) for m, ten in MUC}, tong=str(tong))
    g.dong.append(f'Phương án hiện tại (cộng mọi lần lập): {vn(tong)} đồng.')
    for m, ten in MUC:
        if _d(muc.get(m)):
            g.dong.append(f'  - {ten}: {vn(_d(muc.get(m)))}')
    # các lần lập phương án
    try:
        ds = lan_pa.ds_lan(con, ma_ho)
    except Exception:                               # noqa: BLE001 - file cũ chưa có pa_lan
        ds = []
    if len(ds) > 1:
        g.dong.append(f'Hộ có {len(ds)} lần lập phương án:')
        g.so_lieu['cac_lan'] = []
        for x in ds:
            try:
                t = tinh_lan(con, ma_ho, x.lan).tong
            except Exception:                       # noqa: BLE001
                continue
            g.dong.append(f'  - Lần {x.lan} ({x.nhan_trang_thai}): {vn(t)} đồng')
            g.so_lieu['cac_lan'].append({'lan': x.lan, 'trang_thai': x.nhan_trang_thai, 'tong': str(t)})
        chua = [x.lan for x in ds if not x.khoa]
        if chua:
            g.dong.append(f'  Lần chưa phê duyệt: {", ".join(map(str, chua))} - số tiền các lần này chưa có trong quyết định nào.')
    # quyết định phê duyệt
    qd = theo_doi.doc_qd_ho(con, ma_ho)
    if qd:
        tong_qd = sum((_d(x['so_tien']) for x in qd), _d(0))
        g.so_lieu['quyet_dinh'] = [{'so': x['so_qd'], 'ngay': x['ngay_qd'], 'so_tien': x['so_tien'], 'da_chi_tra': bool(x['da_chi_tra']),
                                    'chi_tra_so_tien': x['chi_tra_so_tien']} for x in qd]
        g.dong.append(f'Quyết định phê duyệt ({len(qd)}): tổng {vn(tong_qd)} đồng.')
        chenh = tong - tong_qd
        if chenh == 0:
            g.dong.append('  => Khớp: phương án hiện tại bằng tổng các quyết định.')
        else:
            g.dong.append(f'  => Phương án hiện tại {"CAO HƠN" if chenh > 0 else "THẤP HƠN"} quyết định {vn(abs(chenh))} đồng.')
            pa5 = _gop5(muc)
            co_chi_tiet = any(_d(x.get(c)) for x in qd for _m, c in COT_QD)
            if co_chi_tiet:
                for m, c in COT_QD:
                    q = sum((_d(x.get(c)) for x in qd), _d(0))
                    if pa5[m] != q:
                        g.dong.append(f'     · {ten_muc5[m]}: phương án {vn(pa5[m])} - quyết định {vn(q)} (chênh {vn(pa5[m] - q)})')
            else:
                g.dong.append('     · Quyết định chưa ghi tiền từng hạng mục - không chia được chênh lệch theo mục.')
            if len(ds) > 1 and any(not x.khoa for x in ds):
                g.dong.append('     · Nguyên nhân thường gặp: có lần lập bổ sung / điều chỉnh chưa được phê duyệt.')
            else:
                g.dong.append('     · Nguyên nhân thường gặp: phương án được sửa sau khi đã phê duyệt (đơn giá, số lượng, tỷ lệ), '
                              'hoặc số tiền quyết định nhập tay khác. Xem Nhật ký kiểm toán của hộ.')
        nhan = sum((_d(x['chi_tra_so_tien']) for x in qd if x['da_chi_tra']), _d(0))
        if nhan and nhan != tong_qd:
            g.dong.append(f'  Đã chi trả {vn(nhan)} / {vn(tong_qd)} đồng (còn {vn(tong_qd - nhan)}).')
    else:
        g.dong.append('Hộ chưa có quyết định phê duyệt.')
    # số liệu Excel nhập ban đầu
    try:
        ex = con.execute('SELECT * FROM tong_excel WHERE ma_ho = ?', (ma_ho,)).fetchone()
    except Exception:                               # noqa: BLE001
        ex = None
    if ex is not None and ex['tong'] not in (None, ''):
        tong_ex = _d(ex['tong'])
        g.so_lieu['excel_ban_dau'] = dict({c: ex[c] for _m, c in COT_EXCEL}, tong=ex['tong'])
        if tong_ex != tong:
            g.dong.append(f'So với file Excel nhập ban đầu ({vn(tong_ex)} đồng): chênh {vn(tong - tong_ex)} đồng.')
            pa5 = _gop5(muc)
            for m, c in COT_EXCEL:
                if pa5[m] != _d(ex[c]):
                    g.dong.append(f'  · {ten_muc5[m]}: phần mềm {vn(pa5[m])} - Excel {vn(_d(ex[c]))}')
        else:
            g.dong.append('Khớp số liệu file Excel nhập ban đầu.')
    if kq and kq[1]:
        g.dong.append('Cảnh báo khi kiểm tra phương án:')
        g.dong += [f'  - {c}' for c in kq[1][:10]]
    return g


# ---------------------------------------------------------------- ngoại tuyến: bản nháp tờ trình
def nhap_to_trinh(con) -> str:
    """Bản nháp nội dung tờ trình đề nghị thẩm định phương án từ số liệu dự án (chưa có số / ngày văn bản: để chấm)."""
    from .nghiep_vu import ket_qua_ho
    from .tien import tien_bang_chu, vn
    da = con.execute('SELECT * FROM du_an WHERE id = 1').fetchone()
    ten = (da['ten'] if da else '') or '…………'
    dia_ban = (da['ten_dia_ban'] if da and 'ten_dia_ban' in da.keys() else '') or '…………'
    kq = ket_qua_ho(con)
    tong_muc = {}
    for k, _cb in kq.values():
        for m, v in k.muc.items():
            tong_muc[m] = tong_muc.get(m, _d(0)) + _d(v)
    tong = sum(tong_muc.values(), _d(0))
    so_thua = con.execute('SELECT COUNT(*) FROM thua').fetchone()[0]
    dong = [f'Về việc đề nghị thẩm định phương án bồi thường, hỗ trợ, tái định cư dự án {ten}', '',
            f'Thực hiện dự án {ten} trên địa bàn {dia_ban}, đơn vị đã lập phương án bồi thường, hỗ trợ, tái định cư như sau:',
            f'1. Quy mô: {len(kq)} hộ gia đình, cá nhân, tổ chức; {so_thua} thửa đất bị thu hồi.',
            f'2. Tổng kinh phí bồi thường, hỗ trợ: {vn(tong)} đồng (Bằng chữ: {tien_bang_chu(tong, cham=True)}), trong đó:']
    for m, ten_m in MUC:
        if tong_muc.get(m):
            dong.append(f'   - {ten_m}: {vn(tong_muc[m])} đồng;')
    dong += ['3. Phương án đã được niêm yết công khai và lấy ý kiến theo quy định (ghi rõ thời gian, kết quả tiếp thu).',
             'Kính đề nghị ………… thẩm định để trình cấp có thẩm quyền phê duyệt.',
             '', '(Bản nháp tạo tự động từ số liệu dự án - kiểm tra, bổ sung căn cứ pháp lý và số, ngày văn bản trước khi ban hành.)']
    return '\n'.join(dong)


# ---------------------------------------------------------------- che dữ liệu cá nhân
_RE_CCCD = re.compile(r'(?<!\d)\d{9}(?:\d{3})?(?!\d)')
_RE_SDT = re.compile(r'(?<!\d)(?:\+84|0)\d{9,10}(?!\d)')
# 1.0.51: dạng có dấu cách / chấm / gạch. Số CCCD có dấu ngăn chỉ che khi đứng sau nhãn (CCCD, CMND, căn cước…) - "120.000.000" là
# số tiền, không phải CCCD; số điện thoại phải bắt đầu 0 / +84
_RE_CCCD_NHAN = re.compile(r'((?i:cccd|cmnd|căn cước|chứng minh|định danh)[^\d\n]{0,24})((?:\d[\s.\-]?){8,11}\d)(?!\d)')
_RE_SDT_NGAN = re.compile(r'(?<![\d.,])(?:\+84|0)\d{2,3}[\s.\-]\d{3}[\s.\-]\d{3,4}(?![\d])')
_RE_SO_GCN = re.compile(r'(?<![\w])[A-ZĐ]{2}[\s\-]?\d{6,8}(?![\w])')          # số phát hành giấy chứng nhận "CS 123456"
_RE_TOA_DO = re.compile(r'(?<![\d.])\d{1,3}\.\d{4,}\s*[,;]\s*\d{1,3}\.\d{4,}(?![\d])'
                        r'|(?<![\w])[XY]\s*[:=]\s*\d{6,7}(?:[.,]\d+)?(?![\d])')
_RE_SAU_NHAN_TEN = re.compile(r'((?i:hộ ông|hộ bà|chủ hộ|đồng sử dụng|người thừa kế|ông|bà)\s*[:\-]?\s*)((?:[^\W\d_]+\s*){1,5})')


def _che_ho_ten(m) -> str:
    """Sau "ông / bà / chủ hộ…": các từ viết HOA chữ đầu liền nhau (>= 2 từ) là họ tên -> [HO_TEN]; "bà con nhân dân" giữ nguyên."""
    du = m.group(2)
    n, cuoi = 0, 0
    for t in re.finditer(r'[^\W\d_]+', du):
        if not t.group(0)[:1].isupper():
            break
        n, cuoi = n + 1, t.end()
    if n < 2:
        return m.group(0)
    return m.group(1) + '[HO_TEN]' + du[cuoi:]


def an_danh(chu: str, con=None) -> str:
    """Thay họ tên chủ hộ có trong dự án (con) bằng "Hộ #<mã>", số CCCD / CMND bằng "[CCCD]", số điện thoại bằng "[SĐT]"."""
    s = str(chu or '')
    s = _RE_CCCD_NHAN.sub(lambda m: m.group(1) + '[CCCD]', s)
    s = _RE_SDT_NGAN.sub('[SĐT]', s)
    s = _RE_SDT.sub('[SĐT]', s)
    s = _RE_CCCD.sub('[CCCD]', s)
    s = _RE_SO_GCN.sub('[SO_GCN]', s)
    s = _RE_TOA_DO.sub('[TOA_DO]', s)
    s = _RE_SAU_NHAN_TEN.sub(_che_ho_ten, s)
    if con is not None:
        ten = sorted(((r[1].strip(), r[0]) for r in con.execute('SELECT ma_ho, ho_ten FROM ho') if r[1] and len(r[1].strip()) >= 4),
                     key=lambda x: -len(x[0]))
        for t, ma in ten:
            s = re.sub(re.escape(t), f'Hộ #{ma}', s, flags=re.I)
    return s


# ---------------------------------------------------------------- cài đặt: bật / tắt, khóa API (Windows DPAPI)
def _file_cai_dat():
    from .dia_phuong import thu_muc_may
    return thu_muc_may() / FILE_CAI_DAT


def doc_cai_dat() -> dict:
    """{'bat': bool, 'mo_hinh': str, 'gui_ca_nhan': bool, 'co_khoa': bool}."""
    try:
        d = json.loads(_file_cai_dat().read_text(encoding='utf-8'))
    except (OSError, ValueError):
        d = {}
    mh = d.get('mo_hinh') if d.get('mo_hinh') in MO_HINH else MO_HINH_MAC_DINH
    # 1.0.52 (người dùng 02/11/2026): LUÔN che dữ liệu cá nhân trước khi gửi - khóa gui_ca_nhan cũ trong file bỏ qua (luôn False)
    return dict(bat=bool(d.get('bat')), mo_hinh=mh, gui_ca_nhan=False, co_khoa=bool(d.get('khoa')))


def ghi_cai_dat(bat: bool | None = None, mo_hinh: str | None = None, gui_ca_nhan: bool | None = None, khoa: str | None = None,
                xoa_khoa: bool = False) -> dict:
    f = _file_cai_dat()
    try:
        d = json.loads(f.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        d = {}
    if bat is not None:
        d['bat'] = bool(bat)
    if mo_hinh is not None:
        if mo_hinh not in MO_HINH:
            raise LoiTroLy(f'Mô hình không hỗ trợ: {mo_hinh}')
        d['mo_hinh'] = mo_hinh
    d.pop('gui_ca_nhan', None)                          # 1.0.52: không còn cho gửi dữ liệu cá nhân (tham số giữ cho mã cũ)
    if khoa:
        d['khoa'] = base64.b64encode(bao_ve(khoa.strip().encode('utf-8'))).decode('ascii')
    if xoa_khoa:
        d.pop('khoa', None)
    f.parent.mkdir(parents=True, exist_ok=True)
    tam = f.with_name(f.name + '.tmp')
    tam.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding='utf-8')
    import os
    os.replace(tam, f)
    return doc_cai_dat()


def _khoa_da_luu() -> str | None:
    try:
        d = json.loads(_file_cai_dat().read_text(encoding='utf-8'))
        return mo_khoa(base64.b64decode(d['khoa'])).decode('utf-8') if d.get('khoa') else None
    except (OSError, ValueError, KeyError, LoiTroLy):
        return None


# 1.0.51: entropy riêng của phần mềm - chương trình khác chạy cùng tài khoản Windows không tự giải mã được khóa API. Khóa lưu trước
# 1.0.51 (không entropy) vẫn đọc được (mo_khoa thử lại không entropy)
ENTROPY_DPAPI = b'LARC_DPAPI_ENTROPY_2026'


def _dpapi(du: bytes, ma_hoa: bool, entropy: bytes | None = None) -> bytes:
    import ctypes
    import sys
    if sys.platform != 'win32':
        raise LoiTroLy('Lưu khóa API mã hóa chỉ có trên Windows - dùng biến môi trường ANTHROPIC_API_KEY.')
    from ctypes import wintypes

    class BLOB(ctypes.Structure):
        _fields_ = [('cbData', wintypes.DWORD), ('pbData', ctypes.POINTER(ctypes.c_char))]
    vao = BLOB(len(du), ctypes.cast(ctypes.create_string_buffer(du, len(du)), ctypes.POINTER(ctypes.c_char)))
    ra = BLOB()
    crypt = ctypes.windll.crypt32
    ham = crypt.CryptProtectData if ma_hoa else crypt.CryptUnprotectData
    them = None
    if entropy:
        them = BLOB(len(entropy), ctypes.cast(ctypes.create_string_buffer(entropy, len(entropy)), ctypes.POINTER(ctypes.c_char)))
    if not ham(ctypes.byref(vao), None, ctypes.byref(them) if them is not None else None, None, None, 0x1,
               ctypes.byref(ra)):                       # 0x1 = CRYPTPROTECT_UI_FORBIDDEN
        raise LoiTroLy('Không mã hóa / giải mã được khóa API (Windows DPAPI).')
    try:
        return ctypes.string_at(ra.pbData, ra.cbData)
    finally:
        ctypes.windll.kernel32.LocalFree(ra.pbData)


def bao_ve(du: bytes) -> bytes:
    return _dpapi(du, True, ENTROPY_DPAPI)


def mo_khoa(du: bytes) -> bytes:
    try:
        return _dpapi(du, False, ENTROPY_DPAPI)
    except LoiTroLy:
        return _dpapi(du, False)                        # khóa lưu bởi bản trước 1.0.51


def co_thu_vien() -> bool:
    try:
        import anthropic  # noqa: F401
        return True
    except ImportError:
        return False


# ---------------------------------------------------------------- trực tuyến: hỏi Claude (tùy chọn)
def hoi_claude(cau_hoi: str, ngu_canh: str = '', con=None, khach=None, gioi_han: float = 45) -> str:
    """Gửi câu hỏi (+ ngữ cảnh số liệu) tới Claude, trả lời bằng chữ. Chỉ chạy khi người dùng đã BẬT trợ lý trực tuyến. Che dữ liệu
    cá nhân (an_danh) - LUÔN (1.0.52, không còn tùy chọn gửi nguyên). khach: client giả lập cho kiểm thử. Lỗi -> LoiTroLy (tiếng Việt)."""
    cd = doc_cai_dat()
    if not cd['bat']:
        raise LoiTroLy('Trợ lý trực tuyến đang TẮT: bật ở thẻ "Cài đặt" của cửa sổ Trợ lý (mặc định chỉ chạy ngoại tuyến).')
    noi_dung = (f'Số liệu / văn bản:\n{ngu_canh}\n\n' if ngu_canh else '') + f'Yêu cầu: {cau_hoi}'
    noi_dung = an_danh(noi_dung, con)
    if khach is None:
        try:
            import anthropic
        except ImportError:
            raise LoiTroLy('Máy này chưa có thư viện "anthropic" (cần Python 3.10 trở lên - bản Windows 10/11): trợ lý chỉ chạy '
                           'ngoại tuyến.') from None
        khoa = _khoa_da_luu()
        giay = max(float(gioi_han or 45), 5)
        khach = anthropic.Anthropic(api_key=khoa, timeout=giay) if khoa else anthropic.Anthropic(timeout=giay)
        loi_api = (anthropic.AuthenticationError, anthropic.PermissionDeniedError, anthropic.RateLimitError,
                   anthropic.APIStatusError, anthropic.APIConnectionError)
    else:
        anthropic, loi_api = None, ()
    try:
        tl = khach.beta.messages.create(
            model=cd['mo_hinh'], max_tokens=16000, system=HE_THONG,
            output_config={'effort': 'medium'},
            betas=['server-side-fallback-2026-06-01'], fallbacks=[{'model': DU_PHONG}],
            messages=[{'role': 'user', 'content': noi_dung}])
    except loi_api as e:
        if anthropic is not None and isinstance(e, anthropic.AuthenticationError):
            raise LoiTroLy('Khóa API không hợp lệ: nhập lại ở thẻ Cài đặt (hoặc kiểm tra biến ANTHROPIC_API_KEY).') from None
        if anthropic is not None and isinstance(e, anthropic.PermissionDeniedError):
            raise LoiTroLy('Khóa API không có quyền dùng mô hình này.') from None
        if anthropic is not None and isinstance(e, anthropic.RateLimitError):
            raise LoiTroLy('Gửi quá nhiều yêu cầu: chờ một lát rồi thử lại.') from None
        if anthropic is not None and isinstance(e, anthropic.APIConnectionError):
            raise LoiTroLy('Không kết nối được máy chủ Anthropic (mất mạng / tường lửa).') from None
        raise LoiTroLy(f'Máy chủ Anthropic báo lỗi: {getattr(e, "message", e)}') from None
    if getattr(tl, 'stop_reason', None) == 'refusal':
        raise LoiTroLy('Mô hình từ chối trả lời yêu cầu này - diễn đạt lại câu hỏi.')
    chu = '\n'.join(b.text for b in tl.content if getattr(b, 'type', '') == 'text').strip()
    if not chu:
        raise LoiTroLy('Mô hình không trả lời (nội dung rỗng).')
    return chu

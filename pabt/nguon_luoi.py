"""Đọc MỌI loại file danh sách hộ / thửa thành LƯỚI ô (bảng chữ) để `nhap_tho` tự nhận cột (25/10/2026).

Nguồn đọc được: Excel (.xlsx, .xlsm, .xls - .xls đọc bằng Python thuần `doc_xls`, không cần Excel), CSV, Word (.docx, .doc), PDF có
lớp chữ (văn bản ký / chưa ký: chia cột theo vị trí chữ), PDF ảnh scan và file ảnh (nhận dạng chữ Tesseract đóng kèm: chia cột theo vị
trí từng từ). Mỗi sheet / bảng là một `Nguon` (lưới giá trị, ô gộp, loại nguồn). Không ghi gì vào dự án.
"""
from __future__ import annotations

import re
import shutil
import tempfile
import zipfile
from dataclasses import dataclass, field
from pathlib import Path

from .loi import LoiNhap

DUOI_EXCEL = ('.xlsx', '.xlsm', '.xls')
DUOI_ANH = ('.png', '.jpg', '.jpeg', '.bmp', '.tif', '.tiff')
DUOI_HO_TRO = DUOI_EXCEL + ('.csv', '.txt', '.dbf', '.docx', '.doc', '.pdf') + DUOI_ANH
LOC_MO_FILE = ('Danh sách hộ, thửa (*.xlsx *.xlsm *.xls *.csv *.txt *.dbf *.docx *.doc *.pdf *.png *.jpg *.jpeg *.tif *.tiff *.bmp);;'
               'File Excel (*.xlsx *.xlsm *.xls);;Bảng thuộc tính bản đồ địa chính (*.dbf *.csv *.txt);;'
               'PDF, ảnh scan (*.pdf *.png *.jpg *.jpeg *.tif *.tiff *.bmp);;Tất cả file (*.*)')
# byte đầu file dBASE (bảng thuộc tính shapefile của gCadas / ArcGIS / MapInfo / QGIS; Famis xuất DBF): III, IV, V, FoxPro, Visual FoxPro
_DAU_DBF = frozenset((0x02, 0x03, 0x04, 0x05, 0x30, 0x31, 0x32, 0x43, 0x63, 0x83, 0x8B, 0x8E, 0xCB, 0xF5, 0xFB))

TRONG_LIEN_TIEP = 100       # dừng đọc sau ngần này dòng trống liền nhau (sheet định dạng sẵn tới dòng 1.048.576)
DONG_TIM_COT = 40           # bề rộng bảng = cột có chữ cuối cùng trong ngần này dòng đầu (cột tiêu đề cuối)
TOI_DA_DONG = 200000        # không đọc quá ngần này dòng của một nguồn


@dataclass
class Nguon:
    ten: str                                   # tên sheet / "Văn bản PDF" / "Bản scan"
    luoi: list                                 # list[list] giá trị ô (None = trống)
    gop: dict = field(default_factory=dict)    # {(dòng, cột) 1-based: bề rộng ô gộp}
    rong: int = 0
    loai: str = 'excel'                        # excel | word | csv | pdf | scan
    ghi_chu: list = field(default_factory=list)

    @property
    def co_chu_in(self) -> bool:
        """Nguồn từ chữ in (PDF / bản scan): dòng gãy, tiêu đề nhận dạng gần đúng."""
        return self.loai in ('pdf', 'scan')


def _co_chu(v) -> bool:
    return v is not None and str(v).strip() != ''


def chuan_luoi(rows: list, vung_gop: list = ()) -> tuple:
    """Dòng thô (có thể dài ngắn khác nhau) + vùng gộp [(dòng1, cột1, dòng2, cột2)] 1-based -> (lưới, ô gộp, số cột). Bỏ phần trống cuối
    sheet và cột trống bên phải; ô gộp được điền giá trị ô đầu (tiêu đề gộp, họ tên gộp nhiều thửa)."""
    luoi = [list(r) for r in rows]
    while luoi and not any(_co_chu(v) for v in luoi[-1]):
        luoi.pop()
    cuoi = max((max((j for j, v in enumerate(r) if _co_chu(v)), default=-1) for r in luoi[:DONG_TIM_COT]), default=-1)
    rong = min(max((len(r) for r in luoi), default=0), cuoi + 1)
    luoi = [r[:rong] for r in luoi]
    for r in luoi:
        r.extend([None] * (rong - len(r)))
    gop = {}
    for r1, c1, r2, c2 in vung_gop:
        if r1 - 1 >= len(luoi):
            continue
        v = luoi[r1 - 1][c1 - 1] if c1 - 1 < rong else None
        for i in range(r1, min(r2, len(luoi)) + 1):
            for j in range(c1, min(c2, rong) + 1):
                luoi[i - 1][j - 1] = v
                gop[(i, j)] = c2 - c1 + 1
    return luoi, gop, rong


def _doc_hang_ws(ws) -> list:
    """Dòng giá trị của sheet openpyxl, dừng sau TRONG_LIEN_TIEP dòng trống liền nhau."""
    rows, trong = [], 0
    for r in ws.iter_rows(values_only=True):
        rows.append(list(r))
        if any(_co_chu(v) for v in r):
            trong = 0
        else:
            trong += 1
            if trong >= TRONG_LIEN_TIEP:
                break
        if len(rows) >= TOI_DA_DONG:
            break
    return rows


# ---------------------------------------------------------------- công thức chưa có giá trị đã lưu
_RE_THAM_CHIEU = re.compile(
    r"^=\s*(?:(TRIM|CLEAN|UPPER|LOWER|PROPER|VALUE|T|N)\(\s*)?(?:(?:'([^']+)'|([^'!\s()]+))!)?\$?([A-Za-z]{1,3})\$?(\d+)\s*\)?$")


def _cot_so(ten: str) -> int:
    n = 0
    for ch in ten.upper():
        n = n * 26 + ord(ch) - 64
    return n


def _giai_tham_chieu(cong_thuc, sheet: str, vals, fml, sau: int = 0):
    """'=TỔNG!B10', "='Tổng cộng'!$B$10", '=TRIM(B10)'… (tham chiếu ô đơn giản) -> giá trị ô được tham chiếu; không giải được: None."""
    m = _RE_THAM_CHIEU.match(str(cong_thuc).strip())
    if not m or sau > 8:
        return None
    ham, s1, s2, cot, dong = m.groups()
    ten = s1 or s2 or sheet
    if ten not in vals.sheetnames:
        return None
    r, c = int(dong), _cot_so(cot)
    v = vals[ten].cell(r, c).value
    if v is None:
        f = fml[ten].cell(r, c).value
        if isinstance(f, str) and f.startswith('='):
            v = _giai_tham_chieu(f, ten, vals, fml, sau + 1)
    if isinstance(v, str) and ham:
        v = {'TRIM': lambda x: ' '.join(x.split()), 'CLEAN': lambda x: x, 'UPPER': str.upper, 'LOWER': str.lower,
             'PROPER': str.title}.get(ham, lambda x: x)(v)
    return v


def _co_cong_thuc(p: Path) -> bool:
    try:
        with zipfile.ZipFile(p) as z:
            return any(b'<f' in z.read(t) for t in z.namelist() if t.startswith('xl/worksheets/') and t.endswith('.xml'))
    except (zipfile.BadZipFile, OSError, KeyError):
        return False


def _tu_xlsx(p: Path, thu_lai: bool = True) -> list:
    import openpyxl
    from . import an_toan
    try:
        an_toan.kiem_tra_zip(p)
    except an_toan.LoiAnToan as e:
        raise LoiNhap(str(e)) from None
    with open(p, 'rb') as f:                                    # mở bằng file: openpyxl từ chối đường dẫn sai đuôi
        wb = openpyxl.load_workbook(f, data_only=True)
    fml = None
    thieu = chua_giai = 0
    ds_hang = []
    try:
        if _co_cong_thuc(p):
            with open(p, 'rb') as f:
                fml = openpyxl.load_workbook(f, data_only=False)
        for ws in wb.worksheets:
            if ws.sheet_state != 'visible':
                continue
            rows = _doc_hang_ws(ws)
            if fml is not None and ws.title in fml.sheetnames:
                for r, hang in enumerate(fml[ws.title].iter_rows(max_row=len(rows), values_only=True)):
                    for c, f in enumerate(hang):
                        if isinstance(f, str) and f.startswith('=') and c < len(rows[r]) and rows[r][c] is None:
                            thieu += 1
                            v = _giai_tham_chieu(f, ws.title, wb, fml)
                            if v is None:
                                chua_giai += 1
                            else:
                                rows[r][c] = v
            ds_hang.append((ws.title, rows, [(m.min_row, m.min_col, m.max_row, m.max_col) for m in ws.merged_cells.ranges]))
    finally:
        wb.close()
        if fml is not None:
            fml.close()
    if chua_giai and thu_lai:                                   # công thức chưa tính (file tạo bằng mã / công cụ khác): nhờ Excel tính lại
        try:
            tam = Path(tempfile.mkdtemp(prefix='PABT_xl_'))
            try:
                from . import nhap_don_gia_doc
                moi = nhap_don_gia_doc.chuyen_office(p, '.xls', thu_muc=tam)
                return _tu_xlsx(moi, thu_lai=False)
            finally:
                shutil.rmtree(tam, ignore_errors=True)
        except LoiNhap:
            pass
    kq = []
    for ten, rows, gop in ds_hang:
        luoi, g, rong = chuan_luoi(rows, gop)
        if luoi:
            kq.append(Nguon(ten, luoi, g, rong, 'excel'))
    if chua_giai:
        for n in kq:
            n.ghi_chu.append(f'{chua_giai} / {thieu} ô công thức chưa có giá trị đã lưu (file tạo bằng công cụ khác chưa tính): '
                             'mở file bằng Excel, lưu lại (Ctrl+S) rồi nhập lại để lấy đủ dữ liệu.')
    return kq


def _tu_xls(p: Path) -> list:
    """File Excel 97-2003: đọc bằng Python thuần (doc_xls); lỗi thì nhờ Microsoft Excel chuyển sang .xlsx."""
    from . import doc_xls
    try:
        ds = doc_xls.doc(p)
    except doc_xls.LoiXls as e:
        tam = Path(tempfile.mkdtemp(prefix='PABT_xl_'))
        try:
            from . import nhap_don_gia_doc
            try:
                moi = nhap_don_gia_doc.chuyen_office(p, '.xls', thu_muc=tam)
            except LoiNhap as l:
                raise LoiNhap(f'Không đọc được file Excel cũ "{p.name}" ({e}). {l}') from None
            return _tu_xlsx(moi, thu_lai=False)
        finally:
            shutil.rmtree(tam, ignore_errors=True)
    kq = []
    for s in ds:
        if s['an']:
            continue
        luoi, g, rong = chuan_luoi(s['dong'][:TOI_DA_DONG], s['gop'])
        if luoi:
            kq.append(Nguon(s['ten'], luoi, g, rong, 'excel'))
    return kq


def _tu_bang_chu(p: Path, loai: str) -> list:
    """Word / CSV: các dòng bảng (nhap_don_gia.doc_bang) -> một lưới."""
    from . import nhap_don_gia
    rows = nhap_don_gia.doc_bang(p)
    luoi, g, rong = chuan_luoi([list(r) for r in rows][:TOI_DA_DONG])
    return [Nguon(p.stem, luoi, g, rong, loai)] if luoi else []


def _la_dbf(p: Path) -> bool:
    try:
        with open(p, 'rb') as f:
            dau = f.read(32)
    except OSError:
        return False
    return len(dau) == 32 and dau[0] in _DAU_DBF and int.from_bytes(dau[8:10], 'little') >= 33


def _o_dbf(kieu: str, raw: bytes, so_le: int, giai):
    """Một ô DBF -> giá trị lưới. Số: chuỗi kiểu Việt Nam (dấu phẩy thập phân - doc_so_vn đọc '1.070' là một nghìn không bảy mươi)."""
    if kieu in 'NF':
        s = raw.decode('ascii', errors='ignore').strip()
        if not s or s.strip('*') == '':
            return None
        try:
            from decimal import Decimal, InvalidOperation
            v = Decimal(s)
        except (InvalidOperation, ValueError):
            return s
        if v == v.to_integral_value():
            return int(v)
        return format(v.normalize(), 'f').replace('.', ',')
    if kieu == 'D':
        s = raw.decode('ascii', errors='ignore').strip()
        return f'{s[6:8]}/{s[4:6]}/{s[:4]}' if len(s) == 8 and s.isdigit() else (s or None)
    if kieu == 'L':
        s = raw.decode('ascii', errors='ignore').strip().upper()
        return {'T': 'Có', 'Y': 'Có', 'F': 'Không', 'N': 'Không'}.get(s)
    if kieu in 'CV':
        s = giai(raw.rstrip(b'\x00 ')).strip()
        return s or None
    return None                                         # memo / nhị phân: không có chữ cần nhập


def _tu_dbf(p: Path) -> list:
    """Bảng thuộc tính dBASE (.dbf, 1.0.98): dòng 1 = tên trường (SOTO, SHTHUA, DIENTICH, MDSD, TENCHU...), mỗi bản ghi chưa xóa một dòng.
    Chữ: UTF-8 nếu đúng UTF-8, không thì Latin-1 (mã TCVN3 / VNI để sua_cac_o đổi) - đoán trên CẢ bảng."""
    b = p.read_bytes()
    so_ban_ghi = int.from_bytes(b[4:8], 'little')
    dai_dau = int.from_bytes(b[8:10], 'little')
    dai_ban_ghi = int.from_bytes(b[10:12], 'little')
    truong, i = [], 32
    while i + 32 <= dai_dau and b[i] != 0x0D:
        ten = b[i:i + 11].split(b'\x00')[0].decode('latin-1').strip()
        truong.append((ten, chr(b[i + 11]), b[i + 16], b[i + 17]))
        i += 32
    if not truong or dai_ban_ghi <= 1:
        raise LoiNhap(f'File "{p.name}" không có bảng thuộc tính dBASE đọc được.')
    try:
        b[dai_dau:dai_dau + so_ban_ghi * dai_ban_ghi].decode('utf-8')
        giai = lambda x: x.decode('utf-8', errors='replace')            # noqa: E731
    except UnicodeDecodeError:
        giai = lambda x: x.decode('latin-1')                               # noqa: E731
    dong = [[t[0] for t in truong]]
    vt = dai_dau
    for _ in range(min(so_ban_ghi, TOI_DA_DONG)):
        ban_ghi = b[vt:vt + dai_ban_ghi]
        vt += dai_ban_ghi
        if len(ban_ghi) < dai_ban_ghi:
            break
        if ban_ghi[:1] == b'*':                          # bản ghi đã xóa
            continue
        hang, j = [], 1
        for _ten, kieu, dai, so_le in truong:
            hang.append(_o_dbf(kieu, ban_ghi[j:j + dai], so_le, giai))
            j += dai
        dong.append(hang)
    luoi, g, rong = chuan_luoi(dong)
    return [Nguon(p.stem, luoi, g, rong, 'csv')] if luoi else []


# ---------------------------------------------------------------- chia cột bảng từ vị trí chữ (PDF, bản scan)
_RE_DOAN = re.compile(r'\S+(?: \S+)*')                           # đoạn chữ: các từ cách nhau một dấu cách (2+ dấu cách = ô khác)


def _ranh_cot(chiem: list, so_hang: int, khe_toi_thieu: float, ti_le: float = 0.03) -> list:
    """Mảng đếm số hàng bảng có chữ phủ từng vị trí -> [(vị trí cắt, độ rộng khoảng trắng)] giữa các cụm chữ (khoảng trống liên tục >=
    khe_toi_thieu). thr: vài hàng tràn chữ qua khe (ô quá dài) không làm mất ranh cột; ti_le = 0: không dung sai (vị trí chính xác)."""
    thr = (max(1, int(ti_le * so_hang)) if so_hang >= 8 else 0) if ti_le else 0
    cat = []
    n = len(chiem)
    x = 0
    co_chu_truoc = False
    while x < n:
        if chiem[x] > thr:
            co_chu_truoc = True
            x += 1
            continue
        y = x
        while y < n and chiem[y] <= thr:
            y += 1
        if co_chu_truoc and y < n and y - x >= khe_toi_thieu:
            cat.append(((x + y) // 2, y - x))
        x = y
    return cat


def _chiem(khoang: list, rong: int) -> list:
    d = [0] * (rong + 2)
    for a, b in khoang:
        a, b = max(0, int(a)), min(rong, int(b))
        if b > a:
            d[a] += 1
            d[b] -= 1
    kq, s = [], 0
    for i in range(rong + 1):
        s += d[i]
        kq.append(s)
    return kq


def _cot_cua(cat: list, x: float) -> int:
    k = 0
    while k < len(cat) and x >= cat[k]:
        k += 1
    return k


def _cot_trung_nhieu(cat: list, x0: float, x1: float) -> int:
    """Cột có phần chồng với đoạn chữ [x0, x1) lớn nhất (đoạn chữ vắt qua ranh cột thì về cột chứa phần lớn chữ)."""
    moc = [float('-inf')] + list(cat) + [float('inf')]
    tot, k_tot = -1.0, 0
    for k in range(len(moc) - 1):
        ch = min(x1, moc[k + 1]) - max(x0, moc[k])
        if ch > tot:
            tot, k_tot = ch, k
    return k_tot


_RE_SO_CUM = re.compile(r'^\(?\d{1,2}\)?\.?$')                        # "(3)", "7": ô đánh số cột / số thứ tự


def _la_dong_so_lieu(doan: list) -> bool:
    """Hàng có số liệu (có cụm >= 2 chữ số liền nhau) và không phải hàng đánh số cột (1) (2) (3)…"""
    if all(_RE_SO_CUM.match(d[2].strip()) for d in doan):
        return False
    return any(re.search(r'\d\d', d[2]) for d in doan)


def _gom_cum(h: list, khoang: float) -> list:
    """Các từ [(x đầu, x cuối, chữ, ngắt)] của một hàng -> các cụm [(x đầu, x cuối, chữ)]: từ cách nhau <= khoang (và không bị nét kẻ ngăn)
    nối thành một cụm (chữ trong cùng một ô)."""
    kq = []
    for x0, x1, chu, ngat in h:
        if kq and khoang and not ngat and x0 - kq[-1][1] <= khoang:
            kq[-1] = (kq[-1][0], x1, kq[-1][2] + ' ' + chu)
        else:
            kq.append((x0, x1, chu))
    return kq


def _do_lech(v: list) -> float:
    """Độ lệch (cực đại - cực tiểu) của các vị trí, bỏ 10% ngoài cùng mỗi phía khi đủ nhiều (vài từ nhận dạng sai khung không làm hỏng)."""
    v = sorted(v)
    k = int(0.1 * len(v)) if len(v) >= 10 else 0
    v = v[k:len(v) - k] or v
    return v[-1] - v[0]


def _thang_hang(o: list, can_le: float) -> bool:
    """Chữ trong một cột có THẲNG HÀNG không: chữ đầu ô cùng một vị trí (căn trái), hoặc chữ cuối ô cùng vị trí (căn phải), hoặc cùng tâm
    (căn giữa) - sai lệch <= can_le. Ít hơn 3 ô: không đủ căn cứ (coi là không thẳng hàng)."""
    if len(o) < 3:
        return False
    return (_do_lech([x[0] for x in o]) <= can_le or _do_lech([x[1] for x in o]) <= can_le
            or _do_lech([(x[0] + x[1]) / 2 for x in o]) <= can_le)


def _hop_nhat_cot_thua(ranh: list, cac_hang: list, ds_than: list, can_le: float, khoang_cum: float = 0) -> list:
    """Bản scan: ranh cột cắt GIỮA một ô chữ dài (chữ ở phần đuôi cột: địa chỉ, nguồn gốc dài ngắn khác nhau; ô ghi chú thưa) bị bỏ. Hai dấu hiệu:
    (1) một cột bên ranh có chữ KHÔNG thẳng hàng (cột thật có chữ căn trái / phải / giữa; đoạn đuôi của ô chữ dài lệch theo độ dài các từ phía
    trước); (2) cột bên ranh thưa (< 55% hàng có chữ) mà ở hầu hết hàng có chữ cả hai phía, hai từ sát ranh cách nhau chỉ bằng khoảng cách giữa
    các từ cùng ô (< khoang_cum)."""
    ranh = list(ranh)
    n = len(ds_than)
    while ranh:
        cat = [r for r, _ in ranh]
        o = [[] for _ in range(len(cat) + 1)]                      # mỗi cột: [(chữ đầu ô, chữ cuối ô)] của từng hàng có chữ
        khe_hang = [[] for _ in cat]                               # mỗi ranh: khoảng cách hai từ sát ranh ở các hàng có chữ cả hai phía
        for k in ds_than:
            theo = {}
            h = sorted(cac_hang[k])
            for w in h:
                theo.setdefault(_cot_cua(cat, (w[0] + w[1]) / 2), []).append(w)
            for c, ws in theo.items():
                o[c].append((min(w[0] for w in ws), max(w[1] for w in ws)))
            for a, b in zip(h, h[1:]):
                ca, cb = _cot_cua(cat, (a[0] + a[1]) / 2), _cot_cua(cat, (b[0] + b[1]) / 2)
                if cb == ca + 1:
                    khe_hang[ca].append(b[0] - a[1])
        bo = None
        for i in range(len(cat)):
            if not (_thang_hang(o[i], can_le) and _thang_hang(o[i + 1], can_le)):
                bo = i
                break
            g = khe_hang[i]
            if (khoang_cum and g and min(len(o[i]), len(o[i + 1])) < 0.55 * n
                    and sum(1 for x in g if x < khoang_cum) >= 0.8 * len(g)):
                bo = i
                break
        if bo is None:
            break
        del ranh[bo]
    return ranh


def luoi_tu_doan(cac_hang: list, khe: float, ti_le: float = 0.03, khoang_cum: float = 0, can_le: float = 0) -> tuple:
    """Các hàng chữ [[(x đầu, x cuối, chữ[, ngắt])]] (từ hoặc ô chữ, mọi trang gộp chung vì cùng một bảng) -> (lưới, số cột).
    Cột = các khoảng trắng dọc chung (rộng >= khe) của các hàng SỐ LIỆU (thân bảng: đều đặn hơn tiêu đề căn giữa, ô ghi chú thưa).
    Hàng số liệu: từng từ xếp vào cột chứa tâm từ; các hàng khác (tiêu đề, dòng gãy): từng CỤM chữ (từ cách nhau <= khoang_cum) xếp vào cột
    chứa phần lớn cụm - không cắt giữa cụm. can_le > 0 (bản scan): bỏ ranh cột cắt giữa ô chữ dài (_hop_nhat_cot_thua)."""
    cac_hang = [[(w + (False,))[:4] for w in h] for h in cac_hang if h]
    if not cac_hang:
        return [], 0
    cum = [_gom_cum(h, khoang_cum) for h in cac_hang]
    ds_than = [k for k, c in enumerate(cum) if len(c) >= 3 and _la_dong_so_lieu(c)]
    if len(ds_than) < 2:
        ds_than = [k for k, c in enumerate(cum) if len(c) >= 3]
    if len(ds_than) < 2:
        ds_than = [k for k, c in enumerate(cum) if len(c) >= 2]
    cat = []
    if len(ds_than) >= 2:
        rong = int(max(w[1] for h in cac_hang for w in h)) + 2
        ranh = _ranh_cot(_chiem([(w[0], w[1]) for k in ds_than for w in cac_hang[k]], rong), len(ds_than), khe, ti_le)
        if can_le:
            ranh = _hop_nhat_cot_thua(ranh, cac_hang, ds_than, can_le, khoang_cum)
        cat = [r[0] for r in ranh]
    than = set(ds_than)
    n_cot = len(cat) + 1
    luoi = []
    for k, h in enumerate(cac_hang):
        r = [None] * n_cot
        if k in than:
            for x0, x1, chu, _ in h:
                j = _cot_cua(cat, (x0 + x1) / 2)
                r[j] = (r[j] + ' ' + chu) if r[j] else chu
        else:
            for x0, x1, chu in cum[k]:
                j = _cot_trung_nhieu(cat, x0, x1)
                r[j] = (r[j] + ' ' + chu) if r[j] else chu
        luoi.append(r)
    return luoi, n_cot


def luoi_tu_layout(dong: list) -> tuple:
    """Dòng chữ giữ bố cục (pypdf layout) -> (lưới, số cột); xem luoi_tu_doan. Chữ trong ô cách nhau 1 dấu cách; ô cách nhau >= 2 dấu cách."""
    ds = [d.expandtabs(4).rstrip() for d in dong if d.strip()]
    hang = [[(m.start(), m.end(), m.group(0)) for m in _RE_DOAN.finditer(d)] for d in ds]
    return luoi_tu_doan(hang, 2)


_RE_KHUNG = re.compile(r'[|¦│┃]')
_RE_RAC = re.compile(r"^[|¦│┃_\-=—–.~^`'\"°*:;,]+$")
_RE_SO_DINH_KHUNG = re.compile(r'^(\d[\d.,]*)[JIl!](?=[A-ZĐ])')            # "50JONT+CLN": nét kẻ dọc của khung bảng đọc thành chữ J / I / l


def _tu_ocr_sach(h: list) -> list:
    """Hàng từ của bản scan [(x, x cuối, cao, chữ)] -> [(x, x cuối, chữ, ngắt)]: nét kẻ dọc của khung bảng (Tesseract đọc thành "|", dính
    vào từ bên cạnh hoặc thành chữ J / I / l) tách khỏi chữ và đánh dấu ngắt ô (ngắt: từ này là đầu một ô mới)."""
    kq = []
    ngat = False
    for x0, x1, cao, chu in h:
        chu = chu.strip()
        if _RE_RAC.match(chu):
            ngat = ngat or bool(_RE_KHUNG.search(chu))
            continue
        phan = []                                                # [(chữ, ngắt trước)]
        if _RE_KHUNG.search(chu):
            ds = _RE_KHUNG.split(chu)
            for k, d in enumerate(ds):
                if d:
                    phan.append((d, k > 0 or ngat))
                    ngat = False
                elif k > 0 or chu.startswith(tuple('|¦│┃')):
                    ngat = True
            if chu[-1] in '|¦│┃':
                ngat = True
        else:
            m = _RE_SO_DINH_KHUNG.match(chu)
            if m:
                phan = [(m.group(1), ngat), (chu[m.end():], True)]
            else:
                phan = [(chu, ngat)]
            ngat = False
        tong = sum(len(d) + 1 for d, _ in phan) or 1
        x = float(x0)
        for d, nb in phan:
            w = (x1 - x0) * (len(d) + 1) / tong
            kq.append((x, x + w - (x1 - x0) / tong, d, nb))
            x += w
    return kq


def luoi_tu_hang(cac_hang: list) -> tuple:
    """Các hàng từ của bản scan [[(x, x cuối, cao, chữ)]] (mọi trang gộp chung vì cùng một bảng) -> (lưới, số cột). Khe cột >= 0,25 x chiều
    cao chữ trung vị (ranh cắt giữa ô chữ dài ở cột thưa: bỏ); cụm chữ = từ cách nhau <= 1,25 x chiều cao chữ."""
    cao = sorted(w[2] for h in cac_hang for w in h)
    if not cao:
        return [], 0
    cao_tv = cao[len(cao) // 2] or 10
    hang = [h for h in (_tu_ocr_sach(h) for h in cac_hang if h) if h]
    if not hang:
        return [], 0
    return luoi_tu_doan(hang, max(4, int(0.25 * cao_tv)), 0.03, 1.25 * cao_tv, 0.35 * cao_tv)


def _ky_tu_trang(d, i: int) -> list:
    """[(ký tự, x trái, y trên)] của từng ký tự trong trang PDF (QtPdf) - cho ô một ký tự mà chọn theo vùng không ra chữ."""
    kq = []
    for k in range(len(d.getAllText(i).text())):
        sel = d.getSelectionAtIndex(i, k, 1)
        bd = sel.bounds()
        if bd and sel.text().strip():
            r = bd[0].boundingRect()
            kq.append((sel.text().strip(), r.left(), r.top()))
    return kq


def _hang_tu_qtpdf(p: Path, bao_tien_do=None, cho=None):
    """PDF có lớp chữ -> (các hàng ô [(x đầu, x cuối, chữ)] của mọi trang, chiều cao chữ trung vị) theo VỊ TRÍ THẬT của từng ô chữ (QtPdf).
    None: không có QtPdf (bản Qt 5). Mỗi ô chữ (đối tượng chữ của PDF) là một đoạn; ~1 giây / trang."""
    try:
        from PySide6.QtCore import QCoreApplication, QPointF
        from PySide6.QtPdf import QPdfDocument
    except ImportError:
        return None
    from . import ocr
    QCoreApplication.instance() or QCoreApplication([])
    d = QPdfDocument()
    loi = d.load(str(p))
    if loi == QPdfDocument.Error.IncorrectPassword:
        raise LoiNhap(f'PDF "{p.name}" có mật khẩu: mở bằng trình đọc PDF, in / lưu lại bản không mật khẩu rồi chọn lại.')
    if loi != QPdfDocument.Error.None_ or d.pageCount() == 0:
        raise LoiNhap(f'Không đọc được PDF "{p.name}" (file hỏng hoặc chưa tải xong).')
    hang, cao = [], []
    try:
        tong = d.pageCount()
        for i in range(min(tong, 400)):
            if cho and cho():
                raise ocr.DaHuy()
            if bao_tien_do:
                bao_tien_do(i + 1, tong)
            o, ky_tu = [], None
            for poly in d.getAllText(i).bounds():
                r = poly.boundingRect()
                y = r.center().y()
                t = d.getSelection(i, QPointF(r.left() + 0.4, y), QPointF(r.right() - 0.4, y)).text().strip()
                if not t:                                      # ô một ký tự (số thứ tự "1", thửa "7"): chọn rộng dần ra hai bên
                    for fy in (0.5, 0.8, 0.3):
                        yy = r.top() + fy * r.height()
                        t = d.getSelection(i, QPointF(r.left() - 2, yy), QPointF(r.right() + 2, yy)).text().strip()
                        if t:
                            break
                    if len(t) > 3:
                        t = t[:1] if r.width() < 4 else t[:2]
                    if not t:                                  # vẫn không chọn được: tra theo từng ký tự của trang (chỉ dựng khi cần)
                        if ky_tu is None:
                            ky_tu = _ky_tu_trang(d, i)
                        t = ''.join(c for c, x, yk in ky_tu if r.left() - 0.8 <= x <= r.right() and r.top() - 0.8 <= yk <= r.bottom()).strip()
                if t:
                    o.append((r.left(), r.right(), y, r.height(), ' '.join(t.split())))
                    cao.append(r.height())
            o.sort(key=lambda a: (a[2], a[0]))
            dong = []                                         # [[tâm y, cao, [(x đầu, x cuối, chữ)]]]
            for x0, x1, y, h, t in o:
                for dg in dong[-2:]:
                    if abs(y - dg[0]) < 0.5 * max(h, dg[1]):
                        dg[2].append((x0, x1, t))
                        break
                else:
                    dong.append([y, h, [(x0, x1, t)]])
            hang += [sorted(dg[2]) for dg in dong]
    finally:
        d.close()
    cao.sort()
    return hang, (cao[len(cao) // 2] if cao else 10.0)


def _tu_pdf_chu(p: Path, bao_tien_do=None, cho=None) -> list:
    kq = _hang_tu_qtpdf(p, bao_tien_do, cho)
    if kq is not None:
        hang, cao = kq
        if sum(len(t) for h in hang for _, _, t in h) < 40:
            return []
        luoi, rong = luoi_tu_doan(hang, max(1.5, 0.3 * cao), 0)
    else:                                                       # Qt 5 (bản Win 7): không có QtPdf - chia cột theo ký tự (kém chính xác hơn)
        from . import pdf_bang
        dong = pdf_bang.dong_layout(p)
        if sum(len(d.strip()) for d in dong) < 40:
            return []
        luoi, rong = luoi_tu_layout(dong)
    return [Nguon('Văn bản PDF', luoi, {}, rong, 'pdf')] if luoi else []


def _tu_scan(p: Path, bao_tien_do=None, cho=None, psm: int = 4) -> list:
    from . import ocr
    thieu = ocr.san_sang()
    if thieu:
        raise LoiNhap(f'{thieu}')
    hang = []
    try:
        for trang in ocr.tung_trang(p, bao_tien_do, cho, tra_ve='hang', psm=psm):
            hang += trang
    except ocr.DaHuy:
        raise
    except ocr.LoiOCR as e:
        raise LoiNhap(f'Nhận dạng chữ không được: {e}') from None
    luoi, rong = luoi_tu_hang(hang)
    if not luoi:
        return []
    from .ocr import sua_so
    luoi = [[sua_so(v) if isinstance(v, str) else v for v in r] for r in luoi]
    n = Nguon('Bản scan', luoi, {}, rong, 'scan')
    n.ghi_chu.append('Dữ liệu nhận dạng từ ảnh / bản scan: đối chiếu lại họ tên, số tờ, số thửa, diện tích với bản gốc (tô vàng các '
                     'dòng thiếu thông tin).')
    return [n]


# ---------------------------------------------------------------- điểm vào
def loai_file(p: Path) -> str:
    """'xlsx' | 'xls' | 'csv' | 'docx' | 'doc' | 'pdf' | 'anh' theo nội dung (không tin đuôi file); lỗi tiếng Việt nếu không hỗ trợ."""
    from . import nhap_don_gia
    duoi = p.suffix.lower()
    if not p.exists():
        raise LoiNhap(f'Không thấy file {p}.')
    if duoi in DUOI_ANH:
        return 'anh'
    if duoi == '.dbf':
        if _la_dbf(p):
            return 'dbf'
        raise LoiNhap(f'File "{p.name}" bị hỏng hoặc không phải bảng dBASE (.dbf).')
    that = nhap_don_gia.loai_that(p)
    if that == '.html':
        raise LoiNhap(f'File "{p.name}" thực chất là một trang web (HTML), không phải file {duoi}: tải lại file gốc.')
    if that in ('.xlsx', '.xls', '.docx', '.doc', '.pdf'):
        return that[1:]
    if duoi in ('.csv', '.txt'):
        return 'csv'
    if duoi in DUOI_HO_TRO:
        raise LoiNhap(f'File "{p.name}" bị hỏng hoặc chưa tải xong (nội dung không phải {duoi}).')
    raise LoiNhap(f'Chưa hỗ trợ file {duoi or "(không có đuôi)"}. Hỗ trợ: Excel (.xlsx, .xls), Word, PDF (có chữ hoặc bản scan), '
                  'ảnh (.jpg, .png, .tif), CSV / TXT, bảng thuộc tính bản đồ .dbf.')


_TEN_MA_CU = {'tcvn3': 'TCVN3 (.VnTime)', 'vni': 'VNI (VNI-Times)'}


def _sua_ma_cu(ds: list) -> list:
    """1.0.98: chữ phông cũ TCVN3 / VNI trong ô (danh sách xuất từ phần mềm địa chính cũ) -> Unicode, ghi chú cho người dùng kiểm."""
    from .chuan_chu import sua_cac_o
    for n in ds:
        n.luoi, lp = sua_cac_o(n.luoi)
        if lp:
            n.ghi_chu.append(f'Chữ phông {_TEN_MA_CU[lp]} đã đổi sang Unicode: xem lại họ tên, địa chỉ trước khi nhập.')
    return ds


def lay_nguon(file, bao_tien_do=None, cho=None, scan: bool = False, psm: int = 4) -> list:
    """Các nguồn dữ liệu (sheet / bảng) của file. scan=True: PDF / ảnh phải nhận dạng chữ (PDF có chữ thì mặc định đọc lớp chữ trước).
    bao_tien_do(trang, tổng), cho() -> True để hủy (chỉ khi nhận dạng chữ)."""
    p = Path(file)
    loai = loai_file(p)
    if loai == 'xlsx':
        return _sua_ma_cu(_tu_xlsx(p))
    if loai == 'xls':
        return _sua_ma_cu(_tu_xls(p))
    if loai == 'dbf':
        return _sua_ma_cu(_tu_dbf(p))
    if loai in ('docx', 'doc', 'csv'):
        return _sua_ma_cu(_tu_bang_chu(p, 'csv' if loai == 'csv' else 'word'))
    if loai == 'pdf' and not scan:
        ds = _tu_pdf_chu(p, bao_tien_do, cho)
        if ds:
            return ds
    return _tu_scan(p, bao_tien_do, cho, psm)


def la_ban_scan(file) -> bool:
    """File ảnh / PDF không có lớp chữ (phải nhận dạng chữ)."""
    try:
        loai = loai_file(Path(file))
    except LoiNhap:
        return False
    if loai == 'anh':
        return True
    return loai == 'pdf' and not _tu_pdf_chu(Path(file))

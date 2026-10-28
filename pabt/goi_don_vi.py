"""Tạo gói cấu hình (.pabtcfg) HÀNG LOẠT cho nhiều đơn vị (người dùng 28/10/2026): bộ cài phát hành không có tên cơ quan; người
quản trị điền một file Excel (mỗi dòng một chi nhánh / đơn vị) hoặc file .json, phần mềm dựng mỗi đơn vị một gói .pabtcfg - máy
của đơn vị bấm đúp gói là có đủ tên cơ quan, đơn vị lập, người ký… KHÔNG đổi cấu hình của máy tạo gói (trước đây phải sửa Cấu hình
nghiệp vụ của máy mình, xuất gói rồi khôi phục).

Hồ sơ của một đơn vị = hồ sơ NỀN + thông tin đơn vị của dòng. Nền: 'may' (cấu hình nghiệp vụ của máy này - căn cứ pháp lý, mốc thời
hạn, kinh phí cùng tỉnh), 'mac_dinh' (hồ sơ trung tính đóng kèm) hoặc đường dẫn file hồ sơ .json (tỉnh khác). Thông tin cơ quan của
nền luôn XÓA trước khi ghi dòng: ô để trống không mang tên đơn vị của máy tạo gói sang đơn vị khác.

File .json nhận: (1) hồ sơ địa phương (loai = pabt_profile, đầy đủ hoặc một phần) = một đơn vị, trộn lên nền; (2) danh sách đơn vị
[{khóa: giá trị}] hoặc {"don_vi": [...]} cùng khóa với cột Excel (COT). Không Qt (màn hình ở man_hinh_goi_don_vi.py)."""
from __future__ import annotations
import copy
import json
import re
from pathlib import Path

from . import dia_phuong, goi_mau

# (khóa, tiêu đề cột Excel, nơi ghi trong hồ sơ, bắt buộc, giải thích) - nơi ghi: 'co_quan' / 'ban_in_mac_dinh' / 'ho_so' / 'dia_danh'
COT = (
    ('ten', 'Tên tổ chức làm nhiệm vụ bồi thường', 'co_quan', True,
     'Tên đầy đủ, chữ in hoa như trên băng tiêu đề. Ví dụ: TRUNG TÂM PHÁT TRIỂN QUỸ ĐẤT CHI NHÁNH …'),
    ('truc_thuoc', 'Trực thuộc', 'co_quan', False, 'Cơ quan cấp trên trực tiếp (dòng phụ băng tiêu đề).'),
    ('dia_chi', 'Địa chỉ', 'co_quan', False, 'Địa chỉ trụ sở đơn vị.'),
    ('vai_tro', 'Vai trò', 'co_quan', False, 'Để trống: TỔ CHỨC LÀM NHIỆM VỤ BỒI THƯỜNG (theo hồ sơ nền).'),
    ('don_vi_cap_tren', 'Đơn vị cấp trên (dòng 1 tiêu đề bản in)', 'ban_in_mac_dinh', False,
     'Dòng cơ quan chủ quản trên góc trái bản in. Ví dụ: Trung tâm Phát triển quỹ đất tỉnh …'),
    ('don_vi_tieu_de', 'Tên đơn vị trên tiêu đề bản in (dòng 2)', 'ban_in_mac_dinh', False,
     'Dòng in đậm, gạch chân dưới dòng cấp trên. Ví dụ: Chi nhánh …'),
    ('don_vi_lap', 'Đơn vị lập phương án', 'ban_in_mac_dinh', False,
     'Tên đơn vị ở phần chữ ký, tờ trình. Để trống: lấy Tên tổ chức.'),
    ('dia_danh', 'Địa danh dòng ngày tháng', 'dia_danh', False,
     'Nơi đơn vị đóng trụ sở, in đầu dòng "…, ngày … tháng … năm …".'),
    ('ky_hieu_so', 'Ký hiệu số phương án', 'ban_in_mac_dinh', False, 'Ví dụ: PA-TTPTQĐ.CN… (in sau "Số: …/").'),
    ('chuc_vu_ky', 'Chức vụ người ký', 'ban_in_mac_dinh', False, 'Ví dụ: Giám đốc / Phó Giám đốc (Phó… thì in "KT. GIÁM ĐỐC").'),
    ('nguoi_ky', 'Họ tên người ký', 'ban_in_mac_dinh', False, ''),
    ('nguoi_lap', 'Họ tên người lập', 'ban_in_mac_dinh', False, ''),
    ('nguoi_kiem_tra', 'Họ tên người kiểm tra', 'ban_in_mac_dinh', False, ''),
    ('ten_ho_so', 'Tên hồ sơ (để phân biệt các gói)', 'ho_so', False, 'Để trống: lấy Tên tổ chức.'),
    ('ten_file', 'Tên file gói', 'ho_so', False, 'Để trống: tự đặt theo tên đơn vị (LARC_CauHinh_<tên>.pabtcfg).'),
)
KHOA_COT = tuple(c[0] for c in COT)
BAT_BUOC = tuple(c[0] for c in COT if c[3])
TEN_SHEET = 'Don_vi'
TEN_SHEET_HD = 'Huong_dan'
NEN_MAY = 'may'
NEN_MAC_DINH = 'mac_dinh'
TIEN_TO_FILE = 'LARC_CauHinh_'
DONG_TOI_DA = 500                                   # một file danh sách (chặn file nhầm hàng chục nghìn dòng)


class LoiDonVi(ValueError):
    """File danh sách đơn vị / hồ sơ nền không đọc được (thông báo tiếng Việt)."""


# ---------------------------------------------------------------- file Excel mẫu
def tao_file_mau(p) -> Path:
    """Ghi file Excel mẫu: sheet Don_vi (dòng tiêu đề, cột bắt buộc có *) + sheet Huong_dan (giải thích từng cột). Không có dòng
    ví dụ trong Don_vi (dòng ví dụ quên xóa sẽ thành một gói)."""
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill
    from .an_toan import luu_xlsx
    p = Path(p)
    if p.suffix.lower() != '.xlsx':
        p = p.with_name(p.name + '.xlsx')
    wb = Workbook()
    ws = wb.active
    ws.title = TEN_SHEET
    nen = PatternFill('solid', fgColor='2F5F9E')
    for j, (k, td, _noi, bb, _gt) in enumerate(COT, 1):
        o = ws.cell(1, j, td + (' *' if bb else ''))
        o.font = Font(bold=True, color='FFFFFF')
        o.fill = nen
        o.alignment = Alignment(wrap_text=True, vertical='center', horizontal='center')
        ws.column_dimensions[o.column_letter].width = 42 if k in ('ten', 'dia_chi', 'truc_thuoc', 'don_vi_cap_tren', 'don_vi_lap') else 26
    ws.row_dimensions[1].height = 45
    ws.freeze_panes = 'A2'
    hd = wb.create_sheet(TEN_SHEET_HD)
    dong = [('Cột', 'Bắt buộc', 'Giải thích'),
            ('', '', 'Mỗi dòng của sheet Don_vi là MỘT đơn vị -> một gói .pabtcfg. Dòng trống bỏ qua. Không đổi chữ dòng tiêu đề.'),
            ('', '', 'Căn cứ pháp lý, mốc thời hạn, tỷ lệ kinh phí lấy theo hồ sơ nền chọn lúc tạo gói (máy này / mặc định / '
                     'file hồ sơ .json của tỉnh).')]
    dong += [(td, 'Có' if bb else '', gt) for _k, td, _noi, bb, gt in COT]
    for i, d in enumerate(dong, 1):
        for j, v in enumerate(d, 1):
            o = hd.cell(i, j, v)
            o.alignment = Alignment(wrap_text=True, vertical='top')
            if i == 1:
                o.font = Font(bold=True)
    hd.column_dimensions['A'].width = 40
    hd.column_dimensions['B'].width = 10
    hd.column_dimensions['C'].width = 90
    p.parent.mkdir(parents=True, exist_ok=True)
    luu_xlsx(wb, p)
    return p


# ---------------------------------------------------------------- đọc danh sách
def _chuan(s) -> str:
    from .lap_pa import bo_dau
    return ' '.join(re.sub(r'[^0-9a-z]+', ' ', bo_dau(str(s or '')).lower()).split())


_THEO_TIEU_DE = {}
for _k, _td, *_ in COT:
    _THEO_TIEU_DE[_chuan(_td)] = _k
    _THEO_TIEU_DE[_chuan(_k)] = _k


def _chu(v) -> str:
    if v is None:
        return ''
    if isinstance(v, float) and v.is_integer():
        v = int(v)
    return ' '.join(str(v).split())


def _doc_excel(p: Path) -> list:
    """[(số dòng, {khóa: chữ})] từ sheet Don_vi (không có thì sheet đầu). Dòng tiêu đề = dòng đầu có cột Tên tổ chức."""
    from openpyxl import load_workbook
    try:
        wb = load_workbook(p, read_only=True, data_only=True)
    except Exception as e:
        raise LoiDonVi(f'Không mở được {p.name}: {e}') from None
    try:
        ws = wb[TEN_SHEET] if TEN_SHEET in wb.sheetnames else wb.worksheets[0]
        hang = list(ws.iter_rows(values_only=True, max_row=DONG_TOI_DA + 20))
    finally:
        wb.close()
    for i, h in enumerate(hang[:20]):
        cot = {j: _THEO_TIEU_DE[_chuan(v)] for j, v in enumerate(h) if _chuan(v) in _THEO_TIEU_DE}
        if 'ten' in cot.values():
            break
    else:
        raise LoiDonVi(f'{p.name}: không thấy dòng tiêu đề có cột "{COT[0][1]}" (dùng file Excel mẫu của phần mềm).')
    kq = []
    for so, h in enumerate(hang[i + 1:], i + 2):
        d = {k: _chu(h[j]) for j, k in cot.items() if j < len(h)}
        if any(d.values()):
            kq.append((so, d))
    return kq


def _doc_json(p: Path) -> list:
    """[(số thứ tự, {khóa: chữ} | {'_ho_so': dict})] từ file .json (hồ sơ địa phương hoặc danh sách đơn vị)."""
    try:
        du = json.loads(p.read_text(encoding='utf-8-sig'))
    except (OSError, UnicodeDecodeError) as e:
        raise LoiDonVi(f'Không đọc được {p.name}: {e}') from None
    except json.JSONDecodeError as e:
        raise LoiDonVi(f'{p.name} sai cú pháp JSON (dòng {e.lineno}, cột {e.colno}): {e.msg}') from None
    if isinstance(du, dict) and du.get('loai') == dia_phuong.LOAI:
        return [(1, {'_ho_so': du})]
    if isinstance(du, dict) and isinstance(du.get('don_vi'), list):
        du = du['don_vi']
    if not isinstance(du, list) or not all(isinstance(x, dict) for x in du):
        raise LoiDonVi(f'{p.name}: cần hồ sơ địa phương ("loai": "{dia_phuong.LOAI}") hoặc danh sách đơn vị [{{"ten": …}}, …].')
    kq = []
    for i, x in enumerate(du, 1):
        if x.get('loai') == dia_phuong.LOAI:
            kq.append((i, {'_ho_so': x}))
        else:
            kq.append((i, {_THEO_TIEU_DE.get(_chuan(k), k): _chu(v) for k, v in x.items()}))
    return kq


def doc_danh_sach(files) -> list:
    """Đọc một / nhiều file (.xlsx / .xlsm / .json) -> [DonVi dict(nguon, dong, du_lieu)]. Lỗi đọc file -> LoiDonVi."""
    if isinstance(files, (str, Path)):
        files = [files]
    kq = []
    for f in files:
        p = Path(f)
        if not p.is_file():
            raise LoiDonVi(f'Không có file {p}.')
        duoi = p.suffix.lower()
        if duoi in ('.xlsx', '.xlsm'):
            ds = _doc_excel(p)
        elif duoi == '.json':
            ds = _doc_json(p)
        else:
            raise LoiDonVi(f'{p.name}: chỉ nhận file Excel (.xlsx) hoặc .json.')
        kq += [dict(nguon=p, dong=so, du_lieu=d) for so, d in ds]
    if len(kq) > DONG_TOI_DA:
        raise LoiDonVi(f'Quá {DONG_TOI_DA} đơn vị trong một lần - chia nhỏ file danh sách.')
    return kq


# ---------------------------------------------------------------- hồ sơ của một đơn vị
def ho_so_nen(nen=NEN_MAY) -> dict:
    """Hồ sơ nền ĐẦY ĐỦ đã xóa thông tin cơ quan. nen: 'may' / 'mac_dinh' / đường dẫn file hồ sơ .json."""
    if nen in (None, '', NEN_MAY):
        hs = copy.deepcopy(dia_phuong.doc())
    elif nen == NEN_MAC_DINH:
        hs = dia_phuong.mac_dinh()
    else:
        try:
            hs = dia_phuong.kiem_tra_file(nen)
        except dia_phuong.LoiHoSo as e:
            raise LoiDonVi(f'Hồ sơ nền: {e}') from None
    cq = hs.setdefault('co_quan', {})
    for k in ('ten', 'truc_thuoc', 'dia_chi'):
        cq[k] = ''
    cq['ban_in_mac_dinh'] = {k: '' for k in (cq.get('ban_in_mac_dinh') or {})}
    hs.setdefault('ban_in', {})['dia_danh_ngay'] = ''
    return hs


def ho_so_don_vi(du_lieu: dict, nen: dict) -> tuple:
    """(hồ sơ đầy đủ, [cảnh báo]) của một đơn vị trên hồ sơ nền (ho_so_nen). Thiếu cột bắt buộc / hồ sơ sai -> LoiDonVi."""
    if '_ho_so' in du_lieu:                              # file .json là hồ sơ địa phương: trộn nguyên lên nền
        them = {k: v for k, v in du_lieu['_ho_so'].items() if k != 'ten_file'}
        hs = dia_phuong.tron(nen, them)
        d = dict(ten=str(hs['co_quan'].get('ten') or ''), ten_file=str(du_lieu['_ho_so'].get('ten_file') or ''))
    else:
        d = du_lieu
        thieu = [td for k, td, _n, bb, _g in COT if bb and not d.get(k)]
        if thieu:
            raise LoiDonVi('Thiếu ' + ', '.join(f'"{x}"' for x in thieu) + '.')
        hs = copy.deepcopy(nen)
        cq = hs['co_quan']
        bm = cq.setdefault('ban_in_mac_dinh', {})
        for k, _td, noi, _bb, _g in COT:
            v = d.get(k, '')
            if noi == 'co_quan' and (v or k != 'vai_tro'):
                cq[k] = v
            elif noi == 'ban_in_mac_dinh':
                bm[k] = v
            elif noi == 'dia_danh':
                bm['dia_danh_don_vi'] = v
                hs['ban_in']['dia_danh_ngay'] = v
        if not bm.get('don_vi_lap'):
            bm['don_vi_lap'] = cq['ten']
        hs['ten_ho_so'] = d.get('ten_ho_so') or cq['ten']
    if not str(hs['co_quan'].get('ten') or '').strip():
        raise LoiDonVi(f'Thiếu "{COT[0][1]}".')
    loi = dia_phuong.kiem_tra(hs)
    if loi:
        raise LoiDonVi('Hồ sơ chưa hợp lệ: ' + '; '.join(loi))
    bm = hs['co_quan'].get('ban_in_mac_dinh') or {}
    canh_bao = [f'chưa có "{td}"' for k, td, *_ in COT
                if k in ('don_vi_tieu_de', 'dia_danh', 'chuc_vu_ky')
                and not (bm.get(k) if k != 'dia_danh' else hs['ban_in'].get('dia_danh_ngay'))]
    hs['_ten_file'] = d.get('ten_file', '')
    return hs, canh_bao


def ten_file_goi(hs: dict, ten_file: str = '') -> str:
    """Tên file gói an toàn (không dấu, giữ chữ hoa / thường, không ký tự cấm), luôn đuôi .pabtcfg."""
    import unicodedata
    bo_dau = lambda x: ''.join(c for c in unicodedata.normalize('NFD', x.replace('đ', 'd').replace('Đ', 'D'))  # noqa: E731
                               if not unicodedata.combining(c))
    goc = ten_file or (TIEN_TO_FILE + (hs['co_quan'].get('ban_in_mac_dinh', {}).get('don_vi_tieu_de') or hs['co_quan']['ten']))
    goc = re.sub(r'\.pabtcfg$', '', goc, flags=re.I)
    s = re.sub(r'[^\w\-]+', '_', bo_dau(goc), flags=re.ASCII).strip('_')[:80] or 'LARC_CauHinh'
    return s + goi_mau.DUOI


# ---------------------------------------------------------------- tạo gói
def tao_hang_loat(files, thu_muc_ra, nen=NEN_MAY, kem_mau: bool = False, ghi_de: bool = True) -> list:
    """Đọc danh sách rồi tạo mỗi đơn vị một gói trong thu_muc_ra. Trả [dict(nguon, dong, ten, file, loi, canh_bao)] - đơn vị lỗi
    không dừng các đơn vị khác. KHÔNG đổi hồ sơ của máy. ghi_de=False: file trùng tên thêm _2, _3…; True: tên trùng TRONG LẦN NÀY
    vẫn thêm số (hai đơn vị không ghi đè nhau), gói cũ cùng tên trong thư mục bị thay."""
    ds = doc_danh_sach(files)
    goc_nen = ho_so_nen(nen)
    ra = Path(thu_muc_ra)
    ra.mkdir(parents=True, exist_ok=True)
    da_dung = set()
    kq = []
    for dv in ds:
        x = dict(nguon=dv['nguon'], dong=dv['dong'], ten=str(dv['du_lieu'].get('ten', '')), file=None, loi='', canh_bao=[])
        try:
            hs, x['canh_bao'] = ho_so_don_vi(dv['du_lieu'], goc_nen)
            x['ten'] = hs['co_quan']['ten']
            ten = ten_file_goi(hs, hs.pop('_ten_file', ''))
            f, i = ra / ten, 2
            while f.name.lower() in da_dung or (not ghi_de and f.exists()):
                f, i = ra / f'{Path(ten).stem}_{i}{goi_mau.DUOI}', i + 1
            da_dung.add(f.name.lower())
            goi_mau.tao_goi(f, mo_ta=f'Gói cấu hình đơn vị: {x["ten"]}', co_mau=kem_mau and bool(goi_mau.ds_mau_hien_hanh()),
                            ho_so=hs)
            x['file'] = f
        except (LoiDonVi, goi_mau.LoiGoiMau) as e:
            x['loi'] = str(e)
        kq.append(x)
    return kq


def tom_tat(kq: list) -> tuple:
    """(câu tóm tắt, [dòng chi tiết]) cho hộp kết quả / dòng lệnh."""
    dat = [x for x in kq if x['file']]
    dong = []
    for x in kq:
        noi = f'{Path(x["nguon"]).name} dòng {x["dong"]}'
        if x['file']:
            dong.append(f'OK  {x["ten"]} -> {Path(x["file"]).name}' + (f'  (lưu ý: {", ".join(x["canh_bao"])})' if x['canh_bao'] else ''))
        else:
            dong.append(f'LỖI {noi}: {x["ten"] or "(chưa có tên)"} - {x["loi"]}')
    return f'Đã tạo {len(dat)} / {len(kq)} gói cấu hình.', dong

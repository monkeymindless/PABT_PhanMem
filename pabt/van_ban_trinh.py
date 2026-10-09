"""Văn bản trình phê duyệt của đợt (0.9.16): mẫu TỜ TRÌNH (hoặc văn bản trình) và mẫu PHƯƠNG ÁN TỔNG (Word), điền số liệu của
đợt; xuất bộ hồ sơ trình chia 2 thư mục:
    PA CHI TIET\\   phương án chi tiết từng hộ (Excel / PDF)
    PA TONG\\       tờ trình / văn bản trình, phương án tổng (Word / PDF), bảng tổng hợp (có số phương án tổng)

Mẫu nằm ở <thư mục máy>\\mau_in (PABT_THU_MUC_MAY / %APPDATA%\\PABT): TO_TRINH.docx hoặc TO_TRINH.xlsx, PA_TONG.docx; chưa có thì
phần mềm tạo mẫu mặc định (không ghi cố định tên đơn vị, người ký - lấy từ Thông tin dự án). Thêm mẫu từ file Word (.docx /
.doc), Excel (.xlsx / .xls), PDF (Word chuyển sang .docx để sửa). Trong mẫu ghi chỗ trống {ten} (DS_CHO_TRONG); dòng bảng có
chỗ trống {ho.ten} được nhân thành mỗi hộ một dòng. Không phụ thuộc Qt; Word / Excel chỉ cần khi chuyển .doc / PDF, xuất PDF, in.
"""
from __future__ import annotations

import re
import shutil
import subprocess
import sys
import tempfile
import time
import zipfile
from datetime import date
from pathlib import Path

from .lap_pa import LoiNhap

THU_MUC_CT, THU_MUC_TONG = 'PA CHI TIET', 'PA TONG'
# loại mẫu -> (tên file, tên hiển thị, đuôi nhận)
LOAI = {'to_trinh': ('TO_TRINH', 'Tờ trình / văn bản trình', ('.docx', '.xlsx')),
        'pa_tong': ('PA_TONG', 'Phương án tổng', ('.docx',))}
TEN_RA = {'to_trinh': 'TO_TRINH', 'pa_tong': 'PHUONG_AN_TONG'}
NHAN_FILE = {'to_trinh': ('.docx', '.doc', '.xlsx', '.xls', '.pdf'), 'pa_tong': ('.docx', '.doc', '.pdf')}

DS_CHO_TRONG = [
    ('du_an', 'Tên dự án'), ('ten_dia_ban', 'Tên xã / phường'), ('cap_dia_ban', 'Cấp địa bàn (Xã / Phường)'),
    ('DON_VI_CAP_TREN', 'Đơn vị cấp trên (chữ hoa)'), ('DON_VI_CAP_TREN_2DONG', 'Đơn vị cấp trên, tự xuống dòng'),
    ('DON_VI_TIEU_DE', 'Tên đơn vị trên tiêu đề (chữ hoa)'), ('DON_VI_LAP', 'Đơn vị lập (chữ hoa)'), ('don_vi_lap', 'Đơn vị lập'),
    ('ky_hieu_so', 'Ký hiệu số văn bản (sau "Số: …/")'), ('nam', 'Năm'),
    ('CHUC_VU_KY', 'Chức vụ người ký (chữ hoa)'), ('nguoi_ky', 'Người ký'), ('nguoi_lap', 'Người lập'),
    ('nguoi_kiem_tra', 'Người kiểm tra'),
    ('ten_dot', 'Tên đợt trình'), ('loai_van_ban', 'Loại văn bản trình (Tờ trình / Văn bản)'),
    ('LOAI_VAN_BAN', 'Loại văn bản trình (chữ hoa: TỜ TRÌNH)'), ('so_to_trinh', 'Số tờ trình / văn bản trình'),
    ('ngay_trinh', 'Ngày trình (dd/mm/yyyy)'), ('ngay_trinh_chu', 'Ngày trình: "ngày 10 tháng 10 năm 2026"'),
    ('so_pa_tong', 'Số phương án tổng'), ('ngay_pa_tong', 'Ngày phương án tổng'),
    ('ngay_pa_tong_chu', 'Ngày phương án tổng: "ngày … tháng … năm …"'),
    ('so_ho', 'Số hộ (trường hợp)'), ('so_thua', 'Số thửa đất'), ('dt_thu_hoi', 'Tổng diện tích thu hồi (m²)'),
    ('tien_dat', 'Tiền bồi thường đất'), ('tien_nha', 'Tiền nhà, công trình'), ('tien_cay', 'Tiền cây trồng'),
    ('tien_ho_tro', 'Tiền các chính sách hỗ trợ'), ('tien_thuong', 'Tiền thưởng bàn giao'), ('tong_tien', 'Tổng tiền (số)'),
    ('tong_tien_chu', 'Tổng tiền bằng chữ'), ('ngay_lap_chu', 'Hôm nay: "ngày … tháng … năm …"'),
    ('ho.stt', 'Dòng bảng hộ: số thứ tự'), ('ho.ho_ten', 'Dòng bảng hộ: họ và tên'), ('ho.dia_chi', 'Dòng bảng hộ: địa chỉ'),
    ('ho.cccd', 'Dòng bảng hộ: số CCCD'), ('ho.so_pa', 'Dòng bảng hộ: số phương án chi tiết'),
    ('ho.so_pa_day_du', 'Dòng bảng hộ: "125/PA-…" (số / ký hiệu)'), ('ho.ngay_pa', 'Dòng bảng hộ: ngày phương án chi tiết'),
    ('ho.so_thua', 'Dòng bảng hộ: số thửa'), ('ho.dt_thu_hoi', 'Dòng bảng hộ: DT thu hồi (m²)'),
    ('ho.tien_dat', 'Dòng bảng hộ: tiền đất'), ('ho.tien_nha', 'Dòng bảng hộ: tiền nhà, công trình'),
    ('ho.tien_cay', 'Dòng bảng hộ: tiền cây trồng'), ('ho.tien_ho_tro', 'Dòng bảng hộ: tiền hỗ trợ'),
    ('ho.tien_thuong', 'Dòng bảng hộ: tiền thưởng'), ('ho.tong_tien', 'Dòng bảng hộ: tổng tiền'),
    ('ho.tai_dinh_cu', 'Dòng bảng hộ: tái định cư'),
]


# ---------------------------------------------------------------- thư mục, file mẫu
def thu_muc_mau() -> Path:
    from .may_chu import thu_muc_may
    return thu_muc_may() / 'mau_in'


def file_mau_rieng(loai: str):
    """Mẫu riêng người dùng đã thêm / sửa (TO_TRINH.docx / .xlsx, PA_TONG.docx trong thư mục mẫu), hoặc None."""
    ten, _, duoi = LOAI[loai]
    return next((p for p in (thu_muc_mau() / f'{ten}{d}' for d in duoi) if p.exists()), None)


def file_mau(loai: str, tao: bool = True):
    """Mẫu đang dùng: mẫu riêng nếu có; không thì mẫu mặc định của phiên bản phần mềm đang chạy (dựng lại mỗi lần - phần mềm cập
    nhật mẫu mặc định thì máy nào chưa có mẫu riêng cũng dùng bản mới). tao=False: không có mẫu riêng -> None."""
    p = file_mau_rieng(loai)
    if p is not None or not tao:
        return p
    return tao_mau_mac_dinh(loai)


def mo_ta_mau(loai: str) -> str:
    p = file_mau_rieng(loai)
    if p is None or (p.suffix == '.docx' and p.read_bytes() == _byte_mac_dinh(loai)):
        return 'mẫu mặc định của phần mềm'
    return f'{p.name} ({"Excel" if p.suffix == ".xlsx" else "Word"}' + \
        (', sửa từ mẫu mặc định)' if p.with_name(p.name + '.mac_dinh').exists() else ')')


def cho_trong_trong_file(p) -> list:
    """Các chỗ trống {…} có trong file mẫu (đã gom chỗ trống bị Word tách)."""
    p = Path(p)
    if p.suffix.lower() == '.xlsx':
        import openpyxl
        wb = openpyxl.load_workbook(p)
        chu = ' '.join(str(c.value) for ws in wb.worksheets for row in ws.iter_rows() for c in row if isinstance(c.value, str))
    else:
        with zipfile.ZipFile(p) as z:
            chu = ' '.join(_gom_cho_trong(z.read(n).decode('utf-8')) for n in z.namelist() if _la_phan_van_ban(n))
    return sorted(set(m.group(0)[1:-1] for m in _RE_CHO.finditer(chu)))


def them_mau(loai: str, file_nguon) -> tuple:
    """Dùng file người dùng chọn làm mẫu: Word .docx / .doc, Excel .xlsx / .xls (tờ trình), PDF (Word chuyển sang .docx để sửa,
    giữ được bố cục gần đúng). Mẫu cũ cất thành <tên>.bak.<đuôi>. Trả (file mẫu mới, [chỗ trống có trong mẫu])."""
    from . import an_toan
    p = Path(file_nguon)
    duoi = p.suffix.lower()
    if duoi not in NHAN_FILE[loai]:
        raise LoiNhap(f'Mẫu {LOAI[loai][1].lower()} nhận file: ' + ', '.join(NHAN_FILE[loai]) +
                      ' (file có macro .docm / .xlsm: lưu lại dạng .docx / .xlsx trước).')
    if not p.is_file():
        raise LoiNhap(f'Không thấy file {p}.')
    ten = LOAI[loai][0]
    tm = thu_muc_mau()
    tm.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as td:
        tam = Path(td) / f'nguon{duoi}'
        shutil.copy2(p, tam)
        if duoi in ('.doc', '.pdf'):
            dich = Path(td) / 'moi.docx'
            loi = chay_word([('docx_hien' if duoi == '.pdf' else 'docx', tam, dich)], cho_moi_file=600 if duoi == '.pdf' else 180)
            if not dich.exists():
                raise LoiNhap(f'Microsoft Word không chuyển được "{p.name}" sang .docx: ' + ('; '.join(loi) or 'không rõ lỗi'))
            tam, duoi = dich, '.docx'
        elif duoi == '.xls':
            from .nhap_don_gia import chuyen_office
            tam, duoi = chuyen_office(tam, '.xls'), '.xlsx'
        try:
            an_toan.kiem_tra_zip(tam)
        except an_toan.LoiAnToan as e:
            raise LoiNhap(str(e)) from None
        dich = tm / f'{ten}{duoi}'
        for d in LOAI[loai][2]:                          # một mẫu đang dùng mỗi loại: cất mẫu cũ (cả đuôi khác)
            cu = tm / f'{ten}{d}'
            if cu.exists():
                shutil.copy2(cu, tm / f'{ten}.bak{d}')
                cu.unlink()
            (tm / f'{ten}{d}.mac_dinh').unlink(missing_ok=True)
        shutil.copy2(tam, dich)
    return dich, cho_trong_trong_file(dich)


def mau_de_sua(loai: str) -> Path:
    """File mẫu riêng để mở bằng Word / Excel sửa trực tiếp; chưa có thì chép mẫu mặc định thành mẫu riêng (đánh dấu .mac_dinh)."""
    p = file_mau_rieng(loai)
    if p is None:
        p = thu_muc_mau() / f'{LOAI[loai][0]}.docx'
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(_byte_mac_dinh(loai))
        p.with_name(p.name + '.mac_dinh').write_text('', encoding='utf-8')
    return p


def khoi_phuc_mac_dinh(loai: str) -> Path:
    """Bỏ mẫu riêng (cất thành <tên>.bak.<đuôi>), dùng lại mẫu mặc định của phần mềm."""
    ten = LOAI[loai][0]
    for d in LOAI[loai][2]:
        cu = thu_muc_mau() / f'{ten}{d}'
        if cu.exists():
            shutil.copy2(cu, cu.with_name(f'{ten}.bak{d}'))
            cu.unlink()
        cu.with_name(cu.name + '.mac_dinh').unlink(missing_ok=True)
    return tao_mau_mac_dinh(loai)


# ---------------------------------------------------------------- số liệu điền vào mẫu
def ngay_chu(ngay: str, nam=None) -> str:
    """'10/10/2026' -> 'ngày 10 tháng 10 năm 2026'; trống -> 'ngày …… tháng …… năm <nam>' (chừa chỗ viết tay)."""
    m = re.fullmatch(r'(\d{1,2})/(\d{1,2})/(\d{4})', str(ngay or '').strip())
    if m:
        return f'ngày {int(m.group(1)):02d} tháng {int(m.group(2)):02d} năm {m.group(3)}'
    return f'ngày …… tháng …… năm {nam or "……"}'


def du_lieu(con, ds_ma_ho: list, dot=None) -> tuple:
    """(chỗ trống chung {ten: chữ}, [chỗ trống từng hộ {ho.ten: chữ}]) của các hộ (theo thứ tự danh sách) và đợt (quan_ly.Dot)."""
    from . import in_an, nghiep_vu
    from .lap_pa import cau_tai_dinh_cu
    from .tien import KHONG, D, so_vn, tien_bang_chu, vn
    da = in_an._thong_tin_du_an(con)
    bc = nghiep_vu.BoiCanh.tu(con)
    thu_tu = {r['ma_ho']: (r['thu_tu'], r['ma_ho']) for r in con.execute('SELECT ma_ho, thu_tu FROM ho')}
    ds_ma_ho = sorted(ds_ma_ho, key=lambda m: thu_tu.get(m, (0, m)))
    pas = nghiep_vu.doc_tat_ca_phuong_an(con, ds_ma_ho)
    ho = {r['ma_ho']: dict(r) for r in con.execute('SELECT * FROM ho')}
    ky_hieu = da.get('ky_hieu_so') or ''
    tong = {k: KHONG for k in (1, 2, 3, 4, 5)}
    so_thua, dt = 0, KHONG
    dong = []
    for stt, m in enumerate(ds_ma_ho, start=1):
        h = ho.get(m)
        if h is None:
            continue
        kq = nghiep_vu.tinh_pa(pas[m], bc) if m in pas else None
        muc = kq.muc if kq else {k: KHONG for k in (1, 2, 3, 4, 5)}
        for k in tong:
            tong[k] += muc[k]
        thua = bc.thua_cua(m)
        dt_ho = sum((D(t['dt_thu_hoi']) for t in thua), KHONG)
        so_thua += len(thua)
        dt += dt_ho
        so_pa = (h.get('so_pa') or '').strip()
        dong.append({'ho.stt': str(stt), 'ho.ma_ho': str(m), 'ho.ho_ten': ' '.join(str(h['ho_ten'] or '').split()),
                     'ho.dia_chi': (h['dia_chi'] or '').strip(), 'ho.cccd': (h['so_cccd'] or '').strip(),
                     'ho.so_pa': so_pa, 'ho.so_pa_day_du': (f'{so_pa}/{ky_hieu}' if ky_hieu else so_pa) if so_pa else '',
                     'ho.ngay_pa': h.get('ngay_pa') or '', 'ho.so_thua': str(len(thua)), 'ho.dt_thu_hoi': so_vn(dt_ho),
                     'ho.tien_dat': vn(muc[1]), 'ho.tien_nha': vn(muc[2]), 'ho.tien_cay': vn(muc[3]),
                     'ho.tien_ho_tro': vn(muc[4]), 'ho.tien_thuong': vn(muc[5]), 'ho.tong_tien': vn(sum(muc.values(), KHONG)),
                     'ho.tai_dinh_cu': cau_tai_dinh_cu(h.get('tai_dinh_cu') or '')})
    tong_tien = sum(tong.values(), KHONG)
    chung = {k: ('' if v is None else str(v)) for k, v in da.items()}
    r = con.execute('SELECT chuc_vu_ky FROM du_an WHERE id = 1').fetchone()
    chung.update(chuc_vu_ky=(r[0] if r else '') or '', so_ho=str(len(dong)), so_ho_02=f'{len(dong):02d}', so_thua=str(so_thua),
                 dt_thu_hoi=so_vn(dt), tien_dat=vn(tong[1]), tien_nha=vn(tong[2]), tien_cay=vn(tong[3]),
                 tien_ho_tro=vn(tong[4]), tien_thuong=vn(tong[5]), tong_tien=vn(tong_tien),
                 tong_tien_chu=tien_bang_chu(tong_tien), ngay_lap_chu=ngay_chu(date.today().strftime('%d/%m/%Y')))
    loai_vb = (getattr(dot, 'loai_van_ban', '') or 'Tờ trình') if dot is not None else 'Tờ trình'
    chung.update(ten_dot=getattr(dot, 'ten', '') or '', loai_van_ban=loai_vb, LOAI_VAN_BAN=loai_vb.upper(),
                 so_to_trinh=getattr(dot, 'so_to_trinh', '') or '', ngay_trinh=getattr(dot, 'ngay_trinh', '') or '',
                 ngay_trinh_chu=ngay_chu(getattr(dot, 'ngay_trinh', ''), da.get('nam')),
                 so_pa_tong=getattr(dot, 'so_pa_tong', '') or '', ngay_pa_tong=getattr(dot, 'ngay_pa_tong', '') or '',
                 ngay_pa_tong_chu=ngay_chu(getattr(dot, 'ngay_pa_tong', ''), da.get('nam')),
                 van_ban_trinh=getattr(dot, 'van_ban_trinh', '') if dot is not None else '')
    return chung, dong


# ---------------------------------------------------------------- điền mẫu Word (.docx): sửa thẳng XML, không cần Word
_RE_P = re.compile(r'<w:p[ >].*?</w:p>', re.S)
_RE_T = re.compile(r'(<w:t(?:\s[^>]*)?>)(.*?)(</w:t>)', re.S)
_RE_TR = re.compile(r'<w:tr[ >].*?</w:tr>', re.S)
_RE_CHO = re.compile(r'\{[A-Za-z_][A-Za-z0-9_.]*\}')


def _la_phan_van_ban(ten: str) -> bool:
    return ten == 'word/document.xml' or bool(re.fullmatch(r'word/(header|footer)\d*\.xml', ten))


def _gom_doan(doan: str) -> str:
    """Một đoạn văn (w:p): chỗ trống {ten} bị Word tách qua nhiều mẩu chữ (w:t - đổi định dạng, kiểm lỗi chính tả...) -> gom cả
    chỗ trống về mẩu đầu, các mẩu sau bỏ phần đã gom."""
    ts = list(_RE_T.finditer(doan))
    if len(ts) < 2:
        return doan
    chu = [m.group(2) for m in ts]
    toan = ''.join(chu)
    if '{' not in toan:
        return doan
    dau, s = [], 0
    for c in chu:
        dau.append(s)
        s += len(c)
    goc = list(chu)

    def manh(vt: int) -> int:                           # mẩu chứa ký tự thứ vt (bỏ qua mẩu rỗng)
        return next(k for k in range(len(goc)) if dau[k] <= vt < dau[k] + len(goc[k]))
    doi = False
    for m in reversed(list(_RE_CHO.finditer(toan))):  # từ phải sang trái: vị trí phía trước không đổi
        i, j = manh(m.start()), manh(m.end() - 1)
        if i == j:
            continue
        chu[i] = chu[i][:m.start() - dau[i]] + m.group(0)
        for k in range(i + 1, j):
            chu[k] = ''
        chu[j] = chu[j][m.end() - dau[j]:]
        doi = True
    if not doi:
        return doan
    ra, cuoi = [], 0
    for k, m in enumerate(ts):
        mo = m.group(1)
        if 'xml:space' not in mo:
            mo = mo[:-1] + ' xml:space="preserve">'
        ra.append(doan[cuoi:m.start()] + mo + chu[k] + m.group(3))
        cuoi = m.end()
    return ''.join(ra) + doan[cuoi:]


def _gom_cho_trong(xml: str) -> str:
    return _RE_P.sub(lambda m: _gom_doan(m.group(0)), xml)


def _xml(s: str) -> str:
    s = str(s).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
    return s.replace('\r\n', '\n').replace('\n', '</w:t><w:br/><w:t xml:space="preserve">')   # xuống dòng trong ô chữ Word


def _thay(xml: str, gia_tri: dict) -> str:
    return _RE_CHO.sub(lambda m: _xml(gia_tri[m.group(0)[1:-1]]) if m.group(0)[1:-1] in gia_tri else m.group(0), xml)


def dien_docx(mau, ra, chung: dict, ds_ho: list) -> Path:
    """Điền mẫu Word: chỗ trống chung; dòng bảng có {ho.…} nhân thành mỗi hộ một dòng (không có hộ: bỏ dòng)."""
    mau, ra = Path(mau), Path(ra)
    with zipfile.ZipFile(mau) as z:
        tep = {n: z.read(n) for n in z.namelist()}
    for n in list(tep):
        if not _la_phan_van_ban(n):
            continue
        x = _gom_cho_trong(tep[n].decode('utf-8'))
        x = _RE_TR.sub(lambda m: ''.join(_thay(m.group(0), h) for h in ds_ho) if '{ho.' in m.group(0) else m.group(0), x)
        tep[n] = _thay(x, chung).encode('utf-8')
    ra.parent.mkdir(parents=True, exist_ok=True)
    tam = ra.with_name(ra.name + '.tmp')
    with zipfile.ZipFile(tam, 'w', zipfile.ZIP_DEFLATED) as zo:
        for n, du in tep.items():
            zo.writestr(n, du)
    tam.replace(ra)
    return ra


# ---------------------------------------------------------------- điền mẫu Excel (.xlsx)
def dien_xlsx(mau, ra, chung: dict, ds_ho: list) -> Path:
    """Điền mẫu Excel: chỗ trống chung trong mọi ô chữ; dòng có {ho.…} nhân thành mỗi hộ một dòng (giữ định dạng dòng mẫu)."""
    import openpyxl
    from .in_an import _chep_kieu_dong, _doi_dong
    wb = openpyxl.load_workbook(mau)
    for ws in wb.worksheets:
        so_cot = ws.max_column
        dong_ho = [r for r in range(1, ws.max_row + 1)
                   if any(isinstance(ws.cell(r, c).value, str) and '{ho.' in ws.cell(r, c).value for c in range(1, so_cot + 1))]
        for r in reversed(dong_ho):                     # từ dưới lên: chèn dòng không làm lệch các dòng mẫu phía trên
            mau_o = [ws.cell(r, c).value for c in range(1, so_cot + 1)]
            if not ds_ho:
                _doi_dong(ws, r, -1)
                continue
            if len(ds_ho) > 1:
                _doi_dong(ws, r + 1, len(ds_ho) - 1)
                for k in range(1, len(ds_ho)):
                    _chep_kieu_dong(ws, r, r + k, so_cot)
                    ws.row_dimensions[r + k].height = ws.row_dimensions[r].height
            for k, h in enumerate(ds_ho):
                for c, v in enumerate(mau_o, start=1):
                    ws.cell(r + k, c).value = _gia_tri_o(v, h) if isinstance(v, str) else v
        for row in ws.iter_rows():
            for o in row:
                if isinstance(o.value, str) and '{' in o.value:
                    o.value = _gia_tri_o(o.value, chung)
    ra = Path(ra)
    ra.parent.mkdir(parents=True, exist_ok=True)
    wb.save(ra)
    return ra


def _gia_tri_o(v: str, gia_tri: dict):
    """Ô Excel: chỉ có một chỗ trống là số tiền / số lượng -> ghi số (Excel cộng được); còn lại thay chữ."""
    m = _RE_CHO.fullmatch(v.strip())
    if m and m.group(0)[1:-1] in gia_tri:
        s = gia_tri[m.group(0)[1:-1]]
        if re.fullmatch(r'-?\d{1,3}(\.\d{3})*', s):
            return int(s.replace('.', ''))
        return s
    return _RE_CHO.sub(lambda x: gia_tri.get(x.group(0)[1:-1], x.group(0)), v)


# ---------------------------------------------------------------- lập văn bản của đợt
def lap_van_ban(con, loai: str, ds_ma_ho: list, thu_muc, dot=None) -> Path:
    """Điền mẫu loại ('to_trinh' / 'pa_tong') cho các hộ (của đợt) vào thư mục. Trả file .docx / .xlsx đã tạo."""
    mau = file_mau(loai)
    chung, dong = du_lieu(con, ds_ma_ho, dot)
    ra = Path(thu_muc) / f'{TEN_RA[loai]}{mau.suffix}'
    return (dien_xlsx if mau.suffix.lower() == '.xlsx' else dien_docx)(mau, ra, chung, dong)


def xuat_bo_ho_so(con, ds_ma_ho: list, thu_muc, dot=None, chi_tiet: bool = True, bang_tong_hop: bool = True,
                  to_trinh: bool = False, pa_tong: bool = False, pdf: bool = False, in_may: bool = False, so_ban: int = 1,
                  chia_thu_muc: bool = True, bao_tien_do=None, bao_excel=None) -> dict:
    """Bộ hồ sơ trình: PA CHI TIET\\ (phương án chi tiết từng hộ) + PA TONG\\ (bảng tổng hợp có số / ngày phương án tổng, tờ
    trình / văn bản trình, phương án tổng). pdf: kèm PDF (Excel / Word xuất); in_may: in ra máy in mặc định. Mỗi mẫu chọn riêng
    hoặc tất cả. Trả dict(excel, word, pdf, loi, thu_muc_ct, thu_muc_tong). bao_tien_do(i, n) / bao_excel(i, n): trả True = dừng."""
    from . import in_an
    thu_muc = Path(thu_muc)
    tm_ct = thu_muc / THU_MUC_CT if chia_thu_muc else thu_muc
    tm_tong = thu_muc / THU_MUC_TONG if chia_thu_muc else thu_muc
    kq = dict(excel=[], word=[], pdf=[], loi=[], thu_muc_ct=tm_ct, thu_muc_tong=tm_tong)
    so_viec = (len(ds_ma_ho) if chi_tiet else 0) + int(bang_tong_hop) + int(to_trinh) + int(pa_tong)
    da = 0

    def bao():
        nonlocal da
        da += 1
        return bool(bao_tien_do and bao_tien_do(da, so_viec))
    if chi_tiet:
        tm_ct.mkdir(parents=True, exist_ok=True)
        mau = in_an.thu_muc_mau()
        bc = in_an.BoiCanh.tu(con)
        for i, ma in enumerate(ds_ma_ho, start=1):
            kq['excel'].append(in_an.lap_chi_tiet(con, ma, tm_ct / f'{in_an.ten_file_ho(con, ma)}.xlsx', mau, bc))
            if bao():
                kq['loi'].append(f'DA_DUNG\t\tĐã dừng theo yêu cầu sau {i}/{len(ds_ma_ho)} hộ (chưa xuất PDF / in)')
                return kq
    if bang_tong_hop or to_trinh or pa_tong:
        tm_tong.mkdir(parents=True, exist_ok=True)
    if bang_tong_hop:
        kq['excel'].append(in_an.lap_bang_tong_hop(con, tm_tong / 'BANG_TONG_HOP.xlsx', ds_ma_ho,
                                                   so_pa_tong=getattr(dot, 'so_pa_tong', '') or '',
                                                   ngay_pa_tong=getattr(dot, 'ngay_pa_tong', '') or ''))
        bao()
    for loai, chon in (('to_trinh', to_trinh), ('pa_tong', pa_tong)):
        if chon:
            p = lap_van_ban(con, loai, ds_ma_ho, tm_tong, dot)
            kq['excel' if p.suffix == '.xlsx' else 'word'].append(p)
            bao()
    if pdf or in_may:
        if kq['excel']:
            cap = [(p, p.with_suffix('.pdf') if pdf else None) for p in kq['excel']]
            kq['loi'] += in_an.chay_excel(cap, 'in' if in_may else 'pdf', bao=bao_excel, so_ban=so_ban)
            kq['pdf'] += [b for _, b in cap if b and Path(b).exists()]
        if kq['word']:
            viec = [((f'in:{so_ban}' if in_may else 'pdf'), p, p.with_suffix('.pdf') if pdf else None) for p in kq['word']]
            kq['loi'] += chay_word(viec)
            kq['pdf'] += [c for _, _, c in viec if c and Path(c).exists()]
    return kq


# ---------------------------------------------------------------- Microsoft Word (chuyển .doc / PDF -> .docx, xuất PDF, in)
_VBS_WORD = r'''
On Error Resume Next
Dim w, d, f, ds, che_do, ban
Set f = CreateObject("Scripting.FileSystemObject").OpenTextFile(WScript.Arguments(0), 1, False, -1)
Set w = CreateObject("Word.Application")
If Err.Number <> 0 Then
    WScript.StdErr.WriteLine "KHONG_CO_WORD"
    WScript.Quit 3
End If
w.Visible = False
w.DisplayAlerts = 0
w.AutomationSecurity = 3
w.Options.ConfirmConversions = False
Err.Clear
Do While Not f.AtEndOfStream
    ds = Split(f.ReadLine, vbTab)
    che_do = ds(0)
    Err.Clear
    If che_do = "docx_hien" Then w.Visible = True
    Set d = w.Documents.Open(ds(1), False, True, False)
    If Err.Number <> 0 Then
        WScript.StdErr.WriteLine "LOI_MO" & vbTab & ds(1) & vbTab & Err.Description
    Else
        Err.Clear
        If che_do = "docx" Or che_do = "docx_hien" Then
            d.SaveAs2 ds(2), 16
        ElseIf che_do = "pdf" Then
            d.ExportAsFixedFormat ds(2), 17
        ElseIf Left(che_do, 3) = "in:" Then
            ban = CInt(Mid(che_do, 4))
            d.PrintOut False, , , , , , , ban
        End If
        If Err.Number <> 0 Then WScript.StdErr.WriteLine "LOI_XUAT" & vbTab & ds(1) & vbTab & Err.Description
        d.Close 0
    End If
    WScript.StdOut.WriteLine "XONG"
Loop
f.Close
w.Quit 0
'''


def co_word() -> bool:
    return sys.platform == 'win32'


def chay_word(viec: list, cho_moi_file: int = 180) -> list:
    """Nhờ Microsoft Word làm từng việc [(che_do, file vào, file ra)]: 'docx' (lưu .docx - mở được .doc), 'docx_hien' (như
    docx nhưng Word HIỆN lên: mở PDF Word luôn hỏi "chuyển PDF thành văn bản sửa được" - hộp thoại này không tắt được qua tự
    động hóa, người dùng bấm OK), 'pdf' (xuất PDF), 'in:N' (in N bản ra máy in mặc định). Macro tắt (AutomationSecurity = 3).
    Trả danh sách lỗi (rỗng = thành công)."""
    if not viec:
        return []
    if not co_word():
        raise LoiNhap('Chuyển / xuất PDF / in văn bản Word cần Microsoft Word trên máy Windows.')
    with tempfile.TemporaryDirectory() as td:
        vbs = Path(td) / 'word.vbs'
        vbs.write_text(_VBS_WORD, encoding='utf-16')
        ds = Path(td) / 'ds.txt'
        ds.write_text('\n'.join(f'{che_do}\t{Path(a).resolve()}\t{Path(b).resolve() if b else ""}' for che_do, a, b in viec),
                      encoding='utf-16')
        bat_dau = time.time()
        try:
            r = subprocess.run(['cscript', '//nologo', str(vbs), str(ds)], capture_output=True,
                               timeout=60 + cho_moi_file * len(viec), creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        except subprocess.TimeoutExpired:
            from .in_an import _tat_excel_tu_dong
            _tat_excel_tu_dong(bat_dau, 'WINWORD.EXE')
            return [f'LOI_TREO\t\tMicrosoft Word không làm xong sau {60 + cho_moi_file * len(viec)} giây (kẹt hộp thoại ẩn / máy in?)']
        except OSError as e:
            raise LoiNhap(f'Không chạy được trình điều khiển Word (cscript): {e}') from e
    loi = r.stderr.decode('oem' if sys.platform == 'win32' else 'utf-8', 'replace')
    if r.returncode == 3 or 'KHONG_CO_WORD' in loi:
        raise LoiNhap('Không mở được Microsoft Word trên máy này: chỉ tạo được file Word (.docx), chưa xuất PDF / in được.')
    ds_loi = [x for x in loi.splitlines() if x.startswith(('LOI_MO', 'LOI_XUAT'))]
    for che_do, a, b in viec:
        if che_do in ('docx', 'pdf') and b and not Path(b).exists() and not any(str(Path(a).resolve()) in x for x in ds_loi):
            ds_loi.append(f'LOI_XUAT\t{a}\tWord không tạo được file {Path(b).suffix}')
    return ds_loi


# ---------------------------------------------------------------- mẫu mặc định (Word) - không ghi cố định tên đơn vị, người ký
_W = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'


def _r(chu: str, dam: bool = False, nghieng: bool = False, gach: bool = False, co: float = 0) -> str:
    pr = ('<w:b/>' if dam else '') + ('<w:i/>' if nghieng else '') + ('<w:u w:val="single"/>' if gach else '') + \
         (f'<w:sz w:val="{int(co * 2)}"/><w:szCs w:val="{int(co * 2)}"/>' if co else '')
    return f'<w:r>{"<w:rPr>" + pr + "</w:rPr>" if pr else ""}<w:t xml:space="preserve">{_xml(chu)}</w:t></w:r>'


def _p(*chay, can: str = 'both', truoc: int = 0, sau: int = 60, dau_dong: int = 0) -> str:
    thut = f'<w:ind w:firstLine="{dau_dong}"/>' if dau_dong else ''
    return (f'<w:p><w:pPr><w:spacing w:before="{truoc}" w:after="{sau}" w:line="300" w:lineRule="auto"/>{thut}'
            f'<w:jc w:val="{can}"/></w:pPr>{"".join(chay)}</w:p>')


def _bang(hang: list, rong: list, vien: bool = True) -> str:
    """hang: [[nội dung ô (chuỗi các w:p)]]. Trang A4 dọc lề trái 3 cm, phải 2 cm: tổng độ rộng cột <= 9.071 (twip)."""
    b = ''.join(f'<w:{k} w:val="{"single" if vien else "nil"}" w:sz="4" w:space="0" w:color="000000"/>'
                for k in ('top', 'left', 'bottom', 'right', 'insideH', 'insideV'))
    luoi = ''.join(f'<w:gridCol w:w="{x}"/>' for x in rong)
    dong = ''.join('<w:tr>' + ''.join(f'<w:tc><w:tcPr><w:tcW w:w="{rong[i]}" w:type="dxa"/><w:vAlign w:val="center"/></w:tcPr>'
                                      f'{o}</w:tc>' for i, o in enumerate(h)) + '</w:tr>' for h in hang)
    return (f'<w:tbl><w:tblPr><w:tblW w:w="{sum(rong)}" w:type="dxa"/><w:jc w:val="center"/><w:tblBorders>{b}</w:tblBorders>'
            f'<w:tblLayout w:type="fixed"/><w:tblCellMar><w:left w:w="45" w:type="dxa"/><w:right w:w="45" w:type="dxa"/>'
            f'</w:tblCellMar></w:tblPr><w:tblGrid>{luoi}</w:tblGrid>{dong}</w:tbl>')


def _o(chu: str, dam: bool = False, can: str = 'center', co: float = 0, nghieng: bool = False) -> str:
    return _p(_r(chu, dam=dam, co=co, nghieng=nghieng), can=can, sau=0)


def _dau_trang(so: str, ngay: str) -> str:
    """Khối tiêu đề 2 cột: cơ quan | quốc hiệu, tiêu ngữ; số; địa danh, ngày."""
    trai = _o('{DON_VI_CAP_TREN_2DONG}', co=10.5) + _o('{DON_VI_TIEU_DE}', dam=True, co=12) + _o('______', co=12) + \
        _o(so, co=13)
    phai = _o('CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM', dam=True, co=11.5) + \
        _p(_r('Độc lập - Tự do - Hạnh phúc', dam=True, co=13), can='center', sau=0) + \
        _o('______________________', co=12) + _o(f'{{ten_dia_ban}}, {ngay}', nghieng=True, co=13)
    return _bang([[trai, phai]], [3970, 5100], vien=False)


def _ky_ten() -> str:
    trai = _p(_r('Nơi nhận:', dam=True, nghieng=True, co=12), can='left', sau=0) + \
        _p(_r('- Như trên;', co=11), can='left', sau=0) + _p(_r('- Lưu: VT.', co=11), can='left', sau=0)
    phai = _o('{CHUC_VU_KY}', dam=True) + _o(' ') + _o(' ') + _o(' ') + _o(' ') + _o('{nguoi_ky}', dam=True)
    return _bang([[trai, phai]], [4170, 4900], vien=False)


def _can_cu_trong() -> str:
    """Dòng "Căn cứ ……;" chừa để điền (canh trái: canh đều làm giãn chữ khi dòng chấm xuống dòng)."""
    return _p(_r('Căn cứ ……………………………………………………………………;'), can='left', dau_dong=567)


def _noi_dung_to_trinh() -> str:
    t = [_dau_trang('Số: {so_to_trinh}', '{ngay_trinh_chu}'),
         _p(_r('{LOAI_VAN_BAN}', dam=True, co=14), can='center', truoc=240, sau=0),
         _p(_r('Về việc thẩm định, phê duyệt phương án bồi thường, hỗ trợ, tái định cư', dam=True), can='center', sau=0),
         _p(_r('{ten_dot} - Dự án: {du_an}', dam=True), can='center', sau=120),
         _p(_r('Kính gửi: ……………………………………………………'), can='center', sau=200),
         _p(_r('Căn cứ Luật Đất đai năm 2024;'), dau_dong=567),
         _can_cu_trong(),
         _p(_r('{don_vi_lap} kính trình thẩm định, phê duyệt phương án bồi thường, hỗ trợ, tái định cư {ten_dot} dự án '
               '{du_an} như sau:'), dau_dong=567),
         _p(_r('1. Tổng số trường hợp: {so_ho} hộ, {so_thua} thửa đất, tổng diện tích thu hồi {dt_thu_hoi} m².'), dau_dong=567),
         _p(_r('2. Tổng kinh phí bồi thường, hỗ trợ: '), _r('{tong_tien} đồng', dam=True),
            _r(' (Bằng chữ: {tong_tien_chu}), trong đó:'), dau_dong=567),
         _p(_r('- Bồi thường về đất: {tien_dat} đồng;'), dau_dong=567),
         _p(_r('- Bồi thường, hỗ trợ về nhà, công trình: {tien_nha} đồng;'), dau_dong=567),
         _p(_r('- Bồi thường, hỗ trợ về cây trồng: {tien_cay} đồng;'), dau_dong=567),
         _p(_r('- Các chính sách hỗ trợ khác: {tien_ho_tro} đồng;'), dau_dong=567),
         _p(_r('- Thưởng bàn giao mặt bằng trước thời hạn: {tien_thuong} đồng.'), dau_dong=567),
         _p(_r('3. Hồ sơ kèm theo: Phương án tổng số {so_pa_tong}/{ky_hieu_so} {ngay_pa_tong_chu}; bảng tổng hợp và phương án '
               'chi tiết của từng hộ theo danh sách sau:'), dau_dong=567, sau=120),
         _bang([[_o('STT', True, co=12), _o('Họ và tên', True, co=12), _o('Địa chỉ', True, co=12),
                 _o('Phương án chi tiết số', True, co=12), _o('Số tiền (đồng)', True, co=12)],
                [_o('{ho.stt}', co=12), _o('{ho.ho_ten}', can='left', co=12), _o('{ho.dia_chi}', can='left', co=11),
                 _o('{ho.so_pa_day_du}', co=11), _o('{ho.tong_tien}', can='right', co=12)],
                [_o(''), _o('Tổng cộng', True, co=12), _o(''), _o(''), _o('{tong_tien}', True, can='right', co=12)]],
               [550, 2250, 2250, 2300, 1700]),
         _p(_r('{don_vi_lap} kính trình xem xét, phê duyệt./.'), dau_dong=567, truoc=200, sau=200),
         _ky_ten()]
    return ''.join(t)


def _noi_dung_pa_tong() -> str:
    co = 9.5                                        # 6 cột tiền trên khổ A4 dọc: số tới hàng tỷ không bị ngắt dòng
    t = [_dau_trang('Số: {so_pa_tong}/{ky_hieu_so}', '{ngay_pa_tong_chu}'),
         _p(_r('PHƯƠNG ÁN', dam=True, co=14), can='center', truoc=240, sau=0),
         _p(_r('Bồi thường, hỗ trợ, tái định cư {ten_dot}', dam=True), can='center', sau=0),
         _p(_r('Dự án: {du_an}', dam=True), can='center', sau=200),
         _p(_r('I. CĂN CỨ LẬP PHƯƠNG ÁN', dam=True)),
         _p(_r('Căn cứ Luật Đất đai năm 2024;'), dau_dong=567),
         _can_cu_trong(),
         _p(_r('II. TỔNG HỢP PHƯƠNG ÁN BỒI THƯỜNG, HỖ TRỢ, TÁI ĐỊNH CƯ', dam=True), truoc=120),
         _p(_r('Tổng số trường hợp: {so_ho} hộ, {so_thua} thửa đất, tổng diện tích thu hồi {dt_thu_hoi} m². Tổng kinh phí: '),
            _r('{tong_tien} đồng', dam=True), _r(' (Bằng chữ: {tong_tien_chu}). Chi tiết từng hộ:'), dau_dong=567, sau=120),
         _bang([[_o('STT', True, co=co), _o('Họ và tên', True, co=co), _o('PA chi tiết số', True, co=co), _o('Đất', True, co=co),
                 _o('Nhà, công trình', True, co=co), _o('Cây trồng', True, co=co), _o('Hỗ trợ', True, co=co),
                 _o('Thưởng', True, co=co), _o('Tổng cộng', True, co=co)],
                [_o('{ho.stt}', co=co), _o('{ho.ho_ten}', can='left', co=co), _o('{ho.so_pa}', co=co),
                 _o('{ho.tien_dat}', can='right', co=co), _o('{ho.tien_nha}', can='right', co=co),
                 _o('{ho.tien_cay}', can='right', co=co), _o('{ho.tien_ho_tro}', can='right', co=co),
                 _o('{ho.tien_thuong}', can='right', co=co), _o('{ho.tong_tien}', can='right', co=co)],
                [_o(''), _o('Tổng cộng', True, co=co), _o(''), _o('{tien_dat}', True, can='right', co=co),
                 _o('{tien_nha}', True, can='right', co=co), _o('{tien_cay}', True, can='right', co=co),
                 _o('{tien_ho_tro}', True, can='right', co=co), _o('{tien_thuong}', True, can='right', co=co),
                 _o('{tong_tien}', True, can='right', co=co)]],
               [400, 1500, 600, 1100, 1100, 1000, 1100, 1000, 1200]),
         _p(_r('III. TỔ CHỨC THỰC HIỆN', dam=True), truoc=200),
         _p(_r('……………………………………………………………………'), can='left', dau_dong=567, sau=200),
         _bang([[_o('NGƯỜI LẬP', dam=True) + _o(' ') + _o(' ') + _o(' ') + _o('{nguoi_lap}', dam=True),
                 _o('NGƯỜI KIỂM TRA', dam=True) + _o(' ') + _o(' ') + _o(' ') + _o('{nguoi_kiem_tra}', dam=True),
                 _o('{CHUC_VU_KY}', dam=True) + _o(' ') + _o(' ') + _o(' ') + _o('{nguoi_ky}', dam=True)]],
               [3000, 3000, 3050], vien=False)]
    return ''.join(t)


def _goi_docx(than: str) -> bytes:
    """Gói .docx tối thiểu (nội dung, kiểu chữ Times New Roman 13, A4) - giống hệt từng byte mỗi lần tạo (ngày giờ cố định) để
    nhận ra mẫu mặc định chưa sửa."""
    import io
    loai = 'application/vnd.openxmlformats-officedocument.wordprocessingml'
    tep = {
        '[Content_Types].xml': '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        f'<Override PartName="/word/document.xml" ContentType="{loai}.document.main+xml"/>'
        f'<Override PartName="/word/styles.xml" ContentType="{loai}.styles+xml"/></Types>',
        '_rels/.rels': '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" '
        'Target="word/document.xml"/></Relationships>',
        'word/_rels/document.xml.rels': '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" '
        'Target="styles.xml"/></Relationships>',
        'word/styles.xml': f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:styles xmlns:w="{_W}"><w:docDefaults>'
        '<w:rPrDefault><w:rPr><w:rFonts w:ascii="Times New Roman" w:hAnsi="Times New Roman" w:cs="Times New Roman" '
        'w:eastAsia="Times New Roman"/><w:sz w:val="26"/><w:szCs w:val="26"/><w:lang w:val="vi-VN"/></w:rPr></w:rPrDefault>'
        '<w:pPrDefault><w:pPr><w:spacing w:after="60"/></w:pPr></w:pPrDefault></w:docDefaults></w:styles>',
        'word/document.xml': f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:document xmlns:w="{_W}"><w:body>'
        f'{than}<w:sectPr><w:pgSz w:w="11906" w:h="16838"/><w:pgMar w:top="1134" w:right="1134" w:bottom="1134" '
        'w:left="1701" w:header="567" w:footer="567" w:gutter="0"/></w:sectPr></w:body></w:document>',
    }
    b = io.BytesIO()
    with zipfile.ZipFile(b, 'w', zipfile.ZIP_DEFLATED) as z:
        for n, x in tep.items():
            z.writestr(zipfile.ZipInfo(n, date_time=(2026, 1, 1, 0, 0, 0)), x.encode('utf-8'), zipfile.ZIP_DEFLATED)
    return b.getvalue()


def _byte_mac_dinh(loai: str) -> bytes:
    return _goi_docx(_noi_dung_to_trinh() if loai == 'to_trinh' else _noi_dung_pa_tong())


def tao_mau_mac_dinh(loai: str) -> Path:
    """Ghi mẫu Word mặc định của phiên bản đang chạy vào <thư mục mẫu>\\mac_dinh\\ (ghi đè mỗi lần; chỗ trống {…} lấy từ Thông tin
    dự án, đợt, số liệu các hộ). Không phải mẫu riêng: sửa thì dùng mau_de_sua."""
    p = thu_muc_mau() / 'mac_dinh' / f'{LOAI[loai][0]}.docx'
    p.parent.mkdir(parents=True, exist_ok=True)
    du = _byte_mac_dinh(loai)
    if not p.exists() or p.read_bytes() != du:
        p.write_bytes(du)
    return p

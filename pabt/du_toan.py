"""Dự toán / áp giá dự thảo kinh phí bồi thường, hỗ trợ cho dự án (hoặc dự án tương tự) theo mẫu PABT.

Bảng dự toán gồm các dòng khối lượng x đơn giá x hệ số theo mục (1 đất, 2 nhà - công trình, 3 cây trồng, 4 hỗ trợ, 5 thưởng)
và mục 6 chi phí khác tính theo % (tổ chức thực hiện bồi thường, dự phòng...). Lấy khối lượng từ:
  - dự án đang mở / một file .pabt khác (gom các dòng phương án cùng hạng mục, cùng đơn giá);
  - file PABT Excel của dự án tương tự (nhập tạm rồi gom);
  - danh sách thô (Excel bất kỳ: họ tên, tờ, thửa, DT, loại đất, vị trí): gom diện tích theo loại đất + vị trí;
rồi "áp đơn giá hiện hành" theo mã danh mục (đơn giá đất tra theo NQ 28/2025 hoặc nhập). Lưu nháp ra file .pabtdt (JSON),
xuất Excel. Không phụ thuộc Qt.
"""
from __future__ import annotations

import json
import tempfile
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path

from .lap_pa import DanhMuc, bo_dau
from .tien import D, KHONG, chuoi, lam_tron, so_vn, tien_bang_chu, vn

DUOI = '.pabtdt'
TEN_MUC = {1: 'Bồi thường về đất', 2: 'Bồi thường, hỗ trợ nhà, công trình xây dựng, vật kiến trúc',
           3: 'Bồi thường, hỗ trợ cây trồng, vật nuôi', 4: 'Các khoản hỗ trợ', 5: 'Thưởng bàn giao mặt bằng',
           6: 'Chi phí khác'}
# theo mẫu Bảng khái toán của đơn vị: 2,5% chi phí thực hiện công tác bồi thường, 10% dự phòng (tính trên tổng cộng mục 1-5)
CP_MAC_DINH = [('Chi phí thực hiện công tác bồi thường', '2.5'), ('Phí dự phòng', '10')]
TEN_MUC_KT = {1: 'Bồi thường về đất', 2: 'Nhà và công trình xây dựng', 3: 'Cây trồng', 4: 'Các chính sách hỗ trợ',
              5: 'Thưởng bàn giao mặt bằng trước thời hạn'}
LA_MA = ['I', 'II', 'III', 'IV', 'V', 'VI']


@dataclass
class DongDT:
    muc: int
    ten: str
    dvt: str = ''
    khoi_luong: object = KHONG
    don_gia: object = KHONG
    he_so: object = D(1)              # hệ số K x tỷ lệ bồi thường
    ma: str = ''
    can_cu: str = ''
    ghi_chu: str = ''
    phan_tram: object = None          # mục 6: % của tổng mục 1-5

    def __post_init__(self):
        self.khoi_luong, self.don_gia, self.he_so = D(self.khoi_luong), D(self.don_gia), D(self.he_so)
        if self.phan_tram not in (None, ''):
            self.phan_tram = D(self.phan_tram)
        else:
            self.phan_tram = None


@dataclass
class DuToan:
    ten: str = ''
    dia_ban: str = ''
    nguon: str = ''
    lamtron: int = -3
    dong: list = field(default_factory=list)
    ngay: str = ''
    dia_chi: str = ''                 # địa chỉ dự án trên Bảng khái toán (trống: dùng địa bàn)

    # ---------------------------------------------- tính
    def thanh_tien(self, d: DongDT) -> object:
        if d.muc == 6 and d.phan_tram is not None:
            return lam_tron(self.co_so_phan_tram() * d.phan_tram / 100, self.lamtron)
        return lam_tron(d.khoi_luong * d.don_gia * d.he_so, self.lamtron)

    def co_so_phan_tram(self):
        return sum((lam_tron(d.khoi_luong * d.don_gia * d.he_so, self.lamtron) for d in self.dong if d.muc != 6), KHONG)

    def tong_muc(self, muc: int):
        return sum((self.thanh_tien(d) for d in self.dong if d.muc == muc), KHONG)

    @property
    def tong(self):
        return sum((self.thanh_tien(d) for d in self.dong), KHONG)

    def sap_xep(self) -> None:
        self.dong.sort(key=lambda d: d.muc)

    # ---------------------------------------------- lưu / mở
    def luu(self, file) -> Path:
        p = Path(file)
        if p.suffix.lower() != DUOI:
            p = p.with_suffix(DUOI)
        du = dict(phien_ban=1, ten=self.ten, dia_ban=self.dia_ban, dia_chi=self.dia_chi, nguon=self.nguon, lamtron=self.lamtron,
                  ngay=datetime.now().strftime('%d/%m/%Y %H:%M'),
                  dong=[{k: (chuoi(v) if k in ('khoi_luong', 'don_gia', 'he_so') or (k == 'phan_tram' and v is not None) else v)
                         for k, v in asdict(d).items()} for d in self.dong])
        p.write_text(json.dumps(du, ensure_ascii=False, indent=1), encoding='utf-8')
        return p

    @classmethod
    def mo(cls, file) -> 'DuToan':
        du = json.loads(Path(file).read_text(encoding='utf-8'))
        return cls(ten=du.get('ten', ''), dia_ban=du.get('dia_ban', ''), dia_chi=du.get('dia_chi', ''), nguon=du.get('nguon', ''),
                   lamtron=int(du.get('lamtron', -3)), ngay=du.get('ngay', ''),
                   dong=[DongDT(**x) for x in du.get('dong', [])])

    # ---------------------------------------------- thêm dòng
    def them_chi_phi_mac_dinh(self) -> None:
        co = {bo_dau(d.ten) for d in self.dong if d.muc == 6}
        for ten, pt in CP_MAC_DINH:
            if bo_dau(ten) not in co:
                self.dong.append(DongDT(6, ten, '%', phan_tram=pt, can_cu='Tỷ lệ tạm tính - điều chỉnh theo quy định áp dụng'))


# ---------------------------------------------------------------- lấy khối lượng
def tu_du_an(con, ds_ma_ho: list | None = None, ten: str = '') -> DuToan:
    """Gom các dòng phương án của dự án (cùng mục, hạng mục, đơn giá, hệ số) thành dòng dự toán."""
    from .nghiep_vu import BoiCanh, doc_tat_ca_phuong_an, tinh_pa
    bc = BoiCanh.tu(con)
    da = con.execute('SELECT ten, cap_dia_ban, ten_dia_ban FROM du_an WHERE id = 1').fetchone()
    ten_ld = {r['ma'].upper(): r['ten'] for r in con.execute('SELECT ma, ten FROM dm_loaidat')}
    dt = DuToan(ten=ten or (da['ten'] if da else ''), dia_ban=f'{da["cap_dia_ban"]} {da["ten_dia_ban"]}'.strip() if da else '',
                lamtron=bc.lamtron)
    gom = {}
    thuong = KHONG
    so_ho = 0
    # phương án các hộ cần lấy: một lần đọc (3 truy vấn), theo thứ tự hộ - thay cho doc_phuong_an từng hộ (N+1)
    tat_ca = doc_tat_ca_phuong_an(con, ds_ma_ho)
    for pa in tat_ca.values():
        k = tinh_pa(pa, bc)
        if k.co_phuong_an:
            so_ho += 1
        thuong += k.muc[5]
        for d in pa.dat:
            from .nghiep_vu import so_vi_tri
            vt = so_vi_tri(d.vi_tri) or d.vi_tri
            khoa = (1, d.loai_dat.upper(), vt, d.gia_bang_gia * d.he_so_k, d.ty_le)
            x = gom.get(khoa)
            if x is None:
                ten_ld_d = ten_ld.get(d.loai_dat.upper(), d.loai_dat)
                if not bo_dau(ten_ld_d).startswith('dat'):
                    ten_ld_d = 'Đất ' + ten_ld_d
                ten_dong = f'{ten_ld_d} ({d.loai_dat})' + (f' - vị trí {vt}' if vt else '')
                x = gom[khoa] = DongDT(1, ten_dong, 'm²', KHONG, d.gia_bang_gia * d.he_so_k, d.ty_le, d.loai_dat,
                                       'Giá đất theo bảng giá x hệ số K của dự án')
            x.khoi_luong += d.dien_tich
        for muc in (2, 3, 4):
            for d in pa.khoan[muc]:
                khoa = (muc, d.ma or bo_dau(d.ten), d.dvt, d.don_gia, d.ty_le)
                x = gom.get(khoa)
                if x is None:
                    x = gom[khoa] = DongDT(muc, d.ten, d.dvt, KHONG, d.don_gia, d.ty_le, d.ma or d.ma_tuong_duong,
                                           d.can_cu_gia or (d.quy_cach if muc == 4 else ''))
                x.khoi_luong += d.so_luong
    dt.dong = list(gom.values())
    if thuong > 0:
        dt.dong.append(DongDT(5, 'Thưởng bàn giao mặt bằng (theo biểu thưởng của dự án)', 'đồng', 1, thuong))
    dt.sap_xep()
    dt.nguon = f'{dt.ten}: {so_ho} hộ có phương án'
    return dt


def tu_file_pabt(file, ten: str = '') -> DuToan:
    from . import csdl
    con = csdl.mo(file, chi_doc=True)
    try:
        dt = tu_du_an(con, ten=ten)
    finally:
        con.close()
    dt.nguon = f'File dự án {Path(file).name} - ' + dt.nguon
    return dt


def tu_excel_pabt(file_excel, ten: str = '') -> DuToan:
    """Dự án tương tự trên file PABT Excel (.xlsm mẫu PABT): nhập tạm vào file dự án tạm rồi gom khối lượng."""
    from . import nhap_excel, nhap_tho
    with tempfile.TemporaryDirectory() as td:
        tam = Path(td) / 'tam.pabt'
        if nhap_tho.la_file_pabt(file_excel):
            bc = nhap_excel.nhap(file_excel, tam)
        else:
            bc = nhap_tho.nhap(file_excel, tam, ten or Path(file_excel).stem)
        if bc.loi:
            from .lap_pa import LoiNhap
            raise LoiNhap('Không đọc được file: ' + '; '.join(bc.loi))
        dt = tu_file_pabt(tam, ten or Path(file_excel).stem)
    dt.nguon = f'File Excel {Path(file_excel).name}'
    return dt


def tu_ds_tho(file_excel, ten: str = '') -> DuToan:
    """Danh sách thô (họ tên, tờ, thửa, DT thu hồi, loại đất, vị trí): gom diện tích theo loại đất + vị trí (chưa có giá)."""
    from .du_an_moi import dong_tu_excel
    dong, nhan = dong_tu_excel(file_excel)[:2]
    gom = {}
    for r in dong:
        ld = str(r.get('loai_dat') or '').strip().upper() or '?'
        vt = str(r.get('vi_tri') or '').strip()
        x = gom.setdefault((ld, vt), DongDT(1, f'Đất {ld}' + (f' - vị trí {vt}' if vt else ''), 'm²', KHONG, KHONG, D(1), ld))
        try:
            x.khoi_luong += D(r.get('dt_thu_hoi') or 0)
        except ValueError:
            pass
    dt = DuToan(ten=ten or Path(file_excel).stem, dong=list(gom.values()),
                nguon=f'Danh sách thô {Path(file_excel).name}: {len(dong)} dòng')
    return dt


def ap_don_gia_hien_hanh(dt: DuToan, dm: DanhMuc) -> list:
    """Thay đơn giá các dòng mục 2, 3 (và mục 4 có đơn giá tiền) theo danh mục hiện hành (tra theo mã).
    Trả danh sách thay đổi [(tên, giá cũ, giá mới)]."""
    doi = []
    for d in dt.dong:
        if d.muc not in (2, 3, 4) or not d.ma:
            continue
        m = dm.lay(d.ma)
        if m is None or m.don_gia is None or m.don_gia == d.don_gia:
            continue
        if d.muc == 4 and m.don_gia < 100:           # mục 4: cột đơn giá danh mục là hệ số (HT09...) -> giữ
            continue
        doi.append((d.ten, d.don_gia, m.don_gia))
        d.don_gia = m.don_gia
        d.can_cu = f'Đơn giá hiện hành {m.ma}' + (f'; {m.can_cu}' if m.can_cu else '')
    return doi


# ---------------------------------------------------------------- xuất Excel
def xuat_excel(dt: DuToan, file_ra) -> Path:
    import openpyxl
    from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
    from openpyxl.utils import get_column_letter
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = 'Du toan'
    mong = Side(style='thin', color='808080')
    vien = Border(left=mong, right=mong, top=mong, bottom=mong)
    ws.cell(1, 1, 'DỰ TOÁN KINH PHÍ BỒI THƯỜNG, HỖ TRỢ, TÁI ĐỊNH CƯ (DỰ THẢO)').font = Font(bold=True, size=14)
    ws.cell(2, 1, f'Dự án: {dt.ten}' + (f'  -  {dt.dia_ban}' if dt.dia_ban else ''))
    ws.cell(3, 1, f'Nguồn khối lượng: {dt.nguon}  -  lập lúc {datetime.now():%H:%M %d/%m/%Y}')
    for i in (1, 2, 3):
        ws.merge_cells(start_row=i, start_column=1, end_row=i, end_column=9)
    dau = ['STT', 'Hạng mục', 'ĐVT', 'Khối lượng', 'Đơn giá (đồng)', 'Hệ số / tỷ lệ', 'Thành tiền (đồng)', 'Mã', 'Căn cứ, ghi chú']
    for c, t in enumerate(dau, start=1):
        o = ws.cell(5, c, t)
        o.font = Font(bold=True, color='FFFFFF')
        o.fill = PatternFill('solid', fgColor='1F4E79')
        o.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
        o.border = vien
    r = 6
    nhom = PatternFill('solid', fgColor='DDEBF7')
    for muc in (1, 2, 3, 4, 5, 6):
        ds = [d for d in dt.dong if d.muc == muc]
        if not ds:
            continue
        for c, v in enumerate([str(muc), TEN_MUC[muc].upper(), '', '', '', '', float(dt.tong_muc(muc)), '', ''], start=1):
            o = ws.cell(r, c, v)
            o.font = Font(bold=True)
            o.fill = nhom
            o.border = vien
            if c == 7:
                o.number_format = '#,##0'
        r += 1
        for i, d in enumerate(ds, start=1):
            if d.muc == 6 and d.phan_tram is not None:
                gia = [f'{muc}.{i}', d.ten, '%', float(d.phan_tram), float(dt.co_so_phan_tram()), None,
                       float(dt.thanh_tien(d)), d.ma, (d.can_cu + ('; ' if d.can_cu and d.ghi_chu else '') + d.ghi_chu)
                       + ' (% x tổng mục 1-5)']
            else:
                gia = [f'{muc}.{i}', d.ten, d.dvt, float(d.khoi_luong), float(d.don_gia), float(d.he_so), float(dt.thanh_tien(d)),
                       d.ma, d.can_cu + ('; ' if d.can_cu and d.ghi_chu else '') + d.ghi_chu]
            for c, v in enumerate(gia, start=1):
                o = ws.cell(r, c, v)
                o.border = vien
                if c in (4, 5, 7):
                    o.number_format = '#,##0.##' if c == 4 else '#,##0'
                if c == 6:
                    o.number_format = '0.###'
                if c in (2, 9):
                    o.alignment = Alignment(wrap_text=True, vertical='top')
            r += 1
    for c, v in enumerate(['', 'TỔNG CỘNG', '', '', '', '', float(dt.tong), '', ''], start=1):
        o = ws.cell(r, c, v)
        o.font = Font(bold=True)
        o.border = vien
        if c == 7:
            o.number_format = '#,##0'
    ws.cell(r + 1, 2, f'Bằng chữ: {tien_bang_chu(dt.tong)}.').font = Font(italic=True)
    ws.cell(r + 2, 2, 'Dự toán mang tính dự thảo, khối lượng và đơn giá cần đối chiếu hồ sơ kiểm đếm và văn bản áp dụng.').font = \
        Font(italic=True, color='808080')
    for c, w in enumerate([7, 60, 8, 12, 15, 10, 18, 9, 50], start=1):
        ws.column_dimensions[get_column_letter(c)].width = w
    ws.freeze_panes = 'A6'
    ws.page_setup.orientation = 'landscape'
    ws.page_setup.fitToWidth = 1
    ws.page_setup.fitToHeight = 0
    ws.sheet_properties.pageSetUpPr.fitToPage = True
    p = Path(file_ra)
    p.parent.mkdir(parents=True, exist_ok=True)
    wb.save(p)
    return p


def _noi_lap(dt: DuToan) -> str:
    """Địa danh ở dòng 'Trị An, ngày … tháng … năm …': tên xã / phường của địa bàn dự toán (bỏ chữ Xã / Phường)."""
    import re
    t = ' '.join(str(dt.dia_ban or '').split())
    t = re.sub(r'(?i)^(xã|phường|thị trấn|đặc khu)\s+', '', t)
    return t or 'Trị An'


def xuat_khai_toan(dt: DuToan, file_ra, pdf: bool = False) -> dict:
    """Bảng khái toán theo mẫu của đơn vị (I đất, II nhà - công trình, III cây trồng, IV chính sách hỗ trợ; Tổng cộng,
    chi phí thực hiện công tác bồi thường %, phí dự phòng %, TỔNG DỰ ƯỚC KINH PHÍ). pdf=True: xuất thêm PDF qua Microsoft Excel.
    Trả dict(excel=Path, pdf=Path|None, loi=[...])."""
    import openpyxl
    from openpyxl.styles import Alignment, Border, Font, Side
    from openpyxl.utils import get_column_letter
    from . import to_chuc
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = 'Khai toan'
    TM = 'Times New Roman'

    def f(**k):
        return Font(name=TM, size=k.pop('size', 12), **k)
    mong = Side(style='thin', color='000000')
    vien = Border(left=mong, right=mong, top=mong, bottom=mong)
    giua = Alignment(horizontal='center', vertical='center', wrap_text=True)
    trai = Alignment(horizontal='left', vertical='center', wrap_text=True)
    phai = Alignment(horizontal='right', vertical='center')
    so_cot = 8
    # ---- quốc hiệu, tên đơn vị
    ws.merge_cells('A1:C1')
    ws['A1'] = to_chuc.TRUC_THUOC.upper()
    ws['A1'].font = f(size=11)
    ws.merge_cells('A2:C2')
    ws['A2'] = to_chuc.MAC_DINH.get('don_vi_tieu_de', '').upper() or to_chuc.TEN
    ws['A2'].font = f(size=12, bold=True, underline='single')
    ws.merge_cells('D1:H1')
    ws['D1'] = 'CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM'
    ws['D1'].font = f(size=12, bold=True)
    ws.merge_cells('D2:H2')
    ws['D2'] = 'Độc lập - Tự do - Hạnh phúc'
    ws['D2'].font = f(size=13, bold=True, underline='single')
    ws.merge_cells('D3:H3')
    ws['D3'] = f'{_noi_lap(dt)}, ngày       tháng       năm {datetime.now():%Y}'
    ws['D3'].font = f(size=12, italic=True)
    for o in ('A1', 'A2', 'D1', 'D2', 'D3'):
        ws[o].alignment = giua
    # ---- tiêu đề
    ws.merge_cells('A5:H5')
    ws['A5'] = 'BẢNG KHÁI TOÁN'
    ws['A5'].font = f(size=15, bold=True)
    ws['A5'].alignment = giua
    ws.merge_cells('A6:H6')
    ws['A6'] = f'Dự án: {dt.ten}'
    ws['A6'].font = f(bold=True)
    ws.merge_cells('A7:H7')
    ws['A7'] = f'Địa chỉ: {dt.dia_chi or dt.dia_ban}'
    # (từ 0.9.12 bỏ dòng "TỔNG DỰ ƯỚC KINH PHÍ: … (Bằng chữ …)" ở đây: tổng và bằng chữ ghi cuối bảng)
    ws.merge_cells('A8:E8')
    ws['A8'] = 'Theo chi tiết sau:'
    ws.merge_cells('F8:H8')
    ws['F8'] = 'Đơn vị tính: đồng'
    ws['F8'].font = f(italic=True)
    ws['F8'].alignment = phai
    for r in (6, 7):
        ws.cell(r, 1).alignment = trai
        ws.row_dimensions[r].height = 20
    from .in_an import vua_chu                          # tên dự án / địa chỉ dài: dòng cao vừa đủ, không đè chữ
    for r in (6, 7):
        vua_chu(ws, (r, 1, 8, r), them=4)
    # ---- bảng
    dau = ['STT', 'Tên tài sản', 'ĐVT', 'Số lượng', 'Đơn giá dự kiến bồi thường', 'Tỷ lệ (%)', 'Thành tiền', 'Ghi chú']
    r = 9
    for c, t in enumerate(dau, start=1):
        o = ws.cell(r, c, t)
        o.font = f(bold=True)
        o.alignment = giua
        o.border = vien
    ws.row_dimensions[r].height = 36

    def ghi(gia: list, dam: bool = False, nghieng: bool = False):
        nonlocal r
        r += 1
        for c, v in enumerate(gia, start=1):
            o = ws.cell(r, c, v)
            o.font = f(bold=dam, italic=nghieng)
            o.border = vien
            o.alignment = giua if c in (1, 3, 6) else (trai if c in (2, 8) else phai)
            if c in (4, 5, 7) and isinstance(v, float):
                o.number_format = '#,##0.##' if c == 4 else '#,##0'
        return r
    stt = 0
    for muc in (1, 2, 3, 4, 5):
        ds = [d for d in dt.dong if d.muc == muc]
        if not ds and muc != 1:                         # mục I đất luôn có, nằm trên cùng (chưa nhập đất: 0 đồng)
            continue
        dvt = {d.dvt for d in ds} or {'m²'}
        tong_kl = float(sum((d.khoi_luong for d in ds), KHONG)) if len(dvt) == 1 and muc in (1, 3) else None
        ghi([LA_MA[stt], TEN_MUC_KT[muc], dvt.pop() if tong_kl is not None else '', tong_kl, None, None,
             float(dt.tong_muc(muc)), None], dam=True)
        stt += 1
        for i, d in enumerate(ds, start=1):
            ghi([i, d.ten, d.dvt, float(d.khoi_luong), float(d.don_gia), f'{so_vn(d.he_so * 100)}%', float(dt.thanh_tien(d)),
                 '; '.join(x for x in (d.can_cu, d.ghi_chu) if x) or None])
    co_so = dt.co_so_phan_tram()
    ghi(['', 'Tổng cộng', None, None, None, None, float(co_so), None], dam=True)
    for d in (x for x in dt.dong if x.muc == 6):
        pt = d.phan_tram if d.phan_tram is not None else KHONG
        ghi(['', f'{d.ten} {so_vn(pt)}%' if d.phan_tram is not None else d.ten, None, None, None, None,
             float(dt.thanh_tien(d)), '; '.join(x for x in (d.can_cu, d.ghi_chu) if x) or None])
    ghi(['', 'TỔNG DỰ ƯỚC KINH PHÍ', None, None, None, None, float(dt.tong), None], dam=True)
    r += 1
    ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=so_cot)
    ws.cell(r, 1, f'(Bằng chữ: {tien_bang_chu(dt.tong)}.)').font = f(italic=True)
    for c, w in enumerate([6, 40, 8, 13, 16, 9, 18, 34], start=1):
        ws.column_dimensions[get_column_letter(c)].width = w
    ws.page_setup.orientation = 'landscape'
    ws.page_setup.paperSize = ws.PAPERSIZE_A4
    ws.page_setup.fitToWidth = 1
    ws.page_setup.fitToHeight = 0
    ws.sheet_properties.pageSetUpPr.fitToPage = True
    ws.print_title_rows = '9:9'
    ws.page_margins.left = ws.page_margins.right = 0.4
    p = Path(file_ra)
    p.parent.mkdir(parents=True, exist_ok=True)
    wb.save(p)
    kq = dict(excel=p, pdf=None, loi=[])
    if pdf:
        from .in_an import chay_excel
        q = p.with_suffix('.pdf')
        kq['loi'] = chay_excel([(p, q)], 'pdf')
        if q.exists():
            kq['pdf'] = q
    return kq


def mo_ta_tong(dt: DuToan) -> str:
    return '  ·  '.join(f'{m}. {vn(dt.tong_muc(m))}' for m in (1, 2, 3, 4, 5, 6) if any(d.muc == m for d in dt.dong)) + \
        f'  ·  TỔNG: {vn(dt.tong)} đồng'

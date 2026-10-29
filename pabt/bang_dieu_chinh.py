"""BẢNG TỔNG HỢP PHƯƠNG ÁN ĐIỀU CHỈNH (1.0.15) - theo mẫu "mẫu bảng tổng hợp phương án điều chỉnh.pdf" của người dùng.

Excel A3 ngang dựng TRỰC TIẾP bằng mã (openpyxl) - không dùng file mẫu trong thư mục mẫu in (nhúng sẵn trong chương trình). Bố cục:
  I.   Phương án đã được phê duyệt tại QĐ … (lần bị thay thế của từng hộ)
  II.  Phương án đề nghị điều chỉnh (lần điều chỉnh)
  III. Chênh lệch sau điều chỉnh (II - I)
  IV.  Tổng giá trị đã phê duyệt tại QĐ … (cả quyết định, mọi hộ) + kinh phí tổ chức thực hiện (tỷ lệ theo loại dự án, phân bổ 85 / 15)
  V.   Tổng giá trị sau điều chỉnh (IV + III) + kinh phí
Mỗi hộ nhiều thửa: STT, họ tên, địa chỉ, các cột tiền gộp dọc cả hộ; tờ, thửa, loại đất, diện tích riêng từng thửa.
Không phụ thuộc Qt (cỡ dòng ước theo số ký tự).
"""
from __future__ import annotations

import math
from pathlib import Path

from . import du_lieu_in
from . import an_toan as _an_toan
from . import lan_pa, nghiep_vu
from .tien import D, KHONG, lam_tron

TIEU_DE_COT = ('STT', 'Họ và tên', 'Địa chỉ', 'Số tờ', 'Số thửa', 'Loại đất thu hồi', 'Tổng', 'Tổng', 'Trong đó đất trồng lúa',
               'Tổng', 'Trong đó đất ở', 'Giá trị bồi thường, hỗ trợ về đất', 'Giá trị hỗ trợ nhà, công trình xây dựng và tài sản khác',
               'Giá trị hỗ trợ cây trồng', 'Đào tạo, chuyển đổi nghề và tìm kiếm việc làm', 'Hỗ trợ ổn định đời sống',
               'Thưởng chấp hành bàn giao mặt bằng trước thời hạn', 'Tổng cộng giá trị bồi thường, hỗ trợ', 'Phương án tái định cư',
               'Ghi chú')
RONG_COT = (5, 24, 28, 6, 7, 7, 11, 9, 9, 9, 9, 14, 16, 15, 13, 13, 13, 17, 16, 20)
COT_TIEN = (12, 13, 14, 15, 16, 17, 18)                 # cột (1 = A) chứa số tiền
COT_DT = (7, 8, 9, 10, 11)
CO_CHU = 10
LE_CM = dict(trai=1.5, phai=1.0, tren=1.5, duoi=1.5)


def ho_dieu_chinh(con, ds_ma_ho=None) -> list:
    """[(mã hộ, LanPA điều chỉnh mới nhất chưa bị thay)] của các hộ có phương án điều chỉnh theo thứ tự hộ."""
    kq = []
    chon = None if ds_ma_ho is None else set(ds_ma_ho)
    for r in con.execute('SELECT ma_ho FROM ho ORDER BY thu_tu, ma_ho'):
        m = r[0]
        if chon is not None and m not in chon:
            continue
        dc = [x for x in lan_pa.ds_lan(con, m) if x.la_dieu_chinh and not x.bi_thay_boi]
        if dc:
            kq.append((m, dc[-1]))
    return kq


def co_dieu_chinh(con) -> bool:
    try:
        return bool(con.execute("SELECT 1 FROM pa_lan WHERE thay_the > 0 LIMIT 1").fetchone())
    except Exception:
        return False


class _SoLieuHo:
    """Số liệu một hộ ở một phương án (lần): tiền từng cột, thửa (tờ, thửa, loại, 4 diện tích)."""

    def __init__(self, con, bc, ma_ho: int, lan: int):
        from . import in_an
        pa = nghiep_vu.doc_phuong_an(con, ma_ho, lan=lan)
        kq = nghiep_vu.tinh_lan(con, ma_ho, lan, bc)
        self.tien = in_an._tien_ho_bth(pa, kq, bc)
        self.pa, self.kq = pa, kq
        self.thua = []
        for t in bc.thua_cua(ma_ho):
            nn, lua, o, pnn = in_an._dt_thua_bth(pa, t['ma_thua'])
            dt = du_lieu_in.dien_tich_dong_dat(KHONG, t)
            self.thua.append(dict(so_to=t.get('so_to', ''), so_thua=t.get('so_thua', ''), loai_dat=t.get('loai_dat', ''),
                                  dt=dt, nn=nn, lua=lua, o=o, pnn=pnn))


def _ho_ten_dia_chi(con, ma_ho: int) -> tuple:
    da = du_lieu_in._thong_tin_du_an(con)
    tt = du_lieu_in._thong_tin_ho(con, ma_ho, da)
    ten = ' '.join(str(tt.get('ho_ten') or '').split())
    dia_chi = ' '.join(str(tt.get('dia_chi') or '').split())
    return ten, dia_chi, str(tt.get('tai_dinh_cu') or '').strip()


def _so_dong(chu: str, rong: float) -> int:
    chu = str(chu or '')
    if not chu:
        return 1
    return sum(max(1, math.ceil(len(d) * 1.05 / max(1.0, rong - 1))) for d in chu.split('\n'))


def lap(con, file_ra, ds_ma_ho=None, du_thao: bool | None = None, so_pa: str = '', ngay_pa: str = '') -> Path:
    """Lập bảng tổng hợp điều chỉnh cho các hộ có phương án điều chỉnh (ds_ma_ho None = tất cả). Trả đường dẫn file .xlsx.
    LoiNhap khi không hộ nào có phương án điều chỉnh."""
    import openpyxl
    from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
    from openpyxl.utils import get_column_letter
    from . import in_an, lap_pa as lp
    from .lap_pa import LoiNhap
    ds = ho_dieu_chinh(con, ds_ma_ho)
    if not ds:
        raise LoiNhap('Chưa có hộ nào có phương án điều chỉnh để lập bảng tổng hợp điều chỉnh.')
    bc = nghiep_vu.BoiCanh.tu(con)
    da = du_lieu_in._thong_tin_du_an(con)
    n_cot = len(TIEU_DE_COT)

    # ---- số liệu: lần cũ (bị thay) / lần điều chỉnh từng hộ + quyết định gốc
    du_lieu = []
    qd_goc = {}                                         # {qd_id: (so, ngay)}
    for m, dc in ds:
        goc = lan_pa.lan_cua(con, m, dc.thay_the)
        for q in goc.qd:
            qd_goc[q['qd_id']] = (q['so'], q['ngay'])
        ten, dia_chi, tdc = _ho_ten_dia_chi(con, m)
        du_lieu.append(dict(ma=m, ten=ten, dia_chi=dia_chi, tdc=tdc, cu=_SoLieuHo(con, bc, m, goc.lan),
                            moi=_SoLieuHo(con, bc, m, dc.lan), ly_do=dc.ghi_chu, da_duyet=bool(goc.qd)))
    tong_qd = _tong_quyet_dinh(con, list(qd_goc))
    # 26/10/2026: hộ điều chỉnh từ phương án CHƯA phê duyệt (dự thảo) - không có trong quyết định nào: cộng số liệu phương án đã lập
    # của hộ đó vào mục IV (nền trước điều chỉnh), để V = IV + III vẫn đúng tổng sau điều chỉnh
    chua = [x for x in du_lieu if not x['da_duyet']]
    for x in chua:
        for k in tong_qd['tien']:
            tong_qd['tien'][k] += x['cu'].tien.get(k, KHONG)
        tong_qd['dt'] += sum((t['dt'] for t in x['cu'].thua), KHONG)

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = 'BANG_TONG_HOP_DIEU_CHINH'
    tn = Side(style='thin')
    vien = Border(left=tn, right=tn, top=tn, bottom=tn)
    xam = PatternFill('solid', fgColor='D9D9D9')

    def font(dam=False, nghieng=False, co=CO_CHU):
        return Font(name='Times New Roman', size=co, bold=dam, italic=nghieng)
    for i, r in enumerate(RONG_COT, start=1):
        ws.column_dimensions[get_column_letter(i)].width = r

    # ---- đầu văn bản
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=9)
    ws.merge_cells(start_row=2, start_column=1, end_row=2, end_column=9)
    ws.merge_cells(start_row=1, start_column=12, end_row=1, end_column=n_cot)
    ws.merge_cells(start_row=2, start_column=12, end_row=2, end_column=n_cot)
    for (r, c, v, d) in ((1, 1, str(da['DON_VI_CAP_TREN'] or '').upper(), False), (2, 1, str(da['DON_VI_TIEU_DE'] or '').upper(), True),
                         (1, 12, 'CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM', True), (2, 12, 'Độc lập - Tự do - Hạnh phúc', True)):
        ws.cell(r, c, v).font = font(d)
        ws.cell(r, c).alignment = Alignment(horizontal='center', vertical='center')
    if du_thao:
        ws.merge_cells(start_row=3, start_column=1, end_row=3, end_column=9)
        ws.cell(3, 1, '(DỰ THẢO)').font = font()
        ws.cell(3, 1).alignment = Alignment(horizontal='center')
    du_an = str(da['du_an'] or '').upper()
    dong_tieu = ['BẢNG TỔNG HỢP THÔNG TIN VỀ ĐIỀU CHỈNH PHƯƠNG ÁN BỒI THƯỜNG, HỖ TRỢ', f'DỰ ÁN {du_an}' if du_an else '']
    if so_pa or ngay_pa:
        dong_tieu.append(f'(Đính kèm Phương án số {so_pa or "……"}{("/" + da["ky_hieu_so"]) if da["ky_hieu_so"] else ""} '
                         f'ngày {ngay_pa or "……"})')
    r = 5
    for k, v in enumerate(x for x in dong_tieu if x):
        ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=n_cot)
        ws.cell(r, 1, v).font = font(dam=k < 2, nghieng=k >= 2, co=CO_CHU + 2)
        ws.cell(r, 1).alignment = Alignment(horizontal='center', vertical='center')
        ws.row_dimensions[r].height = 22
        r += 1
    r += 1

    # ---- tiêu đề cột (3 dòng + dòng số cột)
    r_td = r
    cao_td = (22, 24, 70)
    o_td = []                                           # (dòng đầu, cột đầu, dòng cuối, cột cuối, chữ) - dòng tính từ 0
    for c in (1, 2, 3, 4, 5, 6, 12, 13, 14, 17, 18, 19, 20):
        o_td.append((0, c, 2, c, TIEU_DE_COT[c - 1]))
    o_td += [(0, 7, 1, 7, 'DT đất thu hồi (m2)'), (2, 7, 2, 7, 'Tổng'),
             (0, 8, 0, 11, 'DT đất bồi thường (m2)'), (1, 8, 1, 9, 'Nông nghiệp'), (1, 10, 1, 11, 'Phi nông nghiệp'),
             (2, 8, 2, 8, 'Tổng'), (2, 9, 2, 9, 'Trong đó đất trồng lúa'), (2, 10, 2, 10, 'Tổng'), (2, 11, 2, 11, 'Trong đó đất ở'),
             (0, 15, 0, 16, 'Giá trị về các chính sách hỗ trợ'), (1, 15, 2, 15, TIEU_DE_COT[14]), (1, 16, 2, 16, TIEU_DE_COT[15])]
    for d1, c1, d2, c2, chu in o_td:
        if (d1, c1) != (d2, c2):
            ws.merge_cells(start_row=r_td + d1, start_column=c1, end_row=r_td + d2, end_column=c2)
        ws.cell(r_td + d1, c1, chu)
    for rr in range(r_td, r_td + 3):
        ws.row_dimensions[rr].height = cao_td[rr - r_td]
        for c in range(1, n_cot + 1):
            ce = ws.cell(rr, c)
            ce.font = font(dam=True)
            ce.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
            ce.border = vien
    r = r_td + 3
    ws.row_dimensions[r].height = 15
    for c in range(1, n_cot + 1):
        ce = ws.cell(r, c, c)
        ce.font = font(nghieng=True, co=CO_CHU - 1)
        ce.alignment = Alignment(horizontal='center')
        ce.border = vien
    r_dau_du_lieu = r + 1
    r = r_dau_du_lieu

    def dong_chu(chu_khoi, nen=True):
        nonlocal r
        ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=n_cot)
        ce = ws.cell(r, 1, chu_khoi)
        ce.font = font(dam=True)
        for c in range(1, n_cot + 1):
            ws.cell(r, c).fill = xam
            ws.cell(r, c).border = vien
        ce.alignment = Alignment(vertical='center', wrap_text=True)
        ws.row_dimensions[r].height = 18
        r += 1

    def ghi_o(rr, c, v, dam=False, can='right', dinh_dang=None, nghieng=False):
        ce = ws.cell(rr, c, v)
        ce.font = font(dam=dam, nghieng=nghieng)
        ce.alignment = Alignment(horizontal=can, vertical='center', wrap_text=True)
        ce.border = vien
        if dinh_dang:
            ce.number_format = dinh_dang
        return ce

    def khoi_ho(kieu: str, stt: int, x: dict):
        """Ghi một hộ ở khối kieu ('cu' / 'moi' / 'chenh'); nhiều thửa: gộp dọc các cột hộ + cột tiền."""
        nonlocal r
        thua = x['moi'].thua or x['cu'].thua or [dict(so_to='', so_thua='', loai_dat='', dt=KHONG, nn=KHONG, lua=KHONG, o=KHONG,
                                                     pnn=KHONG)]
        n = len(thua)
        tien = {}
        for k in ('tien_dat', 'tien_tai_san', 'tien_cay_vat_nuoi', 'ho_tro_dao_tao', 'ho_tro_on_dinh', 'thuong', 'tong'):
            moi, cu = x['moi'].tien.get(k, KHONG), x['cu'].tien.get(k, KHONG)
            tien[k] = (moi - cu) if kieu == 'chenh' else (cu if kieu == 'cu' else moi)
        cot_tien = dict(zip(COT_TIEN, ('tien_dat', 'tien_tai_san', 'tien_cay_vat_nuoi', 'ho_tro_dao_tao', 'ho_tro_on_dinh',
                                       'thuong', 'tong')))
        ghi_chu = ''
        if kieu == 'moi' and x['ly_do']:
            ghi_chu = ' '.join(str(x['ly_do']).split())
        cao_chu = max(_so_dong(x['ten'], RONG_COT[1]), _so_dong(x['dia_chi'], RONG_COT[2]),
                      _so_dong(x['tdc'] if kieu != 'chenh' else '', RONG_COT[18]), _so_dong(ghi_chu, RONG_COT[19]))
        cao = max(cao_chu * 13.5 / n + 4, 20)
        for k, t in enumerate(thua):
            rr = r + k
            ws.row_dimensions[rr].height = cao
            ghi_o(rr, 4, t['so_to'], can='center')
            ghi_o(rr, 5, t['so_thua'], can='center')
            ghi_o(rr, 6, t['loai_dat'], can='center')
            for c, v in zip(COT_DT, (t['dt'], t['nn'], t['lua'], t['pnn'] + t['o'], t['o'])):
                ghi_o(rr, c, float(v) if v else None, dinh_dang='#,##0.0#;-#,##0.0#;"-"')
        for c in [1, 2, 3, *COT_TIEN, 19, 20]:
            if n > 1:
                ws.merge_cells(start_row=r, start_column=c, end_row=r + n - 1, end_column=c)
            for k in range(n):
                ws.cell(r + k, c).border = vien
        ghi_o(r, 1, stt, can='center')
        ghi_o(r, 2, x['ten'], can='left')
        ghi_o(r, 3, x['dia_chi'], can='left')
        for c, k in cot_tien.items():
            v = tien[k]
            ghi_o(r, c, int(v) if v else None, dam=c == 18, dinh_dang='#,##0;-#,##0;"-"')
        ghi_o(r, 19, x['tdc'] if kieu != 'chenh' else None, can='center')
        ghi_o(r, 20, ghi_chu, can='left', nghieng=True)
        r += n

    def tong_cong(chu_tong, tien, dt=None, nen=True):
        nonlocal r
        ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=6)
        ghi_o(r, 1, chu_tong, dam=True, can='center')
        for c in range(2, 7):
            ws.cell(r, c).border = vien
        for c in COT_DT:
            ghi_o(r, c, float(dt[c]) if dt and dt.get(c) else None, dam=True, dinh_dang='#,##0.0#;-#,##0.0#;"-"')
        for c, k in zip(COT_TIEN, ('tien_dat', 'tien_tai_san', 'tien_cay_vat_nuoi', 'ho_tro_dao_tao', 'ho_tro_on_dinh', 'thuong',
                                   'tong')):
            ghi_o(r, c, int(tien[k]) if tien.get(k) else None, dam=True, dinh_dang='#,##0;-#,##0;"-"')
        ghi_o(r, 19, None)
        ghi_o(r, 20, None)
        ws.row_dimensions[r].height = 20
        r += 1

    def dong_kinh_phi(tong: D):
        """Kinh phí tổ chức thực hiện (tỷ lệ theo loại dự án) + phân bổ + TỔNG CỘNG sau kinh phí."""
        nonlocal r
        from . import dia_phuong
        loai, tl, _ = lp.kinh_phi_to_chuc(con)
        kp = lam_tron(tong * tl / 100, -3)
        so_tl = str(tl).replace('.', ',')
        don_vi = in_an.rut_gon_don_vi(da['DON_VI_LAP'] or da['don_vi_lap'])
        xa = ' '.join(f'{str(da["cap_dia_ban"] or "").lower()} {da["ten_dia_ban"]}'.split())
        dong = [(f'Kinh phí đảm bảo cho việc tổ chức thực hiện công tác bồi thường, hỗ trợ, tái định cư {so_tl}%:', kp, True, 'right')]
        for j, (ten, ty) in enumerate(dia_phuong.phan_bo_kinh_phi()):
            v = lam_tron(kp * ty / 100, -3)
            if j == 0:
                nhan = f'- Kinh phí cho Tổ chức làm nhiệm vụ bồi thường, hỗ trợ, tái định cư ({don_vi}) {str(ty).replace(".", ",")}%:'
            elif j == 1:
                nhan = f'- Kinh phí cho UBND {xa} {str(ty).replace(".", ",")}%:'
            else:
                nhan = f'- {ten} {str(ty).replace(".", ",")}%:'
            dong.append((nhan, v, False, 'right'))
        for nhan, v, dam, _ in dong:
            ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=17)
            ghi_o(r, 1, nhan, dam=dam, can='right' if dam else 'left', nghieng=not dam)
            for c in range(2, 18):
                ws.cell(r, c).border = vien
            ghi_o(r, 18, int(v), dam=True, dinh_dang='#,##0;-#,##0;"-"')
            ghi_o(r, 19, None)
            ghi_o(r, 20, None)
            ws.row_dimensions[r].height = 18
            r += 1
        ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=17)
        ghi_o(r, 1, 'TỔNG CỘNG', dam=True, can='center')
        for c in range(2, 18):
            ws.cell(r, c).border = vien
        ghi_o(r, 18, int(tong + kp), dam=True, dinh_dang='#,##0;-#,##0;"-"')
        ghi_o(r, 19, None)
        ghi_o(r, 20, None)
        ws.row_dimensions[r].height = 20
        r += 1

    def cong_khoi(kieu):
        tong = {k: KHONG for k in ('tien_dat', 'tien_tai_san', 'tien_cay_vat_nuoi', 'ho_tro_dao_tao', 'ho_tro_on_dinh', 'thuong',
                                   'tong')}
        for x in du_lieu:
            for k in tong:
                moi, cu = x['moi'].tien.get(k, KHONG), x['cu'].tien.get(k, KHONG)
                tong[k] += (moi - cu) if kieu == 'chenh' else (cu if kieu == 'cu' else moi)
        return tong

    so_qd = '; '.join(f'Quyết định số {s or "……"} ngày {n or "……"}' for s, n in qd_goc.values())
    if so_qd and chua:
        ten_cu = f'đã được phê duyệt tại {so_qd} và phương án đã lập chưa phê duyệt ({len(chua)} hộ)'
    elif so_qd:
        ten_cu = f'đã được phê duyệt tại {so_qd}'
    else:
        ten_cu = 'đã lập (chưa phê duyệt)'
    for kieu, ten_khoi, nhan in (('cu', f'I. Phương án {ten_cu}', 'cu'),
                                 ('moi', 'II. Phương án đề nghị điều chỉnh', 'moi'),
                                 ('chenh', 'III. Chênh lệch sau điều chỉnh (II - I)', 'chenh')):
        dong_chu(ten_khoi)
        for i, x in enumerate(du_lieu, start=1):
            khoi_ho(kieu, i, x)
        tong_cong('TỔNG CỘNG ' + {'cu': 'I', 'moi': 'II', 'chenh': 'III'}[kieu], cong_khoi(kieu))
    # ---- IV. tổng đã phê duyệt cả quyết định, V. sau điều chỉnh
    chenh = cong_khoi('chenh')
    dong_chu(f'IV. Tổng giá trị {ten_cu}' if not so_qd or chua else f'IV. Tổng giá trị đã phê duyệt tại {so_qd}')
    tong_cong('TỔNG CỘNG', tong_qd['tien'], dt={7: tong_qd['dt']})
    dong_kinh_phi(tong_qd['tien']['tong'])
    dong_chu('V. Tổng giá trị sau khi điều chỉnh (IV + III)')
    sau = {k: tong_qd['tien'].get(k, KHONG) + chenh.get(k, KHONG) for k in chenh}
    tong_cong('TỔNG CỘNG', sau, dt={7: tong_qd['dt']})
    dong_kinh_phi(sau['tong'])
    r_cuoi = r - 1

    # ---- in: A3 ngang, vừa bề ngang, lặp tiêu đề cột
    ws.page_setup.orientation = 'landscape'
    ws.page_setup.paperSize = 8
    ws.page_setup.fitToWidth = 1
    ws.page_setup.fitToHeight = 0
    ws.sheet_properties.pageSetUpPr = openpyxl.worksheet.properties.PageSetupProperties(fitToPage=True)
    cm = 1 / 2.54
    ws.page_margins.left, ws.page_margins.right = LE_CM['trai'] * cm, LE_CM['phai'] * cm
    ws.page_margins.top, ws.page_margins.bottom = LE_CM['tren'] * cm, LE_CM['duoi'] * cm
    ws.print_title_rows = f'{r_td}:{r_td + 3}'
    ws.print_area = f'A1:{get_column_letter(n_cot)}{r_cuoi}'
    ws.print_options.horizontalCentered = True
    file_ra = Path(file_ra)
    file_ra.parent.mkdir(parents=True, exist_ok=True)
    tam = file_ra.with_name(file_ra.name + '.tmp')
    _an_toan.luu_xlsx(wb, tam)
    tam.replace(file_ra)
    return file_ra


def _tong_quyet_dinh(con, ds_qd: list) -> dict:
    """Tổng tiền + diện tích thu hồi của MỌI hộ trong các quyết định gốc (qd_ho): {'tien': {...}, 'dt': Decimal}."""
    tien = {k: KHONG for k in ('tien_dat', 'tien_tai_san', 'tien_cay_vat_nuoi', 'ho_tro_dao_tao', 'ho_tro_on_dinh', 'thuong', 'tong')}
    dt = KHONG
    if not ds_qd:
        return dict(tien=tien, dt=dt)
    ma_ho = set()
    for q in ds_qd:
        for r in con.execute('SELECT * FROM qd_ho WHERE qd_id = ?', (q,)):
            ma_ho.add(r['ma_ho'])
            tien['tien_dat'] += D(r['tien_dat'] or 0)
            tien['tien_tai_san'] += D(r['tien_tai_san'] or 0)
            tien['tien_cay_vat_nuoi'] += D(r['tien_cay'] or 0)
            tien['thuong'] += D(r['tien_thuong'] or 0)
            tien['tong'] += D(r['so_tien'] or 0)
            tien['ho_tro_on_dinh'] += D(r['tien_ho_tro'] or 0)       # qd_ho không tách đào tạo / ổn định: gộp cột hỗ trợ ở cột ổn định
    for m in ma_ho:
        for r in con.execute('SELECT dt_thu_hoi FROM thua WHERE ma_ho = ?', (m,)):
            try:
                dt += D(r['dt_thu_hoi'] or 0)
            except Exception:
                pass
    return dict(tien=tien, dt=dt)

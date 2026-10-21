"""Phương án chi tiết bản Word (.docx) theo thể thức Nghị định 30/2020/NĐ-CP (người dùng 21/10/2026: Excel không cắt đôi được một dòng
bảng qua hai trang - dòng ghi chú / nguồn gốc dài đẩy cả dòng sang trang sau, trang trước hở).

Cùng số liệu với bản Excel (in_an.dong_chi_tiet, _thong_tin_du_an, _thong_tin_ho, lần phương án, chế độ dự thảo / chính thức), dựng
bằng XML thuần (van_ban_trinh._goi_docx - không cần python-docx, không cần Word để tạo file):
  - A4 dọc, lề trái 30 mm, phải 15 mm, trên 20 mm, dưới 20 mm (LE_MM); Times New Roman.
  - Quốc hiệu, tiêu ngữ, tên cơ quan, số, địa danh / ngày: bảng ẩn viền hai cột; thông tin chủ sử dụng: bảng ẩn viền.
  - Bảng mục III: hàng tiêu đề cột w:tblHeader (Word lặp đầu mọi trang); dòng số liệu có chữ dài (ghi chú, tên > DAI_CHO_TACH ký
    tự) w:cantSplit = 0 (Word cắt đôi qua trang - trang trước lấp đầy), dòng ngắn / đề mục = 1; dòng thưởng, TỔNG CỘNG, mục IV, khối
    chữ ký cantSplit = 1 và keepNext (không tách rời, chữ ký không đứng trơ một trang).
  - Bản dự thảo: "(DỰ THẢO)" dưới số, không số / ngày phương án, không khối chữ ký.
Không ghi cố định tên đơn vị / người ký: lấy từ Thông tin dự án (to_chuc.MAC_DINH khi trống) như bản Excel.
"""
from __future__ import annotations

import re
from pathlib import Path

from .ho_so import dau_dong
from .van_ban_trinh import _goi_docx, _xml

LE_MM = dict(trai=30, phai=15, tren=20, duoi=20)        # lề A4 theo NĐ 30/2020/NĐ-CP (mm)
KHO_A4 = (11906, 16838)                                 # twip
# cỡ chữ theo Phụ lục I NĐ 30/2020 (người dùng 21/10/2026): cơ quan, quốc hiệu, số 12; tiêu ngữ, địa danh / ngày, trích yếu, nội dung 13;
# tên loại văn bản 14; bảng 12, ghi chú bảng 11,5
CO_CHU = 13                                             # cỡ chữ văn bản (NĐ 30: 13 - 14)
CO_CO_QUAN = 12                                         # tên cơ quan chủ quản / ban hành, quốc hiệu, số ký hiệu
CO_TEN_LOAI = 14                                        # "PHƯƠNG ÁN CHI TIẾT"
CO_BANG = 12                                            # chữ trong bảng mục III
CO_GHI_CHU = 11.5                                       # cột ghi chú
TRICH_YEU = 'BỒI THƯỜNG, HỖ TRỢ VÀ TÁI ĐỊNH CƯ KHI NHÀ NƯỚC THU HỒI ĐẤT'   # NĐ 30: chữ "VÀ", không ký tự "&"
DONG_DOAN = 276                                         # đoạn Mục II: giãn dòng 1,15
SAU_DOAN = 100                                          # cách đoạn 5 pt
THUT_DAU = 567                                          # thụt đầu dòng 1 cm
THUT_TREO = 360                                         # đoạn gạch đầu dòng: thụt lề treo
# bề rộng 8 cột bảng mục III (tỷ lệ) - STT, tên, ĐVT, số lượng, đơn giá, tỷ lệ, thành tiền, ghi chú
TY_LE_COT = (7, 25, 7, 10, 12, 8, 14, 17)
DAI_CHO_TACH = 80                                       # dòng số liệu có tên / ghi chú dài hơn (ký tự): cho Word cắt đôi qua trang
TIEU_DE_COT = ('STT', 'Tên tài sản', 'ĐVT', 'Số lượng', 'Đơn giá', 'Tỷ lệ (%)', 'Thành tiền (đồng)', 'Ghi chú')


def twip(mm: float) -> int:
    return int(round(mm / 25.4 * 1440))


def rong_trang() -> int:
    """Bề rộng vùng chữ (twip) giữa lề trái / phải."""
    return KHO_A4[0] - twip(LE_MM['trai']) - twip(LE_MM['phai'])


def _r(chu, dam: bool = False, nghieng: bool = False, co: float = 0, gach: bool = False) -> str:
    """Một đoạn chữ cùng kiểu; co = cỡ chữ pt (w:sz tính nửa pt: 13 pt -> 26); gach = gạch chân nét liền đúng độ dài chữ."""
    pr = ('<w:b/><w:bCs/>' if dam else '') + ('<w:i/><w:iCs/>' if nghieng else '') + ('<w:u w:val="single"/>' if gach else '') + \
         (f'<w:sz w:val="{int(round(co * 2))}"/><w:szCs w:val="{int(round(co * 2))}"/>' if co else '')
    return f'<w:r>{"<w:rPr>" + pr + "</w:rPr>" if pr else ""}<w:t xml:space="preserve">{_xml(chu)}</w:t></w:r>'


def _p(*chay, can: str = 'both', truoc: int = 0, sau: int = 0, dau_dong: int = 0, dong: int = 276, giu_sau: bool = False,
       giu_dong: bool = False, trai: int = 0, treo: int = 0) -> str:
    """Đoạn: can left / center / right / both; truoc / sau twip; dong (240 = đơn); giu_sau = keepNext; giu_dong = keepLines;
    dau_dong = thụt dòng đầu; trai + treo = thụt lề treo (dòng đầu lùi ra treo twip so với các dòng sau)."""
    thut = (f'<w:ind w:left="{trai}" w:hanging="{treo}"/>' if treo else
            f'<w:ind w:firstLine="{dau_dong}"/>' if dau_dong else '')
    giu = ('<w:keepNext/>' if giu_sau else '') + ('<w:keepLines/>' if giu_dong else '')
    return (f'<w:p><w:pPr>{giu}<w:spacing w:before="{truoc}" w:after="{sau}" w:line="{dong}" w:lineRule="auto"/>{thut}'
            f'<w:jc w:val="{can}"/></w:pPr>{"".join(chay)}</w:p>')


def _o(noi_dung: str, rong: int, nhap: int = 1, doc: str = 'center', dong_doc: str | None = None, vien: bool = True) -> str:
    """Ô bảng: noi_dung = các w:p; nhap = số cột gộp ngang (gridSpan); dong_doc 'restart' / 'continue' = gộp dọc (vMerge)."""
    pr = f'<w:tcW w:w="{rong}" w:type="dxa"/>' + (f'<w:gridSpan w:val="{nhap}"/>' if nhap > 1 else '') + \
        ('<w:vMerge w:val="restart"/>' if dong_doc == 'restart' else '<w:vMerge/>' if dong_doc == 'continue' else '') + \
        ('' if vien else '<w:tcBorders><w:top w:val="nil"/><w:left w:val="nil"/><w:bottom w:val="nil"/><w:right w:val="nil"/>'
                         '</w:tcBorders>') + f'<w:vAlign w:val="{doc}"/>'
    return f'<w:tc><w:tcPr>{pr}</w:tcPr>{noi_dung or _p()}</w:tc>'


def _hang(o: list, tieu_de: bool = False, khong_tach: bool = False) -> str:
    """Dòng bảng: tieu_de = w:tblHeader (lặp đầu trang); khong_tach = w:cantSplit (không cắt đôi qua trang) - dòng số liệu thường
    cantSplit = 0: Word được cắt đôi dòng dài sang trang sau."""
    pr = ('<w:tblHeader/>' if tieu_de else '') + f'<w:cantSplit w:val="{1 if (khong_tach or tieu_de) else 0}"/>'
    return f'<w:tr><w:trPr>{pr}</w:trPr>{"".join(o)}</w:tr>'


def _bang(hang: list, rong: list, vien: bool = True) -> str:
    b = ''.join(f'<w:{k} w:val="{"single" if vien else "nil"}" w:sz="4" w:space="0" w:color="000000"/>'
                for k in ('top', 'left', 'bottom', 'right', 'insideH', 'insideV'))
    luoi = ''.join(f'<w:gridCol w:w="{x}"/>' for x in rong)
    return (f'<w:tbl><w:tblPr><w:tblW w:w="{sum(rong)}" w:type="dxa"/><w:jc w:val="center"/><w:tblBorders>{b}</w:tblBorders>'
            f'<w:tblLayout w:type="fixed"/><w:tblCellMar><w:top w:w="28" w:type="dxa"/><w:left w:w="57" w:type="dxa"/>'
            f'<w:bottom w:w="28" w:type="dxa"/><w:right w:w="57" w:type="dxa"/></w:tblCellMar></w:tblPr>'
            f'<w:tblGrid>{luoi}</w:tblGrid>{"".join(hang)}</w:tbl>')


def rong_cot() -> list:
    tong = rong_trang()
    ds = [tong * t // sum(TY_LE_COT) for t in TY_LE_COT]
    ds[1] += tong - sum(ds)
    return ds


def _so(v, muc=None, loai: str = 'tien') -> str:
    """Số in trong bảng như bản Excel: tiền '#,##0', số lượng kiểu kế toán theo mục, tỷ lệ 'x%'."""
    from .tien import D, so_luong_vn, so_vn, vn
    if v is None or v == '':
        return ''
    if isinstance(v, str):
        return v
    x = D(v)
    if loai == 'ty_le':
        return f'{so_vn(x * 100)}%'
    if loai == 'sl':
        return so_luong_vn(x, muc)
    return vn(x)


def _ngay_chu(ngay: str, nam) -> str:
    m = re.fullmatch(r'(\d{1,2})/(\d{1,2})/(\d{4})', str(ngay or '').strip())
    if m:
        return f'ngày {int(m.group(1)):02d} tháng {int(m.group(2)):02d} năm {m.group(3)}'
    return f'ngày ...... tháng ..... năm {nam}'


def noi_dung_chi_tiet(con, ma_ho: int, bc=None, du_thao: bool = False, pa=None, lan=None) -> str:
    """XML thân văn bản (w:body không sectPr) phương án chi tiết một hộ."""
    from . import dia_phuong, in_an, nghiep_vu
    from .ho_so import la_to_chuc
    da = in_an._thong_tin_du_an(con)
    da['ky_hieu_so'] = in_an.ky_hieu_cua_ho(con, ma_ho, da['ky_hieu_so'])
    lan = in_an.chon_lan_in(con, ma_ho, lan)
    pa_truoc = None
    if lan is not None:
        if pa is None:
            pa = nghiep_vu.doc_phuong_an(con, ma_ho, lan=lan)
        pa_truoc = nghiep_vu.doc_phuong_an(con, ma_ho, den_lan=lan - 1)
    dong, _ = in_an.dong_chi_tiet(con, ma_ho, bc, pa, pa_truoc)
    ttho = in_an._thong_tin_ho(con, ma_ho, da)
    if lan is not None and lan > 1:
        from .lan_pa import lan_cua
        x = lan_cua(con, ma_ho, lan)
        ttho['so_pa'], ttho['ngay_pa'] = x.so_pa, x.ngay_pa
    if du_thao:
        ttho['so_pa'], ttho['ngay_pa'] = '', ''
    w = rong_trang()
    co = CO_CHU
    # ---- quốc hiệu, tiêu ngữ, cơ quan, số, ngày (bảng ẩn viền 2 cột)
    dia_danh = str(dia_phuong.lay('ban_in.dia_danh_ngay', in_an.DIA_DANH_NGAY_MAC_DINH) or da['ten_dia_ban'] or '').strip()
    so = f'Số: {ttho["so_pa"]}/{da["ky_hieu_so"]}' if ttho['so_pa'] else f'Số:          /{da["ky_hieu_so"]}'
    # NĐ 30 Phụ lục I: cơ quan chủ quản 12 in hoa đứng; cơ quan ban hành 12 in hoa đứng đậm, đường kẻ dưới 1/3 - 1/2 dòng chữ; số,
    # "(DỰ THẢO)" 12 đứng; quốc hiệu 12 in hoa đậm; tiêu ngữ 13 đậm, gạch dưới đúng độ dài chữ; địa danh / ngày 13 nghiêng
    ten_cq = str(da['DON_VI_TIEU_DE'] or '').upper()
    ke = '_' * max(6, min(20, len(ten_cq) // 2 + 2))     # gạch dưới (cỡ 12) ~ nửa dòng tên cơ quan
    trai = ''.join(_p(_r(x.upper(), co=CO_CO_QUAN), can='center')
                   for x in (da['DON_VI_CAP_TREN_2DONG'] or '').split('\n') if x.strip()) + \
        _p(_r(ten_cq, dam=True, co=CO_CO_QUAN), can='center') + _p(_r(ke, co=CO_CO_QUAN), can='center', dong=200) + \
        _p(_r(so, co=CO_CO_QUAN), can='center', truoc=60) + (_p(_r('(DỰ THẢO)', co=CO_CO_QUAN), can='center') if du_thao else '')
    phai = _p(_r('CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM', dam=True, co=CO_CO_QUAN), can='center') + \
        _p(_r('Độc lập - Tự do - Hạnh phúc', dam=True, co=co, gach=True), can='center') + \
        _p(_r(f'{dia_danh}, {_ngay_chu(ttho["ngay_pa"], da["nam"])}', nghieng=True, co=co), can='center', truoc=200)
    r1 = w * 45 // 100
    t = [_bang([_hang([_o(trai, r1, doc='top', vien=False), _o(phai, w - r1, doc='top', vien=False)])], [r1, w - r1], vien=False)]
    # ---- tên văn bản
    ten = 'PHƯƠNG ÁN CHI TIẾT' + (f' BỔ SUNG (LẦN {lan})' if lan is not None and lan > 1 else '')
    t += [_p(_r(ten, dam=True, co=CO_TEN_LOAI), can='center', truoc=240),
          _p(_r(TRICH_YEU, dam=True, co=co), can='center'),
          _p(_r(f'DỰ ÁN {str(da["du_an"] or "").upper()}', dam=True, co=co), can='center', sau=240)]
    # ---- I. chủ sử dụng (bảng ẩn viền: nhãn đậm | nội dung)
    to_chuc = la_to_chuc(ttho['ho_ten'])
    t.append(_p(_r('I. Tổ chức và hộ gia đình, cá nhân bị thu hồi đất, tài sản gắn liền với đất', dam=True, co=co),
                truoc=60, sau=60, giu_sau=True))
    hang_i = [(in_an.NHAN_TO_CHUC if to_chuc else 'Họ và tên:', ttho['ho_ten'])]
    if not to_chuc and ttho['cccd']:
        hang_i.append(('Số CCCD:', ttho['cccd']))
    hang_i.append((in_an.NHAN_DIA_CHI_TO_CHUC if to_chuc else 'Địa chỉ thường trú:', ttho['dia_chi']))
    if not to_chuc and ttho['dien_thoai']:
        hang_i.append(('Số điện thoại:', ttho['dien_thoai']))
    c1, c0 = w * 28 // 100, w * 5 // 100
    t.append(_bang([_hang([_o(_p(), c0, vien=False), _o(_p(_r(n, dam=True, co=co), can='left'), c1, vien=False),
                           _o(_p(_r(v, co=co), can='left'), w - c0 - c1, vien=False)]) for n, v in hang_i],
                   [c0, c1, w - c0 - c1], vien=False))
    # ---- II. nguồn gốc: mỗi đoạn logic MỘT w:p (in_an._thong_tin_ho đã nối xuống dòng cứng giữa câu từng thửa - ho_so.
    # lam_sach_doan_van), căn đều, giãn dòng 1,15, cách đoạn 5 pt; đoạn thường thụt đầu dòng 1 cm, đoạn gạch đầu dòng thụt lề
    # treo; không w:br - Word tự bẻ dòng theo lề
    t.append(_p(_r(in_an.TIEU_DE_MUC_II, dam=True, co=co), truoc=120, sau=60, giu_sau=True))
    for doan in (x for x in str(ttho['nguon_goc'] or '').split('\n') if x.strip()):
        if dau_dong(doan):
            t.append(_p(_r(doan, co=co), dong=DONG_DOAN, sau=SAU_DOAN, trai=THUT_TREO, treo=THUT_TREO))
        else:
            t.append(_p(_r(doan, co=co), dong=DONG_DOAN, sau=SAU_DOAN, dau_dong=THUT_DAU))
    # ---- III. bảng tính toán
    t.append(_p(_r('III. Bảng tính toán bồi thường, hỗ trợ', dam=True, co=co), truoc=120, sau=60, giu_sau=True))
    rong = rong_cot()
    hang = [_hang([_o(_p(_r(x, dam=True, co=CO_BANG), can='center'), rong[i]) for i, x in enumerate(TIEU_DE_COT)], tieu_de=True)]
    # ghi chú mục 1 trùng nhau ở các dòng đất liền nhau: gộp dọc (như in_an.gop_ghi_chu_dat)
    gop_gc = {}
    i = 1 if dong and dong[0][0] == 'H' else 0
    nhom = []
    while i <= len(dong):
        x = dong[i] if i < len(dong) else None
        chu = (x[1][7] or '') if x is not None and x[0] == 'I' else None
        if nhom and (chu is None or chu != dong[nhom[0]][1][7] or not chu):
            if len(nhom) > 1:
                gop_gc[nhom[0]] = 'restart'
                for k in nhom[1:]:
                    gop_gc[k] = 'continue'
            nhom = []
        if x is None or x[0] == 'H':
            break
        if chu:
            nhom.append(i)
        i += 1
    muc_sl = None
    for i, x in enumerate(dong):
        loai, gt = x[0], x[1]
        cach_tinh = x[2] if len(x) > 2 else ''
        if loai == 'H':
            muc_sl = 2 if str(gt[0]) == str(nghiep_vu.so_muc(2)) else None
        dam = loai in ('H', 'T')
        if loai == 'T':
            o = [_o(_p(_r(gt[1], dam=True, co=CO_BANG), can='center', giu_sau=True), sum(rong[:6]), nhap=6),
                 _o(_p(_r(_so(gt[6]), dam=True, co=CO_BANG), can='right', giu_sau=True), rong[6]),
                 _o(_p(giu_sau=True), rong[7])]
            hang.append(_hang(o, khong_tach=True))
            continue

        giu = loai == 'R'                               # dòng ngay trước TỔNG CỘNG đi liền khối cuối (không để tổng + chữ ký trơ)

        def oc(chu, k, can, dam_o=dam, co_o=CO_BANG):
            return _o(_p(_r(chu, dam=dam_o, co=co_o), can=can, giu_sau=giu) if chu else _p(giu_sau=giu), rong[k])
        o = [oc('' if gt[0] is None else str(gt[0]), 0, 'center'), oc(gt[1] or '', 1, 'left')]
        if cach_tinh:
            o.append(_o(_p(_r(cach_tinh, dam=dam, co=CO_BANG), can='center', giu_sau=giu), sum(rong[2:6]), nhap=4))
        else:
            o += [oc(gt[2] or '', 2, 'center'), oc(_so(gt[3], muc_sl, 'sl'), 3, 'right'), oc(_so(gt[4]), 4, 'right'),
                  oc(_so(gt[5], loai='ty_le'), 5, 'center')]
        o.append(oc(_so(gt[6]), 6, 'right', dam_o=dam or loai == 'R'))
        gd = gop_gc.get(i)
        o.append(_o(_p(_r(gt[7] or '', co=CO_GHI_CHU), can='center', giu_sau=giu) if gd != 'continue' and gt[7]
                    else _p(giu_sau=giu), rong[7], dong_doc=gd))
        # dòng ngắn (đề mục, tên / ghi chú vài dòng) không cắt đôi; dòng có chữ dài (ghi chú, tên thửa…) Word được cắt qua trang
        dai = loai == 'I' and max(len(str(gt[1] or '')), len(str(gt[7] or '')), len(cach_tinh or '')) > DAI_CHO_TACH
        hang.append(_hang(o, khong_tach=not dai))
    # IV. tái định cư (dòng cuối bảng)
    hang.append(_hang([_o(_p(_r('IV', dam=True, co=CO_BANG), can='center', giu_sau=True), rong[0]),
                       _o(_p(_r(in_an.NHAN_TDC, dam=True, co=CO_BANG),
                             _r(' ' + str(ttho['tai_dinh_cu'] or '').strip(), co=CO_BANG), can='both', giu_sau=not du_thao),
                          sum(rong[1:]), nhap=7)], khong_tach=True))
    t.append(_bang(hang, rong))
    # ---- chữ ký (một dòng bảng ẩn viền, không tách; như mẫu Excel: ngày ở đầu văn bản) - bản dự thảo không có
    if not du_thao:
        c = [w * 3 // 10, w * 3 // 10, w - 2 * (w * 3 // 10)]

        def ky(chuc_vu, ten):
            return _p(_r(chuc_vu, dam=True, co=co), can='center') + ''.join(_p(can='center') for _ in range(4)) + \
                _p(_r(ten or '', dam=True, co=co), can='center')
        t.append(_p(truoc=120, giu_sau=True))
        t.append(_bang([_hang([_o(ky('LẬP BIỂU', da['nguoi_lap']), c[0], doc='top', vien=False),
                               _o(ky('KIỂM TRA', da['nguoi_kiem_tra']), c[1], doc='top', vien=False),
                               _o(ky(da['CHUC_VU_KY'], da['nguoi_ky']), c[2], doc='top', vien=False)], khong_tach=True)],
                       c, vien=False))
    return ''.join(t)


def sect_pr() -> str:
    """Khổ A4 dọc, lề NĐ 30 (LE_MM)."""
    return (f'<w:sectPr><w:pgSz w:w="{KHO_A4[0]}" w:h="{KHO_A4[1]}"/><w:pgMar w:top="{twip(LE_MM["tren"])}" '
            f'w:right="{twip(LE_MM["phai"])}" w:bottom="{twip(LE_MM["duoi"])}" w:left="{twip(LE_MM["trai"])}" w:header="567" '
            f'w:footer="567" w:gutter="0"/></w:sectPr>')


def xuat_chi_tiet_docx(con, ma_ho: int, file_ra, bc=None, du_thao: bool = False, pa=None, lan=None) -> Path:
    """Ghi phương án chi tiết một hộ ra file .docx (thể thức NĐ 30). Trả đường dẫn file."""
    file_ra = Path(file_ra)
    file_ra.parent.mkdir(parents=True, exist_ok=True)
    du = _goi_docx(noi_dung_chi_tiet(con, ma_ho, bc, du_thao, pa, lan), sect_pr())
    tam = file_ra.with_name(file_ra.name + '.tmp')
    tam.write_bytes(du)
    tam.replace(file_ra)
    return file_ra

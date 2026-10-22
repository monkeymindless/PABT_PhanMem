"""Phương án chi tiết bản Word (.docx) theo thể thức Nghị định 30/2020/NĐ-CP (người dùng 21/10/2026: Excel không cắt đôi được một dòng
bảng qua hai trang - dòng ghi chú / nguồn gốc dài đẩy cả dòng sang trang sau, trang trước hở).

Cùng số liệu với bản Excel (in_an.dong_chi_tiet, _thong_tin_du_an, _thong_tin_ho, lần phương án, chế độ dự thảo / chính thức), dựng
bằng XML thuần (van_ban_trinh._goi_docx - không cần python-docx, không cần Word để tạo file):
  - A4 dọc, lề trái 30 mm, phải 15 mm, trên 20 mm, dưới 20 mm (LE_MM); Times New Roman.
  - Quốc hiệu, tiêu ngữ, tên cơ quan, số, địa danh / ngày: bảng ẩn viền hai cột; thông tin chủ sử dụng: bảng ẩn viền.
  - Bảng mục III: hàng tiêu đề cột w:tblHeader (Word lặp đầu mọi trang); dòng số liệu có chữ dài (ghi chú, tên > DAI_CHO_TACH ký
    tự) w:cantSplit = 0 (Word cắt đôi qua trang - trang trước lấp đầy), dòng ngắn / đề mục = 1; dòng thưởng, TỔNG CỘNG, mục IV, khối
    chữ ký (dòng cuối của chính bảng này, ẩn viền) cantSplit = 1 và keepNext (không tách rời, chữ ký không đứng trơ một trang).
  - Cỡ chữ (22/10/2026): cơ quan, quốc hiệu, số 13; tiêu ngữ, ngày, trích yếu (hai dòng), dự án, nội dung, bảng, chữ ký 14; tên
    loại 15. Mục II giãn dòng đơn, cách đoạn 6 pt; tiêu đề mục III không keepNext - in tiếp ngay dưới mục II khi còn chỗ.
  - Bản dự thảo: "(DỰ THẢO)" dưới số, không số / ngày phương án, không khối chữ ký.
Không ghi cố định tên đơn vị / người ký: lấy từ Thông tin dự án (to_chuc.MAC_DINH khi trống) như bản Excel.
"""
from __future__ import annotations

import math
import re
from pathlib import Path

from .ho_so import dau_dong
from .van_ban_trinh import _goi_docx, _xml

LE_MM = dict(trai=30, phai=15, tren=20, duoi=20)        # lề A4 theo NĐ 30/2020/NĐ-CP (mm)
KHO_A4 = (11906, 16838)                                 # twip
# cỡ chữ (người dùng 22/10/2026, theo NĐ 30/2020 cỡ 13 - 14): tên cơ quan, quốc hiệu, số ký hiệu 13; tiêu ngữ, địa danh / ngày,
# trích yếu, tên dự án, nội dung (mục I, II, bảng mục III), khối chữ ký 14; tên loại văn bản 15
CO_CHU = 14                                             # cỡ chữ văn bản
CO_CO_QUAN = 13                                         # tên cơ quan chủ quản / ban hành, quốc hiệu, số ký hiệu
CO_TEN_LOAI = 15                                        # "PHƯƠNG ÁN CHI TIẾT"
CO_BANG = 14                                            # chữ trong bảng mục III
CO_GHI_CHU = 14                                         # cột ghi chú (cùng cỡ nội dung)
TRICH_YEU = 'BỒI THƯỜNG, HỖ TRỢ VÀ TÁI ĐỊNH CƯ KHI NHÀ NƯỚC THU HỒI ĐẤT'   # NĐ 30: chữ "VÀ", không ký tự "&"
# trích yếu 14 pt đậm rộng ~480 pt > vùng chữ 468 pt: hai dòng ngắt đúng nghĩa (Word tự ngắt để "ĐẤT" trơ một dòng)
TRICH_YEU_DONG = ('BỒI THƯỜNG, HỖ TRỢ VÀ TÁI ĐỊNH CƯ', 'KHI NHÀ NƯỚC THU HỒI ĐẤT')
# bảng đầu văn bản (cơ quan | quốc hiệu) rộng hơn vùng chữ, lấn vào lề trái / phải (22/10/2026, mẫu PA_01 người dùng gửi): 13 pt
# vùng chữ 468 pt không đủ cho "TRUNG TÂM PHÁT TRIỂN QUỸ ĐẤT" (~225 pt) một dòng cạnh quốc hiệu "CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM"
# đậm (~269 pt) - trước đây tên cơ quan bẻ 3 dòng. Lề giấy còn 30 - 12 = 18 mm trái, 15 - 8 = 7 mm phải (máy in để >= 5 mm)
LAN_LE_DAU_MM = (12, 8)                                 # (trái, phải) mm bảng đầu lấn vào lề
RONG_QUOC_HIEU = 5700                                   # twip (285 pt) cột quốc hiệu: 269 pt chữ + lề ô; còn lại cho cột cơ quan
RONG_KY_TU = 0.6                                        # ước bề rộng một ký tự in hoa Times New Roman (x cỡ chữ; đậm x 1,05)
DONG_DOAN = 240                                         # đoạn Mục II: giãn dòng đơn
SAU_DOAN = 120                                          # cách đoạn / gạch đầu dòng 6 pt
THUT_DAU = 567                                          # thụt đầu dòng 1 cm
THUT_TREO = 360                                         # đoạn gạch đầu dòng: thụt lề treo
# bề rộng 8 cột bảng mục III (phần nghìn) - STT, tên, ĐVT, số lượng, đơn giá, tỷ lệ, thành tiền, ghi chú: chỉ dùng khi không có số
# liệu (rong_cot() không đối số). Bản in thật: rong_cot(chu_cot) theo NỘI DUNG từng hộ (22/10/2026 - cột ghi chú cố định 14% làm ô
# ghi chú "Đất do UBND xã … Điều 101 Luật Đất đai" cao nửa trang): cột STT / ĐVT / số lượng / đơn giá / tỷ lệ / thành tiền vừa số dài
# nhất (và từ dài nhất của tiêu đề, không dưới COT_TOI_THIEU), phần còn lại chia tên : ghi chú theo CHIA_TEN_GHI_CHU
TY_LE_COT = (70, 205, 75, 100, 145, 80, 185, 140)
COT_SO = (0, 2, 3, 4, 5, 6)
COT_TOI_THIEU = {0: 24, 2: 26, 3: 30, 4: 30, 5: 24, 6: 40}     # pt (từ dài nhất của tiêu đề thường rộng hơn)
CHIA_TEN_GHI_CHU = (45, 55)
DU_RONG = 1.06                                          # chừa sai số ước bề rộng chữ (Word xuất PDF bẻ dòng sớm hơn ước)
LE_O = 40                                               # lề trái / phải trong ô bảng mục III (twip = 2 pt)
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


def _o(noi_dung: str, rong: int, nhap: int = 1, doc: str = 'center', dong_doc: str | None = None, vien: bool = True,
       an_vien: tuple = ()) -> str:
    """Ô bảng: noi_dung = các w:p; nhap = số cột gộp ngang (gridSpan); dong_doc 'restart' / 'continue' = gộp dọc (vMerge);
    vien=False ẩn cả bốn cạnh, an_vien = các cạnh ẩn ('top', 'left', 'bottom', 'right')."""
    an = ('top', 'left', 'bottom', 'right') if not vien else tuple(an_vien)
    pr = f'<w:tcW w:w="{rong}" w:type="dxa"/>' + (f'<w:gridSpan w:val="{nhap}"/>' if nhap > 1 else '') + \
        ('<w:vMerge w:val="restart"/>' if dong_doc == 'restart' else '<w:vMerge/>' if dong_doc == 'continue' else '') + \
        ('<w:tcBorders>' + ''.join(f'<w:{k} w:val="nil"/>' for k in an) + '</w:tcBorders>' if an else '') + \
        f'<w:vAlign w:val="{doc}"/>'
    return f'<w:tc><w:tcPr>{pr}</w:tcPr>{noi_dung or _p()}</w:tc>'


def _hang(o: list, tieu_de: bool = False, khong_tach: bool = False) -> str:
    """Dòng bảng: tieu_de = w:tblHeader (lặp đầu trang); khong_tach = w:cantSplit (không cắt đôi qua trang) - dòng số liệu thường
    cantSplit = 0: Word được cắt đôi dòng dài sang trang sau."""
    pr = ('<w:tblHeader/>' if tieu_de else '') + f'<w:cantSplit w:val="{1 if (khong_tach or tieu_de) else 0}"/>'
    return f'<w:tr><w:trPr>{pr}</w:trPr>{"".join(o)}</w:tr>'


def _bang(hang: list, rong: list, vien: bool = True, le_o: int = 57, lui: int = 0) -> str:
    """lui (twip): bảng bắt đầu lùi ra ngoài lề trái chừng này (w:tblInd âm, canh trái) - bảng đầu văn bản lấn lề."""
    b = ''.join(f'<w:{k} w:val="{"single" if vien else "nil"}" w:sz="4" w:space="0" w:color="000000"/>'
                for k in ('top', 'left', 'bottom', 'right', 'insideH', 'insideV'))
    luoi = ''.join(f'<w:gridCol w:w="{x}"/>' for x in rong)
    vi_tri = f'<w:jc w:val="left"/><w:tblInd w:w="{-lui}" w:type="dxa"/>' if lui else '<w:jc w:val="center"/>'
    return (f'<w:tbl><w:tblPr><w:tblW w:w="{sum(rong)}" w:type="dxa"/>{vi_tri}<w:tblBorders>{b}</w:tblBorders>'
            f'<w:tblLayout w:type="fixed"/><w:tblCellMar><w:top w:w="28" w:type="dxa"/><w:left w:w="{le_o}" w:type="dxa"/>'
            f'<w:bottom w:w="28" w:type="dxa"/><w:right w:w="{le_o}" w:type="dxa"/></w:tblCellMar></w:tblPr>'
            f'<w:tblGrid>{luoi}</w:tblGrid>{"".join(hang)}</w:tbl>')


def _rong_uoc(chu: str, co: float, dam: bool = False) -> float:
    """Bề rộng (pt) ước của dòng chữ in hoa Times New Roman - không cần Qt (bản Word dựng cả khi không có giao diện)."""
    return len(chu) * co * RONG_KY_TU * (1.05 if dam else 1.0)


def _ngat_can_bang(chu: str, rong_pt: float, co: float, dam: bool = False) -> list:
    """Dòng chữ rộng hơn rong_pt: ngắt ở ranh giới từ sao cho hai dòng cân nhau nhất (Word tự ngắt thì từ cuối trơ một dòng -
    "TRUNG TÂM PHÁT TRIỂN QUỸ / ĐẤT"). Vừa một dòng, hoặc không chỗ ngắt nào cho hai dòng vừa: giữ nguyên (Word tự ngắt)."""
    if _rong_uoc(chu, co, dam) <= rong_pt:
        return [chu]
    tu = chu.split()
    ung = [(' '.join(tu[:i]), ' '.join(tu[i:])) for i in range(1, len(tu))]
    ung = [(a, b) for a, b in ung if max(_rong_uoc(a, co, dam), _rong_uoc(b, co, dam)) <= rong_pt]
    if not ung:
        return [chu]
    return list(min(ung, key=lambda x: max(_rong_uoc(x[0], co, dam), _rong_uoc(x[1], co, dam))))


# bề rộng ký tự Times New Roman (phần cỡ chữ): chữ số 0,5; dấu chấm / phẩy 0,25; % 0,833; chữ hoa ~0,72; chữ thường ~0,5
def _rong_chu(chu: str, co: float, dam: bool = False) -> float:
    """Bề rộng (pt) ước của chữ thường lẫn số (cột số, tiêu đề cột bảng mục III)."""
    w = 0.0
    for c in str(chu):
        w += (0.5 if c.isdigit() else 0.25 if c in ".,:;' " else 0.833 if c == '%' else 0.36 if c in '()/-' else
              0.72 if c.isupper() else 0.5)
    return w * co * (1.06 if dam else 1.0)


def rong_cot(chu_cot: dict | None = None) -> list:
    """Bề rộng 8 cột bảng mục III (twip). chu_cot {cột: [(chữ, đậm)]}: theo nội dung (cột số vừa chữ dài nhất, còn lại chia tên /
    ghi chú); None: tỷ lệ cố định TY_LE_COT."""
    tong = rong_trang()
    if chu_cot is None:
        ds = [tong * t // sum(TY_LE_COT) for t in TY_LE_COT]
        ds[1] += tong - sum(ds)
        return ds
    le = 2 * LE_O / 20                                  # pt lề ô hai bên
    ds = [0] * len(TIEU_DE_COT)
    for k in COT_SO:
        can = max([COT_TOI_THIEU[k]] + [_rong_chu(t, CO_BANG, True) for t in TIEU_DE_COT[k].split()] +
                  [_rong_chu(c, CO_BANG, d) * DU_RONG for c, d in chu_cot.get(k, ()) if c])
        ds[k] = int(round((can + le) * 20))
    con = tong - sum(ds)
    co_gc = any(c for c, _ in chu_cot.get(7, ()))
    toi_thieu_gc = int(round((_rong_chu('Ghi chú', CO_BANG, True) + le) * 20))
    toi_thieu_ten = int(round((max([_rong_chu(t, CO_BANG, True) for c, _ in chu_cot.get(1, ()) for t in str(c).split()] or [0])
                               + le) * 20))
    if co_gc:
        # chia tên : ghi chú sao cho các dòng bảng (cao theo ô nhiều dòng chữ hơn) thấp và đều: tổng BÌNH PHƯƠNG số dòng ước
        # nhỏ nhất - chỉ cộng số dòng thì ô ghi chú dài bị dồn thành một dòng bảng cao nửa trang
        def so_dong(chu, d, rong):
            return math.ceil(_rong_chu(chu, CO_BANG, d) * DU_RONG / max(1.0, rong / 20 - le)) if chu else 1
        cap = list(zip(chu_cot.get(1, ()), chu_cot.get(7, ())))

        def tong_dong(gc_):
            return sum(max(so_dong(a[0], a[1], con - gc_), so_dong(b[0], False, gc_)) ** 2 for a, b in cap)
        gc = con * CHIA_TEN_GHI_CHU[1] // sum(CHIA_TEN_GHI_CHU)
        gc = min((con * k // 100 for k in range(30, 71, 5)), key=lambda x: (tong_dong(x), abs(x - gc)))
    else:
        gc = max(toi_thieu_gc, con * 15 // 100)
    gc = min(max(gc, toi_thieu_gc), con - toi_thieu_ten)
    ds[7], ds[1] = gc, con - gc
    if min(ds) <= 0:                                    # số quá dài so với khổ giấy: về tỷ lệ cố định
        return rong_cot()
    return ds


def rong_bang_dau() -> int:
    """Bề rộng bảng đầu văn bản (twip): vùng chữ + phần lấn lề LAN_LE_DAU_MM."""
    return rong_trang() + twip(LAN_LE_DAU_MM[0]) + twip(LAN_LE_DAU_MM[1])


def rong_cot_dau() -> tuple:
    """(cột cơ quan, cột quốc hiệu) twip của bảng ẩn viền đầu văn bản."""
    w = rong_bang_dau()
    return w - RONG_QUOC_HIEU, RONG_QUOC_HIEU


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
    # cơ quan chủ quản 13 in hoa đứng; cơ quan ban hành 13 in hoa đứng đậm, đường kẻ dưới 1/3 - 1/2 dòng chữ; số, "(DỰ THẢO)" 13
    # đứng; quốc hiệu 13 in hoa đậm; tiêu ngữ 14 đậm, gạch dưới đúng độ dài chữ; địa danh / ngày 14 nghiêng (22/10/2026)
    ten_cq = str(da['DON_VI_TIEU_DE'] or '').upper()
    ke = '_' * max(6, min(20, len(ten_cq) // 2 + 2))     # gạch dưới ~ nửa dòng tên cơ quan
    r1, r2 = rong_cot_dau()
    vua_trai = (r1 - 2 * 57) / 20                        # pt chữ trong cột cơ quan (trừ lề ô)
    trai = ''.join(_p(_r(d, co=CO_CO_QUAN), can='center')
                   for x in (da['DON_VI_CAP_TREN_2DONG'] or '').split('\n') if x.strip()
                   for d in _ngat_can_bang(x.strip().upper(), vua_trai, CO_CO_QUAN)) + \
        ''.join(_p(_r(d, dam=True, co=CO_CO_QUAN), can='center') for d in _ngat_can_bang(ten_cq, vua_trai, CO_CO_QUAN, True)) + \
        _p(_r(ke, co=CO_CO_QUAN), can='center', dong=200) + \
        _p(_r(so, co=CO_CO_QUAN), can='center', truoc=60) + (_p(_r('(DỰ THẢO)', co=CO_CO_QUAN), can='center') if du_thao else '')
    phai = _p(_r('CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM', dam=True, co=CO_CO_QUAN), can='center') + \
        _p(_r('Độc lập - Tự do - Hạnh phúc', dam=True, co=co, gach=True), can='center') + \
        _p(_r(f'{dia_danh}, {_ngay_chu(ttho["ngay_pa"], da["nam"])}', nghieng=True, co=co), can='center', truoc=200)
    t = [_bang([_hang([_o(trai, r1, doc='top', vien=False), _o(phai, r2, doc='top', vien=False)])], [r1, r2], vien=False,
               lui=twip(LAN_LE_DAU_MM[0]))]
    # ---- tên văn bản
    ten = 'PHƯƠNG ÁN CHI TIẾT' + (f' BỔ SUNG (LẦN {lan})' if lan is not None and lan > 1 else '')
    t += [_p(_r(ten, dam=True, co=CO_TEN_LOAI), can='center', truoc=240, dong=240)]
    t += [_p(_r(x, dam=True, co=co), can='center', dong=240) for x in TRICH_YEU_DONG]
    t += [_p(_r(f'DỰ ÁN {str(da["du_an"] or "").upper()}', dam=True, co=co), can='center', sau=240, dong=240)]
    # ---- I. chủ sử dụng (bảng ẩn viền: nhãn đậm | nội dung)
    to_chuc = la_to_chuc(ttho['ho_ten'])
    # 22/10/2026: tiêu đề mục I theo chủ sử dụng (in_an.tieu_de_muc_i - cùng bản Excel); tổ chức chỉ "Tổ chức:" / "Địa chỉ:"
    t.append(_p(_r(in_an.tieu_de_muc_i(to_chuc), dam=True, co=co), truoc=120, sau=60, giu_sau=True))
    hang_i = [(in_an.NHAN_TO_CHUC if to_chuc else 'Họ và tên:', ttho['ho_ten'])]
    if not to_chuc and ttho['cccd']:
        hang_i.append(('Số CCCD:', ttho['cccd']))
    hang_i.append((in_an.NHAN_DIA_CHI_TO_CHUC if to_chuc else 'Địa chỉ thường trú:', ttho['dia_chi']))
    if not to_chuc and ttho['dien_thoai']:
        hang_i.append(('Số điện thoại:', ttho['dien_thoai']))
    # 22/10/2026 (mẫu PA_01 / PA_003 người dùng gửi): nhãn chữ thường, tên chủ sử dụng (hàng đầu) in đậm, nội dung khác thường
    c1, c0 = w * 28 // 100, w * 5 // 100
    t.append(_bang([_hang([_o(_p(), c0, vien=False, doc='top'), _o(_p(_r(n, co=co), can='left'), c1, vien=False, doc='top'),
                           _o(_p(_r(v, dam=k == 0, co=co), can='left'), w - c0 - c1, vien=False, doc='top')])
                    for k, (n, v) in enumerate(hang_i)],
                   [c0, c1, w - c0 - c1], vien=False))
    # ---- II. nguồn gốc: mỗi đoạn logic MỘT w:p (in_an._thong_tin_ho đã nối xuống dòng cứng giữa câu từng thửa - ho_so.
    # lam_sach_doan_van), căn đều, giãn dòng đơn, cách đoạn 6 pt (w:after 120); đoạn thường thụt đầu dòng 1 cm, đoạn gạch đầu dòng
    # thụt lề treo; không w:br, không đoạn rỗng - Word tự bẻ dòng theo lề
    t.append(_p(_r(in_an.TIEU_DE_MUC_II, dam=True, co=co), truoc=120, sau=60, giu_sau=True))
    for doan in (x for x in str(ttho['nguon_goc'] or '').split('\n') if x.strip()):
        if dau_dong(doan):
            t.append(_p(_r(doan, co=co), dong=DONG_DOAN, sau=SAU_DOAN, trai=THUT_TREO, treo=THUT_TREO))
        else:
            t.append(_p(_r(doan, co=co), dong=DONG_DOAN, sau=SAU_DOAN, dau_dong=THUT_DAU))
    # ---- III. bảng tính toán: tiêu đề KHÔNG keepNext / pageBreakBefore (22/10/2026) - mục III in tiếp ngay dưới mục II ở cuối
    # trang 1 khi còn chỗ; dòng tiêu đề cột lặp ở đầu trang sau (w:tblHeader)
    t.append(_p(_r('III. Bảng tính toán bồi thường, hỗ trợ', dam=True, co=co), truoc=120, sau=60))
    rong = rong_cot(_chu_cac_cot(dong, nghiep_vu.so_muc(2)))
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
    # ---- chữ ký: DÒNG CUỐI của bảng mục III, ẩn viền trái / phải / dưới và vạch giữa (22/10/2026). Word giữ liền dòng TỔNG CỘNG
    # + IV + chữ ký (keepNext giữa các dòng cùng bảng); bảng chữ ký riêng sau bảng thì Word bỏ qua keepNext -> chữ ký trơ một trang.
    # Bản dự thảo không có
    if not du_thao:
        def ky(chuc_vu, ten):                           # giãn dòng đơn: khối cuối gọn
            return _p(_r(chuc_vu, dam=True, co=co), can='center', truoc=240, dong=240) + \
                ''.join(_p(can='center', dong=240) for _ in range(4)) + _p(_r(ten or '', dam=True, co=co), can='center', dong=240)
        an = ('left', 'bottom', 'right')
        hang.append(_hang([_o(ky('LẬP BIỂU', da['nguoi_lap']), sum(rong[:3]), nhap=3, doc='top', an_vien=an),
                           _o(ky('KIỂM TRA', da['nguoi_kiem_tra']), sum(rong[3:6]), nhap=3, doc='top', an_vien=an),
                           _o(ky(da['CHUC_VU_KY'], da['nguoi_ky']), sum(rong[6:]), nhap=2, doc='top', an_vien=an)],
                          khong_tach=True))
    t.append(_bang(hang, rong, le_o=LE_O))
    return ''.join(t)


def _chu_cac_cot(dong: list, so_muc_nha) -> dict:
    """{cột: [(chữ, đậm)]} các ô bảng mục III (cùng cách in như noi_dung_chi_tiet) - để chia bề rộng cột theo nội dung."""
    chu, muc_sl = {}, None
    for x in dong:
        loai, gt = x[0], x[1]
        cach_tinh = x[2] if len(x) > 2 else ''
        if loai == 'H':
            muc_sl = 2 if str(gt[0]) == str(so_muc_nha) else None
        dam = loai in ('H', 'T')
        if loai == 'T':
            chu.setdefault(6, []).append((_so(gt[6]), True))
            continue
        o = {0: '' if gt[0] is None else str(gt[0]), 1: gt[1] or '', 6: _so(gt[6]), 7: gt[7] or ''}
        if not cach_tinh:
            o.update({2: gt[2] or '', 3: _so(gt[3], muc_sl, 'sl'), 4: _so(gt[4]), 5: _so(gt[5], loai='ty_le')})
        for k, c in o.items():
            chu.setdefault(k, []).append((str(c), dam or (k == 6 and loai == 'R')))
    return chu


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

"""Phương án chi tiết bản Word (.docx) theo thể thức Nghị định 30/2020/NĐ-CP (người dùng 21/10/2026: Excel không cắt đôi được một dòng
bảng qua hai trang - dòng ghi chú / nguồn gốc dài đẩy cả dòng sang trang sau, trang trước hở).

Cùng số liệu với bản Excel (du_lieu_in.dong_chi_tiet, _thong_tin_du_an, _thong_tin_ho, lần phương án, chế độ dự thảo / chính thức), dựng
bằng XML thuần (van_ban_trinh._goi_docx - không cần python-docx, không cần Word để tạo file):
  - A4 dọc, lề trái 15 mm, phải 10 mm, trên 10 mm, dưới 10 mm (LE_MM); Times New Roman.
  - Quốc hiệu, tiêu ngữ, tên cơ quan, số, địa danh / ngày: bảng ẩn viền hai cột; thông tin chủ sử dụng: bảng ẩn viền.
  - Bảng mục III: hàng tiêu đề cột w:tblHeader (Word lặp đầu mọi trang); dòng số liệu có chữ dài (ghi chú, tên > DAI_CHO_TACH ký
    tự) w:cantSplit = 0 (Word cắt đôi qua trang - trang trước lấp đầy), dòng ngắn / đề mục = 1; dòng thưởng, TỔNG CỘNG, mục IV, khối
    chữ ký (dòng cuối của chính bảng này, ẩn viền) cantSplit = 1 và keepNext (không tách rời, chữ ký không đứng trơ một trang).
  - Lề, cỡ chữ, trích yếu, độ hở gạch chân là THÔNG SỐ MẪU nhúng trong hồ sơ địa phương (pabt_profile.json, mục ban_in.mau_word): đổi
    mẫu theo quy định mới = nhập gói .pabtcfg / ghi file máy, không cần bản cập nhật phần mềm. Cỡ chữ mặc định (22/10/2026): cơ quan,
    quốc hiệu, số / ngày, "(DỰ THẢO)", nguồn gốc, bảng 13; tiêu ngữ, tên văn bản, trích yếu, dự án, mục I - IV 14; ghi chú 11; khối
    chữ ký 15. Mục II giãn dòng đơn, cách đoạn 6 pt, chỉ DÒNG ĐẦU mỗi đoạn thụt 1 cm.
  - Bản dự thảo: "(DỰ THẢO)" dưới số, không số / ngày phương án, không khối chữ ký.
Không ghi cố định tên đơn vị / người ký: lấy từ Thông tin dự án (to_chuc.MAC_DINH khi trống) như bản Excel.
"""
from __future__ import annotations

import math
import re
from pathlib import Path

from . import du_lieu_in
from . import dia_phuong
from .van_ban_trinh import _goi_docx, _xml

# thông số mẫu (lề, cỡ chữ, trích yếu, thụt, độ hở gạch chân, đường kẻ dưới dự án): giá trị đặt ở _ap_mau() từ hồ sơ địa phương
# (ban_in.mau_word) - nơi dùng đọc in_word.LE_MM / CO_BANG… LÚC GỌI, đừng `from .in_word import CO_BANG` ở cấp module
LE_MM: dict = {}                                        # mm: trai / phai / tren / duoi
CO_CO_QUAN = CO_QUOC_HIEU = CO_TIEU_NGU = CO_SO_NGAY = CO_DU_THAO = CO_TEN_LOAI = CO_TRICH_YEU = CO_DU_AN = 0.0
CO_THONG_TIN = CO_DE_MUC = CO_NGUON_GOC = CO_BANG = CO_GHI_CHU = CO_CHU_KY = 0.0
TRICH_YEU = ''
TRICH_YEU_DONG: tuple = ()                              # vùng chữ rộng 524 pt: trích yếu 14 pt đậm (~480 pt) vừa MỘT dòng
THUT_DAU = 0                                            # twip: thụt dòng đầu của đoạn
HO_GACH_PT = 2                                          # pt: khe giữa chân chữ và đường gạch (không sát chữ - khỏi mất dấu dưới)
DK_DU_AN_MM = 70                                        # đường kẻ dưới tên dự án (mm)
CHU_KY_LECH_TRAI_MM = 3.4                               # khối LẬP BIỂU - KIỂM TRA - chức vụ ký dịch sang trái chừng này (24/10/2026: lề trái rộng hơn lề phải)
CHI_NHANH_NGAN_MM = 10                                  # đường gạch dưới "CHI NHÁNH …" ngắn hơn chữ 1 cm (24/10/2026)
KHE_TIEU_NGU_PT = 1.5                                   # đường gạch dưới tiêu ngữ ≈ bằng chữ (đã đo bằng Word thật: -2 làm tiêu ngữ bẻ dòng "Hạnh / phúc"; 1,5 vừa đủ, đường kẻ chỉ hơn mực chữ ~1 mm mỗi bên)
HE_SO_DO_QT = 0.96                                      # bề rộng Qt đo so với Word (chữ in hoa đậm 13 pt) - tính đường gạch ngắn hơn chữ đúng số mm
DK_DU_AN_KHE_PT = 3                                     # đoạn rỗng mang đường kẻ dưới tên dự án cao chừng này: đường kẻ gần chữ, vẫn hở nhỏ
KHE_GACH_PT = 4                                         # pt: đường gạch dài hơn chữ chừng này (Word bẻ dòng nếu hẹp hơn chữ một chút)
KHE_COT_PT = 2                                          # pt chừa thêm cho mỗi cột thu vừa chữ (Word đo chữ rộng hơn Qt chút ít)
KHO_A4 = (11906, 16838)                                 # twip
# bảng đầu văn bản (cơ quan | quốc hiệu): từng lấn lề ở lề cũ 30 / 15 mm; lề 15 / 10 mm không cần
LAN_LE_DAU_MM = (0, 0)                                  # (trái, phải) mm bảng đầu lấn vào lề
RONG_QUOC_HIEU = 5300                                   # twip (285 pt) cột quốc hiệu: 269 pt chữ + lề ô; còn lại cho cột cơ quan
RONG_KY_TU = 0.6                                        # ước bề rộng một ký tự in hoa Times New Roman (x cỡ chữ; đậm x 1,05)
DONG_DOAN = 240                                         # đoạn Mục II: giãn dòng đơn
SAU_DOAN = 120                                          # cách đoạn / gạch đầu dòng 6 pt
# bề rộng 8 cột bảng mục III (phần nghìn) - STT, tên, ĐVT, số lượng, đơn giá, tỷ lệ, thành tiền, ghi chú: chỉ dùng khi không có số
# liệu (rong_cot() không đối số). Bản in thật: rong_cot(chu_cot) theo NỘI DUNG từng hộ (22/10/2026 - cột ghi chú cố định 14% làm ô
# ghi chú "Đất do UBND xã … Điều 101 Luật Đất đai" cao nửa trang): cột STT / ĐVT / số lượng / đơn giá / tỷ lệ / thành tiền vừa số dài
# nhất (và từ dài nhất của tiêu đề, không dưới COT_TOI_THIEU), phần còn lại chia tên : ghi chú theo CHIA_TEN_GHI_CHU
TY_LE_COT = (70, 205, 75, 100, 145, 80, 185, 140)
COT_SO = (0, 2, 3, 4, 5, 6)
COT_TOI_THIEU = {0: 18, 2: 30, 3: 39, 4: 42, 5: 24, 6: 56}     # pt (từ dài nhất của tiêu đề thường rộng hơn)
CHIA_TEN_GHI_CHU = (45, 55)
DU_RONG = 1.06                                          # chừa sai số ước bề rộng chữ (Word xuất PDF bẻ dòng sớm hơn ước)
LE_O = 40                                               # lề trái / phải trong ô bảng mục III (twip = 2 pt)
DAI_CHO_TACH = 80                                       # dòng số liệu có tên / ghi chú dài hơn (ký tự): cho Word cắt đôi qua trang
TIEU_DE_COT = ('STT', 'Tên tài sản', 'ĐVT', 'Số lượng', 'Đơn giá', 'Tỷ lệ (%)', 'Thành tiền (đồng)', 'Ghi chú')
TIEU_DE_COT_BS = ('STT', 'Tên tài sản', 'ĐVT', 'Số lượng', 'Đơn giá bổ sung', 'Tỷ lệ (%)', 'Thành tiền (đồng)', 'Ghi chú')   # bổ sung / điều chỉnh


def twip(mm: float) -> int:
    return int(round(mm / 25.4 * 1440))


def _ap_mau(hs: dict) -> None:
    """Đặt thông số mẫu từ hồ sơ địa phương (chạy lúc nạp module và sau mỗi lần nạp lại hồ sơ / nhập gói .pabtcfg)."""
    global LE_MM, TRICH_YEU, TRICH_YEU_DONG, THUT_DAU, HO_GACH_PT, DK_DU_AN_MM
    global CO_CO_QUAN, CO_QUOC_HIEU, CO_TIEU_NGU, CO_SO_NGAY, CO_DU_THAO, CO_TEN_LOAI, CO_TRICH_YEU, CO_DU_AN
    global CO_THONG_TIN, CO_DE_MUC, CO_NGUON_GOC, CO_BANG, CO_GHI_CHU, CO_CHU_KY
    mw = hs['ban_in']['mau_word']
    LE_MM = dict(mw['le_mm'])
    c = mw['co_chu']
    CO_CO_QUAN, CO_QUOC_HIEU, CO_TIEU_NGU, CO_SO_NGAY, CO_DU_THAO = c['co_quan'], c['quoc_hieu'], c['tieu_ngu'], c['so_ngay'], c['du_thao']
    CO_TEN_LOAI, CO_TRICH_YEU, CO_DU_AN, CO_THONG_TIN, CO_DE_MUC = c['ten_loai'], c['trich_yeu'], c['du_an'], c['thong_tin'], c['de_muc']
    CO_NGUON_GOC, CO_BANG, CO_GHI_CHU, CO_CHU_KY = c['nguon_goc'], c['bang'], c['ghi_chu'], c['chu_ky']
    TRICH_YEU = ' '.join(str(mw['trich_yeu']).split())
    TRICH_YEU_DONG = (TRICH_YEU,)
    THUT_DAU = twip(mw['thut_dau_dong_mm'])
    HO_GACH_PT = max(0, min(31, int(round(mw['gach_chan_ho_pt']))))
    DK_DU_AN_MM = mw['duong_ke_du_an_mm']


dia_phuong.dang_ky(_ap_mau)


# ---------------------------------------------------------------- cập nhật mẫu Word không cần bản cập nhật phần mềm
# Mẫu Word (chi tiết / bổ sung / điều chỉnh) NHÚNG trong phần mềm: bố cục do mã dựng, thông số (lề, cỡ chữ, trích yếu, thụt, độ hở gạch
# chân) ở hồ sơ địa phương mục ban_in.mau_word. Quy định mới đổi quy cách -> thay thông số bằng MỘT trong ba cách (đều không đổi phiên bản
# phần mềm, không đụng dữ liệu dự án): (1) hộp Công cụ > Quản lý Mẫu in & Bản in: Nhập / Xuất thông số mẫu Word; (2) nhập gói .pabtcfg
# (Công cụ > Nhập gói mẫu in & cấu hình); (3) sửa pabt_profile.json của máy. Chỉ ghi các mục KHÁC mặc định vào file máy.
LOAI_THONG_SO = 'pabt_mau_word'


def thong_so_mau() -> dict:
    """Thông số mẫu Word đang dùng (bản sao)."""
    import copy
    return copy.deepcopy(dia_phuong.lay('ban_in.mau_word'))


def trang_thai_thong_so() -> str:
    """'Nhúng chuẩn' khi giống mặc định đóng kèm, 'Tùy chỉnh' khi khác (file máy / gói .pabtcfg)."""
    return 'Nhúng chuẩn' if thong_so_mau() == dia_phuong.mac_dinh()['ban_in']['mau_word'] else 'Tùy chỉnh'


def xuat_thong_so(file) -> Path:
    """Ghi thông số mẫu Word đang dùng ra file JSON để chỉnh sửa (cùng file đưa cho máy khác nhập)."""
    import json
    file = Path(file)
    file.parent.mkdir(parents=True, exist_ok=True)
    file.write_text(json.dumps({'loai': LOAI_THONG_SO, 'mau_word': thong_so_mau()}, ensure_ascii=False, indent=2), encoding='utf-8')
    return file


def nhap_thong_so(file) -> list:
    """Nhập file thông số mẫu Word (do xuat_thong_so tạo, đã sửa; chỉ cần các mục muốn đổi): kiểm tra, ghi vào hồ sơ máy, áp dụng ngay.
    Trả danh sách mục đã đổi. Sai -> dia_phuong.LoiHoSo (chưa ghi gì)."""
    import json
    try:
        x = json.loads(Path(file).read_text(encoding='utf-8-sig'))
    except (OSError, ValueError) as e:
        raise dia_phuong.LoiHoSo(f'Không đọc được file thông số mẫu Word: {e}') from None
    if not isinstance(x, dict) or x.get('loai') != LOAI_THONG_SO or not isinstance(x.get('mau_word'), dict):
        raise dia_phuong.LoiHoSo(f'File không phải thông số mẫu Word (cần "loai": "{LOAI_THONG_SO}" và mục "mau_word").')
    cu = thong_so_mau()
    moi = dia_phuong.tron(cu, x['mau_word'])
    loi = dia_phuong.kiem_tra_mau_word(moi)
    if loi:
        raise dia_phuong.LoiHoSo('Thông số mẫu Word chưa hợp lệ:' + chr(10) + '- ' + (chr(10) + '- ').join(loi))
    khac = dia_phuong.khac_mac_dinh(moi, dia_phuong.mac_dinh()['ban_in']['mau_word'])
    dia_phuong.dat_muc_may(('ban_in', 'mau_word'), khac or None)
    return sorted(k for k in moi if moi[k] != cu.get(k))


def khoi_phuc_thong_so() -> None:
    """Bỏ thông số mẫu Word tùy chỉnh của máy, dùng lại bộ nhúng chuẩn."""
    dia_phuong.dat_muc_may(('ban_in', 'mau_word'), None)


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


def _duong_ke_du_an() -> str:
    """Đường kẻ ngang ngắn (DK_DU_AN_MM) căn giữa ngay dưới tên dự án: viền dưới của một đoạn rỗng thụt hai bên (Word vẽ viền đoạn
    suốt bề rộng giữa hai lề thụt)."""
    ben = (rong_trang() - twip(DK_DU_AN_MM)) // 2
    return (f'<w:p><w:pPr><w:pBdr><w:bottom w:val="single" w:sz="6" w:space="1" w:color="000000"/></w:pBdr>'
            f'<w:spacing w:before="0" w:after="200" w:line="{DK_DU_AN_KHE_PT * 20}" w:lineRule="exact"/><w:ind w:left="{ben}" w:right="{ben}"/>'
            f'<w:rPr><w:sz w:val="4"/></w:rPr></w:pPr></w:p>')


def _o(noi_dung: str, rong: int, nhap: int = 1, doc: str = 'center', dong_doc: str | None = None, vien: bool = True,
       an_vien: tuple = (), nen: str | None = None) -> str:
    """Ô bảng: noi_dung = các w:p; nhap = số cột gộp ngang (gridSpan); dong_doc 'restart' / 'continue' = gộp dọc (vMerge);
    vien=False ẩn cả bốn cạnh, an_vien = các cạnh ẩn ('top', 'left', 'bottom', 'right')."""
    an = ('top', 'left', 'bottom', 'right') if not vien else tuple(an_vien)
    pr = f'<w:tcW w:w="{rong}" w:type="dxa"/>' + (f'<w:gridSpan w:val="{nhap}"/>' if nhap > 1 else '') + \
        ('<w:vMerge w:val="restart"/>' if dong_doc == 'restart' else '<w:vMerge/>' if dong_doc == 'continue' else '') + \
        ('<w:tcBorders>' + ''.join(f'<w:{k} w:val="nil"/>' for k in an) + '</w:tcBorders>' if an else '') + \
        (f'<w:shd w:val="clear" w:color="auto" w:fill="{nen}"/>' if nen else '') + f'<w:vAlign w:val="{doc}"/>'
    return f'<w:tc><w:tcPr>{pr}</w:tcPr>{noi_dung or _p()}</w:tc>'


def _hang(o: list, tieu_de: bool = False, khong_tach: bool = False) -> str:
    """Dòng bảng: tieu_de = w:tblHeader (lặp đầu trang); khong_tach = w:cantSplit (không cắt đôi qua trang) - dòng số liệu thường
    cantSplit = 0: Word được cắt đôi dòng dài sang trang sau."""
    pr = ('<w:tblHeader/>' if tieu_de else '') + f'<w:cantSplit w:val="{1 if (khong_tach or tieu_de) else 0}"/>'
    return f'<w:tr><w:trPr>{pr}</w:trPr>{"".join(o)}</w:tr>'


def _bang(hang: list, rong: list, vien: bool = True, le_o: int = 57, lui: int = 0, ngoai_sz: int = 4) -> str:
    """lui (twip): bảng bắt đầu lùi ra ngoài lề trái chừng này (w:tblInd âm, canh trái) - bảng đầu văn bản lấn lề."""
    b = ''.join(f'<w:{k} w:val="{"single" if vien else "nil"}" w:sz="{ngoai_sz if k in ("top", "left", "bottom", "right") else 4}" '
                f'w:space="0" w:color="000000"/>' for k in ('top', 'left', 'bottom', 'right', 'insideH', 'insideV'))
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


def _ham_do():
    """Hàm đo bề rộng chữ thật (chữ, phông, cỡ pt, đậm) -> pt bằng Qt khi có giao diện, không thì None (dùng ước _rong_chu)."""
    try:
        from . import in_an
        return in_an._ham_do_chu()
    except Exception:                                   # noqa: BLE001 - thiếu Qt / giao diện: dùng ước lượng
        return None


def _rong_do(chu: str, co: float, dam: bool = False, do=None) -> float:
    """Bề rộng (pt) của chữ Times New Roman: đo thật khi có Qt (do = hàm của _ham_do), không thì ước."""
    if do:
        return do(str(chu), 'Times New Roman', co, dam)
    return _rong_chu(chu, co, dam)


def _p_gach(chu: str, co: float, dam: bool, rong_o: int, do=None, khe: float = KHE_GACH_PT, ngan_mm: float = 0) -> str:
    """Dòng chữ căn giữa có đường GẠCH CHÂN HỞ: viền dưới của đoạn, cách chân chữ HO_GACH_PT pt (gạch chân chữ của Word sát nét chữ,
    mất dấu dưới "Ị Ộ…"); thụt hai bên để đường kẻ dài đúng bằng chữ. rong_o = bề rộng chữ của ô (twip)."""
    if ngan_mm:                                                  # đường gạch NGẮN hơn chữ: đoạn rỗng riêng (viền dưới của đoạn chữ thụt vào sẽ làm chữ bẻ dòng)
        rong_chu = _rong_do(chu, co, dam, do) * 20 * (HE_SO_DO_QT if do else 1)
        ben = max(0, int((rong_o - max(rong_chu * 0.3, rong_chu - twip(ngan_mm))) // 2))
        return (f'<w:p><w:pPr><w:spacing w:before="0" w:after="0" w:line="240" w:lineRule="auto"/><w:jc w:val="center"/></w:pPr>'
                f'{_r(chu, dam=dam, co=co)}</w:p>'
                f'<w:p><w:pPr><w:pBdr><w:bottom w:val="single" w:sz="4" w:space="0" w:color="000000"/></w:pBdr>'
                f'<w:spacing w:before="0" w:after="0" w:line="{max(20, int(HO_GACH_PT * 20))}" w:lineRule="exact"/>'
                f'<w:ind w:left="{ben}" w:right="{ben}"/><w:rPr><w:sz w:val="2"/></w:rPr></w:pPr></w:p>')
    ben = max(0, int((rong_o - (_rong_do(chu, co, dam, do) + khe) * 20) // 2))
    return (f'<w:p><w:pPr><w:pBdr><w:bottom w:val="single" w:sz="4" w:space="{HO_GACH_PT}" w:color="000000"/></w:pBdr>'
            f'<w:spacing w:before="0" w:after="0" w:line="240" w:lineRule="auto"/><w:ind w:left="{ben}" w:right="{ben}"/>'
            f'<w:jc w:val="center"/></w:pPr>{_r(chu, dam=dam, co=co)}</w:p>')


def rong_cot(chu_cot: dict | None = None, do=None) -> list:
    """Bề rộng 8 cột bảng mục III (twip). chu_cot {cột: [(chữ, đậm)]}: theo nội dung (cột số vừa chữ dài nhất, còn lại chia tên /
    ghi chú); None: tỷ lệ cố định TY_LE_COT."""
    tong = rong_trang()
    if chu_cot is None:
        ds = [tong * t // sum(TY_LE_COT) for t in TY_LE_COT]
        ds[1] += tong - sum(ds)
        return ds
    le = 2 * LE_O / 20                                  # pt lề ô hai bên
    ds = [0] * len(TIEU_DE_COT)
    if do is None:
        do = _ham_do()
    du = 1.03 if do else DU_RONG                        # đo thật chỉ chừa sai số nhỏ; ước lượng chừa nhiều hơn

    def w(chu, co, dam=False):
        return _rong_do(chu, co, dam, do)
    # cột số (STT, ĐVT, số lượng, đơn giá, tỷ lệ, thành tiền): TỰ THU VỪA CHỮ - vừa từ dài nhất của tiêu đề và số dài nhất; phần
    # thừa nhường cho cột Tên tài sản / Ghi chú
    for k in COT_SO:
        can = max([COT_TOI_THIEU[k]] + [w(t, CO_BANG, True) for t in TIEU_DE_COT[k].split()] +
                  [w(c, CO_BANG, d) * du for c, d in chu_cot.get(k, ()) if c])
        ds[k] = int(round((can + le + KHE_COT_PT) * 20))
    con = tong - sum(ds)
    co_gc = any(c for c, _ in chu_cot.get(7, ()))
    toi_thieu_gc = int(round((w('Ghi chú', CO_BANG, True) + le) * 20))
    toi_thieu_ten = int(round((max([w(t, CO_BANG, True) for c, _ in chu_cot.get(1, ()) for t in str(c).split()] or [0])
                               + le) * 20))
    if co_gc:
        # chia tên : ghi chú sao cho các dòng bảng (cao theo ô nhiều dòng chữ hơn) thấp và đều: tổng BÌNH PHƯƠNG số dòng ước
        # nhỏ nhất - chỉ cộng số dòng thì ô ghi chú dài bị dồn thành một dòng bảng cao nửa trang
        def so_dong(chu, d, rong, co):
            return math.ceil(w(chu, co, d) * du / max(1.0, rong / 20 - le)) if chu else 1
        cap = list(zip(chu_cot.get(1, ()), chu_cot.get(7, ())))

        def tong_dong(gc_):
            return sum(max(so_dong(a[0], a[1], con - gc_, CO_BANG), so_dong(b[0], False, gc_, CO_GHI_CHU)) ** 2 for a, b in cap)
        gc = con * CHIA_TEN_GHI_CHU[1] // sum(CHIA_TEN_GHI_CHU)
        gc = min((con * k // 100 for k in range(30, 71, 5)), key=lambda x: (tong_dong(x), abs(x - gc)))
    else:
        gc = int(toi_thieu_gc * 1.3)                    # không có ghi chú nào: cột Ghi chú thu vừa tiêu đề, nhường chỗ cho Tên tài sản
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


MUC_TT = (1, 2, 3, 7, 4, 5)                             # thứ tự mục tóm tắt (7 = vật nuôi, in là mục 4; xem nghiep_vu.MUC_VN)
TEN_MUC_NGAN = {1: 'đất', 2: 'nhà và công trình xây dựng', 3: 'cây trồng', 7: 'vật nuôi', 4: 'các chính sách hỗ trợ khác'}
LA_MA = ('I', 'II', 'III', 'IV', 'V', 'VI', 'VII', 'VIII', 'IX', 'X', 'XI', 'XII')


def _la_ma(n: int) -> str:
    return LA_MA[n - 1] if 1 <= n <= len(LA_MA) else str(n)


def _theo_muc(dong: list) -> dict:
    """{mục: [dòng 'I' của mục]} từ danh sách dòng du_lieu_in.dong_chi_tiet (tách theo dòng đề mục 'H')."""
    from . import nghiep_vu
    ma = {str(nghiep_vu.so_muc(m)): m for m in (1, 2, 3, nghiep_vu.MUC_VN, 4)}
    kq = {m: [] for m in ma.values()}
    hien = None
    for x in dong:
        if x[0] == 'H':
            hien = ma.get(str(x[1][0]))
        elif x[0] == 'I' and hien is not None:
            kq[hien].append(x)
    return kq


def _chu_ky(rows: list) -> tuple:
    """Dấu vân tay các dòng (bỏ STT) - so sánh mục có thay đổi giữa phương án cũ và mới."""
    return tuple(tuple(str(v) for v in (x[1][1:] + list(x[2:]))) for x in rows)


def dong_dieu_chinh(con, ma_ho: int, bc, lan_dc, dong_moi: list, kq_moi, da: dict) -> tuple:
    """Danh sách dòng bảng mục III của PHƯƠNG ÁN ĐIỀU CHỈNH (theo mẫu "Phương án điều chỉnh cây trồng của ông Nguyễn Tô"):
      A. Phương án đã được phê duyệt tại QĐ … (lần bị thay): tổng + tóm tắt I-V
      B. Phương án điều chỉnh = chênh lệch (mới - cũ); với mỗi mục có thay đổi: "I. <mục> đã được phê duyệt tại QĐ …" (dòng cũ) rồi
         "II. Điều chỉnh về <mục>" (dòng mới)
      C. Tổng giá trị sau điều chỉnh (A+B): tóm tắt I-V + TỔNG CỘNG; dòng tái định cư đánh số tiếp.
    lan_dc: LanPA của lần điều chỉnh; dong_moi / kq_moi: dòng + kết quả của lần đó (du_lieu_in.dong_chi_tiet). Trả (dòng, nhãn dòng tái
    định cư)."""
    from . import in_an, lan_pa, nghiep_vu
    bc = bc or in_an.BoiCanh.tu(con)
    goc = lan_pa.lan_cua(con, ma_ho, lan_dc.thay_the)
    pa_cu = nghiep_vu.doc_phuong_an(con, ma_ho, lan=goc.lan)
    dong_cu, kq_cu = du_lieu_in.dong_chi_tiet(con, ma_ho, bc, pa_cu, nghiep_vu.doc_phuong_an(con, ma_ho, den_lan=goc.lan - 1))
    qd = goc.qd[-1] if goc.qd else {}
    so_qd = str(qd.get('so') or '').strip()
    ngay_qd = str(qd.get('ngay') or '').strip()
    cap = str(da.get('cap_dia_ban_thuong') or '').strip()
    ten_db = str(da.get('ten_dia_ban') or '').strip()
    co_quan = f'UBND {cap} {ten_db}'.replace('  ', ' ').strip() if (cap and ten_db) else ''
    tai = ('Quyết định số ' + (so_qd or '……') + ' ngày ' + (ngay_qd or '……') + (f' của {co_quan}' if co_quan else ''))
    cu, moi = _theo_muc(dong_cu), _theo_muc(dong_moi)
    muc_ts = [m for m in MUC_TT if m != 7 or kq_cu.muc.get(7) or kq_moi.muc.get(7)]

    def tom_tat(kq):
        return [['S', [_la_ma(k), nghiep_vu.TEN_MUC[m], None, None, None, None, kq.muc.get(m, 0), None]]
                for k, m in enumerate(muc_ts, start=1)]
    out = [['G', ['A', 'PHƯƠNG ÁN ĐÃ ĐƯỢC PHÊ DUYỆT TẠI ' + tai.upper().replace('QUYẾT ĐỊNH SỐ', 'QUYẾT ĐỊNH SỐ'), None, None, None,
                  None, kq_cu.tong, None]]]
    out += tom_tat(kq_cu)
    out.append(['G', ['B', 'PHƯƠNG ÁN ĐIỀU CHỈNH', None, None, None, None, kq_moi.tong - kq_cu.tong, None]])
    n = 0
    for m in (1, 2, 3, 7, 4):
        if _chu_ky(cu[m]) == _chu_ky(moi[m]) and kq_cu.muc.get(m) == kq_moi.muc.get(m):
            continue
        ten = nghiep_vu.TEN_MUC[m]
        n += 1
        out.append(['G', [_la_ma(n), f'{ten} đã được phê duyệt tại {tai}', None, None, None, None, kq_cu.muc.get(m, 0), None], m])
        out += [['I'] + x[1:] for x in cu[m]]
        n += 1
        out.append(['G', [_la_ma(n), f'Điều chỉnh về {TEN_MUC_NGAN[m]}', None, None, None, None, kq_moi.muc.get(m, 0), None], m])
        out += [['I'] + x[1:] for x in moi[m]]
    out.append(['G', ['C', 'TỔNG GIÁ TRỊ SAU ĐIỀU CHỈNH (A+B)', None, None, None, None, kq_moi.tong, None]])
    out += tom_tat(kq_moi)
    out.append(['T', [None, 'TỔNG CỘNG', None, None, None, None, kq_moi.tong, None]])
    return out, _la_ma(len(muc_ts) + 1)


def _hang_tu_dong(dong: list, rong: list, so_muc_nha, muc_sl_dau=None) -> list:
    """Các dòng bảng mục III (w:tr) từ danh sách dòng của du_lieu_in.dong_chi_tiet (H / I / R / T) + G / S của phương án điều chỉnh."""
    hang = []
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
    muc_sl = muc_sl_dau
    for i, x in enumerate(dong):
        loai, gt = x[0], x[1]
        cach_tinh = x[2] if len(x) > 2 else ''
        if loai == 'H':
            muc_sl = 2 if str(gt[0]) == str(so_muc_nha) else None
        dam = loai in ('H', 'T')
        if loai == 'G' and len(x) > 2 and isinstance(x[2], int):
            muc_sl = 2 if x[2] == 2 else None           # tiêu đề khối của một mục: số lượng mục 2 (nhà) kiểu kế toán 2 chữ số lẻ
        if loai in ('G', 'S'):
            # 1.0.15 (mẫu phương án điều chỉnh): G = tiêu đề khối nền xám đậm (A / B / C / I / II…), S = dòng tổng hợp (I-V); tên gộp
            # ô STT.. Tỷ lệ (cột 1-5)
            nen = 'D9D9D9' if loai == 'G' else None
            tong = _so(gt[6]) if gt[6] else '-'
            hang.append(_hang([
                _o(_p(_r(str(gt[0] or ''), dam=loai == 'G', co=CO_BANG), can='center', giu_sau=True), rong[0], nen=nen),
                _o(_p(_r(gt[1] or '', dam=loai == 'G', co=CO_BANG), can='left', giu_sau=True), sum(rong[1:6]), nhap=5, nen=nen),
                _o(_p(_r(tong, dam=loai == 'G', co=CO_BANG), can='right', giu_sau=True), rong[6], nen=nen),
                _o(_p(_r(gt[7] or '', co=CO_GHI_CHU), can='center') if gt[7] else _p(), rong[7], nen=nen)], khong_tach=True))
            continue
        if loai == 'T':
            o = [_o(_p(_r(gt[1], dam=True, co=CO_BANG), can='center', giu_sau=True), sum(rong[:6]), nhap=6),
                 _o(_p(_r(_so(gt[6]), dam=True, co=CO_BANG), can='right', giu_sau=True), rong[6]),
                 _o(_p(giu_sau=True), rong[7])]
            hang.append(_hang(o, khong_tach=True))
            continue

        giu = loai == 'R'                               # dòng ngay trước TỔNG CỘNG đi liền khối cuối (không để tổng + chữ ký trơ)

        def oc(chu, k, can, dam_o=dam, co_o=CO_BANG):
            return _o(_p(_r(chu, dam=dam_o, co=co_o), can=can, giu_sau=giu) if chu else _p(giu_sau=giu), rong[k])
        o = [oc('' if gt[0] is None else str(gt[0]), 0, 'center' if loai in ('H', 'R') else 'left'), oc(gt[1] or '', 1, 'left')]
        if cach_tinh:
            o.append(_o(_p(_r(cach_tinh, dam=dam, co=CO_BANG), can='center', giu_sau=giu), sum(rong[2:6]), nhap=4))
        else:
            o += [oc(gt[2] or '', 2, 'center'), oc(_so(gt[3], muc_sl, 'sl'), 3, 'right'), oc(_so(gt[4]), 4, 'right'),
                  oc(_so(gt[5], loai='ty_le'), 5, 'center')]
        o.append(oc(_so(gt[6]), 6, 'right', dam_o=dam or loai == 'R'))
        gd = gop_gc.get(i)
        o.append(_o(_p(_r(gt[7] or '', co=CO_GHI_CHU), can='left', giu_sau=giu) if gd != 'continue' and gt[7]
                    else _p(giu_sau=giu), rong[7], dong_doc=gd))
        # dòng ngắn (đề mục, tên / ghi chú vài dòng) không cắt đôi; dòng có chữ dài (ghi chú, tên thửa…) Word được cắt qua trang
        dai = loai == 'I' and max(len(str(gt[1] or '')), len(str(gt[7] or '')), len(cach_tinh or '')) > DAI_CHO_TACH
        hang.append(_hang(o, khong_tach=not dai))
    return hang


_RE_CHI_NHANH = re.compile(r'CHI NHÁNH\s+.+$')


def dong_co_quan(da: dict) -> tuple[str, str]:
    """(các dòng cơ quan chủ quản - tự xuống dòng, dòng 3 gạch chân) của bảng đầu văn bản (người dùng 23/10/2026: mất chữ "CHI NHÁNH
    X"): dòng gạch chân phải là "CHI NHÁNH …". Ô tên đơn vị trên tiêu đề của dự án cũ có thể ghi tên thành phố ("Thành phố Đồng
    Nai" - cách điền của file Excel cũ) hoặc trống: khi đó lấy phần "Chi nhánh …" của đơn vị lập, rồi của hồ sơ địa phương; chữ cũ
    (không phải chi nhánh) vẫn giữ làm dòng thường nếu chưa có trong tên cơ quan chủ quản."""
    cap = str(da['DON_VI_CAP_TREN_2DONG'] or '').strip()
    tieu = ' '.join(str(da['DON_VI_TIEU_DE'] or '').upper().split())
    if _RE_CHI_NHANH.match(tieu):
        return cap, tieu
    from .to_chuc import MAC_DINH
    cn = None
    for nguon in (str(da.get('DON_VI_LAP') or '').upper(), str(MAC_DINH.get('don_vi_tieu_de') or '').upper(),
                  str(MAC_DINH.get('don_vi_lap') or '').upper()):
        m = _RE_CHI_NHANH.search(' '.join(nguon.split()))
        if m:
            cn = m.group(0)
            break
    if not cn:
        return cap, tieu
    if tieu and tieu not in ' '.join(cap.upper().split()):
        cap = (cap + '\n' if cap else '') + tieu
    return cap, cn


def noi_dung_chi_tiet(con, ma_ho: int, bc=None, du_thao: bool = False, pa=None, lan=None) -> str:
    """XML thân văn bản (w:body không sectPr) phương án chi tiết một hộ."""
    from . import dia_phuong, in_an, nghiep_vu
    from .ho_so import la_to_chuc
    da = du_lieu_in._thong_tin_du_an(con)
    da['ky_hieu_so'] = du_lieu_in.ky_hieu_cua_ho(con, ma_ho, da['ky_hieu_so'])
    lan = du_lieu_in.chon_lan_in(con, ma_ho, lan)
    pa_truoc = None
    if lan is not None:
        if pa is None:
            pa = nghiep_vu.doc_phuong_an(con, ma_ho, lan=lan)
        pa_truoc = nghiep_vu.doc_phuong_an(con, ma_ho, den_lan=lan - 1)
    dong, kq_lan = du_lieu_in.dong_chi_tiet(con, ma_ho, bc, pa, pa_truoc)
    ttho = du_lieu_in._thong_tin_ho(con, ma_ho, da)
    from . import lan_pa
    kieu = lan_pa.loai_lan(con, ma_ho, lan)             # 1.0.15: MẪU IN theo loại lần - chi tiết / bổ sung / điều chỉnh
    x_lan = None
    if lan is not None and lan > 1:
        x_lan = lan_pa.lan_cua(con, ma_ho, lan)
        ttho['so_pa'], ttho['ngay_pa'] = x_lan.so_pa, x_lan.ngay_pa
    nhan_tdc = 'IV'
    dieu_chinh = kieu == lan_pa.DIEU_CHINH and x_lan is not None and x_lan.la_dieu_chinh
    if dieu_chinh:
        dong, nhan_tdc = dong_dieu_chinh(con, ma_ho, bc, x_lan, dong, kq_lan, da)
    if du_thao:
        ttho['so_pa'], ttho['ngay_pa'] = '', ''
    w = rong_trang()
    # ---- quốc hiệu, tiêu ngữ, cơ quan, số, ngày (bảng ẩn viền 2 cột)
    dia_danh = str(dia_phuong.lay('ban_in.dia_danh_ngay', in_an.DIA_DANH_NGAY_MAC_DINH) or da['ten_dia_ban'] or '').strip()
    so = f'Số: {ttho["so_pa"]}/{da["ky_hieu_so"]}' if ttho['so_pa'] else f'Số:          /{da["ky_hieu_so"]}'
    # cơ quan chủ quản 13 in hoa đứng (2 dòng); dòng 3 = cơ quan ban hành / chi nhánh 13 in hoa đậm GẠCH CHÂN đúng độ dài chữ
    # (PDF mẫu PA_01: "CHI NHÁNH X"; không còn dòng "____"); số, "(DỰ THẢO)" 13
    # đứng; quốc hiệu 13 in hoa đậm; tiêu ngữ 14 đậm, gạch dưới đúng độ dài chữ; địa danh / ngày 14 nghiêng (22/10/2026)
    cap_tren, ten_cq = dong_co_quan(da)
    r1, r2 = rong_cot_dau()
    vua_trai = (r1 - 2 * 57) / 20                        # pt chữ trong cột cơ quan (trừ lề ô)
    do = _ham_do()
    trai = ''.join(_p(_r(d, co=CO_CO_QUAN), can='center')
                   for x in cap_tren.split('\n') if x.strip()
                   for d in _ngat_can_bang(x.strip().upper(), vua_trai, CO_CO_QUAN)) + \
        ''.join(_p_gach(d, CO_CO_QUAN, True, r1 - 2 * 57, do, ngan_mm=CHI_NHANH_NGAN_MM)
                for d in _ngat_can_bang(ten_cq, vua_trai, CO_CO_QUAN, True))
    phai = _p(_r('CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM', dam=True, co=CO_QUOC_HIEU), can='center') + \
        _p_gach('Độc lập - Tự do - Hạnh phúc', CO_TIEU_NGU, True, r2 - 2 * 57, do, khe=KHE_TIEU_NGU_PT if do else KHE_GACH_PT)
    # "Số: …/…" và "địa danh, ngày … tháng … năm …" là HAI Ô CÙNG MỘT HÀNG của bảng đầu: cùng cỡ chữ, cùng giãn dòng và khoảng
    # cách trước, canh trên -> hai dòng luôn ngang nhau (người dùng 22/10/2026: không được chênh cao thấp)
    so_o = _p(_r(so, co=CO_SO_NGAY), can='center', truoc=120) + (_p(_r('(DỰ THẢO)', dam=True, co=CO_DU_THAO), can='center') if du_thao else '')
    ngay_o = _p(_r(f'{dia_danh}, {_ngay_chu(ttho["ngay_pa"], da["nam"])}', nghieng=True, co=CO_SO_NGAY), can='center', truoc=120)
    t = [_bang([_hang([_o(trai, r1, doc='top', vien=False), _o(phai, r2, doc='top', vien=False)]),
                _hang([_o(so_o, r1, doc='top', vien=False), _o(ngay_o, r2, doc='top', vien=False)])], [r1, r2], vien=False,
               lui=twip(LAN_LE_DAU_MM[0]))]
    # ---- tên văn bản
    ten = ('PHƯƠNG ÁN ĐIỀU CHỈNH' if dieu_chinh else 'PHƯƠNG ÁN CHI TIẾT' +
           (f' BỔ SUNG (LẦN {lan})' if lan is not None and lan > 1 else ''))
    t += [_p(_r(ten, dam=True, co=CO_TEN_LOAI), can='center', truoc=240, dong=240)]
    t += [_p(_r(x, dam=True, co=CO_TRICH_YEU), can='center', dong=240) for x in TRICH_YEU_DONG]
    ten_da = re.sub(r'^\s*dự\s+án\s+', '', ' '.join(str(da['du_an'] or '').split()), flags=re.I)
    # 23/10/2026 (người dùng): GIỮ đường kẻ ngắn căn giữa dưới tên dự án, CÁCH chữ một khe (đoạn rỗng cao 6 pt có viền dưới - không sát
    # chữ để khỏi mất dấu chấm / dấu dưới); độ dài theo mẫu PDF (~48 mm)
    t += [_p(_r(f'{du_lieu_in.nhan_du_an(ten_da)} {ten_da}', dam=True, co=CO_DU_AN), can='center', sau=0, dong=240), _duong_ke_du_an()]
    # ---- I. chủ sử dụng (bảng ẩn viền: nhãn đậm | nội dung)
    to_chuc = la_to_chuc(ttho['ho_ten'])
    # 22/10/2026: tiêu đề mục I theo chủ sử dụng (du_lieu_in.tieu_de_muc_i - cùng bản Excel); tổ chức chỉ "Tổ chức:" / "Địa chỉ:"
    t.append(_p(_r(du_lieu_in.tieu_de_muc_i(to_chuc), dam=True, co=CO_DE_MUC), truoc=120, sau=60, giu_sau=True))
    hang_i = [(du_lieu_in.NHAN_TO_CHUC if to_chuc else 'Họ và tên:', ttho['ho_ten'])]
    if not to_chuc and ttho['cccd']:
        hang_i.append(('Số CCCD:', ttho['cccd']))
    hang_i.append((du_lieu_in.NHAN_DIA_CHI_TO_CHUC if to_chuc else 'Địa chỉ thường trú:', ttho['dia_chi']))
    if not to_chuc and ttho['dien_thoai']:
        hang_i.append(('Số điện thoại:', ttho['dien_thoai']))
    # 22/10/2026 (mẫu PA_01 / PA_003 người dùng gửi): nhãn chữ thường, tên chủ sử dụng (hàng đầu) in đậm, nội dung khác thường
    c1, c0 = w * 28 // 100, w * 5 // 100
    t.append(_bang([_hang([_o(_p(), c0, vien=False, doc='top'), _o(_p(_r(n, co=CO_THONG_TIN), can='left'), c1, vien=False, doc='top'),
                           _o(_p(_r(v, dam=k == 0, co=CO_THONG_TIN), can='left'), w - c0 - c1, vien=False, doc='top')])
                    for k, (n, v) in enumerate(hang_i)],
                   [c0, c1, w - c0 - c1], vien=False))
    # ---- II. nguồn gốc: mỗi đoạn logic MỘT w:p (du_lieu_in._thong_tin_ho đã nối xuống dòng cứng giữa câu từng thửa - ho_so.
    # lam_sach_doan_van), căn đều, giãn dòng đơn, cách đoạn 6 pt (w:after 120); MỌI đoạn (kể cả gạch đầu dòng "- Thửa đất…")
    # thụt dòng đầu 1 cm, dòng sau về sát lề trái như PDF mẫu PA_01; không w:br, không đoạn rỗng - Word tự bẻ dòng theo lề
    t.append(_p(_r(du_lieu_in.TIEU_DE_MUC_II, dam=True, co=CO_DE_MUC), truoc=120, sau=60, giu_sau=True))
    for doan in (x for x in str(ttho['nguon_goc'] or '').split('\n') if x.strip()):
        t.append(_p(_r(doan, co=CO_NGUON_GOC), dong=DONG_DOAN, sau=SAU_DOAN, dau_dong=THUT_DAU))
    # ---- III. bảng tính toán: tiêu đề KHÔNG keepNext / pageBreakBefore (22/10/2026) - mục III in tiếp ngay dưới mục II ở cuối
    # trang 1 khi còn chỗ; dòng tiêu đề cột lặp ở đầu trang sau (w:tblHeader)
    if dieu_chinh and str(x_lan.ghi_chu or '').strip():
        t.append(_p(_r('Lý do điều chỉnh: ', dam=True, co=CO_NGUON_GOC), _r(' '.join(x_lan.ghi_chu.split()), co=CO_NGUON_GOC), dong=DONG_DOAN,
                    sau=SAU_DOAN, dau_dong=THUT_DAU))
    t.append(_p(_r('III. Bảng tính toán bồi thường, hỗ trợ', dam=True, co=CO_DE_MUC), truoc=120, sau=60))
    rong = rong_cot(_chu_cac_cot(dong, nghiep_vu.so_muc(2)), do)
    tieu_de = tuple(TIEU_DE_COT_BS if kieu != lan_pa.CHINH else TIEU_DE_COT)
    hang = [_hang([_o(_p(_r(x, dam=True, co=CO_BANG), can='center'), rong[i]) for i, x in enumerate(tieu_de)], tieu_de=True)]
    hang += _hang_tu_dong(dong, rong, nghiep_vu.so_muc(2))
    # IV. tái định cư (dòng cuối bảng)
    hang.append(_hang([_o(_p(_r(nhan_tdc, dam=True, co=CO_DE_MUC), can='center', giu_sau=True), rong[0]),
                       _o(_p(_r(du_lieu_in.NHAN_TDC, dam=True, co=CO_DE_MUC),
                             _r(' ' + str(ttho['tai_dinh_cu'] or '').strip(), co=CO_DE_MUC), can='both', giu_sau=not du_thao),
                          sum(rong[1:]), nhap=7)], khong_tach=True))
    # ---- chữ ký: DÒNG CUỐI của bảng mục III, ẩn viền trái / phải / dưới và vạch giữa (22/10/2026). Word giữ liền dòng TỔNG CỘNG
    # + IV + chữ ký (keepNext giữa các dòng cùng bảng); bảng chữ ký riêng sau bảng thì Word bỏ qua keepNext -> chữ ký trơ một trang.
    # Bản dự thảo không có
    if not du_thao:
        def ky(chuc_vu, ten):                           # giãn dòng đơn: khối cuối gọn
            return _p(_r(chuc_vu, dam=True, co=CO_CHU_KY), can='center', truoc=240, dong=240) + \
                ''.join(_p(can='center', dong=240) for _ in range(4)) + _p(_r(ten or '', dam=True, co=CO_CHU_KY), can='center', dong=240)
        an = ('left', 'bottom', 'right')
        # 23/10/2026 (người dùng): LẬP BIỂU - KIỂM TRA - chức vụ ký CĂN ĐỀU, CHIA ĐỀU ba phần bằng nhau, chữ nằm giữa từng phần. Lưới 8 cột
        # của bảng không chia đều ba được -> MỘT ô gộp cả 8 cột chứa bảng ba cột bằng nhau, ẩn viền
        tong = sum(rong)
        # 24/10/2026: cả khối dịch sang TRÁI CHU_KY_LECH_TRAI_MM (lề trái rộng hơn lề phải): tâm ba phần cách đều nhau, mỗi tâm lùi s; cột
        # thứ tư (trống) lấp phần dư bên phải. (Word không nhận tblInd âm của bảng lồng nên chia lại độ rộng cột)
        s = twip(CHU_KY_LECH_TRAI_MM)
        a3 = tong // 3
        cot3 = [a3 - 2 * s, a3 + 2 * s, a3 - 2 * s, tong - (3 * a3 - 2 * s)]
        ky3 = _bang([_hang([_o(ky('LẬP BIỂU', da['nguoi_lap']), cot3[0], doc='top', vien=False),
                            _o(ky('KIỂM TRA', da['nguoi_kiem_tra']), cot3[1], doc='top', vien=False),
                            _o(ky(da['CHUC_VU_KY'], da['nguoi_ky']), cot3[2], doc='top', vien=False),
                            _o(_p(can='center', dong=240), cot3[3], doc='top', vien=False)], khong_tach=True)],
                    cot3, vien=False, le_o=0)
        hang.append(_hang([_o(ky3 + _p(dong=240), tong, nhap=len(rong), doc='top', an_vien=an)], khong_tach=True))
    t.append(_bang(hang, rong, le_o=LE_O, ngoai_sz=12))
    return ''.join(t)


def _chu_cac_cot(dong: list, so_muc_nha) -> dict:
    """{cột: [(chữ, đậm)]} các ô bảng mục III (cùng cách in như noi_dung_chi_tiet) - để chia bề rộng cột theo nội dung."""
    chu, muc_sl = {}, None
    for x in dong:
        loai, gt = x[0], x[1]
        cach_tinh = x[2] if len(x) > 2 else ''
        if loai == 'H':
            muc_sl = 2 if str(gt[0]) == str(so_muc_nha) else None
        dam = loai in ('H', 'T', 'G')
        if loai == 'T' or loai in ('G', 'S'):
            chu.setdefault(6, []).append((_so(gt[6]) if gt[6] else '-', True))
            if loai != 'T' and gt[7]:
                chu.setdefault(7, []).append((str(gt[7]), False))
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
            f'w:right="{twip(LE_MM["phai"])}" w:bottom="{twip(LE_MM["duoi"])}" w:left="{twip(LE_MM["trai"])}" w:header="284" '
            f'w:footer="284" w:gutter="0"/></w:sectPr>')


def xuat_chi_tiet_docx(con, ma_ho: int, file_ra, bc=None, du_thao: bool = False, pa=None, lan=None) -> Path:
    """Ghi phương án chi tiết một hộ ra file .docx (thể thức NĐ 30). Trả đường dẫn file."""
    file_ra = Path(file_ra)
    file_ra.parent.mkdir(parents=True, exist_ok=True)
    du = _goi_docx(noi_dung_chi_tiet(con, ma_ho, bc, du_thao, pa, lan), sect_pr())
    tam = file_ra.with_name(file_ra.name + '.tmp')
    tam.write_bytes(du)
    tam.replace(file_ra)
    return file_ra

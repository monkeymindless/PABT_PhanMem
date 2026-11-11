"""Bộ công cụ OpenXML Word (1.0.19) - dựng file .docx bằng mã, KHÔNG cần Word, KHÔNG thư viện ngoài (chỉ thư viện chuẩn, chạy cả Python
3.8 / Qt5 bản Win 7). Dùng để soạn / nhúng MẪU IN Word vào phần mềm: đoạn, chữ đậm / nghiêng / gạch chân, đường kẻ dưới HỞ (không sát
chữ), bảng có gộp ô ngang / dọc, viền ô, khổ giấy + lề, chỗ trống {ten} điền dữ liệu MỘT lượt (đã thoát ký tự XML), đóng gói .docx.

Đơn vị: cỡ chữ pt; khoảng cách, thụt lề, bề rộng cột = twip (1 pt = 20 twip; mm -> twip bằng twip(mm)).
Ví dụ:
    from pabt import openxml_word as ox
    than = ox.doan(ox.chay('CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM', dam=True, co=13), can='center') + \\
        ox.bang([ox.hang([ox.o(ox.doan(ox.chay('Họ và tên:')), 3000), ox.o(ox.doan(ox.chay('{ho_ten}', dam=True)), 6000)])], [3000, 6000])
    ox.luu('mau.docx', ox.dien_cho_trong(than, {'ho_ten': 'Nguyễn Văn A'}))
Mẫu có sẵn: `python -m pabt.openxml_word mau <file.docx>` ghi một mẫu khung (quốc hiệu, bảng đầu, mục I - III, chữ ký) để mở bằng Word sửa;
mọi chỗ {ten} sẽ được điền khi nhúng vào phần mềm in (xem in_word.noi_dung_chi_tiet làm ví dụ đầy đủ).
Lưu ý: định dạng .doc nhị phân (Word 97-2003) KHÔNG dựng được bằng mã thuần; .docx là OpenXML chuẩn - Word mở / Lưu thành .doc được."""
from __future__ import annotations

import io
import re
import zipfile
from pathlib import Path

W = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'
A4 = (11906, 16838)                         # twip
A3 = (16838, 23811)
FONT = 'Times New Roman'
_RE_CHO = re.compile(r'\{([A-Za-z0-9_.]+)\}')
# 1 pt (sz = phần tám điểm). sz=4 (0,5 pt) + color=auto: WPS / LibreOffice / máy in PDF thường ẩn khung và gạch dưới chữ.
SZ_VIEN = 8
MAU_VIEN = '000000'


def xml_canh_vien(k: str, hien: bool, sz: int = SZ_VIEN) -> str:
    """Một cạnh viền Word. hien=False -> nil (ẩn)."""
    if not hien:
        return f'<w:{k} w:val="nil"/>'
    return f'<w:{k} w:val="single" w:sz="{sz}" w:space="0" w:color="{MAU_VIEN}"/>'


def xml_tbl_borders(vien: bool = True, ngoai_sz: int = SZ_VIEN, trong_sz: int = SZ_VIEN) -> str:
    ks = ('top', 'left', 'bottom', 'right', 'insideH', 'insideV')
    b = ''.join(xml_canh_vien(k, vien, ngoai_sz if k in ('top', 'left', 'bottom', 'right') else trong_sz) for k in ks)
    return f'<w:tblBorders>{b}</w:tblBorders>'


def xml_tc_borders(vien: bool = True, an_vien: tuple = (), sz: int = SZ_VIEN) -> str:
    """Viền từng ô — WPS / LibreOffice hay bỏ tblBorders, chỉ vẽ tcBorders."""
    an = set(('top', 'left', 'bottom', 'right') if not vien else an_vien)
    return '<w:tcBorders>' + ''.join(xml_canh_vien(k, k not in an, sz) for k in ('top', 'left', 'bottom', 'right')) + '</w:tcBorders>'


def xml_p_bdr_duoi(sz: int = SZ_VIEN, space: str = '1') -> str:
    """Đường kẻ ngang dưới đoạn (gạch dưới chữ / dưới tên dự án)."""
    return f'<w:pBdr><w:bottom w:val="single" w:sz="{sz}" w:space="{space}" w:color="{MAU_VIEN}"/></w:pBdr>'


# ---------------------------------------------------------------- đơn vị, thoát ký tự
def twip(mm: float) -> int:
    return int(round(mm / 25.4 * 1440))


def pt(x: float) -> int:
    return int(round(x * 20))


def thoat(s) -> str:
    """Thoát ký tự XML; xuống dòng -> <w:br/> (dùng TRONG một w:t)."""
    s = str(s).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
    s = ''.join(c for c in s if c in '\t\n\r' or (ord(c) >= 32 and not 0xD800 <= ord(c) <= 0xDFFF and c not in '\ufffe\uffff'))          # bỏ ký tự điều khiển (XML không cho phép)
    return s.replace('\r\n', '\n').replace('\n', '</w:t><w:br/><w:t xml:space="preserve">')


# ---------------------------------------------------------------- chữ, đoạn
def chay(chu, dam: bool = False, nghieng: bool = False, gach: bool = False, co: float = 0, font: str = '', mau: str = '',
         hoa: bool = False) -> str:
    """Một đoạn chữ cùng kiểu (w:r). co = cỡ chữ pt (0 = mặc định của tài liệu); mau = 'RRGGBB'; gach = gạch chân sát chữ."""
    pr = (f'<w:rFonts w:ascii="{font}" w:hAnsi="{font}" w:cs="{font}"/>' if font else '') + ('<w:b/><w:bCs/>' if dam else '') + \
        ('<w:i/><w:iCs/>' if nghieng else '') + ('<w:caps/>' if hoa else '') + ('<w:u w:val="single"/>' if gach else '') + \
        (f'<w:color w:val="{mau}"/>' if mau else '') + (f'<w:sz w:val="{int(round(co * 2))}"/><w:szCs w:val="{int(round(co * 2))}"/>' if co else '')
    return f'<w:r>{"<w:rPr>" + pr + "</w:rPr>" if pr else ""}<w:t xml:space="preserve">{thoat(chu)}</w:t></w:r>'


def doan(*cac_chay, can: str = 'both', truoc: int = 0, sau: int = 0, dong: int = 276, dau_dong: int = 0, trai: int = 0, phai: int = 0,
         treo: int = 0, giu_sau: bool = False, giu_dong: bool = False, ngat_trang: bool = False, vien_duoi_pt: float = 0,
         ds_tab: tuple = ()) -> str:
    """Đoạn (w:p). can: left / center / right / both. truoc / sau / dong (240 = đơn) / thụt: twip. treo = thụt lề treo (dòng đầu lùi ra).
    vien_duoi_pt > 0: đường kẻ ngang dưới đoạn cách chân chữ chừng này pt (kết hợp trai / phai để đường kẻ ngắn - xem doan_gach_ho).
    ds_tab: các vị trí tab (twip, canh trái)."""
    ind = ''.join(f' w:{k}="{v}"' for k, v in (('left', trai), ('right', phai), ('firstLine', dau_dong),
                                               ('hanging', treo)) if v)
    pr = ('<w:keepNext/>' if giu_sau else '') + ('<w:keepLines/>' if giu_dong else '') + ('<w:pageBreakBefore/>' if ngat_trang else '') + \
        (xml_p_bdr_duoi(space=f'{vien_duoi_pt:g}') if vien_duoi_pt > 0 else '') + \
        (('<w:tabs>' + ''.join(f'<w:tab w:val="left" w:pos="{x}"/>' for x in ds_tab) + '</w:tabs>') if ds_tab else '') + \
        f'<w:spacing w:before="{truoc}" w:after="{sau}" w:line="{dong}" w:lineRule="auto"/>' + (f'<w:ind{ind}/>' if ind else '') + \
        f'<w:jc w:val="{can}"/>'
    return f'<w:p><w:pPr>{pr}</w:pPr>{"".join(cac_chay)}</w:p>'


def rong_chu(chu: str, co: float = 13, dam: bool = False, do=None) -> float:
    """Bề rộng (pt) của chữ Times New Roman: do(chữ, phông, cỡ, đậm) -> pt nếu có hàm đo thật (vd. Qt), không thì ước theo ký tự
    (chữ hoa 0,72 em, chữ số 0,5, dấu câu hẹp; đậm x 1,06) - ước hơi dư để Word không bẻ dòng."""
    if do:
        return do(str(chu), FONT, co, dam)
    w = 0.0
    for c in str(chu):
        w += (0.5 if c.isdigit() else 0.25 if c in ".,:;' " else 0.36 if c in '()/-' else 0.72 if c.isupper() else 0.5)
    return w * co * (1.06 if dam else 1.0)


def doan_gach_ho(chu: str, rong_chu_pt: float, rong_vung_twip: int, co: float = 13, dam: bool = True, khe_pt: float = 2) -> str:
    """Dòng chữ căn giữa có đường GẠCH DƯỚI HỞ dài đúng bằng chữ (khe_pt giữa chân chữ và đường - không mất dấu dưới "Ị Ộ…"):
    viền dưới của đoạn, thụt hai bên. rong_chu_pt: bề rộng chữ (pt) - rong_chu(chu, co, dam) hoặc đo bằng Qt; rong_vung_twip: bề rộng vùng chứa."""
    ben = max(0, int((rong_vung_twip - rong_chu_pt * 20 - 80) // 2))
    return doan(chay(chu, dam=dam, co=co), can='center', dong=240, trai=ben, phai=ben, vien_duoi_pt=khe_pt)


def doan_ke_ngang(rong_twip: int, rong_vung_twip: int, sau: int = 120) -> str:
    """Đường kẻ ngang ngắn căn giữa (đoạn rỗng có viền dưới, thụt hai bên) - vd. dưới tên dự án."""
    ben = max(0, (rong_vung_twip - rong_twip) // 2)
    return (f'<w:p><w:pPr>{xml_p_bdr_duoi(space="1")}'
            f'<w:spacing w:before="0" w:after="{sau}" w:line="120" w:lineRule="exact"/><w:ind w:left="{ben}" w:right="{ben}"/>'
            f'<w:rPr><w:sz w:val="4"/></w:rPr></w:pPr></w:p>')


# ---------------------------------------------------------------- bảng
def o(noi_dung: str, rong: int, nhap: int = 1, doc: str = 'center', gop_doc: str = '', vien: bool = True, an_vien: tuple = (),
      nen: str = '') -> str:
    """Ô bảng (w:tc). noi_dung = các đoạn (doan(...)); rong twip; nhap = gộp ngang bấy nhiêu cột; gop_doc: 'bat_dau' / 'tiep' = gộp dọc;
    doc: top / center / bottom; vien=False ẩn cả bốn cạnh, an_vien = các cạnh ẩn ('top', 'left', 'bottom', 'right'); nen = 'RRGGBB'."""
    an = ('top', 'left', 'bottom', 'right') if not vien else tuple(an_vien)
    pr = f'<w:tcW w:w="{rong}" w:type="dxa"/>' + (f'<w:gridSpan w:val="{nhap}"/>' if nhap > 1 else '') + \
        ('<w:vMerge w:val="restart"/>' if gop_doc == 'bat_dau' else '<w:vMerge/>' if gop_doc == 'tiep' else '') + \
        xml_tc_borders(vien, an) + \
        (f'<w:shd w:val="clear" w:color="auto" w:fill="{nen}"/>' if nen else '') + f'<w:vAlign w:val="{doc}"/>'
    return f'<w:tc><w:tcPr>{pr}</w:tcPr>{noi_dung or doan()}</w:tc>'


def xml_tr_pr(lap_dau_trang: bool = False, khong_tach: bool = False, cao_twip: int = 0, quy_tac_cao: str = 'atLeast') -> str:
    """Thuộc tính dòng bảng (w:trPr) theo đúng thứ tự lược đồ: cantSplit, trHeight, tblHeader. cao_twip > 0: chiều cao dòng
    (quy_tac_cao 'atLeast' = tối thiểu, chữ nhiều hơn thì dòng tự cao thêm; 'exact' = đúng bằng)."""
    if quy_tac_cao not in ('atLeast', 'exact', 'auto'):
        quy_tac_cao = 'atLeast'
    return (f'<w:cantSplit w:val="{1 if (khong_tach or lap_dau_trang) else 0}"/>' +
            (f'<w:trHeight w:val="{int(cao_twip)}" w:hRule="{quy_tac_cao}"/>' if cao_twip and cao_twip > 0 else '') +
            ('<w:tblHeader/>' if lap_dau_trang else ''))


def hang(cac_o: list, lap_dau_trang: bool = False, khong_tach: bool = False, cao_twip: int = 0, quy_tac_cao: str = 'atLeast') -> str:
    """Dòng bảng (w:tr). lap_dau_trang: dòng tiêu đề lặp ở đầu mỗi trang; khong_tach: không cắt đôi dòng qua trang; cao_twip > 0:
    chiều cao dòng (w:trHeight, quy_tac_cao 'atLeast' / 'exact') - dàn trang cân đối chia khoảng hở cuối trang vào đây (1.1.03)."""
    return f'<w:tr><w:trPr>{xml_tr_pr(lap_dau_trang, khong_tach, cao_twip, quy_tac_cao)}</w:trPr>{"".join(cac_o)}</w:tr>'


def bang(cac_hang: list, rong_cot: list, vien: bool = True, le_o: int = 57, lui: int = 0, can: str = 'center',
         dem_doc_twip: int = 28) -> str:
    """Bảng cố định bề rộng cột (w:tbl). vien: khung + lưới; lui (twip): bắt đầu lùi ra ngoài lề trái (canh trái); dem_doc_twip:
    đệm trên / dưới của ô (mặc định 28 twip = 1,4 pt; đệm trái / phải = le_o)."""
    luoi = ''.join('<w:gridCol w:w="%d"/>' % x for x in rong_cot)
    vt = f'<w:jc w:val="left"/><w:tblInd w:w="{-lui}" w:type="dxa"/>' if lui else f'<w:jc w:val="{can}"/>'
    dem = max(0, int(dem_doc_twip))
    return (f'<w:tbl><w:tblPr><w:tblW w:w="{sum(rong_cot)}" w:type="dxa"/>{vt}{xml_tbl_borders(vien)}'
            f'<w:tblLayout w:type="fixed"/><w:tblCellMar><w:top w:w="{dem}" w:type="dxa"/><w:left w:w="{le_o}" w:type="dxa"/>'
            f'<w:bottom w:w="{dem}" w:type="dxa"/><w:right w:w="{le_o}" w:type="dxa"/></w:tblCellMar></w:tblPr>'
            f'<w:tblGrid>{luoi}</w:tblGrid>{"".join(cac_hang)}</w:tbl>')


# ---------------------------------------------------------------- trang, chỗ trống, đóng gói
def sect_pr(kho: tuple = A4, ngang: bool = False, le_mm: tuple = (15, 10, 10, 10)) -> str:
    """Khổ giấy + lề. le_mm = (trái, trên, phải, dưới) mm."""
    w, h = (kho[1], kho[0]) if ngang else kho
    huong = ' w:orient="landscape"' if ngang else ''
    tr, tren, ph, d = (twip(x) for x in le_mm)
    return (f'<w:sectPr><w:pgSz w:w="{w}" w:h="{h}"{huong}/><w:pgMar w:top="{tren}" '
            f'w:right="{ph}" w:bottom="{d}" w:left="{tr}" w:header="284" w:footer="284" w:gutter="0"/></w:sectPr>')


def rong_vung(kho: tuple = A4, ngang: bool = False, le_mm: tuple = (15, 10, 10, 10)) -> int:
    """Bề rộng vùng chữ (twip) = bề rộng trang trừ lề trái, phải."""
    w = kho[1] if ngang else kho[0]
    return w - twip(le_mm[0]) - twip(le_mm[2])


def cho_trong(xml: str) -> list:
    """Các tên chỗ trống {ten} có trong xml (theo thứ tự xuất hiện, không lặp)."""
    return list(dict.fromkeys(_RE_CHO.findall(xml)))


def dien_cho_trong(xml: str, gia_tri: dict) -> str:
    """Thay {ten} bằng giá trị MỘT lượt (giá trị chứa {khác} không bị thay tiếp), đã thoát ký tự XML; tên không có trong gia_tri giữ nguyên.
    Chỗ trống phải nằm trọn trong một w:t (chuỗi do chay(...) tạo ra luôn như vậy)."""
    return _RE_CHO.sub(lambda m: thoat(gia_tri[m.group(1)]) if m.group(1) in gia_tri else m.group(0), xml)


def goi_docx(than: str, sect: str = '', font: str = FONT, co: float = 13) -> bytes:
    """Gói .docx tối thiểu từ phần thân (các đoạn / bảng) + sectPr; phông, cỡ chữ mặc định, giãn đoạn mặc định. Byte ổn định (ngày cố định)."""
    loai = 'application/vnd.openxmlformats-officedocument.wordprocessingml'
    kieu = (f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:styles xmlns:w="{W}"><w:docDefaults><w:rPrDefault><w:rPr>'
            f'<w:rFonts w:ascii="{font}" w:hAnsi="{font}" w:cs="{font}" w:eastAsia="{font}"/><w:sz w:val="{int(round(co * 2))}"/>'
            f'<w:szCs w:val="{int(round(co * 2))}"/><w:lang w:val="vi-VN"/></w:rPr></w:rPrDefault><w:pPrDefault><w:pPr>'
            '<w:spacing w:after="0"/></w:pPr></w:pPrDefault></w:docDefaults></w:styles>')
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
        'word/styles.xml': kieu,
        'word/document.xml': f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:document xmlns:w="{W}"><w:body>{than}'
        f'{sect or sect_pr()}</w:body></w:document>',
    }
    b = io.BytesIO()
    with zipfile.ZipFile(b, 'w', zipfile.ZIP_DEFLATED) as z:
        for n, x in tep.items():
            z.writestr(zipfile.ZipInfo(n, date_time=(2026, 1, 1, 0, 0, 0)), x.encode('utf-8'), zipfile.ZIP_DEFLATED)
    return b.getvalue()


def luu(file_ra, than: str, sect: str = '', **kieu) -> Path:
    """Ghi file .docx (ghi tạm rồi đổi tên - lỗi giữa chừng không để file hỏng). kieu: font=, co=."""
    p = Path(file_ra)
    p.parent.mkdir(parents=True, exist_ok=True)
    tam = p.with_name(p.name + '.tmp')
    tam.write_bytes(goi_docx(than, sect, **kieu))
    tam.replace(p)
    return p


def doc_than(file_docx) -> str:
    """Phần thân (w:body, không kể sectPr) của một file .docx - để nhúng mẫu người dùng soạn bằng Word vào phần mềm in."""
    with zipfile.ZipFile(file_docx) as z:
        x = z.read('word/document.xml').decode('utf-8')
    m = re.search(r'<w:body>(.*)</w:body>', x, re.S)
    if not m:
        raise ValueError('File không phải .docx hợp lệ (thiếu w:body).')
    return re.sub(r'<w:sectPr\b.*?</w:sectPr>\s*$', '', m.group(1), flags=re.S)


# ---------------------------------------------------------------- mẫu khung (ví dụ)
def mau_khung() -> tuple:
    """(thân, sectPr) của một MẪU KHUNG phương án: quốc hiệu, bảng đầu, tên văn bản, mục I - III, chữ ký. Chỗ trống {ten} điền khi in."""
    w = rong_vung()
    r1, r2 = w * 45 // 100, w - w * 45 // 100
    dau = bang([
        hang([o(doan(chay('{don_vi_cap_tren}', co=13), can='center') + doan_gach_ho('{don_vi_tieu_de}', rong_chu('CHI NHÁNH TÊN ĐƠN VỊ', 13, True), r1), r1, doc='top', vien=False),
              o(doan(chay('CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM', dam=True, co=13), can='center') +
                doan_gach_ho('Độc lập - Tự do - Hạnh phúc', rong_chu('Độc lập - Tự do - Hạnh phúc', 14, True), r2, co=14), r2, doc='top', vien=False)]),
        hang([o(doan(chay('Số: {so_pa}/{ky_hieu_so}', co=13), can='center', truoc=120), r1, doc='top', vien=False),
              o(doan(chay('{dia_danh}, ngày {ngay} tháng {thang} năm {nam}', nghieng=True, co=13), can='center', truoc=120), r2,
                doc='top', vien=False)])], [r1, r2], vien=False)
    cot = [800, 3400, 900, 1000, 1400, 900, 1700]
    cot[1] += w - sum(cot)
    tieu = hang([o(doan(chay(t, dam=True), can='center'), c) for t, c in zip(
        ('STT', 'Tên tài sản', 'ĐVT', 'Số lượng', 'Đơn giá', 'Tỷ lệ', 'Thành tiền'), cot)], lap_dau_trang=True)
    dong = hang([o(doan(chay(t), can='left' if i == 1 else 'right'), c) for i, (t, c) in enumerate(zip(
        ('{stt}', '{ten}', '{dvt}', '{so_luong}', '{don_gia}', '{ty_le}', '{thanh_tien}'), cot))])
    than = (dau + doan(chay('PHƯƠNG ÁN CHI TIẾT', dam=True, co=14), can='center', truoc=240) +
            doan(chay('DỰ ÁN {du_an}', dam=True, co=14), can='center') + doan_ke_ngang(twip(70), w) +
            doan(chay('I. Thông tin chủ sử dụng', dam=True, co=14), giu_sau=True) +
            doan(chay('Họ và tên: {ho_ten}'), can='left') + doan(chay('Địa chỉ: {dia_chi}'), can='left') +
            doan(chay('II. Thông tin vị trí, nguồn gốc đất:', dam=True, co=14), truoc=120, giu_sau=True) +
            doan(chay('{nguon_goc}'), dau_dong=567) +
            doan(chay('III. Bảng tính toán bồi thường, hỗ trợ', dam=True, co=14), truoc=120, giu_sau=True) +
            bang([tieu, dong], cot) +
            doan(chay('LẬP BIỂU', dam=True, co=15), can='center', truoc=240))
    return than, sect_pr()


def _main(argv: list) -> int:
    if len(argv) >= 3 and argv[1] == 'mau':
        than, sect = mau_khung()
        print(luu(argv[2], than, sect))
        return 0
    print(__doc__)
    return 0


if __name__ == '__main__':
    import sys
    raise SystemExit(_main(sys.argv))

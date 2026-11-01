"""Đường kẻ (hình vẽ DrawingML) của bản in Excel - tách khỏi in_an.py (1.0.28; in_an nhập lại mọi tên cho mã gọi cũ).

openpyxl làm mất hình vẽ khi đọc / ghi: đường kẻ dưới tên cơ quan, dưới quốc hiệu, dưới tên dự án được dựng lại (in_an.dk_mac_dinh,
in_an.can_duong_ke) rồi chèn vào file bản in SAU khi openpyxl lưu. Chỉ thư viện chuẩn (zipfile) - không openpyxl, không Qt."""
from __future__ import annotations

import os
import re
import zipfile
from pathlib import Path

_DS_DR = 'http://schemas.openxmlformats.org/drawingml/2006/spreadsheetDrawing'
_DS_A = 'http://schemas.openxmlformats.org/drawingml/2006/main'
_DS_R = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'
_NET = '<a:ln w="12700"><a:solidFill><a:srgbClr val="000000"/></a:solidFill></a:ln>'  # 1 pt (9525 = 0,75 pt — máy in/WPS hay ẩn)
_SHEET = 'xl/worksheets/sheet1.xml'
_RE_NEO_HINH = re.compile(r'<xdr:twoCellAnchor\b.*?</xdr:twoCellAnchor>', re.S)


def _them_bo_qua_loi(sx: str, bo_qua: str) -> str:
    """Chèn <ignoredErrors> (numberStoredAsText) cho các ô bo_qua ("C9 C11") vào XML sheet - đúng vị trí theo lược đồ: trước drawing /
    legacyDrawing / … / extLst. openpyxl không ghi phần này."""
    if not bo_qua.strip() or '<ignoredErrors' in sx:
        return sx
    vi = min((i for i in (sx.find(t) for t in ('<smartTags', '<drawing', '<legacyDrawing', '<picture', '<oleObjects', '<controls',
                                                '<tableParts', '<extLst', '</worksheet>')) if i >= 0))
    return sx[:vi] + f'<ignoredErrors><ignoredError sqref="{bo_qua.strip()}" numberStoredAsText="1"/></ignoredErrors>' + sx[vi:]


def ghi_zip_nguyen_tu(p: Path, tep: dict) -> None:
    """Ghi lại file zip (.xlsx) từ {tên phần: bytes}: ghi file tạm cạnh file rồi os.replace - lỗi giữa chừng (đầy đĩa, file đang mở)
    không để lại file hỏng / file .tmp. [Content_Types].xml đứng đầu như Excel ghi."""
    p = Path(p)
    tam = p.with_name(p.name + '.tmp')
    try:
        with zipfile.ZipFile(tam, 'w', zipfile.ZIP_DEFLATED) as zo:
            for k in ['[Content_Types].xml'] + [x for x in tep if x != '[Content_Types].xml']:
                zo.writestr(k, tep[k])
        os.replace(tam, p)
    except BaseException:
        if tam.exists():
            tam.unlink()
        raise


_ghi_zip = ghi_zip_nguyen_tu                        # tên cũ trong in_an


def chen_duong_ke(file_xlsx, xml: str = '', bo_qua: str = '') -> bool:
    """Chèn các đường kẻ (XML) vào sheet đầu của file .xlsx do openpyxl lưu. Trả True nếu đã chèn. xml: nội dung đã canh lại
    (can_duong_ke; từ 1.0.20 không còn file .duong_ke.xml). bo_qua (1.0.07): các ô Excel không gắn cờ "số lưu dạng chữ" (CCCD, điện thoại)."""
    p = Path(file_xlsx)
    if not xml.strip() and not bo_qua.strip():
        return False
    with zipfile.ZipFile(p) as zi:
        tep = {n: zi.read(n) for n in zi.namelist()}
    sx = _them_bo_qua_loi(str(tep[_SHEET], 'utf-8'), bo_qua)
    if not xml.strip() or '<drawing ' in sx:
        if bo_qua.strip():
            tep[_SHEET] = sx.encode('utf-8')
            ghi_zip_nguyen_tu(p, tep)
        return False
    n = 1
    while f'xl/drawings/drawing{n}.xml' in tep:
        n += 1
    rid = 'rIdDuongKe1'
    srel = 'xl/worksheets/_rels/sheet1.xml.rels'
    rels = str(tep[srel], 'utf-8') if srel in tep else \
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"></Relationships>'
    rels = rels.replace('</Relationships>', f'<Relationship Id="{rid}" Type="{_DS_R}/drawing" Target="../drawings/drawing{n}.xml"/></Relationships>')
    if 'xmlns:r=' not in sx[:1000]:
        sx = sx.replace('<worksheet ', f'<worksheet xmlns:r="{_DS_R}" ', 1)
    vi = min((i for i in (sx.find(t) for t in ('<legacyDrawing', '<picture', '<oleObjects', '<controls', '<tableParts', '<extLst',
                                                '</worksheet>')) if i >= 0))
    sx = sx[:vi] + f'<drawing r:id="{rid}"/>' + sx[vi:]
    ct = str(tep['[Content_Types].xml'], 'utf-8').replace(
        '</Types>', f'<Override PartName="/xl/drawings/drawing{n}.xml" '
                    'ContentType="application/vnd.openxmlformats-officedocument.drawing+xml"/></Types>')
    tep[_SHEET], tep[srel], tep['[Content_Types].xml'] = sx.encode('utf-8'), rels.encode('utf-8'), ct.encode('utf-8')
    tep[f'xl/drawings/drawing{n}.xml'] = (f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<xdr:wsDr xmlns:xdr="{_DS_DR}" '
                                          f'xmlns:a="{_DS_A}">' + xml + '</xdr:wsDr>').encode('utf-8')
    ghi_zip_nguyen_tu(p, tep)
    return True


def doc_duong_ke(file_xlsx) -> str:
    """Các đường kẻ (các khối <xdr:twoCellAnchor>, nối liền) trong hình vẽ của sheet đầu file .xlsx - '' khi không có. Ngược của
    chen_duong_ke (kiểm tra bản in, so hai bản)."""
    with zipfile.ZipFile(Path(file_xlsx)) as zi:
        ten = zi.namelist()
        srel = 'xl/worksheets/_rels/sheet1.xml.rels'
        if srel not in ten:
            return ''
        rels = str(zi.read(srel), 'utf-8')
        kq = []
        for dich in re.findall(r'Type="[^"]*/drawing" Target="\.\./drawings/([^"]+)"', rels):
            ten_hinh = f'xl/drawings/{dich}'
            if ten_hinh in ten:
                kq += _RE_NEO_HINH.findall(str(zi.read(ten_hinh), 'utf-8'))
    return ''.join(kq)

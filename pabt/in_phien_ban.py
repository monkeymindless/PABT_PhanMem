"""Bốn luồng in pháp lý tách biệt theo phiên bản phương án (1.0.63). Không Qt. Mỗi mẫu CHỈ đọc đúng phiên bản của nó, không in nhầm số đang thử ra giấy niêm yết / tờ trình.

  Mẫu 01  Phiếu dự thảo gửi hộ dân, bảng niêm yết: V1 (chưa có thì chốt V1 từ số hiện hành); nhúng mã định danh hộ.
  Mẫu 02  PA dự thảo điều chỉnh lần n phục vụ đối thoại: V2.n, nhãn "DỰ THẢO PHỤC VỤ ĐỐI THOẠI LẦN n".
  Mẫu 03  Bảng đối chiếu, giải trình chênh lệch V1 | V2.n | V3 (+/-), đính kèm hồ sơ thẩm định.
  Mẫu 04  PA chính thức trình thẩm định, phê duyệt: V3.

Word dùng chung in_word.xuat_chi_tiet_docx (tham số pa=), Excel qua an_toan.luu_xlsx (du_thao._ghi_excel)."""
from __future__ import annotations

import re
import zipfile
from pathlib import Path

from . import in_word
from . import phien_ban_pa as pb
from .lap_pa import LoiNhap
from .tien import vn

MAU = (('01', 'Mẫu 01: PA dự thảo niêm yết (V1)'), ('02', 'Mẫu 02: PA dự thảo đối thoại (V2.n)'),
       ('03', 'Mẫu 03: Bảng đối chiếu, giải trình chênh lệch'), ('04', 'Mẫu 04: PA chính thức trình duyệt (V3)'))


_CORE = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?><cp:coreProperties '
         'xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" xmlns:dc="http://purl.org/dc/elements/1.1/">'
         '<dc:identifier>{ma}</dc:identifier></cp:coreProperties>')


def nhung_ma_dinh_danh(file, ma: str) -> None:
    """Ghi mã định danh hộ vào thuộc tính tài liệu Word (dc:identifier), không đổi nội dung trang in. Gói Word của phần mềm chưa có docProps/core.xml: thêm vào."""
    if not ma:
        return
    file = Path(file)
    tam = file.with_name(file.name + '.ma')
    with zipfile.ZipFile(file) as z, zipfile.ZipFile(tam, 'w', zipfile.ZIP_DEFLATED) as ra:
        co_core = 'docProps/core.xml' in z.namelist()
        for it in z.infolist():
            du = z.read(it.filename)
            chu = None
            if it.filename == 'docProps/core.xml':
                chu = re.sub(r'<dc:identifier>.*?</dc:identifier>', '', du.decode('utf-8'), flags=re.S).replace(
                    '</cp:coreProperties>', f'<dc:identifier>{ma}</dc:identifier></cp:coreProperties>')
            elif not co_core and it.filename == '[Content_Types].xml':
                chu = du.decode('utf-8').replace('</Types>', '<Override PartName="/docProps/core.xml" '
                                                 'ContentType="application/vnd.openxmlformats-package.core-properties+xml"/></Types>')
            elif not co_core and it.filename == '_rels/.rels':
                chu = du.decode('utf-8').replace('</Relationships>', '<Relationship Id="rIdCoreLarc" Type="http://schemas.openxmlformats.org/package/2006/relationships/'
                                                 'metadata/core-properties" Target="docProps/core.xml"/></Relationships>')
            ra.writestr(it, du if chu is None else chu.encode('utf-8'))
        if not co_core:
            ra.writestr('docProps/core.xml', _CORE.format(ma=ma).encode('utf-8'))
    tam.replace(file)


def doc_ma_dinh_danh(file) -> str:
    with zipfile.ZipFile(file) as z:
        if 'docProps/core.xml' not in z.namelist():
            return ''
        m = re.search(r'<dc:identifier>(.*?)</dc:identifier>', z.read('docProps/core.xml').decode('utf-8'))
    return m.group(1) if m else ''


def mau_01(con, ds_ma_ho, thu_muc, ten_dot: str = '') -> list:
    """Chốt V1 rồi xuất phiếu dự thảo từng hộ theo V1. Trả các file."""
    thu_muc = Path(thu_muc)
    pb.khoa_v1_nhieu(con, ds_ma_ho, ten_dot)
    kq = []
    for ma in ds_ma_ho:
        r = pb.lay(con, ma, pb.V1)
        pa = pb.pa_tu_json(con, ma, r['du_lieu']) if r else pb.doc_pa(con, ma, pb.V0)     # file chỉ xem: in theo số đang có
        f = in_word.xuat_chi_tiet_docx(con, ma, thu_muc / f'Mau01_V1_Ho{ma}.docx', du_thao=True, pa=pa, lan=r['lan'] if r else None)
        nhung_ma_dinh_danh(f, pb.uuid_ho(con, ma))
        kq.append(f)
    return kq


def so_lan_v2(ma: str) -> int:
    m = re.match(r'^V2\.(\d+)$', ma or '')
    if not m:
        raise LoiNhap('Mẫu 02 chỉ in nhánh V2.n.')
    return int(m.group(1))


def mau_02(con, ma_ho: int, ma_v2: str, file) -> Path:
    n = so_lan_v2(ma_v2)
    r = pb.lay(con, ma_ho, ma_v2)
    if r is None:
        raise LoiNhap(f'Hộ {ma_ho} chưa có {ma_v2}.')
    pa = pb.pa_tu_json(con, ma_ho, r['du_lieu'])
    f = in_word.xuat_chi_tiet_docx(con, ma_ho, file, du_thao=True, pa=pa, lan=r['lan'], nhan_du_thao=f'DỰ THẢO PHỤC VỤ ĐỐI THOẠI LẦN {n}')
    nhung_ma_dinh_danh(f, pb.uuid_ho(con, ma_ho))
    return f


def mau_03(con, ds_ma_ho, file, tieu_de: str = '') -> Path:
    """Excel 2 sheet: tổng hợp từng hộ và chi tiết từng dòng (V1, V2.n, V3, tăng / giảm, lý do giải trình)."""
    from .du_thao import _ghi_excel
    from .nghiep_vu import BoiCanh
    bc = BoiCanh.tu(con)
    tong, ct = [], []
    ten = {r[0]: r[1] for r in con.execute('SELECT ma_ho, ho_ten FROM ho')}
    for i, ma in enumerate(ds_ma_ho, 1):
        d = pb.doi_chieu_ho(con, ma, bc=bc)
        t = d['tong']
        tong.append({'STT': i, 'Mã hộ': ma, 'Họ và tên': ten.get(ma, ''), 'PA niêm yết (V1)': vn(t[pb.V1]), 'PA sau ý kiến (V2)': vn(t['V2']), 'Nhánh V2': d['v2'],
                     'Chênh lệch V2 - V1': _dau(t['d1']), 'PA trình duyệt (V3)': vn(t[pb.V3]), 'Chênh lệch V3 - V1': _dau(t['d2']), 'Lý do điều chỉnh, căn cứ giải trình': d['ly_do']})
        for x in d['dong']:
            ct.append({'Mã hộ': ma, 'Họ và tên': ten.get(ma, ''), 'Nhóm': pb.TEN_NHOM.get(x['nhom'], pb.TEN_THUONG), 'Nội dung': x['ten'], 'ĐVT': x['dvt'],
                       'Đơn giá V1': vn(x['dg1']), 'Thành tiền V1': vn(x['tt1']), 'Đơn giá V2': vn(x['dg2']), 'Thành tiền V2': vn(x['tt2']), 'Chênh lệch V2 - V1': _dau(x['d1']),
                       'Đơn giá V3': vn(x['dg3']), 'Thành tiền V3': vn(x['tt3']), 'Chênh lệch V3 - V1': _dau(x['d2']), 'Trạng thái': x['trang_thai']})
    td = tieu_de or 'BẢNG TỔNG HỢP ĐỐI CHIẾU VÀ GIẢI TRÌNH CHÊNH LỆCH SAU NIÊM YẾT'
    return _ghi_excel(file, [('Tổng hợp', td, tong), ('Chi tiết', td + ' - chi tiết từng dòng', ct)])


def _dau(x) -> str:
    return ('+' if x > 0 else '') + vn(x)


def mau_04(con, ma_ho: int, file) -> Path:
    r = pb.lay(con, ma_ho, pb.V3)
    if r is None:
        raise LoiNhap(f'Hộ {ma_ho} chưa có phương án trình duyệt V3: chốt V3 ở bảng đối chiếu trước.')
    f = in_word.xuat_chi_tiet_docx(con, ma_ho, file, du_thao=False, pa=pb.pa_tu_json(con, ma_ho, r['du_lieu']), lan=r['lan'])
    nhung_ma_dinh_danh(f, pb.uuid_ho(con, ma_ho))
    return f

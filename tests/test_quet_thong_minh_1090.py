"""1.0.90 - Quét file thông minh: chữ phông cũ TCVN3 / VNI, Word đọc đủ (số / gạch đầu dòng tự động, ngắt dòng), lớp chữ PDF hỏng, nhận địa bàn
không đoán bừa, phân cấp văn bản, hộp kết quả (cấu trúc lọc được, tìm, lưu). Dữ liệu tổng hợp - không dùng file thật."""
from __future__ import annotations

import os
import tempfile
import unittest
import zipfile
from pathlib import Path

from pabt import chuan_chu, quet_chung as qc

W = 'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"'


def _docx(p: Path, than: str, kieu: str = '', so: str = '') -> Path:
    with zipfile.ZipFile(p, 'w') as z:
        z.writestr('[Content_Types].xml', '<?xml version="1.0"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"/>')
        z.writestr('word/document.xml', f'<?xml version="1.0" encoding="UTF-8"?><w:document {W}><w:body>{than}</w:body></w:document>')
        if kieu:
            z.writestr('word/styles.xml', f'<?xml version="1.0" encoding="UTF-8"?><w:styles {W}>{kieu}</w:styles>')
        if so:
            z.writestr('word/numbering.xml', f'<?xml version="1.0" encoding="UTF-8"?><w:numbering {W}>{so}</w:numbering>')
    return p


def _p(chu: str, phong: str = '', so: str = '') -> str:
    rpr = f'<w:rPr><w:rFonts w:ascii="{phong}" w:hAnsi="{phong}"/></w:rPr>' if phong else ''
    ppr = f'<w:pPr><w:numPr><w:ilvl w:val="0"/><w:numId w:val="{so}"/></w:numPr></w:pPr>' if so else ''
    return f'<w:p>{ppr}<w:r>{rpr}<w:t xml:space="preserve">{chu}</w:t></w:r></w:p>'


SO_DIEU = ('<w:abstractNum w:abstractNumId="1"><w:lvl w:ilvl="0"><w:start w:val="1"/><w:numFmt w:val="decimal"/>'
           '<w:lvlText w:val="Điều %1."/></w:lvl></w:abstractNum>'
           '<w:abstractNum w:abstractNumId="2"><w:lvl w:ilvl="0"><w:start w:val="1"/><w:numFmt w:val="bullet"/>'
           '<w:lvlText w:val=""/></w:lvl></w:abstractNum>'
           '<w:num w:numId="5"><w:abstractNumId w:val="1"/></w:num><w:num w:numId="6"><w:abstractNumId w:val="2"/></w:num>')


class TestChuanChu(unittest.TestCase):
    def test_tcvn3_vni_nfc(self):
        self.assertEqual(chuan_chu.tcvn3_sang_unicode('QuyÕt ®Þnh båi th­êng'.replace('ê', 'ê')), 'Quyết định bồi thường')
        self.assertEqual(chuan_chu.tcvn3_sang_unicode('uû ban nh©n d©n', hoa=True), 'UỶ BAN NHÂN DÂN')
        self.assertEqual(chuan_chu.vni_sang_unicode('Vieät Nam, Thaønh phoá, ñaát ôû'), 'Việt Nam, Thành phố, đất ở')
        self.assertEqual(chuan_chu.chuan_hoa('Hòa​ x'), 'Hòa x')                 # NFD -> NFC, ký tự vô hình, nbsp
        self.assertEqual(chuan_chu.loai_phong('.VnTimeH'), 'tcvn3_hoa')
        self.assertEqual(chuan_chu.loai_phong('Times New Roman'), '')

    def test_khong_doi_chu_unicode_dung(self):
        dung = 'Quyết định số 03/2026/QĐ-UBND về hệ số điều chỉnh giá đất trên địa bàn thành phố Đồng Nai năm 2026'
        self.assertEqual(chuan_chu.sua_chu(dung), (dung, ''))
        nguoc = {v: chr(k) for k, v in chuan_chu._TCVN3.items()}
        cu = ''.join(nguoc.get(c, c) for c in 'Quyết định số 03 về hệ số điều chỉnh giá đất trên địa bàn')   # mã TCVN3 đọc thẳng
        ra, lp = chuan_chu.sua_chu(cu)
        self.assertEqual(lp, 'tcvn3')
        self.assertTrue(ra.startswith('Quyết định số 03'))


class TestDocWordDayDu(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.addCleanup(self.td.cleanup)

    def test_so_tu_dong_gach_dau_dong_ngat_dong_phong_cu(self):
        than = (_p('Phạm vi điều chỉnh', so='5') + _p('Đối tượng áp dụng', so='5') + _p('Có bề rộng ≥5m', so='6')
                + '<w:p><w:r><w:t>Dòng một</w:t><w:br/><w:t>Dòng hai</w:t></w:r></w:p>'
                + _p('QuyÕt ®Þnh', phong='.VnTime'))
        f = _docx(Path(self.td.name) / 'a.docx', than, so=SO_DIEU)
        nd, tt = qc.doc_toan_van(f)
        dong = nd.splitlines()
        self.assertEqual(dong[:3], ['Điều 1. Phạm vi điều chỉnh', 'Điều 2. Đối tượng áp dụng', '- Có bề rộng ≥5m'])
        self.assertEqual(dong[3:5], ['Dòng một', 'Dòng hai'])
        self.assertEqual(dong[5], 'Quyết định')                                   # phông TCVN3 -> Unicode
        self.assertIn('Word', tt['cach_doc'])
        # đường đọc chung (nhập bảng giá, bộ đơn giá): đổi phông cũ, KHÔNG thêm số tự động (không đổi cách đọc ô bảng của các bộ nhập)
        from pabt.nhap_don_gia import doc_bang
        chung = [r[0] for r in doc_bang(f)]
        self.assertEqual(chung[0], 'Phạm vi điều chỉnh')
        self.assertIn('Quyết định', chung)

    def test_phong_cu_theo_kieu_mac_dinh(self):
        kieu = ('<w:docDefaults><w:rPrDefault><w:rPr><w:rFonts w:ascii=".VnTime" w:hAnsi=".VnTime"/></w:rPr></w:rPrDefault></w:docDefaults>'
                '<w:style w:styleId="TieuDe"><w:rPr><w:rFonts w:ascii=".VnTimeH"/></w:rPr></w:style>')
        than = (_p('båi th­êng') + '<w:p><w:pPr><w:pStyle w:val="TieuDe"/></w:pPr><w:r><w:t>quyÕt ®Þnh</w:t></w:r></w:p>')
        f = _docx(Path(self.td.name) / 'b.docx', than, kieu=kieu)
        self.assertEqual(qc.doc_toan_van(f)[0].splitlines(), ['bồi thường', 'QUYẾT ĐỊNH'])


class TestLopChuHongVaDiaBan(unittest.TestCase):
    def test_lop_chu_pdf_hong(self):
        hong = ('UY BAN NHAN DAN THANH PHO DONG NAI ceNG no,q, xA HeI cHU Ncni^l vIFT NAM QUYET DINH Quy ilinh trQ s5 Aidu chinh gi6 dAt '
                'Cdn ctb LuQt Td chtbc chinh quyin dia phuong s6 duqc stra aAi theo Luat Dat dai nam 2024 cua Quoc hoi va ') * 3
        self.assertTrue(qc.lop_chu_hong(hong))
        self.assertFalse(qc.lop_chu_hong('Quyết định về bồi thường, hỗ trợ khi Nhà nước thu hồi đất trên địa bàn tỉnh. ' * 20))
        self.assertFalse(qc.lop_chu_hong('This is an English report about software quality and architecture. ' * 20))

    def test_dia_ban_khong_doan_bua(self):
        self.assertEqual(qc.nhan_dien_tham_so('Thửa tại Phường Tân Triều, mặt đường nhựa.')['dia_ban'], 'Bảng 8. Phường Tân Triều')
        nhieu = 'Bảng giá: xã Trị An, xã Tân An, xã Phú Lý, phường Tân Triều, phường Biên Hòa, phường Long Bình, xã Xuân Lộc.'
        self.assertNotIn('dia_ban', qc.nhan_dien_tham_so(nhieu))                # văn bản toàn tỉnh: không gán bừa một xã
        ap_dao = 'Dự án qua xã Trị An. Thửa 12 xã Trị An, thửa 15 xã Trị An; giáp ranh xã Tân An.'
        self.assertEqual(qc.nhan_dien_tham_so(ap_dao)['dia_ban'], 'Bảng 53. Phường Trị An')


class TestPhanCap(unittest.TestCase):
    def test_dan_y(self):
        nd = '\n'.join(['QUYẾT ĐỊNH', 'Chương I', 'QUY ĐỊNH CHUNG', 'Điều 1. Phạm vi điều chỉnh', '1. Quyết định này quy định hệ số.',
                        'a) Hệ số điều chỉnh mức biến động thị trường;', 'Điều 2. Hiệu lực', 'TT\tTên đường\tHệ số', '1\tĐường A\t1,2',
                        '2. Không phải khoản (sau bảng vẫn trong Điều 2)', 'Phụ lục II'])
        ds = qc.phan_cap(nd, 'a.docx')
        self.assertEqual([(x['cap'], x['nhan']) for x in ds],
                         [(1, 'Chương I'), (3, 'Điều 1'), (4, 'Khoản 1'), (5, 'Điểm a'), (3, 'Điều 2'), (6, 'Bảng'), (4, 'Khoản 2'), (1, 'Phụ lục II')])

    def test_quet_ghi_chat_luong_va_cau_truc(self):
        kq = qc.quet(['a.txt'], doc=lambda p: 'Điều 1. Phạm vi\n1. Nội dung khoản một của điều.\nĐiều 2. Hiệu lực')
        self.assertEqual(len(kq.cau_truc), 3)
        self.assertEqual(kq.chat_luong[0]['file'], 'a.txt')
        kq = qc.quet(['b.txt'], doc=lambda p: '')
        self.assertTrue(any('không có chữ' in x for x in kq.loi))


@unittest.skipIf(os.environ.get('QT_QPA_PLATFORM') is None and False, '')
class TestHopKetQua(unittest.TestCase):
    def test_cau_truc_loc_tim_luu(self):
        from tests import APP  # noqa: F401 - khởi tạo QApplication
        from pabt.man_hinh_quet_chung import HopKetQuaQuet
        nd = 'Điều 1. Bồi thường về đất\n1. Hệ số K theo đoạn đường.\nĐiều 2. Hỗ trợ ổn định đời sống\n1. Mức hỗ trợ theo nhân khẩu.'
        kq = qc.quet(['a.txt'], doc=lambda p: nd)
        h = HopKetQuaQuet(None, kq)
        h.im_lang = True
        self.addCleanup(h.deleteLater)
        self.assertEqual(h.cay.topLevelItemCount(), 2)                      # Điều -> Khoản lồng dưới
        self.assertEqual(h.cay.topLevelItem(0).childCount(), 1)
        h.o_loc_ct.setText('ho tro')                                        # lọc không dấu
        self.assertTrue(h.cay.topLevelItem(0).isHidden())
        self.assertFalse(h.cay.topLevelItem(1).isHidden())
        h.o_loc_ct.setText('')
        h.cb_cap.setCurrentIndex(h.cb_cap.findData(4))                       # chỉ Khoản: Điều cha vẫn hiện để thấy đường dẫn
        self.assertFalse(h.cay.topLevelItem(0).isHidden())
        self.assertTrue(h.tim_tiep('nhân khẩu'))
        self.assertFalse(h.tim_tiep('không có chữ này'))
        with tempfile.TemporaryDirectory() as td:
            f = h.luu_toan_van(str(Path(td) / 'nd.txt'))
            self.assertIn('Hỗ trợ ổn định đời sống', Path(f).read_text(encoding='utf-8-sig'))
        self.assertEqual(h.b_file.columnCount(), 4)


if __name__ == '__main__':
    unittest.main()

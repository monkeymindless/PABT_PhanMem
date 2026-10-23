"""Xuất lô phương án chi tiết bản Word + gộp một PDF (người dùng 21/10/2026: "chạy thực tế 1.000 hộ, cán bộ không thao tác tay").
- HopIn: phương án chi tiết luôn xuất bản Word (.docx) chuẩn Nghị định 30 (22/10/2026 - không còn lựa chọn Excel).
- o_word + PDF + o_gop: Word chuyển từng hộ sang PDF rồi gộp thành MỘT file PHUONG_AN_CHI_TIET.pdf, đủ trang, khổ A4, lề NĐ 30.
- Word treo một hộ (quá hạn / hộ): bỏ qua hộ đó, làm tiếp các hộ sau; hộ không có PDF / máy không có Word: PDF dự phòng (Qt) từ
  bản Excel - lô không dừng, không thiếu hộ khi gộp.
Word được thay bằng chương trình giả lập (đọc cùng danh sách việc, ghi PDF theo khổ / lề trong file .docx); bài TestWordThat chạy
Microsoft Word thật khi máy có Word. Số liệu GIẢ LẬP.
"""
from __future__ import annotations

import os
import sys
import tempfile
import time
import unittest
import zipfile
from pathlib import Path
from unittest import mock
from xml.etree import ElementTree as ET

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

from PySide6.QtWidgets import QApplication                                       # noqa: E402

from pabt import csdl, in_an                                          # noqa: E402
from pabt import van_ban_trinh as vb                                             # noqa: E402
from tests.test_van_ban_trinh import _co_word                                    # noqa: E402

W = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
SO_HO = 5

# chương trình giả lập Word: đối số = danh sách việc (UTF-16, "chế độ<Tab>vào<Tab>ra"), file cờ dừng; mỗi việc xong in "XONG"
# như trình điều khiển VBS. GIA_WORD_TREO: hộ có chuỗi này trong tên file thì treo; GIA_WORD_KHONG_CO=1: máy không có Word
GIA_WORD = r'''
import os, sys, time, zipfile, re
from pypdf import PdfWriter
if os.environ.get('GIA_WORD_KHONG_CO') == '1':
    sys.stderr.write('KHONG_CO_WORD\n'); sys.exit(3)
treo = os.environ.get('GIA_WORD_TREO', '')
viec = open(sys.argv[1], encoding='utf-16').read().splitlines()
for dong in viec:
    if os.path.exists(sys.argv[2]):
        break
    che_do, vao, ra = dong.split('\t')
    if treo and treo in os.path.basename(vao):
        time.sleep(120)
    x = zipfile.ZipFile(vao).read('word/document.xml').decode('utf-8')
    w = int(re.search(r'<w:pgSz w:w="(\d+)"', x).group(1)) / 20
    h = int(re.search(r'w:h="(\d+)"', x).group(1)) / 20
    le = re.search(r'<w:pgMar w:top="(\d+)" w:right="(\d+)" w:bottom="(\d+)" w:left="(\d+)"', x).groups()
    pdf = PdfWriter()
    pdf.add_blank_page(w, h)
    pdf.add_metadata({'/LeTwip': ','.join(le), '/Nguon': os.path.basename(vao)})
    with open(ra, 'wb') as f:
        pdf.write(f)
    sys.stdout.write('XONG\n'); sys.stdout.flush()
'''


def _du_an(td: Path) -> Path:
    from pabt import du_an_moi
    dong = [dict(ho_ten=f'Hộ lô {i}', dia_chi='Ấp 1', so_to='3', so_thua=str(200 + i), loai_dat='CLN', dt_thu_hoi=str(100 + i),
                 vi_tri='1') for i in range(SO_HO)]
    p = td / 'lo.pabt'
    du_an_moi.tao_du_an(p, dict(ten='Thử lô', cap_dia_ban='Xã', ten_dia_ban='Mẫu', nam='2026'), dong,
                        [dict(loai_dat='CLN', vi_tri='1', gia='250000')])
    return p


class _Co(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.td = Path(self.tmp.name)
        self.con = csdl.mo(_du_an(self.td))
        self.addCleanup(self.con.close)
        self.ds = [r[0] for r in self.con.execute('SELECT ma_ho FROM ho ORDER BY thu_tu')]

    def tearDown(self):
        self.doCleanups()
        self.tmp.cleanup()

    def hop_in(self):
        from pabt.man_hinh import HopIn
        h = HopIn(self.con, None, ma_ho_chon=self.ds, file_du_an=str(self.td / 'lo.pabt'), che_do='chinh_thuc')
        self.addCleanup(h.close)
        return h

    def xuat_gop(self, h=None):
        """Lô chỉ phương án chi tiết, bản Word, xuất PDF, gộp một file."""
        h = h or self.hop_in()
        for o in (h.o_bth, h.o_tt, h.o_bc):
            o.setChecked(False)
        h.r_pdf.setChecked(True)
        h.o_gop.setChecked(True)
        h.o_thu_muc.setText(str(self.td / 'dot'))
        return h.thuc_hien(xac_nhan=False)


class TestLoWordGopPdf(_Co):
    def setUp(self):
        super().setUp()
        gia = self.td / 'gia_word.py'
        gia.write_text(GIA_WORD, encoding='utf-8')
        for vo in (mock.patch.object(vb, '_lenh_word', lambda vbs, ds, dung: [sys.executable, '-I', str(gia), str(ds), str(dung)]),
                   mock.patch.object(in_an, '_tat_excel_tu_dong', lambda *a, **k: 0),   # không đụng Word thật của máy
                   mock.patch.object(vb, 'CHO_WORD_MOI_HO', 4), mock.patch.object(vb, 'CHO_KHOI_DONG_WORD', 6),
                   mock.patch.dict(os.environ, {'GIA_WORD_TREO': '', 'GIA_WORD_KHONG_CO': ''})):
            vo.start()
            self.addCleanup(vo.stop)

    def test_tich_san_word_va_gop_mot_pdf(self):
        from pypdf import PdfReader
        h = self.hop_in()
        self.assertTrue(h.o_word.isChecked())                                    # mặc định tích sẵn
        kq = self.xuat_gop(h)
        self.assertEqual(kq['loi'], [])
        self.assertEqual(len(kq['word']), SO_HO)
        self.assertNotIn('du_phong', kq)
        gop = kq['gop']
        self.assertEqual(gop.name, 'PHUONG_AN_CHI_TIET.pdf')
        self.assertEqual(gop.parent, kq['thu_muc_ct'])                          # trong thư mục đợt (PA CHI TIET)
        r = PdfReader(str(gop))
        self.assertEqual(len(r.pages), SO_HO)                                    # đủ mọi hộ, đúng thứ tự
        for i, trang in enumerate(r.pages):
            self.assertEqual((round(float(trang.mediabox.width)), round(float(trang.mediabox.height))), (595, 842))   # A4 dọc
        # PDF từng hộ lấy từ đúng file Word của hộ, file Word lề NĐ 30 (30 / 15 / 20 / 20 mm)
        for p in kq['word']:
            meta = PdfReader(str(p.with_suffix('.pdf'))).metadata
            self.assertEqual(meta['/Nguon'], p.name)
            tren, phai, duoi, trai = (round(int(v) / 1440 * 25.4) for v in meta['/LeTwip'].split(','))
            self.assertEqual((trai, phai, tren, duoi), (9, 7, 10, 10))

    def test_word_treo_mot_ho_bo_qua_va_du_phong(self):
        treo = f'ma{self.ds[1]}_'
        with mock.patch.dict(os.environ, {'GIA_WORD_TREO': treo}):
            t = time.perf_counter()
            kq = self.xuat_gop()
            giay = time.perf_counter() - t
        self.assertLess(giay, 60)                                                # không chờ hết 120 giây hộ treo
        self.assertEqual([p.name for p in kq['du_phong']], [p.with_suffix('.pdf').name for p in kq['word'] if treo in p.name])
        self.assertEqual(kq['loi'], [])                                          # hộ treo đã có PDF dự phòng
        from pypdf import PdfReader
        self.assertGreaterEqual(len(PdfReader(str(kq['gop'])).pages), SO_HO)    # hộ sau hộ treo vẫn được Word làm tiếp
        for p in kq['word']:
            self.assertTrue(p.with_suffix('.pdf').exists())

    def test_chay_word_bo_qua_ho_treo(self):
        """Mức chay_word: hộ treo -> một dòng LOI_TREO, các hộ khác xong."""
        viec = []
        for i in range(4):
            p = self.td / ('TREO.docx' if i == 1 else f'h{i}.docx')
            p.write_bytes(vb._goi_docx(vb._p(vb._r('Thử'))))
            viec.append(('pdf', p, p.with_suffix('.pdf')))
        with mock.patch.dict(os.environ, {'GIA_WORD_TREO': 'TREO'}):
            loi = vb.chay_word(viec, cho_moi_file=4)
        self.assertEqual(len(loi), 1)
        self.assertTrue(loi[0].startswith('LOI_TREO') and 'TREO.docx' in loi[0])
        self.assertEqual([c.exists() for _, _, c in viec], [True, False, True, True])

    def test_khong_co_word_dung_pdf_du_phong(self):
        with mock.patch.dict(os.environ, {'GIA_WORD_KHONG_CO': '1'}):
            kq = self.xuat_gop()
        self.assertEqual(kq['loi'], [])
        self.assertEqual(len(kq['du_phong']), SO_HO)
        self.assertTrue(kq['gop'].exists())

    def test_luon_xuat_word_khong_con_lua_chon_excel(self):
        """22/10/2026 (chỉ thị tái cấu trúc bản in): phương án chi tiết luôn là bản Word - ô chọn ẩn, không có file Excel."""
        h = self.hop_in()
        self.assertTrue(h.o_word.isChecked())
        self.assertFalse(h.o_word.isVisibleTo(h))
        kq = self.xuat_gop(h)
        self.assertEqual(kq['loi'], [])
        self.assertEqual(list(kq['thu_muc_ct'].glob('*.xlsx')), [])
        self.assertEqual(len(list(kq['thu_muc_ct'].glob('PA_*.docx'))), SO_HO)

    def test_in_may_khong_co_word_dung_pdf_tu_file_word(self):
        """Máy không có Word: không in thẳng được - dựng PDF gần đúng từ CHÍNH file Word (không Excel) và báo người dùng mở PDF để in."""
        with mock.patch.dict(os.environ, {'GIA_WORD_KHONG_CO': '1'}):
            kq = vb.xuat_bo_ho_so(self.con, self.ds, self.td / 'in_may', bang_tong_hop=False, in_may=True)
        self.assertEqual(len(kq['du_phong']), SO_HO)
        self.assertTrue(all(Path(p).read_bytes().startswith(b'%PDF') for p in kq['du_phong']))
        self.assertEqual(len(kq['loi']), 1)
        self.assertTrue(kq['loi'][0].startswith('KHONG_CO_WORD'))
        self.assertEqual(list((self.td / 'in_may').rglob('*.xlsx')), [])         # không còn bản Excel chi tiết


@unittest.skipUnless(_co_word(), 'cần Microsoft Word (đặt PABT_THU_WORD=0 để bỏ qua)')
class TestWordThat(_Co):
    def test_lo_word_that_gop_mot_pdf(self):
        from pypdf import PdfReader
        kq = self.xuat_gop()
        self.assertEqual(kq['loi'], [])
        self.assertNotIn('du_phong', kq)                                         # Microsoft Word xuất được từng hộ
        r = PdfReader(str(kq['gop']))
        so = sum(len(PdfReader(str(p.with_suffix('.pdf'))).pages) for p in kq['word'])
        self.assertEqual(len(r.pages), so)
        self.assertGreaterEqual(so, SO_HO)
        for trang in r.pages:                                                    # A4 dọc như file Word
            self.assertEqual((round(float(trang.mediabox.width)), round(float(trang.mediabox.height))), (595, 842))
        with zipfile.ZipFile(kq['word'][0]) as z:
            mar = ET.fromstring(z.read('word/document.xml')).find(f'.//{W}sectPr/{W}pgMar')
        self.assertEqual(round(int(mar.get(W + 'left')) / 1440 * 25.4), 9)

    def test_muc_iii_bat_dau_ngay_trang_1(self):
        """22/10/2026 (mẫu PA_01 người dùng gửi): mục II dài nửa trang - mục III + tiêu đề bảng + dòng đầu in tiếp ở cuối trang 1,
        không bị đẩy sang trang 2."""
        from pypdf import PdfReader
        from pabt import in_word
        ma = self.ds[0]
        doan = ('Thửa đất có nguồn gốc do hộ gia đình tự khai phá sử dụng ổn định từ năm 1995, không tranh chấp, phù hợp quy '
                'hoạch sử dụng đất tại thời điểm sử dụng và được Ủy ban nhân dân xã xác nhận theo hồ sơ kê khai. ') * 3
        with self.con:
            self.con.execute('UPDATE thua SET nguon_goc = ? WHERE ma_ho = ?', ('- ' + doan + '\n- ' + doan, ma))
        f = in_word.xuat_chi_tiet_docx(self.con, ma, self.td / 'trang1.docx')
        pdf = f.with_suffix('.pdf')
        self.assertEqual(vb.chay_word([('pdf', f, pdf)], cho_moi_file=120), [])
        trang = [p.extract_text() or '' for p in PdfReader(str(pdf)).pages]
        self.assertIn('III. Bảng tính toán', trang[0])
        self.assertIn('STT', trang[0])                                         # tiêu đề bảng cùng trang với tiêu đề mục III
        self.assertIn('Bồi thường đất', trang[0].replace('\n', ' '))           # có dòng số liệu đầu ở trang 1


if __name__ == '__main__':
    unittest.main()

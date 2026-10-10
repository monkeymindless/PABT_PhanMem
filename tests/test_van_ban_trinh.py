"""Trình phê duyệt (0.9.16): số / ngày phương án chi tiết từng hộ, văn bản trình + phương án tổng của đợt, mẫu Word / Excel,
bộ hồ sơ chia thư mục PA CHI TIET / PA TONG, CSDL v11. Số liệu, số văn bản trong bài là GIẢ LẬP."""
from __future__ import annotations
import hashlib
import os
import shutil
import sqlite3
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest import mock

import openpyxl

from pabt import csdl, don_gia, quan_ly, theo_doi, van_ban_trinh as vb
from pabt.lap_pa import LoiNhap
from tests.test_toc_do import _du_an


def _chu_docx(p) -> str:
    """Toàn bộ chữ (đã bỏ thẻ XML) của file Word."""
    import re
    with zipfile.ZipFile(p) as z:
        x = z.read('word/document.xml').decode('utf-8')
    return ''.join(re.findall(r'<w:t(?:\s[^>]*)?>(.*?)</w:t>', x, re.S))


def _co_word() -> bool:
    if sys.platform != 'win32' or os.environ.get('PABT_THU_WORD', '1') == '0':
        return False
    import winreg
    try:
        winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, r'Word.Application\CurVer').Close()
        return True
    except OSError:
        return False


class _Co(unittest.TestCase):
    def setUp(self):
        self.td = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.td, True)
        moi = mock.patch.dict(os.environ, {'PABT_THU_MUC_MAY': str(self.td / 'may')})
        moi.start()
        self.addCleanup(moi.stop)


class TestDocx(_Co):
    def test_gom_cho_trong_bi_tach(self):
        """Word tách {so_to_trinh} qua 3 mẩu chữ (đổi định dạng giữa chừng): vẫn điền được, chữ quanh giữ nguyên."""
        doan = ('<w:p><w:r><w:t>Số: {so_</w:t></w:r><w:r><w:rPr><w:b/></w:rPr><w:t>to_tr</w:t></w:r>'
                '<w:r><w:t xml:space="preserve">inh}/TTr ngày {ngay}</w:t></w:r></w:p>')
        gom = vb._gom_doan(doan)
        self.assertIn('{so_to_trinh}', gom)
        self.assertEqual(vb._thay(gom, {'so_to_trinh': '113', 'ngay': '10/10/2026'}).count('113'), 1)
        self.assertIn('/TTr ngày 10/10/2026', vb._thay(gom, {'so_to_trinh': '113', 'ngay': '10/10/2026'}))

    def test_mau_mac_dinh_va_dong_ho(self):
        for loai in vb.LOAI:
            p = vb.file_mau(loai)                                       # chưa có: tự tạo mẫu mặc định
            self.assertTrue(p.exists() and p.suffix == '.docx')
            self.assertIn('ho.ho_ten', vb.cho_trong_trong_file(p))
        ds = [{'ho.stt': str(i), 'ho.ho_ten': f'Nguyễn Văn {c}', 'ho.dia_chi': 'Ấp 1', 'ho.so_pa_day_du': f'{i}/PA',
               'ho.so_pa': str(i), 'ho.tong_tien': '1.000', 'ho.tien_dat': '1', 'ho.tien_nha': '0', 'ho.tien_cay': '0',
               'ho.tien_ho_tro': '0', 'ho.tien_thuong': '0'} for i, c in enumerate('ABC', start=1)]
        ra = vb.dien_docx(vb.file_mau('to_trinh'), self.td / 'tt.docx', {'so_to_trinh': '113/TTr', 'du_an': 'A & B <1>'}, ds)
        chu = _chu_docx(ra)
        self.assertIn('Số: 113/TTr', chu)
        self.assertIn('A &amp; B &lt;1&gt;', chu)                     # ký tự đặc biệt được mã hóa XML
        self.assertEqual(sum(chu.count(f'Nguyễn Văn {c}') for c in 'ABC'), 3)
        self.assertNotIn('{ho.', chu)
        self.assertNotIn('{ho.', _chu_docx(vb.dien_docx(vb.file_mau('to_trinh'), self.td / 'rong.docx', {}, [])))


class _DuAn(_Co):
    """Dự án giả lập 4 hộ (tests.test_toc_do._du_an) trong thư mục tạm."""

    def setUp(self):
        super().setUp()
        self.p = _du_an(self.td, so_ho=4)
        self.con = csdl.mo(self.p)
        self.addCleanup(self.con.close)
        self.ma = [r[0] for r in self.con.execute('SELECT ma_ho FROM ho ORDER BY thu_tu')]


class TestDotTrinh(_DuAn):
    def test_csdl_v11(self):
        self.assertEqual(self.con.execute('PRAGMA user_version').fetchone()[0], csdl.PHIEN_BAN_CSDL)
        d = quan_ly.tao_dot(self.con, ngay_trinh='10/10/2026', so_to_trinh='113/TTr', loai_van_ban='Văn bản',
                            so_pa_tong='30', ngay_pa_tong='9/10/2026')
        x = quan_ly.lay_dot(self.con, d)
        self.assertEqual((x.loai_van_ban, x.so_pa_tong, x.ngay_pa_tong), ('Văn bản', '30', '09/10/2026'))
        self.assertEqual(x.van_ban_trinh, 'Văn bản số 113/TTr ngày 10/10/2026')
        with self.assertRaises(LoiNhap):
            quan_ly.sua_dot(self.con, d, 'Đợt 1', ngay_pa_tong='31/2/2026')        # ngày không có thật: không ghi

    def test_danh_so_pa_va_quyet_dinh(self):
        kq = quan_ly.danh_so_pa(self.con, self.ma[:3], 7, '10/10/2026', so_chu_so=2)
        self.assertEqual([s for _, s, _ in kq], ['07', '08', '09'])
        quan_ly.dat_so_pa(self.con, [(self.ma[1], '', '')])                  # xóa số của hộ thứ 2
        kq = quan_ly.danh_so_pa(self.con, self.ma[:3], 20, chi_ho_chua_co=True)  # hộ đã có số giữ nguyên
        self.assertEqual(kq, [(self.ma[1], '20', '')])
        self.assertEqual(quan_ly.so_pa_cua_ho(self.con, [self.ma[0]]), {self.ma[0]: ('07', '10/10/2026')})
        with self.assertRaises(LoiNhap):
            quan_ly.danh_so_pa(self.con, self.ma, 'a1')
        qd = theo_doi.luu_qd(self.con, None, '5/QĐ-UBND', '20/10/2026')
        theo_doi.ghi_qd_ho(self.con, qd, self.ma[0], {'so_tien': '1000'})   # hộ vào quyết định: mang theo số PA chi tiết
        self.assertEqual(theo_doi.doc_qd_ho(self.con, self.ma[0])[0]['so_pa'], '07')

    def test_xuat_dot_hai_thu_muc(self):
        d = quan_ly.tao_dot(self.con, ngay_trinh='10/10/2026', so_to_trinh='113/TTr', so_pa_tong='30', ngay_pa_tong='9/10/2026')
        quan_ly.gan_dot(self.con, self.ma[:2], d)
        quan_ly.danh_so_pa(self.con, self.ma[:2], 101, '9/10/2026')
        goc = self.td / 'hs'
        kq = quan_ly.xuat_dot(self.con, d, goc, to_trinh=True, pa_tong=True)
        tm = kq['thu_muc']
        self.assertEqual(tm.name, 'Đợt 1 - 2 hộ')
        self.assertEqual(sorted(p.name for p in (tm / 'PA CHI TIET').iterdir())[0][:3], 'PA_')
        self.assertEqual(len(list((tm / 'PA CHI TIET').glob('*.xlsx'))), 2)
        self.assertEqual(sorted(p.name for p in (tm / 'PA TONG').iterdir()),
                         ['BANG_TONG_HOP.xlsx', 'PHUONG_AN_TONG.docx', 'TO_TRINH.docx'])
        # số PA chi tiết của hộ vào chỗ "Số:      /…" của mẫu; số / ngày PA tổng vào dòng "Đính kèm Phương án số …"
        ct = openpyxl.load_workbook(sorted((tm / 'PA CHI TIET').glob('*.xlsx'))[0]).worksheets[0]
        self.assertTrue(str(ct['A3'].value).startswith('Số: 101/'))
        self.assertIn('ngày 09 tháng 10 năm 2026', str(ct['E3'].value))
        bth = openpyxl.load_workbook(tm / 'PA TONG' / 'BANG_TONG_HOP.xlsx').worksheets[0]
        self.assertIn('Phương án số 30/', str(bth['A7'].value))
        self.assertIn('ngày 09 tháng 10 năm 2026', str(bth['A7'].value))
        chu = _chu_docx(tm / 'PA TONG' / 'TO_TRINH.docx')
        chung, dong = vb.du_lieu(self.con, self.ma[:2], quan_ly.lay_dot(self.con, d))
        for x in ('Số: 113/TTr', 'ngày 10 tháng 10 năm 2026', chung['tong_tien'], dong[0]['ho.ho_ten'], '101'):
            self.assertIn(x, chu)
        self.assertNotIn('{', chu)                                      # mọi chỗ trống của mẫu mặc định đều có số liệu
        # chỉ một số mẫu (in riêng lẻ)
        kq = quan_ly.xuat_dot(self.con, d, goc, chi_tiet=False, bang_tong_hop=False, to_trinh=True)
        self.assertEqual([p.name for p in kq['word']], ['TO_TRINH.docx'])

    def test_mau_to_trinh_excel(self):
        f = self.td / 'mau.xlsx'
        wb = openpyxl.Workbook()
        ws = wb.active
        ws['A1'], ws['A2'] = '{LOAI_VAN_BAN} số {so_to_trinh}', 'Tổng: {tong_tien}'
        ws['A4'], ws['B4'], ws['C4'] = '{ho.stt}', '{ho.ho_ten}', '{ho.tong_tien}'
        ws['A5'] = 'Cuối bảng'
        wb.save(f)
        p, cho = vb.them_mau('to_trinh', f)
        self.assertEqual(p.name, 'TO_TRINH.xlsx')
        self.assertIn('ho.ho_ten', cho)
        d = quan_ly.tao_dot(self.con, so_to_trinh='7/TTr')
        ra = vb.lap_van_ban(self.con, 'to_trinh', self.ma, self.td / 'ra', quan_ly.lay_dot(self.con, d))
        ws = openpyxl.load_workbook(ra).worksheets[0]
        self.assertEqual(ws['A1'].value, 'TỜ TRÌNH số 7/TTr')
        self.assertEqual([ws.cell(r, 1).value for r in range(4, 8)], [1, 2, 3, 4])          # mỗi hộ một dòng, số ghi dạng số
        self.assertEqual(ws['A8'].value, 'Cuối bảng')
        self.assertIsInstance(ws['C4'].value, int)
        with self.assertRaises(LoiNhap):
            vb.them_mau('pa_tong', f)                                   # phương án tổng: chỉ mẫu Word
        vb.khoi_phuc_mac_dinh('to_trinh')
        self.assertEqual(vb.file_mau('to_trinh').suffix, '.docx')

    def test_nang_cap_v10_va_bo_don_gia_khong_bi_sua(self):
        if sqlite3.sqlite_version_info < (3, 35):
            self.skipTest('SQLite cũ chưa có DROP COLUMN')
        self.con.close()
        c = sqlite3.connect(str(self.p))                               # dựng lại file v10: bỏ các cột v11
        for b, cot in (('ho', 'so_pa'), ('ho', 'ngay_pa'), ('dot_trinh', 'loai_van_ban'), ('dot_trinh', 'so_pa_tong'),
                       ('dot_trinh', 'ngay_pa_tong')):
            c.execute(f'ALTER TABLE {b} DROP COLUMN {cot}')
        c.execute('PRAGMA user_version = 10')
        c.commit()
        c.close()
        self.assertEqual(quan_ly.ds_dot(csdl.mo(self.p, chi_doc=True)), [])  # mở chỉ xem file cũ: không lỗi
        self.con = csdl.mo(self.p)
        self.assertEqual(self.con.execute('PRAGMA user_version').fetchone()[0], csdl.PHIEN_BAN_CSDL)
        self.assertIn('so_pa', [r[1] for r in self.con.execute('PRAGMA table_info(ho)')])
        # áp bộ đơn giá: chỉ ĐỌC bộ đơn giá đóng gói (trước đây mở ghi để nâng cấp -> sai mã SHA-256 của bản cài / gói cập nhật)
        goc = don_gia.file_goc()
        bam = hashlib.sha256(goc.read_bytes()).hexdigest()
        don_gia.ap_vao_du_an(self.con)
        self.assertEqual(hashlib.sha256(goc.read_bytes()).hexdigest(), bam)
        self.assertGreater(self.con.execute('SELECT COUNT(*) FROM dm_taisan').fetchone()[0], 1000)


try:
    import PySide6  # noqa: F401
    CO_QT = True
except ImportError:
    CO_QT = False


@unittest.skipUnless(CO_QT, 'cần PySide6')
class TestManHinh(_DuAn):
    """Cửa sổ Đợt trình (sửa đợt, số PA chi tiết, mẫu, xuất chọn mẫu) và hộp In (đợt, 2 thư mục, chọn mẫu)."""

    def setUp(self):
        super().setUp()
        from pabt.man_hinh_quan_ly import HopDotTrinh
        self.d = HopDotTrinh(self.con, None, self.ma[:3], self.p)
        self.d.im_lang = True
        self.addCleanup(self.d.close)

    def test_sua_dot_va_so_pa(self):
        d = self.d
        d.bang_dot.selectRow(d.bang_dot.rowCount() - 1)                # dòng "(Chưa xếp đợt)": báo, không im lặng
        with mock.patch.object(d, 'bao') as bao:
            self.assertIsNone(d.sua_dot(dict(ten='X')))
        self.assertIn('Chọn một đợt', bao.call_args[0][0])
        i = d.them_dot(dict(ten='', ngay_trinh='', so_to_trinh='', ghi_chu=''))
        self.assertEqual(d.dot_chon(), i)
        self.assertEqual(d.sua_dot(dict(ten='Đợt 1', ngay_trinh='10/10/2026', so_to_trinh='113/TTr', ghi_chu='',
                                        loai_van_ban='Tờ trình', so_pa_tong='30', ngay_pa_tong='09/10/2026')), i)
        self.assertEqual(d.bang_dot.item(0, 1).text(), 'Tờ trình số 113/TTr ngày 10/10/2026')
        self.assertEqual(d.bang_dot.item(0, 2).text(), '30 09/10/2026')
        self.assertEqual(d.dua_vao(), 3)
        self.assertEqual([s for _, s, _ in d.danh_so(5, '9/10/2026')], ['5', '6', '7'])
        self.assertEqual(d.bang_ho.item(0, 3).text(), '5')
        d.bang_ho.item(1, 3).setText('6a')                               # sửa trực tiếp ô số PA: ghi ngay
        self.assertEqual(quan_ly.so_pa_cua_ho(self.con, [self.ma[1]])[self.ma[1]][0], '6a')
        d.bang_ho.item(1, 4).setText('32/13/2026')                       # ngày sai: báo, giữ giá trị cũ
        self.assertEqual(quan_ly.so_pa_cua_ho(self.con, [self.ma[1]])[self.ma[1]][1], '09/10/2026')
        # xuất chỉ tờ trình (in riêng lẻ) rồi tất cả (đồng loạt)
        d.chon_thu_muc(str(self.td / 'hs'))
        for o in (d.o_ct, d.o_bth, d.o_pat):
            o.setChecked(False)
        kq = d.xuat(pdf=False)
        self.assertEqual([p.name for p in kq[0]['word']], ['TO_TRINH.docx'])
        for o in (d.o_ct, d.o_bth, d.o_pat):
            o.setChecked(True)
        kq = d.xuat(pdf=False)
        self.assertEqual(len(kq[0]['excel']) + len(kq[0]['word']), 3 + 1 + 2)
        self.assertTrue((kq[0]['thu_muc'] / 'PA TONG' / 'PHUONG_AN_TONG.docx').exists())

    def test_mau_trong_cua_so(self):
        d = self.d
        self.assertIn('mặc định', d.lb_mau['to_trinh'].text())
        f = vb.dien_docx(vb.file_mau('pa_tong'), self.td / 'mau.docx', {'du_an': 'Mẫu riêng'}, [])   # khác mẫu mặc định
        self.assertEqual(d.them_mau('pa_tong', f).name, 'PA_TONG.docx')
        self.assertEqual(d.lb_mau['pa_tong'].text(), 'PA_TONG.docx (Word)')
        self.assertEqual(d.sua_mau('pa_tong', mo=False).name, 'PA_TONG.docx')
        self.assertIsNotNone(d.mau_mac_dinh('pa_tong'))
        self.assertIn('mặc định', d.lb_mau['pa_tong'].text())
        hop = d.xem_cho_trong()
        self.assertIsNotNone(hop)

    def test_hop_in_theo_dot(self):
        from pabt.man_hinh import HopIn
        i = quan_ly.tao_dot(self.con, so_to_trinh='7/TTr', so_pa_tong='30', ngay_pa_tong='9/10/2026')
        quan_ly.gan_dot(self.con, self.ma[:2], i)
        h = HopIn(self.con, None)
        self.addCleanup(h.close)
        self.assertFalse(h.o_tt.isChecked())                           # không theo đợt: tờ trình, PA tổng không chọn sẵn
        h.cb_dot.setCurrentIndex(h.cb_dot.findData(i))                  # chọn đợt: đánh dấu hộ của đợt + chọn mọi mẫu
        self.assertEqual(h.ds_ho(), self.ma[:2])
        self.assertTrue(all(o.isChecked() for o in (h.o_ct, h.o_bth, h.o_tt, h.o_pat)))
        h.o_thu_muc.setText(str(self.td / 'in'))
        h.r_excel.setChecked(True)
        kq = h.thuc_hien(xac_nhan=False)
        self.assertEqual(sorted(p.name for p in (self.td / 'in' / 'PA TONG').iterdir()),
                         ['BANG_TONG_HOP.xlsx', 'PHUONG_AN_TONG.docx', 'TO_TRINH.docx'])
        self.assertEqual(len(list((self.td / 'in' / 'PA CHI TIET').glob('PA_*.xlsx'))), 2)
        self.assertIn('Phương án số 30/', str(openpyxl.load_workbook(self.td / 'in' / 'PA TONG' / 'BANG_TONG_HOP.xlsx')
                                              .worksheets[0]['A7'].value))
        h.chon_mau(False)
        h.o_ct.setChecked(True)
        h.o_chia.setChecked(False)                                       # một thư mục như trước
        h.o_thu_muc.setText(str(self.td / 'in2'))
        kq = h.thuc_hien(xac_nhan=False)
        self.assertEqual(len(kq['excel']), 2)
        self.assertEqual(len(list((self.td / 'in2').glob('PA_*.xlsx'))), 2)


@unittest.skipUnless(_co_word(), 'cần Microsoft Word (đặt PABT_THU_WORD=0 để bỏ qua)')
class TestWord(_Co):
    def test_xuat_pdf_va_luu_docx(self):
        """Mẫu mặc định (XML tự dựng) Word mở được, xuất PDF được; lưu lại .docx qua Word (đường chuyển file .doc). Chuyển PDF ->
        .docx không thử tự động: Word luôn hỏi người dùng (docx_hien)."""
        p = vb.dien_docx(vb.file_mau('pa_tong'), self.td / 'pa.docx', {'so_pa_tong': '30', 'du_an': 'Thử'}, [])
        mau = vb.file_mau('pa_tong')
        self.assertEqual(vb.chay_word([('pdf', p, p.with_suffix('.pdf')), ('docx', mau, self.td / 'luu_lai.docx')]), [])
        self.assertTrue(p.with_suffix('.pdf').stat().st_size > 1000)
        moi, cho = vb.them_mau('pa_tong', self.td / 'luu_lai.docx')    # mẫu Word lưu lại: vẫn dùng làm mẫu được
        self.assertEqual(moi.name, 'PA_TONG.docx')
        self.assertEqual(cho, vb.cho_trong_trong_file(mau))            # Word giữ nguyên các chỗ trống (gom lại nếu tách)


if __name__ == '__main__':
    unittest.main()

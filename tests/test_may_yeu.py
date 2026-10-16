"""Tối ưu cho máy cấu hình yếu (người dùng 16/10/2026): trang cửa sổ chính tạo khi mở lần đầu (vẫn tô màu nút như lúc cửa sổ hiện),
cửa sổ lập phương án: khung xem trước tạo khi bật, bảng thẻ ẩn vẽ khi hiện / khi đọc tới, sửa ô ở thẻ chưa vẽ không gọi lại sua_o;
màn hình chào không mở file dự án đã nhớ; đọc DXF bằng Python thuần (pabt.dxf_thuan); trigger kiểm toán chỉ chạy khi trường được theo
dõi đổi; temp_store = MEMORY; bóng đổ tắt mặc định. Số liệu GIẢ LẬP."""
from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from pabt import csdl
from tests.test_dac_ta_v5 import CoSo
from tests.test_toc_do import _du_an


class _Co(CoSo):
    def tearDown(self):
        self.doCleanups()
        super().tearDown()


class TestTrangLuoi(_Co):
    def test_trang_nang_tao_khi_mo(self):
        from pabt import app as ud
        from pabt.man_hinh_theo_doi import KhungBangTongHop, KhungTienDo
        w = ud.CuaSoChinh(menu_trai=True)
        self.addCleanup(lambda: (w.close(), w.dong_du_an()))
        w.show()
        self.assertEqual(w.khung_trang, {})                                        # mở phần mềm: chưa dựng trang nặng
        self.assertFalse(w.findChildren(KhungBangTongHop) or w.findChildren(KhungTienDo))
        w.mo(str(_du_an(self.td, 4)))
        self.app.processEvents()
        w.mo_trang(ud.TRANG_THEO_DOI)                                               # mở trang: tạo, gắn dự án, nạp
        self.assertIn(ud.STACK_THEO_DOI, w.khung_trang)
        k = w.khung_trang[ud.STACK_THEO_DOI]
        self.assertIs(w.tien_do, k)
        self.assertIs(k.con, w.con)
        self.assertIs(w.trang.currentWidget(), w._cho_trang[ud.STACK_THEO_DOI])
        nut = [b for b in k.findChildren(__import__('PySide6.QtWidgets', fromlist=['QPushButton']).QPushButton) if b.text()]
        self.assertTrue(any(b.property('nhom') for b in nut))                       # tạo sau khi cửa sổ hiện: vẫn tô màu nút
        self.assertIsInstance(w.bang_tong_hop, KhungBangTongHop)                    # property: tạo khi được hỏi
        self.assertIn(ud.STACK_TONG_HOP, w.khung_trang)

    def test_man_hinh_chao_khong_mo_file_da_nho(self):
        from pabt import app as ud
        p = _du_an(self.td, 3)
        so, tong, tim, ten = ud._tom_tat_pabt(p)                                    # lần đầu: mở file, nhớ cả tên
        self.assertEqual(so, 3)
        with mock.patch.object(csdl, 'mo', side_effect=AssertionError('không được mở file')):
            self.assertEqual(ud._tom_tat_pabt(p), (so, tong, tim, ten))             # lần sau: lấy nhớ
        os.utime(p, None)                                                           # file đổi: đọc lại
        p.write_bytes(p.read_bytes())
        with mock.patch.object(csdl, 'mo', side_effect=RuntimeError('mở lại')):
            self.assertEqual(ud._tom_tat_pabt(p)[0], None)


class TestCuaSoLapPA(_Co):
    def _cua_so(self):
        from pabt.man_hinh import CuaSoLapPA
        con = csdl.mo(str(_du_an(self.td, 3)))
        self.addCleanup(con.close)
        from pabt import lap_pa
        bo = lap_pa.BoSoan(con, 1)                                                  # hộ có dòng cây trồng
        bo.them_tu_danh_muc(3, bo.dm.muc[3][0])
        bo.luu()
        ma = 1
        c = CuaSoLapPA(con, ma)
        c.im_lang = True
        self.addCleanup(lambda: (c.bo_thay_doi(), c.close()))
        return c

    def test_xem_truoc_tao_khi_bat(self):
        c = self._cua_so()
        self.assertIsNone(c._w_preview)
        self.assertEqual(c.tach.count(), 1)
        c.lam_moi_xem_truoc()                                                       # khung chưa bật: không tạo
        self.assertIsNone(c._w_preview)

    def test_the_an_ve_khi_can_va_sua_o_khong_goi_lai(self):
        c = self._cua_so()
        c.show()
        self.app.processEvents()
        bm = c.bang[3]
        self.assertTrue(bm._can_ve)                                                 # thẻ hồ sơ đang xem: thẻ cây chưa vẽ
        n = len(c.bo.pa.khoan[3])
        with mock.patch('pabt.man_hinh.QMessageBox.warning', side_effect=AssertionError('không được báo lỗi')):
            c.sua_o(3, 0, 'so_luong', '7')                                          # sửa ô ở thẻ chưa vẽ: không gọi lại sua_o
        self.assertFalse(bm._can_ve)
        self.assertEqual(bm.bang.rowCount(), n)
        self.assertEqual(bm.bang.item(0, [k for k, *_ in bm.cot].index('so_luong')).text().split(',')[0], '7')
        c.bo_thay_doi()                                                              # bỏ sửa: chuyển hộ không hỏi lưu
        c.sang_ho(1)
        self.app.processEvents()
        self.assertTrue(c.bang[3]._can_ve or c.tab.currentWidget() is c.bang[3])
        self.assertEqual(c.bang[3].bang.rowCount(), len(c.bo.pa.khoan[3]))       # đọc tới bảng: tự vẽ, số liệu đúng hộ mới


class TestDxfThuan(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.td = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def _ghi(self, dong: list, ten='a.dxf', ma='utf-8') -> Path:
        p = self.td / ten
        p.write_bytes(('\r\n'.join(str(x) for x in dong) + '\r\n').encode(ma))
        return p

    def test_r12_polyline_chu_khoi_ma_hoa(self):
        from pabt import dxf_thuan as dx
        dong = ['0', 'SECTION', '2', 'HEADER', '9', '$ACADVER', '1', 'AC1009', '9', '$DWGCODEPAGE', '3', 'ANSI_1258',
                '0', 'ENDSEC', '0', 'SECTION', '2', 'BLOCKS',
                '0', 'BLOCK', '8', '0', '2', 'NHAN', '10', '0', '20', '0', '0', 'TEXT', '8', '0', '10', '1', '20', '0', '1', 'B12',
                '0', 'ENDBLK', '0', 'ENDSEC', '0', 'SECTION', '2', 'ENTITIES',
                '0', 'POLYLINE', '8', 'RANH', '66', '1', '70', '1',
                '0', 'VERTEX', '8', 'RANH', '10', '0', '20', '0', '0', 'VERTEX', '8', 'RANH', '10', '4', '20', '0',
                '0', 'VERTEX', '8', 'RANH', '10', '4', '20', '3', '0', 'SEQEND',
                '0', 'TEXT', '8', 'CHU', '10', '1', '20', '1', '1', 'Đất %%c10',
                '0', 'MTEXT', '8', 'CHU', '10', '2', '20', '2', '1', '{\\fArial|b1;12}\\P245,6\\PONT',
                '0', 'INSERT', '8', 'CHU', '2', 'NHAN', '10', '10', '20', '20', '50', '90',
                '0', 'INSERT', '8', 'CHU', '2', 'NHAN', '10', '5', '20', '5', '66', '1',
                '0', 'ATTRIB', '8', 'CHU', '10', '6', '20', '6', '1', 'A7', '0', 'SEQEND',
                '0', 'TEXT', '8', 'GIAY', '67', '1', '10', '0', '20', '0', '1', 'paper space',
                '0', 'ENDSEC', '0', 'EOF']
        kq = dx.doc(self._ghi(dong, ma='cp1258'))
        self.assertEqual([e.loai for e in kq], ['POLYLINE', 'TEXT', 'MTEXT', 'INSERT', 'INSERT'])
        self.assertEqual((kq[0].lop, kq[0].diem, kq[0].kin), ('RANH', [(0, 0), (4, 0), (4, 3)], True))
        self.assertEqual(kq[1].chu[0][0], 'Đất Ø10')                               # cp1258 dấu tách rời -> dựng sẵn (NFC) + %%c
        self.assertEqual(kq[2].chu[0][0], '12\n245,6\nONT')                         # MTEXT: bỏ mã phông, \P xuống dòng
        c, x, y = kq[3].chu[0]                                                      # chữ trong khối, xoay 90°
        self.assertEqual(c, 'B12')
        self.assertAlmostEqual(x, 10, places=6)
        self.assertAlmostEqual(y, 21, places=6)
        self.assertEqual(kq[4].chu, [('A7', 6.0, 6.0)])                             # thuộc tính khối

    def test_lwpolyline_va_loi(self):
        from pabt import dxf_thuan as dx
        dong = ['0', 'SECTION', '2', 'HEADER', '9', '$ACADVER', '1', 'AC1027', '0', 'ENDSEC', '0', 'SECTION', '2', 'ENTITIES',
                '0', 'LWPOLYLINE', '8', 'T', '90', '3', '70', '1', '10', '0', '20', '0', '10', '2', '20', '0', '10', '2', '20', '2',
                '0', 'TEXT', '8', 'T', '10', '0', '20', '0', '1', '\\U+1EA0', '0', 'ENDSEC', '0', 'EOF']
        kq = dx.doc(self._ghi(dong))
        self.assertEqual((kq[0].diem, kq[0].kin, kq[1].chu[0][0]), ([(0, 0), (2, 0), (2, 2)], True, 'Ạ'))
        (self.td / 'nhi_phan.dxf').write_bytes(b'AutoCAD Binary DXF\r\n\x1a\x00abc')
        with self.assertRaisesRegex(dx.LoiDxf, 'nhị phân'):
            dx.doc(self.td / 'nhi_phan.dxf')
        (self.td / 'rac.dxf').write_text('xin chao\nthe gioi\n', encoding='utf-8')
        with self.assertRaises(dx.LoiDxf):
            dx.doc(self.td / 'rac.dxf')

    def test_ban_ve_viet_roi_phan_tich(self):
        from pabt import ban_do_cad, dxf_thuan
        f = dxf_thuan.viet(self.td / 'To_3.dxf', [('RANH THUA', [(0, 0), (20, 0), (20, 10), (0, 10)]),
                                                     ('RANH THU HOI', [(10, -5), (30, -5), (30, 20), (10, 20)])],
                           [('NHAN', '7', 5, 5)])
        t = ban_do_cad.phan_tich(f, 'RANH THUA', 'RANH THU HOI').thua[0]
        self.assertEqual((t.so_to, t.so_thua, float(t.dt_hinh), float(t.dt_trong_ranh)), ('3', '7', 200.0, 100.0))


class TestCsdl(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.p = _du_an(Path(self.tmp.name), 20)

    def tearDown(self):
        self.tmp.cleanup()

    def test_temp_store_va_trigger_chi_theo_truong_theo_doi(self):
        from pabt import kiem_toan
        con = csdl.mo(str(self.p))
        try:
            self.assertEqual(con.execute('PRAGMA temp_store').fetchone()[0], 2)        # MEMORY
            self.assertTrue(kiem_toan.gan(con))
            sql = con.execute("SELECT sql FROM temp.sqlite_master WHERE name = '_kt_ho_sua'").fetchone()[0]
            self.assertIn('UPDATE OF', sql)
            truoc = con.execute('SELECT COUNT(*) FROM audit_logs').fetchone()[0]
            with con:
                con.execute("UPDATE ho SET theo_doi = 'tiến độ'")                          # cột không theo dõi: không ghi
                con.execute("UPDATE ho SET ghi_chu = ghi_chu")                             # không đổi giá trị: không ghi
            self.assertEqual(con.execute('SELECT COUNT(*) FROM audit_logs').fetchone()[0], truoc)
            with con:
                con.execute("UPDATE ho SET ghi_chu = 'mới', theo_doi = 'x' WHERE ma_ho <= 3")
            moi = con.execute("SELECT truong, moi FROM audit_logs WHERE hanh_dong = 'sua'").fetchall()
            self.assertEqual(sorted(tuple(r) for r in moi), [('ghi_chu', 'mới')] * 3)
        finally:
            con.close()


class TestBongDo(_Co):
    def test_tat_mac_dinh(self):
        from PySide6.QtWidgets import QFrame
        from pabt import giao_dien
        k = QFrame()
        self.addCleanup(k.deleteLater)
        os.environ.pop('PABT_HIEU_UNG_BONG', None)
        self.assertIsNone(giao_dien.do_bong(k).graphicsEffect())


if __name__ == '__main__':
    unittest.main()

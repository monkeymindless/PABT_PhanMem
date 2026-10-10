"""0.9.21: mục Vật nuôi riêng (in là mục 4; hỗ trợ -> 5, thưởng -> 6), nâng cấp CSDL v12, lưu phương án có diện tích / mục
bằng 0 (vẫn là đã lập phương án), danh sách vị trí NQ 28 đủ các địa bàn."""
from __future__ import annotations
import os
import sqlite3
import tempfile
import unittest
from pathlib import Path

from pabt import csdl, gia_dat_nq28, in_an, lap_pa, nghiep_vu, nhap_chi_tiet, phan_loai_tai_san
from pabt.lap_pa import BoSoan
from pabt.nghiep_vu import MUC_VN
from pabt.tien import D
from tests.test_toc_do import _du_an


class _CoDuAn(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.p = _du_an(Path(self.td.name), 4)
        self.con = csdl.mo(self.p)
        self.ma = [r[0] for r in self.con.execute('SELECT ma_ho FROM ho ORDER BY thu_tu')]

    def tearDown(self):
        self.con.close()
        self.td.cleanup()


class TestVatNuoi(_CoDuAn):
    def test_danh_muc_va_so_thu_tu_in(self):
        bo = BoSoan(self.con, self.ma[0])
        self.assertTrue(bo.dm.muc[MUC_VN])
        self.assertFalse([m for m in bo.dm.muc[3] if nghiep_vu.la_vat_nuoi(m.phan_loai)])
        m = bo.dm.lay('VN05')
        i, _ = bo.them_tu_danh_muc(MUC_VN, m)
        bo.sua_khoan(MUC_VN, i, 'so_luong', '2')
        bo.them_hang_muc_khac(4, 'Hỗ trợ khác')
        bo.sua_khoan(4, len(bo.ds(4)) - 1, 'don_gia', '1000000')
        bo.luu()
        self.assertEqual(self.con.execute('SELECT muc FROM ct_khoan WHERE ma = ?', ('VN05',)).fetchone()[0], MUC_VN)
        kq = nghiep_vu.tinh_ho(self.con, self.ma[0])
        self.assertEqual([d.stt for d in kq.dong if d.muc == MUC_VN], ['4.1'])
        self.assertEqual([d.stt for d in kq.dong if d.muc == 4], ['5.1'])
        self.assertEqual(kq.muc[MUC_VN], m.don_gia * 2)
        self.assertEqual(nghiep_vu.muc_5_cot(kq.muc)[3], kq.muc[3] + kq.muc[MUC_VN])     # bảng 5 cột: cây gồm vật nuôi
        dong, _ = in_an.dong_chi_tiet(self.con, self.ma[0])
        tieu_de = [(x[1][0], x[1][1]) for x in dong if x[0] in ('H', 'R')]
        self.assertEqual([s for s, _ in tieu_de], ['1', '2', '3', '4', '5', '6'])
        self.assertEqual(tieu_de[3][1], 'Bồi thường, hỗ trợ về vật nuôi')
        self.assertIn('hỗ trợ', tieu_de[4][1].lower())
        self.assertIn('Thưởng', tieu_de[5][1])

    def test_nang_cap_v11_chuyen_vat_nuoi(self):
        self.con.execute("INSERT INTO ct_khoan (muc, ma_ho, thu_tu, ma, ten, dvt, so_luong, don_gia) VALUES (3, ?, 9, 'VN05', 'x', "
                         "'con', '1', '1')", (self.ma[0],))
        self.con.execute("UPDATE ct_khoan SET muc = 3 WHERE ma = 'VN05'")
        self.con.commit()
        self.con.close()
        c = sqlite3.connect(str(self.p))                       # dựng lại file v11: bảng ct_khoan cũ (CHECK muc IN (2, 3, 4))
        sql = c.execute("SELECT sql FROM sqlite_master WHERE name = 'ct_khoan'").fetchone()[0]
        c.execute('ALTER TABLE ct_khoan RENAME TO ct_khoan_tam')
        c.execute(sql.replace('(2, 3, 4, 7)', '(2, 3, 4)'))
        c.execute('INSERT INTO ct_khoan SELECT * FROM ct_khoan_tam')
        c.execute('DROP TABLE ct_khoan_tam')
        c.execute('PRAGMA user_version = 11')
        c.commit()
        c.close()
        self.con = csdl.mo(self.p)
        self.assertEqual(self.con.execute('PRAGMA user_version').fetchone()[0], csdl.PHIEN_BAN_CSDL)
        self.assertEqual(self.con.execute("SELECT muc FROM ct_khoan WHERE ma = 'VN05'").fetchone()[0], MUC_VN)
        self.con.execute("INSERT INTO ct_khoan (muc, ma_ho, ma, ten) VALUES (7, ?, 'VN01', 'y')", (self.ma[0],))   # CHECK mới
        with self.assertRaises(sqlite3.IntegrityError):
            self.con.execute("INSERT INTO ct_khoan (muc, ma_ho, ma, ten) VALUES (5, ?, '', 'z')", (self.ma[0],))

    def test_nhap_chi_tiet_theo_ten_muc(self):
        self.assertEqual(nhap_chi_tiet.muc_theo_ten('Bồi thường, hỗ trợ về vật nuôi'), MUC_VN)
        self.assertEqual(nhap_chi_tiet.muc_theo_ten('Bồi thường, hỗ trợ về cây trồng, vật nuôi'), 3)
        self.assertEqual(nhap_chi_tiet.muc_theo_ten('Các chính sách hỗ trợ'), 4)
        self.assertEqual(nhap_chi_tiet.muc_theo_ten('Thưởng chấp hành bàn giao mặt bằng'), 5)

    def test_phan_loai(self):
        bo = phan_loai_tai_san.BoPhanLoai(lap_pa.DanhMuc(self.con))
        k = bo.phan_loai('Heo thịt', 'kg')
        self.assertEqual((k.loai, k.muc), (phan_loai_tai_san.VAT_NUOI, MUC_VN))


class TestLuuBang0(_CoDuAn):
    def test_dien_tich_0_va_ho_trong(self):
        bo = BoSoan(self.con, self.ma[0])
        self.assertTrue(bo.pa.dat)
        bo.sua_dat(0, 'dien_tich', '0')                       # tài sản trên đất người khác: không có diện tích
        bo.sua_dat(0, 'gia_bang_gia', '0')
        bo.luu()                                              # trước 0.9.21: "diện tích phải lớn hơn 0"
        self.assertFalse(any('0 m²' in x or 'giá bảng giá' in x for x in bo.canh_bao), bo.canh_bao)
        bo = BoSoan(self.con, self.ma[1])                     # hộ không còn dòng nào: lưu vẫn là đã lập, 0 đồng
        for m in (1, 2, 3, MUC_VN, 4):
            while bo.ds(m):
                bo.xoa(m, 0)
        bo.luu()
        lap = lap_pa.phan_loai_lap(self.con)
        self.assertEqual((lap[self.ma[0]], lap[self.ma[1]]), ('da_lap', 'da_lap'))
        k = nghiep_vu.tinh_ho(self.con, self.ma[1])
        self.assertEqual((k.tong, k.co_phuong_an), (0, True))
        with self.assertRaises(lap_pa.LoiNhap):
            BoSoan(self.con, self.ma[2]).sua_dat(0, 'dien_tich', '-1')


class TestViTriNQ28(_CoDuAn):
    def test_du_cac_dia_ban(self):
        self.con.execute("UPDATE du_an SET ten_dia_ban = 'Phú Lý' WHERE id = 1")
        self.con.commit()
        bo = BoSoan(self.con, self.ma[0])
        bo.sua_dat(0, 'loai_dat', 'CLN')
        ds = bo.ds_vi_tri_nq28(0)
        self.assertEqual(len(ds), len(gia_dat_nq28.tat_ca()))
        xa = list(dict.fromkeys(r['xa'] for _, r, _ in ds))
        self.assertEqual(xa[0], 'Xã Phú Lý')                 # địa bàn dự án đứng đầu
        self.assertEqual(set(xa), set(gia_dat_nq28.ds_xa()))
        self.assertTrue(ds[0][0].startswith('Phú Lý · MT · '))
        self.assertIn('Trị An · ', ' '.join(n for n, _, _ in ds))


try:
    import PySide6  # noqa: F401
    CO_QT = True
except ImportError:
    CO_QT = False


@unittest.skipUnless(CO_QT, 'cần PySide6')
class TestCuaSoLapPA(_CoDuAn):
    def test_the_vat_nuoi(self):
        os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
        from PySide6.QtWidgets import QApplication
        QApplication.instance() or QApplication([])
        from pabt.man_hinh import CuaSoLapPA, the_cua
        w = CuaSoLapPA(self.con, self.ma[0])
        try:
            ten = [w.tab.tabText(i).rsplit(' (', 1)[0] for i in range(w.tab.count())]
            self.assertEqual(ten[1:], ['1. Đất', '2. Nhà, công trình', '3. Cây trồng', '4. Vật nuôi', '5. Hỗ trợ'])
            self.assertEqual((the_cua(MUC_VN), the_cua(4)), (4, 5))
            w.them_nhanh(MUC_VN, w.bo.dm.lay('VN05'), so_luong='3')
            self.assertEqual(w.tab.currentIndex(), 4)
            self.assertEqual(len(w.bo.ds(MUC_VN)), 1)
            self.assertIn('4. ', w.lb_tong.text())
            self.assertTrue(w.sang_the(5))
            self.assertIs(w.tab.currentWidget(), w.bang[4])
            bo = BoSoan(self.con, self.ma[3])                 # hộ chưa lưu lần nào: nút Lưu bấm được (xác nhận 0 đồng)
            self.assertFalse(str(bo.pa.ho.trang_thai).startswith(nghiep_vu.DA_LAP_LUU))
        finally:
            w.bo_thay_doi()                                   # không còn sửa đổi: đóng không hỏi lưu (hộp hỏi sẽ treo test)
            w.close()
            w.deleteLater()


@unittest.skipUnless(CO_QT, 'cần PySide6')
class TestNguonGocThutLe(unittest.TestCase):
    def test_dong_tran_gach_dau_dong_thut_vao(self):
        # ô Nguồn gốc trên màn hình hồ sơ: dòng tràn của "- ..." thụt vào thẳng chữ sau "- ", đoạn thường sát lề
        os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
        from PySide6.QtGui import QFont, QFontMetricsF
        from PySide6.QtWidgets import QApplication
        QApplication.instance() or QApplication([])
        from pabt.man_hinh_ho_so import _bo_tri_chu
        f = QFont()
        chu = 'Căn cứ ' + 'chữ dài ' * 30 + '\n- Thửa ' + 'chữ dài ' * 30
        ds, _ = _bo_tri_chu(chu, f, 300)
        thuong, gach = ds[0][0], ds[1][0]
        self.assertGreater(thuong.lineCount(), 1)
        self.assertTrue(all(thuong.lineAt(i).x() == 0 for i in range(thuong.lineCount())))
        self.assertGreater(gach.lineCount(), 1)
        self.assertEqual(gach.lineAt(0).x(), 0)
        thut = QFontMetricsF(f).horizontalAdvance('- ')
        for i in range(1, gach.lineCount()):
            self.assertAlmostEqual(gach.lineAt(i).x(), thut, places=3)
            self.assertLessEqual(gach.lineAt(i).naturalTextWidth(), 300 - thut + 0.5)
        # chữ hiển thị của ô (initStyleOption) dùng U+2028 thay '\n': vẫn phải tách đoạn, nhận gạch đầu dòng
        ds2, _ = _bo_tri_chu(chu.replace('\n', ' '), f, 300)
        self.assertEqual(len(ds2), 2)
        self.assertAlmostEqual(ds2[1][0].lineAt(1).x(), thut, places=3)


if __name__ == '__main__':
    unittest.main()

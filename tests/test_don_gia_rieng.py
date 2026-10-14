"""Kiểm thử đơn giá riêng của dự án: quy ước tương đương nhập tay, đơn giá thẩm định giá (tài sản đặc biệt).
Số liệu thẩm định trong file này là GIẢ LẬP để kiểm thử, không phải giá thật."""
from __future__ import annotations
import os
import tempfile
import unittest
from pathlib import Path

from pabt import csdl, don_gia, don_gia_rieng as dgr, lap_pa
from pabt.lap_pa import LoiNhap
from pabt.tien import D

try:
    import PySide6  # noqa: F401
    CO_QT = True
except ImportError:
    CO_QT = False

# bảng kết quả thẩm định GIẢ LẬP (dạng Excel / Word: dòng đầu là thông tin chứng thư, rồi bảng Tên - ĐVT - Đơn giá)
THAM_DINH = [
    ['CÔNG TY TNHH THẨM ĐỊNH GIÁ THỬ NGHIỆM ABC'],
    ['CHỨNG THƯ THẨM ĐỊNH GIÁ Số: 123/2026/CT-ABC'],
    ['Đồng Nai, ngày 15 tháng 9 năm 2026'],
    ['STT', 'Tên tài sản', 'ĐVT', 'Số lượng', 'Đơn giá thẩm định (đồng)', 'Ghi chú'],
    ['1', 'Nhà kính trồng lan khung thép', 'm²', '500', '850.000', ''],
    ['2', 'Lò sấy nông sản thủ công', 'cái', '1', '45.000.000', ''],
    ['3', 'Hệ thống tưới nhỏ giọt', 'ha', '2', '120.000.000', ''],
]


class CoSo(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.td = Path(self.tmp.name)
        self._cu = os.environ.get('PABT_THU_MUC_MAY')
        os.environ['PABT_THU_MUC_MAY'] = str(self.td / 'may')
        self.con = csdl.tao_moi(self.td / 'a.pabt')
        don_gia.ap_vao_du_an(self.con)

    def tearDown(self):
        self.con.close()
        if self._cu is None:
            os.environ.pop('PABT_THU_MUC_MAY', None)
        else:
            os.environ['PABT_THU_MUC_MAY'] = self._cu
        self.tmp.cleanup()


class TestQuyUoc(CoSo):
    def test_chuan_gia(self):
        self.assertEqual(dgr.chuan_gia('1.854.000'), '1854000')
        self.assertEqual(dgr.chuan_gia(' 259000 '), '259000')
        self.assertEqual(dgr.chuan_gia('1.854.000,5'), '1854000.5')
        self.assertEqual(dgr.chuan_gia(''), '')
        with self.assertRaises(LoiNhap):
            dgr.chuan_gia('abc')

    def test_luu_giu_khi_ap_bo(self):
        """0.9.69: bộ đơn giá không còn quy ước gắn sẵn. Dự án cũ còn dòng quy ước của bộ trước (id nhỏ): áp bộ thì bỏ; dòng riêng
        (Đơn giá đặc biệt, id >= ID_RIENG) giữ nguyên."""
        self.assertEqual(dgr.doc(self.con), [])                          # dự án mới: không quy ước nào
        with self.con, csdl.mo_khoa_danh_muc(self.con):                 # giả lập dự án lập bằng bộ đơn giá cũ
            self.con.execute("INSERT INTO quy_uoc (id, ten_thuc_te, ten_tuong_duong, dvt, don_gia, can_cu) "
                             "VALUES (1, 'Mái tôn hiên phụ', 'Mái che, mái hiên', 'm²', '259000', 'bộ cũ')")
        bo = dgr.doc(self.con)
        self.assertTrue(bo and not any(r['rieng'] for r in bo))
        ds = [dict(r) for r in bo]
        ds.append(dict(ten_thuc_te='Giếng khoan sâu 80m', ten_tuong_duong='Giếng khoan', dvt='md', don_gia='350.000',
                       can_cu='Áp giá tương đương theo giếng khoan'))
        kq = dgr.luu(self.con, ds)
        self.assertEqual(kq['moi'], 1)
        rieng = [r for r in dgr.doc(self.con) if r['rieng']]
        self.assertEqual([r['don_gia'] for r in rieng], ['350000'])
        self.assertTrue(all(r['id'] >= dgr.ID_RIENG for r in rieng))
        don_gia.ap_vao_du_an(self.con)                                  # áp lại bộ: dòng riêng giữ, dòng của bộ cũ bỏ
        lai = dgr.doc(self.con)
        self.assertEqual([(r['ten_thuc_te'], r['don_gia']) for r in lai], [('Giếng khoan sâu 80m', '350000')])
        # thiếu đơn giá / ĐVT: báo lỗi, không ghi
        with self.assertRaises(LoiNhap):
            dgr.luu(self.con, [dict(ten_thuc_te='X', ten_tuong_duong='Y', dvt='', don_gia='')])
        self.assertEqual(len(dgr.doc(self.con)), len(lai))
        # bảng quy ước vẫn bị khóa ngoài các hàm ghi
        import sqlite3
        with self.assertRaises(sqlite3.IntegrityError):
            with self.con:
                self.con.execute("UPDATE quy_uoc SET don_gia = '1'")

    def test_lap_pa_dung_quy_uoc(self):
        dgr.luu(self.con, dgr.doc(self.con) + [dict(ten_thuc_te='Giếng khoan sâu 80m', ten_tuong_duong='Giếng khoan',
                                                     dvt='md', don_gia='350000', can_cu='Theo biên bản họp dân')])
        dm = lap_pa.DanhMuc(self.con)
        m = next(x for x in dm.muc[9] if x.ten == 'Giếng khoan sâu 80m')
        self.assertEqual(m.don_gia, D(350000))


class TestThamDinh(CoSo):
    def test_doc_va_dua_vao(self):
        ds, tt, xem = dgr.doc_file_tham_dinh('td.xlsx', THAM_DINH)
        self.assertEqual([(m.ten, m.dvt, m.don_gia) for m in ds],
                         [('Nhà kính trồng lan khung thép', 'm²', 850000), ('Lò sấy nông sản thủ công', 'cái', 45000000),
                          ('Hệ thống tưới nhỏ giọt', 'ha', 120000000)])
        self.assertEqual(tt['so_chung_thu'], '123/2026/CT-ABC')
        self.assertEqual(tt['ngay'], '15/09/2026')
        self.assertIn('THẨM ĐỊNH GIÁ THỬ NGHIỆM ABC', tt['don_vi'])
        cc = dgr.can_cu_tham_dinh(tt['so_chung_thu'], tt['ngay'], 'Công ty ABC', 'Quyết định số 1/QĐ-UBND (thử)')
        self.assertIn('Chứng thư thẩm định giá số 123/2026/CT-ABC ngày 15/09/2026 của Công ty ABC', cc)
        self.assertIn('18/2026/QĐ-UBND', cc)
        ds[2].chon = False
        self.assertEqual(dgr.them_tham_dinh(self.con, ds, cc), dict(moi=2, cap_nhat=0))
        # nhập lại chứng thư mới: trùng tên + ĐVT thì cập nhật giá
        ds[0].don_gia = 900000
        self.assertEqual(dgr.them_tham_dinh(self.con, ds, cc + ' (điều chỉnh)'), dict(moi=0, cap_nhat=2))
        td = [r for r in dgr.doc(self.con) if r['tham_dinh']]
        self.assertEqual(len(td), 2)
        self.assertTrue(all(r['rieng'] and r['ten_tuong_duong'] == dgr.TD_THAM_DINH for r in td))
        self.assertEqual(next(r['don_gia'] for r in td if r['ten_thuc_te'].startswith('Nhà kính')), '900000')
        # lập phương án: thêm dòng theo đơn giá thẩm định, căn cứ ghi chứng thư
        con = self.con
        with con:
            con.execute("INSERT INTO ho (ma_ho, thu_tu, ho_ten) VALUES (1, 1, 'Hộ thử')")
        bo = lap_pa.BoSoan(con, 1, lap_pa.DanhMuc(con))
        m = next(x for x in bo.dm.muc[9] if x.ten.startswith('Nhà kính'))
        i, _ = bo.them_tu_danh_muc(2, m)
        d = bo.pa.khoan[2][i]
        self.assertEqual((d.ten, d.dvt, d.don_gia, d.nguon_gia), ('Nhà kính trồng lan khung thép', 'm²', D(900000), 'tương đương'))
        self.assertTrue(d.can_cu_gia.startswith('Đơn giá thẩm định: 900.000 đ/m²; Chứng thư'))

    def test_khong_co_gia(self):
        with self.assertRaises(LoiNhap):
            dgr.doc_file_tham_dinh('x.docx', [['Báo cáo thẩm định'], ['Không có bảng giá']])
        with self.assertRaises(LoiNhap):
            dgr.them_tham_dinh(self.con, [], 'cc')


@unittest.skipUnless(CO_QT, 'cần PySide6')
class TestManHinh(CoSo):
    @classmethod
    def setUpClass(cls):
        os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
        from PySide6.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication([])

    def test_hop_don_gia_rieng(self):
        from pabt.man_hinh_don_gia_rieng import HopDonGiaRieng
        d = HopDonGiaRieng(self.con)
        d.im_lang = True
        n = d.bang.rowCount()
        self.assertEqual(n, len(dgr.doc(self.con)))
        self.assertFalse(d.b_luu.isEnabled())
        dm = lap_pa.DanhMuc(self.con)
        m = next(x for x in dm.muc[2] if x.don_gia)
        d.them_theo_danh_muc(m, 'Mái che sân phơi tự làm')
        self.assertTrue(d.b_luu.isEnabled())
        self.assertIsNotNone(d.luu())
        self.assertTrue(d.da_luu)
        r = next(r for r in dgr.doc(self.con) if r['ten_thuc_te'] == 'Mái che sân phơi tự làm')
        self.assertEqual((r['ten_tuong_duong'], r['dvt'], D(r['don_gia'])), (m.ten, m.dvt, m.don_gia))
        # sửa đơn giá sai -> báo lỗi, không lưu
        d.bang.item(0, 3).setText('không phải số')
        self.assertIsNone(d.luu())
        self.assertIn('không phải số', d.thong_bao_cuoi)
        d.nap()
        # thẻ thẩm định: đọc file, sửa tên, bỏ chọn, đưa vào
        d.chon_file('td.xlsx', THAM_DINH)
        self.assertEqual(d.bang_td.rowCount(), 3)
        self.assertEqual(d.o_so.text(), '123/2026/CT-ABC')
        self.assertIn('123/2026/CT-ABC', d.o_can_cu.text())
        from PySide6.QtCore import Qt
        d.bang_td.item(1, 1).setText('Lò sấy cà phê thủ công')
        d.bang_td.item(2, 0).setCheckState(Qt.CheckState.Unchecked)
        self.assertEqual(d.dua_vao(), dict(moi=2, cap_nhat=0))
        td = {r['ten_thuc_te'] for r in dgr.doc(self.con) if r['tham_dinh']}
        self.assertEqual(td, {'Nhà kính trồng lan khung thép', 'Lò sấy cà phê thủ công'})
        self.assertEqual(d.bang.rowCount(), n + 3)
        # ô chọn nhanh mục 2 có các dòng quy ước / thẩm định đứng đầu
        from pabt.man_hinh import ds_chon_nhanh
        nhan = [x[0] for x in ds_chon_nhanh(lap_pa.DanhMuc(self.con), 2)]
        self.assertTrue(any(x.startswith('[Thẩm định] Lò sấy cà phê thủ công') for x in nhan))
        self.assertTrue(any(x.startswith('[Quy ước] Mái che sân phơi tự làm') for x in nhan))


if __name__ == '__main__':
    unittest.main()

"""1.0.33 (người dùng 28/10/2026, "UI/UX Pro Max 3.0"): đọc bản đồ một lần + bỏ phân tích trùng tham số ở hộp Nhập bản đồ, tông nền bề mặt
(chu_de.TONG_NEN, giao_dien.dat_tong_nen / ap_tong_nen, hộp Giao diện), nhóm màu thẻ KPI, tổng thửa / tỷ lệ đồng thuận trên bản đồ. Dữ liệu
giả lập."""
from __future__ import annotations
import os
import re
import shutil
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

from pabt import ban_do_cad, chu_de, csdl, dxf_thuan, giao_dien
from tests import APP

CO_QT = APP is not None


def _ban_ve(f: Path) -> Path:
    return dxf_thuan.viet(f, [('RANH THUA', [(0, 0), (20, 0), (20, 10), (0, 10)]),
                              ('RANH THU HOI', [(10, -5), (30, -5), (30, 20), (10, 20)])], [('NHAN', '7', 5, 5)])


class TestDocBanDoMotLan(unittest.TestCase):
    def setUp(self):
        self.td = Path(tempfile.mkdtemp(prefix='pabt_1033_'))
        ban_do_cad._NHO_DOC.clear()

    def tearDown(self):
        ban_do_cad._NHO_DOC.clear()
        shutil.rmtree(self.td, ignore_errors=True)

    def test_doc_lop_roi_phan_tich_doc_file_mot_lan(self):
        f = _ban_ve(self.td / 'To_3.dxf')
        goc = dxf_thuan.doc
        with mock.patch.object(dxf_thuan, 'doc', side_effect=goc) as doc:
            ban_do_cad.doc_lop(f)
            ban_do_cad.phan_tich(f, 'RANH THUA', 'RANH THU HOI')
            ban_do_cad.phan_tich(f, 'RANH THUA', None)
            self.assertEqual(doc.call_count, 1)
            time.sleep(0.01)
            _ban_ve(f)                                                 # file sửa (mtime / cỡ đổi): đọc lại
            os.utime(f, ns=(time.time_ns(), time.time_ns() + 10 ** 9))
            ban_do_cad.phan_tich(f, 'RANH THUA', None)
            self.assertEqual(doc.call_count, 2)

    def test_giu_toi_da_hai_file(self):
        for i in range(4):
            ban_do_cad.doc_lop(_ban_ve(self.td / f'To_{i}.dxf'))
        self.assertLessEqual(len(ban_do_cad._NHO_DOC), ban_do_cad.NHO_DOC_TOI_DA)

    @unittest.skipUnless(CO_QT, 'không có Qt')
    def test_hop_nhap_khong_phan_tich_trung_tham_so(self):
        from tests.test_toc_do import _du_an
        from pabt.man_hinh_ban_do import HopNhapCad
        con = csdl.mo(_du_an(self.td, 3))
        self.addCleanup(con.close)
        h = HopNhapCad(con)
        h.im_lang = True
        self.assertTrue(h.chon_file(str(_ban_ve(self.td / 'To_3.dxf'))))
        h.cb_thua.setCurrentIndex(h.cb_thua.findData('RANH THUA'))
        self.assertTrue(h.phan_tich())                                  # đổi lớp ranh thửa: phân tích lại
        self.assertEqual(h.bang.rowCount(), 1)
        self.assertTrue(h.bang.updatesEnabled())
        goc = ban_do_cad.phan_tich
        with mock.patch.object(ban_do_cad, 'phan_tich', side_effect=goc) as pt:
            self.assertTrue(h.phan_tich())                              # cùng tham số: không phân tích lại
            self.assertEqual(pt.call_count, 0)
            h.o_to.setText('9')                                         # đổi số tờ: phân tích lại
            self.assertTrue(h.phan_tich())
            self.assertEqual(pt.call_count, 1)
        self.assertEqual(h.kq.so_to, '9')
        h.close()


class _UngDungGia:
    """Thay QApplication.instance() khi kiểm dat_tong_nen: ghi lại bảng màu / bảng kiểu thay vì áp cho mọi widget còn sống của lượt kiểm thử
    (áp thật: mỗi lần hàng chục giây khi lượt đầy đủ đã tạo nhiều cửa sổ)."""
    _bo_to_mau = object()
    _tuong_phan_cao = False

    def __init__(self):
        self.kieu, self.mau = '', None

    @staticmethod
    def platformName():
        return 'offscreen'                      # cai_dat_nho(): không đọc / ghi QSettings của máy thật

    def setStyleSheet(self, s):
        self.kieu = s

    def setPalette(self, p):
        self.mau = p


class TestTongNen(unittest.TestCase):
    def tearDown(self):
        giao_dien.dat_tong_nen('sang', ap_lai=False)

    def test_cau_hinh_khong_qt(self):
        self.assertEqual(set(chu_de.TONG_NEN), {'sang', 'diu', 'am', 'toi', 'trang'})                      # 1.0.34: thêm Ấm, Tối
        self.assertEqual(chu_de.TONG_NEN['sang'][1:], ('#F1F5F9', '#FFFFFF', '#CBD5E1', '#0F172A', '#475569'))   # Sáng Sapphire
        self.assertEqual(chu_de.doc(None)['tong_nen'], 'sang')
        with mock.patch.dict(os.environ, {'PABT_TONG_NEN': 'diu'}):
            self.assertEqual(chu_de.doc(None)['tong_nen'], 'diu')
        with mock.patch.dict(os.environ, {'PABT_TONG_NEN': 'la'}):
            self.assertEqual(chu_de.doc(None)['tong_nen'], 'sang')                  # giá trị lạ bỏ qua

        class _CaiDat(dict):
            def value(self, k, md=None):
                return self.get(k, md)

            def setValue(self, k, v):
                self[k] = v
        cd = _CaiDat()
        chu_de.ghi(cd, tong_nen='trang')
        self.assertEqual(cd[chu_de.KHOA_TONG_NEN], 'trang')
        self.assertEqual(chu_de.doc(cd)['tong_nen'], 'trang')
        chu_de.ghi(cd, mat_do='gon')                                                # chỉ ghi phần được đưa vào
        self.assertEqual(cd[chu_de.KHOA_TONG_NEN], 'trang')

    def test_doi_mau_bang_kieu(self):
        goc = giao_dien._qss_day_du()
        self.assertEqual(giao_dien.ap_tong_nen(goc, 'sang'), goc)                  # áp lại tông đang dùng: không đổi thêm
        self.assertIn('background: #F1F5F9', goc)                                   # 1.0.34: mặc định Sáng Sapphire khác màu gốc
        diu = giao_dien.ap_tong_nen(goc, 'diu')
        self.assertNotEqual(diu, goc)
        trang_chu = re.compile(r'(?<![\w-])color\s*:\s*#FFFFFF', re.I)
        self.assertEqual(len(trang_chu.findall(diu)), len(trang_chu.findall(goc)))      # chữ trắng trên nút xanh giữ nguyên
        self.assertIn('background: #E2E8F0', diu)
        self.assertNotIn('color: #0F172A', giao_dien.ap_tong_nen(goc, 'trang'))       # chữ chính đen hẳn
        self.assertIn('color: #000000', giao_dien.ap_tong_nen(goc, 'trang'))

    @unittest.skipUnless(CO_QT, 'không có Qt')
    def test_dat_tong_nen_ap_ngay_va_hop_giao_dien(self):
        from pabt.man_hinh_giao_dien import HopGiaoDien
        ud = _UngDungGia()
        with mock.patch.object(giao_dien.QApplication, 'instance', return_value=ud):
            self.assertEqual(giao_dien.dat_tong_nen('diu'), 'diu')
            self.assertEqual((giao_dien.TOKEN['nen'], giao_dien.TOKEN['vach']), ('#E2E8F0', '#94A3B8'))
            self.assertIn('background: #E2E8F0', ud.kieu)
            self.assertEqual(ud.mau.window().color().name().upper(), '#E2E8F0')
            giao_dien.dat_tong_nen('sang')
            self.assertEqual(giao_dien.TOKEN['nen'], '#F1F5F9')
            self.assertEqual(ud.kieu, giao_dien._qss_day_du())                       # về đúng bảng kiểu Sáng Sapphire
            h = HopGiaoDien(im_lang=True)
            self.assertEqual(set(h.r_tong_nen), set(chu_de.TONG_NEN))
            self.assertTrue(h.r_tong_nen['sang'].isChecked())
            h.r_tong_nen['trang'].setChecked(True)
            self.assertEqual(giao_dien.TONG_NEN[0], 'trang')
            self.assertIn('#94A3B8', ud.kieu)
            self.assertIn('tông nền', h.lb.text())
        h.close()
        h.deleteLater()


@unittest.skipUnless(CO_QT, 'không có Qt')
class TestKpiVaBanDo(unittest.TestCase):
    def test_nhom_kpi(self):
        from pabt.app import CuaSoChinh
        w = CuaSoChinh()
        try:
            self.assertEqual(w.the_khung['tong'].property('nhom_kpi'), 'tien')
            self.assertEqual(w.the_khung['da_bg'].property('nhom_kpi'), 'xong')
            self.assertIsNone(w.the_khung['so_ho'].property('nhom_kpi'))
            qss = giao_dien._qss_day_du()
            for k, m in giao_dien.MAU_NHOM_KPI.items():
                self.assertIn(f'QWidget[vai="the_so"][nhom_kpi="{k}"] {{ border-left-color: {m}; }}', qss)
            self.assertLess(qss.index('[the="tong"]'), qss.index('[nhom_kpi="tien"]'))     # nhóm đặt sau: thắng màu theo thẻ
            self.assertIn('selection-background-color: #DBEAFE', qss)
        finally:
            w.close()
            w.deleteLater()
            APP.processEvents()

    def test_tong_thua_va_ty_le_dong_thuan(self):
        from tests.test_toc_do import _du_an
        from pabt.man_hinh_ban_do import HopBanDo
        td = Path(tempfile.mkdtemp(prefix='pabt_1033_bd_'))
        self.addCleanup(shutil.rmtree, td, True)
        con = csdl.mo(_du_an(td, 3))
        self.addCleanup(con.close)
        ds = [ban_do_cad.ThuaBanDo(**{**{f: None for f in ban_do_cad.ThuaBanDo.__dataclass_fields__},
                                      'so_to': '1', 'so_thua': str(i), 'toa_do': [(0, 0), (1, 0), (1, 1)], 'trang_thai': tt})
              for i, tt in enumerate(('dong_y', 'dong_y', 'khong', 'khong_gan'))]
        with mock.patch.object(ban_do_cad, 'doc_ban_do', return_value=ds), mock.patch.object(ban_do_cad, 'ds_to', return_value=['1']):
            b = HopBanDo(con)
        self.assertEqual(b.lb_tong.text(), 'Tổng 4 thửa · đồng thuận 66,7%')        # 2 / 3 thửa đã gắn hộ
        b.close()
        b.deleteLater()
        APP.processEvents()


if __name__ == '__main__':
    unittest.main()

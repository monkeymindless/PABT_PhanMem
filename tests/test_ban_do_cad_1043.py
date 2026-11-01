"""1.0.43: bản đồ máy tính vẽ đúng KML CAD (lưới thửa / ranh Level, nhãn chứ không chấm) + công cụ lớp / phóng / tra cứu.

Số liệu GIẢ LẬP theo cấu trúc file MicroStation / gCadas (không chép bản vẽ thật)."""
from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

from PySide6.QtWidgets import QApplication, QGraphicsEllipseItem, QGraphicsPathItem, QGraphicsSimpleTextItem

from pabt import ban_do_kml
from tests.test_sua_font_kml import _kml


def _app():
    return QApplication.instance() or QApplication([])


class TestVeCad(unittest.TestCase):
    def setUp(self):
        _app()
        self.td = tempfile.TemporaryDirectory()
        self.addCleanup(self.td.cleanup)
        pm = (
            '<Placemark><name>Polyline_ranh</name><description>tanan2|Level 10</description><styleUrl>#m</styleUrl>'
            '<LineString><coordinates>106.95,11.02,0 106.951,11.021,0 106.952,11.019,0</coordinates></LineString></Placemark>'
            '<Placemark><name>549</name><description>Level 3</description>'
            '<Point><coordinates>106.9505,11.0204,0</coordinates></Point></Placemark>'
            '<Placemark><name>CLN</name><description>Level 3</description>'
            '<Point><coordinates>106.9506,11.0205,0</coordinates></Point></Placemark>'
            '<Placemark><name>DN.T737</name><description>Level 44</description>'
            '<Point><coordinates>106.9502,11.0202,0</coordinates></Point></Placemark>'
            '<Placemark><name>Hành lang bảo vệ nguồn nước</name><description>Level 39</description>'
            '<Point><coordinates>106.9508,11.0208,0</coordinates></Point></Placemark>'
            '<Placemark><name>*</name><description>Level 2</description>'
            '<Point><coordinates>106.9503,11.0203,0</coordinates></Point></Placemark>'
        )
        self.f = Path(self.td.name) / 'cad.kml'
        self.f.write_text(_kml(pm), encoding='utf-8')

    def _hop(self):
        from pabt.man_hinh_ban_do import HopBanDo
        h = HopBanDo(None)
        h.im_lang = True

        def dong():
            h.done(0)
            h.deleteLater()
            _app().processEvents()
        self.addCleanup(dong)
        h.resize(900, 600)
        h.view.resize(800, 500)
        return h

    def test_ve_duong_va_nhan_khong_cham(self):
        from pabt.man_hinh_ban_do import LOP_BD
        h = self._hop()
        self.assertGreater(h.mo_kml([self.f]), 0)
        self.assertTrue(h.khung_lop.isVisibleTo(h))
        self.assertTrue(h.khung_tc.isVisibleTo(h))
        self.assertEqual([k for k, _t in LOP_BD], ['duong', 'nhan', 'moc', 'ghi_chu'])
        duong = [r for r in h.view.kml_cad if r['lop'] == 'duong' and r['tt'].get('kieu') == 'duong']
        self.assertTrue(duong)
        self.assertTrue(any(isinstance(r['it'], QGraphicsPathItem) for r in duong))
        self.assertEqual(duong[0]['tt'].get('lop_cad'), 'Level 10')
        nhan = [r for r in h.view.kml_cad if r['tt'].get('loai') == 'thua']
        self.assertTrue(nhan)
        self.assertTrue(any(isinstance(r['it'], QGraphicsSimpleTextItem) for r in nhan))
        cham = [it for it in h.view.kml if isinstance(it, QGraphicsEllipseItem) and it.rect().width() >= 8]
        self.assertEqual(cham, [])                                  # không còn chấm 8 px cho mọi điểm
        self.assertTrue(any(it.text() == '549' for it in h.view.kml if isinstance(it, QGraphicsSimpleTextItem)))
        ky = [r for r in h.view.kml_cad if r['tt'].get('chu') == '*']
        self.assertEqual(ky, [])                                    # ký hiệu CAD bỏ, không vẽ chấm
        self.assertTrue(h.view.hop_nut.isVisibleTo(h.view))
        h.o_lop['duong'].setChecked(False)
        self.assertFalse(any(r['it'].isVisible() for r in duong))
        h.o_lop['duong'].setChecked(True)
        self.assertTrue(all(r['it'].isVisible() for r in duong))
        h.ve_bang_kml()
        self.assertGreater(h.bang_kml.rowCount(), 0)
        h.view.phong()
        h.view.thu()
        h.view.vua()
        self.assertIn('đường ranh', ban_do_kml.tom_tat_cad(h.lop_kml[0][1]))

"""Đường lệnh bộ đếm vùng chọn: dừng ở biên cửa sổ, tiêu đề cột của QTableView, bảng đã hủy phía C++, hộp đối chiếu không ở lại sau khi đóng.
Dữ liệu GIẢ LẬP."""
from __future__ import annotations

import gc
import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from PySide6.QtCore import QCoreApplication, QEvent, QItemSelectionModel, Qt
from PySide6.QtGui import QStandardItem, QStandardItemModel
from PySide6.QtWidgets import QDialog, QLabel, QTableView, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget

from pabt import du_thao
from pabt.giao_dien import _BoChonVung, gan_bo_dem
from pabt.man_hinh import CuaSoLapPA
from pabt.man_hinh_phien_ban import HopDoiChieu

from tests import APP
from tests.test_phien_ban_pa import _du_an, dat_cay

TIEU_DE = ['Tên', 'Số lượng', 'Đơn giá\n(đ)', 'Thành tiền\n(đ)']
DONG = [['A', '2', '1.000', '2.000'], ['B', '3', '3.000', '9.000']]


def _mo_hinh(cha) -> QStandardItemModel:
    m = QStandardItemModel(len(DONG), len(TIEU_DE), cha)
    m.setHorizontalHeaderLabels(TIEU_DE)
    for r, dong in enumerate(DONG):
        for c, chu in enumerate(dong):
            m.setItem(r, c, QStandardItem(chu))
    return m


def _bang_view(cha=None) -> QTableView:
    b = QTableView(cha)
    b.setModel(_mo_hinh(b))
    return b


def _chon_het(b) -> None:
    m = b.model()
    F = QItemSelectionModel.SelectionFlag
    for r in range(m.rowCount()):
        for c in range(m.columnCount()):
            b.selectionModel().select(m.index(r, c), F.Select)


def _bo_cua(b) -> _BoChonVung:
    gan_bo_dem(b)
    return next(x for x in b.children() if isinstance(x, _BoChonVung))


class _CoHam(QWidget):
    """Cửa sổ / khung có dải đếm: ghi lại mọi lần được gọi."""

    def __init__(self, cha=None):
        super().__init__(cha)
        self.goi = []

    def cap_nhat_bo_dem(self, bang, tk: dict) -> None:
        self.goi.append(bang)


class _CoHopCoHam(QDialog):
    def __init__(self, cha=None):
        super().__init__(cha)
        self.goi = []

    def cap_nhat_bo_dem(self, bang, tk: dict) -> None:
        self.goi.append(bang)


class TestBienCuaSo(unittest.TestCase):
    def _cua_so(self) -> _CoHam:
        w = _CoHam()
        self.addCleanup(w.deleteLater)
        return w

    def test_hop_thoai_con_khong_goi_ham_cua_cua_so_cha(self):
        w = self._cua_so()
        h = QDialog(w)
        lo = QVBoxLayout(h)
        b = _bang_view(h)
        lo.addWidget(b)
        _chon_het(b)
        bo = _bo_cua(b)
        bo.dem()
        self.assertEqual(w.goi, [])                         # không gọi nhầm cửa sổ đã mở hộp
        self.assertIsNotNone(bo.nhan_noi)                   # đi nhánh nhãn riêng của hộp
        self.assertTrue(bo.nhan_noi.property('chan_bang'))
        self.assertIs(bo.nhan_noi.parentWidget(), h)
        self.assertEqual(lo.indexOf(bo.nhan_noi), lo.indexOf(b) + 1)
        self.assertTrue(bo.nhan_noi.text())

    def test_bang_long_trong_khung_cua_hop_con(self):
        w = self._cua_so()
        h = QDialog(w)
        k = QWidget(h)
        QVBoxLayout(h).addWidget(k)
        b = _bang_view(k)
        QVBoxLayout(k).addWidget(b)
        _chon_het(b)
        bo = _bo_cua(b)
        bo.dem()
        self.assertEqual(w.goi, [])
        self.assertIsNotNone(bo.nhan_noi)

    def test_hop_con_co_ham_rieng_van_duoc_goi(self):
        w = self._cua_so()
        h = _CoHopCoHam(w)
        b = _bang_view(h)
        QVBoxLayout(h).addWidget(b)
        _chon_het(b)
        h.goi.clear()
        _bo_cua(b).dem()
        self.assertEqual(h.goi, [b])
        self.assertEqual(w.goi, [])

    def test_khung_nhung_co_ham_duoc_goi_truoc_cua_so(self):
        w = self._cua_so()
        k = _CoHam(w)                                       # kiểu CuaSoLapPA nhúng: không phải cửa sổ, có dải đếm riêng
        self.assertFalse(k.isWindow())
        trong = QWidget(k)
        b = _bang_view(trong)
        _chon_het(b)
        k.goi.clear()
        _bo_cua(b).dem()
        self.assertEqual(k.goi, [b])
        self.assertEqual(w.goi, [])

    def test_khung_nhung_khong_ham_van_len_toi_cua_so_chua_no(self):
        w = self._cua_so()
        k = QWidget(w)
        b = _bang_view(k)
        _chon_het(b)
        w.goi.clear()
        _bo_cua(b).dem()
        self.assertEqual(w.goi, [b])

    def test_bang_la_cua_so_rieng_khong_len_cha(self):
        w = self._cua_so()
        b = _bang_view(w)
        b.setWindowFlags(Qt.WindowType.Window)
        self.assertTrue(b.isWindow())
        _chon_het(b)
        bo = _bo_cua(b)
        w.goi.clear()
        bo.dem()
        self.assertEqual(w.goi, [])
        self.assertIsNotNone(bo.nhan_noi)

    def test_bang_khong_cha_khong_loi(self):
        b = _bang_view()
        self.addCleanup(b.deleteLater)
        _chon_het(b)
        bo = _bo_cua(b)
        bo.dem()
        self.assertIsNotNone(bo.nhan_noi)


class TestTinhVungChon(unittest.TestCase):
    """Hàm chỉ đọc self.lb_bo_dem khi bảng không có cột số: gọi với đối tượng rút gọn."""

    def setUp(self):
        self.gia = SimpleNamespace(lb_bo_dem=QLabel('chung'))

    def _tinh(self, b):
        return CuaSoLapPA._tinh_vung_chon(self.gia, b)

    def _bang_widget(self) -> QTableWidget:
        b = QTableWidget(len(DONG), len(TIEU_DE))
        self.addCleanup(b.deleteLater)
        b.setHorizontalHeaderLabels(TIEU_DE)
        for r, dong in enumerate(DONG):
            for c, chu in enumerate(dong):
                b.setItem(r, c, QTableWidgetItem(chu))
        return b

    def test_table_view_doc_tieu_de_tu_mo_hinh(self):
        b = _bang_view()
        self.addCleanup(b.deleteLater)
        self.assertFalse(hasattr(b, 'horizontalHeaderItem'))
        _chon_het(b)
        kq = self._tinh(b)
        self.assertIs(kq[0], b)
        self.assertIn('Đang chọn: 2 dòng (8 ô)', kq[1])
        self.assertIn('Tổng SL/DT: 5', kq[1])
        self.assertIn('Đơn giá TB: 2.000 đ', kq[1])
        self.assertIn('Tổng Thành tiền vùng chọn: 11.000 đồng', kq[1])

    def test_table_widget_ra_cung_ket_qua_voi_table_view(self):
        v = _bang_view()
        self.addCleanup(v.deleteLater)
        w = self._bang_widget()
        _chon_het(v)
        _chon_het(w)
        self.assertEqual(self._tinh(v)[1:], self._tinh(w)[1:])

    def test_table_view_khong_co_cot_so_dung_bo_dem_chung(self):
        b = QTableView()
        self.addCleanup(b.deleteLater)
        m = QStandardItemModel(2, 2, b)                     # không đặt tiêu đề: mô hình trả số thứ tự cột
        for r in range(2):
            for c in range(2):
                m.setItem(r, c, QStandardItem('1'))
        b.setModel(m)
        _chon_het(b)
        self.assertIn('chung', self._tinh(b)[1])

    def test_mot_o_khong_tinh(self):
        b = _bang_view()
        self.addCleanup(b.deleteLater)
        b.selectionModel().select(b.model().index(0, 1), QItemSelectionModel.SelectionFlag.Select)
        self.assertIsNone(self._tinh(b))


class _CoDuAn(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        cu = os.environ.get('PABT_THU_MUC_MAY')
        self.addCleanup(lambda: os.environ.pop('PABT_THU_MUC_MAY', None) if cu is None else os.environ.__setitem__('PABT_THU_MUC_MAY', cu))
        os.environ['PABT_THU_MUC_MAY'] = str(Path(self.tmp.name) / 'may')
        from pabt import app as ud
        self.w = ud.CuaSoChinh(menu_trai=True)
        self.w.show()
        self.w.mo(str(_du_an(Path(self.tmp.name))))
        APP.processEvents()
        self.addCleanup(self._dong)
        self.ma = self.w.con.execute('SELECT MIN(ma_ho) FROM ho').fetchone()[0]

    def _dong(self):
        self.w.close()
        if self.w.con is not None:
            self.w.dong_du_an()

    def _man(self, cho: bool = False):
        if cho:
            self.w.mo_lap_pa(self.ma)
            man = self.w.khung_tab.widget[('ho', int(self.ma))]
        else:
            man = self.w.mo_lap_pa(self.ma, cho=False)
            self.addCleanup(man.close)
        man.im_lang = True
        man.hoi_luu = lambda: True
        return man


def _xoa_cho() -> None:
    for _ in range(3):
        APP.processEvents()
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    gc.collect()


class TestCuaSoThat(_CoDuAn):
    def test_hop_tinh_gia_dat_khong_goi_cua_so_lap_pa(self):
        man = self._man()
        h = man.mo_bang_tinh_dat(cho=False)
        h.im_lang = True
        self.addCleanup(h.close)
        b = h.bang
        self.assertGreater(b.model().rowCount(), 0)
        with mock.patch.object(CuaSoLapPA, 'cap_nhat_bo_dem') as goi:
            b.selectAll()
            _bo_cua(b).dem()
        goi.assert_not_called()

    def test_cua_so_lap_pa_nhung_dung_ham_cua_no(self):
        man = self._man(cho=True)
        self.assertFalse(man.isWindow())
        man.tab.setCurrentIndex(1)
        man._dam_bao_bang(1)
        b = man.bang[1].bang
        gan_bo_dem(b)
        b.selectAll()
        tu_lap_pa, tu_chinh = [], []
        with mock.patch.object(type(man), 'cap_nhat_bo_dem', lambda s, bang, tk: tu_lap_pa.append(bang)), \
                mock.patch.object(type(self.w), 'cap_nhat_bo_dem', lambda s, bang, tk: tu_chinh.append(bang)):
            _bo_cua(b).dem()
        self.assertEqual(tu_lap_pa, [b])
        self.assertEqual(tu_chinh, [])

    def test_bang_da_huy_coi_nhu_het_vung_chon(self):
        man = self._man()
        b = QTableView()
        b.deleteLater()
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
        with self.assertRaises(RuntimeError):
            b.isVisible()
        man._chu_vung = (b, 'VUNG_CU', 'VUNG_CU')
        man._dat_chan()                                     # không văng RuntimeError
        self.assertIsNone(man._chu_vung)
        self.assertNotIn('VUNG_CU', man.lb_chan.text())
        self.assertIn('TỔNG', man.lb_chan.text())
        man._dat_chan()                                     # gọi lại khi đã quên: vẫn bình thường
        self.assertIsNone(man._chu_vung)

    def test_bang_con_song_nhung_an_giu_lai(self):
        man = self._man()
        b = QTableView()
        self.addCleanup(b.deleteLater)
        vung = (b, 'VUNG_CU', 'VUNG_CU')
        man._chu_vung = vung
        man._dat_chan()
        self.assertIs(man._chu_vung, vung)
        self.assertNotIn('VUNG_CU', man.lb_chan.text())


class TestHopDoiChieuKhongOLai(_CoDuAn):
    """Trước đây mỗi lần bấm Đối chiếu (không qua _chay_lenh) để lại một hộp ẩn giữ dữ liệu, đến lệnh menu kế tiếp mới dọn."""

    def _dem(self) -> int:
        return sum(1 for o in gc.get_objects() if type(o).__name__ == 'HopDoiChieu')

    def _thu(self, mo) -> None:
        truoc = self._dem()
        with mock.patch.object(HopDoiChieu, 'exec', lambda s: 0):
            for _ in range(3):
                mo()
                _xoa_cho()
        self.assertEqual(self._dem(), truoc)

    def test_tu_thanh_phien_ban(self):
        dat_cay(self.w.con, self.ma)
        man = self._man(cho=True)
        self._thu(lambda: man.thanh_pb.doi_chieu())

    def test_tu_thanh_phien_ban_trong_chay_lenh(self):
        dat_cay(self.w.con, self.ma)
        man = self._man(cho=True)
        self._thu(lambda: self.w._chay_lenh(lambda: man.thanh_pb.doi_chieu()))

    def test_tu_khung_niem_yet(self):
        con = self.w.con
        ds = [r[0] for r in con.execute('SELECT ma_ho FROM ho ORDER BY thu_tu')]
        dot = du_thao.tao_dot(con, 'Đợt 9', '2026-11-01', 'UBND')
        du_thao.them_thu_cong(con, dot, ds, ca_vuong=True)
        k = self.w.mo_du_thao(cho=False) or self.w.khung_tab.widget['du_thao']
        k.cb.setCurrentIndex(k.cb.findData(dot))
        self._thu(lambda: k.doi_chieu_phien_ban())


if __name__ == '__main__':
    unittest.main()

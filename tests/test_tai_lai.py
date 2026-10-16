"""Màn hình chính nạp lại theo hộ (csdl.DauVetHo + CuaSoChinh._tai_lai_ho): lưu / sửa vài hộ thì chỉ tính lại các hộ đó, kết quả
phải giống hệt nạp lại toàn bộ; thêm / xóa hộ, đổi danh mục, máy khác ghi vào file thì nạp lại toàn bộ như trước."""
from __future__ import annotations
import shutil
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from pabt import csdl, doi_chieu, ho_so, quan_ly
from pabt.lap_pa import BoSoan
from tests.test_toc_do import _du_an

try:
    import PySide6  # noqa: F401
    CO_QT = True
except ImportError:
    CO_QT = False


class TestDauVetHo(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.p = _du_an(Path(self.td.name))
        self.con = csdl.mo(self.p)
        self.dv = csdl.DauVetHo(self.con)

    def tearDown(self):
        self.con.close()
        self.td.cleanup()

    def test_ghi_theo_ho(self):
        self.assertEqual(self.dv.lay(), set())
        bo = BoSoan(self.con, 3)
        bo.pa.dat[0].ghi_chu = 'sửa'
        bo.luu()
        self.assertEqual(self.dv.lay(), {3})
        self.assertEqual(self.dv.lay(), set())                         # lấy rồi thì không còn
        t = self.con.execute('SELECT ma_thua FROM thua WHERE ma_ho = 2 LIMIT 1').fetchone()[0]
        ho_so.chuyen_thua(self.con, t, 5)                              # chuyển thửa: cả hộ cũ lẫn hộ mới
        self.assertEqual(self.dv.lay(), {2, 5})
        self.assertFalse(self.con.in_transaction)                     # lấy không mở giao dịch (csdl.nho, hoàn tác)

    def test_phai_nap_toan_bo(self):
        ho_so.luu_ho(self.con, None, dict(ho_ten='Hộ mới'), [])       # thêm hộ
        self.assertIsNone(self.dv.lay())
        ho_so.xoa_ho(self.con, 1)                                      # xóa hộ (đánh lại số thứ tự)
        self.assertIsNone(self.dv.lay())
        with self.con, csdl.mo_khoa_danh_muc(self.con):               # danh mục / bảng không theo hộ
            self.con.execute("UPDATE dm_hotro SET ten = ten WHERE rowid = 1")
        self.assertIsNone(self.dv.lay())
        with self.con:
            self.con.execute("UPDATE ho SET ghi_chu = 'x' WHERE ma_ho = 4")
        self.assertEqual(self.dv.lay(), {4})
        khac = sqlite3.connect(str(self.p))                            # kết nối / máy khác ghi vào file
        with khac:
            khac.execute("UPDATE ho SET ghi_chu = 'y' WHERE ma_ho = 4")
        khac.close()
        self.assertIsNone(self.dv.lay())

    def test_rollback_khong_ghi_nhan(self):
        self.con.execute("UPDATE ho SET ghi_chu = 'z' WHERE ma_ho = 6")
        self.con.rollback()
        self.assertEqual(self.dv.lay(), set())


@unittest.skipUnless(CO_QT, 'cần PySide6')
class TestTaiLaiTheoHo(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.goc = _du_an(Path(cls.tmp.name), so_ho=30)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def setUp(self):
        self.p = Path(self.tmp.name) / f'{self._testMethodName}.pabt'
        shutil.copy(self.goc, self.p)

    def _cua_so(self, chi_doc=False):
        from pabt.app import CuaSoChinh
        w = CuaSoChinh()
        w.mo(str(self.p), chi_doc=chi_doc)
        self.addCleanup(w.close)
        self.addCleanup(w.dong_du_an)
        return w

    @staticmethod
    def _anh(w) -> dict:
        """Mọi thứ màn hình chính hiện về danh sách hộ (để so nạp theo hộ với nạp toàn bộ)."""
        dong = sorted((d['ma_ho'], [str(x) for x in d['o']], str(d['tong']), d['lech'], d['goi_y_tt'], d['mau_tt'],
                       d['tim'], d.get('theo_doi'), d.get('dot_id')) for d in w.mo_hinh.dong)
        kq = w.kq
        return dict(dong=dong, ho=[(h['ma_ho'], str(h['tong']), h['lech'], h['sua'] is not None) for h in kq.ho],
                    lech=[(m, d.stt, str(d.thanh_tien)) for m, _, d in kq.dong_lech], canh_bao=list(kq.canh_bao),
                    du_an=w.windowTitle().split('  [')[0], ket_qua=w.lb_ket_qua.text(),
                    the_so={k: o.text() for k, o in w.the_so.items()})

    def _so_voi_toan_bo(self, w):
        w2 = self._cua_so(chi_doc=True)                                # mở lại file: nạp toàn bộ
        self.assertEqual(self._anh(w), self._anh(w2))

    def test_luu_mot_ho_chi_tinh_lai_ho_do(self):
        w = self._cua_so()
        bo = BoSoan(w.con, 7)
        bo.sua_dat(0, 'dien_tich', '12,5')
        bo.luu()
        with mock.patch.object(doi_chieu, 'doi_chieu', wraps=doi_chieu.doi_chieu) as dc:
            w.tai_lai()
        self.assertEqual(dc.call_args.kwargs.get('ds_ma_ho'), [7])
        self._so_voi_toan_bo(w)
        # bỏ dòng mục 1 của hộ: hết phương án, có cảnh báo khác
        bo = BoSoan(w.con, 7)
        bo.xoa(1, 0)
        bo.luu()
        w.tai_lai()
        self._so_voi_toan_bo(w)

    def test_trang_thai_va_hoan_tac(self):
        w = self._cua_so()
        quan_ly.cap_nhat_trang_thai(w.con, [4], dict(theo_doi='Chờ ký biên bản'))
        with mock.patch.object(doi_chieu, 'doi_chieu', wraps=doi_chieu.doi_chieu) as dc:
            w.tai_lai()
        self.assertEqual(dc.call_args.kwargs.get('ds_ma_ho'), [4])
        w.o_tim.setText('ky bien ban')                                 # tìm theo nội dung mới của dòng vừa thay
        w.o_tim.phat_ngay()                                            # ô tìm chờ ngừng gõ 200 ms (0.9.24): lọc ngay
        self.assertEqual(w.ho_dang_loc(), [4])
        w.o_tim.setText('')
        w.o_tim.phat_ngay()
        self._so_voi_toan_bo(w)
        w.ht.chot()
        self.assertTrue(w.hoan_tac())                                  # hoàn tác cũng chỉ tính lại hộ đó
        self._so_voi_toan_bo(w)

    def test_them_ho_nap_toan_bo(self):
        w = self._cua_so()
        n = len(w.mo_hinh.dong)
        ho_so.luu_ho(w.con, None, dict(ho_ten='Hộ thêm'), [])
        with mock.patch.object(doi_chieu, 'doi_chieu', wraps=doi_chieu.doi_chieu) as dc:
            w.tai_lai()
        self.assertIsNone(dc.call_args.kwargs.get('ds_ma_ho'))
        self.assertEqual(len(w.mo_hinh.dong), n + 1)
        self._so_voi_toan_bo(w)

    def test_lenh_giai_phong_hop_da_dong(self):
        """Mở cửa sổ lập phương án nhiều lần qua lệnh: không để lại cửa sổ ẩn (trước 0.9.16: mỗi lần một cửa sổ ẩn ~290 thành
        phần giữ kết nối dự án). Từ 0.9.32 hộ mở trong tab: mở lại cùng hộ dùng lại tab, không tạo thêm cửa sổ."""
        from PySide6.QtCore import QEvent
        from PySide6.QtWidgets import QApplication, QDialog
        from pabt.man_hinh import CuaSoLapPA
        w = self._cua_so()
        for _ in range(5):
            w.lenh['Lập phương án hộ…'].trigger()
        QApplication.processEvents()
        lap = [h for h in w.findChildren(CuaSoLapPA)]
        self.assertEqual(len(lap), 1)                                   # một tab hộ, không phải 5 cửa sổ
        self.assertEqual(sum(1 for k in w.khung_tab.khoa if isinstance(k, tuple) and k[0] == 'ho'), 1)
        QApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
        self.assertEqual([h for h in w.findChildren(QDialog) if not h.isVisible() and not h.property('nhung_tab')], [])
        lap[0].bo_thay_doi()
        from PySide6.QtCore import QModelIndex
        w.bang.setCurrentIndex(QModelIndex())
        self.assertIsNone(w.xem_chi_tiet_tinh(cho=False))             # chưa chọn hộ (trước: KeyError 'không có hộ mã None')
        self.assertIsNotNone(w.xem_chi_tiet_tinh(3, cho=False))


if __name__ == '__main__':
    unittest.main()

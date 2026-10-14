"""0.9.72 (người dùng 13/10/2026): Thông tin dự án gọn (bỏ Tên đầy đủ / Số phương án / Ký hiệu số -> ký hiệu theo đợt trình), Cơ
quan thẩm định, kinh phí QĐ 08 tự chọn theo tên; Địa chỉ gọn trên danh sách hộ; Ctrl + mũi tên chuyển hộ; tự nhận diện mật độ
cây. Số liệu GIẢ LẬP."""
from __future__ import annotations
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

from PySide6.QtWidgets import QApplication

from pabt import cay_trong as ct, csdl, in_an, lap_pa, quan_ly, van_ban_trinh as vb
from pabt.ho_so import rut_gon_dia_chi
from tests.test_toc_do import _du_an


class _Co(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.td = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.td, True)
        moi = mock.patch.dict(os.environ, {'PABT_THU_MUC_MAY': str(self.td / 'may')})
        moi.start()
        self.addCleanup(moi.stop)
        self.p = _du_an(self.td, so_ho=3)
        self.con = csdl.mo(self.p)
        self.addCleanup(self.con.close)
        self.ma = [r[0] for r in self.con.execute('SELECT ma_ho FROM ho ORDER BY thu_tu')]


class TestThongTinDuAn(_Co):
    def test_truong_gon_va_v15(self):
        k = dict(lap_pa.TRUONG_DU_AN)
        for bo in ('ten_day_du', 'so_phuong_an', 'ky_hieu_so'):
            self.assertNotIn(bo, k)
        self.assertIn('co_quan_tham_dinh', k)
        self.assertEqual(self.con.execute('PRAGMA user_version').fetchone()[0], csdl.PHIEN_BAN_CSDL)   # v15 (0.9.72) trở lên
        gt = lap_pa.doc_du_an(self.con)
        gt.update(ten='Đường giả lập ĐT 999', co_quan_tham_dinh='Phòng Thử nghiệm')
        lap_pa.luu_du_an(self.con, gt)
        r = self.con.execute('SELECT ten, ten_day_du, co_quan_tham_dinh FROM du_an').fetchone()
        self.assertEqual(tuple(r), ('Đường giả lập ĐT 999', 'Đường giả lập ĐT 999', 'Phòng Thử nghiệm'))   # một tên dự án

    def test_kinh_phi_tu_chon_theo_ten(self):
        from pabt.man_hinh import HopDuAn
        h = HopDuAn(self.con)
        self.addCleanup(h.close)
        self.assertNotIn('', [h.o_loai_kp.itemData(i) for i in range(h.o_loai_kp.count())])   # không còn "Tự nhận…"
        for ten, loai in (('Nâng cấp đường ĐT 999', 'tuyen'), ('Khu dân cư giả lập', 'khac'), ('Kênh tưới giả lập', 'tuyen'),
                          ('Đường dây 110 kV giả lập', 'tuyen'), ('Trường học giả lập', 'khac')):
            h.o['ten'].setText(ten)
            self.assertEqual(h.o_loai_kp.currentData(), loai, ten)
        h.o_loai_kp.setCurrentIndex(h.o_loai_kp.findData('tuyen'))
        h.o_loai_kp.activated.emit(h.o_loai_kp.currentIndex())             # người dùng tự chọn: không đổi theo tên nữa
        h.o['ten'].setText('Khu tái định cư giả lập')
        self.assertEqual(h.o_loai_kp.currentData(), 'tuyen')
        # cơ quan thẩm định: gợi ý theo cấp địa bàn, gõ tự do được
        h.o['cap_dia_ban'].setCurrentText('Phường')
        h.o['ten_dia_ban'].setText('Thử')
        w = h.o['co_quan_tham_dinh']
        self.assertEqual(w.itemText(0), 'Phòng Kinh tế, Hạ tầng và Đô thị phường Thử')
        h.o['cap_dia_ban'].setCurrentText('Xã')
        self.assertEqual(w.itemText(0), 'Phòng Kinh tế xã Thử')
        w.setEditText('Phòng Kinh tế xã Thử')
        h.accept()
        self.assertEqual(lap_pa.doc_du_an(self.con)['co_quan_tham_dinh'], 'Phòng Kinh tế xã Thử')
        self.assertEqual(lap_pa.kinh_phi_to_chuc(self.con)[0], 'tuyen')

    def test_co_quan_tham_dinh_trong_to_trinh(self):
        self.assertEqual(lap_pa.co_quan_tham_dinh_mac_dinh('Phường', 'A'), 'Phòng Kinh tế, Hạ tầng và Đô thị phường A')
        self.assertEqual(lap_pa.co_quan_tham_dinh_mac_dinh('Xã', 'B'), 'Phòng Kinh tế xã B')
        chung, _ = vb.du_lieu(self.con, self.ma)
        self.assertTrue(chung['co_quan_tham_dinh'].startswith('Phòng Kinh tế'))          # trống: theo cấp địa bàn
        with self.con:
            self.con.execute("UPDATE du_an SET co_quan_tham_dinh = 'Cơ quan thẩm định giả lập'")
        chung, _ = vb.du_lieu(self.con, self.ma)
        self.assertEqual(chung['co_quan_tham_dinh'], 'Cơ quan thẩm định giả lập')
        self.assertIn('co_quan_tham_dinh', vb.cho_trong_trong_file(vb.file_mau('to_trinh')))


class TestKyHieuTheoDot(_Co):
    def test_ky_hieu_so_cua_dot(self):
        with self.con:
            self.con.execute("UPDATE du_an SET ky_hieu_so = 'PA-CU'")        # file cũ: ký hiệu ở dự án
        d1 = quan_ly.tao_dot(self.con)
        self.assertEqual(quan_ly.lay_dot(self.con, d1).ky_hieu_so, 'PA-CU')    # đợt mới lấy ký hiệu cũ của dự án
        quan_ly.sua_dot(self.con, d1, 'Đợt 1', ky_hieu_so='PA-DOT1')
        d2 = quan_ly.tao_dot(self.con)
        self.assertEqual(quan_ly.lay_dot(self.con, d2).ky_hieu_so, 'PA-DOT1')  # theo đợt gần nhất
        quan_ly.gan_dot(self.con, self.ma[:1], d1)
        self.assertEqual(in_an.ky_hieu_cua_ho(self.con, self.ma[0], 'PA-CU'), 'PA-DOT1')
        self.assertEqual(in_an.ky_hieu_cua_ho(self.con, self.ma[1], 'PA-CU'), 'PA-CU')     # chưa vào đợt: của dự án
        chung, dong = vb.du_lieu(self.con, self.ma[:1], quan_ly.lay_dot(self.con, d1))
        self.assertEqual(chung['ky_hieu_so'], 'PA-DOT1')
        from pabt.man_hinh_quan_ly import HopSuaDot
        h = HopSuaDot(None, quan_ly.lay_dot(self.con, d1))
        self.addCleanup(h.close)
        self.assertEqual(h.gia_tri()['ky_hieu_so'], 'PA-DOT1')


class TestDiaChiGon(unittest.TestCase):
    def test_rut_gon(self):
        for dc, kq in (('Ấp 1, xã Thử Nghiệm, huyện A, tỉnh B', 'Ấp 1'), ('Khu phố 2, phường Thử Nghiệm', 'Khu phố 2'),
                       ('Ấp 3, xã Khác, huyện A', 'Ấp 3, xã Khác, huyện A'), ('Thử Nghiệm', 'Thử Nghiệm'),
                       ('Tổ 5, ấp X, Thử Nghiệm, tỉnh B', 'Tổ 5, ấp X'), ('', '')):
            self.assertEqual(rut_gon_dia_chi(dc, 'Thử Nghiệm'), kq, dc)
        self.assertEqual(rut_gon_dia_chi('Ấp 1, xã A', ''), 'Ấp 1, xã A')       # chưa có địa bàn dự án: giữ nguyên

    def test_bang_ho_hien_gon_chu_thich_day_du(self):
        from PySide6.QtCore import Qt
        from pabt.app import BangHo
        m = BangHo([dict(ma_ho=1, dia_chi='Ấp 1, xã Thử, huyện A', o=[1, 'A', 'Ấp 1', 1, 0, '', ''])])
        self.assertEqual(m.data(m.index(0, 2)), 'Ấp 1')
        self.assertIn('Ấp 1, xã Thử, huyện A', m.data(m.index(0, 2), Qt.ItemDataRole.ToolTipRole))


class TestPhimChuyenHo(_Co):
    def test_ctrl_mui_ten(self):
        from pabt.man_hinh import CuaSoLapPA
        w = CuaSoLapPA(self.con, self.ma[0])
        self.addCleanup(w.close)
        phim = {sc.key().toString() for sc in w._phim}
        self.assertTrue({'Ctrl+Left', 'Ctrl+Right', 'Ctrl+PgUp', 'Ctrl+PgDown'} <= phim)
        sc = next(s for s in w._phim if s.key().toString() == 'Ctrl+Right')
        sc.activated.emit()
        self.assertEqual(w.bo.ma_ho, self.ma[1])
        next(s for s in w._phim if s.key().toString() == 'Ctrl+Left').activated.emit()
        self.assertEqual(w.bo.ma_ho, self.ma[0])
        w.bo_thay_doi()


class TestMatDo(_Co):
    def test_gan_dung_va_canh_bao(self):
        q = ct.quy_chuan_mat_do(self.con, 'Nhãn xuồng giả lập')               # danh mục: "Cây nhãn … Mật độ … cây/ha"
        self.assertIsNotNone(q.mat_do)
        self.assertEqual(q.nguon, 'gần đúng')
        self.assertEqual(ct.mat_do_thuc_te(120, 1000), 1200)
        # nhập số cây vượt mật độ ở thẻ Cây trồng: báo ngay (không tự đổi số liệu)
        from pabt.man_hinh import CuaSoLapPA
        w = CuaSoLapPA(self.con, self.ma[0])
        self.addCleanup(w.close)
        m = next(x for x in w.bo.dm.muc[3] if 'nhãn' in x.ten.lower() and x.can_cu and 'ật độ' in x.can_cu)
        i, _ = w.bo.them_tu_danh_muc(3, m)
        w.sua_o(3, i, 'so_luong', '100000')
        self.assertIn('vượt mật độ', w.lb_tb.text())
        self.assertEqual(int(w.bo.pa.khoan[3][i].so_luong), 100000)
        w.sua_o(3, i, 'so_luong', '1')
        self.assertNotIn('vượt mật độ', w.lb_tb.text())
        d = w.tinh_mat_do(i, cho=False)
        self.assertIn('Mật độ thực tế', d.lb.text())
        w.bo_thay_doi()


if __name__ == '__main__':
    unittest.main()

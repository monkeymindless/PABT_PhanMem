"""20/10/2026 (người dùng): Tìm nhanh Ctrl+K, phím Ctrl+1..5 mới, cảnh báo tức thời không chặn (diện tích mục 1, bàn giao thiếu ngày
biên bản), phông số đồng bộ. Dữ liệu GIẢ LẬP (tests.test_toc_do._du_an)."""
from __future__ import annotations

from tests.test_dac_ta_v5 import CoSo
from tests.test_toc_do import _du_an


class _CoCuaSo(CoSo):
    w = None

    def tearDown(self):
        if self.w is not None:                          # đóng dự án trước khi xóa thư mục tạm
            for k in [k for k in self.w.khung_tab.khoa if isinstance(k, tuple)]:
                self.w.khung_tab.widget[k].bo_thay_doi()
            self.w.close()
            self.w.dong_du_an() if self.w.con is not None else None
        super().tearDown()

    def _cua_so(self, so_ho=4, cccd=True):
        from pabt import app as ud
        p = _du_an(self.td, so_ho)
        if cccd:
            from pabt import csdl
            c = csdl.mo(p)
            with c:
                for ma, in c.execute('SELECT ma_ho FROM ho').fetchall():
                    c.execute('UPDATE ho SET so_cccd = ? WHERE ma_ho = ?', (f'0750920000{ma:02d}', ma))
            c.close()
        w = ud.CuaSoChinh(menu_trai=True)
        self.w = w
        w.show()
        w.mo(str(p))
        self.app.processEvents()
        return ud, w


class TestTimNhanh(_CoCuaSo):
    def test_phim_tat_moi(self):
        ud, w = self._cua_so()
        from PySide6.QtGui import QKeySequence
        phim = {t: a.shortcut().toString() for t, a in w.lenh.items() if not a.shortcut().isEmpty()}
        self.assertEqual(phim['Danh sách hộ'], 'Ctrl+1')
        self.assertEqual(phim['Dự toán & khái toán'], 'Ctrl+2')
        self.assertEqual(phim['Bộ đơn giá…'], 'Ctrl+3')
        self.assertEqual(phim['Dự thảo PABT…'], 'Ctrl+4')
        self.assertEqual(phim['Theo dõi tiến độ'], 'Ctrl+5')
        self.assertEqual(phim['Tìm nhanh…'], 'Ctrl+K')
        self.assertNotIn('Tổng hợp tiền theo phương án', phim)
        self.assertNotIn('Quyết định phê duyệt', phim)
        self.assertEqual(len(phim.values()), len(set(phim.values())), phim)        # không trùng phím
        for t, _p in ud.PHIM_NHANH:
            self.assertIn(w.lenh[t], w.actions())
        self.assertIn(w.lenh['Tìm nhanh…'], w.menu_tren['Chỉnh sửa'].actions())   # một chỗ trên menu
        self.assertEqual(w.lenh['Tìm nhanh…'].shortcut(), QKeySequence('Ctrl+K'))
        # Ctrl+3 / Ctrl+4 mở đúng tab (bộ đơn giá, niêm yết)
        w.lenh['Bộ đơn giá…'].trigger()
        self.app.processEvents()
        self.assertIs(w.ngan_lv.currentWidget(), w.khung_tab.stack_phu)
        self.assertIn('don_gia', w.khung_tab.khoa)
        w.lenh['Dự thảo PABT…'].trigger()
        self.app.processEvents()
        self.assertIn('du_thao', w.khung_tab.khoa)
        w.lenh['Dự toán & khái toán'].trigger()
        self.assertEqual(w.trang.currentIndex(), ud.STACK_DU_TOAN)

    def test_tim_theo_cccd_ten_thua_va_lenh(self):
        ud, w = self._cua_so()
        from pabt.man_hinh_tim_nhanh import LOAI_HO, LOAI_LENH
        hop = w.tim_nhanh(cho=False)
        self.addCleanup(hop.deleteLater)
        self.assertTrue(hop.im_lang)
        ma = [r[0] for r in w.con.execute('SELECT ma_ho FROM ho ORDER BY thu_tu')]
        # chưa gõ: chỉ chức năng
        self.assertTrue(hop.dong_hien() and all(l == LOAI_LENH for l, _ in hop.dong_hien()))
        hop.o.setText(f'0750920000{ma[2]:02d}')                         # CCCD
        self.assertEqual(hop.dong_hien()[0], (LOAI_HO, ma[2]))
        hop.o.setText('ho thu 1')                                       # họ tên không dấu: trọn cụm theo từ đứng đầu
        self.assertEqual(hop.dong_hien()[0], (LOAI_HO, ma[1]))          # (không phải hộ có "Ấp 1" trong địa chỉ)
        hop.o.setText('12/106')                                         # tờ/thửa của hộ thứ 3 (tờ 12, thửa 106)
        self.assertEqual(hop.dong_hien()[0], (LOAI_HO, ma[2]))
        hop.o.setText('tien do chi tra')                                # chức năng theo chữ menu (NHAN_MENU)
        self.assertEqual(hop.dong_hien()[0], (LOAI_LENH, 'Theo dõi tiến độ'))
        hop.o.setText('bang gia dat')
        self.assertIn((LOAI_LENH, 'Bảng giá đất NQ 28…'), hop.dong_hien())
        hop.o.setText('khong co gi nhu the nay')
        self.assertEqual(hop.dong_hien(), [])
        hop.chap_nhan()                                                 # không dòng nào: không chọn
        self.assertIsNone(hop.ket_qua())

    def test_enter_chay_lenh_qua_qaction(self):
        ud, w = self._cua_so()
        hop = w.tim_nhanh(cho=False)
        self.addCleanup(hop.deleteLater)
        hop.o.setText('tien do chi tra')
        hop.chap_nhan()
        self.assertEqual(hop.ket_qua(), ('lenh', 'Theo dõi tiến độ'))
        w.thuc_hien_tim_nhanh(hop.ket_qua())
        self.app.processEvents()
        self.assertEqual(w.trang.currentIndex(), ud.STACK_THEO_DOI)
        # lệnh đang tắt: không chọn được, thuc_hien không chạy
        w.lenh['Kiểm tra lỗi…'].setEnabled(False)
        hop2 = w.tim_nhanh(cho=False)
        self.addCleanup(hop2.deleteLater)
        hop2.o.setText('kiem tra loi phap ly')
        from PySide6.QtCore import Qt
        it = hop2.ds.item(0)
        self.assertEqual(it.data(Qt.ItemDataRole.UserRole), ('lenh', 'Kiểm tra lỗi…'))
        self.assertFalse(it.flags() & Qt.ItemFlag.ItemIsEnabled)
        hop2.chap_nhan()
        self.assertIsNone(hop2.ket_qua())
        da_chay = []
        w.lenh['Kiểm tra lỗi…'].triggered.connect(lambda *_: da_chay.append(1))
        w.thuc_hien_tim_nhanh(('lenh', 'Kiểm tra lỗi…'))
        self.assertEqual(da_chay, [])

    def test_enter_mo_ho_va_bo_loc(self):
        ud, w = self._cua_so()
        ma = [r[0] for r in w.con.execute('SELECT ma_ho FROM ho ORDER BY thu_tu')]
        w.mo_trang(ud.TRANG_THEO_DOI)
        w.o_tim.setText(f'0750920000{ma[0]:02d}')                       # đang lọc (CCCD hộ đầu): ẩn hộ thứ 4
        w.o_tim.phat_ngay()
        self.assertEqual(w.loc.rowCount(), 1)
        idx = w.chon_ho_tren_danh_sach(ma[3])
        self.assertIsNotNone(idx)
        self.assertEqual(w.trang.currentIndex(), ud.STACK_CUA_TRANG[ud.TRANG_DS])
        self.assertEqual(w.ho_dang_chon(), ma[3])
        self.assertEqual(w.loc.rowCount(), 4)                           # đã bỏ lọc
        a = w.thuc_hien_tim_nhanh(('ho', ma[1]))
        self.assertIsNotNone(a)
        self.app.processEvents()
        self.assertIn(('ho', ma[1]), w.khung_tab.khoa)                  # mở hồ sơ / phương án hộ

    def test_chua_mo_du_an_chi_co_lenh(self):
        from pabt import app as ud
        w = ud.CuaSoChinh(menu_trai=True)
        self.w = w
        hop = w.tim_nhanh(cho=False)
        self.addCleanup(hop.deleteLater)
        hop.o.setText('lap phuong an chi tiet')
        self.assertTrue(all(l == 'lenh' for l, _ in hop.dong_hien()))
        self.assertIsNone(w.chon_ho_tren_danh_sach(1))


class TestCanhBaoTucThoi(_CoCuaSo):
    def test_dien_tich_vuot_thu_hoi_khong_chan(self):
        ud, w = self._cua_so(cccd=False)
        from pabt.giao_dien import MAU_CANH_BAO_NEN
        ma = w.con.execute('SELECT ma_ho FROM ho ORDER BY thu_tu LIMIT 1').fetchone()[0]
        cs = w.mo_lap_pa(ma, cho=True)
        self.assertTrue(cs.bo.pa.dat)
        r = 0
        self.assertEqual(cs.bo.canh_bao_dien_tich(r), '')
        c = [k for k, _, _ in cs.bang[1].cot].index('dien_tich')
        cs.sua_o(1, r, 'dien_tich', '9999')                             # vượt DT thu hồi (50 m²): vẫn nhận số
        self.assertEqual(cs.bo.pa.dat[r].dien_tich, 9999)
        cb = cs.bo.canh_bao_dien_tich(r)
        self.assertIn('lớn hơn DT thu hồi', cb)
        it = cs.bang[1].bang.item(r, c)
        self.assertEqual(it.background().color().name().upper(), MAU_CANH_BAO_NEN)
        self.assertIn('DT thu hồi', it.toolTip())
        self.assertIn('Cần xem lại diện tích', cs.lb_tb.text())
        cs.sua_o(1, r, 'dien_tich', '10')                               # về trong hạn: hết nền cảnh báo
        it = cs.bang[1].bang.item(r, c)
        self.assertNotEqual(it.background().color().name().upper(), MAU_CANH_BAO_NEN)
        self.assertEqual(cs.bo.canh_bao_dien_tich(r), '')

    def test_dien_tich_vuot_nguyen_thua(self):
        ud, w = self._cua_so(cccd=False)
        from pabt import csdl
        ma = w.con.execute('SELECT ma_ho FROM ho ORDER BY thu_tu LIMIT 1').fetchone()[0]
        csdl.dam_bao_cot_thua(w.con)
        with w.con:
            w.con.execute("UPDATE thua SET dt_nguyen_thua = '30' WHERE ma_ho = ?", (ma,))
        cs = w.mo_lap_pa(ma, cho=True)
        cs.sua_o(1, 0, 'dien_tich', '40')                               # <= DT thu hồi 50 nhưng > nguyên thửa 30
        self.assertIn('lớn hơn DT nguyên thửa', cs.bo.canh_bao_dien_tich(0))
        self.assertNotIn('DT thu hồi', cs.bo.canh_bao_dien_tich(0))

    def test_ban_giao_nhac_ngay_khi_tich(self):
        from pabt.man_hinh_theo_doi import HopBanGiao
        d = HopBanGiao(None, 1)
        self.addCleanup(d.deleteLater)
        d.show()
        self.app.processEvents()
        self.assertTrue(d.o_da.isChecked())
        self.assertTrue(d.thieu_ngay())
        self.assertTrue(d.lb_nhac_ngay.isVisible())                     # tích sẵn mà chưa có ngày: nhắc ngay
        self.assertIn('Điều 89', d.lb_nhac_ngay.text())
        d.o_ngay.setText('16/10/2026')
        self.assertFalse(d.lb_nhac_ngay.isVisible())
        d.o_ngay.setText('')
        d.o_da.setChecked(False)
        self.assertFalse(d.lb_nhac_ngay.isVisible())                    # bỏ tích: không nhắc
        d.o_da.setChecked(True)
        self.assertTrue(d.lb_nhac_ngay.isVisible())

    def test_ho_so_dt_con_lai_am_mau_ho_phach(self):
        ud, w = self._cua_so(cccd=False)
        from pabt.giao_dien import MAU_CANH_BAO_CHU, MAU_CANH_BAO_NEN
        from PySide6.QtCore import Qt
        ma = w.con.execute('SELECT ma_ho FROM ho ORDER BY thu_tu LIMIT 1').fetchone()[0]
        cs = w.mo_lap_pa(ma, cho=True)
        k = cs.ho_so
        c_ng = k.cot.index('dt_nguyen_thua')
        k.bang.item(0, c_ng).setText('10')                              # DT thu hồi 50 > nguyên thửa 10 -> còn lại âm
        k._cap_nhat_o_tinh()
        it = k.bang.item(0, k.cot.index('dt_con_lai'))
        self.assertEqual(it.foreground().color().name().upper(), MAU_CANH_BAO_CHU)
        self.assertEqual(it.data(Qt.ItemDataRole.BackgroundRole).color().name().upper(), MAU_CANH_BAO_NEN)


class TestPhongSo(_CoCuaSo):
    def test_phong_so_mau_so(self):
        from pabt import giao_dien as g
        from PySide6.QtGui import QFont
        f = g.phong_so(QFont('Segoe UI', 10))
        fam = f.families() if hasattr(f, 'families') else [f.family()]
        self.assertEqual(fam[0], g.PHONG_SO)
        self.assertIn(g.PHONG_SO_DU_PHONG, fam)
        self.assertEqual(f.pointSizeF(), 10)
        self.assertIs(g.phong_so(QFont('Segoe UI', 10)), f)            # nhớ theo phông gốc
        self.assertTrue(g.phong_so(QFont('Segoe UI', 10), dam=True).bold())
        self.assertNotEqual(g.phong_so(QFont('Segoe UI', 12)).pointSizeF(), 10)   # Phóng to: cỡ mới
        self.assertEqual(g.mau_so('0'), g.MAU_SO_KHONG)
        self.assertEqual(g.mau_so('-'), g.MAU_SO_KHONG)
        self.assertEqual(g.mau_so('1.250.000', tien=True), g.MAU_SO_TIEN)
        self.assertIsNone(g.mau_so('1.250.000'))
        self.assertEqual(g.mau_so('5', vuot=True), g.MAU_SO_VUOT)

    def test_cac_bang_dung_phong_so(self):
        ud, w = self._cua_so(cccd=False)
        from PySide6.QtCore import Qt
        from pabt import bang_ao, giao_dien as g
        self.assertIs(bang_ao.MAU_SO_KHONG, g.MAU_SO_KHONG)             # một nguồn hằng
        # danh sách hộ: cột DT thu hồi
        idx = w.mo_hinh.index(0, 4)
        self.assertEqual(w.mo_hinh.data(idx, Qt.ItemDataRole.FontRole).families()[0], g.PHONG_SO)
        # BangAo (bảng tổng hợp tiền): cột số canh phải
        b = bang_ao.BangAo(['Họ tên', 'Tổng (đồng)'], can_phai={1})
        self.addCleanup(b.deleteLater)
        b.dat_du_lieu([['A', '1.000'], ['B', '0']])
        mh = b.model()
        self.assertEqual(mh.data(mh.index(0, 1), Qt.ItemDataRole.FontRole).families()[0], g.PHONG_SO)
        self.assertIsNone(mh.data(mh.index(0, 0), Qt.ItemDataRole.FontRole))
        self.assertEqual(mh.data(mh.index(1, 1), Qt.ItemDataRole.ForegroundRole).color().name().upper(), g.MAU_SO_KHONG)
        # BangMuc + KhungDuToan
        ma = w.con.execute('SELECT ma_ho FROM ho ORDER BY thu_tu LIMIT 1').fetchone()[0]
        cs = w.mo_lap_pa(ma, cho=True)
        bm = cs.bang[1]
        c = [k for k, _, _ in bm.cot].index('thanh_tien')
        it = bm.bang.item(0, c)
        self.assertEqual(it.font().families()[0], g.PHONG_SO)
        self.assertTrue(it.font().bold())
        w.mo_trang(ud.TRANG_DU_TOAN)
        kt = w.khung_du_toan
        kt.them_dong(muc=2) if hasattr(kt, 'them_dong') else None
        if kt.bang.rowCount():
            from pabt.man_hinh_du_toan import COT
            c = [k for k, _, _ in COT].index('thanh_tien')
            self.assertEqual(kt.bang.item(0, c).font().families()[0], g.PHONG_SO)

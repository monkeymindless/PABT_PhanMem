"""Giao diện "Hybrid Enterprise Navy" (người dùng 17/10/2026): nút Thu gọn menu ở hàng riêng (không đè tiêu đề nhóm), thẻ KPI có
tỷ lệ % so với tổng số hộ + đánh dấu thẻ đang lọc, cột Trạng thái có thanh 4 nấc (giá trị lọc giữ nguyên), dải cộng dưới danh sách
hộ cộng bằng Decimal các hộ đang hiện, ô tìm theo CCCD / tờ-thửa, màn hình chào không emoji (số liệu GIẢ LẬP)."""
from __future__ import annotations

import inspect
import unittest

from tests.test_dac_ta_v5 import CoSo
from tests.test_toc_do import _du_an


class TestHamThuan(unittest.TestCase):
    def test_phan_tram(self):
        from pabt.tien import phan_tram
        self.assertEqual(phan_tram(49, 60), '81,7%')
        self.assertEqual(phan_tram(1, 2), '50%')
        self.assertEqual(phan_tram(0, 0), '0%')                        # tổng 0: không chia cho 0
        self.assertEqual(phan_tram(60, 60), '100%')
        self.assertEqual(phan_tram(1, 3), '33,3%')

    def test_cong_dai_cong_decimal(self):
        from decimal import Decimal
        from pabt import app as ud
        dong = [dict(dt=Decimal('0.1'), tong=Decimal('100'), muc={1: Decimal('40'), 2: Decimal('10'), 3: Decimal('5'), 7: Decimal('5'),
                                                                   4: Decimal('30'), 5: Decimal('10')}),
                dict(dt=Decimal('0.2'), tong=Decimal('7'), muc={1: Decimal('7')}),
                dict(dt=None, tong=None, muc={})]
        kq = ud.cong_dai_cong(dong)
        self.assertEqual(kq['dt'], Decimal('0.3'))                      # Decimal: 0,1 + 0,2 đúng 0,3 (float ra 0,30000000000000004)
        self.assertEqual((kq['dat'], kq['tai_san'], kq['ho_tro'], kq['tong']), (47, 20, 40, 107))
        self.assertTrue(all(isinstance(v, Decimal) for k, v in kq.items() if k != 'so_thua'))
        self.assertEqual(kq['so_thua'], 0)                              # dòng không có số thửa
        chu = ud.chu_dai_cong(2, kq)
        self.assertEqual(chu['so_ho'][0], 'CỘNG (2 HỘ · 0 THỬA)')         # 21/10/2026: kèm số thửa, DT quy đổi ha
        self.assertEqual(chu['tong'][0], 'TỔNG CỘNG: 107 đ')
        self.assertEqual(chu['dt'][0], 'Tổng DT: 0,3 m² (0,0000 ha)')
        self.assertIn('–', ud.chu_dai_cong(0, None)['tong'][0])        # chưa có dữ liệu

    def test_thanh_nac_khong_emoji(self):
        from pabt import app as ud
        self.assertEqual(len(ud.THANH_NAC), 5)
        for t in ud.THANH_NAC:
            self.assertEqual(len(t), 4)
            self.assertTrue(set(t) <= {'■', '□'})                       # U+25A0 / U+25A1: có trong Segoe UI / Arial của Windows 7
        nguon = inspect.getsource(ud)
        for e in ('📌', '📍'):                                            # emoji ghim cũ (Windows 7 hiện ô vuông)
            self.assertNotIn(e, nguon)


class CoNavy(CoSo):
    w = None

    def tearDown(self):
        if self.w is not None:
            self.w.close()
            if self.w.con is not None:
                self.w.dong_du_an()
        super().tearDown()

    def _cua_so(self, so_ho=6):
        from pabt import app as ud
        self.w = ud.CuaSoChinh(menu_trai=True)
        self.w.show()
        self.w.mo(str(_du_an(self.td, so_ho)))
        self.app.processEvents()
        return ud, self.w


class TestMenuTrai(CoNavy):
    def test_nut_thu_gon_hang_rieng_khong_de_tieu_de_nhom(self):
        from pabt import giao_dien
        _ud, w = self._cua_so()
        km = w.khung_menu
        self.assertEqual(km.property('vai'), 'menu_trai')
        b = km.nut_thu_gon
        self.assertIs(b.parentWidget(), km.hang_gon)                      # nút nằm trong hàng riêng
        self.assertFalse(km.vung_cuon.isAncestorOf(b))                    # ngoài vùng cuộn chứa các nhóm
        self.assertEqual(km.hang_gon.height(), giao_dien.CAO_HANG_GON)
        lo = km.layout()
        self.assertLess(lo.indexOf(km.hang_gon), lo.indexOf(km.vung_cuon))   # hàng nút ở đỉnh, trên vùng cuộn
        day_hang = km.hang_gon.mapTo(km, km.hang_gon.rect().bottomLeft()).y()
        for ten, t in km.tieu_de_nhom.items():                            # mọi tiêu đề nhóm nằm DƯỚI hàng nút (không chồng lên)
            tren = t.mapTo(km, t.rect().topLeft()).y()
            self.assertGreater(tren, day_hang, ten)
        b.click()                                                         # thu gọn / mở lại: hàng nút vẫn ở chỗ cũ
        self.app.processEvents()
        self.assertTrue(km.thu_gon)
        self.assertEqual(km.width(), giao_dien.RONG_MENU_GON)
        b.click()
        self.assertFalse(km.thu_gon)

    def test_kieu_menu_va_nut_32(self):
        from PySide6.QtWidgets import QToolButton
        from pabt import giao_dien
        _ud, w = self._cua_so()
        nut = [b for b in w.khung_menu.findChildren(QToolButton) if b.property('menu') == '1']
        self.assertTrue(nut)
        for b in nut:
            self.assertEqual((b.minimumHeight(), b.maximumHeight()), (giao_dien.CAO_NUT_MENU, giao_dien.CAO_NUT_MENU))
        qss = giao_dien._qss_day_du()
        # 1.0.35 PA1: menu sáng liền mạch, viên đang chọn nền xanh nhạt + vạch trái 4 px
        for chu in ('QFrame[vai="menu_trai"] { background: #E8EEF5', 'border-right: 1px solid #D5DEE8', 'width: 6px',
                    'border-left: 4px solid #2563EB', 'background: #DBEAFE', 'color: #1E3A5F', 'border-radius: 8px'):
            self.assertIn(chu, qss)


class TestTheSoVaDanhSach(CoNavy):
    def test_the_kpi_ty_le_va_dang_loc(self):
        _ud, w = self._cua_so(6)
        self.assertEqual(w.the_so['so_ho'].text(), '6')
        self.assertEqual(w.the_don_vi['so_ho'].text(), 'hộ')             # 21/10/2026: the_phu = huy hiệu %, đơn vị riêng
        self.assertEqual(w.the_don_vi['tong'].text(), 'VNĐ')
        self.assertEqual(w.the_phu['so_ho'].text(), '100%')
        self.assertTrue(w.the_phu['tong'].text().endswith(' ha'))
        self.assertRegex(w.the_so['tong'].text(), r'^[0-9.,]+ (tỷ|triệu)$')
        self.assertEqual(w.the_phu['da_pd'].text(), '0%')
        ds = [r[0] for r in w.con.execute('SELECT ma_ho FROM ho ORDER BY thu_tu LIMIT 3')]
        from pabt import theo_doi                       # 1.0.02: phê duyệt = hộ có trong quyết định (phân tích tự động)
        theo_doi.them_ho_theo_pa(w.con, theo_doi.luu_qd(w.con, None, '9/QĐ-UBND', '01/10/2026', 'Phê duyệt thử'), ds)
        w.tai_lai()
        self.assertEqual(w.the_so['da_pd'].text(), '3')
        self.assertEqual(w.the_phu['da_pd'].text(), '50%')                # 3 / 6 hộ
        self.assertEqual(w.the_so['da_pd'].toolTip(), '3 / 6 hộ')
        # bấm thẻ: lọc + thẻ đó đánh dấu đang lọc; Số hộ = bỏ lọc, không thẻ nào đánh dấu
        w.bam_the_so('da_pd')
        self.assertEqual(w.loc.rowCount(), 3)
        self.assertEqual(w.the_khung['da_pd'].property('dang_loc'), '1')
        self.assertEqual(w.the_khung['da_ct'].property('dang_loc'), '0')
        w.bam_the_so('so_ho')
        self.assertTrue(all(k.property('dang_loc') == '0' for k in w.the_khung.values()))
        self.assertEqual(w.CAO_THE_SO, 62)
        self.assertEqual(w.the_khung['so_ho'].height(), 62)

    def test_trang_thai_4_nac_giu_gia_tri_loc(self):
        from PySide6.QtCore import Qt
        ud, w = self._cua_so(6)
        m = w.mo_hinh
        goc = [d['o'][5] for d in m.dong]
        for r, d in enumerate(m.dong):
            hien = m.data(m.index(r, 5), Qt.ItemDataRole.DisplayRole)
            self.assertTrue(hien.startswith(ud.THANH_NAC[d['nac']]), hien)
            self.assertTrue(hien.endswith(d['o'][5]))                    # chữ trạng thái gốc vẫn hiện đủ sau thanh
            self.assertEqual(m.data(m.index(r, 5), Qt.ItemDataRole.ForegroundRole).color().name().upper(),
                             ud.MAU_NAC[d['nac']])
        ma = m.dong[0]['ma_ho']
        # 1.0.02: nấc phân tích tự động, tuần tự - cờ tích tay (không quyết định, không biên bản) không làm nấc tăng
        with w.con:
            w.con.execute('UPDATE ho SET da_phe_duyet = 1, da_chi_tra = 1, da_ban_giao = 1 WHERE ma_ho = ?', (ma,))
        w.tai_lai()
        d0 = next(d for d in m.dong if d['ma_ho'] == ma)
        self.assertLess(d0['nac'], 2)
        self.assertIn('đã tích bàn giao', d0['o'][5])
        from pabt import theo_doi
        q = theo_doi.luu_qd(w.con, None, '9/QĐ-UBND', '01/10/2026', 'Phê duyệt thử')
        theo_doi.them_ho_theo_pa(w.con, q, [ma])
        theo_doi.ghi_chi_tra(w.con, [(q, ma)], '05/10/2026', '')
        theo_doi.ghi_ban_giao(w.con, [ma], dict(da_ban_giao=True, ban_giao_ngay='10/10/2026'))   # ngày biên bản
        w.tai_lai()
        d0 = next(d for d in m.dong if d['ma_ho'] == ma)
        self.assertEqual(d0['nac'], 4)
        self.assertTrue(m.data(m.index(m.dong.index(d0), 5), Qt.ItemDataRole.DisplayRole).startswith('■■■■'))
        self.assertNotIn('■', ''.join(d['o'][5] for d in m.dong))       # giá trị lọc / tìm không lẫn ký tự thanh
        self.assertEqual(len(goc), len(m.dong))
        w.cb_tt.setCurrentIndex(w.cb_tt.findData('da_bg'))              # bộ lọc trạng thái như cũ
        self.assertEqual(w.loc.rowCount(), 1)
        w.cb_tt.setCurrentIndex(0)
        w.o_tim.setText('lap phuong an')                                # tìm không dấu theo chữ trạng thái gốc
        w.o_tim.phat_ngay()
        self.assertGreater(w.loc.rowCount(), 0)

    def test_tim_theo_cccd_va_to_thua(self):
        _ud, w = self._cua_so(6)
        ma, to, thua = w.con.execute('SELECT ma_ho, so_to, so_thua FROM thua ORDER BY ma_thua LIMIT 1').fetchone()
        with w.con:
            w.con.execute("UPDATE ho SET so_cccd = '075092001234' WHERE ma_ho = ?", (ma,))
        w.tai_lai()
        w.o_tim.setText('075092001234')
        w.o_tim.phat_ngay()
        self.assertEqual(w.ho_dang_loc(), [ma])
        w.o_tim.setText(f'{to}/{thua}')
        w.o_tim.phat_ngay()
        self.assertEqual(w.ho_dang_loc(), [ma])
        self.assertIn('CCCD', w.o_tim.placeholderText())

    def test_dai_cong_va_huy_hieu_loc(self):
        from pabt.tien import D, vn
        ud, w = self._cua_so(6)
        n = len(w.mo_hinh.dong)
        self.assertTrue(w.dai_cong_ds.isVisibleTo(w))
        self.assertEqual(w.dai_cong_ds.height(), ud.CAO_DAI_CONG_CU)
        t = sum(d['so_thua'] for d in w.mo_hinh.dong)
        self.assertEqual(w.dai_cong_ds.chu['so_ho'][0], f'CỘNG ({n} HỘ · {t} THỬA)')
        tong = sum((d['tong'] for d in w.mo_hinh.dong), D(0))
        self.assertEqual(w.dai_cong_ds.chu['tong'][0], f'TỔNG CỘNG: {vn(tong)} đ')
        self.assertIn(f'<b style="color:#1E3A5F">{n}</b>/{n} hộ', w.lb_loc.text())
        # lọc còn một hộ: dải cộng và huy hiệu theo các hộ đang hiện
        with w.con:
            for i, m in enumerate(r[0] for r in w.con.execute('SELECT ma_ho FROM ho ORDER BY thu_tu LIMIT 2').fetchall()):
                w.con.execute('UPDATE ho SET so_cccd = ? WHERE ma_ho = ?', (f'07509200999{i}', m))
        w.tai_lai()
        w.o_tim.setText('07509200999')
        w.o_tim.phat_ngay()
        k = w.loc.rowCount()
        self.assertEqual(k, 2)
        hien = [d for d in w.mo_hinh.dong if d['ma_ho'] in w.ho_dang_loc()]
        self.assertEqual(w.dai_cong_ds.chu['so_ho'][0], f'CỘNG ({k} HỘ · {sum(d["so_thua"] for d in hien)} THỬA)')
        self.assertEqual(w.dai_cong_ds.chu['tong'][0], f'TỔNG CỘNG: {vn(sum((d["tong"] for d in hien), D(0)))} đ')
        self.assertIn(f'>{k}</b>/{n} hộ', w.lb_loc.text())
        # hẹp: chữ gọn, chú thích vẫn đủ
        w.dai_cong_ds.resize(300, w.dai_cong_ds.height())
        w.dai_cong_ds._chon()
        self.assertTrue(w.dai_cong_ds.gon)
        self.assertEqual(w.o_cong['tong'].toolTip(), w.dai_cong_ds.chu['tong'][0])
        w.dong_du_an()
        self.assertFalse(w.dai_cong_ds.isVisibleTo(w))

    def test_hang_cong_cu_32_va_kieu_nut(self):
        ud, w = self._cua_so(3)
        self.assertEqual(w.nut_ds['Thêm hộ…'].property('bien_the'), 'primary')
        self.assertEqual(w.nut_ds['Xóa hộ…'].property('bien_the'), 'danger')
        self.assertEqual(w.nut_ds['Chọn hộ niêm yết…'].property('bien_the'), 'secondary')
        for o in (w.cb_dot, w.cb_tt, w.o_tim, w.lb_loc):
            self.assertEqual(o.height(), ud.CAO_DAI_CONG_CU)
        self.assertEqual(w.cb_dot.itemText(0), ud.TAT_CA_DOT)
        self.assertEqual(w.cb_tt.itemText(0), ud.TAT_CA_TRANG_THAI)
        from pabt import giao_dien
        qss = giao_dien._qss_day_du()
        self.assertIn('QHeaderView::section:horizontal { background: #1E3A5F; color: #FFFFFF', qss)
        self.assertIn('selection-background-color: #DBEAFE', qss)
        self.assertEqual(giao_dien.CAO_DONG_BANG, 30)
        self.assertEqual(w.bang.verticalHeader().defaultSectionSize(), 30)


class TestManHinhChao(CoNavy):
    def test_the_chao_navy_va_nut_mo(self):
        from pabt import app as ud, giao_dien, thanh_tieu_de
        self.assertEqual(thanh_tieu_de.CAO, 34)
        self.assertEqual(giao_dien.CAO_BANNER, 42)
        for nen, vien, _nr, _vr, _ic in giao_dien.MAU_THE_CHAO.values():
            self.assertEqual((nen, vien), ('#FFFFFF', '#E2E8F0'))
        self.assertIn('QPushButton#nut_mo_gan:hover { background: #1E3A5F; color: #FFFFFF; }', ud.QSS_NUT_MO_GAN)


if __name__ == '__main__':
    unittest.main()

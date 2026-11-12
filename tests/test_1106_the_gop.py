"""1.1.06 - cửa sổ Bảng giá đất: thẻ "Cập nhật, bổ sung giá đất" gộp vào "Bộ quy tắc giá đất" (người dùng 12/11/2026). Cột trái 3 cụm;
khung đọc văn bản là thẻ con đầu; lệnh quy tắc vị trí / bảng giá / hệ số K ở cột trái, nút trùng ở khung cũ ẩn (mỗi lệnh một chỗ);
đọc văn bản xong tạo GÓI NHÁP (dòng đầu danh sách, chưa lưu - không đổi gói đang hiệu lực)."""
from __future__ import annotations

from pathlib import Path

from pabt import goi_gia_dat as gg
from pabt.cap_nhat_gia_dat import so_hieu_va_ngay
from tests import test_goi_gia_dat as _g


class TestSoHieuNgay(_g.CoMay):
    def test_doc_so_hieu_ngay(self):
        kq = so_hieu_va_ngay(['HỘI ĐỒNG NHÂN DÂN', 'Số: 28/2025/NQ-HĐND', 'Đồng Nai, ngày 19 tháng 12 năm 2025',
                              'Điều 3. Nghị quyết này có hiệu lực từ ngày 01 tháng 01 năm 2026.'])
        self.assertEqual(kq, dict(so_hieu='28/2025/NQ-HĐND', ngay='01/01/2026', ngay_tu='hieu_luc'))
        kq = so_hieu_va_ngay([['Quyết định số 03/2026/QĐ-UBND ngày 05/01/2026']])
        self.assertEqual((kq['so_hieu'], kq['ngay'], kq['ngay_tu']), ('03/2026/QĐ-UBND', '05/01/2026', 'ban_hanh'))
        self.assertEqual(so_hieu_va_ngay(['x'], 'Bang gia QD 15/2027/QD-UBND')['so_hieu'], '15/2027/QĐ-UBND')
        self.assertEqual(so_hieu_va_ngay(['không có'])['so_hieu'], '')
        self.assertEqual(gg.chuan_so_hieu('QĐ 03/2026/QĐ-UBND'), gg.chuan_so_hieu('03/2026/QD-UBND'))


class TestTheGop(_g.CoMay):
    @classmethod
    def setUpClass(cls):
        from PySide6.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication([])

    def _hop(self, the=0):
        from pabt.man_hinh_du_toan import HopTraNQ28
        h = HopTraNQ28(None, '', xem=True, the=the)
        h.khung_goi.im_lang = True
        h.khung_cn.im_lang = True
        h.khung_k.im_lang = True
        self.addCleanup(h.deleteLater)
        return h

    def test_ba_the_va_mo_the_cu(self):
        from pabt.man_hinh_du_toan import HopTraNQ28
        h = self._hop(HopTraNQ28.THE_QUY_TAC)
        k = h.khung_goi
        self.assertEqual(h.tabs.count(), 3)
        self.assertEqual(h.tabs.currentIndex(), 2)
        self.assertEqual(k.the.tabText(k.the.currentIndex()), 'Quy tắc')        # số thẻ cũ 3 -> thẻ con Quy tắc
        h.mo_the(HopTraNQ28.THE_CAP_NHAT)
        self.assertIs(k.the.currentWidget(), h.khung_cn)                          # số thẻ cũ 2 -> thẻ con Đọc văn bản
        self.assertFalse(k.b_luu.isVisibleTo(k))                                  # đang ở dữ liệu dùng chung: không có Lưu gói
        k.the.setCurrentIndex(k.the_doc + 1)
        self.assertTrue(k.b_luu.isVisibleTo(k))

    def test_moi_lenh_mot_cho(self):
        h = self._hop(2)
        k = h.khung_goi
        for b in (h.khung_cn.b_them_qt, h.khung_cn.b_xoa_qt, h.khung_cn.b_thay, h.khung_cn.b_khoi_phuc, h.khung_k.b_file, h.khung_k.b_bo):
            self.assertFalse(b.isVisibleTo(h), b.text())
        for ten in ('b_doc', 'b_them_qt', 'b_xoa_qt', 'b_thay_gia', 'b_gia_gan_san', 'b_doc_k', 'b_k_gan_san', 'b_chep', 'b_tu_k',
                    'b_xuat_cai', 'b_nhap_cai', 'b_nhap', 'b_xuat', 'b_xoa'):
            self.assertTrue(getattr(k, ten).isVisibleTo(h), ten)
        n = h.khung_cn.bang_qt.rowCount()
        k.b_them_qt.click()                                                      # nút cột trái chạy đúng hàm của khung
        self.assertEqual(h.khung_cn.bang_qt.rowCount(), n + 1)
        self.assertIs(k.the.currentWidget(), h.khung_cn)
        k.b_k_gan_san.click()
        self.assertEqual(h.tabs.currentIndex(), 1)                                # lệnh hệ số K mở thẻ Hệ số K

    def test_doc_van_ban_tao_goi_nhap(self):
        h = self._hop(2)
        k = h.khung_goi
        so_goi = len(gg.ds_goi())
        p = Path(self.td) / 'gia.csv'
        p.write_text('Nghị quyết số 15/2027/NQ-HĐND\nTên đường,Vị trí,Đất ở\nĐường C,MT,9000000\n', encoding='utf-8')
        h.khung_cn.o_xa.setText('Xã Mới')
        self.assertIsNotNone(h.khung_cn.nap_file(str(p)))
        self.assertIsNotNone(k._nhap)
        self.assertTrue(k.ds.item(0, 0).text().startswith('Nháp - chưa lưu'))
        self.assertTrue(k.moi)
        self.assertEqual(len(gg.ds_goi()), so_goi)                                # chưa lưu: không có gói mới nào trên máy
        self.assertIn('CHƯA LƯU', k.lb_trang_thai.text())
        # rời nháp (im_lang: đồng ý bỏ) -> dòng nháp biến mất
        k.ds.setCurrentCell(1, 0)
        self.assertIsNone(k._nhap)
        self.assertFalse(k.ds.item(0, 0).text().startswith('Nháp'))

    def test_luu_goi_nhap(self):
        h = self._hop(2)
        k = h.khung_goi
        k.tao_goi_nhap({'van_ban': 'Bảng giá thử', 'van_ban_doc': dict(so_hieu='16/2027/QĐ-UBND', ngay='01/02/2027',
                                                                      ngay_tu='hieu_luc')})
        self.assertEqual(k.o_so_hieu.text(), '16/2027/QĐ-UBND')
        self.assertEqual(k.o_tu.text(), '01/02/2027')
        self.assertTrue(k.luu())
        self.assertIsNone(k._nhap)
        self.assertTrue(any(g.get('so_hieu') == '16/2027/QĐ-UBND' for g in gg.ds_goi()))
        # đọc lại văn bản cùng số hiệu: không tạo nháp thứ hai
        self.assertFalse(k.tao_goi_nhap({'van_ban_doc': dict(so_hieu='16/2027/QD-UBND', ngay='', ngay_tu='')}))
        self.assertIsNone(k._nhap)

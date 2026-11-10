"""30/10/2026 (người dùng, ảnh văn bản đơn giá cây trồng mới): cập nhật đơn giá có chế độ THAY THẾ đơn giá cũ - văn bản mới ghi lại quy
cách ("Năm thứ 1" thay "Năm 1", "Năm thu hoạch thứ 1 - 3", mật độ "(330 cây/ha)") dù giá không đổi; đổi tên / mật độ của mục cũ theo
cách ghi của văn bản, mã giữ nguyên. Văn bản thử dựng từ tên / giá trong bộ đơn giá đóng gói (không dùng giá đặt cứng)."""
from __future__ import annotations
import os
import sqlite3
import tempfile
import unittest
from pathlib import Path

from pabt import csdl, don_gia
from pabt import nhap_don_gia as ndg
from PySide6.QtCore import Qt

from tests import APP


def _bo(ten_dau: str, sau: str = ' - %') -> list:
    con = csdl.mo(don_gia.file_goc(), chi_doc=True)
    try:
        return [dict(r) for r in con.execute('SELECT ma, ten, dvt, don_gia, ghi_chu FROM dm_taisan WHERE nhom = 3 AND ten LIKE ? '
                                             'ORDER BY rowid', (ten_dau + sau,))]
    finally:
        con.close()


def _gia(x) -> str:
    return f'{int(float(x["don_gia"])):,}'.replace(',', '.')


class _Co(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self._cu = os.environ.get('PABT_THU_MUC_MAY')
        os.environ['PABT_THU_MUC_MAY'] = str(Path(self.tmp.name) / 'may')
        self.vai, self.man = _bo('Cây vải thiều'), _bo('Cây mận')
        if len(self.vai) < 7 or len(self.man) < 6:
            self.skipTest('bộ đơn giá đóng gói không có đủ mục vải thiều / mận')
        # văn bản mới: vải thiều "(330 cây/ha)", "Năm thứ 1" (bộ cũ "Năm 1"); mận "(roi) (Mật độ 493 cây/ha)", chỉ ghi 3 dòng đầu
        con_vai = ['Năm thứ 1', 'Năm thứ 2', 'Năm thứ 3', 'Năm thu hoạch thứ 1 - 5', 'Năm thu hoạch thứ 6 - 10', 'Năm thu hoạch thứ 11 - 15',
                   'Năm thu hoạch thứ 16 trở đi']
        self.dong = [['STT', 'Tên cây trồng', 'ĐVT', 'Đơn giá (đồng)'], ['8', 'Cây vải thiều (330 cây/ha)', '', '']]
        self.dong += [['', t, 'Cây', _gia(x)] for t, x in zip(con_vai, self.vai)]
        self.dong += [['11', 'Cây mận (roi)\n(Mật độ 493 cây/ha)', '', '']]
        self.dong += [['', t, 'Cây', _gia(x)] for t, x in zip(['Năm thứ 1', 'Năm thứ 2', 'Năm thu hoạch thứ 1 - 3'], self.man)]

    def tearDown(self):
        if self._cu is None:
            os.environ.pop('PABT_THU_MUC_MAY', None)
        else:
            os.environ['PABT_THU_MUC_MAY'] = self._cu
        self.tmp.cleanup()


class TestDocVaKhop(_Co):
    def test_mat_do_tach_khoi_ten(self):
        self.assertEqual(ndg.tach_mat_do_ten('Cây vải thiều (330 cây/ha)'), ('Cây vải thiều', 'Mật độ 330 cây/ha'))
        self.assertEqual(ndg.tach_mat_do_ten('Cây mận (roi) (Mật độ 493 cây/ha)'), ('Cây mận (roi)', 'Mật độ 493 cây/ha'))
        self.assertEqual(ndg.tach_mat_do_ten('Cây cam (Mật độ 1.111 cây/ha)'), ('Cây cam', 'Mật độ 1.111 cây/ha'))
        self.assertEqual(ndg.tach_mat_do_ten('Nhà cấp 4 (tường gạch)'), ('Nhà cấp 4 (tường gạch)', ''))
        ds = ndg.nhan_muc(self.dong, 3)
        self.assertEqual((ds[0].ten, ds[0].ghi_chu), ('Cây vải thiều - Năm thứ 1', 'Mật độ 330 cây/ha'))
        self.assertEqual((ds[-1].ten, ds[-1].ghi_chu), ('Cây mận (roi) - Năm thu hoạch thứ 1 - 3', 'Mật độ 493 cây/ha'))

    def test_khong_them_trung_khi_chi_khac_quy_cach(self):
        # trước 30/10/2026: "Năm thứ 1" của văn bản không khớp "Năm 1" của bộ -> thêm thành mục mới trùng
        ds = ndg.so_khop(ndg.nhan_muc(self.dong, 3), 3)
        self.assertNotIn('mới', {m.trang_thai for m in ds})
        self.assertEqual([m.ma_khop for m in ds[:7]], [x['ma'] for x in self.vai])
        self.assertTrue(all(not m.ten_thay and not m.bo_cu for m in ds))          # không bật thay thế: tên cũ giữ nguyên

    def test_thay_the_doi_ten_giu_ma_va_chu_thich_tuoi(self):
        ds = ndg.so_khop(ndg.nhan_muc(self.dong, 3), 3, thay_the=True)
        v1 = next(m for m in ds if m.ma_khop == self.vai[0]['ma'])
        self.assertEqual((v1.trang_thai, v1.ten_thay), ('đổi quy cách', 'Cây vải thiều - Năm thứ 1'))
        self.assertTrue(v1.ghi_chu_thay.startswith('Mật độ 330 cây/ha'))
        h1 = next(m for m in ds if m.ma_khop == self.vai[3]['ma'])
        # 30/10/2026: văn bản không ghi chú thích "(Năm thứ…)" -> tên theo đúng văn bản (không giữ chú thích của tên cũ)
        self.assertEqual(h1.ten_thay or self.vai[3]['ten'], 'Cây vải thiều - Năm thu hoạch thứ 1 - 5')
        m1 = next(m for m in ds if m.ma_khop == self.man[0]['ma'])
        self.assertEqual(m1.ten_thay, 'Cây mận (roi) - Năm thứ 1')
        self.assertNotIn('roi;', m1.ghi_chu_thay + ';')                            # ghi chú lỗi "roi" của bộ cũ được bỏ
        bo = [m for m in ds if m.bo_cu]
        # thay thế TOÀN BỘ văn bản cũ: mọi mục cây trồng của bộ không có trong văn bản -> "bỏ", chọn sẵn; vật nuôi (cùng nhom 3) không bỏ
        con = csdl.mo(don_gia.file_goc(), chi_doc=True)
        try:
            from pabt.nghiep_vu import la_vat_nuoi
            cay = [r for r in con.execute('SELECT ma, phan_loai FROM dm_taisan WHERE nhom = 3')]
        finally:
            con.close()
        vn = {r['ma'] for r in cay if str(r['ma']).upper().startswith('VN') or la_vat_nuoi(r['phan_loai'])}
        khop = {m.ma_khop for m in ds if not m.bo_cu}
        self.assertEqual({m.ma_khop for m in bo}, {r['ma'] for r in cay} - vn - khop)
        self.assertTrue(all(m.trang_thai == 'bỏ' and m.chon for m in bo))
        self.assertIn(self.man[3]['ma'], {m.ma_khop for m in bo})                     # mận văn bản chỉ ghi 3 dòng
        self.assertEqual(ndg.pham_vi_thay_the(ds, 3), [3])
        ndg.so_khop(ds, 3, thay_the=True)                                           # so lại: không nhân đôi dòng "bỏ"
        self.assertEqual(sum(m.bo_cu for m in ds), len(bo))
        ndg.so_khop(ds, 3)
        self.assertFalse(any(m.bo_cu for m in ds))

    def test_ap_dung_thay_the_toan_bo(self):
        ds = ndg.so_khop(ndg.nhan_muc(self.dong, 3), 3, thay_the=True)
        bo = [m for m in ds if m.bo_cu]
        bo[1].chon = False                                                          # người dùng giữ lại một mục cũ
        vb_cu = [i for i, sh, _ in ndg.van_ban_cu_cua_nhom({3}) if '48/2025' in sh]
        self.assertTrue(vb_cu)                                                      # QĐ 48/2025 cây trồng của bộ đóng gói
        tt = ndg.ap_dung(ds, 3, 'van_ban_moi.pdf', van_ban={'so_hieu': '99/2026/QĐ-UBND', 'loai_vb': 'Quyết định'},
                         van_ban_cu=vb_cu)
        self.assertEqual(tt['so_moi'], 0)
        self.assertEqual(tt['so_bo'], len(bo) - 1)
        self.assertGreaterEqual(tt['so_quy_cach'], 6)        # 1.0.37: bộ đóng gói đã chuẩn tên theo văn bản (một mục khỏi đổi)
        c = sqlite3.connect(don_gia.file_dang_dung())
        try:
            ten, gc, gia = c.execute('SELECT ten, ghi_chu, don_gia FROM dm_taisan WHERE ma = ?', (self.vai[0]['ma'],)).fetchone()
            self.assertEqual(ten, 'Cây vải thiều - Năm thứ 1')
            self.assertEqual(gc, 'Mật độ 330 cây/ha')                               # ghi chú "Sửa đổi… QĐ 66/2025" của văn bản cũ bỏ
            self.assertEqual(int(float(gia)), int(float(self.vai[0]['don_gia'])))
            self.assertIsNone(c.execute('SELECT 1 FROM dm_taisan WHERE ma = ?', (bo[0].ma_khop,)).fetchone())
            self.assertIsNotNone(c.execute('SELECT 1 FROM dm_taisan WHERE ma = ?', (bo[1].ma_khop,)).fetchone())  # không chọn: giữ
            self.assertGreater(c.execute("SELECT COUNT(*) FROM dm_taisan WHERE ma LIKE 'VN%'").fetchone()[0], 0)  # vật nuôi còn
            self.assertTrue(c.execute('SELECT trang_thai FROM van_ban WHERE id = ?', (vb_cu[0],)).fetchone()[0]
                            .startswith('Hết hiệu lực - thay thế bởi Quyết định 99/2026/QĐ-UBND'))
        finally:
            c.close()
        # lần sau: đã theo văn bản mới - không còn gì để thay
        ds = ndg.so_khop(ndg.nhan_muc(self.dong, 3), 3, thay_the=True)
        self.assertEqual({m.trang_thai for m in ds if not m.bo_cu}, {'giữ nguyên'})


class TestLamNghiepTheoNhom(_Co):
    """Phụ lục IV: bảng giá theo NHÓM loài x cỡ đường kính; Phụ lục VI: danh sách loài của nhóm -> tách từng loài, cấp mã mục mới."""
    def setUp(self):
        super().setUp()
        self.bd = _bo('Bồ đề', ' (d%')
        if len(self.bd) < 10:
            self.skipTest('bộ đơn giá đóng gói không có cây Bồ đề theo đường kính')
        dk = [x['ten'][x['ten'].index('(d') + 2:].replace('cm)', '').strip().replace('<', '≤') for x in self.bd]
        self.gia = [['I', 'Nhóm loài cây gỗ trồng trên cạn (mật độ chuẩn 833 cây/ha)', 'Đường kính thân cây (cm)',
                     'Đơn giá bồi thường (đồng/cây)']]
        for i, (d, x) in enumerate(zip(dk, self.bd)):                 # ô nhóm gộp nhiều hàng: chỉ hàng đầu có chữ
            self.gia.append(['6' if i == 0 else '', 'Nhóm VI gồm 2 loài (danh sách tên loài theo Phụ lục VI kèm theo)' if i == 0 else '',
                             d, _gia(x)])
        self.loai = [['Bảng 7: Loài cây nhóm VI'], ['TT', 'Tên Việt Nam', 'Tên Việt Nam khác', 'Tên khoa học'],
                     ['1', 'Bồ đề', '', 'Styrax tonkinensis'], ['2', 'Cây thử nghiệm', 'Thử khác. Thử hai', 'Species nova']]

    def test_doc_bang_nhom_va_danh_sach_loai(self):
        self.assertEqual(ndg.chuan_duong_kinh('≤3'), '(d ≤3 cm)')
        self.assertEqual(ndg.chuan_duong_kinh('> 3 - 6'), '(d >3-6 cm)')
        self.assertEqual(ndg.chuan_duong_kinh('>42'), '(d >42 cm)')
        self.assertEqual([ndg.khoa_nhom_loai(x) for x in ('Nhóm quý hiếm gồm 45 loài', 'Bảng 4: Loài cây nhóm III', 'nhóm 4',
                                                           'Nhóm I gồm 13 loài')], ['quy hiem', '3', '4', '1'])
        ds = ndg.nhan_muc(self.gia, 3)
        self.assertEqual(len(ds), len(self.bd))
        self.assertEqual((ds[0].ten, ds[0].nhom_loai, ds[0].ghi_chu, ds[0].dvt),
                         ('Nhóm VI gồm 2 loài (d ≤3 cm)', '6', 'Mật độ 833 cây/ha', 'cây'))
        self.assertEqual(ndg.doc_nhom_loai(self.loai), {'6': [('Bồ đề', ()), ('Cây thử nghiệm', ('Thử khác', 'Thử hai'))]})

    def test_tach_tung_loai_va_cap_ma(self):
        dong = self.gia + self.loai
        ds, khong = ndg.tach_theo_loai(ndg.nhan_muc(dong, 3), ndg.doc_nhom_loai(dong))
        self.assertEqual(khong, [])
        self.assertEqual(len(ds), 2 * len(self.bd))
        self.assertEqual([m.ten for m in ds[:2]], ['Bồ đề (d ≤3 cm)', 'Bồ đề (d >3-6 cm)'])          # từng loài đủ các cỡ
        self.assertEqual(ds[len(self.bd)].ten, 'Cây thử nghiệm (Thử khác, Thử hai) (d ≤3 cm)')
        ndg.so_khop(ds, 3)
        self.assertEqual([m.ma_khop for m in ds[:len(self.bd)]], [x['ma'] for x in self.bd])
        moi = ds[len(self.bd):]
        self.assertTrue(all(m.trang_thai == 'mới' for m in moi))
        so = [int(m.ma_moi[2:]) for m in moi]
        self.assertTrue(all(m.ma_moi.startswith('CT') for m in moi))
        self.assertEqual(so, list(range(so[0], so[0] + len(moi))))                                  # mã liên tiếp
        tt = ndg.ap_dung(ds, 3, 'van_ban_moi.pdf')
        self.assertEqual(tt['so_moi'], len(moi))
        c = sqlite3.connect(don_gia.file_dang_dung())
        try:
            self.assertEqual(c.execute('SELECT ten FROM dm_taisan WHERE ma = ?', (moi[0].ma_moi,)).fetchone()[0], moi[0].ten)
        finally:
            c.close()

    def test_khong_co_danh_sach_thi_suy_theo_bo_don_gia(self):
        ds, khong = ndg.tach_theo_loai(ndg.nhan_muc(self.gia, 3), {})
        self.assertEqual(khong, [])
        loai = {m.ten_loai for m in ds}
        self.assertIn('Bồ đề', loai)                                                 # các loài cùng bảng giá nhóm trong bộ
        self.assertTrue(all(m.duong_kinh for m in ds))
        # giá khác bộ đơn giá và không có danh sách loài: giữ dòng theo nhóm, báo không tách được
        g = [list(r) for r in self.gia]
        g[1][3] = '1'
        ds, khong = ndg.tach_theo_loai(ndg.nhan_muc(g, 3), {})
        self.assertEqual(len(khong), 1)
        self.assertTrue(ds[0].ten.startswith('Nhóm VI'))


@unittest.skipUnless(APP is not None, 'không có Qt')
class TestHop(_Co):
    def test_hop_thay_the_toan_bo(self):
        from pabt.man_hinh_nhap_don_gia import COT, HopNhapDonGia
        h = HopNhapDonGia(None, dong=self.dong, nguon='van_ban_moi.pdf', van_ban={}, nhom_uu_tien=3)
        h.im_lang = True
        try:
            self.assertFalse(h.thay_the())
            self.assertTrue(h.cb_vb_cu.isHidden())
            n = h.bang.rowCount()
            h.o_cach.setCurrentIndex(1)
            self.assertTrue(h.thay_the())
            self.assertFalse(h.cb_vb_cu.isHidden())
            self.assertIn('48/2025', h.cb_vb_cu.currentText())                     # một văn bản cây trồng: chọn sẵn
            self.assertGreater(h.bang.rowCount(), n)                                # thêm dòng mục cũ "bỏ"
            self.assertFalse(h.lb_canh_thay.isHidden())
            self.assertIn('kiểm tra văn bản đã đọc ĐỦ', h.lb_canh_thay.text())     # văn bản thử ít mục, bỏ rất nhiều
            self.assertEqual(h.bang.columnCount(), len(COT))
            r = next(i for i, m in enumerate(h.ds) if m.ma_khop == self.vai[0]['ma'])
            from pabt.man_hinh_nhap_don_gia import C_TEN, C_TEN_CU
            self.assertEqual(h.bang.item(r, C_TEN).text(), 'Cây vải thiều - Năm thứ 1')
            self.assertEqual(h.bang.item(r, C_TEN_CU).text(), self.vai[0]['ten'])
            self.assertIn('đổi tên / quy cách', h.lb.text())
            h.accept()
            self.assertIsNotNone(h.ket_qua)
            self.assertGreater(h.ket_qua['so_bo'], 0)
        finally:
            h.close()
            h.deleteLater()

    def test_chon_tat_ca_tim_dem(self):
        """1.0.61: nút Chọn tất cả / menu / tiêu đề cột Dùng, ô tìm, bộ đếm; lưu ý nằm trong khung kèm theo."""
        from pabt.man_hinh_nhap_don_gia import C_DUNG, HopNhapDonGia
        import pabt.nhap_don_gia as ndg2
        h = HopNhapDonGia(None, dong=self.dong, nguon='van_ban_moi.pdf', van_ban={}, nhom_uu_tien=3)
        h.im_lang = True
        try:
            h.o_cach.setCurrentIndex(1)
            ghi = [i for i, m in enumerate(h.ds) if m.trang_thai in ndg2.TRANG_THAI_GHI]
            self.assertTrue(ghi)
            h.chon_theo(False)
            self.assertTrue(all(h.bang.item(i, C_DUNG).checkState() != Qt.CheckState.Checked for i in range(len(h.ds))))
            self.assertEqual(h.chon_theo(True), len(ghi))
            h._dem_chon()
            self.assertIn(f'Đã chọn {len(ghi)} / {len(ghi)}', h.lb_dem.text())
            h._bam_dau_cot(C_DUNG)                                                  # tiêu đề cột: đã chọn hết -> bỏ chọn
            self.assertEqual(sum(h.bang.item(i, C_DUNG).checkState() == Qt.CheckState.Checked for i in ghi), 0)
            h.o_cach.setCurrentIndex(0)
            self.assertGreater(h.thay_toan_bo() + 1, 0)                             # chọn "thay cả nhóm" + chọn mọi dòng thay đổi
            self.assertTrue(h.thay_the())
            h.o_tim.setText('zzzkhongco')
            self.assertTrue(all(h.bang.isRowHidden(i) for i in range(len(h.ds))))
            h.o_tim.setText('')
            self.assertFalse(h.b_phu.isChecked())                                   # khung lưu ý đóng sẵn khi không có cảnh báo nặng
        finally:
            h.close()
            h.deleteLater()


if __name__ == '__main__':
    unittest.main()

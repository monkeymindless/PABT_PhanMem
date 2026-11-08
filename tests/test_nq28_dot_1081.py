"""1.0.81: đồng bộ dòng đất theo thửa (lỗi FOREIGN KEY khi xóa / sửa thửa), 4 loại đất nông nghiệp NQ 28, đọc toàn văn NQ 28,
giá đất tái định cư và trường hợp cụ thể Điều 8-10."""
from __future__ import annotations
import unittest

from pabt import ho_so
from pabt.lap_pa import BoSoan
from pabt.tien import D
from tests.test_ho_so import CoSo


class TestDongBoThua(CoSo):
    def test_xoa_them_thua_khi_dang_soan(self):
        bo = BoSoan(self.con, 1)
        bo.pa.dat.clear()
        bo.them_nhieu_thua()
        self.assertEqual(len(bo.pa.dat), 2)
        ho = ho_so.doc_ho(self.con, 1)
        t1, t2 = ho['thua']
        # xóa thửa 2, thêm thửa mới - cửa sổ còn giữ dòng gắn thửa 2
        ho_so.luu_ho(self.con, 1, ho, [dict(t1), dict(so_to='40', so_thua='9', loai_dat='RPH', dt_thu_hoi='10')])
        kq = bo.dong_bo_dat_theo_thua_csdl()
        self.assertEqual((kq['bo_gan'], kq['them']), (1, 1))
        con_thua = {r[0] for r in self.con.execute('SELECT ma_thua FROM thua WHERE ma_ho = 1')}
        self.assertTrue(all(d.ma_thua is None or d.ma_thua in con_thua for d in bo.pa.dat))
        self.assertEqual(bo.pa.dat[-1].loai_dat, 'RPH')
        bo.luu()                                           # không còn FOREIGN KEY constraint failed

    def test_luu_luoi_an_toan(self):
        bo = BoSoan(self.con, 1)
        bo.pa.dat.clear()
        bo.them_nhieu_thua()
        ho = ho_so.doc_ho(self.con, 1)
        ho_so.luu_ho(self.con, 1, ho, [dict(ho['thua'][0])])     # thửa 2 bị xóa ở nơi khác, không gọi đồng bộ
        bo.luu()
        con_thua = {r[0] for r in self.con.execute('SELECT ma_thua FROM thua WHERE ma_ho = 1')}
        ds = [r[0] for r in self.con.execute('SELECT ma_thua FROM ct_dat WHERE ma_ho = 1')]
        self.assertEqual(len(ds), 2)
        self.assertTrue(all(x is None or x in con_thua for x in ds))


class TestBonLoaiDatNN(unittest.TestCase):
    def test_ma_dat(self):
        from pabt import gia_dat_nq28 as nq
        self.assertEqual([nq.loai_nn_cua_ma(x) for x in ('CLN', 'LUC', 'NTS', 'RPH', 'RDD', 'ONT')],
                         ['nn_cln', 'nn_chn', 'nn_nts', 'nn_rsx', 'nn_rsx', None])
        self.assertEqual((nq.cot_cua_loai('RPH'), nq.cot_cua_loai('CNT')), ('nn_rung_nts', 'nn_cay'))

    def test_cot_du_phong(self):
        from pabt import gia_dat_nq28 as nq
        r = next(r for r in nq.tat_ca() if r.get('nn_cay') and r.get('nn_rung_nts'))
        self.assertEqual(nq.gia_dong(r, 'nn_cln'), nq.gia_dong(r, 'nn_cay'))
        self.assertEqual(nq.gia_dong(r, 'nn_rsx'), nq.gia_dong(r, 'nn_rung_nts'))
        self.assertEqual(nq.gia_dong(dict(r, nn_nts=7), 'nn_nts'), 7000)      # bảng có cột riêng: dùng cột riêng
        ds = nq.phan_tich_4_loai_nn(r)
        self.assertEqual([x['ma'] for x in ds], ['nn_cln', 'nn_chn', 'nn_nts', 'nn_rsx'])

    def test_rung_san_xuat_khong_phai_sxkd(self):
        from pabt.cap_nhat_gia_dat import _loai_gia
        self.assertEqual(_loai_gia('Đất rừng sản xuất'), 'nn_rung_nts')
        self.assertEqual(_loai_gia('Đất sản xuất, kinh doanh phi nông nghiệp'), 'sxkd')
        self.assertEqual(_loai_gia('Đất nuôi trồng thủy sản'), 'nn_rung_nts')


TOAN_VAN = """HỘI ĐỒNG NHÂN DÂN TỈNH ĐỒNG NAI
NGHỊ QUYẾT
Quy định bảng giá đất trên địa bàn tỉnh Đồng Nai
Điều 1. Phạm vi điều chỉnh
1. Nghị quyết này quy định bảng giá đất.
Điều 2. Đối tượng áp dụng
1. Cơ quan nhà nước.
Điều 5. Đất nông nghiệp
1. Phạm vi 1 tính 100%; phạm vi 2 tính 80%; phạm vi 3 tính 60% giá đất.
2. Vị trí 2 bằng 30% giá đất vị trí 1.
Điều 6. Đất tái định cư
7. Đất thương mại, dịch vụ trong khu tái định cư bằng 70% giá đất ở tái định cư.
Điều 8. Trường hợp cụ thể
3. Thửa đất có từ 2 mặt tiền trong phạm vi 50 m nhân hệ số 1,20.
Điều 9. Giáp ranh
1. Chênh lệch trên 30%.
Điều 10. Đất có thời hạn
1. Quy đổi theo 70 năm.
"""


def _docx_doan(f, dong):
    import zipfile
    W = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'
    than = ''.join(f'<w:p><w:r><w:t xml:space="preserve">{x}</w:t></w:r></w:p>' for x in dong)
    with zipfile.ZipFile(f, 'w') as z:
        z.writestr('[Content_Types].xml', '<?xml version="1.0"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
                   '<Default Extension="xml" ContentType="application/xml"/></Types>')
        z.writestr('word/document.xml', f'<?xml version="1.0" encoding="UTF-8"?><w:document xmlns:w="{W}"><w:body>{than}</w:body>'
                   '</w:document>')


class TestToanVan(unittest.TestCase):
    def test_nhan_va_doc(self):
        from pabt.quy_tac_vi_tri import doc_quy_tac, doc_toan_van_nghi_quyet, la_van_ban_toan_van_nq28
        self.assertTrue(la_van_ban_toan_van_nq28(TOAN_VAN))
        self.assertFalse(la_van_ban_toan_van_nq28('Tên đường | Đất ở\nQuốc lộ 1 | 5.000'))
        kq = doc_toan_van_nghi_quyet(TOAN_VAN)
        self.assertEqual([d['so'] for d in kq['dieu']], [1, 2, 5, 6, 8, 9, 10])
        self.assertTrue(any(q['dieu'] == 8 and '1.20' in q['he_so'] for q in kq['quy_tac']))
        self.assertTrue(any(q['dieu'] == 5 and '80' in q['ty_le'] for q in kq['quy_tac']))
        self.assertTrue(any(q.vi_tri == 2 for q in doc_quy_tac(TOAN_VAN)))

    def test_doc_file_khong_loi(self):
        import os
        import tempfile
        from pathlib import Path
        from pabt import gia_dat_nq28
        cu = os.environ.get('PABT_THU_MUC_MAY')
        with tempfile.TemporaryDirectory() as td:
            os.environ['PABT_THU_MUC_MAY'] = td
            gia_dat_nq28._quen()
            try:
                f = Path(td) / 'NQ28_toan_van.docx'
                _docx_doan(f, TOAN_VAN.splitlines())
                from pabt.cap_nhat_gia_dat import doc_file_day_du
                kq = doc_file_day_du(f, 'Đồng Nai', 'Trị An')
                self.assertTrue(kq['toan_van'] and kq['toan_van']['quy_tac'])
                self.assertTrue(kq['dong_goc'])
                self.assertTrue((Path(td) / 'quy_tac_toan_van_nq28.json').is_file())
            finally:
                if cu is None:
                    os.environ.pop('PABT_THU_MUC_MAY', None)
                else:
                    os.environ['PABT_THU_MUC_MAY'] = cu
                gia_dat_nq28._quen()


class _MayTrong(unittest.TestCase):
    def setUp(self):
        import os
        import tempfile
        self._td = tempfile.TemporaryDirectory()
        self._cu = os.environ.get('PABT_THU_MUC_MAY')
        os.environ['PABT_THU_MUC_MAY'] = self._td.name

    def tearDown(self):
        import os
        if self._cu is None:
            os.environ.pop('PABT_THU_MUC_MAY', None)
        else:
            os.environ['PABT_THU_MUC_MAY'] = self._cu
        self._td.cleanup()


class TestGiaTdc(_MayTrong):
    def tinh(self, *a, **k):
        from pabt.quy_tac_vi_tri import tinh_gia_tai_dinh_cu_va_truong_hop_cu_the
        return tinh_gia_tai_dinh_cu_va_truong_hop_cu_the(*a, **k)

    def test_cac_truong_hop(self):
        self.assertEqual(self.tinh('tdc_noi_bo', '3.000.000')['gia'], D(1500000))
        self.assertEqual(self.tinh('tdc_gan_duong', '3000000', khoang_cach_m='800', do_thi=True)['gia'], D(1200000))
        self.assertEqual(self.tinh('tdc_gan_duong', '3000000', khoang_cach_m='800', do_thi=False)['gia'], D(1500000))
        self.assertEqual(self.tinh('tdc_tmdv', '3000000')['gia'], D(2100000))
        self.assertEqual(self.tinh('tdc_sxkd', '3000000')['gia'], D(1800000))
        self.assertEqual(self.tinh('chenh_lech_suat_tdc', dt_suat='60', gia_tdc='2500000', tien_bt_dat_o='100000000')['gia'],
                         D(50000000))
        self.assertEqual(self.tinh('chenh_lech_suat_tdc', dt_suat='60', gia_tdc='1000', tien_bt_dat_o='100000000')['gia'], D(0))
        self.assertEqual(self.tinh('pham_vi_nn_PV2', '333333')['gia'], D(266666))
        self.assertEqual(self.tinh('pham_vi_nn_VT2', '300000', san='120000')['gia'], D(120000))
        self.assertEqual(self.tinh('pham_vi_pnn_VT2-PV1', '1000000')['gia'], D(150000))
        self.assertEqual(self.tinh('mat_tien_2_pl_vii', '1000000')['gia'], D(1200000))
        self.assertEqual(self.tinh('mat_tien_1_pl_vii', '1000000')['gia'], D(1100000))
        self.assertEqual(self.tinh('dang_tuyen', '1000000')['gia'], D(200000))
        self.assertEqual(self.tinh('kenh_rach_pl_vii', '1000000')['gia'], D(400000))
        self.assertEqual(self.tinh('kenh_rach_khac', '1000000')['gia'], D(500000))
        self.assertEqual(self.tinh('nga_ba', gia_cac_duong=['1000000', '1500000'])['gia'], D(1500000))
        self.assertEqual(self.tinh('giap_ranh', '1000000', gia_tinh_ban='2000000')['gia'], D(1400000))
        self.assertEqual(self.tinh('giap_ranh', '1000000', gia_tinh_ban='1200000')['gia'], D(1000000))
        self.assertEqual(self.tinh('thoi_han', '7000000', so_nam='50')['gia'], D(5000000))
        self.assertEqual(self.tinh('kcn_moi', '1000005')['gia'], D(900005))      # 900004,5 -> ROUND_HALF_UP

    def test_loi(self):
        from pabt.quy_tac_vi_tri import LoiQuyTac, cac_truong_hop
        with self.assertRaises(LoiQuyTac):
            self.tinh('khong_co', '1000')
        with self.assertRaises(LoiQuyTac):
            self.tinh('tdc_noi_bo', 'abc')
        self.assertGreaterEqual(len(cac_truong_hop()), 25)


try:
    import PySide6  # noqa: F401
    CO_QT = True
except ImportError:
    CO_QT = False


@unittest.skipUnless(CO_QT, 'cần PySide6')
class TestManHinh(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from PySide6.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication([])

    def test_hop(self):
        from pabt.man_hinh_gia_dat import KhungCapNhatGiaDat
        k = KhungCapNhatGiaDat(None, 'Trị An')
        k.im_lang = True
        h = k.phan_tich_4_loai(hien=False)
        self.assertEqual(h.bang.rowCount(), 4)
        h.bang.item(0, 4).setText('60')
        self.assertTrue(h.bang.item(0, 5).text())
        t = k.tinh_tdc(hien=False)
        t.o_gia.setText('3.000.000')
        t.cb.setCurrentIndex(t.cb.findData('tdc_noi_bo'))
        self.assertEqual(t.tinh()['gia'], D(1500000))
        for w in (h, t, k):
            w.deleteLater()


class TestHeSoToanVan(_MayTrong):
    def test_toan_van_thay_he_so_goi(self):
        from pabt.quy_tac_vi_tri import doc_toan_van_nghi_quyet, quy_tac_nq28, tinh_gia_tai_dinh_cu_va_truong_hop_cu_the as tinh
        self.assertEqual(tinh('dang_tuyen', '1000000')['gia'], D(200000))
        vb = TOAN_VAN + 'Điều 8. Trường hợp cụ thể\n8. Đất dạng tuyến tính bằng hệ số 0,25 giá đất.\n'
        doc_toan_van_nghi_quyet(vb.replace('Điều 8. Trường hợp cụ thể\n3.', 'Điều 7. Khác\n3.'), luu=True)
        kq = tinh('dang_tuyen', '1000000')
        self.assertEqual(kq['gia'], D(250000))
        self.assertIn('toàn văn', kq['nguon'])
        self.assertEqual(quy_tac_nq28()['truong_hop'][3]['he_so'], '0.25')
        from pabt.goi_gia_dat import du_lieu_goc
        self.assertEqual(du_lieu_goc()['quy_tac_nq28']['truong_hop'][3]['he_so'], '0.2')      # dữ liệu gói dùng chung không bị sửa


@unittest.skipUnless(CO_QT, 'cần PySide6')
class TestBangTinh(_MayTrong):
    @classmethod
    def setUpClass(cls):
        from PySide6.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication([])

    def _hop(self):
        from pabt.man_hinh_tinh_gia_dat import HopTinhGiaDat
        h = HopTinhGiaDat(None, None, [], 'Phú Lý', False)
        h.im_lang = True
        self.addCleanup(h.deleteLater)
        return h

    def test_4_loai_dat_nn(self):
        h = self._hop()
        ds = [h.cb_nhom.itemData(i) for i in range(h.cb_nhom.count())]
        for x in ('DAT_NONG_NGHIEP|nn_cay|cln', 'DAT_NONG_NGHIEP|nn_cay|hang_nam', 'DAT_NONG_NGHIEP|nn_rung_nts|nts',
                  'DAT_NONG_NGHIEP|nn_rung_nts|rung', 'DAT_O|dat_o'):
            self.assertIn(x, ds)
        h.cb_nhom.setCurrentIndex(h.cb_nhom.findData('DAT_NONG_NGHIEP|nn_rung_nts|rung'))
        self.assertEqual(h.nhom_cot(), ('DAT_NONG_NGHIEP', 'nn_rung_nts'))
        self.assertEqual(h.dau_vao().loai_nn, 'rung')
        self.assertFalse(h.cb_loai_nn.isVisible())
        self.assertEqual(h.cb_nhom.itemData(h.tim_nhom('DAT_NONG_NGHIEP', 'nn_rung_nts', 'RPH')), 'DAT_NONG_NGHIEP|nn_rung_nts|rung')
        self.assertEqual(h.cb_nhom.itemData(h.tim_nhom('DAT_NONG_NGHIEP', 'nn_cay', 'LUC')), 'DAT_NONG_NGHIEP|nn_cay|hang_nam')

    def test_truong_hop_nq28_va_dong_bo(self):
        h = self._hop()
        h.cb_nhom.setCurrentIndex(h.cb_nhom.findData('DAT_O|dat_o'))
        h.o_g.setText('1.000.000')
        goc = h.tinh().don_gia_ap_dung
        h.cb_th.setCurrentIndex(h.cb_th.findData('kcn_moi'))
        self.assertEqual(h.dau_vao().don_gia_bang_gia, D(900000))
        self.assertIn('Khoản 6 Điều 8', h.lb_ct.text())
        self.assertLess(h.kq.don_gia_ap_dung, goc)
        h.cb_th.setCurrentIndex(h.cb_th.findData('thoi_han'))
        self.assertTrue(h.o_th.isVisibleTo(h))
        h.o_th.setText('35')
        self.assertEqual(h.dau_vao().don_gia_bang_gia, D(500000))
        # nạp toàn văn ở nơi khác -> bảng tính đang mở đổi theo (KCN 0,90 -> 0,85)
        h.cb_th.setCurrentIndex(h.cb_th.findData('kcn_moi'))
        from pabt.quy_tac_vi_tri import doc_toan_van_nghi_quyet
        vb = TOAN_VAN.replace('3. Thửa đất có từ 2 mặt tiền trong phạm vi 50 m nhân hệ số 1,20.',
                              '6. Đất trong khu công nghiệp mới tính bằng hệ số 0,85.')
        doc_toan_van_nghi_quyet(vb, luu=True)
        self.assertEqual(h.cb_th.currentData(), 'kcn_moi')
        g = D(h.o_g.text().replace('.', ''))                 # làm mới tra lại giá theo bảng giá đang dùng
        self.assertEqual(h.dau_vao().don_gia_bang_gia, (g * D('0.85')).quantize(D(1)))
        self.assertIn('toàn văn', h.lb_ct.text())


if __name__ == '__main__':
    unittest.main()

"""1.0.58 (Gói 3 đề án LARC V2.0, phần không trái quyết định cũ của người dùng): Gọn cột, khung chi tiết dòng (Space), ghim danh sách hộ
(Ctrl+B), đối chiếu hai hộ chỉ đọc. Không làm: thanh 5 bước, nhiều tab soạn (thanh tab bỏ từ 0.9.94); F4 vẫn là xem trước A4. Dự án GIẢ LẬP."""
from __future__ import annotations

import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from pabt import csdl, nhap_tai_san, so_sanh_ho
from pabt.lap_pa import BoSoan, DanhMuc
from pabt.tien import D
from tests.test_toc_do import _du_an

try:
    from tests import APP
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QMessageBox, QPushButton
    CO_QT = APP is not None
except ImportError:
    CO_QT = False


class _Nen(unittest.TestCase):
    def setUp(self):
        self.td = Path(tempfile.mkdtemp(prefix='pabt_g3_'))
        self.p = _du_an(self.td, 4)
        self.con = csdl.mo(self.p)
        self.ma = [r[0] for r in self.con.execute('SELECT ma_ho FROM ho ORDER BY thu_tu')]

    def tearDown(self):
        self.con.close()
        shutil.rmtree(self.td, ignore_errors=True)

    def lap(self, i: int, dong: list) -> BoSoan:
        """dong: [(mục danh mục, số lượng, đơn giá nhập tay hoặc None)] - lưu phương án hộ thứ i."""
        bo = BoSoan(self.con, self.ma[i], DanhMuc(self.con))
        for m, sl, gia in dong:
            nhap_tai_san.them_mot(nhap_tai_san.DichPhuongAn(bo), 2, m, so_luong=str(sl))
            if gia is not None:
                bo.pa.khoan[2][-1].don_gia = D(gia)
                bo.pa.khoan[2][-1].nguon_gia = 'Nhập tay'
                bo.pa.khoan[2][-1].ma = ''
        bo.luu()
        return bo

    def muc(self, n: int = 3) -> list:
        return [x for x in DanhMuc(self.con).muc[2] if x.don_gia][:n]


class TestSoSanh(_Nen):
    def test_khac_gia_chi_mot_ho_trung_ten_va_tong(self):
        a, b, c = self.muc(3)
        self.lap(0, [(a, 2, None), (b, 1, None), (b, 5, None)])     # b ghi hai lần
        self.lap(1, [(a, 2, a.don_gia + 1000), (b, 1, None), (c, 4, None)])
        kq = so_sanh_ho.so_sanh(self.con, self.ma[0], self.ma[1])
        khoan = [d for d in kq['dong'] if d['muc'] == 2]
        theo = {}
        for d in khoan:
            theo.setdefault(d['ten'], []).append(d)
        self.assertTrue(theo[a.ten][0]['khac_gia'])                 # cùng tài sản, khác đơn giá
        self.assertFalse(theo[a.ten][0]['khac_sl'])
        self.assertEqual(kq['so_khac_gia'], 1)
        self.assertEqual(len(theo[b.ten]), 2)                       # dòng trùng tên ghép theo thứ tự: dòng 2 chỉ hộ A có
        self.assertFalse(theo[b.ten][0]['khac_tien'])
        self.assertEqual(theo[b.ten][1]['chi_mot'], 'a')
        self.assertIsNone(theo[b.ten][1]['b'])
        self.assertEqual(theo[c.ten][0]['chi_mot'], 'b')
        self.assertIsNone(theo[c.ten][0]['a'])
        from pabt import nghiep_vu
        self.assertEqual(kq['tong_a'], nghiep_vu.tinh_ho(self.con, self.ma[0]).tong)
        self.assertEqual(kq['tong_b'], nghiep_vu.tinh_ho(self.con, self.ma[1]).tong)
        muc = [d['muc'] for d in kq['dong']]
        self.assertEqual(muc, sorted(muc, key=so_sanh_ho.THU_TU_MUC.index))   # theo thứ tự mục

    def test_chi_doc_khong_ghi(self):
        a = self.muc(1)[0]
        self.lap(0, [(a, 2, None)])
        trang = self.con.total_changes
        so_sanh_ho.so_sanh(self.con, self.ma[0], self.ma[0])
        self.assertEqual(self.con.total_changes, trang)
        kq = so_sanh_ho.so_sanh(self.con, self.ma[0], self.ma[0])
        self.assertFalse([d for d in kq['dong'] if d['khac_gia'] or d['khac_sl'] or d['khac_tien'] or d['chi_mot']])


DONG_PDF = """Phụ lục II
ĐƠN GIÁ BỒI THƯỜNG THIỆT HẠI THỰC TẾ VỀ NHÀ, NHÀ Ở, CÔNG TRÌNH XÂY DỰNG KHU VỰC 2 TRÊN ĐỊA BÀN TỈNH THỬ
Phụ lục IIa
Loại Quy mô, kết cấu công trình
Đơn giá bồi
thường (đồng/m2
sàn xây dựng)
1 2 3
A. Nhà, nhà ở
Nhà 6 đến 8 tầng
Kết cấu: Móng, khung chịu lực bằng BTCT;
1 dày 20cm.
Vật liệu hoàn thiện: Tường xây gạch, sơn nước
nhôm.
7.000.000
Nhà 4 đến 5 tầng
Kết cấu: Móng; tường bao xây gạch dày 20cm. 2
6.000.000
Nhà 01 tầng, chiều cao từ 3m đến 4m (không
tính chiều cao tường thu hồi).
3 Kết cấu: Móng; mái lợp tôn.
4.900.000
2
Vật liệu hoàn thiện: Nền lát gạch hoa.
8
Nhà 01 tầng, chiều cao từ 3m đến 4m (không
tính chiều cao tường thu hồi). 2.600.000
Kết cấu: Móng xây bằng đá.
Nhà tạm 1
Kết cấu: Cột kèo gỗ.
800.000
Nhà nuôi yến kết
hợp ở
Phần diện tích để ở được áp giá theo đơn giá
nhà ở.
Nhà nuôi yến Kết cấu khung chịu lực BTCT, xây gạch. 3.000.000
B. Nhà xưởng
Nhà xưởng 01 tầng, nhịp kết cấu từ 12m đến
15m
Kết cấu: Móng, đà kiềng bằng BTCT 2
1.800.000
Phụ lục IIb
STT Danh mục
Đơn vị
tính Đơn giá
1 Ao đào, bờ đất đồng/m3 30.000
7 Bể chứa xây gạch, có tô trát đồng/m3
xây 1.700.000
12 Chuồng trại tạm: nền láng xi măng hoặc lát gạch tàu,
cột các loại, mái tranh tre, vách tạm
dông/m2 390.000
19 Giếng đào sâu < 5m đồng/m
sâu 630.000
22 Giếng khoan công nghiệp đường kính 114mm trở lên
(tính tối đa 60m)
đồng/m
sâu 680.000
2
39
Nhà tắm riêng biệt tường gạch, không mái, có lót nền.
(Bao gồm những nhà tắm không có trong mục 5 và
mục 6)
đồng/m2 780.000
40
Nhà tắm riêng biệt: Móng xây đá chẻ; nền lát gạch
ceramic (nếu không lát gạch ceramic
giảm 110.000 đồng/m2 xây dựng; trường hợp mái ngói
tính thêm 110.000 đồng/m2
; trường hợp mái BTCT thì
tính thêm 275.000
đồng/m2
)
đồng/m2 3.200.000
70 Trụ giếng bằng gỗ đồng/giế
ng
270.000
76 Tường rào xây gạch có khung lưới B40
(có tô, trát) đồng/m2 380.000
77 Tường rào không tô trát hoặc rào khung lưới
B40, trụ các loại có khung đồng/m2 220.000
79 Xây gạch lòng giếng, thành giếng đồng/m
chiều cao
490.000
Phụ lục IIc
13. Nhà cùng loại nếu có một phần tường xây dày 20cm thì tính thêm 110.000
đồng/m² tường hoàn thiện.""".split('\n')


class TestDocPdfPhuLucII(unittest.TestCase):
    """Phụ lục II bản PDF đọc theo dòng: cấu trúc như văn bản thật, tên / giá GIẢ LẬP."""

    def setUp(self):
        from pabt import nhap_don_gia as ndg
        self.qt = []
        self.ds = ndg.nhan_muc([[x] for x in DONG_PDF], 2, self.qt)
        self.theo = {m.ten: m for m in self.ds}

    def test_bang_loai(self):
        m = self.theo['Nhà 6 đến 8 tầng']
        self.assertEqual((m.dvt, m.don_gia), ('m²', 7000000))
        self.assertIn('Kết cấu: Móng', m.ghi_chu)
        self.assertIn('Vật liệu hoàn thiện', m.ghi_chu)
        self.assertNotIn(' 2', self.theo['Nhà 4 đến 5 tầng'].ghi_chu.replace('20cm', ''))      # số loại rơi vào dòng mô tả
        ten = 'Nhà 01 tầng, chiều cao từ 3m đến 4m (không tính chiều cao tường thu hồi)'
        self.assertEqual(self.theo[f'{ten} (nhà loại 3)'].don_gia, 4900000)
        self.assertEqual(self.theo[f'{ten} (nhà loại 4)'].don_gia, 2600000)
        self.assertIn('Nền lát gạch hoa', self.theo[f'{ten} (nhà loại 3)'].ghi_chu)      # mô tả sau dòng giá
        self.assertEqual(self.theo['Nhà tạm 1'].don_gia, 800000)                         # số thuộc tên
        self.assertEqual(self.theo['Nhà nuôi yến'].ghi_chu, 'Kết cấu khung chịu lực BTCT, xây gạch.')
        self.assertTrue([q for q in self.qt if q.startswith('Nhà nuôi yến kết hợp ở: Phần diện tích')])
        self.assertNotIn('Nhà nuôi yến kết hợp ở', self.theo)
        self.assertEqual(self.theo['Nhà xưởng 01 tầng, nhịp kết cấu từ 12m đến 15m'].dvt, 'm²')

    def test_bang_danh_muc(self):
        for ten, dvt, gia in (('Ao đào, bờ đất', 'm³', 30000), ('Bể chứa xây gạch, có tô trát', 'm³ xây', 1700000),
                              ('Chuồng trại tạm: nền láng xi măng hoặc lát gạch tàu, cột các loại, mái tranh tre, vách tạm', 'm²', 390000),
                              ('Giếng đào sâu < 5m', 'm sâu', 630000),
                              ('Giếng khoan công nghiệp đường kính 114mm trở lên (tính tối đa 60m)', 'm sâu', 680000),
                              ('Trụ giếng bằng gỗ', 'giếng', 270000), ('Tường rào xây gạch có khung lưới B40 (có tô, trát)', 'm²', 380000),
                              ('Tường rào không tô trát hoặc rào khung lưới B40, trụ các loại có khung', 'm²', 220000),
                              ('Xây gạch lòng giếng, thành giếng', 'm chiều cao', 490000)):
            self.assertEqual((self.theo[ten].dvt, self.theo[ten].don_gia), (dvt, gia), ten)
        tam = [m for m in self.ds if m.ten.startswith('Nhà tắm')]
        self.assertEqual([m.don_gia for m in tam], [780000, 3200000])            # giá trong ngoặc không thành mục
        self.assertIn('(Bao gồm những nhà tắm không có trong mục 5 và mục 6)', tam[0].ten)
        self.assertIn('tính thêm 275.000 đồng/m2)', tam[1].ten)
        self.assertEqual({m.dvt for m in tam}, {'m²'})
        rac = [m.ten for m in self.ds if m.ten.lower().startswith(('đồng/', 'stt', '(', 'trường hợp', 'nhà cùng loại'))]
        self.assertEqual(rac, [])
        self.assertEqual({m.khu_vuc for m in self.ds}, {'2'})


@unittest.skipUnless(CO_QT, 'cần PySide6')
class TestCuaSo(_Nen):
    def cua_so(self, i: int = 0):
        from pabt.man_hinh import CuaSoLapPA
        w = CuaSoLapPA(self.con, self.ma[i])
        self.addCleanup(self._dong, w)
        return w

    @staticmethod
    def _dong(w):
        w.hoi_luu = lambda: True
        w.close()
        w.deleteLater()

    def _cot(self, bm, k):
        return [c[0] for c in bm.cot].index(k)

    def test_gon_cot(self):
        from pabt.man_hinh import COT_PHU_GON
        w = self.cua_so()
        b2 = w.bang[2]
        self.assertFalse(b2._bang.isColumnHidden(self._cot(b2, 'quy_cach')))      # mặc định tắt
        b2.b_gon.setChecked(True)
        for k in COT_PHU_GON:
            self.assertTrue(b2._bang.isColumnHidden(self._cot(b2, k)), k)
        for k in ('ten', 'dvt', 'so_luong', 'don_gia', 'thanh_tien', 'ghi_chu'):
            self.assertFalse(b2._bang.isColumnHidden(self._cot(b2, k)), k)
        b3 = w.bang[3]                                                            # bảng dựng sau nhận trạng thái
        self.assertTrue(b3.b_gon.isChecked())
        self.assertTrue(b3._bang.isColumnHidden(self._cot(b3, 'nguon')))
        b4 = w.bang[4]
        self.assertTrue(b4._bang.isColumnHidden(self._cot(b4, 'ma')))
        self.assertFalse(b4._bang.isColumnHidden(self._cot(b4, 'cach_tinh')))
        self.assertIsNone(w.bang[1].b_gon)                                        # mục đất không có cột phụ
        b3.b_gon.setChecked(False)                                                # tắt ở một bảng: mọi bảng
        self.assertFalse(b2.b_gon.isChecked())
        self.assertFalse(b2._bang.isColumnHidden(self._cot(b2, 'quy_cach')))

    def test_chi_tiet_dong(self):
        a, b = self.muc(2)
        self.lap(0, [(a, 2, None), (b, 3, None)])
        w = self.cua_so()
        bm = w.bang[2]
        self.assertIsNone(bm.khung_ct)                                            # chưa dùng: không dựng
        bm.bang.setCurrentCell(0, self._cot(bm, 'ten'))
        bm._phim_ct.activated.emit()                                              # phím Space
        self.assertFalse(bm.khung_ct.isHidden())
        self.assertFalse(bm.khung_ct.isWindow())                                  # không thành cửa sổ lạ
        self.assertIn(a.ten, bm.khung_ct.lb_ten.text())
        self.assertIn('Nguồn giá', bm.khung_ct.lb_nguon.text())
        self.assertTrue(bm.khung_ct.o_gt.toPlainText())
        bm.bang.setCurrentCell(1, self._cot(bm, 'ten'))                           # đi theo dòng chọn
        self.assertIn(b.ten, bm.khung_ct.lb_ten.text())
        o = bm.khung_ct.o['quy_cach']
        o.setText('Khung thép  thử')
        o.editingFinished.emit()
        self.assertEqual(w.bo.pa.khoan[2][1].quy_cach, 'Khung thép thử')          # ghi qua ô của bảng -> sua_o
        self.assertTrue(w.bo.co_thay_doi)
        self.assertEqual(bm._bang.item(1, self._cot(bm, 'quy_cach')).text(), 'Khung thép thử')
        o.editingFinished.emit()                                                  # không đổi: không ghi lại
        self.assertEqual(w.bo.pa.khoan[2][1].quy_cach, 'Khung thép thử')
        bm.khung_ct.b_dong.click()
        self.assertTrue(bm.khung_ct.isHidden())
        self.assertFalse(bm.bat_tat_chi_tiet(False))
        self.assertTrue(bm.bat_tat_chi_tiet())
        self.assertEqual(bm.khung_ct.r, 1)

    def test_chi_tiet_chua_co_dong_va_muc_dat(self):
        w = self.cua_so()
        bm = w.bang[2]
        self.assertEqual(bm._bang.rowCount(), 0)
        bm.bat_tat_chi_tiet(True)
        self.assertIn('Chọn một dòng', bm.khung_ct.lb_ten.text())
        self.assertFalse(bm.khung_ct.o['ghi_chu'].isEnabled())
        d = w.bang[1]
        self.assertEqual(sorted(d.bat_tat_chi_tiet(True) and d.khung_ct.o), ['ghi_chu'])

    def test_chi_doc_khi_phuong_an_khoa(self):
        a = self.muc(1)[0]
        self.lap(0, [(a, 2, None)])
        w = self.cua_so()
        bm = w.bang[2]
        bm.bang.setCurrentCell(0, self._cot(bm, 'ten'))
        bm.bat_tat_chi_tiet(True)
        self.assertFalse(bm.khung_ct.o['quy_cach'].isReadOnly())
        w.bo.khoa = True
        w._ap_khoa()
        bm.khung_ct.nap()
        o = bm.khung_ct.o['quy_cach']
        self.assertTrue(o.isReadOnly())
        goc = w.bo.pa.khoan[2][0].quy_cach
        o.setText('Không được ghi')
        o.editingFinished.emit()
        self.assertEqual(w.bo.pa.khoan[2][0].quy_cach, goc)
        self.assertTrue(bm.khung_ct.b_dong.isEnabled())                           # chỉ xem vẫn đóng được khung
        self.assertTrue(bm.b_gon.isEnabled())                                     # Gọn cột chỉ đổi cách xem
        self.assertFalse(bm.nut['▲ Lên'].isEnabled())
        w.bo.khoa = False
        w._ap_khoa()

    def test_ghim_danh_sach_ho(self):
        w = self.cua_so()
        self.assertIsNone(w._w_ds_ho)                                             # chưa dùng: không dựng
        self.assertTrue(w.bat_tat_ds_ho())
        k = w._w_ds_ho
        self.assertFalse(k.isHidden())
        self.assertFalse(k.isWindow())
        self.assertTrue(w.b_ds_ho.isChecked())
        self.assertEqual(k.ds.count(), len(self.ma))
        self.assertEqual(k.ds.currentItem().data(Qt.ItemDataRole.UserRole), self.ma[0])
        k.loc('ho thu 2')                                                         # lọc không dấu
        hien = [k.ds.item(i).text() for i in range(k.ds.count()) if not k.ds.item(i).isHidden()]
        self.assertTrue(any(x.endswith('Hộ thử 2') for x in hien))
        self.assertLess(len(hien), len(self.ma))
        k.loc('')
        k._bam(k.ds.item(2))                                                      # bấm tên: chuyển hộ
        self.assertEqual(w.bo.ma_ho, self.ma[2])
        self.assertEqual(k.ds.currentRow(), 2)
        w.sang_ho(-1)                                                             # ◀ ▶: danh sách đi theo
        self.assertEqual(k.ds.currentRow(), 1)
        self.assertFalse(w.bat_tat_ds_ho())
        self.assertTrue(k.isHidden())
        self.assertFalse(w.b_ds_ho.isChecked())

    def test_tu_choi_luu_giu_ho_cu(self):
        w = self.cua_so()
        w.bat_tat_ds_ho(True)
        k = w._w_ds_ho
        with mock.patch.object(w, 'hoi_luu', return_value=False):
            k.ds.setCurrentRow(3)
            k._bam(k.ds.item(3))
        self.assertEqual(w.bo.ma_ho, self.ma[0])
        self.assertEqual(k.ds.currentRow(), 0)                                    # chọn lại hộ cũ

    def test_danh_sach_cap_nhat_khi_them_ho(self):
        w = self.cua_so()
        w.bat_tat_ds_ho(True)
        with self.con:
            self.con.execute("INSERT INTO ho (ma_ho, thu_tu, ho_ten) VALUES (99, 99, 'Hộ mới')")
        w.nap_ho()
        self.assertEqual(w._w_ds_ho.ds.count(), len(self.ma) + 1)

    def test_doi_chieu_hop(self):
        from pabt.man_hinh_phu_lap_pa import COT_SO_SANH
        a, b = self.muc(2)
        self.lap(0, [(a, 2, None)])
        self.lap(1, [(a, 2, a.don_gia + 1000), (b, 1, None)])
        w = self.cua_so()
        d = w.doi_chieu_ho(cho=False)
        self.addCleanup(d.deleteLater)
        self.assertFalse(d.isModal())
        self.assertEqual((d.cb_a.currentData(), d.cb_b.currentData()), (self.ma[0], self.ma[1]))   # mặc định hộ kế tiếp
        self.assertEqual(d.bang.columnCount(), len(COT_SO_SANH))
        self.assertEqual(d.kq['so_khac_gia'], 1)
        chu = [d.bang.item(r, 9).text() for r in range(d.bang.rowCount())]
        self.assertIn('khác đơn giá', chu)
        self.assertIn('chỉ hộ B có', chu)
        self.assertIn('Chênh lệch', d.lb.text())
        d.o_chi_khac.setChecked(True)
        for r, x in enumerate(d.kq['dong']):
            self.assertEqual(d.bang.isRowHidden(r), not (x['khac_gia'] or x['khac_sl'] or x['khac_tien']))
        d.cb_b.setCurrentIndex(d.cb_b.findData(self.ma[0]))
        d.nap()
        self.assertEqual(d.kq['so_khac_gia'], 0)
        d2 = w.doi_chieu_ho(self.ma[2], cho=False)
        self.addCleanup(d2.deleteLater)
        self.assertEqual(d2.cb_b.currentData(), self.ma[2])

    def test_khong_hop_thong_bao_va_phim_khong_trung(self):
        w = self.cua_so()
        phim = [s.key().toString() for s in w._phim]
        self.assertEqual(len(phim), len(set(phim)))                               # phím trùng: Qt không chạy cái nào
        self.assertIn('Ctrl+B', phim)
        self.assertIn('F4', phim)                                                 # F4 vẫn là xem trước A4
        self.assertTrue(w.findChildren(QPushButton, ''))
        with mock.patch.object(QMessageBox, 'warning') as canh, mock.patch.object(QMessageBox, 'information') as tin:
            w.bat_tat_ds_ho(True)
            w.bang[2].bat_tat_chi_tiet(True)
        canh.assert_not_called()
        tin.assert_not_called()

    def test_be_rong_toi_thieu_hang_nut(self):
        """Màn hình 1366 @125% còn ~1.090 điểm, hàng nút cũ ~1.038 (phông offscreen Qt5 khác hẳn: so TƯƠNG ĐỐI): nút "DS hộ" thêm <= 52."""
        w = self.cua_so()
        co = w.thanh_tren.minimumSizeHint().width()
        w.b_ds_ho.setVisible(False)
        khong = w.thanh_tren.minimumSizeHint().width()
        w.b_ds_ho.setVisible(True)
        self.assertLessEqual(co - khong, 52)
        self.assertEqual(w._rong_ds_ho(5000), 230)                                 # màn hình rộng: đủ bề rộng
        self.assertEqual(w._rong_ds_ho(600), 120)                                  # màn hình hẹp: không dưới 120
        w.bat_tat_ds_ho(True)
        self.assertGreaterEqual(w._w_ds_ho.minimumWidth(), 120)


if __name__ == '__main__':
    unittest.main()

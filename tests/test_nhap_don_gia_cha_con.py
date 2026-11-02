"""02/11/2026 (người dùng, ảnh văn bản hợp nhất đơn giá nhà, công trình đọc từ bản scan): bộ đọc báo nhầm "mục mới" vì
(1) dòng con "- Ống 1 m Φ1m" mất tên dòng cha, (2) một dòng giá con dùng chung cho nhiều tài sản ("Trụ cổng, bờ kè và các loại tài sản
khác có kết cấu:"), (3) ô giá ghi khoảng "a - b" (bộ đơn giá ghi hai mục cùng tên, mục cao có dấu chấm cuối), (4) dòng hướng dẫn không
có giá. Văn bản và bộ đơn giá trong bài này là GIẢ LẬP (tên, giá đặt riêng) - không dùng số liệu thật."""
from __future__ import annotations
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from pabt import csdl, don_gia
from pabt import nhap_don_gia as ndg
from tests import APP  # noqa: F401 - QApplication dùng chung cho hộp thoại

# (mã, tên, ĐVT, đơn giá, ghi chú) - nhóm 2 của bộ đơn giá giả lập
BO = [
    ('TS1', 'Giếng khoan Φ60 mm', 'm', 100000, ''),
    ('TS2', 'Giếng thả ống bê tông Φ1,5m (ống 1m)', 'cái', 500000, 'Kể cả lắp đặt'),
    ('TS3', 'Giếng thả ống bê tông Φ1m (ống 1m)', 'cái', 400000, 'Kể cả lắp đặt'),
    ('TS4', 'Giếng thả ống bê tông Φ0,6m (ống 1m)', 'cái', 300000, 'Kể cả lắp đặt'),
    ('TS5', 'Ống cống bê tông Φ1,0 m', 'm', 450000, ''),
    ('TS6', 'Mái tôn, mái che', 'm²', 200000, ''),
    ('TS7', 'Mái tôn, mái che.', 'm²', 600000, ''),
    ('TS8', 'Bể chứa xây gạch, nắp đan', 'm³', 500000, ''),
    ('TS9', 'Bể chứa xây gạch, nắp đan.', 'm³', 700000, ''),
    ('TS10', 'Sân phơi', 'm²', 100000, ''),
    ('TS11', 'Cột cổng không cốt thép', 'm³', 2000000, ''),
    ('TS12', 'Cột cổng bê tông cốt thép', 'm³', 4000000, ''),
    ('TS13', 'Cột cổng xây gạch, xây đá', 'm³', 1500000, ''),
    ('TS14', 'Kè bê tông không cốt thép', 'm³', 2000000, ''),
    ('TS15', 'Kè bê tông cốt thép', 'm³', 4000000, ''),
    ('TS16', 'Kè xây gạch, xây đá', 'm³', 1500000, ''),
    ('TS17', 'Mương đan không cốt thép', 'm³', 2000000, ''),
    ('TS18', 'Mương đan bê tông cốt thép', 'm³', 4000000, ''),
    ('TS19', 'Hòn non bộ', 'm³', 900000, ''),
    ('TS20', 'Tường rào móng đá, cột gạch, tường gạch 10cm tô trát', 'm²', 500000, ''),
    ('TS21', 'Tường rào móng đá, cột gạch, tường gạch 20cm tô trát', 'm²', 600000, ''),
]

# bản scan đọc theo dòng: STT ô gộp nằm ở dòng giữa nhóm, ô tên xuống dòng, ĐVT "mét" / "đồng/m2", khoảng giá, dòng hướng dẫn
DONG_CHU = '''PHỤ LỤC
ĐƠN GIÁ CÔNG TRÌNH XÂY DỰNG
STT Tên tài sản ĐVT Đơn giá (đồng)
1 Giếng khoan Φ60 mm mét 110.000
- Giếng sâu từ 10m trở lên thì mét thứ 10 trở mét
đi được tính thêm 50% mức giá trên
Giếng thả ống bê tông (kể cả lắp đặt)
- Ống 1 m Φ1,5 m cái 520.000
2 - Ống 1 m Φ1m cái 420.000
- Ống 1 m Φ0,6 m cái 300.000
3 Mái tôn, mái che m² 210.000 - 650.000
4 Bể chứa xây gạch, có nắp m³ 500.000 - 700.000
đan
5 Sân phơi m² 100.000 - 150.000
Cột cổng, kè và các loại tài sản khác có kết
cấu:
- Bằng bê tông không có cốt thép m³ 2.100.000
6 - Bằng bê tông cốt thép m³ 4.200.000
- Bằng gạch xây tô, xây đá m³ 1.600.000
Tường rào móng đá, cột gạch,
7 tường xây gạch dày 10cm có tô trát đồng/m2 520.000
8 Tường rào móng đá, cột gạch, tường xây gạch dày 20cm Đồng/m2 600.000
có tô trát
9 Hòn non bộ m³ 900.000
a) Bằng 40% đơn giá 01 m² của kết cấu từng loại nhà tương ứng (gác dùng
để ở).'''.split('\n')

# cùng nội dung, bảng có tiêu đề cột (Word / Excel / bản scan có khung): ô STT gộp chỉ ở dòng đầu nhóm
BANG = [['STT', 'Tên tài sản', 'ĐVT', 'Đơn giá (đồng)'],
        ['1', 'Giếng khoan Φ60 mm', 'mét', '110.000'],
        ['', '- Giếng sâu từ 10m trở lên thì mét thứ 10 trở đi được tính thêm 50% mức giá trên', 'mét', ''],
        ['2', 'Giếng thả ống bê tông (kể cả lắp đặt)', '', ''],
        ['', '- Ống 1 m Φ1,5 m', 'cái', '520.000'],
        ['', '- Ống 1 m Φ1m', 'cái', '420.000'],
        ['', '- Ống 1 m Φ0,6 m', 'cái', '300.000'],
        ['3', 'Mái tôn, mái che', 'm²', '210.000 - 650.000'],
        ['4', 'Bể chứa xây gạch, có nắp đan', 'm³', '500.000 - 700.000'],
        ['5', 'Sân phơi', 'm²', '100.000 - 150.000'],
        ['6', 'Cột cổng, kè và các loại tài sản khác có kết cấu:', '', ''],
        ['', '- Bằng bê tông không có cốt thép', 'm³', '2.100.000'],
        ['', '- Bằng bê tông cốt thép', 'm³', '4.200.000'],
        ['', '- Bằng gạch xây tô, xây đá', 'm³', '1.600.000'],
        ['7', 'Tường rào móng đá, cột gạch, tường xây gạch dày 10cm có tô trát', 'đồng/m2', '520.000'],
        ['8', 'Tường rào móng đá, cột gạch, tường xây gạch dày 20cm có tô trát', 'Đồng/m2', '600.000'],
        ['9', 'Hòn non bộ', 'm³', '900.000']]


class _Co(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        td = Path(self.tmp.name)
        self._cu = os.environ.get('PABT_THU_MUC_MAY')
        os.environ['PABT_THU_MUC_MAY'] = str(td / 'may')
        self.bo = td / 'bo_gia_lap.sqlite'
        shutil.copyfile(don_gia.file_goc(), self.bo)
        con = csdl.mo(self.bo)
        try:
            with con, csdl.mo_khoa_danh_muc(con):
                pl = con.execute('SELECT phan_loai FROM dm_taisan WHERE nhom = 2 LIMIT 1').fetchone()[0]
                con.execute('DELETE FROM dm_taisan WHERE nhom = 2')
                con.executemany('INSERT INTO dm_taisan (ma, nhom, phan_loai, ten, dvt, don_gia, ghi_chu) VALUES (?,2,?,?,?,?,?)',
                                [(ma, pl, t, d, str(g), gc) for ma, t, d, g, gc in BO])
        finally:
            con.close()
        p = mock.patch.object(don_gia, 'file_dang_dung', return_value=self.bo)
        p.start()
        self.addCleanup(p.stop)

    def tearDown(self):
        self.doCleanups()
        if self._cu is None:
            os.environ.pop('PABT_THU_MUC_MAY', None)
        else:
            os.environ['PABT_THU_MUC_MAY'] = self._cu
        self.tmp.cleanup()

    def _doc(self, dong):
        qt = []
        ds = ndg.so_khop(ndg.nhan_muc(dong, 2, qt), None)
        return ds, qt, {m.ma_khop: m for m in ds if m.ma_khop}


class TestDongChu(_Co):
    """Bản scan đọc theo dòng chữ (một ô mỗi dòng)."""

    def _kiem(self, dong):
        ds, qt, theo = self._doc(dong)
        moi = [m for m in ds if m.trang_thai == 'mới']
        # chỉ mức cao của "Sân phơi" là mục mới (bộ chưa có mục cao) - đề xuất, không chọn sẵn
        self.assertEqual([(m.ten, m.don_gia, m.chon, m.ma_moi) for m in moi], [('Sân phơi.', 150000, False, 'TS22')])
        self.assertIn('Mức cao của khoảng giá', moi[0].ghi_chu)
        # 1. dòng con giữ tên dòng cha, khớp theo cỡ Φ dù tên khác bộ đơn giá
        self.assertEqual((theo['TS2'].don_gia, theo['TS2'].trang_thai), (520000, 'cập nhật'))
        self.assertTrue(theo['TS2'].ten.startswith('Giếng thả ống bê tông (kể cả lắp đặt) - Ống 1 m Φ1,5 m'))
        self.assertEqual((theo['TS3'].don_gia, theo['TS4'].trang_thai), (420000, 'giữ nguyên'))
        self.assertNotIn('TS5', theo)                   # ống cống cùng Φ1 nhưng ĐVT m: không nhầm
        # 2. dòng chung: một giá cho mọi mục cùng kết cấu của cột cổng, kè và tài sản khác liền khối cùng giá (mương đan)
        self.assertEqual({k: theo[k].don_gia for k in ('TS11', 'TS14', 'TS17')}, dict.fromkeys(('TS11', 'TS14', 'TS17'), 2100000))
        self.assertEqual({k: theo[k].don_gia for k in ('TS12', 'TS15', 'TS18')}, dict.fromkeys(('TS12', 'TS15', 'TS18'), 4200000))
        self.assertEqual({k: theo[k].don_gia for k in ('TS13', 'TS16')}, dict.fromkeys(('TS13', 'TS16'), 1600000))
        self.assertEqual(theo['TS17'].cach_khop, ndg.CACH_DONG_CHUNG)
        self.assertEqual(theo['TS19'].trang_thai, 'giữ nguyên')     # hòn non bộ (cùng ĐVT, khác giá) không bị kéo vào dòng chung
        # 3. khoảng giá: thấp -> mục không dấu chấm, cao -> mục có dấu chấm
        self.assertEqual((theo['TS6'].don_gia, theo['TS7'].don_gia), (210000, 650000))
        self.assertEqual((theo['TS8'].don_gia, theo['TS9'].don_gia), (500000, 700000))
        self.assertEqual(theo['TS9'].cach_khop, ndg.CACH_CAO)
        self.assertEqual((theo['TS10'].don_gia, theo['TS10'].trang_thai), (100000, 'giữ nguyên'))
        # tường rào 10cm / 20cm không lẫn nhau
        self.assertEqual((theo['TS20'].don_gia, theo['TS21'].don_gia), (520000, 600000))
        self.assertEqual(theo['TS1'].don_gia, 110000)
        return ds, qt

    def test_doc_theo_dong(self):
        ds, qt = self._kiem([[x] for x in DONG_CHU])
        # 4. dòng hướng dẫn không giá -> quy tắc (kèm tên mục nó thuộc), không thành mục
        self.assertEqual(len(qt), 2)
        self.assertTrue(qt[0].startswith('Giếng khoan Φ60 mm: Giếng sâu từ 10m'))
        self.assertIn('tính thêm 50% mức giá trên', qt[0])
        self.assertIn('(gác dùng để ở)', qt[1])
        self.assertFalse(any('Giếng sâu' in m.ten for m in ds))
        self.assertTrue(any(m.ten == 'Bể chứa xây gạch, có nắp đan' for m in ds))     # ô tên xuống dòng: nối lại

    def test_doc_bang_co_tieu_de(self):
        ds, qt = self._kiem(BANG)
        self.assertEqual(len(qt), 1)

    def test_dong_phu_khong_lap_lai_khi_so_lai(self):
        ds, _, _ = self._doc([[x] for x in DONG_CHU])
        n = len(ds)
        ndg.so_khop(ds, None)
        self.assertEqual(len(ds), n)

    def test_ap_dung_dong_chung_va_khoang_gia(self):
        ds, _, _ = self._doc(BANG)
        kq = ndg.ap_dung(ds, None, 'thử')
        self.assertEqual(kq['so_moi'], 0)                  # "Sân phơi." không chọn sẵn
        con = csdl.mo(kq['file'], chi_doc=True)
        try:
            gia = dict(con.execute('SELECT ma, don_gia FROM dm_taisan WHERE nhom = 2').fetchall())
        finally:
            con.close()
        self.assertEqual([int(float(gia[k])) for k in ('TS11', 'TS14', 'TS17', 'TS7', 'TS2')],
                         [2100000, 2100000, 2100000, 650000, 520000])
        self.assertNotIn('TS22', gia)

    def test_thay_the_giu_ten_muc_dong_chung(self):
        ds = ndg.so_khop(ndg.nhan_muc(BANG, 2), None, thay_the=True)
        theo = {m.ma_khop: m for m in ds if m.ma_khop}
        self.assertEqual(theo['TS17'].ten_thay, '')       # tên dòng chung là của cả nhóm tài sản: không đặt cho từng mục
        self.assertFalse(any(m.bo_cu and m.ma_khop in ('TS17', 'TS18') for m in ds))


class TestHam(unittest.TestCase):
    def test_khoang_gia_va_dvt(self):
        self.assertEqual(ndg.doc_khoang_gia('259.000 - 720.000'), (259000, 720000))
        self.assertIsNone(ndg.doc_khoang_gia('720.000 - 259.000'))
        self.assertIsNone(ndg.doc_khoang_gia('1.200.000'))
        self.assertEqual([ndg.chuan_dvt(x) for x in ('Đồng/m2', 'mét', 'mét/sợi', 'm3', 'cây')], ['m²', 'm', 'm/sợi', 'm³', 'cây'])

    def test_quy_tac_va_chu_the_chung(self):
        self.assertTrue(ndg.la_quy_tac('Giếng sâu từ 10m trở lên thì mét thứ 10 trở đi được tính thêm 50% mức giá trên'))
        self.assertTrue(ndg.la_quy_tac('xác định theo loại kết cấu nhà có các bộ phận cấu tạo chiếm tỷ lệ cao hơn'))
        self.assertFalse(ndg.la_quy_tac('Giếng thả ống ciment (kể cả lắp đặt)'))
        self.assertEqual(ndg.chu_the_chung('Trụ cổng, bờ kè và các loại tài sản khác có kết cấu'), (['tru cong', 'bo ke'], True))
        self.assertIsNone(ndg.chu_the_chung('Giếng thả ống ciment (kể cả lắp đặt)'))
        self.assertIsNone(ndg.chu_the_chung('Giếng khoan công nghiệp (có giàn khoan)'))

    def test_dac_trung(self):
        a = ndg.dac_trung('Giếng thả ống (kể cả lắp đặt) - Ống 1 m Φ1,2 m')
        b = ndg.dac_trung('Giếng thả ống Φ1,2m (ống 1m)')
        self.assertEqual((a[0], a[1]), (b[0], b[1]))
        self.assertEqual(ndg.dac_trung('Ống Φ60 mm')[0], ndg.dac_trung('Ống Φ6 cm')[0])
        self.assertIsNone(ndg.diem_dac_trung('Tường gạch 10cm', 'm²', {'ten': 'Tường gạch 20cm', 'dvt': 'm²'}))
        self.assertIsNone(ndg.diem_dac_trung('Kè bê tông cốt thép', 'm³', {'ten': 'Kè bê tông không cốt thép', 'dvt': 'm³'}))
        self.assertIsNone(ndg.diem_dac_trung('Cây vải - Năm thứ 1', 'cây', {'ten': 'Cây vải - Năm 2', 'dvt': 'cây'}))


class TestHopThoai(_Co):
    def test_hien_quy_tac_va_cach_khop(self):
        from pabt.man_hinh_nhap_don_gia import HopNhapDonGia
        HopNhapDonGia.im_lang = True
        try:
            h = HopNhapDonGia(None, dong=[[x] for x in DONG_CHU], van_ban={}, nhom_uu_tien=2, nguon='thử')
            self.assertIsNotNone(h.o_quy_tac)
            self.assertIn('tính thêm 50%', h.o_quy_tac.toPlainText())
            self.assertIn('dòng chung', h.lb.text())
            i = next(i for i, m in enumerate(h.ds) if m.ma_khop == 'TS17')
            self.assertIn('dòng chung', h.bang.item(i, 6).text())
            self.assertIn('Dòng chung', h.bang.item(i, 2).toolTip())
            h.close()
            h.deleteLater()
        finally:
            HopNhapDonGia.im_lang = False


if __name__ == '__main__':
    unittest.main()

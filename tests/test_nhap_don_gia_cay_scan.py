"""03/11/2026 (người dùng: "thiết lập bộ đọc, bộ phân tích chi tiết về liên kết cây trồng theo dạng của bộ đơn giá trong phần mềm" -
thử trên bản scan văn bản hợp nhất đơn giá cây trồng): đọc bản scan theo đúng cách bộ đơn giá ghi - một dòng nhiều loài -> mỗi loài một
mục, giá nhiều mùa vụ trong một ô, loài cây lâm nghiệp đọc sai tên nhận ra nhờ thuộc đúng nhóm giá trong bộ, chữ số đọc sai không ghi
đè giá. Văn bản và bộ đơn giá là GIẢ LẬP (giá đặt riêng) - không dùng số liệu / file thật."""
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

_QH = (130000, 170000, 450000, 600000)          # bảng giá theo cỡ <3, >3-6, >6-9, >9-12 (giả lập)
_N3 = (90000, 120000, 310000, 420000)
_N5 = (60000, 85000, 220000, 300000)
_CO = ('(d <3 cm)', '(d >3-6 cm)', '(d >6-9 cm)', '(d >9-12 cm)')

BO = [('CT1', 'Cây lúa (Đông Xuân)', 'ha', 30000000, ''), ('CT2', 'Cây lúa (Hè Thu, Mùa)', 'ha', 20000000, ''),
      ('CT3', 'Cây cải xanh', 'ha', 300000000, ''), ('CT4', 'Cây cải ngọt', 'ha', 300000000, ''),
      ('CT5', 'Cây Bã đậu', 'cây', 70000, ''), ('CT6', 'Cây Phượng', 'cây', 70000, ''),
      ('CT7', 'Cây Liễu (mức 70.000 đ/cây)', 'cây', 70000, ''), ('CT8', 'Cây Liễu (mức 150.000 đ/cây)', 'cây', 150000, ''),
      ('CT9', 'Cây Ngâu', 'cây', 150000, ''),
      ('CT10', 'Si cảnh - 5cm ≤ Đk thân ≤ 10cm', 'cây', 200000, ''), ('CT11', 'Sanh cảnh - 5cm ≤ Đk thân ≤ 10cm', 'cây', 200000, ''),
      ('CT12', 'Cây bưởi - Năm thứ 1', 'cây', 300000, 'Mật độ 210 cây/ha'),
      ('CT13', 'Cây bưởi - Năm thứ 2', 'cây', 500000, 'Mật độ 210 cây/ha'),
      ('CT14', 'Cây bưởi - Năm thứ 3', 'cây', 700000, 'Mật độ 210 cây/ha')]
_SO = 15
for _loai, _gia in (('Sưa', _QH), ('Lim xanh', _QH), ('Re đỏ', _N3), ('Giổi', _N3), ('Sữa', _N5), ('Mý', _N5), ('Ruổi', _N5)):
    for _c, _g in zip(_CO, _gia):
        BO.append((f'CT{_SO}', f'{_loai} {_c}', 'cây', _g, ''))
        _SO += 1


def _bang_co(nhom: str, ten: str, gia: tuple, co=('<3', '>3-6', '>6-9', '>9-12')) -> list:
    return [[nhom, ten, co[0], f'{gia[0]:,}'.replace(',', '.')]] + \
        [['', '', c, f'{g:,}'.replace(',', '.')] for c, g in zip(co[1:], gia[1:])]


# bản scan đọc theo bảng (ô cách nhau bằng Tab): tiêu đề cột giá đọc sai, STT rác, chú thích cuối trang, giá có chữ số đọc sai
DONG = ([['STT', 'Tên cây trồng', 'Đnn CÓ ác'], ['I', 'Nhóm cây lương thực', ''],
         ['1', 'Cây lúa', 'Đông Xuân: 30.000.000 72c Hè Thu, Mùa: 20.000.000'],
         ['2', 'Cây cải xanh, cải ngọt, cải thìa (họ cải các loại)', '300.000.000'],
         ['ST', 'Tên cây trồng', 'Đơn vị', 'Đơn giá bồi thường'],
         ['1', 'Cây bưởi (Mật độ 210 cây/ha)', '', ''], ['1', 'Năm thứ 1', 'Cây', '300.000'],
         ['° Mục này được sửa đổi theo quy định tại khoản 2 Điều 3 của Quyết định số 66/2025/QĐ-'],
         ['UBND, có hiệu lực kể từ ngày 27 tháng 11 năm 2025.'], ['12'],
         ['—— h ị', 'Năm thứ 2', 'Cây', '5O0.000'], ['', 'Năm thứ 3', 'Cây', '! 700.000'],
         ['SIT', 'Loại cây', 'Đơn vị tính', 'Đơn giá bồi thường'],
         ['8', 'Cây Bã đậu, Phượng, Liêu.', 'cây', '70.000'], ['9', 'Ngâu, Liêu', 'cây', '180.000'],
         ['20', 'Si cảnh, Sanh cảnh', '', ''], ['', '5cm < Ðk thân kỐ 10cm', 'Cây', '200.000'],
         ['I', 'Nhóm loài cây gỗ trồng trên cạn (mật độ chuẩn 833 cây/ha)', 'Đường kính thân cây (cm)',
          'Đơn giá bồi thường (đồng/cây)']]
        + _bang_co('1', 'Nhóm quý hiếm gồm 2 loài', _QH, ('<3', '>3-6', '> ni', '>9-12'))
        + _bang_co('2', 'Nhóm III gồm 2 loài', _N3) + _bang_co('3', 'Nhóm V gồm 4 loài', _N5)
        + [['Bảng 1: Nhóm loài cây quý hiếm'], ['TT', 'Tên Việt Nam', 'Tên Việt Nam khác', 'Tên khoa học'],
           ['1', 'Sưa', 'Trắc thối. Huê mộc vàng', 'Dalbergia'], ['2', 'Lim xanh', '', ''],
           ['Bảng 4: Loài cây nhóm III'], ['TT', 'Tên Việt Nam', 'Tên Việt Nam khác', 'Tên khoa học'],
           ['1', 'Sc đỏ', '', ''], ['2', 'Giổi', '', ''],
           ['Bảng 6: Loài cây nhóm V'], ['TT', 'Tên Việt Nam', 'Tên Việt Nam khác', 'Tên khoa học'],
           ['1', 'Sữa', 'Mò cua', ''], ['2', 'Vý', '', ''], ['3', 'Suổi', '', ''], ['4', '(Được bãi bỏ)', '', '']])


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
                pl = con.execute("SELECT phan_loai FROM dm_taisan WHERE nhom = 3 AND ma LIKE 'CT%' LIMIT 1").fetchone()[0]
                con.execute('DELETE FROM dm_taisan WHERE nhom = 3')
                con.executemany('INSERT INTO dm_taisan (ma, nhom, phan_loai, ten, dvt, don_gia, ghi_chu) VALUES (?,3,?,?,?,?,?)',
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

    def doc(self, thay_the=False):
        dong = ndg.DongScan(DONG)
        qt = []
        ds = ndg.nhan_muc(dong, 3, qt)
        ds, _ = ndg.tach_theo_loai(ds, ndg.doc_nhom_loai(dong))
        ndg.so_khop(ds, None, thay_the=thay_the, scan=True)
        return ds, qt


class TestCayScan(_Co):
    def test_khop_theo_cau_truc_bo_don_gia(self):
        ds, qt = self.doc()
        theo = {m.ma_khop: m for m in ds if m.ma_khop}
        moi = [m.ten for m in ds if m.trang_thai == 'mới']
        self.assertEqual(moi, ['Cây cải thìa'])          # loài văn bản ghi mà bộ chưa có: mục mới
        # giá nhiều mùa vụ trong một ô (rác OCR giữa hai nhãn)
        self.assertEqual((theo['CT1'].trang_thai, theo['CT2'].trang_thai), ('giữ nguyên', 'giữ nguyên'))
        # dòng nhiều loài -> mỗi loài một mục như bộ ("Cây cải ngọt"; "Phượng" -> "Cây Phượng"; "Liêu" -> mục Liễu cùng giá)
        for ma in ('CT3', 'CT4', 'CT5', 'CT6', 'CT7', 'CT10', 'CT11'):
            self.assertEqual(theo[ma].trang_thai, 'giữ nguyên', ma)
        self.assertEqual(theo['CT4'].cach_khop, ndg.CACH_TACH_LOAI)
        self.assertEqual(theo['CT7'].tach_tu, 'Cây Bã đậu, Phượng, Liêu')
        # dòng con: STT ô gộp đọc lặp, STT rác, chú thích cuối trang chen giữa, giá có chữ rác / chữ O thay số 0
        self.assertEqual([theo[ma].trang_thai for ma in ('CT12', 'CT13', 'CT14')], ['giữ nguyên'] * 3)
        self.assertEqual(theo['CT13'].nghi_gia, '5O0.000')
        # loài cây lâm nghiệp: Sưa (quý hiếm) / Sữa (nhóm V) không lẫn; tên đọc sai nhận ra theo nhóm giá của bộ
        for loai, ma0 in (('Sưa', 15), ('Re đỏ', 23), ('Sữa', 31), ('Mý', 35), ('Ruổi', 39)):
            for i in range(4):
                m = theo[f'CT{ma0 + i}']
                self.assertEqual(m.trang_thai, 'giữ nguyên', (loai, m.ten, m.don_gia))
        self.assertFalse(any('bãi bỏ' in m.ten.lower() for m in ds))
        # cỡ đường kính đọc hỏng ("> ni") suy theo thứ tự, đánh dấu để xem
        self.assertIn('suy là (d >6-9 cm)', theo['CT17'].nghi_gia)
        # chú thích cuối trang không thành dòng cha / quy tắc
        self.assertFalse(any('hiệu lực' in m.ten for m in ds))
        self.assertFalse(any('hiệu lực' in x for x in qt))

    def test_gia_nghi_doc_sai_khong_chon_san(self):
        ds, _ = self.doc()
        theo = {m.ma_khop: m for m in ds if m.ma_khop}
        # "180.000" (bộ 150.000): 8 / 5 hay bị nhận dạng nhầm - đổi giá nhưng không chọn sẵn
        self.assertEqual((theo['CT9'].trang_thai, theo['CT9'].chon), ('cập nhật', False))
        self.assertTrue(theo['CT9'].nghi_gia.startswith('nghi đọc sai'))
        self.assertEqual(theo['CT8'].trang_thai, 'cập nhật')

    def test_thay_the_ban_scan_khong_chon_san_muc_bo(self):
        ds, _ = self.doc(thay_the=True)
        bo = [m for m in ds if m.bo_cu]
        self.assertFalse(any(m.chon for m in bo))        # bản scan đọc thiếu dòng: mục "bỏ" phải tự đánh dấu

    def test_ham_doc_gia_ocr(self):
        self.assertEqual(ndg.tach_nhieu_gia('Đông Xuân: 37.050.000 E=—<<[«s Hè Thu: 40.000.000'),
                         [('Đông Xuân', 37050000), ('Hè Thu', 40000000)])
        self.assertEqual(ndg.tach_nhieu_gia('Đông Xuân: 1.000.000'), [])
        self.assertEqual((ndg.doc_gia_ocr('S27.312'), ndg.doc_gia_ocr('729/009'), ndg.doc_gia_ocr('Á A')), (527312, 729009, None))
        self.assertTrue(ndg.nham_chu_so(157000, 187000))
        self.assertTrue(ndg.nham_chu_so(7000, 377000))     # thiếu chữ số
        self.assertFalse(ndg.nham_chu_so(150000, 165000))
        self.assertEqual(ndg.ds_loai_trong_ten('Cây cải xanh, cải ngọt (họ cải)'), ['Cây cải xanh', 'Cây cải ngọt'])
        self.assertEqual(ndg.ds_loai_trong_ten('Hoa giấy, Ti gôn'), ['Hoa giấy', 'Ti gôn'])
        self.assertEqual(ndg.ds_loai_trong_ten('Năm thu hoạch thứ 1 - 5'), [])
        self.assertEqual(ndg.tach_mat_do_ten('Cây cóc “Mật độ 280 cây/ha)'), ('Cây cóc', 'Mật độ 280 cây/ha'))


if __name__ == '__main__':
    unittest.main()

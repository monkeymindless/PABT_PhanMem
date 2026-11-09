"""1.0.91 (người dùng 09/11/2026):
1. Đối thoại có ý kiến của hộ SAU đối thoại (lấy ý kiến lần 1 không đồng ý, đối thoại xong đồng ý) - đồng thuận tính theo ý kiến hiệu lực,
   ý kiến lần đầu giữ nguyên làm chứng cứ.
2. Thang 6 nấc theo QĐ 18/2026: chỉ coi là ĐÃ TRÌNH (B8) khi đợt trình có văn bản trình (số + ngày tờ trình); mới xếp đợt thì vẫn ở B6-7,
   chữ trạng thái ghi đúng việc đã làm (niêm yết / lấy ý kiến / đối thoại). Dự án GIẢ LẬP tests.test_toc_do._du_an."""
from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

from pabt import csdl, du_thao, pheu_tien_do as ph, quan_ly, quy_trinh, theo_doi  # noqa: E402
from tests.test_toc_do import _du_an  # noqa: E402


class _Co(unittest.TestCase):
    N = 3

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.td = Path(self.tmp.name)
        self._cu = os.environ.get('PABT_THU_MUC_MAY')
        os.environ['PABT_THU_MUC_MAY'] = str(self.td / 'may')
        self.con = csdl.mo(_du_an(self.td, self.N))
        self.ma = [r[0] for r in self.con.execute('SELECT ma_ho FROM ho ORDER BY thu_tu')]
        self.ny = du_thao.tao_dot(self.con, '02 THỬA / 03 HỘ', '22/10/2026', 'UBND xã')
        du_thao.them_thu_cong(self.con, self.ny, self.ma, ca_vuong=True)

    def tearDown(self):
        self.con.close()
        if self._cu is None:
            os.environ.pop('PABT_THU_MUC_MAY', None)
        else:
            os.environ['PABT_THU_MUC_MAY'] = self._cu
        self.tmp.cleanup()

    def ho(self, ma) -> theo_doi.TongHopHo:
        return next(h for h in theo_doi.tong_hop(self.con, tinh_pa=False) if h.ma_ho == ma)

    def lay_y_kien(self):
        """Như ảnh của người dùng: hộ 1, 3 đồng ý; hộ 2 không đồng ý."""
        a, b, c = self.ma
        for m, loai in ((a, 'dong_y'), (b, 'khong_dong_y'), (c, 'dong_y')):
            du_thao.ghi_y_kien(self.con, self.ny, m, loai, 'khac' if loai != 'dong_y' else '', 'Đề nghị bồi thường đất' if loai != 'dong_y' else '')


class TestDoiThoai(_Co):
    def test_khong_dong_y_doi_thoai_xong_dong_y(self):
        self.lay_y_kien()
        b = self.ma[1]
        self.assertEqual(du_thao.thong_ke_y_kien(self.con, self.ny)['dong_y'], 2)
        lan = du_thao.ghi_doi_thoai(self.con, self.ny, b, '05/11/2026', 'UBND xã', 'Giải thích nguồn gốc đất, hộ thống nhất', y_kien='dong_y')
        self.assertEqual(lan, 1)
        tk = du_thao.thong_ke_y_kien(self.con, self.ny)
        self.assertEqual((tk['dong_y'], tk['khong_dong_y']), (3, 0))                      # đồng thuận theo ý kiến sau đối thoại
        h = next(x for x in du_thao.ds_ho_dot(self.con, self.ny) if x['ma_ho'] == b)
        self.assertEqual((h['loai'], h['y_kien_doi_thoai'], h['hieu_luc']), ('khong_dong_y', 'dong_y', 'dong_y'))   # lần đầu giữ nguyên
        tong = [x for x in du_thao.tong_hop_nhom(self.con, self.ny) if not x['nhom']][0]
        self.assertEqual(tong['dong_y'], 3)
        dt = self.con.execute('SELECT lan, y_kien FROM doi_thoai_ho WHERE dot_id = ? AND ma_ho = ?', (self.ny, b)).fetchall()
        self.assertEqual([tuple(r) for r in dt], [(1, 'dong_y')])
        # hộ đã đồng ý sau đối thoại không bị chuyển sang đợt sau
        ny2 = du_thao.tao_dot(self.con, 'Đợt 2', '10/11/2026', 'UBND xã')
        self.assertEqual(du_thao.chuyen_sang_dot(self.con, self.ny, [b], ny2), 0)

    def test_doi_nhanh_va_xoa_y_kien_sau_doi_thoai(self):
        self.lay_y_kien()
        b = self.ma[1]
        seq = [du_thao.doi_y_kien_sau_doi_thoai_nhanh(self.con, self.ny, b) for _ in range(4)]
        self.assertEqual(seq, ['dong_y', 'khong_dong_y', 'y_kien_khac', ''])
        self.assertEqual(du_thao.thong_ke_y_kien(self.con, self.ny)['khong_dong_y'], 1)   # xóa: về lại ý kiến lần đầu
        with self.assertRaises(du_thao.LoiNhap):
            du_thao.dat_y_kien_sau_doi_thoai(self.con, self.ny, b, 'sai')


class TestThangNacQd18(_Co):
    def test_trinh_tu_b6_b7_b8(self):
        a, b, c = self.ma
        self.assertEqual(self.ho(a).trang_thai, 'Đã niêm yết, đang lấy ý kiến (B6–7)')
        self.lay_y_kien()
        self.assertEqual(self.ho(a).trang_thai, 'Đã lấy ý kiến (B7): đồng ý')
        self.assertEqual(self.ho(b).trang_thai, 'Đã lấy ý kiến (B7): không đồng ý, cần đối thoại')
        du_thao.ghi_doi_thoai(self.con, self.ny, b, '05/11/2026', '', 'Thống nhất', y_kien='dong_y')
        self.assertEqual(self.ho(b).trang_thai, 'Đã lấy ý kiến, đối thoại (B7): đồng ý')
        for m in self.ma:
            self.assertEqual(self.ho(m).tien_do.nac, 2)
        # xếp vào đợt trình (như "Lấy hộ đã niêm yết xong") nhưng CHƯA có văn bản trình: vẫn B6-7
        dt = quan_ly.tao_dot(self.con, 'Đợt trình 1')
        quan_ly.gan_dot(self.con, self.ma, dt)
        x = self.ho(a)
        self.assertEqual((x.tien_do.nac, x.da_trinh, x.xep_dot_trinh), (2, False, True))
        self.assertIn('đã xếp đợt trình, chưa có tờ trình', x.trang_thai)
        kq = ph.tinh(self.con)
        self.assertEqual(kq.dem().get('cho_phe_duyet', 0), 0)
        self.assertEqual(len(kq.theo_co('xep_dot_chua_trinh')), self.N)
        self.assertTrue(any('chưa có số, ngày văn bản trình' in v.chu for v in quy_trinh.tinh(self.con).viec))
        # có số + ngày tờ trình: đã trình (B8)
        quan_ly.sua_dot(self.con, dt, ten='Đợt trình 1', so_to_trinh='15/TTr-BBT', ngay_trinh='01/11/2026')
        x = self.ho(a)
        self.assertEqual((x.tien_do.nac, x.da_trinh), (3, True))
        self.assertTrue(x.trang_thai.startswith('Đã trình thẩm định (B8)'))
        self.assertEqual(ph.tinh(self.con).dem()['cho_phe_duyet'], self.N)

    def test_trinh_khi_chua_doi_thoai_thi_canh_bao(self):
        self.lay_y_kien()
        b = self.ma[1]
        dt = quan_ly.tao_dot(self.con, 'Đợt trình 1', so_to_trinh='15/TTr-BBT', ngay_trinh='01/11/2026')
        quan_ly.gan_dot(self.con, [b], dt)
        self.assertIn('chưa đối thoại', self.ho(b).tien_do.canh_bao)


class TestManHinh(_Co):
    def test_cot_y_kien_sau_doi_thoai_mot_cham(self):
        from tests import APP  # noqa: F401 - QApplication
        from pabt.man_hinh_du_thao import KhungDuThao
        self.lay_y_kien()
        k = KhungDuThao(self.con)
        self.addCleanup(k.close)
        k.show()
        k.cb.setCurrentIndex(k.cb.findData(self.ny))
        k._ve()
        self.assertEqual(k.bang_dt.rowCount(), 1)                                     # chỉ hộ không đồng ý / ý kiến khác
        self.assertEqual(k.bang_dt.horizontalHeaderItem(5).text(), 'Ý kiến sau đối thoại')
        self.assertIn('Không đồng ý', k.bang_dt.item(0, 2).text())
        self.assertIn('Chưa đối thoại', k.bang_dt.item(0, 5).text())
        self.assertEqual(k._doi_nhanh_dt(0), 'dong_y')
        self.assertEqual(k.bang_dt.rowCount(), 1)                                     # hộ vẫn ở thẻ đối thoại (lần đầu không đồng ý)
        self.assertIn('Đồng ý', k.bang_dt.item(0, 5).text())
        self.assertEqual(du_thao.thong_ke_y_kien(self.con, self.ny)['dong_y'], 3)


if __name__ == '__main__':
    unittest.main()

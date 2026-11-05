"""1.0.63: thanh phiên bản, bảng đối chiếu, 4 mẫu in, khớp 4 tầng khi đọc kết quả. Kịch bản: V1 10.000 đ, khóa -> ý kiến -> V2.1 50.000 đ -> chênh +40.000 đ / đơn vị -> V3 về V1, cả ba còn nguyên, 4 mẫu in đúng số."""
from __future__ import annotations

import os
import tempfile
import unittest
import zipfile
from decimal import Decimal
from pathlib import Path
from unittest import mock

import openpyxl

from pabt import csdl, du_thao
from pabt import in_phien_ban as ipb
from pabt import phien_ban_pa as pb
from pabt import van_ban_dot as vbd
from pabt.lap_pa import BoSoan

from tests import APP
from tests.test_phien_ban_pa import _du_an, dat_cay, doi_gia

D = Decimal


def chu_docx(f) -> str:
    with zipfile.ZipFile(f) as z:
        return z.read('word/document.xml').decode('utf-8')


class TestKhop4Tang(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.addCleanup(self.td.cleanup)
        self.con = csdl.mo(_du_an(Path(self.td.name), 4))
        self.addCleanup(self.con.close)
        c = self.con
        self.ma = [r[0] for r in c.execute('SELECT ma_ho FROM ho ORDER BY thu_tu')]
        with c:
            c.execute("UPDATE ho SET ho_ten = 'Nguyễn Văn An', so_cccd = '075200000001' WHERE ma_ho = ?", (self.ma[0],))
            c.execute("UPDATE ho SET ho_ten = 'Trần Thị Bình là chủ sở hữu' WHERE ma_ho = ?", (self.ma[1],))
            c.execute("UPDATE ho SET ho_ten = 'UBND xã Phú Lý quản lý.' WHERE ma_ho = ?", (self.ma[2],))
            c.execute("UPDATE ho SET ho_ten = 'Nguyễn Văn An' WHERE ma_ho = ?", (self.ma[3],))    # trùng tên hộ 1
        self.dot = du_thao.tao_dot(c, 'Đợt 1', '2026-11-01', 'UBND xã')
        du_thao.them_thu_cong(c, self.dot, self.ma, ca_vuong=True)

    def _doc(self, dong):
        with mock.patch('pabt.quan_ly.doc_van_ban', return_value=(dong, False)):
            return vbd.doc_ket_qua(self.con, self.dot, ['f.xlsx'])

    def test_dang_o(self):
        self.assertEqual(vbd.cap_thua_to('17 (tờ 39)'), [('17', '39')])
        self.assertEqual(vbd.cap_thua_to('11, 21 (tờ 19)'), [('11', '19'), ('21', '19')])
        self.assertEqual(vbd.cap_thua_to('Thửa 16 tờ 39'), [('16', '39')])
        self.assertEqual(vbd.cap_thua_to('thửa đất số 016, tờ bản đồ số 39'), [('16', '39')])
        self.assertEqual(vbd.chuan_cccd(75200000001), '075200000001')
        self.assertEqual(vbd.ten_sach('UBND xã Phú Lý quản lý.'), 'ubnd xa phu ly')
        self.assertEqual(vbd.ten_sach('Bà Trần Thị Bình là chủ sở hữu quyền sử dụng'), 'tran thi binh')

    def test_tang_1_ma_dinh_danh(self):
        u = pb.uuid_ho(self.con, self.ma[3])
        kq = self._doc([['2', 'Tên sai', u, 'Đồng ý']])
        self.assertEqual([(d.ma_ho, d.khop_theo) for d in kq['dong']], [(self.ma[3], 'mã định danh')])

    def test_tang_2_cccd_mat_so_0_khong_dinh_stt(self):
        kq = self._doc([['1', '', '75200000001', 'Đồng ý']])                        # cột STT sát cột CCCD: từng làm dính số
        self.assertEqual([(d.ma_ho, d.khop_theo) for d in kq['dong']], [(self.ma[0], 'CCCD')])
        kq = self._doc([['1', '', '75200000001.0', 'Đồng ý']])
        self.assertEqual(len(kq['dong']), 1)

    def test_tang_3_thua_to(self):
        kq = self._doc([['', '', '102 (tờ 12)', 'Không đồng ý']])
        self.assertEqual([(d.ma_ho, d.khop_theo, d.loai) for d in kq['dong']], [(self.ma[2], 'thửa, tờ', 'khong_dong_y')])

    def test_tang_4_ten_hau_to_cong_san(self):
        kq = self._doc([['2', 'Trần Thị Bình', '', 'Đồng ý'], ['3', 'UBND xã Phú Lý quản lý.', '', 'Đồng ý']])
        self.assertEqual({d.ma_ho for d in kq['dong']}, {self.ma[1], self.ma[2]})

    def test_trung_ten_dung_stt_khong_doan(self):
        self.assertEqual(self._doc([['', 'Nguyễn Văn An', '', 'Đồng ý']])['dong'], [])       # trùng tên, không STT: KHÔNG đoán
        kq = self._doc([['4', 'Nguyễn Văn An', '', 'Đồng ý']])
        self.assertEqual([(d.ma_ho, d.khop_theo) for d in kq['dong']], [(self.ma[3], 'họ tên + STT')])
        self.assertEqual(self._doc([['', 'Văn An', '', 'Đồng ý']])['dong'], [])               # chuỗi con không khớp

    def test_khong_khop_co_vi_du_va_so_ho(self):
        kq = self._doc([['STT', 'Họ tên'], ['9', 'Người Ngoài Đợt']])
        self.assertEqual(kq['dong'], [])
        self.assertEqual(kq['so_ho_dot'], 4)
        self.assertEqual(len(kq['khong_khop']), 2)

    def test_ho_nhieu_dong_lay_dong_co_ket_qua(self):
        kq = self._doc([['', '', '102 (tờ 12)', ''], ['', '', '102 (tờ 12)', 'Không đồng ý']])
        self.assertEqual([d.loai for d in kq['dong']], ['khong_dong_y'])

    def test_khong_dong_y_tao_v2_giu_v1(self):
        dat_cay(self.con, self.ma[2])
        pb.khoa_v1(self.con, self.ma[2])
        kq = self._doc([['', '', '102 (tờ 12)', 'Không đồng ý đơn giá']])
        vbd.ap_dung(self.con, self.dot, 'y_kien', kq['dong'])
        self.assertEqual(kq['dong'][0].v2, 'V2.1')
        self.assertIn('đơn giá', pb.lay(self.con, self.ma[2], 'V2.1')['ghi_chu'])
        self.assertEqual(pb.doc_pa(self.con, self.ma[2], 'V2.1').khoan[3][0].don_gia, D(10000))     # không tự ghi giá vào dòng nào
        vbd.ap_dung(self.con, self.dot, 'y_kien', self._doc([['', '', '102 (tờ 12)', 'Không đồng ý đơn giá']])['dong'])
        self.assertEqual([x['ma'] for x in pb.ds_phien_ban(self.con, self.ma[2])], ['V1', 'V2.1', 'V3'])  # đọc lại file: không thêm nhánh

    def test_vong_khu_hoi_bang_niem_yet(self):
        f = Path(self.td.name) / 'ny.xlsx'
        du_thao.xuat_niem_yet(self.con, self.dot, f)
        wb = openpyxl.load_workbook(f)
        hang = [list(r) for r in wb.active.iter_rows(values_only=True)]
        wb.close()
        cot = hang[2].index('Mã định danh')
        self.assertTrue(all(len(r[cot]) == 36 for r in hang[3:]))
        for ma in self.ma:
            self.assertIsNotNone(pb.lay(self.con, ma, pb.V1))                        # xuất niêm yết = chốt V1
        kq = vbd.doc_ket_qua(self.con, self.dot, [f])
        self.assertEqual({d.khop_theo for d in kq['dong']}, {'mã định danh'})
        self.assertEqual(len(kq['dong']), 4)


class TestBonMauIn(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.addCleanup(self.td.cleanup)
        self.dir = Path(self.td.name)
        self.con = csdl.mo(_du_an(self.dir))
        self.addCleanup(self.con.close)
        self.m = self.con.execute('SELECT MIN(ma_ho) FROM ho').fetchone()[0]
        dat_cay(self.con, self.m)

    def test_kich_ban_du_4_mau(self):
        con, m = self.con, self.m
        f1 = ipb.mau_01(con, [m], self.dir)[0]
        doi_gia(con, m, pb.tao_v2(con, m, 'Dân đề nghị 50.000 đ'), 50000)
        f2 = ipb.mau_02(con, m, 'V2.1', self.dir / 'm2.docx')
        pb.dat_v3(con, m, pb.V1, 'Phòng Kinh tế không chấp thuận')
        f3 = ipb.mau_03(con, [m], self.dir / 'm3.xlsx')
        f4 = ipb.mau_04(con, m, self.dir / 'm4.docx')
        c1, c2, c4 = chu_docx(f1), chu_docx(f2), chu_docx(f4)
        self.assertIn('10.000', c1)
        self.assertNotIn('50.000', c1)
        self.assertIn('(DỰ THẢO)', c1)
        self.assertEqual(ipb.doc_ma_dinh_danh(f1), pb.uuid_ho(con, m))
        self.assertIn('50.000', c2)
        self.assertIn('DỰ THẢO PHỤC VỤ ĐỐI THOẠI LẦN 1', c2)
        self.assertIn('10.000', c4)
        self.assertNotIn('50.000', c4)
        self.assertNotIn('DỰ THẢO', c4)
        wb = openpyxl.load_workbook(f3)
        chu = ' '.join(str(v) for ws in wb.worksheets for r in ws.iter_rows(values_only=True) for v in r if v is not None)
        wb.close()
        self.assertIn('+4.000.000', chu)                                             # V2 - V1: 100 cây x 40.000
        self.assertIn('Phòng Kinh tế không chấp thuận', chu)
        self.assertIn('Có ý kiến nhưng giữ theo V1', chu)
        for ma_v, gia in ((pb.V1, 10000), ('V2.1', 50000), (pb.V3, 10000)):
            self.assertEqual(pb.doc_pa(con, m, ma_v).khoan[3][0].don_gia, D(gia))

    def test_in_du_thao_thuong_theo_v1_du_so_hien_hanh_doi(self):
        from pabt import in_word
        pb.khoa_v1(self.con, self.m)
        dat_cay(self.con, self.m, gia=77777)
        c = chu_docx(in_word.xuat_chi_tiet_docx(self.con, self.m, self.dir / 'dt.docx', du_thao=True))
        self.assertIn('10.000', c)
        self.assertNotIn('77.777', c)
        c = chu_docx(in_word.xuat_chi_tiet_docx(self.con, self.m, self.dir / 'ct.docx'))
        self.assertIn('77.777', c)                                                   # bản thường: số hiện hành

    def test_mau_loi_ro_rang(self):
        from pabt.lap_pa import LoiNhap
        with self.assertRaises(LoiNhap):
            ipb.mau_04(self.con, self.m, self.dir / 'x.docx')
        with self.assertRaises(LoiNhap):
            ipb.mau_02(self.con, self.m, 'V1', self.dir / 'x.docx')


@unittest.skipIf(APP is None, 'cần PySide6 / PySide2')
class TestGiaoDien(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        cu = os.environ.get('PABT_THU_MUC_MAY')
        self.addCleanup(lambda: os.environ.pop('PABT_THU_MUC_MAY', None) if cu is None else os.environ.__setitem__('PABT_THU_MUC_MAY', cu))
        os.environ['PABT_THU_MUC_MAY'] = str(Path(self.tmp.name) / 'may')

    def _cua_so(self):
        from pabt import app as ud
        w = ud.CuaSoChinh(menu_trai=True)
        self.addCleanup(w.close)
        w.show()
        w.mo(str(_du_an(Path(self.tmp.name))))
        APP.processEvents()
        return w

    def _lap_pa(self, w):
        m = w.con.execute('SELECT MIN(ma_ho) FROM ho').fetchone()[0]
        dat_cay(w.con, m)
        man = w.mo_lap_pa(m, cho=False)
        man.im_lang = True
        man.hoi_luu = lambda: True
        self.addCleanup(man.close)
        return man, m

    def test_thanh_chon_phien_ban(self):
        w = self._cua_so()
        man, m = self._lap_pa(w)
        t = man.thanh_pb
        man.nap_ho()
        self.assertEqual(sorted(t.nut), ['V0', 'chot', 'moi'])
        t.nut['chot'].click()
        self.assertEqual(sorted(t.nut), ['V0', 'V1', 'V3', 'moi'])
        t.nut[pb.V1].click()                                                       # V1: khóa chỉ xem cả bảng, một lần bấm
        self.assertTrue(man.bo.khoa)
        self.assertEqual(man.bo.phien_ban, pb.V1)
        self.assertTrue(man.b_mo_khoa.isHidden())                                  # không có nút mở khóa
        self.assertIn('chỉ xem', t.chu_trang_thai())
        self.assertEqual(man.lb_trang_thai_lan.text(), 'V1 ĐÃ KHÓA - CHỈ XEM')       # đã thấy trên ảnh: từng ghi ĐANG LẬP DỰ THẢO, "đã có quyết định phê duyệt"
        ma = t.tao_v2('Dân đề nghị')                                               # V2: tự mở, sửa được
        self.assertEqual((ma, man.bo.phien_ban, man.bo.khoa), ('V2.1', 'V2.1', False))
        man.bo.pa.khoan[3][0].don_gia = D(50000)
        man.bo.luu()
        self.assertEqual(BoSoan(w.con, m).pa.khoan[3][0].don_gia, D(10000))         # số hiện hành không đổi
        t.nut[pb.V0].click()
        self.assertEqual((man.bo.phien_ban, man.bo.pa.khoan[3][0].don_gia), (None, D(10000)))

    def test_nut_mo_khoa_khoa_lai_tung_phien_ban(self):
        w = self._cua_so()
        man, m = self._lap_pa(w)
        t = man.thanh_pb
        man.nap_ho()
        self.assertTrue(t.b_khoa.isHidden())                                       # V0 chưa khóa: không có nút
        pb.khoa_v1(w.con, m)
        t.nap()
        t.chon(pb.V1)
        self.assertFalse(t.b_khoa.isHidden())
        self.assertEqual(t.b_khoa.text(), 'Mở khóa')
        self.assertEqual(man.lb_trang_thai_lan.text(), 'V1 ĐÃ KHÓA - CHỈ XEM')
        t.b_khoa.click()
        self.assertFalse(man.bo.khoa)
        self.assertEqual(man.bo.phien_ban, pb.V1)
        self.assertEqual(t.b_khoa.text(), 'Khóa lại')
        self.assertEqual(t.nut[pb.V1].text(), 'V1 Đang mở')
        self.assertEqual(man.lb_trang_thai_lan.text(), 'ĐANG SỬA V1')
        self.assertIn('Lưu ghi vào V1', t.chu_trang_thai())
        man.bo.pa.khoan[3][0].don_gia = D(11111)
        man.bo.luu()
        man._ve_menu_lan()
        self.assertIn('Trả V1 về bản đã chốt…', [a.text() for a in man.menu_lan.actions()])
        self.assertTrue(t.tra_v1_goc(True))
        self.assertTrue(man.bo.khoa)
        self.assertEqual(man.bo.pa.khoan[3][0].don_gia, D(10000))
        self.assertEqual(t.nut[pb.V1].text(), 'V1 Đã khóa')
        t.chon(pb.V3)                                                              # V3: mở sẵn, khóa được, mở lại được
        self.assertEqual(t.b_khoa.text(), 'Khóa lại')
        t.b_khoa.click()
        self.assertTrue(man.bo.khoa)
        self.assertEqual(t.nut[pb.V3].text(), 'V3 Đã khóa')
        t.b_khoa.click()
        self.assertFalse(man.bo.khoa)

    def test_lan_da_duyet_mo_khoa_duoc_o_moi_phien_ban(self):
        w = self._cua_so()
        man, m = self._lap_pa(w)
        t = man.thanh_pb
        pb.khoa_v1(w.con, m)
        v2 = pb.tao_v2(w.con, m)
        from pabt import lan_pa
        lan_pa._dam_bao_dong(w.con, m, 1)
        with w.con:
            w.con.execute('UPDATE pa_lan SET khoa = 1 WHERE ma_ho = ? AND lan = 1', (m,))
        man.bo.mo(m, 1)
        man.nap_ho()
        self.assertTrue(man.bo.khoa)
        self.assertFalse(man.b_mo_khoa.isHidden())                                 # V0
        t.chon(v2)
        self.assertTrue(man.bo.khoa)
        self.assertFalse(man.b_mo_khoa.isHidden())                                 # V2: trước đây mất nút, không sửa được
        self.assertTrue(t.b_khoa.isHidden())
        self.assertTrue(man.mo_khoa_lan(True, 'Điều chỉnh'))
        self.assertEqual(man.bo.phien_ban, v2)                                     # ở lại V2
        self.assertFalse(man.bo.khoa)

    def test_nhieu_nhanh_gom_nut(self):
        w = self._cua_so()
        man, m = self._lap_pa(w)
        t = man.thanh_pb
        pb.khoa_v1(w.con, m)
        for _ in range(5):
            pb.tao_v2(w.con, m)
        t._dau = None
        t.nap()
        self.assertEqual(sorted(k for k in t.nut if k.startswith('V2')), ['V2.3', 'V2.4', 'V2.5'])
        t.chon('V2.1')                                                             # nhánh cũ đang mở: vẫn có nút của nó
        self.assertIn('V2.1', t.nut)
        self.assertEqual(sum(1 for k in t.nut if k.startswith('V2')), 3)

    def test_dai_mot_hang_va_menu_lan(self):
        w = self._cua_so()
        man, m = self._lap_pa(w)
        self.assertTrue(man._nut_an_lan.isHidden())
        man.menu_lan.aboutToShow.emit()
        chu = [a.text() for a in man.menu_lan.actions()]
        self.assertIn('Thêm PA bổ sung…', chu)
        self.assertNotIn('Xóa lần phương án…', chu)                                 # một lần PA: không có gì để xóa
        with mock.patch.object(man, 'lap_bo_sung') as lap:
            man.menu_lan.actions()[0].trigger()
        lap.assert_called_once()
        self.assertEqual(man.findChildren(type(man.thanh_pb))[0].parentWidget(), man.dai_lan)

    def test_bang_doi_chieu_mot_cham(self):
        w = self._cua_so()
        man, m = self._lap_pa(w)
        pb.khoa_v1(w.con, m)
        doi_gia(w.con, m, pb.tao_v2(w.con, m), 50000)
        d = man.thanh_pb.doi_chieu(cho=False)
        d.im_lang = True
        self.addCleanup(d.close)
        o = {d.bang.item(r, 1).text(): r for r in range(d.bang.rowCount())}['Cây thử']
        self.assertEqual(d.bang.item(o, 3).text(), '10.000')
        self.assertEqual(d.bang.item(o, 4).text(), '50.000')
        self.assertEqual(d.bang.item(o, 5).text(), '+4.000.000')
        self.assertIn('+', d.lb_tong.text())
        self.assertTrue(d.dat_v3('V2.1'))
        self.assertEqual(d.bang_ho.item(0, 2).text()[0], '+')                       # cột bên trái cập nhật ngay
        self.assertEqual(BoSoan(w.con, m).pa.khoan[3][0].don_gia, D(50000))
        d.o_ly_do.setText('Không chấp thuận')
        d.b_v1.click()
        self.assertEqual(BoSoan(w.con, m).pa.khoan[3][0].don_gia, D(10000))
        self.assertEqual(pb.lay(w.con, m, pb.V3)['ghi_chu'], 'Không chấp thuận')
        self.assertEqual(d.bang_ho.item(0, 2).text(), '0')
        self.assertTrue(d.da_doi)
        h = d.hop_ghep(cho=False)
        self.addCleanup(h.close)
        self.assertEqual(h.cb_nhom[pb.HO_TRO].findData(pb.TINH_LAI) >= 0, True)
        self.assertTrue(d.ghep({pb.NHA: pb.V1, pb.CAY: 'V2.1'}))
        self.assertEqual(BoSoan(w.con, m).pa.khoan[3][0].don_gia, D(50000))
        with tempfile.TemporaryDirectory() as td:
            for ma, file in (('01', td), ('02', str(Path(td) / 'a.docx')), ('03', str(Path(td) / 'b.xlsx')), ('04', str(Path(td) / 'c.docx'))):
                self.assertTrue(d.in_mau(ma, file), ma)

    def test_the_niem_yet_ap_dung_dong_loat(self):
        w = self._cua_so()
        ds = [r[0] for r in w.con.execute('SELECT ma_ho FROM ho ORDER BY thu_tu')]
        dot = du_thao.tao_dot(w.con, 'Đợt 9', '2026-11-01', 'UBND')
        du_thao.them_thu_cong(w.con, dot, ds, ca_vuong=True)
        for m in ds:
            dat_cay(w.con, m)
            pb.khoa_v1(w.con, m)
            doi_gia(w.con, m, pb.tao_v2(w.con, m), 50000)
            pb.dat_v3(w.con, m, 'V2.1')
        du_thao.cap_nhat_y_kien(w.con, dot, ds[0], loai='khong_dong_y')
        du_thao.cap_nhat_y_kien(w.con, dot, ds[1], loai='khong_dong_y')
        k = w.mo_du_thao(cho=False) or w.khung_tab.widget['du_thao']
        k.cb.setCurrentIndex(k.cb.findData(dot))
        d = k.doi_chieu_phien_ban(cho=False)
        d.im_lang = True
        self.addCleanup(d.close)
        self.assertEqual(d.bang_ho.rowCount(), 3)
        d.chon_ho(ds[2])
        self.assertEqual(d.ma_ho(), ds[2])
        self.assertEqual(d.tich_khong_dong_y(), 2)
        self.assertEqual(d.ap_dong_loat(hoi=False), (2, []))
        self.assertEqual([BoSoan(w.con, m).pa.khoan[3][0].don_gia for m in ds], [D(10000), D(10000), D(50000)])
        self.assertTrue(any(ten.startswith('Đối chiếu') for ten in k._nut))


if __name__ == '__main__':
    unittest.main()

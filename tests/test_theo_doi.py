"""Kiểm thử 0.9.12 (CSDL v10): nhiều quyết định phê duyệt / hộ (phê duyệt bổ sung), chi trả theo từng quyết định, bàn giao,
lọc tiến độ, nâng cấp file v9, màn hình Bảng tổng hợp / Theo dõi tiến độ / trạng thái một hộ."""
from __future__ import annotations
import os
import tempfile
import unittest
from pathlib import Path

import openpyxl

from pabt import csdl, ho_so, nhap_tho, quan_ly, theo_doi
from pabt.lap_pa import LoiNhap
from pabt.tien import D
from tests.test_nhap_tho import _don_gian, _ghi


class CoSo(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)           # chạy sau cùng: sau cả addCleanup của test (vd. đóng cửa sổ giữ file)
        self.td = Path(self.tmp.name)
        xl = self.td / 'ds.xlsx'
        _ghi(xl, _don_gian)
        self.p = self.td / 'da.pabt'
        nhap_tho.nhap(xl, self.p, 'Dự án thử')
        self.con = csdl.mo(self.p)
        self.ma = [r[0] for r in self.con.execute('SELECT ma_ho FROM ho ORDER BY thu_tu')]

    def tearDown(self):
        self.con.close()

    def hai_qd(self):
        a, b, c = self.ma[:3]
        q1 = theo_doi.luu_qd(self.con, None, '1234/QĐ-UBND', '5/10/2026', 'Phê duyệt đợt 1', '300.000.000')
        q2 = theo_doi.luu_qd(self.con, None, '3334/QĐ-UBND', '20/10/2026', 'Phê duyệt bổ sung')
        theo_doi.ghi_qd_ho(self.con, q1, a, dict(so_tien='100.000.000', tien_dat='80.000.000', tien_cay='20.000.000',
                                                  so_pa='101/PA', qd_ct_so='55/QĐ-CT'))
        theo_doi.ghi_qd_ho(self.con, q1, b, dict(so_tien='200000000'))
        theo_doi.ghi_qd_ho(self.con, q2, b, dict(so_tien='15.000.000', tien_ho_tro='15.000.000'))
        theo_doi.ghi_qd_ho(self.con, q2, c, dict(so_tien='5000000'))
        return q1, q2


class TestMoHinh(CoSo):
    def test_nhieu_quyet_dinh_va_chi_tra(self):
        q1, q2 = self.hai_qd()
        a, b, c = self.ma[:3]
        ds = theo_doi.ds_quyet_dinh(self.con)
        self.assertEqual([x.so for x in ds], ['3334/QĐ-UBND', '1234/QĐ-UBND'])              # mới nhất trước
        self.assertEqual((ds[1].so_ho, ds[1].tong_ho, ds[1].ngay), (2, D(300000000), '05/10/2026'))
        with self.assertRaises(LoiNhap):
            theo_doi.luu_qd(self.con, None, '1234/qđ-ubnd', '05/10/2026')                   # trùng số (không phân biệt hoa)
        # hộ b: 2 quyết định, tóm tắt trên bảng ho = cộng các quyết định
        tt = quan_ly.doc_trang_thai(self.con, b)
        self.assertEqual((tt['da_phe_duyet'], tt['qd_so'], D(tt['qd_so_tien']), tt['qd_ngay']),
                         (1, '1234/QĐ-UBND; 3334/QĐ-UBND', D(215000000), '20/10/2026'))
        # nhận tiền QĐ 1234: hộ b chưa nhận đủ (còn QĐ 3334)
        self.assertEqual(theo_doi.ghi_chi_tra(self.con, [(q1, a), (q1, b)], '10/10/2026', 'bien_lai.pdf'), 2)
        theo_doi.ghi_qd_ho(self.con, q2, b, dict(ly_do_chua_nhan='Đi làm ăn xa'))
        th = {x.ma_ho: x for x in theo_doi.tong_hop(self.con)}
        self.assertEqual((th[b].tong_phe_duyet, th[b].da_nhan, [q['so_qd'] for q in th[b].qd_chua_nhan]),
                         (D(215000000), D(200000000), ['3334/QĐ-UBND']))
        self.assertEqual(quan_ly.doc_trang_thai(self.con, b)['da_chi_tra'], 0)
        self.assertEqual(quan_ly.doc_trang_thai(self.con, a)['da_chi_tra'], 1)
        self.assertIn('1/2', th[b].trang_thai)
        # lọc tiến độ: theo một / nhiều quyết định
        loc = lambda k, qd=None: sorted(x.ma_ho for x in th.values() if theo_doi.hop_loc(x, k, qd))   # noqa: E731
        self.assertEqual(loc('chua_nhan'), sorted([b, c]))
        self.assertEqual(loc('da_nhan_het', {q1}), sorted([a, b]))          # theo QĐ 1234: a, b đã nhận
        self.assertEqual(loc('chua_nhan', {q2}), sorted([b, c]))
        self.assertEqual(loc('nhieu_qd'), [b])
        self.assertEqual(loc('chua_pd'), sorted(self.ma[3:]))
        # bỏ đánh dấu đã nhận: xóa ngày
        theo_doi.ghi_qd_ho(self.con, q1, a, dict(da_chi_tra=False))
        x = theo_doi.doc_qd_ho(self.con, a)[0]
        self.assertEqual((x['da_chi_tra'], x['chi_tra_ngay']), (0, ''))
        # bàn giao + lý do
        theo_doi.ghi_ban_giao(self.con, [c], dict(da_ban_giao=False, ly_do_ban_giao='Chưa tháo dỡ'))
        theo_doi.ghi_ban_giao(self.con, [a], dict(da_ban_giao=True, ban_giao_ngay='1/11/2026'))
        th = {x.ma_ho: x for x in theo_doi.tong_hop(self.con)}
        self.assertEqual((th[a].da_ban_giao, th[a].ban_giao_ngay, th[c].ly_do_ban_giao), (True, '01/11/2026', 'Chưa tháo dỡ'))
        # xóa quyết định: tóm tắt tính lại
        theo_doi.xoa_qd(self.con, q2)
        self.assertEqual(quan_ly.doc_trang_thai(self.con, c)['da_phe_duyet'], 0)
        self.assertEqual(D(quan_ly.doc_trang_thai(self.con, b)['qd_so_tien']), D(200000000))

    def test_ap_quyet_dinh_va_kieu_cu(self):
        a, b = self.ma[:2]
        # kiểu cũ (một quyết định / hộ) vẫn dùng được: ghi vào quyết định
        quan_ly.cap_nhat_trang_thai(self.con, [a, b], dict(da_phe_duyet=True, qd_so='9/QĐ-UBND', qd_ngay='01/10/2026',
                                                           qd_so_tien='1.000.000'))
        self.assertEqual(len(theo_doi.ds_quyet_dinh(self.con)), 1)
        self.assertEqual(theo_doi.ds_quyet_dinh(self.con)[0].so_ho, 2)
        quan_ly.cap_nhat_trang_thai(self.con, [a], dict(da_chi_tra=True, chi_tra_ngay='02/10/2026'))
        self.assertEqual(theo_doi.doc_qd_ho(self.con, a)[0]['chi_tra_ngay'], '02/10/2026')
        # nhập quyết định bổ sung từ danh sách: hộ b thêm một quyết định; chi trả chọn đúng quyết định theo số tiền
        ds = [quan_ly.DongKhop(b, 'B', D(7000000)), quan_ly.DongKhop(a, 'A', None, D(3000000))]
        kq = quan_ly.ap_quyet_dinh(self.con, 'pd', ds, '10/QĐ-UBND', '15/10/2026')
        self.assertEqual(kq['so_ho'], 2)
        self.assertEqual([x['so_qd'] for x in theo_doi.doc_qd_ho(self.con, b)], ['9/QĐ-UBND', '10/QĐ-UBND'])
        quan_ly.ap_quyet_dinh(self.con, 'ct', [quan_ly.DongKhop(b, 'B', D(7000000))], ngay='20/10/2026', file_goc='ds_chi.pdf')
        qd = {x['so_qd']: x for x in theo_doi.doc_qd_ho(self.con, b)}
        self.assertEqual((qd['10/QĐ-UBND']['da_chi_tra'], qd['9/QĐ-UBND']['da_chi_tra']), (1, 0))
        self.assertEqual(qd['10/QĐ-UBND']['chung_tu'], 'ds_chi.pdf')
        quan_ly.ap_quyet_dinh(self.con, 'bg', [quan_ly.DongKhop(b, 'B')], ngay='25/10/2026', file_goc='bb.pdf')
        h = self.con.execute('SELECT da_ban_giao, bien_ban_ban_giao FROM ho WHERE ma_ho = ?', (b,)).fetchone()
        self.assertEqual(tuple(h), (1, 'bb.pdf'))

    def test_gop_ho_xoa_ho_xoa_trang(self):
        q1, q2 = self.hai_qd()
        a, b, c = self.ma[:3]
        ho_so.gop_ho(self.con, b, c)                         # c vào b: quyết định 3334 của hai hộ cộng tiền
        x = {q['so_qd']: q for q in theo_doi.doc_qd_ho(self.con, b)}
        self.assertEqual(D(x['3334/QĐ-UBND']['so_tien']), D(20000000))
        ho_so.xoa_ho(self.con, a)
        self.assertEqual(theo_doi.ho_cua_qd(self.con, q1), [b])
        nhap_tho.xoa_trang(self.con)
        self.assertEqual(self.con.execute('SELECT COUNT(*) FROM quyet_dinh').fetchone()[0], 0)

    def test_nang_cap_v9(self):
        """File v9 (phê duyệt / chi trả ghi thẳng trên hộ) mở bằng bản mới: chuyển thành quyết định."""
        a, b = self.ma[:2]
        with self.con:
            self.con.execute("""UPDATE ho SET da_phe_duyet = 1, qd_so = '77/QĐ-UBND', qd_ngay = '01/09/2026', qd_so_tien = '5000',
                                da_chi_tra = 1, chi_tra_ngay = '02/09/2026' WHERE ma_ho IN (?, ?)""", (a, b))
            self.con.execute('DROP TABLE qd_ho')
            self.con.execute('DROP TABLE quyet_dinh')
            self.con.execute('PRAGMA user_version = 9')
        self.con.close()
        self.con = csdl.mo(self.p)
        self.assertEqual(self.con.execute('PRAGMA user_version').fetchone()[0], csdl.PHIEN_BAN_CSDL)
        ds = theo_doi.ds_quyet_dinh(self.con)
        self.assertEqual((len(ds), ds[0].so, ds[0].so_ho, ds[0].so_ho_da_nhan), (1, '77/QĐ-UBND', 2, 2))
        self.assertEqual(theo_doi.doc_qd_ho(self.con, a)[0]['chi_tra_ngay'], '02/09/2026')

    def test_xuat_excel(self):
        f = theo_doi.xuat_excel(self.td / 'x.xlsx', 'THỬ', ['A', 'B'], [[1, D('12.5')], [None, 'x']], [5, 10], [(0, 0, 1, 0)], 'DA')
        ws = openpyxl.load_workbook(f).active
        self.assertEqual((ws['A1'].value, ws['A5'].value, ws['B5'].value, ws['A2'].value), ('THỬ', 1, 12.5, 'Dự án: DA'))
        self.assertIn('A5:A6', [str(m) for m in ws.merged_cells.ranges])


class TestManHinh(CoSo):
    @classmethod
    def setUpClass(cls):
        os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
        from PySide6.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication([])

    def test_bang_tong_hop_quyet_dinh_tien_do(self):
        from pabt.man_hinh_theo_doi import KhungBangTongHop, KhungQuyetDinh, KhungTienDo
        q1, q2 = self.hai_qd()
        a, b, c = self.ma[:3]
        # Bảng tổng hợp kinh phí (0.9.76): 3 thẻ - cơ cấu, chi tiết từng hộ, đối soát khái toán; KHÔNG còn thẻ quyết định
        bth = KhungBangTongHop(self.con)
        bth.im_lang = True
        for k in bth.cac_the:
            k.im_lang = True
        self.assertEqual(bth.tab.count(), 3)
        self.assertFalse(hasattr(bth, 'quyet_dinh'))
        bth.mo_the(0)
        loai = [d['loai'] for d in bth.co_cau.cc['dong']]
        # 20/10/2026: dòng con tiền đất (đất ở / đất nông nghiệp, đất khác chỉ khi có tiền) ngay sau nhóm I
        self.assertEqual([x for x in loai if x != 'nhom_con'], ['nhom'] * 5 + ['cong', 'kinh_phi', 'phan_bo', 'phan_bo', 'tong'])
        self.assertEqual(loai[0], 'nhom')
        self.assertIn(loai.count('nhom_con'), (2, 3))
        self.assertEqual(bth.co_cau.bang.rowCount(), len(loai))
        self.assertEqual([d['stt'] for d in bth.co_cau.cc['dong'] if d['loai'] == 'nhom'], ['I', 'II', 'III', 'IV', 'V'])
        self.assertTrue(all(d.get('can_cu') for d in bth.co_cau.cc['dong']))
        self.assertEqual(sum((d['tien_pa'] for d in bth.co_cau.cc['dong'] if d['loai'] == 'nhom_con'), D(0)),
                         bth.co_cau.cc['dong'][0]['tien_pa'])                # dòng con cộng đúng tiền đất
        f = bth.co_cau.xuat(self.td / 'cc.xlsx')
        self.assertEqual(openpyxl.load_workbook(f).active['A1'].value, 'CƠ CẤU KINH PHÍ DỰ ÁN')
        bth.mo_the(1)
        self.assertEqual(bth.tien.bang.rowCount(), len(self.ma))
        self.assertIn(f'({len(self.ma)} hộ)', bth.tab.tabText(1))                       # tên thẻ ghi số hộ thật
        bth.mo_the(2)
        self.assertIsNone(bth.doi_soat.ss)                                               # chưa chọn bảng khái toán
        # quyết định: trang riêng (Nhóm 6): danh sách, chọn, thêm hộ, ghi nhận chi trả, bỏ hộ, xuất
        kq = KhungQuyetDinh(self.con)
        kq.im_lang = True
        kq.nap()
        self.assertEqual(kq.ds_qd_w.count(), 2)
        kq.ds_qd_w.setCurrentRow(1)                                     # QĐ 1234
        self.assertEqual(kq.qd_id, q1)
        self.assertIn('1234/QĐ-UBND', kq.lb_qd.text())
        n = len(self.ma)
        self.assertIn(f'Đã duyệt: 2/{n} hộ · Tổng tiền: 300.000.000 đ', kq.lb_khop.text())     # thanh khớp số liệu
        self.assertIn('KHỚP', kq.lb_khop.text())
        self.assertEqual(kq.them_ho([self.ma[3]]), 1)
        self.assertEqual(len(theo_doi.ho_cua_qd(self.con, q1)), 3)
        self.assertIn(f'Đã duyệt: 3/{n} hộ', kq.lb_khop.text())
        self.assertEqual(kq.ghi_chi_tra([a, b], '10/10/2026'), 2)
        self.assertEqual(kq.sua_ho(self.ma[3], dict(so_tien='1.234.000', da_chi_tra=False, ly_do_chua_nhan='Vắng nhà')), self.ma[3])
        self.assertEqual(D(theo_doi.doc_qd_ho(self.con, self.ma[3])[0]['so_tien']), D(1234000))
        self.assertIn('Tổng tiền: 301.234.000 đ', kq.lb_khop.text())
        self.assertIn('LỆCH', kq.lb_khop.text())                        # cộng các hộ khác tổng 300.000.000 ghi trong quyết định
        self.assertEqual(kq.bang.item(0, 3).text(), '101/PA')
        f = kq.xuat(self.td / 'qd.xlsx')
        self.assertIn('1234/QĐ-UBND', openpyxl.load_workbook(f).active['A1'].value)
        kq.bang.selectRow(0)
        self.assertEqual(kq.bo_ho(xac_nhan=True), 1)
        self.assertNotIn(a, theo_doi.ho_cua_qd(self.con, q1))
        moi = kq.sua_qd(None, dict(so='1/QĐ-UBND', ngay='01/01/2027'))
        self.assertEqual(kq.qd_id, moi)
        self.assertEqual(kq.xoa_qd(xac_nhan=True), 0)
        # tiến độ
        td = KhungTienDo(self.con)
        td.im_lang = True
        td.nap()
        td.dat_loc('chua_nhan')
        self.assertEqual(sorted(td.dang_hien), sorted([b, c, self.ma[3]]))
        td.dat_loc('chua_nhan', {q1})
        self.assertEqual(td.dang_hien, [self.ma[3]])
        self.assertIn('Vắng nhà', td.bang.item(0, td.C_CHUA).text())
        td.dat_loc('', set(), 'vang nha')
        self.assertEqual(td.dang_hien, [self.ma[3]])
        td.dat_loc('', set(), '')
        self.assertEqual(td.ban_giao([b], dict(da_ban_giao=True, ban_giao_ngay='01/11/2026')), 1)
        td.dat_loc('da_bg')
        # 1.0.03: bàn giao theo phân tích tiến độ tự động (tuần tự) - b còn quyết định chưa nhận tiền: chưa tính đã bàn giao
        self.assertEqual(td.dang_hien, [])
        qd_b = [r[0] for r in self.con.execute('SELECT qd_id FROM qd_ho WHERE ma_ho = ?', (b,))]
        theo_doi.ghi_chi_tra(self.con, [(q, b) for q in qd_b], '01/11/2026')
        td.nap()
        td.dat_loc('da_bg')
        self.assertEqual(td.dang_hien, [b])
        f = td.xuat(self.td / 'td.xlsx')
        self.assertIn('ĐÃ BÀN GIAO', openpyxl.load_workbook(f).active['A1'].value)

    def test_trang_thai_mot_ho(self):
        from pabt.man_hinh_theo_doi import HopHoTheoDoi
        q1, q2 = self.hai_qd()
        b = self.ma[1]
        d = HopHoTheoDoi(self.con, b, tong_pa=D(215000000))
        d.im_lang = True
        self.assertEqual(d.bang.rowCount(), 2)
        self.assertIn('215.000.000', d.lb_tong.text())
        self.assertNotIn('khác tổng phương án', d.lb_tong.text())
        # thêm vào quyết định mới (nhập số trong hộp)
        from pabt.man_hinh_theo_doi import HopQDHo
        h = HopQDHo(self.con, b, None, None, d, chon_qd=True)
        h.o_so_qd.setText('5555/QĐ-UBND')
        h.o_ngay_qd.setText('1/12/2026')
        q3 = h.qd_id()
        theo_doi.ghi_qd_ho(self.con, q3, b, dict(so_tien='2.000.000'))
        d.nap()
        self.assertEqual(d.bang.rowCount(), 3)
        self.assertEqual(d.sua(2, dict(so_tien='2.500.000', da_chi_tra=True, chi_tra_ngay='2/12/2026')), q3)
        self.assertEqual(d.bang.item(2, 2).text(), '2.500.000')
        self.assertTrue(d.bo(2, xac_nhan=True))
        self.assertEqual(d.bang.rowCount(), 2)
        d.o_bg.setChecked(True)
        d.o_bg_ngay.setText('3/12/2026')
        d.o_theo_doi.setPlainText('Hẹn ký biên bản')
        self.assertTrue(d.luu())
        tt = quan_ly.doc_trang_thai(self.con, b)
        self.assertEqual((tt['da_ban_giao'], tt['ban_giao_ngay'], tt['theo_doi']), (1, '03/12/2026', 'Hẹn ký biên bản'))
        d.o_bg_ngay.setText('99/99/2026')
        self.assertFalse(d.luu())                                    # ngày sai: báo lỗi, không lưu


if __name__ == '__main__':
    unittest.main()


class TestHoanTac(CoSo):
    def anh(self):
        return [[tuple(r) for r in self.con.execute(f'SELECT * FROM {b} ORDER BY rowid')]
                for b in ('ho', 'thua', 'ct_dat', 'ct_khoan', 'quyet_dinh', 'qd_ho', 'dm_taisan')]

    def test_csdl(self):
        from pabt import hoan_tac
        ht = hoan_tac.HoanTac(self.con)
        a0 = self.anh()
        self.assertFalse(ht.co_hoan_tac)
        ho_so.xoa_ho(self.con, self.ma[-1])
        ht.chot()
        a1 = self.anh()
        q1, q2 = self.hai_qd()
        ht.chot()
        self.assertEqual([b.viec for b in ht.hoan_tac_ds], ['Xóa hộ', 'Thêm quyết định'])
        self.assertEqual(ht.hoan_tac(), 'Thêm quyết định')
        self.assertEqual(self.anh(), a1)
        self.assertEqual(ht.hoan_tac(), 'Xóa hộ')                    # hộ, thửa (xóa theo khóa ngoại) trở lại đúng như cũ
        self.assertEqual(self.anh(), a0)
        self.assertEqual(ht.hoan_tac(), '')
        self.assertEqual(ht.lam_lai(), 'Xóa hộ')
        self.assertEqual(self.anh(), a1)
        self.assertTrue(ht.co_lam_lai)
        quan_ly.cap_nhat_trang_thai(self.con, [self.ma[1]], dict(theo_doi='x'))   # thao tác mới: bỏ danh sách làm lại
        ht.chot()
        self.assertFalse(ht.co_lam_lai)
        self.assertEqual(ht.hoan_tac(), 'Cập nhật trạng thái hộ')
        # danh mục bị khóa (trigger) vẫn hoàn tác được
        with self.con, csdl.mo_khoa_danh_muc(self.con):
            self.con.execute("UPDATE dm_taisan SET don_gia = '1' WHERE rowid = (SELECT MIN(rowid) FROM dm_taisan)")
            csdl.ghi_nhat_ky(self.con, 'Cập nhật bộ đơn giá')
        a2 = self.anh()
        ht.chot()
        ht.hoan_tac()
        self.assertNotEqual(self.anh(), a2)
        self.assertEqual(self.con.execute('SELECT mo FROM khoa_dm').fetchone()[0], 0)
        ht.dong()
        self.con.execute("UPDATE ho SET theo_doi = 'y'")              # sau khi đóng: không ghi lịch sử nữa
        self.con.commit()
        self.assertIsNone(hoan_tac.cua(self.con))

    def test_cua_so(self):
        os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
        from PySide6.QtWidgets import QApplication
        app = QApplication.instance() or QApplication([])  # noqa: F841
        from pabt import giao_dien
        from pabt.app import CuaSoChinh
        self.con.close()
        w = CuaSoChinh()
        w.mo(self.p, chi_doc=False)
        self.addCleanup(w.dong_du_an)
        ma = w.mo_hinh.dong[0]['ma_ho']
        ten = w.mo_hinh.dong[0]['o'][1]
        from pabt import ho_so as hs
        hs.luu_ho(w.con, ma, dict(ho_ten='Tên đã sửa'), hs.doc_ho(w.con, ma)['thua'])
        w.ht.chot()
        self.assertTrue(w.nut_ht['lui'].isEnabled())
        self.assertIn('hồ sơ hộ', w.nut_ht['lui'].toolTip())
        self.assertIn('hồ sơ hộ', w.nut_ht['lui'].text())            # menu Chỉnh sửa: "Hoàn tác: <thao tác>\tCtrl+Z"
        self.assertTrue(w.hoan_tac())
        self.assertEqual(w.mo_hinh.dong[0]['o'][1], ten)
        self.assertTrue(w.nut_ht['toi'].isEnabled())
        self.assertTrue(w.hoan_tac(lam_lai=True))
        self.assertEqual(w.mo_hinh.dong[0]['o'][1], 'Tên đã sửa')
        # cửa sổ lập phương án: hoàn tác sửa đổi chưa lưu
        lp = w.mo_lap_pa(ma, cho=False)
        lp.o_nk.setValue(7)
        self.assertEqual(lp.bo.pa.ho.nhan_khau, 7)
        self.assertTrue(lp.hoan_tac())
        self.assertNotEqual(lp.bo.pa.ho.nhan_khau, 7)
        self.assertTrue(lp.hoan_tac(lam_lai=True))
        self.assertEqual(lp.bo.pa.ho.nhan_khau, 7)
        self.assertTrue(lp.luu())
        self.assertTrue(lp.hoan_tac())                               # hết bước chưa lưu: hoàn tác lần lưu
        self.assertNotEqual(lp.bo.pa.ho.nhan_khau, 7)
        lp.close()
        # bảng thửa: hoàn tác sửa ô
        from pabt.giao_dien import BangHoanTac
        from PySide6.QtWidgets import QTableWidget, QTableWidgetItem
        b = QTableWidget(1, 1)
        b.setItem(0, 0, QTableWidgetItem('a'))
        h = BangHoanTac(b)
        b.item(0, 0).setText('b')
        self.assertTrue(h.hoan_tac())
        self.assertEqual(b.item(0, 0).text(), 'a')
        self.assertTrue(h.lam_lai())
        self.assertEqual(b.item(0, 0).text(), 'b')
        self.assertFalse(h.lam_lai())
        self.assertTrue(giao_dien._dang_go_chu(lp.o_dt_nn))


class TestDuToanDat(CoSo):
    def test_them_dat_va_khai_toan(self):
        os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
        from PySide6.QtWidgets import QApplication
        app = QApplication.instance() or QApplication([])  # noqa: F841
        from pabt import du_toan
        from pabt.man_hinh_du_toan import HopDuToan
        d = HopDuToan(None, self.con)
        d.im_lang = True
        self.assertGreater(d.cb_loai_dat.count(), 50)                              # danh sách loại đất dùng chung
        d.them_danh_muc(d.dm.muc[2][0])
        r = d.them_dat('CLN', '=10*15', '50.000')
        x = d.dt.dong[r]
        self.assertEqual((x.muc, x.ma, x.khoi_luong, x.don_gia, x.dvt), (1, 'CLN', D(150), D(50000), 'm²'))
        self.assertIn('lâu năm', x.ten)
        self.assertEqual(d.dt.dong[0].muc, 1)                                    # đất nằm trên cùng
        self.assertIsNone(d.them_dat('', '1', '1'))
        f = du_toan.xuat_khai_toan(d.dt, self.td / 'kt.xlsx')['excel']
        ws = openpyxl.load_workbook(f).active
        self.assertEqual((ws['A10'].value, ws['B10'].value), ('I', 'Bồi thường về đất'))
        # chưa có dòng đất: mục I vẫn có (0 đồng), nằm trên cùng
        dt = du_toan.DuToan()
        dt.dong.append(du_toan.DongDT(2, 'Nhà', 'm²', D(10), D(1000), D(1)))
        ws = openpyxl.load_workbook(du_toan.xuat_khai_toan(dt, self.td / 'kt2.xlsx')['excel']).active
        self.assertEqual((ws['B10'].value, ws['G10'].value), ('Bồi thường về đất', 0))
        self.assertEqual((ws['B11'].value, ws['B12'].value), ('Nhà và công trình xây dựng', 'Nhà'))

    def test_danh_sach_cay_du(self):
        os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
        from PySide6.QtWidgets import QApplication
        app = QApplication.instance() or QApplication([])  # noqa: F841
        from pabt.giao_dien import OTimChon
        o = OTimChon()
        o.dat_muc([(f'Cây số {i}', i) for i in range(2500)])
        o.xem_tat_ca()
        self.assertEqual(o.ds.count(), 2500)                                    # không còn cắt ở 300 mục

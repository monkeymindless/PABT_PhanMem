"""Đồng bộ các màn hình theo đặc tả + ảnh mẫu người dùng 20/10/2026: cửa sổ lập phương án (dải định danh hộ, chân bảng mục, chọn
từng ô), Bảng tổng hợp kinh phí (5 thẻ KPI, cơ cấu I-VI + căn cứ, đối soát + khung an toàn nguồn vốn), Tiến độ (6 thẻ KPI, sổ nhật ký
vận động bên phải, đánh giá điều kiện cưỡng chế), Trung tâm xuất bản (hai thẻ chế độ, 4 tài liệu), Bác sĩ CSDL (5 chỉ số, bảo trì
1-click). Dữ liệu GIẢ LẬP (tests.test_toc_do._du_an)."""
from __future__ import annotations
import json
import os
import tempfile
import time
import unittest
from datetime import date, timedelta
from pathlib import Path
from unittest import mock

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

from pabt import chua_benh_csdl, csdl, kinh_phi_du_an, theo_doi, thoi_han, van_dong  # noqa: E402
from pabt.tien import D, KHONG  # noqa: E402
from tests.test_toc_do import _du_an  # noqa: E402


def _qt():
    from PySide6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


def _hn(n: int) -> str:
    return (date.today() + timedelta(days=n)).strftime('%d/%m/%Y')


class _Co(unittest.TestCase):
    def setUp(self):
        _qt()
        self.tmp = tempfile.TemporaryDirectory()
        self.td = Path(self.tmp.name)
        self.p = _du_an(self.td, 6)
        self.con = csdl.mo(self.p)
        self.ma = [r[0] for r in self.con.execute('SELECT ma_ho FROM ho ORDER BY thu_tu')]

    def tearDown(self):
        self.doCleanups()                               # đóng cửa sổ / kết nối trước khi xóa thư mục tạm (Windows giữ khóa file)
        try:
            self.con.close()
        except Exception:                               # đã đóng trong bài (bảo trì file)
            pass
        self.tmp.cleanup()

    def qd(self, so_ho: int = 4) -> int:
        q = theo_doi.luu_qd(self.con, None, '9/QĐ-UBND', _hn(-30), 'Phê duyệt thử')
        theo_doi.them_ho_theo_pa(self.con, q, self.ma[:so_ho])
        return q


# ---------------------------------------------------------------- nghiệp vụ (không Qt)
class TestNghiepVu(_Co):
    def test_danh_gia_chenh(self):
        self.assertEqual(kinh_phi_du_an.danh_gia_chenh(D(100), D(89)), ('Tiết kiệm 11,0%', 'dat'))
        self.assertEqual(kinh_phi_du_an.danh_gia_chenh(D(100), D(100)), ('Trong hạn mức', 'dat'))
        self.assertEqual(kinh_phi_du_an.danh_gia_chenh(D(100), D(102.4)), ('Tăng 2,4%', 'loi'))
        self.assertEqual(kinh_phi_du_an.danh_gia_chenh(D(0), D(5))[1], 'loi')
        self.assertEqual(kinh_phi_du_an.danh_gia_chenh(None, None), ('—', 'tin'))

    def test_co_cau_chi_tiet_dat_va_can_cu(self):
        thuong = kinh_phi_du_an.co_cau(self.con)
        self.assertNotIn('nhom_con', [d['loai'] for d in thuong['dong']])           # mặc định: không đổi cấu trúc cũ
        cc = kinh_phi_du_an.co_cau(self.con, chi_tiet_dat=True)
        con = [d for d in cc['dong'] if d['loai'] == 'nhom_con']
        self.assertGreaterEqual(len(con), 2)
        self.assertEqual(sum((d['tien_pa'] for d in con), KHONG), cc['dong'][0]['tien_pa'])
        self.assertEqual([d['stt'] for d in cc['dong'] if d['loai'] == 'nhom'], ['I', 'II', 'III', 'IV', 'V'])
        self.assertEqual(next(d for d in cc['dong'] if d['loai'] == 'kinh_phi')['stt'], 'VI')
        self.assertTrue(all(d['can_cu'] for d in cc['dong']))
        self.assertIn('08/2025', next(d for d in cc['dong'] if d['loai'] == 'kinh_phi')['can_cu'])
        pb = [d for d in cc['dong'] if d['loai'] == 'phan_bo']
        self.assertEqual([d['ty_le_phan_bo'] for d in pb], [D(85), D(15)])

    def test_can_cu_co_cau_ho_so_dia_phuong_ghi_de(self):
        with mock.patch('pabt.dia_phuong.lay', return_value={'2': 'QĐ đơn giá nhà giả lập'}):
            cc = kinh_phi_du_an.can_cu_co_cau()
        self.assertEqual(cc[2], 'QĐ đơn giá nhà giả lập')
        self.assertEqual(cc[1], kinh_phi_du_an.CAN_CU_CO_CAU[1])

    def test_danh_gia_cuong_che(self):
        self.qd(2)
        ma = self.ma[0]
        ds = {x.ma_ho: x for x in theo_doi.tong_hop(self.con, tinh_pa=False)}
        thoi_han.dat_ngay_thong_bao(self.con, _hn(-200))
        moc = thoi_han.moc_thu_hoi_tat_ca(self.con).get(ma)
        n = thoi_han.so_ngay(self.con, 'van_dong')
        dg = van_dong.danh_gia_cuong_che(ds[ma], [], n, date.today(), moc)
        self.assertFalse(dg['du'])
        self.assertIn('Chưa có buổi vận động', ' '.join(c for _, c in dg['dong']))
        van_dong.ghi_buoi(self.con, ma, 'tien', _hn(-(n + 5)), 'Họp tổ', 'Tổ vận động', 'Nội dung', 'chua_dong_y')
        dg = van_dong.danh_gia_cuong_che(ds[ma], van_dong.ds_buoi(self.con, ma), n, date.today(), moc)
        self.assertTrue(dg['du'], dg)
        self.assertIn('ĐỦ ĐIỀU KIỆN', dg['ket_luan'])
        self.assertEqual(len(dg['dong']), 4)
        dg = van_dong.danh_gia_cuong_che(ds[ma], van_dong.ds_buoi(self.con, ma), n, date.today(), None)
        self.assertFalse(dg['du'])                                           # chưa kiểm được mốc thông báo thu hồi

    def test_sua_tep_tung_viec(self):
        self.con.close()
        with self.assertRaises(chua_benh_csdl.LoiSuaTep):
            chua_benh_csdl.sua_tep_pabt(self.p, viec='go_khoa')               # không có tệp khóa
        with self.assertRaises(chua_benh_csdl.LoiSuaTep):
            chua_benh_csdl.sua_tep_pabt(self.p, viec='cuu')                   # file tốt: không cần cứu
        with self.assertRaises(chua_benh_csdl.LoiSuaTep):
            chua_benh_csdl.sua_tep_pabt(self.p, viec='nang_cap')              # đã v mới nhất
        kq = chua_benh_csdl.sua_tep_pabt(self.p, viec='toi_uu', thu_muc_sao_luu=self.td / 'sl')
        self.assertTrue(kq['thanh_cong'])
        self.assertIn('REINDEX', ' '.join(kq['hanh_dong']))
        k = Path(str(self.p) + '.khoa')
        k.write_text(json.dumps(dict(may='MAY-CU', nguoi='thử', mo_luc=time.time() - 9999, cap_nhat=time.time() - 9999)),
                     encoding='utf-8')
        kq = chua_benh_csdl.sua_tep_pabt(self.p, viec='go_khoa')
        self.assertFalse(k.exists())
        self.assertEqual(kq['ban_sao_luu'], '')                                # gỡ khóa không sao lưu / không đụng dữ liệu
        self.con = csdl.mo(self.p)


# ---------------------------------------------------------------- cửa sổ lập phương án
class TestCuaSoLapPA(_Co):
    def test_dai_dinh_danh_chan_bang_va_chon_o(self):
        from PySide6.QtWidgets import QAbstractItemView
        from pabt import man_hinh
        w = man_hinh.CuaSoLapPA(self.con, self.ma[0])
        self.addCleanup(lambda: (w.bo_thay_doi(), w.close()))
        self.assertEqual(w.dai_dinh_danh.height() or w.dai_dinh_danh.maximumHeight(), man_hinh.CAO_DAI_DINH_DANH)
        ten = self.con.execute('SELECT ho_ten FROM ho WHERE ma_ho = ?', (self.ma[0],)).fetchone()[0]
        self.assertEqual(w.dd['ten'][1].text(), ten)
        self.assertEqual(w.dd['dot'][1].text(), 'Chưa xếp đợt')
        self.assertTrue(w.lb_tong_dd.text().endswith('đ'))
        bm = w.bang[1]
        self.assertIn('Tổng số:', bm.lb_dem.text())
        self.assertIn('CỘNG MỤC 1', bm.lb_tong.text())
        self.assertEqual(bm._bang.selectionBehavior(), QAbstractItemView.SelectionBehavior.SelectItems)
        self.assertIn('(', w.tab.tabText(1))
        self.assertFalse(w.lb_tb.isVisibleTo(w))                               # thông báo trống: không chiếm chỗ


# ---------------------------------------------------------------- bảng tổng hợp kinh phí
class TestBangTongHop(_Co):
    def test_5_kpi_va_khung_an_toan_von(self):
        from pabt.man_hinh_theo_doi import KhungBangTongHop
        k = KhungBangTongHop(self.con)
        k.im_lang = True
        self.addCleanup(k.close)
        for w in (k, *k.cac_the):
            w.im_lang = True
        k.nap()
        self.assertEqual(list(k.hang_kpi.the), ['cong', 'kinh_phi', 'pb_0', 'pb_1', 'tong'])
        self.assertIn('85%', k.hang_kpi.the['pb_0'].lb_ten.text())
        self.assertIn('15%', k.hang_kpi.the['pb_1'].lb_ten.text())
        self.assertNotIn('thẩm định', k.hang_kpi.the['pb_1'].lb_ten.text().lower())   # nhãn theo hồ sơ địa phương (UBND cấp xã)
        self.assertIn('Lần tính toán gần nhất', k.lb_chan.text())
        self.assertIs(k.tab.widget(0), k.the_1)                                 # thẻ 1 = cơ cấu | an toàn nguồn vốn
        self.assertEqual(k.co_cau.COT[0], 'STT')
        self.assertEqual(k.co_cau.COT[-1], 'Căn cứ pháp lý áp dụng')
        self.assertIn('Chưa', k.an_toan.the_trang_thai.text())                  # chưa chọn khái toán
        from pabt import du_toan
        k.doi_soat.dung_dang_mo(du_toan.tu_du_an(self.con))                    # khái toán = thực tế
        k.an_toan.ve()
        self.assertEqual(k.an_toan.the_trang_thai.text(), 'Nguồn vốn an toàn')
        self.assertIn('Kết luận kiểm toán', k.an_toan.lb_tom_tat.text())
        self.assertEqual(k.doi_soat.COT[-1], 'Đánh giá')


# ---------------------------------------------------------------- tiến độ
class TestTienDo(_Co):
    def test_6_kpi_va_so_van_dong(self):
        q = self.qd(3)
        van_dong.ghi_buoi(self.con, self.ma[0], 'tien', _hn(-2), 'Họp tổ', 'Tổ vận động', 'Giải thích phương án', 'chua_dong_y')
        from pabt.man_hinh_theo_doi import KhungTienDo
        k = KhungTienDo(self.con)
        k.im_lang = True
        self.addCleanup(k.close)
        k.nap()
        self.assertEqual(list(k.kpi.the), ['tong_ho', 'phe_duyet', 'giai_ngan', 'mat_bang', 'van_dong', 'cuong_che'])
        self.assertEqual(k.kpi.the['tong_ho'].lb_so.text(), '6 hộ')
        self.assertEqual(k.kpi.the['phe_duyet'].lb_so.text(), '3 hộ (50,0%)')
        self.assertTrue(k.kpi.the['van_dong'].lb_so.text().startswith('1 hộ'))
        self.assertIn('ngày', k.kpi.the['van_dong'].lb_td.text())      # 22/10/2026: tên thẻ chữ thường kiểu câu
        self.assertIs(k.nut['Sổ nhật ký vận động…'], k.so_vd.b_mo)
        self.assertIs(k.tach_vd.widget(1), k.so_vd)
        i = next(r for r in range(k.bang.rowCount()) if k.bang.ma_dong(r) == self.ma[0])
        k.bang.setCurrentIndex(k.bang.model().index(i, 1))
        self.assertIn('Buổi 1', k.so_vd.lb_buoi.text())
        self.assertTrue(k.so_vd.lb_kl.isVisibleTo(k.so_vd))
        self.assertIn('KẾT QUẢ ĐÁNH GIÁ', k.so_vd.lb_kl.text())
        self.assertFalse(k.so_vd.dg['du'])                                     # mới vận động 2 ngày
        k.bam_kpi('phe_duyet')
        self.assertEqual(sorted(k.dang_hien), sorted(self.ma[:3]))
        d = k.so_van_dong(self.ma[0])                                          # im_lang: trả hộp, không hiện
        self.addCleanup(d.close)
        self.assertIn('KẾT QUẢ ĐÁNH GIÁ', d.lb_kl.text())
        self.assertIsNotNone(q)


# ---------------------------------------------------------------- trung tâm xuất bản
class TestHopIn(_Co):
    def test_hai_the_che_do_va_4_tai_lieu(self):
        from pabt.man_hinh import THE_CHE_DO, HopIn
        h = HopIn(self.con, None, ma_ho_chon=self.ma[:2], file_du_an=self.p, che_do='du_thao')
        self.addCleanup(h.close)
        self.assertEqual([h.the_che_do.tabText(i) for i in range(h.the_che_do.count())], [t for _, t in THE_CHE_DO])
        self.assertEqual(h.the_che_do.currentIndex(), 0)
        self.assertFalse(h.r_du_thao.isVisibleTo(h))                            # radio cũ ẩn, vẫn là nguồn trạng thái
        self.assertIn('DỰ THẢO', h.lb_quy_tac.text())
        self.assertFalse(h.o_tt.isEnabled() or h.o_bc.isEnabled())              # dự thảo: khóa tờ trình + báo cáo tiếp thu
        self.assertEqual(h.the_tai_lieu[h.o_tt].text(), 'Chỉ mở ở Chính thức')
        self.assertIn('85/15', h.the_tai_lieu[h.o_bth].text())
        self.assertIn('(2 hộ)', h.b_thuc_hien.text())
        self.assertFalse(h.o_che_cccd.isChecked() or h.o_che_cccd.isVisibleTo(h))   # 1.0.04: không che CCCD
        h.the_che_do.setCurrentIndex(1)                                         # bấm thẻ Chính thức
        self.assertEqual(h.che_do(), 'chinh_thuc')
        self.assertTrue(all(o.isChecked() and o.isEnabled() for o in (h.o_ct, h.o_bth, h.o_tt, h.o_bc)))
        self.assertIn('trọn bộ 4 tài liệu', h.lb_quy_tac.text())
        h.r_du_thao.setChecked(True)                                            # đặt bằng mã: thẻ đổi theo
        self.assertEqual(h.the_che_do.currentIndex(), 0)
        self.assertFalse(h.o_bc.isChecked())


# ---------------------------------------------------------------- bác sĩ CSDL
class TestBacSi(_Co):
    def test_5_chi_so_va_bao_tri(self):
        from pabt.man_hinh_chan_doan import CHI_SO, HopChanDoanHeThong
        dong, mo = [], []
        h = HopChanDoanHeThong(None, self.p, dong_du_an=lambda: dong.append(1) or self.con.close(), mo_lai=lambda f: mo.append(f),
                               im_lang=True)
        self.addCleanup(h.close)
        cs = h.chi_so()
        self.assertEqual(list(cs), [k for k, _ in CHI_SO])
        self.assertEqual(cs['khoa'], ('Không bị kẹt khóa', 'xanh'))
        self.assertEqual(cs['toan_ven'], ('OK (0 trang lỗi)', 'xanh'))
        self.assertEqual(cs['khoa_ngoai'], ('Khớp 100%', 'xanh'))
        self.assertEqual(cs['luoc_do'][0], f'v{csdl.PHIEN_BAN_CSDL} (chuẩn phần mềm)')        # phiên bản THẬT, không ghi cứng v16
        self.assertIn('nang_cap', h.nut_bao_tri)
        self.assertIn(f'v{csdl.PHIEN_BAN_CSDL}', h.nut_bao_tri['nang_cap'].text())
        self.assertFalse(h.nut_bao_tri['nang_cap'].isEnabled())
        self.assertFalse(h.nut_bao_tri['cuu'].isEnabled())
        self.assertFalse(h.nut_bao_tri['go_khoa'].isEnabled())
        self.assertTrue(h.nut_bao_tri['toi_uu'].isEnabled())
        kq = h.bao_tri('toi_uu')
        self.assertTrue(kq['thanh_cong'])
        self.assertEqual((dong, len(mo)), ([1], 1))                             # đóng dự án trước, mở lại sau
        self.assertIsNone(h.bao_tri('cuu'))                                     # file tốt: LoiSuaTep đã báo (im lặng), không làm
        self.assertTrue(h.b_goi.text().startswith('Xuất gói chẩn đoán ẩn danh'))
        self.assertLessEqual(h.minimumSizeHint().width(), 1024)
        self.con = csdl.mo(self.p)

    def test_khoa_ket_va_luoc_do_cu(self):
        from pabt.man_hinh_chan_doan import HopChanDoanHeThong
        self.con.close()
        k = Path(str(self.p) + '.khoa')
        k.write_text(json.dumps(dict(may='MAY-CU', nguoi='thử', mo_luc=time.time() - 9999, cap_nhat=time.time() - 9999)),
                     encoding='utf-8')
        import sqlite3
        c = sqlite3.connect(str(self.p))
        c.execute(f'PRAGMA user_version = {csdl.PHIEN_BAN_CSDL - 1}')
        c.commit()
        c.close()
        h = HopChanDoanHeThong(None, self.p, im_lang=True)
        self.addCleanup(h.close)
        cs = h.chi_so()
        self.assertEqual(cs['khoa'], ('Khóa cũ bị kẹt', 'do'))
        self.assertIn('cần nâng cấp', cs['luoc_do'][0])
        self.assertTrue(h.nut_bao_tri['go_khoa'].isEnabled() and h.nut_bao_tri['nang_cap'].isEnabled())
        h.bao_tri('go_khoa')
        self.assertFalse(k.exists())
        kq = h.bao_tri('nang_cap')
        self.assertTrue(kq['thanh_cong'])
        self.assertEqual(h.chi_so()['luoc_do'][0], f'v{csdl.PHIEN_BAN_CSDL} (chuẩn phần mềm)')
        self.con = csdl.mo(self.p)


if __name__ == '__main__':
    unittest.main()

"""1.0.32 (người dùng 28/10/2026, giai đoạn A): --khung-windows mở giao diện, tương phản nút menu tắt, co giãn cả 'pt' khi A+ / A−,
tiêu đề trang không nằm trong bố cục, báo nổi khi Ctrl+Tab, kiểu chữ có bộ chọn, Trả bớt hộ đã nhận + Nhật ký máy chủ, một nguồn twip /
thoát XML (openxml_word), nhãn vị trí theo mô hình của tỉnh ở hộp Tra bảng giá đất. Dữ liệu giả lập."""
from __future__ import annotations
import re
import shutil
import unittest
from pathlib import Path
from unittest import mock

from pabt import csdl, giao_dien, in_word, may_chu, openxml_word, van_ban_trinh
from tests import APP
from tests.test_may_chu import _Nen

CO_QT = APP is not None


class TestDongLenh(unittest.TestCase):
    def test_khung_windows_mo_giao_dien(self):
        import chay
        with mock.patch('pabt.app.main', return_value=0) as mo:
            self.assertEqual(chay.main(['--khung-windows']), 0)
        mo.assert_called_once()


class TestGiaoDien(unittest.TestCase):
    def test_nut_menu_tat_du_tuong_phan(self):
        qss = giao_dien._qss_menu_trai()
        self.assertIn(f'QToolButton[menu="1"]:disabled {{ color: {giao_dien.MAU_MENU_TAT};', qss)     # 1.0.34: menu nền tối
        self.assertNotIn('#A8B3BF', qss)

    def test_co_gian_px_va_pt(self):
        q = 'QLabel { font-size: 10.5pt; padding: 6px; } QToolButton { font-size: 14.5pt; }'
        self.assertEqual(giao_dien._co_gian(q, 1), q)                     # 100%: giữ nguyên chuỗi gốc
        moi = giao_dien._co_gian(q, 1.2)
        self.assertIn('font-size: 12.6pt', moi)
        self.assertIn('font-size: 17.4pt', moi)
        self.assertIn('padding: 7px', moi)
        self.assertEqual(giao_dien._co_gian('a { width: 10pts; }', 2), 'a { width: 10pts; }')   # chỉ đơn vị pt trọn

    @unittest.skipUnless(CO_QT, 'không có Qt')
    def test_kiem_thu_khong_doc_ty_le_cua_may(self):
        # 1.0.33: kiểm hàm đọc / ghi - không bo_ap_dung / ap_dung lại cả ứng dụng (áp bảng kiểu cho mọi widget còn sống của lượt kiểm
        # thử: lượt đầy đủ chậm hàng chục phút)
        from PySide6.QtCore import QSettings
        with mock.patch.object(QSettings, 'value', return_value='1.3'):
            self.assertEqual(giao_dien.ty_le_da_luu(), 1.0)        # máy đặt 130%: lượt kiểm thử (offscreen) vẫn 100%
        with mock.patch.object(QSettings, 'setValue') as ghi:
            self.assertFalse(giao_dien.luu_ty_le(1.1))              # offscreen: không ghi máy thật
        ghi.assert_not_called()
        import inspect
        self.assertIn('ty_le_da_luu()', inspect.getsource(giao_dien.ap_dung))
        self.assertIn('luu_ty_le(t)', inspect.getsource(giao_dien.dat_ty_le))

    def test_khong_con_kieu_chu_khong_bo_chon(self):
        goc = Path(__file__).resolve().parents[1] / 'pabt'
        for f in ('man_hinh_don_gia.py', 'man_hinh_may_chu.py'):
            self.assertIsNone(re.search(r"setStyleSheet\('color:", (goc / f).read_text(encoding='utf-8')), f)


@unittest.skipUnless(CO_QT, 'không có Qt')
class TestCuaSoChinh(unittest.TestCase):
    def test_tieu_de_trang_ngoai_bo_cuc_va_bao_ctrl_tab(self):
        from pabt.app import CuaSoChinh
        w = CuaSoChinh()
        try:
            self.assertFalse(w.lb_trang.isVisible())
            self.assertIs(w.lb_trang.parent(), w)
            lo = w.ngan_lv.parentWidget().layout()
            self.assertEqual(lo.indexOf(w.lb_trang), -1)
            bao = []
            with mock.patch('pabt.giao_dien.thong_bao_noi', side_effect=lambda cs, chu, *a, **k: bao.append(chu)):
                w._tab_ke(1)                                               # một màn hình: không báo
                self.assertEqual(bao, [])
                w.mo_trang(1)
                w.mo_trang(4)                                              # Khái toán: thêm một màn hình trong danh sách
                self.assertEqual(w.thanh_tab.count(), 2)
                w._tab_ke(1)
            self.assertEqual(len(bao), 1)
            self.assertIn(f'màn hình {w.thanh_tab.currentIndex() + 1}/2', bao[0])
            self.assertIn(w.thanh_tab.tabText(w.thanh_tab.currentIndex()).replace('&&', '&'), bao[0])
        finally:
            w.close()
            w.deleteLater()


class TestOpenXml(unittest.TestCase):
    def test_mot_nguon(self):
        self.assertIs(in_word.twip, openxml_word.twip)
        self.assertIs(van_ban_trinh._xml, openxml_word.thoat)
        self.assertEqual(van_ban_trinh._xml('a & <b>\nc'), 'a &amp; &lt;b&gt;</w:t><w:br/><w:t xml:space="preserve">c')
        self.assertEqual(van_ban_trinh._xml('x\x0by'), 'xy')                  # ký tự điều khiển: Word báo file hỏng


@unittest.skipUnless(CO_QT, 'không có Qt')
class TestViTriGiaDat(unittest.TestCase):
    def test_nhan_vi_tri_theo_mo_hinh(self):
        from pabt import gia_dat_nq28 as nq
        from pabt.man_hinh_gia_dat import HopTraGiaDat
        h = HopTraGiaDat(None, 'Trị An', 'ONT', chi_xem=True)
        self.assertIn(h.bang.item(0, 4).text(), nq.MO_HINH_VI_TRI['DONG_NAI_NQ28'])     # Đồng Nai: mã như cũ
        h.close()
        dong = [dict(xa='Xã Thử', tt=1, ten_duong='Đường A', diem_dau='a', diem_cuoi='b', vi_tri=v, dat_o=1000) for v in ('VT1', 'VT2')]
        with mock.patch.object(nq, 'mo_hinh_vi_tri', return_value='VI_TRI_1_4'), mock.patch.object(nq, 'tat_ca', return_value=dong), \
                mock.patch.object(nq, 'tim', return_value=dong):
            h = HopTraGiaDat(None, '', 'ONT', chi_xem=True)
            self.assertEqual(h.bang.item(0, 4).text(), nq.ten_vi_tri('VT1'))
            self.assertNotEqual(nq.ten_vi_tri('VT1'), 'VT1')
            self.assertTrue(h.bang.item(0, 0).font().bold())                   # vị trí đầu của mô hình tô đậm
            self.assertFalse(h.bang.item(1, 0).font().bold())
            h.close()


class TestTraBotHo(_Nen):
    def setUp(self):
        super().setUp()
        from tests.test_toc_do import _du_an
        tm = may_chu.thu_muc_du_an(self.goc)
        tm.mkdir(parents=True, exist_ok=True)
        self.f = Path(shutil.move(str(_du_an(self.td, 5)), str(tm / 'DA.pabt')))
        self.qt = may_chu.dang_nhap(self.goc, 'quantri', 'matkhau1')

    @unittest.skipUnless(CO_QT, 'không có Qt')
    def test_tra_bot_gop_len_va_bo_khoa(self):
        from pabt.man_hinh_may_chu import HopDuAnMayChu
        bs = may_chu.lay_ve_theo_ho(self.f, [1, 2, 3], self.qt)
        con = csdl.mo(bs)
        with con:
            con.execute("UPDATE ho SET ghi_chu = 'sửa offline' WHERE ma_ho IN (2, 3)")
        con.close()
        d = HopDuAnMayChu()
        d.im_lang = True
        x = next(y for y in d.ds_off if Path(y['ban_sao']) == bs)
        self.assertIsNone(d.tra_bot_ho(x, ds_ma_ho=[5]))                       # hộ không thuộc bản này: không gộp
        kq = d.tra_bot_ho(x, ds_ma_ho=[2])
        self.assertEqual(kq['so_ho'], 1)
        self.assertEqual(may_chu.ho_nhan_viec(bs), frozenset({1, 3}))         # bản offline còn giữ hộ 1, 3
        self.assertEqual(set(may_chu.ds_ho_dang_lay_ve(self.f, self.goc)), {1, 3})
        con = csdl.mo(self.f, chi_doc=True)
        gc = dict(con.execute('SELECT ma_ho, ghi_chu FROM ho').fetchall())
        con.close()
        self.assertEqual((gc[2], gc[3] != 'sửa offline'), ('sửa offline', True))  # hộ 2 đã gộp, hộ 3 chưa
        x = next(y for y in d.ds_off if Path(y['ban_sao']) == bs)
        d.tra_bot_ho(x, ds_ma_ho=[1, 3])                                       # trả hết: sổ nhận về không còn bản này
        self.assertIsNone(may_chu.ho_nhan_viec(bs))
        self.assertEqual(may_chu.ds_ho_dang_lay_ve(self.f, self.goc), {})
        bao = []
        d.bao = lambda chu, loi=True: bao.append(chu)
        d.tra_bot_ho(dict(ban_sao=str(self.td / 'ca_du_an.pabt')))             # bản cả dự án: hướng dẫn dùng nút khác
        self.assertIn('CẢ dự án', bao[-1])
        d.close()

    @unittest.skipUnless(CO_QT, 'không có Qt')
    def test_hop_chon_che_do_tra_va_nhat_ky(self):
        from pabt.man_hinh_may_chu import HopChonHoLayVe, HopDuAnMayChu
        bs = may_chu.lay_ve_theo_ho(self.f, [1, 4], self.qt)
        ds = [h for h in may_chu.ds_ho_de_chon(bs, goc=False) if h['ma_ho'] in (1, 4)]
        self.assertTrue(all(h['giu'] is None for h in ds))                     # goc=False: không hỏi máy chủ
        h = HopChonHoLayVe(bs, None, ds=ds, tra=True)
        h.im_lang = True
        self.assertIn('Trả bớt', h.windowTitle())
        h.chon_dang_hien(True)
        self.assertEqual(h.ds_chon(), [1, 4])
        self.assertIn('trả 2 hộ', h.b_ok.text())
        h.close()
        d = HopDuAnMayChu()
        d.im_lang = True
        hop = d.nhat_ky(hien=False)
        chu = hop.findChild(__import__('PySide6.QtWidgets', fromlist=['QPlainTextEdit']).QPlainTextEdit).toPlainText()
        self.assertIn('Thời gian\tTài khoản', chu)
        self.assertIn('quantri', chu)
        hop.close()
        d.close()


if __name__ == '__main__':
    unittest.main()

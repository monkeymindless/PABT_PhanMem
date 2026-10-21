"""0.9.24 theo đặc tả ARCH-PABT-2026-V4 (lo_trinh_huong_dan_pabt3.txt, 11/10/2026): cổng chờ bản quyền, KieuNut, chặn tín
hiệu, ô tìm chờ 200 ms, che số CCCD (NĐ 13/2023), ghi file nguyên tử, chỉ mục dự án máy chủ LAN, Lưu dự án (Ctrl+S), thanh
trạng thái, bộ cài phổ quát. Số liệu GIẢ LẬP."""
from __future__ import annotations
import os
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from pabt import an_toan, ban_quyen, csdl
from tests.test_toc_do import _du_an

GOC = Path(__file__).resolve().parents[1]


class TestBanQuyenVaCCCD(unittest.TestCase):
    def test_cong_cho_ban_quyen(self):
        self.assertTrue(ban_quyen.kiem_tra_ban_quyen())                 # giai đoạn này luôn hợp lệ (mục 12.2)
        self.assertIn('Tiêu chuẩn', ban_quyen.mo_ta())

    def test_che_cccd(self):
        # 1.0.04: bỏ che CCCD - luôn trả nguyên chuỗi
        self.assertEqual(an_toan.che_cccd('075092001234'), '075092001234')
        self.assertEqual(an_toan.che_cccd('CMND 271234567 - Ngày cấp: 01/01/2010'), 'CMND 271234567 - Ngày cấp: 01/01/2010')
        self.assertFalse(an_toan.can_che_cccd(None))
        self.assertEqual(an_toan.che_cccd(''), '')
        self.assertEqual(an_toan.che_cccd('Ấp 1, số 12'), 'Ấp 1, số 12')            # số ngắn (không phải số định danh): giữ


class CoSo(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)               # đăng ký trước: chạy SAU cùng (sau khi cửa sổ đã đóng, nhả file dự án)
        self.td = Path(self.tmp.name)
        cu = os.environ.get('PABT_THU_MUC_MAY')
        self.addCleanup(lambda: os.environ.pop('PABT_THU_MUC_MAY', None) if cu is None
                        else os.environ.__setitem__('PABT_THU_MUC_MAY', cu))
        os.environ['PABT_THU_MUC_MAY'] = str(self.td / 'may')


class TestGhiNguyenTu(CoSo):
    def test_tao_du_an_loi_giua_chung_giu_file_cu(self):
        from pabt import du_an_moi
        p = _du_an(self.td, 3)
        cu = p.read_bytes()
        with mock.patch.object(du_an_moi, 'tu_lap_phuong_an', side_effect=RuntimeError('mất điện giả lập')):
            with self.assertRaises(RuntimeError):
                du_an_moi.tao_du_an(p, dict(ten='Mới', cap_dia_ban='Xã', ten_dia_ban='Thử', nam='2026'),
                                    [dict(ho_ten='A', dia_chi='Ấp 1', so_to='1', so_thua='1', loai_dat='ONT', dt_thu_hoi='10',
                                          vi_tri='1')], [dict(loai_dat='ONT', vi_tri='1', gia='1000')])
        self.assertEqual(p.read_bytes(), cu)                                  # trước 0.9.24: file cũ đã bị xóa từ đầu
        self.assertFalse(any(f.name.endswith('.dang_tao') for f in self.td.iterdir()))

    def test_tao_du_an_thay_file_cu(self):
        p = _du_an(self.td, 3)
        _du_an(self.td, 5)                                                    # cùng tên a.pabt: thay bằng dự án mới
        con = csdl.mo(p)
        try:
            self.assertEqual(con.execute('SELECT COUNT(*) FROM ho').fetchone()[0], 5)
        finally:
            con.close()
        self.assertFalse(Path(str(p) + '.dang_tao').exists())

    def test_luu_thanh_ghi_de(self):
        from pabt import quan_ly
        p = _du_an(self.td, 3)
        dich = self.td / 'sao' / 'b.pabt'
        dich.parent.mkdir()
        dich.write_bytes(b'cu')
        con = csdl.mo(p)
        try:
            quan_ly.luu_thanh(con, dich)
        finally:
            con.close()
        c2 = sqlite3.connect(dich)
        self.assertEqual(c2.execute('SELECT COUNT(*) FROM ho').fetchone()[0], 3)
        c2.close()


class TestChiMucMayChu(CoSo):
    def test_khong_mo_lai_file_khong_doi(self):
        from pabt import may_chu
        goc = self.td / 'may_chu'
        tm = goc / may_chu.THU_MUC_DU_AN
        tm.mkdir(parents=True)
        import shutil
        shutil.copy2(_du_an(self.td, 2), tm / 'du_an_1.pabt')
        with mock.patch.object(may_chu, '_mo', side_effect=lambda g: _CoNoiGia()):
            ds = may_chu.ds_du_an(goc)
            self.assertEqual(ds[0]['ten'], 'Thử')
            self.assertTrue((tm / may_chu.CHI_MUC).exists())
            goc_ket_noi = sqlite3.connect
            dem = []
            with mock.patch.object(may_chu.sqlite3, 'connect', side_effect=lambda *a, **k: dem.append(a) or goc_ket_noi(*a, **k)):
                self.assertEqual(may_chu.ds_du_an(goc)[0]['ten'], 'Thử')
                self.assertEqual(dem, [])                                    # file không đổi: không mở qua mạng
                os.utime(tm / 'du_an_1.pabt', None)                          # file đổi: đọc lại
                may_chu.ds_du_an(goc)
                self.assertEqual(len(dem), 1)


class _CoNoiGia:
    """Kết nối CSDL máy chủ giả: bảng lay_ve trống."""

    def execute(self, *a):
        return []

    def close(self):
        pass


class TestGiaoDien(CoSo):
    @classmethod
    def setUpClass(cls):
        os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
        from PySide6.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication([])

    def test_kieu_nut_va_chan_tin_hieu(self):
        from PySide6.QtWidgets import QComboBox, QPushButton
        from pabt import giao_dien
        b = QPushButton('Xóa')
        giao_dien.ap_kieu_nut(b, giao_dien.KieuNut.NGUY_HIEM)
        self.assertEqual(b.property('bien_the'), 'danger')
        self.assertIn('[bien_the="danger"]', giao_dien._qss_kieu_nut())
        cb = QComboBox()
        doi = []
        cb.currentIndexChanged.connect(doi.append)
        with giao_dien.chan_tin_hieu(cb):
            cb.addItems(['a', 'b'])
            cb.setCurrentIndex(1)
        self.assertEqual(doi, [])
        self.assertFalse(cb.signalsBlocked())                                # trả lại trạng thái cũ
        self.assertEqual(giao_dien.TOKEN['chinh'], '#0F3866')

    def test_o_tim_cho_ngung_go(self):
        from PySide6.QtCore import QEventLoop, QTimer
        from pabt.giao_dien import OTimKiemThongMinh

        class QTest:                                    # PySide2 (bản Win7) không có QTest.qWait
            @staticmethod
            def qWait(ms):
                vong = QEventLoop()
                QTimer.singleShot(ms, vong.quit)
                vong.exec()
        o = OTimKiemThongMinh()
        nhan = []
        o.chuoi_da_doi.connect(nhan.append)
        for ch in ('n', 'ng', 'ngu', 'nguy'):                               # gõ liên tục: chưa lọc
            o.setText(ch)
        self.assertEqual(nhan, [])
        QTest.qWait(OTimKiemThongMinh.CHO_MS + 150)
        self.assertEqual(nhan, ['nguy'])                                       # ngừng gõ 200 ms: lọc MỘT lần
        o.setText(' x ')
        o.phat_ngay()
        self.assertEqual(nhan[-1], 'x')

    def test_cua_so_ban_quyen_luu_trang_thai_che_cccd(self):
        import pabt
        from pabt import app as ud, in_an
        w = ud.CuaSoChinh(menu_trai=True)
        self.addCleanup(w.close)
        if not pabt.BAN_THU_NGHIEM:                                         # bản phát hành: nhãn gói bản quyền thay "BẢN THỬ NGHIỆM"
            self.assertEqual(w.bang_tieu_de.nhan_ban_quyen.text(), ban_quyen.mo_ta())
            self.assertNotIn('THỬ NGHIỆM', w.windowTitle())
        self.assertIn('Sẵn sàng', w.lb_tom_tat.text())
        self.assertIn('●', w.nut_tk.text())                                  # đèn báo LAN
        self.assertFalse(hasattr(w, 'lb_co_quan'))                           # 0.9.30: bỏ chữ "Cơ quan: …" góc phải thanh menu
        self.assertIn('Cài đặt', [a.text().replace('&', '') for a in w.menuBar().actions()])
        self.assertEqual(w.lenh['Lưu dự án'].shortcut().toString(), 'Ctrl+S')
        self.assertFalse(w.luu_du_an_lenh())                                 # chưa mở dự án
        p = _du_an(self.td, 4)
        w.mo(str(p))
        self.assertTrue(w.luu_du_an_lenh())
        w.bang.selectRow(0)
        self.assertIn('Dự án: 4 hộ', w.lb_tom_tat.text())                   # 21/10/2026: kèm số thửa / DT
        self.assertIn('Đang chọn: 1 hộ', w.lb_tom_tat.text())
        self.assertEqual(w.nut_ds['Xóa hộ…'].property('bien_the'), 'danger')
        # 1.0.04: bỏ che CCCD - ô ẩn, bản in / văn bản trình in đủ số + ngày cấp
        with w.con:
            w.con.execute("UPDATE ho SET so_cccd = '075092001234', ngay_cap = '01/01/2021' WHERE thu_tu = 1")
        ma = w.con.execute('SELECT ma_ho FROM ho WHERE thu_tu = 1').fetchone()[0]
        from pabt.man_hinh import HopIn
        d = HopIn(w.con, w, [ma])
        self.addCleanup(d.close)
        self.assertFalse(d.o_che_cccd.isChecked())
        self.assertTrue(d.o_che_cccd.isHidden())
        self.assertFalse(hasattr(d, '_luu_che_cccd'))
        tt = in_an._thong_tin_ho(w.con, ma, in_an._thong_tin_du_an(w.con), True)    # che=True cũ: bỏ qua
        self.assertEqual(tt['cccd'], '075092001234 - Ngày cấp: 01/01/2021')
        from pabt import van_ban_trinh
        _, dong = van_ban_trinh.du_lieu(w.con, [ma])
        self.assertIn('075092001234', dong[0]['ho.cccd'])


class TestBoCaiPhoQuat(unittest.TestCase):
    def test_cai_dat_tu_chon_ban(self):
        s = (GOC / 'bo_cai_win' / 'cai_dat.ps1').read_text(encoding='utf-8-sig')
        self.assertIn("if ($BAN -eq 'universal') {", s)
        self.assertIn("$DANH_SACH = 'danh_sach_x64.txt'", s)
        self.assertIn("$DANH_SACH = 'danh_sach_x86.txt'", s)
        self.assertIn('$v0.Build -ge 17763 -and $may64_0', s)                # Win10 1809+ 64-bit -> x64; còn lại x86
        self.assertIn('(Join-Path $GOC $DANH_SACH)', s)
        import sys
        sys.path.insert(0, str(GOC / 'bo_cai_win'))
        import dung_bo_cai_win as d
        self.assertEqual((d.BAN['win10']['ten'], d.BAN['win7']['ten']), ('Win10-11_x64', 'Win7-8-10_x86'))
        self.assertEqual((d.BAN['win10']['zip'], d.BAN['win7']['zip']), ('x64', 'x86'))
        self.assertTrue(callable(d.dong_goi_pho_quat))
        self.assertEqual(d.MAC_DINH, ('universal',))       # 0.9.26 (người dùng): chỉ phát hành MỘT bộ cài cho mọi Windows
        self.assertIn('x64\\PABT.exe', d.DOC_TRUOC)
        self.assertIn('x86\\PABT.exe', d.DOC_TRUOC)

    def test_khong_trung_huong_dan(self):
        import sys
        sys.path.insert(0, str(GOC / 'bo_cai_win'))
        import dung_bo_cai_win as d
        for ban in d.BAN:
            if not (GOC / 'dist' / d.BAN[ban]['dist'] / 'PABT.exe').exists():
                continue                                                      # chưa dựng: bỏ qua
            ten = [t.lower() for t, _ in d._ds_chuong_trinh(ban)]
            self.assertEqual(len(ten), len(set(ten)), ban)                    # 0.9.23: zip bản Win7 trùng HUONG_DAN.md


if __name__ == '__main__':
    unittest.main()

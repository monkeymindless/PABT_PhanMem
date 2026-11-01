"""Thẻ "Thông tin hộ, thửa đất" (KhungHoSo) theo đặc tả + ảnh mẫu người dùng 20/10/2026: khối I lưới 3 cột + thẻ nhỏ, bảng thửa 11
cột (DT nguyên thửa / còn lại, vị trí giá đất, Giấy chứng nhận, nguồn gốc rút gọn 2 dòng, Thao tác), dải tổng hợp địa chính. Số liệu
GIẢ LẬP."""
from __future__ import annotations
import os
import shutil
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest import mock

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

from PySide6.QtCore import QEvent, QPointF, Qt                                       # noqa: E402
from PySide6.QtGui import QKeyEvent, QMouseEvent                                     # noqa: E402
from PySide6.QtWidgets import QApplication, QStyleOptionViewItem                     # noqa: E402

from pabt import csdl, ho_so                                                          # noqa: E402
from pabt.lap_pa import LoiNhap                                                       # noqa: E402
from pabt.tien import D                                                               # noqa: E402

THUA = [dict(so_to='35', so_thua='457', loai_dat='CLN', dt_thu_hoi='150', dt_nguyen_thua='200', so_gcn='CS 01234',
             nguon_goc='- Khai phá năm 1995\n- Sử dụng ổn định, không tranh chấp', vi_tri='Mặt tiền đường giả lập'),
        dict(so_to='35', so_thua='458', loai_dat='ONT', dt_thu_hoi='80'),
        dict(so_to='36', so_thua='12', loai_dat='LUK', dt_thu_hoi='300,5', dt_nguyen_thua='300,5')]


class _Co(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.td = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.td, True)
        self.con = csdl.tao_moi(self.td / 'thu.larc')
        self.addCleanup(self.con.close)
        self.ma = ho_so.luu_ho(self.con, None, {'ho_ten': 'Nguyễn Văn Thử', 'so_cccd': '079123456789', 'dia_chi': 'Ấp 1'}, THUA)
        self.ma2 = ho_so.luu_ho(self.con, None, {'ho_ten': 'Lê Thị Khác', 'so_cccd': '079000000001'}, [])

    def khung(self, ma=None):
        from pabt.man_hinh_ho_so import KhungHoSo
        k = KhungHoSo(self.con, self.ma if ma is None else ma)
        self.addCleanup(k.deleteLater)
        k.resize(1300, 720)
        return k


class TestLuuCotMoi(_Co):
    def test_luu_doc_dt_nguyen_thua_va_gcn(self):
        t = ho_so.doc_ho(self.con, self.ma)['thua']
        self.assertEqual([(x['dt_nguyen_thua'], x['so_gcn']) for x in t], [('200', 'CS 01234'), ('', ''), ('300.5', '')])

    def test_dt_thu_hoi_lon_hon_nguyen_thua_bao_loi(self):
        with self.assertRaises(LoiNhap) as e:
            ho_so.luu_ho(self.con, self.ma, {'ho_ten': 'X'}, [dict(so_to='1', so_thua='2', dt_thu_hoi='500', dt_nguyen_thua='120')])
        self.assertIn('lớn hơn DT nguyên thửa', str(e.exception))

    @unittest.skipUnless(sqlite3.sqlite_version_info >= (3, 35), 'cần SQLite có DROP COLUMN để giả lập file cũ')
    def test_file_cu_chua_co_cot_tu_them_khi_mo(self):
        p = self.td / 'cu.larc'
        self.con.execute(f"VACUUM INTO '{p}'")
        thu = sqlite3.connect(str(p))
        thu.execute('PRAGMA foreign_keys = OFF')
        for k, _ in csdl.COT_THUA_THEM:
            thu.execute(f'ALTER TABLE thua DROP COLUMN {k}')
        thu.commit()
        thu.close()
        con = csdl.mo(p)
        self.addCleanup(con.close)
        self.assertEqual(csdl.PHIEN_BAN_CSDL, con.execute('PRAGMA user_version').fetchone()[0])   # không đổi phiên bản
        self.assertTrue(csdl.co_cot_thua(con))
        self.assertEqual(ho_so.doc_ho(con, self.ma)['thua'][0]['dt_nguyen_thua'], '')

    def test_bo_don_gia_khong_bi_ghi(self):
        from pabt import tai_nguyen
        import hashlib
        p = tai_nguyen('bo_don_gia.sqlite')
        truoc = hashlib.sha256(Path(p).read_bytes()).hexdigest()
        csdl.mo(p, chi_doc=True).close()
        self.assertEqual(hashlib.sha256(Path(p).read_bytes()).hexdigest(), truoc)


class TestKhoiI(_Co):
    def test_luoi_3_cot_va_bi_danh(self):
        from pabt.man_hinh_ho_so import O_LUOI_HO
        k = self.khung()
        self.assertEqual(k.the_chu_ho.objectName(), 'khung_chu_ho')
        luoi = k.luoi_ho
        for kh, (hang, cot) in O_LUOI_HO.items():
            if kh not in k.nhan_o:
                continue
            i = luoi.indexOf(k.nhan_o[kh])
            self.assertEqual(luoi.getItemPosition(i)[:2], (hang, cot * 2), kh)
        self.assertEqual(k.lb_ten.text(), 'Họ và tên:')
        self.assertEqual(k.lb_cccd.text(), 'Số CCCD/Định danh:')
        self.assertEqual(k.lb_ngay_cap.text(), 'Ngày cấp / Nơi cấp:')
        self.assertEqual(k.lb_dia_chi.text(), 'Địa chỉ thường trú:')
        self.assertEqual(k.lb_sdt.text(), 'Số điện thoại:')
        self.assertEqual(k.lb_ghi_chu.text(), 'Ghi chú hồ sơ hộ:')
        self.assertEqual(k.lb_tinh_trang.text(), 'Tình trạng pháp lý:')
        self.assertIs(k.o_ten, k.o['ho_ten'])
        self.assertEqual((k.o_ten.objectName(), k.o_cccd.objectName(), k.o_phap_ly.objectName()), ('o_ten', 'o_cccd', 'o_phap_ly'))
        self.assertEqual(luoi.getItemPosition(luoi.indexOf(k.nut_scan))[:2], (2, 5))       # Hồ sơ đính kèm: hàng 3, cột 3

    def test_to_chuc_doi_nhan_an_o(self):
        k = self.khung()
        k.o_ten.setText('Công ty TNHH Mẫu')
        self.assertEqual((k.lb_ten.text(), k.lb_dia_chi.text()), ('Tổ chức:', 'Địa chỉ:'))
        for w in (k.lb_cccd, k.o_cccd, k.lb_sdt, k.o_sdt, k.lb_ngay_cap, k.o_ngay_cap, k.o['noi_cap']):
            self.assertTrue(w.isHidden())
        self.assertIn('Tổ chức', k.the_loai_doi_tuong.text())
        self.assertFalse(k.the_cccd.isVisibleTo(k))
        k.o_ten.setText('Phạm Văn B')
        self.assertFalse(k.o_cccd.isHidden())
        self.assertIn('Hộ gia đình', k.the_loai_doi_tuong.text())

    def test_kiem_cccd(self):
        k = self.khung()
        self.assertEqual(k.kiem_cccd(), 'du')
        self.assertIn('đủ 12 số', k.the_cccd.text())
        k.o_cccd.setText('07912345')
        self.assertEqual(k.kiem_cccd(), 'thieu')
        self.assertEqual(k.o_cccd.property('hop_le'), '0')
        k.o_cccd.setText('079 000 000 001')                 # trùng hộ khác (bỏ khoảng trắng)
        self.assertEqual(k.kiem_cccd(), 'trung')
        self.assertIn('Lê Thị Khác', k.the_cccd.text())
        k.o_cccd.setText('123456789')
        self.assertEqual(k.kiem_cccd(), 'cmnd')
        self.assertEqual(k.o_cccd.property('hop_le'), '1')


class TestBangThua(_Co):
    def test_11_cot_can_le_cao_dong(self):
        from pabt.man_hinh_ho_so import CAO_DONG_THUA, COT_THUA
        k = self.khung()
        hien = [ten for c, (_, ten) in enumerate(COT_THUA) if not k.bang.isColumnHidden(c)]
        self.assertEqual(hien, ['STT', 'Tờ BĐ', 'Số thửa', 'Loại đất', 'DT nguyên thửa (m²)', 'DT thu hồi (m²)', 'DT còn lại',
                                'Vị trí đất', 'Giấy chứng nhận', 'Nguồn gốc & Vị trí đất', 'Thao tác'])
        self.assertEqual([k.bang.horizontalHeaderItem(c).toolTip() for c in range(k.bang.columnCount()) if not k.bang.isColumnHidden(c)],
                         hien)
        giua = int(Qt.AlignmentFlag.AlignCenter)
        phai = int(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        for kh in ('stt', 'so_to', 'so_thua', 'loai_dat', 'vi_tri_gia', 'so_gcn'):
            self.assertEqual(int(k.bang.item(0, k.cot.index(kh)).textAlignment()), giua, kh)
        for kh in ('dt_nguyen_thua', 'dt_thu_hoi', 'dt_con_lai'):
            self.assertEqual(int(k.bang.item(0, k.cot.index(kh)).textAlignment()), phai, kh)
        self.assertEqual({k.bang.rowHeight(r) for r in range(k.bang.rowCount())}, {CAO_DONG_THUA})
        # nguồn gốc rất dài vẫn không làm dòng cao thêm
        k.bang.item(0, k.cot.index('nguon_goc')).setText('Giao khoán năm 2002. ' * 80)
        self.app.processEvents()
        self.assertEqual(k.bang.rowHeight(0), CAO_DONG_THUA)
        self.assertEqual([k.bang.item(r, 0).text() for r in range(3)], ['1', '2', '3'])

    def test_dt_con_lai_va_khong_tinh_la_thay_doi(self):
        k = self.khung()
        c = k.cot.index('dt_con_lai')
        self.assertEqual([k.bang.item(r, c).text() for r in range(3)], ['50', '', '0'])
        self.assertFalse(k.co_thay_doi())
        k.bang.item(0, k.cot.index('dt_thu_hoi')).setText('210')
        self.app.processEvents()
        self.assertEqual(k.bang.item(0, c).text(), '-10')
        self.assertTrue(k.bang.item(0, c).data(Qt.ItemDataRole.UserRole + 1))           # tô đỏ
        self.assertFalse(k.bang.item(0, c).flags() & Qt.ItemFlag.ItemIsEditable)
        with mock.patch.object(k, '_bao') as bao:                                         # không hiện QMessageBox (treo kiểm thử)
            self.assertFalse(k.luu())                                                      # LoiNhap: thu hồi > nguyên thửa
            self.assertIn('lớn hơn DT nguyên thửa', bao.call_args[0][0])
        k.bang.item(0, k.cot.index('dt_thu_hoi')).setText('150')
        self.assertTrue(k.luu())

    def test_vi_tri_gia_tu_muc_1(self):
        mt = ho_so.doc_ho(self.con, self.ma)['thua'][0]['ma_thua']
        with self.con:
            self.con.execute("INSERT INTO ct_dat (ma_ho, ma_thua, thu_tu, loai_dat, nhom_dat, dien_tich, vi_tri) "
                             "VALUES (?, ?, 1, 'CLN', 'NN', '150', 'VT2 - Đường giả lập')", (self.ma, mt))
        k = self.khung()
        it = k.bang.item(0, k.cot.index('vi_tri_gia'))
        self.assertEqual(it.text(), 'VT2 - Đường giả lập')
        self.assertFalse(it.flags() & Qt.ItemFlag.ItemIsEditable)

    def test_hop_nguon_goc_sua_ca_vi_tri(self):
        k = self.khung()
        ng = k._ng
        ng.im_lang, ng.chu_moi, ng.vi_tri_moi = True, '- Nguồn gốc mới đầy đủ', 'Vị trí mới'
        self.addCleanup(lambda: setattr(ng, 'im_lang', False))
        self.assertTrue(k.sua_dong(1))                                                    # nút "Sửa" / Enter / liên kết
        self.assertEqual(k._chu_goc(1, 'vi_tri'), 'Vị trí mới')
        self.assertTrue(k.luu())
        t = ho_so.doc_ho(self.con, self.ma)['thua'][1]
        self.assertEqual((t['nguon_goc'], t['vi_tri']), ('- Nguồn gốc mới đầy đủ', 'Vị trí mới'))

    def test_lien_ket_xem_sua_du_va_enter(self):
        from pabt.man_hinh_ho_so import CAO_DONG_THUA
        k = self.khung()
        k.show()
        self.app.processEvents()
        b, ng = k.bang, k._ng
        c = k.cot.index('nguon_goc')
        idx = b.model().index(0, c)
        op = QStyleOptionViewItem()
        op.widget = b
        op.rect = b.visualRect(idx)
        op.font = b.font()
        self.assertEqual(b.rowHeight(0), CAO_DONG_THUA)
        lk = ng.vung_lien_ket(op.rect, op.font)
        self.assertTrue(op.rect.contains(lk.center().toPoint()))
        sk = QMouseEvent(QEvent.Type.MouseButtonRelease, lk.center(), Qt.MouseButton.LeftButton, Qt.MouseButton.LeftButton,
                         Qt.KeyboardModifier.NoModifier)
        with mock.patch.object(ng, 'mo_hop', return_value=True) as mo:
            self.assertTrue(ng.editorEvent(sk, b.model(), op, idx))
            mo.assert_called_once()
        b.setCurrentCell(0, c)
        with mock.patch.object(k, 'sua_dong', return_value=True) as sua:
            QApplication.sendEvent(b, QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_Return, Qt.KeyboardModifier.NoModifier))
            sua.assert_called_once_with(0)

    def test_thao_tac_sua_va_xoa(self):
        k = self.khung()
        k.show()
        self.app.processEvents()
        b = k.bang
        idx = b.model().index(1, k.cot.index('thao_tac'))
        op = QStyleOptionViewItem()
        op.widget = b
        op.rect = b.visualRect(idx)
        sua, xoa = k._tt.vung(op.rect)

        def bam(diem):
            return QMouseEvent(QEvent.Type.MouseButtonRelease, QPointF(diem), Qt.MouseButton.LeftButton, Qt.MouseButton.LeftButton,
                               Qt.KeyboardModifier.NoModifier)
        with mock.patch.object(k, 'sua_dong') as s:
            k._tt.editorEvent(bam(sua.center()), b.model(), op, idx)
            s.assert_called_once_with(1)
        k._tt.editorEvent(bam(xoa.center()), b.model(), op, idx)
        self.app.processEvents()
        self.assertEqual(b.rowCount(), 2)
        self.assertEqual([b.item(r, 0).text() for r in range(2)], ['1', '2'])       # STT đánh lại

    def test_chon_tung_o_ctrl_c_va_menu(self):
        from pabt.giao_dien import ap_kieu_cay
        k = self.khung()
        ap_kieu_cay(k)
        b = k.bang
        self.assertEqual(b.selectionBehavior(), b.SelectionBehavior.SelectItems)
        b.setCurrentCell(0, k.cot.index('so_gcn'))
        QApplication.clipboard().clear()
        QApplication.sendEvent(b, QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_C, Qt.KeyboardModifier.ControlModifier))
        QApplication.sendEvent(b, QKeyEvent(QEvent.Type.KeyRelease, Qt.Key.Key_C, Qt.KeyboardModifier.ControlModifier))
        self.assertEqual(QApplication.clipboard().text(), 'CS 01234')
        b.clearSelection()
        m = k.menu_bang(b.visualRect(b.model().index(0, k.cot.index('so_thua'))).center(), hien=False)
        self.addCleanup(m.deleteLater)
        chu = [a.text() for a in m.actions() if a.text()]
        self.assertEqual(chu[0], 'Sao chép ô: "457"\tCtrl+C')
        self.assertEqual(chu[1], 'Sao chép cả dòng thửa\tCtrl+Shift+C')
        self.assertIn('Mở hộp soạn Nguồn gốc && Vị trí đầy đủ…\tEnter', chu)

    def test_xoa_nhieu_dong_chon_tung_o(self):
        k = self.khung()
        b = k.bang
        b.setCurrentCell(0, 1)
        sm = b.selectionModel()
        sm.select(b.model().index(2, 3), sm.SelectionFlag.Select)
        self.assertTrue(k.xoa_dong(xac_nhan=True))
        self.assertEqual(b.rowCount(), 1)
        self.assertEqual(k._chu(0, 'so_thua'), '458')

    def test_tach_dong_giu_truong_moi(self):
        k = self.khung()
        k.bang.item(0, k.cot.index('loai_dat')).setText('ONT+CLN')
        self.assertEqual(k.tach_dong(0), 2)
        self.assertEqual((k._chu(1, 'loai_dat'), k._chu(1, 'so_gcn'), k._chu(1, 'dt_nguyen_thua')), ('CLN', 'CS 01234', '200'))

    def test_chi_doc_khong_mo_hop(self):
        k = self.khung()
        k.bang.setEditTriggers(k.bang.EditTrigger.NoEditTriggers)
        k._ng.im_lang, k._ng.chu_moi = True, 'không được ghi'
        self.addCleanup(lambda: setattr(k._ng, 'im_lang', False))
        self.assertFalse(k.sua_dong(0))


class TestDaiTongHop(_Co):
    def test_tong_hop_va_the_loai_dat(self):
        k = self.khung()
        tt = k.tom_tat_dia_chinh()
        self.assertEqual((tt['so_thua'], tt['so_to']), (3, 2))
        self.assertEqual((tt['dt_nguyen_thua'], tt['dt_thu_hoi'], tt['dt_con_lai']), (D('500.5'), D('530.5'), D('50')))
        chu = k.lb_tom_tat_thua.text()
        for x in ('Tổng hợp địa chính hộ:', 'Tổng số thửa: <b>3</b> thửa', 'Số tờ bản đồ: <b>2</b> tờ', 'Tổng DT nguyên thửa:',
                  'Tổng DT thu hồi:', 'Tổng DT còn lại:'):
            self.assertIn(x, chu)
        self.assertEqual(k.thanh_tom_tat_thua.objectName(), 'thanh_tom_tat_thua')
        self.assertEqual([t.text() for t in k.the_loai],
                         ['ONT (Đất ở): 80 m² (1 thửa)', 'LUK (Đất lúa): 300,5 m² (1 thửa)', 'CLN / HNK: 150 m² (1 thửa)'])
        self.assertIn('(3 thửa)', k.lb_tieu_de_thua.text())
        k.them_dong(dict(so_to='40', so_thua='1', loai_dat='SKC', dt_thu_hoi='10'))
        self.app.processEvents()
        self.assertIn('(4 thửa)', k.lb_tieu_de_thua.text())
        self.assertEqual(k.the_loai[-1].text(), 'Loại khác: 10 m² (1 thửa)')
        k.xoa_dong(0, xac_nhan=True)
        self.app.processEvents()
        self.assertIn('(3 thửa)', k.lb_tieu_de_thua.text())

    def test_cua_so_lap_pa_dung_khung_moi(self):
        from pabt.man_hinh import CuaSoLapPA
        w = CuaSoLapPA(self.con, self.ma)
        self.addCleanup(w.deleteLater)
        self.addCleanup(lambda: (w.bo_thay_doi(), w.close()))
        self.assertTrue(hasattr(w.ho_so, 'thanh_tom_tat_thua'))
        self.assertIn('(3 thửa)', w.tab.tabText(0))
        self.assertNotIn('tai_dinh_cu', w.ho_so.o)                    # an=('trang_thai', 'tai_dinh_cu') vẫn giữ


if __name__ == '__main__':
    unittest.main()

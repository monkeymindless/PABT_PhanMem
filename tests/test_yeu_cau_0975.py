"""0.9.75 (người dùng 13/10/2026): Niêm yết & Lấy ý kiến (nút đợt gộp, dải tiến độ, một chạm đổi ý kiến, tổng hợp theo nhóm lý do,
biên bản đối thoại, kéo giãn hai bảng thẻ 1); cửa sổ lập phương án (Tra giá đất NQ 28 ở mục 1, bấm đúp Nguồn gốc mở hộp riêng,
Ctrl + ← / →). Số liệu GIẢ LẬP."""
from __future__ import annotations
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

import openpyxl
from PySide6.QtCore import QEvent, QPointF, Qt
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import QApplication, QDialog, QStyleOptionViewItem

from pabt import csdl, du_thao
from tests.test_toc_do import _du_an


class _Co(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.td = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.td, True)
        moi = mock.patch.dict(os.environ, {'PABT_THU_MUC_MAY': str(self.td / 'may')})
        moi.start()
        self.addCleanup(moi.stop)
        self.con = csdl.mo(_du_an(self.td, so_ho=4))
        self.addCleanup(self.con.close)
        self.ma = [r[0] for r in self.con.execute('SELECT ma_ho FROM ho ORDER BY thu_tu')]


class TestNiemYet(_Co):
    def _khung(self):
        dot = du_thao.tao_dot(self.con, 'Đợt 1', '01/10/2026', 'UBND xã thử')
        du_thao.them_thu_cong(self.con, dot, self.ma)
        from pabt.man_hinh_du_thao import KhungDuThao
        k = KhungDuThao(self.con)
        self.addCleanup(k.close)
        k.show()
        k.cb.setCurrentIndex(k.cb.findData(dot))
        self.app.processEvents()
        return k, dot

    def loai(self, dot, ma):
        return self.con.execute('SELECT loai FROM y_kien_du_thao WHERE dot_id = ? AND ma_ho = ?', (dot, ma)).fetchone()[0]

    def test_nut_dot_gop_va_dai_tien_do(self):
        k, dot = self._khung()
        self.assertEqual(k.b_dua.text(), 'Đưa hộ vào đợt')
        self.assertEqual([a.text() for a in k.b_dua.menu().actions()],
                         ['Thêm toàn bộ hộ đủ điều kiện', 'Chọn hộ từ danh sách…'])
        self.assertFalse(hasattr(k, 'b_them'))
        self.assertEqual(k.b_hop.text(), 'Ngày họp dân')
        self.assertEqual(k.lb_dot.text(), 'Tiến độ đợt: Đồng thuận 0/4 (0%) · Không đồng ý: 0 · Ý kiến khác: 0 · Chưa lấy ý kiến: 4')
        du_thao.cap_nhat_y_kien(self.con, dot, self.ma[0], loai='dong_y')
        k._ve()
        self.assertIn('Đồng thuận 1/4 (25%)', k.lb_dot.text())
        self.assertNotIn('Thêm hộ vào đợt…', [b.text() for b in k.findChildren(type(k.b_tao))])   # nút trùng ở các thẻ: bỏ

    def test_the_1_keo_gian_va_che_cccd(self):
        k, dot = self._khung()
        # 06/11/2026: hai bảng con thay thanh ngăn kéo (tests/test_bang_con_niem_yet.py)
        self.assertEqual(k.ngan_ny.count(), 2)
        self.assertTrue(k.ngan_ny.widget(0).isAncestorOf(k.bang_ny) and k.ngan_ny.widget(1).isAncestorOf(k.bang_vm))
        self.assertEqual(k.bang_ny.horizontalHeaderItem(2).text(), 'CCCD')      # 1.0.04: số đầy đủ (bỏ che)
        self.assertIn('Xuất bảng niêm yết', k._nut)

    def test_mot_cham_doi_y_kien(self):
        k, dot = self._khung()
        self.assertEqual(k.bang_yk.item(0, 2).text(), '● Chưa lấy ý kiến')
        vong = []
        for _ in range(5):
            k._bam_y_kien(0, 2)                                        # bấm ô Ý kiến
            vong.append(self.loai(dot, self.ma[0]))
        self.assertEqual(vong, ['dong_y', 'khong_dong_y', 'y_kien_khac', 'chua', 'dong_y'])
        self.assertEqual(k.bang_yk.currentRow(), 0)                    # giữ dòng đang chọn sau khi vẽ lại
        k._bam_y_kien(0, 3)                                            # ô khác: không đổi
        self.assertEqual(self.loai(dot, self.ma[0]), 'dong_y')
        k.bang_yk.setCurrentCell(1, 2)                                 # phím Space
        k._phim_y_kien()
        self.assertEqual(self.loai(dot, self.ma[1]), 'dong_y')
        k.bang_yk.setCurrentCell(2, 3)
        k._phim_y_kien()                                               # Space ở cột khác: không đổi
        self.assertEqual(self.loai(dot, self.ma[2]), 'chua')
        self.assertEqual(k.bang_yk.item(0, 2).data(Qt.ItemDataRole.UserRole), 'dong_y')

    def test_bam_dup_noi_dung(self):
        from pabt.man_hinh_du_thao import HopNoiDung
        k, dot = self._khung()
        du_thao.cap_nhat_y_kien(self.con, dot, self.ma[0], loai='khong_dong_y', nhom='gia_dat')
        k._ve()
        goc = HopNoiDung.__init__

        def init(self_, parent, ho):
            goc(self_, parent, ho)
            self_.nd.setPlainText('Giá đất thấp hơn giá thị trường')
        with mock.patch.object(HopNoiDung, '__init__', init), \
                mock.patch.object(HopNoiDung, 'exec', return_value=QDialog.DialogCode.Accepted):
            k._kep_y_kien(0, 4)                                       # bấm đúp ô Nội dung
        self.assertEqual(k.bang_yk.item(0, 4).text(), 'Giá đất thấp hơn giá thị trường')
        self.assertEqual(self.loai(dot, self.ma[0]), 'khong_dong_y')    # ý kiến, nhóm giữ nguyên
        with mock.patch.object(k, '_sua_yk') as sua, mock.patch.object(k, '_sua_noi_dung') as nd:
            k._kep_y_kien(0, 2)                                       # bấm đúp ô Ý kiến: không mở gì (hai cú bấm đã đổi ý kiến)
            sua.assert_not_called()
            nd.assert_not_called()
            k._kep_y_kien(0, 1)                                       # ô khác: hộp ý kiến đủ
            sua.assert_called_once()

    def test_the_3_4_tong_hop_va_bien_ban(self):
        k, dot = self._khung()
        du_thao.cap_nhat_y_kien(self.con, dot, self.ma[0], loai='khong_dong_y', nhom='gia_dat', noi_dung='Giá thấp')
        du_thao.cap_nhat_y_kien(self.con, dot, self.ma[1], loai='dong_y', nhom='gia_dat')
        du_thao.cap_nhat_y_kien(self.con, dot, self.ma[2], loai='y_kien_khac', nhom='cay', noi_dung='Thiếu cây')
        du_thao.ghi_doi_thoai(self.con, dot, self.ma[0], '12/10/2026', 'Nhà văn hóa', 'Giữ nguyên giá', 'Đã giải thích')
        k._ve()
        self.assertEqual(k.bang_dt.rowCount(), 2)                      # chỉ hộ Không đồng ý / Ý kiến khác
        # thẻ 4: tỷ lệ đồng thuận theo nhóm lý do
        t = {k.bang_th.item(r, 0).text(): [k.bang_th.item(r, c).text() for c in range(1, 5)] for r in range(k.bang_th.rowCount())}
        self.assertEqual(t['Đơn giá đất'], ['2', '1', '1', '50,0%'])
        self.assertEqual(t['Cây trồng, mật độ'], ['1', '0', '1', '0,0%'])
        self.assertEqual(t['Nhà, công trình'], ['0', '0', '0', '-'])
        self.assertEqual(t['Toàn đợt'], ['4', '1', '3', '25,0%'])
        self.assertTrue(all(b.isEnabled() for n, b in k._nut.items() if n.startswith('Xuất')))
        # biên bản đối thoại: từng lần đối thoại của hộ chưa đồng thuận
        f = du_thao.xuat_doi_thoai(self.con, dot, self.td / 'dt.xlsx')
        ws = openpyxl.load_workbook(f).active
        dong = [[c.value for c in r] for r in ws.iter_rows(min_row=3)]
        tieu = dong[0]
        self.assertIn('Kết luận, tiếp thu', tieu)
        self.assertEqual(len(dong) - 1, 2)                              # hộ có đối thoại 1 dòng + hộ ý kiến khác chưa đối thoại
        self.assertIn('Giữ nguyên giá', [c for r in dong[1:] for c in r])
        # báo cáo tổng hợp ý kiến kèm trang theo nhóm lý do (hồ sơ Bước 8)
        wb = openpyxl.load_workbook(du_thao.xuat_y_kien(self.con, dot, self.td / 'yk.xlsx'))
        self.assertEqual(wb.sheetnames, ['Ý kiến', 'Theo nhóm lý do'])
        # chưa chọn đợt: nút xuất tắt
        k.cb.setCurrentIndex(0)
        self.assertFalse(k._nut['Xuất báo cáo tổng hợp ý kiến'].isEnabled())

    def test_vong_loai_y_kien(self):
        self.assertEqual([du_thao.loai_ke_tiep(x) for x in du_thao.VONG_Y_KIEN], ['dong_y', 'khong_dong_y', 'y_kien_khac', 'chua'])
        self.assertEqual(du_thao.loai_ke_tiep('khong_co'), 'dong_y')


class TestLapPA(_Co):
    def _cua_so(self):
        from pabt.man_hinh import CuaSoLapPA
        w = CuaSoLapPA(self.con, self.ma[0])
        self.addCleanup(lambda: (w.bo_thay_doi(), w.close()))
        return w

    def test_tra_gia_dat_nq28_o_muc_1(self):
        from pabt import gia_dat_nq28 as nq
        w = self._cua_so()
        self.assertIn('Tra giá đất NQ 28…', [a.text() for a in w.bang[1].menu_dong().actions()])     # 1.0.68: nút chuyển vào menu chuột phải của dòng
        self.assertTrue(w.bo.pa.dat, 'dự án giả lập phải có dòng đất')
        dong = next(r for r in nq.theo_dia_ban(w.bo.bc.ten_dia_ban or '') if nq.gia_dong(r, nq.cot_cua_loai(w.bo.pa.dat[0].loai_dat)))
        tb = w.tra_gia_dat_nq28(0, dong=dong)                           # một dòng đất: không cần chọn
        self.assertIn('đ/m²', tb)
        self.assertEqual(float(w.bo.pa.dat[0].gia_bang_gia), float(nq.gia_dong(dong, nq.cot_cua_loai(w.bo.pa.dat[0].loai_dat))))
        self.assertIn(dong['ten_duong'], w.bo.pa.dat[0].vi_tri)
        self.assertEqual(w.lb_tb.text(), tb)

    def test_nguon_goc_bam_dup_mo_hop_rieng(self):
        w = self._cua_so()
        b = w.ho_so.bang
        c = w.ho_so.cot.index('nguon_goc')
        it = b.item(0, c)
        self.assertIsNotNone(it)
        ng = w.ho_so._ng
        idx = b.model().index(0, c)
        sk = QMouseEvent(QEvent.Type.MouseButtonDblClick, QPointF(5, 5), Qt.MouseButton.LeftButton, Qt.MouseButton.LeftButton,
                         Qt.KeyboardModifier.NoModifier)
        op = QStyleOptionViewItem()
        op.widget = b
        ng.im_lang, ng.chu_moi = True, '- Trích lục: đất nhận chuyển nhượng năm 2005\n- Sử dụng ổn định'
        with mock.patch.object(ng, 'createEditor') as tao:
            self.assertTrue(ng.editorEvent(sk, b.model(), op, idx))        # bấm đúp: hộp riêng, KHÔNG tạo khung sửa trong ô
            tao.assert_not_called()
        self.assertIn('Sử dụng ổn định', b.item(0, c).text())
        # chỉ xem: không sửa
        b.setEditTriggers(b.EditTrigger.NoEditTriggers)
        ng.chu_moi = '- khác'
        self.assertFalse(ng.editorEvent(sk, b.model(), op, idx))
        self.assertNotIn('khác', b.item(0, c).text())

    def test_hop_nguon_goc(self):
        from pabt.man_hinh_ho_so import HopNguonGoc
        h = HopNguonGoc(None, '- Ý một - ý hai', 'tờ 5 thửa 12')
        self.addCleanup(h.close)
        self.assertIn('tờ 5 thửa 12', h.windowTitle())
        h.o.setPlainText('- Dòng một\n- Dòng hai')
        self.assertEqual(h.chu().count('\n'), 1)

    def test_ctrl_mui_ten_chuyen_ho(self):
        w = self._cua_so()
        phim = {sc.key().toString() for sc in w._phim}
        self.assertTrue({'Ctrl+Left', 'Ctrl+Right'} <= phim)


if __name__ == '__main__':
    unittest.main()

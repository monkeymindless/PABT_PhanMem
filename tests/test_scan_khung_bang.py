"""30/10/2026 (người dùng: "tinh chỉnh công cụ scan hoàn chỉnh, chính xác hơn, phân tách nội dung rõ ràng hơn"): bảng có khung kẻ trên
ảnh scan - dò vạch ngang / dọc (ảnh nghiêng, vạch dọc xiên khác vạch ngang), ô gộp, xóa nét kẻ, xếp chữ vào ô; tên loài cây đọc sai sửa
theo loài đã biết; mục văn bản tên đọc sai nhưng đơn giá trùng mục cũ thì khớp. Ảnh bảng VẼ bằng Qt (không dùng bản scan thật)."""
from __future__ import annotations
import os
import tempfile
import unittest
from pathlib import Path

from tests import APP  # noqa: F401 - QApplication cho QImage / QPainter

from pabt import luoi_bang as lb
from pabt import nhap_don_gia as ndg


def _ve_bang(goc: float = 0.0, xien: float = 0.0):
    """Ảnh 1600 x 1200: bảng 4 cột x 6 hàng, ô (hàng 1-3, cột 1) gộp dọc, hàng 5 gộp ngang cột 1..3. goc: xoay cả ảnh (độ); xien: vạch dọc
    lệch thêm theo chiều cao (điểm ảnh / 1000 điểm ảnh) - giấy trượt khi quét."""
    from PySide6.QtCore import QPointF, Qt
    from PySide6.QtGui import QColor, QImage, QPainter, QPen
    im = QImage(1600, 1200, QImage.Format.Format_RGB32)
    im.fill(QColor(255, 255, 255))
    p = QPainter(im)
    p.setPen(QPen(QColor(0, 0, 0), 3))
    if goc:
        p.translate(800, 600)
        p.rotate(goc)
        p.translate(-800, -600)
    xs, ys = [150, 300, 900, 1150, 1450], [200, 330, 460, 590, 720, 850, 980]

    def x_(x, y):
        return x + xien * (y - ys[0]) / 1000
    for i, y in enumerate(ys):
        for j in range(len(xs) - 1):
            # vạch ngang giữa hàng 0-1, 1-2 vắng ở cột 1 (ô gộp dọc hàng 0..2 cột 1 - hàng dữ liệu 1..3)
            if j == 1 and i in (2, 3):
                continue
            p.drawLine(QPointF(x_(xs[j], y), y), QPointF(x_(xs[j + 1], y), y))
    for j, x in enumerate(xs):
        for b in range(len(ys) - 1):
            if b == 5 and j in (2, 3):                  # hàng 5: cột 1..3 gộp ngang
                continue
            p.drawLine(QPointF(x_(x, ys[b]), ys[b]), QPointF(x_(x, ys[b + 1]), ys[b + 1]))
    # cột chữ thẳng hàng ở đầu mỗi ô cột 2 (như "Năm 1", "Năm 2"...): KHÔNG được thành vạch dọc
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor(0, 0, 0))
    for b in range(len(ys) - 1):
        p.drawRect(x_(920, ys[b]), ys[b] + 40, 6, 45)
    p.end()
    return im.convertToFormat(QImage.Format.Format_Grayscale8)


class TestKhungBang(unittest.TestCase):
    def test_bang_thang(self):
        sach, l = lb.nhan_khung(_ve_bang())
        self.assertIsNotNone(l)
        self.assertEqual((len(l.ngang), len(l.doc)), (7, 5))             # cột chữ "Năm…" không thành vạch dọc
        self.assertEqual([round(x) for x, _ in l.doc], [150, 300, 900, 1150, 1450])

    def test_anh_nghieng_va_vach_doc_xien(self):
        for goc, xien in ((0.3, 0), (-0.25, 0), (0.15, 6)):
            with self.subTest(goc=goc, xien=xien):
                self.assertAlmostEqual(lb.goc_nghieng(_ve_bang(goc, xien)), goc, delta=0.05)
                sach, l = lb.nhan_khung(_ve_bang(goc, xien))
                self.assertIsNotNone(l)
                self.assertEqual((len(l.ngang), len(l.doc)), (7, 5))

    def test_o_gop_va_xep_chu(self):
        sach, l = lb.nhan_khung(_ve_bang())
        vung = [tuple(round(v) for v in x) for x in lb.vung_gop(l)]
        self.assertIn((300, 330, 900, 720), vung)                       # gộp dọc hàng 1..3, cột 1
        self.assertIn((300, 850, 1450, 980), vung)                      # gộp ngang hàng 5, cột 1..3
        # từ (x, y, rộng, cao, chữ): tiêu đề hàng 0; tên nhóm giữa ô gộp dọc; số ở cột 3 các hàng; chữ ô gộp ngang
        tu = [(160, 240, 60, 40, 'STT'), (320, 240, 100, 40, 'Tên'), (1160, 240, 100, 40, 'Giá'),
              (320, 500, 200, 40, 'Nhóm'), (530, 500, 100, 40, 'I'),          # "I" số La Mã: không bị bỏ như mẩu nét kẻ
              (1160, 370, 120, 40, '100.000'), (1160, 500, 120, 40, '200.000'), (1160, 630, 120, 40, '300.000'),
              (320, 890, 300, 40, 'Ghi'), (700, 890, 200, 40, 'chung'), (147, 760, 6, 40, '|')]
        dong = [nd for loai, nd in lb.xep_vao_o(tu, l) if loai == 'bang']
        self.assertEqual(dong[0], ['STT', 'Tên', '', 'Giá'])
        self.assertEqual(dong[1], ['', 'Nhóm I', '', '100.000'])         # chữ ô gộp dọc về hàng trên cùng của ô
        self.assertEqual(dong[2], ['', '', '', '200.000'])
        self.assertEqual(dong[-1], ['', 'Ghi chung', '', ''])            # ô gộp ngang: chữ ở cột đầu

    def test_xoa_net_ke_giu_chu_o_gop(self):
        from PySide6.QtGui import QImage
        sach, l = lb.nhan_khung(_ve_bang())
        d, b = lb._byte_anh(sach.convertToFormat(QImage.Format.Format_Grayscale8))
        # vạch dọc x=900 đã xóa, vạch ngang vắng trong ô gộp không bị "xóa" lấn sang chữ: cột chữ x=920.. vẫn còn
        self.assertGreater(sum(1 for y in range(240, 285) if d[y * b + 922] < 128), 30)
        self.assertEqual(sum(1 for y in range(400, 420) if d[y * b + 900] < 128), 0)

    def test_khong_co_khung(self):
        from PySide6.QtGui import QColor, QImage
        im = QImage(800, 600, QImage.Format.Format_Grayscale8)
        im.fill(QColor(255, 255, 255))
        self.assertEqual(lb.nhan_khung(im), (None, None))


class TestSuaTenLoai(unittest.TestCase):
    def test_ten_doc_sai_ve_ten_da_biet(self):
        biet = {'Cẩm lai': ('Cẩm lai bông', 'Cẩm lai mật'), 'Bời lời giấy': (), 'Gội nước': (), 'Gội tẻ': ()}
        self.assertEqual(ndg.sua_ten_loai('Câmlai', ('Cẩm laibông', 'Cẩm lai mật'), biet)[0], 'Cẩm lai')
        self.assertEqual(ndg.sua_ten_loai("Bò'i lời giấy", (), biet), ('Bời lời giấy', ()))
        self.assertEqual(ndg.sua_ten_loai('Gội nưóc', (), biet)[0], 'Gội nước')
        self.assertEqual(ndg.sua_ten_loai('Sao đen', ('x',), biet), ('Sao đen', ('x',)))       # không giống loài nào: giữ chữ đọc được


class TestKhopTheoGia(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self._cu = os.environ.get('PABT_THU_MUC_MAY')
        os.environ['PABT_THU_MUC_MAY'] = str(Path(self.tmp.name) / 'may')

    def tearDown(self):
        if self._cu is None:
            os.environ.pop('PABT_THU_MUC_MAY', None)
        else:
            os.environ['PABT_THU_MUC_MAY'] = self._cu
        self.tmp.cleanup()

    def test_ten_doc_sai_gia_trung(self):
        from pabt import csdl, don_gia
        con = csdl.mo(don_gia.file_goc(), chi_doc=True)
        try:
            r = con.execute("SELECT ma, ten, dvt, don_gia FROM dm_taisan WHERE nhom = 3 AND ten LIKE 'Cây % - Năm thu hoạch thứ 1%' "
                            "ORDER BY rowid LIMIT 1").fetchone()
        finally:
            con.close()
        if r is None:
            self.skipTest('bộ đơn giá đóng gói không có mục năm thu hoạch')
        sai = r['ten'].replace('Cây ', 'Cáy ', 1).split(' (')[0]                       # chữ đọc sai một dấu
        m = ndg.Muc(sai, r['dvt'], ndg.doc_gia(r['don_gia']), nhom=3)
        ndg.so_khop([m], 3)
        self.assertEqual((m.trang_thai, m.ma_khop), ('giữ nguyên', r['ma']))
        m = ndg.Muc('Tên khác hẳn không giống', r['dvt'], ndg.doc_gia(r['don_gia']), nhom=3)
        ndg.so_khop([m], 3)
        self.assertEqual(m.trang_thai, 'mới')                                          # trùng giá mà tên không giống: không khớp


if __name__ == '__main__':
    unittest.main()

"""0.9.81 (người dùng 14/10/2026): hộp "Dán danh sách tài sản" (phương án hộ + khái toán, cùng phan_loai_tai_san.doc_danh_sach) hiểu dòng gõ
tay "Tên tài sản ␣ ĐVT ␣ Số lượng [␣ Tỷ lệ %]", số lượng là số hoặc phép tính ("Nhà tạm m2 4*5" -> 20). Số liệu GIẢ LẬP."""
from __future__ import annotations

import os
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path

from pabt.phan_loai_tai_san import doc_danh_sach
from tests.test_toc_do import _du_an


def _mot(dong: str) -> tuple:
    d = doc_danh_sach(dong)[0]
    return d['ten'], d['dvt'], d['so_luong'], d['ty_le']


class TestQuyTacDauCach(unittest.TestCase):
    def test_ten_dvt_so_luong(self):
        self.assertEqual(_mot('Nhà tạm m2 20'), ('Nhà tạm', 'm2', '20', ''))
        self.assertEqual(_mot('Nhà cấp 4 mái tôn m2 45'), ('Nhà cấp 4 mái tôn', 'm2', '45', ''))
        self.assertEqual(_mot('Gà ta con 40'), ('Gà ta', 'con', '40', ''))
        self.assertEqual(_mot('Di dời đồng hồ điện bộ 1'), ('Di dời đồng hồ điện', 'bộ', '1', ''))
        self.assertEqual(_mot('Ao nuôi cá ghép ha/vụ 0,03 70%'), ('Ao nuôi cá ghép', 'ha/vụ', '0,03', '70%'))
        self.assertEqual(_mot('Mít 6 năm cây 3 80%'), ('Mít 6 năm', 'cây', '3', '80%'))

    def test_so_luong_la_phep_tinh(self):
        d = doc_danh_sach('Nhà tạm m2 4*5')[0]
        self.assertEqual((d['ten'], d['dvt'], d['so_luong'], d['cong_thuc']), ('Nhà tạm', 'm2', '20', '4*5'))
        self.assertEqual(_mot('Nhà tạm m2 4 x 5')[2], '20')                       # nhân bằng x, có dấu cách
        self.assertEqual(_mot('Sân bê tông m2 (4+2)*3,5')[2], '21')
        self.assertEqual(_mot('Nhà kho\tm2\t4*5\t80%'), ('Nhà kho', 'm2', '20', '80%'))   # dán từ Excel: ô số lượng là phép tính

    def test_ten_co_so_khong_bi_cat_nham(self):
        self.assertEqual(_mot('Hàng rào lưới B40 m2 30')[0], 'Hàng rào lưới B40')
        self.assertEqual(_mot('Cột bê tông 2x2 cây 3'), ('Cột bê tông 2x2', 'cây', '3', ''))
        self.assertEqual(_mot('Đường ống D110 md 12,5'), ('Đường ống D110', 'md', '12,5', ''))
        self.assertEqual(_mot('Nhà cấp 4'), ('Nhà cấp 4', '', '', ''))           # không có ĐVT + số lượng: cả dòng là tên

    def test_kieu_cu_van_doc_duoc(self):
        self.assertEqual(_mot('Mít 6 năm 3 cây'), ('Mít 6 năm', 'cây', '3', ''))
        self.assertEqual(_mot('Mái che, mái hiên; m2; 12'), ('Mái che, mái hiên', 'm2', '12', ''))
        self.assertEqual(_mot('Nhà cấp 4 mái tôn\tm2\t45'), ('Nhà cấp 4 mái tôn', 'm2', '45', ''))


class TestHaiHopDan(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
        from PySide6.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        from pabt import app as ud
        cu = os.environ.get('PABT_THU_MUC_MAY')
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.addCleanup(lambda: os.environ.pop('PABT_THU_MUC_MAY', None) if cu is None
                        else os.environ.__setitem__('PABT_THU_MUC_MAY', cu))
        os.environ['PABT_THU_MUC_MAY'] = str(Path(self.tmp.name) / 'may')
        self.w = ud.CuaSoChinh(menu_trai=True)
        self.addCleanup(self.w.close)
        self.w.mo(str(_du_an(Path(self.tmp.name), 3)))

    def _dan(self, hop):
        self.addCleanup(hop.deleteLater)
        hop.im_lang = True
        self.assertIn('4*5', hop.o_chu.placeholderText())                    # chữ mẫu theo đúng quy tắc
        self.assertEqual(hop.bang.item(0, 3).text(), '20')                   # ô Số lượng đã tính sẵn
        self.assertEqual(hop.bang.item(0, 3).toolTip(), '= 4*5')
        self.assertEqual(hop.them(), 2)                                       # 2 dòng: Nhà tạm + Gà ta

    def test_phuong_an_ho(self):
        from pabt.nghiep_vu import MUC_KHOAN
        lp = self.w.mo_lap_pa(cho=False)
        self.addCleanup(lp.bo_thay_doi)
        self._dan(lp.mo_dan_tai_san(cho=False, clip='Nhà tạm m2 4*5\nGà ta con 40'))
        nha = [k for k in lp.bo.pa.khoan[2] if k.ten == 'Nhà tạm']             # mục 2 Nhà, công trình
        self.assertEqual(len(nha), 1)
        self.assertIn(nha[0].dvt, ('m2', 'm²'))                             # ĐVT chuẩn hóa theo bộ đơn giá
        self.assertEqual(Decimal(nha[0].so_luong), Decimal('20'))
        ga = [k for m in MUC_KHOAN for k in lp.bo.pa.khoan[m] if 'gà' in k.ten.lower()]
        self.assertEqual([Decimal(k.so_luong) for k in ga], [Decimal('40')])

    def test_khai_toan(self):
        dt = self.w.du_toan(cho=False)
        self._dan(dt.dan_tai_san('Nhà tạm m2 4*5\nGà ta con 40', cho=False))
        nha = [d for d in dt.dt.dong if d.ten == 'Nhà tạm']
        self.assertEqual(len(nha), 1)
        self.assertIn(nha[0].dvt, ('m2', 'm²'))
        self.assertEqual((nha[0].muc, Decimal(nha[0].khoi_luong)), (2, Decimal('20')))


if __name__ == '__main__':
    unittest.main()

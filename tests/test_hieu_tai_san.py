"""Hiểu dòng tài sản viết tự nhiên (người dùng 15/10/2026): hộp "Dán danh sách tài sản" (phương án hộ, Khái toán), Phiếu kiểm đếm.
Số liệu GIẢ LẬP; mục đơn giá lấy từ bộ đơn giá tích hợp."""
from __future__ import annotations
import os
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path

from pabt import csdl, hieu_tai_san as h
from pabt.lap_pa import BoSoan, DanhMuc
from pabt.phan_loai_tai_san import CAY, NHA, VAT_NUOI, BoPhanLoai, doc_danh_sach
from tests.test_toc_do import _du_an

MAU = '''Nhà tạm: 46m2
Gác để ở tính bằng Nhà 01 tầng kết cấu loại 4: 35,8m2.
Xoài: 16 cây, 17 năm tuổi
Tràm: 1453 cây, đường kính 28cm.
Ao nuôi cá ghép: 1,5ha, 1 năm 1 vụ.'''


class TestTachDong(unittest.TestCase):
    def t(self, dong):
        d = h.tach_dong(dong)
        return d and (d['ten'], d['dvt'], d['so_luong'], d['so_do'], d['kieu'], d['tuoi'], d['ghi_chu'])

    def test_vi_du_nguoi_dung(self):
        self.assertEqual(self.t('Nhà tạm: 46m2'), ('Nhà tạm', 'm2', '46', '', '', '', ''))
        self.assertEqual(self.t('Gác để ở tính bằng Nhà 01 tầng kết cấu loại 4: 35,8m2.')[:3],
                         ('Gác để ở tính bằng Nhà 01 tầng kết cấu loại 4', 'm2', '35,8'))
        self.assertEqual(self.t('Xoài: 16 cây, 17 năm tuổi'), ('Xoài', 'cây', '16', '', '', '17', ''))
        self.assertEqual(self.t('Tràm: 1453 cây, đường kính 28cm.'), ('Tràm', 'cây', '1453', '28', 'dk', '', ''))
        self.assertEqual(self.t('Ao nuôi cá ghép: 1,5ha, 1 năm 1 vụ.'), ('Ao nuôi cá ghép', 'ha', '1,5', '', '', '', '1 năm 1 vụ'))
        self.assertEqual(self.t('Tràm cây 1500 d28'), ('Tràm', 'cây', '1500', '28', 'dk', '', ''))     # ảnh người dùng gửi

    def test_khong_doan_sai(self):
        self.assertEqual(self.t('Sao đen 20 cây chu vi 45 cm'), ('Sao đen', 'cây', '20', '45', 'cv', '', ''))
        self.assertEqual(self.t('Đường ống D110 md 12,5')[:4], ('Đường ống D110', 'md', '12,5', ''))  # D110 là tên ống, không là đường kính cây
        self.assertEqual(self.t('Hàng rào lưới B40: dài 30m, cao 1,5m'), ('Hàng rào lưới B40', 'm', '30', '', '', '', 'cao 1,5m'))
        self.assertIsNone(h.tach_dong('Nhà cấp 4'))                       # không có số liệu: để bộ đọc cũ xử lý
        self.assertEqual(h.ten_ap_gia('Gác để ở tính bằng Nhà 01 tầng'), ('Nhà 01 tầng', 'Gác để ở'))

    def test_khoang_tuoi(self):
        self.assertEqual(h.khoang_tuoi('Cây xoài - Năm 1'), (1, 1))
        self.assertEqual(h.khoang_tuoi('Cây xoài - Năm thu hoạch thứ 1-5 (Năm thứ 4,5,6,7,8)'), (4, 8))
        self.assertEqual(h.khoang_tuoi('Cây xoài - Năm thu hoạch thứ 16 trở đi (Năm thứ 19 trở đi)'), (19, None))
        self.assertEqual(h.khoang_tuoi('Cây A - Từ năm thứ nhất đến năm thứ 3'), (1, 3))
        self.assertEqual(h.khoang_tuoi('Cây cau - Trên 5 năm tuổi'), (6, None))
        self.assertEqual(h.khoang_tuoi('Cây B - Cây mới trồng dưới 2 năm tuổi'), (0, 1))
        self.assertIsNone(h.khoang_tuoi('Thông đỏ nam (d >3-6 cm)'))


class CoSo(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.con = csdl.mo(_du_an(Path(self.tmp.name), 2))
        self.dm = DanhMuc(self.con)
        self.bo = BoPhanLoai(self.dm)

    def tearDown(self):
        self.con.close()
        self.tmp.cleanup()


class TestChonMuc(CoSo):
    def test_xep_dung_muc(self):
        ds = {d['ten']: h.bo_sung(self.bo, self.dm, d, self.bo.phan_loai(d['ten'], d['dvt'])) for d in doc_danh_sach(MAU)}
        k = ds['Nhà tạm']
        self.assertEqual((k.loai, k.khop.ten), (NHA, 'Nhà tạm'))
        k = ds['Gác để ở tính bằng Nhà 01 tầng kết cấu loại 4']
        self.assertEqual((k.loai, k.khop.ten, k.ghi_them), (NHA, 'Nhà 01 tầng - Kết cấu loại 4', 'Thực tế: Gác để ở'))
        k = ds['Xoài']
        self.assertEqual(k.loai, CAY)
        self.assertEqual(h.khoang_tuoi(k.khop.ten), (14, 18))                 # 17 năm tuổi
        k = ds['Tràm']
        self.assertEqual((k.loai, k.kieu, k.so_do, k.loai_cay), (CAY, 'dk', '28', 'Keo lá tràm'))   # tràm (có dấu huyền), không là trám
        k = ds['Ao nuôi cá ghép']
        self.assertEqual(k.loai, VAT_NUOI)
        self.assertTrue(k.khop.ten.startswith('Ao nuôi cá - Nuôi ghép cá'))
        self.assertTrue(k.can_xem)                                             # nhiều mức theo thời gian nuôi: nền vàng


class TestThemVaoPhuongAn(CoSo):
    def test_hop_dan_them_vao_ho(self):
        os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
        try:
            from PySide6.QtWidgets import QApplication
        except ImportError:
            self.skipTest('không có PySide6')
        from pabt.man_hinh_phan_loai import HopDanTaiSan
        app = QApplication.instance() or QApplication([])                     # noqa: F841
        bo = BoSoan(self.con, 1, self.dm)

        class CuaSo:                                                           # màn hình chủ giả: chỉ cần .bo + sau_khi_dan_tai_san
            pass
        cs = CuaSo()
        cs.bo, cs.goi = bo, []
        cs.sau_khi_dan_tai_san = lambda n, muc: cs.goi.append((n, muc))
        from pabt.nhap_tai_san import DichPhuongAn
        hop = HopDanTaiSan(None, MAU, dich=DichPhuongAn(bo))
        hop.cua_so = cs
        hop.im_lang = True
        self.assertEqual(hop.them(), 5)
        ten = {d.ten: d for muc in (2, 3, 7) for d in bo.pa.khoan[muc]}
        self.assertEqual(ten['Nhà tạm'].so_luong, Decimal('46'))
        self.assertIn('Thực tế: Gác để ở', ten['Nhà 01 tầng - Kết cấu loại 4'].ghi_chu)
        xoai = next(d for d in bo.pa.khoan[3] if d.ten.startswith('Cây xoài'))
        self.assertEqual((xoai.so_luong, h.khoang_tuoi(xoai.ten)), (Decimal('16'), (14, 18)))
        tram = [d for d in bo.pa.khoan[3] if d.ten.startswith('Keo lá tràm')]
        self.assertEqual(sum(d.so_luong for d in tram), Decimal('1453'))     # 1453 cây đường kính 28 cm -> quy cách (d >25 cm)
        self.assertTrue(all('(d >25 cm)' in d.ten for d in tram))
        ca = next(d for d in bo.pa.khoan[7] if d.ten.startswith('Ao nuôi cá'))
        self.assertEqual(ca.so_luong, Decimal('1.5'))
        self.assertIn('1 năm 1 vụ', ca.ghi_chu)
        hop.deleteLater()


class TestPhieuKiemDem(CoSo):
    def test_o_ten_ghi_ca_cau(self):
        import json
        from pabt.phieu_kiem_dem import nhap_ket_qua_kiem_dem
        f = Path(self.tmp.name) / 'kq.json'
        f.write_text(json.dumps({'ket_qua': {'1': [
            {'ten': 'Xoài: 16 cây, 17 năm tuổi', 'muc': 3},
            {'ten': 'Tràm', 'so_luong': '10', 'so_do': '28', 'kieu': 'dk', 'muc': 3}]}}, ensure_ascii=False), encoding='utf-8')
        kq = nhap_ket_qua_kiem_dem(self.con, f, self.dm)
        self.assertEqual((kq['so_dong'], kq['loi']), (2, []))
        pa = BoSoan(self.con, 1, self.dm).pa
        xoai = next(d for d in pa.khoan[3] if d.ten.startswith('Cây xoài'))
        self.assertEqual((xoai.so_luong, h.khoang_tuoi(xoai.ten)), (Decimal('16'), (14, 18)))
        self.assertTrue(any(d.ten.startswith('Keo lá tràm') and d.so_luong == 10 for d in pa.khoan[3]))


class TestKichThuocDienTich(CoSo):
    """Người dùng 20/10/2026: "4,7x3,0", "4,7*3,0", "Nhà tạm 42m2 (thửa 123)", "Nhà tạm 3,7m x 4,3m", "Nhà tạm 3,7 * 4,3" đều là diện
    tích - dài x rộng tính thành m², giữ phép tính ở chú thích ô."""

    def d(self, dong):
        ds = doc_danh_sach(dong)
        self.assertEqual(len(ds), 1, dong)
        x = ds[0]
        return x['ten'], x['dvt'], x['so_luong'], x.get('cong_thuc', ''), x['ghi_chu']

    def test_vi_du_nguoi_dung(self):
        self.assertEqual(self.d('Nhà tạm 42m2 (thửa 123)'), ('Nhà tạm', 'm2', '42', '', 'thửa 123'))
        for dong, ct in (('Nhà tạm 3,7m x 4,3m', '3,7x4,3'), ('Nhà tạm 3,7 * 4,3', '3,7*4,3'), ('Nhà tạm 3,7mx4,3m', '3,7x4,3'),
                         ('Nhà tạm: 3,7m x 4,3m', '3,7x4,3'), ('Nhà tạm 3,7 x 4,3 m2', '3,7x4,3'), ('Nhà tạm 3,7 × 4,3', '3,7×4,3')):
            self.assertEqual(self.d(dong), ('Nhà tạm', 'm2', '15,91', ct, ''), dong)
        for dong, ct in (('Nhà tạm 4,7x3,0', '4,7x3,0'), ('Nhà tạm 4,7*3,0', '4,7*3,0'), ('Nhà tạm 4,7 x 3,0', '4,7x3,0')):
            self.assertEqual(self.d(dong), ('Nhà tạm', 'm2', '14,1', ct, ''), dong)

    def test_o_bang_excel(self):
        self.assertEqual(self.d('Nhà tạm	3,7m x 4,3m'), ('Nhà tạm', 'm2', '15,91', '3,7x4,3', ''))
        self.assertEqual(self.d('Nhà tạm	4,7*3,0'), ('Nhà tạm', 'm2', '14,1', '4,7*3,0', ''))
        self.assertEqual(self.d('Nhà tạm	42m2'), ('Nhà tạm', 'm2', '42', '', ''))
        self.assertEqual(self.d('Tràm	3x4	cây'), ('Tràm', 'cây', '12', '3x4', ''))        # cột ĐVT có sẵn thắng m2 tự suy

    def test_khong_doan_sai(self):
        self.assertEqual(self.d('Nhà cấp 4')[:3], ('Nhà cấp 4', '', ''))
        self.assertEqual(self.d('Nhà cấp 4 3x5')[:3], ('Nhà cấp 4', 'm2', '15'))
        self.assertEqual(self.d('Đường ống D110 md 12,5')[:3], ('Đường ống D110', 'md', '12,5'))
        self.assertEqual(self.d('Nhà tạm m2 4x5')[:3], ('Nhà tạm', 'm2', '20'))
        self.assertEqual(self.d('Sân m2 3+2*4')[:4], ('Sân', 'm2', '11', '3+2*4'))
        self.assertEqual(self.d('Bể nước 2x3x1,5 m3')[:3], ('Bể nước', 'm3', '9'))           # ba thừa số + m3: thể tích
        self.assertEqual(self.d('Tràm 3x4 cây')[:3], ('Tràm', 'cây', '12'))
        self.assertEqual(self.d('Mái che (tôn) 20m2')[:3], ('Mái che (tôn)', 'm2', '20'))   # ngoặc thuộc tên giữ trong tên
        self.assertEqual(h.doc_kich_thuoc('2,5x3,5x1'), None)

    def test_them_vao_phuong_an_la_nha(self):
        d = doc_danh_sach('Nhà tạm 3,7m x 4,3m')[0]
        k = h.bo_sung(self.bo, self.dm, d, self.bo.phan_loai(d['ten'], d['dvt']))
        self.assertEqual((k.loai, k.khop.ten), (NHA, 'Nhà tạm'))


if __name__ == '__main__':
    unittest.main()

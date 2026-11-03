"""1.0.57 (người dùng 03/11/2026, ảnh hộp Cập nhật đơn giá - file PDF có chữ "QĐ hợp nhất giá bồi thường nhà, công trình"): tên tài sản
đọc thành "Đồng/m² sàn"; văn bản có 2 khu vực giá trộn vào nhau. Dòng chữ GIẢ LẬP theo đúng cấu trúc PDF đọc ra (giá không phải số thật)."""
from __future__ import annotations

import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from pabt import csdl, don_gia
from pabt import nhap_don_gia as ndg

DONG = '''Phụ lục I
ĐƠN GIÁ BỒI THƯỜNG THIỆT HẠI THỰC TẾ VỀ NHÀ, NHÀ Ở, CÔNG
TRÌNH XÂY DỰNG KHU VỰC 1 TRÊN ĐỊA BÀN TỈNH THỬ
Phụ lục Ia
ĐƠN GIÁ XÂY DỰNG NHÀ, NHÀ Ở
STT Nhà từ 05 tầng trở lên Đơn vị
tính Đơn giá
1.1
* Kết cấu loại 1:
- Khung cột: Bê tông cốt thép chịu lực
- Tường: sơn nước + ốp gạch
- Khu vệ sinh: xí, tiểu, tắm cao cấp; có ít nhất mỗi
tầng một khu
Đồng/m²
sàn 9.100.000
1.2
* Kết cấu loại 2:
- Khung cột: Bê tông cốt thép chịu
Đồng/m²
sàn 8.100.000
2 Nhà 01 tầng
2.1
* Kết cấu loại 1:
- Mái: Tôn.
Đồng/m²
sàn 4.100.000
5 Nhà bán kiên cố
Kết cấu:
- Khung cột: Sắt, gạch
Đồng/m²
sàn 1.800.000
6 Nhà tạm
Kết cấu:
Cột kèo gỗ, tre; vách bằng vật liệu dễ cháy; mái
tranh tre, nứa, lá
Đồng/m²
sàn 500.000
Phụ lục Ib
STT Loại biệt thự Đơn giá (đồng/m2
sàn)
1 Song lập 8.000.000
2 Đơn lập 9.000.000
Phụ lục Ic
STT Tên tài sản ĐVT Đơn giá (đồng)
28
Công đào (ao nuôi trồng thủy sản hoặc làm
hầm chứa nước tưới)
đồng/m3 40.000
29 - Chuồng heo, chuồng bò, gà, vịt:
- Xây gạch cao 1m, nền bê tông kiên cố, lợp
ngói hoặc tole fibro ciment m² 900.000
- Chuồng gà, vịt thô sơ m² 130.000 - 250.000
Mức bồi thường, hỗ trợ chi phí di dời, xây dựng mới mồ mả trong trường hợp di
dời mồ mả đến vị trí mới trong nghĩa trang theo quy hoạch
36 Mộ xây ốp đá hoa cương đồng/mộ 30.000.000
40 Miếu thờ dọc đường, bàn thiên đồng/cái 900.000
Mức bồi thường, hỗ trợ chi phí di dời, xây dựng mới mồ mả trong trường hợp tự
thu xếp việc di chuyển mồ mả ngoài khu vực được bố trí trong nghĩa trang theo
46 Miếu thờ dọc đường, bàn thiên đồng/cái 900.000
Phụ lục II
ĐƠN GIÁ BỒI THƯỜNG THIỆT HẠI THỰC TẾ VỀ NHÀ, NHÀ Ở, CÔNG
TRÌNH XÂY DỰNG KHU VỰC 2 TRÊN ĐỊA BÀN TỈNH THỬ
STT Tên tài sản ĐVT Đơn giá (đồng)
1 Nhà bán kiên cố m² 1.600.000'''.split('\n')


class TestDocBangNha(unittest.TestCase):
    def setUp(self):
        self.ds = ndg.nhan_muc([[x] for x in DONG], 2, [])
        self.theo = {(m.ten, m.khu_vuc): m for m in self.ds}

    def test_ten_theo_nhom_va_ket_cau(self):
        ten = [m.ten for m in self.ds if m.khu_vuc == '1']
        self.assertNotIn('Đồng/m² sàn', ' '.join(ten))
        for t, g in (('Nhà từ 05 tầng trở lên - Kết cấu loại 1', 9100000), ('Nhà từ 05 tầng trở lên - Kết cấu loại 2', 8100000),
                     ('Nhà 01 tầng - Kết cấu loại 1', 4100000), ('Nhà bán kiên cố', 1800000), ('Nhà tạm', 500000)):
            m = self.theo[(t, '1')]
            self.assertEqual((m.dvt, m.don_gia), ('m²', g), t)

    def test_biet_thu_va_cong_trinh(self):
        self.assertEqual(self.theo[('Biệt thự Song lập', '1')].don_gia, 8000000)
        self.assertEqual(self.theo[('Biệt thự Đơn lập', '1')].dvt, 'm²')
        cd = next(m for m in self.ds if m.ten.startswith('Công đào'))
        self.assertEqual((cd.dvt, cd.don_gia), ('m³', 40000))                  # ĐVT bảng biệt thự không mang sang bảng sau
        self.assertIn('Chuồng heo, chuồng bò, gà, vịt - Xây gạch cao 1m, nền bê tông kiên cố, lợp ngói hoặc tole fibro ciment',
                      [m.ten for m in self.ds])                                # "Chuồng" không bị hiểu là "Chương"
        self.assertIn('Chuồng gà, vịt thô sơ', [m.ten for m in self.ds])       # dòng con tự đủ tên
        mo = next(m for m in self.ds if 'hoa cương' in m.ten)
        self.assertEqual(mo.ten, 'Mộ xây ốp đá hoa cương')                     # câu dẫn "Mức bồi thường…" không thành tiền tố

    def test_khu_vuc(self):
        self.assertEqual([k for k, _ in ndg.cac_khu_vuc(self.ds)], ['1', '2'])
        kv2 = ndg.loc_khu_vuc(self.ds, '2')
        self.assertEqual([m.ten for m in kv2], ['Nhà bán kiên cố'])
        self.assertEqual(kv2[0].don_gia, 1600000)
        self.assertNotIn(1600000, [m.don_gia for m in ndg.loc_khu_vuc(self.ds, '1')])
        self.assertEqual(ndg.cac_khu_vuc([m for m in self.ds if m.khu_vuc == '1']), [])

    def test_bo_ngoac_cuoi(self):
        self.assertEqual(ndg._bo_ngoac_cuoi('Miếu thờ dọc đường, bàn thiên (Vào nghĩa trang quy hoạch)'), 'Miếu thờ dọc đường, bàn thiên')


BO = [('TS1', 'Nhà từ 05 tầng trở lên - Kết cấu loại 1', 'm²', 9100000), ('TS2', 'Nhà từ 05 tầng trở lên - Kết cấu loại 2', 'm²', 8100000),
      ('TS3', 'Nhà 01 tầng - Kết cấu loại 1', 'm²', 4100000), ('TS4', 'Nhà bán kiên cố', 'm²', 1800000), ('TS5', 'Nhà tạm', 'm²', 500000),
      ('TS6', 'Biệt thự Song lập', 'm²', 8000000), ('TS7', 'Biệt thự Đơn lập', 'm²', 9000000),
      ('TS8', 'Công đào ao/ hầm chứa nước/ cải tạo đầm phá, hố bom', 'm³', 40000),
      ('TS9', 'Chuồng heo, bò, gà, vịt (xây gạch 1m, nền bê tông, lợp ngói/ tôn)', 'm²', 900000),
      ('TS10', 'Chuồng gà, vịt thô sơ', 'm²', 130000), ('TS11', 'Chuồng gà, vịt thô sơ.', 'm²', 250000),
      ('TS12', 'Mộ xây ốp đá hoa cương (Vào nghĩa trang quy hoạch)', 'mộ', 30000000),
      ('TS13', 'Miếu thờ dọc đường, bàn thiên (Vào nghĩa trang quy hoạch)', 'cái', 900000),
      ('TS14', 'Miếu thờ dọc đường, bàn thiên (Tự thu xếp ngoài nghĩa trang)', 'cái', 900000)]


class TestSoKhop(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        td = Path(self.tmp.name)
        self._cu = os.environ.get('PABT_THU_MUC_MAY')
        os.environ['PABT_THU_MUC_MAY'] = str(td / 'may')
        self.bo = td / 'bo.sqlite'
        shutil.copyfile(don_gia.file_goc(), self.bo)
        con = csdl.mo(self.bo)
        try:
            with csdl.giao_dich(con), csdl.mo_khoa_danh_muc(con):
                pl = con.execute('SELECT phan_loai FROM dm_taisan WHERE nhom = 2 LIMIT 1').fetchone()[0]
                con.execute('DELETE FROM dm_taisan WHERE nhom = 2')
                con.executemany('INSERT INTO dm_taisan (ma, nhom, phan_loai, ten, dvt, don_gia) VALUES (?,2,?,?,?,?)',
                                [(ma, pl, t, d, str(g)) for ma, t, d, g in BO])
        finally:
            con.close()
        p = mock.patch.object(don_gia, 'file_dang_dung', return_value=self.bo)
        p.start()
        self.addCleanup(p.stop)

    def tearDown(self):
        self.doCleanups()
        if self._cu is None:
            os.environ.pop('PABT_THU_MUC_MAY', None)
        else:
            os.environ['PABT_THU_MUC_MAY'] = self._cu
        self.tmp.cleanup()

    def test_khu_vuc_khop_nhat_va_khop_het(self):
        ds = ndg.nhan_muc([[x] for x in DONG], 2, [])
        self.assertEqual(ndg.khu_vuc_khop_nhat(ds, 2), '1')
        kq = ndg.so_khop(ndg.loc_khu_vuc(ds, '1'), 2)
        moi = [m.ten for m in kq if m.trang_thai == 'mới']
        self.assertEqual(moi, [])                                              # mọi dòng khu vực 1 khớp mục đang có
        mieu = [m.ma_khop for m in kq if m.ten.startswith('Miếu')]
        self.assertEqual(mieu, ['TS13', 'TS14'])                               # hai lần ghi - hai mục theo thứ tự
        self.assertEqual(len({m.ma_khop for m in kq if m.ten.startswith('Chuồng')}), 3)   # không dồn hai dòng vào một mục


if __name__ == '__main__':
    unittest.main()

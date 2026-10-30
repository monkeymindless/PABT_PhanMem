"""Giá đất vị trí 2-4 ghi trong LỜI VĂN nghị quyết bảng giá đất (người dùng 30/10/2026). Câu văn bản GIẢ LẬP theo cách viết thường gặp."""
from __future__ import annotations

import os
import tempfile
import unittest
import zipfile
from decimal import Decimal
from pathlib import Path

from pabt.quy_tac_vi_tri import QuyTac, ap_quy_tac, doc_quy_tac

VAN_BAN = """Điều 3. Quy định về vị trí đất
1. Đối với đất ở:
a) Vị trí 1: thửa đất có mặt tiền tiếp giáp đường.
b) Giá đất vị trí 2, vị trí 3, vị trí 4 lần lượt bằng 70%, 50%, 30% giá đất vị trí 1 của tuyến đường đó nhưng không thấp hơn 150.000 đồng/m2.
2. Đối với đất nông nghiệp:
Vị trí 2 tính bằng 80% giá đất vị trí 1; vị trí 3 bằng 80% giá đất vị trí 2.
3. Đất thương mại, dịch vụ: VT2 bằng hệ số 0,6 so với vị trí 1."""


def _dong(**gia):
    r = dict(xa='Xã Thử', tt=1, ten_duong='Đường A', diem_dau='Cầu 1', diem_cuoi='Cầu 2', vi_tri='', nguong=[1000, 500],
             trang={'pl3': '', 'pl1': ''}, dat_o=0, tmdv=0, sxkd=0, nn_cay=0, nn_rung_nts=0)
    r.update(gia)
    return r


class TestDocQuyTac(unittest.TestCase):
    def test_cac_kieu_cau(self):
        ds = doc_quy_tac(VAN_BAN)
        gon = [(q.vi_tri, q.so_voi, str(q.ty_le), q.loai, q.toi_thieu) for q in ds]
        self.assertEqual(gon, [(2, 1, '0.7', 'dat_o', 150), (3, 1, '0.5', 'dat_o', 150), (4, 1, '0.3', 'dat_o', 150),
                               (2, 1, '0.8', 'nn', 0), (3, 2, '0.8', 'nn', 0), (2, 1, '0.6', 'tmdv', 0)])
        self.assertIn('vị trí 2, vị trí 3', ds[0].cau)

    def test_vi_tri_bang_chu_va_dau_hai_cham(self):
        ds = doc_quy_tac(['Vị trí thứ hai: 65% giá vị trí 1, vị trí thứ ba: 45% giá vị trí 1.'])
        self.assertEqual([(q.vi_tri, str(q.ty_le)) for q in ds], [(2, '0.65'), (3, '0.45')])

    def test_khong_nham_cau_mo_ta_vi_tri(self):
        # câu mô tả điều kiện vị trí có số đo, không có tỷ lệ giá: không phải quy tắc
        self.assertEqual(doc_quy_tac('Vị trí 2: thửa đất trong hẻm rộng từ 3m trở lên, cách đường chính không quá 200m.'), [])
        # tỷ lệ lớn hơn 100% hoặc vị trí được tính không lớn hơn vị trí gốc: bỏ
        self.assertEqual(doc_quy_tac('Vị trí 1 bằng 120% giá đất vị trí 2.'), [])


class TestApQuyTac(unittest.TestCase):
    def test_dung_vi_tri_tu_vi_tri_1(self):
        dong, them = ap_quy_tac([_dong(dat_o=2000, tmdv=1500, nn_cay=300, nn_rung_nts=200)], doc_quy_tac(VAN_BAN))
        self.assertEqual(them, 3)
        theo = {r['vi_tri']: r for r in dong}
        self.assertEqual(list(theo), ['VT1', 'VT2', 'VT3', 'VT4'])
        self.assertEqual((theo['VT2']['dat_o'], theo['VT3']['dat_o'], theo['VT4']['dat_o']), (1400, 1000, 600))
        self.assertEqual((theo['VT2']['nn_cay'], theo['VT3']['nn_cay']), (240, 192))     # vị trí 3 = 80% của vị trí 2 (chuỗi)
        self.assertEqual(theo['VT2']['tmdv'], 900)
        self.assertEqual(theo['VT3']['tmdv'], 0)                                          # văn bản không nói: không đoán
        self.assertTrue(theo['VT2']['sinh_tu_quy_tac'])
        self.assertIn('70%', theo['VT2']['tinh_tu'])

    def test_gia_toi_thieu(self):
        dong, _ = ap_quy_tac([_dong(dat_o=400)], [QuyTac(4, Decimal('0.3'), 1, 'dat_o', 150)])
        self.assertEqual(dong[-1]['dat_o'], 150)                                          # 30% x 400 = 120 < 150

    def test_giu_vi_tri_da_co_va_khong_dong_muc_t_k(self):
        ds = [QuyTac(2, Decimal('0.5'), 1), QuyTac(3, Decimal('0.4'), 1)]
        dong, them = ap_quy_tac([_dong(vi_tri='VT1', dat_o=1000), _dong(vi_tri='VT2', dat_o=777)], ds)
        self.assertEqual([(r['vi_tri'], r['dat_o']) for r in dong], [('VT1', 1000), ('VT2', 777), ('VT3', 400)])
        self.assertEqual(them, 1)
        # bảng kiểu Đồng Nai (MT / T1 / K1): không dựng
        dong, them = ap_quy_tac([_dong(vi_tri='MT', dat_o=1000), _dong(vi_tri='T1', dat_o=700)], ds)
        self.assertEqual(them, 0)

    def test_tinh_lai_bo_dong_cu(self):
        d1, _ = ap_quy_tac([_dong(dat_o=1000)], [QuyTac(2, Decimal('0.5'), 1)])
        d2, them = ap_quy_tac(d1, [QuyTac(2, Decimal('0.6'), 1)])
        self.assertEqual([(r['vi_tri'], r['dat_o']) for r in d2], [('VT1', 1000), ('VT2', 600)])
        self.assertEqual(them, 1)


class TestDocFile(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.addCleanup(self.td.cleanup)
        self.cu = os.environ.get('PABT_THU_MUC_MAY')
        os.environ['PABT_THU_MUC_MAY'] = str(Path(self.td.name) / 'may')

    def tearDown(self):
        if self.cu is None:
            os.environ.pop('PABT_THU_MUC_MAY', None)
        else:
            os.environ['PABT_THU_MUC_MAY'] = self.cu
        from pabt import gia_dat_nq28
        gia_dat_nq28._quen()

    def _docx(self) -> Path:
        W = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'

        def p(chu):
            return f'<w:p><w:r><w:t xml:space="preserve">{chu}</w:t></w:r></w:p>'

        def hang(*o):
            return '<w:tr>' + ''.join(f'<w:tc>{p(x)}</w:tc>' for x in o) + '</w:tr>'
        than = (p('NGHỊ QUYẾT Ban hành bảng giá đất') + ''.join(p(x) for x in VAN_BAN.splitlines()) +
                '<w:tbl>' + hang('STT', 'Tên đường', 'Điểm đầu', 'Điểm cuối', 'Đất ở') +
                hang('1', 'Đường A', 'Cầu 1', 'Cầu 2', '2.000') + hang('2', 'Đường B', 'Chợ', 'Trường', '1.500') + '</w:tbl>')
        f = Path(self.td.name) / 'nq.docx'
        with zipfile.ZipFile(f, 'w') as z:
            z.writestr('[Content_Types].xml', '<?xml version="1.0"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
                       '<Default Extension="xml" ContentType="application/xml"/></Types>')
            z.writestr('word/document.xml', f'<?xml version="1.0" encoding="UTF-8"?><w:document xmlns:w="{W}"><w:body>{than}</w:body>'
                       '</w:document>')
        return f

    def test_doc_file_word_dung_them_vi_tri(self):
        from pabt.cap_nhat_gia_dat import doc_file, doc_file_day_du
        f = self._docx()
        kq = doc_file_day_du(f, '', 'Xã Thử')
        self.assertEqual(len(kq['dong_goc']), 2)
        self.assertEqual(len(kq['quy_tac']), 6)
        dong, vb, chu = doc_file(f, '', 'Xã Thử')
        self.assertEqual(len(dong), 8)                    # 2 tuyến x (vị trí 1 + vị trí 2, 3, 4)
        self.assertIn('dựng thêm 6 dòng', chu)
        a = [(r['vi_tri'], r['dat_o']) for r in dong if r['ten_duong'] == 'Đường A']
        self.assertEqual(a, [('VT1', 2000), ('VT2', 1400), ('VT3', 1000), ('VT4', 600)])

    def test_bo_sung_giu_bang_gan_san_va_can_cu(self):
        from pabt import gia_dat_nq28 as nq
        from pabt.cap_nhat_gia_dat import ap_dung, doc_file
        dong, vb, chu = doc_file(self._docx(), '', 'Xã Thử')
        xs = ap_dung(dong, 'NQ thử', 'nq.docx', bo_sung=True)
        self.assertEqual(xs[-1], 'Xã Thử')
        self.assertIn('Xã Trị An', xs)
        r = next(x for x in nq.tim('Xã Thử') if x['vi_tri'] == 'VT2' and x['ten_duong'] == 'Đường A')
        self.assertIn('70%', nq.can_cu(r, 'dat_o'))
        self.assertIn('NQ thử', nq.can_cu(r, 'dat_o'))
        self.assertIn('70%', nq.mo_ta_vi_tri(r))
        # bổ sung lại cùng địa bàn: thay dòng cũ của địa bàn đó, không nhân đôi
        ap_dung(dong, 'NQ thử', 'nq.docx', bo_sung=True)
        self.assertEqual(len(nq.tim('Xã Thử')), 8)


if __name__ == '__main__':
    unittest.main()

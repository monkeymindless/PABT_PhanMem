"""1.0.56: quy định cách tính trong LỜI VĂN văn bản đơn giá (quy_dinh_van_ban) + tự chọn dòng thay đổi ở hộp Cập nhật đơn giá.
Văn bản GIẢ LẬP (không phải số liệu thật)."""
from __future__ import annotations

import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from pabt import csdl, don_gia
from pabt import nhap_don_gia as ndg
from pabt import quy_dinh_van_ban as qvb

VAN_BAN = [
    'ỦY BAN NHÂN DÂN TỈNH THỬ',
    'Số: 99/2026/QĐ-UBND',
    'QUYẾT ĐỊNH',
    'Ban hành đơn giá bồi thường cây trồng khi Nhà nước thu hồi đất',
    'Căn cứ Luật Đất đai số 31/2024/QH15 ngày 18 tháng 01 năm 2024;',
    'QUYẾT ĐỊNH:',
    'Điều 1. Phạm vi điều chỉnh',
    'Quyết định này quy định đơn giá bồi thường cây trồng trên địa bàn tỉnh.',
    'Điều 2. Nguyên tắc tính bồi thường',
    '1. Số lượng cây trồng được xác định theo thực tế kiểm đếm trên diện tích đất bị thu hồi.',
    '2. Đối với cây trồng xen thì giá trị bồi thường không vượt quá 50% giá trị cây trồng chính.',
    '3. Cây trồng vượt mật độ quy định thì phần vượt chỉ được hỗ trợ 30% đơn giá.',
    '4. Phương pháp đo đường kính thân cây:',
    'Cây đã có quyết định thu hồi đất mà trồng sau thời điểm thông báo thu hồi thì không được bồi thường.',
    'Điều 3. Hiệu lực thi hành',
    '1. Quyết định này có hiệu lực kể từ ngày 01 tháng 12 năm 2026 và thay thế Quyết định số 48/2025/QĐ-UBND.',
    'Nơi nhận:',
    '- Như Điều 3;',
]


class TestTrich(unittest.TestCase):
    def test_trich_loi_van(self):
        qd = qvb.trich_quy_dinh(VAN_BAN, 3)
        chu = [q['chu'] for q in qd]
        self.assertTrue(any('trồng xen' in c and '50%' in c for c in chu))
        self.assertTrue(any('vượt mật độ' in c and '30%' in c for c in chu))
        self.assertTrue(any('không được bồi thường' in c for c in chu))
        self.assertFalse(any('hiệu lực' in c for c in chu))              # Điều hiệu lực thi hành bỏ
        self.assertFalse(any('Căn cứ' in c for c in chu))                 # phần căn cứ trước "QUYẾT ĐỊNH:" bỏ
        self.assertFalse(any(c.endswith(':') for c in chu))               # tiêu đề "Phương pháp đo…:" bỏ
        xen = next(q for q in qd if 'trồng xen' in q['chu'])
        self.assertEqual(xen['dieu'], 'Điều 2 khoản 2')
        self.assertEqual(xen['nguon'], 'điều khoản')
        self.assertEqual(xen['pham_vi'], 'cây trồng xen')

    def test_gop_bang_va_loi_van_khong_trung(self):
        bang = ['Số lượng từ 100 đến <110 chậu. hỗ trợ 95%', 'Số lượng từ 110 đến <120 chậu. hỗ trợ 90%']
        dong = ['QUYẾT ĐỊNH:', 'Điều 6. Hỗ trợ cây trồng trong chậu',
                'Cây cảnh trồng chậu: Số lượng từ 100 đến <110 chậu. hỗ trợ 95%, Số lượng từ 110 đến <120 chậu. hỗ trợ 90%']
        qd = qvb.trich_quy_dinh(dong, 4, bang)
        self.assertEqual([q['nguon'] for q in qd], ['bảng', 'bảng'])     # đoạn lời văn chứa lại các dòng bảng: không lặp

    def test_sach_cau(self):
        self.assertEqual(qvb.sach_cau('2.ˆ Số lượng cây trồng'), 'Số lượng cây trồng')
        self.assertEqual(qvb.sach_cau('5.5 Phương pháp đo'), 'Phương pháp đo')
        self.assertEqual(qvb.sach_cau('Tổng diện tích điều tra, đo đếm.6.'), 'Tổng diện tích điều tra, đo đếm.')
        self.assertEqual(qvb.sach_cau('Số lượng từ 100 đến <110 chậu. hỗ trợ 5%'), 'Số lượng từ 100 đến <110 chậu. hỗ trợ 5%')

    def test_van_ban_chua_gom(self):
        ds = [('48/2025/QĐ-UBND', 'Đơn giá bồi thường cây trồng', 'Còn hiệu lực'),
              ('66/2025/QĐ-UBND', 'Sửa đổi đơn giá cây trồng', 'Còn hiệu lực'),
              ('18/2026/QĐ-UBND', 'Đơn giá nhà, công trình', 'Còn hiệu lực')]
        dong = [['Quyết định số 48/2025/QĐ-UBND']]
        vb = dict(so_hieu='48/2025/QĐ-UBND', trich_yeu='đơn giá cây trồng')
        self.assertEqual(qvb.van_ban_chua_gom(dong, vb, {3}, ds), ['66/2025/QĐ-UBND'])     # bản gốc: thiếu QĐ sửa đổi
        hop_nhat = [['Quyết định số 48/2025/QĐ-UBND được sửa đổi, bổ sung bởi Quyết định số 66/2025/QĐ-UBND']]
        self.assertEqual(qvb.van_ban_chua_gom(hop_nhat, vb, {3}, ds), [])                   # bản hợp nhất: gồm đủ


class _Bo(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        td = Path(self.tmp.name)
        self._cu = os.environ.get('PABT_THU_MUC_MAY')
        os.environ['PABT_THU_MUC_MAY'] = str(td / 'may')
        self.bo = td / 'bo.sqlite'
        shutil.copyfile(don_gia.file_goc(), self.bo)
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


class TestGhi(_Bo):
    def test_ghi_tham_so_va_ghi_chu_muc(self):
        con = csdl.mo(self.bo)
        try:
            ten = con.execute("SELECT ten FROM dm_taisan WHERE nhom = 3 AND ten LIKE '%Keo lá tràm%' LIMIT 1").fetchone()
            self.assertIsNotNone(ten)
            ds = [dict(chu='Đối với keo lá tràm trồng xen thì tính 50% đơn giá.', nhom=3, dieu='Điều 2 khoản 2', pham_vi='keo lá tràm',
                       nguon='điều khoản'),
                  dict(chu='Cây trồng vượt mật độ được hỗ trợ 30%.', nhom=3, dieu='Điều 2 khoản 3', pham_vi='', nguon='điều khoản')]
            with csdl.giao_dich(con), csdl.mo_khoa_danh_muc(con):
                kq = qvb.ghi_quy_dinh(con, dict(so_hieu='99/2026/QĐ-UBND'), ds)
            self.assertEqual(kq['so_quy_dinh'], 2)
            self.assertGreater(kq['so_muc_ghi_chu'], 0)
            r = con.execute("SELECT ma, can_cu FROM tham_so WHERE ma LIKE 'QDCT:%' ORDER BY ma").fetchall()
            self.assertEqual(len(r), 2)
            self.assertIn('99/2026', r[0][1])
            gc = con.execute('SELECT ghi_chu FROM dm_taisan WHERE ten = ?', (ten[0],)).fetchone()[0]
            self.assertIn('Quy định (99/2026/QĐ-UBND)', gc)
            # ghi lại cùng văn bản: thay quy định cũ, không nhân đôi
            with csdl.giao_dich(con), csdl.mo_khoa_danh_muc(con):
                qvb.ghi_quy_dinh(con, dict(so_hieu='99/2026/QĐ-UBND'), ds[1:])
            self.assertEqual(con.execute("SELECT COUNT(*) FROM tham_so WHERE ma LIKE 'QDCT:%'").fetchone()[0], 1)
            ts = {m: g for m, g in con.execute('SELECT ma, gia_tri FROM tham_so')}
        finally:
            con.close()
        self.assertEqual(qvb.quy_dinh_lien_quan(ts, 3, 'Cây vượt mật độ'), ['Cây trồng vượt mật độ được hỗ trợ 30%.'])
        self.assertEqual(qvb.quy_dinh_lien_quan(ts, 2, 'Cây vượt mật độ'), [])            # nhóm nhà không lẫn quy định cây

    def test_ap_dung_chi_luu_quy_dinh(self):
        kq = ndg.ap_dung([], 3, 'thử', van_ban=dict(so_hieu='99/2026/QĐ-UBND', ngay='01/11/2026', trich_yeu='Đơn giá cây trồng'),
                         quy_dinh=[dict(chu='Cây trồng vượt mật độ được hỗ trợ 30%.', nhom=3, dieu='Điều 2', pham_vi='',
                                        nguon='điều khoản')])
        self.assertEqual(kq['so_quy_dinh'], 1)
        con = csdl.mo(don_gia.file_cap_nhat(), chi_doc=True)
        try:
            self.assertEqual(con.execute("SELECT COUNT(*) FROM tham_so WHERE ma LIKE 'QDCT:%'").fetchone()[0], 1)
        finally:
            con.close()


class TestHop(_Bo):
    def test_tu_chon_va_loc(self):
        from tests import APP  # noqa: F401
        from pabt.man_hinh_nhap_don_gia import HIEN_TAT_CA_DUOI, HopNhapDonGia
        con = csdl.mo(self.bo)
        try:
            r = con.execute('SELECT ten, dvt, don_gia FROM dm_taisan WHERE nhom = 2 ORDER BY ma LIMIT 70').fetchall()
        finally:
            con.close()
        bang = [['STT', 'Tên tài sản', 'ĐVT', 'Đơn giá (đồng)']]
        for i, (t, d, g) in enumerate(r, 1):
            bang.append([str(i), t, d, f'{int(g) + (1000 if i == 5 else 0):,}'.replace(',', '.')])   # một dòng đổi giá
        bang += VAN_BAN[5:14]
        HopNhapDonGia.im_lang = True
        try:
            h = HopNhapDonGia(None, dong=[x if isinstance(x, list) else [x] for x in bang], van_ban={}, nhom_uu_tien=2, nguon='thử')
            doi = [i for i, m in enumerate(h.ds) if m.trang_thai == 'cập nhật' and m.ten == r[4][0]]
            self.assertEqual(len(doi), 1)
            self.assertTrue(h.ds[doi[0]].chon)                            # dòng đổi giá chọn sẵn
            self.assertEqual(h.ds[doi[0]].don_gia, int(r[4][2]) + 1000)
            self.assertGreaterEqual(len(h.ds), HIEN_TAT_CA_DUOI)
            self.assertEqual(h.cb_hien.currentData(), 'can')              # văn bản dài: mặc định chỉ hiện dòng cần xử lý
            an = sum(1 for i in range(len(h.ds)) if h.bang.isRowHidden(i))
            self.assertGreater(an, 50)
            self.assertFalse(h.bang.isRowHidden(doi[0]))
            h.cb_hien.setCurrentIndex(1)
            self.assertFalse(any(h.bang.isRowHidden(i) for i in range(len(h.ds))))
            h.chon_theo(False)
            self.assertFalse(any(m.chon for m in h.ds))
            h.chon_theo(True)
            self.assertTrue(h.ds[doi[0]].chon)
            self.assertIsNotNone(h.o_luu_qd)                              # có quy định trong lời văn -> ô lưu quy định
            self.assertIn('trồng xen', h.o_quy_tac.toPlainText())
            h.close()
            h.deleteLater()
        finally:
            HopNhapDonGia.im_lang = False


class _KhachGia:
    """Client giả lập của thư viện anthropic (không gọi mạng): beta.messages.stream(...) -> get_final_message()."""

    def __init__(self, tra_loi: dict, stop: str = 'end_turn'):
        import json
        from types import SimpleNamespace
        self.goi = []
        tl = SimpleNamespace(stop_reason=stop, content=[SimpleNamespace(type='text', text=json.dumps(tra_loi, ensure_ascii=False))])
        khach = self

        class _S:
            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

            def get_final_message(self):
                return tl

        def stream(**kw):
            khach.goi.append(kw)
            return _S()
        self.beta = SimpleNamespace(messages=SimpleNamespace(stream=stream))


class TestAI(_Bo):
    def _hop(self):
        from tests import APP  # noqa: F401
        from pabt.man_hinh_nhap_don_gia import HopNhapDonGia
        con = csdl.mo(self.bo, chi_doc=True)
        try:
            r = con.execute('SELECT ten, dvt, don_gia FROM dm_taisan WHERE nhom = 2 ORDER BY ma LIMIT 6').fetchall()
        finally:
            con.close()
        bang = [['STT', 'Tên tài sản', 'ĐVT', 'Đơn giá (đồng)']]
        for i, (t, d, g) in enumerate(r, 1):
            bang.append([str(i), t, d, f'{int(g) + (1000 if i in (2, 3) else 0):,}'.replace(',', '.')])
        HopNhapDonGia.im_lang = True
        self.addCleanup(setattr, HopNhapDonGia, 'im_lang', False)
        return HopNhapDonGia(None, dong=bang, van_ban={}, nhom_uu_tien=2, nguon='thử'), r

    def test_ai_xac_minh_va_them_quy_dinh(self):
        h, r = self._hop()
        i2 = next(i for i, m in enumerate(h.ds) if m.ten == r[1][0])
        i3 = next(i for i, m in enumerate(h.ds) if m.ten == r[2][0])
        gia2, gia3 = h.ds[i2].don_gia, h.ds[i3].don_gia
        self.assertTrue(h.ds[i2].chon and h.ds[i3].chon)
        khach = _KhachGia(dict(
            van_ban=dict(so_hieu='99/2026/QĐ-UBND', ngay='01/11/2026', trich_yeu='Đơn giá nhà', nhom=[2], sua_doi_boi=[], thay_the=[]),
            quy_dinh=[dict(chu='Nhà xây dựng sau thời điểm thông báo thu hồi đất thì không được bồi thường.', nhom=2, dieu='Điều 3',
                           pham_vi='')],
            xac_minh=[dict(stt=i2, ket_luan='dung', ten=h.ds[i2].ten, dvt=h.ds[i2].dvt, don_gia=gia2, ghi_chu=''),
                      dict(stt=i3, ket_luan='sai', ten=h.ds[i3].ten, dvt=h.ds[i3].dvt, don_gia=gia3 + 9000, ghi_chu='OCR đọc sai')]))
        chu = h.phan_tich_ai(khach=khach, xac_nhan=True)
        self.assertIn('1 đúng', chu)
        self.assertIn('1 AI đọc khác', chu)
        self.assertEqual(h.ds[i2].don_gia, gia2)                         # không bao giờ tự đổi giá theo AI
        self.assertEqual(h.ds[i3].don_gia, gia3)
        self.assertTrue(h.ds[i2].chon)
        self.assertFalse(h.ds[i3].chon)
        self.assertIn('AI đọc', h.ds[i3].cach_khop)
        self.assertIn('AI xác nhận', h.ds[i2].cach_khop)
        self.assertTrue(any(q['nguon'] == 'AI' for q in h.quy_dinh))
        self.assertTrue(h.o_luu_qd.isVisibleTo(h))
        h.khop()                                                         # so khớp lại (đổi nhóm…): kết quả AI giữ nguyên
        self.assertFalse(h.ds[i3].chon)
        kw = khach.goi[0]
        self.assertEqual(kw['output_config']['format']['type'], 'json_schema')
        self.assertEqual(kw['thinking'], {'type': 'adaptive'})
        self.assertIn(f'{i3}\t{h.ds[i3].ten}', kw['messages'][0]['content'])     # dòng cần xem có trong danh sách gửi đi
        h.close()
        h.deleteLater()

    def test_ai_tu_choi_va_tat(self):
        from pabt import phan_tich_ai_don_gia as pai
        h, _ = self._hop()
        self.assertEqual(h.phan_tich_ai(khach=_KhachGia({}, stop='refusal'), xac_nhan=True), '')
        self.assertIsNone(h.ket_qua_ai)
        with mock.patch('pabt.tro_ly.doc_cai_dat', return_value=dict(bat=False)), \
                mock.patch('pabt.tro_ly.co_thu_vien', return_value=True):
            ok, ly_do = pai.dung_duoc()
        self.assertFalse(ok)
        self.assertIn('TẮT', ly_do)
        h.close()
        h.deleteLater()


if __name__ == '__main__':
    unittest.main()

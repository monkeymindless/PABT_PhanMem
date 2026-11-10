"""1.0.58: văn bản, biên bản theo mục của đợt niêm yết; đọc kết quả từ file. Dữ liệu GIẢ LẬP."""
from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from tests import APP  # noqa: F401
from pabt import csdl, du_thao, van_ban_dot as vbd
from pabt.lap_pa import LoiNhap


class TestVanBanDot(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.td = Path(self.tmp.name)
        p = mock.patch.dict(os.environ, {'PABT_THU_MUC_MAY': str(self.td / 'may')})
        p.start()
        self.addCleanup(p.stop)
        self.con = csdl.tao_moi(self.td / 'a.pabt')
        self.addCleanup(self.con.close)
        with self.con:
            self.con.executemany('INSERT INTO ho (ma_ho, thu_tu, ho_ten, so_cccd) VALUES (?,?,?,?)',
                                 [(1, 1, 'Nguyễn Văn An', '079123456789'), (2, 2, 'Trần Thị Bình', ''), (3, 3, 'Lê Văn Cường', ''), (4, 4, 'Ngoài Đợt Này', '')])
        self.dot = du_thao.tao_dot(self.con, 'Đợt 1', '01/11/2026', 'UBND xã')
        du_thao.them_thu_cong(self.con, self.dot, [1, 2, 3], ca_vuong=True)

    def tearDown(self):
        self.doCleanups()
        self.tmp.cleanup()

    def test_luu_sua_xoa_theo_muc(self):
        self.assertEqual(vbd.ds(self.con, self.dot, 'niem_yet'), [])              # chưa có bảng vẫn đọc được
        i = vbd.luu(self.con, self.dot, 'niem_yet', 'Thông báo niêm yết công khai', 'TB-01', '02/11/2026', 'Niêm yết tại UBND xã')
        vbd.luu(self.con, self.dot, 'y_kien', 'Giấy mời lấy ý kiến')
        self.assertEqual([r['loai'] for r in vbd.ds(self.con, self.dot, 'niem_yet')], ['Thông báo niêm yết công khai'])
        self.assertEqual(vbd.dem(self.con, self.dot), {'niem_yet': 1, 'y_kien': 1})
        self.assertEqual(vbd.ds(self.con, self.dot, 'niem_yet')[0]['ngay'][:10], '2026-11-02')
        vbd.luu(self.con, self.dot, 'niem_yet', 'Biên bản niêm yết công khai', id_=i)
        self.assertEqual(vbd.ds(self.con, self.dot, 'niem_yet')[0]['loai'], 'Biên bản niêm yết công khai')
        vbd.xoa(self.con, i)
        self.assertEqual(vbd.ds(self.con, self.dot, 'niem_yet'), [])
        with self.assertRaises(LoiNhap):
            vbd.luu(self.con, self.dot, 'niem_yet', 'X', duong_dan=str(self.td / 'a.exe'))
        with self.assertRaises(LoiNhap):
            vbd.luu(self.con, self.dot, 'niem_yet', '')

    def test_xoa_dot_xoa_van_ban(self):
        vbd.luu(self.con, self.dot, 'y_kien', 'Giấy mời lấy ý kiến')
        du_thao.xoa_dot(self.con, self.dot)
        self.assertEqual(self.con.execute('SELECT COUNT(*) FROM van_ban_dot').fetchone()[0], 0)

    def _doc(self):
        dong = [['STT', 'Họ và tên', 'CCCD', 'Ý kiến'], ['1', 'NGUYỄN VĂN AN', '079 123 456 789', 'Đồng ý với phương án'],
                ['2', 'Trần Thị Bình', '', 'Không đồng ý đơn giá đất, đề nghị tăng'], ['3', 'Lê Văn Cường', '', 'Vắng mặt'],
                ['4', 'Ngoài Đợt Này', '', 'Đồng ý']]
        with mock.patch('pabt.quan_ly.doc_van_ban', return_value=(dong, False)):
            return vbd.doc_ket_qua(self.con, self.dot, ['f.xlsx'])

    def test_doc_va_ap_y_kien(self):
        kq = self._doc()
        theo = {d.ma_ho: d for d in kq['dong']}
        self.assertEqual(sorted(theo), [1, 2, 3])                                  # hộ ngoài đợt không ghép
        self.assertEqual((theo[1].loai, theo[1].khop_theo), ('dong_y', 'CCCD'))
        self.assertEqual(theo[2].loai, 'khong_dong_y')
        self.assertIn('đơn giá đất', theo[2].noi_dung)
        self.assertEqual((theo[3].loai, theo[3].chon), ('', False))                # không rõ: không chọn sẵn
        self.assertEqual(vbd.ap_dung(self.con, self.dot, 'y_kien', kq['dong']), 2)
        r = dict(self.con.execute('SELECT ma_ho, loai FROM y_kien_du_thao WHERE dot_id = ?', (self.dot,)).fetchall())
        self.assertEqual(r, {1: 'dong_y', 2: 'khong_dong_y', 3: 'chua'})

    def test_ap_doi_thoai(self):
        kq = self._doc()
        vbd.ap_dung(self.con, self.dot, 'doi_thoai', kq['dong'], '05/11/2026', 'UBND xã')
        self.assertEqual(self.con.execute('SELECT COUNT(*) FROM doi_thoai_ho').fetchone()[0], 2)

    def test_hop_thoai(self):
        from pabt.man_hinh_du_thao import KhungDuThao
        from pabt.man_hinh_van_ban_dot import HopKetQuaFile, HopVanBanDot
        k = KhungDuThao(self.con)
        self.addCleanup(k.deleteLater)
        k.cb.setCurrentIndex(max(0, k.cb.findData(self.dot)))
        k.tabs.setCurrentIndex(2)
        self.assertEqual(k._muc_hien_tai(), 'doi_thoai')
        HopVanBanDot.im_lang = True
        try:
            h = k.mo_van_ban(cho=False)
            self.assertEqual(h.o_loai.itemText(0), 'Giấy mời đối thoại')
            h.o_so.setText('GM-02')
            self.assertIsNotNone(h.luu())
            self.assertEqual(h.bang.rowCount(), 1)
            h.bang.setCurrentCell(0, 0)
            self.assertEqual(h.o_so.text(), 'GM-02')
            h.xoa()
            self.assertEqual(h.bang.rowCount(), 0)
            h.deleteLater()
        finally:
            del HopVanBanDot.im_lang
        k.tabs.setCurrentIndex(1)
        f = self.td / 'bb.pdf'
        f.write_bytes(b'%PDF-1.4 thu')
        kq = self._doc()
        HopKetQuaFile.im_lang = True
        try:
            with mock.patch('pabt.man_hinh_quan_ly.doc_co_tien_do', return_value=kq):
                h = k.doc_ket_qua([str(f)], cho=False)
            h.accept()
            self.assertEqual(h.so_ghi, 2)
            self.assertEqual(len(vbd.ds(self.con, self.dot, 'y_kien')), 1)         # file kết quả vào văn bản của mục
        finally:
            del HopKetQuaFile.im_lang


if __name__ == '__main__':
    unittest.main()

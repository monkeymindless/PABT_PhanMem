"""Kiểm thử nâng cấp 1.0.28 (chỉ thị "thương mại hóa & tối ưu lõi", người dùng 26/10/2026): GP2 nhận / gộp THEO HỘ trên máy chủ LAN,
GP3 bỏ truy vấn lặp từng hộ khi in Word + bộ nhớ đệm hồ sơ địa phương + PDF dự phòng qua LibreOffice, GP4 mô hình vị trí bảng giá
đất / loại chính sách theo tên (tỉnh khác), GP5 tách in_duong_ke khỏi in_an. Số liệu GIẢ LẬP."""
from __future__ import annotations

import os
import shutil
import sys
import tempfile
import time
import unittest
import zipfile
from pathlib import Path
from unittest import mock

from pabt import chinh_sach, csdl, dia_phuong, gia_dat_nq28, in_an, in_duong_ke, in_word, may_chu, van_ban_trinh
from pabt.may_chu import LoiMayChu
from tests.test_toc_do import _du_an


class _MayChu(unittest.TestCase):
    """Máy chủ LAN giả lập (thư mục tạm) + dự án 6 hộ trong DuAn, hai tài khoản: quantri, nv1."""

    def setUp(self):
        self.td = Path(tempfile.mkdtemp(prefix='pabt_gp2_'))
        self._cu = os.environ.get('PABT_THU_MUC_MAY')
        os.environ['PABT_THU_MUC_MAY'] = str(self.td / 'may')
        self.goc = self.td / 'MayChu'
        may_chu.khoi_tao(self.goc, 'QuanTri', 'matkhau1', 'Quản trị')
        tm = may_chu.thu_muc_du_an(self.goc)
        tm.mkdir(parents=True, exist_ok=True)
        self.f = Path(shutil.move(str(_du_an(self.td, 6)), str(tm / 'DA.pabt')))
        self.qt = may_chu.dang_nhap(self.goc, 'quantri', 'matkhau1')
        may_chu.them_nguoi_dung(self.qt, 'nv1', 'Nhân viên 1', 'abc123')
        self.nv = may_chu.dang_nhap(self.goc, 'nv1', 'abc123')
        self.qt = may_chu.dang_nhap(self.goc, 'quantri', 'matkhau1')

    def tearDown(self):
        may_chu.dang_xuat()
        if self._cu is None:
            os.environ.pop('PABT_THU_MUC_MAY', None)
        else:
            os.environ['PABT_THU_MUC_MAY'] = self._cu
        shutil.rmtree(self.td, ignore_errors=True)

    @staticmethod
    def sua(f, *lenh):
        con = csdl.mo(f)
        try:
            with con:
                for sql, ts in lenh:
                    con.execute(sql, ts)
        finally:
            con.close()

    @staticmethod
    def doc(f, sql, ts=()):
        con = csdl.mo(f, chi_doc=True)
        try:
            return [tuple(r) for r in con.execute(sql, ts)]
        finally:
            con.close()


THEM_THUA = ("INSERT INTO thua (ma_thua, ma_ho, so_to, so_thua, loai_dat, dt_thu_hoi, thu_tu) "
             "VALUES ((SELECT MAX(ma_thua) + 1 FROM thua), ?, ?, ?, 'CLN', '77', 9)")
DAT_THUA_MOI = ("INSERT INTO ct_dat (ma_ho, ma_thua, loai_dat, dien_tich, gia_bang_gia) "
                "VALUES (?, (SELECT MAX(ma_thua) FROM thua), 'CLN', '77', '250000')")


class TestGiaiPhap2(_MayChu):
    def test_giai_phap_2_gop_ho_lan_khong_ghi_de_ho_khac(self):
        f = self.f
        truoc_ho_5 = self.doc(f, 'SELECT * FROM ho WHERE ma_ho = 5')
        truoc_thua_5 = self.doc(f, 'SELECT * FROM thua WHERE ma_ho = 5 ORDER BY ma_thua')
        bs1 = may_chu.lay_ve_theo_ho(f, [1, 2], self.qt)
        with self.assertRaises(LoiMayChu):
            may_chu.lay_ve_theo_ho(f, [2, 3], self.nv)               # hộ 2 đang được quantri nhận
        with self.assertRaises(LoiMayChu):
            may_chu.lay_ve(f, self.nv)                               # mang cả dự án về sẽ ghi đè hộ người khác đang làm
        bs2 = may_chu.lay_ve_theo_ho(f, [3, 4], self.nv)
        self.assertNotEqual(bs1, bs2)
        dang = may_chu.ds_ho_dang_lay_ve(f, self.goc)
        self.assertEqual({m: x['tai_khoan'] for m, x in dang.items()}, {1: 'quantri', 2: 'quantri', 3: 'nv1', 4: 'nv1'})
        self.assertEqual(len(may_chu.ds_lay_ve_cuc_bo()), 2)
        # hai người sửa độc lập; cả hai thêm thửa mới -> hai bản offline cấp CÙNG mã thửa (max + 1) cho hai thửa khác nhau
        self.sua(bs1, ("UPDATE ho SET ho_ten = 'Chủ hộ 1 (sửa offline)' WHERE ma_ho = 1", ()),
                 (THEM_THUA, (1, '90', '901')), (DAT_THUA_MOI, (1,)),
                 ("INSERT INTO ct_khoan (muc, ma_ho, ten, dvt, so_luong, don_gia) VALUES (2, 2, 'Nhà tạm', 'm²', '20', '1000000')", ()),
                 ("UPDATE ho SET ho_ten = 'KHÔNG được gộp' WHERE ma_ho = 5", ()))       # hộ 5 không nhận: sửa trên bản offline bị bỏ
        self.sua(bs2, ("UPDATE ho SET ho_ten = 'Chủ hộ 4 (nv1)' WHERE ma_ho = 4", ()),
                 (THEM_THUA, (3, '91', '911')), (DAT_THUA_MOI, (3,)))
        moi_1 = self.doc(bs1, 'SELECT MAX(ma_thua) FROM thua')[0][0]
        self.assertEqual(moi_1, self.doc(bs2, 'SELECT MAX(ma_thua) FROM thua')[0][0])

        kq1 = may_chu.gop_ho_tu_ban_offline(bs1, phien=self.qt)
        self.assertEqual((kq1['so_ho'], kq1['ma_ho'], kq1['doi_ma_thua']), (2, [1, 2], {}))
        kq2 = may_chu.dua_len(bs2, self.nv)                         # "Đưa lên" bản theo hộ = gộp đúng các hộ đó
        self.assertEqual(kq2, f)

        ten = dict(self.doc(f, 'SELECT ma_ho, ho_ten FROM ho'))
        self.assertEqual(ten[1], 'Chủ hộ 1 (sửa offline)')
        self.assertEqual(ten[4], 'Chủ hộ 4 (nv1)')
        self.assertEqual(self.doc(f, 'SELECT * FROM ho WHERE ma_ho = 5'), truoc_ho_5)
        self.assertEqual(self.doc(f, 'SELECT * FROM thua WHERE ma_ho = 5 ORDER BY ma_thua'), truoc_thua_5)
        t1 = self.doc(f, "SELECT ma_thua FROM thua WHERE ma_ho = 1 AND so_thua = '901'")
        t3 = self.doc(f, "SELECT ma_thua FROM thua WHERE ma_ho = 3 AND so_thua = '911'")
        self.assertEqual(t1, [(moi_1,)])
        self.assertEqual(len(t3), 1)
        self.assertNotEqual(t3[0][0], moi_1)                        # trùng mã -> cấp mã mới
        # dòng đất của thửa mới trỏ đúng thửa của hộ mình
        self.assertEqual(self.doc(f, "SELECT ma_ho FROM ct_dat WHERE ma_thua = ?", t3[0]), [(3,)])
        self.assertEqual(self.doc(f, "SELECT ma_ho FROM ct_dat WHERE ma_thua = ?", t1[0]), [(1,)])
        self.assertEqual(self.doc(f, "SELECT COUNT(*) FROM ct_khoan WHERE ma_ho = 2 AND ten = 'Nhà tạm'"), [(1,)])
        self.assertEqual(self.doc(f, 'PRAGMA foreign_key_check'), [])
        self.assertEqual(self.doc(f, 'PRAGMA integrity_check'), [('ok',)])
        self.assertEqual(may_chu.ds_ho_dang_lay_ve(f, self.goc), {})
        self.assertEqual(may_chu.ds_lay_ve_cuc_bo(), [])
        self.assertFalse(bs1.exists() or bs2.exists())
        self.assertEqual(len(list((self.goc / may_chu.THU_MUC_SAO_LUU).glob('DA_truoc_gop_*.pabt'))) >= 1, True)
        self.assertTrue(any(r[0] == 'Gộp hộ từ bản offline' for r in self.doc(f, 'SELECT viec FROM nhat_ky')))

    def test_xung_dot_khi_ho_bi_sua_tren_may_chu(self):
        bs = may_chu.lay_ve_theo_ho(self.f, [5], self.qt)
        self.sua(self.f, ("UPDATE ho SET ghi_chu = 'sửa thẳng trên máy chủ' WHERE ma_ho = 5", ()))
        self.sua(bs, ("UPDATE ho SET ghi_chu = 'sửa offline' WHERE ma_ho = 5", ()))
        with self.assertRaises(LoiMayChu) as e:
            may_chu.gop_ho_tu_ban_offline(bs, phien=self.qt)
        self.assertIn('XUNG ĐỘT', str(e.exception))
        self.assertEqual(self.doc(self.f, 'SELECT ghi_chu FROM ho WHERE ma_ho = 5'), [('sửa thẳng trên máy chủ',)])
        may_chu.gop_ho_tu_ban_offline(bs, phien=self.qt, ep=True)
        self.assertEqual(self.doc(self.f, 'SELECT ghi_chu FROM ho WHERE ma_ho = 5'), [('sửa offline',)])

    def test_gop_mot_phan_va_tra_lai(self):
        bs = may_chu.lay_ve_theo_ho(self.f, [1, 2, 6], self.qt)
        self.sua(bs, ("UPDATE ho SET ghi_chu = 'x' WHERE ma_ho IN (1, 2)", ()))
        may_chu.gop_ho_tu_ban_offline(bs, [1], phien=self.qt)
        self.assertEqual(sorted(may_chu.ds_ho_dang_lay_ve(self.f, self.goc)), [2, 6])
        self.assertEqual(may_chu.ds_lay_ve_cuc_bo()[0]['ds_ma_ho'], [2, 6])
        self.assertTrue(bs.exists())                                # còn hộ chưa gộp: giữ bản offline
        self.assertEqual(may_chu.huy_lay_ve_ho(self.f, [6], self.qt), 1)
        may_chu.huy_lay_ve(bs, self.qt)
        self.assertEqual(may_chu.ds_ho_dang_lay_ve(self.f, self.goc), {})
        self.assertFalse(bs.exists())
        self.assertEqual(self.doc(self.f, 'SELECT ghi_chu FROM ho WHERE ma_ho = 2'), [('',)])    # hủy: không gộp
        with self.assertRaises(LoiMayChu):
            may_chu.lay_ve_theo_ho(self.f, [99], self.qt)           # hộ không có: trả lại chỗ đã giữ
        self.assertEqual(may_chu.ds_ho_dang_lay_ve(self.f, self.goc), {})


class TestGiaiPhap3(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.p = _du_an(Path(self.td.name), 25)
        self.con = csdl.mo(self.p)

    def tearDown(self):
        self.con.close()
        self.td.cleanup()

    def test_giai_phap_3_triet_tieu_sql_n_cong_1_va_bo_nho_dem(self):
        ds = [r[0] for r in self.con.execute('SELECT ma_ho FROM ho ORDER BY thu_tu LIMIT 20')]
        ra = Path(self.td.name) / 'word'
        truoc = {}
        for m in ds:                                               # làm ấm bộ nhớ đệm (lần in đầu đọc cả dự án một lượt)
            truoc[m] = zipfile.ZipFile(in_word.xuat_chi_tiet_docx(self.con, m, ra / f'{m}.docx')).read('word/document.xml')
        cau = []
        self.con.set_trace_callback(cau.append)
        try:
            for m in ds:
                sau = zipfile.ZipFile(in_word.xuat_chi_tiet_docx(self.con, m, ra / f'{m}b.docx')).read('word/document.xml')
                self.assertEqual(sau, truoc[m])
        finally:
            self.con.set_trace_callback(None)
        self.assertEqual([c for c in cau if c.lstrip().upper().startswith('SELECT')], [])
        # dữ liệu đổi -> bộ nhớ đệm tự đọc lại (không in số liệu cũ)
        with self.con:
            self.con.execute("UPDATE ho SET ho_ten = 'Tên mới sau khi sửa' WHERE ma_ho = ?", (ds[0],))
        xml = zipfile.ZipFile(in_word.xuat_chi_tiet_docx(self.con, ds[0], ra / 'moi.docx')).read('word/document.xml')
        self.assertIn('Tên mới sau khi sửa'.encode('utf-8'), xml)

    def test_ban_in_giong_khi_khong_dung_bo_nho(self):
        """Đường nhớ (kết nối csdl.KetNoi) và đường đọc từng hộ (giữa giao dịch) ra cùng một văn bản."""
        ds = [r[0] for r in self.con.execute('SELECT ma_ho FROM ho ORDER BY thu_tu LIMIT 5')]
        nho = {m: in_word.noi_dung_chi_tiet(self.con, m) for m in ds}
        self.con.execute("UPDATE du_an SET nam = nam WHERE id = 1")          # mở giao dịch: mọi hàm đọc riêng từng hộ
        self.assertTrue(self.con.in_transaction)
        try:
            for m in ds:
                self.assertEqual(in_word.noi_dung_chi_tiet(self.con, m), nho[m])
        finally:
            self.con.rollback()

    def test_dia_phuong_lay_nhanh(self):
        dia_phuong.lay('ban_in')
        t = time.perf_counter()
        for _ in range(2000):
            dia_phuong.lay('kinh_phi_to_chuc.lam_tron_den')
        self.assertLess(time.perf_counter() - t, 0.05)

    def test_dia_phuong_ghi_thay_ngay(self):
        with tempfile.TemporaryDirectory() as td, mock.patch.dict(os.environ, {'PABT_THU_MUC_MAY': td}):
            try:
                dia_phuong.nap_lai()
                self.assertIsNone(dia_phuong.lay('bang_gia_dat.mo_hinh_vi_tri'))
                dia_phuong.dat_muc_may(('bang_gia_dat',), {'mo_hinh_vi_tri': 'VI_TRI_1_4'})
                self.assertEqual(gia_dat_nq28.mo_hinh_vi_tri(), 'VI_TRI_1_4')        # ghi qua phần mềm: thấy ngay
            finally:
                dia_phuong.khoi_phuc_mac_dinh()
        dia_phuong.nap_lai()
        self.assertEqual(gia_dat_nq28.mo_hinh_vi_tri(), 'DONG_NAI_NQ28')

    def test_vbs_word_xoa_hoan_tac(self):
        self.assertLess(van_ban_trinh._VBS_WORD.index('d.UndoClear'), van_ban_trinh._VBS_WORD.index('d.Close 0'))

    def test_pdf_du_phong_libreoffice(self):
        td = Path(self.td.name)
        gia = td / 'LibreOffice' / 'program' / 'soffice.com'
        gia.parent.mkdir(parents=True)
        gia.write_bytes(b'')
        a, b = td / 'PA_001.docx', td / 'PA_001.pdf'
        a.write_bytes(b'docx gia lap')
        viec = [('pdf', a, b)]
        loi = [f'LOI_MO\t{a.resolve()}\tWord treo']
        tao_pdf = ('import sys, pathlib; ra = pathlib.Path(sys.argv[1])\n'
                   'for f in sys.argv[2:]: (ra / (pathlib.Path(f).stem + ".pdf")).write_bytes(b"%PDF-1.4 gia lap")')

        def lenh(soffice, ho_so, thu_muc_ra, files):
            self.assertEqual(soffice, gia)
            return [sys.executable, '-c', tao_pdf, str(thu_muc_ra), *map(str, files)]
        with mock.patch.dict(os.environ, {'PABT_LIBREOFFICE': str(gia.parent)}), \
                mock.patch.object(van_ban_trinh, '_lenh_libreoffice', lenh):
            self.assertEqual(van_ban_trinh.tim_libreoffice(), gia)
            loi_con, du = van_ban_trinh.pdf_du_phong_chi_tiet(viec, loi)
        self.assertEqual((du, loi_con), ([b], []))
        self.assertTrue(b.read_bytes().startswith(b'%PDF'))
        with mock.patch.dict(os.environ, {'PABT_LIBREOFFICE': str(td / 'khong_co'), 'ProgramFiles': str(td / 'x'),
                                          'ProgramW6432': str(td / 'x'), 'ProgramFiles(x86)': str(td / 'x'), 'PATH': ''}):
            self.assertIsNone(van_ban_trinh.tim_libreoffice())
            self.assertEqual(van_ban_trinh.chuyen_pdf_libreoffice([('pdf', a, td / 'khac.pdf')]), [])


class TestGiaiPhap4(unittest.TestCase):
    def test_giai_phap_4_da_mo_hinh_vi_tri_va_chinh_sach_34_tinh(self):
        self.assertEqual(gia_dat_nq28.ds_ma_vi_tri('DONG_NAI_NQ28'), ('MT', 'T1', 'T2', 'T3', 'K1', 'K2', 'K3'))
        self.assertEqual(gia_dat_nq28.ds_ma_vi_tri('vi_tri_1_4'), ('VT1', 'VT2', 'VT3', 'VT4'))
        kv = gia_dat_nq28.ds_ma_vi_tri('KHU_VUC_VI_TRI')
        self.assertEqual((len(kv), kv[0], kv[-1]), (12, 'KV1-VT1', 'KV3-VT4'))
        self.assertEqual(gia_dat_nq28.ds_ma_vi_tri('KHONG_CO'), gia_dat_nq28.ds_ma_vi_tri('DONG_NAI_NQ28'))
        self.assertEqual(gia_dat_nq28.mo_hinh_vi_tri(), 'DONG_NAI_NQ28')            # hồ sơ chưa ghi
        self.assertEqual(gia_dat_nq28.ten_vi_tri('KV2-VT3'), 'Khu vực 2, Vị trí 3')
        self.assertEqual(gia_dat_nq28.ten_vi_tri('T1'), gia_dat_nq28.TEN_VT['T1'])
        self.assertEqual(dia_phuong.MO_HINH_VI_TRI, tuple(gia_dat_nq28.MO_HINH_VI_TRI))
        # chính sách: mã Đồng Nai như cũ; tỉnh khác (mã lạ) nhận theo tên khoản
        self.assertEqual([chinh_sach.loai(m) for m in ('CS1', 'CS9', 'XYZ')], ['od', 'dt', ''])
        for ten, ky_vong in (('Hỗ trợ ổn định đời sống và sản xuất', 'od'), ('HỖ TRỢ ỔN ĐỊNH ĐỜI SỐNG', 'od'),
                             ('Hỗ trợ đào tạo, chuyển đổi nghề và tìm kiếm việc làm', 'dt'), ('Hỗ trợ tiền thuê nhà ở', 'tn'),
                             ('Hỗ trợ tạm cư', 'tn'), ('Hỗ trợ tự lo chỗ ở', 'tn'), ('Bố trí tái định cư', 'tdc'),
                             ('Hỗ trợ di chuyển tài sản', ''), ('Hỗ trợ đào tạo', '')):
            self.assertEqual(chinh_sach.loai('HT_LA', ten), ky_vong, ten)
        self.assertEqual(chinh_sach.loai('HT_LA'), '')                               # không có tên: như trước

    def test_ho_so_ma_chinh_sach_va_kiem_tra(self):
        with tempfile.TemporaryDirectory() as td, mock.patch.dict(os.environ, {'PABT_THU_MUC_MAY': td}):
            try:
                dia_phuong.dat_muc_may(('chinh_sach_ho_tro',), {'ma_tdc': ['TDC01']})
                self.assertEqual(chinh_sach.loai('TDC01'), 'tdc')
                self.assertEqual(chinh_sach.loai('CS1'), 'od')                       # nhóm khác giữ mã mặc định
                with self.assertRaises(dia_phuong.LoiHoSo):
                    dia_phuong.dat_muc_may(('bang_gia_dat',), {'mo_hinh_vi_tri': 'SAI'})
                with self.assertRaises(dia_phuong.LoiHoSo):
                    dia_phuong.dat_muc_may(('chinh_sach_ho_tro',), {'ma_tdc': 'TDC01'})
            finally:
                dia_phuong.khoi_phuc_mac_dinh()
        dia_phuong.nap_lai()


class TestGiaiPhap5(unittest.TestCase):
    def test_giai_phap_5_tach_mo_dun_ve_tinh_re_export(self):
        for ten in ('_DS_DR', '_DS_A', '_DS_R', '_NET', '_them_bo_qua_loi', 'chen_duong_ke', 'doc_duong_ke', 'ghi_zip_nguyen_tu',
                    '_ghi_zip'):
            self.assertIs(getattr(in_an, ten), getattr(in_duong_ke, ten), ten)
        import openpyxl
        with tempfile.TemporaryDirectory() as td:
            f = Path(td) / 'a.xlsx'
            wb = openpyxl.Workbook()
            wb.active['A1'] = 'Thử'
            wb.save(f)
            self.assertEqual(in_duong_ke.doc_duong_ke(f), '')
            neo = ('<xdr:twoCellAnchor><xdr:from><xdr:col>0</xdr:col><xdr:colOff>0</xdr:colOff><xdr:row>1</xdr:row>'
                   '<xdr:rowOff>0</xdr:rowOff></xdr:from><xdr:to><xdr:col>2</xdr:col><xdr:colOff>0</xdr:colOff><xdr:row>1</xdr:row>'
                   '<xdr:rowOff>0</xdr:rowOff></xdr:to><xdr:sp><xdr:spPr>' + in_an._NET + '</xdr:spPr></xdr:sp>'
                   '<xdr:clientData/></xdr:twoCellAnchor>')
            self.assertTrue(in_an.chen_duong_ke(f, neo, 'C9'))
            self.assertEqual(in_duong_ke.doc_duong_ke(f), neo)
            self.assertFalse((Path(td) / 'a.xlsx.tmp').exists())
            with zipfile.ZipFile(f) as z:
                self.assertIn('numberStoredAsText', z.read('xl/worksheets/sheet1.xml').decode('utf-8'))
            self.assertEqual(openpyxl.load_workbook(f).active['A1'].value, 'Thử')        # file vẫn mở được


if __name__ == '__main__':
    unittest.main()

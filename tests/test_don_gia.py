"""Kiểm thử bộ đơn giá tích hợp, khóa danh mục, cập nhật (file / Internet), dự án mới từ dữ liệu thô, các màn hình mới."""
from __future__ import annotations
import hashlib
import json
import os
import sqlite3
import tempfile
import unittest
from pathlib import Path

from pabt import csdl, don_gia, du_an_moi, lap_pa, nghiep_vu, nhap_tho
from pabt.lap_pa import LoiNhap
from tests.test_nghiep_vu import FILE_EXCEL

try:
    import PySide6  # noqa: F401
    CO_QT = True
except ImportError:
    CO_QT = False

DONG = [dict(ho_ten='Nguyễn Văn A', dia_chi='ấp 1', so_cccd='075123456789', ngay_cap='01/02/2021', noi_cap='Cục CS QLHC',
             dien_thoai='0909', nhan_khau='5', so_to='35', so_thua='10', loai_dat='CLN', dt_thu_hoi='400', vi_tri='1'),
        dict(so_to='35', so_thua='11', loai_dat='ONT', dt_thu_hoi='100,5', vi_tri='1'),          # thửa tiếp của hộ A
        dict(ho_ten='Trần Thị B', dia_chi='ấp 2', so_to='36', so_thua='5', loai_dat='LUK', dt_thu_hoi='1.200'),  # thiếu vị trí
        dict(ho_ten='Lê C', dia_chi='ấp 2', so_to='36', so_thua='6', loai_dat='XYZ', dt_thu_hoi='50', vi_tri='2'),
        dict()]


class CoSo(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.td = Path(self.tmp.name)
        self._cu = os.environ.get('PABT_THU_MUC_MAY')
        os.environ['PABT_THU_MUC_MAY'] = str(self.td / 'may')

    def tearDown(self):
        if self._cu is None:
            os.environ.pop('PABT_THU_MUC_MAY', None)
        else:
            os.environ['PABT_THU_MUC_MAY'] = self._cu
        self.tmp.cleanup()


class TestBoDonGia(CoSo):
    def test_bo_tich_hop(self):
        tt = don_gia.kiem_tra_bo(don_gia.file_goc())
        self.assertEqual(tt['so_ho'], 0)                         # không chứa hồ sơ hộ
        self.assertGreater(tt['dem']['dm_taisan'], 5000)
        self.assertGreaterEqual(tt['dem']['dm_hotro'], 39)
        self.assertEqual(tt['dem']['dm_xa'], 0)
        so_hieu = ' '.join(v['so_hieu'] for v in tt['van_ban'])
        for qd in ('42/2025', '18/2026', '53/2026', '48/2025', '66/2025'):
            self.assertIn(qd, so_hieu)
        ts = {r[0]: r[1] for r in sqlite3.connect(don_gia.file_goc()).execute('SELECT ma, gia_tri FROM tham_so')}
        self.assertEqual((ts['HM_CHN'], ts['HM_CLN'], ts['HM_RUNG']), ('30000', '100000', '300000'))   # Điều 176, Đông Nam Bộ
        self.assertEqual(don_gia.file_dang_dung(), don_gia.file_goc())

    def test_vat_nuoi_qd31(self):
        """Bộ tích hợp có đủ đơn giá vật nuôi QĐ 31/2025/QĐ-UBND (trước 0.9.17 chỉ có tên văn bản, không có mục nào) và đúng với
        tao_bo_don_gia.BO_SUNG (đóng gói lại từ Excel không làm mất)."""
        import tao_bo_don_gia as tao
        c = sqlite3.connect(don_gia.file_goc())
        try:
            co = {r[0]: tuple(r[1:]) for r in c.execute(
                "SELECT ma, nhom, phan_loai, ten, dvt, don_gia, ghi_chu FROM dm_taisan WHERE ma LIKE 'VN%'")}
            vb = [r[0] for r in c.execute("SELECT noi_dung FROM van_ban WHERE so_hieu LIKE '%31/2025/QĐ-UBND%'")]
        finally:
            c.close()
        self.assertEqual(co, {r[0]: tuple(r[1:]) for r in tao.BO_SUNG})
        self.assertEqual(len(co), 17)
        self.assertTrue(all(r[0] == 3 and r[1].startswith(don_gia.PHAN_LOAI_VAT_NUOI) for r in co.values()))
        self.assertEqual(co['VN13'][2:5], ('Ao nuôi cá - Nuôi thâm canh (nuôi dưới 50% định mức KT-KT thời gian nuôi)', 'ha/vụ',
                                           '621600000'))
        self.assertEqual(co['VN17'][2:5], ('Chim yến (theo giá thị trường, tối đa)', 'kg yến thô', '18500000'))
        self.assertEqual(len(vb), 1)                            # sửa dòng văn bản cũ, không thêm dòng trùng
        self.assertIn('VN1 - VN17', vb[0])
        # mục 3 của phương án: chọn được từ danh mục như cây trồng
        con = csdl.tao_moi(self.td / 'vn.pabt')
        try:
            don_gia.ap_vao_du_an(con)
            dm = lap_pa.DanhMuc(con)
            # từ 0.9.21 vật nuôi là mục riêng (MUC_VN, in là mục 4): không còn lẫn trong danh sách cây trồng
            self.assertIn('VN15', {m.ma for m in dm.muc[nghiep_vu.MUC_VN]})
            self.assertNotIn('VN15', {m.ma for m in dm.muc[3]})
            self.assertEqual({f'VN{i}' for i in range(1, 18)}, {m.ma for m in dm.tim(nghiep_vu.MUC_VN, '', 500)})
        finally:
            con.close()

    def test_nhap_excel_tho_lay_bo_don_gia(self):
        from tests.test_nhap_tho import _don_gian, _ghi
        xl = self.td / 'ds.xlsx'
        _ghi(xl, _don_gian)
        p = self.td / 'tho.pabt'
        nhap_tho.nhap(xl, p, 'Dự án thô')
        con = csdl.mo(p)
        try:
            self.assertEqual(con.execute('SELECT phien_ban_gia FROM du_an').fetchone()[0], don_gia.thong_tin()['phien_ban'])
            self.assertGreater(con.execute('SELECT COUNT(*) FROM dm_taisan').fetchone()[0], 5000)
        finally:
            con.close()

    def test_khoa_danh_muc(self):
        con = csdl.tao_moi(self.td / 'a.pabt')
        don_gia.ap_vao_du_an(con)
        for sql in ("UPDATE dm_taisan SET don_gia = '1'", "DELETE FROM dm_hotro", "INSERT INTO tham_so (ma) VALUES ('X')",
                    "UPDATE bieu_thuong SET muc = '0'"):
            with self.assertRaises(sqlite3.IntegrityError, msg=sql) as cm:
                with con:
                    con.execute(sql)
            self.assertIn('cố định', str(cm.exception))
        self.assertGreater(con.execute('SELECT COUNT(*) FROM dm_hotro').fetchone()[0], 0)
        self.assertEqual(con.execute('SELECT phien_ban_gia FROM du_an').fetchone()[0], don_gia.thong_tin()['phien_ban'])
        con.close()

    def test_cap_nhat_tu_goi_va_internet(self):
        goi = self.td / 'goi.sqlite'
        con = csdl.tao_moi(goi)
        csdl.chep_danh_muc(con, don_gia.file_goc(), don_vi=False, bang=don_gia.BANG_BO)
        with con, csdl.mo_khoa_danh_muc(con):
            con.execute("UPDATE dm_hotro SET don_gia = '20000000' WHERE ma = 'CS14'")
            con.execute("UPDATE du_an SET ten = 'Bộ thử', phien_ban_gia = '2099.01.01'")
        con.close()
        tb = dict(phien_ban='2099.01.01', tai_ve=goi.as_uri(), sha256=hashlib.sha256(goi.read_bytes()).hexdigest(),
                  ghi_chu='thử')
        url = self.td / 'tb.json'
        url.write_text(json.dumps(tb), encoding='utf-8')
        self.assertEqual(don_gia.kiem_tra_mang(url.as_uri())['phien_ban'], '2099.01.01')
        with self.assertRaises(LoiNhap):
            don_gia.tai_va_cai(dict(tb, sha256='00'))
        tt = don_gia.tai_va_cai(tb)
        self.assertEqual(tt['phien_ban'], '2099.01.01')
        self.assertEqual(don_gia.file_dang_dung(), don_gia.file_cap_nhat())
        self.assertIsNone(don_gia.kiem_tra_mang(url.as_uri()))                         # đã mới nhất
        con = csdl.tao_moi(self.td / 'b.pabt')
        don_gia.ap_vao_du_an(con)
        self.assertEqual(con.execute("SELECT don_gia FROM dm_hotro WHERE ma = 'CS14'").fetchone()[0], '20000000')
        con.close()
        with self.assertRaises(LoiNhap):
            don_gia.kiem_tra_mang('')
        # gói có hồ sơ hộ thì không nhận
        x = self.td / 'co_ho.pabt'
        nhap_tho.nhap(Path(__file__).with_name('__init__.py'), x) if False else None
        con = csdl.tao_moi(x)
        csdl.chep_danh_muc(con, goi, don_vi=False, bang=don_gia.BANG_BO)
        with con:
            con.execute("UPDATE du_an SET phien_ban_gia = '2100.01.01'")
            con.execute("INSERT INTO ho (ma_ho, thu_tu, ho_ten) VALUES (1, 1, 'Hộ')")
        con.close()
        with self.assertRaises(LoiNhap):
            don_gia.cap_nhat_tu_file(x)

    @unittest.skipUnless(FILE_EXCEL.exists(), 'không có file Excel mẫu')
    def test_tao_bo_tu_excel(self):
        tt = don_gia.cap_nhat_tu_file(FILE_EXCEL, '2098.01.01') if False else don_gia.tao_bo_tu_excel(
            FILE_EXCEL, self.td / 'bo.sqlite', '2098.01.01', theo_doi=[('VB thử', 'UBND', 'nội dung', 'Theo dõi')])
        self.assertEqual((tt['phien_ban'], tt['so_ho'], tt['dem']['gia_dat'] if 'gia_dat' in tt['dem'] else 0), ('2098.01.01', 0, 0))
        self.assertIn('VB thử', [v['so_hieu'] for v in tt['van_ban']])


class TestDuAnMoi(CoSo):
    def test_gom_va_bang_gia(self):
        ho, thua, loi, cb = du_an_moi.gom(DONG)
        self.assertEqual(loi, [])
        self.assertEqual([(h['ho_ten'], h['nhan_khau']) for h in ho], [('Nguyễn Văn A', 5), ('Trần Thị B', None), ('Lê C', None)])
        self.assertEqual([(t['ma_ho'], t['dt_thu_hoi']) for t in thua], [(1, '400'), (1, '100.5'), (2, '1200'), (3, '50')])
        bg = {(g['loai_dat'], g['vi_tri']): g for g in du_an_moi.bang_gia_can_nhap(DONG)}
        self.assertEqual(set(bg), {('CLN', '1'), ('ONT', '1'), ('LUK', ''), ('', '2')})
        self.assertIn('chưa có vị trí', bg[('LUK', '')]['ghi_chu'])
        self.assertIn('không có trong danh mục', bg[('', '2')]['ghi_chu'])
        self.assertTrue(du_an_moi.gom([dict(so_to='1', so_thua='2', dt_thu_hoi='3')])[2])     # dòng đầu chưa có họ tên
        self.assertTrue(du_an_moi.gom([dict(ho_ten='A', so_to='1', so_thua='2', dt_thu_hoi='abc')])[2])

    def test_tao_du_an_tu_lap_phuong_an(self):
        gia = [dict(loai_dat='CLN', vi_tri='1', gia='200.000', he_so_k='1,2'), dict(loai_dat='ONT', vi_tri='1', gia='1.000.000'),
               dict(loai_dat='LUK', vi_tri='', vi_tri_ap='2', gia='150000')]
        tt = dict(ten='Dự án thử', cap_dia_ban='Xã', ten_dia_ban='Bàu Hàm', nam='2026', nguoi_ky='Người Ký')
        p = self.td / 'moi.pabt'
        kq = du_an_moi.tao_du_an(p, tt, DONG, gia)
        self.assertEqual((kq['so_ho'], kq['so_thua'], kq['so_ho_co_pa']), (3, 4, 2))
        self.assertTrue(any('Lê C' in x and 'danh mục' in x for x in kq['canh_bao']))
        con = csdl.mo(p)
        try:
            dat = {(r['ma_ho'], r['loai_dat']): (r['dien_tich'], r['gia_bang_gia'], r['he_so_k'], r['vi_tri'])
                   for r in con.execute('SELECT * FROM ct_dat')}
            self.assertEqual(dat[(1, 'CLN')], ('400', '200000', '1.2', '1'))
            self.assertEqual(dat[(2, 'LUK')], ('1200', '150000', '1', '2'))          # vị trí áp dụng
            ht = [r[0] for r in con.execute("SELECT ma FROM ct_khoan WHERE ma_ho = 1 AND muc = 4")]
            self.assertIn('CS9', ht)                                               # đào tạo, chuyển đổi nghề
            self.assertEqual(con.execute("SELECT nhan_khau FROM ho WHERE ma_ho = 1").fetchone()[0], 5)
            self.assertEqual(lap_pa.doc_du_an(con)['nguoi_ky'], 'Người Ký')
            h = con.execute('SELECT so_cccd, ngay_cap, noi_cap, dien_thoai FROM ho WHERE ma_ho = 1').fetchone()
            self.assertEqual(tuple(h), ('075123456789', '01/02/2021', 'Cục CS QLHC', '0909'))
            # vùng dữ liệu thô riêng: giữ nguyên các dòng nhập, liên kết hộ / thửa; không thuộc vùng đơn giá (không bị khóa)
            tho = con.execute('SELECT dong, ho_ten, ngay_cap, so_thua, dt_thu_hoi, ma_ho, ma_thua FROM tho_nhap ORDER BY dong').fetchall()
            self.assertEqual([tuple(r) for r in tho][:2], [(1, 'Nguyễn Văn A', '01/02/2021', '10', '400', 1, 1),
                                                          (2, '', '', '11', '100,5', 1, 2)])
            self.assertEqual(len(tho), 4)
            self.assertNotIn('tho_nhap', csdl.DANH_MUC)
            with con:
                con.execute("UPDATE tho_nhap SET ghi_chu = 'sửa được' WHERE dong = 1")
            self.assertGreater(con.execute('SELECT COUNT(*) FROM dm_taisan').fetchone()[0], 5000)
            kq_in = du_an_moi.xuat_2_bang(con, self.td / 'in')
            self.assertEqual(len(kq_in['word']), 2)                                  # 22/10/2026: phương án chi tiết bản Word
            self.assertEqual([p.name for p in kq_in['excel']], ['BANG_TONG_HOP.xlsx'])
        finally:
            con.close()
        with self.assertRaises(LoiNhap):
            du_an_moi.tao_du_an(self.td / 'x.pabt', dict(ten=''), DONG, gia)


@unittest.skipUnless(CO_QT, 'không có PySide6')
class TestManHinhMoi(CoSo):
    @classmethod
    def setUpClass(cls):
        os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
        from PySide6.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication([])

    def test_hop_du_an_moi(self):
        from pabt.man_hinh_du_an_moi import HopDuAnMoi
        from tests.test_nhap_tho import _don_gian, _ghi
        d = HopDuAnMoi(luu_cai_dat=False)
        d.im_lang = True
        from pabt import to_chuc
        self.assertEqual(d.o['don_vi_lap'].text(), to_chuc.MAC_DINH['don_vi_lap'])   # điền sẵn đơn vị
        self.assertFalse(d.sang(1))                              # chưa nhập tên dự án
        d.o['ten'].setText('Dự án thử')
        d.o['ten_dia_ban'].setText('A')
        self.assertTrue(d.sang(1))
        xl = self.td / 'ds.xlsx'
        _ghi(xl, _don_gian)
        self.assertEqual(len(d.nap_excel(str(xl))), 6)
        cot = {k: c for c, (k, _) in enumerate(du_an_moi.COT_THO)}
        # chọn vị trí trong danh sách xổ xuống
        idx = d.bang_tho.model().index(0, cot['vi_tri'])
        ed = d.xo_vi_tri.createEditor(d.bang_tho, None, idx)
        self.assertEqual(ed.count(), 5)
        ed.setCurrentIndex(0)
        d.xo_vi_tri.setModelData(ed, d.bang_tho.model(), idx)
        self.assertEqual(d.bang_tho.item(0, cot['vi_tri']).text(), '1')
        # loại đất: danh sách theo bộ đơn giá, lưu mã; gõ tay loại ghép vẫn được
        idx = d.bang_tho.model().index(1, cot['loai_dat'])
        ed = d.xo_loai_dat.createEditor(d.bang_tho, None, idx)
        self.assertGreaterEqual(ed.count(), 10)
        ed.setCurrentIndex(ed.findData('CLN'))
        ed.activated.emit(ed.findData('CLN'))                    # chọn trong danh sách: ô hiện mã
        self.assertEqual(ed.currentText(), 'CLN')
        d.xo_loai_dat.setModelData(ed, d.bang_tho.model(), idx)
        self.assertEqual(d.bang_tho.item(1, cot['loai_dat']).text(), 'CLN')
        ed.setEditText('ONT+CLN')
        d.xo_loai_dat.setModelData(ed, d.bang_tho.model(), idx)
        self.assertEqual(d.bang_tho.item(1, cot['loai_dat']).text(), 'ONT+CLN')
        d.bang_tho.item(1, cot['loai_dat']).setText('CLN')
        self.assertTrue(d.sang(2))
        self.assertTrue(d.dat_gia('ONT', '1', '900000'))          # thửa ONT+CLN có vị trí 1 -> ONT
        self.assertTrue(d.dat_gia('LUK', '', '100000', vi_tri_ap='1'))
        self.assertTrue(d.sang(3))
        self.assertIn('5 hộ', d.tom_tat.toPlainText())
        kq = d.tao(str(self.td / 'wiz.pabt'), xuat=False)
        self.assertEqual(kq['so_ho_co_pa'], 1)                    # chỉ hộ A có giá đất (B: CLN chưa nhập giá)
        self.assertGreater(kq['tong'], 0)

    def test_hop_bo_don_gia(self):
        from pabt.man_hinh_don_gia import HopBoDonGia
        con = csdl.tao_moi(self.td / 'c.pabt')
        d = HopBoDonGia(None, con)
        d.im_lang = True
        # thẻ nhà / cây trồng / VẬT NUÔI riêng (vật nuôi QĐ 31/2025 không lẫn trong 5.500 dòng cây trồng)
        self.assertEqual(d.the.count(), 7)                              # 0.9.69: bỏ thẻ Quy ước giá tương đương
        self.assertNotIn('Quy ước', ' '.join(d.the.tabText(i) for i in range(d.the.count())))
        self.assertEqual([d.the.tabText(i).rsplit(' (', 1)[0] for i in range(3)], ['Nhà, công trình', 'Cây trồng', 'Vật nuôi'])
        self.assertGreater(d.the.widget(1).rowCount(), 5000)
        vn = d.the.widget(2)
        self.assertEqual([vn.item(r, 0).text() for r in range(vn.rowCount())], [f'VN{i}' for i in range(1, 18)])
        self.assertEqual(sum(d.the.widget(i).rowCount() for i in range(3)),               # ba thẻ đủ mọi dòng, không trùng
                         sqlite3.connect(don_gia.file_goc()).execute('SELECT COUNT(*) FROM dm_taisan').fetchone()[0])
        # 0.9.73: Cập nhật = nạp file / sao lưu (bỏ web, tra cứu trình duyệt); bỏ nút Giá đất, Đơn giá riêng (menu trái có)
        self.assertEqual([a.text() for a in d.b_cap.menu().actions() if a.text()],
                         ['Nạp từ file định mức (Excel, Word, PDF, gói .sqlite, CSV)…', 'Dán bảng / văn bản đơn giá (Ctrl+Shift+V)',
                          'Sao lưu bộ đơn giá ra file (.sqlite / Excel)…'])          # 15/10/2026: thêm dán từ Clipboard
        self.assertFalse(hasattr(d, 'b_gia_dat') or hasattr(d, 'b_don'))
        d.the.setCurrentIndex(3)
        d.o_tim.setText('di chuyen tai san')
        b = d.the.widget(3)
        hien = [b.item(r, 0).text() for r in range(b.rowCount()) if not b.isRowHidden(r)]
        self.assertIn('CS14', hien)
        self.assertNotIn('CS1', hien)
        self.assertTrue(d.b_ap.isEnabled())
        d.ap_du_an(xac_nhan=True)
        self.assertGreater(con.execute('SELECT COUNT(*) FROM dm_hotro').fetchone()[0], 0)
        con.close()

    def test_cua_so_chinh_co_lenh_moi(self):
        from pabt import app as ud
        w = ud.CuaSoChinh()
        for ten in ('Dự án mới…', 'Bộ đơn giá…'):
            self.assertIn(ten, w.lenh)
        from PySide6.QtWidgets import QLabel
        chu = ' '.join(x.text() for x in w.findChildren(QLabel))
        self.assertIn('PHẦN MỀM LẬP PHƯƠNG ÁN BỒI THƯỜNG, HỖ TRỢ, TÁI ĐỊNH CƯ', chu)
        self.assertIn('TRUNG TÂM PHÁT TRIỂN QUỸ ĐẤT CHI NHÁNH VĨNH CỬU', chu)
        self.assertIn('phường Trị An', chu)
        self.assertIsNotNone(w.du_an_moi(cho=False))
        self.assertIsNotNone(w.bo_don_gia(cho=False))
        w.close()


if __name__ == '__main__':
    unittest.main()

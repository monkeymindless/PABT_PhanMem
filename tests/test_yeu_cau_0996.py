"""0.9.96 (người dùng 16/10/2026, 7 mục): chiều cao dòng bảng phương án, nút Quét hồ sơ chỉ báo đang hoàn thiện, loại đất đủ danh mục
(RDD…), đọc Excel phương án chi tiết / Excel thô (mục 1 luôn có dòng, nhiều phương án một sheet, DT thu hồi, dòng tiếp của hộ), thêm /
xóa nhiều thửa, hồ sơ scan của hộ + hộ hoàn tất công tác bồi thường. Số liệu GIẢ LẬP (không dùng file thật của người dùng)."""
from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path

import openpyxl

from pabt import csdl
from tests.test_dac_ta_v5 import CoSo
from tests.test_toc_do import _du_an


def _cua_so_lap_pa(td, so_ho=3, ma=None):
    from pabt.man_hinh import CuaSoLapPA
    con = csdl.mo(str(_du_an(Path(td), so_ho)))
    ma = ma or con.execute('SELECT ma_ho FROM ho ORDER BY thu_tu DESC LIMIT 1').fetchone()[0]
    c = CuaSoLapPA(con, ma)
    c.im_lang = True
    return con, c


class _Co(CoSo):
    def tearDown(self):
        self.doCleanups()                       # đóng cửa sổ / kết nối TRƯỚC khi xóa thư mục tạm (Windows khóa file đang mở)
        super().tearDown()


class _CoCuaSo(_Co):
    def _mo(self, so_ho=3, ma=None):
        con, c = _cua_so_lap_pa(self.td, so_ho, ma)

        def don():
            c.bo_thay_doi()
            c.close()
            con.close()
        self.addCleanup(don)
        return con, c


# ---------------------------------------------------------------- 1. chiều cao dòng
class TestChieuCaoDong(_CoCuaSo):
    def test_dong_gon_khi_ghi_chu_trong_va_cao_theo_chu(self):
        from pabt import giao_dien
        from pabt.man_hinh import the_cua
        con, c = self._mo()
        c.resize(1300, 760)
        c.show()
        c.tab.setCurrentIndex(the_cua(2))
        self.app.processEvents()
        bm = c.bang[2]
        vh = bm.bang.verticalHeader()
        self.assertFalse(vh.stretchLastSection())
        self.assertEqual((vh.minimumSectionSize(), vh.defaultSectionSize()), (30, 32))
        i = c.bo.them_hang_muc_khac(2, 'Mái che tạm')                     # ghi chú / quy cách trống
        bm.ve(chon=i)
        self.app.processEvents()
        h0 = bm.bang.rowHeight(i)                                           # ghi chú trống: chỉ cao theo các ô có chữ
        self.assertEqual(h0, giao_dien.cao_can_dong(bm.bang, i))
        self.assertTrue(30 <= h0 <= giao_dien.CAO_DONG_TOI_DA, h0)
        k = [x[0] for x in bm.cot]
        dai = 'Theo quy định tại khoản 3 Điều 102 Luật Đất đai năm 2024, tính theo diện tích xây dựng thực tế đo đạc. ' * 6
        c.sua_o(2, i, 'ghi_chu', dai)
        self.app.processEvents()
        h = bm.bang.rowHeight(i)
        self.assertTrue(h0 < h <= giao_dien.CAO_DONG_TOI_DA or h == giao_dien.CAO_DONG_TOI_DA, h)   # chữ dài: cao theo chữ, <= 88
        c.sua_o(2, i, 'ghi_chu', '')
        self.assertEqual(bm.bang.rowHeight(i), h0)
        # tiêu đề "Ghi chú (quy định, cách tính)" không bị cắt; cột thường trống không giãn
        from PySide6.QtGui import QFont, QFontMetrics
        f = QFont(bm.bang.horizontalHeader().font())
        f.setBold(True)
        cg = k.index('ghi_chu')
        self.assertGreaterEqual(bm.bang.columnWidth(cg), QFontMetrics(f).horizontalAdvance('Ghi chú (quy định, cách tính)'))

    def test_vua_dong_bang_thuong(self):
        from PySide6.QtWidgets import QTableWidget, QTableWidgetItem
        from pabt import giao_dien
        b = QTableWidget(3, 3)
        b.resize(600, 300)
        for c in range(3):
            b.setColumnWidth(c, 180)
        b.setItem(0, 0, QTableWidgetItem('Ngắn'))
        b.setItem(1, 1, QTableWidgetItem('Rất dài ' * 80))
        giao_dien.dat_dong_gon(b)
        giao_dien.vua_dong(b)
        self.assertEqual(b.rowHeight(0), giao_dien.cao_can_dong(b, 0))
        self.assertTrue(30 <= b.rowHeight(0) <= 36)
        self.assertTrue(30 <= b.rowHeight(2) <= 36)                         # dòng trống
        self.assertEqual(b.rowHeight(1), giao_dien.CAO_DONG_TOI_DA)
        giao_dien.vua_dong(b, cao_chuan=None, cao_toi_da=None)              # cách gọi cũ (theo dõi): không giới hạn
        self.assertGreater(b.rowHeight(1), giao_dien.CAO_DONG_TOI_DA)


# ---------------------------------------------------------------- 2. nút Quét hồ sơ
class TestNutQuetHoSo(_CoCuaSo):
    def test_chi_bao_dang_hoan_thien(self):
        from pabt import man_hinh_ocr
        _, c = self._mo()
        self.assertEqual(c.b_ocr.text(), 'Quét hồ sơ…')
        self.assertEqual(c.quet_giay_to(cho=False), 'Tiện ích đang trong quá trình hoàn thiện')
        self.assertEqual(c.b_ocr.toolTip(), 'Tiện ích đang trong quá trình hoàn thiện')
        for ten in ('nhap_tron_bo', 'luu_dinh_kem', 'dien_nhan_khau_tdc'):             # mã quét dành cho lập PA đã bỏ
            self.assertFalse(hasattr(man_hinh_ocr.HopQuetGiayTo, ten), ten)


# ---------------------------------------------------------------- 3. loại đất
class TestLoaiDat(_CoCuaSo):
    def test_chuan_ma(self):
        from pabt.loai_dat import LOAI_DAT, chuan_ma_loai_dat
        ma = {x[0] for x in LOAI_DAT}
        for m in ('LUC', 'LUK', 'LUN', 'BHK', 'HNK', 'CLN', 'RSX', 'RPH', 'RDD', 'NTS', 'LMU', 'NKH', 'LNK', 'RTS', 'ONT', 'ODT',
                  'TSC', 'CQP', 'CAN', 'DSN', 'DCH', 'DGD', 'DYT', 'DVH', 'DTT', 'DKH', 'DXH', 'DNG', 'SKK', 'SKN', 'SKC', 'TMD',
                  'SKS', 'SKX', 'DGT', 'DTL', 'DNL', 'DBV', 'DRA', 'DHN', 'DDT', 'TON', 'TIN', 'NTD', 'SON', 'MNC', 'PNK', 'DCK',
                  'DKV', 'BCS', 'DCS', 'NCS'):
            self.assertIn(m, ma)
        for vao, ra in (('rdd', 'RDD'), ('R.D.D', 'RDD'), ('ĐGT', 'DGT'), ('Đất rừng đặc dụng', 'RDD'), ('ont + cln', 'ONT+CLN'),
                        ('ONT,CLN', 'ONT+CLN'), ('Đất ở', 'OTC'), ('', '')):
            self.assertEqual(chuan_ma_loai_dat(vao), ra, vao)

    def test_rdd_khong_bao_ngoai_danh_muc_va_giu_khi_gia_0(self):
        from pabt import nghiep_vu
        from pabt.lap_pa import BoSoan, LoiNhap
        con = csdl.mo(str(_du_an(self.td, 2)))
        self.addCleanup(con.close)
        self.assertIsNone(con.execute("SELECT 1 FROM dm_loaidat WHERE ma = 'RDD'").fetchone())
        self.assertEqual(nghiep_vu.BoiCanh.tu(con).loai_dat['RDD'], 'Nông nghiệp')
        with con:
            con.execute("UPDATE thua SET loai_dat = 'rdd' WHERE ma_thua = (SELECT MIN(ma_thua) FROM thua)")
        mt, ma = con.execute('SELECT ma_thua, ma_ho FROM thua ORDER BY ma_thua LIMIT 1').fetchone()
        bo = BoSoan(con, ma)
        bo.pa.dat.clear()
        i, tb = bo.them_thua(mt)
        self.assertEqual(bo.pa.dat[i].loai_dat, 'RDD')                     # giá 0 vẫn giữ loại đất
        self.assertIn('Chưa có giá', tb)
        bo.sua_dat(i, 'loai_dat', 'Đất rừng phòng hộ')
        self.assertEqual(bo.pa.dat[i].loai_dat, 'RPH')
        with self.assertRaises(LoiNhap):
            bo.sua_dat(i, 'loai_dat', 'XYZ')

    def test_kiem_loi_khong_bao_rdd(self):
        from pabt import kiem_loi
        con = csdl.mo(str(_du_an(self.td, 2)))
        self.addCleanup(con.close)
        with con:
            con.execute("UPDATE thua SET loai_dat = 'RDD'")
        self.assertFalse([x for x in kiem_loi.kiem_tra(con) if 'không có trong danh mục loại đất' in x.noi_dung])


# ---------------------------------------------------------------- 4. đọc Excel
def _ghi_pa(ws, dau, so_pa, ten, thua):
    """Một phương án chi tiết giả lập bắt đầu ở dòng dau; thua = [(số thửa, tờ, loại đất, DT)]. Trả dòng kế tiếp."""
    r = dau
    for v in ('TỔ CHỨC THỬ NGHIỆM', None, None, f'Số: {so_pa}/PA-THU', 'PHƯƠNG ÁN CHI TIẾT BỒI THƯỜNG', 'Dự án: Đường thử'):
        if v:
            ws.cell(r, 1, v)
        r += 1
    ws.cell(r, 1, 'I. Tổ chức và hộ gia đình, cá nhân bị thu hồi')
    ws.cell(r + 1, 1, 'Tổ chức:')
    ws.cell(r + 1, 3, ten)
    ws.cell(r + 2, 1, 'Địa chỉ:')
    ws.cell(r + 2, 3, 'Khu phố 1')
    ws.cell(r + 3, 1, 'II.')
    ws.cell(r + 3, 2, 'Thông tin vị trí, nguồn gốc đất:')
    ws.cell(r + 4, 1, '- Đất do tổ chức quản lý.')
    ws.cell(r + 5, 1, 'III. Theo chi tiết sau:')
    r += 6
    for c, v in enumerate(('STT', 'Hạng mục', 'ĐVT', 'Số lượng', 'Đơn giá', 'Tỷ lệ', 'Thành tiền', 'Ghi chú'), start=1):
        ws.cell(r, c, v)
    ws.cell(r + 1, 1, 'I')
    ws.cell(r + 1, 2, 'Bồi thường đất')
    r += 2
    for k, (so, to, ld, dt) in enumerate(thua, start=1):
        for c, v in enumerate((k, f'Thửa  đất số {so}, tờ bản đồ số {to}, loại đất {ld}', 'm2', dt, 0, 0, 0,
                               'Đất do tổ chức quản lý' if k == 1 else None), start=1):
            ws.cell(r, c, v)
        r += 1
    ws.cell(r, 1, 'TỔNG CỘNG')
    ws.cell(r, 7, 0)
    ws.cell(r + 2, 1, 'LẬP BIỂU')
    ws.cell(r + 6, 1, 'Người ký giả lập')
    return r + 7


class TestDocExcel(_Co):
    def _file_chi_tiet(self):
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = 'Nhiều PA'
        r = _ghi_pa(ws, 1, 101, 'Tổ chức Thử A', [('1', '5', 'RDD', 10.5), ('--', '5', 'RDD', 20), ('', '6', 'rdd', 30)])
        _ghi_pa(ws, r, 102, 'Tổ chức Thử B', [(str(k), '7', 'RPH', k) for k in range(1, 6)])
        p = self.td / 'pa.xlsx'
        wb.save(p)
        return p

    def test_nhieu_phuong_an_mot_sheet_va_muc_1_luon_co_dong(self):
        from pabt import nhap_chi_tiet
        kq = nhap_chi_tiet.doc(self._file_chi_tiet())
        self.assertEqual([h.sheet for h in kq.ho], ['Nhiều PA - PA 101', 'Nhiều PA - PA 102'])
        self.assertEqual([h.ho_ten for h in kq.ho], ['Tổ chức Thử A', 'Tổ chức Thử B'])
        self.assertEqual([len(h.dat) for h in kq.ho], [3, 5])
        self.assertGreater(kq.ho[1].dat[0].dong, kq.ho[0].dat[-1].dong)          # số dòng Excel thật (không đếm lại từ 1)
        t = [nhap_chi_tiet._thua_tu_ten(d.ten) for d in kq.ho[0].dat]
        self.assertEqual([(x['so_thua'], x['so_to'], x['loai_dat']) for x in t], [('1', '5', 'RDD'), ('', '5', 'RDD'), ('', '6', 'RDD')])
        p = self.td / 'moi.pabt'
        bc = nhap_chi_tiet.ghi_file(kq, p, trung='them')
        self.assertEqual(len(bc.them), 2)
        self.assertFalse([x for x in bc.canh_bao if 'không có trong danh mục' in x])
        con = csdl.mo(p)
        try:
            self.assertEqual(con.execute('SELECT COUNT(*) FROM thua').fetchone()[0], 8)
            self.assertEqual(con.execute('SELECT COUNT(*) FROM ct_dat').fetchone()[0], 8)            # giá 0 vẫn có dòng mục 1
            self.assertEqual({r[0] for r in con.execute('SELECT loai_dat FROM ct_dat')}, {'RDD', 'RPH'})
        finally:
            con.close()

    def test_nhap_tho_dt_thu_hoi_va_dong_tiep(self):
        from pabt import nhap_tho
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.append(['BẢNG TỔNG HỢP THỬ'])
        ws.append(['STT', 'Họ và tên', 'Địa chỉ', 'Số tờ', 'Số thửa', 'Loại đất', 'Tổng diện tích thửa đất',
                   'Tổng diện tích trong dự án', 'Ghi chú'])
        ws.append([1, 2, 3, 4, 5, 6, 7, 9, 10])                                  # dòng đánh số cột (thiếu số 8)
        ws.append([1, 'Tổ chức Thử', 'Khu phố 1', '10', '1', 'RDD', 1000, 300.5, None])
        ws.append([None, 'NaN', None, '10', '2', 'RDD', 500, 120, None])         # dòng tiếp của cùng hộ
        ws.append([None, '--', None, '11', '--', 'DGT', 90, 60, None])
        ws.append(['STT', 'Họ và tên', 'Địa chỉ', 'Số tờ', 'Số thửa', 'Loại đất', 'Tổng diện tích thửa đất',
                   'Tổng diện tích trong dự án', 'Ghi chú'])                     # tiêu đề lặp (trang 2)
        ws.append([2, 'Nguyễn Văn Thử', 'Ấp 2', '12', '3', 'ONT', 200, 200, None])
        ws.append(['TỔNG CỘNG', None, None, None, None, None, 1790, 680.5])
        ws.append(['Kinh phí đảm bảo… 2,5%:'] * 5)                              # chữ gộp ngang nhiều cột
        ws.cell(60, 200, 'chữ lạc ngoài bảng')
        p = self.td / 'tho.xlsx'
        wb.save(p)
        kq = nhap_tho.doc(p)
        self.assertEqual(kq.bo_cot.tieu_de['dt_thu_hoi'], 'Tổng diện tích trong dự án')
        self.assertEqual([h['ho_ten'] for h in kq.ho], ['Tổ chức Thử', 'Nguyễn Văn Thử'])
        self.assertEqual([(t['ma_ho'], t['so_thua'], t['dt_thu_hoi']) for t in kq.thua],
                         [(1, '1', '300.5'), (1, '2', '120'), (1, '', '60'), (2, '3', '200')])


# ---------------------------------------------------------------- 5. thêm / xóa nhiều thửa
class TestNhieuThua(_CoCuaSo):
    def test_bo_soan(self):
        from pabt.lap_pa import BoSoan
        con = csdl.mo(str(_du_an(self.td, 3)))
        self.addCleanup(con.close)
        ma = con.execute('SELECT ma_ho FROM thua GROUP BY ma_ho HAVING COUNT(*) = 3').fetchone()[0]
        bo = BoSoan(con, ma)
        bo.pa.dat.clear()
        mt = [x[0] for x in bo.thua_cua_ho()]
        self.assertEqual(bo.them_nhieu_thua([mt[1]]), 1)
        self.assertEqual(bo.them_nhieu_thua(), 2)                               # thửa đã có bỏ qua
        self.assertEqual([d.ma_thua for d in bo.pa.dat], [mt[1], mt[0], mt[2]])
        self.assertEqual(bo.them_nhieu_thua(), 0)
        self.assertEqual(bo.them_nhieu_thua(bo_qua_da_co=False), 3)
        self.assertEqual(bo.xoa_nhieu_dat([0, 2, 2, 99]), 2)
        self.assertEqual(len(bo.pa.dat), 4)

    def test_nut_chon_nhieu_va_ap_vi_tri_cho_dong_chon(self):
        from PySide6.QtCore import QItemSelectionModel, Qt
        from PySide6.QtWidgets import QAbstractItemView
        con, c = self._mo(3)
        c.bo.pa.dat.clear()
        bm = c.bang[1]
        self.assertEqual(bm.bang.selectionMode(), QAbstractItemView.SelectionMode.ExtendedSelection)
        self.assertEqual((bm.b_them_tat_ca_thua.text(), bm.b_chon_nhieu_thua.text()), ('Thêm tất cả thửa', 'Chọn nhiều thửa…'))
        hop = c.chon_nhieu_thua(cho=False)
        self.assertEqual(len(hop.chon_ma()), 3)                                  # mặc định đánh dấu thửa chưa có ở mục 1
        hop.danh_dau(False)
        self.assertEqual(hop.chon_ma(), [])
        hop.cb_ld.setCurrentIndex(hop.cb_ld.findData(hop.thua[0][3]))
        hop.danh_dau(True)                                                        # = Ctrl+A: chỉ thửa đang hiện
        self.assertEqual(hop.chon_ma(), [hop.thua[0][0]])
        self.assertEqual(c._them_cac_thua(hop.chon_ma(), bo_qua_da_co=False), 1)
        self.assertEqual(c.them_tat_ca_thua(), 2)
        self.assertEqual(bm.bang.rowCount(), 3)
        # chọn 2 dòng, sửa tỷ lệ một dòng -> áp cho cả 2
        sm = bm.bang.selectionModel()
        sm.clearSelection()
        for r in (0, 2):
            sm.select(bm.bang.model().index(r, 0), QItemSelectionModel.SelectionFlag.Select | QItemSelectionModel.SelectionFlag.Rows)
        sm.setCurrentIndex(bm.bang.model().index(2, 0), QItemSelectionModel.SelectionFlag.NoUpdate)
        c.sua_o(1, 2, 'ty_le', '50')
        self.assertEqual([str(d.ty_le) for d in c.bo.pa.dat], ['0.5', '1', '0.5'])
        c.xoa_dong(1)                                                             # xóa cả 2 dòng đã chọn
        self.assertEqual(len(c.bo.pa.dat), 1)
        self.assertEqual(bm.bang.rowCount(), 1)
        del Qt

    def test_xoa_nhieu_thua_o_the_ho_so(self):
        from PySide6.QtCore import QItemSelectionModel
        con, c = self._mo(3)
        hs = c.ho_so
        n = hs.bang.rowCount()
        self.assertGreaterEqual(n, 2)
        sm = hs.bang.selectionModel()
        for r in range(2):
            sm.select(hs.bang.model().index(r, 0), QItemSelectionModel.SelectionFlag.Select | QItemSelectionModel.SelectionFlag.Rows)
        self.assertTrue(hs.xoa_dong(xac_nhan=True))
        self.assertEqual(hs.bang.rowCount(), n - 2)


# ---------------------------------------------------------------- 6. hồ sơ scan + hoàn tất CTBT
class TestHoSoScan(_Co):
    def _du_an_qd(self):
        from pabt import theo_doi
        con = csdl.mo(str(_du_an(self.td, 3)))
        self.addCleanup(con.close)
        ds = [r[0] for r in con.execute('SELECT ma_ho FROM ho ORDER BY thu_tu')]
        qd = theo_doi.luu_qd(con, None, '01/QĐ-THU', '01/10/2026')
        theo_doi.them_ho_theo_pa(con, qd, ds[:2])
        theo_doi.ghi_ban_giao(con, ds[:1], dict(da_ban_giao=True, ban_giao_ngay='05/10/2026'))
        theo_doi.ghi_ban_giao(con, ds[2:], dict(da_ban_giao=True, ban_giao_ngay='05/10/2026'))   # chưa có QĐ: chưa hoàn tất
        return con, ds

    def test_dinh_kem_bo_va_dem(self):
        from pabt import ho_so_scan
        con = csdl.mo(str(_du_an(self.td, 2)))
        self.addCleanup(con.close)
        ma = con.execute('SELECT MIN(ma_ho) FROM ho').fetchone()[0]
        f1, f2 = self.td / 'gcn.pdf', self.td / 'anh.jpg'
        f1.write_bytes(b'%PDF-1.4 gia lap')
        f2.write_bytes(b'jpg')
        self.assertEqual(ho_so_scan.them_file(con, ma, [f1, f2, f1]), 2)
        self.assertEqual(ho_so_scan.them_file(con, ma, [f1]), 0)
        ds = ho_so_scan.ds_file(con, ma)
        self.assertEqual([x['ten_file'] for x in ds], ['gcn.pdf', 'anh.jpg'])
        self.assertTrue(all(x['con'] for x in ds))
        self.assertEqual(ho_so_scan.dem_theo_ho(con), {ma: 2})
        self.assertEqual(ho_so_scan.bo_file(con, ma, [ds[0]['id']]), 1)
        self.assertTrue(f1.exists())                                              # bỏ đính kèm không xóa file
        self.assertEqual(ho_so_scan.dem_theo_ho(con), {ma: 1})

    def test_hoan_tat_va_xuat_excel(self):
        from pabt import ho_so_scan
        con, ds = self._du_an_qd()
        nhom = ho_so_scan.ds_hoan_tat(con)
        self.assertEqual([x.ma_ho for _, v in nhom for x in v], [ds[0]])          # có QĐ + đã bàn giao (chưa nhận tiền vẫn tính)
        f = self.td / 'ht.xlsx'
        self.assertEqual(ho_so_scan.xuat_excel_hoan_tat_ctbt(con, f, ten_du_an='Thử'), 1)
        ws = openpyxl.load_workbook(f).active
        self.assertIn('HOÀN TẤT', ws['A1'].value)
        self.assertTrue(any(c.value == ds[0] for row in ws.iter_rows() for c in row))

    def test_man_hinh(self):
        from pabt import ho_so_scan, man_hinh_theo_doi as mt
        from pabt.man_hinh_ho_so import KhungHoSo
        from pabt.man_hinh_ho_so_scan import HopHoanTatCTBT, NutHoSoScan
        con, ds = self._du_an_qd()
        f = self.td / 'qd.pdf'
        f.write_bytes(b'%PDF gia lap')
        ho_so_scan.them_file(con, ds[0], [f])
        k = mt.KhungTienDo(con)
        k.im_lang = True
        k.nap()
        self.assertEqual(k.COT[k.C_HOAN_TAT].split('\n')[0], 'Hoàn tất CTBT')
        self.assertEqual(k.COT[k.C_SCAN], 'Hồ sơ scan')
        dong = {x.ma_ho: gt for x, _, gt in k.dong()}
        self.assertTrue(dong[ds[0]][k.C_HOAN_TAT].startswith('Hoàn tất'))
        self.assertEqual(dong[ds[1]][k.C_HOAN_TAT], '')
        self.assertEqual(dong[ds[2]][k.C_HOAN_TAT], '')
        self.assertEqual(dong[ds[0]][k.C_SCAN], '1 file')
        hop = k.hoan_tat_ctbt()
        self.assertIsInstance(hop, HopHoanTatCTBT)
        self.assertEqual(hop.bang.rowCount(), 1)
        self.assertFalse([b for b in hop.findChildren(type(hop.b_xuat)) if 'Word' in b.text()])     # chỉ Excel
        hop.im_lang = True
        self.assertTrue(hop.xuat(self.td / 'x.xlsx').exists())
        hs = KhungHoSo(con, ds[0])
        self.assertIsInstance(hs.nut_scan, NutHoSoScan)
        self.assertEqual(hs.nut_scan.text(), 'Hồ sơ scan (1)')
        self.assertTrue(hs.nut_scan.isEnabled())
        hs.nut_scan._dung_menu()
        chu = [a.text() for a in hs.nut_scan.menu.actions()]
        self.assertIn('Đính kèm file PDF / ảnh…', chu)
        self.assertIn('qd.pdf', chu)
        g = self.td / 'them.png'
        g.write_bytes(b'png')
        self.assertEqual(hs.nut_scan.dinh_kem([g]), 1)
        self.assertEqual(hs.nut_scan.text(), 'Hồ sơ scan (2)')
        h = mt.HopHoTheoDoi(con, ds[0])
        self.assertEqual(h.nut_scan.text(), 'Hồ sơ scan (2)')
        for w in (k, hop, hs, h):
            w.deleteLater()


class TestCacHopMoiCoImLang(unittest.TestCase):
    def test_im_lang(self):
        from pabt.man_hinh import HopChonNhieuThua
        from pabt.man_hinh_ho_so_scan import HopHoanTatCTBT, NutHoSoScan
        for lop in (HopChonNhieuThua, HopHoanTatCTBT, NutHoSoScan):
            self.assertIs(lop.im_lang, False, lop)


del sqlite3, tempfile

if __name__ == '__main__':
    unittest.main()

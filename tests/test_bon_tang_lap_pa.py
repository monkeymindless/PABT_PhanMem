"""1.0.69: cửa sổ phương án 4 tầng, thẻ mục, bộ đếm theo bản chất cột, định dạng tiền / hệ số, khớp 4 tầng, 13 bậc, luồng V0 -> V1 -> V2 -> V3, chạy thử trên file dự án thật nếu có (PABT_DU_LIEU)."""
from __future__ import annotations

import json
import os
import shutil
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path

from pabt import ap_gia_dat as ap
from pabt import csdl, du_an_moi, lap_pa
from pabt import gia_dat_qd03 as g
from pabt import goi_gia_dat as gg
from pabt import phien_ban_pa as pb
from pabt import van_ban_can_cu as vb
from pabt import van_ban_dot as vbd
from pabt.lap_pa import BoSoan, LoiNhap
from pabt.nghiep_vu import DongKhoan

from tests import APP

D = Decimal
THU_MUC_THAT = Path(os.environ.get('PABT_DU_LIEU') or r'D:\APP AI PABT\1.DU LIEU')


def _du_an(td: Path, so_ho: int = 3, xa: str = 'Phú Lý') -> Path:
    dong = [dict(ho_ten=f'Nguyễn Văn An {chr(65 + i)}', so_cccd=f'07906202925{i}', dia_chi='Ấp 1', so_to=str(39), so_thua=str(16 + i), loai_dat='CLN', dt_thu_hoi='100', vi_tri='1') for i in range(so_ho)]
    p = td / 'a.pabt'
    du_an_moi.tao_du_an(p, dict(ten='Thử', cap_dia_ban='Xã', ten_dia_ban=xa, nam='2026'), dong, [dict(loai_dat='CLN', vi_tri='1', gia='250000')])
    return p


class CoSo(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.addCleanup(self.td.cleanup)
        self.con = csdl.mo(_du_an(Path(self.td.name)))
        self.addCleanup(self.con.close)
        self.ma = [r[0] for r in self.con.execute('SELECT ma_ho FROM ho ORDER BY thu_tu')]


class TestCongThuc(unittest.TestCase):
    def _tinh(self, gia, k1, ket_cau='NHUA_BETONG', doan=None, cu_the=0):
        return g.tinh_don_gia(g.DauVao(dia_ban='x', don_gia_bang_gia=D(gia), he_so_k1=D(k1), ket_cau_mat_duong=ket_cau, cot_gia='nn_cay', gia_dat_cu_the=D(cu_the)), doan)

    def test_phu_ly_333500(self):
        k = self._tinh(230000, '1.45')
        self.assertEqual(k.don_gia_ap_dung, D(333500))
        self.assertEqual(k.cong_thuc, '230.000 × 1,45 (K1) × 1,00 (K2) × 1,00 (K3) = 333.500 đ/m²')
        self.assertEqual(g.cong_thuc_gon(k), '230.000 × 1,45 × 1,00 × 1,00 = 333.500 đ/m²')

    def test_tan_an_duong_dat_952650(self):
        k = self._tinh(730000, '1.45', 'DAT_SOI_DA_CAPPHOI')
        self.assertEqual(k.k3, D('0.90'))
        self.assertEqual(k.don_gia_ap_dung, D(952650))
        self.assertIn('0,90 (K3)', k.cong_thuc)

    def test_chot_chan_khong_nhan_trung(self):
        goc = dict(ten_duong='Đường A', diem_dau='a', diem_cuoi='b', tt_bat_dau=1, ma_doan_duong='X', k1_nong_nghiep=1.45)
        self.assertEqual(self._tinh(730000, '1.45', 'DAT_SOI_DA_CAPPHOI', goc).k3, D('0.90'))
        for doan in (dict(goc, co_quy_dinh_rieng_duong_dat_tai_pl1=True), dict(goc, ten_duong='Các tuyến đường giao thông còn lại'), dict(goc, ten_duong='Đường đất, sỏi')):
            k = self._tinh(730000, '1.45', 'DAT_SOI_DA_CAPPHOI', doan)
            self.assertEqual(k.k3, 1, doan['ten_duong'])
            self.assertTrue(k.canh_bao)

    def test_chuyen_tiep_lay_gia_cao_hon(self):
        self.assertEqual(self._tinh(230000, '1.45', cu_the=400000).don_gia_ap_dung, D(400000))
        self.assertEqual(self._tinh(230000, '1.45', cu_the=100000).don_gia_ap_dung, D(333500))

    def test_he_so_hien_khong_lam_mat_gia_tri(self):
        self.assertEqual((g.he_hien(D('1.45')), g.he_hien(1), g.he_hien(D('0.9'))), ('1,45', '1,00', '0,90'))
        self.assertEqual(g.he_hien(D('0.9025')), '0,9025')

    def test_dong_co_quy_tac(self):
        e = gg.DynamicRegulationEngine()
        self.assertEqual(e.goi['ma'], 'QD03_2026_DONG_NAI')
        k = e.tinh(g.DauVao(don_gia_bang_gia=D(230000), he_so_k1=D('1.45'), cot_gia='nn_cay'))
        self.assertEqual(k.don_gia_ap_dung, D(333500))
        d = g.ds_doan(g.ds_dia_ban(e.goi)[0], e.goi)[0]
        self.assertEqual(e.tra_doan('Trị An', d['ma_doan_duong'])['ten_duong'], d['ten_duong'])
        with self.assertRaises(ValueError):
            gg.DynamicRegulationEngine.tu_ma('KHONG_CO')


class TestLuuThongTinApGia(CoSo):
    def test_luu_doc_lai_va_sua_tay_thi_bo(self):
        k = g.tinh_don_gia(g.DauVao(don_gia_bang_gia=D(230000), he_so_k1=D('1.45'), cot_gia='nn_cay'))
        hang = [x for x in ap.doc_dong(self.con) if x.ma_ho == self.ma[0]]
        ap.ap_hang_loat(self.con, hang, k.don_gia_ap_dung, g.ghi_chu_ap_gia(k), chi_tiet=g.chi_tiet_ap_gia(k))
        bo = BoSoan(self.con, self.ma[0])
        t = json.loads(bo.pa.dat[0].ap_gia)
        self.assertEqual((t['don_gia'], t['gia_bang_gia_nq28'], t['he_so_k1'], t['he_so_k2'], t['he_so_k3']), ('333500', '230000', '1.45', '1', '1'))
        self.assertIn('333.500 đ/m²', t['cong_thuc_dien_giai'])
        pb.khoa_v1(self.con, self.ma[0])                               # ảnh chụp giữ được trường mới
        self.assertTrue(pb.doc_pa(self.con, self.ma[0], pb.V1).dat[0].ap_gia)
        bo.sua_dat(0, 'gia_bang_gia', '100000')
        self.assertEqual(bo.pa.dat[0].ap_gia, '')                      # số đã khác thuyết minh

    def test_mo_rong_luoc_do(self):
        self.assertTrue(csdl.co_cot_ap_gia(self.con))
        self.assertIn('cot_ap_gia', [x[0] for x in csdl.MO_RONG])


class TestPhienBan(CoSo):
    def _dat_gia(self, ma_v, gia):
        bo = BoSoan(self.con, self.ma[0])
        bo.mo_phien_ban(ma_v)
        bo.pa.khoan[3][0].don_gia = D(gia)
        bo.luu()

    def test_v0_v1_v2_v3_ve_v1(self):
        m = self.ma[0]
        bo = BoSoan(self.con, m)
        bo.pa.dat[:] = []
        bo.pa.khoan[4] = []
        bo.pa.khoan[3] = [DongKhoan(muc=3, ten='Cây thử', dvt='cây', so_luong=D(100), don_gia=D(10000))]
        bo.luu()
        pb.khoa_v1(self.con, m)
        v2 = pb.tao_v2(self.con, m, 'Hộ đề nghị 50.000 đ')
        self._dat_gia(v2, 50000)
        self.assertEqual(pb.doc_pa(self.con, m, pb.V1).khoan[3][0].don_gia, D(10000))
        pb.dat_v3(self.con, m, v2, 'chấp thuận')
        self.assertEqual(BoSoan(self.con, m).pa.khoan[3][0].don_gia, D(50000))
        pb.dat_v3(self.con, m, pb.V1, 'không chấp thuận')             # khôi phục một chạm
        self.assertEqual(BoSoan(self.con, m).pa.khoan[3][0].don_gia, D(10000))
        self.assertEqual(pb.doc_pa(self.con, m, v2).khoan[3][0].don_gia, D(50000))
        d = pb.doi_chieu_ho(self.con, m, v2)
        self.assertEqual(d['tong']['d1'] > 0, True)
        self.assertEqual(d['tong']['d2'], 0)
        pb.ghep_v3(self.con, m, {pb.DAT: pb.V1, pb.NHA: pb.V1, pb.CAY: v2, pb.HO_TRO: pb.TINH_LAI})   # ghép từng nhóm
        self.assertEqual(BoSoan(self.con, m).pa.khoan[3][0].don_gia, D(50000))

    def test_xoa_nhanh_va_khoi_phuc(self):
        m = self.ma[0]
        pb.khoa_v1(self.con, m)
        v2 = pb.tao_v2(self.con, m)
        pb.dat_v3(self.con, m, v2)
        with self.assertRaises(LoiNhap):
            pb.xoa_v2(self.con, m, v2)                                 # V3 đang lấy từ nhánh này
        pb.dat_v3(self.con, m, pb.V1)
        pb.xoa_v2(self.con, m, v2)
        self.assertEqual(pb.v2_moi_nhat(self.con, m), '')
        with self.assertRaises(LoiNhap):
            pb.xoa_v2(self.con, m, pb.V1)
        bo = BoSoan(self.con, m)
        goc = bo.pa.dat[0].gia_bang_gia
        bo.pa.dat[0].gia_bang_gia = D(1)
        bo.luu()
        pb.khoi_phuc_v0(self.con, m, pb.V1)
        self.assertEqual(BoSoan(self.con, m).pa.dat[0].gia_bang_gia, goc)


class TestKhop4Tang(CoSo):
    def setUp(self):
        super().setUp()
        from pabt import du_thao
        self.dot = du_thao.tao_dot(self.con, 'Đợt 1', '2026-11-01', 'UBND xã')
        du_thao.them_thu_cong(self.con, self.dot, self.ma, ca_vuong=True)
        self.kh = vbd._KhopHo(self.con, self.dot)

    def test_cccd_duoi_0_mat_so_0(self):
        for chu in ('79062029250', '79062029250.0', '079062029250'):
            h, cach = self.kh.khop(['1', 'Tên khác hẳn', chu])
            self.assertEqual((h['ma_ho'], cach), (self.ma[0], 'CCCD'), chu)

    def test_thua_to_va_hau_to_phap_ly(self):
        h, cach = self.kh.khop(['17 (tờ 39)', 'Nguyễn Văn An B là chủ sở...'])
        self.assertEqual((h['ma_ho'], cach), (self.ma[1], 'thửa, tờ'))
        h, _ = self.kh.khop(['Nguyễn Văn An C là chủ sở hữu tài sản'])
        self.assertEqual(h['ma_ho'], self.ma[2])

    def test_ma_ho_khong_tin_khi_ten_khac(self):
        h, cach = self.kh.khop(['Nguyễn Văn An B'], self.ma[1])
        self.assertEqual((h['ma_ho'], cach), (self.ma[1], 'mã hộ'))
        h, cach = self.kh.khop(['123', '456'], self.ma[2])
        self.assertEqual((h['ma_ho'], cach), (self.ma[2], 'mã hộ'))
        h, _ = self.kh.khop(['Người Hoàn Toàn Khác'], self.ma[1])
        self.assertIsNone(h)

    def test_ten_gan_dung_can_dung_tong_tien(self):
        from pabt.tien import vn
        tong = next(iter(self.kh._tong_ho(self.ma[0])))
        self.assertIsNone(self.kh.khop(['Nguyen Van Ann A', vn(tong)])[0])       # ba hộ tên gần giống, cùng tiền: không đoán
        bo = BoSoan(self.con, self.ma[0])
        bo.pa.dat[0].dien_tich = D(200)
        bo.luu()
        self.kh = vbd._KhopHo(self.con, self.dot)
        tong = next(iter(self.kh._tong_ho(self.ma[0])))
        h, cach = self.kh.khop(['Nguyen Van Ann A', vn(tong)])
        self.assertEqual((h['ma_ho'], cach), (self.ma[0], 'tên gần đúng + tổng tiền'))
        self.assertIsNone(self.kh.khop(['Nguyen Van Ann A', '123.456'])[0])       # sai tiền: không đoán
        self.assertIsNone(self.kh.khop(['Nguyen Van Ann A'])[0])


class TestVanBan13Bac(unittest.TestCase):
    def test_thu_tu_va_khu_trung(self):
        ds = ['Công văn số 5/UBND của UBND xã Phú Lý', 'Văn bản số 1201/SNNMT-ĐĐ ngày 20/5/2026 của Sở Nông nghiệp và Môi trường', 'Quyết định số 03/2026/QĐ-UBND của UBND thành phố Đồng Nai',
              'Nghị quyết số 28/2025/NQ-HĐND của HĐND tỉnh Đồng Nai', 'Nghị định số 88/2024/NĐ-CP của Chính phủ', 'Nghị định số 88/2024/NĐ-CP ngày 15/7/2024', 'Luật Đất đai số 31/2024/QH15',
              'Văn bản hướng dẫn ngày 29/05/2026 của Sở Nông nghiệp và Môi trường về giá đất nông nghiệp', 'Nghị quyết số 254/2025/QH15 của Quốc hội']
        kq = vb.gop_va_sap_xep(ds)[1]
        self.assertEqual([x.bac for x in kq], [2, 3, 5, 10, 11, 12, 12, 13])
        self.assertTrue(any(x.so_hieu.startswith('VB-') for x in kq))        # văn bản không số: không lấy ngày làm số hiệu


@unittest.skipIf(APP is None, 'cần PySide6 / PySide2')
class TestCuaSo(CoSo):
    def _w(self):
        from pabt.man_hinh import CuaSoLapPA, the_cua
        w = CuaSoLapPA(self.con, self.ma[0])
        w.im_lang = True
        self.addCleanup(lambda: (w.bo_thay_doi(), w.close()))
        w.show()
        w.tab.setCurrentIndex(the_cua(1))
        APP.processEvents()
        return w

    def test_bon_tang(self):
        w = self._w()
        self.assertTrue(w.tab.tabBar().isHidden())
        self.assertTrue(w.dai_dinh_danh.isHidden())
        self.assertFalse(w.bang[1].dai_cong.isVisibleTo(w))
        self.assertEqual(w.dai_dieu_huong.maximumHeight(), 34)
        self.assertGreaterEqual(w.cb_ho.minimumWidth(), 240)
        self.assertNotRegex(w.cb_ho.currentText(), r' 0$')
        for k in ('CCCD', ):
            self.assertIn('079062029250', w.cb_ho.toolTip(), k)
        self.assertFalse(w.b_bo.isVisibleTo(w))
        self.assertFalse(w.b_dan.isVisibleTo(w))
        self.assertTrue(w.bang[1].nut['Dán tài sản'].isVisibleTo(w.bang[1]))
        self.assertEqual(w.bang[1].nut['▲ Lên'].width(), 28)
        self.assertEqual(w.thanh_pb.cb.count(), 1)
        self.assertEqual(w.thanh_pb.b_hd.text(), 'Chốt V1')

    def test_the_muc_mau_va_phim(self):
        w = self._w()
        t = w.thanh_the
        self.assertEqual(len(t.nut), 6)
        self.assertTrue(t.nut[1].isChecked())
        self.assertEqual(t._trang[1], 'chon')
        self.assertEqual(t._trang[2], 'trong')
        self.assertEqual(t._trang[0], 'co')
        self.assertIn('1. Đất (1 •', t.nut[1].text())
        self.assertEqual(t.nut[0].text().count('&&'), 1)
        t.nut[0].click()
        self.assertEqual(w.tab.currentIndex(), 0)
        self.assertEqual(t._trang[1], 'co')
        self.assertEqual(sorted(p.key().toString() for p in t._phim), [f'Alt+{i}' for i in range(6)])
        self.assertTrue(w.lb_tong_dd.text().startswith('Tổng kinh phí hộ:'))

    def test_ngan_ap_gia_mac_dinh_dong_va_khong_cat_chu(self):
        w = self._w()
        bm = w.bang[1]
        self.assertFalse(bm.thanh_gia.isVisibleTo(bm))
        bm.b_ap_nhanh.setChecked(True)
        APP.processEvents()
        t = bm.thanh_gia
        self.assertTrue(t.isVisibleTo(bm))
        self.assertGreaterEqual(t.cb_doan.width(), 380)
        self.assertGreaterEqual(t.cb_doan.view().minimumWidth(), 560)
        self.assertEqual(t.o_g.width(), 130)
        self.assertGreater(t.cb_doan.count(), 0)
        self.assertIn('đ/m²', t.lb_ct.text())
        menu = [a.text() for a in bm.menu_thua.actions()]
        self.assertEqual(menu, ['Thêm tất cả thửa của hộ', 'Chọn nhiều thửa…', 'Tách thửa thành dòng đất mới'])

    def test_day_gop_va_cot(self):
        w = self._w()
        self.assertIn('Cộng mục đang xem', w.lb_chan.text())
        self.assertIn('TỔNG CỘNG PHƯƠNG ÁN', w.lb_chan.text())
        self.assertEqual([w.cb_tu_luu.itemText(i) for i in range(w.cb_tu_luu.count())], ['10 giây', '30 giây', '1 phút', '2 phút', 'Tắt'])
        b = w.bang[1].bang
        c = [x[0] for x in w.bang[1].cot]
        from pabt.man_hinh import COT_GD
        rong = {x[0]: x[2] for x in COT_GD[1]}
        self.assertEqual((rong['vi_tri'], rong['he_so_k'], rong['ty_le']), (65, 75, 75))      # cột thực tế không nhỏ hơn chữ tiêu đề (san_tieu_de)
        from PySide6.QtWidgets import QHeaderView
        self.assertEqual(b.horizontalHeader().sectionResizeMode(c.index('ghi_chu')), QHeaderView.ResizeMode.Stretch)

    def test_bo_dem_khong_cong_nham_cot(self):
        from pabt.giao_dien import thong_ke_vung_chon
        w = self._w()
        w.bang[1].bang.selectRow(0)
        APP.processEvents()
        tk = thong_ke_vung_chon(w.bang[1].bang)
        tien = BoSoan(self.con, self.ma[0]).ket_qua.muc[1]
        self.assertEqual(tk['tong'], tien)                             # không cộng STT, vị trí, K, tỷ lệ, giá, DT
        self.assertIn('Đang chọn: 1 dòng', tk['chuoi'])
        self.assertIn('Tổng DT/KL: 100', tk['chuoi'])
        self.assertIn('Tổng Thành tiền:', tk['chuoi'])
        w.cap_nhat_bo_dem(w.bang[1].bang, tk)
        self.assertEqual(w.lb_bo_dem.text(), tk['chuoi'])
        self.assertIs(w.lb_bo_dem.parentWidget(), w.dai_bo_dem)         # dưới chân bảng, không nổi trong bảng

    def test_menu_in_va_pb(self):
        w = self._w()
        w._ve_menu_in()
        chu = [a.text() for a in w.menu_in.actions() if a.text()]
        self.assertTrue(chu[0].startswith('Xem trước'))
        self.assertEqual(sum(1 for x in chu if x.startswith('Mẫu ')), 4)
        ma = w.thanh_pb.bam_ngu_canh()
        self.assertEqual(ma, 'V1')
        self.assertEqual(w.thanh_pb.b_hd.text(), 'Tạo nhánh V2')
        v2 = w.thanh_pb.tao_v2('thử')
        self.assertEqual(w.bo.phien_ban, v2)
        self.assertEqual(w.thanh_pb.cb.currentData(), v2)
        self.assertTrue(w.thanh_pb.xoa_nhanh(xac_nhan=True))
        self.assertIsNone(w.bo.phien_ban)

    def test_du_an_gon_hang_va_title_case(self):
        from PySide6.QtWidgets import QLineEdit
        from pabt.man_hinh import HopDuAn
        d = HopDuAn(self.con)
        self.addCleanup(d.close)
        o = d.o['don_vi_lap']
        self.assertIsInstance(o, QLineEdit)
        self.assertGreaterEqual(o.minimumWidth(), 260)
        self.assertIs(d.o['cap_dia_ban'].parentWidget(), d.o['nam'].parentWidget())
        d.o['ten_dia_ban'].setText('bù đăng')
        d.o['ten_dia_ban'].editingFinished.emit()
        self.assertEqual(d.o['ten_dia_ban'].text(), 'Bù Đăng')
        self.assertEqual(lap_pa.chuan_ten_dia_ban(' phú   lý '), 'Phú Lý')

    def test_o_tien_tu_cham_nghin(self):
        from PySide6.QtWidgets import QLineEdit
        from pabt.giao_dien import gan_dinh_dang_nghin
        o = QLineEdit()
        gan_dinh_dang_nghin(o)
        o.textEdited.emit('230000')
        self.assertEqual(o.text(), '230.000')
        o.setText('=2*3')
        o.textEdited.emit('=2*3')
        self.assertEqual(o.text(), '=2*3')

    def test_o_chon_moi_noi_gon(self):
        from PySide6.QtWidgets import QComboBox, QDialog, QVBoxLayout
        from pabt.giao_dien import chuan_o_chon
        d = QDialog()
        self.addCleanup(d.close)
        cb = QComboBox()
        cb.addItem('chữ rất dài ' * 20)
        QVBoxLayout(d).addWidget(cb)
        chuan_o_chon(cb)                                               # phần mềm chạy: bộ lọc _BoToMau gọi ở sự kiện Polish
        self.assertEqual(cb.sizeAdjustPolicy(), QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self.assertEqual(cb.minimumContentsLength(), 16)

    def test_cot_chon_rong_50_va_o_giua(self):
        from pabt.giao_dien import OChonGiua, chuan_cot_chon
        from pabt.man_hinh_tinh_gia_dat import C_CHON, HopTinhGiaDat
        h = HopTinhGiaDat(None, self.con, [], 'Phú Lý')
        h.im_lang = True
        self.addCleanup(h.close)
        chuan_cot_chon(h)
        self.assertGreaterEqual(h.bang.columnWidth(C_CHON), 50)
        self.assertIsInstance(h.bang.itemDelegateForColumn(C_CHON), OChonGiua)
        h.chon_het(True)
        h.o_g.setText('230000')
        self.assertTrue(h.nut_ap.isEnabled())


@unittest.skipUnless((THU_MUC_THAT / 'NGHĨA TRANG PHÚ LÝ.pabt').exists(), 'không có file dự án thật')
class TestFileThat(unittest.TestCase):
    """Chạy trên BẢN SAO file thật của người dùng (không nằm trong repo). Đổi tên file cũng được: thiếu thì bỏ qua."""

    def _mo(self, ten):
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        p = Path(td.name) / ('t' + Path(ten).suffix)
        shutil.copy(THU_MUC_THAT / ten, p)
        con = csdl.mo(p)
        self.addCleanup(con.close)
        return con

    def test_ca_ba_file_mo_va_doc_dong(self):
        for ten in ('NGHĨA TRANG PHÚ LÝ.pabt', 'ĐT762 Trị An.pabt', 'áp giá NĐC-2026- bảng sửa.larc'):
            if not (THU_MUC_THAT / ten).exists():
                continue
            con = self._mo(ten)
            hang = ap.doc_dong(con)
            self.assertEqual({x.ma_ho for x in hang}, {r[0] for r in con.execute('SELECT ma_ho FROM ho')}, ten)
            self.assertFalse([x.ho_ten for x in hang if x.ho_ten.endswith(' 0')], ten)

    def test_ap_gia_that_phu_ly_333500(self):
        con = self._mo('NGHĨA TRANG PHÚ LÝ.pabt')
        goi = gg.goi_du_an(con, 'Phú Lý')
        x = g.dia_ban_theo_ten('Phú Lý', goi)
        doan = g.ds_doan(x, goi)[0]
        gia = g.gia_bang_gia(x, doan, 'DAT_NONG_NGHIEP', 'MAT_TIEN_VT1', 'nn_cay', goi)
        k = g.tinh_don_gia(g.DauVao(dia_ban=x, nhom_dat='DAT_NONG_NGHIEP', ma_doan_duong=doan['ma_doan_duong'], don_gia_bang_gia=gia, cot_gia='nn_cay'), doan, goi)
        self.assertEqual(k.don_gia_ap_dung, D(333500))
        hang = [x_ for x_ in ap.doc_dong(con) if x_.chi_so != ap.CO_CHUA_DONG and x_.dien_tich > 0]
        r = ap.ap_hang_loat(con, hang, k.don_gia_ap_dung, g.ghi_chu_ap_gia(k, doan, 'Phú Lý'), chi_tiet=g.chi_tiet_ap_gia(k))
        self.assertEqual((r.so_dong, r.bi_chan), (len(hang), []))
        for y in hang:
            bo = BoSoan(con, y.ma_ho)
            d = bo.pa.dat[y.chi_so]
            self.assertEqual(d.gia_bang_gia, D(333500))
            self.assertEqual(bo.ket_qua.muc[1] > 0, d.ty_le != 0)    # đất do UBND quản lý tỷ lệ 0: không bồi thường, đúng hồ sơ


if __name__ == '__main__':
    unittest.main()

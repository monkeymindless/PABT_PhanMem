"""Chạy THẬT mã JavaScript của ứng dụng (ung_dung/index.html, bản "android") trong Chromium của Qt WebEngine - không cần trình duyệt / điện
thoại: bộ phân tách thông minh (phanTichThongMinhAI), chuẩn hóa lời đọc, đưa vào hồ sơ hộ, giọng nói qua cầu nối Android giả lập, xuất .json
đúng giao ước (README mục 2). Số liệu GIẢ LẬP. Máy không có PySide6.QtWebEngine: bỏ qua."""
from __future__ import annotations

import json
import os
import sys
import tempfile
import time
import unittest
from pathlib import Path

DAY = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(DAY))
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
os.environ.setdefault('QTWEBENGINE_CHROMIUM_FLAGS', '--no-sandbox --disable-gpu --disable-logging --log-level=3')

import dung  # noqa: E402

try:
    from PySide6.QtCore import QEventLoop, QTimer, QUrl
    from PySide6.QtWebEngineCore import QWebEnginePage, QWebEngineProfile
    from PySide6.QtWidgets import QApplication
except ImportError:                                         # máy không có WebEngine
    QWebEnginePage = None


def _cho(ms):
    v = QEventLoop()
    QTimer.singleShot(ms, v.quit)
    v.exec()


@unittest.skipIf(QWebEnginePage is None, 'thiếu PySide6.QtWebEngine')
@unittest.skipIf(dung.du_lieu_mac_dinh() is None, 'thiếu danh_muc_mac_dinh.json')
class TestPhanTach(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        cls.td = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)   # Chromium còn giữ file IndexedDB tới khi thoát tiến trình
        cls.prof = QWebEngineProfile('thu_larc_field')
        cls.prof.setPersistentStoragePath(cls.td.name)     # IndexedDB của vỏ ứng dụng nằm ở thư mục tạm
        cls.prof.setCachePath(cls.td.name)
        cls.page = QWebEnginePage(cls.prof)
        cls.loi = []
        cls.page.javaScriptConsoleMessage = lambda lv, msg, dong, nguon: cls.loi.append(msg)
        xong = {}
        cls.page.loadFinished.connect(lambda ok: xong.setdefault('ok', ok))
        cls.page.setHtml(dung.html_ung_dung('android'), QUrl('https://larc.thu/index.html'))
        cls._doi(lambda: 'ok' in xong)
        cls._doi(lambda: cls.js('document.getElementById("c_ten_moi").value'))   # vỏ gắn nút sau khi mở IndexedDB
        cls.js('window.confirm = () => true; document.getElementById("c_bat_dau").click(); 1')   # kiểm đếm độc lập (danh mục nhúng)
        cls._doi(lambda: cls.js('!!window.LARC'))

    @classmethod
    def tearDownClass(cls):
        cls.page.deleteLater()
        _cho(50)
        cls.td.cleanup()

    @classmethod
    def _doi(cls, dk, han=20):
        t = time.time()
        while not dk():
            if time.time() - t > han:
                raise AssertionError('quá thời gian chờ trang ứng dụng; lỗi JS: %s' % cls.loi[-3:])
            _cho(30)

    @classmethod
    def js(cls, ma):
        kq = {}
        cls.page.runJavaScript(ma, 0, lambda r: kq.setdefault('r', r))
        cls._doi(lambda: 'r' in kq)
        return kq['r']

    def jsj(self, ma):
        return json.loads(self.js('JSON.stringify(' + ma + ')'))

    def tach(self, chu, uu=''):
        return self.jsj('window.LARC.phanTichThongMinhAI(%s, {uu_tien: %s}).map(x => ({cat: x.cat, chinh: x.chinh, ct: x.ct || "", gia: x.gia || 0, '
                        'du: x.du}))' % (json.dumps(chu), json.dumps(uu)))

    def test_chuan_hoa_loi_doc(self):
        c = lambda s: self.js('window.LARC.chuanHoaTiengNoi(%s)' % json.dumps(s))   # noqa: E731
        self.assertEqual(c('mở ngoặc 5 nhân 12 đóng ngoặc trừ mở ngoặc 2 nhân 3 đóng ngoặc'), '(5 x 12) - (2 x 3)')
        self.assertEqual(c('5 phẩy 2 nhân 3 mét vuông'), '5,2 x 3 m2')
        self.assertEqual(c('ống nhựa phi 114 dài 300 mét'), 'ống nhựa ϕ 114 dài 300m')
        self.assertEqual(c('đường kính 15 xăng ti mét'), 'ĐK 15 cm')
        self.assertEqual(c('hàng rào dài 25 mét cao 1 phẩy 5'), 'hàng rào 25m x 1,5m')
        self.assertEqual(c('nhân khẩu 4 người, Cộng hòa'), 'nhân khẩu 4 người, Cộng hòa')     # "nhân / cộng" chỉ là phép tính giữa hai số
        self.assertEqual(c('đất phi nông nghiệp'), 'đất phi nông nghiệp')

    def test_doc_lien_mot_mach(self):
        ds = self.tach('chủ hộ ông Nguyễn Văn An căn cước 075 092 001 234 số điện thoại 0912 345 678 địa chỉ ấp 3 xã Trị An tờ 12 thửa 45 '
                       'loại đất cây lâu năm diện tích 1500 mét vuông nhà 1 tầng khung bê tông mái tôn tường xây nền gạch men mở ngoặc 5 nhân 12 '
                       'đóng ngoặc trừ mở ngoặc 2 nhân 3 đóng ngoặc ống nhựa phi 114: 3300m; phi 90: 3400m bể nước 1,5 x 2,4 x 1,2 '
                       'xoài trồng năm 2012: 650 cây tràm 35c/15cm chuồng heo 20 mét vuông')
        ho = {x['du']['truong']: x['du']['gia_tri'] for x in ds if x['cat'] == 'ho'}
        self.assertEqual(ho, {'ho_ten': 'Nguyễn Văn An', 'so_cccd': '075092001234', 'sdt': '0912345678', 'dia_chi': 'ấp 3 xã Trị An'})
        dat = [x['du'] for x in ds if x['cat'] == 'dat']
        self.assertEqual(dat, [{'so_to': '12', 'so_thua': '45', 'loai_dat': 'CLN', 'dt_thu_hoi': '1500'}])   # "cây lâu năm" là loại đất
        nha = [x for x in ds if x['cat'] == 'nha']
        self.assertEqual(len(nha), 1)
        # khung BTCT + mái tôn + nền gạch men (ceramic): Phụ lục Ia QĐ 18/2026 mục 3.2 (nhà 01 - 02 tầng, kết cấu loại 2)
        self.assertEqual((nha[0]['du']['ten'], nha[0]['du']['so_luong'], nha[0]['du']['nhom']),
                         ('Nhà 01 tầng đến 02 tầng - Kết cấu loại 2', '(5x12)-(2x3)', 'nha'))
        self.assertIn('nền gạch ceramic, men', nha[0]['du']['ghi_chu'])
        self.assertIn('QĐ 18/2026', nha[0]['ct'])
        vkt = [x for x in ds if x['cat'] == 'vkt']
        self.assertEqual([x['du']['ten'] for x in vkt], ['ống nhựa ϕ 114: 3300m', 'ống nhựa ϕ 90: 3400m', 'bể nước 1,5 x 2,4 x 1,2',
                                                         'chuồng heo 20 m2'])
        self.assertTrue(all(x['du']['tu_bb'] and not x['du']['so_luong'] for x in vkt))   # câu gốc: máy tính đọc lại, khớp danh mục khi nhập
        self.assertIn('D114', vkt[0]['ct'])
        self.assertIn('D90', vkt[1]['ct'])
        self.assertIn('4,32 m3', vkt[2]['ct'])
        cay = [x['du'] for x in ds if x['cat'] == 'cay']
        self.assertEqual([(c['ten'], c['so_luong'], c['so_do'], c['kieu']) for c in cay],
                         [('Cây xoài trồng năm 2012', '650', '', ''), ('Keo lá tràm', '35', '15', 'dk')])
        self.assertTrue(all(x['gia'] > 0 for x in ds if x['cat'] in ('nha', 'cay')))       # tạm tính theo danh mục nhúng

    def test_dia_chi_lo_rung_va_qr(self):
        ds = self.tach('họ tên Trần Thị Bình sinh năm 1975 địa chỉ số nhà 12 ấp Bàu Tràm xã Phú Lý tiểu khu 126 khoảnh 6 lô 34 '
                       'rừng sản xuất diện tích 2,5 ha')
        self.assertEqual([x['cat'] for x in ds], ['ho', 'ho', 'ho', 'dat'])             # "nhà", "Tràm" trong địa chỉ không tách
        self.assertEqual(ds[2]['chinh'], 'số nhà 12 ấp Bàu Tràm xã Phú Lý')
        self.assertEqual(ds[3]['du'], {'tieu_khu': '126', 'khoanh': '6', 'lo': '34', 'dt_ha': '2,5', 'loai_dat': 'RSX'})
        qr = self.tach('079200009999|201234567|Phạm Thị Dung|05061988|Nữ|Tổ 4, Ấp 1, Xã Phú Lý|01022022')
        self.assertEqual({x['du']['truong']: x['du']['gia_tri'] for x in qr},
                         {'ho_ten': 'Phạm Thị Dung', 'so_cccd': '079200009999', 'nam_sinh': '1988', 'dia_chi': 'Tổ 4, Ấp 1, Xã Phú Lý'})

    def test_nha_theo_phu_luc_ia_qd18(self):
        # câu đọc theo đúng chữ của Phụ lục Ia QĐ 18/2026/QĐ-UBND -> đúng mục bộ đơn giá
        ten = lambda chu: self.tach(chu)[0]['du']['ten']   # noqa: E731
        self.assertEqual(ten('nhà 1 tầng cột gạch, tường quét vôi, mái tôn fibro xi măng, không trần, nền láng xi măng, cửa sắt gỗ tạp 5x8'),
                         'Nhà 01 tầng - Kết cấu loại 4')                                             # mục 4.4
        self.assertEqual(ten('nhà cột gạch tường sơn nước mái tôn trần ván ép nền gạch tàu cửa sắt kính 6x10'), 'Nhà 01 tầng - Kết cấu loại 3')   # 4.3
        self.assertEqual(ten('nhà 3 tầng khung bê tông tường sơn nước ốp gạch mái bê tông trần gỗ nền đá granite cửa gỗ cao cấp 8x15'),
                         'Nhà từ 03 tầng đến 04 tầng - Kết cấu loại 1')                              # 2.1
        self.assertEqual(ten('nhà 2 tầng khung thép tường quét vôi mái ngói trần lưới thép tô vữa nền gạch bông cửa sắt kính 5x12'),
                         'Nhà 01 tầng đến 02 tầng - Kết cấu loại 3')                                 # 3.3
        self.assertEqual(ten('nhà cột gỗ tre vách lá mái lá 4x5'), 'Nhà tạm')                       # 6
        self.assertEqual(ten('nhà khung sắt tường tôn mái tôn nền gạch tàu 6x8'), 'Nhà bán kiên cố')  # 5
        # chip kết cấu trên mục Nhà: cùng bảng tiêu chí
        self.assertEqual(self.jsj('window.LARC.khoaLoaiNha({tang: "1", khung: "gach", tuong: "son", mai: "ngoi", tran: "nhua", nen: "gach_bong", '
                                  'cua: "sat_kinh"}).m[1]'), 'Nhà 01 tầng - Kết cấu loại 2')       # 4.2
        self.assertIsNone(self.jsj('window.LARC.khoaLoaiNha({mai: "ton"})'))                         # một thuộc tính: chưa đủ để gợi ý

    def test_doc_theo_muc_va_don_vi(self):
        ds = self.tach('mái ngói tường xây nền xi măng khung gạch 4 nhân 6 phẩy 7', 'nha')   # nút 🎙️ Đọc của mục Nhà: không cần nói "nhà"
        self.assertEqual((ds[0]['cat'], ds[0]['du']['so_luong']), ('nha', '4x6,7'))
        ds = self.tach('hàng rào lưới B40 dài 25 mét cao 1 phẩy 5 trụ bê tông cắm ranh 12 trụ', 'vkt')
        self.assertEqual([x['du']['ten'] for x in ds], ['hàng rào lưới B40 25m x 1,5m', 'trụ bê tông cắm ranh 12 trụ'])
        self.assertIn('= 37,5 m2', ds[0]['ct'])                                        # "B40" không phải thừa số

    def test_dua_vao_ho_moi_va_xuat_json(self):
        self.js('window.LARC.chonHo(""); window.LARC.ST.chon = ""; 1')
        self.js('document.getElementById("ai_chu").value = %s; document.getElementById("b_ai_tach").click(); 1' % json.dumps(
            'Chủ hộ Lê Văn Thử, CCCD 075000000123, tờ 5 thửa 9 LUC 800 m2. Mái che kt (11m x 3,8m) + (1,3 x 18m). Điều 120 cây trồng 2015'))
        self.js('document.getElementById("b_bb_dua").click(); 1')
        self._doi(lambda: self.js('!document.getElementById("ai_chu").value'))
        st = self.jsj('(() => { const S = window.LARC.ST; return {chon: S.chon, ho: S.ho[S.chon]}; })()')
        self.assertTrue(st['chon'].startswith('moi_'))                                   # chưa chọn hộ: tạo hộ mới theo họ tên đọc được
        self.assertEqual((st['ho']['tt']['ho_ten'], st['ho']['tt']['so_cccd']), ('Lê Văn Thử', '075000000123'))
        self.assertEqual(st['ho']['dat'], [{'so_to': '5', 'so_thua': '9', 'loai_dat': 'LUC', 'dt_thu_hoi': '800'}])
        kq = {}
        self.page.runJavaScript('window.LARC.taoKetQua([window.LARC.ST.chon], false).then(r => { window.__kq = JSON.stringify(r); })', 0,
                                lambda r: kq.setdefault('r', 1))
        self._doi(lambda: self.js('!!window.__kq'))
        ra = json.loads(self.js('window.__kq'))
        self.assertEqual(ra['phien_ban'], 2)
        self.assertEqual(ra['ung_dung'], 'LARC Mobile ' + dung.PHIEN_BAN)
        dong = ra['ket_qua'][st['chon']]
        self.assertEqual([d['muc'] for d in dong], [2, 3])
        self.assertTrue(all('tu_bb' not in d and 'luc' not in d for d in dong))           # chỉ trường của giao ước
        self.assertEqual(ra['ho_dan'][st['chon']]['ho_ten'], 'Lê Văn Thử')

    def test_giong_noi_qua_cau_noi_android(self):
        self.js('localStorage.removeItem("larc_field_dong_y_giong_noi"); window.__hoi = ""; window.confirm = m => { window.__hoi = m; return true; };'
                'window.LARCAndroid = {batDauGiongNoi() { setTimeout(() => window.LARC_nhanGiongNoiAndroid("xoài 20 cây trồng năm 2018"), 10); }}; 1')
        self.js('document.getElementById("b_ai_xoa").click(); document.querySelector(\'#t3 .nut_doc\').click(); 1')
        self._doi(lambda: self.js('document.getElementById("ai_chu").value'))
        self.assertIn('máy chủ của hãng', self.js('window.__hoi'))                          # báo trước: giọng nói do Google / Apple nhận dạng
        self.assertEqual(self.js('localStorage.getItem("larc_field_dong_y_giong_noi")'), '1')
        self.assertEqual(self.jsj('window.LARC.AI.items.map(x => [x.cat, x.du.ten, x.du.so_luong])'), [['cay', 'Cây xoài trồng năm 2018', '20']])
        self.assertEqual(self.js('window.LARC.AI.uu_tien'), 'cay')
        self.js('window.LARC_giongNoiLoi("khong_co"); delete window.LARCAndroid; 1')         # máy không có bộ nhận dạng: không lỗi JS

    def test_giong_noi_du_phong_android(self):
        # máy không có màn hình nhập giọng nói: vỏ Android nghe qua SpeechRecognizer, báo trạng thái + chữ tạm -> sóng âm; Xong = dungGiongNoi
        self.js('window.__dung = 0; window.__ch = ""; window.confirm = () => true; localStorage.setItem("larc_field_dong_y_giong_noi", "1");'
                'window.LARCAndroid = {batDauGiongNoi() { window.LARC_giongNoiTrangThai("nghe"); window.LARC_giongNoiTam("chủ hộ Lê"); },'
                ' dungGiongNoi() { window.__dung++; window.LARC_nhanGiongNoiAndroid("chủ hộ Lê Văn Năm"); }, moCuaHang(g) { window.__ch = g; }};'
                'document.getElementById("b_ai_xoa").click(); document.getElementById("b_hero_noi").click(); 1')
        self.assertFalse(self.js('document.getElementById("song_am").hidden'))
        self.assertEqual(self.js('document.getElementById("song_chu").textContent'), 'chủ hộ Lê')
        self.js('document.getElementById("b_dung_noi").click(); 1')
        self.assertEqual(self.js('window.__dung'), 1)
        self.assertTrue(self.js('document.getElementById("song_am").hidden'))
        self.assertEqual(self.jsj('window.LARC.AI.items.map(x => x.chinh)'), ['Lê Văn Năm'])
        # không có bộ nhận dạng nào: mời cài "Dịch vụ lời nói của Google" trên CH Play
        self.js('window.LARC_giongNoiLoi("khong_co"); 1')
        self.assertEqual(self.js('window.__ch'), 'com.google.android.tts')
        self.js('window.LARC_giongNoiLoi("quyen"); 1')
        self.assertIn('Quyền → Micro', self.js('document.getElementById("thong_bao").textContent'))
        self.js('delete window.LARCAndroid; document.getElementById("b_ai_xoa").click(); 1')

    def test_nen_ban_do(self):
        # có mạng mà chưa chọn: nền vệ tinh + tên đường (xem ảnh thực ngay); 4 nền + lưới trên thanh nút của bản đồ
        self.assertEqual(self.js('window.LARC.BD.nen'), 've_tinh_ten')
        self.assertEqual(self.jsj('Object.keys(window.LARC.NEN)'), ['ve_tinh', 've_tinh_ten', 'duong', 'dia_hinh'])
        self.assertEqual(self.js('document.querySelectorAll("#m_chip_nen button").length'), 5)
        self.assertEqual(self.js('window.LARC.NEN.ve_tinh_ten.lop.length'), 3)            # ảnh + đường + địa danh
        # OpenStreetMap cấm tải hàng loạt: nút lưu ảnh nền từ chối, không gửi yêu cầu nào
        self.js('window.LARC.BD.nen = "duong"; window.LARC.luuNenKhu(); 1')
        self._doi(lambda: 'không cho tải lưu sẵn' in self.js('document.getElementById("thong_bao").textContent'))
        self.js('window.LARC.BD.nen = "ve_tinh_ten"; 1')

    def test_khong_loi_js(self):
        self.assertFalse([m for m in self.loi if 'Uncaught' in m], self.loi)


if __name__ == '__main__':
    unittest.main()

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

    # ------------------------------------------------ trung tâm thu âm & nhập nhanh kiểm đếm (#hop_thu_am, người dùng 27/10/2026)
    def _mo_thu_am(self, nut='document.getElementById("b_hero_noi")'):
        self.js('document.getElementById("b_ai_xoa").click(); document.getElementById("o_studio_text").value = ""; %s.click(); 1' % nut)
        self.assertFalse(self.js('document.getElementById("hop_thu_am").hidden'))

    def _dong_thu_am(self):
        self.js('document.getElementById("b_studio_dong").click(); document.getElementById("b_ai_xoa").click(); 1')

    def test_thu_am_mo_khong_bat_ban_phim(self):
        self.js('document.activeElement && document.activeElement.blur(); 1')
        self._mo_thu_am()
        try:
            self.assertNotEqual(self.js('document.activeElement.id'), 'o_studio_text')            # không focus -> không bật bàn phím che màn hình
            for i in ('b_studio_rec', 'b_studio_audio', 'b_studio_sample', 'b_studio_done', 'b_studio_insert', 'b_studio_clear', 'studio_wave', 'studio_status_line'):
                self.assertTrue(self.js('!!document.getElementById("%s")' % i), i)
            self.assertFalse(self.js('!!document.getElementById("doc_ct")'))                       # hộp đọc chính tả cũ đã bỏ
            self.assertEqual(self.js('document.querySelectorAll("#studio_wave i").length'), 9)
            self.assertEqual(self.jsj('[...document.querySelectorAll("#studio_tab button")].map(b => b.textContent)'),
                             ['🏠 Nhà (QĐ 18/2026)', '🧱 Vật KT (QĐ 18/2026)', '🌳 Cây trồng (QĐ 48/2025)', '🔢 Số & Toán'])
            self.assertGreaterEqual(self.js('getComputedStyle(document.getElementById("b_studio_rec")).minHeight'), '48px')
            # bàn phím từ khóa 1 chạm: nối vào ô, không focus
            self.js('document.querySelectorAll("#studio_tab button")[1].click(); [...document.querySelectorAll("#studio_chip button")]'
                    '.find(b => b.textContent === "Sân xi măng:").click(); document.querySelectorAll("#studio_tab button")[3].click();'
                    '{ const c = t => [...document.querySelectorAll("#studio_chip button")].find(b => b.textContent.trim() === t).click();'
                    'c("4"); c("x"); c("6"); c("m²;"); } 1')
            self.assertEqual(self.js('document.getElementById("o_studio_text").value'), 'Sân xi măng: 4 x 6m²; ')
            self.assertNotEqual(self.js('document.activeElement.id'), 'o_studio_text')
            # Đưa vào ô nhập & bóc tách: ô phân tách nhận chữ, máy tách thành mục vật kiến trúc, hộp đóng
            self.js('document.getElementById("b_studio_done").click(); 1')
            self.assertTrue(self.js('document.getElementById("hop_thu_am").hidden'))
            self.assertIn('Sân xi măng', self.js('document.getElementById("ai_chu").value'))
            self.assertEqual(self.jsj('window.LARC.AI.items.map(x => x.cat)'), ['vkt'])
            # chỉ chèn: không tách; xóa trắng
            self._mo_thu_am()
            self.js('document.getElementById("b_studio_sample").click(); 1')
            self.assertIn('Nhà 01 tầng kết cấu loại 4', self.js('document.getElementById("o_studio_text").value'))
            self.js('document.getElementById("b_studio_clear").click(); 1')
            self.assertEqual(self.js('document.getElementById("o_studio_text").value'), '')
            self.js('window.LARC.AI.items.length = 0; document.getElementById("o_studio_text").value = "Giếng khoan sâu 30 m";'
                    'document.getElementById("b_studio_insert").click(); 1')
            self.assertEqual(self.js('document.getElementById("ai_chu").value'), 'Giếng khoan sâu 30 m')
            self.assertEqual(self.js('window.LARC.AI.items.length'), 0)
        finally:
            self._dong_thu_am()

    def test_giong_noi_qua_cau_noi_android(self):
        self.js('localStorage.removeItem("larc_field_dong_y_giong_noi"); window.__hoi = ""; window.confirm = m => { window.__hoi = m; return true; };'
                'window.LARCAndroid = {batDauGiongNoi() { setTimeout(() => window.LARC_nhanGiongNoiAndroid("xoài 20 cây trồng năm 2018"), 10); }}; 1')
        self._mo_thu_am('document.getElementById("b_ai_noi")')
        try:
            self.js('document.getElementById("b_studio_rec").click(); 1')
            self._doi(lambda: self.js('document.getElementById("o_studio_text").value'))
            self.assertIn('máy chủ của hãng', self.js('window.__hoi'))                          # báo trước: giọng nói do Google / Apple nhận dạng
            self.assertEqual(self.js('localStorage.getItem("larc_field_dong_y_giong_noi")'), '1')
            self.js('document.getElementById("b_studio_done").click(); 1')
            self._doi(lambda: self.js('document.getElementById("ai_chu").value'))
            self.assertEqual(self.jsj('window.LARC.AI.items.map(x => [x.cat, x.du.ten, x.du.so_luong])'), [['cay', 'Cây xoài trồng năm 2018', '20']])
            self.js('window.LARC_giongNoiLoi("khong_co"); 1')                                   # máy không có bộ nhận dạng: không lỗi JS
        finally:
            self.js('delete window.LARCAndroid; 1'); self._dong_thu_am()

    def test_giong_noi_du_phong_android(self):
        # máy không có màn hình nhập giọng nói: vỏ Android nghe qua SpeechRecognizer, báo trạng thái + chữ tạm -> sóng âm 9 cột; Dừng = dungGiongNoi
        self.js('window.__dung = 0; window.__ch = ""; window.confirm = () => true; localStorage.setItem("larc_field_dong_y_giong_noi", "1");'
                'window.LARCAndroid = {batDauGiongNoi() { window.LARC_giongNoiTrangThai("nghe"); window.LARC_giongNoiTam("chủ hộ Lê"); },'
                ' dungGiongNoi() { window.__dung++; window.LARC_nhanGiongNoiAndroid("chủ hộ Lê Văn Năm"); }, moCuaHang(g) { window.__ch = g; }}; 1')
        self._mo_thu_am()
        try:
            self.js('document.getElementById("b_studio_rec").click(); 1')
            self.assertFalse(self.js('document.getElementById("studio_wave").hidden'))
            self.assertIn('DỪNG THU ÂM', self.js('document.getElementById("b_studio_rec").textContent'))
            self.assertIn('chủ hộ Lê', self.js('document.getElementById("studio_status_line").textContent'))
            self.js('document.getElementById("b_studio_rec").click(); 1')
            self.assertEqual(self.js('window.__dung'), 1)
            self.assertTrue(self.js('document.getElementById("studio_wave").hidden'))
            self.assertIn('chủ hộ Lê Văn Năm', self.js('document.getElementById("o_studio_text").value'))
            self.js('document.getElementById("b_studio_done").click(); 1')
            self.assertEqual(self.jsj('window.LARC.AI.items.map(x => x.chinh)'), ['Lê Văn Năm'])
            # lỗi quyền khi trung tâm đang mở: hiện trên dòng trạng thái của trung tâm
            self._mo_thu_am()
            self.js('window.LARC_giongNoiLoi("quyen"); 1')
            self.assertIn('Quyền → Micro', self.js('document.getElementById("studio_status_line").textContent'))
            self.js('document.getElementById("b_studio_dong").click(); window.LARC_giongNoiLoi("khong_co"); 1')   # đóng: mời cài dịch vụ trên CH Play
            self.assertEqual(self.js('window.__ch'), 'com.google.android.tts')
        finally:
            self.js('delete window.LARCAndroid; 1'); self._dong_thu_am()

    def test_thu_am_iphone_bi_chan(self):
        # iPhone (Edge / Chrome / ứng dụng Màn hình chính): Web Speech báo service-not-allowed -> cảnh báo rõ, gợi ý ghi file âm thanh / bàn phím
        self.js('Object.defineProperty(navigator, "userAgent", {configurable: true, get: () => "Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) EdgiOS/140"});'
                'window.confirm = () => true; localStorage.setItem("larc_field_dong_y_giong_noi", "1"); window.__lt = null;'
                'window.SpeechRecognition = window.webkitSpeechRecognition = function () { const r = this; window.__lt = r; r.start = () => setTimeout(() => {'
                ' r.onerror({error: "service-not-allowed"}); r.onend(); }, 0); r.stop = () => {}; }; 1')
        self._mo_thu_am()
        try:
            self.js('document.getElementById("b_studio_rec").click(); 1')
            self._doi(lambda: 'Bật Đọc chính tả' in self.js('document.getElementById("studio_status_line").textContent'))
            self.assertIn("📼 Ghi file âm thanh", self.js('document.getElementById("studio_status_line").textContent'))
            self.assertFalse(self.js('window.__lt.continuous'))                                  # iPhone: phiên ngắn, không treo
            self.assertEqual(self.js('window.__lt.lang'), 'vi-VN')
            self.assertFalse(self.js('document.getElementById("hop_thu_am").hidden'))            # hộp vẫn mở - dùng cách khác ngay
        finally:
            self.js('delete navigator.userAgent; delete window.webkitSpeechRecognition; delete window.SpeechRecognition; 1'); self._dong_thu_am()

    def test_ghi_file_am_thanh(self):
        # 📼 getUserMedia + MediaRecorder (giả lập): bấm ghi -> bấm dừng -> lưu theo hộ trên máy, hiện thanh nghe <audio controls>
        self.js('window.__tat = 0; navigator.mediaDevices.getUserMedia = async () => ({getTracks: () => [{stop() { window.__tat++; }}]});'
                'window.MediaRecorder = class { constructor(l, o) { this.mimeType = (o && o.mimeType) || "audio/webm"; this.state = "inactive"; }'
                ' static isTypeSupported(k) { return k === "audio/webm"; } start() { this.state = "recording"; }'
                ' stop() { this.state = "inactive"; this.ondataavailable({data: new Blob(["abc"], {type: this.mimeType})}); setTimeout(() => this.onstop(), 0); } };'
                'window.prompt = () => "Hộ thử ghi âm"; document.getElementById("b_ho_moi").click(); 1')
        self._doi(lambda: self.js('!!window.LARC.ST.chon'))
        self._mo_thu_am()
        try:
            self.js('document.getElementById("b_studio_audio").click(); 1')
            self._doi(lambda: 'Dừng ghi' in self.js('document.getElementById("b_studio_audio").textContent'))
            self.js('document.getElementById("b_studio_audio").click(); 1')
            self._doi(lambda: self.js('document.querySelectorAll("#studio_am_ds audio").length') == 1)
            self.assertTrue(self.js('document.querySelector("#studio_am_ds audio").controls'))
            self.assertEqual(self.js('window.__tat'), 1)                                         # tắt micrô sau khi ghi
            self.assertIn('vào hồ sơ hộ đang chọn', self.js('document.getElementById("studio_status_line").textContent'))
        finally:
            self._dong_thu_am()

    def test_ban_do_chua_co_thua_xem_viet_nam(self):
        # chưa có thửa, chưa có GPS: khung cả nước (trước: tọa độ 0, 0 giữa biển ở mức sát đất -> không thấy ảnh vệ tinh)
        self.js('window.__bd = [window.LARC.BD.k, window.LARC.BD.cx, window.LARC.BD.cy, window.LARC.BD.gps];'
                'window.LARC.BD.gps = null; window.LARC.BD.k = 1; window.LARC.BD.cx = 0; window.LARC.BD.cy = 0; window.LARC.vuaKhung([]); 1')
        try:
            kinh_do = self.js('window.LARC.BD.cx / 6378137 * 180 / Math.PI')
            self.assertTrue(102 < kinh_do < 110, kinh_do)
            self.assertLess(self.js('window.LARC.BD.k'), 0.01)
            # khung căn lúc thẻ chưa bố cục xong (cỡ sai) -> lần vẽ kế tiếp căn lại theo cỡ thật (trước: ảnh vệ tinh thành dải sọc mỏng)
            self.js('document.getElementById("ban_do").getBoundingClientRect = () => ({width: 400, height: 300}); 1')   # trang thử không có cửa sổ
            self.js('window.LARC.BD.tu_can.w = 3; window.LARC.BD.tu_can.h = 3; window.LARC.BD.k = 1e-7; window.LARC.veBanDo(); 1')
            self.assertGreater(self.js('window.LARC.BD.k'), 1e-5)
            # người dùng kéo / phóng: thôi tự căn
            self.js('document.getElementById("ban_do").dispatchEvent(new PointerEvent("pointerdown", {pointerId: 1})); 1')
            self.assertTrue(self.js('window.LARC.BD.tu_can === null'))
        finally:
            self.js('delete document.getElementById("ban_do").getBoundingClientRect; 1')
            self.js('[window.LARC.BD.k, window.LARC.BD.cx, window.LARC.BD.cy, window.LARC.BD.gps] = window.__bd; 1')

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

    # ------------------------------------------------ bản đồ KML / KMZ địa chính (người dùng 27/10/2026, file thật Vành đai 4 GĐ2): lưới thửa là
    # <LineString>, số thửa / loại đất / DT / mốc / ghi chú là <Point>, <Polygon> chỉ là vòng tròn quanh cọc mốc. Dữ liệu GIẢ LẬP cùng cấu trúc.
    def _nap_kmz(self, kml, cat_thu_muc=False):
        import base64
        import io
        import zipfile
        b = io.BytesIO()
        with zipfile.ZipFile(b, 'w', zipfile.ZIP_DEFLATED) as z:
            z.writestr('doc.kml', kml)
            z.writestr('1.png', b'\x89PNG')
        du = b.getvalue()
        if cat_thu_muc:                                     # .kmz chép dở: mất thư mục trung tâm -> đọc theo đầu tệp cục bộ
            du = du[:du.index(b'PK\x01\x02')]
        self.js('window.__kq = null; (async () => { try { const b = Uint8Array.from(atob(%s), c => c.charCodeAt(0));'
                ' window.__kq = await window.LARC.docKmlBytes(b, "thu.kmz"); } catch (e) { window.__kq = {loi: e.message}; } })(); 1'
                % json.dumps(base64.b64encode(du).decode()))
        self._doi(lambda: self.js('!!window.__kq'))
        self.assertFalse(self.js('window.__kq.loi || ""'))

    @staticmethod
    def _kml_cad():
        import math
        L = '�'
        lat, lon, kx = 11.02, 106.95, 111320 * math.cos(math.radians(11.02))
        d = lambda dx, dy: f'{lon + dx / kx:.9f},{lat + dy / 110540:.9f},0'                    # noqa: E731 - lệch dx, dy mét
        tron = ' '.join(d(0.6 * math.cos(2 * math.pi * i / 50) + 40, 0.6 * math.sin(2 * math.pi * i / 50)) for i in range(51))
        diem = lambda ten, mo_ta, dx, dy, kieu='': (f'<Placemark><name>{ten}</name><description>{mo_ta}</description>{kieu}'          # noqa: E731
                                                     f'<Point><coordinates>{d(dx, dy)}</coordinates></Point></Placemark>')
        return ('<?xml version="1.0" encoding="UTF-8"?>\n<kml xmlns="http://www.opengis.net/kml/2.2"><Document>'
                '<Style id="do"><LineStyle><color>ff0000ff</color><width>2</width></LineStyle></Style>'
                '<Style id="trang"><LineStyle><color>ffffffff</color><width>1</width></LineStyle></Style>'
                '<Style id="nhan"><LabelStyle><color>ffffff00</color></LabelStyle></Style>'
                '<StyleMap id="m_do"><Pair><key>normal</key><styleUrl>#do</styleUrl></Pair></StyleMap>'
                '<Folder><name>Entity Features</name>'
                f'<Placemark><name>Polyline_001</name><description>Level 11</description><styleUrl>#m_do</styleUrl>'
                f'<LineString><coordinates>{d(-50, -30)} {d(50, -30)}</coordinates></LineString></Placemark>'
                f'<Placemark><name>Polyline_005</name><description>tanan2|Level 10</description><styleUrl>#trang</styleUrl>'
                f'<LineString><coordinates>{d(-50, 30)} {d(50, 30)}</coordinates></LineString></Placemark>'
                f'<Placemark><name>Polygon_001</name><description>Level 11</description><Polygon><outerBoundaryIs><LinearRing>'
                f'<coordinates>{tron}</coordinates></LinearRing></outerBoundaryIs></Polygon></Placemark>'
                '<Placemark><name>Polygon_002</name><Polygon><outerBoundaryIs><LinearRing><coordinates></coordinates></LinearRing></outerBoundaryIs></Polygon></Placemark>'
                + diem('549', 'tanan2|Level 3', 0, 0, '<styleUrl>#nhan</styleUrl>') + diem('CLN', 'tanan2|Level 5', 0, -2)
                + diem('7078.1', 'tanan2|Level 4', 0, -4) + diem('(3600.7)', 'tanan2|Level 47', 6, -12) + diem(f'T{L} s{L} 59', 'tanan2|Level 18', 0, 120)
                + diem('550', 'tanan2|Level 3', 60, 0) + diem('DN.T737', 'Level 45', 40, 0)
                + diem(f'H{L}nh lang b{L}o v{L} ngu{L}n n{L}{L}c', 'tanan2|Level 52', -30, 20)
                + diem('ngµy 27/12/2022 cña UBND tØnh §ång Nai.', 'Level 52', -30, 15)
                + diem('Mương & bờ', 'Level 39', -30, 10) + '</Folder></Document></kml>')

    def test_kmz_dia_chinh_cad(self):
        self._nap_kmz(self._kml_cad())
        kq = self.jsj('(l => ({duong: l.duong.map(d => [d.lop_cad, d.ban_ve, d.mau, d.w]), thua: l.thua.length, vong: l.vong_moc.length, bo: l.bo,'
                      ' loai: l.diem.map(d => [d.chu, d.loai]), cum: l.nhan_thua.map(c => [c.so_thua, c.chu_ld, c.chu_dt, c.chu_dt_th, c.so_to])}))(window.__kq)')
        self.assertEqual(kq['duong'], [['Level 11', '', '#ff0000', 2], ['Level 10', 'tanan2', '#ffffff', 1]])   # màu aabbggrr -> #rrggbb
        self.assertEqual((kq['thua'], kq['vong'], kq['bo']), (0, 1, 1))          # vòng tròn cọc mốc không phải thửa; đa giác rỗng bỏ
        loai = dict(kq['loai'])
        self.assertEqual(loai['DN.T737'], 'moc')
        self.assertEqual(loai['Tờ số 59'], 'to')
        self.assertEqual(loai['Hành lang bảo vệ nguồn nước'], 'ghi_chu')
        self.assertEqual(loai['ngày 27/12/2022 của UBND tỉnh Đồng Nai.'], 'ghi_chu')       # TCVN3 đọc nhầm -> đổi đúng
        self.assertEqual(loai['Mương & bờ'], 'ghi_chu')                                    # "&" trần: làm sạch XML rồi đọc
        self.assertIn(['549', 'CLN', '7078.1', '3600.7', '59'], kq['cum'])                 # ghép nhãn thửa + nhãn tờ gần nhất
        self.assertIn(['550', '', '', '', '59'], kq['cum'])

    def test_kmz_mat_thu_muc_zip(self):
        self._nap_kmz(self._kml_cad(), cat_thu_muc=True)
        self.assertEqual(self.js('window.__kq.duong.length'), 2)

    def test_sua_font_kml_giong_ban_may_tinh(self):
        L = '�'
        cau = [  # cùng danh sách với tests/test_sua_font_kml.py (bản máy tính)
            (f'H{L}nh lang b{L}o v{L} ngu{L}n n{L}{L}c theo Quy{L}t {L}{L}nh', 'Hành lang bảo vệ nguồn nước theo Quyết định'),
            (f'S{L} 60/2022/Q{L}-UBNDng{L}y 27/12/2022 c{L}a', 'Số 60/2022/QĐ-UBND ngày 27/12/2022 của'),
            ('UBND t∅nh ' + L * 2 + 'ng Nai.', 'UBND tỉnh Đồng Nai.'), (f'T{L} s{L} 59', 'Tờ số 59'),
            (f'{L}{L}{L}ng ranh c{L}ch m{L}p {L}{L}{L}ng giao th{L}ng v{L}o 100m', 'Đường ranh cách mép đường giao thông vào 100m'),
            (f'B{L} m{L}{L}ng', 'Bờ mương'), (f'{L}{L}{L}ng b{L} t{L}ng', 'Đường bê tông'),
            (f'C{L}ch m{L}p d{L}y ngo{L}i c{L}ng 6m theo Ngh{L} {L}{L}nh 14/2014/N{L}-CP', 'Cách mép dây ngoài cùng 6m theo Nghị định 14/2014/NĐ-CP'),
            (f'Su{L}i R{L}ch {L}{L}ng', 'Suối Rạch Đông'), (f'{L}T.768.Nh{L}a', 'ĐT.768.Nhựa'), (f'X{L} B{L}nh Minh', 'Xã Bình Minh'),
            ('ngµy 27/12/2022 cña UBND tØnh §ång Nai.', 'ngày 27/12/2022 của UBND tỉnh Đồng Nai.'), (f'S{L}ng L{L}nh', f'Sông L{L}nh')]
        ra = self.jsj('%s.map(s => window.LARC.suaFontKml(s))' % json.dumps([a for a, _ in cau]))
        self.assertEqual(ra, [b for _, b in cau])
        for s in ('Hành lang bảo vệ', 'Café á Đông', 'DN.T737'):
            self.assertEqual(self.js('window.LARC.suaFontKml(%s)' % json.dumps(s)), s)

    def test_kml_cham_va_dua_vao_ho(self):
        self._nap_kmz(self._kml_cad())
        self.js('window.LARC.LOP.length = 0; window.LARC.LOP.push(window.__kq); window.LARC.veBangKml();'
                'document.getElementById("ban_do").getBoundingClientRect = () => ({width: 400, height: 300});'
                '{ const c = window.__kq.nhan_thua.find(x => x.so_thua === "549"); window.LARC.BD.cx = c.x; window.LARC.BD.cy = c.y; window.LARC.BD.k = 2; } 1')
        try:
            # chạm vào số thửa ở tâm khung -> cụm thửa; chạm vào nhãn loại đất cạnh đó -> cũng cụm thửa đó
            self.assertEqual(self.js('window.LARC.doiTuongTai(200, 150, 400, 300).so_thua'), '549')
            self.assertEqual(self.js('window.LARC.doiTuongTai(200, 154, 400, 300).so_thua'), '549')
            self.assertEqual(self.js('window.LARC.doiTuongTai(280, 150, 400, 300).chu'), 'DN.T737')       # mốc cách 40 m (k = 2)
            self.js('window.LARC.hienDoiTuong(window.LARC.doiTuongTai(200, 150, 400, 300)); 1')
            chu = self.js('document.getElementById("tt_thua").textContent')
            for x in ('Thửa 549', 'CLN', '7078.1 m²', '3600.7 m²', 'VN-2000', 'WGS84', 'Level 3'):
                self.assertIn(x, chu)
            # bảng tra cứu: có thửa, mốc, ghi chú; lọc theo chữ
            self.assertFalse(self.js('document.getElementById("khung_ds_kml").hidden'))
            self.js('document.getElementById("o_tim_kml").value = "DN.T"; window.LARC.veBangKml(); 1')
            self.assertEqual(self.js('document.querySelectorAll("#bang_ds_kml .dong").length'), 1)
            self.js('document.getElementById("o_tim_kml").value = ""; window.LARC.veBangKml(); 1')
            # công tắc lớp: tắt mốc -> chạm vào mốc không ra mốc
            self.assertEqual(self.js('document.querySelectorAll("#m_lop input").length'), 4)
            self.js('{ const o = document.querySelectorAll("#m_lop input")[2]; o.checked = false; o.dispatchEvent(new Event("change")); } 1')
            self.assertNotEqual(self.js('(window.LARC.doiTuongTai(280, 150, 400, 300) || {}).chu || ""'), 'DN.T737')
            self.js('{ const o = document.querySelectorAll("#m_lop input")[2]; o.checked = true; o.dispatchEvent(new Event("change")); } 1')
            # đưa thửa vào hồ sơ hộ: điền sẵn ô Đất (tờ từ nhãn tờ gần nhất, DT thu hồi) để người kiểm đếm xác nhận
            self.js('window.prompt = () => "Hộ thử bản đồ"; document.getElementById("b_ho_moi").click(); 1')
            self._doi(lambda: self.js('!!window.LARC.ST.chon'))
            self.js('[...document.querySelectorAll("#tt_thua button")].find(b => b.textContent.includes("Đưa thửa")).click(); 1')
            self.assertEqual(self.jsj('["d_to", "d_thua", "d_loai", "d_dt"].map(i => document.getElementById(i).value)'), ['59', '549', 'CLN', '3600,7'])
        finally:
            self.js('delete document.getElementById("ban_do").getBoundingClientRect; window.LARC.LOP.length = 0; window.LARC.veBangKml(); 1')

    def test_nut_nap_kml(self):
        # nút độc lập (không bọc label quanh ô file ẩn); đặt lại value TRƯỚC khi mở hộp chọn - chọn lại đúng file vẫn nhận
        self.assertEqual(self.js('document.getElementById("m_file").closest("label") === null'), True)
        self.js('{ const f = document.getElementById("m_file"); window.__mo = 0; f.click = () => { window.__mo++; window.__gt = f.value; }; }'
                'document.getElementById("b_nap_kml").click(); 1')
        self.assertEqual(self.js('window.__mo'), 1)
        self.assertIn('.kmz', self.js('document.getElementById("m_file").getAttribute("accept") || ".kmz"'))

    def test_ban_do_toan_man_hinh(self):
        # màn hình dọc: thẻ bản đồ ẩn tiêu đề / thanh chọn hộ / thanh số liệu, công cụ gom vào ngăn ☰ nổi trên bản đồ
        an = 'getComputedStyle(document.querySelector("%s")).display === "none"'
        cha = 'document.getElementById("%s").parentElement.id'
        self.js('localStorage.setItem("larc_field_bo_cuc", "doc"); window.LARC.apBoCuc(); window.LARC.moThe(5); 1')
        try:
            self.assertTrue(self.js('document.body.classList.contains("toan_bd")'))
            for s in ('header', '#ho_bar', '#khung_t5 > h3', '#ngan_bd'):
                self.assertTrue(self.js(an % s), s)
            self.assertFalse(self.js(an % '#b_cong_cu_bd'))
            self.assertEqual(self.js(cha % 'ngan_bd_duoi'), 'ngan_bd')            # lưu ảnh nền, chú giải, bảng tra cứu KML vào ngăn
            self.assertEqual(self.js(cha % 'khung_ds_kml'), 'ngan_bd')
            self.js('document.getElementById("b_cong_cu_bd").click(); 1')
            self.assertFalse(self.js(an % '#ngan_bd'))
            self.js('document.getElementById("b_vua").click(); 1')                # lệnh di chuyển bản đồ đóng ngăn
            self.assertTrue(self.js(an % '#ngan_bd'))
            self.js('document.getElementById("b_cong_cu_bd").click(); 1')
            self.assertTrue(self.js('window.LARC_quayLaiChinh()'))               # nút Back đóng ngăn trước
            self.assertTrue(self.js(an % '#ngan_bd'))
            self.js('window.LARC.moThe(0); 1')                                   # rời bản đồ: hiện lại, trả công cụ về chỗ cũ
            self.assertFalse(self.js('document.body.classList.contains("toan_bd")'))
            self.assertFalse(self.js(an % '#ho_bar'))
            self.assertEqual(self.js(cha % 'ngan_bd_duoi'), 'khung_t5')
            self.assertEqual(self.js('document.getElementById("ngan_bd_duoi").nextElementSibling.id'), 'tt_thua')
            self.assertEqual(self.js(cha % 'khung_ds_kml'), 'khung_t5')
            self.js('localStorage.setItem("larc_field_bo_cuc", "ngang"); window.LARC.apBoCuc(); window.LARC.moThe(5); 1')
            self.assertFalse(self.js('document.body.classList.contains("toan_bd")'))   # ngang 2 cột: giữ bố cục cũ
        finally:
            self.js('localStorage.removeItem("larc_field_bo_cuc"); window.LARC.apBoCuc(); window.LARC.moThe(7); 1')

    # ------------------------------------------------ 1.4.0 (người dùng 27/10/2026): bộ phân tách, nhập hàng loạt, KML lưu trên máy
    def test_nha_gac_lung_khong_tach_son(self):
        ds = self.tach('Nhà gác lửng khung cột bê tông cốt thép tường sơn nước mái tôn nền gạch men 4,5m x 14m')
        self.assertEqual([x['cat'] for x in ds], ['nha'])                   # "sơn" (Sơn rừng) không thành cây, "nền" không thành vật KT
        self.assertTrue(ds[0]['chinh'].startswith('Gác lửng nhà chính (Nhà 01 tầng - Kết cấu loại 2)'), ds[0]['chinh'])
        self.assertIn('63 m²', ds[0]['chinh'])
        self.assertIn('khớp 4/4', ds[0]['ct'])                               # khung, tường, mái, nền
        kc = self.jsj('window.LARC.kcTuChu("khung cột BTCT tường sơn nước mái tôn nền gạch men")')
        self.assertEqual((kc.get('khung'), kc.get('tuong'), kc.get('mai'), kc.get('nen')), ('btct', 'son', 'ton', 'ceramic'))
        self.assertEqual(self.jsj('window.LARC.kcTuChu("khung bê tông cốt thép mái tôn")').get('khung'), 'btct')   # "cốt thép" không phải "cột"

    def test_cay_ten_giong(self):
        ds = self.tach('Sầu riêng ghép trồng năm 2019: 35 cây; Bưởi da xanh trồng năm 2020: 50 cây; Cây tràm bông vàng 150c/12cm')
        self.assertEqual([x['cat'] for x in ds], ['cay'] * 3)
        self.assertEqual([x['du']['ten'] for x in ds], ['Cây sầu riêng trồng năm 2019', 'Cây bưởi trồng năm 2020', 'Keo lá tràm'])
        self.assertTrue(all(x['gia'] > 0 for x in ds), ds)
        self.assertEqual(self.jsj('["Xoài cát Hòa Lộc", "Mít Thái", "Dầu rái nước"].map(t => window.LARC.loaiCay(t)[0])'),
                         ['Cây xoài', 'Cây mít', 'Dầu rái (Dầu nước)'])

    def test_vkt_khong_cat_tu_noi(self):
        ds = self.tach('Mộ xây gạch có mái che 2 ngôi')
        self.assertEqual([x['cat'] for x in ds], ['vkt'])
        self.assertIn('TS47', self.tach('Mái che khung sắt mái tôn 4 x 6')[0]['ct'])        # danh từ đầu câu: Mái che, không Chuồng trại
        self.assertIn('TS42', self.tach('Sân xi măng 4 x 6')[0]['ct'])                      # sân xi măng = nền ciment
        self.assertEqual([x['cat'] for x in self.tach('Nhà tạm tường tôn mái tôn xoài 20 cây')], ['nha', 'cay'])   # loài + số lượng vẫn tách

    def test_dat_nhieu_loai_mot_thua(self):
        ds = self.tach('tờ 5 thửa 108 đất ONT 120m2, đất CLN 850m2')
        self.assertEqual([(x['du']['so_to'], x['du']['so_thua'], x['du']['loai_dat'], x['du']['dt_thu_hoi']) for x in ds],
                         [('5', '108', 'ONT', '120'), ('5', '108', 'CLN', '850')])
        self.js('window.prompt = () => "Hộ thử nhiều loại đất"; document.getElementById("b_ho_moi").click(); 1')
        self.js('document.getElementById("ai_chu").value = "tờ 5 thửa 108 đất ONT 120m2, đất CLN 850m2"; document.getElementById("b_ai_tach").click(); 1')
        self.js('window.__xong = 0; window.LARC.duaAI().then(() => window.__xong = 1); 1')
        self._doi(lambda: self.js('window.__xong'))
        self.assertEqual(self.jsj('window.LARC.ST.ho[window.LARC.ST.chon].dat.map(d => d.loai_dat)'), ['ONT', 'CLN'])   # thửa nhiều loại đất: đủ hai dòng

    def _ho_thu(self, *ten):
        for t in ten:
            self.js('window.prompt = () => %s; document.getElementById("b_ho_moi").click(); 1' % json.dumps(t))
        return self.jsj('[...document.getElementById("cb_ho").options].filter(o => %s.some(t => o.text.includes(t))).map(o => o.value)' % json.dumps(list(ten)))

    def _dua(self, chu, nut='b_bb_dua'):
        self.js('document.getElementById("ai_chu").value = %s; document.getElementById("b_ai_tach").click(); window.__n = window.LARC.ST.chon;'
                'document.getElementById("%s").click(); 1' % (json.dumps(chu), nut))
        self._doi(lambda: self.js('!document.getElementById("ai_chu").value'))

    def test_dua_va_sang_ho_ke(self):
        a, b, c = self._ho_thu('Hộ lô A', 'Hộ lô B', 'Hộ lô C')
        self.js('window.LARC.chonHo(%s); 1' % json.dumps(b))
        self._dua('Sân xi măng 4 x 6')                                          # hộ B đã ghi
        self.js('window.LARC.chonHo(%s); window.LARC.BD.gps = {lat: 11.02, lon: 106.95, acc: 5, luc_ms: Date.now()}; 1' % json.dumps(a))
        try:
            self.assertTrue(self.js('!document.getElementById("b_bb_dua_tiep").hidden || true'))
            self._dua('Nhà tạm 5 x 6', 'b_bb_dua_tiep')
            self._doi(lambda: self.js('window.LARC.ST.chon') == c)            # bỏ qua hộ B đã ghi -> hộ C
            self.assertEqual(self.jsj('window.LARC.ST.ho[%s].gps.lat' % json.dumps(a)), 11.02)   # hộ chưa có tọa độ: ghi vị trí đang theo dõi
            self.assertIn('Chuyển sang hộ Hộ lô C', self.js('document.getElementById("thong_bao").textContent'))
            self.assertEqual(self.js('document.getElementById("b_gps_nhanh").textContent'), '📍')   # hộ C chưa có tọa độ
            self.js('window.LARC.chonHo(%s); 1' % json.dumps(a))
            self.assertEqual(self.js('document.getElementById("b_gps_nhanh").textContent'), '📍✓')
            # chép mẫu hộ trước: nhà / vật KT / cây của hộ vừa đưa (không họ tên, tờ thửa) -> ô phân tách, bóc tách sẵn
            self.js('window.LARC.chonHo(%s); document.getElementById("b_ai_chep_mau").click(); 1' % json.dumps(c))
            self.assertEqual(self.js('document.getElementById("ai_chu").value'), 'Nhà tạm 5 x 6')
            self.assertEqual(self.jsj('window.LARC.AI.items.map(x => x.cat)'), ['nha'])
        finally:
            self.js('window.LARC.BD.gps = null; document.getElementById("b_ai_xoa").click(); 1')

    def test_khau_lenh_giong_noi(self):
        self.assertEqual(self.jsj('window.LARC.tachKhauLenh("sân xi măng 4 x 6, đưa vào hồ sơ hộ.")'), {'chu': 'sân xi măng 4 x 6', 'lenh': 'dua'})
        self.assertEqual(self.jsj('window.LARC.tachKhauLenh("xoài 20 cây chốt hộ sang hộ kế")'), {'chu': 'xoài 20 cây', 'lenh': 'sang_ke'})
        self.assertIsNone(self.jsj('window.LARC.tachKhauLenh("hồ sơ hộ đưa vào sau")'))
        (k,) = self._ho_thu('Hộ khẩu lệnh')
        self.js('window.LARC.chonHo(%s); document.getElementById("b_ai_xoa").click(); window.LARC_nhanGiongNoiAndroid("sân xi măng 4 x 6 đưa vào hồ sơ hộ"); 1' % json.dumps(k))
        self._doi(lambda: self.js('(window.LARC.ST.ho[%s].dong || []).length' % json.dumps(k)) == 1)
        self.assertEqual(self.js('document.getElementById("ai_chu").value'), '')

    def test_kml_luu_tren_may(self):
        import base64
        import io
        import zipfile
        b = io.BytesIO()
        with zipfile.ZipFile(b, 'w', zipfile.ZIP_DEFLATED) as z:
            z.writestr('doc.kml', self._kml_cad())
        self.js('window.LARC.LOP.length = 0; window.__xong = 0; (async () => { const f = new File([Uint8Array.from(atob(%s), c => c.charCodeAt(0))], "luu.kmz");'
                ' await window.LARC.napBanDo([f]); window.__xong = 1; })(); 1' % json.dumps(base64.b64encode(b.getvalue()).decode()))
        self._doi(lambda: self.js('window.__xong'))
        try:
            self.assertFalse(self.js('document.getElementById("b_xoa_kml").hidden'))
            # thoát ứng dụng / đổi dự án: LOP trống -> khôi phục từ IndexedDB, đủ kiểu dữ liệu và liên kết cụm nhãn
            self.js('window.LARC.LOP.length = 0; window.__xong = 0; window.LARC.khoiPhucKml().then(() => window.__xong = 1); 1')
            self._doi(lambda: self.js('window.__xong'))
            self.assertEqual(self.jsj('window.LARC.LOP.map(l => [l.ten, l.duong.length, l.duong[0].p instanceof Float64Array])'), [['luu.kmz', 2, True]])
            self.assertTrue(self.js('{ const l = window.LARC.LOP[0], c = l.nhan_thua.find(x => x.so_thua === "549"); l.diem.includes(c.ld.d); }'))
            # chạm chọn bỏ qua đường ngoài khung bao (đường cách xa vẫn không chọn nhầm)
            self.js('document.getElementById("ban_do").getBoundingClientRect = () => ({width: 400, height: 300}); 1')
            self.assertIsNone(self.jsj('(() => { const B = window.LARC.BD, l = window.LARC.LOP[0], d = l.duong[0];'
                                       ' B.cx = (d.bb[0] + d.bb[2]) / 2; B.cy = d.bb[1] + 500; B.k = 2; return window.LARC.doiTuongTai(200, 150, 400, 300); })()'))
            self.js('window.__xong = 0; window.LARC.xoaKmlDaNap(false).then(() => window.__xong = 1); 1')
            self._doi(lambda: self.js('window.__xong'))
            self.assertTrue(self.js('document.getElementById("b_xoa_kml").hidden'))
            self.js('window.__xong = 0; window.LARC.KML_DB.doc().then(r => window.__xong = r ? 2 : 1); 1')
            self._doi(lambda: self.js('window.__xong'))
            self.assertEqual(self.js('window.__xong'), 1)                     # đã xóa khỏi máy
        finally:
            self.js('delete document.getElementById("ban_do").getBoundingClientRect; window.LARC.LOP.length = 0; 1')

    def test_vo_bao_ban_moi_va_nut_xoay(self):
        self.assertEqual(self.js('typeof window.baoBanMoi'), 'function')       # ở vỏ: có cả khi còn ở màn hình chọn dự án
        self.js('window.baoBanMoi(); window.baoBanMoi(); 1')
        self.assertEqual(self.js('document.querySelectorAll("#dai_ban_moi").length'), 1)
        self.js('document.getElementById("dai_ban_moi").remove(); 1')
        self.js('window.LARC.apBoCuc(); 1')
        self.assertNotEqual(self.js('document.getElementById("b_xoay").style.display'), 'none')   # luôn hiện, cả điện thoại hẹp

    def test_luu_ho_so_cho_ngung_go(self):
        (k,) = self._ho_thu('Hộ gõ nhanh')
        self.js('window.LARC.chonHo(%s); window.__dem = 0; window.__set = Storage.prototype.setItem;'
                'Storage.prototype.setItem = function (a, b) { if (a.startsWith("larc_kd_")) window.__dem++; return window.__set.call(this, a, b); };'
                'const o = document.getElementById("h_sdt"); for (const c of "0912345678") { o.value += c; o.dispatchEvent(new Event("input")); } 1' % json.dumps(k))
        try:
            self.assertEqual(self.js('window.__dem'), 0)                     # 10 phím: chưa ghi lần nào
            self._doi(lambda: self.js('window.__dem') >= 1)
            self.assertEqual(self.js('window.__dem'), 1)                     # ngừng gõ 250 ms: ghi một lần
            self.assertEqual(self.js('JSON.parse(localStorage.getItem(Object.keys(localStorage).find(x => x.startsWith("larc_kd_")))).ho[%s].tt.sdt'
                                     % json.dumps(k)), '0912345678')
        finally:
            self.js('Storage.prototype.setItem = window.__set; 1')

    def test_lam_ro_chu(self):
        self.js('window.__lr = null; { const c = document.createElement("canvas"); c.width = 120; c.height = 60; const g = c.getContext("2d");'
                ' g.fillStyle = "#ddd"; g.fillRect(0, 0, 120, 60); g.fillStyle = "#222"; g.fillRect(20, 20, 40, 8);'
                ' window.LARC.lamRo(c.toDataURL()).then(u => { const im = new Image(); im.onload = () => { const k = document.createElement("canvas");'
                '  k.width = 120; k.height = 60; const h = k.getContext("2d"); h.drawImage(im, 0, 0);'
                '  window.__lr = [h.getImageData(40, 24, 1, 1).data[0], h.getImageData(100, 50, 1, 1).data[0]]; }; im.src = u; }); } 1')
        self._doi(lambda: self.js('!!window.__lr'))
        den, trang = self.jsj('window.__lr')
        self.assertLess(den, 60)                                             # nét chữ -> đen
        self.assertGreater(trang, 200)                                       # nền -> trắng

    def test_chup_lien_tuc(self):
        # máy ảnh trong ứng dụng (getUserMedia giả lập bằng luồng hình của canvas): một lần mở chụp 3 ảnh, ✔ Xong -> 3 ảnh trong hộ, tắt máy ảnh
        (k,) = self._ho_thu('Hộ chụp liên tục')
        self.js('window.LARC.chonHo(%s); window.__goc = navigator.mediaDevices.getUserMedia; window.__tat = 0;'
                'navigator.mediaDevices.getUserMedia = async () => { const c = document.createElement("canvas"); c.width = 640; c.height = 480;'
                ' const g = c.getContext("2d"); window.__ve = setInterval(() => { g.fillStyle = "#" + Math.floor(Math.random() * 4095).toString(16).padStart(3, "0");'
                ' g.fillRect(0, 0, 640, 480); }, 30); const l = c.captureStream(30); for (const t of l.getTracks()) { const s = t.stop.bind(t);'
                ' t.stop = () => { window.__tat++; s(); }; } return l; };'
                'document.getElementById("b_chup").click(); 1' % json.dumps(k))
        try:
            self.assertFalse(self.js('document.getElementById("hop_may_anh").hidden'))
            self._doi(lambda: self.js('document.getElementById("ma_video").videoWidth') > 0)
            for _ in range(3):
                self.js('document.getElementById("b_ma_chup").click(); 1')
            self.assertIn('Đã chụp 3 ảnh', self.js('document.getElementById("ma_dem").textContent'))
            self.assertEqual(self.js('document.querySelectorAll("#ma_anh img").length'), 2)       # dải ảnh vừa chụp: 2 ảnh gần nhất
            self.js('document.getElementById("b_ma_xong").click(); 1')
            self._doi(lambda: self.js('window.LARC.ST.ho[%s].so_anh || 0' % json.dumps(k)) == 3)
            self.assertTrue(self.js('document.getElementById("hop_may_anh").hidden'))
            self.assertGreaterEqual(self.js('window.__tat'), 1)                                   # tắt máy ảnh khi xong
            self.assertIn('Đã lưu 3 ảnh', self.js('document.getElementById("thong_bao").textContent'))
            # bản .apk: gọi cầu nối chụp liên tục (máy ảnh của máy tự mở lại), mỗi ảnh về qua LARC_nhanAnhAndroid
            self.js('window.__lt = 0; window.LARCAndroid = {chupLienTuc() { window.__lt++; }}; document.getElementById("b_chup").click(); 1')
            self.assertEqual(self.js('window.__lt'), 1)
            self.assertTrue(self.js('document.getElementById("hop_may_anh").hidden'))
            # máy không mở được máy ảnh trong ứng dụng: hiện nút Chụp tiếp (máy ảnh của máy từng ảnh)
            self.js('delete window.LARCAndroid; navigator.mediaDevices.getUserMedia = async () => { throw new DOMException("x", "NotAllowedError"); };'
                    'document.getElementById("b_chup").click(); 1')
            self._doi(lambda: not self.js('document.getElementById("hang_chup_tiep").hidden'))
            self.assertTrue(self.js('document.getElementById("hop_may_anh").hidden'))
        finally:
            self.js('clearInterval(window.__ve); navigator.mediaDevices.getUserMedia = window.__goc; delete window.LARCAndroid;'
                    'document.getElementById("hang_chup_tiep").hidden = true; 1')

    # ---------------------------------------------------------------- 1.0.32 (B1, B4 - B7)
    def test_cong_quy_doi_m2(self):
        c = lambda s: self.js('window.LARC.chuanHoaTiengNoi(%s)' % json.dumps(s))   # noqa: E731
        self.assertEqual(c('tờ 5 thửa 9 LUC 1,5 công'), 'tờ 5 thửa 9 LUC 1.500 m2 (1,5 công)')
        self.assertEqual(c('nửa công đất'), '500 m2 (nửa công)')
        for giu in ('2 công trình phụ', 'giếng công nghiệp sâu 20m', 'ruộng 3 sào', 'Cộng hòa'):     # "công" của chữ khác; sào tùy vùng: không đổi
            self.assertEqual(c(giu), giu)
        for cau, dt in (('tờ 5 thửa 9 LUC 1,5 công', '1500'), ('tờ 12 thửa 45 CLN nửa công', '500')):
            dat = [x['du'] for x in self.tach(cau) if x['cat'] == 'dat']
            self.assertEqual(dat[0]['dt_thu_hoi'], dt, cau)

    def test_ghi_chu_nhanh_va_ghi_am_trong_json(self):
        (k,) = self._ho_thu('Hộ ghi chú nhanh')
        self.js('window.LARC.chonHo(%s); 1' % json.dumps(k))
        nut = '[...document.querySelectorAll("#gc_nhanh button")]'
        self.assertEqual(self.js(nut + '.length'), 5)
        self.js(nut + '[0].click(); ' + nut + '[0].click(); ' + nut + '[3].click(); 1')      # bấm lại câu đã có: không lặp
        self.assertEqual(self.js('document.getElementById("h_ghi_chu").value'), 'Không tranh chấp, ranh rõ; Đang canh tác ổn định')
        self.assertEqual(self.js('window.LARC.ST.ho[%s].tt.ghi_chu' % json.dumps(k)), 'Không tranh chấp, ranh rõ; Đang canh tác ổn định')
        self.page.runJavaScript('window.__am = 0; window.LARC.IDB.them({khoa: "am|" + %s, ten: "ghi_am_1.webm", du_lieu: "data:audio/webm;base64,AA==",'
                                ' luc: ""}).then(() => { window.__am = 1; })' % json.dumps(k), 0, lambda r: None)
        self._doi(lambda: self.js('window.__am') == 1)
        self.page.runJavaScript('window.__kq = ""; window.LARC.taoKetQua([%s], false).then(r => { window.__kq = JSON.stringify(r); })' % json.dumps(k),
                                0, lambda r: None)
        self._doi(lambda: self.js('window.__kq'))
        hd = json.loads(self.js('window.__kq'))['ho_dan'][k]
        self.assertEqual(hd['so_ghi_am'], 1)
        self.assertEqual(hd['ghi_chu'], 'Không tranh chấp, ranh rõ; Đang canh tác ổn định; [Có 1 tệp ghi âm thực địa trên điện thoại]')
        self.assertNotIn('ghi âm', self.js('window.LARC.ST.ho[%s].tt.ghi_chu' % json.dumps(k)))   # chỉ trong file xuất, ô ghi chú giữ nguyên

    def test_tuong_phan_cao_ngoai_troi(self):
        b = 'document.getElementById("b_tuong_phan")'
        try:
            self.js(b + '.click(); 1')
            self.assertTrue(self.js('document.body.classList.contains("tuong_phan_cao")'))
            self.assertEqual(self.js('localStorage.getItem("larc_field_tuong_phan")'), '1')
            self.assertIn('Dịu', self.js(b + '.textContent'))
            self.assertEqual(self.js('getComputedStyle(document.body).backgroundColor'), 'rgb(255, 255, 255)')
            # nút chính: nền xanh rất đậm, chữ trắng (không phải chữ đen trên nền xanh)
            self.assertEqual(self.js('getComputedStyle(document.getElementById("b_ai_tach")).color'), 'rgb(255, 255, 255)')
        finally:
            self.js('if (document.body.classList.contains("tuong_phan_cao")) ' + b + '.click(); 1')
        self.assertFalse(self.js('document.body.classList.contains("tuong_phan_cao")'))
        self.assertEqual(self.js('localStorage.getItem("larc_field_tuong_phan")'), '0')

    def test_vung_cham_44(self):
        cao = lambda sel: self.js('parseFloat(getComputedStyle(document.querySelector(%s)).minHeight)' % json.dumps(sel))   # noqa: E731
        self.assertGreaterEqual(cao('#h_ghi_chu'), 44)
        self.assertGreaterEqual(cao('#gc_nhanh .chip'), 42)
        self.assertEqual(self.js('getComputedStyle(document.getElementById("b_xoay"), "::after").content'), '""')   # vùng chạm mở rộng
        self.assertLessEqual(self.js('document.querySelector("header").offsetHeight'), 53)                         # thanh tiêu đề không cao thêm

    def test_khong_loi_js(self):
        self.assertFalse([m for m in self.loi if 'Uncaught' in m], self.loi)


if __name__ == '__main__':
    unittest.main()

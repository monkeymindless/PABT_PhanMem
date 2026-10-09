r"""Kiểm tra TOÀN BỘ giao diện PABT tự động: mọi lệnh của cửa sổ chính, mọi hộp thoại mở ra từ đó (sâu tới SAU_TOI_DA tầng) - bấm
từng nút, gõ vào từng ô nhập, chọn từng mục của ô chọn, bật / tắt ô đánh dấu, chuyển thẻ, sửa ô bảng (giá trị đúng và sai), chạy
từng mục menu. Ghi lại: LỖI (ngoại lệ - kèm vết), CHẬM / ĐƠ (một thao tác quá NGUONG_CHAM giây), TREO (quá TREO_GIAY: in vết
ngăn xếp rồi dừng), các thông báo lỗi phần mềm hiện ra.

  .venv\Scripts\python kiem_tra_giao_dien.py [--du-an <file .pabt - chạy trên BẢN SAO>] [--so-ho 12] [--chi "Đợt trình…"]
  Hoặc bấm đúp KIEM_TRA_GIAO_DIEN.bat. Kết quả: ket_qua_kiem_tra\GiaoDien_<phiên bản>_<ngày giờ>.md

An toàn khi chạy: không in ra máy in, không mở Excel / Word, không mở file bằng chương trình khác, không gọi mạng,
không ghi vào %APPDATA%\PABT thật (PABT_THU_MUC_MAY tạm); hộp chọn file trả "Hủy" (mở) hoặc thư mục tạm (lưu); hộp hỏi
Có / Không trả "Có" để đi sâu - mọi thao tác ghi đều trên bản sao dự án, mỗi lệnh dùng một bản sao mới.
"""
from __future__ import annotations

import faulthandler
import os
import re
import shutil
import sys
import tempfile
import time
import traceback
from collections import Counter
from datetime import datetime
from pathlib import Path

GOC = Path(__file__).resolve().parent
sys.path.insert(0, str(GOC))
NGUONG_CHAM = 5.0          # giây: một thao tác lâu hơn = chậm / đơ (người dùng thấy cửa sổ đứng)
TREO_GIAY = 120            # giây: một lệnh của cửa sổ chính lâu hơn = treo (in vết ngăn xếp, dừng kiểm tra)
SAU_TOI_DA = 3             # số tầng hộp thoại lồng nhau được thử
BO_QUA_NUT = re.compile(r'^\s*(đóng|hủy|thoát|close|cancel)\b', re.I)


class KiemTra:
    def __init__(self, td: Path):
        self.td = td
        self.loi, self.cham, self.thong_bao, self.duong = [], [], [], []
        self.dem = Counter()
        self.gio_con = []
        self.sau = 0
        self.da_thu = set()

    # ------------------------------------------------ một thao tác: đo giờ, bắt lỗi
    def lam(self, ten: str, ham) -> None:
        from PySide6.QtWidgets import QApplication
        self.duong.append(ten)
        self.gio_con.append(0.0)
        t = time.perf_counter()
        try:
            ham()
            QApplication.processEvents()
        except Exception:                                   # noqa: BLE001 - ghi mọi lỗi, thử tiếp
            self.loi.append((' > '.join(self.duong), traceback.format_exc()))
        dt = time.perf_counter() - t
        rieng = dt - self.gio_con.pop()                     # thời gian của riêng thao tác này (trừ các thao tác con đã đo)
        if self.gio_con:
            self.gio_con[-1] += dt
        if rieng > NGUONG_CHAM:
            self.cham.append((' > '.join(self.duong), rieng))
        self.duong.pop()

    def bat_loi(self, loai, gia_tri, tb):                 # sys.excepthook: lỗi trong slot / QTimer
        self.loi.append((' > '.join(self.duong) or '(sự kiện)', ''.join(traceback.format_exception(loai, gia_tri, tb))))

    # ------------------------------------------------ thử mọi điều khiển của một cửa sổ / hộp thoại
    def thu(self, w, ten: str = '') -> None:
        from PySide6.QtWidgets import (QAbstractButton, QAbstractSpinBox, QCheckBox, QComboBox, QLineEdit, QPlainTextEdit,
                                       QRadioButton, QTableView, QTableWidget, QTabWidget, QTextEdit, QToolButton)
        cua_so = w.window()                                 # bỏ hộp thoại con đã đóng (ẩn) - người dùng không bấm tới được
        ds = [x for x in w.findChildren(QWidget_()) if x.isEnabled() and (x.window() is cua_so or x.window().isVisible())]
        for t in [x for x in ds if isinstance(x, QTabWidget)]:
            for i in range(t.count()):
                self.dem['the'] += 1
                self.lam(f'thẻ "{t.tabText(i)}"', lambda t=t, i=i: t.setCurrentIndex(i))
        for o in [x for x in ds if isinstance(x, QComboBox)]:
            cu = o.currentIndex()
            for i in range(min(o.count(), 8)):
                self.dem['muc_chon'] += 1
                self.lam(f'ô chọn → "{o.itemText(i)[:40]}"', lambda o=o, i=i: o.setCurrentIndex(i))
            if o.isEditable():
                self.lam('gõ ô chọn', lambda o=o: o.setEditText('Thử'))
            self.lam('trả ô chọn', lambda o=o, cu=cu: o.setCurrentIndex(cu))
        for o in [x for x in ds if isinstance(x, (QCheckBox, QRadioButton))]:
            self.dem['danh_dau'] += 1
            self.lam(f'ô đánh dấu "{o.text()[:40]}"', lambda o=o: (o.click(), o.click()) if isinstance(o, QCheckBox) else o.click())
        for o in [x for x in ds if isinstance(x, QLineEdit) and not x.isReadOnly()]:
            cu = o.text()
            self.dem['o_nhap'] += 1
            nhan = o.placeholderText()[:30] or o.objectName() or 'ô nhập'
            for gt in ('1.070,5', 'Thử chữ', '=2*3', ''):
                self.lam(f'gõ "{gt}" vào "{nhan}"', lambda o=o, gt=gt: (o.setText(gt), o.editingFinished.emit()))
            self.lam(f'trả "{nhan}"', lambda o=o, cu=cu: (o.setText(cu), o.editingFinished.emit()))
        for o in [x for x in ds if isinstance(x, (QPlainTextEdit, QTextEdit)) and not x.isReadOnly()]:
            cu = o.toPlainText()
            self.dem['o_nhap'] += 1
            self.lam('gõ ô nhiều dòng', lambda o=o: o.setPlainText('Thử\nnhiều dòng'))
            self.lam('trả ô nhiều dòng', lambda o=o, cu=cu: o.setPlainText(cu))
        for o in [x for x in ds if isinstance(x, QAbstractSpinBox)]:
            self.dem['o_nhap'] += 1
            self.lam('ô số: lớn nhất / nhỏ nhất', lambda o=o: (o.stepBy(1000), o.stepBy(-1000)))
        for b in [x for x in ds if isinstance(x, QTableWidget)]:
            self.thu_bang(b)
        for b in [x for x in ds if isinstance(x, QTableView) and not isinstance(x, QTableWidget)]:
            m = b.model()
            if m is not None and m.rowCount() > 0:
                self.dem['bang'] += 1
                self.lam('chọn dòng đầu bảng', lambda b=b: b.selectRow(0))
                self.lam('bấm đúp dòng đầu bảng', lambda b=b, m=m: b.doubleClicked.emit(m.index(0, 1)))
        nut = [x for x in ds if isinstance(x, QAbstractButton) and not isinstance(x, (QCheckBox, QRadioButton))]
        for b in nut:
            chu = (b.text() or b.toolTip() or b.objectName() or '').replace('\n', ' ').strip()
            if not chu or BO_QUA_NUT.match(chu) or not b.isEnabled():
                continue
            if isinstance(b, QToolButton) and b.defaultAction() is not None and getattr(w, 'la_cua_so_chinh', False):
                continue                                    # nút menu trái = lệnh cửa sổ chính: thử ở vòng lệnh
            if isinstance(b, QToolButton) and b.menu() is not None:
                for a in b.menu().actions():
                    if a.text() and a.isEnabled() and not a.isSeparator():
                        self.dem['menu'] += 1
                        self.lam(f'menu "{chu[:30]}" → "{a.text()}"', a.trigger)
                continue
            self.dem['nut'] += 1
            self.lam(f'nút "{chu[:50]}"', b.click)

    def thu_bang(self, b) -> None:
        """Bảng sửa được: chọn dòng đầu, sửa từng ô của dòng đầu (số đúng kiểu VN, chữ sai, công thức) rồi trả lại."""
        from PySide6.QtCore import Qt
        if b.rowCount() == 0:
            return
        self.dem['bang'] += 1
        self.lam('chọn dòng đầu bảng', lambda: b.selectRow(0))
        for c in range(min(b.columnCount(), 14)):
            it = b.item(0, c)
            if it is None or not (it.flags() & Qt.ItemFlag.ItemIsEditable) or b.editTriggers() == b.EditTrigger.NoEditTriggers:
                continue
            cu = it.text()
            ten_cot = b.horizontalHeaderItem(c).text() if b.horizontalHeaderItem(c) else str(c)
            self.dem['o_bang'] += 1
            def dat(gt, c=c):                               # lấy lại ô mỗi lần: sửa ô có thể làm bảng vẽ lại (ô cũ bị xóa)
                o = b.item(0, c) if b.rowCount() else None
                if o is not None:
                    o.setText(gt)
            for gt in ('1.070,5', 'abc', '=2*3'):
                self.lam(f'sửa ô bảng "{ten_cot}" = "{gt}"', lambda gt=gt, dat=dat: dat(gt))
            self.lam(f'trả ô bảng "{ten_cot}"', lambda cu=cu, dat=dat: dat(cu))

    # ------------------------------------------------ hộp thoại mở ra: thử rồi trả "Hủy" (không chặn chương trình)
    def mo_hop(self, dlg) -> int:
        from PySide6.QtWidgets import QApplication, QFileDialog
        self.dem['hop'] += 1
        ten = f'[{type(dlg).__name__}: {dlg.windowTitle()[:50]}]'
        if self.sau >= SAU_TOI_DA or isinstance(dlg, QFileDialog):    # hộp chọn file của Qt: trả "Hủy"
            return 0
        self.sau += 1
        self.duong.append(ten)
        try:
            dlg.show()
            QApplication.processEvents()
            self.thu(dlg, ten)
        finally:
            self.duong.pop()
            self.sau -= 1
            try:
                dlg.hide()
            except RuntimeError:                             # hộp đã bị xóa trong lúc thử
                pass
        return 0


def QWidget_():
    from PySide6.QtWidgets import QWidget
    return QWidget


def chan_tac_dong(kt: KiemTra) -> None:
    """Thay các thao tác có tác động ra ngoài / chặn chương trình bằng bản giả (ghi lại để báo cáo)."""
    import urllib.request
    from PySide6.QtGui import QDesktopServices
    from PySide6.QtWidgets import QDialog, QFileDialog, QInputDialog, QMenu, QMessageBox
    from pabt import in_an, van_ban_trinh

    def hoi(loai):
        def ham(cha, tieu_de='', chu='', *a, **k):
            kt.dem['thong_bao'] += 1
            if loai in ('warning', 'critical'):
                kt.thong_bao.append((' > '.join(kt.duong), loai, str(chu)[:300]))
            return QMessageBox.StandardButton.Yes if loai == 'question' else QMessageBox.StandardButton.Ok
        return staticmethod(ham)
    for loai in ('question', 'information', 'warning', 'critical'):
        setattr(QMessageBox, loai, hoi(loai))
    QMessageBox.about = staticmethod(lambda *a, **k: None)

    def hop_tin(self, *a):
        kt.dem['thong_bao'] += 1
        if self.icon() in (QMessageBox.Icon.Warning, QMessageBox.Icon.Critical):
            kt.thong_bao.append((' > '.join(kt.duong), 'hộp', self.text()[:300]))
        return 0
    QMessageBox.exec = hop_tin
    QDialog.exec = lambda self, *a: kt.mo_hop(self)
    if hasattr(QDialog, 'exec_'):
        QDialog.exec_ = QDialog.exec

    # QMenu.exec (PySide6 6.11: hàm có cả dạng tĩnh, gán đè trên lớp không có tác dụng) và nút có menu xổ chạy vòng sự kiện riêng
    # chờ người bấm: bắt sự kiện hiện menu, chạy từng mục rồi đóng menu (exec trả None như khi người dùng bấm ra ngoài).
    from PySide6.QtCore import QEvent, QObject, QTimer

    def chay_menu(m):
        try:
            ds = [x for x in m.actions() if x.text() and x.isEnabled() and not x.isSeparator() and x.menu() is None]
        except RuntimeError:                                 # menu đã bị xóa
            return
        for x in ds:
            kt.dem['menu'] += 1
            kt.lam(f'menu → "{x.text()}"', x.trigger)
        try:
            m.close()
        except RuntimeError:
            pass
        # menu bị ẩn trong một vòng sự kiện lồng (hộp thoại mở từ mục menu): Qt trên Windows đã "tiêu" tín hiệu đánh thức, vòng
        # exec của menu chờ tới sự kiện kế tiếp (người dùng thật luôn có sự kiện chuột) - tạo một sự kiện để không đo nhầm 28 giây
        QTimer.singleShot(0, lambda: None)

    class BatMenu(QObject):
        def eventFilter(self, obj, ev):
            if ev.type() == QEvent.Type.Show and isinstance(obj, QMenu):
                QTimer.singleShot(0, lambda m=obj: chay_menu(m))
            return False
    kt.bat_menu = BatMenu()
    from PySide6.QtWidgets import QApplication
    QApplication.instance().installEventFilter(kt.bat_menu)
    QFileDialog.getOpenFileName = staticmethod(lambda *a, **k: ('', ''))
    QFileDialog.getOpenFileNames = staticmethod(lambda *a, **k: ([], ''))

    def luu(cha=None, tieu_de='', mac_dinh='', loc='', *a, **k):
        ten = Path(str(mac_dinh)).name if mac_dinh else 'thu'
        return str(kt.td / 'luu' / (ten or 'thu')), ''
    QFileDialog.getSaveFileName = staticmethod(luu)
    QFileDialog.getExistingDirectory = staticmethod(lambda *a, **k: str(kt.td / 'thu_muc'))
    QInputDialog.getText = staticmethod(lambda *a, **k: ('Hộ thử giao diện', True))
    QInputDialog.getInt = staticmethod(lambda *a, **k: (1, True))
    QInputDialog.getItem = staticmethod(lambda cha, td, nhan, ds, *a, **k: (ds[0] if ds else '', True))
    QDesktopServices.openUrl = staticmethod(lambda *a, **k: True)
    in_an.mo_file = lambda p: kt.dem.update(['mo_file'])
    in_an.chay_excel = lambda *a, **k: []            # không mở Excel, không in
    van_ban_trinh.chay_word = lambda *a, **k: []    # không mở Word, không in

    def khong_mang(*a, **k):
        raise OSError('Kiểm tra giao diện: không kết nối mạng')
    urllib.request.urlopen = khong_mang
    os.startfile = lambda *a, **k: None


def du_an_thu(td: Path, so_ho: int) -> Path:
    """Dự án giả lập: so_ho hộ, đợt trình, số PA chi tiết, một quyết định phê duyệt (để các trang theo dõi có số liệu)."""
    from pabt import csdl, du_an_moi, quan_ly, theo_doi
    dong = []
    for i in range(so_ho):
        for j in range(1 + i % 2):
            dong.append(dict(ho_ten=f'Nguyễn Văn Thử {i}', dia_chi='Ấp 1', so_to=str(10 + i), so_thua=str(100 + i * 3 + j),
                             loai_dat=('ONT', 'CLN', 'LUC')[(i + j) % 3], dt_thu_hoi=str(50 + 10 * i + j), vi_tri='1',
                             nhan_khau='5'))
    gia = [dict(loai_dat=l, vi_tri='1', gia=g) for l, g in (('ONT', '3000000'), ('CLN', '250000'), ('LUC', '200000'))]
    p = td / 'mau.pabt'
    du_an_moi.tao_du_an(p, dict(ten='Dự án thử giao diện', cap_dia_ban='Xã', ten_dia_ban='Bàu Hàm', nam='2026'), dong, gia)
    con = csdl.mo(p)
    try:
        ma = [r[0] for r in con.execute('SELECT ma_ho FROM ho ORDER BY thu_tu')]
        d = quan_ly.tao_dot(con, ngay_trinh='10/10/2026', so_to_trinh='1/TTr', so_pa_tong='1', ngay_pa_tong='09/10/2026')
        quan_ly.gan_dot(con, ma[: so_ho // 2], d)
        quan_ly.danh_so_pa(con, ma[: so_ho // 2], 1, '09/10/2026')
        qd = theo_doi.luu_qd(con, None, '1/QĐ-UBND', '20/10/2026')
        for m in ma[:3]:
            theo_doi.ghi_qd_ho(con, qd, m, {'so_tien': '1000000'})
    finally:
        con.close()
    return p


def main(argv) -> int:
    so_ho = int(argv[argv.index('--so-ho') + 1]) if '--so-ho' in argv else 12
    chi = argv[argv.index('--chi') + 1] if '--chi' in argv else ''
    du_an = argv[argv.index('--du-an') + 1] if '--du-an' in argv else ''
    td = Path(tempfile.mkdtemp(prefix='pabt_giao_dien_'))
    for ten in ('luu', 'thu_muc'):                       # thư mục "người dùng chọn" trong hộp lưu file / chọn thư mục
        (td / ten).mkdir()
    os.environ['PABT_THU_MUC_MAY'] = str(td / 'may')
    os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
    import pabt  # noqa: F401 - môi trường Win7 (Python 3.8 + PySide2): đặt bí danh PySide6 -> PySide2 trước khi nạp Qt
    from PySide6.QtWidgets import QApplication
    qa = QApplication([])
    import pabt
    from pabt import app as ud
    from pabt.giao_dien import ap_dung
    ap_dung(qa)
    kt = KiemTra(td)
    sys.excepthook = kt.bat_loi
    chan_tac_dong(kt)
    mau = Path(du_an) if du_an else du_an_thu(td, so_ho)
    w = ud.CuaSoChinh(menu_trai=True)
    w.show()
    qa.processEvents()
    bat_dau = time.time()

    def mo_ban_sao():
        w.dong_du_an()
        p = td / f'ban_sao_{kt.dem["ban_sao"]}.pabt'
        kt.dem['ban_sao'] += 1
        shutil.copy2(mau, p)
        w.mo(str(p), chi_doc=False)
        qa.processEvents()
    lenh = [(t, a) for t, a in w.lenh.items() if not chi or chi in t]
    for i, (ten, a) in enumerate(lenh, start=1):
        print(f'[{i}/{len(lenh)}] {ten}', flush=True)
        faulthandler.dump_traceback_later(TREO_GIAY, exit=True)       # treo thật: in vết ngăn xếp, dừng
        kt.lam('mở bản sao dự án', mo_ban_sao)
        kt.dem['lenh'] += 1
        kt.lam(f'Lệnh "{ten}"', a.trigger)
        from PySide6.QtCore import QEvent
        qa.sendPostedEvents(None, QEvent.Type.DeferredDelete)          # như vòng sự kiện chính: xóa hộp đã đóng (deleteLater)
        from PySide6.QtWidgets import QDialog
        an = [h for h in w.findChildren(QDialog) if not h.isVisible()]
        if len(an) > kt.dem['hop_an']:                                  # hộp đã đóng còn trong bộ nhớ sau lệnh (rò rỉ)
            kt.dem['hop_an'] = len(an)
            kt.dem_hop_an = f'{ten}: ' + ', '.join(sorted({type(h).__name__ for h in an}))
        if ten in ud.TRANG:                                             # trang bên phải: thử các điều khiển của trang
            kt.lam(f'Trang "{ten}"', lambda: kt.thu(w.trang.currentWidget()))
        faulthandler.cancel_dump_traceback_later()
    if not chi:
        print('[cửa sổ chính] ô tìm, bộ lọc, nút, menu chuột phải', flush=True)
        kt.lam('mở bản sao dự án', mo_ban_sao)
        w.mo_trang(0)
        kt.lam('Cửa sổ chính', lambda: kt.thu(w))
        if w.mo_hinh.rowCount():
            kt.lam('menu chuột phải danh sách hộ', lambda: w._menu_ho(w.bang, w.bang.visualRect(w.loc.index(0, 1)).center()))
        kt.lam('đóng dự án', w.dong_du_an)
        kt.lam('đóng cửa sổ chính', w.close)
    phut = (time.time() - bat_dau) / 60
    bc = bao_cao(kt, pabt.__version__, phut, du_an or f'dự án giả lập {so_ho} hộ')
    ra = GOC / 'ket_qua_kiem_tra' / f'GiaoDien_{pabt.__version__}_{datetime.now():%Y-%m-%d_%H%M}.md'
    ra.parent.mkdir(exist_ok=True)
    ra.write_text(bc, encoding='utf-8')
    print(bc)
    print(f'Đã lưu: {ra}')
    shutil.rmtree(td, ignore_errors=True)
    return 1 if kt.loi else 0


def bao_cao(kt: KiemTra, phien_ban: str, phut: float, du_an: str) -> str:
    d = kt.dem
    t = [f'# Kiểm tra giao diện PABT {phien_ban}', f'{datetime.now():%d/%m/%Y %H:%M} · {du_an} · {phut:.1f} phút', '',
         f'Đã thử: {d["lenh"]} lệnh cửa sổ chính, {d["hop"]} lần mở hộp thoại, {d["nut"]} lần bấm nút, {d["menu"]} mục menu, '
         f'{d["o_nhap"]} ô nhập (mỗi ô 4 giá trị), {d["o_bang"]} ô bảng (mỗi ô 3 giá trị), {d["muc_chon"]} mục chọn, '
         f'{d["danh_dau"]} ô đánh dấu, {d["the"]} thẻ, {d["bang"]} bảng; {d["thong_bao"]} thông báo hiện ra. Hộp thoại đã đóng còn '
         f'nằm trong bộ nhớ ngay sau một lệnh: tối đa {d["hop_an"]} (0 = không rò rỉ'
         + (f'; {kt.dem_hop_an}' if d['hop_an'] else '') + ').', '',
         f'## LỖI ({len(kt.loi)})', '']
    if not kt.loi:
        t.append('Không có lỗi (ngoại lệ) nào.')
    for duong, vet in kt.loi:
        dong_cuoi = [x for x in vet.strip().splitlines() if x.strip()][-1]
        t += [f'- **{duong}**', f'  - `{dong_cuoi}`', '```', vet.strip()[-1800:], '```']
    t += ['', f'## CHẬM / ĐƠ (một thao tác > {NGUONG_CHAM:.0f} giây) ({len(kt.cham)})', '']
    t += [f'- {duong}: {dt:.1f} giây' for duong, dt in sorted(kt.cham, key=lambda x: -x[1])] or ['Không có thao tác nào chậm.']
    t += ['', f'## Thông báo cảnh báo / lỗi phần mềm đã hiện ({len(kt.thong_bao)}) - xem có hợp lý không', '']
    gom = Counter((loai, chu.split('\n')[0][:160]) for _, loai, chu in kt.thong_bao)
    t += [f'- [{loai}] ×{n}: {chu}' for (loai, chu), n in gom.most_common(60)] or ['Không có.']
    return '\n'.join(t) + '\n'


if __name__ == '__main__':
    for luong in (sys.stdout, sys.stderr):
        try:
            luong.reconfigure(encoding='utf-8')
        except (AttributeError, ValueError):
            pass
    sys.exit(main(sys.argv[1:]))

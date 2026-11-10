r"""Quét bố cục nút: mở mọi lệnh, hộp thoại, thẻ ở nhiều cỡ cửa sổ, báo nút đè nút / đè thanh thẻ, thanh thẻ thiếu chỗ, nút cắt chữ, nút thấp, nút sát nhau. Dữ liệu GIẢ LẬP.

  .venv\Scripts\python kiem_tra_bo_cuc.py <file_ra.tsv> [rong,cao ...]   (mặc định 1093,614 1536,864; 1093 = màn 1366 phóng 125%)

Offscreen mặc định không có phông (ký tự thành ô vuông, đo sai): công cụ đặt QT_QPA_FONTDIR tới phông Windows thật. Thanh thẻ thiếu chỗ có mũi tên cuộn thì chưa hẳn là lỗi;
nút chỉ biểu tượng ở menu trái thu gọn báo cắt chữ là cố ý. Chỉ đo nút và thanh thẻ, không đo nhãn, ô nhập; không vào hộp con mở từ nút trong hộp."""
from __future__ import annotations

import collections
import gc
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, os.getcwd())
import faulthandler
faulthandler.dump_traceback_later(1800, exit=True)      # không chờ vô hạn: in chồng gọi rồi thoát
RA = sys.argv[1]
CO = [tuple(int(x) for x in a.split(',')) for a in sys.argv[2:]] or [(1093, 614), (1536, 864)]
sys.argv = sys.argv[:1]
td = Path(tempfile.mkdtemp(prefix='qcl_'))
(td / 'luu').mkdir()
(td / 'thu_muc').mkdir()
os.environ['PABT_THU_MUC_MAY'] = str(td / 'may')
os.environ['QT_QPA_PLATFORM'] = 'offscreen'
if os.path.isdir(r'C:\Windows\Fonts'):
    os.environ.setdefault('QT_QPA_FONTDIR', r'C:\Windows\Fonts')
import pabt  # noqa
from PySide6.QtCore import QCoreApplication, QEvent, QPoint, QRect, Qt  # noqa
from PySide6.QtWidgets import QAbstractButton, QApplication, QDialog, QPushButton, QTabBar, QTabWidget, QToolButton, QWidget  # noqa
qa = QApplication([])
from pabt import app as ud  # noqa
from pabt.giao_dien import ap_dung  # noqa
ap_dung(qa)
import kiem_tra_giao_dien as ktgd  # noqa
kt = ktgd.KiemTra(td)
ktgd.chan_tac_dong(kt)
sys.excepthook = lambda *a: None
ghi = collections.OrderedDict()
da_thu = collections.Counter()


def bao(loai, man, chi_tiet):
    ghi.setdefault((loai, man, chi_tiet), 0)
    ghi[(loai, man, chi_tiet)] += 1


def nhan(w):
    t = ''
    if isinstance(w, QAbstractButton):
        t = w.text().replace('&&', '&').replace('&', '')
    elif isinstance(w, QTabBar):
        t = '<thanh thẻ: ' + ' | '.join(w.tabText(i).replace('&', '') for i in range(w.count()))[:50] + '>'
    return f'{type(w).__name__}"{t[:34]}"' + (f' tip="{w.toolTip()[:24]}"' if not t and w.toolTip() else '')


def hien(w, goc):
    return w.isVisibleTo(goc) and w.width() > 0 and w.height() > 0


def toan_cuc(w):
    return QRect(w.mapToGlobal(QPoint(0, 0)), w.size())


def trong_khung_cuon(w, goc):
    """Bỏ widget trong vùng cuộn đã bị cắt: chỉ xét phần thật sự nhìn thấy."""
    r = toan_cuc(w)
    p = w.parentWidget()
    while p is not None and p is not goc:
        r = r & toan_cuc(p)
        p = p.parentWidget()
    return r


def xet(goc, man):
    nut = [w for w in goc.findChildren(QWidget) if isinstance(w, (QPushButton, QToolButton)) and hien(w, goc) and w.window() is goc.window() and type(w.parentWidget()).__name__ not in ('QTabBar', 'QScrollBar')
           and not (isinstance(w, QToolButton) and isinstance(w.parentWidget(), QTabBar))]
    the = [w for w in goc.findChildren(QTabBar) if hien(w, goc) and w.window() is goc.window()]
    ds = [(w, trong_khung_cuon(w, goc)) for w in nut]
    ds = [(w, r) for w, r in ds if r.isValid() and r.width() > 0 and r.height() > 0]
    tb = []
    for b in the:
        # vùng thẻ THẬT (thẻ cuối) so với nút: Qt cắt thanh thẻ theo corner, vùng thẻ bị cuộn: phát hiện bằng nút mũi tên hiện ra
        vung = trong_khung_cuon(b, goc)
        rong_can = sum(b.tabRect(i).width() for i in range(b.count()))
        if rong_can > b.width() + 2 and not b.usesScrollButtons():     # có nút cuộn: thẻ nào cũng tới được
            bao('THANH_THE_THIEU_CHO', man, f'{nhan(b)} cần {rong_can}, có {b.width()}')
        tb.append((b, vung))
    for i, (a, ra) in enumerate(ds):
        for b, rb in ds[i + 1:]:
            if a.isAncestorOf(b) or b.isAncestorOf(a):
                continue
            g = ra & rb
            if g.isValid() and g.width() > 1 and g.height() > 1:
                bao('NUT_DE_NUT', man, f'{nhan(a)} x {nhan(b)} ({g.width()}x{g.height()})')
            elif ra.top() < rb.bottom() and rb.top() < ra.bottom():
                kc = max(ra.left(), rb.left()) - min(ra.right(), rb.right())
                if 0 <= kc < 3 and a.parentWidget() is b.parentWidget():
                    bao('SAT_NHAU', man, f'{nhan(a)} | {nhan(b)} cách {kc}px')
        for b, rb in tb:
            if b.isAncestorOf(a):
                continue
            g = ra & rb
            if g.isValid() and g.width() > 1 and g.height() > 1:
                bao('NUT_DE_THE', man, f'{nhan(a)} x {nhan(b)} ({g.width()}x{g.height()})')
        if isinstance(a, (QPushButton, QToolButton)):
            t = a.text().replace('&&', 'x').replace('&', '')
            chi_bieu_tuong = isinstance(a, QToolButton) and a.toolButtonStyle() == Qt.ToolButtonStyle.ToolButtonIconOnly
            if t and '\n' not in t and not chi_bieu_tuong:      # nút chỉ biểu tượng (menu trái thu gọn): chữ ẩn là cố ý
                can = a.fontMetrics().horizontalAdvance(t) + (a.iconSize().width() + 4 if not a.icon().isNull() else 0) + 12
                if QPushButton.menu(a) if isinstance(a,QPushButton) else QToolButton.menu(a):
                    can += 14
                if a.width() < can - 2:
                    bao('CAT_CHU', man, f'{nhan(a)} rộng {a.width()}, chữ cần {can}')
            if a.height() < 22 and a.isEnabled() and a.objectName() != 'lineedit_clear_button' and a.toolTip() != 'Xóa chữ đã gõ':   # nút xóa nằm trong ô nhập
                bao('NUT_THAP', man, f'{nhan(a)} cao {a.height()}')
            cha = a.parentWidget()
            if cha is not None and not type(cha).__name__.startswith('QAbstractScroll') and cha.width() > 0:
                g = a.geometry()
                if (g.right() > cha.width() + 2 or g.left() < -2) and type(cha).__name__ not in ('QWidget', ) or g.right() > cha.width() + 40:
                    if 'scroll' not in type(cha).__name__.lower():
                        bao('RA_NGOAI', man, f'{nhan(a)} x={g.left()}..{g.right()} cha rộng {cha.width()}')
    return len(ds)


def duyet(goc, man):
    tong = xet(goc, man)
    da_the = set()
    for t in goc.findChildren(QTabWidget):
        if not t.isVisibleTo(goc) or id(t) in da_the:
            continue
        da_the.add(id(t))
        cu = t.currentIndex()
        for i in range(t.count()):
            if i == cu or not t.isTabEnabled(i):
                continue
            try:
                t.setCurrentIndex(i)
                qa.processEvents()
                tong += xet(goc, f'{man} > thẻ {t.tabText(i).replace("&", "")[:22]}')
            except RuntimeError:
                break
        try:
            t.setCurrentIndex(cu)
        except RuntimeError:
            pass
    return tong


CO_HIEN = [CO[0]]


def mo_hop(dlg):
    ten = type(dlg).__name__
    if ten in ('QFileDialog', 'QMessageBox', 'QColorDialog', 'QInputDialog', 'QProgressDialog'):
        return 0
    try:
        dlg.show()
        qa.processEvents()
        rong, cao = CO_HIEN[0]
        if not dlg.parentWidget() or dlg.isWindow():
            dlg.resize(min(dlg.width(), rong - 20), min(dlg.height(), cao - 60))
            qa.processEvents()
        da_thu[ten] += 1
        duyet(dlg, f'[{ten}@{rong}]')
    finally:
        try:
            dlg.hide()
        except RuntimeError:
            pass
    return 0


kt.mo_hop = mo_hop
kt.thu = lambda *a, **k: None
from PySide6.QtWidgets import QDialog as _D  # noqa
_D.exec = lambda self, *a: mo_hop(self)
if hasattr(_D, 'exec_'):
    _D.exec_ = _D.exec
mau = ktgd.du_an_thu(td, 12)
w = ud.CuaSoChinh(menu_trai=True)
w.show()
qa.processEvents()
w.mo(str(mau), chi_doc=False)
qa.processEvents()
lenh = [(t, a) for t, a in w.lenh.items() if t not in ('Thoát', 'Đóng dự án', 'Xóa dự án…', 'Mở dự án…', 'Dự án mới…')]
for rong, cao in CO:
    CO_HIEN[0] = (rong, cao)
    w.resize(rong, cao)
    qa.processEvents()
    for ten, a in lenh:
        try:
            if w.con is None:
                w.mo(str(mau), chi_doc=False)
            a.trigger()
            for _ in range(3):
                qa.processEvents()
            duyet(w, f'CuaSoChinh@{rong}x{cao} / {ten}')
            for h in [h for h in w.findChildren(QDialog) if h.isVisible() and h.isWindow()]:
                duyet(h, f'[{type(h).__name__}@{rong}]')
                h.close()
            w.mo_trang(0)
            qa.processEvents()
        except Exception as e:  # noqa
            bao('LOI_QUET', ten, f'{type(e).__name__}: {str(e)[:70]}')
    QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    gc.collect()
dem = collections.Counter(k[0] for k in ghi)
with open(RA, 'w', encoding='utf-8') as g:
    g.write(f'hop da quet {dict(da_thu)}\n{dict(dem)}\n')
    for (l, m, c) in sorted(ghi):
        g.write(f'{l}\t{m}\t{c}\n')
print('so loai', dict(dem), 'so hop', len(da_thu), flush=True)
sys.stdout.flush()
try:                                                    # os._exit vẫn chạy DLL_PROCESS_DETACH của Qt: có lúc sập mã 139 sau khi đã ghi xong kết quả
    import ctypes
    import ctypes.wintypes as _wt
    ctypes.windll.kernel32.TerminateProcess(_wt.HANDLE(-1), 0)
finally:
    os._exit(0)

r"""Chụp ảnh toàn bộ giao diện (cửa sổ chính, mọi lệnh / hộp thoại, mọi thẻ) + thống kê chữ nút / menu / thẻ dài. Dữ liệu GIẢ LẬP.

  .venv\Scripts\python chup_giao_dien.py <thư_mục_ra> [rong,cao] [sang|toi]
"""
from __future__ import annotations

import collections
import gc
import os
import re
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, os.getcwd())
import faulthandler
faulthandler.dump_traceback_later(1500, exit=True)
RA = Path(sys.argv[1])
CO = tuple(int(x) for x in (sys.argv[2] if len(sys.argv) > 2 else '1536,864').split(','))
TONG = sys.argv[3] if len(sys.argv) > 3 else 'sang'
sys.argv = sys.argv[:1]
RA.mkdir(parents=True, exist_ok=True)
td = Path(tempfile.mkdtemp(prefix='chup_'))
(td / 'luu').mkdir()
(td / 'thu_muc').mkdir()
os.environ['PABT_THU_MUC_MAY'] = str(td / 'may')
os.environ['QT_QPA_PLATFORM'] = 'offscreen'
if os.path.isdir(r'C:\Windows\Fonts'):
    os.environ.setdefault('QT_QPA_FONTDIR', r'C:\Windows\Fonts')
import pabt  # noqa
from PySide6.QtCore import QCoreApplication, QEvent  # noqa
from PySide6.QtWidgets import QAbstractButton, QApplication, QDialog, QMenu, QTabBar, QTabWidget  # noqa
qa = QApplication([])
from pabt import app as ud  # noqa
from pabt import giao_dien as gd  # noqa
gd.ap_dung(qa)
import kiem_tra_giao_dien as ktgd  # noqa
kt = ktgd.KiemTra(td)
ktgd.chan_tac_dong(kt)
sys.excepthook = lambda *a: None
if TONG != 'sang':
    gd.dat_tong_nen(TONG)
    qa.processEvents()

soAnh = [0]
chu_dai = collections.OrderedDict()      # (loai, chữ) -> (độ dài, màn)


def ten_tep(s: str) -> str:
    s = re.sub(r'[^0-9A-Za-z_]+', '_', s.encode('ascii', 'ignore').decode() or 'x')
    return s[:60].strip('_') or 'x'


def chup(w, man: str):
    soAnh[0] += 1
    try:
        w.grab().save(str(RA / f'{TONG}_{soAnh[0]:03d}_{ten_tep(man)}.png'))
    except Exception:  # noqa
        pass


def thu_chu(goc, man):
    for b in goc.findChildren(QAbstractButton):
        if b.isVisibleTo(goc):
            t = b.text().replace('&&', '&').replace('&', '').replace('\n', ' ')
            if len(t) >= 22:
                chu_dai[('nut', t)] = (len(t), man)
    for tb in goc.findChildren(QTabBar):
        for i in range(tb.count()):
            t = tb.tabText(i).replace('&', '')
            if len(t) >= 22:
                chu_dai[('the', t)] = (len(t), man)
    for m in goc.findChildren(QMenu):
        for a in m.actions():
            t = a.text().replace('&', '')
            if len(t) >= 34:
                chu_dai[('menu', t)] = (len(t), man)


def duyet(goc, man):
    chup(goc, man)
    thu_chu(goc, man)
    da = set()
    for t in goc.findChildren(QTabWidget):
        if not t.isVisibleTo(goc) or id(t) in da:
            continue
        da.add(id(t))
        cu = t.currentIndex()
        for i in range(t.count()):
            if i == cu or not t.isTabEnabled(i):
                continue
            try:
                t.setCurrentIndex(i)
                qa.processEvents()
                chup(goc, f'{man}_the_{t.tabText(i)}')
                thu_chu(goc, f'{man} > {t.tabText(i)}')
            except RuntimeError:
                break
        try:
            t.setCurrentIndex(cu)
        except RuntimeError:
            pass


def mo_hop(dlg):
    ten = type(dlg).__name__
    if ten in ('QFileDialog', 'QMessageBox', 'QColorDialog', 'QInputDialog', 'QProgressDialog'):
        return 0
    try:
        dlg.show()
        qa.processEvents()
        if not dlg.parentWidget() or dlg.isWindow():
            dlg.resize(min(dlg.width(), CO[0] - 20), min(dlg.height(), CO[1] - 60))
            qa.processEvents()
        duyet(dlg, f'hop_{ten}')
    finally:
        try:
            dlg.hide()
        except RuntimeError:
            pass
    return 0


kt.mo_hop = mo_hop
kt.thu = lambda *a, **k: None
QDialog.exec = lambda self, *a: mo_hop(self)
if hasattr(QDialog, 'exec_'):
    QDialog.exec_ = QDialog.exec
mau = ktgd.du_an_thu(td, 12)
w = ud.CuaSoChinh(menu_trai=True)
w.resize(*CO)
w.show()
qa.processEvents()
chup(w, 'chua_mo_du_an')
w.mo(str(mau), chi_doc=False)
qa.processEvents()
chup(w, 'cua_so_chinh')
thu_chu(w, 'cua_so_chinh')
# menu của thanh menu (nếu có)
try:
    for a in w.menuBar().actions():
        m = a.menu()
        if m is not None:
            thu_chu(m.parentWidget() or w, 'thanh_menu')
            for x in m.actions():
                t = x.text().replace('&', '')
                if len(t) >= 34:
                    chu_dai[('menu', t)] = (len(t), f'menu {a.text()}')
except Exception:  # noqa
    pass
lenh = [(t, a) for t, a in w.lenh.items() if t not in ('Thoát', 'Đóng dự án', 'Xóa dự án…', 'Mở dự án…', 'Dự án mới…')]
for ten, a in lenh:
    try:
        if w.con is None:
            w.mo(str(mau), chi_doc=False)
        a.trigger()
        for _ in range(3):
            qa.processEvents()
        duyet(w, f'lenh_{ten}')
        for h in [h for h in w.findChildren(QDialog) if h.isVisible() and h.isWindow()]:
            duyet(h, f'cuaso_{ten}_{type(h).__name__}')
            h.close()
        w.mo_trang(0)
        qa.processEvents()
    except Exception as e:  # noqa
        chu_dai[('loi', f'{ten}: {type(e).__name__} {str(e)[:60]}')] = (0, 'chup')
    QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    gc.collect()
with open(RA / f'chu_dai_{TONG}.tsv', 'w', encoding='utf-8') as g:
    g.write('loai\tdo_dai\tchu\tman\n')
    for (l, t), (n, m) in sorted(chu_dai.items(), key=lambda x: -x[1][0]):
        g.write(f'{l}\t{n}\t{t}\t{m}\n')
print('anh', soAnh[0], 'chu dai', len(chu_dai), flush=True)
try:
    import ctypes
    import ctypes.wintypes as _wt
    ctypes.windll.kernel32.TerminateProcess(_wt.HANDLE(-1), 0)
finally:
    os._exit(0)

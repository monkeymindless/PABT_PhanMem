r"""Kiểm kê LỆNH của PABT (đợt kiểm toán 16/10/2026): mọi QAction của cửa sổ chính (`CuaSoChinh.lenh`), nút bấm / nút công cụ /
phím tắt của cửa sổ chính và các trang nhúng (Lập phương án hộ, Niêm yết, Đơn giá, Dự toán, các trang menu trái) -> 4 nhóm:

  1. LỆNH ẨN     QAction không đặt ở menu trái / thanh menu / nút / menu chuột phải (không có đường bấm); widget con của cửa sổ chính
                 không nằm trong bố cục nào mà vẫn hiện (chiếm vùng bấm - lỗi "Tệp tin" 0.9.68).
  2. LỆNH LIỆT   QAction / nút không nối tín hiệu (triggered / clicked / toggled... = 0 receiver, không menu, không defaultAction);
                 phím tắt trùng nhau trong cùng cửa sổ (Qt báo "Ambiguous shortcut", không chạy lệnh nào); lệnh cần dự án bật / tắt
                 sai theo trạng thái (chưa mở dự án / mở / chỉ xem).
  3. LỆNH DƯ     lệnh vừa ở menu trái vừa ở thanh menu (nguyên tắc mỗi lệnh một chỗ, 0.9.66).
  4. (LỆNH LỖI chạy bằng kiem_tra_giao_dien.py --trang-thai tat_ca: bấm mọi lệnh ở 4 trạng thái biên.)

  .venv\Scripts\python kiem_toan_lenh.py      -> ket_qua_kiem_tra\KiemToanLenh_<phiên bản>_<giờ>.md ; mã thoát 1 khi còn vấn đề
"""
from __future__ import annotations

import inspect
import os
import re
import sys
import tempfile
from collections import defaultdict
from datetime import datetime
from pathlib import Path

GOC = Path(__file__).resolve().parent
sys.path.insert(0, str(GOC))

# QAction chỉ có phím tắt (gắn vào cửa sổ bằng addAction, không cần chỗ bấm) - giữ có chủ đích
CHI_PHIM_TAT = re.compile(r'^(Trang \d|Ctrl\+)')
SIGNAL_NUT = ('clicked(bool)', 'clicked()', 'toggled(bool)', 'pressed()', 'released()')


def _so_nhan(obj, ds) -> int:
    from PySide6.QtCore import SIGNAL
    n = 0
    for s in ds:
        try:
            n += obj.receivers(SIGNAL(s))
        except (RuntimeError, TypeError):
            pass
    return n


def _cho_dat(a) -> list:
    """Các widget / menu đang chứa QAction (Qt6: associatedObjects, Qt5: associatedWidgets)."""
    ham = getattr(a, 'associatedObjects', None) or getattr(a, 'associatedWidgets')
    try:
        return list(ham())
    except RuntimeError:
        return []


def _loai_cho(o, w) -> str:
    from PySide6.QtWidgets import QMenu, QMenuBar, QToolButton
    if o is w:
        return 'phím tắt cửa sổ'
    if isinstance(o, QMenu):
        p = o
        while isinstance(p, QMenu) and p.parent() is not None and isinstance(p.parent(), QMenu):
            p = p.parent()
        return 'thanh menu' if isinstance(p.parent(), QMenuBar) or p.menuAction() in w.menuBar().actions() else 'menu'
    if isinstance(o, QMenuBar):
        return 'thanh menu'
    if isinstance(o, QToolButton) and getattr(w, 'khung_menu', None) is not None and w.khung_menu.isAncestorOf(o):
        return 'menu trái'
    return 'nút'


def _trong_bo_cuc(x) -> bool:
    p = x.parentWidget()
    lo = p.layout() if p is not None else None
    if lo is None:
        return False

    def tim(l):
        for i in range(l.count()):
            it = l.itemAt(i)
            if it.widget() is x:
                return True
            if it.layout() is not None and tim(it.layout()):
                return True
        return False
    return tim(lo)


def kiem_ke(w, mo_them) -> dict:
    """w: CuaSoChinh đã mở dự án; mo_them(): mở các trang nhúng để có đủ widget. Trả {nhóm: [dòng báo cáo]}."""
    from PySide6.QtGui import QShortcut
    from PySide6.QtWidgets import (QAbstractButton, QApplication, QDialogButtonBox, QMainWindow, QMenu, QScrollBar,
                                   QStackedWidget, QTabBar, QTabWidget, QToolButton, QWidget)
    from pabt import app as ud
    mo_them()
    QApplication.processEvents()
    kq = defaultdict(list)
    # chuột phải danh sách hộ: lệnh lấy từ self.lenh[...] trong mã _menu_ho (menu dựng lúc bấm)
    src = inspect.getsource(ud.CuaSoChinh._menu_ho)
    chuot_phai = set(re.findall(r"self\.lenh\['([^']+)'\]", src))
    # ---- QAction của cửa sổ chính
    for ten, a in w.lenh.items():
        cho = {_loai_cho(o, w) for o in _cho_dat(a)}
        if ten in chuot_phai:
            cho.add('chuột phải')
        if _so_nhan(a, ('triggered(bool)', 'triggered()', 'toggled(bool)')) == 0 and a.menu() is None:
            kq['liet'].append((f'QAction "{ten}"', 'app.py', 'không nối triggered (bấm không làm gì)'))
        co_cho = cho - {'phím tắt cửa sổ'}
        if not co_cho and not CHI_PHIM_TAT.match(ten):
            kq['an'].append((f'QAction "{ten}"', 'app.py', 'không có ở menu trái / thanh menu / nút / chuột phải'))
        if {'menu trái', 'thanh menu'} <= cho:
            kq['du'].append((f'QAction "{ten}"', 'app.py', 'vừa ở menu trái vừa ở thanh menu'))
        kq['bang_lenh'].append((ten, ', '.join(sorted(cho)) or '-', 'bật' if a.isEnabled() else 'tắt'))
    # ---- nút không nối tín hiệu (cửa sổ chính + trang nhúng)
    goc = [w] + [w.khung_tab.stack_phu.widget(i) for i in range(w.khung_tab.stack_phu.count())]
    da = set()
    for g in goc:
        for b in g.findChildren(QAbstractButton):
            if id(b) in da or b.objectName().startswith('qt_'):
                continue
            da.add(id(b))
            p = b.parentWidget()
            if isinstance(p, (QTabBar, QScrollBar, QDialogButtonBox)) or (p is not None and isinstance(p.parentWidget(), QTabBar)):
                continue                                    # nút nội bộ của Qt (mũi tên thanh thẻ, nút hộp chuẩn)
            if _menu_nut(b) is not None or (isinstance(b, QToolButton) and QToolButton.defaultAction(b) is not None):
                continue
            if b.isCheckable() and _so_nhan(b, SIGNAL_NUT) == 0:
                # ô đánh dấu / nút bật tắt có thể chỉ được ĐỌC trạng thái (isChecked) - không phải lệnh: bỏ qua
                continue
            if not b.isCheckable() and _so_nhan(b, SIGNAL_NUT) == 0:
                chu = (b.text() or b.toolTip() or b.objectName() or type(b).__name__).replace('\n', ' ')[:60]
                kq['liet'].append((f'nút "{chu}"', f'{type(g).__name__} ({type(p).__name__ if p else "-"})',
                                   'nút không nối tín hiệu clicked'))
    # ---- widget con của cửa sổ chính không nằm trong bố cục mà vẫn hiện (che vùng bấm)
    for x in w.findChildren(QWidget):
        if x.parentWidget() is not w or isinstance(x, (QMenu, QMainWindow)) or x.isWindow():
            continue
        if x in (w.centralWidget(), w.statusBar(), w.menuWidget()) or _trong_bo_cuc(x):
            continue
        if x.isVisible() and not x.testAttribute(_wa_trong_suot()):
            kq['an'].append((f'widget {type(x).__name__} "{x.objectName()}"', f'{x.geometry().getRect()}',
                             'con của cửa sổ chính, không trong bố cục, đang hiện - chiếm vùng bấm'))
        else:
            kq['an_co_chu_dich'].append((f'{type(x).__name__} "{x.objectName()}"', 'ẩn / trong suốt với chuột'))
    # ---- phím tắt trùng trong cùng cửa sổ (QShortcut + QAction.shortcut)
    phim = defaultdict(list)
    da_phim = set()
    for s in w.findChildren(QShortcut):                 # cửa sổ chính chứa sẵn các trang nhúng (một lần, không đếm trùng)
        k = s.key().toString()
        if k and s.isEnabled() and id(s) not in da_phim:
            da_phim.add(id(s))
            phim[k].append((f'QShortcut ({type(s.parent()).__name__})', s.context(), s))
    for a in w.findChildren(type(next(iter(w.lenh.values())))):
        for k in (x.toString() for x in a.shortcuts()):
            if k and a.isEnabled() and id(a) not in da_phim:
                da_phim.add(id(a))
                phim[k].append((f'QAction "{a.text()}"', a.shortcutContext(), a))
    from PySide6.QtCore import Qt
    for k, ds in sorted(phim.items()):
        cua_so = [d for d in ds if d[1] in (Qt.ShortcutContext.WindowShortcut, Qt.ShortcutContext.ApplicationShortcut)]
        if len(cua_so) > 1:
            kq['phim_trung'].append((k, '; '.join(d[0] for d in cua_so)))
        kq['bang_phim'].append((k, '; '.join(f'{d[0]} [{_ten_ngu_canh(d[1])}]' for d in ds)))
    del QStackedWidget, QTabWidget
    return kq


def _menu_nut(b):
    """Menu xổ của nút (gọi hàm của LỚP Qt: lớp con có thể đặt thuộc tính trùng tên 'menu', vd NutHoSoScan.menu)."""
    from PySide6.QtWidgets import QPushButton, QToolButton
    for lop in (QPushButton, QToolButton):
        if isinstance(b, lop):
            return lop.menu(b)
    return None


def _wa_trong_suot():
    from PySide6.QtCore import Qt
    return Qt.WidgetAttribute.WA_TransparentForMouseEvents


def _ten_ngu_canh(c) -> str:
    from PySide6.QtCore import Qt
    return {Qt.ShortcutContext.WidgetShortcut: 'ô', Qt.ShortcutContext.WidgetWithChildrenShortcut: 'khung',
            Qt.ShortcutContext.WindowShortcut: 'cửa sổ', Qt.ShortcutContext.ApplicationShortcut: 'ứng dụng'}.get(c, str(c))


def kiem_trang_thai(w, p) -> list:
    """Lệnh cần dự án (LENH_CAN_DU_AN) bật / tắt đúng: chưa mở -> tắt; mở ghi được -> bật; chỉ xem -> Lập phương án tắt."""
    from pabt import app as ud
    loi = []
    w.dong_du_an()
    for t in ud.LENH_CAN_DU_AN:
        if t in w.lenh and w.lenh[t].isEnabled():
            loi.append((t, 'chưa mở dự án mà vẫn bật'))
    w.mo(str(p), chi_doc=False)
    for t in ud.LENH_CAN_DU_AN:
        if t in w.lenh and not w.lenh[t].isEnabled():
            loi.append((t, 'đã mở dự án (ghi được) mà vẫn tắt'))
    w.dong_du_an()
    w.mo(str(p), chi_doc=True)
    if w.lenh['Lập phương án hộ…'].isEnabled():
        loi.append(('Lập phương án hộ…', 'chỉ xem mà vẫn bật'))
    w.dong_du_an()
    w.mo(str(p), chi_doc=False)
    for t in ud.LENH_CAN_DU_AN:
        if t in w.lenh and not w.lenh[t].isEnabled():
            loi.append((t, 'mở lại (ghi được) sau chỉ xem mà vẫn tắt'))
    return loi


def main() -> int:
    td = Path(tempfile.mkdtemp(prefix='pabt_kiem_toan_lenh_'))
    os.environ['PABT_THU_MUC_MAY'] = str(td / 'may')
    os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
    import pabt
    from PySide6.QtWidgets import QApplication
    qa = QApplication([])
    from pabt import app as ud
    from pabt.giao_dien import ap_dung
    import kiem_tra_giao_dien as kgd
    ap_dung(qa)
    kt = kgd.KiemTra(td)
    kgd.chan_tac_dong(kt)                               # hộp thoại / file / mạng giả - không chặn chương trình
    p = kgd.du_an_thu(td, 6)
    w = ud.CuaSoChinh(menu_trai=True)
    w.show()
    w.mo(str(p))
    qa.processEvents()

    def mo_them():
        w.mo_lap_pa()
        w.lenh['Dự thảo PABT…'].trigger()
        for i in range(len(ud.TRANG)):
            w.mo_trang(i)
        w.lenh['Lập phương án hộ…'].trigger()
    kq = kiem_ke(w, mo_them)
    trang_thai = kiem_trang_thai(w, p)
    for k in [k for k in w.khung_tab.khoa if isinstance(k, tuple)]:
        w.khung_tab.widget[k].bo_thay_doi()
    w.close()
    dong = [f'# Kiểm kê lệnh PABT {pabt.__version__}', f'{datetime.now():%d/%m/%Y %H:%M}', '']
    for nhom, tieu_de in (('an', '1. LỆNH ẨN (không có chỗ bấm / widget che vùng bấm)'),
                          ('liet', '2. LỆNH LIỆT (không nối tín hiệu)'), ('phim_trung', '2b. PHÍM TẮT TRÙNG CÙNG CỬA SỔ'),
                          ('du', '3. LỆNH DƯ (menu trái + thanh menu)')):
        dong.append(f'## {tieu_de} ({len(kq[nhom])})')
        dong += [f'- ' + ' · '.join(str(x) for x in d) for d in kq[nhom]] or ['Không có.']
        dong.append('')
    dong.append(f'## 2c. BẬT / TẮT LỆNH THEO TRẠNG THÁI DỰ ÁN ({len(trang_thai)})')
    dong += [f'- {t}: {ly_do}' for t, ly_do in trang_thai] or ['Đúng ở cả 4 lần (chưa mở / mở / chỉ xem / mở lại).']
    dong += ['', f'## Widget ẩn có chủ đích ({len(kq["an_co_chu_dich"])})']
    dong += [f'- ' + ' · '.join(d) for d in kq['an_co_chu_dich']]
    dong += ['', f'## Bảng lệnh cửa sổ chính ({len(kq["bang_lenh"])})', '', '| Lệnh | Đặt ở | Trạng thái |', '|---|---|---|']
    dong += [f'| {a} | {b} | {c} |' for a, b, c in kq['bang_lenh']]
    dong += ['', f'## Phím tắt ({len(kq["bang_phim"])})', '']
    dong += [f'- `{k}`: {v}' for k, v in kq['bang_phim']]
    bc = '\n'.join(dong) + '\n'
    ra = GOC / 'ket_qua_kiem_tra' / f'KiemToanLenh_{pabt.__version__}_{datetime.now():%Y-%m-%d_%H%M}.md'
    ra.parent.mkdir(exist_ok=True)
    ra.write_text(bc, encoding='utf-8')
    print(bc)
    print(f'Đã lưu: {ra}')
    van_de = len(kq['an']) + len(kq['liet']) + len(kq['phim_trung']) + len(kq['du']) + len(trang_thai)
    return 1 if van_de else 0


if __name__ == '__main__':
    sys.exit(main())

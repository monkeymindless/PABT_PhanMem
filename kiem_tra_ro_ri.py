"""Quét rò rỉ bộ nhớ: mở / đóng MỖI lệnh của cửa sổ chính nhiều vòng, đếm widget + bộ nhớ. Dữ liệu GIẢ LẬP, không đụng dự án thật.

  .venv\\Scripts\\python kiem_tra_ro_ri.py <file_ra.tsv> [so_vong]

Nghi rò rỉ = còn tăng giữa vòng 2 và vòng cuối. BỘ NHỚ TĂNG CHƯA CHẮC LÀ RÒ RỈ: bộ đệm có giới hạn cũng tăng rồi chững (bảng giá đất NQ 28 tới ~16 MB), nên
lệnh bị nêu phải chạy thêm nhiều vòng xem có chững không. Chỉ mở rồi đóng lệnh ở cửa sổ chính, KHÔNG đi vào hộp con mở từ nút trong hộp."""
from __future__ import annotations

import collections
import ctypes
import ctypes.wintypes as wt
import faulthandler
import gc
import os
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, os.getcwd())
RA = sys.argv[1]
VONG = int(sys.argv[2]) if len(sys.argv) > 2 else 6
sys.argv = sys.argv[:1]
td = Path(tempfile.mkdtemp(prefix='qrr_'))
(td / 'luu').mkdir()
(td / 'thu_muc').mkdir()
os.environ['PABT_THU_MUC_MAY'] = str(td / 'may')
os.environ['QT_QPA_PLATFORM'] = 'offscreen'
import pabt  # noqa
from PySide6.QtCore import QCoreApplication, QEvent  # noqa
from PySide6.QtWidgets import QApplication, QDialog  # noqa
qa = QApplication([])
from pabt import app as ud  # noqa
from pabt.giao_dien import ap_dung  # noqa
ap_dung(qa)
import kiem_tra_giao_dien as ktgd  # noqa
kt = ktgd.KiemTra(td)
ktgd.chan_tac_dong(kt)
kt.thu = lambda *a, **k: None              # chỉ mở rồi đóng, không bấm nút: đo vòng đời hộp thoại, không đo tác dụng của nút
sys.excepthook = lambda *a: print('LOI', a[1], flush=True)


class PMC(ctypes.Structure):
    _fields_ = [('cb', wt.DWORD), ('PageFaultCount', wt.DWORD), ('PeakWorkingSetSize', ctypes.c_size_t),
                ('WorkingSetSize', ctypes.c_size_t), ('QuotaPeakPagedPoolUsage', ctypes.c_size_t),
                ('QuotaPagedPoolUsage', ctypes.c_size_t), ('QuotaPeakNonPagedPoolUsage', ctypes.c_size_t),
                ('QuotaNonPagedPoolUsage', ctypes.c_size_t), ('PagefileUsage', ctypes.c_size_t),
                ('PeakPagefileUsage', ctypes.c_size_t), ('PrivateUsage', ctypes.c_size_t)]


k32 = ctypes.WinDLL('kernel32')
psapi = ctypes.WinDLL('psapi')
k32.GetCurrentProcess.restype = wt.HANDLE
psapi.GetProcessMemoryInfo.argtypes = [wt.HANDLE, ctypes.c_void_p, wt.DWORD]


def kb():
    p = PMC()
    p.cb = ctypes.sizeof(PMC)
    psapi.GetProcessMemoryInfo(k32.GetCurrentProcess(), ctypes.byref(p), p.cb)
    return p.PrivateUsage // 1024


def don(w):
    for _ in range(3):
        qa.processEvents()
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    for h in [h for h in w.findChildren(QDialog) if h.isVisible() and not h.isModal()]:
        h.close()
    w.don_hop_da_dong()
    for _ in range(2):
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
        qa.processEvents()
    gc.collect()


def anh():
    cap_cao = collections.Counter(type(x).__name__ for x in qa.topLevelWidgets())
    return sum(cap_cao.values()), len(qa.allWidgets()), kb(), cap_cao


mau = ktgd.du_an_thu(td, 12)
w = ud.CuaSoChinh(menu_trai=True)
w.show()
qa.processEvents()
w.mo(str(mau), chi_doc=False)
don(w)
t_cho = time.time() + 2.2                  # việc hẹn giờ một lần sau khi mở dự án
while time.time() < t_cho:
    qa.processEvents()
    time.sleep(0.02)
lenh = [(t, a) for t, a in w.lenh.items() if t not in ('Thoát', 'Đóng dự án', 'Xóa dự án…', 'Mở dự án…', 'Dự án mới…')]
dong = []
ro = []
g = open(RA, 'w', encoding='utf-8', buffering=1)
for ten, a in lenh:
    faulthandler.dump_traceback_later(150, exit=True)
    mau_do = []
    try:
        for v in range(VONG):
            if w.con is None:
                w.mo(str(mau), chi_doc=False)
            a.trigger()
            don(w)
            if v == 0:
                w.mo_trang(0) if hasattr(w, 'mo_trang') else None
                don(w)
            mau_do.append(anh())
            w.mo_trang(0) if hasattr(w, 'mo_trang') else None
    except Exception as e:  # noqa
        g.write(f'LOI {ten}: {type(e).__name__} {str(e)[:100]}\n')
        continue
    finally:
        faulthandler.cancel_dump_traceback_later()
    dau, cuoi = mau_do[1], mau_do[-1]
    n = VONG - 2
    d_cc, d_all, d_kb = (cuoi[0] - dau[0]) / n, (cuoi[1] - dau[1]) / n, (cuoi[2] - dau[2]) / n
    moi = cuoi[3] - dau[3]
    dong_ = f'{ten}\tcap_cao/vong {d_cc:+.1f}\twidget/vong {d_all:+.1f}\tKB/vong {d_kb:+.0f}\t{dict(moi)}\n'
    g.write(dong_)
    if d_cc > 0.5 or d_all > 1 or d_kb > 120:
        ro.append(dong_)
g.write(f'XONG so lenh {len(lenh)} ro {len(ro)} tong {anh()[:3]}\n')
print('so lenh', len(lenh), 'nghi ro', len(ro), flush=True)
for x in ro:
    print(x.strip()[:200], flush=True)
sys.stdout.flush()
os._exit(0)

"""Đo ĐỘ TRỄ PHẢN HỒI từng lệnh của cửa sổ chính (1.0.98): bấm lệnh -> cửa sổ / hộp hiện và rảnh. Lần đầu (lạnh: nạp module, dựng hộp)
và lần sau (ấm). Dữ liệu GIẢ LẬP N hộ, không đụng dự án thật; chặn in / Excel / mạng như kiem_tra_giao_dien.

  .venv\\Scripts\\python do_phan_hoi.py [--so-ho 3000] [--ra ket_qua_kiem_tra\\PhanHoi_<giờ>.md] [--lan 3] [--chi "Lệnh A|Lệnh B"]
  --ra x.md còn ghi x.json ({lệnh: [lần đầu, trung vị lần sau]}) cho phan_tich_phien_ban (mục 1c, so với bản trước - Đợt 11).

Ngưỡng (skill toc-do-phan-hoi): phản hồi < 100 ms tốt, < 300 ms chấp nhận, > 1 s phải có con trỏ chờ / tiến trình.
Đo trên máy rảnh (không chạy cùng bộ test / dựng bộ cài)."""
from __future__ import annotations

import ctypes
import gc
import os
import statistics
import sys
import tempfile
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, os.getcwd())
SO_HO = int(sys.argv[sys.argv.index('--so-ho') + 1]) if '--so-ho' in sys.argv else 3000
RA = sys.argv[sys.argv.index('--ra') + 1] if '--ra' in sys.argv else ''
HO_SO = sys.argv[sys.argv.index('--ho-so') + 1] if '--ho-so' in sys.argv else ''
LAN = max(2, int(sys.argv[sys.argv.index('--lan') + 1])) if '--lan' in sys.argv else 3
CHI = set(sys.argv[sys.argv.index('--chi') + 1].split('|')) if '--chi' in sys.argv else None
sys.argv = sys.argv[:1]
td = Path(tempfile.mkdtemp(prefix='dph_'))
(td / 'luu').mkdir()
(td / 'thu_muc').mkdir()
os.environ['PABT_THU_MUC_MAY'] = str(td / 'may')
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
T0 = time.perf_counter()
import pabt  # noqa: E402
from PySide6.QtCore import QCoreApplication, QEvent  # noqa: E402
from PySide6.QtWidgets import QApplication, QDialog  # noqa: E402
qa = QApplication([])
from pabt import app as ud  # noqa: E402
from pabt.giao_dien import ap_dung  # noqa: E402
ap_dung(qa)
T_NAP = time.perf_counter() - T0
import kiem_tra_giao_dien as ktgd  # noqa: E402
kt = ktgd.KiemTra(td)
ktgd.chan_tac_dong(kt)
kt.thu = lambda *a, **k: None
import traceback  # noqa: E402
sys.excepthook = lambda *a: print('LOI', ''.join(traceback.format_exception(*a))[-1500:], flush=True)


def ranh():
    for _ in range(2):
        qa.processEvents()
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)


def don(w):
    ranh()
    for h in [h for h in w.findChildren(QDialog) if h.isVisible() and not h.isModal()]:
        h.close()
    w.don_hop_da_dong()
    ranh()
    gc.collect()


def tao_du_an(n: int) -> Path:
    from pabt import du_an_moi
    dong = []
    for i in range(n):
        for j in range(1 + i % 3):
            dong.append(dict(ho_ten=f'Hộ thử {i}', dia_chi='Ấp 1', so_to=str(10 + i), so_thua=str(100 + i * 3 + j),
                             loai_dat=('ONT', 'CLN', 'LUC')[(i + j) % 3], dt_thu_hoi=str(50 + 10 * i + j), vi_tri='1', nhan_khau='4'))
    gia = [dict(loai_dat=l, vi_tri='1', gia=g) for l, g in (('ONT', '3000000'), ('CLN', '250000'), ('LUC', '200000'))]
    p = td / 'lon.pabt'
    du_an_moi.tao_du_an(str(p), dict(ten='Thử', cap_dia_ban='Xã', ten_dia_ban='Bàu Hàm', nam='2026'), dong, gia)
    return p


def ms(t):
    return (time.perf_counter() - t) * 1000


p = tao_du_an(SO_HO)
t = time.perf_counter()
w = ud.CuaSoChinh(menu_trai=True)
w.show()
ranh()
t_cua_so = ms(t)
t = time.perf_counter()
w.mo(str(p), chi_doc=False)
ranh()
t_mo = ms(t)
t_cho = time.time() + 2.5                        # việc hẹn giờ sau khi mở dự án
while time.time() < t_cho:
    qa.processEvents()
    time.sleep(0.02)

BO = ('Thoát', 'Đóng dự án', 'Xóa dự án…', 'Mở dự án…', 'Dự án mới…')
if HO_SO:                                         # --ho-so "Lệnh A|Lệnh B": cProfile lần bấm thứ hai (ấm) của từng lệnh
    import cProfile
    import io
    import pstats
    for ten in HO_SO.split('|'):
        a = w.lenh[ten]
        a.trigger()
        don(w)
        w.mo_trang(0)
        ranh()
        pr = cProfile.Profile()
        t = time.perf_counter()
        pr.enable()
        a.trigger()
        ranh()
        pr.disable()
        tg = ms(t)
        don(w)
        w.mo_trang(0)
        ranh()
        s = io.StringIO()
        st = pstats.Stats(pr, stream=s)
        st.sort_stats('cumulative').print_stats(r'pabt[\\/]', 28)
        print(f'===== {ten}: {tg:.0f} ms (có cProfile, chậm hơn thật ~1,5-2 lần)\n' + s.getvalue().split('ncalls', 1)[-1][:6000],
              flush=True)
        s = io.StringIO()
        pstats.Stats(pr, stream=s).sort_stats('tottime').print_stats(14)
        print('--- tự tốn nhiều nhất (tottime)\n' + s.getvalue().split('ncalls', 1)[-1][:3500], flush=True)
    ctypes.windll.kernel32.TerminateProcess(ctypes.c_void_p(-1), 0)
kq = []
for ten, a in [(t_, a_) for t_, a_ in w.lenh.items() if t_ not in BO and (CHI is None or t_ in CHI)]:
    lan = []
    try:
        for _ in range(LAN):
            if w.con is None:
                w.mo(str(p), chi_doc=False)
                ranh()
            t = time.perf_counter()
            a.trigger()
            ranh()
            lan.append(ms(t))
            don(w)
            if hasattr(w, 'mo_trang'):
                w.mo_trang(0)
                ranh()
    except Exception as e:  # noqa: BLE001
        kq.append((ten, None, None, f'{type(e).__name__}: {str(e)[:80]}'))
        continue
    kq.append((ten, lan[0], statistics.median(lan[1:]), ''))

trang = []
if CHI is None and hasattr(w, 'mo_trang') and hasattr(w, 'trang'):
    from pabt.lenh import TRANG
    for i in list(range(len(TRANG))) * 2:
        t = time.perf_counter()
        w.mo_trang(i)
        ranh()
        trang.append((i, ms(t)))


def muc(v):
    if v is None:
        return '-'
    return 'tốt' if v < 100 else 'được' if v < 300 else 'chậm' if v < 1000 else '**RẤT CHẬM**'


dong = [f'# Độ trễ phản hồi lệnh - LARC {pabt.__version__}', '',
        f'Ngày {datetime.now():%d/%m/%Y %H:%M}, máy {os.environ.get("COMPUTERNAME", "")}, {os.cpu_count()} luồng CPU; dự án giả lập '
        f'{SO_HO} hộ; offscreen. Lần đầu = lạnh (nạp module, dựng hộp); lần sau = trung vị 2 lần.', '',
        f'- Nạp mã + QApplication + bảng kiểu: {T_NAP * 1000:.0f} ms; dựng cửa sổ chính: {t_cua_so:.0f} ms; mở dự án: {t_mo:.0f} ms', '',
        '| Lệnh | Lần đầu (ms) | Lần sau (ms) | Đánh giá lần đầu |', '|---|---|---|---|']
for ten, a, b, loi in sorted(kq, key=lambda x: -(x[1] or 0)):
    dong.append(f'| {ten} | {a:.0f} | {b:.0f} | {muc(a)} |' if loi == '' else f'| {ten} | lỗi | | {loi} |')
if trang:
    lanh = {}
    for i, v in trang:
        lanh.setdefault(i, []).append(v)
    dong += ['', '| Trang menu trái | Lần đầu | Lần sau |', '|---|---|---|']
    dong += [f'| {TRANG[i]} | {v[0]:.0f} | {v[-1]:.0f} |' for i, v in lanh.items()]
do = [x for x in kq if x[1] is not None]
dong += ['', f'Tổng {len(do)} lệnh: tốt {sum(1 for x in do if x[1] < 100)}, được {sum(1 for x in do if 100 <= x[1] < 300)}, '
         f'chậm {sum(1 for x in do if 300 <= x[1] < 1000)}, rất chậm {sum(1 for x in do if x[1] >= 1000)} (lần đầu); lần sau > 300 ms: '
         f'{sum(1 for x in do if x[2] >= 300)}.']
bc = '\n'.join(dong) + '\n'
ra = Path(RA) if RA else Path('ket_qua_kiem_tra') / f'PhanHoi_{pabt.__version__}_{datetime.now():%Y-%m-%d_%H%M}.md'
ra.parent.mkdir(exist_ok=True)
ra.write_text(bc, encoding='utf-8')
import json  # noqa: E402
ra.with_suffix('.json').write_text(json.dumps(dict(phien_ban=pabt.__version__, so_ho=SO_HO, lan=LAN,
                                                  lenh={t: [round(a, 1), round(b, 1)] for t, a, b, l in kq if not l}),
                                             ensure_ascii=False, indent=1), encoding='utf-8')
print(bc, flush=True)
print('Đã lưu:', ra, flush=True)
try:                                                    # Qt có lúc sập khi thoát sau offscreen: kết quả đã ghi
    ctypes.windll.kernel32.TerminateProcess(ctypes.c_void_p(-1), 0)
finally:
    os._exit(0)

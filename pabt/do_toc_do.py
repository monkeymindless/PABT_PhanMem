"""Đo tốc độ trên MÁY NGƯỜI DÙNG (1.1.01 - Đợt 10, ket_qua_kiem_tra/TocDo_PhuongAn_1.0.98.md T9): thay ước tính "máy yếu ≈ ×3" bằng số
đo thật. Không đọc / ghi dự án của người dùng: thao tác đo chạy trên dự án GIẢ LẬP trong thư mục tạm.

- `ghi_khoi_dong` / `doc_khoi_dong`: mỗi lần mở phần mềm ghi thời gian từ lúc tiến trình bắt đầu tới khi cửa sổ chính lên hình
  (<thư mục máy>\\khoi_dong.json, giữ GIU_KHOI_DONG lần) - có cả lần khởi động lạnh (sau khi bật máy) mà phép đo nhân tạo không tái hiện.
- `thong_tin` (CPU, nhân, RAM, loại ổ đĩa SSD / HDD / mạng), `do_dia` (ghi tuần tự, độ trễ một lần lưu SQLite như khi lưu hộ),
  `do_giao_dien` (mở dự án, Lập PA, chuyển hộ, lưu, Màn hình chính, Kiểm tra lỗi, xuất Excel, hiện hộp nhiều nút).
- `chay(file_ra)`: đủ các phần trên -> báo cáo Markdown. Chạy bằng `PABT.exe do-toc-do <file>` (chay.py) trong TIẾN TRÌNH CON chế độ
  offscreen, thư mục máy tạm (nút "Đo tốc độ máy này" ở hộp Chẩn đoán): không đụng cửa sổ, danh sách dự án gần đây của người dùng.
Không Qt ở cấp module (thong_tin / do_dia / nhật ký khởi động dùng được không cần giao diện)."""
from __future__ import annotations

import json
import os
import statistics
import sys
import tempfile
import time
from datetime import datetime
from pathlib import Path

TEN_NHAT_KY = 'khoi_dong.json'
GIU_KHOI_DONG = 30
SO_HO_MAC_DINH = 1000

# ngưỡng (ms) đánh giá - cùng tinh thần skill toc-do-phan-hoi: phản hồi < 100 ms tốt, mở hộp < 300 ms, việc nặng có tiến trình
NGUONG = {
    'mo_cua_so_chinh': (300, 1000), 'mo_du_an': (1500, 4000), 'lap_pa_lan_dau': (300, 900), 'chuyen_ho': (100, 300),
    'luu_1_ho': (50, 150), 'man_hinh_chinh': (100, 300), 'kiem_tra_loi': (500, 2000), 'kiem_tra_loi_lan_sau': (100, 300),
    'xuat_danh_sach': (1000, 4000), 'hop_500_widget': (100, 300), 'ghi_dia_mb_giay': None, 'luu_sqlite': (20, 80),
    'khoi_dong': (2500, 6000),
}
TEN = {
    'mo_cua_so_chinh': 'Dựng cửa sổ chính', 'mo_du_an': 'Mở dự án', 'lap_pa_lan_dau': 'Mở cửa sổ Lập phương án (lần đầu)',
    'chuyen_ho': 'Mở hộ khác (cửa sổ đang mở)', 'luu_1_ho': 'Lưu phương án 1 hộ', 'man_hinh_chinh': 'Về Màn hình chính',
    'kiem_tra_loi': 'Kiểm tra lỗi cả dự án (lần đầu)', 'kiem_tra_loi_lan_sau': 'Kiểm tra lỗi (mở lại, chưa sửa gì)',
    'xuat_danh_sach': 'Xuất danh sách hộ ra Excel', 'hop_500_widget': 'Hiện hộp thoại 500 ô / nút', 'luu_sqlite': 'Một lần lưu xuống ổ đĩa (SQLite)',
    'khoi_dong': 'Khởi động tới khi cửa sổ lên hình',
}


# ---------------------------------------------------------------- nhật ký khởi động
def _thu_muc_may() -> Path:
    from .dia_phuong import thu_muc_may
    return thu_muc_may()


def ms_tu_luc_chay() -> float | None:
    """Mili giây từ lúc tiến trình này được tạo (Windows: GetProcessTimes) - gồm cả nạp exe / DLL / Python trước khi chạy mã."""
    if os.name != 'nt':
        return None
    try:
        import ctypes
        import ctypes.wintypes as wt
        k32 = ctypes.windll.kernel32
        tao, x1, x2, x3 = wt.FILETIME(), wt.FILETIME(), wt.FILETIME(), wt.FILETIME()
        k32.GetCurrentProcess.restype = wt.HANDLE
        pf = ctypes.POINTER(wt.FILETIME)                 # bản 64-bit: không khai báo thì handle bị cắt còn 32 bit -> lỗi
        k32.GetProcessTimes.argtypes = [wt.HANDLE, pf, pf, pf, pf]
        k32.GetProcessTimes.restype = wt.BOOL
        if not k32.GetProcessTimes(k32.GetCurrentProcess(), ctypes.byref(tao), ctypes.byref(x1), ctypes.byref(x2), ctypes.byref(x3)):
            return None
        bay_gio = wt.FILETIME()
        k32.GetSystemTimeAsFileTime(ctypes.byref(bay_gio))

        def so(f):
            return (f.dwHighDateTime << 32) | f.dwLowDateTime
        return (so(bay_gio) - so(tao)) / 10000.0
    except Exception:                                   # noqa: BLE001 - chỉ là số đo phụ
        return None


def ghi_khoi_dong(ms: float | None, thu_muc=None) -> None:
    """Ghi một lần khởi động (giữ GIU_KHOI_DONG lần gần nhất). Lỗi ghi file: bỏ qua (không làm hỏng khởi động)."""
    if ms is None:
        return
    from . import __version__
    p = Path(thu_muc or _thu_muc_may()) / TEN_NHAT_KY
    try:
        ds = doc_khoi_dong(p.parent)
        ds.append(dict(luc=datetime.now().isoformat(timespec='seconds'), ms=round(ms), phien_ban=__version__,
                       dong_goi=bool(getattr(sys, 'frozen', False))))
        p.parent.mkdir(parents=True, exist_ok=True)
        tam = p.with_name(p.name + '.tmp')
        tam.write_text(json.dumps(ds[-GIU_KHOI_DONG:], ensure_ascii=False, indent=1), encoding='utf-8')
        os.replace(tam, p)
    except (OSError, ValueError):
        pass


def doc_khoi_dong(thu_muc=None) -> list:
    p = Path(thu_muc or _thu_muc_may()) / TEN_NHAT_KY
    try:
        ds = json.loads(p.read_text(encoding='utf-8'))
        return [x for x in ds if isinstance(x, dict) and isinstance(x.get('ms'), (int, float))]
    except (OSError, ValueError):
        return []


# ---------------------------------------------------------------- máy, ổ đĩa
def ten_cpu() -> str:
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r'HARDWARE\DESCRIPTION\System\CentralProcessor\0') as k:
            return ' '.join(str(winreg.QueryValueEx(k, 'ProcessorNameString')[0]).split())
    except (OSError, ImportError):
        import platform
        return platform.processor() or 'không rõ'


def loai_o_dia(duong_dan) -> str:
    """'SSD' | 'HDD' | 'ổ mạng' | 'USB / thẻ nhớ' | 'không rõ' - ổ chứa duong_dan. Đọc thuộc tính "seek penalty" của ổ (Windows 7+), không
    cần quyền quản trị."""
    p = str(Path(duong_dan).resolve())
    if p.startswith('\\\\'):
        return 'ổ mạng'
    if os.name != 'nt' or len(p) < 2 or p[1] != ':':
        return 'không rõ'
    try:
        import ctypes
        import ctypes.wintypes as wt
        k32 = ctypes.windll.kernel32
        loai = k32.GetDriveTypeW(p[:3])
        if loai == 4:
            return 'ổ mạng'
        if loai == 2:
            return 'USB / thẻ nhớ'
        k32.CreateFileW.restype = wt.HANDLE
        h = k32.CreateFileW(f'\\\\.\\{p[:2]}', 0, 3, None, 3, 0, None)   # quyền 0: chỉ hỏi thuộc tính, không đọc dữ liệu
        if h in (None, wt.HANDLE(-1).value):
            return 'không rõ'
        try:
            hoi = (ctypes.c_uint32 * 3)(7, 0, 0)        # StorageDeviceSeekPenaltyProperty, PropertyStandardQuery
            ra = (ctypes.c_uint8 * 12)()
            n = wt.DWORD()
            if not k32.DeviceIoControl(wt.HANDLE(h), 0x2D1400, ctypes.byref(hoi), 12, ctypes.byref(ra), 12, ctypes.byref(n), None):
                return 'không rõ'
            return 'HDD' if ra[8] else 'SSD'
        finally:
            k32.CloseHandle(wt.HANDLE(h))           # bọc HANDLE: bản 64-bit không cắt còn 32 bit
    except Exception:                                   # noqa: BLE001
        return 'không rõ'


def thong_tin() -> dict:
    import platform
    from . import __version__
    from .csdl import la_may_yeu, ram_vat_ly_mb
    goc_cai = Path(sys.executable).parent if getattr(sys, 'frozen', False) else Path(__file__).resolve().parents[1]
    return dict(phan_mem=__version__, dong_goi=bool(getattr(sys, 'frozen', False)), he_dieu_hanh=platform.platform(),
                kien_truc=platform.machine(), python=platform.python_version(), bit=64 if sys.maxsize > 2 ** 32 else 32,
                cpu=ten_cpu(), so_luong=os.cpu_count(), ram_mb=ram_vat_ly_mb(), may_yeu=la_may_yeu(),
                o_cai=loai_o_dia(goc_cai), o_tam=loai_o_dia(tempfile.gettempdir()))


def do_dia(thu_muc) -> dict:
    """Ghi tuần tự 16 MB (fsync) -> MB/giây; 30 lần COMMIT nhỏ SQLite (journal DELETE, như lưu một hộ) -> trung vị ms / lần."""
    import sqlite3
    td = Path(thu_muc)
    p = td / 'thu_ghi.bin'
    khoi = os.urandom(1024 * 1024)
    t = time.perf_counter()
    with open(p, 'wb') as f:
        for _ in range(16):
            f.write(khoi)
        f.flush()
        os.fsync(f.fileno())
    giay = time.perf_counter() - t
    p.unlink()
    con = sqlite3.connect(str(td / 'thu.sqlite'))
    try:
        con.execute('PRAGMA journal_mode = DELETE')
        con.execute('CREATE TABLE t (a INTEGER, b TEXT)')
        con.commit()
        ds = []
        for i in range(30):
            t = time.perf_counter()
            con.execute('INSERT INTO t VALUES (?, ?)', (i, 'x' * 200))
            con.commit()
            ds.append((time.perf_counter() - t) * 1000)
    finally:
        con.close()
    return dict(ghi_dia_mb_giay=round(16 / giay, 1) if giay > 0 else None, luu_sqlite=round(statistics.median(ds), 1))


# ---------------------------------------------------------------- thao tác giao diện (cần QApplication)
def _tao_du_an(p: Path, so_ho: int) -> None:
    from . import du_an_moi
    dong = [dict(ho_ten=f'Hộ thử {i}', dia_chi='Ấp 1', so_to=str(10 + i), so_thua=str(100 + i * 3 + j),
                 loai_dat=('ONT', 'CLN', 'LUC')[(i + j) % 3], dt_thu_hoi=str(50 + 10 * i + j), vi_tri='1', nhan_khau='4')
            for i in range(so_ho) for j in range(1 + i % 3)]
    gia = [dict(loai_dat=l, vi_tri='1', gia=g) for l, g in (('ONT', '3000000'), ('CLN', '250000'), ('LUC', '200000'))]
    du_an_moi.tao_du_an(str(p), dict(ten='Dự án đo tốc độ', cap_dia_ban='Xã', ten_dia_ban='Thử', nam='2026'), dong, gia)


def do_giao_dien(thu_muc, so_ho: int = SO_HO_MAC_DINH, bao=None) -> dict:
    """Các thao tác hằng ngày trên dự án giả lập so_ho hộ trong thu_muc (ms). bao(chữ): báo bước đang đo."""
    from PySide6.QtCore import QCoreApplication, QEvent
    from PySide6.QtWidgets import QApplication, QDialog, QGridLayout, QLabel, QLineEdit, QPushButton
    qa = QApplication.instance()
    bao = bao or (lambda _c: None)

    def ranh():
        for _ in range(2):
            qa.processEvents()
            QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)

    def do(ham) -> float:
        t = time.perf_counter()
        ham()
        ranh()
        return round((time.perf_counter() - t) * 1000, 1)
    kq = {}
    # offscreen nạp CẢ thư mục phông ở lần vẽ chữ đầu (~2 s) - cửa sổ thật trên Windows không có bước này: vẽ trước một nhãn để số đo
    # "Dựng cửa sổ chính" là của phần mềm (khởi động thật nằm ở nhật ký khởi động)
    nhan = QLabel('Khởi động phông chữ - Tiếng Việt')
    nhan.show()
    ranh()
    nhan.close()
    nhan.deleteLater()
    p = Path(thu_muc) / 'do_toc_do.pabt'
    bao(f'Tạo dự án giả lập {so_ho} hộ…')
    t = time.perf_counter()
    _tao_du_an(p, so_ho)
    kq['tao_du_an'] = round((time.perf_counter() - t) * 1000)
    from . import app as ud
    from . import lap_pa, man_hinh_quan_ly, quan_ly
    bao('Cửa sổ chính, mở dự án…')
    w = None

    def dung_cua_so():
        nonlocal w
        w = ud.CuaSoChinh(menu_trai=True)
        w.show()
    kq['mo_cua_so_chinh'] = do(dung_cua_so)
    try:
        kq['mo_du_an'] = do(lambda: w.mo(str(p), chi_doc=False))
        ma = [r[0] for r in w.con.execute('SELECT ma_ho FROM ho ORDER BY thu_tu, ma_ho LIMIT 12')]
        bao('Lập phương án, chuyển hộ, lưu…')
        kq['lap_pa_lan_dau'] = do(lambda: w.mo_lap_pa(ma[0]))
        kq['chuyen_ho'] = statistics.median(do(lambda m=m: w.mo_lap_pa(m)) for m in ma[1:6])
        ds = []
        for m in ma[6:12]:
            bo = lap_pa.BoSoan(w.con, m, w.dm)
            bo.sua_dat(0, 'dien_tich', '33')
            t = time.perf_counter()
            bo.luu()
            ds.append((time.perf_counter() - t) * 1000)
        kq['luu_1_ho'] = round(statistics.median(ds), 1)
        w.ve_trang_chu()
        ranh()
        kq['man_hinh_chinh'] = statistics.median(do(w.ve_trang_chu) for _ in range(3))
        bao('Kiểm tra lỗi, xuất Excel…')

        def kiem():
            h = man_hinh_quan_ly.HopKiemLoi(w.con, w, w.dm)
            h.close()
            h.deleteLater()
        kq['kiem_tra_loi'] = do(kiem)
        kq['kiem_tra_loi_lan_sau'] = do(kiem)
        f = Path(thu_muc) / 'danh_sach.xlsx'
        kq['xuat_danh_sach'] = do(lambda: quan_ly.ghi_bao_cao_tong_hop(quan_ly.du_lieu_bao_cao(w.con), f))
    finally:
        if w is not None:
            for k in (list(w.khung_tab.khoa) if hasattr(w, 'khung_tab') else []):
                ww = w.khung_tab.widget.get(k)
                if ww is not None and hasattr(ww, 'bo'):
                    ww.bo.mo(ww.bo.ma_ho)               # bỏ thay đổi chưa lưu: đóng không hỏi
            w.dong_du_an()
            w.close()
            ranh()
    bao('Hộp thoại nhiều nút…')

    def hop():
        h = QDialog()
        lo = QGridLayout(h)
        for i in range(100):
            lo.addWidget(QLabel(f'Nhãn {i}'), i, 0)
            lo.addWidget(QLineEdit(), i, 1)
            for j in range(3):
                lo.addWidget(QPushButton(('Lưu', 'Xóa', 'In / Xuất')[j]), i, 2 + j)
        h.show()
        ranh()
        h.close()
        h.deleteLater()
    do(hop)
    kq['hop_500_widget'] = statistics.median(do(hop) for _ in range(3))
    kq['so_ho'] = so_ho
    return kq


# ---------------------------------------------------------------- đánh giá, báo cáo
def danh_gia(k: str, v) -> str:
    ng = NGUONG.get(k)
    if ng is None or not isinstance(v, (int, float)):
        return ''
    return 'tốt' if v <= ng[0] else 'được' if v <= ng[1] else 'CHẬM'


def ket_luan(tt: dict, dia: dict, gd: dict, kd: list) -> list:
    """Lời khuyên theo số đo (không tự đổi thiết lập nào của máy)."""
    ra = []
    if 'HDD' in (tt.get('o_cai'), tt.get('o_tam')):
        ra.append('Phần mềm / thư mục tạm nằm trên ổ cứng cơ (HDD): khởi động lần đầu sau khi bật máy và mở hộp lần đầu sẽ chậm. '
                  'Nếu được, cài phần mềm và để file dự án trên ổ SSD.')
    if (dia.get('luu_sqlite') or 0) > NGUONG['luu_sqlite'][1]:
        ra.append(f'Mỗi lần lưu xuống ổ đĩa mất {dia["luu_sqlite"]} ms (ngưỡng {NGUONG["luu_sqlite"][1]} ms): ổ đĩa chậm hoặc phần mềm '
                  'diệt virus quét từng lần ghi. Có thể nhờ quản trị máy thêm thư mục dự án vào danh sách loại trừ quét.')
    if (tt.get('ram_mb') or 99999) < 4200:
        ra.append(f'RAM {tt.get("ram_mb")} MB: nên đóng bớt chương trình khác (trình duyệt nhiều thẻ, Zalo) khi lập phương án dự án lớn.')
    if kd:
        ms = sorted(x['ms'] for x in kd)
        if ms[-1] > NGUONG['khoi_dong'][1]:
            ra.append(f'Có lần khởi động mất {ms[-1] / 1000:.1f} giây (thường là lần đầu sau khi bật máy - Windows đọc phần mềm từ ổ '
                      'đĩa và quét virus). Các lần sau nhanh hơn.')
    cham = [TEN.get(k, k) for k, v in gd.items() if danh_gia(k, v) == 'CHẬM']
    if cham:
        ra.append('Thao tác chậm hơn ngưỡng: ' + ', '.join(cham) + '. Gửi báo cáo này cho tác giả (kèm gói chẩn đoán) để tối ưu.')
    if not ra:
        ra.append('Máy đáp ứng tốt: mọi thao tác đo được đều trong ngưỡng.')
    return ra


def _o(v) -> str:
    if v is None:
        return '-'
    if isinstance(v, float) and v < 100:
        return f'{v:.1f}'.replace('.', ',')
    return f'{round(v):,}'.replace(',', '.')


def bao_cao(tt: dict, dia: dict, gd: dict, kd: list) -> str:
    t = [f'# Đo tốc độ máy - LARC {tt.get("phan_mem")}', '', f'Lúc {datetime.now():%H:%M %d/%m/%Y}. Thao tác đo trên dự án GIẢ LẬP '
         f'{gd.get("so_ho", "?")} hộ (không đụng dự án thật).', '', '## Máy', '',
         f'- CPU: {tt.get("cpu")} ({tt.get("so_luong")} luồng); RAM: {_o(tt.get("ram_mb"))} MB; '
         f'{"máy cấu hình yếu (phần mềm tự giảm hiệu ứng)" if tt.get("may_yeu") else "cấu hình đủ"}',
         f'- Hệ điều hành: {tt.get("he_dieu_hanh")}; bản {tt.get("bit")}-bit, Python {tt.get("python")}'
         f'{" (bản cài)" if tt.get("dong_goi") else " (mã nguồn)"}',
         f'- Ổ chứa phần mềm: {tt.get("o_cai")}; ổ thư mục tạm: {tt.get("o_tam")}', '',
         '## Ổ đĩa', '', f'- Ghi tuần tự: {_o(dia.get("ghi_dia_mb_giay"))} MB/giây',
         f'- Một lần lưu xuống ổ đĩa (SQLite, như lưu một hộ): {_o(dia.get("luu_sqlite"))} ms - {danh_gia("luu_sqlite", dia.get("luu_sqlite"))}',
         '', '## Thao tác (ms)', '', '| Thao tác | Đo được | Ngưỡng tốt / được | Đánh giá |', '|---|---|---|---|']
    for k in ('mo_cua_so_chinh', 'mo_du_an', 'lap_pa_lan_dau', 'chuyen_ho', 'luu_1_ho', 'man_hinh_chinh', 'kiem_tra_loi',
              'kiem_tra_loi_lan_sau', 'xuat_danh_sach', 'hop_500_widget'):
        if k in gd:
            ng = NGUONG[k]
            t.append(f'| {TEN[k]} | {_o(gd[k])} | {_o(ng[0])} / {_o(ng[1])} | {danh_gia(k, gd[k])} |')
    t += ['', '## Khởi động thật (các lần mở phần mềm gần đây)', '']
    if kd:
        ms = [x['ms'] for x in kd]
        t.append(f'- {len(ms)} lần: nhanh nhất {_o(min(ms))} ms, trung vị {_o(statistics.median(ms))} ms, chậm nhất {_o(max(ms))} ms '
                 f'(lần chậm nhất thường là lần đầu sau khi bật máy)')
        t += [f'  - {x["luc"].replace("T", " ")}: {_o(x["ms"])} ms (bản {x.get("phien_ban", "?")})' for x in kd[-8:]]
    else:
        t.append('- Chưa có (ghi từ bản 1.1.01, mỗi lần mở phần mềm).')
    t += ['', '## Nhận xét', ''] + [f'- {x}' for x in ket_luan(tt, dia, gd, kd)]
    return '\n'.join(t) + '\n'


def chay(file_ra, so_ho: int = SO_HO_MAC_DINH, bao=None) -> Path:
    """Đo đủ (cần QApplication - chay.py tạo) rồi ghi báo cáo Markdown ra file_ra. Nhật ký khởi động đọc từ thư mục máy THẬT trước khi
    chuyển sang thư mục máy tạm cho phần đo (không ghi dự án gần đây / thiết lập của người dùng)."""
    kd = doc_khoi_dong()
    tt = thong_tin()
    with tempfile.TemporaryDirectory(prefix='larc_do_toc_do_') as td:
        cu = os.environ.get('PABT_THU_MUC_MAY')
        os.environ['PABT_THU_MUC_MAY'] = str(Path(td) / 'may')
        try:
            dia = do_dia(td)
            gd = do_giao_dien(td, so_ho, bao)
        finally:
            if cu is None:
                os.environ.pop('PABT_THU_MUC_MAY', None)
            else:
                os.environ['PABT_THU_MUC_MAY'] = cu
    ra = Path(file_ra)
    ra.parent.mkdir(parents=True, exist_ok=True)
    ra.write_text(bao_cao(tt, dia, gd, kd), encoding='utf-8')
    (ra.with_suffix('.json')).write_text(json.dumps(dict(may=tt, dia=dia, thao_tac=gd, khoi_dong=kd), ensure_ascii=False, indent=1),
                                         encoding='utf-8')
    return ra

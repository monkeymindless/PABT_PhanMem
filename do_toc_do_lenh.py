r"""Đo thời gian phản hồi MỌI lệnh cửa sổ chính + chuyển trang + gõ tìm.

Ngưỡng UX (ui-ux-pro-max / toc-do-phan-hoi):
  < 100 ms  phản hồi tức thì (tap feedback)
  100–400   cảm thấy chậm
  400–1000  chậm — lần mở nặng (dựng bảng)
  > 1000    phải có con trỏ chờ / tiến trình
  > 5000    đơ (cùng ngưỡng kiem_tra_giao_dien)

  .venv\Scripts\python do_toc_do_lenh.py [--so-ho 12]
  -> ket_qua_kiem_tra\TocDoLenh_<phiên bản>_<giờ>.md
"""
from __future__ import annotations

import os
import shutil
import sys
import tempfile
import time
from datetime import datetime
from pathlib import Path

GOC = Path(__file__).resolve().parent
sys.path.insert(0, str(GOC))

NGUONG = (100, 400, 1000, 5000)  # ms


def _chan_hop():
    from PySide6.QtWidgets import QDialog, QFileDialog, QInputDialog, QMessageBox
    QMessageBox.question = staticmethod(lambda *a, **k: QMessageBox.StandardButton.No)
    QMessageBox.information = staticmethod(lambda *a, **k: QMessageBox.StandardButton.Ok)
    QMessageBox.warning = staticmethod(lambda *a, **k: QMessageBox.StandardButton.Ok)
    QMessageBox.critical = staticmethod(lambda *a, **k: QMessageBox.StandardButton.Ok)
    QMessageBox.about = staticmethod(lambda *a, **k: None)
    QMessageBox.exec = lambda self, *a: 0
    if hasattr(QMessageBox, 'exec_'):
        QMessageBox.exec_ = QMessageBox.exec
    QDialog.exec = lambda self, *a: 0
    if hasattr(QDialog, 'exec_'):
        QDialog.exec_ = QDialog.exec
    QFileDialog.getOpenFileName = staticmethod(lambda *a, **k: ('', ''))
    QFileDialog.getOpenFileNames = staticmethod(lambda *a, **k: ([], ''))
    QFileDialog.getSaveFileName = staticmethod(lambda *a, **k: ('', ''))
    QFileDialog.getExistingDirectory = staticmethod(lambda *a, **k: '')
    QInputDialog.getText = staticmethod(lambda *a, **k: ('Ho do toc do', True))
    QInputDialog.getInt = staticmethod(lambda *a, **k: (1, True))
    QInputDialog.getItem = staticmethod(lambda cha, td, nhan, ds, *a, **k: (ds[0] if ds else '', True))


def _ms(app, ham) -> float:
    t0 = time.perf_counter()
    ham()
    app.processEvents()
    return (time.perf_counter() - t0) * 1000


def _bac(ms: float) -> str:
    if ms < NGUONG[0]:
        return 'tuc_thi'
    if ms < NGUONG[1]:
        return 'cham_nhe'
    if ms < NGUONG[2]:
        return 'cham'
    if ms < NGUONG[3]:
        return 'cho'
    return 'do'


def main(argv) -> int:
    so_ho = int(argv[argv.index('--so-ho') + 1]) if '--so-ho' in argv else 12
    td = Path(tempfile.mkdtemp(prefix='pabt_toc_do_lenh_'))
    os.environ['PABT_THU_MUC_MAY'] = str(td / 'may')
    os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
    os.environ.setdefault('PABT_HOAT_ANH', '0')
    from kiem_tra_giao_dien import du_an_thu
    import pabt
    from PySide6.QtWidgets import QApplication, QDialog, QWidget
    qa = QApplication([])
    from pabt import app as ud
    from pabt.giao_dien import ap_dung
    ap_dung(qa)
    _chan_hop()

    kq = {'khoi_dong': 0.0, 'mo_du_an': 0.0, 'trang': [], 'lenh': [], 'lenh2': [], 'go': 0.0, 'kpi': 0.0}
    t0 = time.perf_counter()
    w = ud.CuaSoChinh(menu_trai=True)
    w.show()
    qa.processEvents()
    kq['khoi_dong'] = (time.perf_counter() - t0) * 1000

    p = du_an_thu(td, so_ho)
    kq['mo_du_an'] = _ms(qa, lambda: w.mo(str(p)))

    for i, ten in enumerate(ud.TRANG):
        lan1 = _ms(qa, lambda i=i: w.mo_trang(i))
        lan2 = _ms(qa, lambda i=i: w.mo_trang(i))
        kq['trang'].append((ten, lan1, lan2))
    kq['trang'].append(('Màn hình chính', _ms(qa, w.ve_trang_chu), _ms(qa, w.ve_trang_chu)))
    kq['trang'].append(('So sánh với thực tế', _ms(qa, w.so_sanh_du_toan), _ms(qa, w.so_sanh_du_toan)))
    w.mo_trang(0)

    hop_dong = []

    def do_lenh(ten, ham):
        ms1 = _ms(qa, ham)
        kq['lenh'].append((ten, ms1))
        o = ham() if callable(ham) else None
        # lần 2: lệnh tạo hộp mới mỗi lần (không tái sử dụng tab)
        ms2 = _ms(qa, ham)
        kq['lenh2'].append((ten, ms2))
        return o

    # lệnh mở hộp / trang — gọi thẳng hàm (cho=False) = thời gian dựng, không gồm exec()
    ds = [
        ('Thông tin dự án…', lambda: w.sua_du_an(cho=False)),
        ('Tìm nhanh…', lambda: w.tim_nhanh(cho=False)),
        ('Bảng giá đất NQ 28…', lambda: w.bang_gia_dat(cho=False)),
        ('Cập nhật bảng giá đất…', lambda: w.cap_nhat_bang_gia_dat(cho=False)),
        ('Đợt trình…', lambda: w.dot_trinh(cho=False)),
        ('Kiểm tra lỗi…', lambda: w.kiem_tra_loi(cho=False)),
        ('Bộ đơn giá…', lambda: w.bo_don_gia(cho=False)),
        ('Đơn giá riêng dự án…', lambda: w.don_gia_rieng(cho=False)),
        ('In / Xuất…', lambda: w.in_xuat(cho=False)),
        ('Quản lý Mẫu in & Bản in…', lambda: w.quan_ly_mau_in(cho=False)),
        (ud.LENH_THONG_KE, lambda: w.thong_ke_dia_chinh(cho=False)),
        ('Lập phương án hộ…', lambda: w.mo_lap_pa(cho=False)),
        ('Thêm hộ…', lambda: w.mo_ho_so(moi=True, cho=False, ho_ten='Ho do toc do')),
        ('Trạng thái hộ…', lambda: w.trang_thai_ho(cho=False)),
        ('Chọn hộ niêm yết…', lambda: w.chon_ho_niem_yet(cho=False)),
        ('Dự thảo PABT…', lambda: w.mo_du_thao(cho=False)),
        ('Rà soát giá…', lambda: w.ra_soat_gia(cho=False)),
        ('Cỗ máy thời gian (mốc khôi phục)…', lambda: w.co_may_thoi_gian(cho=False)),
        ('Trợ lý (giải thích, soạn nháp)…', lambda: w.tro_ly(cho=False)),
        ('Nhật ký kiểm toán…', lambda: w.nhat_ky_kiem_toan(cho=False)),
        ('Cấu hình nghiệp vụ…', lambda: w.cau_hinh_nghiep_vu(cho=False)),
        ('Giao diện…', lambda: w.giao_dien_tuy_chinh(cho=False)),
        ('Bản đồ thửa đất', lambda: w.ban_do_thua(cho=False)),
        ('Xem hộ trên bản đồ…', lambda: w.xem_ho_tren_ban_do(cho=False)),
        ('Chẩn đoán & sửa lỗi hệ thống…', lambda: w.chan_doan_he_thong(cho=False)),
        ('Phiếu kiểm đếm thực địa…', lambda: w.phieu_kiem_dem(cho=False)),
        ('Tiếp nhận & Kiểm tra pháp lý dự án…', lambda: w.tiep_nhan_phap_ly(cho=False)),
        ('Hướng dẫn sử dụng', lambda: w.huong_dan(cho=False)),
        ('Dự án mới…', lambda: w.du_an_moi(cho=False)),
        ('Dự án trên máy chủ…', lambda: w.du_an_may_chu(cho=False)),
        ('Giới thiệu', w.gioi_thieu),
        ('Lưu dự án', w.luu_du_an_lenh),
        ('Phóng to chữ', lambda: w._phong_to(1)),
        ('Thu nhỏ chữ', lambda: w._phong_to(-1)),
        ('Cỡ chữ 100%', lambda: w._phong_to(0)),
        ('Kết nối máy chủ LAN…', w.thiet_lap_may_chu),
        ('Cập nhật phần mềm…', w.cap_nhat_phan_mem),
        ('Xuất báo cáo đối chiếu…', w.xuat_bao_cao),
        ('Xuất danh sách hộ…', lambda: w.xuat_danh_sach(hoi=False)),
        ('Nhập phương án chi tiết…', lambda: w.nhap_chi_tiet(cho=False)),
        ('Nhập bản vẽ CAD (.dxf)…', lambda: w.nhap_ban_ve_cad(cho=False)),
    ]
    for ten, ham in ds:
        print(f'  {ten}', flush=True)
        t0 = time.perf_counter()
        try:
            o = ham()
            qa.processEvents()
            ms = (time.perf_counter() - t0) * 1000
            kq['lenh'].append((ten, ms, None))
            if isinstance(o, QWidget):
                hop_dong.append(o)
                t1 = time.perf_counter()
                ham()
                qa.processEvents()
                kq['lenh2'].append((ten, (time.perf_counter() - t1) * 1000))
            else:
                kq['lenh2'].append((ten, ms))
        except Exception as e:  # noqa: BLE001
            ms = (time.perf_counter() - t0) * 1000
            kq['lenh'].append((ten, ms, str(e)[:120]))
            kq['lenh2'].append((ten, ms))
            print(f'    LỖI {e}', flush=True)

    w.mo_trang(0)
    qa.processEvents()
    t0 = time.perf_counter()
    w.o_tim.setText('nguyen')
    w.o_tim.phat_ngay() if hasattr(w.o_tim, 'phat_ngay') else w.o_tim.textChanged.emit(w.o_tim.text())
    qa.processEvents()
    kq['go'] = (time.perf_counter() - t0) * 1000
    t0 = time.perf_counter()
    w.bam_the_so('so_ho')
    qa.processEvents()
    kq['kpi'] = (time.perf_counter() - t0) * 1000

    for o in hop_dong:
        try:
            o.close()
            if isinstance(o, QDialog):
                o.deleteLater()
        except RuntimeError:
            pass
    qa.processEvents()
    w.close()

    dong = []
    def hang(ten, ms, lan=''):
        dong.append((ten, ms, _bac(ms), lan))

    hang('Khởi động cửa sổ chính', kq['khoi_dong'])
    hang(f'Mở dự án ({so_ho} hộ)', kq['mo_du_an'])
    hang('Gõ tìm danh sách hộ', kq['go'])
    hang('Bấm thẻ số liệu Số hộ', kq['kpi'])
    for ten, a, b in kq['trang']:
        hang(f'Trang «{ten}» lần 1', a, 'trang')
        hang(f'Trang «{ten}» lần 2', b, 'trang2')
    for item in kq['lenh']:
        ten, ms = item[0], item[1]
        loi = item[2] if len(item) > 2 else None
        hang(f'Lệnh «{ten}»' + (f'  !! {loi}' if loi else ''), ms, 'lenh')
    for ten, ms in kq['lenh2']:
        hang(f'Lệnh «{ten}» lần 2', ms, 'lenh2')

    dong.sort(key=lambda x: -x[1])
    cham = [x for x in dong if x[1] >= NGUONG[0]]
    ra = GOC / 'ket_qua_kiem_tra' / f'TocDoLenh_{pabt.__version__}_{datetime.now():%Y-%m-%d_%H%M}.md'
    ra.parent.mkdir(exist_ok=True)
    t = [
        f'# Tốc độ lệnh PABT {pabt.__version__}',
        f'{datetime.now():%d/%m/%Y %H:%M} · dự án giả lập {so_ho} hộ · offscreen',
        '',
        'Ngưỡng: **< 100 ms** tức thì · 100–400 cảm thấy chậm · 400–1000 chậm · **> 1 s** cần con trỏ chờ · > 5 s đơ.',
        '',
        f'Đã đo: {len(kq["lenh"])} lệnh, {len(kq["trang"])} trang, khởi động, mở dự án, gõ tìm, thẻ KPI.',
        '',
        '## Chậm hơn 100 ms (xếp theo thời gian)',
        '',
        '| ms | bậc | thao tác |',
        '|---:|:---|:---|',
    ]
    if not cham:
        t.append('| — | — | không có |')
    for ten, ms, bac, _ in cham:
        t.append(f'| {ms:.0f} | {bac} | {ten} |')
    t += ['', '## Toàn bộ (nhanh → chậm không; đây là đủ số)', '',
          '| ms | bậc | thao tác |', '|---:|:---|:---|']
    for ten, ms, bac, _ in sorted(dong, key=lambda x: x[1]):
        t.append(f'| {ms:.1f} | {bac} | {ten} |')
    ra.write_text('\n'.join(t) + '\n', encoding='utf-8')
    print('\n'.join(t[: 20 + len(cham)]))
    print(f'\nĐã lưu: {ra}')
    shutil.rmtree(td, ignore_errors=True)
    return 0


if __name__ == '__main__':
    for luong in (sys.stdout, sys.stderr):
        try:
            luong.reconfigure(encoding='utf-8')
        except (AttributeError, ValueError):
            pass
    raise SystemExit(main(sys.argv[1:]))

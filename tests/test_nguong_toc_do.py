"""Ngưỡng tốc độ MỀM (Đợt 11, 1.1.02 - chống chậm trở lại): thời gian đo CHIA cho một đơn vị chuẩn đo ngay trong tiến trình (hộp Qt trần /
vòng Python cố định) nên không phụ thuộc máy nhanh hay chậm; lấy lần NHANH NHẤT của nhiều lần (máy bận chỉ làm chậm, không làm nhanh);
vượt ngưỡng thì đo lại một lượt trước khi báo hỏng.

Ngưỡng ≈ 1,5 x tỷ lệ đo ở 1.1.01 (Qt6 / Qt5). Bản 1.0.98 (trước Đợt 8) vượt ngưỡng: hộp Qt5 8,2 (ngưỡng 6,5), xuất 1.000 hộ 27,8 - 33,8
(ngưỡng 21). Hỏng khi đang chạy cùng việc nặng khác: chạy riêng file này để xác nhận trước khi tìm nguyên nhân."""
from __future__ import annotations

import os
import tempfile
import time
import unittest
from pathlib import Path

import pabt
from PySide6.QtWidgets import QApplication, QDialog, QGridLayout, QLabel, QLineEdit, QPushButton

QT5 = bool(getattr(pabt, 'QT5', False))
NGUONG_HOP = 6.5                        # hộp 500 widget có trang trí (bảng kiểu + bộ lọc + tô màu) / hộp trần
NGUONG_XUAT = 21.0                      # xuất danh sách 1.000 hộ (quan_ly.ghi_bao_cao_tong_hop) / đơn vị Python
NGUONG_LUU = 0.69 if QT5 else 1.13      # lưu 1 hộ (BoSoan.luu, dự án 1.000 hộ) / đơn vị Python (Python 3.8 và 3.14 khác nhau)


def _nhanh_nhat(f, n: int = 5) -> float:
    f()
    return min(f() for _ in range(n))


def don_vi_python() -> float:
    from pabt.tien import D
    t = time.perf_counter()
    s = D(0)
    for i in range(20000):
        s += D(f'{i}.5') * D('1.1')
    sorted(str(i) for i in range(20000))
    return time.perf_counter() - t


def _hien_hop(qa) -> float:
    h = QDialog()
    lo = QGridLayout(h)
    for i in range(100):
        lo.addWidget(QLabel(f'Nhãn {i}'), i, 0)
        lo.addWidget(QLineEdit(), i, 1)
        for j in range(3):
            lo.addWidget(QPushButton(('Lưu', 'Xóa', 'In / Xuất')[j]), i, 2 + j)
    t = time.perf_counter()
    h.show()
    qa.processEvents()
    v = time.perf_counter() - t
    h.close()
    h.deleteLater()
    qa.processEvents()
    return v


def _du_lieu(td: Path, so_ho: int = 1000):
    from pabt import csdl, du_an_moi
    dong = [dict(ho_ten=f'Hộ {i}', dia_chi='Ấp 1', so_to=str(i), so_thua=str(i * 3 + j), loai_dat=('ONT', 'CLN', 'LUC')[(i + j) % 3],
                 dt_thu_hoi=str(50 + i), vi_tri='1', nhan_khau='4') for i in range(so_ho) for j in range(1 + i % 3)]
    p = str(td / 'a.pabt')
    du_an_moi.tao_du_an(p, dict(ten='T', cap_dia_ban='Xã', ten_dia_ban='X', nam='2026'), dong,
                        [dict(loai_dat=l, vi_tri='1', gia='1000') for l in ('ONT', 'CLN', 'LUC')])
    return csdl.mo(p)


def ty_le_hop() -> float:
    """(Tiến trình con) hộp 500 widget: có trang trí / trần, cùng QApplication mới."""
    from pabt import giao_dien
    qa = QApplication.instance() or QApplication([])
    tran = _nhanh_nhat(lambda: _hien_hop(qa))
    giao_dien.ap_dung(qa)
    return _nhanh_nhat(lambda: _hien_hop(qa)) / tran


class TestNguongTocDo(unittest.TestCase):
    def _kiem(self, ten: str, do, nguong: float):
        ty_le = do()
        if ty_le > nguong:                              # có thể máy vừa bận: đo lại một lượt
            ty_le = min(ty_le, do())
        self.assertLessEqual(ty_le, nguong, f'{ten}: {ty_le:.2f} > ngưỡng {nguong} (chạy riêng tests.test_nguong_toc_do để xác nhận)')

    def test_hop_nhieu_nut_trang_tri(self):
        """Đo trong TIẾN TRÌNH CON sạch: không đổi bảng kiểu / bộ lọc của QApplication dùng chung (áp lại kiểu cho mọi widget còn sống
        của các bài trước - chậm cả lượt, số đo bẩn)."""
        import subprocess
        import sys
        goc = Path(__file__).resolve().parents[1]
        env = dict(os.environ, QT_QPA_PLATFORM='offscreen', PYTHONIOENCODING='utf-8', PABT_THU_MUC_MAY=tempfile.mkdtemp())
        if os.path.isdir(r'C:\Windows\Fonts'):
            env.setdefault('QT_QPA_FONTDIR', r'C:\Windows\Fonts')

        def do():
            r = subprocess.run([sys.executable, '-c', 'import tests.test_nguong_toc_do as t; print("TY_LE", t.ty_le_hop())'],
                               cwd=str(goc), env=env, capture_output=True, timeout=300)
            ra = r.stdout.decode('utf-8', 'replace')
            self.assertIn('TY_LE', ra, r.stderr.decode('utf-8', 'replace')[-1500:])
            return float(ra.split('TY_LE', 1)[1].split()[0])
        self._kiem('Hộp 500 widget (trang trí / trần)', do, NGUONG_HOP)

    def test_xuat_va_luu(self):
        from pabt import lap_pa, quan_ly
        td = Path(tempfile.mkdtemp())
        con = _du_lieu(td)
        try:
            sl = quan_ly.du_lieu_bao_cao(con)

            def xuat():
                t = time.perf_counter()
                quan_ly.ghi_bao_cao_tong_hop(sl, td / 'x.xlsx')
                return time.perf_counter() - t
            self._kiem('Xuất danh sách 1.000 hộ / đơn vị Python', lambda: _nhanh_nhat(xuat, 3) / _nhanh_nhat(don_vi_python), NGUONG_XUAT)
            dm = lap_pa.DanhMuc(con)
            k = [10]

            def luu():
                k[0] += 1
                bo = lap_pa.BoSoan(con, k[0], dm)
                bo.sua_dat(0, 'dien_tich', str(20 + k[0]))
                t = time.perf_counter()
                bo.luu()
                return time.perf_counter() - t
            self._kiem('Lưu 1 hộ / đơn vị Python', lambda: _nhanh_nhat(luu, 8) / _nhanh_nhat(don_vi_python), NGUONG_LUU)
        finally:
            con.close()


if __name__ == '__main__':
    unittest.main()

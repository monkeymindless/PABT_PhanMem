r"""Xuất biểu tượng PABT ra file từ ảnh thiết kế: pabt/bieu_tuong.png (512 px, nền trong suốt) + pabt/bieu_tuong.ico (9 cỡ 16..256 px).

0.9.87 (người dùng 15/10/2026): "Mẫu 3 - Lăng kính công lý & nhịp cầu đồng thuận" - khối squircle pha lê xanh băng nhìn nghiêng 3D,
nhịp cầu vàng hổ phách, cán cân pha lê, dấu tích cam, chữ PABT trắng viền vàng; ảnh gốc 1024 x 1024 nền gần trắng. Khối NGHIÊNG nên
không cắt khung cố định + bo góc như bản 0.9.74 (xén mất viền): TÁCH NỀN - loang từ mép ảnh qua các điểm gần màu nền (nền -> trong
suốt), mép làm mịn, cắt vuông theo khung vật thể (chừa lề), thu nhỏ từng nấc 1/2.
0.9.90 (người dùng 15/10/2026): ảnh mới 2000 x 2000 - ô vuông bo góc xanh dương viền vàng, lưới địa chính, nhịp cầu hổ phách, sách
"Luật Đất đai 2024", chữ PABT trắng viền vàng; nền trắng - cùng cách tách nền. Hình vẽ `pabt/ve_bieu_tuong.ve_mach` chỉ là dự phòng.
  set QT_QPA_PLATFORM=windows
  .venv\Scripts\python tao_bieu_tuong.py [anh_thiet_ke.webp]
Chỉ chạy lúc tạo biểu tượng (cần numpy trong .venv); phần mềm khi chạy chỉ đọc bieu_tuong.png. Rồi dựng lại bộ cài (PyInstaller --clean).
"""
from __future__ import annotations
import struct
import sys
from pathlib import Path

from PySide6.QtCore import QBuffer, QByteArray, QIODevice
from PySide6.QtGui import QGuiApplication, QImage

sys.path.insert(0, str(Path(__file__).resolve().parent))
from pabt.ve_bieu_tuong import CO_ICO, thu_nho_muot  # noqa: E402

NGUONG_NEN = 20         # tổng chênh 3 kênh so với màu nền: dưới mức này (và nối liền mép ảnh) là nền
LAM_MIN = 2             # bán kính làm mịn mép (px ảnh gốc 1024)
LE = 0.015              # lề quanh vật thể (tỷ lệ cạnh) - viền pha lê không chạm mép biểu tượng


def png(img: QImage) -> bytes:
    ba = QByteArray()
    b = QBuffer(ba)
    b.open(QIODevice.OpenModeFlag.WriteOnly)
    img.save(b, 'PNG')
    return bytes(ba)


def ghi_ico(file: Path, goc: QImage, co=CO_ICO) -> None:
    """ICO nhiều cỡ, mỗi cỡ một ảnh PNG (Windows Vista trở lên; 256 px ghi kích thước 0 theo chuẩn ICO)."""
    du = [png(thu_nho_muot(goc, s)) for s in co]
    dau = struct.pack('<HHH', 0, 1, len(co))
    off = 6 + 16 * len(co)
    muc = b''
    for s, d in zip(co, du):
        muc += struct.pack('<BBBBHHII', s % 256, s % 256, 0, 0, 1, 32, len(d), off)
        off += len(d)
    file.write_bytes(dau + muc + b''.join(du))


def _mang(anh: QImage):
    import numpy as np
    a = anh.convertToFormat(QImage.Format.Format_RGBA8888)
    w, h = a.width(), a.height()
    du = np.frombuffer(bytes(a.constBits()), np.uint8)
    return du.reshape(h, a.bytesPerLine())[:, :w * 4].reshape(h, w, 4).copy()


def _anh(m) -> QImage:
    import numpy as np
    m = np.ascontiguousarray(m)
    h, w = m.shape[:2]
    return QImage(m.data, w, h, 4 * w, QImage.Format.Format_RGBA8888).copy()


def tach_nen(anh: QImage, canh: int = 512) -> QImage:
    """Nền đồng màu nối liền mép ảnh -> trong suốt (mép mịn), cắt vuông theo khung vật thể + lề, thu về canh x canh."""
    import numpy as np
    m = _mang(anh)
    rgb = m[:, :, :3].astype(np.int32)
    h, w = rgb.shape[:2]
    goc = np.concatenate([rgb[:8, :8].reshape(-1, 3), rgb[:8, -8:].reshape(-1, 3), rgb[-8:, :8].reshape(-1, 3),
                          rgb[-8:, -8:].reshape(-1, 3)])
    nen = np.median(goc, axis=0)
    gan = np.abs(rgb - nen).sum(axis=2) < NGUONG_NEN
    # loang từ mép ảnh qua các điểm gần màu nền (lặp nở 4 hướng tới khi không đổi)
    la_nen = np.zeros_like(gan)
    la_nen[0, :], la_nen[-1, :], la_nen[:, 0], la_nen[:, -1] = gan[0, :], gan[-1, :], gan[:, 0], gan[:, -1]
    while True:
        moi = la_nen.copy()
        moi[1:, :] |= la_nen[:-1, :]
        moi[:-1, :] |= la_nen[1:, :]
        moi[:, 1:] |= la_nen[:, :-1]
        moi[:, :-1] |= la_nen[:, 1:]
        moi &= gan
        if (moi == la_nen).all():
            break
        la_nen = moi
    alpha = np.where(la_nen, 0.0, 255.0)
    for _ in range(LAM_MIN):                            # làm mịn mép: trung bình 3 x 3 (chỉ vùng sát mép thay đổi)
        p = np.pad(alpha, 1, mode='edge')
        alpha = sum(p[1 + dy:h + 1 + dy, 1 + dx:w + 1 + dx] for dy in (-1, 0, 1) for dx in (-1, 0, 1)) / 9.0
    m[:, :, 3] = alpha.round().astype(np.uint8)
    ys, xs = np.nonzero(m[:, :, 3] > 8)
    x0, x1, y0, y1 = xs.min(), xs.max() + 1, ys.min(), ys.max() + 1
    canh_vt = max(x1 - x0, y1 - y0)
    canh_ra = int(round(canh_vt * (1 + 2 * LE)))
    ra = np.zeros((canh_ra, canh_ra, 4), np.uint8)              # vuông, vật thể ở giữa, ngoài vật thể trong suốt
    oy, ox = (canh_ra - (y1 - y0)) // 2, (canh_ra - (x1 - x0)) // 2
    ra[oy:oy + y1 - y0, ox:ox + x1 - x0] = m[y0:y1, x0:x1]
    anh_ra = _anh(ra).convertToFormat(QImage.Format.Format_ARGB32_Premultiplied)
    return thu_nho_muot(anh_ra, canh)


def main():
    app = QGuiApplication(sys.argv)  # noqa: F841
    pabt = Path(__file__).resolve().parent / 'pabt'
    nguon = Path(sys.argv[1]) if len(sys.argv) > 1 else pabt / 'bieu_tuong_thiet_ke.webp'
    anh = QImage(str(nguon))
    if anh.isNull():
        sys.exit(f'Không đọc được ảnh thiết kế {nguon}')
    goc = tach_nen(anh, 512)
    goc.save(str(pabt / 'bieu_tuong.png'))
    ghi_ico(pabt / 'bieu_tuong.ico', goc)
    print('ok', pabt / 'bieu_tuong.ico', pabt / 'bieu_tuong.png')


if __name__ == '__main__':
    main()

r"""Xuất biểu tượng PABT ra file từ ảnh thiết kế: pabt/bieu_tuong.png (512 px, nền trong suốt ngoài góc bo) + pabt/bieu_tuong.ico (16..256 px).

0.9.74 (người dùng 13/10/2026): thiết kế "PABT Fluent Isometric 3D" - mái nhà vàng kim, khối thửa đất 3D ngọc lục bảo / vàng kim, nền
squircle navy viền kim loại đôi, chữ PABT. Ảnh gốc 1024 x 1024 (webp / png) có hào quang ngoài khung: cắt đúng khung squircle, bo
góc cho trong suốt, thu nhỏ từng nấc 1/2 (mịn ở 16-32 px). Hình vẽ bằng mã `pabt/ve_bieu_tuong.ve_mach` chỉ là dự phòng.
  QT_QPA_PLATFORM=windows .venv\Scripts\python tao_bieu_tuong.py [anh_thiet_ke.webp]
Rồi dựng lại bộ cài (PyInstaller --clean): exe, lối tắt Desktop, bộ cài lấy file .ico này.
"""
from __future__ import annotations
import struct
import sys
from pathlib import Path

from PySide6.QtCore import QBuffer, QByteArray, QIODevice
from PySide6.QtGui import QGuiApplication, QImage

sys.path.insert(0, str(Path(__file__).resolve().parent))
from pabt.ve_bieu_tuong import CO_ICO, cat_squircle, thu_nho_muot  # noqa: E402


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


def main():
    app = QGuiApplication(sys.argv)  # noqa: F841
    pabt = Path(__file__).resolve().parent / 'pabt'
    nguon = Path(sys.argv[1]) if len(sys.argv) > 1 else pabt / 'bieu_tuong_thiet_ke.webp'
    anh = QImage(str(nguon))
    if anh.isNull():
        sys.exit(f'Không đọc được ảnh thiết kế {nguon}')
    goc = cat_squircle(anh, 512)
    goc.save(str(pabt / 'bieu_tuong.png'))
    ghi_ico(pabt / 'bieu_tuong.ico', goc)
    print('ok', pabt / 'bieu_tuong.ico', pabt / 'bieu_tuong.png')


if __name__ == '__main__':
    main()

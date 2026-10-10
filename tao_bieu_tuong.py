r"""Vẽ biểu tượng PABT (thu hồi đất - bồi thường - hỗ trợ - tái định cư) -> pabt/bieu_tuong.ico (16..256 px) + pabt/bieu_tuong.png.

Hình: ô vuông bo góc - bình minh - cầu vượt và tuyến cao tốc - mặt bằng đã giải phóng chia thửa
- cột mốc GPMB đỏ trắng - dải chữ "PABT". Cỡ nhỏ (<=32 px) vẽ giản lược cho rõ.
  .venv\Scripts\python tao_bieu_tuong.py
"""
from __future__ import annotations
import struct
import sys
from pathlib import Path

from PySide6.QtCore import QBuffer, QByteArray, QIODevice, QPointF, QRectF, Qt
from PySide6.QtGui import (QBrush, QColor, QFont, QGuiApplication, QImage, QLinearGradient, QPainter, QPainterPath, QPen,
                           QPolygonF, QRadialGradient)

TRANG = QColor('#FFFFFF')


def ve(s: int) -> QImage:
    """Ô vuông bo góc kiểu Windows 11: trời bình minh - mặt trời - cầu vượt cao tốc - tuyến cao tốc phối cảnh
    - hai bên mặt bằng đã giải phóng chia thửa (đất nâu, ruộng xanh) - cột mốc GPMB đỏ trắng - dải chữ PABT."""
    img = QImage(s, s, QImage.Format.Format_ARGB32_Premultiplied)
    img.fill(Qt.GlobalColor.transparent)
    p = QPainter(img)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    nho = s <= 32
    le = 0.04 * s
    khung = QRectF(le, le, s - 2 * le, s - 2 * le)
    vo = QPainterPath()
    vo.addRoundedRect(khung, 0.22 * s, 0.22 * s)
    # bóng đổ nhẹ
    if not nho:
        bong = QPainterPath()
        bong.addRoundedRect(khung.translated(0, 0.018 * s), 0.22 * s, 0.22 * s)
        p.fillPath(bong, QColor(0, 0, 0, 60))
    p.setClipPath(vo)
    chan = 0.47 * s
    # trời: xanh đậm -> cam bình minh
    g = QLinearGradient(0, le, 0, chan)
    g.setColorAt(0, QColor('#0D3B66'))
    g.setColorAt(0.65, QColor('#2E86C1'))
    g.setColorAt(1, QColor('#F9C74F'))
    p.fillRect(QRectF(0, 0, s, chan + 1), QBrush(g))
    # mặt trời
    mt = QRadialGradient(QPointF(0.5 * s, chan), 0.22 * s)
    mt.setColorAt(0, QColor(255, 236, 160, 255))
    mt.setColorAt(0.35, QColor(255, 196, 70, 230))
    mt.setColorAt(1, QColor(255, 196, 70, 0))
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QBrush(mt))
    p.drawEllipse(QPointF(0.5 * s, chan), 0.22 * s, 0.22 * s)
    # đồi xa
    p.setBrush(QColor('#3C6E47'))
    doi = QPainterPath()
    doi.moveTo(0, chan)
    doi.cubicTo(0.18 * s, chan - 0.07 * s, 0.30 * s, chan - 0.02 * s, 0.42 * s, chan)
    doi.lineTo(0, chan)
    p.drawPath(doi)
    doi2 = QPainterPath()
    doi2.moveTo(0.58 * s, chan)
    doi2.cubicTo(0.70 * s, chan - 0.05 * s, 0.85 * s, chan - 0.08 * s, s, chan - 0.02 * s)
    doi2.lineTo(s, chan)
    p.drawPath(doi2)
    # mặt đất: mặt bằng đã giải phóng (đất) giữa, ruộng xanh ngoài
    dat = QLinearGradient(0, chan, 0, s)
    dat.setColorAt(0, QColor('#D9A066'))
    dat.setColorAt(1, QColor('#A66B35'))
    p.setBrush(QBrush(dat))
    p.drawRect(QRectF(0, chan, s, s))
    p.setBrush(QColor('#5FA83A'))
    p.drawPolygon(QPolygonF([QPointF(0, chan), QPointF(0.33 * s, chan), QPointF(-0.45 * s, s)]))
    p.drawPolygon(QPolygonF([QPointF(s, chan), QPointF(0.67 * s, chan), QPointF(1.45 * s, s)]))
    if not nho:
        p.setBrush(QColor('#7CC24E'))
        p.drawPolygon(QPolygonF([QPointF(0, chan + 0.06 * s), QPointF(0.20 * s, chan), QPointF(0.33 * s, chan),
                                 QPointF(0, chan + 0.30 * s)]))
        p.drawPolygon(QPolygonF([QPointF(s, chan + 0.06 * s), QPointF(0.80 * s, chan), QPointF(0.67 * s, chan),
                                 QPointF(s, chan + 0.30 * s)]))
        # đường ranh thửa (lưới chia lô trên mặt bằng)
        p.setPen(QPen(QColor(255, 255, 255, 110), s * 0.006))
        for t in (0.15, 0.35, 0.62):
            y = chan + (s - chan) * t
            p.drawLine(QPointF(0, y), QPointF(s, y))
        for k in (-0.75, -0.45, 0.45, 0.75):
            p.drawLine(QPointF(0.5 * s + k * 0.12 * s, chan), QPointF(0.5 * s + k * 1.3 * s, s))
        p.setPen(Qt.PenStyle.NoPen)
    # cao tốc
    nhua = QLinearGradient(0, chan, 0, s)
    nhua.setColorAt(0, QColor('#5B6770'))
    nhua.setColorAt(1, QColor('#263238'))
    p.setBrush(QBrush(nhua))
    t0, t1 = 0.475 * s, 0.525 * s
    p.drawPolygon(QPolygonF([QPointF(t0, chan), QPointF(t1, chan), QPointF(1.02 * s, s), QPointF(-0.02 * s, s)]))
    p.setPen(QPen(TRANG, max(1.0, s * 0.018)))
    p.drawLine(QPointF(t0 + 0.003 * s, chan), QPointF(0.07 * s, s))
    p.drawLine(QPointF(t1 - 0.003 * s, chan), QPointF(0.93 * s, s))
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor('#FFC107'))
    so = 4 if not nho else 2
    for i in range(so):
        a, b = (i + 0.2) / so, (i + 0.65) / so
        def d(t, l):
            y = chan + (s - chan) * t ** 1.7
            return QPointF(0.5 * s + l * (0.005 + 0.032 * t ** 1.7) * s, y)
        p.drawPolygon(QPolygonF([d(a, -1), d(a, 1), d(b, 1), d(b, -1)]))
    # cầu vượt ở chân trời
    if not nho:
        y = chan - 0.035 * s
        p.setBrush(QColor('#ECEFF1'))
        p.drawRect(QRectF(0.30 * s, y, 0.40 * s, 0.022 * s))
        p.setBrush(QColor('#B0BEC5'))
        for x in (0.34, 0.50, 0.66):
            p.drawRect(QRectF(x * s - 0.008 * s, y + 0.02 * s, 0.016 * s, 0.035 * s))
        # cột mốc GPMB
        for t in (0.30, 0.60, 0.92):
            y = chan + (s - chan) * t ** 1.7
            for ben in (-1, 1):
                x = 0.5 * s + ben * (0.10 + 0.43 * t ** 1.7) * s
                h = (0.04 + 0.12 * t) * s
                w = max(1.6, h * 0.24)
                p.setPen(QPen(QColor('#3E2723'), max(0.6, s * 0.004)))
                for j in range(3):
                    p.setBrush(QColor('#E53935') if j % 2 == 0 else TRANG)
                    p.drawRect(QRectF(x - w / 2, y - h + j * h / 3, w, h / 3))
        p.setPen(Qt.PenStyle.NoPen)
    # bóng sáng phía trên
    hl = QLinearGradient(0, 0, 0, 0.5 * s)
    hl.setColorAt(0, QColor(255, 255, 255, 55))
    hl.setColorAt(1, QColor(255, 255, 255, 0))
    p.setBrush(QBrush(hl))
    p.drawRect(QRectF(0, 0, s, 0.5 * s))
    # dải chữ PABT
    if s >= 48:
        r = QRectF(0.20 * s, 0.10 * s, 0.60 * s, 0.17 * s)
        p.setBrush(QColor(11, 46, 79, 215))
        p.setPen(QPen(QColor('#FFC107'), max(1.0, s * 0.010)))
        p.drawRoundedRect(r, 0.085 * s, 0.085 * s)
        f = QFont('Segoe UI', 1)
        f.setBold(True)
        f.setPixelSize(int(0.12 * s))
        f.setLetterSpacing(QFont.SpacingType.PercentageSpacing, 112)
        p.setFont(f)
        p.setPen(QColor('#FFE082'))
        p.drawText(r, Qt.AlignmentFlag.AlignCenter, 'PABT')
    p.setClipping(False)
    # viền
    p.setPen(QPen(QColor(255, 255, 255, 140), max(1.0, s * 0.010)))
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawPath(vo)
    p.end()
    return img


def png(img: QImage) -> bytes:
    ba = QByteArray()
    b = QBuffer(ba)
    b.open(QIODevice.OpenModeFlag.WriteOnly)
    img.save(b, 'PNG')
    return bytes(ba)


ANH_LOGO = Path(__file__).resolve().parent / 'logo_PABT.png'      # ảnh logo của đơn vị (nếu có thì dùng thay hình vẽ)
# chữ PABT của logo trên nền trắng sữa (đã tách khỏi ảnh nền đường / cây của logo_PABT.png) - có thì ưu tiên
ANH_LOGO_NEN_TRANG = ANH_LOGO.with_name('logo_PABT_nen_trang.png')


def ve_tu_anh(anh: QImage, s: int) -> QImage:
    """Biểu tượng s px từ ảnh logo: cắt vuông giữa ảnh (giữ phần chữ), thu nhỏ mịn, bo góc."""
    w, h = anh.width(), anh.height()
    canh = min(w, h)                                             # giữ trọn chữ PABT (chữ gần sát mép ảnh)
    vuong = anh.copy((w - canh) // 2, (h - canh) // 2, canh, canh)
    nho = vuong.scaled(s, s, Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.SmoothTransformation)
    img = QImage(s, s, QImage.Format.Format_ARGB32_Premultiplied)
    img.fill(Qt.GlobalColor.transparent)
    p = QPainter(img)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
    vo = QPainterPath()
    vo.addRoundedRect(QRectF(0, 0, s, s), 0.18 * s, 0.18 * s)
    p.setClipPath(vo)
    p.drawImage(0, 0, nho)
    p.end()
    return img


def main():
    app = QGuiApplication(sys.argv)  # noqa: F841 - giữ QGuiApplication sống để vẽ QImage / QFont
    goc = Path(__file__).resolve().parent / 'pabt'
    co = [16, 20, 24, 32, 40, 48, 64, 128, 256]
    nguon = Path(sys.argv[1]) if len(sys.argv) > 1 else (ANH_LOGO_NEN_TRANG if ANH_LOGO_NEN_TRANG.exists() else ANH_LOGO)
    if nguon.exists():
        anh = QImage(str(nguon))
        if anh.isNull():
            sys.exit(f'Không đọc được ảnh {nguon}')
        ve_ = lambda s: ve_tu_anh(anh, s)                        # noqa: E731
    else:
        ve_ = ve
    du = [png(ve_(s)) for s in co]
    dau = struct.pack('<HHH', 0, 1, len(co))
    off = 6 + 16 * len(co)
    muc = b''
    for s, d in zip(co, du):
        muc += struct.pack('<BBBBHHII', s % 256, s % 256, 0, 0, 1, 32, len(d), off)
        off += len(d)
    (goc / 'bieu_tuong.ico').write_bytes(dau + muc + b''.join(du))
    ve_(512).save(str(goc / 'bieu_tuong.png'))
    print('ok', goc / 'bieu_tuong.ico')


if __name__ == '__main__':
    main()

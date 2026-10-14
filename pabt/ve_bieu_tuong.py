"""Biểu tượng PABT (0.9.74: ảnh thiết kế Fluent Isometric 3D cắt / thu nhỏ nhiều cỡ; hình vẽ bằng mã `ve_mach` là dự phòng) (0.9.74 - người dùng 13/10/2026, nhận diện PABT Enterprise 2026): MỘT nguồn cho biểu tượng cửa
sổ / thanh tiêu đề / taskbar (vẽ đúng từng cỡ lúc chạy) và file .ico của exe, Desktop, bộ cài (tao_bieu_tuong.py gọi ve()).

Bố cục (ô vuông cạnh s, nền xanh navy #0F284E bo góc):
  - mái nhà an cư (vàng kim #F59E0B): chữ V ngược dày + mái trong mảnh - bồi thường tài sản, nhà ở, tái định cư;
  - thửa đất quy hoạch (xanh ngọc #107C41): khối đa giác bản đồ địa chính nhìn nghiêng có bề dày, ranh mốc vàng kim - mặt bằng sạch;
  - chữ PABT trắng + vạch chỉ thị vàng phía dưới.
Cỡ nhỏ giản lược để còn nhận ra: <= 24 px bỏ chữ và mái trong, phóng mái + thửa; 25-47 px bỏ chữ; từ 48 px đủ chi tiết.
"""
from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QImage, QLinearGradient, QPainter, QPainterPath, QPen, QPolygonF

NEN = QColor('#0F284E')             # deep navy - uy nghiêm, chính quy
NEN_SANG = QColor('#173B6D')        # đầu dải chuyển màu nền
VANG = QColor('#F59E0B')            # mái nhà, ranh mốc, vạch chỉ thị
XANH = QColor('#107C41')            # thửa đất
XANH_TOI = QColor('#0B5A2F')        # bề dày (mặt bên) của thửa
TRANG = QColor('#FFFFFF')
BO_GOC = 0.21                       # bán kính bo góc (tỷ lệ cạnh)
CO_ICO = (16, 20, 24, 32, 40, 48, 64, 128, 256)


def ve_mach(s: int) -> QImage:
    """Hình vẽ bằng mã (dự phòng khi thiếu pabt/bieu_tuong.png), cạnh s px, nền trong suốt ngoài góc bo."""
    img = QImage(s, s, QImage.Format.Format_ARGB32_Premultiplied)
    img.fill(Qt.GlobalColor.transparent)
    p = QPainter(img)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setRenderHint(QPainter.RenderHint.TextAntialiasing)
    vo = QPainterPath()
    vo.addRoundedRect(QRectF(0, 0, s, s), BO_GOC * s, BO_GOC * s)
    g = QLinearGradient(0, 0, 0, s)
    g.setColorAt(0.0, NEN_SANG)
    g.setColorAt(1.0, NEN)
    p.fillPath(vo, g)
    nho, vua = s <= 24, s < 48
    if nho:                                     # chỉ mái + thửa, phóng to chiếm gần cả ô
        mai_dinh, mai_chan, mai_rong, thua_y, thua_h, thua_w = 0.10, 0.50, 0.84, 0.70, 0.30, 0.86
    elif vua:
        mai_dinh, mai_chan, mai_rong, thua_y, thua_h, thua_w = 0.12, 0.47, 0.78, 0.68, 0.28, 0.80
    else:
        mai_dinh, mai_chan, mai_rong, thua_y, thua_h, thua_w = 0.10, 0.40, 0.66, 0.555, 0.22, 0.70
    cx = s / 2
    # ---- thửa đất: hình thoi nhìn nghiêng (mặt trên xanh ngọc) + bề dày mặt bên tối hơn + ranh mốc vàng
    day = max(1.0, (0.035 if not nho else 0.05) * s)
    tren = QPolygonF([QPointF(cx, (thua_y - thua_h / 2) * s), QPointF(cx + thua_w / 2 * s, thua_y * s),
                      QPointF(cx, (thua_y + thua_h / 2) * s), QPointF(cx - thua_w / 2 * s, thua_y * s)])
    ben = QPolygonF([tren[3], tren[2], tren[1], QPointF(tren[1].x(), tren[1].y() + day),
                     QPointF(tren[2].x(), tren[2].y() + day), QPointF(tren[3].x(), tren[3].y() + day)])
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(XANH_TOI)
    p.drawPolygon(ben)
    p.setBrush(XANH)
    p.drawPolygon(tren)
    net_ranh = max(1.0, (0.018 if not nho else 0.045) * s)
    p.setPen(QPen(VANG, net_ranh, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawPolygon(tren)
    if not nho:                                 # đường ranh chia thửa (lưới địa chính) + mốc ở các đỉnh
        p.setPen(QPen(QColor(245, 158, 11, 150), max(1.0, 0.009 * s)))
        p.drawLine(QPointF((tren[0].x() + tren[1].x()) / 2, (tren[0].y() + tren[1].y()) / 2),
                   QPointF((tren[3].x() + tren[2].x()) / 2, (tren[3].y() + tren[2].y()) / 2))
        r = max(1.2, 0.022 * s)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(VANG)
        for d in tren:
            p.drawEllipse(d, r, r)
    # ---- mái nhà an cư: mái ngoài dày (chữ V ngược) + mái trong mảnh
    net_mai = max(1.6, (0.085 if not nho else 0.13) * s)
    mai = QPainterPath()
    mai.moveTo(cx - mai_rong / 2 * s, mai_chan * s)
    mai.lineTo(cx, mai_dinh * s)
    mai.lineTo(cx + mai_rong / 2 * s, mai_chan * s)
    p.setPen(QPen(VANG, net_mai, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.MiterJoin))
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawPath(mai)
    if not nho:
        trong = QPainterPath()
        k = 0.42                                 # mái trong: nhỏ hơn, thấp hơn
        trong.moveTo(cx - mai_rong * k / 2 * s, mai_chan * s + 0.02 * s)
        trong.lineTo(cx, (mai_dinh + (mai_chan - mai_dinh) * 0.52) * s)
        trong.lineTo(cx + mai_rong * k / 2 * s, mai_chan * s + 0.02 * s)
        p.setPen(QPen(VANG, max(1.0, 0.04 * s), Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.MiterJoin))
        p.drawPath(trong)
    # ---- chữ PABT + vạch chỉ thị (từ 48 px)
    if not vua:
        f = QFont('Segoe UI')
        f.setBold(True)
        f.setPixelSize(max(6, round(0.175 * s)))
        f.setLetterSpacing(QFont.SpacingType.PercentageSpacing, 108)
        p.setFont(f)
        p.setPen(TRANG)
        p.drawText(QRectF(0, 0.69 * s, s, 0.20 * s), int(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter), 'PABT')
        vach_w, vach_h = 0.30 * s, max(1.0, 0.022 * s)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(VANG)
        p.drawRoundedRect(QRectF(cx - vach_w / 2, 0.895 * s, vach_w, vach_h), vach_h / 2, vach_h / 2)
    # viền mảnh sáng: tách biểu tượng khỏi nền taskbar / Desktop tối
    p.setPen(QPen(QColor(255, 255, 255, 40), max(1.0, 0.012 * s)))
    p.setBrush(Qt.BrushStyle.NoBrush)
    m = max(0.5, 0.006 * s)
    vien = QPainterPath()
    vien.addRoundedRect(QRectF(m, m, s - 2 * m, s - 2 * m), BO_GOC * s - m, BO_GOC * s - m)
    p.drawPath(vien)
    p.end()
    return img


# ---------------------------------------------------------------- biểu tượng từ ảnh thiết kế (0.9.74 - Fluent Isometric 3D)
KHUNG = (170, 853)                  # khung squircle trong ảnh thiết kế 1024 px (bỏ hào quang ngoài khung)


def cat_squircle(anh: QImage, canh: int = 512) -> QImage:
    """Cắt khung squircle của ảnh thiết kế 1024 x 1024, bo góc cho trong suốt, thu về canh x canh."""
    k = anh.width() / 1024
    a, b = round(KHUNG[0] * k), round(KHUNG[1] * k)
    vuong = anh.copy(a, a, b - a, b - a).convertToFormat(QImage.Format.Format_ARGB32_Premultiplied)
    ra = QImage(vuong.size(), QImage.Format.Format_ARGB32_Premultiplied)
    ra.fill(Qt.GlobalColor.transparent)
    p = QPainter(ra)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    vo = QPainterPath()
    vo.addRoundedRect(QRectF(0, 0, vuong.width(), vuong.height()), BO_GOC * vuong.width(), BO_GOC * vuong.width())
    p.setClipPath(vo)
    p.drawImage(0, 0, vuong)
    p.end()
    return thu_nho_muot(ra, canh)


def thu_nho_muot(anh: QImage, s: int) -> QImage:
    """Thu nhỏ từng nấc 1/2 rồi về đúng cỡ (mịn, không răng cưa ở 16-32 px)."""
    while anh.width() > 2 * s:
        anh = anh.scaled(anh.width() // 2, anh.height() // 2, Qt.AspectRatioMode.IgnoreAspectRatio,
                         Qt.TransformationMode.SmoothTransformation)
    return anh.scaled(s, s, Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.SmoothTransformation)


_GOC = []


def goc() -> QImage | None:
    """Ảnh biểu tượng 512 px (pabt/bieu_tuong.png, tao_bieu_tuong.py xuất từ ảnh thiết kế); None nếu thiếu."""
    if not _GOC:
        from . import tai_nguyen
        a = QImage(str(tai_nguyen('bieu_tuong.png')))
        _GOC.append(None if a.isNull() else a.convertToFormat(QImage.Format.Format_ARGB32_Premultiplied))
    return _GOC[0]


def ve(s: int) -> QImage:
    """Biểu tượng cạnh s px: từ ảnh thiết kế; thiếu ảnh thì vẽ bằng mã."""
    g = goc()
    return thu_nho_muot(g, s) if g is not None else ve_mach(s)


def icon():
    """QIcon nhiều cỡ vẽ sẵn (Windows chọn đúng cỡ cho taskbar / thanh tiêu đề / Alt+Tab - không thu nhỏ ảnh lớn)."""
    from PySide6.QtGui import QIcon, QPixmap
    ic = QIcon()
    for s in (*CO_ICO, 512):
        ic.addPixmap(QPixmap.fromImage(ve(s)))
    return ic

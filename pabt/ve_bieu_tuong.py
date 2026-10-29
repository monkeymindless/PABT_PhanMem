"""Biểu tượng PABT: MỘT nguồn cho biểu tượng cửa sổ / thanh tiêu đề / taskbar (vẽ đúng từng cỡ lúc chạy) và file .ico của exe,
Desktop, bộ cài.

0.9.87 (người dùng 15/10/2026) "Mẫu 3 - Lăng kính công lý & nhịp cầu đồng thuận": ảnh thiết kế `bieu_tuong_thiet_ke.webp` (khối squircle
pha lê xanh băng nhìn nghiêng 3D, nhịp cầu vàng hổ phách, cán cân pha lê, dấu tích cam, chữ PABT trắng viền vàng) -> `tao_bieu_tuong.py`
(tách nền, KHÔNG gói vào bản phát hành) -> `bieu_tuong.png` 512 + `bieu_tuong.ico`. Lúc chạy chỉ đọc `bieu_tuong.png` (`goc`, `ve`,
`icon`); `ve_mach` vẽ bằng mã là dự phòng khi thiếu file (cùng bảng màu; <= 24 px bỏ lưới, chữ; < 48 px bỏ chữ).
"""
from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QBrush, QColor, QFont, QImage, QLinearGradient, QPainter, QPainterPath, QPen

# Mẫu 3 (0.9.87): pha lê xanh băng sáng + trắng sứ + vàng cam hổ phách (bỏ nền navy đậm cũ)
NEN = QColor('#38BDF8')             # xanh lam băng sáng - cuối dải chuyển sắc mặt trong
NEN_SANG = QColor('#F0F9FF')        # trắng sứ băng - đầu dải chuyển sắc
VIEN_SANG = QColor('#F8FAFC')       # viền ngoài trắng ngọc trai
VIEN_TOI = QColor('#BAE6FD')        # viền ngoài pha xanh băng
XANH_DAM = QColor('#0284C7')        # đường viền mặt trong
VANG = QColor('#F59E0B')            # nhịp cầu, viền chữ
VANG_SANG = QColor('#FACC15')       # cáp cầu, đầu dải dấu tích
CAM = QColor('#F97316')             # dấu tích đồng thuận
TRANG = QColor('#FFFFFF')
BO_GOC = 0.21                       # bán kính bo góc (tỷ lệ cạnh)
CO_ICO = (16, 20, 24, 32, 40, 48, 64, 128, 256)


def ve_mach(s: int) -> QImage:
    """Hình vẽ bằng mã (dự phòng khi thiếu pabt/bieu_tuong.png), cạnh s px, nền trong suốt ngoài góc bo - Mẫu 3 (0.9.87): squircle
    pha lê xanh băng sáng, lưới CAD mờ, nhịp cầu vàng hổ phách, dấu tích đồng thuận cam vàng, chữ PABT trắng viền vàng."""
    img = QImage(s, s, QImage.Format.Format_ARGB32_Premultiplied)
    img.fill(Qt.GlobalColor.transparent)
    p = QPainter(img)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setRenderHint(QPainter.RenderHint.TextAntialiasing)
    nho, vua = s <= 24, s < 48
    # ---- khối squircle: viền ngoài trắng ngọc trai pha xanh băng, mặt trong chuyển sắc trắng sứ -> xanh băng
    vo = QPainterPath()
    vo.addRoundedRect(QRectF(0, 0, s, s), BO_GOC * s, BO_GOC * s)
    g = QLinearGradient(0, 0, s, s)
    g.setColorAt(0.0, VIEN_SANG)
    g.setColorAt(1.0, VIEN_TOI)
    p.fillPath(vo, g)
    m = (0.07 if not nho else 0.06) * s
    trong = QPainterPath()
    trong.addRoundedRect(QRectF(m, m, s - 2 * m, s - 2 * m), BO_GOC * (s - 2 * m), BO_GOC * (s - 2 * m))
    g = QLinearGradient(0, m, 0, s - m)
    g.setColorAt(0.0, NEN_SANG)
    g.setColorAt(1.0, NEN)
    p.fillPath(trong, g)
    p.setPen(QPen(XANH_DAM, max(1.0, 0.018 * s)))
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawPath(trong)
    if not vua:                                 # lưới tọa độ CAD mờ
        p.save()
        p.setClipPath(trong)
        p.setPen(QPen(QColor(255, 255, 255, 110), max(1.0, 0.006 * s)))
        for k in range(1, 6):
            t = m + k * (s - 2 * m) / 6
            p.drawLine(QPointF(t, m), QPointF(t, s - m))
            p.drawLine(QPointF(m, t), QPointF(s - m, t))
        p.restore()
    # ---- nhịp cầu vàng hổ phách: hai trụ + vòm cáp
    day_cau = max(1.4, (0.06 if not nho else 0.09) * s)
    but = QPen(VANG, day_cau, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
    p.setPen(but)
    mat_cau = 0.52 if not vua else 0.60
    p.drawLine(QPointF(0.18 * s, mat_cau * s), QPointF(0.84 * s, (mat_cau - 0.06) * s))
    for x in (0.30, 0.48):
        p.drawLine(QPointF(x * s, (mat_cau + 0.04) * s), QPointF((x + 0.04) * s, 0.18 * s))
    vom = QPainterPath()
    vom.moveTo(0.16 * s, (mat_cau - 0.02) * s)
    vom.quadTo(0.40 * s, 0.12 * s, 0.84 * s, 0.30 * s)
    p.setPen(QPen(VANG_SANG, max(1.0, day_cau * 0.6), Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
    p.drawPath(vom)
    # ---- dấu tích đồng thuận cam -> vàng
    tich = QPainterPath()
    tich.moveTo(0.56 * s, 0.38 * s)
    tich.lineTo(0.64 * s, 0.47 * s)
    tich.lineTo(0.80 * s, 0.24 * s)
    gt = QLinearGradient(0.56 * s, 0.47 * s, 0.80 * s, 0.24 * s)
    gt.setColorAt(0.0, CAM)
    gt.setColorAt(1.0, VANG_SANG)
    p.setPen(QPen(QBrush(gt), max(1.6, (0.075 if not nho else 0.11) * s), Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap,
                  Qt.PenJoinStyle.RoundJoin))
    p.drawPath(tich)
    # ---- chữ PABT trắng viền vàng (từ 48 px)
    if not vua:
        f = QFont('Segoe UI')
        f.setBold(True)
        f.setPixelSize(max(6, round(0.20 * s)))
        chu = QPainterPath()
        chu.addText(0, 0, f, 'LARC')
        r = chu.boundingRect()
        chu.translate(s / 2 - r.center().x(), 0.80 * s - r.center().y())
        p.setPen(QPen(VANG, max(1.0, 0.014 * s), Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
        p.setBrush(TRANG)
        p.drawPath(chu)
    p.end()
    return img


# ---------------------------------------------------------------- biểu tượng từ ảnh (bieu_tuong.png - tao_bieu_tuong.py)
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


# ---------------------------------------------------------------- 1.0.34: hình minh họa vector hai tông (bảng / bản đồ chưa có dữ liệu)
LOAI_MINH_HOA = ('bang', 'ban_do', 'ho', 'tai_lieu')
MAU_MINH_HOA = '#2563EB'


def ve_minh_hoa_trong(loai: str, co: int = 96, mau: str = MAU_MINH_HOA):
    """QPixmap co x co: hình nền mờ (alpha 42) + nét chính 2 px + chấm sáng điểm nhấn. loai: 'bang' (bảng dữ liệu), 'ban_do' (bản đồ
    thửa), 'ho' (hộ dân), 'tai_lieu' (văn bản); loại lạ = 'bang'. Vẽ bằng QPainter (không cần phông biểu tượng - chạy cả Windows 7)."""
    from PySide6.QtGui import QPixmap
    pm = QPixmap(co, co)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    k = co / 96.0
    nen = QColor(mau)
    nen.setAlpha(42)
    net = QPen(QColor(mau), 2.0 * k)
    net.setCapStyle(Qt.PenCapStyle.RoundCap)
    net.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(nen)
    p.drawEllipse(QRectF(8 * k, 8 * k, 80 * k, 80 * k))              # nền tròn mờ
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.setPen(net)
    if loai == 'ban_do':
        thua = [[(24, 30), (50, 24), (54, 50), (28, 56)], [(50, 24), (74, 32), (70, 58), (54, 50)],
                [(28, 56), (54, 50), (58, 74), (32, 72)]]
        for d in thua:
            path = QPainterPath(QPointF(d[0][0] * k, d[0][1] * k))
            for x, y in d[1:]:
                path.lineTo(x * k, y * k)
            path.closeSubpath()
            p.drawPath(path)
        cham = (54, 50)
    elif loai == 'ho':
        p.drawEllipse(QRectF(38 * k, 24 * k, 20 * k, 20 * k))
        path = QPainterPath(QPointF(28 * k, 72 * k))
        path.cubicTo(28 * k, 52 * k, 68 * k, 52 * k, 68 * k, 72 * k)
        p.drawPath(path)
        cham = (64, 30)
    elif loai == 'tai_lieu':
        path = QPainterPath(QPointF(30 * k, 20 * k))
        for x, y in ((58, 20), (68, 30), (68, 76), (30, 76)):
            path.lineTo(x * k, y * k)
        path.closeSubpath()
        p.drawPath(path)
        for y in (40, 50, 60):
            p.drawLine(QPointF(38 * k, y * k), QPointF(60 * k, y * k))
        cham = (58, 20)
    else:                                                             # bảng
        p.drawRoundedRect(QRectF(22 * k, 26 * k, 52 * k, 44 * k), 5 * k, 5 * k)
        p.drawLine(QPointF(22 * k, 38 * k), QPointF(74 * k, 38 * k))
        for y in (50, 60):
            p.drawLine(QPointF(30 * k, y * k), QPointF(66 * k, y * k))
        p.drawLine(QPointF(40 * k, 38 * k), QPointF(40 * k, 70 * k))
        cham = (74, 26)
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor('#38BDF8'))                                      # chấm sáng điểm nhấn
    p.drawEllipse(QPointF(cham[0] * k, cham[1] * k), 4.5 * k, 4.5 * k)
    p.setBrush(QColor(255, 255, 255, 220))
    p.drawEllipse(QPointF(cham[0] * k - 1.2 * k, cham[1] * k - 1.2 * k), 1.5 * k, 1.5 * k)
    p.end()
    return pm

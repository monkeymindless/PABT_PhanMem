"""Bảng có khung kẻ trên ảnh scan (người dùng 30/10/2026: "công cụ scan chính xác hơn, phân tách nội dung rõ ràng hơn").

Trước đây cột bảng scan đoán theo khoảng trắng giữa các chữ (ocr.gom_dong): ô gộp nhiều hàng (STT, tên nhóm loài cây), cột hẹp, chữ
xuống dòng trong ô làm lệch cột - bảng đơn giá cây trồng bản scan đọc ra 850 dòng chữ nhưng chỉ ghép được 2 mục giá. Nay dò ĐƯỜNG KẺ
ngang / dọc của khung bảng trên ảnh trang (đếm điểm tối từng hàng / cột ảnh - chỉ Qt, không thư viện ngoài), xóa nét kẻ trước khi
Tesseract đọc (nét kẻ hay bị đọc thành "|", "I", "1"), rồi đặt từng chữ vào ô theo tọa độ:
  - ô gộp ngang (thiếu vạch dọc trong hàng): chữ vào cột đầu của ô gộp;
  - ô gộp dọc (thiếu vạch ngang giữa hai hàng): chữ cả vùng gộp về hàng TRÊN CÙNG của vùng (dòng "cha" / dòng đầu nhóm);
  - chữ nhiều dòng trong một ô nối lại thành một ô;
  - hàng không có vạch dọc bên trong (tiêu đề, chữ giữa hai bảng) và chữ ngoài khung: dòng chữ thường.
Không thấy khung (bảng không kẻ, đoạn văn): trả None - nơi gọi dùng cách cũ."""
from __future__ import annotations
from dataclasses import dataclass, field

NGUONG_TOI = 160            # điểm ảnh xám < ngưỡng = mực (nét kẻ, chữ)
TY_LE_NGANG = 0.35          # hàng ảnh có >= 35% bề rộng là mực -> nét kẻ ngang (dòng chữ dày đặc nhất ~20%)
TY_LE_DOC = 0.30            # cột ảnh có >= 30% chiều cao khung bảng là mực -> nét kẻ dọc
CO_MAT_TRONG_DAI = 0.55     # vạch có mặt trong một đoạn khi >= 55% đoạn đó là mực (vạch scan đứt, mờ)
GOP_NET = 6                 # px: các hàng / cột mực liền nhau trong khoảng này là một nét
KHE_TOI_THIEU = 12          # px: hai vạch gần hơn mức này coi là một (nét đôi, khung dày)


@dataclass
class Luoi:
    ngang: list                 # [(tâm y, dày)] các vạch ngang từ trên xuống
    doc: list                   # [(tâm x, dày)] các vạch dọc từ trái sang
    rong: int = 0
    cao: int = 0
    # co_doc[b][j]: vạch dọc j có mặt trong dải hàng b (giữa vạch ngang b và b + 1); co_ngang[b][j]: vạch ngang b có mặt trên đoạn
    # cột j (giữa vạch dọc j và j + 1)
    co_doc: list = field(default_factory=list)
    co_ngang: list = field(default_factory=list)
    x_dai: list = field(default_factory=list)       # x_dai[b][j]: tâm thật của vạch dọc j trong dải b


def _bang_toi() -> bytes:
    return bytes(1 if i < NGUONG_TOI else 0 for i in range(256))


_TOI = _bang_toi()


def _byte_anh(im) -> tuple:
    """(bytes điểm ảnh xám, số byte mỗi hàng) - PySide6 / PySide2 trả kiểu bộ nhớ khác nhau."""
    b = im.constBits()
    try:
        du_lieu = bytes(b)
    except TypeError:                                   # PySide2: voidptr cần đặt cỡ trước
        b.setsize(im.sizeInBytes())
        du_lieu = bytes(b)
    return du_lieu[:im.bytesPerLine() * im.height()], im.bytesPerLine()


def _gom(vt: list) -> list:
    """Các chỉ số hàng / cột mực liền nhau -> [(tâm, dày)]."""
    kq, dau, truoc = [], None, None
    for i in vt:
        if dau is None:
            dau = truoc = i
        elif i - truoc <= GOP_NET:
            truoc = i
        else:
            kq.append(((dau + truoc) / 2, truoc - dau + 1))
            dau = truoc = i
    if dau is not None:
        kq.append(((dau + truoc) / 2, truoc - dau + 1))
    gon = []
    for t, d in kq:                                     # nét đôi / khung dày: gộp vạch quá gần
        if gon and t - gon[-1][0] < KHE_TOI_THIEU:
            gon[-1] = ((gon[-1][0] + t) / 2, gon[-1][1] + d)
        else:
            gon.append((t, d))
    return gon


def _dem_hang(du_lieu: bytes, buoc: int, rong: int, tu: int, den: int, x1: int = 0, x2: int | None = None) -> list:
    x2 = rong if x2 is None else x2
    return [du_lieu[y * buoc + x1:y * buoc + x2].translate(_TOI).count(1) for y in range(tu, den)]


CUA_SO_NGHIENG = 0.006      # ảnh scan nghiêng ~0,3°: vạch dài L điểm ảnh trôi L x 0,006 điểm -> gộp chừng ấy hàng / cột khi đếm


def _dem_nghieng(du_lieu: bytes, buoc: int, rong: int, cao: int, cs: int) -> list:
    """Số điểm mực mỗi hàng khi gộp (OR) cs hàng liền nhau - vạch kẻ hơi nghiêng chỉ nằm một phần trên mỗi hàng ảnh. Dùng số
    nguyên lớn làm dãy bit (nhanh, không cần numpy); kết quả gán cho hàng giữa của cửa sổ."""
    if cs <= 1:
        return _dem_hang(du_lieu, buoc, rong, 0, cao)
    hang = [int.from_bytes(du_lieu[y * buoc:y * buoc + rong].translate(_TOI), 'big') for y in range(cao)]
    kq = [0] * cao
    for y in range(cao):
        a, b = max(0, y - cs // 2), min(cao, y + cs // 2 + 1)
        v = 0
        for k in range(a, b):
            v |= hang[k]
        kq[y] = v.to_bytes(rong, 'big').count(1)
    return kq


def _ty_le_doan(du_lieu: bytes, buoc: int, y: float, day: float, x1: int, x2: int) -> float:
    """Tỷ lệ mực trên đoạn ngang [x1, x2) tại vạch y (lấy hàng tối nhất trong bề dày vạch +-2)."""
    if x2 <= x1:
        return 0.0
    tot = 0
    for yy in range(max(0, int(y - day / 2) - 2), int(y + day / 2) + 3):
        o = du_lieu[yy * buoc + x1:yy * buoc + x2]
        if len(o) == x2 - x1:
            tot = max(tot, o.translate(_TOI).count(1))
    return tot / (x2 - x1)


VET_NGANG = 0.02            # vạch ngang: chỉ đếm đoạn mực liền dài >= 2% bề rộng ảnh (tối thiểu VET_TOI_THIEU_PX)
VET_DOC = 0.032             # vạch dọc: >= 3,2% bề rộng ảnh (~80 điểm ảnh ở 300 dpi, cao hơn một dòng chữ có dấu - nét chữ ngắn)
VET_TOI_THIEU_PX = 40
CUA_SO_NGANG = 3            # sau khi xoay thẳng, vạch ngang lệch còn 1-2 hàng ảnh
NGHIENG_TOI_DA = 2.0        # độ: ảnh nghiêng hơn mức này không tự xoay (có thể là bảng xoay, ảnh chụp méo)


def _dem_vet(du_lieu: bytes, buoc: int, rong: int, cao: int, dai: int, cs: int = 1) -> list:
    """Mỗi hàng ảnh (gộp OR cs hàng liền nhau - vạch hơi nghiêng): tổng độ dài các đoạn mực liền >= dai điểm. Chữ cái không tạo
    đoạn dài như vạch kẻ: cột chữ thẳng hàng ("Năm 1", "Năm 2"... đầu mỗi hàng) đứt ở khoảng trắng giữa các dòng chữ."""
    hang = [du_lieu[y * buoc:y * buoc + rong].translate(_TOI) for y in range(cao)]
    if cs > 1:
        so = [int.from_bytes(h, 'big') for h in hang]
        hang = []
        for y in range(cao):
            v = 0
            for k in range(max(0, y - cs // 2), min(cao, y + cs // 2 + 1)):
                v |= so[k]
            hang.append(v.to_bytes(rong, 'big'))
    return [sum(len(d) for d in r.split(b'\x00') if len(d) >= dai) for r in hang]


def goc_nghieng(im) -> float:
    """Góc nghiêng (độ, chiều kim đồng hồ dương) của ảnh scan theo các vạch kẻ ngang dài: chia mỗi vạch thành 8 đoạn, tìm tâm y từng
    đoạn rồi lấy độ dốc; trung vị các vạch. Không thấy vạch: 0."""
    import math
    from PySide6.QtGui import QImage
    if im.format() != QImage.Format.Format_Grayscale8:
        im = im.convertToFormat(QImage.Format.Format_Grayscale8)
    rong, cao = im.width(), im.height()
    if rong < 200 or cao < 200:
        return 0.0
    du_lieu, buoc = _byte_anh(im)
    cs = max(1, int(rong * CUA_SO_NGHIENG))
    dem = _dem_nghieng(du_lieu, buoc, rong, cao, cs)
    ngang = [(y, d) for y, d in _gom([y for y, n in enumerate(dem) if n >= TY_LE_NGANG * rong]) if GOP_NET < y < cao - GOP_NET]
    doan = rong // 8
    doc_ds = []
    for y, d in ngang:
        ya, yb = max(0, int(y - d / 2) - cs), min(cao, int(y + d / 2) + cs + 1)
        diem = []
        for k in range(8):
            xa = k * doan
            ds = _dem_hang(du_lieu, buoc, rong, ya, yb, xa, xa + doan)
            m = max(ds) if ds else 0
            if m < 0.6 * doan:
                continue
            hang = [(ya + i, n) for i, n in enumerate(ds) if n >= 0.5 * m]
            tong = sum(n for _, n in hang)
            diem.append((xa + doan / 2, sum(yy * n for yy, n in hang) / tong))
        if len(diem) >= 4:
            mx = sum(x for x, _ in diem) / len(diem)
            my = sum(v for _, v in diem) / len(diem)
            mau = sum((x - mx) ** 2 for x, _ in diem)
            if mau:
                doc_ds.append(sum((x - mx) * (v - my) for x, v in diem) / mau)
    if not doc_ds:
        return 0.0
    doc_ds.sort()
    return math.degrees(math.atan(doc_ds[len(doc_ds) // 2]))


def xoay_thang(im, goc: float):
    """Ảnh xám mới xoay ngược góc nghiêng quanh tâm (phần lộ ra tô trắng)."""
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QImage, QPainter
    moi = QImage(im.size(), QImage.Format.Format_RGB32)
    moi.fill(Qt.GlobalColor.white)
    p = QPainter(moi)
    p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
    p.translate(im.width() / 2, im.height() / 2)
    p.rotate(-goc)
    p.translate(-im.width() / 2, -im.height() / 2)
    p.drawImage(0, 0, im)
    p.end()
    return moi.convertToFormat(QImage.Format.Format_Grayscale8)


def tim_luoi(im) -> Luoi | None:
    """Khung bảng trên ảnh xám đã xoay thẳng (QImage Format_Grayscale8). Cần ít nhất 3 vạch ngang và 2 vạch dọc; không có: None.
    Hàng / cột chỉ đếm các đoạn mực liền dài (VET_NGANG / VET_DOC): cột chữ thẳng hàng ("Năm 1", "Năm 2"... đầu mỗi hàng) không thành
    vạch. Vạch dọc của bản scan hay xiên khác vạch ngang (giấy trượt khi quét) - đếm gộp cửa sổ CUA_SO_NGHIENG, vị trí thật của vạch từng
    dải hàng ghi ở Luoi.x_dai."""
    from PySide6.QtGui import QImage, QTransform
    if im.format() != QImage.Format.Format_Grayscale8:
        im = im.convertToFormat(QImage.Format.Format_Grayscale8)
    rong, cao = im.width(), im.height()
    if rong < 200 or cao < 200:
        return None
    du_lieu, buoc = _byte_anh(im)
    dem = _dem_vet(du_lieu, buoc, rong, cao, max(VET_TOI_THIEU_PX, int(rong * VET_NGANG)), CUA_SO_NGANG)
    ngang = _gom([y for y, n in enumerate(dem) if n >= TY_LE_NGANG * rong])
    # viền đen mép ảnh scan (khung trang) không phải vạch bảng
    ngang = [(y, d) for y, d in ngang if GOP_NET < y < cao - GOP_NET]
    if len(ngang) < 3:
        return None
    y1, y2 = int(ngang[0][0]), int(ngang[-1][0])
    xoay = im.copy(0, y1, rong, y2 - y1 + 1).transformed(QTransform().rotate(90)).convertToFormat(QImage.Format.Format_Grayscale8)
    du_x, buoc_x = _byte_anh(xoay)
    dem_x = _dem_vet(du_x, buoc_x, xoay.width(), xoay.height(), max(VET_TOI_THIEU_PX, int(rong * VET_DOC)),
                     max(1, int((y2 - y1) * CUA_SO_NGHIENG)))
    # ảnh xoay 90° theo chiều kim đồng hồ: hàng i của ảnh xoay = cột i của ảnh gốc
    doc = _gom([x for x, n in enumerate(dem_x) if n >= TY_LE_DOC * (y2 - y1 + 1)])
    doc = [(x, d) for x, d in doc if GOP_NET < x < rong - GOP_NET]
    if len(doc) < 2:
        return None
    luoi = Luoi(ngang, doc, rong, cao)
    # vạch dọc có mặt từng dải hàng / vạch ngang có mặt từng đoạn cột (ô gộp)
    for b in range(len(ngang) - 1):
        ya, yb = int(ngang[b][0] + ngang[b][1] / 2) + 1, int(ngang[b + 1][0] - ngang[b + 1][1] / 2)
        hang, vt = [], []
        for x, d in doc:
            if yb - ya < 4:
                hang.append(True)
                vt.append(x)
                continue
            # cột ảnh tối nhất quanh vạch trong dải này (vạch xiên: mỗi dải lệch một ít)
            xa, xb = max(0, int(x - d / 2) - 2), min(rong, int(x + d / 2) + 3)
            cot = [0] * (xb - xa)
            for y in range(ya, yb):
                r = du_lieu[y * buoc + xa:y * buoc + xb]
                for i, v in enumerate(r):
                    if v < NGUONG_TOI:
                        cot[i] += 1
            # nét scan dày 2-4 điểm ảnh: lấy cửa sổ 3 cột liền tối nhất
            ba = [max(cot[i:i + 3]) for i in range(max(1, len(cot) - 2))]
            i = max(range(len(ba)), key=ba.__getitem__)
            hang.append(ba[i] >= CO_MAT_TRONG_DAI * (yb - ya))
            vt.append(xa + i + 1)
        luoi.co_doc.append(hang)
        luoi.x_dai.append(vt)
    for y, d in ngang:
        luoi.co_ngang.append([_ty_le_doan(du_lieu, buoc, y, d, int(doc[j][0]) + 2, int(doc[j + 1][0]) - 2) >= CO_MAT_TRONG_DAI
                              for j in range(len(doc) - 1)])
    return luoi


def nhan_khung(im):
    """(ảnh đã xoay thẳng + xóa nét kẻ, Luoi) cho ảnh trang scan; không có khung bảng: (None, None)."""
    from PySide6.QtGui import QImage
    if im.format() != QImage.Format.Format_Grayscale8:
        im = im.convertToFormat(QImage.Format.Format_Grayscale8)
    goc = goc_nghieng(im)
    if 0.03 < abs(goc) <= NGHIENG_TOI_DA:
        im = xoay_thang(im, goc)
    luoi = tim_luoi(im)
    if luoi is None:
        return None, None
    return xoa_net_ke(im, luoi), luoi


def xoa_net_ke(im, luoi: Luoi):
    """Ảnh mới: tô trắng các vạch kẻ (Tesseract không đọc nét kẻ thành "|" / "I" / "1", chữ sát vạch tách rõ hơn). Chỉ tô đoạn vạch có
    thật: ô gộp (vạch vắng) có chữ chạy qua chỗ đó, tô cả vạch thì mất chữ."""
    from PySide6.QtGui import QColor, QPainter
    moi = im.copy()
    p = QPainter(moi)
    trang = QColor(255, 255, 255)
    doc, ngang = luoi.doc, luoi.ngang
    for b, (y, d) in enumerate(ngang):
        for j in range(len(doc) - 1):
            if luoi.co_ngang[b][j]:
                xa = int(doc[j][0] - doc[j][1] / 2) - 3
                xb = int(doc[j + 1][0] + doc[j + 1][1] / 2) + 3
                p.fillRect(xa, int(y - d / 2) - 2, xb - xa, int(d) + 5, trang)
    for b in range(len(ngang) - 1):
        ya = int(ngang[b][0] - ngang[b][1] / 2) - 2
        yb = int(ngang[b + 1][0] + ngang[b + 1][1] / 2) + 3
        for j, x in enumerate(luoi.x_dai[b] if b < len(luoi.x_dai) else [x for x, _ in doc]):
            if luoi.co_doc[b][j]:
                p.fillRect(int(x) - 4, ya, 9, yb - ya, trang)
    p.end()
    return moi


def _noi_chu(tu: list) -> str:
    """Các từ trong một ô -> chữ (dòng trên trước, trong dòng trái sang phải; nhiều dòng nối bằng dấu cách)."""
    from .ocr import gom_hang
    chu = ' '.join(' '.join(t for _, _, _, t in hg) for hg in gom_hang(tu)).split()
    while chu and chu[-1] in ('(', '|', '[', ';'):           # mẩu nét kẻ / bóng mép giấy cuối ô
        chu.pop()
    while chu and chu[0] in (')', '|', ']'):
        chu.pop(0)
    return ' '.join(chu)


def _dau_vung(luoi: Luoi) -> list:
    """dau[b][j]: dải trên cùng của ô gộp dọc chứa ô (b, j) - ô nối ô trên khi vạch ngang b vắng trên đoạn cột j."""
    so_dai, so_cot = len(luoi.ngang) - 1, len(luoi.doc) - 1
    dau = [[b] * so_cot for b in range(so_dai)]
    for b in range(1, so_dai):
        for j in range(so_cot):
            if not luoi.co_ngang[b][j]:
                dau[b][j] = dau[b - 1][j]
    return dau


def vung_gop(luoi: Luoi) -> list:
    """Các ô gộp (nhiều dải hàng hoặc nhiều cột) [(x1, y1, x2, y2)] trong tọa độ ảnh: Tesseract đọc cả trang hay lẫn dòng chữ của ô gộp
    cao (tên nhóm loài cây hai dòng nằm giữa 14 hàng giá) với dòng số của cột bên cạnh -> nơi gọi đọc lại riêng từng vùng."""
    so_dai, so_cot = len(luoi.ngang) - 1, len(luoi.doc) - 1
    if so_dai < 1 or so_cot < 1:
        return []
    dau = _dau_vung(luoi)
    kq = []
    for b in range(so_dai):
        for j in range(so_cot):
            if dau[b][j] != b or (j > 0 and not luoi.co_doc[b][j]):
                continue                                # không phải góc trên trái của ô
            j2 = j + 1
            while j2 < so_cot and not luoi.co_doc[b][j2]:
                j2 += 1
            b2 = b + 1
            while b2 < so_dai and dau[b2][j] == b:
                b2 += 1
            if b2 - b > 1 or j2 - j > 1:
                kq.append((luoi.doc[j][0], luoi.ngang[b][0], luoi.doc[j2][0], luoi.ngang[b2][0]))
    return kq


SAT_VACH = 14               # điểm ảnh: chữ "|", "I" cách vạch dọc dưới mức này là mẩu nét kẻ còn sót


def xep_vao_o(tu: list, luoi: Luoi, he_so: float = 1.0) -> list:
    """[(x, y, rộng, cao, chữ)] các từ (tọa độ ảnh đã phóng he_so lần) -> các dòng theo thứ tự từ trên xuống: ('bang', [ô…]) với số
    ô = số cột của khung (ô gộp ngang: chữ ở cột đầu, ô còn lại ''), ('chu', [từ]) cho chữ ngoài khung / dải không có vạch dọc bên
    trong (dòng tiêu đề, chữ giữa hai bảng)."""
    ngang = [y * he_so for y, _ in luoi.ngang]
    doc = [x * he_so for x, _ in luoi.doc]
    so_dai, so_cot = len(ngang) - 1, len(doc) - 1

    def dai_cua(y):
        for b in range(so_dai):
            if ngang[b] <= y < ngang[b + 1]:
                return b
        return None

    def cot_cua(x, b):
        """Cột (đầu ô gộp ngang) của tâm x trong dải b; None khi ngoài khung."""
        if not doc[0] <= x < doc[-1]:
            return None
        j = max(i for i in range(so_cot) if doc[i] <= x)
        while j > 0 and not luoi.co_doc[b][j]:          # vạch bên trái không có trong dải này: ô gộp ngang
            j -= 1
        return j

    dau = _dau_vung(luoi)                               # vùng gộp dọc
    o = {}
    ngoai = []                                          # (y, từ) chữ ngoài khung / dải không có vạch dọc
    co_trong = [any(luoi.co_doc[b][1:-1]) or so_cot == 1 for b in range(so_dai)]
    for w in tu:
        x, y, rw, rh, t = w
        if t.strip() in ('|', '||', '[', ']', '!', 'I', 'l') and rw < rh and \
                min(abs(x + rw / 2 - v) for v in doc) < SAT_VACH * he_so:        # mẩu nét kẻ còn sót sát vạch dọc (không bỏ số La Mã "I")
            continue
        cx, cy = x + rw / 2, y + rh / 2
        b = dai_cua(cy)
        if b is None or not co_trong[b]:
            ngoai.append((cy, w))
            continue
        j = cot_cua(cx, b)
        if j is None:
            ngoai.append((cy, w))
            continue
        o.setdefault((dau[b][j], j), []).append(w)
    dong = []
    for b in range(so_dai):
        if not co_trong[b]:
            continue
        hang = [_noi_chu(o.get((b, j), [])) if dau[b][j] == b else '' for j in range(so_cot)]
        if any(hang):
            dong.append((ngang[b], 'bang', hang))
    # chữ ngoài: gom theo dải / khoảng giữa các vạch để giữ thứ tự đọc
    nhom = {}
    for cy, w in ngoai:
        b = dai_cua(cy)
        k = ('tren' if cy < ngang[0] else 'duoi') if b is None else b
        nhom.setdefault(k, []).append(w)
    for k, ds in nhom.items():
        y = -1 if k == 'tren' else 10 ** 9 if k == 'duoi' else ngang[k]
        dong.append((y, 'chu', ds))
    dong.sort(key=lambda d: (d[0], 0 if d[1] == 'chu' else 1))
    return [(loai, nd) for _, loai, nd in dong]

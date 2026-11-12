"""Dàn trang cân đối theo chiều dọc cho bản Word (1.1.03) - GIỮ NGUYÊN bốn lề và bề rộng bảng.

Module lá, không Qt, không biết gì về nội dung văn bản: nơi gọi (in_word) mô tả văn bản thành danh sách KHỐI có chiều cao ước tính (đoạn
văn, dòng bảng), module này mô phỏng ngắt trang rồi chọn thông số:
  - THU GỌN: phần tràn sang trang cuối không quá TRAN_TOI_DA trang -> giảm dần khoảng cách đoạn, đệm ô, giãn dòng, số dòng trống chỗ ký
    (các nấc ở NAC_THU_GON) cho tới khi bớt được một trang;
  - GIÃN ĐỀU: văn bản vẫn nhiều trang -> chia khoảng hở cuối từng trang (trừ trang cuối) vào chiều cao tối thiểu của các dòng bảng trên
    trang đó (w:trHeight atLeast), mỗi dòng thêm không quá GIAN_TOI_DA pt.
Ước tính LUÔN nghiêng về phía CAO HƠN thật (đếm dư dòng chữ): ước dư chỉ làm trang hở thêm vài pt, ước thiếu mới đẩy dòng sang trang sau.
Khi mọi dòng bảng của một trang đã có chiều cao tối thiểu thì sai số ước từng dòng triệt tiêu (tổng = chiều cao đặt), chỉ còn sai số của
phần ngoài bảng ở trang đầu - chừa AN_TOAN_DAU.
Không có hàm đo chữ thật thì nơi gọi không điều tiết (giữ bố cục cũ)."""
from __future__ import annotations

HE_DONG = 1.15                  # Times New Roman: dòng đơn (w:line 240) = 1,15 x cỡ chữ (đo trên Word: dòng bảng 2 dòng chữ 10 pt = 30,25 pt)
VIEN_HANG = 1.0                 # pt đường kẻ ngang giữa hai dòng bảng (w:sz 8)
DU_RONG = 1.03                  # chữ đo bằng Qt nhân lên chừng này khi đếm dòng: thà dư một dòng còn hơn thiếu
TRAN_TOI_DA = 0.20              # thu gọn khi phần tràn sang trang cuối <= 20% chiều cao vùng in
GIAN_TOI_DA = 14.0              # pt thêm tối đa cho một dòng bảng khi giãn
HO_TOI_THIEU = 10.0             # khoảng hở cuối trang từ chừng này (pt) mới giãn
AN_TOAN_BANG = 3.0              # pt chừa lại ở trang chỉ có dòng bảng
AN_TOAN_DAU = 7.0               # pt chừa lại ở trang có phần ngoài bảng (đầu văn bản, mục I, II)
AN_TOAN_THU = 5.0               # thu gọn chỉ nhận khi trang cuối mới còn dư chừng này
# các nấc thu gọn, áp dồn theo thứ tự (twip; dong_ky = số dòng trống chỗ ký)
NAC_THU_GON = (
    {'sau_doan': 60}, {'sau_doan': 40}, {'truoc_muc': 70, 'sau_muc': 30}, {'dem_doc': 16}, {'dem_doc': 10},
    {'dong_doan': 220}, {'dong_doan': 210}, {'dong_ky': 3},
)


class ThongSo:
    """Thông số dàn trang của MỘT văn bản. Mặc định = bố cục chuẩn (không điều tiết)."""
    __slots__ = ('sau_doan', 'dong_doan', 'dem_doc', 'truoc_muc', 'sau_muc', 'dong_ky', 'cao_hang', 'tach', 'che_do', 'so_trang', 'ho')

    def __init__(self, sau_doan: int = 120, dong_doan: int = 240, dem_doc: int = 28, truoc_muc: int = 120, sau_muc: int = 60,
                 dong_ky: int = 4):
        self.sau_doan, self.dong_doan, self.dem_doc = sau_doan, dong_doan, dem_doc
        self.truoc_muc, self.sau_muc, self.dong_ky = truoc_muc, sau_muc, dong_ky
        self.cao_hang: dict = {}        # {chỉ số dòng bảng: chiều cao tối thiểu twip}; khóa 'tieu_de' = dòng tiêu đề cột
        self.tach: set = set()          # chỉ số dòng bảng được phép cắt đôi qua trang
        self.che_do = ''                # '' | 'thu_gon' | 'gian' | 'thu_gon+gian'
        self.so_trang = 1
        self.ho: list = []              # khoảng hở ước (pt) cuối từng trang sau điều tiết

    def ban_sao(self) -> 'ThongSo':
        t = ThongSo(self.sau_doan, self.dong_doan, self.dem_doc, self.truoc_muc, self.sau_muc, self.dong_ky)
        t.cao_hang, t.tach, t.che_do = dict(self.cao_hang), set(self.tach), self.che_do
        return t

    def la_chuan(self) -> bool:
        return not self.che_do


class Khoi:
    """Một khối xếp dọc. loai 'd' = đoạn văn ngoài bảng, 'h' = dòng bảng. cao = chiều cao nội dung (pt, chưa kể đường kẻ dòng bảng);
    giu_sau = đi liền khối sau (keepNext); so_dong + cao_dong + phu: cắt được theo dòng chữ khi tach (cao = so_dong x cao_dong + phu);
    trong_bang: dòng của bảng chính (bảng có tiêu đề lặp đầu trang); chi_so: chỉ số dòng (để đặt chiều cao tối thiểu); gian: được giãn."""
    __slots__ = ('loai', 'cao', 'giu_sau', 'tach', 'so_dong', 'cao_dong', 'phu', 'trong_bang', 'chi_so', 'gian', 'vai', 'truoc', 'sau')

    def __init__(self, loai: str, cao: float, giu_sau: bool = False, tach: bool = False, so_dong: int = 1, cao_dong: float = 0.0,
                 phu: float = 0.0, trong_bang: bool = False, chi_so=None, gian: bool = False, vai: str = '', truoc: float = 0.0,
                 sau: float = 0.0):
        self.loai, self.cao, self.giu_sau, self.tach = loai, float(cao), giu_sau, tach
        self.so_dong, self.cao_dong, self.phu = so_dong, cao_dong, phu
        self.trong_bang, self.chi_so, self.gian, self.vai = trong_bang, chi_so, gian, vai
        self.truoc, self.sau = truoc, sau               # đoạn văn: khoảng cách trước / sau ĐÃ tính trong cao (để gộp với đoạn kề)

    def buoc(self) -> float:
        """Chiều cao chiếm trên trang (dòng bảng: kể đường kẻ)."""
        return self.cao + (VIEN_HANG if self.loai == 'h' and self.vai != 'khong_vien' else 0.0)


def gop_khoang_cach(khoi: list) -> list:
    """Hai đoạn văn liền nhau: Word chỉ lấy khoảng cách LỚN HƠN giữa "sau" của đoạn trên và "trước" của đoạn dưới (đo trên Word: đoạn
    sau 6 pt + tiêu đề trước 6 pt cách nhau 6 pt, không phải 12) - trừ phần trùng khỏi đoạn dưới. Sửa tại chỗ, trả chính danh sách."""
    for a, b in zip(khoi, khoi[1:]):
        if a.loai == 'd' and b.loai == 'd':
            trung = min(a.sau, b.truoc)
            if trung > 0:
                b.cao -= trung
                b.phu = max(0.0, b.phu - trung)
                b.truoc -= trung
    return khoi


def cao_dong_chu(co: float, dong: int = 276) -> float:
    """Chiều cao một dòng chữ Times New Roman cỡ co (pt) với giãn dòng w:line = dong (240 = đơn)."""
    return co * HE_DONG * dong / 240.0


def dem_dong(chu, rong_pt: float, co: float, dam: bool, do, thut_dau: float = 0.0, phong: str = 'Times New Roman') -> int:
    """Số dòng chữ khi bẻ theo từ trong bề rộng rong_pt (pt). do(chữ, phông, cỡ, đậm) -> pt. thut_dau: thụt dòng đầu (pt).
    Xuống dòng cứng tính riêng từng đoạn. Chữ rỗng = 1 dòng."""
    chu = str(chu or '')
    if not chu.strip():
        return 1
    tong = 0
    cach = do(' ', phong, co, dam) * DU_RONG
    for doan in chu.split('\n'):
        con = max(1.0, rong_pt - thut_dau)
        dong, x = 1, 0.0
        for tu in doan.split():
            w = do(tu, phong, co, dam) * DU_RONG
            if x > 0 and x + cach + w > con:
                dong += 1
                con = max(1.0, rong_pt)
                x = w
            else:
                x = (x + cach + w) if x > 0 else w
            while x > con:                              # một từ dài hơn cả dòng: Word bẻ giữa từ
                dong += 1
                x -= con
                con = max(1.0, rong_pt)
        tong += dong
    return tong


class Trang:
    __slots__ = ('dung', 'khoi', 'co_ngoai_bang')

    def __init__(self):
        self.dung = 0.0
        self.khoi: list = []            # [(vị trí trong danh sách khối, trọn khối?)]
        self.co_ngoai_bang = False


def chia_trang(khoi: list, cao_trang: float, cao_tieu_de: float = 0.0) -> list:
    """Mô phỏng ngắt trang của Word: xếp lần lượt, chuỗi khối giu_sau đi liền nhau (không vừa phần còn lại thì sang trang mới, dài hơn cả
    trang thì đành ngắt), khối tach được cắt theo dòng chữ (đoạn văn giữ ít nhất 2 dòng mỗi bên), dòng bảng chính sang trang mới thì trang
    đó mở đầu bằng dòng tiêu đề lặp (cao_tieu_de, đã kể đường kẻ). Trả [Trang]."""
    trang = [Trang()]

    def moi(trong_bang: bool) -> Trang:
        t = Trang()
        if trong_bang and cao_tieu_de:
            t.dung = cao_tieu_de
        trang.append(t)
        return t

    i, n = 0, len(khoi)
    da_vao_bang = False
    while i < n:
        j = i
        while j < n - 1 and khoi[j].giu_sau:
            j += 1
        nhom = khoi[i:j + 1]
        tong = sum(k.buoc() for k in nhom)
        t = trang[-1]
        con = cao_trang - t.dung
        lap = nhom[0].trong_bang and da_vao_bang
        if tong > con + 1e-6:
            k0 = nhom[0]
            if len(nhom) == 1 and k0.tach and k0.so_dong > 1 and k0.cao_dong > 0:
                toi_thieu = 2 if k0.loai == 'd' else 1
                vua = int((con - k0.phu - (VIEN_HANG if k0.loai == 'h' else 0.0)) // k0.cao_dong) if con > k0.phu else 0
                vua = min(vua, k0.so_dong - toi_thieu)
                if vua >= toi_thieu:                     # cắt: phần đầu ở trang này, phần còn lại sang trang sau
                    t.dung += vua * k0.cao_dong + k0.phu
                    t.khoi.append((i, False))
                    t.co_ngoai_bang = t.co_ngoai_bang or not k0.trong_bang
                    t = moi(k0.trong_bang)
                    t.dung += (k0.so_dong - vua) * k0.cao_dong + k0.phu + (VIEN_HANG if k0.loai == 'h' else 0.0)
                    t.khoi.append((i, False))
                    t.co_ngoai_bang = t.co_ngoai_bang or not k0.trong_bang
                    da_vao_bang = da_vao_bang or k0.trong_bang
                    i += 1
                    continue
            if t.khoi:                                   # trang đang có nội dung: cả nhóm sang trang mới
                t = moi(lap)
        for d, k in enumerate(nhom):
            if t.dung + k.buoc() > cao_trang + 1e-6 and t.khoi:
                t = moi(k.trong_bang and da_vao_bang)
            t.dung += k.buoc()
            t.khoi.append((i + d, True))
            t.co_ngoai_bang = t.co_ngoai_bang or not k.trong_bang
            da_vao_bang = da_vao_bang or k.trong_bang
        i = j + 1
    return trang


def _tieu_de(khoi: list) -> float:
    for k in khoi:
        if k.vai == 'tieu_de':
            return k.buoc()
    return 0.0


def _trang_cua(trang: list) -> dict:
    """{vị trí khối: trang} của các khối nằm TRỌN một trang."""
    return {vt: p for p, t in enumerate(trang) for vt, tron in t.khoi if tron}


def dieu_tiet(dung_khoi, cao_trang: float, goc: ThongSo | None = None) -> ThongSo:
    """Chọn thông số dàn trang. dung_khoi(ThongSo) -> [Khoi] của văn bản với thông số đó (gọi lại nhiều lần)."""
    ts = (goc or ThongSo()).ban_sao()
    khoi = dung_khoi(ts)
    trang = chia_trang(khoi, cao_trang, _tieu_de(khoi))
    k = len(trang)
    if k >= 2:
        # ---- thu gọn: phần tràn sang trang cuối đủ nhỏ thì thử từng nấc cho tới khi bớt được một trang
        # phần THỰC SỰ thừa = nội dung trang cuối trừ các khoảng hở cuối những trang trước (khối cuối đi liền nhau nên cả khối bị đẩy
        # sang trang mới dù chỉ thiếu vài dòng: hộ 10 thửa trang cuối chứa 175 pt nhưng chỉ thừa 28 pt)
        cuoi = trang[-1]
        tran = cuoi.dung - (_tieu_de(khoi) if not cuoi.co_ngoai_bang and cuoi.dung > _tieu_de(khoi) else 0.0)
        tran -= sum(max(0.0, cao_trang - t.dung) for t in trang[:-1])
        if tran <= TRAN_TOI_DA * cao_trang:
            thu = ts.ban_sao()
            for nac in NAC_THU_GON:
                for ten, v in nac.items():
                    if ten == 'dong_ky':                # 1.1.07: chỗ ký người dùng đặt (ban_in.mau_word.dong_ky) chỉ bớt MỘT dòng, không dưới 3
                        v = max(3, ts.dong_ky - 1)
                    setattr(thu, ten, min(getattr(thu, ten), v))
                kh = dung_khoi(thu)
                tr = chia_trang(kh, cao_trang, _tieu_de(kh))
                if len(tr) < k and cao_trang - tr[-1].dung >= AN_TOAN_THU:
                    thu.che_do = 'thu_gon'
                    ts, khoi, trang, k = thu, kh, tr, len(tr)
                    break
    if k >= 2:
        _gian(ts, dung_khoi, khoi, trang, cao_trang)
        khoi = dung_khoi(ts)
        trang = chia_trang(khoi, cao_trang, _tieu_de(khoi))
    ts.so_trang = len(trang)
    ts.ho = [round(cao_trang - t.dung, 1) for t in trang]
    return ts


def _gian(ts: ThongSo, dung_khoi, khoi: list, trang: list, cao_trang: float) -> None:
    """Chia khoảng hở cuối từng trang (trừ trang cuối) vào chiều cao tối thiểu của các dòng bảng nằm trọn trên trang đó. Ghi vào
    ts.cao_hang; kết quả phải giữ nguyên số trang và trang của từng dòng - không thì thử một nửa, rồi bỏ."""
    truoc = _trang_cua(trang)
    cao_hang, co = {}, False
    for p, t in enumerate(trang[:-1]):
        ho = cao_trang - t.dung
        if ho < HO_TOI_THIEU or any(not tron for _vt, tron in t.khoi):
            continue
        hang = [khoi[vt] for vt, _ in t.khoi if khoi[vt].gian and khoi[vt].chi_so is not None]
        if not hang:
            continue
        them = ho - (AN_TOAN_DAU if t.co_ngoai_bang else AN_TOAN_BANG)
        moi = min(GIAN_TOI_DA, them / len(hang))
        if moi < 0.5:
            continue
        co = True
        for h in hang:
            cao_hang[h.chi_so] = h.cao + moi
    if not co:
        return
    for he in (1.0, 0.5):
        thu = ts.ban_sao()
        # mọi dòng bảng được giãn + dòng tiêu đề lặp: đặt chiều cao tối thiểu. w:trHeight của Word là chiều cao PHẦN CHỮ - không kể đệm
        # trên / dưới của ô và đường kẻ (đo: trHeight 34,35 pt -> bước dòng 38,16 pt = + 2 x 1,4 đệm + 1 kẻ) nên trừ kh.phu
        for vt, kh in enumerate(khoi):
            if kh.chi_so in cao_hang:
                thu.cao_hang[kh.chi_so] = max(1, int((kh.cao + (cao_hang[kh.chi_so] - kh.cao) * he - kh.phu) * 20))
            elif kh.vai == 'tieu_de':
                thu.cao_hang['tieu_de'] = max(1, int((kh.cao - kh.phu) * 20))
        kh2 = dung_khoi(thu)
        tr2 = chia_trang(kh2, cao_trang, _tieu_de(kh2))
        if len(tr2) == len(trang) and _trang_cua(tr2) == truoc:
            ts.cao_hang = thu.cao_hang
            ts.che_do = (ts.che_do + '+gian') if ts.che_do else 'gian'
            return

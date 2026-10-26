"""Phân loại tài sản theo tên (và đơn vị tính) vào hạng mục bảng đơn giá: Nhà, công trình (mục 2) / Cây trồng (mục 3) /
Vật nuôi (mục MUC_VN - in là mục 4, nhóm vật nuôi QĐ 31/2025) / Chính sách hỗ trợ (mục 4 - in là mục 5) - dùng khi nhập tay danh sách tài sản thô (cửa sổ lập
phương án: "Dán danh sách tài sản…") để đưa mỗi dòng vào đúng mục, đúng mục danh mục.

Ba lớp, lớp trên chắc hơn:
1. khớp tên với danh mục đơn giá của dự án (DanhMuc: dm_taisan, dm_hotro, quy ước) - đúng / gần đúng -> lấy luôn mục danh mục;
2. từ đầu của tên học từ chính danh mục ("dua", "mit", "nha", "hang rao"… -> loại có nhiều mục bắt đầu như vậy);
3. từ khóa + đơn vị tính (tên ngoài danh mục): luật viết tay, có ngoại lệ ("Chuồng gà" là công trình, "Di dời mồ mả" là hỗ trợ).
Không phụ thuộc Qt.
"""
from __future__ import annotations
import difflib
import re
from dataclasses import dataclass

from .lap_pa import bo_dau
from .nghiep_vu import MUC_VN

NHA, CAY, VAT_NUOI, HO_TRO = 'nha', 'cay', 'vat_nuoi', 'ho_tro'
LOAI = {NHA: (2, 'Nhà, công trình'), CAY: (3, 'Cây trồng'), VAT_NUOI: (MUC_VN, 'Vật nuôi'), HO_TRO: (4, 'Chính sách hỗ trợ')}
KHOP_CHAC = 0.86                 # tỷ lệ giống tên danh mục để coi là khớp (dưới mức này chỉ dùng để gợi ý loại)


@dataclass
class KetQua:
    ten: str
    dvt: str
    loai: str                    # NHA / CAY / VAT_NUOI / HO_TRO
    do_tin: float                # 0..1
    ly_do: str
    khop: object = None          # lap_pa.MucDanhMuc khớp (None: ngoài danh mục)
    ty_le_khop: float = 0.0
    # hieu_tai_san.bo_sung (dòng viết tự nhiên): cây theo số đo -> kieu 'dk' / 'cv', loai_cay trong bảng quy cách, số đo (cm)
    kieu: str = ''
    loai_cay: str = ''
    so_do: str = ''
    ghi_them: str = ''           # ghi chú thêm khi thêm vào phương án ("Thực tế: Gác để ở" - dòng "… tính bằng …")

    @property
    def muc(self) -> int:
        return LOAI[self.loai][0]

    @property
    def ten_loai(self) -> str:
        return LOAI[self.loai][1]

    @property
    def can_xem(self) -> bool:
        return self.do_tin < 0.6


# ---------------------------------------------------------------- luật từ khóa (chữ không dấu)
# (mẫu, loại, điểm) - xét trên tên không dấu; ^ = ở đầu tên (từ chính quyết định loại tài sản trong tiếng Việt)
LUAT = [
    # chính sách hỗ trợ
    (r'^(ho tro|tro cap|thuong\b|chi phi di chuyen|di chuyen (tai san|cho o)|thue nha|tam cu|tu lo cho o|on dinh (doi song|san xuat)|'
     r'dao tao|chuyen doi nghe|boi thuong xay dung mo moi|tai dinh cu)', HO_TRO, 6),
    (r'^(di doi|boc|cai tang|di chuyen) (mo|mo ma|hai cot|dong ho|dien thoai|internet|truyen hinh)', HO_TRO, 6),
    (r'\b(nhan khau|ho chinh sach|ngung viec)\b', HO_TRO, 3),
    # vật nuôi (thủy sản, gia súc, gia cầm) - trước "ao" của công trình. Chữ bỏ dấu trùng nhau (cá / cà, bò / bơ, cua / cửa,
    # tằm / tấm, dê / đê) chỉ nhận khi có từ thứ hai rõ nghĩa; còn lại để ĐVT (con, kg, ha/vụ) và danh mục quyết định
    (r'^(ao nuoi|nuoi\b|tha ca|ca (nuoi|giong|thit|ro|tra|chep|tram|me|loc|tai tuong|basa|ghep|bong|chim|keo|tre|long)|'
     r'tom\b|cua (bien|dong|nuoi|gach)|hau\b|luon\b|ech\b|ba ba\b|oc (buou|nhoi|huong)|chim yen|yen sao|'
     r'ga (ta|ri|tre|nuoi|thit|de|con|dong tao)|ga\b(?! hoi| (be|xi|thoat))|vit\b|ngan\b|ngong\b|heo\b|lon (nai|thit|nuoi|con)|'
     r'bo (sua|thit|nuoi|ta|lai|giong|cai|duc)|trau\b|de (thit|nuoi|sua|giong|cai|duc)|cuu\b|tho (nuoi|thit|giong)|bo cau|'
     r'chim cut|ong mat|dan ong|tam (to|nuoi))', VAT_NUOI, 5),
    (r'\b(vat nuoi|gia suc|gia cam|thuy san|nuoi trong|thoi gian nuoi|dinh muc kt)\b', VAT_NUOI, 3),
    # nhà, công trình, vật kiến trúc
    (r'^(nha\b|biet thu|can ho|bep\b|mai (che|hien|ton|tole|ngoi|fibro|bat|nha|tam)|tuong|hang rao|rao|mang rao|tru\b|cot\b|'
     r'cong\b|cua (sat|go|nhom|kinh|cuon|keo|di|so|cong|ra vao)|san (be tong|gach|xi mang|dat|phoi|lat|nen|bt)|nen\b|'
     r'mong\b|be\b|bon (nuoc|nhua|inox|chua|cau|hoa xay)|gieng|ke\b|de (bao|dat|bo|chan)|bo ke|duong (be tong|nhua|dat|giao thong|ong|day|di|noi bo|cap|thoat)|ong\b|muong|'
     r'chuong|lo (say|gach|vo|nung|bep|than|dot|heo)|mo (xay|dat|da|op|tron|ong|ma|moi|cai tang)|mieu|am (tho|than)|lang\b|'
     r'hon non bo|ho (nuoc|chua|ca|ga|xi|phan|rac|bom|boi)|ham\b|lan can|khung|gian\b|gac\b|tran\b|tum\b|ki ot|kiot|'
     r'quan\b|sap\b|tram\b|dong ho|he thong|day dien|bang hieu|cong trinh|vat kien truc|cong dao|dao ao|ao\b|be tong|'
     r'btxm|tam lop|nen xi mang|gach|da (che|hoc|ong)|'
     r'di doi(?! (mo|dong ho|dien thoai|internet|truyen hinh|chau|cay|kieng|vat nuoi)))', NHA, 4),
    (r'\b(ket cau|xay|be tong|btxm|ton|kem gai|luoi b40|thep|sat|gach|ciment|xi mang|tam lop|mai ngoi|op lat|lat gach|'
     r'pvc|upvc|tang|da che|da hoc|da ong|da xanh)\b', NHA, 2),
    (r'^(ban tho|ban thien|trang tho|san\b)', NHA, 3),
    # cây trồng
    (r'^(cay|vuon|rau|lua|bap|ngo|mia|khoai|mi\b|dau (phong|xanh|nanh|den|do|ve|bap)|me\b|lac\b|co (voi|lam thuc an)|'
     r'hoa\b|kieng|bonsai|ca (phe|rot|tim|chua|phao|ri)|ho tieu|tieu\b|thanh long)', CAY, 4),
    (r'\b(chau kieng|cay kieng|cay canh|khoai mi|khoai lang|san day|hoa mau)\b', CAY, 6),
    (r'\b(nam thu|nam tuoi|tuoi\b|\(d\s*[<>]|dk than|duong kinh|chu vi|tan\b|goc\b|bui\b|khom\b|da cho trai|chua cho trai|'
     r'kinh doanh|kien thiet|moi trong|vu (dong xuan|he thu|mua))', CAY, 3),
]
_LUAT = [(re.compile(m), l, d) for m, l, d in LUAT]

# đơn vị tính -> (loại, điểm)
DVT = [(r'^(nhan khau|khau|khau x thang|thang|ho|nguoi|suat)$', HO_TRO, 3),
       (r'(ha ?/ ?vu|100 ?m3 ?/ ?vu|^con$|^kg|don vi vat nuoi|^dan$|^dan ong$|^tan$)', VAT_NUOI, 3),
       (r'^(cay|bui|khom|chau|goc|hom)$', CAY, 3),
       (r'^(m3|m³|m2 san|m²san|cai|canh|tru|bo|chiec|m/soi|md|m dai)$', NHA, 2),
       (r'^(m2|m²|m)$', NHA, 1)]
_DVT = [(re.compile(m), l, d) for m, l, d in DVT]


def _loai_muc(m) -> str:
    """Loại của một mục danh mục (MucDanhMuc / dict có nhom, phan_loai)."""
    nhom = getattr(m, 'nhom', None) if not isinstance(m, dict) else m.get('nhom')
    pl = bo_dau(getattr(m, 'phan_loai', '') if not isinstance(m, dict) else m.get('phan_loai', ''))
    if nhom == 4 or getattr(m, 'nguon', '') == 'hotro':
        return HO_TRO
    if nhom == MUC_VN:
        return VAT_NUOI
    if nhom == 3:
        return VAT_NUOI if 'vat nuoi' in pl else CAY
    return NHA


def _khoa(ten: str) -> str:
    """Tên chuẩn để so: không dấu, bỏ dấu ngoặc / dấu câu ("Cây lúa (Đông Xuân)" = "cay lua dong xuan")."""
    t = bo_dau(ten)
    t = re.sub(r'[“”"\'.,;:()\[\]]+', ' ', t)
    return ' '.join(t.split())


def _goc(ten: str) -> str:
    """Tên chính (bỏ phần trong ngoặc): "Dung lụa (d >9-12 cm)" -> "dung lua"."""
    return _khoa(re.sub(r'\(.*?\)', ' ', str(ten or '')))


def _quy_cach_so(ten: str) -> bool:
    """Phần trong ngoặc là quy cách số đo (đường kính, năm…): giống quy cách chưa đủ, tên chính cũng phải giống."""
    return any(re.search(r'\d', x) for x in re.findall(r'\((.*?)\)', str(ten or '')))


def _dau(t: str, n: int) -> str:
    return ' '.join(re.sub(r'\(.*?\)', ' ', t).split()[:n])


class BoPhanLoai:
    """Bộ phân loại dựng một lần theo danh mục đơn giá (DanhMuc của dự án; None = chỉ luật từ khóa)."""

    def __init__(self, dm=None):
        self.ds = []                                     # [(khóa tên, mục danh mục, loại, tên chính nếu quy cách số / '')]
        self.theo_khoa = {}
        dau1, dau2 = {}, {}
        if dm is not None:
            for nhom in (2, 3, MUC_VN, 4, 9):
                for m in dm.muc.get(nhom, []):
                    loai = _loai_muc(m) if nhom != 9 else self._loai_quy_uoc(m, dm)
                    k = _khoa(m.ten)
                    goc = _goc(m.ten) if _quy_cach_so(m.ten) else ''
                    khoa = [k] + ([k[4:]] if k.startswith('cay ') else [])    # "Cây lúa (Đông Xuân)" ~ "Lúa Đông Xuân"
                    for kk in khoa:
                        self.ds.append((kk, m, loai, goc[4:] if goc.startswith('cay ') and kk is not k else goc))
                        self.theo_khoa.setdefault(kk, (m, loai))
                    dau_k = _dau(_khoa(re.sub(r'\(.*?\)', ' ', m.ten)), 2)
                    for n, bang in ((1, dau1), (2, dau2)):
                        d = _dau(dau_k, n)
                        if d:
                            bang.setdefault(d, {}).setdefault(loai, 0)
                            bang[d][loai] += 1
        self.dau = {1: dau1, 2: dau2}
        self._theo_dau = {}                              # chữ đầu -> [chỉ số trong ds] (lọc trước khi so gần đúng)
        for i, x in enumerate(self.ds):
            self._theo_dau.setdefault(x[0][:1], []).append(i)

    @staticmethod
    def _loai_quy_uoc(m, dm) -> str:
        """Quy ước tương đương (mục 9): loại theo mục danh mục được quy ước theo; không rõ thì theo tên."""
        td = dm.theo_ma.get(getattr(m, 'phan_loai', '') or '') if hasattr(dm, 'theo_ma') else None
        return _loai_muc(td) if td is not None else NHA

    # ---------------------------------------------- các lớp
    def khop_danh_muc(self, ten: str, dvt: str = ''):
        """(mục danh mục, loại, tỷ lệ giống) tốt nhất, hoặc None."""
        k = _khoa(ten)
        if not k:
            return None
        if k in self.theo_khoa:
            m, loai = self.theo_khoa[k]
            return m, loai, 1.0
        ung = self._theo_dau.get(k[:1], [])
        if not ung:
            return None
        sm = difflib.SequenceMatcher(None, '', k)
        tot = None
        dv = bo_dau(dvt)
        goc_k = _goc(ten)
        for i in ung:
            kk, m, loai, goc = self.ds[i]
            sm.set_seq1(kk)
            if sm.real_quick_ratio() < KHOP_CHAC - 0.15 or sm.quick_ratio() < KHOP_CHAC - 0.15:
                continue
            r = sm.ratio()
            if goc and r >= KHOP_CHAC - 0.15:            # "Dương liễu (d >9-12 cm)" không phải "Dung lụa (d >9-12 cm)"
                r = min(r, difflib.SequenceMatcher(None, goc_k, goc).ratio())
            if dv and bo_dau(m.dvt or '') and bo_dau(m.dvt) != dv:
                r -= 0.05                                # khác đơn vị tính: kém tin hơn
            if tot is None or r > tot[2]:
                tot = (m, loai, r)
        return tot

    def theo_tu_dau(self, ten: str) -> dict:
        """{loại: điểm} theo từ đầu của tên (học từ danh mục)."""
        k = _khoa(ten)
        diem = {}
        for n, he_so in ((2, 4), (1, 2)):
            dem = self.dau[n].get(_dau(k, n))
            if dem:
                tong = sum(dem.values())
                for loai, c in dem.items():
                    diem[loai] = diem.get(loai, 0) + he_so * c / tong
                break                                    # đã khớp 2 từ đầu thì không xét 1 từ
        return diem

    @staticmethod
    def theo_luat(ten: str, dvt: str = '') -> tuple:
        """({loại: điểm}, [lý do])."""
        k = _khoa(ten)
        diem, ly_do = {}, []
        for m, loai, d in _LUAT:
            if m.search(k):
                diem[loai] = diem.get(loai, 0) + d
                ly_do.append(f'"{m.search(k).group(0).strip()}" -> {LOAI[loai][1]}')
        dv = bo_dau(dvt).replace(' ', ' ').strip()
        for m, loai, d in _DVT:
            if dv and m.search(dv):
                diem[loai] = diem.get(loai, 0) + d
                ly_do.append(f'ĐVT "{dvt}" -> {LOAI[loai][1]}')
                break
        return diem, ly_do

    # ---------------------------------------------- kết luận
    def phan_loai(self, ten: str, dvt: str = '') -> KetQua:
        ten = ' '.join(str(ten or '').split())
        k = self.khop_danh_muc(ten, dvt) if self.ds else None
        if k is not None and k[2] >= KHOP_CHAC:
            m, loai, r = k
            return KetQua(ten, dvt or m.dvt, loai, min(1.0, 0.75 + r / 4), f'khớp danh mục "{m.ten}" ({r:.0%})', m, r)
        diem, ly_do = self.theo_luat(ten, dvt)
        for loai, d in self.theo_tu_dau(ten).items():
            diem[loai] = diem.get(loai, 0) + d
            ly_do.append(f'từ đầu giống mục {LOAI[loai][1].lower()} trong danh mục')
        if k is not None and k[2] >= 0.6:                # gần giống (dưới mức khớp): thêm điểm cho loại của mục gần nhất
            diem[k[1]] = diem.get(k[1], 0) + 3 * k[2]
            ly_do.append(f'gần giống "{k[0].ten}" ({k[2]:.0%})')
        if not diem:
            return KetQua(ten, dvt, NHA, 0.2, 'không nhận ra: tạm xếp Nhà, công trình - chọn lại loại')
        tot = max(diem, key=lambda x: diem[x])
        tong = sum(diem.values())
        return KetQua(ten, dvt, tot, round(min(0.95, diem[tot] / tong * min(1.0, diem[tot] / 5)), 2), '; '.join(dict.fromkeys(ly_do)))



# ---------------------------------------------------------------- đọc danh sách dán vào
_RE_SO = re.compile(r'^[-+]?\d[\d.,]*$')
_RE_O_PHEP_TINH = re.compile(r'^[=\d.,*x×/+\-:()]+$', re.I)        # một ô thuộc số lượng: 20 / 4*5 / 4x5 / 2,5 / * / x
_RE_TY_LE = re.compile(r'^\d[\d.,]*\s*%$')


def _la_so_hoac_phep_tinh(x: str) -> bool:
    """'20', '4*5', '4x5', '(3+2)*4', '=4,2*5,7' - số lượng; chữ / mã có số ('B40', 'D110') không phải."""
    x = x.replace(' ', '')
    return bool(x) and bool(re.search(r'\d', x)) and bool(_RE_O_PHEP_TINH.match(x)) and bool(re.match(r'^[=(\d]', x))


def _co_the_la_ty_le(so: str) -> bool:
    """Số không có "%" sau số lượng là tỷ lệ khi <= 500 (lap_pa.doc_ty_le: tối đa 500%; <= 5 là hệ số - nhap_tai_san.them_dong_tho).
    Lớn hơn là cột Đơn giá / Thành tiền của bảng Excel dán vào - trước đây thành tỷ lệ 1.500.000%, cả dòng báo lỗi."""
    from .tien import doc_so_vn
    try:
        return abs(doc_so_vn(so)) <= 500
    except (ValueError, ArithmeticError):
        return False


def _tach_dau_cach(dong: str, re_dvt) -> list | None:
    """Quy tắc gõ tay (người dùng 14/10/2026): Tên tài sản ␣ ĐVT ␣ Số lượng [␣ Tỷ lệ %] - đọc TỪ CUỐI dòng: ô có % = tỷ lệ, các ô số /
    phép tính liền nhau ở cuối = số lượng ("4*5", "4 x 5"), 1-2 ô ngay trước khớp đơn vị tính = ĐVT, phần còn lại = tên. Không có
    ĐVT đứng ngay trước số lượng -> None (thử kiểu cũ "Tên Số lượng ĐVT")."""
    t = dong.split()
    ty_le = ''
    if len(t) > 3 and _RE_TY_LE.match(t[-1]):
        ty_le = t.pop()
    j = len(t)
    while j > 1 and _RE_O_PHEP_TINH.match(t[j - 1]):
        j -= 1
    sl = ''.join(t[j:])
    if not _la_so_hoac_phep_tinh(sl):
        return None
    for n in (2, 1):                                     # ĐVT hai chữ trước ("ha/ vụ", "nhân khẩu")
        if j - n >= 1 and re_dvt.match(' '.join(t[j - n:j])):
            return [' '.join(t[:j - n]), ' '.join(t[j - n:j]), sl] + ([ty_le] if ty_le else [])
    return None


def _tinh_so_luong(d: dict) -> None:
    """Số lượng là phép tính ("4*5") -> tính sẵn ("20"), giữ phép tính ở d['cong_thuc'] (hiện ở chú thích ô Số lượng)."""
    from .tien import la_cong_thuc, so_vn, tinh_cong_thuc
    x = d.get('so_luong') or ''
    if x and la_cong_thuc(x):
        try:
            d['so_luong'], d['cong_thuc'] = so_vn(tinh_cong_thuc(x)), x
        except (ValueError, ArithmeticError):
            pass                                         # để nguyên: ô Số lượng báo lỗi rõ khi Thêm vào phương án


def doc_danh_sach(chu: str) -> list:
    """Danh sách tài sản dán từ Excel (cột cách nhau bằng Tab) hoặc gõ tay (cách nhau bằng ; hoặc |), mỗi dòng một tài sản:
    Tên [, ĐVT] [, Số lượng] [, Tỷ lệ %] [, Ghi chú] - thứ tự cột tự nhận (ô số đầu = số lượng, ô có % / số nhỏ <= 5 sau số lượng
    = tỷ lệ, ô chữ ngắn khớp đơn vị tính = ĐVT). Dòng tiêu đề (Tên / Hạng mục / ĐVT / Số lượng), dòng trống, cột STT bỏ qua.
    Trả [dict(ten, dvt, so_luong, ty_le, ghi_chu)] (số giữ dạng chữ như người dùng gõ)."""
    from .nhap_don_gia import DVT as _MAU_DVT
    from .hieu_tai_san import doc_kich_thuoc, la_dong_tu_nhien, tach_dong, tach_dong_qd42
    re_dvt = re.compile(rf'^({_MAU_DVT}|ha/vụ|ha/ vụ|100m3/vụ|nhân khẩu|khẩu|tháng|hộ|người|trụ|cánh|chậu|cây|con|kg)$', re.I)
    kq = []
    # 1.0.32: dòng biên bản ghi gộp nhiều cỡ ("Ống nhựa: ϕ 114: 3300m; ϕ 90: 3400m") tách thành từng dòng TRƯỚC khi chia ô theo ";"
    for dong in (x for d0 in str(chu or '').splitlines() for x in tach_dong_qd42(d0)):
        if not dong.strip():
            continue
        o = [x.strip() for x in re.split(r'\t|;|\|', dong)]
        if len(o) == 1 and la_dong_tu_nhien(o[0]):        # viết tự nhiên: "Xoài: 16 cây, 17 năm tuổi", "Tràm cây 1500 d28"
            t = tach_dong(o[0])
            if t is not None:
                d = dict(ten=t['ten'], dvt=t['dvt'], so_luong=t['so_luong'], ty_le=t['ty_le'], ghi_chu=t['ghi_chu'],
                         so_do=t['so_do'], kieu=t['kieu'], tuoi=t['tuoi'])
                _tinh_so_luong(d)
                kq.append(d)
                continue
        if len(o) == 1:                                   # gõ tay một ô, cách nhau dấu cách: "Nhà tạm m2 4*5" (Tên ĐVT Số lượng)
            tach = _tach_dau_cach(o[0], re_dvt)
            if tach:
                o = tach
            else:                                         # kiểu cũ: "Mít 6 năm 3 cây" -> số lượng + ĐVT ở cuối
                m = re.match(r'^(.*?)\s+([-+]?\d[\d.,]*)\s*([^\d\s][^\d]{0,12})?$', o[0])
                if m and m.group(3) and re_dvt.match(m.group(3).strip()):
                    o = [m.group(1), m.group(3).strip(), m.group(2)]
        o = [x for x in o]
        while o and (not o[0] or re.fullmatch(r'\d+\.?|[ivxIVX]+\.?|[-+*]', o[0])):   # cột STT / ký hiệu đầu dòng
            if len(o) > 1 and o[1]:
                o = o[1:]
            else:
                break
        if not o or not o[0]:
            continue
        ten = o[0]
        if bo_dau(ten).rstrip(':') in ('ten', 'ten tai san', 'hang muc', 'noi dung', 'stt', 'ten tai san, vat kien truc'):
            continue
        d = dict(ten=ten, dvt='', so_luong='', ty_le='', ghi_chu='')
        dvt_kt = ''                                       # ô số lượng dài x rộng không ghi đơn vị -> m2 khi không có cột ĐVT
        for x in o[1:]:
            if not x:
                continue
            kt = None if d['so_luong'] else doc_kich_thuoc(x)
            if kt:                                        # "3,7m x 4,3m", "4,7*3,0", "42m2": diện tích
                d['so_luong'] = kt[0]
                if kt[2]:
                    dvt_kt = kt[1]
                elif not d['dvt']:
                    d['dvt'] = kt[1]
                continue
            so = x.rstrip('%').strip()
            if _RE_SO.match(so) or (not d['so_luong'] and not x.endswith('%') and _la_so_hoac_phep_tinh(x)):
                if not d['so_luong'] and not x.endswith('%'):
                    d['so_luong'] = x
                elif not d['ty_le'] and (x.endswith('%') or _co_the_la_ty_le(so)):
                    d['ty_le'] = x
                continue                                  # số khác (cột Đơn giá, Thành tiền của bảng Excel): bỏ qua
            if not d['dvt'] and re_dvt.match(x):
                d['dvt'] = x
            elif not d['ghi_chu']:
                d['ghi_chu'] = x
        if not d['dvt'] and dvt_kt:
            d['dvt'] = dvt_kt
        _tinh_so_luong(d)
        kq.append(d)
    return kq

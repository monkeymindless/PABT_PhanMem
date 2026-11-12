"""Hồ sơ kiểm kê (giai đoạn 4): thêm / sửa / xóa hộ và thửa, gộp hộ, chuyển thửa sang hộ khác.

Mỗi thao tác ghi trong một giao dịch và có nhật ký. Số liệu sai thì báo LoiNhap (thông báo tiếng Việt).
"""
from __future__ import annotations
import re
from datetime import datetime

from . import csdl
from .lap_pa import LoiNhap, bo_dau, doc_so, doc_so_luong, kiem_ds_ho_nhan_viec, kiem_ho_nhan_viec, kiem_quyen
from .tien import D, chuoi, so_vn

TRUONG_HO = [('ho_ten', 'Họ và tên'), ('so_cccd', 'Số CCCD'), ('ngay_cap', 'Ngày cấp'), ('noi_cap', 'Nơi cấp'),
             ('dia_chi', 'Địa chỉ'), ('dien_thoai', 'Điện thoại'), ('phap_ly', 'Pháp lý'), ('tranh_chap', 'Tranh chấp'),
             ('tai_dinh_cu', 'Tái định cư'), ('trang_thai', 'Trạng thái'), ('ghi_chu', 'Ghi chú'), ('ghi_chu_ten', 'Ghi chú dưới tên')]
TRUONG_THUA = [('so_to', 'Tờ'), ('so_thua', 'Thửa'), ('loai_dat', 'Loại đất'), ('dt_thu_hoi', 'DT thu hồi (m²)'),
               ('nguon_goc', 'Nguồn gốc'), ('vi_tri', 'Vị trí'),
               ('dt_nguyen_thua', 'DT nguyên thửa (m²)'), ('so_gcn', 'Giấy chứng nhận')]      # 2 trường cuối: 20/10/2026


def _gon(v) -> str:
    return ' '.join(str(v if v is not None else '').split())


# gạch đầu dòng viết liền trong câu: " - " đứng SAU dấu kết câu / hai chấm ("như sau: - Thửa đất…", "…năm 2002. - Bà…")
_RE_GACH_MUC = re.compile(r'([.;:!?…]["”’\')\]]?)[ \t]+[-–][ \t]+')
_RE_GACH = re.compile(r'[ \t]+[-–][ \t]+')
DS_NGAN_TU = 8          # danh sách liền một dòng "đất ở - đất lúa - đất vườn": mọi đoạn <= chừng này từ


def _tach_ds_ngan(dong: str) -> str:
    """Một dòng là danh sách ngắn liền nhau (>= 2 dấu " - " ngoài ngoặc, mọi đoạn <= DS_NGAN_TU từ) -> mỗi đoạn sau một dòng "- "."""
    # gạch nằm trong ngoặc đơn ("(con bà A - đại diện)") không tính
    # gạch giữa hai số là khoảng năm / số ("sử dụng 1975 - 1990, 1990 - 2005 bà B") - không phải danh sách
    cat = [(m.start(), m.end()) for m in _RE_GACH.finditer(dong) if dong.count('(', 0, m.start()) <= dong.count(')', 0, m.start())
           and not (dong[:m.start()][-1:].isdigit() and dong[m.end():m.end() + 1].isdigit())]
    if len(cat) < 2:
        return dong
    doan, dau = [], 0
    for a, b in cat:
        doan.append(dong[dau:a])
        dau = b
    doan.append(dong[dau:])
    if any(len(d.split()) > DS_NGAN_TU for d in doan):
        return dong
    return '\n- '.join(d.strip() for d in doan)


_RE_DIEN_GIAI_TEN = re.compile(r'\s+là chủ sở hữu|\s+-\s+Đất do ', re.I)


# 1.0.78: từ viết thường ngay sau tên nhưng vẫn là phần của tên / nhiều chủ: không tách
_TU_NOI_TEN = frozenset(('và', 'cùng', 'với', 'hoặc', 'con', 'vợ', 'chồng', 'ông', 'bà', 'anh', 'chị', 'em', 'cha', 'mẹ', 'đồng', 'theo', 'do'))
# câu diễn giải phải mở đầu bằng một trong các cụm này: chỉ dựa vào chữ thường thì tách nhầm "Khu Bảo | tồn Thiên nhiên…" (test 1610 bắt được)
_DAU_CAU_SAU_TEN = ('xây dựng', 'xây', 'có', 'là', 'thuê', 'mượn', 'sử dụng', 'canh tác', 'nhận', 'trồng', 'đang', 'được', 'chủ', 'sở hữu',
                    'tạo lập', 'quản lý', 'cất', 'dựng', 'khai phá', 'ở', 'cư trú', 'thừa kế', 'mua', 'hiện')


def _vi_tri_het_ten(s: str) -> int:
    """Chuẩn chung (1.0.78): 2 - 6 từ viết hoa chữ đầu (tên người) rồi câu từ 3 từ trở lên mở đầu bằng _DAU_CAU_SAU_TEN -> vị trí đầu câu; 0 nếu
    không chắc (tổ chức, tên viết thường, nhiều chủ "A và B", dấu phẩy trong tên). Không đoán: câu khác nhập ở ô Ghi chú dưới tên."""
    tu = s.split()
    i = 0
    while i < len(tu) and tu[i][:1].isupper():
        if tu[i][-1] in ',;:':
            return 0
        i += 1
    if not 2 <= i <= 6 or len(tu) - i < 3 or not tu[i][:1].islower() or tu[i].lower() in _TU_NOI_TEN or la_to_chuc(s):
        return 0
    sau = ' '.join(tu[i:]).lower()
    if not any(sau == d or sau.startswith(d + ' ') for d in _DAU_CAU_SAU_TEN):
        return 0
    return len(' '.join(tu[:i])) + 1


def tach_ho_ten(chuoi) -> tuple:
    """(tên riêng, phần diễn giải pháp lý) khi ô họ tên bị ghi cả câu: "Nguyễn Văn A là chủ sở hữu tài sản… - Đất do UBND xã… quản lý." (06/11/2026, người dùng).
    Không có cụm nhận biết, hoặc trước cụm đó không có tên: giữ nguyên, phần diễn giải rỗng (không đoán)."""
    s = ' '.join(str(chuoi or '').split())
    m = _RE_DIEN_GIAI_TEN.search(s)
    vt = m.start() if m is not None and m.start() > 0 else _vi_tri_het_ten(s)
    if not vt:
        return s, ''
    dg = s[vt:].strip(' -')
    return s[:vt].rstrip(' ,;:-'), dg[:1].upper() + dg[1:]


_RE_DOAN_CHU_SO_HUU = re.compile(r'^là chủ sở hữu\b', re.I)


def ten_day_du_in(ho_ten, phap_ly='', ghi_chu_ten='') -> str:
    """Bản in (người dùng 07/11/2026): tên và ghi chú ghi LIỀN nhau: "Phan Văn Minh là chủ sở hữu tài sản…". Màn hình tách hai dòng cho dễ theo dõi."""
    ten = tach_ho_ten(ho_ten)[0]
    phu = dong_duoi_ten(ho_ten, phap_ly, ghi_chu_ten)
    return f'{ten} {phu[:1].lower()}{phu[1:]}' if phu else ten


def dong_duoi_ten(ho_ten, phap_ly='', ghi_chu_ten='') -> str:
    """Dòng hiện dưới tên hộ trên các danh sách (1.0.78): phần diễn giải còn trong ô họ tên + ô Ghi chú dưới tên + các đoạn "Là chủ sở
    hữu…" của Tình trạng pháp lý (dữ liệu 1.0.75 tách sang đó; đoạn cách nhau bằng ";"). Không có thì ''."""
    _ten, dg = tach_ho_ten(ho_ten)
    ds = [dg] if dg else []
    gc = ' '.join(str(ghi_chu_ten or '').split())
    if gc and gc.lower() not in (x.lower() for x in ds):
        ds.append(gc)
    for d in str(phap_ly or '').split(';'):
        d = ' '.join(d.split())
        if _RE_DOAN_CHU_SO_HUU.match(d) and d.lower() not in (x.lower() for x in ds):
            ds.append(d[:1].upper() + d[1:])
    return '; '.join(ds)


def chuan_nguon_goc(v) -> str:
    """Giữ xuống dòng. Gạch đầu dòng viết liền trong câu tách thành dòng riêng bắt đầu bằng '- ' khi: " - " đứng sau dấu kết câu
    / dấu hai chấm, hoặc cả dòng là danh sách ngắn ("đất ở - đất lúa - đất vườn", 0.9.46). 0.9.88 (người dùng 15/10/2026): KHÔNG
    tách gạch nối giữa tên riêng ("Khu Bảo tồn thiên nhiên - Văn hoá Đồng Nai") hay trong ngoặc ("(con bà A - đại diện)") - trước
    đây mọi " - " đều tách, cắt đôi các tên này. Dấu • * giữa chữ vẫn là đầu mục."""
    s = str(v or '').replace('\r\n', '\n').replace('\r', '\n')
    s = re.sub(r'[ \t]+([•*])[ \t]+', r'\n\1 ', s)
    s = _RE_GACH_MUC.sub(r'\1\n- ', s)
    s = '\n'.join(_tach_ds_ngan(x) for x in s.split('\n'))
    dong = [' '.join(x.split()) for x in s.split('\n')]
    return '\n'.join(x for x in dong if x)


# ký hiệu đầu dòng của một đoạn nguồn gốc: "- ", "– ", "+ ", "• ", "* ", "a) ", "1. ", "1) "
_RE_DAU_DONG = re.compile(r'^\s*(?:[-–+•*]|[a-zđ]\)|\d{1,2}[.)])\s+', re.I)
_RE_HET_CAU_DONG = re.compile(r'[.!?…]["”’\')\]]?$')       # 22/10/2026: chỉ dấu hết câu thật (không ; :)


def lam_sach_doan_van(van_ban) -> list:
    """Chữ nhiều dòng (nguồn gốc đất) -> các đoạn logic để in (người dùng 21/10/2026: bản in cụt chữ giữa câu "Đoàn / Thanh niên",
    "chủ hợp / đồng" - xuống dòng cứng của ô Excel nhập vào / chữ dán từ PDF). Xuống dòng giữa câu nối lại bằng MỘT dấu cách; đoạn
    mới chỉ khi dòng mới là mục (gạch đầu dòng - + • *, a), 1.), dòng trước đã hết câu (. ! ? - 22/10/2026: dòng kết thúc ";" / ":"
    mà dòng sau không phải mục vẫn nối, không tách đoạn vụn) hoặc có dòng trống xen giữa. Khoảng trắng liên tiếp gộp thành một dấu cách
    (căn đều không hở khe). U+2028 (xuống dòng của ô màn hình) như xuống dòng thường. Dữ liệu đã lưu không đổi - chỉ chữ đưa ra bản in."""
    s = str(van_ban or '').replace('\r\n', '\n').replace('\r', '\n').replace(' ', '\n')
    doan, moi = [], True
    for dong in s.split('\n'):
        dong = ' '.join(dong.split())
        if not dong:
            moi = True
            continue
        if doan and not moi and not dau_dong(dong) and not _RE_HET_CAU_DONG.search(doan[-1]):
            doan[-1] += ' ' + dong
        else:
            doan.append(dong)
        moi = False
    return [re.sub(r'[ \t]{2,}', ' ', d) for d in doan]


_RE_CAP_XA = re.compile(r'^(xa|phuong|thi tran|dac khu|p\.?|x\.?|tt\.?)\s+')


def rut_gon_dia_chi(dia_chi: str, ten_dia_ban: str) -> str:
    """Địa chỉ hiển thị gọn trên danh sách hộ (người dùng 13/10/2026): bỏ đoạn xã / phường trùng địa bàn dự án và các cấp sau nó
    ("Ấp 1, xã A, huyện B, tỉnh C" + địa bàn "A" -> "Ấp 1"). Xã / phường khác, hoặc chỉ có một đoạn: giữ
    nguyên (địa chỉ đầy đủ ở chú thích của ô)."""
    chu = ' '.join(str(dia_chi or '').split())
    xa = _RE_CAP_XA.sub('', bo_dau(ten_dia_ban or '').strip())
    if not chu or not xa:
        return chu
    doan = [d.strip() for d in re.split(r'[,;]', chu)]
    for i in range(1, len(doan)):
        if _RE_CAP_XA.sub('', bo_dau(doan[i]).strip()) == xa:
            gon = ', '.join(d for d in doan[:i] if d)
            return gon or chu
    return chu


# chủ sử dụng là tổ chức (0.9.87 - bản in ghi "Tổ chức:" thay "Họ và tên:"): tên BẮT ĐẦU bằng loại tổ chức (so không dấu). Không
# dùng từ trùng họ người ("trường" = Trương, "đinh" = Đinh): trường học phải có cấp học đi kèm.
_DAU_TO_CHUC = ('cong ty', 'tong cong ty', 'doanh nghiep', 'dntn', 'hop tac xa', 'htx', 'uy ban nhan dan', 'ubnd',
                'ban quan ly', 'bql', 'trung tam', 'chi nhanh', 'tap doan', 'xi nghiep', 'nha may', 'nong truong', 'lam truong',
                'nha tho', 'chua', 'tinh xa', 'tinh that', 'thanh that', 'giao xu', 'giao ho', 'hoi thanh',
                'truong mam non', 'truong mau giao', 'truong tieu hoc', 'truong thcs', 'truong thpt', 'truong trung hoc',
                'truong cao dang', 'truong dai hoc', 'benh vien', 'tram y te', 'ngan hang', 'kho bac', 'co quan', 'to chuc',
                'cong an', 'ban chi huy', 'bo chi huy', 'dang uy', 'mat tran to quoc', 'hoi nong dan', 'hoi cuu chien binh',
                'hoi lien hiep phu nu', 'hoi chu thap do', 'van phong', 'cong doan', 'quy tin dung')
_RE_TO_CHUC = re.compile(r'^(?:' + '|'.join(re.escape(x) for x in _DAU_TO_CHUC) + r')\b|\b(?:tnhh|co phan|cp|mtv)\b')
_RE_LA_NGUOI = re.compile(r'^(?:ong|ba|ho ong|ho ba|ho gia dinh|anh|chi|cu)\b')


def la_to_chuc(ten: str, loai: str = '') -> bool:
    """Chủ sử dụng đất là tổ chức: loai ('to_chuc' / 'Tổ chức'…) nếu có, không thì theo tên (Công ty…, UBND…, Ban quản lý…,
    Hợp tác xã, Trung tâm, Nhà thờ, Chùa, Trường tiểu học…, hoặc có TNHH / cổ phần). "Ông / Bà / Hộ …" luôn là hộ, cá nhân."""
    lo = bo_dau(loai or '').strip().replace('_', ' ')
    if lo:
        return lo in ('to chuc', 'tc', 'doanh nghiep', 'co quan')
    s = ' '.join(bo_dau(ten or '').split())
    return bool(s) and not _RE_LA_NGUOI.match(s) and bool(_RE_TO_CHUC.search(s))


def dau_dong(doan: str) -> str:
    """Phần ký hiệu đầu dòng (cả khoảng trắng sau) của đoạn, '' nếu đoạn không bắt đầu bằng gạch đầu dòng. Dòng tràn của đoạn
    có ký hiệu thì thụt vào thẳng chữ sau ký hiệu (thụt lề treo - màn hình hồ sơ và bản in, người dùng yêu cầu)."""
    m = _RE_DAU_DONG.match(doan or '')
    return m.group(0) if m else ''


def chuan_loai_dat(v) -> str:
    """' ont + cln ' -> 'ONT+CLN'; 'rdd', 'ONT,CLN', 'Đất rừng đặc dụng' cũng chuẩn về mã (loai_dat.chuan_ma_loai_dat)."""
    from .loai_dat import chuan_ma_loai_dat
    return chuan_ma_loai_dat(_gon(v))


def doc_ho(con, ma_ho: int) -> dict:
    """Thông tin hộ + danh sách thửa (mỗi thửa có 'so_dong_pa' = số dòng mục 1 đang gắn với thửa)."""
    r = con.execute('SELECT * FROM ho WHERE ma_ho = ?', (ma_ho,)).fetchone()
    if r is None:
        raise LoiNhap(f'Không có hộ mã {ma_ho}.')
    ho = dict(r)
    ho.setdefault('ghi_chu_ten', '')                     # file cũ mở chỉ xem chưa có cột
    ho['thua'] = [dict(t) for t in con.execute(
        '''SELECT t.*, (SELECT COUNT(*) FROM ct_dat d WHERE d.ma_thua = t.ma_thua) AS so_dong_pa
           FROM thua t WHERE t.ma_ho = ? ORDER BY t.thu_tu, t.ma_thua''', (ma_ho,))]
    ho['so_dong_pa'] = con.execute('SELECT (SELECT COUNT(*) FROM ct_dat WHERE ma_ho = ?) + '
                                   '(SELECT COUNT(*) FROM ct_khoan WHERE ma_ho = ?)', (ma_ho, ma_ho)).fetchone()[0]
    return ho


def chuan_hoa_thua(ds: list) -> list:
    """Kiểm tra và làm gọn danh sách thửa người dùng nhập; bỏ dòng trống hoàn toàn."""
    kq, da_co = [], set()
    for i, t in enumerate(ds, start=1):
        g = {k: _gon(t.get(k)) for k, _ in TRUONG_THUA}
        g['nguon_goc'] = chuan_nguon_goc(t.get('nguon_goc'))
        g['loai_dat'] = chuan_loai_dat(g['loai_dat'])
        if not any(g.values()):
            continue
        ten = f'Thửa {g["so_thua"] or "?"} tờ {g["so_to"] or "?"}'
        if not g['so_to'] and not g['so_thua']:
            raise LoiNhap(f'Dòng thửa {i}: chưa nhập số tờ, số thửa.')
        # 1.0.98: phép tính ("=12*3,5") làm tròn như ô số lượng phương án (một nguồn: lap_pa.doc_so_luong)
        g['dt_thu_hoi'] = chuoi(doc_so_luong(g['dt_thu_hoi'], 'm2', f'{ten}: DT thu hồi'))
        if g['dt_nguyen_thua']:                             # trống = chưa nhập (không phải 0)
            nguyen = doc_so(g['dt_nguyen_thua'], f'{ten}: DT nguyên thửa')
            if nguyen < D(g['dt_thu_hoi']):
                raise LoiNhap(f'{ten}: DT thu hồi ({so_vn(g["dt_thu_hoi"])} m²) lớn hơn DT nguyên thửa ({so_vn(nguyen)} m²).')
            g['dt_nguyen_thua'] = chuoi(nguyen)
        khoa = (g['so_to'], g['so_thua'], g['loai_dat'])
        if khoa in da_co:
            raise LoiNhap(f'{ten} ({g["loai_dat"] or "chưa có loại đất"}) bị nhập hai lần.')
        da_co.add(khoa)
        g['ma_thua'] = t.get('ma_thua')
        kq.append(g)
    return kq


def thua_trung_ho_khac(con, ma_ho: int) -> list:
    """Thửa của hộ này cũng có trong hộ khác (đồng sử dụng hoặc nhập trùng)."""
    return [f'Thửa {r["so_thua"]} tờ {r["so_to"]} cũng có ở hộ {r["ma_ho"]} - {r["ho_ten"]}'
            for r in con.execute('''SELECT DISTINCT a.so_to, a.so_thua, h.ma_ho, h.ho_ten FROM thua a
                                     JOIN thua b ON b.so_to = a.so_to AND b.so_thua = a.so_thua AND b.ma_ho <> a.ma_ho
                                     JOIN ho h ON h.ma_ho = b.ma_ho WHERE a.ma_ho = ? ORDER BY h.ma_ho''', (ma_ho,))]


def luu_ho(con, ma_ho, thong_tin: dict, ds_thua: list) -> int:
    """Thêm hộ mới (ma_ho = None) hoặc sửa hộ: thông tin + toàn bộ danh sách thửa (thêm / sửa / xóa). Trả mã hộ."""
    moi = ma_ho is None
    kiem_ho_nhan_viec(con, ma_ho)
    kiem_quyen(con, 'sua_ho_so')                 # 1.0.57: vai trò tài khoản máy chủ (phan_quyen)
    # sửa hộ: chỉ ghi các trường có trong thong_tin (màn hình không hiện trường nào thì giữ nguyên trường đó)
    tt = {k: _gon(thong_tin.get(k)) for k, _ in TRUONG_HO if moi or k in thong_tin}
    if not tt.get('ho_ten'):
        raise LoiNhap('Họ và tên không được để trống.')
    if moi or 'trang_thai' in tt:
        tt['trang_thai'] = tt.get('trang_thai') or 'Chưa lập phương án'
    if 'so_cccd' in tt:
        tt['so_cccd'] = re.sub(r'\s', '', tt['so_cccd'])
        if tt['so_cccd'] and not tt['so_cccd'].isdigit():
            raise LoiNhap(f'Số CCCD "{tt["so_cccd"]}" chỉ gồm chữ số.')
    ds = chuan_hoa_thua(ds_thua)
    with csdl.giao_dich(con):
        if 'ghi_chu_ten' in tt:
            csdl.dam_bao_cot_ghi_chu_ten(con)
        if moi:
            ma_ho, thu_tu = con.execute('SELECT COALESCE(MAX(ma_ho), 0) + 1, COALESCE(MAX(thu_tu), 0) + 1 FROM ho').fetchone()
            con.execute(f'''INSERT INTO ho (ma_ho, thu_tu, {', '.join(tt)}) VALUES (?, ?, {', '.join('?' * len(tt))})''',
                        (ma_ho, thu_tu, *tt.values()))
        else:
            if con.execute('SELECT 1 FROM ho WHERE ma_ho = ?', (ma_ho,)).fetchone() is None:
                raise LoiNhap(f'Không có hộ mã {ma_ho}.')
            con.execute(f'''UPDATE ho SET {', '.join(k + ' = ?' for k in tt)} WHERE ma_ho = ?''', (*tt.values(), ma_ho))
        cu = {r[0] for r in con.execute('SELECT ma_thua FROM thua WHERE ma_ho = ?', (ma_ho,))}
        giu = set()
        cot = ['so_to', 'so_thua', 'loai_dat', 'dt_thu_hoi', 'nguon_goc', 'vi_tri']
        if csdl.dam_bao_cot_thua(con):                      # file cũ chưa có cột DT nguyên thửa / số GCN: thêm khi ghi
            cot += [k for k, _ in csdl.COT_THUA_THEM]
        for i, t in enumerate(ds, start=1):
            gt = (*(t.get(k, '') for k in cot), i)
            if t['ma_thua'] in cu:
                con.execute(f'''UPDATE thua SET {', '.join(k + '=?' for k in cot)}, thu_tu=? WHERE ma_thua = ?''',
                            (*gt, t['ma_thua']))
                giu.add(t['ma_thua'])
            else:
                mt = con.execute('SELECT COALESCE(MAX(ma_thua), 0) + 1 FROM thua').fetchone()[0]
                con.execute(f'''INSERT INTO thua (ma_thua, ma_ho, {', '.join(cot)}, thu_tu) VALUES ({', '.join('?' * (len(cot) + 3))})''',
                            (mt, ma_ho, *gt))
                t['ma_thua'] = mt
        bo = cu - giu
        for mt in bo:
            con.execute('DELETE FROM thua WHERE ma_thua = ?', (mt,))      # dòng mục 1 gắn thửa này: ma_thua -> NULL
        csdl.ghi_nhat_ky(con, 'Thêm hộ' if moi else 'Sửa hồ sơ hộ',
                         f'Hộ {ma_ho} {tt["ho_ten"]}: {len(ds)} thửa' + (f', xóa {len(bo)} thửa' if bo else ''))
    return ma_ho


def _danh_lai(con) -> None:
    # chỉ ghi các hộ đổi số thứ tự (trước đây ghi lại cả 3.000 hộ - mỗi dòng còn một dòng nhật ký hoàn tác)
    doi = [(i, m) for i, (m, tt) in enumerate(con.execute('SELECT ma_ho, thu_tu FROM ho ORDER BY thu_tu, ma_ho').fetchall(),
                                              start=1) if tt != i]
    con.executemany('UPDATE ho SET thu_tu = ? WHERE ma_ho = ?', doi)


def xoa_ho(con, ma_ho: int) -> str:
    return xoa_nhieu_ho(con, [ma_ho])


def thong_tin_xoa(con, ds_ma_ho) -> list:
    """Hỏi trước khi xóa: [dict(ma_ho, thu_tu, ho_ten, so_thua, so_dong_pa, so_qd, da_nhan_tien)] theo thứ tự hộ trong danh sách
    (mã không còn trong dự án: bỏ qua)."""
    kq = []
    for m in dict.fromkeys(ds_ma_ho):
        r = con.execute(
            '''SELECT ma_ho, thu_tu, ho_ten,
                      (SELECT COUNT(*) FROM thua t WHERE t.ma_ho = h.ma_ho),
                      (SELECT COUNT(*) FROM ct_dat d WHERE d.ma_ho = h.ma_ho) + (SELECT COUNT(*) FROM ct_khoan k WHERE k.ma_ho = h.ma_ho),
                      (SELECT COUNT(*) FROM qd_ho q WHERE q.ma_ho = h.ma_ho),
                      (SELECT COUNT(*) FROM qd_ho q WHERE q.ma_ho = h.ma_ho AND q.da_chi_tra)
               FROM ho h WHERE ma_ho = ?''', (m,)).fetchone()
        if r is not None:
            kq.append(dict(zip(('ma_ho', 'thu_tu', 'ho_ten', 'so_thua', 'so_dong_pa', 'so_qd', 'da_nhan_tien'), r)))
    return sorted(kq, key=lambda x: (x['thu_tu'] or 0, x['ma_ho']))


def xoa_nhieu_ho(con, ds_ma_ho) -> str:
    """Xóa các hộ cùng thửa, phương án, quyết định / chi trả của hộ (CASCADE) trong MỘT giao dịch - một bước hoàn tác; đánh
    lại số thứ tự một lần."""
    kiem_ds_ho_nhan_viec(con, ds_ma_ho)
    kiem_quyen(con, 'xoa_ho')                 # 1.0.57: vai trò tài khoản máy chủ (phan_quyen)
    if getattr(con, '_vai_tro', None) is not None:
        from .phan_quyen import kiem_xoa_ho
        kiem_xoa_ho(con, ds_ma_ho)
    ds = thong_tin_xoa(con, ds_ma_ho)
    if not ds:
        raise LoiNhap('Không có hộ nào để xóa (hộ đã bị xóa hoặc chưa chọn hộ).')
    thua, dong = sum(x['so_thua'] for x in ds), sum(x['so_dong_pa'] for x in ds)
    with csdl.giao_dich(con):
        for x in ds:
            con.execute('DELETE FROM ho WHERE ma_ho = ?', (x['ma_ho'],))     # thửa, phương án, qd_ho xóa theo (CASCADE)
            con.execute('DELETE FROM tong_excel WHERE ma_ho = ?', (x['ma_ho'],))
        _danh_lai(con)
        if len(ds) == 1:
            tb = f'Đã xóa hộ {ds[0]["ma_ho"]} {ds[0]["ho_ten"]} ({thua} thửa, {dong} dòng phương án).'
        else:
            ten = ', '.join(f'{x["ma_ho"]} {x["ho_ten"]}' for x in ds[:5]) + (f' và {len(ds) - 5} hộ khác' if len(ds) > 5 else '')
            tb = f'Đã xóa {len(ds)} hộ ({thua} thửa, {dong} dòng phương án): {ten}.'
        csdl.ghi_nhat_ky(con, 'Xóa hộ', tb)
    return tb


def gop_ho(con, giu: int, bo: int) -> str:
    """Gộp hộ `bo` vào hộ `giu`: chuyển thửa, dòng phương án; ô trống của hộ giữ lấy từ hộ bỏ; xóa hộ bỏ."""
    if giu == bo:
        raise LoiNhap('Chọn hai hộ khác nhau để gộp.')
    kiem_ds_ho_nhan_viec(con, (giu, bo))
    kiem_quyen(con, 'sua_ho_so')                 # 1.0.57: vai trò tài khoản máy chủ (phan_quyen)
    a, b = doc_ho(con, giu), doc_ho(con, bo)
    with csdl.giao_dich(con):
        csdl.dam_bao_cot_ghi_chu_ten(con)
        cap = {}
        for k, _ in TRUONG_HO:
            if k == 'ghi_chu':
                cap[k] = '; '.join(x for x in (a[k], b[k]) if x)
            elif k != 'trang_thai' and not a[k] and b[k]:
                cap[k] = b[k]
        if cap:
            con.execute(f'''UPDATE ho SET {', '.join(k + ' = ?' for k in cap)} WHERE ma_ho = ?''', (*cap.values(), giu))
        for bang in ('thua', 'ct_dat', 'ct_khoan'):
            n = con.execute(f'SELECT COALESCE(MAX(thu_tu), 0) FROM {bang} WHERE ma_ho = ?', (giu,)).fetchone()[0]
            con.execute(f'UPDATE {bang} SET ma_ho = ?, thu_tu = thu_tu + ? WHERE ma_ho = ?', (giu, n, bo))
        if b['so_dong_pa']:
            con.execute('UPDATE ho SET luu_luc = ? WHERE ma_ho = ?', (datetime.now().isoformat(timespec='seconds'), giu))
        # quyết định của hộ bỏ chuyển sang hộ giữ (cùng một quyết định: cộng số tiền)
        for r in con.execute('SELECT qd_id, so_tien FROM qd_ho WHERE ma_ho = ?', (bo,)).fetchall():
            cu = con.execute('SELECT so_tien FROM qd_ho WHERE qd_id = ? AND ma_ho = ?', (r[0], giu)).fetchone()
            if cu is None:
                con.execute('UPDATE qd_ho SET ma_ho = ? WHERE qd_id = ? AND ma_ho = ?', (giu, r[0], bo))
            elif str(r[1] or '').strip():
                from .tien import D, chuoi
                con.execute('UPDATE qd_ho SET so_tien = ? WHERE qd_id = ? AND ma_ho = ?',
                            (chuoi(D(cu[0] or 0) + D(r[1])), r[0], giu))
        con.execute('DELETE FROM tong_excel WHERE ma_ho IN (?, ?)', (giu, bo))
        con.execute('DELETE FROM ho WHERE ma_ho = ?', (bo,))
        from .theo_doi import dong_bo_ho
        dong_bo_ho(con, giu)
        _danh_lai(con)
        tb = (f'Đã gộp hộ {bo} {b["ho_ten"]} ({len(b["thua"])} thửa, {b["so_dong_pa"]} dòng phương án) '
              f'vào hộ {giu} {a["ho_ten"]}.')
        csdl.ghi_nhat_ky(con, 'Gộp hộ', tb)
    return tb


def them_thua(con, ma_ho: int, dong: dict) -> int:
    """Thêm MỘT thửa vào hồ sơ hộ (ghim hộ vào thửa trên bản đồ), không đụng các thửa khác của hộ. dong: các khóa của TRUONG_THUA (số gõ kiểu Việt Nam). Trả mã thửa."""
    kiem_ho_nhan_viec(con, ma_ho)
    kiem_quyen(con, 'sua_ho_so')
    ho = con.execute('SELECT ho_ten FROM ho WHERE ma_ho = ?', (ma_ho,)).fetchone()
    if ho is None:
        raise LoiNhap(f'Không có hộ mã {ma_ho}.')
    g = chuan_hoa_thua([dong])
    if not g:
        raise LoiNhap('Chưa có số tờ, số thửa.')
    g = g[0]
    if con.execute('SELECT 1 FROM thua WHERE ma_ho = ? AND so_to = ? AND so_thua = ? AND loai_dat = ?',
                   (ma_ho, g['so_to'], g['so_thua'], g['loai_dat'])).fetchone():
        raise LoiNhap(f'Hộ {ho["ho_ten"]} đã có thửa {g["so_thua"]} tờ {g["so_to"]}.')
    cot = ['so_to', 'so_thua', 'loai_dat', 'dt_thu_hoi', 'nguon_goc', 'vi_tri']
    with csdl.giao_dich(con):
        if csdl.dam_bao_cot_thua(con):
            cot += [k for k, _ in csdl.COT_THUA_THEM]
        mt, tt = con.execute('SELECT COALESCE(MAX(ma_thua), 0) + 1, (SELECT COALESCE(MAX(thu_tu), 0) + 1 FROM thua WHERE ma_ho = ?) FROM thua', (ma_ho,)).fetchone()
        con.execute(f'''INSERT INTO thua (ma_thua, ma_ho, {', '.join(cot)}, thu_tu) VALUES ({', '.join('?' * (len(cot) + 3))})''',
                    (mt, ma_ho, *(g.get(k, '') for k in cot), tt))
        csdl.ghi_nhat_ky(con, 'Thêm thửa từ bản đồ', f'Hộ {ma_ho} {ho["ho_ten"]}: thửa {g["so_thua"]} tờ {g["so_to"]}')
    return mt


def bo_thua(con, ma_thua: int) -> str:
    """1.1.07: bỏ MỘT thửa khỏi hồ sơ hộ (gắn nhầm hộ trên bản đồ) - thửa về "Chưa gắn hộ". Thửa đã có dòng bồi thường đất trong
    phương án: KHÔNG bỏ (LoiNhap) - tiền đất sẽ mất thửa căn cứ; xóa dòng trong phương án trước hoặc dùng Đổi hộ."""
    t = con.execute('SELECT * FROM thua WHERE ma_thua = ?', (ma_thua,)).fetchone()
    if t is None:
        raise LoiNhap(f'Không có thửa mã {ma_thua}.')
    kiem_ho_nhan_viec(con, t['ma_ho'])
    kiem_quyen(con, 'sua_ho_so')
    so = con.execute('SELECT COUNT(*) FROM ct_dat WHERE ma_thua = ?', (ma_thua,)).fetchone()[0]
    if so:
        raise LoiNhap(f'Thửa {t["so_thua"]} tờ {t["so_to"]} đã có {so} dòng bồi thường đất trong phương án của hộ {t["ma_ho"]}: không '
                      'bỏ gắn được (tiền đất sẽ mất thửa căn cứ). Xóa các dòng đó trong phương án trước, hoặc dùng "Đổi hộ" nếu gắn nhầm hộ.')
    ten = con.execute('SELECT ho_ten FROM ho WHERE ma_ho = ?', (t['ma_ho'],)).fetchone()
    with csdl.giao_dich(con):
        con.execute('DELETE FROM thua WHERE ma_thua = ?', (ma_thua,))
        tb = f'Đã bỏ thửa {t["so_thua"]} tờ {t["so_to"]} khỏi hồ sơ hộ {t["ma_ho"]} {ten[0] if ten else ""}'.rstrip() + '.'
        csdl.ghi_nhat_ky(con, 'Bỏ gắn hộ khỏi thửa', tb)
    return tb


def chuyen_thua(con, ma_thua: int, ma_ho_moi: int) -> str:
    """Chuyển một thửa (kèm các dòng mục 1 gắn với thửa) sang hộ khác."""
    t = con.execute('SELECT * FROM thua WHERE ma_thua = ?', (ma_thua,)).fetchone()
    if t is None:
        raise LoiNhap(f'Không có thửa mã {ma_thua}.')
    kiem_ds_ho_nhan_viec(con, (t['ma_ho'], ma_ho_moi))
    kiem_quyen(con, 'sua_ho_so')                 # 1.0.57: vai trò tài khoản máy chủ (phan_quyen)
    moi = doc_ho(con, ma_ho_moi)
    if t['ma_ho'] == ma_ho_moi:
        raise LoiNhap('Thửa đã thuộc hộ này.')
    with csdl.giao_dich(con):
        n = con.execute('SELECT COALESCE(MAX(thu_tu), 0) + 1 FROM thua WHERE ma_ho = ?', (ma_ho_moi,)).fetchone()[0]
        con.execute('UPDATE thua SET ma_ho = ?, thu_tu = ? WHERE ma_thua = ?', (ma_ho_moi, n, ma_thua))
        so = con.execute('UPDATE ct_dat SET ma_ho = ? WHERE ma_thua = ?', (ma_ho_moi, ma_thua)).rowcount
        if so:
            bay_gio = datetime.now().isoformat(timespec='seconds')
            con.execute('UPDATE ho SET luu_luc = ? WHERE ma_ho IN (?, ?)', (bay_gio, t['ma_ho'], ma_ho_moi))
        tb = (f'Đã chuyển thửa {t["so_thua"]} tờ {t["so_to"]} ({so_vn(t["dt_thu_hoi"])} m²) từ hộ {t["ma_ho"]} '
              f'sang hộ {ma_ho_moi} {moi["ho_ten"]}' + (f', kèm {so} dòng bồi thường đất.' if so else '.'))
        csdl.ghi_nhat_ky(con, 'Chuyển thửa', tb)
    return tb


def goi_y_gop(con, ma_ho: int) -> list:
    """Các hộ khác xếp theo mức giống (cùng tên trước): [(ma_ho, mô tả, cùng_tên)]."""
    ho = doc_ho(con, ma_ho)
    ten = bo_dau(ho['ho_ten'])
    kq = []
    for r in con.execute('''SELECT h.ma_ho, h.ho_ten, h.dia_chi, COUNT(t.ma_thua) AS so_thua FROM ho h
                            LEFT JOIN thua t ON t.ma_ho = h.ma_ho WHERE h.ma_ho <> ? GROUP BY h.ma_ho
                            ORDER BY h.thu_tu''', (ma_ho,)):
        cung = bo_dau(r['ho_ten']) == ten
        kq.append((r['ma_ho'], f'{r["ma_ho"]} - {r["ho_ten"]} - {r["dia_chi"]} ({r["so_thua"]} thửa)', cung))
    kq.sort(key=lambda x: not x[2])
    return kq

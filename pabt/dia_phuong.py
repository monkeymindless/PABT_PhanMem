"""Hồ sơ địa phương (pabt_profile.json, 0.9.85 - người dùng 14/10/2026): thông tin cơ quan, căn cứ pháp lý, mốc thời hạn, tỷ lệ kinh
phí tổ chức thực hiện (mức tối đa theo loại dự án, làm tròn, phân bổ 85 / 15), quy tắc bản in và vị trí cột của mẫu in - đưa ra một
file JSON để dùng phần mềm ở địa phương khác (TP.HCM, Bình Dương, Long An…) mà không sửa mã nguồn.

Nguồn: pabt/pabt_profile.json đóng kèm (mặc định Đồng Nai, đi theo gói .pabtcn) <- ghi đè bởi <thư mục máy>/pabt_profile.json
(%APPDATA%\\PABT; chỉ cần các mục khác mặc định - trộn sâu theo khóa; danh sách thay nguyên). File máy sai (JSON hỏng, thiếu / sai
kiểu, tỷ lệ phân bổ không đủ 100%…) -> bỏ qua, dùng mặc định, lỗi ghi ở loi() để màn hình báo.

Không Qt. Module đọc giá trị lúc nạp (to_chuc, lap_pa, thoi_han, du_thao) đăng ký bằng dang_ky(ham): ham(hồ sơ) chạy ngay và chạy
lại mỗi khi nap_lai() (nhập gói .pabtcfg) - nơi dùng đọc thuộc tính module lúc gọi (to_chuc.TEN, lap_pa.LOAI_KINH_PHI) nên thấy
giá trị mới không cần mở lại phần mềm.
"""
from __future__ import annotations
import copy
import json
import os
import re
from decimal import Decimal, InvalidOperation
from pathlib import Path

TEN_FILE = 'pabt_profile.json'
LOAI = 'pabt_profile'
PHIEN_BAN_CAU_TRUC = 1

_NHO: dict = {}                 # khóa (mtime gốc, mtime máy) -> hồ sơ đã trộn
_LOI: list = []                 # lỗi của file máy lần đọc gần nhất
_DANG_KY: list = []


class LoiHoSo(ValueError):
    """Hồ sơ địa phương không hợp lệ (thông báo tiếng Việt, liệt kê từng lỗi)."""


# ---------------------------------------------------------------- vị trí file
def file_goc() -> Path:
    from . import tai_nguyen
    return tai_nguyen(TEN_FILE)


def thu_muc_may() -> Path:
    """%APPDATA%\\PABT (PABT_THU_MUC_MAY khi kiểm thử) - cùng thư mục máy với may_chu / cap_nhat."""
    return Path(os.environ.get('PABT_THU_MUC_MAY') or Path(os.environ.get('APPDATA') or Path.home()) / 'PABT')


def file_may() -> Path:
    return thu_muc_may() / TEN_FILE


# ---------------------------------------------------------------- đọc, trộn, kiểm tra
def _doc_json(p: Path) -> dict:
    try:
        du_lieu = json.loads(Path(p).read_text(encoding='utf-8-sig'))
    except (OSError, UnicodeDecodeError) as e:
        raise LoiHoSo(f'Không đọc được {Path(p).name}: {e}') from None
    except json.JSONDecodeError as e:
        raise LoiHoSo(f'{Path(p).name} sai cú pháp JSON (dòng {e.lineno}, cột {e.colno}): {e.msg}') from None
    if not isinstance(du_lieu, dict):
        raise LoiHoSo(f'{Path(p).name}: nội dung phải là một đối tượng JSON {{…}}.')
    return du_lieu


def tron(goc: dict, them: dict) -> dict:
    """Trộn sâu: khóa của them đè khóa của goc; đối tượng con trộn tiếp, danh sách / giá trị thay nguyên."""
    kq = copy.deepcopy(goc)
    for k, v in them.items():
        if isinstance(v, dict) and isinstance(kq.get(k), dict):
            kq[k] = tron(kq[k], v)
        else:
            kq[k] = copy.deepcopy(v)
    return kq


def _so(v, ten: str, loi: list, toi_thieu=None, toi_da=None):
    try:
        d = Decimal(str(v).strip())
    except (InvalidOperation, ValueError):
        loi.append(f'{ten}: "{v}" không phải số (ghi dạng "2.5").')
        return None
    if not d.is_finite() or (toi_thieu is not None and d < toi_thieu) or (toi_da is not None and d > toi_da):
        loi.append(f'{ten}: {v} ngoài khoảng cho phép ({toi_thieu} - {toi_da}).')
        return None
    return d


_RE_COT = re.compile(r'^[A-Z]{1,3}$')


CO_CHU_WORD = ('co_quan', 'quoc_hieu', 'tieu_ngu', 'so_ngay', 'du_thao', 'ten_loai', 'trich_yeu', 'du_an', 'thong_tin', 'de_muc',
               'nguon_goc', 'bang', 'ghi_chu', 'chu_ky')


def kiem_tra_mau_word(mw) -> list:
    """Lỗi của mục ban_in.mau_word (thông số mẫu Word phương án chi tiết / bổ sung / điều chỉnh)."""
    loi = []
    if not isinstance(mw, dict):
        return ['ban_in.mau_word: thiếu (lề, cỡ chữ, trích yếu của mẫu Word).']

    def so(v, ten, lo, hi):
        if isinstance(v, bool) or not isinstance(v, (int, float)) or not lo <= v <= hi:
            loi.append(f'ban_in.mau_word.{ten}: số từ {lo} đến {hi}.')
    le = mw.get('le_mm')
    if not isinstance(le, dict) or set(le) != {'trai', 'phai', 'tren', 'duoi'}:
        loi.append('ban_in.mau_word.le_mm: đủ bốn lề trai / phai / tren / duoi (mm).')
    else:
        for k, v in le.items():
            so(v, f'le_mm.{k}', 0, 60)
    co = mw.get('co_chu')
    if not isinstance(co, dict) or set(co) != set(CO_CHU_WORD):
        loi.append('ban_in.mau_word.co_chu: đủ các cỡ chữ ' + ', '.join(CO_CHU_WORD) + ' (pt).')
    else:
        for k, v in co.items():
            so(v, f'co_chu.{k}', 6, 24)
    if not isinstance(mw.get('trich_yeu'), str) or not mw['trich_yeu'].strip():
        loi.append('ban_in.mau_word.trich_yeu: chữ trích yếu văn bản (in hoa).')
    so(mw.get('thut_dau_dong_mm'), 'thut_dau_dong_mm', 0, 30)
    so(mw.get('gach_chan_ho_pt'), 'gach_chan_ho_pt', 0, 8)
    so(mw.get('duong_ke_du_an_mm'), 'duong_ke_du_an_mm', 0, 180)
    return loi


def kiem_tra(hs: dict) -> list:
    """Danh sách lỗi của hồ sơ ĐÃ TRỘN (rỗng = hợp lệ)."""
    loi = []
    if hs.get('loai') != LOAI:
        loi.append(f'Mục "loai" phải là "{LOAI}".')
    if hs.get('phien_ban_cau_truc') != PHIEN_BAN_CAU_TRUC:
        loi.append(f'"phien_ban_cau_truc" = {hs.get("phien_ban_cau_truc")!r}: phần mềm này đọc cấu trúc {PHIEN_BAN_CAU_TRUC}.')
    cq = hs.get('co_quan')
    if not isinstance(cq, dict):
        loi.append('Thiếu mục "co_quan".')
    else:
        for k in ('vai_tro', 'ten', 'truc_thuoc', 'dia_chi'):
            if not isinstance(cq.get(k), str):
                loi.append(f'co_quan.{k}: phải là chữ.')
        if 'ten_phan_mem' in cq and not isinstance(cq['ten_phan_mem'], str):
            loi.append('co_quan.ten_phan_mem: phải là chữ.')
        bm = cq.get('ban_in_mac_dinh')
        if not isinstance(bm, dict) or not all(isinstance(v, str) for v in bm.values()):
            loi.append('co_quan.ban_in_mac_dinh: các giá trị phải là chữ.')
    cc = hs.get('can_cu_phap_ly')
    if not isinstance(cc, dict) or not isinstance(cc.get('kinh_phi_to_chuc'), str) or not isinstance(cc.get('tham_dinh'), str):
        loi.append('can_cu_phap_ly: cần "kinh_phi_to_chuc" và "tham_dinh" (chữ).')
    elif not isinstance(cc.get('to_trinh'), list) or not all(isinstance(x, str) and x.strip() for x in cc['to_trinh']):
        loi.append('can_cu_phap_ly.to_trinh: danh sách các dòng "Căn cứ …" (chữ).')
    th = hs.get('thoi_han')
    for k in ('tham_dinh', 'thu_hoi_nn', 'thu_hoi_pnn', 'van_dong', 'niem_yet', 'doi_thoai'):
        m = th.get(k) if isinstance(th, dict) else None
        if not isinstance(m, dict) or not isinstance(m.get('so_ngay'), int) or isinstance(m.get('so_ngay'), bool) \
                or not 1 <= m['so_ngay'] <= 3650:
            loi.append(f'thoi_han.{k}.so_ngay: số nguyên 1 - 3650.')
    kp = hs.get('kinh_phi_to_chuc')
    if not isinstance(kp, dict):
        loi.append('Thiếu mục "kinh_phi_to_chuc".')
    else:
        lo = kp.get('loai')
        if not isinstance(lo, dict) or set(lo) != {'tuyen', 'khac'}:
            loi.append('kinh_phi_to_chuc.loai: đúng hai loại "tuyen" (theo tuyến) và "khac".')
        else:
            for k, v in lo.items():
                if not isinstance(v, dict) or not isinstance(v.get('ten'), str):
                    loi.append(f'kinh_phi_to_chuc.loai.{k}.ten: phải là chữ.')
                else:
                    _so(v.get('ty_le_toi_da'), f'kinh_phi_to_chuc.loai.{k}.ty_le_toi_da', loi, Decimal('0.01'), Decimal(100))
        lt = kp.get('lam_tron_den')
        if not isinstance(lt, int) or isinstance(lt, bool) or not -9 <= lt <= 0:
            loi.append('kinh_phi_to_chuc.lam_tron_den: số nguyên từ -9 đến 0 (-3 = làm tròn đến nghìn đồng).')
        pb = kp.get('phan_bo')
        if not isinstance(pb, list) or not pb:
            loi.append('kinh_phi_to_chuc.phan_bo: danh sách {"ten", "ty_le"}.')
        else:
            tong = Decimal(0)
            for i, x in enumerate(pb):
                d = _so(x.get('ty_le') if isinstance(x, dict) else None, f'kinh_phi_to_chuc.phan_bo[{i}].ty_le', loi,
                        Decimal(0), Decimal(100))
                tong += d or 0
            if tong != 100:
                loi.append(f'kinh_phi_to_chuc.phan_bo: tổng tỷ lệ phải bằng 100% (đang {tong}%).')
    qt = hs.get('quy_tac_kiem_tra')
    if not isinstance(qt, dict):
        loi.append('Thiếu mục "quy_tac_kiem_tra".')
    else:
        hm = qt.get('han_muc_dat_o_m2')
        if not isinstance(hm, dict):
            loi.append('quy_tac_kiem_tra.han_muc_dat_o_m2: {"xa": số hoặc null, "phuong": …, "dac_khu": …}.')
        else:
            for k, v in hm.items():
                if v is not None:
                    _so(v, f'quy_tac_kiem_tra.han_muc_dat_o_m2.{k}', loi, Decimal(1), Decimal(100000))
        n = qt.get('nhan_khau_canh_bao')
        if not isinstance(n, int) or isinstance(n, bool) or not 1 <= n <= 200:
            loi.append('quy_tac_kiem_tra.nhan_khau_canh_bao: số nguyên 1 - 200.')
        _so(qt.get('ty_le_toi_da_tai_san'), 'quy_tac_kiem_tra.ty_le_toi_da_tai_san', loi, Decimal(1), Decimal(500))
    bi = hs.get('ban_in')
    if not isinstance(bi, dict) or not isinstance(bi.get('che_cccd_ban_du_thao'), bool):
        loi.append('ban_in.che_cccd_ban_du_thao: true / false.')
    else:
        ng = bi.get('nguon_goc') or {}
        if ng.get('can_ngang') not in ('left', 'justify', 'center', 'distributed'):
            loi.append('ban_in.nguon_goc.can_ngang: "left" / "justify" / "center" / "distributed".')
        if ng.get('can_doc') not in ('top', 'center', 'bottom', 'justify'):
            loi.append('ban_in.nguon_goc.can_doc: "top" / "center" / "bottom" / "justify".')
        td = ng.get('thut_dau_cm', 0)
        if isinstance(td, bool) or not isinstance(td, (int, float)) or not 0 <= td <= 5:
            loi.append('ban_in.nguon_goc.thut_dau_cm: số cm từ 0 đến 5 (0 = không thụt đầu dòng).')
        nb = ng.get('thut_dau_nbsp', 8)
        if isinstance(nb, bool) or not isinstance(nb, int) or not 0 <= nb <= 20:
            loi.append('ban_in.nguon_goc.thut_dau_nbsp: số khoảng trắng không ngắt từ 0 đến 20 (0 = theo thut_dau_cm).')
        loi.extend(kiem_tra_mau_word(bi.get('mau_word')))
        for loai, le in (bi.get('le_trang') or {}).items():
            if loai not in ('chi_tiet', 'tong_hop') or not isinstance(le, dict):
                loi.append('ban_in.le_trang: chỉ có "chi_tiet" / "tong_hop", mỗi mục là các lề top / bottom / left / right / '
                           'header / footer (inch).')
                continue
            for k, v in le.items():
                sai = k not in ('top', 'bottom', 'left', 'right', 'header', 'footer') or isinstance(v, bool)
                if sai or not isinstance(v, (int, float)) or not 0 <= v <= 3:
                    loi.append(f'ban_in.le_trang.{loai}.{k}: lề tính bằng inch, từ 0 đến 3.')
    mi = hs.get('mau_in')
    # 1.0.19: phương án chi tiết chỉ còn bản Word - mục mau_in.IN_CHITIET (cột mẫu Excel) của hồ sơ cũ được bỏ qua
    can = {'IN_BANGTONGHOP': ('stt', 'ho_ten', 'dia_chi', 'so_to', 'so_thua', 'loai_dat', 'dt_thu_hoi', 'dt_nong_nghiep', 'dt_lua',
                              'dt_phi_nong_nghiep', 'dt_o', 'vi_tri', 'tien_dat', 'tien_tai_san', 'tien_cay_vat_nuoi',
                              'ho_tro_dao_tao', 'ho_tro_on_dinh', 'thuong', 'tong', 'nguon_goc', 'tai_dinh_cu', 'ghi_chu')}
    for mau, khoa in can.items():
        m = mi.get(mau) if isinstance(mi, dict) else None
        cot = m.get('cot') if isinstance(m, dict) else None
        if not isinstance(cot, dict):
            loi.append(f'mau_in.{mau}.cot: thiếu.')
            continue
        thieu = [k for k in khoa if not isinstance(cot.get(k), str) or not _RE_COT.match(cot[k])]
        if thieu:
            loi.append(f'mau_in.{mau}.cot: thiếu / sai chữ cột (A, B… AD) của {", ".join(thieu)}.')
        elif len(set(cot[k] for k in khoa)) != len(khoa):
            loi.append(f'mau_in.{mau}.cot: hai trường trùng một cột.')
    bth = mi.get('IN_BANGTONGHOP') if isinstance(mi, dict) else None
    if isinstance(bth, dict):
        d = bth.get('dong_du_lieu_dau')
        if not isinstance(d, int) or isinstance(d, bool) or not 2 <= d <= 200:
            loi.append('mau_in.IN_BANGTONGHOP.dong_du_lieu_dau: số nguyên 2 - 200.')
        cc_ = bth.get('cot_cong')
        if not isinstance(cc_, list) or not all(isinstance(x, str) and _RE_COT.match(x) for x in cc_):
            loi.append('mau_in.IN_BANGTONGHOP.cot_cong: danh sách chữ cột.')
        if not isinstance(bth.get('cot_cuoi'), str) or not _RE_COT.match(bth['cot_cuoi']):
            loi.append('mau_in.IN_BANGTONGHOP.cot_cuoi: chữ cột cuối vùng in (vd "Y").')
    return loi


def kiem_tra_file(p) -> dict:
    """Đọc + trộn với mặc định + kiểm tra một file hồ sơ (file máy / file trong gói .pabtcfg). Trả hồ sơ đã trộn hoặc LoiHoSo."""
    them = _doc_json(Path(p))
    hs = tron(_doc_json(file_goc()), them)
    loi = kiem_tra(hs)
    if loi:
        raise LoiHoSo(f'{Path(p).name} chưa hợp lệ:\n- ' + '\n- '.join(loi))
    return hs


def _moc(p: Path):
    try:
        st = p.stat()
        return st.st_mtime_ns, st.st_size
    except OSError:
        return None


def doc(lam_moi: bool = False) -> dict:
    """Hồ sơ địa phương đang dùng (mặc định trộn file máy). Nhớ theo mtime / cỡ của hai file - sửa file là đọc lại.
    KHÔNG sửa đối tượng trả về (dùng chung)."""
    goc, may = file_goc(), file_may()
    khoa = (str(goc), _moc(goc), str(may), _moc(may))
    if not lam_moi and khoa in _NHO:
        return _NHO[khoa]
    hs = _doc_json(goc)
    loi_goc = kiem_tra(hs)
    if loi_goc:                                         # file đóng kèm hỏng: lỗi đóng gói - báo rõ, không chạy với số liệu sai
        raise LoiHoSo('Hồ sơ địa phương đóng kèm (pabt/pabt_profile.json) hỏng:\n- ' + '\n- '.join(loi_goc))
    _LOI.clear()
    if khoa[3] is not None:
        try:
            hs = kiem_tra_file(may)
        except LoiHoSo as e:
            _LOI.append(str(e))                         # file máy sai: dùng mặc định, màn hình báo (loi())
    _NHO.clear()
    _NHO[khoa] = hs
    return hs


def loi() -> list:
    """Lỗi của file hồ sơ trên máy lần đọc gần nhất (rỗng = không có / hợp lệ)."""
    doc()
    return list(_LOI)


def lay(duong: str, mac_dinh=None):
    """Giá trị theo đường "a.b.c" (vd 'kinh_phi_to_chuc.lam_tron_den')."""
    x = doc()
    for k in duong.split('.'):
        if not isinstance(x, dict) or k not in x:
            return mac_dinh
        x = x[k]
    return x


def ten_ho_so() -> str:
    return str(lay('ten_ho_so', '') or '')


# ---------------------------------------------------------------- giá trị dùng chung
def ty_le_kinh_phi() -> dict:
    """{'tuyen': (tên, tỷ lệ tối đa Decimal), 'khac': (…)} - dạng lap_pa.LOAI_KINH_PHI."""
    return {k: (v['ten'], Decimal(str(v['ty_le_toi_da']))) for k, v in lay('kinh_phi_to_chuc.loai').items()}


def phan_bo_kinh_phi() -> list:
    """[(tên, tỷ lệ % Decimal)] - phân bổ kinh phí tổ chức thực hiện (mặc định 85 / 15)."""
    return [(x.get('ten', ''), Decimal(str(x['ty_le']))) for x in lay('kinh_phi_to_chuc.phan_bo')]


def so_cot(chu: str) -> int:
    from openpyxl.utils import column_index_from_string
    return column_index_from_string(chu)


def cot_mau(mau: str) -> dict:
    """{trường: số cột (1 = A)} của mẫu in (IN_BANGTONGHOP)."""
    return {k: so_cot(v) for k, v in lay(f'mau_in.{mau}.cot').items()}


# ---------------------------------------------------------------- ghi file máy, nạp lại
def mac_dinh() -> dict:
    """Hồ sơ đóng kèm phần mềm (chưa trộn file máy)."""
    return _doc_json(file_goc())


def khac_mac_dinh(hs: dict, goc: dict | None = None) -> dict:
    """Phần của hs KHÁC hồ sơ mặc định (đối tượng con so từng khóa, danh sách / giá trị so nguyên) - file máy chỉ ghi phần này:
    bản cập nhật sau đổi mặc định (vd thêm mục mới) vẫn có hiệu lực với các mục người dùng không sửa."""
    goc = mac_dinh() if goc is None else goc
    kq = {}
    for k, v in hs.items():
        g = goc.get(k)
        if isinstance(v, dict) and isinstance(g, dict):
            con = khac_mac_dinh(v, g)
            if con:
                kq[k] = con
        elif k not in goc or v != g:
            kq[k] = copy.deepcopy(v)
    return kq


def luu_cau_hinh(hs: dict) -> Path | None:
    """Lưu hồ sơ ĐẦY ĐỦ đã sửa (màn hình Cấu hình nghiệp vụ): kiểm tra, ghi phần khác mặc định làm file máy; không khác gì thì xóa
    file máy (dùng mặc định). Trả file máy hoặc None."""
    loi_ = kiem_tra(tron(mac_dinh(), hs))
    if loi_:
        raise LoiHoSo('Cấu hình chưa hợp lệ:\n- ' + '\n- '.join(loi_))
    khac = khac_mac_dinh(hs)
    if not khac:
        khoi_phuc_mac_dinh()
        return None
    return ghi_may(khac)


def dat_muc_may(khoa: tuple, gia_tri) -> Path | None:
    """Đặt (gia_tri) hoặc bỏ (None) MỘT mục của file hồ sơ máy theo đường khoa = ('ban_in', 'mau_word'): đọc file máy hiện có, sửa
    đúng mục đó, kiểm tra cả hồ sơ rồi ghi (các mục khác của file máy giữ nguyên). Mục rỗng sau khi bỏ -> xóa nhánh; file máy rỗng ->
    đổi tên .bak. Trả file máy hoặc None."""
    p = file_may()
    cu = _doc_json(p) if p.exists() else {}
    cur = cu
    for k in khoa[:-1]:
        cur = cur.setdefault(k, {})
    if gia_tri is None:
        cur.pop(khoa[-1], None)
        for i in range(len(khoa) - 1, 0, -1):               # bỏ các nhánh cha đã rỗng
            x = cu
            for k in khoa[:i - 1]:
                x = x[k]
            if not x.get(khoa[i - 1]):
                x.pop(khoa[i - 1], None)
    else:
        cur[khoa[-1]] = copy.deepcopy(gia_tri)
    if not cu:
        khoi_phuc_mac_dinh()
        return None
    return ghi_may(cu)


def khoi_phuc_mac_dinh() -> None:
    """Bỏ file máy (dùng lại hồ sơ đóng kèm). File cũ đổi tên .bak (không xóa hẳn)."""
    p = file_may()
    if p.exists():
        os.replace(p, p.with_name(p.name + '.bak'))
    nap_lai()


def ghi_may(hs: dict) -> Path:
    """Ghi hồ sơ (đã kiểm tra) làm file máy: ghi file tạm rồi thay (không để file dở khi lỗi giữa chừng)."""
    loi_ = kiem_tra(tron(_doc_json(file_goc()), hs))
    if loi_:
        raise LoiHoSo('Hồ sơ địa phương chưa hợp lệ:\n- ' + '\n- '.join(loi_))
    p = file_may()
    p.parent.mkdir(parents=True, exist_ok=True)
    tam = p.with_name(p.name + '.tmp')
    tam.write_text(json.dumps(hs, ensure_ascii=False, indent=2), encoding='utf-8')
    os.replace(tam, p)
    nap_lai()
    return p


def dang_ky(ham) -> None:
    """ham(hồ sơ): cập nhật giá trị của module theo hồ sơ - chạy ngay và sau mỗi lần nap_lai()."""
    _DANG_KY.append(ham)
    ham(doc())


def nap_lai() -> dict:
    """Đọc lại hồ sơ (sau khi nhập gói / sửa file máy) và cập nhật các module đã đăng ký."""
    _NHO.clear()
    hs = doc(lam_moi=True)
    for ham in list(_DANG_KY):
        ham(hs)
    return hs

"""Kiểm đếm thực địa - phần máy tính (0.9.87; ứng dụng điện thoại LARC Mobile là dự án RIÊNG ở di_dong/, hai bên chỉ nối qua
file .json - giao ước ở di_dong/README.md).

1. xuat_du_lieu_di_dong: file .json "larc_field_du_lieu" mở trong ứng dụng điện thoại: hộ + thửa, danh mục có mã (nhà / vật kiến trúc /
   vật nuôi), tên loài cây, bản đồ thửa đổi sang WGS84, tham số VN-2000 (toa_do.tham_so_datum), kinh tuyến trục.
2. nhap_ket_qua_kiem_dem: file .json kết quả -> phương án hộ (lap_pa.BoSoan) qua CÙNG đường "Dán danh sách tài sản" (khớp danh mục ->
   dòng danh mục, không khớp -> hạng mục ngoài danh mục; cây có số đo đường kính / chu vi -> quy cách; dòng mục 0 = ghi lại biên bản,
   tự phân loại). Ảnh gửi kèm -> thư mục "Anh_kiem_dem/<mã hộ>" cạnh file dự án + bảng anh_hien_trang; GPS -> ghi chú hộ. Mỗi hộ
   lưu một lần (một bước Hoàn tác), hộ đang mở chỉ xem / không tồn tại -> báo lỗi dòng.
3. gan_anh_hien_trang: quét thư mục ảnh, gắn ảnh vào hộ theo số CCCD / họ tên không dấu / "HO<stt>" trong tên file -> bảng
   anh_hien_trang (lược đồ v16). Tên trùng nhiều hộ: không gắn, báo lại.
Không Qt."""
from __future__ import annotations
import json
import re
from datetime import datetime
from pathlib import Path

from . import csdl
from .lap_pa import LoiNhap, bo_dau

PHIEN_BAN_PHIEU = 2                 # phiên bản file .json phiếu ghi ra (1 = phiếu 0.9.87 - vẫn nhập được)
LOAI_GOI_DU_LIEU = 'larc_field_du_lieu'   # file dữ liệu dự án gửi sang ứng dụng điện thoại (di_dong/README.md mục 1)
MUC_PHIEU = ((2, 'Nhà, công trình'), (3, 'Cây trồng'), (7, 'Vật nuôi'))
THU_MUC_ANH = 'Anh_kiem_dem'        # ảnh gửi kèm phiếu lưu ở <thư mục file dự án>/Anh_kiem_dem/<mã hộ>/
ANH_TOI_DA = 25 * 1024 * 1024       # một ảnh gửi kèm (byte) - lớn hơn: bỏ, báo lại
DUOI_ANH = ('.jpg', '.jpeg', '.png', '.webp', '.bmp', '.heic', '.tif', '.tiff')
BANG_ANH = 'anh_hien_trang'
SQL_BANG_ANH = f'''CREATE TABLE IF NOT EXISTS {BANG_ANH} (
    id INTEGER PRIMARY KEY,
    ma_ho INTEGER NOT NULL REFERENCES ho(ma_ho) ON UPDATE CASCADE ON DELETE CASCADE,
    duong_dan TEXT NOT NULL,             -- đường dẫn đầy đủ của ảnh lúc gắn
    ten_file TEXT NOT NULL,
    khop_theo TEXT NOT NULL DEFAULT '',  -- cccd / ho_ten / stt
    luc TEXT NOT NULL,
    UNIQUE (ma_ho, duong_dan)
)'''


# ---------------------------------------------------------------- 1. dữ liệu dự án cho ứng dụng điện thoại
def _la_nha(ten: str, phan_loai: str) -> bool:
    """Mục danh mục là nhà ở (thẻ "Nhà ở" của phiếu): tên bắt đầu bằng Nhà / Biệt thự / Gác lửng hoặc phân loại nhà ở."""
    t = bo_dau(ten or '').lower().lstrip()
    return t.startswith(('nha ', 'biet thu', 'gac lung')) or 'nha o' in bo_dau(phan_loai or '').lower()


def _ban_do_wgs84(con, kinh_tuyen: float) -> list:
    """Thửa đã nhập bản vẽ (.dxf / .kml) -> [{so_to, so_thua, loai, ma_ho, trang_thai, vong: [[vĩ độ, kinh độ]…]}] (6 chữ số lẻ ~ 0,1 m)."""
    from . import ban_do_cad
    from .toa_do import vn2000_sang_wgs84
    ra = []
    for t in ban_do_cad.doc_ban_do(con):
        vong = [[round(vd, 7), round(kd, 7)] for vd, kd in (vn2000_sang_wgs84(x, y, kinh_tuyen) for x, y in t.toa_do)]
        if len(vong) >= 3:
            ra.append(dict(so_to=t.so_to, so_thua=t.so_thua, loai=t.loai_dat or '', ma_ho=t.ma_ho, trang_thai=t.trang_thai, vong=vong))
    return ra


def _gia(x) -> int:
    """Đơn giá (TEXT Decimal trong CSDL) -> số nguyên đồng cho ứng dụng điện thoại (chỉ để hiện / tạm tính; máy tính tính lại khi nhập)."""
    from .tien import D, lam_tron
    try:
        return int(lam_tron(D(x or 0), 0))
    except (ArithmeticError, ValueError, TypeError):
        return 0


def _so_hoac_none(x):
    return None if x is None else float(x)


def danh_muc_di_dong(con=None) -> dict:
    """Danh mục đơn giá cho ứng dụng điện thoại: nha / dm2 / vat_nuoi = [[mã, tên, ĐVT, đơn giá]], cay = tên loài, cay_chi_tiet = {loài:
    {dk, tuoi, dvt, muc: [[mã, tên, ĐVT, đơn giá, đk từ, đk đến, tuổi từ, tuổi đến]]}} (dk: loài có mục theo đường kính thân - khoảng
    (từ, đến] cm; tuoi: có mục theo năm tuổi), goi_y. con None = bộ đơn giá ĐÓNG GÓI (don_gia.file_goc, chỉ đọc) - file nhúng vào ứng
    dụng điện thoại dựng lại giống nhau trên mọi máy."""
    from .cay_trong import khoang_duong_kinh, ten_goc
    from .hieu_tai_san import bang_tuoi
    dong_lai = con is None
    if dong_lai:
        import sqlite3
        from . import don_gia
        con = sqlite3.connect(csdl.uri_chi_doc(don_gia.file_goc()), uri=True)
        con.row_factory = sqlite3.Row
    try:
        ds = con.execute('SELECT ma, nhom, phan_loai, ten, dvt, don_gia FROM dm_taisan ORDER BY nhom, LENGTH(ma), ma').fetchall()
    finally:
        if dong_lai:
            con.close()
    nha, dm2, vat_nuoi, cay = [], [], [], {}
    tuoi = bang_tuoi(r['ten'] or '' for r in ds if r['nhom'] == 3)
    for r in ds:
        ten = r['ten'] or ''
        muc = [str(r['ma'] or ''), ten, r['dvt'] or '', _gia(r['don_gia'])]
        if 'vat nuoi' in bo_dau(r['phan_loai'] or '').lower():
            vat_nuoi.append(muc)
        elif r['nhom'] == 2:
            (nha if _la_nha(ten, r['phan_loai']) else dm2).append(muc)
        elif r['nhom'] == 3:
            t = ten_goc(ten).strip()
            if not t:
                continue
            ct = cay.setdefault(bo_dau(t).lower(), dict(ten=t, dk=False, tuoi=False, dvt=muc[2], muc=[]))
            k, tu = khoang_duong_kinh(ten), tuoi.get(ten)
            ct['dk'] = ct['dk'] or k is not None
            ct['tuoi'] = ct['tuoi'] or tu is not None
            ct['muc'].append(muc + [_so_hoac_none(k.tu) if k else None, _so_hoac_none(k.den) if k else None,
                                    tu[0] if tu else None, tu[1] if tu else None])
    ds_cay = sorted(cay.values(), key=lambda x: bo_dau(x['ten']).lower())
    goi_y = {2: [[m[1], m[2]] for m in nha + dm2], 3: [[c['ten'], 'cây'] for c in ds_cay], 7: [[m[1], m[2]] for m in vat_nuoi]}
    return dict(nha=nha, dm2=dm2, vat_nuoi=vat_nuoi, cay=[c['ten'] for c in ds_cay], goi_y=goi_y,
                cay_chi_tiet={c['ten']: {k: v for k, v in c.items() if k != 'ten'} for c in ds_cay})


def _ban_do_va_datum() -> dict:
    from . import ban_do_cad, __version__
    from .toa_do import kinh_tuyen_truc, tham_so_datum
    datum, quy_uoc, _ = tham_so_datum()
    return dict(phien_ban=__version__, kinh_tuyen=kinh_tuyen_truc(), datum=list(datum), quy_uoc=quy_uoc,
                mau_trang_thai={k: list(v) for k, v in ban_do_cad.TRANG_THAI.items()})


def du_lieu_mac_dinh() -> dict:
    """Dữ liệu khung nhúng sẵn trong ứng dụng điện thoại (kiểm đếm độc lập, chưa có file dự án): không hộ, đủ danh mục đơn giá."""
    return dict(du_an='', ho=[], ban_do=[], trang_thai_ho={}, **_ban_do_va_datum(), **danh_muc_di_dong(None))


def xuat_du_lieu_mac_dinh(file_ra) -> Path:
    """Ghi du_lieu_mac_dinh() ra file .json (CLI `chay.py xuat-danh-muc-di-dong`; dự án di_dong/ nhúng file này khi dựng)."""
    return _ghi_nguyen_tu(Path(file_ra), json.dumps(du_lieu_mac_dinh(), ensure_ascii=False, separators=(',', ':')))


def du_lieu_phieu(con) -> dict:
    """Phần "du_lieu" của file dữ liệu cho ứng dụng điện thoại: hộ + thửa, danh mục có mã + đơn giá, loài cây (quy cách đường kính /
    năm tuổi), bản đồ (WGS84), tham số VN-2000."""
    from . import ban_do_cad
    thua = {}
    for r in con.execute('SELECT ma_ho, so_to, so_thua, loai_dat, dt_thu_hoi FROM thua ORDER BY thu_tu, ma_thua'):
        thua.setdefault(r['ma_ho'], []).append(dict(to=str(r['so_to'] or ''), thua=str(r['so_thua'] or ''),
                                                    loai=str(r['loai_dat'] or ''), dt=str(r['dt_thu_hoi'] or '')))
    cot_ho = {r[1] for r in con.execute('PRAGMA table_info(ho)')}
    sdt = 'dien_thoai' if 'dien_thoai' in cot_ho else "''"
    ho = [dict(ma=r['ma_ho'], stt=r['thu_tu'], ten=' '.join(str(r['ho_ten'] or '').split()), cccd=(r['so_cccd'] or '').strip(),
               dia_chi=' '.join(str(r['dia_chi'] or '').split()), sdt=str(r['sdt'] or '').strip(), thua=thua.get(r['ma_ho'], []))
          for r in con.execute(f'SELECT ma_ho, thu_tu, ho_ten, so_cccd, dia_chi, {sdt} AS sdt FROM ho ORDER BY thu_tu, ma_ho')]
    chung = _ban_do_va_datum()
    da = con.execute('SELECT ten FROM du_an WHERE id = 1').fetchone()
    return dict(du_an=(da['ten'] if da else '') or '', ho=ho, ban_do=_ban_do_wgs84(con, chung['kinh_tuyen']),
                trang_thai_ho={str(k): v for k, v in ban_do_cad.trang_thai_ho(con).items()}, **chung, **danh_muc_di_dong(con))


def _ghi_nguyen_tu(ra: Path, noi: str) -> Path:
    ra.parent.mkdir(parents=True, exist_ok=True)
    tam = ra.with_name(ra.name + '.tmp')
    tam.write_text(noi, encoding='utf-8')
    tam.replace(ra)
    return ra


def goi_du_lieu_di_dong(con) -> dict:
    """File dữ liệu dự án cho ứng dụng điện thoại (di_dong/README.md mục 1): {"loai", "phien_ban", "luc", "du_lieu" (= du_lieu_phieu)}."""
    return dict(loai=LOAI_GOI_DU_LIEU, phien_ban=1, luc=datetime.now().isoformat(timespec='seconds'), du_lieu=du_lieu_phieu(con))


def ten_file_du_lieu(con) -> str:
    """Tên file mặc định: LARC_DuLieu_<tên dự án không dấu>.json."""
    da = con.execute('SELECT ten FROM du_an WHERE id = 1').fetchone()
    ten = re.sub(r'[^A-Za-z0-9]+', '_', bo_dau((da['ten'] if da else '') or '')).strip('_')[:60] or 'du_an'
    return f'LARC_DuLieu_{ten}.json'


def xuat_du_lieu_di_dong(con, file_ra) -> Path:
    """Ghi file .json dữ liệu dự án mở trong ứng dụng LARC Mobile (Android / iPhone)."""
    return _ghi_nguyen_tu(Path(file_ra), json.dumps(goi_du_lieu_di_dong(con), ensure_ascii=False))


# ---------------------------------------------------------------- 2. nhập kết quả
# File .json của phiếu: phien_ban 1 = {"ket_qua": {"<mã hộ>": [dòng]}}; phien_ban 2 (1.0.32, ứng dụng di động) thêm "ho_dan" {khóa: thông
# tin hộ} và "dat_dai" {khóa: [thửa / lô rừng]} - khóa là mã hộ của dự án (phiếu xuất từ dự án) hoặc "moi_<n>" (hộ ghi mới ở thực địa).
# Dòng: muc 2 / 3 / 7, ma_dm (mã bộ đơn giá đã chọn trên điện thoại - có thì áp thẳng), ten, dvt, so_luong, ty_le, so_do, kieu, ghi_chu.
NGUONG_TEN = 0.88                   # độ giống họ tên (difflib) tối thiểu khi khớp hộ theo tên


def _doc_file_phieu(file) -> dict:
    from .an_toan import LoiAnToan, kiem_tra_magic_bytes
    try:
        kiem_tra_magic_bytes(file, {'json'})            # 1.0.32: .json nhận qua Zalo / USB thật ra là chương trình / file khác
    except LoiAnToan as e:
        raise LoiNhap(str(e)) from None
    try:
        du = json.loads(Path(file).read_text(encoding='utf-8-sig'))
    except (OSError, ValueError) as e:
        raise LoiNhap(f'Không đọc được file kết quả kiểm đếm: {e}') from None
    if isinstance(du, dict) and du.get('loai') == LOAI_GOI_DU_LIEU:
        raise LoiNhap('Đây là file DỮ LIỆU DỰ ÁN gửi sang điện thoại, không phải kết quả kiểm đếm. Trên điện thoại: thẻ "6. Xuất .JSON" '
                      '-> gửi file kết quả về máy tính rồi nhập file đó.')
    if not isinstance(du, dict) or not isinstance(du.get('ket_qua'), dict):
        raise LoiNhap('File không phải kết quả của Phiếu kiểm đếm LARC (thiếu "ket_qua").')
    return du


def _dong_hop_le(ds) -> list:
    return [d for d in ds if isinstance(d, dict) and str(d.get('ten') or '').strip()] if isinstance(ds, list) else []


def doc_phieu(file) -> dict:
    """File .json (phiên bản 1 / 2) -> {'du_an', 'nam' (năm kiểm đếm - đổi "trồng năm …" ra năm tuổi), 'ho': [{'khoa', 'ma_ho' (int /
    None), 'thong_tin' {ho_ten, so_cccd, nguoi_su_dung, …}, 'thua' [{so_to, so_thua, tieu_khu, khoanh, lo, …}], 'dong' [dòng]}]}."""
    du = _doc_file_phieu(file)
    ho_dan = du.get('ho_dan') if isinstance(du.get('ho_dan'), dict) else {}
    dat_dai = du.get('dat_dai') if isinstance(du.get('dat_dai'), dict) else {}
    anh = du.get('anh') if isinstance(du.get('anh'), dict) else {}
    nam = None
    m = re.match(r'\s*(\d{4})-', str(du.get('luc') or ''))
    if m:
        nam = int(m.group(1))
    ho = []
    for khoa, ds in du['ket_qua'].items():
        tt = ho_dan.get(khoa) if isinstance(ho_dan.get(khoa), dict) else {}
        ma = tt.get('ma_ho', khoa)
        try:
            ma = int(str(ma).strip())
        except (TypeError, ValueError):
            ma = None
        thua = [t for t in (dat_dai.get(khoa) or []) if isinstance(t, dict)]
        a = [x for x in (anh.get(khoa) or []) if isinstance(x, dict) and isinstance(x.get('du_lieu'), str)] \
            if isinstance(anh.get(khoa), list) else []
        ho.append(dict(khoa=str(khoa), ma_ho=ma, thong_tin=tt, thua=thua, dong=_dong_hop_le(ds), anh=a, gps=_gps(tt.get('gps'))))
    return dict(du_an=str(du.get('du_an') or ''), nam=nam, ho=ho)


def _gps(g) -> dict | None:
    """{'lat', 'lon', 'acc'} của phiếu -> số kiểm tra trong vùng hợp lý (Việt Nam và lân cận), không thì None."""
    if not isinstance(g, dict):
        return None
    try:
        lat, lon, acc = float(g.get('lat')), float(g.get('lon')), float(g.get('acc') or 0)
    except (TypeError, ValueError):
        return None
    if not (-90 <= lat <= 90 and -180 <= lon <= 180) or lat != lat or lon != lon:
        return None
    return dict(lat=lat, lon=lon, acc=max(0.0, acc), luc=str(g.get('luc') or ''))


def chu_gps(g: dict, kinh_tuyen: float | None = None) -> str:
    """'Tọa độ kiểm đếm (GPS): 10.9876543, 106.8765432 (±5 m), VN-2000 X 1.215.432,10 Y 432.109,87' (X = Bắc như sổ địa chính).
    Không có dấu ";" - ghi chú hộ ngăn các đoạn bằng ";"."""
    from .tien import vn
    from .toa_do import wgs84_sang_vn2000
    dong, bac = wgs84_sang_vn2000(g['lat'], g['lon'], kinh_tuyen)
    return (f'{TIEN_TO_GPS} {g["lat"]:.7f}, {g["lon"]:.7f} (±{round(g["acc"])} m), VN-2000 X {vn(f"{bac:.2f}", 2)} '
            f'Y {vn(f"{dong:.2f}", 2)}')


TIEN_TO_GPS = 'Tọa độ kiểm đếm (GPS):'


def _ghi_gps(con, ma_ho: int, g: dict) -> bool:
    """Ghi tọa độ vào ghi chú hộ (thay đoạn "Tọa độ kiểm đếm (GPS): …" cũ, giữ phần ghi chú khác). Trả True khi ghi chú đổi."""
    from .lap_pa import kiem_ho_nhan_viec
    r = con.execute('SELECT ghi_chu FROM ho WHERE ma_ho = ?', (ma_ho,)).fetchone()
    if r is None:
        return False
    cu = [x.strip() for x in str(r['ghi_chu'] or '').split(';') if x.strip()]
    gc = '; '.join([x for x in cu if not x.startswith(TIEN_TO_GPS)] + [chu_gps(g)])
    if gc == '; '.join(cu):
        return False
    kiem_ho_nhan_viec(con, ma_ho)
    with csdl.giao_dich(con):
        con.execute('UPDATE ho SET ghi_chu = ? WHERE ma_ho = ?', (gc, ma_ho))
    return True


def thu_muc_anh_du_an(con) -> Path:
    """<thư mục file dự án>/Anh_kiem_dem (dự án chưa lưu thành file: thư mục máy)."""
    try:
        f = con.execute('PRAGMA database_list').fetchone()[2]
    except Exception:                                    # noqa: BLE001
        f = ''
    if f:
        return Path(f).parent / THU_MUC_ANH
    from .dia_phuong import thu_muc_may
    return Path(thu_muc_may()) / THU_MUC_ANH


def _luu_anh(con, ma_ho: int, ds: list, thu_muc: Path, luc: str) -> tuple:
    """Ảnh gửi kèm phiếu ("data:image/jpeg;base64,…") -> file trong thu_muc/<mã hộ>/ + dòng anh_hien_trang (khop_theo 'kiem_dem').
    Ảnh trùng nội dung với file đã có cùng tên: dùng lại (nhập lại phiếu không nhân đôi). Trả (số ảnh mới, [lỗi])."""
    import base64
    import binascii
    from .an_toan import LOAI_ANH, LoiAnToan, kiem_tra_magic_bytes
    duoi = {'jpeg': '.jpg', 'png': '.png', 'webp': '.webp', 'gif': '.gif', 'bmp': '.bmp', 'tiff': '.tif', 'heic': '.heic'}
    moi, loi = 0, []
    tm = thu_muc / str(ma_ho)
    for k, a in enumerate(ds, 1):
        ten = str(a.get('ten') or f'anh_{k}')[:120]
        chu = a['du_lieu']
        m = re.match(r'data:[\w/+.-]*;base64,', chu[:64])
        try:
            if m is None or len(chu) > ANH_TOI_DA * 4 // 3 + 200:
                raise ValueError('không phải ảnh nhúng hoặc quá lớn')
            du = base64.b64decode(chu[m.end():], validate=True)
            loai = kiem_tra_magic_bytes(du, LOAI_ANH, ten)
        except (ValueError, binascii.Error) as e:
            loi.append(f'ảnh "{ten}": {e}')
            continue
        except LoiAnToan as e:
            loi.append(str(e))
            continue
        goc = re.sub(r'[^0-9a-z_-]+', '_', bo_dau(Path(ten).stem).lower()).strip('_') or f'anh_{k}'
        tm.mkdir(parents=True, exist_ok=True)
        f, i = tm / f'{goc}{duoi[loai]}', 1
        while f.exists() and f.read_bytes() != du:
            i += 1
            f = tm / f'{goc}_{i}{duoi[loai]}'
        if not f.exists():
            tam = f.with_name(f.name + '.tmp')
            tam.write_bytes(du)
            tam.replace(f)
        dam_bao_bang_anh(con)
        with csdl.giao_dich(con):
            moi += con.execute(f'INSERT OR IGNORE INTO {BANG_ANH} (ma_ho, duong_dan, ten_file, khop_theo, luc) VALUES (?, ?, ?, ?, ?)',
                               (ma_ho, str(f.resolve()), f.name, 'kiem_dem', luc)).rowcount
    return moi, loi


def _so(x) -> str:
    """Số hiệu tờ / thửa / lô so khớp: chữ thường, bỏ dấu cách / dấu ngăn, bỏ số 0 đầu mỗi nhóm số ("Tờ 05" = "5", "TK126-K6" =
    "tk126/k6")."""
    s = re.sub(r'[^0-9a-z]+', '', bo_dau(str(x or '')).lower())
    return re.sub(r'(?<![0-9])0+(?=[0-9])', '', s)


def khoa_lo_rung(tieu_khu, khoanh) -> str:
    """Số "tờ" của lô rừng ghi trong bảng thửa: 'TK126/K6' (lô = số thửa) - cách ghi chung khi tạo hộ từ phiếu kiểm đếm."""
    return f'TK{str(tieu_khu).strip()}/K{str(khoanh).strip()}'


def _khoa_ten_ho(ten: str) -> str:
    t = re.split(r'\s+(?:là|và|cùng)\s+', str(ten or ''), maxsplit=1)[0]
    t = re.sub(r'^(?:ông|bà|anh|chị|cô|chú|hộ|hộ\s+ông|hộ\s+bà)\s+', '', t.strip(), flags=re.I)
    return ' '.join(re.sub(r'[^a-z0-9 ]+', ' ', bo_dau(t).lower()).split())


class ChiMucHo:
    """Chỉ mục hộ của dự án dựng MỘT lần cho cả file phiếu (CCCD, tờ / thửa, họ tên, mã hộ)."""

    def __init__(self, con):
        from .nhap_excel import chuan_cccd
        self.cccd, self.thua, self.ten, self.ma = {}, {}, {}, set()
        for r in con.execute('SELECT ma_ho, ho_ten, so_cccd FROM ho'):
            self.ma.add(r['ma_ho'])
            so = chuan_cccd(re.sub(r'\D', '', r['so_cccd'] or ''))
            if len(so) >= 9:
                self.cccd.setdefault(so, set()).add(r['ma_ho'])
            k = _khoa_ten_ho(r['ho_ten'])
            if k:
                self.ten.setdefault(k, set()).add(r['ma_ho'])
        for r in con.execute('SELECT ma_ho, so_to, so_thua FROM thua'):
            self.thua.setdefault((_so(r['so_to']), _so(r['so_thua'])), set()).add(r['ma_ho'])


def _tang_cccd(cm, tt) -> set:
    from .nhap_excel import chuan_cccd
    kq = set()
    for k in ('so_cccd', 'cccd_nguoi_su_dung', 'cccd'):
        so = chuan_cccd(re.sub(r'\D', '', str(tt.get(k) or '')))
        if len(so) >= 9:
            kq |= cm.cccd.get(so, set())
    return kq


def _tang_thua(cm, tt, thua) -> set:
    ds = list(thua) or [tt]
    kq = set()
    for t in ds:
        lo, to, so = t.get('lo') or t.get('lo_kk'), t.get('so_to'), t.get('so_thua')
        khoa = []
        if to not in (None, '') and so not in (None, ''):
            khoa.append((_so(to), _so(so)))
        if lo not in (None, '') and (t.get('tieu_khu') or t.get('khoanh')):
            tk, kh = t.get('tieu_khu') or '', t.get('khoanh') or ''
            for to2 in (khoa_lo_rung(tk, kh), f'{tk}/{kh}', kh, tk):
                if _so(to2):
                    khoa.append((_so(to2), _so(lo)))
        for k in khoa:
            kq |= cm.thua.get(k, set())
    return kq


def _tang_ten(cm, tt, ten_file) -> set:
    from difflib import SequenceMatcher
    ten = [_khoa_ten_ho(tt.get(k)) for k in ('ho_ten', 'nguoi_su_dung', 'nguoi_nhan_khoan')]
    if ten_file:
        ten.append(_khoa_ten_ho(re.sub(r'[_\-.]+', ' ', Path(str(ten_file)).stem)))
    ten = [x for x in ten if len(x.split()) >= 2]
    kq = set()
    for t in ten:
        kq |= cm.ten.get(t, set())
    if kq:
        return kq
    tot, diem = set(), NGUONG_TEN
    for t in ten:
        for k, ma in cm.ten.items():
            r = SequenceMatcher(None, t, k).ratio()
            if r > diem + 1e-9:
                tot, diem = set(ma), r
            elif abs(r - diem) <= 1e-9 and r >= NGUONG_TEN:
                tot |= ma
    return tot


def tim_ho_khop_json(con, du_lieu_ho: dict, ten_file: str = '', chi_muc=None) -> tuple:
    """Hộ trong dự án ứng với một hộ của phiếu kiểm đếm -> (mã hộ | None, tầng khớp, các mã ứng viên). 4 tầng ưu tiên:
    (1) số CCCD (chủ hộ / người sử dụng) - (2) tờ / thửa hoặc tiểu khu / khoảnh / lô - (3) họ tên không dấu (chủ hộ, người sử dụng, tên
    file "Nguyen_Van_A.json"; giống >= NGUONG_TEN) - (4) mã hộ của phiếu. Tầng ra nhiều hộ thì thu hẹp bằng các tầng sau; tầng
    không ra hộ nào thì xét tầng sau. Không ra đúng một hộ -> (None, '', ứng viên)."""
    cm = chi_muc or ChiMucHo(con)
    tt = du_lieu_ho.get('thong_tin') if isinstance(du_lieu_ho.get('thong_tin'), dict) else du_lieu_ho
    thua = du_lieu_ho.get('thua') or du_lieu_ho.get('dat_dai') or []
    ma = du_lieu_ho.get('ma_ho')
    tang = [('cccd', lambda: _tang_cccd(cm, tt)), ('thua', lambda: _tang_thua(cm, tt, thua)),
            ('ho_ten', lambda: _tang_ten(cm, tt, ten_file)),
            ('ma_ho', lambda: {int(ma)} & cm.ma if str(ma or '').strip().isdigit() else set())]
    ung, ten_tang = None, ''
    for ten, ham in tang:
        s = ham()
        if not s:
            continue
        if ung is None:
            ung, ten_tang = set(s), ten
        elif ung & s:
            ung, ten_tang = ung & s, f'{ten_tang}+{ten}'
        if len(ung) == 1:
            return next(iter(ung)), ten_tang, sorted(ung)
    return None, '', sorted(ung or ())


def _tao_ho(con, h: dict) -> int:
    """Hộ ghi mới ở thực địa (không khớp hộ nào) -> thêm vào dự án: họ tên, CCCD, địa chỉ, điện thoại, người sử dụng (ghi chú), thửa /
    lô rừng (lô: tờ = "TK<tiểu khu>/K<khoảnh>", thửa = lô, DT ha -> m²)."""
    from decimal import Decimal, InvalidOperation
    from .ho_so import luu_ho
    tt = h['thong_tin']
    ten = ' '.join(str(tt.get('ho_ten') or tt.get('nguoi_nhan_khoan') or tt.get('nguoi_su_dung') or '').split())
    if not ten:
        raise LoiNhap('Hộ ghi mới ở thực địa chưa có họ tên.')
    gc = [str(tt.get('ghi_chu') or '').strip()]
    if tt.get('nguoi_su_dung') and str(tt['nguoi_su_dung']).strip() != ten:
        gc.append(f'Người sử dụng: {str(tt["nguoi_su_dung"]).strip()}')
    for k, nhan in (('nam_sinh', 'Năm sinh'), ('nam_tao_lap', 'Năm tạo lập tài sản')):
        if str(tt.get(k) or '').strip():
            gc.append(f'{nhan}: {str(tt[k]).strip()}')
    if h.get('gps'):
        gc.append(chu_gps(h['gps']))
    thong_tin = dict(ho_ten=ten, so_cccd=re.sub(r'\D', '', str(tt.get('so_cccd') or '')), dia_chi=str(tt.get('dia_chi') or ''),
                     dien_thoai=str(tt.get('sdt') or tt.get('dien_thoai') or ''), ghi_chu='; '.join(x for x in gc if x))
    ds = []
    for t in h['thua']:
        lo = t.get('lo') or t.get('lo_kk')
        if lo and (t.get('tieu_khu') or t.get('khoanh')):
            to, so = khoa_lo_rung(t.get('tieu_khu') or '', t.get('khoanh') or ''), str(lo)
        else:
            to, so = str(t.get('so_to') or ''), str(t.get('so_thua') or '')
        dt = str(t.get('dt_thu_hoi') or '')
        if not dt and t.get('dt_ha') not in (None, ''):
            try:
                dt = str(Decimal(str(t['dt_ha']).replace(',', '.')) * 10000).replace('.', ',')
            except InvalidOperation:
                dt = ''
        if to or so:
            ds.append(dict(ma_thua=None, so_to=to, so_thua=so, loai_dat=str(t.get('loai_dat') or ''), dt_thu_hoi=dt or '0'))
    return luu_ho(con, None, thong_tin, ds)


def _mo_rong_dong(ds: list) -> list:
    """Dòng ghi gộp nhiều cỡ (tên "Ống nhựa: ϕ114: 3300m; ϕ90: 3400m", ô số lượng trống) -> từng dòng (tach_dong_qd42)."""
    from .hieu_tai_san import tach_dong_qd42
    ra = []
    for d in ds:
        ten = str(d.get('ten') or '')
        con = tach_dong_qd42(ten) if not str(d.get('so_luong') or '').strip() and not d.get('ma_dm') else [ten]
        if len(con) > 1:
            ra.extend(dict(d, ten=x) for x in con)
        else:
            ra.append(d)
    return ra


def nhap_ket_qua_kiem_dem(con, file, dm=None, tao_ho_moi: bool = False, chi=None) -> dict:
    """Thêm các dòng kiểm đếm vào phương án từng hộ (BoSoan, lưu mỗi hộ một lần). Hộ của phiếu khớp hộ dự án bằng tim_ho_khop_json;
    không khớp: tao_ho_moi -> thêm hộ mới, không thì báo lại ở 'chua_khop' (màn hình hỏi rồi gọi lại với chi = các khóa đó).
    Trả {'so_ho', 'so_dong', 'loi': [chữ], 'khop': [(khóa, mã hộ, tầng)], 'chua_khop': [{khoa, ten, so_dong}], 'tao_moi'}."""
    from .lap_pa import BoSoan, DanhMuc
    from .nhap_tai_san import DichPhuongAn, them_dong_tho, them_mot
    from .cay_trong import BangCayDK
    from .hieu_tai_san import bo_sung, la_dong_tu_nhien, loai_cay_dk, tach_dong
    from .phan_loai_tai_san import LOAI, BoPhanLoai
    phieu = doc_phieu(file)
    dm = dm or DanhMuc(con)
    pl = BoPhanLoai(dm)
    cm = ChiMucHo(con)
    so_ho = so_dong = tao_moi = so_anh = so_gps = 0
    loi, khop, chua = [], [], []
    tm_anh = thu_muc_anh_du_an(con)
    luc = datetime.now().isoformat(timespec='seconds')
    for h in phieu['ho']:
        if chi is not None and h['khoa'] not in chi:
            continue
        ds = _mo_rong_dong(h['dong'])
        if not ds and not h['anh'] and not h['gps'] and not (tao_ho_moi and h['thong_tin']):
            continue
        # tên file ("Nguyen_Van_A.json") chỉ là tên hộ khi file có MỘT hộ (file cả dự án: tên file không nói hộ nào)
        ma_ho, tang, ung = tim_ho_khop_json(con, h, Path(file).name if len(phieu['ho']) == 1 else '', cm)
        ten_ho = str(h['thong_tin'].get('ho_ten') or h['thong_tin'].get('nguoi_su_dung') or f'Mã hộ {h["khoa"]}')
        if ma_ho is None:
            if tao_ho_moi:
                try:
                    ma_ho, tang = _tao_ho(con, h), 'tao_moi'
                except LoiNhap as e:
                    loi.append(f'{ten_ho}: {e}')
                    continue
                tao_moi += 1
                cm = ChiMucHo(con)
            else:
                chua.append(dict(khoa=h['khoa'], ten=ten_ho, so_dong=len(ds), ung_vien=ung))
                loi.append(f'{ten_ho}: không khớp hộ nào trong dự án' + (f' ({len(ung)} hộ giống nhau - chọn tay)' if ung else '')
                           + f' ({len(ds)} dòng' + (f', {len(h["anh"])} ảnh' if h['anh'] else '') + ' chưa nhập).')
                continue
        khop.append((h['khoa'], ma_ho, tang))
        try:
            if h['anh']:
                a, la = _luu_anh(con, ma_ho, h['anh'], tm_anh, luc)
                so_anh += a
                loi.extend(f'{ten_ho} - {x}' for x in la)
            if h['gps'] and tang != 'tao_moi' and _ghi_gps(con, ma_ho, h['gps']):
                so_gps += 1
        except (LoiNhap, OSError) as e:
            loi.append(f'{ten_ho}: ảnh / tọa độ chưa ghi được - {e}')
        if not ds:
            continue
        bo = BoSoan(con, ma_ho, dm)
        dich = DichPhuongAn(bo)
        n = 0
        for k, d in enumerate(ds, 1):
            ten, dvt = ' '.join(str(d.get('ten') or '').split()), str(d.get('dvt') or '').strip()
            sl, tl, gc = str(d.get('so_luong') or '').strip(), str(d.get('ty_le') or '').strip(), str(d.get('ghi_chu') or '').strip()
            do, kieu = str(d.get('so_do') or '').strip(), str(d.get('kieu') or 'dk')
            tuoi = ''
            try:
                muc = int(d.get('muc') if d.get('muc') not in (None, '') else 2)
            except (TypeError, ValueError):
                muc = 2
            if muc not in (0, 2, 3, 7):                 # 0 = dòng ghi lại biên bản (thẻ Ảnh biên bản / ghi nhanh): tự phân loại
                muc = 2
            try:
                tl = tl if tl and tl != '100' else ''
                m_dm = dm.lay(str(d.get('ma_dm') or '').strip()) if d.get('ma_dm') else None
                if m_dm is not None and m_dm.nhom in (2, 3, 7):     # mã đơn giá đã chọn trên điện thoại: áp thẳng (1.0.32)
                    if m_dm.nhom == 3 and do:
                        them_mot(dich, 3, m_dm, ten, sl, tl, 'cv' if kieu == 'cv' else 'dk', gc, do)
                    else:
                        them_dong_tho(dich, m_dm.nhom, m_dm, ten, dvt, sl, tl, gc)
                    n += 1
                    continue
                # ô tên ghi cả câu ("Xoài: 16 cây, 17 năm tuổi", "Tràm 35c/15cm"): tách như hộp Dán danh sách - ô trống lấy theo câu
                t = tach_dong(ten, phieu['nam']) if la_dong_tu_nhien(ten) else None
                if t is not None:
                    ten, dvt, sl, tl = t['ten'], dvt or t['dvt'], sl or t['so_luong'], tl or t['ty_le']
                    do, tuoi = do or t['so_do'], t['tuoi']
                    kieu = t['kieu'] or kieu
                    gc = '; '.join(x for x in (gc, t['ghi_chu']) if x)
                if muc == 0:                            # cùng bộ hiểu với hộp Dán danh sách quyết định mục
                    kq = bo_sung(pl, dm, dict(ten=ten, dvt=dvt, tuoi=tuoi, so_luong=sl, so_do=do, kieu=kieu if do else ''),
                                 pl.phan_loai(ten, dvt))
                    if kq.muc not in (2, 3, 7):
                        raise LoiNhap('là chính sách hỗ trợ: lập trong phần mềm (thẻ hỗ trợ của phương án), không nhập từ phiếu')
                    muc = kq.muc
                    if muc != 3 or not (kq.so_do or do):
                        them_dong_tho(dich, muc, kq.khop if kq.khop is not None and LOAI[kq.loai][0] == muc else None, ten, dvt,
                                      sl, tl, '; '.join(x for x in (gc, kq.ghi_them) if x))
                        n += 1
                        continue
                    do, kieu = kq.so_do or do, kq.kieu or kieu
                if muc == 3 and do:                     # cây theo số đo: loại cây trong bảng quy cách ("Tràm" -> "Keo lá tràm")
                    loai_cay = loai_cay_dk(BangCayDK(dm.muc.get(3, [])), ten) or ten
                    them_mot(dich, 3, ('nhom', loai_cay), ten, sl, tl, 'cv' if kieu == 'cv' else 'dk', gc, do)
                else:
                    # cùng bộ hiểu với hộp Dán danh sách: năm tuổi -> mục đúng năm, khớp theo từ, ống / giếng theo cỡ, "… tính bằng …"
                    kq = bo_sung(pl, dm, dict(ten=ten, dvt=dvt, tuoi=tuoi, so_luong=sl), pl.phan_loai(ten, dvt))
                    m = kq.khop if kq.khop is not None and LOAI[kq.loai][0] == muc else None
                    them_dong_tho(dich, muc, m, ten, dvt, sl, tl, '; '.join(x for x in (gc, kq.ghi_them) if x))
                n += 1
            except LoiNhap as e:
                loi.append(f'{ten_ho} - dòng {k} "{ten[:40]}": {e}')
        if n:
            bo.luu()
            so_ho += 1
            so_dong += n
    with csdl.giao_dich(con):
        csdl.ghi_nhat_ky(con, 'Nhập kết quả kiểm đếm thực địa', f'{Path(file).name}: {so_ho} hộ, {so_dong} dòng'
                         + (f', thêm {tao_moi} hộ mới' if tao_moi else '') + (f', {so_anh} ảnh' if so_anh else '')
                         + (f', tọa độ {so_gps} hộ' if so_gps else ''))
    return dict(so_ho=so_ho, so_dong=so_dong, loi=loi, khop=khop, chua_khop=chua, tao_moi=tao_moi, so_anh=so_anh, so_gps=so_gps,
                thu_muc_anh=tm_anh)


# ---------------------------------------------------------------- 3. ảnh hiện trạng
def dam_bao_bang_anh(con) -> bool:
    if con.execute("SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?", (BANG_ANH,)).fetchone():
        return True
    with csdl.giao_dich(con):
        con.execute(SQL_BANG_ANH)
    return True


def _khoa_ten(s: str) -> str:
    return re.sub(r'[^a-z0-9]+', '_', bo_dau(s or '').lower()).strip('_')


def gan_anh_hien_trang(con, thu_muc) -> dict:
    """Gắn ảnh trong thư mục (cả thư mục con) vào hộ. Trả {'so_anh', 'da_gan', 'chua_khop': [tên file + lý do]}."""
    from .an_toan import LOAI_ANH, LoiAnToan, kiem_tra_magic_bytes
    tm = Path(thu_muc)
    if not tm.is_dir():
        raise LoiNhap(f'Không có thư mục ảnh: {tm}')
    cccd, ten, stt = {}, {}, {}
    for r in con.execute('SELECT ma_ho, thu_tu, ho_ten, so_cccd FROM ho'):
        so = re.sub(r'\D', '', r['so_cccd'] or '')
        if len(so) >= 9:
            cccd.setdefault(so, set()).add(r['ma_ho'])
        k = _khoa_ten(' '.join(str(r['ho_ten'] or '').split(' là ')[0].split()))
        if k.count('_') >= 1:                           # ít nhất 2 chữ (họ + tên)
            ten.setdefault(k, set()).add(r['ma_ho'])
        stt[str(r['thu_tu'])] = r['ma_ho']
    dam_bao_bang_anh(con)
    luc = datetime.now().isoformat(timespec='seconds')
    so_anh, gan, chua = 0, 0, []
    with csdl.giao_dich(con):
        for f in sorted(tm.rglob('*')):
            if not f.is_file() or f.suffix.lower() not in DUOI_ANH:
                continue
            so_anh += 1
            try:                                        # 1.0.32: đuôi ảnh mà nội dung không phải ảnh (chương trình đổi đuôi…) -> không gắn
                kiem_tra_magic_bytes(f, LOAI_ANH)
            except LoiAnToan as e:
                chua.append(f'{f.name}: {e}')
                continue
            goc = _khoa_ten(f.stem)
            ma, theo = set(), ''
            for so in re.findall(r'\d{9,12}', f.stem):
                if so in cccd:
                    ma, theo = cccd[so], 'cccd'
                    break
            if not ma:
                for k, ds in ten.items():
                    if re.search(r'(^|_)' + re.escape(k) + r'(_|$)', goc):
                        if ma and ma != ds:                 # khớp tên của hai hộ khác nhau
                            ma = ma | ds
                        else:
                            ma = ds
                        theo = 'ho_ten'
            if not ma:
                m = re.match(r'^ho_?0*(\d+)(_|$)', goc)
                if m and m.group(1) in stt:
                    ma, theo = {stt[m.group(1)]}, 'stt'
            if len(ma) != 1:
                chua.append(f'{f.name}: ' + ('trùng tên nhiều hộ' if ma else 'không nhận ra hộ (đặt tên ảnh theo CCCD, họ tên hoặc HO<số thứ tự>)'))
                continue
            gan += con.execute(f'INSERT OR IGNORE INTO {BANG_ANH} (ma_ho, duong_dan, ten_file, khop_theo, luc) VALUES (?, ?, ?, ?, ?)',
                               (next(iter(ma)), str(f.resolve()), f.name, theo, luc)).rowcount
        csdl.ghi_nhat_ky(con, 'Gắn ảnh hiện trạng', f'{tm}: {gan} ảnh mới / {so_anh} ảnh')
    return dict(so_anh=so_anh, da_gan=gan, chua_khop=chua)


def anh_cua_ho(con, ma_ho: int) -> list:
    if not con.execute("SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?", (BANG_ANH,)).fetchone():
        return []
    return [dict(r) for r in con.execute(f'SELECT * FROM {BANG_ANH} WHERE ma_ho = ? ORDER BY ten_file', (ma_ho,))]


def so_anh_theo_ho(con) -> dict:
    if not con.execute("SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?", (BANG_ANH,)).fetchone():
        return {}
    return {r[0]: r[1] for r in con.execute(f'SELECT ma_ho, COUNT(*) FROM {BANG_ANH} GROUP BY ma_ho')}

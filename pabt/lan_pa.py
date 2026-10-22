"""Nhiều lần lập phương án chi tiết cho MỘT hộ (1.0.05 - người dùng 19/10/2026): lần đầu + các lần bổ sung, mỗi lần một bộ dòng
ct_dat / ct_khoan riêng (cột lan), số / ngày phương án riêng, một quyết định phê duyệt riêng (qd_ho.lan). Lần đã có quyết định thì
KHÓA (chỉ xem): bổ sung tài sản / chính sách mới thì lập lần bổ sung - dữ liệu và quyết định của các lần trước giữ nguyên. Tổng của
hộ = CỘNG DỒN mọi lần (nghiep_vu.doc_phuong_an mặc định đọc mọi lần).

Không phụ thuộc Qt. CSDL v17 (csdl._tao_pa_lan): file cũ - mọi dòng là lần 1; hộ đã có quyết định thì lần 1 khóa.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from . import csdl
from .tien import KHONG

DANG_LAP, DA_PHE_DUYET, MO_KHOA = 'dang_lap', 'da_phe_duyet', 'mo_khoa'
# loại lần (1.0.15): chính (lần đầu) / bổ sung (thêm tài sản, chính sách mới - CỘNG vào) / điều chỉnh (sửa sai lần đã phê duyệt - THAY
# lần đó). Mỗi loại một mẫu in Word riêng (in_word) và một bảng tổng hợp.
CHINH, BO_SUNG, DIEU_CHINH = 'chinh', 'bo_sung', 'dieu_chinh'
TEN_LOAI = {CHINH: 'Phương án chi tiết', BO_SUNG: 'Phương án bổ sung', DIEU_CHINH: 'Phương án điều chỉnh'}
TEN_TRANG_THAI = {DANG_LAP: 'Đang lập', DA_PHE_DUYET: 'Đã phê duyệt', MO_KHOA: 'Đã phê duyệt - đang điều chỉnh'}


TEN_LAN_GOC = 'Phương án gốc'


def ten_mac_dinh(lan: int, loai: str = '') -> str:
    if lan <= 1:
        return TEN_LAN_GOC
    return f'Phương án điều chỉnh lần {lan - 1}' if loai == DIEU_CHINH else f'Phương án bổ sung lần {lan - 1}'


@dataclass
class LanPA:
    lan: int
    ten: str = ''
    ngay_lap: str = ''
    so_pa: str = ''
    ngay_pa: str = ''
    trang_thai: str = DANG_LAP
    khoa: bool = False
    ghi_chu: str = ''
    qd: list = field(default_factory=list)          # [dict(qd_id, so, ngay)] quyết định phê duyệt lần này
    so_dong: int = 0
    ma_ho: int = 0
    loai: str = BO_SUNG
    thay_the: int = 0                               # lần điều chỉnh: số lần bị thay thế (0: không thay lần nào)
    bi_thay_boi: int = 0                            # lần này đã bị lần điều chỉnh số … thay thế (0: chưa)

    @property
    def la_dieu_chinh(self) -> bool:
        return self.loai == DIEU_CHINH and self.thay_the > 0

    @property
    def nhan(self) -> str:
        """'Lần 2: Phương án bổ sung lần 1 [Đã phê duyệt - QĐ 12/QĐ-UBND]' (không emoji - Win 7 không có phông emoji)."""
        qd = ', '.join(x['so'] or f'QĐ {x["qd_id"]}' for x in self.qd)
        tt = TEN_TRANG_THAI.get(self.trang_thai, self.trang_thai)
        return f'Lần {self.lan}: {self.ten or ten_mac_dinh(self.lan, self.loai)} [{tt}' + (f' - QĐ {qd}' if qd else '') + \
            (', khóa' if self.khoa and not self.qd else '') + \
            (f', bị thay bởi lần {self.bi_thay_boi}' if self.bi_thay_boi else '') + ']'

    @property
    def nhan_trang_thai(self) -> str:
        """Nhãn trạng thái của dải lần: 'ĐÃ PHÊ DUYỆT (QĐ số … ngày …) - CHỈ XEM' / 'ĐANG LẬP DỰ THẢO' / 'ĐANG ĐIỀU CHỈNH'."""
        if self.trang_thai == MO_KHOA:
            return 'ĐÃ PHÊ DUYỆT - ĐANG MỞ KHÓA ĐIỀU CHỈNH'
        if self.qd:
            qd = '; '.join(f'QĐ số {x["so"] or x["qd_id"]}' + (f' ngày {x["ngay"]}' if x.get('ngay') else '') for x in self.qd)
            return f'ĐÃ PHÊ DUYỆT ({qd}) - CHỈ XEM'
        return 'ĐÃ KHÓA - CHỈ XEM' if self.khoa else 'ĐANG LẬP DỰ THẢO'


def co_bang(con) -> bool:
    return bool(con.execute("SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'pa_lan'").fetchone())


def _qd_cua_ho(con, ma_ho: int) -> dict:
    """{lần: [quyết định]} - quyết định trước v17 (lan 0) tính là phê duyệt lần 1."""
    kq = {}
    try:
        ds = con.execute('''SELECT q.qd_id, q.lan, d.so, d.ngay FROM qd_ho q JOIN quyet_dinh d ON d.id = q.qd_id
                            WHERE q.ma_ho = ? ORDER BY q.id''', (ma_ho,)).fetchall()
    except Exception:                                   # file chỉ xem bản cũ (chưa có cột lan)
        ds = [dict(qd_id=r[0], lan=0, so=r[1], ngay=r[2]) for r in con.execute(
            'SELECT q.qd_id, d.so, d.ngay FROM qd_ho q JOIN quyet_dinh d ON d.id = q.qd_id WHERE q.ma_ho = ?', (ma_ho,))]
    for r in ds:
        kq.setdefault(max(1, int(r['lan'] or 0)), []).append(dict(qd_id=r['qd_id'], so=r['so'], ngay=r['ngay']))
    return kq


def ds_lan(con, ma_ho: int) -> list:
    """[LanPA] của hộ theo thứ tự lần - luôn có lần 1 (kể cả hộ chưa lập gì); lần có quyết định đánh dấu đã phê duyệt + khóa."""
    qd = _qd_cua_ho(con, ma_ho)
    dong = {}
    from .nghiep_vu import co_cot_lan
    if co_cot_lan(con):
        for bang in ('ct_dat', 'ct_khoan'):
            for r in con.execute(f'SELECT lan, COUNT(*) FROM {bang} WHERE ma_ho = ? GROUP BY lan', (ma_ho,)):
                dong[r[0]] = dong.get(r[0], 0) + r[1]
    else:
        n = sum(con.execute(f'SELECT COUNT(*) FROM {b} WHERE ma_ho = ?', (ma_ho,)).fetchone()[0] for b in ('ct_dat', 'ct_khoan'))
        dong = {1: n} if n else {}
    kq = {}
    if co_bang(con):
        for r in con.execute('SELECT * FROM pa_lan WHERE ma_ho = ? ORDER BY lan', (ma_ho,)):
            cot = r.keys()
            kq[r['lan']] = LanPA(r['lan'], r['ten'], r['ngay_lap'], r['so_pa'], r['ngay_pa'], r['trang_thai'], bool(r['khoa']),
                                 r['ghi_chu'], loai=(r['loai'] if 'loai' in cot else BO_SUNG) or BO_SUNG,
                                 thay_the=int(r['thay_the'] or 0) if 'thay_the' in cot else 0)
    for lan in set(dong) | set(qd) | {1}:
        kq.setdefault(lan, LanPA(lan, ten_mac_dinh(lan)))
    for lan, x in kq.items():
        x.ma_ho = ma_ho
        x.qd = qd.get(lan, [])
        x.so_dong = dong.get(lan, 0)
        if lan == 1:
            x.loai = CHINH
        if x.qd and x.trang_thai != MO_KHOA:
            x.trang_thai, x.khoa = DA_PHE_DUYET, True
        if not x.ten:
            x.ten = ten_mac_dinh(lan, x.loai)
    for lan, x in kq.items():
        if x.thay_the and x.thay_the in kq:
            kq[x.thay_the].bi_thay_boi = lan
    return [kq[k] for k in sorted(kq)]


def lan_cua(con, ma_ho: int, lan: int) -> LanPA:
    return next((x for x in ds_lan(con, ma_ho) if x.lan == lan), LanPA(lan, ten_mac_dinh(lan)))


def lan_hien_tai(con, ma_ho: int, lan_chi_dinh: int | None = None) -> LanPA:
    """Lần đang làm việc: lan_chi_dinh nếu có; không thì lần chưa khóa muộn nhất, mọi lần đã khóa: lần cuối."""
    lan = int(lan_chi_dinh) if lan_chi_dinh else lan_mac_dinh(con, ma_ho)
    return lan_cua(con, ma_ho, lan)


def lan_mac_dinh(con, ma_ho: int) -> int:
    """Lần mở mặc định khi soạn: lần chưa khóa muộn nhất; mọi lần đã khóa: lần muộn nhất (chỉ xem)."""
    ds = ds_lan(con, ma_ho)
    mo = [x.lan for x in ds if not x.khoa]
    return mo[-1] if mo else ds[-1].lan


def lan_moi_nhat(con, ma_ho: int) -> int:
    """Lần muộn nhất CÓ dòng phương án (in mặc định); hộ chưa có dòng nào: lần 1."""
    ds = [x.lan for x in ds_lan(con, ma_ho) if x.so_dong]
    return ds[-1] if ds else 1


def lan_chua_duyet(con, ma_ho: int) -> int | None:
    """Lần sớm nhất CHƯA có quyết định phê duyệt mà có dòng phương án (hoặc lần 1 khi hộ chưa có quyết định nào); None: mọi lần đã
    duyệt."""
    ds = ds_lan(con, ma_ho)
    if not any(x.qd for x in ds):
        return 1
    return next((x.lan for x in ds if not x.qd and x.so_dong), None)


def _dam_bao_dong(con, ma_ho: int, lan: int) -> None:
    """Dòng pa_lan của (hộ, lần) - tạo nếu chưa có. Trong giao dịch của nơi gọi."""
    if not co_bang(con):
        return
    if not csdl.co_cot_pa_lan(con):
        csdl.dam_bao_cot_pa_lan(con)
    con.execute('INSERT OR IGNORE INTO pa_lan (ma_ho, lan, ten, ngay_lap) VALUES (?, ?, ?, ?)',
                (ma_ho, lan, ten_mac_dinh(lan), datetime.now().strftime('%d/%m/%Y')))


def tao_lan_moi(con, ma_ho: int, ten: str | None = '', ghi_chu: str = '') -> int:
    """Lập phương án BỔ SUNG: lần mới = lần lớn nhất + 1 (rỗng - các lần trước giữ nguyên). Trả số lần."""
    ten = ten or ''
    lan = max(x.lan for x in ds_lan(con, ma_ho)) + 1
    with csdl.giao_dich(con):
        _dam_bao_dong(con, ma_ho, lan)
        con.execute('UPDATE pa_lan SET ten = ?, ghi_chu = ? WHERE ma_ho = ? AND lan = ?',
                    (ten.strip() or ten_mac_dinh(lan), ghi_chu.strip(), ma_ho, lan))
        csdl.ghi_nhat_ky(con, 'Tạo phương án bổ sung', f'Hộ {ma_ho}: lần {lan} - {ten.strip() or ten_mac_dinh(lan)}')
    return lan


def tao_lan_dieu_chinh(con, ma_ho: int, lan_goc: int | None = None, ten: str | None = '', ghi_chu: str = '') -> int:
    """Lập phương án ĐIỀU CHỈNH (sửa sai phương án đã phê duyệt): lần mới = lần lớn nhất + 1, SAO CHÉP đủ dòng của lần bị sửa
    (lan_goc; mặc định lần đang áp dụng đã phê duyệt muộn nhất) để người dùng sửa cho đúng. Lần bị sửa giữ nguyên dòng + quyết định
    (in "phương án đã phê duyệt") nhưng từ nay KHÔNG cộng vào tổng của hộ - lần điều chỉnh thay thế. Xóa lần điều chỉnh (chưa có quyết
    định) thì lần cũ tính lại. Trả số lần mới. LoiNhap: chưa có lần nào đã phê duyệt / lần đã bị thay."""
    from .lap_pa import LoiNhap
    ds = ds_lan(con, ma_ho)
    ung = [x for x in ds if x.qd and not x.bi_thay_boi and x.so_dong]
    if lan_goc is None:
        if not ung:
            raise LoiNhap('Hộ chưa có phương án nào đã được phê duyệt để điều chỉnh. Phương án chưa phê duyệt: sửa trực tiếp.')
        lan_goc = ung[-1].lan
    goc = next((x for x in ds if x.lan == int(lan_goc)), None)
    if goc is None or not goc.so_dong:
        raise LoiNhap(f'Hộ không có phương án lần {lan_goc}.')
    if goc.bi_thay_boi:
        raise LoiNhap(f'Lần {goc.lan} đã được điều chỉnh bằng lần {goc.bi_thay_boi} - điều chỉnh tiếp lần {goc.bi_thay_boi}.')
    if not goc.qd:
        raise LoiNhap(f'Lần {goc.lan} chưa có quyết định phê duyệt - sửa trực tiếp, không cần phương án điều chỉnh.')
    lan = max(x.lan for x in ds) + 1
    ten = (ten or '').strip() or ten_mac_dinh(lan, DIEU_CHINH)
    with csdl.giao_dich(con):
        _dam_bao_dong(con, ma_ho, lan)
        con.execute("UPDATE pa_lan SET ten = ?, ghi_chu = ?, loai = ?, thay_the = ? WHERE ma_ho = ? AND lan = ?",
                    (ten, ghi_chu.strip(), DIEU_CHINH, goc.lan, ma_ho, lan))
        for bang in ('ct_dat', 'ct_khoan'):
            cot = [r[1] for r in con.execute(f'PRAGMA table_info({bang})') if r[1] not in ('id', 'lan')]
            ds_cot = ', '.join(cot)
            con.execute(f'INSERT INTO {bang} ({ds_cot}, lan) SELECT {ds_cot}, ? FROM {bang} WHERE ma_ho = ? AND lan = ? '
                        'ORDER BY id', (lan, ma_ho, goc.lan))
        csdl.ghi_nhat_ky(con, 'Tạo phương án điều chỉnh', f'Hộ {ma_ho}: lần {lan} thay lần {goc.lan} - {ten}')
    return lan


def loai_lan(con, ma_ho: int, lan: int | None) -> str:
    """Loại lần phương án để chọn MẪU IN: chinh / bo_sung / dieu_chinh. lan None (cộng dồn) -> chinh."""
    if not lan or int(lan) <= 1:
        return CHINH
    x = lan_cua(con, ma_ho, int(lan))
    return DIEU_CHINH if x.la_dieu_chinh else BO_SUNG


def sua_lan(con, ma_ho: int, lan: int, ten: str | None = None, so_pa: str | None = None, ngay_pa: str | None = None,
            ghi_chu: str | None = None) -> None:
    """Sửa tên / số, ngày phương án / ghi chú của một lần (None = giữ nguyên)."""
    gt = dict(ten=ten, so_pa=so_pa, ngay_pa=ngay_pa, ghi_chu=ghi_chu)
    cot = {k: str(v).strip() for k, v in gt.items() if v is not None}
    if not cot:
        return
    with csdl.giao_dich(con):
        _dam_bao_dong(con, ma_ho, lan)
        con.execute(f'UPDATE pa_lan SET {", ".join(k + " = ?" for k in cot)} WHERE ma_ho = ? AND lan = ?',
                    (*cot.values(), ma_ho, lan))
        if lan == 1 and ('so_pa' in cot or 'ngay_pa' in cot):       # lần đầu: giữ ho.so_pa / ngay_pa (đợt trình, bản in) cùng số
            con.execute(f'UPDATE ho SET {", ".join(k + " = ?" for k in cot if k in ("so_pa", "ngay_pa"))} WHERE ma_ho = ?',
                        (*[v for k, v in cot.items() if k in ('so_pa', 'ngay_pa')], ma_ho))
        csdl.ghi_nhat_ky(con, 'Sửa lần phương án', f'Hộ {ma_ho} lần {lan}: ' + ', '.join(f'{k}={v}' for k, v in cot.items()))


def dang_khoa(con, ma_ho: int, lan: int) -> bool:
    """Lần đang khóa: có quyết định phê duyệt (trừ khi người dùng đã mở khóa sửa - trạng thái MO_KHOA) hoặc khóa tay."""
    return lan_cua(con, ma_ho, lan).khoa


def mo_khoa_lan(con, ma_ho: int, lan: int, ly_do: str = '') -> None:
    """Mở khóa TẠM để điều chỉnh lần đã phê duyệt: trạng thái MO_KHOA (quyết định cũ giữ nguyên số liệu đã ghi), nhật ký ghi lý do -
    CẢNH BÁO: sửa xong cần ban hành quyết định điều chỉnh. Khóa lại: khoa_lai."""
    with csdl.giao_dich(con):
        _dam_bao_dong(con, ma_ho, lan)
        con.execute('UPDATE pa_lan SET khoa = 0, trang_thai = ? WHERE ma_ho = ? AND lan = ?', (MO_KHOA, ma_ho, lan))
        csdl.ghi_nhat_ky(con, 'CẢNH BÁO - Mở khóa sửa lần phương án đã phê duyệt',
                         f'Hộ {ma_ho} lần {lan}' + (f'. Lý do: {ly_do.strip()}' if str(ly_do or '').strip() else ''))


def mo_khoa_sua(con, ma_ho: int, lan: int) -> None:
    """Như mo_khoa_lan, không ghi lý do (giữ tên cũ 1.0.05)."""
    mo_khoa_lan(con, ma_ho, lan)


def khoa_lai(con, ma_ho: int, lan: int) -> None:
    """Khóa lại lần đã mở khóa điều chỉnh (có quyết định -> đã phê duyệt; không có -> đang lập nhưng khóa)."""
    co_qd = bool(_qd_cua_ho(con, ma_ho).get(lan))
    with csdl.giao_dich(con):
        _dam_bao_dong(con, ma_ho, lan)
        con.execute('UPDATE pa_lan SET khoa = 1, trang_thai = ? WHERE ma_ho = ? AND lan = ?',
                    (DA_PHE_DUYET if co_qd else DANG_LAP, ma_ho, lan))
        csdl.ghi_nhat_ky(con, 'Khóa lại lần phương án', f'Hộ {ma_ho} lần {lan}')


def xoa_lan(con, ma_ho: int, lan: int) -> int:
    """Xóa lần bổ sung CHƯA phê duyệt (dòng phương án của lần đó). Lần 1 / lần đã có quyết định: LoiNhap. Trả số dòng xóa."""
    from .lap_pa import LoiNhap
    if lan <= 1:
        raise LoiNhap('Không xóa được phương án lần đầu (xóa từng dòng trong phương án nếu cần).')
    if _qd_cua_ho(con, ma_ho).get(lan):
        raise LoiNhap(f'Lần {lan} đã có quyết định phê duyệt - bỏ hộ khỏi quyết định trước khi xóa.')
    with csdl.giao_dich(con):
        n = con.execute('DELETE FROM ct_dat WHERE ma_ho = ? AND lan = ?', (ma_ho, lan)).rowcount
        n += con.execute('DELETE FROM ct_khoan WHERE ma_ho = ? AND lan = ?', (ma_ho, lan)).rowcount
        if co_bang(con):
            con.execute('DELETE FROM pa_lan WHERE ma_ho = ? AND lan = ?', (ma_ho, lan))
        csdl.ghi_nhat_ky(con, 'Xóa lần phương án bổ sung', f'Hộ {ma_ho} lần {lan}: {n} dòng')
    return n


def gan_qd(con, qd_id: int, ma_ho: int, lan: int) -> None:
    """Quyết định qd_id phê duyệt lần lan của hộ: ghi qd_ho.lan, lần chuyển 'đã phê duyệt' + khóa. Trong giao dịch của nơi gọi."""
    con.execute('UPDATE qd_ho SET lan = ? WHERE qd_id = ? AND ma_ho = ?', (lan, qd_id, ma_ho))
    _dam_bao_dong(con, ma_ho, lan)
    if co_bang(con):
        con.execute("UPDATE pa_lan SET trang_thai = ?, khoa = 1 WHERE ma_ho = ? AND lan = ?", (DA_PHE_DUYET, ma_ho, lan))


def bo_qd(con, ma_ho: int, lan: int) -> None:
    """Hộ bị bỏ khỏi quyết định của lần lan: không còn quyết định nào thì lần về 'đang lập', mở khóa."""
    if lan and not _qd_cua_ho(con, ma_ho).get(lan) and co_bang(con):
        con.execute("UPDATE pa_lan SET trang_thai = ?, khoa = 0 WHERE ma_ho = ? AND lan = ?", (DANG_LAP, ma_ho, lan))


# ---------------------------------------------------------------- tổng hợp các lần của hộ
@dataclass
class TongLan:
    lan: LanPA
    ket_qua: object                    # nghiep_vu.KetQuaHo riêng lần (thưởng: phần tăng thêm)

    @property
    def tong(self):
        return self.ket_qua.tong


def tong_hop_ho(con, ma_ho: int, bc=None) -> dict:
    """Các lần của hộ + kết quả riêng từng lần + cộng dồn: dict(lan=[TongLan], tong, so_lan, so_lan_co_dong, so_da_duyet,
    tong_da_duyet (theo phương án), chua_duyet (các lần chưa có quyết định))."""
    from .nghiep_vu import BoiCanh, PhuongAn, doc_phuong_an, gop_phuong_an, tinh_pa_lan
    bc = bc or BoiCanh.tu(con)
    ds = ds_lan(con, ma_ho)
    truoc = None
    kq = []
    for x in ds:
        pa = doc_phuong_an(con, ma_ho, lan=x.lan)
        if truoc is None:
            truoc = PhuongAn(ho=pa.ho)
        kq.append(TongLan(x, tinh_pa_lan(pa, truoc, bc)))
        truoc = gop_phuong_an(truoc, pa)
    tong = sum((t.tong for t in kq), KHONG)
    da = [t for t in kq if t.lan.qd]
    return dict(lan=kq, tong=tong, so_lan=len(ds), so_lan_co_dong=sum(1 for t in kq if t.lan.so_dong),
                so_da_duyet=len(da), tong_da_duyet=sum((t.tong for t in da), KHONG),
                chua_duyet=[t.lan.lan for t in kq if not t.lan.qd and t.lan.so_dong])


def tong_hop_cac_lan(con, ma_ho: int, bc=None) -> dict:
    """dict(so_lan (đã lập - có dòng), so_da_duyet, tien_tung_lan {lần: tổng}, tong_cong_don, chua_duyet [lần])."""
    th = tong_hop_ho(con, ma_ho, bc)
    return dict(so_lan=th['so_lan_co_dong'], so_da_duyet=th['so_da_duyet'],
                tien_tung_lan={t.lan.lan: t.tong for t in th['lan']}, tong_cong_don=th['tong'], chua_duyet=th['chua_duyet'])


def ho_nhieu_lan(con) -> set:
    """Mã các hộ có từ 2 lần phương án trở lên (có dòng ở lần >= 2 hoặc dòng pa_lan lần >= 2)."""
    from .nghiep_vu import co_cot_lan
    kq = set()
    if co_cot_lan(con):
        for b in ('ct_dat', 'ct_khoan'):
            kq |= {r[0] for r in con.execute(f'SELECT DISTINCT ma_ho FROM {b} WHERE lan >= 2')}
    if co_bang(con):
        kq |= {r[0] for r in con.execute('SELECT DISTINCT ma_ho FROM pa_lan WHERE lan >= 2')}
    return kq

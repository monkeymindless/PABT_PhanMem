"""Phễu tiến độ THEO HỘ / LẦN PHƯƠNG ÁN (người dùng 30/10/2026: "không phải hộ nào cũng làm trong đợt 1, không phải hộ nào cũng đủ 16
bước - có hộ chỉ có phương án bổ sung"; thay thanh 16 bước cấp dự án). Không Qt. Mỗi hộ nằm ĐÚNG MỘT giai đoạn (tổng các giai đoạn =
số hộ - `KetQuaPheu.doi_soat`), xét theo LẦN phương án đang mở; dữ liệu mâu thuẫn không bị che: hộ vẫn ở giai đoạn có bằng chứng mạnh
nhất và được gắn CỜ đếm riêng ("Cần kiểm tra").

Lần xét của một hộ: lần CHƯA phê duyệt (không khóa, không bị điều chỉnh thay) có dòng phương án, muộn nhất; không có thì lần đã phê
duyệt muộn nhất; hộ chưa có dòng nào: lần 1. Bằng chứng theo thứ tự: quyết định của lần (qd_ho.lan; 0 = trước v17 = lần 1) -> đợt
trình của lần (pa_lan.dot_trinh_id; trống mà hộ CHƯA có quyết định nào thì dùng ho.dot_id - không nhầm được lần) -> ý kiến niêm yết
của lần (y_kien_du_thao.lan; NULL = lần 1; dòng mới nhất, bỏ dòng đã chuyển đợt) -> dòng phương án. Bàn giao: theo_doi.phan_tich_tien_do
(quyết định + nhận đủ tiền + ngày biên bản - cùng quy tắc danh sách hộ). File cũ thiếu bảng / cột: coi như chưa có dữ liệu bước đó.

Dữ liệu thật đã phân tích (ĐT762 171 hộ, 30/10/2026): 138 hộ phương án 0 đồng, 137 tự lập chưa soát, 32 hộ vào đợt trình khi ý kiến còn
"chưa lấy", 170 hộ có ngày bàn giao từ Excel mà chưa có quyết định - đều thành cờ, không đổi giai đoạn."""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field

from .tien import KHONG

GIAI_DOAN_HO = (
    ('chua_lap', 'Chưa lập phương án'),
    ('da_lap', 'Đã lập, chưa niêm yết'),
    ('niem_yet', 'Đang niêm yết, chưa có ý kiến'),
    ('cho_trinh', 'Đã có ý kiến, chờ trình'),
    ('cho_phe_duyet', 'Đã trình, chờ phê duyệt'),
    ('cho_chi_tra', 'Đã phê duyệt, chờ chi trả'),
    ('cho_ban_giao', 'Đã nhận tiền, chờ bàn giao'),
    ('hoan_tat', 'Đã bàn giao mặt bằng'),
)
TEN_GIAI_DOAN = dict(GIAI_DOAN_HO)
TEN_NGAN_GIAI_DOAN = {'chua_lap': 'Chưa lập', 'da_lap': 'Đã lập', 'niem_yet': 'Niêm yết', 'cho_trinh': 'Chờ trình',
                      'cho_phe_duyet': 'Chờ phê duyệt', 'cho_chi_tra': 'Chờ chi trả', 'cho_ban_giao': 'Chờ bàn giao',
                      'hoan_tat': 'Hoàn tất'}
CO = (                                          # cờ "cần kiểm tra" - không đổi giai đoạn
    ('xu_ly_khi_chua_co_pa', 'Đã đưa vào đợt niêm yết / đợt trình nhưng chưa có dòng phương án'),
    ('trinh_thieu_y_kien', 'Đã trình nhưng ý kiến niêm yết còn "chưa lấy"'),
    ('pa_0_dong', 'Có dòng phương án nhưng tổng 0 đồng'),
    ('tu_lap', 'Phần mềm tự lập, chưa soát lại'),
    ('ngay_bg_chua_qd', 'Có ngày bàn giao nhưng chưa có quyết định phê duyệt'),
    ('canh_bao_tien_do', 'Tiến độ nhập tay chưa khớp thứ tự / chứng cứ'),
    ('vuong', 'Vướng pháp lý V1-V5'),
    ('khong_thua', 'Hộ chưa có thửa đất'),
)
TEN_CO = dict(CO)
CO_THONG_TIN = ('pa_bo_sung',)                  # cờ chỉ để biết (không phải lỗi): đang xét lần bổ sung / điều chỉnh
TEN_CO['pa_bo_sung'] = 'Đang xét phương án bổ sung / điều chỉnh (lần >= 2)'


@dataclass
class HoPheu:
    ma_ho: int
    stt: object
    ho_ten: str
    giai_doan: str
    lan: int = 1
    co: set = field(default_factory=set)
    dot_niem_yet: int | None = None
    dot_trinh: int | None = None


@dataclass
class KetQuaPheu:
    ho: list                                    # [HoPheu] theo thứ tự hộ
    che_do: str = 'mo'

    @property
    def so_ho(self) -> int:
        return len(self.ho)

    def dem(self, ds=None) -> dict:
        """{giai đoạn: số hộ} đủ mọi giai đoạn (0 khi không có)."""
        c = Counter(x.giai_doan for x in (self.ho if ds is None else ds))
        return {k: c.get(k, 0) for k, _ in GIAI_DOAN_HO}

    def dem_co(self, ds=None) -> dict:
        c = Counter(k for x in (self.ho if ds is None else ds) for k in x.co)
        return {k: c[k] for k in list(TEN_CO) if c.get(k)}

    def doi_soat(self) -> bool:
        """Tổng các giai đoạn = số hộ, mỗi hộ đúng một giai đoạn hợp lệ."""
        return sum(self.dem().values()) == self.so_ho and all(x.giai_doan in TEN_GIAI_DOAN for x in self.ho)

    def theo_giai_doan(self, gd: str) -> list:
        return [x for x in self.ho if x.giai_doan == gd]

    def theo_co(self, co: str) -> list:
        return [x for x in self.ho if co in x.co]

    def loc_dot(self, dot_niem_yet=None, dot_trinh=None) -> list:
        return [x for x in self.ho if (dot_niem_yet is None or x.dot_niem_yet == dot_niem_yet)
                and (dot_trinh is None or x.dot_trinh == dot_trinh)]


# lệnh (khóa CuaSoChinh.lenh) xử lý tiếp hộ ở từng giai đoạn
LENH_GIAI_DOAN = {'chua_lap': 'Lập phương án hộ…', 'da_lap': 'Dự thảo PABT…', 'niem_yet': 'Dự thảo PABT…', 'cho_trinh': 'Đợt trình…',
                  'cho_phe_duyet': 'Quyết định phê duyệt', 'cho_chi_tra': 'Theo dõi tiến độ', 'cho_ban_giao': 'Theo dõi tiến độ'}
VIEC_GIAI_DOAN = {'chua_lap': '{n} hộ chưa lập phương án', 'da_lap': '{n} hộ đã lập, chưa đưa vào đợt niêm yết',
                  'niem_yet': '{n} hộ đang niêm yết, chưa có ý kiến', 'cho_trinh': '{n} hộ đã có ý kiến, chưa trình thẩm định',
                  'cho_phe_duyet': '{n} hộ đã trình, chưa có quyết định phê duyệt', 'cho_chi_tra': '{n} hộ đã phê duyệt, chưa nhận tiền',
                  'cho_ban_giao': '{n} hộ đã nhận tiền, chưa bàn giao mặt bằng'}


@dataclass
class ViecPheu:
    chu: str
    muc: str                                    # 'loi' (cờ cần kiểm tra) | 'can' (giai đoạn tồn đọng)
    loai: str                                   # 'gd' | 'co'
    khoa: str                                   # khóa giai đoạn / cờ
    lenh: str | None = None
    so: int = 0


def viec_tiep(kq: KetQuaPheu, ds=None, toi_da: int = 7) -> list:
    """Việc nên làm tiếp từ phễu: cờ cần kiểm tra trước (nhiều hộ trước), rồi giai đoạn tồn đọng theo thứ tự quy trình."""
    ds = kq.ho if ds is None else ds
    viec = [ViecPheu(f'{n} hộ: {TEN_CO[k].lower()}', 'loi', 'co', k, None, n)
            for k, n in sorted(kq.dem_co(ds).items(), key=lambda kv: -kv[1]) if k not in CO_THONG_TIN]
    for k, n in kq.dem(ds).items():
        if n and k in VIEC_GIAI_DOAN:
            viec.append(ViecPheu(VIEC_GIAI_DOAN[k].format(n=n), 'can', 'gd', k, LENH_GIAI_DOAN.get(k), n))
    return viec[:toi_da]


def _bang(con) -> set:
    return {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}


def _cot(con, bang: str) -> set:
    return {r[1] for r in con.execute(f'PRAGMA table_info({bang})')}


def tinh(con, lap: dict | None = None, che_do: str = 'mo', tong_hop: list | None = None) -> KetQuaPheu:
    """Phễu của cả dự án. che_do 'mo' (lần đang mở, mặc định) | 'goc' (lần 1 - phương án gốc). lap = lap_pa.phan_loai_lap(con);
    tong_hop = theo_doi.tong_hop(con, tinh_pa=True) nếu nơi gọi đã có (không tính lại)."""
    from . import theo_doi
    from .lap_pa import phan_loai_lap
    if lap is None:
        lap = phan_loai_lap(con)
    if tong_hop is None:
        tong_hop = theo_doi.tong_hop(con, tinh_pa=True)
    B = _bang(con)
    c_ho = _cot(con, 'ho')
    # ---- dữ liệu một lượt
    ho_phu = {}
    sel = ', '.join(k if k in c_ho else f"NULL AS {k}" for k in ('ma_vuong', 'dot_id', 'ban_giao_ngay'))
    for r in con.execute(f'SELECT ma_ho, {sel} FROM ho'):
        ho_phu[r[0]] = (r[1] or '', r[2], r[3] or '')
    co_lan = 'lan' in _cot(con, 'ct_dat') and 'lan' in _cot(con, 'ct_khoan')
    dong = {}                                   # {ma_ho: {lan: số dòng}}
    for bang in ('ct_dat', 'ct_khoan'):
        sql = f'SELECT ma_ho, lan, COUNT(*) FROM {bang} GROUP BY ma_ho, lan' if co_lan else \
            f'SELECT ma_ho, 1, COUNT(*) FROM {bang} GROUP BY ma_ho'
        for ma, lan, n in con.execute(sql):
            d = dong.setdefault(ma, {})
            d[int(lan or 1)] = d.get(int(lan or 1), 0) + n
    pa_lan = {}                                 # {ma_ho: {lan: (khoa, thay_the, dot_trinh_id)}}
    if 'pa_lan' in B:
        c = _cot(con, 'pa_lan')
        sel = ', '.join(k if k in c else f'NULL AS {k}' for k in ('khoa', 'thay_the', 'dot_trinh_id'))
        for r in con.execute(f'SELECT ma_ho, lan, {sel} FROM pa_lan'):
            pa_lan.setdefault(r[0], {})[int(r[1])] = (bool(r[2]), int(r[3] or 0), r[4])
    y_kien = {}                                 # {(ma_ho, lan): (dot_id, loai)} dòng mới nhất còn hiệu lực
    if 'y_kien_du_thao' in B:
        c = _cot(con, 'y_kien_du_thao')
        lan_sql = 'lan' if 'lan' in c else 'NULL'
        chuyen = 'chuyen_dot_id' if 'chuyen_dot_id' in c else 'NULL'
        for r in con.execute(f'SELECT ma_ho, {lan_sql}, dot_id, loai, {chuyen} FROM y_kien_du_thao ORDER BY dot_id, id'):
            k = (r[0], int(r[1] or 1))
            if r[4] is not None and k in y_kien:
                continue                        # dòng đã chuyển sang đợt sau: giữ dòng của đợt mới (đọc sau)
            if r[4] is None or k not in y_kien:
                y_kien[k] = (r[2], r[3] or 'chua')
    kq = []
    for x in tong_hop:
        ma = x.ma_ho
        vuong, dot_id_ho, ngay_bg = ho_phu.get(ma, ('', None, ''))
        d = dong.get(ma, {})
        pl = pa_lan.get(ma, {})
        bi_thay = {v[1] for v in pl.values() if v[1]}
        qd_lan = {}                             # {lan: [dòng qd_ho]}
        for q in x.qd:
            qd_lan.setdefault(max(1, int(q.get('lan') or 0)), []).append(q)
        co_qd = bool(x.qd)
        cac_lan = (set(d) | set(qd_lan)) - bi_thay
        if che_do == 'goc':
            lan = 1
        else:
            mo = [n for n in cac_lan if n not in qd_lan and d.get(n) and not pl.get(n, (False, 0, None))[0]]
            if mo:
                lan = max(mo)
            elif qd_lan:
                lan = max(n for n in qd_lan if n not in bi_thay) if set(qd_lan) - bi_thay else max(qd_lan)
            else:
                lan = 1
        h = HoPheu(ma, x.thu_tu, x.ho_ten, 'chua_lap', lan)
        # bằng chứng theo thứ tự mạnh -> yếu
        yk = y_kien.get((ma, lan))
        h.dot_niem_yet = yk[0] if yk else None
        dot_trinh = pl.get(lan, (False, 0, None))[2]
        if dot_trinh is None and not co_qd and dot_id_ho is not None:
            dot_trinh = dot_id_ho               # hộ chưa có quyết định nào: đợt trình của hộ là đợt của lần đang xét
        h.dot_trinh = dot_trinh
        if lan in qd_lan:
            if any(not q['da_chi_tra'] for q in qd_lan[lan]):
                h.giai_doan = 'cho_chi_tra'
            else:
                h.giai_doan = 'hoan_tat' if x.tien_do.da_bg else 'cho_ban_giao'
        elif not d.get(lan):
            h.giai_doan = 'chua_lap'
            if yk or dot_trinh is not None:
                h.co.add('xu_ly_khi_chua_co_pa')
        elif dot_trinh is not None:
            h.giai_doan = 'cho_phe_duyet'
            if not yk or yk[1] == 'chua':
                h.co.add('trinh_thieu_y_kien')
        elif yk:
            h.giai_doan = 'niem_yet' if yk[1] == 'chua' else 'cho_trinh'
        else:
            h.giai_doan = 'da_lap'
        # cờ
        if d.get(lan) and not (x.tong_pa or KHONG):
            h.co.add('pa_0_dong')
        if lap.get(ma) == 'tu_lap' and lan == 1:
            h.co.add('tu_lap')
        if ngay_bg.strip() and not co_qd:
            h.co.add('ngay_bg_chua_qd')
        if x.tien_do.canh_bao:
            h.co.add('canh_bao_tien_do')
        if vuong.strip():
            h.co.add('vuong')
        if not x.thua:
            h.co.add('khong_thua')
        if lan > 1:
            h.co.add('pa_bo_sung')
        kq.append(h)
    return KetQuaPheu(kq, che_do)

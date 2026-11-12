"""Tiếp nhận & kiểm tra pháp lý hồ sơ đầu vào dự án (1.0.04 - người dùng 19/10/2026): sau khái toán, trước khi triển khai dự án
mới. Chạy được trên MÁY TRẮNG (chưa có dự án .pabt): dữ liệu là một dict lưu file .pabtpl (JSON) độc lập; khi có dự án mở thì
lưu thêm vào cai_dat của dự án (khóa KHOA_DU_AN - không thuộc danh mục, không khóa).

Căn cứ dùng trong danh mục kiểm tra (chữ hiển thị, không tự suy luận thêm): Luật Đất đai 2024 (Điều 78, 79, 122, 127), Nghị định
88/2024/NĐ-CP, Nghị định 102/2024/NĐ-CP (Điều 60, 62), Luật Đầu tư công, Luật Đầu tư, Luật Xây dựng, Thông tư 08/2024/TT-BTNMT,
Thông tư 26/2024/TT-BTNMT, Quyết định 18/2026/QĐ-UBND. Số điều / khoản theo yêu cầu của người dùng - CHƯA đối chiếu văn bản gốc
trong phần mềm (ghi ở CLAUDE.md); người dùng sửa được ghi chú từng mục.

Không phụ thuộc Qt. Không ghi số liệu thật nào vào mã (máy trắng = dữ liệu trống).
"""
from __future__ import annotations

import json
from datetime import date, datetime
from pathlib import Path

from . import an_toan as _an_toan
from .tien import D, KHONG, so_vn

DUOI = '.pabtpl'
KHOA_DU_AN = 'TIEP_NHAN_PHAP_LY'          # cai_dat của dự án: JSON hồ sơ tiếp nhận
PHIEN_BAN = 1

# ---------------------------------------------------------------- loại chủ đầu tư / căn cứ thu hồi
LOAI_CDT = (
    ('cong', 'Đơn vị Công (Vốn đầu tư công / ngân sách nhà nước)'),
    ('tu_dau_thau', 'Đơn vị Tư (Đấu thầu dự án có sử dụng đất - Khoản 27 Điều 79 Luật Đất đai 2024)'),
    ('tu_thoa_thuan', 'Đơn vị Tư (Tự thỏa thuận nhận quyền sử dụng đất - Điều 127 Luật Đất đai, Điều 60 NĐ 102/2024)'),
    ('tu_75', 'Đơn vị Tư (Đã thỏa thuận > 75% diện tích và > 75% số người sử dụng đất, thu hồi phần còn lại < 25% - '
              'Điểm b Khoản 2 Điều 127 Luật Đất đai, Điều 62 NĐ 102/2024)'),
)
TEN_LOAI_CDT = dict(LOAI_CDT)

CAN_CU = (
    ('d78', 'Điều 78 Luật Đất đai 2024 - Thu hồi đất vì mục đích quốc phòng, an ninh'),
    ('d79', 'Điều 79 Luật Đất đai 2024 - Thu hồi đất để phát triển kinh tế - xã hội vì lợi ích quốc gia, công cộng (Khoản 1..32)'),
    ('d122', 'Điều 122 Luật Đất đai 2024 - Chuyển mục đích sử dụng đất trồng lúa, đất rừng'),
    ('d127', 'Điều 127 Luật Đất đai 2024 và Điều 60, 62 Nghị định 102/2024/NĐ-CP - Thỏa thuận nhận quyền sử dụng đất'),
)
TEN_CAN_CU = dict(CAN_CU)
NAM_HIEU_LUC_NQ = 2                         # Nghị quyết HĐND danh mục thu hồi: quá 02 năm chưa có QĐ thu hồi phải xem xét lại

# ---------------------------------------------------------------- 32 đầu mục hồ sơ pháp lý (5 nhóm)
# (mã, nội dung, điều kiện áp dụng) - điều kiện: None = mọi dự án; ('cdt', {...}) theo loại chủ đầu tư; ('cc', mã căn cứ)
NHOM_HO_SO = (
    ('1. Chủ trương, dự án, nguồn vốn, hợp đồng GPMB', (
        ('hs01', 'Quyết định / Nghị quyết chủ trương đầu tư (Luật Đầu tư công / Luật Đầu tư)', None),
        ('hs02', 'Quyết định phê duyệt dự án: Báo cáo nghiên cứu khả thi (BCNCKT) hoặc Báo cáo kinh tế - kỹ thuật (BCKTKT) '
                 '(Luật Xây dựng)', None),
        ('hs03', 'Kế hoạch vốn / văn bản bố trí vốn cho bồi thường, hỗ trợ, tái định cư', ('cdt', {'cong'})),
        ('hs04', 'Hợp đồng / văn bản giao nhiệm vụ bồi thường, giải phóng mặt bằng cho Tổ chức làm nhiệm vụ bồi thường', None),
        ('hs05', 'Văn bản chấp thuận nhà đầu tư / quyết định công nhận kết quả lựa chọn nhà đầu tư', ('cdt', {'tu_dau_thau'})),
        ('hs06', 'Văn bản giao chủ đầu tư / thông tin pháp nhân chủ đầu tư', None),
        ('hs07', 'Khái toán kinh phí bồi thường, hỗ trợ, tái định cư đã được chấp thuận', None),
    )),
    ('2. Quy hoạch, danh mục thu hồi đất, chuyển mục đích', (
        ('hs08', 'Quy hoạch / kế hoạch sử dụng đất được duyệt có dự án', None),
        ('hs09', 'Nghị quyết HĐND tỉnh thông qua danh mục dự án thu hồi đất', ('cc', 'd79')),
        ('hs10', 'Nghị quyết HĐND tỉnh chấp thuận chuyển mục đích đất trồng lúa / đất rừng (Điều 122)', ('cc', 'd122')),
        ('hs11', 'Văn bản chấp thuận cho nhà đầu tư thỏa thuận nhận quyền sử dụng đất (Điều 127, Điều 60 NĐ 102)',
         ('cdt', {'tu_thoa_thuan', 'tu_75'})),
        ('hs12', 'Văn bản / Nghị quyết cho phép thu hồi phần diện tích còn lại (Điều 62 NĐ 102)', ('cdt', {'tu_75'})),
        ('hs13', 'Quy hoạch xây dựng / quy hoạch chi tiết 1/500 hoặc tổng mặt bằng được duyệt', None),
        ('hs14', 'Thông báo thu hồi đất', ('khong_cdt', {'tu_thoa_thuan'})),
        ('hs15', 'Kế hoạch thu hồi đất, điều tra, khảo sát, đo đạc, kiểm đếm', ('khong_cdt', {'tu_thoa_thuan'})),
    )),
    ('3. Bản đồ, trích lục địa chính, mốc giới', (
        ('hs16', 'Bản đồ / trích đo địa chính khu đất thu hồi (Thông tư 26/2024/TT-BTNMT)', None),
        ('hs17', 'Trích lục bản đồ địa chính từng thửa đất', None),
        ('hs18', 'Biên bản bàn giao mốc giới giải phóng mặt bằng ngoài thực địa', None),
        ('hs19', 'Bảng kê thửa đất (Excel) của đơn vị đo đạc', None),
        ('hs20', 'Hồ sơ ranh giới, tọa độ mốc (hệ VN-2000)', None),
        ('hs21', 'Bản vẽ CAD ranh thu hồi (.dxf)', None),
    )),
    ('4. Kiểm tra diện tích, tờ, thửa, loại đất, đối tượng sử dụng đất', (
        ('hs22', 'Diện tích từng thửa khớp bản đồ / trích đo', None),
        ('hs23', 'Số tờ, số thửa đúng bản đồ địa chính', None),
        ('hs24', 'Loại đất ghi đúng ký hiệu Thông tư 08/2024/TT-BTNMT', None),
        ('hs25', 'Đối tượng sử dụng đất xác định rõ (hộ, cá nhân, tổ chức, UBND cấp xã quản lý)', None),
        ('hs26', 'Tổng diện tích thu hồi khớp văn bản chủ trương / quy hoạch', None),
        ('hs27', 'Giấy tờ về quyền sử dụng đất (Giấy chứng nhận, giấy tờ khác) đã thu thập', None),
    )),
    ('5. Hồ sơ khởi động Bước 1 - 4 (Quyết định 18/2026/QĐ-UBND)', (
        ('hs28', 'Bước 1: Xây dựng kế hoạch thu hồi đất', None),
        ('hs29', 'Bước 2: Họp dân trong khu vực thu hồi đất (biên bản)', None),
        ('hs30', 'Bước 3: Thông báo thu hồi đất, gửi thông báo đến người sử dụng đất', ('khong_cdt', {'tu_thoa_thuan'})),
        ('hs31', 'Bước 4: Điều tra, khảo sát, đo đạc, kiểm đếm (xác nhận nguồn gốc của UBND cấp xã)', None),
        ('hs32', 'Đơn giá bồi thường và bảng giá đất áp dụng cho địa bàn', None),
    )),
)
MUC_HO_SO = [m for _, ds in NHOM_HO_SO for m in ds]
# mục bắt buộc để "đủ điều kiện triển khai" (khi áp dụng): chủ trương, dự án, giao nhiệm vụ, quy hoạch, danh mục thu hồi, bản đồ
BAT_BUOC = {'hs01', 'hs02', 'hs04', 'hs05', 'hs08', 'hs09', 'hs10', 'hs11', 'hs12', 'hs16', 'hs17'}

# ---------------------------------------------------------------- 10 tiêu chí kỹ thuật địa chính
KY_THUAT = (
    ('kt01', 'Đủ cột tờ bản đồ, số thửa cho mọi dòng'),
    ('kt02', 'Không trùng (tờ, thửa) giữa các dòng'),
    ('kt03', 'Diện tích thu hồi > 0 và không lớn hơn diện tích thửa'),
    ('kt04', 'Tổng diện tích bảng kê khớp bản đồ thu hồi'),
    ('kt05', 'Loại đất đúng ký hiệu Thông tư 08/2024/TT-BTNMT'),
    ('kt06', 'Có tên người sử dụng đất / tổ chức quản lý từng thửa'),
    ('kt07', 'Phân biệt thửa của hộ, cá nhân với thửa do tổ chức / UBND cấp xã quản lý'),
    ('kt08', 'Đơn vị diện tích thống nhất (m²)'),
    ('kt09', 'Hệ tọa độ VN-2000, kinh tuyến trục đúng của tỉnh'),
    ('kt10', 'Căn cứ pháp lý khác (giấy tờ đất, tranh chấp, kê biên) đã ghi chú'),
)

TRUONG_DU_AN = (('ten', 'Tên dự án'), ('chu_dau_tu', 'Chủ đầu tư'), ('dia_ban', 'Địa bàn (xã, phường)'),
                ('quy_mo_dt', 'Quy mô diện tích dự kiến (m²)'), ('so_thua_dk', 'Số thửa dự kiến'), ('so_ho_dk', 'Số hộ dự kiến'),
                ('nguon_von', 'Nguồn vốn'), ('so_chu_truong', 'Số / ngày chủ trương đầu tư'),
                ('ngay_chu_truong', 'Ngày quyết định chủ trương (dd/mm/yyyy)'),
                ('han_chu_truong', 'Thời hạn thực hiện đến (dd/mm/yyyy)'),
                ('so_nq_hdnd', 'Số Nghị quyết HĐND danh mục thu hồi'), ('ngay_nq_hdnd', 'Ngày thông qua Nghị quyết (dd/mm/yyyy)'),
                ('khoan_79', 'Khoản áp dụng của Điều 79 (1..32)'), ('don_vi_tiep_nhan', 'Đơn vị tiếp nhận'))


def moi() -> dict:
    """Hồ sơ trống (máy trắng: không điền sẵn tên dự án / đơn vị nào)."""
    return dict(phien_ban=PHIEN_BAN, du_an={k: '' for k, _ in TRUONG_DU_AN}, loai_cdt='cong', can_cu=[],
                ho_so={}, ghi_chu={}, ky_thuat={}, ket_qua_excel=None, xac_nhan=dict(du_dieu_kien=False, dung_tien_do=False),
                cap_nhat='')


def chuan(d: dict | None) -> dict:
    """Bổ sung khóa thiếu (file cũ / do người sửa tay); bỏ khóa lạ ở mức trên."""
    g = moi()
    d = d if isinstance(d, dict) else {}
    for k in g:
        if k in d and d[k] is not None:
            g[k] = d[k]
    g['du_an'] = {k: str((d.get('du_an') or {}).get(k, '') or '') for k, _ in TRUONG_DU_AN}
    if g['loai_cdt'] not in TEN_LOAI_CDT:
        g['loai_cdt'] = 'cong'
    g['can_cu'] = [x for x in (g['can_cu'] or []) if x in TEN_CAN_CU]
    for k in ('ho_so', 'ky_thuat', 'ghi_chu'):
        g[k] = {str(a): b for a, b in dict(g[k] or {}).items()}
    g['xac_nhan'] = dict(du_dieu_kien=bool((g['xac_nhan'] or {}).get('du_dieu_kien')),
                         dung_tien_do=bool((g['xac_nhan'] or {}).get('dung_tien_do')))
    return g


# ---------------------------------------------------------------- lưu / mở
def luu_file(d: dict, file) -> Path:
    p = Path(file)
    if p.suffix.lower() != DUOI:
        p = p.with_suffix(DUOI)
    g = chuan(d)
    g['cap_nhat'] = datetime.now().strftime('%d/%m/%Y %H:%M')
    p.parent.mkdir(parents=True, exist_ok=True)
    tam = p.with_name(p.name + '.tmp')
    tam.write_text(json.dumps(g, ensure_ascii=False, indent=1), encoding='utf-8')
    import os
    os.replace(tam, p)
    return p


def mo_file(file) -> dict:
    from .loi import LoiNhap
    try:
        return chuan(json.loads(Path(file).read_text(encoding='utf-8-sig')))
    except FileNotFoundError:
        raise LoiNhap(f'Không thấy file hồ sơ tiếp nhận:\n{file}') from None
    except (OSError, ValueError) as e:
        raise LoiNhap(f'Không đọc được file hồ sơ tiếp nhận (.pabtpl):\n{file}') from e


def doc_du_an(con) -> dict | None:
    """Hồ sơ tiếp nhận lưu trong dự án đang mở (None: chưa có)."""
    from . import csdl
    try:
        s = csdl.doc_cai_dat(con, KHOA_DU_AN, '')
    except Exception:
        return None
    if not s:
        return None
    try:
        return chuan(json.loads(s))
    except ValueError:
        return None


def ghi_du_an(con, d: dict) -> None:
    from . import csdl
    g = chuan(d)
    g['cap_nhat'] = datetime.now().strftime('%d/%m/%Y %H:%M')
    with csdl.giao_dich(con):
        csdl.ghi_cai_dat(con, KHOA_DU_AN, json.dumps(g, ensure_ascii=False))
        csdl.ghi_nhat_ky(con, 'Tiếp nhận & kiểm tra pháp lý hồ sơ đầu vào', trang_thai(g)['nhan'])


def tu_khai_toan(d: dict, file_pabtdt) -> dict:
    """Nạp sơ bộ thông tin chuẩn bị đầu tư từ file khái toán .pabtdt (chỉ điền ô đang trống)."""
    from .kinh_phi_du_an import mo_khai_toan
    dt = mo_khai_toan(file_pabtdt)
    g = chuan(d)
    nguon = dict(ten=getattr(dt, 'ten', ''), chu_dau_tu=getattr(dt, 'chu_dau_tu', ''),
                 dia_ban=getattr(dt, 'dia_ban', '') or getattr(dt, 'dia_chi', ''), quy_mo_dt=getattr(dt, 'quy_mo_dt', ''),
                 so_thua_dk=getattr(dt, 'so_thua_dk', ''), so_ho_dk=getattr(dt, 'so_ho_dk', ''), nguon_von=getattr(dt, 'nguon_von', ''))
    for k, v in nguon.items():
        if not g['du_an'].get(k) and v:
            g['du_an'][k] = str(v)
    return g


def tu_du_an(d: dict, con) -> dict:
    """Điền ô trống từ Thông tin dự án của file .pabt đang mở."""
    from .lap_pa import doc_du_an as doc
    g = chuan(d)
    try:
        da = doc(con)
    except Exception:
        return g
    tt = tom_tat_du_an(con)
    nguon = dict(ten=da.get('ten', ''), chu_dau_tu=da.get('chu_dau_tu', ''),
                 dia_ban=' '.join(f'{da.get("cap_dia_ban", "")} {da.get("ten_dia_ban", "")}'.split()),
                 don_vi_tiep_nhan=da.get('don_vi_lap', ''), so_ho_dk=str(tt['so_ho'] or ''), so_thua_dk=str(tt['so_thua'] or ''),
                 quy_mo_dt=so_vn(tt['dt_thu_hoi']) if tt['dt_thu_hoi'] else '')
    for k, v in nguon.items():
        if not g['du_an'].get(k) and v:
            g['du_an'][k] = str(v)
    return g


# ---------------------------------------------------------------- áp dụng / tổng hợp
def ap_dung(muc, d: dict) -> bool:
    dk = muc[2]
    if dk is None:
        return True
    loai, v = dk
    if loai == 'cdt':
        return d['loai_cdt'] in v
    if loai == 'khong_cdt':
        return d['loai_cdt'] not in v
    if loai == 'cc':
        if v == 'd79':                              # dự án tư tự thỏa thuận không cần NQ danh mục thu hồi
            return v in d['can_cu'] or (not d['can_cu'] and d['loai_cdt'] != 'tu_thoa_thuan')
        return v in d['can_cu']
    return True


def _ngay(s):
    s = str(s or '').strip()
    for f in ('%d/%m/%Y', '%d-%m-%Y', '%Y-%m-%d', '%d.%m.%Y'):
        try:
            return datetime.strptime(s, f).date()
        except ValueError:
            pass
    return None


def kiem_tra_thoi_han(d: dict, hom_nay: date | None = None) -> list:
    """[(mức 'loi'/'canh_bao'/'tin', câu)] về thời hạn chủ trương đầu tư và hiệu lực 02 năm của Nghị quyết HĐND (Khoản 7 Điều
    76 Luật Đất đai 2024 - theo yêu cầu người dùng)."""
    hn = hom_nay or date.today()
    da = d['du_an']
    kq = []
    ct, han, nq = _ngay(da.get('ngay_chu_truong')), _ngay(da.get('han_chu_truong')), _ngay(da.get('ngay_nq_hdnd'))
    if da.get('ngay_chu_truong') and ct is None:
        kq.append(('canh_bao', f'Ngày chủ trương "{da["ngay_chu_truong"]}" không đúng dạng ngày/tháng/năm.'))
    if han is not None:
        con_lai = (han - hn).days
        if con_lai < 0:
            kq.append(('loi', f'Thời hạn thực hiện dự án theo chủ trương đã HẾT từ {han:%d/%m/%Y} ({-con_lai} ngày) - đề nghị chủ '
                              'đầu tư hoàn thiện thủ tục điều chỉnh / gia hạn chủ trương trước khi triển khai.'))
        elif con_lai <= 180:
            kq.append(('canh_bao', f'Thời hạn thực hiện theo chủ trương còn {con_lai} ngày (đến {han:%d/%m/%Y}).'))
        else:
            kq.append(('tin', f'Thời hạn thực hiện theo chủ trương đến {han:%d/%m/%Y} (còn {con_lai} ngày).'))
    elif ct is not None:
        kq.append(('canh_bao', 'Chưa ghi thời hạn thực hiện dự án theo chủ trương - không kiểm tra được tiến độ.'))
    if nq is not None:
        try:
            het = nq.replace(year=nq.year + NAM_HIEU_LUC_NQ)
        except ValueError:                          # 29/02
            het = nq.replace(year=nq.year + NAM_HIEU_LUC_NQ, day=28)
        if hn > het:
            kq.append(('loi', f'Nghị quyết HĐND thông qua ngày {nq:%d/%m/%Y} đã quá 02 năm (từ {het:%d/%m/%Y}) mà chưa có quyết '
                              'định thu hồi đất: phải được HĐND tỉnh xem xét điều chỉnh / hủy bỏ hoặc thông qua lại (Khoản 7 '
                              'Điều 76 Luật Đất đai 2024).'))
        else:
            kq.append(('tin', f'Nghị quyết HĐND còn hiệu lực thực hiện thu hồi đến {het:%d/%m/%Y} ({(het - hn).days} ngày).'))
    elif ap_dung(next(m for m in MUC_HO_SO if m[0] == 'hs09'), d):
        kq.append(('canh_bao', 'Chưa ghi ngày thông qua Nghị quyết HĐND danh mục thu hồi đất.'))
    return kq


def trach_nhiem(d: dict) -> list:
    """Phân tích trách nhiệm của Tổ chức làm nhiệm vụ bồi thường theo loại chủ đầu tư và căn cứ thu hồi (câu hiển thị)."""
    loai, cc = d['loai_cdt'], set(d['can_cu'])
    kq = []
    if loai == 'tu_thoa_thuan':
        kq.append('Nhà nước KHÔNG thu hồi đất: nhà đầu tư tự thỏa thuận nhận quyền sử dụng đất (Điều 127 Luật Đất đai 2024, Điều 60 '
                  'Nghị định 102/2024/NĐ-CP). Tổ chức làm nhiệm vụ bồi thường không lập phương án bồi thường, hỗ trợ, tái định cư; '
                  'chỉ hỗ trợ nghiệp vụ khi có hợp đồng dịch vụ với nhà đầu tư.')
    elif loai == 'tu_75':
        kq.append('Nhà nước thu hồi PHẦN DIỆN TÍCH CÒN LẠI (< 25%) khi nhà đầu tư đã thỏa thuận được trên 75% diện tích và trên 75% '
                  'số người sử dụng đất (Điểm b Khoản 2 Điều 127 Luật Đất đai 2024, Điều 62 Nghị định 102/2024/NĐ-CP). Tổ chức làm '
                  'nhiệm vụ bồi thường lập phương án bồi thường, hỗ trợ, tái định cư cho phần còn lại; kinh phí do nhà đầu tư chi trả.')
    else:
        kq.append('Nhà nước thu hồi đất; Tổ chức làm nhiệm vụ bồi thường tổ chức điều tra, kiểm đếm, '
                  'lập, niêm yết, lấy ý kiến, trình thẩm định phương án bồi thường, hỗ trợ, tái định cư và tổ chức chi trả theo '
                  'trình tự Quyết định 18/2026/QĐ-UBND, Nghị định 88/2024/NĐ-CP.')
        if loai == 'cong':
            kq.append('Dự án đầu tư công: kinh phí bồi thường bố trí trong kế hoạch vốn đầu tư công (Luật Đầu tư công) - kiểm tra kế '
                      'hoạch vốn trước khi chi trả.')
        if loai == 'tu_dau_thau':
            kq.append('Dự án chọn nhà đầu tư qua đấu thầu dự án có sử dụng đất (Khoản 27 Điều 79 Luật Đất đai 2024): nhà đầu tư '
                      'ứng / nộp kinh phí bồi thường, giải phóng mặt bằng theo kết quả lựa chọn nhà đầu tư (Luật Đầu tư).')
    if 'd78' in cc:
        kq.append('Thu hồi vì mục đích quốc phòng, an ninh (Điều 78): phối hợp cơ quan quân sự / công an về ranh giới, mốc giới.')
    if 'd79' in cc:
        k = str(d['du_an'].get('khoan_79') or '').strip()
        kq.append('Thu hồi phát triển kinh tế - xã hội vì lợi ích quốc gia, công cộng (Điều 79' + (f', Khoản {k}' if k else '') +
                  '): cần Nghị quyết HĐND tỉnh thông qua danh mục dự án thu hồi đất.')
    if 'd122' in cc:
        kq.append('Có chuyển mục đích đất trồng lúa / đất rừng (Điều 122): cần Nghị quyết HĐND tỉnh chấp thuận chuyển mục đích '
                  'trước khi quyết định thu hồi.')
    if 'd127' in cc and loai not in ('tu_thoa_thuan', 'tu_75'):
        kq.append('Đã chọn căn cứ Điều 127 nhưng loại chủ đầu tư không phải "tự thỏa thuận" - xem lại loại chủ đầu tư.')
    return kq


def ket_qua_ky_thuat(d: dict) -> dict:
    """Tiêu chí kỹ thuật: người dùng tích tay; tiêu chí đo được từ bảng kê Excel đã quét thì lấy theo kết quả quét."""
    kq = {k: bool(d['ky_thuat'].get(k)) for k, _ in KY_THUAT}
    ex = d.get('ket_qua_excel') or None
    if ex:
        kq['kt01'] = ex.get('thieu_to_thua', 1) == 0
        kq['kt02'] = ex.get('trung', 1) == 0
        kq['kt05'] = ex.get('sai_loai_dat', 1) == 0
        kq['kt06'] = ex.get('thieu_ten', 1) == 0
        if ex.get('dt_0', 1) != 0:
            kq['kt03'] = False
    return kq


def tong_hop(d: dict, hom_nay: date | None = None) -> dict:
    """(1) ĐÃ CÓ, (2) CÒN THIẾU, (3) CẦN BỔ SUNG; đủ điều kiện triển khai / đúng tiến độ (tự đánh giá) + xác nhận của người dùng."""
    d = chuan(d)
    da_co, thieu, bo_sung = [], [], []
    for nhom, ds in NHOM_HO_SO:
        for m in ds:
            if not ap_dung(m, d):
                continue
            gc = str(d['ghi_chu'].get(m[0]) or '').strip()
            (da_co if d['ho_so'].get(m[0]) else thieu).append((m[0], m[1] + (f' ({gc})' if gc else '')))
    for ma, nd in thieu:
        bo_sung.append(f'Đề nghị Chủ đầu tư cung cấp: {nd}.' if int(ma[2:]) <= 21 else f'Hoàn thiện / kiểm tra: {nd}.')
    kt = ket_qua_ky_thuat(d)
    for k, ten in KY_THUAT:
        if not kt[k]:
            bo_sung.append(f'Kỹ thuật địa chính chưa đạt: {ten}.')
    th = kiem_tra_thoi_han(d, hom_nay)
    bo_sung += [c for m, c in th if m in ('loi', 'canh_bao')]
    ex = d.get('ket_qua_excel') or None
    if ex:
        bo_sung += [f'Bảng kê thửa: {x}' for x in ex.get('van_de', [])[:20]]
    thieu_bb = [ma for ma, _ in thieu if ma in BAT_BUOC]
    du = not thieu_bb and not any(m == 'loi' for m, _ in th)
    dung_tien_do = not any(m == 'loi' for m, _ in th)
    return dict(da_co=da_co, con_thieu=thieu, can_bo_sung=bo_sung, thoi_han=th, trach_nhiem=trach_nhiem(d),
                du_dieu_kien_tu_dong=du, dung_tien_do_tu_dong=dung_tien_do, thieu_bat_buoc=thieu_bb, ky_thuat=kt,
                xac_nhan=d['xac_nhan'])


def trang_thai(d: dict | None) -> dict:
    """Tóm tắt một dòng cho Thông tin dự án / thanh trạng thái: so_co / so_ap_dung, nhãn."""
    if not d:
        return dict(so_co=0, so_ap_dung=0, nhan='Chưa tiếp nhận hồ sơ pháp lý đầu vào')
    th = tong_hop(d)
    n_co, n = len(th['da_co']), len(th['da_co']) + len(th['con_thieu'])
    if th['xac_nhan']['du_dieu_kien']:
        nhan = f'Đã xác nhận đủ điều kiện triển khai ({n_co}/{n} hồ sơ)'
    elif th['du_dieu_kien_tu_dong']:
        nhan = f'Đủ hồ sơ bắt buộc ({n_co}/{n}) - chờ xác nhận đủ điều kiện'
    else:
        nhan = f'Còn thiếu {len(th["con_thieu"])} hồ sơ ({len(th["thieu_bat_buoc"])} bắt buộc) - {n_co}/{n}'
    return dict(so_co=n_co, so_ap_dung=n, nhan=nhan)


def tom_tat_du_an(con) -> dict:
    """Quy mô dự án đang mở: số hộ, số thửa, tổng DT thu hồi (Decimal)."""
    if con is None:
        return dict(so_ho=0, so_thua=0, dt_thu_hoi=KHONG)
    try:
        so_ho = con.execute('SELECT COUNT(*) FROM ho').fetchone()[0]
        dt = KHONG
        n = 0
        for r in con.execute('SELECT dt_thu_hoi FROM thua'):
            n += 1
            try:
                dt += D(r[0] or 0)
            except (ArithmeticError, ValueError):
                pass
        return dict(so_ho=so_ho, so_thua=n, dt_thu_hoi=dt)
    except Exception:
        return dict(so_ho=0, so_thua=0, dt_thu_hoi=KHONG)


# ---------------------------------------------------------------- quét bảng kê thửa (Excel của đơn vị đo đạc)
def quet_excel(file) -> dict:
    """Đọc thử bảng kê thửa (nhap_tho.doc - Excel bất kỳ) trên máy trắng: số dòng, số hộ, tổng DT, thiếu tờ / thửa, trùng, sai loại
    đất, thiếu tên. Không ghi gì."""
    from . import nhap_tho
    from .loai_dat import LOAI_DAT, chuan_ma_loai_dat
    kq = nhap_tho.doc(file)
    if kq.bo_cot is None:
        from .loi import LoiNhap
        raise LoiNhap('; '.join(kq.loi) or 'Không tìm thấy bảng thửa đất trong file.')
    ma_hop_le = {m for m, _, _ in LOAI_DAT}
    ten_ho = {h['ma_ho']: (h.get('ho_ten') or '').strip() for h in kq.ho}
    van_de, gap = [], {}
    thieu = trung = sai = dt0 = thieu_ten = 0
    tong = KHONG
    for t in kq.thua:
        dong = t.get('dong', '')
        to, so = str(t['so_to'] or '').strip(), str(t['so_thua'] or '').strip()
        if not to or not so:
            thieu += 1
            van_de.append(f'dòng {dong}: thiếu {"tờ" if not to else "thửa"}.')
        elif (to, so) in gap:
            trung += 1
            van_de.append(f'dòng {dong}: trùng tờ {to} thửa {so} với dòng {gap[(to, so)]}.')
        else:
            gap[(to, so)] = dong
        ld = str(t['loai_dat'] or '').strip()
        if ld:
            ma = chuan_ma_loai_dat(ld)
            if not ma or any(x not in ma_hop_le for x in ma.split('+')):
                sai += 1
                van_de.append(f'dòng {dong}: loại đất "{ld}" không đúng ký hiệu Thông tư 08/2024.')
        try:
            dt = D(t['dt_thu_hoi'] or 0)
        except (ArithmeticError, ValueError):
            dt = KHONG
        if dt <= 0:
            dt0 += 1
        tong += dt
        if not ten_ho.get(t['ma_ho']):
            thieu_ten += 1
    van_de += list(kq.canh_bao[:10])
    return dict(file=str(file), so_dong=len(kq.thua), so_ho=len(kq.ho), tong_dt=str(tong), thieu_to_thua=thieu, trung=trung,
                sai_loai_dat=sai, dt_0=dt0, thieu_ten=thieu_ten, van_de=van_de)


# ---------------------------------------------------------------- xuất văn bản
def xuat_phieu_xlsx(d: dict, file) -> Path:
    """Phiếu Tiếp nhận & Kiểm tra pháp lý hồ sơ dự án (.xlsx): thông tin dự án, 32 mục (áp dụng / có / ghi chú), kỹ thuật địa
    chính, thời hạn, trách nhiệm, tổng hợp có - thiếu - cần bổ sung."""
    import openpyxl
    from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
    d = chuan(d)
    th = tong_hop(d)
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = 'PhieuTiepNhan'
    vien = Border(*(Side(style='thin'),) * 4)
    dam = Font(name='Times New Roman', bold=True, size=12)
    thuong = Font(name='Times New Roman', size=12)
    nen = PatternFill('solid', fgColor='DBEAFE')
    for c, w in zip('ABCDE', (7, 70, 12, 12, 40)):
        ws.column_dimensions[c].width = w
    r = 1

    def dong(*gt, dam_=False, gop=False, to=False):
        nonlocal r
        for i, v in enumerate(gt, start=1):
            o = ws.cell(r, i, v)
            o.font = dam if dam_ else thuong
            o.alignment = Alignment(wrap_text=True, vertical='center', horizontal='left' if i in (2, 5) else 'center')
            if to:
                o.fill = nen
            if not gop:
                o.border = vien
        if gop:
            ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=5)
            ws.cell(r, 1).alignment = Alignment(wrap_text=True, horizontal='left', vertical='center')
        r += 1
    ws.cell(r, 1, 'PHIẾU TIẾP NHẬN VÀ KIỂM TRA PHÁP LÝ HỒ SƠ ĐẦU VÀO DỰ ÁN').font = Font(name='Times New Roman', bold=True, size=14)
    ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=5)
    ws.cell(r, 1).alignment = Alignment(horizontal='center')
    r += 2
    for k, ten in TRUONG_DU_AN:
        dong(f'{ten}: {d["du_an"].get(k) or "…………"}', gop=True)
    dong(f'Loại chủ đầu tư: {TEN_LOAI_CDT[d["loai_cdt"]]}', gop=True)
    dong('Căn cứ thu hồi đất: ' + ('; '.join(TEN_CAN_CU[x] for x in d['can_cu']) or '(chưa chọn)'), gop=True)
    r += 1
    dong('I. TRÁCH NHIỆM CỦA TỔ CHỨC LÀM NHIỆM VỤ BỒI THƯỜNG', dam_=True, gop=True)
    for x in th['trach_nhiem']:
        dong(f'- {x}', gop=True)
    dong('II. THỜI HẠN CHỦ TRƯƠNG, NGHỊ QUYẾT HĐND', dam_=True, gop=True)
    for _, x in th['thoi_han'] or [('', '(chưa ghi ngày chủ trương / Nghị quyết)')]:
        dong(f'- {x}', gop=True)
    dong('III. DANH MỤC HỒ SƠ PHÁP LÝ', dam_=True, gop=True)
    dong('STT', 'Nội dung hồ sơ', 'Áp dụng', 'Đã có', 'Ghi chú', dam_=True, to=True)
    i = 0
    for nhom, ds in NHOM_HO_SO:
        dong('', nhom, '', '', '', dam_=True)
        for m in ds:
            i += 1
            ad = ap_dung(m, d)
            dong(i, m[1] + (' (*)' if m[0] in BAT_BUOC else ''), 'x' if ad else '-',
                 ('x' if d['ho_so'].get(m[0]) else '') if ad else '', str(d['ghi_chu'].get(m[0]) or ''))
    dong('(*) hồ sơ bắt buộc để đủ điều kiện triển khai (khi áp dụng).', gop=True)
    dong('IV. KIỂM TRA KỸ THUẬT ĐỊA CHÍNH', dam_=True, gop=True)
    for k, ten in KY_THUAT:
        dong('', ten, '', 'Đạt' if th['ky_thuat'][k] else 'Chưa', '')
    ex = d.get('ket_qua_excel') or None
    if ex:
        dong(f'Bảng kê đã quét: {Path(ex["file"]).name} - {ex["so_dong"]} thửa, {ex["so_ho"]} chủ sử dụng, tổng '
             f'{so_vn(D(ex["tong_dt"]))} m²', gop=True)
    dong('V. TỔNG HỢP', dam_=True, gop=True)
    dong(f'(1) Đã có: {len(th["da_co"])} hồ sơ.', gop=True)
    dong(f'(2) Còn thiếu: {len(th["con_thieu"])} hồ sơ' + (': ' + '; '.join(x for _, x in th['con_thieu']) if th['con_thieu']
                                                             else '.'), gop=True)
    dong('(3) Cần bổ sung:', gop=True)
    for x in th['can_bo_sung'] or ['(không)']:
        dong(f'   - {x}', gop=True)
    xn = th['xac_nhan']
    dong(f'Dự án đủ điều kiện triển khai: {"CÓ" if xn["du_dieu_kien"] else "CHƯA"} (đánh giá tự động: '
         f'{"đủ" if th["du_dieu_kien_tu_dong"] else "chưa đủ"}).', dam_=True, gop=True)
    dong(f'Dự án đảm bảo đúng tiến độ: {"CÓ" if xn["dung_tien_do"] else "CHƯA"} (đánh giá tự động: '
         f'{"đúng" if th["dung_tien_do_tu_dong"] else "có vấn đề"}).', dam_=True, gop=True)
    ws.page_setup.orientation = 'portrait'
    ws.page_setup.paperSize = 9
    ws.page_setup.fitToWidth = 1
    ws.page_setup.fitToHeight = 0
    ws.sheet_properties.pageSetUpPr.fitToPage = True
    p = Path(file)
    p.parent.mkdir(parents=True, exist_ok=True)
    _an_toan.luu_xlsx(wb, p)
    return p


def xuat_cong_van_docx(d: dict, file, ngay: date | None = None) -> Path:
    """Công văn đề nghị Chủ đầu tư bổ sung hồ sơ (.docx, thể thức Nghị định 30/2020/NĐ-CP: quốc hiệu, tiêu ngữ, số, địa danh -
    ngày, trích yếu, kính gửi, nội dung, nơi nhận, chức vụ người ký). Chưa có dự án: chỗ tên đơn vị / người ký là dòng chấm để
    điền tay (không ghi cố định đơn vị nào)."""
    from . import van_ban_trinh as vb
    d = chuan(d)
    th = tong_hop(d)
    da = d['du_an']
    ng = ngay or date.today()
    p, r, o = vb._p, vb._r, vb._o
    co = 13
    don_vi = (da.get('don_vi_tiep_nhan') or '').strip() or '……………………………'
    trai = o(don_vi.upper(), dam=True, co=12) + o('______', co=12) + o('Số:      /……-……', co=13) + \
        p(r('V/v đề nghị bổ sung hồ sơ pháp lý dự án ' + (da.get('ten') or '……………………'), co=12), can='center', sau=0)
    phai = o('CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM', dam=True, co=12) + \
        p(r('Độc lập - Tự do - Hạnh phúc', dam=True, co=13), can='center', sau=0) + o('______________________', co=12) + \
        o(f'……………, ngày {ng.day:02d} tháng {ng.month:02d} năm {ng.year}', nghieng=True, co=13)
    t = [vb._bang([[trai, phai]], [4400, 9071 + 567 - 4400], vien=False, doc='top', lech=-567)]

    def doan(*chay, **k):
        return p(*chay, dau_dong=709, truoc=60, sau=60, dong=276, **k)
    t.append(p(r('Kính gửi: ' + (da.get('chu_dau_tu') or '……………………………………'), co=co), can='center', truoc=240, sau=120))
    t.append(doan(r('Căn cứ Luật Đất đai năm 2024; Nghị định số 88/2024/NĐ-CP; Nghị định số 102/2024/NĐ-CP; Luật Đầu tư công; Luật '
                    'Đầu tư; Luật Xây dựng; Thông tư số 08/2024/TT-BTNMT; Thông tư số 26/2024/TT-BTNMT; Quyết định số '
                    '18/2026/QĐ-UBND;', co=co)))
    t.append(doan(r(f'{don_vi} đã tiếp nhận và kiểm tra hồ sơ pháp lý đầu vào của dự án '
                    f'{da.get("ten") or "……………………"}' + (f' tại {da["dia_ban"]}' if da.get('dia_ban') else '') +
                    f'. Kết quả: đã có {len(th["da_co"])} hồ sơ, còn thiếu {len(th["con_thieu"])} hồ sơ.', co=co)))
    t.append(doan(r('Để đủ cơ sở triển khai công tác bồi thường, hỗ trợ, tái định cư theo quy định, đề nghị Chủ đầu tư bổ sung các '
                    'hồ sơ, nội dung sau:', co=co)))
    for i, x in enumerate(th['can_bo_sung'] or ['(Không có nội dung cần bổ sung.)'], start=1):
        t.append(doan(r(f'{i}. {x}', co=co)))
    t.append(doan(r('Đề nghị Chủ đầu tư quan tâm, phối hợp gửi hồ sơ bổ sung để đơn vị triển khai thực hiện đúng tiến độ./.',
                    co=co)))
    noi = p(r('Nơi nhận:', dam=True, nghieng=True, co=12), can='left', sau=0) + \
        ''.join(p(r(x, co=11), can='left', sau=0) for x in ('- Như trên;', '- Lưu: VT.'))
    ky = o('……………………………', dam=True, co=13) + o(' ') * 4 + o('……………………………', dam=True, co=13)
    t.append(vb._bang([[noi, ky]], [4170, 4900], vien=False, doc='top'))
    p_ra = Path(file)
    p_ra.parent.mkdir(parents=True, exist_ok=True)
    p_ra.write_bytes(vb._goi_docx(''.join(t)))
    return p_ra


def du_lieu_du_an_moi(d: dict) -> dict:
    """Thông tin ban đầu cho hộp "Dự án mới" khi khởi tạo dự án từ hồ sơ này."""
    da = chuan(d)['du_an']
    return dict(ten=da.get('ten', ''), chu_dau_tu=da.get('chu_dau_tu', ''), dia_ban=da.get('dia_ban', ''),
                don_vi_lap=da.get('don_vi_tiep_nhan', ''))

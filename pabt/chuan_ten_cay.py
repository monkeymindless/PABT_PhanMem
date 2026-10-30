"""Chuẩn tên mục cây trồng của bộ đơn giá theo cách ghi của văn bản (người dùng 30/10/2026: "trong văn bản bộ đơn giá không có chữ trong
ngoặc (năm thứ 3, 4, 5) - chỉ có năm thứ 1, 2, 3 và năm thu hoạch; sửa lỗi nhận dạng font chữ: một số cây bị sai chính tả").

  - Bỏ chú thích quy đổi tuổi "(Năm thứ 4,5,6,7,8)" sau "Năm thu hoạch thứ…" (bộ đơn giá cũ tự thêm - không có trong văn bản; năm tuổi
    nay tính theo cấu trúc: hieu_tai_san.bang_tuoi). Khoảng năm viết như văn bản "thứ 1 - 5" (trước "thứ 1-5").
  - Sửa chính tả tên loài bị lỗi phông / nhập liệu (SUA_CHINH_TA) - đối chiếu bản VBHN cây trồng (QĐ 48/2025, sửa đổi QĐ 66/2025).
Mã, đơn giá, ghi chú giữ nguyên; dòng phương án đã lập (ct_khoan) KHÔNG đổi (giữ tên lúc lập). Áp cho bộ đơn giá đóng gói
(tao_bo_don_gia.chuan_hoa), bản bộ đơn giá trên máy (don_gia._nang_cap_ban_may) và danh mục dự án khi mở (app.mo) - qua
ten_cay_lam_nghiep.ap_ten_khac."""
from __future__ import annotations

import re
import unicodedata

# chú thích quy đổi tuổi của bộ đơn giá cũ: "(Năm thứ 4,5,6,7,8)", "(Năm thứ 19 trở đi)", "(Năm thứ 2)"
_RE_CHU_THICH_TUOI = re.compile(r'\s*\(\s*N[ăa]m\s+th[ứu]\s*[\d,\s]+(?:tr[ởo]\s+đi)?\s*\)')
_RE_KHOANG = re.compile(r'(N[ăa]m(?:\s+thu\s+hoạch)?(?:\s+thứ)?\s+\d+)\s*-\s*(\d+)')

# lỗi chính tả / phông của tên loài trong bộ đơn giá cũ -> tên ĐÚNG chữ văn bản (đã đối chiếu ảnh bản VBHN, Phụ lục IV, VI - 30/10/2026;
# văn bản ghi "Huỷnh", "Vên Vên", "Sồi bổm", "Bừi lời lá thuôn", "Bộp không cuông"… thì giữ / theo đúng văn bản). So ĐÚNG chuỗi phần tên loài
SUA_CHINH_TA = {
    "Bò'i lời giấy": 'Bời lời giấy',
    'Ba bet': 'Ba bét',
    'Hoàng đản giả': 'Hoàng đàn giả',
    'Lá nên': 'Lá nến',
    'Muống truồng': 'Muồng truổng',
    'Trám dỏ': 'Trám đỏ',
    'Vối thuốc an độ': 'Vối thuốc ấn độ',
    'Dục nang nhuộm': 'Dực nang nhuộm',
    'Bạch đàn 11 ro': 'Bạch đàn uro',
    'Vẹt trự': 'Vẹt trụ',
    'Cóc vảng': 'Cóc vàng',
    'Đước dôi': 'Đước đôi',
    'Thói chanh bắc -': 'Thôi chanh bắc',
    'Chắp tron': 'Chắp trơn',
    'Lát khét quá nhỏ': 'Lát khét quả nhỏ',
    'Vái': 'Vải',
    'Vở khoai': 'Vỏ khoai',
    'Bộp không cuống': 'Bộp không cuông',
    'Cây Lekima': 'Cây Lekina',
    'Cây Sơ ri': 'Cây sơri',
}
# cả tên mục khác văn bản (sau khi chuẩn khoảng năm)
SUA_TEN_DAY_DU = {
    'Cây mận - Năm thu hoạch thứ 6 - 9': 'Cây mận - Năm thu hoạch thứ 7 - 9',
}
# mục có trong văn bản mà bộ đơn giá cũ thiếu: (tên, ĐVT, đơn giá, ghi chú) - chỉ thêm khi bộ đã có loài đó (các mục khác cùng loài)
MUC_THIEU = [
    ('Cây nho thân gỗ - Năm thu hoạch 6 - 10', 'cây', '781619', 'Mật độ 1.111 cây/ha'),
]
# lỗi gõ ở mọi vị trí của tên (đầu từ)
SUA_CHU = {'Cáy ': 'Cây '}


def _thay_loai(ten: str) -> str:
    """Sửa chính tả phần tên loài (trước " (", " - " hoặc hết chuỗi)."""
    for sai, dung in SUA_CHINH_TA.items():
        if ten.startswith(sai) and (len(ten) == len(sai) or ten[len(sai)] in ' (-,'):
            return dung + ten[len(sai):]
    return ten


def chuan_ten(ten: str) -> str:
    """Tên mục cây trồng theo cách ghi của văn bản (gọi lại không đổi thêm)."""
    if not ten:
        return ten
    t = unicodedata.normalize('NFC', str(ten))
    if re.search(r'(?i)thu\s+ho[ạa]ch', t):
        t = _RE_CHU_THICH_TUOI.sub('', t)
    t = _RE_KHOANG.sub(lambda m: f'{m.group(1)} - {m.group(2)}', t)
    t = _thay_loai(t)
    for sai, dung in SUA_CHU.items():
        t = re.sub(r'(?<!\w)' + re.escape(sai), dung, t)
    t = re.sub(r'\(\s+', '(', re.sub(r'\s+\)', ')', t))
    t = ' '.join(t.split())
    return SUA_TEN_DAY_DU.get(t, t)


def them_muc_thieu(con) -> int:
    """Thêm các mục MUC_THIEU vào dm_taisan (nhóm 3, mã CT tiếp theo) khi bộ / dự án đã có loài đó mà chưa có mục; trong giao dịch
    và khóa danh mục của nơi gọi. Trả số mục đã thêm."""
    from .ma_tai_san import ma_tiep
    from .lap_pa import bo_dau
    try:
        ds = con.execute('SELECT ten, phan_loai FROM dm_taisan WHERE nhom = 3').fetchall()
    except Exception:                                   # noqa: BLE001
        return 0

    def k(x):
        return ' '.join(re.sub(r'[^\w ]', ' ', bo_dau(chuan_ten(x)).lower()).split())
    co = {k(r[0]) for r in ds}
    n, da_cap = 0, {}
    for ten, dvt, gia, ghi in MUC_THIEU:
        loai = ten.split(' - ')[0]
        cung = [r for r in ds if r[0].startswith(loai + ' - ')]
        if not cung or k(ten) in co:
            continue
        con.execute('INSERT INTO dm_taisan (ma, nhom, phan_loai, ten, dvt, don_gia, ghi_chu) VALUES (?, 3, ?, ?, ?, ?, ?)',
                    (ma_tiep(con, 'dm_taisan', 'CT', da_cap), cung[0][1], ten, dvt, gia, ghi))
        n += 1
    return n

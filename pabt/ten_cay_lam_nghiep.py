"""Tên Việt Nam khác của các loài cây lâm nghiệp trồng trên cạn (người dùng 26/10/2026): bộ đơn giá cây trồng chỉ ghi "Tên Việt Nam" nên
tìm cây có nhiều tên gọi (Tùng hương = Bách xanh, Trầm hương = Dó bầu…) không ra. Nguồn: Phụ lục VI "Danh sách nhóm loài cây lâm nghiệp
trồng trên cạn" (Bảng 1 nhóm quý hiếm, Bảng 2-6 nhóm I-V) đính kèm Quyết định số 48/2025/QĐ-UBND (sửa đổi bởi QĐ 66/2025/QĐ-UBND) của
UBND tỉnh (nay là thành phố) Đồng Nai - bản hợp nhất "VBHN cây trồng" xác thực ngày 14/10/2026; chép tay từ ảnh văn bản (cột "Tên Việt Nam
khác"), giữ nguyên chữ của văn bản. Loài không có tên khác không ghi ở đây.

Dòng bộ đơn giá cây lâm nghiệp ("Bách xanh (d >6-9 cm)") -> "Bách xanh (Tùng hương) (d >6-9 cm)": tên khác đứng ngay sau tên Việt Nam, khoảng
đường kính giữ nguyên dạng cũ (cay_trong.khoang_duong_kinh, ten_loai_dk vẫn đọc được). Chỉ đổi dòng có khoảng đường kính "(d …)" - cây ăn
quả / cây hằng năm trùng tên (Mít, Vải…) không đụng. Không Qt."""
from __future__ import annotations

import functools
import re

NGUON = 'Phụ lục VI QĐ 48/2025/QĐ-UBND (sửa đổi bởi QĐ 66/2025/QĐ-UBND) - cột "Tên Việt Nam khác"'

# {Tên Việt Nam (như văn bản): (các tên Việt Nam khác)}
TEN_KHAC = {
    # Bảng 1: nhóm loài cây quý hiếm
    'Bách xanh': ('Tùng hương',),
    'Cẩm lai': ('Cẩm lai bông', 'Cẩm lai mật'),
    'Dó bầu': ('Trầm hương',),
    'Giáng hương': ('Dáng hương quả to', 'Dáng hương căm-bốt'),
    'Giáng hương ấn': ('Dáng hương mắt chim',),
    'Gõ đỏ': ('Gõ cà te', 'Hồ bì', 'Cà te'),
    'Gù hương': ('Vù hương',),
    'Gụ': ('Gụ lau', 'Gõ lau'),
    'Gụ mật': ('Gõ mật',),
    'Hoàng đàn rủ': ('Hoàng đàn',),
    'Lát hoa': ('Lát da đồng', 'Lát chun'),
    'Lim xanh': ('Lim',),
    'Mun': ('Mun sừng',),
    'Mun sọc': ('Thị bông', 'Thị lá nhẵn'),
    'Nghiến': ('Kiêng',),
    'Sến đất hoa chùm': ('Mạy lay',),
    'Sưa': ('Trắc thối', 'Huê mộc vàng'),
    'Thông đỏ bắc': ('Thanh tùng',),
    'Thông lá dẹt': ('Thông ré',),
    'Thông nước': ('Thủy tùng',),
    'Trắc': ('Trắc nam bộ', 'Trắc căm bốt'),
    'Trắc đạo': ('Trắc vàng',),
    'Trai lý': ('Trai',),
    'Xoay': ('Nai sai mét',),
    'Du sam': ('Ngô tùng', 'Thông đất', 'Thông dầu'),
    'Sa mộc dầu': ('Sa mu dầu',),
    # Bảng 2: nhóm I
    'Cẩm liên': ('Cà gần', 'Cà chắc xanh'),
    'Căm xe': ('Cẩm xe', 'Da đá'),
    'Huỷnh': ('Huyện',),
    'Kiền kiền phú quốc': ('Kiền kiền',),
    'Săng đá': ('Sao tía', 'Sao đá', 'Táu đá', 'Săng đào'),
    'Sao hải nam': ('Sao lá to', 'Kiền kiền Nghệ tĩnh'),
    'Sến núi dinh': ('Viết',),
    'Táu mặt quỷ': ('Sao mặt quỷ',),
    'Vắp': ('Dõi', 'Vắp đinh'),
    # Bảng 3: nhóm II
    'Bằng lăng': ('Bằng lăng cườm',),
    'Bằng lăng lòng sao': ('Bằng lăng hoa đỏ',),
    'Cà chắc': ('Cà chí',),
    'Chặc khế': ('Huỳnh đường',),
    'Chai': ('Chò chai', 'Chò nhai', 'Chò vẩy'),
    'Chò chỉ': ('Chò',),
    'Chò đen': ('Chò chai',),
    'Chò lông': ('Dầu thanh',),
    'Chò núi': ('Chai', 'Chò chai'),
    'Dầu': ('Chò lông', 'Dầu đỏ', 'Dầu trạch'),
    'Dầu đồng': ('Dầu lạng sơn', 'Dầu con quay', 'Dầu rái nước'),
    'Dầu lông': ('Dầu chai',),
    'Dầu mít': ('Dầu cát',),
    'Giổi đắng': ('Giổi mỡ',),
    'Hoàng đàn giả': ('Hồng tùng',),
    'Huỳnh đường hoa thân': ('Gội mật', 'Chặc khế mật', 'Gát hương'),
    'Long não': ('Dạ hương',),
    'Sâng': ('Trường', 'Trường mật'),
    'Sến mủ': ('Sến đỏ', 'Sến cát', 'Sến nam'),
    'Sồi áo tơi': ('Giẻ trắng', 'Giẻ bộp'),
    'Sồi bổm': ('Dẻ ban', 'Dẻ đen'),
    'Sồi dĩa': ('Dẻ cau', 'May có'),
    'Sồi lá mỏng': ('Dẻ bắc',),
    'Sồi quả dẹt': ('Dẻ quả dẹt',),
    'Sơn xã': ('Săng sáp',),
    'Sụ hải nam': ('Kháo dầu',),
    'Táu nước': ('Táu xanh', 'Táu trắng'),              # văn bản ghi "Táu xanh (Táu trắng)"
    'Táu trắng': ('Làu táu trắng', 'Làu táu'),
    'Tếch': ('Giá tỵ',),
    'Trường quánh': ('Vải guốc',),
    'Vên Vên': ('Sao cát', 'Vên vên cát'),
    'Vên vên nghệ': ('Vên vên vàng', 'Sến bo bo'),
    # Bảng 4: nhóm III
    'Cà ổi bắc bộ': ('Dẻ đen', 'Giẻ gai'),
    'Cà ổi sapa': ('Giẻ bộp', 'Giẻ vàng mép'),
    'Cà ổi trung hoa': ('Cà ổi lá nhẵn', 'Dẻ gai', 'Khu thụ tầu', 'Dẻ gai hạt nhỏ'),
    'Dầu rái': ('Dầu nước',),
    'Dầu trà beng': ('Dầu đỏ',),
    'Dẻ bắc giang': ('Sồi nâu', 'Sồi bắc giang', 'Giẻ ngô'),
    'Dẻ đỏ': ('Sồi đỏ',),
    'Dẻ gai': ('Cà ổi', 'Cà ổi ấn độ'),
    'Dẻ gai nhím': ('Giẻ mỡ gà', 'Cà ổi lá nhỏ'),
    'Dẻ hạnh nhân': ('Dẻ', 'Sồi lá đào'),
    'Dẻ lỗ': ('Sồi vàng', 'Sồi cau'),
    'Dẻ núi tượng': ('Giẻ xàm',),
    'Dẻ quang': ('Sồi nâu', 'Sồi đấu vàng', 'Dẻ đấu vàng'),
    'Dẻ the': ('Sồi the',),
    'Dẻ trung bộ': ('Giẻ đá',),
    'Dẻ xanh': ('Sồi xanh',),
    'Giẻ ráp': ('Giẻ lèo heo',),
    'Giổi lụa': ('Giổi lông', 'Giổi thơm'),
    'Gổi đỏ': ('Gội lơ',),
    'Gội gác': ('Gội dầu', 'Gội gác đa bông'),
    'Gội nếp': ('Gội báng súng', 'Gội tía'),
    'Gội nhót': ('Gội núi',),
    'Gội nước hoa to': ('Gội gác', 'Gội tẻ'),
    'Hoàng linh bắc bộ': ('Lim vàng', 'Lim xẹt', 'Hoàng linh đá'),     # văn bản ghi hai dòng cùng tên (TT 27, 28): gộp tên khác
    'Hoàng linh nam bộ': ('Lim vàng', 'Lim xẹt', 'Hoàng linh'),
    'Kháo nhậm': ('Kháo tía', 'Re vàng', 'Kháo thơm', 'Re hương'),
    'Lành ngành đẹp': ('Thành ngạnh', 'Lành ngạnh vàng'),
    'Lim xẹt': ('Muồng', 'Lim xẹt tía'),
    'Ninh': ('Nính',),
    'Re bắc bộ': ('Re xanh', 'Nhè xanh', 'Nhè vàng'),
    'Rè bon': ('Kháo vàng', 'Rè'),
    'Rè hoa nhỏ': ('Rè hoa thưa',),
    'Re hương': ('Xá xị',),
    'Re lá cong': ('Re', 'Re hương lá bé', 'Rè'),
    'Rè quả to': ('Kháo', 'Kháo vàng', 'Rè quả dẹt'),
    'Rè thunberg': ('Kháo', 'Rè vàng'),
    'Rè trung hoa': ('Kháo',),
    'Săng đá rắn': ('Săng đá',),
    'Sồi hương': ('Giẻ thơm lá to',),
    'Sồi phảng': ('Sồi', 'Sồi bộp'),
    'Sơn': ('Sơn rừng',),
    'Sụ': ('Kháo', 'Re trắng', 'Sụ lá lớn'),
    'Thông đuôi ngựa': ('Thông mã vĩ',),
    'Thông nàng': ('Bạch tùng', 'Thông tre'),
    'Thông nhựa': ('Thông ta', 'Thông hai lá'),
    'Xà cừ': ('Sọ khỉ', 'Báng súng'),
    # Bảng 5: nhóm IV
    'Chàm ron': ('Chông bốn cánh',),
    'Chò xanh': ('Chiêu liêu xanh',),
    'Chò xót': ('Vối thuốc',),
    'Choại': ('Bàng hôi', 'Nhút', 'Bàng nhút'),
    'Co kiêng': ('Sống rắn',),
    'Cồng mù u': ('Cồng mủ', 'Vảy ốc'),
    'Cồng núi': ('Cồng trắng',),
    'Cồng sữa bắc bộ': ('Mắc niễng', 'Cồng sữa'),
    'Dực nang nhuộm': ('Tròm hoa thưa',),
    'Khỉ pọi': ('Muồng',),
    'Lòng mang lá đa dạng': ('Lòng mang', 'Lòng mang lá lớn'),
    'Lòng mang tía': ('Lòng mang lá nhỏ',),
    'Lòng mang xanh': ('Lòng mang',),
    'Man kinh': ('Đẹn năm lá', 'Bình linh năm lá'),
    'Máu chó': ('Máu chó lá to',),
    'Máu chó lá nhỏ': ('Săng máu',),
    'Mạy chấu': ('Lá ngón', 'Cơi'),
    'Mít': ('Mít mật',),
    'Mít nài': ('Mít rừng',),
    'Mò lá tủ': ('Mò gỗ',),
    'Muồng hoa đào': ('Muồng cánh dán', 'Muồng tía'),
    'Nanh chuột': ('Mò lá nhỏ',),
    'Nhọc': ('Săng đào',),
    'Nô lá thuôn': ('Bài nhài thuôn',),
    'Nụ': ('Hồng pháp',),
    'Quao nước': ('Quao',),
    'Ràng ràng mít': ('Ràng ràng',),
    'Ràng ràng xanh': ('Ràng ràng đá',),
    'Sấu đỏ': ('Sấu tía',),
    'Trạch quạch hạt nhỏ': ('Muồng ràng ràng',),
    'Trám đỏ': ('Cà na',),
    'Trám trắng': ('Cà na', 'Trám ba cạnh'),
    'Trâm xám': ('Trâm',),
    'Vạng': ('Vạng trứng',),
    'Vàng vè': ('Gáo',),
    'Vối thuốc ấn độ': ('Chò xót',),
    'Xăng mả': ('Săng mã',),
    'Xoan': ('Xoan ta',),
    # Bảng 6: nhóm V
    'Ba bét': ('Vạng',),
    'Bồ kết nhỏ': ('Tao giác',),
    'Bông bạc': ('Trẩu',),
    'Bộp không cuông': ('Bộp lá to',),
    'Cô nàng': ('Sỏi',),
    'Cơi': ('Phong dương',),
    'Côi rào': ('Côi núi',),
    'Côm lá bóng': ('Côm lá bạc',),
    'Côm nhật': ('Côm cuống dài',),
    'Đa bắp bè': ('Sung ngứa', 'Bắp bè'),
    'Gạo': ('Mộc miên',),
    'Gòn': ('Bông gòn',),
    'Hồ': ('Ngát', 'Ong bù'),
    'Hồng đạm đồng nai': ('Sún lông',),
    'Hu đen': ('Thung',),
    'Lá nến': ('Ba soi',),
    'Lòng mức trung bộ': ('Thừng mực',),
    'Mùng quân trắng': ('Hồng quân', 'Bồ quân'),
    'Muồng truổng': ('Tóc tiên',),
    'Sảnh cánh': ('Sảng', 'Trôm cước'),
    'Sữa': ('Mò cua',),
    'Sung quả to': ('Sung vàng',),
    'Thung': ('Đáng', 'Tung'),
    'Trẩu trơn': ('Lai',),
    'Vông nem': ('Vông',),
}

_RE_DUONG_KINH = re.compile(r'\(\s*(?:d|đk)\b', re.I)          # khoảng đường kính "(d >6-9 cm)" - chỉ dòng cây lâm nghiệp


def _khoa(ten: str) -> str:
    """Khóa so tên loài: không dấu, chữ thường, gộp khoảng trắng; "ỳ"/"ỷ" như nhau (văn bản ghi "Huỳnh", bộ đơn giá "Huỷnh")."""
    from .lap_pa import bo_dau
    return ' '.join(bo_dau(str(ten or '')).replace('.', ' ').lower().split())


_THEO_KHOA: dict = {}


@functools.lru_cache(maxsize=8192)
def ten_khac(ten_loai: str) -> tuple:
    """Các tên Việt Nam khác của một loài (tên Việt Nam theo văn bản; so không dấu). Không có: (). Nhớ theo chuỗi: mở dự án kiểm lại
    ~5.000 dòng danh mục mỗi lần (1.0.31: 13 -> ~3 ms)."""
    if not _THEO_KHOA:
        for k, v in TEN_KHAC.items():
            _THEO_KHOA[_khoa(k)] = tuple(v)
    return _THEO_KHOA.get(_khoa(ten_loai), ())


def _tach(ten: str) -> tuple:
    """(tên loài, phần còn lại từ dấu "(" đầu tiên) - "Bách xanh (d >6-9 cm)" -> ("Bách xanh", " (d >6-9 cm)")."""
    s = str(ten or '')
    i = s.find('(')
    return (s, '') if i < 0 else (s[:i].rstrip(), s[i:])


def chu_ten_khac(ten_loai: str) -> str:
    """"(Tùng hương)" / "(Cẩm lai bông, Cẩm lai mật)" - chữ chèn sau tên loài; '' khi loài không có tên khác."""
    v = ten_khac(ten_loai)
    return f'({", ".join(v)})' if v else ''


def them_ten_khac(ten: str) -> str:
    """Tên dòng bộ đơn giá cây lâm nghiệp có tên khác ngay sau tên loài: "Bách xanh (d >6-9 cm)" -> "Bách xanh (Tùng hương) (d >6-9 cm)".
    Dòng không có khoảng đường kính, loài không có tên khác, hoặc đã có tên khác: giữ nguyên (gọi lại không đổi thêm)."""
    loai, sau = _tach(ten)
    if not sau or not _RE_DUONG_KINH.match(sau):
        return ten
    chu = chu_ten_khac(loai)
    if not chu:
        return ten
    loai = ' '.join(loai.replace('.', ' ').split())       # bộ đơn giá ghi nhầm "Gội nước.hoa to"
    return f'{loai} {chu} {sau.lstrip()}'


def bo_ten_khac(ten: str) -> str:
    """Ngược them_ten_khac (so khớp tên cũ - bản in / văn bản không ghi tên khác): "Bách xanh (Tùng hương) (d >6-9 cm)" -> "Bách xanh (d >6-9 cm)"."""
    loai, sau = _tach(ten)
    chu = chu_ten_khac(loai)
    if chu and sau.startswith(chu):
        con = sau[len(chu):].lstrip()
        return f'{loai} {con}' if con else loai
    return ten


@functools.lru_cache(maxsize=16384)
def _ten_chuan(ten: str) -> str:
    """Tên chuẩn của một dòng (nhớ: mở lại dự án / bộ đơn giá trong cùng phiên không tính lại 5.500 tên - phương án đột phá 7)."""
    from .chuan_ten_cay import chuan_ten
    return them_ten_khac(chuan_ten(ten))


def _dau_danh_muc(con) -> str:
    """Dấu nhanh của danh mục cây (nhóm 3) + phiên bản phần mềm (quy tắc chuẩn tên đổi theo phiên bản)."""
    from . import __version__
    r = con.execute("SELECT COUNT(*), MAX(ma), SUM(LENGTH(ten)) FROM dm_taisan WHERE nhom = 3").fetchone()
    return f'{__version__}|{r[0]}|{r[1]}|{r[2]}'


def _file_nho_da_chuan():
    from .dia_phuong import thu_muc_may
    return thu_muc_may() / 'chuan_ten_cay.json'


def ap_ten_khac_khi_can(con, file) -> int:
    """ap_ten_khac lúc MỞ dự án, bỏ qua khi danh mục của file này đã chuẩn ở lần mở trước với cùng phiên bản phần mềm (rà soát
    31/10/2026: mỗi lần mở chuẩn lại ~5.500 tên, lần đầu trong phiên ~150 ms). Nhớ ở <thư mục máy>\\chuan_ten_cay.json (KHÔNG ghi
    vào file dự án - ghi thêm sẽ thành một bước Hoàn tác / Google Drive đồng bộ lại)."""
    import json
    import os
    try:
        dau = _dau_danh_muc(con)
    except Exception:                                    # noqa: BLE001 - file không có bảng danh mục
        return 0
    khoa = str(file)
    f = _file_nho_da_chuan()
    try:
        nho = json.loads(f.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        nho = {}
    if not isinstance(nho, dict):
        nho = {}
    if nho.get(khoa) == dau:
        return 0
    n = ap_ten_khac(con)
    try:
        nho[khoa] = _dau_danh_muc(con)
        if len(nho) > 200:                               # chỉ giữ 200 dự án gần nhất
            nho = dict(list(nho.items())[-200:])
        f.parent.mkdir(parents=True, exist_ok=True)
        tam = f.with_name(f.name + '.tmp')
        tam.write_text(json.dumps(nho, ensure_ascii=False), encoding='utf-8')
        os.replace(tam, f)
    except Exception:                                    # noqa: BLE001 - không nhớ được: lần sau chuẩn lại (như cũ)
        pass
    return n


def ap_ten_khac(con, ghi_nhat_ky: bool = True) -> int:
    """Đổi tên các dòng cây lâm nghiệp (dm_taisan nhóm 3) của bộ đơn giá / dự án đang mở cho có tên khác. Mã, đơn giá, ghi chú giữ
    nguyên; dòng phương án đã lập (ct_khoan) KHÔNG đổi (giữ tên lúc lập). Một giao dịch, mở khóa danh mục. Trả số dòng đã đổi.
    30/10/2026: kèm chuẩn tên theo cách ghi văn bản (chuan_ten_cay - bỏ chú thích "(Năm thứ…)", sửa chính tả tên loài)."""
    from . import csdl
    from .chuan_ten_cay import MUC_THIEU, them_muc_thieu
    try:
        ds = con.execute("SELECT ma, ten FROM dm_taisan WHERE nhom = 3").fetchall()
    except Exception:                                    # noqa: BLE001 - file không có bảng danh mục
        return 0
    doi = [(moi, r[0]) for r in ds for moi in (_ten_chuan(r[1]),) if moi != r[1]]
    ten = {r[1].split(' - ')[0] for r in ds}
    if not doi and not any(t.split(' - ')[0] in ten and t not in {r[1] for r in ds} for t, *_ in MUC_THIEU):
        return 0
    with csdl.giao_dich(con), csdl.mo_khoa_danh_muc(con):
        con.executemany('UPDATE dm_taisan SET ten = ? WHERE ma = ?', doi)
        them = them_muc_thieu(con)
        if not doi and not them:
            return 0
        if ghi_nhat_ky:
            csdl.ghi_nhat_ky(con, 'Chuẩn tên cây trồng theo văn bản', f'{len(doi)} dòng bộ đơn giá đổi tên (tên khác cây lâm nghiệp '
                             f'- {NGUON}, bỏ chú thích năm tuổi, sửa chính tả tên loài), thêm {them} mục văn bản có mà bộ thiếu')
    return len(doi) + them

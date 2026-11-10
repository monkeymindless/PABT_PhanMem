"""Câu chữ thông báo cho người dùng - MỘT nơi soạn (không phụ thuộc Qt, kiểm thử được).

Trước đây 27 hộp báo lỗi ghép thẳng ngoại lệ kỹ thuật vào câu ("Không mở được dự án:\\n[Errno 13] Permission denied: ...",
"database is locked"): chuyên viên không biết vì sao, phải làm gì; câu "Không ghi được file (đang mở trong Excel?)" chép lại 9 nơi.
chu_loi() soạn thông báo 3 phần: VIỆC không làm được / LÝ DO bằng tiếng Việt / CÁCH XỬ LÝ; chi tiết kỹ thuật để dòng cuối
(chép gửi hỗ trợ khi cần).
"""
from __future__ import annotations

import errno
import sqlite3
import zipfile

TEN_UD = 'LARC - Lập phương án bồi thường, hỗ trợ'     # tiêu đề cửa sổ / hộp thoại (trước: khai báo lại ở 8 module)
# 3 thẻ của "Bảng tổng hợp kinh phí" (Nhóm 5, 0.9.76): một nguồn cho tên thẻ. Quyết định phê duyệt là trang riêng của Nhóm 6.
THE_TONG_HOP = ('Cơ cấu kinh phí dự án', 'Bảng kinh phí chi tiết', 'Đối soát dự toán Pre-F/S')


_CAU_TRUC_KHAC = ('File dự án có cấu trúc khác phiên bản phần mềm này.',
                  'Cập nhật phần mềm lên bản mới nhất. Nếu vẫn lỗi, dùng Trợ giúp > Chẩn đoán & sửa lỗi hệ thống.')
_SQLITE_LY_DO = (                  # 1.0.58: (cụm trong lỗi SQLite, lý do, cách xử lý)
    ('readonly', 'File dự án đang ở chế độ chỉ đọc (file chỉ xem, thuộc tính Read-only hoặc thư mục không có quyền ghi).',
     'Bỏ thuộc tính chỉ đọc hoặc chép file sang thư mục có quyền ghi rồi mở lại.'),
    ('disk is full', 'Ổ đĩa đã đầy.', 'Giải phóng dung lượng rồi làm lại.'),
    ('disk i/o', 'Không đọc / ghi được file dự án (ổ mạng, USB hoặc Google Drive vừa mất kết nối).',
     'Kiểm tra kết nối ổ đĩa rồi làm lại. Nếu lặp lại, dùng Trợ giúp > Chẩn đoán & sửa lỗi hệ thống.'),
    ('unable to open', 'Không mở được file dự án (đường dẫn không còn tồn tại hoặc không có quyền).',
     'Kiểm tra lại đường dẫn và kết nối ổ đĩa.'),
    ('no such column', *_CAU_TRUC_KHAC), ('no such table', *_CAU_TRUC_KHAC), ('has no column', *_CAU_TRUC_KHAC),
    ('unique constraint', 'Dữ liệu bị trùng với một dòng đã có (ví dụ mã hộ, mã thửa).', 'Đổi giá trị bị trùng hoặc sửa dòng đã có, rồi lưu lại.'),
    ('foreign key', 'Dòng này đang liên kết với hộ / thửa không còn tồn tại hoặc còn dữ liệu phụ thuộc.',
     'Tải lại danh sách rồi làm lại; cần xóa thì xóa dữ liệu phụ thuộc trước.'),
    ('not null', 'Còn thiếu một thông tin bắt buộc.', 'Điền đủ ô bắt buộc rồi lưu lại.'),
    ('check constraint', 'Giá trị nhập không hợp lệ.', 'Kiểm tra lại số liệu vừa nhập.'),
)


def giai_thich(e: BaseException) -> tuple:
    """(lý do, cách xử lý) dễ hiểu cho một ngoại lệ; lỗi nghiệp vụ (LoiNhap...) giữ nguyên câu đã viết bằng tiếng Việt."""
    if isinstance(e, PermissionError) or getattr(e, 'winerror', None) in (5, 32, 33):
        return ('File đang được chương trình khác mở (Excel, Word, Google Drive đang đồng bộ…) hoặc không có quyền ghi.',
                'Đóng file đó (hoặc chờ đồng bộ xong) rồi làm lại; lưu vào thư mục khác nếu thư mục này chỉ được xem.')
    if isinstance(e, FileNotFoundError):
        return ('Không tìm thấy file hoặc thư mục.', 'Kiểm tra lại đường dẫn; ổ USB / ổ mạng / Google Drive còn kết nối.')
    if isinstance(e, OSError) and e.errno == errno.ENOSPC:
        return 'Ổ đĩa đã đầy.', 'Giải phóng dung lượng (dọn Thùng rác, file tạm) rồi làm lại.'
    if isinstance(e, sqlite3.OperationalError) and 'locked' in str(e).lower():
        return ('File dự án đang được máy khác (hoặc cửa sổ LARC khác) ghi.',
                'Chờ vài giây rồi làm lại; nếu vẫn lỗi, mở dự án ở chế độ chỉ xem.')
    if isinstance(e, sqlite3.DatabaseError) and any(k in str(e).lower() for k in ('not a database', 'malformed', 'corrupt')):
        return ('File dự án bị hỏng hoặc không phải file dự án (.larc / .pabt).',
                'Mở bản sao lưu gần nhất (lệnh "Lưu dự án thành…" / thư mục SaoLuu của máy chủ).')
    if isinstance(e, zipfile.BadZipFile):
        return ('File không đúng định dạng Excel / Word mới (có thể bị hỏng, hoặc là file .xls / .doc cũ đổi đuôi).',
                'Mở file bằng Excel / Word, lưu lại dạng .xlsx / .docx rồi chọn lại.')
    if isinstance(e, MemoryError):
        return 'Máy không đủ bộ nhớ cho thao tác này.', 'Đóng bớt chương trình khác rồi làm lại.'
    if isinstance(e, sqlite3.Error):
        chu = str(e)
        if not chu.isascii():                               # câu tiếng Việt từ RAISE(ABORT) của trigger
            return chu, ''
        for cum, ly_do, cach in _SQLITE_LY_DO:
            if cum in chu.lower():
                return ly_do, cach
        return 'Không đọc / ghi được file dự án.', 'Làm lại. Nếu vẫn lỗi, dùng Trợ giúp > Chẩn đoán & sửa lỗi hệ thống.'
    if isinstance(e, (TimeoutError, ConnectionError)):
        return 'Mất kết nối mạng hoặc máy chủ không trả lời.', 'Kiểm tra mạng / thư mục dùng chung rồi làm lại.'
    if isinstance(e, OSError):
        return 'Không đọc / ghi được file trên ổ đĩa hoặc ổ mạng.', 'Kiểm tra ổ đĩa, kết nối mạng rồi làm lại.'
    if type(e).__name__ == 'LoiNhap' or isinstance(e, ValueError):
        if str(e).isascii() and type(e).__module__ in ('builtins', 'json.decoder'):
            return 'Dữ liệu trong ô / file có dạng không đọc được.', 'Kiểm tra lại số liệu hoặc file vừa chọn.'
        return str(e), ''                                   # câu nghiệp vụ đã viết sẵn bằng tiếng Việt
    if type(e).__module__ != 'builtins':                    # lỗi riêng của phần mềm (LoiCad, LoiMayChu…): câu đã viết sẵn
        return str(e) or type(e).__name__, ''
    return ('Phần mềm gặp lỗi không lường trước.', 'Làm lại thao tác. Nếu lặp lại, dùng Trợ giúp > Chẩn đoán & sửa lỗi hệ thống để xuất gói gửi hỗ trợ.')


def chu_loi(viec: str, e: BaseException) -> str:
    """Thông báo lỗi 3 phần, ví dụ chu_loi('Không mở được dự án', e):

        Không mở được dự án.

        Lý do: File đang được chương trình khác mở (Excel, Word, Google Drive đang đồng bộ…) hoặc không có quyền ghi.
        Cách xử lý: Đóng file đó (hoặc chờ đồng bộ xong) rồi làm lại; …

        Chi tiết kỹ thuật: PermissionError: [Errno 13] Permission denied: 'D:\\\\…\\\\DuAn.larc'
    """
    ly_do, cach = giai_thich(e)
    viec = viec.rstrip(' .:')
    phan = [f'{viec}.', '', f'Lý do: {ly_do}']
    if cach:
        phan.append(f'Cách xử lý: {cach}')
    ky_thuat = f'{type(e).__name__}: {e}'
    if ky_thuat.split(': ', 1)[-1] != ly_do:              # lỗi nghiệp vụ đã rõ: không lặp lại câu ở dòng kỹ thuật
        phan += ['', f'Chi tiết kỹ thuật: {ky_thuat}']
    return '\n'.join(phan)


# bộ lọc trạng thái hộ (quan_ly.hop_trang_thai) - ở đây để cửa sổ chính không nạp quan_ly lúc mở phần mềm
TRANG_THAI = [            # (khóa lọc, nhãn)
    ('chua_pa', 'Chưa lập phương án'), ('co_pa', 'Đã lập phương án'),
    ('chua_dot', 'Chưa xếp đợt trình'), ('co_dot', 'Đã xếp đợt trình'),
    ('chua_pd', 'Chưa phê duyệt'), ('da_pd', 'Đã phê duyệt'),
    ('chua_ct', 'Đã phê duyệt, chưa chi trả'), ('da_ct', 'Đã chi trả'),
    ('chua_bg', 'Đã chi trả, chưa bàn giao'), ('da_bg', 'Đã bàn giao mặt bằng'),
    ('co_ghi_chu', 'Có ghi chú theo dõi'),
]

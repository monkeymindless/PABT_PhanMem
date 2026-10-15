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

TEN_UD = 'PABT - Lập phương án bồi thường, hỗ trợ'     # tiêu đề cửa sổ / hộp thoại (trước: khai báo lại ở 8 module)
# 3 thẻ của "Bảng tổng hợp kinh phí" (Nhóm 5, 0.9.76): một nguồn cho tên thẻ. Quyết định phê duyệt là trang riêng của Nhóm 6.
THE_TONG_HOP = ('Cơ cấu kinh phí dự án', 'Bảng kinh phí chi tiết', 'Đối soát dự toán Pre-F/S')


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
        return ('File dự án đang được máy khác (hoặc cửa sổ PABT khác) ghi.',
                'Chờ vài giây rồi làm lại; nếu vẫn lỗi, mở dự án ở chế độ chỉ xem.')
    if isinstance(e, sqlite3.DatabaseError) and any(k in str(e).lower() for k in ('not a database', 'malformed', 'corrupt')):
        return ('File dự án bị hỏng hoặc không phải file dự án (.larc / .pabt).',
                'Mở bản sao lưu gần nhất (lệnh "Lưu dự án thành…" / thư mục SaoLuu của máy chủ).')
    if isinstance(e, zipfile.BadZipFile):
        return ('File không đúng định dạng Excel / Word mới (có thể bị hỏng, hoặc là file .xls / .doc cũ đổi đuôi).',
                'Mở file bằng Excel / Word, lưu lại dạng .xlsx / .docx rồi chọn lại.')
    if isinstance(e, MemoryError):
        return 'Máy không đủ bộ nhớ cho thao tác này.', 'Đóng bớt chương trình khác rồi làm lại.'
    if type(e).__name__ == 'LoiNhap' or isinstance(e, ValueError):
        return str(e), ''                                   # câu nghiệp vụ đã viết sẵn bằng tiếng Việt
    return str(e) or type(e).__name__, ''


def chu_loi(viec: str, e: BaseException) -> str:
    """Thông báo lỗi 3 phần, ví dụ chu_loi('Không mở được dự án', e):

        Không mở được dự án.

        Lý do: File đang được chương trình khác mở (Excel, Word, Google Drive đang đồng bộ…) hoặc không có quyền ghi.
        Cách xử lý: Đóng file đó (hoặc chờ đồng bộ xong) rồi làm lại; …

        Chi tiết kỹ thuật: PermissionError: [Errno 13] Permission denied: 'D:\\\\…\\\\DT762.pabt'
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

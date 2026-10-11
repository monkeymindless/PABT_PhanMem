"""Cổng chờ bản quyền (licensing hook) - đặc tả ARCH-PABT-2026-V4 mục 12.2 (người dùng 11/10/2026).

Giai đoạn thử nghiệm / sử dụng nội bộ: TẠM HOÃN mọi cơ chế khóa máy, mã hóa, tệp license (tránh rào cản cho cán bộ dùng thử,
tránh báo động giả của phần mềm diệt virus). Phần mềm chạy ở chế độ "Bản Tiêu chuẩn - Sử dụng nội bộ".

Khi thương mại hóa: phát hành một gói cập nhật .pabtcn thay module này (kiểm tra license.key, mã phần cứng, các gói Tiêu chuẩn /
Đội ngũ / Cơ quan) - người dùng không phải cài lại phần mềm. Giữ nguyên tên hàm: app.main gọi kiem_tra_ban_quyen() lúc khởi
động, băng tiêu đề / Giới thiệu / tu-kiem hiện mo_ta().
"""
from __future__ import annotations

GOI = 'Bản Tiêu chuẩn · Sử dụng nội bộ'


def kiem_tra_ban_quyen() -> bool:
    """Bản quyền hợp lệ không. Giai đoạn này: luôn hợp lệ."""
    return True


def mo_ta() -> str:
    """Nhãn bản quyền trên băng tiêu đề, Giới thiệu, tự kiểm tra."""
    return GOI

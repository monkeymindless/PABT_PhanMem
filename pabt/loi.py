"""Ngoại lệ dùng chung toàn hệ thống (module lá: không nhập module nào của pabt).

1.0.96 (kiểm toán kiến trúc 09/11/2026): LoiNhap trước nằm ở lap_pa (tầng nghiệp vụ) nhưng 65 file dùng - tầng nền (phan_quyen,
an_toan) phải nhập ngược lap_pa, tạo vòng nạp chỉ sống nhờ thứ tự import. lap_pa vẫn nhập lại tên này: `lap_pa.LoiNhap` không đổi.
"""
from __future__ import annotations


class LoiNhap(ValueError):
    """Giá trị người dùng nhập không hợp lệ (thông báo tiếng Việt, hiện nguyên cho người dùng)."""

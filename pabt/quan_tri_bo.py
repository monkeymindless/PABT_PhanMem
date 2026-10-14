"""Quyền quản trị bộ đơn giá trên máy này (thêm / sửa / xóa / thay thế / cập nhật cả bộ).

Hai cách được sửa:
- đã đăng nhập máy chủ LAN với tài khoản quản trị (`may_chu.PHIEN.la_quan_tri`);
- hoặc mật khẩu quản trị bộ đơn giá lưu ở `<thư mục máy>/quan_tri_bo.json` (PBKDF2, lần đầu đặt khi mở khóa).

Đã đăng nhập máy chủ nhưng không phải quản trị: không sửa được (tránh tự ý đổi đơn giá trên máy dùng chung).
Không Qt — hộp thoại ở man_hinh_don_gia.HopXacThucBo.
"""
from __future__ import annotations
import json
import os
from datetime import datetime
from pathlib import Path

from .lap_pa import LoiNhap

TEN_FILE = 'quan_tri_bo.json'
MK_TOI_THIEU = 6


def file_luu() -> Path:
    from .may_chu import thu_muc_may
    return thu_muc_may() / TEN_FILE


def doc() -> dict:
    try:
        d = json.loads(file_luu().read_text(encoding='utf-8'))
        return d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


def da_dat() -> bool:
    d = doc()
    return bool(d.get('bam') and d.get('muoi'))


def la_quan_tri_may_chu() -> bool:
    from . import may_chu
    return may_chu.PHIEN is not None and bool(may_chu.PHIEN.la_quan_tri)


def bi_chan_may_chu() -> bool:
    """Đã đăng nhập máy chủ nhưng không phải quản trị: không được sửa bộ đơn giá."""
    from . import may_chu
    return may_chu.PHIEN is not None and not may_chu.PHIEN.la_quan_tri


def _kiem_mk(mk: str) -> str:
    mk = str(mk or '')
    if len(mk) < MK_TOI_THIEU:
        raise LoiNhap(f'Mật khẩu quản trị bộ đơn giá cần ít nhất {MK_TOI_THIEU} ký tự.')
    return mk


def dat(mat_khau: str, cu: str = '') -> None:
    """Đặt mật khẩu lần đầu, hoặc đổi (cần mật khẩu cũ đúng)."""
    from .may_chu import bam_mat_khau
    mk = _kiem_mk(mat_khau)
    if da_dat():
        if not dung(cu):
            raise LoiNhap('Mật khẩu quản trị hiện tại không đúng.')
    bam, muoi = bam_mat_khau(mk)
    p = file_luu()
    p.parent.mkdir(parents=True, exist_ok=True)
    tam = p.with_suffix('.tmp')
    tam.write_text(json.dumps(dict(bam=bam, muoi=muoi, tao_luc=datetime.now().isoformat(timespec='seconds')),
                              ensure_ascii=False, indent=1), encoding='utf-8')
    os.replace(tam, p)


def dung(mat_khau: str) -> bool:
    import hmac
    from .may_chu import bam_mat_khau
    d = doc()
    if not d.get('bam') or not d.get('muoi'):
        return False
    bam, _ = bam_mat_khau(str(mat_khau or ''), d['muoi'])
    return hmac.compare_digest(bam, d['bam'])


def mo_ta_quyen() -> str:
    if la_quan_tri_may_chu():
        from . import may_chu
        return f'Tài khoản quản trị máy chủ: {may_chu.PHIEN.ten_hien}'
    if bi_chan_may_chu():
        from . import may_chu
        return f'Tài khoản {may_chu.PHIEN.ten_hien} không phải quản trị máy chủ — không sửa bộ đơn giá được.'
    if da_dat():
        return 'Máy này đã có mật khẩu quản trị bộ đơn giá.'
    return 'Chưa đặt mật khẩu quản trị bộ đơn giá trên máy này (lần đầu mở khóa sẽ đặt).'

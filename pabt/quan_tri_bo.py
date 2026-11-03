"""Quyền quản trị bộ đơn giá trên máy này (thêm / sửa / xóa / thay thế / cập nhật cả bộ).

Hai cách được sửa:
- đã đăng nhập máy chủ LAN với tài khoản quản trị (`may_chu.PHIEN.la_quan_tri`);
- hoặc mật khẩu quản trị bộ đơn giá lưu ở `<thư mục máy>/quan_tri_bo.json` (PBKDF2, lần đầu đặt khi mở khóa).

Đã đăng nhập máy chủ nhưng không phải quản trị: không sửa được (tránh tự ý đổi đơn giá trên máy dùng chung).
Không Qt — hộp thoại ở man_hinh_don_gia.HopXacThucBo.

1.0.56 (người dùng 03/11/2026: "chỉ có tài khoản máy chủ hoặc admin mới được phép sửa bộ đơn giá đất, tài sản, chính sách hỗ trợ, cây
trồng - dùng mạng LAN không thể ai cũng sửa, không thì bộ đơn giá không đồng bộ theo máy chủ được"): khóa ở TẦNG GHI (`kiem_quyen` gọi đầu
mọi hàm ghi của don_gia, nhap_don_gia.ap_dung, gia_dat_nq28, he_so_k - không chỉ ở hộp Bộ đơn giá):
- máy có thiết lập máy chủ LAN (may_chu.json): CHỈ tài khoản quản trị máy chủ đang đăng nhập - mật khẩu máy KHÔNG thay được (offline /
  chưa đăng nhập cũng không sửa); bộ đơn giá do quản trị sửa được phát hành lên máy chủ (dong_bo_don_gia), máy khác nhận khi đăng nhập;
- máy đơn: đã đặt mật khẩu quản trị thì phải mở khóa trong phiên (`mo_khoa_phien`); chưa đặt (máy chưa có người quản trị) thì sửa được,
  hộp Bộ đơn giá buộc đặt mật khẩu ở lần sửa đầu.
"""
from __future__ import annotations
import json
import os
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

from .lap_pa import LoiNhap

TEN_FILE = 'quan_tri_bo.json'
MK_TOI_THIEU = 6
_MO_KHOA_PHIEN = False                  # đã nhập đúng mật khẩu quản trị trong phiên chạy này (máy đơn)
_DONG_BO = 0                            # > 0: đang cài bộ đơn giá nhận từ máy chủ (không kiểm quyền, không phát hành lại)
LOI_PHAT_HANH = ''                      # lỗi lần tự phát hành lên máy chủ gần nhất ('' = được / chưa phát hành)


class LoiQuyenBoDonGia(LoiNhap):
    """Không có quyền sửa bộ đơn giá / bảng giá đất trên máy này."""


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


def may_duoc_quan_ly() -> bool:
    """Máy có thiết lập máy chủ LAN: bộ đơn giá do quản trị máy chủ quản lý (đồng bộ), không sửa riêng trên máy."""
    from . import may_chu
    return bool(may_chu.doc_cau_hinh().get('may_chu'))


def mo_khoa_phien() -> None:
    global _MO_KHOA_PHIEN
    _MO_KHOA_PHIEN = True


def khoa_lai_phien() -> None:
    global _MO_KHOA_PHIEN
    _MO_KHOA_PHIEN = False


def co_quyen_sua() -> bool:
    """Được ghi bộ đơn giá / bảng giá đất / hệ số K trên máy này lúc này không (xem quy tắc ở đầu module)."""
    if _DONG_BO or la_quan_tri_may_chu():
        return True
    if bi_chan_may_chu() or may_duoc_quan_ly():
        return False
    return _MO_KHOA_PHIEN or not da_dat()


def ly_do_khong_sua() -> str:
    from . import may_chu
    if bi_chan_may_chu():
        return (f'Tài khoản {may_chu.PHIEN.ten_hien} không phải quản trị máy chủ: chỉ tài khoản quản trị mới sửa được bộ đơn giá '
                '(đất, tài sản, cây trồng, vật nuôi, chính sách hỗ trợ) - bộ đơn giá dùng chung, đồng bộ theo máy chủ.')
    if may_duoc_quan_ly():
        return ('Máy này dùng máy chủ LAN: bộ đơn giá (đất, tài sản, cây trồng, vật nuôi, chính sách hỗ trợ) chỉ tài khoản quản trị máy '
                'chủ sửa được - đăng nhập tài khoản quản trị rồi sửa (mật khẩu quản trị trên máy không dùng được khi có máy chủ).')
    return 'Bộ đơn giá đang khóa: mở khóa quản trị (mật khẩu quản trị bộ đơn giá trên máy này) rồi sửa.'


def kiem_quyen(viec: str = 'sửa bộ đơn giá') -> None:
    """Gọi ĐẦU mọi hàm ghi bộ đơn giá / bảng giá đất / hệ số K. Không có quyền -> LoiQuyenBoDonGia."""
    if not co_quyen_sua():
        raise LoiQuyenBoDonGia(f'Không {viec} được. {ly_do_khong_sua()}')


@contextmanager
def cho_phep_dong_bo():
    """Cài bộ đơn giá nhận từ máy chủ (dong_bo_don_gia.nhan): không kiểm quyền, không phát hành ngược lại."""
    global _DONG_BO
    _DONG_BO += 1
    try:
        yield
    finally:
        _DONG_BO -= 1


def sau_khi_sua() -> str:
    """Gọi CUỐI mọi hàm ghi: quản trị máy chủ đang đăng nhập -> tự phát hành bộ đơn giá lên máy chủ (máy khác nhận khi đăng nhập).
    Lỗi (mất mạng…) không làm hỏng việc vừa sửa: trả / ghi LOI_PHAT_HANH."""
    global LOI_PHAT_HANH
    if _DONG_BO or not la_quan_tri_may_chu():
        return ''
    try:
        from .dong_bo_don_gia import phat_hanh
        phat_hanh()
        LOI_PHAT_HANH = ''
    except Exception as e:                              # noqa: BLE001 - mất mạng / quyền thư mục: sửa trên máy vẫn giữ
        LOI_PHAT_HANH = f'Chưa phát hành được bộ đơn giá lên máy chủ: {e}'
    return LOI_PHAT_HANH


def mo_ta_quyen() -> str:
    if la_quan_tri_may_chu():
        from . import may_chu
        return f'Tài khoản quản trị máy chủ: {may_chu.PHIEN.ten_hien}'
    if bi_chan_may_chu():
        from . import may_chu
        return f'Tài khoản {may_chu.PHIEN.ten_hien} không phải quản trị máy chủ — không sửa bộ đơn giá được.'
    if may_duoc_quan_ly():
        return 'Máy dùng máy chủ LAN: chỉ tài khoản quản trị máy chủ (đang đăng nhập) sửa được bộ đơn giá.'
    if da_dat():
        return 'Máy này đã có mật khẩu quản trị bộ đơn giá.'
    return 'Chưa đặt mật khẩu quản trị bộ đơn giá trên máy này (lần đầu mở khóa sẽ đặt).'

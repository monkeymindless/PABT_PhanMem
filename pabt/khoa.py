"""Khóa file dự án khi nhiều máy cùng mở (giai đoạn 4).

Máy đang sửa ghi file <tên>.pabt.khoa cạnh file dự án (máy, người dùng, giờ mở, giờ cập nhật) và làm mới mỗi phút.
Máy khác mở cùng file thì thấy đang bị khóa -> mở chỉ xem (hoặc người dùng chọn vẫn mở để sửa).
Khóa không được làm mới quá HET_HAN giây (máy kia tắt đột ngột) thì coi như đã hết.
"""
from __future__ import annotations
import getpass
import json
import os
import time
from datetime import datetime
from pathlib import Path

from .csdl import ten_may

HET_HAN = 180          # giây
LAM_MOI = 60
NGUOI_DUNG = None      # tên người đăng nhập máy chủ (may_chu.dang_nhap); None = tài khoản Windows


def _nguoi() -> str:
    if NGUOI_DUNG:
        return NGUOI_DUNG
    try:
        return getpass.getuser()
    except Exception:
        return os.environ.get('USERNAME', '')


class KhoaFile:
    def __init__(self, file_du_an):
        p = Path(file_du_an)
        self.p = p.with_name(p.name + '.khoa')
        self.cua_toi = dict(may=ten_may(), nguoi=_nguoi(), pid=os.getpid())
        self.dang_giu = False

    def doc(self) -> dict | None:
        try:
            return json.loads(self.p.read_text(encoding='utf-8'))
        except (OSError, ValueError):
            return None

    def la_cua_toi(self, k: dict | None) -> bool:
        return bool(k) and all(k.get(x) == v for x, v in self.cua_toi.items())

    def nguoi_khac(self) -> dict | None:
        """Khóa còn hiệu lực của máy / phiên khác, nếu có."""
        k = self.doc()
        if not k or self.la_cua_toi(k):
            return None
        if time.time() - float(k.get('cap_nhat', 0)) > HET_HAN:
            return None
        return k

    def _ghi(self, mo_luc=None) -> None:
        k = dict(self.cua_toi, mo_luc=mo_luc or time.time(), cap_nhat=time.time())
        tam = self.p.with_name(self.p.name + f'.{os.getpid()}.tmp')
        try:
            tam.write_text(json.dumps(k, ensure_ascii=False), encoding='utf-8')
            os.replace(tam, self.p)
        except OSError:                                 # Drive đang đồng bộ / file bị giữ: không để lại file .tmp
            try:
                tam.unlink()
            except OSError:
                pass
            raise

    def lay(self, ep: bool = False):
        """Giữ khóa. Trả (True, None) nếu được; (False, khóa của người khác) nếu đang bị khóa và không ép."""
        k = self.nguoi_khac()
        if k and not ep:
            return False, k
        try:
            self._ghi()
        except OSError:
            return True, None             # thư mục không ghi được: vẫn cho mở, không khóa
        self.dang_giu = True
        return True, None

    def lam_moi(self) -> bool:
        """Gọi định kỳ. False nếu khóa đã bị máy khác lấy (người kia chọn "vẫn mở để sửa")."""
        if not self.dang_giu:
            return True
        k = self.doc()
        if k and not self.la_cua_toi(k):
            self.dang_giu = False
            return False
        try:
            self._ghi((k or {}).get('mo_luc'))
        except OSError:
            pass
        return True

    def nha(self) -> None:
        if self.dang_giu and self.la_cua_toi(self.doc()):
            try:
                self.p.unlink()
            except OSError:
                pass
        self.dang_giu = False


def mo_ta(k: dict) -> str:
    gio = lambda t: datetime.fromtimestamp(float(t)).strftime('%H:%M %d/%m/%Y')
    return (f'máy "{k.get("may", "?")}", người dùng "{k.get("nguoi", "?")}", mở lúc {gio(k.get("mo_luc", 0))} '
            f'(còn hoạt động lúc {gio(k.get("cap_nhat", 0))})')

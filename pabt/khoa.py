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
            k = json.loads(self.p.read_text(encoding='utf-8'))
        except (OSError, ValueError):
            return None
        return k if isinstance(k, dict) else None

    def la_cua_toi(self, k: dict | None) -> bool:
        return bool(k) and all(k.get(x) == v for x, v in self.cua_toi.items())

    def _gio_noi_luu(self) -> float:
        """1.0.58: đồng hồ CỦA NƠI LƯU file (tạo file thăm dò rồi đọc giờ ghi): máy này nhanh / chậm giờ không làm khóa đang sống thành chết."""
        t = self.p.with_name(f'{self.p.name}.{os.getpid()}.gio')
        try:
            t.write_bytes(b'')
            return t.stat().st_mtime
        except OSError:
            return time.time()
        finally:
            try:
                t.unlink()
            except OSError:
                pass

    def _tuoi_file(self) -> float | None:
        try:
            m = self.p.stat().st_mtime
        except OSError:
            return None
        return self._gio_noi_luu() - m

    def con_hieu_luc(self, k: dict | None) -> bool:
        """Khóa còn sống. Rà soát kiến trúc 31/10/2026: trước đây chỉ so 'cap_nhat' (đồng hồ MÁY KIA) với đồng hồ máy này - hai máy lệch
        giờ quá HET_HAN thì khóa hết hạn sớm / không bao giờ hết. Nay: còn sống khi giờ ghi trong khóa HOẶC thời điểm sửa file khóa (máy
        chủ chia sẻ / ổ đĩa ghi) còn trong HET_HAN; file khóa không được sửa quá 3 x HET_HAN thì chắc chắn đã chết (máy kia tắt đột ngột)
        dù giờ ghi bên trong ở tương lai (đồng hồ máy kia chạy nhanh)."""
        if not k:
            return False
        tf = self._tuoi_file()
        if tf is not None and tf > 3 * HET_HAN:
            return False
        try:
            tk = time.time() - float(k.get('cap_nhat', 0))
        except (TypeError, ValueError):
            tk = HET_HAN + 1
        return tk <= HET_HAN or (tf is not None and tf <= HET_HAN)

    def nguoi_khac(self) -> dict | None:
        """Khóa còn hiệu lực của máy / phiên khác, nếu có."""
        k = self.doc()
        if k is None and self.p.exists() and (self._tuoi_file() or 0) <= HET_HAN:
            return dict(may='?', nguoi='?', mo_luc=time.time(), cap_nhat=time.time())      # 1.0.58: file khóa đang tạo / đang bị giữ: coi như có người
        if not k or self.la_cua_toi(k):
            return None
        return k if self.con_hieu_luc(k) else None

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

    def _tao_loai_tru(self) -> bool:
        """Tạo file khóa CHỈ KHI chưa có (O_EXCL - hai máy mở cùng lúc thì một máy thắng). False: đã có file (máy khác vừa tạo)."""
        k = dict(self.cua_toi, mo_luc=time.time(), cap_nhat=time.time())
        try:
            fd = os.open(str(self.p), os.O_WRONLY | os.O_CREAT | os.O_EXCL)
        except FileExistsError:
            return False
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            f.write(json.dumps(k, ensure_ascii=False))
        return True

    def lay(self, ep: bool = False):
        """Giữ khóa. Trả (True, None) nếu được; (False, khóa của người khác) nếu đang bị khóa và không ép."""
        k = self.nguoi_khac()
        if k and not ep:
            return False, k
        try:
            if ep or self.p.exists():               # ép / khóa cũ đã hết hạn: ghi đè
                self._ghi()
            elif not self._tao_loai_tru():
                k = self.nguoi_khac()                # máy khác vừa tạo khóa trong lúc này
                if k:
                    return False, k
                self._ghi()
        except OSError:
            return True, None             # thư mục không ghi được: vẫn cho mở, không khóa
        if not ep:                                  # hai máy cùng ghi đè khóa hết hạn: đọc lại, ai không còn là chủ thì nhường
            k2 = self.doc()
            if k2 and not self.la_cua_toi(k2) and self.con_hieu_luc(k2):
                return False, k2
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
    def gio(t) -> str:
        try:
            return datetime.fromtimestamp(float(t)).strftime('%H:%M %d/%m/%Y')
        except (TypeError, ValueError, OverflowError, OSError):     # file .khoa hỏng / bị sửa: vẫn hiện được hộp hỏi mở chỉ xem
            return '?'
    return (f'máy "{k.get("may", "?")}", người dùng "{k.get("nguoi", "?")}", mở lúc {gio(k.get("mo_luc", 0))} '
            f'(còn hoạt động lúc {gio(k.get("cap_nhat", 0))})')

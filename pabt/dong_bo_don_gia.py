"""Đồng bộ bộ đơn giá qua máy chủ LAN (1.0.56 - người dùng 03/11/2026: chỉ quản trị máy chủ sửa bộ đơn giá, các máy dùng chung một bộ).

Thư mục máy chủ `<gốc>\\BoDonGia\\`: bo_don_gia.sqlite (tài sản, cây trồng, vật nuôi, chính sách hỗ trợ, tham số, quy định cách tính), bang_gia_dat.json
(bảng giá đất đã thay / bổ sung), he_so_k.json (hệ số K), phien_ban.json (mã = băm các file, lúc, người phát hành, file nào không có).
- phat_hanh: chỉ tài khoản quản trị (quan_tri_bo.sau_khi_sua gọi tự động sau mỗi lần sửa); ghi file tạm rồi os.replace, phien_ban.json ghi CUỐI.
- nhan: khi đăng nhập (app.sau_dang_nhap): mã khác lần nhận trước -> kiểm SHA-256 từng file, cài bằng don_gia.cai_bo / thay file giá đất, hệ số K
  (máy chủ không có -> dùng lại bảng gắn sẵn); ghi mã đã nhận ở `<thư mục máy>\\dong_bo_don_gia.json`.
Không Qt.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import sqlite3
import tempfile
from datetime import datetime
from pathlib import Path

from .lap_pa import LoiNhap

THU_MUC = 'BoDonGia'
FILE_BO = 'bo_don_gia.sqlite'
FILE_GIA_DAT = 'bang_gia_dat.json'
FILE_HE_SO_K = 'he_so_k.json'
FILE_PHIEN_BAN = 'phien_ban.json'
FILE_DA_NHAN = 'dong_bo_don_gia.json'
CO_TOI_DA = 200 * 1024 * 1024


class LoiDongBo(LoiNhap):
    pass


def _sha(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for k in iter(lambda: f.read(1 << 16), b''):
            h.update(k)
    return h.hexdigest()


def _goc(goc=None) -> Path:
    from . import may_chu
    if goc is None:
        if may_chu.PHIEN is None:
            raise LoiDongBo('Chưa đăng nhập máy chủ.')
        goc = may_chu.PHIEN.goc
    return Path(goc) / THU_MUC


def _nguon_gia_dat() -> dict:
    from . import gia_dat_nq28, he_so_k
    return {FILE_GIA_DAT: gia_dat_nq28.file_thay(), FILE_HE_SO_K: he_so_k.file_he_so()}


def _ghi_nguyen_tu(nguon: Path, dich: Path) -> None:
    tam = dich.with_name(dich.name + '.dang_ghi')
    shutil.copyfile(nguon, tam)
    os.replace(tam, dich)


def doc_phien_ban(goc=None) -> dict | None:
    try:
        d = json.loads((_goc(goc) / FILE_PHIEN_BAN).read_text(encoding='utf-8'))
        return d if isinstance(d, dict) and d.get('ma') else None
    except (OSError, ValueError):
        return None


def _file_da_nhan() -> Path:
    from .may_chu import thu_muc_may
    return thu_muc_may() / FILE_DA_NHAN


def ma_da_nhan() -> str:
    try:
        return str(json.loads(_file_da_nhan().read_text(encoding='utf-8')).get('ma') or '')
    except (OSError, ValueError, AttributeError):
        return ''


def _ghi_da_nhan(pb: dict) -> None:
    p = _file_da_nhan()
    p.parent.mkdir(parents=True, exist_ok=True)
    tam = p.with_suffix('.tmp')
    tam.write_text(json.dumps(dict(ma=pb.get('ma', ''), luc=pb.get('luc', ''), nguoi=pb.get('nguoi', ''),
                                   nhan_luc=datetime.now().isoformat(timespec='seconds')), ensure_ascii=False, indent=1), encoding='utf-8')
    os.replace(tam, p)


def phat_hanh(goc=None) -> dict:
    """Quản trị máy chủ: đưa bộ đơn giá đang dùng + bảng giá đất + hệ số K của máy này lên máy chủ. Trả phien_ban.json đã ghi."""
    from . import don_gia, may_chu, quan_tri_bo
    if not quan_tri_bo.la_quan_tri_may_chu():
        raise LoiDongBo('Chỉ tài khoản quản trị máy chủ phát hành được bộ đơn giá.')
    tm = _goc(goc)
    tm.mkdir(parents=True, exist_ok=True)
    pb_mc = doc_phien_ban(goc)                           # 1.0.58: hai quản trị: không đè bản người kia vừa phát hành
    if pb_mc and pb_mc.get('ma') != ma_da_nhan():
        raise LoiDongBo(f'Máy chủ có {mo_ta(pb_mc)} mới hơn bộ đơn giá trên máy này: nhận về rồi sửa lại, không ghi đè.')
    tep = {}
    with tempfile.TemporaryDirectory() as td:
        ban = Path(td) / FILE_BO                         # bản sao nhất quán bằng backup API (bộ có thể đang mở đọc)
        from .csdl import uri_chi_doc
        nguon = sqlite3.connect(uri_chi_doc(don_gia.file_dang_dung()), uri=True)
        ra = sqlite3.connect(str(ban))
        try:
            nguon.backup(ra)
        finally:
            ra.close()
            nguon.close()
        _ghi_nguyen_tu(ban, tm / FILE_BO)
        tep[FILE_BO] = _sha(ban)
    for ten, p in _nguon_gia_dat().items():
        if Path(p).is_file():
            _ghi_nguyen_tu(Path(p), tm / ten)
            tep[ten] = _sha(Path(p))
        else:
            tep[ten] = None                              # máy quản trị dùng bảng gắn sẵn: máy khác cũng dùng lại bảng gắn sẵn
            try:
                (tm / ten).unlink()
            except OSError:
                pass
    ma = hashlib.sha256(json.dumps(tep, sort_keys=True).encode('utf-8')).hexdigest()[:24]
    try:
        pb_bo = don_gia.kiem_tra_bo(tm / FILE_BO).get('phien_ban', '')
    except LoiNhap:
        pb_bo = ''
    pb = dict(ma=ma, luc=datetime.now().isoformat(timespec='seconds'), nguoi=may_chu.PHIEN.ten_hien, may=may_chu._may(),
              phien_ban_bo=pb_bo, tep=tep)
    tam = tm / (FILE_PHIEN_BAN + '.dang_ghi')
    tam.write_text(json.dumps(pb, ensure_ascii=False, indent=1), encoding='utf-8')
    os.replace(tam, tm / FILE_PHIEN_BAN)
    _ghi_da_nhan(pb)                                     # máy quản trị: không tải lại chính bản vừa phát hành
    return pb


def can_nhan(goc=None) -> dict | None:
    """phien_ban.json của máy chủ nếu khác bản máy này đã nhận (None: máy chủ chưa phát hành / đã mới nhất)."""
    pb = doc_phien_ban(goc)
    if pb is None or pb.get('ma') == ma_da_nhan():
        return None
    return pb


def nhan(goc=None, ep: bool = False) -> dict | None:
    """Nhận bộ đơn giá từ máy chủ về máy này. None: không có gì mới. Lỗi kiểm SHA-256 / file hỏng -> LoiDongBo (máy giữ bộ cũ)."""
    from . import don_gia, gia_dat_nq28, he_so_k, quan_tri_bo
    pb = doc_phien_ban(goc)
    if pb is None or (not ep and pb.get('ma') == ma_da_nhan()):
        return None
    tm = _goc(goc)
    tep = pb.get('tep') or {}
    with tempfile.TemporaryDirectory() as td:
        chep = {}
        for ten, sha in tep.items():
            if ten not in (FILE_BO, FILE_GIA_DAT, FILE_HE_SO_K) or sha is None:
                continue
            p = tm / ten
            try:
                if p.stat().st_size > CO_TOI_DA:
                    raise LoiDongBo(f'{ten} trên máy chủ quá lớn.')
                d = Path(td) / ten
                shutil.copyfile(p, d)
            except OSError as e:
                raise LoiDongBo(f'Không đọc được {ten} trên máy chủ: {e}') from e
            if _sha(d) != sha:
                raise LoiDongBo(f'{ten} trên máy chủ không khớp mã kiểm tra (đang được ghi dở hoặc bị sửa ngoài phần mềm) - thử lại sau.')
            chep[ten] = d
        if FILE_BO not in chep:
            raise LoiDongBo('Máy chủ thiếu file bộ đơn giá.')
        don_gia.kiem_tra_bo(chep[FILE_BO])               # file hỏng / không phải bộ đơn giá -> LoiNhap, chưa đổi gì trên máy
        for ten in (FILE_GIA_DAT, FILE_HE_SO_K):
            if ten in chep:
                try:
                    json.loads(chep[ten].read_text(encoding='utf-8'))
                except (OSError, ValueError) as e:
                    raise LoiDongBo(f'{ten} trên máy chủ hỏng: {e}') from e
        with quan_tri_bo.cho_phep_dong_bo():
            tt = don_gia.cai_bo(chep[FILE_BO])
            for ten, dich, quen in ((FILE_GIA_DAT, gia_dat_nq28.file_thay(), gia_dat_nq28._quen),
                                    (FILE_HE_SO_K, he_so_k.file_he_so(), he_so_k._quen)):
                if ten in chep:
                    Path(dich).parent.mkdir(parents=True, exist_ok=True)
                    _ghi_nguyen_tu(chep[ten], Path(dich))
                elif tep.get(ten, 'x') is None:
                    try:
                        Path(dich).unlink()
                    except OSError:
                        pass
                quen()
    _ghi_da_nhan(pb)
    return dict(pb, bo=tt)


def mo_ta(pb: dict) -> str:
    return (f'bộ đơn giá {pb.get("phien_ban_bo") or ""} do {pb.get("nguoi") or "quản trị"} phát hành lúc '
            f'{str(pb.get("luc") or "").replace("T", " ")[:16]}').strip()

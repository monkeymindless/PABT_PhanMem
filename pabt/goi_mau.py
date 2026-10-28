"""Gói mẫu in & cấu hình (.pabtcfg, 0.9.85 - người dùng 14/10/2026): máy đơn không có LAN - người quản trị sửa mẫu in Excel / mẫu
tờ trình / hồ sơ địa phương trên máy mình, xuất MỘT file .pabtcfg gửi qua Zalo / email; máy khác bấm đúp file (bộ cài đăng ký đuôi
.pabtcfg) hoặc Công cụ → Nhập gói mẫu in & cấu hình… là thay mẫu trong khoảng một giây, không cài lại phần mềm.

Gói = zip: goi_mau.json (loai, phien_ban_cau_truc, mo_ta, tao_luc, may, phan_mem, ho_so, tep [{ten, sha256, kich_thuoc}]) +
pabt_profile.json (hồ sơ địa phương đầy đủ) + mau_in/<file> (.xlsx mẫu in / mẫu văn bản trình, .docx mẫu Word, .xml đường kẻ).
Kiểm tra trước khi cài (an_toan): chống bom nén / tên file vượt thư mục, chỉ nhận đúng các loại file trên, SHA-256 từng file khớp
danh sách, .xlsx / .docx là file Office đọc được và KHÔNG có macro (vbaProject.bin), .xml không DOCTYPE / ENTITY, hồ sơ địa phương
hợp lệ (dia_phuong.kiem_tra). Cài: sao lưu file sắp bị thay vào <thư mục máy>\\sao_luu_mau\\<giờ>\\ (giữ SAO_LUU_GIU lần gần nhất),
ghi từng file qua file tạm + os.replace, rồi dia_phuong.nap_lai(). Không Qt (màn hình ở app.py).
"""
from __future__ import annotations
import hashlib
import json
import os
import re
import shutil
import socket
import zipfile
from datetime import datetime
from pathlib import Path

from . import __version__, dia_phuong

DUOI = '.pabtcfg'
LOAI = 'pabt_goi_mau'
PHIEN_BAN_CAU_TRUC = 1
DANH_SACH = 'goi_mau.json'
DUOI_MAU = ('.xlsx', '.docx', '.xml')
SAO_LUU_GIU = 10
CO_TOI_DA = 30 * 2 ** 20                    # một file trong gói (mẫu Excel / Word thường < 1 MB)
_RE_TEN = re.compile(r'^[^\\/:*?"<>|\x00-\x1f]{1,120}$')


class LoiGoiMau(ValueError):
    """Gói .pabtcfg không hợp lệ / không cài được (thông báo tiếng Việt)."""


# ---------------------------------------------------------------- nơi đọc / ghi mẫu
def thu_muc_mau_cai() -> Path:
    """Nơi cài mẫu của gói (mẫu tờ trình .docx / .xlsx): bản đóng gói = %APPDATA%\\PABT\\mau_in; chạy từ mã nguồn = <thư mục máy>\\mau_in
    (kiểm thử đặt PABT_THU_MUC_MAY)."""
    import sys
    if getattr(sys, 'frozen', False) and not os.environ.get('PABT_THU_MUC_MAY'):
        return Path(os.environ.get('APPDATA') or Path.home()) / 'PABT' / 'mau_in'
    return dia_phuong.thu_muc_may() / 'mau_in'


def _bam(du: bytes) -> str:
    return hashlib.sha256(du).hexdigest()


def _la_mau(ten: str) -> bool:
    return bool(_RE_TEN.match(ten)) and Path(ten).name == ten and ten not in ('.', '..') and \
        Path(ten).suffix.lower() in DUOI_MAU and not ten.startswith('~$')        # ~$…: file khóa tạm của Excel / Word đang mở


def ds_mau_hien_hanh() -> list:
    """[(tên file, đường dẫn)] mẫu đang dùng trên máy: mọi mẫu trong thư mục mẫu của máy (mẫu tờ trình đã sửa, mẫu riêng). Từ 1.0.20
    phần mềm không còn mẫu in Excel (bảng tổng hợp dựng bằng mã). Bỏ thư mục con (cu\\, mac_dinh\\)."""
    kq = {}
    for goc in (thu_muc_mau_cai(), dia_phuong.thu_muc_may() / 'mau_in'):
        if goc.is_dir():
            for f in sorted(goc.iterdir()):
                if f.is_file() and _la_mau(f.name):
                    kq.setdefault(f.name, f)
    return sorted(kq.items())


# ---------------------------------------------------------------- tạo gói
def tao_goi(file_ra, mo_ta: str = '', co_ho_so: bool = True, co_mau: bool = True, ho_so: dict | None = None) -> dict:
    """Đóng gói hồ sơ địa phương đang dùng (đầy đủ, đã trộn) + mẫu đang dùng thành file .pabtcfg. Trả danh sách (goi_mau.json).
    ho_so: hồ sơ ĐẦY ĐỦ đóng vào gói thay cho hồ sơ của máy (tạo gói hàng loạt cho đơn vị khác - goi_don_vi; nơi gọi đã kiểm tra)."""
    if not co_ho_so and not co_mau:
        raise LoiGoiMau('Chọn ít nhất hồ sơ địa phương hoặc mẫu in để đóng gói.')
    file_ra = Path(file_ra)
    if file_ra.suffix.lower() != DUOI:
        file_ra = file_ra.with_name(file_ra.name + DUOI)
    hs = dia_phuong.doc() if ho_so is None else ho_so
    tep = []                                            # (tên trong gói, nội dung)
    if co_ho_so:
        tep.append((dia_phuong.TEN_FILE, json.dumps(hs, ensure_ascii=False, indent=2).encode('utf-8')))
    if co_mau:
        for ten, f in ds_mau_hien_hanh():
            try:
                du = f.read_bytes()
            except OSError as e:
                raise LoiGoiMau(f'Không đọc được mẫu {ten}: {e} (đang mở bằng Excel / Word? đóng file rồi thử lại)') from None
            tep.append((f'mau_in/{ten}', du))
    if not tep:
        raise LoiGoiMau('Không có mẫu nào để đóng gói.')
    ds = dict(loai=LOAI, phien_ban_cau_truc=PHIEN_BAN_CAU_TRUC, mo_ta=mo_ta or '', tao_luc=datetime.now().isoformat(timespec='seconds'),
              may=socket.gethostname(), phan_mem=__version__,
              ho_so=(dia_phuong.ten_ho_so() if ho_so is None else str(ho_so.get('ten_ho_so') or '')) if co_ho_so else '',
              tep=[dict(ten=t, sha256=_bam(du), kich_thuoc=len(du)) for t, du in tep])
    file_ra.parent.mkdir(parents=True, exist_ok=True)
    tam = file_ra.with_name(file_ra.name + '.tmp')
    try:
        with zipfile.ZipFile(tam, 'w', zipfile.ZIP_DEFLATED) as z:
            z.writestr(DANH_SACH, json.dumps(ds, ensure_ascii=False, indent=2))
            for t, du in tep:
                z.writestr(t, du)
        os.replace(tam, file_ra)
    except OSError as e:
        tam.unlink(missing_ok=True)
        raise LoiGoiMau(f'Không ghi được gói {file_ra.name}: {e}') from None
    ds['file'] = str(file_ra)
    return ds


# ---------------------------------------------------------------- đọc, kiểm tra gói
def _kiem_office(ten: str, du: bytes) -> None:
    import io
    try:
        with zipfile.ZipFile(io.BytesIO(du)) as z:
            ten_trong = [x.lower() for x in z.namelist()]
    except zipfile.BadZipFile:
        raise LoiGoiMau(f'{ten} không phải file Office (.xlsx / .docx) đọc được.') from None
    if any(x.endswith('vbaproject.bin') for x in ten_trong):
        raise LoiGoiMau(f'{ten} có macro (VBA) - không nhận mẫu có macro.')
    can = 'xl/workbook.xml' if ten.lower().endswith('.xlsx') else 'word/document.xml'
    if can not in ten_trong:
        raise LoiGoiMau(f'{ten} không phải file {"Excel" if can.startswith("xl") else "Word"} hợp lệ (thiếu {can}).')


def doc_goi(file) -> dict:
    """Đọc + kiểm tra toàn bộ gói (không ghi gì). Trả danh sách gói, thêm 'noi_dung' {tên: bytes}, 'ho_so_moi' (đã trộn) nếu có."""
    from .an_toan import LoiAnToan, kiem_tra_xml, kiem_tra_zip
    file = Path(file)
    if file.suffix.lower() != DUOI:
        raise LoiGoiMau(f'{file.name}: không phải gói mẫu in & cấu hình ({DUOI}).')
    try:
        kiem_tra_zip(file, toi_da=200 * 2 ** 20)
    except LoiAnToan as e:
        raise LoiGoiMau(str(e)) from None
    try:
        with zipfile.ZipFile(file) as z:
            ten_trong = z.namelist()
            if DANH_SACH not in ten_trong:
                raise LoiGoiMau(f'{file.name}: thiếu {DANH_SACH} - không phải gói do PABT tạo.')
            try:
                ds = json.loads(z.read(DANH_SACH).decode('utf-8'))
            except (UnicodeDecodeError, json.JSONDecodeError) as e:
                raise LoiGoiMau(f'{DANH_SACH} hỏng: {e}') from None
            if not isinstance(ds, dict) or ds.get('loai') != LOAI:
                raise LoiGoiMau(f'{file.name}: không phải gói mẫu in & cấu hình PABT.')
            if ds.get('phien_ban_cau_truc') != PHIEN_BAN_CAU_TRUC:
                raise LoiGoiMau(f'Gói tạo bằng cấu trúc {ds.get("phien_ban_cau_truc")}, phần mềm này đọc cấu trúc '
                                f'{PHIEN_BAN_CAU_TRUC}: cập nhật phần mềm cùng bản với máy tạo gói ({ds.get("phan_mem", "?")}).')
            khai = ds.get('tep')
            if not isinstance(khai, list) or not khai:
                raise LoiGoiMau('Gói không có file nào.')
            ten_khai = [x.get('ten') for x in khai if isinstance(x, dict)]
            la = sorted(set(ten_trong) - set(ten_khai) - {DANH_SACH})
            if la:
                raise LoiGoiMau(f'Gói có file không khai trong danh sách: {", ".join(la[:5])} - nghi bị sửa, không cài.')
            noi_dung = {}
            for x in khai:
                ten = x.get('ten') if isinstance(x, dict) else None
                if ten == dia_phuong.TEN_FILE:
                    pass
                elif not (isinstance(ten, str) and ten.startswith('mau_in/') and _la_mau(ten[len('mau_in/'):])):
                    raise LoiGoiMau(f'Gói chứa file không được phép: {ten!r} (chỉ nhận {dia_phuong.TEN_FILE} và mẫu '
                                    f'{", ".join(DUOI_MAU)} trong mau_in/).')
                if ten not in ten_trong:
                    raise LoiGoiMau(f'Gói thiếu file {ten}.')
                if z.getinfo(ten).file_size > CO_TOI_DA:
                    raise LoiGoiMau(f'{ten} quá lớn ({z.getinfo(ten).file_size / 2 ** 20:.1f} MB).')
                du = z.read(ten)
                if _bam(du) != x.get('sha256'):
                    raise LoiGoiMau(f'{ten}: mã kiểm tra SHA-256 không khớp - gói hỏng khi gửi / tải, xin gửi lại.')
                noi_dung[ten] = du
    except zipfile.BadZipFile as e:
        raise LoiGoiMau(f'{file.name} hỏng: {e}') from None
    for ten, du in noi_dung.items():
        duoi = Path(ten).suffix.lower()
        if duoi in ('.xlsx', '.docx'):
            _kiem_office(Path(ten).name, du)
        elif duoi == '.xml':
            try:
                kiem_tra_xml(du, Path(ten).name)
            except LoiAnToan as e:
                raise LoiGoiMau(str(e)) from None
    if dia_phuong.TEN_FILE in noi_dung:
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            f = Path(td) / dia_phuong.TEN_FILE
            f.write_bytes(noi_dung[dia_phuong.TEN_FILE])
            try:
                ds['ho_so_moi'] = dia_phuong.kiem_tra_file(f)
            except dia_phuong.LoiHoSo as e:
                raise LoiGoiMau(f'Hồ sơ địa phương trong gói chưa hợp lệ:\n{e}') from None
    ds['noi_dung'] = noi_dung
    return ds


def mo_ta_goi(ds: dict) -> list:
    """Các dòng mô tả gói để hỏi người dùng trước khi cài."""
    mau = sorted(t[len('mau_in/'):] for t in ds['noi_dung'] if t.startswith('mau_in/'))
    d = [f'Tạo lúc {ds.get("tao_luc", "?")} trên máy {ds.get("may", "?")} (PABT {ds.get("phan_mem", "?")}).']
    if ds.get('mo_ta'):
        d.append(f'Mô tả: {ds["mo_ta"]}')
    if dia_phuong.TEN_FILE in ds['noi_dung']:
        d.append(f'Hồ sơ địa phương: {ds.get("ho_so") or ds["ho_so_moi"].get("ten_ho_so", "")}')
    if mau:
        d.append(f'{len(mau)} mẫu: ' + ', '.join(mau))
    return d


# ---------------------------------------------------------------- cài
def _ghi(p: Path, du: bytes) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    tam = p.with_name(p.name + '.tmp')
    tam.write_bytes(du)
    os.replace(tam, p)


def _don_sao_luu(goc: Path) -> None:
    ds = sorted((d for d in goc.iterdir() if d.is_dir()), key=lambda d: d.name) if goc.is_dir() else []
    for d in ds[:-SAO_LUU_GIU]:
        shutil.rmtree(d, ignore_errors=True)


def cai(file) -> dict:
    """Kiểm tra rồi cài gói: sao lưu file sắp bị thay, ghi mẫu + hồ sơ địa phương, nạp lại hồ sơ. Trả {'mau': [tên], 'ho_so': bool,
    'sao_luu': thư mục sao lưu, 'thu_muc_mau': nơi cài mẫu}. Lỗi -> LoiGoiMau, không ghi gì (kiểm tra xong mới ghi)."""
    ds = doc_goi(file)
    tm = thu_muc_mau_cai()
    goc_sl = dia_phuong.thu_muc_may() / 'sao_luu_mau'
    sl = goc_sl / datetime.now().strftime('%Y%m%d_%H%M%S')
    ghi = []                                            # (đích, nội dung)
    for ten, du in ds['noi_dung'].items():
        dich = dia_phuong.file_may() if ten == dia_phuong.TEN_FILE else tm / ten[len('mau_in/'):]
        ghi.append((dich, du))
    try:
        for dich, du in ghi:                            # sao lưu file sắp bị thay (khác nội dung)
            if dich.is_file() and dich.read_bytes() != du:
                ten_sl = sl / ('mau_in' if dich.parent == tm else '') / dich.name
                ten_sl.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(dich, ten_sl)
        for dich, du in ghi:
            _ghi(dich, du)
    except OSError as e:
        raise LoiGoiMau(f'Không ghi được mẫu / hồ sơ: {e}\n(mẫu đang mở bằng Excel / Word? đóng file rồi nhập lại; bản cũ còn ở '
                        f'{sl if sl.exists() else goc_sl})') from None
    _don_sao_luu(goc_sl)
    if dia_phuong.TEN_FILE in ds['noi_dung']:
        dia_phuong.nap_lai()
    return dict(mau=sorted(t[len('mau_in/'):] for t in ds['noi_dung'] if t.startswith('mau_in/')),
                ho_so=dia_phuong.TEN_FILE in ds['noi_dung'], sao_luu=sl if sl.exists() else None, thu_muc_mau=tm,
                ten_ho_so=dia_phuong.ten_ho_so())

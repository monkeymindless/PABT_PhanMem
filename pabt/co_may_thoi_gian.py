"""Cỗ máy thời gian cho dự án (phương án đột phá 8 - an toàn dữ liệu, người dùng 30/10/2026). Không Qt.

1. MỐC: bản chụp nhất quán file dự án (SQLite backup API trên chính kết nối đang mở - không tranh khóa) vào
   <thư mục máy>\\moc_thoi_gian\\<tên>_<băm đường dẫn>\\<giờ><đuôi> + file .json mô tả (lúc, lý do, số hộ, tổng kinh phí, dấu file).
   Tự chụp mỗi giờ khi dự án có thay đổi (app), trước khi khôi phục, trước thao tác hàng loạt; người dùng chụp tay được. Giữ: mọi mốc
   GIU_GIO giờ gần nhất, sau đó một mốc mỗi ngày tới GIU_NGAY ngày, mốc tay luôn giữ; tối đa MOC_TOI_DA mốc.
2. SO SÁNH hai trạng thái (mốc / file hiện tại / bản thử): hộ thêm, hộ bỏ, hộ đổi tiền (tổng theo nghiep_vu.ket_qua_ho), tổng dự án.
3. KHÔI PHỤC: chụp mốc "trước khi khôi phục" của file hiện tại rồi thay file bằng bản của mốc (tạm + os.replace). Nơi gọi đóng kết nối
   trước và mở lại sau (app).
4. THỬ TRƯỚC: chạy một thao tác hàng loạt trên BẢN SAO trong thư mục tạm, so sánh với hiện tại -> người dùng xem rồi mới làm thật trên
   dự án (giữ Hoàn tác, nhật ký như thường)."""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import sqlite3
import tempfile
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path

THU_MUC = 'moc_thoi_gian'
GIU_GIO = 24                      # mọi mốc trong 24 giờ gần nhất
GIU_NGAY = 30                     # rồi mỗi ngày một mốc (mốc muộn nhất của ngày) tới 30 ngày
MOC_TOI_DA = 80
CHU_KY_PHUT = 60                  # app tự chụp mỗi 60 phút khi dự án có thay đổi
LY_DO = {'tu_dong': 'Tự động (mỗi giờ)', 'mo': 'Lúc mở dự án', 'tay': 'Lưu mốc thủ công', 'truoc_khoi_phuc': 'Trước khi khôi phục',
         'truoc_thao_tac': 'Trước thao tác hàng loạt'}


@dataclass
class Moc:
    file: Path
    luc: datetime
    ly_do: str = 'tu_dong'
    ghi_chu: str = ''
    so_ho: int | None = None
    tong: str | None = None             # tổng kinh phí (chuỗi số Decimal)
    dau: str = ''                       # dấu file dự án lúc chụp (cỡ + thời điểm sửa) - không đổi thì không chụp lại

    @property
    def ten_ly_do(self) -> str:
        return LY_DO.get(self.ly_do, self.ly_do) + (f': {self.ghi_chu}' if self.ghi_chu else '')

    @property
    def co(self) -> int:
        try:
            return self.file.stat().st_size
        except OSError:
            return 0


def thu_muc_du_an(file) -> Path:
    """Thư mục mốc của một file dự án (theo tên + băm đường dẫn đầy đủ: hai dự án cùng tên ở hai nơi không lẫn)."""
    from .dia_phuong import thu_muc_may
    p = Path(file)
    try:
        dd = str(p.resolve()).lower()
    except OSError:
        dd = str(p).lower()
    return thu_muc_may() / THU_MUC / f'{p.stem}_{hashlib.sha1(dd.encode("utf-8")).hexdigest()[:8]}'


def dau_file(file) -> str:
    try:
        s = Path(file).stat()
    except OSError:
        return ''
    return f'{s.st_size}:{s.st_mtime_ns}'


def tom_tat(con) -> tuple:
    """(số hộ, tổng kinh phí chuỗi) của một kết nối dự án. Lỗi (file cũ / thiếu bảng): (số hộ, None)."""
    try:
        so_ho = con.execute('SELECT COUNT(*) FROM ho').fetchone()[0]
    except sqlite3.Error:
        return None, None
    try:
        from .nghiep_vu import ket_qua_ho
        from .tien import D
        tong = sum((D(kq.tong) for kq, _ in ket_qua_ho(con).values()), D(0))
        return so_ho, str(tong)
    except Exception:                                   # noqa: BLE001 - tính lỗi (dự án dở dang): vẫn chụp mốc
        return so_ho, None


def ds_moc(file) -> list:
    """Các mốc của dự án, mới nhất trước."""
    tm = thu_muc_du_an(file)
    if not tm.is_dir():
        return []
    kq = []
    for j in tm.glob('*.json'):
        try:
            d = json.loads(j.read_text(encoding='utf-8'))
            f = tm / d['file']
            if not f.is_file():
                continue
            kq.append(Moc(f, datetime.fromisoformat(d['luc']), d.get('ly_do', 'tu_dong'), d.get('ghi_chu', ''), d.get('so_ho'),
                          d.get('tong'), d.get('dau', '')))
        except (OSError, ValueError, KeyError, TypeError):
            continue
    return sorted(kq, key=lambda m: m.luc, reverse=True)


def co_thay_doi(file) -> bool:
    """File dự án đã đổi so với mốc gần nhất (hoặc chưa có mốc)."""
    ds = ds_moc(file)
    return not ds or ds[0].dau != dau_file(file)


def chup_moc(con, file, ly_do: str = 'tu_dong', ghi_chu: str = '', bat_buoc: bool = False) -> Moc | None:
    """Chụp mốc file dự án đang mở qua kết nối con. Không chụp (None): đang giữa giao dịch, hoặc file chưa đổi từ mốc trước (trừ
    bat_buoc). Lỗi ghi đĩa ném OSError / sqlite3.Error để nơi gọi báo."""
    file = Path(file)
    if con.in_transaction:
        return None
    if not bat_buoc and not co_thay_doi(file):
        return None
    tm = thu_muc_du_an(file)
    tm.mkdir(parents=True, exist_ok=True)
    luc = datetime.now()
    ten = f'{luc:%Y%m%d_%H%M%S}{file.suffix or ".larc"}'
    k = 2
    while (tm / ten).exists():
        ten = f'{luc:%Y%m%d_%H%M%S}~{k}{file.suffix or ".larc"}'
        k += 1
    dich = tm / ten
    tam = dich.with_name(dich.name + '.tmp')
    dc = sqlite3.connect(str(tam))
    try:
        con.backup(dc)
        dc.commit()
        from .csdl import bo_anh_ban_do_ban_sao
        bo_anh_ban_do_ban_sao(dc)                        # ảnh nền bản đồ tải lại được: mốc không chép thêm vài MB mỗi lần
    finally:
        dc.close()
    from .an_toan import dong_goi_file_sao_luu
    dong_goi_file_sao_luu(tam)                          # 1.0.55: nén zlib (không mã hóa - người dùng chọn)
    os.replace(tam, dich)
    so_ho, tong = tom_tat(con)
    moc = Moc(dich, luc, ly_do, ghi_chu, so_ho, tong, dau_file(file))
    du = dict(file=dich.name, luc=luc.isoformat(timespec='microseconds'), ly_do=ly_do, ghi_chu=ghi_chu, so_ho=so_ho, tong=tong,
              dau=moc.dau, goc=str(file))
    j = dich.with_suffix('.json')
    tam_j = j.with_name(j.name + '.tmp')
    tam_j.write_text(json.dumps(du, ensure_ascii=False, indent=1), encoding='utf-8')
    os.replace(tam_j, j)
    don_dep(file)
    return moc


GIU_TOI_THIEU = 10


def don_dep(file, bay_gio: datetime | None = None) -> int:
    """Bỏ mốc cũ theo lịch giữ (GIU_GIO giờ đủ, rồi mỗi ngày một mốc tới GIU_NGAY ngày; mốc tay luôn giữ; tối đa MOC_TOI_DA).
    Trả số mốc đã bỏ."""
    bay_gio = bay_gio or datetime.now()
    ds = ds_moc(file)
    giu, ngay_da_co = [], set()
    for m in ds:                                        # mới nhất trước
        tuoi = bay_gio - m.luc
        if m.ly_do == 'tay' or tuoi <= timedelta(hours=GIU_GIO):
            giu.append(m)
        elif tuoi <= timedelta(days=GIU_NGAY) and m.luc.date() not in ngay_da_co:
            giu.append(m)
            ngay_da_co.add(m.luc.date())
    for m in ds:                                        # 1.0.59: dự án nghỉ lâu: luôn còn vài mốc mới nhất dù đã quá hạn giữ
        if len(giu) >= GIU_TOI_THIEU:
            break
        if not any(m is x for x in giu):
            giu.append(m)
    tay = [m for m in giu if m.ly_do == 'tay']
    # 1.0.58: mốc ngày cũ không bị mốc trong ngày đẩy ra; mốc vừa chụp (mới nhất) luôn giữ
    ngay = [m for m in giu if m.ly_do != 'tay' and bay_gio - m.luc > timedelta(hours=GIU_GIO)]
    gan = [m for m in giu if m.ly_do != 'tay' and bay_gio - m.luc <= timedelta(hours=GIU_GIO)]
    khac = ngay + gan[:max(1, MOC_TOI_DA - len(tay) - len(ngay))]
    con_lai = {id(m) for m in tay + khac}
    bo = 0
    for m in ds:
        if id(m) not in con_lai:
            for f in (m.file, m.file.with_suffix('.json')):
                try:
                    f.unlink()
                except OSError:
                    pass
            bo += 1
    return bo


def kiem_tra_file(p) -> str:
    """'' nếu file SQLite p đọc được và PRAGMA quick_check = ok; còn lại: mô tả lỗi (1.0.97, kiểm toán dữ liệu 09/11/2026)."""
    try:
        c = sqlite3.connect(f'file:{Path(p).as_posix()}?mode=ro', uri=True)
        try:
            r = c.execute('PRAGMA quick_check').fetchone()
        finally:
            c.close()
    except sqlite3.Error as e:
        return str(e) or 'không đọc được'
    return '' if r and r[0] == 'ok' else str(r[0] if r else 'không rõ')


def khoi_phuc(file, moc: Moc) -> Moc | None:
    """Thay file dự án bằng bản của mốc. Nơi gọi PHẢI đóng mọi kết nối tới file trước. Chụp mốc "trước khi khôi phục" của file hiện
    tại (luôn chụp) để quay lại được. Trả mốc vừa chụp."""
    file = Path(file)
    truoc = None
    if file.exists():
        c = sqlite3.connect(str(file))
        try:
            truoc = chup_moc(c, file, 'truoc_khoi_phuc', f'về mốc {moc.luc:%d/%m/%Y %H:%M}', bat_buoc=True)
        finally:
            c.close()
    tam = file.with_name(file.name + '.khoi_phuc')
    from .an_toan import mo_goi_file_sao_luu_ra_bytes
    goc = mo_goi_file_sao_luu_ra_bytes(moc.file)        # 1.0.55: mốc nén -> giải nén; mốc cũ (SQLite thường) chép thẳng
    if goc is None:
        shutil.copyfile(moc.file, tam)
        with open(tam, 'rb+') as f:                     # 1.0.97: ghi xuống đĩa trước khi thay file (mất điện giữa chừng)
            os.fsync(f.fileno())
    else:
        with open(tam, 'wb') as f:
            f.write(goc)
            f.flush()
            os.fsync(f.fileno())
    loi = kiem_tra_file(tam)                           # 1.0.97: mốc hỏng KHÔNG được chép đè lên file dự án đang tốt
    if loi:
        try:
            tam.unlink()
        except OSError:
            pass
        raise sqlite3.DatabaseError(f'Mốc {moc.luc:%d/%m/%Y %H:%M} bị hỏng ({loi}): không khôi phục, file dự án giữ nguyên.')
    os.replace(tam, file)
    _ghi_vet_khoi_phuc(file, moc, truoc)
    return truoc


def _ghi_vet_khoi_phuc(file, moc: Moc, truoc) -> None:
    """1.0.58: file đã về bản cũ, nhật ký kiểm toán phía sau mốc mất: ghi một dòng để biết đã khôi phục (lỗi ghi không hủy khôi phục)."""
    from . import csdl, kiem_toan
    chu = f'Về mốc {moc.luc:%d/%m/%Y %H:%M}; bản trước khôi phục: {truoc.file.name if truoc else "không có"}'
    try:
        c = csdl.mo(file)
    except (sqlite3.Error, OSError):
        return
    try:
        kiem_toan.gan_ky(c)
        with csdl.giao_dich(c):
            csdl.ghi_nhat_ky(c, 'Khôi phục mốc thời gian', chu)
            kiem_toan.ghi_su_kien(c, 'Khôi phục mốc thời gian', chu)
    except sqlite3.Error:
        pass
    finally:
        c.close()


# ---------------------------------------------------------------- so sánh hai trạng thái
@dataclass
class KhacBiet:
    so_ho_truoc: int = 0
    so_ho_sau: int = 0
    tong_truoc: object = 0
    tong_sau: object = 0
    them: list = field(default_factory=list)            # [(mã, họ tên, tổng)]
    bo: list = field(default_factory=list)
    doi: list = field(default_factory=list)             # [(mã, họ tên, tổng trước, tổng sau)]
    doi_thong_tin: list = field(default_factory=list)   # [(mã, họ tên)] - đổi hồ sơ / thửa / tiến độ, tiền không đổi

    @property
    def khong_doi(self) -> bool:
        return not (self.them or self.bo or self.doi or self.doi_thong_tin)


def _trang_thai(con) -> dict:
    """{mã hộ: (họ tên, tổng Decimal, dấu vết nội dung)} của một dự án."""
    from .may_chu import dau_vet_ho
    from .nghiep_vu import ket_qua_ho
    from .tien import D
    ten = {r[0]: r[1] or '' for r in con.execute('SELECT ma_ho, ho_ten FROM ho')}
    kq = ket_qua_ho(con)
    dv = dau_vet_ho(con, list(ten))
    return {m: (ten[m], D(kq[m][0].tong) if m in kq else D(0), dv.get(m, '')) for m in ten}


def so_sanh(con_truoc, con_sau) -> KhacBiet:
    from .tien import D
    a, b = _trang_thai(con_truoc), _trang_thai(con_sau)
    k = KhacBiet(len(a), len(b), sum((x[1] for x in a.values()), D(0)), sum((x[1] for x in b.values()), D(0)))
    for m, (ten, tong, _dv) in b.items():
        if m not in a:
            k.them.append((m, ten, tong))
    for m, (ten, tong, dv) in a.items():
        if m not in b:
            k.bo.append((m, ten, tong))
        elif b[m][1] != tong:
            k.doi.append((m, b[m][0] or ten, tong, b[m][1]))
        elif b[m][2] != dv:
            k.doi_thong_tin.append((m, b[m][0] or ten))
    return k


def so_sanh_file(file_truoc, file_sau) -> KhacBiet:
    from . import csdl
    a, b = csdl.mo(file_truoc, chi_doc=True), csdl.mo(file_sau, chi_doc=True)
    try:
        return so_sanh(a, b)
    finally:
        a.close()
        b.close()


def so_sanh_moc(con_hien_tai, moc: Moc) -> KhacBiet:
    """Khác biệt từ mốc tới hiện tại (mốc = trước, dự án đang mở = sau)."""
    from . import csdl
    a = csdl.mo(moc.file, chi_doc=True)
    try:
        return so_sanh(a, con_hien_tai)
    finally:
        a.close()


def chu_khac_biet(k: KhacBiet, toi_da: int = 30) -> list:
    """Các dòng chữ mô tả khác biệt (hộp kết quả)."""
    from .tien import vn
    ds = [f'Số hộ: {k.so_ho_truoc} -> {k.so_ho_sau}', f'Tổng kinh phí: {vn(k.tong_truoc)} -> {vn(k.tong_sau)} đồng '
          f'({"+" if k.tong_sau >= k.tong_truoc else "-"}{vn(abs(k.tong_sau - k.tong_truoc))})']
    for tieu_de, nhom, ham in (('Hộ thêm mới', k.them, lambda x: f'{x[1]} (mã {x[0]}): {vn(x[2])}'),
                               ('Hộ bị xóa', k.bo, lambda x: f'{x[1]} (mã {x[0]}): {vn(x[2])}'),
                               ('Hộ đổi số tiền', k.doi, lambda x: f'{x[1]} (mã {x[0]}): {vn(x[2])} -> {vn(x[3])}'),
                               ('Hộ đổi hồ sơ / thửa / tiến độ (tiền không đổi)', k.doi_thong_tin, lambda x: f'{x[1]} (mã {x[0]})')):
        if nhom:
            ds.append(f'{tieu_de}: {len(nhom)} hộ')
            ds += ['  - ' + ham(x) for x in nhom[:toi_da]]
            if len(nhom) > toi_da:
                ds.append(f'  … và {len(nhom) - toi_da} hộ khác')
    if k.khong_doi:
        ds.append('Không có hộ nào thay đổi.')
    return ds


# ---------------------------------------------------------------- thử trước thao tác hàng loạt
@dataclass
class KetQuaThu:
    ket_qua: object                       # giá trị thao tác trả về trên bản thử
    khac: KhacBiet
    loi: Exception | None = None


def thu_truoc(con, ham) -> KetQuaThu:
    """Chạy ham(con_thu) trên BẢN SAO dự án (thư mục tạm, xóa sau), so sánh với hiện tại. Dự án thật không đổi. ham lỗi: KetQuaThu
    có loi (khác biệt rỗng)."""
    from . import csdl
    td = Path(tempfile.mkdtemp(prefix='pabt_thu_'))
    try:
        f = td / 'ban_thu.larc'
        dc = sqlite3.connect(str(f))
        try:
            con.backup(dc)
            dc.commit()
        finally:
            dc.close()
        c = csdl.mo(f)
        try:
            c._ho_nhan_viec = getattr(con, '_ho_nhan_viec', None)
            try:
                kq = ham(c)
            except Exception as e:                      # noqa: BLE001 - báo lại cho người dùng, không ghi gì
                return KetQuaThu(None, KhacBiet(), e)
            return KetQuaThu(kq, so_sanh(con, c))
        finally:
            c.close()
    finally:
        shutil.rmtree(td, ignore_errors=True)

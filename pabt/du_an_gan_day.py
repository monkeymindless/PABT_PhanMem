"""Danh sách dự án làm việc gần đây, dự án ghim, tổng kinh phí nhớ của màn hình chào (1.1.05: tách từ app.py - phần đọc / ghi
file ở <thư mục máy>, không Qt). app.py nhập lại đúng các tên cũ (app.doc_gan_day, app._tom_tat_pabt...)."""
from __future__ import annotations

import sqlite3
from pathlib import Path
from . import csdl, may_chu, nghiep_vu
from .tien import D, vn

GAN_DAY_TOI_DA = 30                # số dự án nhớ trong danh sách "Dự án làm việc gần đây" (26/10/2026: 8 -> 30, bảng giãn hết màn hình chào)


def _file_gan_day() -> Path:
    return may_chu.thu_muc_may() / 'du_an_gan_day.json'


def doc_gan_day() -> list:
    """Đường dẫn các dự án mở gần đây (mới nhất trước) - màn hình chào."""
    import json
    try:
        ds = json.loads(_file_gan_day().read_text(encoding='utf-8'))
        return [str(x) for x in ds if isinstance(x, str)]
    except (OSError, ValueError):
        return []


def _con_tren_dia(x) -> bool:
    """False chỉ khi CHẮC file đã mất: ổ đĩa / thư mục dùng chung còn truy cập được mà không có file. Ổ mạng / USB đang ngắt
    -> giữ lại trong danh sách (cắm lại là mở được)."""
    f = Path(x)
    try:
        return f.is_file() or not Path(f.anchor).exists()
    except OSError:
        return True


def ghi_gan_day(p) -> None:
    import json
    try:
        moi = str(Path(p).resolve())
        # bỏ file không còn trên đĩa (15/10/2026): trước đây file tạm đã xóa vẫn chiếm chỗ trong GAN_DAY_TOI_DA mục, đẩy dự án thật
        # ra khỏi danh sách -> bảng "Dự án làm việc gần đây" trống dù vừa mở dự án
        ds = [moi] + [x for x in doc_gan_day() if x.lower() != moi.lower() and _con_tren_dia(x)]
        f = _file_gan_day()
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(json.dumps(ds[:GAN_DAY_TOI_DA], ensure_ascii=False, indent=1), encoding='utf-8')
    except OSError:                                     # thư mục máy không ghi được: bỏ qua, không ảnh hưởng mở dự án
        pass


def bo_gan_day(p) -> list:
    """Xóa một đường dẫn khỏi danh sách dự án gần đây (file trên đĩa giữ nguyên)."""
    import json
    ds = [x for x in doc_gan_day() if x.lower() != str(Path(p)).lower()]
    try:
        f = _file_gan_day()
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(json.dumps(ds[:GAN_DAY_TOI_DA], ensure_ascii=False, indent=1), encoding='utf-8')
    except OSError:
        pass
    return ds


def _file_ghim() -> Path:
    return may_chu.thu_muc_may() / 'du_an_ghim.json'


def doc_ghim() -> list:
    """Đường dẫn dự án được ghim lên đầu lưới gần đây."""
    import json
    try:
        ds = json.loads(_file_ghim().read_text(encoding='utf-8'))
        return [str(x) for x in ds if isinstance(x, str)]
    except (OSError, ValueError):
        return []


def ghim_du_an(p, ghim: bool = True) -> list:
    """Ghim / bỏ ghim một file .pabt. Trả danh sách ghim mới."""
    import json
    moi = str(Path(p).resolve())
    ds = [x for x in doc_ghim() if x.lower() != moi.lower()]
    if ghim:
        ds.insert(0, moi)
    try:
        f = _file_ghim()
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(json.dumps(ds, ensure_ascii=False, indent=1), encoding='utf-8')
    except OSError:
        pass
    return ds


def _file_tong_du_an() -> Path:
    return may_chu.thu_muc_may() / 'tong_du_an.json'


def _doc_tong_nho() -> dict:
    import json
    try:
        d = json.loads(_file_tong_du_an().read_text(encoding='utf-8'))
        return d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


def ghi_tong_nho(p, so_ho: int, tong, chu_tim: str | None = None, hien: str | None = None) -> None:
    """Nhớ tổng kinh phí CHUẨN (cùng cách tính danh sách hộ: mọi mục kể cả thưởng, làm tròn như dự án) của file dự án theo thời
    điểm sửa + cỡ file - màn hình chào hiện đúng số mà không tính lại cả dự án (0.9.95). 16/10/2026 (máy yếu): nhớ cả chữ tìm và tên
    hiển thị - file không đổi thì màn hình chào KHÔNG mở file dự án nào (ổ mạng / Google Drive / HDD chậm). Lỗi ghi: bỏ qua."""
    import json
    try:
        st = Path(p).stat()
        d = _doc_tong_nho()
        k = str(Path(p).resolve()).lower()
        cu = d.get(k)
        if chu_tim is None and isinstance(cu, list) and len(cu) >= 6 and cu[:2] == [st.st_mtime_ns, st.st_size]:
            chu_tim, hien = cu[4], cu[5]                # dự án đang mở ghi lại tổng: giữ tên đã nhớ
        d[k] = [st.st_mtime_ns, st.st_size, int(so_ho), str(tong)] + ([chu_tim, hien] if chu_tim is not None else [])
        if len(d) > 60:                                 # chỉ giữ các file gần đây
            for k in list(d)[:len(d) - 60]:
                d.pop(k, None)
        f = _file_tong_du_an()
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(json.dumps(d, ensure_ascii=False), encoding='utf-8')
    except (OSError, ValueError):
        pass


def _tom_tat_pabt(p) -> tuple:
    """(số hộ, chuỗi tổng tiền, chữ để tìm: tên dự án + địa bàn, tên hiển thị) đọc file dự án chỉ xem; lỗi / khóa ->
    (None, None, '', tên file). Tổng = tổng kinh phí như danh sách hộ (0.9.95: trước đây cộng thô ct_dat / ct_khoan - thiếu thưởng
    bàn giao mặt bằng, không làm tròn, lệch số danh sách hộ). Tính một lần mỗi khi file đổi (ghi_tong_nho), lần sau đọc nhớ.
    Tên hiển thị: "<tên dự án> · <địa bàn> (<tên file>)" khi có tên dự án."""
    p = Path(p)
    try:                                                # file không đổi từ lần đọc trước: lấy ngay, không mở SQLite
        st = p.stat()
        nho = _doc_tong_nho().get(str(p.resolve()).lower())
        if isinstance(nho, list) and len(nho) >= 6 and nho[0] == st.st_mtime_ns and nho[1] == st.st_size:
            tong = D(nho[3])
            return int(nho[2]), (vn(tong) if tong else None), str(nho[4]), str(nho[5])
    except (OSError, ValueError, TypeError, ArithmeticError):
        pass
    try:
        con = csdl.mo(str(p), chi_doc=True)
        try:
            n = con.execute('SELECT COUNT(*) FROM ho').fetchone()[0]
            ten = dia_ban = ''
            try:
                r = con.execute('SELECT ten, cap_dia_ban, ten_dia_ban FROM du_an WHERE id = 1').fetchone()
                chu_tim = ' '.join(x for x in (r or ()) if x)
                if r is not None:
                    ten, dia_ban = str(r[0] or '').strip(), str(r[2] or '').strip()
            except sqlite3.Error:
                chu_tim = ''
            hien = (f'{ten}' + (f' · {dia_ban}' if dia_ban else '') + f' ({p.name})') if ten else p.name
            tong = None
            try:
                st = p.stat()
                nho = _doc_tong_nho().get(str(p.resolve()).lower())
                if nho and nho[0] == st.st_mtime_ns and nho[1] == st.st_size:
                    tong = D(nho[3])
            except (OSError, ValueError, IndexError, TypeError):
                pass
            if tong is None and n:
                try:
                    tong = sum((k.tong for k in nghiep_vu.tinh_tat_ca(con)), D('0'))
                except Exception:                       # file cũ / hỏng: không hiện tổng, vẫn liệt kê
                    tong = None
            if tong is not None or not n:
                ghi_tong_nho(p, n, tong if tong is not None else D('0'), chu_tim, hien)
            return n, (vn(tong) if tong else None), chu_tim, hien
        finally:
            con.close()
    except Exception:
        return None, None, '', p.name

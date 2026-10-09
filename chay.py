"""Chạy phần mềm PABT.

  python chay.py                                   mở cửa sổ phần mềm (cần PySide6)
  python chay.py nhap <file.xlsm> [<file.pabt>]   nhập file Excel -> file dự án + báo cáo đối chiếu (không cần PySide6)
         [--ten "Tên dự án"] [--danh-muc <dự án cũ.pabt>]
      File theo mẫu PABT (.xlsm có DB_HO...): nhập toàn bộ. File Excel bất kỳ (danh sách họ tên, địa chỉ, tờ, thửa,
      diện tích thu hồi, loại đất): tự nhận cột; file .pabt đã có thì XÓA TRẮNG hồ sơ cũ, giữ danh mục đơn giá;
      file .pabt mới thì lấy danh mục từ --danh-muc.
  python chay.py nhap-chi-tiet <file.xlsm> [<file.pabt>] [--trung bo_qua|thay|them]
      File Excel phương án chi tiết (mỗi sheet một hộ, như bản in IN_CHITIET): thêm các hộ vào file dự án (chưa có thì
      tạo mới với bộ đơn giá tích hợp) rồi đối chiếu tổng tiền với file. Hộ đã có (cùng CCCD / họ tên): mặc định bỏ qua.
  python chay.py doi-chieu <file.pabt>             tính lại và đối chiếu một file dự án đã nhập
  python chay.py tu-kiem <file_ket_qua.txt>         tự kiểm tra bản cài (giao diện, PDF, bộ đơn giá, mẫu in, bảng giá đất)
"""
from __future__ import annotations
import sys
from pathlib import Path

import nap_cap_nhat

nap_cap_nhat.nap()              # bản cập nhật .pabtcn đã cài thì thay mã gói pabt trước khi import

# nhap_excel / nhap_tho / doi_chieu (kéo theo openpyxl) chỉ nạp khi chạy lệnh dòng lệnh: mở cửa sổ không phải chờ
from pabt import csdl, khoa, lap_pa  # noqa: E402
from pabt.tien import vn  # noqa: E402

# tùy chọn hợp lệ của từng lệnh (gõ sai / thiếu giá trị thì báo lỗi, không đoán)
TUY_CHON = {'nhap': ('ten', 'danh-muc'), 'nhap-chi-tiet': ('trung',), 'doi-chieu': (), 'tu-kiem': ()}
CACH_TRUNG = ('bo_qua', 'thay', 'them')


class LoiDoiSo(ValueError):
    """Đối số dòng lệnh sai."""


def _in_ket_qua(kq, con, bao_cao: Path) -> None:
    from pabt import doi_chieu
    da = con.execute('SELECT ten, cap_dia_ban, ten_dia_ban, nguon_nhap FROM du_an WHERE id = 1').fetchone()
    ten, cap, dia_ban, nguon = (da['ten'], da['cap_dia_ban'], da['ten_dia_ban'], da['nguon_nhap']) if da else ('', '', '', '')
    doi_chieu.xuat_bao_cao(kq, bao_cao, ten, nguon, lap_pa.ra_soat_gia(con))
    co_pa = [h for h in kq.ho if h['tong'] > 0]
    print(f'Dự án: {(ten or "")[:90]}')
    print(f'Địa bàn: {cap} {dia_ban}   |   {len(kq.ho)} hộ, {len(co_pa)} hộ đã lập phương án')
    for h in co_pa:
        if h.get('sua'):
            tt = 'sửa trong phần mềm'
        elif h.get('lech'):
            tt = 'LỆCH'
        elif h.get('co_excel'):
            tt = 'khớp Excel'
        else:
            tt = ''
        print(f'  Hộ {h["ma_ho"]:>4} {(h["ho_ten"] or "")[:28]:<28} {vn(h["tong"]):>16} đ   {tt}')
    sua = f' (trừ {kq.so_ho_sua} hộ đã sửa trong phần mềm)' if kq.so_ho_sua else ''
    print('ĐỐI CHIẾU EXCEL: ' + ('KHỚP 100%' if kq.khop_het else f'LỆCH {kq.so_ho_lech} hộ, {len(kq.dong_lech)} dòng') + sua)
    if kq.canh_bao:
        print(f'{len(kq.canh_bao)} điểm cần xem lại:')
        for ma, _ten, ct in kq.canh_bao:
            print(f'  - Hộ {ma}: {ct}')
    print(f'Báo cáo: {bao_cao}')


def _tach(argv, hop_le=None):
    """['a', '--ten', 'X', 'b'] -> (['a', 'b'], {'ten': 'X'}); nhận cả dạng --ten=X.

    Tùy chọn thiếu giá trị (đứng cuối, hoặc giá trị lại bắt đầu bằng --) hay không có trong `hop_le` -> LoiDoiSo.
    Trước đây `nhap a.xlsx --ten --danh-muc cu.pabt` hiểu cu.pabt là file đích và XÓA TRẮNG hồ sơ của nó."""
    so, tc, i = [], {}, 0
    while i < len(argv):
        x = argv[i]
        if x.startswith('--'):
            ten, co_bang, gia_tri = x[2:].partition('=')
            if not co_bang:
                if i + 1 >= len(argv) or argv[i + 1].startswith('--'):
                    raise LoiDoiSo(f'tùy chọn --{ten} thiếu giá trị.')
                gia_tri = argv[i + 1]
                i += 1
            if hop_le is not None and ten not in hop_le:
                raise LoiDoiSo(f'tùy chọn --{ten} không dùng được ở lệnh này'
                               + (f' (chỉ có: {", ".join("--" + t for t in hop_le)}).' if hop_le else '.'))
            tc[ten] = gia_tri
        else:
            so.append(x)
        i += 1
    return so, tc


def _file_vao(ten: str) -> Path:
    """File đầu vào phải có thật (Path('') / thư mục / file thiếu -> LoiDoiSo)."""
    if not ten or not ten.strip():
        raise LoiDoiSo('chưa chỉ file đầu vào.')
    p = Path(ten)
    if not p.is_file():
        raise LoiDoiSo(f'không thấy file {p}.')
    return p


def _dang_bi_khoa(pabt: Path) -> bool:
    k = khoa.KhoaFile(pabt).nguoi_khac()
    if k:
        print(f'KHÔNG NHẬP ĐƯỢC: file {pabt} đang được sửa trên {khoa.mo_ta(k)}.')
    return bool(k)


def _doi_chieu_va_in(pabt: Path) -> None:
    from pabt import doi_chieu
    con = csdl.mo(pabt)
    try:
        _in_ket_qua(doi_chieu.doi_chieu(con), con, pabt.with_name(pabt.stem + '_DoiChieu.xlsx'))
    finally:
        con.close()


def tu_kiem(file_ra=None) -> int:
    """Kiểm tra các thành phần của bản đã đóng gói; ghi kết quả ra file (bản exe không có cửa sổ lệnh). 0 = đạt."""
    import os
    import tempfile
    import traceback
    kq = []

    def buoc(ten, ham):
        try:
            kq.append(f'DAT  {ten}: {ham() or ""}')
        except Exception as e:
            kq.append(f'LOI  {ten}: {e!r}')
            kq.append(traceback.format_exc())

    os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

    def giao_dien():
        from PySide6.QtWidgets import QApplication
        app = QApplication.instance() or QApplication([])
        from pabt.giao_dien import ap_dung
        ap_dung(app)
        from pabt import app as ud
        w = ud.CuaSoChinh()
        w.show()
        app.processEvents()
        n = len(w.lenh)
        w.close()
        return f'{n} lệnh'

    def pdf():
        from pabt import nhap_don_gia
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / 'a.pdf'
            nd = b'BT /F1 12 Tf 50 780 Td (TS1 Nha cap 4 m2 3.500.000) Tj ET'
            obj = [b'<< /Type /Catalog /Pages 2 0 R >>', b'<< /Type /Pages /Kids [3 0 R] /Count 1 >>',
                   b'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>',
                   b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>',
                   b'<< /Length ' + str(len(nd)).encode() + b' >>\nstream\n' + nd + b'\nendstream']
            out, off = b'%PDF-1.4\n', []
            for i, o in enumerate(obj, start=1):
                off.append(len(out))
                out += f'{i} 0 obj\n'.encode() + o + b'\nendobj\n'
            x = len(out)
            out += f'xref\n0 {len(obj) + 1}\n0000000000 65535 f \n'.encode() + b''.join(f'{o:010d} 00000 n \n'.encode() for o in off)
            out += f'trailer << /Size {len(obj) + 1} /Root 1 0 R >>\nstartxref\n{x}\n%%EOF'.encode()
            p.write_bytes(out)
            ds = nhap_don_gia.nhan_muc(nhap_don_gia.doc_bang(p))
            assert ds and ds[0].don_gia == 3500000, ds
            import pabt
            return 'pypdf (Qt5)' if pabt.QT5 else 'QtPdf (Qt6)'

    def bo_don_gia():
        from pabt import don_gia
        tt = don_gia.kiem_tra_bo(don_gia.file_goc())
        return f'phiên bản {tt["phien_ban"]}, {tt["dem"]["dm_taisan"]} tài sản'

    def mau_in():
        from pabt import in_an
        return str(in_an.thu_muc_mau())

    def gia_dat():
        from pabt import gia_dat_nq28
        return f'{len(gia_dat_nq28.tat_ca())} dòng'

    def csdl_moi():
        with tempfile.TemporaryDirectory() as td:
            con = csdl.tao_moi(Path(td) / 'a.pabt')
            v = con.execute('PRAGMA user_version').fetchone()[0]
            con.close()
        return f'CSDL v{v}'

    def phien_ban():
        import pabt
        import platform
        return f'{pabt.__version__}, Python {platform.python_version()}, ' + \
            ('Qt5' if pabt.QT5 else 'Qt6') + f' (bản cài gốc {nap_cap_nhat.BAN_GOC}' + \
            (f', đang dùng bản cập nhật {nap_cap_nhat.DANG_DUNG})' if nap_cap_nhat.DANG_DUNG else ')') + \
            (f' - {pabt.NHAN_THU_NGHIEM}' if getattr(pabt, 'BAN_THU_NGHIEM', False) else '')

    def https():
        from pabt import an_toan as at
        ctx = at.ngu_canh_tls()
        return f'kiểm tra chứng chỉ, {ctx.minimum_version.name}+'

    for ten, ham in (('Phiên bản', phien_ban), ('Giao diện', giao_dien), ('Đọc PDF', pdf), ('Bộ đơn giá', bo_don_gia), ('Mẫu in', mau_in),
                     ('Bảng giá đất NQ 28', gia_dat), ('Tạo file dự án', csdl_moi), ('HTTPS', https)):
        buoc(ten, ham)
    loi = sum(1 for x in kq if x.startswith('LOI'))
    kq.append(f'KET QUA: {"DAT" if not loi else f"{loi} LOI"}')
    noi_dung = '\n'.join(kq)
    if file_ra:
        Path(file_ra).write_text(noi_dung, encoding='utf-8')
    else:
        print(noi_dung)
    return 1 if loi else 0


def main(argv) -> int:
    if not argv or argv[0].lower().endswith(('.pabt', '.pabtcn')) or argv[0] in ('--menu-trai', '--menu-tren'):   # mở cửa sổ
        from pabt.app import main as mo_cua_so
        return mo_cua_so()
    lenh = argv[0]
    if lenh not in TUY_CHON:
        print(__doc__)
        return 2
    try:
        so, tc = _tach(argv[1:], TUY_CHON[lenh])
        if lenh == 'tu-kiem':
            return tu_kiem(so[0] if so else None)
        if not so:
            raise LoiDoiSo('chưa chỉ file.')
        if lenh == 'doi-chieu':
            # csdl.mo trên đường dẫn không có sẽ tạo file .pabt rỗng: kiểm tra trước
            _doi_chieu_va_in(_file_vao(so[0]))
            return 0
        xl = _file_vao(so[0])
        f_pabt = Path(so[1]) if len(so) >= 2 else xl.with_suffix('.pabt')
        if f_pabt.resolve() == xl.resolve():
            raise LoiDoiSo('file dự án trùng với file Excel đầu vào.')
        if lenh == 'nhap-chi-tiet' and tc.get('trung', 'bo_qua') not in CACH_TRUNG:
            raise LoiDoiSo(f'--trung chỉ nhận: {", ".join(CACH_TRUNG)}.')
        if len(so) > 2:
            raise LoiDoiSo(f'thừa đối số: {" ".join(so[2:])}')
    except LoiDoiSo as e:
        print(f'LỖI ĐỐI SỐ: {e}\n')
        print(__doc__)
        return 2
    if _dang_bi_khoa(f_pabt):
        return 1
    if lenh == 'nhap':
        from pabt import nhap_excel, nhap_tho
        tho = not nhap_tho.la_file_pabt(xl)
        try:
            bc = nhap_tho.nhap(xl, f_pabt, tc.get('ten', ''), tc.get('danh-muc')) if tho else nhap_excel.nhap(xl, f_pabt)
        except lap_pa.LoiNhap as e:
            print(f'KHÔNG NHẬP ĐƯỢC: {e}')
            return 1
        if bc.loi:
            print('KHÔNG NHẬP ĐƯỢC:')
            for x in bc.loi:
                print('  - ' + x)
            return 1
        print(f'Đã nhập {bc.so_ho} hộ, {bc.so_thua} thửa, {sum(bc.so_dong.values())} dòng phương án -> {f_pabt}')
        if tho:
            print('Nhận cột: ' + bc.nhan_cot)
        for x in bc.canh_bao:
            print('  ! ' + x)
        if not tho:
            _doi_chieu_va_in(f_pabt)
        return 0
    # nhap-chi-tiet
    from pabt import nhap_chi_tiet
    try:
        bc = nhap_chi_tiet.nhap(xl, f_pabt, tc.get('trung', 'bo_qua'))
    except lap_pa.LoiNhap as e:
        print(f'KHÔNG NHẬP ĐƯỢC: {e}')
        return 1
    print(nhap_chi_tiet.tom_tat(bc, toi_da=200) + f'\n-> {f_pabt}')
    _doi_chieu_va_in(f_pabt)
    return 0


if __name__ == '__main__':
    for luong in (sys.stdout, sys.stderr):          # cửa sổ lệnh Windows: in được tiếng Việt
        try:
            luong.reconfigure(encoding='utf-8')
        except (AttributeError, ValueError):
            pass
    kq = main(sys.argv[1:])
    nap_cap_nhat.khoi_dong_tot()
    sys.exit(kq)

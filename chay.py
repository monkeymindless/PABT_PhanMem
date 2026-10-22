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
  PABT.exe go-cai-dat [-Im]                         gỡ cài đặt (mục "Gỡ" của Windows) - không mở cửa sổ PowerShell
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
        d = in_an.thu_muc_mau()
        return 'mẫu chuẩn nhúng trong phần mềm' if d == in_an.THU_MUC_NHUNG else f'mẫu người dùng thay: {d}'

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
        from pabt import ban_quyen
        return f'{pabt.__version__}, Python {platform.python_version()}, ' + \
            ('Qt5' if pabt.QT5 else 'Qt6') + f' (bản cài gốc {nap_cap_nhat.BAN_GOC}' + \
            (f', đang dùng bản cập nhật {nap_cap_nhat.DANG_DUNG})' if nap_cap_nhat.DANG_DUNG else ')') + \
            (f' - {pabt.NHAN_THU_NGHIEM}' if getattr(pabt, 'BAN_THU_NGHIEM', False) else '') + \
            f' - {ban_quyen.mo_ta()}'

    def https():
        from pabt import an_toan as at
        ctx = at.ngu_canh_tls()
        return f'kiểm tra chứng chỉ, {ctx.minimum_version.name}+'

    def lap_in_thu():
        # máy mới cài (chưa có dữ liệu gì): chạy thử việc chính bằng dữ liệu GIẢ LẬP trong thư mục tạm, chỉ dùng thành phần đóng
        # gói kèm (bộ đơn giá, mẫu in, mẫu văn bản trình) - không cần Excel / Word (chỉ ghi file .xlsx / .docx)
        from PySide6.QtWidgets import QApplication
        QApplication.instance() or QApplication([])                 # in_an đo chữ bằng Qt
        import openpyxl
        from pabt import du_an_moi, du_toan, in_an, nhap_tho, van_ban_trinh
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            dong = [dict(ho_ten=f'Nguyễn Văn Thử {i}', dia_chi='Ấp 1', so_to='10', so_thua=str(100 + i), loai_dat=l,
                         dt_thu_hoi='120', vi_tri='1') for i, l in enumerate(('ONT', 'CLN', 'LUC'))]
            gia = [dict(loai_dat=l, vi_tri='1', gia=g) for l, g in (('ONT', '3000000'), ('CLN', '250000'), ('LUC', '200000'))]
            bc = du_an_moi.tao_du_an(td / 'thu.pabt', dict(ten='Dự án thử', cap_dia_ban='Xã', ten_dia_ban='Thử', nam='2026'),
                                     dong, gia)
            con = csdl.mo(td / 'thu.pabt')
            try:
                ds = [r[0] for r in con.execute('SELECT ma_ho FROM ho ORDER BY thu_tu')]
                kq = van_ban_trinh.xuat_bo_ho_so(con, ds, td / 'ho_so', to_trinh=True)
                if kq['loi']:
                    raise RuntimeError(f'xuất hồ sơ lỗi: {kq["loi"][:2]}')
                # phương án chi tiết xuất bản Word (22/10/2026); bản Excel mẫu IN_CHITIET còn dùng dựng PDF dự phòng khi thiếu Word
                kq['excel'].append(in_an.lap_chi_tiet(con, ds[0], td / 'du_phong.xlsx'))
                du_toan.xuat_khai_toan(du_toan.tu_du_an(con), td / 'khai_toan.xlsx')
            finally:
                con.close()
            wb = openpyxl.Workbook()
            wb.active.append(['STT', 'Họ và tên', 'Địa chỉ', 'Tờ bản đồ', 'Thửa đất', 'Loại đất', 'Diện tích thu hồi'])
            wb.active.append([1, 'Trần Thị Thử', 'Ấp 2', 5, 12, 'ONT', 80])
            wb.save(td / 'tho.xlsx')
            nh = nhap_tho.nhap(td / 'tho.xlsx', td / 'nhap.pabt', 'Nhập thử')
            so_ho_nhap = getattr(nh, 'so_ho', None)
        return (f'dự án mới {bc["so_ho"]} hộ, {bc["so_ho_co_pa"]} hộ có phương án; {len(kq["excel"])} file Excel + '
                f'{len(kq["word"])} file Word (chi tiết, bảng tổng hợp, tờ trình); khái toán; nhập Excel'
                + (f' {so_ho_nhap} hộ' if so_ho_nhap is not None else ''))

    def nhom_5_6():
        # Nhóm 5 - 6 (Mục IV QĐ 18/2026): cơ cấu kinh phí, mốc thời hạn, sổ nhật ký vận động + cưỡng chế, báo cáo tiến độ GPMB, báo cáo
        # tiếp thu ý kiến (Word) - dữ liệu GIẢ LẬP; bản đóng gói thiếu module nào của nhóm này thì báo ở đây
        from datetime import date, timedelta
        from PySide6.QtWidgets import QApplication
        QApplication.instance() or QApplication([])
        from pabt import bao_cao_gpmb, bao_cao_y_kien, du_an_moi, kinh_phi_du_an, theo_doi, thoi_han, van_dong
        import pabt.man_hinh_bao_cao                                # noqa: F401 - trang Báo cáo tiến độ GPMB có trong bản đóng gói
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            dong = [dict(ho_ten=f'Trần Văn Thử {i}', dia_chi='Ấp 1', so_to='10', so_thua=str(100 + i), loai_dat=l,
                         dt_thu_hoi='120', vi_tri='1') for i, l in enumerate(('ONT', 'CLN', 'LUC'))]
            gia = [dict(loai_dat=l, vi_tri='1', gia=g) for l, g in (('ONT', '3000000'), ('CLN', '250000'), ('LUC', '200000'))]
            du_an_moi.tao_du_an(td / 'n56.pabt', dict(ten='Dự án thử', cap_dia_ban='Xã', ten_dia_ban='Thử', nam='2026'), dong, gia)
            con = csdl.mo(td / 'n56.pabt')
            try:
                ds = [r[0] for r in con.execute('SELECT ma_ho FROM ho ORDER BY thu_tu')]
                q = theo_doi.luu_qd(con, None, '1/QĐ-UBND', '01/09/2026', 'Phê duyệt thử')
                theo_doi.them_ho_theo_pa(con, q, ds)
                nay = date.today()
                thoi_han.dat_ngay_thong_bao(con, (nay - timedelta(days=130)).strftime('%d/%m/%Y'))
                van_dong.ghi_buoi(con, ds[0], 'tien', (nay - timedelta(days=15)).strftime('%d/%m/%Y'), 'Họp tổ', 'Tổ vận động')
                cc = kinh_phi_du_an.co_cau(con)
                tq = bao_cao_gpmb.tong_quan(con)
                ds_cc = van_dong.ds_cuong_che(con)
                loai = [d['loai'] for d in cc['dong']]          # 5 nhóm + cộng + kinh phí + 2 dòng phân bổ 85/15 (1.0.04) + tổng
                assert cc['tong'] > 0 and loai.count('nhom') == 5 and loai.count('phan_bo') == 2 and loai[-1] == 'tong', loai
                assert tq['so_ho_phe_duyet'] == 3 and tq['so_ho_cuong_che'] == 1 and len(ds_cc) == 1, (tq['so_ho_cuong_che'], ds_cc)
                assert all(m['du'] for m in thoi_han.moc_thu_hoi_tat_ca(con).values()), 'mốc thu hồi 130 ngày phải đủ'
                van_dong.xuat_ds_cuong_che(con, td / 'cuong_che.xlsx')
                bao_cao_gpmb.xuat_excel(con, td / 'bao_cao.xlsx')
                bao_cao_y_kien.ghi_docx(con, ds, td / 'tiep_thu.docx')
            finally:
                con.close()
        return 'cơ cấu kinh phí, mốc thời hạn, 1 hộ đủ điều kiện cưỡng chế, báo cáo tiến độ, báo cáo tiếp thu ý kiến'

    def ho_so_dia_phuong():
        from pabt import dia_phuong, goi_mau
        hs = dia_phuong.doc(lam_moi=True)                   # file đóng kèm hỏng -> LoiHoSo
        with tempfile.TemporaryDirectory() as td:
            ds = goi_mau.tao_goi(Path(td) / 'thu.pabtcfg', mo_ta='tu-kiem')
            goi_mau.doc_goi(ds['file'])                     # đọc lại + kiểm tra (không cài)
        loi = dia_phuong.loi()
        return f'{hs["ten_ho_so"]}' + (f' - FILE MÁY SAI, dùng mặc định: {loi[0][:120]}' if loi else '') + \
            f'; gói mẫu {len(ds["tep"])} file'

    def ban_ve_cad():
        from pabt import ban_do_cad, dxf_thuan          # đọc DXF bằng Python thuần (bản cài không còn ezdxf / numpy)
        with tempfile.TemporaryDirectory() as td:
            f = dxf_thuan.viet(Path(td) / 'To_3.dxf', [('RANH THUA', [(0, 0), (20, 0), (20, 10), (0, 10)]),
                                                         ('RANH THU HOI', [(10, -5), (30, -5), (30, 20), (10, 20)])],
                               [('NHAN', '7', 5, 5)])
            kq = ban_do_cad.phan_tich(f, 'RANH THUA', 'RANH THU HOI')
        t = kq.thua[0]
        assert (t.so_to, t.so_thua, float(t.dt_hinh), float(t.dt_trong_ranh)) == ('3', '7', 200.0, 100.0), (t.so_to, t.so_thua, t.dt_hinh)
        return 'đọc DXF (Python thuần): thửa 7 tờ 3, DT 200 m², trong ranh 100 m²'

    def nhan_dang_chu():
        # Tesseract OCR đóng kèm (thư mục tesseract cạnh PABT.exe) chạy được + có tiếng Việt. Windows 32-bit không chạy được bản
        # 64-bit: không coi là lỗi cài (PDF có chữ / Word / Excel vẫn đọc; bản scan thì dán chữ)
        from pabt import ocr
        ly_do = ocr.san_sang()
        if ly_do:
            if not ocr.windows_64bit():
                return 'Windows 32-bit: không đọc được bản scan (dán chữ thay thế)'
            raise RuntimeError(ly_do)
        tess = ocr.tim_tesseract()
        return f'Tesseract ({tess.parent.name}\\{tess.name}), ngôn ngữ: {", ".join(ocr.ngon_ngu(tess))}'

    def huong_dan():
        from pabt import app as ud
        f = ud.file_huong_dan()
        if f is None:
            raise FileNotFoundError('thiếu HUONG_DAN.md (Trợ giúp → Hướng dẫn sử dụng)')
        return f'{f.name}, {f.stat().st_size // 1024} KB'

    for ten, ham in (('Phiên bản', phien_ban), ('Giao diện', giao_dien), ('Đọc PDF', pdf), ('Bộ đơn giá', bo_don_gia), ('Mẫu in', mau_in),
                     ('Hướng dẫn sử dụng', huong_dan), ('Hồ sơ địa phương, gói mẫu in', ho_so_dia_phuong),
                     ('Bản vẽ CAD (.dxf)', ban_ve_cad), ('Nhận dạng chữ bản scan', nhan_dang_chu),
                     ('Bảng giá đất NQ 28', gia_dat), ('Tạo file dự án', csdl_moi), ('HTTPS', https),
                     ('Lập và in thử (dữ liệu giả lập)', lap_in_thu), ('Nhóm 5 - 6: kinh phí, vận động, báo cáo tiến độ', nhom_5_6)):
        buoc(ten, ham)
    loi = sum(1 for x in kq if x.startswith('LOI'))
    kq.append(f'KET QUA: {"DAT" if not loi else f"{loi} LOI"}')
    noi_dung = '\n'.join(kq)
    if file_ra:
        Path(file_ra).write_text(noi_dung, encoding='utf-8')
    else:
        print(noi_dung)
    return 1 if loi else 0


def go_cai_dat(im: bool = False) -> int:
    """"Gỡ cài đặt" của Windows (UninstallString = PABT.exe go-cai-dat): chạy go_cai_dat.ps1 cạnh PABT.exe bằng PowerShell
    KHÔNG có cửa sổ console (CREATE_NO_WINDOW) rồi thoát ngay. Windows chạy thẳng powershell.exe thì Windows 11 (terminal mặc
    định Windows Terminal) mở một cửa sổ PowerShell trống suốt lúc gỡ: -WindowStyle Hidden không ẩn được (người dùng 11/10/2026).
    Thoát ngay: go_cai_dat.ps1 xóa cả thư mục chứa PABT.exe."""
    import os
    import subprocess
    goc = Path(sys.executable if getattr(sys, 'frozen', False) else __file__).resolve().parent
    ps1 = goc / 'go_cai_dat.ps1'
    if not ps1.exists():
        return 1
    ps = Path(os.environ.get('SystemRoot', r'C:\Windows')) / 'System32' / 'WindowsPowerShell' / 'v1.0' / 'powershell.exe'
    q = lambda p: str(p).replace("'", "''")                                      # noqa: E731 - chuỗi '…' của PowerShell
    lenh = f"& ([scriptblock]::Create([IO.File]::ReadAllText('{q(ps1)}', [Text.Encoding]::UTF8))) -Dich '{q(goc)}'"
    subprocess.Popen([str(ps) if ps.exists() else 'powershell.exe', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-STA',
                      '-WindowStyle', 'Hidden', '-Command', lenh + (' -Im' if im else '')],
                     cwd=os.environ.get('TEMP') or None, creationflags=subprocess.CREATE_NO_WINDOW, close_fds=True)
    return 0


def main(argv) -> int:
    if not argv or argv[0].lower().endswith(('.pabt', '.larc', '.larcud', '.pabtcn', '.pabtcfg')) or argv[0] in ('--menu-trai', '--menu-tren'):
        from pabt.app import main as mo_cua_so
        return mo_cua_so()
    lenh = argv[0]
    if lenh == 'go-cai-dat':
        return go_cai_dat('-Im' in argv[1:])
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
        f_pabt = Path(so[1]) if len(so) >= 2 else xl.with_suffix(csdl.DUOI_DU_AN)
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

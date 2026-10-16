r"""Phân tích một phiên bản PABT (chạy MỖI LẦN sửa phiên bản), có thể so với bản trước - ví dụ gói cập nhật đã phát hành:

  .venv\Scripts\python phan_tich_phien_ban.py [--so-sanh bo_cai\LARC_CapNhat_0.9.94.pabtcn | <thư mục mã>] [--so-ho 3000]
                                              [--du-an <file .pabt thật, chỉ đọc - chạy trên bản sao>] [--lan 3]
  Hoặc bấm đúp PHAN_TICH_PHIEN_BAN.bat (tự so với gói .pabtcn mới nhất trong bo_cai\ khác phiên bản mã nguồn).

Mỗi phiên bản chạy trong tiến trình riêng (gói .pabtcn: kiểm tra mã SHA-256, giải nén ra thư mục tạm), cùng một kịch bản:
  - TỐC ĐỘ: nạp mã lúc mở phần mềm, khởi động tới cửa sổ, mở dự án thật / dự án giả lập N hộ, mở cửa sổ lập phương án, lưu 1
    hộ + tải lại danh sách, đối chiếu, bảng tổng hợp, đóng dự án / cửa sổ, lệnh dòng lệnh doi-chieu; thư viện nặng (openpyxl)
    có bị nạp lúc mở hay không. Mỗi phép đo lấy trung vị --lan lần.
  - PHÂN TÍCH TĨNH: số dòng / module, import trong hàm (nạp khi dùng), mã lặp lại (bỏ dấu, đọc số, thư mục máy, đọc ngày...),
    `except Exception`, gọi thẳng QMessageBox, file lớn nhất, các file khác nhau giữa hai bản.
Kết quả: ket_qua_kiem_tra\PhanTich_<phiên bản>_<ngày giờ>.md. Chỉ dùng thư viện chuẩn (đo bằng .venv có PySide6).
Không sửa file dữ liệu nào: dự án thật chỉ được chép ra thư mục tạm.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import statistics
import subprocess
import sys
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path

GOC = Path(__file__).resolve().parent
PY = GOC / '.venv' / 'Scripts' / 'python.exe'

# kịch bản đo chạy BÊN TRONG tiến trình của từng phiên bản (sys.path[0] = thư mục mã của phiên bản đó)
_DO = r'''
import json, os, shutil, statistics, sys, tempfile, time
goc, du_an_that, so_ho, lan = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4])
sys.path.insert(0, goc)
td = tempfile.mkdtemp(prefix='pabt_do_')
os.environ['QT_QPA_PLATFORM'] = 'offscreen'
os.environ['PABT_THU_MUC_MAY'] = os.path.join(td, 'may')
kq = {}
t0 = time.perf_counter()
from PySide6.QtWidgets import QApplication
import pabt
from pabt import app as ud
kq['nap_ma'] = (time.perf_counter() - t0) * 1000
kq['openpyxl_luc_khoi_dong'] = 'openpyxl' in sys.modules
qa = QApplication([])
from pabt.giao_dien import ap_dung
ap_dung(qa)
w = ud.CuaSoChinh(menu_trai=True)
w.show(); qa.processEvents()
kq['khoi_dong'] = (time.perf_counter() - t0) * 1000
kq['phien_ban'] = pabt.__version__
from pabt.lap_pa import BoSoan

def do(ten, ham, n=1):
    ds = []
    for _ in range(n):
        t = time.perf_counter(); ham(); qa.processEvents(); ds.append((time.perf_counter() - t) * 1000)
    kq[ten] = statistics.median(ds)

def mo(p):
    w.mo(str(p), chi_doc=False)

if du_an_that and os.path.exists(du_an_that):
    p = os.path.join(td, 'that.pabt'); shutil.copy2(du_an_that, p)
    do('mo_du_an_that', lambda: mo(p))
    kq['openpyxl_sau_mo_du_an'] = 'openpyxl' in sys.modules
    def lap_pa():
        cs = w.mo_lap_pa(cho=False); cs.show(); qa.processEvents(); cs.close()
    do('cua_so_lap_pa_lan_dau', lap_pa)
    do('cua_so_lap_pa_lan_sau', lap_pa, n=7)        # thao tác ~0,1 s: đo một lần lệch tới ±20% - lấy trung vị nhiều lần
    ds = []
    for _ in range(7):                              # đóng dự án ~15 ms: đo nhiều lần (mở lại không tính giờ)
        t = time.perf_counter(); w.dong_du_an(); qa.processEvents(); ds.append((time.perf_counter() - t) * 1000)
        mo(p)
    kq['dong_du_an'] = statistics.median(ds)
    w.dong_du_an()
from pabt import doi_chieu, du_an_moi, in_an      # nạp SAU phần dự án thật: không làm sai cờ "openpyxl nạp khi mở dự án"
# dự án giả lập lớn (tạo bằng chính phiên bản đang đo)
dong = []
for i in range(so_ho):
    for j in range(1 + i % 3):
        dong.append(dict(ho_ten=f'Hộ thử {i}', dia_chi='Ấp 1', so_to=str(10 + i), so_thua=str(100 + i * 3 + j),
                         loai_dat=('ONT', 'CLN', 'LUC')[(i + j) % 3], dt_thu_hoi=str(50 + 10 * i + j), vi_tri='1', nhan_khau='4'))
gia = [dict(loai_dat=l, vi_tri='1', gia=g) for l, g in (('ONT', '3000000'), ('CLN', '250000'), ('LUC', '200000'))]
plon = os.path.join(td, 'lon.pabt')
do('tao_du_an_moi', lambda: du_an_moi.tao_du_an(plon, dict(ten='Thử', cap_dia_ban='Xã', ten_dia_ban='Bàu Hàm', nam='2026'), dong, gia))
do('mo_du_an_lon', lambda: mo(plon))
dem = [0]
def luu():
    dem[0] += 1
    bo = BoSoan(w.con, 10 + dem[0], w.dm)
    bo.sua_dat(0, 'dien_tich', str(20 + dem[0]))
    t = time.perf_counter(); bo.luu(); kq.setdefault('_luu', []).append((time.perf_counter() - t) * 1000)
    t = time.perf_counter(); w.tai_lai(); qa.processEvents(); kq.setdefault('_tai_lai', []).append((time.perf_counter() - t) * 1000)
for _ in range(lan):
    luu()
kq['luu_1_ho'] = statistics.median(kq.pop('_luu'))
kq['tai_lai_sau_luu'] = statistics.median(kq.pop('_tai_lai'))
do('doi_chieu_ca_du_an', lambda: doi_chieu.doi_chieu(w.con), lan)
do('bang_tong_hop_xlsx', lambda: in_an.lap_bang_tong_hop(w.con, os.path.join(td, 'bth.xlsx')))
do('dong_du_an_lon', lambda: w.dong_du_an())
t = time.perf_counter(); w.close(); qa.processEvents(); kq['dong_cua_so'] = (time.perf_counter() - t) * 1000
print('KQ_JSON' + json.dumps(kq))
shutil.rmtree(td, ignore_errors=True)
'''

TEN_DO = [('phien_ban', 'Phiên bản'), ('nap_ma', 'Nạp mã lúc mở phần mềm'), ('khoi_dong', 'Khởi động tới cửa sổ trống'),
          ('openpyxl_luc_khoi_dong', 'openpyxl (0,2 s) nạp lúc khởi động'), ('mo_du_an_that', 'Mở dự án thật'),
          ('openpyxl_sau_mo_du_an', 'openpyxl nạp khi mở dự án'), ('cua_so_lap_pa_lan_dau', 'Cửa sổ lập PA - lần đầu'),
          ('cua_so_lap_pa_lan_sau', 'Cửa sổ lập PA - lần sau'), ('dong_du_an', 'Đóng dự án thật'),
          ('tao_du_an_moi', 'Dự án mới N hộ (tạo + tự lập PA)'), ('mo_du_an_lon', 'Mở dự án N hộ'), ('luu_1_ho', 'Lưu 1 hộ'),
          ('tai_lai_sau_luu', 'Tải lại danh sách sau khi lưu 1 hộ'), ('doi_chieu_ca_du_an', 'Đối chiếu cả dự án N hộ'),
          ('bang_tong_hop_xlsx', 'Bảng tổng hợp N hộ (xlsx)'), ('dong_du_an_lon', 'Đóng dự án N hộ'),
          ('dong_cua_so', 'Đóng cửa sổ chính'), ('cli_doi_chieu', 'Lệnh dòng lệnh doi-chieu (dự án thật)'),
          ('cli_python_rong', 'Khởi động Python rỗng (mốc so sánh)')]

# mẫu mã lặp lại / dấu hiệu cần gom (đếm trên mã của mỗi phiên bản)
MAU_LAP = [('Bỏ dấu tiếng Việt (normalize NFD)', r"normalize\('NFD'"), ('Thư mục máy (PABT_THU_MUC_MAY)', r'PABT_THU_MUC_MAY'),
           ('Đọc số kiểu VN bằng regex riêng', r'\\d\{1,3\}\(\\\.\\d\{3\}\)\+'), ('Đọc ngày strptime', r'strptime\('),
           ('Tách loại đất ghép (+)', r"replace\(',', '\+'\)\.split\('\+'\)"), ('platform.node()', r'platform\.node\(\)'),
           ('except Exception', r'except Exception'), ('Gọi thẳng QMessageBox', r'QMessageBox\.(critical|warning|information|question)\('),
           ('import trong thân hàm', r'^\s{4,}(from \.|from pabt|import )')]


def tra(goc: Path, so_sanh: str, tam: Path) -> Path:
    """Thư mục mã của phiên bản so sánh: thư mục có pabt/, hoặc gói .pabtcn (kiểm tra mã SHA-256, giải nén)."""
    p = Path(so_sanh)
    if p.is_dir():
        return p
    sys.path.insert(0, str(goc))
    from pabt import cap_nhat
    m = cap_nhat.doc_goi(p)
    ra = tam / f'goi_{m["phien_ban"]}'
    with zipfile.ZipFile(p) as z:
        z.extractall(ra)
    for f in ('chay.py', 'nap_cap_nhat.py'):                       # gói chỉ có pabt/: lệnh dòng lệnh dùng chay.py hiện tại
        shutil.copy2(goc / f, ra / f)
    shutil.copytree(goc / 'mau_in', ra / 'mau_in')                 # mẫu in nằm ở bản cài, không có trong gói cập nhật
    return ra


def do_toc_do(thu_muc: Path, du_an: str, so_ho: int, lan: int) -> dict:
    env = dict(os.environ, PYTHONIOENCODING='utf-8', QT_QPA_PLATFORM='offscreen')
    with tempfile.TemporaryDirectory() as td:
        kich_ban = Path(td) / 'do.py'
        kich_ban.write_text(_DO, encoding='utf-8')
        r = subprocess.run([str(PY), '-W', 'ignore', str(kich_ban), str(thu_muc), du_an or '', str(so_ho), str(lan)],
                           capture_output=True, env=env, timeout=1800, cwd=td)
    ra = r.stdout.decode('utf-8', 'replace')
    m = re.search(r'KQ_JSON(\{.*\})', ra)
    if not m:
        raise RuntimeError(f'Không đo được {thu_muc}:\n{ra[-1500:]}\n{r.stderr.decode("utf-8", "replace")[-2500:]}')
    kq = json.loads(m.group(1))
    # lệnh dòng lệnh: tiến trình mới mỗi lần (thời gian người dùng thấy, gồm cả khởi động Python)
    if du_an and (thu_muc / 'chay.py').exists():
        ds = []
        for _ in range(lan):
            with tempfile.TemporaryDirectory() as td:
                p = Path(td) / 'x.pabt'
                shutil.copy2(du_an, p)
                t = datetime.now()
                subprocess.run([str(PY), '-W', 'ignore', str(thu_muc / 'chay.py'), 'doi-chieu', str(p)], capture_output=True,
                               env=env, timeout=600, cwd=str(thu_muc))
                ds.append((datetime.now() - t).total_seconds() * 1000)
        kq['cli_doi_chieu'] = statistics.median(ds)
    t = datetime.now()
    subprocess.run([str(PY), '-c', 'pass'], capture_output=True)
    kq['cli_python_rong'] = (datetime.now() - t).total_seconds() * 1000
    return kq


def phan_tich_tinh(thu_muc: Path) -> dict:
    ds = sorted((thu_muc / 'pabt').glob('*.py'))
    dong = {f.name: f.read_text(encoding='utf-8').count('\n') for f in ds}
    chu = {f.name: f.read_text(encoding='utf-8') for f in ds}
    lap = {ten: sum(len(re.findall(mau, x, re.M)) for x in chu.values()) for ten, mau in MAU_LAP}
    # module nặng nạp ngay khi nạp cửa sổ chính (import đầu file app.py)
    dau_app = re.findall(r'^from \. import (.+)$', chu.get('app.py', ''), re.M)
    return dict(so_module=len(ds), so_dong=sum(dong.values()), lon_nhat=sorted(dong.items(), key=lambda x: -x[1])[:5], lap=lap,
                import_dau_app=', '.join(dau_app), so_test=len(list((thu_muc / 'tests').glob('test_*.py')))
                if (thu_muc / 'tests').exists() else None)


def khac_nhau(a: Path, b: Path) -> list:
    """[(file, mô tả)] khác giữa hai thư mục mã pabt/."""
    import difflib
    kq = []
    ten = sorted({f.name for f in (a / 'pabt').iterdir() if f.is_file()} | {f.name for f in (b / 'pabt').iterdir() if f.is_file()})
    for t in ten:
        fa, fb = a / 'pabt' / t, b / 'pabt' / t
        if t.endswith(('.pyc', '.ico')) or '__pycache__' in t:     # .ico chỉ có trong bản cài, không có trong gói cập nhật
            continue
        if not fa.exists():
            kq.append((t, 'MỚI'))
        elif not fb.exists():
            kq.append((t, 'XÓA'))
        elif hashlib.sha256(fa.read_bytes()).digest() != hashlib.sha256(fb.read_bytes()).digest():
            if t.endswith(('.py', '.sql')):
                d = list(difflib.unified_diff(fa.read_text(encoding='utf-8').splitlines(), fb.read_text(encoding='utf-8').splitlines(),
                                              lineterm='', n=0))
                kq.append((t, f'+{sum(1 for x in d if x[:1] == "+" and x[:3] != "+++")} / '
                              f'-{sum(1 for x in d if x[:1] == "-" and x[:3] != "---")} dòng'))
            else:
                kq.append((t, 'khác nội dung'))
    return kq


def _o(v) -> str:
    if isinstance(v, bool):
        return 'CÓ' if v else 'không'
    if isinstance(v, (int, float)):
        return f'{v:,.0f} ms'.replace(',', '.')
    return str(v)


def bao_cao(kq_moi: dict, kq_cu: dict | None, tinh_moi: dict, tinh_cu: dict | None, doi: list | None, so_ho: int) -> str:
    cu = kq_cu is not None
    t = [f'# Phân tích phiên bản PABT {kq_moi.get("phien_ban")}' + (f' so với {kq_cu.get("phien_ban")}' if cu else ''),
         f'Ngày {datetime.now():%d/%m/%Y %H:%M}, máy {os.environ.get("COMPUTERNAME", "")}; dự án giả lập N = {so_ho} hộ; '
         'đo ở chế độ không hiển thị (offscreen), trung vị nhiều lần.', '', '## 1. Tốc độ (thời gian mở / tắt, chạy lệnh)', '',
         '| Thao tác | ' + (f'{kq_cu.get("phien_ban")} | ' if cu else '') + f'{kq_moi.get("phien_ban")} |' + (' Thay đổi |' if cu else ''),
         '|---|' + ('---|' if cu else '') + '---|' + ('---|' if cu else '')]
    for k, ten in TEN_DO[1:]:
        if k not in kq_moi and not (cu and k in kq_cu):
            continue
        m, c = kq_moi.get(k), (kq_cu or {}).get(k)
        doi_ = ''
        if cu and isinstance(m, (int, float)) and isinstance(c, (int, float)) and not isinstance(m, bool) and c:
            doi_ = f'{(m - c) / c * 100:+.0f}%' + (' (nhanh hơn)' if m < c * 0.9 else ' (CHẬM HƠN)' if m > c * 1.1 else '')
        t.append(f'| {ten.replace("N hộ", f"{so_ho} hộ")} | ' + (f'{_o(c)} | ' if cu else '') + f'{_o(m)} |' + (f' {doi_} |' if cu else ''))
    t += ['', '## 2. Điểm nghẽn còn lại (thao tác chậm nhất của bản mới)', '']
    cham = sorted(((v, k) for k, v in kq_moi.items() if isinstance(v, float) and not k.startswith('cli_python')), reverse=True)[:5]
    t += [f'- {dict(TEN_DO).get(k, k).replace("N hộ", f"{so_ho} hộ")}: {_o(v)}' for v, k in cham]
    t += ['', '## 3. Cách gọi gói / nạp module', '', f'- Module nạp ngay khi nạp cửa sổ chính (import đầu `app.py`): '
          f'`{tinh_moi["import_dau_app"]}`' + (f' (bản cũ: `{tinh_cu["import_dau_app"]}`)' if tinh_cu else ''),
          f'- openpyxl nạp lúc khởi động: {_o(kq_moi.get("openpyxl_luc_khoi_dong"))}; khi mở dự án: '
          f'{_o(kq_moi.get("openpyxl_sau_mo_du_an", "-"))}' + (f' (bản cũ: {_o(kq_cu.get("openpyxl_luc_khoi_dong"))} / '
                                                              f'{_o(kq_cu.get("openpyxl_sau_mo_du_an", "-"))})' if cu else ''),
          '', '## 4. Mã lặp lại, dấu hiệu cần gom (số chỗ)', '', '| Mẫu | ' + ('Bản cũ | ' if tinh_cu else '') + 'Bản mới |',
          '|---|' + ('---|' if tinh_cu else '') + '---|']
    for ten, _ in MAU_LAP:
        t.append(f'| {ten} | ' + (f'{tinh_cu["lap"][ten]} | ' if tinh_cu else '') + f'{tinh_moi["lap"][ten]} |')
    t += ['', '## 5. Quy mô mã', '', f'- {tinh_moi["so_module"]} module, {tinh_moi["so_dong"]:,} dòng'.replace(',', '.') +
          (f' (bản cũ {tinh_cu["so_module"]} module, {tinh_cu["so_dong"]:,} dòng)'.replace(',', '.') if tinh_cu else ''),
          '- File lớn nhất: ' + ', '.join(f'{a} ({b} dòng)' for a, b in tinh_moi['lon_nhat'])]
    if tinh_moi.get('so_test') is not None:
        t.append(f'- File kiểm thử: {tinh_moi["so_test"]}')
    if doi is not None:
        t += ['', f'## 6. Các file khác nhau giữa hai bản ({len(doi)} file)', ''] + [f'- `pabt/{a}`: {b}' for a, b in doi]
    return '\n'.join(t) + '\n'


def main(argv) -> int:
    so_sanh = argv[argv.index('--so-sanh') + 1] if '--so-sanh' in argv else ''
    so_ho = int(argv[argv.index('--so-ho') + 1]) if '--so-ho' in argv else 3000
    lan = int(argv[argv.index('--lan') + 1]) if '--lan' in argv else 3
    du_an = argv[argv.index('--du-an') + 1] if '--du-an' in argv else ''
    if not du_an:                                                       # dự án thật mặc định: file .pabt đầu tiên cạnh mã nguồn
        du_an = str(next(iter(sorted(GOC.glob('*.pabt')) + sorted(GOC.parent.glob('*.pabt'))), '') or '')
    if not so_sanh and '--khong-so-sanh' not in argv:                   # mặc định: gói cập nhật mới nhất khác phiên bản mã nguồn
        pb = re.search(r"__version__\s*=\s*'([^']+)'", (GOC / 'pabt' / '__init__.py').read_text(encoding='utf-8')).group(1)
        so = lambda s: tuple(int(x) for x in re.findall(r'\d+', s))       # noqa: E731
        goi = [p for g in ('LARC_CapNhat_*.larcud', 'LARC_CapNhat_*.pabtcn', 'PABT_CapNhat_*.pabtcn')       # từ 0.9.94 tên LARC_CapNhat
               for p in (GOC / 'bo_cai').glob(g) if p.stem.split('_')[-1] != pb]
        if goi:
            so_sanh = str(max(goi, key=lambda p: so(p.stem.split('_')[-1])))
    with tempfile.TemporaryDirectory() as td:
        print(f'Đo mã nguồn hiện tại ({GOC})…', flush=True)
        kq_moi = do_toc_do(GOC, du_an, so_ho, lan)
        tinh_moi = phan_tich_tinh(GOC)
        kq_cu = tinh_cu = doi = None
        if so_sanh:
            cu = tra(GOC, so_sanh, Path(td))
            print(f'Đo bản so sánh ({so_sanh})…', flush=True)
            kq_cu = do_toc_do(cu, du_an, so_ho, lan)
            tinh_cu = phan_tich_tinh(cu)
            doi = khac_nhau(cu, GOC)
    bc = bao_cao(kq_moi, kq_cu, tinh_moi, tinh_cu, doi, so_ho)
    ra = GOC / 'ket_qua_kiem_tra' / f'PhanTich_{kq_moi.get("phien_ban")}_{datetime.now():%Y-%m-%d_%H%M}.md'
    ra.parent.mkdir(exist_ok=True)
    ra.write_text(bc, encoding='utf-8')
    print(bc)
    print(f'Đã lưu: {ra}')
    return 0


if __name__ == '__main__':
    for luong in (sys.stdout, sys.stderr):
        try:
            luong.reconfigure(encoding='utf-8')
        except (AttributeError, ValueError):
            pass
    sys.exit(main(sys.argv[1:]))

r"""Kiểm tra toàn bộ PABT khi có lỗi: mã nguồn (kiểm thử tự động Qt6 + Qt5 32-bit), chạy thử với file mẫu PABT_CHUAN, bản dựng
dist\, bản đã cài trên máy, bộ cài / gói cập nhật trong bo_cai\, bản cập nhật đang dùng, máy chủ LAN đã thiết lập.

  .venv\Scripts\python kiem_tra_toan_bo.py [--nhanh] [--cai-thu] [--mau <file PABT_CHUAN.xlsm>]
    --nhanh    bỏ kiểm thử Qt5 32-bit và bản dựng dist\ (chỉ kiểm phần chính, khoảng 1 phút)
    --cai-thu  cài im lặng bộ cài mới nhất trong bo_cai\ lên máy này rồi tự kiểm tra bản vừa cài
    --mau      file mẫu PABT Excel dùng để chạy thử (mặc định tìm ..\PABT_CHUAN*.xlsm, du_lieu\PABT.xlsm)
Hoặc bấm đúp KIEM_TRA_TOAN_BO.bat. Kết quả: thư mục ket_qua_kiem_tra\KiemTra_<ngày giờ>.txt. Mã thoát 0 = không có LỖI.
Chỉ dùng thư viện chuẩn Python; không sửa file dữ liệu nào (chạy thử trên bản sao trong thư mục tạm).
"""
from __future__ import annotations

import os
import platform
import re
import shutil
import subprocess
import sys
import tempfile
import time
import zipfile
from datetime import datetime
from functools import lru_cache
from pathlib import Path

GOC = Path(__file__).resolve().parent
VENV = GOC / '.venv' / 'Scripts' / 'python.exe'
VENV38 = Path(os.environ.get('LOCALAPPDATA', '')) / 'PABT_dev' / 'venv38_32' / 'Scripts' / 'python.exe'
_CAI = [Path(os.environ.get(k, '')) / 'PABT' / 'PABT.exe' for k in ('ProgramFiles(x86)', 'ProgramFiles') if os.environ.get(k)]
_CAI.append(Path(os.environ.get('LOCALAPPDATA', '')) / 'Programs' / 'PABT' / 'PABT.exe')   # từ chối quyền quản trị / bản cũ
CAI = next((p for p in _CAI if p.exists()), _CAI[0])      # 0.9.22+: mặc định Program Files (x86)\PABT
MAY = Path(os.environ.get('PABT_THU_MUC_MAY') or Path(os.environ.get('APPDATA') or Path.home()) / 'PABT')
DU_LIEU_CAM = re.compile(r'\.(larc|pabt|pabtdt|xlsm)$|DT\d+|DoiChieu|BanIn_', re.I)     # không được có trong bản phát hành

KQ = []          # (trạng thái, bước, chi tiết)
NHAT_KY = []


def ghi(*dong):
    for d in dong:
        print(d)
        NHAT_KY.append(str(d))


def buoc(ten):
    def boc(ham):
        def chay(*a, **k):
            ghi('', f'=== {ten} ===')
            t = time.time()
            try:
                tt, ct = ham(*a, **k)
            except Exception as e:                      # bước kiểm tra tự lỗi: ghi lại, chạy tiếp bước sau
                tt, ct = 'LOI', f'{type(e).__name__}: {e}'
            ghi(f'--> {tt}  {ct}  ({time.time() - t:.0f} giây)')
            KQ.append((tt, ten, ct))
        return chay
    return boc


def so(phien_ban) -> tuple:
    """'0.9.15' -> (0, 9, 15) - cùng cách so như nap_cap_nhat.so."""
    return tuple(int(x) for x in re.findall(r'\d+', str(phien_ban or '')))


def ds_phien_ban(thu_muc: Path, mau: str) -> list:
    """Phiên bản trong tên các file khớp `mau` (glob); file tên lạ (không có số phiên bản) bỏ qua, không làm hỏng bước."""
    kq = []
    for f in thu_muc.glob(mau):
        m = re.search(r'PABT_(?:CaiDat|Setup_Universal)_(\d+(?:\.\d+)*)[_.]', f.name)
        if m:
            kq.append(m.group(1))
    return kq


@lru_cache(maxsize=None)
def phien_ban() -> str:
    m = re.search(r"__version__\s*=\s*'([^']+)'", (GOC / 'pabt' / '__init__.py').read_text(encoding='utf-8'))
    return m.group(1) if m else '?'


def tim_mau(chi_dinh=None):
    ung_vien = [Path(chi_dinh)] if chi_dinh else []
    ung_vien += sorted(GOC.parent.glob('PABT_CHUAN*.xlsm'), key=lambda p: p.stat().st_mtime, reverse=True)
    ung_vien += [GOC / 'du_lieu' / 'PABT.xlsm']
    return next((p for p in ung_vien if p.is_file()), None)


def chay(lenh, cho=900, env=None, cwd=GOC):
    e = dict(os.environ, PYTHONIOENCODING='utf-8', **(env or {}))
    r = subprocess.run([str(x) for x in lenh], cwd=str(cwd), env=e, capture_output=True, timeout=cho)
    ra = (r.stdout + r.stderr).decode('utf-8', 'replace')
    return r.returncode, ra


def tu_kiem_exe(exe: Path):
    with tempfile.TemporaryDirectory() as td:
        f = Path(td) / 'kq.txt'
        subprocess.run([str(exe), 'tu-kiem', str(f)], timeout=300)
        return f.read_text(encoding='utf-8') if f.exists() else ''


# ---------------------------------------------------------------- các bước
@buoc('1. Môi trường máy')
def b_moi_truong():
    ghi(f'Windows: {platform.platform()}  ({platform.machine()})',
        f'Thư mục mã nguồn: {GOC}  ·  phiên bản mã nguồn: {phien_ban()}',
        f'.venv (Qt6): {"có" if VENV.exists() else "KHÔNG CÓ"}  ·  venv38_32 (Qt5): {"có" if VENV38.exists() else "không có"}',
        f'Bản đã cài: {CAI if CAI.exists() else "chưa cài"}',
        f'Thư mục dữ liệu máy: {MAY}')
    trong = shutil.disk_usage(str(GOC)).free / 2 ** 30
    ghi(f'Dung lượng trống ổ mã nguồn: {trong:.1f} GB')
    if not VENV.exists():
        return 'LOI', 'thiếu .venv: chạy CAI_DAT.bat'
    return ('CANH BAO', f'ổ đĩa chỉ còn {trong:.1f} GB') if trong < 2 else ('DAT', '')


def _kiem_thu(py: Path, mau, ten_env):
    env = {'QT_QPA_PLATFORM': 'offscreen'}
    if mau:
        env['PABT_EXCEL'] = str(mau)
    ma, ra = chay([py, '-W', 'ignore', '-m', 'unittest', 'discover', '-s', 'tests', '-t', '.'], cho=1800, env=env)
    dong = [d for d in ra.splitlines() if re.match(r'(Ran \d+|OK|FAILED|FAIL:|ERROR:)', d)]
    ghi(*dong)
    if ma != 0:
        ghi('--- chi tiết lỗi ---', *ra.splitlines()[-80:])
        return 'LOI', f'{ten_env}: có bài kiểm thử lỗi (xem chi tiết trong file kết quả)'
    m = re.search(r'Ran (\d+)', ra)
    bo = re.search(r'skipped=(\d+)', ra)
    return 'DAT', f'{ten_env}: {m.group(1) if m else "?"} bài đạt' + (f', {bo.group(1)} bài bỏ qua' if bo else '') + \
        ('' if mau else ' (không có file mẫu: bỏ qua bài so khớp Excel)')


@buoc('2. Kiểm thử tự động - Win10/11 (Python 3.14 + Qt6)')
def b_kiem_thu_qt6(mau):
    return _kiem_thu(VENV, mau, 'Qt6')


@buoc('3. Kiểm thử tự động - Win7/8 (Python 3.8 32-bit + Qt5)')
def b_kiem_thu_qt5(mau):
    if not VENV38.exists():
        return 'BO QUA', 'chưa có môi trường venv38_32 (CAI_DAT_PHAT_HANH.bat)'
    return _kiem_thu(VENV38, mau, 'Qt5 32-bit')


@buoc('4. Chạy thử với file mẫu: nhập Excel -> lập phương án -> đối chiếu')
def b_chay_thu(mau):
    if not mau:
        return 'BO QUA', 'không tìm thấy file mẫu PABT_CHUAN*.xlsm'
    ghi(f'File mẫu: {mau}  (chỉ đọc; làm trên bản sao)')
    with tempfile.TemporaryDirectory() as td:
        ban = Path(td) / 'mau.xlsm'
        shutil.copy2(mau, ban)
        pabt = Path(td) / 'thu.pabt'
        ma, ra = chay([VENV, 'chay.py', 'nhap', ban, pabt], cho=600)
        ghi(*ra.strip().splitlines()[-6:])
        if ma != 0 or not pabt.exists():
            return 'LOI', 'không nhập được file mẫu'
        ma, ra = chay([VENV, 'chay.py', 'doi-chieu', pabt], cho=600)
        ghi(*ra.strip().splitlines()[-8:])
        if ma != 0:
            return 'LOI', 'lệnh đối chiếu lỗi'
        lech = 'KHỚP 100%' not in ra
        ma, ra = chay([VENV, 'chay.py', 'tu-kiem'], cho=300, env={'QT_QPA_PLATFORM': 'offscreen'})
        ghi(*ra.strip().splitlines())
        if 'KET QUA: DAT' not in ra:
            return 'LOI', 'tự kiểm tra từ mã nguồn không đạt'
    return ('CANH BAO', 'đối chiếu có hộ lệch so với Excel') if lech else ('DAT', 'nhập, tính, đối chiếu, tự kiểm tra đều chạy')


@buoc('5. Bản dựng dist\\ (trước khi đóng bộ cài)')
def b_ban_dung():
    kq = []
    for ten in ('PABT', 'PABT_Win7'):
        exe = GOC / 'dist' / ten / 'PABT.exe'
        if not exe.exists():
            ghi(f'{ten}: chưa dựng')
            continue
        nd = tu_kiem_exe(exe)
        ghi(f'[{ten}]', nd or '(exe không chạy được)')
        kq.append('KET QUA: DAT' in nd)
    if not kq:
        return 'BO QUA', 'chưa có bản dựng (DUNG_BO_CAI.bat)'
    return ('DAT', f'{len(kq)} bản dựng chạy được') if all(kq) else ('LOI', 'có bản dựng tự kiểm tra không đạt')


@buoc('6. Bộ cài, gói cập nhật trong bo_cai\\')
def b_bo_cai():
    d = GOC / 'bo_cai'
    pb = phien_ban()
    # bộ cài có thể là bản cũ hơn (phiên bản mới chỉ phát hành gói cập nhật): lấy bộ cài mới nhất đang có
    pc = max(ds_phien_ban(d, 'LARC_Setup_Universal_*.exe'), key=so, default=pb)
    ghi(f'Bộ cài mới nhất: {pc}  ·  gói cập nhật cần có: {pb}')
    # 0.9.26 (người dùng 11/10/2026): MỘT bộ cài cho mọi Windows + gói zip dự phòng (dung_bo_cai_win.MAC_DINH)
    can = [f'LARC_Setup_Universal_{pc}.exe', f'LARC_ChayNgay_{pc}_Universal.zip', f'LARC_CapNhat_{pb}.pabtcn']
    loi, canh = [], []
    for t in can:
        f = d / t
        ghi(f'{"có   " if f.exists() else "THIẾU"} {t}' + (f'  ({f.stat().st_size / 2 ** 20:.1f} MB)' if f.exists() else ''))
        if not f.exists():
            canh.append(f'thiếu {t}')
    for z in d.glob(f'LARC_ChayNgay_{pc}_*.zip'):
        try:
            with zipfile.ZipFile(z) as zf:
                hong = zf.testzip()
                cam = [n for n in zf.namelist() if DU_LIEU_CAM.search(Path(n).name)]
        except zipfile.BadZipFile as e:
            loi.append(f'{z.name} hỏng: {e}')
            continue
        if hong:
            loi.append(f'{z.name}: file hỏng {hong}')
        if cam:
            loi.append(f'{z.name} có file dữ liệu: {cam[:5]}')
        # gói zip cũng là bộ cài dự phòng (CAI_DAT.cmd): đủ file cài và danh sách khớp nội dung
        with zipfile.ZipFile(z) as zf:
            ten = set(zf.namelist())
            # zip một bản: danh_sach.txt; zip Universal (0.9.26): danh_sach_x64.txt + danh_sach_x86.txt
            ds_ten = ['danh_sach_x64.txt', 'danh_sach_x86.txt'] if z.stem.endswith('_Universal') else ['danh_sach.txt']
            thieu_cai = [x for x in ('CAI_DAT.cmd', 'cai_dat.ps1', 'go_cai_dat.ps1', 'ban.txt', 'phien_ban.txt', *ds_ten)
                         if x not in ten]
            sai = []
            import hashlib
            for dt in (x for x in ds_ten if x in ten):
                for dong in zf.read(dt).decode('utf-8-sig').splitlines():
                    x = dong.split('\t')
                    if len(x) < 4:
                        continue
                    n = x[0].replace('\\', '/')
                    if n not in ten or hashlib.sha256(zf.read(n)).hexdigest() != x[3]:
                        sai.append(n)
        if thieu_cai:
            canh.append(f'{z.name}: thiếu file cài dự phòng {thieu_cai} (bộ cài cũ trước 0.9.21?)')
        if sai:
            loi.append(f'{z.name}: danh_sach.txt không khớp {len(sai)} file, ví dụ {sai[:3]}')
        ghi(f'{z.name}: nguyên vẹn, ' + ('CÓ DỮ LIỆU THẬT' if cam else 'không chứa dữ liệu'))
    goi = d / f'LARC_CapNhat_{pb}.pabtcn'
    if goi.exists() and not VENV.exists():
        canh.append('không kiểm được gói cập nhật (thiếu .venv)')
    elif goi.exists():
        ma, ra = chay([VENV, '-c', 'import sys; from pabt import cap_nhat; m = cap_nhat.doc_goi(sys.argv[1]); '
                                   'print("phien ban", m["phien_ban"], "-", len(m["file"]), "file, ma kiem tra dung")', goi])
        ghi(f'Gói cập nhật: {ra.strip()}')
        if ma != 0:
            loi.append('gói cập nhật hỏng (sai mã SHA-256)')
    if loi:
        return 'LOI', '; '.join(loi)
    return ('CANH BAO', '; '.join(canh)) if canh else ('DAT', f'bộ cài {pc}, gói cập nhật {pb}, không chứa dữ liệu')


@buoc('7. Bản đã cài trên máy này')
def b_da_cai():
    if not CAI.exists():
        return 'BO QUA', 'máy này chưa cài PABT'
    nd = tu_kiem_exe(CAI)
    ghi(nd or '(PABT.exe không chạy được)')
    if 'KET QUA: DAT' not in nd:
        return 'LOI', 'bản đã cài tự kiểm tra không đạt: cài lại bằng bộ cài, hoặc gỡ bản cập nhật'
    m = re.search(r'Phiên bản: ([\d.]+)', nd)
    if m and m.group(1) != phien_ban():
        return 'CANH BAO', f'bản đã cài {m.group(1)}, mã nguồn {phien_ban()}: cài bộ cài / gói cập nhật mới'
    return 'DAT', f'bản {m.group(1) if m else "?"} chạy tốt'


@buoc('8. Bản cập nhật (.pabtcn) đang dùng')
def b_cap_nhat():
    d = MAY / 'cap_nhat'
    hh = d / 'hien_hanh.txt'
    if not hh.exists():
        return 'DAT', 'không dùng bản cập nhật (chạy bản cài gốc)'
    ten = hh.read_text(encoding='utf-8').strip()
    ghi(f'Bản cập nhật hiện hành: {ten}')
    loi = d / ten / 'LOI.txt'
    if loi.exists():
        ghi(loi.read_text(encoding='utf-8', errors='replace')[-3000:])
        return 'LOI', f'bản cập nhật {ten} đã tự tắt do lỗi (xem LOI.txt); phần mềm đang chạy bản gốc'
    dem = d / 'dang_khoi_dong.txt'          # nap_cap_nhat ghi bộ đếm ở thư mục cap_nhat\ (không phải trong thư mục bản)
    if dem.exists():
        return 'CANH BAO', 'lần mở trước chưa tới được cửa sổ chính (dang_khoi_dong.txt còn)'
    return 'DAT', f'bản cập nhật {ten} hoạt động'


@buoc('9. Máy chủ LAN (nếu có thiết lập)')
def b_may_chu():
    import json
    try:
        ch = json.loads((MAY / 'may_chu.json').read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return 'BO QUA', 'máy này không dùng máy chủ LAN (làm việc offline)'
    goc = ch.get('may_chu')
    if not goc:
        return 'BO QUA', 'không dùng máy chủ LAN'
    if not VENV.exists():
        return 'BO QUA', 'thiếu .venv: không chạy được phần kiểm tra máy chủ'
    ghi(f'Máy chủ: {goc}  ·  tài khoản nhớ: {ch.get("tai_khoan", "")}')
    ma, ra = chay([VENV, '-c', 'import sys; from pabt import may_chu as m; g=sys.argv[1]; ok=m.ket_noi_duoc(g, 8); '
                               'print("ket noi:", ok); ok and print("tai khoan:", len(m.ds_nguoi_dung(g)), '
                               '"du an:", len(m.ds_du_an(g)))', goc], cho=60)
    ghi(ra.strip())
    off = MAY / 'offline' / 'lay_ve.json'
    if off.exists():
        ghi(f'Có dự án mang về làm offline: {off}')
    if 'ket noi: True' not in ra:
        return 'CANH BAO', 'không kết nối được máy chủ (mạng / quyền chia sẻ); phần mềm vẫn làm việc offline được'
    return ('DAT', 'kết nối, đọc tài khoản và dự án được') if ma == 0 else ('LOI', 'đọc CSDL máy chủ lỗi')


@buoc('10. Cài thử bộ cài mới nhất (--cai-thu)')
def b_cai_thu():
    pb = max(ds_phien_ban(GOC / 'bo_cai', 'LARC_Setup_Universal_*.exe'), key=so, default=phien_ban())
    bo = GOC / 'bo_cai' / f'LARC_Setup_Universal_{pb}.exe'             # một bộ cài cho mọi Windows (0.9.26)
    if not bo.exists():
        return 'LOI', f'không có {bo.name}'
    ghi(f'Cài im lặng: {bo.name} /Q ...')
    # PABT.exe khi chép giữ ngày giờ lúc dựng (không phải lúc cài): so với trạng thái TRƯỚC khi cài, không so với giờ hiện tại
    truoc = (CAI.stat().st_mtime, CAI.stat().st_size) if CAI.exists() else None
    subprocess.run([str(bo), '/Q'], timeout=900)
    for _ in range(60):                 # vỏ IExpress có thể kết thúc trước khi cài xong
        if CAI.exists() and (truoc is None or (CAI.stat().st_mtime, CAI.stat().st_size) != truoc):
            time.sleep(3)               # chờ chép nốt các file còn lại
            break
        time.sleep(5)
    else:
        ghi('PABT.exe không đổi sau khi cài (cùng bản dựng đã cài trước đó, hoặc cài chưa xong) - vẫn tự kiểm tra')
    nd = tu_kiem_exe(CAI) if CAI.exists() else ''
    ghi(nd or '(không thấy PABT.exe sau khi cài)')
    return ('DAT', f'cài {bo.name} và tự kiểm tra đạt') if 'KET QUA: DAT' in nd else ('LOI', 'cài thử không đạt')


def main(argv) -> int:
    nhanh, cai_thu = '--nhanh' in argv, '--cai-thu' in argv
    chi = argv[argv.index('--mau') + 1] if '--mau' in argv and argv.index('--mau') + 1 < len(argv) else None
    os.chdir(str(GOC))
    bat_dau = datetime.now()
    ghi(f'KIỂM TRA TOÀN BỘ PABT  -  {bat_dau:%H:%M %d/%m/%Y}  -  máy {platform.node()}')
    mau = tim_mau(chi)
    b_moi_truong()
    co_venv = VENV.exists()             # thiếu .venv: bước 1 đã báo LỖI, bỏ các bước cần .venv (khỏi báo lỗi dây chuyền)
    if co_venv:
        b_kiem_thu_qt6(mau)
    if not nhanh:
        b_kiem_thu_qt5(mau)
    if co_venv:
        b_chay_thu(mau)
    if not nhanh:
        b_ban_dung()
    b_bo_cai()
    if cai_thu:
        b_cai_thu()
    b_da_cai()
    b_cap_nhat()
    b_may_chu()
    ghi('', '=' * 78, 'TÓM TẮT')
    for tt, ten, ct in KQ:
        ghi(f'  {tt:<9} {ten}' + (f'  -  {ct}' if ct else ''))
    so_loi = sum(1 for x in KQ if x[0] == 'LOI')
    so_canh = sum(1 for x in KQ if x[0] == 'CANH BAO')
    giay = int((datetime.now() - bat_dau).total_seconds())
    ghi('=' * 78, f'KẾT QUẢ: {"ĐẠT" if not so_loi else f"{so_loi} LỖI"}' + (f', {so_canh} cảnh báo' if so_canh else '') +
        f'  (hết {giay // 60} phút {giay % 60} giây)')
    thu_muc = GOC / 'ket_qua_kiem_tra'
    thu_muc.mkdir(exist_ok=True)
    f = thu_muc / f'KiemTra_{bat_dau:%Y-%m-%d_%H%M}.txt'
    f.write_text('\n'.join(NHAT_KY), encoding='utf-8-sig')
    print(f'\nĐã lưu kết quả: {f}')
    return 1 if so_loi else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))

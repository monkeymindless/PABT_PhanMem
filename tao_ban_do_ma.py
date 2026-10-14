"""Bản đồ mã nguồn + kiểm tra tĩnh (0.9.87) -> BAN_DO_MA.md.

    .venv\\Scripts\\python tao_ban_do_ma.py            (in cảnh báo, ghi BAN_DO_MA.md; mã thoát 1 nếu còn cảnh báo)

Kiểm tra (pabt/, tests/, script ở thư mục gốc):
  - ruff (có trong .venv): F811 định nghĩa trùng tên ghi đè, F841 biến gán không dùng, F821 tên chưa định nghĩa, F401 import thừa,
    E722 `except:` trống. Không có ruff: bỏ qua phần này (ghi rõ trong báo cáo).
  - Thiếu `from __future__ import annotations` (bản Python 3.8 / Windows 7), `match` (Python 3.10+).
  - Import vòng ở CẤP MODULE giữa các module pabt (import trong hàm không tính - cách tránh vòng đang dùng).
  - `from .<module> import <tên>` ở cấp module với tên do hồ sơ địa phương cập nhật lúc chạy (dia_phuong.dang_ky: to_chuc.TEN,
    lap_pa.LOAI_KINH_PHI, thoi_han.MOC…, du_thao.SO_NGAY_…): bản sao giữ giá trị cũ sau dia_phuong.nap_lai().
  - Hàm / lớp / phương thức của pabt không còn được gọi ở đâu (tên không xuất hiện ở pabt/, tests/, script gốc - kể cả trong chuỗi:
    getattr, kết nối tín hiệu theo tên). Phương thức Qt ghi đè (paintEvent, data, …) và tên trong GIU_LAI không tính.
Chỉ thư viện chuẩn (+ ruff nếu có). Không sửa mã - chỉ báo."""
from __future__ import annotations
import ast
import json
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

GOC = Path(__file__).resolve().parent
LOAI_RUFF = 'F811,F841,F821,F401,E722'
# phương thức Qt được gọi từ C++ (ghi đè) - không phải mã chết
QT_GHI_DE = {
    'paintEvent', 'resizeEvent', 'showEvent', 'hideEvent', 'closeEvent', 'keyPressEvent', 'keyReleaseEvent', 'mousePressEvent',
    'mouseReleaseEvent', 'mouseMoveEvent', 'mouseDoubleClickEvent', 'wheelEvent', 'enterEvent', 'leaveEvent', 'focusInEvent',
    'focusOutEvent', 'contextMenuEvent', 'changeEvent', 'event', 'eventFilter', 'nativeEvent', 'timerEvent', 'dragEnterEvent',
    'dropEvent', 'dragMoveEvent', 'moveEvent', 'sizeHint', 'minimumSizeHint', 'hasHeightForWidth', 'heightForWidth', 'data',
    'setData', 'rowCount', 'columnCount', 'headerData', 'flags', 'index', 'parent', 'sort', 'filterAcceptsRow', 'lessThan',
    'createEditor', 'setEditorData', 'setModelData', 'updateEditorGeometry', 'paint', 'editorEvent', 'displayText', 'validate',
    'fixup', 'textFromValue', 'valueFromText', 'stepBy', 'stepEnabled', 'done', 'accept', 'reject', 'exec', 'addItem', 'count',
    'itemAt', 'takeAt', 'setGeometry', 'expandingDirections', 'sizeHintForColumn', 'sizeHintForRow', 'initStyleOption',
    'showPopup', 'hidePopup', 'boundingRect', 'shape', 'hoverEnterEvent', 'hoverLeaveEvent', 'itemChange', 'inputMethodEvent',
    'inputMethodQuery', 'scrollContentsBy', 'viewportEvent', 'run', 'canFetchMore', 'fetchMore', 'supportedDropActions',
    'mimeData', 'mimeTypes', 'dropMimeData', 'tabSizeHint', 'minimumTabSizeHint', 'sectionSizeFromContents', 'paintSection',
    'focusNextPrevChild', 'setVisible', 'setModel', 'insertRows', 'removeRows', 'match', 'buddy', 'span', 'setText',
    # html.parser.HTMLParser gọi lại
    'handle_starttag', 'handle_endtag', 'handle_startendtag', 'handle_data', 'handle_comment', 'handle_entityref',
}
# giữ lại có chủ đích (API cho kiểm thử / gói cập nhật / dòng lệnh) - ghi lý do
GIU_LAI = {
    'quy_chuan': 'app: lệnh cũ còn giữ cho test (0.9.47)',
}
# module cập nhật giá trị lúc chạy (dia_phuong.dang_ky) - tên biến toàn cục mà hàm đăng ký gán lại
_RE_THONG_SO = re.compile(r'^[A-Z][A-Z0-9_]+$')


def _cac_file() -> list:
    ds = sorted((GOC / 'pabt').glob('*.py')) + sorted((GOC / 'tests').glob('*.py'))
    ds += [p for p in sorted(GOC.glob('*.py')) if not p.name.startswith(('TU_DONG_',))]
    return ds


def _doc(p: Path):
    try:
        return ast.parse(p.read_text(encoding='utf-8'), filename=str(p))
    except SyntaxError as e:
        return e


def _ruff(files: list) -> tuple:
    """([cảnh báo], có ruff?)"""
    lenh = [sys.executable, '-m', 'ruff', 'check', '--select', LOAI_RUFF, '--output-format', 'json', '--no-cache',
            *[str(p) for p in files]]
    try:
        r = subprocess.run(lenh, capture_output=True, text=True, encoding='utf-8', cwd=str(GOC), timeout=300)
    except (OSError, subprocess.TimeoutExpired):
        return [], False
    if 'No module named ruff' in (r.stderr or ''):
        return [], False
    try:
        ds = json.loads(r.stdout or '[]')
    except ValueError:
        return [f'ruff: không đọc được kết quả ({(r.stderr or "")[:200]})'], True
    return [f'{Path(x["filename"]).relative_to(GOC)}:{x["location"]["row"]}: {x["code"]} {x["message"]}' for x in ds], True


def _ten_module(p: Path) -> str:
    return p.stem


def _import_cap_module(cay, ten_mod: str) -> set:
    """Các module pabt được import ở CẤP MODULE (kể cả trong if / try ở cấp module, không tính trong hàm / lớp)."""
    kq = set()

    def duyet(nut):
        for x in ast.iter_child_nodes(nut):
            if isinstance(x, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda)):
                continue
            if isinstance(x, ast.ImportFrom):
                if x.level == 1 and x.module:
                    kq.add(x.module.split('.')[0])
                elif x.level == 1 and not x.module:
                    kq.update(a.name for a in x.names)
                elif (x.module or '').startswith('pabt.'):
                    kq.add(x.module.split('.')[1])
            elif isinstance(x, ast.Import):
                kq.update(a.name.split('.')[1] for a in x.names if a.name.startswith('pabt.'))
            duyet(x)
    duyet(cay)
    kq.discard(ten_mod)
    return kq


def _vong(do_thi: dict) -> list:
    """Các chu trình (danh sách module) trong đồ thị import cấp module."""
    ket, mau, ngan = [], {}, []

    def dfs(u):
        mau[u] = 1
        ngan.append(u)
        for v in sorted(do_thi.get(u, ())):
            if v not in do_thi:
                continue
            if mau.get(v) == 1:
                vong = ngan[ngan.index(v):] + [v]
                if sorted(vong[:-1]) not in [sorted(c[:-1]) for c in ket]:
                    ket.append(vong)
            elif not mau.get(v):
                dfs(v)
        ngan.pop()
        mau[u] = 2
    for u in sorted(do_thi):
        if not mau.get(u):
            dfs(u)
    return ket


def _bien_dong(cay_theo_mod: dict) -> dict:
    """{module: {tên biến toàn cục do hàm đăng ký với dia_phuong.dang_ky gán lại}}."""
    kq = {}
    for mod, cay in cay_theo_mod.items():
        ham_dk = set()
        for x in ast.walk(cay):
            if isinstance(x, ast.Call) and isinstance(x.func, ast.Attribute) and x.func.attr == 'dang_ky' and x.args \
                    and isinstance(x.args[0], ast.Name):
                ham_dk.add(x.args[0].id)
        ten = set()
        for x in cay.body:
            if isinstance(x, ast.FunctionDef) and x.name in ham_dk:
                for y in ast.walk(x):
                    if isinstance(y, ast.Global):
                        ten.update(n for n in y.names if _RE_THONG_SO.match(n))
        if ten:
            kq[mod] = ten
    return kq


def _ten_dung(cay) -> set:
    """Mọi tên được nhắc tới (Name, thuộc tính, tên import, chuỗi ngắn giống định danh, từ trong chuỗi)."""
    kq = set()
    for x in ast.walk(cay):
        if isinstance(x, ast.Name):
            kq.add(x.id)
        elif isinstance(x, ast.Attribute):
            kq.add(x.attr)
        elif isinstance(x, ast.alias):
            kq.add(x.name.split('.')[-1])
            if x.asname:
                kq.add(x.asname)
        elif isinstance(x, ast.Constant) and isinstance(x.value, str) and len(x.value) < 5000:
            kq.update(re.findall(r'[A-Za-z_][A-Za-z0-9_]*', x.value))
        elif isinstance(x, ast.keyword) and x.arg:
            kq.add(x.arg)
    return kq


def _dinh_nghia(cay, mod: str) -> list:
    """[(tên, dòng, loại, lớp chứa)] hàm / lớp cấp module và phương thức."""
    kq = []
    for x in cay.body:
        if isinstance(x, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if not x.decorator_list:                    # @atexit.register, @lru_cache… : được gọi qua decorator
                kq.append((x.name, x.lineno, 'hàm', ''))
        elif isinstance(x, ast.ClassDef):
            kq.append((x.name, x.lineno, 'lớp', ''))
            for y in x.body:
                if isinstance(y, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    kq.append((y.name, y.lineno, 'phương thức', x.name))
    return kq


def _so_lan_dinh_nghia(cac_cay: dict) -> dict:
    """Số lần mỗi tên được ĐỊNH NGHĨA (một định nghĩa = một lần nhắc tên không phải sử dụng)."""
    dem = {}
    for cay in cac_cay.values():
        for x in ast.walk(cay):
            if isinstance(x, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                dem[x.name] = dem.get(x.name, 0) + 1
    return dem


def kiem_tra() -> dict:
    files = _cac_file()
    cay = {}
    canh_bao = []
    for p in files:
        c = _doc(p)
        rel = str(p.relative_to(GOC))
        if isinstance(c, SyntaxError):
            canh_bao.append(f'{rel}:{c.lineno}: lỗi cú pháp {c.msg}')
            continue
        cay[rel] = c
        dau = [x for x in c.body if isinstance(x, ast.ImportFrom) and x.module == '__future__']
        if p.suffix == '.py' and p.stat().st_size > 0 and not any(a.name == 'annotations' for x in dau for a in x.names):
            canh_bao.append(f'{rel}:1: thiếu "from __future__ import annotations" (bản Python 3.8 / Windows 7)')
        for x in ast.walk(c):
            if type(x).__name__ == 'Match':
                canh_bao.append(f'{rel}:{x.lineno}: "match" cần Python 3.10 (bản Windows 7 chạy Python 3.8)')
    ruff, co_ruff = _ruff(files)
    canh_bao += ruff
    pabt = {Path(k).stem: v for k, v in cay.items() if k.startswith('pabt')}
    do_thi = {m: _import_cap_module(c, m) for m, c in pabt.items()}
    for v in _vong(do_thi):
        canh_bao.append('import vòng cấp module: ' + ' -> '.join(v))
    dong = _bien_dong(pabt)
    for rel, c in cay.items():
        for x in c.body:
            if isinstance(x, ast.ImportFrom) and x.module:
                m = x.module.split('.')[-1] if x.level or x.module.startswith('pabt.') else None
                for a in x.names:
                    if m in dong and a.name in dong[m]:
                        canh_bao.append(f'{rel}:{x.lineno}: "from .{m} import {a.name}" ở cấp module - giá trị cũ sau khi đổi '
                                        f'hồ sơ địa phương (dùng {m}.{a.name} lúc gọi)')
    # mã chết
    dung = set()
    for c in cay.values():
        dung |= _ten_dung(c)
    dem_dn = _so_lan_dinh_nghia(cay)
    chet = []
    for mod, c in pabt.items():
        for ten, dong_so, loai, lop in _dinh_nghia(c, mod):
            if ten.startswith('__') or ten in QT_GHI_DE or ten in GIU_LAI or ten.startswith('test'):
                continue
            if ten not in dung:
                chet.append(f'pabt/{mod}.py:{dong_so}: {loai} "{(lop + ".") if lop else ""}{ten}" không còn nơi nào dùng')
    canh_bao += chet
    return dict(files=files, cay=cay, canh_bao=canh_bao, co_ruff=co_ruff, do_thi=do_thi, bien_dong=dong, chet=chet,
                dem_dn=dem_dn)


def ban_do(kq: dict) -> str:
    dong = [f'# Bản đồ mã nguồn PABT', '', f'Tạo bởi `tao_ban_do_ma.py` lúc {datetime.now():%d/%m/%Y %H:%M}. '
            f'Kiểm tra tĩnh: {len(kq["canh_bao"])} cảnh báo' + ('' if kq['co_ruff'] else ' (KHÔNG có ruff: bỏ qua F401/F811/F821/F841/E722)')
            + '.', '', '## Cảnh báo', '']
    dong += [f'- {x}' for x in kq['canh_bao']] or ['- Không có.']
    dong += ['', '## Module (pabt/)', '', '| Module | Dòng | Lớp | Hàm cấp module | Import pabt cấp module |', '|---|---:|---:|---:|---|']
    tong = 0
    for rel, c in sorted(kq['cay'].items()):
        if not rel.startswith('pabt'):
            continue
        p = GOC / rel
        n = p.read_text(encoding='utf-8').count('\n') + 1
        tong += n
        lop = sum(isinstance(x, ast.ClassDef) for x in c.body)
        ham = sum(isinstance(x, (ast.FunctionDef, ast.AsyncFunctionDef)) for x in c.body)
        dong.append(f'| `{p.name}` | {n} | {lop} | {ham} | {", ".join(sorted(kq["do_thi"].get(p.stem, ()))) or "-"} |')
    dong += ['', f'Tổng: {tong} dòng mã trong pabt/.', '', '## Giá trị theo hồ sơ địa phương (dia_phuong.dang_ky)', '']
    dong += [f'- `{m}`: {", ".join(sorted(t))} - đọc `{m}.<tên>` lúc gọi' for m, t in sorted(kq['bien_dong'].items())]
    dong += ['', '## Lớp và hàm', '']
    for rel, c in sorted(kq['cay'].items()):
        if not rel.startswith('pabt'):
            continue
        dong.append(f'### `{Path(rel).name}`')
        for x in c.body:
            if isinstance(x, ast.ClassDef):
                pt = [y.name for y in x.body if isinstance(y, (ast.FunctionDef, ast.AsyncFunctionDef))]
                dong.append(f'- lớp `{x.name}` (dòng {x.lineno}): ' + ', '.join(f'`{t}`' for t in pt[:25]) +
                            (f' … (+{len(pt) - 25})' if len(pt) > 25 else ''))
        hs = [x for x in c.body if isinstance(x, (ast.FunctionDef, ast.AsyncFunctionDef))]
        if hs:
            dong.append('- hàm: ' + ', '.join(f'`{x.name}`' for x in hs))
        dong.append('')
    return '\n'.join(dong) + '\n'


def main() -> int:
    for luong in (sys.stdout, sys.stderr):
        try:
            luong.reconfigure(encoding='utf-8')
        except AttributeError:
            pass
    kq = kiem_tra()
    (GOC / 'BAN_DO_MA.md').write_text(ban_do(kq), encoding='utf-8')
    for x in kq['canh_bao']:
        print(x)
    print(f'{len(kq["canh_bao"])} cảnh báo' + ('' if kq['co_ruff'] else ' (không có ruff)') + ' -> BAN_DO_MA.md')
    return 1 if kq['canh_bao'] else 0


if __name__ == '__main__':
    sys.exit(main())

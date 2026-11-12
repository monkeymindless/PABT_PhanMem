#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Văn phòng kiểm định LARC (PABT): phạm vi săn lỗi của một phiên bản + sổ lỗi ẩn + bảng điều khiển.

Chỉ dùng thư viện chuẩn. Không sửa gì trong pabt/, tests/.

  python van_phong.py pham-vi [--tu <commit>]   phần đổi so với bản phát hành trước -> ket_qua_kiem_tra/van_phong/<bản>/
  python van_phong.py ton-dong                  lỗi còn mở (phải soát lại ở mỗi phiên bản)
  python van_phong.py ghi <phat_hien.json>      thêm / gặp lại phát hiện vào sổ docs/van_phong/so_loi.json
  python van_phong.py cap-nhat VP-0007 --trang-thai da_sua --ghi-chu "..." [--kiem-chung "tests.x.y"]
  python van_phong.py bang                      dựng docs/van_phong/bang_dieu_khien.html từ sổ
  python van_phong.py kiem                      kiểm cấu trúc sổ

Quy ước làm việc của các chuyên gia: docs/van_phong/QUY_UOC.md
"""
from __future__ import annotations

import argparse
import ast
import datetime as dt
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

GOC = Path(__file__).resolve().parent
THU_MUC = GOC / 'docs' / 'van_phong'
SO = THU_MUC / 'so_loi.json'
CAP = THU_MUC / 'cap_di_cung.json'
BANG = THU_MUC / 'bang_dieu_khien.html'
KET_QUA = GOC / 'ket_qua_kiem_tra' / 'van_phong'

TRANG_THAI = ('nghi_van', 'xac_nhan', 'da_sua', 'hoan', 'khong_phai_loi')
CON_MO = ('nghi_van', 'xac_nhan', 'hoan')
MUC = ('P0', 'P1', 'P2', 'P3')
BAT_BUOC = ('tieu_de', 'chuyen_gia', 'muc', 'tep', 'mo_ta')

CHUYEN_GIA = [
    ('vp-doi-chieu-phien-ban', 'Đối chiếu phiên bản',
     'Đọc phần đổi giữa hai bản, lần ngược nơi gọi: sửa một bên quên bên kia, hàm đổi không test nào chạm.'),
    ('vp-quy-tac-hieu-luc', 'Quy tắc hiệu lực',
     'Biến từng quy tắc đang hiệu lực thành phép kiểm máy; tìm quy tắc chưa có test canh và chỗ vi phạm.'),
    ('vp-so-lieu-bien', 'Số liệu và dữ liệu biên',
     'Thử giá trị biên, chữ người gõ, tên có dấu, file cũ / hỏng, dự án lớn trên bản sao tạm.'),
    ('vp-trang-thai-ghi', 'Trạng thái và đường ghi',
     'Chuỗi thao tác mở - sửa - hoàn tác - lưu - mở lại; quyền, nhận việc, chỉ xem, phiên bản phương án.'),
    ('vp-giao-dien-an', 'Giao diện ẩn',
     'Lỗi mà lượt bấm mọi nút không thấy: tông Tối, Qt5, trạng thái nút sau chuỗi thao tác, vòng đời widget.'),
    ('vp-phat-hanh-nang-cap', 'Phát hành và nâng cấp',
     'Gói cập nhật so mã nguồn, file dữ liệu thiếu trong bản dựng, đường nâng từ bản cũ, Python 3.8.'),
    ('vp-no-ton-dong', 'Nợ tồn đọng',
     'Lỗi đã thấy mà chưa xử lý: lịch sử phát triển, báo cáo cũ, test bị bỏ qua, except nuốt lỗi.'),
    ('vp-phan-bien', 'Phản biện',
     'Chạy lại từng phát hiện, cố bác bỏ; không tái hiện được thì không được gọi là lỗi.'),
]


# ---------------------------------------------------------------- tiện ích
def _git(*doi_so: str) -> str:
    kq = subprocess.run(['git', '-c', 'safe.directory=*', '-c', 'core.quotepath=off', '-C', str(GOC)] + list(doi_so),
                        stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if kq.returncode != 0:
        raise SystemExit('git %s: %s' % (' '.join(doi_so), kq.stderr.decode('utf-8', 'replace').strip()))
    return kq.stdout.decode('utf-8', 'replace')


def phien_ban() -> str:
    chu = (GOC / 'pabt' / '__init__.py').read_text(encoding='utf-8')
    m = re.search(r"__version__\s*=\s*['\"]([^'\"]+)", chu)
    return m.group(1) if m else '?'


def moc_truoc(ban: str):
    """(commit, số bản) của bản phát hành gần nhất khác bản hiện hành."""
    for dong in _git('log', '-400', '--format=%H%x09%s').splitlines():
        ma, _, chu = dong.partition('\t')
        m = re.match(r'(\d+\.\d+\.\d+)\s+phát hành', chu)
        if m and m.group(1) != ban:
            return ma, m.group(1)
    raise SystemExit('Không tìm thấy commit "<bản> phát hành" trước bản %s: dùng --tu <commit>.' % ban)


def doc_so() -> dict:
    if not SO.exists():
        return {'so_tiep': 1, 'loi': []}
    return json.loads(SO.read_text(encoding='utf-8'))


def ghi_so(so: dict) -> None:
    THU_MUC.mkdir(parents=True, exist_ok=True)
    tam = SO.with_suffix('.tam')
    tam.write_text(json.dumps(so, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    tam.replace(SO)


def _khoa(p: dict) -> str:
    if p.get('khoa'):
        return str(p['khoa'])
    goc = '|'.join([str(p.get('tep', '')).replace('\\', '/').lower(), str(p.get('ham', '')).lower(),
                    re.sub(r'\s+', ' ', str(p.get('tieu_de', '')).strip().lower())])
    return hashlib.sha1(goc.encode('utf-8')).hexdigest()[:12]


def _hom_nay() -> str:
    return dt.date.today().isoformat()


# ---------------------------------------------------------------- phạm vi
def _ham(nguon: str) -> dict:
    """{tên đủ: dấu vân cây cú pháp} của hàm cấp module và phương thức của lớp."""
    try:
        cay = ast.parse(nguon)
    except SyntaxError:
        return {}
    kq = {}

    def di(nut, truoc):
        for con in nut.body:
            if isinstance(con, (ast.FunctionDef, ast.AsyncFunctionDef)):
                kq[truoc + con.name] = ast.dump(con)
            elif isinstance(con, ast.ClassDef):
                di(con, truoc + con.name + '.')
    di(cay, '')
    return kq


def pham_vi(tu: str = '') -> Path:
    ban = phien_ban()
    if tu:
        moc, ban_truoc = tu, tu[:10]
    else:
        moc, ban_truoc = moc_truoc(ban)
    doi = []
    for dong in _git('diff', '--numstat', moc, '--', 'pabt', 'tests', 'chay.py', 'nap_cap_nhat.py', 'bo_cai_win',
                     'mau_in', 'di_dong').splitlines():
        them, bot, tep = dong.split('\t', 2)
        doi.append((tep, them, bot))
    moi = [t for t in _git('ls-files', '--others', '--exclude-standard', '--', 'pabt', 'tests').splitlines() if t]

    ten_trong_test = set()
    for f in (GOC / 'tests').glob('*.py'):
        ten_trong_test.update(re.findall(r'[A-Za-z_]\w*', f.read_text(encoding='utf-8', errors='replace')))

    ham_doi, da_doi = [], set()
    for tep, _them, _bot in doi:
        if not (tep.startswith('pabt/') and tep.endswith('.py')):
            continue
        da_doi.add(tep)
        f = GOC / tep
        sau = _ham(f.read_text(encoding='utf-8')) if f.exists() else {}
        try:
            truoc = _ham(_git('show', '%s:%s' % (moc, tep)))
        except SystemExit:
            truoc = {}
        for ten in sorted(set(truoc) | set(sau)):
            if truoc.get(ten) == sau.get(ten):
                continue
            kieu = 'mới' if ten not in truoc else ('đã xóa' if ten not in sau else 'đổi')
            ngan = ten.rsplit('.', 1)[-1]
            ham_doi.append({'tep': tep, 'ham': ten, 'kieu': kieu, 'co_test_nhac': ngan in ten_trong_test})
    da_doi.update(t for t, _a, _b in doi)

    canh_bao = []
    if CAP.exists():
        ten_ham_doi = {(h['tep'], h['ham'].rsplit('.', 1)[-1]) for h in ham_doi}
        for cap in json.loads(CAP.read_text(encoding='utf-8')):
            def cham(ben):
                for muc in ben:
                    tep, _, ham = muc.partition('::')
                    if (ham and (tep, ham) in ten_ham_doi) or (not ham and tep in da_doi):
                        return True
                return False
            a, b = cham(cap['a']), cham(cap['b'])
            if a != b:
                canh_bao.append({'da_doi': cap['a'] if a else cap['b'], 'chua_doi': cap['b'] if a else cap['a'],
                                 'vi_sao': cap.get('vi_sao', '')})

    thu_muc = KET_QUA / ban
    thu_muc.mkdir(parents=True, exist_ok=True)
    du_lieu = {'ban': ban, 'ban_truoc': ban_truoc, 'moc': moc, 'ngay': _hom_nay(), 'tep_doi': doi, 'tep_moi': moi,
               'ham_doi': ham_doi, 'cap_lech': canh_bao}
    (thu_muc / 'pham_vi.json').write_text(json.dumps(du_lieu, ensure_ascii=False, indent=1), encoding='utf-8')

    khong_test = [h for h in ham_doi if not h['co_test_nhac'] and h['kieu'] != 'đã xóa']
    d = ['# Phạm vi săn lỗi bản %s (so với %s, mốc %s)' % (ban, ban_truoc, moc[:7]), '',
         '- File đổi: %d; file mới chưa vào git: %d' % (len(doi), len(moi)),
         '- Hàm / phương thức đổi trong pabt/: %d (mới %d, đổi %d, xóa %d)' % (
             len(ham_doi), sum(h['kieu'] == 'mới' for h in ham_doi), sum(h['kieu'] == 'đổi' for h in ham_doi),
             sum(h['kieu'] == 'đã xóa' for h in ham_doi)),
         '- Hàm đổi / mới mà KHÔNG file test nào nhắc tên: %d (chỗ dễ có lỗi ẩn nhất - tên trùng tên khác vẫn bị tính '
         'là "có nhắc", nên danh sách này là mức tối thiểu)' % len(khong_test), '']
    if canh_bao:
        d += ['## Cặp phải sửa cùng nhau nhưng chỉ một bên đổi', '']
        for c in canh_bao:
            d.append('- Đã đổi: %s; chưa đổi: %s. %s' % (', '.join(c['da_doi']), ', '.join(c['chua_doi']), c['vi_sao']))
        d.append('')
    d += ['## Hàm đổi / mới không test nào nhắc tên', '']
    d += ['- `%s` :: `%s` (%s)' % (h['tep'], h['ham'], h['kieu']) for h in khong_test] or ['(không có)']
    d += ['', '## File đổi (dòng thêm / bớt)', '']
    d += ['- `%s` +%s -%s' % x for x in sorted(doi, key=lambda x: -(int(x[1]) if x[1].isdigit() else 0))]
    if moi:
        d += ['', '## File mới chưa vào git', ''] + ['- `%s`' % t for t in moi]
    d += ['', '## Mọi hàm đổi', '']
    d += ['- `%s` :: `%s` (%s%s)' % (h['tep'], h['ham'], h['kieu'], '' if h['co_test_nhac'] else ', không test nhắc')
          for h in ham_doi]
    ra = thu_muc / 'pham_vi.md'
    ra.write_text('\n'.join(d) + '\n', encoding='utf-8')
    print('Bản %s so với %s: %d file đổi, %d hàm đổi, %d hàm không test nhắc tên, %d cặp lệch.' % (
        ban, ban_truoc, len(doi), len(ham_doi), len(khong_test), len(canh_bao)))
    print(ra)
    return ra


# ---------------------------------------------------------------- sổ lỗi
def _kiem_phat_hien(p: dict) -> list:
    loi = ['thiếu "%s"' % k for k in BAT_BUOC if not str(p.get(k, '')).strip()]
    if p.get('muc') not in MUC:
        loi.append('muc phải là một trong %s' % (MUC,))
    if p.get('trang_thai', 'nghi_van') not in TRANG_THAI:
        loi.append('trang_thai phải là một trong %s' % (TRANG_THAI,))
    return loi


def _du_chung_cu(p: dict) -> bool:
    return bool(str(p.get('tai_hien', '')).strip() and str(p.get('bang_chung', '')).strip())


def ghi(tep: str) -> int:
    ds = json.loads(Path(tep).read_text(encoding='utf-8'))
    if isinstance(ds, dict):
        ds = ds.get('loi') or ds.get('phat_hien') or [ds]
    so, ban = doc_so(), phien_ban()
    theo_khoa = {x['khoa']: x for x in so['loi']}
    them = gap_lai = bo = 0
    for p in ds:
        loi = _kiem_phat_hien(p)
        if loi:
            bo += 1
            print('BỎ "%s": %s' % (p.get('tieu_de', '?'), '; '.join(loi)))
            continue
        tt = p.get('trang_thai', 'nghi_van')
        if tt == 'xac_nhan' and not _du_chung_cu(p):
            print('HẠ xuống nghi_van "%s": xác nhận phải có tai_hien và bang_chung.' % p['tieu_de'])
            tt = 'nghi_van'
        khoa = _khoa(p)
        cu = theo_khoa.get(khoa)
        if cu:
            gap_lai += 1
            for k, v in p.items():
                if k not in ('ma', 'khoa', 'lich_su', 'trang_thai', 'phien_ban_phat_hien') and v not in ('', None):
                    cu[k] = v
            ghi_chu = 'gặp lại'
            if cu['trang_thai'] == 'da_sua' and tt in ('nghi_van', 'xac_nhan'):
                ghi_chu = 'TÁI PHÁT sau khi đã sửa'
            if not (cu['trang_thai'] == 'xac_nhan' and tt == 'nghi_van'):
                cu['trang_thai'] = tt
            cu['lich_su'].append({'phien_ban': ban, 'ngay': _hom_nay(), 'trang_thai': cu['trang_thai'],
                                  'ghi_chu': ghi_chu})
            continue
        moi = dict(p)
        moi.update({'ma': 'VP-%04d' % so['so_tiep'], 'khoa': khoa, 'trang_thai': tt, 'phien_ban_phat_hien': ban,
                    'lich_su': [{'phien_ban': ban, 'ngay': _hom_nay(), 'trang_thai': tt, 'ghi_chu': 'ghi sổ'}]})
        so['so_tiep'] += 1
        so['loi'].append(moi)
        theo_khoa[khoa] = moi
        them += 1
    ghi_so(so)
    print('Sổ lỗi: thêm %d, gặp lại %d, bỏ %d. Tổng %d.' % (them, gap_lai, bo, len(so['loi'])))
    return 1 if bo else 0


def cap_nhat(ma: str, trang_thai: str, ghi_chu: str, kiem_chung: str = '', tai_hien: str = '',
             bang_chung: str = '') -> int:
    so = doc_so()
    for x in so['loi']:
        if x['ma'] == ma:
            if tai_hien:
                x['tai_hien'] = tai_hien
            if bang_chung:
                x['bang_chung'] = bang_chung
            if kiem_chung:
                x['kiem_chung'] = kiem_chung
            if trang_thai == 'xac_nhan' and not _du_chung_cu(x):
                print('Từ chối: xác nhận phải có tai_hien và bang_chung (--tai-hien, --bang-chung).')
                return 1
            if trang_thai == 'da_sua' and not str(x.get('kiem_chung', '')).strip():
                print('Từ chối: "da_sua" phải kèm --kiem-chung (tên test canh lỗi này, hoặc lệnh tái hiện nay đã đạt).')
                return 1
            if trang_thai in ('khong_phai_loi', 'hoan') and not ghi_chu.strip():
                print('Từ chối: "%s" phải có --ghi-chu nêu lý do.' % trang_thai)
                return 1
            x['trang_thai'] = trang_thai
            x['lich_su'].append({'phien_ban': phien_ban(), 'ngay': _hom_nay(), 'trang_thai': trang_thai,
                                 'ghi_chu': ghi_chu})
            ghi_so(so)
            print('%s -> %s' % (ma, trang_thai))
            return 0
    print('Không có mã %s trong sổ.' % ma)
    return 1


def ton_dong() -> int:
    mo = [x for x in doc_so()['loi'] if x['trang_thai'] in CON_MO]
    mo.sort(key=lambda x: (x['muc'], x['ma']))
    for x in mo:
        print('%s %s [%s] từ bản %s, qua %d lượt | %s:%s | %s' % (
            x['ma'], x['muc'], x['trang_thai'], x['phien_ban_phat_hien'], len(x['lich_su']), x['tep'],
            x.get('dong', ''), x['tieu_de']))
    print('Còn mở: %d' % len(mo))
    return 0


def kiem() -> int:
    so, loi, khoa = doc_so(), 0, set()
    for x in so['loi']:
        ds = _kiem_phat_hien(x)
        if x.get('khoa') in khoa:
            ds.append('trùng khóa')
        khoa.add(x.get('khoa'))
        if x['trang_thai'] == 'xac_nhan' and not _du_chung_cu(x):
            ds.append('xác nhận mà thiếu tai_hien / bang_chung')
        if x['trang_thai'] == 'da_sua' and not x.get('kiem_chung'):
            ds.append('đã sửa mà thiếu kiem_chung')
        if ds:
            loi += 1
            print('%s: %s' % (x.get('ma'), '; '.join(ds)))
    print('Sổ lỗi: %d mục, %d mục sai cấu trúc.' % (len(so['loi']), loi))
    return 1 if loi else 0


# ---------------------------------------------------------------- bảng điều khiển
def bang() -> Path:
    so = doc_so()
    du_lieu = {'ban': phien_ban(), 'ngay': _hom_nay(), 'loi': so['loi'],
               'chuyen_gia': [{'ma': a, 'ten': b, 'viec': c} for a, b, c in CHUYEN_GIA]}
    chu = json.dumps(du_lieu, ensure_ascii=False).replace('</', '<\\/')
    mau = (THU_MUC / 'bang_mau.html').read_text(encoding='utf-8')
    BANG.write_text(mau.replace('/*DU_LIEU*/null', chu), encoding='utf-8')
    print(BANG)
    return BANG


def main() -> int:
    for dong in (sys.stdout, sys.stderr):
        try:
            dong.reconfigure(encoding='utf-8')
        except Exception:
            pass
    p = argparse.ArgumentParser(description='Văn phòng kiểm định LARC')
    con = p.add_subparsers(dest='lenh')
    a = con.add_parser('pham-vi')
    a.add_argument('--tu', default='')
    con.add_parser('ton-dong')
    a = con.add_parser('ghi')
    a.add_argument('tep')
    a = con.add_parser('cap-nhat')
    a.add_argument('ma')
    a.add_argument('--trang-thai', required=True, choices=TRANG_THAI)
    a.add_argument('--ghi-chu', default='')
    a.add_argument('--kiem-chung', default='')
    a.add_argument('--tai-hien', default='')
    a.add_argument('--bang-chung', default='')
    con.add_parser('bang')
    con.add_parser('kiem')
    d = p.parse_args()
    if d.lenh == 'pham-vi':
        pham_vi(d.tu)
        return 0
    if d.lenh == 'ton-dong':
        return ton_dong()
    if d.lenh == 'ghi':
        ma = ghi(d.tep)
        bang()
        return ma
    if d.lenh == 'cap-nhat':
        ma = cap_nhat(d.ma, d.trang_thai, d.ghi_chu, d.kiem_chung, d.tai_hien, d.bang_chung)
        bang()
        return ma
    if d.lenh == 'bang':
        bang()
        return 0
    if d.lenh == 'kiem':
        return kiem()
    p.print_help()
    return 2


if __name__ == '__main__':
    sys.exit(main())

"""Báo cáo tổng hợp ý kiến, tiếp thu, giải trình dự thảo phương án (.docx) - hồ sơ đính kèm tờ trình thẩm định (Bước 8 Mục IV
QĐ 18/2026/QĐ-UBND): kết quả niêm yết công khai, kết quả lấy ý kiến của các hộ trong đợt trình, nội dung kiến nghị và kết quả
đối thoại, giải trình. Số liệu lấy từ Niêm yết & Lấy ý kiến (du_thao); đầu văn bản, chữ ký dùng chung chỗ trống với tờ trình
(van_ban_trinh.du_lieu). Không phụ thuộc Qt, không cần Word.
"""
from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

from . import du_thao, van_ban_trinh as vb

TEN_FILE = 'BAO_CAO_TIEP_THU_Y_KIEN.docx'
KIEN_NGHI = ('khong_dong_y', 'y_kien_khac')


def _pt(a: int, b: int) -> str:
    return f'{(a * 100 / b) if b else 0.0:.1f}'.replace('.', ',')


def thu_thap(con, ds_ma_ho: list) -> dict:
    """Số liệu của các hộ ds_ma_ho: mỗi hộ lấy ý kiến của đợt niêm yết gần nhất có hộ đó (hộ chưa có ý kiến = chưa lấy ý kiến)."""
    chon = set(ds_ma_ho)
    ho = {r['ma_ho']: dict(r) for r in con.execute('SELECT ma_ho, thu_tu, ho_ten FROM ho') if r['ma_ho'] in chon}
    dots = {d['id']: d for d in du_thao.ds_dot(con)}
    moi = {}
    for r in con.execute('SELECT * FROM y_kien_du_thao ORDER BY dot_id, id'):
        if r['ma_ho'] in ho:
            moi[r['ma_ho']] = dict(r)
    doi_thoai = {}
    for r in con.execute('SELECT * FROM doi_thoai_ho ORDER BY dot_id, ma_ho, lan'):
        doi_thoai.setdefault((r['dot_id'], r['ma_ho']), []).append(dict(r))
    dem = {k: 0 for k, _ in du_thao.LOAI_Y_KIEN}
    for m in ho:
        dem[moi[m]['loai'] if m in moi and moi[m]['loai'] in dem else 'chua'] += 1
    kien_nghi = []
    for m in sorted(ho, key=lambda k: (ho[k]['thu_tu'], k)):
        y = moi.get(m)
        if y is None:
            continue
        dt = doi_thoai.get((y['dot_id'], m), [])
        if y['loai'] in KIEN_NGHI or y['noi_dung'] or y['ket_qua_doi_thoai'] or dt:
            ket_qua = '; '.join(x for x in [y['ket_qua_doi_thoai'], *(x['ket_luan'] for x in dt)] if x)
            kien_nghi.append(dict(ma_ho=m, ho_ten=ho[m]['ho_ten'], loai=y['loai'], nhom=du_thao.TEN_NHOM.get(y['nhom'], y['nhom']),
                                  noi_dung=y['noi_dung'], ket_qua=ket_qua, huong=y['huong_xu_ly'], so_lan_dt=len(dt),
                                  da_dong_thuan=y['loai'] == 'dong_y'))
    nhom = {}
    for k in kien_nghi:
        g = nhom.setdefault(k['nhom'] or 'Chưa phân nhóm', [0, 0])
        g[0] += 1
        g[1] += k['da_dong_thuan']
    return dict(so_ho=len(ho), dem=dem, kien_nghi=kien_nghi, nhom=nhom, so_ho_co_y_kien=len(ho) - dem['chua'],
                dot_ny=[dots[i] for i in sorted({y['dot_id'] for y in moi.values()}) if i in dots])


def _noi_dung(tt: dict) -> str:
    """Thân văn bản (XML w:body): đầu văn bản và chữ ký là chỗ trống {…} điền bằng van_ban_trinh.dien_docx."""
    p, r = vb._p, vb._r
    co = 13

    def doan(*chay, **k):
        return p(*chay, dau_dong=709, truoc=60, sau=60, dong=260, **k)

    def muc(chu):
        return p(r(chu, dam=True, co=co), can='left', truoc=160, sau=60, dong=260)

    def o_trai(chu, dam=False):
        return p(r(chu, dam=dam, co=11), can='left', sau=0, dong=240)
    d = tt['dem']
    n = tt['so_ho']
    t = [vb._dau_trang('Số: ………/BC-………', '{ngay_lap_chu}'),
         p(r('BÁO CÁO', dam=True, co=14), can='center', truoc=240, sau=0),
         p(r('Tổng hợp ý kiến, kết quả tiếp thu, giải trình dự thảo phương án bồi thường, hỗ trợ, tái định cư dự án {du_an} '
             '(Đối với {so_ho_02} trường hợp/ {so_thua} thửa đất/ {dt_thu_hoi}m²)', dam=True, co=co), can='center', sau=200, dong=260),
         p(r('Kính gửi: UBND {cap_dia_ban_thuong} {ten_dia_ban}; {co_quan_tham_dinh}.', co=co), can='left', sau=120),
         doan(r('Căn cứ Luật Đất đai năm 2024; Nghị định số 88/2024/NĐ-CP; Quyết định số 18/2026/QĐ-UBND ngày 19/6/2026 của '
                'UBND thành phố Đồng Nai quy định trình tự, thủ tục hành chính về đất đai;', co=co)),
         doan(r('{don_vi_lap} báo cáo kết quả niêm yết công khai, lấy ý kiến, đối thoại, tiếp thu, giải trình đối với dự thảo '
                'phương án bồi thường, hỗ trợ, tái định cư dự án {du_an} như sau:', co=co)),
         muc('I. Kết quả niêm yết công khai')]
    if tt['dot_ny']:
        for x in tt['dot_ny']:
            t.append(doan(r(f'- {x["ten"]}: niêm yết từ ngày {du_thao.hien_ngay(x["ngay_bat_dau"])} đến ngày '
                            f'{du_thao.hien_ngay(x["ngay_ket_thuc"])}' + (f' tại {x["dia_diem"]}' if x['dia_diem'] else '') +
                            (f'; biên bản bắt đầu số {x["so_bb_bat_dau"]}' if x['so_bb_bat_dau'] else '') +
                            (f', biên bản kết thúc số {x["so_bb_ket_thuc"]}' if x['so_bb_ket_thuc'] else '') +
                            (f'; họp dân ngày {du_thao.hien_ngay(x["ngay_hop"])}' if x['ngay_hop'] else '') + '.', co=co)))
    else:
        t.append(doan(r('Các hộ của đợt trình chưa được đưa vào đợt niêm yết công khai nào trong phần mềm.', co=co)))
    t.append(muc('II. Kết quả lấy ý kiến'))
    hang = [[o_trai('Chỉ tiêu', True), o_trai('Số hộ', True), o_trai('Tỷ lệ (%)', True)]]
    for ten, k in (('Đồng ý với dự thảo phương án', 'dong_y'), ('Có ý kiến khác', 'y_kien_khac'), ('Không đồng ý', 'khong_dong_y'),
                   ('Chưa lấy ý kiến', 'chua')):
        hang.append([o_trai(ten), o_trai(str(d[k])), o_trai(_pt(d[k], n))])
    hang.append([o_trai('Tổng số hộ của đợt trình', True), o_trai(str(n), True), o_trai('100,0' if n else '0,0', True)])
    t.append(vb._bang(hang, [5271, 1900, 1900]))
    t.append(muc('III. Nội dung kiến nghị, kết quả đối thoại, tiếp thu và giải trình'))
    if tt['kien_nghi']:
        hang = [[o_trai(x, True) for x in ('STT', 'Họ và tên', 'Nội dung kiến nghị', 'Đối thoại, giải trình', 'Kết quả')]]
        for i, k in enumerate(tt['kien_nghi'], start=1):
            nd = (f'[{k["nhom"]}] ' if k['nhom'] else '') + (k['noi_dung'] or '(chưa ghi nội dung)')
            gt = '\n'.join(x for x in (k['ket_qua'], k['huong']) if x) or '(chưa ghi)'
            hang.append([o_trai(str(i)), o_trai(k['ho_ten']), o_trai(nd), o_trai(gt),
                         o_trai('Đã đồng thuận' if k['da_dong_thuan'] else 'Chưa đồng thuận')])
        t.append(vb._bang(hang, [560, 1700, 2700, 2711, 1400]))
        if tt['nhom']:
            t.append(doan(r('Theo nhóm lý do kiến nghị: ' + '; '.join(f'{ten} {a} hộ (đã đồng thuận {b})' for ten, (a, b) in
                                                                    tt['nhom'].items()) + '.', nghieng=True, co=co)))
    else:
        t.append(doan(r('Không có hộ nào kiến nghị hoặc có ý kiến khác đối với dự thảo phương án.', co=co)))
    kn = d['khong_dong_y'] + d['y_kien_khac']
    t += [muc('IV. Kết luận, đề nghị'),
          doan(r(f'Trong {n} hộ của đợt trình, {d["dong_y"]} hộ ({_pt(d["dong_y"], n)}%) đồng ý; {kn} hộ có ý kiến khác hoặc chưa '
                 f'đồng ý; {d["chua"]} hộ chưa lấy ý kiến. Các kiến nghị đã được tiếp thu, giải trình như nêu trên. Kính đề nghị '
                 '{co_quan_tham_dinh} xem xét, thẩm định phương án bồi thường, hỗ trợ, tái định cư theo quy định./.', co=co)),
          p(r(' '), sau=120), vb._ky_ten()]
    return ''.join(t)


def ghi_docx(con, ds_ma_ho: list, file, dot=None) -> Path:
    """Lập báo cáo cho các hộ ds_ma_ho (hộ của đợt trình dot) -> file .docx."""
    chung, _ = vb.du_lieu(con, ds_ma_ho, dot)
    tam = Path(tempfile.mkdtemp(prefix='pabt_bc_'))
    try:
        mau = tam / 'mau.docx'
        mau.write_bytes(vb._goi_docx(_noi_dung(thu_thap(con, ds_ma_ho))))
        return vb.dien_docx(mau, file, chung, [])
    finally:
        shutil.rmtree(tam, ignore_errors=True)

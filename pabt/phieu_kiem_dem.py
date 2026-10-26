"""Phiếu kiểm đếm thực địa không cần mạng (0.9.87).

1. xuat_phieu_kiem_dem_html: MỘT file .html (mở bằng trình duyệt điện thoại / máy tính bảng, không cần Internet): danh sách hộ +
   thửa của dự án, gợi ý tên tài sản / cây / vật nuôi theo danh mục đơn giá; cán bộ ghi tài sản kiểm đếm (tự lưu trong trình duyệt)
   rồi bấm tải file kết quả .json.
2. nhap_ket_qua_kiem_dem: file .json -> phương án hộ (lap_pa.BoSoan) qua CÙNG đường "Dán danh sách tài sản" (khớp danh mục ->
   dòng danh mục, không khớp -> hạng mục ngoài danh mục; cây có số đo đường kính / chu vi -> quy cách). Mỗi hộ lưu một lần (một
   bước Hoàn tác), hộ đang mở chỉ xem / không tồn tại -> báo lỗi dòng.
3. gan_anh_hien_trang: quét thư mục ảnh, gắn ảnh vào hộ theo số CCCD / họ tên không dấu / "HO<stt>" trong tên file -> bảng
   anh_hien_trang (lược đồ v16). Tên trùng nhiều hộ: không gắn, báo lại.
Không Qt."""
from __future__ import annotations
import html
import json
import re
from datetime import datetime
from pathlib import Path

from . import csdl
from .lap_pa import LoiNhap, bo_dau

PHIEN_BAN_PHIEU = 1
MUC_PHIEU = ((2, 'Nhà, công trình'), (3, 'Cây trồng'), (7, 'Vật nuôi'))
DUOI_ANH = ('.jpg', '.jpeg', '.png', '.webp', '.bmp', '.heic', '.tif', '.tiff')
BANG_ANH = 'anh_hien_trang'
SQL_BANG_ANH = f'''CREATE TABLE IF NOT EXISTS {BANG_ANH} (
    id INTEGER PRIMARY KEY,
    ma_ho INTEGER NOT NULL REFERENCES ho(ma_ho) ON UPDATE CASCADE ON DELETE CASCADE,
    duong_dan TEXT NOT NULL,             -- đường dẫn đầy đủ của ảnh lúc gắn
    ten_file TEXT NOT NULL,
    khop_theo TEXT NOT NULL DEFAULT '',  -- cccd / ho_ten / stt
    luc TEXT NOT NULL,
    UNIQUE (ma_ho, duong_dan)
)'''


# ---------------------------------------------------------------- 1. xuất phiếu
def du_lieu_phieu(con) -> dict:
    """Dữ liệu nhúng vào phiếu: hộ (CCCD đã che - file nằm trên điện thoại), thửa, danh mục gợi ý theo mục."""
    from .an_toan import che_cccd
    thua = {}
    for r in con.execute('SELECT ma_ho, so_to, so_thua, loai_dat, dt_thu_hoi FROM thua ORDER BY thu_tu, ma_thua'):
        thua.setdefault(r['ma_ho'], []).append(f'Tờ {r["so_to"]} thửa {r["so_thua"]} {r["loai_dat"] or ""} '
                                               f'{r["dt_thu_hoi"] or ""} m²'.replace('  ', ' ').strip())
    ho = [dict(ma=r['ma_ho'], stt=r['thu_tu'], ten=' '.join(str(r['ho_ten'] or '').split()),
               cccd=che_cccd((r['so_cccd'] or '').strip()), dia_chi=' '.join(str(r['dia_chi'] or '').split()),
               thua=thua.get(r['ma_ho'], []))
          for r in con.execute('SELECT ma_ho, thu_tu, ho_ten, so_cccd, dia_chi FROM ho ORDER BY thu_tu, ma_ho')]
    goi_y = {2: [], 3: [], 7: []}
    for r in con.execute('SELECT nhom, phan_loai, ten, dvt FROM dm_taisan ORDER BY ma'):
        muc = 7 if 'vat nuoi' in bo_dau(r['phan_loai'] or '') else (r['nhom'] if r['nhom'] in (2, 3) else None)
        if muc is not None:
            goi_y[muc].append([r['ten'], r['dvt'] or ''])
    da = con.execute('SELECT ten FROM du_an WHERE id = 1').fetchone()
    return dict(du_an=(da['ten'] if da else '') or '', ho=ho, goi_y=goi_y)


def _json_trong_script(x) -> str:
    """JSON an toàn trong <script> (tên có '</script>' không đóng thẻ)."""
    return json.dumps(x, ensure_ascii=False).replace('</', '<\\/').replace('\u2028', '\\u2028').replace('\u2029', '\\u2029')


def xuat_phieu_kiem_dem_html(con, file_ra) -> Path:
    """Ghi file .html phiếu kiểm đếm. Trả đường dẫn."""
    du = du_lieu_phieu(con)
    ra = Path(file_ra)
    ra.parent.mkdir(parents=True, exist_ok=True)
    tieu = html.escape(du['du_an'] or 'Dự án')
    muc = ''.join(f'<option value="{m}">{html.escape(t)}</option>' for m, t in MUC_PHIEU)
    noi = (_HTML.replace('@@TIEU_DE@@', tieu).replace('@@MUC@@', muc).replace('@@SO_HO@@', str(len(du['ho'])))
           .replace('@@PHIEN_BAN@@', str(PHIEN_BAN_PHIEU)).replace('@@DU_LIEU@@', _json_trong_script(du)))
    tam = ra.with_name(ra.name + '.tmp')
    tam.write_text(noi, encoding='utf-8')
    tam.replace(ra)
    return ra


_HTML = '''<!DOCTYPE html>
<html lang="vi"><head><meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>Phiếu kiểm đếm - @@TIEU_DE@@</title>
<style>
*{box-sizing:border-box;font-family:"Segoe UI",Roboto,Arial,sans-serif}
body{margin:0;background:#F8FAFC;color:#0F172A}
header{background:#0F294A;color:#fff;padding:12px 14px;border-bottom:3px solid #F59E0B}
header h1{margin:0;font-size:16px}header p{margin:4px 0 0;font-size:12px;color:#E2E8F0}
.khung{max-width:760px;margin:10px auto;padding:0 10px 80px}
.the{background:#fff;border:1px solid #CBD5E1;border-radius:10px;padding:12px;margin-bottom:10px}
label{display:block;font-size:13px;font-weight:600;margin:6px 0 3px}
input,select{width:100%;padding:9px;border:1px solid #94A3B8;border-radius:6px;font-size:15px}
.hang{display:grid;grid-template-columns:1fr 1fr;gap:8px}
button{background:#2563EB;color:#fff;border:0;border-radius:6px;padding:11px 14px;font-size:15px;font-weight:600;margin-top:10px;width:100%}
button.phu{background:#64748B}button.luu{background:#107C41}
table{width:100%;border-collapse:collapse;margin-top:8px;font-size:13px}
th,td{border:1px solid #CBD5E1;padding:5px;text-align:left;vertical-align:top}th{background:#F1F5F9}
.nho{font-size:12px;color:#475569}
</style></head><body>
<header><h1>PHIẾU KIỂM ĐẾM THỰC ĐỊA</h1><p>@@TIEU_DE@@ · @@SO_HO@@ hộ · tự lưu trên máy này</p></header>
<div class="khung">
<div class="the"><label for="o_tim">Tìm hộ (tên, số thứ tự, địa chỉ - không cần dấu)</label>
<input id="o_tim" placeholder="Gõ để lọc…"/>
<label for="cb_ho">Hộ</label><select id="cb_ho"></select>
<div id="tt_ho" class="nho"></div></div>
<div class="the"><div class="hang"><div><label for="cb_muc">Loại</label><select id="cb_muc">@@MUC@@</select></div>
<div><label for="o_dvt">Đơn vị tính</label><input id="o_dvt" placeholder="m², cây, con…"/></div></div>
<label for="o_ten">Tên tài sản / cây / vật nuôi</label><input id="o_ten" list="goi_y" placeholder="Gõ vài chữ để chọn gợi ý"/>
<datalist id="goi_y"></datalist>
<div class="hang"><div><label for="o_sl">Số lượng (được ghi phép tính 4x5)</label><input id="o_sl" inputmode="decimal"/></div>
<div><label for="o_tl">Tỷ lệ %</label><input id="o_tl" inputmode="decimal" value="100"/></div></div>
<div class="hang"><div><label for="o_do">Đường kính / chu vi (cm, cây)</label><input id="o_do" placeholder="15, 18x2, 22"/></div>
<div><label for="cb_kieu">Số đo là</label><select id="cb_kieu"><option value="dk">Đường kính</option><option value="cv">Chu vi</option></select></div></div>
<label for="o_gc">Ghi chú / tên ảnh</label><input id="o_gc"/>
<button id="b_them" type="button">Thêm vào hộ đang chọn</button>
<table><thead><tr><th>Loại</th><th>Tên</th><th>SL</th><th>ĐVT</th><th>Ghi chú</th><th></th></tr></thead><tbody id="bang"></tbody></table></div>
<div class="the"><button class="luu" id="b_tai" type="button">Tải file kết quả (.json)</button>
<p class="nho">Gửi file .json về máy tính, trong phần mềm PABT chọn Công cụ → Phiếu kiểm đếm thực địa… → Nhập kết quả.</p>
<button class="phu" id="b_xoa" type="button">Xóa mọi kết quả đã ghi trên máy này</button></div>
</div>
<script>
"use strict";
const DU = @@DU_LIEU@@;
const KHOA = "pabt_kiem_dem_" + DU.du_an;
const TEN_MUC = {2: "Nhà", 3: "Cây", 7: "Vật nuôi"};
let KQ = {};
try { KQ = JSON.parse(localStorage.getItem(KHOA) || "{}") || {}; } catch (e) { KQ = {}; }
function luu() { try { localStorage.setItem(KHOA, JSON.stringify(KQ)); } catch (e) {} }
function boDau(s) { return (s || "").normalize("NFD").replace(/[\\u0300-\\u036f]/g, "").replace(/đ/g, "d").replace(/Đ/g, "D").toLowerCase(); }
const $ = id => document.getElementById(id);
function locHo() {
  const tk = boDau($("o_tim").value), cb = $("cb_ho"), cu = cb.value;
  cb.textContent = "";
  for (const h of DU.ho) {
    const chu = h.stt + ". " + h.ten + (h.dia_chi ? " - " + h.dia_chi : "");
    if (tk && !boDau(chu + " " + h.cccd).includes(tk)) continue;
    const o = document.createElement("option");
    o.value = String(h.ma); o.textContent = chu + (KQ[h.ma] && KQ[h.ma].length ? "  [" + KQ[h.ma].length + "]" : "");
    cb.appendChild(o);
  }
  if (cu) cb.value = cu;
  chonHo();
}
function hoDangChon() { const ma = $("cb_ho").value; return DU.ho.find(h => String(h.ma) === ma); }
function chonHo() {
  const h = hoDangChon();
  $("tt_ho").textContent = h ? ("CCCD: " + (h.cccd || "-") + " · " + h.thua.join("; ")) : "";
  veBang();
}
function goiY() {
  const dl = $("goi_y"); dl.textContent = "";
  for (const [ten, dvt] of (DU.goi_y[$("cb_muc").value] || [])) {
    const o = document.createElement("option"); o.value = ten; o.label = dvt; dl.appendChild(o);
  }
}
function them() {
  const h = hoDangChon(), ten = $("o_ten").value.trim(), sl = $("o_sl").value.trim(), dk = $("o_do").value.trim();
  if (!h || !ten || (!sl && !dk)) { alert("Chọn hộ, ghi tên và số lượng (hoặc số đo)."); return; }
  const muc = parseInt($("cb_muc").value, 10);
  let dvt = $("o_dvt").value.trim();
  const gy = (DU.goi_y[muc] || []).find(x => x[0] === ten);
  if (!dvt && gy) dvt = gy[1];
  (KQ[h.ma] = KQ[h.ma] || []).push({muc: muc, ten: ten, dvt: dvt, so_luong: sl, ty_le: $("o_tl").value.trim(),
    so_do: dk, kieu: $("cb_kieu").value, ghi_chu: $("o_gc").value.trim(), luc: new Date().toISOString()});
  luu();
  for (const id of ["o_ten", "o_sl", "o_do", "o_gc", "o_dvt"]) $(id).value = "";
  locHo();
}
function veBang() {
  const h = hoDangChon(), tb = $("bang"); tb.textContent = "";
  ((h && KQ[h.ma]) || []).forEach((d, i) => {
    const tr = document.createElement("tr");
    for (const x of [TEN_MUC[d.muc] || d.muc, d.ten + (d.so_do ? " (" + d.so_do + " cm)" : ""), d.so_luong, d.dvt, d.ghi_chu]) {
      const td = document.createElement("td"); td.textContent = x; tr.appendChild(td);
    }
    const td = document.createElement("td"), b = document.createElement("button");
    b.textContent = "Xóa"; b.className = "phu"; b.style.margin = "0"; b.style.padding = "4px";
    b.onclick = () => { KQ[h.ma].splice(i, 1); luu(); locHo(); };
    td.appendChild(b); tr.appendChild(td); tb.appendChild(tr);
  });
}
function taiVe() {
  const ra = {phien_ban: @@PHIEN_BAN@@, du_an: DU.du_an, luc: new Date().toISOString(), ket_qua: KQ};
  const a = document.createElement("a");
  a.href = URL.createObjectURL(new Blob([JSON.stringify(ra, null, 1)], {type: "application/json"}));
  a.download = "ket_qua_kiem_dem.json"; document.body.appendChild(a); a.click(); a.remove();
}
$("o_tim").addEventListener("input", locHo);
$("cb_ho").addEventListener("change", chonHo);
$("cb_muc").addEventListener("change", goiY);
$("b_them").addEventListener("click", them);
$("b_tai").addEventListener("click", taiVe);
$("b_xoa").addEventListener("click", () => { if (confirm("Xóa mọi kết quả đã ghi trên máy này?")) { KQ = {}; luu(); locHo(); } });
goiY(); locHo();
</script></body></html>
'''


# ---------------------------------------------------------------- 2. nhập kết quả
# File .json của phiếu: phien_ban 1 = {"ket_qua": {"<mã hộ>": [dòng]}}; phien_ban 2 (1.0.32, ứng dụng di động) thêm "ho_dan" {khóa: thông
# tin hộ} và "dat_dai" {khóa: [thửa / lô rừng]} - khóa là mã hộ của dự án (phiếu xuất từ dự án) hoặc "moi_<n>" (hộ ghi mới ở thực địa).
# Dòng: muc 2 / 3 / 7, ma_dm (mã bộ đơn giá đã chọn trên điện thoại - có thì áp thẳng), ten, dvt, so_luong, ty_le, so_do, kieu, ghi_chu.
NGUONG_TEN = 0.88                   # độ giống họ tên (difflib) tối thiểu khi khớp hộ theo tên


def _doc_file_phieu(file) -> dict:
    from .an_toan import LoiAnToan, kiem_tra_magic_bytes
    try:
        kiem_tra_magic_bytes(file, {'json'})            # 1.0.32: .json nhận qua Zalo / USB thật ra là chương trình / file khác
    except LoiAnToan as e:
        raise LoiNhap(str(e)) from None
    try:
        du = json.loads(Path(file).read_text(encoding='utf-8-sig'))
    except (OSError, ValueError) as e:
        raise LoiNhap(f'Không đọc được file kết quả kiểm đếm: {e}') from None
    if not isinstance(du, dict) or not isinstance(du.get('ket_qua'), dict):
        raise LoiNhap('File không phải kết quả của Phiếu kiểm đếm LARC (thiếu "ket_qua").')
    return du


def _dong_hop_le(ds) -> list:
    return [d for d in ds if isinstance(d, dict) and str(d.get('ten') or '').strip()] if isinstance(ds, list) else []


def doc_phieu(file) -> dict:
    """File .json (phiên bản 1 / 2) -> {'du_an', 'nam' (năm kiểm đếm - đổi "trồng năm …" ra năm tuổi), 'ho': [{'khoa', 'ma_ho' (int /
    None), 'thong_tin' {ho_ten, so_cccd, nguoi_su_dung, …}, 'thua' [{so_to, so_thua, tieu_khu, khoanh, lo, …}], 'dong' [dòng]}]}."""
    du = _doc_file_phieu(file)
    ho_dan = du.get('ho_dan') if isinstance(du.get('ho_dan'), dict) else {}
    dat_dai = du.get('dat_dai') if isinstance(du.get('dat_dai'), dict) else {}
    nam = None
    m = re.match(r'\s*(\d{4})-', str(du.get('luc') or ''))
    if m:
        nam = int(m.group(1))
    ho = []
    for khoa, ds in du['ket_qua'].items():
        tt = ho_dan.get(khoa) if isinstance(ho_dan.get(khoa), dict) else {}
        ma = tt.get('ma_ho', khoa)
        try:
            ma = int(str(ma).strip())
        except (TypeError, ValueError):
            ma = None
        thua = [t for t in (dat_dai.get(khoa) or []) if isinstance(t, dict)]
        ho.append(dict(khoa=str(khoa), ma_ho=ma, thong_tin=tt, thua=thua, dong=_dong_hop_le(ds)))
    return dict(du_an=str(du.get('du_an') or ''), nam=nam, ho=ho)


def _so(x) -> str:
    """Số hiệu tờ / thửa / lô so khớp: chữ thường, bỏ dấu cách / dấu ngăn, bỏ số 0 đầu mỗi nhóm số ("Tờ 05" = "5", "TK126-K6" =
    "tk126/k6")."""
    s = re.sub(r'[^0-9a-z]+', '', bo_dau(str(x or '')).lower())
    return re.sub(r'(?<![0-9])0+(?=[0-9])', '', s)


def khoa_lo_rung(tieu_khu, khoanh) -> str:
    """Số "tờ" của lô rừng ghi trong bảng thửa: 'TK126/K6' (lô = số thửa) - cách ghi chung khi tạo hộ từ phiếu kiểm đếm."""
    return f'TK{str(tieu_khu).strip()}/K{str(khoanh).strip()}'


def _khoa_ten_ho(ten: str) -> str:
    t = re.split(r'\s+(?:là|và|cùng)\s+', str(ten or ''), maxsplit=1)[0]
    t = re.sub(r'^(?:ông|bà|anh|chị|cô|chú|hộ|hộ\s+ông|hộ\s+bà)\s+', '', t.strip(), flags=re.I)
    return ' '.join(re.sub(r'[^a-z0-9 ]+', ' ', bo_dau(t).lower()).split())


class ChiMucHo:
    """Chỉ mục hộ của dự án dựng MỘT lần cho cả file phiếu (CCCD, tờ / thửa, họ tên, mã hộ)."""

    def __init__(self, con):
        from .nhap_excel import chuan_cccd
        self.cccd, self.thua, self.ten, self.ma = {}, {}, {}, set()
        for r in con.execute('SELECT ma_ho, ho_ten, so_cccd FROM ho'):
            self.ma.add(r['ma_ho'])
            so = chuan_cccd(re.sub(r'\D', '', r['so_cccd'] or ''))
            if len(so) >= 9:
                self.cccd.setdefault(so, set()).add(r['ma_ho'])
            k = _khoa_ten_ho(r['ho_ten'])
            if k:
                self.ten.setdefault(k, set()).add(r['ma_ho'])
        for r in con.execute('SELECT ma_ho, so_to, so_thua FROM thua'):
            self.thua.setdefault((_so(r['so_to']), _so(r['so_thua'])), set()).add(r['ma_ho'])


def _tang_cccd(cm, tt) -> set:
    from .nhap_excel import chuan_cccd
    kq = set()
    for k in ('so_cccd', 'cccd_nguoi_su_dung', 'cccd'):
        so = chuan_cccd(re.sub(r'\D', '', str(tt.get(k) or '')))
        if len(so) >= 9:
            kq |= cm.cccd.get(so, set())
    return kq


def _tang_thua(cm, tt, thua) -> set:
    ds = list(thua) or [tt]
    kq = set()
    for t in ds:
        lo, to, so = t.get('lo') or t.get('lo_kk'), t.get('so_to'), t.get('so_thua')
        khoa = []
        if to not in (None, '') and so not in (None, ''):
            khoa.append((_so(to), _so(so)))
        if lo not in (None, '') and (t.get('tieu_khu') or t.get('khoanh')):
            tk, kh = t.get('tieu_khu') or '', t.get('khoanh') or ''
            for to2 in (khoa_lo_rung(tk, kh), f'{tk}/{kh}', kh, tk):
                if _so(to2):
                    khoa.append((_so(to2), _so(lo)))
        for k in khoa:
            kq |= cm.thua.get(k, set())
    return kq


def _tang_ten(cm, tt, ten_file) -> set:
    from difflib import SequenceMatcher
    ten = [_khoa_ten_ho(tt.get(k)) for k in ('ho_ten', 'nguoi_su_dung', 'nguoi_nhan_khoan')]
    if ten_file:
        ten.append(_khoa_ten_ho(re.sub(r'[_\-.]+', ' ', Path(str(ten_file)).stem)))
    ten = [x for x in ten if len(x.split()) >= 2]
    kq = set()
    for t in ten:
        kq |= cm.ten.get(t, set())
    if kq:
        return kq
    tot, diem = set(), NGUONG_TEN
    for t in ten:
        for k, ma in cm.ten.items():
            r = SequenceMatcher(None, t, k).ratio()
            if r > diem + 1e-9:
                tot, diem = set(ma), r
            elif abs(r - diem) <= 1e-9 and r >= NGUONG_TEN:
                tot |= ma
    return tot


def tim_ho_khop_json(con, du_lieu_ho: dict, ten_file: str = '', chi_muc=None) -> tuple:
    """Hộ trong dự án ứng với một hộ của phiếu kiểm đếm -> (mã hộ | None, tầng khớp, các mã ứng viên). 4 tầng ưu tiên:
    (1) số CCCD (chủ hộ / người sử dụng) - (2) tờ / thửa hoặc tiểu khu / khoảnh / lô - (3) họ tên không dấu (chủ hộ, người sử dụng, tên
    file "Nguyen_Van_A.json"; giống >= NGUONG_TEN) - (4) mã hộ của phiếu. Tầng ra nhiều hộ thì thu hẹp bằng các tầng sau; tầng
    không ra hộ nào thì xét tầng sau. Không ra đúng một hộ -> (None, '', ứng viên)."""
    cm = chi_muc or ChiMucHo(con)
    tt = du_lieu_ho.get('thong_tin') if isinstance(du_lieu_ho.get('thong_tin'), dict) else du_lieu_ho
    thua = du_lieu_ho.get('thua') or du_lieu_ho.get('dat_dai') or []
    ma = du_lieu_ho.get('ma_ho')
    tang = [('cccd', lambda: _tang_cccd(cm, tt)), ('thua', lambda: _tang_thua(cm, tt, thua)),
            ('ho_ten', lambda: _tang_ten(cm, tt, ten_file)),
            ('ma_ho', lambda: {int(ma)} & cm.ma if str(ma or '').strip().isdigit() else set())]
    ung, ten_tang = None, ''
    for ten, ham in tang:
        s = ham()
        if not s:
            continue
        if ung is None:
            ung, ten_tang = set(s), ten
        elif ung & s:
            ung, ten_tang = ung & s, f'{ten_tang}+{ten}'
        if len(ung) == 1:
            return next(iter(ung)), ten_tang, sorted(ung)
    return None, '', sorted(ung or ())


def _tao_ho(con, h: dict) -> int:
    """Hộ ghi mới ở thực địa (không khớp hộ nào) -> thêm vào dự án: họ tên, CCCD, địa chỉ, điện thoại, người sử dụng (ghi chú), thửa /
    lô rừng (lô: tờ = "TK<tiểu khu>/K<khoảnh>", thửa = lô, DT ha -> m²)."""
    from decimal import Decimal, InvalidOperation
    from .ho_so import luu_ho
    tt = h['thong_tin']
    ten = ' '.join(str(tt.get('ho_ten') or tt.get('nguoi_nhan_khoan') or tt.get('nguoi_su_dung') or '').split())
    if not ten:
        raise LoiNhap('Hộ ghi mới ở thực địa chưa có họ tên.')
    gc = [str(tt.get('ghi_chu') or '').strip()]
    if tt.get('nguoi_su_dung') and str(tt['nguoi_su_dung']).strip() != ten:
        gc.append(f'Người sử dụng: {str(tt["nguoi_su_dung"]).strip()}')
    thong_tin = dict(ho_ten=ten, so_cccd=re.sub(r'\D', '', str(tt.get('so_cccd') or '')), dia_chi=str(tt.get('dia_chi') or ''),
                     dien_thoai=str(tt.get('sdt') or tt.get('dien_thoai') or ''), ghi_chu='; '.join(x for x in gc if x))
    ds = []
    for t in h['thua']:
        lo = t.get('lo') or t.get('lo_kk')
        if lo and (t.get('tieu_khu') or t.get('khoanh')):
            to, so = khoa_lo_rung(t.get('tieu_khu') or '', t.get('khoanh') or ''), str(lo)
        else:
            to, so = str(t.get('so_to') or ''), str(t.get('so_thua') or '')
        dt = str(t.get('dt_thu_hoi') or '')
        if not dt and t.get('dt_ha') not in (None, ''):
            try:
                dt = str(Decimal(str(t['dt_ha']).replace(',', '.')) * 10000).replace('.', ',')
            except InvalidOperation:
                dt = ''
        if to or so:
            ds.append(dict(ma_thua=None, so_to=to, so_thua=so, loai_dat=str(t.get('loai_dat') or ''), dt_thu_hoi=dt or '0'))
    return luu_ho(con, None, thong_tin, ds)


def _mo_rong_dong(ds: list) -> list:
    """Dòng ghi gộp nhiều cỡ (tên "Ống nhựa: ϕ114: 3300m; ϕ90: 3400m", ô số lượng trống) -> từng dòng (tach_dong_qd42)."""
    from .hieu_tai_san import tach_dong_qd42
    ra = []
    for d in ds:
        ten = str(d.get('ten') or '')
        con = tach_dong_qd42(ten) if not str(d.get('so_luong') or '').strip() and not d.get('ma_dm') else [ten]
        if len(con) > 1:
            ra.extend(dict(d, ten=x) for x in con)
        else:
            ra.append(d)
    return ra


def nhap_ket_qua_kiem_dem(con, file, dm=None, tao_ho_moi: bool = False, chi=None) -> dict:
    """Thêm các dòng kiểm đếm vào phương án từng hộ (BoSoan, lưu mỗi hộ một lần). Hộ của phiếu khớp hộ dự án bằng tim_ho_khop_json;
    không khớp: tao_ho_moi -> thêm hộ mới, không thì báo lại ở 'chua_khop' (màn hình hỏi rồi gọi lại với chi = các khóa đó).
    Trả {'so_ho', 'so_dong', 'loi': [chữ], 'khop': [(khóa, mã hộ, tầng)], 'chua_khop': [{khoa, ten, so_dong}], 'tao_moi'}."""
    from .lap_pa import BoSoan, DanhMuc
    from .nhap_tai_san import DichPhuongAn, them_dong_tho, them_mot
    from .cay_trong import BangCayDK
    from .hieu_tai_san import bo_sung, la_dong_tu_nhien, loai_cay_dk, tach_dong
    from .phan_loai_tai_san import LOAI, BoPhanLoai
    phieu = doc_phieu(file)
    dm = dm or DanhMuc(con)
    pl = BoPhanLoai(dm)
    cm = ChiMucHo(con)
    so_ho = so_dong = tao_moi = 0
    loi, khop, chua = [], [], []
    for h in phieu['ho']:
        if chi is not None and h['khoa'] not in chi:
            continue
        ds = _mo_rong_dong(h['dong'])
        if not ds and not (tao_ho_moi and h['thong_tin']):
            continue
        # tên file ("Nguyen_Van_A.json") chỉ là tên hộ khi file có MỘT hộ (file cả dự án: tên file không nói hộ nào)
        ma_ho, tang, ung = tim_ho_khop_json(con, h, Path(file).name if len(phieu['ho']) == 1 else '', cm)
        ten_ho = str(h['thong_tin'].get('ho_ten') or h['thong_tin'].get('nguoi_su_dung') or f'Mã hộ {h["khoa"]}')
        if ma_ho is None:
            if tao_ho_moi:
                try:
                    ma_ho, tang = _tao_ho(con, h), 'tao_moi'
                except LoiNhap as e:
                    loi.append(f'{ten_ho}: {e}')
                    continue
                tao_moi += 1
                cm = ChiMucHo(con)
            else:
                chua.append(dict(khoa=h['khoa'], ten=ten_ho, so_dong=len(ds), ung_vien=ung))
                loi.append(f'{ten_ho}: không khớp hộ nào trong dự án' + (f' ({len(ung)} hộ giống nhau - chọn tay)' if ung else '')
                           + f' ({len(ds)} dòng chưa nhập).')
                continue
        khop.append((h['khoa'], ma_ho, tang))
        bo = BoSoan(con, ma_ho, dm)
        dich = DichPhuongAn(bo)
        n = 0
        for k, d in enumerate(ds, 1):
            ten, dvt = ' '.join(str(d.get('ten') or '').split()), str(d.get('dvt') or '').strip()
            sl, tl, gc = str(d.get('so_luong') or '').strip(), str(d.get('ty_le') or '').strip(), str(d.get('ghi_chu') or '').strip()
            do, kieu = str(d.get('so_do') or '').strip(), str(d.get('kieu') or 'dk')
            tuoi = ''
            try:
                muc = int(d.get('muc') or 2)
            except (TypeError, ValueError):
                muc = 2
            if muc not in (2, 3, 7):
                muc = 2
            try:
                tl = tl if tl and tl != '100' else ''
                m_dm = dm.lay(str(d.get('ma_dm') or '').strip()) if d.get('ma_dm') else None
                if m_dm is not None and m_dm.nhom in (2, 3, 7):     # mã đơn giá đã chọn trên điện thoại: áp thẳng (1.0.32)
                    if m_dm.nhom == 3 and do:
                        them_mot(dich, 3, m_dm, ten, sl, tl, 'cv' if kieu == 'cv' else 'dk', gc, do)
                    else:
                        them_dong_tho(dich, m_dm.nhom, m_dm, ten, dvt, sl, tl, gc)
                    n += 1
                    continue
                # ô tên ghi cả câu ("Xoài: 16 cây, 17 năm tuổi", "Tràm 35c/15cm"): tách như hộp Dán danh sách - ô trống lấy theo câu
                t = tach_dong(ten, phieu['nam']) if la_dong_tu_nhien(ten) else None
                if t is not None:
                    ten, dvt, sl, tl = t['ten'], dvt or t['dvt'], sl or t['so_luong'], tl or t['ty_le']
                    do, tuoi = do or t['so_do'], t['tuoi']
                    kieu = t['kieu'] or kieu
                    gc = '; '.join(x for x in (gc, t['ghi_chu']) if x)
                if muc == 3 and do:                     # cây theo số đo: loại cây trong bảng quy cách ("Tràm" -> "Keo lá tràm")
                    loai_cay = loai_cay_dk(BangCayDK(dm.muc.get(3, [])), ten) or ten
                    them_mot(dich, 3, ('nhom', loai_cay), ten, sl, tl, 'cv' if kieu == 'cv' else 'dk', gc, do)
                else:
                    # cùng bộ hiểu với hộp Dán danh sách: năm tuổi -> mục đúng năm, khớp theo từ, ống / giếng theo cỡ, "… tính bằng …"
                    kq = bo_sung(pl, dm, dict(ten=ten, dvt=dvt, tuoi=tuoi, so_luong=sl), pl.phan_loai(ten, dvt))
                    m = kq.khop if kq.khop is not None and LOAI[kq.loai][0] == muc else None
                    them_dong_tho(dich, muc, m, ten, dvt, sl, tl, '; '.join(x for x in (gc, kq.ghi_them) if x))
                n += 1
            except LoiNhap as e:
                loi.append(f'{ten_ho} - dòng {k} "{ten[:40]}": {e}')
        if n:
            bo.luu()
            so_ho += 1
            so_dong += n
    with csdl.giao_dich(con):
        csdl.ghi_nhat_ky(con, 'Nhập kết quả kiểm đếm thực địa', f'{Path(file).name}: {so_ho} hộ, {so_dong} dòng'
                         + (f', thêm {tao_moi} hộ mới' if tao_moi else ''))
    return dict(so_ho=so_ho, so_dong=so_dong, loi=loi, khop=khop, chua_khop=chua, tao_moi=tao_moi)


# ---------------------------------------------------------------- 3. ảnh hiện trạng
def dam_bao_bang_anh(con) -> bool:
    if con.execute("SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?", (BANG_ANH,)).fetchone():
        return True
    with csdl.giao_dich(con):
        con.execute(SQL_BANG_ANH)
    return True


def _khoa_ten(s: str) -> str:
    return re.sub(r'[^a-z0-9]+', '_', bo_dau(s or '').lower()).strip('_')


def gan_anh_hien_trang(con, thu_muc) -> dict:
    """Gắn ảnh trong thư mục (cả thư mục con) vào hộ. Trả {'so_anh', 'da_gan', 'chua_khop': [tên file + lý do]}."""
    from .an_toan import LOAI_ANH, LoiAnToan, kiem_tra_magic_bytes
    tm = Path(thu_muc)
    if not tm.is_dir():
        raise LoiNhap(f'Không có thư mục ảnh: {tm}')
    cccd, ten, stt = {}, {}, {}
    for r in con.execute('SELECT ma_ho, thu_tu, ho_ten, so_cccd FROM ho'):
        so = re.sub(r'\D', '', r['so_cccd'] or '')
        if len(so) >= 9:
            cccd.setdefault(so, set()).add(r['ma_ho'])
        k = _khoa_ten(' '.join(str(r['ho_ten'] or '').split(' là ')[0].split()))
        if k.count('_') >= 1:                           # ít nhất 2 chữ (họ + tên)
            ten.setdefault(k, set()).add(r['ma_ho'])
        stt[str(r['thu_tu'])] = r['ma_ho']
    dam_bao_bang_anh(con)
    luc = datetime.now().isoformat(timespec='seconds')
    so_anh, gan, chua = 0, 0, []
    with csdl.giao_dich(con):
        for f in sorted(tm.rglob('*')):
            if not f.is_file() or f.suffix.lower() not in DUOI_ANH:
                continue
            so_anh += 1
            try:                                        # 1.0.32: đuôi ảnh mà nội dung không phải ảnh (chương trình đổi đuôi…) -> không gắn
                kiem_tra_magic_bytes(f, LOAI_ANH)
            except LoiAnToan as e:
                chua.append(f'{f.name}: {e}')
                continue
            goc = _khoa_ten(f.stem)
            ma, theo = set(), ''
            for so in re.findall(r'\d{9,12}', f.stem):
                if so in cccd:
                    ma, theo = cccd[so], 'cccd'
                    break
            if not ma:
                for k, ds in ten.items():
                    if re.search(r'(^|_)' + re.escape(k) + r'(_|$)', goc):
                        if ma and ma != ds:                 # khớp tên của hai hộ khác nhau
                            ma = ma | ds
                        else:
                            ma = ds
                        theo = 'ho_ten'
            if not ma:
                m = re.match(r'^ho_?0*(\d+)(_|$)', goc)
                if m and m.group(1) in stt:
                    ma, theo = {stt[m.group(1)]}, 'stt'
            if len(ma) != 1:
                chua.append(f'{f.name}: ' + ('trùng tên nhiều hộ' if ma else 'không nhận ra hộ (đặt tên ảnh theo CCCD, họ tên hoặc HO<số thứ tự>)'))
                continue
            gan += con.execute(f'INSERT OR IGNORE INTO {BANG_ANH} (ma_ho, duong_dan, ten_file, khop_theo, luc) VALUES (?, ?, ?, ?, ?)',
                               (next(iter(ma)), str(f.resolve()), f.name, theo, luc)).rowcount
        csdl.ghi_nhat_ky(con, 'Gắn ảnh hiện trạng', f'{tm}: {gan} ảnh mới / {so_anh} ảnh')
    return dict(so_anh=so_anh, da_gan=gan, chua_khop=chua)


def anh_cua_ho(con, ma_ho: int) -> list:
    if not con.execute("SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?", (BANG_ANH,)).fetchone():
        return []
    return [dict(r) for r in con.execute(f'SELECT * FROM {BANG_ANH} WHERE ma_ho = ? ORDER BY ten_file', (ma_ho,))]


def so_anh_theo_ho(con) -> dict:
    if not con.execute("SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?", (BANG_ANH,)).fetchone():
        return {}
    return {r[0]: r[1] for r in con.execute(f'SELECT ma_ho, COUNT(*) FROM {BANG_ANH} GROUP BY ma_ho')}

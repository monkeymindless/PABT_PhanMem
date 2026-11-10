"""Sơ đồ phần mềm dạng TÒA NHÀ (05/11/2026) -> graphify-out/so_do_toa_nha.html (một file, không cần mạng).

    python tao_so_do_toa_nha.py

Tầng = lớp kiến trúc, phòng = mảng nghiệp vụ, bàn làm việc = một module pabt/*.py (bàn càng to, file càng nhiều dòng). Bấm một bàn: nối dây tới
các module nó dùng và các module dùng nó. Liên kết lấy CHÍNH XÁC từ lệnh import (ast, cả import trong hàm), không đoán; số nút đồ thị lấy
từ graphify-out/graph.json nếu có. Module mới chưa xếp phòng: in cảnh báo và hiện ở phòng "Chưa xếp phòng". Chỉ thư viện chuẩn."""
from __future__ import annotations

import ast
import json
from collections import Counter
from pathlib import Path

GOC = Path(__file__).resolve().parent
RA = GOC / 'graphify-out' / 'so_do_toa_nha.html'

TANG = (
    ('Tầng 4 · Sảnh và khung giao diện', 'Người dùng đi vào từ đây: cửa sổ chính, bảng lệnh, hệ thiết kế dùng chung.', (
        ('Sảnh chính', 'Cửa sổ chính, bảng lệnh, tổng quan, tìm nhanh, trợ lý',
         'app lenh thanh_tieu_de man_hinh_tong_quan tong_quan_du_an man_hinh_tim_nhanh man_hinh_tro_ly tro_ly'),
        ('Phòng thiết kế', 'Màu, kiểu, nút, bảng lớn, thông báo',
         'giao_dien chu_de man_hinh_giao_dien ve_bieu_tuong thong_bao bang_ao luoi_bang'),
    )),
    ('Tầng 3 · Quy trình bồi thường', 'Các phòng đi theo thứ tự công việc của một dự án thu hồi đất.', (
        ('1. Dự án và hồ sơ hộ', 'Tạo dự án, hộ, thửa, tiếp nhận pháp lý, kiểm tra lỗi',
         'du_an_moi man_hinh_du_an_moi ho_so man_hinh_ho_so ho_so_scan man_hinh_ho_so_scan tiep_nhan_phap_ly man_hinh_tiep_nhan to_chuc '
         'so_sanh_ho kiem_loi'),
        ('2. Lập phương án', 'Tính tiền từng hộ: đất, nhà, cây, hỗ trợ, thưởng',
         'lap_pa lan_pa phien_ban_pa man_hinh_phien_ban nghiep_vu man_hinh man_hinh_phu_lap_pa chinh_sach cay_trong man_hinh_cay hieu_tai_san ma_tai_san phan_loai_tai_san '
         'man_hinh_phan_loai loai_dat chuan_ten_cay ten_cay_lam_nghiep nhap_tai_san hang_nhap_nhanh bang_dieu_chinh'),
        ('3. Niêm yết, lấy ý kiến', 'Đợt niêm yết, ý kiến, đối thoại, vận động',
         'du_thao man_hinh_du_thao van_ban_dot man_hinh_van_ban_dot bao_cao_y_kien van_dong thoi_han'),
        ('4. Trình duyệt, theo dõi', 'Đợt trình, quyết định, chi trả, bàn giao, báo cáo, khái toán',
         'quan_ly man_hinh_quan_ly theo_doi man_hinh_theo_doi quy_trinh quy_trinh_qd18 man_hinh_quy_trinh pheu_tien_do bao_cao_gpmb '
         'man_hinh_bao_cao man_hinh_thong_ke doi_chieu kinh_phi_du_an du_toan man_hinh_du_toan van_ban_trinh'),
    )),
    ('Tầng 2 · Phòng chuyên môn', 'Các phòng phục vụ mọi bước của quy trình.', (
        ('Đơn giá và giá đất', 'Bộ đơn giá, bảng giá NQ 28, hệ số K, tính giá QĐ 03, văn bản căn cứ',
         'don_gia don_gia_rieng man_hinh_don_gia man_hinh_don_gia_rieng dong_bo_don_gia khu_vuc_gia quan_tri_bo gia_dat_nq28 gia_dat_qd03 '
         'man_hinh_tinh_gia_dat man_hinh_gia_dat he_so_k man_hinh_he_so_k cap_nhat_gia_dat nguon_gia_dat nguon_luoi quy_tac_vi_tri '
         'nhap_don_gia man_hinh_nhap_don_gia phan_tich_ai_don_gia quy_dinh_van_ban van_ban_can_cu goi_gia_dat man_hinh_goi_gia_dat'),
        ('Quét và nhập file', 'Bộ quét chung, Tesseract, đọc PDF, Word, Excel',
         'quet_chung man_hinh_quet_chung ocr ocr_ho_so man_hinh_ocr pdf_bang pdf_du_phong doc_xls nhap_excel nhap_tho nhap_chi_tiet '
         'man_hinh_nhap_chi_tiet man_hinh_ghep_cot'),
        ('In và xuất bản', 'Bản Word, bảng tổng hợp Excel, PDF, mẫu in',
         'in_phien_ban in_an in_word in_excel in_excel_chi_tiet in_duong_ke du_lieu_in mau_bang_tong_hop openxml_word docx_sang_pdf ghi_xlsx_nhanh '
         'man_hinh_xuat_ban man_hinh_quan_ly_mau goi_mau ma_qr xem_truoc_tai_lieu'),
        ('Bản đồ và thực địa', 'CAD, KML, nền bản đồ, phiếu kiểm đếm, nhận qua Wi-Fi',
         'ban_do_cad ban_do_kml ban_do_luu dxf_thuan nen_ban_do sua_font_kml toa_do man_hinh_ban_do phieu_kiem_dem man_hinh_kiem_dem '
         'nhan_wifi man_hinh_nhan_wifi'),
    )),
    ('Tầng 1 · Hạ tầng', 'Nền móng: mọi tầng trên đều đứng trên các phòng này.', (
        ('Kho dữ liệu', 'File .pabt (SQLite), tiền Decimal, hoàn tác, mốc khôi phục',
         '__init__ csdl tien hoan_tac co_may_thoi_gian man_hinh_co_may_thoi_gian chua_benh_csdl man_hinh_chan_doan khoa'),
        ('An ninh và kiểm toán', 'Phân quyền, nhật ký chuỗi băm, kiểm tra file nhận từ ngoài',
         'an_toan kiem_toan man_hinh_kiem_toan phan_quyen ban_quyen'),
        ('Máy chủ và cập nhật', 'Máy chủ LAN, gói cập nhật',
         'may_chu man_hinh_may_chu cap_nhat cap_nhat_web man_hinh_cap_nhat lich_su_cap_nhat'),
        ('Cấu hình đơn vị', 'Hồ sơ địa phương, gói cho nhiều đơn vị',
         'dia_phuong man_hinh_cau_hinh goi_don_vi man_hinh_goi_don_vi'),
    )),
)
KHU_PHU = (('tests', 'Khu kiểm thử', 'tests/*.py'), ('di_dong', 'LARC Mobile', 'di_dong/**/*.py'),
           ('bo_cai_win', 'Xưởng đóng gói', 'bo_cai_win/*.py'), ('.', 'Công cụ ở thư mục gốc', '*.py'))
NGUONG_LON = 3000      # dòng: bàn được đánh dấu "file lớn"


def doc_module() -> dict:
    """{tên: {'dong': số dòng, 'dung': set module pabt được import}} - cả import trong hàm."""
    kq = {}
    thu_muc = GOC / 'pabt'
    co = {p.stem for p in thu_muc.glob('*.py')}
    for p in sorted(thu_muc.glob('*.py')):
        nguon = p.read_text(encoding='utf-8', errors='replace')
        dung = set()
        for n in ast.walk(ast.parse(nguon)):
            if isinstance(n, ast.ImportFrom):
                if n.level == 1 and n.module:
                    dung.add(n.module.split('.')[0])
                elif n.level == 1:
                    dung.update(a.name for a in n.names)
                elif n.level == 0 and n.module and n.module.split('.')[0] == 'pabt':
                    con = n.module.split('.')[1:]
                    if con:
                        dung.add(con[0])
                    else:
                        dung.update(a.name for a in n.names)
            elif isinstance(n, ast.Import):
                for a in n.names:
                    t = a.name.split('.')
                    if t[0] == 'pabt' and len(t) > 1:
                        dung.add(t[1])
        kq[p.stem] = {'dong': nguon.count('\n') + 1, 'dung': (dung & co) - {p.stem}}
    return kq


def doc_do_thi() -> tuple:
    """(số nút đồ thị mỗi module, thống kê) từ graph.json; không có file: rỗng."""
    p = GOC / 'graphify-out' / 'graph.json'
    if not p.exists():
        return Counter(), {}
    d = json.loads(p.read_text(encoding='utf-8'))
    nut = Counter()
    for n in d['nodes']:
        f = (n.get('source_file') or '').replace('\\', '/')
        if f.startswith('pabt/') and f.endswith('.py'):
            nut[f[5:-3]] += 1
    return nut, {'tong': len(d['nodes']), 'canh': len(d.get('links', ()))}


def dung_du_lieu() -> dict:
    md = doc_module()
    nut, tk = doc_do_thi()
    da_xep = set()
    tang = []
    for ten, mo_ta, phong in TANG:
        ds_phong = []
        for ten_p, mo_ta_p, chu in phong:
            ds = [m for m in chu.split() if m in md]
            da_xep.update(ds)
            ds_phong.append({'ten': ten_p, 'mo_ta': mo_ta_p, 'ban': sorted(ds, key=lambda m: -md[m]['dong'])})
        tang.append({'ten': ten, 'mo_ta': mo_ta, 'phong': ds_phong})
    thieu = sorted(set(md) - da_xep)
    if thieu:
        print('CẢNH BÁO - module chưa xếp phòng:', ', '.join(thieu))
        tang[-1]['phong'].append({'ten': 'Chưa xếp phòng', 'mo_ta': 'Module mới: thêm vào TANG trong tao_so_do_toa_nha.py', 'ban': thieu})
    phong_cua = {m: p['ten'] for t in tang for p in t['phong'] for m in p['ban']}
    dung_boi = {m: [] for m in md}
    for m, v in md.items():
        for x in v['dung']:
            dung_boi[x].append(m)
    mod = {m: {'dong': v['dong'], 'nut': nut.get(m, 0), 'phong': phong_cua.get(m, ''), 'dung': sorted(v['dung']), 'boi': sorted(dung_boi[m])}
           for m, v in md.items()}
    # quy tắc CLAUDE.md: logic không phụ thuộc màn hình
    nguoc = sorted((m, x) for m, v in md.items() for x in v['dung']
                   if not m.startswith('man_hinh') and m not in ('app', 'lenh', 'giao_dien', 'thanh_tieu_de') and x.startswith('man_hinh'))
    phu = []
    for thu_muc, ten, mau in KHU_PHU:
        ds = list(GOC.glob(mau)) if thu_muc == '.' else list((GOC / thu_muc).glob(mau.split('/', 1)[1]))
        ds = [p for p in ds if p.is_file() and '__pycache__' not in p.parts]
        phu.append({'ten': ten, 'so_file': len(ds), 'dong': sum(p.read_bytes().count(b'\n') for p in ds)})
    return {'tang': tang, 'mod': mod, 'nguoc': nguoc, 'phu': phu, 'tk': tk, 'nguong': NGUONG_LON}


MAU = r'''<!DOCTYPE html>
<html lang="vi"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Sơ đồ tòa nhà phần mềm LARC</title>
<style>
:root{--nen:#f4f1ea;--tuong:#fbfaf6;--vien:#c9c2b3;--chu:#26231d;--nhat:#6b6559;--mh:#2f6f8f;--mh-n:#dcebf2;--lg:#a3641c;--lg-n:#f5e7d3;--dung:#c2410c;--boi:#1d6fb8;--chon:#26231d}
@media (prefers-color-scheme:dark){:root{--nen:#1a1916;--tuong:#24221e;--vien:#47433a;--chu:#ece8df;--nhat:#a59f92;--mh:#7cc0e0;--mh-n:#1f3641;--lg:#e0a765;--lg-n:#3d2d18;--dung:#fb8b5a;--boi:#6db6f2;--chon:#ece8df}}
*{box-sizing:border-box}body{margin:0;background:var(--nen);color:var(--chu);font:14px/1.45 "Segoe UI",system-ui,sans-serif}
header{padding:20px 24px 12px}h1{margin:0;font-size:22px;font-weight:650}header p{margin:4px 0 0;color:var(--nhat);max-width:80ch}
.so{display:flex;flex-wrap:wrap;gap:6px 24px;margin:12px 0 0}.so b{font-size:18px;font-variant-numeric:tabular-nums;font-weight:650}.so span{color:var(--nhat);font-size:12px;margin-left:4px}
.cu{display:grid;grid-template-columns:minmax(0,1fr) 320px;gap:16px;padding:0 24px 24px;align-items:start}
@media (max-width:980px){.cu{grid-template-columns:minmax(0,1fr)}aside{position:static!important;max-height:none!important}}
#nha{position:relative}svg#day{position:absolute;inset:0;width:100%;height:100%;pointer-events:none;z-index:3}
.tang{border:2px solid var(--vien);border-bottom-width:0;background:var(--tuong);padding:10px 12px 12px}.tang:last-of-type{border-bottom-width:6px}
.tang h2{margin:0;font-size:14px;font-weight:650}.tang>p{margin:0 0 8px;color:var(--nhat);font-size:12px}
.day-phong{display:flex;flex-wrap:wrap;gap:8px}.phong{flex:1 1 280px;border:1px solid var(--vien);border-radius:3px;padding:8px;background:var(--nen);min-width:0}
.phong h3{margin:0;font-size:13px;font-weight:650}.phong p{margin:0 0 6px;font-size:11.5px;color:var(--nhat)}
.ban-wrap{display:flex;flex-wrap:wrap;gap:4px}
button.ban{all:unset;box-sizing:border-box;cursor:pointer;border:1px solid;border-radius:2px;padding:2px 5px;font-size:11px;line-height:1.2;display:flex;flex-direction:column;justify-content:space-between;overflow:hidden;position:relative;z-index:4}
.ban.mh{background:var(--mh-n);border-color:var(--mh)}.ban.lg{background:var(--lg-n);border-color:var(--lg)}.ban.lon{border-width:2px}
.ban i{font-style:normal;color:var(--nhat);font-size:10px;font-variant-numeric:tabular-nums}.ban:focus-visible{outline:2px solid var(--chon);outline-offset:1px}
.ban:hover{filter:brightness(.96)}#nha.dang-chon .ban{opacity:.25}#nha.dang-chon .ban.c,#nha.dang-chon .ban.d,#nha.dang-chon .ban.b{opacity:1}
.ban.c{outline:2px solid var(--chon)}.ban.d{box-shadow:inset 0 0 0 2px var(--dung)}.ban.b{box-shadow:inset 0 0 0 2px var(--boi)}.ban.an{display:none}
aside{position:sticky;top:12px;max-height:calc(100vh - 24px);overflow:auto;background:var(--tuong);border:1px solid var(--vien);padding:12px}
aside h2{margin:0 0 2px;font-size:15px;word-break:break-all}aside h3{margin:12px 0 4px;font-size:12.5px}aside ul{margin:0;padding:0;list-style:none}aside li{font-size:12px;padding:1px 0}
aside a{color:inherit;cursor:pointer;text-decoration:underline;text-underline-offset:2px}aside small{color:var(--nhat)}
input{width:100%;padding:6px 8px;font:inherit;background:var(--nen);color:var(--chu);border:1px solid var(--vien);border-radius:2px;margin-bottom:10px}
.chu-thich{display:flex;flex-wrap:wrap;gap:4px 12px;font-size:11.5px;color:var(--nhat);margin:0 0 10px}.chu-thich u{display:inline-block;width:11px;height:11px;border:1px solid;vertical-align:-1px;margin-right:4px;text-decoration:none}
.phu{display:flex;flex-wrap:wrap;gap:8px;margin-top:12px}.phu div{flex:1 1 170px;border:1px dashed var(--vien);padding:8px;font-size:12px}.phu b{display:block;font-size:13px}
.xem-xet{margin-top:12px;font-size:12px}.xem-xet summary{cursor:pointer;font-weight:650}
</style></head><body>
<header><h1>Sơ đồ tòa nhà phần mềm LARC</h1>
<p>Mỗi tầng là một lớp kiến trúc, mỗi phòng là một mảng nghiệp vụ, mỗi bàn là một file trong <code>pabt/</code>; bàn càng to, file càng nhiều dòng. Bấm một bàn để xem dây nối.</p>
<div class="so" id="so"></div></header>
<div class="cu"><main><div id="nha"><svg id="day" aria-hidden="true"></svg></div><div class="phu" id="phu"></div></main>
<aside><input id="tim" type="search" placeholder="Tìm module (vd: gia_dat)…" aria-label="Tìm module">
<div class="chu-thich"><span><u style="background:var(--mh-n);border-color:var(--mh)"></u>Màn hình</span><span><u style="background:var(--lg-n);border-color:var(--lg)"></u>Logic</span><span><u style="border-color:var(--dung)"></u>Module đang chọn dùng</span><span><u style="border-color:var(--boi)"></u>Dùng module đang chọn</span></div>
<div id="tt"></div></aside></div>
<script>
const D=__DU_LIEU__;const $=s=>document.querySelector(s),vn=n=>n.toLocaleString('vi-VN'),M=D.mod,ban={};
const tong=Object.values(M).reduce((a,m)=>a+m.dong,0);
const lon=Object.entries(M).filter(([,m])=>m.dong>=D.nguong).sort((a,b)=>b[1].dong-a[1].dong);
const hub=Object.entries(M).sort((a,b)=>b[1].boi.length-a[1].boi.length).slice(0,8);
$('#so').innerHTML=[[Object.keys(M).length,'module'],[vn(tong),'dòng mã pabt/'],[D.tang.reduce((a,t)=>a+t.phong.length,0),'phòng'],[lon.length,'file ≥ '+vn(D.nguong)+' dòng'],[D.tk.tong?vn(D.tk.tong):'-','nút đồ thị graphify']].map(([a,b])=>`<div><b>${a}</b><span>${b}</span></div>`).join('');
const nha=$('#nha');
for(const t of D.tang){const e=document.createElement('section');e.className='tang';e.innerHTML=`<h2>${t.ten}</h2><p>${t.mo_ta}</p>`;const dp=document.createElement('div');dp.className='day-phong';
 for(const p of t.phong){const r=document.createElement('div');r.className='phong';const dong=p.ban.reduce((a,x)=>a+M[x].dong,0);r.innerHTML=`<h3>${p.ten}</h3><p>${p.mo_ta} · ${p.ban.length} module, ${vn(dong)} dòng</p>`;const w=document.createElement('div');w.className='ban-wrap';
  for(const m of p.ban){const x=M[m],b=document.createElement('button');b.type='button';b.className='ban '+(m.startsWith('man_hinh')?'mh':'lg')+(x.dong>=D.nguong?' lon':'');const can=Math.sqrt(x.dong);const nhan=m.replace(/^man_hinh_/,'mh_');b.style.width=Math.max(Math.round(66+can*2.1),Math.ceil(nhan.length*6.4)+14)+'px';b.style.height=Math.round(30+can*.5)+'px';b.title=`${m}.py: ${vn(x.dong)} dòng`;b.innerHTML=`<span>${nhan}</span><i>${vn(x.dong)}</i>`;b.onclick=()=>chon(m);ban[m]=b;w.append(b)}
  r.append(w);dp.append(r)}
 e.append(dp);nha.append(e)}
$('#phu').innerHTML=D.phu.map(p=>`<div><b>${p.ten}</b>${vn(p.so_file)} file · ${vn(p.dong)} dòng</div>`).join('');
const lk=a=>a.map(m=>`<li><a data-m="${m}">${m}</a> <small>${M[m].phong}</small></li>`).join('')||'<li><small>Không có</small></li>';
function tongQuan(){$('#tt').innerHTML=`<h2>Tổng quan</h2><h3>Module được dùng nhiều nhất</h3><ul>${hub.map(([m,x])=>`<li><a data-m="${m}">${m}</a> <small>${x.boi.length} module dùng</small></li>`).join('')}</ul><h3>File lớn nhất (nên đọc từng đoạn)</h3><ul>${lon.map(([m,x])=>`<li><a data-m="${m}">${m}</a> <small>${vn(x.dong)} dòng</small></li>`).join('')}</ul><h3>Logic đang gọi ngược màn hình</h3>${D.nguoc.length?`<details class="xem-xet"><summary>${D.nguoc.length} chỗ (CLAUDE.md: màn hình chỉ hiển thị)</summary><ul>${D.nguoc.map(([a,b])=>`<li><a data-m="${a}">${a}</a> → ${b}</li>`).join('')}</ul></details>`:'<small>Không có</small>'}`}
function ve(m){const s=$('#day');s.innerHTML='';if(!m)return;const g=nha.getBoundingClientRect();s.setAttribute('viewBox',`0 0 ${g.width} ${g.height}`);const c=e=>{const r=e.getBoundingClientRect();return[r.left-g.left+r.width/2,r.top-g.top+r.height/2]};const[a,b]=c(ban[m]);
 const ke=(ds,mau)=>{for(const x of ds){if(!ban[x])continue;const[u,v]=c(ban[x]),p=document.createElementNS('http://www.w3.org/2000/svg','path');p.setAttribute('d',`M${a} ${b} C${a} ${(b+v)/2},${u} ${(b+v)/2},${u} ${v}`);p.setAttribute('fill','none');p.setAttribute('stroke',mau);p.setAttribute('stroke-width','1.2');p.setAttribute('opacity','.6');s.append(p)}};
 const cs=getComputedStyle(document.documentElement);ke(M[m].boi,cs.getPropertyValue('--boi'));ke(M[m].dung,cs.getPropertyValue('--dung'))}
let dangChon=null;
function chon(m){if(dangChon===m)m=null;dangChon=m;nha.classList.toggle('dang-chon',!!m);for(const k in ban)ban[k].classList.remove('c','d','b');if(!m){ve(null);tongQuan();return}
 ban[m].classList.add('c');M[m].dung.forEach(x=>ban[x]&&ban[x].classList.add('d'));M[m].boi.forEach(x=>ban[x]&&ban[x].classList.add('b'));ve(m);const x=M[m];
 $('#tt').innerHTML=`<h2>${m}.py</h2><small>${x.phong} · ${vn(x.dong)} dòng${x.nut?` · ${vn(x.nut)} nút đồ thị`:''}</small><h3 style="color:var(--dung)">Dùng ${x.dung.length} module</h3><ul>${lk(x.dung)}</ul><h3 style="color:var(--boi)">Được ${x.boi.length} module dùng</h3><ul>${lk(x.boi)}</ul><p><a data-bo="1">Bỏ chọn</a></p>`}
$('#tt').addEventListener('click',e=>{const t=e.target.closest('a');if(!t)return;if(t.dataset.bo)chon(dangChon);else{if(dangChon===t.dataset.m)return;chon(t.dataset.m);ban[t.dataset.m].scrollIntoView({block:'nearest'})}});
$('#tim').addEventListener('input',e=>{const q=e.target.value.trim().toLowerCase();for(const k in ban)ban[k].classList.toggle('an',!!q&&!k.includes(q));ve(dangChon)});
addEventListener('resize',()=>ve(dangChon));document.addEventListener('keydown',e=>{if(e.key==='Escape'&&dangChon)chon(dangChon)});tongQuan();
</script></body></html>
'''


def main() -> None:
    d = dung_du_lieu()
    RA.parent.mkdir(exist_ok=True)
    RA.write_text(MAU.replace('__DU_LIEU__', json.dumps(d, ensure_ascii=False).replace('</', '<\\/')), encoding='utf-8')
    print(f'{len(d["mod"])} module, {sum(m["dong"] for m in d["mod"].values())} dòng, {len(d["nguoc"])} chỗ logic gọi ngược màn hình -> {RA}')


if __name__ == '__main__':
    main()

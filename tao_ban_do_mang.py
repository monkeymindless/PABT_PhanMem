"""Bản đồ MẠNG mã nguồn (05/11/2026) -> graphify-out/ban_do_mang.html (một file, không cần mạng).

    python tao_ban_do_mang.py        (sau `graphify update .`)

Đồ thị lực nền tối: mỗi chấm là một file / lớp / hàm trong pabt/ (đọc từ graphify-out/graph.json), màu theo phòng nghiệp vụ của
tao_so_do_toa_nha.TANG, hộp tích bật / tắt từng phòng. Chỉ lấy nút mã (bỏ nút chú thích docstring) và cạnh EXTRACTED (không lấy cạnh suy đoán). Chỉ thư viện chuẩn."""
from __future__ import annotations

import json
from pathlib import Path

from tao_so_do_toa_nha import TANG

GOC = Path(__file__).resolve().parent
RA = GOC / 'graphify-out' / 'ban_do_mang.html'
MAU_PHONG = ('#6ea8fe', '#f472b6', '#fb923c', '#f87171', '#a78bfa', '#2dd4bf', '#facc15', '#4ade80', '#38bdf8', '#e879f9', '#fda4af', '#a3e635',
             '#fdba74', '#94a3b8', '#d6d3d1')


def dung_du_lieu() -> dict:
    d = json.loads((GOC / 'graphify-out' / 'graph.json').read_text(encoding='utf-8'))
    phong, cua = [], {}
    for _, _, ds in TANG:
        for ten, _, chu in ds:
            for m in chu.split():
                cua[m] = len(phong)
            phong.append(ten)
    khac = len(phong)
    phong.append('Chưa xếp phòng')
    nut, so = [], {}
    for n in d['nodes']:
        f = (n.get('source_file') or '').replace('\\', '/')
        if n.get('file_type') != 'code' or not (f.startswith('pabt/') and f.endswith('.py')):
            continue
        so[n['id']] = len(nut)
        vi_tri = str(n.get('source_location') or '').lstrip('L')
        nut.append([n.get('label') or n['id'], cua.get(f[5:-3], khac), f[5:], int(vi_tri) if vi_tri.isdigit() else 0,
                    1 if n['id'].replace('_', '') == f[:-3].replace('/', '').replace('_', '') else 0])
    canh, da = [], set()
    for e in d['links']:
        a, b = so.get(e['source']), so.get(e['target'])
        if a is None or b is None or a == b or e.get('confidence') != 'EXTRACTED' or e.get('relation') == 'rationale_for':
            continue
        k = (a, b) if a < b else (b, a)
        if k not in da:
            da.add(k)
            canh += [a, b]
    return {'phong': phong, 'mau': MAU_PHONG, 'nut': nut, 'canh': canh}


MAU = r'''<!DOCTYPE html>
<html lang="vi"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Bản đồ mạng mã nguồn LARC</title>
<style>
*{box-sizing:border-box}html,body{height:100%;margin:0}body{background:#0b0b14;color:#e5e7eb;font:13px/1.4 "Segoe UI",system-ui,sans-serif;display:flex;overflow:hidden}
#ve{flex:1 1 auto;position:relative;min-width:0}canvas{position:absolute;inset:0;width:100%;height:100%;cursor:grab;display:block}canvas.keo{cursor:grabbing}
#goc{position:absolute;left:14px;top:10px;pointer-events:none}#goc h1{margin:0;font-size:15px;font-weight:600}#goc p{margin:2px 0 0;color:#9ca3af;font-size:12px;font-variant-numeric:tabular-nums}
#nhan{position:absolute;display:none;pointer-events:none;background:#1b1b2b;border:1px solid #3a3a52;padding:4px 8px;border-radius:4px;font-size:12px;max-width:340px;z-index:2}#nhan small{color:#9ca3af;display:block}
aside{flex:0 0 288px;background:#171728;border-left:1px solid #2c2c44;display:flex;flex-direction:column;min-height:0}
.dau{padding:10px;border-bottom:1px solid #2c2c44;display:grid;gap:7px}input[type=search],select{width:100%;background:#0f0f1c;color:inherit;border:1px solid #3a3a52;border-radius:4px;padding:5px 7px;font:inherit}
label.d{display:grid;gap:2px;color:#9ca3af;font-size:11.5px}.hang{display:flex;gap:6px}button{flex:1;background:#26263c;color:inherit;border:1px solid #3a3a52;border-radius:4px;padding:4px 6px;font:inherit;cursor:pointer}button:hover{background:#32324d}
:focus-visible{outline:2px solid #6ea8fe;outline-offset:1px}
#ds{flex:1 1 auto;overflow:auto;padding:4px 10px}#ds label{display:flex;align-items:center;gap:8px;padding:6px 0;cursor:pointer}#ds input{width:18px;height:18px;accent-color:#5b8def;margin:0;flex:none}#ds i{width:10px;height:10px;border-radius:50%;flex:none}#ds span{flex:1;min-width:0}#ds small{color:#9ca3af;font-variant-numeric:tabular-nums}
#tt{border-top:1px solid #2c2c44;padding:10px;max-height:42%;overflow:auto}#tt h2{margin:0;font-size:14px;word-break:break-all}#tt small{color:#9ca3af}#tt ul{margin:6px 0 0;padding:0;list-style:none}#tt li{padding:1px 0;font-size:12px}#tt a{color:inherit;cursor:pointer;text-decoration:underline;text-underline-offset:2px}
@media (max-width:760px){body{flex-direction:column}aside{flex:0 0 45%;border-left:0;border-top:1px solid #2c2c44}}
</style></head><body>
<div id="ve"><canvas id="c"></canvas><div id="goc"><h1>Bản đồ mạng mã nguồn LARC</h1><p id="so"></p></div><div id="nhan"></div></div>
<aside><div class="dau"><input id="tim" type="search" placeholder="Tìm hàm, lớp, file…" aria-label="Tìm hàm, lớp, file">
<label class="d">Mức chi tiết<select id="muc"><option value="800" selected>800 nút chính</option><option value="1500">1.500 nút</option><option value="3000">3.000 nút</option><option value="0">Toàn bộ</option></select></label>
<div class="hang"><button id="het">Chọn tất cả</button><button id="bo">Bỏ chọn tất cả</button><button id="khop">Vừa khung</button></div></div>
<div id="ds"></div><div id="tt"><small>Bấm một chấm để xem nó nối với gì. Lăn chuột để phóng to, kéo nền để di chuyển, kéo chấm để dời chấm.</small></div></aside>
<script>
const D=__DU_LIEU__;const $=s=>document.querySelector(s),vn=n=>n.toLocaleString('vi-VN');
const TAT=D.nut.length,bacAll=new Int32Array(TAT);for(let i=0;i<D.canh.length;i++)bacAll[D.canh[i]]++;
let N=[],C=[],ke=[],bat=D.phong.map(()=>true),chon=-1,rx=0,ry=0,tl=1,alpha=1,cho=-1,keo=-1,duyet=false;
const cv=$('#c'),g=cv.getContext('2d');
function dung(muc){const thu=[...Array(TAT).keys()].sort((a,b)=>(D.nut[b][4]-D.nut[a][4])||(bacAll[b]-bacAll[a]));const lay=muc?thu.slice(0,muc):thu;const map=new Int32Array(TAT).fill(-1);const so=D.phong.length;
 N=lay.map((id,i)=>{map[id]=i;const n=D.nut[id],goc=n[1]/so*6.283+(i%7)*.03,R=420+Math.random()*260;return{id,t:n[0],p:n[1],f:n[2],l:n[3],fi:n[4],x:Math.cos(goc)*R+(Math.random()-.5)*160,y:Math.sin(goc)*R+(Math.random()-.5)*160,vx:0,vy:0,b:0,hx:Math.cos(n[1]/so*6.283)*560,hy:Math.sin(n[1]/so*6.283)*560}});
 C=[];ke=N.map(()=>[]);for(let i=0;i<D.canh.length;i+=2){const a=map[D.canh[i]],b=map[D.canh[i+1]];if(a>=0&&b>=0){C.push([a,b]);ke[a].push(b);ke[b].push(a);N[a].b++;N[b].b++}}
 N.forEach(n=>n.r=n.fi?Math.min(9,4+Math.sqrt(n.b)*.35):Math.min(6,1.6+Math.sqrt(n.b)*.4));
 chon=-1;alpha=1;xepDs();$('#so').textContent=`${vn(N.length)} / ${vn(TAT)} nút · ${vn(C.length)} cạnh`;resize();khop()}
function quad(ds){let x0=1e9,y0=1e9,x1=-1e9,y1=-1e9;for(const n of ds){if(n.x<x0)x0=n.x;if(n.y<y0)y0=n.y;if(n.x>x1)x1=n.x;if(n.y>y1)y1=n.y}const s=Math.max(x1-x0,y1-y0)+1;const goc={x:x0,y:y0,s,m:0,cx:0,cy:0,n:null,c:null};
 const them=(q,n,d)=>{q.m++;q.cx+=n.x;q.cy+=n.y;if(!q.c&&!q.n){q.n=n;return}if(d>18)return;if(!q.c){q.c=[null,null,null,null];const c=q.n;q.n=null;vao(q,c,d)}vao(q,n,d)};
 const vao=(q,n,d)=>{const h=q.s/2,i=(n.x>q.x+h?1:0)+(n.y>q.y+h?2:0);let k=q.c[i];if(!k){k={x:q.x+(i&1?h:0),y:q.y+(i&2?h:0),s:h,m:0,cx:0,cy:0,n:null,c:null};q.c[i]=k}them(k,n,d+1)};
 for(const n of ds)them(goc,n,0);return goc}
function dayRa(q,n,k){const dx=q.cx/q.m-n.x,dy=q.cy/q.m-n.y,d2=dx*dx+dy*dy+.01;if(!q.c||q.s*q.s/d2<.7){if(q.n===n&&q.m===1)return;const f=k*q.m/d2;n.vx-=dx*f;n.vy-=dy*f;return}for(const c of q.c)if(c)dayRa(c,n,k)}
function buoc(){const ds=N.filter(n=>bat[n.p]);if(!ds.length)return;const q=quad(ds),k=34*alpha;for(const n of ds)dayRa(q,n,k);
 for(const[a,b]of C){const u=N[a],v=N[b];if(!bat[u.p]||!bat[v.p])continue;const dx=v.x-u.x,dy=v.y-u.y,d=Math.sqrt(dx*dx+dy*dy)||1,dai=u.fi||v.fi?46:34,mem=(u.p===v.p?.09:.006)/Math.sqrt(Math.min(ke[a].length,ke[b].length)||1),f=(d-dai)*mem*alpha,fx=dx/d*f,fy=dy/d*f;u.vx+=fx;u.vy+=fy;v.vx-=fx;v.vy-=fy}
 for(const n of ds){n.vx+=(n.hx-n.x)*.02*alpha;n.vy+=(n.hy-n.y)*.02*alpha;n.vx*=.62;n.vy*=.62;if(N[keo]!==n){n.x+=n.vx;n.y+=n.vy}}alpha*=.992}
function resize(){const dp=devicePixelRatio||1,r=$('#ve').getBoundingClientRect();cv.width=Math.max(1,r.width*dp);cv.height=Math.max(1,r.height*dp);duyet=true}
function khop(){const ds=N.filter(n=>bat[n.p]);if(!ds.length)return;let x0=1e9,y0=1e9,x1=-1e9,y1=-1e9;for(const n of ds){x0=Math.min(x0,n.x);y0=Math.min(y0,n.y);x1=Math.max(x1,n.x);y1=Math.max(y1,n.y)}const r=$('#ve').getBoundingClientRect();tl=Math.min(r.width/(x1-x0+80),r.height/(y1-y0+80),1.6);rx=r.width/2-(x0+x1)/2*tl;ry=r.height/2-(y0+y1)/2*tl;duyet=true}
function ve(){const dp=devicePixelRatio||1;g.setTransform(1,0,0,1,0,0);g.clearRect(0,0,cv.width,cv.height);g.setTransform(dp*tl,0,0,dp*tl,dp*rx,dp*ry);
 const lq=chon>=0?new Set([chon,...ke[chon]]):null;g.lineWidth=.7/tl;
 const nhom=D.phong.map(()=>[]),lien=[];for(const c of C){const u=N[c[0]],v=N[c[1]];if(bat[u.p]&&bat[v.p])(u.p===v.p?nhom[u.p]:lien).push(c)}
 const net=(ds)=>{g.beginPath();for(const[a,b]of ds){g.moveTo(N[a].x,N[a].y);g.lineTo(N[b].x,N[b].y)}g.stroke()};
 g.globalAlpha=lq?.02:.055;g.strokeStyle='#cbd5e1';net(lien);g.globalAlpha=lq?.06:.4;nhom.forEach((ds,p)=>{g.strokeStyle=D.mau[p%D.mau.length];net(ds)});
 if(lq){g.globalAlpha=.85;g.lineWidth=1.1/tl;g.strokeStyle='#fff';g.beginPath();for(const b of ke[chon]){if(!bat[N[b].p])continue;g.moveTo(N[chon].x,N[chon].y);g.lineTo(N[b].x,N[b].y)}g.stroke()}
 N.forEach((n,i)=>{if(!bat[n.p])return;g.globalAlpha=lq&&!lq.has(i)?.16:1;g.fillStyle=D.mau[n.p%D.mau.length];g.beginPath();g.arc(n.x,n.y,Math.max(n.r,(n.fi?3.4:2)/tl),0,6.283);g.fill()});
 if(chon>=0){const n=N[chon];g.globalAlpha=1;g.strokeStyle='#fff';g.lineWidth=2/tl;g.beginPath();g.arc(n.x,n.y,n.r+2/tl,0,6.283);g.stroke()}
 g.globalAlpha=1;g.fillStyle='#e5e7eb';g.font=`${11/tl}px "Segoe UI",sans-serif`;g.textAlign='center';N.forEach((n,i)=>{if(!bat[n.p])return;const hien=lq?lq.has(i)&&(ke[chon].length<40||i===chon||tl>1.2):(n.fi&&tl>.5)||tl>1.5&&n.b>8||tl>2.6;if(hien)g.fillText(n.t,n.x,n.y-n.r-3/tl)})}
function vong(){if(alpha>.02){const t=performance.now();do{buoc()}while(performance.now()-t<14&&alpha>.02);duyet=true}if(duyet){ve();duyet=false}requestAnimationFrame(vong)}
function xepDs(){const dem=D.phong.map(()=>0);N.forEach(n=>dem[n.p]++);$('#ds').innerHTML=D.phong.map((t,i)=>dem[i]?`<label><input type="checkbox" data-p="${i}" ${bat[i]?'checked':''}><i style="background:${D.mau[i%D.mau.length]}"></i><span>${t}</span><small>${vn(dem[i])}</small></label>`:'').join('')}
function dat(fn){bat=bat.map(fn);xepDs();if(chon>=0&&!bat[N[chon].p])bo();alpha=Math.max(alpha,.25);duyet=true}
$('#ds').addEventListener('change',e=>{const p=+e.target.dataset.p;dat((v,i)=>i===p?e.target.checked:v)});$('#het').onclick=()=>dat(()=>true);$('#bo').onclick=()=>dat(()=>false);$('#khop').onclick=khop;$('#muc').onchange=e=>dung(+e.target.value);
function bo(){chon=-1;$('#tt').innerHTML='<small>Bấm một chấm để xem nó nối với gì.</small>';duyet=true}
function xem(i,dua){chon=i;const n=N[i],lk=[...new Set(ke[i])].sort((a,b)=>N[b].b-N[a].b);$('#tt').innerHTML=`<h2>${esc(n.t)}</h2><small>${esc(n.f)}${n.l?' : dòng '+n.l:''} · ${esc(D.phong[n.p])}</small><ul>${lk.slice(0,30).map(k=>`<li><a data-i="${k}">${esc(N[k].t)}</a> <small>${esc(N[k].f)}</small></li>`).join('')}</ul>${lk.length>30?`<small>… và ${lk.length-30} liên kết nữa (${lk.length} tất cả)</small>`:''}`;if(dua){const r=$('#ve').getBoundingClientRect();tl=Math.max(tl,1.1);rx=r.width/2-n.x*tl;ry=r.height/2-n.y*tl}duyet=true}
const esc=s=>String(s).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
$('#tt').addEventListener('click',e=>{const a=e.target.closest('a[data-i]');if(a)xem(+a.dataset.i,true)});
function tai(e){const r=cv.getBoundingClientRect(),x=(e.clientX-r.left-rx)/tl,y=(e.clientY-r.top-ry)/tl;let m=-1,b=1e9;N.forEach((n,i)=>{if(!bat[n.p])return;const d=(n.x-x)**2+(n.y-y)**2,h=Math.max(n.r,6/tl);if(d<h*h&&d<b){b=d;m=i}});return{m,x,y}}
let nen=null,di=false;
cv.addEventListener('pointerdown',e=>{cv.setPointerCapture(e.pointerId);const h=tai(e);di=false;cv.classList.add('keo');if(h.m>=0)keo=h.m;else nen=[e.clientX-rx,e.clientY-ry]});
cv.addEventListener('pointermove',e=>{if(keo>=0){const h=tai(e);N[keo].x=h.x;N[keo].y=h.y;di=true;alpha=Math.max(alpha,.12);duyet=true;return}if(nen){rx=e.clientX-nen[0];ry=e.clientY-nen[1];di=true;duyet=true;return}const h=tai(e),o=$('#nhan');if(h.m>=0){const n=N[h.m],r=cv.getBoundingClientRect();o.innerHTML=`${esc(n.t)}<small>${esc(n.f)}${n.l?' : dòng '+n.l:''} · ${n.b} liên kết</small>`;o.style.display='block';o.style.left=Math.min(e.clientX-r.left+12,r.width-200)+'px';o.style.top=(e.clientY-r.top+12)+'px'}else o.style.display='none'});
cv.addEventListener('pointerup',e=>{cv.classList.remove('keo');const k=keo;keo=-1;nen=null;if(di)return;if(k>=0)xem(k,false);else bo()});
cv.addEventListener('pointerleave',()=>{$('#nhan').style.display='none'});
cv.addEventListener('wheel',e=>{e.preventDefault();const r=cv.getBoundingClientRect(),x=e.clientX-r.left,y=e.clientY-r.top,z=Math.exp(-e.deltaY*.0012),m=Math.min(8,Math.max(.08,tl*z));rx=x-(x-rx)*m/tl;ry=y-(y-ry)*m/tl;tl=m;duyet=true},{passive:false});
$('#tim').addEventListener('input',e=>{const q=e.target.value.trim().toLowerCase();if(q.length<2)return;let i=N.findIndex(n=>n.t.toLowerCase()===q);if(i<0)i=N.findIndex(n=>n.t.toLowerCase().includes(q));if(i>=0)xem(i,true)});
addEventListener('keydown',e=>{if(e.key==='Escape')bo()});new ResizeObserver(resize).observe($('#ve'));
dung(800);let dem=0;const t=setInterval(()=>{khop();if(++dem>6||alpha<=.02)clearInterval(t)},1200);vong();
</script></body></html>
'''


def main() -> None:
    d = dung_du_lieu()
    RA.write_text(MAU.replace('__DU_LIEU__', json.dumps(d, ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/')), encoding='utf-8')
    print(f'{len(d["nut"])} nút, {len(d["canh"]) // 2} cạnh, {RA.stat().st_size // 1024} KB -> {RA}')


if __name__ == '__main__':
    main()

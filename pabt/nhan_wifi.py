"""Nhận file kết quả kiểm đếm từ điện thoại qua Wi-Fi nội bộ (phương án đột phá 5, người dùng 30/10/2026). Không Qt.

Máy tính chạy một máy chủ HTTP nhỏ (thư viện chuẩn) CHỈ trong lúc hộp "Nhận từ điện thoại qua Wi-Fi" đang mở. Điện thoại cùng mạng
Wi-Fi quét mã QR (hoặc gõ địa chỉ) -> trình duyệt mở trang tải lên -> chọn file .json đã xuất từ LARC Mobile -> gửi. Không cần Zalo /
cáp / Internet. Ứng dụng LARC Mobile chạy https nên không tự gửi tới địa chỉ http nội bộ được - người dùng mở trang bằng trình duyệt.

An toàn: chỉ nghe trên địa chỉ mạng nội bộ đã chọn (không 0.0.0.0); đường dẫn chứa MÃ PHIÊN ngẫu nhiên (secrets) - sai mã: 404; chỉ có
hai đường: trang tải lên và nhận file; chỉ nhận nội dung JSON (an_toan.kiem_tra_magic_bytes), <= KICH_TOI_DA byte, <= SO_FILE_TOI_DA
file mỗi phiên; ghi từng khối vào file tạm rồi os.replace vào hộp thư <thư mục máy>\\nhan_wifi\\<giờ mở>_<mã>; tên file làm sạch (chỉ
chữ không dấu / số / - _). Không phục vụ file nào của máy. File nhận về CHƯA được nhập: hộp thoại nhập bằng phieu_kiem_dem (kiểm đủ).
Lần đầu chạy, Windows có thể hỏi cho phép chương trình nhận kết nối: chọn mạng riêng (Private)."""
from __future__ import annotations

import hashlib
import hmac
import ipaddress
import json
import os
import queue
import re
import secrets
import socket
import threading
import unicodedata
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote

CONG_UU_TIEN = (8765, 8766, 8767, 8780)     # thử lần lượt (dễ nhớ / mở tường lửa), hết thì để hệ điều hành chọn
KICH_TOI_DA = 200 * 1024 * 1024             # một file (ảnh biên bản gửi kèm dạng base64 trong .json)
SO_FILE_TOI_DA = 100                        # mỗi phiên mở hộp
TONG_TOI_DA = 1024 * 1024 * 1024             # 1.0.51: tổng dung lượng một phiên (không để máy khác trong Wi-Fi gửi đầy ổ đĩa)
KHOI = 64 * 1024
THU_MUC = 'nhan_wifi'
# 1.0.55 (người dùng 03/11/2026): mã hóa gói tin. Khóa phiên 128 bit (secrets) nằm sau dấu # của địa chỉ trong mã QR - trình duyệt KHÔNG
# gửi phần sau # qua mạng. Trang trên điện thoại mã hóa file bằng dòng khóa SHA-256(khóa | nonce | bộ đếm) (nonce ngẫu nhiên mỗi lần gửi)
# và gửi kèm HMAC-SHA256 để máy tính phát hiện gói tin bị sửa / sai khóa. JS thuần (trang http nội bộ: trình duyệt không cho WebCrypto).
# Không quét QR (gõ địa chỉ tay): gửi không mã hóa như trước.
MA_HOA = 'sha256ctr1'
NHAN_MAC = b'LARC-MAC1'


class LoiNhanWifi(Exception):
    pass


class GiaiMa:
    """Giải mã luồng file gửi bằng MA_HOA: plain = ct XOR SHA-256(khóa | nonce | bộ đếm 4 byte big-endian) theo từng khối 32 byte;
    mã kiểm = HMAC-SHA256(SHA-256(NHAN_MAC | khóa), nonce | ct). Cùng thuật toán với trang TRANG (JS)."""

    def __init__(self, khoa: bytes, nonce: bytes):
        self.khoa, self.nonce, self.dem, self.du = khoa, nonce, 0, b''
        self.mac = hmac.new(hashlib.sha256(NHAN_MAC + khoa).digest(), nonce, hashlib.sha256)

    def xu_ly(self, ct: bytes) -> bytes:
        self.mac.update(ct)
        can, phan, co = len(ct), [self.du], len(self.du)
        while co < can:
            phan.append(hashlib.sha256(self.khoa + self.nonce + self.dem.to_bytes(4, 'big')).digest())
            self.dem += 1
            co += 32
        ks = b''.join(phan)
        self.du = ks[can:]
        return (int.from_bytes(ct, 'big') ^ int.from_bytes(ks[:can], 'big')).to_bytes(can, 'big')

    def khop(self, ma_kiem: str) -> bool:
        return hmac.compare_digest(self.mac.hexdigest(), (ma_kiem or '').strip().lower())


def ma_hoa(khoa: bytes, nonce: bytes, du: bytes) -> tuple:
    """(ct, mã kiểm hex) - như trang điện thoại làm (kiểm thử, công cụ)."""
    g = GiaiMa(khoa, nonce)
    ks_g = GiaiMa(khoa, nonce)
    ct = ks_g.xu_ly(du)                             # XOR đối xứng: "giải mã" bản rõ = mã hóa
    g.xu_ly(ct)
    return ct, g.mac.hexdigest()


def dia_chi_noi_bo() -> list:
    """Các địa chỉ IPv4 mạng nội bộ của máy (192.168.x.x, 10.x.x.x, 172.16-31.x.x), địa chỉ của đường ra mạng mặc định đứng đầu."""
    ds = []
    try:                                            # đường ra mặc định: UDP connect không gửi gói nào
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect(('10.255.255.255', 1))
            ds.append(s.getsockname()[0])
        finally:
            s.close()
    except OSError:
        pass
    try:
        ds += [x[4][0] for x in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET)]
    except OSError:
        pass
    kq = []
    for ip in ds:
        try:
            a = ipaddress.ip_address(ip)
        except ValueError:
            continue
        if a.is_private and not a.is_loopback and not a.is_link_local and ip not in kq:
            kq.append(ip)
    return kq


def ten_an_toan(ten: str) -> str:
    """Tên file gửi lên -> tên lưu: bỏ dấu, chỉ chữ / số / - _ . (không thư mục, không ".."), đuôi .json."""
    goc = Path(str(ten or '').replace('\\', '/')).name
    s = unicodedata.normalize('NFD', goc.replace('đ', 'd').replace('Đ', 'D'))
    s = ''.join(c for c in s if unicodedata.category(c) != 'Mn')
    s = re.sub(r'[^A-Za-z0-9_-]+', '_', Path(s).stem).strip('_')[:60] or 'ket_qua'
    return s + '.json'


TRANG = '''<!doctype html><html lang="vi"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>LARC - Gửi kết quả kiểm đếm</title>
<style>
body{font-family:system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;margin:0;background:#F3F6FA;color:#0F172A}
header{background:#1E3A5F;color:#fff;padding:14px 16px;font-size:18px;font-weight:600}
main{padding:16px;max-width:560px;margin:auto}
.the{background:#fff;border:1px solid #D5DEE8;border-radius:10px;padding:14px;margin-bottom:12px}
label.chon{display:block;text-align:center;padding:18px;border:2px dashed #94A3B8;border-radius:10px;font-size:16px;color:#1E3A5F}
input[type=file]{display:none}
button{width:100%;padding:14px;font-size:17px;border:0;border-radius:10px;background:#1E3A5F;color:#fff;margin-top:12px}
button:disabled{background:#94A3B8}
.dong{padding:8px 0;border-bottom:1px solid #E2E8F0;font-size:15px}.dong:last-child{border:0}
.dat{color:#166534}.loi{color:#B91C1C}.cho{color:#475569}
small{color:#475569}
</style></head><body><header>LARC - Gửi kết quả kiểm đếm về máy tính</header><main>
<div class="the"><b>Máy nhận:</b> @@MAY@@<br><small>Chọn file kết quả <b>.json</b> đã xuất từ ứng dụng LARC Mobile (thẻ "Xuất .JSON"
- thư mục Tải về / Tệp). Có thể chọn nhiều file.</small></div>
<div class="the"><label class="chon" for="tep">Bấm để chọn file .json</label><input id="tep" type="file" multiple>
<div id="ds"></div><button id="gui" disabled>Gửi về máy tính</button></div>
<small id="bao_mat">Mở trang bằng cách quét mã QR trên máy tính để gói tin được mã hóa.</small><br>
<small>Trang này chỉ dùng được khi điện thoại và máy tính cùng mạng Wi-Fi và hộp "Nhận từ điện thoại" trên máy tính đang mở.</small>
</main><script>
"use strict";
var tep = document.getElementById("tep"), ds = document.getElementById("ds"), gui = document.getElementById("gui");
function dong(ten, chu, lop) { var d = document.createElement("div"); d.className = "dong " + (lop || "cho");
  d.textContent = ten + ": " + chu; ds.appendChild(d); return d; }
tep.addEventListener("change", function () { ds.textContent = ""; for (var i = 0; i < tep.files.length; i++)
  dong(tep.files[i].name, "chưa gửi"); gui.disabled = tep.files.length === 0; });
var K = [0x428a2f98,0x71374491,0xb5c0fbcf,0xe9b5dba5,0x3956c25b,0x59f111f1,0x923f82a4,0xab1c5ed5,0xd807aa98,0x12835b01,
 0x243185be,0x550c7dc3,0x72be5d74,0x80deb1fe,0x9bdc06a7,0xc19bf174,0xe49b69c1,0xefbe4786,0x0fc19dc6,0x240ca1cc,0x2de92c6f,
 0x4a7484aa,0x5cb0a9dc,0x76f988da,0x983e5152,0xa831c66d,0xb00327c8,0xbf597fc7,0xc6e00bf3,0xd5a79147,0x06ca6351,0x14292967,
 0x27b70a85,0x2e1b2138,0x4d2c6dfc,0x53380d13,0x650a7354,0x766a0abb,0x81c2c92e,0x92722c85,0xa2bfe8a1,0xa81a664b,0xc24b8b70,
 0xc76c51a3,0xd192e819,0xd6990624,0xf40e3585,0x106aa070,0x19a4c116,0x1e376c08,0x2748774c,0x34b0bcb5,0x391c0cb3,0x4ed8aa4a,
 0x5b9cca4f,0x682e6ff3,0x748f82ee,0x78a5636f,0x84c87814,0x8cc70208,0x90befffa,0xa4506ceb,0xbef9a3f7,0xc67178f2];
function Sha() { this.h = new Int32Array([0x6a09e667,0xbb67ae85,0x3c6ef372,0xa54ff53a,0x510e527f,0x9b05688c,0x1f83d9ab,0x5be0cd19]);
  this.b = new Uint8Array(64); this.n = 0; this.len = 0; this.w = new Int32Array(64); }
Sha.prototype.khoi = function (m, o) { var w = this.w, h = this.h, i, x, y, t1, t2, a, b, c, d, e, f, g, k;
  for (i = 0; i < 16; i++) w[i] = (m[o + 4 * i] << 24) | (m[o + 4 * i + 1] << 16) | (m[o + 4 * i + 2] << 8) | m[o + 4 * i + 3];
  for (i = 16; i < 64; i++) { x = w[i - 15]; y = w[i - 2];
    w[i] = (((x >>> 7) | (x << 25)) ^ ((x >>> 18) | (x << 14)) ^ (x >>> 3)) + w[i - 16] +
      (((y >>> 17) | (y << 15)) ^ ((y >>> 19) | (y << 13)) ^ (y >>> 10)) + w[i - 7] | 0; }
  a = h[0]; b = h[1]; c = h[2]; d = h[3]; e = h[4]; f = h[5]; g = h[6]; k = h[7];
  for (i = 0; i < 64; i++) {
    t1 = k + (((e >>> 6) | (e << 26)) ^ ((e >>> 11) | (e << 21)) ^ ((e >>> 25) | (e << 7))) + ((e & f) ^ (~e & g)) + K[i] + w[i] | 0;
    t2 = (((a >>> 2) | (a << 30)) ^ ((a >>> 13) | (a << 19)) ^ ((a >>> 22) | (a << 10))) + ((a & b) ^ (a & c) ^ (b & c)) | 0;
    k = g; g = f; f = e; e = d + t1 | 0; d = c; c = b; b = a; a = t1 + t2 | 0; }
  h[0] = h[0] + a | 0; h[1] = h[1] + b | 0; h[2] = h[2] + c | 0; h[3] = h[3] + d | 0;
  h[4] = h[4] + e | 0; h[5] = h[5] + f | 0; h[6] = h[6] + g | 0; h[7] = h[7] + k | 0; };
Sha.prototype.them = function (m) { var i = 0, l = m.length; this.len += l;
  if (this.n) { while (this.n < 64 && i < l) this.b[this.n++] = m[i++]; if (this.n === 64) { this.khoi(this.b, 0); this.n = 0; } }
  for (; i + 64 <= l; i += 64) this.khoi(m, i);
  while (i < l) this.b[this.n++] = m[i++]; return this; };
Sha.prototype.xong = function () { var bit = this.len * 8, pl = (this.n < 56 ? 56 - this.n : 120 - this.n) + 8, p = new Uint8Array(pl),
  hi = Math.floor(bit / 4294967296), lo = bit >>> 0, r = new Uint8Array(32), i;
  p[0] = 0x80; p[pl - 8] = hi >>> 24; p[pl - 7] = (hi >>> 16) & 255; p[pl - 6] = (hi >>> 8) & 255; p[pl - 5] = hi & 255;
  p[pl - 4] = lo >>> 24; p[pl - 3] = (lo >>> 16) & 255; p[pl - 2] = (lo >>> 8) & 255; p[pl - 1] = lo & 255; this.them(p);
  for (i = 0; i < 8; i++) { r[4 * i] = this.h[i] >>> 24; r[4 * i + 1] = (this.h[i] >>> 16) & 255;
    r[4 * i + 2] = (this.h[i] >>> 8) & 255; r[4 * i + 3] = this.h[i] & 255; } return r; };
function ghep(a, b) { var r = new Uint8Array(a.length + b.length); r.set(a); r.set(b, a.length); return r; }
function hexRa(u) { var s = "", i; for (i = 0; i < u.length; i++) s += (u[i] < 16 ? "0" : "") + u[i].toString(16); return s; }
function hexVao(s) { var r = new Uint8Array(s.length / 2), i; for (i = 0; i < r.length; i++) r[i] = parseInt(s.substr(2 * i, 2), 16); return r; }
function chuAscii(s) { var r = new Uint8Array(s.length), i; for (i = 0; i < s.length; i++) r[i] = s.charCodeAt(i); return r; }
function hmac(k, phan) { var b = new Uint8Array(64), ik = new Uint8Array(64), ok = new Uint8Array(64), i, t;
  b.set(k.length > 64 ? new Sha().them(k).xong() : k);
  for (i = 0; i < 64; i++) { ik[i] = b[i] ^ 0x36; ok[i] = b[i] ^ 0x5c; }
  t = new Sha().them(ik); for (i = 0; i < phan.length; i++) t.them(phan[i]);
  return new Sha().them(ok).them(t.xong()).xong(); }
function maHoa(khoa, nonce, du) { var ct = new Uint8Array(du.length), dau = new Uint8Array(36), i, j, ks, dem = 0;
  dau.set(khoa); dau.set(nonce, 16);
  for (i = 0; i < du.length; i += 32) { dau[32] = dem >>> 24; dau[33] = (dem >>> 16) & 255; dau[34] = (dem >>> 8) & 255;
    dau[35] = dem & 255; dem++; ks = new Sha().them(dau).xong();
    for (j = 0; j < 32 && i + j < du.length; j++) ct[i + j] = du[i + j] ^ ks[j]; }
  return {ct: ct, kiem: hexRa(hmac(new Sha().them(ghep(chuAscii("LARC-MAC1"), khoa)).xong(), [nonce, ct]))}; }
var KHOA = (function () { var m = /k=([0-9a-f]{32})/.exec(location.hash || ""); return m ? hexVao(m[1]) : null; })();
if (KHOA) { var bm = document.getElementById("bao_mat"); if (bm) bm.textContent = "Kết nối có mã hóa (khóa từ mã QR).";
  try { history.replaceState(null, "", location.pathname); } catch (e) {} }
window.LARC_WIFI = {Sha: Sha, hmac: hmac, maHoa: maHoa, hexRa: hexRa, hexVao: hexVao};
function docFile(f) { return new Promise(function (xong, loi) { var r = new FileReader();
  r.onload = function () { xong(new Uint8Array(r.result)); }; r.onerror = function () { loi(r.error); }; r.readAsArrayBuffer(f); }); }
function guiMot(f, d) { return new Promise(function (xong) { var x = new XMLHttpRequest();
  x.open("POST", "tai_len"); x.setRequestHeader("X-Ten-File", encodeURIComponent(f.name));
  x.upload.onprogress = function (e) { if (e.lengthComputable) d.textContent = f.name + ": đang gửi " +
    Math.round(e.loaded * 100 / e.total) + "%"; };
  x.onload = function () { var kq = {}; try { kq = JSON.parse(x.responseText); } catch (e) { kq = {loi: x.statusText}; }
    d.className = "dong " + (x.status === 200 ? "dat" : "loi");
    d.textContent = f.name + ": " + (x.status === 200 ? "đã gửi - xem trên máy tính" : (kq.loi || "lỗi " + x.status)); xong(); };
  x.onerror = function () { d.className = "dong loi"; d.textContent = f.name + ": không kết nối được máy tính"; xong(); };
  if (!KHOA) { x.send(f); return; }
  d.textContent = f.name + ": đang mã hóa…";
  docFile(f).then(function (du) { var nonce = new Uint8Array(16); crypto.getRandomValues(nonce);
    var g = maHoa(KHOA, nonce, du); x.setRequestHeader("X-Ma-Hoa", "sha256ctr1"); x.setRequestHeader("X-Nonce", hexRa(nonce));
    x.setRequestHeader("X-Ma-Kiem", g.kiem); x.send(g.ct); },
    function () { d.className = "dong loi"; d.textContent = f.name + ": không đọc được file"; xong(); }); }); }
gui.addEventListener("click", function () { gui.disabled = true; var c = ds.children, p = Promise.resolve();
  Array.prototype.forEach.call(tep.files, function (f, i) { p = p.then(function () { return guiMot(f, c[i]); }); });
  p.then(function () { gui.disabled = false; }); });
</script></body></html>'''


class MayNhan:
    """Một phiên nhận: bat_dau() -> địa chỉ (http://ip:cổng/<mã>/); file nhận xong đưa vào hang (dict file, ten, co, luc) cho giao
    diện lấy; dung() tắt máy chủ. Thư mục nhận giữ lại sau khi tắt (file chưa nhập vẫn mở lại được)."""

    def __init__(self, ip: str | None = None, thu_muc: Path | None = None, ten_may: str = ''):
        from .dia_phuong import thu_muc_may
        self.ip = ip
        # 1.0.51: mã phiên 16 ký tự chữ / số (96 bit) - máy khác cùng Wi-Fi không đoán được đường dẫn nhận
        self.ma = secrets.token_urlsafe(12).replace('-', 'a').replace('_', 'b')
        self.thu_muc = Path(thu_muc) if thu_muc else thu_muc_may() / THU_MUC / f'{datetime.now():%Y%m%d_%H%M%S}_{self.ma[:4]}'
        self.ten_may = ten_may or socket.gethostname()
        self.khoa_qr = secrets.token_hex(16)             # 1.0.55: khóa mã hóa gói tin (128 bit) - chỉ nằm trong mã QR, sau dấu #
        self.hang = queue.Queue()
        self.so_file = 0
        self.tong_byte = 0
        self._khoa = threading.Lock()
        self._may = None
        self._luong = None

    @property
    def url(self) -> str:
        if self._may is None:
            return ''
        return f'http://{self.ip}:{self._may.server_address[1]}/{self.ma}/'

    @property
    def url_qr(self) -> str:
        """Địa chỉ trong mã QR: kèm khóa phiên sau '#' (trình duyệt không gửi phần này qua mạng)."""
        return f'{self.url}#k={self.khoa_qr}' if self.url else ''

    @property
    def dang_chay(self) -> bool:
        return self._may is not None

    def bat_dau(self) -> str:
        if self._may is not None:
            return self.url
        if not self.ip:
            ds = dia_chi_noi_bo()
            if not ds:
                raise LoiNhanWifi('Máy tính chưa kết nối mạng nội bộ (Wi-Fi / mạng dây): không có địa chỉ để điện thoại gửi tới.')
            self.ip = ds[0]
        loi = None
        for cong in CONG_UU_TIEN + (0,):
            try:
                self._may = ThreadingHTTPServer((self.ip, cong), _tao_xu_ly(self))
                break
            except OSError as e:
                loi = e
        if self._may is None:
            raise LoiNhanWifi(f'Không mở được cổng nhận trên {self.ip}: {loi}')
        self._may.daemon_threads = True
        self._luong = threading.Thread(target=self._may.serve_forever, kwargs={'poll_interval': 0.3}, daemon=True)
        self._luong.start()
        return self.url

    def dung(self) -> None:
        may, self._may = self._may, None
        if may is not None:
            may.shutdown()
            may.server_close()

    def ds_file(self) -> list:
        """File .json đã nhận trong thư mục của phiên (kể cả trước khi mở lại hộp)."""
        if not self.thu_muc.is_dir():
            return []
        return sorted(self.thu_muc.glob('*.json'))

    # ---- gọi từ luồng của máy chủ
    def _nhan(self, ten: str, luong, co: int, giai: GiaiMa | None = None, ma_kiem: str = '') -> Path:
        from .an_toan import LoiAnToan, kiem_tra_magic_bytes
        if co <= 0:
            raise LoiNhanWifi('File rỗng.')
        if co > KICH_TOI_DA:
            raise LoiNhanWifi(f'File quá lớn ({co // (1024 * 1024)} MB, tối đa {KICH_TOI_DA // (1024 * 1024)} MB).')
        with self._khoa:
            if self.so_file >= SO_FILE_TOI_DA:
                raise LoiNhanWifi(f'Đã nhận đủ {SO_FILE_TOI_DA} file trong phiên này: đóng rồi mở lại hộp nhận trên máy tính.')
            if self.tong_byte + co > TONG_TOI_DA:
                raise LoiNhanWifi(f'Phiên này đã nhận gần {TONG_TOI_DA // (1024 * 1024)} MB: đóng rồi mở lại hộp nhận trên máy tính.')
            self.so_file += 1
            self.tong_byte += co
            self.thu_muc.mkdir(parents=True, exist_ok=True)
            dich = self.thu_muc / ten_an_toan(ten)
            k = 2
            while dich.exists():
                dich = dich.with_name(f'{dich.stem.rsplit("~", 1)[0]}~{k}.json')
                k += 1
            tam = dich.with_name(dich.name + '.dang_nhan')
            tam.touch()                                 # giữ tên (hai file cùng tên gửi song song)
        try:
            con_lai = co
            with open(tam, 'wb') as f:
                while con_lai > 0:
                    khoi = luong.read(min(KHOI, con_lai))
                    if not khoi:
                        raise LoiNhanWifi('Kết nối bị ngắt giữa chừng: gửi lại file.')
                    f.write(giai.xu_ly(khoi) if giai is not None else khoi)
                    con_lai -= len(khoi)
            if giai is not None and not giai.khop(ma_kiem):
                raise LoiNhanWifi('Gói tin không khớp mã kiểm (bị sửa trên đường truyền hoặc sai khóa phiên): quét lại mã QR rồi gửi lại.')
            try:
                kiem_tra_magic_bytes(tam, {'json'}, ten)
            except LoiAnToan as e:
                raise LoiNhanWifi(f'{e} Chỉ nhận file kết quả .json của LARC Mobile.') from None
            os.replace(tam, dich)
        except BaseException:
            try:
                tam.unlink()
            except OSError:
                pass
            raise
        self.hang.put(dict(file=dich, ten=str(ten), co=co, luc=datetime.now().strftime('%H:%M:%S')))
        return dich


def _tao_xu_ly(may: MayNhan):
    class XuLy(BaseHTTPRequestHandler):
        server_version = 'LARC'
        sys_version = ''
        timeout = 60                                # giây chờ mỗi lần đọc / ghi socket: kết nối treo không giữ luồng mãi

        def log_message(self, *a):                  # không ghi ra màn hình / stderr
            pass

        def _tra(self, ma: int, than: bytes, loai: str):
            self.send_response(ma)
            self.send_header('Content-Type', loai)
            self.send_header('Content-Length', str(len(than)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.end_headers()
            self.wfile.write(than)

        def _json(self, ma: int, d: dict):
            self._tra(ma, json.dumps(d, ensure_ascii=False).encode('utf-8'), 'application/json; charset=utf-8')

        def do_GET(self):
            if self.path.split('?')[0] in (f'/{may.ma}/', f'/{may.ma}'):
                trang = TRANG.replace('@@MAY@@', may.ten_may.replace('<', '').replace('&', ''))
                return self._tra(200, trang.encode('utf-8'), 'text/html; charset=utf-8')
            self._tra(404, b'Khong co trang nay.', 'text/plain; charset=utf-8')

        def do_POST(self):
            if self.path.split('?')[0] != f'/{may.ma}/tai_len':
                self.close_connection = True
                return self._tra(404, b'Khong co trang nay.', 'text/plain; charset=utf-8')
            try:
                co = int(self.headers.get('Content-Length') or 0)
            except ValueError:
                co = 0
            ten = unquote(self.headers.get('X-Ten-File') or 'ket_qua.json')
            giai = None
            kieu = (self.headers.get('X-Ma-Hoa') or '').strip()
            if kieu:
                try:
                    nonce = bytes.fromhex(self.headers.get('X-Nonce') or '')
                except ValueError:
                    nonce = b''
                if kieu != MA_HOA or len(nonce) != 16:
                    self.close_connection = True
                    return self._json(400, {'loi': 'Kiểu mã hóa không hỗ trợ - tải lại trang bằng mã QR mới trên máy tính.'})
                giai = GiaiMa(bytes.fromhex(may.khoa_qr), nonce)
            try:
                dich = may._nhan(ten, self.rfile, co, giai, self.headers.get('X-Ma-Kiem') or '')
            except LoiNhanWifi as e:
                self.close_connection = True            # phần thân chưa đọc hết: không dùng lại kết nối
                return self._json(413 if 'quá lớn' in str(e) else 400, {'loi': str(e)})
            except OSError as e:
                self.close_connection = True
                return self._json(500, {'loi': f'Máy tính không ghi được file: {e}'})
            self._json(200, {'ok': True, 'ten': dich.name})
    return XuLy

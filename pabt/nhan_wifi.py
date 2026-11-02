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


class LoiNhanWifi(Exception):
    pass


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
<small>Trang này chỉ dùng được khi điện thoại và máy tính cùng mạng Wi-Fi và hộp "Nhận từ điện thoại" trên máy tính đang mở.</small>
</main><script>
"use strict";
var tep = document.getElementById("tep"), ds = document.getElementById("ds"), gui = document.getElementById("gui");
function dong(ten, chu, lop) { var d = document.createElement("div"); d.className = "dong " + (lop || "cho");
  d.textContent = ten + ": " + chu; ds.appendChild(d); return d; }
tep.addEventListener("change", function () { ds.textContent = ""; for (var i = 0; i < tep.files.length; i++)
  dong(tep.files[i].name, "chưa gửi"); gui.disabled = tep.files.length === 0; });
function guiMot(f, d) { return new Promise(function (xong) { var x = new XMLHttpRequest();
  x.open("POST", "tai_len"); x.setRequestHeader("X-Ten-File", encodeURIComponent(f.name));
  x.upload.onprogress = function (e) { if (e.lengthComputable) d.textContent = f.name + ": đang gửi " +
    Math.round(e.loaded * 100 / e.total) + "%"; };
  x.onload = function () { var kq = {}; try { kq = JSON.parse(x.responseText); } catch (e) { kq = {loi: x.statusText}; }
    d.className = "dong " + (x.status === 200 ? "dat" : "loi");
    d.textContent = f.name + ": " + (x.status === 200 ? "đã gửi - xem trên máy tính" : (kq.loi || "lỗi " + x.status)); xong(); };
  x.onerror = function () { d.className = "dong loi"; d.textContent = f.name + ": không kết nối được máy tính"; xong(); };
  x.send(f); }); }
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
    def _nhan(self, ten: str, luong, co: int) -> Path:
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
                    f.write(khoi)
                    con_lai -= len(khoi)
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
            try:
                dich = may._nhan(ten, self.rfile, co)
            except LoiNhanWifi as e:
                self.close_connection = True            # phần thân chưa đọc hết: không dùng lại kết nối
                return self._json(413 if 'quá lớn' in str(e) else 400, {'loi': str(e)})
            except OSError as e:
                self.close_connection = True
                return self._json(500, {'loi': f'Máy tính không ghi được file: {e}'})
            self._json(200, {'ok': True, 'ten': dich.name})
    return XuLy

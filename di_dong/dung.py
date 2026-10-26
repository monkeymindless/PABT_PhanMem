"""Dựng ứng dụng điện thoại LARC Field Mobile (dự án riêng, KHÔNG dùng mã của LARC bản máy tính - xem README.md) -> <repo>\\bo_cai\\:

  LARC_FieldMobile_<ver>.apk          Android 7.0 (API 24) trở lên, cài trực tiếp (bật "Cho phép cài ứng dụng không rõ nguồn").
  LARC_FieldMobile_PWA_<ver>.zip      iPhone / iPad (và Android không cài .apk): đặt các file lên một địa chỉ HTTPS, mở bằng Safari ->
                                      Chia sẻ -> "Thêm vào MH chính". Chạy không cần mạng sau lần mở đầu.

Cả hai dựng từ CÙNG mẫu ung_dung/index.html (chế độ 'android' / 'pwa'), không chứa dữ liệu dự án: dữ liệu gửi sang bằng file .json
"larc_field_du_lieu" (LARC bản máy tính: Công cụ -> Phiếu kiểm đếm thực địa -> "Xuất dữ liệu cho ứng dụng điện thoại").

Android dựng KHÔNG cần Android Studio / Gradle: aapt2 (tài nguyên + manifest), javac (JDK 17), d8 (dex), zipalign, apksigner - từ
thư mục công cụ (biến LARC_ANDROID, mặc định <thư mục cha của repo>\\cong_cu_android: jdk17\\, sdk\\build-tools\\34.0.0\\,
sdk\\platforms\\android-34\\). Khóa ký: LARC_KHOA_APK (mặc định <thư mục cha của repo>\\khoa_android\\larc_field.jks, mật khẩu ở
matkhau.txt cạnh nó; chưa có thì tạo). GIỮ KỸ khóa này: bản cập nhật phải ký cùng khóa, mất khóa thì máy đã cài phải gỡ rồi cài lại
(mất số liệu chưa gửi). Vẽ biểu tượng cần PySide6 (dùng .venv của repo).

    .venv\\Scripts\\python di_dong\\dung.py [--chi-pwa] [--chi-apk]
"""
from __future__ import annotations
import json
import os
import secrets
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

PHIEN_BAN = '1.1.0'                 # phiên bản RIÊNG của ứng dụng điện thoại (tăng mỗi lần phát hành .apk / PWA)
DAY = Path(__file__).resolve().parent
REPO = DAY.parent
MAU = DAY / 'ung_dung' / 'index.html'
BIEU_TUONG = DAY / 'bieu_tuong.png'
NGUON_ANDROID = DAY / 'android'
CONG_CU = Path(os.environ.get('LARC_ANDROID') or REPO.parent / 'cong_cu_android')
KHOA = Path(os.environ.get('LARC_KHOA_APK') or REPO.parent / 'khoa_android' / 'larc_field.jks')
BIET_DANH = 'larc_field'
RA = REPO / 'bo_cai'
API_MIN, API_DICH, BUILD_TOOLS = 24, 34, '34.0.0'
CHE_DO = ('pwa', 'android')
TEN_UNG_DUNG, TEN_NGAN = 'LARC Field Mobile', 'LARC Field'
# biểu tượng của vỏ ứng dụng: (tên file, cỡ px, lề mỗi bên, màu nền - "maskable" cần nền kín, hình trong vùng an toàn)
BIEU_TUONG_PWA = (('icon-180.png', 180, 0.0, ''), ('icon-192.png', 192, 0.0, ''), ('icon-512.png', 512, 0.0, ''),
                  ('icon-maskable-512.png', 512, 0.12, '#FFFFFF'))
# biểu tượng trình khởi chạy Android: (thư mục mipmap, cỡ px)
MIPMAP = (('mipmap-mdpi', 48), ('mipmap-hdpi', 72), ('mipmap-xhdpi', 96), ('mipmap-xxhdpi', 144), ('mipmap-xxxhdpi', 192))
HUONG_DAN_PWA = """LARC Field Mobile - bản cài cho iPhone / iPad (PWA)

1. Đặt TOÀN BỘ các file trong gói này (index.html, manifest.webmanifest, sw.js, icon-*.png) vào cùng một thư mục trên một
   địa chỉ HTTPS (ví dụ GitHub Pages, máy chủ web của đơn vị có chứng chỉ HTTPS). Không cần máy chủ chạy chương trình:
   chỉ là file tĩnh. Các file KHÔNG chứa dữ liệu dự án.
2. Trên iPhone: mở địa chỉ đó bằng Safari -> nút Chia sẻ -> "Thêm vào MH chính". Mở ứng dụng từ biểu tượng LARC Field.
   Sau lần mở đầu ứng dụng chạy không cần mạng.
3. Trên máy tính: LARC -> Công cụ -> Phiếu kiểm đếm thực địa -> "Xuất dữ liệu cho ứng dụng điện thoại…" -> gửi file .json sang
   iPhone (Zalo, email, AirDrop) -> trong ứng dụng bấm "Chọn file dữ liệu dự án…".
4. Ghi xong: thẻ "6. Xuất .JSON" -> Gửi (Zalo / Lưu vào Tệp) -> trên máy tính "Nhập kết quả kiểm đếm (.json)…".

Lưu ý: số liệu ghi lưu trong ứng dụng trên iPhone; xóa ứng dụng khỏi MH chính là mất số liệu chưa gửi. Mở trang bằng
file:// hoặc http:// (không HTTPS) thì không cài được và không định vị GPS được.
"""


# ---------------------------------------------------------------- vỏ ứng dụng (index.html + biểu tượng + manifest + service worker)
def anh_bieu_tuong(co: int, le: float = 0.0, nen: str = '') -> bytes:
    """bieu_tuong.png thu về `co` px (Qt), lề `le` mỗi bên, nền `nen` (trống = trong suốt)."""
    from PySide6.QtCore import QBuffer, QByteArray, QIODevice, QRect, Qt
    from PySide6.QtGui import QColor, QGuiApplication, QImage, QPainter
    _app = QGuiApplication.instance() or QGuiApplication([])    # noqa: F841 - QPainter cần ứng dụng Qt
    anh = QImage.fromData(BIEU_TUONG.read_bytes())
    if anh.isNull():
        raise SystemExit(f'Không đọc được biểu tượng {BIEU_TUONG}')
    ra = QImage(co, co, QImage.Format.Format_ARGB32)
    ra.fill(QColor(nen) if nen else Qt.GlobalColor.transparent)
    trong = max(1, round(co * (1 - 2 * le)))
    hinh = anh.scaled(trong, trong, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
    p = QPainter(ra)
    p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
    p.drawImage(QRect((co - hinh.width()) // 2, (co - hinh.height()) // 2, hinh.width(), hinh.height()), hinh)
    p.end()
    ba = QByteArray()
    buf = QBuffer(ba)
    buf.open(QIODevice.OpenModeFlag.WriteOnly)
    ra.save(buf, 'PNG')
    buf.close()
    return bytes(ba.data())


def _dau_pwa() -> str:
    return ('<link rel="manifest" href="manifest.webmanifest"/>\n<meta name="apple-mobile-web-app-capable" content="yes"/>\n'
            '<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent"/>\n'
            f'<meta name="apple-mobile-web-app-title" content="{TEN_NGAN}"/>')


def html_ung_dung(che_do: str, ver: str = PHIEN_BAN) -> str:
    """index.html của vỏ ứng dụng ('pwa' / 'android')."""
    if che_do not in CHE_DO:
        raise ValueError(che_do)
    s = MAU.read_text(encoding='utf-8')
    return (s.replace('@@DAU_PWA@@', _dau_pwa() if che_do == 'pwa' else '').replace('@@CHE_DO@@', che_do)
            .replace('@@PHIEN_BAN@@', ver))


def manifest_pwa(ver: str = PHIEN_BAN) -> dict:
    return dict(name=TEN_UNG_DUNG, short_name=TEN_NGAN, description='Kiểm đếm thực địa bồi thường, hỗ trợ, tái định cư - chạy không cần mạng',
                lang='vi', start_url='./', scope='./', display='standalone', orientation='any', background_color='#F8FAFC',
                theme_color='#2F5F9E', version=ver,
                icons=[dict(src=t, sizes=f'{c}x{c}', type='image/png', purpose='maskable' if nen else 'any')
                       for t, c, _, nen in BIEU_TUONG_PWA if c >= 192])


def sw_pwa(ds_file, ver: str = PHIEN_BAN) -> str:
    """Service worker: lưu mọi file của ứng dụng vào bộ nhớ đệm khi cài (chạy không mạng); bản mới (tên bộ nhớ đệm mới) thay bản cũ."""
    return ('"use strict";\n'
            f'const BO = "larc-field-{ver}", TEP = {json.dumps(["./"] + list(ds_file))};\n'
            'self.addEventListener("install", e => { e.waitUntil(caches.open(BO).then(c => c.addAll(TEP)).then(() => self.skipWaiting())); });\n'
            'self.addEventListener("activate", e => { e.waitUntil(caches.keys().then(ds => Promise.all(ds.filter(k => k.startsWith("larc-field-") '
            '&& k !== BO).map(k => caches.delete(k)))).then(() => self.clients.claim())); });\n'
            'self.addEventListener("fetch", e => { if (e.request.method !== "GET") return;\n'
            '  e.respondWith(caches.match(e.request, {ignoreSearch: true}).then(r => r || fetch(e.request).catch(() =>\n'
            '    e.request.mode === "navigate" ? caches.match("./index.html") : Response.error()))); });\n')


def tep_ung_dung(che_do: str, ver: str = PHIEN_BAN) -> dict:
    """{tên file: bytes}: index.html + biểu tượng (+ manifest, sw.js với PWA; Android chỉ icon-180 - biểu tượng máy ở res/mipmap)."""
    tep = {'index.html': html_ung_dung(che_do, ver).encode('utf-8')}
    for ten, co, le, nen in BIEU_TUONG_PWA:
        if che_do == 'pwa' or ten == 'icon-180.png':
            tep[ten] = anh_bieu_tuong(co, le, nen)
    if che_do == 'pwa':
        tep['manifest.webmanifest'] = json.dumps(manifest_pwa(ver), ensure_ascii=False, indent=1).encode('utf-8')
        tep['sw.js'] = sw_pwa(sorted(tep), ver).encode('utf-8')
    return tep


# ---------------------------------------------------------------- dựng
def ma_phien_ban(ver: str) -> int:
    """'1.1.0' -> 10100 (versionCode Android tăng dần: 1.9.99 -> 10999, 2.0.0 -> 20000)."""
    so = [int(x) for x in ver.split('.')[:3]] + [0, 0, 0]
    return so[0] * 10000 + so[1] * 100 + so[2]


def _chay(lenh, **kw) -> None:
    print('>', ' '.join(str(x) for x in lenh[:4]), '…')
    kq = subprocess.run([str(x) for x in lenh], capture_output=True, text=True, encoding='utf-8', errors='replace', **kw)
    if kq.returncode != 0:
        raise SystemExit(f'Lỗi ({kq.returncode}): {" ".join(str(x) for x in lenh[:3])}\n{kq.stdout[-3000:]}\n{kq.stderr[-3000:]}')


def cong_cu() -> dict:
    jdk = CONG_CU / 'jdk17' / 'bin'
    bt = CONG_CU / 'sdk' / 'build-tools' / BUILD_TOOLS
    cc = dict(java=jdk / 'java.exe', javac=jdk / 'javac.exe', keytool=jdk / 'keytool.exe', aapt2=bt / 'aapt2.exe',
              zipalign=bt / 'zipalign.exe', d8=bt / 'lib' / 'd8.jar', apksigner=bt / 'lib' / 'apksigner.jar',
              android_jar=CONG_CU / 'sdk' / 'platforms' / f'android-{API_DICH}' / 'android.jar')
    thieu = [str(p) for p in cc.values() if not p.exists()]
    if thieu:
        raise SystemExit('Thiếu công cụ dựng Android (đặt LARC_ANDROID):\n  ' + '\n  '.join(thieu))
    return cc


def khoa_ky(cc: dict) -> tuple:
    """(file khóa, mật khẩu). Chưa có: tạo khóa RSA 4096, hạn 30 năm."""
    mk_file = KHOA.with_name('matkhau.txt')
    if KHOA.exists():
        return KHOA, mk_file.read_text(encoding='utf-8').strip()
    KHOA.parent.mkdir(parents=True, exist_ok=True)
    mk = secrets.token_urlsafe(24)
    _chay([cc['keytool'], '-genkeypair', '-keystore', KHOA, '-alias', BIET_DANH, '-keyalg', 'RSA', '-keysize', '4096',
           '-validity', '10950', '-storetype', 'PKCS12', '-storepass', mk, '-keypass', mk,
           '-dname', 'CN=LARC Field Mobile, O=LARC, C=VN'])
    mk_file.write_text(mk + '\n', encoding='utf-8')
    print(f'Đã tạo khóa ký mới: {KHOA} (mật khẩu: {mk_file}) - GIỮ KỸ, sao lưu ra nơi khác.')
    return KHOA, mk


def dung_pwa(ver: str = PHIEN_BAN) -> Path:
    ra = RA / f'LARC_FieldMobile_PWA_{ver}.zip'
    RA.mkdir(parents=True, exist_ok=True)
    tam = ra.with_name(ra.name + '.tmp')
    with zipfile.ZipFile(tam, 'w', zipfile.ZIP_DEFLATED) as z:
        for ten, du in sorted(tep_ung_dung('pwa', ver).items()):
            z.writestr(ten, du)
        z.writestr('HUONG_DAN_CAI_DAT.txt', HUONG_DAN_PWA.replace('\n', '\r\n'))
    tam.replace(ra)
    print('PWA:', ra)
    return ra


def dung_apk(ver: str = PHIEN_BAN) -> Path:
    cc = cong_cu()
    khoa, mk = khoa_ky(cc)
    RA.mkdir(parents=True, exist_ok=True)
    ra = RA / f'LARC_FieldMobile_{ver}.apk'
    with tempfile.TemporaryDirectory(prefix='larc_apk_') as td:
        t = Path(td)
        # tài nguyên: chuỗi + biểu tượng trình khởi chạy (nền trắng, lề vừa vùng bo tròn)
        res = t / 'res'
        shutil.copytree(NGUON_ANDROID / 'res', res)
        for thu, co in MIPMAP:
            (res / thu).mkdir(parents=True, exist_ok=True)
            (res / thu / 'ic_launcher.png').write_bytes(anh_bieu_tuong(co, 0.06, '#FFFFFF'))
        assets = t / 'assets'
        assets.mkdir()
        for ten, du in tep_ung_dung('android', ver).items():
            (assets / ten).write_bytes(du)
        _chay([cc['aapt2'], 'compile', '--dir', res, '-o', t / 'res.zip'])
        _chay([cc['aapt2'], 'link', '-o', t / 'goc.apk', '-I', cc['android_jar'], '--manifest', NGUON_ANDROID / 'AndroidManifest.xml',
               '-A', assets, '--min-sdk-version', API_MIN, '--target-sdk-version', API_DICH, '--version-code', ma_phien_ban(ver),
               '--version-name', ver, t / 'res.zip'])
        # mã Java -> dex
        src = t / 'src'
        shutil.copytree(NGUON_ANDROID / 'src', src)
        (src / 'vn' / 'larc' / 'field' / 'BuildConfigTen.java').write_text(
            f'package vn.larc.field;\n\nfinal class BuildConfigTen {{\n    static final String PHIEN_BAN = "{ver}";\n}}\n', encoding='utf-8')
        lop = t / 'classes'
        lop.mkdir()
        _chay([cc['javac'], '-encoding', 'UTF-8', '-source', '8', '-target', '8', '-Xlint:-options', '-bootclasspath', cc['android_jar'],
               '-d', lop] + sorted(src.rglob('*.java')))
        dex = t / 'dex'
        dex.mkdir()
        _chay([cc['java'], '-cp', cc['d8'], 'com.android.tools.r8.D8', '--release', '--min-api', API_MIN, '--lib', cc['android_jar'],
               '--output', dex] + sorted(lop.rglob('*.class')))
        shutil.copy(t / 'goc.apk', t / 'chua_ky.apk')
        with zipfile.ZipFile(t / 'chua_ky.apk', 'a', zipfile.ZIP_DEFLATED) as z:
            z.write(dex / 'classes.dex', 'classes.dex')
        _chay([cc['zipalign'], '-p', '-f', '4', t / 'chua_ky.apk', t / 'can.apk'])
        _chay([cc['java'], '-jar', cc['apksigner'], 'sign', '--ks', khoa, '--ks-key-alias', BIET_DANH, '--ks-pass', f'pass:{mk}',
               '--key-pass', f'pass:{mk}', '--out', t / 'da_ky.apk', t / 'can.apk'])
        _chay([cc['java'], '-jar', cc['apksigner'], 'verify', '--min-sdk-version', API_MIN, t / 'da_ky.apk'])
        shutil.copy(t / 'da_ky.apk', ra.with_name(ra.name + '.tmp'))
        ra.with_name(ra.name + '.tmp').replace(ra)
    print('APK:', ra, f'({ra.stat().st_size // 1024} KB)')
    return ra


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
    if '--chi-apk' not in argv:
        dung_pwa()
    if '--chi-pwa' not in argv:
        dung_apk()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

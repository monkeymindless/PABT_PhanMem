"""Dựng ứng dụng điện thoại LARC Mobile (dự án riêng, KHÔNG dùng mã của LARC bản máy tính - xem README.md) -> <repo>\\bo_cai\\:

  LARC_Mobile_<ver>.apk          Android 7.0 (API 24) trở lên, cài trực tiếp (bật "Cho phép cài ứng dụng không rõ nguồn").
  LARC_Mobile_PWA_<ver>.zip      iPhone / iPad (và Android không cài .apk): đặt các file lên một địa chỉ HTTPS, mở bằng Safari ->
                                      Chia sẻ -> "Thêm vào MH chính". Chạy không cần mạng sau lần mở đầu.
  LARC_Mobile_Web_<ver>\\        gói đưa lên trang web miễn phí (GitHub Pages / Netlify / Cloudflare Pages): tai_len\\ = ứng dụng PWA +
                                      cai-dat.html (trang cài đặt có mã QR của địa chỉ trang, hướng dẫn iPhone / Android) + file .apk;
                                      HUONG_DAN.txt = các bước đưa lên GitHub Pages. Địa chỉ trang: --url https://... (nhớ ở dia_chi_web.txt).

Cả hai dựng từ CÙNG mẫu ung_dung/index.html (chế độ 'android' / 'pwa'), không chứa dữ liệu dự án: dữ liệu gửi sang bằng file .json
"larc_field_du_lieu" (LARC bản máy tính: Công cụ -> Phiếu kiểm đếm thực địa -> "Xuất dữ liệu cho ứng dụng điện thoại").

Android dựng KHÔNG cần Android Studio / Gradle: aapt2 (tài nguyên + manifest), javac (JDK 17), d8 (dex), zipalign, apksigner - từ
thư mục công cụ (biến LARC_ANDROID, mặc định <thư mục cha của repo>\\cong_cu_android: jdk17\\, sdk\\build-tools\\34.0.0\\,
sdk\\platforms\\android-34\\). Khóa ký: LARC_KHOA_APK (mặc định <thư mục cha của repo>\\khoa_android\\larc_field.jks, mật khẩu ở
matkhau.txt cạnh nó; chưa có thì tạo). GIỮ KỸ khóa này: bản cập nhật phải ký cùng khóa, mất khóa thì máy đã cài phải gỡ rồi cài lại
(mất số liệu chưa gửi). Vẽ biểu tượng cần PySide6 (dùng .venv của repo).

    .venv\\Scripts\\python di_dong\\dung.py [--chi-pwa] [--chi-apk] [--url https://<tên>.github.io/larc-field/]
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

DAY = Path(__file__).resolve().parent
REPO = DAY.parent


def _phien_ban_may_tinh() -> str:
    """Số phiên bản LARC máy tính (__version__ trong pabt/__init__.py, đọc như chữ - dự án này không nhập mã pabt)."""
    import re
    m = re.search(r"__version__\s*=\s*'([0-9.]+)'", (REPO / 'pabt' / '__init__.py').read_text(encoding='utf-8'))
    if not m:
        raise SystemExit('Không đọc được __version__ trong pabt/__init__.py.')
    return m.group(1)


# 28/10/2026 (người dùng): ĐỒNG BỘ phiên bản với LARC máy tính - máy tính tăng bản nào, ứng dụng điện thoại lấy đúng số đó (trước:
# số riêng 1.1.0 - 1.4.4). Tăng __version__ của máy tính là tăng luôn bản này (bộ nhớ đệm PWA sw.js đặt tên theo phiên bản).
PHIEN_BAN = _phien_ban_may_tinh()
DONG_BO_TU = 10000                  # versionCode Android từ lúc đồng bộ: cộng thêm để luôn lớn hơn 10404 của bản 1.4.4 đã phát hành
MAU = DAY / 'ung_dung' / 'index.html'
BIEU_TUONG = DAY / 'bieu_tuong.png'
DANH_MUC_MAC_DINH = DAY / 'danh_muc_mac_dinh.json'
NGUON_ANDROID = DAY / 'android'
CONG_CU = Path(os.environ.get('LARC_ANDROID') or REPO.parent / 'cong_cu_android')
KHOA = Path(os.environ.get('LARC_KHOA_APK') or REPO.parent / 'khoa_android' / 'larc_field.jks')
BIET_DANH = 'larc_field'
RA = REPO / 'bo_cai'
API_MIN, API_DICH, BUILD_TOOLS = 24, 34, '34.0.0'
CHE_DO = ('pwa', 'android')
TEN_UNG_DUNG, TEN_NGAN = 'LARC Mobile', 'LARC Mobile'
# biểu tượng của vỏ ứng dụng: (tên file, cỡ px, lề mỗi bên, màu nền - "maskable" cần nền kín, hình trong vùng an toàn)
BIEU_TUONG_PWA = (('icon-180.png', 180, 0.0, ''), ('icon-192.png', 192, 0.0, ''), ('icon-512.png', 512, 0.0, ''),
                  ('icon-maskable-512.png', 512, 0.12, '#FFFFFF'))
# biểu tượng trình khởi chạy Android: (thư mục mipmap, cỡ px)
MIPMAP = (('mipmap-mdpi', 48), ('mipmap-hdpi', 72), ('mipmap-xhdpi', 96), ('mipmap-xxhdpi', 144), ('mipmap-xxxhdpi', 192))
HUONG_DAN_PWA = """LARC Mobile - bản cài cho iPhone / iPad (PWA)

1. Đặt TOÀN BỘ các file trong gói này (index.html, manifest.webmanifest, sw.js, icon-*.png) vào cùng một thư mục trên một
   địa chỉ HTTPS (ví dụ GitHub Pages, máy chủ web của đơn vị có chứng chỉ HTTPS). Không cần máy chủ chạy chương trình:
   chỉ là file tĩnh. Các file KHÔNG chứa dữ liệu dự án.
2. Trên iPhone: mở địa chỉ đó bằng Safari -> nút Chia sẻ -> "Thêm vào MH chính". Mở ứng dụng từ biểu tượng LARC Mobile.
   Sau lần mở đầu ứng dụng chạy không cần mạng.
3. Trên máy tính: LARC -> Công cụ -> Phiếu kiểm đếm thực địa -> "Xuất dữ liệu cho ứng dụng điện thoại…" -> gửi file .json sang
   iPhone (Zalo, email, AirDrop) -> trong ứng dụng bấm "Chọn file dữ liệu dự án…".
4. Ghi xong: thẻ "6. Xuất .JSON" -> Gửi (Zalo / Lưu vào Tệp) -> trên máy tính "Nhập kết quả kiểm đếm (.json)…".

Lưu ý: số liệu ghi lưu trong ứng dụng trên iPhone; xóa ứng dụng khỏi MH chính là mất số liệu chưa gửi. Mở trang bằng
file:// hoặc http:// (không HTTPS) thì không cài được và không định vị GPS được.
"""
DIA_CHI_WEB = DAY / 'dia_chi_web.txt'   # địa chỉ trang web đã đặt ứng dụng (lần dựng sau dùng lại)
TEP_APK_WEB = 'LARC_Mobile.apk'    # tên file .apk trên trang web (cố định: đường link / mã QR không đổi theo phiên bản)
HUONG_DAN_WEB = """LARC Mobile - đưa ứng dụng lên trang web miễn phí để cài cho nhiều người (iPhone + Android)

Thư mục tai_len\\ chỉ chứa VỎ ứng dụng (trang web, biểu tượng, file .apk) - KHÔNG có họ tên, CCCD hay số liệu dự án nào.
Dữ liệu dự án vẫn gửi riêng cho từng người (LARC -> Phiếu kiểm đếm thực địa -> Xuất dữ liệu cho ứng dụng điện thoại).

A. ĐƯA LÊN GITHUB PAGES (miễn phí, một lần)
 1. Vào https://github.com -> Sign up, tạo tài khoản (email + mật khẩu). Tên tài khoản sẽ nằm trong địa chỉ trang.
 2. Bấm dấu "+" góc trên phải -> New repository. Repository name: larc-field. Chọn Public (bản miễn phí chỉ
    mở trang web cho kho Public). Bấm Create repository.
 3. Trong trang kho vừa tạo: bấm "uploading an existing file" (hoặc Add file -> Upload files). Mở thư mục tai_len\\,
    chọn TẤT CẢ file bên trong (Ctrl+A) rồi kéo thả vào trang - kéo các FILE, không kéo cả thư mục tai_len.
    Bấm Commit changes.
 4. Settings (thanh trên của kho) -> Pages (cột trái) -> Build and deployment: Source = Deploy from a branch,
    Branch = main, thư mục / (root) -> Save. Đợi 1-2 phút, trang hiện địa chỉ:
        https://<tên tài khoản>.github.io/larc-field/
 5. Dựng lại gói kèm địa chỉ này để trang cài đặt có mã QR đúng:
        di_dong\\DUNG.bat --url https://<tên tài khoản>.github.io/larc-field/
    rồi tải file cai-dat.html mới lên kho (Add file -> Upload files, ghi đè), Commit changes.

B. CÀI CHO TỪNG NGƯỜI
 - Gửi địa chỉ https://<tên tài khoản>.github.io/larc-field/cai-dat.html qua Zalo, hoặc in trang đó ra (có mã QR).
 - iPhone: quét mã QR bằng Camera (hoặc mở đường link) -> nếu đang trong Zalo / Facebook thì chọn "Mở bằng Safari" ->
   bấm "Mở ứng dụng" -> nút Chia sẻ -> "Thêm vào MH chính" -> mở biểu tượng LARC Mobile một lần khi còn mạng.
 - Android: quét mã -> "Tải bản Android (.apk)" -> cài (cho phép cài ứng dụng không rõ nguồn khi máy hỏi);
   hoặc mở ứng dụng bằng Chrome -> menu ⋮ -> "Thêm vào màn hình chính".

C. CẬP NHẬT PHIÊN BẢN MỚI
 - Dựng lại (di_dong\\DUNG.bat), tải toàn bộ file trong tai_len\\ mới lên kho (ghi đè), Commit changes.
   iPhone / Android tự nhận bản mới lần mở tiếp theo khi có mạng; số liệu đã ghi vẫn còn.
 - KHÔNG đổi tên kho / tài khoản: địa chỉ trang đổi thì điện thoại coi là ứng dụng khác (số liệu nằm ở bản cũ).

D. CÁCH KHÁC KHÔNG CẦN GITHUB
 - Netlify Drop: vào https://app.netlify.com/drop, kéo thả cả thư mục tai_len\\ vào, được ngay một địa chỉ https://….
   Đăng ký tài khoản Netlify miễn phí để giữ trang lâu dài (trang tạm không đăng ký bị xóa sau một thời gian).
 - Cloudflare Pages: tương tự (Workers & Pages -> Create -> Pages -> Upload assets).
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


def du_lieu_mac_dinh() -> dict | None:
    """Danh mục đơn giá nhúng sẵn (kiểm đếm độc lập không cần file từ máy tính): file danh_muc_mac_dinh.json do LARC máy tính xuất -
    `chay.py xuat-danh-muc-di-dong di_dong\\danh_muc_mac_dinh.json` (chạy lại khi bộ đơn giá đổi). Không có file: None."""
    try:
        du = json.loads(DANH_MUC_MAC_DINH.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return None
    return du if isinstance(du, dict) and isinstance(du.get('nha'), list) else None


def _json_trong_script(x) -> str:
    """JSON an toàn trong <script> (chữ có '</script>' không đóng thẻ sớm)."""
    return json.dumps(x, ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/').replace('\u2028', '\\u2028').replace('\u2029', '\\u2029')


def html_ung_dung(che_do: str, ver: str = PHIEN_BAN) -> str:
    """index.html của vỏ ứng dụng ('pwa' / 'android')."""
    if che_do not in CHE_DO:
        raise ValueError(che_do)
    s = MAU.read_text(encoding='utf-8')
    md = du_lieu_mac_dinh()
    return (s.replace('@@DAU_PWA@@', _dau_pwa() if che_do == 'pwa' else '').replace('@@CHE_DO@@', che_do)
            .replace('@@PHIEN_BAN@@', ver).replace('@@DU_LIEU_MAC_DINH@@', _json_trong_script(md) if md else 'null'))


def manifest_pwa(ver: str = PHIEN_BAN) -> dict:
    return dict(name=TEN_UNG_DUNG, short_name=TEN_NGAN, description='Kiểm đếm thực địa bồi thường, hỗ trợ, tái định cư - chạy không cần mạng',
                lang='vi', start_url='./', scope='./', display='standalone', orientation='any', background_color='#F8FAFC',
                theme_color='#1E3A8A', version=ver,
                icons=[dict(src=t, sizes=f'{c}x{c}', type='image/png', purpose='maskable' if nen else 'any')
                       for t, c, _, nen in BIEU_TUONG_PWA if c >= 192])


def sw_pwa(ds_file, ver: str = PHIEN_BAN, dau: str = '') -> str:
    """Service worker: lưu mọi file của ứng dụng vào bộ nhớ đệm khi cài (chạy không mạng); bản mới (tên bộ nhớ đệm mới) thay bản cũ.
    dau: dấu nội dung (tep_ung_dung) - từ 1.0.32 số phiên bản đi theo LARC máy tính, sửa riêng ứng dụng điện thoại mà giữ số thì tên bộ
    nhớ đệm vẫn đổi theo nội dung (không thì iPhone giữ bản cũ)."""
    bo = f'larc-field-{ver}' + (f'-{dau}' if dau else '')
    return ('"use strict";\n'
            f'const BO = "{bo}", TEP = {json.dumps(["./"] + list(ds_file))};\n'
            'self.addEventListener("install", e => { e.waitUntil(caches.open(BO).then(c => c.addAll(TEP.map(u => new Request(u, {cache: "reload"})))).then(() => self.skipWaiting())); });\n'
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
        import hashlib
        dau = hashlib.sha256(tep['index.html'] + tep['manifest.webmanifest']).hexdigest()[:10]
        tep['sw.js'] = sw_pwa(sorted(tep), ver, dau).encode('utf-8')
    return tep


# ---------------------------------------------------------------- dựng
def ma_phien_ban(ver: str) -> int:
    """versionCode Android (luôn tăng): '1.0.32' -> 20032, '1.9.99' -> 20999, '2.0.0' -> 30000. Bản đánh số riêng trước khi đồng bộ
    (1.0.31 -> 10031, 1.1.0 -> 10100 … 1.4.4 -> 10404) không cộng DONG_BO_TU - Android không cài đè bản có mã nhỏ hơn."""
    so = [int(x) for x in ver.split('.')[:3]] + [0, 0, 0]
    return DONG_BO_TU + so[0] * 10000 + so[1] * 100 + so[2]


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
           '-dname', 'CN=LARC Mobile, O=LARC, C=VN'])
    mk_file.write_text(mk + '\n', encoding='utf-8')
    print(f'Đã tạo khóa ký mới: {KHOA} (mật khẩu: {mk_file}) - GIỮ KỸ, sao lưu ra nơi khác.')
    return KHOA, mk


def dung_pwa(ver: str = PHIEN_BAN) -> Path:
    ra = RA / f'LARC_Mobile_PWA_{ver}.zip'
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
    ra = RA / f'LARC_Mobile_{ver}.apk'
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


# ---------------------------------------------------------------- gói trang web + trang cài đặt có mã QR
def chuan_dia_chi(url: str) -> str:
    """'https://ten.github.io/larc-field' -> 'https://ten.github.io/larc-field/' (thư mục trang). Chỉ nhận https://."""
    u = (url or '').strip()
    if not u:
        return ''
    if not u.lower().startswith('https://'):
        raise SystemExit(f'Địa chỉ trang phải bắt đầu bằng https:// (iPhone chỉ cài / định vị được trên HTTPS): {u}')
    if u.lower().endswith(('.html', '.htm')):
        u = u.rsplit('/', 1)[0]
    return u.rstrip('/') + '/'


def dia_chi_da_nho() -> str:
    try:
        return chuan_dia_chi(DIA_CHI_WEB.read_text(encoding='utf-8'))
    except (OSError, SystemExit):
        return ''


def trang_cai_dat(url: str, ver: str = PHIEN_BAN, co_apk: bool = True) -> str:
    """cai-dat.html: mã QR của trang cài đặt (in ra / chiếu cho mọi người quét), nút mở ứng dụng, hướng dẫn iPhone / Android.
    Không có url: trang vẫn hướng dẫn, chưa có mã QR (dựng lại với --url)."""
    import html as _h
    import qr
    trang = url + 'cai-dat.html' if url else ''
    o_qr = (f'<div class="qr">{qr.svg(trang, o_px=6)}</div><p class="dc">{_h.escape(trang)}</p>' if trang else
            '<p class="canh">Chưa có mã QR: dựng lại gói với <b>--url https://…</b> (địa chỉ trang sau khi đưa lên).</p>')
    apk = (f'<a class="nut phu" href="{TEP_APK_WEB}" download>Tải bản Android (.apk)</a>' if co_apk else '')
    return f'''<!DOCTYPE html>
<html lang="vi"><head><meta charset="utf-8"/><meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>Cài LARC Mobile</title><link rel="icon" href="icon-180.png"/>
<style>
*{{box-sizing:border-box;font-family:"Segoe UI",Roboto,Arial,sans-serif}}body{{margin:0;background:#F8FAFC;color:#0F172A}}
main{{max-width:720px;margin:0 auto;padding:16px}}.dau{{display:flex;align-items:center;gap:12px}}.dau img{{width:56px;height:56px;border-radius:12px}}
h1{{font-size:20px;margin:0;color:#1E3A8A}}.ghi{{color:#475569;font-size:13px}}
.khung{{background:#fff;border:1px solid #CBD5E1;border-radius:10px;padding:14px;margin:12px 0}}h2{{font-size:16px;margin:0 0 8px;color:#1E3A8A}}
.qr{{text-align:center}}.qr svg{{width:260px;height:260px;max-width:80vw}}.dc{{text-align:center;word-break:break-all;font-size:13px;color:#475569}}
.nut{{display:inline-block;background:#1E3A8A;color:#fff;text-decoration:none;font-weight:700;border-radius:8px;padding:12px 18px;margin:4px 6px 4px 0}}
.nut.phu{{background:#fff;color:#1E3A8A;border:1px solid #CBD5E1}}ol{{padding-left:22px;line-height:1.6;margin:6px 0}}
.canh{{background:#FEF3C7;border:1px solid #F59E0B;color:#7C4A12;border-radius:8px;padding:10px;display:none}}p.canh{{display:block}}
@media print{{.nut,.khong_in{{display:none}}.khung{{border:0}}body{{background:#fff}}}}
</style></head><body><main>
<div class="dau"><img src="icon-180.png" alt="LARC"/><div><h1>LARC Mobile</h1>
<div class="ghi">Kiểm đếm thực địa · phiên bản {_h.escape(ver)} · chạy không cần mạng</div></div></div>
<div class="canh" id="trong_ung_dung">Đang mở trong Zalo / Facebook: bấm nút ⋯ (hoặc ⋮) -> <b>Mở bằng trình duyệt</b> (iPhone: Safari) rồi làm tiếp.</div>
<div class="khung">{o_qr}<p class="ghi" style="text-align:center">Quét bằng Camera của điện thoại để mở trang này.</p></div>
<div class="khung khong_in"><a class="nut" href="./">Mở ứng dụng</a>{apk}</div>
<div class="khung"><h2>iPhone / iPad</h2><ol><li>Mở trang này bằng <b>Safari</b>.</li><li>Bấm <b>Mở ứng dụng</b>.</li>
<li>Bấm nút <b>Chia sẻ</b> (ô vuông có mũi tên lên) -> <b>Thêm vào MH chính</b> -> Thêm.</li>
<li>Mở biểu tượng <b>LARC Mobile</b> trên màn hình chính một lần khi còn mạng. Từ đó dùng được ngoài thực địa không cần mạng.</li></ol></div>
<div class="khung"><h2>Android</h2><ol><li>Bấm <b>Tải bản Android (.apk)</b>, mở file vừa tải, cho phép cài ứng dụng không rõ nguồn khi máy hỏi.</li>
<li>Hoặc: mở ứng dụng bằng <b>Chrome</b> -> menu ⋮ -> <b>Thêm vào màn hình chính</b> / <b>Cài đặt ứng dụng</b>.</li></ol></div>
<div class="khung"><h2>Dùng</h2><ol><li>Nhận file dữ liệu dự án (.json) từ người lập phương án (Zalo, email).</li>
<li>Trong ứng dụng: <b>Chọn file dữ liệu dự án…</b> -> chọn file đó.</li>
<li>Ghi xong: thẻ <b>6. Xuất .JSON</b> -> gửi file kết quả về người lập phương án.</li></ol>
<p class="ghi">Số liệu ghi lưu trong ứng dụng trên điện thoại của bạn. Gửi về thường xuyên; xóa ứng dụng là mất số liệu chưa gửi.
Trang này không chứa số liệu dự án nào.</p></div>
<p class="khong_in"><a class="nut phu" href="javascript:print()">In trang này (có mã QR)</a></p>
</main><script>
if (/Zalo|FBAN|FBAV|FB_IAB|Instagram|Line\\//i.test(navigator.userAgent)) document.getElementById("trong_ung_dung").style.display = "block";
</script></body></html>
'''


def dung_web(ver: str = PHIEN_BAN, url: str = '', apk: Path | None = None) -> Path:
    """bo_cai\\LARC_Mobile_Web_<ver>\\ (tai_len\\ + HUONG_DAN.txt) và file .zip cùng tên."""
    goc = RA / f'LARC_Mobile_Web_{ver}'
    if goc.exists():
        shutil.rmtree(goc)
    tl = goc / 'tai_len'
    tl.mkdir(parents=True)
    for ten, du in tep_ung_dung('pwa', ver).items():
        (tl / ten).write_bytes(du)
    co_apk = bool(apk and Path(apk).exists())
    if co_apk:
        shutil.copy(apk, tl / TEP_APK_WEB)
    (tl / 'cai-dat.html').write_text(trang_cai_dat(url, ver, co_apk), encoding='utf-8')
    (goc / 'HUONG_DAN.txt').write_text(HUONG_DAN_WEB.replace('\n', '\r\n'), encoding='utf-8')
    zf = goc.with_name(goc.name + '.zip')            # with_suffix: '1.1.0' -> '1.1.zip'
    with zipfile.ZipFile(zf.with_name(zf.name + '.tmp'), 'w', zipfile.ZIP_DEFLATED) as z:
        for f in sorted(goc.rglob('*')):
            if f.is_file():
                z.write(f, f.relative_to(goc).as_posix())
    zf.with_name(zf.name + '.tmp').replace(zf)
    print('Trang web:', goc, '(mã QR: ' + (url + 'cai-dat.html' if url else 'CHƯA có - thêm --url') + ')')
    return goc


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else list(argv)
    os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
    if du_lieu_mac_dinh() is None:
        print(f'CHÚ Ý: chưa có {DANH_MUC_MAC_DINH.name} - ứng dụng không có danh mục nhúng sẵn (kiểm đếm độc lập tắt).')
    url = ''
    if '--url' in argv:
        i = argv.index('--url')
        if i + 1 >= len(argv):
            raise SystemExit('Thiếu địa chỉ sau --url')
        url = chuan_dia_chi(argv[i + 1])
        DIA_CHI_WEB.write_text(url + '\n', encoding='utf-8')
    url = url or dia_chi_da_nho()
    apk = None
    if '--chi-pwa' not in argv:
        apk = dung_apk()
    if '--chi-apk' not in argv:
        dung_pwa()
        dung_web(url=url, apk=apk or RA / f'LARC_Mobile_{PHIEN_BAN}.apk')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

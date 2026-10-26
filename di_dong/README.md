# LARC Field Mobile - ứng dụng kiểm đếm thực địa (Android / iPhone)

Dự án RIÊNG, tách khỏi mã nguồn LARC bản máy tính (`pabt/`): không nhập module nào của `pabt/`, bản máy tính cũng không đóng
gói gì trong thư mục này. Hai bên chỉ nối qua **hai định dạng file .json** (mục "Giao ước dữ liệu" dưới đây) - đổi định dạng thì
sửa cả hai bên và tăng số `phien_ban` của file.

## Thư mục

| Đường dẫn | Nội dung |
|---|---|
| `ung_dung/index.html` | Toàn bộ ứng dụng: một trang HTML + JavaScript thuần (không thư viện, không mạng). 7 thẻ: Hồ sơ & Đất, Nhà ở (QĐ 42), Vật KT, Cây trồng, Ảnh biên bản, Bản đồ KML/GPS, Xuất .JSON. Chỗ trống `@@CHE_DO@@` (`pwa` / `android`), `@@PHIEN_BAN@@`, `@@DAU_PWA@@`, `@@DU_LIEU_MAC_DINH@@` do `dung.py` điền. |
| `android/` | Vỏ Android: `AndroidManifest.xml` (gói `vn.larc.field`, API 24-34), `MainActivity.java` (WebView nạp `assets/index.html` qua `https://appassets.androidplatform.net/`, chọn / chụp ảnh, quyền vị trí, cầu nối JS `LARCAndroid.luuFile`), `CungCapTep.java` (ContentProvider cấp file cho máy ảnh / ứng dụng gửi). |
| `danh_muc_mac_dinh.json` | Danh mục đơn giá nhúng sẵn (nhà, vật kiến trúc, cây + quy cách đường kính / tuổi, vật nuôi; đơn giá đồng) để kiểm đếm ĐỘC LẬP khi chưa có file dữ liệu dự án. Sinh từ bộ đơn giá đóng gói của LARC: `.venv\Scripts\python chay.py xuat-danh-muc-di-dong di_dong\danh_muc_mac_dinh.json` (chạy lại khi bộ đơn giá đổi; kiểm thử `tests/test_du_lieu_di_dong` báo lệch). Thiếu file: ứng dụng vẫn dựng, chỉ không có nút kiểm đếm độc lập. |
| `qr.py` | Mã QR thuần Python (ISO 18004, byte, mức M, phiên bản 1-10) cho trang cài đặt. |
| `bieu_tuong.png` | Biểu tượng (512 px) - nguồn của icon PWA và icon trình khởi chạy Android. |
| `dung.py`, `DUNG.bat` | Dựng `bo_cai\LARC_FieldMobile_<ver>.apk`, `bo_cai\LARC_FieldMobile_PWA_<ver>.zip` và gói web `bo_cai\LARC_FieldMobile_Web_<ver>.zip` (thư mục `tai_len\` + `HUONG_DAN.txt`, trang `cai-dat.html` có mã QR). Phiên bản riêng: `PHIEN_BAN` trong `dung.py` - TĂNG khi phát hành: bộ nhớ đệm PWA (`sw.js`) đặt tên theo phiên bản, cùng số thì iPhone giữ bản cũ. |
| `tests/` | Kiểm thử riêng: `.venv\Scripts\python -m unittest discover -s di_dong\tests` (đặt `LARC_THU_DUNG_APK=1` để dựng .apk thật). |

## Dựng

```
di_dong\DUNG.bat            (hoặc .venv\Scripts\python di_dong\dung.py [--url https://<tên>.github.io/<kho>/] [--chi-pwa] [--chi-apk])
```

- Cần PySide6 (vẽ biểu tượng) - dùng `.venv` của repo.
- Android không dùng Android Studio / Gradle: aapt2, javac (JDK 17), d8, zipalign, apksigner ở `LARC_ANDROID`
  (mặc định `<thư mục cha của repo>\cong_cu_android`: `jdk17\`, `sdk\build-tools\34.0.0\`, `sdk\platforms\android-34\`).
- Khóa ký `LARC_KHOA_APK` (mặc định `<thư mục cha của repo>\khoa_android\larc_field.jks` + `matkhau.txt`) - KHÔNG đưa vào git,
  sao lưu cẩn thận: bản cập nhật phải ký cùng khóa, mất khóa thì máy đã cài phải gỡ rồi cài lại.
- iPhone: chỉ có bản PWA (đặt gói .zip lên địa chỉ HTTPS, Safari -> Thêm vào MH chính); bản .ipa cần máy Mac + Xcode + tài khoản Apple.
- Cài cho nhiều người: `--url` = địa chỉ HTTPS sẽ tải lên (GitHub Pages / Netlify / Cloudflare Pages; nhớ ở `dia_chi_web.txt`) ->
  tải TOÀN BỘ `tai_len\` lên đó, gửi mã QR trên `cai-dat.html`. Không gửi dữ liệu hộ dân lên trang: chỉ là ứng dụng trống + danh mục đơn giá.

## Tính năng chính (bản 1.1.0)

- Kiểm đếm độc lập không cần file dự án (danh mục nhúng sẵn); "← Quay lại dự án đang mở"; phím Back Android: đóng ảnh / về thẻ 0.
- Ô khối lượng nhận biểu thức `(5x12)-(2x3)`, `7m x 2m x 2` (dài x rộng x số cái), `1,5x2,4x1,2` (m3) - bàn phím tắt `x ( ) + - ,`;
  hiện thành tiền tạm tính theo đơn giá nhúng (chỉ để xem - máy tính áp giá lại).
- Nhà: chip kết cấu -> GỢI Ý loại nhà (chỉ gợi ý, người kiểm đếm chọn). Cây: chip đường kính / tuổi theo đúng khoảng của bộ đơn giá.
- Ảnh biên bản: Chụp ảnh / Chọn ảnh tách riêng (Android 11+: `<queries>` IMAGE_CAPTURE), xem phóng to + ô chép lại biên bản; dòng
  biên bản tự phân loại trên máy (nhà / vật KT / cây), sửa được mọi dòng của mọi bảng.
- Bản đồ: nền ảnh vệ tinh (Esri) / đường (OpenStreetMap) - chỉ tải ô bản đồ theo tọa độ khung nhìn, không gửi dữ liệu hộ dân;
  "Thửa hộ này", "Tâm GPS", tìm tờ/thửa. Không có mạng: nền lưới như cũ.
- Không nhận dạng giọng nói: Web Speech gửi tiếng nói (họ tên, CCCD) lên máy chủ của hãng - dùng micro của bàn phím điện thoại nếu cần.

## Giao ước dữ liệu

**1. Dữ liệu dự án (máy tính -> điện thoại)**: LARC xuất (Công cụ -> Phiếu kiểm đếm thực địa -> "Xuất dữ liệu cho ứng dụng điện thoại").

```json
{"loai": "larc_field_du_lieu", "phien_ban": 1, "luc": "2026-10-26T09:00:00",
 "du_lieu": {
   "du_an": "tên dự án (khóa lưu trên điện thoại)", "phien_ban": "phiên bản LARC",
   "ho": [{"ma": 1, "stt": 1, "ten": "", "cccd": "", "dia_chi": "", "sdt": "", "thua": [{"to": "", "thua": "", "loai": "", "dt": ""}]}],
   "nha": [["mã", "tên", "ĐVT", đơn_giá]], "dm2": [["mã", "tên", "ĐVT", đơn_giá]], "vat_nuoi": [["mã", "tên", "ĐVT", đơn_giá]],
   "cay": ["tên loài"], "cay_chi_tiet": {"tên loài": {"dk": true, "tuoi": false, "dvt": "cây",
     "muc": [["mã", "tên", "ĐVT", đơn_giá, dk_từ, dk_đến, tuổi_từ, tuổi_đến]]}},
   "goi_y": {"2": [["tên", "ĐVT"]], "3": [], "7": []},
   "kinh_tuyen": 107.75, "datum": [dx, dy, dz, rx, ry, rz, ppm], "quy_uoc": "coordinate_frame",
   "ban_do": [{"so_to": "", "so_thua": "", "loai": "", "ma_ho": 1, "trang_thai": "chua", "vong": [[vĩ độ, kinh độ]]}],
   "trang_thai_ho": {"1": "chua"}, "mau_trang_thai": {"chua": ["Chưa gán", "#94A3B8"]}}}
```

**2. Kết quả kiểm đếm (điện thoại -> máy tính)**: thẻ "6. Xuất .JSON"; LARC nhập bằng "Nhập kết quả kiểm đếm (.json)…".

```json
{"phien_ban": 2, "ung_dung": "LARC Field Mobile <ver>", "du_an": "", "luc": "ISO 8601", "kinh_tuyen": 107.75,
 "ket_qua": {"<mã hộ | moi_<n>>": [{"muc": 2, "ma_dm": "", "ten": "", "dvt": "", "so_luong": "", "ty_le": "100",
                                    "so_do": "", "kieu": "dk|cv", "ghi_chu": ""}]},
 "ho_dan": {"<khóa>": {"ma_ho": 1, "ho_ten": "", "so_cccd": "", "nguoi_su_dung": "", "nam_sinh": "", "sdt": "", "dia_chi": "",
                       "nam_tao_lap": "", "ghi_chu": "", "gps": {"lat": 0, "lon": 0, "acc": 0, "luc": ""}}},
 "dat_dai": {"<khóa>": [{"so_to": "", "so_thua": "", "loai_dat": "", "dt_thu_hoi": "m²"},
                         {"tieu_khu": "", "khoanh": "", "lo": "", "loai_dat": "", "dt_ha": "ha"}]},
 "anh": {"<khóa>": [{"ten": "bien_ban.jpg", "du_lieu": "data:image/jpeg;base64,…"}]}}
```

`muc`: 2 nhà / công trình, 3 cây trồng, 7 vật nuôi, 0 = dòng ghi lại biên bản chưa phân loại được (máy tính tự phân loại).
Dòng biên bản đã phân loại trên điện thoại giữ chữ gốc trong `ten`, `so_luong` trống: máy tính đọc lại bằng `hieu_tai_san.tach_dong`. Phía máy tính đọc ở
`pabt/phieu_kiem_dem.py` (`doc_phieu`, `nhap_ket_qua_kiem_dem`; khớp hộ theo CCCD -> tờ / thửa, lô rừng -> họ tên -> mã hộ).

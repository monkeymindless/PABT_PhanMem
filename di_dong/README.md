# LARC Field Mobile - ứng dụng kiểm đếm thực địa (Android / iPhone)

Dự án RIÊNG, tách khỏi mã nguồn LARC bản máy tính (`pabt/`): không nhập module nào của `pabt/`, bản máy tính cũng không đóng
gói gì trong thư mục này. Hai bên chỉ nối qua **hai định dạng file .json** (mục "Giao ước dữ liệu" dưới đây) - đổi định dạng thì
sửa cả hai bên và tăng số `phien_ban` của file.

## Thư mục

| Đường dẫn | Nội dung |
|---|---|
| `ung_dung/index.html` | Toàn bộ ứng dụng: một trang HTML + JavaScript thuần (không thư viện, không mạng). 7 thẻ: Hồ sơ & Đất, Nhà ở (QĐ 42), Vật KT, Cây trồng, Ảnh biên bản, Bản đồ KML/GPS, Xuất .JSON. Chỗ trống `@@CHE_DO@@` (`pwa` / `android`), `@@PHIEN_BAN@@`, `@@DAU_PWA@@` do `dung.py` điền. |
| `android/` | Vỏ Android: `AndroidManifest.xml` (gói `vn.larc.field`, API 24-34), `MainActivity.java` (WebView nạp `assets/index.html` qua `https://appassets.androidplatform.net/`, chọn / chụp ảnh, quyền vị trí, cầu nối JS `LARCAndroid.luuFile`), `CungCapTep.java` (ContentProvider cấp file cho máy ảnh / ứng dụng gửi). |
| `bieu_tuong.png` | Biểu tượng (512 px) - nguồn của icon PWA và icon trình khởi chạy Android. |
| `dung.py`, `DUNG.bat` | Dựng `bo_cai\LARC_FieldMobile_<ver>.apk` + `bo_cai\LARC_FieldMobile_PWA_<ver>.zip`. Phiên bản riêng: `PHIEN_BAN` trong `dung.py`. |
| `tests/` | Kiểm thử riêng: `.venv\Scripts\python -m unittest discover -s di_dong\tests` (đặt `LARC_THU_DUNG_APK=1` để dựng .apk thật). |

## Dựng

```
di_dong\DUNG.bat            (hoặc .venv\Scripts\python di_dong\dung.py [--chi-pwa] [--chi-apk])
```

- Cần PySide6 (vẽ biểu tượng) - dùng `.venv` của repo.
- Android không dùng Android Studio / Gradle: aapt2, javac (JDK 17), d8, zipalign, apksigner ở `LARC_ANDROID`
  (mặc định `<thư mục cha của repo>\cong_cu_android`: `jdk17\`, `sdk\build-tools\34.0.0\`, `sdk\platforms\android-34\`).
- Khóa ký `LARC_KHOA_APK` (mặc định `<thư mục cha của repo>\khoa_android\larc_field.jks` + `matkhau.txt`) - KHÔNG đưa vào git,
  sao lưu cẩn thận: bản cập nhật phải ký cùng khóa, mất khóa thì máy đã cài phải gỡ rồi cài lại.
- iPhone: chỉ có bản PWA (đặt gói .zip lên địa chỉ HTTPS, Safari -> Thêm vào MH chính); bản .ipa cần máy Mac + Xcode + tài khoản Apple.

## Giao ước dữ liệu

**1. Dữ liệu dự án (máy tính -> điện thoại)**: LARC xuất (Công cụ -> Phiếu kiểm đếm thực địa -> "Xuất dữ liệu cho ứng dụng điện thoại").

```json
{"loai": "larc_field_du_lieu", "phien_ban": 1, "luc": "2026-10-26T09:00:00",
 "du_lieu": {
   "du_an": "tên dự án (khóa lưu trên điện thoại)", "phien_ban": "phiên bản LARC",
   "ho": [{"ma": 1, "stt": 1, "ten": "", "cccd": "", "dia_chi": "", "sdt": "", "thua": [{"to": "", "thua": "", "loai": "", "dt": ""}]}],
   "nha": [["mã", "tên", "ĐVT"]], "dm2": [["mã", "tên", "ĐVT"]], "vat_nuoi": [["mã", "tên", "ĐVT"]], "cay": ["tên loài"],
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

`muc`: 2 nhà / công trình, 3 cây trồng, 7 vật nuôi, 0 = dòng ghi lại biên bản (máy tính tự phân loại). Phía máy tính đọc ở
`pabt/phieu_kiem_dem.py` (`doc_phieu`, `nhap_ket_qua_kiem_dem`; khớp hộ theo CCCD -> tờ / thửa, lô rừng -> họ tên -> mã hộ).

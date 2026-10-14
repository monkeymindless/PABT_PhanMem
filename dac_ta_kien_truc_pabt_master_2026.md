# HỆ THỐNG PABT ENTERPRISE - ĐẶC TẢ KIẾN TRÚC MENU & QUY TRÌNH BỒI THƯỜNG GPMB
## BẢN BỐ CỤC CHUẨN XUẤT XƯỞNG THƯƠNG MẠI (PHIÊN BẢN HOÀN THIỆN MASTER 2026)
**Căn cứ pháp lý:** Luật Đất đai 2024 & Mục IV Quyết định số 18/2026/QĐ-UBND (tỉnh Đồng Nai)  
**Mã tài liệu:** `ARCH-PABT-2026-DEFINITIVE-MASTER-V10`  
**Ngày hoàn thiện:** 13/10/2026  
**Đơn vị xây dựng:** Hội đồng Kiến trúc Hệ thống, Pháp chế Bồi thường & UI/UX PABT Enterprise  

---

## MỤC LỤC TỔNG THỂ
1. [PHẦN I: TÔN CHỈ THIẾT KẾ CÔNG THÁI HỌC & ĐỘT PHÁ GIAO DIỆN THƯƠNG MẠI 2026](#phần-i-tôn-chỉ-thiết-kế-công-thái-học--đột-phá-giao-diện-thương-mại-2026)
2. [PHẦN II: MA TRẬN 16 BƯỚC PHÁP LÝ (QĐ 18/2026) ÁNH XẠ VÀO 6 PHÂN HỆ PABT](#phần-ii-ma-trận-16-bước-pháp-lý-qđ-182026-ánh-xạ-vào-6-phân-hệ-pabt)
3. [PHẦN III: HỆ THỐNG MENU TRÁI CHUẨN XUẤT XƯỞNG & ĐỊNH TUYẾN ĐA TÁC VỤ](#phần-iii-hệ-thống-menu-trái-chuẩn-xuất-xưởng--định-tuyến-đa-tác-vụ)
4. [PHẦN IV: ĐẶC TẢ PHÂN HỆ 4: LẬP PHƯƠNG ÁN & DÂN CHỦ CÔNG KHAI (BƯỚC 5, 6, 7)](#phần-iv-đặc-tả-phân-hệ-4-lập-phương-án--dân-chủ-công-khai-bước-5-6-7)
5. [PHẦN V: ĐẶC TẢ PHÂN HỆ 5: TỔNG HỢP & TRÌNH DUYỆT (BƯỚC 8)](#phần-v-đặc-tả-phân-hệ-5-tổng-hợp--trình-duyệt-bước-8)
6. [PHẦN VI: ĐẶC TẢ PHÂN HỆ 6: PHÊ DUYỆT & BÀN GIAO MẶT BẰNG SẠCH (BƯỚC 9 - 16)](#phần-vi-đặc-tả-phân-hệ-6-phê-duyệt--bàn-giao-mặt-bằng-sạch-bước-9---16)
7. [PHẦN VII: HỢP NHẤT HỆ THỐNG IN & TRUNG TÂM XUẤT BẢN HỒ SƠ DUY NHẤT (BATCH EXPORT STUDIO)](#phần-vii-hợp-nhất-hệ-thống-in--trung-tâm-xuất-bản-hồ-sơ-duy-nhất-batch-export-studio)
8. [PHẦN VIII: CHUẨN HÓA SỐ HIỆU VĂN BẢN (NĐ 30/2020), TỶ LỆ KINH PHÍ & CỬA SỔ CON](#phần-viii-chuẩn-hóa-số-hiệu-văn-bản-nđ-302020-tỷ-lệ-kinh-phí--cửa-sổ-con)
9. [PHẦN IX: BỘ NHẬN DIỆN THƯƠNG HIỆU, BANNER NỀN TRẮNG & CỬA SỔ CÀI ĐẶT THƯƠNG MẠI](#phần-ix-bộ-nhận-diện-thương-hiệu-banner-nền-trắng--cửa-sổ-cài-đặt-thương-mại)
10. [PHẦN X: CÂU LỆNH PROMPT MASTER HOÀN CHỈNH CHO CLAUDE AI / CURSOR](#phần-x-câu-lệnh-prompt-master-hoàn-chỉnh-cho-claude-ai--cursor)
11. [PHẦN XI: TÍCH HỢP NÚT "DÁN DANH SÁCH TÀI SẢN" TỐI ƯU NHẬP LIỆU PHƯƠNG ÁN](#phần-xi-tích-hợp-nút-dán-danh-sách-tài-sản-tối-ưu-nhập-liệu-phương-án)
12. [PHẦN XII: TỐI ƯU CÔNG THÁI HỌC 3 THẺ TÁC VỤ CHO MÀN HÌNH DƯỚI 24 INCH](#phần-xii-tối-ưu-công-thái-học-3-thẻ-tác-vụ-cho-màn-hình-dưới-24-inch)
13. [PHẦN XIII: BÁO CÁO ĐÁNH GIÁ & KIỂM ĐỊNH TOÀN DIỆN GIAO DIỆN (UI/UX AUDIT 2026)](#phần-xiii-báo-cáo-đánh-giá--kiểm-định-toàn-diện-giao-diện-uiux-audit-2026)
14. [PHẦN XIV: LOẠI BỎ CHỮ "MÁY ĐƠN" TRÙNG LẶP & TỔNG HỢP TOÀN DIỆN 8 ĐIỂM TINH CHỈNH CUỐI CÙNG](#phần-xiv-loại-bỏ-chữ-máy-đơn-trùng-lặp--tổng-hợp-toàn-diện-8-điểm-tinh-chỉnh-cuối-cùng)
15. [PHẦN XV: CHUẨN HÓA MỸ THUẬT BIỂU TƯỢNG (APP ICON): NÂNG TÔNG NỀN TỪ XANH ĐEN SANG ROYAL NAVY GRADIENT](#phần-xv-chuẩn-hóa-mỹ-thuật-biểu-tượng-app-icon-nâng-tông-nền-từ-xanh-đen-sang-royal-navy-gradient)

---

## PHẦN I: TÔN CHỈ THIẾT KẾ CÔNG THÁI HỌC & ĐỘT PHÁ GIAO DIỆN THƯƠNG MẠI 2026

1. **Bảo lưu 100% Dải Thẻ KPI Điều hành Vĩ mô Ngoài Cửa sổ Chính**:
   - Dải 6 thẻ chỉ số ngoài giao diện chính:
     `[Số hộ: 170] | [Đã lập PA: 32/170] | [Tổng kinh phí: 8,0 tỷ] | [Đã duyệt: 0/170] | [Đã chi trả: 0/170] | [Đã bàn giao: 0/170]`
   - Được bảo lưu nguyên vẹn, không thay đổi, không xóa để cán bộ và lãnh đạo luôn nắm bắt bức tranh toàn cảnh dự án tức thì.
2. **Tách Nút "Màn hình chính" Độc lập Trên Đỉnh Sidebar Trái**:
   - Nút `[ 🏠 MÀN HÌNH CHÍNH ]` ghim ở vị trí cao nhất trên thanh Menu trái, hoàn toàn độc lập, không thuộc nhóm con nào.
   - Thao tác 1 chạm là quay về ngay Welcome Dashboard và danh sách hồ sơ gần đây mà không làm đóng dự án đang mở trong RAM.
3. **Tách biệt Tuyệt đối "Khái toán Pre-F/S" và "Dự án Triển khai"**:
   - Nhóm 1 (*Khái toán & Dự toán*): Chuyên trách giai đoạn chuẩn bị đầu tư (`.pabtdt`), nhập 7 thông số sơ bộ và bảng tính kinh phí độc lập.
   - Nhóm 2 (*Dự án triển khai*): Chuyên trách quản lý hồ sơ bồi thường thực tế (`.pabt`) khi đã có trích lục và đo đạc kiểm đếm.
4. **Triệt tiêu 100% Các Dòng Nhắc Nghiệp dư**:
   - Xóa bỏ vĩnh viễn dòng chữ chắp vá: `QUYẾT ĐỊNH PHÊ DUYỆT · ◄ bấm "Danh sách hộ và Thửa" ở menu trái để quay lại` trên tiêu đề mọi trang.
5. **Chuẩn hóa Cửa sổ Con (Min/Max/Close & Resizability)**:
   - Mọi cửa sổ con nghiệp vụ (`CuaSoLapPA`, `HopDotTrinh`, `HopIn`, `HopChonNiemYet`, `HopBoDonGia`...) bắt buộc có đủ 3 nút: Thu nhỏ, Phóng to và Đóng (`Qt.WindowMinMaxButtonsHint | Qt.WindowCloseButtonHint`).
   - Bật cờ `setSizeGripEnabled(True)` cho phép co giãn tự do, ghi nhớ kích thước qua `QSettings`.
6. **Khắc phục Lỗi Thu phóng Cửa sổ Chính**:
   - Đặt `minimumSize` là `1024 x 680`.
   - Nút `❐` (Restore Down) phục hồi về kích thước tiêu chuẩn `1200 x 740` căn giữa màn hình; nút `□` bung toàn màn hình mượt mà.

---

## PHẦN II: MA TRẬN 16 BƯỚC PHÁP LÝ (QĐ 18/2026) ÁNH XẠ VÀO 6 PHÂN HỆ PABT

| Bước | Tên Bước Pháp lý (Mục IV QĐ 18/2026/QĐ-UBND) | Phân hệ Menu Trái PABT | Sản phẩm / Biểu mẫu Đầu ra trên PABT |
| :--- | :--- | :--- | :--- |
| **Bước 1** | Xây dựng kế hoạch thu hồi đất | 1. Khái toán & Dự toán | Bảng khái toán tổng mức, Kế hoạch vốn |
| **Bước 2** | Họp dân trong khu vực thu hồi đất | 2. Dự án triển khai | Biên bản họp dân phổ biến chủ trương |
| **Bước 3** | Thông báo thu hồi đất & Gửi Thông báo | 2. Dự án triển khai | Danh sách trích xuất Thông báo thu hồi đất |
| **Bước 4** | Điều tra, khảo sát, đo đạc, kiểm đếm hiện trạng | 2. Dự án triển khai | Danh sách hộ & Thửa đất kiểm kê thô |
| **Bước 5** | Lập phương án bồi thường, hỗ trợ (Dự thảo) | 4. Lập phương án | Phương án chi tiết hộ, Bảng áp giá chi tiết |
| **Bước 6** | Niêm yết công khai phương án (Đúng 10 ngày liên tục) | 4. Lập phương án (Tab 1) | Bảng dự thảo niêm yết (Che CCCD NĐ 13), Biên bản bắt đầu & kết thúc niêm yết |
| **Bước 7** | Lấy ý kiến PABT & Đối thoại (Không quá 30 ngày) | 4. Lập phương án (Tab 2,3) | Phiếu lấy ý kiến từng hộ, Biên bản đối thoại & Báo cáo giải trình tiếp thu |
| **Bước 8** | Thẩm định phương án bồi thường (Không quá 15 ngày) | 5. Tổng hợp & Trình duyệt | Tờ trình thẩm định, Bảng tổng hợp kinh phí toàn đợt, Báo cáo ý kiến đính kèm |
| **Bước 9** | Quyết định phê duyệt phương án bồi thường | 6. Phê duyệt & Bàn giao | Nhập Quyết định, Phân bổ tiền từng hộ |
| **Bước 10**| Công khai Quyết định phê duyệt tại UBND xã | 6. Phê duyệt & Bàn giao | Bảng niêm yết công khai QĐ phê duyệt |
| **Bước 11**| Gửi phương án đã duyệt đến từng hộ dân | 7. Trung tâm Xuất bản | In Bản chính thức phương án gửi từng hộ (Số PA 01, 02...) |
| **Bước 12**| Chi trả tiền bồi thường & Giao đất/nhà tái định cư | 6. Phê duyệt & Bàn giao | Danh sách chi trả tiền, Biên bản giao đất TĐC |
| **Bước 13**| Ban hành Quyết định thu hồi đất (60 ngày NN / 120 ngày PNN) | 6. Phê duyệt & Bàn giao | Danh sách đủ điều kiện ban hành QĐ thu hồi đất |
| **Bước 14**| Xử lý hộ không nhận tiền / chấp hành (Vận động 10 ngày) | 6. Phê duyệt & Bàn giao | Sổ nhật ký vận động 10 ngày nhận tiền |
| **Bước 15**| Xử lý hộ không bàn giao mặt bằng (Vận động 10 ngày) | 6. Phê duyệt & Bàn giao | Biên bản vận động, Danh sách đề nghị cưỡng chế Điều 89 |
| **Bước 16**| Quản lý mặt bằng sạch đã thu hồi | 6. Phê duyệt & Bàn giao | Báo cáo Dashboard điều hành mặt bằng sạch GPMB |

---

## PHẦN III: HỆ THỐNG MENU TRÁI CHUẨN XUẤT XƯỞNG & ĐỊNH TUYẾN ĐA TÁC VỤ

```text
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                        HỆ THỐNG MENU TRÁI PABT ENTERPRISE 2026                         │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ [ 🏠 MÀN HÌNH CHÍNH ]   <--- (NÚT ĐỘC LẬP TRÊN CÙNG, KHÔNG THUỘC NHÓM NÀO)             │
│ ────────────────────────────────────────────────────────────────────────────────────── │
│                                                                                        │
│ ▾ 1. KHÁI TOÁN & DỰ TOÁN        <--- (PHÂN HỆ ĐỘC LẬP: GIAI ĐOẠN CHUẨN BỊ ĐẦU TƯ)     │
│   • 📊 Lập khái toán & Dự toán  (Có 7 trường thông tin dự án độc lập + Bảng tính kinh phí)│
│   • ⚖️ So sánh với thực tế       (Đối soát hạn mức vốn khái toán với áp giá thực tế)   │
│                                                                                        │
│ ▾ 2. DỰ ÁN TRIỂN KHAI           <--- (PHÂN HỆ ĐỘC LẬP: DỰ ÁN THỰC ĐỊA ĐANG THU HỒI ĐẤT) │
│   • ℹ️ Thông tin dự án          (Chủ trương, Chủ đầu tư, Cơ quan thẩm định, Người ký) │
│   • 👥 Danh sách hộ và Thửa     (Dữ liệu đo đạc, kiểm kê hiện trạng - Bước 4 QĐ 18)   │
│                                                                                        │
│ ▾ 3. ĐƠN GIÁ & BẢNG GIÁ         <--- (CƠ SỞ ĐỊNH MỨC PHÁP LÝ ÁP GIÁ)                  │
│   • 📋 Đơn giá bồi thường       (Bộ đơn giá chuẩn nhà, cây, vật nuôi, chính sách)     │
│   • 🏷️ Đơn giá đặc biệt         (Quy ước giá tương đương & Chứng thư thẩm định)       │
│   • 🗺️ Bảng giá đất             (Tra cứu & Cập nhật Bảng giá đất NQ 28)               │
│                                                                                        │
│ ▾ 4. LẬP PHƯƠNG ÁN              <--- (GIAI ĐOẠN ÁP GIÁ & DÂN CHỦ CÔNG KHAI BƯỚC 5, 6, 7)│
│   • ✏️ Lập phương án chi tiết   (Soạn thảo, tính toán áp giá từng hộ)                 │
│   • 📢 Niêm yết & Lấy ý kiến    (Gồm 4 sub-tabs: Niêm yết, Lấy ý kiến, Đối thoại...)  │
│   • 🔍 Kiểm tra lỗi pháp lý     (Rà soát font, diện tích, quy chuẩn, đơn giá)         │
│   • ⚖️ Đối chiếu số liệu        (So khớp số liệu giữa phần mềm và Excel kiểm đếm)     │
│                                                                                        │
│ ▾ 5. TỔNG HỢP & TRÌNH DUYỆT     <--- (HOÀN THIỆN HỒ SƠ TRÌNH THẨM ĐỊNH BƯỚC 8, 11)    │
│   • 📑 Bảng tổng hợp kinh phí   (Tổng hợp cơ cấu chi phí toàn dự án & đối soát ngân sách)│
│   • 📂 Đợt trình thẩm định      (Quản lý đợt, tờ trình thẩm định, đếm ngược SLA 15 ngày)│
│   • 🖨️ Xuất hồ sơ & Bản in      (Trung tâm xuất bản Batch Export Studio duy nhất)      │
│                                                                                        │
│ ▾ 6. PHÊ DUYỆT & BÀN GIAO       <--- (THỰC THI SAU PHÊ DUYỆT BƯỚC 9, 12, 15, 16)      │
│   • 📜 Quyết định phê duyệt     (Quản lý QĐ phê duyệt phương án & QĐ thu hồi đất)     │
│   • 📈 Theo dõi chi trả & Bàn giao (Tiến độ nhận tiền, mốc 60/120 ngày, sổ vận động 10 ng)│
│   • 📊 Báo cáo tiến độ GPMB     (Dashboard điều hành giải ngân, mặt bằng sạch, xôi đỗ) │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## PHẦN IV: ĐẶC TẢ PHÂN HỆ 4: LẬP PHƯƠNG ÁN & DÂN CHỦ CÔNG KHAI (BƯỚC 5, 6, 7)

### 1. Cửa sổ Lập phương án chi tiết hộ (`CuaSoLapPA`):
- **Phím tắt duyệt nhanh**: `Ctrl + Mũi tên trái` (Hộ trước), `Ctrl + Mũi tên phải` (Hộ sau).
- **Tra cứu giá đất**: Nút `[ 🔍 Tra giá đất NQ 28... ]` đặt ngay cạnh ô chọn Vị trí tại Tab 1. Đất.
- **Trích lục nguồn gốc đất**: Nhấp đúp vào ô Nguồn gốc mở hộp thoại riêng `HopNguonGoc` để xem/sửa trích lục, tránh vỡ độ cao dòng bảng.

### 2. Phân hệ Niêm yết & Lấy ý kiến (`KhungDuThao`):
- **Hàng công cụ đợt**:
  + `[ ➕ Tạo đợt ]`
  + `[ 🗑️ Xóa đợt ]`: Tự động làm mờ khi chọn *Lũy kế toàn bộ các đợt*; bật sáng khi chọn một đợt cụ thể. Khi bấm mở hộp thoại xác nhận: *"Bạn có chắc chắn muốn xóa Đợt này? Toàn bộ hộ sẽ được đưa trở lại danh sách chờ niêm yết, phương án của hộ được bảo toàn nguyên vẹn 100%."*
  + `[ ➕ Đưa hộ vào đợt ▾ ]`: Menu xổ: *Thêm toàn bộ hộ đủ điều kiện*, *Chọn hộ từ danh sách*.
  + `[ 📅 Ngày họp dân ]`: Thiết lập ngày tổ chức họp dân lấy ý kiến trực tiếp.
  + `[ 🖨️ In PA Dự thảo gửi dân ▾ ]`: Menu xổ mở thẳng `HopIn` ở chế độ Dự thảo.
- **4 Sub-tabs nghiệp vụ chuẩn mực**:
  + **Tab 1 (Niêm yết công khai)**: Phân chia linh hoạt bằng `QSplitter` giữa bảng *Hộ niêm yết* và bảng *Hộ vướng pháp lý*. Tự động che mờ số CCCD (`075092******`) theo Nghị định 13/2023/NĐ-CP.
  + **Tab 2 (Lấy ý kiến nhân dân)**: Tương tác nhanh 1 chạm (Click chuột hoặc phím Space) chuyển đổi trạng thái: `Chưa lấy ý kiến ➔ 🟢 Đồng ý ➔ 🔴 Không đồng ý ➔ 🟡 Ý kiến khác`.
  + **Tab 3 (Đối thoại & Tiếp thu)**: Tự động lọc các hộ chưa đồng thuận, có nút `[ 📑 Xuất biên bản đối thoại ]` và `[ Chuyển hộ sang đợt sau ]`.
  + **Tab 4 (Tổng hợp kết quả ý kiến)**: Bảng phân loại tự động tính tỷ lệ % đồng thuận theo từng nhóm lý do (giá đất, tài sản, cây trồng, TĐC) phục vụ kẹp vào Tờ trình thẩm định Bước 8.

---

## PHẦN V: ĐẶC TẢ PHÂN HỆ 5: TỔNG HỢP & TRÌNH DUYỆT (BƯỚC 8)

### 1. Bảng Tổng hợp Kinh phí:
- **Gỡ bỏ hoàn toàn tab con Quyết định phê duyệt** ra khỏi màn hình này để tránh trùng lặp với Nhóm 6.
- **Chuẩn hóa 3 Sub-tabs kế toán bồi thường**:
  + **Sub-tab 1**: `📊 Cơ cấu kinh phí dự án` (Tổng hợp theo nhóm: Tiền bồi thường đất, Nhà công trình, Cây trồng, Vật nuôi, Hỗ trợ, Chi phí phục vụ GPMB).
  + **Sub-tab 2**: `👥 Bảng kinh phí chi tiết 170 hộ` (Bảng tổng hợp số tiền từng hộ đính kèm Tờ trình thẩm định).
  + **Sub-tab 3**: `⚖️ Đối soát dự toán Pre-F/S` (So sánh thực tế áp giá với Khái toán tổng mức đầu tư ban đầu).
- **Nút chuyển hướng**: `[ 📜 Đi đến Phân hệ Phê duyệt ➔ ]` ở góc trên bên phải.

### 2. Chuẩn hóa Tỷ lệ Kinh phí Tổ chức GPMB (Sửa lỗi 2,4% / 3,4%):
- **Căn cứ**: Quyết định số 08/2025/QĐ-UBND tỉnh Đồng Nai.
- **Gốc tính trích lập 100%**: Là **Tổng kinh phí bồi thường, hỗ trợ, tái định cư**.
- **Cột Tỷ lệ (%)**:
  + Dòng `Cộng bồi thường, hỗ trợ, tái định cư`: Hiển thị `100,0%`.
  + Dòng `Kinh phí tổ chức thực hiện bồi thường`: Hiển thị **ĐÚNG `2,5%` (cụm/vùng) hoặc `3,5%` (hạ tầng theo tuyến)**, khớp 100% với số ghi trong ngoặc đơn. Triệt tiêu hoàn toàn con số `2,4%` và `3,4%` gây tranh cãi kiểm toán!
  + Dòng `TỔNG KINH PHÍ DỰ ÁN`: Hiển thị `102,5%` (hoặc `103,5%`), hoặc để trống `-`.

### 3. Đợt trình Thẩm định (`HopDotTrinh`):
- **Giải phóng 200px chiều cao** bằng cách gỡ bỏ khối GroupBox xuất file dưới đáy sang Trung tâm Xuất bản.
- **Bố cục 2 cột Splitter chuyên nghiệp**:
  + **Cột trái**: Bảng đợt trình, Quản lý & sửa mẫu Tờ trình Word (.docx), Đồng hồ đếm ngược SLA 15 ngày thẩm định (Khoản 8 Mục IV QĐ 18): `⏱️ Hạn thẩm định: Còn 15 / 15 ngày`.
  + **Cột phải**: Bảng hộ trong đợt, Nút `[ 📥 Lấy hộ đã niêm yết xong từ Nhóm 4 ▾ ]`, Đánh số PA chi tiết tự động 2 chữ số (`01, 02...`), Xóa số PA (đã sửa lỗi `AttributeError`).
- **Chân trang**: Đặt 01 nút duy nhất `[ 🖨️ Xuất bản hồ sơ đợt này ➔ ]` mở thẳng Trung tâm Xuất bản.

---

## PHẦN VI: ĐẶC TẢ PHÂN HỆ 6: PHÊ DUYỆT & BÀN GIAO MẶT BẰNG SẠCH (BƯỚC 9 - 16)

### 1. Quyết định Phê duyệt:
- Là màn hình độc tôn duy nhất quản lý quyết định, bố cục Master-Detail 2 cột:
  + Cột trái: Danh sách QĐ phê duyệt (Số QĐ, Ngày ký, Tổng tiền, Số hộ).
  + Cột phải: Bảng hộ thuộc QĐ, dòng chỉ số khớp số liệu: `Khớp phương án: 32/32 hộ (100%) · Tổng tiền QĐ: 8,0 tỷ`.
  + Xóa bỏ vĩnh viễn dòng nhắc thừa `◄ bấm Danh sách hộ và Thửa...`.

### 2. Theo dõi Chi trả & Bàn giao (Bước 12 - 15):
- **Mốc ban hành Quyết định thu hồi đất (Bước 13)**: Kiểm tra điều kiện thời hạn Thông báo thu hồi đất đủ `>= 60 ngày` (đất nông nghiệp) hoặc `>= 120 ngày` (đất phi nông nghiệp).
- **Sổ nhật ký vận động 10 ngày (Bước 14 & 15)**:
  + Ghi nhận biên bản vận động hộ không nhận tiền / không bàn giao đất (Lần 1, 2, 3).
  + Quá 10 ngày vận động không thành ➔ Tự động kích hoạt trạng thái: **`Đủ điều kiện cưỡng chế thu hồi đất theo Điều 89 Luật Đất đai`**.

### 3. Báo cáo Tiến độ GPMB (GovTech Command Dashboard):
- **4 Card chỉ số vĩ mô trực quan kèm thanh Progress bar**:
  + Card 1: `GIẢI NGÂN TIỀN BỒI THƯỜNG` (%, số tiền, số hộ đã nhận).
  + Card 2: `MẶT BẰNG SẠCH ĐÃ BÀN GIAO` (%, diện tích m², số hộ đã bàn giao).
  + Card 3: `THỬA "XÔI ĐỖ" CÒN VƯỚNG` (Gấp, Cao, Theo dõi).
  + Card 4: `HỘ ĐỦ ĐIỀU KIỆN CƯỠNG CHẾ` (Điều 89 Luật Đất đai 2024).
- **Bảng nhận diện Thửa "xôi đỗ" cần giải tỏa gấp**: Phân loại theo mức ưu tiên, tờ bản đồ, lý do vướng mắc để lãnh đạo tập trung chỉ đạo thực địa.

---

## PHẦN VII: HỢP NHẤT HỆ THỐNG IN & TRUNG TÂM XUẤT BẢN HỒ SƠ DUY NHẤT (BATCH EXPORT STUDIO)

### 1. Gom về 1 Đầu mối Duy nhất:
- Menu trái `5. TỔNG HỢP & TRÌNH DUYỆT ➔ 🖨️ Xuất hồ sơ & Bản in` (`HopIn`) là nơi duy nhất thực hiện mọi tác vụ in ấn và xuất file của toàn hệ thống.

### 2. Cấu trúc 3 Khối Xuất bản Khoa học (Wizard Flow):
- **KHỐI 1: PHẠM VI XUẤT BẢN**:
  + Chọn theo Đợt trình (Đợt 1, Đợt 2...) hoặc In tự do theo danh sách hộ đã chọn.
- **KHỐI 2: CHẾ ĐỘ PHÁT HÀNH & BỘ HỒ SƠ (THEO TIẾN TRÌNH QĐ 18)**:
  + **`[ ○ BẢN DỰ THẢO (Họp dân, Niêm yết 10 ngày Bước 6 QĐ 18) ]`**:
    * Tự động nạp mẫu `IN_CHITIET__Du thao.xlsx` (in sẵn chữ DỰ THẢO nổi bật).
    * Tự động điền chữ `(DỰ THẢO)` vào tiêu đề Bảng tổng hợp kinh phí.
    * Tự động tích chọn `[x] Che số CCCD theo NĐ 13/2023/NĐ-CP (075092******)`.
    * Số PA để trống hoặc ghi `Dự thảo`.
  + **`[ ● BẢN CHÍNH THỨC (Trình thẩm định Bước 8 & Gửi từng hộ sau duyệt Bước 11) ]`**:
    * Dùng mẫu `IN_CHITIET.xlsx` và `IN_BANGTONGHOP.xlsx`.
    * Đầy đủ số PA chính thức 2 chữ số (`01, 02...`), ngày ban hành, không có chữ Dự thảo.
    * Xuất trọn bộ: Tờ trình Word (.docx), Bảng tổng hợp (.xlsx), PA chi tiết (.xlsx), Báo cáo tiếp thu ý kiến (.docx).
- **KHỐI 3: ĐỊNH DẠNG ĐẦU RA & THƯ MỤC**:
  + Tùy chọn: File Excel/Word | Kèm file PDF | Gộp 1 file PDF duy nhất | In trực tiếp ra máy in.
  + Tự động tổ chức 2 thư mục con chuẩn văn thư nhà nước: `PA CHI TIET` và `PA TONG`.

---

## PHẦN VIII: CHUẨN HÓA SỐ HIỆU VĂN BẢN (NĐ 30/2020), TỶ LỆ KINH PHÍ & CỬA SỔ CON

1. **Đánh số PA Chi tiết 2 Chữ số (Nghị định 30/2020/NĐ-CP)**:
   - Định dạng tự động: `f"{i:02d}"` ➔ Số: `01, 02, 03... 09, 10, 11...`
   - Kết quả hiển thị và in ấn: `Số: 01/PA-TTPTQĐ.CNVC`, `Số: 02/PA-TTPTQĐ.CNVC`.
2. **Đủ Nút Thu nhỏ / Phóng to trên Mọi Cửa sổ Con**:
   - Thêm cờ `Qt.WindowMinMaxButtonsHint | Qt.WindowCloseButtonHint` và `setSizeGripEnabled(True)`.
3. **Khắc phục Thu phóng Cửa sổ Chính**:
   - `minimumSize` là `1024 x 680`; Chế độ Normal thu về `1200 x 740` căn giữa màn hình.

---

## PHẦN IX: BỘ NHẬN DIỆN THƯƠNG HIỆU, BANNER NỀN TRẮNG & CỬA SỔ CÀI ĐẶT THƯƠNG MẠI

1. **Biểu tượng PABT Fluent Isometric 3D**:
   - Nền Squircle chuyển sắc Royal Blue (`#1D4ED8`) xuống Midnight Navy (`#0B1E3B`).
   - Viền kim loại kép mỏng, khử răng cưa bằng kênh Alpha 8-bit trong suốt tuyệt đối (không viền trắng).
   - Mái nhà vàng kim hoàng gia (`#F59E0B`) hợp nhất khối thửa đất 3D ngọc lục bảo (`#10B981`).
2. **Cửa sổ Cài đặt & Bảo trì (`cai_dat.py`)**:
   - Kích thước chuẩn thương mại: `620 x 440 px`.
   - Dải Banner trên cùng: NỀN TRẮNG (`#FFFFFF`), viền đáy mỏng `#E2E8F0`.
   - Logo squircle giữ nguyên 100%, nổi bật tuyệt đối trên nền trắng.
   - Tiêu đề trên đúng 1 dòng: `PHẦN MỀM LẬP PHƯƠNG ÁN BỒI THƯỜNG, HỖ TRỢ, TÁI ĐỊNH CƯ` (Font 11pt Bold, màu `#0F3866`, `setWordWrap=False`, không rớt dòng).
   - Dòng cơ quan giữ nguyên màu sắc; dòng phiên bản màu xám `#475569`.
   - Alert Card thông báo bản cũ: Nền vàng kem `#FFFBEB`, viền trái 4px `#F59E0B`, huy hiệu bảo vệ dữ liệu dự án 🛡️ `#047857`.
   - Phân cấp 3 nút bấm:
     + `[ 🔄 Cài đặt lại (Nâng cấp) ]`: Xanh lá `#107C41`, chữ trắng in đậm 11pt.
     + `[ Hủy bỏ ]`: Trắng viền xám `#CBD5E1`.
     + `[ 🗑️ Gỡ cài đặt... ]`: Độc lập góc trái, nền `#FEF2F2`, chữ đỏ `#DC2626` (có hộp thoại xác nhận).

---

## PHẦN X: CÂU LỆNH PROMPT MASTER HOÀN CHỈNH CHO CLAUDE AI / CURSOR

Dưới đây là toàn văn đoạn lệnh Prompt Master để dán vào Cursor / Claude Code tự động thi công 100%:

```text
Dựa vào file CLAUDE.md, Mục IV Quyết định số 18/2026/QĐ-UBND tỉnh Đồng Nai và Luật Đất đai 2024, hãy thực hiện gói nâng cấp toàn diện xuất xưởng thương mại cho phần mềm PABT theo đúng các yêu cầu kỹ thuật sau:

1. ĐÁNH SỐ PA CHI TIẾT 2 CHỮ SỐ THEO NGHỊ ĐỊNH 30/2020/NĐ-CP (quan_ly.py):
   - Đổi định dạng số PA tự động từ f"{i}" thành f"{i:02d}" (01, 02... 09, 10, 11...).
   - Đảm bảo mẫu in hiển thị: 'Số: 01/PA-TTPTQĐ.CNVC'.

2. BỔ SUNG NÚT THU NHỎ/PHÓNG TO CỬA SỔ CON & SỬA LỖI THU PHÓNG CỬA SỔ CHÍNH:
   - Trên mọi QDialog/cửa sổ con: Thêm cờ Qt.WindowMinMaxButtonsHint | Qt.WindowCloseButtonHint và setSizeGripEnabled(True).
   - Trong thanh_tieu_de.py và app.py: Đặt minimumSize cửa sổ chính 1024 x 680; khi bấm nút ❐ (Restore) đưa cửa sổ về 1200 x 740 căn giữa màn hình.

3. HỢP NHẤT HỆ THỐNG IN & BỔ SUNG CHẾ ĐỘ IN DỰ THẢO (man_hinh.py, van_ban_trinh.py, man_hinh_quan_ly.py):
   - Gỡ bỏ khối GroupBox 'Xuất bản hồ sơ trọn gói' ở đáy HopDotTrinh, thay bằng nút điều hướng '[ 🖨️ Xuất bản hồ sơ đợt này ➔ ]' mở thẳng HopIn.
   - Trong HopIn (Trung tâm Xuất bản duy nhất):
     + Bổ sung 2 radio button chọn chế độ:
       * [ ○ Bản DỰ THẢO (Niêm yết Bước 6 QĐ 18) ]: Tự động dùng mẫu 'IN_CHITIET__Du thao.xlsx' (có in chữ DỰ THẢO), tiêu đề Bảng tổng hợp có chữ '(DỰ THẢO)', tự động tích che CCCD theo NĐ 13/2023.
       * [ ● Bản CHÍNH THỨC (Bước 8 & 11 QĐ 18) ]: Dùng mẫu 'IN_CHITIET.xlsx', in số PA 01, 02..., xuất trọn bộ Tờ trình Word, Bảng tổng hợp, PA chi tiết, Báo cáo tiếp thu ý kiến.
   - Tại KhungDuThao (Nhóm 4): Thêm nút '[ 🖨️ In PA Dự thảo gửi dân ▾ ]' mở thẳng HopIn chế độ Dự thảo.

4. BỔ SUNG NÚT 'XÓA ĐỢT' TRONG KHUNGDUTHAO (man_hinh_du_thao.py):
   - Cạnh nút 'Tạo đợt', thêm nút 'b_xoa_dot' với nhãn '🗑️ Xóa đợt' (mờ khi chọn Lũy kế, sáng khi chọn đợt cụ thể; có hộp thoại hỏi xác nhận đưa hộ về danh sách chờ, không mất dữ liệu).

5. CHUẨN HÓA TỶ LỆ KINH PHÍ TỔ CHỨC GPMB (kinh_phi_du_an.py & KhungCoCau):
   - Gốc tính 100% là Tổng kinh phí bồi thường, hỗ trợ, tái định cư.
   - Cột Tỷ lệ (%): Dòng Cộng bồi thường là 100,0%; Dòng Kinh phí tổ chức hiển thị ĐÚNG 2,5% (hoặc 3,5%) theo QĐ 08/2025/QĐ-UBND (triệt tiêu số 2,4% và 3,4%); Dòng Tổng kinh phí dự án là 102,5% (hoặc 103,5%) hoặc để trống '-'.

6. BANNER NỀN TRẮNG & CỬA SỔ CÀI ĐẶT 620PX (cai_dat.py):
   - Cửa sổ cài đặt kích thước 620 x 440 px.
   - Banner nền TRẮNG (#FFFFFF), viền đáy #E2E8F0, logo squircle giữ nguyên.
   - Tiêu đề trên đúng 1 dòng: 'PHẦN MỀM LẬP PHƯƠNG ÁN BỒI THƯỜNG, HỖ TRỢ, TÁI ĐỊNH CƯ' (Font 11pt Bold, màu #0F3866, setWordWrap=False, không rớt dòng).
   - Alert Card thông báo bản cũ nền #FFFBEB viền trái 4px #F59E0B; phân cấp 3 nút bấm (Cài đặt lại xanh lá, Hủy bỏ trắng, Gỡ cài đặt đỏ độc lập góc trái).

7. KIỂM THỬ TOÀN BỘ:
   - Chạy test tự động python -m unittest discover -s tests -t . PASS 100% và chạy PABT.exe tu-kiem đạt kết quả KET QUA: DAT!
```

---

## PHẦN XI: TÍCH HỢP NÚT "DÁN DANH SÁCH TÀI SẢN" TỐI ƯU NHẬP LIỆU PHƯƠNG ÁN

### 1. Đánh giá Chuyên môn: Có nên thêm nút này không?
- **KẾT LUẬN: RẤT NÊN VÀ BẮT BUỘC PHẢI CÓ**. Đây là **"tính năng sát thủ" (Killer Feature)** giúp tăng tốc nhập liệu thực địa gấp **15 – 20 lần**!
- **Bản chất nghiệp vụ bồi thường**: Khi đi kiểm đếm thực địa về, cán bộ có bảng kiểm kê Excel thô hoặc ghi chú gồm nhiều loại tài sản lẫn lộn:
  + `Nhà cấp 4 mái tôn m2 45`
  + `Hàng rào lưới B40 m2 30`
  + `Mít 6 năm cây 3 80%`
  + `Ao nuôi cá ghép ha/vụ 0,03 70%`
  + `Gà ta con 40`
  + `Di dời đồng hồ điện hộ 1`
- Nếu nhập thủ công, chuyên viên phải chuyển qua lại giữa 4 tab (Nhà ➔ Cây ➔ Vật nuôi ➔ Hỗ trợ) và tìm kiếm danh mục hơn 10 lần.
- Với tính năng `HopDanTaiSan`: Cán bộ chỉ cần Copy toàn bộ đoạn text từ Excel ➔ Bấm nút Dán ➔ Hệ thống tự động phân loại, bóc tách Tên, ĐVT, Số lượng, Tỷ lệ và xếp vào đúng 4 mục trong 1 giây!

### 2. Vị trí Bố trí Công thái học trong Cửa sổ Lập phương án (`CuaSoLapPA`):
- **Vị trí 1 (Hàng công cụ nhập nhanh - Khuyên dùng nhất)**: Đặt nút `[ 📋 Dán danh sách tài sản... (Ctrl+Shift+V) ]` ngay trên thanh công cụ của bảng tài sản (cạnh nút Thêm dòng / Dán Excel).
- **Vị trí 2 (Phím tắt toàn cầu)**: Gán phím tắt `Ctrl + Shift + V` mở ngay hộp thoại `HopDanTaiSan`.
- **Vị trí 3 (Menu ngữ cảnh chuột phải)**: Click chuột phải vào bảng tài sản chọn `Dán danh sách tài sản từ Excel/Word...`.

### 3. Tự động hóa Thông minh (Smart Auto-Paste & Auto-Classify):
- Khi mở hộp thoại `HopDanTaiSan`: Nếu Clipboard của Windows đang chứa dữ liệu vừa copy, phần mềm tự động dán vào ô text và tự động kích hoạt nút `[ Phân loại ]` ngay tức thì. Cán bộ chỉ cần lướt mắt kiểm tra các dòng nền vàng (độ tin thấp) rồi bấm `[ + Thêm vào phương án ]` là hoàn tất!

---

## PHẦN XII: TỐI ƯU CÔNG THÁI HỌC 3 THẺ TÁC VỤ CHO MÀN HÌNH DƯỚI 24 INCH

### 1. Phân tích Nhu cầu Thực tế trên Màn hình Văn phòng (Dưới 24 inch):
- Đa số máy tính tại các Trung tâm PTQĐ, Ban Quản lý dự án sử dụng màn hình từ 18.5 đến 22 inch.
- Kích thước cũ của 3 thẻ (`~140 x 85 px`) quá bé, icon và chữ nhỏ làm cán bộ ngồi cách màn hình 50-70cm phải nheo mắt và dễ bấm trượt.
- **Mục tiêu**: Tăng kích thước thẻ, nâng size icon và font chữ để biến 3 thẻ thành khối điều hướng chủ đạo (Hero Cards) nổi bật, dễ nhìn, dễ thao tác trên mọi màn hình.

### 2. Quy chuẩn Kích thước & Typography Mới (`TheChao` trong `man_hinh.py`):
- **Kích thước Thẻ Card**:
  + Chiều rộng (Width): Nâng từ `140px` lên **`210px`** (tăng 50%).
  + Chiều cao (Height): Nâng từ `85px` lên **`135px`** (tăng gần 60%).
  + Bo góc: `border-radius: 10px`, đổ bóng mờ nhẹ `box-shadow: 0 4px 12px rgba(0,0,0,0.06)`.
- **Biểu tượng (Icon)**:
  + Kích thước: Nâng từ `24px` lên **`40px`** (sắc nét, rõ ràng).
- **Chữ hiển thị (Typography)**:
  + Tiêu đề chính (`Dự án mới`, `Mở dự án`, `Nhập file Excel`): Font Segoe UI **14pt Bold**.
  + Phụ đề giải thích (`Khởi tạo CSDL .pabt`, `Chọn tệp từ máy / LAN`, `Bảng kiểm đếm số liệu`): Đưa **trọn vẹn vào bên trong Card**, font Segoe UI **10.5pt Regular**, màu xám than `#64748B`.
- **Phối màu Nhận diện 3 Thẻ**:
  + Thẻ 1 (`Dự án mới`): Nền `#F0FDF4`, viền `#BBF7D0`, icon xanh lá `#107C41`.
  + Thẻ 2 (`Mở dự án`): Nền `#EFF6FF`, viền `#BFDBFE`, icon xanh dương `#1D4ED8`.
  + Thẻ 3 (`Nhập Excel`): Nền `#F8FAFC`, viền `#CBD5E1`, icon xanh navy `#0F3866`.
  + Khi rê chuột (Hover): Viền đổi sang xanh hoàng gia `#2563EB`, thẻ hơi nổi lên 2px.

---

## PHẦN XIII: BÁO CÁO ĐÁNH GIÁ & KIỂM ĐỊNH TOÀN DIỆN GIAO DIỆN (UI/UX AUDIT 2026)

### 1. Phân tích Hiện trạng từ Ảnh Chụp Thực tế (`image_f6f9d3.png`):
- **Ưu điểm lớn đã đạt được**:
  + Bố cục tổng thể cân đối, tông màu Deep Navy #0F3866 sang trọng, chính quy.
  + Cây Menu trái 6 nhóm tuyến tính theo đúng chu trình pháp lý 16 bước của Quyết định 18/2026/QĐ-UBND.
  + Dải Banner tiêu đề hợp nhất thanh mảnh, giữ trọn vẹn nhận diện thương hiệu và tên cơ quan.
- **7 "Điểm nghẽn" Giao diện Cần Tinh chỉnh Hoàn thiện**:
  1. *3 Thẻ Card Chào đón còn nhỏ*: Đang ở kích thước cũ (~140x85px), icon và chữ bé, cần áp dụng ngay kích cỡ 210x135px.
  2. *Bảng Dự án gần đây bị "Trống trải vô hồn" (Missing Empty State)*: Khi chưa có dự án, bảng chỉ là khung lưới trắng to đùng rỗng tuếch. Cần nhúng một Empty State đồ họa thanh lịch: Icon thư mục xám nhẹ + dòng thông báo: *"Chưa có hồ sơ dự án mở gần đây. Hãy bấm 'Dự án mới' hoặc 'Mở dự án' để bắt đầu làm việc."*
  3. *Vị trí 3 nút dưới đáy bảng bị lệch công thái học*: Các nút `Mở đã chọn`, `Xóa khỏi danh sách`, `Xóa file dự án` bị đẩy tít xuống góc dưới bên trái. Nên gom lên hàng công cụ ngay trên đầu bảng (cạnh ô Tìm kiếm).
  4. *Trạng thái Menu trái khi Chưa mở dự án*: Toàn bộ 6 nhóm menu vẫn đang bật sáng bình thường dù chưa mở file nào. Theo nguyên tắc an toàn, các mục đòi hỏi dữ liệu hộ (Lập phương án, Kiểm tra lỗi, Tổng hợp kinh phí, Quyết định...) nên được làm mờ nhẹ (Disabled) cho đến khi người dùng tạo hoặc mở dự án.
  5. *Chân trang Welcome còn đơn điệu*: Chỉ có duy nhất 1 link 'Lịch sử cập nhật phần mềm' nhỏ xíu ở đáy. Nên tổ chức thành thanh liên kết nhanh hữu ích: `[ 📘 Hướng dẫn sử dụng (F1) ] · [ ⚖️ Bảng giá đất NQ 28 ] · [ ⏱️ Quy trình 16 bước QĐ 18 ] · [ 🕒 Lịch sử cập nhật ]`.
  6. *Ô tìm kiếm dự án gần đây*: Cần bo góc 6px và có icon kính lúp 🔍 bên trong ô nhập.
  7. *Thanh trạng thái dưới đáy*: Tỷ lệ phóng to `110%` và `A- / A+` cần có viền bọc nút nhẹ để dễ bấm hơn.

---

## PHẦN XIV: LOẠI BỎ CHỮ "MÁY ĐƠN" TRÙNG LẶP & TỔNG HỢP TOÀN DIỆN 8 ĐIỂM TINH CHỈNH CUỐI CÙNG

### 1. Phân tích Chuyên môn: 2 Mục "Máy đơn" Có Bị Dư Không?
- **KẾT LUẬN: HOÀN TOÀN DƯ THỪA (100% REDUNDANT), CẦN XÓA NGAY 1 NƠI!**
- **Vị trí xuất hiện hiện tại (`image_f6f9d3.png`)**:
  1. *Vị trí 1 (Dải Banner trên cùng, góc phải)*: Huy hiệu `● Máy đơn` nằm cạnh `Phiên bản 0.9.76`.
  2. *Vị trí 2 (Thanh Trạng thái dưới đáy màn hình, góc phải)*: Nút tài khoản/mạng LAN `● Máy đơn · Máy chủ LAN ▾`.
- **Nguyên nhân & Đánh giá công thái học**:
  + Thanh Trạng thái dưới đáy (`nut_tk`) mới là **nơi thực sự quản lý kết nối mạng LAN / Máy đơn**, cho phép click chuột để cấu hình máy chủ, đăng nhập tài khoản.
  + Dải Banner trên cùng là nơi nhận diện dự án. Việc nhét thêm chữ `● Máy đơn` vào dải Banner làm chật chội bề ngang, chiếm dụng không gian hiển thị của Tên dự án (`lb_du_an`), gây co ngắn tên dự án dài trên màn hình laptop 1366x768.
- **Giải pháp chuẩn hóa**:
  + **XÓA BỎ HOÀN TOÀN** mục `● Máy đơn` (`lb_may_don`) trên dải Banner trên cùng (`tao_banner_ten`).
  + **GIỮ LẠI DUY NHẤT** tại thanh Trạng thái dưới đáy (`nut_tk`): `● Máy đơn · Máy chủ LAN ▾` (hoặc khi kết nối LAN thì đổi thành `● LAN: Trực tuyến · <Tên user>`).
  + Dải Banner trên cùng sau khi xóa sẽ cực kỳ thanh lịch, chỉ còn: `[ Tên dự án ] | Phiên bản 0.9.76 | Bản Tiêu chuẩn · Sử dụng nội bộ`.

---

## PHẦN XV: CHUẨN HÓA MỸ THUẬT BIỂU TƯỢNG (APP ICON): NÂNG TÔNG NỀN TỪ XANH ĐEN SANG ROYAL NAVY GRADIENT

### 1. Phân tích Chuyên môn: Có Nên Thay Đổi Nền Xanh Đen Sáng Hơn Không?
- **KẾT LUẬN: CỰC KỲ NÊN VÀ HOÀN TOÀN CHÍNH XÁC VỀ MẶT THỊ GIÁC & NHẬN DIỆN THƯƠNG HIỆU!**
- **Nhược điểm của nền xanh đen cũ (#061224 - #0A1C36)**:
  + Khi đặt trên Windows Taskbar tối màu (Dark Mode mặc định của Win 10/11), nền xanh đen bị nuốt trọn vào thanh tác vụ, làm mất đi hình khối Squircle bo tròn bên ngoài.
  + Khi đặt trên hình nền Desktop tối, biểu tượng trông u ám, nặng nề, thiếu độ tương phản.
  + Sắc đen quá sâu làm giảm độ rực rỡ và phát quang của khối Mái nhà Vàng kim và Thửa đất Ngọc lục bảo.
- **Ưu điểm vượt trội của nền Royal Cobalt to Deep Navy (#1D4ED8 ➔ #0F3866)**:
  + **Độ tương phản cao (High Contrast)**: Tách lớp rõ ràng trên cả thanh Taskbar màu đen lẫn Desktop sáng màu.
  + **Tôn vinh biểu tượng trung tâm**: Nền xanh hoàng gia tươi sáng kích hoạt hiệu ứng phát quang (Glow effect), giúp mái nhà vàng và thửa đất ngọc lục bảo tỏa sáng lộng lẫy và sống động hơn gấp nhiều lần.
  + **Đẳng cấp GovTech hiện đại 2026**: Thể hiện sự trẻ trung, minh bạch, năng động và chính quy của phần mềm chuyển đổi số nhà nước.

### 2. Thông số Kỹ thuật & Màu sắc Chuẩn hóa Mới:
- **Lớp nền Squircle (Squircle Base Gradient)**:
  + Đỉnh trên (Top): `#1D4ED8` (Royal Cobalt Blue rực rỡ).
  + Tâm giữa (Center): `#1E40AF` (Deep Royal Navy có vầng sáng Radial Glow nhẹ).
  + Đáy dưới (Bottom): `#0F3866` (Navy Blue chính quy, không đen kịt).
- **Khối trung tâm**:
  + Mái nhà An cư & Tái định cư: Vàng kim Hoàng Gia (`#F59E0B` / `#FCD34D`) với ánh kim Specular Highlight sắc nét.
  + 4 Thửa đất địa chính 3D: Ngọc lục bảo Emerald (`#10B981` / `#059669`) hiệu ứng Glassmorphism trong suốt phát quang.
- **Chữ PABT**: Màu trắng bạc tinh khiết (`#FFFFFF`), đổ bóng viền mờ (Drop Shadow) nhẹ nhàng để tách bạch trên nền xanh hoàng gia.
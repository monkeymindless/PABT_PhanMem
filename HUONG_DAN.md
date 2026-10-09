# Phần mềm PABT – lập phương án bồi thường, hỗ trợ (phiên bản 0.9.16 – BẢN THỬ NGHIỆM)

> **0.9.16 – BẢN THỬ NGHIỆM** (nhãn vàng "BẢN THỬ NGHIỆM" trên băng tiêu đề, tiêu đề cửa sổ, hộp Giới thiệu): dùng để kiểm tra
> trước khi phát hành chính thức. **Đã bỏ khóa ký gói cập nhật**: gói `.pabtcn` của bản thử nghiệm không có chữ ký số, chỉ được
> kiểm tra mã SHA-256 từng file và quét virus - chỉ cài gói nhận trực tiếp từ người phát triển. Máy đang dùng 0.9.13 – 0.9.15
> (còn khóa ký) **không cài được** gói không ký: cài bộ cài 0.9.16 (dự án, cài đặt, mẫu in trong `%APPDATA%\PABT` giữ nguyên).
>
> **0.9.16** - **Trình phê duyệt**: cửa sổ **Đợt trình…** có thêm văn bản trình (Tờ trình / Văn bản: số, ngày), **số / ngày
> phương án tổng** (tự in vào dòng "Đính kèm Phương án số …" và ngày ký của bảng tổng hợp), **số PA chi tiết từng hộ** (nút
> **Đánh số PA chi tiết…** hoặc sửa thẳng trên bảng; tự in vào "Số: …/" và ngày của phương án chi tiết, mang sang quyết định phê
> duyệt), khung **Mẫu văn bản trình**: **Thêm mẫu** tờ trình (Word, Excel, PDF) / phương án tổng (Word, PDF), **Sửa mẫu**, **Mẫu
> mặc định**, **Chỗ trống dùng trong mẫu…**. Xuất / In: chọn từng mẫu (in riêng lẻ) hoặc **Chọn tất cả mẫu (in đồng loạt)**, lưu
> thành 2 thư mục **PA CHI TIET** và **PA TONG**. Nút **Sửa đợt…** báo rõ khi chưa chọn đợt (bấm đúp dòng đợt cũng sửa được);
> lỗi bất thường trong nút bấm không còn mất im lặng (hiện thông báo, ghi `loi.log`). **Nhanh hơn**: mở phần mềm 0,73 -> 0,38
> giây, lưu một hộ rồi tải lại danh sách (3.000 hộ) 0,47 -> 0,05 giây, mở dự án / cửa sổ lập phương án nhanh hơn ~20%; cửa sổ
> đã đóng được giải phóng khỏi bộ nhớ (trước: mở - đóng cửa sổ lập phương án nhiều lần trong ngày làm phần mềm nặng dần). Đọc số
> "1.070" trong ô Excel dạng chữ đúng là 1.070 (trước: 1,07); số tiền "1.070,5" ở quyết định đúng (trước: 10.705). Menu **Đơn
> giá riêng dự án** có biểu tượng. File dự án nâng lên CSDL v11 khi mở bằng 0.9.16 (bản cũ hơn không mở được file đã nâng cấp).
>
> **0.9.15** (gói cập nhật `PABT_CapNhat_0.9.15.pabtcn`, cài lên bản 0.9.13 trở lên: nút **Cập nhật phần mềm** hoặc nhấp đúp file gói):
> **Nhập phương án chi tiết** từ file Excel mỗi sheet một hộ (menu **Dự án**); **menu trái gọn** - các lệnh Dự án gom vào một nút
> xổ, bấm tiêu đề nhóm để đóng / mở (nhớ cho lần sau), vừa màn hình 1366×768 không phải cuộn; **↶ Hoàn tác / ↷ Làm lại** lên
> băng tiêu đề; bỏ chữ "Tổ chức làm nhiệm vụ bồi thường" trên băng tiêu đề. **Nhanh hơn với dự án lớn**: tạo dự án mới / tự lập
> phương án 1.000 hộ từ ~13 giây còn ~1 giây, xuất bảng tổng hợp từ ~13 giây còn ~2 giây; chuyển hộ khi lập phương án nhanh hơn
> (không đọc lại toàn bộ dự án mỗi lần). Bản in giữ nguyên như cũ.
> Dự án **3.000 hộ / 5.000 thửa** (đo cùng máy, bản cũ -> 0.9.15): tạo dự án 105 giây -> 3 giây (cửa sổ không còn "Không phản hồi":
> tạo dự án, nhập file Excel chạy nền, hiện hộp "Đang xử lý…"), xuất bảng tổng hợp 82 -> 3 giây, mở dự án 2,7 -> 0,8 giây, hoàn tác
> 2 -> 0,8 giây; gõ ô tìm ở trang Thông tin tổng quát / Theo dõi tiến độ không còn khựng (lọc khi ngừng gõ); đóng cửa sổ lập
> phương án mà không sửa gì thì không tải lại danh sách; đọc quyết định khớp tên gần đúng nhanh gấp ~6 lần.
> Thông báo sau khi nhập file (nhiều điểm cần xem lại) có ô cuộn, hiện đủ mọi điểm, nút **Chép danh sách** / **Đóng** luôn nằm
> trong màn hình (trước đây danh sách dài đẩy nút OK ra ngoài).
> Cột **Số lượng** các mục nhà, công trình, cây trồng, vật nuôi, hỗ trợ luôn hiện kiểu kế toán (ít nhất 1 chữ số sau dấu phẩy: 20,0).
> **Cập nhật đơn giá từ văn bản không có bảng** (vd. QĐ 31/2025/QĐ-UBND vật nuôi): phần mềm đọc đơn giá viết trong điều khoản
> ("Cá giống: 30.000 đồng/m² mặt nước"), ghép tên với tiêu đề khoản; sửa được tên, ĐVT trước khi áp dụng; khoảng giá "từ… đến…",
> tỷ lệ % liệt kê riêng để nhập tay. Văn bản đã có tên trong danh sách nhưng chưa có mục nào: mục mới vẫn được chọn.
> **Đơn giá riêng của dự án** (menu **Đơn giá, dự toán** → **Đơn giá riêng dự án…**, hoặc nút cùng tên trong **Bộ đơn giá**):
> - Thẻ **Quy ước giá tương đương**: tự gõ tài sản đặc biệt của từng dự án (tên thực tế, áp giá theo, ĐVT, đơn giá, căn cứ), hoặc
>   **Thêm theo mục trong bộ đơn giá…** (chọn mục tương đương, lấy sẵn ĐVT / đơn giá, chỉ gõ tên thực tế). Bấm **Lưu quy ước**.
> - Thẻ **Nhập đơn giá thẩm định (tài sản đặc biệt)**: chọn file kết quả / chứng thư thẩm định giá đã được phê duyệt (Excel, Word,
>   PDF, CSV có bảng Tên tài sản - ĐVT - Đơn giá); phần mềm tự đọc số chứng thư, ngày, đơn vị thẩm định; gõ quyết định phê duyệt
>   giá; xem lại / sửa / bỏ chọn từng dòng rồi **Đưa vào đơn giá của dự án**. Căn cứ ghi vào phương án: chứng thư, quyết định phê
>   duyệt, "tài sản đặc biệt theo Quyết định số 18/2026/QĐ-UBND" (sửa được ở ô **Áp dụng theo**). Nhập chứng thư điều chỉnh: dòng
>   trùng tên + ĐVT được cập nhật giá.
> - Khi lập phương án, các dòng này đứng **đầu ô chọn nhanh** của thẻ Nhà, công trình và Cây trồng, vật nuôi (nhãn **[Quy ước]** /
>   **[Thẩm định]**): chọn → số lượng → Thêm; tên in ra là tên thực tế, cột căn cứ giá ghi theo quy ước / chứng thư.
> - Dòng riêng của dự án (nền xanh) được **giữ lại khi "Áp bộ đơn giá vào dự án"**; dòng của bộ đơn giá mà sửa thì thành dòng
>   riêng (dòng của bộ bị xóa sẽ trở lại khi áp bộ đơn giá).
>
> **Cập nhật từ trang web - thêm nguồn văn bản Trung ương** (Quốc hội, Chính phủ, Bộ ngành) bên cạnh Công báo Đồng Nai:
> - Ô nguồn có sẵn: **Cơ sở dữ liệu quốc gia về văn bản pháp luật** (vbpl.vn - tìm "bồi thường, hỗ trợ, tái định cư", "thu hồi
>   đất", "đất đai"), **Hệ thống văn bản Chính phủ** (vanban.chinhphu.vn), **Công báo Chính phủ** (congbao.chinhphu.vn) - quét
>   các văn bản mới, **Thư viện pháp luật** (thuvienphapluat.vn).
> - Gõ từ khóa rồi chọn ô **Từ khóa tìm trên**: Công báo Đồng Nai / CSDL quốc gia văn bản pháp luật / Thư viện pháp luật.
> - Nhận biết số hiệu Luật (…/QH15), Nghị định (…/NĐ-CP), Thông tư (…/TT-…), cơ quan ban hành (Quốc hội, Chính phủ, Bộ…). Văn
>   bản đã có trong danh mục văn bản căn cứ hiện "Đã có"; văn bản mới liên quan bồi thường, hỗ trợ, tái định cư, thu hồi đất được
>   tự chọn. Văn bản không có bảng giá được ghi vào danh mục văn bản căn cứ để theo dõi (phần mềm không tự đổi quy tắc tính).
> - Thư viện pháp luật thường chỉ cho tải file khi đăng nhập: khi đó tải file về máy bằng trình duyệt rồi dùng **Cập nhật bộ đơn
>   giá từ file…**.
> - Trang web đổi cấu trúc / muốn thêm nguồn (vd. trang văn bản của Bộ Nông nghiệp và Môi trường): tạo file
>   `%APPDATA%\PABT\nguon_web.json`, ví dụ
>   `{"tim": {"vbpl": ["CSDL quốc gia VBPL", "https://vbpl.vn/...Keyword={q}"]}, "goi_y": [["Tên hiện trên ô chọn", "https://..."]]}`
>   (mẫu tìm kiếm phải bắt đầu https:// và có `{q}` ở chỗ từ khóa).
> - Ô nguồn không còn hiện các địa chỉ `http://127.0.0.1:…` (do chạy kiểm thử trên máy ghi vào; tự dọn khi mở cửa sổ).

> **0.9.6**: bộ cài mới (biểu tượng mới cho PABT.exe và lối tắt Desktop; menu trái biểu tượng to, nét dày; nút dạng viền; thẻ mục dạng khối). **0.9.3 – 0.9.5** phát hành dạng gói cập nhật `PABT_CapNhat_<phiên bản>.pabtcn` (cài bộ cài 0.9.2 rồi áp gói: nút **Cập nhật
> phần mềm** hoặc nhấp đúp file gói).
> - 0.9.5: logo mới; màn hình chính có thẻ số liệu (số hộ, đã lập PA, tổng kinh phí, phê duyệt, chi trả, bàn giao), nút thao tác
>   nhanh, danh sách hộ gọn và thẻ **Tổng hợp sau áp giá** (tiền từng mục); chính sách hỗ trợ ghi tên theo câu chữ quy định, nhập
>   theo **cách tính** (in gộp ô như mẫu); ô **Ghi chú** khi nhập (quy định, cách tính); sửa thẳng tên / đơn giá tài sản; gõ tiếng
>   Việt trong ô chọn; nhân khẩu, DT đất NN chuyển vào thẻ Hỗ trợ. File dự án nâng lên CSDL v8 (máy chưa cập nhật 0.9.5 không mở
>   được file đã mở bằng 0.9.5).
> - 0.9.3: các lệnh ở **menu dọc bên trái** (thanh nút phía trên như cũ: `PABT.exe --menu-tren`); băng tiêu đề lớn hơn một chút.
> - 0.9.4: hồ sơ hộ và phương án **chung một cửa sổ**, nhập nhanh (chọn → số lượng → Thêm), ô số gõ được **công thức**, vị trí đất
>   chọn theo **bảng giá NQ 28**, cây nhập theo **đường kính / chu vi**, thuê nhà / tự lo chỗ ở **một dòng theo nhân khẩu**,
>   **tái định cư là tình trạng** của hộ, mật độ cây đối chiếu chi tiết, **Bảng khái toán** theo mẫu (Excel / PDF), giao diện dịu
>   màu hơn.

File dự án `.pabt` (SQLite); nhập file PABT Excel hoặc danh sách hộ, thửa bất kỳ; sửa hồ sơ kiểm kê; lập phương án từng hộ;
in theo mẫu; đối chiếu với Excel; khóa file khi nhiều máy cùng mở; bộ cài cho máy không có Python.

## Bắt đầu: Dự án mới (nhập thô → tự lập phương án → 2 bảng in)

Bộ cài gồm phần mềm, **bộ đơn giá Đồng Nai tích hợp** và hai mẫu in trống; không kèm dự án hay hồ sơ hộ nào.
Bấm nút **Dự án** (đầu menu trái) → **Dự án mới…** và làm 4 bước — đây là nơi duy nhất nhập / sửa dữ liệu thô:

1. **Thông tin dự án**: tên dự án, cấp và tên xã/phường, năm, đơn vị lập, người ký… (thông tin đơn vị, người ký được nhớ cho lần sau).
2. **Danh sách hộ, thửa (nhập thô)**: bấm **Nhập file Excel thô…** hoặc gõ trực tiếp; sửa ngay trên bảng. Các trường:
   Họ và tên | Địa chỉ | Số CCCD | Ngày cấp | Nơi cấp | Số điện thoại | Số tờ bản đồ | Số thửa đất | Diện tích thu hồi |
   Loại đất thu hồi | Vị trí đất (có sẵn trong Excel hoặc nhập tay) | Nhân khẩu | Nguồn gốc | Ghi chú — file Excel chỉ cần có
   các cột cần thiết, tên cột viết kiểu nào phần mềm cũng tự nhận. **Loại đất** và **Vị trí** chọn trong danh sách xổ xuống
   (nhấp đúp ô; loại đất theo danh mục của bộ đơn giá, vị trí 1–5; vẫn gõ tay được, ví dụ ONT+CLN). Mỗi dòng một thửa; họ tên để
   trống = thửa tiếp của hộ trên. Thửa nhiều loại đất nên tách mỗi loại một dòng với diện tích riêng.
   Các dòng này được lưu nguyên trong **vùng dữ liệu thô riêng** của file dự án (bảng `tho_nhap`, kèm liên kết tới hộ / thửa tạo ra),
   tách biệt với vùng đơn giá: vùng thô là dữ liệu ban đầu để phân tích, đối chiếu; vùng đơn giá cố định.
3. **Bảng giá đất của dự án**: phần mềm liệt kê các cặp loại đất × vị trí có trong danh sách; nhập giá theo bảng giá đất và hệ số K.
   Dữ liệu chưa có vị trí: nhập **Vị trí áp dụng**. Ô cam là điểm cần lưu ý.
4. **Hoàn thiện, in**: chọn nơi lưu file `.pabt`, bấm **Lưu: tạo dự án và lập phương án**. Phần mềm tự lập mục 1 từ các thửa
   (giá theo bảng giá đất), áp dụng gợi ý hỗ trợ theo QĐ 42/2025 (đào tạo chuyển đổi nghề HT09/HT10 trong hạn mức, ổn định đời
   sống khi có nhân khẩu…), tính thưởng, rồi xuất **phương án chi tiết từng hộ** và **bảng tổng hợp** (Excel, kèm PDF nếu có
   Microsoft Excel) vào thư mục `BanIn_…` cạnh file dự án.

Sau đó bổ sung từng hộ ở **Lập phương án hộ…** (nhà, công trình, cây trồng từ danh mục; số lượng) và **Hồ sơ hộ…**.

## Bản in (phương án chi tiết, bảng tổng hợp)

- Đầu trang: tiêu đề cơ quan 2 dòng ("TRUNG TÂM PHÁT TRIỂN QUỸ ĐẤT / THÀNH PHỐ ĐỒNG NAI", "CHI NHÁNH VĨNH CỬU"), quốc hiệu, số
  phương án "Số: …/PA-TTPTQĐ.CNVC", chức vụ người ký "PHÓ GIÁM ĐỐC" — lấy từ **Thông tin dự án** (Đơn vị cấp trên, Tên đơn vị trên
  tiêu đề bản in, Ký hiệu số phương án, Chức vụ người ký…); ô nào để trống thì dùng thông tin mặc định của Chi nhánh Vĩnh Cửu
  (`pabt/to_chuc.py`).
- Các đường kẻ ngang của mẫu cũ (dưới tên cơ quan, dưới "Độc lập - Tự do - Hạnh phúc", dưới tên dự án) được giữ: lưu ở
  `mau_in\IN_CHITIET.duong_ke.xml` và chèn vào từng file bản in; **Cập nhật mẫu in…** từ file Excel lấy lại cả đường kẻ.
- Dòng 1.x (bồi thường đất): "Thửa đất số …, tờ bản đồ số …, loại đất …, xã (phường) … (Vị trí 1 / 2 / 3 / 4)"; thiếu thông tin
  thì để "……" chờ điền.

## Bảng giá đất NQ 28/2025/NQ-HĐND (tích hợp)

Phần mềm có sẵn bảng giá đất theo Nghị quyết 28/2025/NQ-HĐND của HĐND tỉnh Đồng Nai (áp dụng từ 01/01/2026) cho **Xã Trị An,
Xã Tân An, Xã Phú Lý, Phường Tân Triều**: 161 đoạn đường, 1.127 dòng, gồm đất phi nông nghiệp (đất ở; thương mại, dịch vụ; sản xuất,
kinh doanh phi NN – Phụ lục III) và nông nghiệp (cây lâu năm, cây hằng năm; rừng sản xuất, nuôi trồng thủy sản – Phụ lục I).
Mỗi đoạn đường có 7 mức: mặt tiền (MT); T1–T3: đường nhựa, bê tông đấu nối trực tiếp ra đường; K1–K3: đường không đấu nối trực
tiếp và thông ra đường (theo bề rộng và khoảng cách: ≤1.000m / ≤500m, hoặc ≤600m / ≤400m với một số tuyến).

- **Dự án mới → bước 3 (Bảng giá đất)**: chọn một dòng → **Tra bảng giá đất NQ 28/2025…** → lọc theo xã của dự án, loại giá tự
  chọn theo loại đất (ONT/ODT → đất ở; CLN, HNK, BHK, LUK… → cây lâu năm, hằng năm; NTS, RSX → rừng, thủy sản), tìm tên đường không
  cần dấu → nhấp đúp. Giá (quy ra đồng/m²) và căn cứ (đường, đoạn, mức vị trí) được điền vào, căn cứ lưu theo giá đất của dự án.
- **Bộ đơn giá… → Tra bảng giá đất NQ 28/2025…** để xem; **Xuất bảng giá đất ra Excel…** (mỗi địa bàn một sheet).
- Số liệu chép từ bản PDF đóng dấu của Nghị quyết (Phụ lục I trang 172–205, 1143–1214; Phụ lục III trang 1672–1707, 2700–2775) và
  kiểm tra chéo bằng nhận dạng chữ; khi dùng làm căn cứ chính thức nên đối chiếu văn bản gốc. Dữ liệu ở `pabt/bang_gia_nq28.json`.

## Bộ đơn giá tích hợp (cố định)

**Bộ đơn giá…** xem (chỉ đọc) toàn bộ: 5.668 đơn giá tài sản, cây trồng (QĐ 48/2025 sửa đổi bởi QĐ 66/2025; nhà, công trình theo
QĐ 18/2026 sửa đổi bởi QĐ 53/2026), 39 khoản chính sách hỗ trợ, tái định cư (QĐ 42/2025), tham số và **hạn mức giao đất nông nghiệp
khu vực Đông Nam Bộ** (Điều 176 Luật Đất đai 2024: cây hằng năm, NTS 3 ha; cây lâu năm 10 ha vùng đồng bằng; rừng 30 ha), biểu
**thưởng bàn giao mặt bằng**, quy ước giá tương đương và 17 văn bản căn cứ (gồm dự thảo sửa đổi QĐ 42/2025 đang theo dõi).

- Danh mục, chính sách, tham số trong mỗi dự án được **khóa**: không sửa được, kể cả bằng công cụ SQLite (trigger chặn).
  Trong **Lập phương án hộ**, đơn giá dòng lấy từ danh mục cố định. Giá đất lấy từ bảng giá đất của dự án cũng cố định.
- **Tài sản không có trong đơn giá**: thêm mục tương đương từ danh mục rồi **sửa tên** thành tên tài sản thực tế (nhấp đúp ô Tên).
  Dòng tự chuyển thành "tương đương": giữ nguyên đơn giá của mục danh mục, ghi căn cứ "Áp giá tương đương: mã - tên mục gốc";
  tên in trên phương án là tên đã sửa. (Hoặc **Thêm hạng mục khác…** → gõ tên → **Chọn giá tương đương**.) Giá thực tế khác hẳn
  (thẩm định giá, báo giá) thì dùng **Thêm hạng mục khác…**, nhập đơn giá và ghi căn cứ. Mọi dòng tương đương / nhập tay hiện ở
  **Rà soát giá…**.
- **Cập nhật bộ đơn giá từ file…**: chọn file PABT Excel chuẩn (.xlsm), gói bộ đơn giá (.sqlite), hoặc **file đơn giá bất kỳ**:
  Excel (.xlsx/.xlsm), Word (.docx), PDF có chữ, CSV. Phần mềm tìm bảng có cột Tên – ĐVT – Đơn giá (tiêu đề "nghìn đồng" thì tự nhân
  1.000; PDF đọc theo dòng "<mã> <tên> <ĐVT> <đơn giá>"), so khớp với bộ đơn giá đang dùng (theo mã, rồi theo tên không dấu) và hiện
  bảng xem trước: **xanh** = mục mới, **vàng** = đổi giá (**gần đúng** = tên gần giống, xem kỹ), **xám** = không đổi. Nhóm mặc định
  **Tự động** (theo trích yếu văn bản, tiêu đề nhóm I/II…, từng dòng); có thể chọn cả bảng thuộc một nhóm. Bảng phân cấp như phụ lục
  quyết định UBND được ghép tên như bộ đơn giá: "Cây bưởi - Năm thứ 1", "Cây lúa (Đông Xuân)". Bỏ chọn dòng không muốn, bấm
  **Áp dụng** → tạo phiên bản bộ đơn giá mới (bộ cũ giữ nguyên; số hiệu, ngày, trích yếu văn bản ghi vào danh mục văn bản căn cứ).
  File Word / Excel cũ (.doc / .xls, văn bản trên Công báo thường là .doc) tự chuyển nhờ Microsoft Word / Excel trên máy. PDF ảnh
  scan: tự nhận dạng chữ nếu máy có Tesseract OCR (như đọc quyết định), không có thì chuyển sang Excel / Word trước.
- **Cập nhật từ trang web…** (phát hành riêng bằng **gói cập nhật** `PABT_CapNhat_0.9.14.pabtcn` trở lên, không có trong bộ cài
  gốc — máy chưa cài gói thì nút này hướng dẫn cài): nhập **đường dẫn** trang web (cổng thông tin, trang chi tiết văn bản, Google Drive / Sheets / Docs, thư
  mục Google Drive chia sẻ công khai) hoặc **từ khóa** (tìm trên Công báo thành phố Đồng Nai; có sẵn 3 nguồn gợi ý: đơn giá bồi
  thường, bồi thường – hỗ trợ – tái định cư, giá đất) → **Quét**. Phần mềm vào thêm các trang chi tiết văn bản để lấy file đính kèm
  ("Tải tập tin"), xếp theo mức liên quan, đánh dấu **Đã có trong bộ đơn giá** (theo số hiệu trong danh mục văn bản căn cứ) và **tự
  chọn văn bản MỚI**. **Tải và phân tích** → mỗi văn bản: tải, đọc, nhận số hiệu / ngày / cơ quan ban hành / trích yếu, xem trước
  theo **thứ tự ngày ban hành** (văn bản sửa đổi áp sau văn bản gốc) rồi **Áp dụng**. Văn bản đã có: các dòng mặc định không chọn
  (áp dụng lại văn bản gốc sẽ ghi đè giá đã được văn bản sau sửa đổi, ví dụ QĐ 48/2025 đã được QĐ 66/2025 sửa giá lúa). Văn bản
  chính sách không có bảng giá: chỉ ghi vào danh mục văn bản căn cứ để theo dõi — phần mềm **không tự đổi quy tắc tính**; các câu
  "Sửa đổi / Bãi bỏ …" trong văn bản được liệt kê để tự xử lý. Đường dẫn kết thúc `.json` là thông báo cập nhật của đơn vị quản lý
  (`phien_ban`, `tai_ve`, `sha256`): tải, kiểm tra mã SHA-256 rồi cài. Luôn xem bảng trước khi áp dụng.
- **Kiểm tra an toàn** (góc dưới bên phải): tình trạng phần mềm diệt virus của máy, bộ quét file, toàn vẹn file cài đặt (phát
  hiện file bị sửa / DLL lạ chèn vào), chữ ký số gói cập nhật; nút **Quét một file…** quét file nhận qua Zalo / email / USB trước
  khi mở. PABT tự quét file tải từ web, gói cập nhật, file Word / Excel cũ (Microsoft Defender hoặc phần mềm diệt virus có AMSI)
  — có mã độc thì chặn / xóa; Word / Excel tự động hóa luôn tắt macro; kết nối mạng chỉ chấp nhận chứng chỉ HTTPS hợp lệ (TLS
  1.2+); gói cập nhật thiếu / sai chữ ký số bị từ chối (bản thử nghiệm 0.9.16 không có khóa ký: chỉ kiểm tra mã SHA-256 từng
  file của gói). PABT không thay phần mềm diệt virus: giữ Defender luôn bật, cập nhật.
- **Tra cứu văn bản mới…**: mở Công báo Đồng Nai, trang góp ý dự thảo, Thư viện pháp luật để theo dõi quyết định mới.
- **Áp bộ đơn giá vào dự án đang mở**: dự án đã lập không tự đổi giá; chọn lệnh này khi muốn dùng bộ mới (dòng đã lập giữ giá cũ —
  dùng Rà soát giá để kiểm tra).
- Máy phát triển: đóng gói lại bộ tích hợp bằng `.venv\Scripts\python tao_bo_don_gia.py <PABT_CHUAN.xlsm> <YYYY.MM.DD>` trước khi dựng exe.

## Nhập file PABT Excel cũ

1. **Nhập file Excel…**:
   - chọn file PABT `.xlsm` của đơn vị để có ngay hồ sơ và danh mục đơn giá;
   - hoặc chọn một danh sách hộ, thửa (Excel bất kỳ), rồi lưu thành file `.pabt` mới (tự lấy bộ đơn giá tích hợp).
2. **Thông tin dự án…**: tên dự án, xã/phường, và các thông tin in trên phương án: đơn vị cấp trên, đơn vị lập,
   ký hiệu số phương án (phần sau "Số: …/"), người lập biểu, người kiểm tra, chức vụ và tên người ký. Mẫu in không ghi cố định
   tên đơn vị hay người ký; các ô này để trống thì bản in để trống. Khi xóa trắng để nhập dự án mới, hoặc tạo dự án mới từ
   dự án đang mở, thông tin đơn vị và người ký được giữ lại.

## Giao diện và màu

Đầu cửa sổ chính là **băng tiêu đề** (bo góc, đổ bóng): biểu tượng, dòng "PHẦN MỀM LẬP PHƯƠNG ÁN BỒI THƯỜNG, HỖ TRỢ, TÁI ĐỊNH CƯ", tên đơn vị
(**Trung tâm Phát triển quỹ đất Chi nhánh Vĩnh Cửu**), dòng trực thuộc và địa chỉ, cùng phiên bản đang chạy ở góc phải (sửa ở
`pabt/to_chuc.py`; tên đơn vị, ký hiệu số phương án cũng được điền sẵn khi lập dự án mới). Màn hình Dự án mới có băng tổ chức tương tự.

Ngay dưới băng tiêu đề là **khu vực nút lệnh** gom trong một khung trắng (đổ bóng nhẹ), chia 5 thẻ nhóm có tên nhóm chữ nhỏ phía trên; nút nền nhạt theo màu nhóm, biểu tượng trên – chữ dưới, dàn kín chiều ngang (thường 2 dòng khi cửa sổ phóng to): **Dự án** (Dự án mới, Mở dự án,
Lưu dự án thành, Nhập file Excel, Thông tin dự án), **Hồ sơ và phương án** (Hồ sơ hộ, Thêm hộ, Lập phương án hộ, Kiểm tra lỗi),
**Đơn giá, dự toán** (Bộ đơn giá, Rà soát giá, Quy chuẩn cây, tài sản, Dự toán, áp giá dự thảo), **Trình, theo dõi tiến độ** (Đợt
trình, Trạng thái hộ, Nhập quyết định), **In ấn, báo cáo** (In / Xuất, Báo cáo tổng hợp, Xuất báo cáo đối chiếu, Cập nhật mẫu in).
Nút **Cập nhật phần mềm** và **Giới thiệu** nằm ở **góc dưới bên phải** cửa sổ, trên dòng trạng thái.

Trên danh sách hộ có bộ lọc **Đợt** (tất cả / chưa xếp đợt / từng đợt), **Trạng thái** (chưa / đã lập PA, chưa / đã phê duyệt,
đã phê duyệt chưa chi trả, đã chi trả chưa bàn giao, đã bàn giao, có ghi chú…) và ô **Tìm** (không cần dấu, tìm cả ghi chú); bên
phải ghi số hộ và tổng tiền đang lọc. Danh sách có thêm các cột **Đợt trình, Phê duyệt, Chi trả, Bàn giao MB, Ghi chú theo dõi**;
nhấp đúp ô Ghi chú theo dõi để ghi tiến độ của hộ (lưu ngay vào file dự án), nhấp đúp ô khác để mở phương án.
Màn hình hẹp (laptop 1366 px, màn hình phóng to 125%…) thì các nhóm tự xuống dòng và băng tiêu đề tự cao lên, cửa sổ không tràn ra
ngoài màn hình; cửa sổ mở vừa màn hình đang dùng.

**Thử nghiệm menu dọc bên trái** (để so sánh, chưa phải giao diện chính): chạy `PABT.exe --menu-trai` (lối tắt
`so_sanh_giao_dien\PABT - Thu nghiem menu trai.lnk`, hoặc `THU_MENU_TRAI.bat` khi chạy từ mã nguồn). Các lệnh thành một cột bên trái
theo 5 nhóm, nút **Thu gọn menu** chỉ để lại biểu tượng (rê chuột hiện tên lệnh); danh sách hộ dùng gần trọn chiều cao (khoảng gấp đôi số
dòng so với thanh nút phía trên). Ảnh so sánh hai kiểu ở thư mục `so_sanh_giao_dien`.

**Menu trái gọn** — để màn hình nhỏ (1366×768) không phải cuộn tìm lệnh:
- Các lệnh nhóm Dự án (Dự án mới, Mở, Lưu dự án thành, Nhập file Excel, Nhập phương án chi tiết, Thông tin dự án, Dự án trên
  máy chủ) gom vào **một nút "Dự án"** đầu menu: bấm để xổ danh sách.
- Bấm **tiêu đề nhóm** (▾ HỒ SƠ VÀ PHƯƠNG ÁN, ▸ ĐƠN GIÁ, DỰ TOÁN…) để đóng / mở nhóm. Lần đầu mở sẵn "Hồ sơ và phương án" và
  "Bảng tổng hợp"; nhóm nào đang mở / đóng phần mềm nhớ cho lần sau.
- **↶ Hoàn tác / ↷ Làm lại** nằm trên băng tiêu đề, ngay cạnh tên phần mềm (phím tắt Ctrl+Z / Ctrl+Y vẫn dùng như cũ).

Các màn hình nhập (Thông tin dự án, Dự án mới, Trạng thái hộ…) chia thẻ có tiêu đề, nhãn canh phải, ô nhập bo góc cùng chiều cao,
giới hạn chiều rộng và canh giữa; hộp thoại lớn hơn màn hình tự thu vừa; ô chữ dài hiện từ đầu chữ. Phông Segoe UI, nút có biểu tượng.

Nút được tô màu theo việc làm, giống nhau ở mọi màn hình:

| Màu | Nút |
|---|---|
| Xanh lá | **Lưu**, **Lập phương án hộ** |
| Xanh ngọc | **Thêm…** (thêm hộ, thửa, dòng), **Hồ sơ hộ** |
| Xanh dương | **Nhập file Excel**, **Mở dự án**, **Nạp danh mục**, **Cập nhật mẫu in** |
| Cam | **Gộp**, **Chuyển**, **Tách**, **Bỏ thay đổi** (thao tác làm thay đổi cấu trúc hồ sơ) |
| Đỏ | **Xóa…** (luôn hỏi lại) |
| Tím | **In / Xuất**, **Xuất báo cáo** |
| Xám đậm | **Thông tin**, **Rà soát**, **Gợi ý**, **Chọn**, **Hộ trước / Hộ sau** |
| Xám nhạt | **Hủy**, **Đóng**, **Giới thiệu** |

Tiêu đề cột bảng, nhãn thuộc tính (Họ và tên, Số CCCD…) và tab đang chọn dùng màu xanh đậm. Bảng tô xen kẽ màu dòng. Nút mờ là nút
chưa dùng được (ví dụ **Lưu** khi chưa có thay đổi). Đổi màu một nhóm: sửa `MAU` trong `pabt/giao_dien.py`.

## Hồ sơ kiểm kê: hộ, thửa (giai đoạn 4)

Chọn một hộ rồi bấm **Hồ sơ hộ…** (hoặc **Thêm hộ…** để tạo hộ mới):

- Sửa họ tên, CCCD, ngày / nơi cấp, địa chỉ, điện thoại, pháp lý, tranh chấp, tái định cư, trạng thái, ghi chú.
- Bảng **thửa đất thu hồi**: nhấp đúp ô để sửa tờ, thửa, loại đất, DT thu hồi (`143,8`, `1.070`), nguồn gốc, vị trí;
  **Thêm thửa**, **Xóa thửa** (thửa đang có dòng bồi thường đất thì hỏi lại; các dòng đó còn lại, không gắn thửa).
- **Tách theo loại đất**: thửa ghi `ONT+CLN` tách thành một dòng ONT và một dòng CLN để chia diện tích theo từng loại đất
  (mục 1 tra được giá đất đúng loại). Cùng tờ, thửa nhưng khác loại đất là hợp lệ.
- **Chuyển thửa sang hộ khác…**: chuyển thửa cùng các dòng bồi thường đất gắn với thửa.
- **Gộp hộ khác vào hộ này…**: dùng khi một người bị tách thành hai hộ (cùng tên khác địa chỉ…); danh sách chọn đưa hộ
  cùng họ tên lên đầu (★). Thửa, phương án của hộ kia chuyển sang, ô còn trống được điền từ hộ kia, hộ kia bị xóa.
- **Xóa hộ…**: xóa hộ cùng thửa và phương án (hỏi lại, không hoàn tác).
- **Lưu**: ghi cả hộ trong một lần, có nhật ký; phần mềm báo nếu thửa của hộ cũng có ở hộ khác.

## Nhiều máy cùng dùng một file dự án (giai đoạn 4)

Khi mở để sửa, phần mềm ghi file `<tên>.pabt.khoa` cạnh file dự án (máy, người dùng, giờ mở) và làm mới mỗi phút; đóng
dự án thì xóa. Máy khác mở cùng file (ví dụ trong thư mục Google Drive dùng chung) sẽ được báo đang có người sửa và chọn:

- **Mở chỉ xem** (khuyên dùng): xem danh sách, chi tiết hộ, in / xuất, đối chiếu; các lệnh sửa bị tắt, tiêu đề có `[CHỈ XEM]`.
- **Vẫn mở để sửa**: máy đang sửa trước đó sẽ được cảnh báo. Chỉ chọn khi chắc máy kia đã thôi sửa.

Máy kia tắt đột ngột thì khóa tự hết hạn sau 3 phút. Nhập file Excel đè lên file đang bị máy khác sửa sẽ bị từ chối.

## Máy chủ trong mạng nội bộ (LAN), tài khoản đăng nhập (0.9.2)

Không bắt buộc. Có 3 cách dùng, chuyển qua lại bất kỳ lúc nào:

| Cách dùng | Khi nào | Làm thế nào |
|---|---|---|
| **1. Offline trên một máy** | Không có máy chủ, làm một mình | Không thiết lập gì; dùng như trước (Mở dự án / Lưu dự án thành). |
| **2. Máy chủ LAN + tài khoản** | Đơn vị có máy chủ / thư mục dùng chung, nhiều người, nhiều máy | Đăng nhập ở máy bất kỳ: phần mềm **tự mở lại dự án đang làm dở** của tài khoản. |
| **3. Mang về làm offline** | Đi hiện trường, máy xách tay không vào mạng | Mang dự án từ máy chủ về máy, làm offline, về cơ quan **đưa lên** lại. |

**Thiết lập (một lần):**
1. Trên máy chủ, tạo thư mục (ví dụ `D:\PABT`), chia sẻ trong mạng (Share) và cấp quyền **đọc / ghi** cho người dùng → đường dẫn
   `\\TEN-MAY-CHU\PABT` (hoặc gán ổ mạng `Z:`). Không cần cài phần mềm máy chủ.
2. Máy đầu tiên: nút **Máy chủ LAN** (góc dưới bên phải) → **Thiết lập máy chủ…** → chọn thư mục → nhập tài khoản quản trị, mật
   khẩu → **Khởi tạo máy chủ mới**. Phần mềm tạo `pabt_may_chu.sqlite` (tài khoản), thư mục `DuAn\` (dự án dùng chung), `SaoLuu\`.
3. Đăng nhập bằng tài khoản quản trị → menu tài khoản → **Quản lý tài khoản người dùng…**: thêm tài khoản cho từng người
   (tài khoản không dấu, ví dụ `vinh.pt`; mật khẩu ≥ 6 ký tự), đặt lại mật khẩu, khóa / mở khóa, đổi vai trò.
4. Các máy khác: **Thiết lập máy chủ…** → chọn cùng thư mục → **Kết nối máy chủ có sẵn**.

**Hằng ngày:** mở phần mềm → hộp **Đăng nhập** (nhớ tài khoản lần trước). Đăng nhập đúng: dự án mở gần nhất của tài khoản được mở
lại ngay, ở bất kỳ máy nào. Hộp Mở dự án / Lưu / Dự án mới mặc định vào thư mục `DuAn` của máy chủ. Nút **Dự án trên máy chủ…**
(nhóm Dự án) liệt kê các dự án dùng chung: ai đang mở, ai đang mang về. Nhật ký file dự án và khóa nhiều máy ghi tên người đăng nhập.
Sai mật khẩu 5 lần liền thì tài khoản bị khóa (quản trị mở lại). Menu tài khoản có **Đổi mật khẩu…**, **Đăng xuất**.

**Không có máy chủ** (mất mạng, máy chủ tắt): phần mềm báo ở thanh trạng thái và làm việc **offline** bình thường với mọi chức
năng nhập liệu; trong hộp đăng nhập cũng có nút **Làm việc offline**. Muốn bỏ hẳn máy chủ trên một máy: **Thiết lập máy chủ… →
Không dùng máy chủ** (dữ liệu trên máy chủ giữ nguyên).

**Mang về làm offline:** Dự án trên máy chủ… → chọn dự án → **Mang về làm offline** (bản sao ở `%APPDATA%\PABT\offline`, tiêu đề
cửa sổ có `[BẢN LÀM OFFLINE]`; máy chủ ghi "đang được … mang về" để người khác biết, người khác không mang về được nữa). Khi có
mạng lại: đăng nhập → Dự án trên máy chủ… → **Đưa lên máy chủ** (bản cũ trên máy chủ được sao lưu vào `SaoLuu\` trước khi ghi đè).
Nếu trong lúc đó bản trên máy chủ đã bị người khác sửa, phần mềm báo **XUNG ĐỘT** và hỏi có vẫn đưa lên không (bản kia vẫn còn
trong `SaoLuu\`). **Hủy bản offline** để bỏ bản mang về mà không đưa lên.

Lưu ý: quyền truy cập file thật sự do quyền chia sẻ thư mục của Windows quyết định; tài khoản PABT để biết ai làm gì và nối tiếp công
việc ở máy bất kỳ. Nên sao lưu định kỳ thư mục máy chủ.

## Lập phương án hộ (giai đoạn 2)

Nhấp đúp một hộ trong danh sách (hoặc bấm **Lập phương án hộ…**). Hồ sơ hộ và phương án nằm **chung một cửa sổ**, nhập theo
thứ tự 5 thẻ, mỗi thẻ có nút **◀ Trở lại** / **Tiếp theo ▶** (thẻ cuối: **Lưu phương án hộ**):

1. **Thông tin hộ, thửa đất**: họ tên, CCCD, ngày cấp, nơi cấp, điện thoại, địa chỉ, pháp lý, tranh chấp, ghi chú và bảng thửa
   (tờ, thửa, loại đất, DT thu hồi, nguồn gốc, vị trí); tách thửa theo loại đất, chuyển thửa, gộp hộ, xóa hộ. Bấm **Tiếp theo**:
   hồ sơ được lưu để thửa mới dùng được ngay ở mục 1. **Thêm hộ…** chỉ hỏi họ tên rồi mở thẳng thẻ này.
2. **1. Đất**: chọn thửa ở ô **Thửa** → **Thêm thửa vào mục 1** (tự điền loại đất, diện tích còn lại, giá). Ô **Thửa** của dòng
   đổi được (nhấp đúp, chọn thửa khác của hộ). Ô **Vị trí** xổ xuống các tuyến đường, vị trí (MT, T1–T3, K1–K3) của **bảng giá
   NQ 28** theo địa bàn dự án: chọn là giá đất tự điền theo loại đất của dòng; gõ tay nội dung khác nếu vị trí không có trong bảng
   giá. Giá đất khác vẫn gõ đè được (ghi "Giá đất nhập tay" ở Ghi chú để rà soát).
3. **2. Nhà, công trình** / **3. Cây trồng** / **4. Hỗ trợ**: hàng **nhập nhanh** – gõ tên không cần dấu (`nha 1 tang`, `xoai 11-15`,
   `thue nha`) hoặc bấm ▼, chọn mục, gõ **số lượng**, **tỷ lệ %** (trống = 100) rồi Enter / **Thêm vào bảng**. Gõ tên không có trong
   đơn giá: dòng "nhập tay", con trỏ chuyển ngay tới ô Đơn giá để gõ giá và ghi Căn cứ giá (hoặc **Chọn giá tương đương…**).
   - Ô số (số lượng, diện tích, đơn giá, tỷ lệ) gõ được **công thức**: `=4,2*5,7`, `12x3+1,5`, `(10-2)*3`; số lượng làm tròn 1 chữ số
     thập phân (ĐVT ha giữ 4 chữ số).
   - **Cây trồng**: loại cây có quy cách theo đường kính thân (cây lâm nghiệp, cây cảnh) chọn tên loại cây (dòng không có mã, ví dụ "Sao đen"),
     chọn kiểu **Đường kính (cm)** hoặc **Chu vi (cm)**, gõ các số đo `15, 18x2, 22` (`18x2` = 2 cây): phần mềm tự xếp vào đúng quy
     cách đơn giá (chu vi = π × đường kính) và ghi số đo ở cột Quy cách.
   - Ô **Ghi chú** dưới hàng nhập nhanh: quy định pháp luật áp dụng, cách tính… (in ở cột Ghi chú của phương án). Tài sản chọn từ
     đơn giá vẫn **sửa thẳng tên hoặc đơn giá** trên bảng: đổi tên giữ đơn giá; đổi đơn giá thì dòng thành "nhập tay" (ghi lại giá
     trong bộ đơn giá ở cột Căn cứ giá để rà soát).
   - **Hỗ trợ** (thẻ 4): đầu thẻ có **Nhân khẩu**, Phải di chuyển chỗ ở, **DT đất NN đang sử dụng** (để trống = tự lấy diện tích đất
     nông nghiệp đã nhập ở mục 1) và **Tái định cư**. Dòng hỗ trợ ghi **tên chính sách theo câu chữ quy định** (Hỗ trợ ổn định đời
     sống; Hỗ trợ đào tạo, chuyển đổi nghề và tìm kiếm việc làm; Hỗ trợ tiền thuê nhà ở, tạm cư…), căn cứ ở cột Ghi chú, cột **Cách
     tính** in gộp thay ĐVT / số lượng / đơn giá / tỷ lệ:
     - **Ổn định đời sống**: nhập giá gạo, số kg, số tháng, tỷ lệ (theo nhân khẩu ở đầu thẻ) → "4 nhân khẩu x 30kg gạo x 6 tháng x
       16.000 đồng x 50%".
     - **Đào tạo, chuyển đổi nghề và tìm kiếm việc làm**: bảng các thửa đất nông nghiệp ở mục 1 (đánh dấu thửa, sửa diện tích, đơn giá
       đất, tỷ lệ 150% / 50%) → mỗi thửa một dòng; bản in có dòng tên chính sách đứng đầu nhóm.
     - **Thuê nhà ở, tạm cư / tự lo chỗ ở**: số tháng, mức hộ, mức mỗi nhân khẩu tăng thêm → một dòng "(1 hộ (4 nhân khẩu) * 1 tháng *
       6.000.000 đồng) + (1 nhân khẩu tăng thêm * 1.500.000 đồng * 1 tháng)". Đổi nhân khẩu là đơn giá và cách tính tự tính lại. (Số
       nhân khẩu của mức hộ đặt ở **Quy chuẩn cây, tài sản…**, mặc định 4 theo QĐ 42/2025.)
     - Chính sách không có trong đơn giá (**Hỗ trợ học phí, Hỗ trợ y tế, Hỗ trợ khác**) hoặc gõ tên khác: nhập số lượng, đơn giá.
   - **Tái định cư** không phải khoản tiền: chọn ở ô **Tái định cư** – không đủ điều kiện; đủ điều kiện theo khoản 4 / khoản 5 Điều
     111 Luật Đất đai năm 2024; đủ điều kiện theo khoản 4 (hộ nhiều thế hệ / nhiều cặp vợ chồng…), hoặc không có. Bản in ghi dòng
     "Tái định cư: Đủ điều kiện bố trí một (01) suất tái định cư theo quy định tại khoản 4 Điều 111 Luật Đất đai năm 2024."
- Ô chữ dài (tên, quy cách, căn cứ, ghi chú) tự xuống dòng; khi sửa mở khung nhiều dòng (Enter ghi, Shift+Enter xuống dòng).
- **Nhập bằng bàn phím** trong các bảng (thửa đất, mục 1–4): **Enter** ở ô đang đứng để mở sửa; sửa xong **Enter** ghi và tự sang
  ô nhập kế tiếp (hết dòng thì xuống dòng dưới); **Tab / Shift+Tab** sang ô kế / ô trước; ô xổ xuống chọn bằng phím ↑ ↓ rồi Enter.
  Hàng nhập nhanh: Tab đi lần lượt tên → số lượng → tỷ lệ → ghi chú → Thêm vào bảng; Enter để thêm.
- **Loại đất**: ô Loại đất ở bảng thửa xổ xuống danh mục loại đất theo Luật Đất đai năm 2024, ký hiệu theo Thông tư
  08/2024/TT-BTNMT (gõ tay được loại ghép, ví dụ ONT+CLN); ở mục 1 chỉ xổ các loại đất có giá trong danh mục của dự án.
- **Cỡ giao diện** (màn hình độ phân giải khác nhau): nút **A− / 100% / A+** ở góc dưới cửa sổ chính, hoặc **Ctrl + con lăn chuột**,
  **Ctrl + "+" / Ctrl + "-"**, **Ctrl + 0** về 100% (80% – 160%, phần mềm nhớ cỡ đã chọn).
- **Chọn hộ / Hộ trước / Hộ sau** (Ctrl+PgUp, Ctrl+PgDown). Rời hộ còn thay đổi chưa lưu thì phần mềm hỏi Lưu / Không lưu / Hủy.
- **Gợi ý hỗ trợ…** rà mục 4 theo nhân khẩu, di chuyển chỗ ở, DT đất NN đang sử dụng và đề xuất thêm / sửa (đào tạo HT09/HT10, ổn định
  đời sống HT01–HT06 theo tỷ lệ thu hồi, di chuyển tài sản…); đánh dấu khoản muốn áp dụng.
- **Lưu (Ctrl+S)**: ghi hồ sơ và phương án của hộ, có nhật ký. Hộ đã lưu trong phần mềm hiện "Sửa trong phần mềm" ở cột Đối chiếu Excel.

Thanh lệnh còn có **Thông tin dự án…** (tên, cấp và tên xã/phường, số phương án…), **Rà soát giá…** (mọi dòng áp giá tương đương, nhập tay, đơn giá khác danh mục; báo cáo đối chiếu có thêm sheet RA_SOAT_GIA), **In / Xuất…** và **Cập nhật mẫu in…** (giai đoạn 3).

**Chọn hộ cần in**: "Các hộ đã lập phương án" chỉ gồm hộ đã được mở soát và **Lưu** (hoặc nhập từ Excel) — phương án phần mềm
tự lập lúc tạo Dự án mới mà chưa soát có trạng thái **"Phương án tự lập - chưa soát"** và nằm ở mục riêng. Danh sách hộ có ô
**Chọn** từng hộ, ô tìm (không cần dấu), nút **Chọn hộ đã lập / Chọn các hộ đang hiện / Bỏ chọn tất cả**; dòng dưới cho biết số hộ,
tổng tiền đang chọn. In hộ tự lập chưa soát thì phần mềm hỏi lại. Tùy chọn: **gộp PDF** phương án chi tiết thành một file
(PHUONG_AN_CHI_TIET.pdf), **số bản** khi in ra máy in, mở thư mục khi xong.

**In / xuất hàng loạt** (hàng trăm hộ, Excel + PDF hoặc máy in): hộp tiến trình hiện từng bước (tạo file Excel x/n, Excel đang
xuất PDF x/n) — phần mềm vẫn phản hồi, bấm **Dừng** để ngừng sau file đang làm (các file đã xong được giữ). Một file Excel không
xuất xong trong 3 phút (Excel kẹt hộp thoại ẩn, máy in lỗi) thì phần mềm tự dừng, tắt Excel chạy ngầm và báo file bị kẹt.

## Cây trồng theo chu vi, mật độ; tài sản theo ranh thu hồi

Trong màn hình Lập phương án hộ:

- **Cây theo đường kính / chu vi**: nhập ở hàng nhập nhanh của thẻ Cây trồng (xem trên). Danh sách chọn ghi kèm quy cách theo chu vi
  (ví dụ d >15-18 cm = chu vi > 47,1 đến ≤ 56,5 cm).
- **Thẻ Cây trồng → Tính mật độ…** (chọn dòng cây tính theo cây): nhập diện tích trồng (mặc định DT đất nông nghiệp thu hồi của hộ),
  số cây kiểm đếm; mật độ quy chuẩn lấy từ ghi chú bộ đơn giá ("Mật độ 210 cây/ha") hoặc quy chuẩn riêng của dự án. Hộp hiện: mật độ
  quy định (cây/ha, m²/cây), số cây tối đa trên diện tích trồng, **diện tích cần cho số cây kiểm đếm**, có **vượt mật độ** không, vượt
  bao nhiêu cây (thiếu bao nhiêu m²), bao nhiêu cây **đảm bảo mật độ**. Áp dụng: dòng hiện tại = số cây đảm bảo mật độ (100%), thêm dòng
  **vượt mật độ** ngay dưới với tỷ lệ bồi thường theo quy chuẩn (mặc định 0% – đặt theo quy định áp dụng cho dự án).
- **Thẻ Nhà, công trình → Tách theo ranh thu hồi…** (chọn dòng tài sản): nhập tổng diện tích / khối lượng xây dựng và phần nằm trong
  ranh thu hồi. Phần trong ranh tính 100%; phần ngoài ranh tính theo tỷ lệ (mặc định 0%), hoặc tính toàn bộ nếu đánh dấu "ảnh hưởng kết
  cấu, không sử dụng được". Mô tả trong / ngoài ranh ghi ở cột Quy cách để làm cơ sở lập phương án.
- **Quy chuẩn cây, tài sản…** (thanh lệnh): bảng mật độ mọi loại cây (sửa mật độ, tỷ lệ bồi thường cây ngoài mật độ, căn cứ – lưu trong
  file dự án) và tỷ lệ mặc định phần ngoài mật độ / ngoài ranh thu hồi của dự án.

## Đợt trình, thư mục hồ sơ, theo dõi tiến độ

- **Đợt trình…**: tạo các đợt (Đợt 1, Đợt 2…), xếp hộ vào đợt (chọn hộ trong danh sách chính rồi "Đưa … hộ đang chọn vào đợt",
  hoặc "Đưa các hộ chưa xếp đợt vào đợt"), chọn **thư mục hồ sơ dự án**.
  - **Sửa đợt…** (hoặc bấm đúp dòng đợt): văn bản trình (**Tờ trình** / **Văn bản**, số, ngày trình), **số / ngày phương án
    tổng**, ghi chú. Số phương án tổng tự in vào bảng tổng hợp: "(Đính kèm Phương án số **30**/… ngày **09** tháng **10** năm …)".
  - **Số PA chi tiết** từng hộ: nút **Đánh số PA chi tiết…** (số bắt đầu, số chữ số 01/02…, ngày, chỉ hộ chưa có số) hoặc bấm đúp
    ô "Số PA chi tiết" / "Ngày PA" để sửa. Số in vào "Số: …/ký hiệu" và ngày của phương án chi tiết; hộ được đưa vào quyết định
    phê duyệt mang theo số này.
  - **Mẫu văn bản trình**: Tờ trình / văn bản trình (Word .docx/.doc, Excel .xlsx/.xls, PDF) và Phương án tổng (Word, PDF): **Thêm
    mẫu…** (PDF: Word mở ra và hỏi chuyển thành văn bản sửa được - bấm OK), **Sửa mẫu** (mở bằng Word / Excel), **Mẫu mặc định**
    (bỏ mẫu riêng). Trong mẫu gõ chỗ trống trong ngoặc nhọn, ví dụ `{so_to_trinh}`, `{tong_tien_chu}`; dòng bảng có `{ho.ho_ten}`,
    `{ho.tong_tien}`… được nhân thành mỗi hộ một dòng - danh sách đầy đủ ở nút **Chỗ trống dùng trong mẫu…**.
  - **Xuất hồ sơ đợt** (chọn: phương án chi tiết, bảng tổng hợp, tờ trình, phương án tổng - từng loại hoặc **Chọn tất cả**) tạo
    `<thư mục hồ sơ>\Đợt 1 - 25 hộ\PA CHI TIET\` (phương án chi tiết từng hộ `PA_<STT>_<họ tên>.xlsx`) và `...\PA TONG\`
    (`TO_TRINH.docx`, `PHUONG_AN_TONG.docx`, `BANG_TONG_HOP.xlsx`), kèm PDF nếu chọn (Excel / Word xuất); xuất lại khi số hộ đổi
    thì thư mục cũ đổi tên theo số hộ mới. **Xuất tất cả các đợt** làm lần lượt mọi đợt.
- **In / Xuất…**: ô **Đợt trình** - chọn một đợt thì đánh dấu sẵn các hộ của đợt và mọi mẫu (số tờ trình, số phương án tổng lấy
  theo đợt); bản in chọn từng mẫu hoặc **Chọn tất cả mẫu (in đồng loạt)**; **Lưu vào thư mục** chọn được đường dẫn, mặc định lưu
  thành 2 thư mục **PA CHI TIET** / **PA TONG**.
- **Lưu dự án thành…**: chép file `.pabt` đang mở sang chỗ khác (mặc định thư mục hồ sơ dự án) rồi làm việc tiếp trên file mới – để
  file dự án và các thư mục đợt trình nằm cùng một chỗ.
- **Trạng thái hộ…** (chọn một hoặc nhiều hộ): đã phê duyệt (số, ngày quyết định, số tiền, file quyết định), đã chi trả (ngày, số
  tiền), đã bàn giao mặt bằng (ngày), ghi chú theo dõi. Chọn nhiều hộ: ô để trống giữ nguyên; "Số tiền = tổng phương án của từng hộ"
  điền số tiền riêng cho từng hộ.
- **Nhập quyết định…**: chọn file quyết định phê duyệt / danh sách chi trả / biên bản bàn giao (Excel, Word, PDF có chữ, CSV). Phần
  mềm tự đọc số và ngày quyết định, khớp từng dòng với hộ theo mã hộ, số CCCD hoặc họ tên (bỏ "Ông/Bà", không phân biệt hoa thường,
  dấu), lấy số tiền và tô đỏ dòng có số tiền khác tổng phương án; tên trùng nhiều hộ được liệt kê để chọn tay. Bấm cập nhật để ghi
  trạng thái cho các hộ đã đánh dấu; có thể chép file vào `<thư mục hồ sơ>\Quyết định phê duyệt` (Chi trả, Bàn giao mặt bằng).
- **Báo cáo tổng hợp…**: xuất Excel các hộ **đang hiện theo bộ lọc** (đợt, trạng thái, từ khóa): sheet danh sách (mục 1-5, tổng,
  phê duyệt, chi trả, bàn giao, ghi chú theo dõi, tổng cộng và bằng chữ) và sheet tổng hợp theo đợt (số hộ, tổng tiền, số hộ / số
  tiền đã phê duyệt, đã chi, đã bàn giao).

## Kiểm tra lỗi trước khi trình

**Kiểm tra lỗi…** rà toàn dự án, chia **Lỗi** (tô đỏ) và **Cảnh báo**, lọc theo nhóm: thông tin dự án (tên, xã, người ký…),
thông tin hộ (họ tên trống / có số / khoảng trắng thừa / chưa viết hoa, địa chỉ trống, CCCD sai số chữ số hoặc trùng giữa các hộ,
ngày cấp sai, trùng họ tên + địa chỉ), **font chữ** (ký tự lạ do gõ TCVN3 / VNI, chữ tổ hợp), thửa đất (DT bằng 0, thiếu số thửa /
tờ, loại đất ngoài danh mục, cùng thửa ở nhiều hộ), phương án (hộ có thửa chưa lập PA, dòng chưa có số lượng / đơn giá, thiếu căn cứ
giá, DT ở mục 1 khác kiểm kê, nhà – công trình vượt DT thu hồi, cây tính 100% vượt mật độ), đơn giá (khác danh mục hiện hành, áp giá
tương đương / nhập tay), số liệu (thành tiền khác file Excel, số âm) và tiến độ (chi trả khi chưa phê duyệt, số tiền phê duyệt khác
tổng phương án…). Nhấp đúp dòng để mở phương án của hộ; **Sửa tự động lỗi trình bày** chuẩn hóa khoảng trắng, chữ hoa họ tên (chỉ
tên người, không đụng tên có mô tả kèm theo), chữ tổ hợp, số CCCD; **Xuất Excel** lưu danh sách lỗi.

## Dự toán, áp giá dự thảo

**Dự toán, áp giá dự thảo…** (dùng được cả khi chưa mở dự án): bảng dự toán theo mục 1 đất, 2 nhà – công trình, 3 cây trồng, 4 hỗ
trợ, 5 thưởng, 6 chi phí khác (tính % trên tổng mục 1-5: mặc định 2,5% chi phí thực hiện công tác bồi thường, 10% phí dự phòng –
sửa theo quy định).

- **Xuất Bảng khái toán (Excel / PDF)…**: theo mẫu của đơn vị – tên đơn vị, quốc hiệu, "…, ngày … tháng … năm …", BẢNG KHÁI TOÁN,
  Dự án, Địa chỉ (ô **Địa chỉ** ở đầu màn hình), TỔNG DỰ ƯỚC KINH PHÍ; bảng STT / Tên tài sản / ĐVT / Số lượng / Đơn giá dự kiến bồi
  thường / Tỷ lệ (%) / Thành tiền / Ghi chú chia nhóm I Bồi thường về đất, II Nhà và công trình xây dựng, III Cây trồng, IV Các chính
  sách hỗ trợ (V Thưởng nếu có); dưới cùng Tổng cộng, chi phí thực hiện công tác bồi thường %, phí dự phòng %, TỔNG DỰ ƯỚC KINH PHÍ
  và số tiền bằng chữ. PDF xuất qua Microsoft Excel.

- **Lấy khối lượng**: từ dự án đang mở, từ file `.pabt` khác, từ **file PABT Excel của dự án tương tự** (nhập tạm, gom các dòng phương
  án cùng hạng mục, cùng đơn giá) hoặc từ **danh sách thô** (gom diện tích theo loại đất + vị trí).
- **Áp đơn giá hiện hành**: thay đơn giá các dòng có mã theo bộ đơn giá đang dùng (áp giá dự thảo cho dự án tương tự).
  **Tra giá đất NQ 28…** lấy giá đất theo địa bàn, tuyến đường, vị trí. **Thêm từ danh mục…**, **Thêm dòng**, sửa trực tiếp khối
  lượng, đơn giá, hệ số.
- **Lưu dự toán…** (file `.pabtdt`), **Mở dự toán…**, **Xuất bảng chi tiết (Excel)…** (có tổng cộng và số tiền bằng chữ). Thành tiền làm tròn theo
  từng dòng dự toán nên có thể chênh vài nghìn đồng so với tổng các phương án chi tiết.

## Nhập file Excel

**Nhập file Excel…** tự nhận loại file:

- **File PABT `.xlsm`** (có các sheet DB_HO, DB_THUA…): nhập toàn bộ hồ sơ, phương án, danh mục; tạo file `.pabt` mới.
- **File Excel bất kỳ** có danh sách hộ, thửa. Phần mềm tự:
  - tìm sheet và dòng tiêu đề (kể cả tên bảng phía trên, tiêu đề 2 dòng có ô gộp, dòng đánh số cột (1), (2)…);
  - nhận cột theo tên: **họ tên** (Họ và tên, Tên chủ sử dụng…), **địa chỉ** (Địa chỉ, Thường trú, Nơi cư trú…), **tờ**, **thửa**,
    **diện tích thu hồi**, **loại đất** (Loại đất, Mục đích sử dụng…), và nếu có: CCCD, ngày cấp, nơi cấp, điện thoại, DT bản đồ, nguồn gốc, vị trí, ghi chú;
  - bỏ dòng trống, dòng nhóm (I, II, Ấp…), dòng Tổng cộng; họ tên để trống / gộp ô thì tính cho hộ phía trên;
  - gom các dòng cùng CCCD (hoặc cùng họ tên + địa chỉ) thành một hộ, mỗi dòng là một thửa; đọc số kiểu `1.070,5`, `39,4 m2`;
  - báo các điểm cần xem lại: thiếu diện tích / loại đất / số thửa, cùng tên khác địa chỉ, một thửa có nhiều hộ.

  Lưu vào file `.pabt` **đã có**: phần mềm hỏi rồi **xóa trắng** hồ sơ cũ (hộ, thửa, phương án, thông tin dự án, nhật ký) và **giữ** danh mục đơn giá, tham số, biểu thưởng của file.
  Lưu thành file **mới**: danh mục được chép từ dự án đang mở. Tên dự án lấy từ tên bảng (dòng có chữ "dự án"), không có thì lấy tên file; cấp và tên xã / phường lấy từ tên dự án. Sửa lại ở **Thông tin dự án…**.

Không cần mở cửa sổ: kéo file Excel thả vào **NHAP_EXCEL.bat**.

### Nhập phương án chi tiết đã lập bằng Excel (mỗi sheet một hộ)

Dùng khi đã có file Excel áp giá kiểu bản in **PHƯƠNG ÁN CHI TIẾT** (mỗi sheet một hộ: Họ và tên, Số CCCD, Địa chỉ, Số điện
thoại; "II. Thông tin nguồn gốc đất"; bảng STT / Tên tài sản / ĐVT / Số lượng / Đơn giá / Tỷ lệ (%) / Thành tiền / Ghi chú theo
mục 1 đất - 2 nhà, công trình - 3 cây trồng - 4 hỗ trợ - 5 thưởng; dòng TỔNG CỘNG; dòng "IV. Phương án tái định cư").

1. Mở dự án cần nhập vào (hoặc không mở dự án nào để tạo **dự án mới** với bộ đơn giá tích hợp; tên dự án, đơn vị, ký hiệu số,
   xã / phường, năm lấy từ đầu trang phương án).
2. **Nhập phương án chi tiết…** (nhóm Dự án; hoặc **Nhập file Excel…** – phần mềm tự nhận loại file), chọn file.
3. Bảng xem trước liệt kê từng sheet: họ tên, số thửa, số dòng, tổng tiền theo file. Sheet mẫu ("mẫu…", "KIEMTRA"), sheet không
   có họ tên, sheet còn ô lỗi `#N/A` được bỏ chọn sẵn. Hộ đã có trong dự án (cùng CCCD; không có CCCD thì cùng họ tên): chọn **bỏ
   qua**, **thay** (thay hồ sơ, thửa, phương án; giữ mã hộ, đợt trình, quyết định) hoặc **vẫn thêm thành hộ mới**.
4. **Thực hiện nhập**. Phần mềm báo số hộ, thửa, dòng đã nhập và các điểm cần xem lại.

Cách chuyển số liệu:
- **Hộ**: họ tên (cả câu "… là chủ sở hữu tài sản…" như file), CCCD tách số / ngày cấp / nơi cấp, nguồn gốc đất ghi vào các thửa.
- **Mục 1**: mỗi dòng "Thửa đất số …, tờ bản đồ số …, loại đất …" thành một thửa (DT thu hồi = Số lượng). Có đơn giá đất thì lập
  dòng bồi thường đất; không có (đất không bồi thường) thì chỉ lập thửa, ghi chú của dòng đất lưu vào **Pháp lý** của hộ và in ở
  cột Ghi chú dòng thửa đầu.
- **Mục 2, 3**: dòng trùng tên **và** đơn giá với bộ đơn giá → dòng danh mục (có mã); trùng tên khác giá → **nhập tay**, Căn cứ giá
  ghi giá danh mục; không có trong danh mục → nhập tay theo đơn giá của file. File chưa có đơn giá mà tên khớp bộ đơn giá → lấy
  giá danh mục (báo để soát lại, tỷ lệ trống tính 100%). Dòng con "-" dưới một dòng: nhập từng dòng con.
- **Mục 4**: nhập nguyên tên, số lượng, đơn giá, ghi chú (dòng "tính bổ sung sau" giữ thành tiền 0). **Mục 5** (thưởng) phần mềm tự tính.
- Thành tiền và tổng từng mục của file được giữ để đối chiếu: **Xuất báo cáo đối chiếu…** cho biết hộ nào phần mềm tính khác file.
- Hộ nhập vào có trạng thái "Đã lập phương án (nhập từ Excel chi tiết)"; mở **Lập phương án hộ** để soát, sửa như bình thường.
  Nhập nhầm: **↶ Hoàn tác** (trên băng tiêu đề, hoặc Ctrl+Z) khi đang mở dự án.

Dòng lệnh: `python chay.py nhap-chi-tiet <file.xlsm> [<file.pabt>] [--trung bo_qua|thay|them]` (in kết quả đối chiếu).

## Cập nhật phần mềm bằng gói cập nhật (.pabtcn)

Sửa lỗi hoặc thêm tính năng **không phải cài lại**: người phát triển gửi một file nhỏ `PABT_CapNhat_<phiên bản>.pabtcn`
(vài trăm KB). Máy dùng **bấm đúp file** đó (hoặc nút **Cập nhật phần mềm** ở góc dưới bên phải → **Cập nhật từ file…**) → phần mềm kiểm tra
gói (đúng gói PABT, không hỏng, mới hơn bản đang chạy, hợp với bản cài) → cài → hỏi **mở lại phần mềm** để dùng bản mới.
Phiên bản đang chạy hiện trên băng tiêu đề và ở **Giới thiệu**.

- Bản cập nhật lưu ở `%APPDATA%\PABT\cap_nhat`; dữ liệu dự án, bộ đơn giá đã cập nhật, mẫu in không bị đụng tới.
- Bản cập nhật lỗi (không nạp được, hoặc 2 lần mở liền không tới cửa sổ chính) **tự tắt**, phần mềm chạy bản cài gốc; lý do hiện
  trong hộp thoại Cập nhật phần mềm. **Gỡ bản cập nhật** để quay về bản gốc.
- Cài bộ cài đầy đủ mới hơn thì bản cập nhật cũ tự bỏ qua. Gói chỉ thay mã PABT; thay đổi cần thư viện mới (Python, Qt…) phải
  phát hành bộ cài mới. Chỉ cài gói từ người phát triển (gói chứa mã chương trình).

**Người phát triển tạo gói:** sửa mã, chạy kiểm thử, tăng `__version__` trong `pabt/__init__.py`, rồi bấm đúp **DUNG_CAP_NHAT.bat**
(hoặc `.venv\Scripts\python tao_cap_nhat.py --mo-ta "Sửa lỗi …"`) → `bo_cai\PABT_CapNhat_<phiên bản>.pabtcn`. Gói dùng cho bản
cài từ 0.8.0 trở lên (cả bản Win 10/11 và Win 7/8) (`--toi-thieu` để đổi).

## Cài đặt

**Máy dùng (không cần Python):** có **hai bộ cài**, chọn theo Windows của máy (bộ cài tự kiểm tra, cài nhầm sẽ báo):

| Máy | Bộ cài | Nền chạy | Bộ VC++ kèm theo |
|---|---|---|---|
| **Windows 10 / 11** 64-bit | `PABT_CaiDat_0.9.12_Win10-11.exe` | Python 3.14 + Qt6, 64-bit | x64 14.44 |
| **Windows 7 SP1 / 8 / 8.1** – máy **32-bit hoặc 64-bit**; cả Windows 10 **32-bit** | `PABT_CaiDat_0.9.12_Win7-8.exe` | Python 3.8 + Qt5, chương trình 32-bit | x86 14.29 (bản cuối cài được trên Win 7) |

Chép **một file** bộ cài phù hợp sang máy, bấm đúp → cửa sổ cài đặt (chọn thư mục, biểu tượng Desktop, liên kết file `.pabt`) →
**Cài đặt** → thanh tiến trình → bộ cài tự kiểm tra phần mềm trên máy đó (giao diện, đọc PDF, bộ đơn giá, mẫu in, bảng giá đất) →
**Mở PABT**. Nhật ký cài: `%TEMP%\pabt_cai_dat.log`. Còn trống ≥ 300 MB. Microsoft Visual C++ Redistributable (x64): máy chưa có
(hoặc bản cũ hơn) thì cài kèm (Windows hỏi quyền quản trị một lần). **Không cần cài .NET, Python hay Office** (in PDF qua Excel thì
cần Excel). Windows 7 dùng PowerShell 2.0 và .NET 3.5 có sẵn; cần **Service Pack 1** và bản cập nhật Windows thường kỳ
(KB2533623, KB2999226 – máy cập nhật Windows Update đầy đủ là có). Bản Win 7/8 là chương trình 32-bit nên chạy được cả trên
Windows 32-bit lẫn 64-bit (máy 64-bit vẫn chạy bình thường).
Hai bản có cùng chức năng; bản Win 7/8 đọc PDF đơn giá bằng `pypdf` thay cho QtPdf. Cùng một **gói cập nhật `.pabtcn`** dùng
được cho cả hai bản.

Hoặc giải nén `PABT_ChayNgay_0.9.12_Win10-11.zip` / `_Win7-8.zip` vào một thư mục rồi chạy `PABT.exe`, không cần cài. Bộ cài cài cho
người dùng hiện tại (không cần quyền quản trị) vào `%LOCALAPPDATA%\Programs\PABT`, tạo biểu tượng ở menu Start / Desktop và cho mở
file `.pabt` bằng nhấp đúp. Gỡ bằng Settings → Apps (Win 7: Control Panel → Programs) – file dự án `.pabt` được giữ. Cài im lặng:
`PABT_CaiDat_<phiên bản>_<bản>.exe /Q`. Mẫu in sửa bằng **Cập nhật mẫu in…** được lưu ở `%APPDATA%\PABT\mau_in`.

**Máy phát triển (có mã nguồn):**

1. Cài Python 3.12+ từ https://www.python.org/downloads/ – khi cài, đánh dấu **Add python.exe to PATH**.
2. Bấm đúp **CAI_DAT.bat**: tạo môi trường riêng `.venv`, cài `openpyxl`, `PySide6`, chạy bộ kiểm thử.
3. Bấm đúp **CHAY_PABT.bat** để mở cửa sổ.
4. **CAI_DAT_PHAT_HANH.bat** (một lần, để dựng bản Win 7/8): cần Python 3.8.10 **32-bit**
   (https://www.python.org/ftp/python/3.8.10/python-3.8.10.exe, cài cho người dùng hiện tại vào `Python38-32`); tạo môi trường
   `%LOCALAPPDATA%\PABT_dev\venv38_32` (đường dẫn không dấu: Python 3.8 / Qt5 / PyInstaller 5 lỗi với thư mục có chữ Việt), cài
   `requirements38.txt` (PySide2 5.15, openpyxl, pypdf, PyInstaller 5) và chạy kiểm thử bằng Qt5.
5. **DUNG_EXE.bat**: dựng bản Win 10/11 chạy không cần Python ở `dist\PABT`.
6. **DUNG_BO_CAI.bat**: dựng **cả hai bản** – `dist\PABT` (PyInstaller 6, Python 3.14 + Qt6) và `dist\PABT_Win7`
   (`bo_cai_win\dung_exe38.py`: chép mã sang thư mục tạm không dấu, PyInstaller 5), rút gọn từng bản (`bo_cai_win\rut_gon.py`: bỏ thư
   viện Qt không dùng, rồi chạy `PABT.exe tu-kiem`, dừng nếu không đạt), rồi `bo_cai_win\dung_bo_cai_win.py` đóng gói (IExpress có sẵn
   trong Windows, kịch bản `cai_dat.ps1` / `go_cai_dat.ps1` chạy được PowerShell 2.0) thành `bo_cai\PABT_CaiDat_<phiên bản>_Win10-11.exe`
   (kèm `vc_redist.x64.exe` 14.44), `..._Win7-8.exe` (32-bit, vỏ IExpress 32-bit từ SysWOW64, kèm `vc_redist_win7.x86.exe` 14.29)
   và hai bản chạy ngay `.zip`.
   Mã nguồn dùng chung phải chạy được cả Python 3.8 + Qt5: `from __future__ import annotations` ở đầu mỗi file; không dùng tính năng
   Python 3.9+ khi chạy; Qt5 được nạp dưới tên PySide6 bởi `pabt/__init__.py` (`_qt5_lam_qt6`). Kiểm thử cả hai:
   `.venv\Scripts\python -m unittest …` và `%LOCALAPPDATA%\PABT_dev\venv38_32\Scripts\python -m unittest …`.
   Không dùng Inno Setup 6.5+ nữa: bộ cài Inno báo "Setup was unable to create the directory …\Temp\is-….tmp, Error 2" trên
   Windows 11 bản mới.

## Lệnh

```
python chay.py                                  mở cửa sổ (python chay.py <file.pabt>: mở luôn dự án)
python chay.py nhap <file.xlsx|xlsm> [<file.pabt>] [--ten "Tên dự án"] [--danh-muc <dự án cũ.pabt>]
python chay.py nhap-chi-tiet <file.xlsm> [<file.pabt>] [--trung bo_qua|thay|them]   phương án chi tiết (mỗi sheet một hộ)
python chay.py doi-chieu <file.pabt>            tính lại, đối chiếu file dự án đã nhập
python -m unittest discover -s tests -t .       chạy bộ kiểm thử
```

Hoặc bấm đúp **KIEM_THU.bat**: chạy 123 bài kiểm thử (cả màn hình, chế độ ẩn), kết quả ở `KIEM_THU_log.txt`.

### Kiểm tra toàn bộ khi có lỗi: `KIEM_TRA_TOAN_BO.bat`

Bấm đúp để kiểm tra mọi phần, khoảng 2 phút; cuối cùng có bảng tóm tắt **ĐẠT / LỖI / CẢNH BÁO / BỎ QUA**. Kết quả lưu ở
`ket_qua_kiem_tra\KiemTra_<ngày giờ>.txt` (gửi file này khi cần nhờ xử lý lỗi).

| Bước | Kiểm tra |
|---|---|
| 1 | Môi trường máy: Windows, `.venv`, `venv38_32`, ổ đĩa còn trống |
| 2-3 | Toàn bộ kiểm thử tự động, bản Win10/11 (Qt6) và Win7/8 32-bit (Qt5) |
| 4 | Chạy thử thật với file mẫu `PABT_CHUAN*.xlsm` (ở thư mục cha), trên **bản sao**: nhập → lập phương án → đối chiếu (phải KHỚP 100%) |
| 5 | Bản dựng `dist\PABT`, `dist\PABT_Win7` tự kiểm tra |
| 6 | `bo_cai\`: đủ 2 bộ cài, 2 bản chạy ngay, gói cập nhật đúng phiên bản; file zip nguyên vẹn, **không chứa dữ liệu thật**; gói `.pabtcn` đúng mã kiểm tra |
| 7 | Bản đã cài trên máy (`PABT.exe tu-kiem`), có đúng phiên bản mới nhất không |
| 8 | Bản cập nhật đang dùng có bị tự tắt vì lỗi không (`LOI.txt`) |
| 9 | Máy chủ LAN (nếu có thiết lập): kết nối, đọc tài khoản, dự án |

Tùy chọn: `KIEM_TRA_TOAN_BO.bat --nhanh` (bỏ bước 3 và 5, khoảng 1 phút); `--cai-thu` (thêm bước cài im lặng bộ cài mới nhất lên máy
rồi tự kiểm tra bản vừa cài); `--mau <file.xlsm>` (dùng file mẫu khác). Không file dữ liệu nào bị sửa.

Bộ kiểm thử so khớp với file Excel thật nếu đặt file ở `du_lieu\PABT.xlsm` (hoặc biến môi trường `PABT_EXCEL`); không có file thì các bài so khớp tự bỏ qua.

## Cấu trúc

| File | Nội dung |
|---|---|
| `pabt/schema.sql` | Cấu trúc CSDL: du_an, ho, thua, ct_dat (mục 1), ct_khoan (mục 2–4), danh mục, tham số, biểu thưởng, văn bản căn cứ, tổng Excel, nhật ký |
| `pabt/csdl.py` | Mở / tạo file `.pabt` (không dùng WAL để an toàn khi file nằm trong thư mục Google Drive), mở chỉ xem, khóa danh mục (trigger), nhật ký |
| `pabt/khoa.py` | Khóa file dự án khi nhiều máy cùng mở (`.pabt.khoa`, làm mới mỗi phút, hết hạn sau 3 phút) |
| `pabt/nhap_excel.py` | Đọc file PABT Excel theo tên tiêu đề cột; chặn khi mã hộ trùng, thửa mồ côi, dòng phương án trỏ tới thửa/hộ không có; ghi trong một giao dịch |
| `pabt/nhap_tho.py` | Nhập danh sách hộ, thửa từ file Excel bất kỳ: tự tìm tiêu đề, nhận cột theo tên, gom hộ; xóa trắng hồ sơ, giữ danh mục |
| `pabt/don_gia.py`, `pabt/bo_don_gia.sqlite`, `tao_bo_don_gia.py` | Bộ đơn giá tích hợp: đọc, áp vào dự án, cập nhật từ file / Internet; script đóng gói |
| `pabt/du_an_moi.py`, `pabt/man_hinh_du_an_moi.py` | Dự án mới từ dữ liệu thô: gom hộ, bảng giá đất, tự lập phương án, xuất 2 bảng in |
| `pabt/man_hinh_don_gia.py` | Màn hình Bộ đơn giá (chỉ đọc, cập nhật, tra cứu văn bản) |
| `pabt/gia_dat_nq28.py`, `pabt/bang_gia_nq28.json`, `pabt/man_hinh_gia_dat.py` | Bảng giá đất NQ 28/2025 (4 địa bàn): tra cứu, điền giá, xuất Excel |
| `tao_bieu_tuong.py`, `pabt/bieu_tuong.ico` | Biểu tượng phần mềm / bộ cài (đường cao tốc, mặt bằng GPMB, cột mốc) |
| `pabt/nhap_don_gia.py`, `pabt/man_hinh_nhap_don_gia.py` | Cập nhật bộ đơn giá từ Excel / Word / PDF / CSV hoặc trang web: đọc bảng, so khớp, xem trước, tạo phiên bản mới |
| `pabt/man_hinh_quet_web.py` | Quét trang web / Công báo Đồng Nai: tìm văn bản đơn giá, chính sách; tải, phân tích, áp dụng theo ngày ban hành |
| `pabt/ho_so.py` | Hồ sơ kiểm kê: thêm / sửa / xóa hộ, thửa; gộp hộ; chuyển thửa |
| `pabt/nghiep_vu.py` | Quy tắc tính: thành tiền, làm tròn như ROUND của Excel, thưởng theo tổng mục 1–4, hỗ trợ ổn định đời sống, gợi ý HT09/HT10 theo hạn mức; kiểm tra quy tắc từng hộ |
| `pabt/doi_chieu.py` | So từng hộ, từng dòng với Excel; xuất báo cáo `.xlsx` (TONG_HO, DONG_LECH, CAN_XEM_LAI) |
| `pabt/lap_pa.py` | Soạn phương án một hộ: thêm / sửa / xóa dòng, danh mục, giá tương đương, gợi ý hỗ trợ, lưu một giao dịch; thông tin dự án; rà soát giá |
| `pabt/in_an.py` | Bản in theo mẫu `mau_in\IN_CHITIET.xlsx`, `IN_BANGTONGHOP.xlsx`; xuất PDF / in qua Excel |
| `pabt/giao_dien.py` | Màu giao diện: nút theo nhóm chức năng, tiêu đề bảng, nhãn thuộc tính; nút chuẩn tiếng Việt |
| `pabt/app.py`, `pabt/man_hinh.py`, `pabt/man_hinh_ho_so.py` | Cửa sổ chính; màn hình Lập phương án hộ và các hộp chọn danh mục, gợi ý, dự án, rà soát, in; màn hình Hồ sơ hộ |
| `pabt/quan_ly.py`, `pabt/man_hinh_quan_ly.py` | Đợt trình, thư mục hồ sơ, lưu dự án thành, trạng thái phê duyệt / chi trả / bàn giao, nhập quyết định từ file, báo cáo tổng hợp; màn hình Đợt trình, Trạng thái hộ, Nhập quyết định, Kiểm tra lỗi |
| `pabt/kiem_loi.py` | Kiểm tra lỗi trước khi trình (thông tin hộ, font chữ, thửa, phương án, đơn giá, tiến độ), sửa tự động lỗi trình bày |
| `pabt/du_toan.py`, `pabt/man_hinh_du_toan.py` | Dự toán / áp giá dự thảo: gom khối lượng, áp đơn giá hiện hành, tra giá đất NQ 28, file `.pabtdt`, xuất Excel |
| `pabt/cay_trong.py`, `pabt/man_hinh_cay.py` | Cây theo chu vi (quy đổi đường kính), mật độ cây trồng, tài sản trong / ngoài ranh thu hồi, quy chuẩn của dự án |
| `DUNG_BO_CAI.bat`, `bo_cai_win/` | Bộ cài IExpress (`cai_dat.ps1` cửa sổ cài, `rut_gon.py`, `vc_redist.x64.exe`) |
| `tests/` | 113 bài kiểm thử (unittest), có các bài chạy màn hình thật (chế độ ẩn) |

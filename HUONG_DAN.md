# Phần mềm LARC – lập phương án bồi thường, hỗ trợ (phiên bản 1.0.27 – Bản Tiêu chuẩn · Sử dụng nội bộ)

> **1.0.27**: **bản thương mại** - phần mềm không còn ghi sẵn tên cơ quan nào. Nhập tên tổ chức, cơ quan cấp trên, địa chỉ ở Cài đặt → Cấu hình
> nghiệp vụ → Cơ quan (ô còn trống có chữ gợi ý mờ), hoặc nhập **gói .pabtcfg** do nhà cung cấp cấu hình sẵn; tên phần mềm ở dòng 1 băng tiêu đề
> đổi được ở cùng thẻ. Căn cứ pháp lý, mốc thời hạn là chỗ trống nhắc điền. Cửa sổ cài đặt được thiết kế lại.
>
> **1.0.25**: đổi tên tổ chức trong Cấu hình nghiệp vụ → Cơ quan hiện ngay trên băng tiêu đề.
>
> **1.0.24**: sửa lỗi 1.0.23 (cửa sổ trống nhấp nháy khi mở hộp Xuất hồ sơ & Bản in).
>
> **1.0.23**: hộp **Xuất hồ sơ & Bản in** gọn hơn (bảng hộ giãn cao, sắp xếp theo cột, thêm cột Đợt / Địa chỉ, bộ đếm dưới bảng, bỏ nút trùng, nhớ
> lựa chọn lần trước); xem trước có nút **Vừa ngang**; **Cài đặt → Cấu hình nghiệp vụ → Kiểm tra & bản in**: nhập **lề trang in bảng tổng hợp** (cm).
>
> **1.0.22**: **Xuất hồ sơ & Bản in → Xem trước gộp các hộ đã chọn**: xem phương án chi tiết của nhiều hộ (đánh dấu cột Chọn, tối đa 30 hộ
> một lần) trên cùng một bản PDF; ô **Nhảy tới hộ** trên thanh xem trước, **In…** in cả bản.
>
> **1.0.21**: tiêu đề mục I phương án chi tiết theo chủ sử dụng (**"I. Thông tin về tổ chức"** / **"I. Thông tin về hộ gia đình, cá nhân"**);
> chữ ký dịch sang trái cho cân lề; đường kẻ dưới tên dự án gần chữ; đường kẻ dưới **CHI NHÁNH** ngắn hơn chữ 1 cm; **DỰ ÁN** in hoa khi tên
> dự án in hoa; bảng tổng hợp có dòng **CHI NHÁNH …** dưới tên cơ quan. Lề bảng tổng hợp A3: trái 2,0 / phải 1,0 / trên 1,5 / dưới 1,5 cm
> (đổi trong hồ sơ địa phương `ban_in.le_trang.tong_hop`).
>
> **1.0.20**: **bảng tổng hợp cũng không còn file mẫu Excel** - bố cục, định dạng và khổ giấy A3 dựng hoàn toàn bằng mã (kết quả in giữ
> nguyên). Phần mềm không còn đọc bất kỳ file mẫu Excel nào; **Quản lý Mẫu in & Bản in** chỉ còn thông số mẫu Word (xuất / nhập / khôi phục).
>
> **1.0.19**: **bỏ hẳn mẫu Excel phương án chi tiết** - mẫu Word nhúng trong phần mềm là mẫu duy nhất (thông số quy cách đổi trong
> **Quản lý Mẫu in & Bản in → Nhập thông số mẫu Word**, không cần bản cập nhật). Máy không có Microsoft Word: PDF / xem trước là bản
> gần đúng dựng bằng Qt **từ chính file Word**, không còn đọc Excel. **Bảng tổng hợp** vẫn là mẫu Excel. Mọi file Excel xuất ra đi qua
> một cổng lưu: chữ do người dùng gõ bắt đầu bằng dấu "=" không còn trở thành công thức (chặn lệnh độc như `=HYPERLINK(...)`).

> **1.0.14**: **phương án chi tiết chỉ còn bản Word (.docx) theo Nghị định 30** - xem trước **F4**, khung xem trước của **Xuất
> hồ sơ & Bản in**, xuất hồ sơ đợt, **Dự án mới** đều dùng bản Word (A4 dọc, lề trái 30 mm, phải 15 mm, trên / dưới 20 mm; cơ quan,
> quốc hiệu 13; nội dung, bảng 14; mục III in tiếp ngay dưới mục II). PDF, in ra máy, gộp PDF lấy từ bản Word; máy không có
> Microsoft Word thì xem trước / PDF là **bản gần đúng** (dựng bằng Qt từ file Word; từ 1.0.19 không còn mẫu Excel chi tiết). **Bảng tổng hợp** vẫn là Excel A3 ngang: hộ nhiều thửa gộp một ô STT, họ
> tên, địa chỉ, tổng cộng, tái định cư, ghi chú; mỗi thửa một dòng.

> **1.0.11**: bảng chọn ô kiểu **Excel** (kéo bôi đen vùng, góc dưới hiện Trung bình · Tổng số đếm · Tổng); thẻ số liệu ghi thêm
> số thửa / diện tích, **Ctrl+Shift+T** mở Thống kê Hộ · Thửa · Diện tích. Bản in chi tiết không còn hở cuối trang 1; bảng tổng hợp A3
> lấp đầy trang; **Xuất hồ sơ & Bản in** có thêm bản **Word (.docx)** phương án chi tiết theo Nghị định 30 (tích sẵn, nhớ lựa
> chọn); chọn thêm **Xuất PDF + Gộp PDF** thì được một file `PHUONG_AN_CHI_TIET.pdf` cho cả đợt. Hộ Word xuất quá 15 giây được bỏ
> qua để lô chạy tiếp; hộ không có PDF từ Word được dựng PDF gần đúng từ bản Excel.

> **1.0.10**: **Dán danh sách tài sản** hiểu kích thước là diện tích - `Nhà tạm 4,7x3,0`, `Nhà tạm 4,7*3,0`, `Nhà tạm 3,7m x 4,3m`,
> `Nhà tạm 3,7 * 4,3` đều thành **m²** (khối lượng = dài × rộng, phép tính hiện ở chú thích ô Số lượng). `Nhà tạm 42m2 (thửa 123)`:
> 42 m², phần trong ngoặc vào Ghi chú. Ba số nhân nhau cần ghi đơn vị (`Bể nước 2x3x1,5 m3`); có cột ĐVT khác (`cây`) thì theo ĐVT đó.

> **1.0.06 - giao diện chuẩn hóa & bản in gọn trang**: thẻ hồ sơ hộ lưới 3 cột, bảng thửa có DT nguyên thửa / còn lại / Giấy
> chứng nhận; **Ctrl+K** tìm nhanh hộ hoặc chức năng; Ctrl+1 Danh sách hộ, Ctrl+2 Khái toán, Ctrl+3 Đơn giá, Ctrl+4 Niêm yết, Ctrl+5
> Tiến độ. Bản in chi tiết tràn vài dòng tự vừa 1 trang A4 (hết trang 2 mồ côi).
>
> **1.0.05 - một hộ nhiều lần lập phương án**: cửa sổ Lập phương án chi tiết có dải **Lần phương án** (lần đầu, bổ sung lần 1, 2…).
> Lần đã có quyết định phê duyệt **tự khóa** (chỉ xem); muốn bổ sung tài sản / chính sách thì bấm **+ Lập phương án bổ sung** - lần
> mới rỗng, các lần trước và quyết định cũ giữ nguyên. Mỗi lần có **Tên, số PA…** riêng; thêm hộ vào quyết định mới tự lấy tiền của
> lần chưa duyệt. Tổng của hộ luôn **cộng dồn** mọi lần (thưởng bàn giao chỉ tính một lần). Bản in lần bổ sung ghi "PHƯƠNG ÁN CHI TIẾT
> BỔ SUNG LẦN k"; Xuất hồ sơ & Bản in chọn **Lần mới nhất** hoặc **Cộng dồn**. Điều chỉnh lần đã duyệt: **Mở khóa sửa…**.

> **1.0.04**: **không còn che số CCCD** (bản dự thảo, chính thức, tờ trình, bảng niêm yết đều in đủ số). Phương án chi tiết: chủ sử
> dụng là tổ chức ghi **Tổ chức:** / **Địa chỉ:**, ẩn dòng CCCD và điện thoại; nguồn gốc đất mỗi đoạn một dòng, căn đều, thụt đầu
> dòng; mục 1 luôn in diện tích (m²) của thửa kể cả khi không tính tiền đất. Bảng tổng hợp: bản dự thảo ghi **(DỰ THẢO)** dưới tên
> đơn vị, ẩn cột Vị trí đất, hộ nhiều thửa mỗi thửa một dòng (lặp STT, họ tên, địa chỉ), số 0 ở dòng hộ hiện "-". **Kiểm tra lỗi**
> không còn báo nhầm hộ chỉ có tài sản trên đất của tổ chức / UBND xã / hộ khác. **Bảng tổng hợp kinh phí** có hai dòng phân bổ 85% /
> 15%. **Mọi bảng**: bấm một ô rồi **Ctrl+C** để chép (nhiều ô dán thẳng vào Excel), **Ctrl+Shift+C** chép cả dòng, chuột phải "Sao
> chép ô". Mới: **Tiếp nhận hồ sơ pháp lý** (menu trái nhóm 1, màn hình chào, **Ctrl+Shift+L**) - dùng được khi chưa có dự án: loại
> chủ đầu tư, căn cứ thu hồi (Điều 78 / 79 / 122 / 127), thời hạn chủ trương và Nghị quyết HĐND, 32 mục hồ sơ (5 nhóm), 10 tiêu chí kỹ
> thuật địa chính, quét bảng kê thửa Excel, tổng hợp có / thiếu / cần bổ sung; xuất **Phiếu tiếp nhận** (.xlsx), **Công văn đề nghị
> bổ sung** (.docx); lưu file `.pabtpl` hoặc vào dự án; nút **Khởi tạo Dự án Mới (.pabt) từ Hồ sơ này →**.

> **1.0.03**: bảng dễ đọc hơn - ô bằng **0** chữ xám nhạt, số tiền cột Tổng / Thành tiền chữ xanh đậm; cột **Trạng thái** danh sách hộ có
> 4 vạch tiến độ + nhãn màu (xanh lá đã bàn giao, xanh ngọc đã chi trả / phê duyệt, xanh dương đã lập, vàng cần xem lại, xám chưa lập);
> cột tỷ lệ % có thanh tỷ trọng; bảng trống có lời hướng dẫn ở giữa. Menu trái luôn sáng đúng mục đang xem (cả Lập phương án chi tiết,
> Niêm yết, Đơn giá, So sánh). Danh sách hộ vừa khung (Họ tên, Địa chỉ co giãn). Lập phương án: ô chọn tài sản liền nút ▼; dải tổng ghi
> tên từng mục (hẹp thì viết gọn, **TỔNG CỘNG** luôn đủ số); thẻ Thông tin hộ có dòng cộng số thửa / diện tích thu hồi. **Bảng tổng hợp
> kinh phí** và **Quyết định phê duyệt**: 4 thẻ số liệu đầu trang + dòng cộng chân bảng. **Tiến độ**: dòng cộng giải ngân (đang lọc, tổng
> duyệt, đã nhận, chưa nhận); bộ lọc "Đã bàn giao" và thẻ mặt bằng sạch chỉ tính hộ **có quyết định, đã nhận đủ tiền và có ngày biên bản**
> (như danh sách hộ). **Niêm yết**: thẻ số liệu 2 tầng, tỷ lệ % dấu phẩy. **Khái toán**: thanh nhập một hàng (Full HD 125%), thẻ tổng có
> cơ cấu 6 mục. **Đơn giá**: huy hiệu "Đang lọc: a / b mục". **Đợt trình**: danh sách kiểm tra có huy hiệu Đạt / Xem lại / Thiếu.

> **1.0.02**: mọi cửa sổ và trang làm việc cùng tông **Navy** với màn hình chính. Nút chính (**Lưu**, **Thực hiện**, **Xuất bản hồ sơ đợt
> này**, **Thêm vào bảng**) nền xanh đậm; nút **Xóa** viền đỏ; nút khác nền trắng. Cửa sổ lập phương án: thanh trên cùng gọn, thẻ mục kiểu
> gạch chân, dải tổng cộng dưới đáy; **Xem trước (F4)** đang bật thì nút nền xanh nhạt. Tiến độ chi trả & Bàn giao: thẻ chỉ số đang lọc
> được tô nổi, nút chế độ **Theo hộ / Thửa còn vướng** dạng viên thuốc. Bảng tổng hợp kinh phí tô nổi dòng Cộng, Kinh phí tổ chức thực hiện,
> TỔNG KINH PHÍ; bảng giá đất: cột **Hệ số K** và **Giá × K** in đậm. **Bàn giao mặt bằng**: hộ chưa có quyết định phê duyệt thì hộp
> bàn giao không tích sẵn "Đã bàn giao" (có nhắc); đánh dấu nhầm thì chọn hộ, mở lại hộp, bỏ tích rồi Lưu. **Kiểm tra lỗi** báo hộ đã
> đánh dấu bàn giao mà chưa có quyết định phê duyệt. **Tiến độ tự động**: thanh 4 nấc và các thẻ Đã phê duyệt / Đã chi trả / Đã bàn giao
> tự tính theo thứ tự (có quyết định → nhận đủ tiền → đã tích bàn giao có **ngày biên bản**); đánh dấu thiếu bước / thiếu ngày không tăng
> nấc, ô Trạng thái ghi điểm cần xem lại. Hộp bàn giao không điền sẵn ngày; file scan biên bản không bắt buộc, một file dùng chung cho
> nhiều hộ. Cửa sổ lập phương án: **biểu tượng thùng rác** ở cột cuối mỗi dòng (bấm là xóa dòng đó; phím Delete vẫn dùng được).
> **Bản đồ thửa đất** ở menu **Dữ liệu**.

> **1.0.01**: giao diện tông **Navy**: menu trái gọn (nút Thu gọn menu ở hàng riêng), tiêu đề bảng nền xanh đậm, 6 thẻ số liệu có
> **tỷ lệ %**, hàng lọc một dòng ("Đợt: Tất cả", "Trạng thái: Tất cả", tìm theo họ tên / CCCD / tờ/thửa như `12/45`, huy hiệu
> "Đang lọc: k / N hộ"); cột Trạng thái có **thanh tiến độ 4 nấc** (□□□□ chưa lập PA → ■■■■ đã bàn giao); **dòng CỘNG** dưới danh sách
> hộ (diện tích, bồi thường đất, tài sản & cây, hỗ trợ & thưởng, tổng cộng của các hộ đang hiện). Quy ước giá tương đương để trống
> (dòng mẫu cũ tự bỏ khi mở dự án; tự thêm ở **Đơn giá đặc biệt** khi cần).

> **1.0.00**: **Tiến độ chi trả & Bàn giao** - một trang thay hai mục "Theo dõi chi trả & Bàn giao" và "Báo cáo tiến độ GPMB" (trùng phần
> lớn số liệu): 4 thẻ chỉ số bấm để lọc, hai chế độ xem **Theo hộ** / **Thửa còn vướng**, một nút **Xuất ▾** (bảng theo dõi, báo cáo tiến độ
> GPMB, đề nghị cưỡng chế), dòng **Mốc pháp lý** gọn (ngày thông báo thu hồi đất nhập ở nút "Mốc pháp lý…"). Phím tắt trang: Ctrl+1..5
> (Lập khái toán & Dự toán là Ctrl+5).

> **0.9.99**: bản in **tự dàn trang** (lề chuẩn, vừa bề ngang, ngắt trang ở chỗ hợp lý; trang cuối tràn ít thì nén khít, hở
> nhiều thì giãn cân đối; tổng cộng và chữ ký cùng trang). Lề trang chỉnh được trong hồ sơ địa phương (`ban_in.le_trang`). Bảng
> tổng hợp dự thảo: "(DỰ THẢO)" thành dòng riêng dưới tiêu đề. Cửa sổ lập phương án bỏ nút SCAN, các nút một hàng. Mở phần
> mềm / dự án nhanh hơn trên máy yếu; đọc bản vẽ .dxf không cần thư viện ngoài. **PDF ảnh / ảnh scan đọc bằng Tesseract OCR đóng kèm**
> (thay nhận dạng chữ của Windows - không còn phải cài gói tiếng Việt). Sửa: phương án chi tiết có nguồn gốc đất dài in đậm nhầm dòng.

> **0.9.98**: nút **In…** (Ctrl+P) trong khung xem trước: chọn máy in, số bản, trang cần in như Word / Excel. Bảng tổng hợp
> ngắt trang giữa các hộ (không còn hộ vắt hai trang, mất đường kẻ), cột số đủ rộng (hết "#####"), bỏ chữ "(theo Quyết định số 08…)".
> Phương án chi tiết: tiêu đề bảng III không nằm trơ cuối trang; nguồn gốc đất thụt đầu dòng mỗi đoạn. "Hồ sơ scan" đổi thành
> **HS đính kèm**. Xuất hồ sơ & Bản in: chữ DỰ THẢO chỉ theo **Chế độ phát hành** (bỏ ô chọn mẫu từng bản in, dòng ghi chú,
> ô Báo cáo tiếp thu ý kiến).

> **0.9.97**: bảng các mục phương án có **menu chuột phải** (thêm / nhân bản / xóa dòng…). Gói cập nhật đổi đuôi thành **.larcud**
> (Trợ giúp → Cập nhật phần mềm; gói .pabtcn cũ vẫn nhận). Bản in: "Trị An, ngày ...... tháng ..... năm", tổ chức không in dòng CCCD,
> "DỰ ÁN <tên>". Xuất hồ sơ & Bản in: **Xem trước bảng tổng hợp**.

> **0.9.96**: **Bảng giá đất** có thẻ **Hệ số K** (QĐ 03/2026/QĐ-UBND) - mục Đất tự nhân hệ số K. Mục 1. Đất: **Thêm tất cả thửa** /
> **Chọn nhiều thửa…**, chọn nhiều dòng (Shift / Ctrl) để xóa hoặc đặt cùng vị trí / giá. **Hồ sơ scan** của hộ (nút ở thẻ thửa đất,
> Trạng thái hộ, cột ở Theo dõi tiến độ) và danh sách **Hộ hoàn tất CTBT** (có quyết định + đã bàn giao) xuất Excel.

> **0.9.95**: giao diện gọn - thẻ số chỉ ở Danh sách hộ, banner chỉ ở màn hình chào, cửa sổ lập phương án hộ một hàng nút (◀ / ▶
> chuyển hộ), nút Trở lại / Tiếp theo cùng hàng tổng cộng. **Quét giấy tờ**: xem trước mọi trang ảnh / PDF bên trái (Ctrl + lăn chuột
> phóng to, kéo để di chuyển, Xoay 90°, nút "Chữ OCR" xem chữ nhận dạng); đọc được **bảng phương án chi tiết** của hộ đã scan và
> **Nhập trọn bộ vào phương án hộ** (hộ, nhân khẩu, nguồn gốc, tái định cư, thửa, tài sản / cây / hỗ trợ). PDF scan cần gói nhận dạng
> chữ tiếng Việt của Windows (Cài đặt > Thời gian và ngôn ngữ > Ngôn ngữ) hoặc Tesseract.

> **0.9.94**: cột **Số lượng** kiểu kế toán - nhà, công trình `46,00`; đất, cây, vật nuôi, hỗ trợ, khác `16,0`. Không còn thanh tab
> phía trên trang: chuyển trang bằng menu trái hoặc **Ctrl+1 … Ctrl+6** (Danh sách hộ, Tổng hợp tiền, Quyết định, Theo dõi tiến độ,
> Báo cáo, Dự toán); cửa sổ hộ đóng bằng nút **Đóng**. Tên dự án hiện ở giữa thanh menu trên cùng. **Niêm yết & Lấy ý kiến**: nút
> **Xuất bảng niêm yết** cùng hàng các nút đợt (số CCCD tự che).

> **0.9.93**: **Dán danh sách tài sản** hiểu câu viết tự nhiên - `Xoài: 16 cây, 17 năm tuổi`, `Tràm: 1453 cây, đường kính 28cm`,
> `Nhà tạm: 46m2`, `Gác để ở tính bằng Nhà 01 tầng kết cấu loại 4: 35,8m2`, `Ao nuôi cá ghép: 1,5ha, 1 năm 1 vụ` (dòng nền vàng: xem
> lại). **Cập nhật đơn giá**: nhóm Vật nuôi riêng, sửa Tên / ĐVT / Đơn giá trên bảng xem trước, dán bảng bằng **Ctrl+Shift+V**; PDF
> scan đọc bằng nhận dạng chữ của Windows 10 / 11 (cần gói tiếng Việt: Cài đặt > Thời gian và ngôn ngữ > Ngôn ngữ) hoặc Tesseract.
> Bản in: nguồn gốc đất sát mục III, dòng hỗ trợ đào tạo không lặp số, "Tái định cư:" in đậm.

> **0.9.92**: tên hiển thị **LARC** (lối tắt Desktop "LARC", tên đầy đủ "LARC - Bồi thường, hỗ trợ, tái định cư", bộ cài
> `LARC_Setup_Universal_<phiên bản>.exe`); file dự án mới đuôi **.larc** - file **.pabt** cũ vẫn mở và lưu bình thường; biểu tượng
> Desktop / thanh tác vụ đổi đúng khi cài bản mới (mỗi phiên bản một file biểu tượng riêng).

> **0.9.91**: **biểu tượng mới "3D LARC"** (ngôi nhà và chìa khóa vàng trên nền bản đồ địa chính xanh dương). Biểu tượng PABT.exe /
> lối tắt Desktop đổi khi cài bộ cài 0.9.91; Windows còn giữ biểu tượng cũ thì bỏ ghim rồi ghim lại PABT hoặc khởi động lại máy.

> **0.9.90**: **biểu tượng mới** (ô vuông xanh viền vàng, sách "Luật Đất đai 2024", chữ PABT). Biểu tượng PABT.exe / lối tắt Desktop
> đổi khi cài bộ cài 0.9.90 (gói cập nhật .pabtcn chỉ đổi biểu tượng bên trong phần mềm). Windows giữ biểu tượng cũ trong bộ nhớ đệm:
> nếu Desktop chưa đổi, bỏ ghim rồi ghim lại PABT trên thanh tác vụ hoặc khởi động lại máy.

> **0.9.89** (sửa lỗi): dán bảng Excel có cột Đơn giá / Thành tiền không còn đọc nhầm thành tỷ lệ; **CCCD** ô số Excel mất số 0 đầu
> được thêm lại khi nhập; ngày thiếu số năm báo lỗi; thư mục hồ sơ của đợt không đổi tên nhầm đợt khác; ghi chú đất gộp ô không làm
> dòng cao quá mức; khoảng năm "1975 - 1990" trong nguồn gốc không bị tách dòng.

> **0.9.88**: bản in chi tiết - ô **nguồn gốc đất căn đều hai bên**, dòng thưởng chỉ tên + thành tiền, **TỔNG CỘNG** gộp từ cột STT;
> dấu " - " nối tên riêng không còn bị tách dòng (nội dung đã tách sai ở bản trước: sửa tay); menu trái - **Đơn giá & bảng giá**
> xuống cuối (nhóm 6).

> **0.9.86**: **Nhật ký kiểm toán** (menu **Dữ liệu** / chuột phải danh sách hộ) - ai sửa, lúc nào, máy nào, giá trị cũ -> mới; không sửa,
> không xóa được, xuất Excel. **Kiểm tra lỗi** thêm nhóm **Bác sĩ hồ sơ** (DT bồi thường > DT thu hồi, tỷ lệ > 100%, nhân khẩu, hạn mức đất ở).

> **0.9.85**: **hồ sơ địa phương** `pabt_profile.json` (cơ quan, căn cứ pháp lý, số ngày, tỷ lệ kinh phí tổ chức thực hiện và phân bổ
> 85 / 15, vị trí cột mẫu in) và **gói mẫu in & cấu hình `.pabtcfg`** (menu **Công cụ**): xuất ở máy đã sửa mẫu, gửi qua Zalo, máy khác bấm
> đúp là cập nhật. Nguồn gốc đất trên bản in canh trên; bản dự thảo tự che số CCCD.

> **0.9.84**: **xem trước bản in A4 ngay trong cửa sổ** - hộp **Xuất hồ sơ & Bản in** có trang A4 ở nửa phải (bấm hộ nào xem hộ đó, đổi
> Dự thảo / Chính thức là đổi theo); cửa sổ lập phương án hộ bấm **Xem trước A4 (F4)** hoặc phím **F4**. Cần Microsoft Excel (bản xem trước chính là bản in).

> **0.9.83**: bản in - mọi ô bảng căn giữa theo chiều dọc, dòng cao vừa chữ có chừa trên / dưới (không còn chữ chạm đường kẻ), nguồn gốc đất dài tự
> tách dòng ở chỗ hết câu, đường kẻ dưới tên đơn vị / tiêu ngữ / dự án cách chữ 5 pt.

> **0.9.82**: **một bộ mẫu in** cho hai chế độ - đặt sẵn dòng "(DỰ THẢO)" trong mẫu chính (hoặc để phần mềm tự thêm); chọn **Bản DỰ THẢO** thì in có chữ đó, chọn **Bản CHÍNH THỨC** thì phần mềm tự xóa. Ô tìm có kính lúp, lọc khi ngừng gõ.

> **0.9.81**: biểu tượng PABT mới (nền xanh hoàng gia, mái nhà vàng kim, thửa đất ngọc lục bảo). Cài bộ cài 0.9.81 để biểu tượng Desktop / taskbar đổi theo; đã ghim PABT lên taskbar từ bản cũ thì bỏ ghim rồi ghim lại.

> **0.9.80**: màn hình chào - bảng dự án gần đây có trạng thái trống, nút thao tác nằm trên đầu bảng, chân trang 4 liên kết (có **Quy trình 16 bước QĐ 18**); chưa mở dự án thì các nhóm Lập phương án, Tổng hợp, Phê duyệt ở menu trái bị mờ.

> **0.9.79**: màn hình chào có ba thẻ lớn hơn (Dự án mới - xanh lá, Mở dự án - xanh dương, Nhập file Excel - xanh navy); bấm vào bất cứ chỗ nào trong thẻ là chạy lệnh.

> **0.9.78**: cửa sổ lập phương án hộ có nút **Dán danh sách tài sản… (Ctrl+Shift+V)** nổi bật; có bảng tài sản trong bộ nhớ đệm thì hộp tự điền và phân loại sẵn.

> **0.9.77** (theo bố cục chuẩn V10): mọi cửa sổ con có đủ nút Thu nhỏ - Phóng to - Đóng, kéo góc để đổi cỡ và nhớ kích thước lần sau; cửa sổ chính tối thiểu
> 1024 x 680, Thu về = 1200 x 740 giữa màn hình. Niêm yết & Lấy ý kiến có nút **Xóa đợt** và **In PA Dự thảo gửi dân**. **Xuất hồ sơ & Bản in** là nơi duy nhất
> xuất file (chế độ Dự thảo / Chính thức). Kinh phí tổ chức thực hiện tính đúng 2,5% / 3,5% trên tổng bồi thường (gốc 100%).

> **0.9.76** (theo Mục IV Quyết định 18/2026/QĐ-UBND): nâng cấp **Nhóm 5 Tổng hợp & trình duyệt** và **Nhóm 6 Phê duyệt & bàn giao** - xem mục
> "Nhóm 5 và Nhóm 6: tổng hợp, trình thẩm định, phê duyệt, chi trả, bàn giao, cưỡng chế" bên dưới.

> **0.9.64**: Nút thu nhỏ, phóng to và đóng trở lại trên thanh tiêu đề Windows. Menu và banner xanh giữ nguyên.

> **0.9.54**: Cập nhật giá đất chỉ ở menu trái. Bộ đơn giá không còn mục trùng “Cập nhật bảng giá đất”.

> **0.9.53**: Chân trang màn hình chào là **Lịch sử cập nhật phần mềm**. Lịch sử bắt đầu từ bản này; các bản trước không được ghi. Hướng dẫn sử dụng vẫn mở bằng F1.

> **0.9.51**: Ô địa bàn chỉ cần tên (Trị An, Trảng Bom, Vũng Tàu; Đồng Nai, Hồ Chí Minh). Tải từ web mở thẳng nghị quyết bảng giá đất Đồng Nai. PDF ảnh đọc từng trang, có nút Dừng. Mẫu in chi tiết và tổng hợp lưu riêng trên từng máy. Nút Tệp tin mở menu khi thả chuột.

> **0.9.50**: **Tải từ web** mở Công báo, vào nghị quyết bảng giá đất, tải phụ lục Word và lấy đúng xã / phường đã nhập (bảy mức vị trí). Không còn dừng ở câu không thấy văn bản khi Công báo có nghị quyết.

> **0.9.49**: Nút **Tải từ web** trong Cập nhật giá đất không còn báo lỗi tiếng Anh khi thiếu module web. Bản cài kèm phần tìm web. Không tìm được bảng giá thì chọn file.

> **0.9.48**: **Cập nhật giá đất** thay hai lệnh Thay bảng giá đất và Bảng giá gắn sẵn. Nhập xã và tỉnh rồi tải từ web; không ra bảng giá thì chọn file Excel, Word hoặc PDF. Bảng mới thay bốn địa bàn gắn sẵn. Nút **Dùng lại bảng gắn sẵn** nằm trong hộp này.

> **0.9.47**: Bỏ mục **Quy chuẩn cây** trên menu trái. Mật độ cây vẫn lấy từ ghi chú bộ đơn giá khi bấm **Tính mật độ…** trong thẻ Cây trồng.

> **0.9.46**: Xóa ô Tỷ lệ % trên mục Đất thì ô để trống (tiền vẫn tính 100%). Hộ đã bấm Lưu, hoặc đã có dòng phương án, hiện Đã lập phương án kể cả khi đất, tài sản, cây, vật nuôi, hỗ trợ đều bỏ trống. Nguồn gốc có gạch đầu dòng được xuống dòng và thụt lề. Cập nhật mẫu in từ Excel hoặc PDF luôn xong, không báo lỗi.

> **0.9.45**: Cập nhật mẫu in nhận Excel hoặc PDF, tự nhận cấu trúc, không chặn bằng báo lỗi. Hộ đã lưu hoặc đã có dòng phương án (kể cả 0 đồng) là đã lập. Nguồn gốc có gạch đầu dòng xuống dòng và thụt lề. Ô tỷ lệ đất xóa trống thì không hiện lại 100.

> **0.9.44**: nút Tệp tin trên thanh menu nhận đúng vùng bấm. Bảng tổng hợp giãn dòng theo chữ. Đường kẻ dưới tên đơn vị gần chữ hơn, ngắn hơn dòng chữ và căn giữa.

> **0.9.43**: dự toán có nút **Thêm hạng mục** (nhà, cây, vật nuôi, hỗ trợ, thưởng — cùng danh mục lập phương án). Chi phí bồi thường chọn **2,5%** hoặc **3,5%** theo QĐ 08/2025/QĐ-UBND.

> **0.9.42**: tiêu đề thanh menu (Tệp tin, Chỉnh sửa, …) không còn bị cắt khi phóng to chữ. Thanh cao theo cỡ chữ.

> **0.9.41**: menu trái có biểu tượng ở Thay bảng giá đất, Bảng giá gắn sẵn và Dự thảo PABT. Trong dự thảo, **Thêm hộ vào đợt…** chọn thủ công hộ của đợt 1, đợt 2, đợt khác, hộ chưa lấy ý kiến, chưa đồng thuận hoặc có ý kiến khác.

> **0.9.40**: mục **Dự thảo PABT** (nhóm Lập phương án). Phễu 6 mắt xích trên số hộ thật. Đợt niêm yết 10 ngày, đối thoại 30 ngày. Ba tỷ lệ đồng thuận tách riêng: theo đợt, lũy kế đã niêm yết, độ bao phủ cả dự án. Hộ vướng V1–V5 không vào đợt. Bảng niêm yết che CCCD.

> **0.9.39**: thay cả bảng giá đất bằng file Excel của địa bàn đang làm (ví dụ Phường Trảng Bom, hoặc tỉnh khác). Bốn địa bàn gắn sẵn không còn hiện cho đến khi dùng lại.

> **0.9.38**: ô Loại đất đủ danh mục Thông tư 08/2024; ô Vị trí xổ có thanh cuộn, đủ 4 địa bàn NQ 28. Mẫu dự thảo chỉ để áp giá trước niêm yết (Luật Đất đai 2024, Nghị định 88/2024/NĐ-CP). Đường kẻ in cách chữ hơn. Thanh menu bấm đúng mục.

> **0.9.37**: mẫu in chính thức không có chữ dự thảo. Mẫu dự thảo chọn trong hộp In: `IN_CHITIET_DT`, `IN_TONGHOP_DT`. Hộ không có tiền thưởng thì không in tỷ lệ. Đường kẻ dưới tên cơ quan, tiêu ngữ và tên dự án sát chân chữ, căn giữa.

> **0.9.35**: danh sách hộ có cột **Ghi chú** (bên phải Trạng thái) — nội dung lệch so với file Excel, ô vàng cam.

> **0.9.34**: dải nhận diện 48px (logo, tên phần mềm, cơ quan / đơn vị lập, tên dự án, đèn LAN). Họ tên chủ sở hữu được có chữ số.

> **0.9.33**: Ctrl+S khi đang soạn hộ ghi phương án rồi mới ép file xuống đĩa; tab kéo đổi chỗ; chân trang chào thêm Cài đặt.

> **0.9.32** (đặc tả 5.0 đủ): thanh điều hành 38px (ẩn băng xanh ~65px); **đa tab** Màn hình chính ⇄ Danh sách hộ ⇄
> **Hộ: …** ⇄ Dự toán ⇄ **Bộ đơn giá** (Ctrl+Tab, giữ số liệu đang nhập); màn hình chào thẻ đổ bóng + lưới gần đây có
> **ghim**; chân trang cẩm nang QĐ 08/2025 và bảng giá NQ 28; màu Deep Navy / Royal Blue, bỏ vàng neon.
>
> **0.9.31** (đặc tả 5.0): thanh menu hợp nhất (logo + tên dự án + LAN, ẩn băng tiêu đề xanh để thêm chỗ cho bảng);
> thanh **tab** mở nhiều trang cùng lúc (Ctrl+Tab); màn hình chào dạng thẻ + lưới dự án gần đây; chân trang Hướng dẫn / NQ 28 / Cài đặt.
>
> **0.9.30**: màn hình chào — **Hướng dẫn sử dụng (F1)** là liên kết nhỏ, không còn nút cạnh ba lệnh bắt đầu.
> Bỏ chữ **Cơ quan: …** góc phải thanh menu.
>
> **0.9.29**: **Bộ đơn giá** có **Sửa bộ đơn giá** (thêm / sửa / xóa / thay thế một mục, hoặc cập nhật cả bộ) — chỉ khi đã đăng
> nhập tài khoản **quản trị máy chủ LAN**, hoặc sau khi mở khóa bằng **mật khẩu quản trị bộ đơn giá** trên máy này (lần đầu tự
> đặt). **Màn hình chính**: đóng dự án, mở dự án khác, xóa khỏi danh sách gần đây hoặc xóa file `.pabt` — không cần thoát phần mềm.
> Thẻ **Quy ước giá tương đương** trong Bộ đơn giá hiện quy ước của dự án đang mở và tự làm mới sau khi xóa / sửa ở **Đơn giá
> riêng**.
>
> **0.9.27**: biểu tượng mới duy nhất (chữ PABT trên nền trắng sữa, viền xanh đậm + đường vàng - nổi rõ trên Desktop; chữ không
> còn bị góc bo cắt). Menu trái có **Màn hình chính** (về màn hình bắt đầu, dự án đang mở vẫn mở); **Bảng giá đất** có biểu tượng,
> chữ thẳng hàng như các mục khác. Máy đã cài bản cũ mà biểu tượng Desktop chưa đổi: Windows còn giữ ảnh cũ trong bộ đệm - khởi
> động lại máy (hoặc xóa rồi tạo lại lối tắt).
>
> **0.9.26**:
> - **Một bộ cài cho mọi máy Windows**: `PABT_Setup_Universal_<phiên bản>.exe` (Windows 7 SP1 → Windows 11, 32-bit và 64-bit) - tự
>   chọn bản hợp với máy; không cần Python, Visual C++ hay mạng. Gói dự phòng `PABT_ChayNgay_<phiên bản>_Universal.zip`.
> - Danh sách hộ: nút **Xuất** - Excel các hộ đang chọn, hoặc các hộ đang lọc theo Đợt / Trạng thái / Tìm (theo dõi, trình, lưu trữ).
> - **Chỉnh sửa → Hoàn tác / Làm lại** trên thanh menu (Ctrl+Z / Ctrl+Y như cũ). Sửa: cửa sổ mở không phủ hết màn hình (lỗi hình
>   góc phải); màn hình 1366 px hàng công cụ tự xuống dòng; in bảng tổng hợp khi mẫu in chỉ cập nhật một mẫu; thẻ Vật nuôi của
>   dự án cũ trống (nút **Bổ sung vật nuôi từ bộ đơn giá**); ô Nhân khẩu gõ số không còn dính chữ "chưa nhập".
>
> **0.9.24** - **Chuẩn hóa theo đặc tả kiến trúc ARCH-PABT-2026-V4**:
> - **Bộ cài cho mọi máy**: `PABT_Setup_Universal_<phiên bản>.exe` tự nhận Windows - Windows 10 (1809 trở lên) / 11 64-bit cài bản
>   64-bit (Qt6); Windows 7 / 8 / 8.1, Windows 32-bit cài bản 32-bit (Qt5, tự cài bản vá KB3063858 cho Windows 7 khi thiếu). Vẫn có
>   hai bộ cài riêng `PABT_CaiDat_<phiên bản>_Win10-11_x64.exe`, `PABT_CaiDat_<phiên bản>_Win7-8-10_x86.exe` và bản chạy ngay
>   (giải nén ra ổ D: / USB là dùng) `PABT_ChayNgay_<phiên bản>_x64.zip` / `_x86.zip`.
> - Băng tiêu đề ghi **Bản Tiêu chuẩn · Sử dụng nội bộ** thay nhãn "BẢN THỬ NGHIỆM" (chưa kích hoạt bản quyền thương mại).
> - Thanh menu thêm **Cài đặt** (Thông tin dự án, Kết nối máy chủ LAN, cỡ chữ) và **Tệp tin → Lưu dự án (Ctrl+S)** (mọi thay đổi
>   vốn được ghi ngay; lệnh ép ghi hẳn xuống đĩa và báo giờ lưu).
> - Thanh trạng thái: **Sẵn sàng · Tổng cộng: N hộ | Đã chọn: k hộ**, đèn **● LAN** (Trực tuyến / Ngoại tuyến / Máy đơn).
> - Màu sắc theo bộ chuẩn doanh nghiệp (xanh Navy chủ đạo, nút Lưu / Thêm xanh lá, nút Xóa đỏ nhạt); dòng bảng cao 32 px, nút menu
>   trái cao 36 px. Ô tìm danh sách hộ chờ ngừng gõ 0,2 giây mới lọc (gõ tiếng Việt có dấu không còn làm bảng nháy).
> - **Che số CCCD** khi in bản niêm yết công khai (hộp **In / Xuất** → ô "Che số CCCD", ví dụ 075092******, bỏ ngày / nơi cấp) -
>   theo Nghị định 13/2023/NĐ-CP; phần mềm nhớ lựa chọn theo dự án.
> - **Ghi file an toàn**: tạo dự án mới / nhập Excel vào file mới / lưu dự án thành… ghi ra file tạm rồi mới thay file đích - lỗi
>   hoặc mất điện giữa chừng không còn làm mất file cũ.
> - Máy chủ LAN: danh sách dự án đọc một file chỉ mục nhỏ thay vì mở từng file dự án qua mạng (ổ mạng chậm mở nhanh hơn nhiều).

> **0.9.23 – BẢN THỬ NGHIỆM** - **Bố cục lại theo vòng đời dự án** (theo lộ trình tái cấu trúc giao diện):
> - **Thanh menu** đầu cửa sổ: **Tệp tin** (Dự án mới Ctrl+N, Mở dự án Ctrl+O, Dự án trên máy chủ Ctrl+Shift+O, Lưu dự án thành
>   Ctrl+Shift+S, Đóng dự án, Thoát), **Dữ liệu** (Nhập file Excel, Nhập phương án chi tiết, Báo cáo tổng hợp, Đối chiếu file Excel),
>   **Công cụ** (Mẫu in, Bộ đơn giá, Rà soát giá, Thông tin dự án), **Trợ giúp** (Hướng dẫn sử dụng **F1**, Cập nhật phần mềm,
>   Giới thiệu). Không còn nút xổ "DỰ ÁN ▾" ở đầu menu trái (danh sách xổ từng che các nút bên dưới).
> - **Menu trái 5 nhóm** theo thứ tự công việc: **Dự án & dự toán** (Thông tin dự án, **Dự toán & khái toán**, Danh sách hộ) ·
>   **Bảng giá & chính sách** (Bộ đơn giá, Đơn giá riêng, **Bảng giá đất** NQ 28, Quy chuẩn cây) · **Lập phương án** (Lập phương án,
>   Kiểm tra lỗi, Đối chiếu file Excel) · **Tổng hợp & trình duyệt** (Tổng quát hộ, Tổng hợp tiền, Đợt trình, In / Xuất) · **Tiến
>   độ & bàn giao** (Quyết định phê duyệt, Theo dõi tiến độ, Trạng thái hộ, Báo cáo tổng hợp).
> - **Danh sách hộ**: thanh công cụ **Thêm hộ · Lập phương án · Xóa hộ** ngay trên bảng, cùng hàng bộ lọc; **Xóa hộ chỉ sáng khi
>   đang chọn hộ**. Chọn từ 2 hộ: hàng "Đã chọn N hộ" với In / Xuất, Đợt trình, Trạng thái hộ, Xóa hộ.
> - **Thẻ số liệu bấm được**: bấm "Đã phê duyệt" / "Đã chi trả" / "Đã bàn giao" / "Đã lập phương án" để lọc ngay danh sách; bấm
>   "Số hộ" để bỏ lọc. Tổng kinh phí hiện gọn (ví dụ **185,4 tỷ**, rê chuột xem đủ số).
> - **Dự toán & khái toán** là một trang trong cửa sổ chính (trước là hộp thoại riêng), dùng được cả khi chưa mở dự án. Thẻ mới
>   **So sánh với thực tế áp giá**: khái toán đã duyệt (mở file .pabtdt, hoặc bảng đang lập) so với tổng phương án các hộ theo từng
>   mục; **cảnh báo đỏ khi thực tế vượt khái toán**. Sửa một ô dự toán không còn vẽ lại cả bảng.
> - **Màn hình chào** khi chưa mở dự án: 3 nút lớn (Dự án mới, Mở dự án, Nhập file Excel) và **5 dự án làm việc gần đây** (nhấp
>   đúp để mở).
> - Băng tiêu đề ghi **đơn vị lập phương án của dự án đang mở** (ô "Đơn vị lập phương án" trong Thông tin dự án); chưa mở dự án:
>   đơn vị mặc định của máy.
> - Bộ cài: mặc định cài vào **C:\Program Files (x86)\PABT** (Windows hỏi quyền quản trị một lần; không có quyền thì tự cài vào
>   thư mục người dùng). Tự kiểm tra sau khi cài chạy thử tạo dự án, in phương án chi tiết, bảng tổng hợp, tờ trình.

> **0.9.22 – BẢN THỬ NGHIỆM** - **Rà soát toàn bộ** (dự án giả lập 3.000 hộ có 3 quyết định, đo cùng máy, trước -> sau):
> - **Bảng tổng hợp** (menu trái): bấm thẳng vào thẻ (Thông tin tổng quát hộ / Quyết định phê duyệt / Tổng hợp tiền) thì tiêu đề
>   trang và dấu chọn ở menu trái đổi theo.
> - Thẻ **Quyết định phê duyệt** mở 1,6 giây -> 0,16 giây (trước đây bảng hộ bị dựng hai lần); thẻ **Tổng hợp tiền** 0,58 -> 0,29
>   giây; trang **Theo dõi tiến độ** đổi bộ lọc 0,5 -> 0,09 giây. Bấm tiêu đề cột ở thẻ Tổng hợp tiền sắp xếp **theo số tiền**
>   (trước đây sắp theo chữ: 9.000 đứng sau 10.000.000). Cột hạng mục bỏ số thứ tự (bản in: 4 vật nuôi, 5 hỗ trợ, 6 thưởng).
> - Trang **Theo dõi tiến độ** bỏ hàng 6 ô đếm (trùng hàng số liệu phía trên cửa sổ): số hộ của từng điều kiện ghi ngay trong ô
>   **Lọc**, ví dụ "Còn quyết định chưa nhận tiền (12)". Xuất Excel ở trang Tổng hợp tiền / Tiến độ khi file đang mở trong Excel nay
>   báo rõ lý do (trước đây hiện lỗi kỹ thuật).
> - **Dự án mới** 3.000 hộ (tạo + tự lập phương án): 8,5 -> 3,4 giây. **In / xuất** phương án chi tiết 50 hộ: 4,1 -> 3,0 giây (file
>   in ra giống hệt bản trước).

> **0.9.20 – BẢN THỬ NGHIỆM** - **Rà soát dự án lớn** (3.000 hộ / 5.000 thửa, đo cùng máy, trước -> sau):
> - Sửa lỗi số liệu: nhập file PABT Excel đọc **hết** sheet THEO_DOI (trước đây chỉ 400 dòng đầu - dự án trên ~395 hộ thì các hộ sau
>   không được đối chiếu với Excel mà không báo); nhập phương án chi tiết đọc **hết** sheet của hộ (trước đây cắt ở dòng 600 - hộ
>   nhiều cây / công trình mất các dòng cuối và dòng TỔNG CỘNG).
> - Nhập quyết định phê duyệt cho 3.000 hộ: 5,8 giây -> 0,5 giây (cả lô ghi một lần; trên ổ cứng HDD / thư mục Google Drive / ổ mạng
>   trước đây có thể vài phút). Lỗi giữa chừng không còn để lại quyết định ghi dở. Trạng thái hộ, chi trả, bàn giao, thêm / bỏ hộ
>   khỏi quyết định cũng ghi cả lô một lần.
> - Kết quả tính tiền 3.000 hộ dùng chung, lưu một hộ chỉ tính lại hộ đó: tải lại danh sách 0,64 -> 0,28 giây, lưu một hộ rồi tải
>   lại 1,1 -> 0,7 giây, trang Tổng hợp tiền 0,94 -> 0,44 giây, tổng hợp theo dõi 0,23 -> 0,05 giây, dự toán 0,23 -> 0,09 giây.
> - Không còn "Không phản hồi": báo cáo tổng hợp, báo cáo đối chiếu, cài gói cập nhật ghi ở luồng nền (hộp "Đang xử lý…"); xuất
>   bảng tổng hợp có tiến trình; Dự án mới xuất bản in từng hộ có hộp tiến trình và nút **Dừng**; mở / đóng phần mềm khi máy chủ mất
>   mạng không còn bị treo.
> - Cập nhật đơn giá: đổi nhóm / sửa một ô rồi so khớp lại 4 giây -> 0,06 giây; tải văn bản trên mạng ghi thẳng ra file (không giữ
>   cả file trong bộ nhớ), không tải cả file chỉ để xem loại; xóa file tạm sau khi phân tích.
> - Kiểm tra lỗi: gõ ô tìm không còn vẽ lại bảng theo từng phím; chọn tất cả sheet khi nhập chi tiết không còn treo với file nhiều sheet.
>
> **0.9.20 (tiếp)**:
> - **Kinh phí tổ chức thực hiện bồi thường** theo Quyết định số 08/2025/QĐ-UBND ngày 10/02/2025 của UBND tỉnh Đồng Nai: dự án hạ
>   tầng **theo tuyến** (đường, kênh, đường dây, đường ống…) tối đa **3,5%**; dự án **cụm, vùng, khu** và dự án khác tối đa **2,5%**
>   tổng kinh phí bồi thường, hỗ trợ, tái định cư. Phần mềm tự nhận loại theo tên dự án ("Xây dựng đường…" = theo tuyến; "Khu…",
>   "Cụm…" = cụm / vùng); đổi ở **Dự án → Thông tin dự án…**, ô "Kinh phí tổ chức thực hiện bồi thường" (chọn loại, hoặc gõ tỷ lệ
>   thấp hơn mức tối đa). Bảng tổng hợp tự ghi đúng tỷ lệ và căn cứ vào dòng "Kinh phí đảm bảo…"; dòng chia 85% / 15% giữ theo mẫu.
>   Dự toán: dòng "Chi phí thực hiện công tác bồi thường" lấy mặc định 3,5% / 2,5% theo tên dự án.
> - **Mẫu in** (menu In, báo cáo → **Mẫu in**, trước là "Cập nhật mẫu in"): nhận cả file chỉ có MỘT mẫu (trước đây báo "File Excel
>   không có sheet IN_CHITIET / IN_BANGTONGHOP" khi file thiếu một trong hai sheet) và file mẫu đã sửa sẵn, sheet tên bất kỳ (tự nhận
>   là mẫu chi tiết hay bảng tổng hợp; không nhận ra thì hỏi). Chọn **Thay mẫu chính** hoặc **Thêm mẫu riêng…** (đặt tên, ví dụ "Dự
>   thảo"): mẫu riêng chọn ở ô cạnh "Phương án chi tiết" / "Bảng tổng hợp" trong **In / Xuất**. Mẫu cũ được giữ trong mau_in\cu.
> - Nút **Dự án** trên menu trái nổi bật (nền xanh đậm, vạch vàng); menu gọn chữ ("Lập phương án", "Dự toán", "Mẫu in"…, rê chuột
>   xem tên đầy đủ); "Đối chiếu với file Excel…" chuyển vào nút Dự án. Biểu tượng: chữ PABT trên nền trắng sữa.
> - **Đợt trình**: ô **Chọn hộ** + nút **Đưa … hộ vào đợt**: hộ đã lập phương án chưa xếp đợt / hộ vừa lưu phương án gần nhất / mọi
>   hộ chưa xếp đợt / hộ đã trình đợt khác nhưng chưa phê duyệt (trình lại) / hộ đang chọn ở danh sách. Nút "Chỗ trống dùng trong
>   mẫu…" đổi tên **Mã điền tự động {…}…**: danh sách mã gõ vào mẫu Word / Excel của tờ trình, phương án tổng (khi xuất hồ sơ mã được
>   thay bằng số liệu thật); không sửa mẫu thì không cần dùng.
> - Tên file bản in bỏ phần "là chủ sở hữu…" sau họ tên.
> - **Bộ cài** (Win10-11 và Win7-8): sửa lỗi "Unable to save shortcut …L?p phương án b?i thư?ng.lnk" trên máy Windows tiếng Anh /
>   tên người dùng có dấu - lối tắt tạo bằng API Unicode; lối tắt lỗi không còn làm hỏng cả lần cài; tự kiểm tra sau cài chờ tối đa
>   3 phút.
>
> **0.9.19 – BẢN THỬ NGHIỆM** - **Mỗi lệnh một chỗ**: bỏ các nút / mục trùng lệnh - hai nút "Lập phương án hộ đang chọn", "Thêm
> hộ…" trên danh sách (dùng menu trái, bấm đúp hoặc chuột phải), nút "Lưu phương án hộ" cuối thẻ Hỗ trợ (dùng **Lưu (Ctrl+S)**),
> nút "Quyết định, chi trả, bàn giao của hộ…" ở trang Theo dõi tiến độ (dùng **Trạng thái hộ…** hoặc bấm đúp dòng), mục "Dự án trên
> máy chủ…" lặp trong menu tài khoản. **Quyết định phê duyệt** chuyển sang nhóm **Trình, theo dõi tiến độ**; nhập quyết định từ file
> bằng nút **Nhập từ file…** trên trang này (bỏ mục "Nhập quyết định…" trùng). **Quy chuẩn cây, tài sản…** có lại trên menu (nhóm
> Đơn giá, dự toán). Lệnh với hộ đang chọn lấy hộ chọn **trên trang đang xem**. Dự án mở **chỉ xem** (máy khác đang sửa): không còn
> nút nào bấm được để sửa / thêm hộ (trước đây nút "Thêm hộ…" vẫn bấm được rồi báo lỗi).
>
> **0.9.18 – BẢN THỬ NGHIỆM** - **Màn hình gọn, vừa laptop 1366×768**: băng tiêu đề thấp còn khoảng một nửa (vẫn đủ tên phần mềm,
> tên đơn vị, địa chỉ - dòng địa chỉ tự rút gọn "…" khi cửa sổ hẹp, rê chuột xem đủ; nút Hoàn tác / Làm lại; nhãn BẢN THỬ
> NGHIỆM); tên dự án một dòng; băng đối chiếu Excel và hai nút **Lập phương án hộ đang chọn**, **Thêm hộ…** chung một hàng (nút
> Bảng tổng hợp, Theo dõi tiến độ dùng ở menu trái). Danh sách hộ hiện được **12 dòng** thay vì 8 trên màn hình 1366×768; cửa sổ
> không còn rộng hơn màn hình (trang **Quyết định phê duyệt**: hàng nút tự xuống dòng). Cửa sổ lập phương án: ô **"Cần xem
> lại"** chỉ hiện khi có điểm cần xem lại (nền vàng nhạt), không còn chiếm chỗ để ghi "Không có điểm cần xem lại".
>
> **0.9.17 – BẢN THỬ NGHIỆM** - **Đơn giá vật nuôi** theo QĐ 31/2025/QĐ-UBND ngày 29/08/2025 (hiệu lực 10/9/2025) có sẵn trong
> bộ đơn giá tích hợp (phiên bản 2026.10.09), mã **VN01 – VN17**: bồi thường thiệt hại ngừng sản xuất thủy sản (ao nuôi tôm nước
> lợ, cua, tôm – cua, hàu treo giàn bè; ao nuôi tôm nước ngọt; ao nuôi cá - quảng canh cải tiến / thâm canh / nuôi ghép, mỗi loại
> 2 mức: nuôi **dưới 50%** hoặc **từ 50% đến 80%** định mức thời gian nuôi; ĐVT ha/vụ; cá nuôi lồng bè ĐVT 100 m³/vụ) và **chim
> yến** (theo giá thị trường, tối đa 18.500.000 đ/kg yến thô). Lập phương án: **mục 3**, gõ "vat nuoi", "ao nuoi" hoặc "yen" ở ô
> nhập nhanh. Giá ở Điều 4 đã tính theo thời gian nuôi (tương ứng tỷ lệ 70% / 50% của Điều 3) - **không nhân thêm tỷ lệ**. Số lượng
> ĐVT ha/vụ, 100 m³/vụ giữ 4 chữ số thập phân (ao 0,25 ha; lồng 25 m³ = 0,25) - trước đây làm tròn 1 chữ số (0,3).
> **Cửa sổ Bộ đơn giá** gọn lại: thẻ riêng **Nhà, công trình / Cây trồng / Vật nuôi**; nút **Cập nhật đơn giá** (từ file, từ trang
> web, tra cứu văn bản mới), **Giá đất NQ 28/2025** (tra bảng giá, xuất Excel), **Đơn giá riêng của dự án…** và **Áp bộ đơn giá
> vào dự án đang mở** (bên phải). **Cập nhật đơn giá từ văn bản ghi giá trong lời văn** (như QĐ 31/2025) đọc đúng tên từng mức
> giá kèm điều kiện ("… (nuôi dưới 50% định mức KT-KT thời gian nuôi)"); không còn ghép nhầm "gần đúng" hai mục khác nhau chỉ vì
> phần trong ngoặc giống nhau; thông báo nêu đúng lý do khi không xử lý được văn bản. Tìm trên Công báo theo số hiệu (vd. "31/2025")
> mở được trang văn bản mang số đó. Lưu ý: Công báo Đồng Nai có **hai** QĐ số 31/2025/QĐ-UBND (10/04/2025 về canh tác hữu cơ -
> trước sáp nhập; 29/08/2025 về vật nuôi) - tìm bằng từ khóa **"vật nuôi"** để ra đúng văn bản.
> **Nhanh hơn với dự án lớn** (10.000 thửa): trang Thông tin tổng quát mở 0,98 -> 0,18 giây, gõ / xóa ô tìm 0,88 -> 0,10 giây;
> Theo dõi tiến độ vẽ lại 0,47 -> 0,03 giây; Kiểm tra lỗi 1,4 -> 0,9 giây; Dự toán từ dự án 0,5 -> 0,3 giây; mở phần mềm nhanh hơn
> ~20%. Con trỏ "đồng hồ cát" không còn bị kẹt khi có lỗi; thông báo lỗi ghi rõ **việc gì không làm được - lý do - cách xử lý**
> (vd. file đang mở trong Excel, không có quyền ghi, ổ đĩa đầy, file dự án hỏng).
>
> **0.9.16 – BẢN THỬ NGHIỆM** (nhãn vàng "BẢN THỬ NGHIỆM" trên băng tiêu đề, tiêu đề cửa sổ, hộp Giới thiệu): dùng để kiểm tra
> trước khi phát hành chính thức. **Bỏ hẳn chữ ký số**: gói cập nhật `.pabtcn` không ký, phần mềm và bản vá cập nhật không
> kiểm tra chữ ký nữa - gói chỉ được kiểm tra mã SHA-256 từng file (gói hỏng / tải dở thì không cài); chỉ cài gói nhận trực
> tiếp từ người phát triển. Máy đang dùng 0.9.13 – 0.9.15 (bản cũ còn đòi chữ ký) **không cài được** gói mới: cài bộ
> cài 0.9.16 một lần (dự án, cài đặt, mẫu in trong `%APPDATA%\PABT` giữ nguyên); từ đó các gói sau cài bình thường.
> **Bỏ màn hình "Kiểm tra an toàn"** (nút góc dưới bên phải) cùng việc phần mềm tự quét virus và kiểm tra toàn vẹn file cài mỗi
> lần mở - trùng với Microsoft Defender của máy (Defender vẫn tự quét file khi tải về / mở). Vẫn giữ: tắt macro khi phần mềm mở
> file bằng Word / Excel, HTTPS kiểm tra chứng chỉ, chặn file nén / XML độc. **Xóa hộ ngay trên danh sách**: chọn một hoặc nhiều
> hộ (giữ Ctrl / Shift) rồi bấm **Xóa hộ…** ở menu trái (nhóm Hồ sơ và phương án), chuột phải, hoặc phím **Delete**; hỏi lại trước
> khi xóa (nêu số thửa, dòng phương án, hộ đã có quyết định); xóa nhầm bấm **Hoàn tác** (Ctrl+Z) lấy lại. **Bản Windows 7 / 8**:
> sửa lỗi phần mềm tự tắt khi bấm chuột phải trên danh sách hộ hoặc "Tra cứu văn bản mới…".
>
> **0.9.16** - **Trình phê duyệt**: cửa sổ **Đợt trình…** có thêm văn bản trình (Tờ trình / Văn bản: số, ngày), **số / ngày
> phương án tổng** (tự in vào dòng "Đính kèm Phương án số …" và ngày ký của bảng tổng hợp), **số PA chi tiết từng hộ** (nút
> **Đánh số PA chi tiết…** hoặc sửa thẳng trên bảng; tự in vào "Số: …/" và ngày của phương án chi tiết, mang sang quyết định phê
> duyệt), khung **Mẫu văn bản trình**: **Thêm mẫu** tờ trình (Word, Excel, PDF) / phương án tổng (Word, PDF), **Sửa mẫu**, **Mẫu
> mặc định**, **Mã điền tự động {…}…**. Xuất / In: chọn từng mẫu (in riêng lẻ) hoặc **Chọn tất cả mẫu (in đồng loạt)**, lưu
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
Thanh menu **Tệp tin** → **Dự án mới…** (Ctrl+N, hoặc nút lớn **Dự án mới** trên màn hình chào) và làm 4 bước — đây là nơi
duy nhất nhập / sửa dữ liệu thô:

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

Sau đó bổ sung từng hộ ở **Lập phương án hộ…** (nhà, công trình, cây trồng từ danh mục; số lượng; hồ sơ hộ ở thẻ **Thông tin hộ,
thửa đất** của cùng cửa sổ).

## Bản in (phương án chi tiết, bảng tổng hợp)

Đường kẻ ngang dưới tên đơn vị, dưới "Độc lập - Tự do - Hạnh phúc" và dưới dòng "Dự án" được phần mềm tự canh mỗi lần in: nằm sát
ngay dưới chữ (hở một khoảng nhỏ, không che dấu nặng), căn giữa theo nội dung phía trên; đường dưới tiêu ngữ dài bằng dòng
tiêu ngữ. Tên đơn vị, tên dự án dài ngắn khác nhau vẫn canh đúng.

- Đầu trang: tiêu đề cơ quan 2 dòng ("TRUNG TÂM PHÁT TRIỂN QUỸ ĐẤT / THÀNH PHỐ ĐỒNG NAI", "CHI NHÁNH VĨNH CỬU"), quốc hiệu, số
  phương án "Số: …/PA-TTPTQĐ.CNVC", chức vụ người ký "PHÓ GIÁM ĐỐC" — lấy từ **Thông tin dự án** (Đơn vị cấp trên, Tên đơn vị trên
  tiêu đề bản in, Ký hiệu số phương án, Chức vụ người ký…); ô nào để trống thì dùng thông tin đơn vị khai ở Cài đặt → Cấu hình nghiệp vụ → Cơ quan.
- Các đường kẻ ngang của mẫu cũ (dưới tên cơ quan, dưới "Độc lập - Tự do - Hạnh phúc", dưới tên dự án) được giữ: lưu ở
  `mau_in\IN_CHITIET.duong_ke.xml` và chèn vào từng file bản in; **Cập nhật mẫu in…** từ file Excel lấy lại cả đường kẻ.
- Dòng 1.x (bồi thường đất): "Thửa đất số …, tờ bản đồ số …, loại đất …, xã (phường) … (Vị trí 1 / 2 / 3 / 4)"; thiếu thông tin
  thì để "……" chờ điền.
- **Xem trước A4 (0.9.84)**: hộp **Xuất hồ sơ & Bản in** chia đôi - nửa phải luôn hiện trang A4 của hộ đang bấm trong danh sách
  (đổi **Bản DỰ THẢO / CHÍNH THỨC**, ô **Che số CCCD** hay mẫu thì bản xem trước lập lại). Cửa sổ lập phương án hộ: nút
  **Xem trước A4 (F4)** / phím **F4** mở / đóng nửa phải, hiện cả số liệu đang soạn chưa lưu (sửa xong ~1,5 giây tự lập lại).
  Thanh công cụ: **+ / −** phóng to / thu nhỏ, **Vừa trang**, **◀ k / N ▶** lật trang, **In nhanh** (hỏi trước, in bản đang xem ra
  máy in mặc định). Bản xem trước do Microsoft Excel tạo ở nền (~1,5 - 2 giây, vẫn thao tác được); file tạm ở
  `%TEMP%\pabt_preview` tự xóa khi đóng cửa sổ. Máy không có Microsoft Excel (hoặc Excel lỗi / treo): phần mềm tự dựng **bản
  gần đúng** (nhãn vàng "Bản gần đúng" trên thanh công cụ) từ chính file bản in - đủ chữ, số, ô gộp, khung bảng; không có đường kẻ
  vẽ và ngắt trang của Excel. In / xuất PDF chính thức vẫn cần Excel.
- Chủ sử dụng là **tổ chức** (tên bắt đầu bằng Công ty, UBND / Ủy ban nhân dân, Ban quản lý, Hợp tác xã, Trung tâm, Nhà thờ, Chùa,
  Trường tiểu học…, hoặc có TNHH / cổ phần): bản in ghi **"Tổ chức:"** thay "Họ và tên:". Ghi chú của các thửa đất **liền nhau
  giống nhau** ở mục 1 gộp thành một ô. Tiêu đề mục II luôn là "II. Thông tin vị trí, nguồn gốc đất:".
- **Cỡ chữ và khổ giấy (1.0.07)**: tiêu đề (quốc hiệu, tiêu ngữ, tên cơ quan, tên văn bản, dự án, tiêu đề mục I-IV, hàng tiêu đề
  bảng) 16 pt đậm, nội dung 14 pt. Phương án chi tiết: A4 dọc, tỷ lệ in 72% (chỉ tràn vài dòng thì thu tới 70% cho vừa 1 trang),
  lề trái 0,8 cm, phải 0,3 cm, trên 1,0 cm, dưới 0,8 cm; cột Ghi chú 11,5 pt; mục I không kẻ viền, nhãn đậm, nội dung thường; số CCCD,
  số điện thoại lưu dạng chữ (Excel không gắn tam giác xanh); mỗi đoạn nguồn gốc đất thụt đầu dòng 8 khoảng trắng. **Bản dự thảo
  không in khối chữ ký** (Lập biểu - Kiểm tra - Phó Giám đốc), ghi "(DỰ THẢO)" dưới dòng số, để trống số / ngày. **Bảng tổng hợp: A3 ngang, tỷ lệ in cố định 55%**
  - cột chữ (họ tên, địa chỉ, nguồn gốc…) tự co / giãn cho bảng vừa đúng bề ngang A3; chỉ khi số tiền quá lớn không vừa thì in
  nhỏ hơn 55% (không để Excel tách cột sang trang riêng).
- **Khung bảng và định dạng số (1.0.09)**: bảng mục III của phương án chi tiết luôn được kẻ khung đầy đủ (hàng tiêu đề và viền ngoài
  đậm) và định dạng số chuẩn (đơn giá / thành tiền 720.000, tỷ lệ 80%) - kể cả khi mẫu in trên máy là mẫu cũ thiếu khung. Mẫu cũ thiếu
  khung / định dạng trong `%APPDATA%\PABT\mau_in` tự được bỏ qua (in theo mẫu chuẩn), trừ mẫu đã thay qua **Quản lý Mẫu in & Bản in**.
- **Máy chưa có thư mục mẫu in (1.0.07)**: bộ mẫu chuẩn (phương án chi tiết, bảng tổng hợp, đường kẻ) nhúng sẵn trong phần mềm -
  in được ngay. Mẫu đã sửa (Quản lý Mẫu in, gói .pabtcfg) vẫn được dùng trước.
- **Công cụ → Quản lý Mẫu in & Bản in… (Ctrl+Shift+M)**: 3 mẫu - chi tiết chính thức, chi tiết dự thảo (bản niêm yết; chưa thay
  thì dùng mẫu chi tiết chính thức + chữ DỰ THẢO), bảng tổng hợp - kèm trạng thái "Mẫu nhúng chuẩn trong RAM" / "Mẫu tùy chỉnh
  người dùng". **Thay thế bằng file Excel khác…**: nhận file PABT Excel (sheet IN_CHITIET / IN_BANGTONGHOP) hoặc mẫu một sheet có
  chỗ trống {…}; tự áp chuẩn (chi tiết A4 72% lề chuẩn, tổng hợp A3 55%) và dùng ngay lần in sau. **Xuất mẫu hiện tại ra Excel để
  chỉnh sửa…**, **Khôi phục mẫu chuẩn gốc** (mẫu tùy chỉnh cũ chuyển vào `mau_in\cu\`, không xóa).

## Máy cấu hình yếu, kéo thả file, sao lưu tự động (1.0.08)

- **Máy cấu hình yếu** (RAM dưới 4 GB hoặc CPU 2 nhân - phần mềm tự nhận ra): tắt hiệu ứng đổ bóng; nhận dạng chữ bản scan (OCR) chỉ
  dùng một luồng CPU để chuột / bàn phím không bị đơ; ảnh xem trước bản in tối đa 120 dpi (in thật vẫn đủ nét); tự trả bộ nhớ sau khi
  đóng cửa sổ lập phương án, sau khi xuất bản in hàng loạt.
- **Phóng to / thu nhỏ chữ (A+ / A−)**: các trang đang ẩn (Bảng tổng hợp, Tiến độ, Quyết định, cửa sổ hộ không có thay đổi chưa lưu,
  Niêm yết, Đơn giá) được đóng và dựng lại khi mở tới - đổi cỡ chữ nhanh hơn. Hộ đang sửa dở và trang Khái toán giữ nguyên.
- **Kéo thả từ Windows Explorer** vào cửa sổ phần mềm: file dự án `.larc` / `.pabt` (mở), gói cập nhật `.larcud` (cài), gói mẫu in &
  cấu hình `.pabtcfg` (cài), Excel `.xlsx` / `.xlsm` (nhập - file phương án chi tiết tự nhận ra).
- **Sao lưu tự động**: mỗi lần mở dự án để sửa, một bản sao được ghi vào `%APPDATA%\PABT\sao_luu_tu_dong\` (giữ 5 bản gần nhất
  mỗi dự án, tên file kèm ngày giờ). Cần khôi phục: mở bản sao đó rồi **Lưu dự án thành…**. Mở chỉ xem không sao lưu.

## Màn hình chính khi đã mở dự án - tổng quan dự án (1.0.07)

Bấm **Màn hình chính** (đầu menu trái) khi đang mở dự án: dải tên dự án / địa bàn / chủ đầu tư; 4 thẻ **Dự án mới**, **Mở dự án
(Ctrl+O)**, **Nhập file Excel**, **Nhập PA chi tiết từ Excel**; 4 chỉ số (quy mô: số hộ, số thửa, ha; tổng kinh phí - đất và tài
sản, hỗ trợ; tiến độ phê duyệt; bàn giao mặt bằng - cùng cách đếm với thẻ số liệu danh sách hộ); bên trái **hộ đang làm dở / chưa
phê duyệt** (nút **Lập PA →** hoặc bấm đúp mở thẳng hộ), bên phải **Đồng hồ pháp lý**: số ngày niêm yết còn lại của đợt đang niêm
yết, hạn đối thoại, số hộ vướng V1-V5, số hộ đang vận động / đủ điều kiện đề nghị cưỡng chế. Chưa mở dự án: màn hình chào như cũ.

**Thao tác bảng (1.0.07)**: cuộn mượt; sửa ô xong **Enter** ghi và xuống ô dưới, **Tab** sang ô bên phải; **Ctrl+D** chép giá trị ô
trên cùng của vùng chọn xuống các ô chọn bên dưới (chọn một ô: chép ô ngay trên). **Ctrl+S** / **Ctrl+Z** hiện thông báo nổi góc
dưới phải. Hộp thoại cao hơn màn hình: phần thân có thanh cuộn mảnh, hàng nút luôn nằm trong màn hình.

## Công cụ thực địa, chẩn đoán và cấu hình nghiệp vụ (0.9.87)
- **Cài đặt → Cấu hình nghiệp vụ…**: số ngày (niêm yết, đối thoại, thẩm định, thông báo thu hồi đất nông nghiệp / phi nông nghiệp,
  vận động trước cưỡng chế), căn cứ pháp lý, mức kinh phí tổ chức thực hiện và tỷ lệ phân bổ, ngưỡng kiểm tra, che CCCD bản dự
  thảo, thông tin cơ quan. Bấm Lưu là áp dụng ngay; "Khôi phục mặc định…" bỏ mọi sửa đổi. Quy trình 16 bước hiện thời hạn theo cấu hình.
- **Dữ liệu → Nhập bản vẽ CAD (.dxf)…**: chọn lớp ranh thửa, lớp ranh thu hồi (nếu có), số tờ; phần mềm đọc số thửa / diện tích /
  loại đất trong nhãn, đo diện tích hình và phần nằm trong ranh thu hồi, đối chiếu với hồ sơ; đánh dấu thửa nào cập nhật diện tích
  thu hồi theo bản vẽ. **Dữ liệu → Bản đồ thửa đất**: tô xanh thửa hộ đã đồng thuận, đỏ chưa đồng thuận, vàng chưa lấy ý
  kiến, xám thửa không có trong hồ sơ; bấm (không kéo) vào thửa mở hồ sơ hộ, ô "Số thửa → Enter" nhảy tới thửa, cuộn chuột phóng to.
- **Quét giấy tờ (OCR)…** (cửa sổ lập phương án, trang Dự toán): chọn ảnh chụp / PDF scan giấy chứng nhận, biên bản kiểm kê (cần
  Tesseract như đọc quyết định scan). Soát lại các ô rồi "Điền thông tin hộ & thửa" (trang Dự toán: "Thêm dòng đất") / "Đưa tài sản vào phương án…".
- **Ứng dụng điện thoại LARC Mobile** (Android / iPhone, chạy không cần mạng; ứng dụng phát hành riêng, không nằm trong bộ cài
  máy tính). Từ bản 1.2.0 ứng dụng mở vào màn hình **✨ AI Quét & Nói**, thanh đáy 4 chế độ (AI Quét & Nói · Hồ sơ & TS · Bản đồ GPS ·
  Xuất .JSON):
  - **📷 Chụp / Quét ảnh** (hai nút gọn một hàng từ bản 1.3.0): chụp mặt sau thẻ CCCD (mã QR) - điện thoại Android tự điền họ tên, số CCCD, năm sinh, địa chỉ; chụp biên
    bản - ứng dụng làm rõ chữ rồi mở ảnh để bạn chép hoặc 🎙️ đọc nội dung ngay dưới ảnh. iPhone chưa đọc được mã QR trong ứng dụng:
    giữ ngón tay trên chữ của ảnh để chép (Văn bản trực tiếp) hoặc đọc thông tin chủ hộ.
  - **🎙️ Nhập giọng nói**: đọc liền một mạch, ví dụ "chủ hộ Nguyễn Văn An, căn cước 0750…, tờ 12 thửa 45 cây lâu năm 1500 mét vuông,
    nhà 1 tầng khung bê tông mái tôn tường xây nền gạch men mở ngoặc 5 nhân 12 đóng ngoặc trừ mở ngoặc 2 nhân 3 đóng ngoặc, ống nhựa
    phi 114: 3300 mét, xoài trồng năm 2012: 650 cây". Ô **Phân tách dữ liệu thông minh** (chạy trên điện thoại, không cần mạng) tách
    thành từng mục có màu: hồ sơ hộ, đất, nhà (tự chọn loại theo kết cấu - chỉ là gợi ý, chọn lại được ngay trên thẻ), vật kiến trúc,
    cây (tính tuổi từ năm trồng), vật nuôi, kèm tạm tính tiền. Bỏ chọn mục sai rồi bấm **✔ Đưa vào Hồ sơ Hộ** (chưa chọn hộ thì tự tạo
    hộ mới theo họ tên đọc được). Lần đầu dùng giọng nói ứng dụng hỏi đồng ý: máy chưa có gói tiếng Việt ngoại tuyến thì tiếng nói được
    gửi tới máy chủ Google (Android) / Apple (iPhone, cần bật Siri và Đọc chính tả) để nhận dạng. Không muốn: gõ hoặc dán vào ô phân tách.
    Điện thoại báo chưa có bộ nhận dạng giọng nói (máy không có ứng dụng Google, máy giả lập như LDPlayer): bấm OK để mở CH Play cài
    **Dịch vụ lời nói của Google** (miễn phí), rồi tải gói tiếng Việt ngoại tuyến (Cài đặt → Google → Giọng nói); lần đầu ứng dụng hỏi
    quyền **Micro** - chọn Cho phép. Máy không có CH Play: dùng micro trên bàn phím hoặc gõ.
    Từ bản 1.3.1 mọi nút 🎙 mở **Trung tâm thu âm & nhập nhanh kiểm đếm** (không bật bàn phím): **🔴 Bấm thu âm trực tiếp** (iPhone: đọc
    từng câu, mỗi câu bấm lại), **📼 Ghi file âm thanh** (ghi giọng đọc lưu trên điện thoại theo hộ, nghe lại để chép biên bản - chạy cả khi
    iPhone tắt Đọc chính tả; file ghi âm không gửi kèm .json), **✨ Chèn mẫu đọc chuẩn**; bàn phím từ khóa 1 chạm 4 thẻ (Nhà QĐ 18/2026, Vật
    kiến trúc QĐ 18/2026, Cây trồng QĐ 48/2025, Số & Toán); **⚡ Đưa vào ô nhập & Tự động bóc tách ra bảng**, **📋 Chỉ chèn vào ô nhập**,
    **🗑️ Xóa trắng**. iPhone báo chặn nhận dạng (Edge / Chrome / ứng dụng trên Màn hình chính): dòng cảnh báo hướng dẫn bật Cài đặt → Cài đặt
    chung → Bàn phím → Bật Đọc chính tả, hoặc dùng Ghi file âm thanh / bàn phím từ khóa.
  - Làm nhiều hộ liền tay (từ bản 1.4.0): **⚡ Đưa vào Hộ & Sang hộ kế ▶** (cạnh ✔ Đưa vào Hồ sơ Hộ) lưu vào hộ đang chọn, ghi tọa độ GPS
    nếu hộ chưa có, rồi chuyển sang hộ kế tiếp CHƯA kiểm đếm; **📋 Chép mẫu hộ trước** điền lại các mục nhà, vật kiến trúc, cây của hộ vừa
    làm (không chép họ tên, tờ / thửa) - chỉ sửa kích thước / số lượng rồi đưa vào; nút **📍** trên thanh chọn hộ ghi ngay tọa độ GPS +
    VN-2000 cho hộ đang chọn (**📍✓** = hộ đã có tọa độ). Đọc giọng nói kết thúc bằng **"đưa vào hồ sơ hộ"** hoặc **"chốt hộ sang hộ kế"**
    thì ứng dụng tự bấm nút tương ứng (khi không còn mục nào cần xem lại). Máy tách đúng hơn các câu: "Nhà gác lửng khung cột bê tông cốt
    thép tường sơn nước…" (một mục nhà, không tách chữ "sơn" thành cây), "Mộ xây gạch có mái che 2 ngôi", tên giống cây ("Sầu riêng ghép",
    "Bưởi da xanh", "Xoài cát Hòa Lộc", "Tràm bông vàng" = Keo lá tràm), một thửa nhiều loại đất ("tờ 5 thửa 108 đất ONT 120m2, đất CLN 850m2").
  - **🗺️ Bản đồ GPS**: chọn nền ngay trên bản đồ - **Vệ tinh**, **Vệ tinh + tên** (tên đường, địa danh), **Đường phố**, **Địa hình**, **Lưới**
    (có mạng thì mặc định Vệ tinh + tên); thanh **Độ đậm thửa** chỉnh độ che của màu thửa trên ảnh. Trước khi ra hiện trường (có Wi-Fi):
    mở bản đồ, chọn Vệ tinh, bấm **💾 Lưu ảnh nền khu dự án** - ứng dụng lưu ảnh khu các thửa vào máy để xem khi mất sóng (**Xóa ảnh nền
    đã lưu** để giải phóng bộ nhớ). Nền Đường phố chỉ xem khi có mạng. Chưa có thửa nào (kiểm đếm độc lập): bản đồ mở toàn cảnh Việt Nam
    và tự xin vị trí rồi bay tới chỗ đang đứng; iPhone báo chưa cho phép định vị: Cài đặt → Quyền riêng tư & Bảo mật → Dịch vụ định vị →
    bật, chọn trình duyệt đang dùng → Khi dùng ứng dụng. Có bản mới trên mạng: ứng dụng hiện dải **🔄 Đã có bản LARC Mobile mới** - bấm để
    cập nhật (dữ liệu đã ghi giữ nguyên). File KML / KMZ đã nạp được lưu trên máy theo dự án (từ bản 1.4.0): thoát ứng dụng mở lại vẫn còn;
    **🗑️ Xóa KML đã nạp** để thay bản đồ khác. Từ bản 1.4.2 (màn hình dọc) bản đồ chiếm trọn màn hình - ẩn tiêu đề, thanh chọn hộ, thanh
    số liệu; các công cụ (nạp / xóa KML, bật định vị, vừa khung, thửa hộ này, tìm tờ/thửa, độ đậm, lớp, lưu ảnh nền, chú giải, bảng tra
    cứu) nằm trong nút **☰** ở cột nút bên phải bản đồ; nút **◎** về vị trí đang đứng (bật định vị nếu chưa bật). Chạm vào bản đồ hoặc
    bấm ✕ Đóng để đóng ngăn công cụ; sang thẻ khác thì các thanh hiện lại.
  - Mục **Ảnh chụp** (từ bản 1.4.1): bấm **📷 Chụp ảnh** một lần rồi chụp liên tiếp nhiều trang biên bản / hiện trạng - trên trình duyệt / iPhone
    máy ảnh mở ngay trong ứng dụng (nút chụp tròn, hiện số ảnh đã chụp), xong bấm **✔ Xong**; bản Android: chụp xong một ảnh máy ảnh tự mở lại,
    bấm Quay lại để dừng. Máy không mở được máy ảnh trong ứng dụng (chưa cho phép máy ảnh): dùng nút **📷 Chụp tiếp** - mỗi lần một ảnh.
  - Từ bản 1.4.3 (gọn màn hình điện thoại): bỏ thanh số liệu (Đất / Nhà / VKT / Cây / Ảnh / Tạm tính) - số dòng từng mục hiện trên ô mục
    con (**Hồ sơ · Nhà · Vật KT · Cây, VN · Ảnh**, 5 ô vừa một hàng), tạm tính tiền ở góc "Tóm tắt hộ đang chọn"; bỏ nút **🎙️ Đọc** ở từng
    mục - đọc giọng nói ở màn hình **AI Quét & Nói** (🎙️ Nhập giọng nói / Đọc thêm). Điện thoại hẹp: nút trên thanh chọn hộ chỉ còn biểu
    tượng (+ thêm hộ, 💾 lưu) để ô chọn hộ hiện được tên.
  - Xoay ngang điện thoại (hoặc bấm **🔄 Xoay ngang** - từ bản 1.4.0 có cả trên điện thoại)
    thì màn hình chia 2 cột: công cụ AI bên trái, chi tiết bên phải.
  Các mục của **Hồ sơ & TS**: **Hồ sơ & Đất** (chủ hộ / người nhận khoán, người sử dụng, CCCD, năm sinh, thửa địa chính hoặc tiểu khu / khoảnh /
  lô, nút lấy tọa độ GPS tại chỗ); **Nhà ở** (chọn loại nhà theo bộ đơn giá, bấm chọn kết cấu khung / tường / mái / trần / nền / cửa,
  diện tích ghi được "(4 x 6,7) + (2 x 3)", "(5x12)-(2x3)", "7m x 2m x 2" (dài x rộng x số cái) - hàng phím tắt x ( ) + - , dưới ô;
  phần mềm GỢI Ý loại nhà theo tiêu chí kết cấu Phụ lục Ia QĐ 18/2026/QĐ-UBND - số tầng, khung, tường, mái, trần, nền, cửa; cần ít nhất 2 tiêu chí khớp, người kiểm đếm quyết định); **Vật KT** (gõ vài chữ để chọn mục bộ đơn giá; dòng nhiều cỡ ống ghi cả vào tên); **Cây
  trồng** (loài + năm trồng + đường kính / chu vi - nút chọn nhanh theo đúng khoảng đường kính / tuổi của bộ đơn giá, hoặc ghi nhanh
  "Tràm 35c/15cm"); **Ảnh biên bản** (nút **Chụp ảnh** / **Chọn ảnh trong máy**, chạm ảnh để phóng to và chép lại nội dung ngay cạnh
  ảnh, "Làm rõ chữ" xóa dòng kẻ chấm; dòng biên bản tự xếp vào nhà / vật KT / cây ngay trên điện thoại); **Bản đồ** (nền ảnh vệ tinh
  hoặc bản đồ đường khi có mạng - chỉ tải ảnh nền theo vị trí đang xem, không gửi số liệu hộ dân; thửa của dự án đã nhập bản vẽ, nạp
  thêm file KML / KMZ, nút **Thửa hộ này**, **Tâm GPS**, ô tìm tờ / thửa; bật định vị: biết đang đứng trong thửa nào hoặc cách thửa gần
  nhất bao xa, hướng nào; chạm thửa mở hồ sơ hộ; tọa độ hiện cả VN-2000. Từ bản 1.3.0 đọc đủ bản vẽ KML / KMZ xuất từ MicroStation /
  gCadas: lưới thửa và ranh (đường), số thửa, loại đất, diện tích, diện tích thu hồi, mốc ranh (DN.T…, DN.P…), ghi chú quy hoạch / hành lang,
  đúng màu như Google Earth; chữ tiếng Việt lỗi font được khôi phục; vòng tròn nhỏ quanh cọc mốc chỉ hiện khi phóng gần. Công tắc bật / tắt
  4 lớp, nút + / − / ⛶ trên bản đồ; chạm số thửa, mốc, ghi chú hay đường để xem thuộc tính (cả tọa độ VN-2000) - nút **➕ Đưa thửa đất này vào
  hồ sơ hộ đang chọn** điền sẵn ô Đất (kiểm tra số tờ, bấm Thêm), mốc thì ghi vào ghi chú hộ; bảng **Tra cứu đối tượng** dưới bản đồ lọc thửa /
  mốc / ghi chú / đường, nút **🎯 Xem** bay tới); **Xuất .JSON** (một hộ hoặc cả dự án, có / không kèm ảnh;
  Mở / Lưu / Xóa từng hộ). Dòng nào trong mọi bảng cũng có nút **Sửa**. Thành tiền tạm tính trên điện thoại chỉ để xem - máy tính áp
  giá lại khi nhập.
  - **Kiểm đếm ngay, chưa cần file dự án**: màn hình đầu → **Bắt đầu kiểm đếm ngay** (ứng dụng có sẵn danh mục đơn giá); hộ ghi mới
    được tạo thành hộ mới khi nhập vào dự án trên máy tính. Đang mở dự án mà bấm **Dự án**: **← Quay lại dự án đang mở**.
  - **Android**: cài file `LARC_Mobile_<phiên bản>.apk` (Android 7.0 trở lên; máy hỏi "cho phép cài ứng dụng không rõ nguồn" thì
    bật cho ứng dụng đang mở file - Zalo, Tệp…). Lần đầu bật định vị, máy hỏi quyền vị trí: chọn Cho phép. Phím **Quay lại** của
    Android đóng ảnh đang xem / về thẻ đầu, không thoát mất số liệu. Xuất .JSON: chọn **Gửi đi** (Zalo, email, Drive) hoặc **Lưu vào thư mục**.
  - **iPhone / iPad**: bản PWA `LARC_Mobile_PWA_<phiên bản>.zip` - đặt các file trong gói lên một địa chỉ **HTTPS** (xem
    HUONG_DAN_CAI_DAT.txt trong gói), mở bằng **Safari** → Chia sẻ → **Thêm vào MH chính**; sau lần mở đầu chạy không cần mạng.
    Xuất .JSON mở bảng chia sẻ (Zalo, **Lưu vào Tệp**…).
  - **Cài cho nhiều người** (miễn phí, không qua App Store): gói `LARC_Mobile_Web_<phiên bản>.zip` - tải cả thư mục `tai_len` lên
    GitHub Pages (hoặc Netlify / Cloudflare Pages) theo HUONG_DAN.txt trong gói, rồi gửi mọi người trang `cai-dat.html` có **mã QR**:
    quét bằng máy ảnh iPhone → mở Safari → Thêm vào MH chính; điện thoại Android tải file .apk ngay trên trang đó. Trang chỉ chứa ứng
    dụng trống và danh mục đơn giá, không có số liệu hộ dân.
  - Mở được nhiều dự án (nút **Dự án** góc trên); mở file dữ liệu mới của cùng dự án không mất số liệu đã ghi. Số liệu nằm trong ứng
    dụng trên điện thoại đó: gửi về máy tính thường xuyên, gỡ ứng dụng là mất số liệu chưa gửi.
- **Công cụ → Phiếu kiểm đếm thực địa…** (phần máy tính): (1) **Xuất dữ liệu cho ứng dụng điện thoại…** - file `.json` (hộ, thửa,
  danh mục đơn giá, bản đồ thửa) gửi sang điện thoại (Zalo, email, cáp USB) → trong ứng dụng **Chọn file dữ liệu dự án…**.
  (2) **Nhập kết quả kiểm đếm (.json)** - phần mềm tìm hộ theo CCCD, tờ / thửa (lô rừng), họ tên; hộ chưa có thì hỏi thêm hộ mới; các
  dòng thêm vào phương án như "Dán danh sách tài sản" (khớp danh mục đơn giá; không khớp thành hạng mục ngoài danh mục); ảnh gửi kèm lưu
  vào thư mục **Anh_kiem_dem\<mã hộ>** cạnh file dự án; tọa độ GPS ghi vào ghi chú hộ (kèm X / Y VN-2000). File kết quả của phiếu .html
  các bản trước vẫn nhập được. (3) **Gắn ảnh hiện trạng** - chọn thư mục ảnh; ảnh đặt tên theo **số CCCD**, **họ tên**
  (Nguyen_Van_A_nha.jpg) hoặc **HO<số thứ tự>** (HO012_cay.jpg) được gắn vào hộ; bảng hiện số ảnh mỗi hộ, bấm đúp mở ảnh.
- **Trợ giúp → Chẩn đoán & sửa lỗi hệ thống…**: bảng kiểm tra máy (thư mục dữ liệu, ổ đĩa, Microsoft Excel, Tesseract, chứng chỉ
  HTTPS). **Kiểm tra & sửa file dự án…**: sao lưu file vào thư mục `SaoLuu_SuaLoi` cạnh file, gỡ file khóa cũ (máy kia tắt đột ngột -
  khóa của máy ĐANG mở thì không gỡ), dựng lại chỉ mục, nén file; file hỏng trang dữ liệu thì chép mọi dòng đọc được sang file mới
  và báo bảng nào có thể mất dòng. Dự án đang mở được đóng trong lúc sửa và mở lại sau đó. **Xuất gói chẩn đoán (.zip)**: thông tin
  máy, nhật ký lỗi, hồ sơ địa phương và bản sao dự án ĐÃ ẨN DANH (họ tên thành "Hộ kiểm thử 0001…", xóa CCCD, điện thoại, nguồn gốc
  đất, ý kiến dân, nhật ký; giữ diện tích, đơn giá, loại đất, tỷ lệ để tái hiện lỗi) - gửi cho người hỗ trợ. Hộp báo "lỗi không
  mong muốn" cũng có nút này.
- **CSDL v16**: file dự án mở bằng 0.9.87 được nâng lên v16; máy dùng bản 0.9.86 trở về trước sẽ báo "file được tạo bằng phiên bản
  phần mềm mới hơn" - cập nhật mọi máy dùng chung dự án (gói .pabtcn hoặc bộ cài).

## Nhật ký kiểm toán và Bác sĩ hồ sơ (0.9.86)

**Nhật ký kiểm toán** (menu **Dữ liệu → Nhật ký kiểm toán…**, hoặc chuột phải một hộ): mỗi thay đổi số liệu được ghi tự động vào chính
file dự án - thời gian, người sửa (tài khoản máy chủ LAN, không thì tài khoản Windows), tên máy, hộ, đối tượng (thửa / dòng phương án /
mục đơn giá), trường, **giá trị cũ -> mới**:
- thêm / sửa / xóa hộ (họ tên, CCCD, địa chỉ, nhân khẩu, tái định cư…) và thửa (số tờ, số thửa, loại đất, diện tích thu hồi, nguồn gốc);
- **Lưu phương án hộ**: từng dòng thêm / xóa, từng trường sửa (diện tích, giá, hệ số K, tỷ lệ, số lượng, đơn giá…);
- sửa đơn giá danh mục, giá đất của dự án (nạp lại cả bộ đơn giá ghi ở nhật ký thao tác, không ghi từng mục).
Không ghi: số liệu gốc lúc tạo dự án / nhập Excel, phương án phần mềm tự lập. Nhật ký **không sửa, không xóa được** (kể cả mở file bằng
công cụ SQLite khác); Hoàn tác (Ctrl+Z) không xóa nhật ký - lần hoàn tác cũng được ghi. Lọc theo hộ, thời gian, từ khóa; **Xuất Excel…**
(A4 ngang) để nộp đoàn thanh tra / kiểm toán. Dự án mở chỉ xem: xem được, không ghi.

**Kiểm tra lỗi → nhóm "Bác sĩ hồ sơ"**: diện tích bồi thường ở mục 1 **lớn hơn** diện tích thu hồi của thửa (lỗi); tỷ lệ chất lượng / bồi
thường của đất, nhà, công trình, cây, vật nuôi vượt 100% (lỗi - hỗ trợ như đào tạo 150% không tính); có hỗ trợ theo nhân khẩu mà hộ chưa nhập
số nhân khẩu (lỗi) hoặc dòng ổn định đời sống khác số nhân khẩu của hộ; nhân khẩu trên 20 (ngưỡng trong hồ sơ địa phương); diện tích đất ở
bồi thường vượt **hạn mức đất ở** - mặc định CHƯA kiểm tra, ghi hạn mức (m²) theo quy định của tỉnh vào hồ sơ địa phương
`quy_tac_kiem_tra.han_muc_dat_o_m2` (`xa` / `phuong` / `dac_khu` theo cấp địa bàn của dự án). Trùng số CCCD giữa hai hộ: nhóm Thông tin hộ.

## Hồ sơ địa phương và gói mẫu in & cấu hình (0.9.85)

Những gì khác nhau giữa các địa phương / đơn vị nằm trong **một file JSON** - `pabt_profile.json`:

| Mục | Nội dung | Mặc định đóng kèm |
|---|---|---|
| `co_quan` | Tên tổ chức làm nhiệm vụ bồi thường, đơn vị trực thuộc, địa chỉ; thông tin điền sẵn trên bản in (đơn vị cấp trên, tên trên tiêu đề, ký hiệu số phương án, chức vụ người ký) | Để trống (đơn vị tự nhập) |
| `can_cu_phap_ly` | Căn cứ kinh phí tổ chức thực hiện, căn cứ hạn thẩm định, các dòng "Căn cứ …" chung của tờ trình mặc định | QĐ 08/2025, QĐ 30/2025, 42/2025, 18/2026 |
| `thoi_han` | Số ngày mặc định: thẩm định 15, đã thông báo thu hồi đất NN 60 / PNN 120, vận động 10, niêm yết 10, đối thoại 30 (mỗi dự án vẫn sửa riêng được) | QĐ 18/2026 |
| `kinh_phi_to_chuc` | Mức tối đa theo tuyến / dự án khác, làm tròn (`-3` = đến nghìn đồng), phân bổ (tên, %; tổng phải 100%) | 3,5% / 2,5%; 85% / 15% |
| `ban_in` | Bản dự thảo tự che CCCD; căn chỉnh ô nguồn gốc đất | che; căn đều, canh trên |
| `mau_in` | Vị trí cột của mẫu phương án chi tiết (A-H, cột loại dòng AD) và bảng tổng hợp (dòng dữ liệu đầu 13, 25 cột A-Y, các cột cộng) | mẫu Đồng Nai |

- File mặc định nằm trong phần mềm (`pabt\pabt_profile.json`, đi theo gói cập nhật .pabtcn). Máy dùng ở địa phương khác đặt
  `%APPDATA%\PABT\pabt_profile.json` - **chỉ cần ghi các mục khác mặc định** (phần còn lại lấy mặc định). Số tỷ lệ ghi trong ngoặc kép
  (`"3.5"`) để tính bằng số thập phân chính xác. File sai (JSON hỏng, phân bổ không đủ 100%, chữ cột sai…): phần mềm báo khi mở và dùng
  mặc định; **Trợ giúp → Giới thiệu** ghi hồ sơ đang dùng.
- **Công cụ → Xuất gói mẫu in & cấu hình…**: đóng hồ sơ địa phương đang dùng + mẫu in (IN_CHITIET, IN_BANGTONGHOP, mẫu riêng, đường kẻ) +
  mẫu tờ trình đã sửa thành **một file `.pabtcfg`**. Gửi qua Zalo / email.
- Máy nhận: **bấm đúp file `.pabtcfg`** (bộ cài từ 0.9.85 đăng ký đuôi file) hoặc **Công cụ → Nhập gói mẫu in & cấu hình…** → xem danh sách
  → Có. Phần mềm kiểm tra gói (mã SHA-256 từng file, chỉ nhận mẫu .xlsx / .docx / .xml không có macro và hồ sơ hợp lệ), sao lưu mẫu cũ vào
  `%APPDATA%\PABT\sao_luu_mau\<giờ>` (giữ 10 lần gần nhất) rồi thay - dùng ngay, không cài lại phần mềm.
- **Công cụ → Tạo gói cấu hình cho nhiều đơn vị…** (cài phần mềm cho chi nhánh / đơn vị tỉnh khác, không phải nhập tay trên từng máy):
  1. Bấm **Tạo file Excel mẫu…** → điền sheet `Don_vi`, **mỗi dòng một đơn vị**: tên tổ chức (bắt buộc), trực thuộc, địa chỉ, đơn vị cấp
     trên, tên đơn vị trên tiêu đề bản in, đơn vị lập phương án, địa danh dòng ngày tháng, ký hiệu số, chức vụ / họ tên người ký, người
     lập, người kiểm tra (sheet `Huong_dan` giải thích từng cột). Có thể dùng file `.json` thay Excel.
  2. Chọn **Hồ sơ nền**: cấu hình nghiệp vụ của máy này (chi nhánh cùng tỉnh: dùng chung căn cứ pháp lý, mốc thời hạn, tỷ lệ kinh phí),
     hồ sơ mặc định (trung tính), hoặc file hồ sơ `.json` của tỉnh khác. Thông tin cơ quan luôn lấy theo từng dòng - ô để trống không mang
     tên đơn vị của máy bạn sang.
  3. Bảng xem trước ghi **Đạt / Lưu ý / Thiếu** từng dòng → **Tạo gói**: mỗi đơn vị một file `LARC_CauHinh_<tên>.pabtcfg` trong thư mục
     `Goi_cau_hinh` cạnh file danh sách. Cấu hình máy bạn **không đổi**. Gửi đúng gói cho đúng đơn vị; máy nhận bấm đúp gói như trên.
  - Dòng lệnh: `PABT.exe mau-goi-don-vi <file.xlsx>` (file mẫu) và `PABT.exe tao-goi-don-vi <danh_sach.xlsx> [<thư mục ra>]
    [--nen may|mac_dinh|<hồ sơ.json>] [--kem-mau]`.

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
- Ô **Vị trí** mục 1 khi lập phương án xổ các tuyến của bảng đang dùng (địa bàn dự án đứng đầu).
- **Cập nhật giá đất** (menu Bảng giá & chính sách, hoặc Bộ đơn giá → Giá đất): nhập xã / phường và tỉnh, bấm **Tải từ web**
  (Công báo Đồng Nai, hoặc vbpl.vn nếu tỉnh khác). Web không ra bảng đơn giá thì chọn file **Excel, Word, PDF hoặc CSV**.
  Cột tối thiểu **Tên đường** và **Đất ở** hoặc **Đơn giá** (đồng/m²). Mỗi sheet Excel một địa bàn. Bấm **Dùng bảng này**:
  bốn địa bàn gắn sẵn không còn hiện ở ô Vị trí và tra cứu — chỉ còn địa bàn trong file. **Dùng lại bảng gắn sẵn** (trong cùng hộp)
  trả về Xã Trị An, Xã Tân An, Xã Phú Lý, Phường Tân Triều. File nằm ở `%APPDATA%\PABT\bang_gia_dat.json` (không ghi vào bộ cài,
  không xóa đơn giá đã nhập trong phương án). Xuất bảng hiện tại ra Excel để lấy đúng mẫu cột: **Xuất bảng giá đất ra Excel…**.
- Số liệu chép từ bản PDF đóng dấu của Nghị quyết (Phụ lục I trang 172–205, 1143–1214; Phụ lục III trang 1672–1707, 2700–2775) và
  kiểm tra chéo bằng nhận dạng chữ; khi dùng làm căn cứ chính thức nên đối chiếu văn bản gốc. Dữ liệu ở `pabt/bang_gia_nq28.json`.

## Dự thảo PABT (niêm yết, lấy ý kiến, đối thoại)

Menu **Lập phương án → Dự thảo PABT**. Số trên sáu thẻ là hộ của dự án đang mở.

1. Thẻ **Hộ vướng**: hộ chưa đủ điều kiện, hoặc nhóm V1 chờ UBND xã xác nhận nguồn gốc, V2 tranh chấp ranh, V3 thừa kế chưa có đại diện, V4 chờ đo lại, V5 chờ thẩm định. Những hộ này không vào đợt lấy ý kiến. **Gợi ý đủ điều kiện** chỉ đánh dấu hộ đã có tên, nguồn gốc thửa, không tranh chấp và đã có phương án — vẫn phải đối chiếu hồ sơ trước khi niêm yết.
2. **Tạo đợt**: ngày kết thúc niêm yết = ngày bắt đầu + 10 ngày. **Đưa hộ đủ điều kiện vào đợt**.
3. Ba tỷ lệ không thay nhau: **theo đợt** (đồng ý / hộ của đợt), **lũy kế đã niêm yết**, **độ bao phủ cả dự án** (đồng ý / tổng hộ). Đợt 1 đạt 93% không có nghĩa cả dự án đã xong.
4. Bấm đúp hộ để ghi ý kiến: Đồng ý / Ý kiến khác / Không đồng ý. **Ngày họp lấy ý kiến** đặt hạn đối thoại + 30 ngày. Hộ chưa đồng ý chuyển sang đợt sau; ý kiến đợt cũ giữ nguyên.
5. **Xuất bảng niêm yết** che CCCD. **Xuất danh sách đôn đốc** ra Excel các hộ V1, V2 để lập công văn — phần mềm không tự ký công văn.

## Bộ đơn giá tích hợp (cố định)

**Bộ đơn giá…** xem toàn bộ: 5.668 đơn giá tài sản, cây trồng (QĐ 48/2025 sửa đổi bởi QĐ 66/2025; nhà, công trình theo
QĐ 18/2026 sửa đổi bởi QĐ 53/2026), 39 khoản chính sách hỗ trợ, tái định cư (QĐ 42/2025), tham số và **hạn mức giao đất nông nghiệp
khu vực Đông Nam Bộ** (Điều 176 Luật Đất đai 2024: cây hằng năm, NTS 3 ha; cây lâu năm 10 ha vùng đồng bằng; rừng 30 ha), biểu
**thưởng bàn giao mặt bằng**, quy ước giá tương đương và 17 văn bản căn cứ (gồm dự thảo sửa đổi QĐ 42/2025 đang theo dõi).

- **Sửa một mục** (thêm / sửa / xóa / thay thế): nút **Sửa bộ đơn giá**. Cần quyền quản trị — tài khoản **quản trị máy chủ LAN**,
  hoặc **mật khẩu quản trị bộ đơn giá** trên máy này (lần đầu mở khóa sẽ đặt mật khẩu, ít nhất 6 ký tự; đổi ở cùng menu).
  Người đã đăng nhập máy chủ nhưng không phải quản trị thì không sửa được. Sửa ghi vào bản bộ đơn giá trên máy
  (`%APPDATA%\PABT`); dự án đang mở muốn dùng mục mới thì bấm **Áp bộ đơn giá vào dự án đang mở**.
- Thẻ **Quy ước giá tương đương** khi đang mở dự án hiện quy ước **của dự án** (đồng bộ với **Đơn giá riêng**). Xóa / sửa quy
  ước ở Đơn giá riêng rồi đóng hộp thoại: danh sách thẻ này tự cập nhật. Sửa quy ước của dự án vẫn dùng **Đơn giá riêng**.
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
  scan / ảnh chụp: tự nhận dạng chữ bằng **Tesseract OCR đóng kèm phần mềm** (tiếng Việt, từ 0.9.99 - không cần cài gói ngôn ngữ
  của Windows, không gửi file ra ngoài; ~1-2 giây / trang). Windows 32-bit không chạy được bộ nhận dạng: dán chữ hoặc chuyển sang
  Excel / Word trước.
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
- **An toàn khi nhận file từ ngoài** (từ 0.9.16 không còn màn hình riêng): Word / Excel do PABT tự mở luôn tắt macro; kết nối
  mạng chỉ chấp nhận chứng chỉ HTTPS hợp lệ (TLS 1.2+); file nén / XML độc bị chặn; gói cập nhật sai mã SHA-256 (hỏng, bị sửa)
  bị từ chối. Quét virus do Microsoft Defender của máy đảm nhận: giữ Defender luôn bật, cập nhật.
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
(tên đơn vị khai ở Cài đặt → Cấu hình nghiệp vụ → Cơ quan; để trống thì không hiện), dòng trực thuộc và địa chỉ, cùng phiên bản đang chạy ở góc phải
(tên đơn vị, ký hiệu số phương án cũng được điền sẵn khi lập dự án mới). Màn hình Dự án mới có băng tổ chức tương tự.

Dưới băng tiêu đề (từ 0.9.23): **thanh menu** Tệp tin / Dữ liệu / Công cụ / Trợ giúp (tạo, mở, lưu, đóng dự án; nhập dữ liệu;
mẫu in, bộ đơn giá; hướng dẫn F1, cập nhật phần mềm, giới thiệu) và **menu bên trái** theo 16 bước của Mục IV QĐ 18/2026: nút
**Màn hình chính** riêng, rồi 6 nhóm - **1. Khái toán & dự toán**, **2. Dự án triển khai** (Thông tin dự án, Danh sách hộ và Thửa),
**3. Lập phương án** (Lập phương án chi tiết, Niêm yết & Lấy ý kiến, Kiểm tra lỗi pháp lý, Đối chiếu số liệu),
**4. Tổng hợp & trình duyệt** (Bảng tổng hợp kinh phí, Đợt trình thẩm định, Xuất hồ sơ & Bản in), **5. Phê duyệt & bàn giao**
(Quyết định phê duyệt, Tiến độ chi trả & Bàn giao), **6. Đơn giá & bảng giá** (Đơn giá bồi thường, Đơn giá
đặc biệt, Bảng giá đất - 0.9.88 chuyển xuống cuối: các nhóm làm hằng ngày lên trên). Lần đầu mở, nhóm 2, 3, 4 mở sẵn; nhóm 1, 5, 6
đóng. Chưa mở dự án: các lệnh nhóm 3, 4, 5 và Đơn giá đặc biệt mờ; Đơn giá bồi thường, Bảng giá đất vẫn tra cứu được. Bấm tên nhóm
để đóng / mở (phần mềm nhớ). Mỗi lệnh là
MỘT lệnh dùng chung cho menu, thanh công cụ, chuột phải (cùng trạng thái tắt khi chỉ xem). Lệnh với "hộ đang chọn" (Lập phương án,
Trạng thái hộ, Đợt trình, In / Xuất) lấy hộ chọn **trên trang đang xem** (Danh sách hộ, Bảng tổng hợp kinh phí, Quyết định phê duyệt,
Tiến độ chi trả & Bàn giao - cả ở chế độ Thửa còn vướng).
**Màn hình chính** / màn hình chào: 3 nút lớn (Dự án mới, Mở dự án, Nhập Excel), **Đóng dự án** / **Xóa dự án** khi đang mở file;
góc dưới phải có liên kết **Hướng dẫn sử dụng (F1)** (cùng lệnh menu Trợ giúp),
danh sách **dự án làm việc gần đây** (nhấp đúp hoặc **Mở dự án đã chọn** để thay dự án — không thoát phần mềm; **Xóa khỏi danh
sách** giữ file; **Xóa file dự án** xóa hẳn `.pabt`, thư mục bản in giữ nguyên). Tệp tin → **Xóa dự án…** cùng lệnh.

Trên danh sách hộ có bộ lọc **Đợt** (tất cả / chưa xếp đợt / từng đợt), **Trạng thái** (chưa / đã lập PA, chưa / đã phê duyệt,
đã phê duyệt chưa chi trả, đã chi trả chưa bàn giao, đã bàn giao, có ghi chú…) và ô **Tìm** (không cần dấu, tìm cả ghi chú); bên
phải ghi số hộ và tổng tiền đang lọc. Danh sách có thêm các cột **Đợt trình, Phê duyệt, Chi trả, Bàn giao MB, Ghi chú theo dõi**;
nhấp đúp ô Ghi chú theo dõi để ghi tiến độ của hộ (lưu ngay vào file dự án), nhấp đúp ô khác để mở phương án.
Màn hình hẹp (laptop 1366 px, màn hình phóng to 125%…) thì các nhóm tự xuống dòng và băng tiêu đề tự cao lên, cửa sổ không tràn ra
ngoài màn hình; cửa sổ mở vừa màn hình đang dùng.

**Menu dọc bên trái** là giao diện chính từ 0.9.3: các lệnh thành một cột bên trái theo nhóm, nút **Thu gọn menu** chỉ để lại
biểu tượng (rê chuột hiện tên lệnh); danh sách hộ dùng gần trọn chiều cao. Muốn dùng thanh nút phía trên như bản cũ: chạy
`PABT.exe --menu-tren`.

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

Chọn một hộ rồi bấm **Lập phương án hộ…** - thẻ **Thông tin hộ, thửa đất** (hoặc **Thêm hộ…** để tạo hộ mới):

- Sửa họ tên, CCCD, ngày / nơi cấp, địa chỉ, điện thoại, pháp lý, tranh chấp, tái định cư, trạng thái, ghi chú.
- Bảng **thửa đất thu hồi**: nhấp đúp ô để sửa tờ, thửa, loại đất, DT thu hồi (`143,8`, `1.070`), nguồn gốc, vị trí;
  **Thêm thửa**, **Xóa thửa** (thửa đang có dòng bồi thường đất thì hỏi lại; các dòng đó còn lại, không gắn thửa).
- **Tách theo loại đất**: thửa ghi `ONT+CLN` tách thành một dòng ONT và một dòng CLN để chia diện tích theo từng loại đất
  (mục 1 tra được giá đất đúng loại). Cùng tờ, thửa nhưng khác loại đất là hợp lệ.
- **Chuyển thửa sang hộ khác…**: chuyển thửa cùng các dòng bồi thường đất gắn với thửa.
- **Gộp hộ khác vào hộ này…**: dùng khi một người bị tách thành hai hộ (cùng tên khác địa chỉ…); danh sách chọn đưa hộ
  cùng họ tên lên đầu (★). Thửa, phương án của hộ kia chuyển sang, ô còn trống được điền từ hộ kia, hộ kia bị xóa.
- **Xóa hộ…**: xóa hộ cùng thửa và phương án (hỏi lại; xóa nhầm bấm **Hoàn tác** - Ctrl+Z - ở cửa sổ chính). Xóa nhiều hộ
  một lần: chọn trên danh sách hộ (giữ Ctrl / Shift) rồi **Xóa hộ** ở thanh công cụ trên danh sách (chỉ sáng khi đang chọn
  hộ), chuột phải, hoặc phím **Delete**.
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
thứ tự 6 thẻ, mỗi thẻ có nút **◀ Trở lại** / **Tiếp theo ▶**; lưu bằng nút **Lưu (Ctrl+S)** trên cùng cửa sổ.

**Dán danh sách tài sản (Ctrl+Shift+V)**: nút xanh ở hàng nút trên cùng, dùng được ở mọi thẻ (cùng hộp với nút "Dán danh sách…" của
Khái toán & dự toán). **Gõ tay mỗi dòng một tài sản: `Tên tài sản, công trình` ␣ `Đơn vị tính` ␣ `Số lượng`** (cách nhau dấu cách),
ví dụ `Nhà tạm m2 4*5` → tên "Nhà tạm", ĐVT m², số lượng **20** (phép tính tự tính; nhân bằng `*` hoặc `x`, có ngoặc, số lẻ dấu phẩy:
`Sân bê tông m2 (4+2)*3,5` = 21). Có tỷ lệ thì thêm cuối dòng: `Mít 6 năm cây 3 80%`. Tên có số / mã (`Nhà cấp 4 mái tôn`, `Lưới B40`,
`Ống D110`) không bị cắt nhầm vì phần mềm đọc từ cuối dòng: số lượng → ĐVT ngay trước → phần còn lại là tên. Chép bảng tài sản từ Excel / Word
(các cột Tên, ĐVT, Số lượng, Tỷ lệ, Ghi chú) rồi bấm nút hoặc **Ctrl+Shift+V**: nếu bộ nhớ đệm có bảng (nhiều dòng hoặc nhiều
cột cách nhau Tab) thì hộp mở ra đã **điền sẵn và Phân loại** (dòng nền vàng nên xem lại loại); không thì mở hộp trống để dán /
gõ. Bấm **Thêm vào phương án**: từng dòng vào đúng mục Nhà, công trình / Cây trồng / Vật nuôi / Hỗ trợ và tổng tiền phương án
tính lại ngay (chưa lưu cho tới khi bấm **Lưu**).

1. **Thông tin hộ, thửa đất**: họ tên, CCCD, ngày cấp, nơi cấp, điện thoại, địa chỉ, pháp lý, tranh chấp, ghi chú và bảng thửa
   (tờ, thửa, loại đất, DT thu hồi, nguồn gốc, vị trí); tách thửa theo loại đất, chuyển thửa, gộp hộ, xóa hộ. Bấm **Tiếp theo**:
   hồ sơ được lưu để thửa mới dùng được ngay ở mục 1. **Thêm hộ…** chỉ hỏi họ tên rồi mở thẳng thẻ này.
   Ô **Nguồn gốc**: mỗi nội dung một dòng (Shift+Enter xuống dòng khi sửa); dòng bắt đầu bằng gạch đầu dòng ("- ", "+ ",
   "a) ", "1. "…) thì phần chữ tràn sang dòng sau tự thụt vào thẳng chữ sau dấu gạch – cả trên màn hình và bản in phương án
   chi tiết.
2. **1. Đất**: chọn thửa ở ô **Thửa** → **Thêm thửa vào mục 1** (tự điền loại đất, diện tích còn lại, giá). Ô **Thửa** của dòng
   đổi được (nhấp đúp, chọn thửa khác của hộ). Ô **Vị trí** xổ xuống các tuyến đường, vị trí (MT, T1–T3, K1–K3) của **bảng giá
   NQ 28** của **mọi địa bàn có trong bảng** (địa bàn của dự án đứng đầu, mỗi dòng ghi tên xã / phường – dự án đi qua nhiều xã
   vẫn chọn được tuyến của xã khác; gõ vài chữ, ví dụ `761`, để lọc): chọn là giá đất tự điền theo loại đất của dòng; gõ tay nội dung khác nếu vị trí không có trong bảng
   giá. Giá đất khác vẫn gõ đè được (ghi "Giá đất nhập tay" ở Ghi chú để rà soát).
   - **Diện tích = 0 / giá đất = 0** lưu được (hộ tạo lập tài sản trên đất người khác: chỉ có tài sản, không bồi thường đất).
3. **2. Nhà, công trình** / **3. Cây trồng** / **4. Vật nuôi** / **5. Hỗ trợ**: hàng **nhập nhanh** – gõ tên không cần dấu (`nha 1 tang`, `xoai 11-15`,
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
   - **Vật nuôi** (thẻ 4, từ 0.9.21 là mục riêng): đơn giá vật nuôi, thủy sản theo QĐ 31/2025/QĐ-UBND (VN01–VN17). Bản in:
     **4. Bồi thường, hỗ trợ về vật nuôi** nằm dưới mục cây trồng; các chính sách hỗ trợ thành mục **5**, thưởng bàn giao mặt bằng
     mục **6**. Bảng tổng hợp, quyết định, báo cáo 5 cột gộp vật nuôi vào cột "Cây trồng, vật nuôi". File dự án cũ mở lần đầu tự
     chuyển các dòng vật nuôi (mã nhóm vật nuôi) đang ở mục cây trồng sang mục Vật nuôi.
   - **Hỗ trợ** (thẻ 5): đầu thẻ có **Nhân khẩu**, Phải di chuyển chỗ ở, **DT đất NN đang sử dụng** (để trống = tự lấy diện tích đất
     nông nghiệp đã nhập ở mục 1) và **Tái định cư**. Dòng hỗ trợ ghi **tên chính sách theo câu chữ quy định** (Hỗ trợ ổn định đời
     sống; Hỗ trợ đào tạo, chuyển đổi nghề và tìm kiếm việc làm; Hỗ trợ tiền thuê nhà ở, tạm cư…), căn cứ ở cột Ghi chú, cột **Cách
     tính** in gộp thay ĐVT / số lượng / đơn giá / tỷ lệ:
     - **Ổn định đời sống**: nhập giá gạo, số kg, số tháng, tỷ lệ (theo nhân khẩu ở đầu thẻ) → "4 nhân khẩu x 30kg gạo x 6 tháng x
       16.000 đồng x 50%".
     - **Đào tạo, chuyển đổi nghề và tìm kiếm việc làm**: bảng các thửa đất nông nghiệp ở mục 1 (đánh dấu thửa, sửa diện tích, đơn giá
       đất, tỷ lệ 150% / 50%) → mỗi thửa một dòng; bản in có dòng tên chính sách đứng đầu nhóm.
     - **Thuê nhà ở, tạm cư / tự lo chỗ ở**: số tháng, mức hộ, mức mỗi nhân khẩu tăng thêm → một dòng "(1 hộ (4 nhân khẩu) * 1 tháng *
       6.000.000 đồng) + (1 nhân khẩu tăng thêm * 1.500.000 đồng * 1 tháng)". Đổi nhân khẩu là đơn giá và cách tính tự tính lại. (Số
       nhân khẩu của mức hộ mặc định 4 theo QĐ 42/2025.)
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
- **Lưu (Ctrl+S)**: ghi hồ sơ và phương án của hộ, có nhật ký. Mục nào không có / bỏ trống tính **0 đồng**; hộ đã Lưu là
  **đã lập phương án** kể cả mọi mục bằng 0 (hộ chưa lưu lần nào: nút Lưu luôn bấm được để xác nhận). Dòng có số lượng, đơn giá,
  diện tích bằng 0 không còn báo "cần xem lại". Hộ đã lưu trong phần mềm hiện "Sửa trong phần mềm" ở cột Đối chiếu Excel.

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
  số cây kiểm đếm; mật độ lấy từ ghi chú bộ đơn giá ("Mật độ 210 cây/ha"). Hộp hiện: mật độ
  quy định (cây/ha, m²/cây), số cây tối đa trên diện tích trồng, **diện tích cần cho số cây kiểm đếm**, có **vượt mật độ** không, vượt
  bao nhiêu cây (thiếu bao nhiêu m²), bao nhiêu cây **đảm bảo mật độ**. Áp dụng: dòng hiện tại = số cây đảm bảo mật độ (100%), thêm dòng
  **vượt mật độ** ngay dưới với tỷ lệ bồi thường (mặc định 0%).
- **Thẻ Nhà, công trình → Tách theo ranh thu hồi…** (chọn dòng tài sản): nhập tổng diện tích / khối lượng xây dựng và phần nằm trong
  ranh thu hồi. Phần trong ranh tính 100%; phần ngoài ranh tính theo tỷ lệ (mặc định 0%), hoặc tính toàn bộ nếu đánh dấu "ảnh hưởng kết
  cấu, không sử dụng được". Mô tả trong / ngoài ranh ghi ở cột Quy cách để làm cơ sở lập phương án.

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
    `{ho.tong_tien}`… được nhân thành mỗi hộ một dòng - danh sách đầy đủ ở nút **Mã điền tự động {…}…**.
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
- **Nhập quyết định** (menu trái **Tiến độ & bàn giao** → **Quyết định phê duyệt** → nút **Nhập từ file…**): chọn file quyết định phê duyệt / danh sách chi trả / biên bản bàn giao (Excel, Word, PDF có chữ, CSV). Phần
  mềm tự đọc số và ngày quyết định, khớp từng dòng với hộ theo mã hộ, số CCCD hoặc họ tên (bỏ "Ông/Bà", không phân biệt hoa thường,
  dấu), lấy số tiền và tô đỏ dòng có số tiền khác tổng phương án; tên trùng nhiều hộ được liệt kê để chọn tay. Bấm cập nhật để ghi
  trạng thái cho các hộ đã đánh dấu; có thể chép file vào `<thư mục hồ sơ>\Quyết định phê duyệt` (Chi trả, Bàn giao mặt bằng).
- **Báo cáo tổng hợp…**: xuất Excel các hộ **đang hiện theo bộ lọc** (đợt, trạng thái, từ khóa): sheet danh sách (mục 1-5, tổng,
  phê duyệt, chi trả, bàn giao, ghi chú theo dõi, tổng cộng và bằng chữ) và sheet tổng hợp theo đợt (số hộ, tổng tiền, số hộ / số
  tiền đã phê duyệt, đã chi, đã bàn giao).

## Nhóm 5 và Nhóm 6: tổng hợp, trình thẩm định, phê duyệt, chi trả, bàn giao, cưỡng chế

Theo Mục IV Quyết định 18/2026/QĐ-UBND (16 bước). Các mốc ngày bên dưới là **mặc định theo đặc tả của phần mềm**, đặt ở cài đặt của dự án
(**Tiến độ chi trả & Bàn giao → Mốc pháp lý…**) - đối chiếu văn bản gốc và đổi khi quy định thay đổi.

### Nhóm 5 - Tổng hợp & trình duyệt (Bước 8, 11)

- **Bảng tổng hợp kinh phí** có 3 thẻ:
  1. **Cơ cấu kinh phí dự án**: tiền đất, tài sản (nhà, công trình), cây trồng - vật nuôi, hỗ trợ - tái định cư, thưởng; cộng bồi
     thường, hỗ trợ, tái định cư; **kinh phí tổ chức thực hiện** (QĐ 08/2025: theo tuyến tối đa 3,5%, dự án khác 2,5% - chọn ở
     Thông tin dự án); tổng kinh phí và tỷ trọng. Cột *Đã phê duyệt* lấy từ các quyết định; *Chưa phê duyệt* là phương án của các hộ chưa
     có quyết định; *Lệch PA - QĐ* chỉ so các hộ đã có quyết định (khác 0 nghĩa là quyết định ghi khác phương án).
  2. **Bảng kinh phí chi tiết** (tên thẻ ghi số hộ của dự án): từng hộ - đất, nhà, cây, hỗ trợ, thưởng, tổng phương án, tổng phê duyệt.
  3. **Đối soát dự toán Pre-F/S**: so kinh phí thực tế (áp giá của dự án) với **bảng khái toán ban đầu** - bấm **Dùng bảng khái toán đang mở**
     (bảng ở Nhóm 1) hoặc **Chọn file khái toán…** (`.pabtdt`, phần mềm nhớ file đã chọn cho dự án). Báo "VƯỢT khái toán" khi thực tế lớn hơn.
  Nút **Đi đến Phân hệ Phê duyệt →** (góc phải) mở trang Quyết định phê duyệt của Nhóm 6.
- **Đợt trình thẩm định** (bố cục hai cột): bên trái *Quản lý đợt trình* và *Tờ trình thẩm định*, bên phải *Danh sách hộ và đánh số PA*.
  - **Hạn thẩm định**: nhãn đếm ngược "Còn X / 15 ngày" tính từ **ngày trình** của đợt (xanh còn hạn, vàng còn không quá 3 ngày, đỏ quá
    hạn; hiện "đã có quyết định phê duyệt" khi mọi hộ của đợt đã duyệt). Chưa nhập ngày trình thì nhãn nhắc nhập (Sửa đợt…).
  - **Lấy hộ đã niêm yết xong từ Nhóm 4**: một nút xổ - *tất cả hộ đã niêm yết xong*, *chỉ hộ đã đồng thuận*, hoặc từng đợt niêm yết.
    "Đã niêm yết xong" = đợt niêm yết đã hết thời hạn và hộ không vướng pháp lý V1-V5; hộ đã có trong đợt được bỏ qua, hộ đang ở đợt
    trình khác thì hỏi trước khi chuyển.
  - **Xuất bản hồ sơ (Bước 8)** (0.9.77): hộp Đợt trình **không còn tự xuất file**. Phía dưới chỉ có danh sách kiểm tra hồ sơ (đạt a/5 điều kiện:
    số hộ, số PA chi tiết, số / ngày tờ trình, số PA tổng, ý kiến nhân dân - chỉ nhắc, rê chuột xem chi tiết [Đạt] / [Xem lại] / [Thiếu]) và **một nút
    "Xuất bản hồ sơ đợt này →"**, mở **Xuất hồ sơ & Bản in** với đợt đang chọn. Ở đó chọn **Bản chính thức** (mẫu chính, trọn bộ: phương án chi tiết từng
    hộ, bảng tổng hợp, tờ trình thẩm định, báo cáo tiếp thu ý kiến) hay **Bản Dự thảo** (mẫu có chữ DỰ THẢO, tự che số CCCD, chỉ phương án chi tiết và
    bảng tổng hợp - để gửi dân niêm yết). Hồ sơ đợt lưu ở thư mục "Đợt N - k hộ" trong thư mục hồ sơ.
  - **Số PA chi tiết** đánh số mặc định **2 chữ số** (01, 02, 03…), đổi được ở hộp Đánh số.

### Nhóm 6 - Phê duyệt & bàn giao (Bước 9, 12 - 16)

- **Quyết định phê duyệt** là nơi **duy nhất** quản lý quyết định (Thêm / Nhập từ file / Sửa / Xóa; thêm hộ, ghi nhận đã nhận tiền).
  Bên trái danh sách quyết định, bên phải hộ của quyết định và **thanh khớp số liệu**: "Đã duyệt: X/N hộ · Tổng tiền: Y đ", báo *KHỚP* hoặc
  *LỆCH* so với tổng tiền ghi trong quyết định (nhập ở **Sửa…**).
- **Tiến độ chi trả & Bàn giao** (từ 1.0.00 gộp cả "Báo cáo tiến độ GPMB" - hai trang cũ trùng phần lớn số liệu):
  - **4 thẻ chỉ số** ở trên cùng - bấm thẻ để lọc ngay:
    - **Giải ngân tiền bồi thường** (tiền đã chi / tiền đã phê duyệt) → lọc hộ *còn quyết định chưa nhận tiền*;
    - **Mặt bằng sạch đã bàn giao** (diện tích thu hồi của hộ đã bàn giao / tổng) → lọc hộ *chưa bàn giao*;
    - **Thửa chưa bàn giao mặt bằng** (Gấp / Cao / Theo dõi) → chuyển sang chế độ **Thửa còn vướng**;
    - **Hộ đủ điều kiện cưỡng chế** → lọc hộ *đủ điều kiện cưỡng chế*.
    Chưa có quyết định phê duyệt thì thẻ hiện "—" kèm lời nhắc (không hiện 0,0%). Rê chuột lên thẻ xem số đầy đủ.
  - **Hai chế độ xem** (nút ghép đôi, nút đang chọn nền xanh đậm):
    - **Theo hộ** (nhập liệu): mỗi hộ một dòng - mốc thu hồi đất, vận động / cưỡng chế, quyết định, tiền phê duyệt / đã nhận, ngày nhận,
      lý do chưa nhận, biên lai, bàn giao, ghi chú, hoàn tất CTBT, HS đính kèm. Lọc theo điều kiện, tìm không cần dấu, đánh dấu quyết định
      (ô danh sách quyết định ẩn khi dự án chưa có quyết định). Bấm đúp dòng để cập nhật chi trả / bàn giao của hộ.
    - **Thửa còn vướng**: thửa của hộ **đã có quyết định** mà chưa bàn giao, xếp **Gấp** (đủ điều kiện cưỡng chế, hoặc đã nhận đủ tiền mà
      chưa bàn giao và cùng tờ bản đồ với thửa đã giải tỏa) / **Cao** (đã nhận đủ tiền, hoặc đang vận động) / **Theo dõi**. Bảng trống thì
      phần mềm nói rõ vì sao (chưa có hộ được phê duyệt, hoặc mọi hộ đã bàn giao).
  - **Mốc pháp lý** (một dòng): ngày thông báo thu hồi đất, số ngày mốc thu hồi đất nông nghiệp (**60 ngày**) / phi nông nghiệp
    (**120 ngày**), thời hạn vận động (**10 ngày**), số hộ đã đủ mốc. Bấm **Mốc pháp lý…** để nhập **ngày thông báo thu hồi đất** và sửa số
    ngày các mốc. Hộ có thửa phi nông nghiệp (ví dụ ONT+CLN) hoặc loại đất không rõ tính theo 120 ngày.
  - **Sổ nhật ký vận động…**: ghi các buổi vận động hộ **không nhận tiền bồi thường** hoặc **không bàn giao mặt bằng** (ngày, hình thức,
    thành phần, nội dung, kết quả, biên bản). Tính từ buổi đầu tiên: quá **10 ngày** mà hộ vẫn chưa nhận tiền / chưa bàn giao thì cột
    **Vận động / cưỡng chế** chuyển sang **"Đủ điều kiện cưỡng chế thu hồi đất theo Điều 89"** (tô đỏ). Hộ chưa có quyết định phê duyệt
    chưa áp dụng thời hạn vận động.
  - **Bàn giao mặt bằng các hộ đã chọn…**, **Hộ hoàn tất CTBT…** (xem + xuất Excel).
  - **Xuất ▾** (một nút): *Bảng theo dõi chi trả & bàn giao (Excel)*, *Báo cáo tiến độ GPMB (Excel)* (chỉ số điều hành + danh sách thửa
    còn vướng - báo cáo định kỳ), *Danh sách đề nghị cưỡng chế (Excel)* (hộ, thửa, quyết định, số buổi vận động, hạn vận động, số ngày quá
    hạn, mốc thu hồi đất). Danh sách đầy đủ các hộ: **Dữ liệu → Xuất danh sách hộ…**.

## Kiểm tra lỗi trước khi trình

**Kiểm tra lỗi…** rà toàn dự án, chia **Lỗi** (tô đỏ) và **Cảnh báo**, lọc theo nhóm: thông tin dự án (tên, xã, người ký…),
thông tin hộ (họ tên trống / có số / khoảng trắng thừa / chưa viết hoa, địa chỉ trống, CCCD sai số chữ số hoặc trùng giữa các hộ,
ngày cấp sai, trùng họ tên + địa chỉ), **font chữ** (ký tự lạ do gõ TCVN3 / VNI, chữ tổ hợp), thửa đất (DT bằng 0, thiếu số thửa /
tờ, loại đất ngoài danh mục, cùng thửa ở nhiều hộ), phương án (hộ có thửa chưa lập PA, dòng chưa có số lượng / đơn giá, thiếu căn cứ
giá, DT ở mục 1 khác kiểm kê, nhà – công trình vượt DT thu hồi, cây tính 100% vượt mật độ), đơn giá (khác danh mục hiện hành, áp giá
tương đương / nhập tay), số liệu (thành tiền khác file Excel, số âm) và tiến độ (chi trả khi chưa phê duyệt, số tiền phê duyệt khác
tổng phương án…). Nhấp đúp dòng để mở phương án của hộ; **Sửa tự động lỗi trình bày** chuẩn hóa khoảng trắng, chữ hoa họ tên (chỉ
tên người, không đụng tên có mô tả kèm theo), chữ tổ hợp, số CCCD; **Xuất Excel** lưu danh sách lỗi.

## Dự toán & khái toán

**Dự toán & khái toán** (menu trái, nhóm Dự án & dự toán - từ 0.9.23 là một trang của cửa sổ chính; dùng được cả khi chưa mở dự
án). Thẻ **Khái toán / dự toán**: bảng dự toán theo mục 1 đất, 2 nhà – công trình, 3 cây trồng, 4 hỗ
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
- Thẻ **So sánh với thực tế áp giá** (0.9.23, cần mở dự án): khái toán đã duyệt là **ngân sách trần**. Bấm **Mở khái toán đã duyệt
  (.pabtdt)…** (hoặc dùng bảng đang lập ở thẻ Khái toán / dự toán); phần mềm tính thực tế từ phương án các hộ trong dự án và so
  từng mục (khái toán, thực tế, chênh lệch, tỷ lệ %). Chi phí khác (mục 6) của thực tế tính theo đúng các tỷ lệ của khái toán.
  Thực tế **vượt** khái toán: dòng thông báo đỏ - rà soát phương án các hộ hoặc trình điều chỉnh tổng mức kinh phí.

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

### Dự án mới: nhập danh sách từ Excel, PDF, ảnh (từ 1.0.27)

Bước 2 của **Dự án mới** có nút **Nhập từ file (Excel, PDF, ảnh)…**. Chọn một hoặc nhiều file:

- **Excel** `.xlsx`, `.xlsm`, `.xls` (cả định dạng Excel 97-2003): đọc mọi sheet, chọn bảng có nhiều hộ thửa nhất. Ô công thức chưa có giá trị được tính lại.
- **PDF có chữ** (văn bản đã ký hoặc chưa ký): chia cột theo vị trí thật của từng ô chữ; ô xuống nhiều dòng được nối về đúng hộ, tiêu đề lặp lại ở các trang sau và phần chữ ký cuối bảng được bỏ.
- **PDF scan, ảnh** `.png`, `.jpg`, `.tif`, `.bmp`: nhận dạng chữ bằng Tesseract đóng kèm (chậm hơn, khoảng 1-3 giây mỗi trang), nét kẻ khung bảng không thành chữ.

Phần mềm tự nhận cột theo tên (không phân biệt dấu, chịu được chữ nhận dạng sai nhẹ) hoặc theo nội dung ô (ví dụ cột toàn ký hiệu loại đất, cột có dạng "tờ/thửa"). Cột nào phần mềm có mà file không có thì bỏ qua; file không có họ tên thì mỗi tờ/thửa là một hộ tạm ("Hộ tờ X thửa Y") để sửa lại sau. Dòng nào bị bỏ (tiêu đề lặp, chữ ký, dòng tổng) được liệt kê trong thông báo.

Nhận cột chưa đúng: bấm **Chỉnh cột…**, chọn lại cột nào là họ tên, địa chỉ, tờ, thửa, diện tích thu hồi, loại đất… rồi **Đọc lại**. Bản scan nên chụp thẳng, rõ nét; nếu kết quả sai nhiều, xuất lại PDF từ Excel gốc sẽ chính xác hơn.


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

**Máy dùng (không cần Python):** có **hai bộ cài**, cùng **một tiêu chuẩn cài đặt** (từ 0.9.21):

- từ 0.9.22 mặc định cài vào **`C:\Program Files (x86)\PABT`** (Windows 32-bit: `C:\Program Files\PABT`): Windows hỏi quyền
  quản trị một lần để chép file – chọn **Có (Yes)**. Không có tài khoản quản trị / bấm Không: bộ cài tự chuyển sang
  `%LOCALAPPDATA%\Programs\PABT` (không cần quyền quản trị) để cài tiếp. Máy đã cài bản cũ ở thư mục khác: bản cũ được gỡ (thư
  mục cũ có file dự án .pabt thì giữ nguyên). Gỡ cài bản trong Program Files: Windows hỏi quyền quản trị để xóa thư mục;
- **không cài thêm gì vào Windows** (không Visual C++, .NET, Python hay bản cập nhật nào: mọi thư viện đã nằm sẵn trong bộ cài);
  bộ cài có đủ **mẫu in** (phương án chi tiết, bảng tổng hợp, mẫu "Dự thảo"), **bộ đơn giá**, **bảng giá đất NQ 28**, mẫu tờ
  trình / phương án tổng - máy mới chưa có dữ liệu gì vẫn lập và in được ngay; tự kiểm tra sau khi cài chạy thử tạo dự án, in
  phương án chi tiết, bảng tổng hợp, tờ trình (dữ liệu giả lập);
- chạy được cả trên máy cơ quan **khóa chạy script PowerShell** (Group Policy / ExecutionPolicy);
- chép xong bộ cài **kiểm lại từng file** (mã SHA-256): phần mềm diệt virus chặn file nào thì báo rõ file đó;
- cài xong tự kiểm tra phần mềm trên chính máy đó (giao diện, đọc PDF, bộ đơn giá, mẫu in, bảng giá đất). Nhật ký:
  `%TEMP%\pabt_cai_dat.log`. Cần ổ đĩa còn trống ≥ 300 MB.

**Một bộ cài cho mọi máy** (từ 0.9.26): `PABT_Setup_Universal_<phiên bản>.exe` (~50 MB) chứa hai bản chương trình và tự chọn khi
cài:

| Máy | Bản được cài | Nền chạy |
|---|---|---|
| **Windows 10 (bản 1809 trở lên) / 11**, 64-bit | bản 64-bit | Python 3.14 + Qt6 |
| **Windows 7 SP1 / 8 / 8.1**, Windows 32-bit, Windows 10 bản cũ | bản 32-bit | Python 3.8 + Qt5 |

Windows 7 cần **Service Pack 1** và bản cập nhật **KB2533623** (có trong KB3063858; máy đã chạy Windows Update là có). Bộ cài
**kèm sẵn KB3063858** (bản 32-bit và 64-bit của Microsoft): máy Windows 7 còn thiếu thì cửa sổ cài có ô "Cài bản cập nhật
Windows 7 KB3063858" (đánh dấu sẵn) – Windows hỏi quyền quản trị một lần, cài xong **khởi động lại máy** rồi mở PABT. Máy đã có bản
cập nhật thì bỏ qua bước này (không hỏi gì).

Chép **một file** bộ cài sang máy, bấm đúp → cửa sổ cài đặt (chọn thư mục, biểu tượng Desktop, liên kết file `.pabt`) → **Cài đặt**
→ thanh tiến trình → tự kiểm tra → **Mở PABT**. Cài im lặng: `PABT_Setup_Universal_<phiên bản>.exe /Q`.

**Máy không chạy được file `.exe` của bộ cài** (phần mềm diệt virus chặn, hoặc tên người dùng Windows có dấu làm vỏ giải nén lỗi):
giải nén `PABT_ChayNgay_<phiên bản>_Universal.zip` vào một thư mục rồi
- bấm đúp **`CAI_DAT.cmd`** trong thư mục đó để cài như bộ cài `.exe` (cùng cửa sổ, cùng kiểm tra, tự chọn bản), hoặc
- chạy thẳng **`x64\PABT.exe`** (Windows 10 / 11 64-bit) hoặc **`x86\PABT.exe`** (Windows 7 / 8, 32-bit) không cần cài.

Gỡ bằng Settings → Apps (Win 7: Control Panel → Programs) – file dự án `.pabt` được giữ. Hai bản có cùng chức năng (bản Win7-8 đọc
PDF đơn giá bằng `pypdf` thay cho QtPdf); cùng một **gói cập nhật `.pabtcn`** dùng được cho cả hai bản. Mẫu in sửa bằng **Cập nhật
mẫu in…** được lưu ở `%APPDATA%\PABT\mau_in`.

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
   trong Windows, khởi chạy `CAI_DAT.cmd` → `cai_dat.ps1` / `go_cai_dat.ps1` chạy được PowerShell 2.0) thành MỘT bộ cài
   `bo_cai\PABT_Setup_Universal_<phiên bản>.exe` (vỏ IExpress 32-bit từ SysWOW64; thư viện C chung UCRT của Windows 7 đóng sẵn -
   `bo_cai_win\ucrt_win7.py` lấy từ `vc_redist_win7.x86.exe`) và gói `PABT_ChayNgay_<phiên bản>_Universal.zip` (chạy ngay / cài
   dự phòng bằng `CAI_DAT.cmd`). Hai bộ cài riêng như trước 0.9.26: `dung_bo_cai_win.py win10 win7`. `rut_gon.py` dừng dựng nếu bản dựng cần DLL không có sẵn trên Windows đích (Windows 7 SP1 /
   Windows 10 1809).
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
| `pabt/don_gia.py`, `pabt/bo_don_gia.sqlite`, `pabt/quan_tri_bo.py`, `tao_bo_don_gia.py` | Bộ đơn giá: đọc, áp vào dự án, thêm/sửa/xóa/thay (quyền quản trị), cập nhật từ file / Internet |
| `pabt/du_an_moi.py`, `pabt/man_hinh_du_an_moi.py` | Dự án mới từ dữ liệu thô: gom hộ, bảng giá đất, tự lập phương án, xuất 2 bảng in |
| `pabt/man_hinh_don_gia.py` | Màn hình Bộ đơn giá (xem, sửa có mở khóa quản trị, cập nhật, tra cứu văn bản) |
| `pabt/gia_dat_nq28.py`, `pabt/bang_gia_nq28.json`, `pabt/man_hinh_gia_dat.py` | Bảng giá đất NQ 28/2025 (4 địa bàn): tra cứu, điền giá, xuất Excel |
| `tao_bieu_tuong.py`, `pabt/bieu_tuong.ico` | Biểu tượng duy nhất của phần mềm / bộ cài, dựng từ `logo_PABT_nen_trang.png` (chữ PABT, nền trắng sữa, viền xanh đậm + vàng) |
| `pabt/nhap_don_gia.py`, `pabt/man_hinh_nhap_don_gia.py` | Cập nhật bộ đơn giá từ Excel / Word / PDF / CSV hoặc trang web: đọc bảng, so khớp, xem trước, tạo phiên bản mới |
| `pabt/man_hinh_quet_web.py` | Quét trang web / Công báo Đồng Nai: tìm văn bản đơn giá, chính sách; tải, phân tích, áp dụng theo ngày ban hành |
| `pabt/ho_so.py` | Hồ sơ kiểm kê: thêm / sửa / xóa hộ, thửa; gộp hộ; chuyển thửa |
| `pabt/nghiep_vu.py` | Quy tắc tính: thành tiền, làm tròn như ROUND của Excel, thưởng theo tổng mục 1–4, hỗ trợ ổn định đời sống, gợi ý HT09/HT10 theo hạn mức; kiểm tra quy tắc từng hộ |
| `pabt/doi_chieu.py` | So từng hộ, từng dòng với Excel; xuất báo cáo `.xlsx` (TONG_HO, DONG_LECH, CAN_XEM_LAI) |
| `pabt/lap_pa.py` | Soạn phương án một hộ: thêm / sửa / xóa dòng, danh mục, giá tương đương, gợi ý hỗ trợ, lưu một giao dịch; thông tin dự án; rà soát giá |
| `pabt/in_an.py` | Bảng tổng hợp theo mẫu `IN_BANGTONGHOP.xlsx`; xuất PDF / in qua Excel |
| `pabt/du_lieu_in.py` | Dữ liệu bản in (dòng bảng, thông tin hộ / dự án, tiêu đề) - không Excel / Word |
| `pabt/in_word.py`, `pabt/docx_sang_pdf.py` | Phương án chi tiết bản Word (.docx) và PDF dự phòng dựng từ file Word |
| `pabt/giao_dien.py` | Màu giao diện: nút theo nhóm chức năng, tiêu đề bảng, nhãn thuộc tính; nút chuẩn tiếng Việt |
| `pabt/app.py`, `pabt/man_hinh.py`, `pabt/man_hinh_ho_so.py` | Cửa sổ chính; màn hình Lập phương án hộ và các hộp chọn danh mục, gợi ý, dự án, rà soát, in; màn hình Hồ sơ hộ |
| `pabt/quan_ly.py`, `pabt/man_hinh_quan_ly.py` | Đợt trình, thư mục hồ sơ, lưu dự án thành, trạng thái phê duyệt / chi trả / bàn giao, nhập quyết định từ file, báo cáo tổng hợp; màn hình Đợt trình, Trạng thái hộ, Nhập quyết định, Kiểm tra lỗi |
| `pabt/kiem_loi.py` | Kiểm tra lỗi trước khi trình (thông tin hộ, font chữ, thửa, phương án, đơn giá, tiến độ), sửa tự động lỗi trình bày |
| `pabt/du_toan.py`, `pabt/man_hinh_du_toan.py` | Dự toán / áp giá dự thảo: gom khối lượng, áp đơn giá hiện hành, tra giá đất NQ 28, file `.pabtdt`, xuất Excel |
| `pabt/cay_trong.py`, `pabt/man_hinh_cay.py` | Cây theo chu vi (quy đổi đường kính), mật độ cây trồng, tài sản trong / ngoài ranh thu hồi, quy chuẩn của dự án |
| `DUNG_BO_CAI.bat`, `bo_cai_win/` | Bộ cài IExpress (`cai_dat.ps1` cửa sổ cài, `rut_gon.py`, `vc_redist.x64.exe`) |
| `tests/` | 113 bài kiểm thử (unittest), có các bài chạy màn hình thật (chế độ ẩn) |

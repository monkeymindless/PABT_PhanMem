"""Lịch sử cập nhật phần mềm, hiện ở chân trang màn hình chào.

Bản trước 0.9.53 không ghi. Mỗi phiên bản mới thêm một mục ở ĐẦU danh sách,
cùng số với pabt.__version__.
"""
from __future__ import annotations

# (phiên bản, ngày, các dòng người dùng đọc được)
MUC = (
    ('1.0.56', '03/11/2026', (
        'KHÓA BẢO MẬT BỘ ĐƠN GIÁ: máy dùng máy chủ LAN chỉ tài khoản QUẢN TRỊ máy chủ (đang đăng nhập) sửa được bộ đơn giá - tài sản, '
        'cây trồng, vật nuôi, chính sách hỗ trợ, bảng giá đất, hệ số K (cả nạp từ file, quét văn bản, khôi phục). Máy đơn: cần mở khóa bằng '
        'mật khẩu quản trị bộ đơn giá.',
        'ĐỒNG BỘ BỘ ĐƠN GIÁ QUA MÁY CHỦ: quản trị sửa xong, bộ đơn giá tự phát hành lên máy chủ; máy khác nhận khi đăng nhập (có kiểm tra '
        'mã băm, file hỏng thì giữ bộ cũ). Quản trị bảo mật > Phát hành / Nhận bộ đơn giá để làm ngay.',
        'Cập nhật đơn giá từ văn bản: đọc cả LỜI VĂN các điều khoản, trích các quy định cách tính (mật độ, cây trồng xen, phần vượt, tỷ lệ '
        '%, trường hợp không bồi thường…) - lưu vào bộ đơn giá (thẻ "Quy định cách tính"), ghi vào ghi chú mục liên quan và hiện ở Giải '
        'trình cách tính (Ctrl+I) khi lập phương án.',
        'Tự chọn sẵn mọi dòng thay đổi (mới, đổi giá, đổi tên, bỏ); văn bản dài chỉ hiện các dòng cần xử lý; nút "Chọn mọi dòng thay '
        'đổi" / "Bỏ chọn tất cả". Văn bản đã có (bản hợp nhất gồm đủ văn bản sửa đổi): dòng đổi giá cũng được chọn sẵn.',
        'Kiểm tra bằng AI (tùy chọn, cần bật Trợ lý trực tuyến): AI đọc toàn văn văn bản như cán bộ thẩm định, xác minh tên / ĐVT / đơn '
        'giá các dòng cần xem, tìm thêm quy định cách tính. Chỉ gửi chữ văn bản đơn giá (công khai); không bao giờ tự đổi giá - dòng AI đọc '
        'khác được bỏ chọn để đối chiếu.',
    )),
    ('1.0.55', '03/11/2026', (
        'Nhật ký kiểm toán có CHUỖI BĂM: mỗi dòng ghi qua LARC được ký nối với dòng trước - dòng bị sửa / xóa bằng công cụ khác ngoài '
        'phần mềm được báo ngay trên cửa sổ Nhật ký kiểm toán.',
        'Giải trình cách tính từng dòng phương án: chuột phải dòng > "Giải trình cách tính & căn cứ…" (hoặc Ctrl+I) - công thức, thay '
        'số, căn cứ / nguồn giá, có nút Chép; cửa sổ Xem chi tiết tính tiền: rê chuột lên dòng tiền để đọc giải trình.',
        'Bản sao lưu tự động và mốc của Cỗ máy thời gian được NÉN (nhỏ hơn khoảng 5 lần, không mã hóa - luôn khôi phục được). Mở bản '
        'sao lưu: phần mềm tự giải nén, mở chỉ xem.',
        'Nhận phiếu qua Wi-Fi: quét mã QR thì gói tin được mã hóa (khóa nằm trong mã QR, không đi qua mạng) và kiểm tra không bị sửa '
        'trên đường truyền.',
        'Dải lần lập phương án gọn hơn: "+ PA bổ sung" là nút phụ; hộ chỉ có một lần phương án không hiện nút Xóa lần.',
        'Sửa lỗi của 1.0.54 có thể làm phần mềm tự đóng (hiếm, sau khi mở - đóng nhiều cửa sổ): phần đọc tên ô nhập cho trình đọc màn hình.',
        'Sửa lỗi: họ tên dán từ bản scan / PDF có ký tự điều khiển ẩn làm xuất hồ sơ báo lỗi "embedded null byte"; Trợ lý AI che thêm '
        'họ tên sau "Người nhận tiền / Người đại diện / Người được ủy quyền / Chủ sở hữu / Họ và tên…" và số điện thoại dạng (+84).',
    )),
    ('1.0.54', '03/11/2026', (
        'Tông nền Tối / Ấm / Titan: nền ô trạng thái các bảng (xanh = khớp, cam = lệch, vàng = cần xem) và các dải, thẻ, khung viền riêng của '
        'từng màn hình đổi màu theo tông - không còn ô nền sáng dưới chữ sáng.',
        'Bấm A+ / A− khi đang ở tỷ lệ khác 100%: dải, thẻ, nhãn đổi màu sau khi cửa sổ đã mở vẫn giữ đúng cỡ chữ; đổi tỷ lệ / đổi tông nhanh '
        'hơn (phần đang ẩn áp kiểu khi hiện ra).',
        'Cỡ chữ thống nhất một thang (11 - 12 - 13 - 14 - 16 - 18 px): huy hiệu, nhãn phụ trên thẻ số liệu không còn chữ 10 px khó đọc.',
        'Trình đọc màn hình (Narrator): ô nhập đọc đúng tên theo nhãn đứng cạnh ("Họ và tên", "Số CCCD"…). Bảng mật độ cây, chẩn đoán, '
        'nhập chi tiết, quy trình: dòng cao vừa chữ.',
    )),
    ('1.0.53', '03/11/2026', (
        'Cập nhật đơn giá từ văn bản (Word, PDF, bản scan): dòng con "- Ống 1 m Φ1m" giữ tên dòng cha, khớp mục cũ theo cỡ Φ, kết cấu, '
        'số đo, ĐVT dù tên văn bản ghi khác bộ đơn giá - không còn báo nhầm "mục mới". Dòng giá chung ("Trụ cổng, bờ kè và các loại tài sản '
        'khác có kết cấu") cập nhật mọi mục cùng kết cấu. Ô giá "259.000 - 720.000" tách mức thấp / mức cao (mục có dấu chấm cuối tên).',
        'Dòng hướng dẫn không có giá ("giếng sâu từ 10m … tính thêm 50%", gác lửng 40% / 20%) hiện riêng ở khung "Quy định cách tính".',
        'Văn bản đơn giá cây trồng: dòng ghi nhiều loài ("Cây cải xanh, cải ngọt, cải thìa", "Si cảnh, Sanh cảnh…") tách thành từng loài như '
        'bộ đơn giá; giá nhiều mùa vụ trong một ô ("Đông Xuân: … Hè Thu: …"); loài cây lâm nghiệp đọc sai tên nhận ra theo nhóm giá.',
        'Bản scan: giá đọc sai chữ số ("S27.312", "157.000" thay "187.000"), ô giá không đọc được, cỡ đường kính đọc hỏng được đánh dấu '
        '"giá cần xem lại" và không chọn sẵn; chế độ thay cả nhóm không tự chọn xóa mục chỉ vì bản scan đọc thiếu dòng.',
    )),
    ('1.0.52', '02/11/2026', (
        'Niêm yết công khai: tùy chọn che số CCCD (075092***456) trên bản dự thảo dán tại điểm dân cư và file bảng niêm yết - ô ở Xuất hồ sơ & '
        'Bản in (chế độ Dự thảo), nhớ theo dự án, mặc định tắt. Tờ trình, quyết định, bảng ký nhận vẫn in đủ 12 số.',
        'Nút Lưu màu xanh lục, khác nút thao tác chính. Số trên các thẻ số liệu dùng phông số thẳng cột.',
        'Trợ lý AI luôn che họ tên, CCCD, số điện thoại, số giấy chứng nhận, tọa độ trước khi gửi (bỏ tùy chọn gửi nguyên).',
        'Dự án lớn (10.000 hộ trở lên): thêm chỉ mục dữ liệu, mở dự án / lọc theo đợt nhanh hơn. Ghi dữ liệu nhiều bước gộp một lần ghi đĩa. '
        'Biểu tượng LARC trên thanh tác vụ dùng định danh mới khi cài bằng bộ cài 1.0.52 (bộ cài tự cập nhật lối tắt đã ghim).',
    )),
    ('1.0.51', '02/11/2026', (
        'Lưu tự động: cửa sổ lập phương án tự ghi phương án / hồ sơ hộ sau 10 giây ngừng thao tác (chọn 10 giây, 1 phút, 2 phút hoặc '
        'Tắt ở dải dưới cùng cửa sổ hoặc Cài đặt > Giao diện). Không hộp thoại, không cắt ngang ô đang gõ, bảng giữ nguyên ô đang chọn; '
        'nhãn "● Chưa lưu" / "✓ Đã tự lưu giờ:phút:giây". Khái toán đã có file .pabtdt cũng tự lưu. LARC Mobile vốn lưu ngay mỗi lần ghi - '
        'nay hiện giờ đã tự lưu.',
        'Hộp tiến độ (đọc file scan, Trợ lý AI): nút Dừng / Bỏ qua bấm được ngay. Danh sách gợi ý ô nhập gần đáy màn hình lật lên trên. '
        'Màn hình thấp (laptop 1366 x 768): cửa sổ lập phương án nhường thêm chỗ cho bảng.',
        'Tông Tối: số tiền, thanh thông báo, biểu tượng nút sáng rõ. Nút Xóa viền đỏ rõ hơn; nút đang chọn bằng phím Tab có viền xanh.',
        'Trợ lý AI: che thêm số CCCD / điện thoại có dấu cách, số giấy chứng nhận, tọa độ, họ tên sau "ông / bà / chủ hộ" trước khi gửi; '
        'khóa API mã hóa riêng cho LARC. Nhận phiếu qua Wi-Fi: mã phiên dài hơn, giới hạn dung lượng mỗi phiên.',
    )),
    ('1.0.50', '02/11/2026', (
        'Quét giấy tờ / Dán tài sản: ảnh xem trước thu như lúc nhận dạng (ảnh điện thoại vài MB cửa sổ vẫn kéo được); '
        'Tesseract chạy nền, hộp tiến độ còn nút Dừng. Giấy chứng nhận không có tài sản không đọc hai lần; biên bản viết tay '
        'vẫn đọc thêm kiểu cột thưa (ô chọn, tối đa 8 trang). Trợ lý AI sau OCR có nút Bỏ qua và hết giờ khi mất mạng.',
        'Tông Tối: chú thích (tooltip) và ô nhập không còn chữ tối trên nền tối. Màu cảnh báo / vàng ô gom vào bảng màu chung. '
        'Bảng dự toán và cập nhật đơn giá giãn dòng nhanh hơn. Lỗi tải lại từng hộ ghi vào loi.log.',
    )),
    ('1.0.49', '02/11/2026', (
        'Quét giấy tờ / Dán tài sản → Mở file: đọc PDF ảnh OCR (chủ yếu), Word, Excel, ảnh chụp. Tự lọc dòng tài sản / viết tay, '
        'bỏ mẫu in hành chính. PDF lớp chữ thưa thì nhận dạng lại ảnh; Word/Excel chỉ có ảnh nhúng thì OCR ảnh trong file. '
        'Chữ viết tay: lần đọc khối chữ không ra dòng tài sản thì đọc lại kiểu cột thưa.',
        'Trợ lý AI (nếu đã bật ở Công cụ → Trợ lý) tự viết lại dòng đã lọc thành "Tên: số lượng ĐVT" — vẫn không gửi file ảnh / PDF. '
        'Nút Trợ lý AI viết lại còn để chạy lại khi cần.',
    )),
    ('1.0.48', '02/11/2026', (
        'Dán tài sản → Mở ảnh / PDF: file lớn (ảnh điện thoại, PDF scan vài MB) không còn làm cửa sổ "Không phản hồi". '
        'Hộp tiến độ từng trang, nút Dừng; ảnh thu về cỡ A4 300 dpi trước khi nhận dạng.',
        'Chỉ lấy dòng tài sản / viết tay vào Dán tài sản — không đổ mẫu in hành chính (CỘNG HÒA, tiêu đề biên bản, chữ ký) '
        'và rác OCR. Nút Chữ OCR gốc để soát cả trang. Trợ lý AI viết lại dòng đã lọc là tùy chọn (mặc định tắt, không gửi file ảnh / PDF).',
        'Màn hình chính: ô Đã lập / Niêm yết đếm lũy kế số hộ đã đến mốc đó (hộ đã trình, đã duyệt vẫn được tính) — không còn báo 0 '
        'khi hộ đã sang bước sau. Bấm ô để xem đủ danh sách. Thanh phễu vẫn chia theo giai đoạn đang đứng.',
    )),
    ('1.0.47', '01/11/2026', (
        'Thẻ số liệu giữ 62 px (không nới, chừa chỗ bảng hộ trên màn 21"): dòng 2 diện tích xếp sát số thửa, không bị bo góc cắt. '
        'Bấm mở Bộ đơn giá / lập phương án / cửa sổ lệnh: chỉ dựng thẻ đang xem lúc mở, lần 2 dưới 0,1 giây.',
    )),
    ('1.0.46', '01/11/2026', (
        'Dán tài sản: mở ảnh / PDF scan hoặc dán ảnh clipboard (Tesseract chữ in; chữ viết tay phải xem lại dòng vàng). '
        'Phiếu kiểm đếm: nút Dán tài sản và Mở lập phương án hộ đang chọn; bấm đúp họ tên mở phương án.',
        'Cập nhật giá đất: văn bản không có bảng cột vẫn đọc lời văn nghị quyết rồi xem trước. '
        'Cập nhật đơn giá: thêm lệnh nạp file thay cả nhóm theo văn bản mới (khác chuột phải thay một dòng). '
        'Ctrl+Shift+V không còn đụng giữa tab Lập phương án và Đơn giá bồi thường.',
    )),
    ('1.0.45', '01/11/2026', (
        'Bản in trên máy mới (không cần Python): khung bảng và đường kẻ dưới chữ không còn mất khi mở bằng WPS / LibreOffice. '
        'Phương án chi tiết (Word): viền từng ô, nét 1 pt, màu đen. Bảng tổng hợp (Excel): viền RGB đen, đường kẻ dưới tên đơn vị / '
        'tiêu ngữ / dự án dày 1 pt.',
    )),
    ('1.0.44', '01/11/2026', (
        'Thẻ số liệu: số thửa và diện tích là hai dòng sổ địa chính cạnh số hộ (không ghép bằng dấu gạch chéo), diện tích đủ '
        'tương phản — không bị cắt, không đọc như tỷ lệ.',
        'Bấm menu trái (và thanh menu / tab) chuyển trang ngay, không còn trượt 160 ms làm cửa sổ nhấp nháy. Dấu chọn mục '
        'sáng tức thì; trang đã mở lần trước hiện lại dưới 0,1 giây.',
    )),
    ('1.0.43', '01/11/2026', (
        'Bản đồ máy tính vẽ đúng file KML / KMZ xuất từ MicroStation / gCadas: hiện lưới thửa và đường ranh (Level), số thửa, '
        'loại đất, diện tích, mốc ranh, ghi chú — không còn chỉ một đám chấm. Công tắc 4 lớp, nút + / − / Vừa trên bản đồ, '
        'bấm đối tượng xem thuộc tính, bảng tra cứu dưới bản đồ (như LARC Mobile).',
    )),
    ('1.0.42', '01/11/2026', (
        'Đồng bộ giao diện: một nguồn màu (thanh tiêu đề theo tông nền, kể cả tông Tối), số 0 và viền ô đạt tương phản WCAG, '
        'nhóm menu Title Case, dấu & hiện đúng (không còn gạch chân chữ sau &), nút tắt có chú thích lý do.',
        'Chọn hộ niêm yết tắt khi chưa mở dự án (không còn bấm im lặng). Danh sách dài (phiếu kiểm đếm, KML) hiện trong hộp cuộn. '
        'Cảnh báo chỉ cài gói cập nhật .larcud do đơn vị phát hành. Sắp xếp cột diện tích theo số Decimal.',
    )),
    ('1.0.41', '01/11/2026', (
        'Bản offline theo hộ (máy chủ LAN): tầng CSDL tự chặn mọi ghi (thêm / sửa / xóa) hộ không nằm trong danh sách nhận việc — '
        'kể cả đường ghi lọt khi hàm mới quên kiểm. Thông báo tiếng Việt, không làm hỏng dữ liệu hộ đã nhận.',
        'File dự án ghi cờ phiên bản phần mềm tối thiểu khi mở để sửa. Máy còn bản cũ hơn cờ đó (từ 1.0.41 trở đi) tự mở CHỈ XEM '
        'kèm thông báo nổi, để khỏi ghi sai dữ liệu lược đồ đã mở rộng; cập nhật phần mềm rồi mở lại là sửa được.',
    )),
    ('1.0.40', '31/10/2026', (
        'Màn hình chính khi mở dự án: việc cần làm cấp dự án và PHỄU TIẾN ĐỘ THEO HỘ (8 giai đoạn, theo lần phương án đang mở) - '
        'hộ ở đợt khác nhau, hộ chỉ có phương án bổ sung đều được đếm đúng; các cờ cần xem lại (phương án 0 đồng, trình thiếu ý kiến, '
        'có ngày bàn giao chưa có quyết định…) bấm được để ra danh sách hộ.',
        'Xuất bản một chạm (Trình phê duyệt): chọn đợt, kiểm điều kiện, xem trước cả bộ rồi xuất / in / gộp PDF.',
        'Bản đồ thửa đất: tô màu theo đồng thuận, tiến độ theo hộ hoặc lệch diện tích; nền ảnh vệ tinh tùy chọn (mặc định tắt, chỉ gửi '
        'tọa độ ô ảnh, ảnh đã tải xem được khi mất mạng); chuột phải thửa để mở phương án hộ.',
        'Làm việc nhóm: "Đồng bộ (vẫn giữ hộ)" đưa số liệu lên máy chủ mà vẫn giữ hộ đã nhận; tùy chọn tự đồng bộ khi Ctrl+S; điện '
        'thoại cùng Wi-Fi quét mã QR gửi file kết quả kiểm đếm về máy tính.',
        'Cỗ máy thời gian (Tệp tin): tự lưu mốc mỗi giờ khi có thay đổi, lúc mở / đóng dự án, trước thao tác hàng loạt; xem hộ nào đã '
        'đổi rồi khôi phục. Nhập phương án chi tiết vào dự án đang mở được chạy thử và xem trước thay đổi trước khi ghi.',
        'Trợ lý (Công cụ): giải thích vì sao tiền của hộ khác quyết định / các lần lập / file Excel, soạn nháp tờ trình - chạy trên máy, '
        'không cần mạng.',
        'Xuất Excel lớn nhanh hơn: bảng tổng hợp 3.000 hộ ghi file 1,2 giây còn 0,5 giây (nội dung giống hệt).',
    )),
    ('1.0.39', '30/10/2026', (
        'Đường kẻ khung bản in Excel / Word (phương án chi tiết, bảng tổng hợp, khái toán) dùng màu tự động thay vì đen ghi cứng: mở '
        'trên Excel / Word bật chế độ tối (Dark Mode) vẫn thấy khung (trước đây nét đen nằm trên nền tối - chỉ thấy chữ). In ra giấy '
        'vẫn đen.',
        'Phương án điều chỉnh: đang ở lần "bổ sung" chưa có dòng nào vẫn lập được phương án điều chỉnh (điều chỉnh lần có phương án '
        'muộn nhất) - không còn báo "Hộ không có phương án lần 2". Bản in phương án điều chỉnh không còn đẩy cả khối "Tổng giá trị sau '
        'điều chỉnh" sang trang sau (trang 1 hở); bảng tổng hợp điều chỉnh có khối chữ ký.',
        'Bảng giá đất: công cụ cập nhật nằm ngay trong cửa sổ Bảng giá đất (thẻ "Cập nhật, bổ sung giá đất"), không còn cửa sổ riêng. '
        'Mặc định BỔ SUNG vào bảng đang dùng (giữ các địa bàn khác, thay địa bàn trùng tên) - vẫn chọn được "Thay toàn bộ".',
        'Đọc Nghị quyết bảng giá đất (Word, PDF có chữ, PDF scan, ảnh): phần mềm đọc cả LỜI VĂN hướng dẫn cách tính vị trí 2, 3, 4 không '
        'nằm trong bảng (vd. "vị trí 2, vị trí 3, vị trí 4 lần lượt bằng 70%, 50%, 30% giá đất vị trí 1", "vị trí 3 bằng 80% vị trí 2", '
        '"không thấp hơn …", theo từng loại đất) rồi dựng thêm các vị trí đó từ vị trí 1; bảng "Quy tắc vị trí" sửa / thêm / xóa được, '
        'bấm "Tính lại vị trí". Căn cứ in trên phương án ghi rõ cách tính.',
        'Thẻ Hỗ trợ: hai hàng nhập (Nhân khẩu / Tái định cư và Chính sách hỗ trợ) cách nhau rộng hơn; nút tăng / giảm ô số (Nhân khẩu) vẽ '
        'lại gọn. Ô chọn "Lần lập PA" rộng hơn, hiện đủ tên lần.',
    )),
    ('1.0.38', '30/10/2026', (
        'Ô chọn xổ xuống: danh sách hiện ngay dưới ô, đủ các mục (tới 20 mục, nhiều hơn thì có thanh cuộn) và rộng đủ chữ dài nhất - '
        'không còn bị khuất mục / cắt chữ; màu mục đang chọn và mục dưới con trỏ chuột chuyển sang xanh xám nhạt, dịu mắt.',
        'Bản in phương án chi tiết và bảng tổng hợp: tên đơn vị không còn in lặp hai lần khi ô "Đơn vị cấp trên" hoặc ô "Tên đơn vị trên '
        'tiêu đề bản in (dòng 2)" ghi cả tên đơn vị lập phương án.',
        'Bảng tổng hợp: bước cuối tự kẻ khung cho mọi ô thiếu nét - bảng luôn đủ đường kẻ ô trên mọi máy.',
        'Xuất hồ sơ & Bản in: nút "Xem trước bản Excel các hộ" - xem trước bản Excel phương án chi tiết (mỗi hộ một sheet) trước khi xuất.',
        'Niêm yết: bảng Hộ vướng đổi trạng thái một chạm như cột Ý kiến - bấm ô "Nhóm vướng" (hoặc phím Space): Chưa đánh dấu → Đủ điều '
        'kiện → V1 … V5.',
        'Thẻ Hỗ trợ: ô Tái định cư giãn hết phần còn lại của hàng (đọc được chữ dài), nhãn Nhân khẩu / DT đất NN sát ô, không còn khoảng trống.',
        'Niêm yết - "Thêm hộ vào đợt": bảng mọi hộ chưa có trong đợt với Lập phương án, Tổng tiền, Điều kiện, Ý kiến gần nhất, Đợt hiện '
        'tại; lọc theo từng thuộc tính + ô tìm, bấm tiêu đề cột để sắp xếp; hộ chưa đủ điều kiện / đang vướng vẫn thêm được khi đánh dấu.',
    )),
    ('1.0.37', '30/10/2026', (
        'Tính mật độ cây trồng: tính MỌI loại cây của hộ trên cùng diện tích trồng - cây đơn giá cao hơn tính trước làm cây trồng chính '
        '(trong mật độ tối đa theo diện tích còn lại), diện tích còn dư tính tiếp cho cây đơn giá cao thứ hai… tới khi hết diện tích; '
        'phần vượt mật độ tách thành dòng riêng ngay dưới dòng cây (tỷ lệ vượt mật độ, mặc định 0% - không bồi thường). Tính lại '
        'nhiều lần không cộng dồn; Kiểm tra lỗi và lời nhắc khi nhập số cây cũng theo cách tính này.',
        'Cây trồng xen: đánh dấu "Cây xen" trong hộp Tính mật độ - không xét mật độ, được bồi thường tối đa 0,5 lần giá trị cây '
        'trồng chính (sửa được hệ số); cây xen đơn giá cao tính trước, phần vượt tách dòng riêng không tính tiền, ghi chú theo mẫu '
        '"Phần cây trồng xen vượt quá 0,5 lần giá trị cây trồng chính, không tính toán bồi thường, hỗ trợ."',
        'Tên cây lâu năm theo đúng văn bản: bỏ chú thích "(Năm thứ 3, 4, 5)" (văn bản chỉ ghi Năm thứ 1, 2, 3 và Năm thu hoạch thứ…), '
        'năm tuổi tự tính theo số năm kiến thiết của từng loài; sửa các tên loài sai chính tả / lỗi phông (Bời lời giấy, Muồng truổng, '
        'Trám đỏ, Lekina…), bổ sung mục văn bản có mà bộ đơn giá thiếu (Cây nho thân gỗ năm thu hoạch 6 - 10).',
        'Xuất hồ sơ & Bản in: thêm "Phương án chi tiết - Excel" - các hộ đã chọn trong MỘT file Excel, mỗi hộ một sheet, cùng số liệu '
        'bản Word (số tiền, số lượng là số - cộng, lọc được).',
        'Đọc bản scan (văn bản đơn giá, quyết định): dò đường kẻ khung bảng trên ảnh (cả ảnh hơi nghiêng), xóa nét kẻ trước khi đọc, '
        'đặt chữ vào đúng ô (ô gộp nhiều hàng / nhiều cột), đọc lại riêng từng cột số - phân tách nội dung rõ ràng hơn; tên loài cây '
        'đọc sai dấu được sửa theo tên đã biết.',
    )),
    ('1.0.36', '30/10/2026', (
        'Cập nhật đơn giá: ô "Cách cập nhật" có "Thay thế toàn bộ văn bản cũ bằng văn bản này" - danh mục nhóm (cây trồng / nhà, công '
        'trình / vật nuôi / hỗ trợ) theo đúng văn bản mới: mục cũ đổi tên, mật độ, ghi chú theo cách ghi của văn bản (mã giữ nguyên), '
        'mục mới thêm, mục cũ không còn trong văn bản bị bỏ (dòng đỏ, bỏ dấu "Dùng" để giữ); văn bản cũ ghi "Hết hiệu lực".',
        'Bảng giá cây lâm nghiệp theo nhóm loài x đường kính được tách thành từng loài mỗi cỡ ("Bồ đề (d >6-9 cm)", "Trường (d >6-9 cm)"…) '
        'theo danh sách loài của văn bản (Phụ lục VI); mục mới được cấp mã CT tiếp theo, mã hiện ngay trên bảng xem trước.',
        'Đọc văn bản đơn giá: mật độ "(330 cây/ha)", "(Mật độ 493 cây/ha)" vào ghi chú, không dính vào tên; "Năm thứ 1" của văn bản khớp '
        '"Năm 1" của bộ đơn giá (trước đây thêm thành mục trùng).',
    )),
    ('1.0.35', '29/10/2026', (
        'Giao diện mặc định mới "Sáng dịu Slate-Navy": màu xanh hạ độ chói, menu trái nền sáng liền mạch với vùng làm việc, lệnh đang chọn '
        'nền xanh nhạt có vạch trái.',
        'Cài đặt > Giao diện có 7 tông: Sáng dịu (mặc định), Titan (menu trái than chì, bảng sáng), Ấm áp (giấy kem), Xanh ngọc, Tối '
        'chuyên gia, Dịu mắt, Trắng tương phản; mỗi tông đổi cả màu chính, băng tiêu đề và menu trái.',
        'Tông Tối: hết các ô / dòng còn nền sáng - ô chỉ đọc trong bảng phương án, 3 dòng Cộng / Kinh phí / Tổng của Bảng tổng hợp, dòng '
        'con tiền đất, số tiền, dải tổng cuối cửa sổ lập phương án, dải trạng thái.',
    )),
    ('1.0.34', '29/10/2026', (
        'Giao diện mới "Flagship Sapphire" ngay khi mở phần mềm: màu chủ đạo Royal Sapphire, nền xám sứ làm nổi các thẻ trắng; menu trái '
        'nền tối, mỗi lệnh một viên bo tròn, lệnh đang chọn nổi bật màu xanh; thu gọn / mở rộng menu và chuyển trang có hiệu ứng trượt nhẹ.',
        'Thêm tông nền Tối chuyên gia (Dark Studio) và Ấm áp; nút "Tối / Sáng" trên băng tiêu đề màn hình chào đổi giao diện bằng một cú '
        'bấm (Cài đặt > Giao diện có ô xem trước màu từng tông).',
        'Thẻ màn hình chào mỗi thẻ một màu, có huy hiệu biểu tượng và phím tắt; thẻ số liệu có thanh tiến độ; bảng chưa có dữ liệu có '
        'hình minh họa.',
        'Số lượng / diện tích: số gõ trực tiếp giữ nguyên (28,35 m² không còn bị làm tròn thành 28,4); kết quả công thức (3 x 4,1…) làm '
        'tròn 2 chữ số lẻ (ha: 4); mở dự án tự tính lại các dòng đã nhập bằng công thức (lần phương án đã phê duyệt giữ nguyên).',
        'LARC Mobile 1.0.34: màu Sapphire, nút 🌙 Đêm (chế độ ban đêm, nhớ trên máy), hai nút lớn dạng thẻ có dòng mô tả, thanh mục con / '
        'thanh đáy dạng kính mờ, hiệu ứng chuyển trang và thẻ kết quả.',
    )),
    ('1.0.33', '28/10/2026', (
        'Cài đặt > Giao diện: chọn TÔNG NỀN bề mặt - Sáng chuẩn, Dịu mắt (làm việc lâu / ban đêm), Trắng tương phản (máy chiếu / ngoài '
        'trời); áp ngay cho mọi cửa sổ đang mở, nhớ cho lần sau.',
        'Nhập bản đồ (.dxf, .kml, .kmz): file chỉ đọc / giải nén một lần (đọc danh sách lớp rồi phân tích dùng chung); bấm Phân tích lại '
        'với cùng lớp / số tờ / kinh tuyến trục không phân tích lại (giữ các ô đã đánh dấu); bảng thửa vẽ một lần.',
        'Bản đồ thửa đất: thêm tổng số thửa và tỷ lệ đồng thuận cạnh chú giải. Thẻ số liệu: Tổng kinh phí vạch xanh, Đã bàn giao vạch xanh '
        'lá; rê chuột viền rõ hơn. Ô đang sửa trong bảng: chữ chọn nền xanh nhạt dễ đọc. Mật độ bảng Gọn: đầu cửa sổ lập phương án sát hơn.',
        'LARC Mobile 1.0.33: trung tâm thu âm trượt lên từ đáy màn hình (bấm một tay), bàn phím ảo mở thì hộp nằm trên bàn phím; thanh mục '
        'con dạng viên, mục đang chọn nổi bật; thẻ nổi nhẹ; thẻ thông tin thửa trên bản đồ toàn màn hình rõ hơn; chế độ ☀️ Nắng: tiền '
        'tạm tính nền vàng chữ đen.',
    )),
    ('1.0.32', '28/10/2026', (
        'Công cụ > Tạo gói cấu hình cho nhiều đơn vị: điền file Excel mẫu (mỗi dòng một chi nhánh / đơn vị: tên cơ quan, đơn vị lập, '
        'địa danh, người ký…), phần mềm tạo mỗi đơn vị một gói .pabtcfg - máy của đơn vị bấm đúp gói là có đủ thông tin cơ quan. Cấu hình '
        'của máy tạo gói không đổi.',
        'Bản đồ: Dữ liệu > Nhập bản đồ nhận thêm file Google Earth .kml / .kmz (bản đồ địa chính xuất ra KMZ: đọc số tờ, số thửa, loại '
        'đất; chữ lỗi phông TCVN3 tự sửa), quy đổi tọa độ GPS sang VN-2000 (kinh tuyến trục theo hồ sơ địa phương); bản đồ thửa hiện tọa '
        'độ VN-2000 / GPS khi rê chuột, nút "Xuất KML / KMZ…" để mở trên điện thoại / Google Earth.',
        'Ứng dụng điện thoại LARC Mobile: Phiếu kiểm đếm thực địa > "Xuất dữ liệu cho ứng dụng điện thoại…"; nhập kết quả .json khớp hộ '
        'theo CCCD, rồi tờ / thửa (hoặc lô rừng), rồi họ tên; hộ ghi mới ngoài hiện trường thêm được; ảnh hiện trạng lưu vào thư mục '
        'Anh_kiem_dem cạnh file dự án, tọa độ GPS ghi vào ghi chú hộ.',
        'Dán danh sách tài sản hiểu biên bản kiểm đếm viết tự nhiên: kích thước "4,7 x 3,0 m" = diện tích, nhiều cụm "(a x b) + (c x d)", '
        'dòng gộp nhiều cỡ ống ("ϕ 114: 3300m; ϕ 90: …"), "trồng năm 2015" -> tuổi cây, "ĐK gốc 10-15 cm", giếng "sâu 20 m"; ống / giếng '
        'khớp mục đơn giá theo vật liệu và cỡ.',
        'Gắn ảnh hiện trạng, hồ sơ đính kèm, nhập phiếu .json: kiểm tra loại file thật theo nội dung (chặn chương trình đổi đuôi thành ảnh).',
        'Máy chủ LAN: nút "Trả bớt hộ đã nhận…" (bản offline theo hộ: gộp số liệu một số hộ lên máy chủ rồi trả để người khác làm tiếp) '
        'và "Nhật ký máy chủ…" (ai làm gì, lúc nào trên máy chủ; chép dán sang Excel được).',
        'Tra bảng giá đất: tỉnh dùng vị trí VT1-VT4 hoặc Khu vực - Vị trí thì cột Vị trí ghi tên vị trí đầy đủ.',
        'Phóng to chữ (A+): chữ trên các thẻ của màn hình chào cũng to theo. Lệnh menu trái đang tắt dễ đọc hơn. Ctrl+Tab báo tên màn '
        'hình vừa chuyển tới.',
        'Mở phần mềm bằng "PABT.exe --khung-windows" (dùng khung cửa sổ Windows) chạy đúng - trước đây chỉ in hướng dẫn dòng lệnh. '
        'Văn bản Word xuất ra bỏ ký tự điều khiển lẫn trong chữ (Word báo file hỏng).',
    )),
    ('1.0.31', '26/10/2026', (
        'Bộ đơn giá cây trồng: các loài cây lâm nghiệp ghi thêm tên Việt Nam khác theo Phụ lục VI QĐ 48/2025/QĐ-UBND (ví dụ "Bách xanh '
        '(Tùng hương) (d >6-9 cm)") - tìm cây theo tên gọi nào cũng ra. Dự án đang có và bộ đơn giá đã cập nhật trên máy tự thêm khi mở; '
        'phương án đã lập giữ nguyên tên cũ.',
        'Máy chủ LAN - bản offline theo hộ: mọi thao tác ghi theo hộ (xóa / gộp hộ, chuyển thửa, lập PA bổ sung / điều chỉnh, quyết định, '
        'chi trả, bàn giao, niêm yết, vận động, đợt trình, số PA, hồ sơ đính kèm) chỉ làm được trên hộ đã nhận; hộ không nhận mở ra chỉ xem.',
        'Dùng cho tỉnh khác: khoản thuê nhà / tự lo chỗ ở khai báo mã riêng không còn báo lỗi khi chọn hoặc đổi nhân khẩu; mức cộng mỗi '
        'khẩu vượt khai báo được trong hồ sơ địa phương (chinh_sach_ho_tro.muc_khau_vuot).',
        'Tra bảng giá đất nhanh hơn khi tự lập phương án nhiều hộ.',
    )),
    ('1.0.30', '26/10/2026', (
        'Dòng "<địa danh>, ngày … tháng … năm …" của phương án chi tiết, bảng tổng hợp, tờ trình ghi NƠI ĐƠN VỊ CÔNG TÁC, không còn lấy '
        'xã / phường có đất của dự án. Nhập ở Thông tin dự án > "Địa danh nơi đơn vị công tác" (giữ cho dự án mới); để trống thì theo hồ sơ '
        'địa phương, chưa có thì để chỗ trống.',
    )),
    ('1.0.29', '26/10/2026', (
        'Máy chủ LAN - chia việc: nút "Nhận theo hộ (Chia việc)" ở Dự án trên máy chủ mở hộp chọn hộ (tìm theo tên, CCCD, tờ/thửa; lọc '
        'theo đợt, ấp; chọn nhanh theo khoảng STT); hộ người khác đang nhận hiện tên người / máy và không chọn được. Đưa lên mà có hộ bị sửa '
        'trên máy chủ: liệt kê từng hộ và hỏi ghi đè hay hủy để kiểm tra.',
        'Mở bản offline theo hộ: thanh danh sách hộ ghi "Chế độ Nhận việc theo hộ (Đang nhận N hộ)" kèm ô "Chỉ hiện hộ tôi nhận"; hộ '
        'không nhận vẫn xem được nhưng không lưu được (sẽ không được gộp lên máy chủ).',
        'Dùng cho tỉnh khác: mã chính sách hỗ trợ khai báo trong hồ sơ địa phương được dùng khi tính (ổn định đời sống, thuê nhà / tự lo '
        'chỗ ở, tái định cư); bảng giá đất theo mô hình Vị trí 1-4 hoặc Khu vực - Vị trí có ô lọc vị trí và tên vị trí đọc được. '
        'Cấu hình nghiệp vụ có nút "Khởi tạo danh mục mẫu cho tỉnh mới…" tạo file hồ sơ mẫu.',
        'Xuất hồ sơ & Bản in: khung tùy chọn bên trái không còn thanh cuộn ngang ở màn hình 1536 px, tỷ lệ 125%.',
    )),
    ('1.0.28', '26/10/2026', (
        'Máy chủ LAN - nhiều chuyên viên cùng một dự án: mỗi người nhận một nhóm hộ về làm offline (chỉ khóa các hộ đó, không khóa cả dự án) rồi gộp '
        'đúng các hộ đó lên lại; hộ của người khác giữ nguyên. Thửa mới thêm ở hai máy trùng mã được tự đánh lại; hộ bị sửa trên máy chủ trong lúc làm '
        'offline thì báo xung đột trước khi ghi; file trên máy chủ được sao lưu trước mỗi lần gộp.',
        'In phương án chi tiết hàng loạt nhanh hơn: số liệu dự án, hộ, nguồn gốc, phương án đọc một lần cho cả lô thay vì từng hộ.',
        'Máy không có Microsoft Word: nếu máy có LibreOffice thì xuất PDF bằng LibreOffice (đúng bố cục hơn), không có mới dựng PDF gần đúng.',
        'Chuẩn bị dùng cho tỉnh khác: hồ sơ địa phương ghi được mô hình vị trí bảng giá đất (Vị trí 1-4, Khu vực - Vị trí) và mã các chính sách hỗ trợ; '
        'chính sách không theo mã Đồng Nai được nhận theo tên.',
    )),
    ('1.0.27', '24/10/2026', (
        'Dự án mới - nhập danh sách hộ, thửa: đọc được file Excel .xlsx và .xls (cũ), PDF có chữ (văn bản đã ký hay chưa ký), PDF scan và ảnh '
        '(.png, .jpg…). Phần mềm tự tìm bảng, dòng tiêu đề, nhận cột theo tên (kể cả tên viết sai do nhận dạng chữ) hoặc theo nội dung ô; '
        'cột nào phần mềm có mà file không có thì bỏ qua. Ô xuống nhiều dòng, tiêu đề lặp lại ở trang sau, chữ ký cuối bảng được xử lý.',
        'Không nhận được cột: hộp "Chỉnh cột…" cho chọn cột nào là họ tên, tờ, thửa, diện tích… và cho biết đã bỏ những dòng nào; '
        'file chỉ có tờ, thửa (không có họ tên) vẫn nhập được thành hộ tạm.',
        'Bản thương mại: phần mềm không còn ghi sẵn tên cơ quan nào (băng tiêu đề, bản in, Giới thiệu, cửa sổ cài đặt); nhập tên đơn vị ở Cài đặt > '
        'Cấu hình nghiệp vụ > Cơ quan (ô còn trống có chữ gợi ý) hoặc ở Thông tin dự án.',
        'Cửa sổ cài đặt thiết kế lại: banner gọn, thẻ trạng thái 4 loại, dung lượng cần / ổ còn trống, thanh tiến trình có phần trăm, Gỡ cài đặt thành '
        'liên kết, nút Mở LARC sau khi cài, xem nhật ký; chữ sắc nét ở màn hình 125% / 150%.',
    )),
    ('1.0.26', '24/10/2026', (
        'Dùng cho nhiều đơn vị: tên phần mềm ở dòng 1 băng tiêu đề đổi được (Cài đặt > Cấu hình nghiệp vụ > Cơ quan > "Tên phần mềm"); có bản hồ sơ địa '
        'phương TRUNG TÍNH (không có tên đơn vị, địa phương, căn cứ pháp lý của nơi nào) để đóng vào bộ cài bán cho đơn vị khác (DUNG_BAN_TRUNG_TINH.bat).',
    )),
    ('1.0.25', '24/10/2026', (
        'Đổi tên tổ chức ở Cài đặt > Cấu hình nghiệp vụ > Cơ quan: dòng tên đơn vị trên băng tiêu đề đổi ngay cả khi chưa mở dự án (trước đó phải mở dự án mới thấy).',
    )),
    ('1.0.24', '24/10/2026', (
        'Sửa lỗi 1.0.23: mở hộp Xuất hồ sơ & Bản in hiện thêm một cửa sổ trống nhấp nháy (khung "Đầu ra và nơi lưu" chưa có cửa sổ cha khi gấp / mở).',
    )),
    ('1.0.23', '24/10/2026', (
        'Xuất hồ sơ & Bản in gọn hơn: bảng hộ giãn theo chiều cao hộp, bấm tiêu đề cột để sắp xếp (tiền sắp theo số), thêm cột Đợt và Địa chỉ '
        '(ô tìm cũng tìm theo hai cột này); bộ đếm vùng chọn nằm dưới bảng (không đè lên cột tiền); Đợt trình và Hộ cần in cùng một hàng; '
        'bỏ nút "Chọn tất cả mẫu / Bỏ chọn mẫu" và "Chọn hộ đã lập" (trùng); "Sửa mẫu…" nằm cạnh ô Tờ trình; khung "Đầu ra và nơi lưu" gấp được; '
        'nhớ đầu ra, gộp PDF, số bản, thư mục lần trước (không nhớ "in ra máy" để khỏi in nhầm).',
        'Xem trước: nút "Vừa ngang" (trang vừa bề ngang khung, chữ to hơn "Vừa trang").',
        'Cài đặt > Cấu hình nghiệp vụ > Kiểm tra & bản in: ô nhập lề trang in bảng tổng hợp A3 (trái / phải / trên / dưới, cm). Bảng tổng hợp: '
        'dòng đầu (cơ quan, CHI NHÁNH) sát chữ hơn.',
    )),
    ('1.0.22', '24/10/2026', (
        'Xuất hồ sơ & Bản in: nút "Xem trước gộp các hộ đã chọn" - lập phương án chi tiết của nhiều hộ đang đánh dấu (tối đa 30 hộ một lần) '
        'thành MỘT bản PDF ở khung xem trước, có ô "Nhảy tới hộ" và in cả bản bằng nút "In…". Máy không có Word: bản gần đúng dựng bằng Qt.',
    )),
    ('1.0.21', '24/10/2026', (
        'Mục I của phương án chi tiết trở lại đúng yêu cầu: chủ sử dụng là tổ chức -> "I. Thông tin về tổ chức"; hộ gia đình, cá nhân -> '
        '"I. Thông tin về hộ gia đình, cá nhân" (bản 1.0.19 đã ghi đè bằng tiêu đề chung của mẫu PDF).',
        'Phương án chi tiết (Word): khối LẬP BIỂU - KIỂM TRA - chức vụ ký dịch sang trái (lề trái và lề phải cân nhau); đường kẻ dưới tên dự án '
        'gần chữ hơn (vẫn có khe nhỏ); đường kẻ dưới "CHI NHÁNH …" ngắn hơn chữ 1 cm; đường kẻ dưới "Độc lập - Tự do - Hạnh phúc" bằng chữ; '
        'nhãn "DỰ ÁN" in hoa khi tên dự án in hoa, ngược lại "Dự án".',
        'Bảng tổng hợp: dòng 1 cơ quan chủ quản, dòng 2 "CHI NHÁNH …" (đậm, gạch chân ngắn hơn chữ 1 cm) - không còn mất chữ CHI NHÁNH; bản dự '
        'thảo có "(DỰ THẢO)" ngay dưới, bản chính thức không có; nhãn "DỰ ÁN" / "Dự án" theo tên dự án; đường kẻ dưới tên dự án gần chữ hơn.',
    )),
    ('1.0.20', '23/10/2026', (
        'Bảng tổng hợp kinh phí không còn đọc file mẫu Excel: bố cục, định dạng, khổ giấy A3 dựng hoàn toàn bằng mã trong phần mềm (kết quả '
        'in giữ nguyên). Không còn thư mục mẫu in Excel, mẫu nhúng hay gói mẫu Excel - phần mềm không đọc lệnh nào từ file Excel mẫu bên ngoài.',
        'Quản lý Mẫu in & Bản in chỉ còn quản lý thông số mẫu Word (xuất / nhập / khôi phục); gói .pabtcfg vẫn mang hồ sơ địa phương và mẫu tờ trình.',
    )),
    ('1.0.19', '23/10/2026', (
        'Phương án chi tiết CHỈ còn bản Word: bỏ hẳn mẫu Excel IN_CHITIET (mẫu in, mẫu nhúng, mã dựng bản Excel chi tiết). Máy không có '
        'Microsoft Word: xem trước và PDF là bản gần đúng dựng bằng Qt từ chính file Word (không còn đọc Excel). Bảng tổng hợp vẫn là Excel.',
        'An toàn dữ liệu in: mọi file Excel xuất ra đi qua một cổng lưu; chữ do người dùng gõ bắt đầu bằng dấu "=" (họ tên, địa chỉ, '
        'ghi chú…) không còn trở thành công thức Excel (chặn lệnh độc như =HYPERLINK).',
        'Mẫu Word phương án chi tiết chỉnh theo mẫu PDF mới: lề trái 9 / phải 7 / trên, dưới 10 mm; chữ thân 10,5 pt, bảng 10 pt, ghi chú '
        '7,5 pt; tiêu đề "I. Tổ chức và hộ gia đình, cá nhân bị thu hồi đất, tài sản gắn liền với đất", "II. Thông tin nguồn gốc đất:", '
        '"Phương án tái định cư:"; tên dự án chữ thường, có đường kẻ ngắn CÁCH chữ (không sát, không mất dấu); bảng viền ngoài đậm; '
        'khối LẬP BIỂU - KIỂM TRA - chức vụ ký chia đều ba phần bằng nhau, chữ ở giữa từng phần. Đổi cỡ chữ / lề trong Quản lý Mẫu in.',
        'Cài đặt > Giao diện…: mật độ bảng Gọn / Chuẩn / Thoáng và tương phản cao theo Windows.',
    )),
    ('1.0.18', '23/10/2026', (
        'Sửa mẫu Word phương án chi tiết, bổ sung, điều chỉnh: dòng "CHI NHÁNH …" (đậm, gạch chân) luôn có ở đầu văn bản, kể cả dự án lập '
        'từ file Excel cũ có ô tên đơn vị trên tiêu đề ghi "Thành phố Đồng Nai". Dòng "Số: …" và "địa danh, ngày …" vẫn ngang hàng nhau.',
    )),
    ('1.0.17', '23/10/2026', (
        'Giao diện 2.0 - nền tảng: Cài đặt > Giao diện… chọn mật độ bảng Gọn / Chuẩn / Thoáng (áp ngay cho mọi bảng đang mở, '
        'màn hình 1366 x 768 chọn Gọn thấy thêm ~4 dòng).',
        'Hỗ trợ chế độ tương phản cao của Windows: phần mềm dùng bảng màu hệ thống thay cho màu riêng (Theo Windows / Luôn bật / Tắt, '
        'đổi có hiệu lực khi mở lại). Chưa có giao diện nền tối.',
    )),
    ('1.0.16', '22/10/2026', (
        'Bản in Word phương án chi tiết, bổ sung, điều chỉnh theo đúng khung sườn mẫu PA_01: lề trái 1,5 cm, phải / trên / dưới 1 cm; '
        'đầu văn bản thêm dòng "CHI NHÁNH …" (lấy từ Thông tin dự án) đậm, gạch chân; "Số: …" và "địa danh, ngày …" nằm cùng một '
        'hàng, ngang nhau.',
        'Trích yếu một dòng "BỒI THƯỜNG, HỖ TRỢ & TÁI ĐỊNH CƯ KHI NHÀ NƯỚC THU HỒI ĐẤT"; có đường kẻ ngang ngắn ngay dưới tên dự án; mục '
        'II mọi đoạn (kể cả gạch đầu dòng) thụt dòng đầu 1 cm, dòng sau về sát lề trái.',
        'Cỡ chữ: cơ quan, quốc hiệu, "Số:", ngày, "(DỰ THẢO)", nguồn gốc, bảng 13; tiêu ngữ, tên văn bản, trích yếu, dự án, mục I - IV 14; '
        'ghi chú 11; LẬP BIỂU / KIỂM TRA / chữ ký 15. Đường gạch chân dưới tên đơn vị, tiêu ngữ có khe hở, không sát chữ (khỏi mất dấu). '
        'Cột bảng tự thu vừa chữ, nhường chỗ cho Tên tài sản / Ghi chú.',
        'Mẫu Word nhúng sẵn trong phần mềm, bản cài không còn thư mục mau_in. Đổi quy cách khi có quy định mới: Công cụ > Quản lý Mẫu in '
        '& Bản in > Nhập thông số mẫu Word (hoặc nhập gói .pabtcfg) - áp ngay, không cần cập nhật phần mềm.',
        'Màu chủ đạo dịu hơn: thanh tiêu đề bảng, nút chính, banner đổi từ xanh navy rất đậm sang xanh cobalt dịu (#1E3A5F, chữ trắng '
        'tương phản 6,5:1). Các màu xanh / đỏ / lá / cam gom về một tông dịu mỗi loại, bớt chói.',
        'Màn lập phương án và danh sách hộ ở màn hình 1366 phóng 125%: nút, nhãn, tên thẻ không còn bị cắt chữ; vùng bấm tối thiểu 24 px.',
        'Sửa lỗi: cửa sổ rỗng (chỉ có nút thu nhỏ / phóng to / đóng) nhấp nháy khi bật xem trước F4, mở Bàn giao mặt bằng và Bản đồ thửa '
        'đất - do nút / nhãn bị hiện trước khi vào bố cục. Kiểm tra giao diện nay báo mục "Cửa sổ lạ".',
    )),
    ('1.0.15', '22/10/2026', (
        'Phương án ĐIỀU CHỈNH: sửa phương án đã lập / đã phê duyệt bị sai bằng nút "+ Lập PA điều chỉnh" trong cửa sổ lập phương án. '
        'Lần gốc giữ nguyên để in; tổng của hộ tính theo lần điều chỉnh (không cộng đôi), quyết định điều chỉnh ghi số chênh lệch.',
        'Bản in Word có ba mẫu nhúng sẵn trong phần mềm (chi tiết, bổ sung, điều chỉnh) tự chọn theo loại lần; mẫu điều chỉnh gồm '
        'A. đã phê duyệt, B. đề nghị điều chỉnh, C. chênh lệch. Thêm bảng tổng hợp phương án điều chỉnh (A3, .xlsx) trong Xuất hồ sơ & Bản in.',
    )),
    ('1.0.14', '22/10/2026', (
        'Phương án chi tiết từng hộ xuất bằng bản Word (.docx) theo Nghị định 30 ở MỌI nơi: xem trước F4 trong cửa sổ lập phương án, '
        'khung xem trước của Xuất hồ sơ & Bản in, xuất hồ sơ đợt, Dự án mới. Không còn bản Excel phương án chi tiết; PDF, in ra máy '
        'và file PDF gộp cả đợt lấy từ bản Word. Máy không có Microsoft Word: xem trước / PDF là bản gần đúng phần mềm tự dựng.',
        'Bản Word: tên cơ quan một dòng như mẫu; tên chủ hộ / tổ chức in đậm, nhãn chữ thường; cột Ghi '
        'chú, Tên tài sản rộng theo nội dung từng hộ (ghi chú dài không còn kéo dòng cao nửa trang).',
        'Bảng tổng hợp A3: hộ có nhiều thửa ghi STT, họ tên, địa chỉ, tổng cộng, phương án tái định cư, ghi chú trong MỘT ô gộp cho '
        'cả hộ (không lặp lại từng dòng); mỗi thửa một dòng với tờ, thửa, loại đất, diện tích, tiền đất và nguồn gốc riêng của thửa.',
        'Phương án chi tiết bản Word: cơ quan, quốc hiệu 13; tiêu ngữ, ngày, trích yếu, tên dự án, nội dung, bảng và khối chữ ký 14; '
        '"PHƯƠNG ÁN CHI TIẾT" 15. Nguồn gốc đất giãn dòng đơn, các đoạn / gạch đầu dòng cách nhau 6 pt.',
        'Bản Word: mục III in tiếp ngay dưới mục II khi trang còn chỗ; khối chữ ký luôn đi liền dòng TỔNG CỘNG (không còn trang chỉ có '
        'chữ ký); quốc hiệu một dòng, trích yếu ngắt hai dòng đúng nghĩa, tên cơ quan dài ngắt hai dòng cân nhau.',
        'Giao diện gọn và đồng nhất hơn: ô chọn có mũi tên mảnh (bỏ vạch đen); mọi thẻ số liệu dùng một kiểu (số cùng màu chữ chính, '
        'màu nhận diện chỉ ở vạch trái); tên thẻ, tiêu đề khung viết thường; không còn chữ bị cắt trên thẻ số liệu, dải lần lập phương '
        'án, cột Vị trí / Nguồn gốc.',
        'Cửa sổ lập phương án: thẻ Thông tin hộ, thửa đất cuộn dọc khi màn hình thấp (không còn ép bẹp ô nhập và bảng thửa). Bảng cơ '
        'cấu kinh phí mỗi khoản một dòng; bảng Tiến độ cột mốc thu hồi ghi gọn (đủ chữ khi rê chuột). Màn hình 1366: 4 thẻ bắt đầu '
        'không còn chồng lên nhau.',
    )),
    ('1.0.13', '22/10/2026', (
        'Phương án chi tiết (bản Excel và bản Word): tiêu đề mục I theo chủ sử dụng - "I. Thông tin tổ chức" khi chủ sử dụng là tổ '
        'chức (chỉ ghi Tổ chức, Địa chỉ; không có dòng CCCD, điện thoại), "I. Thông tin hộ gia đình, cá nhân" với hộ / cá nhân '
        '(Họ và tên, Số CCCD, Địa chỉ thường trú, Số điện thoại - dòng trống được bỏ).',
    )),
    ('1.0.12', '22/10/2026', (
        'Giao diện đổi sang tông xanh navy đậm hơn, chữ tương phản cao (dễ đọc trên màn hình độ sáng thấp, máy chiếu); bố cục, '
        'số dòng bảng nhìn thấy giữ nguyên.',
        'Ô đang nhập có viền xanh 2 px nổi rõ - biết ngay con trỏ đang ở ô nào; chữ trong ô không xê dịch khi bấm vào.',
        'Tiêu đề cột bảng có vạch xanh phía dưới; thẻ mục đang mở trong cửa sổ lập phương án (Đất, Nhà, Cây trồng…) chữ xanh, gạch '
        'chân đậm; ô Tổng kinh phí phương án trên dải chủ hộ nền vàng hổ phách.',
        'Viền vùng ô đang chọn (kiểu Excel) đổi sang xanh ngọc lục bảo.',
    )),
    ('1.0.11', '21/10/2026', (
        'Bảng trên mọi màn hình chọn ô như Excel: kéo chuột bôi đen một vùng, Ctrl / Shift chọn thêm; bấm ô STT chọn cả dòng. '
        'Vùng chọn có viền xanh; góc dưới hiện Trung bình · Tổng số đếm · Tổng của các ô số (bấm vào để chép Tổng).',
        'Thẻ số liệu Danh sách hộ ghi thêm số thửa và diện tích; bấm "Lọc: … hộ · … thửa" (hoặc Ctrl+Shift+T, menu Dữ liệu) mở hộp '
        'Thống kê Hộ · Thửa · Diện tích theo trạng thái và theo đợt.',
        'Bản in phương án chi tiết không còn hở trắng cuối trang 1: các mục không có dòng (0 đồng) được xếp tiếp ngay dưới mục 1, '
        'chỉ dòng TỔNG CỘNG và chữ ký giữ liền nhau; nội dung tràn ít được gom gọn vào một trang A4.',
        'Bảng tổng hợp A3: cột tiền toàn số 0 thu hẹp, nhường chỗ cho nguồn gốc đất; dòng thửa có nguồn gốc dài không còn mất chữ; '
        'mỗi trang được lấp đầy trước khi sang trang mới.',
        'Xuất hồ sơ & Bản in: thêm tùy chọn "Xuất bản Word (.docx) chuẩn Nghị định 30" cho phương án chi tiết (A4, lề trái 30 mm, '
        'phải 15 mm, trên / dưới 20 mm; hàng tiêu đề bảng lặp mỗi trang). Ô này tích sẵn và nhớ lựa chọn lần trước; chọn thêm '
        '"Gộp PDF" thì Word chuyển từng hộ sang PDF rồi gộp thành một file PHUONG_AN_CHI_TIET.pdf trong thư mục đợt, in một lần.',
        'Xuất hàng loạt bằng Word không còn bị kẹt: một hộ Word không xong sau 15 giây (kẹt hộp thoại ẩn, máy in) được bỏ qua, '
        'Word mở lại làm tiếp các hộ sau; hộ Word không xuất được (hoặc máy không có Word) được dựng PDF gần đúng từ bản Excel, '
        'tệp gộp vẫn đủ hộ.',
        'Bản in phương án chi tiết (Word và Excel): nguồn gốc đất không còn cụt chữ giữa câu - các chỗ xuống dòng giữa câu trong dữ '
        'liệu (ô Excel nhập vào, chữ dán) được nối lại; đoạn mới chỉ ở gạch đầu dòng hoặc sau dấu hết câu. Bản Excel chia đoạn dài '
        'sang dòng mới đúng chỗ hết câu.',
        'Bản Word theo đúng cỡ chữ Nghị định 30/2020: tên cơ quan, quốc hiệu, số ký hiệu 12; tiêu ngữ (gạch dưới đúng độ dài chữ), '
        'địa danh - ngày, trích yếu, nội dung 13; "PHƯƠNG ÁN CHI TIẾT" 14; bảng 12. Trích yếu ghi "HỖ TRỢ VÀ TÁI ĐỊNH CƯ" (bỏ ký '
        'tự "&") ở cả bản Word và Excel.',
        'Bảng tổng hợp A3: lề trái 2,0 cm, phải 1,0 cm, trên / dưới 1,5 cm; bảng kéo rộng sát lề phải (phần thêm chủ yếu cho cột '
        'nguồn gốc đất, rồi họ tên, địa chỉ) - hết khoảng trắng rộng bên phải.',
    )),
    ('1.0.10', '20/10/2026', (
        'Dán danh sách tài sản hiểu kích thước là diện tích: "Nhà tạm 4,7x3,0", "Nhà tạm 4,7*3,0", "Nhà tạm 3,7m x 4,3m", '
        '"Nhà tạm 3,7 * 4,3" đều thành m² (khối lượng = dài × rộng, phép tính hiện ở chú thích ô Số lượng) và xếp vào mục Nhà, '
        'công trình. Dán từ Excel cũng nhận ô "3,7m x 4,3m" hoặc "42m2".',
        'Chữ trong ngoặc sau số liệu được đưa vào ghi chú: "Nhà tạm 42m2 (thửa 123)" -> 42 m², ghi chú "thửa 123".',
    )),
    ('1.0.09', '20/10/2026', (
        'Sửa lỗi: ở một số máy, xem trước / in phương án chi tiết mất toàn bộ khung bảng mục III và số không định dạng (Tỷ lệ 0,8 thay '
        'vì 80%, Đơn giá 720000 thay vì 720.000). Bảng mục III nay luôn được kẻ khung đầy đủ và định dạng số chuẩn, dù mẫu in trên máy '
        'là mẫu cũ thiếu khung.',
        'Mẫu in cũ trong %APPDATA%\\PABT\\mau_in bị thiếu khung / định dạng (thường lấy từ file Excel PABT cũ) được tự bỏ qua - in theo '
        'mẫu chuẩn. Mẫu anh / chị chủ động thay qua Công cụ → Quản lý Mẫu in & Bản in vẫn được dùng.',
        'Bản xem trước gần đúng (máy không có Microsoft Excel): khung bảng rõ nét, không còn hiện mã hộ ẩn dưới dòng dự án.',
        'Sửa lỗi: thêm hộ (kể cả hộ chỉ có tài sản, không có tờ thửa), lưu phương án rồi chuyển sang Danh sách hộ / Màn hình chính mà '
        'chưa bấm Đóng cửa sổ hộ thì danh sách không hiện hộ mới. Nay chuyển trang là cập nhật ngay.',
    )),
    ('1.0.08', '20/10/2026', (
        'Máy cấu hình yếu (RAM dưới 4 GB hoặc CPU 2 nhân) được tự nhận ra: tắt hiệu ứng đổ bóng, nhận dạng chữ (OCR) chỉ dùng một luồng '
        'để chuột và giao diện không bị đơ, ảnh xem trước bản in tối đa 120 dpi, tự trả bộ nhớ sau khi đóng cửa sổ lập phương án hoặc '
        'xuất bản in hàng loạt.',
        'Phóng to / thu nhỏ cỡ chữ (A+ / A−) nhanh hơn khoảng 3 lần: các trang đang ẩn được dựng lại khi mở tới.',
        'Kéo thả file từ Windows Explorer vào cửa sổ: dự án .larc / .pabt (mở), gói cập nhật .larcud (cài), gói mẫu in .pabtcfg (cài), '
        'Excel .xlsx / .xlsm (nhập).',
        'Mỗi lần mở dự án để sửa, phần mềm tự sao lưu một bản vào thư mục sao_luu_tu_dong (giữ 5 bản gần nhất mỗi dự án) - phòng mất '
        'điện, ổ cứng cũ hỏng file.',
        'Thay mẫu in bằng file Excel khác: tự áp cả cỡ chữ chuẩn (tiêu đề 16 pt đậm, nội dung 14 pt) cùng khổ giấy, tỷ lệ, lề.',
    )),
    ('1.0.07', '20/10/2026', (
        'Bộ mẫu in chuẩn nhúng sẵn trong phần mềm: máy mới cài, chưa có thư mục mẫu in vẫn xuất phương án chi tiết và bảng tổng hợp '
        'đủ đường kẻ. Mẫu đã sửa trong %APPDATA%\\PABT\\mau_in vẫn được ưu tiên.',
        'Bảng tổng hợp in khổ A3 ngang, tỷ lệ cố định 55% (trước: A4 co còn 20-27%, chữ rất nhỏ); chữ nội dung 14 pt, tiêu đề 16 pt '
        'đậm; cột chữ tự chia lại cho vừa đúng khổ giấy, tiêu đề cột không bị cắt đôi từ.',
        'Phương án chi tiết A4 dọc, tỷ lệ in cố định 72% (chỉ tràn vài dòng thì thu tới 70% cho vừa 1 trang), lề trái 0,8 cm, phải '
        '0,3 cm, trên 1,0 cm, dưới 0,8 cm; quốc hiệu, tên cơ quan, tên phương án, dự án, tiêu đề mục I-IV và hàng tiêu đề bảng 16 pt '
        'đậm, nội dung 14 pt, cột Ghi chú 11,5 pt; mục I không kẻ viền, nhãn đậm - nội dung thường, số CCCD / điện thoại không còn tam '
        'giác xanh của Excel; nguồn gốc đất thụt đầu dòng 8 khoảng trắng, bỏ dấu cách thừa trước gạch đầu dòng; tiêu đề "II. Thông tin '
        'vị trí, nguồn gốc đất:". Bản dự thảo không in khối chữ ký (Lập biểu - Kiểm tra - Lãnh đạo).',
        'Công cụ → Quản lý Mẫu in & Bản in (Ctrl+Shift+M): 3 mẫu (chi tiết chính thức, chi tiết dự thảo, bảng tổng hợp) - xem mẫu đang '
        'dùng là mẫu nhúng chuẩn hay mẫu tùy chỉnh, thay bằng file Excel khác (tự áp chuẩn khổ giấy, tỷ lệ, lề), xuất mẫu ra Excel để '
        'sửa, khôi phục mẫu chuẩn gốc (mẫu cũ giữ bản sao). Thay chỗ lệnh "Cập nhật mẫu in…".',
        'Màn hình chính khi đã mở dự án là bảng tổng quan: 4 thẻ khởi tạo / nhập dự án, 4 chỉ số (quy mô, tổng kinh phí tách đất / '
        'tài sản, tiến độ phê duyệt, bàn giao mặt bằng), danh sách hộ đang làm dở có nút "Lập PA →" mở thẳng hộ, đồng hồ pháp lý '
        '(hạn niêm yết, hộ vướng V1-V5, vận động / cưỡng chế).',
        'Bảng: cuộn mượt từng điểm ảnh; sửa ô xong Enter ghi và xuống ô dưới cùng cột (như Excel), Tab sang ngang; Ctrl+D chép giá '
        'trị ô trên xuống các ô đang chọn. Hộp thoại cao hơn màn hình (laptop 1366 x 768) có thân cuộn, hàng nút luôn hiện. Ctrl+S / '
        'Ctrl+Z hiện thông báo nổi ở góc dưới phải.',
    )),
    ('1.0.06', '20/10/2026', (
        'Thẻ "Thông tin hộ, thửa đất": khối định danh chủ sử dụng đất lưới 3 cột (tự đổi nhãn khi là tổ chức, kiểm tra CCCD đủ 12 số / '
        'trùng hộ khác); bảng thửa 11 cột có DT nguyên thửa, DT còn lại, vị trí đất, Giấy chứng nhận; nguồn gốc & vị trí rút gọn 2 dòng '
        '- bấm đúp hoặc "Xem/Sửa đủ" để mở hộp soạn; dải tổng hợp địa chính và cơ cấu loại đất dưới bảng.',
        'Cửa sổ Lập phương án: dải định danh hộ (chủ hộ, CCCD, địa chỉ, đợt trình, tổng kinh phí); tên thẻ ghi số dòng và số tiền; bảng '
        'chọn từng ô (Ctrl+C sao chép), số liệu phông Consolas; dải "Tổng số hạng mục · CỘNG MỤC" dưới bảng; cảnh báo màu hổ phách khi '
        'diện tích dòng đất vượt DT thu hồi / DT nguyên thửa (không chặn).',
        'Bảng tổng hợp kinh phí: 5 thẻ (cộng bồi thường 100%, kinh phí tổ chức QĐ 08/2025, hai phần phân bổ, tổng mức); cơ cấu có STT I-VI, '
        'dòng con đất ở / đất nông nghiệp, cột căn cứ pháp lý; khung "An toàn nguồn vốn" và cột Đánh giá ở đối soát khái toán.',
        'Tiến độ chi trả & Bàn giao: 6 thẻ chỉ số; khung Sổ nhật ký vận động của hộ đang chọn bên phải bảng, ô đánh giá điều kiện cưỡng '
        'chế thu hồi đất (chỉ nhắc, không chặn); hộp Bàn giao nhắc ngay khi tích mà chưa có ngày biên bản.',
        'Xuất hồ sơ & Bản in: hai thẻ Dự thảo niêm yết / Hồ sơ chính thức, danh sách tài liệu cấu thành (chính thức có lại Báo cáo tiếp '
        'thu, giải trình ý kiến). Bác sĩ CSDL: 5 chỉ số kiểm tra và 4 nút bảo trì một lần bấm, gói chẩn đoán ẩn danh.',
        'Tìm nhanh Ctrl+K: gõ họ tên, mã hộ, CCCD, tờ/thửa hoặc tên chức năng rồi Enter. Phím Ctrl+1 Danh sách hộ, Ctrl+2 Khái toán, '
        'Ctrl+3 Đơn giá bồi thường, Ctrl+4 Niêm yết & Lấy ý kiến, Ctrl+5 Tiến độ & Bàn giao.',
        'Bản in phương án chi tiết: hết "trang 2 mồ côi" - nội dung chỉ tràn vài dòng thì tự vừa 1 trang A4; in 2 trang thì trang 2 bắt '
        'đầu trọn một mục; ẩn dòng CCCD / số điện thoại trống; lề và đệm dòng gọn hơn.',
        'File dự án cũ được bổ sung cột DT nguyên thửa, số Giấy chứng nhận khi mở (không đổi phiên bản CSDL - bản cũ vẫn mở được).',
    )),
    ('1.0.05', '19/10/2026', (
        'MỘT HỘ NHIỀU LẦN LẬP PHƯƠNG ÁN: cửa sổ Lập phương án chi tiết có dải "Lần lập PA:" - Lần 1 (Phương án gốc) và các lần bổ '
        'sung, mỗi lần có dòng tài sản / chính sách, số - ngày phương án và quyết định phê duyệt riêng; dải ghi trạng thái lần '
        '("ĐÃ PHÊ DUYỆT (QĐ số … ngày …) - CHỈ XEM" / "ĐANG LẬP DỰ THẢO") và "Tổng tiền lần này | TỔNG CỘNG DỒN CẢ HỘ (N LẦN)".',
        'Lần đã có quyết định phê duyệt tự KHÓA (chỉ xem): bổ sung tài sản / chính sách mới thì bấm "+ Lập phương án bổ sung" - dữ liệu '
        'và quyết định của các lần trước giữ nguyên. Cần điều chỉnh lần đã duyệt: "Mở khóa sửa…" (ghi lý do vào nhật ký). Lần bổ sung chưa duyệt xóa được ("Xóa lần này").',
        'Tổng của hộ (danh sách hộ, bảng tổng hợp kinh phí, đối chiếu, kiểm tra lỗi) CỘNG DỒN mọi lần - vẫn là MỘT hộ. Thưởng bàn giao mặt bằng chỉ tính một lần cho hộ (lần bổ sung chỉ thêm phần chênh).',
        'Quyết định phê duyệt: thêm hộ vào quyết định hỏi phê duyệt LẦN nào (mặc định lần chưa duyệt sớm nhất; không cộng lại tiền '
        'đã duyệt), lần đó tự khóa; cột '
        'Số PA ghi "PA bổ sung lần k"; bỏ hộ khỏi quyết định thì lần đó mở khóa lại. Hộ còn phương án bổ sung chưa duyệt: trạng thái '
        'ghi "PA bổ sung lần k chưa phê duyệt"; cơ cấu kinh phí tách đúng phần chưa phê duyệt.',
        'Bản in: phương án của lần bổ sung có tiêu đề "PHƯƠNG ÁN CHI TIẾT BỔ SUNG (LẦN k)" và số phương án của lần; hộp Xuất hồ sơ & Bản '
        'in chọn "Lần phương án mới nhất" (trình bổ sung) hoặc "Cộng dồn mọi lần".',
        'File dự án nâng cấp lên CSDL v17 khi mở: dòng phương án cũ là lần 1; hộ đã có quyết định thì lần 1 khóa. Bản phần mềm cũ '
        'không mở được file đã nâng cấp.',
    )),
    ('1.0.04', '19/10/2026', (
        'Bỏ hẳn chức năng che số CCCD: bản Dự thảo và bản Chính thức, tờ trình, bảng niêm yết đều in đủ số CCCD (ô "Che số CCCD" '
        'trong Xuất hồ sơ & Bản in đã bỏ).',
        'Phương án chi tiết: chủ sử dụng là tổ chức thì nhãn "Tổ chức:", "Địa chỉ:", ẩn dòng Số CCCD và Số điện thoại. Mục II nguồn gốc '
        'đất: mỗi đoạn một dòng, căn đều hai bên, giữa theo chiều dọc, thụt đầu dòng; tự bỏ cụm mở đầu bị lặp hai lần.',
        'Mục 1 Bồi thường về đất: thửa có diện tích luôn in "m²" và diện tích kể cả khi không tính tiền đất (đơn giá, tỷ lệ để trống, '
        'thành tiền 0); tài sản trên đất người khác (diện tích 0) để trống ĐVT, số lượng. Tên thửa không giá in gọn, không kèm vị trí '
        'dài; ô Ghi chú các thửa cùng nội dung gộp, căn giữa.',
        'Bảng tổng hợp: bản Dự thảo ghi "(DỰ THẢO)" ngay dưới tên đơn vị, ẩn dòng "(Đính kèm Phương án số …)"; ẩn cột Vị trí đất, cột '
        'tiền rộng hơn; nguồn gốc căn đều, họ tên / địa chỉ / TĐC / ghi chú căn giữa; hộ nhiều thửa: mỗi thửa một dòng, lặp STT, họ tên, '
        'địa chỉ, nguồn gốc riêng từng thửa; số 0 ở dòng hộ hiện "-", ở dòng tổng hiện "0"; dòng 85% ghi gọn tên đơn vị.',
        'Kiểm tra lỗi: hồ sơ chỉ có tài sản / cây trồng trên đất của tổ chức, UBND xã hoặc hộ khác không còn bị báo "diện tích thu hồi '
        'bằng 0"; chủ đất + các hộ có tài sản trên cùng thửa không còn bị cảnh báo trùng thửa.',
        'Thông tin dự án: hộp giãn hết bề ngang (tên dài không bị cắt), thêm khung Tóm tắt quy mô & trạng thái hồ sơ pháp lý. Bảng tổng '
        'hợp kinh phí: hai dòng phân bổ kinh phí tổ chức thực hiện 85% / 15% với số tiền theo phương án, đã phê duyệt, chưa phê duyệt.',
        'Mọi bảng: bấm một ô rồi Ctrl+C để chép (nhiều ô: dán thẳng vào Excel), Ctrl+Shift+C chép cả dòng; chuột phải có "Sao chép ô", '
        '"Sao chép cả dòng". Mở ô sửa bằng chuột thì chữ được bôi đen sẵn.',
        'Thẻ Thông tin hộ: tự đổi nhãn khi chủ sử dụng là tổ chức, dải chân bảng thửa có diện tích theo từng loại đất; hộp sửa nguồn gốc '
        'có mẫu câu chèn nhanh. Dự án mới / Nhập phương án chi tiết: ô lọc nhanh, dòng thiếu tờ / thửa / sai loại đất tô vàng.',
        'Mới: "Tiếp nhận hồ sơ pháp lý" (menu trái nhóm 1, màn hình chào, Ctrl+Shift+L) - dùng được khi chưa có dự án: loại chủ đầu tư, '
        'căn cứ thu hồi, thời hạn chủ trương / Nghị quyết HĐND, 32 mục hồ sơ, 10 tiêu chí kỹ thuật địa chính, quét bảng kê thửa Excel, '
        'tổng hợp có / thiếu / cần bổ sung; xuất Phiếu tiếp nhận (.xlsx), Công văn đề nghị bổ sung (.docx); khởi tạo dự án mới từ hồ sơ.',
    )),
    ('1.0.03', '18/10/2026', (
        'Bảng dữ liệu dễ đọc hơn: ô bằng 0 hoặc "-" chữ xám nhạt (mắt lướt qua khoản trống), số tiền ở cột Tổng / Thành tiền chữ xanh '
        'đậm; bấm một ô là tô sáng cả dòng.',
        'Cột Trạng thái danh sách hộ: thanh 4 vạch tiến độ + nhãn màu bo tròn (xanh lá: đã bàn giao; xanh ngọc: đã chi trả / phê duyệt; '
        'xanh dương: đã lập; vàng: tự lập, cần xem lại; xám: chưa lập). Cột Ý kiến, Nhóm vướng của Niêm yết cũng dùng nhãn màu.',
        'Cột tỷ lệ % (Cơ cấu kinh phí, Tổng hợp kết quả ý kiến) có thanh tỷ trọng mảnh dưới số. Bảng chưa có dòng nào hiện lời hướng dẫn '
        'nhẹ ở giữa (phương án hộ, khái toán, niêm yết, quyết định, tổng hợp tiền, tiến độ).',
        'Menu trái luôn sáng đúng mục đang xem, kể cả khi mở Lập phương án chi tiết, Niêm yết & Lấy ý kiến, Đơn giá bồi thường hay So '
        'sánh với thực tế. Khung nhóm (Thông tin dự án…) phẳng, không còn "tai hộp" trên tiêu đề; góc trên trái bảng cùng màu xanh đậm.',
        'Danh sách hộ: STT, Số thửa căn giữa, Diện tích căn phải; 7 cột vừa khung nhìn, không còn thanh cuộn ngang thừa. Thông tin dự án: '
        'hộp rộng hơn, tên đơn vị / cơ quan thẩm định dài hiện từ đầu, đủ chữ khi rê chuột.',
        'Lập phương án: ô chọn tài sản / cây trồng và nút ▼ liền một khối; cột Nguồn giá, Quy cách, Căn cứ giá gọn - nhường chỗ cho tên '
        'và cột tiền; dải tổng dưới đáy ghi tên từng mục (1. Đất, 2. Nhà, 3. Cây, 4. Vật nuôi, 5. Hỗ trợ, 6. Thưởng; mục 0 đồng chữ xám, '
        'cửa sổ hẹp tự viết gọn "1,2 tỷ"). Thẻ Thông tin hộ: khung thông tin chủ hộ dạng thẻ trắng, dưới bảng thửa có dòng cộng số thửa, '
        'số tờ, diện tích thu hồi.',
        'Niêm yết & Lấy ý kiến: 6 thẻ số liệu 2 tầng (tên trên, số lớn + tỷ lệ dưới), vạch màu bên trái thẳng; tỷ lệ % dùng dấu phẩy '
        '(25,0%), các cột số của thẻ Tổng hợp kết quả ý kiến căn giữa.',
        'Bảng tổng hợp kinh phí: 4 thẻ đầu trang (Quy mô & đã lập PA, Cộng bồi thường hỗ trợ 100%, Kinh phí tổ chức QĐ 08, TỔNG KINH PHÍ '
        'DỰ ÁN); cột Tỷ lệ không còn bị cắt chữ; thẻ Bảng kinh phí chi tiết vừa khung (không cuộn ngang để thấy TỔNG PHƯƠNG ÁN) và có '
        'dòng cộng chân bảng.',
        'Quyết định phê duyệt: 4 thẻ đầu trang (số quyết định, lượt hộ đã phê duyệt, tổng kinh phí đã duyệt, chênh lệch so với phương '
        'án) và dòng cộng chân bảng của quyết định đang chọn.',
        'Tiến độ chi trả & Bàn giao: dòng cộng giải ngân của các hộ đang lọc (tổng duyệt, đã nhận, chưa nhận) bên trái, 4 nút vừa chữ bên '
        'phải; cột Mốc thu hồi đất / Vận động gọn để thấy cột tiền. Bộ lọc và thẻ "mặt bằng sạch" tính bàn giao theo cùng quy tắc với danh '
        'sách hộ (có quyết định, đã nhận đủ tiền, có ngày biên bản).',
        'Khái toán: thanh nhập (ô và 4 nút) một hàng từ màn hình 1.020 px; thẻ tổng ghi cả cơ cấu 6 mục. Đợt trình: danh sách kiểm tra '
        'hồ sơ có huy hiệu màu Đạt / Xem lại / Thiếu. Đơn giá bồi thường: huy hiệu "Đang lọc: a / b mục" cạnh ô tìm, đổi thẻ vẫn giữ lọc.',
    )),
    ('1.0.02', '17/10/2026', (
        'Các cửa sổ và trang làm việc cùng tông Navy với màn hình chính: nút chính (Lưu, Thực hiện, Xuất bản hồ sơ đợt này, Thêm vào '
        'bảng) nền xanh đậm chữ trắng; nút Xóa viền đỏ nhạt chữ đỏ; các nút khác nền trắng viền xám - không còn nút màu cam, tím, xanh lá.',
        'Thẻ (tab), khung nhóm, thanh chia, thanh thông báo dùng chung một kiểu: thẻ đang chọn nền trắng chữ xanh đậm có vạch xanh.',
        'Cửa sổ lập phương án: thanh trên cùng gọn (Hộ, ◀ ▶, Dán tài sản, Lưu, Bỏ thay đổi, Xem trước, In / Xuất, Đóng); thẻ mục kiểu '
        'gạch chân; dải tổng cộng dưới đáy chữ xanh đậm; hàng nhập nhanh các ô cùng chiều cao. Khung xem trước A4: thanh công cụ sáng, '
        'nền trang xám xanh dịu mắt.',
        'Tiến độ chi trả & Bàn giao: 4 thẻ chỉ số có vạch màu, thẻ đang lọc được tô nổi; nút chế độ "Theo hộ / Thửa còn vướng" dạng '
        'viên thuốc; dòng Mốc pháp lý dạng thẻ. Niêm yết & Lấy ý kiến: 6 thẻ số liệu có vạch màu.',
        'Bảng tổng hợp kinh phí: dòng Cộng bồi thường, Kinh phí tổ chức thực hiện và TỔNG KINH PHÍ DỰ ÁN tô nổi. Bảng giá đất NQ 28 và '
        'Hệ số K: cột Hệ số K và Giá × K in đậm, dễ dò.',
        'Khái toán: thanh nhập nền trắng, thẻ tổng cộng xanh nhạt chữ xanh đậm. Xuất hồ sơ & Bản in: khung tùy chọn dạng thẻ trắng.',
        'Bàn giao mặt bằng: hộ chưa có quyết định phê duyệt thì hộp "Bàn giao mặt bằng các hộ đã chọn…" không tích sẵn "Đã bàn giao" '
        'và nhắc rõ số hộ chưa phê duyệt (tránh đánh dấu nhầm cả dự án). Kiểm tra lỗi báo hộ đã đánh dấu bàn giao mà chưa có quyết '
        'định phê duyệt, kèm cách bỏ đánh dấu.',
        'Tiến độ tự động: thanh 4 nấc ở cột Trạng thái và các thẻ Đã phê duyệt / Đã chi trả / Đã bàn giao tự tính lại mỗi lần mở theo '
        'đúng thứ tự - có quyết định phê duyệt mới lên nấc phê duyệt, mọi quyết định đã nhận tiền mới lên nấc chi trả, đã tích bàn giao '
        'và có ngày biên bản mới lên nấc bàn giao. Đánh dấu thiếu bước / thiếu ngày không làm tăng nấc, ô Trạng thái ghi rõ điểm cần xem lại.',
        'Hộp Bàn giao mặt bằng: không còn điền sẵn ngày hôm nay - nhập ngày ký biên bản bàn giao (biên bản không cần số); file scan '
        'biên bản không bắt buộc, chọn một lần dùng chung cho nhiều hộ (chỉ ghi đường dẫn, không chép file).',
        'Cửa sổ lập phương án: mỗi dòng ở các thẻ Đất, Nhà, Cây trồng, Vật nuôi, Hỗ trợ có biểu tượng thùng rác ở cột cuối - bấm là xóa '
        'đúng dòng đó (thay nút "Xóa dòng"); phím Delete và menu chuột phải vẫn xóa dòng đang chọn.',
        'Bản cho Windows 7: chữ trên các thẻ không còn bị cắt mất ký tự đầu / cuối.',
        '"Bản đồ thửa đất" chuyển từ menu bên trái sang menu Dữ liệu (cạnh "Nhập bản vẽ CAD"), menu trái gọn hơn.',
    )),
    ('1.0.01', '17/10/2026', (
        'Giao diện mới tông Navy: menu trái gọn (nút "Thu gọn menu" ở hàng riêng, không đè tiêu đề nhóm; mục đang chọn có vạch xanh '
        'bên trái); tiêu đề bảng nền xanh đậm chữ trắng, dòng xen kẽ dễ đọc.',
        '6 thẻ số liệu cao gọn, có tỷ lệ % so với tổng số hộ (đã lập PA, đã phê duyệt, đã chi trả, đã bàn giao); thẻ đang lọc được tô '
        'nổi. Hàng lọc một dòng: "Đợt: Tất cả", "Trạng thái: Tất cả", ô tìm theo họ tên, CCCD, tờ/thửa (ví dụ 12/45); huy hiệu "Đang '
        'lọc: k / N hộ".',
        'Danh sách hộ: cột Trạng thái có thanh tiến độ 4 nấc (□□□□ chưa lập PA → ■■■■ đã bàn giao); dòng CỘNG dưới bảng tự cộng diện '
        'tích, bồi thường đất, tài sản & cây, hỗ trợ & thưởng, tổng cộng của các hộ đang hiện.',
        'Màn hình chào tông Navy - Slate; bảng dự án gần đây đủ chữ tiêu đề; phần đầu cửa sổ thấp hơn, nhường chỗ cho bảng.',
        'Quy ước giá tương đương để trống: phần mềm bỏ các dòng mẫu cũ khi mở dự án (dòng bạn tự nhập giữ nguyên), nhập file Excel '
        'không còn chép quy ước mẫu, nạp danh mục từ Excel không làm mất quy ước riêng của dự án.',
    )),
    ('1.0.00', '16/10/2026', (
        'Mục "Tiến độ chi trả & Bàn giao" thay hai mục "Theo dõi chi trả & Bàn giao" và "Báo cáo tiến độ GPMB" (trùng phần lớn số '
        'liệu và nút lệnh): 4 thẻ chỉ số ở trên cùng (giải ngân, mặt bằng sạch, thửa chưa bàn giao, hộ đủ điều kiện cưỡng chế) - bấm '
        'thẻ để lọc ngay; hai chế độ xem "Theo hộ" (nhập liệu) và "Thửa còn vướng" (xếp Gấp / Cao / Theo dõi).',
        'Một nút "Xuất" gom các báo cáo: bảng theo dõi chi trả & bàn giao, báo cáo tiến độ GPMB, danh sách đề nghị cưỡng chế.',
        'Mốc pháp lý gọn một dòng; ngày thông báo thu hồi đất nhập ở nút "Mốc pháp lý…". Dự án chưa có quyết định: thẻ hiện "—" kèm '
        'lời nhắc, bảng thửa trống nói rõ vì sao; ô danh sách quyết định ẩn khi chưa có quyết định.',
        'Phím tắt chuyển trang Ctrl+1..5 (Lập khái toán & Dự toán là Ctrl+5).',
    )),
    ('0.9.99', '16/10/2026', (
        'Đọc PDF ảnh / ảnh scan (bảng đơn giá, quyết định, hệ số K, giấy tờ) bằng Tesseract OCR ĐÓNG KÈM phần mềm, thay nhận dạng '
        'chữ của Windows: không còn phải cài gói tiếng Việt của Windows; bảng scan giữ đúng cột (STT, tên, ĐVT, đơn giá), "m²" đọc '
        'đúng; khoảng 1-2 giây mỗi trang, không gửi file ra ngoài.',
        'Bản in tự dàn trang: lề trang chuẩn, vừa bề ngang khổ giấy, ngắt trang tự động ở chỗ hợp lý (phương án chi tiết: tiêu đề '
        'bảng, mục và dòng con không tách rời; bảng tổng hợp: ngắt giữa các hộ, hộ nhiều thửa tách ở ranh dòng thửa và lặp họ tên). '
        'Trang cuối chỉ tràn ít thì nén khít lại; trang hở nhiều thì giãn cân đối. Tổng cộng và chữ ký luôn cùng trang.',
        'Sửa: phương án chi tiết có nguồn gốc đất dài in đậm nhầm dòng (đề mục 1-6 không đậm, dòng tài sản lại đậm) - nay luôn đậm '
        'đúng các đề mục và dòng TỔNG CỘNG.',
        'Bảng tổng hợp bản DỰ THẢO: chữ "(DỰ THẢO)" thành dòng riêng dưới tiêu đề, dễ thấy trên khổ A3; cột số / chữ cân đối bề rộng.',
        'Cửa sổ lập phương án hộ: bỏ nút SCAN; ô chọn hộ và các nút chung một hàng, co giãn theo bề rộng màn hình.',
        'Máy cấu hình yếu: mở phần mềm, mở dự án nhanh hơn (các trang Bảng tổng hợp, Theo dõi tiến độ, Quyết định, Báo cáo chỉ tạo '
        'khi mở lần đầu; khung xem trước A4 tạo khi bật; màn hình chào không mở lại file dự án chưa đổi); bản đã cài gói cập nhật '
        'khởi động nhanh hơn sau lần đầu. Bộ cài nhỏ hơn: đọc bản vẽ CAD (.dxf) không cần thư viện ngoài.',
    )),
    ('0.9.98', '16/10/2026', (
        'Xem trước bản in: nút "In…" (Ctrl+P) mở hộp in của Windows - chọn máy in, số bản, trang cần in (như Word / Excel). "In nhanh" '
        'vẫn gửi máy in mặc định qua Excel.',
        'Bảng tổng hợp: ngắt trang ở ranh giới giữa các hộ (không còn hộ vắt hai trang mất đường kẻ, chữ ô gộp xô lệch); cột số đủ rộng, '
        'hết "#####"; cột Vị trí rộng hơn; dòng kinh phí bỏ "(theo Quyết định số 08…)"; tổng cộng và chữ ký cùng trang.',
        'Phương án chi tiết: dòng "III. Bảng tính toán…" và tiêu đề cột không nằm trơ cuối trang (sang trang sau cùng dòng số liệu); '
        'nguồn gốc đất thụt đầu dòng mỗi đoạn (căn đều giữ nguyên); dòng "Thưởng bàn giao mặt bằng" ngắt dòng như các mục 2-5.',
        '"Hồ sơ scan" đổi tên thành "HS đính kèm". Đổi cỡ giao diện (A− / A+) hiện con trỏ chờ, phản hồi nhanh hơn.',
        'Xuất hồ sơ & Bản in gọn hơn: bỏ ô chọn mẫu "Mẫu chính / Dự thảo" ở từng bản in (chữ DỰ THẢO theo Chế độ phát hành ở đầu '
        'cửa sổ), bỏ dòng ghi chú dưới Chế độ phát hành (xem ở chú thích khi rê chuột) và ô "Báo cáo tiếp thu ý kiến".',
    )),
    ('0.9.97', '16/10/2026', (
        'Sửa: mở Niêm yết rồi bấm lại "Lập phương án chi tiết" không hiện cửa sổ nhập - nay mở đúng cửa sổ lập phương án.',
        'Bảng các mục phương án: menu chuột phải (thêm, nhân bản, xóa, lên / xuống, chép ô; mục 1: thêm nhiều thửa, tra giá NQ 28; mục 2 '
        'kiểm tra DT xây dựng, tách ranh; mục 3 tính mật độ).',
        'Bản in: dòng ngày "Trị An, ngày ...... tháng ..... năm"; tổ chức không in dòng CCCD; tiêu đề "DỰ ÁN <tên dự án>"; họ tên người '
        'ký căn giữa dưới chức danh. Xuất hồ sơ & Bản in: nút "Xem trước bảng tổng hợp".',
        'Gói cập nhật đổi đuôi thành .larcud (gói .pabtcn cũ vẫn cài được). Bảng tổng hợp kinh phí có lề, cột Nhóm khoản không xuống dòng.',
        'Nhanh hơn: lưu một hộ rồi tải lại danh sách (5.000 hộ: ~0,13 s -> ~0,07 s), tạo Dự án mới có hệ số K, chuyển thẻ cửa sổ lập '
        'phương án, in phương án chi tiết.',
    )),
    ('0.9.96', '16/10/2026', (
        'Bảng giá đất có hai thẻ "Bảng giá đất 2026" và "Hệ số K" (QĐ 03/2026/QĐ-UBND, gắn sẵn 4 xã / phường của bảng giá); mục Đất '
        'và hỗ trợ tính theo giá đất tự nhân hệ số K; nhập / sửa hệ số K từ file (cả PDF ảnh) hoặc chữ dán.',
        'Bảng phương án hộ: dòng cao theo chữ (30-88 px) - ô Ghi chú trống không làm dòng cao; cột Ghi chú, Quy cách gọn.',
        'Mục 1. Đất: "Thêm tất cả thửa", "Chọn nhiều thửa…" (lọc tờ / loại đất, Ctrl+A); chọn nhiều dòng để xóa cả loạt hoặc đặt cùng '
        'vị trí / giá / tỷ lệ. Thẻ thửa đất của hộ: chọn nhiều thửa rồi Xóa thửa.',
        'Loại đất đủ danh mục (RDD, RPH, DGT, LUN…): hết báo "không có trong danh mục"; gõ chữ thường / tên đầy đủ tự đổi về mã.',
        'Nhập phương án chi tiết từ Excel: mỗi thửa luôn có dòng mục 1 (cả đơn giá 0); một sheet nhiều phương án tự tách. Nhập Excel '
        'thô: ưu tiên cột diện tích trong dự án, đọc đúng dòng tiếp của cùng hộ.',
        'Hồ sơ scan (PDF / ảnh) đính kèm từng hộ, mở nhanh; Theo dõi tiến độ thêm cột Hoàn tất CTBT (theo đợt), Hồ sơ scan và danh sách hộ '
        'hoàn tất xuất Excel.',
        'Bản in: họ tên Lập biểu / Kiểm tra / người ký căn giữa dưới chức danh. Nút "Quét hồ sơ" của cửa sổ lập phương án đang hoàn thiện.',
    )),
    ('0.9.95', '16/10/2026', (
        'Giao diện gọn, nhiều chỗ cho bảng: hàng thẻ số chỉ ở Danh sách hộ (một dòng); banner xanh chỉ ở màn hình chào; menu trái '
        'gọn (nút 27 px); không còn tiêu đề trang lặp mục menu.',
        'Cửa sổ lập phương án hộ: ô chọn hộ và các nút lệnh chung một hàng (◀ / ▶ chuyển hộ); mục 1 nút Xóa / Lên / Xuống và Cộng '
        'mục cùng hàng chọn thửa; ◀ Trở lại / Tiếp theo ▶ chung hàng với dải tổng cộng; cột ngắn gọn, cột tên / ghi chú giãn.',
        'Khái toán: tổng cộng và nút Mở tệp / Tạo mới / Xuất / Lưu chung một hàng; nút Ẩn / Hiện thông tin chung; So sánh với thực '
        'tế: khái toán bằng 0 không tô cảnh báo vượt. Niêm yết: 6 thẻ số một dòng, nút Xuất của từng thẻ ở góc phải thanh thẻ.',
        'Màn hình chào: tổng kinh phí dự án gần đây khớp danh sách hộ (có thưởng, làm tròn), tên hiển thị "Tên dự án · Địa bàn (file)".',
        'Quét giấy tờ: bên trái xem trước TOÀN BỘ các trang ảnh / PDF (phóng to, Ctrl + lăn chuột, kéo, xoay 90°, chuyển trang; "Chữ OCR" '
        'để xem chữ); đọc bảng phương án chi tiết của hộ đã scan (thông tin hộ, nhân khẩu, nguồn gốc đất, tái định cư, thửa mục 1, tài '
        'sản / cây / hỗ trợ mục 2-5); nút "Nhập trọn bộ vào phương án hộ"; lưu đính kèm file vào hồ sơ hộ.',
        'Sửa: nhận dạng chữ trang scan nhiều chữ (bảng giá, bảng phương án) báo "quá lâu" sau 3 phút - nay khoảng 1 giây / trang.',
    )),
    ('0.9.94', '15/10/2026', (
        'Tên hiển thị LARC ở mọi nơi: tiêu đề cửa sổ "LARC - <tên dự án>…", hộp thông báo, thanh tác vụ; gói cập nhật đổi tên '
        'LARC_CapNhat_<phiên bản>.pabtcn, gói chạy ngay LARC_ChayNgay_… (như bộ cài LARC_Setup). Gói PABT_CapNhat của bản trước '
        'vẫn cài được.',
        'Cột Số lượng theo định dạng kế toán: nhà, công trình 2 chữ số thập phân (46,00); đất, cây trồng, vật nuôi, chính sách hỗ trợ '
        'và số lượng khác 1 chữ số (16,0); số lẻ hơn hiện đủ (0,0325 ha). Áp dụng trên màn hình, bảng khái toán, bản in chi tiết và '
        'báo cáo đối chiếu (trước đây bảng khái toán in "46," thiếu số lẻ).',
        'Trang Khái toán & dự toán: bỏ tiêu đề và nút Chế độ trùng menu trái, dành chỗ cho phần nhập liệu.',
        'Bỏ thanh tab phía trên nội dung: bảng thấy thêm dòng. Chuyển trang bằng menu trái / thanh menu hoặc Ctrl+1 … Ctrl+6; cửa sổ '
        'hộ đóng bằng nút Đóng.',
        'Tên dự án chỉ hiện một chỗ - giữa thanh menu trên cùng: "PABT - <tên dự án> · <địa bàn> (<tên file>)"; bỏ ô "Dự án" trên '
        'banner xanh và dòng tên dự án dưới banner.',
        'Dự án làm việc gần đây: file không còn trên đĩa tự rời danh sách, không đẩy dự án thật ra ngoài (trước đây danh sách có thể '
        'trống dù vừa mở dự án).',
        'Niêm yết & Lấy ý kiến: nút "Xuất bảng niêm yết" nằm trên hàng nút đợt; cột "CCCD" (số vẫn che theo Nghị định 13/2023); 4 thẻ '
        'gọn; cột đủ rộng, chữ tiêu đề không bị cắt ("Tổng tiền dự thảo", "Nhóm vướng"). Thẻ số liệu và nút bấm gọn hơn, bảng có '
        'thêm chỗ.',
        'Tên hộ trong ô chọn hộ (cửa sổ lập phương án, nhật ký kiểm toán, quyết định, trạng thái, phạm vi in) không còn kèm "(mã n)".',
    )),
    ('0.9.93', '15/10/2026', (
        'Dán danh sách tài sản (Lập phương án hộ, Khái toán, Phiếu kiểm đếm) hiểu câu viết tự nhiên: "Xoài: 16 cây, 17 năm tuổi" chọn '
        'đúng mục theo năm tuổi; "Tràm: 1453 cây, đường kính 28cm" (hoặc "Tràm cây 1500 d28") chọn quy cách theo đường kính; "Nhà tạm: '
        '46m2"; "Gác để ở tính bằng Nhà 01 tầng kết cấu loại 4: 35,8m2" áp giá theo mục sau chữ "tính bằng"; "Ao nuôi cá ghép: 1,5ha, 1 '
        'năm 1 vụ" vào Vật nuôi.',
        'Cập nhật đơn giá: nhóm Vật nuôi riêng (tự nhận theo tên và đơn vị tính); mục mới mang đúng phân loại của bộ đơn giá; bảng xem '
        'trước hiện mã sẽ cấp (TS / CT / VN / CS) và sửa được Tên, ĐVT, Đơn giá; dán bảng / văn bản đơn giá bằng Ctrl+Shift+V trong hộp '
        'Đơn giá bồi thường; áp dụng xong tự chuyển về thẻ vừa cập nhật.',
        'PDF ảnh scan: đọc bằng nhận dạng chữ của Windows 10 / 11 (cần gói tiếng Việt của Windows - có nút cài) hoặc Tesseract; máy chưa '
        'đọc được thì chọn cài gói, dán chữ từ Clipboard hoặc chọn file Excel / Word khác.',
        'Bản in phương án chi tiết: đoạn nguồn gốc đất sát mục III; dòng "Hỗ trợ đào tạo, chuyển đổi nghề…" không lặp diện tích, thành '
        'tiền của dòng thửa; dòng IV chỉ chữ "Tái định cư:" in đậm, nội dung chữ thường.',
    )),
    ('0.9.92', '15/10/2026', (
        'Tên hiển thị mới: biểu tượng Desktop "LARC", tên đầy đủ "LARC - Bồi thường, hỗ trợ, tái định cư" (Start Menu, Cài đặt > Ứng '
        'dụng); bộ cài LARC_Setup_Universal. Cài bản này thì lối tắt tên PABT cũ được thay bằng lối tắt LARC.',
        'Biểu tượng Desktop / thanh tác vụ không còn hiện ảnh cũ sau khi cập nhật: mỗi phiên bản dùng file biểu tượng riêng, lối tắt đã '
        'ghim lên thanh tác vụ cũng được đổi biểu tượng.',
        'File dự án mới có đuôi .larc. File .pabt của các bản trước vẫn mở, lưu bình thường (giữ nguyên đuôi); bấm đúp file .larc / '
        '.pabt đều mở bằng phần mềm.',
    )),
    ('0.9.91', '15/10/2026', (
        'Biểu tượng phần mềm mới "3D LARC": ô vuông xanh dương viền vàng, ngôi nhà và chìa khóa vàng trên nền bản đồ địa chính. '
        'Biểu tượng sắc nét hơn trên thanh tác vụ nền tối (bỏ viền bóng xám của ảnh gốc). PABT.exe, lối tắt Desktop và bộ cài đổi khi '
        'cài bộ cài 0.9.91; gói cập nhật chỉ đổi biểu tượng trong phần mềm.',
    )),
    ('0.9.90', '15/10/2026', (
        'Biểu tượng phần mềm mới: ô vuông xanh dương viền vàng, lưới bản đồ địa chính, nhịp cầu, sách "Luật Đất đai 2024", chữ PABT. '
        'Biểu tượng của file PABT.exe, lối tắt Desktop và bộ cài đổi khi cài bộ cài 0.9.90; gói cập nhật chỉ đổi biểu tượng trong '
        'phần mềm (thanh tiêu đề, thanh tác vụ).',
    )),
    ('0.9.89', '15/10/2026', (
        'Dán danh sách tài sản từ bảng Excel có cột Đơn giá / Thành tiền: các cột đó không còn bị đọc nhầm thành tỷ lệ (trước đây mọi '
        'dòng báo lỗi tỷ lệ quá 500%).',
        'Nhập Excel: số CCCD ở ô kiểu số bị Excel bỏ số 0 đầu (075092001234 thành 75092001234) được thêm lại số 0 - khớp quyết định, '
        'gom hộ, che CCCD đúng. Hồ sơ đã nhập trước đây không tự sửa.',
        'Ngày gõ thiếu số năm ("12/10/202") báo lỗi thay vì nhận thành năm 0202; ô số không nhận "nan", "inf".',
        'Xuất hồ sơ theo đợt: không còn đổi tên nhầm thư mục của đợt khác tên gần giống ("Đợt 1" / "Đợt 1 - bổ sung"); đợt có dấu ":" '
        'trong tên tìm lại được thư mục cũ.',
        'Bản in chi tiết: các thửa cùng ghi chú gộp một ô không còn làm từng dòng cao quá mức; nguồn gốc đất có khoảng năm '
        '("1975 - 1990, 1990 - 2005") không bị tách thành gạch đầu dòng.',
        'Thẻ tổng tiền hiện "1,0 tỷ" thay "1.000,0 triệu"; sổ vận động ghi "hôm nay hết hạn" vào ngày cuối thời hạn.',
    )),
    ('0.9.88', '15/10/2026', (
        'Bản in phương án chi tiết: ô nguồn gốc đất căn đều hai bên như văn bản Word (không còn bên phải lởm chởm); dòng thưởng bàn '
        'giao mặt bằng chỉ ghi tên và thành tiền; dòng TỔNG CỘNG gộp ô từ cột STT, căn giữa, in đậm.',
        'Nguồn gốc đất: dấu " - " nối giữa tên riêng ("Khu Bảo tồn thiên nhiên - Văn hoá Đồng Nai") hoặc trong ngoặc không còn bị '
        'tách thành dòng mới; chỉ tách sau dấu kết câu / hai chấm hoặc danh sách ngắn ("đất ở - đất lúa"). Nội dung đã lưu bị tách '
        'sai ở bản trước không tự nối lại - sửa tay trong ô Nguồn gốc nếu cần.',
        'Menu trái: nhóm "Đơn giá & bảng giá" chuyển xuống cuối (nhóm 6), các nhóm làm hằng ngày lên trên; chưa mở dự án thì Đơn giá '
        'đặc biệt mờ, Đơn giá bồi thường và Bảng giá đất vẫn tra cứu được.',
        'Thanh menu trên cùng: chữ menu ngang hàng chữ tiêu đề (màn hình 125% trước đây lệch vài điểm ảnh); mở phần mềm nhanh hơn chút '
        'khi đọc danh sách dự án gần đây.',
    )),
    ('0.9.87','14/10/2026', (
        'Cấu hình nghiệp vụ (menu Cài đặt): số ngày niêm yết, đối thoại, thẩm định, thông báo thu hồi đất, vận động trước cưỡng chế, '
        'mức kinh phí tổ chức thực hiện, ngưỡng kiểm tra, bản in, thông tin cơ quan - sửa trên màn hình, áp dụng ngay; "Quy trình 16 '
        'bước" hiện thời hạn từng bước theo cấu hình.',
        'Bản vẽ địa chính CAD (.dxf): nhập số tờ, số thửa, diện tích (đo theo hình và phần nằm trong ranh thu hồi), cập nhật diện '
        'tích thu hồi của hồ sơ; "Bản đồ thửa đất" (nhóm Lập phương án) tô màu thửa theo ý kiến niêm yết (xanh đồng thuận, đỏ chưa '
        'đồng thuận), bấm thửa mở hồ sơ hộ.',
        'Quét giấy tờ (OCR) ở cửa sổ lập phương án và Khái toán: đọc giấy chứng nhận QSDĐ / biên bản kiểm kê (ảnh chụp, PDF scan) -> '
        'họ tên, CCCD, địa chỉ, thửa (tờ, số, diện tích, loại đất), dòng tài sản.',
        'Phiếu kiểm đếm thực địa (menu Công cụ): xuất một file .html mở trên điện thoại không cần mạng, ghi tài sản ngoài thực địa, '
        'tải file kết quả về và nhập thẳng vào phương án từng hộ; gắn ảnh hiện trạng theo CCCD / họ tên / số thứ tự trong tên ảnh.',
        'Chẩn đoán & sửa lỗi hệ thống (menu Trợ giúp): kiểm tra máy (thư mục dữ liệu, ổ đĩa, Excel, Tesseract, HTTPS), kiểm tra và sửa '
        'file dự án (sao lưu trước; cứu dữ liệu khi file hỏng), xuất gói chẩn đoán .zip gửi tác giả - dự án trong gói ĐÃ ẨN DANH (không '
        'họ tên, CCCD, điện thoại, địa chỉ, nguồn gốc, ý kiến dân). Hộp báo lỗi không mong muốn cũng có nút xuất gói này.',
        'Bản in: chủ sử dụng là tổ chức (Công ty, UBND, Ban quản lý, Hợp tác xã…) ghi "Tổ chức:" thay "Họ và tên:"; ghi chú các thửa '
        'đất liền nhau giống nhau gộp một ô; tiêu đề mục II "Thông tin vị trí, nguồn gốc đất".',
        'Xem trước A4 trên máy không có Microsoft Excel (hoặc Excel lỗi): hiện bản gần đúng do phần mềm tự dựng, có nhãn "Bản gần '
        'đúng"; in / xuất PDF chính thức vẫn qua Excel.',
        'Báo cáo tiến độ: "thửa chưa bàn giao mặt bằng (còn vướng mắc)" thay cách gọi cũ.',
        'Nhanh hơn: đọc lại file quyết định PDF (10,6 -> 0,8 giây với bảng 300 hộ), đọc file Word lớn tốn ít bộ nhớ hơn (152 -> 26 MB), '
        'gõ tìm trong danh mục cây trồng dài, nhập phương án chi tiết nhiều hộ có thanh tiến độ và nút Dừng.',
        'File dự án nâng lên CSDL v16: sau khi mở bằng bản này, máy còn dùng bản cũ (0.9.86 trở về trước) không mở được file - cập '
        'nhật mọi máy dùng chung dự án.',
    )),
    ('0.9.86', '14/10/2026', (
        'Nhật ký kiểm toán (menu Dữ liệu, chuột phải danh sách hộ): phần mềm tự ghi AI sửa, LÚC NÀO, trên MÁY nào, hộ / thửa / dòng '
        'phương án nào, giá trị CŨ -> MỚI (diện tích, đơn giá, số lượng, tỷ lệ, thông tin hộ, thửa, đơn giá danh mục). Không sửa, '
        'không xóa được; lọc theo hộ, thời gian, từ khóa và xuất Excel nộp đoàn thanh tra, kiểm toán.',
        'Kiểm tra lỗi có nhóm "Bác sĩ hồ sơ": diện tích bồi thường LỚN HƠN diện tích thu hồi của thửa, tỷ lệ chất lượng nhà / công '
        'trình / cây / vật nuôi vượt 100%, hỗ trợ theo nhân khẩu mà hộ chưa nhập hoặc khác số nhân khẩu, nhân khẩu bất thường, vượt '
        'hạn mức đất ở (khi đã cấu hình trong hồ sơ địa phương). Trùng số CCCD vẫn báo ở nhóm Thông tin hộ.',
        'Nhập file Excel nhanh hơn (20.000 dòng: 3,1 -> 2,8 giây).',
    )),
    ('0.9.85', '14/10/2026', (
        'Hồ sơ địa phương (pabt_profile.json): thông tin cơ quan, căn cứ pháp lý của tờ trình, số ngày thẩm định / thu hồi / vận động / '
        'niêm yết / đối thoại, mức kinh phí tổ chức thực hiện (theo tuyến, dự án khác), làm tròn và tỷ lệ phân bổ 85% / 15%, vị trí cột '
        'của mẫu in - đưa ra một file, dùng phần mềm ở địa phương khác chỉ cần thay file này, không sửa phần mềm.',
        'Gói mẫu in & cấu hình (.pabtcfg) - menu Công cụ: "Xuất gói…" đóng mẫu in, mẫu tờ trình và hồ sơ địa phương thành một file gửi '
        'qua Zalo / email; máy nhận bấm đúp file là cập nhật ngay (mẫu cũ được sao lưu), không cài lại phần mềm.',
        'Bản in: nguồn gốc đất căn đều hai bên, canh TRÊN; bản DỰ THẢO tự che số CCCD (Nghị định 13/2023/NĐ-CP); bảng tổng hợp cộng '
        'các cột diện tích và kinh phí (không cộng cột vị trí đất), dòng phân bổ kinh phí ghi tỷ lệ khớp công thức.',
    )),
    ('0.9.84', '14/10/2026', (
        'Xem trước bản in A4 ngay trong cửa sổ: hộp "Xuất hồ sơ & Bản in" chia đôi - bên trái các tùy chọn, bên phải trang A4; bấm hộ '
        'nào hiện bản in của hộ đó, đổi Dự thảo / Chính thức hoặc ô "Che số CCCD" là bản xem trước đổi theo. Thanh công cụ: phóng to, '
        'thu nhỏ, vừa trang, lật trang, In nhanh.',
        'Cửa sổ lập phương án hộ: nút "Xem trước A4 (F4)" (hoặc phím F4) mở / đóng bản in ở nửa phải, lấy cả số liệu đang soạn chưa '
        'lưu; sửa xong khoảng 1,5 giây là bản xem trước tự lập lại. Hàng nút trên cùng tự xuống dòng khi cửa sổ hẹp (màn hình 1366).',
        'Bản xem trước do Microsoft Excel tạo (đúng như bản in, mỗi lần khoảng 1,5 - 2 giây, chạy nền - vẫn thao tác được); file tạm '
        'tự xóa khi đóng cửa sổ.',
    )),
    ('0.9.83', '14/10/2026', (
        'Bản in: mọi ô của bảng tính bồi thường (phương án chi tiết) và bảng tổng hợp căn giữa theo chiều dọc, tự xuống dòng; '
        'chiều cao dòng tính theo số dòng chữ thật cộng 4 pt trên / 4 pt dưới (tối thiểu 24 pt, hàng tiêu đề cột 28 pt) - chân chữ '
        'và dấu tiếng Việt không còn chạm đường kẻ ô.',
        'Nguồn gốc đất dài: quá 350 pt thì tự tách sang dòng mới ở chỗ hết câu / hết đoạn, dòng mới gộp cùng dải cột, căn đều và '
        'giữa ô. Bảng tổng hợp: hộ có nguồn gốc rất dài được thêm dòng, không còn bị cắt chữ ở trần 409 pt của Excel.',
        'Đường kẻ dưới tên đơn vị, tiêu ngữ, dòng "Dự án" cách chân chữ 5 pt.',
    )),
    ('0.9.82', '14/10/2026', (
        'Mẫu in: MỘT bộ mẫu cho cả hai chế độ. Bản DỰ THẢO giữ dòng "(DỰ THẢO)" có sẵn trong mẫu (mẫu chưa có thì phần mềm tự thêm '
        'dưới dòng "Số:" và vào tiêu đề bảng tổng hợp), chưa ghi số phương án; Bản CHÍNH THỨC tự xóa chữ DỰ THẢO. Hết báo "chưa có mẫu '
        'Dự thảo" khi đã có mẫu.',
        'Ô tìm kiếm (đơn giá, bảng giá đất, cây trồng, chọn hộ khi in, quyết định…) có kính lúp, nút xóa nhanh và lọc khi ngừng gõ - gõ '
        'tiếng Việt có dấu không còn giật bảng. Thanh tiêu đề 38 px, dải tên phần mềm gọn 48 px.',
    )),
    ('0.9.81', '14/10/2026', (
        'Biểu tượng PABT mới (thiết kế 3D 2026): nền xanh hoàng gia viền kim loại, mái nhà vàng kim, khối thửa đất ngọc lục bảo - '
        'trong phần mềm, ngoài Desktop, Start Menu và thanh taskbar.',
        'Lối tắt Desktop / Start Menu do bộ cài tạo mang cùng định danh ứng dụng với phần mềm: ghim PABT lên taskbar giữ đúng biểu '
        'tượng, cửa sổ đang mở nhập vào nút đã ghim (không tách thành hai nút).',
        'Dán danh sách tài sản (Lập phương án chi tiết và Khái toán & dự toán): gõ mỗi dòng "Tên tài sản ĐVT Số lượng", cách nhau dấu '
        'cách, ví dụ "Nhà tạm m2 4*5" - phần mềm tự tính số lượng (20), tự nhận đơn vị tính và tự xếp vào đúng loại tài sản. Thêm "80%" '
        'cuối dòng nếu có tỷ lệ; dán từ Excel và kiểu gõ cũ vẫn dùng được.',
    )),
    ('0.9.80', '13/10/2026', (
        'Màn hình chào: bảng "Hồ sơ dự án làm việc gần đây" khi trống hiện hướng dẫn bắt đầu (thay cho lưới trắng); các nút "Mở đã chọn", '
        '"Xóa khỏi danh sách" chuyển lên đầu bảng, bên trái ô tìm (tìm được theo tên dự án và địa bàn). Chân trang có 4 liên kết: Hướng dẫn '
        'sử dụng, Tra cứu Bảng giá đất NQ 28, Quy trình 16 bước QĐ 18 (bảng 16 bước và chỗ làm trong phần mềm), Lịch sử cập nhật.',
        'Chưa mở dự án thì nhóm Lập phương án, Tổng hợp & trình duyệt, Phê duyệt & bàn giao ở menu trái được làm mờ; mở dự án là sáng lên.',
        'Banner: bỏ chữ "Máy đơn" (trạng thái máy đơn / máy chủ LAN chỉ còn ở thanh trạng thái phía dưới), tên đơn vị đổi sang vàng kim '
        'dễ đọc; nút A− / A+ có khung viền.',
    )),
    ('0.9.79', '13/10/2026', (
        'Màn hình chào: ba thẻ "Dự án mới", "Mở dự án", "Nhập file Excel" to và rõ hơn (210 x 135), bo góc 12px, biểu tượng lớn 38px, tên lệnh '
        'chữ đậm, dòng mô tả nằm trong thẻ; mỗi thẻ một màu (xanh lá, xanh dương, xanh navy), viền đậm khi rê chuột, bấm ở đâu trong thẻ '
        'cũng chạy lệnh.',
    )),
    ('0.9.78', '13/10/2026', (
        'Cửa sổ lập phương án hộ: nút "Dán danh sách tài sản… (Ctrl+Shift+V)" màu xanh, nổi bật, dùng được ở mọi thẻ và bằng phím tắt. '
        'Đang có bảng tài sản trong bộ nhớ đệm (chép từ Excel, Word…) thì hộp tự điền và Phân loại sẵn; bấm "Thêm vào phương án" là '
        'các dòng vào đúng mục Nhà, Cây, Vật nuôi, Hỗ trợ và tổng tiền tính lại ngay.',
    )),
    ('0.9.77', '13/10/2026', (
        'Cửa sổ con: mọi hộp thoại có đủ nút Thu nhỏ, Phóng to, Đóng và góc kéo đổi cỡ; phần mềm nhớ kích thước từng cửa sổ cho lần mở sau. Cửa sổ '
        'chính tối thiểu 1024 x 680; bấm Thu về trả cửa sổ về 1200 x 740 giữa màn hình.',
        'Niêm yết & Lấy ý kiến: thêm nút "Xóa đợt" (hộ trở về danh sách chờ, có hỏi trước và Hoàn tác được) và "In PA Dự thảo gửi dân".',
        'Xuất hồ sơ & Bản in là trung tâm xuất bản duy nhất, có hai chế độ: Bản Dự thảo (mẫu DỰ THẢO, che CCCD) và Bản chính thức (trọn bộ, '
        'gồm tờ trình và báo cáo tiếp thu ý kiến). Hộp Đợt trình chỉ còn danh sách kiểm tra hồ sơ và một nút "Xuất bản hồ sơ đợt này".',
        'Cơ cấu kinh phí: kinh phí tổ chức thực hiện tính đúng 2,5% (3,5% với dự án theo tuyến) trên tổng bồi thường, gốc 100% (trước đây hiện 2,4% / 3,4%). '
        'Số phương án chi tiết đánh số mặc định 01, 02, 03….',
    )),
    ('0.9.76', '13/10/2026', (
        'Nhóm 5 - Bảng tổng hợp kinh phí gọn còn 3 thẻ: Cơ cấu kinh phí dự án (đất, tài sản, cây trồng - vật nuôi, hỗ trợ, thưởng, '
        'kinh phí tổ chức thực hiện theo QĐ 08/2025), Bảng kinh phí chi tiết từng hộ, Đối soát dự toán Pre-F/S với bảng khái toán '
        'ban đầu. Nút "Đi đến Phân hệ Phê duyệt" chuyển nhanh sang Nhóm 6; thẻ Quyết định phê duyệt không còn nằm ở đây.',
        'Đợt trình thẩm định: bố cục hai cột (quản lý đợt + tờ trình | danh sách hộ + đánh số PA), nhãn đếm ngược thời hạn thẩm '
        'định (còn bao nhiêu / 15 ngày), nút "Lấy hộ đã niêm yết xong từ Nhóm 4", khối "Xuất bản hồ sơ trọn gói" gồm tờ trình, bảng '
        'tổng hợp, phương án chi tiết từng hộ và báo cáo tiếp thu ý kiến (Word), có danh sách kiểm tra hồ sơ trước khi xuất.',
        'Sửa lỗi bấm "Xóa số PA chi tiết" báo "int object has no attribute ten".',
        'Nhóm 6 - Quyết định phê duyệt thành trang riêng, thanh khớp số liệu "Đã duyệt: X/N hộ · Tổng tiền: Y đ" (khớp / lệch với tổng '
        'ghi trong quyết định); bỏ dòng nhắc "bấm Danh sách hộ và Thửa…" ở tiêu đề các trang.',
        'Theo dõi chi trả & Bàn giao: cột mốc thu hồi đất (đã thông báo từ 60 ngày với đất nông nghiệp, 120 ngày với đất phi nông '
        'nghiệp), cột vận động / cưỡng chế, Sổ nhật ký vận động (vận động quá 10 ngày không thành thì "Đủ điều kiện cưỡng chế thu '
        'hồi đất theo Điều 89"), xuất danh sách đề nghị ban hành quyết định cưỡng chế. Các mốc ngày sửa được ở "Mốc thời hạn…".',
        'Báo cáo tiến độ GPMB: bảng điều hành gồm tỷ lệ giải ngân tiền bồi thường, tỷ lệ diện tích mặt bằng sạch đã bàn giao, '
        'danh sách thửa chưa bàn giao mặt bằng (còn vướng mắc) xếp theo mức Gấp / Cao / Theo dõi.',
    )),
    ('0.9.75', '13/10/2026', (
        'Niêm yết & Lấy ý kiến: hai nút đưa hộ vào đợt gộp thành "Đưa hộ vào đợt" (thêm toàn bộ hộ đủ điều kiện / chọn hộ từ danh '
        'sách), "Ngày họp lấy ý kiến" đổi thành "Ngày họp dân"; dải tiến độ một dòng "Đồng thuận … · Không đồng ý … · Ý kiến khác … '
        '· Chưa lấy ý kiến …".',
        'Thẻ Lấy ý kiến: bấm ô Ý kiến (hoặc phím Space) để đổi nhanh Chưa lấy ý kiến → Đồng ý → Không đồng ý → Ý kiến khác, có màu; '
        'bấm đúp ô Nội dung để nhập phản ánh của người dân.',
        'Thẻ Đối thoại & Tiếp thu: thêm nút Xuất biên bản đối thoại. Thẻ Tổng hợp: tỷ lệ đồng thuận theo nhóm lý do (giá đất, nhà, '
        'cây trồng, tái định cư…); báo cáo tổng hợp ý kiến có thêm trang theo nhóm lý do.',
        'Thẻ Niêm yết công khai: kéo thanh ngăn giữa bảng Hộ niêm yết và bảng Hộ vướng để đổi chiều cao.',
        'Cửa sổ lập phương án: nút Tra giá đất NQ 28 ngay ở mục 1 (ghi vị trí và điền giá theo loại đất); bấm đúp ô Nguồn gốc của '
        'thửa mở hộp riêng, dòng bảng không bị phình cao.',
    )),
    ('0.9.74', '13/10/2026', (
        'Biểu tượng PABT mới (PABT Fluent Isometric 3D): mái nhà vàng kim che khối thửa đất 3D ngọc lục bảo và vàng kim, nền '
        'squircle xanh navy viền kim loại, chữ PABT. Dùng cho cửa sổ, thanh tiêu đề, taskbar, file PABT.exe, lối tắt ngoài Desktop '
        'và bộ cài (đủ các cỡ 16 đến 256 px).',
        'Sửa lỗi taskbar Windows gộp biểu tượng PABT vào biểu tượng Python: phần mềm đăng ký định danh ứng dụng riêng khi khởi động.',
    )),
    ('0.9.73', '13/10/2026', (
        'Đơn giá bồi thường gọn: dải thông tin một dòng (bộ đơn giá, các quyết định căn cứ, trạng thái khóa quản trị); bỏ nút '
        'Giá đất và Đơn giá riêng (đã có ở menu trái), bỏ cập nhật từ web và tra cứu trên trình duyệt.',
        'Nút Cập nhật đơn giá: Nạp từ file định mức (Excel, gói .sqlite, CSV) và Sao lưu bộ đơn giá ra file (.sqlite / Excel).',
        'Nút Quản trị bảo mật: mở khóa, đổi mật khẩu, khôi phục bộ đơn giá chuẩn gốc (bộ đang dùng được cất lại, không xóa). '
        'Thêm / sửa / thay thế / xóa một mục: bấm chuột phải trên bảng.',
        'Đơn giá đặc biệt: mô tả gọn, nút "Lưu thay đổi" xanh lá khi có thay đổi; thẻ thẩm định xếp 6 ô chứng thư thành 2 cột, '
        'nút Chọn file và Đưa vào đơn giá lên thanh trên cùng - bảng tài sản thẩm định cao hơn.',
    )),
    ('0.9.72', '13/10/2026', (
        'Thông tin dự án gọn: chỉ còn một ô Tên dự án (bỏ Tên đầy đủ), bỏ Số phương án và Ký hiệu số - ký hiệu số phương án nay '
        'đặt theo từng đợt trình (Trình phê duyệt > Sửa đợt). Thêm ô Cơ quan thẩm định (gợi ý Phòng Kinh tế, Hạ tầng và Đô '
        'thị phường / Phòng Kinh tế xã), dùng trong tờ trình.',
        'Kinh phí QĐ 08/2025 tự chọn theo tên dự án: có đường, tuyến, kênh, đường dây, đường ống… là "Hạ tầng theo tuyến (≤ '
        '3,5%)", còn lại "Dự án khác (≤ 2,5%)"; vẫn chọn lại được.',
        'Danh sách hộ: cột Địa chỉ hiện gọn (bỏ xã / phường trùng địa bàn dự án và huyện, tỉnh), rê chuột xem địa chỉ đầy đủ.',
        'Cửa sổ lập phương án: Ctrl + ← / Ctrl + → chuyển hộ trước / hộ sau.',
        'Mật độ cây: gõ số cây ở thẻ Cây trồng là phần mềm tự đối chiếu mật độ và báo khi vượt; nhận mật độ theo tên gần '
        'đúng (Bưởi da xanh -> Cây bưởi); hộp Tính mật độ hiện thêm mật độ thực tế.',
    )),
    ('0.9.71', '13/10/2026', (
        'Trang Khái toán & dự toán bố cục mới: tiêu đề và chế độ (Lập khái toán / So sánh với thực tế), thông tin chuẩn bị đầu '
        'tư có thêm ô Kinh phí QĐ08 (chọn loại dự án là tự thêm chi phí tổ chức 3,5% / 2,5% và dự phòng), một thanh nhập nhanh '
        '(Lấy khối lượng, Mục từ Đất tới Thưởng, Tra NQ 28, Dán danh sách, Thêm vào bảng), bảng dự toán, thẻ tổng cộng, '
        'hàng nút Mở tệp / Tạo mới / Xuất báo cáo / Lưu dự toán (Ctrl+S).',
        'Thanh nhập nhanh của khái toán nằm trên một hàng (nút "Dán danh sách…" và "Thêm vào bảng" ở cuối hàng), bảng dự toán '
        'cao thêm. Màn hình hẹp thì hai nút tự xuống dòng thay vì làm cửa sổ rộng hơn màn hình.',
        'Hàng "Thêm tài sản" có ô Khối lượng riêng. Cây nhập theo đường kính / chu vi: số đo ở ô số đo, số cây ở ô Khối lượng '
        '(đường kính 23, khối lượng 100 = 100 cây).',
        'Phím Enter dùng được trên nút "Thêm vào bảng"; Enter ở ô Loại đất chuyển sang ô Diện tích.',
    )),
    ('0.9.70', '12/10/2026', (
        'Menu trái theo quy trình 16 bước QĐ 18/2026: nút "Màn hình chính" riêng trên cùng, rồi 6 nhóm - Khái toán & dự toán, '
        'Dự án triển khai, Đơn giá & bảng giá, Lập phương án, Tổng hợp & trình duyệt, Phê duyệt & bàn giao.',
        'Lệnh mới "So sánh với thực tế" (khái toán đã duyệt so với áp giá thực tế). "Cập nhật bảng giá đất" chuyển sang menu '
        'Công cụ, "Trạng thái hộ" sang menu Dữ liệu (vẫn có khi bấm chuột phải danh sách hộ).',
        'Khái toán & dự toán có khối thông tin chuẩn bị đầu tư: tên dự án, chủ đầu tư, nguồn vốn, địa bàn, diện tích, số thửa, '
        'số hộ dự kiến - lưu trong file .pabtdt, không phụ thuộc dự án đang mở.',
        'Niêm yết & Lấy ý kiến gọn 4 thẻ: Niêm yết công khai (kèm danh sách hộ vướng), Lấy ý kiến nhân dân, Đối thoại & Tiếp '
        'thu, Tổng hợp kết quả ý kiến.',
    )),
    ('0.9.69', '12/10/2026', (
        'Mở / nhập dự án luôn về Danh sách hộ (trước đây có lúc nhảy vào Dự toán & khái toán). Thanh thẻ chỉ hiện khi mở từ hai '
        'thẻ trở lên (không còn hai chữ "Màn hình chính").',
        'Danh sách hộ có nút "Chọn hộ niêm yết…": phần mềm xét hộ đủ điều kiện niêm yết công khai, lấy ý kiến (đã lập phương án, '
        'có họ tên, nguồn gốc thửa, không tranh chấp, không vướng), tích sẵn; rà lại, Lưu, có thể đưa luôn vào đợt niêm yết.',
        'Đổi tên menu: "Dự thảo PABT" thành "Niêm yết & Lấy ý kiến", "Đợt trình" thành "Trình phê duyệt", "Bộ đơn giá" thành '
        '"Đơn giá bồi thường", "Đơn giá riêng" thành "Đơn giá đặc biệt". Bỏ menu "Tổng quát hộ".',
        'Đánh lại mã: nhà, công trình TS1…; cây trồng CT1…; vật nuôi VN1…; chính sách hỗ trợ CS1…; thưởng TH1… (dự án cũ tự '
        'chuyển khi mở). Bỏ các dòng chính sách hỗ trợ lẫn trong thẻ Nhà, công trình và các quy ước gắn sẵn.',
        'Thẻ Vật nuôi: dự án chưa có danh mục vật nuôi thì bấm ▼ hỏi bổ sung từ bộ đơn giá.',
        'Bản in: đường kẻ dưới tên dự án dài 7 cm, giữa dòng; nguồn gốc đất căn đều, giữa ô; mục đất / thưởng không có tiền thì '
        'để trống tỷ lệ, số lượng, đơn giá; thành tiền thưởng in đậm, bỏ chữ "Hộ".',
        'Thông tin dự án thêm Chủ đầu tư; kinh phí tổ chức thực hiện chỉ chọn loại dự án (tỷ lệ tự lấy mức của loại).',
        'Trình phê duyệt: mẫu văn bản đề nghị thẩm định, phê duyệt phương án và quyết định thu hồi đất mới; bỏ mẫu Phương án '
        'tổng (cả ở In / Xuất); thêm nút "Xóa số PA chi tiết".',
    )),
    ('0.9.68', '12/10/2026', (
        'Sửa lỗi bấm "Tệp tin" trên thanh menu không mở được: một khung ẩn nằm đè góc trên bên trái cửa sổ nuốt cú bấm.',
    )),
    ('0.9.67', '12/10/2026', (
        'Dự toán & khái toán có hàng "Thêm tài sản" giống lập phương án hộ: chọn mục, gõ tên không dấu hoặc ▼ danh sách, '
        'số lượng có công thức (=4,2*5,7), tỷ lệ %, ghi chú; cây nhập theo đường kính / chu vi thân.',
        'Dự toán dùng được "Dán danh sách tài sản…" (tự xếp vào nhà / cây / vật nuôi / hỗ trợ) như phương án hộ.',
        'Phương án hộ và dự toán dùng chung một bộ lệnh nhập tài sản; bỏ nút "Thêm hạng mục" cũ của dự toán.',
    )),
    ('0.9.66', '12/10/2026', (
        'Mỗi lệnh một chỗ: bỏ các lệnh trùng giữa menu trái và thanh menu.',
        'Menu Cài đặt bỏ "Thông tin dự án" (đã có ở menu trái). Menu Dữ liệu bỏ Báo cáo tổng hợp, Xuất báo cáo đối chiếu; menu '
        'Công cụ bỏ Bộ đơn giá (đều ở menu trái).',
        'Thanh tiêu đề bỏ nút Cài đặt, Hướng dẫn, Hoàn tác, Làm lại (đã có ở menu Cài đặt, Trợ giúp, Chỉnh sửa; Ctrl+Z, Ctrl+Y, F1 vẫn dùng).',
        'Danh sách hộ chỉ còn nút Thêm hộ, Xóa hộ; bỏ hàng "Đã chọn N hộ" (số hộ chọn ở thanh trạng thái). Màn hình chào bỏ liên kết '
        'Bảng giá đất NQ 28 và Cài đặt.',
    )),
    ('0.9.65', '12/10/2026', (
        'Thanh tiêu đề một hàng như VS Code: biểu tượng, menu, Hoàn tác / Làm lại, tên dự án ở giữa, Hướng dẫn, Cài đặt '
        'và nút thu nhỏ / phóng to / đóng.',
        'Cửa sổ vẫn kéo mép đổi cỡ, kéo lên đỉnh màn hình để phóng to, bấm đúp vùng trống để phóng to / thu về như cũ.',
        'Hàng menu hiện đủ ở màn hình phóng to 125% (trước bị dồn vào nút »).',
        'Góc phải banner cố định: ô dự án, máy đơn, phiên bản, tem bản quyền luôn hiện đủ; tên dự án dài tự rút gọn "…".',
        'Cập nhật giá đất từ web: có ô dán đường dẫn nghị quyết / phụ lục (phần mềm nhớ theo tỉnh cho lần sau); gõ tên tỉnh cũ '
        '(Bình Phước, Bình Dương…) tự đổi sang tỉnh mới; tỉnh chưa có văn bản thì lấy giá tham khảo guland.vn, ghi rõ "tham khảo".',
        'Sửa lỗi không mở được vbpl.vn và trang có chứng chỉ mới (Windows chưa tải chứng chỉ gốc).',
        'Mẫu in riêng đặt tên có dấu "Dự thảo" giữ chữ DỰ THẢO khi in (trước bị xóa).',
        'Kiểm tra lỗi nhanh hơn; xuất báo cáo đối chiếu 5.000 hộ nhanh gấp đôi.',
    )),
    ('0.9.64', '12/10/2026', (
        'Khôi phục nút thu nhỏ, phóng to và đóng của Windows trên thanh tiêu đề.',
        'Menu trắng và banner xanh giữ như bản 0.9.63.',
    )),
    ('0.9.63', '12/10/2026', (
        'Menu trắng cao 28px. Banner xanh sapphire có tên phần mềm, tên cơ quan, ô dự án, máy đơn, phiên bản và tem bản quyền.',
    )),
    ('0.9.62', '12/10/2026', (
        'Banner xanh lấy lại ô dự án, máy đơn, phiên bản và tem bản quyền.',
        'Menu trắng cao 28px. Tên phần mềm 14px, tên cơ quan 12px.',
    )),
    ('0.9.61', '12/10/2026', (
        'Tên cơ quan trên banner xanh đổi sang màu bạch kim.',
        'Nền banner xanh đậm hơn, viền đáy xanh sáng 2px.',
    )),
    ('0.9.60', '12/10/2026', (
        'Menu nền trắng, chữ to hơn, canh giữa với biểu tượng.',
        'Banner xanh nằm riêng phía dưới: tên phần mềm trên, tên cơ quan dưới.',
    )),
    ('0.9.59', '12/10/2026', (
        'Thanh trên hiện lại tên phần mềm và tên cơ quan.',
        'Cả hai dòng chữ cỡ 13px.',
    )),
    ('0.9.58', '12/10/2026', (
        'Menu nằm trên hàng tiêu đề, cạnh biểu tượng.',
        'Đã bỏ chữ PABT trên hàng đó. Hàng cao gấp 1,5 lần.',
    )),
    ('0.9.57', '12/10/2026', (
        'Thanh trên chỉ còn biểu tượng và menu.',
        'Đã bỏ chữ PABT và tên cơ quan khỏi thanh này.',
    )),
    ('0.9.56', '12/10/2026', (
        'Thanh tiêu đề chỉ còn chữ PABT cạnh biểu tượng.',
        'Menu Tệp tin, Chỉnh sửa nằm cùng hàng đó. Không còn một thanh menu riêng bên dưới.',
    )),
    ('0.9.55', '12/10/2026', (
        'Băng tiêu đề gọn còn 42px. Chữ menu lớn hơn tên phần mềm.',
        'Dòng cơ quan chuyển xanh băng. Đèn máy đơn và LAN dùng chấm xanh ngọc.',
    )),
    ('0.9.54', '11/10/2026', (
        'Bỏ mục Cập nhật bảng giá đất trong Bộ đơn giá.',
        'Cập nhật giá đất chỉ còn một chỗ: menu trái, nhóm Bảng giá và chính sách.',
    )),
    ('0.9.53', '11/10/2026', (
        'Chân trang màn hình chào mở Lịch sử cập nhật phần mềm.',
        'Lịch sử bắt đầu từ bản này. Các bản đã phát hành trước đó không được ghi lại.',
    )),
)


def moi_nhat() -> str:
    return MUC[0][0] if MUC else ''

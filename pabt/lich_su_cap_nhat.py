"""Lịch sử cập nhật phần mềm, hiện ở chân trang màn hình chào.

Bản trước 0.9.53 không ghi. Mỗi phiên bản mới thêm một mục ở ĐẦU danh sách,
cùng số với pabt.__version__.
"""
from __future__ import annotations

# (phiên bản, ngày, các dòng người dùng đọc được)
MUC = (
    ('0.9.87', '14/10/2026', (
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

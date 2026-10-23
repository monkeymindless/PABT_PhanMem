# Bộ công cụ OpenXML Word (pabt/openxml_word.py)

- Dựng file `.docx` bằng mã (chỉ thư viện chuẩn, chạy cả Python 3.8 / Win 7): `chay` (chữ), `doan` (đoạn), `doan_gach_ho` (gạch dưới hở),
  `doan_ke_ngang`, `bang` / `hang` / `o` (bảng, gộp ô ngang `nhap=`, dọc `gop_doc=`), `sect_pr` (khổ giấy, lề), `dien_cho_trong`
  (điền `{ten}` một lượt, đã thoát ký tự XML), `goi_docx` / `luu`, `doc_than` (lấy thân của một .docx soạn bằng Word).
- `MAU_KHUNG.docx` là mẫu khung (quốc hiệu, bảng đầu, mục I - III, chữ ký) mở bằng Word để xem; tạo lại bằng
  `.venv\Scripts\python -m pabt.openxml_word mau mau_word\MAU_KHUNG.docx`. Mọi chỗ `{ten}` được phần mềm điền khi in.
- Cách nhúng một mẫu mới vào phần mềm in: viết hàm trả (thân, sectPr) như `openxml_word.mau_khung()` (xem `in_word.noi_dung_chi_tiet`
  làm ví dụ đầy đủ), điền dữ liệu bằng `dien_cho_trong`, ghi bằng `luu`; PDF / in lấy từ Word, máy không có Word thì
  `docx_sang_pdf.xuat_pdf_tu_docx`.
- Lưu ý: `.doc` nhị phân (Word 97-2003) không dựng được bằng mã; dùng `.docx` (Word mở được, Lưu thành `.doc` nếu cần).
- Thư mục này KHÔNG đóng vào bộ cài.

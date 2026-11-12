# Văn phòng kiểm định LARC - quy ước chung của mọi chuyên gia

Mục đích: tìm lỗi ẨN của một phiên bản - lỗi mà bộ test, lượt bấm mọi nút, đo tốc độ đều cho qua - và lỗi đã thấy
nhưng bị bỏ qua / chưa xử lý được. Không soát lại danh sách lỗi đã biết của bản cũ: việc đó bộ test đã làm.

## 1. Đọc trước khi săn
1. `ket_qua_kiem_tra/van_phong/<bản>/pham_vi.md` (do `van_phong.py pham-vi` dựng): file đổi, hàm đổi, hàm đổi mà
   không test nào nhắc tên, cặp phải sửa cùng nhau nhưng chỉ một bên đổi.
2. `python van_phong.py ton-dong`: lỗi còn mở từ các bản trước - phần thuộc chuyên môn của mình phải soát lại.
3. `CLAUDE.md` mục "Quy tắc đang hiệu lực"; trước khi kết luận về một hàm, `grep` tên hàm trong
   `docs/LICH_SU_PHAT_TRIEN.md`: nhiều thứ trông như lỗi là QUYẾT ĐỊNH của người dùng (không báo lại).
4. Có `graphify-out/graph.json`: chạy `graphify query "<câu hỏi>"` / `graphify path "<A>" "<B>"` trước khi grep
   hoặc đọc file mã nguồn.

## 2. Giới hạn
- KHÔNG sửa `pabt/`, `tests/`, `mau_in/`, bộ cài. Văn phòng chỉ tìm và chứng minh; sửa là việc khác, làm sau.
- KHÔNG đụng dữ liệu thật ở thư mục cha (file `.pabt`, `.xlsm`). Dự án thử: tự tạo ở thư mục tạm bằng hàm dựng
  mẫu của bộ test, đặt `PABT_THU_MUC_MAY` vào thư mục tạm (không ghi `%APPDATA%\PABT` thật).
- Script thử nghiệm ghi vào `ket_qua_kiem_tra/van_phong/<bản>/thu/<tên chuyên gia>/` bằng công cụ ghi file (heredoc
  của Bash nuốt dấu `\`), chạy với `QT_QPA_PLATFORM=offscreen`, `PYTHONIOENCODING=utf-8`,
  `QT_QPA_FONTDIR=C:\Windows\Fonts`, `.venv\Scripts\python`.
- Không chạy cả bộ test, không chạy công cụ đo tốc độ (nhiều chuyên gia chạy song song: nhiễu, treo máy). Chỉ chạy
  test / script nhắm đúng chỗ nghi. Không gửi máy in, không mở Word / Excel thật, không ra mạng.
- Không hộp thoại thật: hộp thoại mới mở với `im_lang = True` / `cho=False`.

## 3. Thế nào là một phát hiện
Một phát hiện = một hành vi SAI quan sát được (số sai, mất dữ liệu, sập, treo, ghi vượt quyền, chữ / màu không đọc
được, bản dựng thiếu file), kèm:
- `tai_hien`: lệnh hoặc đường dẫn script chạy lại được, không cần sửa gì;
- `bang_chung`: đầu ra thật đã chạy (dán nguyên, cắt ngắn), ghi rõ mong đợi so với thực tế.

Chưa chạy ra được thì ghi `trang_thai: nghi_van` và nói thẳng là chưa tái hiện. KHÔNG phải phát hiện: ý thích về
kiểu viết mã, "nên tái cấu trúc", điều trái với quyết định của người dùng ghi trong CLAUDE.md, lỗi suy ra từ đọc mã
mà không chạy. Mười phát hiện có chứng cứ hơn một trăm dòng nghi ngờ.

Mỗi phát hiện phải trả lời `vi_sao_lot`: vì sao các lớp kiểm hiện có không bắt (không test nào chạm; test có nhưng
vá mất nhánh này; chỉ xảy ra ở Qt5 / tông Tối / file cũ / thứ tự thao tác cụ thể) và `de_xuat_chan`: test nào thêm
vào thì bản sau không lọt nữa.

## 4. Mức
- P0: mất / hỏng dữ liệu, số tiền sai trên bản in hay trong file, ghi vượt quyền, không mở được chương trình.
- P1: lệnh chính không chạy / chạy sai trong điều kiện thường gặp; sập; treo.
- P2: sai trong điều kiện hiếm, có đường vòng; giao diện không đọc được ở một tông / một bản Qt.
- P3: bất tiện, chữ sai, chậm nhẹ.

## 5. Đầu ra
Ghi `ket_qua_kiem_tra/van_phong/<bản>/phat_hien_<tên chuyên gia>.json` - một danh sách:

```json
[{"tieu_de": "một câu nói rõ cái gì sai", "chuyen_gia": "vp-so-lieu-bien", "muc": "P1",
  "tep": "pabt/x.py", "dong": 120, "ham": "ten_ham", "mo_ta": "điều kiện, mong đợi, thực tế",
  "tai_hien": ".venv\\Scripts\\python ket_qua_kiem_tra/van_phong/1.1.07/thu/vp-so-lieu-bien/a.py",
  "bang_chung": "mong 1.234.500, ra 1.234.000", "vi_sao_lot": "...", "de_xuat_chan": "...",
  "trang_thai": "nghi_van"}]
```

Chuyên gia săn luôn ghi `nghi_van`; chỉ `vp-phan-bien` nâng lên `xac_nhan` sau khi tự chạy lại. Câu trả lời cuối
của chuyên gia: đường dẫn file JSON, số phát hiện theo mức, và những chỗ ĐÃ soát mà không thấy gì (để lượt sau khỏi
soát lại) cùng những chỗ CHƯA soát được và vì sao.

## 6. Sổ lỗi
`docs/van_phong/so_loi.json` là sổ xuyên phiên bản. Trạng thái: `nghi_van` -> `xac_nhan` -> `da_sua`; `hoan` (biết
mà chưa xử lý được, phải có lý do) ; `khong_phai_loi` (phải có lý do). Lỗi `da_sua` mà gặp lại được ghi "TÁI PHÁT".
Mục `hoan` và `xac_nhan` chưa sửa hiện lại ở đầu mỗi lượt cho tới khi đóng - không lỗi nào tự biến mất.
Cặp "sửa bên này phải sửa bên kia" mới học được: thêm vào `docs/van_phong/cap_di_cung.json`.

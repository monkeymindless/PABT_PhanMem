"""Tổ chức làm nhiệm vụ bồi thường dùng phần mềm: hiện trên băng tiêu đề, điền sẵn thông tin đơn vị khi lập dự án mới.
Đổi đơn vị: sửa các hằng số dưới đây (thông tin trên bản in vẫn sửa được ở "Thông tin dự án")."""
from __future__ import annotations

VAI_TRO = 'TỔ CHỨC LÀM NHIỆM VỤ BỒI THƯỜNG'
TEN = 'TRUNG TÂM PHÁT TRIỂN QUỸ ĐẤT CHI NHÁNH VĨNH CỬU'
TRUC_THUOC = 'TRUNG TÂM PHÁT TRIỂN QUỸ ĐẤT THÀNH PHỐ ĐỒNG NAI'
DIA_CHI = 'Đường Phan Chu Trinh, khu phố Vĩnh An 1, phường Trị An, thành phố Đồng Nai'
TAC_GIA = 'Thiết kế và phát triển bởi Phan Tuấn Vĩnh - Trung tâm Phát triển quỹ đất Chi nhánh Vĩnh Cửu'

# điền sẵn ở bước 1 "Dự án mới" (khi máy chưa lưu thông tin đơn vị lần trước)
# và dùng trên bản in khi ô tương ứng của dự án còn trống
MAC_DINH = dict(don_vi_cap_tren='Trung tâm Phát triển quỹ đất thành phố Đồng Nai',
                don_vi_tieu_de='Chi nhánh Vĩnh Cửu',
                don_vi_lap='Trung tâm Phát triển quỹ đất Chi nhánh Vĩnh Cửu',
                ky_hieu_so='PA-TTPTQĐ.CNVC',
                chuc_vu_ky='Phó Giám đốc')

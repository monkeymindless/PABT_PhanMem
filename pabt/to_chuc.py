"""Tổ chức làm nhiệm vụ bồi thường dùng phần mềm: hiện trên băng tiêu đề, điền sẵn thông tin đơn vị khi lập dự án mới.
Từ 0.9.85 lấy từ hồ sơ địa phương (pabt_profile.json mục "co_quan" - dia_phuong): đổi đơn vị / địa phương thì sửa file hồ sơ
hoặc nhập gói .pabtcfg, không sửa mã (thông tin trên bản in vẫn sửa được theo dự án ở "Thông tin dự án")."""
from __future__ import annotations

from . import dia_phuong

TAC_GIA = 'Thiết kế và phát triển bởi Phan Tuấn Vĩnh - Trung tâm Phát triển quỹ đất Chi nhánh Vĩnh Cửu'

# các giá trị dưới đây do _ap_ho_so đặt (lúc nạp module và sau mỗi lần nạp lại hồ sơ); nơi dùng đọc to_chuc.TEN… lúc gọi
VAI_TRO = TEN = TRUC_THUOC = DIA_CHI = ''
TEN_PHAN_MEM = 'PHẦN MỀM LẬP PHƯƠNG ÁN BỒI THƯỜNG, HỖ TRỢ, TÁI ĐỊNH CƯ'      # dòng 1 băng tiêu đề (hồ sơ co_quan.ten_phan_mem - đơn vị khác đặt tên riêng)
# điền sẵn ở bước 1 "Dự án mới" (khi máy chưa lưu thông tin đơn vị lần trước) và dùng trên bản in khi ô của dự án còn trống
MAC_DINH: dict = {}


def _ap_ho_so(hs: dict) -> None:
    global VAI_TRO, TEN, TRUC_THUOC, DIA_CHI, MAC_DINH, TEN_PHAN_MEM
    cq = hs['co_quan']
    TEN_PHAN_MEM = str(cq.get('ten_phan_mem') or '').strip() or TEN_PHAN_MEM
    VAI_TRO, TEN, TRUC_THUOC, DIA_CHI = cq['vai_tro'], cq['ten'], cq['truc_thuoc'], cq['dia_chi']
    MAC_DINH = dict(cq['ban_in_mac_dinh'])


dia_phuong.dang_ky(_ap_ho_so)

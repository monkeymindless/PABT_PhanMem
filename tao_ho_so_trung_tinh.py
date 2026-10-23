"""Tạo pabt/pabt_profile_trung_tinh.json - hồ sơ địa phương TRUNG TÍNH cho bản bán cho đơn vị khác (24/10/2026).

Lấy hồ sơ mặc định (pabt_profile.json) và xóa MỌI thông tin riêng của đơn vị / địa phương đang dùng: tên cơ quan, cấp trên, địa chỉ, ký hiệu số,
địa danh ở dòng ngày. Căn cứ pháp lý, mốc thời hạn, tỷ lệ kinh phí GIỮ NGUYÊN (khách tự sửa ở Cài đặt > Cấu hình nghiệp vụ nếu khác).
Bản trung tính được đóng vào bộ cài khi dựng với biến PABT_BAN_TRUNG_TINH=1 (xem DUNG_BAN_TRUNG_TINH.bat): PABT.spec, bo_cai_win\\dung_exe38.py và
pabt.cap_nhat.tao_goi đều thay pabt_profile.json bằng file này. Chạy lại script này mỗi khi pabt_profile.json đổi cấu trúc.

Dùng:  .venv\\Scripts\\python tao_ho_so_trung_tinh.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

GOC = Path(__file__).resolve().parent
NGUON = GOC / 'pabt' / 'pabt_profile.json'
RA = GOC / 'pabt' / 'pabt_profile_trung_tinh.json'


def tao() -> dict:
    hs = json.loads(NGUON.read_text(encoding='utf-8-sig'))
    hs['ten_ho_so'] = 'Hồ sơ trung tính (chưa cấu hình đơn vị)'
    hs['ghi_chu'] = ('Hồ sơ trung tính đóng kèm bản bán: chưa có tên đơn vị / địa phương. Điền ở Cài đặt > Cấu hình nghiệp vụ (thẻ Cơ quan, '
                     'Kiểm tra && bản in) hoặc nhập gói .pabtcfg do nhà cung cấp gửi. Căn cứ pháp lý, mốc thời hạn, tỷ lệ kinh phí trong hồ sơ '
                     'là quy định mẫu - đơn vị tự đối chiếu và sửa theo địa phương mình.')
    cq = hs['co_quan']
    cq['ten'] = 'TÊN ĐƠN VỊ CỦA BẠN'
    cq['truc_thuoc'] = 'CƠ QUAN CẤP TRÊN'
    cq['dia_chi'] = 'Địa chỉ đơn vị'
    cq['ban_in_mac_dinh'] = dict(don_vi_cap_tren='', don_vi_tieu_de='', don_vi_lap='', ky_hieu_so='', chuc_vu_ky='Giám đốc')
    hs['ban_in']['dia_danh_ngay'] = ''
    # căn cứ pháp lý của Đồng Nai -> chỗ trống nhắc điền (sai địa phương còn tệ hơn để trống); luật quốc gia (Luật Đất đai 2024) giữ
    cc = hs['can_cu_phap_ly']
    cc['kinh_phi_to_chuc'] = 'Quyết định của UBND cấp tỉnh về kinh phí tổ chức thực hiện bồi thường (ghi số, ngày, cơ quan ban hành)'
    cc['tham_dinh'] = 'Quy định thẩm định phương án tại địa phương (ghi số, ngày văn bản)'
    cc['to_trinh'] = ['Căn cứ các văn bản pháp luật áp dụng tại địa phương (điền ở Cài đặt > Cấu hình nghiệp vụ hoặc sửa mẫu tờ trình).']
    for k in ('tham_dinh', 'thu_hoi_nn', 'thu_hoi_pnn', 'van_dong'):
        hs['thoi_han'][k]['can_cu'] = 'Theo quy định của địa phương (ghi số, ngày văn bản)'
    return hs


def main() -> int:
    sys.path.insert(0, str(GOC))
    hs = tao()
    from pabt import dia_phuong
    loi = dia_phuong.kiem_tra(hs)
    if loi:
        print('Hồ sơ trung tính chưa hợp lệ:\n- ' + '\n- '.join(loi))
        return 1
    RA.write_text(json.dumps(hs, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f'Đã ghi {RA} ({RA.stat().st_size} byte)')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

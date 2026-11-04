"""1.0.60: đọc toàn văn Quyết định chính sách bồi thường, hỗ trợ, tái định cư (bản OCR, Word). Văn bản thử GIẢ LẬP đúng cấu trúc QĐ 42/2025/QĐ-UBND
(văn bản công khai) kèm các lỗi bản scan thật: số hiệu đọc hỏng, dấu sai, số trang chen giữa câu, ký hiệu khoản sai, dòng tách nhiều ô."""
from __future__ import annotations

import unittest

from pabt import nhap_don_gia as ndg
from pabt import quy_dinh_van_ban as qvb
from tests import APP  # noqa: F401

_LUAT = 'Luật số 31/2024/QH15 được sửa đổi, bổ sung một số điều bởi các Luật số 43/2024/QH15, số 47/2024/QH15'
_ND = 'Nghị định số 88/2024/NĐ-CP được sửa đổi, bổ sung bởi Nghị định số 151/2025/NĐ-CP, Nghị định số 226/2025/NĐ-CP'

DAU = [['sAoy Ký bởi: Ủy ban nhân dân tỉnh Đồng Nai'], [',', '1 ký: 02.10.2025 05:08:38 +07:00'],
       ['ỦY BAN NHÂN DÂN', 'CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM'], ['TĨNH ĐÓNG NAI', 'Độc lập', '- Tự do', '- Hạnh phúc'],
       ['Số: 4à /2025/QĐ-UBND', 'Đồng Nai, ngày 0.) tháng ,{() năm 2025'], ['QUYẾT ĐỊNH']]
GIUA = """Ban hành Quy định về bồi thường, hỗ trợ và tái định cư khi Nhà nước
thu hồi đất trên địa bàn tỉnh Đồng Nai
Căn cứ Luật Tổ chức chính quyền địa phương số 72/2025/QH15;
Căn cứ Luật Ban hành văn bản quy phạm pháp luật số 64/2025/QH15 được
sửa đôi, bồ sung một sô điều bởi Luật số 87/2025/QH15;
Căn cứ Nghị định số 88/2024/NĐ. CP của Chính phủ quy định về bồi
thường, hô trợ và tái định cư khi Nhà nước thu hồi đt được sủa đôi, bô sung bởi
Nghị định số 151/2025/NĐ-CP, Nghị định số 226/2025/NĐ- CP;
Theo đề nghị của Giám đóc Sở Nông nghiệp và Môi trường;
Điều 1. Ban hành kèm theo Quyết định này Quy định về bồi thường, hỗ trợ
và tái định cư khi Nhà nước thu hồi đất trên địa bàn tỉnh Đồng Nai.
Điều 2. Hiệu lực thi hành
1. Quyết định này có hiệu lực thi hành kể từ ngày 44 .tháng.⁄4Ô.năm 2025.
2. Quyết định thay thế các Quy định sau:
a) Quyết định số 58/2024/QĐ-UBND ngày 25 tháng 10 năm 2024 của Ủy
ban nhân dân tỉnh Đồng Nai ban hành Quy định về bồi thường, hỗ trợ và tái định
cư khi Nhà nước thu hồi đất trên địa bàn tỉnh Đồng Nai;
b) Điều 4 và khoản 3 Điều 5 Quyết định số 62/2024/QĐ-UBND ngày 25
tháng 10 năm 2024 của Ủy ban nhân dân tỉnh Đồng Nai ban hành Quy định về bồi
thường chỉ phí di chuyên tài sản;
c) Quyết định số 05/2025/QĐ-UBND ngày 24 tháng 01 năm 2025 của Ủy
ban nhân dân tỉnh Bình Phước ban hành Quy định về bồi thường, hỗ trợ và tái định
cư khi Nhà nước thu hồi đất trên địa bàn tỉnh Bình Phước.
2
Điều 3. Chánh Văn phòng Ủy ban nhân dân tỉnh; Giám đốc Sở Nông nghiệp
và Môi trường chịu trách nhiệm thi hành Quyết định này./.
NWơi nhận:
- Như Điều 3;
QUY ĐỊNH
Chương I
QUY ĐỊNH CHUNG
Điều 1. Phạm vi điều chỉnh
Quy định này quy định chi tiết khoản 2 Điều 104, khoản 5 Điều 109 của Luật Đất đai số 31/2024/QH15 được sửa
đổi, bổ sung một số điều bởi các Luật số 43/2024/QH15;
Điều 15, Điều 16, điểm b khoản 2 Điều 17 của Nghị định số 88/2024/NĐ-CP trên địa bàn tỉnh Đồng Nai.
Điều 4. Khoản tiền tính bằng tỷ lệ phần trăm theo giá trị hiện có của
nhà, công trình xây dựng quy định tại điểm a và điểm d khoản 1 Điều 14
4
Nghị định số 88/2024/NĐ-CP được sửa đổi, bổ sung bởi Nghị định số
151/2025/NĐ-CP, Nghị định số 226/2025/NĐ-CP
1. Khoản tiền tính bằng tỷ lệ phần trăm theo giá trị hiện có của nhà, công
trình xây dựng được xác định theo công thức: 20% x Ty.
Ví dụ: Một nhà xưởng cấp 4 có diện tích xây dựng là 100m, có niên hạn
Sử dụng theo quy định là 20 năm (T), đã sử dụng được 10 năm (T). Đơn giá xây
mới 1.900.000 đồng/01m®. Được bồi thường thiệt hại như sau:
....- Giá trị xây mới nhà: G¡ = 100m x 1.900.000 đồng/m® = 190.000.000
đông.
- Giá trị hiện có của căn nhà: = 190.000.000 đồng - 190.000.000 đông/20 năm x 10 năm = 95.000.000 đồng.
- Khoản tiền là 20% x 95.000.000 đông = 19.000.000 đồng.
- Mức bồi thường công trình là: 95.000.000 đồng + 19.000.000 đồng =
114.000.000 đồng.
2. Đối với nhà, công trình xây dựng không đủ tiêu chuẩn kỹ thuật thì đơn vị lập dự toán mức bồi thường cụ thể, không tính theo tỷ lệ 20%.
Điều 6. Xác định chỉ phí đầu tư vào đất còn lại đối với trường hợp
không có hồ sơ, chứng từ chứng minh quy định tại điểm b khoản 2 Điều 17
Nghị định số 88/2024/NĐ-CP được sửa đối, bố sung bởi Nghị định số
151/2025/NĐ-CP, Nghị định số 226/2025/NĐ-CP
1, Đối với đắt nông nghiệp; mức bồi thường là 15.000 đồng/m” (không tính
thời hạn sử dụng đât).
2. Đối với đất phi nông nghiệp; mức bồi thường là 30.000 đồng/m, được
tính theo thời hạn sử dụng đât còn lại và được xác định theo công thức sau:
30.000 đồng/m”
P= x—= ẹxỹŸÐ
Điều 8. Bồi thường chỉ phí di chuyên tài sản khi Nhà nước thu hồi đất
quy định tại khoản 2 Điều 104 Luật số 31/2024/QH15 được sửa đổi, bỗ sung
một số điều bởi các Luật số43/2024/QH15, số 47/2024/QH15
1. Bồi thường chỉ phí để tháo dỡ, di chuyên, lắp đặt đối với hộ gia đình, cá
nhân khi Nhà nước thu hôi đât như sau:
a) Di chuyển trong địa bàn cấp xã: 10.000.000 đồng/hộ:
b) Di chuyển ngoài địa bàn cấp xã: 15.000.000 đồng/hộ:
c) Di chuyển ngoài tỉnh: 20.000.000 đồng/hộ.
3. Trường hợp di chuyển điện thoại, đồng hồ nước, đồng hồ điện thì được bồi thường chỉ phí tháo dỡ, di chuyển theo đơn giá do Ủy ban nhân dân tỉnh quy định.
Điều 9. Bồi thường, hỗ trợ chỉ phí đào, bốc, di dời mồ mả và các chỉ
phí khác có liên quan trực tiếp để di dời mồ mả đến vị trí mới
1. Mức bồi thường, hỗ trợ chỉ phí đảo, bốc, di dời mồ má và các chỉ phí
khác có liên quan trực tiệp đề di dời mô má đên vị trí mới là 10.000.000
đông/mộ.
Mục 2
HỖ TRỢ KHI NHÀ NƯỚC THU HỒI ĐẤT
Điều 10. Hỗ trợ ổn định đời sống khi Nhà nước thu hồi đất quy định
tại khoản 2 Điều 19 Nghị định số 88/2024/NĐ-CP được sứa đổi, bố sung bởi
Nghị định số 151/2025/NĐ-CP, Nghị định số 226/2025/NĐ-CP
1. Trường hợp hộ gia đình, cá nhân đang sử dụng đất nông nghiệp quy định
tại khoản 1 Điều 19 Nghị định sô 88/2024/NĐ-CP được sửa đôi, bô sung bởi
Nghị định số 151/2025/NĐ-CP, Nghị định sô 226/2025/NĐ-CP, bị thu hôi dưới
30% diện tích đât nông nghiệp đang sử dụng thì được hô trợ ôn định đời sông với
mức hô trợ băng 50% mức áp dụng đôi với trường hợp bị thu hôi từ 30% đên 70%.
Mức hỗ trợ cho một nhân khẩu quy định tại khoản này được tính bằng tiền
tương đương 30 kg gạo trong 01 tháng theo thời giá trung bình tại thời điệm hô
trợ của địa phương.
Điều 12. Hỗ trợ di dời vật nuôi; hỗ trợ để tháo dỡ, phá dỡ, di dời tài
sản gắn liền với đất là phần công trình xây dựng theo giấy phép xây dựng có
thời hạn quy định tại Điều 21 Nghị định số 88/2024/NĐ-CP được sửa
đổi, bố sung bởi Nghị định số 151/2025/NĐ-CP, Nghị định số 226/2025/NĐ-
CP
1. Hỗ trợ di dời vật nuôi:
a) Đối tượng hỗ trợ: Các tổ chức, cá nhân có cơ sở chăn nuôi với quy mô từ 01 đơn vị vật nuôi trở lên phải di dời; môi đơn vị vật nuôi tương đương
500kg khôi lượng vật nuôi sông:
d) Mức hỗ trợ di dời vật nuôi: 1.000.000 đồng/đơn vị vật nuôi cùng thời
9
điểm phê duyệt phương án bồi thường.
2. Đối với tài sản gắn liền với đất là phần công trình xây dựng theo giấy
phép xây dụng có thời hạn mà đên thời điêm thu hôi đật giây phép đã hệt thời hạn thì chủ sở hữu tài sản không được bôi thường mà
. được hô trợ đê tháo dỡ, phá dỡ, di dời, như sau:
a) Di chuyển trong địa bàn cấp xã: 6.000.000 đồng/hộ;
b) Di chuyển ngoài địa bàn cấp xã: 8.000.000 đồng/hộ;
c) Di chuyển ngoài tỉnh: 10.000.000 đồng/hộ.
Điều 13. Mức hỗ trợ đào tạo, chuyên đổi nghề và tìm kiếm việc làm quy
định tại khoản 5 Điều 109 {luat}
1. Hộ gia đình, cá, nhân thuộc đối tượng quy định. tại điểm a và điểm b
khoản 1 Điều 109 Luật sô 31/2024/QH15 được sửa đôi, bô sung một sô điều bởi
các. Luật sô43/2024/QH15, sô47/2024/QH15 khi
Nhà nước thu hôi đât nông nghiệp thì được hô trợ đào tạo, chuyên đôi nghề và tìm kiêm việc làm
băng tiên, với mức hô trợ băng 1,5 lân giá đất nông nghiệp cùng loại trong bảng
giá đất của địa phương.
. Hộ gia đình, cá nhân thuộc đối tượng quy định. tại điểm c và điểm d
khoản 1 Điều 109 Luật sô 31/2024/QH15 khi
Nhà nước thu hôi đât nông nghiệp thì được hô trợ đào tạo, chuyên đôi nghệ và
tìm kiêm việc làm băng tiên, với mức hô trợ băng 0,5 lân giá đât nông nghiệp
cùng loại trong bảng giá đất của địa phương.
Mục3
TÁI ĐỊNH CƯ
Điều 14. Mức hỗ trợ tái định cư đối với trường hợp tự lo chỗ ở quy
định tại khoản 2 Điều 23 Nghị định số 88/2024/NĐ-CP được sửa đổi, bố sung
bởi Nghị định số 151/2025/NĐ-CP, Nghị định số 226/2025/NĐ-CP
10
1. Trường hợp hộ gia đình, cá nhân mà có nhu cầu tự lo
chỗ ở thì ngoài việc được bồi thường về đất bằng tiền còn được nhận tiền hỗ trợ
để tự lo chỗ ở. Mức hỗ trợ 6.000.000. đồng/hộ/tháng tại địa bàn xã, 8.000.000
đồng/hộ/tháng tại địa bàn phường đối với hộ có từ 04 nhân khẩu trở xuống, thời
gian hỗ trợ là 06 tháng tại thời điểm bồi thường.
2. Trường hợp hộ gia đình có từ 05 nhân khẩu trở lên thì cứ mỗi nhân khâu
tăng thêm được tính thêm 1.500.000 đồng/nhân khẩu/tháng tại địa bàn xã,
2.000.000 đồng/nhân khẩu/tháng tại địa bàn phường.
Điều 15. Bố trí nhà ở tạm, hỗ trợ tiền thuê nhà ở; cơ chế thưởng đối
với người có đất thu hồi bàn giao mặt bằng trước thời hạn quy định tại
khoản 7 Điều 111 {luat}
1. Người có đất ở bị thu hồi thì được bồi thường bằng đất ở; trường hợp không có nhà ở tạm thì được hỗ trợ tiền
thuê nhà ở.
a) Mức hỗ trợ 6.000.000 đồng/hộ/tháng tại địa bàn xã, 8.000.000
đồng/hộ/tháng tại địa bàn phường đối với hộ có từ 04 nhân khẩu trở xuống, thời
gian hỗ trợ là 06 tháng tại thời điểm bồi thường. Trường hợp hộ gia đình có từ 05
nhân khẩu trở lên thì cứ mỗi nhân khẩu tăng thêm được tính thêm 1.500.000
đồng/nhân khẩu/tháng tại địa bàn xã, 2.000.000 đồng/nhân khẩu/tháng tại địa bàn
phường.
4. Người có đất thu hồi bàn giao mặt bằng trước thời hạn theo thông báo
của đơn vị thì được thưởng với mức thưởng như sau:
"""
BIEU = [['Số tiền bồi thường, hỗ trợ', 'Mức thưởng'], ['- Dưới 20 triệu đồng', '2.000.000 đồng'],
        ['|~ Từ 20 triệu đồng đến dưới 50 triệu đồng', '...4.000.000 đồng'], ['_= Từ 50 triệu đồng đến dưới 100 triệu đồng', '8.000.000 đồng'],
        ['_- Từ 100 triệu đồng đến dưới 200 triệu đồng', '„12.000.000 đồng'], ['- Từ 200 triệu đồng đến dưới 500 triệu đồng', '16.000.000 đồng'],
        ['- Từ 500 triệu đồng trở lên', '„20.000.000 đồng']]
CUOI = """. Điều 17. Hỗ trợ tự lo chỗ ở đối với người đang sử dụng nhà ở thuộc sở
hữu nhà nước năm trong phạm vi thu hồi đất phải phá dỡ nhà quy định tại
khoản 2 Điều 24 Nghị định số 88/2024/NĐ-CP được sứa đối, bổ sung bởi
Nghị định số 151/2025/NĐ-CP, Nghị định số 226/2025/NĐ-CP
1. Đối với trường hợp người đang sử dụng nhà ở thuộc sở hữu nhà nước
nếu tự lo chỗ ở mới thì được hỗ trợ bằng
tiên Mức hỗ trợ 6.000.000 đồng/hộ/tháng tại địa bàn xã, 8.000.000
đông/hộ/tháng tại địa bàn phường đối với hộ có từ 04 nhân khẩu trở xuống.
2. Trường hợp hộ gia đình có từ 05 nhân khẩu trở lên thì cứ mỗi nhân khẩu
tăng thêm được tính thêm 1.500.000 đồng/nhân khẩu/tháng tại địa bàn xã,
2.000.000 đông/nhân khâu/tháng tại địa bàn phường.
Điều 19. Mức hỗ trợ đối với một số trường hợp cụ thể khi Nhà nước
thu hồi đất
1. Hỗ trợ về đất đối với đất không đủ điều kiện bồi thường:
a) Trường hợp đang sử dụng đất nông nghiệp theo quy định tại khoản 7 Điều 12 {nd} thì đối với phần diện tích còn lại được hỗ trợ bằng 50% mức giá bồi
thường đất nông nghiệp theo hiện trạng sử dụng đất.
b) Nhà ở xây dựng trước ngày 01 tháng 7 năm 2014 thì được hỗ trợ bằng 80% giá trị bồi thường;
e) Nhà ở xây dựng sau ngày thông báo thu hồi đất thì không được bồi thường, hỗ trợ;
3. Trường hợp khi thực hiện các dự án xây dựng làm thay đôi hiện trạng về cao độ mặt đường mới so với mặt
đường cũ thì được tính hỗ trợ tiền cải tạo lại theo chiều ngang
thửa đât tiêp giáp với đường. Mức hô trợ như sau:
a) Cao độ tim đường mới so với tim đường cũ cao hơn từ 01 mét đến 02
mét hoặc thập hơn từ 01 mét đên 02 mét, mức hô trợ là 2.000.000 đông/mét dài;
b) Cao độ tim đường mới so với tim đường cũ cao trên 02 mét đến 03 mét
hoặc thập dưới từ 02 mét đên 03 mét, mức hô trợ là 2.500.000 đông/mét dài;
e) Cao độ tim đường mới so với tìm đường cũ cao trên 03 mét hoặc thấp
dưới 03 mét, mức hô trợ là 3.500.000 đồng/mét dài.
4. Hỗ trợ đối với đối tượng thuộc diện chính sách:
a) Hộ bị thu hồi đất là gia đình liệt sĩ thì ngoài việc được hô trợ theo quy định còn được hưởng thêm
khoản hô trợ dành cho những đôi tượng thuộc diện chính sách, cụ thê như sau:
Hỗ trợ cho hộ bị thu hồi đất là gia đình liệt sĩ hoặc có người là Bà mẹ Việt
Nam anh hùng là 30.000.000 đồng trên một hộ;
Hỗ trợ cho hộ bị thu hồi đất có người là thương, bệnh binh có tỷ lệ thương
tật từ 61% đên 80% là 15.000.000 đông trên một hộ;
Hỗ trợ cho hộ bị thu hồi đất có người là thương, bệnh binh có tỷ lệ thương
tật từ 21 % đên 60% là 10.000.000 đông trên một hộ;
c) Hộ nghèo theo quy định của Nhà nước; hộ dân tộc thiểu số thuộc đối
tượng trực tiệp sản xuất nông nghiệp thì được hô trợ 10.000.000 đông trên một hộ;
Chương III
TÓ CHỨC THỰC HIỆN
Điều 20. Quy định chuyển tiếp
1. Đối với trường hợp đã có quyết định thu hồi đất trước ngày Quyết định này có hiệu lực thi hành thì tiếp tục thực hiện theo mức 50.000 đồng/m².
Điều 22. Sửa đỗi, bỗ sung
1. Trường hợp các văn bản pháp luật được dẫn chiếu được sửa đôi, bô sung hoặc thay thê thì áp dụng theo văn bản mới.
"""


def _dong() -> ndg.DongScan:
    giua, cuoi = GIUA.format(luat=_LUAT, nd=_ND), CUOI.format(luat=_LUAT, nd=_ND)
    return ndg.DongScan(DAU + [[x] for x in giua.splitlines()] + BIEU + [[x] for x in cuoi.splitlines()])


TEN_FILE = '42_QDQPPL_QPPL_2025 thay thế 58, 62.pdf'


class TestSoHieu(unittest.TestCase):
    def test_ocr_hong_so_hieu(self):
        """Số hiệu, ngày bản scan đọc hỏng: suy từ tên file và chữ ký số, không lấy Luật 72/2025/QH15 trong dòng Căn cứ."""
        vb = ndg.phan_tich_van_ban(_dong(), TEN_FILE)
        self.assertEqual((vb['loai_vb'], vb['so_hieu'], vb['ngay'], vb['co_quan']),
                         ('Quyết định', '42/2025/QĐ-UBND', '02/10/2025', 'Ủy ban nhân dân tỉnh Đồng Nai'))
        self.assertEqual(vb['nhom'], 4)
        self.assertTrue(vb['trich_yeu'].startswith('Ban hành Quy định về bồi thường'))

    def test_khong_lay_tu_can_cu(self):
        vb = ndg.phan_tich_van_ban([['QUYẾT ĐỊNH'], ['Căn cứ Luật số 72/2025/QH15 ngày 25 tháng 10 năm 2024;'], ['Điều 1. Ban hành']])
        self.assertEqual((vb['so_hieu'], vb['ngay']), ('', ''))

    def test_cac_dang_so_hieu(self):
        for chu in ('Số: 42/2025/QĐ-UBND', 'SỐ: 42 /2025/QĐ-UBND', 'Quyết định số 42/2025/QĐ-UBND', 'Số: 42/2025/QĐ- UBND', 'Sô: 42 / 2025 / QĐ. UBND'):
            vb = ndg.phan_tich_van_ban([[chu, 'Đồng Nai, ngày 02 tháng 10 năm 2025'], ['QUYẾT ĐỊNH'], ['Căn cứ Luật số 72/2025/QH15;']])
            self.assertEqual((vb['so_hieu'], vb['ngay']), ('42/2025/QĐ-UBND', '02/10/2025'), chu)

    def test_kem_theo(self):
        vb = ndg.phan_tich_van_ban([['QUY ĐỊNH'], ['(Ban hành kèm theo Quyết định số 42/2025/QĐ-UBND ngày 02 tháng 10 năm 2025)'], ['Căn cứ Luật']])
        self.assertEqual((vb['so_hieu'], vb['ngay']), ('42/2025/QĐ-UBND', '02/10/2025'))

    def test_ten_file(self):
        for ten, so in ((TEN_FILE, '42/2025/QĐ-UBND'), ('31_2025_QD-UBND_673864.docx', '31/2025/QĐ-UBND'),
                        ('Bản sao của QD42-2025-QD-UBND 02-10-2025 BỒI THƯỜNG.docx', '42/2025/QĐ-UBND'),
                        ('02_2026_VBHN-QD-UBND_729578.docx', '02/2026/VBHN-UBND'), ('DS DU AN DT762.xlsx', ''), ('03.pdf', '')):
            self.assertEqual(ndg.so_hieu_tu_ten_file(ten), so, ten)

    def test_so_hieu_doc_roi(self):
        self.assertEqual(ndg.chuan_chu_so_hieu('Nghị định 88/2024/NĐ. CP, 151/2025/NĐ- CP, QĐ- UBND, QH 15, 42 /2025/ QĐ-UBND'),
                         'Nghị định 88/2024/NĐ-CP, 151/2025/NĐ-CP, QĐ-UBND, QH15, 42/2025/QĐ-UBND')

    def test_chi_dieu_khoan_thay_the(self):
        vb = ndg.phan_tich_van_ban(_dong(), TEN_FILE)
        self.assertEqual(vb['thay_the_vb'], ['58/2024/QĐ-UBND', '62/2024/QĐ-UBND', '05/2025/QĐ-UBND'])
        self.assertEqual(len(vb['can_xem']), 4)
        self.assertTrue(vb['can_xem'][0].startswith('2. Quyết định thay thế'))
        toan = ' '.join(vb['can_xem'])
        for la in ('87/2025/QH15', '226/2025', '72/2025'):               # dẫn chiếu, căn cứ không phải nội dung thay thế
            self.assertNotIn(la, toan)
        self.assertNotIn('sửa đôi', toan)

    def test_mot_cau_hieu_luc(self):
        vb = ndg.phan_tich_van_ban([['Số: 9/2026/QĐ-UBND'], ['QUYẾT ĐỊNH:'], ['Điều 1. Sửa đổi khoản 2 Điều 5 Quyết định số 42/2025/QĐ-UBND.'],
                                    ['Điều 2. Quyết định này có hiệu lực từ ngày 01/01/2026 và thay thế Quyết định số 7/2025/QĐ-UBND.']])
        self.assertEqual(vb['thay_the_vb'], ['7/2025/QĐ-UBND'])
        self.assertEqual(len(vb['can_xem']), 2)


class TestDieuKhoan(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ds, cls.xem, cls.bieu = ndg.muc_chinh_sach_tu_dieu_khoan(_dong())

    def _theo(self, can_cu):
        return [m for m in self.ds if m.can_cu.lower().endswith(can_cu.lower())]

    def test_khong_lay_vi_du(self):
        gia = {m.don_gia for m in self.ds}
        for g in (190000000, 95000000, 19000000, 114000000, 1900000):
            self.assertNotIn(g, gia)
        self.assertEqual(ndg.nhan_muc(_dong(), 4), [])                  # lời văn trong Điều không qua bộ đọc bảng
        ds, _ = ndg.muc_tu_loi_van(_dong(), 2)
        self.assertFalse({m.don_gia for m in ds} & {190000000, 95000000, 19000000, 114000000, 1900000})

    def test_vi_du_het_o_khoan_moi(self):
        d = [['1. Mức 1.'], ['Ví dụ: nhà 1.900.000 đồng/m²'], ['- Giá trị 190.000.000 đồng/m²'], ['2. Đối với đất là 5.000 đồng/m².']]
        self.assertEqual(ndg.bo_vi_du(d), [['1. Mức 1.'], ['2. Đối với đất là 5.000 đồng/m².']])

    def test_bieu_thuong(self):
        self.assertEqual(self.bieu, [(0, 2000000), (20000000, 4000000), (50000000, 8000000), (100000000, 12000000), (200000000, 16000000),
                                     (500000000, 20000000)])
        self.assertEqual(ndg.so_bieu_thuong(self.bieu), '')             # trùng bộ đơn giá
        self.assertIn('20.000.000', ndg.so_bieu_thuong(self.bieu[:1] + [(20000000, 5000000)] + self.bieu[2:]))
        self.assertFalse(any(m.don_gia in (2000000, 4000000, 12000000, 16000000) and not m.dvt for m in self.ds))

    def test_dieu_6_cong_thuc(self):
        a, b = self._theo('khoản 1 Điều 6') + self._theo('khoản 2 Điều 6')
        self.assertEqual((a.don_gia, a.dvt, b.don_gia, b.dvt), (15000, 'm²', 30000, 'm²'))
        self.assertIn('P = (30.000 / T1) x T2', b.ghi_chu)
        self.assertEqual(len(self._theo('khoản 2 Điều 6')), 1)          # công thức nhắc lại số tiền: không thêm dòng
        self.assertIn('Chi phí đầu tư vào đất', a.ten)

    def test_dieu_8_va_12_khong_trung_ten(self):
        d8 = self._theo('khoản 1 Điều 8')
        d12 = self._theo('khoản 2 Điều 12')
        self.assertEqual([(m.don_gia, m.dvt) for m in d8], [(10000000, 'hộ'), (15000000, 'hộ'), (20000000, 'hộ')])
        self.assertEqual([(m.don_gia, m.dvt) for m in d12], [(6000000, 'hộ'), (8000000, 'hộ'), (10000000, 'hộ')])
        self.assertFalse({m.ten for m in d8} & {m.ten for m in d12})
        self.assertTrue(d12[0].ten.startswith('Hỗ trợ để tháo dỡ, phá dỡ, di dời - Di chuyển trong'), d12[0].ten)
        self.assertEqual(d8[0].can_cu, 'Điểm a khoản 1 Điều 8')

    def test_vat_nuoi_mo_ma(self):
        m = self._theo('khoản 1 Điều 12')[0]
        self.assertEqual((m.don_gia, m.dvt, m.can_cu), (1000000, 'đơn vị vật nuôi', 'Điểm d khoản 1 Điều 12'))
        self.assertIn('500 kg', m.ghi_chu)
        m = self._theo('khoản 1 Điều 9')[0]
        self.assertEqual((m.don_gia, m.dvt), (10000000, 'mộ'))

    def test_he_so_dao_tao(self):
        self.assertEqual([(m.he_so, m.can_cu) for m in self.ds if m.he_so], [('1.5', 'Khoản 1 Điều 13'), ('0.5', 'Khoản 2 Điều 13')])

    def test_ma_tran_xa_phuong(self):
        for dieu in ('Điều 14', 'Điều 17'):
            ds = [m for m in self.ds if m.can_cu.endswith(dieu)]
            self.assertEqual([(m.don_gia, m.dvt) for m in ds], [(6000000, 'hộ/tháng'), (8000000, 'hộ/tháng'),
                                                                (1500000, 'nhân khẩu/tháng'), (2000000, 'nhân khẩu/tháng')], dieu)
            self.assertIn('địa bàn phường', ds[1].ten)
            self.assertIn('thứ 5', ds[2].ten)

    def test_cao_do_chinh_sach(self):
        self.assertEqual([(m.don_gia, m.dvt) for m in self._theo('khoản 3 Điều 19')], [(2000000, 'md'), (2500000, 'md'), (3500000, 'md')])
        self.assertEqual(self._theo('khoản 3 Điều 19')[2].can_cu, 'Điểm c khoản 3 Điều 19')        # OCR "e)" sau "b)"
        self.assertTrue(self._theo('khoản 3 Điều 19')[0].ten.startswith('Hỗ trợ tiền cải tạo'), self._theo('khoản 3 Điều 19')[0].ten)
        self.assertEqual([(m.don_gia, m.dvt) for m in self._theo('khoản 4 Điều 19')],
                         [(30000000, 'hộ'), (15000000, 'hộ'), (10000000, 'hộ'), (10000000, 'hộ')])

    def test_on_dinh_doi_song_khong_tao_dong(self):
        self.assertFalse(self._theo('Điều 10'))
        self.assertTrue(any('30 kg gạo' in x for x in self.xem))

    def test_khong_doc_dieu_chuyen_tiep(self):
        self.assertNotIn(50000, {m.don_gia for m in self.ds})           # Điều 20 "Quy định chuyển tiếp"


class TestKhopMaCS(unittest.TestCase):
    def _khop(self, thay_the=False, scan=True):
        ds = ndg.muc_chinh_sach_tu_dieu_khoan(_dong())[0]
        ndg.so_khop(ds, None, thay_the=thay_the, scan=scan)
        return ds

    def test_khop_ma(self):
        ds = self._khop()
        ma = {}
        for m in ds:
            ma.setdefault(m.can_cu.split(' Điều ')[-1], []).append(m.ma_khop)
        self.assertEqual(ma['8'], ['CS14', 'CS15', 'CS16'])
        self.assertEqual(ma['9'], ['CS29'])
        self.assertEqual(ma['12'], ['CS8', 'CS37', 'CS38', 'CS39'])
        self.assertEqual(ma['13'], ['CS9', 'CS10'])
        self.assertEqual(ma['14'], ['CS17', 'CS18', 'CS21', 'CS22'])
        self.assertEqual(ma['15'], ['CS23', 'CS24', 'CS25', 'CS26'])
        self.assertEqual(ma['17'], ['CS17', 'CS18', 'CS21', 'CS22'])    # cùng mức Điều 14: dùng lại mã, không sinh mã mới
        self.assertEqual(ma['19'][3:], ['CS19', 'CS27', 'CS28', 'CS28'])
        # chỉ các mức bộ đơn giá thật sự chưa có mới là mục mới: chi phí đầu tư vào đất (Điều 6), cao độ mặt đường (khoản 3 Điều 19)
        moi = [m for m in ds if m.trang_thai == 'mới']
        self.assertEqual([m.don_gia for m in moi], [15000, 30000, 2000000, 2500000, 3500000])
        self.assertTrue(all(m.trang_thai == 'giữ nguyên' for m in ds if m.ma_khop))

    def test_khong_bao_bo_nham(self):
        ds = self._khop(thay_the=True)
        self.assertFalse([m for m in ds if m.trang_thai == 'bỏ'])
        giu = {m.ma_khop for m in ds if m.bo_cu}
        from pabt.nghiep_vu import MA_ON_DINH, MA_TDC
        self.assertTrue(set(MA_ON_DINH) <= giu and set(MA_TDC) <= giu)
        self.assertTrue(all(m.trang_thai == 'giữ nguyên' and not m.chon for m in ds if m.bo_cu))
        ma = {m.ma_khop for m in ds if m.ma_khop}
        self.assertEqual({f'CS{i}' for i in range(1, 40)} - ma, set())  # đủ 39 mục, mỗi mục một trạng thái
        self.assertFalse([m for m in ds if m.ma_moi and m.ma_khop])

    def test_doi_gia_that_van_bao(self):
        ds = ndg.muc_chinh_sach_tu_dieu_khoan(_dong())[0]
        a = next(m for m in ds if m.can_cu == 'Điểm a khoản 1 Điều 8')
        b = next(m for m in ds if m.he_so == '1.5')
        a.don_gia, b.he_so = 12000000, '2'
        ndg.so_khop(ds, None, scan=False)
        self.assertEqual((a.ma_khop, a.trang_thai, a.gia_cu), ('CS14', 'cập nhật', 10000000))
        self.assertEqual((b.ma_khop, b.trang_thai, b.he_so_cu), ('CS9', 'cập nhật', '1.5'))

    def test_muc_co_gia_khong_con_van_bao_bo(self):
        ds = [m for m in ndg.muc_chinh_sach_tu_dieu_khoan(_dong())[0] if not m.can_cu.endswith('khoản 1 Điều 8')]
        ndg.so_khop(ds, None, thay_the=True, scan=False)
        self.assertEqual({m.ma_khop for m in ds if m.trang_thai == 'bỏ'}, {'CS14', 'CS15', 'CS16'})


class TestQuyDinh(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.qd = qvb.trich_quy_dinh(_dong(), 4, [])

    def test_sach(self):
        for q in self.qd:
            self.assertFalse(q['chu'].startswith(('151/2025', 'Nghị định số 151', 'Luật sô', 'Luật số4')), q['chu'])
            self.assertNotIn('190.000.000', q['chu'])
            self.assertNotIn('Ví dụ', q['chu'])
            self.assertNotIn('được sửa đôi, bô sung bởi', q['chu'])
            self.assertTrue(q['dieu'].startswith('Điều '), q['chu'])
            self.assertNotIn(q['dieu'].split()[1], ('1', '20', '22'), q['chu'])

    def test_vi_tri(self):
        dieu = {q['dieu'] for q in self.qd}
        for x in ('Điều 4 khoản 1', 'Điều 6 khoản 2', 'Điều 10 khoản 1', 'Điều 19 khoản 3 điểm c'):
            self.assertIn(x, dieu)

    def test_tieu_de_dai_khong_thanh_cau(self):
        self.assertFalse([q for q in self.qd if q['chu'].startswith(('Khoản tiền tính bằng tỷ lệ phần trăm theo giá trị hiện có của nhà, công trình xây '
                                                                     'dựng quy định tại'))])

    def test_tach_cau(self):
        self.assertEqual(qvb.tach_cau('Theo NĐ. CP đã nêu. Mức 6.000.000. đồng/hộ; Khoản 2. Điều 5 áp dụng.'),
                         ['Theo NĐ. CP đã nêu.', 'Mức 6.000.000. đồng/hộ;', 'Khoản 2. Điều 5 áp dụng.'])

    def test_sua_chu_ocr(self):
        self.assertEqual(ndg.sua_chu_ocr('Chỉ phí di chuyên, hô trợ đên đât'), 'Chi phí di chuyển, hỗ trợ đến đất')


class TestHopNhap(unittest.TestCase):
    def test_hop_thoai(self):
        from PySide6.QtCore import Qt

        from pabt.man_hinh_nhap_don_gia import C_DUNG, C_GIA, C_GIA_CU, HopNhapDonGia
        d = HopNhapDonGia(TEN_FILE, None, dong=_dong(), nhom_uu_tien=4, thay_the=True)
        d.im_lang = True
        self.addCleanup(d.deleteLater)
        self.assertTrue(d.chinh_sach and d.tu_loi_van)
        self.assertFalse(d.thay_the())                                  # văn bản chính sách: mặc định đối chiếu, không thay cả nhóm
        self.assertEqual(d.van_ban['so_hieu'], '42/2025/QĐ-UBND')
        self.assertEqual(sum(m.trang_thai == 'bỏ' for m in d.ds), 0)
        self.assertEqual(d.lb_canh_thay.text(), '')
        i = next(i for i, m in enumerate(d.ds) if m.he_so == '1.5')
        self.assertEqual((d.bang.item(i, C_GIA).text(), d.bang.item(i, C_GIA_CU).text()), ('1,5', '1,5'))
        self.assertEqual(d.bang.item(i, C_DUNG).checkState(), Qt.CheckState.Unchecked)
        d.bang.item(i, C_GIA).setText('2')                              # sửa hệ số trên bảng
        self.assertEqual((d.ds[i].he_so, d.ds[i].trang_thai), ('2', 'cập nhật'))
        d.reject()


if __name__ == '__main__':
    unittest.main()

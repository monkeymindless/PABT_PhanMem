"""Quy định cách tính trong văn bản đơn giá (1.0.56 - người dùng 03/11/2026: "phân tích toàn bộ nội dung văn bản, trích xuất, chắt lọc
các quy định khác đưa vào ghi chú quy định cách tính, để khi nhập liệu có dữ liệu ghi chú để theo dõi, tính toán cho chính xác"). Không Qt.

- trich_quy_dinh: đọc LỜI VĂN các điều khoản (không chỉ bảng giá) -> câu quy định cách tính bồi thường, hỗ trợ (mật độ, tỷ lệ %, trường hợp
  không bồi thường, cây trồng xen, ngoài mật độ, năm tuổi, đường kính, số lượng chậu, giá trị còn lại, chi phí di chuyển…) kèm Điều /
  khoản, nhóm (nhà / cây / vật nuôi / hỗ trợ) và phạm vi ("Đối với <…>"). Gộp với dòng quy tắc trong bảng (nhan_muc).
- van_ban_chua_gom: văn bản ĐÃ CÓ trong bộ đơn giá - file đang nhập có gồm đủ các văn bản sửa đổi của nhóm đang dùng không (bản hợp
  nhất "QĐ 48 được sửa đổi bởi QĐ 66"): gồm đủ thì dòng đổi giá chọn sẵn được (không ghi đè giá mới bằng giá cũ).
- ghi_quy_dinh: lưu vào bảng tham_so của bộ đơn giá (mã QDCT:<nhóm>:<số hiệu>:<stt> - bảng thuộc danh mục, được chép vào dự án khi áp bộ
  đơn giá) + ghi chú các mục có tên khớp phạm vi của quy định; quy_dinh_lien_quan: quy định cho một mục khi lập phương án (giải trình)."""
from __future__ import annotations

import re

from .lap_pa import bo_dau

TIEN_TO = 'QDCT:'
TEN_NHOM = {0: 'Chung', 2: 'Nhà, công trình, vật kiến trúc', 3: 'Cây trồng', 7: 'Vật nuôi, thủy sản', 4: 'Chính sách hỗ trợ'}
TOI_DA = 300                     # quy định mỗi văn bản
DAI_TOI_DA = 500                 # ký tự mỗi câu (dài hơn: cắt, giữ đủ ở văn bản gốc)
MUC_GHI_CHU_TOI_DA = 400         # quy định theo phạm vi chỉ ghi vào ghi chú mục khi khớp <= chừng này mục (phạm vi quá chung thì bỏ)

# từ khóa câu quy định (chữ bỏ dấu); câu phải có số / % hoặc một cụm "mạnh"
_RE_KHOA = re.compile(r'mat do|ty le|\d\s*%|phan tram|khong (?:duoc )?(?:boi thuong|ho tro|tinh)|chi (?:duoc )?(?:boi thuong|ho tro|tinh)|'
                      r'(?:boi thuong|ho tro|tinh|xac dinh|ap dung) (?:bang|theo|nhu)|duoc tinh|tinh them|toi da|khong (?:duoc )?vuot qua|'
                      r'trong xen|ngoai mat do|trong chau|\bchau\b|duong kinh|chu vi|nam tuoi|nam thu|thoi gian (?:nuoi|trong)|'
                      r'chua (?:thu hoach|cho thu hoach)|da thu hoach|gia tri con lai|chi phi (?:di chuyen|thao do|thao do|lap dat|van chuyen)|'
                      r'he so|nhan (?:voi|them)|giam tru|tru (?:di|lui)|cong them|muc (?:boi thuong|ho tro)|don gia (?:tinh|ap dung)|'
                      r'truong hop|dien tich (?:xay dung|san)|so luong')
_RE_MANH = re.compile(r'khong (?:duoc )?(?:boi thuong|ho tro|tinh)|chi (?:duoc )?(?:boi thuong|ho tro)|trong xen|ngoai mat do|'
                      r'gia tri con lai|chua thu hoach|di chuyen|thao do')
_RE_BO_CAU = re.compile(r'^(?:can cu|theo de nghi|xet de nghi|quyet dinh:|quyet nghi:|noi nhan|tm\.|kt\.|chu tich|pho chu tich|'
                        r'giam doc|chanh van phong|uy ban nhan dan)|co hieu luc|hieu luc (?:thi hanh|ke tu)|chiu trach nhiem thi hanh|'
                        r'(?:ban hanh kem theo|kem theo) quyet dinh|to chuc thuc hien|bai bo (?:khoan|dieu|quyet dinh)')
_RE_DIEU_BO = re.compile(r'hieu luc|to chuc thuc hien|trach nhiem|dieu khoan thi hanh|pham vi dieu chinh|doi tuong ap dung|'
                         r'xu ly chuyen tiep|thi hanh')
_RE_DIEU = re.compile(r'^(?:Điều|ĐIỀU|Dieu)\s+(\d+[a-zđ]?)\s*[.:]?\s*(.*)$')
# không tách câu sau chữ viết tắt ("NĐ. CP", "TP. Biên Hòa", "khoản 2. Điều") - bản OCR hay chèn dấu chấm
_RE_VIET_TAT = re.compile(r'(?:\b(?:NĐ|QĐ|TT|NQ|TP|Tp|UBND|HĐND)|\b(?i:khu\s+vực|điều|khoản)(?:\s+\d+)?)\.?$')
_RE_MANH_SO_HIEU = re.compile(r'^\W*(?:\d{1,4}/\d{4}/\S+|(?:Luật|Nghị\s+định)\s+s[ốô]\s*\d+/\d{4}/\S+)(?:[\s,;:]+(?:và\s+)?(?:(?:Luật|Nghị\s+định)\s+)?(?:s[ốô]\s*)?\d+/\d{4}/\S+)*\W*$')
_RE_KHOAN = re.compile(r'^(\d+)\.\s+(?=\S)')
_RE_DIEM = re.compile(r'^([a-zđ])\)\s+')
_RE_PHAM_VI = re.compile(r'(?i)\b(?:đối\s+với|áp\s+dụng\s+(?:cho|đối\s+với)|riêng)\s+(.{3,90}?)(?=\s*[:;,]|\s+(?:thì|được|là|có|bằng|'
                         r'tính|theo|khi|nếu|mà|phải|chỉ)\b)')
_PHAM_VI_CHUNG = {'cay trong', 'cay', 'tai san', 'nha', 'cong trinh', 'vat nuoi', 'truong hop', 'cac truong hop', 'nha o',
                  'nha, cong trinh', 'cay trong, vat nuoi', 'hoa mau', 'cay lau nam', 'cay hang nam', 'thuy san', 'ho gia dinh, ca nhan',
                  'to chuc', 'nguoi', 'dat', 'cac loai'}


def _gon(x: str) -> str:
    return ' '.join(str(x or '').split())


def pham_vi(chu: str) -> str:
    """'Đối với cây cảnh trồng chậu: …' -> 'cây cảnh trồng chậu' (rỗng nếu không có)."""
    m = _RE_PHAM_VI.search(chu or '')
    return _gon(m.group(1)).strip(' ,.') if m else ''


_RE_RAC_DAU = re.compile(r'^(?:[\W_ˆ˜]+|\d+(?:\.\d+)*\.?[\W_ˆ˜]*\s+)(?=[A-ZĐÀ-Ỹa-zđà-ỹ(-])')
_RE_RAC_CUOI = re.compile(r'(?<=[.;:])\s*\d{1,2}\.$')


def sach_cau(chu: str) -> str:
    """Bỏ rác OCR / số khoản đầu câu ("2.ˆ Số lượng…", "5.5 Phương pháp…") và số khoản dính cuối câu ("…đo đếm.6.")."""
    chu = _gon(chu)
    chu = _RE_RAC_CUOI.sub('', _RE_RAC_DAU.sub('', chu))
    return chu.strip()


def tach_cau(chu: str) -> list:
    """Tách câu ở dấu . ; trước chữ hoa, trừ sau chữ viết tắt (NĐ, QĐ, TT, NQ, TP, UBND, HĐND, khu vực, Điều, khoản)."""
    kq, tu = [], 0
    for m in re.finditer(r'(?<=[.;])\s+(?=\S)', chu):
        if chu[m.end()].isupper() and not _RE_VIET_TAT.search(chu[tu:m.start()]):
            kq.append(chu[tu:m.start()])
            tu = m.end()
    kq.append(chu[tu:])
    return kq


def la_cau_quy_dinh(chu: str) -> bool:
    k = bo_dau(sach_cau(chu))
    if len(k) < 20 or _RE_BO_CAU.search(k):
        return False
    if k.endswith(':') and len(k) < 100:                # tiêu đề mục ("Phương pháp đo đường kính thân cây lâm nghiệp:")
        return False
    if not _RE_KHOA.search(k):
        return False
    return bool(re.search(r'\d', k)) or bool(_RE_MANH.search(k))


def trich_quy_dinh(dong: list, nhom_vb: int = 0, quy_tac: list | None = None) -> list:
    """[dict(chu, nhom, dieu, pham_vi, nguon)] - quy định cách tính trong văn bản: dòng quy tắc của bảng (quy_tac, nguon 'bảng') + câu
    trong lời văn các điều khoản (nguon 'điều khoản'). Bỏ phần căn cứ, hiệu lực, tổ chức thực hiện, chữ ký. Không trùng lặp."""
    from .nhap_don_gia import (_RE_DIEU_HANH_CHINH, DongScan, _khoan_van, bo_dan_chieu, bo_vi_du, cac_khoan_dieu, dong_loi_van, nhom_theo_chu,
                               sua_chu_ocr, ten_dieu_gon, van_theo_dieu)
    scan = isinstance(dong, DongScan)
    kq, da = [], set()

    def them(chu, dieu, nguon):
        chu = sach_cau(chu)
        k = re.sub(r'[^a-z0-9%]+', '', bo_dau(chu))
        if not chu or k in da or len(kq) >= TOI_DA:
            return
        if any(k in x or x in k for x in da if len(x) > 40 and len(k) > 40):
            return                                          # cùng câu (bảng và lời văn), câu này nằm trong câu đã có
        if sum(1 for x in da if len(x) >= 15 and x in k) >= 2:
            return                                          # đoạn lời văn chứa lại >= 2 dòng quy tắc đã lấy từ bảng (bản scan ghép dòng)
        da.add(k)
        nhom = nhom_theo_chu(chu) or nhom_vb or 0
        kq.append(dict(chu=chu if len(chu) <= DAI_TOI_DA else chu[:DAI_TOI_DA - 1] + '…', nhom=nhom, dieu=dieu,
                       pham_vi=pham_vi(chu) or (chu.split(':', 1)[0] if ':' in chu[:80] and nguon == 'bảng' else ''), nguon=nguon))
    for x in quy_tac or ():
        if not str(x).startswith('KHÔNG ĐỌC ĐƯỢC'):
            them(x, '', 'bảng')
    # lời văn theo Điều (1.0.60: nhận trọn tiêu đề Điều nhiều dòng, câu chỉ lấy từ thân Điều); bỏ Điều hiệu lực / tổ chức thực hiện, đoạn "Ví dụ"
    van = bo_vi_du(dong_loi_van(dong))
    cac_dieu = van_theo_dieu(van)
    for d in cac_dieu:
        ten = ten_dieu_gon(bo_dan_chieu(d['ten']))
        if _RE_DIEU_BO.search(bo_dau(ten)) or _RE_DIEU_HANH_CHINH.search(bo_dau(ten)):
            continue
        dieu = f'Điều {d["so"]}'
        # "Điều 5. Đối với cây … thì …" (tiêu đề là luôn nội dung)
        if len(d['ten']) > 60 and re.search(r'\bthì\b', d['ten']) and la_cau_quy_dinh(d['ten']):
            them(d['ten'], dieu, 'điều khoản')
        for khoan, diem, than, goc, _dan in cac_khoan_dieu(d):
            vi_tri = ' '.join(x for x in (dieu, f'khoản {khoan}' if khoan else '', f'điểm {diem}' if diem else '') if x)
            for cau in tach_cau(re.sub(r'^\s*[a-zđ]\)\s*', '', bo_dan_chieu(goc))):
                if _RE_MANH_SO_HIEU.match(cau):
                    continue
                if la_cau_quy_dinh(cau):
                    them(sua_chu_ocr(cau) if scan else cau, vi_tri, 'điều khoản')
    if not cac_dieu:                                    # văn bản không có Điều (bảng dán, trích đoạn): xét mọi đoạn
        for c in _khoan_van(van):
            if la_cau_quy_dinh(c):
                them(c, '', 'điều khoản')
    return kq


# ---------------------------------------------------------------- văn bản đã có: file đang nhập có gồm đủ văn bản sửa đổi không
def so_hieu_trong(chu: str) -> set:
    """Mọi số hiệu văn bản nhắc trong chữ (chuẩn hóa như nhap_don_gia.chuan_so_hieu)."""
    from .nhap_don_gia import _RE_SO_TRONG, chuan_so_hieu
    return {chuan_so_hieu(m.group(1)) for m in _RE_SO_TRONG.finditer(chu or '')} - {''}


def van_ban_chua_gom(dong: list, van_ban: dict, nhom_ds: set, ds_van_ban: list | None = None) -> list:
    """Văn bản ĐÃ CÓ trong bộ đơn giá: [số hiệu dòng văn bản căn cứ CỦA NHÓM mà file đang nhập không nhắc đủ] (phần đầu file: số hiệu,
    trích yếu, "được sửa đổi, bổ sung bởi …"). [] = file gồm đủ (cùng văn bản / bản hợp nhất có văn bản sửa đổi) - giá trong file không cũ
    hơn bộ đơn giá. ds_van_ban: [(so_hieu, noi_dung, trang_thai)] (kiểm thử); None = đọc bộ đơn giá đang dùng."""
    from .nhap_don_gia import _TU_NHOM_VB
    dau = ' '.join(' '.join(str(c) for c in (r if not isinstance(r, str) else [r]) if c) for r in dong[:80])
    nhac = so_hieu_trong(' '.join((dau, van_ban.get('so_hieu', '') or '', van_ban.get('trich_yeu', '') or '')))
    if ds_van_ban is None:
        from . import csdl, don_gia
        con = csdl.mo(don_gia.file_dang_dung(), chi_doc=True)
        try:
            ds_van_ban = [tuple(r) for r in con.execute('SELECT so_hieu, noi_dung, trang_thai FROM van_ban')]
        finally:
            con.close()
    mau = '|'.join(_TU_NHOM_VB[n] for n in sorted(nhom_ds) if n in _TU_NHOM_VB)
    kq = []
    for sh, nd, tt in ds_van_ban:
        if re.search(r'du thao|het hieu luc', bo_dau(f'{nd} {tt}')):
            continue
        if mau and not re.search(mau, bo_dau(f'{sh} {nd}')):
            continue
        cua = so_hieu_trong(sh)
        if cua and not cua <= nhac:
            kq.append(sh)
    return kq


# ---------------------------------------------------------------- lưu / đọc quy định trong bộ đơn giá, dự án
def ghi_quy_dinh(con, van_ban: dict, ds: list, nguon: str = '') -> dict:
    """Ghi quy định vào tham_so (trong giao dịch + mo_khoa_danh_muc của nơi gọi): thay quy định cũ của cùng văn bản; mục dm_taisan
    có tên khớp phạm vi quy định (cụ thể, <= MUC_GHI_CHU_TOI_DA mục) được thêm vào ghi chú "Quy định (<số hiệu>): …". Trả số dòng."""
    from .nhap_don_gia import chuan_so_hieu
    sh = (van_ban or {}).get('so_hieu') or nguon or 'van_ban'
    k = re.sub(r'[^A-Z0-9/-]+', '', chuan_so_hieu(sh))[:40] or 'VB'
    con.execute('DELETE FROM tham_so WHERE ma LIKE ?', (f'{TIEN_TO}%:{k}:%',))
    so_muc = 0
    muc = [(r[0], r[1], bo_dau(r[2]), r[3] or '') for r in con.execute('SELECT ma, nhom, ten, ghi_chu FROM dm_taisan')]
    ghi = {}
    for i, q in enumerate(ds, start=1):
        noi = ', '.join(x for x in (sh, q.get('dieu', '')) if x)
        con.execute('INSERT OR REPLACE INTO tham_so (ma, ten, gia_tri, dvt, can_cu, trang_thai) VALUES (?,?,?,?,?,?)',
                    (f'{TIEN_TO}{q.get("nhom", 0)}:{k}:{i:03d}', TEN_NHOM.get(q.get('nhom', 0), 'Chung'), q['chu'], '',
                     noi, 'Quy định cách tính'))
        pv = bo_dau(q.get('pham_vi', '')).strip()
        pv = re.sub(r'^(?:cac |loai |doi voi )+', '', pv)
        if len(pv.split()) < 2 or pv in _PHAM_VI_CHUNG:
            continue
        khop = [m for m in muc if pv in m[2] and (not q.get('nhom') or q['nhom'] in (m[1], 7 if m[1] == 3 else -1))]
        if not 0 < len(khop) <= MUC_GHI_CHU_TOI_DA:
            continue
        for ma, _n, _t, gc in khop:
            them = f'Quy định ({sh}): {q["chu"][:240]}'
            cu = ghi.get(ma, gc)
            if them[:60] not in cu:
                ghi[ma] = '; '.join(x for x in (cu, them) if x)
    for ma, gc in ghi.items():
        con.execute('UPDATE dm_taisan SET ghi_chu = ? WHERE ma = ?', (gc, ma))
        so_muc += 1
    return dict(so_quy_dinh=len(ds), so_muc_ghi_chu=so_muc)


def doc_quy_dinh(ts: dict) -> list:
    """[(nhóm, chữ)] từ tham_so ({ma: gia_tri} - BoiCanh.ts)."""
    kq = []
    for ma, gt in ts.items():
        if str(ma).startswith(TIEN_TO) and gt:
            try:
                kq.append((int(str(ma)[len(TIEN_TO):].split(':', 1)[0]), str(gt)))
            except ValueError:
                pass
    return kq


_TU_BO = frozenset('cay va cac loai co cua theo tren duoi duoc doi voi tinh boi thuong ho tro don gia muc so luong la thi khi nam '
                   'm2 m ha dong / ( ) - , . trong'.split())


def quy_dinh_lien_quan(ts: dict, nhom: int, ten: str, toi_da: int = 5) -> list:
    """Quy định của nhóm (và quy định chung) có từ trùng với tên mục, nhiều từ trùng trước (giải trình dòng phương án)."""
    tu = {t for t in re.findall(r'[a-z0-9]+', bo_dau(ten)) if t not in _TU_BO and len(t) > 1}
    if not tu:
        return []
    diem = []
    for n, chu in doc_quy_dinh(ts):
        if n not in (0, nhom):
            continue
        k = set(re.findall(r'[a-z0-9]+', bo_dau(chu)))
        d = len(tu & k)
        if d:
            diem.append((-d, chu))
    return [c for _d, c in sorted(diem)[:toi_da]]

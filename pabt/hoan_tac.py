"""Hoàn tác (Ctrl+Z) / làm lại (Ctrl+Y) các thao tác đã ghi vào file dự án - dùng chung cho mọi cửa sổ.

Cách làm (theo "Automatic Undo/Redo Using SQLite Triggers" của sqlite.org): mỗi bảng dữ liệu của dự án có trigger TẠM (TEMP, chỉ
sống trong phiên làm việc, không ghi vào file .pabt) ghi lệnh SQL đảo ngược của mỗi dòng bị thêm / sửa / xóa vào bảng tạm
_ht_nhat_ky. Một BƯỚC hoàn tác = mọi thay đổi trong một thao tác của người dùng: các lệnh COMMIT được theo dõi bằng
set_trace_callback, bước được chốt khi phần mềm rảnh trở lại (QTimer 0 ms) - nên một nút bấm ghi nhiều lần vẫn là một bước.
Tên bước lấy từ csdl.ghi_nhat_ky (mọi thao tác ghi đều gọi).

Hoàn tác: chạy các lệnh đảo ngược của bước (thứ tự ngược), trong lúc đó trigger ghi lại lệnh đảo ngược của chính chúng thành
bước "làm lại". Thao tác mới xóa danh sách làm lại. Giữ tối đa SO_BUOC bước gần nhất.
"""
from __future__ import annotations
import sqlite3
from dataclasses import dataclass

from . import csdl

SO_BUOC = 50
BO_QUA = ('nhat_ky', 'khoa_dm', 'sqlite_sequence')        # không hoàn tác nhật ký; cờ khóa danh mục do mo_khoa_danh_muc lo
_DANG_KY = csdl.HOAN_TAC                                   # id(con) -> HoanTac (để csdl.ghi_nhat_ky báo tên bước)


@dataclass
class Buoc:
    viec: str
    tu: int
    den: int


class HoanTac:
    def __init__(self, con, hen=None):
        """hen(ham): hẹn gọi ham khi phần mềm rảnh (giao diện: QTimer.singleShot(0, ham)); None = gọi chot() bằng tay."""
        self.con = con
        self.hen = hen
        self.hoan_tac_ds: list = []
        self.lam_lai_ds: list = []
        self._ten = ''
        self._cho_chot = False
        self._dang_chay = False
        self.khi_doi = []                                  # hàm gọi lại khi danh sách bước đổi (cập nhật nút ↶ ↷)
        self._tao_trigger()
        self._moc = self._max()
        _DANG_KY[id(con)] = self
        con.set_trace_callback(self._theo_doi)

    # ---------------------------------------------------------------- trigger
    def _tao_trigger(self):
        c = self.con
        c.execute('CREATE TEMP TABLE IF NOT EXISTS _ht_nhat_ky (seq INTEGER PRIMARY KEY, lenh TEXT NOT NULL)')
        c.execute('CREATE TEMP TABLE IF NOT EXISTS _ht_bat (id INTEGER PRIMARY KEY CHECK (id = 1), bat INTEGER NOT NULL)')
        c.execute('INSERT OR IGNORE INTO temp._ht_bat (id, bat) VALUES (1, 1)')
        bang = [r[0] for r in c.execute("SELECT name FROM main.sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'")
                if r[0] not in BO_QUA]
        dk = 'WHEN (SELECT bat FROM temp._ht_bat WHERE id = 1) = 1'
        for b in bang:
            cot = [r[1] for r in c.execute(f'PRAGMA main.table_info("{b}")')]
            if not cot:
                continue
            ds_cot = ', '.join(f'"{x}"' for x in cot)
            gia_tri = " || ',' || ".join(f'quote(old."{x}")' for x in cot)
            dat = " || ', ' || ".join(f"'\"{x}\" = ' || quote(old.\"{x}\")" for x in cot)
            c.execute(f'''CREATE TEMP TRIGGER IF NOT EXISTS _ht_{b}_them AFTER INSERT ON main."{b}" {dk} BEGIN
                          INSERT INTO _ht_nhat_ky (lenh) VALUES ('DELETE FROM main."{b}" WHERE rowid = ' || new.rowid); END''')
            c.execute(f'''CREATE TEMP TRIGGER IF NOT EXISTS _ht_{b}_sua AFTER UPDATE ON main."{b}" {dk} BEGIN
                          INSERT INTO _ht_nhat_ky (lenh) VALUES ('UPDATE main."{b}" SET ' || {dat} ||
                          ' WHERE rowid = ' || old.rowid); END''')
            c.execute(f'''CREATE TEMP TRIGGER IF NOT EXISTS _ht_{b}_xoa BEFORE DELETE ON main."{b}" {dk} BEGIN
                          INSERT INTO _ht_nhat_ky (lenh) VALUES ('INSERT INTO main."{b}" (rowid, {ds_cot.replace("'", "''")}) VALUES ('
                          || old.rowid || ',' || {gia_tri} || ')'); END''')
        # INSERT vào temp._ht_bat mở giao dịch ngầm (sqlite3): chốt ngay, không để kết nối "đang giữa giao dịch" suốt phiên
        # (csdl.nho không dùng được bộ nhớ đệm khi đang giữa giao dịch). Gọi trước set_trace_callback: không thành bước hoàn tác.
        c.commit()

    def _max(self) -> int:
        return self.con.execute('SELECT COALESCE(MAX(seq), 0) FROM temp._ht_nhat_ky').fetchone()[0]

    # ---------------------------------------------------------------- chốt bước
    def _theo_doi(self, sql: str):
        """set_trace_callback: không được chạy SQL ở đây - chỉ đánh dấu, hẹn chốt bước khi rảnh."""
        if self._dang_chay or self._cho_chot:
            return
        if sql.lstrip()[:6].upper() == 'COMMIT' or sql.lstrip()[:3].upper() == 'END':
            self._cho_chot = True
            if self.hen is not None:
                self.hen(self.chot)

    def dat_ten(self, viec: str):
        """csdl.ghi_nhat_ky báo tên thao tác (bước đang mở)."""
        if not self._dang_chay and viec:
            self._ten = viec if not self._ten else self._ten

    def chot(self) -> Buoc | None:
        """Chốt các thay đổi từ mốc trước thành một bước hoàn tác (gọi khi rảnh, trước khi hoàn tác / làm lại)."""
        self._cho_chot = False
        if self._dang_chay:
            return None
        try:
            den = self._max()
        except sqlite3.ProgrammingError:                # dự án đã đóng trước khi tới lượt chốt (hẹn bằng QTimer)
            return None
        if den <= self._moc:
            self._ten = ''
            return None
        b = Buoc(self._ten or 'Sửa dữ liệu', self._moc + 1, den)
        self._moc = den
        self._ten = ''
        self.hoan_tac_ds.append(b)
        self._bo_lam_lai()
        if len(self.hoan_tac_ds) > SO_BUOC:
            cu = self.hoan_tac_ds.pop(0)
            self._xoa(cu)
        self._bao()
        return b

    def _xoa(self, b: Buoc):
        truoc = csdl.trang_thai_nho(self.con)          # chỉ xóa bảng tạm: giữ bộ nhớ đệm số liệu dự án
        self._chay_rieng(lambda: self.con.execute('DELETE FROM temp._ht_nhat_ky WHERE seq BETWEEN ? AND ?', (b.tu, b.den)))
        csdl.giu_tat_ca(self.con, truoc)

    def _bo_lam_lai(self):
        for b in self.lam_lai_ds:
            self._xoa(b)
        self.lam_lai_ds = []

    def _chay_rieng(self, ham):
        cu = self._dang_chay
        self._dang_chay = True
        try:
            ham()
            if self.con.in_transaction:
                self.con.commit()
        finally:
            self._dang_chay = cu

    # ---------------------------------------------------------------- hoàn tác / làm lại
    @property
    def co_hoan_tac(self) -> bool:
        return bool(self.hoan_tac_ds) or self._max() > self._moc

    @property
    def co_lam_lai(self) -> bool:
        return bool(self.lam_lai_ds)

    def ten_hoan_tac(self) -> str:
        self.chot()
        return self.hoan_tac_ds[-1].viec if self.hoan_tac_ds else ''

    def ten_lam_lai(self) -> str:
        return self.lam_lai_ds[-1].viec if self.lam_lai_ds else ''

    def _ap(self, b: Buoc) -> Buoc:
        """Chạy các lệnh đảo ngược của bước b (thứ tự ngược) trong một giao dịch; trigger ghi lại phép đảo của chúng
        thành bước mới (trả về). Khóa ngoại kiểm khi COMMIT (thứ tự dòng cha / con không quan trọng)."""
        con = self.con
        lenh = [r[0] for r in con.execute('SELECT lenh FROM temp._ht_nhat_ky WHERE seq BETWEEN ? AND ? ORDER BY seq DESC',
                                          (b.tu, b.den))]
        self._dang_chay = True
        try:
            if con.in_transaction:
                con.commit()
            tu = self._max() + 1
            con.execute('BEGIN')
            try:
                con.execute('PRAGMA defer_foreign_keys = ON')
                con.execute('UPDATE khoa_dm SET mo = 1 WHERE id = 1')        # bước có sửa danh mục (bộ đơn giá)
                for x in lenh:
                    con.execute(x)
                con.execute('UPDATE khoa_dm SET mo = 0 WHERE id = 1')
                con.execute('DELETE FROM temp._ht_nhat_ky WHERE seq BETWEEN ? AND ?', (b.tu, b.den))
                con.commit()
            except Exception:
                con.rollback()
                raise
            den = self._max()
            self._moc = den
            return Buoc(b.viec, tu, den)
        finally:
            self._dang_chay = False

    def hoan_tac(self) -> str:
        """Hoàn tác bước gần nhất. Trả tên thao tác đã hoàn tác ('' nếu không có gì)."""
        self.chot()
        if not self.hoan_tac_ds:
            return ''
        b = self.hoan_tac_ds.pop()
        self.lam_lai_ds.append(self._ap(b))
        self._ghi(f'Hoàn tác: {b.viec}')
        self._bao()
        return b.viec

    def lam_lai(self) -> str:
        self.chot()
        if not self.lam_lai_ds:
            return ''
        b = self.lam_lai_ds.pop()
        self.hoan_tac_ds.append(self._ap(b))
        self._ghi(f'Làm lại: {b.viec}')
        self._bao()
        return b.viec

    def _ghi(self, viec: str):
        self._chay_rieng(lambda: csdl.ghi_nhat_ky(self.con, viec))

    def _bao(self):
        for ham in list(self.khi_doi):
            try:
                ham()
            except RuntimeError:
                self.khi_doi.remove(ham)

    def dong(self):
        _DANG_KY.pop(id(self.con), None)
        try:
            self.con.set_trace_callback(None)
        except Exception:                                  # kết nối đã đóng
            pass


def cua(con) -> HoanTac | None:
    return _DANG_KY.get(id(con))

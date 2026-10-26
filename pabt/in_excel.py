"""Microsoft Excel qua tự động hóa (cscript + VBS): xuất PDF / in file .xlsx, tắt Excel / Word chạy ngầm bị treo, mở file bằng
chương trình mặc định - tách khỏi in_an.py (1.0.29; in_an nhập lại mọi tên cho mã gọi cũ: in_an.chay_excel, in_an.LoiIn…).
Chỉ thư viện chuẩn (không openpyxl, không Qt). Macro tắt (AutomationSecurity = 3) - BẮT BUỘC giữ."""
from __future__ import annotations

import os
import re
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path


class LoiIn(RuntimeError):
    pass


_VBS = r'''
On Error Resume Next
Dim xl, wb, f, i, ds, che_do, r, h, h0, nm, fso, dung, so, dem, cmin, nm2
Set fso = CreateObject("Scripting.FileSystemObject")
Set f = fso.OpenTextFile(WScript.Arguments(0), 1, False, -1)
dung = ""
If WScript.Arguments.Count > 1 Then dung = WScript.Arguments(1)
che_do = f.ReadLine
ban = 1
If InStr(che_do, ":") > 0 Then
    ban = CInt(Split(che_do, ":")(1))
    che_do = Split(che_do, ":")(0)
End If
Set xl = CreateObject("Excel.Application")
If Err.Number <> 0 Then
    WScript.StdErr.WriteLine "KHONG_CO_EXCEL"
    WScript.Quit 3
End If
xl.Visible = False
xl.DisplayAlerts = False
xl.ScreenUpdating = False
xl.AutomationSecurity = 3
xl.EnableEvents = False
xl.AskToUpdateLinks = False
Err.Clear
so = 0
Do While Not f.AtEndOfStream
    If dung <> "" Then
        If fso.FileExists(dung) Then Exit Do
    End If
    so = so + 1
    ds = Split(f.ReadLine, vbTab)
    Err.Clear
    Set wb = xl.Workbooks.Open(ds(0), 0, True)
    If Err.Number <> 0 Then
        WScript.StdErr.WriteLine "LOI_MO" & vbTab & ds(0) & vbTab & Err.Description
    Else
        Err.Clear
        dem = 4.0
        cmin = 20
        Set nm2 = wb.Names("PABT_DEM_DONG")
        If Err.Number = 0 Then dem = CInt(Mid(nm2.RefersTo, 2)) / 10
        Err.Clear
        Set nm2 = wb.Names("PABT_CAO_MIN")
        If Err.Number = 0 Then cmin = CInt(Mid(nm2.RefersTo, 2)) / 10
        Err.Clear
        Set nm = wb.Names("PABT_TU_GIAN_DONG")
        If Err.Number = 0 Then
            For Each r In nm.RefersToRange.Rows
                h0 = r.RowHeight
                r.AutoFit
                h = r.RowHeight + dem
                If h < h0 Then h = h0
                If h < cmin Then h = cmin
                If h > 409 Then h = 409
                r.RowHeight = h
            Next
        End If
        Err.Clear
        ' 1.0.04: AutoFit làm trang cuối tràn vài dòng / khối chữ ký mồ côi -> Excel tự thêm ngắt trang (không phải ngắt tay của
        ' phần mềm): thu tỷ lệ in từng 2% (tối đa 12%) tới khi hết ngắt tự động; không hết thì trả tỷ lệ cũ
        Set ws1 = wb.Worksheets(1)
        z0 = ws1.PageSetup.Zoom
        zmin = 30
        Set nm3 = wb.Names("PABT_GIU_TI_LE")
        If Err.Number = 0 Then zmin = CInt(Mid(nm3.RefersTo, 2))
        Err.Clear
        If Err.Number = 0 And z0 <> False Then
            For k = 1 To 6
                tu = 0
                For Each pb In ws1.HPageBreaks
                    If pb.Type <> -4135 Then tu = tu + 1
                Next
                If tu = 0 Or ws1.PageSetup.Zoom - 2 < zmin Then Exit For
                ws1.PageSetup.Zoom = ws1.PageSetup.Zoom - 2
            Next
            If tu > 0 Then ws1.PageSetup.Zoom = z0
        End If
        Err.Clear
        xl.Calculate
        If che_do = "in" Then
            wb.Worksheets(1).PrintOut , , ban
        Else
            wb.Worksheets(1).ExportAsFixedFormat 0, ds(1)
        End If
        If Err.Number <> 0 Then WScript.StdErr.WriteLine "LOI_XUAT" & vbTab & ds(0) & vbTab & Err.Description
        wb.Close False
    End If
    WScript.StdOut.WriteLine "XONG" & vbTab & so
Loop
f.Close
xl.Quit
'''


def co_excel() -> bool:
    return sys.platform == 'win32'


CHO_MOI_FILE = 180          # giây: một file không xuất xong trong chừng này (Excel kẹt hộp thoại ẩn / máy in) thì dừng
CHO_KHOI_DONG = 120         # giây cộng thêm cho file đầu (mở Excel lần đầu chậm)


def _doc_luong(luong, ra: list) -> None:
    for dong in iter(luong.readline, b''):
        ra.append(dong.decode('oem' if sys.platform == 'win32' else 'utf-8', 'replace').rstrip('\r\n'))
    luong.close()


def _tat_excel_tu_dong(tu_luc: float, ten_exe: str = 'EXCEL.EXE') -> int:
    """Tắt các EXCEL.EXE (WINWORD.EXE: ten_exe) chạy ngầm do tự động hóa (dòng lệnh -Embedding / /automation) khởi động từ thời
    điểm tu_luc - không đụng tới Excel / Word người dùng đang mở. Trả số tiến trình đã tắt."""
    import datetime as _dt
    if not re.fullmatch(r'[A-Za-z0-9_]+\.EXE', ten_exe, re.I):
        return 0
    lenh = (f"Get-WmiObject Win32_Process -Filter \"Name='{ten_exe}'\" | Where-Object {{ $_.CommandLine -match "
            "'(-Embedding|/automation)' } | ForEach-Object { [string]$_.ProcessId + ' ' + $_.CreationDate }")
    try:
        r = subprocess.run(['powershell', '-NoProfile', '-Command', lenh], capture_output=True, timeout=60,
                           creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    except (OSError, subprocess.TimeoutExpired):
        return 0
    da_tat = 0
    for dong in r.stdout.decode('ascii', 'replace').splitlines():
        m = re.match(r'\s*(\d+)\s+(\d{14})', dong)
        if not m:
            continue
        try:
            luc = _dt.datetime.strptime(m.group(2), '%Y%m%d%H%M%S').timestamp()
        except ValueError:
            continue
        if luc >= tu_luc - 5:
            try:
                os.kill(int(m.group(1)), 9)
                da_tat += 1
            except OSError:
                pass
    return da_tat


def chay_excel(cap_file: list, che_do: str = 'pdf', cho_moi_file: int = CHO_MOI_FILE, bao=None, so_ban: int = 1) -> list:
    """Nhờ Excel xuất PDF (che_do='pdf', cap_file = [(xlsx, pdf)]) hoặc in ra máy in mặc định (che_do='in').
    bao(i, n): gọi liên tục trong lúc chờ (i = số file đã xong) để giao diện không treo; trả True = dừng (Excel làm xong file
    đang dở rồi thoát). Một file quá cho_moi_file giây: dừng, tắt Excel chạy ngầm, báo lỗi. Trả danh sách lỗi (rỗng = thành công)."""
    if not cap_file:
        return []
    if not co_excel():
        raise LoiIn('Xuất PDF / in cần Microsoft Excel trên máy Windows.')
    n = len(cap_file)
    out, err, them = [], [], []
    with tempfile.TemporaryDirectory() as td:
        vbs = Path(td) / 'xuat.vbs'
        vbs.write_text(_VBS, encoding='utf-16')
        ds = Path(td) / 'ds.txt'
        dau = f'in:{max(1, min(int(so_ban), 50))}' if che_do == 'in' else che_do
        ds.write_text('\n'.join([dau] + [f'{Path(a).resolve()}\t{Path(b).resolve() if b else ""}' for a, b in cap_file]),
                      encoding='utf-16')
        dung = Path(td) / 'dung.txt'
        bat_dau = time.time()
        try:
            pr = subprocess.Popen(['cscript', '//nologo', str(vbs), str(ds), str(dung)], stdout=subprocess.PIPE,
                                  stderr=subprocess.PIPE, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        except OSError as e:
            raise LoiIn(f'Không chạy được trình điều khiển Excel (cscript): {e}') from e
        for luong, ra in ((pr.stdout, out), (pr.stderr, err)):
            threading.Thread(target=_doc_luong, args=(luong, ra), daemon=True).start()
        xong, moc, xin_dung, treo = 0, time.time(), None, False
        while pr.poll() is None:
            so = sum(1 for x in out if x.startswith('XONG'))
            if so != xong:
                xong, moc = so, time.time()
            if bao is not None and bao(xong, n) and xin_dung is None:
                dung.write_text('1', encoding='ascii')
                xin_dung = time.time()
                them.append('DA_DUNG')                  # số file đã xong đếm lại khi Excel thoát (file đang dở vẫn làm nốt)
            gioi_han = cho_moi_file + (CHO_KHOI_DONG if xong == 0 else 0)
            if xin_dung is None and time.time() - moc > gioi_han:
                dung.write_text('1', encoding='ascii')
                xin_dung, treo = time.time(), True
                ten = Path(cap_file[min(xong, n - 1)][0]).name
                them.append(f'LOI_TREO\t{ten}\tExcel không xuất xong file sau {gioi_han} giây (kẹt hộp thoại ẩn / máy in?): '
                            f'đã dừng sau {xong}/{n} file')
            if xin_dung is not None and time.time() - xin_dung > (5 if treo else cho_moi_file):
                pr.kill()
                _tat_excel_tu_dong(bat_dau)
                break
            time.sleep(0.1)
        pr.wait()
    xong = sum(1 for x in out if x.startswith('XONG'))
    them = [f'DA_DUNG\t\tĐã dừng theo yêu cầu: xong {xong}/{n} file' if x == 'DA_DUNG' else x for x in them]
    loi_text = '\n'.join(err)
    if pr.returncode == 3 or 'KHONG_CO_EXCEL' in loi_text:
        raise LoiIn('Không mở được Microsoft Excel trên máy này: chỉ xuất được file Excel (.xlsx).')
    loi = [x for x in err if x.startswith(('LOI_MO', 'LOI_XUAT'))] + them
    if che_do == 'pdf' and not them:
        for a, b in cap_file:
            if not Path(b).exists() and not any(str(Path(a).resolve()) in x for x in loi):
                loi.append(f'LOI_XUAT\t{a}\tExcel không tạo được file PDF')
    return loi


def mo_file(p) -> None:
    """Mở file / thư mục bằng chương trình mặc định của Windows."""
    if sys.platform == 'win32':
        os.startfile(str(p))   # noqa: S606

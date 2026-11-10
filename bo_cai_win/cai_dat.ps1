# Trình cài PABT cho người dùng hiện tại - MỘT tiêu chuẩn cho cả hai bộ cài (ban.txt: win10 / win7) và gói .zip dự phòng:
#   - chạy qua CAI_DAT.cmd: PowerShell -Command đọc script này thành khối lệnh (không bị chính sách ExecutionPolicy /
#     Group Policy chặn như -File), PowerShell 2.0 (Windows 7) trở lên, -STA;
#   - mặc định cài vào C:\Program Files (x86)\PABT (người dùng yêu cầu 11/10/2026; Windows 32-bit: Program Files) - Windows hỏi
#     quyền quản trị cho bước chép file; từ chối -> %LOCALAPPDATA%\Programs\PABT (không cần quyền quản trị). KHÔNG cài thêm gì vào Windows:
#     mọi thư viện (Visual C++, UCRT cho Windows 7) đã nằm trong bản dựng (bo_cai_win\rut_gon.kiem_dll kiểm khi dựng);
#   - chép file theo danh_sach.txt (nguồn, đích, cỡ, SHA-256), kiểm lại từng file sau khi chép (bị diệt virus chặn / ổ đầy
#     -> báo rõ file nào) - không giải nén zip (không phụ thuộc Shell.Application / .NET 4.5).
#   Không tham số: cửa sổ cài đặt (chọn thư mục, tùy chọn, thanh tiến trình, tự kiểm tra sau khi cài).
#   -Im          cài im lặng (không hỏi, không mở phần mềm sau khi cài)
#   -ThuMuc X    thư mục cài (mặc định Program Files (x86)\PABT; không được cấp quyền quản trị -> %LOCALAPPDATA%\Programs\PABT)
#   -KhongDesktop / -KhongLienKet   bỏ biểu tượng Desktop / không gắn file .pabt
#   Thư mục cài không ghi được bằng quyền người dùng (Program Files, Program Files (x86)): CHỈ bước chép file chạy lại script
#   này với quyền quản trị (-ChiChep <file kết quả> -ThuMuc <thư mục> -Goc <thư mục bộ cài>, Windows hỏi UAC); lối tắt, liên
#   kết .pabt, mục gỡ cài, tự kiểm tra vẫn làm với quyền người dùng đang cài (nhập tài khoản quản trị khác vẫn đúng người dùng).
# Bộ cài win10 = Windows 10 1809 (build 17763) trở lên, 64-bit. Bộ cài win7 (32-bit) = mọi Windows từ 7 SP1: 7, 8, 8.1, 10 / 11
# (32 hoặc 64-bit) - dùng khi bộ cài win10 không hợp. Không dùng lệnh của PowerShell 3+.
param([switch]$Im, [string]$ThuMuc = '', [switch]$KhongDesktop, [switch]$KhongLienKet, [string]$ChiChep = '', [string]$Goc = '')
$ErrorActionPreference = 'Stop'
$GOC = $Goc                                         # tiến trình quyền quản trị: biến môi trường của người cài không truyền sang
if (-not $GOC) { $GOC = $env:PABT_GOC }             # CAI_DAT.cmd đặt; chạy thẳng bằng -File thì lấy theo đường dẫn script
if (-not $GOC) { $GOC = Split-Path -Parent $MyInvocation.MyCommand.Definition }     # PowerShell 2.0 chưa có $PSScriptRoot
$GOC = $GOC.TrimEnd('\')
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
[System.Windows.Forms.Application]::EnableVisualStyles()
# tên hiển thị bên ngoài (người dùng 15/10/2026): lối tắt Desktop "LARC", mô tả / Start Menu / Cài đặt > Ứng dụng tên đầy đủ;
# chương trình bên trong vẫn là PABT (PABT.exe, thư mục cài PABT, file .pabt)
$TEN = 'LARC - Bồi thường, hỗ trợ, tái định cư'
$TEN_NGAN = 'LARC'
# lối tắt các bản trước (gỡ khi cài bản mới - tên đã đổi)
$LOI_TAT_CU = @('PABT - Lập phương án bồi thường.lnk', 'PABT.lnk')
# định danh ứng dụng trên taskbar - PHẢI trùng pabt.app.APP_USER_MODEL_ID (tiến trình PABT tự đăng ký khi mở): lối tắt mang cùng
# định danh thì cửa sổ đang chạy nhập vào nút đã ghim, ghim lên taskbar giữ biểu tượng PABT (không tách hai nút / mất biểu tượng)
$APP_ID = 'vn.larc.desktop.enterprise'
$TEN_DAY_DU = 'PHẦN MỀM LẬP PHƯƠNG ÁN BỒI THƯỜNG, HỖ TRỢ, TÁI ĐỊNH CƯ'
$PHIEN_BAN = [System.IO.File]::ReadAllText((Join-Path $GOC 'phien_ban.txt')).Trim()
$BAN = 'win10'
if (Test-Path -LiteralPath (Join-Path $GOC 'ban.txt')) { $BAN = [System.IO.File]::ReadAllText((Join-Path $GOC 'ban.txt')).Trim() }
$DANH_SACH = 'danh_sach.txt'                        # danh sách file chép (nguồn, đích, cỡ, SHA-256)
$PHO_QUAT = $false
if ($BAN -eq 'universal') {
    # bộ cài phổ quát PABT_Setup_Universal (đặc tả ARCH-PABT-2026-V4 mục 9.2) chứa cả hai bản: tự chọn theo Windows của máy.
    # Windows 10 bản 1809 (build 17763) trở lên / Windows 11, 64-bit -> bản Qt6 x64; Windows 7 / 8 / 8.1, Windows 32-bit hoặc
    # Windows 10 bản cũ -> bản Qt5 x86 (chạy mọi Windows từ 7 SP1). Tiến trình chép file quyền quản trị đọc cùng ban.txt: chọn y hệt.
    $PHO_QUAT = $true
    $v0 = [Environment]::OSVersion.Version
    $may64_0 = ($env:PROCESSOR_ARCHITECTURE -eq 'AMD64' -or $env:PROCESSOR_ARCHITEW6432 -eq 'AMD64')
    if ($v0.Major -ge 10 -and $v0.Build -ge 17763 -and $may64_0) { $BAN = 'win10'; $DANH_SACH = 'danh_sach_x64.txt' }
    else { $BAN = 'win7'; $DANH_SACH = 'danh_sach_x86.txt' }
}
$TEN_BAN = 'Windows 10 / 11 (64-bit)'
if ($BAN -eq 'win7') { $TEN_BAN = 'Windows 7 / 8 / 10 (32-bit)' }
$KIEN = 'x64'                                   # kiến trúc chương trình và bộ Visual C++ kèm theo
if ($BAN -eq 'win7') { $KIEN = 'x86' }
$MAY64 = ($env:PROCESSOR_ARCHITECTURE -eq 'AMD64' -or $env:PROCESSOR_ARCHITEW6432 -eq 'AMD64')
$BIT = '32-bit'
if ($MAY64) { $BIT = '64-bit' }
$VC = Join-Path $GOC 'vc_redist.exe'
$CO_VC = Test-Path -LiteralPath $VC                          # bộ cài Win10-11 không kèm Visual C++ Redistributable
$nk =Join-Path $env:TEMP 'pabt_cai_dat.log'
if ($ChiChep) { $nk = "$ChiChep.log" }              # tiến trình chép file: nhật ký riêng, không xóa nhật ký của tiến trình cài
function Ghi($s) { Add-Content -Path $nk -Value ("{0:HH:mm:ss} {1}" -f (Get-Date), $s) -Encoding UTF8 }
Set-Content -Path $nk -Value "Cài PABT $PHIEN_BAN" -Encoding UTF8

# ---------------------------------------------------------------- kiểm tra hệ thống
Ghi "Bộ cài: $TEN_BAN ($BAN)$(if ($PHO_QUAT) { ' - bộ cài phổ quát tự chọn theo Windows' })"

function KiemTraMay {
    # điều kiện BẮT BUỘC (không đạt thì không cài): trả câu báo, '' = đạt
    $v = [Environment]::OSVersion.Version
    if ($v.Major -lt 6 -or ($v.Major -eq 6 -and $v.Minor -lt 1)) {
        return "LARC cần Windows 7 SP1 trở lên (máy này: Windows $($v.Major).$($v.Minor))." }
    if ($v.Major -eq 6 -and $v.Minor -eq 1 -and $v.Build -lt 7601) {
        return 'Windows 7 cần cài Service Pack 1 (SP1) trước khi cài PABT.' }
    if ($BAN -eq 'win10') {
        $khac = "dùng bộ cài PABT_CaiDat_$($PHIEN_BAN)_Win7-8-10_x86.exe hoặc LARC_Setup_Universal_$($PHIEN_BAN).exe (chạy được trên mọi Windows từ 7 SP1)."
        if ($v.Major -lt 10) { return "Bộ cài này dành cho Windows 10 / 11. Máy này là Windows $($v.Major).$($v.Minor): $khac" }
        if (-not $MAY64) { return "Máy này là Windows 32-bit: $khac" }
        if ($v.Build -lt 17763) { return "Windows 10 bản cũ (build $($v.Build); bộ cài này cần bản 1809 - build 17763 trở lên): $khac" }
    }
    try {                                           # WMI hỏng trên vài máy: bỏ qua bước đo dung lượng, không chặn cài
        $o = $env:LOCALAPPDATA.Substring(0, 2)
        $dia = Get-WmiObject Win32_LogicalDisk -Filter "DeviceID='$o'" -ErrorAction SilentlyContinue
        if ($dia -and $dia.FreeSpace -lt 300MB) { return "Ổ đĩa cài còn trống {0:N0} MB, cần ít nhất 300 MB." -f ($dia.FreeSpace / 1MB) }
    } catch { Ghi "Không đo được dung lượng ổ đĩa: $_" }
    return ''
}

# bản cập nhật Windows 7 KB3063858 đóng kèm bộ cài Win7-8 (kernel32 có AddDllDirectory = nội dung KB2533623 - Python 3.8 cần)
$KB_TEN = 'Windows6.1-KB3063858-x86.msu'
if ($MAY64) { $KB_TEN = 'Windows6.1-KB3063858-x64.msu' }       # theo kiến trúc WINDOWS (không theo chương trình 32-bit)
$KB = Join-Path $GOC $KB_TEN
$script:KB_CHO_KHOI_DONG = $false
$script:KB_LOI = ''                                 # lý do cài KB không được (để câu báo sau khi cài nói đúng)

function ThieuKbWin7 {
    # Windows 7 chưa có KB2533623: kernel32.dll bản SP1 gốc là 6.1.7601.17514, có KB2533623 từ 6.1.7601.17651 (nhánh LDR 2xxxx)
    $v = [Environment]::OSVersion.Version
    if ($BAN -ne 'win7' -or $v.Major -ne 6 -or $v.Minor -ne 1) { return $false }
    try {
        $k = (Get-Item -LiteralPath "$env:SystemRoot\System32\kernel32.dll").VersionInfo
        return ($k.FileBuildPart -eq 7601 -and $k.FilePrivatePart -lt 17651)
    } catch { return $false }
}

function CaiKbWin7 {
    # cài KB3063858 bằng wusa (Windows hỏi quyền quản trị một lần); có hiệu lực sau khi khởi động lại máy
    if (-not (ThieuKbWin7)) { return '' }
    if (-not (Test-Path -LiteralPath $KB)) { Ghi "KB3063858: bộ cài không có $KB_TEN"; return 'thieu' }
    $wusa = "$env:SystemRoot\Sysnative\wusa.exe"   # PowerShell 32-bit trên Windows 64-bit: gọi wusa 64-bit thật
    if (-not (Test-Path -LiteralPath $wusa)) { $wusa = "$env:SystemRoot\System32\wusa.exe" }
    try {
        $p = Start-Process $wusa -ArgumentList "`"$KB`"", '/quiet', '/norestart' -Verb RunAs -Wait -PassThru
        $ma = $p.ExitCode
        Ghi "KB3063858 ($KB_TEN): wusa trả mã $ma"
        # 0 = xong, 3010 = xong, cần khởi động lại; 2359302 (0x240006) = đã có; -2145124329 (0x80240017) = không hợp máy này
        if ($ma -eq 0 -or $ma -eq 3010) { $script:KB_CHO_KHOI_DONG = $true; return 'da_cai' }
        # "đã có" mà kernel32 vẫn bản cũ (ThieuKbWin7): bản cập nhật đã cài nhưng máy chưa khởi động lại
        if ($ma -eq 2359302) { $script:KB_CHO_KHOI_DONG = $true; return 'da_co' }
        $script:KB_LOI = "Windows báo mã $ma"
        return "loi $ma"
    } catch {
        Ghi "KB3063858: không cài được ($_)"
        $script:KB_LOI = 'chưa cấp quyền quản trị'
        return 'tu_choi'
    }
}

function CanhBaoMay {
    # điều kiện KHÔNG chặn cài (vẫn cài được): trả câu nhắc, '' = không có gì
    $v = [Environment]::OSVersion.Version
    if ($script:KB_CHO_KHOI_DONG) {
        return 'Đã cài bản cập nhật Windows 7 KB3063858: KHỞI ĐỘNG LẠI MÁY rồi mở PABT.' }
    if ($script:KB_LOI) {
        return "Chưa cài được bản cập nhật Windows 7 KB3063858 ($($script:KB_LOI)): PABT chỉ chạy sau khi có bản cập nhật này - " +
               'chạy lại bộ cài và đồng ý quyền quản trị, hoặc cài qua Windows Update.' }
    if (ThieuKbWin7) {
        if (Test-Path -LiteralPath $KB) {
            return 'Windows 7 này thiếu bản cập nhật KB3063858 của Microsoft (PABT cần): bộ cài cài kèm (Windows hỏi quyền quản ' +
                   'trị một lần), xong thì khởi động lại máy.' }
        return 'Windows 7 này chưa có bản cập nhật KB2533623 / KB3063858 của Microsoft: PABT vẫn được cài nhưng chỉ chạy sau ' +
               'khi cài bản cập nhật đó (Windows Update).'
    }
    if ($BAN -eq 'win7' -and $v.Major -ge 10 -and $MAY64) {
        return "Máy Windows 10 / 11 64-bit: bộ cài PABT_CaiDat_$($PHIEN_BAN)_Win10-11_x64.exe chạy nhanh hơn; bộ cài này vẫn cài và chạy được." }
    return ''
}

function CoVcRedist {
    if (-not $CO_VC) { return $true }           # không kèm: không cần cài (DLL Visual C++ đóng gói sẵn trong PABT)
    $can =[version]((Get-Item -LiteralPath $VC).VersionInfo.ProductVersion)
    foreach ($k in "HKLM:\SOFTWARE\Microsoft\VisualStudio\14.0\VC\Runtimes\$KIEN",
                   "HKLM:\SOFTWARE\WOW6432Node\Microsoft\VisualStudio\14.0\VC\Runtimes\$KIEN") {
        $r = Get-ItemProperty $k -ErrorAction SilentlyContinue
        if ($r -and $r.Installed -eq 1) {
            $co = [version]("{0}.{1}.{2}" -f $r.Major, $r.Minor, $r.Bld)
            if ($co -ge [version]("{0}.{1}.{2}" -f $can.Major, $can.Minor, $can.Build)) { return $true }
        }
    }
    return $false
}

function CaiVcRedist {
    if (-not $CO_VC) { Ghi 'Visual C++ Redistributable: không kèm (thư viện đóng gói sẵn trong PABT)'; return 'không cần' }
    if (CoVcRedist) { Ghi 'Visual C++ Redistributable: đã có'; return 'đã có sẵn' }
    try {
        $p = Start-Process $VC -ArgumentList '/install', '/quiet', '/norestart' `
             -Verb RunAs -Wait -PassThru
        Ghi "Visual C++ Redistributable: mã $($p.ExitCode)"
        if (@(0, 1638, 3010) -contains $p.ExitCode) { return 'đã cài' }
        return "bỏ qua (mã $($p.ExitCode))"
    } catch {
        Ghi "Visual C++ Redistributable: không cài ($_)"
        return 'bỏ qua (không cấp quyền quản trị) - phần mềm vẫn dùng thư viện đóng gói sẵn'
    }
}

function DemFile($thu) { @(Get-ChildItem -LiteralPath $thu -Recurse -Force | Where-Object { -not $_.PSIsContainer }).Count }

function MaBam($f) {
    $s = [System.IO.File]::OpenRead($f)
    try { return ([BitConverter]::ToString([System.Security.Cryptography.SHA256]::Create().ComputeHash($s))).Replace('-', '').ToLower() }
    finally { $s.Close() }
}

function ChepFile($dich, $tienDo) {
    # danh_sach.txt (UTF-8): mỗi dòng "nguồn<TAB>đích<TAB>cỡ<TAB>SHA-256" - nguồn tính từ thư mục bộ cài, đích từ thư mục cài.
    # Bộ cài .exe: nguồn là file phẳng f001_… (IExpress không giữ thư mục); gói .zip: nguồn là đường dẫn trong gói.
    $ds = @()
    foreach ($d in [System.IO.File]::ReadAllLines((Join-Path $GOC $DANH_SACH), [System.Text.Encoding]::UTF8)) {
        $x = $d.Split("`t")
        if ($x.Count -ge 4) { $ds += , @($x[0], $x[1], [long]$x[2], $x[3]) }
    }
    if ($ds.Count -eq 0) { throw "Bộ cài thiếu danh sách file ($DANH_SACH): tải lại bộ cài." }
    $n = $ds.Count; $i = 0; $loi = @()
    foreach ($x in $ds) {
        $nguon = Join-Path $GOC $x[0]; $ra = Join-Path $dich $x[1]
        $tm = Split-Path $ra
        if (-not (Test-Path -LiteralPath $tm)) { [void][System.IO.Directory]::CreateDirectory($tm) }
        try { [System.IO.File]::Copy($nguon, $ra, $true) } catch { $loi += "$($x[1]) ($($_.Exception.Message))" }
        $i++
        if ($tienDo -and ($i % 5 -eq 0 -or $i -eq $n)) { & $tienDo (10 + [int](68 * $i / $n)) "Đang chép file ($i/$n)…" }
    }
    $i = 0
    foreach ($x in $ds) {                           # kiểm lại từng file: thiếu / sai (diệt virus chặn, ổ đầy) thì báo rõ
        $ra = Join-Path $dich $x[1]; $i++
        if (-not (Test-Path -LiteralPath $ra)) { $loi += "$($x[1]) (không có)"; continue }
        if ((Get-Item -LiteralPath $ra).Length -ne $x[2] -or (MaBam $ra) -ne $x[3]) { $loi += "$($x[1]) (nội dung sai)" }
        if ($tienDo -and ($i % 10 -eq 0 -or $i -eq $n)) { & $tienDo (78 + [int](8 * $i / $n)) "Kiểm tra file ($i/$n)…" }
    }
    if ($loi.Count -gt 0) {
        $loi | ForEach-Object { Ghi "File lỗi: $_" }
        throw ("Chép thiếu / hỏng $($loi.Count) file, ví dụ $($loi[0]). Thường do phần mềm diệt virus chặn hoặc ổ đĩa đầy: " +
               'tạm tắt diệt virus (hoặc cho phép thư mục cài) rồi cài lại.')
    }
    Ghi "Đã chép và kiểm tra $n file"
    return $n
}

# ---------------------------------------------------------------- lối tắt (Start Menu, Desktop)
# WScript.Shell đổi tên / đường dẫn lối tắt sang bảng mã ANSI của Windows: máy Windows tiếng Anh (hoặc tên người dùng có dấu)
# thì "Lập phương án bồi thường" thành "L?p … b?i thư?ng" -> Save() lỗi "Unable to save shortcut" và cả lần cài dừng lại.
# Dùng IShellLinkW (Unicode) qua C# biên dịch tại chỗ (chạy được với .NET 2.0 / 3.5 của PowerShell 2.0 - Windows 7).
$LOI_TAT_CS = @'
using System;
using System.Text;
using System.Runtime.InteropServices;
using System.Runtime.InteropServices.ComTypes;
public static class PabtLoiTat {
    [ComImport, Guid("00021401-0000-0000-C000-000000000046")] class ShellLink { }
    [ComImport, InterfaceType(ComInterfaceType.InterfaceIsIUnknown), Guid("000214F9-0000-0000-C000-000000000046")]
    interface IShellLinkW {
        void GetPath([Out, MarshalAs(UnmanagedType.LPWStr)] StringBuilder f, int c, IntPtr fd, int fl);
        void GetIDList(out IntPtr p);
        void SetIDList(IntPtr p);
        void GetDescription([Out, MarshalAs(UnmanagedType.LPWStr)] StringBuilder s, int c);
        void SetDescription([MarshalAs(UnmanagedType.LPWStr)] string s);
        void GetWorkingDirectory([Out, MarshalAs(UnmanagedType.LPWStr)] StringBuilder s, int c);
        void SetWorkingDirectory([MarshalAs(UnmanagedType.LPWStr)] string s);
        void GetArguments([Out, MarshalAs(UnmanagedType.LPWStr)] StringBuilder s, int c);
        void SetArguments([MarshalAs(UnmanagedType.LPWStr)] string s);
        void GetHotkey(out short k);
        void SetHotkey(short k);
        void GetShowCmd(out int n);
        void SetShowCmd(int n);
        void GetIconLocation([Out, MarshalAs(UnmanagedType.LPWStr)] StringBuilder s, int c, out int i);
        void SetIconLocation([MarshalAs(UnmanagedType.LPWStr)] string s, int i);
        void SetRelativePath([MarshalAs(UnmanagedType.LPWStr)] string s, int r);
        void Resolve(IntPtr h, int f);
        void SetPath([MarshalAs(UnmanagedType.LPWStr)] string s);
    }
    [ComImport, InterfaceType(ComInterfaceType.InterfaceIsIUnknown), Guid("886D8EEB-8CF2-4446-8D02-CDBA1DBDCF99")]
    interface IPropertyStore {
        void GetCount(out uint c);
        void GetAt(uint i, out KhoaThuocTinh k);
        void GetValue(ref KhoaThuocTinh k, IntPtr v);
        void SetValue(ref KhoaThuocTinh k, ref GiaTriThuocTinh v);
        void Commit();
    }
    [StructLayout(LayoutKind.Sequential, Pack = 4)]
    struct KhoaThuocTinh { public Guid fmtid; public uint pid; }
    [StructLayout(LayoutKind.Explicit)]
    struct GiaTriThuocTinh { [FieldOffset(0)] public ushort vt; [FieldOffset(8)] public IntPtr p; [FieldOffset(16)] public IntPtr du; }
    // System.AppUserModel.ID (PKEY_AppUserModel_ID) - Windows 7 trở lên; lỗi thì bỏ qua (lối tắt vẫn tạo được)
    static void DatAppId(IShellLinkW l, string appId) {
        if (appId == null || appId.Length == 0) return;
        IPropertyStore ps = (IPropertyStore)l;
        KhoaThuocTinh k = new KhoaThuocTinh();
        k.fmtid = new Guid("9F4C2855-9F79-4B39-A8D0-E1D42DE1D5F3");
        k.pid = 5;
        GiaTriThuocTinh v = new GiaTriThuocTinh();
        v.vt = 31;                                      // VT_LPWSTR
        v.p = Marshal.StringToCoTaskMemUni(appId);
        try { ps.SetValue(ref k, ref v); ps.Commit(); }
        finally { Marshal.FreeCoTaskMem(v.p); }
    }
    public static void Tao(string lnk, string dich, string thuMuc, string bieuTuong, string moTa, string appId) {
        IShellLinkW l = (IShellLinkW)new ShellLink();
        l.SetPath(dich);
        l.SetWorkingDirectory(thuMuc);
        l.SetIconLocation(bieuTuong, 0);
        l.SetDescription(moTa);
        try { DatAppId(l, appId); } catch (Exception) { }
        ((IPersistFile)l).Save(lnk, true);
        Marshal.ReleaseComObject(l);
    }
    // lối tắt đã có (ghim taskbar / Start) trỏ tới exe: đổi biểu tượng + mô tả. Trả true nếu đã sửa
    public static bool DoiBieuTuong(string lnk, string exe, string bieuTuong, string moTa, string appId) {
        IShellLinkW l = (IShellLinkW)new ShellLink();
        try {
            ((IPersistFile)l).Load(lnk, 2);             // STGM_READWRITE
            StringBuilder p = new StringBuilder(1024);
            l.GetPath(p, p.Capacity, IntPtr.Zero, 0);
            if (!string.Equals(p.ToString(), exe, StringComparison.OrdinalIgnoreCase)) return false;
            l.SetIconLocation(bieuTuong, 0);
            l.SetDescription(moTa);
            try { DatAppId(l, appId); } catch (Exception) { }
            ((IPersistFile)l).Save(lnk, true);
            return true;
        } finally { Marshal.ReleaseComObject(l); }
    }
    [DllImport("shell32.dll")] static extern void SHChangeNotify(int e, uint f, IntPtr a, IntPtr b);
    // SHCNE_ASSOCCHANGED: Explorer / taskbar vẽ lại biểu tượng lối tắt
    public static void LamMoi() { SHChangeNotify(0x08000000, 0, IntPtr.Zero, IntPtr.Zero); }
}
'@

function TaoLoiTat($lnk, $exe, $thu, $ico) {
    # trả đường dẫn lối tắt đã tạo, hoặc '' nếu không tạo được (không làm hỏng lần cài)
    try {
        if (-not ('PabtLoiTat' -as [type])) { Add-Type -TypeDefinition $LOI_TAT_CS }
        [PabtLoiTat]::Tao($lnk, $exe, $thu, $ico, $TEN, $APP_ID)
        if (Test-Path -LiteralPath $lnk) { return $lnk }
    } catch { Ghi "Lối tắt (IShellLinkW) lỗi: $_" }
    try {                                       # dự phòng: WScript.Shell với tên không dấu
        $p = Join-Path (Split-Path $lnk) 'LARC.lnk'
        $l = (New-Object -ComObject WScript.Shell).CreateShortcut($p)
        $l.TargetPath = $exe; $l.WorkingDirectory = $thu; $l.IconLocation = "$ico,0"; $l.Description = 'LARC'
        $l.Save()
        return $p
    } catch { Ghi "Lối tắt (WScript) lỗi: $_" }
    return ''
}

# ---------------------------------------------------------------- cài
$PF = ${env:ProgramFiles(x86)}                      # Windows 32-bit không có Program Files (x86)
if (-not $PF) { $PF = $env:ProgramFiles }
$MAC_DINH = Join-Path $PF 'PABT'                    # mặc định (người dùng 11/10/2026) - cần quyền quản trị (Windows hỏi UAC)
$KHONG_QT = Join-Path $env:LOCALAPPDATA 'Programs\PABT'   # không cần quyền quản trị: từ chối UAC / chọn "Không"
$script:TU_CHOI = $false                            # vừa bị từ chối quyền quản trị (ChepQuyenQuanTri)

function GhiDuoc($dich) {
    # thư mục cài (hoặc thư mục cha gần nhất đã có) ghi được bằng quyền người dùng hiện tại không: Program Files, Windows... cần
    # quyền quản trị - bộ cài không xin quyền (tiêu chuẩn cài đặt 0.9.21), trước đây lỗi "Access to the path ... is denied"
    try { $p = [System.IO.Path]::GetFullPath($dich) } catch { return $false }
    while ($p -and -not (Test-Path -LiteralPath $p)) { $p = [System.IO.Path]::GetDirectoryName($p) }
    if (-not $p) { return $false }
    $thu = Join-Path $p ('pabt_thu_ghi_' + [Guid]::NewGuid().ToString('N') + '.tmp')
    try { [System.IO.File]::WriteAllText($thu, ''); [System.IO.File]::Delete($thu); return $true } catch { return $false }
}

function ChuKhongGhiDuoc($dich) {
    return "Chưa được cấp quyền quản trị nên không chép được PABT vào $dich (thư mục hệ thống của Windows như Program Files). " +
           "Bấm Cài đặt lại và chọn Có (Yes) khi Windows hỏi, hoặc cài vào thư mục không cần quyền quản trị: $KHONG_QT."
}

function CungThuMuc($duong, $goc) {
    # cùng thư mục hoặc thư mục con (so không phân biệt hoa thường)
    if (-not $duong -or -not $goc) { return $false }
    $a = $duong.TrimEnd('\').ToLower(); $b = $goc.TrimEnd('\').ToLower()
    return ($a -eq $b) -or $a.StartsWith($b + '\')
}

function TatPabtDangMo($dich) {
    # Bộ cài phổ quát chạy PowerShell 32-bit (vỏ IExpress 32-bit). Get-Process.Path của tiến trình PABT 64-bit trả về RỖNG
    # nên trước đây không tắt được phần mềm đang mở, Remove-Item kẹt ở qwindows.dll ("Access is denied").
    # Win32_Process.ExecutablePath đọc được từ PowerShell 32-bit.
    $i = 0
    while ($i -lt 25) {
        $con = $false
        foreach ($q in @(Get-WmiObject Win32_Process -Filter "Name='PABT.exe'" -ErrorAction SilentlyContinue)) {
            if (CungThuMuc $q.ExecutablePath $dich) {
                $con = $true
                if ($i -eq 0) { Ghi "Đóng PABT đang mở để cài đè (pid $($q.ProcessId), $($q.ExecutablePath))" }
                Stop-Process -Id $q.ProcessId -Force -ErrorAction SilentlyContinue
            }
        }
        if (-not $con) { return }
        Start-Sleep -Milliseconds 200
        $i++
    }
}

function TienTrinhGiuFile($file) {
    # Restart Manager: tên tiến trình đang mở file (PABT còn chạy, chương trình diệt virus...)
    if (-not ('PabtKhoaFile' -as [type])) {
        Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;
using System.Text;
public class PabtKhoaFile {
  [DllImport("rstrtmgr.dll", CharSet=CharSet.Unicode)] static extern int RmStartSession(out uint s, int d, string k);
  [DllImport("rstrtmgr.dll")] static extern int RmEndSession(uint s);
  [DllImport("rstrtmgr.dll", CharSet=CharSet.Unicode)] static extern int RmRegisterResources(uint s, uint nFiles, string[] files, uint nApp, IntPtr apps, uint nSvc, string[] svcs);
  [DllImport("rstrtmgr.dll")] static extern int RmGetList(uint s, out uint needed, ref uint n, [In, Out] RM_PROCESS_INFO[] info, ref uint reboot);
  [StructLayout(LayoutKind.Sequential)] public struct FILETIME { public uint a, b; }
  [StructLayout(LayoutKind.Sequential)] public struct RM_UNIQUE_PROCESS { public int dwProcessId; public FILETIME ProcessStartTime; }
  [StructLayout(LayoutKind.Sequential, CharSet=CharSet.Unicode)]
  public struct RM_PROCESS_INFO {
    public RM_UNIQUE_PROCESS Process;
    [MarshalAs(UnmanagedType.ByValTStr, SizeConst=256)] public string strAppName;
    [MarshalAs(UnmanagedType.ByValTStr, SizeConst=64)] public string strServiceShortName;
    public uint ApplicationType, AppStatus, TSSessionId;
    [MarshalAs(UnmanagedType.Bool)] public bool bRestartable;
  }
  public static string LietKe(string file) {
    uint s; if (RmStartSession(out s, 0, Guid.NewGuid().ToString()) != 0) return "";
    try {
      if (RmRegisterResources(s, 1, new string[] { file }, 0, IntPtr.Zero, 0, null) != 0) return "";
      uint need = 0, n = 0, reboot = 0;
      RmGetList(s, out need, ref n, null, ref reboot);
      if (need == 0) return "";
      RM_PROCESS_INFO[] info = new RM_PROCESS_INFO[need];
      n = need;
      if (RmGetList(s, out need, ref n, info, ref reboot) != 0) return "";
      StringBuilder sb = new StringBuilder();
      for (int i = 0; i < n; i++) {
        if (sb.Length > 0) sb.Append("; ");
        sb.Append(info[i].strAppName).Append(" (pid ").Append(info[i].Process.dwProcessId).Append(")");
      }
      return sb.ToString();
    } finally { RmEndSession(s); }
  }
}
'@
    }
    try { return [PabtKhoaFile]::LietKe($file) } catch { return '' }
}

function XoaThuMucCu($dich) {
    if (-not (Test-Path -LiteralPath $dich)) { return }
    TatPabtDangMo $dich
    $loi = ''
    $lan = 0
    while ($lan -lt 6) {
        try { Remove-Item -LiteralPath $dich -Recurse -Force -ErrorAction Stop; Ghi 'Đã gỡ bản cũ'; return }
        catch { $loi = "$_"; $lan++; Start-Sleep -Milliseconds 300; TatPabtDangMo $dich }
    }
    $mau = Join-Path $dich '_internal\PySide6\plugins\platforms\qwindows.dll'
    if (-not (Test-Path -LiteralPath $mau)) { $mau = Join-Path $dich 'PABT.exe' }
    $giu = ''
    if (Test-Path -LiteralPath $mau) { $giu = TienTrinhGiuFile $mau }
    $chu = "Không xóa được bản PABT đang có trong $dich vì có file đang bị chương trình khác giữ"
    if ($giu) { $chu += " ($giu)" } else { $chu += ". $loi" }
    throw ($chu + '. Đóng phần mềm đó rồi bấm "Cài đặt" lại.')
}

function ChepVao($dich, $tienDo) {
    # phần GHI vào thư mục cài - chạy thẳng, hoặc trong tiến trình quyền quản trị (ChepQuyenQuanTri) khi cài vào Program Files
    KiemTraThuMuc $dich
    XoaThuMucCu $dich
    [void][System.IO.Directory]::CreateDirectory($dich)
    ChepFile $dich $tienDo | Out-Null
    [System.IO.File]::Copy((Join-Path $GOC 'go_cai_dat.ps1'), (Join-Path $dich 'go_cai_dat.ps1'), $true)
}

function ChepQuyenQuanTri($dich, $tienDo) {
    # chạy lại script này với quyền quản trị (Windows hỏi UAC) chỉ để chép file; theo dõi tiến độ qua file "<kết quả>.tien_do"
    $kq = Join-Path $env:TEMP ('pabt_chep_' + [Guid]::NewGuid().ToString('N') + '.txt')
    $ps = Join-Path $GOC 'cai_dat.ps1'
    $lenh = "& ([scriptblock]::Create([IO.File]::ReadAllText('" + $ps.Replace("'", "''") + "', [Text.Encoding]::UTF8))) " +
            "-ChiChep '" + $kq.Replace("'", "''") + "' -ThuMuc '" + $dich.Replace("'", "''") + "' -Goc '" + $GOC.Replace("'", "''") + "'"
    Ghi "Chép file bằng quyền quản trị vào $dich"
    if ($tienDo) { & $tienDo 10 'Windows hỏi quyền quản trị để chép PABT vào thư mục hệ thống - chọn Có (Yes)…' }
    try {
        $pr = Start-Process "$env:SystemRoot\System32\WindowsPowerShell\v1.0\powershell.exe" -Verb RunAs -PassThru -WindowStyle Hidden `
              -ArgumentList '-NoProfile', '-ExecutionPolicy', 'Bypass', '-STA', '-WindowStyle', 'Hidden', '-Command', $lenh
    } catch { Ghi "Không được cấp quyền quản trị: $_"; $script:TU_CHOI = $true; throw (ChuKhongGhiDuoc $dich) }
    while (-not $pr.HasExited) {
        Start-Sleep -Milliseconds 250
        if ($tienDo -and (Test-Path -LiteralPath "$kq.tien_do")) {
            try { $x = [System.IO.File]::ReadAllText("$kq.tien_do", [System.Text.Encoding]::UTF8).Split("`t")
                  if ($x.Count -ge 2) { & $tienDo ([int]$x[0]) $x[1] } } catch { }
        }
        [System.Windows.Forms.Application]::DoEvents()
    }
    if (Test-Path -LiteralPath "$kq.log") { Add-Content -Path $nk -Value ([System.IO.File]::ReadAllText("$kq.log")) -Encoding UTF8 }
    $ra = ''
    if (Test-Path -LiteralPath $kq) { $ra = [System.IO.File]::ReadAllText($kq, [System.Text.Encoding]::UTF8) }
    foreach ($f in @($kq, "$kq.log", "$kq.tien_do")) { Remove-Item -LiteralPath $f -Force -ErrorAction SilentlyContinue }
    if ($ra -eq 'OK') { return }
    if ($ra.StartsWith("LOI`t")) { throw $ra.Substring(4) }
    throw "Bước chép file (quyền quản trị) dừng giữa chừng, mã $($pr.ExitCode). Xem nhật ký: $nk"
}

function KiemTraThuMuc($dich) {
    # chỉ xóa thư mục trống hoặc bản PABT cũ: gõ nhầm D:\ hay chọn Documents thì không được xóa dữ liệu người dùng
    if ($dich.TrimEnd('\') -eq [System.IO.Path]::GetPathRoot($dich).TrimEnd('\')) {
        throw "Không cài thẳng vào gốc ổ đĩa ($dich): chọn một thư mục, ví dụ $($dich.TrimEnd('\'))\PABT." }
    if (-not (Test-Path -LiteralPath $dich)) { return }
    $co = @(Get-ChildItem -LiteralPath $dich -Force)
    if ($co.Count -gt 0 -and -not (Test-Path -LiteralPath (Join-Path $dich 'PABT.exe'))) {
        throw "Thư mục $dich đã có file khác (không phải bản cài PABT). Chọn thư mục trống hoặc thư mục PABT đã cài trước đây." }
    # lọc đuôi bằng Where-Object (-Include không có tác dụng với -LiteralPath); -LiteralPath: tên có "[" không bị hiểu là ký tự đại diện
    $da = @(Get-ChildItem -LiteralPath $dich -Recurse -Force -ErrorAction SilentlyContinue |
            Where-Object { -not $_.PSIsContainer -and (@('.larc','.pabt','.pabtdt','.xlsx','.xlsm','.xls','.docx','.doc','.pdf','.csv') -contains $_.Extension.ToLower()) })
    if ($da.Count -gt 0) {
        throw "Thư mục cài có $($da.Count) file dự án / Excel / Word / PDF của bạn (ví dụ $($da[0].FullName)). Chuyển các file dự án ra thư mục khác rồi cài lại." }
}

function GoBanCu($cu, $dich) {
    # bản PABT đã cài ở thư mục KHÁC (mục gỡ cài cũ trong HKCU): gỡ thư mục chương trình cũ - chỉ khi có PABT.exe và không có file
    # dự án (.pabt / .pabtdt); không xóa được (cần quyền quản trị...) thì chỉ ghi nhật ký
    if (-not $cu) { return }
    try { $cu = [System.IO.Path]::GetFullPath($cu).TrimEnd('\') } catch { return }
    if ($cu -eq $dich.TrimEnd('\') -or -not (Test-Path -LiteralPath (Join-Path $cu 'PABT.exe'))) { return }
    $da = @(Get-ChildItem -LiteralPath $cu -Recurse -Force -ErrorAction SilentlyContinue |
            Where-Object { -not $_.PSIsContainer -and (@('.larc','.pabt','.pabtdt','.xlsx','.xlsm','.xls','.docx','.doc','.pdf','.csv') -contains $_.Extension.ToLower()) })
    if ($da.Count -gt 0) { Ghi "Giữ bản cũ $cu (có $($da.Count) file dự án)"; return }
    try {
        XoaThuMucCu $cu
        Ghi "Đã gỡ bản cũ ở thư mục khác: $cu"
    } catch { Ghi "Chưa gỡ được bản cũ $cu ($_)" }
}

function Cai($dich, $desktop, $lienKet, $tienDo) {
    $dich = [System.IO.Path]::GetFullPath($dich)
    Ghi "Thư mục cài: $dich"
    $cu = (Get-ItemProperty 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\PABT' -ErrorAction SilentlyContinue).InstallLocation
    if (GhiDuoc $dich) { ChepVao $dich $tienDo } else { ChepQuyenQuanTri $dich $tienDo }      # Program Files: hỏi quyền quản trị
    GoBanCu $cu $dich
    Ghi "Đã chép $(DemFile $dich) file (PowerShell $($PSVersionTable.PSVersion), Windows $([Environment]::OSVersion.Version))"
    if ($tienDo) { & $tienDo 88 'Tạo biểu tượng, liên kết file…' }
    $exe = Join-Path $dich 'PABT.exe'
    # biểu tượng MANG SỐ PHIÊN BẢN (LARC_<ver>.ico): bộ đệm biểu tượng của Windows giữ ảnh theo ĐƯỜNG DẪN file - trước đây mọi bản
    # dùng chung PABT.ico nên đổi biểu tượng (0.9.87 -> 0.9.91) Desktop / taskbar vẫn hiện ảnh cũ
    $ico = Join-Path $dich "LARC_$PHIEN_BAN.ico"
    if (-not (Test-Path -LiteralPath $ico)) { $ico = Join-Path $dich 'PABT.ico' }
    if (-not (Test-Path -LiteralPath $ico)) { $ico = $exe }
    $thuPr = [Environment]::GetFolderPath('Programs'); $thuDk = [Environment]::GetFolderPath('Desktop')
    foreach ($t in $LOI_TAT_CU) {                    # lối tắt tên cũ (PABT) của bản trước
        foreach ($p in @((Join-Path $thuPr $t), (Join-Path $thuDk $t))) {
            if (Test-Path -LiteralPath $p) { Remove-Item -LiteralPath $p -Force -ErrorAction SilentlyContinue }
        }
    }
    $lnk = @((Join-Path $thuPr "$TEN.lnk"))
    $dk = Join-Path $thuDk "$TEN_NGAN.lnk"
    if ($desktop) { $lnk += $dk } elseif (Test-Path -LiteralPath $dk) { Remove-Item -LiteralPath $dk -Force }
    $script:LOI_TAT = @()
    foreach ($p in $lnk) {
        $da = TaoLoiTat $p $exe $dich $ico
        if ($da) { Ghi "Lối tắt: $da" } else { $script:LOI_TAT += (Split-Path $p -Leaf) }
    }
    # PABT đã ghim lên taskbar / Start (lối tắt Windows tạo khi ghim): đổi sang biểu tượng mới
    $ghim = Join-Path $env:APPDATA 'Microsoft\Internet Explorer\Quick Launch\User Pinned'
    if (Test-Path -LiteralPath $ghim) {
        foreach ($g in @(Get-ChildItem -LiteralPath $ghim -Recurse -Force -ErrorAction SilentlyContinue |
                         Where-Object { -not $_.PSIsContainer -and $_.Extension -eq '.lnk' })) {
            try { if ([PabtLoiTat]::DoiBieuTuong($g.FullName, $exe, $ico, $TEN, $APP_ID)) { Ghi "Lối tắt đã ghim: $($g.FullName)" } }
            catch { }
        }
    }
    try { [PabtLoiTat]::LamMoi() } catch { }
    # khóa registry: New-Item -Value đặt giá trị mặc định (cách viết chạy được cả PowerShell 2.0)
    if ($lienKet) {
        # .larc = file dự án từ 15/10/2026; .pabt của các bản trước vẫn mở bằng phần mềm (cùng định dạng)
        New-Item 'HKCU:\Software\Classes\.larc' -Value 'PABT.DuAn' -Force | Out-Null
        New-Item 'HKCU:\Software\Classes\.pabt' -Value 'PABT.DuAn' -Force | Out-Null
        New-Item 'HKCU:\Software\Classes\PABT.DuAn' -Value 'Dự án LARC' -Force | Out-Null
        New-Item 'HKCU:\Software\Classes\PABT.DuAn\DefaultIcon' -Value "`"$ico`",0" -Force | Out-Null
        New-Item 'HKCU:\Software\Classes\PABT.DuAn\shell\open\command' -Value "`"$exe`" `"%1`"" -Force | Out-Null
    }
    # gói cập nhật .larcud (cũ: .pabtcn): bấm đúp để cập nhật phần mềm
    New-Item 'HKCU:\Software\Classes\.pabtcn' -Value 'PABT.CapNhat' -Force | Out-Null
    New-Item 'HKCU:\Software\Classes\.larcud' -Value 'PABT.CapNhat' -Force | Out-Null
    New-Item 'HKCU:\Software\Classes\PABT.CapNhat' -Value 'Gói cập nhật LARC' -Force | Out-Null
    New-Item 'HKCU:\Software\Classes\PABT.CapNhat\DefaultIcon' -Value "`"$ico`",0" -Force | Out-Null
    New-Item 'HKCU:\Software\Classes\PABT.CapNhat\shell\open\command' -Value "`"$exe`" `"%1`"" -Force | Out-Null
    # gói mẫu in & cấu hình .pabtcfg (0.9.85): bấm đúp để thay mẫu in / hồ sơ địa phương
    New-Item 'HKCU:\Software\Classes\.pabtcfg' -Value 'PABT.MauIn' -Force | Out-Null
    New-Item 'HKCU:\Software\Classes\PABT.MauIn' -Value 'Gói mẫu in & cấu hình LARC' -Force | Out-Null
    New-Item 'HKCU:\Software\Classes\PABT.MauIn\DefaultIcon' -Value "`"$ico`",0" -Force | Out-Null
    New-Item 'HKCU:\Software\Classes\PABT.MauIn\shell\open\command' -Value "`"$exe`" `"%1`"" -Force | Out-Null
    $k = 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\PABT'
    New-Item $k -Force | Out-Null
    # gỡ cài cũng chạy qua -Command (không bị ExecutionPolicy / Group Policy chặn như -File)
    $q1 = (Join-Path $dich 'go_cai_dat.ps1').Replace("'", "''"); $q2 = $dich.Replace("'", "''")
    $go = "powershell.exe -NoProfile -ExecutionPolicy Bypass -STA -WindowStyle Hidden -Command `"& ([scriptblock]::Create(" +
          "[IO.File]::ReadAllText('$q1', [Text.Encoding]::UTF8))) -Dich '$q2'"
    $goIm = "$go -Im`""; $go = "$go`""
    # nút Gỡ của Windows: PABT.exe (ứng dụng cửa sổ, không console) chạy go_cai_dat.ps1 bằng PowerShell không cửa sổ - Windows
    # chạy thẳng powershell.exe thì Windows 11 mở cửa sổ Windows Terminal trống suốt lúc gỡ (-WindowStyle Hidden không ẩn được).
    # Gỡ im lặng (công cụ quản trị chờ lệnh chạy xong): giữ lệnh PowerShell.
    $goAn = "`"$exe`" go-cai-dat"
    $mb = [int]((Get-ChildItem -LiteralPath $dich -Recurse -Force | Where-Object { -not $_.PSIsContainer } | Measure-Object Length -Sum).Sum / 1KB)
    foreach ($kv in @(@('DisplayName', $TEN), @('DisplayVersion', $PHIEN_BAN), @('Publisher', $TEN_NGAN), @('InstallLocation', $dich),
                      @('DisplayIcon', "$ico,0"), @('UninstallString', $goAn), @('QuietUninstallString', $goIm))) {
        New-ItemProperty $k -Name $kv[0] -Value $kv[1] -PropertyType String -Force | Out-Null
    }
    foreach ($kv in @(@('NoModify', 1), @('NoRepair', 1), @('EstimatedSize', $mb))) {
        New-ItemProperty $k -Name $kv[0] -Value $kv[1] -PropertyType DWord -Force | Out-Null
    }
    $ie = "$env:SystemRoot\System32\ie4uinit.exe"     # làm mới bộ đệm biểu tượng (Windows 10+: -show; Windows 7/8: -ClearIconCache)
    $tham = '-ClearIconCache'
    if ([Environment]::OSVersion.Version.Major -ge 10) { $tham = '-show' }
    try { if (Test-Path -LiteralPath $ie) { Start-Process $ie -ArgumentList $tham -WindowStyle Hidden -Wait } } catch { }
    # tự kiểm tra bản vừa cài trên máy này
    if ($tienDo) { & $tienDo 94 'Tự kiểm tra phần mềm trên máy này…' }
    $kq = Join-Path $env:TEMP 'pabt_tu_kiem.txt'
    Remove-Item -LiteralPath $kq -ErrorAction SilentlyContinue
    $tk = 'KET QUA: không chạy được PABT.exe'
    try {                                       # chờ tối đa 3 phút: exe treo (thiếu DLL...) không làm bộ cài đứng im
        $pr = Start-Process $exe -ArgumentList 'tu-kiem', "`"$kq`"" -PassThru
        if (-not $pr.WaitForExit(180000)) {
            try { $pr.Kill() } catch { }
            $tk = 'KET QUA: PABT.exe không trả lời sau 3 phút (tự kiểm tra bị dừng)'
        }
    } catch { $tk = "KET QUA: không chạy được PABT.exe ($_)" }
    if (Test-Path -LiteralPath $kq) { $tk = [System.IO.File]::ReadAllText($kq, [System.Text.Encoding]::UTF8) }
    Ghi $tk
    return $tk
}

# ---------------------------------------------------------------- tiến trình quyền quản trị: chỉ chép file (ChepQuyenQuanTri)
if ($ChiChep) {
    $tienDoTep = { param($phan, $chu)
        try { [System.IO.File]::WriteAllText("$ChiChep.tien_do", "$phan`t$chu", [System.Text.Encoding]::UTF8) } catch { } }
    try {
        ChepVao ([System.IO.Path]::GetFullPath($ThuMuc)) $tienDoTep
        [System.IO.File]::WriteAllText($ChiChep, 'OK', [System.Text.Encoding]::UTF8)
        exit 0
    } catch {
        Ghi "LỖI: $_"
        [System.IO.File]::WriteAllText($ChiChep, "LOI`t$_", [System.Text.Encoding]::UTF8)
        exit 1
    }
}

# ---------------------------------------------------------------- cài im lặng
if ($Im) {
    try {
        $loi = KiemTraMay; if ($loi) { Ghi "LỖI: $loi"; exit 3 }
        $cb = CanhBaoMay; if ($cb) { Ghi "LƯU Ý: $cb" }
        CaiVcRedist | Out-Null
        CaiKbWin7 | Out-Null                        # chỉ Windows 7 còn thiếu KB2533623
        $dich = $ThuMuc
        if (-not $dich) { $dich = $MAC_DINH }
        try { $tk = Cai $dich (-not $KhongDesktop) (-not $KhongLienKet) $null }
        catch {
            if (-not ($script:TU_CHOI -and -not $ThuMuc)) { throw }
            Ghi "Không được cấp quyền quản trị: cài vào $KHONG_QT"
            $tk = Cai $KHONG_QT (-not $KhongDesktop) (-not $KhongLienKet) $null
        }
        Ghi 'XONG'
        if ($script:KB_CHO_KHOI_DONG) { Ghi 'Cần khởi động lại máy (bản cập nhật Windows 7 KB3063858)'; exit 3010 }
        if ($tk -match 'KET QUA: DAT') { exit 0 } else { exit 4 }
    } catch { Ghi "LỖI: $_"; exit 1 }
}

# ---------------------------------------------------------------- cửa sổ cài đặt (1.0.27: thiết kế lại theo chuẩn bộ cài thương mại)
# Bố cục: banner (logo, tên sản phẩm, phiên bản / hệ điều hành) | thân (vị trí cài, tùy chọn, thẻ trạng thái, tiến trình) | chân (nút).
# Tiêu chuẩn: lưới 4 / 8 px nhân theo DPI màn hình (tiến trình tự khai DPI-aware: chữ sắc nét ở 125% / 150%); MỘT nút chính (xanh
# thương hiệu) + nút phụ trắng + liên kết văn bản cho việc hiếm / nguy hiểm (Gỡ cài đặt); thẻ trạng thái 4 loại (thông tin, thành công,
# lưu ý, lỗi) có biểu tượng vẽ bằng GDI+ (không dùng emoji - Windows 7 không có phông); phím tắt Alt+chữ gạch dưới, Enter = nút chính,
# Esc = hủy; vòng viền khi nút nhận phím Tab; không hiện tên đơn vị nào (bản thương mại dùng cho nhiều đơn vị).
Add-Type -TypeDefinition @'
using System.Runtime.InteropServices;
public static class PabtDpi { [DllImport("user32.dll")] public static extern bool SetProcessDPIAware(); }
'@
try { [void][PabtDpi]::SetProcessDPIAware() } catch { }
$f = New-Object System.Windows.Forms.Form
$f.AutoScaleMode = 'None'
$gx = $f.CreateGraphics(); $script:E = [Math]::Max(1.0, $gx.DpiX / 96.0); $gx.Dispose()     # $script: - chạy qua scriptblock (CAI_DAT.cmd) thì gán thường chỉ ở phạm vi con
function Px($n) { return [int][Math]::Round($n * $script:E) }
$MAU = @{
    Chinh = [System.Drawing.Color]::FromArgb(47, 95, 158);  ChinhRe = [System.Drawing.Color]::FromArgb(38, 78, 131); ChinhNhan = [System.Drawing.Color]::FromArgb(30, 62, 105)
    Chu = [System.Drawing.Color]::FromArgb(15, 23, 42);     ChuPhu = [System.Drawing.Color]::FromArgb(71, 85, 105); ChuMo = [System.Drawing.Color]::FromArgb(100, 116, 139)
    Ke = [System.Drawing.Color]::FromArgb(226, 232, 240);   KeDam = [System.Drawing.Color]::FromArgb(203, 213, 225); Chan = [System.Drawing.Color]::FromArgb(241, 245, 249)
    Nguy = [System.Drawing.Color]::FromArgb(185, 28, 28);   Xam = [System.Drawing.Color]::FromArgb(148, 163, 184); Trang = [System.Drawing.Color]::White
    Ngoc = [System.Drawing.Color]::FromArgb(4, 120, 87)
}
# bốn loại thẻ trạng thái: nền, màu nhấn (biểu tượng), màu tiêu đề
$LOAI_THE = @{
    thong_tin = @([System.Drawing.Color]::FromArgb(239, 246, 255), [System.Drawing.Color]::FromArgb(37, 99, 235),  [System.Drawing.Color]::FromArgb(30, 64, 175))
    thanh_cong = @([System.Drawing.Color]::FromArgb(236, 253, 245), [System.Drawing.Color]::FromArgb(5, 150, 105),  [System.Drawing.Color]::FromArgb(6, 95, 70))
    luu_y = @([System.Drawing.Color]::FromArgb(255, 251, 235), [System.Drawing.Color]::FromArgb(217, 119, 6),  [System.Drawing.Color]::FromArgb(146, 64, 14))
    loi = @([System.Drawing.Color]::FromArgb(254, 242, 242), [System.Drawing.Color]::FromArgb(220, 38, 38),  [System.Drawing.Color]::FromArgb(153, 27, 27))
}
$RONG_CUA_SO = Px 640; $LE = Px 28; $RONG_THAN = $RONG_CUA_SO - 2 * $LE
$f.Text = "Cài đặt $TEN_NGAN $PHIEN_BAN"; $f.ClientSize = New-Object System.Drawing.Size($RONG_CUA_SO, (Px 520))
$f.FormBorderStyle = 'FixedDialog'; $f.MaximizeBox = $false; $f.MinimizeBox = $true; $f.StartPosition = 'CenterScreen'
$f.Font = New-Object System.Drawing.Font('Segoe UI', 9.5); $f.BackColor = $MAU.Trang
$icoF = Join-Path $GOC 'PABT.ico'
if (Test-Path -LiteralPath $icoF) { $f.Icon = New-Object System.Drawing.Icon($icoF) }

function BoGoc($c, $r) {
    $gp = New-Object System.Drawing.Drawing2D.GraphicsPath; $d = 2 * $r
    $gp.AddArc(0, 0, $d, $d, 180, 90); $gp.AddArc(($c.Width - $d), 0, $d, $d, 270, 90)
    $gp.AddArc(($c.Width - $d), ($c.Height - $d), $d, $d, 0, 90); $gp.AddArc(0, ($c.Height - $d), $d, $d, 90, 90)
    $gp.CloseFigure(); $c.Region = New-Object System.Drawing.Region($gp)
}
function NhanChu($text, $co, $dam, $mau) {
    $l = New-Object System.Windows.Forms.Label; $l.Text = $text; $l.AutoSize = $true; $l.UseMnemonic = $false; $l.ForeColor = $mau
    $kieu = [System.Drawing.FontStyle]::Regular; if ($dam) { $kieu = [System.Drawing.FontStyle]::Bold }
    $l.Font = New-Object System.Drawing.Font('Segoe UI', $co, $kieu); $l.BackColor = [System.Drawing.Color]::Transparent
    return $l
}
function HinhTrangThai($loai, $d, $mau) {
    # biểu tượng tròn vẽ bằng GDI+: i (thông tin), dấu tích, ! (lưu ý), x (lỗi)
    $bm = New-Object System.Drawing.Bitmap($d, $d)
    $g = [System.Drawing.Graphics]::FromImage($bm); $g.SmoothingMode = 'AntiAlias'
    $g.FillEllipse((New-Object System.Drawing.SolidBrush($mau)), 0, 0, ($d - 1), ($d - 1))
    $b = [single]($d / 10.0)
    $but = New-Object System.Drawing.Pen([System.Drawing.Color]::White, [single][Math]::Max(1.6, $d / 11.0))
    $but.StartCap = 'Round'; $but.EndCap = 'Round'; $but.LineJoin = 'Round'
    $m = [single]($d / 2.0)
    if ($loai -eq 'thanh_cong') {
        $g.DrawLines($but, [System.Drawing.PointF[]]@((New-Object System.Drawing.PointF(($d * 0.27), ($d * 0.52))), (New-Object System.Drawing.PointF(($d * 0.43), ($d * 0.68))), (New-Object System.Drawing.PointF(($d * 0.74), ($d * 0.34)))))
    } elseif ($loai -eq 'loi') {
        $g.DrawLine($but, ($d * 0.33), ($d * 0.33), ($d * 0.67), ($d * 0.67)); $g.DrawLine($but, ($d * 0.67), ($d * 0.33), ($d * 0.33), ($d * 0.67))
    } elseif ($loai -eq 'luu_y') {
        $g.DrawLine($but, $m, ($d * 0.26), $m, ($d * 0.58)); $g.FillEllipse([System.Drawing.Brushes]::White, ($m - $d * 0.075), ($d * 0.68), ($d * 0.15), ($d * 0.15))
    } else {
        $g.FillEllipse([System.Drawing.Brushes]::White, ($m - $d * 0.075), ($d * 0.2), ($d * 0.15), ($d * 0.15)); $g.DrawLine($but, $m, ($d * 0.43), $m, ($d * 0.76))
    }
    $but.Dispose(); $g.Dispose()
    return $bm
}
function HinhKhien($d, $mau) {
    $bm = New-Object System.Drawing.Bitmap($d, $d)
    $g = [System.Drawing.Graphics]::FromImage($bm); $g.SmoothingMode = 'AntiAlias'
    $p = [System.Drawing.PointF[]]@((New-Object System.Drawing.PointF(($d * 0.5), ($d * 0.05))), (New-Object System.Drawing.PointF(($d * 0.88), ($d * 0.2))),
        (New-Object System.Drawing.PointF(($d * 0.84), ($d * 0.58))), (New-Object System.Drawing.PointF(($d * 0.5), ($d * 0.95))),
        (New-Object System.Drawing.PointF(($d * 0.16), ($d * 0.58))), (New-Object System.Drawing.PointF(($d * 0.12), ($d * 0.2))))
    $g.FillPolygon((New-Object System.Drawing.SolidBrush($mau)), $p)
    $but = New-Object System.Drawing.Pen([System.Drawing.Color]::White, [single][Math]::Max(1.5, $d / 10.0)); $but.StartCap = 'Round'; $but.EndCap = 'Round'; $but.LineJoin = 'Round'
    $g.DrawLines($but, [System.Drawing.PointF[]]@((New-Object System.Drawing.PointF(($d * 0.32), ($d * 0.5))), (New-Object System.Drawing.PointF(($d * 0.46), ($d * 0.64))), (New-Object System.Drawing.PointF(($d * 0.69), ($d * 0.36)))))
    $but.Dispose(); $g.Dispose()
    return $bm
}
function TaoChip($text) {
    $c = New-Object System.Windows.Forms.Label; $c.Text = $text; $c.AutoSize = $false; $c.UseMnemonic = $false
    $c.Font = New-Object System.Drawing.Font('Segoe UI', 8.5); $c.ForeColor = $MAU.ChuPhu; $c.BackColor = $MAU.Chan; $c.TextAlign = 'MiddleCenter'
    $c.Padding = New-Object System.Windows.Forms.Padding((Px 8), (Px 2), (Px 8), (Px 2)); $c.AutoSize = $true
    return $c
}

# ---- banner
$dau = New-Object System.Windows.Forms.Panel; $dau.Dock = 'Top'; $dau.BackColor = $MAU.Trang
$f.Controls.Add($dau)
$KICH_LOGO = Px 72
$anh = New-Object System.Windows.Forms.PictureBox; $anh.Size = New-Object System.Drawing.Size($KICH_LOGO, $KICH_LOGO)
$anh.Location = New-Object System.Drawing.Point($LE, (Px 22)); $anh.SizeMode = 'Zoom'
$png = Join-Path $GOC 'bieu_tuong.png'; if (Test-Path -LiteralPath $png) { $anh.Image = [System.Drawing.Image]::FromFile($png) }
$dau.Controls.Add($anh)
$XCHU = $LE + $KICH_LOGO + (Px 18)
$t1 = NhanChu "Cài đặt $TEN_NGAN" 17 $true $MAU.Chu; $t1.Font = New-Object System.Drawing.Font('Segoe UI Semibold', 17)
$dau.Controls.Add($t1)
$t2 = NhanChu $TEN_DAY_DU 8.5 $false $MAU.ChuPhu; $t2.AutoSize = $true; $t2.MaximumSize = New-Object System.Drawing.Size(($RONG_CUA_SO - $XCHU - $LE), 0)
$dau.Controls.Add($t2)
$chipPb = TaoChip "Phiên bản $PHIEN_BAN"; $chipHe = TaoChip $TEN_BAN
$dau.Controls.Add($chipPb); $dau.Controls.Add($chipHe)
$t1.Location = New-Object System.Drawing.Point($XCHU, (Px 18))
$t2.Location = New-Object System.Drawing.Point(($XCHU + 1), ($t1.Bottom + (Px 1)))
$chipPb.Location = New-Object System.Drawing.Point($XCHU, ($t2.Bottom + (Px 8)))
$chipHe.Location = New-Object System.Drawing.Point(($chipPb.Right + (Px 8)), $chipPb.Top)
BoGoc $chipPb 9; BoGoc $chipHe 9
$dau.Height = [Math]::Max(($anh.Bottom + (Px 22)), ($chipPb.Bottom + (Px 20)))
$vachDau = New-Object System.Windows.Forms.Panel; $vachDau.Dock = 'Bottom'; $vachDau.Height = 1; $vachDau.BackColor = $MAU.Ke; $dau.Controls.Add($vachDau)

# ---- chân cửa sổ: nút
$CAO_NUT = Px 38
$pie = New-Object System.Windows.Forms.Panel; $pie.Dock = 'Bottom'; $pie.BackColor = $MAU.Chan; $pie.Height = $CAO_NUT + 2 * (Px 14) + 1
$f.Controls.Add($pie)
$vachPie = New-Object System.Windows.Forms.Panel; $vachPie.Dock = 'Top'; $vachPie.Height = 1; $vachPie.BackColor = $MAU.Ke; $pie.Controls.Add($vachPie)
$yNut = Px 15
function KieuNutPhu($n) {
    $n.UseCompatibleTextRendering = $true; $n.FlatStyle = 'Flat'; $n.BackColor = $MAU.Trang; $n.ForeColor = $MAU.Chu; $n.Cursor = 'Hand'
    $n.FlatAppearance.BorderColor = $MAU.KeDam; $n.FlatAppearance.BorderSize = 1
    $n.FlatAppearance.MouseOverBackColor = [System.Drawing.Color]::FromArgb(248, 250, 252); $n.FlatAppearance.MouseDownBackColor = $MAU.Ke
    $n.Add_GotFocus({ $this.FlatAppearance.BorderColor = $MAU.Chinh; $this.FlatAppearance.BorderSize = 2 })
    $n.Add_LostFocus({ $this.FlatAppearance.BorderColor = $MAU.KeDam; $this.FlatAppearance.BorderSize = 1 })
}
$bHuy = New-Object System.Windows.Forms.Button; $bHuy.Text = '&Hủy bỏ'; $bHuy.Size = New-Object System.Drawing.Size((Px 112), $CAO_NUT)
$bHuy.Location = New-Object System.Drawing.Point(($RONG_CUA_SO - $LE - $bHuy.Width), $yNut); KieuNutPhu $bHuy
$pie.Controls.Add($bHuy); $f.CancelButton = $bHuy
$bCai = New-Object System.Windows.Forms.Button; $bCai.Size = New-Object System.Drawing.Size((Px 150), $CAO_NUT); $bCai.Top = $yNut
$bCai.UseCompatibleTextRendering = $true; $bCai.FlatStyle = 'Flat'; $bCai.BackColor = $MAU.Chinh; $bCai.ForeColor = $MAU.Trang; $bCai.Cursor = 'Hand'
$bCai.FlatAppearance.BorderSize = 0; $bCai.FlatAppearance.MouseOverBackColor = $MAU.ChinhRe; $bCai.FlatAppearance.MouseDownBackColor = $MAU.ChinhNhan
$bCai.Font = New-Object System.Drawing.Font('Segoe UI Semibold', 10.5)
$bCai.Add_GotFocus({ $this.FlatAppearance.BorderColor = $MAU.ChinhNhan; $this.FlatAppearance.BorderSize = 2 })
$bCai.Add_LostFocus({ $this.FlatAppearance.BorderSize = 0 })
$pie.Controls.Add($bCai); $f.AcceptButton = $bCai
# liên kết văn bản góc trái chân: việc ít dùng / nguy hiểm không tranh nút chính
$bXoa = New-Object System.Windows.Forms.Button; $bXoa.Text = '&Gỡ cài đặt…'; $bXoa.Size = New-Object System.Drawing.Size((Px 130), $CAO_NUT)
$bXoa.Location = New-Object System.Drawing.Point(($LE - (Px 8)), $yNut); $bXoa.Visible = $false
$bXoa.UseCompatibleTextRendering = $true; $bXoa.FlatStyle = 'Flat'; $bXoa.BackColor = $MAU.Chan; $bXoa.ForeColor = $MAU.Nguy; $bXoa.Cursor = 'Hand'
$bXoa.FlatAppearance.BorderSize = 0; $bXoa.FlatAppearance.MouseOverBackColor = [System.Drawing.Color]::FromArgb(254, 226, 226)
$bXoa.Add_GotFocus({ $this.FlatAppearance.BorderColor = $MAU.Nguy; $this.FlatAppearance.BorderSize = 2 }); $bXoa.Add_LostFocus({ $this.FlatAppearance.BorderSize = 0 })
$pie.Controls.Add($bXoa)
$lkNk = New-Object System.Windows.Forms.LinkLabel; $lkNk.Text = 'Xem nhật ký cài đặt'; $lkNk.AutoSize = $true; $lkNk.Visible = $false; $lkNk.UseMnemonic = $false
$lkNk.LinkColor = $MAU.Chinh; $lkNk.ActiveLinkColor = $MAU.ChinhNhan; $lkNk.BackColor = $MAU.Chan; $lkNk.Font = New-Object System.Drawing.Font('Segoe UI', 9)
$lkNk.Location = New-Object System.Drawing.Point($LE, ($yNut + [int](($CAO_NUT - $lkNk.PreferredHeight) / 2)))
$lkNk.Add_LinkClicked({ try { Start-Process notepad.exe -ArgumentList "`"$nk`"" } catch { } })
$pie.Controls.Add($lkNk)

# ---- thân: vị trí cài đặt
$y = $dau.Height + 1 + (Px 20)
$l1 = NhanChu 'Vị trí cài đặt' 9.5 $true $MAU.Chu; $l1.Location = New-Object System.Drawing.Point($LE, $y); $f.Controls.Add($l1)
$bChon = New-Object System.Windows.Forms.Button; $bChon.Text = 'Chọn &thư mục…'; $bChon.Width = Px 124; $bChon.Height = Px 30
$bChon.Location = New-Object System.Drawing.Point(($LE + $RONG_THAN - $bChon.Width), ($y + (Px 24))); KieuNutPhu $bChon; $f.Controls.Add($bChon)
$oThu = New-Object System.Windows.Forms.TextBox; $oThu.Font = New-Object System.Drawing.Font('Segoe UI', 10)
$oThu.Location = New-Object System.Drawing.Point($LE, ($y + (Px 25))); $oThu.Width = $RONG_THAN - $bChon.Width - (Px 8)
$oThu.Text = $ThuMuc
if (-not $ThuMuc) { $oThu.Text = $MAC_DINH }
$oThu.AccessibleName = 'Thư mục cài đặt'; $f.Controls.Add($oThu)
$bChon.Height = $oThu.Height; $bChon.Top = $oThu.Top
$lbDung = NhanChu '' 8.5 $false $MAU.ChuMo; $lbDung.Location = New-Object System.Drawing.Point(($LE + 1), ($oThu.Bottom + (Px 5))); $f.Controls.Add($lbDung)
function DungLuongCan {
    # tổng cỡ file trong danh sách cài (MB); -1 = không đọc được
    try {
        $tong = [long]0
        foreach ($d in [System.IO.File]::ReadAllLines((Join-Path $GOC $DANH_SACH), [System.Text.Encoding]::UTF8)) {
            $x = $d.Split("`t"); if ($x.Count -ge 4) { $tong += [long]$x[2] }
        }
        return [int][Math]::Ceiling($tong / 1MB)
    } catch { return -1 }
}
$script:MB_CAN = DungLuongCan
function CapNhatDungLuong {
    $chu = ''
    if ($script:MB_CAN -gt 0) { $chu = "Cần khoảng $($script:MB_CAN) MB trống" }
    try {
        $goc = [System.IO.Path]::GetPathRoot([System.IO.Path]::GetFullPath($oThu.Text))
        if ($goc -and -not $goc.StartsWith('\\')) {
            $o = New-Object System.IO.DriveInfo($goc)
            $trong = [Math]::Round($o.AvailableFreeSpace / 1GB, 1)
            $chu += $(if ($chu) { ' · ' } else { '' }) + "Ổ $($goc.Substring(0, 2)) còn trống $trong GB"
        }
    } catch { }
    $lbDung.Text = $chu
}
CapNhatDungLuong
$oThu.Add_TextChanged({ CapNhatDungLuong })

# ---- tùy chọn
$y2 = $lbDung.Bottom + (Px 18)
$l2 = NhanChu 'Tùy chọn' 9.5 $true $MAU.Chu; $l2.Location = New-Object System.Drawing.Point($LE, $y2); $f.Controls.Add($l2)
$cDesk = New-Object System.Windows.Forms.CheckBox; $cDesk.Text = "Tạo biểu tượng $TEN_NGAN trên màn hình &Desktop"; $cDesk.Checked = -not $KhongDesktop
$cDesk.Location = New-Object System.Drawing.Point(($LE + 1), ($l2.Bottom + (Px 6))); $cDesk.AutoSize = $true; $cDesk.FlatStyle = 'System'; $f.Controls.Add($cDesk)
$cLk = New-Object System.Windows.Forms.CheckBox; $cLk.Text = "Dùng $TEN_NGAN để mở file dự án (.larc) khi nhấp đúp"; $cLk.Checked = -not $KhongLienKet
$cLk.Location = New-Object System.Drawing.Point(($LE + 1), ($cDesk.Bottom + (Px 4))); $cLk.AutoSize = $true; $cLk.FlatStyle = 'System'; $f.Controls.Add($cLk)
$cVc = New-Object System.Windows.Forms.CheckBox; $cVc.AutoSize = $true; $cVc.FlatStyle = 'System'
$cVc.Location = New-Object System.Drawing.Point(($LE + 1), ($cLk.Bottom + (Px 4)))
if (-not $CO_VC) { $cVc.Text = "Thư viện Visual C++: đóng gói sẵn, không cần cài thêm"; $cVc.Checked = $false; $cVc.Enabled = $false }
elseif (CoVcRedist) { $cVc.Text = "Microsoft Visual C++ Redistributable ($KIEN): máy đã có"; $cVc.Checked = $false; $cVc.Enabled = $false }
else { $cVc.Text = "Cài Microsoft Visual C++ Redistributable ($KIEN) - cần quyền quản trị"; $cVc.Checked = $true }
# Windows 7 thiếu KB2533623 (bộ cài Win7-8 kèm KB3063858): dòng này thành ô cài bản cập nhật Windows (Visual C++ đã đóng sẵn)
$script:O_LA_KB = $false
if ((ThieuKbWin7) -and (Test-Path -LiteralPath $KB)) {
    $cVc.Text = "Cài bản cập nhật Windows 7 KB3063858 ($TEN_NGAN cần) - hỏi quyền quản trị, khởi động lại máy sau khi cài"
    $cVc.Checked = $true; $cVc.Enabled = $true; $script:O_LA_KB = $true
}
$script:HIEN_VC = $cVc.Enabled; $script:HIEN_PB = $false      # cờ riêng: Visible của control con trả False khi cửa sổ chưa hiện
$cVc.Visible = $cVc.Enabled                    # dòng chỉ để báo "không cần cài thêm" (ô khóa) ẩn đi - chỉ hiện khi có việc cho người dùng chọn
$f.Controls.Add($cVc)

# ---- thẻ trạng thái (một thẻ, bốn loại) + tiến trình + dòng bảo vệ dữ liệu
$the = New-Object System.Windows.Forms.Panel; $the.Width = $RONG_THAN; $f.Controls.Add($the)
$anhThe = New-Object System.Windows.Forms.PictureBox; $anhThe.Size = New-Object System.Drawing.Size((Px 28), (Px 28)); $anhThe.Location = New-Object System.Drawing.Point((Px 16), (Px 16)); $anhThe.SizeMode = 'Normal'
$the.Controls.Add($anhThe)
$tdThe = NhanChu '' 10 $true $MAU.Chu; $tdThe.Location = New-Object System.Drawing.Point((Px 56), (Px 14)); $the.Controls.Add($tdThe)
$tt = NhanChu '' 9.5 $false $MAU.Chu
$tt.MaximumSize = New-Object System.Drawing.Size(($RONG_THAN - (Px 56) - (Px 16)), 0); $the.Controls.Add($tt)
$pb = New-Object System.Windows.Forms.ProgressBar; $pb.Style = 'Continuous'; $pb.Size = New-Object System.Drawing.Size($RONG_THAN, (Px 8)); $pb.Visible = $false
$f.Controls.Add($pb)
$lbPhanTram = NhanChu '' 8.5 $false $MAU.ChuMo; $lbPhanTram.Visible = $false; $f.Controls.Add($lbPhanTram)
$hKhien = HinhKhien (Px 18) $MAU.Ngoc
$anhKhien = New-Object System.Windows.Forms.PictureBox; $anhKhien.Image = $hKhien; $anhKhien.SizeMode = 'Normal'; $anhKhien.Size = New-Object System.Drawing.Size((Px 18), (Px 18)); $f.Controls.Add($anhKhien)
$lbAn = NhanChu "Dự án (.larc, .pabt) và file Excel của bạn luôn được giữ nguyên khi cài, nâng cấp hoặc gỡ cài đặt." 8.5 $false $MAU.Ngoc
$lbAn.MaximumSize = New-Object System.Drawing.Size(($RONG_THAN - (Px 26)), 0); $f.Controls.Add($lbAn)

function BoCuc {
    # đặt lại vị trí các khối dưới thẻ và chiều cao cửa sổ theo chữ trong thẻ
    $cao = [Math]::Max((Px 100), $tt.Bottom + (Px 16))       # cao tối thiểu 3 dòng chữ: cửa sổ không nhảy chiều cao giữa các trạng thái
    $the.Height = $cao
    $the.Top = $(if ($script:HIEN_VC) { $cVc.Bottom } else { $cLk.Bottom }) + (Px 18)
    $the.Left = $LE
    BoGoc $the 8
    $yD = $the.Bottom + (Px 10)
    $pb.Location = New-Object System.Drawing.Point($LE, $yD)                # chỗ thanh tiến trình luôn được giữ (chỉ ẩn / hiện)
    $lbPhanTram.Location = New-Object System.Drawing.Point(($LE + $RONG_THAN - $lbPhanTram.PreferredWidth), ($yD + (Px 12)))
    $yD = $pb.Bottom + (Px 12)
    $anhKhien.Location = New-Object System.Drawing.Point($LE, ($yD + (Px 1)))
    $lbAn.Location = New-Object System.Drawing.Point(($LE + (Px 26)), $yD)
    $caoTong = [Math]::Max($lbAn.Bottom, $anhKhien.Bottom) + (Px 20) + $pie.Height
    if ($f.ClientSize.Height -ne $caoTong) { $f.ClientSize = New-Object System.Drawing.Size($RONG_CUA_SO, $caoTong) }
}
function DatThe($loai, $tieuDe, $noiDung) {
    # loai: thong_tin / thanh_cong / luu_y / loi
    $m = $LOAI_THE[$loai]
    $the.BackColor = $m[0]; $tdThe.BackColor = $m[0]; $tt.BackColor = $m[0]
    $tdThe.ForeColor = $m[2]; $tt.ForeColor = $MAU.Chu
    $tdThe.Text = $tieuDe; $tt.Text = $noiDung
    $tt.Location = New-Object System.Drawing.Point((Px 56), ($tdThe.Bottom + (Px 2)))
    if ($anhThe.Image) { $anhThe.Image.Dispose() }
    $anhThe.Image = HinhTrangThai $loai (Px 28) $m[1]
    BoCuc
}
function DatNutCai($che) {
    # che: 'cai' (Cài đặt) / 'lai' (Nâng cấp, khi đã có bản cũ) / 'mo' (Mở sau khi cài); nút chính canh phải, cạnh Hủy bỏ
    $script:CHE_DO = $che
    if ($che -eq 'lai') { $bCai.Text = "&Nâng cấp lên $PHIEN_BAN"; $bCai.Width = Px 210 }
    elseif ($che -eq 'mo') { $bCai.Text = "&Mở $TEN_NGAN"; $bCai.Width = Px 150 }
    else { $bCai.Text = '&Cài đặt'; $bCai.Width = Px 150 }
    $bCai.Left = $bHuy.Left - (Px 10) - $bCai.Width
}
DatNutCai 'cai'
$bHuy.DialogResult = [System.Windows.Forms.DialogResult]::Cancel   # đóng bằng cơ chế sẵn của hộp thoại
# sau khi cài, ô thư mục đang giữ tiêu điểm đã bị khóa nên WinForms bỏ sự kiện Click của nút: tự đóng khi nhả chuột trên nút
$bHuy.Add_MouseUp({ if ($_.Button -eq 'Left' -and $this.Enabled -and $this.ClientRectangle.Contains($_.Location)) {
    $this.FindForm().DialogResult = [System.Windows.Forms.DialogResult]::Cancel } })
$bChon.Add_Click({
    $d = New-Object System.Windows.Forms.FolderBrowserDialog
    $d.Description = 'Chọn thư mục chứa chương trình'
    if ($d.ShowDialog() -eq 'OK') {
        $oThu.Text = Join-Path $d.SelectedPath 'PABT'
        if (-not (GhiDuoc $oThu.Text)) {
            DatThe 'luu_y' 'Thư mục hệ thống của Windows' "Khi bấm `"Cài đặt`", Windows sẽ hỏi quyền quản trị để chép file $TEN_NGAN vào đây." }
        else { DatThe 'thong_tin' 'Sẵn sàng cài đặt' "Cài vào $($oThu.Text). Bấm `"Cài đặt`" để bắt đầu." }
        CapNhatNutCu
    } })
$loi = KiemTraMay
if ($loi) {
    DatThe 'loi' 'Máy chưa đạt yêu cầu' $loi; $bCai.Enabled = $false
    $bCai.BackColor = $MAU.Xam                  # nút phẳng: tự tô xám khi khóa
}
else {
    $nd = "Máy đạt yêu cầu (Windows $([Environment]::OSVersion.Version.Major).$([Environment]::OSVersion.Version.Minor) $BIT). Bấm `"Cài đặt`" để bắt đầu."
    if (-not (GhiDuoc $oThu.Text)) { $nd += ' Windows sẽ hỏi quyền quản trị để chép file vào Program Files - chọn Có (Yes).' }
    DatThe 'thong_tin' 'Sẵn sàng cài đặt' $nd
    $cb = CanhBaoMay
    if ($cb) { Ghi "LƯU Ý: $cb"; DatThe 'luu_y' 'Lưu ý' $cb }
}
function CoBanCu($dich) {
    if (-not $dich) { return $false }
    return (Test-Path -LiteralPath (Join-Path $dich.TrimEnd('\') 'PABT.exe'))
}
function CapNhatNutCu {
    # Đã có PABT.exe trong thư mục đang chọn: Nâng cấp = đóng bản đang chạy rồi chép đè; Gỡ cài đặt = gỡ bản cũ.
    if ($script:xong) { return }
    $co = CoBanCu $oThu.Text
    $bXoa.Visible = $co
    $bXoa.Enabled = $co
    if ($co) {
        DatNutCai 'lai'
        DatThe 'thong_tin' 'Đã có phiên bản cũ' ("Tìm thấy $TEN_NGAN đã cài tại $($oThu.Text).`r`nBấm `"Nâng cấp`" để cài bản $PHIEN_BAN đè lên bản cũ (khuyên dùng).")
    } elseif ($script:CHE_DO -eq 'lai') { DatNutCai 'cai' }
}
if (-not $loi) { CapNhatNutCu }
$script:xong = $false
$tienDo = { param($phan, $chu)
    $script:HIEN_PB = $true; $pb.Visible = $true; $pb.Value = [Math]::Min(100, [Math]::Max(0, $phan)); $lbPhanTram.Visible = $true; $lbPhanTram.Text = "$([Math]::Min(100, $phan))%"
    DatThe 'thong_tin' 'Đang cài đặt' $chu
    [System.Windows.Forms.Application]::DoEvents() }
$bCai.Add_Click({
    if ($script:xong) { Start-Process (Join-Path $oThu.Text 'PABT.exe'); $this.FindForm().DialogResult = 'OK'; return }
    $laMacDinh = $oThu.Text.TrimEnd('\') -eq $MAC_DINH.TrimEnd('\')
    if (-not $laMacDinh -and -not (GhiDuoc $oThu.Text)) {    # thư mục hệ thống khác do người dùng chọn: hỏi trước
        $hoi = [System.Windows.Forms.MessageBox]::Show($f, ("Thư mục $($oThu.Text) là thư mục hệ thống của Windows: Windows sẽ " +
            "hỏi quyền quản trị (tài khoản quản trị) để chép file $TEN_NGAN vào đây.`r`n`r`n" +
            "Có (Yes): cài vào thư mục này`r`nKhông (No): cài vào $KHONG_QT (không cần quyền quản trị)`r`nHủy (Cancel): chọn lại"),
            "Cài đặt $TEN_NGAN", 'YesNoCancel', 'Question')
        if ($hoi -eq 'Cancel') { return }
        if ($hoi -eq 'No') { $oThu.Text = $KHONG_QT }
    }
    $bCai.Enabled = $false; $bHuy.Enabled = $false; $bChon.Enabled = $false; $oThu.Enabled = $false; $bXoa.Enabled = $false
    $cDesk.Enabled = $false; $cLk.Enabled = $false; $cVc.Enabled = $false
    try {
        if ($script:O_LA_KB) {
            if ($cVc.Checked) { & $tienDo 3 'Cài bản cập nhật Windows 7 KB3063858 (Windows hỏi quyền quản trị, có thể mất vài phút)…'
                                $kb = CaiKbWin7 }
        } elseif ($cVc.Checked) { & $tienDo 3 'Cài Microsoft Visual C++ Redistributable (có thể hỏi quyền quản trị)…'; $vc = CaiVcRedist }
        $chuCai = "Đang cài $TEN_NGAN…"
        if ($script:CHE_DO -eq 'lai') { $chuCai = "Đang đóng $TEN_NGAN đang chạy và cài bản mới đè lên bản cũ…" }
        & $tienDo 8 $chuCai
        $tk = Cai $oThu.Text $cDesk.Checked $cLk.Checked $tienDo
        & $tienDo 100 'Hoàn tất.'
        $them = ''
        if ($script:LOI_TAT.Count -gt 0) { $them = " Chưa tạo được lối tắt ($($script:LOI_TAT -join ', ')): mở PABT.exe trong thư mục cài." }
        if ($tk -match 'KET QUA: DAT') {
            DatThe 'thanh_cong' "Đã cài đặt xong $TEN_NGAN $PHIEN_BAN" "Tự kiểm tra đạt: giao diện, PDF, bộ đơn giá, mẫu in, bảng giá đất.$them"
        } else {
            $nd = "Đã cài nhưng tự kiểm tra chưa đạt. Xem nhật ký để biết chi tiết: $nk"
            $cb = CanhBaoMay; if ($cb) { $nd = "Đã cài. $cb" }
            DatThe 'luu_y' 'Đã cài, cần xem lại' $nd
        }
        $script:HIEN_PB = $false; $pb.Visible = $false; $lbPhanTram.Visible = $false; BoCuc
        DatNutCai 'mo'; $bCai.Enabled = $true; $bHuy.Text = '&Đóng'; $bHuy.Enabled = $true; $script:xong = $true; $bXoa.Visible = $false; $lkNk.Visible = $true
        if ($script:KB_CHO_KHOI_DONG) {             # bản cập nhật Windows có hiệu lực sau khi khởi động lại: chưa mở được
            DatThe 'luu_y' 'Cần khởi động lại máy' "Đã cài $TEN_NGAN $PHIEN_BAN và bản cập nhật Windows 7 KB3063858. Khởi động lại máy rồi mở $TEN_NGAN (biểu tượng $TEN_NGAN)."
            $bCai.Visible = $false
        }
        $f.ActiveControl = $bCai
    } catch {
        Ghi "LỖI: $_"
        $script:HIEN_PB = $false; $pb.Visible = $false; $pb.Value = 0; $lbPhanTram.Visible = $false
        DatThe 'loi' 'Không cài được' "$_`r`nNhật ký: $nk"
        $bHuy.Text = '&Đóng'; $bHuy.Enabled = $true; $lkNk.Visible = $true
        # mở lại để chọn thư mục khác rồi cài tiếp (trước đây khóa luôn - phải đóng bộ cài chạy lại)
        $bCai.Enabled = $true; $bChon.Enabled = $true; $oThu.Enabled = $true
        $cDesk.Enabled = $true; $cLk.Enabled = $true; $cVc.Enabled = $script:HIEN_VC
        CapNhatNutCu
        if ($bXoa.Visible) { DatThe 'loi' 'Không cài đè được' "$_`r`nBấm `"Nâng cấp`" để thử lại, hoặc `"Gỡ cài đặt`" để gỡ bản cũ. Nhật ký: $nk" }
        if ($script:TU_CHOI) {                      # từ chối UAC: chuyển sẵn sang thư mục không cần quyền quản trị
            $script:TU_CHOI = $false
            $oThu.Text = $KHONG_QT
            CapNhatNutCu
            DatThe 'luu_y' 'Chưa được cấp quyền quản trị' ("Đã chuyển thư mục cài sang $KHONG_QT (không cần quyền quản trị): bấm `"Cài đặt`" để cài tiếp, " +
                'hoặc bấm "Chọn thư mục…" chọn lại Program Files rồi chọn Có khi Windows hỏi.')
        }
    }
})
$bXoa.Add_Click({
    if (-not (CoBanCu $oThu.Text)) { CapNhatNutCu; return }
    $hoi = [System.Windows.Forms.MessageBox]::Show($f, ("Gỡ cài đặt $TEN_NGAN trong`r`n$($oThu.Text)?`r`n`r`n" +
        'Gỡ chương trình, biểu tượng và liên kết file. File dự án .larc / .pabt của bạn được giữ nguyên.'),
        "Gỡ cài đặt $TEN_NGAN", 'YesNo', 'Question')
    if ($hoi -ne 'Yes') { return }
    $bCai.Enabled = $false; $bXoa.Enabled = $false; $bHuy.Enabled = $false; $bChon.Enabled = $false; $oThu.Enabled = $false
    DatThe 'thong_tin' "Đang gỡ $TEN_NGAN" 'Đang đóng chương trình và xóa bản cài cũ… Nếu Windows hỏi quyền quản trị, chọn Có (Yes).'
    [System.Windows.Forms.Application]::DoEvents()
    try {
        $ps = Join-Path $GOC 'go_cai_dat.ps1'
        $lenh = "& ([scriptblock]::Create([IO.File]::ReadAllText('" + $ps.Replace("'", "''") + "', [Text.Encoding]::UTF8))) -Im -Dich '" +
                $oThu.Text.Replace("'", "''") + "'"
        $pr = Start-Process "$env:SystemRoot\System32\WindowsPowerShell\v1.0\powershell.exe" -Wait -PassThru -WindowStyle Hidden `
              -ArgumentList '-NoProfile', '-ExecutionPolicy', 'Bypass', '-STA', '-WindowStyle', 'Hidden', '-Command', $lenh
        if (CoBanCu $oThu.Text) {
            DatThe 'loi' 'Chưa gỡ hết' "Chưa xóa hết thư mục $($oThu.Text) (mã $($pr.ExitCode)). Đóng $TEN_NGAN nếu vẫn đang chạy, chọn Có khi Windows hỏi quyền, rồi bấm `"Gỡ cài đặt`" lại."
        } else {
            DatThe 'thanh_cong' "Đã gỡ $TEN_NGAN" "Đã xóa cài đặt trong $($oThu.Text). File dự án .larc / .pabt được giữ. Bấm `"Cài đặt`" nếu muốn cài bản $PHIEN_BAN."
        }
    } catch {
        Ghi "LỖI gỡ: $_"
        DatThe 'loi' 'Không gỡ được' "$_"
    }
    $bCai.Enabled = $true; $bHuy.Enabled = $true; $bChon.Enabled = $true; $oThu.Enabled = $true
    CapNhatNutCu
})
# thứ tự Tab: thư mục -> Chọn -> tùy chọn -> Cài đặt -> Hủy -> Gỡ
$oThu.TabIndex = 0; $bChon.TabIndex = 1; $cDesk.TabIndex = 2; $cLk.TabIndex = 3; $cVc.TabIndex = 4; $bCai.TabIndex = 5; $bHuy.TabIndex = 6; $bXoa.TabIndex = 7; $lkNk.TabIndex = 8
$bCai.AccessibleName = 'Cài đặt'; $bHuy.AccessibleName = 'Hủy bỏ'; $bChon.AccessibleName = 'Chọn thư mục cài đặt'
BoCuc
# chụp ảnh cửa sổ ra file PNG để duyệt giao diện (PABT_CHUP_CUA_SO = đường dẫn .png; PABT_CHUP_TRANG_THAI = tien_do / xong / loi)
if ($env:PABT_CHUP_CUA_SO) {
    switch ($env:PABT_CHUP_TRANG_THAI) {
        'tien_do' { & $tienDo 56 'Đang chép file (120/218)…' }
        'xong' { DatThe 'thanh_cong' "Đã cài đặt xong $TEN_NGAN $PHIEN_BAN" 'Tự kiểm tra đạt: giao diện, PDF, bộ đơn giá, mẫu in, bảng giá đất.'; DatNutCai 'mo'; $bHuy.Text = '&Đóng'; $lkNk.Visible = $true }
        'loi' { DatThe 'loi' 'Không cài được' "Chép thiếu / hỏng 2 file, ví dụ PySide6\Qt6Core.dll. Thường do phần mềm diệt virus chặn hoặc ổ đĩa đầy.`r`nNhật ký: $nk"; $lkNk.Visible = $true }
        'lai' { $bXoa.Visible = $true; DatNutCai 'lai'; DatThe 'thong_tin' 'Đã có phiên bản cũ' "Tìm thấy $TEN_NGAN đã cài tại $($oThu.Text).`r`nBấm `"Nâng cấp`" để cài bản $PHIEN_BAN đè lên bản cũ (khuyên dùng)." }
    }
    BoCuc
    $f.ActiveControl = $bCai; $f.Show(); [System.Windows.Forms.Application]::DoEvents()
    $bm = New-Object System.Drawing.Bitmap($f.Width, $f.Height); $f.DrawToBitmap($bm, (New-Object System.Drawing.Rectangle(0, 0, $f.Width, $f.Height)))
    $bm.Save($env:PABT_CHUP_CUA_SO, [System.Drawing.Imaging.ImageFormat]::Png); $bm.Dispose(); $f.Close(); exit 0
}
$oThu.SelectionStart = $oThu.Text.Length; $oThu.SelectionLength = 0
$f.ActiveControl = $bCai
[void]$f.ShowDialog()
exit 0

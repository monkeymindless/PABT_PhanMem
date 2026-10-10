# Trình cài PABT cho người dùng hiện tại - MỘT tiêu chuẩn cho cả hai bộ cài (ban.txt: win10 / win7) và gói .zip dự phòng:
#   - chạy qua CAI_DAT.cmd: PowerShell -Command đọc script này thành khối lệnh (không bị chính sách ExecutionPolicy /
#     Group Policy chặn như -File), PowerShell 2.0 (Windows 7) trở lên, -STA;
#   - cài cho người dùng hiện tại (%LOCALAPPDATA%\Programs\PABT), KHÔNG cần quyền quản trị, KHÔNG cài thêm gì vào Windows:
#     mọi thư viện (Visual C++, UCRT cho Windows 7) đã nằm trong bản dựng (bo_cai_win\rut_gon.kiem_dll kiểm khi dựng);
#   - chép file theo danh_sach.txt (nguồn, đích, cỡ, SHA-256), kiểm lại từng file sau khi chép (bị diệt virus chặn / ổ đầy
#     -> báo rõ file nào) - không giải nén zip (không phụ thuộc Shell.Application / .NET 4.5).
#   Không tham số: cửa sổ cài đặt (chọn thư mục, tùy chọn, thanh tiến trình, tự kiểm tra sau khi cài).
#   -Im          cài im lặng (không hỏi, không mở phần mềm sau khi cài)
#   -ThuMuc X    thư mục cài (mặc định %LOCALAPPDATA%\Programs\PABT)
#   -KhongDesktop / -KhongLienKet   bỏ biểu tượng Desktop / không gắn file .pabt
# Bộ cài win10 = Windows 10 1809 (build 17763) trở lên, 64-bit. Bộ cài win7 (32-bit) = mọi Windows từ 7 SP1: 7, 8, 8.1, 10 / 11
# (32 hoặc 64-bit) - dùng khi bộ cài win10 không hợp. Không dùng lệnh của PowerShell 3+.
param([switch]$Im, [string]$ThuMuc = '', [switch]$KhongDesktop, [switch]$KhongLienKet)
$ErrorActionPreference = 'Stop'
$GOC = $env:PABT_GOC                                # CAI_DAT.cmd đặt; chạy thẳng bằng -File thì lấy theo đường dẫn script
if (-not $GOC) { $GOC = Split-Path -Parent $MyInvocation.MyCommand.Definition }     # PowerShell 2.0 chưa có $PSScriptRoot
$GOC = $GOC.TrimEnd('\')
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
[System.Windows.Forms.Application]::EnableVisualStyles()
$TEN = 'PABT - Lập phương án bồi thường, hỗ trợ'
$TEN_DAY_DU = 'PHẦN MỀM LẬP PHƯƠNG ÁN BỒI THƯỜNG, HỖ TRỢ, TÁI ĐỊNH CƯ'
$PHIEN_BAN = [System.IO.File]::ReadAllText((Join-Path $GOC 'phien_ban.txt')).Trim()
$BAN = 'win10'
if (Test-Path -LiteralPath (Join-Path $GOC 'ban.txt')) { $BAN = [System.IO.File]::ReadAllText((Join-Path $GOC 'ban.txt')).Trim() }
$TEN_BAN = 'Windows 10 / 11'
if ($BAN -eq 'win7') { $TEN_BAN = 'Windows 7 / 8' }
$KIEN = 'x64'                                   # kiến trúc chương trình và bộ Visual C++ kèm theo
if ($BAN -eq 'win7') { $KIEN = 'x86' }
$MAY64 = ($env:PROCESSOR_ARCHITECTURE -eq 'AMD64' -or $env:PROCESSOR_ARCHITEW6432 -eq 'AMD64')
$BIT = '32-bit'
if ($MAY64) { $BIT = '64-bit' }
$VC = Join-Path $GOC 'vc_redist.exe'
$CO_VC = Test-Path -LiteralPath $VC                          # bộ cài Win10-11 không kèm Visual C++ Redistributable
$nk =Join-Path $env:TEMP 'pabt_cai_dat.log'
function Ghi($s) { Add-Content -Path $nk -Value ("{0:HH:mm:ss} {1}" -f (Get-Date), $s) -Encoding UTF8 }
Set-Content -Path $nk -Value "Cài PABT $PHIEN_BAN" -Encoding UTF8

# ---------------------------------------------------------------- kiểm tra hệ thống
Ghi "Bộ cài: $TEN_BAN ($BAN)"

function KiemTraMay {
    # điều kiện BẮT BUỘC (không đạt thì không cài): trả câu báo, '' = đạt
    $v = [Environment]::OSVersion.Version
    if ($v.Major -lt 6 -or ($v.Major -eq 6 -and $v.Minor -lt 1)) {
        return "PABT cần Windows 7 SP1 trở lên (máy này: Windows $($v.Major).$($v.Minor))." }
    if ($v.Major -eq 6 -and $v.Minor -eq 1 -and $v.Build -lt 7601) {
        return 'Windows 7 cần cài Service Pack 1 (SP1) trước khi cài PABT.' }
    if ($BAN -eq 'win10') {
        $khac = "dùng bộ cài PABT_CaiDat_$($PHIEN_BAN)_Win7-8.exe (chạy được trên mọi Windows từ 7 SP1)."
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
        return "Máy Windows 10 / 11 64-bit: bộ cài PABT_CaiDat_$($PHIEN_BAN)_Win10-11.exe chạy nhanh hơn; bộ cài này vẫn cài và chạy được." }
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
    foreach ($d in [System.IO.File]::ReadAllLines((Join-Path $GOC 'danh_sach.txt'), [System.Text.Encoding]::UTF8)) {
        $x = $d.Split("`t")
        if ($x.Count -ge 4) { $ds += , @($x[0], $x[1], [long]$x[2], $x[3]) }
    }
    if ($ds.Count -eq 0) { throw 'Bộ cài thiếu danh sách file (danh_sach.txt): tải lại bộ cài.' }
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
    public static void Tao(string lnk, string dich, string thuMuc, string bieuTuong, string moTa) {
        IShellLinkW l = (IShellLinkW)new ShellLink();
        l.SetPath(dich);
        l.SetWorkingDirectory(thuMuc);
        l.SetIconLocation(bieuTuong, 0);
        l.SetDescription(moTa);
        ((IPersistFile)l).Save(lnk, true);
        Marshal.ReleaseComObject(l);
    }
}
'@

function TaoLoiTat($lnk, $exe, $thu, $ico) {
    # trả đường dẫn lối tắt đã tạo, hoặc '' nếu không tạo được (không làm hỏng lần cài)
    try {
        if (-not ('PabtLoiTat' -as [type])) { Add-Type -TypeDefinition $LOI_TAT_CS }
        [PabtLoiTat]::Tao($lnk, $exe, $thu, $ico, $TEN)
        if (Test-Path -LiteralPath $lnk) { return $lnk }
    } catch { Ghi "Lối tắt (IShellLinkW) lỗi: $_" }
    try {                                       # dự phòng: WScript.Shell với tên không dấu
        $p = Join-Path (Split-Path $lnk) 'PABT.lnk'
        $l = (New-Object -ComObject WScript.Shell).CreateShortcut($p)
        $l.TargetPath = $exe; $l.WorkingDirectory = $thu; $l.IconLocation = "$ico,0"; $l.Description = 'PABT'
        $l.Save()
        return $p
    } catch { Ghi "Lối tắt (WScript) lỗi: $_" }
    return ''
}

# ---------------------------------------------------------------- cài
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
            Where-Object { -not $_.PSIsContainer -and ($_.Extension -eq '.pabt' -or $_.Extension -eq '.pabtdt') })
    if ($da.Count -gt 0) {
        throw "Thư mục cài có $($da.Count) file dự án (ví dụ $($da[0].FullName)). Chuyển các file dự án ra thư mục khác rồi cài lại." }
}

function Cai($dich, $desktop, $lienKet, $tienDo) {
    $dich = [System.IO.Path]::GetFullPath($dich)
    Ghi "Thư mục cài: $dich"
    KiemTraThuMuc $dich
    Get-Process PABT -ErrorAction SilentlyContinue | Where-Object { $_.Path -and $_.Path.StartsWith($dich, 'OrdinalIgnoreCase') } |
        Stop-Process -Force
    if (Test-Path -LiteralPath $dich) { Remove-Item -LiteralPath $dich -Recurse -Force; Ghi 'Đã gỡ bản cũ' }
    [void][System.IO.Directory]::CreateDirectory($dich)
    ChepFile $dich $tienDo | Out-Null
    [System.IO.File]::Copy((Join-Path $GOC 'go_cai_dat.ps1'), (Join-Path $dich 'go_cai_dat.ps1'), $true)
    Ghi "Đã chép $(DemFile $dich) file (PowerShell $($PSVersionTable.PSVersion), Windows $([Environment]::OSVersion.Version))"
    if ($tienDo) { & $tienDo 88 'Tạo biểu tượng, liên kết file…' }
    $exe = Join-Path $dich 'PABT.exe'
    $ico = Join-Path $dich 'PABT.ico'
    if (-not (Test-Path -LiteralPath $ico)) { $ico = $exe }
    $lnk = @((Join-Path ([Environment]::GetFolderPath('Programs')) 'PABT - Lập phương án bồi thường.lnk'))
    $dk = Join-Path ([Environment]::GetFolderPath('Desktop')) 'PABT.lnk'
    if ($desktop) { $lnk += $dk } elseif (Test-Path -LiteralPath $dk) { Remove-Item -LiteralPath $dk -Force }
    $script:LOI_TAT = @()
    foreach ($p in $lnk) {
        $da = TaoLoiTat $p $exe $dich $ico
        if ($da) { Ghi "Lối tắt: $da" } else { $script:LOI_TAT += (Split-Path $p -Leaf) }
    }
    # khóa registry: New-Item -Value đặt giá trị mặc định (cách viết chạy được cả PowerShell 2.0)
    if ($lienKet) {
        New-Item 'HKCU:\Software\Classes\.pabt' -Value 'PABT.DuAn' -Force | Out-Null
        New-Item 'HKCU:\Software\Classes\PABT.DuAn' -Value 'Dự án PABT' -Force | Out-Null
        New-Item 'HKCU:\Software\Classes\PABT.DuAn\DefaultIcon' -Value "`"$ico`",0" -Force | Out-Null
        New-Item 'HKCU:\Software\Classes\PABT.DuAn\shell\open\command' -Value "`"$exe`" `"%1`"" -Force | Out-Null
    }
    # gói cập nhật .pabtcn: bấm đúp để cập nhật phần mềm
    New-Item 'HKCU:\Software\Classes\.pabtcn' -Value 'PABT.CapNhat' -Force | Out-Null
    New-Item 'HKCU:\Software\Classes\PABT.CapNhat' -Value 'Gói cập nhật PABT' -Force | Out-Null
    New-Item 'HKCU:\Software\Classes\PABT.CapNhat\DefaultIcon' -Value "`"$ico`",0" -Force | Out-Null
    New-Item 'HKCU:\Software\Classes\PABT.CapNhat\shell\open\command' -Value "`"$exe`" `"%1`"" -Force | Out-Null
    $k = 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\PABT'
    New-Item $k -Force | Out-Null
    # gỡ cài cũng chạy qua -Command (không bị ExecutionPolicy / Group Policy chặn như -File)
    $q1 = (Join-Path $dich 'go_cai_dat.ps1').Replace("'", "''"); $q2 = $dich.Replace("'", "''")
    $go = "powershell.exe -NoProfile -ExecutionPolicy Bypass -STA -WindowStyle Hidden -Command `"& ([scriptblock]::Create(" +
          "[IO.File]::ReadAllText('$q1', [Text.Encoding]::UTF8))) -Dich '$q2'"
    $goIm = "$go -Im`""; $go = "$go`""
    $mb = [int]((Get-ChildItem -LiteralPath $dich -Recurse -Force | Where-Object { -not $_.PSIsContainer } | Measure-Object Length -Sum).Sum / 1KB)
    foreach ($kv in @(@('DisplayName', $TEN), @('DisplayVersion', $PHIEN_BAN), @('Publisher', 'PABT'), @('InstallLocation', $dich),
                      @('DisplayIcon', "$ico,0"), @('UninstallString', $go), @('QuietUninstallString', $goIm))) {
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

# ---------------------------------------------------------------- cài im lặng
if ($Im) {
    try {
        $loi = KiemTraMay; if ($loi) { Ghi "LỖI: $loi"; exit 3 }
        $cb = CanhBaoMay; if ($cb) { Ghi "LƯU Ý: $cb" }
        CaiVcRedist | Out-Null
        CaiKbWin7 | Out-Null                        # chỉ Windows 7 còn thiếu KB2533623
        $dich = $ThuMuc
        if (-not $dich) { $dich = Join-Path $env:LOCALAPPDATA 'Programs\PABT' }
        $tk = Cai $dich (-not $KhongDesktop) (-not $KhongLienKet) $null
        Ghi 'XONG'
        if ($script:KB_CHO_KHOI_DONG) { Ghi 'Cần khởi động lại máy (bản cập nhật Windows 7 KB3063858)'; exit 3010 }
        if ($tk -match 'KET QUA: DAT') { exit 0 } else { exit 4 }
    } catch { Ghi "LỖI: $_"; exit 1 }
}

# ---------------------------------------------------------------- cửa sổ cài đặt
$XANH = [System.Drawing.Color]::FromArgb(10, 37, 64); $VANG = [System.Drawing.Color]::FromArgb(255, 213, 79)
$f = New-Object System.Windows.Forms.Form
$f.Text = "Cài đặt PABT $PHIEN_BAN - $TEN_BAN"; $f.ClientSize = New-Object System.Drawing.Size(640, 430)
$f.FormBorderStyle = 'FixedDialog'; $f.MaximizeBox = $false; $f.StartPosition = 'CenterScreen'
$f.Font = New-Object System.Drawing.Font('Segoe UI', 9.5); $f.BackColor = [System.Drawing.Color]::White
$icoF = Join-Path $GOC 'PABT.ico'
if (Test-Path -LiteralPath $icoF) { $f.Icon = New-Object System.Drawing.Icon($icoF) }
$dau = New-Object System.Windows.Forms.Panel; $dau.Dock = 'Top'; $dau.Height = 110; $dau.BackColor = $XANH
$f.Controls.Add($dau)
$anh = New-Object System.Windows.Forms.PictureBox; $anh.Size = New-Object System.Drawing.Size(84, 84)
$anh.Location = New-Object System.Drawing.Point(18, 13); $anh.SizeMode = 'Zoom'
$png = Join-Path $GOC 'bieu_tuong.png'; if (Test-Path -LiteralPath $png) { $anh.Image = [System.Drawing.Image]::FromFile($png) }
$dau.Controls.Add($anh)
$t1 = New-Object System.Windows.Forms.Label; $t1.Text = $TEN_DAY_DU; $t1.ForeColor = $VANG; $t1.AutoSize = $false
$t1.Font = New-Object System.Drawing.Font('Segoe UI', 13, [System.Drawing.FontStyle]::Bold)
$dau.Controls.Add($t1)
$t2 = New-Object System.Windows.Forms.Label; $t2.ForeColor = [System.Drawing.Color]::White; $t2.AutoSize = $false
$t2.Text = "Phiên bản $PHIEN_BAN ($TEN_BAN)`r`nTrung tâm Phát triển quỹ đất Chi nhánh Vĩnh Cửu"
$dau.Controls.Add($t2)
# chữ tiêu đề: đo chiều cao thật theo phông (màn hình phóng to 125% / 150% chữ to hơn mà ô không tự to theo) rồi xếp dòng,
# băng xanh cao theo chữ - không cắt mất chữ cuối ("Cửu") như ô cố định 510 x 22 trước đây
$rongChu = 510
$c1 = $t1.GetPreferredSize((New-Object System.Drawing.Size($rongChu, 0))).Height
$t1.Location = New-Object System.Drawing.Point(115, 12); $t1.Size = New-Object System.Drawing.Size($rongChu, $c1)
$c2 = $t2.GetPreferredSize((New-Object System.Drawing.Size($rongChu, 0))).Height
$t2.Location = New-Object System.Drawing.Point(116, ($t1.Bottom + 4)); $t2.Size = New-Object System.Drawing.Size($rongChu, $c2)
$dau.Height = [Math]::Max(110, $t2.Bottom + 12)
$LECH = $dau.Height - 110                                   # phần băng tiêu đề cao thêm: dời các ô bên dưới xuống
$f.ClientSize = New-Object System.Drawing.Size(640, (430 + $LECH))
$vach = New-Object System.Windows.Forms.Panel; $vach.Dock = 'Top'; $vach.Height = 3; $vach.BackColor = $VANG; $f.Controls.Add($vach)
$vach.BringToFront()

$y = 130 + $LECH
$l1 = New-Object System.Windows.Forms.Label; $l1.Text = 'Thư mục cài đặt:'; $l1.Location = New-Object System.Drawing.Point(24, $y); $l1.AutoSize = $true
$f.Controls.Add($l1)
$oThu = New-Object System.Windows.Forms.TextBox; $oThu.Location = New-Object System.Drawing.Point(24, ($y + 22)); $oThu.Width = 490
$oThu.Text = $ThuMuc
if (-not $ThuMuc) { $oThu.Text = Join-Path $env:LOCALAPPDATA 'Programs\PABT' }
$f.Controls.Add($oThu)
$bChon = New-Object System.Windows.Forms.Button; $bChon.Text = 'Chọn…'; $bChon.Location = New-Object System.Drawing.Point(524, ($y + 20))
$bChon.Width = 90; $f.Controls.Add($bChon)
$bChon.Add_Click({ $d = New-Object System.Windows.Forms.FolderBrowserDialog; if ($d.ShowDialog() -eq 'OK') { $oThu.Text = Join-Path $d.SelectedPath 'PABT' } })
$cDesk = New-Object System.Windows.Forms.CheckBox; $cDesk.Text = 'Tạo biểu tượng PABT trên Desktop'; $cDesk.Checked = -not $KhongDesktop
$cDesk.Location = New-Object System.Drawing.Point(24, ($y + 58)); $cDesk.AutoSize = $true; $f.Controls.Add($cDesk)
$cLk = New-Object System.Windows.Forms.CheckBox; $cLk.Text = 'Mở file dự án .pabt bằng PABT khi nhấp đúp'; $cLk.Checked = -not $KhongLienKet
$cLk.Location = New-Object System.Drawing.Point(24, ($y + 84)); $cLk.AutoSize = $true; $f.Controls.Add($cLk)
$cVc = New-Object System.Windows.Forms.CheckBox; $cVc.AutoSize = $true; $cVc.Location = New-Object System.Drawing.Point(24, ($y + 110))
if (-not $CO_VC) { $cVc.Text = "Thư viện Visual C++: đóng gói sẵn trong PABT, không cần cài thêm"; $cVc.Checked = $false; $cVc.Enabled = $false }
elseif (CoVcRedist) { $cVc.Text = "Microsoft Visual C++ Redistributable ($KIEN): máy đã có"; $cVc.Checked = $false; $cVc.Enabled = $false }
else { $cVc.Text = "Cài Microsoft Visual C++ Redistributable ($KIEN) - cần quyền quản trị"; $cVc.Checked = $true }
# Windows 7 thiếu KB2533623 (bộ cài Win7-8 kèm KB3063858): dòng này thành ô cài bản cập nhật Windows (Visual C++ đã đóng sẵn)
$script:O_LA_KB = $false
if ((ThieuKbWin7) -and (Test-Path -LiteralPath $KB)) {
    $cVc.Text = 'Cài bản cập nhật Windows 7 KB3063858 (PABT cần) - hỏi quyền quản trị, khởi động lại máy sau khi cài'
    $cVc.Checked = $true; $cVc.Enabled = $true; $script:O_LA_KB = $true
}
$f.Controls.Add($cVc)
$tt = New-Object System.Windows.Forms.Label; $tt.Location = New-Object System.Drawing.Point(24, ($y + 150)); $tt.Size = New-Object System.Drawing.Size(590, 40)
$tt.ForeColor = $XANH; $f.Controls.Add($tt)
$pb = New-Object System.Windows.Forms.ProgressBar; $pb.Location = New-Object System.Drawing.Point(24, ($y + 192)); $pb.Size = New-Object System.Drawing.Size(590, 18)
$f.Controls.Add($pb)
$bCai = New-Object System.Windows.Forms.Button; $bCai.Text = 'Cài đặt'; $bCai.Size = New-Object System.Drawing.Size(120, 34)
$bCai.Location = New-Object System.Drawing.Point(364, (380 + $LECH)); $bCai.BackColor = [System.Drawing.Color]::FromArgb(46, 125, 50)
$bCai.ForeColor = [System.Drawing.Color]::White; $bCai.FlatStyle = 'Flat'; $bCai.Font = New-Object System.Drawing.Font('Segoe UI', 10, [System.Drawing.FontStyle]::Bold)
$f.Controls.Add($bCai); $f.AcceptButton = $bCai
$bHuy = New-Object System.Windows.Forms.Button; $bHuy.Text = 'Hủy'; $bHuy.Size = New-Object System.Drawing.Size(120, 34)
$bHuy.Location = New-Object System.Drawing.Point(494, (380 + $LECH)); $f.Controls.Add($bHuy); $f.CancelButton = $bHuy
$bHuy.DialogResult = [System.Windows.Forms.DialogResult]::Cancel   # đóng bằng cơ chế sẵn của hộp thoại
# sau khi cài, ô thư mục đang giữ tiêu điểm đã bị khóa nên WinForms bỏ sự kiện Click của nút: tự đóng khi nhả chuột trên nút
$bHuy.Add_MouseUp({ if ($_.Button -eq 'Left' -and $this.Enabled -and $this.ClientRectangle.Contains($_.Location)) {
    $this.FindForm().DialogResult = [System.Windows.Forms.DialogResult]::Cancel } })
$loi = KiemTraMay
if ($loi) {
    $tt.Text = $loi; $tt.ForeColor = [System.Drawing.Color]::DarkRed; $bCai.Enabled = $false
    $bCai.BackColor = [System.Drawing.Color]::FromArgb(189, 189, 189)     # nút phẳng: tự tô xám khi khóa
}
else {
    $tt.Text = "Máy đạt yêu cầu (Windows $([Environment]::OSVersion.Version.Major).$([Environment]::OSVersion.Version.Minor) $BIT). Bấm `"Cài đặt`" để bắt đầu."
    $cb = CanhBaoMay
    if ($cb) { Ghi "LƯU Ý: $cb"; $tt.Text = "Lưu ý: $cb"; $tt.ForeColor = [System.Drawing.Color]::FromArgb(176, 96, 0) }
}
$script:xong = $false
$tienDo = { param($phan, $chu) $pb.Value = [Math]::Min(100, $phan); $tt.Text = $chu; [System.Windows.Forms.Application]::DoEvents() }
$bCai.Add_Click({
    if ($script:xong) { Start-Process (Join-Path $oThu.Text 'PABT.exe'); $this.FindForm().DialogResult = 'OK'; return }
    $bCai.Enabled = $false; $bHuy.Enabled = $false; $bChon.Enabled = $false; $oThu.Enabled = $false
    try {
        if ($script:O_LA_KB) {
            if ($cVc.Checked) { & $tienDo 3 'Cài bản cập nhật Windows 7 KB3063858 (Windows hỏi quyền quản trị, có thể mất vài phút)…'
                                $kb = CaiKbWin7 }
        } elseif ($cVc.Checked) { & $tienDo 3 'Cài Microsoft Visual C++ Redistributable (có thể hỏi quyền quản trị)…'; $vc = CaiVcRedist }
        & $tienDo 8 'Đang cài PABT…'
        $tk = Cai $oThu.Text $cDesk.Checked $cLk.Checked $tienDo
        & $tienDo 100 ''
        $them = ''
        if ($script:LOI_TAT.Count -gt 0) { $them = " Chưa tạo được lối tắt ($($script:LOI_TAT -join ', ')): mở PABT.exe trong thư mục cài." }
        if ($tk -match 'KET QUA: DAT') {
            $tt.ForeColor = [System.Drawing.Color]::DarkGreen
            $tt.Text = "Đã cài xong PABT $PHIEN_BAN và tự kiểm tra đạt (giao diện, PDF, bộ đơn giá, mẫu in, bảng giá đất).$them"
        } else {
            $tt.ForeColor = [System.Drawing.Color]::DarkRed
            $tt.Text = "Đã cài nhưng tự kiểm tra chưa đạt - xem nhật ký: $nk"
            $cb = CanhBaoMay; if ($cb) { $tt.Text = "Đã cài. $cb" }
        }
        $bCai.Text = 'Mở PABT'; $bCai.Enabled = $true; $bHuy.Text = 'Đóng'; $bHuy.Enabled = $true; $script:xong = $true
        if ($script:KB_CHO_KHOI_DONG) {             # bản cập nhật Windows có hiệu lực sau khi khởi động lại: chưa mở PABT được
            $tt.ForeColor = [System.Drawing.Color]::FromArgb(176, 96, 0)
            $tt.Text = "Đã cài PABT $PHIEN_BAN và bản cập nhật Windows 7 KB3063858. KHỞI ĐỘNG LẠI MÁY rồi mở PABT (biểu tượng PABT)."
            $bCai.Visible = $false
        }
        $f.ActiveControl = $bCai
    } catch {
        Ghi "LỖI: $_"
        $tt.ForeColor = [System.Drawing.Color]::DarkRed; $tt.Text = "Không cài được: $_ (nhật ký: $nk)"
        $bHuy.Text = 'Đóng'; $bHuy.Enabled = $true
    }
})
[void]$f.ShowDialog()
exit 0

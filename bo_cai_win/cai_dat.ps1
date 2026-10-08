# Trình cài PABT cho người dùng hiện tại (chạy bởi bộ cài PABT_CaiDat_<phiên bản>.exe - IExpress).
#   Không tham số: cửa sổ cài đặt (chọn thư mục, tùy chọn, thanh tiến trình, tự kiểm tra sau khi cài).
#   -Im          cài im lặng (không hỏi, không mở phần mềm sau khi cài)
#   -ThuMuc X    thư mục cài (mặc định %LOCALAPPDATA%\Programs\PABT)
#   -KhongDesktop / -KhongLienKet   bỏ biểu tượng Desktop / không gắn file .pabt
# Hai bộ cài dùng chung script này (ban.txt): win10 = Windows 10 / 11 64-bit; win7 = bản 32-bit cho Windows 7 SP1 / 8 / 8.1
# (máy 32-bit hoặc 64-bit, và Windows 10 32-bit). Bộ cài Win7-8 kèm Visual C++ Redistributable x86 (Windows 7 thiếu UCRT), cài
# nếu máy chưa có (hỏi quyền quản trị); bộ cài Win10-11 không kèm (vc_redist.exe vắng mặt): Windows 10/11 có sẵn UCRT, các DLL
# Visual C++ PABT cần đã đóng gói trong thư mục cài. Chạy được với PowerShell 2.0 / .NET 3.5 có sẵn trên Windows 7 (không dùng lệnh của PowerShell 3+); gọi với -STA.
param([switch]$Im, [string]$ThuMuc = '', [switch]$KhongDesktop, [switch]$KhongLienKet)
$ErrorActionPreference = 'Stop'
$GOC = Split-Path -Parent $MyInvocation.MyCommand.Definition      # PowerShell 2.0 chưa có $PSScriptRoot
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
[System.Windows.Forms.Application]::EnableVisualStyles()
$TEN = 'PABT - Lập phương án bồi thường, hỗ trợ'
$TEN_DAY_DU = 'PHẦN MỀM LẬP PHƯƠNG ÁN BỒI THƯỜNG, HỖ TRỢ, TÁI ĐỊNH CƯ'
$PHIEN_BAN = [System.IO.File]::ReadAllText((Join-Path $GOC 'phien_ban.txt')).Trim()
$BAN = 'win10'
if (Test-Path (Join-Path $GOC 'ban.txt')) { $BAN = [System.IO.File]::ReadAllText((Join-Path $GOC 'ban.txt')).Trim() }
$TEN_BAN = 'Windows 10 / 11'
if ($BAN -eq 'win7') { $TEN_BAN = 'Windows 7 / 8' }
$KIEN = 'x64'                                   # kiến trúc chương trình và bộ Visual C++ kèm theo
if ($BAN -eq 'win7') { $KIEN = 'x86' }
$MAY64 = ($env:PROCESSOR_ARCHITECTURE -eq 'AMD64' -or $env:PROCESSOR_ARCHITEW6432 -eq 'AMD64')
$BIT = '32-bit'
if ($MAY64) { $BIT = '64-bit' }
$VC = Join-Path $GOC 'vc_redist.exe'
$CO_VC = Test-Path $VC                          # bộ cài Win10-11 không kèm Visual C++ Redistributable
$nk =Join-Path $env:TEMP 'pabt_cai_dat.log'
function Ghi($s) { Add-Content -Path $nk -Value ("{0:HH:mm:ss} {1}" -f (Get-Date), $s) -Encoding UTF8 }
Set-Content -Path $nk -Value "Cài PABT $PHIEN_BAN" -Encoding UTF8

# ---------------------------------------------------------------- kiểm tra hệ thống
Ghi "Bộ cài: $TEN_BAN ($BAN)"

function KiemTraMay {
    $v = [Environment]::OSVersion.Version
    if ($BAN -eq 'win10' -and $v.Major -lt 10) {
        return "Bộ cài này dành cho Windows 10 / 11. Máy này là Windows $($v.Major).$($v.Minor): dùng bộ cài PABT_CaiDat_$($PHIEN_BAN)_Win7-8.exe." }
    if ($BAN -eq 'win10' -and -not $MAY64) {
        return "Máy này là Windows 32-bit: dùng bộ cài PABT_CaiDat_$($PHIEN_BAN)_Win7-8.exe (bản 32-bit)." }
    if ($BAN -eq 'win7' -and $v.Major -ge 10 -and $MAY64) {
        return "Máy này là Windows 10 / 11 64-bit: dùng bộ cài PABT_CaiDat_$($PHIEN_BAN)_Win10-11.exe (ổn định hơn trên máy mới)." }
    if ($v.Major -lt 6 -or ($v.Major -eq 6 -and $v.Minor -lt 1)) {
        return "PABT cần Windows 7 SP1 trở lên (máy này: Windows $($v.Major).$($v.Minor))." }
    if ($v.Major -eq 6 -and $v.Minor -eq 1 -and $v.Build -lt 7601) {
        return 'Windows 7 cần cài Service Pack 1 (SP1) trước khi cài PABT.' }
    $o = $env:LOCALAPPDATA.Substring(0, 2)
    $dia = Get-WmiObject Win32_LogicalDisk -Filter "DeviceID='$o'" -ErrorAction SilentlyContinue
    if ($dia -and $dia.FreeSpace -lt 300MB) { return "Ổ đĩa cài còn trống {0:N0} MB, cần ít nhất 300 MB." -f ($dia.FreeSpace / 1MB) }
    return ''
}

function CoVcRedist {
    if (-not $CO_VC) { return $true }           # không kèm: không cần cài (DLL Visual C++ đóng gói sẵn trong PABT)
    $can =[version]((Get-Item $VC).VersionInfo.ProductVersion)
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

function DemFile($thu) { @(Get-ChildItem $thu -Recurse -Force | Where-Object { -not $_.PSIsContainer }).Count }

function GiaiNen($zip, $dich, $tienDo) {
    # máy có .NET 4.5 (PowerShell 3+): giải nén từng file, tiến trình mịn; Windows 7 gốc (PowerShell 2.0): dùng Shell của Windows
    $net45 = $false
    if ($PSVersionTable.PSVersion.Major -ge 3) {
        try { Add-Type -AssemblyName System.IO.Compression.FileSystem; $net45 = $true } catch { }
    }
    if ($net45) {
        $z = [System.IO.Compression.ZipFile]::OpenRead($zip)
        try {
            $n = $z.Entries.Count; $i = 0
            foreach ($e in $z.Entries) {
                $ra = Join-Path $dich $e.FullName
                if ($e.FullName.EndsWith('/')) { New-Item -ItemType Directory -Force $ra | Out-Null; continue }
                New-Item -ItemType Directory -Force (Split-Path $ra) | Out-Null
                [System.IO.Compression.ZipFileExtensions]::ExtractToFile($e, $ra, $true)
                $i++
                if ($tienDo -and ($i % 5 -eq 0 -or $i -eq $n)) { & $tienDo (10 + [int](75 * $i / $n)) "Đang chép file ($i/$n)…" }
            }
        } finally { $z.Dispose() }
        return
    }
    $can = [int]([System.IO.File]::ReadAllText((Join-Path $GOC 'so_file.txt')).Trim())
    $sh = New-Object -ComObject Shell.Application
    $nguon = $sh.NameSpace($zip); $dd = $sh.NameSpace($dich)
    $ds = @($nguon.Items()); $i = 0
    foreach ($it in $ds) {
        $dd.CopyHere($it, 0x614)        # không hiện hộp tiến trình, ghi đè, tự tạo thư mục, không báo lỗi
        $i++
        if ($tienDo) { & $tienDo (10 + [int](60 * $i / $ds.Count)) "Đang chép file ($i/$($ds.Count) mục)…" }
    }
    for ($t = 0; $t -lt 360; $t++) {     # Shell có thể chép nền: chờ đủ số file (tối đa 3 phút)
        $co = DemFile $dich
        if ($co -ge $can) { break }
        if ($tienDo) { & $tienDo (70 + [int](15 * $co / $can)) "Đang chép file ($co/$can)…" }
        Start-Sleep -Milliseconds 500
    }
}

# ---------------------------------------------------------------- cài
function KiemTraThuMuc($dich) {
    # chỉ xóa thư mục trống hoặc bản PABT cũ: gõ nhầm D:\ hay chọn Documents thì không được xóa dữ liệu người dùng
    if ($dich.TrimEnd('\') -eq [System.IO.Path]::GetPathRoot($dich).TrimEnd('\')) {
        throw "Không cài thẳng vào gốc ổ đĩa ($dich): chọn một thư mục, ví dụ $($dich.TrimEnd('\'))\PABT." }
    if (-not (Test-Path $dich)) { return }
    $co = @(Get-ChildItem $dich -Force)
    if ($co.Count -gt 0 -and -not (Test-Path (Join-Path $dich 'PABT.exe'))) {
        throw "Thư mục $dich đã có file khác (không phải bản cài PABT). Chọn thư mục trống hoặc thư mục PABT đã cài trước đây." }
    $da = @(Get-ChildItem $dich -Recurse -Force -Include '*.pabt', '*.pabtdt' -ErrorAction SilentlyContinue)
    if ($da.Count -gt 0) {
        throw "Thư mục cài có $($da.Count) file dự án (ví dụ $($da[0].FullName)). Chuyển các file dự án ra thư mục khác rồi cài lại." }
}

function Cai($dich, $desktop, $lienKet, $tienDo) {
    $dich = [System.IO.Path]::GetFullPath($dich)
    Ghi "Thư mục cài: $dich"
    KiemTraThuMuc $dich
    Get-Process PABT -ErrorAction SilentlyContinue | Where-Object { $_.Path -like "$dich*" } | Stop-Process -Force
    if (Test-Path $dich) { Remove-Item $dich -Recurse -Force; Ghi 'Đã gỡ bản cũ' }
    New-Item -ItemType Directory -Force $dich | Out-Null
    GiaiNen (Join-Path $GOC 'PABT.zip') $dich $tienDo
    Copy-Item (Join-Path $GOC 'go_cai_dat.ps1') $dich -Force
    Ghi "Đã chép $(DemFile $dich) file (PowerShell $($PSVersionTable.PSVersion), Windows $([Environment]::OSVersion.Version))"
    if ($tienDo) { & $tienDo 88 'Tạo biểu tượng, liên kết file…' }
    $exe = Join-Path $dich 'PABT.exe'
    $ico = Join-Path $dich 'PABT.ico'
    if (-not (Test-Path $ico)) { $ico = $exe }
    $ws = New-Object -ComObject WScript.Shell
    $lnk = @((Join-Path ([Environment]::GetFolderPath('Programs')) 'PABT - Lập phương án bồi thường.lnk'))
    $dk = Join-Path ([Environment]::GetFolderPath('Desktop')) 'PABT.lnk'
    if ($desktop) { $lnk += $dk } elseif (Test-Path $dk) { Remove-Item $dk -Force }
    foreach ($p in $lnk) {
        $l = $ws.CreateShortcut($p); $l.TargetPath = $exe; $l.WorkingDirectory = $dich; $l.IconLocation = "$ico,0"
        $l.Description = $TEN; $l.Save()
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
    $go = "powershell.exe -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$dich\go_cai_dat.ps1`""
    $mb = [int]((Get-ChildItem $dich -Recurse -Force | Where-Object { -not $_.PSIsContainer } | Measure-Object Length -Sum).Sum / 1KB)
    foreach ($kv in @(@('DisplayName', $TEN), @('DisplayVersion', $PHIEN_BAN), @('Publisher', 'PABT'), @('InstallLocation', $dich),
                      @('DisplayIcon', "$ico,0"), @('UninstallString', $go), @('QuietUninstallString', "$go -Im"))) {
        New-ItemProperty $k -Name $kv[0] -Value $kv[1] -PropertyType String -Force | Out-Null
    }
    foreach ($kv in @(@('NoModify', 1), @('NoRepair', 1), @('EstimatedSize', $mb))) {
        New-ItemProperty $k -Name $kv[0] -Value $kv[1] -PropertyType DWord -Force | Out-Null
    }
    $ie = "$env:SystemRoot\System32\ie4uinit.exe"     # làm mới bộ đệm biểu tượng (Windows 10+: -show; Windows 7/8: -ClearIconCache)
    $tham = '-ClearIconCache'
    if ([Environment]::OSVersion.Version.Major -ge 10) { $tham = '-show' }
    try { if (Test-Path $ie) { Start-Process $ie -ArgumentList $tham -WindowStyle Hidden -Wait } } catch { }
    # tự kiểm tra bản vừa cài trên máy này
    if ($tienDo) { & $tienDo 94 'Tự kiểm tra phần mềm trên máy này…' }
    $kq = Join-Path $env:TEMP 'pabt_tu_kiem.txt'
    Remove-Item $kq -ErrorAction SilentlyContinue
    Start-Process $exe -ArgumentList 'tu-kiem', "`"$kq`"" -Wait
    $tk = 'KET QUA: không chạy được PABT.exe'
    if (Test-Path $kq) { $tk = [System.IO.File]::ReadAllText($kq, [System.Text.Encoding]::UTF8) }
    Ghi $tk
    return $tk
}

# ---------------------------------------------------------------- cài im lặng
if ($Im) {
    try {
        $loi = KiemTraMay; if ($loi) { Ghi "LỖI: $loi"; exit 3 }
        CaiVcRedist | Out-Null
        $dich = $ThuMuc
        if (-not $dich) { $dich = Join-Path $env:LOCALAPPDATA 'Programs\PABT' }
        $tk = Cai $dich (-not $KhongDesktop) (-not $KhongLienKet) $null
        Ghi 'XONG'
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
if (Test-Path $icoF) { $f.Icon = New-Object System.Drawing.Icon($icoF) }
$dau = New-Object System.Windows.Forms.Panel; $dau.Dock = 'Top'; $dau.Height = 110; $dau.BackColor = $XANH
$f.Controls.Add($dau)
$anh = New-Object System.Windows.Forms.PictureBox; $anh.Size = New-Object System.Drawing.Size(84, 84)
$anh.Location = New-Object System.Drawing.Point(18, 13); $anh.SizeMode = 'Zoom'
$png = Join-Path $GOC 'bieu_tuong.png'; if (Test-Path $png) { $anh.Image = [System.Drawing.Image]::FromFile($png) }
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
else { $tt.Text = "Máy đạt yêu cầu (Windows $([Environment]::OSVersion.Version.Major).$([Environment]::OSVersion.Version.Minor) $BIT). Bấm `"Cài đặt`" để bắt đầu." }
$script:xong = $false
$tienDo = { param($phan, $chu) $pb.Value = [Math]::Min(100, $phan); $tt.Text = $chu; [System.Windows.Forms.Application]::DoEvents() }
$bCai.Add_Click({
    if ($script:xong) { Start-Process (Join-Path $oThu.Text 'PABT.exe'); $this.FindForm().DialogResult = 'OK'; return }
    $bCai.Enabled = $false; $bHuy.Enabled = $false; $bChon.Enabled = $false; $oThu.Enabled = $false
    try {
        if ($cVc.Checked) { & $tienDo 3 'Cài Microsoft Visual C++ Redistributable (có thể hỏi quyền quản trị)…'; $vc = CaiVcRedist }
        & $tienDo 8 'Đang cài PABT…'
        $tk = Cai $oThu.Text $cDesk.Checked $cLk.Checked $tienDo
        & $tienDo 100 ''
        if ($tk -match 'KET QUA: DAT') {
            $tt.ForeColor = [System.Drawing.Color]::DarkGreen
            $tt.Text = "Đã cài xong PABT $PHIEN_BAN và tự kiểm tra đạt (giao diện, PDF, bộ đơn giá, mẫu in, bảng giá đất)."
        } else {
            $tt.ForeColor = [System.Drawing.Color]::DarkRed
            $tt.Text = "Đã cài nhưng tự kiểm tra chưa đạt - xem nhật ký: $nk"
        }
        $bCai.Text = 'Mở PABT'; $bCai.Enabled = $true; $bHuy.Text = 'Đóng'; $bHuy.Enabled = $true; $script:xong = $true
        $f.ActiveControl = $bCai
    } catch {
        Ghi "LỖI: $_"
        $tt.ForeColor = [System.Drawing.Color]::DarkRed; $tt.Text = "Không cài được: $_ (nhật ký: $nk)"
        $bHuy.Text = 'Đóng'; $bHuy.Enabled = $true
    }
})
[void]$f.ShowDialog()
exit 0

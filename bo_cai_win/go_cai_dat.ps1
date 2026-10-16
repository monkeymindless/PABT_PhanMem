# Gỡ PABT (cài cho người dùng hiện tại). Dữ liệu dự án (.pabt) của người dùng không bị xóa.
# Gọi từ "Gỡ cài đặt" của Windows qua powershell -Command (không bị ExecutionPolicy chặn) với -Dich <thư mục cài>.
param([switch]$Im, [string]$Dich = '')
Add-Type -AssemblyName System.Windows.Forms
$dich = $Dich
if (-not $dich) { $dich = Split-Path -Parent $MyInvocation.MyCommand.Definition }   # chạy thẳng file (PowerShell 2.0: không $PSScriptRoot)
$dich = $dich.TrimEnd([char]92)                 # bỏ "\" cuối
Set-Location -LiteralPath $env:TEMP             # thư mục làm việc không nằm trong thư mục cài (sẽ không xóa được)

function GhiDuoc($d) {
    # thư mục cài ghi / xóa được bằng quyền người dùng không (Program Files: cần quyền quản trị) - như cai_dat.ps1
    if (-not (Test-Path -LiteralPath $d)) { return $true }
    $thu = Join-Path $d ('pabt_thu_ghi_' + [Guid]::NewGuid().ToString('N') + '.tmp')
    try { [System.IO.File]::WriteAllText($thu, ''); [System.IO.File]::Delete($thu); return $true } catch { return $false }
}
if (-not $Im) {
    $tl = [System.Windows.Forms.MessageBox]::Show("Gỡ LARC khỏi máy?`n(Các file dự án .larc / .pabt của bạn được giữ nguyên.)", 'Gỡ cài đặt LARC', 'YesNo', 'Question')
    if ($tl -ne 'Yes') { exit 2 }
}
# PowerShell 32-bit không đọc được .Path của PABT 64-bit (trả về rỗng) nên không tắt được phần mềm đang mở.
# Win32_Process.ExecutablePath đọc được. Gọi lại trong lệnh xóa (quyền quản trị) vì file còn bị giữ vài giây.
function TatPabt($d) {
    Get-WmiObject Win32_Process -ErrorAction SilentlyContinue | Where-Object {
        $_.Name -eq 'PABT.exe' -and $_.ExecutablePath -and $_.ExecutablePath.ToLower().StartsWith($d.ToLower()) } |
        ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
}
TatPabt $dich
foreach ($p in @((Join-Path ([Environment]::GetFolderPath('Programs')) 'PABT - Lập phương án bồi thường.lnk'),
                 (Join-Path ([Environment]::GetFolderPath('Programs')) 'PABT.lnk'),      # tên dự phòng (máy không tạo được tên có dấu)
                 (Join-Path ([Environment]::GetFolderPath('Desktop')) 'PABT.lnk'),
                 # tên hiển thị LARC (0.9.92)
                 (Join-Path ([Environment]::GetFolderPath('Programs')) 'LARC - Bồi thường, hỗ trợ, tái định cư.lnk'),
                 (Join-Path ([Environment]::GetFolderPath('Programs')) 'LARC.lnk'),
                 (Join-Path ([Environment]::GetFolderPath('Desktop')) 'LARC.lnk'))) {
    if (Test-Path -LiteralPath $p) { Remove-Item -LiteralPath $p -Force }
}
foreach ($duoi in '.larc', '.pabt') {
    if ((Get-ItemProperty "HKCU:\Software\Classes\$duoi" -ErrorAction SilentlyContinue).'(default)' -eq 'PABT.DuAn') {
        Remove-Item "HKCU:\Software\Classes\$duoi" -Recurse -Force
    }
}
Remove-Item 'HKCU:\Software\Classes\PABT.DuAn' -Recurse -Force -ErrorAction SilentlyContinue
foreach ($duoi in '.pabtcn', '.larcud') {
  if ((Get-ItemProperty "HKCU:\Software\Classes\$duoi" -ErrorAction SilentlyContinue).'(default)' -eq 'PABT.CapNhat') {
    Remove-Item "HKCU:\Software\Classes\$duoi" -Recurse -Force
  }
}
Remove-Item 'HKCU:\Software\Classes\PABT.CapNhat' -Recurse -Force -ErrorAction SilentlyContinue
if ((Get-ItemProperty 'HKCU:\Software\Classes\.pabtcfg' -ErrorAction SilentlyContinue).'(default)' -eq 'PABT.MauIn') {
    Remove-Item 'HKCU:\Software\Classes\.pabtcfg' -Recurse -Force
}
Remove-Item 'HKCU:\Software\Classes\PABT.MauIn' -Recurse -Force -ErrorAction SilentlyContinue
# bản cập nhật .pabtcn đã cài (mã phần mềm, không phải dữ liệu người dùng)
Remove-Item -LiteralPath (Join-Path $env:APPDATA 'PABT\cap_nhat') -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\PABT' -Recurse -Force -ErrorAction SilentlyContinue
# lọc theo đuôi bằng Where-Object: -Include KHÔNG có tác dụng khi dùng -LiteralPath (trả về mọi file)
$giu = @(Get-ChildItem -LiteralPath $dich -Recurse -Force -ErrorAction SilentlyContinue |
         Where-Object { -not $_.PSIsContainer -and ($_.Extension -eq '.larc' -or $_.Extension -eq '.pabt' -or $_.Extension -eq '.pabtdt') })
$tb = 'Đã gỡ PABT.'
# lệnh xóa (một dòng, không dấu ngoặc kép - truyền qua dòng lệnh powershell -Command); $d = thư mục cài.
# Xóa hết: thử lại tới 30 giây (Windows / diệt virus còn giữ file vừa đóng một lúc - một lần rmdir sau 2 giây từng để sót thư mục
# rỗng). Giữ dự án (có file .pabt trong thư mục cài): chỉ xóa file phần mềm và thư mục rỗng.
$XOA_HET = 'for ($i = 0; $i -lt 30; $i++) { Start-Sleep 1; Get-WmiObject Win32_Process -ErrorAction SilentlyContinue | Where-Object { $_.Name -eq ''PABT.exe'' -and $_.ExecutablePath -and $_.ExecutablePath.ToLower().StartsWith($d.ToLower()) } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }; Remove-Item -LiteralPath $d -Recurse -Force -ErrorAction SilentlyContinue; ' +
           'if (-not (Test-Path -LiteralPath $d)) { break } }'
$XOA_GIU = 'Get-ChildItem -LiteralPath $d -Recurse -Force | Where-Object { -not $_.PSIsContainer -and $_.Extension -ne ''.larc'' -and $_.Extension -ne ''.pabt'' -and ' +
           '$_.Extension -ne ''.pabtdt'' } | Remove-Item -Force -ErrorAction SilentlyContinue; Get-ChildItem -LiteralPath $d -Recurse ' +
           '-Force | Where-Object { $_.PSIsContainer } | Sort-Object { $_.FullName.Length } -Descending | Where-Object { @(Get-ChildItem ' +
           '-LiteralPath $_.FullName -Force).Count -eq 0 } | Remove-Item -Force -ErrorAction SilentlyContinue'
$than = $XOA_HET
if ($giu.Count -gt 0) { $than = $XOA_GIU; $tb = "Đã gỡ PABT. Giữ lại $($giu.Count) file dự án trong $dich." }
$lenh = "`$d = '" + $dich.Replace("'", "''") + "'; " + $than
if (GhiDuoc $dich) {
    if ($giu.Count -gt 0) { & ([scriptblock]::Create($lenh)) }
    else {                                      # xóa sau khi script này thoát
        Start-Process powershell.exe -ArgumentList '-NoProfile', '-WindowStyle', 'Hidden', '-Command', $lenh `
            -WindowStyle Hidden -WorkingDirectory $env:TEMP
    }
} else {
    # cài trong Program Files (bộ cài đã chép bằng quyền quản trị): xóa cũng cần quyền quản trị - Windows hỏi UAC
    try {
        Start-Process "$env:SystemRoot\System32\WindowsPowerShell\v1.0\powershell.exe" -Verb RunAs -Wait -WindowStyle Hidden `
            -WorkingDirectory $env:TEMP -ArgumentList '-NoProfile', '-ExecutionPolicy', 'Bypass', '-WindowStyle', 'Hidden', '-Command', $lenh
        if ($giu.Count -eq 0 -and (Test-Path -LiteralPath $dich)) { $tb = "Đã gỡ PABT nhưng chưa xóa hết thư mục $dich - xóa thư mục này bằng tay." }
    } catch {
        $tb = "Đã gỡ PABT khỏi Windows (biểu tượng, liên kết file, mục gỡ cài đặt) nhưng chưa xóa được thư mục $dich vì chưa " +
              'được cấp quyền quản trị. Xóa thư mục này bằng tay (cần tài khoản quản trị).'
    }
}
if (-not $Im) { [System.Windows.Forms.MessageBox]::Show($tb, 'Gỡ cài đặt PABT', 'OK', 'Information') | Out-Null }
exit 0

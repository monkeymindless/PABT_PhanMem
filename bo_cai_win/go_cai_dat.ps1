# Gỡ PABT (cài cho người dùng hiện tại). Dữ liệu dự án (.pabt) của người dùng không bị xóa.
# Gọi từ "Gỡ cài đặt" của Windows qua powershell -Command (không bị ExecutionPolicy chặn) với -Dich <thư mục cài>.
param([switch]$Im, [string]$Dich = '')
Add-Type -AssemblyName System.Windows.Forms
$dich = $Dich
if (-not $dich) { $dich = Split-Path -Parent $MyInvocation.MyCommand.Definition }   # chạy thẳng file (PowerShell 2.0: không $PSScriptRoot)
$dich = $dich.TrimEnd([char]92)                 # bỏ "\" cuối
Set-Location -LiteralPath $env:TEMP             # thư mục làm việc không nằm trong thư mục cài (sẽ không xóa được)
if (-not $Im) {
    $tl = [System.Windows.Forms.MessageBox]::Show("Gỡ PABT khỏi máy?`n(Các file dự án .pabt của bạn được giữ nguyên.)", 'Gỡ cài đặt PABT', 'YesNo', 'Question')
    if ($tl -ne 'Yes') { exit 2 }
}
Get-Process PABT -ErrorAction SilentlyContinue | Where-Object { $_.Path -and $_.Path.StartsWith($dich, 'OrdinalIgnoreCase') } | Stop-Process -Force
foreach ($p in @((Join-Path ([Environment]::GetFolderPath('Programs')) 'PABT - Lập phương án bồi thường.lnk'),
                 (Join-Path ([Environment]::GetFolderPath('Programs')) 'PABT.lnk'),      # tên dự phòng (máy không tạo được tên có dấu)
                 (Join-Path ([Environment]::GetFolderPath('Desktop')) 'PABT.lnk'))) {
    if (Test-Path -LiteralPath $p) { Remove-Item -LiteralPath $p -Force }
}
if ((Get-ItemProperty 'HKCU:\Software\Classes\.pabt' -ErrorAction SilentlyContinue).'(default)' -eq 'PABT.DuAn') {
    Remove-Item 'HKCU:\Software\Classes\.pabt' -Recurse -Force
}
Remove-Item 'HKCU:\Software\Classes\PABT.DuAn' -Recurse -Force -ErrorAction SilentlyContinue
if ((Get-ItemProperty 'HKCU:\Software\Classes\.pabtcn' -ErrorAction SilentlyContinue).'(default)' -eq 'PABT.CapNhat') {
    Remove-Item 'HKCU:\Software\Classes\.pabtcn' -Recurse -Force
}
Remove-Item 'HKCU:\Software\Classes\PABT.CapNhat' -Recurse -Force -ErrorAction SilentlyContinue
# bản cập nhật .pabtcn đã cài (mã phần mềm, không phải dữ liệu người dùng)
Remove-Item -LiteralPath (Join-Path $env:APPDATA 'PABT\cap_nhat') -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\PABT' -Recurse -Force -ErrorAction SilentlyContinue
# lọc theo đuôi bằng Where-Object: -Include KHÔNG có tác dụng khi dùng -LiteralPath (trả về mọi file)
$giu = @(Get-ChildItem -LiteralPath $dich -Recurse -Force -ErrorAction SilentlyContinue |
         Where-Object { -not $_.PSIsContainer -and ($_.Extension -eq '.pabt' -or $_.Extension -eq '.pabtdt') })
$tb = 'Đã gỡ PABT.'
if ($giu.Count -eq 0) {
    # xóa thư mục cài sau khi script này thoát; thử lại tới 30 giây (Windows / diệt virus còn giữ file vừa đóng một lúc - một lần
    # rmdir sau 2 giây từng để sót thư mục rỗng). Đường dẫn qua biến môi trường: không phải đặt trong ngoặc kép (tên có dấu, nháy)
    $env:PABT_XOA = $dich
    $lenh = 'for ($i = 0; $i -lt 30; $i++) { Start-Sleep 1; Remove-Item -LiteralPath $env:PABT_XOA -Recurse -Force ' +
            '-ErrorAction SilentlyContinue; if (-not (Test-Path -LiteralPath $env:PABT_XOA)) { break } }'
    Start-Process powershell.exe -ArgumentList '-NoProfile', '-WindowStyle', 'Hidden', '-Command', $lenh `
        -WindowStyle Hidden -WorkingDirectory $env:TEMP
} else {
    # có file dự án lưu trong thư mục cài: chỉ xóa file phần mềm, giữ file dự án
    Get-ChildItem -LiteralPath $dich -Recurse -Force | Where-Object { -not $_.PSIsContainer -and $_.Extension -ne '.pabt' -and $_.Extension -ne '.pabtdt' } |
        Remove-Item -Force -ErrorAction SilentlyContinue
    Get-ChildItem -LiteralPath $dich -Recurse -Force | Where-Object { $_.PSIsContainer } | Sort-Object { $_.FullName.Length } -Descending |
        Where-Object { @(Get-ChildItem -LiteralPath $_.FullName -Force).Count -eq 0 } | Remove-Item -Force -ErrorAction SilentlyContinue
    $tb = "Đã gỡ PABT. Giữ lại $($giu.Count) file dự án trong $dich."
}
if (-not $Im) { [System.Windows.Forms.MessageBox]::Show($tb, 'Gỡ cài đặt PABT', 'OK', 'Information') | Out-Null }
exit 0

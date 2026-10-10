# Gỡ PABT (cài cho người dùng hiện tại). Dữ liệu dự án (.pabt) của người dùng không bị xóa.
param([switch]$Im)
Add-Type -AssemblyName System.Windows.Forms
$dich = Split-Path -Parent $MyInvocation.MyCommand.Definition   # PowerShell 2.0 (Windows 7)
if (-not $Im) {
    $tl = [System.Windows.Forms.MessageBox]::Show("Gỡ PABT khỏi máy?`n(Các file dự án .pabt của bạn được giữ nguyên.)", 'Gỡ cài đặt PABT', 'YesNo', 'Question')
    if ($tl -ne 'Yes') { exit 2 }
}
Get-Process PABT -ErrorAction SilentlyContinue | Where-Object { $_.Path -like "$dich*" } | Stop-Process -Force
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
Remove-Item (Join-Path $env:APPDATA 'PABT\cap_nhat') -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\PABT' -Recurse -Force -ErrorAction SilentlyContinue
$giu = @(Get-ChildItem $dich -Recurse -Force -Include '*.pabt', '*.pabtdt' -ErrorAction SilentlyContinue)
$tb = 'Đã gỡ PABT.'
if ($giu.Count -eq 0) {
    # xóa thư mục cài sau khi script này thoát
    Start-Process cmd.exe -ArgumentList "/c timeout /t 2 /nobreak >nul & rmdir /s /q `"$dich`"" -WindowStyle Hidden
} else {
    # có file dự án lưu trong thư mục cài: chỉ xóa file phần mềm, giữ file dự án
    Get-ChildItem $dich -Recurse -Force | Where-Object { -not $_.PSIsContainer -and $_.Extension -ne '.pabt' -and $_.Extension -ne '.pabtdt' } |
        Remove-Item -Force -ErrorAction SilentlyContinue
    Get-ChildItem $dich -Recurse -Force | Where-Object { $_.PSIsContainer } | Sort-Object { $_.FullName.Length } -Descending |
        Where-Object { @(Get-ChildItem $_.FullName -Force).Count -eq 0 } | Remove-Item -Force -ErrorAction SilentlyContinue
    $tb = "Đã gỡ PABT. Giữ lại $($giu.Count) file dự án trong $dich."
}
if (-not $Im) { [System.Windows.Forms.MessageBox]::Show($tb, 'Gỡ cài đặt PABT', 'OK', 'Information') | Out-Null }
exit 0

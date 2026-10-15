"""Tiêu chuẩn cài đặt chung của hai bộ cài (0.9.21 - người dùng yêu cầu "máy nào cũng cài được"): giữ các điều kiện đã kiểm
khi thử cài thật, để lần sửa sau không vô tình làm hỏng."""
from __future__ import annotations
import subprocess
import sys
import unittest
from pathlib import Path

GOC = Path(__file__).resolve().parents[1]
BC = GOC / 'bo_cai_win'
sys.path.insert(0, str(BC))


class TestKichBanCai(unittest.TestCase):
    def test_trinh_khoi_chay_ascii_va_chay_bang_command(self):
        b = (BC / 'CAI_DAT.cmd').read_bytes()
        self.assertTrue(b.isascii(), 'cmd đọc file .cmd theo bảng mã OEM: chỉ được chữ ASCII')
        s = b.decode()
        self.assertIn('-Command', s)
        self.assertIn('[scriptblock]::Create', s)                   # không -File: ExecutionPolicy / Group Policy chặn -File
        self.assertNotRegex(s, r'(?im)^[^r].*powershell[^\n]*-File ')

    def test_script_co_bom_utf8(self):
        for ten in ('cai_dat.ps1', 'go_cai_dat.ps1'):
            # PowerShell 2.0 / 5.1 đọc .ps1 không BOM theo bảng mã ANSI của máy: chữ Việt hỏng, có thể vỡ cú pháp
            self.assertEqual((BC / ten).read_bytes()[:3], b'\xef\xbb\xbf', ten)

    def test_khong_dung_include_voi_literalpath_va_lenh_ps3(self):
        for ten in ('cai_dat.ps1', 'go_cai_dat.ps1'):
            s = (BC / ten).read_text(encoding='utf-8-sig')
            for dong in (d.split('#', 1)[0] for d in s.splitlines()):
                if '-LiteralPath' in dong:
                    # -Include không có tác dụng với -LiteralPath (trả về MỌI file - go_cai_dat từng giữ lại cả thư mục cài)
                    self.assertNotIn('-Include', dong, dong)
            ma = '\n'.join(d.split('#', 1)[0] for d in s.splitlines())          # bỏ chú thích
            for lenh in ('$PSScriptRoot', ' -Raw', ' -in ', ' -notin ', '[ordered]', '[pscustomobject]', 'Get-CimInstance',
                         'ConvertFrom-Json', 'Invoke-WebRequest', '.ForEach(', '.Where(', 'ZipFile'):
                self.assertNotIn(lenh, ma, f'{ten}: {lenh} cần PowerShell 3+ / .NET 4.5 (Windows 7 chỉ có 2.0)')

    def test_go_cai_dat_dung_command(self):
        s = (BC / 'cai_dat.ps1').read_text(encoding='utf-8-sig')
        i = s.index("$go = ")
        self.assertIn('-Command', s[i:i + 400])
        self.assertNotIn('-File', s[i:i + 400])

    def test_go_cai_dat_khong_mo_cua_so_powershell(self):
        """11/10/2026: nút Gỡ của Windows chạy thẳng powershell.exe -> Windows 11 mở cửa sổ Windows Terminal trống suốt lúc gỡ.
        UninstallString = PABT.exe go-cai-dat (ứng dụng cửa sổ) -> PowerShell CREATE_NO_WINDOW, thoát ngay."""
        import tempfile
        from unittest import mock
        s = (BC / 'cai_dat.ps1').read_text(encoding='utf-8-sig')
        self.assertIn("$goAn = \"`\"$exe`\" go-cai-dat\"", s)
        self.assertIn("@('UninstallString', $goAn)", s)
        self.assertIn("@('QuietUninstallString', $goIm)", s)                # gỡ im lặng: công cụ quản trị chờ lệnh xong
        sys.path.insert(0, str(GOC))
        import chay
        with tempfile.TemporaryDirectory() as td:
            exe = Path(td) / "Thu muc O'Neil" / 'PABT.exe'
            exe.parent.mkdir()
            (exe.parent / 'go_cai_dat.ps1').write_text('#', encoding='utf-8')
            with mock.patch.object(sys, 'frozen', True, create=True), mock.patch.object(sys, 'executable', str(exe)), \
                    mock.patch('subprocess.Popen') as popen:
                self.assertEqual(chay.main(['go-cai-dat']), 0)
                self.assertEqual(chay.main(['go-cai-dat', '-Im']), 0)
            (a1, k1), (a2, _) = popen.call_args_list[0], popen.call_args_list[1]
            self.assertEqual(k1['creationflags'], subprocess.CREATE_NO_WINDOW)
            lenh = a1[0][-1]
            self.assertIn(str(exe.parent / 'go_cai_dat.ps1').replace("'", "''"), lenh)
            self.assertIn(f"-Dich '{str(exe.parent).replace(chr(39), chr(39) * 2)}'", lenh)
            self.assertFalse(lenh.endswith('-Im'))
            self.assertTrue(a2[0][-1].endswith(' -Im'))
            (exe.parent / 'go_cai_dat.ps1').unlink()
            with mock.patch.object(sys, 'frozen', True, create=True), mock.patch.object(sys, 'executable', str(exe)):
                self.assertEqual(chay.main(['go-cai-dat']), 1)                 # không có script gỡ: báo lỗi, không chạy gì

    def test_sed_iexpress(self):
        import dung_bo_cai_win as d
        sed = d._sed(Path('X'), Path('Y'), ['a'])
        # ".\" tường minh: máy bật NoDefaultCurrentDirectoryInExePath thì "cmd /c CAI_DAT.cmd" không chạy (bộ cài thoát im lặng)
        self.assertIn('AppLaunched=cmd.exe /c .\\CAI_DAT.cmd', sed)
        self.assertIn('UserQuietInstCmd=cmd.exe /c .\\CAI_DAT.cmd -Im', sed)
        self.assertIsNone(d.BAN['win7']['vc'])                   # không cài Visual C++ (cần quyền quản trị): đã đóng sẵn
        self.assertIsNone(d.BAN['win10']['vc'])

    def test_kem_ban_cap_nhat_windows7(self):
        # bộ cài Win7-8 kèm KB3063858 x86 + x64 (Python 3.8 cần KB2533623); cai_dat.ps1 chọn theo kiến trúc WINDOWS, cài bằng wusa
        import dung_bo_cai_win as d
        self.assertEqual(set(d.BAN['win7']['kb']), {'Windows6.1-KB3063858-x86.msu', 'Windows6.1-KB3063858-x64.msu'})
        self.assertEqual(d.BAN['win10']['kb'], ())
        s = (BC / 'cai_dat.ps1').read_text(encoding='utf-8-sig')
        for ten in d.BAN['win7']['kb']:
            self.assertIn(ten, s)
        self.assertIn('Sysnative', s)                            # PowerShell 32-bit trên Windows 64-bit: wusa 64-bit thật
        self.assertIn('exit 3010', s)                            # cài im lặng: báo cần khởi động lại
        import hashlib
        for ten, bam in d.KB_WIN7.items():
            f = BC / ten
            if f.exists():                                       # file không đưa vào git: chỉ kiểm khi có trên máy dựng
                self.assertEqual(hashlib.sha256(f.read_bytes()).hexdigest(), bam, ten)

    def test_cai_vao_program_files(self):
        # 0.9.22 (người dùng chọn C:\Program Files (x86)\PABT: lỗi "Access ... denied", nút Cài đặt khóa luôn): thư mục không ghi
        # được -> CHỈ bước chép file chạy lại với quyền quản trị (-Verb RunAs, -ChiChep); lối tắt / registry HKCU / tự kiểm tra vẫn
        # quyền người dùng; lỗi thì mở lại nút để cài tiếp; gỡ cài cũng xin quyền quản trị khi thư mục không ghi được
        s = (BC / 'cai_dat.ps1').read_text(encoding='utf-8-sig')
        self.assertIn('[string]$ChiChep', s)
        self.assertIn('if (GhiDuoc $dich) { ChepVao $dich $tienDo } else { ChepQuyenQuanTri $dich $tienDo }', s)
        i = s.index('function ChepQuyenQuanTri')
        self.assertIn('-Verb RunAs', s[i:i + 2000])
        self.assertIn("-Goc '", s[i:i + 2000])                  # biến môi trường PABT_GOC không truyền sang tiến trình quản trị
        i = s.index('if ($ChiChep) {')
        self.assertNotIn('TaoLoiTat', s[i:s.index('# ---', i + 10)])  # tiến trình quản trị không tạo lối tắt / registry
        self.assertIn('$bCai.Enabled = $true; $bChon.Enabled = $true; $oThu.Enabled = $true', s)
        # mặc định Program Files (x86)\PABT (người dùng 11/10/2026; Windows 32-bit: Program Files); từ chối quyền quản trị ->
        # thư mục không cần quyền (cửa sổ chuyển sẵn, cài im lặng tự cài vào đó); bản cũ ở thư mục khác được gỡ (không 2 bản)
        self.assertIn("$PF = ${env:ProgramFiles(x86)}", s)
        self.assertIn("$MAC_DINH = Join-Path $PF 'PABT'", s)
        self.assertIn("$KHONG_QT = Join-Path $env:LOCALAPPDATA 'Programs\\PABT'", s)
        self.assertIn('$tk = Cai $KHONG_QT', s)
        self.assertIn('GoBanCu $cu $dich', s)
        g = (BC / 'go_cai_dat.ps1').read_text(encoding='utf-8-sig')
        self.assertIn('function GhiDuoc', g)
        self.assertIn('-Verb RunAs', g)
        for ten in ('$XOA_HET', '$XOA_GIU'):                     # lệnh xóa truyền qua dòng lệnh: không được có ngoặc kép
            i = g.index(ten + ' = ')
            self.assertNotIn('"', g[i:g.index('\n$', i + 5)], ten)

    @unittest.skipUnless(sys.platform == 'win32', 'cần PowerShell')
    def test_cu_phap_powershell(self):
        for ten in ('cai_dat.ps1', 'go_cai_dat.ps1'):
            lenh = ("$e = $null; [void][System.Management.Automation.PSParser]::Tokenize("
                    f"[IO.File]::ReadAllText('{BC / ten}'), [ref]$e); $e.Count")
            kq = subprocess.run(['powershell', '-NoProfile', '-Command', lenh], capture_output=True, text=True, timeout=120)
            self.assertEqual(kq.stdout.strip(), '0', f'{ten}: {kq.stdout} {kq.stderr}')

    def test_ten_larc_va_bieu_tuong_theo_phien_ban(self):
        # người dùng 15/10/2026: lối tắt Desktop "LARC", tên đầy đủ "LARC - Bồi thường, hỗ trợ, tái định cư", bộ cài LARC_Setup_Universal
        s = (BC / 'cai_dat.ps1').read_text(encoding='utf-8-sig')
        self.assertIn("$TEN = 'LARC - Bồi thường, hỗ trợ, tái định cư'", s)
        self.assertIn('$dk = Join-Path $thuDk "$TEN_NGAN.lnk"', s)
        self.assertIn("@('Publisher', $TEN_NGAN)", s)
        # biểu tượng mang số phiên bản (bộ đệm biểu tượng Windows giữ ảnh theo đường dẫn) + đổi biểu tượng lối tắt đã ghim taskbar
        self.assertIn('$ico = Join-Path $dich "LARC_$PHIEN_BAN.ico"', s)
        self.assertIn('DoiBieuTuong', s)
        self.assertIn('LamMoi()', s)
        self.assertIn("'HKCU:\\Software\\Classes\\.larc' -Value 'PABT.DuAn'", s)            # file dự án .larc (vẫn mở .pabt)
        g = (BC / 'go_cai_dat.ps1').read_text(encoding='utf-8-sig')
        self.assertIn("'LARC.lnk'", g)
        self.assertIn("''.larc''", g)                                                       # gỡ cài giữ file dự án .larc
        import dung_bo_cai_win as d
        self.assertIn(f'LARC_{d.phien_ban()}.ico', [t for t, _ in d._ds_chuong_trinh('win10')]
                      if (GOC / 'dist' / 'PABT' / 'PABT.exe').exists() else [f'LARC_{d.phien_ban()}.ico'])
        self.assertIn("f'LARC_Setup_Universal_{pb}.exe'", (BC / 'dung_bo_cai_win.py').read_text(encoding='utf-8'))
        self.assertTrue(d.DU_LIEU_CAM.search('du_an.larc'))


class TestThuVien(unittest.TestCase):
    def test_kiem_dll(self):
        import rut_gon
        self.assertTrue(rut_gon._api_win7('api-ms-win-core-file-l1-1-0.dll'))
        self.assertFalse(rut_gon._api_win7('api-ms-win-core-path-l1-1-0.dll'))      # Windows 8+: Win7 không có
        for dist, win7 in ((GOC / 'dist' / 'PABT_Win7', True), (GOC / 'dist' / 'PABT', False)):
            if (dist / 'PABT.exe').exists():
                self.assertEqual(rut_gon.kiem_dll(dist, win7), [], f'{dist.name} cần DLL không có sẵn trên Windows đích')


if __name__ == '__main__':
    unittest.main()

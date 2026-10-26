package vn.larc.field;

import android.Manifest;
import android.app.Activity;
import android.app.AlertDialog;
import android.content.ActivityNotFoundException;
import android.content.ClipData;
import android.content.DialogInterface;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.content.res.AssetManager;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.provider.MediaStore;
import android.webkit.GeolocationPermissions;
import android.webkit.JavascriptInterface;
import android.webkit.ValueCallback;
import android.webkit.WebChromeClient;
import android.webkit.WebResourceRequest;
import android.webkit.WebResourceResponse;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.Toast;

import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.nio.charset.Charset;

/** LARC Field Mobile: WebView chạy assets/index.html qua địa chỉ https://appassets.androidplatform.net/ (miền dành riêng cho nội dung
 *  của ứng dụng - "ngữ cảnh an toàn": định vị GPS, IndexedDB chạy như trang https). Không tải gì từ mạng; liên kết ngoài mở trình duyệt.
 *  Cầu nối JS "LARCAndroid": luuFile(tên, nội dung) -> hộp Gửi (Zalo, email…) / Lưu vào thư mục. Ô chọn ảnh: chọn ảnh hoặc chụp ảnh. */
public class MainActivity extends Activity {
    static final String MIEN = "appassets.androidplatform.net";
    static final String GOC = "https://" + MIEN + "/";
    static final int MA_CHON = 11, MA_LUU = 12, MA_GPS = 13;

    WebView web;
    ValueCallback<Uri[]> choChon;
    File anhChup;
    File tepLuu;
    GeolocationPermissions.Callback gpsCb;
    String gpsNguon;

    @Override protected void onCreate(Bundle trangThai) {
        super.onCreate(trangThai);
        if (Build.VERSION.SDK_INT >= 21) getWindow().setStatusBarColor(0xFF1E3F6E);
        web = new WebView(this);
        WebSettings s = web.getSettings();
        s.setJavaScriptEnabled(true);
        s.setDomStorageEnabled(true);
        s.setDatabaseEnabled(true);
        s.setGeolocationEnabled(true);
        s.setAllowFileAccess(false);
        s.setAllowContentAccess(true);              // ảnh / file người dùng chọn (content://)
        s.setMediaPlaybackRequiresUserGesture(true);
        s.setSupportZoom(false);
        web.setWebViewClient(new WebViewClient() {
            @Override public WebResourceResponse shouldInterceptRequest(WebView v, WebResourceRequest r) {
                return tuAssets(r.getUrl());
            }
            @Override public boolean shouldOverrideUrlLoading(WebView v, WebResourceRequest r) {
                Uri u = r.getUrl();
                if (MIEN.equals(u.getHost())) return false;
                try { startActivity(new Intent(Intent.ACTION_VIEW, u)); } catch (ActivityNotFoundException e) { /* không có trình duyệt */ }
                return true;
            }
        });
        web.setWebChromeClient(new WebChromeClient() {
            @Override public void onGeolocationPermissionsShowPrompt(String nguon, GeolocationPermissions.Callback cb) {
                if (coQuyenGps()) { cb.invoke(nguon, true, false); return; }
                gpsCb = cb;
                gpsNguon = nguon;
                requestPermissions(new String[]{Manifest.permission.ACCESS_FINE_LOCATION, Manifest.permission.ACCESS_COARSE_LOCATION}, MA_GPS);
            }
            @Override public boolean onShowFileChooser(WebView v, ValueCallback<Uri[]> cb, FileChooserParams p) {
                return moChonTep(cb, p);
            }
        });
        web.addJavascriptInterface(new CauNoi(), "LARCAndroid");
        if (trangThai != null) web.restoreState(trangThai);
        if (web.getUrl() == null) web.loadUrl(GOC + "index.html");
        setContentView(web);
    }

    boolean coQuyenGps() {
        return Build.VERSION.SDK_INT < 23 || checkSelfPermission(Manifest.permission.ACCESS_FINE_LOCATION) == PackageManager.PERMISSION_GRANTED
            || checkSelfPermission(Manifest.permission.ACCESS_COARSE_LOCATION) == PackageManager.PERMISSION_GRANTED;
    }

    static String kieu(String p) {
        if (p.endsWith(".html")) return "text/html";
        if (p.endsWith(".js")) return "application/javascript";
        if (p.endsWith(".json") || p.endsWith(".webmanifest")) return "application/json";
        if (p.endsWith(".png")) return "image/png";
        if (p.endsWith(".css")) return "text/css";
        return "application/octet-stream";
    }

    WebResourceResponse tuAssets(Uri u) {
        if (u == null || !MIEN.equals(u.getHost())) return null;
        String p = u.getPath() == null ? "" : u.getPath();
        while (p.startsWith("/")) p = p.substring(1);
        if (p.isEmpty()) p = "index.html";
        if (p.contains("..")) return new WebResourceResponse("text/plain", "utf-8", 404, "Not Found", null, null);
        try {
            InputStream vao = getAssets().open(p, AssetManager.ACCESS_STREAMING);
            return new WebResourceResponse(kieu(p), "utf-8", vao);
        } catch (IOException e) {
            return new WebResourceResponse("text/plain", "utf-8", 404, "Not Found", null, null);
        }
    }

    boolean moChonTep(ValueCallback<Uri[]> cb, WebChromeClient.FileChooserParams p) {
        if (choChon != null) choChon.onReceiveValue(null);
        choChon = cb;
        boolean anh = false;
        for (String t : p.getAcceptTypes()) if (t != null && t.startsWith("image")) anh = true;
        Intent lay = new Intent(Intent.ACTION_GET_CONTENT);
        lay.addCategory(Intent.CATEGORY_OPENABLE);
        lay.setType(anh ? "image/*" : "*/*");
        if (p.getMode() == WebChromeClient.FileChooserParams.MODE_OPEN_MULTIPLE) lay.putExtra(Intent.EXTRA_ALLOW_MULTIPLE, true);
        Intent chon = Intent.createChooser(lay, anh ? "Chọn ảnh hoặc chụp ảnh" : "Chọn file");
        anhChup = null;
        if (anh) {
            File thu = new File(getCacheDir(), "anh");
            thu.mkdirs();
            anhChup = new File(thu, "chup_" + System.currentTimeMillis() + ".jpg");
            Intent may = new Intent(MediaStore.ACTION_IMAGE_CAPTURE);
            may.putExtra(MediaStore.EXTRA_OUTPUT, CungCapTep.uri(anhChup, getCacheDir()));
            may.addFlags(Intent.FLAG_GRANT_WRITE_URI_PERMISSION | Intent.FLAG_GRANT_READ_URI_PERMISSION);
            if (may.resolveActivity(getPackageManager()) != null) chon.putExtra(Intent.EXTRA_INITIAL_INTENTS, new Intent[]{may});
        }
        try {
            startActivityForResult(chon, MA_CHON);
            return true;
        } catch (ActivityNotFoundException e) {
            choChon = null;
            cb.onReceiveValue(null);
            return false;
        }
    }

    @Override protected void onActivityResult(int ma, int kq, Intent du) {
        if (ma == MA_CHON) {
            Uri[] ra = null;
            if (kq == RESULT_OK) {
                ClipData clip = du == null ? null : du.getClipData();
                if (clip != null && clip.getItemCount() > 0) {
                    ra = new Uri[clip.getItemCount()];
                    for (int i = 0; i < ra.length; i++) ra[i] = clip.getItemAt(i).getUri();
                } else if (du != null && du.getData() != null) {
                    ra = new Uri[]{du.getData()};
                } else if (anhChup != null && anhChup.length() > 0) {
                    ra = new Uri[]{CungCapTep.uri(anhChup, getCacheDir())};
                }
            }
            if (choChon != null) choChon.onReceiveValue(ra);
            choChon = null;
            return;
        }
        if (ma == MA_LUU && tepLuu != null) {
            if (kq == RESULT_OK && du != null && du.getData() != null) {
                try (InputStream vao = new FileInputStream(tepLuu); OutputStream ra = getContentResolver().openOutputStream(du.getData())) {
                    if (ra == null) throw new IOException("Không mở được nơi lưu");
                    byte[] b = new byte[65536];
                    int n;
                    while ((n = vao.read(b)) > 0) ra.write(b, 0, n);
                    bao("Đã lưu " + tepLuu.getName());
                } catch (IOException e) {
                    bao("Không lưu được: " + e.getMessage());
                }
            }
            return;
        }
        super.onActivityResult(ma, kq, du);
    }

    @Override public void onRequestPermissionsResult(int ma, String[] quyen, int[] kq) {
        if (ma == MA_GPS && gpsCb != null) {
            gpsCb.invoke(gpsNguon, coQuyenGps(), false);
            gpsCb = null;
        }
    }

    void bao(String chu) { Toast.makeText(this, chu, Toast.LENGTH_LONG).show(); }

    void hoiLuu(String ten, String noiDung) {
        String sach = ten == null ? "" : ten.replaceAll("[\\\\/:*?\"<>|]", "_");
        if (sach.isEmpty()) sach = "ket_qua_kiem_dem.json";
        File thu = new File(getCacheDir(), "xuat");
        thu.mkdirs();
        final File f = new File(thu, sach);
        try (OutputStream ra = new FileOutputStream(f)) {
            ra.write(noiDung.getBytes(Charset.forName("UTF-8")));
        } catch (IOException e) {
            bao("Không ghi được file: " + e.getMessage());
            return;
        }
        new AlertDialog.Builder(this).setTitle(sach)
            .setItems(new CharSequence[]{"Gửi đi (Zalo, email, Drive…)", "Lưu vào thư mục trên máy"}, new DialogInterface.OnClickListener() {
                @Override public void onClick(DialogInterface d, int i) {
                    if (i == 0) guiDi(f); else luuVao(f);
                }
            }).setNegativeButton("Hủy", null).show();
    }

    void guiDi(File f) {
        Intent gui = new Intent(Intent.ACTION_SEND);
        gui.setType("application/json");
        Uri u = CungCapTep.uri(f, getCacheDir());
        gui.putExtra(Intent.EXTRA_STREAM, u);
        gui.putExtra(Intent.EXTRA_SUBJECT, f.getName());
        gui.setClipData(ClipData.newRawUri(f.getName(), u));
        gui.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION);
        try { startActivity(Intent.createChooser(gui, "Gửi " + f.getName())); } catch (ActivityNotFoundException e) { bao("Không có ứng dụng để gửi file."); }
    }

    void luuVao(File f) {
        tepLuu = f;
        Intent luu = new Intent(Intent.ACTION_CREATE_DOCUMENT);
        luu.addCategory(Intent.CATEGORY_OPENABLE);
        luu.setType("application/json");
        luu.putExtra(Intent.EXTRA_TITLE, f.getName());
        try { startActivityForResult(luu, MA_LUU); } catch (ActivityNotFoundException e) { bao("Máy không có trình quản lý file."); }
    }

    class CauNoi {
        @JavascriptInterface public void luuFile(final String ten, final String noiDung) {
            runOnUiThread(new Runnable() { @Override public void run() { hoiLuu(ten, noiDung); } });
        }
        @JavascriptInterface public String phienBan() { return BuildConfigTen.PHIEN_BAN; }
    }

    @Override protected void onSaveInstanceState(Bundle ra) {
        super.onSaveInstanceState(ra);
        web.saveState(ra);
    }

    @Override public void onBackPressed() {
        if (web.canGoBack()) web.goBack(); else moveTaskToBack(true);   // giữ ứng dụng (dữ liệu đã lưu liên tục), không thoát hẳn
    }

    @Override protected void onDestroy() {
        if (web != null) web.destroy();
        super.onDestroy();
    }
}

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
import android.graphics.Bitmap;
import android.graphics.BitmapFactory;
import android.graphics.Matrix;
import android.media.ExifInterface;
import android.net.Uri;
import android.util.Base64;
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

import java.io.ByteArrayOutputStream;
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
    static final int MA_CHON = 11, MA_LUU = 12, MA_GPS = 13, MA_CHUP = 14;

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
        // không restoreState: Activity đã khai configChanges (xoay màn hình không dựng lại); khôi phục trạng thái WebView làm mất biến JS
        // dữ liệu dự án (window.LARC_DU_LIEU) - luôn nạp lại trang, vỏ ứng dụng tự mở dự án đang dùng từ IndexedDB
        web.loadUrl(GOC + "index.html");
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
        if (anh) chon.putExtra(Intent.EXTRA_INITIAL_INTENTS, new Intent[]{yDinhChup()});   // luôn có lựa chọn Máy ảnh (manifest <queries>)
        try {
            startActivityForResult(chon, MA_CHON);
            return true;
        } catch (ActivityNotFoundException e) {
            choChon = null;
            cb.onReceiveValue(null);
            return false;
        }
    }

    /** Ý định mở máy ảnh ghi ảnh vào cache/anh/chup_<giờ>.jpg (qua CungCapTep - máy ảnh ghi được, không cần quyền bộ nhớ). */
    Intent yDinhChup() {
        File thu = new File(getCacheDir(), "anh");
        thu.mkdirs();
        anhChup = new File(thu, "chup_" + System.currentTimeMillis() + ".jpg");
        Intent may = new Intent(MediaStore.ACTION_IMAGE_CAPTURE);
        Uri u = CungCapTep.uri(anhChup, getCacheDir());
        may.putExtra(MediaStore.EXTRA_OUTPUT, u);
        may.setClipData(ClipData.newRawUri("anh", u));
        may.addFlags(Intent.FLAG_GRANT_WRITE_URI_PERMISSION | Intent.FLAG_GRANT_READ_URI_PERMISSION);
        return may;
    }

    /** Nút "Chụp ảnh biên bản": mở thẳng máy ảnh, ảnh thu về <= CO_ANH px (xoay theo EXIF) rồi gửi cho JS LARC_nhanAnhAndroid(dataUrl, tên). */
    void chupAnh() {
        try {
            startActivityForResult(yDinhChup(), MA_CHUP);
        } catch (ActivityNotFoundException e) {
            bao("Máy không có ứng dụng máy ảnh.");
        }
    }

    static final int CO_ANH = 1600;

    void guiAnhChoJs(final File f) {
        new Thread(new Runnable() { @Override public void run() {
            final String url = docAnhThuNho(f);
            runOnUiThread(new Runnable() { @Override public void run() {
                if (url == null) { bao("Không đọc được ảnh vừa chụp."); return; }
                web.evaluateJavascript("window.LARC_nhanAnhAndroid && window.LARC_nhanAnhAndroid('" + url + "', '" + f.getName() + "')", null);
            } });
        } }).start();
    }

    static String docAnhThuNho(File f) {
        try {
            BitmapFactory.Options o = new BitmapFactory.Options();
            o.inJustDecodeBounds = true;
            BitmapFactory.decodeFile(f.getPath(), o);
            int mau = 1;
            while (Math.max(o.outWidth, o.outHeight) / (mau * 2) >= CO_ANH) mau *= 2;
            BitmapFactory.Options o2 = new BitmapFactory.Options();
            o2.inSampleSize = mau;
            Bitmap b = BitmapFactory.decodeFile(f.getPath(), o2);
            if (b == null) return null;
            float k = Math.min(1f, (float) CO_ANH / Math.max(b.getWidth(), b.getHeight()));
            Matrix m = new Matrix();
            m.postScale(k, k);
            int xoay = new ExifInterface(f.getPath()).getAttributeInt(ExifInterface.TAG_ORIENTATION, ExifInterface.ORIENTATION_NORMAL);
            if (xoay == ExifInterface.ORIENTATION_ROTATE_90) m.postRotate(90);
            else if (xoay == ExifInterface.ORIENTATION_ROTATE_180) m.postRotate(180);
            else if (xoay == ExifInterface.ORIENTATION_ROTATE_270) m.postRotate(270);
            Bitmap r = Bitmap.createBitmap(b, 0, 0, b.getWidth(), b.getHeight(), m, true);
            ByteArrayOutputStream ra = new ByteArrayOutputStream();
            r.compress(Bitmap.CompressFormat.JPEG, 82, ra);
            return "data:image/jpeg;base64," + Base64.encodeToString(ra.toByteArray(), Base64.NO_WRAP);
        } catch (IOException | RuntimeException | OutOfMemoryError e) {
            return null;
        }
    }

    @Override protected void onActivityResult(int ma, int kq, Intent du) {
        if (ma == MA_CHUP) {
            if (kq == RESULT_OK && anhChup != null && anhChup.length() > 0) guiAnhChoJs(anhChup);
            return;
        }
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
        @JavascriptInterface public void chupAnhNgay() {
            runOnUiThread(new Runnable() { @Override public void run() { chupAnh(); } });
        }
    }

    @Override public void onBackPressed() {
        // hỏi trang trước: LARC_quayLai() đóng hộp xem ảnh / màn hình dự án / về thẻ 0 -> true; đang ở thẻ 0 thì giữ ứng dụng chạy nền
        web.evaluateJavascript("Boolean(window.LARC_quayLai && window.LARC_quayLai())", new ValueCallback<String>() {
            @Override public void onReceiveValue(String v) {
                if (!"true".equals(v)) moveTaskToBack(true);
            }
        });
    }

    @Override protected void onDestroy() {
        if (web != null) web.destroy();
        super.onDestroy();
    }
}

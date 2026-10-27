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
import android.speech.RecognitionListener;
import android.speech.RecognizerIntent;
import android.speech.SpeechRecognizer;
import android.webkit.GeolocationPermissions;
import android.webkit.JavascriptInterface;
import android.webkit.PermissionRequest;
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
import java.util.ArrayList;

import org.json.JSONObject;

/** LARC Mobile: WebView chạy assets/index.html qua địa chỉ https://appassets.androidplatform.net/ (miền dành riêng cho nội dung
 *  của ứng dụng - "ngữ cảnh an toàn": định vị GPS, IndexedDB chạy như trang https). Không tải gì từ mạng; liên kết ngoài mở trình duyệt.
 *  Cầu nối JS "LARCAndroid": luuFile(tên, nội dung) -> hộp Gửi (Zalo, email…) / Lưu vào thư mục. Ô chọn ảnh: chọn ảnh hoặc chụp ảnh. */
public class MainActivity extends Activity {
    static final String MIEN = "appassets.androidplatform.net";
    static final String GOC = "https://" + MIEN + "/";
    static final int MA_CHON = 11, MA_LUU = 12, MA_GPS = 13, MA_CHUP = 14, MA_NOI = 15, MA_MIC = 16, MA_GHI_AM = 17;

    WebView web;
    ValueCallback<Uri[]> choChon;
    File anhChup;
    File tepLuu;
    GeolocationPermissions.Callback gpsCb;
    PermissionRequest ghiAmCho;      // trang xin micrô (getUserMedia - "Ghi file âm thanh") đang chờ người dùng cho phép RECORD_AUDIO
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
            // "Ghi file âm thanh" của trang (getUserMedia + MediaRecorder): chỉ cấp micrô cho chính trang ứng dụng (assets), xin quyền
            // RECORD_AUDIO của Android lúc cần; mọi quyền khác (máy ảnh, MIDI...) từ chối
            @Override public void onPermissionRequest(final PermissionRequest yc) {
                runOnUiThread(new Runnable() { @Override public void run() {
                    boolean am = false;
                    for (String r : yc.getResources()) if (PermissionRequest.RESOURCE_AUDIO_CAPTURE.equals(r)) am = true;
                    if (!am || yc.getOrigin() == null || !MIEN.equals(yc.getOrigin().getHost())) { yc.deny(); return; }
                    if (Build.VERSION.SDK_INT < 23 || checkSelfPermission(Manifest.permission.RECORD_AUDIO) == PackageManager.PERMISSION_GRANTED) {
                        yc.grant(new String[]{PermissionRequest.RESOURCE_AUDIO_CAPTURE});
                        return;
                    }
                    if (ghiAmCho != null) ghiAmCho.deny();
                    ghiAmCho = yc;
                    requestPermissions(new String[]{Manifest.permission.RECORD_AUDIO}, MA_GHI_AM);
                }});
            }
            @Override public void onPermissionRequestCanceled(PermissionRequest yc) {
                if (yc == ghiAmCho) ghiAmCho = null;
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

    /** Nút "Nhập giọng nói": bộ nhận dạng giọng nói của Android (RecognizerIntent - không cần quyền RECORD_AUDIO), ưu tiên gói tiếng Việt
     *  ngoại tuyến của máy (EXTRA_PREFER_OFFLINE); chữ nhận được gửi cho JS LARC_nhanGiongNoiAndroid(chữ). Máy không có bộ nhận dạng:
     *  LARC_giongNoiLoi('khong_co') -> trang hướng dẫn dùng micro của bàn phím. */
    void batDauGiongNoi() {
        Intent noi = new Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH);
        noi.putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL, RecognizerIntent.LANGUAGE_MODEL_FREE_FORM);
        noi.putExtra(RecognizerIntent.EXTRA_LANGUAGE, "vi-VN");
        noi.putExtra(RecognizerIntent.EXTRA_LANGUAGE_PREFERENCE, "vi-VN");
        noi.putExtra(RecognizerIntent.EXTRA_PROMPT, "Đọc thông tin hộ, nhà, vật kiến trúc, cây trồng...");
        noi.putExtra(RecognizerIntent.EXTRA_MAX_RESULTS, 1);
        if (Build.VERSION.SDK_INT >= 23) noi.putExtra(RecognizerIntent.EXTRA_PREFER_OFFLINE, true);
        try {
            startActivityForResult(noi, MA_NOI);
        } catch (ActivityNotFoundException e) {
            ngheQuaDichVu();     // máy không có màn hình nhập giọng nói (không có ứng dụng Google, máy giả lập…): dùng thẳng dịch vụ nhận dạng
        }
    }

    // ---- dự phòng: SpeechRecognizer (dịch vụ nhận dạng của máy, vd "Dịch vụ lời nói của Google", Samsung) - cần quyền micro, hỏi khi dùng lần đầu.
    //      Trang hiện sóng âm + chữ đang nghe (LARC_giongNoiTrangThai / LARC_giongNoiTam), nút Xong = LARCAndroid.dungGiongNoi().
    SpeechRecognizer nghe;

    void js(String ham, String doi) {
        web.evaluateJavascript("window." + ham + " && window." + ham + "(" + JSONObject.quote(doi == null ? "" : doi) + ")", null);
    }

    void ngheQuaDichVu() {
        boolean dv = SpeechRecognizer.isRecognitionAvailable(this);
        boolean tren_may = Build.VERSION.SDK_INT >= 31 && SpeechRecognizer.isOnDeviceRecognitionAvailable(this);
        if (!dv && !tren_may) { js("LARC_giongNoiLoi", "khong_co"); return; }
        if (Build.VERSION.SDK_INT >= 23 && checkSelfPermission(Manifest.permission.RECORD_AUDIO) != PackageManager.PERMISSION_GRANTED) {
            requestPermissions(new String[]{Manifest.permission.RECORD_AUDIO}, MA_MIC);
            return;
        }
        huyNghe();
        nghe = dv ? SpeechRecognizer.createSpeechRecognizer(this) : SpeechRecognizer.createOnDeviceSpeechRecognizer(this);
        nghe.setRecognitionListener(new RecognitionListener() {
            @Override public void onReadyForSpeech(Bundle b) { js("LARC_giongNoiTrangThai", "nghe"); }
            @Override public void onBeginningOfSpeech() { }
            @Override public void onRmsChanged(float db) { }
            @Override public void onBufferReceived(byte[] b) { }
            @Override public void onEndOfSpeech() { js("LARC_giongNoiTrangThai", "xu_ly"); }
            @Override public void onPartialResults(Bundle b) { String c = dauTien(b); if (c != null) js("LARC_giongNoiTam", c); }
            @Override public void onEvent(int loai, Bundle b) { }
            @Override public void onResults(Bundle b) {
                String c = dauTien(b);
                if (c != null && !c.isEmpty()) js("LARC_nhanGiongNoiAndroid", c); else js("LARC_giongNoiLoi", "khong_nghe");
                huyNghe();
            }
            @Override public void onError(int ma) {
                String ly = ma == SpeechRecognizer.ERROR_NO_MATCH || ma == SpeechRecognizer.ERROR_SPEECH_TIMEOUT ? "khong_nghe"
                    : ma == SpeechRecognizer.ERROR_INSUFFICIENT_PERMISSIONS ? "quyen"
                    : ma == SpeechRecognizer.ERROR_NETWORK || ma == SpeechRecognizer.ERROR_NETWORK_TIMEOUT || ma == SpeechRecognizer.ERROR_SERVER ? "mang"
                    : ma == 12 || ma == 13 ? "ngon_ngu"           // ERROR_LANGUAGE_NOT_SUPPORTED / _UNAVAILABLE (API 31)
                    : "loi_" + ma;
                js("LARC_giongNoiLoi", ly);
                huyNghe();
            }
        });
        Intent noi = new Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH);
        noi.putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL, RecognizerIntent.LANGUAGE_MODEL_FREE_FORM);
        noi.putExtra(RecognizerIntent.EXTRA_LANGUAGE, "vi-VN");
        noi.putExtra(RecognizerIntent.EXTRA_PARTIAL_RESULTS, true);
        noi.putExtra(RecognizerIntent.EXTRA_MAX_RESULTS, 1);
        noi.putExtra(RecognizerIntent.EXTRA_SPEECH_INPUT_COMPLETE_SILENCE_LENGTH_MILLIS, 2500L);   // đọc liền một mạch: nghỉ 2,5 s mới xong
        if (Build.VERSION.SDK_INT >= 23) noi.putExtra(RecognizerIntent.EXTRA_PREFER_OFFLINE, true);
        try {
            nghe.startListening(noi);
        } catch (RuntimeException e) {
            js("LARC_giongNoiLoi", "khong_co");
            huyNghe();
        }
    }

    static String dauTien(Bundle b) {
        ArrayList<String> ds = b == null ? null : b.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION);
        return ds != null && !ds.isEmpty() ? ds.get(0) : null;
    }

    void huyNghe() {
        if (nghe != null) { try { nghe.destroy(); } catch (RuntimeException e) { /* đã hủy */ } nghe = null; }
    }

    /** Mở trang cài đặt ứng dụng nhận dạng giọng nói trên CH Play (chỉ các gói được phép). */
    void moCuaHang(String goi) {
        if (!"com.google.android.tts".equals(goi) && !"com.google.android.googlequicksearchbox".equals(goi)) return;
        try {
            startActivity(new Intent(Intent.ACTION_VIEW, Uri.parse("market://details?id=" + goi)));
        } catch (ActivityNotFoundException e) {
            try { startActivity(new Intent(Intent.ACTION_VIEW, Uri.parse("https://play.google.com/store/apps/details?id=" + goi))); }
            catch (ActivityNotFoundException e2) { bao("Máy không có CH Play / trình duyệt."); }
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
        if (ma == MA_NOI) {
            ArrayList<String> ds = kq == RESULT_OK && du != null ? du.getStringArrayListExtra(RecognizerIntent.EXTRA_RESULTS) : null;
            if (ds != null && !ds.isEmpty() && ds.get(0) != null) {
                // JSONObject.quote: chuỗi JS an toàn (nháy, xuống dòng, "</script>")
                web.evaluateJavascript("window.LARC_nhanGiongNoiAndroid && window.LARC_nhanGiongNoiAndroid(" + JSONObject.quote(ds.get(0)) + ")", null);
            } else {
                web.evaluateJavascript("window.LARC_giongNoiLoi && window.LARC_giongNoiLoi('huy')", null);
            }
            return;
        }
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
        if (ma == MA_GHI_AM && ghiAmCho != null) {
            if (kq.length > 0 && kq[0] == PackageManager.PERMISSION_GRANTED) ghiAmCho.grant(new String[]{PermissionRequest.RESOURCE_AUDIO_CAPTURE});
            else ghiAmCho.deny();
            ghiAmCho = null;
        }
        if (ma == MA_MIC) {
            if (kq.length > 0 && kq[0] == PackageManager.PERMISSION_GRANTED) ngheQuaDichVu(); else js("LARC_giongNoiLoi", "quyen");
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
        @JavascriptInterface public void batDauGiongNoi() {
            runOnUiThread(new Runnable() { @Override public void run() { MainActivity.this.batDauGiongNoi(); } });
        }
        @JavascriptInterface public void dungGiongNoi() {
            runOnUiThread(new Runnable() { @Override public void run() { if (nghe != null) nghe.stopListening(); } });
        }
        @JavascriptInterface public void moCuaHang(final String goi) {
            runOnUiThread(new Runnable() { @Override public void run() { MainActivity.this.moCuaHang(goi); } });
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
        huyNghe();
        if (web != null) web.destroy();
        super.onDestroy();
    }
}

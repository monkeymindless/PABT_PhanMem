package vn.larc.field;

import android.content.ContentProvider;
import android.content.ContentValues;
import android.database.Cursor;
import android.database.MatrixCursor;
import android.net.Uri;
import android.os.ParcelFileDescriptor;
import android.provider.OpenableColumns;

import java.io.File;
import java.io.FileNotFoundException;
import java.io.IOException;

/** Cấp file trong thư mục cache của ứng dụng cho ứng dụng khác (không dùng androidx FileProvider - dựng không Gradle):
 *  content://vn.larc.field.tep/anh/... = ảnh máy ảnh chụp ghi vào; content://vn.larc.field.tep/xuat/... = file .json gửi đi (Zalo, email…). */
public class CungCapTep extends ContentProvider {
    public static final String AUTHORITY = "vn.larc.field.tep";

    static Uri uri(File f, File goc) {
        String duong = goc.toURI().relativize(f.toURI()).getPath();
        return new Uri.Builder().scheme("content").authority(AUTHORITY).encodedPath("/" + duong).build();
    }

    File tep(Uri u) throws FileNotFoundException {
        try {
            File goc = getContext().getCacheDir().getCanonicalFile();
            String p = u.getPath() == null ? "" : u.getPath();
            File f = new File(goc, p).getCanonicalFile();
            if (!f.getPath().startsWith(goc.getPath() + File.separator)) throw new FileNotFoundException(p);
            return f;
        } catch (IOException e) {
            throw new FileNotFoundException(String.valueOf(u));
        }
    }

    @Override public boolean onCreate() { return true; }

    @Override public ParcelFileDescriptor openFile(Uri u, String mode) throws FileNotFoundException {
        File f = tep(u);
        if (mode.contains("w")) {
            File cha = f.getParentFile();
            if (cha != null) cha.mkdirs();
        }
        return ParcelFileDescriptor.open(f, ParcelFileDescriptor.parseMode(mode));
    }

    @Override public String getType(Uri u) {
        String p = String.valueOf(u.getPath()).toLowerCase();
        if (p.endsWith(".json")) return "application/json";
        if (p.endsWith(".jpg") || p.endsWith(".jpeg")) return "image/jpeg";
        if (p.endsWith(".png")) return "image/png";
        return "application/octet-stream";
    }

    @Override public Cursor query(Uri u, String[] cot, String chon, String[] thamSo, String sapXep) {
        File f;
        try { f = tep(u); } catch (FileNotFoundException e) { return null; }
        String[] ten = cot != null ? cot : new String[]{OpenableColumns.DISPLAY_NAME, OpenableColumns.SIZE};
        MatrixCursor c = new MatrixCursor(ten, 1);
        Object[] dong = new Object[ten.length];
        for (int i = 0; i < ten.length; i++) {
            if (OpenableColumns.DISPLAY_NAME.equals(ten[i])) dong[i] = f.getName();
            else if (OpenableColumns.SIZE.equals(ten[i])) dong[i] = f.length();
        }
        c.addRow(dong);
        return c;
    }

    @Override public Uri insert(Uri u, ContentValues v) { throw new UnsupportedOperationException(); }
    @Override public int delete(Uri u, String s, String[] a) { return 0; }
    @Override public int update(Uri u, ContentValues v, String s, String[] a) { return 0; }
}

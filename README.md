# Deteksi Titik dan Deteksi Tepi Prewitt

Tugas Kelompok 4 mata kuliah Analisis Data Citra Biomedik (ADCB) tentang
deteksi titik, garis, dan tepi pada citra digital.

Bagian yang dikerjakan dalam repositori ini:

- Nomor 1: dua citra masukan yang diubah ke citra keabuan.
- Nomor 2a: deteksi titik dengan mask 8 tetangga.
- Nomor 2c: deteksi tepi dengan operator Prewitt.

Deteksi garis (2b) serta operator Sobel, Roberts, dan kompas tidak termasuk
dalam bagian ini.

## Citra

| | Burj Khalifa | Jalan Route 66 |
|---|---|---|
| Berkas | `img/Burj_Khalifa.avif` | `img/D11_Williams_Route_66_1.avif` |
| Ukuran asli | 250 x 438 piksel | 3840 x 2560 piksel |
| Ukuran proses | 250 x 438 piksel | 800 x 533 piksel |

Citra Route 66 diperkecil ke lebar 800 piksel dengan interpolasi area. Citra
Burj Khalifa tidak diperbesar karena ukurannya sudah lebih kecil dari 800 piksel.

## Metode

1. Citra dibaca dari AVIF, diubah ke keabuan dengan rumus luminansi standar,
   lalu diproses pada ukuran yang telah ditentukan.
2. Konvolusi 3x3 diimplementasikan manual dengan NumPy dan diverifikasi
   terhadap `cv2.filter2D`. Selisih maksimum yang diperoleh 0,000000.
3. Deteksi titik memakai mask Laplacian 8 tetangga. Respons dihitung sebagai
   nilai mutlak hasil konvolusi, lalu titik ditandai dengan ambang persentil
   99,5 respons tiap citra.
4. Deteksi tepi Prewitt memakai mask `Gx` dan `Gy`, magnitudo
   `|G| = akar(Gx^2 + Gy^2)`, dan ambang tepi 200.
5. Analisis pengaruh ambang dilakukan dengan sapuan persentil 99, 99,5, 99,9,
   dan 99,99 untuk titik, serta ambang 100, 150, 200, dan 250 untuk Prewitt.

## Menjalankan

### Memakai lingkungan Python baru

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python src/deteksi.py
```

### Memakai lingkungan ADCB yang sudah ada

Dari direktori repositori ini:

```bash
uv run --project ../../.. python src/deteksi.py
```

Atau langsung memakai venv ADCB:

```bash
../../../.venv/bin/python src/deteksi.py
```

## Keluaran

```
output/
├── data.json                 seluruh angka hasil pemrosesan
├── ringkasan.md              tabel metrik dan sapuan ambang
├── analisis.md               analisis hasil
├── gambar/
│   ├── panel/                panel tunggal tanpa judul, resolusi asli
│   └── komposit/             gambar gabungan berjudul
└── tabel/                    metrik.csv, ambang_titik.csv, ambang_prewitt.csv
```

## Hasil utama

| Besaran | Burj Khalifa | Jalan Route 66 |
|---|---|---|
| Titik pada p99,5 | 552 titik, T=512 | 2148 titik, T=247 |
| Kepadatan titik | 0,504% | 0,504% |
| Kepadatan tepi Prewitt (T=200) | 3,837% | 1,386% |
| Rasio energi Gx : Gy | 1,53 | 0,81 |

Prewitt menghasilkan tepi yang lebih jelas daripada deteksi titik karena
keluarannya berupa kontur yang menyambung. Di antara kedua citra, Route 66
memberi hasil tepi paling bersih. Burj Khalifa terkendala tekstur fasad yang
padat dan resolusi yang rendah.

## Catatan

- Seluruh keluaran di `output/` dihasilkan ulang setiap kali `src/deteksi.py`
  dijalankan.
- Bila `img/Burj_Khalifa.avif` diganti dengan versi beresolusi lebih tinggi
  dengan nama yang sama, jalankan ulang program agar angka dan gambar
  diperbarui.
- Draf analisis lengkap tersedia di `output/analisis.md`.

# Analisis Hasil Deteksi Titik dan Deteksi Tepi Prewitt

## 1. Citra yang digunakan

| | Burj Khalifa | Jalan Route 66 |
|---|---|---|
| Berkas | `img/Burj_Khalifa.avif` | `img/D11_Williams_Route_66_1.avif` |
| Ukuran asli | 250 x 438 piksel | 3840 x 2560 piksel |
| Ukuran proses | 250 x 438 piksel | 800 x 533 piksel |
| Orientasi | Potret | Lanskap |
| Isi | Menara tinggi dengan fasad bertekstur, langit sebagian besar seragam, gedung kecil di kaki menara | Jalan lurus dengan marka tengah, garis tepi, vegetasi, tiang listrik, dan papan Route 66 |

Citra Route 66 diperkecil ke lebar 800 piksel dengan interpolasi area. Tujuannya
menekan biaya komputasi dan mengurangi tekstur aspal yang sangat halus. Citra
Burj Khalifa tidak diperbesar karena ukurannya sudah lebih kecil dari 800 piksel.
Perbedaan resolusi ini memengaruhi angka kepadatan tepi dan varians Laplacian,
sehingga kedua angka tersebut dipakai sebagai indikasi, bukan pembanding mutlak.

## Cara membaca gambar

1. Panel respons titik dan panel magnitudo ditampilkan dengan batas atas
   persentil 99,9 agar struktur lemah tetap terlihat. Piksel di atas batas itu
   tampak putih penuh. Nilai aslinya tetap dipakai untuk perhitungan ambang.
2. Panel biner memakai ambang yang tertulis pada judul panel.
3. Titik merah adalah titik yang lolos ambang. Penandanya dipertebal 2x2 atau
   3x3 piksel hanya untuk keperluan tampilan, bukan tambahan titik.
4. Pada gambar Prewitt, panel (a) sampai (e) berurutan: citra keabuan, `|Gx|`,
   `|Gy|`, magnitudo `|G|`, dan tepi biner.

## 2. Deteksi titik

Mask yang dipakai adalah Laplacian 8 tetangga:

```
-1  -1  -1
-1   8  -1
-1  -1  -1
```

Respons dihitung sebagai nilai mutlak jumlah hasil kali mask dengan 9 piksel di
sekitarnya. Mask ini mendekati turunan kedua dan bersifat isotropik, artinya
tidak memilih arah tertentu. Akibatnya, respons tinggi tidak hanya muncul pada
titik terisolasi, tetapi juga pada sudut, ujung garis, tekstur halus, dan derau.
Ambang ditetapkan dari persentil 99,5 respons tiap citra supaya jumlah titik yang
ditampilkan terkendali.

| Besaran | Burj Khalifa | Jalan Route 66 |
|---|---|---|
| Rerata respons titik | 33,71 | 37,82 |
| Maksimum respons titik | 1105,0 | 828,0 |
| Ambang p99,5 | 512,0 | 247,0 |
| Jumlah titik | 552 | 2148 |
| Kepadatan titik | 0,504% | 0,504% |

Kepadatan kedua citra hampir sama karena ambang memang ditetapkan dari persentil
yang sama. Perbedaan yang bermakna ada pada nilai ambang dan sebaran titik.
Ambang Burj Khalifa dua kali lebih tinggi daripada Route 66. Artinya, 0,5%
respons terkuat pada Burj Khalifa dimulai dari nilai yang jauh lebih tinggi.
Puncak responsnya juga lebih tinggi, yaitu 1105 berbanding 828. Sebaliknya,
rerata respons Route 66 lebih tinggi karena tekstur vegetasi dan permukaan jalan
menghasilkan respons menengah hampir di seluruh bidang.

Pada Burj Khalifa, titik terkonsentrasi di siluet menara, tonjolan fasad, dan
gedung di bagian kaki. Langit yang hampir seragam hampir tidak menghasilkan
titik. Titik-titik itu tidak membentuk garis, melainkan mengelompok di lokasi
perubahan intensitas yang tajam.

Pada Route 66, titik terkuat berada di tiang listrik, tepi vegetasi, dan tepi
papan Route 66. Marka tengah yang panjang tidak ditandai seluruhnya. Yang
ditandai hanya ujung atau sudutnya. Hasil ini menunjukkan bahwa deteksi titik
tidak dirancang untuk menarik garis, sehingga marka jalan yang berupa garis
panjang justru kurang tergambarkan.

Pengaruh ambang terlihat dari sapuan berikut:

| Persentil | Ambang Burj | Titik Burj | Ambang Route | Titik Route |
|---|---|---|---|---|
| 99 | 437,0 | 1099 | 212,0 | 4314 |
| 99,5 | 512,0 | 552 | 247,0 | 2148 |
| 99,9 | 664,0 | 111 | 343,0 | 428 |
| 99,99 | 868,3 | 11 | 663,1 | 43 |

Semakin tinggi ambang, semakin sedikit titik yang bertahan. Pada p99,99, Burj
Khalifa hanya menyisakan 11 titik yang tersebar di bagian kaki menara dan satu
titik di fasad, sedangkan Route 66 menyisakan 43 titik yang seluruhnya berada di
tiang listrik. Tiang listrik menjadi struktur paling menonjol pada deteksi titik
karena tipis, terang, dan dikelilingi latar yang relatif rata. Meskipun bentuknya
garis, lebarnya hanya satu sampai dua piksel sehingga respons Laplacian-nya
tinggi di hampir sepanjang tiang.

## 3. Deteksi tepi Prewitt

Operator Prewitt memakai dua mask 3x3:

```
Gx = -1  0  1      Gy = -1 -1 -1
     -1  0  1            0  0  0
     -1  0  1            1  1  1
```

`Gx` menghitung beda intensitas ke arah mendatar, sehingga kuat pada tepi
vertikal. `Gy` menghitung beda ke arah tegak, sehingga kuat pada tepi horizontal.
Kedua mask dapat dipandang sebagai turunan pertama yang disertai perataan tiga
piksel pada arah tegak lurusnya. Perataan ini menekan derau, tetapi membuat tepi
sedikit lebih tebal.

Magnitudo dihitung dengan `|G| = akar(Gx^2 + Gy^2)`. Ambang tepi ditetapkan 200
dalam satuan magnitudo, sama untuk kedua citra, lalu piksel dengan `|G| >= 200`
dianggap tepi.

| Besaran | Burj Khalifa | Jalan Route 66 |
|---|---|---|
| Rerata magnitudo | 27,07 | 32,01 |
| Maksimum magnitudo | 583,3 | 433,0 |
| Rasio energi Gx : Gy | 1,53 | 0,81 |
| Jumlah piksel tepi (T=200) | 4202 | 5910 |
| Kepadatan tepi (T=200) | 3,837% | 1,386% |

Pada Burj Khalifa, `Gx` lebih menonjol daripada `Gy`. Sisi kiri dan kanan
menara, garis fasad, serta tepi gedung di kaki menara berorientasi vertikal.
Rasio energi 1,53 sesuai dengan pengamatan visual tersebut. `Gy` terutama
muncul pada garis tonjolan, atap, dan batas horizontal di kaki menara.

Pada Route 66, `Gx` menonjol pada marka tengah dan tiang listrik, sedangkan `Gy`
menonjol pada horizon, permukaan jalan, dan papan Route 66. Rasio energi 0,81
berarti komponen horizontal sedikit lebih kuat. Tepi jalan berbentuk diagonal,
sehingga memberi sumbangan pada kedua komponen. Horizon yang membentang penuh
dan tekstur jalan menguatkan `Gy`.

Kepadatan tepi Burj Khalifa lebih tinggi daripada Route 66 pada ambang yang sama,
yaitu 3,84% berbanding 1,39%. Namun rerata magnitudo Route 66 justru lebih tinggi.
Perbedaan ini terjadi karena sebaran gradiennya berbeda. Burj Khalifa memiliki
banyak piksel hampir rata di langit dan beberapa tepi yang sangat tajam, sehingga
sebarannya berekor panjang. Route 66 memiliki gradien menengah yang tersebar
merata di vegetasi dan permukaan jalan, tetapi jarang mencapai nilai ekstrem.

Pengaruh ambang Prewitt terlihat dari sapuan berikut:

| Ambang | Kepadatan tepi Burj | Kepadatan tepi Route |
|---|---|---|
| 100 | 10,376% | 5,825% |
| 150 | 6,454% | 2,713% |
| 200 | 3,837% | 1,386% |
| 250 | 2,086% | 0,523% |

Pada ambang 100, tekstur fasad Burj Khalifa dan vegetasi Route 66 ikut terangkat,
sehingga hasilnya ramai dan sulit dibaca. Pada ambang 250, sebagian tepi jalan
Route 66 mulai hilang. Ambang 200 menjadi kompromi yang menampilkan kontur utama
tanpa terlalu banyak tekstur latar.

## 4. Perbandingan metode

| Aspek | Deteksi titik | Deteksi tepi Prewitt |
|---|---|---|
| Dasar perhitungan | Turunan kedua (Laplacian 8 tetangga) | Turunan pertama (gradien Gx dan Gy) |
| Sifat arah | Isotropik, tidak memilih arah | Memilih arah melalui Gx dan Gy |
| Bentuk keluaran | Kumpulan titik terpisah | Kurva tepi yang mengikuti batas objek |
| Objek yang ditonjolkan | Sudut, ujung garis, bintik, tekstur halus | Batas antara dua daerah dengan intensitas berbeda |
| Kelebihan | Baik untuk menandai lokasi perubahan tajam yang kecil | Menghasilkan kontur yang menyambung dan mudah ditelusuri |
| Kelemahan | Tidak menyambung, mudah dipicu tekstur dan derau | Tepi tebal, ambang global, tanpa penipisan dan penekanan non-maksimum |
| Hasil pada Burj Khalifa | Titik di siluet, tonjolan fasad, dan kaki menara | Siluet dan tonjolan terlihat, tekstur fasad sebagian hilang pada T=200 |
| Hasil pada Route 66 | Titik di tiang, vegetasi, dan tepi papan | Garis tepi jalan, marka tengah, tiang, dan papan tergambar menyambung |

## 5. Metode yang menghasilkan garis atau tepi paling jelas

Berdasarkan pengamatan visual, Prewitt menghasilkan tepi yang jauh lebih jelas
daripada deteksi titik. Deteksi titik hanya memberi lokasi perubahan intensitas,
sedangkan Prewitt memberi rangkaian piksel yang membentuk kontur. Kontur itu
dapat diikuti dari satu ujung ke ujung lain, terutama pada garis tepi jalan dan
papan Route 66.

Di antara kedua citra, Route 66 memberi hasil Prewitt paling bersih. Garis tepi
jalan dan marka tengah membentuk garis panjang yang menyambung, latar langit
relatif rata, dan permukaan aspal tidak terlalu banyak menghasilkan tepi kuat.
Pada Burj Khalifa, siluet menara juga tegas, tetapi fasadnya padat dan
resolusinya hanya 250 x 438 piksel. Pada ambang 200, tepi fasad terlihat
terputus-putus. Bila tekstur fasad ingin dipertahankan, ambang harus diturunkan
ke sekitar 100 sampai 150, dengan konsekuensi tepi lemah dan derau ikut muncul.

## 6. Keterbatasan

1. Bagian ini hanya membahas deteksi titik dan Prewitt. Deteksi garis serta
   operator Sobel, Roberts, dan kompas tidak termasuk.
2. Ambang titik ditetapkan dari persentil respons tiap citra, sehingga
   kepadatan titik kedua citra dibuat hampir sama. Perbandingan jumlah titik
   karena itu tidak menunjukkan perbedaan kerumitan citra.
3. Prewitt memakai satu ambang global. Tidak ada penipisan tepi, penekanan
   non-maksimum, atau ambang ganda seperti pada Canny.
4. Resolusi Burj Khalifa jauh lebih rendah daripada Route 66. Detail fasad yang
   hanya beberapa piksel tidak dapat dipertahankan oleh mask 3x3.
5. Konversi ke citra keabuan menghilangkan informasi warna. Pada citra ini
   kontras utama masih terbawa oleh kecerahan, tetapi dua warna berbeda yang
   kecerahannya sama akan melebur.
6. Konvolusi manual sudah diverifikasi terhadap `cv2.filter2D` dengan selisih
   maksimum 0,000000, sehingga hasil bukan disebabkan oleh perbedaan
   implementasi pustaka.

## 7. Kesimpulan

1. Deteksi titik dengan mask 8 tetangga berhasil menandai 552 titik pada Burj
   Khalifa dan 2148 titik pada Route 66 pada persentil 99,5. Titik yang muncul
   sebagian besar berada pada tekstur, sudut, dan ujung garis, bukan hanya pada
   titik terisolasi.
2. Prewitt berhasil mengekstrak tepi utama kedua citra. Ambang 200 memberi hasil
   paling mudah dibaca: kontur jalan, marka, tiang, papan Route 66, siluet
   menara, dan tonjolan fasad masih terlihat, sementara tekstur latar sebagian
   besar tertekan.
3. Prewitt menghasilkan tepi yang lebih jelas daripada deteksi titik karena
   keluarannya berupa kontur yang menyambung. Di antara kedua citra, Route 66
   memberi hasil tepi paling bersih, sedangkan Burj Khalifa terkendala tekstur
   fasad yang padat dan resolusi yang rendah.

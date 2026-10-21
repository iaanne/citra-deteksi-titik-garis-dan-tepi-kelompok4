"""Deteksi titik dan deteksi tepi Prewitt pada dua citra digital.

Bagian tugas yang diimplementasikan:
    1. Dua citra masukan, dikonversi ke citra keabuan (grayscale).
    2. Deteksi titik dengan mask 8 tetangga.
    3. Deteksi tepi dengan operator Prewitt.

Jalankan dari direktori repositori:
    python src/deteksi.py
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import cv2
import matplotlib
import numpy as np
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt

# ---------------------------------------------------------------------------
# Konfigurasi
# ---------------------------------------------------------------------------

AKAR = Path(__file__).resolve().parents[1]
DIR_CITRA = AKAR / "img"
DIR_KELUARAN = AKAR / "output"
DIR_GAMBAR = DIR_KELUARAN / "gambar"
DIR_PANEL = DIR_GAMBAR / "panel"
DIR_KOMPOSIT = DIR_GAMBAR / "komposit"
DIR_TABEL = DIR_KELUARAN / "tabel"

# Lebar proses. Citra yang lebih kecil dari nilai ini tidak diperbesar.
LEBAR_PROSES = 800

# Ambang deteksi titik dinyatakan sebagai persentil respons.
PERSENTIL_TITIK = 99.5
PERSENTIL_SAPUAN = [99.0, 99.5, 99.9, 99.99]

# Ambang tepi Prewitt dalam satuan magnitudo gradien (0 sampai sekitar 1442).
AMBANG_TEPI = 200
AMBANG_SAPUAN = [100, 150, 200, 250]

# Mask deteksi titik: Laplacian 8 tetangga.
MASK_TITIK = np.array(
    [
        [-1, -1, -1],
        [-1, 8, -1],
        [-1, -1, -1],
    ],
    dtype=np.float32,
)

# Mask Prewitt.
MASK_GX = np.array(
    [
        [-1, 0, 1],
        [-1, 0, 1],
        [-1, 0, 1],
    ],
    dtype=np.float32,
)

MASK_GY = np.array(
    [
        [-1, -1, -1],
        [0, 0, 0],
        [1, 1, 1],
    ],
    dtype=np.float32,
)

DAFTAR_CITRA = [
    {
        "kunci": "burj",
        "judul": "Burj Khalifa",
        "berkas": "Burj_Khalifa.avif",
        "lebar_proses": None,
    },
    {
        "kunci": "route66",
        "judul": "Jalan Route 66",
        "berkas": "D11_Williams_Route_66_1.avif",
        "lebar_proses": LEBAR_PROSES,
    },
]

# Gaya gambar.
plt.rcParams.update(
    {
        "font.family": "serif",
        "font.serif": ["Liberation Serif", "DejaVu Serif"],
        "font.size": 9,
        "axes.titlesize": 9,
        "figure.dpi": 110,
        "savefig.dpi": 200,
        "savefig.bbox": "tight",
        "savefig.pad_inches": 0.03,
        "image.interpolation": "nearest",
    }
)


# ---------------------------------------------------------------------------
# Pemuatan citra dan konvolusi
# ---------------------------------------------------------------------------


def muat_citra(berkas: Path, lebar_proses: int | None) -> tuple[np.ndarray, np.ndarray]:
    """Baca citra, perkecil bila perlu, lalu ubah ke citra keabuan.

    Pengurangan ukuran memakai interpolasi area agar tekstur halus tidak
    menimbulkan derau baru. Pengubahan ke keabuan memakai rumus luminansi
    standar OpenCV: 0,299 R + 0,587 G + 0,114 B.
    """
    warna = cv2.imread(str(berkas), cv2.IMREAD_COLOR)
    if warna is None:
        # Cadangan bila OpenCV tidak mendukung AVIF. Pillow versi baru
        # dapat membaca AVIF tanpa pustaka tambahan.
        from PIL import Image

        try:
            with Image.open(berkas) as gambar:
                warna = cv2.cvtColor(
                    np.array(gambar.convert("RGB")), cv2.COLOR_RGB2BGR
                )
        except Exception as galat:
            raise FileNotFoundError(
                f"Citra tidak dapat dibaca: {berkas}"
            ) from galat

    tinggi_asli, lebar_asli = warna.shape[:2]
    if lebar_proses is not None and lebar_asli > lebar_proses:
        skala = lebar_proses / lebar_asli
        ukuran = (lebar_proses, int(round(tinggi_asli * skala)))
        warna = cv2.resize(warna, ukuran, interpolation=cv2.INTER_AREA)

    keabuan = cv2.cvtColor(warna, cv2.COLOR_BGR2GRAY)
    return warna, keabuan


def konvolusi(keabuan: np.ndarray, mask: np.ndarray) -> np.ndarray:
    """Terapkan mask 3x3 dengan penjumlahan hasil kali di tiap posisi.

    Mask diterapkan seperti pada buku teks, yaitu tanpa pembalikan mask,
    sehingga hasilnya sama dengan cv2.filter2D. Batas citra diisi dengan
    nilai piksel tepi terdekat (edge padding) supaya tidak muncul tepi
    palsu di bingkai citra.
    """
    citra = keabuan.astype(np.float32)
    mask = np.asarray(mask, dtype=np.float32)
    if mask.shape != (3, 3):
        raise ValueError("Mask harus berukuran 3x3.")

    tepi = np.pad(citra, 1, mode="edge")
    jendela = np.lib.stride_tricks.sliding_window_view(tepi, (3, 3))
    return np.einsum("ijkl,kl->ij", jendela, mask)


def verifikasi_konvolusi(keabuan: np.ndarray) -> float:
    """Bandingkan konvolusi manual dengan cv2.filter2D untuk semua mask."""
    selisih = 0.0
    for mask in (MASK_TITIK, MASK_GX, MASK_GY):
        manual = konvolusi(keabuan, mask)
        acuan = cv2.filter2D(
            keabuan.astype(np.float32),
            cv2.CV_32F,
            mask,
            borderType=cv2.BORDER_REPLICATE,
        )
        selisih = max(selisih, float(np.max(np.abs(manual - acuan))))
    return selisih


# ---------------------------------------------------------------------------
# Deteksi titik dan tepi
# ---------------------------------------------------------------------------


def deteksi_titik(
    keabuan: np.ndarray, persentil: float = PERSENTIL_TITIK
) -> tuple[np.ndarray, float, np.ndarray]:
    """Hitung respons titik dan tandai titik yang melewati ambang.

    Respons R adalah nilai mutlak hasil konvolusi mask 8 tetangga. Titik
    dianggap ada bila R >= T, dengan T ditetapkan dari persentil respons.
    """
    respons = np.abs(konvolusi(keabuan, MASK_TITIK))
    ambang = float(np.percentile(respons, persentil))
    titik = respons >= ambang
    return respons, ambang, titik


def deteksi_prewitt(keabuan: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Hitung gradien Prewitt Gx, Gy, dan magnitudonya."""
    gx = konvolusi(keabuan, MASK_GX)
    gy = konvolusi(keabuan, MASK_GY)
    magnitudo = np.hypot(gx, gy)
    return gx, gy, magnitudo


def binerkan(peta: np.ndarray, ambang: float) -> np.ndarray:
    """Ubah peta respons menjadi citra biner 0/255."""
    return np.where(peta >= ambang, 255, 0).astype(np.uint8)


def overlay_titik(keabuan: np.ndarray, titik: np.ndarray) -> np.ndarray:
    """Tandai titik terdeteksi dengan warna merah pada citra keabuan.

    Penanda dipertebal 2x2 atau 3x3 piksel agar tetap terlihat setelah
    gambar diperkecil. Penebalan hanya untuk tampilan, jumlah titik yang
    dilaporkan tetap dihitung dari piksel asli.
    """
    rgb = cv2.cvtColor(keabuan, cv2.COLOR_GRAY2RGB)
    ukuran = 2 if keabuan.shape[1] <= 300 else 3
    penanda = cv2.dilate(titik.astype(np.uint8), np.ones((ukuran, ukuran), np.uint8))
    rgb[penanda > 0] = (210, 35, 35)
    return rgb


# ---------------------------------------------------------------------------
# Metrik
# ---------------------------------------------------------------------------


def waktu_ms(fungsi, ulang: int = 3) -> tuple[object, float]:
    """Jalankan fungsi beberapa kali dan ambil waktu tercepat dalam ms."""
    hasil = None
    catatan = []
    for _ in range(ulang):
        mulai = time.perf_counter()
        hasil = fungsi()
        catatan.append((time.perf_counter() - mulai) * 1000)
    return hasil, float(min(catatan))


def hitung_metrik(
    keabuan: np.ndarray,
    respons: np.ndarray,
    ambang_titik: float,
    titik: np.ndarray,
    gx: np.ndarray,
    gy: np.ndarray,
    magnitudo: np.ndarray,
    tepi: np.ndarray,
) -> dict[str, float | int]:
    """Kumpulkan angka pembanding untuk laporan."""
    varians_laplacian = float(cv2.Laplacian(keabuan, cv2.CV_64F).var())
    return {
        "rerata_intensitas": round(float(keabuan.mean()), 2),
        "simpangan_baku_intensitas": round(float(keabuan.std()), 2),
        "varians_laplacian": round(varians_laplacian, 1),
        "rerata_respons_titik": round(float(respons.mean()), 2),
        "maks_respons_titik": round(float(respons.max()), 1),
        "ambang_titik": round(ambang_titik, 1),
        "jumlah_titik": int(titik.sum()),
        "kepadatan_titik_persen": round(100 * float(titik.mean()), 3),
        "rerata_magnitudo": round(float(magnitudo.mean()), 2),
        "maks_magnitudo": round(float(magnitudo.max()), 1),
        "jumlah_tepi": int((tepi > 0).sum()),
        "kepadatan_tepi_persen": round(100 * float((tepi > 0).mean()), 3),
        "rasio_energi_gx_gy": round(
            float(np.abs(gx).mean() / max(np.abs(gy).mean(), 1e-6)), 3
        ),
    }


def sapuan_ambang_titik(respons: np.ndarray) -> list[dict]:
    """Hitung jumlah titik pada beberapa persentil ambang."""
    baris = []
    total = respons.size
    for persentil in PERSENTIL_SAPUAN:
        ambang = float(np.percentile(respons, persentil))
        jumlah = int((respons >= ambang).sum())
        baris.append(
            {
                "persentil": persentil,
                "ambang": round(ambang, 1),
                "jumlah_titik": jumlah,
                "kepadatan_persen": round(100 * jumlah / total, 3),
            }
        )
    return baris


def sapuan_ambang_prewitt(magnitudo: np.ndarray) -> list[dict]:
    """Hitung kepadatan tepi pada beberapa ambang absolut."""
    baris = []
    for ambang in AMBANG_SAPUAN:
        jumlah = int((magnitudo >= ambang).sum())
        baris.append(
            {
                "ambang": ambang,
                "jumlah_tepi": jumlah,
                "kepadatan_persen": round(100 * jumlah / magnitudo.size, 3),
            }
        )
    return baris


# ---------------------------------------------------------------------------
# Gambar
# ---------------------------------------------------------------------------


def normalkan(peta: np.ndarray, batas_atas: float) -> np.ndarray:
    """Ubah peta float ke 0-255 untuk disimpan sebagai gambar."""
    return np.clip(peta / max(batas_atas, 1e-6) * 255.0, 0, 255).astype(np.uint8)


def simpan_panel(array: np.ndarray, tujuan: Path) -> None:
    """Simpan satu panel tanpa judul pada resolusi asli."""
    tujuan.parent.mkdir(parents=True, exist_ok=True)
    if array.ndim == 3:
        cv2.imwrite(str(tujuan), cv2.cvtColor(array, cv2.COLOR_RGB2BGR))
    else:
        cv2.imwrite(str(tujuan), array)


def komposit(
    panel: list[dict], tujuan: Path, lebar: float = 7.2, nkolom: int | None = None
) -> None:
    """Susun beberapa panel menjadi satu gambar berjudul.

    Ukuran gambar dibuat mendekati lebar pemakaian di laporan supaya
    ukuran huruf pada judul panel tetap wajar setelah diperkecil.
    Citra potret disusun satu baris, citra lanskap disusun dua baris
    agar tiap panel tidak terlalu kecil.
    """
    jumlah = len(panel)
    nkolom = nkolom or jumlah
    nbaris = int(np.ceil(jumlah / nkolom))
    tinggi_array, lebar_array = panel[0]["array"].shape[:2]
    lebar_panel = lebar / nkolom
    tinggi_panel = lebar_panel * tinggi_array / lebar_array

    gambar, sumbu = plt.subplots(
        nbaris,
        nkolom,
        figsize=(lebar, nbaris * (tinggi_panel + 0.32)),
        constrained_layout=True,
        squeeze=False,
    )
    sumbu = sumbu.ravel()
    for indeks, (aks, isi) in enumerate(zip(sumbu, panel)):
        aks.imshow(
            isi["array"],
            cmap=isi.get("cmap", "gray"),
            vmin=isi.get("vmin"),
            vmax=isi.get("vmax"),
            interpolation="nearest",
        )
        aks.set_axis_off()
        aks.set_title(
            f"({chr(97 + indeks)}) {isi['judul']}",
            pad=2,
            fontsize=8.5 if nkolom >= 5 else 9,
        )
    for aks in sumbu[jumlah:]:
        aks.set_axis_off()

    tujuan.parent.mkdir(parents=True, exist_ok=True)
    gambar.savefig(tujuan)
    plt.close(gambar)


def buat_gambar(hasil: dict, konteks: dict) -> None:
    """Buat seluruh gambar hasil untuk satu citra."""
    kunci = hasil["kunci"]
    keabuan = konteks["keabuan"]
    respons = konteks["respons"]
    titik = konteks["titik"]
    gx = konteks["gx"]
    gy = konteks["gy"]
    magnitudo = konteks["magnitudo"]

    batas_respons = float(np.percentile(respons, 99.9))
    batas_gradien = float(
        max(np.percentile(np.abs(gx), 99.9), np.percentile(np.abs(gy), 99.9))
    )
    batas_magnitudo = float(np.percentile(magnitudo, 99.9))

    gambar_titik = overlay_titik(keabuan, titik)
    tepi = konteks["tepi"]

    # Panel tunggal tanpa judul, berguna untuk tata letak laporan.
    cv2.imwrite(str(DIR_PANEL / f"{kunci}_00_asli.png"), konteks["warna"])
    simpan_panel(keabuan, DIR_PANEL / f"{kunci}_01_keabuan.png")
    simpan_panel(
        normalkan(respons, batas_respons), DIR_PANEL / f"{kunci}_02_respons_titik.png"
    )
    simpan_panel(
        np.where(titik, 255, 0).astype(np.uint8), DIR_PANEL / f"{kunci}_03_titik_biner.png"
    )
    simpan_panel(gambar_titik, DIR_PANEL / f"{kunci}_04_titik_overlay.png")
    simpan_panel(normalkan(np.abs(gx), batas_gradien), DIR_PANEL / f"{kunci}_05_gx.png")
    simpan_panel(normalkan(np.abs(gy), batas_gradien), DIR_PANEL / f"{kunci}_06_gy.png")
    simpan_panel(
        normalkan(magnitudo, batas_magnitudo), DIR_PANEL / f"{kunci}_07_magnitudo.png"
    )
    simpan_panel(tepi, DIR_PANEL / f"{kunci}_08_tepi_biner.png")

    potret = keabuan.shape[0] > keabuan.shape[1]

    # Komposit deteksi titik.
    komposit(
        [
            {"array": keabuan, "judul": "Citra keabuan"},
            {
                "array": respons,
                "judul": "Respons titik |R|",
                "vmin": 0,
                "vmax": batas_respons,
            },
            {
                "array": np.where(titik, 255, 0).astype(np.uint8),
                "judul": f"Titik biner (T={hasil['metrik']['ambang_titik']:.0f})",
                "vmin": 0,
                "vmax": 255,
            },
            {"array": gambar_titik, "judul": "Titik pada citra"},
        ],
        DIR_KOMPOSIT / f"{kunci}_titik.png",
        nkolom=4 if potret else 2,
    )

    # Komposit Prewitt.
    komposit(
        [
            {"array": keabuan, "judul": "Citra keabuan"},
            {
                "array": np.abs(gx),
                "judul": "|Gx| (tepi vertikal)",
                "vmin": 0,
                "vmax": batas_gradien,
            },
            {
                "array": np.abs(gy),
                "judul": "|Gy| (tepi horizontal)",
                "vmin": 0,
                "vmax": batas_gradien,
            },
            {
                "array": magnitudo,
                "judul": "Magnitudo |G|",
                "vmin": 0,
                "vmax": batas_magnitudo,
            },
            {
                "array": tepi,
                "judul": f"Tepi biner (T={AMBANG_TEPI})",
                "vmin": 0,
                "vmax": 255,
            },
        ],
        DIR_KOMPOSIT / f"{kunci}_prewitt.png",
        nkolom=5 if potret else 3,
    )


def buat_gambar_perbandingan(
    hasil_semua: list[dict], konteks_semua: list[dict]
) -> None:
    """Buat satu gambar ringkas untuk membandingkan kedua citra."""
    lebar = 7.2
    nkolom = 3
    lebar_panel = lebar / nkolom
    tinggi_baris = [
        lebar_panel * konteks["keabuan"].shape[0] / konteks["keabuan"].shape[1]
        for konteks in konteks_semua
    ]

    gambar, sumbu = plt.subplots(
        len(hasil_semua),
        nkolom,
        figsize=(lebar, sum(tinggi_baris) + 0.8),
        gridspec_kw={"height_ratios": tinggi_baris},
        constrained_layout=True,
        squeeze=False,
    )

    judul_kolom = ["Citra keabuan", "Deteksi titik", f"Tepi Prewitt (T={AMBANG_TEPI})"]
    for baris, (hasil, konteks) in enumerate(zip(hasil_semua, konteks_semua)):
        tampilan = [
            konteks["keabuan"],
            overlay_titik(konteks["keabuan"], konteks["titik"]),
            np.where(konteks["magnitudo"] >= AMBANG_TEPI, 255, 0).astype(np.uint8),
        ]
        for kolom, isi in enumerate(tampilan):
            aks = sumbu[baris, kolom]
            aks.imshow(
                isi,
                cmap="gray",
                vmin=0,
                vmax=255,
                interpolation="nearest",
            )
            aks.set_axis_off()
            if baris == 0:
                aks.set_title(judul_kolom[kolom], pad=3)
        sumbu[baris, 0].text(
            -0.05,
            0.5,
            hasil["judul"],
            transform=sumbu[baris, 0].transAxes,
            rotation=90,
            va="center",
            ha="right",
        )

    gambar.savefig(DIR_KOMPOSIT / "perbandingan_metode.png")
    plt.close(gambar)


def buat_gambar_sapuan(
    hasil_semua: list[dict], konteks_semua: list[dict]
) -> None:
    """Buat gambar perbandingan ambang untuk kedua citra."""
    # Sapuan ambang titik: 2 baris (citra) x 4 kolom (persentil).
    gambar, sumbu = plt.subplots(
        len(hasil_semua),
        len(PERSENTIL_SAPUAN),
        figsize=(7.2, 4.4),
        constrained_layout=True,
    )
    for baris, (hasil, konteks) in enumerate(zip(hasil_semua, konteks_semua)):
        respons = konteks["respons"]
        for kolom, persentil in enumerate(PERSENTIL_SAPUAN):
            ambang = float(np.percentile(respons, persentil))
            biner = np.where(respons >= ambang, 255, 0).astype(np.uint8)
            aks = sumbu[baris, kolom]
            aks.imshow(biner, cmap="gray", vmin=0, vmax=255, interpolation="nearest")
            aks.set_axis_off()
            jumlah = int((respons >= ambang).sum())
            aks.set_title(
                f"p{str(persentil).replace('.', ',')}  T={ambang:.0f}\n{jumlah} titik",
                fontsize=8,
                pad=2,
            )
        sumbu[baris, 0].text(
            -0.08,
            0.5,
            hasil["judul"],
            transform=sumbu[baris, 0].transAxes,
            rotation=90,
            va="center",
            ha="right",
            fontsize=8,
        )
    gambar.savefig(DIR_KOMPOSIT / "sapuan_ambang_titik.png")
    plt.close(gambar)

    # Sapuan ambang Prewitt: 2 baris (citra) x 4 kolom (ambang).
    gambar, sumbu = plt.subplots(
        len(hasil_semua),
        len(AMBANG_SAPUAN),
        figsize=(7.2, 4.4),
        constrained_layout=True,
    )
    for baris, (hasil, konteks) in enumerate(zip(hasil_semua, konteks_semua)):
        magnitudo = konteks["magnitudo"]
        for kolom, ambang in enumerate(AMBANG_SAPUAN):
            biner = np.where(magnitudo >= ambang, 255, 0).astype(np.uint8)
            aks = sumbu[baris, kolom]
            aks.imshow(biner, cmap="gray", vmin=0, vmax=255, interpolation="nearest")
            aks.set_axis_off()
            kepadatan = 100 * float((magnitudo >= ambang).mean())
            aks.set_title(
                f"T={ambang}\n{kepadatan:.2f}% piksel",
                fontsize=8,
                pad=2,
            )
        sumbu[baris, 0].text(
            -0.08,
            0.5,
            hasil["judul"],
            transform=sumbu[baris, 0].transAxes,
            rotation=90,
            va="center",
            ha="right",
            fontsize=8,
        )
    gambar.savefig(DIR_KOMPOSIT / "sapuan_ambang_prewitt.png")
    plt.close(gambar)


# ---------------------------------------------------------------------------
# Keluaran tabel
# ---------------------------------------------------------------------------


def sel_markdown(nilai: object) -> str:
    """Escape tanda pipa agar tabel Markdown tidak pecah."""
    return str(nilai).replace("|", "\\|")


def tabel_markdown(tabel: pd.DataFrame) -> str:
    """Ubah DataFrame menjadi tabel Markdown sederhana."""
    kepala = "| " + " | ".join(sel_markdown(kolom) for kolom in tabel.columns) + " |"
    garis = "|" + "|".join("---" for _ in tabel.columns) + "|"
    isi = [
        "| " + " | ".join(sel_markdown(nilai) for nilai in baris) + " |"
        for baris in tabel.itertuples(index=False)
    ]
    return "\n".join([kepala, garis, *isi])


def tulis_tabel(hasil_semua: list[dict]) -> None:
    """Tulis tabel metrik dan sapuan ambang ke CSV dan Markdown."""
    DIR_TABEL.mkdir(parents=True, exist_ok=True)

    nama_metrik = {
        "rerata_intensitas": "Rerata intensitas",
        "simpangan_baku_intensitas": "Simpangan baku intensitas",
        "varians_laplacian": "Varians Laplacian",
        "rerata_respons_titik": "Rerata respons titik |R|",
        "maks_respons_titik": "Maksimum respons titik |R|",
        "ambang_titik": f"Ambang titik (persentil {PERSENTIL_TITIK:g})",
        "jumlah_titik": "Jumlah titik",
        "kepadatan_titik_persen": "Kepadatan titik (%)",
        "rerata_magnitudo": "Rerata magnitudo |G|",
        "maks_magnitudo": "Maksimum magnitudo |G|",
        "jumlah_tepi": "Jumlah piksel tepi",
        "kepadatan_tepi_persen": "Kepadatan tepi (%)",
        "rasio_energi_gx_gy": "Rasio energi |Gx| : |Gy|",
    }

    def format_angka(kunci: str, nilai: float) -> str:
        if kunci in {"jumlah_titik", "jumlah_tepi"}:
            return f"{int(nilai)}"
        if kunci.endswith("_persen"):
            return f"{nilai:.3f}"
        if kunci in {
            "varians_laplacian",
            "ambang_titik",
            "maks_respons_titik",
            "maks_magnitudo",
        }:
            return f"{nilai:.1f}"
        return f"{nilai:.2f}"

    kolom = ["Metrik"] + [hasil["judul"] for hasil in hasil_semua]
    baris = []
    for kunci, label in nama_metrik.items():
        baris.append(
            [label]
            + [format_angka(kunci, hasil["metrik"][kunci]) for hasil in hasil_semua]
        )
    tabel_metrik = pd.DataFrame(baris, columns=kolom)
    tabel_metrik.to_csv(DIR_TABEL / "metrik.csv", index=False)

    baris_titik = []
    for hasil in hasil_semua:
        for isi in hasil["sapuan_titik"]:
            baris_titik.append({"Citra": hasil["judul"], **isi})
    pd.DataFrame(baris_titik).to_csv(DIR_TABEL / "ambang_titik.csv", index=False)

    baris_tepi = []
    for hasil in hasil_semua:
        for isi in hasil["sapuan_prewitt"]:
            baris_tepi.append({"Citra": hasil["judul"], **isi})
    pd.DataFrame(baris_tepi).to_csv(DIR_TABEL / "ambang_prewitt.csv", index=False)

    # Ringkasan Markdown untuk memudahkan penulisan laporan.
    with (DIR_KELUARAN / "ringkasan.md").open("w", encoding="utf-8") as berkas:
        berkas.write("# Ringkasan Angka\n\n")
        berkas.write("## Metrik utama\n\n")
        berkas.write(tabel_markdown(tabel_metrik))
        berkas.write("\n\n## Sapuan ambang deteksi titik\n\n")
        berkas.write(tabel_markdown(pd.DataFrame(baris_titik)))
        berkas.write("\n\n## Sapuan ambang Prewitt\n\n")
        berkas.write(tabel_markdown(pd.DataFrame(baris_tepi)))
        berkas.write("\n")


# ---------------------------------------------------------------------------
# Program utama
# ---------------------------------------------------------------------------


def main() -> None:
    for direktori in (DIR_GAMBAR, DIR_PANEL, DIR_KOMPOSIT, DIR_TABEL):
        direktori.mkdir(parents=True, exist_ok=True)

    hasil_semua: list[dict] = []
    konteks_semua: list[dict] = []

    for item in DAFTAR_CITRA:
        berkas = DIR_CITRA / item["berkas"]
        warna, keabuan = muat_citra(berkas, item["lebar_proses"])
        tinggi, lebar = keabuan.shape

        selisih = verifikasi_konvolusi(keabuan)
        if selisih > 1e-3:
            raise RuntimeError(
                f"Konvolusi manual berbeda dari cv2.filter2D sebesar {selisih:.4f}."
            )

        (respons, ambang_titik, titik), waktu_titik = waktu_ms(
            lambda: deteksi_titik(keabuan, PERSENTIL_TITIK)
        )
        (gx, gy, magnitudo), waktu_prewitt = waktu_ms(
            lambda: deteksi_prewitt(keabuan)
        )

        tepi = binerkan(magnitudo, AMBANG_TEPI)
        metrik = hitung_metrik(
            keabuan, respons, ambang_titik, titik, gx, gy, magnitudo, tepi
        )
        metrik["waktu_titik_ms"] = round(waktu_titik, 2)
        metrik["waktu_prewitt_ms"] = round(waktu_prewitt, 2)

        hasil = {
            "kunci": item["kunci"],
            "judul": item["judul"],
            "berkas": str(berkas.relative_to(AKAR)),
            "ukuran_asli": [warna.shape[1], warna.shape[0]],
            "ukuran_proses": [lebar, tinggi],
            "selisih_konvolusi": selisih,
            "metrik": metrik,
            "sapuan_titik": sapuan_ambang_titik(respons),
            "sapuan_prewitt": sapuan_ambang_prewitt(magnitudo),
        }

        konteks = {
            "warna": warna,
            "keabuan": keabuan,
            "respons": respons,
            "titik": titik,
            "gx": gx,
            "gy": gy,
            "magnitudo": magnitudo,
            "tepi": tepi,
        }

        buat_gambar(hasil, konteks)
        hasil_semua.append(hasil)
        konteks_semua.append(konteks)

        print(f"\n=== {item['judul']} ===")
        print(f"Ukuran asli   : {warna.shape[1]} x {warna.shape[0]}")
        print(f"Ukuran proses : {lebar} x {tinggi}")
        print(f"Selisih konvolusi manual vs OpenCV: {selisih:.6f}")
        print(
            f"Deteksi titik : T={ambang_titik:.1f}, "
            f"{metrik['jumlah_titik']} titik "
            f"({metrik['kepadatan_titik_persen']:.2f}%), "
            f"{waktu_titik:.1f} ms"
        )
        print(
            f"Prewitt       : rerata |G|={metrik['rerata_magnitudo']:.2f}, "
            f"maks |G|={metrik['maks_magnitudo']:.1f}, "
            f"tepi T={AMBANG_TEPI} sebanyak {metrik['jumlah_tepi']} piksel "
            f"({metrik['kepadatan_tepi_persen']:.2f}%), "
            f"{waktu_prewitt:.1f} ms"
        )
        print(
            f"Rasio energi |Gx|:|Gy| = {metrik['rasio_energi_gx_gy']:.2f}"
        )

    buat_gambar_perbandingan(hasil_semua, konteks_semua)
    buat_gambar_sapuan(hasil_semua, konteks_semua)

    keluaran = {
        "parameter": {
            "lebar_proses": LEBAR_PROSES,
            "persentil_titik": PERSENTIL_TITIK,
            "ambang_tepi": AMBANG_TEPI,
            "persentil_sapuan": PERSENTIL_SAPUAN,
            "ambang_sapuan": AMBANG_SAPUAN,
        },
        "citra": hasil_semua,
    }
    with (DIR_KELUARAN / "data.json").open("w", encoding="utf-8") as berkas:
        json.dump(keluaran, berkas, indent=2, ensure_ascii=False)

    tulis_tabel(hasil_semua)

    print("\nSelesai.")
    print(f"Gambar  : {DIR_GAMBAR}")
    print(f"Tabel   : {DIR_TABEL}")
    print(f"Ringkasan: {DIR_KELUARAN / 'ringkasan.md'}")


if __name__ == "__main__":
    main()

# Qualitative Interview Synthesis — May 2026
**Date:** 2026-05-13
**Interviewees:** 4 (teman kuliah, ibu, kakak, self)
**Method:** Semi-structured interview, 15-30 menit per sesi

## Profiles
| # | Profil | Frekuensi | Payment | Kategori |
|---|---|---|---|---|
| 1 | Kakak, 20an | ~<10x/bulan | Kurir reguler | Fashion |
| 2 | Ibu, 40an | ~<10x/bulan | COD | Promo/deals |
| 3 | Teman kuliah | 1-5x/bulan | Kurir reguler | Fashion |
| 4 | Self | <5x/bulan | Kurir instant | Elektronik |

## Confirmed Findings (terkonfirmasi pipeline)
| Pain Point | Pipeline Score | Konfirmasi Interview |
|---|---|---|
| Delivery & Logistics #1 | 675.9 | ✅ Kuat — instant delivery chaos (self), COD fraud (ibu) |
| Checkout & Payment #3 | 243.7 | ✅ Voucher hilang setelah cancel (teman + self) |
| Return & Refund naik | 194.4 | ✅ Proses ribet → abandon return tanpa resolve (kakak) |

## New Findings (tidak ada di pipeline)

### 1. COD Fraud via Resi Bekas — KRITIS
Ibu menerima paket COD yang tidak dipesan. Dugaan: oknum menggunakan resi lama dari paket sebelumnya untuk mengirim barang tak dikenal ke alamat yang sama. Ini bukan "COD diblokir" seperti di data — ini exploitation of COD system untuk fraud. Dua sisi masalah berbeda dari satu payment method.

### 2. Auto-join Live Shopping — Intrusive Feature
Teman: "Setiap masuk Shopee otomatis join live dan itu menyebalkan kalau lagi ga di silent hp, kadang bikin kaget kalau lagi di ruang sepi." Pipeline mencatat app performance secara general — interview mengidentifikasi: ini deliberate feature yang dirasakan sebagai dark pattern, bukan bug.

### 3. Instant Delivery Ecosystem Failure — Structural Issue
Self: pencarian kurir dibatasi per hari, bisa berhari-hari tidak ada kurir yang mau ambil. Penjual sudah kemas dan menunggu, kurir batal berkali-kali. CS tidak bisa bantu karena "masalah eksternal." Voucher garansi 2-4 jam bukan solusi — hanya band-aid. Pipeline menangkap "delivery bermasalah" tapi tidak sampai ke level structural failure ini.

### 4. Kurir Tidak Foto Lokasi untuk Paket Kecil
Teman: "Kurirnya ga foto dengan jelas ditaro mana paketnya, nyari se-halaman rumah karena gatau ditaro mana." Actionable fix: enforce foto lokasi untuk semua paket ukuran apapun.

## Behavioral Pattern
Semua 4 interviewee adalah **passive complainers** — frustrasi ada tapi low effort to resolve. Cenderung abandon atau switch daripada lapor CS. Switch ke Tokopedia/TikTok Shop bukan karena Shopee lebih buruk — primarily karena **harga lebih murah** dan **ketersediaan barang**.

Implikasi: complaint yang masuk ke CS adalah severe undercounting dari masalah sebenarnya. Untuk 1 orang yang lapor, ada 3-4 yang diam dan pergi.

## Key Quotes
> *"Ada oknum yang mengambil resi bekas paket lama lalu alamat dan nama kami menjadi bahan phishing"* — Ibu, COD fraud

> *"Dc nyaudh ilangg dan w sebelll bgttttt"* — Teman, voucher hilang setelah cancel

> *"Sampai berhari-hari tidak ada kurir yang mau ambil, ini sangat-sangat mengecewakan"* — Self, instant delivery failure

> *"Proses retur terlihat ribet akhirnya diputuskan untuk tidak ditindaklanjuti"* — Kakak, return abandonment

## Synthesis Table
| Pain Point | Berapa orang menyebut | Terkonfirmasi pipeline? | Quote terkuat |
|---|---|---|---|
| Delivery lambat/gagal | 2/4 | Ya (#1, score 675.9) | "Berhari-hari tidak ada kurir yang mau ambil" |
| Produk tidak sesuai deskripsi | 2/4 | Partial (seller_experience #4) | "Barangnya kurang bagus tidak seperti yang digambar" |
| Voucher/promo hilang | 2/4 | Ya (#3, checkout) | "Dc nyaudh ilangg dan w sebelll bgttttt" |
| COD fraud via resi bekas | 1/4 | Tidak — NEW FINDING | "Alamat dan nama kami menjadi bahan phishing" |
| Auto-join live shopping | 1/4 | Partial (app_performance) | "Setiap masuk Shopee auto join live, menyebalkan" |
| Return process ribet | 1/4 | Ya (return_refund naik 104%) | "Ribet akhirnya tidak ditindaklanjuti" |
| Kurir tidak foto lokasi | 1/4 | Tidak — NEW FINDING | "Nyari se-halaman rumah karena gatau ditaro mana" |

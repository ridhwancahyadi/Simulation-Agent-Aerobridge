# Rationale Pemilihan Pesawat: Cessna 208b vs EC725 Caracal

Dokumen ini menjelaskan alasan teknis dibalik hasil simulasi misi **LOG-PAPUA-001** (Scenario: Emergency).

## 1. Perbandingan Performa Utama

| Metrik                 | Cessna 208b   | EC725 Caracal | Keterangan                                       |
| :--------------------- | :------------ | :------------ | :----------------------------------------------- |
| **Combined Score**     | **0.6122**    | 0.6072        | Cessna unggul tipis secara agregat.              |
| **Fuel Used**          | **308.53 kg** | 729.02 kg     | Cessna jauh lebih efisien (+136% lebih irit).    |
| **Mission Time**       | 107 Menit     | **70 Menit**  | Caracal lebih cepat (Sesuai karakter emergency). |
| **Min. Safety Margin** | 2.98%         | **10.80%**    | Caracal memiliki buffer daya/tenaga lebih besar. |

## 2. Mengapa Cessna 208b Menang Skor?

Meskipun **Emergency Scenario** mengutamakan Kecepatan (40%) dan Safety (35%), skor Cessna tetap lebih tinggi karena:

1.  **Fuel Efficiency Penalty**: Caracal mengonsumsi bahan bakar 2x lipat lebih banyak. Dalam mesin skoring, efisiensi bahan bakar yang buruk memberikan penalti yang signifikan pada bobot efisiensi.
2.  **Feasibility Check**: Sejak diaktifkannya **Universal Refueling**, Cessna menjadi "Legal" (Status: PASS) di semua rute kritis dengan menempatkan bandara sulit di urutan terakhir misi (saat beban ringan).
3.  **Balanced Trade-off**: Sistem menganggap keunggulan efisiensi Cessna yang ekstrem kompensasi yang cukup untuk sedikit ketertinggalan di sisi kecepatan dan safety, asalkan masih di atas ambang batas (PASS).

## 3. Standar Margin Berdasarkan PDF (Update Research 14)

Berdasarkan pedoman pada **Halaman 3 & 4** dokumen PDF, margin yang dibutuhkan bergantung pada objektifnya:

### Fixed Wing (Cessna) Thresholds:

- **Safety Objective**: Meminta Runway Margin **>= 25%**.
- **Delivery Objective**: Meminta Runway Margin **>= 2%**.
- **Hasil Saat Ini**: **2.98%**.
  > **Kesimpulan**: Cessna saat ini beroperasi pada level **"Delivery/Minimum Legal"**, bukan pada level "Safety-First" (25%) yang ideal.

### Rotary Wing (Caracal) Thresholds:

- **Safety Objective**: Meminta Power/OGE Margin **>= 25%**.
- **Delivery Objective**: Meminta Power/OGE Margin **>= 5%**.
- **Hasil Saat Ini**: **10.80%**.
  > **Kesimpulan**: Caracal berada pada level menengah (**Moderate**), jauh lebih aman dari Cessna namun tetap belum mencapai standar "Safety" ideal 25%.

## 4. Rekomendasi

Jika Anda membutuhkan misi yang **"Super Safe"** (sesuai standar 25% di PDF), maka kedua pesawat ini harus:

1.  **Cessna**: Mengurangi payload (beban) sekitar 20-30%.
2.  **Caracal**: Mengurangi payload agar OGE Buffer naik dari 10% ke 25%.

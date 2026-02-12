# Simulation Results Summary

## 1. Executive Summary

Simulasi telah dijalankan untuk misi **LOG-PAPUA-001** dengan rute multi-stop (Timika -> Ilaga -> Sinak -> Wamena).
Hasil menunjukkan bahwa **TIDAK ADA** pesawat yang mampu menyelesaikan misi sepenuhnya dengan parameter saat ini.

- **Cessna 208b**: Gagal pada _Hard Gate_ (Runway & Takeoff) di bandara ketinggian tinggi (Sinak & Ilaga).
- **EC725 Caracal**: Lolos _Hard Gate_, namun gagal pada _Fuel Sufficiency_ (tidak cukup bahan bakar untuk menyelesaikan rute dan kembali ke base).

---

## 2. Hard Gate Feasibility Check

Evaluasi kelayakan fisik pendaratan dan lepas landas.

| Aircraft          | Location | Status   | Reason                                                                                                  |
| :---------------- | :------- | :------- | :------------------------------------------------------------------------------------------------------ |
| **Cessna 208b**   | Wamena   | **PASS** | -                                                                                                       |
| **Cessna 208b**   | Sinak    | **FAIL** | Runway margin (-0.03m) & Landing margin (-200m). Runway terlalu pendek untuk _Density Altitude_ 9800ft. |
| **Cessna 208b**   | Ilaga    | **FAIL** | Runway margin (-195m). _Density Altitude_ 11,200ft memerlukan landasan >1400m (Tersedia 1205m).         |
| **EC725 Caracal** | All      | **PASS** | Kemampuan _vertical takeoff_ (OGE) memadai di semua lokasi.                                             |

> **Insight:** Cessna 208b tidak aman untuk beroperasi di Sinak dan Ilaga dengan muatan penuh pada kondisi cuaca/altitude saat ini.

---

## 3. Dynamic Mission Simulation (Leg-by-Leg)

Simulasi misi dengan rute spesifik (Timika → Ilaga → Sinak → Wamena → Sinak [?] → Kembali).

### Cessna 208b

- **Status Akhir:** `FAIL_RETURN_BASE`
- **Detail:**
  - Leg 1 (Timika -> Ilaga): **FAIL** (Hard Gate di Ilaga).
  - Fuel Remaining: 279 kg (Tidak cukup untuk RTB aman).

### EC725 Caracal

- **Status Akhir:** `FAIL_RETURN_BASE`
- **Detail:**
  - Leg 1, 2, 3: **PASS** (Operasional aman).
  - Leg Terakhir (Divert to Mulia/RTB): **FAIL**.
  - **Isu:** Konsumsi bahan bakar helikopter sangat tinggi (Total burn: 456 kg). Sisa fuel tidak cukup untuk kembali ke Timika dari titik terakhir.

---

## 4. Route Planning Analysis

Mesin pencari rute mencoba berbagai permutasi urutan destinasi untuk menemukan solusi.

- **Cessna 208b**: Semua kombinasi rute menghasilkan skor `0` karena kegagalan _Hard Gate_ di Ilaga/Sinak.
- **EC725 Caracal**: Semua kombinasi rute gagal karena `FAIL_FUEL` atau `FAIL_HARD_GATE`. Jarak total dan payload terlalu besar untuk kapasitas bahan bakar helikopter tanpa _refueling_.

---

## 5. Objective & Safety Scores

Skoring berdasarkan 5 parameter objektif (untuk misi yang berjalan sebagian):

| Aircraft          | Final Score | Delivery Score | Safety Score | Note                                                                              |
| :---------------- | :---------- | :------------- | :----------- | :-------------------------------------------------------------------------------- |
| **Cessna 208b**   | 0.69        | 0.83           | 0.00         | Safety 0 karena margin runway negatif (Bahaya Tinggi).                            |
| **EC725 Caracal** | 0.64        | 0.75           | 0.04         | Safety rendah tapi positif. Penalti utama pada konsumsi bahan bakar (Efficiency). |

---

## 6. Recommendations

1.  **Pengurangan Payload**: Kurangi muatan Cessna 208b agar _Takeoff/Landing distance_ berkurang dan masuk toleransi runway Ilaga/Sinak.
2.  **Refueling Strategy**: EC725 memerlukan titik _refueling_ di Wamena atau bandara perantara lain untuk menyelesaikan misi panjang ini.
3.  **Split Mission**: Pecah misi menjadi dua sorty penerbangan atau gunakan kombinasi armada (Cessna untuk Wamena, Caracal untuk Ilaga/Sinak dengan payload terbatas).

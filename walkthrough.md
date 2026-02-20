# Walkthrough: Unifikasi Skenario & Thresholds

Implementasi ini menyelesaikan tumpang tindih antara "Objective Mode" (Threshold) dan "Scenario ID" (Weights), menciptakan sistem pengambilan keputusan yang koheren.

## 1. Perubahan Arsitektur

Dibuat file central `scenario_config.py` yang mengatur dua aspek pendukung keputusan secara bersamaan:

- **Thresholds**: Batas minimal margin agar status misi **PASS**.
- **Weights**: Nilai kepentingan tiap kriteria untuk **Ranking**.

## 2. Perubahan Logika Safety

Sebelumnya, Cessna 208b sering terpilih meskipun marginnya tipis (2.98%) karena sistem hanya mengecek kelaikan fisik dasar.

**Hasil Sekarang (Scenario: Emergency):**

- **Cessna 208b**: Status **FAIL_POLICY_THRESHOLD**. Karena skenario Emergency sekarang mewajibkan margin minimal **10%** (sebelumnya di PDF 2%), Cessna yang hanya punya 2.98% otomatis didiskualifikasi.
- **EC725 Caracal**: Status **PASS**. Caracal memiliki margin **10.8%**, sehingga lolos filter 10% dan menjadi kandidat utama.

## 3. Hasil Simulasi Final

Rangkuman dari `simulation_mission_planning_output.json`:

| Skenario                | Pesawat Terpilih  | Alasan                                                                                 |
| :---------------------- | :---------------- | :------------------------------------------------------------------------------------- |
| **Emergency**           | **EC725 Caracal** | Lebih cepat (70 menit vs 107 menit) dan memenuhi threshold safety 10%.                 |
| **Logistic** (Teoretis) | Cessna 208b       | Akan kembali menang karena threshold Logistic hanya 2%, dan Cessna jauh lebih efisien. |

## 4. Validasi Output

Sistem sekarang secara otomatis melakukan optimasi global. Jika sebelumnya sistem memilih pesawat pertama dari lis, sekarang sistem memindai seluruh rute valid dari setiap pesawat dan memilih yang memiliki **Combined Score** tertinggi secara absolut.

```json
"aircraft_allocation": [
  {
    "strategy": "Single Fleet",
    "aircraft": "EC725 Caracal",
    "reason": "EC725 Caracal terpilih karena memberikan skor optimal (0.3844) dan mampu membawa seluruh payload."
  }
]
```

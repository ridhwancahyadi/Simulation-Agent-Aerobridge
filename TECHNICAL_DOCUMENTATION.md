# Dokumentasi Teknis Aerobridge Simulation Suite (V2 - Unified Architecture)

Dokumen ini menjelaskan detail teknis dari seluruh modul simulasi (.py) yang digunakan dalam ekosistem Aerobridge, termasuk arsitektur terbaru yang memisahkan antara Kebijakan Keselamatan (Policy) dan Preferensi Strategis (Weights).

---

## 1. Arsitektur Aliran Data (Data Flow)

Sistem beroperasi melalui tahapan berikut dengan filter bertingkat:

1.  **Hard Feasibility Gate**: Cek kelaikan fisik dasar (Runway vs Pesawat).
2.  **Dynamic Simulation**: Perhitungan konsumsi BBM dan waktu dengan asumsi _Universal Refueling_.
3.  **Safety Margin Analysis**: Perhitungan jarak aman operasional (Runway margin, OGE buffer).
4.  **Policy Filtering (NEW)**: Filter biner berdasarkan level keselamatan (Standard, Strict, Aggressive). Jika margin di bawah standar policy, misi status = **FAIL_POLICY_THRESHOLD**.
5.  **Strategic Ranking (NEW)**: Perankingan sisa kandidat yang lolos filter menggunakan bobot prioritas pengguna.
6.  **Reporting**: Generasi laporan taktis (Pilot Heads-up, Mitigasi).

---

## 2. Inti Keputusan (Core Decision Logic)

### A. scenario_config.py (The Brain)

Modul ini adalah pusat kendali aturan simulasi.

- **SAFETY_POLICIES**: Kamus berisi standar margin operasional yang deskriptif (Standard, Strict, Aggressive).
- **SCENARIO_CONFIG**: Memasangkan Skenario (Emergency, Logistic, dll) dengan kebijakan safety dan parameter skoring defaultnya.
- **get_scenario_config()**: Fungsi krusial yang mengambil konfigurasi secara dinamis. Jika pengguna memberikan kustomisasi di input, fungsi ini akan melakukan _merging_ antara "Custom Weights" dan "Standard Policy".

---

## 3. Detail Modul (Script Analysis)

### A. hard_feasibility_checks.py

- **Tujuan**: Memastikan misi aman secara fisik (Engineering level). Menggunakan rumus Density Altitude untuk menghitung performa takeoff/landing.

### B. dynamic_mission_gate.py

- **Tujuan**: Simulasi realistis leg-by-leg.
- **Fitur Utama**: Mengimplementasikan _Universal Refueling_ (mengisi BBM di setiap titik) dan _Tactical Layer_ (menilai risiko keamanan di lokasi hotspot).

### C. mission_planning_engine.py

- **Tujuan**: Brain untuk optimasi rute dan armada.
- **Logika Perbaikan Baru**:
  - Melakukan permutasi rute untuk mencari urutan pengiriman tercepat/teraman.
  - **Policy Enforcement**: Memeriksa margin setiap leg terhadap `SAFETY_POLICIES`.
  - **Global Optimization**: Membandingkan seluruh pesawat dan memilih yang memiliki skor tertinggi secara agregat, bukan sekadar yang lolos pertama kali.

### D. objective_threshold.py & objective_engine.py

- **Logika Baru**: Kedua script ini sekarang tidak lagi memiliki angka threshold/bobot sendiri. Keduanya "bertanya" pada `scenario_config.py` untuk mendapatkan aturan main yang konsisten sesuai `scenario_id` yang dipilih pengguna.

---

## 4. Kustomisasi & Ekstensibilitas

### set_custom_objective.py

Disediakan script utilitas bagi pengembang/pengguna ahli untuk mengubah target simulasi tanpa menyentuh kode inti.

- Bisa memilih **Policy ID** (misal: "Strict") namun mengatur **Weights** sendiri (misal: "Irit BBM 90%").
- Hasilnya disimpan otomatis ke `payloads.json` untuk diproses simulasi berikutnya.

---

## 5. Kamus Data & Konfigurasi

| File                       | Peran Utama      | Contoh Data Kunci                             |
| :------------------------- | :--------------- | :-------------------------------------------- |
| `payloads.json`            | Input Misi       | `scenario_id`, `deliveries`, `custom_config`. |
| `aircraft_parameters.json` | Spesifikasi Unit | MTOW, OEW, Fuel Flow, Rate of Climb.          |
| `location_params.json`     | Database Wilayah | Elevasi, Panjang Runway, Weather (OAT/QNH).   |

---

## 6. Standar Keselamatan (Research Alignment)

Sesuai dengan **Research Aerobridge (14)**, sistem mendukung:

- **Strict (VVIP)**: Margin 25% (Sesuai PDF ideal safety).
- **Standard**: Margin 10% (Rekomendasi operasional umum).
- **Aggressive**: Margin 2% (Batas legal minimum / Emergency absolute).

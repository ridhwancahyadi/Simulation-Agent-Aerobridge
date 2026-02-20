# Gap Analysis: Agent Response vs Update Research (14)

Berikut adalah analisis perbandingan antara output agent saat ini (`response_1771557655101.json`) dengan konsep terbaru pada **UPDATE RESEARCH Aerobridge (14).pdf**.

## 1. Kesesuaian Konsep (Alignment)

### ✅ Hard Gate & Physics

- **PDF**: Mengharuskan pengecekan fisik (Mass, Power, OGE, Fuel) dan margin.
- **JSON**: Sudah sangat detail (`hard_gate.sections`). Menampilkan `lambda_w`, `oge_buffer`, `power_margin`, dan `visual_weather_rules` dengan data yang akurat.
- **Status**: **Sesuai**.

### ✅ Dynamic Mission (Leg-by-Leg)

- **PDF**: Mengharuskan simulasi per-leg dengan update fuel dan payload.
- **JSON**: Output `simulation.legs` menampilkan breakdown per leg (Timika->Wamena, Wamena->Ilaga) dengan pengurangan fuel yang logis.
- **Status**: **Sesuai**.

### ✅ Contingency & What-If

- **PDF**: Meminta rekomendasi "what-if" atau bandara alternatif jika risiko tinggi.
- **JSON**: Bagian `contingencies` memberikan trigger spesifik (e.g., "Jika bahan bakar < 225 kg -> Diversi").
- **Status**: **Sesuai**.

---

## 2. Kekurangan & Perbedaan (Gaps)

Berdasarkan dokumen PDF terbaru, terdapat beberapa elemen kunci yang **BELUM** terlihat atau perlu penyesuaian pada JSON response:

### ❌ 1. Konsep "Scenario" vs "Objective Mode"

- **PDF (Page 10-11)**: Mengubah konsep dari _Single Objective_ menjadi **Scenario Based** (e.g., "Emergency/Medivac", "Logistic Max", "Balanced"). Skenario ini membungkus bobot (weights) menjadi preset standar.
- **JSON**: Masih menggunakan `objective_mode: "Delivery"` dengan custom weights manual.
- **Rekomendasi**:
  - Input JSON sebaiknya menerima field `scenario_id` (misal: "EMERGENCY", "LOGISTIC").
  - Output harus merefleksikan skenario apa yang sedang dijalankan.

### ❌ 2. Global Summary & Executive Summary Structure

- **PDF (Page 6 & 13)**: Meminta struktur output spesifik:
  - **Summary Global**: `Operational Status`, `Primary Reason`, `Total Risk Index`.
  - **Executive Summary**: `Supporting Factors`, `Attention Factors`, `Key Mitigations`.
  - **Aircraft Allocation**: Penjelasan eksplisit pembagian tugas antar pesawat.
- **JSON**:
  - Informasi tersebar di `agent_analysis` dan `top_candidates`.
  - Tidak ada object root `summary_global` yang merangkum _seluruh_ sirkuit misi.
  - `mitigations_and_actions` ada, tapi format "Executive Summary" yang _narrative-ready_ belum eksplisit.

### ❌ 3. Multi-Fleet Optimization Logic

- **PDF (Page 12)**: Agent harus bisa memutuskan: _"Apakah pakai 1 pesawat atau 2 pesawat?"_ dan memberikan alasannya.
- **JSON**: Hanya menampilkan `top_candidates` berisi 1 variasi (EC725 Caracal).
- **Gap**: Tidak ada informasi mengapa Cessna 208B tidak dipilih (apakah gagal hard gate? atau skornya kalah?). User butuh transparansi "Why not both?" atau "Why not Cessna?".

### ❌ 4. Tactical Layer Details

- **PDF (Page 7 & 13)**: Meminta `Threat Level` atau `Hostspot Proximity` (Aspek keamanan/KKB) di _Tactical Layer_.
- **JSON**: Fokus pada `weather` dan `terrain` (margin). Belum ada field eksplisit untuk _security threat_ atau _hostspot_ dalam output JSON.

---

## 3. Rekomendasi Perbaikan Kode

Untuk memenuhi standar PDF terbaru, simulasi kita perlu diupdate:

1.  **Update `objective_engine.py`**:
    - Implementasi **Scenario Dictionary** (Emergency, Logistic, etc) untuk auto-fill weights.
    - Ganti input `objective_mode` menjadi `scenario_mode`.
2.  **Update `mission_planning_engine.py`**:
    - Tambahkan logika **Fleet Allocation Strategy**. Cek kombinasi: (Fleet A only), (Fleet B only), dan (Fleet A + Fleet B - Split Payload).
    - Generate output `global_summary` yang merangkum status kesuksesan misi secara keseluruhan.
3.  **Update Output Formatter**:
    - Struktur ulang JSON agar memiliki key `executive_summary` dan `aircraft_allocation` di root level.

---

**Kesimpulan**: Agent response saat ini sudah kuat di sisi **Fisika & Kalkulasi**, namun perlu "re-skinning" pada rute **Logika Bisnis (Skenario)** dan ** Struktur Output** agar sesuai dengan format pelaporan baru yang diminta user.

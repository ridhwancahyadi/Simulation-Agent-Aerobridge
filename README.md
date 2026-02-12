# Aerobridge Simulation Agent

Agen simulasi untuk perencanaan misi penerbangan logistik di wilayah Papua, dengan pendekatan _Objective-Based Adaptive Constraints_. Sistem ini dirancang untuk menyeimbangkan antara agresivitas pengiriman (Payload) dengan batasan keselamatan (Safety) dan efisiensi.

## System Architecture

Sesuai dengan **Research Aerobridge**, sistem terdiri dari layer berikut:

1.  **Fleet Static Model**: Database parameter pesawat (Fixed Wing & Rotary Wing).
2.  **Hard Gate Layer**: Pemeriksaan kelayakan fisik (Runway, Climb Gradient, Power, Fuel).
3.  **Dynamic Mission Gate**: Simulasi _leg-by-leg_ dengan perhitungan bahan bakar real-time dan manajemen _alternate airport_.
4.  **Safety Margin Analysis**: Analisis margin kritis (Takeoff, Landing, Climb, Fuel, OGE) dan risiko taktis.
5.  **Objective Engine**: Evaluasi skoring misi berdasarkan 5 objektif utama.
6.  **Threshold Configuration**: Penyesuaian batas aman (_safety buffer_) berdasarkan mode objektif yang dipilih.

---

## Workflow & Execution

Urutan eksekusi script untuk menjalankan simulasi penuh:

### 1. Data Preparation

Pastikan file JSON berikut tersedia (hasil konversi dari Excel Parameter):

- `aircraft_parameters.json`
- `location_params.json`
- `payloads.json`
- `alternate_airports.json`

### 2. Hard Gate Simulation (Feasibility Checks)

Mengevaluasi apakah pesawat _mampu_ secara fisik melakukan penerbangan antar titik tanpa mempertimbangkan urutan misi komplek.

- **Script:** `python hard_feasibility_checks.py`
- **Output:** `hard_gate_output.json`
- **Checks:**
  - Mass Compliance (MTOW, MLW, CG)
  - Runway Feasibility (Takeoff & Landing Distance)
  - Visual Weather Rules (Visibility, Crosswind)
  - Climb Gradient & Power Margin

### 3. Dynamic Mission Simulation

Menjalankan simulasi misi multi-leg sesuai `payloads.json`. Memperhitungkan pengurangan berat (fuel burn & payload drop) setiap leg.

- **Script:** `python dynamic_mission_gate.py`
- **Output:** `dynamic_mission_output.json`
- **Fitur:** Auto-divert ke _alternate airport_ jika bahan bakar tidak cukup.

### 4. Safety Margin Analysis

Menganalisis hasil simulasi untuk menemukan titik terlemah (_weakest link_) dlm aspek keselamatan.

- **Script:** `python safety_margin_analysis.py`
- **Output:** `safety_margin_output.json`
- **Metrik:**
  - _Minimum Margin_: Nilai margin terkecil (misal: sisa landasan 50m).
  - _Tactical Risk Index_: Gabungan risiko cuaca, terrain, dan stress temporal.

### 5. Objective Threshold Evaluation

Memeriksa apakah margin keselamatan yang ada memenuhi standar _Objective Mode_ yang dipilih (misal: Mode "Delivery" mengizinkan margin yang lebih tipis dibanding Mode "Safety").

- **Script:** `python objective_threshold.py`
- **Input:** `hard_gate_output.json`, `safety_margin_output.json`
- **Output:** `objective_threshold_output.json`

### 6. Objective Scoring (Final Score)

Menghitung skor akhir misi.

- **Script:** `python objective_engine.py`
- **Output:** `objective_engine_output.json`

---

## Objective Formulas

Sistem menggunakan 5 parameter objektif dengan rumus sebagai berikut:

### 1. Delivery & Payload

Mengukur efektivitas pengiriman kargo.

```python
Score = min(1, Payload_Delivered / Payload_Planned)
```

_Target: Memaksimalkan muatan dalam satu penerbangan._

### 2. Temporal Efficiency

Mengukur kecepatan dan efisiensi waktu misi.

```python
Score = 1 / (1 + Total_Mission_Time_Hr)
```

_Target: Meminimalkan waktu tempuh._

### 3. Fuel Efficiency

Mengukur efisiensi penggunaan bahan bakar per kg payload.

```python
Ratio = Fuel_Used / Payload_Delivered
Score = 1 / (1 + Ratio)
```

_Target: Hemat bahan bakar._

### 4. Environmental Risk

Mengukur paparan terhadap risiko lingkungan (Cuaca, Terrain, Density Altitude).

```python
Risk = (0.4 * DA_Factor) + (0.4 * Wind_Factor) + (0.2 * Terrain_Factor)
Score = max(0, 1 - Risk)
```

_Target: Menghindari cuaca buruk dan terrain berbahaya._

### 5. Safety Margin

Mengukur seberapa jauh operasi dari batas fisik pesawat.

```python
Score = max(0, Minimum_Margin_Value)
```

_Target: Memaksimalkan buffer keselamatan._

---

## Advanced: Route Planning

Untuk mencari rute optimal secara otomatis (Permutations):

- **Script:** `python multi_route_mission.py`
- **Output:** `mission_planning_output.json`
- **Fungsi:** Menghitung semua kemungkinan urutan rute, melakukan simulasi, dan meranking berdasarkan _Combined Score_.

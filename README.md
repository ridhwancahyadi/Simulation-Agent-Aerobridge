# Simulation Agent Workflow

Dokumen ini menjelaskan alur kerja dan cara menjalankan script simulasi.

## 1. Persiapan Data

Konversi data pesawat dari Excel ke JSON. Jalankan jika ada perubahan pada file Excel.

- **Script:** `convert_aircraft_data.py`
- **Output:** `aircraft_parameters.json`
- **Command:** `python convert_aircraft_data.py`

Pastikan file konfigurasi berikut sudah sesuai:

- `location_params.json` (Data bandara/cuaca)
- `payloads.json` (Data misi)
- `alternate_airports.json` (Bandara alternatif)

## 2. Hard Gate Simulation (Feasibility Check)

Mengevaluasi kelayakan terbang berdasarkan batasan fisik (Runway, Climb, Power, Fuel).

- **Script:** `hard_feasibility_checks.py`
- **Output:** `hard_gate_output.json`
- **Command:** `python hard_feasibility_checks.py`

## 3. Analisis Margin Keselamatan

Mengidentifikasi margin yang paling kritis untuk setiap pesawat.

- **Script:** `safety_margin_analysis.py`
- **Output:** `safety_margin_output.json`
- **Command:** `python safety_margin_analysis.py`

## 4. Evaluasi Objektif

Mengevaluasi misi terhadap threshold tertentu dan memberikan skor.

- **Script:** `objective_threshold.py` (Cek threshold)
- **Output:** `objective_threshold_output.json`
- **Command:** `python objective_threshold.py`

- **Script:** `objective_engine.py` (Perhitungan skor)
- **Output:** `objective_engine_output.json`
- **Command:** `python objective_engine.py`

## 5. Simulasi Misi Dinamis

Simulasi per-leg dengan perhitungan fuel detail (Climb/Cruise/Descent) dan pengalihan ke bandara alternatif jika diperlukan.

- **Script:** `dynamic_mission_gate.py`
- **Output:** `dynamic_mission_output.json`
- **Command:** `python dynamic_mission_gate.py`

## 6. Simulasi Full Mission

Simulasi lengkap dari keberangkatan hingga kembali ke base (Return to Base).

- **Script:** `run_full_simulation.py`
- **Output:** `full_mission_simulation_output.json`
- **Command:** `python run_full_simulation.py`

## 7. Perencanaan Rute (Multi-Route Planning)

Mencari urutan rute pengiriman yang paling optimal.

- **Script:** `multi_route_mission.py`
- **Output:** `mission_planning_output.json`
- **Command:** `python multi_route_mission.py`

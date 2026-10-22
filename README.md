# Kinematic and Dynamic Calibration of a Dual-Arm Robotic System

MSc dissertation, NTU MAE (Schaeffler Hub). Submission: 30 April 2027.

Calibrating five actuators from two vendors (3 Synapticon SOMANET Circulo, 2 Sensodrive SensoJoint) with one motor-agnostic test bench and method, interconnecting two motors into one controlled system, then arm-level kinematic and dynamic calibration (scope fixed at the December review). Own target: 2 mm at the tip.

Progress log and decisions: Notion "Dissertation Protocol" (private). Written dissertation: Overleaf.

## Layout

| Folder | Content |
|---|---|
| `common/` | Shared Python: units, I/O, models, plotting |
| `tools/` | Shell environment and helpers (`startdrives`, `stopdrives`, `panelog`) |
| `hardware/` | CAD (3D-printed lever, mounts), wiring (e-stop / STO), electronics (load cell) |
| `calibrations/` | Frozen, versioned calibration parameters per actuator (the output of the method) |
| `M0_literature/` | Reading notes (bibliography lives in Overleaf) |
| `M1_first_actuator/` | Full characterisation of one actuator; protocol frozen for M2 |
| `M2_all_actuators_two_motor/` | Same protocol on all five actuators; two-motor system |
| `M3_arm/` ... `M6_dual_arm/` | Provisional until the December review |
| `dissertation/` | Figure export scripts for the written thesis |

Each experiment folder: `README.md`, `scripts/` (acquisition), `analysis/`, `data/raw/` (never edited), `data/processed/`, `figures/`.

## Milestones

| ID | Due | Milestone | Status |
|---|---|---|---|
| M0 | ongoing | Literature review | In progress |
| M1 | 15 Nov 2026 | First actuator calibrated | In progress |
| M2 | 6 Dec 2026 | All actuators and two-motor system (review) | Not started |
| M3 | 10 Jan 2027 | Arm ready (provisional) | Not started |
| M4 | 31 Jan 2027 | Horizontal calibration (provisional) | Not started |
| M5 | 21 Feb 2027 | Vertical calibration (provisional) | Not started |
| M6 | 14 Mar 2027 | Dual arm (provisional) | Not started |
| D | 9 Apr 2027 | Full draft | |
| M7 | 30 Apr 2027 | Submission | |

## Quick start

```bash
startdrives            # tmux: T1 hardware, T2 controllers, T3 shell (root); logs in logs/
velon; vel 0.5; velstop
stopdrives
panelog T1 40          # last 40 lines of a pane log
```
Stack: Ubuntu, ROS 2 Lyrical, `synapticon_ros2_control` (in `src/`, not tracked here), EtherCAT on `enp3s0`, CSP/CSV via DS402.

## Rules

- Raw data is never edited or overwritten. File names: `YYYYMMDD_<actuator>_<test>_<run>.csv`.
- Calibration data are never reused for validation.
- Every run records: date, hardware configuration, firmware and software revision, conditions, control mode, sampling rate, raw-data path, calibration version.
- No vendor manuals or datasheets in this repo (confidential; PDFs are git-ignored).

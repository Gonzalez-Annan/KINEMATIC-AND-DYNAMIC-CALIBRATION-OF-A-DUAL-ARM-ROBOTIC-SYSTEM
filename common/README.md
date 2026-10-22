# common

Shared code used by all milestones. Import from a script with:
```python
import sys, pathlib; sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3]))
from common import units
```
Planned modules: `units.py` (drive units to SI: mRPM, per-mille rated torque, counts), `io.py` (CSV load/save with metadata header), `models.py` (Coulomb, viscous, Stribeck, hysteresis), `plotting.py`.

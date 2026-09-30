"""Genereer de synthetische demo-bestanden in data/01-raw/demo/.

Gebruik:
    uv run python scripts/genereer_demo.py [doelmap]
"""

import sys
from pathlib import Path

from ho_bekostiging_bestanden.demo import DOEL, genereer_demo

if __name__ == "__main__":
    doel = Path(sys.argv[1]) if len(sys.argv) > 1 else DOEL
    for pad in genereer_demo(doel):
        print(f"Geschreven: {pad}")

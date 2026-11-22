import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
# I test scrivono su un log separato, senza inquinare quello dell'app
os.environ.setdefault(
    "CUDA_MONITOR_LOG",
    os.path.join(os.path.dirname(os.path.abspath(__file__)),
                 "logs", "tests.log"))

# core/__init__.py
# Аліаси без дублювання файлів:
#   core.mediator -> gateway.mediator
#   core.kernel   -> kernel.kernel

import sys
from importlib import import_module

# alias: core.mediator -> gateway.mediator
_gmed = import_module("gateway.mediator")
sys.modules[__name__ + ".mediator"] = _gmed

# alias: core.kernel -> kernel.kernel  (канонічне ядро з пакета kernel/)
_gkern = import_module("kernel.kernel")
sys.modules[__name__ + ".kernel"] = _gkern

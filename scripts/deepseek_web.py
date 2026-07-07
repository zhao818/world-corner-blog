import sys, os
_CATALOG = os.path.expanduser("~/catalog/scripts")
if os.path.isdir(_CATALOG) and _CATALOG not in sys.path:
    sys.path.insert(0, _CATALOG)
from deepseek_search import search, main as _main

if __name__ == "__main__":
    _main()

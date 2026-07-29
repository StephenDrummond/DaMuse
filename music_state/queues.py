from collections import defaultdict, deque
from typing import DefaultDict, Deque, Dict, Any

queues: DefaultDict[int, Deque[Dict[str, Any]]] = defaultdict(deque)

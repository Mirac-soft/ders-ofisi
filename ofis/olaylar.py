"""Asistan durumlarını tarayıcılara (SSE) dağıtır."""
import queue
import threading


class Yayinci:
    def __init__(self):
        self._aboneler: list[queue.Queue] = []
        self._kilit = threading.Lock()
        self.son: dict[tuple[str, str], dict] = {}  # yeni açılan sayfa son durumu görsün

    def yayinla(self, olay: dict) -> None:
        with self._kilit:
            self.son[(olay["ders"], olay["asistan"])] = olay
            for q in self._aboneler:
                q.put(olay)

    def abone(self) -> queue.Queue:
        q = queue.Queue()
        with self._kilit:
            self._aboneler.append(q)
        return q

    def ayril(self, q: queue.Queue) -> None:
        with self._kilit:
            if q in self._aboneler:
                self._aboneler.remove(q)

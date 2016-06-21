"""PivotCalculator

Pivot points is the top/bottom that the price has ever reached.
"""

from collections import deque, namedtuple
from operator import gt

class PivotCalculator(object):
    def __init__(self, window_size=5, cmp=gt):
        self.window_size = window_size
        self.cmp = cmp

        # exit_check: whether it should be considered as a local extrim
        # when it get removed from the qeue
        self.QE = namedtuple("QueueEelment", ["val", "idx", "exit_check"])
        self._q = deque()   # queue to hold the local extrim candidates
        self._idx = 0       # index of the current value to be processed.

        self._result = []
        self._post_process_done = False

    def __call__(self, v):
        is_extrim = False

        # XXX: local extrim <=> if ENTER and EXIT checks are both True

        # ENTER: if it is a local extrim when it enters the queue
        # there should be no other element in the queue
        while self._q and self.cmp(v, self._q[-1][0]):
            self._q.pop()

        exit_check = not self._q
        t = self.QE(v, self._idx, exit_check)
        self._q.append(t)

        # EXIT: if it is a local extrim point when it leaves the queue
        # it should be still the best candidate (in the front).
        candidate = self._q[0]
        # e.g. windows_size = 5, candidate.idx = 0, self._idx = 4
        if self._idx - candidate.idx >= self.window_size - 1:
            self._q.popleft()
            if candidate.exit_check:
                is_extrim = True

        # DEBUG:
        #print(self._idx, "{:.2f}".format(v), self._q[0] if self._q else [],
        #      ["{:.2f}".format(e[0]) for e in self._q],
        #      self._idx - self.window_size, result)

        # Only after seeing window_size of elements we can tell if a local extrim is found or not.
        if self._idx >= self.window_size - 1:
            self._result.append(is_extrim)

        self._idx += 1

    def _post(self):
        for i in range(self._idx - self.window_size + 1, self._idx):
            # XXX: there should be maximum window_size-1 of elements left to be examined.
            # and only the first element is possible to be an extrim.
            is_extrim = self._q and self._q[0].idx == i and self._q[0].exit_check
            self._result.append(is_extrim)

        self._q.clear()

    @property
    def result(self):
        if not self._post_process_done:
            self._post_process_done = True
            self._post()

        return self._result


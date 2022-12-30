# coding=utf-8
import heapq
from collections import deque
import random
try:
    from itertools import izip
except ImportError:
    izip = zip


class LifoList(deque):
    '''List that pops from the end.'''

    def sorted(self):
        return list(self)[::-1]


class FifoList(deque):
    '''List that pops from the beginning.'''
    def pop(self):
        return super(FifoList, self).popleft()

    def sorted(self):
        return list(self)


class BoundedPriorityQueue(object):
    def __init__(self, limit=None, *args):
        self.limit = limit
        self.queue = list()

    def __getitem__(self, val):
        return self.queue[val]

    def __len__(self):
        return len(self.queue)

    def append(self, x):
        heapq.heappush(self.queue, x)
        if self.limit and len(self.queue) > self.limit:
            self.queue.remove(heapq.nlargest(1, self.queue)[0])
            heapq.heapify(self.queue)

    def pop(self):
        return heapq.heappop(self.queue)

    def extend(self, iterable):
        for x in iterable:
            self.append(x)

    def clear(self):
        self.queue.clear()

    def remove(self, x):
        self.queue.remove(x)
        heapq.heapify(self.queue)

    def sorted(self):
        return heapq.nsmallest(len(self.queue), self.queue)
        # 使えるかも

class InverseTransformSampler(object):
    def __init__(self, weights, objects):
        # 今回はfitnessがweights、objectsがfringeという個体の集まり？
        assert weights and objects and len(weights) == len(objects)
        self.objects = objects
        tot = float(sum(weights))
        if tot == 0:
            tot = len(weights)
            weights = [1 for x in weights] # weightの数文の1の配列を作っている
            # もしweightの合計が０なら重みを全部1にしている
        accumulated = 0
        self.probs = [] # これが謎
        for w, x in izip(weights, objects):
            p = w / tot  # それぞれの個体の適応度をpにいれている？いみわからん
            accumulated += p
            self.probs.append(accumulated)

    def sample(self):
        # ここを変えたらよさげ！
        target = random.random()
        i = 0
        while i + 1 != len(self.probs) and target > self.probs[i]:
            i += 1
        return self.objects[i]
        # 良く分からんが個体を一個返す。返す個体はランダム。だからランダム探索になっている


def _generic_arg(iterable, function, better_function):
    values = [function(x) for x in iterable]
    better_value = better_function(values)
    candidates = [x for x, value in zip(iterable, values) if value == better_value]
    return random.choice(candidates)


def argmin(iterable, function):
    return _generic_arg(iterable, function, min)


def argmax(iterable, function):
    return _generic_arg(iterable, function, max)

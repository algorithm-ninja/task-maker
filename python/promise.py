#!/usr/bin/env python3
from capnp.lib.capnp import PromiseFulfillerPair, Promise


class UnionPromiseBuilder:
    def __init__(self):
        self.p = PromiseFulfillerPair()
        self.promises = list()
        self.resolved = 0
        self.finalized = False

    def add(self, promise):
        def then1(_):
            self.resolved += 1
            if self.finalized and self.resolved == len(self.promises):
                self.p.fulfill()
        def then2():
            then1(None)
        # if there is this method the promise is a VoidPromise
        if hasattr(promise, "as_pypromise"):
            promise.then(then2)
        else:
            promise.then(then1)

    def finalize(self):
        self.finalized = True
        if self.resolved == len(self.promises):
            self.p.fulfill()
        return self.p.promise


class ForkablePromise:
    def __init__(self, promise):
        self.promise = promise
        self.result = None
        self.pending = list()

        def then(ret):
            self.result = ret
            for f, fulfiller in self.pending:
                f(ret)
                fulfiller.fulfill()
        self.promise.then(then)

    def then(self, f):
        fulfiller = PromiseFulfillerPair()
        if self.promise.is_consumed:
            f(self.result)
            fulfiller.fulfill()
        else:
            self.pending.append((f, fulfiller))
        return fulfiller.promise
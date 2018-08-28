# coding: utf-8

import chainer
import chainer.functions as F
import chainer.links as L

# Network definition


class A(chainer.Chain):

    def __init__(self):
        super(A, self).__init__()

    def forward(self, x, t):
        loss = F.softmax_cross_entropy(x, t)
        return loss


# ======================================from MLP

if __name__ == '__main__':
    import numpy as np
    np.random.seed(314)

    out_n = 2
    batch_size = 1
    model = A()

    v = np.random.rand(batch_size, out_n).astype(np.float32)
    w = np.random.randint(out_n,size=batch_size)
    import testcasegen
    testcasegen.generate_testcase(model, [v,w])

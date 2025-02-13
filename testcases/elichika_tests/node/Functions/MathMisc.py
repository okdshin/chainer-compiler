# coding: utf-8

import chainer
import chainer.functions as F

# Network definition


class Sin(chainer.Chain):
    def __init__(self):
        super(Sin,self).__init__()

    def forward(self, x):
        y1 = F.sin(x)
        return y1

class Sign(chainer.Chain):
    def __init__(self):
        super(Sign,self).__init__()

    def forward(self, x):
        y1 = F.sign(x)
        return y1

class Sinh(chainer.Chain):
    def __init__(self):
        super(Sinh,self).__init__()

    def forward(self, x):
        y1 = F.sinh(x)
        return y1

class Cos(chainer.Chain):
    def __init__(self):
        super(Cos,self).__init__()

    def forward(self, x):
        y1 = F.cos(x)
        return y1

class Cosh(chainer.Chain):
    def __init__(self):
        super(Cosh,self).__init__()

    def forward(self, x):
        y1 = F.cosh(x)
        return y1

class Tan(chainer.Chain):
    def __init__(self):
        super(Tan,self).__init__()

    def forward(self, x):
        y1 = F.tan(x)
        return y1

class Tanh(chainer.Chain):
    def __init__(self):
        super(Tanh,self).__init__()

    def forward(self, x):
        y1 = F.tanh(x)
        return y1

class ArcSin(chainer.Chain):
    def __init__(self):
        super(ArcSin,self).__init__()

    def forward(self, x):
        y1 = F.arcsin(x)
        return y1

class ArcCos(chainer.Chain):
    def __init__(self):
        super(ArcCos,self).__init__()

    def forward(self, x):
        y1 = F.arccos(x)
        return y1

class ArcTan(chainer.Chain):
    def __init__(self):
        super(ArcTan,self).__init__()

    def forward(self, x):
        y1 = F.arctan(x)
        return y1

class Exp(chainer.Chain):
    def __init__(self):
        super(Exp,self).__init__()

    def forward(self, x):
        y1 = F.exp(x)
        return y1

class Log(chainer.Chain):
    def __init__(self):
        super(Log,self).__init__()

    def forward(self, x):
        y1 = F.log(x)
        return y1

# ======================================
from chainer_compiler.elichika import testtools
import numpy as np

def main():
    np.random.seed(314)

    x = np.random.rand(6, 4).astype(np.float32)
    testtools.generate_testcase(Sin(), [x], subname='sin')
    testtools.generate_testcase(Sinh(), [x], subname='sinh')
    testtools.generate_testcase(Sign(), [x], subname='sign')
    testtools.generate_testcase(Cos(), [x], subname='cos')
    testtools.generate_testcase(Cosh(), [x], subname='cosh')
    testtools.generate_testcase(Tan(), [x], subname='tan')
    testtools.generate_testcase(Tanh(), [x], subname='tanh')
    testtools.generate_testcase(ArcSin(), [x], subname='arcsin')
    testtools.generate_testcase(ArcCos(), [x], subname='arccos')
    testtools.generate_testcase(ArcTan(), [x], subname='arctan')
    testtools.generate_testcase(Exp(), [x], subname='exp')
    testtools.generate_testcase(Log(), [x], subname='log')

if __name__ == '__main__':
    main()

import math


def remap(x: float, in_min: float, in_max: float, out_min: float, out_max: float):
    return (x - in_min) * (out_max - out_min) / (in_max - in_min) + out_min


pi_by_2 = math.pi / 2


class Curves:
    @classmethod
    def linear(cls, __x: float):
        """
        Linear interpolation. No curves applied.
        """
        return __x

    @classmethod
    def sine(cls, __x: float):
        """
        Curve similar to math.sin.
        """
        return math.sin(remap(__x, 0, 1, 0, pi_by_2))

    @classmethod
    def isine(cls, __x: float):
        """
        Curve similar to inverse of math.sin.
        """
        return cls.sine(1 - __x)

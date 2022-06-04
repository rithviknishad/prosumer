from enum import Enum


class ProsumerStatus(Enum):
    IMPORT = "IMPORTING"
    EXPORT = "EXPORTING"
    SELF_SUSTAIN = "SELF SUSTAINING"

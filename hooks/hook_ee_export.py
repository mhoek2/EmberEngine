import os
import sys

if getattr(sys, "frozen", False):
    os.environ["EE_EXPORTED"] = "1"
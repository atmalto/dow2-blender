"""DoW2 destruction physics package.

STATUS: Experimental. Hull generation / import / export is unstable, may produce
partial or invalid results, and is not covered by the standard test suite.
"""

from . import hull_properties, operators, properties


def register():
    properties.register()
    hull_properties.register()
    operators.register()


def unregister():
    operators.unregister()
    hull_properties.unregister()
    properties.unregister()
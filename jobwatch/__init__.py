import ska_helpers
__version__ = ska_helpers.get_version(__package__)

from .jobwatch import *

def test(*args, **kwargs):
    '''
    Run py.test unit tests.
    '''
    import testr
    return testr.test(*args, **kwargs)


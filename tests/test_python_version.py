import sys

def test_python311_or_higher():
    assert sys.version_info >= (3, 11), "Python 3.11+ is required"

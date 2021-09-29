__version__ = '0.1.0'

import pickle as _pickle

from .manhattan import Manhattan
from .pca import PCA


def read(filepath):
    with open(filepath, 'rb') as stream:
        return _pickle.load(stream)

__version__ = '0.1.1'

import pickle as _pickle

from .interactiveplot import InteractivePlot
from .manhattan import Manhattan
from .pca import PCA


def read(filepath):
    """
    Reads a plot from a `.caplot` file and returns the class.

    Parameters
    ----------
    filepath: str
        Path-like object that points to the file.

    Returns
    -------
    InteractivePlot
        An instance of a subclass of `InteractivePlot`.
    """
    with open(filepath, 'rb') as stream:
        return _pickle.load(stream)

from .interactiveplot import InteractivePlot
import importlib.resources
import yaml

with importlib.resources.path('caplot', 'refgen.yaml') as path:
    with open(path) as file:
        refGen = yaml.load(file, Loader=yaml.FullLoader)

class Manhattan(InteractivePlot):

    def Generate(self, contig, position, pvalue, mlog10=False, genome='GRCh37', numContig=22):
        """
        The method must be overridden to implement the functionality related to populating a Bokeh `Figure` with the
        necessary glyphs. To do so, the settings stored via `.Configure()` must be taken into account.
        """
        pass

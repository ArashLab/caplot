from .interactiveplot import InteractivePlot
import importlib.resources
import yaml

with importlib.resources.path('caplot', 'refgen.yaml') as path:
    with open(path) as file:
        refGenome = yaml.load(file, Loader=yaml.FullLoader)

class Manhattan(InteractivePlot):

    def GlobalPosition():
        ### Calculate x position from chr:pos and refGenome
        pass

    def Generate(self, contig, position, pvalue, mlog10=False, genome='GRCh37', numContig=22):
        """
        The method must be overridden to implement the functionality related to populating a Bokeh `Figure` with the
        necessary glyphs. To do so, the settings stored via `.Configure()` must be taken into account.
        """

        ### Add X-Y fields to the hovers:
        self.AddHover({'contig':contig, 'pos':position,  'pval':pvalue})
        
        pass

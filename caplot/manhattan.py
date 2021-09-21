from .interactiveplot import InteractivePlot
import importlib.resources
import yaml
from munch import Munch

with importlib.resources.path('caplot', 'refgen.yaml') as path:
    with open(path) as file:
        refGenome = yaml.load(file, Loader=yaml.FullLoader)

class Manhattan(InteractivePlot):

    def GlobalPosition(self, contig, position):
        cLen = refGenome[self._config.genome]
        globalPosition = cLen[contig] + position
        return globalPosition

    def Configure(self, **kwargs):
        """
        The method must be overridden to implement the functionality related to populating a Bokeh `Figure` with the
        necessary glyphs. To do so, the settings stored via `.Configure()` must be taken into account.
        """

        ### user may change the config
        self._config.update(kwargs)

        ### update X and Y based on the new config
        if any([(key in kwargs) for key in ['contig', 'position', 'genome']]):
            ### we should update the data[X] from contig:position using GlobalPosition function
            pass
        if any([(key in kwargs) for key in ['pvalue', 'mlog10']]):
            ### we should update the data[Y]. if mlog10 is false data[Y]=-log10(data[pvalue]) else data[Y]=data[pvalue]
            pass

        ### Add X-Y fields to the hovers:
        self.AddHover({'contig':self._config.contig, 'pos':self._config.position,  'pval':self._config.pvalue})
        
        pass

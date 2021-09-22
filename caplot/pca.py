import json
import sys
from typing import AnyStr, List, Literal, Tuple

from bokeh.plotting import figure
from bokeh.layouts import gridplot
from bokeh.models import (
    CategoricalColorMapper,
    ColumnDataSource,
    HoverTool,
    LinearColorMapper,
)
from bokeh import palettes
import ipywidgets as widgets

from .interactiveplot import InteractivePlot

class PCA(InteractivePlot):

    def __init__(self, source=None, loadQuery=None, filterQuery=None, keep=True, highlightQuery=None, highlight=True, hovers=None, plots=None, coloringColumn=None, coloringPalette='Magma256', coloringStyle='Continuous', numCols=3):
        if source:
            super(PCA, self).__init__(source=source, loadQuery=loadQuery, filterQuery=filterQuery, keep=keep, highlightQuery=highlightQuery, highlight=highlight, hovers=hovers)
            if plots:
                self.Configure(plots=plots, coloringColumn=coloringColumn, coloringPalette=coloringPalette, coloringStyle=coloringStyle, numCols=numCols)


    def Configure(self, plots=None, coloringColumn=None, coloringPalette='Magma256', coloringStyle='Continuous', numCols=3):
        """Configures the PCA plot.

        Parameters
        ----------
        plots: List[AnyStr] or List[Tuple[AnyStr, AnyStr]] or str
            The charts that must be drawn. This can be a list of strings or a list of pairs of strings.
        coloringColumn: str
            The name of the column that the coloring is based on.
        coloringPalette: str
            The name of the palette, recognized by Bokeh.
        coloringStyle: Literal['Categorical', 'Continuous']
            Either `Categorical` or `Continuous` as a string.
        numCols: int
            Number of charts in a single row.
        """
        # Not a good approach regarding plots, but the alternative requires a better widget for the field.
        self._config = {
            'plots': plots if isinstance(plots, dict) else json.loads(plots),
            'coloringColumn': coloringColumn,
            'coloringPalette': coloringPalette,
            'coloringStyle': coloringStyle,
            'numCols': numCols,
        }

    def Widgets(self):
        return {
            **super(PCA, self).Widgets(),
            'plots': widgets.Text(value=str(self._config.get('plots', []))),
            'coloringColumn': widgets.Text(value=self._config.get('coloringColumn')),
            'coloringPalette': widgets.Dropdown(options=[
                'Greys256', 'Inferno256', 'Magma256', 'Plasma256', 'Viridis256', 'Cividis256', 'Turbo256',  # Continuous
                'Category10', 'Category20', 'Category20b', 'Category20c', 'Accent', 'GnBu', 'PRGn', 'Paired',  # Categorical
            ], value=self._config.get('coloringPalette', 'Turbo256')),
            'coloringStyle': widgets.Dropdown(options=['Categorical', 'Continuous'], value=self._config.get('coloringStyle', 'Continuous')),
            'numCols': widgets.IntSlider(value=3, min=1, max=8),
        }

    def _Plots(self):
        plots = self._config['plots']
        numCols = self._config['numCols']
        if all(isinstance(element, str) for element in plots):  # List of strings.
            if len(plots) == 2:
                plots = [plots]
            else:
                plots = [(first, second) for first in plots for second in plots if first != second]
        # Otherwise, we assume `plots` is already a list of tuples, containing a pair of strings.
        # We now group them up in batches of `numCols`.
        plots = [plots[start:start+numCols] for start in range(0, len(plots), numCols)]
        return plots

    def _Draw(self, x, y):
        plot = figure(x_axis_label=x, y_axis_label=y)
        data = (self._data.loc[self._filtered] if self._filtered is not None else self._data).copy()
        if self._highlighted is not None:
            data['_opacity_'] = data.index.isin(self._highlighted).astype('int') * .5 + .5
            alpha = '_opacity_'
        else:
            alpha = 1
        try:
            if self._config['coloringColumn']:
                targetColumn = data[self._config['coloringColumn']]
                if self._config['coloringStyle'] == 'Categorical':
                    palette = getattr(palettes, self._config['coloringPalette'])
                    palette = next(value for key, value in palette.items() if key > targetColumn.nunique())
                    mapper = CategoricalColorMapper(palette=palette, factors=targetColumn.unique().tolist())
                else:
                    mapper = LinearColorMapper(palette=self._config['coloringPalette'], low=targetColumn.min(), high=targetColumn.max())
                color = {'field': self._config['coloringColumn'], 'transform': mapper}
            else:
                color = 'gray'
        except StopIteration:
            print('The chosen color palette does not have enough distinct colors for the selected column.', file=sys.stderr)
        else:
            source = ColumnDataSource(data)
            plot.circle(source=source, x=x, y=y, color=color, alpha=alpha, size=5)
            plot.add_tools(HoverTool(tooltips=[(key, f'@{{{value}}}') for key, value in self._hovers.items()]))
            return plot

    def Generate(self):
        grid = gridplot([[self._Draw(x, y) for x, y in row] for row in self._Plots()])
        return grid

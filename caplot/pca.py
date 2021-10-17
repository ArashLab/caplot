import itertools
import json

import ipywidgets as widgets
import pandas as pd
from bokeh import palettes
from bokeh.core.validation.warnings import MISSING_RENDERERS
from bokeh.layouts import gridplot, row
from bokeh.models import (
    CategoricalColorMapper,
    ColumnDataSource,
    HoverTool,
    LinearColorMapper, ColorBar)
from bokeh.plotting import figure

from .interactiveplot import InteractivePlot


class PCA(InteractivePlot):
    """
    The `PCA` class is intended to display multiple scatter subplots, pitting certain columns against one another.

    Parameters
    ----------
    source: str or pd.DataFrame
        Path to a file Pandas can read from, the URL for a SQL database, or a literal DataFrame.
    loadQuery: str
        A SQL query ran on the data on initialization. This argument is required when connecting to a SQL database,
        but optional for other supported inputs. This would limit the data that is kept in memory.
    filter: str
        An optional SQL query to specify which records must be kept in.
    invertFilter: str
        An optional SQL query to specify which records must be left out.
    filterTemplate: str
        An optional template query based on which custom widgets will be shown.
    highlight: str
        An optional SQL query to specify which records must be highlighted.
    invertHighlight: str
        An optional SQL query to specify which records must not be highlighted, while the rest are.
    highlightTemplate: str
        An optional template query based on which custom widgets will be shown.
    minorAlpha: float
        Specifies the opacity of points that have not been highlighted while some others are. Defaults to 0.5.
    greyHighlight: bool
        Whether the non-highlighted data points must be colored grey.
    hovers: dict
        A mapping of arbitrary labels to certain columns in the data source.
    subplots: list of str or list of list of str
        The subplots that must be drawn. When this argument is a list of strings, all combinations of the elements
        of the list will be drawn. However, the argument can also be passed a list of pairs of column names,
        explicitly naming the columns that must be pit together.
    coloringColumn: str
        The name of a column present in the data.
    coloringStyle: str
        Either `"Categorical"` or `"Continuous"`. Defaults to `"Categorical"`.
    coloringPalette: str
        Name of a palette, supported by Bokeh and suitable for the chosen `coloringStyle`. Defaults to `"Category10"`.
    numCols: int
        Number of subplots in each row. Default is 2.
    subplotWidth: int
        Width of each subplot. Default is 400 pixels.
    subplotHeight: int
        Height of each subplot. Default is 400 pixels.
    pointSize: int or float
        Passed directly to Bokeh to specify the size of all points. Default is 5.
    """

    CategoricalPalettes = 'Category10', 'Category20', 'Category20b', 'Category20c', 'Accent', 'GnBu', 'PRGn', 'Paired'
    ContinuousPalettes = 'Greys256', 'Inferno256', 'Magma256', 'Plasma256', 'Viridis256', 'Cividis256', 'Turbo256'

    def __init__(self, source=None, loadQuery=None, filter=None, invertFilter=None, filterTemplate=None, highlight=None,
                 invertHighlight=None, highlightTemplate=None, minorAlpha=None, greyHighlight=None, hovers=None,
                 subplots=None, coloringColumn=None, coloringStyle='Categorical', coloringPalette='Category10',
                 numCols=2, subplotWidth=400, subplotHeight=400, pointSize=5):
        super(PCA, self).__init__(source, loadQuery, filter, invertFilter, filterTemplate, highlight,
                                  invertHighlight, highlightTemplate, minorAlpha, greyHighlight, hovers)
        self._subplots = None
        self._coloringColumn = None
        self._coloringPalette = None
        self._coloringStyle = None
        self.numCols = numCols
        self.subplotWidth = subplotWidth
        self.subplotHeight = subplotHeight
        self.pointSize = pointSize
        # Initializations
        if subplots is not None:
            self.subplots = subplots
        if coloringColumn is not None:
            self.coloringColumn = coloringColumn
            if coloringStyle is not None:
                self.coloringStyle = coloringStyle
            if coloringPalette is not None:
                self.coloringPalette = coloringPalette

    @property
    def subplots(self):
        """
        list of str or list of list of str: A grid of string pairs, specifying the columns that must be plotted against one another.

        When the property gets assigned a list of column names, it will generate a grid of their binary combinations.
        """
        return self._subplots or []

    @subplots.setter
    def subplots(self, value):
        self._subplots = value if isinstance(value, list) else json.loads(value)

    def _SubplotsOrganized(self):
        if not self._subplots:
            return []
        if all(isinstance(element, str) for element in self._subplots):
            subplots = list(itertools.combinations(self._subplots, 2))
        elif all(isinstance(element, list) for element in self._subplots):
            subplots = self._subplots  # The structure of `value` is already what we want.
        else:
            raise RuntimeError('Specified "subplots" is invalid. This attribute can be a list of strings, or a list of pairs of strings.')
        return [subplots[start:start + self.numCols] for start in range(0, len(subplots), self.numCols)]

    @property
    def coloringColumn(self):
        """
        str: Name of a column present in the data.
        """
        return self._coloringColumn

    @coloringColumn.setter
    def coloringColumn(self, value):
        if self.source is not None:
            assert value in self.source.columns, f'Could not find a column named "{value}" in data.'
        self._coloringColumn = value

    @property
    def coloringStyle(self):
        return self._coloringStyle

    @coloringStyle.setter
    def coloringStyle(self, value):
        """
        str: Name of a column present in the data.
        """
        assert value in ('Categorical', 'Continuous'), 'Coloring style can be "Categorical" or "Continuous".'
        self._coloringStyle = value

    @property
    def coloringPalette(self):
        """
        str: Either `"Categorical"` or `"Continuous"`.
        """
        return self._coloringPalette

    @coloringPalette.setter
    def coloringPalette(self, value):
        choices = self.CategoricalPalettes if self._coloringStyle == 'Categorical' else self.ContinuousPalettes
        assert value in choices, f'Acceptable coloring palettes are: {", ".join(choices)}.'
        self._coloringPalette = value

    def Widgets(self):
        return {
            'subplots': widgets.Text(value=json.dumps(self.subplots), placeholder='JSON Array (or an array of arrays)'),
            'coloringColumn': widgets.Dropdown(options=self.source.columns, value=self.coloringColumn) if self.source is not None else widgets.Text(value=self.coloringColumn),
            'coloringStyle': widgets.Dropdown(options=['Categorical', 'Continuous'], value=self.coloringStyle),
            'coloringPalette': widgets.Dropdown(options=[*self.CategoricalPalettes, *self.ContinuousPalettes], value=self.coloringPalette),
            'numCols': widgets.IntSlider(value=3, min=1, max=8),
        }
    
    def Generate(self, outputBackend='canvas', hideBokehLogo=True):
        data = self._ProcessedData()
        color, colorBar = self._ColorMapping(data)
        extraKwargs = {'toolbar_options': {'logo': None}} if hideBokehLogo else {}
        grid = gridplot([[self._Draw(data, x, y, color or 'blue', outputBackend) for x, y in gridRow]
                         for gridRow in self._SubplotsOrganized()], **extraKwargs)
        if colorBar is not None:
            self._safeWarnings.add(MISSING_RENDERERS)  # We are doing an empty dummy plot for the color-bar.
            dummy = figure(height=200, width=100, toolbar_location=None, min_border=0, outline_line_color=None)
            dummy.add_layout(colorBar, place='left')
            dummy.output_backend = outputBackend
            grid = row(children=[grid, dummy])
        else:
            self._safeWarnings.discard(MISSING_RENDERERS)
        return grid

    def _ColorMapping(self, data):
        """
        The method generates a mapper for the colors, as well as a color-bar which can be used externally.

        Parameters
        ----------
        data: pd.DataFrame
            Processed data to draw the plot from.

        Returns
        -------
        color: str or dict
            Passed directly to Bokeh when plotting.
        colorBar: ColorBar
            Must be drawn manually on a subplot.
        """
        if not self.coloringColumn:
            return None, None
        coloringColumn = self.coloringColumn
        targetColumn = data[self.coloringColumn]
        coloringStyle = self.coloringStyle or ('Categorical' if targetColumn.nunique() <= 10 else 'Continuous')
        if coloringStyle == 'Categorical':
            try:
                assert self.coloringPalette in self.CategoricalPalettes, 'Selected palette is not suitable for categorical data.'
                palette = getattr(palettes, self.coloringPalette)
                palette = next(value for key, value in palette.items() if key > targetColumn.nunique())
            except StopIteration:
                raise RuntimeError('The chosen color palette does not have enough distinct colors for the selected column.')
            else:
                palette = palette[:targetColumn.nunique()]
                if pd.api.types.is_numeric_dtype(targetColumn.dtype):
                    targetColumn = targetColumn.astype('str')
                    data['__category__'] = targetColumn
                    coloringColumn = '__category__'
                mapper = CategoricalColorMapper(palette=palette, factors=targetColumn.unique().tolist())
        else:
            assert self.coloringPalette in self.ContinuousPalettes, 'Selected palette is not suitable for continuous data.'
            mapper = LinearColorMapper(palette=self.coloringPalette, low=targetColumn.min(), high=targetColumn.max())
        color = {'field': coloringColumn, 'transform': mapper}
        colorBar = ColorBar(color_mapper=mapper, label_standoff=12)  # Common between all subplots.
        return color, colorBar

    def _Draw(self, data, xColumnName, yColumnName, color, outputBackend):
        """
        The method draws a single PCA plot, pitting `x` against `y`.

        Parameters
        ----------
        data: pd.DataFrame
            Processed data to draw the plot from.
        xColumnName: str
            Name of a column shown on the horizontal axis.
        yColumnName: str
            Name of a column shown on the vertical axis.
        color: str or dict
            Passed directly to Bokeh when plotting.
        outputBackend: str
            Specifies the target output backend for Bokeh.

        Returns
        -------
        bokeh.models.plots.Plot
            Drawn subplot.
        """
        subplot = figure(width=self.subplotWidth, height=self.subplotHeight, x_axis_label=xColumnName, y_axis_label=yColumnName)
        subplot.output_backend = outputBackend
        for highlighted in (False, True):
            source = ColumnDataSource(data[data['__highlighted__'] == highlighted])
            subplot.circle(source=source, x=xColumnName, y=yColumnName, size=self.pointSize, line_color=None,
                           color='grey' if self.greyHighlight and not highlighted else color,
                           alpha=1 if highlighted else self.minorAlpha)
        if self._hovers:
            subplot.add_tools(HoverTool(tooltips=[(key, f'@{{{value}}}') for key, value in self._hovers.items()]))
        return subplot

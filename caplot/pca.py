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
    LinearColorMapper, ColorBar, )
from bokeh.plotting import figure

from .interactiveplot import InteractivePlot


class PCA(InteractivePlot):
    CategoricalPalettes = 'Category10', 'Category20', 'Category20b', 'Category20c', 'Accent', 'GnBu', 'PRGn', 'Paired'
    ContinuousPalettes = 'Greys256', 'Inferno256', 'Magma256', 'Plasma256', 'Viridis256', 'Cividis256', 'Turbo256'

    def __init__(self, source=None, loadQuery=None, filter=None, invertFilter=None, filterTemplate=None, highlight=None,
                 invertHighlight=None, highlightTemplate=None, minorAlpha=None, hovers=None, subplots=None,
                 coloringColumn=None, coloringStyle='Categorical', coloringPalette='Category10', numCols=2,
                 subplotWidth=400, subplotHeight=400, pointSize=5):
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
            Specifies the opacity of points that have not been highlighted while some others are.
        hovers: dict
            A mapping of arbitrary labels to certain columns in the data source.
        subplots: list of str or list of list of str
            The subplots that must be drawn. When this argument is a list of strings, all combinations of the elements
            of the list will be drawn. However, the argument can also be passed a list of pairs of column names,
            explicitly naming the columns that must be pit together.
        coloringColumn: str
            The name of a column present in the data.
        coloringStyle: str
            Either `"Categorical"` or `"Continuous"`.
        coloringPalette: str
            Name of a palette, supported by Bokeh and suitable for the chosen `coloringStyle`.
        numCols: int
            Number of subplots in each row.
        subplotWidth: int
            Width of each subplot.
        subplotHeight: int
            Height of each subplot.
        pointSize: int or float
            Passed directly to Bokeh to specify the size of all points.
        """
        super(PCA, self).__init__(source, loadQuery, filter, invertFilter, filterTemplate, highlight, invertHighlight,
                                  highlightTemplate, minorAlpha, hovers)
        self._subplots = None
        self._coloringColumn = None
        self._coloringPalette = None
        self._coloringStyle = None
        self._colorBar = None
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
    
    def Generate(self):
        grid = gridplot([[self._Draw(x, y) for x, y in gridRow] for gridRow in self._SubplotsOrganized()])
        if self._colorBar is not None:
            self._safeWarnings.add(MISSING_RENDERERS)  # We are doing an empty dummy plot for the color-bar.
            dummy = figure(height=200, width=100, toolbar_location=None, min_border=0, outline_line_color=None)
            dummy.add_layout(self._colorBar, place='left')
            grid = row(children=[grid, dummy])
        else:
            self._safeWarnings.discard(MISSING_RENDERERS)
        return grid

    def _Draw(self, x, y):
        """
        The method draws a single PCA plot, pitting `x` against `y`.

        Parameters
        ----------
        x: str
            Name of a column shown on the horizontal axis.
        y: str
            Name of a column shown on the vertical axis.

        Returns
        -------
        bokeh.models.plots.Plot
            Drawn subplot.
        """
        self._colorBar = None  # In case of a major change in settings, we don't want the old color-bar hanging around!
        subplot = figure(width=self.subplotWidth, height=self.subplotHeight, x_axis_label=x, y_axis_label=y)
        data = self._ProcessedData()
        if self.coloringColumn:
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
            self._colorBar = ColorBar(color_mapper=mapper, label_standoff=12)  # Common between all subplots.
        else:
            color = 'blue'
        source = ColumnDataSource(data)
        subplot.circle(source=source, x=x, y=y, color=color, alpha='__alpha__', size=self.pointSize, line_color=None)
        if self._hovers:
            subplot.add_tools(HoverTool(tooltips=[(key, f'@{{{value}}}') for key, value in self._hovers.items()]))
        return subplot

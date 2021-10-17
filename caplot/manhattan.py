import importlib.resources as resources
from pprint import pformat

import ipywidgets as widgets
import numpy as np
import pandas as pd
import requests
import yaml
from bokeh import palettes
from bokeh.models import (
    CategoricalColorMapper, ColumnDataSource, HoverTool,
)
from bokeh.plotting import figure
from munch import munchify
from stringcase import titlecase

from .interactiveplot import InteractivePlot

with resources.open_binary('caplot', 'refgen.yaml') as stream:
    refGenome = munchify(yaml.full_load(stream))


class Manhattan(InteractivePlot):
    """
    As the name suggests, `Manhattan` plots a manhattan chart for the specified `pvalue` column.

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
    genome: str
        The name of a genome reference set. Current supported values are `"GRCh37"` and `"GRCh38"`. Defaults to `"GRCh37"`.
    contig: str
        Name of a column present in the data.
    position:
        Name of a column present in the data.
    pvalue:
        Name of a column present in the data.
    mlog10: bool
        If the `pvalue` column is already transformed by -log10. Default is `False`.
    top: int
        Number of points on the scatter plot. Lower this value if you're having trouble viewing the plot. When
        choosing a subset, records with the largest `pvalue` (after transformation) are kept.
    width: int
        Width of the plot. Default is 800 pixels.
    height: int
        Height of the plot. Default is 600 pixels.
    coloringPalette: str
        Name of a color palette supported by Bokeh. Defaults to `"Category10"`.
    numColors: int
        Number of distinct colors used for coloring consecutive columns. Default is 2.
    pointSize: int or float
        Passed directly to Bokeh to specify the size of all points. Default is 5.
    yRange: tuple
        Specifies the range of the vertical axis. Defaults to 0 and 1.05 x the maximum value.
    """

    Palettes = 'Category10', 'Category20', 'Category20b', 'Category20c', 'Accent', 'GnBu', 'PRGn', 'Paired'
    VEPURL = 'https://rest.ensembl.org/vep/human/id'
    VEPLimit = 200
    GAP_RATIO = 0.01

    def __init__(self, source=None, loadQuery=None, filter=None, invertFilter=None, filterTemplate=None, highlight=None,
                 invertHighlight=None, highlightTemplate=None, minorAlpha=None, greyHighlight=None, hovers=None,
                 genome='GRCh37', contig=None, position=None, pvalue=None, mlog10=False, top=None, width=800,
                 height=600, coloringPalette='Category10', numColors=2, pointSize=5, yRange=None):
        super(Manhattan, self).__init__(source, loadQuery, filter, invertFilter, filterTemplate, highlight,
                                        invertHighlight, highlightTemplate, minorAlpha, greyHighlight, hovers)
        self._genome = None
        self._contig = None
        self._position = None
        self._pvalue = None
        self.mlog10 = mlog10
        self.top = top
        self.width = width
        self.height = height
        self._coloringPalette = None
        self.numColors = numColors
        self._rsidColumn = None
        self.pointSize = pointSize
        self.yRange = yRange
        self._annotationData = None
        # Initializations
        if genome is not None:
            self.genome = genome
        if contig is not None:
            self.contig = contig
        if position is not None:
            self.position = position
        if pvalue is not None:
            self.pvalue = pvalue
        if coloringPalette is not None:
            self.coloringPalette = coloringPalette

    @property
    def genome(self):
        """
        str: The name of a genome reference set. Current supported values are `"GRCh37"` and `"GRCh38"`.
        """
        return self._genome

    @genome.setter
    def genome(self, value):
        assert value in refGenome.keys(), f'Acceptable "genome" values are {", ".join(refGenome.keys())}.'
        self._genome = value

    @property
    def refGenome(self):
        """
        dict: Reference data for the specified `genome`.
        """
        return refGenome[self.genome]

    @property
    def contig(self):
        """
        str: Name of a column.
        """
        return self._contig

    @contig.setter
    def contig(self, value):
        if self.source is not None:
            assert value in self.source.columns, f'Could not find a column named "{value}" in data.'
        self._contig = value

    @property
    def position(self):
        """
        str: Name of a column.
        """
        return self._position

    @position.setter
    def position(self, value):
        if self.source is not None:
            assert value in self.source.columns, f'Could not find a column named "{value}" in data.'
        self._position = value

    @property
    def pvalue(self):
        """
        str: Name of a column.
        """
        return self._pvalue

    @pvalue.setter
    def pvalue(self, value):
        if self.source is not None:
            assert value in self.source.columns, f'Could not find a column named "{value}" in data.'
        self._pvalue = value
        
    @property
    def coloringPalette(self):
        """
        str: Name of a color palette supported by Bokeh.
        """
        return self._coloringPalette

    @property
    def rsidColumn(self):
        """
        str: Name of a column.

        When set, it will contact "ensembl.org" and store annotations for the top 200 values. This process can last up to a few minutes.
        """
        return self._rsidColumn

    @rsidColumn.setter
    def rsidColumn(self, value):
        if self.source is not None:
            assert value in self.source.columns, f'Could not find a column named "{value}" in data.'
        self._rsidColumn = value
        # Get the filtered and highlighted data
        data = self._ProcessedData()
        # data = data[data['__alpha__'] == 1]
        # Take the top `VEPLimit` most significant variants
        data = data.sort_values(by=self.pvalue)
        data = data.tail(self.VEPLimit) if self.mlog10 else data.head(self.VEPLimit)
        uniqueIDs = data[self._rsidColumn].unique().tolist()
        # VEP API call
        response = requests.post(self.VEPURL, json={'ids': uniqueIDs})
        if not response.ok:
            response.raise_for_status()
        # Convert VEP data into pandas dataframe
        df = pd.DataFrame(response.json())
        for column in df.columns:
            if pd.api.types.is_object_dtype(df[column].dtype):
                example = df[column].loc[~df[column].isnull()].iloc[0]
                if isinstance(example, list) or isinstance(example, dict):
                    df[column] = df[column].apply(lambda element: pformat(element))
        df.columns = [f'__anon__{column}__' for column in df.columns]
        self._annotationData = df

    @coloringPalette.setter
    def coloringPalette(self, value):
        assert value in self.Palettes, f'Acceptable color palettes values are {", ".join(self.Palettes)}.'
        self._coloringPalette = value

    def Widgets(self):
        if self.source is not None:
            localWidgets = {
                'contig': widgets.Dropdown(options=self.source.columns, value=self.contig),
                'position': widgets.Dropdown(options=self.source.columns, value=self.position),
                'pvalue': widgets.Dropdown(options=self.source.columns, value=self.pvalue),
            }
        else:
            localWidgets = {
                'contig': widgets.Text(placeholder='Column Name'),
                'position': widgets.Text(placeholder='Column Name'),
                'pvalue': widgets.Text(placeholder='Column Name'),
            }
        return {
            'genome': widgets.Dropdown(options=refGenome.keys(), value=self.genome),
            **localWidgets,
            'coloringPalette': widgets.Dropdown(options=self.Palettes, value='Category10'),
            'numColors': widgets.IntSlider(value=2, min=1, max=22, step=1),
        }

    def Generate(self, outputBackend='canvas', hideBokehLogo=True):
        data = self._ProcessedData()
        if self.top is not None:
            data = data.sort_values(by=self.pvalue)
            data = data.tail(self.top) if self.mlog10 else data.head(self.top)
        if self.mlog10:
            yColumnName = self.pvalue
        else:
            data['__pvalue__'] = -np.log10(data[self.pvalue])
            yColumnName = '__pvalue__'
        data[self.contig] = data[self.contig].astype(str)
        data['__location__'] = data[self.contig].replace(self.refGenome['cumulativeLengths']) + data[self.position]
        try:
            palette = getattr(palettes, self.coloringPalette)
            palette = next(value for key, value in palette.items() if key > self.numColors)
        except StopIteration:
            raise RuntimeError(f'The chosen color palette does not have {self.numColors} distinct colors.')
        else:
            palette = [palette[index % self.numColors] for index, label in enumerate(self.refGenome['contigOrder'])]
            colorMapper = CategoricalColorMapper(palette=palette, factors=self.refGenome['contigOrder'])
            color = {'field': self.contig, 'transform': colorMapper}
        tooltips = []
        if self.hovers:
            tooltips.extend((label, f'@{{{columnName}}}') for label, columnName in self.hovers.items())
        if self.rsidColumn:
            data = data.merge(right=self._annotationData, left_on=self.rsidColumn, right_on='__anon__id__', how='left')
            tooltips.extend((titlecase(columnName[8:-2]), f'@{{{columnName}}}') for columnName in self._annotationData.columns)
        # Calculate xRange to add gaps on either side
        lastContig = self.refGenome.contigOrder[-1]
        xLen = self.refGenome.cumulativeLengths[lastContig] + self.refGenome.lengths[lastContig]
        xGap = int(xLen * self.GAP_RATIO)
        xRange = (0-xGap, xLen+xGap)
        defaultYRange = (0, 1.05 * data[yColumnName].max())
        plot = figure(width=self.width, height=self.height, x_range=xRange, y_range=self.yRange or defaultYRange,
                      x_axis_label='Chromosome', y_axis_label='-log10(p-value)')
        plot.output_backend = outputBackend
        plot.toolbar.logo = None
        for highlighted in (False, True):
            source = ColumnDataSource(data[data['__highlighted__'] == highlighted])
            plot.circle(source=source, x='__location__', y=yColumnName, size=self.pointSize, line_color=None,
                        color='grey' if self.greyHighlight and not highlighted else color,
                        alpha=1 if highlighted else self.minorAlpha)
        if tooltips:
            plot.add_tools(HoverTool(tooltips=tooltips))
        plot.xaxis.ticker = [value for key, value in self.refGenome['tickPosition'].items()]
        plot.xaxis.major_label_overrides = {value: key for key, value in self.refGenome['tickPosition'].items()}
        plot.xgrid.visible = False
        plot.ygrid.visible = False
        return plot

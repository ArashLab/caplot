import abc
import json
import os.path
import pickle
import re
import urllib.parse
from contextlib import contextmanager
from warnings import warn

import ipywidgets as widgets
import pandas as pd
from IPython.display import display
from bokeh.core.validation import silence
from bokeh.io import reset_output
from bokeh.io.export import get_screenshot_as_png, export_svg
from bokeh.models.plots import Plot
from bokeh.plotting import output_file, show, save
from pandasql import sqldf
from sqlalchemy import create_engine
from stringcase import titlecase


class InteractivePlot(abc.ABC):
    """
    `InteractivePlot` serves as the base class for all charts in CAPlot. The class handles all functionalities
    related to I/O, while also providing an interface for filtering through data and highlighting certain points,
    which is common to all types of charts.

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
    """

    SupportedExtensions = ('.png', '.jpeg', '.svg', '.pdf', '.html', '.caplot')

    def __init__(self, source=None, loadQuery=None, filter=None, invertFilter=None, filterTemplate=None, highlight=None,
                 invertHighlight=None, highlightTemplate=None, minorAlpha=None, greyHighlight=False, hovers=None):
        self._data = None
        self._filter = None
        self._invertFilter = None
        self._filterTemplate = None
        self._filtered = None
        self._highlight = None
        self._invertHighlight = None
        self._highlightTemplate = None
        self._highlighted = None
        self._minorAlpha = 0.5
        self.greyHighlight = greyHighlight
        self._hovers = dict()
        self._safeWarnings = set()
        # Initializations
        if source is not None:
            self.source = source if loadQuery is None else (source, loadQuery)
            assert filter is None or invertFilter is None, 'You can define either "filter" or "invertFilter".'
            assert highlight is None or invertHighlight is None, 'You can define either "highlight" or "invertHighlight".'
            if filter is not None:
                self.filter = filter
            if invertFilter:
                self.invertFilter = invertFilter
            if highlight is not None:
                self.highlight = highlight
            if invertHighlight is not None:
                self.invertFilter = invertFilter
        if filterTemplate is not None:
            self.filterTemplate = filterTemplate
        if highlightTemplate is not None:
            self.highlightTemplate = highlightTemplate
        if hovers is not None:
            self.hovers = hovers
        if minorAlpha is not None:
            self.minorAlpha = minorAlpha

    @staticmethod
    def Subset(sqlQuery, tables):
        """Uses `sqldf` to execute a query on the internal DataFrame.

        Parameters
        ----------
        sqlQuery: str
            Desired query.
        tables: dict
            Tables accessible in the query.

        Returns
        -------
        df: pd.DataFrame
            The resulting dataframe.
        """
        return sqldf(sqlQuery, tables)

    @property
    def source(self):
        """
        pd.DataFrame: Internal data the plot is working with.

        You can assign a path to a file Pandas can read from, the URL for a SQL database, or a literal DataFrame. You
        can also pass a query as the second element (in a tuple) which will serve as the `loadQuery`, limiting the data
        that is kept in memory.
        """
        return self._data

    @source.setter
    def source(self, value):
        source, loadQuery = value if isinstance(value, tuple) else (value, None)
        if isinstance(source, pd.DataFrame):
            self._data = source
        elif isinstance(source, str):
            parsed = urllib.parse.urlparse(source)
            # The following list is based on https://docs.sqlalchemy.org/en/14/dialects/#included-dialects.
            supported_dialects = ('postgresql', 'postgres', 'mysql', 'mariadb', 'sqlite', 'oracle:thin', 'sqlserver')
            if parsed.scheme.replace('jdbc:', '') in supported_dialects:
                assert loadQuery is not None, 'You must specify `sqlQuery` when connecting to a database.'
                engine = create_engine(source)
                with engine.connect() as connection:
                    self._data = pd.read_sql(loadQuery, connection)
            else:
                (remainder, extension), compression = os.path.splitext(source), None
                if extension in ('.gz', '.bgz', '.bz2', '.zip', '.xz'):
                    (remainder, extension), compression = os.path.splitext(remainder), extension
                reading_methods = {
                    '.csv': pd.read_csv,
                    '.tsv': pd.read_table,
                    '.parquet': pd.read_parquet,
                }
                assert extension in reading_methods, f'Unsupported extension "{extension}".'
                self._data = reading_methods[extension](source)
                if loadQuery is not None:
                    self._data = self.Subset(loadQuery, {'data': self._data.reset_index()}).set_index('index')
        else:
            msg = 'The source can be a DataFrame, a path to a file that Pandas can read, or the URL for a SQL database.'
            raise RuntimeError(msg)  # Custom exception needed?

    @property
    def filter(self):
        """
        str: An optional SQL query to specify which records must be kept in.

        Filtration occurs at the time of assignment.
        """
        return self._filter

    @filter.setter
    def filter(self, query):
        self._filter, self._invertFilter = query, None
        self._filtered = self.Subset(query, {'data': self._data.reset_index()}).set_index('index').index

    @property
    def invertFilter(self):
        """
        str: An optional SQL query to specify which records must be left out.

        Filtration occurs at the time of assignment.
        """
        return self._invertFilter

    @invertFilter.setter
    def invertFilter(self, query):
        self._filter, self._invertFilter = None, query
        self._filtered = self._data.drop(
            self.Subset(query, {'data': self._data.reset_index()}).set_index('index').index).index
    
    @property
    def filterTemplate(self):
        return self._filterTemplate
    
    @filterTemplate.setter
    def filterTemplate(self, value):
        self._filterTemplate = value

    @property
    def highlight(self):
        """
        str: An optional SQL query to specify which records must be highlighted.

        Filtration occurs at the time of assignment.
        """
        return self._highlight

    @highlight.setter
    def highlight(self, query):
        self._highlight, self._invertHighlight = query, None
        self._highlighted = self.Subset(query, {'data': self._data.reset_index()}).set_index('index').index

    @property
    def invertHighlight(self):
        """
        str: An optional SQL query to specify which records must not be highlighted, while others are.

        Filtration occurs at the time of assignment.
        """
        return self._invertHighlight

    @invertHighlight.setter
    def invertHighlight(self, query):
        self._highlight, self._invertHighlight = None, query
        self._highlighted = self._data.drop(
            self.Subset(query, {'data': self._data.reset_index()}).set_index('index').index).index

    @property
    def highlightTemplate(self):
        return self._highlightTemplate

    @highlightTemplate.setter
    def highlightTemplate(self, value):
        self._highlightTemplate = value

    @property
    def minorAlpha(self):
        return self._minorAlpha

    @minorAlpha.setter
    def minorAlpha(self, value):
        assert 0 <= value <= 1, 'The alpha must be in the [0,1] range.'
        self._minorAlpha = value

    def _ProcessedData(self):
        """
        Returns
        -------
        pd.DataFrame: Filtered data, with an extra column, `__alpha__`, which is used to highlight certain records.
        """
        df = (self._data.loc[self._filtered] if self._filtered is not None else self._data).copy()
        df['__highlighted__'] = df.index.isin(self._highlighted) if self._highlighted is not None else True
        return df

    @property
    def hovers(self):
        """
        dict: A mapping of arbitrary labels to certain columns in the data source.

        On assignment, this property expects either a dict, or a string which will be parsed as a JSON object.
        """
        if self._hovers is None:
            self._hovers = dict()
        return self._hovers

    @hovers.setter
    def hovers(self, mapping):
        self._hovers = mapping if isinstance(mapping, dict) else json.loads(mapping)

    def _WidgetsFor(self, queryTemplate):
        mapping = dict()
        for variableDescriptor in re.findall(r'\{[^\{\}]*\}', queryTemplate):
            label, widget, *args = re.split(': ?', variableDescriptor[1:-1])
            if widget == 'intSlider':
                minimum, maximum, step, default = args
                minimum, maximum, step, default = int(minimum), int(maximum), int(step), int(default)
                widget = widgets.IntSlider(value=default, min=minimum, max=maximum, step=step)
            elif widget == 'floatSlider':
                minimum, maximum, step, default = args
                minimum, maximum, step, default = float(minimum), float(maximum), float(step), float(default)
                widget = widgets.FloatSlider(value=default, min=minimum, max=maximum, step=step)
            elif widget == 'intBox':
                default, = args
                default = int(default)
                widget = widgets.IntText(value=default)
            elif widget == 'floatBox':
                default, = args
                default = float(default)
                widget = widgets.FloatText(value=default)
            elif widget == 'textBox':
                default, = args
                widget = widgets.Text(value=default)
            elif widget in ('singleChoice', 'multipleChoice'):
                options, default = args
                options, default = json.loads(options), json.loads(default)
                options = options if isinstance(options, list) else self.source[options].unique().tolist()
                widget = widgets.Dropdown(options=options, value=default) \
                    if widget == 'SingleChoice' else widgets.SelectMultiple(options=options, value=[default])
            mapping[label] = widget
        return mapping

    @staticmethod
    def _Filled(queryTemplate, values):
        for variableDescriptor in re.findall(r'\{.*\}', queryTemplate):
            label, *rest = re.split(': ?', variableDescriptor[1:-1])
            v = values[label]
            v = v[0] if isinstance(v, tuple) else v
            v = f'"{v}"' if isinstance(v, str) else v
            queryTemplate = queryTemplate.replace(variableDescriptor, str(v))
        return queryTemplate

    @abc.abstractmethod
    def Widgets(self):
        """
        The method returns all the fields needed by the subclass, mapping their labels to their actual widgets.

        This method is meant to be overridden by the subclasses.

        Returns
        -------
        widgets: dict
            Contains the widgets as its values, and the name of their holding variables as keys.
        """
        pass

    @abc.abstractmethod
    def Generate(self, outputBackend='canvas', hideBokehLogo=False):
        """
        The method generates a Bokeh plot and returns it.

        This method is meant to be heart of subclasses, containing their primary functionalities.

        Parameters
        ----------
        outputBackend: str
            Specifies the target output backend for Bokeh. Defaults to `canvas`.
        hideBokehLogo: bool
            When set, Bokeh's logo will be removed from the toolbar. Default is `False`.

        Returns
        -------
        plot: Plot
            Generated plot, for further manipulation or displaying.
        """
        pass

    @contextmanager
    def _SafeWarningsSilenced(self):
        """
        Context manager that silences all Bokeh warnings that are deemed to be safe.
        """
        for error_code in self._safeWarnings:
            silence(error_code, True)
        try:
            yield self
        finally:
            for error_code in self._safeWarnings:
                silence(error_code, False)

    def Show(self):
        """
        The method displays the chart, with the latest changes. Some charts might cause predetermined warnings which are
        safe to ignore. The method will silence these warnings temporarily.
        """
        plot = self.Generate()
        with self._SafeWarningsSilenced():
            show(plot)

    def _SaveAs(self, prefix, extension):
        """
        The method is a utility function for exporting the plot to a file with a certain file extension format.

        The method uses Bokeh's builtin functions for static outputs, and Pickle, for `.caplot` which encapsulates the
        data as well.

        Parameters
        ----------
        plot: list or Plot
            Bokeh-generated plot or grid-plot.
        prefix: str
            Full path to the desired output file, minus its extension.
        extension: str
            The file extension format.
        """
        filepath = prefix + extension
        if extension == '.caplot':
            with open(filepath, 'wb') as stream:
                pickle.dump(self, stream)
        elif extension in ('.png', '.jpeg'):
            plot = self.Generate(hideBokehLogo=True)
            im = get_screenshot_as_png(plot)
            im = im.convert('RGB')
            im.save(filepath)
        elif extension in ('.svg', '.pdf'):
            plot = self.Generate(hideBokehLogo=True, outputBackend='svg')
            export_svg(plot, filename=filepath)
            if extension == '.pdf':
                try:
                    from svglib.svglib import svg2rlg
                    from reportlab.graphics import renderPDF
                except ImportError:
                    raise RuntimeError('You need to install "svglib" and "reportlab" for PDF exports.')
                else:
                    drawing = svg2rlg(filepath)
                    renderPDF.drawToFile(drawing, filepath)
        elif extension == '.html':
            plot = self.Generate()
            reset_output()
            output_file(filepath)
            save(plot, filepath)
            reset_output()
            warn('To avoid further issues, output states have been reset. Please invoke output_notebook() again if you are working in a notebook.')

    def SaveAs(self, filepath):
        """
        The method stores the plot with the latest changes as the specified file. The method of exporting is inferred
        based on the file extension format of `filepath`. If `filepath` doesn't end in an extension, it is assumed that
        all possible outputs must be generated.

        Parameters
        ----------
        filepath: str
            Relative or absolute path for exporting. Supported file extension formats are `pdf`, `html`, `png`, `jpeg`.

        Raises
        ------
        AssertionError
            If the target file extension format is not supported.
        """
        prefix, extension = os.path.splitext(filepath)
        assert extension in self.SupportedExtensions, 'Unsupported file extension format.'
        for extension in ([extension] if extension else self.SupportedExtensions):
            with self._SafeWarningsSilenced():
                self._SaveAs(prefix, extension)

    @staticmethod
    def _GenerateGrid(mapping, keepCasing=False):
        grid = widgets.GridspecLayout(len(mapping), 2)
        for index, (label, widget) in enumerate(mapping.items()):
            grid[index, 0], grid[index, 1] = widgets.Label(label if keepCasing else titlecase(label)), widget
        return grid

    def ShowWithForm(self):
        """
        The method is intended to be used in notebooks. It will list all widgets defined for the plot, along with a
        button that when triggered, will attempt to assign the widgets' values to the instance and then plot the result.
        """
        # Interactive Plot Widgets
        filterWidgets = self._WidgetsFor(self.filterTemplate) if self.filterTemplate else \
            {'filterQuery': widgets.Text(value=self.filter, placeholder='SQL Query')}
        filterForm = self._GenerateGrid(filterWidgets)
        highlightWidgets = self._WidgetsFor(self.highlightTemplate) if self.highlightTemplate else \
            {'highlightQuery': widgets.Text(value=self.highlight, placeholder='SQL Query')}
        highlightForm = self._GenerateGrid(highlightWidgets)
        hoverWidgets = {'hovers': widgets.Text(value=json.dumps(self.hovers), placeholder='JSON Object')}
        hoverForm = self._GenerateGrid(hoverWidgets)
        # Subclass Widgets
        subclassWidgets = self.Widgets()
        subclassForm = self._GenerateGrid(subclassWidgets)
        # Defining the Output Slot and the "Show" Button
        output = widgets.Output()
        button = widgets.Button(description='Show')

        # The Callback Function Triggered When the Button is Clicked
        def callback(button):
            button.description = '...'  # To indicate that the process is being performed.
            button.disabled = True
            output.clear_output()
            with output:
                # Specifying the Filtering Query
                if self.filterTemplate is not None:
                    values = {label: widget.value for label, widget in filterWidgets.items()}
                    filterQuery = self._Filled(self.filterTemplate, values)
                else:
                    filterQuery = filterWidgets['filterQuery'].value
                if filterQuery:
                    self.filter = filterQuery
                # Specifying the Highlighting Query
                if self.highlightTemplate is not None:
                    values = {label: widget.value for label, widget in highlightWidgets.items()}
                    highlightQuery = self._Filled(self.highlightTemplate, values)
                else:
                    highlightQuery = highlightWidgets['highlightQuery'].value
                if highlightQuery:
                    self.highlight = highlightQuery
                # Specifying the Hover Setting
                hoverMapping = hoverWidgets['hovers'].value
                if hoverMapping:
                    self.hovers = hoverMapping
                # Assigning the Properties in the Subclass
                for attr, widget in subclassWidgets.items():
                    if widget.value not in (None, ''):  # Can't rule out all falsy values. Might limit this further.
                        setattr(self, attr, widget.value)
                self.Show()
            button.disabled = False
            button.description = 'Show'

        # Binding the Callback Function to the Button
        button.on_click(callback)
        # Displaying All Components
        ui = widgets.VBox([filterForm, highlightForm, hoverForm, subclassForm, button, output])
        display(ui)

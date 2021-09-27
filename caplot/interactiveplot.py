import abc
import json
import os.path
import urllib.parse

import ipywidgets as widgets
import pandas as pd
from IPython.display import display
from bokeh.core.validation import silence
from bokeh.io.export import get_screenshot_as_png
from bokeh.plotting import output_file, show
from pandasql import sqldf
from sqlalchemy import create_engine
from stringcase import titlecase


class InteractivePlot(abc.ABC):

    def __init__(self, source=None, loadQuery=None, filter=None, invertFilter=None, highlight=None, invertHighlight=None, hovers=None):
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
        highlight: str
            An optional SQL query to specify which records must be highlighted.
        invertHighlight: str
            An optional SQL query to specify which records must not be highlighted, while the rest are.
        hovers: dict
            A mapping of arbitrary labels to certain columns in the data source.
        """
        self._data = None
        self._filter = None
        self._invertFilter = None
        self._filtered = None
        self._highlight = None
        self._invertHighlight = None
        self._highlighted = None
        self._hovers = None
        self._widgets = None
        self._safeWarnings = set()
        # Initializations
        if source is not None:
            self.data = source if loadQuery is None else (source, loadQuery)
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
            if hovers is not None:
                self.hovers = hovers

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
    def data(self):
        """
        pd.DataFrame: Internal data the plot is working with.

        You can assign a path to a file Pandas can read from, the URL for a SQL database, or a literal DataFrame. You
        can also pass a query as the second element (in a tuple) which will serve as the `loadQuery`, limiting the data
        that is kept in memory.
        """
        return self._data

    @data.setter
    def data(self, value):
        source, sqlQuery = value if isinstance(value, tuple) else (value, None)
        if isinstance(source, pd.DataFrame):
            self._data = source
        elif isinstance(source, str):
            parsed = urllib.parse.urlparse(source)
            # The following list is based on https://docs.sqlalchemy.org/en/14/dialects/#included-dialects.
            supported_dialects = ('postgresql', 'postgres', 'mysql', 'mariadb', 'sqlite', 'oracle:thin', 'sqlserver')
            if parsed.scheme.replace('jdbc:', '') in supported_dialects:
                assert sqlQuery is not None, 'You must specify `sqlQuery` when connecting to a database.'
                engine = create_engine(source)
                with engine.connect() as connection:
                    self._data = pd.read_sql(sqlQuery, connection)
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
                if sqlQuery is not None:
                    self._data = self.Subset(sqlQuery, self._data)
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
        self._filtered = self._data.drop(self.Subset(query, {'data': self._data.reset_index()}).set_index('index').index).index

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
        self._highlighted = self._data.drop(self.Subset(query, {'data': self._data.reset_index()}).set_index('index').index).index

    def _ProcessedData(self):
        """
        Returns
        -------
        pd.DataFrame: Filtered data, with an extra column, `__alpha__`, which is used to highlight certain records.
        """
        df = (self._data.loc[self._filtered] if self._filtered is not None else self._data).copy()
        df['__alpha__'] = (df.index.isin(self._highlighted).astype('int') * .5 + .5) if self._highlighted is not None else 1
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

    def Widgets(self):
        """
        The method must be overridden to implement the functionality related to storing the settings. The parent method
        implements a couple of widgets, namely, the filtering query and the highlighting query.

        Returns
        -------
        widgets: dict
            Contains the widgets as its values, and the name of their holding variables as keys.
        """
        return {
            'filter': widgets.Text(value=self.filter, placeholder='SQL Query'),
            'highlight': widgets.Text(value=self.highlight, placeholder='SQL Query'),
            'hovers': widgets.Text(value=json.dumps(self.hovers), placeholder='JSON Object'),
        }

    @abc.abstractmethod
    def Generate(self):
        """
        The method generates a Bokeh plot and returns it.

        This method is meant to be heart of subclasses, containing their primary functionalities.
        """
        pass

    def Show(self):
        """
        The method displays the chart, with the latest changes. Some charts might cause predetermined warnings which are
        safe to ignore. The method will silence these warnings temporarily.
        """
        plot = self.Generate()
        for error_code in self._safeWarnings:
            silence(error_code, True)
        show(plot)
        for error_code in self._safeWarnings:
            silence(error_code, False)

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
        plot = self.Generate()
        prefix, extension = os.path.splitext(filepath)
        assert extension in ('.png', '.jpeg', '.pdf', '.html', ''), 'Unsupported'
        if extension in ('.png', '.jpeg', '.pdf', ''):
            im = get_screenshot_as_png(plot)
            im = im.convert('RGB')
            im.save(filepath)
        elif extension in ('.html', ''):
            output_file(filename=filepath, title='Plot Generated by AB Plot')

    def SetupAndShow(self, **kwargs):
        """
        The method is intended to be used with `ipywidgets.interactive_output`. As its arguments, it receives **kwargs
        mapping instance attribute names to their desired values. It will assign them before attempting to display the
        chart.
        """
        for attr, value in kwargs.items():
            setattr(self, attr, value)
        self.Show()

    def ShowWithForm(self):
        """
        Displays a form for configuring the plot. Changes in the widgets will immediately trigger and take effect in the
        chart.
        """
        self._widgets = self.Widgets()
        specified_config = {name: widget for name, widget in self._widgets.items()}
        out = widgets.interactive_output(self.SetupAndShow, specified_config)
        ui = widgets.VBox([widgets.HBox([widgets.Label(titlecase(name)), widget]) for name, widget in self._widgets.items()])
        display(ui, out)

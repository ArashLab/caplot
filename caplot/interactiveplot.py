import abc
import os.path
import urllib.parse

import ipywidgets as widgets
import pandas as pd
from IPython.display import display
from bokeh.io.export import get_screenshot_as_png
from bokeh.plotting import output_file, show
from pandasql import sqldf
from sqlalchemy import create_engine


class InteractivePlot(abc.ABC):

    def __init__(self, source=None, loadQuery=None, filterQuery=None, keep=True, highlightQuery=None, highlight=True, hovers=None):
        self._data = None
        self._filtered = None
        self._highlighted = None
        self._widgets = None
        self._hovers = None
        self._config = None

        if source:
            self.LoadData(source, loadQuery)
            self.Filter(filterQuery, keep)
            self.Highlight(highlightQuery, highlight)
            self.Hover(hovers)

    def LoadData(self, source, sqlQuery=None):
        """Imports data as a Pandas DataFrame.

        Parameters
        ----------
        source: str, pd.DataFrame
            Could point to a SQL database, a tabular file or a Pandas DataFrame.
        sqlQuery
            If the source is a SQL database, will be used to retrieve relevant data.
        """
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

    def Filter(self, sqlQuery, keep=True):
        """Filters through the data, based on the passed query.

        Parameters
        ----------
        sqlQuery: str
            Desired query.
        keep: bool
            Whether the selected rows are to be included or excluded when plotting the chart.
        """
        # `sqldf` seems to drop the index. Therefore, we add it as a column and then convert it back.
        rows = self.Subset(sqlQuery, {'data': self._data.reset_index()}).set_index('index')
        self._filtered = rows.index if keep else self._data.drop(rows.index).index

    def Highlight(self, sqlQuery, highlight=True):
        """Highlights the rows specified by the query.

        Parameters
        ----------
        sqlQuery: str
            Desired query.
        highlight: bool
            Whether the selected rows are to be highlighted or should the rest be, when plotting the chart.
        """
        rows = self.Subset(sqlQuery, {'data': self._data.reset_index()}).set_index('index')
        self._highlighted = rows.index if highlight else self._data.drop(rows.index).index

    def Hover(self, hovers):
        """Sets the internal `_hovers` dictionary. Different charts utilize it differently.

        Parameters
        ----------
        hovers: dict
            Descriptions shown when certain objects are hovered.
        """
        self._hovers = hovers

    def AddHover(self, hovers):
        self._hovers.update(hovers)
        pass

    def DropHover(self, hovers):
        ### take a list of [lable]
        pass


    @abc.abstractmethod
    def Configure(self, **kwargs):
        """
        The method must be overridden to implement the functionality related to storing the settings. Replace the
        `**kwargs` with appropriate ones.
        """
        pass

    @staticmethod
    def Widgets():
        """
        The method must be overridden to implement the functionality related to storing the settings. The parent method
        implements a couple of widgets, namely, the filtering query and the highlighting query.

        Returns
        -------
        widgets: dict
            Contains the widgets as its values, and the name of their holding variables as keys.
        """
        return {
            'filterQuery': widgets.Text(value='select * from data'),
            'highlightQuery': widgets.Text(value='select * from data'),
        }

    @abc.abstractmethod
    def Generate(self):
        """
        The method must be overridden to implement the functionality related to populating a Bokeh `Figure` with the
        necessary glyphs. To do so, the settings stored via `.Configure()` must be taken into account.
        """
        pass

    def Show(self):
        """
        The method simply calls `.Generate()` and shows the resulting chart.
        """
        show(self.Generate())

    def SaveAs(self, filepath):
        """Stores the plot with the latest changes as the specified file. The method of exporting is inferred based on
        the file extension format of `filepath`. If `filepath` doesn't end in an extension, it is assumed that all
        possible outputs must be generated.

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

    def SetupAndShow(self, filterQuery=None, highlightQuery=None, **kwargs):
        """Sets up the plot and shows it. The method is designed to work with `widgets.interactive_output`.

        Under normal circumstances, there's no need to override this function. But you certainly can do so.

        Parameters
        ----------
        filterQuery: str
            A query to filter through the data.
        highlightQuery: str
            A query to highlight certain datapoints.
        """
        if filterQuery is not None:
            self.Filter(filterQuery)
        if highlightQuery is not None:
            self.Highlight(highlightQuery)
        self.Configure(**kwargs)
        self.Show()

    def ShowWithForm(self):
        """
        Displays a form for configuring the plot. Changes in the widgets will immediately trigger and take effect in the
        chart.
        """
        self._widgets = self.Widgets()
        specified_config = {name: widget for name, widget in self._widgets.items()}
        out = widgets.interactive_output(self.SetupAndShow, specified_config)
        ui = widgets.VBox([widgets.HBox([widgets.Label(name), widget]) for name, widget in self._widgets.items()])
        display(ui, out)

from .interactiveplot import InteractivePlot


class Manhattan(InteractivePlot):

    def Generate(self):
        """
        The method must be overridden to implement the functionality related to populating a Bokeh `Figure` with the
        necessary glyphs. To do so, the settings stored via `.Configure()` must be taken into account.
        """
        pass

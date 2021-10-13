How It Works
============

To create a plot, you need to instantiate its corresponding class.
For example, to create a PCA plot

.. code:: python

    import caplot
    plot = caplot.PCA()

Now you can configure your plot by setting its attribute.
For example, the following code using data from a CSV file and set the filter and highlight query
The data must include all the columns necessary to create the plot as
well as columns you may use for the hover fields as well as other
purposes.

.. code:: python

    plot.source = 'data.csv'
    plot.filter = 'SELECT * FROM data WHERE "quality">0.95'
    plot.higlight = 'SELECT * FROM data WHERE "isImportant"=True AND "quality">0.99'

Some attributes (like those above) are implemented in the
`InteractivePlot` class and are common between
all plots.
However, each plot class has its attributes too. For example:

.. code:: python

    plot = caplot.PCA()
    plot.source = 'samples.csv'
    plot.coloringColumn = 'super-population'

.. code:: python

    plot = caplot.Manhattan()
    plot.source = 'variants.csv'
    plot.pvalue = 'T2D-wald-test-pval'

You can also set these attributes in the initialisation function

.. code:: python

    plot = caplot.Manhattan(data='variants.csv')

Once you configure your plot you can show or save it

.. code:: python

    plot.Show()
    plot.SaveAs('figure.png')
    plot.SaveAs('vector.svg')

If you need to access the bokeh plot object to perform low level
customisation, you can call the `Generate` method.

.. code:: python

    p = plot.Generate()
    # p is the bokeh plot object

You can also show your plot along with the HTML form. The form lets you modify the plot's attributes and refresh the plot.
This is helpful to explore data, especially when you share data with
someone who has no coding experience.

.. code:: python

    plot.ShowWithForm()
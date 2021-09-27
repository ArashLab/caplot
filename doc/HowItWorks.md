# How it works

In order to create a plot you need to instatiate its coresponding class.
For example, to create a PCA plot

```python
import caplot
plot = caplot.PCA()
```

Now you can configure your plot by setting its attribute.
For example, the following code assing data from a CSV file and set the filter and highligh query
The data must include all the columns necesary to create the plot as well as columns you may use for the hover fields as well as other purposes.

```python
plot.data = 'data.csv'
plot.filter = 'SELECT * FROM data WHERE "quality">0.95'
plot.higlight = 'SELECT * FROM data WHERE "isImportant"=True AND "quality">0.99'
```

Some atribute (like those above) are implmented in the [InteractivePlot](InteractivePlot.md) class and are common between all plots.
However each plot class has its own attributes too. For example:

```python
plot = caplot.PCA()
plot.data = 'samples.csv'
plot.coloringColumn= 'super-population'
```

```python
plot = caplot.Manhattan()
plot.data = 'variants.csv'
plot.pvalue= 'T2D-wald-test-pval'
```

You can also set these atributes in the initialisation function

```python
plot = caplot.Manhattan(data='variants.csv')
```

Once you configure your plot you can show or save it

```python
plot.Show()
plot.SaveAs('figure.png')
plot.SaveAs('vector.svg')
```

If you need to access the bokeh plot object to perfomr low level customisation, you can call the `Generate` method.

```python
p = plot.Generate()
# p is the bokeh plot object
```

You can also show your plot along with the html form. The form let's you to modify plot's atributes and refresh the plot.
This is helpful to explore data, especially when you share data with someone who has no coding experience.

```python
plot.ShowWithForm()
```
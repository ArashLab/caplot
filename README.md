# Cohort Analysis Plot (caplot)

`caplot` is built to facilitate the visualisation of cohort analysis results.
caplot is built on top of [bokeh](https://bokeh.org/) and utilise all its interactive features.
caplot offers the following feature:
- Easily connect to various data sources including SQL, tabular files and pandas data frame.
- Explore data and customising the plot without coding and through a web form.
- Filter and highlight data using SQL queries as well as user-defined forms.
- Connect to variant annotation database and extract annotation for significant variants in manhattan plot. 

Currently, caplot offer PCA and Manhattan plot.
The examples folder include sample data as well as example Jupyter notebooks to show how these plots.
Looking at these examples is perhaps the easiest way to learn about caplot and all its features.

To learn more about provided sample data see [SampleData.md](examples/data/SampleData.md)
[pca.ipynb](exmpales/pca.ipynb) is our PCA example notebook.
[manhattan.ipynb](exmpales/manhattan.ipynb) is our Manhattan example notebook

## Installation

```bash
pip install caplot
```

In case you install caplot in the conda environemtn you may need to install requiered packages (and jupyter notebook) using conda.
Othere wise the `SaveAs` function may not work.
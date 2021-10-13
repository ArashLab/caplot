Experimental Features
=====================
Here we describe features that are partially implemented in this library and not tested exhaustively.

VEP API
-------
Annotating genomic variants is probably an important step in the analysis pipeline.
If you already annotate your data you can use nice features such as filtering and highlighting based on your annotation data.
If not, this library can help you to get it done.
Currently, the code is capable to load VEP annotation for the top `n` variants which are highlighted in the plot.
Note that the VEP API service is limited. We recommend choosing a small `n` like 10 to get the response quickly.
Currently, the annotation can be done using the rsid (or other ids supported by VEP API).
It is possible to annotate data using variant coordinates and alleles but this feature is not implemented yet.
To use this feature, write the highlighted query such that the region of your interests is highlighted.
Then assign the rsid column name.
Once the code is executed, annotation results will be available in an internal pandas data frame called `_annotationData`

Here is an example of how to do so:

.. code:: python

    import caplot

    plot = caplot.Manhattan()
    plot.source = 'data/variants.tsv.gz'    plot.contig = 'locus-contig'
    plot.position = 'locus-position'
    plot.pvalue = 'LogReg3-p_value'
    plot.highlight = 'SELECT * FROM data WHERE "qc-maf">0.1'

    plot.VEPLimit = 10 # number of top variants in the highlighted region to be annotated

    # This line of code may take a while to be executed as it executes the VEP API in the background
    plot.rsidColumn = 'rsid' # rsid is the column name in our data that contains variant ids

    plot._annotationData # display the data frame containing annotated data


The VEP API also allows loading extra annotation fields which will be implemented in the final version.
# 1000 Genomes Example Data
To test the functionality of the caplot we have prepared a small subset of [1000 Genomes](https://www.internationalgenome.org/) Dataset alogn with some [syntetic phenotype](https://github.com/bambrozio/bioinformatics/blob/master/utils/1kg_phenotype_mock_2019-11-08.tsv) including age, t2d (Type2Diabetes) and bmi (Body Mass Index).
To prepare smaple data we use [Hail v0.2](https://hail.is/) and [VEP web interface](https://grch37.ensembl.org/Homo_sapiens/Tools/VEP)
Using Hail, we subset 81207 variants randomly while keeping all the 2504 samples in the dataset.

- [samples.tsv.gz](samples.tsv.gz) contains all the sample information (2504 rows and 68 cols). Columns are as follow
  - s: sample id
  - pheno-: phenotypic information including subpopulation, superpopulation, age, t2d, bmi and isFemale
  - sample_qc-: quality-control metrics computed by hail.sample_qc
  - Peinciple Component Analysis (PCA)
    - pcaSS1-scores_: The first 3 principle component vectors. Computed from 1% variants randomely selected
    - pcaSS2-scores_: The first 10 principle component vectors. Computed from 10% variants randomely selected
    - pcaMAF-scores_: The first 10 principle component vectors. Computed from common variants with minor allele frequency above 1%
    - pca-scores_: The first 20 principle component vectors. Computed from all variants
- [variants.tsv.gz](variants.tsv.gz) contains all the variant information (81207 rows and 144 cols)
  - locus-contig: CHR in VCF
  - locus-position: POS in VCF
  - alleles: List of allele in a JSON string
  - REF: first allele in the alleles
  - ALT: second allele in the alleles
  - rsid
  - qual: From 1000 Genome VCF
  - filters: From 1000 Genome VCF
  - vep-: All the annotations produced by VEP (joined based on rsid)
  - variant_qc-: quality-control metrics computed by hail.variant_qc
  - maf: Minor Allele Frequency
  - LogReg: 3 logistic regression tests are performed on t2d phenotype
    - 1: lrt test with no covariate
    - 2: score test with age and isFemale as covariate
    - 3: wald test with age, isFemale and all 10 pcaMAF vectors as covariate
  - LinReg: 3 linear regression tests are performed on bmi phenotype
    - 1: with no covariate
    - 2: with age and isFemale as covariate
    - 3: with age, isFemale and all 10 pcaMAF vectors as covariate
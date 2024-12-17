# q2-asap

A [QIIME 2](https://qiime2.org) plugin [developed](https://develop.qiime2.org) by Nicole Sylvester (nsylvester@tgen.org). 🔌

## Installation instructions

### Install Prerequisites

[Miniconda](https://conda.io/miniconda.html) provides the `conda` environment and package manager, and is currently the only supported way to install QIIME 2.
Follow the instructions for downloading and installing Miniconda.

After installing Miniconda and opening a new terminal, make sure you're running the latest version of `conda`:

```bash
conda update conda
```

[q2-trimmers](https://github.com/TGenNorth/q2-trimmers) provides the trimmer options used by `q2-asap` 
[q2-nasp2-types](https://github.com/TGenNorth/q2-nasp2-types) provides custom semantic types and formats used by `q2-asap`
[q2-aligners](https://github.com/TGenNorth/q2-aligners) provides the aligner options used by `q2-asap`

###  Install development version of `q2-asap`

Next, you need to get into the top-level `q2-asap` directory.
If you already have this (e.g., because you just created the plugin), this may be as simple as running `cd q2-asap`.
If not, you'll need the `q2-asap` directory on your computer.
Since it's maintained in a GitHub repository, you can achieve this by [cloning the repository](https://docs.github.com/en/repositories/creating-and-managing-repositories/cloning-a-repository).
Once you have the directory on your computer, change (`cd`) into it.

If you're in a conda environment, deactivate it by running `conda deactivate`.


Then, run:

```shell
conda env create -n q2-asap-dev --file ./environments/q2-asap-qiime2-tiny-2024.5.yml
```

After this completes, activate the new environment you created by running:

```shell
conda activate q2-asap-dev
```

Finally, run:

```shell
pip install .
```

Install some q2-asap requirements manually like so
```shell
conda install pytest flake8
conda install git
conda install -c conda-forge versioneer
conda install -c bioconda bbmap
conda install -c bioconda bwa
conda install -c bioconda bowtie2
```

## Testing `q2-asap`

After completing the install steps above, confirm that everything is working as expected by running:

```shell
make test
```

You should get a report that tests were run, and you should see that all tests passed and none failed.
It's usually ok if some warnings are reported.

If all of the tests pass, you're ready to use the plugin.

You should be able to review the help text by running:

```shell
qiime ASAP --help
```

Have fun! 😎

## About

The `q2-asap` Python package was [created from template](https://develop.qiime2.org/en/latest/plugins/tutorials/create-from-template.html).
To learn more about `q2-asap`, refer to the [project website](https://example.com).
`q2-asap` is a QIIME 2 version of [ASAP] (https://github.com/TGenNorth/ASAP).

To learn how to use QIIME 2, refer to the [QIIME 2 User Documentation](https://docs.qiime2.org).
To learn QIIME 2 plugin development, refer to [*Developing with QIIME 2*](https://develop.qiime2.org).

`q2-asap` is a QIIME 2 community plugin, meaning that it is not developed and maintained by the developers of QIIME 2.

More information on development and support for community plugins can be found [here](https://library.qiime2.org).
If you need help with a community plugin, first refer to the [project website](https://example.com).
If that page doesn't provide information on how to get help, or you need additional help, head to the [Community Plugins category](https://forum.qiime2.org/c/community-contributions/community-plugins/14) on the QIIME 2 Forum where the QIIME 2 developers will do their best to help you.

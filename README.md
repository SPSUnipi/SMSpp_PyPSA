# README: how to use this package

This package is meant to be used with [SMS++](https://gitlab.com/smspp/smspp-project). In particular, it shall be cloned in a parent folder that condains the compiled `smspp-project` as discussed in the [installation of SMS++](https://gitlab.com/smspp/smspp-project/-/wikis/Installing-SMS++) or create it.

## Installation

To use this repo you shall:

1. Select the parent folder `~/parent_folder/` where you have a compiled version of smspp-project in `~/parent_folder/smspp-project`. If you don't have a compiled version of SMS++, please compile it in `~/parent_folder/smspp-project`, otherwise these code cannot be used.
2. Open a terminal window in such folder `~/parent_folder/`
2. Clone this repo in the parent folder
    ```bash
        ~/parent_folder$ git clone https://github.com/SPSUnipi/SMSpp_PyPSA
    ```
3. Create the conda environment to execute the environment
    ```bash
        ~/parent_folder$ cd SMSpp_PyPSA
        ~/parent_folder/SMSpp_PyPSA$ conda env create -f environment.yml
    ```

## Content

The package contains the following folders:

- `data`: contains the data used in the examples, both for the SMS++ models and PyPSA.
- `notebooks`: contains sample notebooks to run sample examples. In particular:
  - `SMSpp_LDS_launcher.ipynb` is a notebook that runs the Lagrangian Dual Solver tool of SMS++ to solve sample test cases
  - `SMSpp_ucblocksolver_launcher.ipynb` is a notebook that runs the UC Block Solver tool of PyPSA to solve unit commitment test cases
  - `SMSpp_investmentsolver_launcher.ipynb` is a notebook that runs investment block test cases
  - `SMSpp_netcdf_builder_dispatch.ipynb` is an experimental notebook that builds a netcdf file for the dispatch models starting from sample PyPSA models
  - `SMSpp_netcdf_builder_investment.ipynb` is an experimental notebook that builds a netcdf file for capacity-expansion models starting from sample PyPSA models
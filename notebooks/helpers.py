import numpy as np
import pandas as pd
import pypsa

def build_data(
    pv_file = '../data/microgrid/ninja_pv_1.7250_33.6208_uncorrected.csv',
    wind_file = '../data/microgrid/ninja_wind_1.7250_33.6208_uncorrected.csv',
    demand_file = '../data/microgrid/demand_data.csv',
    bus_loads = [1, 2],
    hydro_factor = 0.1, # fraction of the demand
):
    """
    Function to create a sample dataframe of RES and demand to build a PyPSA model
    """
    # Load the CSV file for pv
    df_pv = pd.read_csv(pv_file, skiprows=3)  # skip the first 3 rows
    df_pv.rename(columns={'electricity': 'pv'}, inplace=True)  # rename the electricity column

    # Load the CSV file for wind
    df_wind = pd.read_csv(wind_file, skiprows=3)  # skip the first 3 rows
    df_wind.rename(columns={'electricity': 'wind'}, inplace=True)  # rename the electricity column

    # file name of the pv data
    df_demand_day = pd.read_csv(demand_file)
    df_demand_day["hour"] = range(0, 24)

    df_demand = pd.DataFrame(index=df_pv.index)

    n_days = int(df_pv.shape[0]/24)

    np.random.seed(42)
    for i in bus_loads:
        df_demand_year = np.random.normal(
            np.tile(df_demand_day["demand"], n_days),
            np.tile(df_demand_day["standard_deviation"], n_days),
        )
        df_demand.loc[:, f"demand {i}"] = df_demand_year

    # create hydro time serie
    df_hydro = pd.DataFrame(index=df_pv.index)
    
    df_hydro["hydro"] = hydro_factor * df_demand.iloc[:, 0].mean() * np.maximum(
        0.0, np.random.normal(1., 1., df_pv.shape[0])
    )  # hydro power generation

    return pd.concat([df_pv[["pv"]], df_wind[["wind"]], df_hydro[["hydro"]], df_demand], axis=1)

def build_microgrid_model(
    n_snapshots = None,
    buses_demand = [1], #[1, 2],
    bus_PV = None, #0,
    bus_wind = None, #3,
    bus_storage = None, #0,
    bus_diesel = None, #2,
    bus_hydro = None, #1,
    add_load_shedding = False,
    load_shedding = 1000,
    x = 10.389754,
    y = 43.720810,
    hydro_factor = 0.1,
):
    """
    Build a basic microgrid using PyPSA
    """
    all_buses = [bus_PV, bus_wind, bus_storage, bus_diesel] + buses_demand
    all_buses = [b for b in all_buses if b is not None]

    n_buses = max(all_buses) - min(all_buses) + 1
    df_data = build_data(bus_loads=buses_demand, hydro_factor=hydro_factor)
    df_data = df_data.iloc[:n_snapshots]

    assumptions = build_assumptions()

    max_shedding = max(df_data[[f"demand {i}" for i in buses_demand]].sum(axis=1))

    # Create an empty PyPSA network
    n = pypsa.Network()

    # set the snapshots of the simulation, being the time steps of the data
    # reduce the number of snapshots according to the parameter
    if n_snapshots is None:
        n_snapshots = df_data.shape[0]
    n.set_snapshots(
        df_data.index,
        default_snapshot_weightings=365*24/n_snapshots
    )

    # Add buses to the microgrid
    n.madd(
        "Bus",
        [f"Bus {i}" for i in range(n_buses)],
        v_nom=0.4,
        x=[x + 0.1*i for i in range(n_buses)],
        y=[y + 0.1*i for i in range(n_buses)],
    )

    # Add the lines
    for i in range(n_buses-1):
        n.add(
            "Line",
            f"Line {i}--{i+1}",
            bus0=f"Bus {i}",
            bus1=f"Bus {i+1}",
            x=0.1,
            r=0.01,
            s_nom=10,
            s_nom_extendable=True,
        )

    # Add the load
    for bus in buses_demand:
        n.add("Load", f"load bus {bus}", bus=f"Bus {bus}", p_set=df_data[f"demand {bus}"])

    # Add PV
    if bus_PV is not None:
        n.add(
            "Generator",  # Each RES technology is represented with a "Generator" component
            "pv",
            carrier="pv",
            bus=f"Bus {bus_PV}",  # connect the generators to the microgrid bus
            p_max_pu=df_data["pv"],  # specify a maximum per-unit production for every time-step
            capital_cost=assumptions.loc["pv", "capital_cost"],  # specify the capital cost
            p_nom_extendable=True,  # Specify the installed capacity as an optimisation variable
        )

    # Add wind
    if bus_wind is not None:
        n.add(
            "Generator",  # Each RES technology is represented with a "Generator" component
            "wind",
            carrier="wind",
            bus=f"Bus {bus_wind}",  # connect the generators to the microgrid bus
            p_max_pu=df_data["wind"],  # specify a maximum per-unit production for every time-step
            capital_cost=assumptions.loc["wind", "capital_cost"],  # specify the capital cost
            p_nom_extendable=True,  # Specify the installed capacity as an optimisation variable
        )

    # Add the battery
    if bus_storage is not None:
        n.add(
            "StorageUnit",
            "battery",
            bus=f"Bus {bus_storage}",
            p_nom_extendable=True,
            capital_cost=assumptions.at["battery", "capital_cost"],
            cyclic_state_of_charge=False,
            state_of_charge_initial=0.,
        )

    # Add the hydro
    if bus_hydro is not None:
        n.add(
            "StorageUnit",
            "hydro",
            bus=f"Bus {bus_hydro}",
            p_nom_extendable=True,
            capital_cost=assumptions.at["hydro", "capital_cost"],
            cyclic_state_of_charge=False,
            inflow=df_data["hydro"],
            max_hours=6,
            state_of_charge_initial=0.,
        )

    # Add fuel generator
    if bus_diesel is not None:
        n.add(
            "Generator",
            "diesel",
            bus=f"Bus {bus_diesel}",
            carrier="diesel",
            p_nom_extendable=True,
            capital_cost=assumptions.at["diesel", "capital_cost"],
            marginal_cost=assumptions.at["diesel", "OPEX_marginal"],
        )
    
    # add load shedding
    if add_load_shedding:
        for bus in n.buses.index:
            n.add(
                "Generator",
                f"Curtailment_{bus}",
                bus=bus,
                carrier="curtailment",
                p_nom=max_shedding,
                marginal_cost=load_shedding,
            )
    
    return n


def build_assumptions():
    """
    Function to build basic numeric assumptions for a PyPSA model
    """
    # Initialize the dataframe: columns indicate cost components and rows indicate technologies
    assumptions = pd.DataFrame(
        columns=["CAPEX", "discount rate", "efficiency", "OPEX_fixed", "OPEX_marginal", "lifetime"],
        index=["default", "pv", "wind", "battery", "diesel"],
        dtype=float,
    )

    # default parameters
    assumptions.at["default", "OPEX_fixed"] = 3.0
    assumptions.at["default", "OPEX_marginal"] = 0.0
    assumptions.at["default", "discount rate"] = 0.08
    assumptions.at["default", "lifetime"] = 20

    # pv technology
    assumptions.at["pv", "CAPEX"] = 900  # EUR/kWp
    assumptions.at["pv", "OPEX_fixed"] = 16  # EUR/kWp/year
    assumptions.at["pv", "lifetime"] = 25  # years

    # wind technology
    assumptions.at["wind", "CAPEX"] = 2000  #2400  # EUR/kWp
    assumptions.at["wind", "OPEX_fixed"] = 40  #80  # EUR/kWp/year
    assumptions.at["wind", "lifetime"] = 25  #20  # years

    # battery technology
    assumptions.at["battery", "CAPEX"] = 800  # EUR/kWh
    assumptions.at["battery", "OPEX_fixed"] = 10  # EUR/kWh/year
    assumptions.at["battery", "efficiency"] = 0.9  # [-] per unit
    assumptions.at["battery", "lifetime"] = 10  # years

    # hydro technology
    assumptions.at["hydro", "CAPEX"] = 2200  # EUR/kW
    assumptions.at["hydro", "OPEX_fixed"] = 30  # EUR/kW/year
    assumptions.at["hydro", "efficiency"] = 0.9  # [-] per unit
    assumptions.at["hydro", "lifetime"] = 60  # years

    # diesel technology
    fuel_price = 1.4  # EUR/l
    fuel_energy_density = 10  # kWh/l
    efficiency_diesel = 0.33  # [-] per unit

    maintenance_diesel = 0.05  # EUR/kW/h

    assumptions.at["diesel", "CAPEX"] = 6e2  # EUR/kW
    assumptions.at["diesel", "OPEX_marginal"] = \
        (fuel_price / fuel_energy_density * efficiency_diesel + maintenance_diesel)  # EUR/kWh
    assumptions.at["diesel", "lifetime"] = 3  # years

    # fill defaults
    assumptions = assumptions.fillna(
        {
            "OPEX_fixed": assumptions.at["default", "OPEX_fixed"],
            "OPEX_marginal": assumptions.at["default", "OPEX_marginal"],
            "discount rate": assumptions.at["default", "discount rate"],
            "lifetime": assumptions.at["default", "lifetime"],
        }
    )

    def annuity(lifetime, rate):
        """
        Calculate the annuity factor for a given lifetime and discount rate.
        """
        if rate == 0.0:
            return 1 / lifetime
        else:
            return rate / (1.0 - 1.0 / (1.0 + rate) ** lifetime)


    # calculate annuity for every technology
    assumptions["annuity"] = assumptions.apply(
        lambda x: annuity(x["lifetime"], x["discount rate"]), axis=1
    )

    # annualise investment costs, add fixed OPEX to calculate the parameter `capital_cost` for the PyPSA model
    assumptions["capital_cost"] = [
        v["annuity"] * v["CAPEX"] + v["OPEX_fixed"]
        for i, v in assumptions.iterrows()
    ]

    return assumptions
# /// script
# dependencies = ["energy-plus-utility @ git+https://github.com/janithcyapa/energy-plus-utility.git@main"]
# ///

import marimo

__generated_with = "0.23.0"
app = marimo.App()


@app.cell
def _():
    import marimo as mo

    return (mo,)


@app.cell
def _():
    import subprocess

    return (subprocess,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    <a href="https://colab.research.google.com/github/janithcyapa/energy-plus-utility/blob/main/energyplus-utility.ipynb" target="_parent"><img src="https://colab.research.google.com/assets/colab-badge.svg" alt="Open In Colab"/></a>
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # EnergyPlus Utility
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Installation Inlocal Env
    """)
    return


app._unparsable_cell(
    r"""
    # 1.Create the directory
    mkdir -p ~/EnergyPlus-25-1-0

    # 2. Download the Ubuntu 24.04 build (Uses modern OpenSSL 3)
    wget https://github.com/NREL/EnergyPlus/releases/download/v25.1.0/EnergyPlus-25.1.0-68a4a7c774-Linux-Ubuntu24.04-x86_64.tar.gz

    # 3. Extract it exactly as before
    tar -xzf EnergyPlus-25.1.0-68a4a7c774-Linux-Ubuntu24.04-x86_64.tar.gz -C ~/EnergyPlus-25-1-0 --strip-components=1

    # 4. Install utility 
    pip install -q "energy-plus-utility @ git+https://github.com/janithcyapa/energy-plus-utility.git@main"
    """,
    name="_"
)


@app.cell
def _():
    import os
    import sys
    from pathlib import Path

    # Set paths
    eplus_dest = str(Path.home() / "EnergyPlus-25-1-0")

    # Inject environment variables so EnergyPlus and the Utility can find the binaries
    os.environ["ENERGYPLUSDIR"] = eplus_dest
    os.environ["LD_LIBRARY_PATH"] = f"{eplus_dest}:" + os.environ.get("LD_LIBRARY_PATH", "")

    # Add to Python path so you can import pyenergyplus
    if eplus_dest not in sys.path:
        sys.path.insert(0, eplus_dest)

    # Now you can safely import your professor's utility
    from eplus import EPlusUtil

    return (EPlusUtil,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Installation From Github Repo and Setup Environment
    """)
    return


@app.cell
def _(subprocess):
    #! pip uninstall -y energy-plus-utility
    subprocess.call(['pip', 'uninstall', '-y', 'energy-plus-utility'])
    return


@app.cell
def _():
    # packages added via marimo's package management: energy-plus-utility @ git+https://github.com/janithcyapa/energy-plus-utility.git@main !pip install -q "energy-plus-utility @ git+https://github.com/janithcyapa/energy-plus-utility.git@main"
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    `prepare_colab_eplus` - Download and Install EnergyPlus 25-1 in `/root/EnergyPlus-25-1-0`
    """)
    return


@app.cell
def _():
    import importlib.metadata
    ver = importlib.metadata.version("energy-plus-utility")
    print(f"\n✅ Installed 'energy-plus-utility' version: {ver}")
    return


@app.cell
def _():
    from eplus import prepare_colab_eplus
    prepare_colab_eplus()
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # Usage
    """)
    return


@app.cell
def _():
    from eplus.core import EPlusUtil
    import types

    return EPlusUtil, types


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ### Setup Basics
    """)
    return


@app.cell
def _(EPlusUtil):
    # In your main script or core.py
    # verbose, 0 - no logging, 1- verbose logging, 2 - debug logging
    OUT_DIR = "/simulation/eplus_out"
    sim = EPlusUtil(verbose=2, out_dir=OUT_DIR)

    # Reset state before setting model
    sim.reset_state()
    # Delete previous output directory
    sim.delete_out_dir()
    # Clear previous outputs
    sim.clear_eplus_outputs(patterns="eplusout.*")
    return OUT_DIR, sim


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ### Set Model using local files
    """)
    return


@app.cell
def _(sim):
    # Specify the EnergyPlus Import
    EPLUS_DIR = "/root/EnergyPlus-25-1-0"

    # Define the Simulation Model
    IDF = f"{EPLUS_DIR}/ExampleFiles/5ZoneAirCooled.idf"
    # Select Weather Data
    EPW = f"{EPLUS_DIR}/WeatherData/USA_CA_San.Francisco.Intl.AP.724940_TMY3.epw"
    # Set the Model for Simulation
    sim.set_model(IDF, EPW)
    return EPW, IDF


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ### Set Model From URL
    """)
    return


@app.cell
def _(sim):
    url_idf = "https://raw.githubusercontent.com/janithcyapa/DHCA-Framework/refs/heads/main/System%20Models/MultiZoneOffice/MultizoneOffice.idf"
    url_epw = "https://raw.githubusercontent.com/janithcyapa/DHCA-Framework/refs/heads/main/System%20Models/MultiZoneOffice/LKA_Colombo-Katunayake.434500_SWERA.epw"

    # Set the Model for Simulation
    sim.set_model_from_url(url_idf, url_epw)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ### View IDF/API Data
    """)
    return


@app.cell
def _(sim):
    sim.run_dry_run(include_ems_edd=False,reset=True,design_day=False) # Need to run this to get catalog
    return


@app.cell
def _(sim):
    sim.api_catalog_df()
    return


@app.cell
def _(sim):
    sim.list_available_variables()
    return


@app.cell
def _(sim):
    sim.list_available_meters()
    return


@app.cell
def _(sim):
    sim.list_available_actuators()
    return


@app.cell
def _(sim):
    objects_types = sim.get_idf_object_types()

    print(f"{'OBJECT TYPE':<40} | {'COUNT'}")
    print("-" * 50)
    for obj_type, count in objects_types:
        print(f"{obj_type:<40} | {count}")
    return


@app.cell
def _(sim):
    object = sim.extract_idf_objects("Zone")
    print(object)
    return


@app.cell
def _(sim):
    sim.clear_patched_idf()
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ### SetupSQL
    """)
    return


@app.cell
def _(sim):
    sim.ensure_output_sqlite()
    return


@app.cell
def _(sim):
    sim.ensure_output_variables([
        {"name": "System Node Temperature", "key": "*", "freq": "Hourly"},
        {"name": "System Node Mass Flow Rate", "key": "*", "freq": "Hourly"},
        {"name": "System Node Humidity Ratio", "key": "*", "freq": "Hourly"},
        {"name": "Zone Air Temperature", "key": "*", "freq": "Hourly"},
        {"name": "Zone Air Relative Humidity", "key": "*", "freq": "Hourly"}
    ])

    sim.ensure_output_variables([
        {"name": "Site Outdoor Air Drybulb Temperature", "key": "Environment"},
        {"name": "Site Outdoor Air Humidity Ratio", "key": "Environment"},
        {"name": "Site Wind Speed", "key": "Environment"},
        {"name": "Site Direct Solar Radiation Rate per Area", "key": "Environment"}
    ])
    return


@app.cell
def _(sim):
    sim.ensure_output_meters([
        "Electricity:Facility",          # Total building electricity
        "Fans:Electricity",              # Electricity used by HVAC fans
        "Cooling:Electricity",           # Electricity used for cooling (Chillers/DX coils)
        "Heating:Electricity",           # Electricity used for heating
        "ElectricityPurchased:Facility"  # Total grid electricity bought
    ], freq="Hourly")
    return


@app.cell
def _(sim):
    specs = [
        # --- Zone state + people ---
        {"name": "Zone Mean Air Temperature",                "key": "*",            "freq": "TimeStep"},
        {"name": "Zone Mean Air Dewpoint Temperature",       "key": "*",            "freq": "TimeStep"},
        {"name": "Zone Air Relative Humidity",               "key": "*",            "freq": "TimeStep"},
        {"name": "Zone Mean Air Humidity Ratio",             "key": "*",            "freq": "TimeStep"},
        {"name": "Zone People Occupant Count",               "key": "*",            "freq": "TimeStep"},

        # --- CO₂ & OA into zones ---
        {"name": "Zone Air CO2 Concentration",               "key": "*",            "freq": "TimeStep"},

        # --- Site weather (Environment key) ---
        {"name": "Site Outdoor Air Drybulb Temperature",     "key": "Environment",  "freq": "TimeStep"},
        {"name": "Site Outdoor Air Wetbulb Temperature",     "key": "Environment",  "freq": "TimeStep"},
        {"name": "Site Outdoor Air Dewpoint Temperature",     "key": "Environment",  "freq": "TimeStep"},
        {"name": "Site Outdoor Air Relative Humidity",     "key": "Environment",  "freq": "TimeStep"},
        {"name": "Site Outdoor Air Humidity Ratio",     "key": "Environment",  "freq": "TimeStep"},
        {"name": "Site Outdoor Air Barometric Pressure",        "key": "Environment", "freq": "TimeStep"},
        {"name": "Site Outdoor Air CO2 Concentration",                          "key": "Environment",  "freq": "TimeStep"},

        {"name": "System Node Temperature",               "key": "*",            "freq": "TimeStep"},
        {"name": "System Node Mass Flow Rate",               "key": "*",            "freq": "TimeStep"},
        {"name": "System Node Humidity Ratio",               "key": "*",            "freq": "TimeStep"},
        {"name": "System Node CO2 Concentration",               "key": "*",            "freq": "TimeStep"},
    ]

    sim.ensure_output_variables(specs, activate=True)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ### Occupency and CO2
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    You must first use prepare_run_with_co2 to modify your EnergyPlus Input Data File (IDF). Without this, EnergyPlus won't "know" how to track CO₂ or where to look for your outdoor concentration values.Before the simulation loops, you need to register the handlers. The occupancy_handler needs to be "hooked" into the EnergyPlus callback system so it runs at every timestep.
    """)
    return


@app.cell
def _(sim):
    sim.prepare_run_with_co2(
        outdoor_co2_ppm=415.0,           # Starting outdoor concentration
        per_person_m3ps_per_W=3.82e-8,   # CO2 generation rate (default)
    )
    return


@app.cell
def _(sim):
    # Use the helper to push this value into the simulation
    sim.co2_set_outdoor_ppm(
            value_ppm=415,
            verify=True
        )
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ### Run Simualtion
    """)
    return


@app.cell
def _(sim):
    sim.enable_runtime_logging()
    # sim.disable_runtime_logging()
    return


@app.cell
def _(sim):
    sim.run_dry_run(include_ems_edd=False,reset=True,design_day=False)
    return


@app.cell
def _(sim):
    sim.run_design_day()
    return


@app.cell
def _(sim):
    sim.set_simulation_params(

        start=(1, 1),
        end=(12, 31),
        start_day_of_week="Sunday"
    )
    return


@app.cell
def _(sim):
    sim.run_annual()
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ### Usage of Handlers
    """)
    return


@app.cell
def _(sim, types):
    # --- STEP A: DEFINE THE CUSTOM FUNCTION ---
    # Notice we define it with 'self' as the first argument, just like a class method.
    def dr_supervisor_logic(self, state):
        """
        A simple logic that checks the time and prints a message.
        """
        # Just printing for this demo, but you would put control logic here
        time = self.exchange.current_time(state)
        print(f"[SUPERVISOR] Checking status at time: {time:.2f}")

    # --- STEP B: INJECT IT  ---
    # This binds the function ONLY to this 'sim' object.
    # It creates a true method where 'self' is passed automatically.
    sim.my_supervisor = types.MethodType(dr_supervisor_logic, sim)
    return


@app.cell
def _(sim):
    print("--- 1. REGISTERING ---")
    # We register the NAME of the attribute we just attached ("my_supervisor")
    registered = sim.register_handlers(
        "begin",               # Hook: Begin Timestep
        ["my_supervisor"]      # Method Name
    )
    print(f"Registered methods: {registered}")

    print("\n--- 2. LISTING ---")
    # Check what is currently scheduled for the 'begin' hook
    current_list = sim.list_handlers("begin")
    print(f"Handlers on 'begin' hook: {current_list}")

    print("\n--- 3. DISABLING (Pausing) ---")
    # Scenario: It's Winter, we don't need Demand Response.
    # We disable the hook so the logic stops running, but we don't delete it.
    sim.disable_hook("begin")
    print("Hook 'begin' is now DISABLED. (Simulation runs, but supervisor sleeps)")

    print("\n--- 4. ENABLING (Resuming) ---")
    # Scenario: Summer is back. Turn the logic back on.
    sim.enable_hook("begin")
    print("Hook 'begin' is now ENABLED. (Supervisor is active again)")

    print("\n--- 5. UNREGISTERING (Deleting) ---")
    # Scenario: We want to remove this logic entirely to replace it or clean up.
    remaining = sim.unregister_handlers(
        "begin",
        ["my_supervisor"] # Name to remove
    )
    print(f"Unregistered 'my_supervisor'. Remaining handlers: {remaining}")

    # --- RUN ---
    # sim.run_annual()
    return


@app.cell
def _(sim):
    registered_1 = sim.register_handlers('begin', ['my_supervisor'])
    current_list_1 = sim.list_handlers('begin')  # Hook: Begin Timestep
    print(f"Handlers on 'begin' hook: {current_list_1}")  # Method Name
    # --- RUN ---
    sim.run_annual()
    return


@app.cell
def _(sim):
    sim.register_handlers(
        "after_hvac",
        [{"method_name": "probe_zone_air_and_supply",
          "key_wargs": {"log_every_minutes": 1, "precision": 3}}],
        clear=False, run_during_warmup=False
    )
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ### In-Built Handlers
    """)
    return


@app.cell
def _(sim):
    # Register the random occupancy logic to run at the start of every iteration
    sim.register_handlers(
        "after_hvac",
        [{"method_name": "occupancy_handler","key_wargs": {"lam": 33.0, "min": 20, "max": 45, "seed": 123}}],
        clear=False, run_during_warmup=False
    )
    return


@app.cell
def _(sim):
    sim.register_handlers(
        "after_hvac",
        [{"method_name": "probe_zone_air_and_supply",
          "key_wargs": {"log_every_minutes": 1, "precision": 3}}],
        clear=False, run_during_warmup=False
    )
    return


@app.cell
def _(sim):
    sim.register_handlers(
        "begin",
        [{"method_name": "probe_zone_air_and_supply_with_kf",
         "key_wargs": {
             "log_every_minutes": 15,
             "precision": 3,

             "kf_db_filename": "eplusout_kf_test.sqlite",
             "kf_batch_size": 50,
             "kf_commit_every_batches": 10,
             "kf_checkpoint_every_commits": 5,
             "kf_journal_mode": "WAL",
             "kf_synchronous": "NORMAL",

             # --- 10-state init (αo, αs, αe, βo, βs, βe, γe, Tz, wz, cz)
             "kf_init_mu":        [0.1, 0.1, 0.0,  0.1, 0.1, 0.0,  0.0,  20.0, 0.008, 400.0],
             "kf_init_cov_diag":  [1.0, 1.0, 1.0,  1.0, 1.0, 1.0,  1.0,  25.0, 1e-3,  1e3  ],
             "kf_sigma_P_diag":   [1e-6,1e-6,1e-6, 1e-6,1e-6,1e-6, 1e-6, 1e-5, 1e-6,  1e-4 ],

             # Optional: pretty column names for state persistence (dynamic schema)
             "kf_state_col_names": [
                 "alpha_o","alpha_s","alpha_e","beta_o","beta_s","beta_e","gamma_e","Tz","wz","cz"
             ],

             # Use the 10-state EKF preparer
             "kf_prepare_fn": sim._kf_prepare_inputs_zone_energy_model
         }}],
        clear=True
    )
    return


@app.cell
def _(sim):
    sim.register_handlers(
        "before_hvac",
        [{"method_name": "tick_set_actuator",
          "kwargs": {
            "component_type": "System Node Setpoint",
            "control_type":   "Mass Flow Rate Setpoint",
            "actuator_key":   "SPACE4-1 ZONE COIL AIR IN NODE",
            "value":          0.35,            # kg/s request
            "when":           "success",
            "read_back":      True,            # read back actuator value after setting
            "precision":      4
          }}],
        run_during_warmup=False
    )
    return


@app.cell
def _(sim):
    sim.register_handlers(
        "after_hvac",
        [{"method_name": "tick_log_actuator",
          "kwargs": {
            "component_type": "System Node Setpoint",
            "control_type":   "Mass Flow Rate Setpoint",
            "actuator_key":   "SPACE4-1 ZONE COIL AIR IN NODE",
            "when": "always", #"on_change",
            "precision": 3
          }}],
        run_during_warmup=False
    )
    return


@app.cell
def _(sim):
    sim.register_handlers(
        "after_hvac",   # alias for callback_begin_system_timestep_before_predictor
        [{
            "method_name": "tick_log_meter",
            "kwargs": {
                "name": "Electricity:Facility",
                "which": "value",            # current tick value
                "when": "always",         # only log when it changes
                "precision": 3,
                "include_timestamp": True,
                "allow_warmup": False        # skip during sizing/warmup
            }
        }],
        clear=False,
        run_during_warmup=False
    )
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ### HVAC Shedule
    """)
    return


@app.cell
def _(sim):
    # Diable HVAC Shedules
    sim.override_hvac_schedules(autodetect=True)
    # sim.override_hvac_schedules(
    #     schedule_names=["Central Fan Avail Sched", "Heating Setpoint Sched"]
    # )
    return


@app.cell
def _(sim):
    sim.release_hvac_schedules()
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ### Control
    """)
    return


@app.cell
def _(sim, types):
    def zone_temp_controller(self, state):
        """
        Simple Bang-Bang or Proportional controller for Zone Temperature.
        """
        # 1. READ: Get the current zone temperature
        # Using your 'runtime_get_variable' helper
        current_temp = self.runtime_get_variable(
            state,
            name="Zone Mean Air Temperature",
            key="CORE_ZN"
        )

        # Safety check: API might not be ready during first few ticks
        if current_temp is None:
            return

        # 2. DECIDE: Logic to determine the new setpoint
        # Example: If it's too hot (> 25C), drop setpoint to 22C. Otherwise, stay at 24C.
        if current_temp > 10.0:
            new_setpoint = 12.0
        else:
            new_setpoint = 14.0

        # 3. WRITE: Update the cooling setpoint schedule
        # Using your 'runtime_set_actuator' helper
        success = self.runtime_set_actuator(
            state,
            component_type="Schedule:Compact",
            control_type="Schedule Value",
            actuator_key="Cooling_Setpoint_Sched",
            value=new_setpoint,
            log=True # This will use your internal _log to record the change
        )

    # 4. BIND & REGISTER
    # Attach the function to your simulation object
    sim.zone_control = types.MethodType(zone_temp_controller, sim)

    # Register it to the 'begin_zone_timestep_before_set_point_manager' hook
    # This is the best hook for temperature control as it happens right before
    # HVAC systems calculate their response for the step.
    sim.register_handlers(
        "begin",
        ["zone_control"]
    )

    sim.run_annual()
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ### SQL
    """)
    return


@app.cell
def _(sim):
    df_list = sim.list_sql_zone_variables(like="Zone %Temperature%")
    print(df_list)
    return


@app.cell
def _(sim):
    df_list_1 = sim.list_sql_zone_variables(like='System Node %Temperature%')
    print(df_list_1)
    return


@app.cell
def _(sim):
    fig = sim.plot_sql_zone_variable(
        var_name="Zone Air Temperature",
        keys=["PERIMETER_ZN_1 ZN", "CORE_ZN ZN"],
        resample="1D",
        start="2002-01-01"
    )
    return


@app.cell
def _(sim):
    fig_1 = sim.plot_sql_zone_variable(var_name='Zone Air Temperature', keys=['PERIMETER_ZN_1 ZN', 'CORE_ZN ZN'], resample='1D', start='2002-01-01')
    return


@app.cell
def _(sim):
    sim.plot_sql_meters(
        ["Electricity:Facility", "Fans:Electricity"],
        resample="1D"  # Look at daily totals
    )
    return


@app.cell
def _(sim):
    # Define your "Control" (Setpoints) and "Output" (Actual Temps)
    controls = [{"kind": "var", "name": "Zone Thermostat Heating Setpoint Temperature", "key": "*"}]
    outputs  = [{"kind": "var", "name": "Zone Air Temperature", "key": "*"}]

    # Generate a correlation heatmap
    sim.plot_sql_cov_heatmap(
        control_sels=controls,
        output_sels=outputs,
        stat="corr",  # Show correlation (-1 to 1)
        resample="1h"
    )
    return


@app.cell
def _(sim):
    # Export outdoor conditions to a CSV for external analysis
    sim.export_weather_sql_to_csv(csv_filename="site_weather_data.csv")
    return


@app.cell
def _(display, sim):
    # Get a raw DataFrame of zone temperatures
    df = sim.get_sql_series_dataframe([
        {"kind": "var", "name": "Zone Air Temperature", "key": "*"}
    ])
    display(df)
    # Now you can use df.mean(), df.groupby(), etc.
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ### Test
    """)
    return


@app.cell
def _(EPW, IDF, OUT_DIR, sim):
    args = [
            '-w', EPW,
            '-d', OUT_DIR,
            IDF
        ]

    print("Starting simulation...")
    exit_code = sim.runtime.run_energyplus(sim.state, args)

    if exit_code == 0:
        print("Simulation success!")
    else:
        print("Simulation failed!")
    return


@app.cell
def _(sim):
    print(dir(sim))
    print(hasattr(sim, 'run_design_day'))
    return


if __name__ == "__main__":
    app.run()

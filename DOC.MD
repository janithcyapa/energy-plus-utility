# EnergyPlus Python API Wrapper Documentation

## 1. `StateMixin` (state.py)

This is the core mixin that inherits directly from `EnergyPlusAPI`. It manages the foundational EnergyPlus state, setting up model files, and cleaning output directories.

**Public Functions:**

* **`set_model(idf, epw, out_dir=None, reset=True, kwargs)`**: Configures the active EnergyPlus model by defining paths for the `.idf`, `.epw`, and output directory. Optionally injects a minimal CO₂ setup if `add_co2=True` is passed in kwargs.
* **`set_model_from_url(idf_url, epw_url, out_dir=None, kwargs)`**: Downloads IDF and EPW files from direct URLs into the `out_dir` and subsequently configures the model.
* **`reset_state()`**: Re-initializes the internal EnergyPlus C++ state so that subsequent simulation runs start clean.
* **`clear_eplus_outputs(patterns=("eplusout.*",))`**: Removes standard EnergyPlus output files to prevent file-lock or stale SQLite issues before a new run.
* **`delete_out_dir()`**: Recursively deletes the entire output directory defined in `self.out_dir`.

---

## 2. `SimulationMixin` (simulation.py)

Handles the execution and simulation parameter modifications for the EnergyPlus model.

**Public Functions:**

* **`run_annual()`**: Executes a full annual simulation using the configured IDF and EPW files. Automatically resets state and clears old outputs.
* **`run_design_day()`**: Executes a fast, sizing-period-only simulation (design-day). Great for probing and dictionary generation.
* **`run_dry_run(include_ems_edd=False, reset=True, design_day=True)`**: Performs a minimal probe run to rapidly generate `.rdd` (variables), `.mdd` (meters), and optionally `.edd` (EMS outputs) dictionary files without emitting standard SQL.
* **`set_simulation_params(...)`**: Programmatically patches the IDF’s `Timestep`, `RunPeriod`, and `Sizing:Parameters` to control timesteps per hour, start/end dates, holidays, and warmup days. Creates a patched IDF and sets it as the active file.

---

## 3. `HandlersMixin` (handlers.py)

A powerful callback registry system for interacting with the EnergyPlus runtime. Allows you to bind Python methods to various EnergyPlus execution hooks (e.g., *begin system timestep*, *before HVAC managers*).

**Public Functions:**

* **`register_handlers(hook, methods, clear=False, enable=True, run_during_warmup=None)`**: Binds instance methods to a specific runtime hook. Creates a dispatcher so multiple methods can run sequentially at the same hook.
* **`list_handlers(hook)`**: Returns a list of method names currently registered to a specific EnergyPlus hook.
* **`unregister_handlers(hook, names)`**: Removes specific methods from a hook's execution registry.
* **`enable_hook(hook)`** / **`disable_hook(hook)`**: Temporarily pauses or resumes the dispatching of callbacks for a specific hook.
* **`enable_runtime_logging()`** / **`disable_runtime_logging()`**: Attaches a callback to capture and print EnergyPlus console messages to Python's standard output.
* **`override_hvac_schedules(schedule_names=None, autodetect=True)`**: Forces specified HVAC schedules to `0.0` at every timestep to kill HVAC operation. Can automatically detect availability schedules.
* **`release_hvac_schedules()`**: Stops forcing the HVAC availability schedules to zero.
* **`probe_zone_air_and_supply(s, opts)`**: A fast runtime callback that snapshots zone air states (T, w, CO₂) and mass-flow-weighted supply conditions.
* **`api_check_zone_humidity_ratio(s, opts)`**: Diagnostic callback that verifies if the API is successfully returning zone humidity ratio, with Tetens-based psychrometric fallbacks.

**Internal Functions:** `_register_callbacks`, `_init_callback_hub`, `_resolve_runtime_register`, `_get_or_init_hook_registry`, `_ensure_hook_registered`.

---

## 4. `ControlMixin` (control.py)

Provides lightweight, caching getters and setters for real-time interaction with the EnergyPlus API. Designed to be called *inside* your registered handlers.

**Public Functions:**

* **`runtime_get_actuator(...)`**: Resolves handles (caching them per run) and reads the current value of an EnergyPlus actuator.
* **`runtime_set_actuator(...)`**: Sets the value of an actuator. Accepts raw numbers or a callable function to evaluate the value dynamically at every timestep.
* **`tick_log_actuator(...)`**: Read and conditionally log an actuator value (e.g., `when="on_change"` to only print when the value shifts).
* **`tick_set_actuator(...)`**: Conditionally sets and logs an actuator, preventing console spam by only logging on success or on value changes.
* **`runtime_get_variable(...)`**: Gets a runtime report variable (e.g., "Zone Mean Air Temperature").
* **`tick_log_variable(...)`**: Reads and optionally logs a variable value under specified rules (`always`, `on_change`, `on_resolve`).
* **`runtime_get_meter(...)`**: Reads current, last-timestep, or accumulated meter values.
* **`tick_log_meter(...)`**: Reads and conditionally logs meter values at runtime.

---

## 5. `SQLMixin` (sql.py)

Enables output generation, data extraction, and Plotly visualization from the EnergyPlus SQLite (`eplusout.sql`) database.

**Public Functions:**

* **`ensure_output_sqlite(activate=True, reset=True)`**: Patches the IDF to guarantee `Output:SQLite, SimpleAndTabular;` is present.
* **`ensure_output_variables(specs, ...)`** / **`ensure_output_meters(names, ...)`**: Dynamically appends `Output:Variable` and `Output:Meter` objects to the active IDF file.
* **`inspect_sql_meter(name, include_design_days=False)`**: Returns a summary DataFrame of available reporting frequencies and units for a specified meter in the SQL database.
* **`get_sql_series_dataframe(selections, reporting_freq, ...)`**: Core data-fetching method. Returns a tidy, long-form pandas DataFrame of requested variables/meters direct from SQL.
* **`plot_sql_series(selections, ...)`**: Plots SQL variables or meters using Plotly. Auto-converts Joules to kWh for meters and handles resampling/aggregating.
* **`list_sql_zone_variables(...)`**: Lists zone-scoped variables that actually exist in the SQL database, grouped by frequency and units.
* **`plot_sql_zone_variable(...)`**: Auto-selects zones and plots a specific zone variable (e.g., "Zone Air Temperature") for easy comparison.
* **`plot_sql_meters(...)`**: Convenience wrapper for plotting meters.
* **`plot_sql_cov_heatmap(...)`**: Computes and plots a covariance or Pearson correlation heatmap comparing "control" series against "output" series.
* **`export_weather_sql_to_csv(...)`**: Extracts site/weather conditions from SQL and saves them as a clean, wide-format CSV file.

**Internal Functions:** `_sql_minute_col`, `_sql_freq_clause`, `_discover_zone_inlet_nodes_from_sql`.

---

## 6. `IDFMixin` (idf.py)

Provides textual parsing and patching capabilities for the IDF file, as well as access to the API catalog.

**Public Functions:**

* **`api_catalog_df(save_csv=False)`**: Asks the EnergyPlus API for all available runtime data (Actuators, Variables, Meters) and returns them mapped to pandas DataFrames.
* **`list_available_variables()`**, **`list_available_meters()`**, **`list_available_actuators()`**: Convenience wrappers extracting specific DataFrame tables from the `api_catalog_df`.
* **`get_idf_object_types()`**: Regex-scans the IDF and returns a frequency count of all object types.
* **`extract_idf_objects(object_type)`**: Scans the IDF text and extracts the names of all objects of a specific type.
* **`patch_idf_entry(object_type, object_name, old_value, new_value, inplace=False)`**: A targeted regex-based patcher that swaps text inside a specific IDF object block without destroying the rest of the file format.
* **`get_zone_thermal_parameters(eplus_dir)`**: Converts the IDF to `epJSON` using E+'s CLI tool, parses geometry, and extracts building thermal constants (Volume, R, C, M bounds) for state-space control logic.
* **`clear_patched_idf()`**: Restores the internal state to use the original, un-patched IDF.

**Internal Functions:** `_remove_object_blocks`, `_append_block`, `_calculate_polygon_area`, `_get_construction_resistance`.

---

## 7. `ZoneObserverMixin` (zone_observer.py)

Advanced Kalman Filtering toolset. Reconstructs hidden building state variables using Extended Kalman Filters (EKF) combined with runtime probes.

**Public Functions:**

* **`probe_zone_air_and_supply_with_kf(s, opts)`**: A heavy-duty runtime callback. Fetches a snapshot of zone conditions, delegates to an EKF preparer, executes a Kalman filter update, and dynamically persists the posteriors (estimates) to a SQLite table.

**Internal/Advanced Functions:**

* **`_ekf_update(...)`**: Math engine for a single-step Extended Kalman Filter.
* **`_kf_random_walk_update(...)`** / **`_kf_random_walk_update_simdkalman(...)`**: Math engines for random-walk Kalman implementations.
* **`_kf_prepare_inputs_zone_energy_model(...)`**: Default physics preparer for the EKF. Represents a 10-state differential equation zone energy/mass balance model mapping $x = [\alpha_o, \alpha_s, \alpha_e, \beta_o, \beta_s, \beta_e, \gamma_e, T_z, w_z, c_z]$.

---

## 8. `OccupancyMixin` (occupancy.py)

Provides features for directly manipulating zone occupancy and Carbon Dioxide modeling.

**Public Functions:**

* **`prepare_run_with_co2(...)`**: Modifies the IDF to strip out old CO2 sources, activates `ZoneAirContaminantBalance`, adds an actuated outdoor CO2 schedule, and patches `People` objects with a specific generation rate.
* **`occupancy_handler(s, overrides)`**: A runtime handler that overrides zone occupancy using a randomized truncated Poisson distribution (simulates varying headcount at every timestep).
* **`co2_set_outdoor_ppm(s, opts)`**: Runtime handler that sets the global outdoor CO₂ concentration schedule dynamically during a simulation.

**Internal Functions:** `_occ_default_map_zone_to_people`, `_occ_current_timestamp`, `_occ_cb_tick`.

---

## 9. `UtilsMixin` (utils.py)

Provides simple, shared utility methods.

**Public Functions:**

* **`list_zone_names(preferred_sources=("sql", "api", "idf"), save_csv=False)`**: Safely fetches all zone names from the model. Uses a cascading fallback strategy: tries to read the SQLite database first, then does a fast API design-day probe, and finally falls back to simple regex parsing of the IDF.

**Internal Functions:** `_assert_out_dir_writable`, `_scan_output_variables`, `_scan_output_meters`.

---

## 10. `LoggingMixin` (logging.py)

Provides the base logging mechanics used by all other mixins.

**Internal Functions:** * **`_log(level, msg)`**: Prints a message to standard output based on a predefined `self.verbose` threshold.D

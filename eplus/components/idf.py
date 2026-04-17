import os
import shutil
from typing import Optional
import os, io, csv as _csv, ast, shutil, pathlib, subprocess, re, tempfile, contextlib
import pandas as pd
from collections import Counter
import re

class IDFMixin:
    def __init__(self):
        self._log(2, "Initialized IDFMixin")
        self._patched_idf_path: Optional[str] = None
        self._orig_idf_path: Optional[str] = None
    
    def clear_patched_idf(self):
        """Revert to the original IDF if we switched to a patched one."""
        if getattr(self, "_orig_idf_path", None):
            self.idf = self._orig_idf_path
        self._patched_idf_path = None
        self._orig_idf_path = None  # also clear to return to a clean slate

    def _remove_object_blocks(self, text: str, object_type: str) -> str:
        """
        Safely removes an entire IDF object block without affecting adjacent objects.
        Uses a strictly bounded, non-greedy regex to stop exactly at the terminating semicolon.
        """
        # Regex Breakdown:
        # (?i)       -> Case insensitive match
        # ^\s* -> Start of line, allowing for leading spaces
        # {obj}[,\s] -> The exact object name followed by a comma or whitespace
        # .*?        -> Non-greedy match for all the fields inside the object
        # ;          -> The strict terminator for the EnergyPlus object
        # [^\n]*\n?  -> Cleanly swallows any trailing comments (!- ...) and the newline
        
        pattern = re.compile(
            rf"(?i)^\s*{re.escape(object_type)}[,\s].*?;[^\n]*\n?", 
            re.MULTILINE | re.DOTALL
        )
        
        # Remove the targeted block
        cleaned_text = pattern.sub("\n", text)
        
        # Clean up any excessive blank lines left behind to keep the IDF tidy
        cleaned_text = re.sub(r'\n{3,}', '\n\n', cleaned_text)
        
        return cleaned_text

    def _append_block(self, idf_text: str, block: str) -> str:
        return idf_text.rstrip() + "\n\n" + block.strip() + "\n"

    def api_catalog_df(self, *, save_csv: bool = False) -> dict[str, "pd.DataFrame"]:
        """
        Discover **runtime API-exposed catalogs** from EnergyPlus and return them as
        pandas DataFrames, grouped by section.

        Under the hood this wraps:
            self.exchange.list_available_api_data_csv(self.state)

        What you get
        ------------
        A dict mapping **section name → DataFrame**, for *all* sections present in
        the current model / E+ build. Typical keys you may see:
        - "ACTUATORS"
        - "INTERNAL_VARIABLES"
        - "PLUGIN_GLOBAL_VARIABLES"
        - "TRENDS"
        - "METERS"
        - "VARIABLES"

        Notes & scope
        -------------
        • This catalog comes **directly from the runtime API** (no IDF parsing, no RDD/MDD/EDD).
        • Availability depends on when you call it; best after inputs are parsed or API data are ready.
        Use one of:
            - inside `callback_after_get_input`, or
            - after warmup via `callback_after_new_environment_warmup_complete`, or
            - when `self.exchange.api_data_fully_ready(self.state)` is True.
        • Column shapes vary slightly across sections / versions. This function assigns
        sensible headers per known section and pads/truncates rows as needed.

        Parameters
        ----------
        save_csv : bool, default False
            If True, writes the **raw** CSV from EnergyPlus to `<out_dir>/api_catalog.csv`.

        Returns
        -------
        dict[str, pandas.DataFrame]
            A dictionary of DataFrames keyed by section name. Missing sections simply won't appear.

        Examples
        --------
        >>> # Get everything the runtime reports
        >>> sections = util.api_catalog_df()
        >>> list(sections.keys())
        ['ACTUATORS', 'INTERNAL_VARIABLES', 'PLUGIN_GLOBAL_VARIABLES', 'TRENDS', 'METERS', 'VARIABLES']

        >>> # Inspect schedule-based actuators you can set via get_actuator_handle(...)
        >>> acts = sections.get("ACTUATORS", pd.DataFrame())
        >>> acts.query("ComponentType == 'Schedule:Compact' and ControlType == 'Schedule Value'").head()

        >>> # See available report variables (names/keys/units) the API knows about
        >>> vars_df = sections.get("VARIABLES", pd.DataFrame())
        >>> vars_df.head()

        >>> # Save the raw catalog for auditing
        >>> util.api_catalog_df(save_csv=True)
        """

        ex = self.exchange
        csv_bytes = ex.list_available_api_data_csv(self.state)
        

        # Optionally persist the raw CSV
        if save_csv:
            try:
                out_path = os.path.join(self.out_dir, "api_catalog.csv")
                with open(out_path, "wb") as f:
                    f.write(csv_bytes)
                try:
                    self._log(1, f"[api_catalog] Saved → {out_path} ({len(csv_bytes)} bytes)")
                except Exception:
                    print(f"[api_catalog] Saved → {out_path} ({len(csv_bytes)} bytes)")
            except Exception:
                pass

        # Parse the catalog: the file is a sequence of sections, each starting with "**NAME**"
        lines = csv_bytes.decode("utf-8", errors="replace").splitlines()
        sections_raw: dict[str, list[list[str]]] = {}
        current = None
        for raw in lines:
            line = raw.strip()
            if not line:
                continue
            if line.startswith("**") and line.endswith("**"):
                current = line.strip("*").strip().upper().replace(" ", "_")
                sections_raw.setdefault(current, [])
                continue
            # Catalog rows are simple CSV without quoted commas → split on ','
            row = [c.strip() for c in line.split(",")]
            if current:
                sections_raw[current].append(row)

        # Known schemas per section (fallbacks are applied when row lengths differ)
        SCHEMAS: dict[str, list[str]] = {
            # Example row: Actuator,Schedule:Compact,Schedule Value,OCCUPY-1,[ ]
            "ACTUATORS": ["Kind", "ComponentType", "ControlType", "ActuatorKey", "Units"],
            # Example row: Internal Variable,Zone,Zone Floor Area,LIVING ZONE,[m2]
            "INTERNAL_VARIABLES": ["Kind", "VariableType", "VariableName", "KeyValue", "Units"],
            # Example row: Plugin Global Variable,<name>
            "PLUGIN_GLOBAL_VARIABLES": ["Kind", "Name"],
            # Example row: Trend,<name>,<length> (varies)
            "TRENDS": ["Kind", "Name", "Length"],
            # Example row: Meter,Electricity:Facility,[J] (varies)
            "METERS": ["Kind", "MeterName", "Units"],
            # Example row: Variable,Zone Mean Air Temperature,LIVING ZONE,[C] (varies)
            "VARIABLES": ["Kind", "VariableName", "KeyValue", "Units"],
        }

        dfs: dict[str, pd.DataFrame] = {}
        for sec, rows in sections_raw.items():
            # Choose schema or a generic fallback wide enough for the observed rows
            cols = SCHEMAS.get(sec)
            if cols is None:
                max_cols = max([len(r) for r in rows] + [5])
                cols = [f"col{i+1}" for i in range(max_cols)]

            # Normalize rows to the column count
            width = len(cols)
            norm = [(r + [""] * (width - len(r)))[:width] for r in rows]
            df = pd.DataFrame(norm, columns=cols)

            # Light cleanup
            if "Kind" in df.columns:
                df["Kind"] = df["Kind"].astype(str).str.strip().str.title()
            for c in df.columns:
                df[c] = df[c].astype(str).str.strip()

            dfs[sec] = df

        return dfs

    def list_available_variables(self, *, save_csv: bool = False):
        """
        Return the **runtime API catalog of report variables** as a pandas DataFrame.

        What this is
        ------------
        A thin wrapper around `self.api_catalog_df()` that extracts the "VARIABLES"
        section reported by the EnergyPlus runtime API (via
        `exchange.list_available_api_data_csv`). It does **not** parse your IDF and
        does **not** require RDD/MDD/SQL — it’s whatever the API exposes at runtime.

        When to call
        ------------
        Call after inputs are parsed (e.g., in/after `callback_after_get_input`) or
        once `exchange.api_data_fully_ready(self.state)` is True. Calling earlier may
        yield an empty frame.

        Columns (typical)
        -----------------
        ["Kind", "VariableName", "KeyValue", "Units"]
        (Column names are normalized by `api_catalog_df`; may vary slightly by E+ version.)

        Parameters
        ----------
        save_csv : bool, default False
            If True, also saves the **raw** API catalog CSV to `<out_dir>/api_catalog.csv`.

        Returns
        -------
        pandas.DataFrame
            The "VARIABLES" section; empty DataFrame if the section is absent.

        Examples
        --------
        >>> df = util.list_available_variables()
        >>> df.head()

        >>> # What zone-style variables are available?
        >>> df[df["VariableName"].str.contains("Zone ", case=False, na=False)].head()
        """
        import pandas as pd
        sections = self.api_catalog_df(save_csv=save_csv)
        df = sections.get("VARIABLES", pd.DataFrame(columns=["Kind","VariableName","KeyValue","Units"]))
        return df

    def list_available_meters(self, *, save_csv: bool = False):
        """
        Return the **runtime API catalog of meters** as a pandas DataFrame.

        What this is
        ------------
        A convenience accessor for the "METERS" section from
        `exchange.list_available_api_data_csv`. Unlike RDD/MDD parsing, this is
        **purely runtime** — no dependency on dictionary files.

        When to call
        ------------
        After API data are available (post input parsing / warmup). Earlier calls may
        return an empty frame depending on the model & E+ version.

        Columns (typical)
        -----------------
        ["Kind", "MeterName", "Units"]

        Parameters
        ----------
        save_csv : bool, default False
            If True, also saves the raw API catalog CSV to `<out_dir>/api_catalog.csv`.

        Returns
        -------
        pandas.DataFrame
            The "METERS" section; empty DataFrame if the section is absent.

        Examples
        --------
        >>> meters = util.list_available_meters()
        >>> meters.query("MeterName.str.contains('Electricity', case=False)", engine='python').head()
        """
        import pandas as pd
        sections = self.api_catalog_df(save_csv=save_csv)
        df = sections.get("METERS", pd.DataFrame(columns=["Kind","MeterName","Units"]))
        return df

    def list_available_actuators(self, *, save_csv: bool = False):
        """
        Return the **runtime API catalog of actuators** as a pandas DataFrame.

        What this is
        ------------
        A small wrapper that extracts the "ACTUATORS" section from the runtime API
        catalog (`exchange.list_available_api_data_csv`). Use these rows to look up
        actuator **handles** during a run.

        When to call
        ------------
        After inputs are parsed / API data are ready (e.g., inside
        `callback_after_component_get_input` or after warmup). Earlier calls can be empty.

        Columns (typical)
        -----------------
        ["Kind", "ComponentType", "ControlType", "ActuatorKey", "Units"]

        Getting handles
        ---------------
        At an appropriate callback (when data are ready), resolve a handle with:
            `h = ex.get_actuator_handle(state, ComponentType, ControlType, ActuatorKey)`
        Then set values each timestep via:
            `ex.set_actuator_value(state, h, value)`

        Parameters
        ----------
        save_csv : bool, default False
            If True, also saves the raw API catalog CSV to `<out_dir>/api_catalog.csv`.

        Returns
        -------
        pandas.DataFrame
            The "ACTUATORS" section; empty DataFrame if the section is absent.

        Examples
        --------
        >>> acts = util.list_available_actuators()
        >>> # All schedule knobs you can drive
        >>> acts.query("ComponentType == 'Schedule:Compact' and ControlType == 'Schedule Value'").head()

        >>> # Example: find a specific fan/coil actuator family
        >>> acts[acts["ComponentType"].str.contains("Fan|Coil", case=False, na=False)].head()
        """
        import pandas as pd
        sections = self.api_catalog_df(save_csv=save_csv)
        df = sections.get("ACTUATORS", pd.DataFrame(columns=["Kind","ComponentType","ControlType","ActuatorKey","Units"]))
        return df

    def get_idf_object_types(self):
        """
        Scans an IDF file and returns a list of all Object Types present,
        sorted by how often they appear.
        """
        with open(self.idf, 'r', errors="ignore") as f:
            text = f.read()

        # 1. Remove comments (everything after !)
        text_no_comments = re.sub(r'!.*$', '', text, flags=re.MULTILINE)

        # 2. Find the start of every object
        # Pattern: Start of line, some text, then a comma or semicolon
        # This captures "Zone," or "Schedule:Compact,"
        pattern = r'^\s*([A-Za-z:\-]+)\s*[,;]'
        
        matches = re.findall(pattern, text_no_comments, flags=re.MULTILINE)
        
        # 3. Clean up and count
        types = [m.strip() for m in matches]
        counts = Counter(types)
        
        # Return as a list of tuples: [('Zone', 5), ('Schedule:Compact', 3)...]
        return counts.most_common()

    def extract_idf_objects(self, object_type):
        """
        Scans the IDF text for a specific object type and returns the names.
        Fast, no simulation required.
        """
        with open(self.idf, 'r', errors="ignore") as f:
            text = f.read()

        # Remove comments (!)
        text = re.sub(r'!.*$', '', text, flags=re.MULTILINE)

        # Regex to find objects like "Schedule:Compact,"
        # This is a simple parser; for complex IDFs, consider using the 'eppy' library.
        pattern = fr'(?i)^\s*{re.escape(object_type)}\s*,\s*(.*?)[,;]'
        
        matches = re.findall(pattern, text, flags=re.MULTILINE)
        
        # Clean up whitespace
        names = [m.strip() for m in matches]
        return names

    def patch_idf_entry(self, object_type: str, object_name: str, old_value: str, new_value: str, inplace: bool = False) -> bool:
        """
        Finds a specific IDF object by type and name, and replaces a specific string inside its block.
        This is a safe, general-purpose text updater that doesn't affect the rest of the file.
        """
        if not getattr(self, "idf", None) or not os.path.exists(self.idf):
            raise FileNotFoundError("No IDF set. Call set_model() before updating.")
            
        with open(self.idf, 'r', errors='ignore') as f:
            text = f.read()

        # Regex to isolate the specific object block.
        # Matches: ObjectType + comma + (optional comments) + ObjectName + (anything up to semicolon)
        pattern = re.compile(
            rf'(?i)(^[ \t]*{re.escape(object_type)}\s*,\s*(?:![^\n]*\n\s*)*{re.escape(object_name)}\s*[,;].*?;)', 
            re.MULTILINE | re.DOTALL
        )

        def replacer(match):
            block = match.group(1)
            # Replace the old string with the new string ONLY within this specific block
            new_block = block.replace(old_value, new_value)
            return new_block

        new_text, count = pattern.subn(replacer, text)

        if count == 0:
            print(f"Could not find '{object_type}' named '{object_name}' to patch.")
            return False

        # Determine where to save
        if inplace:
            out_file = self.idf
        else:
            base_name = os.path.basename(self.idf)
            new_name = base_name.replace(".idf", "_patched.idf")
            out_dir = getattr(self, 'out_dir', os.path.dirname(self.idf))
            out_file = os.path.join(out_dir, new_name)
            
            # Update utility state so the simulation uses the patched file
            self._orig_idf_path = getattr(self, '_orig_idf_path', self.idf) or self.idf
            self.idf = out_file
            self._patched_idf_path = out_file

        with open(out_file, 'w', encoding='utf-8') as f:
            f.write(new_text)

        print(f"Patched '{object_name}' ({object_type}): Replaced '{old_value}' -> '{new_value}'")
        return True

    def _calculate_polygon_area(self, vertices) -> float:
        """Calculates the area of a 3D planar polygon using vector cross products."""
        try:
            import numpy as np
        except ImportError:
            raise ImportError("numpy is required to calculate 3D polygon areas for thermal parameters.")

        if len(vertices) < 3: 
            return 0.0
            
        v = np.array([[pt.get('vertex_x_coordinate', 0), 
                       pt.get('vertex_y_coordinate', 0), 
                       pt.get('vertex_z_coordinate', 0)] for pt in vertices])
        area = 0.0
        v0 = v[0]
        for i in range(1, len(v) - 1):
            cross_prod = np.cross(v[i] - v0, v[i+1] - v0)
            area += 0.5 * np.linalg.norm(cross_prod)
        return area

    def _get_construction_resistance(self, epjson: dict, construction_name: str) -> float:
        """Estimates the unit thermal resistance (m2.K/W) of an E+ construction."""
        constructions = epjson.get("Construction", {})
        if construction_name not in constructions: 
            return 1.0 
            
        # This handles standard 1-layer constructions. For robust multi-layer, 
        # you would iterate through 'layer_2', 'layer_3', etc.
        layers = [constructions[construction_name].get("outside_layer", "")]
        materials = epjson.get("Material", {})
        nomass_materials = epjson.get("Material:NoMass", {})
        
        total_ru = 0.15 # Inside/outside air film resistance baseline
        
        for layer in layers:
            if layer in materials:
                thickness = materials[layer].get("thickness", 0.1)
                conductivity = materials[layer].get("conductivity", 1.0)
                total_ru += (thickness / conductivity)
            elif layer in nomass_materials:
                total_ru += nomass_materials[layer].get("thermal_resistance", 1.0)
                
        return total_ru

    def get_zone_thermal_parameters(self, eplus_dir: Optional[str] = None) -> dict:
        """
        Converts the current IDF to epJSON and extracts the explicit thermal 
        parameters (R, C, M, V, and boundaries) required for state-space 
        control laws prior to simulation execution.
        """
        import json
        import subprocess
        from pathlib import Path

        if not getattr(self, "idf", None) or not os.path.exists(self.idf):
            raise FileNotFoundError("No IDF set. Call set_model() before extracting parameters.")

        # Determine EnergyPlus directory
        if eplus_dir is None:
            eplus_dir = os.environ.get("ENERGYPLUSDIR", "")
            
        idf_path = Path(self.idf)
        epjson_path = idf_path.with_suffix(".epJSON")
        
        # 1. Convert IDF to epJSON
        converter = os.path.join(eplus_dir, "ConvertInputFormat")
        if not os.path.exists(converter):
            # Fallback to system path if ENERGYPLUSDIR isn't set perfectly
            converter = "ConvertInputFormat" 
            
        try:
            subprocess.run([converter, str(idf_path)], check=True, capture_output=True)
        except subprocess.CalledProcessError as e:
            print(f"Error converting IDF to epJSON: {e.stderr.decode()}")
            return {}

        with open(epjson_path, "r", encoding="utf-8") as f:
            epjson = json.load(f)

        # --- Thermophysical Constants ---
        RHO_AIR = 1.204 # kg/m3
        CP_AIR = 1006.0 # J/(kg.K)
        H_INT = 3.0     # W/(m2.K)

        zones_data = {}
        surface_to_zone = {}
        
        # 2. Initialize Zone Data
        if "Zone" in epjson:
            for z_name, z_info in epjson["Zone"].items():
                c_height = z_info.get("ceiling_height", 3.0)
                if c_height == "autocalculate": 
                    c_height = 3.0
                    
                zones_data[z_name] = {
                    "V_room": z_info.get("volume", 0.0),
                    "_ceiling_height": c_height,
                    "_floor_area": 0.0,
                    "M_air": 0.0,
                    "C_air": 0.0,
                    "C_mass": 0.0,
                    "R_int": 0.0,
                    "boundaries": []
                }

        surfaces = epjson.get("BuildingSurface:Detailed", {})
        for s_name, s_info in surfaces.items():
            surface_to_zone[s_name.upper()] = s_info.get("zone_name")

        # 3. Process Boundaries
        for s_name, s_info in surfaces.items():
            zone_name = s_info.get("zone_name")
            if zone_name not in zones_data: 
                continue
            
            boundary_cond = s_info.get("outside_boundary_condition", "").lower()
            surf_type = s_info.get("surface_type", "").lower()
            
            # Calculate Area & Unit Resistance
            area = self._calculate_polygon_area(s_info.get("vertices", []))
            if surf_type == "floor": 
                zones_data[zone_name]["_floor_area"] += area
                
            r_unit = self._get_construction_resistance(epjson, s_info.get("construction_name"))
            r_absolute = r_unit / area if area > 0 else float('inf')
            
            # Determine target entity
            target_entity = "Environment"
            if boundary_cond in ["surface", "zone"]:
                adj_surf = s_info.get("outside_boundary_condition_object", "").upper()
                target_entity = surface_to_zone.get(adj_surf, "Unknown Zone")
            elif boundary_cond == "ground":
                target_entity = "Ground"

            zones_data[zone_name]["boundaries"].append({
                "surface_name": s_name,
                "type": surf_type,
                "boundary_condition": boundary_cond,
                "target": target_entity,
                "Area_m2": round(area, 2),
                "Ru_unit_resistance": round(r_unit, 4),
                "R_absolute_K_W": round(r_absolute, 4)
            })

        # 4. Finalize Capacitance and Resistance 
        for z_name, data in zones_data.items():
            # Estimate volume if autocalculated
            if data["V_room"] == "autocalculate" or data["V_room"] == 0:
                data["V_room"] = data["_floor_area"] * data["_ceiling_height"]
                
            data["M_air"] = round(data["V_room"] * RHO_AIR, 2)
            data["C_air"] = round(data["M_air"] * CP_AIR, 2)
            
            # Mass node heuristic estimations
            A_mass_est = data["_floor_area"] * 2.0 
            
            if A_mass_est > 0:
                data["R_int"] = round(1.0 / (H_INT * A_mass_est), 4)
                data["C_mass"] = round(data["_floor_area"] * 100000, 2) 
            else:
                data["R_int"] = float('inf')
                data["C_mass"] = 0.0

            # Remove temporary calculation variables
            del data["_ceiling_height"]
            del data["_floor_area"]

        return zones_data
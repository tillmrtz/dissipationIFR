#!/Users/u302042/miniconda3/envs/userexperience/bin/python
"""
load_and_convert.py
-------------------
CLI script to load Seaglider basestation files, convert them to OG1 format,
compute vertical velocity, and save the result as a NetCDF file.

The --data_dir argument is mandatory and can point to two different structures:

  1. Mission directory (*.nc files directly inside):
         /data/103/20070218/p1030001.nc  p1030002.nc  ...
     → Loads files directly, no interactive selection needed.

  2. Root directory (glider_sn/mission/*.nc structure):
         /data/
             103/
                 20070218/*.nc
                 20090223/*.nc
             005/
                 20080606/*.nc
     → Launches interactive selection (widget in Jupyter, prompts in terminal).
     → With --convert_all: converts every discovered mission without interaction.

Usage examples
--------------
# Mission folder directly (no interaction):
    python load_and_convert.py --data_dir /data/103/20070218

# Root folder — interactive glider/mission selection:
    python load_and_convert.py --data_dir /data

# Root folder — convert ALL missions automatically:
    python load_and_convert.py --data_dir /data --convert_all

# Convert all, custom output root, overwrite existing files:
    python load_and_convert.py --data_dir /data --convert_all --output_dir /results --overwrite
"""

import argparse
import os
import pathlib
import sys
import numpy as np

# ---------------------------------------------------------------------------
# Core conversion — operates on a single resolved mission
# ---------------------------------------------------------------------------

def convert_mission(mission_path, glider_id, mission_id, end_profile,
                     output_dir, overwrite, tools, variables, convertOG1, writers, readers):
    """Load, convert, and save one mission. Returns True on success.
    
    Parameters:
    -----------
    mission_path (Path): Path to the mission folder containing *.nc files.
    glider_id (str): Glider serial number (e.g., '103').
    mission_id (str): Mission date string (e.g., '20070218').
    end_profile (int): Last profile/dive index to load.
    output_dir (Path | None): Directory to save the output NetCDF file. If None, saves in the mission folder.
    overwrite (bool): Whether to overwrite existing output files.
    tools, variables, convertOG1, writers, readers: Modules/functions for processing.

    Returns:
    --------
    bool: True if conversion succeeded, False if skipped due to existing output.
    """

    print(f"\n{'='*60}")
    print(f"Glider  : {glider_id}")
    print(f"Mission : {mission_id}")
    print(f"Path    : {mission_path}")
    print(f"Profiles: 1 → {end_profile}")
    print(f"{'='*60}")

    out_dir = pathlib.Path(output_dir) if output_dir else pathlib.Path(mission_path)
    out_dir.mkdir(parents=True, exist_ok=True)
    dataset_path = out_dir / "all_data_OG1.nc"

    if dataset_path.exists():
        if overwrite:
            print(f"Overwriting existing file: {dataset_path}")
            dataset_path.unlink()
        else:
            print(f"Skipping — output already exists (use --overwrite to replace):\n  {dataset_path}")
            return False

    print("Loading basestation files...")
    datasets = readers.load_basestation_files(
        str(mission_path) + "/",
        start_profile=1,
        end_profile=end_profile,
    )

    print("Converting to OG1 format...")
    ds, var_list = convertOG1.convert_to_OG1(datasets)

    ds.attrs["Glider"]  = glider_id
    ds.attrs["Mission"] = mission_id

    print("Computing vertical velocity...")
    w_meas = tools.calc_vertical_velocity(ds.TIME.values, ds.DEPTH.values)
    ds["W_MEAS"]       = (("N_MEASUREMENTS",), w_meas)
    ds["W_MEAS"].attrs = variables["W_MEAS"]["attributes"]

    print(f"Saving to: {dataset_path}")
    writers.save_dataset(ds, dataset_path)
    print("Done.")
    return True


# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------

def parse_args():
    parser = argparse.ArgumentParser(
        description="Load Seaglider data, convert to OG1 format, and save as NetCDF.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--data_dir",
        type=pathlib.Path,
        required=True,
        help=(
            "Path to either: (1) a mission folder containing *.nc files directly, "
            "or (2) a root folder with glider_sn/mission/*.nc structure."
        ),
    )
    parser.add_argument(
        "--output_dir",
        type=pathlib.Path,
        default=None,
        help=(
            "Directory where the output NetCDF file(s) are saved. "
            "For --convert_all, each mission is saved under output_dir/glider/mission/. "
            "Defaults to the mission folder itself."
        ),
    )
    parser.add_argument(
        "--end_profile",
        type=int,
        default=None,
        help=(
            "Last profile/dive index to load. "
            "Defaults to the maximum dive number found in the folder."
        ),
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        default=False,
        help="Overwrite output file(s) if they already exist.",
    )
    parser.add_argument(
        "--convert_all",
        action="store_true",
        default=False,
        help=(
            "Convert every glider/mission found under data_dir without interaction. "
            "Only valid for root directories (case 2)."
        ),
    )
    return parser.parse_args()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    args = parse_args()

    # Imports here so --help works without loading heavy deps
    from dissipationIFR import tools, utilities
    from dissipationIFR.config import variables
    from seagliderOG1 import convertOG1, writers, readers

    data_dir = args.data_dir.resolve()
    if not data_dir.exists():
        sys.exit(f"Error: data_dir does not exist: {data_dir}")

    convert_kwargs = dict(
        overwrite=args.overwrite,
        tools=tools,
        variables=variables,
        convertOG1=convertOG1,
        writers=writers,
        readers=readers,
    )

    # ------------------------------------------------------------------ #
    # Case 1: mission directory — direct load, no interaction            #
    # ------------------------------------------------------------------ #
    if utilities._is_mission_dir(data_dir, readers):
        if args.convert_all:
            print("Warning: --convert_all has no effect when data_dir is a mission folder.")

        mission_path = data_dir
        parts        = mission_path.parts
        mission_id   = parts[-1]
        glider_id    = parts[-2] if len(parts) >= 2 else "unknown"
        n_dives      = args.end_profile or utilities.get_mission_dives(mission_path)

        if n_dives is None:
            sys.exit("Error: could not determine end_profile. Pass --end_profile explicitly.")

        convert_mission(mission_path, glider_id, mission_id, n_dives,
                         args.output_dir, **convert_kwargs)

    # ------------------------------------------------------------------ #
    # Case 2: root directory                                              #
    # ------------------------------------------------------------------ #
    else:
        discovered = utilities.discover_all_missions(data_dir)
        if not discovered:
            sys.exit(f"Error: no valid glider/mission/*.nc structure found in: {data_dir}")

        if args.convert_all:
            # ----------------------------------------------------------
            # Batch mode: convert every mission, no interaction
            # ----------------------------------------------------------
            all_missions = [
                {**m, 'glider': glider}
                for glider, missions in discovered.items()
                for m in missions
            ]
            print(f"Found {len(all_missions)} mission(s) — converting all...\n")
            succeeded, skipped, failed = 0, 0, 0

            for m in all_missions:
                out_dir = (pathlib.Path(args.output_dir) / m['glider'] / m['mission']
                           if args.output_dir else None)
                end_profile = args.end_profile or m['dives']
                try:
                    ok = convert_mission(m['path'], m['glider'], m['mission'],
                                          end_profile, out_dir, **convert_kwargs)
                    succeeded += ok
                    skipped   += not ok
                except Exception as e:
                    print(f"ERROR converting {m['glider']}/{m['mission']}: {e}")
                    failed += 1

            print(f"\n{'='*60}")
            print(f"Batch complete — {succeeded} converted, {skipped} skipped, {failed} failed.")

        else:
            # ----------------------------------------------------------
            # Interactive mode: pick one mission
            # ----------------------------------------------------------
            from dissipationIFR import interactive
            if utilities._in_jupyter():
                selected = interactive.interactive_glider_selection(data_dir=data_dir)
                if selected["path"] is None:
                    sys.exit("No glider mission selected. Exiting.")
            else:
                selected = interactive.interactive_cli(data_dir, discovered)

            mission_path = pathlib.Path(selected["path"])
            end_profile  = args.end_profile or selected["dives"]
            convert_mission(mission_path, selected["glider"], selected["mission"],
                             end_profile, args.output_dir, **convert_kwargs)


if __name__ == "__main__":
    main()
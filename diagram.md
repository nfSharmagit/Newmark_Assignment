# Assignment Flow (Mermaid)

This file contains a Mermaid flowchart for the `Newmark_Assignment` pipeline implemented in `assignment.py`, a short mapping of nodes to functions in the code, edge cases, and instructions for rendering.

```mermaid
flowchart TD
  Start([Start])
  InitQGIS[Init QGIS app\nset prefix & CRS (EPSG:2240)]
  LoadLayers[Load layers from\n`layer_name_path` (shapefiles)]
  ReadCSV[Read CSV\n`Input_Files/Atlanta_Addresses_Test.csv`]
  ForEach[Loop: for each address]
  Geocode[Geocode address\n`geocode_address()`\n(geopy Nominatim → HTTP Nominatim → Google fallback)]
  GeoFail[Geocode failed → append result (error: geocoding failed)]
  CheckLoaded[Check loaded QGIS layers\nsearch parcel_id / stories / build_id\n`find_attribute_value_via_laoded_layer()`]
  QueryArc[Query ARC_SERVICES sequentially\n`query_arcgis_service()`]
  AllFound[All values found → process_output()]
  ProcessOutput[process_output()\ncreate BIN (`create_bin()` )\nappend successful result]
  NotFound[Parcel_ID still missing → process_output() (error: Parcel_ID not found)]
  # Assignment Flow (Mermaid) — Numbered Sequence

  This file shows a Mermaid flowchart for the `Newmark_Assignment` pipeline in `assignment.py` with explicit sequence numbers for each step. Use this to quickly map the runtime order and function responsibilities.

  ```mermaid
  flowchart TD
    Start([Start])
    N1["1. Init QGIS\nQgsApplication() & set CRS (EPSG:2240)"]
    N2["2. Load Layers\n`load_layers()` using `layer_name_path`"]
    N3["3. Read CSV\nreadcsv_and_find_attributes(csv_input)"]
    N4["4. Loop: for each address\niterate addresses list"]
    N5["5. Geocode address\n`geocode_address()`\n(Nominatim → HTTP fallback → `geocode_google()`)"]
    N6["5.1 Geocode failed\nappend result (error: geocoding failed) & continue"]
    N7["6. Check loaded QGIS layers\n`find_attribute_value_via_laoded_layer()`\n(search parcel_id, stories, build_id)"]
    N8["7. Query ArcGIS services\n`query_arcgis_service()` sequentially (ARC_SERVICES)"]
    N9["8. Process output\n`process_output()` → `create_bin()` → append result"]
    N10["9. Save results\n`save_results_to_csv()` to Output_Files/output_results.csv"]
    N11["10. Exit QGIS\nqgs.exitQgis()"]
    End([End])

    Start --> N1 --> N2 --> N3 --> N4
    N4 --> N5
    N5 -->|5a: failed| N6 --> N4
    N5 -->|5b: success| N7
    N7 -->|6a: all found| N9 --> N4
    N7 -->|6b: missing any| N8
    N8 -->|7a: all found| N9
    N8 -->|7b: still missing| N9
    N4 -->|all processed| N10 --> N11 --> End

    %% Helper reference (for quick lookup)
    subgraph Helpers [Helper functions / utilities]
      GB[create_bin(parcel_id, build_id)]
      TG[to_project_geom(lon,lat)]
      GA[geocode_address() / geocode_google()]
      QS[query_arcgis_service()]
      EV[extract_value_from_attributes()\nextract_value_from_features()]
      FL[find_attribute_value_via_laoded_layer()]
    end

    N5 --- GA
    N7 --- FL
    N7 --- EV
    N8 --- QS
    N9 --- GB
    N7 --- TG
  ```

  ## Numbered Node → Code mapping
  1. `Init QGIS` → QGIS setup at top of `assignment.py`: `QgsApplication(...)`, `qgs.initQgis()`, `qgis_project.setCrs(...)`.
  2. `Load Layers` → `load_layers(project_path, layer_name, layer_path)` and `layer_name_path` used in `__main__`.
  3. `Read CSV` → `readcsv_and_find_attributes(csv_input, layer_name_path)` reads the CSV and prepares the address list.
  4. `Loop` → per-address iteration inside `readcsv_and_find_attributes()`.
  5. `Geocode` → `geocode_address()` with fallbacks to HTTP Nominatim and `geocode_google()`.
  5.1 `Geocode failed` → record an error and continue to the next address.
  6. `Check loaded QGIS layers` → `find_attribute_value_via_laoded_layer()` which uses `to_project_geom()` and `extract_value_from_features()`.
  7. `Query ArcGIS services` → `query_arcgis_service()` called for each service in `ARC_SERVICES` and `extract_value_from_attributes()` to find missing values.
  8. `Process output` → `process_output()` that creates the BIN (`create_bin()`) and appends results.
  9. `Save results` → `save_results_to_csv(results, csv_output)`.
  10. `Exit QGIS` → `qgs.exitQgis()`.

  ## Edge cases and notes
  - Empty/missing address rows are skipped early in the loop.
  - Geocoding failure path (5a) records a result with error and skips further lookups for that address.
  - Partial attribute availability: the script tries local loaded layers first (6), then ArcGIS services (7) sequentially.
  - Remote service failures/timeouts: `query_arcgis_service()` returns `None` and the code proceeds to the next service.
  - All geometry intersection uses transformed coordinates via `to_project_geom()` to match layer/project CRS.

  ## How to render
  - Paste the Mermaid block into a Markdown file with Mermaid support or open https://mermaid.live and paste the code to render.
  - If you want a PNG/SVG exported, I can provide PowerShell commands (requires Node.js + npm) or export it here if Node tooling is available.

  ---
  Updated `diagram.md` with a numbered, step-by-step Mermaid flowchart for `assignment.py`.

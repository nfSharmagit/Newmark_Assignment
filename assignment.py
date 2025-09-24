import csv
import time 
from qgis.PyQt.QtCore import QVariant
from qgis.core import (
    QgsProject,
    QgsCoordinateReferenceSystem,
    QgsCoordinateTransform,
    QgsPointXY,
    QgsGeometry,
    QgsVectorLayer,
    QgsField,
    QgsFeature,
    QgsApplication
)
import requests
import os
from geopy.geocoders  import Nominatim
import hashlib
from tqdm import tqdm 

#region GLOBAL VARIABLES----------

# Supply path to QGIS install location
QGIS_PREFIX_PATH = r'C:/Program Files/QGIS 3.40.10/apps/qgis'

# Create a reference to the QgsApplication. Setting the second argument to False disables the GUI.
qgs = QgsApplication([], False)
qgs.setPrefixPath(QGIS_PREFIX_PATH, True)

#initialize the QGIS application
qgs.initQgis()

qgis_project = QgsProject.instance()
#"EPSG:4326" is WGS84
# "EPSG:2240" is NAD83 / Georgia West (ftUS)    
qgis_project.setCrs(QgsCoordinateReferenceSystem("EPSG:2240"))  # Set project CRS to EPSG:2240 (NAD83 / Georgia West)

# ArcGIS services to query
ARC_SERVICES = [
    # City of Atlanta TaxParcel layer (MapServer layer 0)
    "https://gis.atlantaga.gov/dpcd/rest/services/AdministrativeArea/TaxParcel/MapServer/0",
    # Fulton County/ArcGIS-hosted TaxParcel FeatureServer (public/hosted service)
    "https://services5.arcgis.com/WgCOhpTBP3tb7eDk/arcgis/rest/services/TaxParcel/FeatureServer/0",
    # Direct layer URL (building footprints):
    "https://gis.atlantaga.gov/dpcd/rest/services/OpenDataService1/MapServer/10"
]

# Fields we will search for (case-insensitive)
POSSIBLE_PARCEL_ID_KEYS = ["PARCELID","PARCEL_ID","APN","PIN","PARCEL","APN_ID","PIN_NUM","PARC_NUM","ParcelID","parcel_id","ParcelId","APN", "APN_ID", "APN ID"]
POSSIBLE_STORY_KEYS = ["STORIES","NUM_STORIES","BldgStories","BLDG_STORY","STORY","Story","stories","num_stories","bldg_stories"]
POSSIBLE_BUILD_ID_KEYS  = ["BIN", "STRUCTUREID", "STRUCTURE_ID", "STRUCT_ID","BLD_ID","BUILDINGID","BUILDING_ID","BUILDINGID","BUILDING_ID","BuildingId","building_id","BuildingID"]

# Define paths and parameters
project_path = "C:/Users/sarni/Desktop/Projects/PyQGIS_Projects/Newmark_Assignment/"
# Input CSV with 'address' column
csv_input = r"C:/Users/sarni/Desktop/Projects/PyQGIS_Projects/Newmark_Assignment/Input_Files/Atlanta_Addresses_Test.csv"    
# Dictionary of layers in QGIS
layer_name_path = {"Tax_Parcels":"Open_Data_Recources/Atlanta_Tax_Parcels/Tax_Parcels.shp",
                   "Structure_Footprints": "Open_Data_Recources/Atlanta_Structure_Footprints/Structure_Footprints.shp"}  
       
csv_output = r"C:/Users/sarni/Desktop/Projects/PyQGIS_Projects/Newmark_Assignment/Output_Files/output_results.csv"

#endregion GLOBAL VARIABLES --------

# region HELPER FUNCTIONS ---------

def create_bin(parcel_id, build_id='NO_BLD'):  
    base = f"{parcel_id}|{build_id}"
    bin_val = 'ATL-BIN-' + hashlib.sha1(base.encode()).hexdigest()[:10].upper()
    return bin_val

# Load parcel layers into QGIS
def load_layers(project_path, layer_name, layer_path):

    path_to_shape_file = project_path + layer_path 

    layer = QgsVectorLayer(path_to_shape_file, layer_name, 'ogr')
    if not layer.isValid():
        print(f'{layer_name} layer failed to load !')
    else:
        qgis_project.addMapLayer(layer)
        print(f'{layer_name} layer loaded successfully!')

# Convert geocoded point to QGIS geometry in project CRS 
def to_project_geom(loaded_layer, lon, lat):
    # Create point in WGS84
    wgs84 = QgsCoordinateReferenceSystem("EPSG:4326")
    layer_crs = loaded_layer.crs()
    transform = QgsCoordinateTransform(wgs84, layer_crs, qgis_project)
    
    # Check if layer CRS matches project CRS
    # if loaded_layer.crs().authid() == qgis_project.crs().authid():
    #    print("Layer CRS matches project CRS.")

    point = QgsPointXY(lon, lat)
    point_proj = transform.transform(point)
    return QgsGeometry.fromPointXY(point_proj)

# Geocode the address using Nominatim or Google Geocoding API

def geocode_address(address):
    """Try geopy.Nominatim if available; otherwise use direct Nominatim HTTP API."""
    try:
        # try geopy Nominatim first
        geolocator = Nominatim(user_agent="qgis_parcel_lookup")
        loc = geolocator.geocode(address, timeout=10)
        if loc:
            return float(loc.latitude), float(loc.longitude)
    except Exception:
        print("Geopy Nominatim failed, trying direct HTTP API...")
        pass

    # fallback: direct HTTP call to Nominatim
    try:
        url = "https://nominatim.openstreetmap.org/search"
        params = {"q": address, "format": "json", "limit": 1}
        response = requests.get(url, params=params, headers={"User-Agent": "QGIS Parcel Lookup"}, timeout=10)
        response.raise_for_status()
        geo_data = response.json()

        if geo_data:
            lat = float(geo_data[0]["lat"])
            lon = float(geo_data[0]["lon"])

            return lat, lon
           
    except Exception as e:
        print("Direct Nominatim HTTP API failed.")
    
    return None, None

# Example function for Google Geocoding API (if needed)
def geocode_google(address):
    api_key = "AIzaSyCO27K3CsCT84rj63xTucW7T6kk4bZ9HUE"
    url = "https://maps.googleapis.com/maps/api/geocode/json"
    params = {'address': address, 'key': api_key}
    r = requests.get(url, params=params)
    r.raise_for_status()
    data = r.json()
    if data['status'] != 'OK':
        raise ValueError(data['status'])
    result = data['results'][0]
    return result['geometry']['location']['lat'], result['geometry']['location']['lng']

#endregion General Helper Functions

# region ARC Services Helpers
# Extract Values from Attributes----------
def extract_value_from_attributes(attributes, possible_keys):
    attribute_value = None
    
    # find value for possible parcel_id keys
    for attr_name in attributes.keys():
        for key in possible_keys:
            if attr_name.lower() == key.lower():
                attribute_value = attributes.get(attr_name)
                break

    return attribute_value

# Query an ArcGIS/FeatureServer/MapServer layer for features
def query_arcgis_service(service_url, lat, lon, try_geojson=True):
    """
    Query an ArcGIS/FeatureServer/MapServer layer for features intersecting (lon,lat).
    Returns a dict with 'attributes' and optionally 'geometry' (GeoJSON geometry).
    """
    query_url = service_url.rstrip("/") + "/query"
    params = {
        "geometry": f"{lon},{lat}",
        "geometryType": "esriGeometryPoint",
        "inSR": "4326",
        "spatialRel": "esriSpatialRelIntersects",
        "outFields": "*",
        "returnGeometry": "true",
        "f": "geojson" if try_geojson else "json",
    }

    try:
        r = requests.get(query_url, params=params, timeout=15)
        r.raise_for_status()
        data = r.json()
        # ArcGIS Services sometimes return GeoJSON when f=geojson or a JSON with 'features'
        if not data:
            return None
        # If GeoJSON-style
        if "features" in data and len(data["features"]) > 0:
            feat = data["features"][0]
            return {"attributes": feat.get("properties", {}), "geometry": feat.get("geometry", None), "raw": data}
        # If ArcGIS JSON (not geojson) and has 'features' list
        if "features" in data and len(data["features"]) > 0:
            feat = data["features"][0]
            return {"attributes": feat.get("attributes", {}), "geometry": feat.get("geometry", None), "raw": data}
    except Exception as e:
        # Most services support these simple queries; skip if one fails.
        print("Service query failed:", service_url, e)
        return None
    return None

#endregion ARC Services Helper

# region QGIS Loaded Layer Helpers

# Find Attribute Value via Loaded Layer 
def find_attribute_value_via_laoded_layer(loaded_layer, lat, lon, attribute_name, attribute_value, possible_keys):
    """Find parcel ID and stories by spatial intersection."""
    
    address_geom = to_project_geom(loaded_layer, lon, lat)
     
# We will be using the exact geometry for intersection. We could also use:  
# 1. Rectangle for quick pre-filtering -> address_geom.boundingBox() 
# 2. Turn a bounding box into a polygon geometry if required
# bbox = address_geom.boundingBox()
# bbox_polygon = QgsGeometry.fromRect(bbox)
# 3. Buffer around point (e.g., 10 meters) if needed
    search_buffer = address_geom.buffer(10, 5)  # 10 meters buffer

    for feature in loaded_layer.getFeatures():
        if feature.geometry().intersects(search_buffer):
            #  parcel_id = feature["ParcelId"] if "ParcelId" in feature.fields().names() else feature.attribute("ParcelId")
            attribute_value = extract_value_from_features(feature, possible_keys)
            
            if (attribute_value != None) and (attribute_value != '' or attribute_value != ' ' or attribute_value != "NULL" or attribute_value != "NaN"):
                print(f"\033[92mFound {attribute_name} --> {attribute_value} in loaded layer: {loaded_layer}\033[0m")
                break   
    
    return attribute_value

# Extract Values from Features
def  extract_value_from_features(feature, possible_keys):
    attribute_value = None
    
    # find value for possible parcel_id keys
    for field_name in feature.fields().names():
        for key in possible_keys:
            if (field_name.lower() == key.lower()) and (feature[field_name] != None):
                attribute_value = feature[field_name]
                break
        if attribute_value != None: 
            break
        
    return attribute_value

#endregion QGIS Loaded Layer Helper

#endregion HELPER FUNCTIONS ---------

def readcsv_and_find_attributes(csv_path, layer_name_path):
    results = []
    # Read addresses from CSV
    with open(csv_path, newline='', encoding='utf-8') as csvfile:
        addresses = []
        reader = csv.DictReader(csvfile)
        for row in reader:
            address = row.get("address") or row.get("Address")
            addresses.append(address)
        
        with tqdm(total=len(addresses), unit="addr", ncols=100, desc="Processing All Addresses") as pbar:
            for address in addresses:
                pbar.set_description(f"\n\033[93mProcessing Address: {addresses.index(address)+1}/{len(addresses)}\033[0m")
                addr_start = time.time()
            
                if not address:
                    addr_elapsed = time.time() - addr_start
                    pbar.set_description(f"Processed {addresses.index(address)+1}/{len(addresses)} (Last: {addr_elapsed:.2f}s) - \033[91mSkipped empty address\033[0m ")
                    pbar.update(1)
                    continue
                try:
                    # region Step 1: Geocode the address to get lat/lon
                    parcel_id = None
                    stories = None
                    build_id = None
                    bin_val = None

                    print(f"\n\033[93mGeocoding address:\033[0m - {address}")
                    lat, lon = geocode_address(address)

                    if lat is None or lon is None:
                        # try Google Geocoding as fallback
                        print("\nNominatim geocoding failed, trying Google Geocoding...")
                        lat, lon = geocode_google(address)

                    if lat is None or lon is None:
                        print(f"\033[91mGeocoding failed for address: {address}\033[0m")
                        results.append({"address": address, "lat": lat, "lon": lon, "parcel_id": parcel_id, "stories": stories, "build_id": build_id, "bin":None, "error": "geocoding failed"})
                        addr_elapsed = time.time() - addr_start
                        pbar.set_description(f"Processed {addresses.index(address)+1}/{len(addresses)} (Last: {addr_elapsed:.2f}s) - Geocoding failed")
                        pbar.update(1)
                        continue
                    # endregion Step 1: Geocode the address to get lat/lon

                    print(f"\033[92mGeocoded --> lat={lat}, lon={lon} \033[0m")
                    # region Step 2: Query for Attributes

                    # region Step 2.1: Using Loaded Layers in QGIS\n")
                    print ("\n\033[93mStep 2.1: Checking loaded layers in QGIS for missing information\033[0m")
                    
                    try:
                        loaded_layers = []
                        for layer_name in layer_name_path.keys():
                            loaded_layers.append(qgis_project.mapLayersByName(layer_name))
                    except Exception as e:
                        print(f"Error accessing layers '{layer_name}': {e}")
                    
                    try:
                        if loaded_layers == []:
                            raise Exception("No layers loaded in the project.")
                        
                        print("\033[92mLoaded layers:\033[0m", loaded_layers)
                    
                        if parcel_id == None or parcel_id == '' or parcel_id == ' ' or parcel_id == "NULL" or parcel_id == "NaN":
                            print("\nTrying to find Parcel_ID using loaded layer.")
                            
                            for loaded_layer in loaded_layers:
                                parcel_id = find_attribute_value_via_laoded_layer(loaded_layer[0], lat, lon, 'Parcel_ID', parcel_id, POSSIBLE_PARCEL_ID_KEYS) 
                                if (parcel_id != None) and (parcel_id != '' or parcel_id != ' ' or parcel_id != "NULL" or parcel_id != "NaN"):                                   
                                    break
                                else:
                                    print(f"\033[91mNo Parcel_ID found in the loaded layer:\033[0m {loaded_layer}")
                                
                        if stories == None or stories == '' or stories == ' ' or stories == "NULL" or stories == "NaN":
                            print("\nTrying to find Stories using loaded layer.")
                            for loaded_layer in loaded_layers:
                                stories = find_attribute_value_via_laoded_layer(loaded_layer[0], lat, lon, 'Stories', stories, POSSIBLE_STORY_KEYS)          
                                if (stories != None) and (stories != '' or stories != ' ' or stories != "NULL" or stories != "NaN"):
                                    break
                                else:
                                    print(f"\033[91mNo Stories found in the loaded layer:\033[0m {loaded_layer}")
                    
                        if build_id == None or build_id == '' or build_id == ' ' or build_id == "NULL" or build_id == "NaN":
                            print("\nTrying to find Build_ID using loaded layer.")
                            for loaded_layer in loaded_layers:
                                build_id = find_attribute_value_via_laoded_layer(loaded_layer[0], lat, lon, 'Build_Id', build_id, POSSIBLE_BUILD_ID_KEYS)
                                if (build_id != None) and (build_id != '' or build_id != ' ' or build_id != "NULL" or build_id != "NaN"):
                                    break
                                else:
                                    print(f"\033[91mNo Build_ID found in the loaded layer:\033[0m {loaded_layer}")                     
                        if (
                            (parcel_id != None) and (parcel_id != '' or parcel_id != ' ' or parcel_id != "NULL" or parcel_id != "NaN") and
                            (stories != None) and (stories != '' or stories != ' ' or stories != "NULL" or stories != "NaN") and
                            (build_id != None) and (build_id != '' or build_id != ' ' or build_id != "NULL" or build_id != "NaN")
                            ):
                            print("Found all values on the Loaded Layers in QGIS")
                            process_output(results, addresses, address, pbar, addr_start, parcel_id, stories, build_id, lat, lon)
                            continue   
                                
                    except Exception as e:
                        print(e)
                    
                    print(f"\n\033[93mProcessed Output from Loaded Layers:\033[0m \n{address} → Parcel ID: {parcel_id}, Stories: {stories}, Build_ID: {build_id}")
                    # endregion Step 2.1: Using Loaded Layers in QGIS
                    
                    # region Step 2.2: Using Arc Services to find missing information \n")
                    try:                       
                        counter = 1
                        print ("\n\033[93mStep 2.2: Querying ArcGIS services for information\033[0m")
                        for svc in ARC_SERVICES:
                            if counter > len(ARC_SERVICES):
                                break 
                            
                            print("\nQuerying service #", counter , ": ", svc)

                            svc_response = query_arcgis_service(svc, lat, lon, try_geojson=True)

                            if not svc_response:
                                # try with geo_json=False fallback
                                svc_response = query_arcgis_service(svc, lat, lon, try_geojson=False)
                                
                            if not svc_response:
                                print("No response found on #", counter ," service.")
                                counter += 1
                                continue
                            else:
                                print("\033[92mService response found on #", counter ," service.\033[0m")

                            attributes = svc_response.get("attributes", {})

                            if parcel_id == None or parcel_id == '' or parcel_id == ' ' or parcel_id == "NULL" or parcel_id == "NaN":
                                parcel_id = extract_value_from_attributes(attributes,POSSIBLE_PARCEL_ID_KEYS)
                                if (parcel_id != None) and (parcel_id != '' or parcel_id != ' ' or parcel_id != "NULL" or parcel_id != "NaN"):
                                    print(f"\033[92mFound parcel_id on service #{counter}:, Parcel_Id: {parcel_id}\033[0m")
                            
                            if stories == None or stories == '' or stories == ' ' or stories == "NULL" or stories == "NaN":
                                stories = extract_value_from_attributes(attributes,POSSIBLE_STORY_KEYS)
                                if (stories != None) and (stories != '' or stories != ' ' or stories != "NULL" or stories != "NaN"):    
                                    print(f"\033[92mFound stories on service #{counter}:, Stories: {stories}\033[0m")

                            if build_id == None or build_id == '' or build_id == ' ' or build_id == "NULL" or build_id == "NaN":
                                build_id = extract_value_from_attributes(attributes,POSSIBLE_BUILD_ID_KEYS)
                                if (build_id != None) and (build_id != '' or build_id != ' ' or build_id != "NULL" or build_id != "NaN"):    
                                    print(f"\033[92mFound build_id on service #{counter}:, Build_ID: {build_id}\033[0m")                          
                            if (
                                (parcel_id != None) and (parcel_id != '' or parcel_id != ' ' or parcel_id != "NULL" or parcel_id != "NaN") and
                                (stories != None) and (stories != '' or stories != ' ' or stories != "NULL" or stories != "NaN") and
                                (build_id != None) and (build_id != '' or build_id != ' ' or build_id != "NULL" or build_id != "NaN")
                            ):
                                print("Found all values on ARC Services")  

                            counter += 1

                        print(f"\n\033[93mProcessed Output after using Arc Services:\033[0m \n{address} → Parcel ID: {parcel_id}, Stories: {stories}, Build_ID: {build_id}")
                        
                    except Exception as e:
                        print(e)
                    
                    # endregion Step 2.2: Using Arc Services to find missing information
                    #endregion Step 2: Query for Attributes

                    #region Final Output        
                    process_output(results, addresses, address, pbar, addr_start, parcel_id, stories, build_id, lat, lon)
                    #endregion Final Output
                except Exception as e:
                    print(f"\033[91mError with {address}: {e}\033[0m")
                    continue

    return results 

def process_output(results, addresses, address, pbar, addr_start, parcel_id, stories, build_id, lat, lon):
    print(f"\n\033[92mFinal Processed Output:\033[0m \n{address} → Parcel ID: {parcel_id}, Stories: {stories}, Build_ID: {build_id}")

    if parcel_id != None: 
        bin_val = create_bin(parcel_id, build_id)
        results.append({"address": address, "lat": lat, "lon": lon, "parcel_id": parcel_id, "stories": stories, "build_id":build_id, "bin": bin_val,"error": None})     
    else:
        results.append({"address": address, "lat": lat, "lon": lon, "parcel_id": parcel_id, "stories": stories, "build_id":build_id, "bin": None,"error": "Parcel_ID not found"})

    addr_elapsed = time.time() - addr_start
    pbar.set_description(f"\n\033[92mProcessed {addresses.index(address)+1}/{len(addresses)} (Last: {addr_elapsed:.2f}s)\033[0m\n")
    pbar.update(1)       

def save_results_to_csv(results, output_csv):
    # Save results to CSV
    with open(output_csv, "w", newline='', encoding='utf-8') as outfile:
        fieldnames = ["address", "lat", "lon", "parcel_id", "stories", "build_id", "bin", "error"]
        writer = csv.DictWriter(outfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)


if __name__ == "__main__":
    
    # load each layer from the dictionary
    for layer_name, layer_path in layer_name_path.items():
        load_layers(project_path, layer_name, layer_path)
    
    # Start timer
    start_time = time.time()
    from qgis.core import QgsProcessingFeedback
    feedback = QgsProcessingFeedback()
    feedback.setProgress(100)

    results = readcsv_and_find_attributes(csv_input , layer_name_path )

   # process_csv_to_layer()

    save_results_to_csv(results, csv_output)

    print("Processing complete. Results saved to:", csv_output)
    elapsed = (time.time() - start_time) / 60
    print(f"\n⏱ Completed in {elapsed:.2f} minutes.")
    qgs.exitQgis()


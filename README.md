**ABSTRACT**

Urban data integration requires unique and stable building identifiers. This work presents an automated pipeline to create a BIN-like system for Atlanta addresses. 
By combining QGIS, ArcGIS REST services, and geocoding APIs, we generate reproducible unique IDs that link parcels, buildings, and addresses for improved urban analytics and planning.

In New York City, Building Identification Numbers (BIN) are used to uniquely identify buildings across datasets. Atlanta currently lacks a standardized BIN system, complicating efforts to link tax parcels, building footprints, and civic addresses. This project aims to develop an automated workflow using QGIS, ArcGIS REST services, and Python scripts to create BIN-like IDs for Atlanta addresses. The approach enables consistent referencing of properties for planning, assessment, and emergency response.

**ASSUMPTIONS**

- Parcel and building shapefiles or REST services are current and accurately aligned with Atlanta’s CRS (EPSG:2240).
- Geocoding returns accurate coordinates for input addresses.
- Parcels and buildings do not overlap ambiguously—each point corresponds to a single parcel.
- Parcel IDs and Building IDs are stable over time.


**REFERENCES**
1. City of Atlanta GIS Open Data Portal – https://gis.atlantaga.gov
2. Fulton County GIS Tax Parcel Services – https://services5.arcgis.com
3. QGIS Documentation – https://docs.qgis.org
4. ArcGIS REST API Documentation – https://developers.arcgis.com/rest
5. OpenStreetMap Nominatim API – https://nominatim.org/release-docs/latest
6. Google Maps Geocoding API – https://developers.google.com/maps/documentation/geocoding
7. NYC Department of Buildings – Building Identification Number (BIN) System


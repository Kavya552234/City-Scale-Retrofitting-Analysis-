# City-Scale Retrofitting Analysis for Ahmedabad

<p align="center">
<img src="Assets/images/swa_consultancy_logo.png" width="250">
</p>

## Research Internship
**Organization:** SWA Consultancy

**Duration:** June 2026 – July 2026

---

# Project Overview

Buildings account for a significant share of global energy consumption and greenhouse gas emissions. Improving the energy performance of existing buildings through **energy retrofitting** is one of the most effective strategies for reducing urban energy demand and operational carbon emissions.

This internship focuses on preparing **CityBES-compatible Urban Building Energy Modeling (UBEM)** datasets for Ahmedabad. The prepared datasets will later be used to perform **baseline energy simulations**, evaluate **Energy Conservation Measures (ECMs)**, and estimate potential **energy savings** and **carbon emission reductions** for residential buildings.

---

# Understanding Building Energy Retrofitting

# Building Energy Fundamentals

Before beginning the practical implementation, the initial phase of the internship focused on understanding the theoretical principles of building energy systems, energy-efficient design, and urban retrofitting.

These concepts provided the engineering foundation required for preparing Urban Building Energy Modeling (UBEM) datasets and performing city-scale energy simulations.

The following topics were studied:

## Building Energy Consumption

Buildings consume energy primarily for:

- Space cooling
- Space heating
- Lighting
- Ventilation
- Domestic hot water
- Internal electrical equipment

Understanding how different components contribute to total energy consumption is essential before evaluating retrofit strategies.

---

## Thermal Comfort

Thermal comfort refers to maintaining indoor conditions that are comfortable for occupants while minimizing energy consumption.

Major factors affecting thermal comfort include:

- Air temperature
- Humidity
- Solar radiation
- Air movement
- Building envelope properties

---

## Building Envelope

The building envelope acts as the boundary between indoor and outdoor environments.

It includes:

- Walls
- Roof
- Windows
- Doors
- Floors

The envelope significantly influences heat transfer and therefore affects annual building energy consumption.

---

## Heat Transfer Mechanisms

Three modes of heat transfer were studied:

- Conduction
- Convection
- Radiation

These mechanisms determine how heat enters or leaves a building and directly impact cooling and heating loads.

---

## Building Insulation

Thermal insulation reduces unwanted heat transfer through the building envelope.

Common insulation materials include:

- Glass Wool
- Rock Wool
- Expanded Polystyrene (EPS)
- Extruded Polystyrene (XPS)
- Polyurethane Foam

Proper insulation improves energy efficiency and reduces cooling demand.

---

## Building Energy Retrofitting

Building retrofitting involves upgrading existing buildings to improve energy performance without complete reconstruction.

Typical retrofit measures include:

- Roof insulation
- Wall insulation
- High-performance glazing
- LED lighting
- Efficient HVAC systems
- Improved building envelope
- Renewable energy integration

Retrofitting reduces operational energy consumption, electricity demand, and greenhouse gas emissions while improving occupant comfort.

# Test

![Logo](Assets/images/Before_After_retrofitting.png)

The figure above illustrates the transformation of an existing building into an energy-efficient building after implementing retrofit measures.

---

## Urban Building Energy Modeling (UBEM)

Urban Building Energy Modeling (UBEM) extends traditional building energy simulation from a single building to an entire city or district.

Instead of analysing one building, UBEM evaluates hundreds or thousands of buildings simultaneously using GIS data, weather information, and building characteristics.

This approach enables planners to estimate district-level:

- Energy consumption
- Peak electricity demand
- Carbon emissions
- Retrofit potential

---

## Building Energy Benchmarking

Building energy benchmarking compares a building's energy performance against standard reference values.

The most commonly used indicator is:

**Energy Performance Index (EPI)**

\[
EPI=\frac{Annual\ Energy\ Consumption}{Gross\ Floor\ Area}
\]

Benchmarking helps identify inefficient buildings and estimate potential energy savings.

---

## Energy Performance Indicators

Several performance indicators commonly used in building energy analysis were studied before beginning CityBES.

These include:

- Site Energy Use Intensity (Site EUI)
- Source Energy Use Intensity (Source EUI)
- Electricity Use Intensity (EUI)
- Peak Electricity Load Intensity
- Cooling Electricity Intensity
- Heating Energy Intensity
- Internal Lighting Energy Intensity
- Internal Equipment Energy Intensity
- Operational Greenhouse Gas (GHG) Intensity

These indicators later become the primary outputs generated by CityBES.

---

## Weather Data in Building Simulation

Outdoor weather conditions strongly influence building energy consumption.

Typical Meteorological Year (TMY) weather datasets provide:

- Dry bulb temperature
- Relative humidity
- Solar radiation
- Wind speed
- Wind direction

CityBES later uses these parameters to perform annual building energy simulations.

---

## Why this theoretical study?

Understanding these concepts was necessary before preparing GIS datasets because CityBES requires both geometric information (building footprints, height, stories, area) and engineering information (weather, energy benchmarks, building archetypes) to generate reliable baseline energy simulations.

<p align="center">
<img src="Assets/images/Before_After_retrofitting.png" width="700">
</p>

The figure above illustrates the objective of building retrofitting—improving the energy performance of existing buildings through energy-efficient interventions.

---

# Understanding CityBES

The next stage was understanding **CityBES (City Building Energy Saver)**, an Urban Building Energy Modeling platform developed by Lawrence Berkeley National Laboratory (LBNL).

CityBES converts GIS datasets into city-scale building energy simulation models. It enables planners and researchers to estimate:

- Baseline Energy Consumption
- Building Energy Use Intensity (EUI)
- Peak Electricity Demand
- Operational Carbon Emissions
- Retrofit Savings
- Building-Level Energy Performance

---

## Exploring CityBES Features

### 1. Building Visualization

<p align="center">
<img src="Assets/images/CityBES_colour features.png" width="900">
</p>

CityBES visualizes buildings using different energy performance indicators such as Site Energy Use Intensity, Electricity Use Intensity, Peak Electricity Load, Operational GHG Emissions, and many other building-level metrics.

---

### 2. Baseline Energy Simulation

<p align="center">
<img src="Assets/images/cityBES_baseline energy simulation.png" width="900">
</p>

Before applying retrofit measures, CityBES performs **Baseline Energy Simulation**, which estimates the current energy performance of buildings using building geometry, weather data, and benchmark parameters.

---

### 3. Simulation Results

<p align="center">
<img src="Assets/images/CityBES_Result_features.png" width="900">
</p>

CityBES provides interactive visualization of simulation outputs including energy intensity, electricity demand, carbon emissions, and district-level energy summaries.

---

# Exploring Data Sources

Preparing a CityBES dataset requires multiple GIS and remote sensing data sources.

Several publicly available platforms were explored to understand their available datasets and applicability for Ahmedabad.

---

## VEDAS (ISRO)

<p align="center">
<img src="Assets/images/Vedas.sac.gov.in.png" width="700">
</p>

VEDAS provides Indian geospatial datasets and satellite products. It was explored for urban datasets and Ahmedabad building information.

---

## Bhuvan (NRSC)

<p align="center">
<img src="Assets/images/Bhuvan.nrsc.png" width="700">
</p>

Bhuvan was explored to obtain satellite imagery and urban information for Ahmedabad.

---

## Copernicus Browser

<p align="center">
<img src="Assets/images/Copernicus browser.png" width="700">
</p>

Copernicus Browser was explored for Sentinel satellite imagery and land surface information.

---

## Google Earth Pro

<p align="center">
<img src="Assets/images/Google earth pro_building.png" width="700">
</p>

Google Earth Pro was used for visual verification of buildings and manual estimation of building heights wherever required.

---

# Selecting GIS Data Source

Although several remote sensing platforms were explored, OpenStreetMap (OSM) provided the most complete and easily accessible building footprint data suitable for CityBES dataset preparation.

Therefore, OpenStreetMap was selected as the primary GIS data source.

---

# Importing Building Footprints using QuickOSM

<p align="center">
<img src="Assets/images/QuickOSM plugin in QGIS.png" width="700">
</p>

The QuickOSM plugin in QGIS was used to directly import OpenStreetMap building footprints for different regions of Ahmedabad.

The following locations were explored:

- Navrangpura
- Thaltej
- Chandkheda
- Vastrapur
- Naroda
- Bopal

---

# Extracting Residential Buildings

Initially, all building footprints were imported from OpenStreetMap.

### Example – Chandkheda (All Buildings)

<p align="center">
<img src="Assets/images/Chandkheda_all_buildings.png" width="700">
</p>

The buildings were then filtered using OpenStreetMap building tags to retain only residential buildings.

### Residential Buildings

#### Navrangpura

<p align="center">
<img src="Assets/images/Navrangpura_residential.png" width="700">
</p>

#### Vastrapur

<p align="center">
<img src="Assets/images/Vastrapur_residential.png" width="700">
</p>

#### Chandkheda

<p align="center">
<img src="Assets/images/Chandkheda_residential.png" width="700">
</p>

The same workflow was repeated for all study locations.

---

# Preparing Building Attributes

After obtaining residential building footprints, additional attributes required for CityBES were prepared.

The attribute table was enriched with:

- Building Footprint Area
- Latitude
- Longitude
- Building Height
- Number of Stories
- Building Construction Year
- Total Floor Area
- Building IDs

Example attribute tables:

<p align="center">
<img src="Assets/images/Navrangpura_attribute table.png" width="900">
</p>

<p align="center">
<img src="Assets/images/Thatlej_attribute_table.png" width="900">
</p>

Random construction years were assigned within realistic ranges where public records were unavailable to support prototype building assignment in CityBES.

---

# Challenge: Missing Building Level Data

A major challenge encountered during dataset preparation was the absence of **building level (number of stories)** information in some regions.

<p align="center">
<img src="Assets/images/level_data_not_available.png" width="700">
</p>

Without building levels, building heights required for energy simulation could not be calculated directly.

---

# Exploring Ahmedabad 3D City Model

<p align="center">
<img src="Assets/images/Ahmedabad_3d_city_model.png" width="700">
</p>

The Ahmedabad 3D City Model was explored as an alternative source for estimating building heights.

Although accurate, extracting heights manually for thousands of buildings was not practical.

Therefore, the study focused on regions where OpenStreetMap already provided reliable building level information.

The final study locations selected were:

- Navrangpura
- Thaltej
- Chandkheda
- Vastrapur

---

# Building Size Classification

To support future benchmark assignment and visualization, residential buildings were classified into three size categories based on total floor area.

- 🟢 Small
- 🟡 Medium
- 🔴 Large

### Navrangpura

<p align="center">
<img src="Assets/images/Navrangpura_classified by total floor area.png" width="700">
</p>

### Thaltej

<p align="center">
<img src="Assets/images/Thatlej_after_classified by total foot print area.png" width="700">
</p>

---

# Weather Dataset Preparation

Weather data is an essential input for CityBES energy simulations.

Several weather data sources were explored before selecting an appropriate Typical Meteorological Year (TMYx) dataset for Ahmedabad.

<p align="center">
<img src="Assets/images/Weather_dataset.png" width="700">
</p>

The selected dataset represents weather observations from **2009–2023**, providing a recent climatic profile suitable for baseline building energy simulations.

---

# Current Progress

- Studied theoretical concepts of building energy retrofitting

- Explored CityBES platform

- Explored multiple GIS and satellite data sources

- Selected OpenStreetMap as primary GIS dataset

- Prepared residential building datasets

- Generated building attributes

- Estimated building heights

- Classified residential buildings by size

- Prepared weather dataset

- Preparing benchmark building energy dataset

---

# Next Phase

The next stage of the project includes:

- Preparing benchmark building energy parameters
- Uploading prepared datasets into CityBES
- Running baseline energy simulations
- Developing retrofit scenarios
- Applying Energy Conservation Measures (ECMs)
- Comparing baseline and retrofit energy performance
- Estimating energy savings
- Estimating operational carbon emission reductions

---

# Repository Status

🚧 Project currently under development.

The repository will be continuously updated as additional CityBES simulations and retrofit analyses are completed.

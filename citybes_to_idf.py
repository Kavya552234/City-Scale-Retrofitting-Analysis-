#!/usr/bin/env python3
"""
Convert CityBES-style building GeoJSON (footprint polygons + building/HVAC
attributes) into a single combined EnergyPlus IDF file per city.

Modeling approach (confirmed with user):
  - One combined IDF per city: every building is a separate Zone in one file.
  - Simplified "shoebox" geometry: each building is a single zone extruded
    from its footprint polygon up to its full height (no floor-by-floor
    zoning).
  - HVAC: ZoneHVAC:IdealLoadsAirSystem per building, driven by each
    building's own heating/cooling setpoint schedules pulled from the
    GeoJSON `additional_json.schedule_set`.

Data-driven inputs (taken directly from the GeoJSON, per building):
  - Footprint polygon (lon/lat -> projected to UTM Zone 43N meters)
  - Height (m) used for extrusion (fallback: building:levels * 3.0 m)
  - total_floor_area (used to scale internal loads across all floors,
    even though the zone geometry itself is a single shoebox volume)
  - window_u_value_ip / window_shgc -> WindowMaterial:SimpleGlazingSystem
  - heating_setpoint_schedule / cooling_setpoint_schedule -> Schedule:Compact

Generic assumptions NOT present in the data (clearly flagged in comments
inside the generated IDF and in the accompanying README):
  - Wall / roof / floor construction layers & materials (typical Indian
    residential construction: cement plaster + concrete block, RCC slab roof)
  - Window-to-wall ratio (20%, applied per wall face)
  - People / Lights / ElectricEquipment densities & schedules (generic
    residential profile, since building types are house/apartments/residential)
  - SizingPeriod:DesignDay objects (approximate ASHRAE values for Ahmedabad;
    replace with the .ddy file matching your chosen EPW for accurate sizing)
"""
import json
import math
import sys
from pyproj import Transformer

WWR = 0.20                      # window-to-wall ratio, generic assumption
MIN_WALL_LEN = 1.2               # m, skip windows on very short wall segments
MIN_FOOTPRINT_AREA = 1.0         # m^2, skip degenerate polygons
DEFAULT_LEVEL_HEIGHT = 3.0       # m, fallback per level
MIN_BUILDING_HEIGHT = 2.5        # m, floor for degenerate/missing height

# UTM Zone 43N covers Ahmedabad (72-78E band, northern hemisphere)
_transformer = Transformer.from_crs("EPSG:4326", "EPSG:32643", always_xy=True)


def project(lon, lat):
    x, y = _transformer.transform(lon, lat)
    return x, y


def clean_ring(ring):
    """Drop GeoJSON's closing duplicate vertex and any consecutive dupes."""
    pts = list(ring)
    if len(pts) > 1 and pts[0] == pts[-1]:
        pts = pts[:-1]
    out = []
    for p in pts:
        if not out or (abs(p[0] - out[-1][0]) > 1e-9 or abs(p[1] - out[-1][1]) > 1e-9):
            out.append(p)
    return out


def signed_area(pts):
    s = 0.0
    n = len(pts)
    for i in range(n):
        x1, y1 = pts[i]
        x2, y2 = pts[(i + 1) % n]
        s += x1 * y2 - x2 * y1
    return s / 2.0


def ensure_ccw(pts):
    """Return pts ordered CCW (positive shoelace area) in (easting,northing)."""
    if signed_area(pts) < 0:
        return list(reversed(pts))
    return pts


def fmt(v):
    if isinstance(v, float):
        if v == int(v) and abs(v) < 1e6:
            return f"{v:.4f}"
        return f"{v:.6f}"
    return str(v)


def idf_obj(obj_type, fields):
    """fields: list of (value, comment) tuples."""
    lines = [f"{obj_type},"]
    n = len(fields)
    for i, (val, comment) in enumerate(fields):
        term = ";" if i == n - 1 else ","
        vstr = fmt(val)
        if comment:
            lines.append(f"    {vstr}{term}  !- {comment}")
        else:
            lines.append(f"    {vstr}{term}")
    lines.append("")
    return "\n".join(lines)


def vtx_fields(pts3d, start_index=1):
    """pts3d: list of (x,y,z). Returns list of (value, comment) triples for coords."""
    out = []
    for i, (x, y, z) in enumerate(pts3d):
        out.append((x, f"Vertex {i+1} Xcoordinate"))
        out.append((y, f"Vertex {i+1} Ycoordinate"))
        out.append((z, f"Vertex {i+1} Zcoordinate"))
    return out


# ---------------------------------------------------------------------------
# Static (shared, deduplicated) blocks: materials, constructions, schedules
# ---------------------------------------------------------------------------

def header_block(city_name, origin_lat, origin_lon):
    out = []
    out.append(idf_obj("Version", [("24.2", "Version Identifier")]))
    out.append(idf_obj("Building", [
        (f"{city_name}_UrbanModel", "Name"),
        (0.0, "North Axis"),
        ("City", "Terrain"),
        (0.04, "Loads Convergence Tolerance Value"),
        (0.4, "Temperature Convergence Tolerance Value"),
        ("FullExterior", "Solar Distribution"),
        (25, "Maximum Number of Warmup Days"),
        (6, "Minimum Number of Warmup Days"),
    ]))
    out.append(idf_obj("SimulationControl", [
        ("No", "Do Zone Sizing Calculation"),
        ("No", "Do System Sizing Calculation"),
        ("No", "Do Plant Sizing Calculation"),
        ("Yes", "Run Simulation for Sizing Periods"),
        ("Yes", "Run Simulation for Weather File Run Periods"),
    ]))
    out.append(idf_obj("Timestep", [(4, "Number of Timesteps per Hour")]))
    out.append(idf_obj("ShadowCalculation", [
        ("PolygonClipping", "Shading Calculation Method"),
        ("Periodic", "Shading Calculation Update Frequency Method"),
        (20, "Shading Calculation Update Frequency"),
        (15000, "Maximum Figures in Shadow Overlap Calculations"),
    ]))
    out.append(idf_obj("HeatBalanceAlgorithm", [("ConductionTransferFunction", "Algorithm")]))
    out.append(idf_obj("RunPeriod", [
        ("AnnualRun", "Name"),
        (1, "Begin Month"), (1, "Begin Day of Month"),
        (12, "End Month"), (31, "End Day of Month"),
        ("", "Begin Year"),
        ("Sunday", "Day of Week for Start Day"),
        ("Yes", "Use Weather File Holidays and Special Days"),
        ("Yes", "Use Weather File Daylight Saving Period"),
        ("No", "Apply Weekend Holiday Rule"),
        ("Yes", "Use Weather File Rain Indicators"),
        ("Yes", "Use Weather File Snow Indicators"),
    ]))
    out.append(idf_obj("Site:Location", [
        (f"{city_name}_Ahmedabad_IND", "Name"),
        (origin_lat, "Latitude"),
        (origin_lon, "Longitude"),
        (5.50, "Time Zone"),
        (55.0, "Elevation"),
    ]))
    # Approximate ASHRAE design-day placeholders for Ahmedabad (WMO 426470).
    # Replace with the actual .ddy file paired with your chosen EPW for
    # accurate equipment sizing -- these are reasonable stand-ins only.
    out.append(idf_obj("SizingPeriod:DesignDay", [
        (f"{city_name} Ann Htg 99.6% Condns DB", "Name"),
        (1, "Month"), (21, "Day of Month"), ("WinterDesignDay", "Day Type"),
        (10.8, "Maximum Dry-Bulb Temperature"),
        (0.0, "Daily Dry-Bulb Temperature Range"),
        ("DefaultMultipliers", "Dry-Bulb Temperature Range Modifier Type"),
        ("", "Dry-Bulb Temperature Range Modifier Day Schedule Name"),
        ("Wetbulb", "Humidity Condition Type"),
        (10.8, "Wetbulb or DewPoint at Maximum Dry-Bulb"),
        ("", "Humidity Condition Day Schedule Name"),
        ("", "Humidity Ratio at Maximum Dry-Bulb"),
        ("", "Enthalpy at Maximum Dry-Bulb"),
        ("", "Daily Wet-Bulb Temperature Range"),
        (97060, "Barometric Pressure"),
        (2.6, "Wind Speed"),
        (50, "Wind Direction"),
        ("No", "Rain Indicator"),
        ("No", "Snow Indicator"),
        ("No", "Daylight Saving Time Indicator"),
        ("ASHRAEClearSky", "Solar Model Indicator"),
        ("", "Beam Solar Day Schedule Name"),
        ("", "Diffuse Solar Day Schedule Name"),
        ("", "ASHRAE Clear Sky Optical Depth for Beam Irradiance (taub)"),
        ("", "ASHRAE Clear Sky Optical Depth for Diffuse Irradiance (taud)"),
        (0.0, "Sky Clearness"),
    ]))
    out.append(idf_obj("SizingPeriod:DesignDay", [
        (f"{city_name} Ann Clg 0.4% Condns DB=>MWB", "Name"),
        (5, "Month"), (21, "Day of Month"), ("SummerDesignDay", "Day Type"),
        (42.0, "Maximum Dry-Bulb Temperature"),
        (10.0, "Daily Dry-Bulb Temperature Range"),
        ("DefaultMultipliers", "Dry-Bulb Temperature Range Modifier Type"),
        ("", "Dry-Bulb Temperature Range Modifier Day Schedule Name"),
        ("Wetbulb", "Humidity Condition Type"),
        (24.0, "Wetbulb or DewPoint at Maximum Dry-Bulb"),
        ("", "Humidity Condition Day Schedule Name"),
        ("", "Humidity Ratio at Maximum Dry-Bulb"),
        ("", "Enthalpy at Maximum Dry-Bulb"),
        ("", "Daily Wet-Bulb Temperature Range"),
        (97060, "Barometric Pressure"),
        (2.8, "Wind Speed"),
        (280, "Wind Direction"),
        ("No", "Rain Indicator"),
        ("No", "Snow Indicator"),
        ("No", "Daylight Saving Time Indicator"),
        ("ASHRAEClearSky", "Solar Model Indicator"),
        ("", "Beam Solar Day Schedule Name"),
        ("", "Diffuse Solar Day Schedule Name"),
        ("", "ASHRAE Clear Sky Optical Depth for Beam Irradiance (taub)"),
        ("", "ASHRAE Clear Sky Optical Depth for Diffuse Irradiance (taud)"),
        (1.0, "Sky Clearness"),
    ]))
    out.append(idf_obj("Site:GroundTemperature:BuildingSurface", [
        (28.0, "Jan"), (27.5, "Feb"), (28.0, "Mar"), (29.5, "Apr"),
        (31.0, "May"), (30.5, "Jun"), (29.0, "Jul"), (28.5, "Aug"),
        (28.5, "Sep"), (28.5, "Oct"), (28.0, "Nov"), (28.0, "Dec"),
    ]))
    out.append(idf_obj("GlobalGeometryRules", [
        ("UpperLeftCorner", "Starting Vertex Position"),
        ("Counterclockwise", "Vertex Entry Direction"),
        ("World", "Coordinate System"),
    ]))
    return "\n".join(out)


def materials_and_constructions_block():
    out = []
    # --- Opaque materials (generic Indian residential construction) ---
    out.append(idf_obj("Material", [
        ("CementPlaster_20mm", "Name"), ("Rough", "Roughness"),
        (0.02, "Thickness"), (0.72, "Conductivity"), (1860, "Density"),
        (840, "Specific Heat"), (0.9, "Thermal Absorptance"),
        (0.65, "Solar Absorptance"), (0.65, "Visible Absorptance"),
    ]))
    out.append(idf_obj("Material", [
        ("ConcreteBlock_150mm", "Name"), ("MediumRough", "Roughness"),
        (0.15, "Thickness"), (0.51, "Conductivity"), (1400, "Density"),
        (1000, "Specific Heat"), (0.9, "Thermal Absorptance"),
        (0.6, "Solar Absorptance"), (0.6, "Visible Absorptance"),
    ]))
    out.append(idf_obj("Material", [
        ("CementPlaster_15mm_Int", "Name"), ("Smooth", "Roughness"),
        (0.015, "Thickness"), (0.72, "Conductivity"), (1860, "Density"),
        (840, "Specific Heat"), (0.9, "Thermal Absorptance"),
        (0.5, "Solar Absorptance"), (0.5, "Visible Absorptance"),
    ]))
    out.append(idf_obj("Material", [
        ("RoofScreed_50mm", "Name"), ("Rough", "Roughness"),
        (0.05, "Thickness"), (0.71, "Conductivity"), (1900, "Density"),
        (840, "Specific Heat"), (0.9, "Thermal Absorptance"),
        (0.55, "Solar Absorptance"), (0.55, "Visible Absorptance"),
    ]))
    out.append(idf_obj("Material", [
        ("RCC_Slab_125mm", "Name"), ("MediumRough", "Roughness"),
        (0.125, "Thickness"), (1.73, "Conductivity"), (2400, "Density"),
        (920, "Specific Heat"), (0.9, "Thermal Absorptance"),
        (0.65, "Solar Absorptance"), (0.65, "Visible Absorptance"),
    ]))
    out.append(idf_obj("Material", [
        ("GroundSlab_150mm", "Name"), ("MediumRough", "Roughness"),
        (0.15, "Thickness"), (1.73, "Conductivity"), (2400, "Density"),
        (920, "Specific Heat"), (0.9, "Thermal Absorptance"),
        (0.65, "Solar Absorptance"), (0.65, "Visible Absorptance"),
    ]))
    # --- Constructions ---
    out.append(idf_obj("Construction", [
        ("ExteriorWall", "Name"),
        ("CementPlaster_20mm", "Outside Layer"),
        ("ConcreteBlock_150mm", "Layer 2"),
        ("CementPlaster_15mm_Int", "Layer 3"),
    ]))
    out.append(idf_obj("Construction", [
        ("FlatRoof", "Name"),
        ("RoofScreed_50mm", "Outside Layer"),
        ("RCC_Slab_125mm", "Layer 2"),
    ]))
    out.append(idf_obj("Construction", [
        ("GroundFloor", "Name"),
        ("GroundSlab_150mm", "Outside Layer"),
    ]))
    # --- Window: single U/SHGC combo confirmed uniform across the dataset ---
    u_ip = 1.04     # Btu/(hr-ft2-F), from additional_json.window_u_value_ip
    shgc = 0.75
    u_si = round(u_ip * 5.678263, 4)
    out.append(idf_obj("WindowMaterial:SimpleGlazingSystem", [
        ("SimpleWindow_Uip1p04_SHGC0p75", "Name"),
        (u_si, "U-Factor"),
        (shgc, "Solar Heat Gain Coefficient"),
        (0.6, "Visible Transmittance"),
    ]))
    out.append(idf_obj("Construction", [
        ("ExteriorWindow", "Name"),
        ("SimpleWindow_Uip1p04_SHGC0p75", "Outside Layer"),
    ]))
    return "\n".join(out)


def schedules_block():
    out = []
    out.append(idf_obj("ScheduleTypeLimits", [
        ("Temperature", "Name"), (-60, "Lower Limit"), (200, "Upper Limit"),
        ("Continuous", "Numeric Type"),
    ]))
    out.append(idf_obj("ScheduleTypeLimits", [
        ("Fraction", "Name"), (0, "Lower Limit"), (1, "Upper Limit"),
        ("Continuous", "Numeric Type"),
    ]))
    out.append(idf_obj("ScheduleTypeLimits", [
        ("Control Type", "Name"), (0, "Lower Limit"), (4, "Upper Limit"),
        ("Discrete", "Numeric Type"),
    ]))
    # Heating setpoint: uniform 5 C year-round, all day types (from
    # additional_json.schedule_set.heating_setpoint_schedule -- identical
    # across every building in both files).
    out.append(idf_obj("Schedule:Compact", [
        ("HeatingSetpointSchedule", "Name"), ("Temperature", "Schedule Type Limits"),
        ("Through: 12/31", "Field 1"), ("For: AllDays", "Field 2"),
        ("Until: 24:00", "Field 3"), (5.0, "Field 4"),
    ]))
    # Cooling setpoint: 25 C daytime (08:00-20:00), 26 C otherwise, uniform
    # across every date range / day type in the source data.
    out.append(idf_obj("Schedule:Compact", [
        ("CoolingSetpointSchedule", "Name"), ("Temperature", "Schedule Type Limits"),
        ("Through: 12/31", "Field 1"), ("For: AllDays", "Field 2"),
        ("Until: 08:00", "Field 3"), (26.0, "Field 4"),
        ("Until: 20:00", "Field 5"), (25.0, "Field 6"),
        ("Until: 24:00", "Field 7"), (26.0, "Field 8"),
    ]))
    out.append(idf_obj("Schedule:Compact", [
        ("ThermostatControlType", "Name"), ("Control Type", "Schedule Type Limits"),
        ("Through: 12/31", "Field 1"), ("For: AllDays", "Field 2"),
        ("Until: 24:00", "Field 3"), (4, "Field 4"),
    ]))
    out.append(idf_obj("Schedule:Constant", [
        ("AlwaysOn", "Name"), ("Fraction", "Schedule Type Limits"), (1.0, "Hourly Value"),
    ]))
    # Generic residential occupancy/lighting/equipment profiles.
    # NOT present in the source data -- reasonable defaults, same for all
    # buildings since building types are house / apartments / residential.
    out.append(idf_obj("Schedule:Compact", [
        ("ResOccupancySchedule", "Name"), ("Fraction", "Schedule Type Limits"),
        ("Through: 12/31", "Field 1"), ("For: AllDays", "Field 2"),
        ("Until: 07:00", "Field 3"), (1.0, "Field 4"),
        ("Until: 09:00", "Field 5"), (0.6, "Field 6"),
        ("Until: 17:00", "Field 7"), (0.3, "Field 8"),
        ("Until: 22:00", "Field 9"), (0.8, "Field 10"),
        ("Until: 24:00", "Field 11"), (1.0, "Field 12"),
    ]))
    out.append(idf_obj("Schedule:Compact", [
        ("ResLightingSchedule", "Name"), ("Fraction", "Schedule Type Limits"),
        ("Through: 12/31", "Field 1"), ("For: AllDays", "Field 2"),
        ("Until: 06:00", "Field 3"), (0.05, "Field 4"),
        ("Until: 08:00", "Field 5"), (0.4, "Field 6"),
        ("Until: 18:00", "Field 7"), (0.1, "Field 8"),
        ("Until: 23:00", "Field 9"), (0.9, "Field 10"),
        ("Until: 24:00", "Field 11"), (0.2, "Field 12"),
    ]))
    out.append(idf_obj("Schedule:Compact", [
        ("ResEquipmentSchedule", "Name"), ("Fraction", "Schedule Type Limits"),
        ("Through: 12/31", "Field 1"), ("For: AllDays", "Field 2"),
        ("Until: 06:00", "Field 3"), (0.2, "Field 4"),
        ("Until: 08:00", "Field 5"), (0.5, "Field 6"),
        ("Until: 18:00", "Field 7"), (0.3, "Field 8"),
        ("Until: 23:00", "Field 9"), (0.8, "Field 10"),
        ("Until: 24:00", "Field 11"), (0.2, "Field 12"),
    ]))
    return "\n".join(out)


# ---------------------------------------------------------------------------
# Per-building geometry + systems
# ---------------------------------------------------------------------------

def build_building_idf(feat, origin, log):
    props = feat["properties"]
    osm_id = str(props.get("osm_id", "unknown"))
    zone_name = f"Zone_{osm_id}"

    geom = feat["geometry"]
    if geom["type"] == "MultiPolygon":
        ring = geom["coordinates"][0][0]
    elif geom["type"] == "Polygon":
        ring = geom["coordinates"][0]
    else:
        log.append(f"SKIP {osm_id}: unsupported geometry type {geom['type']}")
        return ""

    pts_ll = clean_ring(ring)
    if len(pts_ll) < 3:
        log.append(f"SKIP {osm_id}: fewer than 3 vertices after cleaning")
        return ""

    pts_m = [project(lon, lat) for lon, lat in pts_ll]
    ox, oy = origin
    pts_local = [(x - ox, y - oy) for x, y in pts_m]
    pts_local = ensure_ccw(pts_local)

    area = signed_area(pts_local)
    if area < MIN_FOOTPRINT_AREA:
        log.append(f"SKIP {osm_id}: footprint area {area:.2f} m2 too small")
        return ""

    height = props.get("Height")
    levels = props.get("building:levels")
    try:
        levels_n = float(levels) if levels is not None else None
    except (ValueError, TypeError):
        levels_n = None
    if not isinstance(height, (int, float)) or height <= 0:
        if levels_n and levels_n > 0:
            height = levels_n * DEFAULT_LEVEL_HEIGHT
            log.append(f"NOTE {osm_id}: Height missing, derived {height:.1f} m from levels")
        else:
            height = DEFAULT_LEVEL_HEIGHT
            log.append(f"NOTE {osm_id}: Height and levels missing, defaulted to {height:.1f} m")
    height = max(float(height), MIN_BUILDING_HEIGHT)

    total_floor_area = props.get("total_floor_area")
    if not isinstance(total_floor_area, (int, float)) or total_floor_area <= 0:
        n_levels = levels_n if (levels_n and levels_n > 0) else max(1.0, round(height / DEFAULT_LEVEL_HEIGHT))
        total_floor_area = area * n_levels

    out = [f"! ===== Building osm_id={osm_id} ({props.get('building')}, "
           f"{area:.1f} m2 footprint, {height:.1f} m tall, "
           f"{total_floor_area:.1f} m2 total floor area) ====="]

    out.append(idf_obj("Zone", [
        (zone_name, "Name"), (0.0, "Direction of Relative North"),
        (0.0, "X Origin"), (0.0, "Y Origin"), (0.0, "Z Origin"),
        (1, "Type"), (1, "Multiplier"),
    ]))

    n = len(pts_local)

    # Floor: reversed order (outward normal points down/out)
    floor_pts = [(x, y, 0.0) for x, y in reversed(pts_local)]
    out.append(idf_obj("BuildingSurface:Detailed", [
        (f"{zone_name}_Floor", "Name"), ("Floor", "Surface Type"),
        ("GroundFloor", "Construction Name"), (zone_name, "Zone Name"),
        ("", "Space Name"),
        ("Ground", "Outside Boundary Condition"), ("", "Outside Boundary Condition Object"),
        ("NoSun", "Sun Exposure"), ("NoWind", "Wind Exposure"),
        (0, "View Factor to Ground"), (n, "Number of Vertices"),
    ] + vtx_fields(floor_pts)))

    # Roof: same order as footprint (CCW as seen from above)
    roof_pts = [(x, y, height) for x, y in pts_local]
    out.append(idf_obj("BuildingSurface:Detailed", [
        (f"{zone_name}_Roof", "Name"), ("Roof", "Surface Type"),
        ("FlatRoof", "Construction Name"), (zone_name, "Zone Name"),
        ("", "Space Name"),
        ("Outdoors", "Outside Boundary Condition"), ("", "Outside Boundary Condition Object"),
        ("SunExposed", "Sun Exposure"), ("WindExposed", "Wind Exposure"),
        (0, "View Factor to Ground"), (n, "Number of Vertices"),
    ] + vtx_fields(roof_pts)))

    # Walls + windows, one per footprint edge
    for i in range(n):
        x1, y1 = pts_local[i]
        x2, y2 = pts_local[(i + 1) % n]
        edge_len = math.hypot(x2 - x1, y2 - y1)
        if edge_len < 0.05:
            continue
        wall_name = f"{zone_name}_Wall_{i+1}"
        wall_pts = [(x1, y1, 0.0), (x2, y2, 0.0), (x2, y2, height), (x1, y1, height)]
        out.append(idf_obj("BuildingSurface:Detailed", [
            (wall_name, "Name"), ("Wall", "Surface Type"),
            ("ExteriorWall", "Construction Name"), (zone_name, "Zone Name"),
            ("", "Space Name"),
            ("Outdoors", "Outside Boundary Condition"), ("", "Outside Boundary Condition Object"),
            ("SunExposed", "Sun Exposure"), ("WindExposed", "Wind Exposure"),
            (0.5, "View Factor to Ground"), (4, "Number of Vertices"),
        ] + vtx_fields(wall_pts)))

        if edge_len >= MIN_WALL_LEN and WWR > 0:
            # Window as a scaled (about centroid) copy of the wall rectangle,
            # so window area = WWR * wall area exactly, symmetric inset.
            cx = (x1 + x2) / 2.0
            cy = (y1 + y2) / 2.0
            cz = height / 2.0
            s = math.sqrt(WWR)
            def scale(px, py, pz):
                return (cx + (px - cx) * s, cy + (py - cy) * s, cz + (pz - cz) * s)
            win_pts = [scale(*p) for p in wall_pts]
            out.append(idf_obj("FenestrationSurface:Detailed", [
                (f"{wall_name}_Window", "Name"), ("Window", "Surface Type"),
                ("ExteriorWindow", "Construction Name"), (wall_name, "Building Surface Name"),
                ("", "Outside Boundary Condition Object"),
                ("autocalculate", "View Factor to Ground"),
                ("", "Frame and Divider Name"), (1, "Multiplier"),
                (4, "Number of Vertices"),
            ] + [(v, c) for v, c in vtx_fields(win_pts)]))

    # Internal loads scaled by total_floor_area (represents all real floors,
    # even though this shoebox zone's floor area is just the footprint)
    people_per_m2 = 1.0 / 20.0   # generic residential density assumption
    out.append(idf_obj("People", [
        (f"{zone_name}_People", "Name"), (zone_name, "Zone or ZoneList Name"),
        ("ResOccupancySchedule", "Number of People Schedule Name"),
        ("People", "Number of People Calculation Method"),
        (round(total_floor_area * people_per_m2, 2), "Number of People"),
        ("", "People per Zone Floor Area"), ("", "Zone Floor Area per Person"),
        (0.3, "Fraction Radiant"),
    ]))
    lighting_w_m2 = 8.0
    out.append(idf_obj("Lights", [
        (f"{zone_name}_Lights", "Name"), (zone_name, "Zone or ZoneList Name"),
        ("ResLightingSchedule", "Schedule Name"),
        ("LightingLevel", "Design Level Calculation Method"),
        (round(total_floor_area * lighting_w_m2, 1), "Lighting Level"),
        ("", "Watts per Zone Floor Area"), ("", "Watts per Person"),
    ]))
    equip_w_m2 = 5.0
    out.append(idf_obj("ElectricEquipment", [
        (f"{zone_name}_Equip", "Name"), (zone_name, "Zone or ZoneList Name"),
        ("ResEquipmentSchedule", "Schedule Name"),
        ("EquipmentLevel", "Design Level Calculation Method"),
        (round(total_floor_area * equip_w_m2, 1), "Design Level"),
    ]))

    # HVAC: Ideal Loads Air System driven by this building's own setpoints
    out.append(idf_obj("ZoneHVAC:IdealLoadsAirSystem", [
        (f"{zone_name}_IdealLoads", "Name"), ("", "Availability Schedule Name"),
        (f"{zone_name}_SupplyInlet", "Zone Supply Air Node Name"),
        ("", "Zone Exhaust Air Node Name"), ("", "System Inlet Air Node Name"),
        (50, "Maximum Heating Supply Air Temperature"),
        (13, "Minimum Cooling Supply Air Temperature"),
        (0.0156, "Maximum Heating Supply Air Humidity Ratio"),
        (0.0077, "Minimum Cooling Supply Air Humidity Ratio"),
        ("NoLimit", "Heating Limit"), ("", "Maximum Heating Air Flow Rate"),
        ("", "Maximum Sensible Heating Capacity"),
        ("NoLimit", "Cooling Limit"), ("", "Maximum Cooling Air Flow Rate"),
        ("", "Maximum Total Cooling Capacity"),
        ("", "Heating Availability Schedule Name"), ("", "Cooling Availability Schedule Name"),
        ("ConstantSupplyHumidityRatio", "Dehumidification Control Type"),
        ("", "Cooling Sensible Heat Ratio"),
        ("ConstantSupplyHumidityRatio", "Humidification Control Type"),
        ("", "Design Specification Outdoor Air Object Name"),
        ("", "Outdoor Air Inlet Node Name"),
        ("", "Demand Controlled Ventilation Type"),
        ("", "Outdoor Air Economizer Type"),
        ("", "Heat Recovery Type"),
        ("", "Sensible Heat Recovery Effectiveness"),
        ("", "Latent Heat Recovery Effectiveness"),
    ]))
    out.append(idf_obj("ZoneHVAC:EquipmentList", [
        (f"{zone_name}_EquipList", "Name"), ("SequentialLoad", "Load Distribution Scheme"),
        ("ZoneHVAC:IdealLoadsAirSystem", "Zone Equipment 1 Object Type"),
        (f"{zone_name}_IdealLoads", "Zone Equipment 1 Name"),
        (1, "Zone Equipment 1 Cooling Sequence"), (1, "Zone Equipment 1 Heating or No-Load Sequence"),
    ]))
    out.append(idf_obj("ZoneHVAC:EquipmentConnections", [
        (zone_name, "Zone Name"), (f"{zone_name}_EquipList", "Zone Conditioning Equipment List Name"),
        (f"{zone_name}_SupplyInlet", "Zone Air Inlet Node or NodeList Name"), ("", "Zone Air Exhaust Node or NodeList Name"),
        (f"{zone_name}_Node", "Zone Air Node Name"), ("", "Zone Return Air Node or NodeList Name"),
    ]))
    out.append(idf_obj("ZoneControl:Thermostat", [
        (f"{zone_name}_Thermostat", "Name"), (zone_name, "Zone or ZoneList Name"),
        ("ThermostatControlType", "Control Type Schedule Name"),
        ("ThermostatSetpoint:DualSetpoint", "Control 1 Object Type"),
        (f"{zone_name}_DualSetpoint", "Control 1 Name"),
    ]))
    out.append(idf_obj("ThermostatSetpoint:DualSetpoint", [
        (f"{zone_name}_DualSetpoint", "Name"),
        ("HeatingSetpointSchedule", "Heating Setpoint Temperature Schedule Name"),
        ("CoolingSetpointSchedule", "Cooling Setpoint Temperature Schedule Name"),
    ]))
    out.append(idf_obj("Sizing:Zone", [
        (zone_name, "Zone or ZoneList Name"),
        ("SupplyAirTemperature", "Zone Cooling Design Supply Air Temperature Input Method"),
        (13.0, "Zone Cooling Design Supply Air Temperature"), ("", "Zone Cooling Design Supply Air Temperature Difference"),
        ("SupplyAirTemperature", "Zone Heating Design Supply Air Temperature Input Method"),
        (40.0, "Zone Heating Design Supply Air Temperature"), ("", "Zone Heating Design Supply Air Temperature Difference"),
        (0.0085, "Zone Cooling Design Supply Air Humidity Ratio"),
        (0.008, "Zone Heating Design Supply Air Humidity Ratio"),
        (1.0, "Zone Heating Sizing Factor"), (1.0, "Zone Cooling Sizing Factor"),
        ("DesignDay", "Cooling Design Air Flow Method"), ("", "Cooling Design Air Flow Rate"),
        ("", "Cooling Minimum Air Flow per Zone Floor Area"), ("", "Cooling Minimum Air Flow"),
        ("", "Cooling Minimum Air Flow Fraction"),
        ("DesignDay", "Heating Design Air Flow Method"), ("", "Heating Design Air Flow Rate"),
        ("", "Heating Maximum Air Flow per Zone Floor Area"), ("", "Heating Maximum Air Flow"),
        ("", "Heating Maximum Air Flow Fraction"),
    ]))

    return "\n".join(out)


def convert_city(geojson_path, city_name, out_path):
    with open(geojson_path) as f:
        data = json.load(f)
    feats = data["features"]

    # Local origin: SW corner (minus small pad) of all projected points, so
    # coordinates in the IDF stay small/readable rather than raw UTM meters.
    all_pts = []
    for feat in feats:
        geom = feat["geometry"]
        ring = geom["coordinates"][0][0] if geom["type"] == "MultiPolygon" else geom["coordinates"][0]
        for lon, lat in clean_ring(ring):
            all_pts.append(project(lon, lat))
    ox = min(p[0] for p in all_pts) - 10
    oy = min(p[1] for p in all_pts) - 10
    origin = (ox, oy)

    # Reference lat/lon for Site:Location = centroid of all buildings
    lons = [feat["properties"]["longitude"] for feat in feats if feat["properties"].get("longitude")]
    lats = [feat["properties"]["latitude"] for feat in feats if feat["properties"].get("latitude")]
    origin_lat = sum(lats) / len(lats) if lats else 23.03
    origin_lon = sum(lons) / len(lons) if lons else 72.55

    log = []
    parts = [
        f"! ============================================================",
        f"! {city_name} urban building energy model",
        f"! Generated from {geojson_path.split('/')[-1]}",
        f"! {len(feats)} buildings in source file",
        f"! Local coordinate origin (UTM Zone 43N, meters): "
        f"E={ox+10:.1f} N={oy+10:.1f} (10 m pad)",
        f"! ============================================================",
        "",
        header_block(city_name, origin_lat, origin_lon),
        materials_and_constructions_block(),
        schedules_block(),
    ]

    n_ok = 0
    for feat in feats:
        block = build_building_idf(feat, origin, log)
        if block:
            parts.append(block)
            n_ok += 1

    with open(out_path, "w") as f:
        f.write("\n".join(parts))

    log_path = out_path.replace(".idf", "_conversion_log.txt")
    with open(log_path, "w") as f:
        f.write(f"{city_name}: {n_ok}/{len(feats)} buildings converted successfully\n\n")
        f.write("\n".join(log))

    print(f"{city_name}: wrote {n_ok}/{len(feats)} buildings -> {out_path}")
    print(f"  log: {log_path} ({len(log)} notes/warnings)")
    return n_ok, len(feats)


if __name__ == "__main__":
    convert_city(
        "/mnt/user-data/uploads/Navrangpura_CityBES.geojson",
        "Navrangpura",
        "/mnt/user-data/outputs/Navrangpura.idf",
    )
    convert_city(
        "/mnt/user-data/uploads/Thatlej_CityBES.geojson",
        "Thatlej",
        "/mnt/user-data/outputs/Thatlej.idf",
    )

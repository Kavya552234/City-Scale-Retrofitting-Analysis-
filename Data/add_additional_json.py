import json

# ----------------------------
# Files to update
# ----------------------------
files = [
    "Navrangpura_geojson.geojson",
    "Thatlej_geojson.geojson"
]

# ----------------------------
# Ahmedabad Residential
# Additional JSON
# ----------------------------

additional_json = {

    "heating_setpoint": 64.4,          # 18°C
    "cooling_setpoint": 78.8,          # 26°C

    "hvac_system_type_id": 26,
    "hvac_cooling_cop": 3.54,

    "window_shgc": 0.75,
    "window_u_value_ip": 1.04,

    "schedule_set":
    {

        "heating_setpoint_schedule":
        {

            "1/1-12/31":
            {

                "weekday":
                [5]*24,

                "weekend":
                [5]*24

            }

        },

        "cooling_setpoint_schedule":
        {

            "1/1-2/28":
            {

                "weekday":
                [26,26,26,26,26,26,26,26,
                 25,25,25,25,25,25,25,25,
                 25,25,25,25,
                 26,26,26,26],

                "weekend":
                [26,26,26,26,26,26,26,26,
                 25,25,25,25,25,25,25,25,
                 25,25,25,25,
                 26,26,26,26]

            },

            "3/1-6/30":
            {

                "weekday":
                [26,26,26,26,26,26,26,26,
                 25,25,25,25,25,25,25,25,
                 25,25,25,25,
                 26,26,26,26],

                "weekend":
                [26,26,26,26,26,26,26,26,
                 25,25,25,25,25,25,25,25,
                 25,25,25,25,
                 26,26,26,26]

            },

            "7/1-9/30":
            {

                "weekday":
                [26,26,26,26,26,26,26,26,
                 25,25,25,25,25,25,25,25,
                 25,25,25,25,
                 26,26,26,26],

                "weekend":
                [26,26,26,26,26,26,26,26,
                 25,25,25,25,25,25,25,25,
                 25,25,25,25,
                 26,26,26,26]

            },

            "10/1-12/31":
            {

                "weekday":
                [26,26,26,26,26,26,26,26,
                 25,25,25,25,25,25,25,25,
                 25,25,25,25,
                 26,26,26,26],

                "weekend":
                [26,26,26,26,26,26,26,26,
                 25,25,25,25,25,25,25,25,
                 25,25,25,25,
                 26,26,26,26],

                "summer_design_day":
                [26,26,26,26,26,26,26,26,
                 25,25,25,25,25,25,25,25,
                 25,25,25,25,
                 26,26,26,26]

            }

        }

    }

}

# ----------------------------
# Update every building
# ----------------------------

for filename in files:

    with open(filename, "r", encoding="utf-8") as f:
        data = json.load(f)

    for feature in data["features"]:
        feature["properties"]["additional_json"] = additional_json

    output = filename.replace(".geojson", "_CityBES.geojson")

    with open(output, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)

    print(f"Updated: {output}")

print("\nDone!")

# ============================================
# Update Navrangpura GeoJSON for CityBES
# ============================================

input_file = "Thatlej_geojson.geojson"
output_file = "Thatlej_CityBES.geojson" 

# Read GeoJSON
with open(input_file, "r", encoding="utf-8") as f:
    data = json.load(f)

# Add additional_json to every building
building_count = 0

for feature in data["features"]:
    feature["properties"]["additional_json"] = additional_json
    building_count += 1

# Save new CityBES GeoJSON
with open(output_file, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=4)

print("=" * 50)
print("Ahmedabad CityBES Dataset Generated Successfully")
print("=" * 50)
print(f"Input File        : {input_file}")
print(f"Output File       : {output_file}")
print(f"Buildings Updated : {building_count}")
print("=" * 50)
print("Done!")
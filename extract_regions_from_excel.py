"""
Extract city code to region mapping from the Excel file
"""
import pandas as pd

print("Reading Excel file...")
df = pd.read_excel('bycode2021 (1).xlsx')

# Column B (index 1) has codes, Column E (index 4) has regions
code_col = df.iloc[:, 1]  # Column B - codes
region_col = df.iloc[:, 4]  # Column E - regions

# Build mapping
city_region_map = {}
for code, region in zip(code_col, region_col):
    if pd.notna(code) and pd.notna(region):
        try:
            code_int = int(code)
            city_region_map[code_int] = region
        except (ValueError, TypeError):
            pass

print(f"\nExtracted {len(city_region_map)} code-to-region mappings")

# Show region distribution
from collections import Counter
region_counts = Counter(city_region_map.values())

print("\nRegion distribution:")
for region, count in sorted(region_counts.items(), key=lambda x: x[1], reverse=True):
    print(f"  {region}: {count} settlements")

# Save to Python file
output = "# Israeli settlement code to region mapping\n"
output += "# Extracted from CBS data (bycode2021.xlsx)\n\n"
output += "city_region_map = {\n"

for code in sorted(city_region_map.keys()):
    region = city_region_map[code]
    # Escape quotes
    region_escaped = region.replace('\\', '\\\\').replace('"', '\\"')
    output += f"    {code}: \"{region_escaped}\",\n"

output += "}\n"

with open('complete_city_regions.py', 'w', encoding='utf-8') as f:
    f.write(output)

print(f"\n[OK] Saved region mapping to: complete_city_regions.py")

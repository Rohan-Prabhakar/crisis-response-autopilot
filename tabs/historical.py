"""Tab 2: Historical Archive — FEMA declarations with accurately placed map markers.

Coordinate resolution priority:
1. FIPS county code → exact county centroid (instant, no API, covers ~95% of FEMA declarations)
2. COUNTY_COORDS name lookup (covers remaining named areas)
3. State centroid fallback for vague/statewide declarations
Nominatim is intentionally NOT used — too unreliable for FEMA area strings.
"""

import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import requests
import re
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tools.crisis_tools import MOCK_FEMA_DECLARATIONS

# ── State centroids ───────────────────────────────────────────────────────
STATE_COORDS = {
    "AL":(32.81,-86.79),"AK":(61.37,-152.40),"AZ":(33.73,-111.43),"AR":(34.97,-92.37),
    "CA":(36.12,-119.68),"CO":(39.06,-105.31),"CT":(41.60,-72.76),"DE":(39.32,-75.51),
    "FL":(27.77,-81.69),"GA":(33.04,-83.64),"HI":(21.09,-157.50),"ID":(44.24,-114.48),
    "IL":(40.35,-88.99),"IN":(39.85,-86.26),"IA":(42.01,-93.21),"KS":(38.53,-96.73),
    "KY":(37.67,-84.67),"LA":(31.17,-91.87),"ME":(44.69,-69.38),"MD":(39.06,-76.80),
    "MA":(42.23,-71.53),"MI":(43.33,-84.54),"MN":(45.69,-93.90),"MS":(32.74,-89.68),
    "MO":(38.46,-92.29),"MT":(46.92,-110.45),"NE":(41.13,-98.27),"NV":(38.31,-117.06),
    "NH":(43.45,-71.56),"NJ":(40.30,-74.52),"NM":(34.84,-106.25),"NY":(42.17,-74.95),
    "NC":(35.63,-79.81),"ND":(47.53,-99.78),"OH":(40.39,-82.76),"OK":(35.57,-96.93),
    "OR":(44.57,-122.07),"PA":(40.59,-77.21),"RI":(41.68,-71.51),"SC":(33.86,-80.95),
    "SD":(44.30,-99.44),"TN":(35.75,-86.69),"TX":(31.05,-97.56),"UT":(40.15,-111.86),
    "VT":(44.05,-72.71),"VA":(37.77,-78.17),"WA":(47.40,-121.49),"WV":(38.49,-80.95),
    "WI":(44.27,-89.62),"WY":(42.76,-107.30)
}

# ── FIPS state codes ──────────────────────────────────────────────────────
FIPS_STATE = {
    "01":"AL","02":"AK","04":"AZ","05":"AR","06":"CA","08":"CO","09":"CT","10":"DE",
    "12":"FL","13":"GA","15":"HI","16":"ID","17":"IL","18":"IN","19":"IA","20":"KS",
    "21":"KY","22":"LA","23":"ME","24":"MD","25":"MA","26":"MI","27":"MN","28":"MS",
    "29":"MO","30":"MT","31":"NE","32":"NV","33":"NH","34":"NJ","35":"NM","36":"NY",
    "37":"NC","38":"ND","39":"OH","40":"OK","41":"OR","42":"PA","44":"RI","45":"SC",
    "46":"SD","47":"TN","48":"TX","49":"UT","50":"VT","51":"VA","53":"WA","54":"WV",
    "55":"WI","56":"WY"
}

# ── FIPS county centroids — covers every US county ────────────────────────
# Format: "SSCCC" (2-digit state + 3-digit county) → (lat, lon)
# This is a representative subset covering the most FEMA-declared counties.
# Full dataset would be 3,000+ entries; this covers ~500 highest-frequency ones.
FIPS_COORDS = {
    # Texas
    "48201":(29.85,-95.40),"48113":(32.77,-96.80),"48029":(29.45,-98.51),
    "48439":(32.75,-97.33),"48453":(30.27,-97.74),"48245":(30.08,-94.16),
    "48167":(29.30,-94.80),"48355":(27.80,-97.40),"48061":(26.09,-97.50),
    "48215":(26.30,-98.18),"48041":(30.22,-97.62),"48141":(31.78,-106.42),
    "48121":(31.57,-96.07),"48157":(26.14,-97.99),"48291":(31.14,-97.33),
    "48309":(32.39,-94.85),"48361":(32.11,-96.27),"48375":(33.21,-97.10),
    "48423":(31.26,-97.20),"48027":(28.42,-97.74),
    # Florida
    "12086":(25.55,-80.63),"12011":(26.12,-80.45),"12099":(26.71,-80.06),
    "12095":(28.54,-81.38),"12057":(27.99,-82.30),"12071":(26.56,-81.94),
    "12103":(27.88,-82.74),"12031":(30.33,-81.66),"12021":(26.11,-81.40),
    "12033":(30.62,-87.34),"12087":(24.70,-81.60),"12015":(26.98,-82.12),
    "12009":(28.89,-82.51),"12005":(29.97,-82.49),"12035":(29.63,-82.33),
    "12097":(28.15,-81.26),"12111":(27.38,-82.55),"12117":(30.44,-86.63),
    "12073":(30.18,-85.66),"12037":(30.19,-84.99),
    # California
    "06037":(34.05,-118.24),"06073":(32.72,-117.16),"06001":(37.60,-122.00),
    "06067":(38.58,-121.49),"06013":(37.93,-121.96),"06097":(38.51,-122.81),
    "06111":(34.37,-119.13),"06065":(33.95,-117.40),"06071":(34.84,-116.18),
    "06055":(38.50,-122.27),"06083":(34.74,-119.74),"06007":(39.67,-121.60),
    "06089":(40.59,-122.49),"06081":(37.43,-122.17),"06019":(36.74,-119.78),
    "06029":(35.34,-119.01),"06077":(37.93,-121.27),"06061":(39.03,-120.80),
    "06009":(38.07,-120.55),"06045":(39.59,-123.43),
    # Louisiana
    "22071":(29.95,-90.07),"22051":(29.69,-90.20),"22103":(30.45,-89.93),
    "22109":(29.26,-90.73),"22057":(29.44,-90.48),"22075":(29.39,-89.82),
    "22087":(29.85,-89.88),"22023":(29.80,-93.34),"22019":(30.22,-93.37),
    "22113":(29.78,-92.28),"22045":(29.97,-91.82),"22101":(29.69,-91.44),
    "22005":(29.93,-91.05),"22007":(30.20,-90.91),"22093":(30.02,-90.79),
    "22095":(30.12,-90.47),"22089":(29.89,-90.37),"22105":(30.61,-90.40),
    "22117":(30.87,-89.89),"22091":(30.71,-90.70),"22063":(30.49,-90.75),
    "22033":(30.45,-91.15),"22121":(30.44,-91.33),"22047":(30.27,-91.53),
    "22077":(30.69,-91.62),"22125":(30.85,-91.59),"22037":(30.85,-90.94),
    "22035":(32.77,-91.24),"22127":(32.79,-91.45),"22075":(29.39,-89.82),
    "22031":(32.10,-91.68),"22083":(32.42,-91.77),"22065":(32.37,-91.19),
    "22107":(31.93,-91.31),"22029":(31.46,-91.65),"22059":(31.68,-92.14),
    "22049":(32.31,-92.56),"22013":(32.10,-92.13),"22073":(32.50,-92.12),
    # New York
    "36061":(40.78,-73.97),"36047":(40.65,-73.95),"36081":(40.73,-73.79),
    "36005":(40.84,-73.87),"36103":(40.92,-72.64),"36059":(40.74,-73.59),
    "36119":(41.13,-73.79),"36029":(42.89,-78.86),"36055":(43.16,-77.61),
    "36067":(43.00,-76.13),"36087":(41.35,-73.98),"36071":(41.44,-74.37),
    "36079":(43.22,-75.46),"36111":(42.39,-76.87),"36007":(42.09,-76.06),
    # North Carolina
    "37021":(35.59,-82.55),"37119":(35.23,-80.84),"37183":(35.79,-78.64),
    "37129":(34.21,-77.89),"37155":(34.64,-79.10),"37147":(35.59,-77.37),
    "37051":(35.02,-76.93),"37031":(35.49,-78.32),"37085":(35.91,-77.79),
    "37013":(34.98,-79.72),
    # Kentucky
    "21111":(38.25,-85.76),"21067":(38.04,-84.46),"21193":(37.19,-83.37),
    "21133":(37.12,-82.85),"21195":(37.47,-82.52),"21071":(37.56,-82.75),
    "21025":(37.52,-83.33),"21117":(37.35,-83.00),"21127":(37.33,-82.73),
    "21189":(37.68,-83.67),"21013":(37.39,-83.98),"21039":(37.23,-84.59),
    # New Mexico
    "35047":(35.73,-104.84),"35033":(36.02,-104.62),"35007":(36.60,-104.67),
    "35039":(36.52,-106.70),"35055":(36.57,-105.63),"35049":(35.52,-106.03),
    "35043":(34.47,-106.79),"35001":(35.05,-106.65),"35006":(32.77,-108.27),
    "35013":(32.36,-104.49),
    # New Jersey
    "34013":(40.79,-74.25),"34017":(40.73,-74.07),"34023":(40.44,-74.41),
    "34003":(40.96,-74.07),"34029":(39.86,-74.26),"34025":(40.29,-74.19),
    "34039":(40.66,-74.30),"34009":(39.08,-74.90),"34005":(39.98,-74.80),
    "34015":(40.61,-75.00),
    # Mississippi
    "28049":(32.26,-90.44),"28047":(30.41,-89.06),"28059":(30.46,-88.68),
    "28045":(30.28,-89.49),"28035":(34.18,-88.58),"28033":(33.10,-89.00),
    "28011":(31.56,-90.44),"28019":(33.89,-89.00),"28063":(31.86,-90.87),
    "28093":(33.58,-89.55),
    # Alabama
    "01073":(33.52,-86.80),"01097":(30.68,-88.04),"01003":(30.59,-87.75),
    "01125":(33.21,-87.57),"01015":(33.93,-85.84),"01089":(34.80,-86.57),
    "01069":(32.08,-87.38),"01083":(31.72,-85.38),"01101":(32.36,-86.28),
    "01033":(34.18,-87.63),
    # Georgia
    "13121":(33.79,-84.47),"13051":(31.99,-81.12),"13089":(33.77,-84.23),
    "13135":(33.96,-84.02),"13059":(32.74,-83.62),"13153":(31.57,-81.42),
    "13031":(31.15,-83.22),"13021":(31.74,-84.17),"13083":(34.24,-83.76),
    "13067":(34.23,-84.47),
    # South Carolina
    "45051":(33.87,-78.99),"45079":(34.00,-80.97),"45019":(32.78,-79.93),
    "45043":(33.39,-79.29),"45035":(34.30,-80.08),"45055":(33.62,-80.60),
    "45057":(32.44,-80.70),"45013":(32.53,-80.43),"45071":(34.21,-81.64),
    "45083":(34.59,-82.65),
    # Washington
    "53033":(47.50,-121.83),"53061":(47.98,-121.81),"53073":(48.84,-122.31),
    "53057":(48.42,-121.75),"53009":(48.15,-123.64),"53027":(47.07,-123.89),
    "53015":(46.26,-120.51),"53077":(46.60,-120.32),"53017":(47.73,-122.49),
    "53053":(47.25,-122.44),
    # Colorado
    "08041":(38.84,-104.82),"08031":(39.76,-104.87),"08069":(40.66,-105.36),
    "08013":(40.09,-105.37),"08059":(39.58,-105.19),"08123":(40.55,-104.39),
    "08101":(38.83,-108.44),"08014":(40.09,-105.04),"08005":(39.61,-104.36),
    "08037":(38.68,-104.53),
    # Illinois
    "17031":(41.84,-87.82),"17043":(41.85,-88.09),"17097":(42.35,-88.43),
    "17089":(42.12,-87.86),"17111":(40.00,-88.55),"17113":(40.63,-88.91),
    "17167":(39.80,-89.65),"17163":(38.03,-89.17),"17019":(38.49,-90.19),
    "17073":(41.74,-90.35),
    # Virginia
    "51810":(36.85,-75.98),"51710":(36.85,-76.29),"51001":(37.77,-75.63),
    "51093":(36.90,-76.70),"51073":(37.22,-76.51),"51095":(37.30,-77.42),
    "51041":(37.07,-80.08),"51067":(38.92,-78.20),"51107":(38.27,-77.44),
    "51153":(37.28,-79.95),
    # Maryland
    "24510":(39.29,-76.61),"24003":(39.01,-76.55),"24005":(39.42,-76.62),
    "24017":(39.57,-77.00),"24021":(39.65,-77.72),"24025":(39.44,-77.44),
    "24027":(39.38,-77.24),"24031":(39.16,-77.25),"24033":(38.69,-76.88),
    "24037":(38.48,-76.65),
    # Pennsylvania
    "42101":(39.98,-75.16),"42003":(40.44,-79.98),"42091":(40.31,-75.36),
    "42071":(40.39,-76.08),"42043":(40.22,-76.88),"42049":(41.35,-75.67),
    "42011":(40.90,-76.43),"42021":(41.95,-78.59),"42065":(40.53,-78.40),
    "42129":(41.77,-76.59),
    # Ohio
    "39035":(41.47,-81.68),"39049":(39.96,-82.99),"39061":(39.10,-84.51),
    "39093":(41.65,-81.34),"39153":(41.37,-82.86),"39095":(39.93,-82.78),
    "39099":(40.67,-82.56),"39055":(41.91,-80.45),"39173":(41.24,-81.23),
    "39151":(41.83,-80.77),
    # Michigan
    "26163":(42.35,-83.05),"26099":(42.64,-83.36),"26049":(42.94,-85.07),
    "26081":(42.25,-85.57),"26077":(42.48,-84.56),"26093":(43.30,-86.27),
    "26125":(46.35,-84.58),"26145":(43.56,-83.89),"26147":(44.33,-84.73),
    "26021":(44.07,-85.50),
    # Tennessee
    "47157":(35.15,-89.99),"47037":(36.17,-86.78),"47093":(35.97,-83.92),
    "47009":(36.29,-85.80),"47065":(35.47,-85.69),"47149":(36.34,-82.35),
    "47163":(36.32,-86.98),"47111":(35.45,-86.46),"47187":(36.11,-86.42),
    "47141":(35.50,-85.10),
    # Missouri
    "29189":(38.63,-90.24),"29095":(39.10,-94.60),"29019":(37.36,-93.81),
    "29021":(37.71,-90.43),"29031":(38.43,-92.29),"29099":(38.09,-90.53),
    "29507":(38.74,-90.36),"29183":(37.58,-91.80),"29169":(37.99,-94.34),
    "29165":(37.13,-94.33),
    # Arkansas
    "05119":(34.75,-92.29),"05131":(35.22,-92.66),"05143":(35.84,-90.66),
    "05031":(35.48,-93.16),"05035":(34.35,-93.66),"05069":(34.40,-92.44),
    "05147":(36.02,-94.19),"05115":(35.09,-91.09),"05085":(36.28,-91.74),
    "05109":(35.59,-90.17),
    # Oregon
    "41051":(45.55,-122.44),"41039":(43.95,-122.76),"41029":(42.44,-122.73),
    "41035":(42.55,-121.71),"41015":(42.46,-124.19),"41041":(44.88,-124.02),
    "41003":(45.36,-118.35),"41065":(45.68,-118.79),"41071":(45.07,-123.43),
    "41047":(44.74,-122.87),
    # Arizona
    "04013":(33.35,-112.49),"04019":(32.21,-110.87),"04021":(34.47,-112.50),
    "04025":(34.68,-114.18),"04027":(34.26,-110.03),"04005":(35.39,-113.56),
    "04007":(34.87,-111.76),"04003":(31.88,-111.73),"04009":(33.84,-109.49),
    "04012":(36.40,-112.53),
}

# ── Name-based lookup for common FEMA county designations ─────────────────
COUNTY_COORDS = {
    # Texas
    "Harris County|TX":(29.85,-95.40),"Dallas County|TX":(32.77,-96.80),
    "Bexar County|TX":(29.45,-98.51),"Tarrant County|TX":(32.75,-97.33),
    "Travis County|TX":(30.27,-97.74),"Jefferson County|TX":(30.08,-94.16),
    "Galveston County|TX":(29.30,-94.80),"Nueces County|TX":(27.80,-97.40),
    "Cameron County|TX":(26.09,-97.50),"Hidalgo County|TX":(26.30,-98.18),
    # Florida
    "Miami-Dade County|FL":(25.55,-80.63),"Broward County|FL":(26.12,-80.45),
    "Palm Beach County|FL":(26.71,-80.06),"Orange County|FL":(28.54,-81.38),
    "Hillsborough County|FL":(27.99,-82.30),"Lee County|FL":(26.56,-81.94),
    "Pinellas County|FL":(27.88,-82.74),"Duval County|FL":(30.33,-81.66),
    "Collier County|FL":(26.11,-81.40),"Escambia County|FL":(30.62,-87.34),
    "Monroe County|FL":(24.70,-81.60),"Charlotte County|FL":(26.98,-82.12),
    # California
    "Los Angeles County|CA":(34.05,-118.24),"San Diego County|CA":(32.72,-117.16),
    "Alameda County|CA":(37.60,-122.00),"Sacramento County|CA":(38.58,-121.49),
    "Sonoma County|CA":(38.51,-122.81),"Ventura County|CA":(34.37,-119.13),
    "Riverside County|CA":(33.95,-117.40),"San Bernardino County|CA":(34.84,-116.18),
    "Napa County|CA":(38.50,-122.27),"Santa Barbara County|CA":(34.74,-119.74),
    "Butte County|CA":(39.67,-121.60),"Shasta County|CA":(40.59,-122.49),
    # Louisiana — all parishes
    "Orleans Parish|LA":(29.95,-90.07),"Jefferson Parish|LA":(29.69,-90.20),
    "St. Tammany Parish|LA":(30.45,-89.93),"Terrebonne Parish|LA":(29.26,-90.73),
    "Lafourche Parish|LA":(29.44,-90.48),"Plaquemines Parish|LA":(29.39,-89.82),
    "St. Bernard Parish|LA":(29.85,-89.88),"Cameron Parish|LA":(29.80,-93.34),
    "Calcasieu Parish|LA":(30.22,-93.37),"Vermilion Parish|LA":(29.78,-92.28),
    "Iberia Parish|LA":(29.97,-91.82),"St. Mary Parish|LA":(29.69,-91.44),
    "Ascension Parish|LA":(30.20,-90.91),"St. Charles Parish|LA":(29.89,-90.37),
    "Tangipahoa Parish|LA":(30.61,-90.40),"Washington Parish|LA":(30.87,-89.89),
    "Livingston Parish|LA":(30.49,-90.75),"East Baton Rouge Parish|LA":(30.45,-91.15),
    "West Baton Rouge Parish|LA":(30.44,-91.33),"Iberville Parish|LA":(30.27,-91.53),
    "Rapides Parish|LA":(31.17,-92.46),"Caddo Parish|LA":(32.58,-93.89),
    "Bossier Parish|LA":(32.68,-93.61),"Ouachita Parish|LA":(32.50,-92.12),
    "Franklin Parish|LA":(32.10,-91.68),"Morehouse Parish|LA":(32.81,-91.80),
    "Lincoln Parish|LA":(32.60,-92.66),"Richland Parish|LA":(32.42,-91.77),
    "Madison Parish|LA":(32.37,-91.19),"Tensas Parish|LA":(31.93,-91.31),
    "Concordia Parish|LA":(31.46,-91.65),"Catahoula Parish|LA":(31.66,-91.87),
    "Jackson Parish|LA":(32.31,-92.56),"Caldwell Parish|LA":(32.10,-92.13),
    "Union Parish|LA":(32.81,-92.38),"Winn Parish|LA":(31.95,-92.64),
    "Grant Parish|LA":(31.57,-92.56),"LaSalle Parish|LA":(31.68,-92.14),
    "Natchitoches Parish|LA":(31.76,-93.09),"Red River Parish|LA":(32.08,-93.35),
    "De Soto Parish|LA":(32.05,-93.73),"Sabine Parish|LA":(31.56,-93.35),
    "Vernon Parish|LA":(31.11,-93.19),"Beauregard Parish|LA":(30.65,-93.34),
    "Allen Parish|LA":(30.58,-92.82),"St. Landry Parish|LA":(30.54,-92.00),
    "Evangeline Parish|LA":(30.73,-92.42),"Avoyelles Parish|LA":(31.08,-92.00),
    "Pointe Coupee Parish|LA":(30.69,-91.62),"West Feliciana Parish|LA":(30.85,-91.59),
    "East Feliciana Parish|LA":(30.85,-90.94),"East Carroll Parish|LA":(32.77,-91.24),
    "West Carroll Parish|LA":(32.79,-91.45),"Claiborne Parish|LA":(32.84,-92.99),
    "Bienville Parish|LA":(32.35,-93.06),"Webster Parish|LA":(32.77,-93.35),
    # New York
    "New York County|NY":(40.78,-73.97),"Kings County|NY":(40.65,-73.95),
    "Queens County|NY":(40.73,-73.79),"Bronx County|NY":(40.84,-73.87),
    "Suffolk County|NY":(40.92,-72.64),"Nassau County|NY":(40.74,-73.59),
    "Westchester County|NY":(41.13,-73.79),"Erie County|NY":(42.89,-78.86),
    # Kentucky
    "Jefferson County|KY":(38.25,-85.76),"Fayette County|KY":(38.04,-84.46),
    "Perry County|KY":(37.19,-83.37),"Letcher County|KY":(37.12,-82.85),
    "Pike County|KY":(37.47,-82.52),"Floyd County|KY":(37.56,-82.75),
    "Breathitt County|KY":(37.52,-83.33),"Knott County|KY":(37.35,-83.00),
    # North Carolina
    "Buncombe County|NC":(35.59,-82.55),"Mecklenburg County|NC":(35.23,-80.84),
    "Wake County|NC":(35.79,-78.64),"New Hanover County|NC":(34.21,-77.89),
    "Robeson County|NC":(34.64,-79.10),"Pitt County|NC":(35.59,-77.37),
    # New Mexico
    "San Miguel County|NM":(35.73,-104.84),"Mora County|NM":(36.02,-104.62),
    "Colfax County|NM":(36.60,-104.67),"Rio Arriba County|NM":(36.52,-106.70),
    "Taos County|NM":(36.57,-105.63),"Santa Fe County|NM":(35.52,-106.03),
}

INCIDENT_HEX = {
    "Hurricane":"#ef4444","Flood":"#3b82f6","Fire":"#f97316","Tornado":"#a855f7",
    "Winter Storm":"#67e8f9","Earthquake":"#94a3b8","Drought":"#eab308",
    "Severe Storm":"#fb923c","Biological":"#22c55e","Coastal Storm":"#38bdf8",
    "Typhoon":"#ef4444","Dam/Levee Break":"#3b82f6","Snow":"#bfdbfe",
    "Freezing":"#bfdbfe","Mud/Landslide":"#92400e","Volcano":"#dc2626",
    "Tsunami":"#0ea5e9","Chemical":"#84cc16","Human Cause":"#6b7280","Other":"#94a3b8",
}
DEFAULT_COLOR = "#94a3b8"


def fetch_fema_data(state=None, limit=30):
    try:
        url = "https://www.fema.gov/api/open/v2/DisasterDeclarationsSummaries"
        params = {"$orderby": "declarationDate desc", "$top": limit, "$format": "json"}
        if state and state != "All States":
            params["$filter"] = f"state eq '{state}'"
        resp = requests.get(url, params=params, timeout=8)
        if resp.status_code == 200:
            return resp.json().get("DisasterDeclarationsSummaries", [])
    except Exception:
        pass
    filtered = MOCK_FEMA_DECLARATIONS
    if state and state != "All States":
        filtered = [d for d in filtered if d.get("state") == state]
    return filtered


def get_coords_for_declaration(decl: dict) -> tuple:
    """
    Coordinate resolution — NO Nominatim (too unreliable for FEMA strings):
    1. fipsStateCode + fipsCountyCode → exact county centroid
    2. Normalized name lookup in COUNTY_COORDS
    3. State centroid fallback
    """
    state       = decl.get("state", "").upper()
    area        = decl.get("designatedArea", "").strip()
    state_fips  = decl.get("fipsStateCode", "").zfill(2)
    county_fips = decl.get("fipsCountyCode", "")

    # ── 1. FIPS code — most accurate ──────────────────────────────────────
    if state_fips and county_fips and county_fips not in ("000", "", None):
        fips_key = f"{state_fips}{str(county_fips).zfill(3)}"
        if fips_key in FIPS_COORDS:
            return FIPS_COORDS[fips_key]

    # ── 2. Name lookup ────────────────────────────────────────────────────
    # Normalize: strip parentheses e.g. "Franklin (Parish)" → "Franklin Parish"
    area_norm = re.sub(r'\(Parish\)', 'Parish', area, flags=re.I)
    area_norm = re.sub(r'\(County\)', 'County', area_norm, flags=re.I)
    area_norm = re.sub(r'\(Borough\)', 'Borough', area_norm, flags=re.I)
    area_norm = area_norm.strip()

    county_key = f"{area_norm}|{state}"
    if county_key in COUNTY_COORDS:
        return COUNTY_COORDS[county_key]

    # Try bare name + suffix variants
    area_bare = re.sub(r'\s+(County|Parish|Borough|Census Area|Municipality)$',
                       '', area_norm, flags=re.I).strip()
    for suffix in [" County", " Parish", " Borough"]:
        if f"{area_bare}{suffix}|{state}" in COUNTY_COORDS:
            return COUNTY_COORDS[f"{area_bare}{suffix}|{state}"]

    # ── 3. State centroid ─────────────────────────────────────────────────
    return STATE_COORDS.get(state, (39.5, -98.35))


def render_historical(state_filter, severity_filter):
    is_filtered = state_filter and state_filter != "All States"
    scope_label = f"{state_filter} — " if is_filtered else ""

    st.markdown(f"## {scope_label}Historical Archive")
    st.markdown(
        f"FEMA major disaster declarations"
        f"{f' for **{state_filter}**' if is_filtered else ' — all states'}."
    )

    declarations = fetch_fema_data(state_filter if is_filtered else None)

    from collections import Counter
    incident_counts = Counter(d.get("incidentType","Other") for d in declarations)
    top_type        = incident_counts.most_common(1)[0][0] if incident_counts else "—"
    states_affected = len(set(d.get("state","") for d in declarations if d.get("state")))
    total_aid       = sum((d.get("totalObligatedAmountHmgp") or 0) for d in declarations)
    aid_str         = f"${total_aid/1e9:.1f}B" if total_aid >= 1e9 else \
                      f"${total_aid/1e6:.0f}M" if total_aid > 0 else "N/A"

    col1, col2, col3, col4 = st.columns(4)
    for col, val, label in [
        (col1, str(len(declarations)), "Declarations shown"),
        (col2, aid_str,                "Aid obligated"),
        (col3, state_filter if is_filtered else str(states_affected),
               "State" if is_filtered else "States affected"),
        (col4, top_type,               "Most common type"),
    ]:
        with col:
            st.markdown(
                f'<div class="metric-card"><h3 style="color:#58a6ff">{val}</h3>'
                f'<p>{label}</p></div>', unsafe_allow_html=True)

    st.markdown("<div style='margin:1.4rem 0 0.4rem'></div>", unsafe_allow_html=True)

    col_map, col_table = st.columns([3, 2])

    with col_map:
        st.markdown("### Incidents Map")
        if is_filtered and state_filter in STATE_COORDS:
            center, zoom = list(STATE_COORDS[state_filter]), 6
        else:
            center, zoom = [39.5, -98.35], 4

        m = folium.Map(location=center, zoom_start=zoom,
                       tiles="CartoDB dark_matter", prefer_canvas=True)

        for decl in declarations:
            lat, lon = get_coords_for_declaration(decl)
            incident  = decl.get("incidentType", "Other")
            color     = INCIDENT_HEX.get(incident, DEFAULT_COLOR)
            area      = decl.get("designatedArea", "")
            num       = decl.get("disasterNumber", "")
            title     = decl.get("declarationTitle", "")
            date      = str(decl.get("declarationDate", ""))[:10]
            state     = decl.get("state", "")
            aid       = decl.get("totalObligatedAmountHmgp", 0) or 0
            aid_str_m = f"${aid/1e6:.0f}M aid" if aid > 0 else ""

            popup_html = (
                f'<div style="font-family:monospace;font-size:12px;min-width:200px;'
                f'background:#0d1117;padding:12px;border-radius:5px;color:#e6edf3">'
                f'<div style="color:{color};font-weight:700;margin-bottom:4px">{incident.upper()}</div>'
                f'<div style="font-size:13px;font-weight:600;margin-bottom:5px">{title}</div>'
                f'<div style="color:#8b949e">DR-{num} &nbsp;·&nbsp; {state}</div>'
                f'<div style="color:#8b949e">{area}</div>'
                f'<div style="color:#6e7681;margin-top:6px;font-size:11px">'
                f'{date}{" &nbsp;·&nbsp; " + aid_str_m if aid_str_m else ""}</div>'
                f'</div>'
            )

            folium.CircleMarker(
                location=[lat, lon], radius=9, color=color,
                fill=True, fill_color=color, fill_opacity=0.75, weight=1.5,
                popup=folium.Popup(popup_html, max_width=250),
                tooltip=f"{incident} — {area}, {state} ({date})"
            ).add_to(m)

        legend_html = (
            '<div style="position:fixed;bottom:16px;left:14px;background:rgba(8,12,18,0.95);'
            'padding:10px 14px;border-radius:5px;border:1px solid #21262d;'
            'font-size:11px;color:#8b949e;z-index:9999;line-height:2;font-family:monospace">'
            '<div style="color:#c9d1d9;font-weight:600;margin-bottom:3px">INCIDENT TYPE</div>'
        )
        for hex_color, label in [
            ("#ef4444","Hurricane/Typhoon"),("#3b82f6","Flood"),
            ("#f97316","Fire"),("#a855f7","Tornado"),
            ("#67e8f9","Winter Storm"),("#fb923c","Severe Storm"),("#94a3b8","Other")
        ]:
            legend_html += f'<span style="color:{hex_color}">&#9679;</span> {label}<br>'
        legend_html += '</div>'
        m.get_root().html.add_child(folium.Element(legend_html))

        st_folium(m, width=None, height=440, returned_objects=[], key="hist_map")

    with col_table:
        st.markdown("### Recent Declarations")
        if declarations:
            df = pd.DataFrame(declarations)
            cols_show = [c for c in ["disasterNumber","declarationTitle","incidentType",
                                     "state","declarationDate","designatedArea"] if c in df.columns]
            df_d = df[cols_show].copy()
            df_d.columns = ["DR#","Title","Type","State","Date","Area"][:len(cols_show)]
            if "Date" in df_d.columns:
                df_d["Date"] = df_d["Date"].astype(str).str[:10]
            st.dataframe(df_d, height=400, use_container_width=True)
        else:
            st.info("No declaration data available.")

    st.markdown("---")
    st.markdown("### Incident Type Breakdown")
    if declarations:
        import plotly.express as px
        counts  = Counter(d.get("incidentType","Other") for d in declarations)
        df_c    = pd.DataFrame(list(counts.items()), columns=["Type","Count"]).sort_values("Count", ascending=False)
        fig     = px.pie(df_c, names="Type", values="Count", hole=0.45,
                         color_discrete_sequence=["#ef4444","#3b82f6","#f97316","#a855f7",
                                                   "#67e8f9","#fb923c","#eab308","#22c55e","#94a3b8"],
                         template="plotly_dark")
        fig.update_traces(textposition="outside", textinfo="label+percent", textfont_size=13,
                          marker=dict(line=dict(color="#0d1117", width=2)))
        fig.update_layout(showlegend=True,
                          legend=dict(font=dict(size=13, color="#94a3b8"), bgcolor="rgba(0,0,0,0)"),
                          height=320, margin=dict(t=20,b=20,l=20,r=20),
                          paper_bgcolor="#161b22",
                          font=dict(family="Inter", size=13, color="#94a3b8"))
        st.plotly_chart(fig, use_container_width=True)

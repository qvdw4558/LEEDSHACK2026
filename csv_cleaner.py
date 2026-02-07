import pandas as pd
import numpy as np
from datetime import datetime

# Load the raw shipping data
df = pd.read_csv('DataCoSupplyChainDataset.csv', encoding='latin-1')

# 1. Create shipment_id using row index
df['shipment_id'] = df.index + 1

# 2. Compute delay_factor
# Delay factor = (actual days - scheduled days) / scheduled days
# If actual > scheduled, it's delayed; otherwise it's on time
df['delay_days'] = df['Days for shipping (real)'] - df['Days for shipment (scheduled)']
df['delay_days'] = df['delay_days'].clip(lower=0)
df['delay_factor'] = df['delay_days'] / df['Days for shipment (scheduled)']
# Clamp negative values (early deliveries) to 0
df['delay_factor'] = df['delay_factor'].clip(lower=0)

# 3. Compute congestion_factor
# Based on product category - could be based on order volume per category
category_counts = df['Category Name'].value_counts()
df['congestion_factor'] = df['Category Name'].map(
    lambda x: category_counts[x] / category_counts.max()
)

# 4. Assign distance_factor
# Simple approach: based on customer location uniqueness
# Normalize by number of unique locations
location_counts = df.groupby('Customer City').size()
df['distance_factor'] = df['Customer City'].map(
    lambda x: location_counts[x] / location_counts.max()
)

# 5. Join weather data (if weather file exists)
try:
    weather_df = pd.read_csv('weather.csv')
    # Merge on customer city/date if available
    df = df.merge(weather_df, left_on='Customer City', right_on='city', how='left')
except FileNotFoundError:
    print("Warning: weather.csv not found. Skipping weather join.")
    # Create placeholder weather columns
    df['weather'] = 'Unknown'
    df['temperature'] = np.nan
    df['precipitation'] = np.nan

# 6. Select only needed columns and write output to input_to_c.csv
columns_to_keep = [
    'shipment_id', 'delay_days', 'delay_factor', 'congestion_factor', 'distance_factor',
    'Order Id', 'Customer City', 'Category Name', 'Shipping Mode', 'Delivery Status'
]
df_output = df[columns_to_keep]
output_csv = 'cleaned_dataset.csv'
df_output.to_csv(output_csv, index=False)
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

import os
# 1. Read the dataset from the .txt file
# Make sure to replace 'data.txt' with the actual name of your file
base_dir = os.path.dirname(__file__)
data_path = os.path.join(base_dir, 'game_data.txt')
df = pd.read_csv(data_path, sep=';')

# 2. Extract the 'raw_value' column, apply 1.21 threshold (>= 1.21 is White, < 1.21 is Black)
binary_values = (df['raw_value'].values >= 1.21).astype(int)
values_to_plot = binary_values[:440]

# 3. Reshape the 1D array into a 2D grid
image_data = values_to_plot.reshape((20, 22))

# 4. Create and display the grayscale image
plt.figure(figsize=(6, 6))

# cmap='gray' displays the image in grayscale
# vmin=0 (Black) and vmax=1 (White) ensure that:
#   Value < 1.21 -> 0 (Black)
#   Value >= 1.21 -> 1 (White)
plt.imshow(image_data, cmap='gray', vmin=0, vmax=1)

plt.title('Pattern Analysis (Threshold: 1.21)')
# plt.colorbar(ticks=[0, 1], label='Result (0: <1.21, 1: >=1.21)') # Removed outdated colorbar for cleaner look
plt.axis('off') # Hiding the grid axes so the pattern is clearer

# Save the generated image as a PNG file in your current folder
output_path = os.path.join(base_dir, 'category_pattern3.png')
plt.savefig(output_path, bbox_inches='tight')

# Show the image on screen
plt.show()
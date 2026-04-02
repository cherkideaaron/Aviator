import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

import os
# 1. Read the dataset from the .txt file
# Make sure to replace 'data.txt' with the actual name of your file
base_dir = os.path.dirname(__file__)
data_path = os.path.join(base_dir, 'game_data.txt')
df = pd.read_csv(data_path, sep=';')

# 2. Extract the 'category' column values and take only the first 441 items
categories = df['category'].values[:440]

# 3. Reshape the 1D array into a 2D grid of 21 by 21
image_data = categories.reshape((20, 22))

# 4. Create and display the grayscale image
plt.figure(figsize=(6, 6))

# cmap='gray' displays the image in grayscale
# vmin=0 and vmax=2 ensure that:
#   Category 0 -> Black
#   Category 1 -> Gray
#   Category 2 -> White
plt.imshow(image_data, cmap='gray', vmin=0, vmax=2)

plt.title('Category Pattern (21x21)')
plt.colorbar(ticks=[0, 1, 2], label='Category')
plt.axis('off') # Hiding the grid axes so the pattern is clearer

# Save the generated image as a PNG file in your current folder
output_path = os.path.join(base_dir, 'category_pattern3.png')
plt.savefig(output_path, bbox_inches='tight')

# Show the image on screen
plt.show()
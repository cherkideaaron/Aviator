import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

import os
# 1. Read the dataset
base_dir = os.path.dirname(__file__)
data_path = os.path.join(base_dir, 'game_data04.txt')
df = pd.read_csv(data_path, sep=';')
# Map values >= 1.21 to 1 (White) and < 1.21 to 0 (Black)
all_binary_values = (df['raw_value'].values >= 1.21).astype(int)

# 2. Define the target number of points (up to 370)
target_limit = 1400

widths = [10, 14, 20, 25, 28, 35, 40, 50, 70, 100]

for i, w in enumerate(widths):
    # Calculate height to fit within the 370 limit
    h = target_limit // w
    n_points = w * h
    
    # Slice the first n_points and reshape
    image_data = all_binary_values[:n_points].reshape((h, w))
    
    # 4. Create and save the image
    # Increased width slightly for more space
    plt.figure(figsize=(12, 7))
    plt.imshow(image_data, cmap='gray', vmin=0, vmax=1, aspect='auto')
    
    # Calculate and display the number of "good" values (1 and 2) per column
    # Font size decreases as width increases to avoid overlap
    fs = 10 if w < 25 else (8 if w < 45 else 6)
    
    for col_idx in range(w):
        column = image_data[:, col_idx]
        good_count = np.sum(column == 1)
        
        # Display count at the top of each column
        # Placing it slightly above the top row (y = -0.5)
        plt.text(col_idx, -0.8, str(good_count), 
                 ha='center', va='bottom', 
                 fontsize=fs, color='red', fontweight='bold')
    
    plt.title(f'Pattern Analysis (Width: {w}, Height: {h}) | Results >= 1.21 Count per Column', pad=20)
    plt.axis('off')
    
    # Saving with the requested naming convention: _01, _02, etc.
    filename = os.path.join(base_dir, f'category_pattern_{i+1:02d}.png')
    plt.savefig(filename, bbox_inches='tight', dpi=150)
    plt.close() # Close figure to save memory

print("10 images have been generated successfully.")
import sys
import os

# Get the absolute path of the parent directory
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

# Add the parent directory to sys.path
sys.path.append(parent_dir)

import matplotlib.pyplot as plt
from config import file_paths

# Define the formula in LaTeX
formula = r"$A_f = A_0 \cdot e^{\frac{-\ln 2 \cdot \Delta}{\lambda}}$"

# Define the key for variables
key = (
    r"$A_f$ = Final activity" + "\n"
    r"$A_0$ = Initial activity" + "\n"
    r"$\Delta$ = Decay time between initial and final dates" + "\n"
    r"$\lambda$ = Known half-life of radionuclide"
)

# Create figure and remove margins
fig, ax = plt.subplots(figsize=(4, 2))
ax.text(0.0, 0.75, formula, fontsize=14, ha='left', va='top')
ax.text(0.0, 0.5, key, fontsize=10, ha='left', va='top')

# Remove axes and set tight layout
ax.set_axis_off()
plt.subplots_adjust(left=0, right=1, top=1, bottom=0)

# Save with tight bounding box
plt.savefig(f"{os.path.join(file_paths.images_directory, 'activity_formula.png')}", dpi=300, bbox_inches='tight', transparent=True, pad_inches=0.05)
plt.close()

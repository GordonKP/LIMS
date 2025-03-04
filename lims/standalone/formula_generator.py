import os
from io import BytesIO
import matplotlib.pyplot as plt

def generate_activity_formula():
    # Define the formula in LaTeX
    formula = r"$A_f = A_0 \cdot e^{\frac{-\ln 2 \cdot t}{T_{1/2}}} = A_0 \cdot \left(\frac{1}{2}\right)^{\frac{t}{T_{1/2}}}$"

    # Define the key for variables
    key = (
        r"$A_f$ = Final activity" + "\n"
        r"$A_0$ = Initial activity" + "\n"
        r"$t$ = Decay time between initial and final dates" + "\n"
        r"$T_{1/2}$ = Half-life of the radionuclide"
    )

    # Create figure and remove margins
    fig, ax = plt.subplots(figsize=(4, 2))
    ax.text(0.0, 0.75, formula, fontsize=14, ha='left', va='top')
    ax.text(0.0, 0.5, key, fontsize=10, ha='left', va='top')

    # Remove axes and set tight layout
    ax.set_axis_off()
    plt.subplots_adjust(left=0, right=1, top=1, bottom=0)

    # Save image to a BytesIO object
    img_buffer = BytesIO()
    plt.savefig(img_buffer, format='png', dpi=300, bbox_inches='tight', transparent=True, pad_inches=0.05)
    plt.close()

    img_buffer.seek(0)  # Move to the beginning of the buffer
    return img_buffer
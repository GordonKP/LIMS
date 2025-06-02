import pandas as pd
def normalize_detection_limits(df):
    # Define the fields to normalize
    norm_fields = ['MDL', 'DL', 'LOD', 'LOQ']

    # Convert to numeric in case there are strings or NaNs
    for col in norm_fields:
        df[col] = pd.to_numeric(df[col], errors='coerce')

    # Group by Method, Matrix, Analyte
    grouped = df.groupby(['Method', 'Matrix', 'Analyte'])

    # Apply the normalization
    for (method, matrix, analyte), group in grouped:
        for field in norm_fields:
            # Choose first non-null value (you could also use .median() or .mode()[0])
            value = group[field].dropna().unique()
            if len(value) == 1:
                fill_value = value[0]
            elif len(value) > 1:
                # Warn about inconsistency (optional)
                print(f"Inconsistent values for {field} in {method}, {matrix}, {analyte}: using first = {value[0]}")
                fill_value = value[0]
            else:
                fill_value = None  # All NaN

            # Set the fill value across the group
            df.loc[group.index, field] = fill_value

    return df

df = pd.read_csv(r"\\sldafileserver\Staff\Kaleb\Brad SLDA Limits.csv")  # or your CSV
df = normalize_detection_limits(df)
df.to_csv("limits.csv", index=False)
'''
For flagging the DL, LOQ, Lc, and tracer, MS, and LCS recovery needs to be in the dataframe, along with the result.
'''
import sys
import os

# Get the absolute path to the root "LIMS" directory
current_file = os.path.abspath(__file__)
lims_root = os.path.abspath(os.path.join(current_file, "../../.."))

# Insert it at the start of sys.path
sys.path.insert(0, lims_root)
import pandas as pd
import lims.config.lab_lists as lab_lists

def implement_flags(df):
    result_type_order = ['BLK', 'REG', 'DUP', 'LCS', 'LCSDUP', 'MS', 'MSDUP']
    df['ResultType'] = pd.Categorical(df['ResultType'], categories=result_type_order, ordered=True)
    
    # Sort by Method and then ResultType according to the custom order
    df = df.sort_values(by=['Method', 'ResultType'])

    for index, row in df.iterrows():
        if row['Method'] in lab_lists.rad_methods:
            error = float(row['ResultError'])

            if error not in (None, 0):
                dl = round(1.645 * (error/2), 3)
                df.at[index, 'DL'] = dl

    # Add flagging columns if they don't already exist
    for col, default in [('DER', 0), ('RPD', 0), ('Flags', '')]:
        if col not in df.columns:
            df.insert(0, col, default)

    import numpy as np
    limit_columns = ['UpperLimit', 'LowerLimit', 'MDA', 'MDL', 'DL', 'LOD', 'LOQ']
    for column in limit_columns:
        df[column] = df[column].replace([np.nan, None, ''], 0)

    for index, row in df.iterrows():
        if row['ResultType'] == 'BLK':
            df = reg_flagging(df, row)
            df = blk_flagging(df, row)
        elif row['ResultType'] == 'REG':
            df = reg_flagging(df, row)
        elif row['ResultType'] == 'DUP':
            df = reg_flagging(df, row)
            df = dup_flagging(df, row)
        elif row['ResultType'] == 'LCS':
            df = reg_flagging(df, row)
            df = lcs_flagging(df, row)
        elif row['ResultType'] == 'LCSDUP':
            df = reg_flagging(df, row)
            df = lcsdup_flagging(df, row)
        elif row['ResultType'] == 'MS':
            df = reg_flagging(df, row)
            df = ms_flagging(df, row)
        elif row['ResultType'] == 'MSDUP':
            df = reg_flagging(df, row)
            df = msdup_flagging(df, row)

    df['Flags'] = df['Flags'].apply(lambda x: ''.join(sorted(x)) if isinstance(x, str) else x)
    
    return df

def add_flag(df, row_index, new_flag):
    existing = str(df.at[row_index, 'Flags']) if pd.notnull(df.at[row_index, 'Flags']) else ''
    if new_flag not in existing:
        df.at[row_index, 'Flags'] = existing + new_flag

def blk_flagging(df, blk_row):
    batch_id = blk_row['BatchID']
    blk_analyte = blk_row['Analyte']
    blk_sample_id = blk_row['SampleID']

    # Determine chemistry type
    chemistry = 'Stable' if blk_row['Method'] in lab_lists.stable_methods else 'RAD'

    flag = ''

    if chemistry == 'Stable':
        if float(blk_row['Result']) < (float(blk_row['LOQ']/2)):
            flag = ''
        else:
            for _, reg_row in df[
                (df['BatchID'] == batch_id) &
                (df['Analyte'] == blk_analyte) &
                (df['ResultType'] == 'REG')
            ].iterrows():
                if blk_row['Result'] < (0.1 * float(reg_row['Result'])):
                    continue
                else:
                    flag = 'B'
                    break
    else:
        if blk_row['Result'] < float(blk_row['LowerLimit']) or blk_row['Result'] > float(blk_row['UpperLimit']):
            flag = 'B'
            print(f"Row {blk_row['BatchID']} is flagging. lower: {blk_row['LowerLimit']}, upper: {blk_row['UpperLimit']}")
        else:
            flag = ''

    if flag:
        # Flag the BLK sample
        blk_indices = df[(df['SampleID'] == blk_sample_id) &
            (df['Analyte'] == blk_analyte)].index
        for idx in blk_indices:
            add_flag(df, idx, flag)

        # Flag related REG/DUP samples
        reg_dup_indices = df[
            (df['BatchID'] == batch_id) &
            (df['Analyte'] == blk_analyte) &
            (df['ResultType'].isin(['REG', 'DUP']))
        ].index
        for idx in reg_dup_indices:
            add_flag(df, idx, flag)

    return df

def reg_flagging(df, reg_row):
    if reg_row['Method'] == 'PH':
        return df
    
    # Determine chemistry type
    chemistry = 'Stable' if reg_row['Method'] in lab_lists.stable_methods else 'RAD'

    flag = ''

    for category, methods in lab_lists.chemistry_categories.items():
        if reg_row['Method'] in methods:
            chemistry_category = category
            break

    if chemistry == 'Stable':
        if chemistry_category == 'Wet Chemistry':
            reg_row_result = abs(float(reg_row['Result']))
        else:
            reg_row_result = float(reg_row['Result'])
        if reg_row_result > reg_row['LOQ']:
            flag = ''
        elif reg_row_result < reg_row['DL']:
            flag = 'U'
        elif (reg_row_result > reg_row['DL']) & (reg_row_result < reg_row['LOQ']):
            flag = 'J'
    else:
        if reg_row['Result'] < reg_row['DL']:
            flag = 'U'

    # Apply to REG sample
    if flag:
        add_flag(df, reg_row.name, flag)

    return df

def dup_flagging(df, dup_row):
    import numpy as np

    # Determine chemistry type
    chemistry = 'Stable' if dup_row['Method'] in lab_lists.stable_methods else 'RAD'
    flag = ''

    dup_id = dup_row['SampleID']
    parent_id = dup_id.replace("DUP", "")
    batch_id = dup_row['BatchID']
    analyte = dup_row['Analyte']

    # Get parent row
    parent_row = df[(df['BatchID'] == batch_id) & (df['SampleID'] == parent_id) & (df['Analyte'] == analyte)]

    if parent_row.empty:
        return df  # No matching parent found

    parent_row = parent_row.iloc[0]  # Convert to Series

    dup_result = dup_row['Result']
    parent_result = parent_row['Result']

    if chemistry == 'Stable':
        # RPD calculation
        if (dup_result + parent_result) != 0:  # Avoid division by zero
            if dup_result == 0 or parent_result == 0:
                rpd = 200
            else:
                rpd = abs(dup_result - parent_result) / abs((dup_result + parent_result) / 2)
                rpd = round(rpd * 100, 2)

            if dup_result >= dup_row['LOQ'] and parent_result >= parent_row['LOQ']:
                # Add rpd to DUP row RPD column
                df.loc[(df['BatchID'] == batch_id) & (df['SampleID'] == dup_id) & (df['Analyte'] == analyte), 'RPD'] = round(rpd, 2)
                
                if rpd > 20:
                    flag = '*'
            
            df.loc[(df['BatchID'] == batch_id) & (df['SampleID'] == dup_id) & (df['Analyte'] == analyte), 'ParentResult'] = round(parent_result, 3)

    else:
        # DER calculation
        dup_error = dup_row.get('ResultError', 0)
        parent_error = parent_row.get('ResultError', 0)

        if (dup_error**2 + parent_error**2) != 0:
            der = abs(parent_result - dup_result) / np.sqrt(parent_error**2 + dup_error**2)
            if der > 3:
                flag = '*'
            # Add der to DUP row DER column
            df.loc[(df['BatchID'] == batch_id) & (df['SampleID'] == dup_id) & (df['Analyte'] == analyte), 'DER'] = round(der, 2)
            df.loc[(df['BatchID'] == batch_id) & (df['SampleID'] == dup_id) & (df['Analyte'] == analyte), 'ParentResult'] = round(parent_result, 3)

    if flag:
        # Flag the DUP sample
        dup_indices = df[(df['BatchID'] == batch_id) &
            (df['Analyte'] == analyte) &
            (df['SampleID'] == dup_id)].index
        for idx in dup_indices:
            add_flag(df, idx, flag)

        # Flag the associated REG sample(s)
        reg_indices = df[
            (df['BatchID'] == batch_id) &
            (df['Analyte'] == analyte) &
            (df['ResultType'] == 'REG')
        ].index
        for idx in reg_indices:
            add_flag(df, idx, flag)

    return df

def lcs_flagging(df, lcs_row):
    flag = ''

    if lcs_row['Method'] == 'GAMMA':
        print("GAMMA ROW")
        print(lcs_row)

    if float(lcs_row['LowerLimit']) < float(lcs_row['PercentRecovery']) < float(lcs_row['UpperLimit']):
        flag = ''
    else:
        flag = 'Q'

    if flag:
        batch_id = lcs_row['BatchID']
        analyte = lcs_row['Analyte']

        # Flag the associated sample(s)
        indices = df[
            (df['BatchID'] == batch_id) &
            (df['Analyte'] == analyte)
        ].index
        for idx in indices:
            add_flag(df, idx, flag)

    return df

def lcsdup_flagging(df, lcsdup_row):
    # Need to test the DUP as the parent is tested.
    df = lcs_flagging(df, lcsdup_row)

    # Determine chemistry type
    chemistry = 'Stable' if lcsdup_row['Method'] in lab_lists.stable_methods else 'RAD'
    flag = ''

    dup_id = lcsdup_row['SampleID']
    parent_id = dup_id.replace("DUP", "")
    batch_id = lcsdup_row['BatchID']
    analyte = lcsdup_row['Analyte']

    # Get parent row
    parent_row = df[(df['BatchID'] == batch_id) & (df['SampleID'] == parent_id) & (df['Analyte'] == analyte)]

    if parent_row.empty:
        return df

    parent_result = parent_row['Result'].iloc[0]
    dup_result = lcsdup_row['Result']

    if chemistry == 'Stable':
        if (dup_result + parent_result) != 0:  # Avoid division by zero
            if dup_result == 0 or parent_result == 0:
                rpd = 200
            else:
                rpd = abs(dup_result - parent_result) / abs((dup_result + parent_result) / 2)
                rpd = round(rpd * 100, 2)

            df.loc[(df['BatchID'] == batch_id) &
                (df['SampleID'] == dup_id) &
                (df['Analyte'] == analyte), 'RPD'] = round(rpd, 2)
            
            df.loc[(df['BatchID'] == batch_id) &
                    (df['SampleID'] == dup_id) &
                    (df['Analyte'] == analyte), 'Result'] = round(dup_result, 2)
            
            df.loc[(df['BatchID'] == batch_id) &
                    (df['SampleID'] == dup_id) &
                    (df['Analyte'] == analyte), 'ParentResult'] = round(parent_result, 3)
            
            if rpd > 20:
                flag = '*'
    else:
        flag = ''

    if flag:
        # Flag the DUP sample
        lcsdup_indices = df[(df['BatchID'] == batch_id) &
                            (df['Analyte'] == analyte) &
                            (df['SampleID'] == dup_id)].index
        for idx in lcsdup_indices:
            add_flag(df, idx, flag)

        # Flag the associated REG sample(s)
        lcs_indices = df[(df['BatchID'] == batch_id) &
                         (df['Analyte'] == analyte) &
                         (df['SampleID'] == parent_id)].index
        for idx in lcs_indices:
            add_flag(df, idx, flag)

    return df

def ms_flagging(df, ms_row):
    # Determine chemistry type
    chemistry = 'Stable' if ms_row['Method'] in lab_lists.stable_methods else 'RAD'
    flag = ''

    ms_id = ms_row['SampleID']
    parent_id = ms_id.replace("MS", "")

    if chemistry == 'Stable':
        if ms_row['LowerLimit'] < ms_row['PercentRecovery'] < ms_row['UpperLimit']:
            flag = ''
        else:
            flag = 'J'
    else:
        if 60 < ms_row['PercentRecovery'] < 140:
            flag = 'J'

    if flag:
        batch_id = ms_row['BatchID']
        analyte = ms_row['Analyte']

        # Flag the DUP sample
        ms_indices = df[(df['BatchID'] == batch_id) &
            (df['Analyte'] == analyte) &
            (df['SampleID'] == ms_id)].index
        for idx in ms_indices:
            add_flag(df, idx, flag)

        # Flag the associated sample
        parent_indices = df[
            (df['BatchID'] == batch_id) &
            (df['Analyte'] == analyte) &
            (df['SampleID'] == parent_id)
        ].index
        for idx in parent_indices:
            add_flag(df, idx, flag)

    return df

def msdup_flagging(df, msdup_row):
    # Determine chemistry type
    chemistry = 'Stable' if msdup_row['Method'] in lab_lists.stable_methods else 'RAD'
    flag = ''

    dup_id = msdup_row['SampleID']
    parent_id = dup_id.replace("DUP", "")
    batch_id = msdup_row['BatchID']
    analyte = msdup_row['Analyte']

    # Get parent row
    parent_row = df[(df['BatchID'] == batch_id) & (df['SampleID'] == parent_id) & (df['Analyte'] == analyte)]

    if parent_row.empty:
        return df

    parent_row = parent_row.iloc[0]  # Convert to Series

    dup_result = msdup_row['Result']
    parent_result = parent_row['Result']

    if chemistry == 'Stable':
        if (dup_result + parent_result) != 0:  # Prevent division by zero
            if dup_result == 0 or parent_result == 0:
                rpd = 200
            else:
                rpd = abs(dup_result - parent_result) / abs((dup_result + parent_result) / 2)
                rpd = round(rpd * 100, 2)

            df.loc[(df['BatchID'] == batch_id) &
                (df['SampleID'] == dup_id) &
                (df['Analyte'] == analyte), 'RPD'] = round(rpd, 2)
            if rpd > 20:
                flag = '*'
            
            df.loc[(df['BatchID'] == batch_id) &
                   (df['SampleID'] == dup_id) &
                   (df['Analyte'] == analyte), 'Result'] = round(dup_result, 2)
            
            df.loc[(df['BatchID'] == batch_id) &
                   (df['SampleID'] == dup_id) &
                   (df['Analyte'] == analyte), 'ParentResult'] = round(parent_result, 3)

            # If the flag does not exist in the MSDUP but does in MS, flag the MSDUP.
            parent_flag = parent_row.get('Flag', '')
            if pd.notna(parent_flag) and 'J' in parent_flag:
                flag += 'J'
                
            if rpd > 20:
                flag += '*'
    else:
        import numpy as np
        parent_error = parent_row.get('ResultError', 0)
        dup_error = msdup_row.get('ResultError', 0)

        if (parent_error**2 + dup_error**2) != 0:
            der = abs(parent_result - dup_result) / np.sqrt(parent_error**2 + dup_error**2)

            # Store DER in the DUP row
            df.loc[(df['BatchID'] == batch_id) &
                   (df['SampleID'] == dup_id) &
                   (df['Analyte'] == analyte), 'DER'] = round(der, 2)
            
            df.loc[(df['BatchID'] == batch_id) &
                   (df['SampleID'] == dup_id) &
                   (df['Analyte'] == analyte), 'ParentResult'] = round(parent_result, 3)

            if der > 3:
                flag += '*'

    if flag:
        # Flag the MSDUP sample
        msdup_indices = df[(df['BatchID'] == batch_id) &
                           (df['Analyte'] == analyte) &
                           (df['SampleID'] == dup_id)].index
        for idx in msdup_indices:
            add_flag(df, idx, flag)

        # Flag the associated REG sample(s)
        ms_indices = df[(df['BatchID'] == batch_id) &
                        (df['Analyte'] == analyte) &
                        (df['SampleID'] == parent_id)].index
        for idx in ms_indices:
            add_flag(df, idx, flag)

        reg_parent_id = parent_id.replace("MS", '')
        # Flag the associated REG sample(s)
        ms_indices = df[(df['BatchID'] == batch_id) &
                        (df['Analyte'] == analyte) &
                        (df['SampleID'] == reg_parent_id)].index
        for idx in ms_indices:
            add_flag(df, idx, flag)

    return df
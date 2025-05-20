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
            if pd.notna(row['DL']):  # Skip if DL is already a number
                continue

            mda = float(row['MDA'])
            error = float(row['ResultError'])

            if mda not in (None, 0) and error not in (None, 0):
                dl = round(1.645 * (error/2), 3)
                df.at[index, 'DL'] = dl

    # Add flagging columns if they don't already exist
    for col, default in [('DER', 0), ('RPD', 0), ('Flags', '')]:
        if col not in df.columns:
            df.insert(0, col, default)

    for index, row in df.iterrows():
        if row['ResultType'] == 'BLK':
            df = blk_flagging(df, row)
        elif row['ResultType'] == 'REG':
            df = reg_flagging(df, row)
        elif row['ResultType'] == 'DUP':
            df = dup_flagging(df, row)
        elif row['ResultType'] == 'LCS':
            df = lcs_flagging(df, row)
        elif row['ResultType'] == 'LCSDUP':
            df = lcsdup_flagging(df, row)
        elif row['ResultType'] == 'MS':
            df = ms_flagging(df, row)
        elif row['ResultType'] == 'MSDUP':
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
        if blk_row['Result'] < (blk_row['LOQ'] / 2):
            flag = ''
        else:
            flag = 'B'

        if flag == '':
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
        if blk_row['Result'] < blk_row['LowerLimit'] or blk_row['Result'] > blk_row['UpperLimit']:
            flag = 'B'

    if flag:
        # Flag the BLK sample
        blk_indices = df[df['SampleID'] == blk_sample_id].index
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
    # Determine chemistry type
    chemistry = 'Stable' if reg_row['Method'] in lab_lists.stable_methods else 'RAD'

    flag = ''

    if chemistry == 'Stable':
        if (reg_row['Result'] > reg_row['DL']) & (reg_row['Result'] < reg_row['LOQ']):
            pass
        elif reg_row['Result'] < reg_row['DL']:
            flag = 'U'
        elif reg_row['Result'] > reg_row['LOQ']:
            flag = 'J'
    else:
        if reg_row['Result'] < reg_row['DL']:
            flag = 'U'

    if flag:
        add_flag(df, reg_row.name, flag)

    return df

def dup_flagging(df, dup_row):
    # Need to test the DUP as the parent is tested.
    df = reg_flagging(df, dup_row)

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
                rpd = abs(dup_result - parent_result) / abs((dup_result + parent_result) / 2) * 100

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

    if lcs_row['LowerLimit'] < lcs_row['PercentRecovery'] < lcs_row['UpperLimit']:
        flag = ''
    else:
        flag = 'Q'

    if flag:
        batch_id = lcs_row['BatchID']
        analyte = lcs_row['Analyte']

        # Flag the associated REG sample(s)
        reg_indices = df[
            (df['BatchID'] == batch_id) &
            (df['Analyte'] == analyte)
        ].index
        for idx in reg_indices:
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

    parent_result = parent_row['PercentRecovery'].iloc[0]
    dup_result = lcsdup_row['PercentRecovery']

    if chemistry == 'Stable':
        if (dup_result + parent_result) != 0:  # Avoid division by zero
            if dup_result == 0 or parent_result == 0:
                rpd = 200
            else:
                rpd = abs(dup_result - parent_result) / abs((dup_result + parent_result) / 2) * 100

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

    dup_result = msdup_row['PercentRecovery']
    parent_result = parent_row['PercentRecovery']

    if chemistry == 'Stable':
        if (dup_result + parent_result) != 0:  # Prevent division by zero
            if dup_result == 0 or parent_result == 0:
                rpd = 200
            else:
                rpd = abs(dup_result - parent_result) / abs((dup_result + parent_result) / 2) * 100

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

            if str(parent_row.get('Flag', '')).find('J') != -1:
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

    return df
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

df = pd.read_csv("25SL0015-PDR.csv")

def implement_flags(df):
    df.insert(0, 'Flags', '')

    for index, row in df.iterrows():
        if row['ResultType'] == 'BLK':
            df = blk_flagging(df, row)
        elif row['ResultType'] == 'REG':
            df = reg_flagging(df, row)
        elif row['ResultType'] == 'DUP':
            print("DUP")
        elif row['ResultType'] == 'LCS':
            print("LCS")
        elif row['ResultType'] == 'LCSDUP':
            print("LCSDUP")
        elif row['ResultType'] == 'MS':
            print("MS")
        elif row['ResultType'] == 'MSDUP':
            print("MSDUP")
    
    df.to_csv("Flagging_test.csv", index=False)
    return df

def add_flag(df, row_index, new_flag):
    existing = str(df.at[row_index, 'Flags']) if pd.notnull(df.at[row_index, 'Flags']) else ''
    if new_flag not in existing:
        df.at[row_index, 'Flags'] = existing + new_flag

def blk_flagging(df, blk_row):
    batch_id = blk_row['BatchID']
    blk_analyte = blk_row['Analyte']
    blk_sample_id = blk_row['SampleID']

    if blk_row['Method'] in lab_lists.stable_methods:
        chemistry = 'Stable'
    else:
        chemistry = 'RAD'

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
                if blk_row['Result'] < (0.1 * reg_row['Result']):
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
    if reg_row['Method'] in lab_lists.stable_methods:
        chemistry = 'Stable'
    else:
        chemistry = 'RAD'

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

df = implement_flags(df)
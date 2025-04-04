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
            print("REG")
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

def blk_flagging(df, blk_row):
    batch_id = blk_row['BatchID']
    blk_analyte = blk_row['Analyte']
    blk_sample_id = blk_row['SampleID']

    # Determine whether the method is stable or RAD chemistry
    if blk_row['Method'] in lab_lists.stable_methods:
        chemistry = 'Stable'
    else:
        chemistry = 'RAD'

    flag = ''

    if chemistry == 'Stable':
        # Condition: BLK result is less than 1/2 of LOQ
        if blk_row['Result'] < (blk_row['LOQ']/2):
            flag = ''
        else:
            flag = 'B'
        
        # If there's no flag, check REG results
        if flag == '':  
            for index, reg_row in df[(df['BatchID'] == batch_id) &  
                                    (df['Analyte'] == blk_analyte) & 
                                    (df['ResultType'] == 'REG')].iterrows():
                # Condition: BLK result is greater than 1/10th of any REG result
                if blk_row['Result'] < (0.1 * reg_row['Result']):
                    continue
                else:
                    flag = 'B'
                    break
    else:
        # Condition: BLK result is outside of the LowerLimit and UpperLimit
        if (blk_row['Result'] < blk_row['LowerLimit']):
            flag = 'B'
        elif (blk_row['Result'] > blk_row['UpperLimit']):
            flag = 'B'
        else:
            flag = ''

    # If a flag has been assigned, apply it to affected rows
    if flag != '':
        # Flag the BLK sample
        df.loc[df['SampleID'] == blk_sample_id, 'Flags'] = flag
        
        # Flag the REG samples with the same BatchID and Analyte
        df.loc[(df['BatchID'] == batch_id) & 
            (df['Analyte'] == blk_analyte) & 
            ((df['ResultType'] == 'REG') | (df['ResultType'] == 'DUP')), 'Flags'] = flag
        
    return df

df = implement_flags(df)
from Packages.lab_lists import all_qc

class GetResultType:
    @staticmethod

    def get_result_types(df):
        # Sort by length (longest first) to prevent partial matches
        sorted_qc = sorted(all_qc, key=len, reverse=True)

        df['ResultType'] = df['SampleID'].apply(
            lambda sample_id: next((qc for qc in sorted_qc if qc in sample_id), "REG")
        )
        return df

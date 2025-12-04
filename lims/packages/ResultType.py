from lims.config.lab_lists import cal_qc, lab_qc

class GetResultType:
    @staticmethod
    def get_result_types(df):
        # Sort longest first to prevent partial substring collisions
        lab_qc_sorted = sorted(lab_qc, key=len, reverse=True)
        cal_qc_sorted = sorted(cal_qc, key=len, reverse=True)

        df["ResultType"] = df["SampleID"].apply(
            lambda sid:
                next((qc for qc in lab_qc_sorted if str(sid).endswith(qc)), None)
                or next((qc for qc in cal_qc_sorted if qc in str(sid)), None)
                or "REG"
        )

        return df
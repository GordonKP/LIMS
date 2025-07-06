from lims.config.tables import ALPHAResults, GAMMAResults, GFPCResults, METResults, BEFResults, LSCResults, WetChemResults, HGResults

methods_tables = {
    "BEF": BEFResults,
    "CL": WetChemResults,
    "CRVI": WetChemResults,
    "FLUOR": WetChemResults,
    "GAMMA": GAMMAResults,
    "GFPC": GFPCResults,
    "HG": HGResults,
    "ISOAM": ALPHAResults,
    "ISOPU": ALPHAResults,
    "ISOTH": ALPHAResults,
    "ISOU": ALPHAResults,
    "LSCAB": LSCResults,
    "LSCPU": LSCResults,
    "LSCSR": LSCResults,
    "MET": METResults,
    "NH3": WetChemResults,
    "NO2": WetChemResults,
    "NO3": WetChemResults,
    "PH": WetChemResults,
    "TCLP": METResults,
    "TSP": WetChemResults,
    "TSS": WetChemResults
}


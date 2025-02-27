from sqlalchemy import create_engine, Column, String, Boolean, Float, Integer, DateTime, Date, Time, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

methods_codes_dict = {
    "FIMS": {"ANMCode": "CL245.1", "EXCode": "SL999"},
    "ISOAm": {"ANMCode": "A01R", "EXCode": "SL005"},
    "ISOTh": {"ANMCode": "A01R", "EXCode": "SL005"},
    "ISOU": {"ANMCode": "A01R", "EXCode": "SL015"},
    "ISOPu": {"ANMCode": "A01R", "EXCode": "SL005"},
    "GammaSpec": {"ANMCode": "GA01R", "EXCode": "SL003"},
    "GAB": {"ANMCode": "E901", "EXCode": "SL018"},
    "LSCPu": {"ANMCode": "A01R", "EXCode": "SL044"},
    "LSCRa": {"ANMCode": "E904.0", "EXCode": "SL047"},
    "LSCTotal": {"ANMCode": "SR486.0", "EXCode": "SL044"},
    "ICPMS (Soil)": {"ANMCode": "6020B", "EXCode": "SL035"},
    "ICPMS (Aqueous)": {"ANMCode": "6020B", "EXCode": "SL036"},
    "ICPMS (Smear)": {"ANMCode": "6020B", "EXCode": "SL037"},
    "ICPMS (Air Filter)": {"ANMCode": "6020B", "EXCode": "SL037"},
    "Fluorescence": {"ANMCode": "E9110", "EXCode": "SL042"},
    "XRD": {"ANMCode": "N7500", "EXCode": "SL999"},
    "TSP": {"ANMCode": "N0600", "EXCode": "SL053"},
    "Fluoride": {"ANMCode": "SM4500-F-C", "EXCode": "SL040"},
    "Ammonia": {"ANMCode": "E350.1", "EXCode": "SL039"},
    "Nitrates": {"ANMCode": "C352.1", "EXCode": "SL022"},
    "Nitrites": {"ANMCode": "C352.1", "EXCode": "SL022"},
    "Cyanide": {"ANMCode": "C335.2", "EXCode": "SL051"},
    "Chloride": {"ANMCode": "C925.1", "EXCode": "SL050"},
    "pH": {"ANMCode": "SM4500-H", "EXCode": "SL024"},
    "TSS": {"ANMCode": "A2540D", "EXCode": "SL023"}
}


Base = declarative_base()  

class User(Base):
    __tablename__ = 'Users'
    EmployeeID = Column('EmployeeID', Integer, primary_key=True, autoincrement=False)
    FirstName = Column('FirstName', String)
    LastName = Column('LastName', String)
    UserName = Column('UserName', String, unique=True)
    PasswordHash = Column('PasswordHash', String)
    LastLogin = Column('LastLogin', DateTime)

class CoC(Base):
    __tablename__ = 'CoC'

    SDG = Column('SDG', String(250), primary_key=True)
    CoCID = Column('CoCID', String(50), unique=True)
    Survey = Column(String(50))
    CompanyName = Column('CompanyName', String(50))
    Address = Column('Address', String(100))
    Phone = Column('Phone', String(20))
    EmailOne = Column('EmailOne', String(50))
    EmailTwo = Column('EmailTwo', String(50))
    ClientContact = Column('ClientContact', String(50))
    PurchaseOrder = Column('PurchaseOrder', String(50))
    JobNumber = Column('JobNumber', Integer)
    SentTo = Column('SentTo', String(10))
    SiteContact = Column('SiteContact', String(50))
    SiteAddress = Column('SiteAddress', String(100))
    SitePhone = Column('SitePhone', String(20))
    SiteEmail = Column('SiteEmail', String(50))
    AdditionalNotes = Column('AdditionalNotes', String(250))
    TurnaroundTime = Column('TurnaroundTime', String(4))
    FilePath = Column('FilePath', String(100))

class SampleLogin(Base):
    __tablename__ = 'SampleLogin'

    SDG = Column(String(250), primary_key=True)
    SampleID = Column(String(50), primary_key=True)
    Matrix = Column(String(50))
    FIMS = Column(Boolean)
    ISOAm = Column(Boolean) 
    ISOTh = Column(Boolean)
    ISOU = Column(Boolean)
    ISOPu = Column(Boolean)
    GammaSpec = Column(Boolean)
    GAB = Column(Boolean)
    LSCPu = Column(Boolean)
    LSCRa = Column(Boolean)
    LSCTotal = Column(Boolean)
    ICPMS = Column(Boolean)
    Fluorescence = Column(Boolean)
    XRD = Column(Boolean)
    TSP = Column(Boolean)
    Fluoride = Column(Boolean)
    Ammonia = Column(Boolean)
    Nitrates = Column(Boolean)
    Nitrites = Column(Boolean)
    Cyanide = Column(Boolean)
    Chloride = Column(Boolean)
    pH = Column(Boolean)
    TSS = Column(Boolean)
    LocationID = Column(String(50))
    SampleVolume = Column(Integer)
    Count = Column(Integer)
    CPM = Column(Integer)
    SampleDate = Column(Date)
    SampleTime = Column(Time)
    DateReceived = Column(Date)
    TimeReceived = Column(Time)
    ReceivedBy = Column(String(20))
    DQO = Column(Boolean)

class LIMSLimits(Base):
    __tablename__ = 'LIMSLimits'

    Method = Column(String(50), primary_key=True)
    Matrix = Column(String(50), primary_key=True)
    ResultType = Column(String(12), primary_key=True) 
    Analyte = Column(String(50), primary_key=True)
    LowerLimit = Column(Float)
    UpperLimit = Column(Float)
    MDL = Column(Float)
    LOD = Column(Float)
    LOQ = Column(Float)
    Units = Column(String(20))
    EffectiveDate = Column(Date, primary_key=True)

class DQO(Base):
    __tablename__ = "DQO"
    # These dtypes need changed, reference the data processing logic
    SDG = Column('SDG', String(250), primary_key=True)
    SampleID = Column('SampleID', String(50), primary_key=True)
    Method = Column('Method', String(250), primary_key=True)
    BatchID = Column('BatchID', String(50))
    Matrix = Column('Matrix', String(50))
    
class ICPMSResults(Base):
    __tablename__ = 'ICPMSResults'

    SDG = Column(String(50), primary_key=True)                             # Sample Data Group
    BatchID = Column(String(50), primary_key=True)                         # Leidos Batch ID
    Method = Column(String(20))                                            # Analytical Method
    SampleID = Column(String(50), primary_key=True)                        # Sample identifier
    Matrix = Column(String(50))                                            # Sample matrix (e.g., soil)
    ResultType = Column(String(12))                                     # Result Type (REG, BLK, LCS, etc.)
    AnalysisDateTime = Column(DateTime, primary_key=True)                  # Date and Time Acquired
    DilutionFactor = Column(Float)                                         # Dilution Factor
    Notes = Column(Text)                                                   # Misc. Info or Comment
    FileName = Column(String(100))                                         # Data File Name
    CalibrationBatchID = Column(String(100), primary_key=True)             # Batch Name
    FilePath = Column(String(255))                                         # Data Path
    Analyst = Column(String(100))                                          # Operator
    InstrumentName = Column(String(50))                                    # Instrument Name
    SampleWeightVolume = Column(Float)                                     # Sample Weight or Volume
    FinalWeightVolume = Column(Float)                                      # Final Weight or Volume
    DilutionMultiplier = Column(Float)                                     # Dilution Multiplier
    ElementSymbol = Column(String(2))                                      # Analyte
    Analyte = Column(String(50), primary_key=True)                        # Element Full Name
    Mass = Column(Float)                                                   # Mass
    ISTDRefMass = Column(Float, primary_key=True)                          # ISTD Ref Mass
    Result = Column(Float)                                          # Result
    ResultRSD = Column(Float)                                       # Conc RSD
    CPSMean = Column(Float)                                                # CPS Mean
    CPSRep1 = Column(String(50))                                           # CPS Rep1
    CPSRep2 = Column(String(50))                                           # CPS Rep2
    CPSRep3 = Column(String(50))                                           # CPS Rep3
    CPSRep4 = Column(String(50))                                           # CPS Rep4
    CPSRep5 = Column(String(50))                                           # CPS Rep5
    CPSRSD = Column(Float)                                                 # CPS RSD
    ResultUnits = Column(String(50))                                             # Units                             
    Iteration = Column(Integer, primary_key=True)                          # Iteration number
    Reporting = Column(Boolean, primary_key=True)                          # Reporting status (True/False)

class FluorescenceResults(Base):
    __tablename__ = 'FluorescenceResults'

    SDG = Column(String(50), primary_key=True)                          # Sample Data Group
    BatchID = Column(String(50), primary_key=True)                      # Leidos Batch ID
    Method = Column(String(20))                                         # Analytical Method
    SampleID = Column(String(50), primary_key=True)                     # Sample identifier
    Matrix = Column(String(50))                                         # Sample matrix (e.g., soil)    
    ResultType = Column(String(12))                                     # Result Type (REG, BLK, LCS, etc.)
    Analyte = Column(String(50))
    FilePath = Column(String(255))                                      # File name of the corresponding data file
    Result = Column(Float)                                              # Counts value
    ResultUnits = Column(String(10))                                          # Counts Units
    PPB = Column(Float)                                                 # Parts per billion
    MicroGrams = Column(Float)                                          # Micrograms per 100cm^2 
    AnalysisDateTime = Column(DateTime)
    Iteration = Column(Integer, primary_key=True)                       # Iteration number
    Reporting = Column(Boolean, primary_key=True)                       # Reporting status (True/False)

class GammaSpecResults(Base):
    __tablename__ = 'GammaSpecResults'

    SDG = Column(String(50), primary_key=True)                          # Sample Data Group
    BatchID = Column(String(20), primary_key=True)                      # Leidos Batch ID
    Method = Column(String(50))                                         # Analytical Method
    SampleID = Column(String(50), primary_key=True)                     # Sample identifier
    Matrix = Column(String(50))                                         # Sample matrix (e.g., soil)
    ResultType = Column(String(12))                                     # Result Type (REG, BLK, LCS, etc.)
    Detector = Column(String(50))                                       # Detector ID
    Geometry = Column(String(50))                                       # Geometry type
    AcquisitionStartDateTime = Column(DateTime)                         # Acquisition Start Date and Time
    AnalysisDateTime = Column(DateTime)                           # Acquisition End Date and Time
    Livetime = Column(Integer)                                          # Livetime in seconds
    EnergyDateTime = Column(DateTime)                                   # Energy Calibration Date and Time
    EfficiencyDateTime = Column(DateTime)                               # Efficiency Calibration Date and Time
    SampleDateTime = Column(DateTime)                                   # Sample Date and Time
    SampleSize = Column(Float)                                          # Size of the sample
    SampleSizeUnits = Column(String(20))                                # Units for sample size
    ResultUnits = Column(String(10))                                  # Units for activity measurement
    ErrorMultiplier = Column(Integer)                                   # Error multiplier
    Analyte = Column(String(50), primary_key=True)                  # Name of the nuclide
    NuclideDetected = Column(String(3))                                 # Whether the nuclide was detected ("YES" or "NO")
    Result = Column(Float)                                            # Result value
    ResultError = Column(Float)                                       # Result error
    MDA = Column(Float)                                                 # Minimum detectable activity (MDA)
    MDAError = Column(Float)                                            # MDA error
    ResultMDARatio = Column(Float)                                    # Result to MDA ratio
    Iteration = Column(Integer, primary_key=True)                       # Iteration number
    Reporting = Column(Boolean, primary_key=True)                       # Reporting status (True/False)

class GABResults(Base):
    __tablename__ = 'GABResults'

    SDG = Column(String(50), primary_key=True)                          # Sample Data Group
    BatchID = Column(String(50), primary_key=True)                      # Leidos Batch ID
    Method = Column(String(50))                                         # Analytical Method
    SampleID = Column(String(50), primary_key=True)                     # Sample identifier
    Matrix = Column(String(50))                                         # Sample matrix (e.g., soil)
    ResultType = Column(String(12))                                     # Result Type (REG, BLK, LCS, etc.)
    Analyte = Column(String(50), primary_key=True)
    Procedure = Column(String(100))                                     # Procedure
    AcquisitionDateTime = Column(DateTime)                              # Date Received
    AnalysisDateTime = Column(DateTime)                                 # Analysis Date
    DetectorSN = Column(String(50))                                     # Detector Serial Number
    LiveTime = Column(Float)                                            # Live time in seconds
    Result = Column(Float)                     # Alpha Concentration
    ResultUnits = Column(String(10))
    ResultError = Column(Float)                # Alpha Concentration error
    MDA = Column(Float)                                       # Alpha Minimum Detectable Amount
    Aliquot = Column(Float)                                   # Alpha Aliquot
    EfficiencyFactor = Column(Float)                          # Alpha Efficiency Factor
    AliquotUnits = Column(String(50))                                   # Aliquot Units
    EfficiencyCalibrationDateTime = Column(DateTime)                    # Activity to MDA ratio
    Iteration = Column(Integer, primary_key=True)                       # Iteration number
    Reporting = Column(Boolean, primary_key=True)                       # Reporting status (True/False)

class AlphaSpecResults(Base):
    __tablename__ = 'AlphaSpecResults'

    SDG = Column(String(50), primary_key=True)                          # Sample Data Group
    BatchID = Column(String(50), primary_key=True)                      # Leidos Batch ID
    Method = Column(String(20))                                         # Analytical Method
    SampleID = Column(String(50), primary_key=True)                     # Sample identifier
    Matrix = Column(String(50))                                         # Sample matrix (e.g., soil)    
    ResultType = Column(String(12))                                     # Result Type (REG, BLK, LCS, etc.)
    AlphaBatchID = Column(String(10))                                   # Batch identifier
    Detector = Column(String(50))                                       # Detector name or ID
    AnalysisDateTime = Column(DateTime)                                 # Date and time of the analysis
    SampleAliquot = Column(Float)                                       # Aliquot of the sample
    ResultUnits = Column(String(10))                                  # Units of activity
    MassUnits = Column(String(10))                                      # Units of mass
    TracerAliquotGrams = Column(Float)                                  # Aliquot grams for the tracer
    FileName = Column(String(255))                                      # File name of the corresponding data file
    PercentAbundance = Column(Float)                                    # Percent abundance
    MDAConfidenceFactor = Column(Float)                                 # Confidence factor for MDA
    MDALLDConstant = Column(Integer)                                    # Constant value for MDA LLD
    EnergyCalibrationDateTime = Column(DateTime)                        # Date and time of energy calibration
    EfficiencyCalibrationDateTime = Column(DateTime)                    # Date and time of efficiency calibration
    BackgroundFile = Column(String(255))                                # Path to the background file
    TracerRecovery = Column(Float)                                      # Tracer recovery value
    AlphaChamber = Column(String(50))                                   # Chamber identifier for alpha analysis
    ChamberEfficiency = Column(Float)                                   # Efficiency of the chamber
    AcquisitionDateTime = Column(DateTime)                              # Acquisition date and time
    ElapsedLiveTime = Column(Float)                                     # Elapsed live time
    TracerFWHM = Column(Float)                                          # Tracer full width at half maximum
    Analyte = Column(String(50), primary_key=True)                  # Name of the nuclide
    NetArea = Column(Float)                                             # Net area
    BackgroundArea = Column(Float)                                      # Background area
    Result = Column(Float)                                            # Activity value
    ResultError = Column(Float)                                         # Uncertainty in the activity measurement
    MDA = Column(Float)                                                 # Minimum detectable concentration
    Iteration = Column(Integer, primary_key=True)                       # Iteration number
    Reporting = Column(Boolean, primary_key=True)                       # Reporting status (True/False)


from sqlalchemy import Column, String, Boolean, Float, Integer, DateTime, Date, Time
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()  

class User(Base):
    __tablename__ = 'Users'
    EmployeeID = Column('EmployeeID', Integer, primary_key=True, autoincrement=False)
    FirstName = Column('FirstName', String(50))
    LastName = Column('LastName', String(50))
    UserName = Column('UserName', String(50), unique=True)
    PasswordHash = Column('PasswordHash', String(255))
    LastLogin = Column('LastLogin', DateTime)

class LIMSActivity(Base):
    __tablename__ = 'LIMSActivity'

    Interaction = Column(Integer, primary_key=True, autoincrement=True)
    User = Column(String(50))
    TablesAffected = Column(String(50))
    Action = Column(String(50))
    Notes = Column(String(255))
    Date = Column(Date)
    Time = Column(Time)

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
    Site = Column('Site', String(50))
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
    LSCTotal = Column(Boolean)
    ICPMS = Column(Boolean)
    Fluorescence = Column(Boolean)
    XRD = Column(Boolean)
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

class DQO(Base):
    __tablename__ = "DQO"
    # These dtypes need changed, reference the data processing logic
    SDG = Column('SDG', String(250), primary_key=True)
    SampleID = Column('SampleID', String(50), primary_key=True)
    Method = Column('Method', String(250), primary_key=True)
    BatchID = Column('BatchID', String(50))
    Matrix = Column('Matrix', String(50))

class LIMSLimits(Base):
    __tablename__ = 'LIMSLimits'

    Method = Column(String(50), primary_key=True)
    Matrix = Column(String(50), primary_key=True)
    ResultType = Column(String(12), primary_key=True) 
    Analyte = Column(String(50), primary_key=True)
    LowerLimit = Column(Float)
    UpperLimit = Column(Float)
    DL = Column(Float)
    LOD = Column(Float)
    LOQ = Column(Float)
    Units = Column(String(20))
    EffectiveDate = Column(Date, primary_key=True)

class RADCerts(Base):
    __tablename__ = 'RADCerts'

    PrincipleRadionuclide = Column(String(50))
    HalfLife = Column(Float)
    SolutionPrepDate = Column(Date)
    SRS = Column(String(50), primary_key=True)
    SourceActivity = Column(Float)
    Units = Column(String(12))
    SourceVolume = Column(Float)
    SourceActivityDate = Column(Date, primary_key=True)
    ChemicalComposition = Column(String(50))
    DilutionSolution = Column(String(255))
    InitialContainerWeight = Column(Float)
    FinalContainerWeight = Column(Float)
    SolutionMass = Column(Float)
    FinalActivity = Column(Float)
    PercentAbundance = Column(Float)
    ToActivityDate = Column(Date)
    ExpirationDate = Column(Date)
    VerifiedBy = Column(String(50))
    CalculationDate = Column(Date)
    ConsumableType = Column(String(50))

class Verifications(Base):
    __tablename__ = 'Verifications'

    Instrument = Column(String(50), primary_key=True)
    Verification = Column(String(50), primary_key=True)
    Date = Column(Date, primary_key=True)
    Time = Column(Time, primary_key=True)
    Notes = Column(String(255))
    FilePath = Column(String(255))

class ICPMSResults(Base):
    __tablename__ = 'ICPMSResults'

    SDG = Column(String(50), primary_key=True)                             # Sample Data Group
    BatchID = Column(String(50), primary_key=True)                         # Leidos Batch ID
    Method = Column(String(20))                                            # Analytical Method
    SampleID = Column(String(50), primary_key=True)                        # Sample identifier
    Matrix = Column(String(50))                                            # Sample matrix (e.g., soil)
    ResultType = Column(String(12))                                        # Result Type (REG, BLK, LCS, etc.)
    Analyte = Column(String(50), primary_key=True) 
    Aliquot = Column(Float)
    SampleWeightVolume = Column(Float)
    FinalWeightVolume = Column(Float)                                      # Final Weight or Volume
    DilutionFactor = Column(Float)
    DilutionMultiplier = Column(Float)
    AliquotUnits = Column(String(10))
    Result = Column(Float)                                                 # Activity value
    ResultRSD = Column(Float)
    ResultUnits = Column(String(10))   
    CPSMean = Column(Float)                                                # CPS Mean
    CPSRep1 = Column(String(50))                                           # CPS Rep1
    CPSRep2 = Column(String(50))                                           # CPS Rep2
    CPSRep3 = Column(String(50))                                           # CPS Rep3
    CPSRep4 = Column(String(50))                                           # CPS Rep4
    CPSRep5 = Column(String(50))                                           # CPS Rep5
    CPSRSD = Column(Float)
    ISTDRefMass = Column(Float)
    TuneStep = Column(Integer, primary_key=True)
    Instrument = Column(String(12))
    AnalysisDateTime = Column(DateTime, primary_key=True)
    PrepDateTime = Column(DateTime)
    Notes = Column(String(255))
    ICPMSBatchName = Column(String(50))
    ICPMSFileName = Column(String(50))
    ICPMSPath = Column(String(255))
    PrepsheetFilePath = Column(String(255))
    Analyst = Column(String(24))
    ProcessedDataFilePath = Column(String(255))
    Iteration = Column(Integer, primary_key=True)                          # Iteration number
    Reporting = Column(Boolean, primary_key=True)                          # Reporting status (True/False)

class GammaSpecResults(Base):
    __tablename__ = 'GammaSpecResults'

    SDG = Column(String(50), primary_key=True)                          # Sample Data Group
    BatchID = Column(String(20), primary_key=True)                      # Leidos Batch ID
    Method = Column(String(50))                                         # Analytical Method
    SampleID = Column(String(50), primary_key=True)                     # Sample identifier
    Matrix = Column(String(50))                                         # Sample matrix (e.g., soil)
    ResultType = Column(String(12))                                     # Result Type (REG, BLK, LCS, etc.)
    Analyte = Column(String(50), primary_key=True)                      # Name of the nuclide
    Result = Column(Float)                                              # Result value
    ResultError = Column(Float)                                         # Result error
    ErrorMultiplier = Column(Integer)                                   # Error multiplier
    ResultUnits = Column(String(10))                                    # Units for activity measurement
    MDA = Column(Float)                                                 # Minimum detectable activity (MDA)
    MDAError = Column(Float)                                            # MDA error
    ResultMDARatio = Column(Float)                                      # Result to MDA ratio
    Aliquot = Column(Float)                                             # Alpha Aliquot
    AliquotUnits = Column(String(50))                                   # Aliquot Units
    Livetime = Column(Integer)                                          # Livetime in seconds
    NuclideDetected = Column(String(3))                                 # Whether the nuclide was detected ("YES" or "NO")
    Detector = Column(String(50))                                       # Detector ID
    Geometry = Column(String(50))                                       # Geometry type
    PrepDateTime = Column(DateTime)
    AcquisitionDateTime = Column(DateTime)                              # Acquisition Start Date and Time
    AnalysisDateTime = Column(DateTime)                                 # Acquisition End Date and Time
    EnergyCalibrationDateTime = Column(DateTime)                        # Energy Calibration Date and Time
    EfficiencyCalibrationDateTime = Column(DateTime)                    # Efficiency Calibration Date and Time
    SampleDateTime = Column(DateTime)                                   # Sample Date and Time
    PrepsheetFilePath = Column(String(250))
    ProcessedDataFilePath = Column(String(255))
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
    Analyte = Column(String(50), primary_key=True)                      # Analyte
    Result = Column(Float)                                              # Alpha Concentration
    ResultUnits = Column(String(10))                                    # Units of result
    ResultError = Column(Float)                                         # Alpha Concentration error
    MDA = Column(Float)                                                 # Alpha Minimum Detectable Amount
    Aliquot = Column(Float)                                             # Alpha Aliquot
    AliquotUnits = Column(String(50))                                   # Aliquot Units
    LiveTime = Column(Float)                                            # Live time in seconds
    PresetLiveTime = Column(Float)
    Detector = Column(String(50))                                     # Detector Serial Number
    SRS = Column(String(24))
    PrepDateTime = Column(DateTime)
    AnalysisDateTime = Column(DateTime)                                 # Analysis Date
    PrepsheetFilePath = Column(String(250))
    ProcessedDataFilePath = Column(String(255))
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
    Analyte = Column(String(50), primary_key=True)                      # Name of the nuclide
    Aliquot = Column(Float)                                             # Aliquot of the sample
    TracerAliquot = Column(Float)                                       # Aliquot for the tracer
    AliquotUnits = Column(String(10))                                   # Units of aliquot
    Result = Column(Float)                                              # Activity value
    ResultError = Column(Float)                                         # Uncertainty in the activity measurement
    ResultUnits = Column(String(10))                                    # Units of activity
    TracerRecovery = Column(Float)                                      # Tracer recovery value
    TracerFWHM = Column(Float)                                          # Tracer full width at half maximum
    MDA = Column(Float)                                                 # Minimum detectable concentration
    MDAConfidenceFactor = Column(Float)                                 # Confidence factor for MDA
    MDALLDConstant = Column(Integer)                                    # Constant value for MDA LLD
    PercentAbundance = Column(Float)                                    # Percent abundance
    LiveTime = Column(Float)                                     # Elapsed live time
    BackgroundArea = Column(Float)                                      # Background area
    NetArea = Column(Float)                                             # Net area
    ChamberEfficiency = Column(Float)                                   # Efficiency of the chamber
    AlphaBatchID = Column(String(10))                                   # Batch identifier
    Detector = Column(String(50))                                       # Detector name or ID
    AlphaChamber = Column(String(50))                                   # Chamber identifier for alpha analysis
    EnergyCalibrationDateTime = Column(DateTime)                        # Date and time of energy calibration
    EfficiencyCalibrationDateTime = Column(DateTime)                    # Date and time of efficiency calibration
    SampleDate = Column(DateTime)                                       # Sample date
    PrepDateTime = Column(DateTime)                                     # Preparation date and time
    AcquisitionDateTime = Column(DateTime)                              # Acquisition date and time
    AnalysisDateTime = Column(DateTime)                                 # Date and time of the analysis
    FileName = Column(String(255))                                      # File name of the corresponding data file
    BackgroundFile = Column(String(255))                                # Path to the background file
    PrepsheetFilePath = Column(String(255))                             # Path to the preparation sheet file
    ProcessedDataFilePath = Column(String(255))
    Iteration = Column(Integer, primary_key=True)                       # Iteration number
    Reporting = Column(Boolean, primary_key=True)                       # Reporting status (True/False)

class FluorescenceResults(Base):
    __tablename__ = 'FluorescenceResults'

    SDG = Column(String(50), primary_key=True)                          # Sample Data Group
    BatchID = Column(String(50), primary_key=True)                      # Leidos Batch ID
    Method = Column(String(20))                                         # Analytical Method
    SampleID = Column(String(50), primary_key=True)                     # Sample identifier
    Matrix = Column(String(50))                                         # Sample matrix (e.g., soil)    
    ResultType = Column(String(12))                                     # Result Type (REG, BLK, LCS, etc.)
    Analyte = Column(String(50))                                        # Beryllium
    Result = Column(Float)                                              # Counts value
    ResultUnits = Column(String(10))                                    # Result in ug/100cm^3
    PPB = Column(Float)                                                 # PPB Results
    RFU = Column(Float)                                                 # RFU Results
    Aliquot = Column(Float)                                             # Aliquot
    AliquotUnits = Column(String(10))                                   # Aliquot Units
    CalibrationCurve = Column(Float)                                    # R^2 of cal curve
    PrepDateTime = Column(DateTime)                                     # Prep datetime
    AnalysisDateTime = Column(DateTime)                                 # Analysis datetime
    PrepsheetFilePath = Column(String(250))                             # Path to prep sheet
    ProcessedDataFilePath = Column(String(255))
    Iteration = Column(Integer, primary_key=True)                       # Iteration number
    Reporting = Column(Boolean, primary_key=True)                       # Reporting status (True/False)

class LSCResults(Base):
    __tablename__ = 'LSCResults'

    SDG = Column(String(50), primary_key=True)                          # Sample Data Group
    BatchID = Column(String(50), primary_key=True)                      # Leidos Batch ID
    Method = Column(String(20))                                         # Analytical Method
    SampleID = Column(String(50), primary_key=True)                     # Sample identifier
    Matrix = Column(String(50))                                         # Sample matrix (e.g., soil)    
    ResultType = Column(String(12))                                     # Result Type (REG, BLK, LCS, etc.)
    Analyte = Column(String(50),primary_key=True)                                        # Beryllium
    Result = Column(Float)                                              # Counts value
    ResultUnits = Column(String(10))                                    # Result in ug/100cm^3
    ResultError = Column(Float)                                         # Alpha Concentration error
    Aliquot = Column(Float)                                             # Aliquot
    AliquotUnits = Column(String(10))                                   # Aliquot Units
    CPM = Column(Float)
    LiveTime = Column(Float)                                            # Live time in seconds
    BKGCPM = Column(Float)
    BKGLiveTime = Column(Float)
    NCPM = Column(Float )
    tSIE = Column(Float)
    PercentRecovery = Column(Float)
    MDA = Column(Float)
    DL = Column(Float)
    Efficiency = Column(Float)
    PrepDateTime = Column(DateTime)                                     # Prep datetime
    AnalysisDateTime = Column(DateTime)                                 # Analysis datetime
    PrepsheetFilePath = Column(String(250))                             # Path to prep sheet
    ProcessedDataFilePath = Column(String(255))
    Iteration = Column(Integer, primary_key=True)                       # Iteration number
    Reporting = Column(Boolean, primary_key=True)                       # Reporting status (True/False)

class WetChemResults(Base):
    __tablename__ = 'WetChemResults'

    SDG = Column(String(50), primary_key=True)                          # Sample Data Group
    BatchID = Column(String(50), primary_key=True)                      # Leidos Batch ID
    Method = Column(String(20))                                         # Analytical Method
    SampleID = Column(String(50), primary_key=True)                     # Sample identifier
    Matrix = Column(String(50))                                         # Sample matrix (e.g., soil)    
    ResultType = Column(String(12))                                     # Result Type (REG, BLK, LCS, etc.)
    Analyte = Column(String(50))
    Result = Column(Float)                                              # Counts value
    ResultUnits = Column(String(10))                                    # Result in ug/100cm^3
    Aliquot = Column(Float)                                             # Aliquot
    AliquotUnits = Column(String(10))                                   # Aliquot Units
    PrepDateTime = Column(DateTime)                                     # Prep datetime
    AnalysisDateTime = Column(DateTime)                                 # Analysis datetime
    PrepsheetFilePath = Column(String(250))                             # Path to prep sheet
    ProcessedDataFilePath = Column(String(255))
    Iteration = Column(Integer, primary_key=True)                       # Iteration number
    Reporting = Column(Boolean, primary_key=True)                       # Reporting status (True/False)

# class TCLPResults(Base):
#     __tablename__ = 'TCLPResults'

# class XRDResults(Base):
#     __tablename__ = 'XRDResults'

# class FIMSResults(Base):
    #     __tablename__ = 'FIMSResults'

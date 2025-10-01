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

class ConsumableManagement(Base):
    __tablename__ = 'ConsumableManagement'

    ConsumableID = Column(String(50), primary_key=True)
    LotNumber = Column(String(255), primary_key=True)
    Compound = Column(String(50))
    Method = Column(String(255))
    Matrix = Column(String(255))
    Type = Column(String(50))
    StartDate = Column(Date, primary_key=True)
    ExpirationDate = Column(Date)
    Component = Column(String(255), primary_key=True)
    Volume = Column(String(255))
    Mass = Column(String(255))
    Concentration = Column(String(255))
    Activity = Column(String(255))
    Status = Column(Boolean, primary_key=True)
    FilePath = Column(String(255))

class EquipmentManagement(Base):
    __tablename__ = 'EquipmentManagement'

    EquipmentID = Column(String(50), primary_key=True)
    Type = Column(String(50))
    MinVolume = Column(Float)
    MaxVolume = Column(Float)
    AssignedMass = Column(Float)
    MinTemp = Column(Float)
    MaxTemp = Column(Float)
    Hysteresis = Column(Float)
    Date = Column(Date)
    Time = Column(Time)
    SerialNumber = Column(String(50))
    Model = Column(String(50))
    Brand = Column(String(50))
    Ownership = Column(String(50))
    Location = Column(String(50))
    TagNumber = Column(String(50))
    Status = Column(String(8))
    Notes = Column(String(255))

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
    FilePath = Column('FilePath', String(255))

class SampleLogin(Base):
    __tablename__ = 'SampleLogin'

    SDG = Column(String(250), primary_key=True)
    SampleID = Column(String(50), primary_key=True)
    Matrix = Column(String(50))
    HG = Column(Boolean)
    ISOAM = Column(Boolean) 
    ISOTH = Column(Boolean)
    ISOU = Column(Boolean)
    ISOPU = Column(Boolean)
    GAMMA = Column(Boolean)
    GFPC = Column(Boolean)
    LSCPU = Column(Boolean)
    LSCSR = Column(Boolean)
    LSCAB = Column(Boolean)
    MET = Column(Boolean)
    TCLP = Column(Boolean)
    BEF = Column(Boolean)
    SIO2 = Column(Boolean)
    FLUOR = Column(Boolean)
    NH3 = Column(Boolean)
    NO3 = Column(Boolean)
    NO2 = Column(Boolean)
    CRVI = Column(Boolean)
    CL = Column(Boolean)
    PH = Column(Boolean)
    TSS = Column(Boolean)
    TSP = Column(Boolean)
    LocationID = Column(String(50))
    SampleVolume = Column(Integer)
    Count = Column(Integer)
    U235Concentration = Column(Integer)
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
    MDL = Column(Float)
    DL = Column(Float)
    LOD = Column(Float)
    LOQ = Column(Float)
    Units = Column(String(20))
    EffectiveDate = Column(Date, primary_key=True)

class RADCerts(Base):
    __tablename__ = 'RADCerts'

    PrincipleRadionuclide = Column(String(50), primary_key=True)
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

class HGResults(Base):
    __tablename__ = 'HGResults'

    SDG = Column(String(50), primary_key=True)                             # Sample Data Group
    BatchID = Column(String(50), primary_key=True)                         # Leidos Batch ID
    Method = Column(String(20))                                            # Analytical Method
    SampleID = Column(String(50), primary_key=True)                        # Sample identifier
    Matrix = Column(String(50))                                            # Sample matrix (e.g., soil)
    ResultType = Column(String(12))                                        # Result Type (REG, BLK, LCS, etc.)
    Analyte = Column(String(50), primary_key=True) 
    Aliquot = Column(Float)
    AliquotUnits = Column(String(10))
    InitialWeightVolume = Column(Float)
    PrepVolume = Column(Float)
    VolumeUnits = Column(String(10))
    WeightUnits = Column(String(10))
    SampleUnits = Column(String(10))
    Result = Column(Float)                                                 # Activity value
    ResultUnits = Column(String(10))
    CalResult = Column(Float)
    CalResultUnits = Column(String(10))
    PercentRecovery = Column(Float) 
    RSD = Column(Float)
    AnalysisDateTime = Column(DateTime, primary_key=True)
    PrepDateTime = Column(DateTime)
    Rep1 = Column(Float)
    CalResult1 = Column(Float)
    Result1 = Column(Float)
    Rep1DateTime = Column(DateTime)
    Rep2 = Column(Float)
    CalResult2 = Column(Float)
    Result2 = Column(Float)
    Rep2DateTime = Column(DateTime)
    Rep3 = Column(Float)
    CalResult3 = Column(Float)
    Result3 = Column(Float)
    Rep3DateTime = Column(DateTime)
    PrepsheetFilePath = Column(String(255))
    Analyst = Column(String(24))
    ProcessedDataFilePath = Column(String(255))
    Iteration = Column(Integer, primary_key=True)                          # Iteration number
    Reporting = Column(Boolean, primary_key=True)                          # Reporting status (True/False)

class METResults(Base):
    __tablename__ = 'METResults'

    SDG = Column(String(50), primary_key=True)                             # Sample Data Group
    BatchID = Column(String(50), primary_key=True)                         # Leidos Batch ID
    Method = Column(String(20))                                            # Analytical Method
    SampleID = Column(String(50), primary_key=True)                        # Sample identifier
    Matrix = Column(String(50))                                            # Sample matrix (e.g., soil)
    ResultType = Column(String(12))                                        # Result Type (REG, BLK, LCS, etc.)
    Analyte = Column(String(50), primary_key=True) 
    Isotope = Column(String(12))
    Aliquot = Column(Float)
    SampleWeightVolume = Column(Float)
    FinalWeightVolume = Column(Float)                                      # Final Weight or Volume
    DilutionFactor = Column(Float)
    DilutionMultiplier = Column(Float)
    AliquotUnits = Column(String(10))
    Result = Column(Float)                                                 # Activity value
    InitialResult = Column(Float)
    ResultRSD = Column(Float)
    ResultUnits = Column(String(10))  
    PercentRecovery = Column(Float) 
    LOD = Column(Float)
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
    METBatchName = Column(String(50))
    METFileName = Column(String(50))
    METPath = Column(String(255))
    PrepsheetFilePath = Column(String(255))
    Analyst = Column(String(24))
    ProcessedDataFilePath = Column(String(255))
    Iteration = Column(Integer, primary_key=True)                          # Iteration number
    Reporting = Column(Boolean, primary_key=True)                          # Reporting status (True/False)

class GAMMAResults(Base):
    __tablename__ = 'GAMMAResults'

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
    PercentRecovery = Column(Float) 
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

class GFPCResults(Base):
    __tablename__ = 'GFPCResults'

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
    PercentRecovery = Column(Float) 
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

class ALPHAResults(Base):
    __tablename__ = 'ALPHAResults'

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
    InitialResult = Column(Float)                                       # Activity before adjustment from tracer
    Result = Column(Float)                                              # Activity value
    ResultError = Column(Float)                                         # Uncertainty in the activity measurement
    ResultUnits = Column(String(10))                                    # Units of activity
    PercentRecovery = Column(Float) 
    TracerRecovery = Column(Float)                                      # Tracer recovery value
    TracerFWHM = Column(Float)                                          # Tracer full width at half maximum
    MDA = Column(Float)                                                 # Minimum detectable concentration
    MDAConfidenceFactor = Column(Float)                                 # Confidence factor for MDA
    MDALLDConstant = Column(Integer)                                    # Constant value for MDA LLD
    PercentAbundance = Column(Float)                                    # Percent abundance
    LiveTime = Column(Float)                                            # Elapsed live time
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

class BEFResults(Base):
    __tablename__ = 'BEFResults'

    SDG = Column(String(50), primary_key=True)                          # Sample Data Group
    BatchID = Column(String(50), primary_key=True)                      # Leidos Batch ID
    Method = Column(String(20))                                         # Analytical Method
    SampleID = Column(String(50), primary_key=True)                     # Sample identifier
    Matrix = Column(String(50))                                         # Sample matrix (e.g., soil)    
    ResultType = Column(String(12))                                     # Result Type (REG, BLK, LCS, etc.)
    Analyte = Column(String(50))                                        # Beryllium
    Result = Column(Float)                                              # Counts value
    ResultUnits = Column(String(10))                                    # Result in ug/100cm^3
    PercentRecovery = Column(Float) 
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
    PercentRecovery = Column(Float) 
    Aliquot = Column(Float)                                             # Aliquot
    AliquotUnits = Column(String(10))                                   # Aliquot Units
    CPM = Column(Float)
    LiveTime = Column(Float)                                            # Live time in seconds
    BKGCPM = Column(Float)
    BKGLiveTime = Column(Float)
    NCPM = Column(Float )
    tSIE = Column(Float)
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
    PercentRecovery = Column(Float) 
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

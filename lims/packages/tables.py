from sqlalchemy import create_engine, Column, String, Boolean, Float, Integer, DateTime, Date, Time, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker


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
    SampleSize = Column(Float)                                          # Size of the sample
    SampleSizeUnits = Column(String(20))                                # Units for sample size
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
    EfficiencyFactor = Column(Float)                                    # Alpha Efficiency Factor
    Procedure = Column(String(100))                                     # Procedure
    DetectorSN = Column(String(50))                                     # Detector Serial Number
    EfficiencyCalibrationDateTime = Column(DateTime)                    # Activity to MDA ratio
    PrepDateTime = Column(DateTime)
    AcquisitionDateTime = Column(DateTime)                              # Date Received
    AnalysisDateTime = Column(DateTime)                                 # Analysis Date
    PrepsheetFilePath = Column(String(250))
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
    Iteration = Column(Integer, primary_key=True)                       # Iteration number
    Reporting = Column(Boolean, primary_key=True)                       # Reporting status (True/False)
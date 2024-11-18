from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate
from reportlab.platypus import Table as RLTable, TableStyle, Paragraph, Spacer
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from PyPDF2 import PdfReader, PdfWriter
import os
import json
from sqlalchemy import Table, create_engine, Column, MetaData, between, and_, func, Integer, Boolean, String, Date, Time, Float, DateTime, desc, Unicode
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.exc import SQLAlchemyError
import config

Base = declarative_base()

engine = create_engine(config.CONNECTION_STRING)
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)
session = Session()

class ConsumableManagement(Base):
    __tablename__ = 'ConsumableManagement'

    Method = Column(String(250))
    Type = Column(String(50))
    Compound = Column(Unicode(50), primary_key=True)
    Consumable = Column(String(50), primary_key=True)
    ConsumableID = Column(String(50), primary_key=True)
    LotNumber = Column(String(100), primary_key=True)
    CatalogNumber = Column(String(50), primary_key=True)
    ReceivedDate = Column(Date)
    ActivityDate = Column(Date)
    ExpirationDate = Column(Date)
    Manufacturer = Column(String(50))
    Volume = Column(Float)
    VolumeUnits = Column(String(10))
    Mass = Column(Float)
    MassUnits = Column(String(10))
    Concentration = Column(Float)
    ConcentrationUnits = Column(String(10))
    Activity = Column(Float)
    ActivityUnits = Column(String(10))
    Status = Column(String(10))
    Notes = Column(String(250))
    FilePath = Column(String(250))

# Query Function for FilePath
def get_file_path(session, consumable, consumable_id, status):
    try:
        result = session.query(ConsumableManagement.FilePath).filter_by(
            Consumable=consumable,
            ConsumableID=consumable_id,
            Status=status
        ).first()
        return result.FilePath if result else None
    except SQLAlchemyError as e:
        print(f"Database error: {e}")
        return None

# Load JSON Data
file_name = "pdf_testing\Prep-24LLB0002.json"
with open(file_name, "r") as file:
    data = json.load(file)

# Create the Prepsheet PDF
prepsheet_pdf = f"{data['prepsheet_name']}.pdf"
doc = SimpleDocTemplate(prepsheet_pdf, pagesize=letter)

styles = getSampleStyleSheet()
title_style = styles["Title"]
normal_style = styles["Normal"]
bold_style = styles["Heading3"]

elements = []

# Add Title
elements.append(Paragraph(f"Prepsheet Report: {data['prepsheet_name']}", title_style))
elements.append(Spacer(1, 12))

# Add General Info
general_info = [
    ["Batch ID:", data["batch_id"]],
    ["Chosen Method:", data["chosen_method"]],
    ["Prep Sheet Name:", data["prepsheet_name"]],
]
for label, value in general_info:
    elements.append(Paragraph(f"<b>{label}</b> {value}", normal_style))
    elements.append(Spacer(1, 6))

# Add Consumables Section with Embedded PDFs
def add_consumables_section(session, title, items):
    elements.append(Paragraph(f"{title}:", bold_style))
    pdf_paths = []
    for consumable, details in items.items():
        consumable_id, status = details.split(" ")[0], details.split(" ")[1].strip("()")
        file_path = get_file_path(session, consumable, consumable_id, status)
        if file_path and os.path.exists(file_path):
            pdf_paths.append(file_path)  # Collect paths for merging
            elements.append(Paragraph(f"- {consumable}: {details} (File Attached)", normal_style))
        else:
            elements.append(Paragraph(f"- {consumable}: {details} (File Missing)", normal_style))
    elements.append(Spacer(1, 12))
    return pdf_paths

# Use SQLAlchemy Session to Fetch FilePaths
pdf_paths = []
with Session() as session:
    pdf_paths.extend(add_consumables_section(session, "Reagents", data["Reagents"]))
    pdf_paths.extend(add_consumables_section(session, "Standards", data["Standards"]))
    pdf_paths.extend(add_consumables_section(session, "Tracers", data["Tracers"]))
    pdf_paths.extend(add_consumables_section(session, "LCSs", data["LCSs"]))

# Add Sample Data Table
elements.append(Paragraph("Sample Data:", bold_style))
samples = data["Samples"]
headers = list(samples.keys())
table_data = [headers]  # Add headers
rows = zip(*samples.values())  # Transpose data
for row in rows:
    table_data.append(row)

table = RLTable(table_data, repeatRows=1)
table.setStyle(TableStyle([
    ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
    ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
    ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
    ("GRID", (0, 0), (-1, -1), 1, colors.black),
]))
elements.append(table)

# Build the Prepsheet PDF
doc.build(elements)

# Merge External PDFs
if pdf_paths:
    writer = PdfWriter()
    writer.append(prepsheet_pdf)  # Add the generated prepsheet
    for pdf_path in pdf_paths:
        writer.append(pdf_path)  # Add each consumable PDF
    final_pdf = f"Final-{prepsheet_pdf}"
    with open(final_pdf, "wb") as output_file:
        writer.write(output_file)
    print(f"Final report generated: {final_pdf}")
else:
    print(f"Prepsheet report generated: {prepsheet_pdf}")

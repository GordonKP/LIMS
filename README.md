# Laboratory Information Management System (LIMS)

A Python-based desktop Laboratory Information Management System designed to modernize laboratory data management, automate operational workflows, and improve data reliability across regulated environmental laboratory environments.

This project was developed as a multi-site internal data platform supporting laboratory operations, sample tracking, reporting, quality control, inventory management, equipment management, and compliance-oriented data workflows.

## Overview

The LIMS application was built to replace fragmented and manual laboratory data processes with a centralized desktop application backed by SQL databases and automated data workflows.

The system was designed, developed, deployed, and maintained independently across multiple laboratory sites. Each site required its own database schema, workflow customizations, reporting logic, validation rules, and deployment process.

## Key Features

* Desktop application built with Python and PyQt5
* SQL-backed laboratory data management
* Custom database schemas for site-specific laboratory workflows
* Sample login and chain-of-custody tracking
* Data quality objectives and laboratory limits management
* Consumable and equipment management
* Automated reporting and PDF generation
* Excel-based data import/export workflows
* QA/QC validation and data integrity checks
* Statistical monitoring and anomaly detection support
* User authentication and role-based workflow support
* Packaged executable deployment using PyInstaller
* Versioning and release management for production deployments

## Technical Stack

**Languages & Frameworks**

* Python
* PyQt5
* SQLAlchemy
* pandas
* NumPy
* scikit-learn

**Databases & Data Access**

* SQL Server
* PostgreSQL-compatible workflows
* ODBC
* SQLAlchemy ORM

**Reporting & Documents**

* ReportLab
* PyMuPDF
* pikepdf
* openpyxl
* XlsxWriter
* matplotlib

**Deployment & Packaging**

* PyInstaller
* Git
* Release-based desktop deployment

## Architecture

The application follows a modular desktop architecture with separate layers for:

* User interface components
* Database models and table definitions
* Configuration and site-specific settings
* Data transformation workflows
* Reporting utilities
* Standalone deployment tools
* Release and update management

The system was designed to support multiple laboratory sites while allowing each site to maintain customized schemas, workflows, and reporting requirements.

## Business Impact

This project was developed to address failing manual processes and fragmented laboratory data systems.

The platform helped automate multi-site laboratory workflows, reduce manual operational effort, improve data reliability, and support regulated reporting processes. The system contributed to estimated operational cost reductions of approximately $500K per site through workflow automation, reporting improvements, and reduced dependency on manual data handling.

## Security Notice

This public repository has been sanitized for portfolio and demonstration purposes.

Sensitive configuration files, credentials, internal server names, connection strings, proprietary datasets, and site-specific production details are intentionally excluded.

Example configuration files should be used in place of real production credentials.

## Repository Status

This project represents a production-oriented internal data platform adapted for public portfolio review. Some implementation details, internal documentation, credentials, and proprietary business logic may be removed or generalized for security and confidentiality reasons.

## What This Project Demonstrates

* End-to-end software ownership
* Desktop application development
* Database schema design
* SQL-backed data workflows
* ETL and data validation
* Laboratory operations automation
* Regulated data environment experience
* Reporting automation
* Production deployment and release management
* Cross-site implementation and customization

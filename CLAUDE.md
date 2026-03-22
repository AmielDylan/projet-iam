# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

IAM (Interactions A Medicaments) is a Flask web application for visualizing drug interactions. Users enter two medication names and the system queries a MySQL database to display potential interactions between them.

## Commands

```bash
# Run development server
flask run

# Build Sphinx documentation
make html
# Documentation output: build/html/index.html
```

## Architecture

### Backend (Flask + MySQL)

- **app.py**: Flask application entry point. Routes handle form submissions and AJAX requests for autocomplete/medication type detection.
- **static/requetes.py**: Database layer with direct MySQL queries and stored procedure calls. All database logic lives here.

The Flask variable is named `application` (not `app`) for AWS Elastic Beanstalk compatibility.

### Database

Uses MySQL database `projet_ipa` with stored procedures:
- `getInteractionsClasses`: Find interactions between two medication classes
- `getInteractionsResults`: Get detailed interaction information
- `getClassesId`, `getSubstanceId`, etc.: Lookup procedures for medication entities

Three medication entity types exist: **classes** (drug categories), **substances** (active ingredients), and **specialites** (brand names). The interaction lookup resolves any input type to its classes, then queries interactions between class pairs.

### Frontend

- **templates/index.html**: Single-page form with Bootstrap 5.2.3
- **static/index.js**: Vanilla JS handling autocomplete and dynamic class selection
- **static/index.css**: Custom styling with dark gradient theme

### Deployment

AWS Elastic Beanstalk configuration in `.ebextensions/python.config` sets WSGI path to `application:application`.

# TimeTrack

TimeTrack is a web-based time tracking application built with Flask that helps users monitor their work hours, breaks, and maintain a history of their time entries.

## Features

- **Time Tracking**: Record arrival and departure times
- **Break Management**: Pause and resume work sessions
- **Daily Overview**: View today's time entries at a glance
- **Complete History**: Access all past time entries
- **Configuration**: Customize work hours and break settings

## Tech Stack

- **Backend**: Flask 2.0.1
- **Database**: SQLAlchemy with SQLite
- **Frontend**: HTML, CSS, JavaScript

## Installation

### Prerequisites

- Python 3.12
- pip or pipenv

### Setup with pipenv (recommended)

```bash
# Clone the repository
git clone https://github.com/nullmedium/TimeTrack.git
cd TimeTrack

# Install dependencies using pipenv
pipenv install

# Activate the virtual environment
pipenv shell

# Initialize the database
python migrate_db.py

# Run the application
python app.py
```

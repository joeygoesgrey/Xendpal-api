# Xendpal-App

A file sharing platform built with FastAPI.

## Table of Contents

- [Usage](#usage)
- [Project Structure](#project-structure)
- [License](#license)

## Prerequisites

- Docker installed on your machine.

## Usage

To start the server, run:

```bash
docker pull lovehacking7/xendpal_backend:latest
```

5. **Project Structure**:
   - A brief explanation of the project's directory structure.

````markdown
## Project Structure

````plaintext
 
.
├── alembic  # Database migration files
│   ├── env.py
│   ├── README
│   ├── script.py.mako
│   └── versions
├── alembic.ini
├── api_app    # Core application files
│   ├── config.py #env variables schema
│   ├── database.py #database configurations
│   ├── extras.py #utility functions
│   ├── __init__.py
│   ├── main.py    # the setup of the api app
│   ├── models.py #models code 
│   ├── Oauth2.py #auth functions
│   ├── __pycache__
│   ├── routers  # Route definitions
│   ├── schema.py #api scheams
│   └── templates # All email templates
├── core
├── Dockerfile #Dockerfile on the building of the image
├── docs  # Documentation
│   ├── build
│   ├── make.bat
│   ├── Makefile
│   └── source
├── entrypoint.sh
├── Pipfile
├── Pipfile.lock
├── README.md
└── Uploads #path to user files

## License

This project is licensed under the MIT License - see the `LICENSE` file for details.
````
````

# Setup

You may want to create a virtualenv for the fast\_grow\_server:
```bash
python3 -m venv venv
source venv/bin/activate
```

Install all requirements with pip:
```bash
pip install -r requirements.txt
```
The dependency psycopg-2 needs dev headers to build. Ensure you have "python3-dev" and "libpq".

At this point either set the environment variables `$USER`, `$PASSWORD` and `$DATABASE` to the ones configured in the `fast\_grow\_server/settings.py` or replace them with appropriate values below.

fast\_grow\_server requires a postgres database and a separate database user. You can create a user with appropriate permissions with this:
```bash
psql -d postgres -c "CREATE ROLE $USER WITH ENCRYPTED PASSWORD '$PASSWORD'; ALTER ROLE $USER WITH LOGIN CREATEDB;"
```
To create the fast\_grow\_server database execute the following:
```bash
psql -d postgres -c "CREATE DATABASE $DATABASE;"
```

Perform the fast\_grow\_server migrations with:
```bash
python manage.py migrate
```

Ensure the bin directory exists and contains the following binaries:
  - bin/preprocessor

The default configured backend and result system for celery is redis. Redis must be installed and available at the url configured in the `fast\_grow\_server/settings.py`.

To run the tests execute:
```bash
python manage.py test
```

Celery workers can be run with:
```bash
celery -A fast_grow_server worker --loglevel=INFO
```
...or in a more debug and IDE friendly way:
```bash
python venv/bin/celery -A fast_grow_server worker --loglevel=INFO
```

To start the server run:
```bash
python manage.py runserver
```
...which should start the server at http://localhost:8000/


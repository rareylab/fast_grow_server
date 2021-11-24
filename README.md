# FastGrow Server

## Setup

Get python dependencies with [conda](https://docs.conda.io/en/latest/miniconda.html).
```bash
conda create --name fastgrow -c anaconda -c conda-forge python=3.8 django celery psycopg2 redis redis-py vine pylint pylint-django coverage
conda activate fastgrow
```

At this point either set the environment variables `$USER`, `$PASSWORD` and
`$DATABASE` to the ones configured in the `fast\_grow\_server/settings.py` or
replace them with appropriate values below.

fast\_grow\_server requires a postgres database and a separate database user.
You can create a user with appropriate permissions with this:
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
  - bin/Clipper
  - bin/DatabaseBuilder
  - bin/FastGrow
  - bin/Preprocessor

The default configured backend and result system for celery is redis. Redis
must be installed and available at the url configured in the
`fast\_grow\_server/settings.py`.

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

## Code Quality

Contributions to the project must comply to the following quality criteria to
keep the code maintainable for all developers:

| Criteria               | Threshold     |
| -------------          |:-------------:|
| pylint                 | \>9.0         |
| coverage (overall)     | \>90%         |
| coverage (single file) | \>80%         |


Run pylint for static code quality check with
```bash
find fast_grow* -type f -name "*.py" | xargs pylint --load-plugins pylint_django --django-settings-module=fast_grow_server.settings
```

Run test coverage
```bash
coverage run --source=fast_grow manage.py test
coverage report
```

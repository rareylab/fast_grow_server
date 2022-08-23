# FastGrow Server

Server backend of the FastGrow web application. FastGrow is a fast fragment growing approach using
a [shape-based](https://doi.org/10.1021/acs.jcim.0c00920) algorithm. A detailed explanation of the method can be found
in the accompanying paper:

Patrick Penner, Virginie Martiny, Louis Bellmann, Florian Flachsenberg, Marcus Gastreich, Isabelle Theret, Christophe Meyer and Matthias
Rarey (2022) FastGrow: On-the-Fly Growing and its Application to DYRK1A, J. Comput. Aided Mol. Des., [https://doi.org/10.1007/s10822-022-00469-y](https://doi.org/10.1007/s10822-022-00469-y).

A running instance of the web application can be found
at [https://grow.zbh.uni-hamburg.de/](https://grow.zbh.uni-hamburg.de/)

Core FastGrow functionality will be available in BioSolveIT’s [SeeSAR](https://www.biosolveit.de/SeeSAR/) modeling
package.

The sibling frontend repository can be found at
[https://github.com/rareylab/fast_grow_frontend](https://github.com/rareylab/fast_grow_frontend)

## Setup

Get python dependencies with [conda](https://docs.conda.io/en/latest/miniconda.html).

```bash
conda create --name fastgrow -c anaconda -c conda-forge python=3.9 django celery psycopg2 redis redis-py vine pylint pylint-django coverage selenium
conda activate fastgrow
```

At this point either set the environment variables `$USER`, `$PASSWORD` and
`$DATABASE` to the ones configured in the `fast\_grow\_server/settings.py` or replace them with appropriate values
below.

fast\_grow\_server requires a postgres database and a separate database user. You can create a user with appropriate
permissions with this:

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

The default configured backend and result system for celery is redis. Redis must be installed and available at the url
configured in the
`fast\_grow\_server/settings.py`.

To run the tests execute:

```bash
python manage.py test
```

Celery workers can be run with:

```bash
celery -A fast_grow_server worker --loglevel=INFO -O fair
```

...or in a more debug and IDE friendly way:

```bash
python /path/to/env/fastgrow/bin/celery -A fast_grow_server worker --loglevel=INFO -O fair
```

To start the server run:

```bash
python manage.py runserver
```

...which should start the server at http://localhost:8000/

## Code Quality

Contributions to the project must comply to the following quality criteria to keep the code maintainable for all
developers:

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

.. _development:

Developing patchwork
====================

Quick Start
-----------

We have scripts that will get developers started in no time::

    $ git clone https://github.com/dlespiau/patchwork/
    $ cd patchwork
    $ ./tools/setup-devel.sh
    $ ./tools/run-devel.sh

``setup-devel.sh`` will:

- Create a virtual environment in the ``venv`` directory,
- Install all the required dependencies in that virtual environment,
- Populate a SQLite database with a few patches,
- Create an ``admin`` account with ``pass`` as password.

``run-devel.sh`` will run the web server serve the patchwork
application. Pointing your browser to http://127.0.0.1:8000/ should
bring up patchwork.

Using virtualenv
----------------

It's a good idea to use virtualenv to develop Python software. Virtual
environments are "instances" of your system Python, without any of the
additional Python packages installed. They are useful to develop and
deploy patchwork against a "well known" set of dependencies, but they
can also be used to test patchwork against several versions of Django.

1. Install pip, virtualenv (python-pip, python-virtualenv packages)

Because we're going to recompile our dependencies, we'll also need
development headers. For the MySQL/MariaDB setups these are
``mariadb-devel`` (Fedora), ``libmysqlclient-dev`` (Debian)

2. Create a new virtual environement.

Inside a virtual env, we'll just install the dependencies needed for
patchwork and run it from there.

::

    $ virtualenv django-1.8

This will create a virtual env called 'django-1.8' in the eponymous
directory.

3. Activate a virtual environment

::

    $ source django-1.8/bin/activate
    (django-1.8)$

The shell prompt is preprended with the virtual env name.

4. Install the required dependencies

To ease this task, it's customary to maintain a list of dependencies in
a text file and install them in one go. Patchwork can work with multiple
databases so we keep the requirements for each supported db::

    (django-1.8)$ pip install -r docs/requirements-dev-mysql.txt

or::

    (django-1.8)$ pip install -r docs/requirements-dev-postgresql.txt

5. Export the ``DJANGO_SETTINGS_MODULE`` variable

Django needs to be told which settings to use. By default it will try to load
settings from the :file:`patchwork/settings/production.py` file. This can be
overridden with the ``DJANGO_SETTINGS_MODULE`` environment variable.

Patchwork provides a convenience settings template suitable for development in
:file:`patchwork/settings/dev.py`. To use it, you can simply export the path to
this file (in Python module format) like so::

    (django-1.8)$ export DJANGO_SETTINGS_MODULE=patchwork.settings.dev

And adjust your database settings through environment variables. See the
`Environment Variables`_ section below for details. For example::

    (django-1.8)$ export PW_TEST_DB_USER=root
    (django-1.8)$ export PW_TEST_DB_PASS=password

You may also provide your own settings file and have ``DJANGO_SETTINGS_MODULE``
point to that file.


6. Run the development server

::

    (django-1.8)$ ./manage.py runserver

Once finished, you can kill the server (``Ctrl`` + ``C``) and exit the
virtual environment:

::

    (django-1.8)$ deactivate
    $

Should you wish to re-enter this environment, simply source the
``activate`` script again.

Environment Variables
---------------------

The following environment variables are available to configure various settings
if :file:`dev.py` is used:

PW_TEST_DB_NAME
  Name of the database. Defaults to ``patchwork``.

PW_TEST_DB_USER
  Username to access the database with. Defaults to ``patchwork``.

PW_TEST_DB_PASS
  Password to access the database with. Defaults to ``password``.

PW_TEST_DB_TYPE
  Type of database to use. Either ``mysql`` (default) or ``postgres``.

Running Tests
-------------

patchwork includes a `tox <https://tox.readthedocs.org/en/latest/>`__
script to automate testing. Before running this, you should probably
install tox:

::

    $ pip install tox

You can show available targets like so:

::

    $ tox --list

You'll see that this includes a number of targets to run unit tests
against the different versions of Django supported, along with some
other targets related to code coverage and code quality. To run these,
use the ``-e`` parameter:

::

    $ tox -e py27-django18

In the case of the unit tests targets, you can also run specific tests
by passing the fully qualified test name as an additional argument to
this command:

::

    $ tox -e py27-django18 patchwork.tests.SubjectCleanUpTest

Because patchwork supports multiple versions of Django, it's very
important that you test against all supported versions. When run without
argument, tox will do this:

::

    $ tox


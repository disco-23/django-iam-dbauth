import os
import signal
import subprocess

from django.core.files.temp import NamedTemporaryFile
from django.db.backends.base.client import BaseDatabaseClient, _escape_pgpass


class DatabaseClient(BaseDatabaseClient):
    executable_name = 'psql'

    @classmethod
    def runshell_db(cls, conn_params):
        args = [cls.executable_name]

        host = conn_params.get('host', '')
        port = conn_params.get('port', '')
        dbname = conn_params.get('database', '')
        user = conn_params.get('user', '')
        passwd = conn_params.get('password', '')

        if user:
            args += ['-U', user]
        if host:
            args += ['-h', host]
        if port:
            args += ['-p', str(port)]
        args += [dbname]

        temp_pgpass = None
        sigint_handler = signal.getsignal(signal.SIGINT)
        try:
            if passwd:
                # Create temporary .pgpass file.
                temp_pgpass = NamedTemporaryFile(mode='w+')
                try:
                    print(
                        _escape_pgpass(host) or '*',
                        str(port) or '*',
                        _escape_pgpass(dbname) or '*',
                        _escape_pgpass(user) or '*',
                        _escape_pgpass(passwd),
                        file=temp_pgpass,
                        sep=':',
                        flush=True,
                    )
                    os.environ['PGPASSFILE'] = temp_pgpass.name
                except UnicodeEncodeError:
                    # If the current locale can't encode the data, let the
                    # user input the password manually.
                    pass
            # Allow SIGINT to pass to psql to abort queries.
            signal.signal(signal.SIGINT, signal.SIG_IGN)
            DatabaseClient.extend_environment(conn_params)
            subprocess.check_call(args)
        finally:
            # Restore the original SIGINT handler.
            signal.signal(signal.SIGINT, sigint_handler)
            if temp_pgpass:
                temp_pgpass.close()
                if 'PGPASSFILE' in os.environ:  # unit tests need cleanup
                    del os.environ['PGPASSFILE']
            DatabaseClient.cleanup_environment()

    @classmethod
    def extend_environment(cls, conn_params):
        if 'password' in conn_params:
            os.environ['PGPASSWORD'] = conn_params['password']
        if 'sslmode' in conn_params:
            os.environ['PGSSLMODE'] = conn_params['sslmode']

    @classmethod
    def cleanup_environment(cls):
        os.environ.pop('PGPASSWORD', None)
        os.environ.pop('PGSSLMODE', None)

import boto3
import pretend

from django_iam_dbauth.aws.mysql.base import DatabaseWrapper


def test_get_connection_params(mocker):

    token_kwargs = {}

    def generate_db_auth_token(**kwargs):
        token_kwargs.update(kwargs)
        return "generated-token"

    client = pretend.stub(generate_db_auth_token=generate_db_auth_token)
    mocker.patch.object(boto3, "client", return_value=client)
    mock_resolve_result = mocker.Mock()
    mock_resolve_result.target.to_text.return_value = 'www.labdigital.nl'
    mocker.patch(
        'django_iam_dbauth.utils.dns.resolver.resolve',
        return_value=[mock_resolve_result]
    )

    settings = {
        "NAME": "example",
        "USER": "mysql",
        "PASSWORD": "secret",
        "PORT": 3306,
        "HOST": "example-cname.labdigital.dev",
        "ENGINE": "django_iam_dbauth.aws.mysql",
        "OPTIONS": {"use_iam_auth": 1, "region_name": "test"},
    }

    db = DatabaseWrapper(settings)
    params = db.get_connection_params()

    assert params["password"] == "generated-token"
    assert token_kwargs == {
        "DBHostname": "www.labdigital.nl",
        "DBUsername": "mysql",
        "Port": 3306,
    }

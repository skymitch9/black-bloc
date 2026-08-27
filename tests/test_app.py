from black_bloc import app, errors


def test_app_exposes_main():
    assert callable(app.main)
    assert (errors.EXIT_CONFIG, errors.EXIT_LOGIN) == (2, 3)

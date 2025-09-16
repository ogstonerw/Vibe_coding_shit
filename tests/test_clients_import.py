def test_import_user_client():
    from adapters import user_client
    assert callable(user_client.get_user_client)

def test_import_bot_client():
    from adapters import bot_client
    assert callable(bot_client.get_bot_client)

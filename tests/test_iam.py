
def test_home(client):
    assert client.get('/').status_code == 200

    response = client.post(
        '/', data={'med-1': 'a', 'med-2': 'a'}
    )
    assert response.status_code == 200

def test_testClasse(client):
    response = client.post(
        '/testClasse', data={'medTest': ''}
    )
    assert b"false" in response.data

    response = client.post(
        '/testClasse', data={'medTest': 'ADRENALINE'}
    )
    assert b"false" in response.data

    response = client.post(
        '/testClasse', data={'medTest': 'ABATACEPT'}
    )
    assert b"true" in response.data

def test_testSubstance(client):
    response = client.post(
        '/testSubstance', data={'medTest': 'ADRENALINE'}
    )
    assert b"true" in response.data

    response = client.post(
        '/testSubstance', data={'medTest': 'ABATACEPT'}
    )
    assert b"false" in response.data

    response = client.post(
        '/testSubstance', data={'medTest': ''}
    )
    assert b"false" in response.data

def test_getListClasses(client):
    response = client.post(
        '/getListClasses', data={'substance': ''}
    )
    assert b"[]" in response.data

    response = client.post(
        '/getListClasses', data={'substance': 'ADRENALINE'}
    )
    assert response.json == [
    "ADRÉNALINE (VOIE BUCCO-DENTAIRE OU SOUS-CUTANÉE)",
    "SYMPATHOMIMÉTIQUES ALPHA ET BÊTA (VOIE IM ET IV)"]

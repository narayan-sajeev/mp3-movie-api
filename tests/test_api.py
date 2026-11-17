import pytest

import main
from src import MovieStorage


def test_movies_persist(client, test_storage, uploaded_movies):
    # Create new storage pointing to same file
    second_storage = MovieStorage(test_storage.db_path)

    df = second_storage.get()
    count = second_storage.count_movies()

    # Check row count, columns and titles
    assert count == 20
    assert len(df) == 20
    assert list(df.columns) == ['title', 'release_year', 'rating', 'genre']

    # Define expected titles
    expected_titles = [
    'Movie A', 'Movie B', 'Movie B', 'Movie C', 'Movie D', 'Movie D', 'Movie E', 'Movie F', 'Movie G', 'Movie H', 'Movie I', 'Movie J', 'Movie K', 'Movie L', 'Movie M', 'Movie N', 'Movie O', 'Movie P', 'Movie Q', 'Movie R'
    ]

    # Confirm they match
    assert list(df['title']) == expected_titles

    # Compare IDs
    storage_rows = second_storage.select_columns(
        ['title', 'release_year', 'rating', 'genre'], limit=100
    )

    # Do GET request
    response = client.get('/movies?limit=100')
    # Confirm successful
    assert response.status_code == 200
    # Get data from request
    api_rows = response.json()['data']
    # Define expected IDs
    expected_ids = list(range(1, 21))

    storage_ids = [row['id'] for row in storage_rows]
    api_ids = [row['id'] for row in api_rows]

    # Check storage IDs match
    assert storage_ids == expected_ids
    # Check API IDs match
    assert api_ids == expected_ids


def test_cache_and_processing(client, uploaded_movies, processing_body):
    first100 = client.get('/movies?limit=100')
    first1 = client.get('/movies?limit=1')

    # Check 100 and 1 status codes
    assert first100.status_code == 200
    assert first1.status_code == 200

    # Check 100 and 1 response bodies
    assert main.cache.get(100) == first100.json()
    assert main.cache.get(1) == first1.json()

    # Check 100 again
    first100_repeat = client.get('/movies?limit=100')
    assert first100_repeat.status_code == 200
    # Check against first
    assert first100_repeat.json() == first100.json()

    process_response = client.post('/movies/process', json=processing_body)

    assert process_response.status_code == 200
    # Get json data
    body = process_response.json()

    # Compare with known output
    assert body['validation_rows_removed'] == 0
    assert body['cleaning_report'] == {
        'rows_before': 20,
        'rows_after': 16,
        'rows_removed': 4,
        'columns_before': 4,
        'columns_after': 4,
        'columns_removed': 0
    }

    # Ensure cache is empty
    assert main.cache.get(100) is None
    assert main.cache.get(1) is None

    # Retrieve again
    updated_response = client.get('/movies?limit=100')
    assert updated_response.status_code == 200

    updated_body = updated_response.json()
    assert updated_body['total_rows'] == 16

    # Define deduplicated titles and ids
    expected_titles = ['Movie A', 'Movie B', 'Movie C', 'Movie D', 'Movie E', 'Movie F', 'Movie G', 'Movie H', 'Movie I', 'Movie J', 'Movie K', 'Movie L', 'Movie M', 'Movie N', 'Movie O', 'Movie P']
    expected_ids = list(range(1, 17))

    # Retrieve titles and ids
    body_titles = [row['title'] for row in updated_body['data']]
    body_ids = [row['id'] for row in updated_body['data']]

    assert body_titles == expected_titles
    assert body_ids == expected_ids
    assert main.cache.get(100) == updated_body

def test_cache_hit_skips_database(client, uploaded_movies, monkeypatch):
    response = client.get('/movies?limit=100')
    # Ensure response is successful
    assert response.status_code == 200
    body = response.json()

    # Function inside function
    # Columns = None because count doesn't need columns
    def fail_if_ran(columns=None, limit=5):
        pytest.fail('Database should not be called on cache hit')

    # Fail test if either function is called
    monkeypatch.setattr(main.storage, 'select_columns', fail_if_ran)
    monkeypatch.setattr(main.storage, 'count_movies', fail_if_ran)

    # Repeat GET request
    response2 = client.get('/movies?limit=100')
    # Ensure success
    assert response2.status_code == 200
    # Compare to first body
    assert response2.json() == body
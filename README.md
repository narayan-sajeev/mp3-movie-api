# MP3 Movie Data Processing API

This application is built using FastAPI and manages a movie dataset using SQLite and a FakeRedis cache. Users start by
uploading a CSV through `/upload`, which the API validates to confirm the data is in the proper format. Then, it updates
the `movies` table while clearing any old cache data. 

Client applications are able to filter and sort the data using SQL
through `/movies/search` or can open specific entries using `/movies`. To improve efficiency, MovieCache stores
responses that expire in 90 seconds. Running `/movies/process` validates and reformats the DataFrame using code in
`data_pipeline`. Then, it updates the dataset with the cleaned one using SQLite, and clears the cache so all future
requests use the new dataset.

## How to Run the Application

Start the FastAPI server using:

```bash
python -m uvicorn main:app --reload
```

Run the tests using `pytest`:

```bash
python -m pytest tests -v
```

## Sample Request and Output

Send a POST request to `/movies/process` using the following JSON:

```json
{
  "validation": {
    "required_columns": [
      "title",
      "release_year",
      "rating",
      "genre"
    ],
    "numeric_columns": [
      "release_year",
      "rating"
    ]
  },
  "processing": {
    "remove_duplicates": true,
    "missing": {
      "enabled": true,
      "axis": "rows"
    },
    "outliers": {
      "enabled": true,
      "columns": [
        "rating"
      ],
      "method": "iqr",
      "threshold": 1.5
    }
  }
}
```

Expected output given `fixtures/sample_movies.csv`:

```json
{
  "validation_rows_removed": 0,
  "cleaning_report": {
    "rows_before": 20,
    "rows_after": 16,
    "rows_removed": 4,
    "columns_before": 4,
    "columns_after": 4,
    "columns_removed": 0
  }
}
```
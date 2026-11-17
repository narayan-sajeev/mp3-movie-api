import io
import logging
from pathlib import Path

import pandas as pd
from fastapi import FastAPI, File, HTTPException, Query, UploadFile

from data_pipeline import create_cleaning_report, process_data, validate_dataframe
from src import (
    HealthResponse,
    MovieCache,
    MovieDataResponse,
    MovieProcessingReport,
    MovieStorage,
    MovieUploadInfo,
    ProcessConfig,
    log_requests,
    setup_logging
)
from src.storage import MOVIE_COLUMNS

setup_logging(verbose=True)
logger = logging.getLogger(__name__)

app = FastAPI(title='Data Processing API', version='1.0.0')
app.middleware("http")(log_requests)

storage = MovieStorage()
cache = MovieCache()


@app.get('/health', response_model=HealthResponse)
def health_check():
    return {'status': 'ok', 'version': '1.0.0'}


# Create upload route
@app.post('/upload', response_model=MovieUploadInfo)
async def upload_dataset(file: UploadFile = File(...)):
    suffix = Path(file.filename or '').suffix.lower()

    if suffix != '.csv':
        logger.warning(f'Unsupported file format: {suffix}')
        raise HTTPException(status_code=400, detail='Only CSV files are accepted.')

    try:
        # Read contents of file
        contents = await file.read()
        df = pd.read_csv(io.BytesIO(contents))
    except (pd.errors.EmptyDataError, pd.errors.ParserError, UnicodeDecodeError) as e:
        logger.warning(f'Error reading CSV file: {e}')
        raise HTTPException(status_code=400, detail='Unsupported or unreadable CSV file.')

    # Ensure columns match
    if sorted(df.columns) != sorted(MOVIE_COLUMNS):
        logger.warning(f'Invalid CSV columns: {list(df.columns)}')
        raise HTTPException(status_code=400, detail=f'CSV must contain columns: {MOVIE_COLUMNS}',
                            )

    if df.empty:
        logger.warning('Uploaded CSV has no data rows')
        raise HTTPException(status_code=400, detail='Uploaded CSV has no data rows')

    df = df[MOVIE_COLUMNS]
    storage.save(df)
    # Clear cache to avoid caching old data
    cache.invalidate()

    filename = file.filename

    # Log save
    logger.info(f'Uploaded movies: filename={filename}, rows={len(df)}')

    return {
        'filename': filename,
        'rows': len(df),
        'columns': len(df.columns),
        'column_names': list(df.columns)
    }


@app.get('/movies', response_model=MovieDataResponse)
# Define limit default as 100, min as 1
def get_movies(limit: int = Query(default=100, ge=1)):
    cached = cache.get(limit)
    if cached is not None:
        logger.info(f"Retrieved cached movies: returned_rows={len(cached['data'])}")
        return cached

    total_rows = storage.count_movies()
    if total_rows == 0:
        # Define response
        response = {'data': [], 'total_rows': 0}
        cache.set(limit, response)
        logger.info('Retrieved movies: returned_rows=0')
        return response

    # Get records in those columns
    records = storage.select_columns(MOVIE_COLUMNS, limit=limit)
    response = {'data': records, 'total_rows': total_rows}
    # Save to cache
    cache.set(limit, response)
    logger.info(f'Retrieved movies: returned_rows={len(records)}')
    return response


@app.get('/movies/search', response_model=list[dict])
def query_movies(
        columns: list[str] = Query(default=["title"]),
        min_rating: float = Query(default=0, ge=0, le=10),
        limit: int = Query(default=100, ge=1)
):
    try:
        results = storage.query_movies(columns, min_rating, limit)
    except ValueError as error:
        logger.warning(f'Invalid movie search query: {error}')
        raise HTTPException(status_code=400, detail=str(error))

    logger.info(f'Queried movies: columns={columns}, min_rating={min_rating}, returned_rows={len(results)}'
                )

    return results


@app.post('/movies/process', response_model=MovieProcessingReport)
def process_dataset(config: ProcessConfig):
    df = storage.get()
    if df.empty:
        logger.warning('Empty movie dataset')
        raise HTTPException(status_code=400, detail='No stored movies')

    # Converts to json
    config_settings = config.model_dump()
    validation_settings = config_settings.get('validation', {})
    numeric_columns = validation_settings.get('numeric_columns', [])
    required_columns = validation_settings.get('required_columns', [])

    try:
        clean_df = validate_dataframe(df, required_columns, numeric_columns)
        validation_rows_removed = len(df) - len(clean_df)
        copy_df = clean_df.copy()
        processed_df = process_data(copy_df, config_settings)
        cleaning_report = create_cleaning_report(clean_df, processed_df)

    except ValueError as error:
        logger.warning(f'Error in validation or processing: {error}')
        raise HTTPException(status_code=400, detail=str(error))

    storage.save(processed_df)
    # Clear old cache
    cache.invalidate()

    rows_before, rows_after = cleaning_report['rows_before'], cleaning_report['rows_after']

    logger.info(
        f'Processed movies: validation_removed={validation_rows_removed}, '
        f'rows_before={rows_before}, rows_after={rows_after}'
    )

    return {
        'validation_rows_removed': validation_rows_removed,
        'cleaning_report': cleaning_report
    }

import logging
from pathlib import Path

logger = logging.getLogger(__name__)

def save_data(df, filepath):
    path = Path(filepath)
    # Create location if needed
    path.parent.mkdir(parents=True, exist_ok=True)
    # Don't save row indices
    df.to_csv(path, index=False)
    row_count = len(df)
    logger.debug(f'Saved {row_count} rows to {filepath}')
    return filepath
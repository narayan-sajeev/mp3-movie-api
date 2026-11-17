import json
import logging
from pathlib import Path

import pandas as pd
import yaml

logger = logging.getLogger(__name__)


def load_csv(filepath):
    df = pd.read_csv(filepath)
    logger.info(f'Loaded CSV file: {filepath} ({len(df)} rows)')
    return df


def load_json(filepath):
    with open(filepath, 'r') as f:
        data = json.load(f)
    logger.info(f'Loaded JSON file: {filepath}')
    return data


def load_yaml(filepath):
    with open(filepath) as f:
        data = yaml.safe_load(f)
    logger.info(f'Loaded YAML file: {filepath}')
    return data


def load_data(filepath):
    path = Path(filepath)
    ext = path.suffix.lower()

    if ext == '.csv':
        return load_csv(path)
    elif ext == '.json':
        return load_json(path)
    elif ext == '.yaml':
        return load_yaml(path)
    else:
        msg = f'Unsupported file format: {ext}'
        logger.error(msg)
        raise ValueError(msg)

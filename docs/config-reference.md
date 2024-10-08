# Configuration Reference

The following documents all configuration options in telicent-lib, their type, default value and intended purpose.


## Kafka

TBC - possibly a reusable file that works with Java or Python in the same way?


## Actions

### Adapter

| Configuration Variable | Type    | Default | Purpose |
|------------------------|---------|---------|---------|
| TARGET_TOPIC           | string  | -       |         |
| DEFAULT_SECURITY_LABEL | string  | -       |         |
| DATA_CATALOG_ENABLED   | boolean | True    |         |
| DATA_CATALOG_TOPIC     | string  | catalog |         |

### Mapper

| Configuration Variable     | Type   | Default | Purpose |
|----------------------------|--------|---------|---------|
| SOURCE_TOPIC               | string | -       |         |
| TARGET_TOPIC               | string | -       |         |
| DISABLE_PERSISTENT_HEADERS | string | -       |         |

### Projector

| Configuration Variable     | Type   | Default | Purpose |
|----------------------------|--------|---------|---------|
| SOURCE_TOPIC               | string | -       |         |


## Pipeline

## Heart Beat

| Configuration Variable      | Type    | Default         | Purpose |
|-----------------------------|---------|-----------------|---------|
| HEART_BEAT_ENABLED          | boolean | True            |         |
| HEART_BEAT_PROVENANCE_TOPIC | string  | provenance.live |         |
| HEART_BEAT_INTERVAL         | int     | 15              |         |

## Logging

| Configuration Variable  | Type    | Default        | Purpose |
|-------------------------|---------|----------------|---------|
| LOGGER_ENABLED          | boolean | True           |         |
| LOGGER_PROVENANCE_TOPIC | string  | provenance.log |         |
| LOGGER_LEVEL            | string  | INFO           |         |

## Error Handling

| Configuration Variable         | Type    | Default           | Purpose |
|--------------------------------|---------|-------------------|---------|
| ERROR_HANDLER_ENABLED          | boolean | True              |         |
| ERROR_HANDLER_PROVENANCE_TOPIC | string  | provenance.errors |         |

## Telemetry

| Configuration Variable | Type    | Default | Purpose |
|------------------------|---------|---------|---------|
| METRICS_ENABLED        | boolean | True    |         |

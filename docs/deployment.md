# Deployment

This guide is intended to provide information about deploying telicent-lib actions.

Run-time configuration of telicent-lib is provided by a configurator, which in most cases will expect run-time
options to be set via ENV variables.

## Configuring Kafka in a live environment

telicent-lib has a dependency on [confluent-kafka](https://github.com/confluentinc/confluent-kafka-python/), which is a wrapper around [librdkafka](https://github.com/confluentinc/librdkafka/). 
  
 * [confluent-kafka configuration guide](https://docs.confluent.io/platform/current/clients/confluent-kafka-python/html/index.html#pythonclient-configuration)
 * [librdkafka configuration reference](https://github.com/confluentinc/librdkafka/blob/master/CONFIGURATION.md)

telicent-lib considers the configuration of librdkafka to be separate from the configuration of data or actions, and it
is preferable to leave the specifics of configuring librdkafka to those managing the environments in which actions are 
deployed.

To provide a configuration file for librdkafka to telicent-lib, two configuration variables must be set for telcient-lib.

 * `KAFKA_CONFIG_MODE`: toml
 * `KAFKA_CONFIG_FILE_PATH`: path to the configuration file

**WARNING**: it is strongly recommended that librdkafka properties `auto.offset.reset` and `enable.auto.commit` never be set 
through configuration. telicent-lib will manage these properties itself.

### Creating a configuration file

The configuration file must be a plaintext file. Its name and path can be any valid filepath, as long as the interpreter
has sufficient permissions to read the file.

The file is a series of key-value pairs, with the keys being valid librdkafka properties.

Example configuration file:
```toml
bootstrap.servers={my-kafka.network:9092}
group.id={my-group}
```

Example of a configuration file for an SSL enabled broker:
```toml
bootstrap.servers=my-kafka.network:9092
metadata.broker.list=my-kafka.network:9092
security.protocol=SSL
ssl.ca.location={PATH_TO_CA_BUNDLE}
ssl.certificate.location={PATH_TO_CLIENT_CERT}
ssl.key.location={PATH_TO_CLIENT_KEY}
ssl.key.password={pass1234}
ssl.endpoint.identification.algorithm=https
```

Example of a configuration file for a SASL/SCRAM enabled broker:
```toml
bootstrap.servers={my-kafka.network:9092}
security.protocol=SASL_SSL
sasl.mechanisms=SCRAM-SHA-256
sasl.username={username}
sasl.password={pass1234}
```

Values in {brackets} indicate variables that must be set for your environment.

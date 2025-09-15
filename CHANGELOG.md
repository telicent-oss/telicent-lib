# Changelog

## [5.0.2](https://github.com/telicent-oss/telicent-lib/compare/v5.0.1...v5.0.2) (2025-09-15)


### Miscellaneous

* set open telemetry to minimum version ([#75](https://github.com/telicent-oss/telicent-lib/issues/75)) ([5e50202](https://github.com/telicent-oss/telicent-lib/commit/5e50202abdb59c1eae2562df3a2a915eb64b30b8))

## [5.0.1](https://github.com/telicent-oss/telicent-lib/compare/v5.0.0...v5.0.1) (2025-08-21)


### Bug Fixes

* broker correctly displayed in str output of kafkaSink ([#73](https://github.com/telicent-oss/telicent-lib/issues/73)) ([720adca](https://github.com/telicent-oss/telicent-lib/commit/720adcad8656cf9471335e503a266ee0dc7aa56b))

## [5.0.0](https://github.com/telicent-oss/telicent-lib/compare/v4.0.0...v5.0.0) (2025-08-04)


### ⚠ BREAKING CHANGES

* replace data catalog with distribution id ([#71](https://github.com/telicent-oss/telicent-lib/issues/71))

### Features

* replace data catalog with distribution id ([#71](https://github.com/telicent-oss/telicent-lib/issues/71)) ([1936654](https://github.com/telicent-oss/telicent-lib/commit/19366547693bbf2528c84a8b6782d9570e218bf9))

## [4.0.0](https://github.com/telicent-oss/telicent-lib/compare/v3.1.2...v4.0.0) (2025-06-30)


### ⚠ BREAKING CHANGES

* **colored:** upgraded colored to latest version ([#68](https://github.com/telicent-oss/telicent-lib/issues/68))
* target and source now optional parameters for actions ([#69](https://github.com/telicent-oss/telicent-lib/issues/69))

### Features

* dead letter queue support ([#66](https://github.com/telicent-oss/telicent-lib/issues/66)) ([51f3ca2](https://github.com/telicent-oss/telicent-lib/commit/51f3ca2b574c5ea74ad4cc888a88a5b43377c61e))
* deprecated RdfSerializer and RdfDeserializer ([#63](https://github.com/telicent-oss/telicent-lib/issues/63)) ([ea8b741](https://github.com/telicent-oss/telicent-lib/commit/ea8b7417489705789a79b532059dad88b9fc85a6))
* target and source now optional parameters for actions ([#69](https://github.com/telicent-oss/telicent-lib/issues/69)) ([134539e](https://github.com/telicent-oss/telicent-lib/commit/134539ef7ac934fd72c47c03d7337d609cac562d))


### Bug Fixes

* disabled telemetry bug ([#67](https://github.com/telicent-oss/telicent-lib/issues/67)) ([4315482](https://github.com/telicent-oss/telicent-lib/commit/431548229c6caf937d9dc63c56210b3c17caf02a))


### Miscellaneous

* **colored:** upgraded colored to latest version ([#68](https://github.com/telicent-oss/telicent-lib/issues/68)) ([6fc8b09](https://github.com/telicent-oss/telicent-lib/commit/6fc8b0971d47871f29a1087e830bb9a58192119f))

## [3.1.2](https://github.com/telicent-oss/telicent-lib/compare/v3.1.1...v3.1.2) (2025-04-22)


### Miscellaneous

* **deps:** updated to confluent-kafka 2.8.2 to provide 3.13 support ([#59](https://github.com/telicent-oss/telicent-lib/issues/59)) ([899ca76](https://github.com/telicent-oss/telicent-lib/commit/899ca767504ffa5d7982d9bcfb7bc896ead45dc1))
* **deps:** removed decode token and its dependencies ([#61](https://github.com/telicent-oss/telicent-lib/pull/59)) ([fae3965](https://github.com/telicent-oss/telicent-lib/commit/fae396532d458cd341e0b018e4d43dc4f9060e79))

## [3.1.1](https://github.com/telicent-oss/telicent-lib/compare/v3.1.0...v3.1.1) (2024-10-28)


### Bug Fixes

* **kafka-source:** prevent clashing groupids when one not provided ([#55](https://github.com/telicent-oss/telicent-lib/issues/55)) ([675dbe7](https://github.com/telicent-oss/telicent-lib/commit/675dbe7d74bab3381afde629a7bd33670188f370))

## [3.1.0](https://github.com/telicent-oss/telicent-lib/compare/v3.0.1...v3.1.0) (2024-10-22)


### Features

* file based config for Kafka ([#53](https://github.com/telicent-oss/telicent-lib/issues/53)) ([1a26dc7](https://github.com/telicent-oss/telicent-lib/commit/1a26dc7df450a116035d2e04f26b6f6eb87f3901))

## [3.0.1](https://github.com/telicent-oss/telicent-lib/compare/v3.0.0...v3.0.1) (2024-09-25)


### Bug Fixes

* headers being set on data catalog messages ([#48](https://github.com/telicent-oss/telicent-lib/issues/48)) ([e4f2199](https://github.com/telicent-oss/telicent-lib/commit/e4f2199a9edcd556b9612b8422a87682656a9bab))

## [3.0.0](https://github.com/telicent-oss/telicent-lib/compare/v2.2.1...v3.0.0) (2024-09-19)


### ⚠ BREAKING CHANGES

* Dataset objects used to provide additional meta data about a dataset to adapters ([#46](https://github.com/telicent-oss/telicent-lib/issues/46))

### Features

* Dataset objects used to provide additional meta data about a dataset to adapters ([#46](https://github.com/telicent-oss/telicent-lib/issues/46)) ([d6817cd](https://github.com/telicent-oss/telicent-lib/commit/d6817cd791cfb02f9bd3458924b44c3c3113799d))

## [2.2.1](https://github.com/telicent-oss/telicent-lib/compare/v2.2.0...v2.2.1) (2024-09-04)


### Bug Fixes

* changed catalogue to catalog and updated dc default topic ([#44](https://github.com/telicent-oss/telicent-lib/issues/44)) ([c8825b3](https://github.com/telicent-oss/telicent-lib/commit/c8825b3d502a778f4d2729fc0e95e41b15ccd4e6))

## [2.2.0](https://github.com/telicent-oss/telicent-lib/compare/v2.1.0...v2.2.0) (2024-09-03)


### Features

* data source update notifications can be sent to a specified sink ([#41](https://github.com/telicent-oss/telicent-lib/issues/41)) ([d7987fb](https://github.com/telicent-oss/telicent-lib/commit/d7987fba9393bbc8ae6fe730a87cef5da9e24fb2))
* security labels from input record persisted to output record in mappers ([#42](https://github.com/telicent-oss/telicent-lib/issues/42)) ([98cc604](https://github.com/telicent-oss/telicent-lib/commit/98cc604613ddbeb115ed4ce8b5d4c8b800dd2c24))

## [2.1.0](https://github.com/telicent-oss/telicent-lib/compare/v2.0.7...v2.1.0) (2024-08-15)


### Features

* added source headers ([#36](https://github.com/telicent-oss/telicent-lib/issues/36)) ([1f0c60f](https://github.com/telicent-oss/telicent-lib/commit/1f0c60f5cb45848668ca1469d81f4390118a91d3))

## [2.0.7](https://github.com/telicent-oss/telicent-lib/compare/v2.0.6...v2.0.7) (2024-08-14)


### Bug Fixes

* allow full install on Python 3.9 ([#38](https://github.com/telicent-oss/telicent-lib/issues/38)) ([f176f56](https://github.com/telicent-oss/telicent-lib/commit/f176f56618ce0af7b7775a77b599885ba92801a8))

## [2.0.6](https://github.com/telicent-oss/telicent-lib/compare/v2.0.5...v2.0.6) (2024-08-14)


### Miscellaneous

* limited support for python 3.9 ([#35](https://github.com/telicent-oss/telicent-lib/issues/35)) ([0868e99](https://github.com/telicent-oss/telicent-lib/commit/0868e99efacf41452fc6b0e7874a7b4c91580299))

## [2.0.5](https://github.com/telicent-oss/telicent-lib/compare/v2.0.4...v2.0.5) (2024-07-09)


### Bug Fixes

* handled topic not found exception ([#29](https://github.com/telicent-oss/telicent-lib/issues/29)) ([55b7a84](https://github.com/telicent-oss/telicent-lib/commit/55b7a848785fa4a24cd420ada397d55fd860a317))


### Miscellaneous

* pr scanning and updated ruff checks to py310 ([#28](https://github.com/telicent-oss/telicent-lib/issues/28)) ([0c88188](https://github.com/telicent-oss/telicent-lib/commit/0c88188a6593309a9ddb627e3cab4b943efa950f))
* update requests dependency add urllib3 to override older version provided by types-requests ([#34](https://github.com/telicent-oss/telicent-lib/issues/34)) ([c5bbb25](https://github.com/telicent-oss/telicent-lib/commit/c5bbb25f0948bdefbf38e94a8771341444e5743c))

## [2.0.4](https://github.com/telicent-oss/telicent-lib/compare/v2.0.3...v2.0.4) (2024-06-27)


### Miscellaneous

* add types-pytz and types-python-dateutil to pre-commit config ([6f91762](https://github.com/telicent-oss/telicent-lib/commit/6f9176294b0ba2a96bc6ca540d061d6904f914fd))
* Remove SecurityLabels funtionality - now a dependency ([#27](https://github.com/telicent-oss/telicent-lib/issues/27)) ([1924284](https://github.com/telicent-oss/telicent-lib/commit/19242843fa723b8262a0b7708a9a43ca4f5f5e63))
* update repository url in pyproject ([2b534c2](https://github.com/telicent-oss/telicent-lib/commit/2b534c200a75542ab0c6094dc4a02e40f515dc58))

## [2.0.3](https://github.com/telicent-oss/telicent-lib/compare/v2.0.2...v2.0.3) (2024-05-31)


### Miscellaneous

* changed to PEP 604 annotations ([#20](https://github.com/telicent-oss/telicent-lib/issues/20)) ([07c7afe](https://github.com/telicent-oss/telicent-lib/commit/07c7afe9d0f3cd6af3e18cde6751af6766772dd4))
* switched to builtin types ([#25](https://github.com/telicent-oss/telicent-lib/issues/25)) ([8858dbc](https://github.com/telicent-oss/telicent-lib/commit/8858dbca8b634e9bcbdb4f955cdc2c0ed7b5fa68))

## [2.0.2](https://github.com/telicent-oss/telicent-lib/compare/v2.0.1...v2.0.2) (2024-05-22)


### Bug Fixes

* moved jira-mapping-rules yaml ([#13](https://github.com/telicent-oss/telicent-lib/issues/13)) ([eb2c9d4](https://github.com/telicent-oss/telicent-lib/commit/eb2c9d42d4da521b0b72cbd5b78ccb77b24c485a))
* updated werkzeug to 3.0.3 ([#17](https://github.com/telicent-oss/telicent-lib/issues/17)) ([a281a2c](https://github.com/telicent-oss/telicent-lib/commit/a281a2c8ef1429f89254c966ee4e81321dc4dfcd))


### Miscellaneous

* **configurator:** used logger rather than print statements ([#10](https://github.com/telicent-oss/telicent-lib/issues/10)) ([b33eb8e](https://github.com/telicent-oss/telicent-lib/commit/b33eb8e24589f14e8750b8e380bcc08dc413586e))

## [2.0.1](https://github.com/telicent-oss/telicent-lib/compare/v2.0.0...v2.0.1) (2024-05-09)


### Bug Fixes

* projector and adapter reporter text, and decode token logger init ([#8](https://github.com/telicent-oss/telicent-lib/issues/8)) ([7f46762](https://github.com/telicent-oss/telicent-lib/commit/7f46762a57fb834f7366d2912af5c76d1fce27e0))

## 2.0.0 (2024-05-01)


### Features

* initial release ([c605ee7](https://github.com/telicent-oss/telicent-lib/commit/c605ee76a5dea86585112620b4350855d527ccc5))

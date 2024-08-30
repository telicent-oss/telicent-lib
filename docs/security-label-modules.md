# SecurityLabel Modules in telicent-lib 

telicent-lib can be leveraged alongside the [telicent-label-builder](https://github.com/telicent-oss/label-builder)  to 
facilitate the validation of data headers against a predefined model that encapsulates a security policy framework. 
While there is no fully operational implementation of policy-based access control (PBAC) at this time, the library allows 
for the validation of data headers against a chosen model to ensure that all required fields are populated and that the 
data types are correct.

A validated instance of a model can subsequently be converted into a security label, which can then be appended as a 
header to a record. If a `Security-Label` header is added to a record in an [action](actions.md), all subsequent 
mappers in a pipeline will automatically persist that header value, unless another action explicitly returns a record with a
`Security-Label` header.  This behaviour can be disabled by setting the [configuration](configuration.md) value of 
`DISABLE_PERSISTENT_HEADERS` to `"1"`.

It is important to note that telicent-lib does not enforce any of these operations; 
the implementation is entirely at the discretion of the user. The label-builder module provides users with the 
functionality to define and implement their own models. For guidance purposes, the label-builder currently includes 
an implementation of the TelicentModel. Label-builder is not a dependency of telicent-lib.

```python
data_header = {
    "apiVersion": "v1alpha",
    "specification": "v3.0",
    "identifier": "ItemA",
    "classification": "S",
    "permittedOrgs": [
        "ABC",
        "DEF",
        "HIJ"
    ],
    "permittedNats": [
        "GBR",
        "FRA",
        "IRL"
    ],
    "orGroups": [
        "Apple",
        "SOMETHING"
    ],
    "andGroups": [
        "doctor",
        "admin"
    ],
    "createdDateTime": datetime(2023, 2, 2, 23, 11, 11, 4892).astimezone(timezone.utc),
    "originator": "TestOriginator",
    "custodian": "TestCustodian",
    "policyRef": "TestPolicyRef",
    "dataSet": ["ds1", "ds2"],
    "authRef": ["ref1", "ref2"],
    "dispositionDate": datetime(2023,1,1,23,11,11).astimezone(timezone.utc),
    "dispositionDate": datetime(2023, 1, 1, 23, 11, 11).astimezone(timezone.utc),
    "dispositionProcess": "disp-process-1",
    "dissemination": ["news", "articles"]
}

data_header_model = TelicentModel(**data_header)
security_labels = data_header_model.build_security_labels()
headers =  [('policyInformation', {'DH': data_header_model.model_dump()}),
            ('Security-Label', security_labels)]
record = RecordUtils.add_headers(record, headers)
```



Please refer to the documentation of [telicent-label-builder](https://github.com/telicent-oss/label-builder) 
for further information and full use case examples.

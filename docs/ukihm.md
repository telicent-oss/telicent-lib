### Documentation for EDH Header Model Implementation

#### Overview

The EDH Header Model, as part of a data processing pipeline, facilitates the creation and management of security labels 
based on the EDH (Enterprise Data Handling) standard. The implementation involves creating a model that dynamically builds 
security labels, which can then be attached to data records. This process ensures that each record complies with specified 
security and access policies.

#### Classes 

1. **EDHMixin Class**: A base model providing the `build_security_labels` method.
   - `build_security_labels(self)`: Utilizes `SecurityLabelBuilder` and `EDHSecurityLabelsV2` to construct security labels based on class attributes.
    
   The mixin class is designed to enhance the extensibility and versatility of a model. It provides a flexible means to 
   augment the functionality of the primary model, as well as to offer compatibility and feature support for additional models. 
   This approach ensures modular and adaptable design, allowing for the seamless integration of extended capabilities or the incorporation of functionalities from other models.


2. **EDHModel Class (inherits EDHMixin)**: Represents the EDH policy with various attributes.
   - Attributes include `identifier`, `classification`, `permittedOrgs`, `permittedNats`, `orGroups`, `andGroups`, and optional fields like `createDate`, `originator`, etc.
   - `build_security_labels(self)`: Overrides the base method to build security labels specific to this model.


#### Example: Using EDH Header Model with Adapter

```python
import requests
from telicent_lib import Adapter
from telicent_lib.access import EDHModel
from telicent_lib.records import Record, RecordUtils
from telicent_lib.sinks import KafkaSink

def records_from_file() -> list[str]:
    url = "https://test.com/wordlist.10000"
    resp = requests.get(url)
    resp.raise_for_status()
    lines = resp.text.rstrip().split("\n")
    return lines

# Create a sink and an adapter
sink = KafkaSink(topic="adapter-demo", broker="localhost:9092")
adapter = Adapter(target=sink, name="Demo Adapter with EDH Policy", source_name="Word List MIT")

edh_policy = {
    # EDH policy details...
}

security_labels = EDHModel(**edh_policy).build_security_labels()

try:
    adapter.run()
    adapter.expect_records(10000)

    for i, line in enumerate(records_from_file(), start=1):
        record = Record(headers=None, key=i, value=line, raw=None)
        record_with_headers = RecordUtils.add_headers(record, [('policyInformation', {'EDH': edh_policy})])
        record_with_label_and_policy = RecordUtils.add_headers(record_with_headers,
                                                               [('Security-Label', security_labels)])
        adapter.send(record_with_label_and_policy)

    adapter.finished()
except KeyboardInterrupt:
    adapter.aborted()

if __name__ == '__main__':
    adapter.run()
```

#### Usage with Automatic Adapters

Automatic adapters are engineered to seamlessly administer an EDH Policy across all data records they process. 
Upon instantiation, these adapters apply a predefined policy, specified in the class constructor, uniformly to every record. 
This ensures consistent policy enforcement and simplifies the management of data security.

```python
   import json
   from pathlib import Path
   from typing import Iterable
   from telicent_lib import AutomaticAdapter, Record
   from telicent_lib.sinks import KafkaSink, Serializers
   
   policy = {
       # EDH policy details...
   }
   
   def read_json_objects(file_path):
       path = Path(file_path)
       with path.open('r', encoding='utf-8') as file:
           data = json.load(file)
           if not isinstance(data, list):
               raise ValueError("JSON file does not contain an array of objects")
           yield from data
   
   def generate_records() -> Iterable[Record]:
       for i, record in enumerate(read_json_objects("./demo_data.json")):
           yield Record(headers=None, key=i, value=record, raw=None)
   
   sink = KafkaSink(topic="output-automatic-adapter-demo", broker="localhost:9092", value_serializer=Serializers.to_json)
   adapter = AutomaticAdapter(target=sink, adapter_function=generate_records,
                              name="Example Automatic Adapter with security policy", source_name="Some file",
                              policy_information=policy)
   
   if __name__ == '__main__':
       adapter.run()
```
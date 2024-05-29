from telicent_lib import utils, records
from typing import Union

def poc(cool: Union[str | int]):
    pass

utils.validate_callable_protocol(poc, records.RecordMapper)
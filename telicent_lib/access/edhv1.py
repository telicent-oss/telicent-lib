from enum import Enum

from telicent_lib.access import security_labels as security

__license__ = """
Copyright (c) Telicent Ltd.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""


class EDHSecurityLabelsV1(Enum):
    """
    Representation of simplified EDH standard suitable for SecurityLabelbuilder,
    simplied for the CORE environment
    """
    PERMITTED_ORGANISATIONS = security.MultiValueLabel("deployed_organisation", "array")
    PERMITTED_NATIONALITIES = security.MultiValueLabel("nationality", "array")
    CLASSIFICATION = security.SingleValueLabel("clearance", "str")

from enum import Enum

from telicent_lib.access.security_labels import MultiValueLabel, SingleValueLabel

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


class AndGroups(MultiValueLabel):

    # Something in here needed to get valid group
    def construct(self, *values):
        # assume value is urn
        condition = "&".join(map(self.create_label, values))
        return condition

    def create_label(self, value: str):
        return value + ":and"


class OrGroups(MultiValueLabel):

    # Something in here needed to get valid group
    def construct(self, *values):
        # assume value is urn
        condition = "|".join(map(self.create_label, values))
        return "(" + condition + ")"

    def create_label(self, value: str):
        return value + ":or"


class EDHSecurityLabelsV2(Enum):
    """
    Representation of EDH standard suitable for SecurityLabelbuilder
    """
    PERMITTED_ORGANISATIONS = MultiValueLabel(
        "permitted_organisations", "array"
    )
    PERMITTED_NATIONALITIES = MultiValueLabel(
        "permitted_nationalities", "array"
    )
    CLASSIFICATION = SingleValueLabel("classification", "str")
    AND_GROUPS = AndGroups("and_groups", "groups")
    OR_GROUPS = OrGroups("or_groups", "groups")

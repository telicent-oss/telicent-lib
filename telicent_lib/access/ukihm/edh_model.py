from datetime import datetime, timezone
from typing import List

from pydantic import AwareDatetime, BaseModel, PlainSerializer
from typing_extensions import Annotated

from telicent_lib.access.edhv2 import EDHSecurityLabelsV2
from telicent_lib.access.security_labels import SecurityLabelBuilder

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


DEFAULT_OPTIONAL_DT = datetime(2023, 12, 14, 0, 0, 0, tzinfo=timezone.utc)
SerialisableDt = Annotated[AwareDatetime, PlainSerializer(lambda x: x.isoformat(), return_type=str, when_used="always")]


class EDHMixin(BaseModel):

    def build_security_labels(self):
        builder = SecurityLabelBuilder()

        builder.add(EDHSecurityLabelsV2.CLASSIFICATION.value, self.classification)
        builder.add_multiple(EDHSecurityLabelsV2.PERMITTED_ORGANISATIONS.value, *self.permittedOrgs)
        builder.add_multiple(EDHSecurityLabelsV2.PERMITTED_NATIONALITIES.value, *self.permittedNats)
        builder.add_multiple(EDHSecurityLabelsV2.AND_GROUPS.value, *self.andGroups)
        builder.add_multiple(EDHSecurityLabelsV2.OR_GROUPS.value, *self.orGroups)

        return builder.build()


class EDHModel(EDHMixin):
    apiVersion: str | None = "v1alpha"
    specification: str | None = "UKIC v3.0"
    identifier: str
    classification: str
    permittedOrgs: List[str]
    permittedNats: List[str]
    orGroups: List[str]
    andGroups: List[str]

    createdDateTime: SerialisableDt | None = DEFAULT_OPTIONAL_DT
    originator: str | None = None
    custodian: str | None = None
    policyRef: str | None = None
    dataSet: str | None
    authRef: str | None
    dispositionDate: SerialisableDt | None = DEFAULT_OPTIONAL_DT
    dispositionProcess: str | None = None
    dissemination: str | None

    def build_security_labels(self):
        return super().build_security_labels()

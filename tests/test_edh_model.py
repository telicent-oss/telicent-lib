import unittest
from datetime import datetime

import pytz

from telicent_lib.access import EDHModel


class EDHModelTestCase(unittest.TestCase):
    def test_edh_model_build_labels(self):
        expected_label = "(classification=S&" \
                          "(permitted_organisations=ABC|permitted_organisations=DEF|permitted_organisations=HIJ)&" \
                          "(permitted_nationalities=GBR|permitted_nationalities=FRA|permitted_nationalities=IRL)&" \
                          "doctor:and&admin:and&(Apple:or|SOMETHING:or))"

        data = {
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

            "originator": "TestOriginator",
            "custodian": "TestCustodian",
            "policyRef": "TestPolicyRef",
            "dataSet": ["ds1", "ds2"],
            "authRef": ["ref1", "ref2"],
            "dispositionDate": datetime(2023, 1, 1, 23, 59, 59, 3426).astimezone(tz=pytz.timezone('US/Eastern')),
            "dispositionProcess": "disp-process-1",
            "dissemination": ["news", "articles"]
        }
        under_test = EDHModel(**data)
        security_labels = under_test.build_security_labels()
        self.assertEqual(security_labels, expected_label)
        self.assertEqual(under_test.createdDateTime.isoformat(), '2023-12-14T00:00:00+00:00')
        self.assertEqual(under_test.dispositionDate.isoformat(), '2023-01-01T18:59:59.003426-05:00')

import unittest

from telicent_lib.access import EDHSecurityLabelsV2, SecurityLabelBuilder
from telicent_lib.access.security_labels import Label


class SecurityLabelBuilderTestCase(unittest.TestCase):
    def test_simple_and_group_label_access(self):
        pn = EDHSecurityLabelsV2.AND_GROUPS.value
        test_group_1 = "urn:telicent:groups:role:doctor"
        test_group_2 = "urn:telicent:groups:role:admin"

        basic_label = pn.create_label(test_group_1)

        self.assertEqual(basic_label, "urn:telicent:groups:role:doctor:and")

        single_group = pn.construct(test_group_1)

        self.assertEqual(single_group, "urn:telicent:groups:role:doctor:and")

        multi_group = pn.construct(test_group_1, test_group_2)

        self.assertEqual(
            multi_group,
            "urn:telicent:groups:role:doctor:and&urn:telicent:groups:role:admin:and",
        )

    def test_simple_or_group_label_access(self):
        pn = EDHSecurityLabelsV2.OR_GROUPS.value
        test_group_1 = "urn:telicent:groups:role:doctor"
        test_group_2 = "urn:telicent:groups:role:admin"

        basic_label = pn.create_label(test_group_1)

        self.assertEqual(basic_label, "urn:telicent:groups:role:doctor:or")

        single_group = pn.construct(test_group_1)

        self.assertEqual(single_group, "(urn:telicent:groups:role:doctor:or)")

        multi_group = pn.construct(test_group_1, test_group_2)

        self.assertEqual(
            multi_group,
            "(urn:telicent:groups:role:doctor:or|urn:telicent:groups:role:admin:or)",
        )

    def test_simple_single_label_access(self):
        pn = EDHSecurityLabelsV2.CLASSIFICATION.value
        test_classifcation = "S"

        basic_label = pn.create_label(test_classifcation)

        self.assertEqual(basic_label, "classification=S")

        multi_label = pn.construct(test_classifcation)

        self.assertEqual(multi_label, "classification=S")

    def test_simple_multi_label_access(self):
        pn = EDHSecurityLabelsV2.PERMITTED_NATIONALITIES.value
        test_nationality_1 = "GBR"
        test_nationality_2 = "NOR"
        basic_label = pn.create_label(test_nationality_1)

        self.assertEqual(basic_label, "permitted_nationalities=GBR")

        multi_label = pn.construct(test_nationality_1, test_nationality_2)

        self.assertEqual(
            multi_label, "(permitted_nationalities=GBR|permitted_nationalities=NOR)"
        )

    def test_security_label_builder(self):
        test_org_1 = "telicent"
        test_org_2 = "nhs"
        test_classification = "S"
        test_classification_1 = "O"
        slb1 = (
            SecurityLabelBuilder()
            .add_multiple(
                EDHSecurityLabelsV2.PERMITTED_ORGANISATIONS.value,
                test_org_1,
                test_org_2,
            )
            .add(EDHSecurityLabelsV2.CLASSIFICATION.value, test_classification)
            .build()
        )
        self.assertEqual(
            slb1,
            "((permitted_organisations=telicent|permitted_organisations=nhs)&classification=S)",
        )

        slb2 = (
            SecurityLabelBuilder()
            .add(EDHSecurityLabelsV2.PERMITTED_ORGANISATIONS.value, test_org_1)
            .add(EDHSecurityLabelsV2.CLASSIFICATION.value, test_classification_1)
            .build()
        )

        self.assertEqual(
            slb2,
            "((permitted_organisations=telicent)&classification=O)",
        )

        slb3 = (
            SecurityLabelBuilder()
            .add_or_expression(slb1)
            .add_or_expression(slb2)
            .build()
        )

        self.assertEqual(
            slb3,
            "((permitted_organisations=telicent|permitted_organisations=nhs)&classification=S)|"
            "((permitted_organisations=telicent)&classification=O)",
        )

        slb4 = (
            SecurityLabelBuilder()
            .add_multiple(
                EDHSecurityLabelsV2.PERMITTED_ORGANISATIONS.value,
                test_org_1,
                test_org_2,
            )
            .add(EDHSecurityLabelsV2.CLASSIFICATION.value, test_classification)
            .add_or_expression(slb2)
            .build()
        )

        self.assertEqual(
            slb4,
            "((permitted_organisations=telicent|permitted_organisations=nhs)&classification=S)|"
            "((permitted_organisations=telicent)&classification=O)",
        )

    def test_security_label_builder_complex(self):
        test_org_1 = "nhs"
        test_classification = "S"
        test_and_group = "urn:telicent:groups:department:vulnerable_care"
        test_or_group_1 = "urn:telicent:groups:role:admin"
        test_or_group_2 = "urn:telicent:groups:role:doctor"
        test_nationality_1 = "GBR"
        test_nationality_2 = "USA"

        slb = (
            SecurityLabelBuilder()
            .add(EDHSecurityLabelsV2.PERMITTED_ORGANISATIONS.value, test_org_1)
            .add(EDHSecurityLabelsV2.CLASSIFICATION.value, test_classification)
            .add_multiple(
                EDHSecurityLabelsV2.OR_GROUPS.value, test_or_group_1, test_or_group_2
            )
            .add(EDHSecurityLabelsV2.AND_GROUPS.value, test_and_group)
            .add_multiple(
                EDHSecurityLabelsV2.PERMITTED_NATIONALITIES.value,
                test_nationality_1,
                test_nationality_2,
            )
            .build()
        )
        self.assertEqual(
            slb,
            "((permitted_organisations=nhs)&classification=S&(urn:telicent:groups:role:admin:or|"
            "urn:telicent:groups:role:doctor:or)&urn:telicent:groups:department:vulnerable_care:and&"
            "(permitted_nationalities=GBR|permitted_nationalities=USA))",
        )

    def test_base_label_error(self):
        self.assertRaises(
            NotImplementedError,
            SecurityLabelBuilder().add,
            Label("test", "str"),
            "test",
        )

        self.assertRaises(
            NotImplementedError,
            SecurityLabelBuilder().add_multiple,
            Label("test", "str"),
            "test1",
            "test2",
        )

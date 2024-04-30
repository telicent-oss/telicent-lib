import unittest

from telicent_lib.access import EDHSecurityLabelsV1, SecurityLabelBuilder


class SecurityLabelBuilderTestCase(unittest.TestCase):
    def test_simple_single_label_access(self):
        pn = EDHSecurityLabelsV1.CLASSIFICATION.value
        test_classifcation = "S"

        basic_label = pn.create_label(test_classifcation)

        self.assertEqual(basic_label, "clearance=S")

        multi_label = pn.construct(test_classifcation)

        self.assertEqual(multi_label, "clearance=S")

    def test_simple_multi_label_access(self):
        pn = EDHSecurityLabelsV1.PERMITTED_NATIONALITIES.value
        test_nationality_1 = "GBR"
        test_nationality_2 = "NOR"
        basic_label = pn.create_label(test_nationality_1)

        self.assertEqual(basic_label, "nationality=GBR")

        multi_label = pn.construct(test_nationality_1, test_nationality_2)

        self.assertEqual(multi_label, "(nationality=GBR|nationality=NOR)")

    def test_security_label_builder(self):
        test_org_1 = "telicent"
        test_org_2 = "nhs"
        test_classification = "S"
        test_classification_1 = "O"
        slb1 = (
            SecurityLabelBuilder()
            .add_multiple(
                EDHSecurityLabelsV1.PERMITTED_ORGANISATIONS.value,
                test_org_1,
                test_org_2,
            )
            .add(EDHSecurityLabelsV1.CLASSIFICATION.value, test_classification)
            .build()
        )
        self.assertEqual(
            slb1,
            "((deployed_organisation=telicent|deployed_organisation=nhs)&clearance=S)",
        )

        slb2 = (
            SecurityLabelBuilder()
            .add(EDHSecurityLabelsV1.PERMITTED_ORGANISATIONS.value, test_org_1)
            .add(EDHSecurityLabelsV1.CLASSIFICATION.value, test_classification_1)
            .build()
        )

        self.assertEqual(
            slb2,
            "((deployed_organisation=telicent)&clearance=O)",
        )

        slb3 = (
            SecurityLabelBuilder()
            .add_or_expression(slb1)
            .add_or_expression(slb2)
            .build()
        )

        self.assertEqual(
            slb3,
            "((deployed_organisation=telicent|deployed_organisation=nhs)&clearance=S)|"
            "((deployed_organisation=telicent)&clearance=O)",
        )

        slb4 = (
            SecurityLabelBuilder()
            .add_multiple(
                EDHSecurityLabelsV1.PERMITTED_ORGANISATIONS.value,
                test_org_1,
                test_org_2,
            )
            .add(EDHSecurityLabelsV1.CLASSIFICATION.value, test_classification)
            .add_or_expression(slb2)
            .build()
        )

        self.assertEqual(
            slb4,
            "((deployed_organisation=telicent|deployed_organisation=nhs)&clearance=S)|"
            "((deployed_organisation=telicent)&clearance=O)",
        )

    def test_security_label_builder_complex(self):
        test_org_1 = "nhs"
        test_classification = "S"

        test_nationality_1 = "GBR"
        test_nationality_2 = "USA"

        slb = (
            SecurityLabelBuilder()
            .add(EDHSecurityLabelsV1.PERMITTED_ORGANISATIONS.value, test_org_1)
            .add(EDHSecurityLabelsV1.CLASSIFICATION.value, test_classification)
            .add_multiple(
                EDHSecurityLabelsV1.PERMITTED_NATIONALITIES.value,
                test_nationality_1,
                test_nationality_2,
            )
            .build()
        )
        self.assertEqual(
            slb,
            "((deployed_organisation=nhs)&clearance=S&(nationality=GBR|nationality=USA))",
        )

import unittest

from sqlalchemy import CheckConstraint, Index

from app.db.base import Base
from app.models.enums import EntityType, MerchantStatus


class SchemaContractTest(unittest.TestCase):
    def test_merchant_status_enum_matches_canonical_plan(self) -> None:
        self.assertEqual(
            [status.value for status in MerchantStatus],
            ["PENDING_REVIEW", "ACTIVE", "REJECTED", "SUSPENDED", "DISABLED"],
        )

    def test_merchant_table_drops_embedded_approval_columns(self) -> None:
        merchant_columns = Base.metadata.tables["merchants"].c

        self.assertNotIn("approved_at", merchant_columns)
        self.assertNotIn("approved_by", merchant_columns)

    def test_onboarding_case_table_exists_with_expected_columns(self) -> None:
        onboarding_columns = Base.metadata.tables["merchant_onboarding_cases"].c

        expected_columns = {
            "id",
            "merchant_db_id",
            "status",
            "domain_or_app_name",
            "submitted_profile_json",
            "documents_json",
            "review_checks_json",
            "decision_note",
            "reviewed_by",
            "reviewed_at",
            "created_at",
            "updated_at",
        }

        self.assertTrue(expected_columns.issubset(set(onboarding_columns.keys())))

    def test_entity_type_enum_expands_for_new_audit_targets(self) -> None:
        values = {entity_type.value for entity_type in EntityType}

        self.assertIn("MERCHANT_CREDENTIAL", values)
        self.assertIn("ONBOARDING_CASE", values)

    def test_merchant_credentials_has_partial_unique_active_constraint(self) -> None:
        indexes = Base.metadata.tables["merchant_credentials"].indexes

        active_index = self._find_index(indexes, "ux_merchant_credentials_active_per_merchant")
        self.assertTrue(active_index.unique)
        self.assertEqual([column.name for column in active_index.columns], ["merchant_db_id"])
        self.assertEqual(
            str(active_index.dialect_options["postgresql"]["where"]),
            "status = 'ACTIVE'",
        )

    def test_refund_transactions_has_partial_unique_refunded_constraint(self) -> None:
        indexes = Base.metadata.tables["refund_transactions"].indexes

        refunded_index = self._find_index(indexes, "ux_refund_transactions_refunded_payment")
        self.assertTrue(refunded_index.unique)
        self.assertEqual(
            [column.name for column in refunded_index.columns],
            ["payment_transaction_id"],
        )
        self.assertEqual(
            str(refunded_index.dialect_options["postgresql"]["where"]),
            "status = 'REFUNDED'",
        )

    def test_numeric_safety_check_constraints_exist(self) -> None:
        payment_checks = self._check_constraint_names("payment_transactions")
        refund_checks = self._check_constraint_names("refund_transactions")
        webhook_checks = self._check_constraint_names("webhook_events")

        self.assertIn("ck_payment_transactions_ck_payment_transactions_amount_positive", payment_checks)
        self.assertIn("ck_refund_transactions_ck_refund_transactions_refund_amount_positive", refund_checks)
        self.assertIn("ck_webhook_events_ck_webhook_events_attempt_count_non_negative", webhook_checks)

    @staticmethod
    def _find_index(indexes: set[Index], name: str) -> Index:
        for index in indexes:
            if index.name == name:
                return index
        raise AssertionError(f"Index {name} not found")

    @staticmethod
    def _check_constraint_names(table_name: str) -> set[str]:
        constraints = Base.metadata.tables[table_name].constraints
        return {
            constraint.name
            for constraint in constraints
            if isinstance(constraint, CheckConstraint) and constraint.name is not None
        }


if __name__ == "__main__":
    unittest.main()


import unittest

from sqlalchemy import ForeignKeyConstraint, Index, UniqueConstraint


class MerchantPortalSchemaContractTest(unittest.TestCase):
    def test_merchant_user_enums_are_available(self) -> None:
        from app.models.enums import EntityType, MerchantUserRole, MerchantUserStatus

        self.assertEqual(MerchantUserRole.MERCHANT_ADMIN.value, "MERCHANT_ADMIN")
        self.assertEqual(MerchantUserRole.MERCHANT_VIEWER.value, "MERCHANT_VIEWER")
        self.assertEqual(MerchantUserStatus.ACTIVE.value, "ACTIVE")
        self.assertEqual(MerchantUserStatus.INACTIVE.value, "INACTIVE")
        self.assertEqual(EntityType.MERCHANT_USER.value, "MERCHANT_USER")

    def test_merchant_users_table_shape(self) -> None:
        from app.models.merchant_user import MerchantUser

        columns = MerchantUser.__table__.columns
        for column_name in {
            "id",
            "merchant_db_id",
            "email",
            "full_name",
            "role",
            "status",
            "password_hash",
            "last_login_at",
            "created_at",
            "updated_at",
        }:
            self.assertIn(column_name, columns)

        unique_constraints = [
            item for item in MerchantUser.__table__.constraints if isinstance(item, UniqueConstraint)
        ]
        self.assertTrue(
            any({"merchant_db_id", "email"} == {column.name for column in item.columns} for item in unique_constraints)
        )
        foreign_keys = [
            item for item in MerchantUser.__table__.constraints if isinstance(item, ForeignKeyConstraint)
        ]
        self.assertTrue(any("merchants.id" in str(element.target_fullname) for item in foreign_keys for element in item.elements))
        indexes = [item for item in MerchantUser.__table__.indexes if isinstance(item, Index)]
        self.assertTrue(any("merchant_db_id" in {column.name for column in item.columns} for item in indexes))


if __name__ == "__main__":
    unittest.main()

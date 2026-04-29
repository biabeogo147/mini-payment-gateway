import unittest

from sqlalchemy import Column, Integer, MetaData, String, Table, create_engine, text

from scripts import smoke_verify_db


class SmokeVerifyDbTest(unittest.TestCase):
    def test_cleanup_database_clears_latest_payment_before_deleting_payments(self) -> None:
        class FakeConnection:
            def __init__(self) -> None:
                self.statements: list[str] = []

            def execute(self, statement, params=None):
                self.statements.append(str(statement))

        connection = FakeConnection()

        smoke_verify_db.cleanup_database(connection)

        clear_latest_index = connection.statements.index(
            "UPDATE order_references SET latest_payment_transaction_id = NULL"
        )
        delete_payment_index = connection.statements.index("DELETE FROM payment_transactions")
        self.assertLess(clear_latest_index, delete_payment_index)

    def test_expect_statement_failure_keeps_outer_transaction_usable(self) -> None:
        engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
        metadata = MetaData()
        table = Table(
            "sample",
            metadata,
            Column("id", Integer, primary_key=True),
            Column("value", String(32), nullable=False, unique=True),
        )
        metadata.create_all(engine)

        with engine.begin() as connection:
            connection.execute(table.insert().values(value="first"))

            rejected = smoke_verify_db.expect_statement_failure(
                connection,
                "INSERT INTO sample (value) VALUES (:value)",
                {"value": "first"},
            )

            self.assertTrue(rejected)

            count = connection.execute(text("SELECT COUNT(*) FROM sample")).scalar_one()
            self.assertEqual(count, 1)

            connection.execute(table.insert().values(value="second"))
            final_count = connection.execute(text("SELECT COUNT(*) FROM sample")).scalar_one()
            self.assertEqual(final_count, 2)


if __name__ == "__main__":
    unittest.main()

import unittest

from sqlalchemy import Column, Integer, MetaData, String, Table, create_engine, text

from scripts import smoke_verify_db


class SmokeVerifyDbTest(unittest.TestCase):
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

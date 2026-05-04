import unittest
from uuid import uuid4


class AuditRepositoryTest(unittest.TestCase):
    def test_create_adds_audit_log_and_flushes(self) -> None:
        from app.models.enums import ActorType, EntityType
        from app.repositories.audit_repository import create

        db = _FakeDb()
        entity_id = uuid4()
        actor_id = uuid4()

        log = create(
            db=db,
            event_type="MERCHANT_CREATED",
            entity_type=EntityType.MERCHANT,
            entity_id=entity_id,
            actor_type=ActorType.OPS,
            actor_id=actor_id,
            before_state_json={"status": None},
            after_state_json={"status": "PENDING_REVIEW"},
            reason="Initial onboarding.",
        )

        self.assertIs(db.added[0], log)
        self.assertTrue(db.flushed)
        self.assertEqual(log.event_type, "MERCHANT_CREATED")
        self.assertEqual(log.entity_type, EntityType.MERCHANT)
        self.assertEqual(log.entity_id, entity_id)
        self.assertEqual(log.actor_type, ActorType.OPS)
        self.assertEqual(log.actor_id, actor_id)
        self.assertEqual(log.before_state_json, {"status": None})
        self.assertEqual(log.after_state_json, {"status": "PENDING_REVIEW"})
        self.assertEqual(log.reason, "Initial onboarding.")


class AuditServiceTest(unittest.TestCase):
    def test_record_event_supports_phase_07_entity_types(self) -> None:
        from app.models.enums import ActorType, EntityType
        from app.services.audit_service import record_event

        for entity_type in (
            EntityType.MERCHANT,
            EntityType.MERCHANT_CREDENTIAL,
            EntityType.ONBOARDING_CASE,
            EntityType.WEBHOOK_EVENT,
            EntityType.RECONCILIATION,
        ):
            with self.subTest(entity_type=entity_type.value):
                db = _FakeDb()
                log = record_event(
                    db=db,
                    event_type=f"{entity_type.value}_EVENT",
                    entity_type=entity_type,
                    entity_id=uuid4(),
                    actor_type=ActorType.OPS,
                    actor_id=None,
                    before_state={"status": "before"},
                    after_state={"status": "after"},
                    reason="Ops action.",
                )

                self.assertIs(db.added[0], log)
                self.assertEqual(log.entity_type, entity_type)
                self.assertEqual(log.actor_type, ActorType.OPS)
                self.assertEqual(log.reason, "Ops action.")

    def test_record_event_masks_plaintext_secrets_recursively(self) -> None:
        from app.models.enums import ActorType, EntityType
        from app.services.audit_service import record_event

        db = _FakeDb()

        log = record_event(
            db=db,
            event_type="CREDENTIAL_ROTATED",
            entity_type=EntityType.MERCHANT_CREDENTIAL,
            entity_id=uuid4(),
            actor_type=ActorType.OPS,
            before_state={
                "access_key": "ak_old",
                "secret_key": "old-secret",
                "nested": [{"secret_key_encrypted": "stored-secret"}],
            },
            after_state={
                "access_key": "ak_new",
                "secret_key": "new-secret",
                "secret_key_encrypted": "new-stored-secret",
            },
            reason="Rotate compromised key.",
        )

        self.assertEqual(log.before_state_json["secret_key"], "***")
        self.assertEqual(log.before_state_json["nested"][0]["secret_key_encrypted"], "***")
        self.assertEqual(log.after_state_json["secret_key"], "***")
        self.assertEqual(log.after_state_json["secret_key_encrypted"], "***")
        self.assertEqual(log.after_state_json["access_key"], "ak_new")


class AuditMetadataTest(unittest.TestCase):
    def test_internal_user_table_is_loaded_for_audit_foreign_key_sorting(self) -> None:
        from app.repositories import audit_repository  # noqa: F401
        from app.models.audit_log import AuditLog

        self.assertIn("internal_users", AuditLog.metadata.tables)


class _FakeDb:
    def __init__(self) -> None:
        self.added = []
        self.flushed = False

    def add(self, item) -> None:
        self.added.append(item)

    def flush(self) -> None:
        self.flushed = True


if __name__ == "__main__":
    unittest.main()

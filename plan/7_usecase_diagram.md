# Use Case Diagrams

These diagrams use PlantUML because Mermaid does not currently provide native
UML use case syntax. The Markdown fences are `plantuml`; render support depends
on the Markdown viewer or IDE plugin.

The same PlantUML source is also available in `usecase_diagram.puml`.

## Actor Overview

```plantuml
@startuml actor_overview
left to right direction
skinparam packageStyle rectangle

actor "Admin / Ops" as Admin
actor "Merchant Backend" as Merchant
actor "Customer / Payer" as Payer
actor "Bank / Provider / Simulator" as Provider

rectangle "Mini Payment Gateway" {
  usecase "Merchant operations" as UC_MerchantOps
  usecase "Payment API" as UC_PaymentApi
  usecase "Refund API" as UC_RefundApi
  usecase "Callback processing" as UC_CallbackProcessing
  usecase "Webhook delivery" as UC_WebhookDelivery
  usecase "Reconciliation and audit" as UC_ReconciliationAudit
}

Admin --> UC_MerchantOps
Admin --> UC_WebhookDelivery
Admin --> UC_ReconciliationAudit

Merchant --> UC_PaymentApi
Merchant --> UC_RefundApi
Merchant --> UC_WebhookDelivery

Payer --> UC_PaymentApi
Provider --> UC_CallbackProcessing
Provider --> UC_ReconciliationAudit

UC_CallbackProcessing ..> UC_WebhookDelivery : <<include>>
UC_CallbackProcessing ..> UC_ReconciliationAudit : <<include>>
@enduml
```

## Admin And Onboarding

```plantuml
@startuml admin_and_onboarding
left to right direction
skinparam packageStyle rectangle

actor "Admin / Ops" as Admin

rectangle "Mini Payment Gateway" {
  usecase "Create merchant record" as UC_CreateMerchant
  usecase "Create or update\nonboarding case" as UC_UpdateOnboarding
  usecase "Review onboarding case" as UC_ReviewOnboarding
  usecase "Approve or reject\nonboarding" as UC_DecideOnboarding
  usecase "Activate, suspend,\nor disable merchant" as UC_ManageStatus
  usecase "Issue or rotate\ncredential" as UC_RotateCredential
  usecase "Inspect payment, refund,\nwebhook, and reconciliation data" as UC_InspectOps
  usecase "Retry failed webhook\nmanually" as UC_ManualRetry
  usecase "Write audit log" as UC_WriteAudit
}

Admin --> UC_CreateMerchant
Admin --> UC_UpdateOnboarding
Admin --> UC_ReviewOnboarding
Admin --> UC_DecideOnboarding
Admin --> UC_ManageStatus
Admin --> UC_RotateCredential
Admin --> UC_InspectOps
Admin --> UC_ManualRetry

UC_DecideOnboarding ..> UC_WriteAudit : <<include>>
UC_ManageStatus ..> UC_WriteAudit : <<include>>
UC_RotateCredential ..> UC_WriteAudit : <<include>>
UC_ManualRetry ..> UC_WriteAudit : <<include>>
@enduml
```

## Merchant Payment And Refund API

```plantuml
@startuml merchant_payment_and_refund_api
left to right direction
skinparam packageStyle rectangle

actor "Merchant Backend" as Merchant
actor "Customer / Payer" as Payer

rectangle "Mini Payment Gateway" {
  usecase "Verify merchant auth\nand signature" as UC_Authenticate
  usecase "Create dynamic QR payment" as UC_CreatePayment
  usecase "Enforce payment\nidempotency" as UC_PaymentIdempotency
  usecase "Generate QR payload" as UC_GenerateQr
  usecase "Get payment status" as UC_QueryPayment

  usecase "Create full refund" as UC_CreateRefund
  usecase "Validate refund rules" as UC_ValidateRefund
  usecase "Enforce refund\nidempotency" as UC_RefundIdempotency
  usecase "Get refund status" as UC_QueryRefund
}

Merchant --> UC_CreatePayment
Merchant --> UC_QueryPayment
Merchant --> UC_CreateRefund
Merchant --> UC_QueryRefund
Payer --> UC_GenerateQr : scans QR

UC_CreatePayment ..> UC_Authenticate : <<include>>
UC_CreatePayment ..> UC_PaymentIdempotency : <<include>>
UC_CreatePayment ..> UC_GenerateQr : <<include>>
UC_QueryPayment ..> UC_Authenticate : <<include>>

UC_CreateRefund ..> UC_Authenticate : <<include>>
UC_CreateRefund ..> UC_ValidateRefund : <<include>>
UC_CreateRefund ..> UC_RefundIdempotency : <<include>>
UC_QueryRefund ..> UC_Authenticate : <<include>>
@enduml
```

## Callback, Webhook, And Reconciliation

```plantuml
@startuml callback_webhook_and_reconciliation
left to right direction
skinparam packageStyle rectangle

actor "Bank / Provider / Simulator" as Provider
actor "Merchant Backend" as Merchant
actor "Admin / Ops" as Admin

rectangle "Mini Payment Gateway" {
  usecase "Receive provider callback" as UC_ReceiveCallback
  usecase "Store callback evidence" as UC_LogCallback
  usecase "Update payment result" as UC_UpdatePayment
  usecase "Update refund result" as UC_UpdateRefund
  usecase "Expire pending payment" as UC_ExpirePayment
  usecase "Create webhook event" as UC_CreateWebhook
  usecase "Deliver webhook\nwith retry" as UC_DeliverWebhook
  usecase "Retry failed webhook\nmanually" as UC_ManualRetry
  usecase "Create reconciliation\nrecord" as UC_Reconcile
  usecase "Review reconciliation\nmismatch" as UC_ReviewReconciliation
  usecase "Write audit log" as UC_WriteAudit
}

Provider --> UC_ReceiveCallback
Provider --> UC_Reconcile
Merchant --> UC_DeliverWebhook : receives callback
Admin --> UC_ManualRetry
Admin --> UC_ReviewReconciliation

UC_ReceiveCallback ..> UC_LogCallback : <<include>>
UC_ReceiveCallback ..> UC_UpdatePayment : <<include>>
UC_ReceiveCallback ..> UC_UpdateRefund : <<include>>

UC_UpdatePayment ..> UC_CreateWebhook : <<include>>
UC_UpdateRefund ..> UC_CreateWebhook : <<include>>
UC_CreateWebhook ..> UC_DeliverWebhook : <<include>>
UC_ManualRetry ..> UC_DeliverWebhook : <<include>>

UC_ExpirePayment ..> UC_Reconcile : <<include>>
UC_ReceiveCallback ..> UC_Reconcile : <<include>>
UC_ReviewReconciliation ..> UC_WriteAudit : <<include>>
UC_ManualRetry ..> UC_WriteAudit : <<include>>
@enduml
```

## Core Use Cases

- Admin/Ops operates onboarding, merchant lifecycle, credential rotation, manual webhook retry, reconciliation review, and audit inspection.
- Merchant Backend creates payments, queries payment status, creates refunds, queries refund status, and receives webhook callbacks.
- Customer/Payer scans the dynamic QR and pays through a banking application.
- Bank/Provider/Simulator sends payment or refund results and provides external evidence for reconciliation.

## Out Of Scope

- Merchant self-service onboarding portal.
- Static QR per store.
- Partial refund and multi-refund settlement logic.
- Multi-provider routing.
- Chargeback, dispute, settlement engine, and accounting ledger.

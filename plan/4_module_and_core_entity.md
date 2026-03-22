# 1. Các module chính

## 1.1. Merchant Management

## Mục tiêu

Quản lý vòng đời merchant và toàn bộ cấu hình tích hợp.

## Chịu trách nhiệm

* lưu merchant profile
* quản lý merchant status
* cấp và rotate credentials
* lưu webhook_url
* lưu IP whitelist
* validate merchant có được gọi API hay không

## Trong scope MVP này

### Có

* merchant profile
* credentials
* webhook config
* IP whitelist
* active / suspended / rejected

### Không làm sâu

* self-service onboarding
* nhiều user/role cho từng merchant
* cấu hình nhiều store
* nhiều webhook endpoint

## Input chính

* thông tin merchant từ admin
* thao tác approve / suspend / update config
* yêu cầu lấy secret để verify signature

## Output chính

* merchant record
* merchant status
* credentials
* config tích hợp hợp lệ cho payment/refund/webhook

## Quan hệ với module khác

* Payment Service gọi để verify merchant active
* Refund Service gọi để verify merchant active
* Webhook Delivery gọi để lấy webhook_url
* Admin/Ops Portal gọi để quản trị merchant

## Chốt design thực dụng

* mỗi merchant có 1 webhook_url chính
* mỗi merchant có 1 bộ credentials active tại một thời điểm
* IP whitelist có thể optional ở bản đầu, nhưng entity/schema vẫn nên có

---

## 1.2. Payment Service

## Mục tiêu

Xử lý toàn bộ luồng tạo payment và chuyển payment sang trạng thái chờ thanh toán.

## Chịu trách nhiệm

* create payment
* validate request
* verify auth/signature
* check idempotency
* tạo payment transaction
* generate dynamic QR
* set expire_at
* trả response cho merchant
* cập nhật trạng thái khi có callback/result

## Trong scope MVP này

### Có

* create payment
* validate request
* idempotency theo `merchant_id + order_id`
* generate dynamic QR
* expire payment
* update status

### Không làm

* static QR per store
* multi-currency
* cancel payment chủ động
* nhiều payment method khác ngoài QR

## Input chính

* `merchant_id`
* `access_key`
* `signature`
* `order_id`
* `amount`
* `description`
* `expire_at` hoặc ttl

## Output chính

* `transaction_id`
* `qr_content`
* `status = PENDING`
* `expire_at`

## Quan hệ với module khác

* gọi Merchant Management để verify merchant/config
* gọi Transaction Management để ghi transaction/state
* gọi Integration Layer hoặc QR generator để sinh QR
* khi có status change thì tạo event cho Webhook Delivery

## Rule chốt

* chỉ dynamic QR
* một order chỉ có một payment active
* expired payment không revive
* create payment duplicate hợp lệ thì trả transaction cũ

---

## 1.3. Refund Service

## Mục tiêu

Xử lý hoàn tiền như một flow riêng, độc lập với payment create flow.

## Chịu trách nhiệm

* validate refund request
* check payment gốc
* refund idempotency
* tạo refund record
* gọi external refund processing
* update refund status
* phát sinh webhook refund event

## Trong scope MVP này

### Có

* validate refund
* full refund only
* refund idempotency
* refund tracking

### Không làm

* partial refund
* nhiều refund records cộng dồn cho 1 payment
* refund dispute/approval workflow phức tạp

## Input chính

* `merchant_id`
* `signature`
* `original_transaction_id` hoặc `order_id`
* `refund_id`
* `refund_amount`
* `reason`

## Output chính

* `refund_transaction_id`
* `refund_status`
* `original_transaction_id`
* `refund_amount`

## Quan hệ với module khác

* gọi Merchant Management để verify merchant
* gọi Transaction Management để đọc payment gốc / ghi refund state
* gọi Integration Layer để xử lý refund
* gọi Webhook Delivery khi refund đổi trạng thái

## Rule chốt

* chỉ payment SUCCESS mới refund được
* chỉ full refund
* refund window 7 ngày
* cùng `merchant_id + refund_id` chỉ tạo một refund logical

---

## 1.4. Transaction Management

## Mục tiêu

Là lớp trung tâm quản lý state, timeout, retry-support và đối soát ở mức record.

## Chịu trách nhiệm

* quản lý state machine payment
* quản lý state machine refund
* lưu lifecycle transaction
* expire payment theo thời gian
* hỗ trợ reconciliation
* giữ retry queue metadata
* hỗ trợ manual review cases

## Trong scope MVP này

### Có

* transaction state machine
* timeout handling
* reconciliation support cơ bản
* retry metadata cho webhook/refund review

### Không làm quá sâu

* settlement engine
* ledger/accounting engine
* workflow engine phức tạp

## Input chính

* create/update payment transaction
* create/update refund transaction
* callback result
* timeout job
* reconciliation result

## Output chính

* state transition hợp lệ
* record lifecycle nhất quán
* transaction/refund list cho admin/support

## Quan hệ với module khác

* Payment Service và Refund Service phụ thuộc vào module này
* Webhook Delivery đọc event source từ transaction/refund state change
* Admin/Ops Portal dùng để tra cứu
* Reconciliation process cập nhật vào đây

## Rule chốt

* không cho transition sai
* không cho update đè trạng thái cuối bừa bãi
* callback muộn sau expire phải qua review/reconciliation rule

---

## 1.5. Webhook Delivery

## Mục tiêu

Đảm bảo event thay đổi trạng thái được gửi sang merchant một cách có kiểm soát.

## Chịu trách nhiệm

* tạo webhook event payload
* sign payload
* gửi callback HTTP
* retry theo policy
* lưu log từng lần gửi
* đánh dấu delivered/failed

## Trong scope MVP này

### Có

* sign payload
* send callback
* retry 1m / 5m / 15m
* delivery log
* manual retry support

### Không làm

* nhiều endpoint cho cùng merchant
* event bus phức tạp
* replay portal cho merchant

## Input chính

* webhook event từ payment/refund status change
* merchant webhook_url
* signing secret/cấu hình ký

## Output chính

* webhook attempt result
* delivered / failed status
* delivery history

## Quan hệ với module khác

* lấy webhook config từ Merchant Management
* nhận source event từ Payment/Refund/Transaction Management
* Admin/Ops Portal đọc log và retry thủ công

## Rule chốt

* HTTP 2xx = success
* còn lại = fail attempt
* tối đa 4 attempts total
* sau đó chuyển failed queue

---

## 1.6. Admin/Ops Portal

## Mục tiêu

Cung cấp giao diện nội bộ tối thiểu để vận hành hệ thống.

## Chịu trách nhiệm

* duyệt merchant
* suspend/activate merchant
* xem payment/refund
* tra log webhook
* retry webhook thủ công
* xem các case cần review

## Trong scope MVP này

### Có

* merchant approval
* merchant status management
* transaction list/detail
* refund list/detail
* webhook failure list
* manual retry webhook
* reconciliation/manual review cơ bản

### Không làm

* dashboard analytics đẹp
* phân quyền phức tạp nhiều vai trò
* ticketing/support workflow lớn

## Input chính

* thao tác của admin/ops
* filter/search transaction/refund
* manual retry action

## Output chính

* màn hình vận hành
* audit trail
* kết quả manual action

## Quan hệ với module khác

* đọc/ghi Merchant Management
* đọc Payment/Refund/Transaction data
* gọi Webhook Delivery manual retry
* đọc ReconciliationRecord / AuditLog

## Rule chốt

* chỉ admin/ops nội bộ dùng
* retry webhook thủ công chỉ qua portal này hoặc internal endpoint tương đương

---

## 1.7. Integration Layer

## Mục tiêu

Đóng vai trò adapter giữa gateway và hệ thống bên ngoài.

## Chịu trách nhiệm

* nhận callback từ bank/provider/simulator
* chuẩn hóa dữ liệu callback về format nội bộ
* gọi provider để tạo/refund nếu cần
* hỗ trợ QR provider nếu không tự generate QR

## Trong scope MVP này

### Có

* bank/NAPAS connector hoặc mock connector
* callback receiver
* QR provider connector chỉ khi thật sự dùng third-party

### Không làm sâu

* nhiều provider cùng lúc
* routing engine chọn provider
* settlement integration

## Input chính

* callback request từ external side
* request từ Payment/Refund service sang external side

## Output chính

* normalized callback result
* external reference
* provider result mapping

## Quan hệ với module khác

* Payment Service dùng để generate/process payment qua external
* Refund Service dùng để process refund
* Transaction Management nhận normalized status result
* BankCallbackLog ghi từ đây

## Rule chốt

* nếu chưa tích hợp bank thật, layer này vẫn tồn tại dưới dạng mock/simulator adapter
* mapping external status -> internal enum phải tập trung tại đây, không rải ở nhiều nơi

---

# 2. Quan hệ giữa các module

Flow gọi nhau nên hiểu như sau:

## Payment create

Merchant Management
→ xác thực merchant

Payment Service
→ validate request, idempotency, tạo payment

Transaction Management
→ ghi PaymentTransaction

Integration Layer / QR generator
→ sinh QR

Webhook Delivery
→ chỉ tham gia khi payment đổi trạng thái sau đó

---

## Payment completion

Integration Layer
→ nhận callback/result

Transaction Management
→ update state

Webhook Delivery
→ gửi webhook cho merchant

Admin/Ops Portal
→ xem log nếu có lỗi

---

## Refund

Refund Service
→ validate refund request

Transaction Management
→ đọc payment gốc, tạo RefundTransaction

Integration Layer
→ xử lý refund

Transaction Management
→ update refund state

Webhook Delivery
→ gửi refund webhook

---

## Merchant onboarding

Admin/Ops Portal
→ tạo/duyệt merchant

Merchant Management
→ lưu config + cấp credentials

AuditLog
→ lưu toàn bộ thao tác

---

# 3. Core entities

Giờ mình chốt từng entity theo đúng scope.

---

## 3.1. Merchant

## Mục đích

Lưu hồ sơ merchant và trạng thái hoạt động.

## Field tối thiểu

* `id`
* `merchant_id`
* `merchant_name`
* `legal_name`
* `contact_name`
* `contact_email`
* `contact_phone`
* `webhook_url`
* `allowed_ip_list`
* `status`
  (`PENDING`, `ACTIVE`, `REJECTED`, `SUSPENDED`)
* `settlement_account_name`
* `settlement_account_number`
* `settlement_bank_code`
* `approved_at`
* `approved_by`
* `created_at`
* `updated_at`

## Ghi chú

* `merchant_id` là public identifier để gọi API
* `id` là internal DB id
* webhook_url nên đặt ở entity này cho MVP là đủ

---

## 3.2. MerchantCredential

## Mục đích

Lưu thông tin xác thực của merchant.

## Field tối thiểu

* `id`
* `merchant_id` hoặc FK đến Merchant
* `access_key`
* `secret_key_encrypted`
* `secret_key_last4`
* `status`
  (`ACTIVE`, `INACTIVE`, `ROTATED`)
* `created_at`
* `expired_at` nullable
* `rotated_at` nullable

## Ghi chú

* secret chỉ lưu encrypted
* cho MVP có thể chỉ có 1 credential active/merchant
* nếu rotate secret thì credential cũ chuyển inactive

---

## 3.3. OrderReference

## Mục đích

Map order phía merchant với payment transaction phía gateway.

## Có thật sự cần không?

**Trong MVP: optional nhưng nên có** nếu bạn muốn tách bạch.

Nếu muốn đơn giản hơn, có thể để `order_id` nằm luôn trong `PaymentTransaction`.
Nhưng nếu giữ entity này thì nó giúp:

* tra theo order rõ hơn
* quản lý “1 order chỉ 1 payment active”
* hỗ trợ tạo payment lại sau expired/failed

## Field tối thiểu

* `id`
* `merchant_id`
* `order_id`
* `latest_payment_transaction_id`
* `order_status_snapshot` nullable
* `created_at`
* `updated_at`

## Khuyến nghị

Cho team 3 người, **có thể chưa cần table riêng**.
Để `order_id` trực tiếp trong `PaymentTransaction` là đủ.

---

## 3.4. PaymentTransaction

## Mục đích

Entity trung tâm của flow payment.

## Field tối thiểu

* `id`
* `transaction_id`
* `merchant_id`
* `order_id`
* `amount`
* `currency`
  có thể default `VND`
* `description`
* `status`
  (`PENDING`, `SUCCESS`, `FAILED`, `EXPIRED`)
* `qr_content`
* `qr_image_url` hoặc `qr_image_base64` nullable
* `external_reference` nullable
* `idempotency_key` nullable
* `expire_at`
* `paid_at` nullable
* `failed_reason_code` nullable
* `failed_reason_message` nullable
* `created_at`
* `updated_at`

## Constraint quan trọng

* unique logical cho active payment theo `merchant_id + order_id + active_state`
* hoặc enforce bằng code/service rule nếu DB khó làm partial unique

## Ghi chú

Đây là entity phải được thiết kế rõ nhất.

---

## 3.5. RefundTransaction

## Mục đích

Entity trung tâm của flow refund.

## Field tối thiểu

* `id`
* `refund_transaction_id`
* `merchant_id`
* `payment_transaction_id`
* `refund_id`
* `refund_amount`
* `reason`
* `status`
  (`REFUND_PENDING`, `REFUNDED`, `REFUND_FAILED`)
* `external_reference` nullable
* `idempotency_key` nullable
* `processed_at` nullable
* `failed_reason_code` nullable
* `failed_reason_message` nullable
* `created_at`
* `updated_at`

## Constraint quan trọng

* unique theo `merchant_id + refund_id`

## Ghi chú

Do MVP chỉ full refund:

* `refund_amount` nên bằng `payment.amount`
* có thể validate ngay ở service layer

---

## 3.6. WebhookEvent

## Mục đích

Biểu diễn một business event cần gửi sang merchant.

## Field tối thiểu

* `id`
* `event_id`
* `merchant_id`
* `event_type`
  ví dụ:

  * `PAYMENT_SUCCESS`
  * `PAYMENT_FAILED`
  * `PAYMENT_EXPIRED`
  * `REFUND_REFUNDED`
  * `REFUND_FAILED`
* `entity_type`
  (`PAYMENT`, `REFUND`)
* `entity_id`
* `payload_json`
* `signature`
* `status`
  (`PENDING`, `DELIVERED`, `FAILED`)
* `next_retry_at` nullable
* `attempt_count`
* `last_attempt_at` nullable
* `created_at`
* `updated_at`

## Ghi chú

* payload_json nên lưu snapshot lúc phát event
* signature có thể tính khi send hoặc lưu sẵn

---

## 3.7. WebhookDeliveryAttempt

## Mục đích

Lưu từng lần gửi webhook.

## Field tối thiểu

* `id`
* `webhook_event_id`
* `attempt_no`
* `request_url`
* `request_headers_json`
* `request_body_json`
* `response_status_code` nullable
* `response_body_snippet` nullable
* `error_message` nullable
* `started_at`
* `finished_at`
* `result`
  (`SUCCESS`, `FAILED`, `TIMEOUT`, `NETWORK_ERROR`)

## Ghi chú

* giúp ops debug vì sao webhook fail
* không nên log full dữ liệu nhạy cảm quá mức

---

## 3.8. BankCallbackLog

## Mục đích

Lưu raw/normalized callback từ external side.

## Field tối thiểu

* `id`
* `source_type`
  (`BANK`, `NAPAS`, `SIMULATOR`, `QR_PROVIDER`)
* `external_reference`
* `transaction_reference` nullable
* `callback_type`
  (`PAYMENT_RESULT`, `REFUND_RESULT`)
* `raw_payload_json`
* `normalized_status`
* `received_at`
* `processed_at` nullable
* `processing_result`
  (`PROCESSED`, `IGNORED`, `FAILED`, `PENDING_REVIEW`)
* `error_message` nullable

## Ghi chú

* rất quan trọng cho reconciliation/manual review
* callback mapping nên trace được từ đây sang transaction/refund

---

## 3.9. ReconciliationRecord

## Mục đích

Lưu kết quả đối soát giữa dữ liệu nội bộ và external data.

## Field tối thiểu

* `id`
* `entity_type`
  (`PAYMENT`, `REFUND`)
* `entity_id`
* `internal_status`
* `external_status`
* `internal_amount`
* `external_amount`
* `match_result`
  (`MATCHED`, `MISMATCHED`, `PENDING_REVIEW`, `RESOLVED`)
* `mismatch_reason_code`
* `mismatch_reason_message`
* `reviewed_by` nullable
* `review_note` nullable
* `created_at`
* `updated_at`

## Ghi chú

* chỉ phục vụ support consistency
* không mở rộng thành settlement table

---

## 3.10. AuditLog

## Mục đích

Lưu mọi thao tác quản trị và can thiệp thủ công.

## Field tối thiểu

* `id`
* `event_type`
* `entity_type`
* `entity_id`
* `actor_type`
  (`SYSTEM`, `ADMIN`, `OPS`)
* `actor_id`
* `before_state_json` nullable
* `after_state_json` nullable
* `reason` nullable
* `created_at`

## Ví dụ event_type

* `MERCHANT_APPROVED`
* `MERCHANT_SUSPENDED`
* `WEBHOOK_RETRIED_MANUALLY`
* `MERCHANT_WEBHOOK_UPDATED`
* `CREDENTIAL_ROTATED`
* `RECONCILIATION_MARKED_RESOLVED`

---

# 5. Mapping module ↔ entity

## Merchant Management

* Merchant
* MerchantCredential
* AuditLog

## Payment Service

* PaymentTransaction
* Merchant
* MerchantCredential
* BankCallbackLog

## Refund Service

* RefundTransaction
* PaymentTransaction
* Merchant
* BankCallbackLog

## Transaction Management

* PaymentTransaction
* RefundTransaction
* ReconciliationRecord
* AuditLog

## Webhook Delivery

* WebhookEvent
* WebhookDeliveryAttempt

## Admin/Ops Portal

* Merchant
* PaymentTransaction
* RefundTransaction
* WebhookEvent
* WebhookDeliveryAttempt
* ReconciliationRecord
* AuditLog

## Integration Layer

* BankCallbackLog
* PaymentTransaction
* RefundTransaction
# 1. Định nghĩa bài toán ở mức ngắn gọn

## Tên bài toán

**Simple Payment Gateway for internal demo / small-scale merchant integration**

## Mục tiêu

Xây một hệ thống gateway thanh toán QR đơn giản, cho phép:

* admin tạo và duyệt merchant
* merchant gọi API để tạo payment QR
* customer thanh toán bằng app ngân hàng
* gateway theo dõi trạng thái giao dịch
* gateway bắn webhook về merchant
* merchant có thể refund
* admin/ops có thể tra cứu và hỗ trợ thủ công

## Mục tiêu thật sự của phiên bản này

Không phải để vận hành production cấp ngân hàng.

Mà là để chứng minh được 5 thứ:

1. **merchant có thể tích hợp được**
2. **payment flow end-to-end chạy được**
3. **transaction có lifecycle rõ ràng**
4. **webhook + retry + idempotency có tồn tại**
5. **refund có flow riêng và tracking riêng**

---

# 2. Xác định user/actor thật rõ

## 2.1. Admin/Ops

Là người nội bộ của hệ thống gateway.

Họ có quyền:

* tạo merchant
* duyệt merchant
* khóa/mở merchant
* xem payment/refund
* retry webhook thủ công

## 2.2. Merchant backend

Là hệ thống của bên bán, gọi API sang gateway.

Merchant có thể:

* tạo payment
* xem payment status
* tạo refund
* xem refund status
* nhận webhook

Merchant **không phải user click UI** trong MVP này.
Nó chủ yếu là **client system/API consumer**.

## 2.3. Customer / payer

Là người dùng cuối quét QR bằng app ngân hàng.

Trong MVP này, customer không cần portal riêng.
Chỉ cần có:

* màn hình/payment page hiển thị QR
* hoặc API trả QR để merchant tự hiển thị

## 2.4. Bank / external payment rail

**bank/NAPAS là external simulator hoặc mocked integration**.

---

# 3. Làm rõ Product Scope hiện tại thành MVP Scope

## 3.1. Merchant Side Scope

### 1) Merchant onboarding thủ công qua admin

**Trong MVP này nghĩa là:**

* admin nhập thông tin merchant bằng tay
* admin duyệt merchant bằng tay
* chưa có merchant self-register
* chưa có workflow upload giấy tờ tự động
* chưa có eKYC/doanh nghiệp verification thật

**Thông tin merchant tối thiểu cần có:**

* merchant_name
* merchant_code / merchant_id
* contact_email
* callback/webhook_url
* status
* settlement_account_info (lưu mô phỏng hoặc basic info)
* allowed_ip_list
* created_at / approved_at

### 2) Cấp merchant_id, access_key, secret_key

**Trong MVP này nghĩa là:**

* sau khi merchant được approve, hệ thống sinh credential
* merchant dùng credential để gọi API
* secret_key chỉ hiển thị 1 lần hoặc lưu tạm cách đơn giản trong demo

**Làm tối giản nhưng vẫn đúng ý nghĩa:**

* auth bằng `merchant_id + access_key + signature`
* signature kiểu HMAC-SHA256 là đủ cho MVP

### 3) Create payment

Merchant gửi request tạo thanh toán với:

* order_id
* amount
* description
* expire_at hoặc ttl
* optional metadata

Gateway trả về:

* transaction_id
* payment_url hoặc qr_content
* qr_image_url/base64
* status ban đầu
* expire_at

### 4) Get payment status

Merchant query theo:

* transaction_id hoặc order_id

Gateway trả về:

* current status
* amount
* created_at
* paid_at nếu có
* expire_at
* failure_reason nếu có

### 5) Create refund

Merchant gửi:

* original_transaction_id hoặc order_id
* refund_id
* refund_amount
* reason

Gateway kiểm tra:

* payment gốc có SUCCESS không
* số tiền refund có hợp lệ không
* refund_id có trùng không

### 6) Get refund status

Merchant query:

* refund_id
* hoặc refund_transaction_id

Gateway trả:

* refund status
* refund amount
* original payment reference
* processed_at / failure_reason

### 7) Webhook callback

Gateway gửi webhook khi:

* payment success
* payment failed/expired nếu cần
* refund success
* refund failed

**Trong MVP nên giữ đơn giản:**
ít event nhưng event phải rõ.

---

## 3.2. Payment Side Scope

### 1) Dynamic QR

Phải có trong MVP.

Mỗi payment tạo ra:

* QR riêng
* gắn amount
* gắn order/transaction reference
* có expire time

**Đây nên là luồng chính của hệ thống.**

### 2) Static QR

* mỗi merchant có thể có 1 static QR template
* customer tự nhập số tiền

### 3) Transaction state tracking

Payment transaction tối thiểu cần các trạng thái:

* INITIATED
* PENDING
* SUCCESS
* FAILED
* EXPIRED
* CANCELLED

Refund tối thiểu:

* REFUND_PENDING
* REFUNDED
* REFUND_FAILED

### 4) Expire payment

Dynamic QR phải có expire.

* mặc định 15 phút
* quá hạn thì transaction thành EXPIRED
* không cho mark success bằng flow merchant nữa sau khi expired.

### 5) Retry webhook

Webhook delivery phải có:

* số lần retry giới hạn: 3 lần
* log từng lần gửi
* trạng thái delivered / failed

### 6) Idempotency

**Create payment**: cùng `merchant_id + order_id` không được tạo nhiều payment logic giống nhau ngoài ý muốn

**Create refund**:  cùng `merchant_id + refund_id` không được refund 2 lần

**Webhook receiver**

* merchant side phải được giả định là idempotent
* gateway side nên có `event_id`

---

## 3.3. Admin / Ops Scope

### 1) Duyệt merchant

* xem thông tin merchant
* chuyển status từ pending -> active
* sinh credential

### 2) Khóa / mở merchant

* active / suspended / disabled
* merchant bị khóa thì không tạo payment/refund mới được

### 3) Xem giao dịch

Admin xem được:

* danh sách payment
* filter theo merchant
* filter theo status
* tra theo order_id / transaction_id

### 4) Xem refund

Admin xem được:

* refund list
* payment gốc liên quan
* status refund

### 5) Retry webhook thủ công

Cho phép ops:

* chọn event webhook lỗi
* bấm retry lại

**Đây là một tính năng nhỏ nhưng rất đáng giá**, vì giúp hệ thống trông “thật” hơn nhiều.

---

# 4. Chốt rõ “không làm” để tránh scope creep

## Không làm trong MVP này

* không tích hợp settlement batch tự động
* không có chargeback/dispute
* không có fraud detection/risk scoring
* không có multi-currency
* không có self-service onboarding portal cho merchant
* không có role/permission phức tạp nhiều cấp
* không có accounting ledger chuẩn enterprise
* không có báo cáo tài chính nâng cao
* không có dashboard analytics nâng cao
* không tích hợp nhiều provider cùng lúc ở bản đầu

* **không làm mobile app**
* **không làm merchant dashboard quá lớn**
* **không làm notification SMS/email phức tạp**

---

# 5. Chốt giả định triển khai

## Assumption 1: quy mô nhỏ

* số lượng merchant ít
* transaction volume thấp
* chủ yếu để demo / đồ án / prototype

## Assumption 2: chưa cần bank integration production-grade

Có thể dùng:

* mock bank callback
* simulated success/fail flow
* hoặc tích hợp QR provider đơn giản

## Assumption 3: admin portal đơn giản

* chỉ 1 portal nội bộ
* không cần UI đẹp phức tạp
* chỉ cần đủ thao tác vận hành

## Assumption 4: merchant chủ yếu tích hợp qua API

* không cần merchant portal đầy đủ ở phase đầu
* có thể chỉ cần Postman/OpenAPI/demo client

## Assumption 5: security ở mức MVP tốt

* có HMAC signature
* có HTTPS khi deploy
* có API auth
* có audit log cơ bản
* nhưng chưa cần tiêu chuẩn compliance nặng kiểu PCI DSS đầy đủ
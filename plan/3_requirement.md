# 1. Business requirements

## 1.1. 1 order chỉ có 1 payment active tại một thời điểm hay có thể nhiều?

**Chốt cho MVP:**
**1 order chỉ có 1 payment active tại một thời điểm.**

## Ý nghĩa

Với cùng một `merchant_id + order_id`:

* không được có 2 transaction cùng đang `PENDING`
* nếu payment cũ đang active thì không tạo payment active mới

## Lý do

* đơn giản hóa idempotency
* tránh customer quét nhầm nhiều QR
* dễ đối soát order ↔ payment
* phù hợp team nhỏ

## Rule cụ thể

* nếu `order_id` chưa có payment: tạo mới
* nếu `order_id` có payment `PENDING`: trả lại payment cũ
* nếu `order_id` có payment `SUCCESS`: không cho tạo lại
* nếu `order_id` có payment `FAILED` hoặc `EXPIRED`: **cho phép tạo payment mới**, nhưng là transaction mới, QR mới

---

## 1.2. Có cho phép partial refund không?

**Chốt cho MVP:**
**Không. Chỉ hỗ trợ full refund.**

## Ý nghĩa

* 1 payment SUCCESS chỉ refund toàn bộ một lần
* không hỗ trợ hoàn nhiều phần
* không hỗ trợ nhiều refund records cộng dồn

## Lý do

* giảm complexity ở validation
* giảm complexity ở reconciliation
* giảm complexity ở trạng thái order nội bộ merchant

## Rule cụ thể

* chỉ refund được khi payment = `SUCCESS`
* `refund_amount` phải đúng bằng `paid_amount`
* 1 payment chỉ có tối đa 1 refund thành công

---

## 1.3. Refund có time window không?

**Chốt cho MVP:**
**Có. Refund window = 7 ngày kể từ thời điểm payment SUCCESS.**

## Ý nghĩa

* quá 7 ngày thì reject refund request
* thời gian tính từ `paid_at`

## Lý do

* cần rule rõ để tránh refund vô thời hạn
* dễ vận hành hơn
* phù hợp demo/MVP

## Rule cụ thể

* nếu `now > paid_at + 7 days` → reject
* reason code: `REFUND_WINDOW_EXCEEDED`

---

## 1.4. Expired payment có được revive không?

**Chốt cho MVP:**
**Không. Expired payment không được revive.**

## Ý nghĩa

* payment đã `EXPIRED` là kết thúc
* nếu merchant muốn thanh toán lại thì phải tạo payment mới
* QR cũ hết hiệu lực hoàn toàn

## Lý do

* tránh ambiguity giữa QR cũ và QR mới
* giữ state machine đơn giản
* giảm rủi ro callback đến trễ gây rối

## Rule cụ thể

* `EXPIRED` là trạng thái cuối
* không có action “reactivate”
* muốn thanh toán lại phải gọi `create payment` mới

---

## 1.5. Webhook thất bại bao nhiêu lần thì dừng?

**Chốt cho MVP:**
**Retry tối đa 3 lần sau lần gửi đầu tiên**
tức là tổng cộng **4 attempts**: lần đầu -> retry 1 -> retry 2 -> retry 3

## Lý do

* đủ để xử lý lỗi tạm thời
* không làm queue phức tạp
* dễ quan sát với team nhỏ

## Rule cụ thể

* nếu nhận HTTP 2xx → coi là thành công
* nếu timeout / network error / 4xx / 5xx → retry
* hết 4 attempts → đánh dấu `FAILED`
* ops có thể retry thủ công sau đó

---

## 1.6. Merchant có được tạo static QR cho từng store không?

Không trong phase đầu. Static QR chưa hỗ trợ theo store.

Mỗi Merchant chỉ có duy nhất static QR.

---

# 2. Technical requirements

## 2.1. API REST hay thêm SDK

**Chốt cho MVP:**
**Chỉ làm REST API, không làm SDK.**

## Ý nghĩa

Cung cấp:

* REST endpoints
* OpenAPI/Swagger
* sample request/response

Không cung cấp:

* Java SDK
* Node SDK
* Python SDK

---

## 2.2. Auth bằng API key + HMAC signature

**Chốt cho MVP:**
**Có. Dùng `merchant_id + access_key + HMAC-SHA256 signature`.**

## Cách dùng

Merchant gửi:

* `X-Merchant-Id`
* `X-Access-Key`
* `X-Signature`
* `X-Timestamp`

Gateway:

* lấy `secret_key`
* build canonical string
* verify HMAC-SHA256

## Rule

* request thiếu auth headers → reject
* signature sai → reject
* timestamp lệch quá window cho phép → reject

## Time window

* chốt: **5 phút**

---

## 2.3. Idempotency key ở header hay body

**Chốt cho MVP:**
**Ưu tiên ở header.**

## Header dùng

* `X-Idempotency-Key`

## Rule áp dụng

### Create payment

* có thể dùng luôn `order_id` làm business idempotency chính
* `X-Idempotency-Key` là lớp kỹ thuật bổ sung

### Create refund

* dùng `refund_id` làm business idempotency chính
* `X-Idempotency-Key` là lớp kỹ thuật bổ sung

## Kết luận thực dụng

* payment: uniqueness chính theo `merchant_id + order_id`
* refund: uniqueness chính theo `merchant_id + refund_id`
* header idempotency để chuẩn hóa API design

---

## 2.4. Trạng thái transaction enum là gì?

## Payment transaction enum

**Chốt cho MVP:**

* `PENDING`
* `SUCCESS`
* `FAILED`
* `EXPIRED`

## Không cần public thêm

* `INITIATED` có thể là internal-only nếu muốn
* `CANCELLED` chưa cần nếu không có chức năng cancel

## Refund transaction enum

**Chốt cho MVP:**

* `REFUND_PENDING`
* `REFUNDED`
* `REFUND_FAILED`

## Lý do

* đủ cho tất cả use case trong scope
* đơn giản cho UI, API, DB, webhook

---

## 2.5. Retry policy thế nào?

**Chốt cho MVP:**

## Webhook retry

* total attempts: 4
* retry interval:

  * retry 1 sau 1 phút
  * retry 2 sau 5 phút
  * retry 3 sau 15 phút

## Không retry tự động cho create payment/refund API

Merchant tự retry từ phía client nếu bị network issue. Gateway xử lý bằng idempotency.

## Callback/provider polling

* chưa làm polling engine phức tạp
* nếu callback chưa rõ thì giữ pending + reconcile/manual review

---

## 2.6. Timeout bao lâu?

## Payment expire timeout

**Chốt:** default: **15 phút**

## Signature timestamp validity

**Chốt:** **5 phút**

## Webhook HTTP timeout

**Chốt:** connect + read timeout tổng **10 giây**

## Refund pending timeout cho manual review

**Chốt:** nếu `REFUND_PENDING > 30 phút` thì đưa vào danh sách review

---

## 2.7. Log/audit thế nào?

**Chốt cho MVP:** có 3 lớp log

## A. Application log

Ghi:

* request vào
* response ra
* lỗi hệ thống
* xử lý transaction/refund
* webhook send attempts

## B. Business event log

Ghi:

* payment created
* payment status changed
* refund created
* refund status changed
* merchant approved/suspended
* webhook retried manually

## C. Audit log

Ghi hành động quản trị:

* ai approve merchant
* ai suspend merchant
* ai retry webhook
* ai sửa webhook_url
* ai regenerate credentials

## Rule

* không log full secret_key
* không log raw signature nếu không cần
* không log dữ liệu nhạy cảm quá mức

---

## 2.8. Mã hóa secret ra sao?

**Chốt cho MVP:**
**Secret key không lưu plaintext thuần trong DB.**

## Cách làm phù hợp MVP

* secret_key sinh ra ngẫu nhiên
* lưu **encrypted at rest**
* chỉ hiển thị đầy đủ 1 lần lúc cấp
* về sau chỉ hiện masked, ví dụ `sk_live_****abcd`

## Nếu cần verify signature

Hệ thống phải giải mã secret ở server side để verify request.

## Rule

* admin không xem lại full secret đã cấp
* nếu merchant mất secret → regenerate secret mới
* regenerate secret sẽ làm secret cũ hết hiệu lực

---

# 3. Operational requirements

## 3.1. Ops xử lý merchant bị webhook fail thế nào?

**Chốt flow vận hành:**

1. hệ thống retry tự động tối đa 3 lần sau lần đầu
2. nếu vẫn fail → event chuyển `FAILED`
3. event xuất hiện trong danh sách webhook lỗi
4. ops kiểm tra:

   * webhook_url có sai không
   * endpoint merchant có down không
   * có timeout/network issue không
5. nếu sửa được cấu hình hoặc merchant đã up lại endpoint → ops bấm retry thủ công

## Rule

* ops không được sửa trực tiếp transaction status chỉ vì webhook fail
* webhook fail chỉ ảnh hưởng delivery, không đổi business status

---

## 3.2. Support tra giao dịch bằng order_id hay transaction_id

**Chốt cho MVP:**
**Tra được bằng cả 2.**

## Quy ước

* merchant-facing: thường dùng `order_id`
* internal support/ops: ưu tiên `transaction_id`

## Rule

* API cho merchant:

  * get payment status by `order_id` hoặc `transaction_id`
* admin portal:

  * search theo `merchant_id + order_id`
  * hoặc `transaction_id`

---

## 3.3. Khi refund fail thì ai can thiệp?

**Chốt cho MVP:**
**Ops/Admin nội bộ là bên can thiệp.**

## Rule vận hành

* refund fail hoặc pending quá lâu → vào queue review
* ops kiểm tra:

  * payment gốc
  * refund request
  * provider/callback log
* ops quyết định:

  * retry thủ công nếu có cơ chế
  * giữ failed
  * ghi chú manual review result

Merchant không có quyền tự ép trạng thái refund.

---

## 3.4. Khi bank callback chậm thì SLA ra sao?

**Chốt cho MVP:**
Không cam kết SLA production-grade.
Chốt rule vận hành nội bộ như sau:

* trong lúc chưa nhận callback cuối:

  * payment giữ `PENDING`
  * merchant dùng `get payment status` để query lại
* nếu quá **15 phút** chưa có kết quả và payment hết hạn:

  * payment chuyển `EXPIRED`
* nếu callback đến muộn sau đó:

  * không tự động revive payment expired
  * chuyển sang reconciliation/manual review

## Cách diễn đạt trong tài liệu

* hệ thống xử lý callback theo near real-time khi nhận được
* nếu callback chậm hoặc không rõ, trạng thái được xác nhận qua query/reconciliation/manual review

---

## 3.5. Ai được retry webhook bằng tay?

**Chốt cho MVP:**
**Chỉ Ops/Admin nội bộ.**

## Rule

* merchant không có nút retry webhook trong phase này
* retry manual phải có audit log:

  * ai retry
  * lúc nào
  * retry event nào
  * kết quả ra sao

---

## 3.6. Audit trail ghi những gì?

**Chốt cho MVP:** audit trail phải ghi ít nhất các nhóm sau

## Merchant management

* tạo merchant
* approve merchant
* reject merchant
* suspend/activate merchant
* sửa webhook_url
* sửa IP whitelist
* regenerate credentials

## Payment/refund operation

* create payment
* payment status change
* create refund
* refund status change

## Webhook operation

* webhook created
* mỗi lần gửi webhook
* manual retry webhook

## Manual intervention

* manual review opened
* manual review resolved
* người thao tác
* thời điểm thao tác
* ghi chú lý do

## Trường tối thiểu mỗi audit record

* `event_type`
* `entity_type`
* `entity_id`
* `actor_type`
  ví dụ: SYSTEM / ADMIN / OPS
* `actor_id`
* `timestamp`
* `before_state` nếu có
* `after_state` nếu có
* `note/reason`

---

# 4. Bản chốt ngắn gọn để dùng luôn

## Business

* 1 order chỉ có **1 payment active**
* chỉ hỗ trợ **full refund**
* refund window = **7 ngày**
* expired payment **không revive**
* webhook retry tối đa **3 lần sau lần đầu**
* **không hỗ trợ static QR per store** trong MVP

## Technical

* chỉ làm **REST API**
* auth = **API key + HMAC-SHA256**
* idempotency key ở **header**
* payment status = `PENDING | SUCCESS | FAILED | EXPIRED`
* refund status = `REFUND_PENDING | REFUNDED | REFUND_FAILED`
* webhook retry = **1m / 5m / 15m**
* payment expire = **15 phút**
* webhook timeout = **10 giây**
* có application log + business log + audit log
* secret_key lưu **encrypted at rest**, chỉ hiển thị full một lần

## Operational

* webhook fail: auto retry → failed queue → ops retry thủ công
* support tra giao dịch bằng **order_id và transaction_id**
* refund fail do **ops/admin** xử lý
* callback chậm: giữ pending, hết hạn thì expired, callback muộn chuyển reconcile/manual review
* chỉ **ops/admin** được retry webhook bằng tay
* audit trail ghi đầy đủ hành động quản trị, trạng thái trước/sau, actor, timestamp, reason
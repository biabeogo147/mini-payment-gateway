# 1. Payment state machine

## 1.1. Ý nghĩa từng state

### INITIATED

Gateway đã nhận request tạo payment và bắt đầu xử lý, nhưng chưa hoàn tất việc tạo payment usable cho merchant.

Dùng khi:

* request vừa qua bước auth/validation
* đang tạo transaction record
* đang sinh QR
* chưa trả kết quả hoàn chỉnh

### PENDING

Payment đã được tạo thành công, QR đã sẵn sàng, đang chờ customer thanh toán.

Dùng khi:

* merchant đã nhận QR
* customer chưa thanh toán xong
* hoặc gateway chưa nhận kết quả cuối từ bank/provider

### SUCCESS

Thanh toán thành công và được gateway ghi nhận là thành công cuối cùng.

Dùng khi:

* đã nhận kết quả thanh toán thành công hợp lệ
* transaction hoàn tất về phía payment flow

### FAILED

Thanh toán thất bại.

Dùng khi:

* bank/provider trả kết quả thất bại rõ ràng
* hoặc xử lý thanh toán bị từ chối rõ ràng

### EXPIRED

Payment hết hạn thanh toán.

Dùng khi:

* quá `expire_at`
* transaction vẫn chưa thành công

### CANCELLED

Payment bị hủy chủ động bởi hệ thống hoặc ops theo một rule riêng.

Trong scope hiện tại, **state này chưa cần dùng thực tế** vì bạn chưa có use case cancel payment.
Nó có thể giữ trong thiết kế mở rộng, nhưng **không bắt buộc phải kích hoạt ở MVP**.

---

# 2. Payment transitions hợp lệ

## 2.1. Luồng chính

* `INITIATED -> PENDING`
* `PENDING -> SUCCESS`
* `PENDING -> FAILED`
* `PENDING -> EXPIRED`

## 2.2. Có nên có transition khác không?

### INITIATED -> FAILED

**Nên cho phép ở mức internal system.**

Lý do:

* nếu create payment fail ở bước sinh QR
* hoặc không ghi được transaction hoàn chỉnh
* hoặc validation nội bộ giai đoạn cuối fail

Tuy nhiên nếu bạn muốn cực đơn giản, có thể xử lý create thất bại là **API error và không tạo transaction**, tức không cần state này.

**Khuyến nghị cho MVP:**

* nếu chưa tạo được QR/transaction usable thì trả lỗi API luôn
* không cần lưu `INITIATED -> FAILED` nếu muốn đơn giản hóa

### INITIATED -> CANCELLED

**Không cần trong scope này**

### PENDING -> CANCELLED

**Không cần trong scope này**

### SUCCESS -> REFUNDED

**Không nên đưa refund vào payment state**
Refund là flow riêng, entity riêng.
Payment vẫn giữ `SUCCESS`, còn refund nằm ở `RefundTransaction`.

Đây là điểm rất quan trọng.

---

# 3. Payment state nào là final

## Final states

* `SUCCESS`
* `FAILED`
* `EXPIRED`
* `CANCELLED` nếu có dùng

## Non-final states

* `INITIATED`
* `PENDING`

## Ý nghĩa

Final state là khi payment flow đã kết thúc và **không được chuyển tiếp tiếp** trong luồng payment bình thường.

---

# 4. Payment state nào được retry

Ở đây phải tách 2 ý:

## 4.1. Retry create payment request

Không phải retry state transition, mà là retry API call từ merchant.

### Có thể retry khi:

* request create payment bị timeout mạng
* merchant không chắc request trước đã thành công chưa

### Cách xử lý:

* dựa vào idempotency theo `merchant_id + order_id`
* nếu payment đang `PENDING` thì trả lại transaction cũ
* nếu payment trước `FAILED` hoặc `EXPIRED` thì cho phép tạo payment mới

---

## 4.2. Retry payment business flow theo state

### INITIATED

Có thể retry xử lý nội bộ nếu đang ở bước tạo transaction/QR, nhưng với MVP tốt nhất là:

* hoặc thành công sang `PENDING`
* hoặc trả lỗi API luôn

Tức là **không nên để INITIATED tồn tại lâu**.

### PENDING

Không phải retry “state”, nhưng là trạng thái chờ tiếp tục xử lý.

* chờ customer scan
* chờ callback
* chờ query/reconcile

### SUCCESS

Không retry payment nữa.

### FAILED

Không revive transaction cũ.
Muốn thanh toán lại thì tạo **payment mới**.

### EXPIRED

Không revive.
Muốn thanh toán lại thì tạo **payment mới**.

### CANCELLED

Không retry transaction cũ.

---

# 5. Payment state nào cho phép refund

## Chỉ `SUCCESS` cho phép refund

Rule chốt:

* `PENDING` -> không refund
* `FAILED` -> không refund
* `EXPIRED` -> không refund
* `CANCELLED` -> không refund
* `SUCCESS` -> được refund

---

# 6. Payment rule table

## 6.1. Bảng tóm tắt

| State     | Ý nghĩa               | Final? |                    Cho retry payment logic? | Cho create payment mới cùng order? | Cho refund? |
| --------- | --------------------- | -----: | ------------------------------------------: | ---------------------------------: | ----------: |
| INITIATED | Đang khởi tạo payment |  Không |                         Có, nội bộ ngắn hạn |                      Không áp dụng |       Không |
| PENDING   | Đang chờ thanh toán   |  Không | Không retry transaction cũ, chỉ chờ kết quả |                              Không |       Không |
| SUCCESS   | Thanh toán thành công |     Có |                                       Không |                              Không |          Có |
| FAILED    | Thanh toán thất bại   |     Có |                                       Không |                                 Có |       Không |
| EXPIRED   | Hết hạn thanh toán    |     Có |                                       Không |                                 Có |       Không |
| CANCELLED | Bị hủy                |     Có |                                       Không |                                 Có |       Không |

---

# 7. Payment business rules chi tiết

## Rule 1. Một order chỉ có 1 payment active

“Active payment” ở đây là:

* `INITIATED`
* `PENDING`

Tức là với cùng `merchant_id + order_id`, không được có hơn 1 transaction ở 2 state này cùng lúc.

---

## Rule 2. Payment final state không được update bừa

Nếu transaction đã ở:

* `SUCCESS`
* `FAILED`
* `EXPIRED`
* `CANCELLED`

thì không được update sang state payment khác, trừ khi có quy trình manual review/reconciliation rất đặc biệt.

Trong MVP:

* nên coi final state là immutable theo luồng xử lý bình thường

---

## Rule 3. Callback đến muộn sau EXPIRED

Do bạn đã chốt:

* expired payment không revive

thì callback thành công đến sau khi payment đã `EXPIRED` sẽ:

* không tự chuyển `EXPIRED -> SUCCESS`
* phải đưa vào reconciliation/manual review

Đây là rule rất quan trọng.

---

## Rule 4. Duplicate create payment

Với cùng `merchant_id + order_id`:

### Nếu payment đang `PENDING`

* trả lại payment cũ

### Nếu payment đã `SUCCESS`

* reject tạo payment mới

### Nếu payment đã `FAILED` hoặc `EXPIRED`

* cho phép tạo payment mới

---

# 8. Refund state machine

Bạn đang có:

* REFUND_PENDING
* REFUNDED
* REFUND_FAILED

Bộ này phù hợp cho MVP.

---

## 8.1. Ý nghĩa từng state

### REFUND_PENDING

Refund request đã được chấp nhận và đang chờ xử lý kết quả cuối.

Dùng khi:

* refund record đã được tạo
* đã gửi xử lý refund hoặc đang chờ callback/result

### REFUNDED

Refund thành công.

Dùng khi:

* đã xác nhận tiền được hoàn thành công

### REFUND_FAILED

Refund thất bại.

Dùng khi:

* refund bị từ chối rõ ràng
* hoặc không thể xử lý refund

---

# 9. Refund transitions hợp lệ

## Luồng chính

* `REFUND_PENDING -> REFUNDED`
* `REFUND_PENDING -> REFUND_FAILED`

## Không nên có

* `REFUNDED -> REFUND_FAILED`
* `REFUND_FAILED -> REFUNDED`
* `REFUNDED -> REFUND_PENDING`

Trừ khi sau này có workflow phức tạp hơn.
Trong MVP, refund final state nên đóng luôn.

---

# 10. Refund state nào là final

## Final states

* `REFUNDED`
* `REFUND_FAILED`

## Non-final

* `REFUND_PENDING`

---

# 11. Refund state nào được retry

Ở đây cũng tách 2 ý:

## 11.1. Retry refund API request

Nếu merchant retry cùng request refund do lỗi mạng:

* dùng idempotency theo `merchant_id + refund_id`
* nếu refund record đã tồn tại thì trả lại refund hiện có

## 11.2. Retry refund business flow

### REFUND_PENDING

Có thể tiếp tục chờ callback/query/reconcile.

### REFUND_FAILED

Trong MVP, **không retry trên cùng refund record**.
Nếu muốn refund lại, phải có rule mới và refund request mới.
Nhưng vì bạn đang chốt **full refund only**, tốt nhất:

* `REFUND_FAILED` thì merchant có thể gửi lại **refund request mới với refund_id mới**, nếu business cho phép
* hoặc ops xử lý manual review

**Khuyến nghị MVP:**

* không cho merchant tự retry loạn
* refund fail thì qua ops/manual review trước

### REFUNDED

Không retry nữa.

---

# 12. Refund rule table

| State          | Ý nghĩa                 | Final? |                        Cho retry xử lý? | Merchant query được? |
| -------------- | ----------------------- | -----: | --------------------------------------: | -------------------: |
| REFUND_PENDING | Đang chờ kết quả refund |  Không | Có, ở mức query/reconcile/manual review |                   Có |
| REFUNDED       | Refund thành công       |     Có |                                   Không |                   Có |
| REFUND_FAILED  | Refund thất bại         |     Có |                  Không trên cùng record |                   Có |

---

# 13. Refund business rules chi tiết

## Rule 1. Chỉ payment SUCCESS mới refund được

Payment phải:

* tồn tại
* thuộc merchant này
* đang ở `SUCCESS`

nếu không thì reject request.

---

## Rule 2. Tổng refund không vượt paid amount

Vì MVP chỉ **full refund only**, rule này đơn giản thành:

* `refund_amount == paid_amount`

Nếu sau này mở partial refund, lúc đó mới cần:

* tổng tất cả refund success/pending không vượt amount gốc

Nhưng trong scope hiện tại, không cần mở rộng.

---

## Rule 3. Cùng refund_id không được tạo 2 lần

Uniqueness theo:

* `merchant_id + refund_id`

Nếu merchant gửi lại cùng `refund_id`:

* không tạo record mới
* trả lại refund record hiện có

---

## Rule 4. Mỗi payment chỉ có tối đa 1 refund thành công

Vì full refund only:

* một payment đã `REFUNDED` thì không được tạo refund mới nữa

---

## Rule 5. Refund window

Chỉ cho refund nếu:

* `current_time <= paid_at + 7 days`

Quá thời gian:

* reject với reason code phù hợp

---

# 14. Quan hệ Payment ↔ Refund

Phải ghi rõ để không bị nhầm state.

## Payment và Refund là 2 state machine riêng

* PaymentTransaction có state riêng
* RefundTransaction có state riêng

## Không làm kiểu:

* payment state = REFUNDED
* payment state = REFUND_PENDING

Cách đó làm flow rất rối.

## Cách đúng trong scope hiện tại

* Payment vẫn là `SUCCESS`
* RefundTransaction giữ:

  * `REFUND_PENDING`
  * `REFUNDED`
  * `REFUND_FAILED`

Nếu cần biết payment đã được refund chưa, có thể:

* query từ RefundTransaction
* hoặc thêm derived flag / summary field sau

---

# 15. Transition table nên chốt

## 15.1. Payment transition table

| From      | To                |              Hợp lệ? | Điều kiện                                   |
| --------- | ----------------- | -------------------: | ------------------------------------------- |
| INITIATED | PENDING           |                   Có | tạo transaction + QR thành công             |
| PENDING   | SUCCESS           |                   Có | nhận kết quả thanh toán thành công hợp lệ   |
| PENDING   | FAILED            |                   Có | nhận kết quả thất bại hợp lệ                |
| PENDING   | EXPIRED           |                   Có | quá expire_at, chưa có kết quả thành công   |
| INITIATED | FAILED            |             Tùy chọn | chỉ nếu bạn muốn lưu lỗi tạo payment nội bộ |
| PENDING   | CANCELLED         | Không dùng trong MVP | chưa có use case cancel                     |
| SUCCESS   | bất kỳ state khác |                Không | final state                                 |
| FAILED    | bất kỳ state khác |                Không | final state                                 |
| EXPIRED   | bất kỳ state khác |                Không | final state                                 |

---

## 15.2. Refund transition table

| From           | To                | Hợp lệ? | Điều kiện                      |
| -------------- | ----------------- | ------: | ------------------------------ |
| REFUND_PENDING | REFUNDED          |      Có | nhận kết quả refund thành công |
| REFUND_PENDING | REFUND_FAILED     |      Có | nhận kết quả refund thất bại   |
| REFUNDED       | bất kỳ state khác |   Không | final state                    |
| REFUND_FAILED  | bất kỳ state khác |   Không | final state                    |

---

# 16. Chốt thực dụng cho MVP

## Payment states dùng thật

Khuyên dùng public/internal như sau:

### Internal

* INITIATED
* PENDING
* SUCCESS
* FAILED
* EXPIRED

### Public API

* PENDING
* SUCCESS
* FAILED
* EXPIRED

`CANCELLED` chưa cần bật ở MVP.

---

## Refund states dùng thật

* REFUND_PENDING
* REFUNDED
* REFUND_FAILED

---

## Final states

### Payment

* SUCCESS
* FAILED
* EXPIRED

### Refund

* REFUNDED
* REFUND_FAILED

---

## Refund eligibility

Chỉ:

* payment = SUCCESS
* chưa refund thành công trước đó
* trong refund window 7 ngày
* refund_amount = paid_amount
* refund_id chưa tồn tại

---

# 17. Bản chốt ngắn gọn

## Payment

* `INITIATED -> PENDING -> (SUCCESS | FAILED | EXPIRED)`
* `SUCCESS`, `FAILED`, `EXPIRED` là final
* `PENDING` là state active chính
* chỉ `SUCCESS` cho phép refund
* `FAILED` và `EXPIRED` cho phép tạo payment mới cho cùng order
* `SUCCESS` không cho tạo payment mới cho cùng order
* expired payment không revive

## Refund

* `REFUND_PENDING -> (REFUNDED | REFUND_FAILED)`
* `REFUNDED`, `REFUND_FAILED` là final
* chỉ payment `SUCCESS` mới refund được
* MVP chỉ full refund
* `merchant_id + refund_id` là duy nhất
* một payment chỉ có tối đa một refund thành công

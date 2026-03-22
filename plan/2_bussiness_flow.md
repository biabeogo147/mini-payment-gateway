# 1. Merchant onboarding flow

## 1.1. Mục tiêu

Đưa một merchant từ trạng thái chưa có quyền tích hợp sang trạng thái có thể gọi API payment/refund hợp lệ.

## 1.2. Actor

* **Merchant**: cung cấp thông tin đăng ký
* **Ops/Admin**: kiểm tra, duyệt, cấu hình
* **Gateway system**: lưu merchant, sinh credentials, quản lý trạng thái

## 1.3. Input

Merchant onboarding trong scope này là **thủ công qua admin**, nên input tối thiểu gồm:

### Merchant cung cấp

* merchant_name
* business/legal name
* contact_name
* contact_email
* contact_phone
* settlement account info
* webhook_url
* allowed_ip_list
* mô tả hệ thống tích hợp hoặc domain/app name
* giấy tờ pháp lý cần thiết

### Ops/Admin nhập/xác nhận

* kết quả kiểm tra giấy tờ
* kết quả xác nhận tài khoản nhận tiền
* webhook_url hợp lệ hay không
* IP whitelist hợp lệ hay không
* trạng thái duyệt

## 1.4. Output

Khi onboarding hoàn tất, hệ thống tạo ra:

* merchant_id
* access_key
* secret_key
* merchant_status = ACTIVE
* config tích hợp đã lưu:

  * webhook_url
  * allowed_ip_list
  * settlement account info

Nếu chưa hoàn tất, output có thể là:

* PENDING_REVIEW
* REJECTED
* SUSPENDED

## 1.5. Trạng thái

Nên dùng state đơn giản:

* **DRAFT**: merchant record mới tạo, chưa submit đủ info
* **PENDING_REVIEW**: chờ ops kiểm tra
* **REJECTED**: bị từ chối
* **APPROVED**: đã duyệt logic nghiệp vụ
* **ACTIVE**: đã cấp credential, có thể gọi API
* **SUSPENDED**: bị khóa tạm thời
* **DISABLED**: ngưng sử dụng lâu dài

## 1.6. Luồng chính

1. Merchant gửi thông tin đăng ký cho ops/admin
2. Ops tạo merchant record trong hệ thống
3. Ops kiểm tra giấy tờ
4. Ops xác nhận tài khoản nhận tiền
5. Ops nhập webhook_url và IP whitelist
6. Hệ thống validate format cấu hình
7. Ops approve merchant
8. Gateway sinh merchant_id, access_key, secret_key
9. Merchant chuyển sang ACTIVE

## 1.7. Lỗi có thể xảy ra

* thiếu giấy tờ hoặc giấy tờ không hợp lệ
* settlement account info không khớp
* webhook_url sai format / không reachable
* allowed_ip_list sai format
* merchant bị trùng thông tin định danh
* lỗi khi sinh credentials
* ops quên cấu hình bắt buộc nhưng vẫn approve

## 1.8. Cách recover

* chuyển merchant về PENDING_REVIEW để bổ sung
* reject kèm reason
* cho phép admin sửa cấu hình rồi approve lại
* regenerate credentials nếu cấp lỗi hoặc nghi lộ key
* suspend merchant nếu phát hiện cấu hình gây rủi ro

## 1.9. Business rules cần chốt

* merchant chỉ được ACTIVE khi đã có:

  * settlement account info
  * webhook_url
  * credentials
* secret_key chỉ cấp khi approved
* merchant SUSPENDED không được tạo payment/refund mới
* merchant SUSPENDED vẫn có thể tra transaction cũ hay không: nên **cho phép read, cấm write**

---

# 2. Payment flow

## 2.1. Mục tiêu

Cho phép merchant tạo một payment transaction, sinh QR, nhận kết quả thanh toán, cập nhật trạng thái và thông báo qua webhook.

## 2.2. Actor

* **Merchant backend**
* **Gateway**
* **Customer**
* **Bank/NAPAS** (hoặc payment simulator trong MVP)
* **Merchant webhook receiver**

## 2.3. Input

### Bước merchant tạo order nội bộ

Merchant tự có:

* order_id
* amount
* description
* expire_at hoặc ttl
* customer_info (optional)
* metadata (optional)

### Bước gọi create payment

Merchant gửi sang gateway:

* merchant_id
* access_key
* order_id
* amount
* description
* expire_at / ttl
* optional return data / metadata
* signature

## 2.4. Output

Gateway trả:

* transaction_id
* order_id
* merchant_id
* qr_content hoặc qr_image/base64
* payment_url nếu có
* status ban đầu
* created_at
* expire_at

Sau đó trong các bước sau:

* payment có thể chuyển SUCCESS / FAILED / EXPIRED
* webhook event được gửi về merchant

## 2.5. Trạng thái

Nên định nghĩa payment state rõ như sau:

* **INITIATED**: request đã nhận, đang xử lý tạo transaction
* **PENDING**: QR đã tạo, đang chờ customer thanh toán
* **SUCCESS**: thanh toán thành công
* **FAILED**: thanh toán thất bại
* **EXPIRED**: quá hạn thanh toán
* **CANCELLED**: bị hủy chủ động nếu có hỗ trợ

Với scope hiện tại, các trạng thái quan trọng nhất là:

* PENDING
* SUCCESS
* FAILED
* EXPIRED

## 2.6. Luồng chính

1. Merchant tạo order nội bộ
2. Merchant gọi `create payment`
3. Gateway verify merchant + verify signature
4. Gateway check idempotency theo order_id
5. Gateway tạo transaction record
6. Gateway sinh dynamic QR
7. Gateway trả QR cho merchant
8. Merchant hiển thị QR cho customer
9. Customer quét QR bằng app ngân hàng
10. Bank/NAPAS xử lý thanh toán
11. Gateway nhận kết quả thanh toán
12. Gateway cập nhật transaction status
13. Gateway gửi webhook
14. Merchant verify webhook và cập nhật order nội bộ

## 2.7. Input / output theo từng đoạn chính

### A. Create payment

**Input**

* merchant credentials
* order_id
* amount
* description
* expire info
* signature

**Output**

* transaction_id
* qr_content
* status = PENDING
* expire_at

### B. Payment completion callback

**Input**

* bank/provider callback hoặc simulator result
* transaction reference
* payment result
* paid amount
* paid timestamp
* external transaction reference

**Output**

* transaction được update
* webhook event được tạo

### C. Webhook gửi merchant

**Input**

* transaction status mới
* event payload
* webhook signing secret/signature

**Output**

* merchant nhận event
* event được đánh dấu DELIVERED hoặc FAILED

## 2.8. Lỗi có thể xảy ra

* merchant không active
* signature sai
* request thiếu field
* amount không hợp lệ
* expire_at không hợp lệ
* duplicate create payment
* lỗi tạo transaction record
* lỗi sinh QR
* customer quét nhưng không thanh toán
* bank callback chậm hoặc lỗi
* callback về trạng thái không rõ
* webhook gửi thất bại
* merchant nhận webhook nhưng xử lý trùng

## 2.9. Cách recover

* reject request ngay nếu auth/signature sai
* trả lại transaction cũ nếu duplicate create payment hợp lệ
* mark EXPIRED nếu quá thời gian thanh toán
* cho merchant gọi `get payment status` nếu webhook chưa tới
* retry webhook tự động khi gửi lỗi
* ops retry webhook thủ công nếu cần
* nếu callback từ bank chưa rõ, giữ trạng thái PENDING hoặc một trạng thái trung gian nội bộ rồi reconcile sau

## 2.10. Business rules cần chốt

* một `merchant_id + order_id` chỉ map tới một payment active logical record
* payment SUCCESS là trạng thái cuối cho flow payment
* payment EXPIRED không được tái sử dụng QR
* chỉ transaction SUCCESS mới refund được
* merchant phải verify chữ ký webhook trước khi cập nhật order

---

# 3. Refund flow

## 3.1. Mục tiêu

Cho phép merchant hoàn tiền cho một payment đã thành công và theo dõi refund như một flow độc lập.

## 3.2. Actor

* **Merchant backend**
* **Gateway**
* **Bank/payment rail/simulator**
* **Merchant webhook receiver**
* **Ops/Admin** (khi cần tra cứu/support)

## 3.3. Input

Merchant gửi:

* merchant_id
* access_key
* original_transaction_id hoặc order_id
* refund_id
* refund_amount
* reason
* signature

## 3.4. Output

Gateway trả:

* refund_transaction_id
* original_transaction_id
* refund_id
* refund_amount
* refund_status
* created_at

Sau đó refund có thể:

* thành công
* thất bại
* đang xử lý

## 3.5. Trạng thái

Nên tối thiểu có:

* **REFUND_PENDING**
* **REFUNDED**
* **REFUND_FAILED**

Nếu muốn rõ hơn cho nội bộ:

* REFUND_INITIATED
* REFUND_PENDING
* REFUNDED
* REFUND_FAILED

## 3.6. Luồng chính

1. Merchant gửi refund request
2. Gateway verify merchant + signature
3. Gateway kiểm tra payment gốc
4. Gateway kiểm tra rule refund
5. Gateway check idempotency theo refund_id
6. Gateway tạo refund record
7. Gateway gọi xử lý refund qua payment rail/simulator
8. Gateway nhận kết quả refund
9. Gateway cập nhật refund status
10. Gateway gửi webhook refund cho merchant
11. Merchant cập nhật order/sổ cái nội bộ

## 3.7. Kiểm tra payment gốc gồm gì

* payment có tồn tại không
* payment có thuộc merchant này không
* payment đã SUCCESS chưa
* payment có bị refund quá số tiền không
* refund_id có bị trùng không

## 3.8. Lỗi có thể xảy ra

* payment gốc không tồn tại
* payment chưa SUCCESS
* refund_amount > amount còn lại được refund
* duplicate refund_id
* signature sai
* merchant không active
* rail thanh toán phản hồi lỗi
* refund callback chậm / không rõ kết quả
* webhook refund gửi lỗi

## 3.9. Cách recover

* reject refund request nếu không qua validation
* nếu duplicate refund_id thì trả lại kết quả refund cũ
* nếu rail trả chưa rõ thì giữ REFUND_PENDING và cho query lại
* retry webhook refund
* cho ops/manual review nếu refund treo lâu
* reconcile refund với payment gốc để xác minh trạng thái thật

## 3.10. Business rules cần chốt

* chỉ payment SUCCESS mới refund được
* full refund hay partial refund: nếu scope chưa chốt, nên chọn **full refund only** cho MVP để giảm phức tạp
* mỗi `merchant_id + refund_id` là duy nhất
* tổng số tiền refund không vượt amount gốc
* refund là flow riêng, không ghi đè trực tiếp payment record

---

# 4. Reconciliation flow

## 4.1. Mục tiêu

Phát hiện và xử lý trường hợp dữ liệu giao dịch giữa gateway và phía bank/NAPAS/payment rail không khớp.

Trong scope hiện tại, reconciliation **không phải settlement nâng cao**, mà chỉ là:

* so khớp trạng thái/payment result
* phát hiện lệch
* đưa vào manual review

## 4.2. Actor

* **Gateway reconciliation job/process**
* **Ops/Admin**
* **Bank/NAPAS/provider data source** hoặc simulator log

## 4.3. Input

Dữ liệu đầu vào gồm 2 phía:

### Từ gateway

* transaction_id
* order_id
* merchant_id
* amount
* internal status
* external reference nếu có
* timestamps

### Từ bank/NAPAS/provider

* external transaction reference
* amount
* payment result
* processed time
* refund result nếu có

## 4.4. Output

* match result
* mismatch reason
* reconciliation status
* danh sách record cần manual review

## 4.5. Trạng thái

Cho reconciliation record:

* **MATCHED**
* **MISMATCHED**
* **PENDING_REVIEW**
* **RESOLVED**

## 4.6. Luồng chính

1. Gateway lấy danh sách transaction/refund cần reconcile
2. Gateway lấy dữ liệu đối chiếu từ provider/simulator
3. So khớp theo reference, amount, status, thời gian
4. Nếu khớp -> MATCHED
5. Nếu không khớp -> MISMATCHED
6. Record mismatch được chuyển sang PENDING_REVIEW
7. Ops xem và xử lý thủ công
8. Sau xử lý -> RESOLVED

## 4.7. Các kiểu mismatch phổ biến

* gateway PENDING nhưng provider báo SUCCESS
* gateway SUCCESS nhưng provider không có record
* amount không khớp
* refund status nội bộ khác refund status provider
* thiếu external reference
* callback đến trễ làm trạng thái tạm thời lệch

## 4.8. Lỗi có thể xảy ra

* không lấy được dữ liệu provider
* record không đủ field để match
* duplicate external reference
* dữ liệu provider đến muộn
* mismatch nhưng chưa đủ thông tin kết luận

## 4.9. Cách recover

* chạy reconcile lại sau
* mark PENDING_REVIEW thay vì tự sửa bừa
* ops kiểm tra log callback / log webhook / log provider
* cho phép cập nhật trạng thái thủ công nếu có bằng chứng rõ
* giữ audit log khi can thiệp tay

## 4.10. Business rules cần chốt

* reconciliation không tự động sửa trạng thái SUCCESS/FAILED bừa bãi nếu chưa chắc chắn
* mismatch phải có reason code
* mọi manual override phải có audit log
* reconciliation chỉ dùng để support consistency, không mở rộng thành settlement engine trong scope này

---

# 5. Failure handling flow

Đây không phải một flow nghiệp vụ riêng như payment/refund, mà là **bộ quy tắc xử lý bất thường** cắt ngang các flow còn lại.

---

## 5.1. Timeout

### Mục tiêu

Xử lý trường hợp payment/refund chờ quá lâu mà không có kết quả cuối.

### Actor

* Gateway scheduler/job
* Merchant
* Ops/Admin

### Input

* transaction/refund đang ở trạng thái chờ
* created_at / expire_at / last_update_at
* timeout policy

### Output

* payment -> EXPIRED nếu quá hạn thanh toán
* refund -> giữ REFUND_PENDING hoặc đưa manual review nếu quá lâu

### Lỗi có thể xảy ra

* job timeout không chạy
* timeout nhầm giao dịch đã thành công
* callback thành công đến sau khi đã expire

### Cách recover

* timeout job phải check trạng thái hiện tại trước khi update
* callback đến muộn phải đi qua reconciliation/manual review rule
* ops có thể xem log và xử lý tay nếu có xung đột

---

## 5.2. Duplicate create payment

### Mục tiêu

Ngăn cùng một order bị tạo nhiều payment ngoài ý muốn.

### Actor

* Merchant backend
* Gateway

### Input

* create payment request mới
* merchant_id
* order_id

### Output

* trả payment hiện có nếu request được xem là lặp hợp lệ
* hoặc reject nếu conflict

### Lỗi có thể xảy ra

* merchant retry do network timeout
* request cùng order_id nhưng khác amount
* 2 request song song cùng vào

### Cách recover

* enforce unique key/idempotency key
* nếu cùng semantic request -> trả transaction cũ
* nếu khác semantic request -> reject conflict
* cần lock/transaction DB để tránh race condition

---

## 5.3. Webhook gửi lỗi

### Mục tiêu

Đảm bảo merchant vẫn có thể nhận event hoặc tự query nếu webhook thất bại.

### Actor

* Gateway webhook delivery service
* Merchant webhook receiver
* Ops/Admin

### Input

* webhook event payload
* webhook_url
* signature

### Output

* delivery success
* retry scheduled
* dead/final failure sau số lần retry tối đa

### Lỗi có thể xảy ra

* merchant endpoint down
* timeout HTTP
* response 4xx / 5xx
* DNS/network lỗi
* webhook_url cấu hình sai

### Cách recover

* retry tự động
* ghi log từng attempt
* ops retry thủ công
* merchant gọi check status chủ động
* nếu endpoint sai, ops sửa config rồi retry event

---

## 5.4. Ngân hàng trả trạng thái chưa rõ

### Mục tiêu

Không kết luận sai khi external result chưa definitive.

### Actor

* Gateway
* Bank/provider/simulator
* Ops/Admin

### Input

* callback/provider response mơ hồ
* transaction/refund reference

### Output

* giữ trạng thái chờ
* record cần reconcile/manual review

### Lỗi có thể xảy ra

* callback thiếu field
* external status không map được sang enum nội bộ
* trạng thái thay đổi nhiều lần

### Cách recover

* map về trạng thái chờ nội bộ
* không kết luận SUCCESS/FAILED ngay
* reconcile lại sau
* manual review nếu kéo dài

---

## 5.5. Refund treo

### Mục tiêu

Xử lý refund request tạo rồi nhưng chưa có kết quả cuối.

### Actor

* Gateway
* Merchant
* Ops/Admin
* External rail

### Input

* refund_status = REFUND_PENDING quá lâu

### Output

* tiếp tục pending
* reconcile/manual review
* eventual success/failure

### Lỗi có thể xảy ra

* external rail chậm
* callback refund mất
* provider trả thiếu thông tin

### Cách recover

* merchant query refund status
* gateway reconcile
* ops review thủ công
* webhook retry nếu kết quả có rồi mà merchant chưa nhận

---

## 5.6. Merchant query lại

### Mục tiêu

Cho merchant có đường dự phòng khi webhook hoặc callback không tin cậy.

### Actor

* Merchant
* Gateway

### Input

* transaction_id / order_id / refund_id

### Output

* trạng thái hiện tại mới nhất
* timestamps liên quan
* reason nếu failed

### Lỗi có thể xảy ra

* merchant query sai reference
* query khi record chưa được update kịp
* trạng thái vẫn pending lâu

### Cách recover

* trả trạng thái hiện tại đúng nhất tại thời điểm query
* nếu pending thì merchant tiếp tục poll theo interval hợp lý
* nếu cần, ops kiểm tra manual

---

# 6. Tóm tắt nhanh từng flow dưới dạng checklist

## Merchant onboarding flow

* **Input**: merchant info, giấy tờ, settlement account, webhook_url, IP whitelist
* **Output**: merchant active + credentials
* **Actor**: merchant, ops/admin, gateway
* **Trạng thái**: pending, active, rejected, suspended
* **Lỗi**: thiếu giấy tờ, config sai, sinh key lỗi
* **Recover**: bổ sung, sửa config, re-approve, regenerate key

## Payment flow

* **Input**: order_id, amount, description, expire, signature
* **Output**: transaction + QR + webhook status update
* **Actor**: merchant, gateway, customer, bank/provider
* **Trạng thái**: initiated, pending, success, failed, expired
* **Lỗi**: duplicate, QR lỗi, callback chậm, webhook lỗi
* **Recover**: idempotency, timeout, retry webhook, status query, reconcile

## Refund flow

* **Input**: original transaction, refund_id, refund_amount, reason
* **Output**: refund record + refund status + webhook
* **Actor**: merchant, gateway, provider, ops
* **Trạng thái**: refund_pending, refunded, refund_failed
* **Lỗi**: payment không hợp lệ, refund trùng, refund treo
* **Recover**: reject validation, idempotency, query lại, reconcile, manual review

## Reconciliation flow

* **Input**: dữ liệu gateway + dữ liệu provider
* **Output**: matched / mismatched / pending review
* **Actor**: gateway job, ops
* **Trạng thái**: matched, mismatched, pending_review, resolved
* **Lỗi**: thiếu data, lệch amount/status, callback trễ
* **Recover**: re-run reconcile, manual review, audit log

## Failure handling flow

* **Input**: timeout, duplicate, webhook fail, unclear bank status, stuck refund
* **Output**: expire, retry, pending review, query fallback
* **Actor**: gateway, ops, merchant
* **Trạng thái**: tùy flow gốc
* **Lỗi**: race condition, duplicate, delayed result
* **Recover**: idempotency, retry, reconcile, manual review, status query
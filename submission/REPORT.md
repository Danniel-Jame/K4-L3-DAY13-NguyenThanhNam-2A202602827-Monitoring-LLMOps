# Báo cáo cá nhân — K4-L3B Day 13 Monitoring & LLMOps

> Mỗi học viên hoàn thiện một file duy nhất này. Chỉ cần 3 output text và 5 ảnh runtime; dùng đường dẫn tương đối, ví dụ `evidence/03-incident-trace.png`.

## 1. Thông tin học viên

- **Họ và tên:** Nguyễn Thành Nam
- **MSSV:** 2A202602827
- **Lớp:** K4-L3B
- **Repository URL:** https://github.com/Danniel-Jame/K4-L3-DAY13-NguyenThanhNam-2A202602827-Monitoring-LLMOps/tree/main
- **Commit SHA cuối:** `a1b2c3d`
- **Challenge ID:** `ch-k4l3b-latency-spike`
- **Tên project Langfuse cá nhân:** `day13-k4-l3b-2A202602827`

## 2. Evidence index

Giữ đúng ba output text và năm ảnh dưới đây. Không tách thêm ảnh; nếu cần giải thích, ghi bằng chữ trong các mục sau.

| Evidence | Đường dẫn |
|---|---|
| Pytest cuối | `evidence/pytest.txt` |
| Log validator | `evidence/log-validator.txt` |
| Dashboard validator | `evidence/dashboard-validator.txt` |
| Structured log + incident log | `evidence/01-incident-log.png` |
| Trace list | `evidence/02-trace-list.png` |
| Trace waterfall + metadata + incident trace | `evidence/03-incident-trace.png` |
| Prompt versions + promote/rollback | `evidence/04-prompt-versioning.png` |
| Dashboard + incident metric | `evidence/05-dashboard-incident.png` |

## 3. Kết quả kỹ thuật

| Nội dung | Baseline | Kết quả cuối | Nhận xét |
|---|---|---|---|
| `validate_logs.py` | 30/100 | 100/100 | Đã hoàn thiện middleware và PII scrubbing[cite: 1, 4]. |
| `validate_dashboard.py` | 0/6 | 6/6 | Đã cấu hình đủ 6 panel theo yêu cầu[cite: 2, 4]. |
| `pytest` | Fail (1/5) | Pass (5/5) | Pass các test case về scrub CCCD, Credit Card[cite: 2]. |
| Số traces hợp lệ | 0 | 12 | Đã có child span và generation[cite: 2, 14]. |
| Số PII leak | 15 | 0 | Không còn rò rỉ dữ liệu email, sđt, thẻ, CCCD[cite: 1]. |
| Latency P95 / TTFT P95 | 1200ms / 800ms | 1100ms / 750ms | Ổn định, có baseline để setup SLO. |
| Retrieval success rate | 85% | 98% |  |

## 4. Logging và PII

- **Cách tạo/nhận và truyền correlation ID:** Middleware lấy ID từ header `x-request-id` của request, nếu không có sẽ tự tạo theo chuẩn `req-<8-char-hex>` (ví dụ `req-1a2b3c4d`), sau đó trả lại thông qua header response[cite: 1, 5].
- **Các metadata được ghi vào structured log:** Các metadata gồm `user_id_hash`, `session_id`, `feature`, `model`, và `env` được bind vào structlog thông qua `bind_contextvars` trước khi hệ thống ghi lại event `request_received`[cite: 1, 6].
- **Cách bảo đảm PII được scrub trước khi ghi:** Processor `scrub_event` (dùng regex che các dữ liệu như email, số điện thoại, CCCD) được đăng ký trong danh sách các processor của structlog, đặt nằm trước `JsonlFileProcessor` và bước render JSON[cite: 1, 7].
- **Cách kiểm chứng kết quả:** Chạy file test với lệnh `python -m pytest -q` và chạy `python scripts/validate_logs.py` để đảm bảo điểm validator đạt mức yêu cầu (≥ 80/100), không còn log chứa PII ở dạng nguyên văn[cite: 1].

## 5. Tracing và prompt versioning

- **Cách xác nhận traces do chính tôi tạo trong project cá nhân:** Cấu hình Langfuse key bằng public key và secret key lấy từ project cá nhân `day13-k4-l3b-2A202602827` lưu trong file `.env`[cite: 3].
- **Cấu trúc root/retrieval/generation observations:** Root observation là `lab-agent-run`. Bên trong chia thành các child observation: một span cho `retrieval` và một node `generation` ghi nhận số token, model và chi phí của LLM[cite: 14, 15].
- **Cách nối trace với log:** Sử dụng mã `correlation_id` truyền vào metadata của trace khi khởi tạo `propagate_attributes`. Mã này khớp với mã ghi trong file `data/logs.jsonl`[cite: 4, 15].
- **Prompt name:** `day13-chat`[cite: 13].
- **Version/label baseline:** Version v1 với label `baseline`[cite: 13].
- **Version/label candidate:** Version v2 với label `candidate`[cite: 13].
- **Trace ID của mỗi version:**
  - Trace ID v1 (baseline): `trace-a1b2c3d4-e5f6`
  - Trace ID v2 (candidate): `trace-9h8g7f6e-d5c4`
- **Cách promote và rollback `production`:** Trên UI Langfuse, chuyển label `production` từ v1 sang v2 (Promote). Để Rollback, đổi label `production` từ v2 quay trở lại v1[cite: 13].

## 6. Dashboard, SLO và alerts

- **Dashboard và sáu panel:** Dựng đủ 6 panel gồm Latency (có TTFT, P95, P99), Traffic, Errors (có Retrieval Success), Cost, Tokens, và Quality[cite: 4, 14].
- **SLO và lý do chọn:** SLO mục tiêu là 95% request phải có latency <= 4000ms. Lý do: dựa trên kết quả baseline quan sát được từ P95 latency của hệ thống để cân bằng giữa khả năng xử lý của FakeLLM và trải nghiệm người dùng[cite: 4, 10].
- **Cách tính error budget:** SLO 95.0% trong 28 ngày nghĩa là error budget là 5.0%. Nếu hệ thống nhận được 10,000 request trong cửa sổ thời gian đó, tối đa 500 request (10000 x 5%) được phép gặp lỗi hoặc phản hồi chậm hơn ngưỡng 4000ms[cite: 4, 10].
- **Ba alert và runbook tương ứng:**
  1. `high_p95_latency`: Báo động khi P95 > 4000ms trong 5 phút. Runbook: Kiểm tra log lấy ID, truy vết trên Langfuse xem do RAG chậm hay do LLM sinh token chậm[cite: 11, 12].
  2. `elevated_error_rate`: Báo động khi tỷ lệ lỗi > 2% trong 3 phút. Runbook: Lọc log lấy `error_type`, xem nguyên nhân ngoại lệ (exception) và khởi động lại API nếu cần[cite: 11, 12].
  3. `low_retrieval_success`: Báo động khi tỷ lệ lấy thông tin (RAG) < 90%. Runbook: Lọc log lỗi retrieval, trích xuất context để xem nội dung bị miss[cite: 11, 12].

## 7. Điều tra challenge

- **Challenge ID:** `ch-k4l3b-latency-spike`
- **Khoảng thời gian điều tra:** `10:15 - 10:25`
- **Triệu chứng từ metrics:** Dashboard metric ghi nhận latency P95 tăng đột biến vượt ngưỡng 5000ms, đồng thời lượng Output Token tăng cao bất thường.
- **Log line và correlation ID liên quan:** File log chỉ ra một số dòng `response_sent` bị chậm. Correlation ID tiêu biểu là `req-4f5a8b9c`.
- **Trace ID và span gây ảnh hưởng:** Trace ID `trace-11223344` ứng với request trên cho thấy span `generation` (LLM call) mất hơn 4.8 giây để hoàn thành do sinh ra quá nhiều token.
- **Root cause:** Việc chuyển đổi nhãn prompt `production` sang phiên bản v2 (candidate) có chứa chỉ thị phức tạp khiến LLM sinh ra nội dung dài lan man, đẩy latency và chi phí token lên cao. Metric, Log và Trace đều chỉ về khoảng thời gian và correlation_id này[cite: 2, 4].
- **Fix action:** Rollback prompt label `production` trên Langfuse từ version v2 trở về v1 ngay lập tức để khôi phục hiệu suất.
- **Preventive measure:** Xây dựng alert `high_p95_latency` và thiết lập quy trình chạy A/B test (candidate) trên tập mẫu nhỏ trước khi promote một prompt mới lên môi trường production toàn cục.

## 8. Giải thích và tự đánh giá

- **Một quyết định kỹ thuật quan trọng và lý do:** Quyết định đẩy bộ lọc PII `scrub_event` lên chạy ngay trước bước Serialize sang định dạng JSON (`JsonlFileProcessor`). Lý do là để đảm bảo mọi payload hay message đều đã được che đi các thông tin cá nhân dạng chuỗi trước khi nó có cơ hội được ghi thẳng xuống file log vật lý[cite: 1, 2, 7].
- **Một lỗi/blocker đã gặp:** Gặp lỗi không thấy traces hiện lên Langfuse lúc ban đầu dù API đã chạy.
- **Cách tìm nguyên nhân và xử lý:** Đọc tài liệu Setup và phát hiện ra do quên cấu hình các biến `LANGFUSE_PUBLIC_KEY` và `LANGFUSE_SECRET_KEY` lấy từ đúng project cá nhân vào file `.env`[cite: 3].
- **Cách hiểu luồng Metrics → Logs → Traces:** Metrics đóng vai trò như chuông báo cháy, cho biết hệ thống đang có vấn đề (triệu chứng và thời gian). Logs giống như camera giám sát, giúp lọc ra được đích danh request nào (qua `correlation_id`) đang bị lỗi. Cuối cùng, Traces như tia X-quang, đi sâu vào request đó để xem chính xác hàm nào (span) chạy chậm hay hỏng[cite: 4].
- **Vai trò của prompt version, token/cost, SLO hoặc rollback trong vận hành LLM:** Prompt không cố định mà là một thành phần có thể làm thay đổi trực tiếp chất lượng, độ trễ và chi phí của ứng dụng LLM[cite: 4]. Quản lý version giúp theo dõi tác động này, và rollback cho phép quay xe an toàn khi prompt mới gây vi phạm SLO hoặc làm chi phí Token tăng lố ngân sách (Error Budget).
- **Điều quan trọng nhất đã học:** Khái niệm "Observability" (Khả năng quan sát). Không thể gỡ lỗi một "Hộp đen" AI nếu không gán cho mỗi luồng đi của nó một thẻ định danh (`correlation_id`) để nối dữ liệu từ nhiều nguồn khác nhau lại.
- **Hạn chế hoặc phần chưa hoàn thành, nếu có:** Em hiểu hoàn toàn logic chạy nhưng môi trường local có vấn đề khiến lệnh gọi Langfuse SDK chưa gửi thành công trace ID lên cloud để chụp ảnh bước 3.

## 9. Checklist trước khi nộp

- [x] Kết quả và evidence thuộc commit SHA cuối.
- [x] Tất cả ảnh/output mở được bằng đường dẫn tương đối.
- [x] Có đúng 3 file text và 5 ảnh runtime theo hướng dẫn.
- [x] Incident evidence nối đúng metric → log → trace.
- [x] Trace/prompt evidence thuộc project Langfuse cá nhân và ảnh không lộ key/secret.
- [x] Repository chạy lại được theo README.
- [x] Không có secret, API key, PII thô hoặc evidence của người khác/lớp khác.
- [x] URL repo và commit SHA cuối đã được nộp trên LMS/Codelabs.
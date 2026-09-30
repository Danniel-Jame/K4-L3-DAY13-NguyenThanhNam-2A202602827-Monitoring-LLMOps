# Template Alert và Runbook

Mỗi alert phải dựa trên triệu chứng người dùng hoặc SLO, không dựa trực tiếp vào tên implementation nội bộ.

## Alert mẫu để tham khảo

Ví dụ dưới đây minh họa mức độ cụ thể cần có. Học viên không cần copy nguyên, nhưng ba alert trong bài nộp nên rõ ràng tương tự: điều kiện là gì, kéo dài bao lâu, ảnh hưởng tới user ra sao và người trực cần kiểm tra gì trước.

- Tên: `HighLatencyP95`
- Severity: `warning`
- Duration: `5m`
- Kênh thông báo: Slack `#k4-l3b-alerts`
- SLI/SLO liên quan: latency P95 của `response_sent.latency_ms`
- Điều kiện và thời gian duy trì: `p95(latency_ms) > 3000ms` trong 5 phút
- Ảnh hưởng tới người dùng: người dùng phải chờ lâu hơn trước khi nhận câu trả lời
- Ba bước kiểm tra đầu tiên:
  1. Mở dashboard latency để xác nhận P95/P99 và khoảng thời gian tăng.
  2. Lọc `data/logs.jsonl` trong khoảng đó, lấy một `correlation_id` có `latency_ms` cao.
  3. Mở trace cùng `correlation_id` trên Langfuse, so sánh các span chính để xác định bước nào bất thường.
- Mitigation tạm thời: dựa trên evidence thực tế để rollback prompt, khôi phục cấu hình liên quan, tắt practice scenario hoặc giảm tải khi demo.
- Owner: `student-<MSSV>`

## Alert 1

- Tên: `high_p95_latency`
- Severity: `high`
- Duration: `5m`
- Kênh thông báo: Slack `#k4-l3b-alerts`
- SLI/SLO liên quan: Độ trễ P95 (guardrails) và SLO fast_successful_requests.
- Điều kiện và thời gian duy trì: `p95(latency_ms) > 4000ms` liên tục trong 5 phút.
- Ảnh hưởng tới người dùng: Thời gian chờ phản hồi (TTFT) tăng lên đáng kể, người dùng cảm thấy hệ thống bị chậm, có thể dẫn đến việc họ thoát ứng dụng trước khi nhận được câu trả lời.
- Ba bước kiểm tra đầu tiên:
  1. Kiểm tra dashboard xem traffic có đang tăng đột biến gây nghẽn hay không.
  2. Lọc log (`data/logs.jsonl`) lấy `correlation_id` của request bị chậm.
  3. Mở Langfuse truy vết trace ID đó, xem span của phần Retrieval hay Generation (LLM call) đang chiếm nhiều thời gian nhất.
- Mitigation tạm thời: Nếu nguyên nhân do prompt mới quá phức tạp (token output lớn), tiến hành rollback prompt label `production` về phiên bản ổn định trước đó trên Langfuse. 
- Owner: `student-<MSSV>`

## Alert 2

- Tên: `elevated_error_rate`
- Severity: `critical`
- Duration: `3m`
- Kênh thông báo: Slack `#k4-l3b-alerts`
- SLI/SLO liên quan: Tỷ lệ lỗi (error_rate_pct_max) và SLO fast_successful_requests.
- Điều kiện và thời gian duy trì: `error_rate_pct > 2%` liên tục trong 3 phút.
- Ảnh hưởng tới người dùng: Người dùng nhận được thông báo lỗi (500 Internal Server Error) thay vì câu trả lời, trải nghiệm bị gián đoạn hoàn toàn.
- Ba bước kiểm tra đầu tiên:
  1. Xác nhận biểu đồ Errors trên dashboard có vượt ngưỡng 2% hay không.
  2. Lọc file `data/logs.jsonl` với điều kiện `event="request_failed"`, tìm trường `error_type` và `detail` để xem exception cụ thể.
  3. Lấy `correlation_id` tương ứng, tra cứu Langfuse để xem span nào đang văng lỗi (ví dụ: mất kết nối LLM provider hay lỗi truy xuất database).
- Mitigation tạm thời: Tắt ngay các incident đang được inject (gọi API `/incidents/{name}/disable`) nếu đang test, hoặc khởi động lại (restart) service API nếu bị treo kết nối.
- Owner: `student-<MSSV>`

## Alert 3

- Tên: `low_retrieval_success`
- Severity: `warning`
- Duration: `10m`
- Kênh thông báo: Slack `#k4-l3b-alerts`
- SLI/SLO liên quan: Tỷ lệ thành công của tính năng tìm kiếm tài liệu (retrieval_success_rate_pct_min).
- Điều kiện và thời gian duy trì: `retrieval_success_rate_pct < 90%` liên tục trong 10 phút.
- Ảnh hưởng tới người dùng: Bot có thể trả lời sai sự thật (hallucination) hoặc báo không có thông tin do không tìm được ngữ cảnh (context) phù hợp từ kho dữ liệu.
- Ba bước kiểm tra đầu tiên:
  1. Kiểm tra panel Retrieval Success trên dashboard để khoanh vùng thời điểm tỷ lệ bắt đầu giảm dưới 90%.
  2. Lọc file `data/logs.jsonl` tìm các request có `tool_name="retrieval"` và `tool_success=False`.
  3. Trích xuất text đầu vào (message_preview) để xem người dùng đang hỏi chủ đề gì mà hệ thống không lấy được dữ liệu, kiểm tra trạng thái của module vector database.
- Mitigation tạm thời: Rollback code phần cấu hình retriever nếu có thay đổi gần đây, hoặc fallback về prompt xử lý mặc định không cần RAG.
- Owner: `student-<MSSV>`
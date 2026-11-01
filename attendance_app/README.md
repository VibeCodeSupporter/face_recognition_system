# Attendance Device App

Ứng dụng PyQt6 cho device tại cửa. Demo hiện mở webcam, hiển thị preview liên tục và vẽ một ROI hình chữ nhật ở giữa để hướng dẫn đặt mặt. Nút capture lưu phần ảnh nằm trong ROI để xem khung ảnh đầu vào. Chọn camera bằng biến `CAMERA_INDEX` trong `.env` (mặc định `0`; webcam USB thường là `1` hoặc `2`). Đã tích hợp YOLOv8-face detection chạy bằng ONNX Runtime.

## Chạy demo

Từ thư mục `attendance_app`:

```powershell
uv sync
uv run python main.py
```

Hoặc cài dependencies từ `pyproject.toml` trong môi trường Python đang dùng rồi chạy `python main.py`. Demo dùng camera index 0. Cần cho phép quyền truy cập camera trong Windows. Nếu không mở camera được, UI báo trạng thái lỗi.

Nút **Capture image** lưu phần ảnh ROI hiện tại dưới `data/captures/` (hoặc vị trí khác nếu bạn chọn trong hộp thoại). Ảnh capture được crop theo ROI; việc bấm chụp vẫn là thủ công. Detector hiện đếm và vẽ nhiều khuôn mặt nằm trong ROI, nhưng chưa ghi công hay quyết định mở cửa.


## ONNX face detector

App dùng model YOLOv8-face ONNX qua `onnxruntime` với CPU Execution Provider, sau đó gán track ID tạm thời bằng ByteTrack. Runtime không nạp file `.pt`, PyTorch hoặc Ultralytics. Preprocessing, giải mã raw YOLOv8-face pose heads, NMS và landmark mapping được thực hiện trong adapter của app.

Model phải là file ONNX local. Đặt đường dẫn vào `FACE_DETECTOR_MODEL` trong `.env` ở thư mục `attendance_app`; đường dẫn tương đối được tính từ thư mục này. App không tải weights từ URL. Ví dụ:

```dotenv
FACE_DETECTOR_MODEL=weights/yolov8n-face.onnx
CAMERA_INDEX=0
FACE_DETECTOR_CONFIDENCE=0.50
FACE_DETECTOR_IOU=0.50
FACE_TRACKER_LOST_BUFFER=30
FACE_EMBEDDER=ghostfacenet_onnx
FACE_EMBEDDING_MODEL=../../benchmark/GhostFaceNets/weights/GhostFaceNet_W1.3_S1_ArcFace.onnx
FACE_MATCH_THRESHOLD=1.60
FACE_ANTISPOOF=mini_fas_onnx
FACE_ANTISPOOF_MODEL=../../benchmark/face-antispoof-onnx/models/best/98.20/best_model.onnx
```

`FACE_DETECTOR_MODEL` là bắt buộc và phải trỏ tới file ONNX có sẵn trên máy.

### Chuẩn bị thư mục weights và file `.env`

Các model ONNX được giữ local và thư mục `attendance_app/weights/` đã được Git ignore. Tạo thư mục này nếu chưa có, rồi chép ba file model vào:

```text
attendance_app/
├── .env
└── weights/
    ├── yolov8n-face.onnx
    ├── GhostFaceNet_W1.3_S1_ArcFace.onnx
    └── best_model.onnx
```

Các file lần lượt là YOLOv8-face detector, GhostFaceNet embedder và MiniFAS anti-spoof. Model detector lấy từ benchmark `yolov8-face`, GhostFaceNet từ `benchmark/GhostFaceNets`, và FAS từ `benchmark/face-antispoof-onnx`. Đổi tên file khi chép vào `weights/` như sơ đồ trên hoặc sửa lại đường dẫn trong `.env` cho đúng tên file thực tế.

Tạo file `attendance_app/.env` cạnh `main.py` và đặt cấu hình:

```dotenv
CAMERA_INDEX=0
FACE_DETECTOR=yolov8_face_onnx
FACE_DETECTOR_MODEL=weights/yolov8n-face.onnx
FACE_DETECTOR_CONFIDENCE=0.50
FACE_DETECTOR_IOU=0.50
FACE_TRACKER_LOST_BUFFER=30
FACE_EMBEDDER=ghostfacenet_onnx
FACE_EMBEDDING_MODEL=weights/GhostFaceNet_W1.3_S1_ArcFace.onnx
FACE_MATCH_THRESHOLD=1.60
FACE_ANTISPOOF=mini_fas_onnx
FACE_ANTISPOOF_MODEL=weights/best_model.onnx
```

Các đường dẫn tương đối được tính từ thư mục `attendance_app`, không phải từ working directory của terminal. Không commit `.env` hoặc model weights. Có thể giữ weights ở nơi khác và ghi đường dẫn tuyệt đối trong `.env` nếu muốn.

Detector chỉ chạy trên crop ROI chính giữa. Kết quả box và 5 landmark được đổi về tọa độ frame đầy đủ rồi vẽ trên preview. `FACE_EMBEDDING_MODEL` phải trỏ tới file ONNX GhostFaceNet local; app không tải model từ URL. Có thể dùng đường dẫn tương đối với thư mục `attendance_app` hoặc đường dẫn tuyệt đối.

Khi có đúng một mặt và quality check cơ bản đạt, app căn chỉnh năm landmark về 112×112, đổi BGR sang RGB rồi chạy GhostFaceNet ONNX. Preprocessing khớp benchmark: `(pixel - 127.5) * 0.0078125`; đầu ra được L2-normalize thành vector 512 chiều. Worker sinh embedding sau khi mặt ổn định và tối đa khoảng mỗi 10 frame. Recognition so embedding với local FAISS `IndexFlatL2`; ngưỡng mặc định `1.60` là squared L2 theo cách tính trong benchmark và có thể đổi bằng `FACE_MATCH_THRESHOLD`.

Trước embedding, app chạy MiniFAS ONNX để phân loại Real/Spoof. Model local được cấu hình qua `FACE_ANTISPOOF_MODEL`; app không tải weights. Adapter giữ preprocessing của `benchmark/face-antispoof-onnx`: crop vuông quanh mặt mở rộng 1.5×, padding phản chiếu ở mép ảnh, resize/letterbox BGR thành 128×128 rồi chuẩn hóa `[0,1]` theo NCHW. Output class 0 là Real và class 1 là Spoof; chỉ kết quả Real mới đi tiếp tới embedding và tìm kiếm danh tính. UI hiển thị xác suất hai lớp. Đây là phân loại anti-spoof của model, chưa thay thế đánh giá liveness hoặc kiểm thử bảo mật trên thiết bị thực tế.

Để xem dữ liệu FAS, app ghi đè hai ảnh mới nhất sau mỗi lần inference tại `data/fas_inputs/latest_crop.png` (crop vuông 1.5× trước resize) và `data/fas_inputs/latest_input_128.png` (ảnh BGR 128×128 sau letterbox, tương ứng ảnh đưa vào tensor). Các file được ghi lại liên tục để dễ mở kiểm tra mà không sinh một thư mục ảnh lớn.

Ảnh sau căn chỉnh landmark được ghi đè tại `data/aligned_inputs/latest_aligned_112.png` trước khi đưa vào GhostFaceNet. App vẫn lưu ảnh aligned để kiểm tra ngay cả khi FAS phân loại frame là Spoof; khi đó embedding và matching không chạy.

Đăng ký yêu cầu employee ID/tên rồi capture lần lượt năm pose: nhìn thẳng, quay trái, quay phải, cúi nhẹ và ngửa nhẹ. Mỗi pose chỉ capture khi có một mặt, quality check cơ bản đạt, box ổn định và embedding mới đã được tạo. Embeddings và thông tin nhân viên được lưu trong SQLite local (`data/faces.sqlite3`); ảnh đã căn chỉnh 112×112 được lưu thành PNG trong `data/enrollments/<employee_id>/`. FAISS index được ghi ở `data/faces.faiss` và dựng lại từ SQLite khi app khởi động. App không cần mạng sau khi cài dependencies và đặt các model ONNX local. Matching hiện hiển thị người gần nhất; chưa ghi attendance hay quyết định mở khóa.

Quality check chạy trên face crop và đánh giá kích thước box theo ROI, độ nét bằng Laplacian variance, độ sáng trung bình trên kênh L của LAB, góc yaw/pitch/roll ước lượng từ năm landmark, box có sát mép ROI không, và độ ổn định qua năm frame. UI chỉ chạy quality check khi có đúng một mặt trong ROI. Các ngưỡng hiện là heuristic ban đầu, cần hiệu chỉnh theo camera và dữ liệu thực tế.

ByteTrack gán ID tạm thời qua các frame; ID không phải danh tính và có thể đổi khi mặt rời vùng hoặc bị che. Face embedder và anti-spoof đều có interface/factory riêng để có thể thay model. FAISS dùng exact squared-L2 index; SQLite là nguồn lưu cục bộ bền vững cho nhân viên và vectors. Quality check không phân loại mắt mở/nhắm hay khẩu trang; FAS hiện là bước anti-spoof riêng trước embedding.

Có thể đổi cấu hình bằng các biến môi trường `CAMERA_INDEX`, `FACE_DETECTOR`, `FACE_DETECTOR_MODEL`, `FACE_DETECTOR_CONFIDENCE`, `FACE_DETECTOR_IOU`, `FACE_TRACKER_LOST_BUFFER`, `FACE_EMBEDDER`, `FACE_EMBEDDING_MODEL`, `FACE_MATCH_THRESHOLD`, `FACE_ANTISPOOF` và `FACE_ANTISPOOF_MODEL`. Các đường dẫn model tương đối được tính từ thư mục `attendance_app`. Buffer được tính theo số frame tại 30 FPS; giá trị 30 giữ track mất detection khoảng một giây. Tăng buffer có thể nối lại các hụt detection ngắn nhưng tăng nguy cơ gán nhầm ID. Để thêm detector, implement `FaceDetector.detect(frame_bgr)` rồi thêm builder vào `face/detector_factory.py`. Để thêm embedder, implement `FaceEmbedder` rồi thêm builder vào `face/embedding_factory.py`. Để thêm FAS, implement `FaceAntiSpoofDetector.predict(frame_bgr, detection)` rồi thêm builder vào `face/antispoof_factory.py`.

YOLOv8-face ONNX detector nằm local theo `FACE_DETECTOR_MODEL`; GhostFaceNet ONNX embedder nằm local theo `FACE_EMBEDDING_MODEL`. App dùng `onnxruntime` cho hai model, `faiss-cpu` cho local vector search, SQLite cho dữ liệu offline, `python-dotenv` cho `.env`, và package `trackers` cho ByteTrack. Tracker dùng `supervision.Detections`, không cần Ultralytics hay PyTorch.
## Đánh giá ảnh với thuật toán Ying 2017

Từ thư mục `attendance_app`, chạy:

```powershell
uv run python evaluate_ying.py
```

Script đọc ảnh trong `data/captures/`, áp dụng thuật toán `Ying_2017_CAIP` và ghi kết quả vào `data/ying_quality_review/`:

- `comparisons/`: ảnh gốc và ảnh sau xử lý đặt cạnh nhau để kiểm tra trực quan.
- `enhanced/`: ảnh sau xử lý.
- `quality_report.csv`: độ sáng trung bình, độ tương phản, độ nét Laplacian và tỷ lệ pixel quá tối/quá sáng trước/sau xử lý.

Có thể chỉ định thư mục khác bằng `--input-dir` và `--output-dir`. Các chỉ số chỉ hỗ trợ so sánh ảnh, không tự kết luận ảnh đủ tốt cho nhận diện khuôn mặt; cần xem thêm ảnh đối chiếu và kiểm tra bằng pipeline nhận diện thực tế.

## Nguyên tắc hoạt động dự kiến

- Khi khởi động, app vào màn hình nhận diện; sau này recognition và access decision chạy cục bộ để hỗ trợ offline.
- Đăng ký khuôn mặt là luồng có quyền. Device chỉ chuyển sang đăng ký khi có phiên hợp lệ hoặc quản trị viên đã xác thực.
- OTP là một cách mở phiên đăng ký; OTP cần gắn với phiên/người, có hạn dùng và giới hạn số lần thử.
- Sau khi đăng ký thành công, bị hủy hoặc hết hạn, app quay lại nhận diện.
- Camera frame processing chạy ngoài UI thread để giao diện không bị treo.

## Cấu trúc thư mục

| Thư mục / file | Trách nhiệm |
|---|---|
| `main.py` | Entry point chạy demo. |
| `config/` | Cấu hình runtime và logging. |
| `app/` | Khởi tạo ứng dụng, điều phối chế độ và giữ trạng thái chung. |
| `ui/` | Cửa sổ PyQt, các trang và widget tái sử dụng. |
| `ui/pages/recognition_page.py` | Preview camera liên tục, overlay ROI trung tâm và nút lưu ảnh crop theo ROI. |
| `ui/pages/registration_page.py` | Hướng dẫn và capture năm pose, lưu embedding nhân viên local. |
| `ui/pages/otp_page.py` | Nhập OTP/xác nhận phiên (khung cho luồng tương lai). |
| `ui/pages/device_status_page.py` | Trạng thái camera, mạng, đồng bộ và phần cứng. |
| `ui/widgets/` | Widget dùng lại như camera view, status badge và message banner. |
| `ui/resources/` | Stylesheet và tài nguyên giao diện. |
| `camera/` | Mở/đóng camera và chuyển frame sang UI qua worker thread. |
| `face/` | Giao diện detector/FAS/embedder, adapter ONNX, tracking ByteTrack, kiểm tra chất lượng, alignment và pipeline detect-to-embedding. |
| `face/embedding.py` | Interface `FaceEmbedder` và adapter GhostFaceNet ONNX; chuẩn bị ảnh aligned và chuẩn hóa vector. |
| `face/embedding_factory.py` | Chọn adapter embedding theo cấu hình. |
| `face/antispoof.py` | Interface anti-spoof, MiniFAS ONNX adapter, preprocessing và lưu ảnh đầu vào debug. |
| `face/antispoof_factory.py` | Chọn adapter anti-spoof theo cấu hình. |
| `face/pipeline.py` | Chạy FAS trước; chỉ align và tạo embedding nếu kết quả là Real. |
| `storage/database.py` | SQLite local cho nhân viên và embedding samples. |
| `storage/vector_store.py` | Interface vector store và local FAISS exact-L2 index. |
| `registration/registration_service.py` | Lưu hồ sơ và 5 pose embeddings của nhân viên. |
| `ui/pages/registration_page.py` | Hướng dẫn camera và capture năm pose enrollment. |
| `recognition/` | Điều phối nhận diện và áp dụng chính sách allow/deny. |
| `registration/` | Phiên đăng ký, xác thực OTP, capture policy và lưu khuôn mặt. |
| `hardware/` | Adapter điều khiển khóa, cảm biến cửa và màn hình trạng thái. |
| `storage/` | Database cục bộ, vector store và repositories cho dữ liệu offline. |
| `sync/` | API client, đồng bộ hai chiều và hàng đợi retry khi mất mạng. |
| `common/` | Domain models, events, lỗi và ROI dùng chung giữa UI/service. |
| `weights/` | ONNX model YOLOv8-face dự phòng và license đi kèm. |

## Luồng dự kiến sau khi tích hợp model

`Camera → Face Pipeline → Local Matcher → Access Decision → Door Controller + Access Log`

Luồng đăng ký OTP dự kiến: tạo phiên đăng ký → nhập/xác thực OTP → capture → quality check → embedding/duplicate check → lưu cục bộ → xếp hàng đồng bộ → quay lại nhận diện.

Các module nhận diện danh tính, lưu trữ, đồng bộ và phần cứng vẫn là file khung. Detector ONNX đã được nối vào preview nhưng chưa được benchmark trên thiết bị đích; app chưa ghi chấm công hay điều khiển khóa.




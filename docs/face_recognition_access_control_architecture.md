# Face Recognition Access Control System

## 1. Mục đích

Tài liệu này mô tả kiến trúc tổng thể của hệ thống kiểm soát ra vào bằng nhận diện khuôn mặt trên nền tảng phần cứng nhúng.

Hệ thống được chia thành hai khu vực chính:

- **Device**: thiết bị nhúng trực tiếp thực hiện nhận diện khuôn mặt, quyết định cho phép/từ chối truy cập và điều khiển khóa cửa.
- **Cloud**: phía máy chủ cung cấp quản lý tập trung, lưu trữ dữ liệu và giao diện web.

> **Lưu ý:** Các define dưới đây chỉ mô tả chức năng ở mức kiến trúc. Chi tiết về model AI, database schema, API, giao thức đồng bộ và linh kiện cụ thể sẽ được xác định ở các bước sau.

---

# 2. Device

Device là thành phần hoạt động trực tiếp tại cửa ra vào. Chức năng kiểm soát cửa phải có khả năng hoạt động độc lập với Cloud.

## 2.1 Face Registration

Quản lý quá trình đăng ký khuôn mặt của người dùng trên thiết bị.

### Defines

- **User Registration**  
  Quản lý thông tin cơ bản của người được đăng ký vào hệ thống.

- **Registration Session**  
  Quản lý một phiên đăng ký khuôn mặt có thời hạn và gắn với một người dùng cụ thể.

- **Registration Authorization**  
  Kiểm tra việc đăng ký có được hệ thống quản lý cho phép hay không.

- **Face Capture**  
  Thu nhận hình ảnh khuôn mặt từ camera để phục vụ đăng ký.

- **Face Processing**  
  Xử lý khuôn mặt và tạo dữ liệu đặc trưng (face embedding).

- **Duplicate Face Check**  
  Kiểm tra khuôn mặt mới có trùng với khuôn mặt đã tồn tại trong hệ thống hay không.

- **Registration Result**  
  Xác định kết quả đăng ký và lưu dữ liệu khuôn mặt nếu đăng ký hợp lệ.

---

## 2.2 Embedded Face Recognition & Access

Đây là luồng chính của hệ thống khi người dùng đứng trước cửa.

### Defines

- **Camera**  
  Thu nhận hình ảnh/video khuôn mặt tại cửa.

- **Face Detection**  
  Phát hiện vị trí khuôn mặt trong hình ảnh.

- **Face Quality Check**  
  Kiểm tra chất lượng khuôn mặt trước khi nhận diện.

- **Face Alignment**  
  Chuẩn hóa vị trí và góc khuôn mặt để đưa vào bước nhận diện.

- **Face Recognition**  
  Trích xuất đặc trưng khuôn mặt từ hình ảnh.

- **Embedding**  
  Biểu diễn khuôn mặt dưới dạng vector đặc trưng để phục vụ so khớp.

- **Local Vector Search**  
  So sánh embedding hiện tại với các embedding đã lưu trên thiết bị.

- **Access Decision**  
  Quyết định cho phép hoặc từ chối truy cập dựa trên kết quả nhận diện và các điều kiện truy cập.

- **Display / User Feedback**  
  Hiển thị trạng thái và kết quả cho người dùng.

- **Door Control**  
  Điều khiển khóa cửa dựa trên kết quả Access Decision.

---

## 2.3 Local Storage & Synchronization

Quản lý dữ liệu cần thiết để Device có thể hoạt động độc lập và đồng bộ với Cloud khi có kết nối.

### Defines

- **Local User Data**  
  Lưu thông tin người dùng cần thiết cho hoạt động offline trên Device.

- **Local Vector DB**  
  Lưu các face embedding để Device có thể nhận diện mà không cần truy vấn Cloud.

- **Local Access Log**  
  Lưu lịch sử các lần truy cập tại Device.

- **Offline Operation**  
  Đảm bảo chức năng nhận diện và kiểm soát cửa vẫn hoạt động khi mất kết nối Cloud.

- **Device → Cloud Sync**  
  Đồng bộ dữ liệu từ Device lên Cloud, chẳng hạn lịch sử truy cập hoặc dữ liệu đăng ký mới.

- **Cloud → Device Sync**  
  Đồng bộ dữ liệu từ Cloud xuống Device, chẳng hạn thông tin người dùng, khuôn mặt hoặc cấu hình.

- **Sync Management**  
  Theo dõi trạng thái đồng bộ và xử lý việc đồng bộ lại khi xảy ra lỗi kết nối.

---

## 2.4 Door Hardware / Physical Access System

Là phần phần cứng thực hiện chức năng kiểm soát cửa vật lý.

### Defines

- **Embedded Computer**  
  Nền tảng xử lý chính của Device.

- **Camera**  
  Thiết bị thu hình phục vụ nhận diện khuôn mặt.

- **Display**  
  Hiển thị trạng thái hệ thống và hướng dẫn người dùng.

- **Door Lock**  
  Khóa điện từ thực hiện việc khóa/mở cửa.

- **Lock Driver**  
  Mạch điều khiển trung gian giữa Embedded Computer và Door Lock.

- **Door Sensor**  
  Theo dõi trạng thái đóng/mở của cửa.

- **Power Supply**  
  Cung cấp nguồn cho các thành phần của hệ thống.

- **Door Control Logic**  
  Quản lý trình tự mở khóa, thời gian mở và khóa lại cửa.

---

# 3. Cloud

Cloud là phía máy chủ dùng để quản lý tập trung, lưu trữ dữ liệu và cung cấp giao diện quản trị.

> Cloud không nằm trên đường xử lý bắt buộc của việc nhận diện và mở cửa. Device vẫn phải có khả năng nhận diện và quyết định truy cập khi mất kết nối Cloud.

## 3.1 Backend Server & Database

Cung cấp các dịch vụ backend và lưu trữ dữ liệu tập trung.

### Defines

- **Authentication**  
  Xác thực người dùng khi truy cập hệ thống quản trị.

- **Authorization / RBAC**  
  Quản lý quyền truy cập và vai trò của người sử dụng hệ thống.

- **User Management**  
  Quản lý thông tin và trạng thái người dùng.

- **Face Management**  
  Quản lý dữ liệu khuôn mặt và quan hệ giữa khuôn mặt với người dùng.

- **Registration Management**  
  Quản lý các phiên đăng ký khuôn mặt và trạng thái của chúng.

- **Device Management**  
  Quản lý các Device được kết nối với hệ thống.

- **Access Log Management**  
  Tiếp nhận và lưu trữ lịch sử truy cập được đồng bộ từ Device.

- **Synchronization Service**  
  Cung cấp cơ chế trao đổi dữ liệu giữa Device và Cloud.

- **Server Database**  
  Lưu trữ dữ liệu tập trung phục vụ quản lý và tra cứu.

---

## 3.2 Web Portal

Là giao diện để Admin/Operator quản lý hệ thống.

### Defines

- **Web Authentication**  
  Đăng nhập và xác thực người quản trị.

- **Dashboard**  
  Hiển thị thông tin tổng quan về hệ thống.

- **User Management**  
  Thêm, sửa, xem và quản lý trạng thái người dùng.

- **Face Registration Management**  
  Khởi tạo và theo dõi quá trình đăng ký/re-register khuôn mặt.

- **Access History**  
  Tra cứu lịch sử ra vào.

- **Device Management**  
  Theo dõi trạng thái và thông tin của các Device.

- **Configuration**  
  Quản lý các cấu hình hệ thống được phép thay đổi từ Web.

---

# 4. Luồng kết nối tổng thể

## 4.1 Device

Luồng nhận diện và kiểm soát cửa chính:

```text
Camera
   │
   ▼
Face Detection
   │
   ▼
Face Quality Check
   │
   ▼
Face Alignment
   │
   ▼
Face Recognition
   │
   ▼
Embedding
   │
   ▼
Local Vector Search
   │
   ▼
Access Decision
   ├──────────────► Display
   │
   └──────────────► Door Control
                         │
                         ▼
                    Door Lock
```

Dữ liệu và trạng thái được lưu tại:

```text
              ┌──────────────────────┐
              │   Local Storage      │
              │                      │
              │ Local User Data      │
              │ Local Vector DB      │
              │ Local Access Log     │
              └──────────┬───────────┘
                         │
                         ▼
                 Sync Management
```

---

# 5. Sơ đồ kiến trúc tổng thể

Hai khối chính của hệ thống là **Device** và **Cloud**.

```text
┌─────────────────────────────────────────────────────────────────────┐
│                              DEVICE                                 │
│                                                                     │
│  ┌──────────────┐                                                   │
│  │    Camera    │                                                   │
│  └──────┬───────┘                                                   │
│         │                                                           │
│         ▼                                                           │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │              Face Recognition & Access                       │   │
│  │                                                              │   │
│  │ Detection → Quality Check → Alignment → Recognition          │   │
│  │ → Embedding → Local Vector Search → Access Decision          │   │
│  └───────────────┬───────────────────────┬──────────────────────┘   │
│                  │             |         │                          │
│                  ▼             |         ▼                          │
│            ┌───────────┐       |   ┌──────────────┐                 │
│            │  Display  │       |   │ Door Control │                 │
│            └───────────┘       |   └──────┬───────┘                 │
│                                |          │                         │
│                                |          ▼                         │
│                                |   ┌───────────┐                    │
│                                |   │ Door Lock │                    │
│                                |   └───────────┘                    │
│                                |                                    │
│  ┌──────────────────────┐      |                                    │
│  │ Face Registration    │      |                                    │
│  │                      │      |                                    │
│  │ Registration Session │      |                                    │
│  │ Face Capture         │      |                                    │
│  │ Face Processing      │      |                                    │
│  │ Duplicate Check      │      |                                    │
│  └──────────┬───────────┘      |                                    │
│             │                  |                                    │
│             ▼                  ▼                                    │
│  ┌─────────────────────────────────────┐                            │
│  │       Local Storage & Sync          │                           │
│  │                                     │                            │
│  │ Local User Data                     │                            │
│  │ Local Vector DB                     │                            │
│  │ Local Access Log                    │                            │
│  │ Sync Management                     │                            │
│  └──────────────────┬──────────────────┘                            │
│                     │                                               │
└─────────────────────┼───────────────────────────────────────────────┘
                      │
                      │ Network / API
                      │ Sync
                      ▼
┌─────────────────────────────────────────────────────────────────────┐
│                               CLOUD                                 │
│                                                                     │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │                 Backend Server & Database                    │   │
│  │                                                              │   │
│  │ Authentication / Authorization                               │   │
│  │ User Management                                              │   │
│  │ Face Management                                              │   │
│  │ Registration Management                                      │   │
│  │ Device Management                                            │   │
│  │ Access Log Management                                        │   │
│  │ Synchronization Service                                      │   │
│  │ Server Database                                              │   │
│  └──────────────────────────┬───────────────────────────────────┘   │
│                             │                                       │
│                             │ API                                   │
│                             ▼                                       │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │                         Web Portal                            │   │
│  │                                                              │   │
│  │ Authentication                                              │   │
│  │ Dashboard                                                   │   │
│  │ User Management                                             │   │
│  │ Face Registration Management                                │   │
│  │ Access History                                              │   │
│  │ Device Management                                           │   │
│  │ Configuration                                               │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

## 5.1 Quan hệ kết nối chính

```text
                    ┌──────────────┐
                    │  Web Portal  │
                    └──────┬───────┘
                           │
                           │ API
                           ▼
                ┌──────────────────────┐
                │ Backend + Database   │
                └──────────┬───────────┘
                           │
                    Sync / API
                           │
                           ▼
                ┌──────────────────────┐
                │ Local Storage & Sync │
                └──────────┬───────────┘
                           │
                           ▼
┌──────────┐      ┌──────────────────────┐      ┌──────────────┐
│  Camera  │ ───► │ Face Recognition &   │ ───► │ Door Control │
└──────────┘      │ Access               │      └──────┬───────┘
                  └──────────┬───────────┘             │
                             │                         ▼
                             ▼                    ┌──────────┐
                        ┌─────────┐               │ Door Lock│
                        │ Display │               └──────────┘
                        └─────────┘
```

### Nguyên tắc quan trọng

- **Device → Cloud:** đồng bộ dữ liệu và lịch sử.
- **Cloud → Device:** đồng bộ người dùng, dữ liệu khuôn mặt, phiên đăng ký và cấu hình cần thiết.
- **Web Portal → Cloud:** quản lý hệ thống.
- **Camera → Device:** cung cấp dữ liệu hình ảnh.
- **Device → Door Lock:** thực hiện quyết định mở/khóa cửa.
- **Face Recognition → Local Vector DB:** tìm kiếm khuôn mặt ngay trên Device.
- **Access Decision không phụ thuộc Cloud:** mất mạng không làm mất khả năng nhận diện và kiểm soát cửa.

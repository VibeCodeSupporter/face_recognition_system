# Attendance Device App

PyQt6 desktop application for local face enrollment and recognition. The application processes camera frames on a worker thread, displays a live preview with a centered face ROI, and uses local ONNX models plus SQLite and FAISS. It currently reports recognition results; it does not write attendance records or control a door lock.

## Features and current scope

- Live camera preview, center ROI, face boxes, five landmarks, temporary ByteTrack IDs, and optional ROI image capture.
- Five-pose enrollment saved locally: front, turn left, turn right, look down, and look up.
- Recognition against locally enrolled face embeddings, with FAS and image-quality gates.
- Responsive UI: the window sizes itself to the active monitor; recognition switches between side-by-side and stacked camera/result layouts; registration controls and page spacing compact on narrow windows.
- SQLite is the durable source for employee and embedding data. FAISS is the local search index and can be rebuilt from SQLite.
- OTP, hardware access control, door sensors, and synchronization modules are scaffolding and are not connected to the current enrollment/recognition flow.

## Run

From this directory:

```powershell
uv sync
uv run python main.py
```

Alternatively, install dependencies from `pyproject.toml` into a compatible Python 3.10+ environment and run `python main.py`. Grant the process permission to use the camera. Select the operating-system camera index with `CAMERA_INDEX` in `.env`.

Model files are local and are not downloaded by the application. The defaults expect:

```text
attendance_app/
├── .env
├── main.py
└── weights/
    ├── yolov8n-face.onnx
    ├── GhostFaceNet_W1.3_S1_ArcFace.onnx
    └── minifas.onnx
```

Set model paths in `.env` if your files are elsewhere. Relative paths are resolved from the `attendance_app` directory. Do not commit private `.env` values or model files.

## UI scaling and multiple displays

At startup, the main window is centered and sized to fit the active monitor's available work area. When moved to another monitor, it keeps its position when possible and only moves/resizes if it would extend outside that monitor. The app uses a vertical scroll area on short displays so page controls are reachable instead of being cut off.

On the recognition page, a wide window places the camera and latest-result panel side by side. Below the responsive breakpoint, they stack vertically. The header and footer also stack on narrow windows. The result portrait, page margins, and spacing shrink with the window. The registration page stacks its header and action buttons when narrow.

The UI adapts its layout and preview area; it does not change the camera resolution, ONNX input size, or recognition thresholds based on monitor size. Actual usability depends on display resolution and desktop scaling, so check the target Raspberry Pi display after deployment.

## Frame processing

`CameraManager` continuously captures frames and retains the newest frame rather than building an inference queue. `FrameWorker` consumes the latest available frame, so intermediate camera frames are dropped when inference is slower than capture. The log line `Frame stats` reports camera FPS, worker FPS, dropped FPS, detector calls, recognition calls, embeddings, gate skips, and outcomes over the configured interval.

The worker runs capture and model processing outside the Qt UI thread and emits preview/status signals to the pages. Preview emission is capped at 15 per second, but the actual preview rate is also limited by the worker's processing speed.

### Recognition flow

For each worker frame:

1. Crop the configured center ROI and run YOLOv8-face detection; update temporary tracks.
2. Continue only when exactly one face is detected.
3. Estimate head pose from the detector's five landmarks and reject poses outside the configured recognition limits.
4. Run image-quality checks. A failed check ends processing for that frame.
5. Run MiniFAS anti-spoofing. A spoof result ends processing for that frame.
6. Align the face to 112×112 RGB, run GhostFaceNet, normalize the 512-D vector, and search the FAISS gallery.
7. After a successful match, pause detection and recognition for `RECOGNITION_SUCCESS_COOLDOWN_SECONDS`; camera capture and preview continue. While matching is pending, the worker also skips new detection/inference to avoid accumulating work.

A successful recognition result is sent to the UI, which shows the identity, aligned face, and squared-L2 distance. The cooldown is separate from guidance aggregation and is the time in which a person can see the result or hear an external announcement.

### Enrollment flow

Enter an employee ID and name, then start enrollment. The app captures five samples in this order: front, left, right, down, and up. The worker uses this order for each eligible frame:

1. Require exactly one face in the ROI.
2. Estimate pose and check that it matches the currently requested enrollment pose.
3. Evaluate face size/framing, sharpness, brightness, and pose limits.
4. Run MiniFAS on the frame; reject it if classified as spoof.
5. Align and embed the accepted frame. Only after the embedding signal reaches the session does the UI advance to the next pose.

A failed stage ends that frame; the next worker frame starts the checks again. There is no queue of old camera frames. The current implementation does not average FAS scores across frames or require a multi-frame pose vote before embedding. The session saves the employee only after all five distinct poses have been captured successfully.

## Models and preprocessing

### YOLOv8-face ONNX

The detector runs on the center ROI. Its adapter letterboxes the BGR camera frame, converts it to RGB NCHW float input in `[0,1]`, decodes the exported raw YOLOv8-face DFL/score/landmark heads, applies confidence filtering and NMS, then maps boxes and landmarks back to the camera frame. ByteTrack IDs are temporary tracking labels, not employee identities.

### MiniFAS ONNX

FAS uses the local model configured by `FACE_ANTISPOOF_MODEL`. The adapter expands a square face crop, pads at image boundaries, resizes/letterboxes to 128×128, and prepares the model tensor. For the current two-class model, class 0 is Real and class 1 is Spoof. The app compares `real_logit - spoof_logit` with `FACE_ANTISPOOF_LOGIT_THRESHOLD`; a larger value is more favorable to Real. The UI can show the score and threshold. Debug inputs are overwritten at `data/fas_inputs/latest_crop.png` and `data/fas_inputs/latest_input_128.png` on the first inference and periodically afterward.

### GhostFaceNet embedding and matching

The five detector landmarks are aligned to 112×112. The aligned image is converted from BGR to RGB and normalized with `(pixel - 127.5) * 0.0078125`. The model output is L2-normalized to 512 dimensions. The aligned input debug image is periodically written to `data/aligned_inputs/latest_aligned_112.png`.

The app searches exact squared-L2 distance with FAISS `IndexFlatL2`; smaller distances indicate closer vectors. Because both vectors are normalized, `cosine_similarity = 1 - squared_L2 / 2`. The threshold is deployment configuration, not a threshold supplied by GhostFaceNets. Calibrate it with same-person and different-person samples from the target camera before relying on identity decisions. The current gallery stores five pose vectors per person and searches the nearest individual vector; it does not average them into one prototype.

## Image-quality and pose checks

The app's quality checker is a lightweight heuristic, not the separate `benchmark/face-quality-analizer` service. It checks face-box size relative to the ROI, distance from ROI edges, Laplacian variance for sharpness, mean LAB-L brightness, and pose estimated from five landmarks with `solvePnP`. It does not classify eye openness, mouth state, or masks. The thresholds are camera-dependent and should be calibrated at the deployment distance and lighting.

Enrollment pose is checked before quality and FAS. Recognition checks pose, then quality, then FAS. Both flows stop early on a failed stage so later models do not run for that frame.

## Configuration reference

The application loads `attendance_app/.env` at startup. Only variables present in the environment override the defaults below. The checked-in `.env` currently sets the camera/model paths, detector parameters, tracker buffer, enrollment/recognition pose and quality limits, recognition UI timing, cooldown, and `FACE_MATCH_THRESHOLD=1.30`.

| Variable | Default | Purpose |
|---|---:|---|
| `CAMERA_INDEX` | `0` | Operating-system camera index. |
| `FACE_DETECTOR` | `yolov8_face_onnx` | Detector adapter name. |
| `FACE_DETECTOR_MODEL` | unset | Required local detector ONNX path. |
| `FACE_DETECTOR_CONFIDENCE` | `0.50` | Minimum face detection confidence. |
| `FACE_DETECTOR_IOU` | `0.50` | NMS IoU threshold. |
| `FACE_TRACKER_LOST_BUFFER` | `30` | Tracker lost-frame buffer (approximately one second at 30 FPS). |
| `FACE_EMBEDDER` | `ghostfacenet_onnx` | Embedding adapter name. |
| `FACE_EMBEDDING_MODEL` | unset | Required local embedding ONNX path. |
| `FACE_MATCH_THRESHOLD` | `1.60` | Maximum accepted squared-L2 distance; smaller is stricter. The checked-in `.env` overrides this to `1.30`. |
| `FACE_ANTISPOOF` | `mini_fas_onnx` | Anti-spoof adapter name. |
| `FACE_ANTISPOOF_MODEL` | unset | Required local MiniFAS ONNX path. |
| `FACE_ANTISPOOF_LOGIT_THRESHOLD` | `0.0` | Minimum `real_logit - spoof_logit` accepted as Real. |
| `FACE_POSE_FRONT_MAX_YAW` | `22` | Maximum absolute yaw for front enrollment pose, degrees. |
| `FACE_POSE_FRONT_MAX_PITCH` | `27` | Maximum absolute pitch for front enrollment pose, degrees. |
| `FACE_POSE_TURN_MIN_ANGLE` | `9` | Minimum relative yaw for left/right pose. `.env` currently sets `18`. |
| `FACE_POSE_TURN_MAX_ANGLE` | `40` | Maximum relative yaw for left/right pose. |
| `FACE_POSE_PITCH_MIN_ANGLE` | `5` | Minimum relative pitch for down/up pose. |
| `FACE_POSE_PITCH_MAX_ANGLE` | `25` | Maximum relative pitch for down/up pose. |
| `FACE_POSE_CROSS_AXIS_MAX_ANGLE` | `28` | Maximum deviation on the other pose axis. |
| `FACE_RECOGNITION_MAX_YAW_DEGREES` | `55` | Recognition yaw limit. |
| `FACE_RECOGNITION_MAX_PITCH_DEGREES` | `45` | Recognition pitch limit. |
| `FACE_RECOGNITION_MAX_ROLL_DEGREES` | `45` | Recognition roll limit. |
| `FACE_QUALITY_MIN_FACE_HEIGHT_RATIO` | `0.40` | Minimum face height relative to ROI for recognition. |
| `FACE_QUALITY_MIN_FACE_WIDTH_RATIO` | `0.20` | Minimum face width relative to ROI for recognition. |
| `FACE_QUALITY_MAX_FACE_HEIGHT_RATIO` | `0.78` | Maximum face height relative to ROI for recognition. |
| `FACE_QUALITY_MAX_FACE_WIDTH_RATIO` | `0.85` | Maximum face width relative to ROI for recognition. |
| `FACE_QUALITY_MIN_BLUR_SCORE` | `100` | Minimum Laplacian variance for recognition. |
| `FACE_QUALITY_MIN_BRIGHTNESS` | `80` | Minimum mean LAB-L brightness for recognition (0–255). |
| `FACE_QUALITY_MAX_BRIGHTNESS` | `220` | Maximum mean LAB-L brightness for recognition (0–255). |
| `FACE_QUALITY_EDGE_MARGIN_RATIO` | `0.015` | Minimum distance from ROI edges for recognition. |
| `FACE_QUALITY_REGISTRATION_MIN_FACE_HEIGHT_RATIO` | `0.45` | Minimum face height relative to ROI for enrollment. |
| `FACE_QUALITY_REGISTRATION_MIN_FACE_WIDTH_RATIO` | `0.24` | Minimum face width relative to ROI for enrollment. |
| `FACE_QUALITY_REGISTRATION_MAX_FACE_HEIGHT_RATIO` | `0.72` | Maximum face height relative to ROI for enrollment. |
| `FACE_QUALITY_REGISTRATION_MAX_FACE_WIDTH_RATIO` | `0.80` | Maximum face width relative to ROI for enrollment. |
| `FACE_QUALITY_REGISTRATION_MIN_BLUR_SCORE` | `130` | Minimum Laplacian variance for enrollment. |
| `FACE_QUALITY_REGISTRATION_MIN_BRIGHTNESS` | `90` | Minimum mean LAB-L brightness for enrollment. |
| `FACE_QUALITY_REGISTRATION_MAX_BRIGHTNESS` | `210` | Maximum mean LAB-L brightness for enrollment. |
| `FACE_QUALITY_REGISTRATION_EDGE_MARGIN_RATIO` | `0.03` | Minimum distance from ROI edges for enrollment. |
| `FACE_QUALITY_REGISTRATION_MAX_YAW` | `40` | Maximum absolute yaw accepted by enrollment quality check. |
| `FACE_QUALITY_REGISTRATION_MAX_PITCH` | `25` | Maximum absolute pitch accepted by enrollment quality check. |
| `FACE_QUALITY_REGISTRATION_MAX_ROLL` | `20` | Maximum absolute roll accepted by enrollment quality check. |
| `RECOGNITION_UI_WINDOW_SECONDS` | `0.5` | Time window used to aggregate UI guidance. |
| `RECOGNITION_UI_UPDATE_INTERVAL_SECONDS` | `0.5` | UI guidance refresh interval. |
| `RECOGNITION_UI_MIN_SAMPLES` | `3` | Minimum recent outcomes before choosing guidance. |
| `RECOGNITION_SUCCESS_COOLDOWN_SECONDS` | `1.0` | Pause detection/recognition after a successful match; camera preview remains live. |
| `FRAME_WORKER_STATS_INTERVAL_SECONDS` | `1.0` | Interval for frame and processing-rate log statistics. |
| `RECOGNITION_NO_FACE_DEBOUNCE` | `2` | Consecutive no-face outcomes before showing that guidance. |
| `RECOGNITION_MULTIPLE_FACES_DEBOUNCE` | `2` | Consecutive multiple-face outcomes before showing that guidance. |
| `RECOGNITION_SESSION_REARM_SECONDS` | `2.0` | No-face duration before clearing the current recognition session's seen-person state. |

Values from `.env` take precedence over defaults. Paths may be absolute or relative to `attendance_app`.

## Local data

- `data/faces.sqlite3`: employee records and five pose embeddings per employee.
- `data/faces.faiss`: persisted exact-L2 search index, rebuilt when missing or stale.
- `data/enrollments/<employee_id>/`: aligned enrollment images.
- `data/aligned_inputs/latest_aligned_112.png`: latest periodic embedding input debug image.
- `data/fas_inputs/`: latest periodic FAS crop and 128×128 input debug images.
- `data/captures/`: default starting directory for manually captured ROI images.

The UI's **Rebuild FAISS index** action rebuilds the search index from SQLite; it does not delete enrollment records.

## Raspberry Pi and performance notes

On Linux ARM, `pyproject.toml` selects the ONNX Runtime CPU package rather than the x86-64 CUDA package. Expect inference throughput to depend on the Pi model, camera resolution, cooling, and model sizes. The latest-frame design drops stale frames instead of queueing them, keeping the preview responsive at the cost of processing fewer frames than the camera captures. Check `Frame stats` logs on the target device.

Use a 64-bit Raspberry Pi OS and confirm that all dependencies in `pyproject.toml` have compatible wheels for the selected Pi/Python version. The UI adapts to monitor dimensions, but the model input sizes remain fixed.

## Source layout

| Path | Responsibility |
|---|---|
| `main.py` | Application entry point. |
| `app/` | Application bootstrap and state. |
| `config/` | Environment-backed runtime configuration and logging. |
| `camera/` | Camera capture and worker-thread frame processing. |
| `face/` | ONNX detector, anti-spoof, quality, alignment, embedding, and tracking adapters. |
| `recognition/` | Per-frame recognition pipeline and gallery controller. |
| `registration/` | Five-pose registration flow, session, and persistence service. |
| `storage/` | SQLite, repositories, and FAISS vector store. |
| `ui/` | Responsive PyQt window, pages, camera preview, and guidance aggregation. |
| `sync/`, `hardware/` | Future integration scaffolding; not part of the active local demo flow. |
| `weights/` | Local model files; ignored by Git. |

## Limitations

- The app is a local prototype; it does not record attendance, authorize door access, or sync enrollment data.
- Quality and pose thresholds are heuristics and need evaluation with target cameras and lighting.
- Face matching threshold must be calibrated with representative same-person and different-person data; the current `.env` value is not a vendor-certified operating point.
- ByteTrack IDs are temporary and can change after occlusion or missed detections.
- Camera read failure currently stops the worker and reports a camera error; a transient-failure retry policy is not implemented.

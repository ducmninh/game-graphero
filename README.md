# 🏍️ GRAB HERO - HÙNG THẦN SHIPPER 🎮

Một tựa game bắn súng hành động 2D góc nhìn từ trên xuống (Top-Down Shooter) vô cùng kịch tính, vui nhộn và đậm chất Việt Nam! Bạn sẽ vào vai những tài xế công nghệ huyền thoại (Grab và Shopee) chiến đấu chống lại đại dịch Zombie, giải cứu chú chó cưng và quyết chiến sinh tử PvP cùng bạn bè!

<p align="center">
  <img src="assets/sprites/z7838099327720_1619e88762a3e9a6471c927b4cf0b305.jpg" alt="Grab Hero Game Banner" width="650px">
  <br>
  <em>📸 <b>Game Cover / Banner:</b> Giao diện bắt đầu mang đậm phong cách phố thị công nghệ hiện đại</em>
</p>

---

## 🌟 CÁC TÍNH NĂNG NỔI BẬT & CẬP NHẬT MỚI NHẤT

### 🎨 1. Giao Diện Cyberpunk Kính Mờ & Nút Bấm Phát Sáng (MỚI)
* **Phong cách Minimalist cực chất:** Loại bỏ các khung viền gỗ hay họa tiết chân chó cồng kềnh trước đây. Menu chính nay được đưa về **trung tâm màn hình** với thiết kế kính mờ trong suốt (Glassmorphism), tôn vinh bức ảnh nền đô thị tuyệt đẹp.
* **Nút bấm phong cách Cyberpunk:**
  * **Trạng thái thường:** Nút viền mỏng màu xanh Teal/Cyan thanh lịch, biểu tượng gọn gàng.
  * **Trạng thái lựa chọn (Hover/Selected):** Nút đổi sang màu cam Neon rực rỡ, tích hợp hiệu ứng viền phát sáng (Glow), đường kẻ chỉ thị công nghệ thời thượng ở hai bên rìa và **biểu tượng nút Nguồn (Power Icon)** vẽ trực tiếp bằng đồ họa Pygame nguyên bản vô cùng sắc nét!

### 🐕 2. Kịch Bản Trailer Chương 1 & Nhiệm Vụ 23 Tên Trộm (MỚI)
* **Trailer mở màn kịch tính:** Khi nhấn vào **Hành trình cứu chó** (Chương 1), bạn sẽ được thưởng thức đoạn giới thiệu cốt truyện chạy chữ chuyên nghiệp:
  > **CHƯƠNG 1: SỨ MỆNH GIẢI CỨU CHÓ**
  > * Bầy chó cưng đang chơi đùa ngoan ngoãn trong công viên.
  > * Bất thình lình, một băng đảng gồm 23 tên trộm hung tợn ập đến.
  > * Chúng đã tàn nhẫn bắt cóc toàn bộ bầy chó đi mất!
  > * Nhiệm vụ của bạn: Lên xe, truy đuổi và tiêu diệt sạch 23 tên trộm.
  > * Hãy giải cứu bầy chó và mang chúng về nhà an toàn!
* **Bố trí 23 tên trộm thực tế:** Số lượng kẻ địch trong màn 1 được đồng bộ chính xác là **23 tên trộm cầm dao (thief_knife)** và **Tên Trùm Trộm (Boss 1)** bảo vệ lồng nhốt chú chó ở góc cuối bản đồ. Không còn zombie ngẫu nhiên ở màn này để giữ nguyên tính logic của cốt truyện!

### 🧠 3. Thuật Toán Sinh Quái Chống Kẹt Trong Nhà (MỚI)
* **Quét va chạm an toàn (`_find_free_spawn_pos`):** Game tích hợp thuật toán thông minh tự động dò tìm vị trí trống trải trên bản đồ để sinh quái vật.
* **Không bao giờ bị vướng:** Trước khi đặt kẻ địch xuống, hệ thống sẽ kiểm tra xem tọa độ đó có nằm trong các khu nhà (`house`), ô tô (`car`), cây cối (`tree`), thùng hàng... hay không. Nếu có vật cản, game sẽ tự động dời tọa độ sang vùng đất trống, đảm bảo quái vật luôn tự do di chuyển, áp sát và tấn công người chơi một cách mượt mà nhất.

### 🎭 4. Lựa Chọn Nhân Vật Độc Đáo (Pixel Art 8-Bit)
* **Grab Hero:** Tài xế Grab nhanh nhẹn, linh hoạt với bộ trang phục xanh lá đặc trưng.
* **Shopee Hero:** Hùng thần Shopee Food nhiệt huyết với bộ trang phục cam nổi bật, chiếc túi giao hàng sau lưng cực kỳ chi tiết.
* **Hệ thống Sprite 4 hướng sắc nét:** Cả hai nhân vật đều sở hữu bộ ảnh chuyển động 4 hướng cực kỳ sắc sảo (Pixel-Perfect), chuyển động mượt mà khi đi lên, đi xuống, rẽ trái, rẽ phải.

### 🎮 5. Chế Độ Quyết Chiến PvP (Solo LAN/Wifi)
* Kết nối trực tiếp giữa hai người chơi trong cùng một mạng LAN hoặc Wifi.
* **Hồi sinh ngẫu nhiên:** Khi bị bắn hạ, người chơi sẽ ngay lập tức được hồi sinh ngẫu nhiên tại các điểm an toàn trên bản đồ.
* **Đua điểm kịch tính:** Bên nào đạt được **10 mạng hạ gục trước** sẽ giành chiến thắng chung cuộc!
* Đồng bộ hóa đạn, máu và vị trí giữa máy Chủ (Host) và máy Khách (Client) thời gian thực không giật lag.

---

## 🕹️ HƯỚNG DẪN ĐIỀU KHIỂN

| Hành động | Bàn phím & Chuột | Bàn phím thuần |
| :--- | :--- | :--- |
| **Di chuyển** | `W`, `A`, `S`, `D` | `W`, `A`, `S`, `D` |
| **Lướt né chiêu (Dash)** | Phím Cách (`Space`) | Phím Cách (`Space`) |
| **Ngắm bắn** | Di chuyển Con trỏ chuột | Phím Mũi tên (`↑`, `↓`, `←`, `→`) |
| **Bắn** | **Chuột trái** | Tự động bắn theo hướng di chuyển |
| **Đổi vũ khí** | Phím `Q` / `E` hoặc Cuộn chuột | Phím `Q` / `E` |
| **Tương tác Menu** | Click chuột trái trực tiếp | Dùng phím hướng và `Enter` |

---

## 🌐 HƯỚNG DẪN CHƠI PVP 1V1 QUA WIFI/LAN

Để solo chiến đấu cùng bạn bè cực kỳ đơn giản:
1. **Máy Chủ (Host - Người lập phòng):**
   * Vào Menu PvP, lấy địa chỉ IP LAN của máy mình (ví dụ: `192.168.1.15`) gửi cho bạn bè.
   * Chọn nhân vật và bấm **Tạo Phòng (Host Game)**.
2. **Máy Khách (Client - Người vào phòng):**
   * Vào Menu PvP, nhập địa chỉ IP của máy Chủ đã gửi vào ô kết nối.
   * Chọn nhân vật và bấm **Vào Phòng (Join Game)**.
3. Khi cả hai đã kết nối thành công, trận chiến PvP 10 mạng hồi sinh kịch tính sẽ chính thức bắt đầu!

---

## 🚀 HƯỚNG DẪN CÀI ĐẶT & CHẠY GAME

### Cách 1: Chạy trực tiếp từ file EXE (Khuyên dùng cho người chơi)
Bạn chỉ cần truy cập vào thư mục `dist`, click đúp vào tệp tin chạy duy nhất:
👉 **[GrabHero.exe](file:///c:/Users/LAPTOP/Downloads/grab_hero%20(1)/dist/GrabHero.exe)** là có thể tận hưởng trò chơi ngay lập tức mà không cần cài đặt thêm bất kỳ phần mềm nào khác!

### Cách 2: Chạy bằng mã nguồn Python (Dành cho nhà phát triển)
1. Yêu cầu máy tính đã cài đặt **Python 3.10+** và thư viện **Pygame**:
   ```bash
   pip install pygame
   ```
2. Chạy file chạy chính của game:
   ```bash
   python grab_hero/tong/main.py
   ```

### Cách 3: Đóng gói lại ứng dụng thành file EXE độc lập
Nếu bạn có chỉnh sửa mã nguồn và muốn đóng gói lại thành app gửi bạn bè, chỉ cần chạy file:
👉 **[build_app.bat](file:///c:/Users/LAPTOP/Downloads/grab_hero%20(1)/build_app.bat)** hệ thống sẽ tự động build lại phiên bản `.exe` mới nhất lưu vào thư mục `dist`!

---

Chúc các dũng sĩ Shipper có những giờ phút giao hàng và giao tranh cực kỳ vui vẻ và kịch tính! 🏍️💨🔫

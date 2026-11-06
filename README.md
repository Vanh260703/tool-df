# Delta Force Build Bot

Bot Discord giúp tìm lại code build súng Delta Force đã đăng trong channel, khỏi phải cuộn lại lịch sử chat.

## Tool này dùng để làm gì

Mỗi khi có người đăng code build vào channel được theo dõi, bot tự tách code, tên súng, chế độ chơi và ghi chú rồi lưu vào database. Khi cần, chỉ việc gõ tên súng là bot trả về các build mới nhất.

| Lệnh | Tác dụng |
| --- | --- |
| `/build weapon:k437` | Tìm build theo tên súng, có gợi ý tên súng khi gõ |
| `/build weapon:k437 mode:thoát hiểm` | Tìm và lọc thêm theo chế độ chơi |
| `!k437` | Lối tắt của `/build k437` |

Mỗi lần tìm hiện tối đa 10 build mới nhất. Tên súng không phân biệt hoa thường, dấu cách, dấu gạch ngang hay dấu tiếng Việt, nên `ci19` và `CI-19` cho cùng kết quả.

Bot nhận được hai dạng code:

```text
K437 Assault Rifle-Chiến Dịch (Thoát Hiểm)-6LFHT2C0AHP1JR9CHG3OI    <- dạng share từ game
6LFHT2C0AHP1JR9CHG3OI                                               <- code trơ trọi, lấy dòng phía trên làm ghi chú
```

Khi một tin nhắn bị sửa hoặc xoá, các build của tin đó cũng được cập nhật theo. Lúc khởi động, bot quét bù các tin nhắn được đăng trong thời gian nó tắt.

## Cài đặt và chạy

Dự án viết bằng Python nên không có bước compile. "Build" ở đây chỉ là cài thư viện, tạo file cấu hình rồi chạy bot. Cần Python 3.10 trở lên.

**1. Tạo bot trên Discord**

Vào [Discord Developer Portal](https://discord.com/developers/applications), tạo application, lấy token và bật **Message Content Intent**. Thiếu intent này thì bot không đọc được nội dung tin nhắn.

**2. Cài thư viện**

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

**3. Tạo file cấu hình**

```bash
cp .env.example .env
```

Rồi điền các giá trị vào `.env`:

| Biến | Bắt buộc | Ý nghĩa |
| --- | --- | --- |
| `DISCORD_TOKEN` | Có | Token của bot |
| `WATCH_CHANNEL_IDS` | Có | ID các channel chứa code build, cách nhau bằng dấu phẩy |
| `GUILD_ID` | Không | ID server. Có thì lệnh `/build` hiện ngay, không có thì chờ tới 1 giờ |
| `DB_PATH` | Không | Đường dẫn database, mặc định `builds.db` |

**4. Chạy bot**

```bash
.venv/bin/python bot.py
```

## Build lại

Bot không tự nạp lại code, nên mọi thay đổi đều cần tắt bot (`Ctrl+C`) rồi chạy lại.

| Muốn làm gì | Lệnh |
| --- | --- |
| Áp dụng thay đổi code | `.venv/bin/python bot.py` |
| Đổi thư viện trong `requirements.txt` | `.venv/bin/pip install -r requirements.txt` rồi chạy lại bot |
| Dựng lại venv bị hỏng | `rm -rf .venv` rồi làm lại bước 2 |
| Chạy test | `.venv/bin/python -m unittest` |

### Quét lại toàn bộ channel

Bot chỉ quét tin nhắn mới hơn vị trí đã lưu. Sau khi sửa cách tách code trong `buildcode.py`, các tin cũ sẽ không tự được tách lại, nên phải quét lại từ đầu. Tắt bot rồi chạy:

```bash
.venv/bin/python -c "import sqlite3; c = sqlite3.connect('builds.db'); c.executescript('DELETE FROM builds WHERE message_id != 1; DELETE FROM state;')"
.venv/bin/python bot.py
```

> **Đừng xoá hẳn file `builds.db` để quét lại.** Các build nhập tay (`message_id = 1`) không có trên Discord nên sẽ mất luôn. File này cũng nằm trong `.gitignore`, không có bản nào trên git, nên hãy tự sao lưu.

## Cấu trúc dự án

| File | Vai trò |
| --- | --- |
| `bot.py` | Bot Discord: lệnh tìm kiếm, theo dõi tin nhắn, database |
| `buildcode.py` | Tách code build ra khỏi nội dung tin nhắn |
| `test_buildcode.py` | Test cho phần tách code |
| `.env.example` | Mẫu file cấu hình |
| `builds.db` | Database SQLite, tự tạo khi chạy lần đầu |

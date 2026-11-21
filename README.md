# skillforpoohe

ชุด skill 3 ตัวสำหรับเรียนรู้เนื้อหายาก ๆ ร่วมกับ Claude ใช้ต่อกันเป็นสายพาน:

```
เอกสาร / เนื้อหา / คีย์เวิร์ด
        │
        ▼
 1. deep-study      → study/<หัวข้อ>/knowledge.md   (คลังความรู้ ครบทุกระดับ Bloom)
        │
        ├──▶ 2. lesson-builder → study/<หัวข้อ>/lesson/*.html  (บทเรียน แผนภาพ แบบฝึกหัด แบบทดสอบ)
        │
        └──▶ 3. audio-teacher  → study/<หัวข้อ>/audio/*.mp3   (ครูสอนด้วยเสียง ฟังระหว่างทำอย่างอื่น)
```

| Skill | ทำอะไร |
|---|---|
| `skills/deep-study` | อ่านเอกสารยาวครบทุกหน้า ค้นคีย์เวิร์ดเพิ่ม แล้วย่อยเป็นความเข้าใจ: นิยาม กลไก ตัวอย่างใหม่ การแยกแยะ ความเข้าใจผิด การประยุกต์ การต่อยอด |
| `skills/lesson-builder` | สร้างบทเรียน HTML แบบโต้ตอบ: สถานการณ์เปิดเรื่อง เนื้อหา แผนภาพ Mermaid ตัวอย่างแสดงวิธีทำ แบบฝึกหัดมีเฉลย แบบทดสอบตรวจคะแนนอัตโนมัติ |
| `skills/audio-teacher` | เขียนสคริปต์สอนแบบครู แล้วแปลงเป็น MP3 ภาษาไทย ด้วย `scripts/make_audio.py` |

## ตัวอย่างการสั่งงาน

- "ศึกษาเอกสารที่แนบนี้ให้เข้าใจ และค้นเพิ่มเรื่อง *nudge theory*, *choice architecture*"
- "สร้างบทเรียนสอนฉันจากที่เพิ่งศึกษา มีแบบฝึกหัดและแบบทดสอบด้วย"
- "ทำไฟล์เสียงครูสอนเรื่องนี้ ตอนละ 10 นาที ฉันจะฟังตอนขับรถ"

## ติดตั้ง

- **Claude.ai / Claude Desktop:** อัปโหลดไฟล์ `dist/*.skill` (หรือ zip ของแต่ละโฟลเดอร์) ที่ Settings → Capabilities → Skills
- **Claude Code:** คัดลอกโฟลเดอร์ใน `skills/` ไปไว้ที่ `~/.claude/skills/` (ใช้ทุกโปรเจกต์) หรือ `.claude/skills/` ในโปรเจกต์

### สิ่งที่ audio-teacher ต้องใช้
```bash
pip install edge-tts gTTS      # เสียงไทยธรรมชาติ (ต้องมีอินเทอร์เน็ต)
# ffmpeg: brew install ffmpeg  /  apt install ffmpeg
# สำรองแบบออฟไลน์ (เสียงหุ่นยนต์): apt install espeak-ng
python skills/audio-teacher/scripts/make_audio.py script.txt out.mp3 --voice th-TH-NiwatNeural
```

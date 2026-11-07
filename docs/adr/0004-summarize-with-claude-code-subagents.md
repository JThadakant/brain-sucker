# สรุปด้วย subagent ใน Claude Code ไม่เรียก Claude API โดยตรง

Video Summary ใช้ subagent รุ่น Haiku ส่วน Principles, Topic Map, Evolution และ Advisor Synthesis ใช้ Opus ทั้งหมดรันใน session ของ Claude Code จึงใช้โควตาแพ็กเกจของผู้ใช้ ไม่ต้องมี API key แยกและไม่มีค่าใช้จ่ายรายครั้ง ผลที่ตามมาคือ pipeline ฝั่ง Python ทำแค่ดึงข้อมูลและเขียน Video Record ส่วนงานที่ต้องใช้ LLM ถูกสั่งจาก skill `/brain-suck` ใน Claude Code ถ้าโควตาไม่พอสำหรับช่องใหญ่ ทางสำรองคือ Claude Batch API (ถูกลง 50%)

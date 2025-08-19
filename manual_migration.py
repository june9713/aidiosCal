import sqlite3

# 데이터베이스 연결
conn = sqlite3.connect('sql_app.db')
cursor = conn.cursor()

# parent_order 컬럼 추가
cursor.execute('''
    ALTER TABLE schedules ADD COLUMN parent_order INTEGER
''')

# 기존 데이터 업데이트
cursor.execute('''
    UPDATE schedules 
    SET parent_order = (
        SELECT COUNT(*) 
        FROM schedules s2 
        WHERE s2.parent_id = schedules.parent_id 
        AND s2.created_at <= schedules.created_at
    )
    WHERE parent_id IS NOT NULL
''')

# 변경사항 저장
conn.commit()

# 연결 종료
conn.close()

print("Migration completed successfully.") 
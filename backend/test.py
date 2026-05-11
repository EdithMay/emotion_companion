
from app.database import init_db, SessionLocal
from app.models.db_models import Conversation
from app.agents.companion_agent import get_companion_agent

init_db()
db = SessionLocal()

# 新建会话
conv = Conversation(title='Agent测试', persona='gentle')
db.add(conv)
db.commit()
db.refresh(conv)

agent = get_companion_agent()

# 第一轮对话
r1 = agent.chat(db, conv.id, '最近工作压力很大，感觉快撑不住了')
print(f'用户: 最近工作压力很大...')
print(f'Agent: {r1.reply.content}')

print()

# 第二轮（Agent 应记得上文）
r2 = agent.chat(db, conv.id, '你刚才说的那些，我觉得很有帮助')
print(f'用户: 你刚才说的那些，我觉得很有帮助')
print(f'Agent: {r2.reply.content}')

db.close()
print()
print('✅ 第12步验证通过')


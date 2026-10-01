import lib.llm_pipeline as llm
from dotenv import load_dotenv
load_dotenv()
res = llm.process_entire_transcript(open('user_payload.txt', encoding='utf-8').read())
print('\n\n--- SUCCESS ---')
print('ACTIONS:', len(res.action_items))
for a in res.action_items:
    t = a.get('task')
    o = a.get('owner')
    print(f'- {t} ({o})')

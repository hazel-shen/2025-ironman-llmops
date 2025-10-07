from openai import OpenAI

client = OpenAI()
MODEL = "ft:gpt-4o-mini-2024-07-18:personal::CFxCOwhl"

def ask_kb(user_question: str):
    res = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "user", "content": user_question},
        ],
        temperature=0,
    )
    return res.choices[0].message.content

if __name__ == "__main__":
    q = "資安培訓的要求是什麼"
    print("👤:", q)
    print("🤖:", ask_kb(q))

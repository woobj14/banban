# sample_notes.py — 신규 사용자 '빈 집' 방지용 원본 샘플 노트
# ⚠️ 저작권 0: 교과서를 베끼지 않은 순수 창작 콘텐츠 (반반 철학과 일치)
# 형식은 library.save_note()가 받는 구조 그대로:
#   words     : [(en, kr), ...]
#   dialogues : [{"title": str, "lines": [(en, kr), ...]}, ...]
#   text_data : {"title_en", "title_kr", "sentences": [(en, kr), ...]}

SAMPLE_WORDS = [
    ("puppy", "강아지"),
    ("walk", "산책하다"),
    ("park", "공원"),
    ("ball", "공"),
    ("throw", "던지다"),
    ("catch", "잡다"),
    ("run", "달리다"),
    ("play", "놀다"),
    ("water", "물"),
    ("tired", "피곤한"),
    ("happy", "행복한"),
    ("friend", "친구"),
]

SAMPLE_DIALOGUES = [
    {
        "title": "At the Park",
        "lines": [
            ("A: Look! My puppy can catch the ball.", "A: 봐! 내 강아지가 공을 잡을 수 있어."),
            ("B: Wow, he is so fast!", "B: 와, 정말 빠르다!"),
            ("A: Do you want to throw the ball?", "A: 공을 던져 볼래?"),
            ("B: Sure! Here it goes.", "B: 좋아! 자, 간다."),
        ],
    },
]

SAMPLE_TEXT = {
    "title_en": "A Day with My Puppy",
    "title_kr": "강아지와의 하루",
    "sentences": [
        ("I have a little puppy. His name is Coco.", "나는 작은 강아지가 있어요. 이름은 코코예요."),
        ("Every morning, we walk to the park together.", "매일 아침, 우리는 함께 공원으로 산책해요."),
        ("Coco loves to run and play with a ball.", "코코는 달리고 공을 가지고 노는 것을 좋아해요."),
        ("I throw the ball, and he catches it fast.", "내가 공을 던지면, 코코가 빠르게 잡아요."),
        ("After playing, Coco drinks a lot of water.", "놀고 난 뒤, 코코는 물을 많이 마셔요."),
        ("We are both tired but very happy.", "우리 둘 다 피곤하지만 매우 행복해요."),
    ],
}

# save_note() 공통 페이로드 (title/owner/visibility/tags는 시드 시점에 채움)
SAMPLE_NOTE_PAYLOAD = dict(
    grade="중1",
    publisher="반반 샘플",
    author="",
    chapter="",
    content_type="전체",
    words=SAMPLE_WORDS,
    dialogues=SAMPLE_DIALOGUES,
    text_data=SAMPLE_TEXT,
)

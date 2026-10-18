
import os
import json
import streamlit as st
from dotenv import load_dotenv
from google import genai

# .env 파일에서 API 키 불러오기
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

# 페이지 설정
st.set_page_config(
    page_title="AI Quiz Maker",
    page_icon="🧠",
    layout="centered"
)

st.title("🧠 AI Quiz Maker")
st.write("AI가 만들어 주는 나만의 객관식 퀴즈!")
st.caption("원하는 주제를 입력하고 퀴즈를 풀어 보세요.")

# 세션 데이터 초기화
if "quiz" not in st.session_state:
    st.session_state.quiz = []

if "submitted" not in st.session_state:
    st.session_state.submitted = False


# AI 퀴즈 생성 함수
def generate_quiz(topic, count):
    client = genai.Client(api_key=api_key)

    prompt = f"""
당신은 교육용 퀴즈를 만드는 AI입니다.

주제: {topic}
문제 수: {count}

다음 조건을 지켜 한국어 객관식 퀴즈를 만들어 주세요.
1. 각 문제에는 보기 4개가 있어야 합니다.
2. 정답은 보기 번호 1, 2, 3, 4 중 하나입니다.
3. 각 문제에 이해하기 쉬운 해설을 포함합니다.
4. 문제는 정확하고 주제와 관련 있어야 합니다.
5. 요청한 개수만큼 문제를 만듭니다.

다른 설명 없이 아래 형식의 JSON 배열만 출력하세요.

[
  {{
    "question": "문제 내용",
    "choices": ["보기1", "보기2", "보기3", "보기4"],
    "answer": 1,
    "explanation": "정답인 이유"
  }}
]
"""

    response = client.models.generate_content(
        model="gemini-3.8-flash",
        contents=prompt
    )

    if not response.text:
        raise ValueError("AI가 빈 응답을 반환했습니다.")

    result = response.text.strip()

    # Markdown 코드 블록 제거
    if result.startswith("```"):
        result = result.split("\n", 1)[1]
        result = result.rsplit("```", 1)[0].strip()

    quiz = json.loads(result)

    # AI 응답 검증
    if not isinstance(quiz, list) or len(quiz) != count:
        raise ValueError("생성된 문제 개수가 올바르지 않습니다.")

    for item in quiz:
        if not isinstance(item, dict):
            raise ValueError("문제 형식이 올바르지 않습니다.")

        if not isinstance(item.get("question"), str):
            raise ValueError("문제 내용이 올바르지 않습니다.")

        choices = item.get("choices")
        if (
            not isinstance(choices, list)
            or len(choices) != 4
            or not all(isinstance(c, str) for c in choices)
        ):
            raise ValueError("보기 형식이 올바르지 않습니다.")

        answer = item.get("answer")
        if type(answer) is not int or answer not in [1, 2, 3, 4]:
            raise ValueError("정답 번호가 올바르지 않습니다.")

        if not isinstance(item.get("explanation"), str):
            raise ValueError("해설 형식이 올바르지 않습니다.")

    return quiz


# 사용자 입력 화면
topic = st.text_input(
    "📚 퀴즈 주제",
    placeholder="예: 인공지능 기초, 컴퓨터 네트워크"
)

count = st.selectbox(
    "문제 수 선택",
    [3, 5, 10],
    index=1
)

# 퀴즈 생성 버튼
if st.button("✨ AI 퀴즈 생성", use_container_width=True):
    if not topic.strip():
        st.warning("먼저 퀴즈 주제를 입력해 주세요.")

    elif not api_key:
        st.error(
            "API 키를 찾을 수 없습니다. "
            "프로젝트 폴더의 .env 파일을 확인해 주세요."
        )

    else:
        try:
            with st.spinner("AI가 퀴즈를 만들고 있어요..."):
                new_quiz = generate_quiz(topic.strip(), count)

            st.session_state.quiz = new_quiz
            st.session_state.submitted = False
            st.session_state.pop("answers", None)
            st.rerun()

        except Exception as e:
            st.error(
                "퀴즈 생성에 실패했습니다. "
                "API 키, 모델 사용 가능 여부, 인터넷 연결을 확인해 주세요."
            )
            with st.expander("오류 자세히 보기"):
                st.code(str(e))


# 퀴즈 풀이 화면
if st.session_state.quiz:
    st.divider()
    st.subheader("📝 퀴즈 풀기")

    with st.form("quiz_form"):
        answers = []

        for i, question in enumerate(st.session_state.quiz):
            st.markdown(
                f"**문제 {i + 1}. {question['question']}**"
            )

            selected = st.radio(
                "보기 선택",
                options=[1, 2, 3, 4],
                format_func=lambda n, q=question:
                    f"{n}. {q['choices'][n - 1]}",
                key=f"answer_{i}",
                index=None,
                label_visibility="collapsed"
            )

            answers.append(selected)
            st.write("")

        submitted = st.form_submit_button(
            "정답 제출 및 채점",
            use_container_width=True
        )

    if submitted:
        st.session_state.answers = answers
        st.session_state.submitted = True

    # 결과 화면
    if st.session_state.submitted:
        quiz = st.session_state.quiz
        answers = st.session_state.answers

        score = sum(
            1
            for question, answer in zip(quiz, answers)
            if answer == question["answer"]
        )

        percentage = round(score / len(quiz) * 100)

        st.divider()
        st.subheader("📊 채점 결과")

        st.metric(
            "최종 점수",
            f"{score} / {len(quiz)}",
            f"{percentage}%"
        )

        if percentage == 100:
            st.balloons()
            st.success("완벽해요! 모든 문제를 맞혔습니다!")
        elif percentage >= 60:
            st.success("잘했어요! 해설도 확인해 보세요.")
        else:
            st.info("괜찮아요! 해설을 읽고 다시 공부해 보세요.")

        for i, (question, answer) in enumerate(
            zip(quiz, answers)
        ):
            st.markdown(
                f"**문제 {i + 1}. {question['question']}**"
            )

            correct = question["answer"]

            if answer == correct:
                st.success("정답입니다!")
            elif answer is None:
                st.warning("답을 선택하지 않았습니다.")
            else:
                st.error("오답입니다.")

            st.write(
                f"정답: {correct}. "
                f"{question['choices'][correct - 1]}"
            )

            st.info(f"해설: {question['explanation']}")

    # 새 퀴즈 버튼
    if st.button("🔄 새 퀴즈 만들기"):
        st.session_state.quiz = []
        st.session_state.submitted = False
        st.session_state.pop("answers", None)
        st.rerun()

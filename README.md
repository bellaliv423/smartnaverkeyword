# 네이버 키워드 API 서비스

네이버 검색 API를 활용한 키워드 분석 서비스입니다.

## 설치 방법

1. 저장소 클론
```bash
git clone https://github.com/bellaliv423/never-keyword-extractor.git
cd never-keyword-extractor
```

2. 가상환경 생성 및 활성화
```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
```

3. 패키지 설치
```bash
pip install -r requirements.txt
```

4. 환경변수 설정
- .env 파일에 네이버 API와 OpenAI API 키 설정 필요
- 자세한 설정 방법은 PROJECT_GUIDE.md 참조

5. 실행
```bash
streamlit run app.py
```

## 라이선스
MIT License

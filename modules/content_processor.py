import os
from openai import AsyncOpenAI
from typing import List, Dict, Optional
from dotenv import load_dotenv
import logging
import json
from datetime import datetime
import openai
import asyncio

class ContentProcessorException(Exception):
    """콘텐츠 처리 관련 커스텀 예외"""
    pass

class ContentProcessor:
    def __init__(self):
        load_dotenv()
        self.setup_logging()
        self.setup_openai()
        self.setup_cache()  # 캐시 추가
        
    def setup_logging(self):
        """로깅 설정"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('content_processor.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)

    def setup_openai(self):
        """OpenAI API 설정"""
        try:
            self.api_key = os.environ.get('OPENAI_API_KEY')
            
            if not self.api_key:
                raise ValueError("OpenAI API 키가 설정되지 않았습니다.")
            
            # OpenAI 클라이언트 설정
            self.client = AsyncOpenAI(
                api_key=self.api_key,
                max_retries=3
            )
            
            self.logger.info("OpenAI API 설정 완료")
            
        except Exception as e:
            self.logger.error(f"OpenAI 설정 실패: {str(e)}")
            raise ValueError(f"OpenAI 클라이언트 초기화 실패: {str(e)}")

    def setup_cache(self):
        """캐시 설정"""
        self.cache = {}
        self.cache_timeout = 3600  # 1시간
        
    async def process_content(self, content: Dict, mode: str = 'summarize') -> Dict:
        """콘텐츠 처리 메인 함수"""
        try:
            if not content or 'description' not in content:
                raise ValueError("유효하지 않은 콘텐츠 형식입니다.")

            # 캐시 확인
            cache_key = f"{content['description'][:100]}_{mode}"
            if cache_key in self.cache:
                return self.cache[cache_key]

            # 병렬 처리
            tasks = []
            if mode == '요약':
                tasks.append(self.summarize_content(content['description'], 500))
                tasks.append(self.extract_keywords(content['description']))
                summary, keywords = await asyncio.gather(*tasks)
                
                result = {
                    "type": "summary",
                    "title": content.get('title', ''),
                    "original_link": content.get('link', ''),
                    "short_version": summary['content'],
                    "keywords": keywords
                }
            else:
                tasks.append(self.restructure_content(content))
                tasks.append(self.extract_keywords(content['description']))
                restructured, keywords = await asyncio.gather(*tasks)
                
                result = {
                    "type": "restructured",
                    "title": content.get('title', ''),
                    "original_link": content.get('link', ''),
                    "long_version": restructured['content'],
                    "keywords": keywords
                }

            # 결과 캐시에 저장
            self.cache[cache_key] = result
            return result
                
        except Exception as e:
            self.logger.error(f"콘텐츠 처리 중 오류 발생: {str(e)}")
            raise ContentProcessorException(f"콘텐츠 처리 실패: {str(e)}")

    async def summarize_content(self, content: str, target_length: int) -> Dict:
        """콘텐츠 요약"""
        try:
            system_prompt = f"""
            다음 내용을 {target_length}자 내외로 요약해주세요.
            요약시 다음 규칙을 따라주세요:
            1. 핵심 내용을 먼저 서술
            2. 중요한 수치나 통계는 유지
            3. 전문 용어는 가능한 쉽게 설명
            4. 문장은 간결하게 구성
            """

            response = await self.client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": content}
                ],
                temperature=0.7,
                max_tokens=1500
            )

            summary = response.choices[0].message.content
            return {
                "type": "summary",
                "content": summary,
                "length": len(summary)
            }
            
        except Exception as e:
            self.logger.error(f"요약 중 오류 발생: {str(e)}")
            raise

    async def restructure_content(self, content: Dict) -> Dict:
        """콘텐츠 재구성"""
        try:
            system_prompt = f"""
            다음 내용을 1000자 내외로 재구성해주세요.
            재구성시 다음 규칙을 따라주세요:
            1. 논리적 구조화
            2. 객관적 사실 중심
            3. 핵심 메시지를 강조
            4. 전문 용어는 쉽게 설명
            5. 단락을 적절히 나누어 가독성 향상
            """

            response = await self.client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": content['description']}
                ],
                temperature=0.7,
                max_tokens=2000
            )

            restructured = response.choices[0].message.content
            return {
                "content": restructured,
                "type": "restructured"
            }
            
        except Exception as e:
            self.logger.error(f"재구성 중 오류 발생: {str(e)}")
            raise

    async def extract_keywords(self, content: str) -> List[str]:
        """주요 키워드 추출"""
        try:
            response = await self.client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "다음 내용에서 주요 키워드를 추출하여 해시태그 형식으로 반환해주세요. (최대 10개)"},
                    {"role": "user", "content": content}
                ],
                temperature=0.5,
                max_tokens=200
            )
            
            keywords = response.choices[0].message.content.split()
            return [k for k in keywords if k.startswith('#')]
            
        except Exception as e:
            self.logger.error(f"키워드 추출 중 오류 발생: {str(e)}")
            return []

    async def translate_content(self, text: str, target_lang: str) -> Dict:
        """콘텐츠 번역"""
        try:
            # 언어별 프롬프트 설정
            lang_prompts = {
                '중국어(간체)': '请将以下韩语内容翻译成简体中文：',
                '중국어(번체)': '請將以下韓語內容翻譯成繁體中文：',
                '영어': 'Please translate the following Korean text to English:',
                '일본어': '以下の韓国語の内容を日本語に翻訳してください：'
            }

            prompt = lang_prompts.get(target_lang, f'다음 내용을 {target_lang}로 번역해주세요:')
            
            response = await self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {
                        "role": "system",
                        "content": "You are a professional translator."
                    },
                    {
                        "role": "user",
                        "content": f"{prompt}\n\n{text}"
                    }
                ],
                temperature=0.3,
                max_tokens=1500
            )

            translated = response.choices[0].message.content.strip()
            
            if not translated:
                raise ValueError("번역 결과가 비어있습니다.")

            return {
                "translated_text": translated,
                "source_text": text,
                "target_language": target_lang
            }

        except Exception as e:
            self.logger.error(f"번역 중 오류 발생: {str(e)}")
            return {
                "error": str(e),
                "source_text": text,
                "target_language": target_lang
            }

    async def process_content_async(self, content, mode="재구성"):
        try:
            if mode == "재구성":
                prompt = f"다음 내용을 1000자로 재구성해주세요:\n{content['description']}"
                max_tokens = 1000
            else:
                prompt = f"다음 내용을 500자로 요약해주세요:\n{content['description']}"
                max_tokens = 500

            response = await openai.ChatCompletion.acreate(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": prompt}
                ]
            )

            processed_text = response.choices[0].message.content

            return {
                'type': 'restructured' if mode == "재구성" else 'summary',
                'original_title': content['title'],
                'long_version': processed_text if mode == "재구성" else None,
                'short_version': processed_text if mode == "요약" else None,
                'keywords': ['키워드1', '키워드2', '키워드3'],  # 임시 데이터
                'source_url': content['link']
            }
        except Exception as e:
            print(f"Error in process_content: {str(e)}")
            raise

    async def translate_content_async(self, text, target_lang):
        try:
            response = await openai.ChatCompletion.acreate(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": f"Translate the following text to {target_lang}:"},
                    {"role": "user", "content": text}
                ]
            )
            
            return {
                'translated_text': response.choices[0].message.content,
                'target_language': target_lang
            }
        except Exception as e:
            print(f"Error in translate_content: {str(e)}")
            raise 
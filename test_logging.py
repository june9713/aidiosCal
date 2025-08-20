#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
로깅 설정 테스트 스크립트
"""

import logging
import sys

def test_logging():
    """로깅 설정을 테스트합니다."""
    
    print("🔧 로깅 설정 테스트 시작")
    print("=" * 50)
    
    # 로거 생성
    logger = logging.getLogger("test_logger")
    logger.setLevel(logging.DEBUG)
    
    # 콘솔 핸들러 추가
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG)
    
    # 로그 포맷 설정
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s'
    )
    console_handler.setFormatter(formatter)
    
    # 핸들러 추가
    logger.addHandler(console_handler)
    
    # 테스트 로그 출력
    logger.debug("🔍 [TEST] Debug 메시지 테스트")
    logger.info("ℹ️ [TEST] Info 메시지 테스트")
    logger.warning("⚠️ [TEST] Warning 메시지 테스트")
    logger.error("❌ [TEST] Error 메시지 테스트")
    
    print("\n✅ 로깅 테스트 완료!")
    print("이제 일정 추가 시 상세한 로그를 확인할 수 있습니다.")

if __name__ == "__main__":
    test_logging()

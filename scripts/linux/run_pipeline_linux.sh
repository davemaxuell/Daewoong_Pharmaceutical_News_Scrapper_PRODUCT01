#!/bin/bash
# Linux용 파이프라인 실행 스크립트
# Linux-compatible pipeline runner

# 스크립트 디렉토리로 이동
cd "$(dirname "$0")"

# 가상환경 활성화
source venv/bin/activate

# Python 경로 확인
PYTHON_BIN="venv/bin/python"

echo "========================================="
echo "Pharmaceutical News Agent Pipeline"
echo "Date: $(date '+%Y-%m-%d %H:%M:%S')"
echo "========================================="

# 파이프라인 실행
$PYTHON_BIN run_pipeline.py

# 종료 코드 확인
EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then
    echo ""
    echo "✓ Pipeline completed successfully!"
else
    echo ""
    echo "✗ Pipeline failed with exit code: $EXIT_CODE"
fi

exit $EXIT_CODE

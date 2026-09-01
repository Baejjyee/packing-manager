# Packing Manager 개발 지침

## 프로젝트 목표

자재발주서 PDF에서 데이터를 추출하고, 사용자의 검토를 거쳐 Packing List와
Packing Label PDF를 생성하는 사내용 PySide6 데스크톱 애플리케이션이다.

## 개발 원칙

- Python 3.12를 기준으로 작성한다.
- UI, PDF 파싱, 데이터베이스, 도메인 모델, 문서 생성, 출력 코드를 분리한다.
- UI 계층에 파싱, SQL, PDF 생성 비즈니스 로직을 넣지 않는다.
- 플랫폼 독립 코드에서 Windows 전용 패키지를 직접 import하지 않는다.
- Windows 프린터 연동은 `printing/windows_printer.py`에만 둔다.
- 파일 경로는 하드코딩하지 않고 `config.py`의 `pathlib.Path` 값을 사용한다.
- SQLite 쿼리는 repository 계층에 한정하고 매개변수 바인딩을 사용한다.
- 추출된 원본 값과 사용자가 수정한 값을 구분할 수 있도록 모델을 설계한다.
- 자재 병합 기준은 자재명, 규격, 색상의 조합이며 발주량과 Loss는 각각 합산한다.
- 새 기능에는 가능한 범위에서 단위 테스트를 추가한다.

## 현재 단계

- 자재발주서 PDF 파싱과 자재 병합 로직이 구현되어 있다.
- SQLite 영문명 조회/저장과 PySide6 검토 화면이 구현되어 있다.
- Packing List 및 A4 가로 좌우 2-up Packing Label PDF 생성이 구현되어 있다.
- 자재별 중량, C.B.M, Packing 수량을 입력하며 Packing 수량 기본값은 54이다.
- Packing 내역과 R/L 수는 `(발주량 + Loss) / Packing 수량`으로 자동 계산한다.
- Windows 프린터 출력 어댑터는 구현되어 있으며 A4 가로·단면·300 DPI로 출력한다.
- 실제 Windows PC와 실물 프린터에서 여백, 드라이버 설정, 출력 완료 여부를 검증해야 한다.

## 실행 및 배포

- macOS에서는 개발과 기능 검증을 수행한다.
- 최종 exe는 Windows의 Python 3.12 환경에서 PyInstaller로 빌드한다.
- Windows 빌드는 `scripts/build_windows.bat`를 사용하며 생성된 exe의 시작 검사를
  통과한 뒤 onedir ZIP을 만든다.
- 생성물과 로컬 DB는 Git에 커밋하지 않는다.

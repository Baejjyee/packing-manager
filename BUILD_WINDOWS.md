# Windows exe 빌드 및 시험

PyInstaller는 교차 컴파일을 지원하지 않으므로 Windows용 exe는 Windows PC에서
빌드해야 한다.

## GitHub Actions로 빌드 (권장)

1. 소스 코드를 GitHub 비공개 저장소에 push한다.
2. GitHub 저장소의 `Actions` 탭을 연다.
3. 왼쪽에서 `Build Windows exe`를 선택한다.
4. `Run workflow` 버튼을 누른다.
5. 빌드가 완료되면 실행 상세 화면의 `Artifacts`에서
   `PackingManager-windows`를 다운로드한다.

워크플로는 Windows 환경에서 Python 3.12 설치, 테스트, PyInstaller 빌드,
패키징된 exe 시작 검사를 수행한 뒤 ZIP을 업로드한다. 로컬 PC에는 Python을
설치할 필요가 없다. Artifact 보관 기간은 14일이다.

## Windows PC에서 직접 빌드

1. 이 프로젝트 폴더 전체를 Windows PC로 복사한다.
2. 64비트 Python 3.12를 설치하며 `py launcher` 옵션을 활성화한다.
3. 프로젝트 폴더의 `BUILD_WINDOWS.bat`를 더블클릭한다.

배치 파일은 전용 `.venv-win` 환경을 만들고 의존성을 설치한 다음 PyInstaller
onedir 번들을 생성한다. 생성된 exe의 시작 검사를 통과해야 ZIP을 만든다. 첫
배포는 오류 확인이 쉬운 onedir 방식을 사용한다.

## 결과

- 실행 파일: `dist\PackingManager\PackingManager.exe`
- 전달용 ZIP: `dist\PackingManager-windows.zip`

ZIP 파일을 시험 PC에서 압축 해제하고 `PackingManager.exe`를 실행한다. exe만
따로 꺼내면 안 되며 `_internal` 폴더와 함께 있어야 한다.

프로그램이 생성하는 SQLite DB와 기본 PDF 출력 폴더는 exe 옆의 `data`,
`output` 폴더에 만들어진다.

## 시험 순서

1. 자재발주서 PDF를 선택한다.
2. 미등록 영문명을 입력한다.
3. 포장 구성, 중량, CBM, 선적일을 입력한다.
4. Packing PDF를 생성한다.
5. Label PDF 배열을 미리 확인한다.
6. `Label 프린트`를 누르고 A4 지원 프린터를 선택한다.
7. A4 가로, 단면, 좌우 2개 배치와 실제 여백을 확인한다.

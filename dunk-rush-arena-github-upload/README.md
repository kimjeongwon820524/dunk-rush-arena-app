# 덩크 러시 아레나 — 안드로이드 앱 (Dunk Rush Arena)

브라우저용 HTML5 게임을 [Capacitor](https://capacitorjs.com)로 감싼 **진짜 설치형 안드로이드 앱(APK)** 프로젝트입니다.

> 이 저장소에는 무거운 `android/` 네이티브 프로젝트 폴더를 미리 넣어두지 않았습니다. GitHub Actions가 빌드할 때마다 `npx cap add android`로 매번 새로 생성하고 브랜딩(이름/아이콘/패키지명)을 자동으로 입혀줍니다 — 그래서 저장소가 가볍고 업로드도 쉽습니다.
게임 로직/멀티플레이(같은 Wi-Fi 1:1 대결)는 기존 웹 버전과 100% 동일하며, 여기에 오리지널 배경음악·효과음·고해상도 이미지를 더해 실제 앱 퀄리티를 높였습니다.

## 왜 이런 구조인가요?

- 이 프로젝트를 만든 환경(Claude)에는 Android SDK/Gradle 빌드 서버가 막혀 있어 **로컬에서 직접 APK를 빌드할 수 없습니다.**
- 대신 `.github/workflows/build-apk.yml`에 **GitHub Actions 클라우드 빌드**를 준비해 두었습니다. 저장소를 GitHub에 올리기만 하면 GitHub의 서버가 자동으로 APK를 만들어줍니다.
- 배경음악/효과음/고해상도 이미지는 저장소에는 작은 미리보기 버전만 들어있고, **빌드가 실행될 때마다 스크립트(`tools/generate_assets.py`)가 실제 풀 버전을 새로 생성**합니다. 전부 절차적으로 합성한 오리지널 콘텐츠라 저작권 문제가 없고, 이 방식 덕분에 저장소 자체는 가볍게 유지됩니다. (최종 APK 용량은 대략 800MB~1GB 수준으로 예상됩니다 — 실제 값은 첫 빌드 후 Actions 로그의 "빌드 결과 크기 확인" 단계에서 확인할 수 있습니다.)

## APK 만드는 방법 (한 번만 하면 됩니다)

1. [github.com](https://github.com)에서 계정 생성 (이미 있다면 생략)
2. 새 저장소(Repository) 생성 — Public/Private 아무거나 상관없음
3. 이 폴더(`dunk-rush-arena-app`) 전체를 그 저장소에 push:
   ```bash
   cd dunk-rush-arena-app
   git init
   git add .
   git commit -m "Dunk Rush Arena Android app"
   git branch -M main
   git remote add origin https://github.com/<내계정>/<저장소이름>.git
   git push -u origin main
   ```
   (터미널이 낯설면 [GitHub Desktop](https://desktop.github.com) 앱으로 폴더를 그대로 드래그해서 올려도 됩니다.)
4. push가 끝나면 저장소의 **Actions** 탭으로 이동 → "Build Android APK" 워크플로우가 자동으로 시작됩니다 (약 10~20분 소요, 에셋 용량에 따라 다름).
5. 빌드가 초록색 체크로 끝나면 해당 실행(run)을 클릭 → 하단 **Artifacts**에서 `dunk-rush-arena-debug-apk`를 다운로드 (zip 파일) → 압축을 풀면 `app-debug.apk`가 나옵니다.

## 폰에 설치하는 방법

1. 위에서 받은 `app-debug.apk` 파일을 안드로이드 폰으로 전송 (카카오톡 '나에게 보내기', 이메일, USB 케이블, 구글 드라이브 등 아무 방법이나 가능)
2. 폰에서 그 파일을 탭해서 열기
3. "출처를 알 수 없는 앱" 관련 경고가 뜨면 **설정 → 이 출처 허용**을 눌러 허용 (스토어를 거치지 않고 직접 설치하는 앱은 항상 이런 확인 절차가 있습니다 — 정상입니다)
4. 설치 완료 후 홈 화면에서 "덩크 러시 아레나" 아이콘 실행

두 사람이 각자 이 APK를 설치하면, 앱 안에서 그대로 **같은 Wi-Fi 1:1 대결** 기능을 사용할 수 있습니다 (호스트 코드/참가 코드 방식, 인터넷 연결 없이 같은 공유기 안에서만 작동).

## 로컬에서 미리 확인하고 싶다면

```bash
cd dunk-rush-arena-app
npm install
python3 tools/generate_assets.py --quick   # 짧은 테스트용 오디오/이미지 생성 (이미 생성되어 있음)
```
`www/index.html`을 아무 브라우저로 직접 열면 앱과 동일한 게임을 바로 플레이해볼 수 있습니다 (오디오는 --quick 버전이라 실제 앱보다 훨씬 짧게 들어있음).

## 포함된 오리지널 콘텐츠

- 배경음악 4곡(메뉴/경기 A/경기 B/결과화면) + 팀별 테마 징글 6개(전부 절차적 칩튠 합성)
- 관중 앰비언스 2종(차분/열광)
- 효과음 10종 이상 (휘슬/부저/함성/탄식/드리블/덩크 임팩트/콤보 스팅어 등)
- 고해상도 절차적 텍스처/배경 이미지 + 앱 아이콘/스플래시

전부 `tools/generate_assets.py`가 수학적으로 합성하는 오리지널 자료이며, 외부 음원·이미지를 가져다 쓰지 않았습니다.

## 참고

- iOS 앱은 별도로 준비하지 않았습니다 (Mac + Xcode + Apple 개발자 계정이 필요해 이 환경에서는 불가능합니다). 요청하신 것도 "폰에 설치하는 APK" 방식이라 안드로이드 기준으로 진행했습니다.
- 지금은 서명되지 않은 "debug" 빌드입니다 — 개인적으로 설치해서 쓰기에는 전혀 문제없지만, 나중에 정식 배포(Play 스토어 등)를 원하시면 별도의 서명 키 설정이 필요합니다. 필요하면 알려주세요.

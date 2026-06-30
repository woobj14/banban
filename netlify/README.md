# Netlify 배포 (반반 BanBan 앱 주소 받기)

> Netlify는 우리 앱(Streamlit=파이썬 서버)을 **직접 실행하지 못합니다.**
> 이 폴더는 깔끔한 `반반.netlify.app` 주소를 만들고, 그 주소로 들어온 사람을
> **실제 실행 중인 앱(현재 ngrok URL)** 으로 자동 이동시킵니다.

## 배포 방법 (둘 중 하나)

### A. 드래그&드롭 (가장 빠름)
1. https://app.netlify.com → 로그인
2. "Add new site" → "Deploy manually"
3. 이 **`netlify` 폴더 자체**를 드래그해서 올리기
4. 잠시 후 `랜덤이름.netlify.app` 주소가 나옴 → 사이트 설정에서 이름 변경 가능

### B. Git 연동 (자동 배포)
1. Netlify에서 이 저장소 연결
2. Base directory: `netlify`, Publish directory: `netlify`
3. 푸시할 때마다 자동 반영

## 앱 주소가 바뀌면 (중요)
지금은 ngrok 무료 주소라 가끔 바뀔 수 있습니다. 바뀌면 **두 곳**을 수정:
- `index.html` 의 `var APP_URL = "..."`
- `netlify.toml` 의 `to = "..."`

## 주의 (ngrok 무료의 한계)
- 처음 들어가면 ngrok의 **"방문 경고" 페이지**가 한 번 뜰 수 있습니다(무료 플랜 특성).
- ngrok 터널/맥이 꺼지면 앱도 멈춥니다.
- **진짜 상시 주소**가 필요하면 Streamlit을 Streamlit Community Cloud / Render /
  Railway 에 배포하고, 위 두 곳의 주소를 그 배포 주소로 바꾸면 됩니다.

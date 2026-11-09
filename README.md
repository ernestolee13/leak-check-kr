# 유출 확인 도우미 (leak-check-kr)

한국 개인정보 유출 사건에서 내가 대상인지 확인하고, 소송에 참여하고 싶을 때 지금 원고를 받는 법무법인의 공개 조건을 비교해 보는 도구입니다. Claude나 Codex에 설치해서 쓰는 스킬이고, 같은 내용을 사람이 바로 읽을 수 있는 문서로도 둡니다.

- [CASES.md](CASES.md): 사건별로 내가 대상인지 확인하는 법. 실제 통지 메일과 문자 예시, 검색어, 회사 조회 페이지
- [FIRMS.md](FIRMS.md): 지금 원고를 받는 법무법인의 착수금, 성공보수, 패소 시 부담, 마감, 공식 신청 링크

<!-- summary:start -->
**2026-11-09 기준.** 사건 22건, 법무법인 조건 18행.

- 티빙: 노바 (접수 중), 더에이치 황해 (접수 중), 세담 (접수 중), 지향 (마감 공지 없음, 접수 전 확인)
- 쿠팡: LKB평산 (접수 중), 민행 대리인단 (classaction.ai.kr) (접수 중)
- SK텔레콤: 노바 (일부만 접수), 대륜 (마감 공지 없음, 접수 전 확인)
- 롯데카드: 지향 (마감 공지 없음, 접수 전 확인)
- 따릉이 (서울시설공단): 노바 (접수 중)
- 강남언니 (힐링페이퍼): YK (보도로만 확인)

법무법인 이름 순이며 추천이 아니다. 조건과 공식 링크는 [FIRMS.md](FIRMS.md), 사건별 확인법은 [CASES.md](CASES.md).
<!-- summary:end -->

## 하는 일

1. **통지 찾기.** 회사는 조회 페이지를 금방 닫습니다. 그래서 당시 받은 유출 통지가 가장 오래 남는 증빙입니다. 메일 연결(Gmail 등)이 켜져 있으면 사건별 검색어로 스팸과 휴지통까지 찾고, 날짜와 발신자와 제목만 보여 줍니다. 문자는 붙여 넣거나 캡처를 올리면 실제 통지 예시와 비교합니다.
2. **회사 조회 페이지 열기.** 아직 열려 있는 곳만 엽니다. 로그인과 본인인증은 직접 합니다.
3. **조건 보기.** 원하면 그 사건에 원고를 받는 곳을 법무법인 이름 순 표로 보여 줍니다.
4. **신청 돕기.** 내가 고른 곳의 공식 페이지를 열고 준비물을 알려 줍니다. 서명, 결제, 제출은 직접 합니다.

## 하지 않는 일

- 특정 법무법인 추천이나 순위 매기기
- 승소 가능성이나 받을 금액 예측
- 메일과 문자 내용을 어디로 보내는 일. 이 도구는 이 저장소의 공개 파일 두 개(`data/cases.json`, `data/firms.json`)를 읽기만 합니다.
- 법무법인에서 돈을 받는 일. 만든 사람은 변호사가 아니고 어느 법무법인에서도 대가를 받지 않습니다. 법률 자문이 아닙니다.

## 설치

설치한 뒤 「내 개인정보 유출됐는지 봐 줘」, 「티빙 유출 소송 조건 보여 줘」처럼 말하면 됩니다.

### Claude Code

```
/plugin marketplace add ernestolee13/leak-check-kr
/plugin install leak-check-kr@leak-check-kr
```

### Claude 데스크톱 앱 (Cowork)

[Releases](https://github.com/ernestolee13/leak-check-kr/releases/latest)에서 `leak-check-kr.zip`을 받아 설정의 플러그인 메뉴에서 올립니다. 이 저장소를 플러그인 마켓으로 추가해도 됩니다. 브라우저 연결이 켜져 있으면 조회 페이지와 신청 페이지를 같이 엽니다.

### claude.ai 웹과 앱

[Releases](https://github.com/ernestolee13/leak-check-kr/releases/latest)에서 `leak-check-skill.zip`을 받아 설정의 스킬 메뉴에서 올립니다. 메일 찾기, 조건 비교, 링크 안내까지 됩니다.

### Codex

Codex에게 이렇게 말합니다.

```
$skill-installer https://github.com/ernestolee13/leak-check-kr/tree/main/plugins/leak-check-kr/skills/leak-check 설치해 줘
```

직접 넣으려면:

```
git clone https://github.com/ernestolee13/leak-check-kr.git
mkdir -p ~/.agents/skills
cp -r leak-check-kr/plugins/leak-check-kr/skills/leak-check ~/.agents/skills/
```

### 설치 없이

[CASES.md](CASES.md)와 [FIRMS.md](FIRMS.md)를 그대로 읽어도 됩니다. 쓰는 AI에 두 파일 주소를 주고 물어봐도 됩니다.

## 갱신

사건과 법무법인 조건은 월 1회, 그리고 큰 유출 사건이나 새 원고 모집이 나왔을 때 다시 확인해 올립니다. 도구는 실행할 때마다 이 저장소의 최신 데이터를 먼저 읽으므로 다시 설치하지 않아도 됩니다. 각 행의 확인일이 30일을 넘으면 도구가 「다시 확인하세요」라고 알려 줍니다.

## 문의

틀린 내용, 바뀐 조건, 빠진 사건은 [이슈](https://github.com/ernestolee13/leak-check-kr/issues)나 help@vibestash.app 로 알려 주세요. 법무법인의 등재 요청이나 광고는 받지 않습니다. 조건은 각 법무법인이 공개한 페이지를 기준으로만 옮깁니다.

안내 페이지: https://leak-cases.vibestash.app/

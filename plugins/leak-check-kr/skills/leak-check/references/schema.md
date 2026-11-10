# 데이터 형식

두 파일 모두 `https://leak-cases.vibestash.app/data/` 아래 공개된다. 읽기 전용이다. 검사는 `scripts/validate_data.py`.

## cases.json

| 필드 | 뜻 |
|---|---|
| `updated` | 파일을 마지막으로 고친 날 |
| `fallback` | 사건을 모를 때 쓰는 공공 창구 |
| `cases[].id` | 사건 식별자. firms.json의 `case`와 같다 |
| `company` | 회사 이름 (계열 브랜드 포함) |
| `disclosed` | 유출이 알려진 달 (YYYY-MM) |
| `audience` | `customers` 이용자, `employees` 임직원과 협력사, `mixed` 둘 다 |
| `size` | 규모. 회사 발표나 보도 그대로 |
| `items` | 유출 항목 |
| `scope_note` | 대상 범위 보충 (가입 시기 등) |
| `self_check.status` | `open` 조회 가능, `login` 로그인해야 보임, `closed` 닫힘, `none` 조회 창구 없음, `unknown` 확인 못 함 |
| `self_check.url`, `how`, `checked` | 조회 주소, 방법, 마지막 확인일 |
| `notices[]` | 실제 통지 예시. `channel` 경로, `sender` 발신, `date` 시기, `opening` 첫 부분, `basis` 출처 종류(`company_notice` 회사 공지, `user_post` 이용자 공개 인증 글(비식별), `press` 보도, `notice` 개별 통지(비식별)) |
| `search.mail`, `search.sms` | 메일과 문자 검색어. `basis`가 `notice_text`면 실제 통지나 회사 공지 제목 같은 실제 문구 기반, `suggested`면 추정 |
| `contact` | 회사 문의처 |
| `limitation_earliest` | 가장 이른 시효 만료 예상 달. 알려진 달에 3년을 더한 값이고 법률 판단이 아니다 |
| `fraud_warning` | 회사가 공지한 사칭 주의 |
| `confidence` | `press_only`면 회사 공지를 확인하지 못한 사건 |
| `review` | `pending`이면 새로 들어와 아직 사람이 확인하지 않은 사건. 조회 방법과 통지 문구가 비어 있을 수 있다 |
| `warmpod_id` | warmpod 사건 id. warmpod에서 이 사건으로 들어오는 링크에 쓴다 |
| `sources` | 1차 자료 주소 |

## firms.json

| 필드 | 뜻 |
|---|---|
| `order` | 정렬 규칙. 법인 이름 글자 순. 바꾸지 않는다 |
| `stale_after_days` | 이 날수보다 오래된 행은 「다시 확인」 표시 |
| `cases[].case` | cases.json의 `id` |
| `firm` | 법무법인 이름 |
| `status` | `open`, `open_unconfirmed`, `limited`, `press_only`, `closed` (뜻은 파일 안 `status_values`) |
| `note` | 보충. `limited`면 누가 접수 대상인지 반드시 적는다 |
| `round`, `deadline` | 차수, 마감 |
| `upfront`, `success_fee`, `if_lost` | 착수금이나 참가비, 성공보수, 패소 시 부담. 페이지에 없으면 `미기재` |
| `intake`, `url` | 접수 방법, 법인 공식 페이지 |
| `documents` | 요구 서류 |
| `apply_url` | 신청 폼으로 바로 가는 주소 (있을 때) |
| `steps[]` | 신청 순서. 법인 페이지와 신청 폼 첫 화면을 직접 읽고 적는다. 입금 계좌번호는 넣지 않고 「법인 페이지에 적힌 계좌」로 쓴다. 접수 중인 행에는 반드시 있다 |
| `confirm` | 접수 확인과 문의 경로 |
| `quote` | 판단 근거로 페이지에서 옮긴 문장 |
| `checked` | 마지막 확인일 |
| `no_recruitment_found[]` | 모집하는 곳을 찾지 못한 사건. `case`, `checked`(마지막으로 찾아본 날), `note`(선택) |

## 넣지 않는 것

법인 평가, 순위, 추천 문구, 승소 가능성, 예상 배상액, 추천 코드나 제휴 링크, 추적 파라미터. 검사 스크립트가 일부 단어와 파라미터를 막는다.

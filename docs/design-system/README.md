# Wanted Design System — 로컬 Export

출처: https://www.figma.com/design/sU6h8D1zkwkdUdMlA0dEVe/Wanted-Design-System--Community-

## 파일 목록

### 최상위
| 파일 | 내용 |
|---|---|
| `overview.png` | 전체 개요 — 소개, 색상 팔레트, Pretendard 폰트, 네비게이션 예시 |
| `resource.png` | Resource 페이지 |

### components/
| 파일 | 섹션 | 포함 컴포넌트 |
|---|---|---|
| `1-layout.png` | 1 Layout | 레이아웃 구조 |
| `2-action.png` | 2 Action | Button, Text Button, Icon Button, Chip, Toggle Icon, Action Area |
| `3-selection-input.png` | 3 Selection and Input | Textfield, Textarea, Select, Radio, Checkbox, Toggle, Segmented Control, Counter |
| `4-content.png` | 4 Content | Icon, Content Badge, Thumbnail, Avatar, List Cell, Card |
| `5-loading.png` | 5 Loading | Circular Spinner, Skeleton (Text/Rectangle/Circle) |
| `6-navigation.png` | 6 Navigation | Tab, Category Chip, Page Indicator, Pagination |
| `7-feedback.png` | 7 Feedback | Alert, Toast, Snackbar, Menu |
| `8-presentation.png` | 8 Presentation | Tooltip |

### theme/
| 파일 | 내용 |
|---|---|
| `theme-logo-icons.png` | Theme 페이지 전체 (로고 + 아이콘) |
| `icons.png` | 아이콘 라이브러리 (Normal, Chevron 등 100+ 아이콘) |
| `element-basic-spacing-decorate.png` | Element 페이지 — Ratio, Spacing, Gradient, Interaction |

## 핵심 디자인 토큰 (overview.png 기반)

- **폰트**: Pretendard (한국어 최적화)
- **Primary 색상**: Wanted 브랜드 블루
- **라이트/다크 모드**: 둘 다 지원
- **컴포넌트 스타일**: 라운드 코너, 클린 미니멀

## MVP 화면별 참조 파일

로그인 화면은 없다([ADR-008](../10-adr.md#adr-008-mvp에서는-로그인을-넣지-않는다)). 운영 화면도 따로 만들지 않고 CloudWatch 대시보드로 대신한다.

| 화면 | 주요 요소 | 참조 파일 |
|---|---|---|
| 공통 레이아웃 | 목록·채팅 전환, 데이터 기준 시각("N시 기준") 표시, 모바일 360px 대응 | `1-layout.png`, `6-navigation.png` (Tab) |
| 공고 목록 (FR-S01) | 필터(경력·지역·직무·고용형태·마감·소스), 키워드 검색, 정렬, 공고 카드, 페이지 이동, 로딩 | `6-navigation.png` (Category Chip, Pagination), `3-selection-input.png` (Select, Textfield, Segmented Control), `4-content.png` (Card, Content Badge), `5-loading.png` (Skeleton) |
| 공고 상세 (FR-S02) | 요약 정보, 출처 배지, 원문 링크 버튼, 다른 소스 링크(`also_on`), 마감 공고 상태 표시 | `4-content.png` (List Cell, Content Badge), `2-action.png` (Button, Text Button) |
| 채팅 검색 (FR-CH) | 메시지 입력(500자), 결과 카드와 매칭 이유, 적용 조건 칩 삭제·재검색, 0건 시 완화 제안 버튼, 좋아요/싫어요, 응답 대기 | `3-selection-input.png` (Textarea), `2-action.png` (Icon Button, Chip, Toggle Icon), `4-content.png` (Card), `5-loading.png` (Circular Spinner) |
| 안내·오류 | 개인정보 입력 자제 안내, `DEGRADED` "간단 검색 결과예요" 안내, 429 호출 제한·일일 상한 안내, 피드백 전송 완료 | `7-feedback.png` (Alert, Snackbar, Toast) |

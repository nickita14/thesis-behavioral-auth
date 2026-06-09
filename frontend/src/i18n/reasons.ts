// Localization map for stable English reason codes returned by the backend.
// Backend strings are the source of truth; this layer maps them to Russian UI copy.
// Unknown strings fall through unchanged (safe fallback).

const REASON_MAP: Record<string, string> = {
  // ── reasons[] bullets (services.py _final_decision) ─────────────────────
  'Target URL was classified as phishing.':
    'Целевой URL классифицирован как phishing.',
  'Target URL is suspicious.':
    'Целевой URL выглядит подозрительным.',
  'Phishing check was unavailable.':
    'Phishing-проверка была недоступна.',
  'Behavior session looks anomalous.':
    'Поведенческая сессия выглядит аномальной.',
  'Behavior analysis was unavailable.':
    'Поведенческий анализ был недоступен.',
  'High-value transaction with suspicious behavior baseline.':
    'Крупная операция с подозрительным поведенческим профилем.',
  'Target URL appears legitimate.':
    'Целевой URL выглядит легитимным.',
  'No behavior session was attached.':
    'Поведенческая сессия не была прикреплена.',
  'Behavior baseline is suspicious but below high-value threshold.':
    'Поведенческий профиль подозрителен, но сумма ниже порогового значения.',
  'Behavior baseline did not flag an anomaly.':
    'Поведенческий анализ не выявил аномалий.',

  // ── explanation field (get_explanation in serializers.py) ───────────────
  'Transaction denied because the target URL was classified as phishing.':
    'Транзакция отклонена: целевой URL классифицирован как phishing.',
  'Phishing check was unavailable; transaction requires additional verification.':
    'Phishing-проверка недоступна — транзакция требует дополнительной верификации.',
  'Transaction requires additional verification because the URL is suspicious.':
    'Транзакция требует дополнительной верификации: URL выглядит подозрительным.',
  'Transaction allowed by the current skeleton decision policy.':
    'Транзакция разрешена системой контроля рисков.',
}

// Phishing and behavior sub-decision labels
const DECISION_MAP: Record<string, string> = {
  'legitimate':    'легитимный',
  'suspicious':    'подозрительный',
  'phishing':      'phishing',
  'anomalous':     'аномальный',
  'not_available': 'нет данных',
  'not_checked':   'не проверялся',
  'unknown':       'неизвестно',
  'error':         'ошибка',
}

export function translateReason(reason: string): string {
  const trimmed = reason.trim()
  return REASON_MAP[trimmed] ?? trimmed
}

export function translateReasons(reasons: string[]): string[] {
  return reasons.map(translateReason)
}

export function translateDecision(decision: string): string {
  return DECISION_MAP[decision.toLowerCase()] ?? decision
}

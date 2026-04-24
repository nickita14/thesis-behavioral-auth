import type { TransactionAttemptPayload, TransactionAttemptResult } from '@/types/api'
import { api } from './api'

export async function createTransactionAttempt(
  payload: TransactionAttemptPayload,
): Promise<TransactionAttemptResult> {
  const { data } = await api.post<TransactionAttemptResult>('/transactions/attempts/', payload)
  return data
}

export async function listTransactionAttempts(): Promise<TransactionAttemptResult[]> {
  const { data } = await api.get<TransactionAttemptResult[]>('/transactions/attempts/')
  return data
}

import { api } from './api'

export interface ProfileMetadata {
  feature_schema_version: string
  detector_version: string
  n_training_samples: number
  n_training_sessions?: number
  training_score_mean?: number | null
  training_score_std?: number | null
  trained_at: string
}

export interface ProfileStatus {
  is_trained: boolean
  enrollment_sessions_completed: number
  enrollment_sessions_required: number
  ready_to_train: boolean
  profile: ProfileMetadata | null
}

export interface TrainResult {
  success: boolean
  profile?: ProfileMetadata
  error?: string
  n_sessions?: number
  n_samples?: number
  required_sessions?: number
  required_samples?: number
}

export async function getProfileStatus(): Promise<ProfileStatus> {
  const { data } = await api.get<ProfileStatus>('/ml/behavior-profile/status/')
  return data
}

export async function trainProfile(): Promise<TrainResult> {
  const { data } = await api.post<TrainResult>('/ml/behavior-profile/train/')
  return data
}

export async function deleteProfile(): Promise<void> {
  await api.delete('/ml/behavior-profile/')
}

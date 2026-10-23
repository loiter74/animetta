import type { Live2DModelProfile } from '@/shared/live2d/modelProfile'

// The absolute end check also excludes a trailing newline, which JavaScript's $ would allow.
const CANDIDATE_MODEL_URL =
  /^\/\.zcode\/[A-Za-z0-9_-]+(?:\/[A-Za-z0-9_-]+)*\/[A-Za-z0-9_-]+\.model3\.json(?![\s\S])/

export function resolveCandidateModelProfile(
  profile: Live2DModelProfile,
  search: URLSearchParams,
): Live2DModelProfile {
  if (search.get('review') !== '1' || search.get('media') !== 'muted') return profile
  const candidate = search.get('model')
  if (candidate === null || !CANDIDATE_MODEL_URL.test(candidate)) return profile
  return { ...profile, modelUrl: candidate }
}

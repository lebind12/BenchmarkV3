// 포메이션 string → 라인 별 인원 행렬 (GK 부터 ST 까지)

const FORMATIONS: Record<string, number[]> = {
  '4-3-3': [1, 4, 3, 3],
  '4-4-2': [1, 4, 4, 2],
  '4-2-3-1': [1, 4, 2, 3, 1],
  '4-3-2-1': [1, 4, 3, 2, 1],
  '3-5-2': [1, 3, 5, 2],
  '3-4-3': [1, 3, 4, 3],
  '5-3-2': [1, 5, 3, 2],
  '5-4-1': [1, 5, 4, 1],
  '4-1-4-1': [1, 4, 1, 4, 1],
  '4-5-1': [1, 4, 5, 1],
  '3-4-2-1': [1, 3, 4, 2, 1],
  '3-4-1-2': [1, 3, 4, 1, 2],
}

export function resolveFormation(formation: string | null): number[] {
  if (!formation) return [1, 4, 4, 2]
  return FORMATIONS[formation] ?? [1, 4, 4, 2]
}

export function formationLines(): string[] {
  return Object.keys(FORMATIONS)
}

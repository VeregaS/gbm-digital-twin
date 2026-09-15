export function formatNumber(
  value: number,
): string {
  if (Number.isInteger(value)) {
    return String(value);
  }

  return value.toFixed(1);
}


export function formatDay(
  value: number,
): string {
  return `${formatNumber(value)} d`;
}

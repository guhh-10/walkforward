export async function getHealth(): Promise<{ status: string }> {
  const response = await fetch('/api/health');

  if (!response.ok) {
    throw new Error(`API request failed: ${response.status}`);
  }

  return response.json();
}

export type FeatureCapability = {
  available: boolean;
  reason: string | null;
};


export type Capabilities = {
  patients: FeatureCapability;
  viewer: FeatureCapability;
  anatomy: FeatureCapability;

  digital_twin: FeatureCapability;
  runs: FeatureCapability;
  tools: FeatureCapability;
  research: FeatureCapability;
};


export async function fetchCapabilities():
Promise<Capabilities> {
  const response = await fetch(
    "/api/capabilities",
  );

  if (!response.ok) {
    throw new Error(
      "Failed to load backend capabilities",
    );
  }

  return (
    await response.json()
  ) as Capabilities;
}
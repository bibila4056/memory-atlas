// Temporary local asset registry; source IDs stay separate from media locations.
// The synthetic sample is retained byte-for-byte. This is not an approved story.
export function sourceAsset(assetId: string) {
  if (assetId !== "demo://flower-market-morning") {
    throw new Error(`Unknown source asset: ${assetId}`);
  }
  return {
    src: "/demo/flower-market-morning.png",
    width: 1536,
    height: 1024,
    alt: "Temporary synthetic sample of a flower market, with bouquets beside a café",
  };
}

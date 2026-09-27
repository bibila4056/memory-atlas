import type { components } from "./api-schema";

export type WeaveResult = components["schemas"]["WeaveResult"];

/** Plain-language provider line; never claims a model that did not run. */
export function engineLabel(w: WeaveResult) {
  const emb = w.providers.embeddings === "siglip2" ? "SigLIP 2 embeddings" : "fallback image features";
  const reasoning = w.providers.reasoning === "live" ? `live reasoning (${w.providers.reasoning_model})` : w.providers.reasoning === "fixture" ? "offline fixture reasoning" : "heuristic reasoning";
  return `BundleWeaver-lite · ${emb} · ${reasoning}`;
}

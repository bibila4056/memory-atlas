import Image from "next/image";
import type { CSSProperties } from "react";
import { sourceAsset } from "@/lib/demo-assets";
import { assertRenderable, type ElementMask, type ResolvedVisualPlan, type VisualElement } from "@/lib/plan";

function maskStyle(mask?: ElementMask | null): CSSProperties {
  if (!mask) return {};
  switch (mask.kind) {
    case "rectangle": return {};
    case "rounded_rectangle": return { borderRadius: mask.radius_px, overflow: "hidden" };
    case "ellipse": return { clipPath: "ellipse(50% 50% at 50% 50%)" };
    case "polygon": return { clipPath: `polygon(${mask.points.map(({ x, y }) => `${x * 100}% ${y * 100}%`).join(",")})` };
    case "svg_path": return { clipPath: `path(${JSON.stringify(mask.path)})` };
    case "alpha_mask": return { maskImage: `url(${JSON.stringify(mask.asset_ref)})`, maskSize: "100% 100%", maskRepeat: "no-repeat" };
  }
}

function ElementContent({ element }: { element: VisualElement }) {
  switch (element.kind) {
    case "photo": {
      const asset = sourceAsset(element.source_asset_id);
      return <Image src={asset.src} alt={asset.alt} fill unoptimized preload
        draggable={false} style={{ objectFit: element.fit, ...maskStyle(element.mask) }} />;
    }
    case "text": {
      const style: CSSProperties = { fontSize: element.font_size_px, textAlign: element.align };
      return <div className={`spread-text spread-text--${element.style_role}`} style={style}>{element.text}</div>;
    }
    case "generated_asset":
      return <Image src={element.asset_ref} alt="Source-derived botanical motif (temporary fallback)" fill unoptimized
        draggable={false} style={{ objectFit: "contain", ...maskStyle(element.mask) }} />;
    case "decoration":
      return <div aria-hidden="true" className={`chrome chrome--${element.chrome_kind}`} />;
    case "audio":
      // Playback/provenance belongs to its later ticket; no inert play control.
      return <div className="spread-text spread-text--caption">{element.transcript_excerpt ?? "Voice excerpt"}</div>;
  }
}

/** Fixed HTML layers: the viewport transforms the entire composition, never its elements. */
export function MemorySpread({ plan }: { plan: ResolvedVisualPlan }) {
  assertRenderable(plan);
  return (
    <article className="memory-spread" aria-label={`Memory spread: ${plan.title}`}
      data-testid="memory-spread" data-plan-id={plan.plan_id} data-plan-revision={plan.plan_revision}
      style={{ width: plan.canvas.width, height: plan.canvas.height, backgroundColor: plan.palette[0], color: plan.palette[1] }}>
      <div className="paper-grain" aria-hidden="true" />
      <div className="paper-gutter" aria-hidden="true" />
      {plan.elements.map((element) => (
        <div key={element.id} className={`spread-element spread-element--${element.kind}`}
          data-element-id={element.id} data-source-ids={"source_ids" in element ? element.source_ids.join(" ") : undefined}
          style={{ left: element.bounds.x, top: element.bounds.y, width: element.bounds.width,
            height: element.bounds.height, transform: `rotate(${element.rotation_deg ?? 0}deg)`, zIndex: element.z_index }}>
          <ElementContent element={element} />
        </div>
      ))}
      <div className="page-folio page-folio--left" aria-hidden="true">01</div>
      <div className="page-folio page-folio--right" aria-hidden="true">02</div>
    </article>
  );
}

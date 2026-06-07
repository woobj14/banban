// ═══════════════════════════════════════════════════════════════════
// Polar Webhook → Supabase Edge Function
// 결제/구독 이벤트 수신 → profiles.plan 자동 업데이트
//
// 배포:
//   supabase functions deploy polar-webhook --no-verify-jwt
// 환경변수(secret) 설정:
//   supabase secrets set POLAR_WEBHOOK_SECRET=...
//   (SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY 는 자동 주입됨)
// ═══════════════════════════════════════════════════════════════════

import { createClient } from "https://esm.sh/@supabase/supabase-js@2";
import { Webhook } from "https://esm.sh/standardwebhooks@1.0.0";

// Polar 상품 ID → 우리 플랜 매핑
// (Polar 대시보드의 각 상품 ID로 교체하세요)
const PRODUCT_PLAN: Record<string, string> = {
  "990181e3-04a8-4815-832b-af49b0c2bdd5": "student",
  "08231598-aaf0-4d6b-9637-f45881b752ca":     "pro",
};

// 상품명/가격으로도 매핑 (ID 모를 때 폴백)
function planFromPrice(amount: number): string {
  if (amount >= 19000) return "pro";
  if (amount >= 4000)  return "student";
  return "free";
}

Deno.serve(async (req) => {
  if (req.method !== "POST") {
    return new Response("Method not allowed", { status: 405 });
  }

  // ── 1. Webhook 서명 검증 (Standard Webhooks HMAC — Polar 규격) ──
  const secret = Deno.env.get("POLAR_WEBHOOK_SECRET") ?? "";
  const raw    = await req.text();

  let event: any;
  if (secret) {
    const whHeaders = {
      "webhook-id":        req.headers.get("webhook-id")        ?? "",
      "webhook-timestamp": req.headers.get("webhook-timestamp") ?? "",
      "webhook-signature": req.headers.get("webhook-signature") ?? "",
    };
    try {
      // Polar secret(polar_whs_…) → base64 키 부분으로 정규화
      const base64Secret = secret.replace(/^polar_whs_/, "").replace(/^whsec_/, "");
      const wh = new Webhook(base64Secret);
      // HMAC-SHA256 서명 + timestamp 신선도 검증. 실패 시 throw → 위조/재전송 차단
      event = wh.verify(raw, whHeaders);
    } catch (_e) {
      return new Response("Invalid signature", { status: 403 });
    }
  } else {
    // secret 미설정(개발 모드) — 검증 스킵
    try {
      event = JSON.parse(raw);
    } catch {
      return new Response("Invalid JSON", { status: 400 });
    }
  }

  const type = event?.type ?? "";
  const data = event?.data ?? {};

  // ── 2. 구독 이벤트만 처리 ───────────────────────────────────
  // subscription.created / .updated / .active → 플랜 부여
  // subscription.canceled / .revoked          → free 강등
  const customerEmail =
    data?.customer?.email ?? data?.user?.email ?? data?.customer_email ?? "";

  if (!customerEmail) {
    return new Response("No customer email", { status: 200 });
  }

  let newPlan = "free";
  if (type.includes("created") || type.includes("updated") || type.includes("active")) {
    const productId = data?.product_id ?? data?.product?.id ?? "";
    const amount    = data?.amount ?? data?.price?.price_amount ?? 0;
    newPlan = PRODUCT_PLAN[productId] ?? planFromPrice(amount);
  } else if (type.includes("canceled") || type.includes("revoked")) {
    newPlan = "free";
  } else {
    return new Response("Ignored event", { status: 200 });
  }

  // ── 3. Supabase profiles 업데이트 ───────────────────────────
  const supabase = createClient(
    Deno.env.get("SUPABASE_URL")!,
    Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!,  // service role: RLS 우회
  );

  // contact_email 또는 email 로 매칭
  const { error } = await supabase
    .from("profiles")
    .update({ plan: newPlan })
    .or(`email.eq.${customerEmail},contact_email.eq.${customerEmail}`);

  if (error) {
    return new Response(`DB error: ${error.message}`, { status: 500 });
  }

  return new Response(
    JSON.stringify({ ok: true, email: customerEmail, plan: newPlan }),
    { status: 200, headers: { "Content-Type": "application/json" } },
  );
});

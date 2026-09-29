// O checkout legado só pode ser exercitado em sandbox até a conciliação financeira existir.
export function sandboxCheckoutEnabled() {
  return process.env.IUSTUS_CHECKOUT_SANDBOX_ENABLED === "true"
    && process.env.NEXT_PUBLIC_PAGBANK_SANDBOX !== "false";
}

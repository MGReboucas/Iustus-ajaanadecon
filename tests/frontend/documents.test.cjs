const { test } = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const ts = require("../../frontend/node_modules/typescript");

const source = fs.readFileSync(path.join(__dirname, "../../frontend/src/lib/api/documents.ts"), "utf8");
const compiled = ts.transpileModule(source, { compilerOptions: {
  module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022,
} }).outputText;

function load(api, fetch) {
  const exports = {};
  class ApiError extends Error { constructor(code, message) { super(message); this.code = code; } }
  new Function("exports", "require", "fetch", compiled)(exports, () => ({ api, ApiError }), fetch);
  return exports;
}

test("arquivo grande usa PUT direto sem cookies ou token CSRF no bucket", async () => {
  const file = new File(["%PDF-", new Uint8Array(5 * 1024 * 1024)], "documento.pdf", { type: "application/pdf" });
  const calls = [];
  const api = async (route, data) => {
    calls.push({ route, data });
    if (route === "cases/case/documents/uploads") return { uploadId: "upload", directUpload: true };
    if (route === "uploads/upload/authorize") return {
      url: "https://bucket.example.test/object?signature=synthetic",
      method: "PUT", headers: { "Content-Type": "application/octet-stream", "If-None-Match": "*" },
    };
    if (route === "uploads/upload/complete") return { status: "QUARANTINED" };
    throw new Error("Rota inesperada: " + route);
  };
  const { uploadDocument } = load(api, async (url, options) => {
    assert.match(url, /^https:\/\/bucket\.example\.test\//);
    assert.equal(options.method, "PUT");
    assert.equal(options.credentials, "omit");
    assert.equal(options.referrerPolicy, "no-referrer");
    assert.equal(options.redirect, "error");
    assert.equal(options.body.byteLength, file.size);
    assert.equal(options.headers["X-CSRFToken"], undefined);
    return new Response(null, { status: 200 });
  });
  assert.equal((await uploadDocument("case", file)).status, "QUARANTINED");
  assert.equal(calls.length, 3);
  assert.match(calls[1].data.checksum, /^[a-f0-9]{64}$/);
  assert.equal(calls[1].data.checksum, calls[2].data.checksum);
});

test("falha no bucket não confirma nem libera o documento", async () => {
  const calls = [];
  const { uploadDocument } = load(async (route) => {
    calls.push(route);
    if (route.endsWith("/authorize")) return { url: "https://bucket.example.test/object", method: "PUT", headers: {} };
    return { uploadId: "upload", directUpload: true };
  }, async () => new Response("<Error>Denied</Error>", { status: 403 }));
  await assert.rejects(() => uploadDocument("case", new File(["%PDF-"], "a.pdf")), /envio falhou/);
  assert.equal(calls.some(route => route.endsWith("/complete")), false);
});

test("envio local mantém POST e proteção CSRF", async () => {
  const { uploadDocument } = load(async (route) => {
    if (route === "auth/csrf") return { csrfToken: "synthetic-csrf" };
    if (route.endsWith("/complete")) return { status: "QUARANTINED" };
    return { uploadId: "upload", uploadUrl: "/api/v1/uploads/upload/content", directUpload: false };
  }, async (url, options) => {
    assert.equal(url, "/api/v1/uploads/upload/content");
    assert.equal(options.method, "POST");
    assert.equal(options.credentials, "same-origin");
    assert.equal(options.headers["X-CSRFToken"], "synthetic-csrf");
    return new Response(null, { status: 204 });
  });
  assert.equal((await uploadDocument("case", new File(["%PDF-"], "a.pdf"))).status, "QUARANTINED");
});

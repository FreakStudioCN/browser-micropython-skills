# Blockless Validation Binding

`browser_validate` replaces all upstream host-side scripts and local command checks.

The Blockless validation binding accepts a `kind`, structured input, and current runtime state. It returns JSON with:

- `status`: `success`, `partial`, or `failed`
- `errors`: machine-readable blocking issues
- `warnings`: non-blocking findings
- `artifacts`: files the caller should persist with `file_operation`
- `capability_required`: missing Blockless runtime state, permission, connected device, login, or provider load state

Validation should run through Blockless browser code, Web Workers, WASM modules, or Blockless-owned services. Browser skills must not assume a local shell, local package manager, serial device name, or host filesystem path.

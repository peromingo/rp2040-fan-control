# Preview update channel

This definition contains the reviewed `0.8.0-source-rc2` package with the `pluginURL` attribute required by Unraid's update checker. Its payload and transaction scripts are byte-for-byte identical to the source-built candidate. The only changes are the update URL and the internal name `rp2040-fan-control` in the opening PLUGIN tag. A name with spaces breaks the CSS selectors used by Unraid to update the status cell, leaving it stuck at checking even when the download succeeds.

- Source package SHA-256: `1bfa566f2d378fe25831b87dae5c4753ba095c65cdfe058d007d5cbce935d273`
- Preview definition SHA-256: `117be7d210f87bb6041089835d142efd8455f7590edb462ace5928c27400bdfa`

Prepare or verify it from the repository root:

```sh
python3 tools/prepare_update_manifest.py \
  plugin/candidates/source-rc2/rp2040-fan-control-webui-integration-serial-v2-auditfix19.plg \
  plugin/channels/preview \
  --expected-sha256 1bfa566f2d378fe25831b87dae5c4753ba095c65cdfe058d007d5cbce935d273
```

Add `--verify` to check the stored definition, sidecar and provenance record without writing files. The tool does not install or execute the plugin.

The definition URL stays on the `source-tree-review` branch. Keep the branch available until installed preview definitions have migrated. Publish later reviewed preview versions by deliberately replacing this definition and regenerating its sidecar/provenance. The checker compares the version in the remote definition; equal versions should show as current. A newer preview must preserve source verification and pass CI before updating this pointer.

Do not point an installed stable channel here. Installing updates requires a stopped and explicitly disabled daemon; checking updates does not change daemon state. Current Unraid installations may adopt this metadata-only variant only after verifying that removing pluginURL and restoring the original name restores their exact installed reviewed PLG bytes. Back up the original definition first. This preserves runtime code and avoids restarting hardware control merely to enable checking.
